# CSDL SQLite của Multi-Tenant SaaS (schema v2). CSDL riêng (hub.db) — KHÔNG đụng gateway/du-lieu/gateway.db.
# v2 đổi lõi quyền: user ↔ NHIỀU tenant qua tenant_memberships; quyền lưu trong CSDL (roles/permissions).
import contextlib
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta

import cau_hinh

PHIEN_BAN_SCHEMA = 9

HAN_DOI_WAL = 40          # 40 lượt, giãn dần 50ms→2s: tổng ~41 giây
MUI_GIO_VN = timezone(timedelta(hours=7))
khoa_ghi = threading.RLock()   # serialize mọi lượt GHI (WAL: một writer tại một thời điểm)
# Mỗi THREAD một kết nối SQLite riêng. Dùng chung một connection giữa các thread
# (dù check_same_thread=False) làm các truy vấn đồng thời giẫm lên nhau → trả về byte rác
# (đã gặp: UnicodeDecodeError 0x80 khi dashboard gọi 2 API song song). Đây là cách an toàn chuẩn.
_local = threading.local()
_da_khoi_tao = threading.Event()
_khoa_khoi_tao = threading.Lock()


def bay_gio():
    return datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S%z")


def thang_nay():
    return datetime.now(MUI_GIO_VN).strftime("%Y-%m")


# Bảng nghiệp vụ dùng tên tiếng Việt (giữ nguyên từ bản trước để không phá mã đang chạy).
# Ánh xạ sang tên trong brief: users=users · tenants=tenants · tenant_memberships=tenant_memberships
# roles/permissions/role_permissions · user_sessions=sessions · customers=khach_hang
# carrier_providers=carrier_providers · carrier_accounts=carrier_accounts · orders=don_hang
# order_events=don_lich_su · audit_logs=audit.
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
  phien_ban INTEGER PRIMARY KEY,
  ap_dung_luc TEXT NOT NULL,
  ghi_chu TEXT
);
CREATE TABLE IF NOT EXISTS goi_dich_vu (
  id TEXT PRIMARY KEY, ten TEXT NOT NULL, gia_thang INTEGER NOT NULL,
  han_muc_don_thang INTEGER NOT NULL, han_muc_ai_thang INTEGER NOT NULL,
  so_nhan_vien INTEGER NOT NULL, so_tai_khoan_hang INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE,
  ten TEXT NOT NULL,
  goi_id TEXT NOT NULL REFERENCES goi_dich_vu(id),
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',   -- hoat_dong | khoa
  tao_luc TEXT NOT NULL,
  cap_nhat_luc TEXT
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ten_dang_nhap TEXT NOT NULL UNIQUE,
  mat_khau_hash TEXT NOT NULL,
  ho_ten TEXT NOT NULL,
  platform_role TEXT,                              -- NULL = người thường; PLATFORM_OWNER/PLATFORM_ADMIN
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',    -- hoat_dong | khoa (do QUẢN TRỊ khóa)
  so_lan_sai INTEGER NOT NULL DEFAULT 0,
  khoa_den TEXT,                                   -- khóa TẠM do đoán sai; hết giờ tự mở
  tao_luc TEXT NOT NULL,
  doi_mat_khau_luc TEXT
);
-- Một user thuộc NHIỀU tenant. Vai trò trong tenant nằm ở đây, không nằm ở users.
CREATE TABLE IF NOT EXISTS tenant_memberships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  role TEXT NOT NULL REFERENCES roles(ma),
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',    -- hoat_dong | vo_hieu
  moi_boi INTEGER REFERENCES users(id),
  tao_luc TEXT NOT NULL,
  UNIQUE (user_id, tenant_id)
);
CREATE INDEX IF NOT EXISTS ix_mem_user ON tenant_memberships(user_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_mem_tenant ON tenant_memberships(tenant_id, trang_thai);
CREATE TABLE IF NOT EXISTS roles (
  ma TEXT PRIMARY KEY, ten TEXT NOT NULL,
  pham_vi TEXT NOT NULL                            -- platform | tenant
);
CREATE TABLE IF NOT EXISTS permissions (
  ma TEXT PRIMARY KEY, mo_ta TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_permissions (
  role_ma TEXT NOT NULL REFERENCES roles(ma),
  perm_ma TEXT NOT NULL REFERENCES permissions(ma),
  PRIMARY KEY (role_ma, perm_ma)
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,                     -- SHA-256 của token; token gốc không lưu
  user_id INTEGER NOT NULL REFERENCES users(id),
  active_tenant_id INTEGER REFERENCES tenants(id), -- tenant đang thao tác (đổi bằng switch-tenant)
  tao_luc TEXT NOT NULL,
  het_han TEXT NOT NULL,
  thu_hoi INTEGER NOT NULL DEFAULT 0,
  dia_chi TEXT
);
CREATE INDEX IF NOT EXISTS ix_session_user ON sessions(user_id, thu_hoi);
CREATE TABLE IF NOT EXISTS reset_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  het_han TEXT NOT NULL,
  da_dung INTEGER NOT NULL DEFAULT 0,
  tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS khach_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten TEXT NOT NULL, sdt TEXT, dia_chi TEXT, ghi_chu TEXT,
  tao_luc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_khach_tenant ON khach_hang(tenant_id);
CREATE TABLE IF NOT EXISTS carrier_providers (
  ma TEXT PRIMARY KEY, ten TEXT NOT NULL,
  capabilities_json TEXT NOT NULL,
  live_mo INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  hang TEXT NOT NULL REFERENCES carrier_providers(ma),
  ten TEXT NOT NULL,
  moi_truong TEXT NOT NULL DEFAULT 'mock',         -- mock | sandbox | production (prod khóa ở local)
  credentials_ma_hoa TEXT NOT NULL,                -- JSON mã hóa (bao_mat.ma_hoa)
  credentials_duoi TEXT NOT NULL DEFAULT '',       -- 4 ký tự cuối để hiển thị
  credentials_doi_luc TEXT,                        -- lần rotate gần nhất
  webhook_ma TEXT NOT NULL,                        -- định danh công khai trên URL webhook
  webhook_secret_ma_hoa TEXT NOT NULL,
  kich_hoat INTEGER NOT NULL DEFAULT 1,            -- 1=ACTIVE, 0=DISABLED
  tao_luc TEXT NOT NULL,
  UNIQUE (webhook_ma)
);
CREATE INDEX IF NOT EXISTS ix_ca_tenant ON carrier_accounts(tenant_id, kich_hoat);
CREATE TABLE IF NOT EXISTS don_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ma_don TEXT NOT NULL,
  idem_key TEXT,
  khach_hang_id INTEGER REFERENCES khach_hang(id),
  nguoi_gui_ten TEXT NOT NULL, nguoi_gui_sdt TEXT NOT NULL, nguoi_gui_dia_chi TEXT NOT NULL,
  nguoi_nhan_ten TEXT NOT NULL, nguoi_nhan_sdt TEXT NOT NULL, nguoi_nhan_dia_chi TEXT NOT NULL,
  hang_hoa TEXT NOT NULL, khoi_luong_gram INTEGER NOT NULL,
  cod INTEGER NOT NULL DEFAULT 0, gia_tri_khai INTEGER NOT NULL DEFAULT 0,
  phi_van_chuyen INTEGER,
  ghi_chu TEXT,
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  ma_van_don TEXT,
  trang_thai TEXT NOT NULL DEFAULT 'nhap',         -- nhap | da_duyet | dang_gui | da_gui | huy
  can_doi_soat_ket_qua INTEGER NOT NULL DEFAULT 0,
  trang_thai_giao TEXT,
  hang_trang_thai_giao INTEGER NOT NULL DEFAULT 0,
  nguoi_tao INTEGER NOT NULL REFERENCES users(id),
  tao_luc TEXT NOT NULL, cap_nhat_luc TEXT NOT NULL,
  UNIQUE (tenant_id, ma_don),
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_don_tenant ON don_hang(tenant_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_don_mvd ON don_hang(ma_van_don);
CREATE TABLE IF NOT EXISTS don_lich_su (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  don_id INTEGER NOT NULL REFERENCES don_hang(id),
  luc TEXT NOT NULL, nguon TEXT NOT NULL,
  noi_dung TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ls_don ON don_lich_su(don_id);
CREATE TABLE IF NOT EXISTS wh_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  carrier_account_id INTEGER NOT NULL REFERENCES carrier_accounts(id),
  event_id TEXT NOT NULL,
  payload_tho BLOB NOT NULL, headers_json TEXT NOT NULL,
  nhan_luc TEXT NOT NULL,
  trang_thai TEXT NOT NULL DEFAULT 'moi',
  so_lan_thu INTEGER NOT NULL DEFAULT 0, loi_cuoi TEXT, xu_ly_xong_luc TEXT,
  UNIQUE (carrier_account_id, event_id)
);
CREATE TABLE IF NOT EXISTS import_batch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten_file TEXT NOT NULL, loai_file TEXT NOT NULL,
  -- UPLOADED PARSING VALIDATING READY APPROVED PROCESSING COMPLETED PARTIAL_FAILED FAILED
  -- (SHARED_CONTRACTS mục 6). Giá trị cũ 'moi'/'da_duyet_mot_phan'/'xong' vẫn ĐỌC được
  -- qua nhap_file.trang_thai_batch() — không cần migrate dữ liệu để mã chạy.
  trang_thai TEXT NOT NULL DEFAULT 'UPLOADED',
  loi TEXT,                                        -- lý do khi batch ở FAILED
  nguoi_tao INTEGER NOT NULL REFERENCES users(id), tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_dong (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES import_batch(id),
  stt INTEGER NOT NULL,
  du_lieu_json TEXT NOT NULL,
  -- VALID INVALID READY SUBMITTED SUCCESS FAILED UNSUPPORTED NEEDS_REVIEW
  trang_thai TEXT NOT NULL,
  loi TEXT,                                        -- lỗi chặn HOẶC cảnh báo 'cần xem: ...'
  don_id INTEGER REFERENCES don_hang(id)
);
CREATE TABLE IF NOT EXISTS usage_thang (
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  thang TEXT NOT NULL,
  so_don INTEGER NOT NULL DEFAULT 0,
  so_ai INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, thang)
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  luc TEXT NOT NULL,
  tenant_id INTEGER,
  user_id INTEGER,                                 -- actor_id
  hanh_dong TEXT NOT NULL,                         -- action
  doi_tuong TEXT NOT NULL,                         -- "<resource_type>:<resource_id>"
  resource_type TEXT, resource_id TEXT,
  ket_qua TEXT NOT NULL DEFAULT 'thanh_cong',      -- thanh_cong | tu_choi | that_bai
  chi_tiet TEXT, dia_chi TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_tenant ON audit(tenant_id, id);
"""


# ====== BIÊN DRIVER — chỉ tệp NÀY được `import sqlite3` ======
# Trước đây 7 tệp cùng nạp driver, nhưng 5 trong số đó KHÔNG mở kết nối nào: chúng nạp
# cả driver chỉ để gọi tên ba kiểu của nó (`Row`, `IntegrityError`, `Error`). Đó là nợ
# kiến trúc đo được: mã nghiệp vụ nói tên một driver cụ thể ở 10 chỗ rời nhau, nên đổi
# driver là đi sửa 10 chỗ — và chỗ nào quên thì KHÔNG báo lỗi lúc nạp, chỉ hỏng lúc
# đúng nhánh `except` đó chạy (CLAUDE.md §12.2: hỏng im lặng).
# Ba tên dưới đây là tên NGHIỆP VỤ của ba tình huống, không phải tên driver:
Row = sqlite3.Row                     # một hàng truy cập được theo tên cột
LoiCSDL = sqlite3.Error               # gốc của mọi lỗi tầng CSDL
LoiToanVen = sqlite3.IntegrityError   # vi phạm UNIQUE / FOREIGN KEY / CHECK / NOT NULL
LoiVanHanh = sqlite3.OperationalError # CSDL bị khóa, hết giờ chờ, bảng không có
# Lưu ý khi sang PostgreSQL: `LoiToanVen` ánh xạ được sang `psycopg.errors.IntegrityError`,
# nhưng `LoiVanHanh` thì KHÔNG một-một — ca "database is locked" của SQLite tương ứng
# `SerializationFailure`/`LockNotAvailable` bên kia. Chỗ đó phải đo lại, không suy ra.


# `sqlite3.complete_statement`: một câu SQL đã TRỌN chưa. Phơi ra đây vì biên driver —
# migrate cần nó để tách DDL mà không được tự nạp sqlite3.
cau_sql_du = sqlite3.complete_statement


def ket_noi(duong_dan=None, timeout=10, theo_ten_cot=False, tuong_minh=False):
    """Kết nối THÔ, KHÔNG dùng bộ nhớ đệm theo thread — dành cho migrate, sao lưu, công cụ.

    Khác `mo()` ở hai điểm cố ý: người gọi phải tự `close()`, và không đặt
    `foreign_keys=ON` (migrate cần tắt khóa ngoại để đổi bảng).

    `tuong_minh=True` tắt phần TỰ QUẢN GIAO DỊCH của mô-đun sqlite3 (isolation_level=None):
    từ đó `BEGIN`/`COMMIT`/`ROLLBACK` do người gọi viết là thứ DUY NHẤT điều khiển giao dịch.
    Cần thiết, không phải cho đẹp — đo được ngày 15/10/2026: ở chế độ mặc định, ba tiến trình
    cùng chạy `BEGIN IMMEDIATE` thì CẢ BA đều lấy được khoá (0,000 · 0,038 · 0,051 giây) dù
    COMMIT đầu tiên mãi 0,074 giây mới xảy ra — tức khoá KHÔNG loại trừ được ai. Lý do: mô-đun
    tự mở/chốt giao dịch theo sổ sách riêng của nó, và sổ đó lệch với `BEGIN` tường minh (ca A
    đã đo: sau một `SAVEPOINT`, `in_transaction` vẫn báo False). Hai bộ điều khiển cùng tranh
    một giao dịch thì không bộ nào đúng.
    """
    kn = sqlite3.connect(duong_dan or cau_hinh.DUONG_DAN_CSDL, timeout=timeout,
                         isolation_level=None if tuong_minh else "")
    if theo_ten_cot:
        kn.row_factory = Row
    return kn


def _dat_wal(kn):
    """Bật WAL — nhưng ĐỌC TRƯỚC, chỉ ĐẶT khi chưa phải WAL.

    `PRAGMA journal_mode=WAL` cần khoá ĐỘC QUYỀN để đổi chế độ sổ ghi; `PRAGMA journal_mode`
    (không gán) chỉ là lượt đọc, không cần khoá nào. Gần như mọi lượt mở kết nối thì CSDL đã
    ở WAL, nên lượt đặt ấy chẳng đổi gì mà vẫn phải tranh khoá độc quyền. Đo 15/10/2026:
    8 tiến trình cùng mở một CSDL MỚI thì 3 chết ngay tại dòng đặt WAL với "database is
    locked", trước khi migration kịp bắt đầu.
    """
    # `busy_timeout` KHÔNG phủ lệnh đổi chế độ sổ ghi: SQLite trả SQLITE_BUSY NGAY khi có
    # kết nối khác đang mở, không chờ. Nên phải tự chờ. Đo 15/10/2026: 8 tiến trình cùng mở
    # một CSDL MỚI thì 1 tiến trình nhận "database is locked" ở đúng chỗ này (chập chờn,
    # 1/8 lượt) kể cả sau khi đã thêm busy_timeout 30 giây.
    #
    # Và chỉ cần MỘT tiến trình đặt được WAL là cả CSDL thành WAL — nên thua cuộc đua này
    # không phải lỗi, miễn là đọc lại thấy đã thành WAL.
    for lan in range(HAN_DOI_WAL):
        if (kn.execute("PRAGMA journal_mode").fetchone()[0] or "").lower() == "wal":
            return
        try:
            kn.execute("PRAGMA journal_mode=WAL")
            return
        except sqlite3.OperationalError:
            time.sleep(0.05 * (lan + 1))
    che_do = (kn.execute("PRAGMA journal_mode").fetchone()[0] or "?").lower()
    if che_do != "wal":
        # KHÔNG đi tiếp im lặng: chế độ `delete` vẫn chạy nhưng cho MỘT người ghi tại một
        # thời điểm và chặn cả người đọc — hệ sẽ chậm bất thường mà không ai biết vì sao.
        raise LoiVanHanh(
            "không chuyển được CSDL sang WAL sau %d lượt thử (đang ở %r). Có tiến trình khác "
            "giữ CSDL rất lâu, hoặc CSDL nằm trên ổ mạng — SQLite không khoá đáng tin ở đó."
            % (HAN_DOI_WAL, che_do))


def _khoi_tao_schema(kn):
    """Tạo schema + seed MỘT lần, TRÊN KẾT NỐI TRUYỀN VÀO — không tự mở kết nối thứ hai.

    Trước 15/10/2026 hàm này tự `sqlite3.connect()` một kết nối tạm, và `mo()` gọi nó TRƯỚC
    khi xét kết nối của thread. Cộng với việc `dong()` xoá cờ `_da_khoi_tao` — biến TOÀN CỤC,
    không theo thread — nó sinh ra ca TỰ KHOÁ CHÍNH MÌNH: thread B đang mở giao dịch trên kết
    nối B1; thread A gọi `dong()` xoá cờ; lượt ghi tiếp của B vào `mo()` → thấy cờ trống →
    chạy hàm này → mở kết nối B2 → B2 ghi và chờ khoá mà chính B1 đang giữ. Một thread, hai
    kết nối, khoá nhau. Không khoá nào của Python cứu được: `khoa_ghi` là RLock nên B đi
    xuyên qua nó, vì B đã giữ nó rồi.

    Đo trong `test_d5` (10 thread): thời gian mỗi thread LƯỢNG TỬ HOÁ theo đúng busy_timeout
    — 0,005 · 30,35 · 30,35 · 60,70 · 60,70 · 91,04 · 91,05 · 121,42 · 121,43 · 121,43 giây,
    4 thread nhận `database is locked`. Không phải "chậm" mà là CHỜ HẾT GIỜ theo từng đợt.
    Chỉ lộ ra khi giao dịch trải cả khối, nên `giao_dich()` không gây ra lỗi này — lỗi nằm sẵn.

    Dùng chính kết nối của thread thì không còn kết nối thứ hai để khoá nhau. `mo()` chỉ gọi
    hàm này khi thread CHƯA có kết nối, nên lúc đó không thể đang giữa một giao dịch —
    `executescript` tự COMMIT, mà ở đây không có gì để commit sớm.
    """
    with khoa_ghi, _khoa_khoi_tao:
        if _da_khoi_tao.is_set():
            return
        kn.executescript(SCHEMA)
        for g in cau_hinh.GOI_MAC_DINH:
            kn.execute(
                "INSERT OR IGNORE INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,han_muc_ai_thang,so_nhan_vien,so_tai_khoan_hang) "
                "VALUES (:id,:ten,:gia_thang,:han_muc_don_thang,:han_muc_ai_thang,:so_nhan_vien,:so_tai_khoan_hang)", g)
        kn.commit()
        _da_khoi_tao.set()


def mo():
    """Trả kết nối RIÊNG của thread hiện tại (tạo nếu chưa có).

    THỨ TỰ CỐ Ý: có kết nối thì trả NGAY, không xét cờ khởi tạo. Thiếu lối ra sớm này thì một
    lượt ghi giữa giao dịch rơi được vào `_khoi_tao_schema` — xem chú thích ở đó.
    """
    kn = getattr(_local, "kn", None)
    if kn is not None:
        return kn
    os.makedirs(cau_hinh.THU_MUC_DU_LIEU, exist_ok=True)
    # `isolation_level=None`: TẮT phần tự quản giao dịch của mô-đun. Cùng lý do như
    # `ket_noi(tuong_minh=True)` — hai bộ điều khiển tranh một giao dịch thì không bộ nào đúng.
    kn = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL, timeout=30, isolation_level=None)
    kn.row_factory = Row
    _dat_wal(kn)
    kn.execute("PRAGMA foreign_keys=ON")
    kn.execute("PRAGMA busy_timeout=30000")
    _local.kn = kn
    if not _da_khoi_tao.is_set():
        _khoi_tao_schema(kn)
    return kn


def dong():
    """Đóng kết nối của thread hiện tại và cho phép khởi tạo lại (phục vụ bộ thử)."""
    kn = getattr(_local, "kn", None)
    if kn is not None:
        kn.close()
        _local.kn = None
    _local.sau_giao_dich = 0   # bậc lồng đi theo kết nối; quên xoá là lượt sau không chịu commit
    _da_khoi_tao.clear()


def phien_ban_hien_tai():
    """Phiên bản schema đang có trong CSDL (0 nếu chưa ghi nhận)."""
    r = mot("SELECT MAX(phien_ban) pb FROM schema_version")
    return (r["pb"] or 0) if r else 0


def ghi(sql, tham_so=()):
    """Ghi MỘT câu. Tự commit NẾU không nằm trong `giao_dich()`; nằm trong thì để khối ngoài chốt."""
    kn = mo()
    with khoa_ghi:
        # Kết nối ở chế độ tường minh (isolation_level=None) nên MỘT câu ngoài giao dịch
        # tự chốt luôn — không cần `commit()`. Trong giao dịch thì tuyệt đối không chốt.
        return kn.execute(sql, tham_so)


@contextlib.contextmanager
def giao_dich():
    """Gộp nhiều câu ghi thành MỘT đơn vị: vào hết, hoặc không câu nào vào.

    Vì sao cần, đo được ngày 15/10/2026: `tai_chinh.ghi_but_toan` có docstring ghi
    "ghi bút toán + cập nhật công nợ trong CÙNG một transaction", nhưng cả hai bước đều gọi
    `csdl.ghi()` — mà hàm đó commit sau MỖI câu. Ép bước hai hỏng: bút toán 777.000đ VÀO SỔ,
    công nợ KHÔNG đổi, sổ lệch đúng 777.000đ. Và bút toán ấy KHÔNG XOÁ ĐƯỢC (trigger bất
    biến), nên sai nằm lại vĩnh viễn, chỉ chữa được bằng bút toán đảo.

    Dùng SAVEPOINT cho MỌI tầng, không dùng `BEGIN IMMEDIATE`. Đo trên python 3.9.6 +
    SQLite 3.51.0 (ca C): `BEGIN IMMEDIATE` NỔ "cannot start a transaction within a
    transaction" nếu python đã tự mở giao dịch cho một câu DML trước đó — mà python tự mở
    lúc nào thì mã gọi không kiểm soát được. SAVEPOINT chạy đúng ở CẢ HAI thế: ở đỉnh thì nó
    tự mở giao dịch (đo ca F: RELEASE xong dữ liệu BỀN, đọc được từ kết nối khác; ca G:
    ROLLBACK TO thì bỏ sạch), lồng trong thì nó là điểm lùi (ca H).

    Nó cũng vá được ca nguy nhất — ca E: `RAISE(ABORT)` của SQLite chỉ huỷ CÂU, không huỷ
    GIAO DỊCH, nên câu chạy SAU một trigger-chặn vẫn commit bình thường. Bọc SAVEPOINT thì
    câu trước đó bị cuốn theo (đo ca I). PostgreSQL thì `RAISE EXCEPTION` huỷ cả giao dịch —
    KHÁC BIỆT THẬT, đã ghi trong thu_postgres.test_c2.

    Giữ `khoa_ghi` suốt khối: trong MỘT tiến trình thì mỗi lúc chỉ một người ghi.
    KHÔNG phủ nhiều tiến trình — chỗ đó phải đo riêng (mục 11 của chỉ thị G12).
    """
    kn = mo()
    with khoa_ghi:
        sau = getattr(_local, "sau_giao_dich", 0)
        ten = "gd%d" % sau
        if sau == 0:
            # TẦNG NGOÀI lấy khoá GHI NGAY (`BEGIN IMMEDIATE`), không mở giao dịch hoãn.
            #
            # `SAVEPOINT` trần mở giao dịch HOÃN: khoá đọc trước, tới câu ghi mới xin nâng
            # lên khoá ghi. Nếu tiến trình khác đã commit kể từ ảnh đọc của mình thì SQLite
            # trả SQLITE_BUSY_SNAPSHOT — và `busy_timeout` KHÔNG chờ ca này, nó trả NGAY.
            # Đo 15/10/2026 (2 tiến trình × 15 lượt đọc-sửa-ghi): 14/30 lượt nhận
            # "database is locked" ở 0,0 giây. Không phải chờ lâu — là bị từ chối tức thì.
            # Xin khoá ghi ngay từ đầu thì không còn lượt nâng nào để mà thất bại, và
            # `busy_timeout` CÓ phủ `BEGIN IMMEDIATE` (đo: các tiến trình chờ 0,047–0,106s
            # rồi vào được, ở bộ thu_migrate_dong_thoi).
            kn.execute("BEGIN IMMEDIATE")
        else:
            kn.execute("SAVEPOINT " + ten)
        _local.sau_giao_dich = sau + 1
        try:
            yield kn
        except BaseException:
            # BaseException chứ không Exception: KeyboardInterrupt/SystemExit giữa chừng cũng
            # phải lùi, không được để lại nửa bút toán rồi đi ra.
            if sau == 0:
                kn.execute("ROLLBACK")
            else:
                kn.execute("ROLLBACK TO " + ten)
                kn.execute("RELEASE " + ten)
            _local.sau_giao_dich = sau
            raise
        if sau == 0:
            kn.execute("COMMIT")
        else:
            kn.execute("RELEASE " + ten)
        _local.sau_giao_dich = sau


def mot(sql, tham_so=()):
    return mo().execute(sql, tham_so).fetchone()


def nhieu(sql, tham_so=()):
    return mo().execute(sql, tham_so).fetchall()


def audit(hanh_dong, doi_tuong, chi_tiet="", tenant_id=None, user_id=None, dia_chi=None,
          ket_qua="thanh_cong"):
    """Ghi audit log. doi_tuong dạng '<resource_type>:<resource_id>' — tự tách thành 2 cột."""
    rt, _, rid = doi_tuong.partition(":")
    ghi("INSERT INTO audit (luc, tenant_id, user_id, hanh_dong, doi_tuong, resource_type, resource_id,"
        " ket_qua, chi_tiet, dia_chi) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (bay_gio(), tenant_id, user_id, hanh_dong, doi_tuong, rt or None, rid or None,
         ket_qua, chi_tiet, dia_chi))
