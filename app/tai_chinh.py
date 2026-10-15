# G07 — TÀI CHÍNH: sổ COD, phí hãng, đợt thanh toán, công nợ, điều chỉnh, nhật ký bất biến.
#
# ===== BỐN BẤT BIẾN CỦA FILE NÀY (docs/SHARED_CONTRACTS.md mục 16, 17, 18) =====
#
# 1) TIỀN LÀ `INTEGER` ĐỒNG. Không float, không Decimal, không nhân 100. Vào cửa nào cũng đi
#    qua `so_tien()` — hàm đó CHẶN phần thập phân thay vì cắt cụt (mất tiền im lặng là dạng
#    hỏng xấu nhất). Chỉ có MỘT bộ lọc tiền trong hệ: `don_hang._so_nguyen_tien`. File này
#    GỌI LẠI nó, không viết bản thứ hai — hai bộ lọc là hai bộ sẽ lệch nhau (§12.2).
#
# 2) BÚT TOÁN BẤT BIẾN. Sai thì ghi bút toán ĐẢO. Điều này được CSDL cưỡng chế bằng TRIGGER
#    `BEFORE UPDATE`/`BEFORE DELETE` → `RAISE(ABORT)` trên `tc_but_toan` và `tc_nhat_ky`,
#    KHÔNG bằng lời dặn trong tài liệu. Một `UPDATE` lọt vào sau này sẽ ném lỗi ngay, không
#    sửa sổ trong im lặng.
#
# 3) `trang_thai_giao='giao_thanh_cong'` KHÔNG LÀM COD THÀNH `COD_SETTLED`. Giao hàng và thu
#    tiền là hai sự kiện của hai bên khác nhau, cách nhau nhiều ngày. Trong file này KHÔNG có
#    đường nào đi từ trạng thái giao sang `COD_SETTLED`: muốn settled thì phải có một ĐỢT
#    THANH TOÁN của hãng (`tc_dot_tt`) với số tiền thật. Ca thử `thu_tai_chinh` canh điều đó.
#
# 4) CÁCH LY TENANT Ở MỌI TRUY VẤN. Mọi `SELECT`/`UPDATE` trong file này đều có `tenant_id=?`.
#    Không có hàm nào nhận `don_id` mà không nhận `tenant_id`.
#
# ===== ĐỒNG THỜI =====
# Mọi lượt đổi trạng thái/cộng tiền làm bằng MỘT câu `UPDATE` có điều kiện trạng thái trong
# `WHERE` rồi xét `rowcount` (khuôn `don_hang._chiem_de_gui`, `gioi_han._cong_co_tran`).
# CẤM đọc-rồi-ghi: hai lượt song song cùng đọc thấy "chưa áp" thì cả hai đều áp.
#
# ===== SCHEMA =====
# `DDL_G07` dưới đây là MỘT NGUỒN DUY NHẤT cho ba chỗ: bộ thử (tự chạy qua `_dam_bao_bang()`),
# tài liệu `docs/G07_FINAL_REPORT.md`, và đề xuất migration v8 gửi AG-00. AG-01 KHÔNG được sửa
# `app/csdl.py` / `app/migrate.py` (hợp đồng mục 22), nên mã ở đây phải chạy được trên CSDL
# CHƯA có migration v8 — `_dam_bao_bang()` dùng `CREATE TABLE IF NOT EXISTS`.
import hashlib
import json
import threading

import csdl
import don_hang
import quyen


# ============================================================================
# DDL ĐỀ XUẤT CHO AG-00 (migration v8) — file này KHÔNG ghi vào csdl.py/migrate.py
# ============================================================================
# KHÔNG có `DROP`, KHÔNG có `ALTER ... TYPE`, KHÔNG xoá dữ liệu. Hai chữ `DELETE` duy nhất
# nằm trong `BEFORE DELETE ... RAISE(ABORT)` — đó là CHỐT CHẶN xoá, ngược với xoá.
DDL_G07 = """
-- ---------- 1. Bút toán bất biến (SHARED_CONTRACTS §17) ----------
CREATE TABLE IF NOT EXISTS tc_but_toan (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
  loai               TEXT    NOT NULL,              -- xem tai_chinh.TAC_DONG_CONG_NO
  don_id             INTEGER REFERENCES don_hang(id),
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  so_tien_dong       INTEGER NOT NULL,              -- ĐỒNG, luôn >= 0; hướng nằm ở `chieu`
  chieu              TEXT    NOT NULL,              -- ghi_no | ghi_co
  nguon              TEXT    NOT NULL,              -- hang | nguoi | he_thong
  can_cu             TEXT    NOT NULL,              -- vì sao có dòng này (bắt buộc, không rỗng)
  tao_boi            INTEGER,                       -- users.id; NULL = hệ thống
  tao_luc            TEXT    NOT NULL,
  batch_id           INTEGER,                       -- ds_dot.id hoặc tc_dot_tt.id
  dao_cua            INTEGER REFERENCES tc_but_toan(id),  -- dòng này ĐẢO dòng nào
  CHECK (so_tien_dong >= 0),
  CHECK (chieu IN ('ghi_no','ghi_co')),
  CHECK (nguon IN ('hang','nguoi','he_thong')),
  CHECK (length(can_cu) > 0)
);
CREATE INDEX IF NOT EXISTS ix_tc_bt_tenant ON tc_but_toan(tenant_id, id);
CREATE INDEX IF NOT EXISTS ix_tc_bt_don ON tc_but_toan(tenant_id, don_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_tc_bt_dao ON tc_but_toan(dao_cua)
  WHERE dao_cua IS NOT NULL;
-- Bất biến do CSDL cưỡng chế, không do lời dặn.
CREATE TRIGGER IF NOT EXISTS trg_tc_but_toan_cam_sua
  BEFORE UPDATE ON tc_but_toan
  BEGIN SELECT RAISE(ABORT, 'tc_but_toan bat bien: sai thi ghi but toan DAO, khong UPDATE'); END;
CREATE TRIGGER IF NOT EXISTS trg_tc_but_toan_cam_xoa
  BEFORE DELETE ON tc_but_toan
  BEGIN SELECT RAISE(ABORT, 'tc_but_toan bat bien: khong duoc xoa but toan'); END;

-- ---------- 2. Nhật ký tài chính bất biến, có móc băm ----------
CREATE TABLE IF NOT EXISTS tc_nhat_ky (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  luc       TEXT    NOT NULL,
  hanh_dong TEXT    NOT NULL,
  doi_tuong TEXT    NOT NULL,                       -- "<loai>:<id>"
  chi_tiet  TEXT    NOT NULL DEFAULT '',
  nguoi     INTEGER,
  bam_truoc TEXT    NOT NULL DEFAULT '',            -- băm của dòng trước CÙNG tenant
  bam       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tc_nk_tenant ON tc_nhat_ky(tenant_id, id);
CREATE TRIGGER IF NOT EXISTS trg_tc_nhat_ky_cam_sua
  BEFORE UPDATE ON tc_nhat_ky
  BEGIN SELECT RAISE(ABORT, 'tc_nhat_ky bat bien: khong duoc sua'); END;
CREATE TRIGGER IF NOT EXISTS trg_tc_nhat_ky_cam_xoa
  BEFORE DELETE ON tc_nhat_ky
  BEGIN SELECT RAISE(ABORT, 'tc_nhat_ky bat bien: khong duoc xoa'); END;

-- ---------- 3. Sổ COD, một dòng một đơn (SHARED_CONTRACTS §18) ----------
CREATE TABLE IF NOT EXISTS tc_cod (
  don_id             INTEGER PRIMARY KEY REFERENCES don_hang(id),
  tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  so_tien_du_kien    INTEGER NOT NULL DEFAULT 0,    -- COD khi tạo đơn
  so_tien_hang_bao   INTEGER,                       -- hãng báo đã thu (NULL = chưa báo)
  so_tien_doi_soat   INTEGER,                       -- số đã chốt sau đối soát
  so_tien_da_tt      INTEGER NOT NULL DEFAULT 0,    -- hãng đã trả về (cộng dần, cho phép một phần)
  trang_thai         TEXT    NOT NULL DEFAULT 'COD_EXPECTED',
  ly_do_tranh_chap   TEXT,
  tao_luc            TEXT    NOT NULL,
  cap_nhat_luc       TEXT    NOT NULL,
  CHECK (so_tien_du_kien >= 0),
  CHECK (so_tien_da_tt >= 0),
  CHECK (trang_thai IN ('COD_EXPECTED','COD_COLLECTED','COD_RECONCILED',
                        'COD_SETTLED','COD_DISPUTED','COD_ADJUSTED'))
);
CREATE INDEX IF NOT EXISTS ix_tc_cod_tenant ON tc_cod(tenant_id, trang_thai);

-- ---------- 4. Lịch sử chuyển trạng thái COD ----------
CREATE TABLE IF NOT EXISTS tc_cod_chuyen (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  don_id    INTEGER NOT NULL REFERENCES don_hang(id),
  tu        TEXT    NOT NULL,
  den       TEXT    NOT NULL,
  nguon     TEXT    NOT NULL,
  can_cu    TEXT    NOT NULL,
  nguoi     INTEGER,
  luc       TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tc_codch_don ON tc_cod_chuyen(tenant_id, don_id, id);

-- ---------- 5. Phí vận chuyển: nhiều khoản một đơn, mỗi khoản có NGUỒN ----------
CREATE TABLE IF NOT EXISTS tc_phi (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
  don_id             INTEGER REFERENCES don_hang(id),
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  loai               TEXT    NOT NULL,              -- xem tai_chinh.LOAI_PHI
  so_tien_dong       INTEGER NOT NULL,              -- có thể ÂM (phí hoàn / điều chỉnh giảm)
  nguon              TEXT    NOT NULL,              -- hang | nguoi | he_thong
  can_cu             TEXT    NOT NULL,
  ghi_nhan_luc       TEXT    NOT NULL,              -- thời điểm ghi nhận (yêu cầu G07.3)
  tao_boi            INTEGER,
  but_toan_id        INTEGER REFERENCES tc_but_toan(id),
  batch_id           INTEGER,
  CHECK (nguon IN ('hang','nguoi','he_thong')),
  CHECK (length(can_cu) > 0)
);
CREATE INDEX IF NOT EXISTS ix_tc_phi_don ON tc_phi(tenant_id, don_id, loai);

-- ---------- 6. Đợt thanh toán của hãng (hãng chuyển tiền COD về) ----------
CREATE TABLE IF NOT EXISTS tc_dot_tt (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
  hang               TEXT    NOT NULL,
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  ma_dot             TEXT    NOT NULL,              -- mã sao kê/uỷ nhiệm chi của hãng
  ky_tu              TEXT,
  ky_den             TEXT,
  so_tien_hang_bao   INTEGER NOT NULL DEFAULT 0,
  trang_thai         TEXT    NOT NULL DEFAULT 'MOI',   -- MOI | DA_AP | HUY
  tao_boi            INTEGER,
  tao_luc            TEXT    NOT NULL,
  ap_luc             TEXT,
  CHECK (so_tien_hang_bao >= 0),
  CHECK (trang_thai IN ('MOI','DA_AP','HUY')),
  UNIQUE (tenant_id, hang, ma_dot)                  -- idempotent: cùng mã đợt = một đợt
);

-- ---------- 7. Dòng của đợt thanh toán ----------
CREATE TABLE IF NOT EXISTS tc_dot_tt_dong (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  dot_id       INTEGER NOT NULL REFERENCES tc_dot_tt(id),
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  don_id       INTEGER NOT NULL REFERENCES don_hang(id),
  so_tien_dong INTEGER NOT NULL,
  CHECK (so_tien_dong >= 0),
  UNIQUE (dot_id, don_id)                           -- một đơn một lần trong một đợt
);

-- ---------- 8. Công nợ: phải thu / phải trả theo đối tác ----------
-- Đây là số TỔNG HỢP, dựng từ `tc_but_toan`. `tinh_lai_cong_no()` dựng lại được từ đầu và
-- ca thử đối chiếu hai con số — lệch là bộ thử HỎNG, không lệch im lặng.
CREATE TABLE IF NOT EXISTS tc_cong_no (
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  so           TEXT    NOT NULL,                    -- phai_thu | phai_tra
  doi_tac      TEXT    NOT NULL,                    -- 'hang:vtp' | 'noi_bo'
  so_du_dong   INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT,
  PRIMARY KEY (tenant_id, so, doi_tac),
  CHECK (so IN ('phai_thu','phai_tra'))
);

-- ---------- 9. Điều chỉnh tài chính: lý do + người + lịch sử, bắt buộc ----------
CREATE TABLE IF NOT EXISTS tc_dieu_chinh (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  don_id       INTEGER REFERENCES don_hang(id),
  loai         TEXT    NOT NULL,                    -- cod | phi
  so_tien_dong INTEGER NOT NULL,                    -- âm = giảm
  ly_do        TEXT    NOT NULL,
  nguoi        INTEGER NOT NULL REFERENCES users(id),
  but_toan_id  INTEGER REFERENCES tc_but_toan(id),
  luc          TEXT    NOT NULL,
  CHECK (length(ly_do) > 0),
  CHECK (loai IN ('cod','phi'))
);
CREATE INDEX IF NOT EXISTS ix_tc_dc_tenant ON tc_dieu_chinh(tenant_id, id);

-- ---------- 10. Đợt đối soát (import bảng kê của hãng) ----------
CREATE TABLE IF NOT EXISTS ds_dot (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id          INTEGER NOT NULL REFERENCES tenants(id),
  hang               TEXT    NOT NULL,
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  ten_file           TEXT    NOT NULL,
  loai_file          TEXT    NOT NULL,              -- csv | xlsx
  van_tay_file       TEXT    NOT NULL,              -- sha256 nội dung file
  anh_xa_phien_ban   TEXT    NOT NULL DEFAULT '',
  ky_thanh_toan      TEXT    NOT NULL DEFAULT '',
  -- MOI PARSING DOI_CHIEU CHO_DUYET DA_AP TU_CHOI FAILED
  trang_thai         TEXT    NOT NULL DEFAULT 'MOI',
  loi                TEXT,
  so_dong            INTEGER NOT NULL DEFAULT 0,
  tao_boi            INTEGER,
  tao_luc            TEXT    NOT NULL,
  duyet_boi          INTEGER,
  duyet_luc          TEXT,
  CHECK (trang_thai IN ('MOI','PARSING','DOI_CHIEU','CHO_DUYET','DA_AP','TU_CHOI','FAILED'))
);
CREATE INDEX IF NOT EXISTS ix_ds_dot_tenant ON ds_dot(tenant_id, trang_thai);

-- ---------- 11. Dòng bảng kê của hãng ----------
-- `van_tay_dong` = sha256 của dòng đã chuẩn hoá. UNIQUE(tenant_id, hang, ky, van_tay) là
-- CHỐT IDEMPOTENT Ở TẦNG CSDL: nạp lại đúng file đó thì câu INSERT ném IntegrityError, không
-- có khe hở nào giữa "kiểm xem có chưa" và "ghi vào" như phép kiểm trong mã.
CREATE TABLE IF NOT EXISTS ds_dong (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  dot_id        INTEGER NOT NULL REFERENCES ds_dot(id),
  tenant_id     INTEGER NOT NULL REFERENCES tenants(id),
  hang          TEXT    NOT NULL,
  stt           INTEGER NOT NULL,
  ma_van_don    TEXT,
  ma_don        TEXT,
  cod_hang_bao  INTEGER,
  phi_hang_bao  INTEGER,
  ky_thanh_toan TEXT    NOT NULL DEFAULT '',
  tho_json      TEXT    NOT NULL,                   -- dòng gốc, để tra lại
  van_tay_dong  TEXT    NOT NULL,
  don_id        INTEGER REFERENCES don_hang(id),    -- khớp được thì trỏ về đơn
  ket_qua       TEXT    NOT NULL DEFAULT 'CHUA_XET',
  UNIQUE (tenant_id, hang, ky_thanh_toan, van_tay_dong)
);
CREATE INDEX IF NOT EXISTS ix_ds_dong_dot ON ds_dong(dot_id, stt);

-- ---------- 12. Chênh lệch đối soát, PHÂN LOẠI RIÊNG từng loại ----------
CREATE TABLE IF NOT EXISTS ds_chenh_lech (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  dot_id     INTEGER NOT NULL REFERENCES ds_dot(id),
  tenant_id  INTEGER NOT NULL REFERENCES tenants(id),
  dong_id    INTEGER REFERENCES ds_dong(id),
  don_id     INTEGER REFERENCES don_hang(id),
  loai       TEXT    NOT NULL,                      -- xem doi_soat.LOAI_CHENH_LECH
  so_he      INTEGER,
  so_hang    INTEGER,
  lech_dong  INTEGER,
  chi_tiet   TEXT    NOT NULL DEFAULT '',
  xu_ly      TEXT    NOT NULL DEFAULT 'mo',         -- mo | da_xu | bo_qua
  xu_ly_boi  INTEGER,
  xu_ly_luc  TEXT,
  ghi_chu_xu_ly TEXT
);
CREATE INDEX IF NOT EXISTS ix_ds_cl_dot ON ds_chenh_lech(dot_id, loai);

-- ---------- 13. Ánh xạ cột theo HÃNG, có phiên bản ----------
-- Mỗi hãng một định dạng. Bản gốc nằm trong `doi_soat.ANH_XA_COT` (mã), bảng này là nơi
-- ghi đè theo tenant khi hãng đổi mẫu file mà chưa kịp sửa mã.
CREATE TABLE IF NOT EXISTS ds_anh_xa_cot (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id  INTEGER REFERENCES tenants(id),        -- NULL = áp cho mọi tenant
  hang       TEXT    NOT NULL,
  phien_ban  TEXT    NOT NULL,
  anh_xa_json TEXT   NOT NULL,                      -- {"ten cot trong file": "truong_chuan"}
  kich_hoat  INTEGER NOT NULL DEFAULT 1,
  tao_luc    TEXT    NOT NULL,
  UNIQUE (tenant_id, hang, phien_ban)
);
"""


class LoiTaiChinh(don_hang.LoiNghiepVu):
    """Lỗi nghiệp vụ tài chính. Kế thừa `LoiNghiepVu` để `server.py` map mã HTTP như cũ."""


# ============================================================================
# Bảo đảm bảng — chịu được CSDL CHƯA có migration v8
# ============================================================================
_da_tao_bang = False
_khoa_bang = threading.Lock()


def _dam_bao_bang():
    """Chạy `DDL_G07` một lần. Toàn bộ là `IF NOT EXISTS` nên gọi nhiều lần vô hại."""
    global _da_tao_bang
    if _da_tao_bang:
        return
    with _khoa_bang:
        if _da_tao_bang:
            return
        kn = csdl.mo()
        with csdl.khoa_ghi:
            kn.executescript(DDL_G07)
        _da_tao_bang = True


def quen_cache_bang():
    """Cho bộ thử: buộc chạy lại DDL sau khi đổi CSDL."""
    global _da_tao_bang
    _da_tao_bang = False


# ============================================================================
# TIỀN — một bộ lọc duy nhất trong cả hệ
# ============================================================================
def so_tien(gt, ten="số tiền"):
    """Số nguyên ĐỒNG. Gọi lại `don_hang._so_nguyen_tien` — KHÔNG viết bộ lọc thứ hai.

    `don_hang._so_nguyen_tien` ném `don_hang.LoiNghiepVu`; ở đây chuyển sang `LoiTaiChinh`
    cho thông điệp nhất quán nhưng KHÔNG đổi luật (vẫn chặn phần thập phân, không cắt cụt).
    """
    try:
        return don_hang._so_nguyen_tien(gt, ten)
    except don_hang.LoiNghiepVu as e:
        raise LoiTaiChinh(str(e), getattr(e, "ma", 400))


# ============================================================================
# QUYỀN — dùng quyền ĐÃ CÓ trong CSDL, không tự thêm quyền mới
# ============================================================================
# `app/quyen.py` do AG-01 sở hữu ở ĐỢT 2 nhưng KHÔNG nằm trong danh sách sở hữu đợt 3
# (SHARED_CONTRACTS §22), nên file này KHÔNG seed quyền mới. Mỗi việc tài chính khai một
# DÃY quyền chấp nhận được: ưu tiên quyền riêng `tenant.taichinh.*` (AG-00 seed sau), rơi về
# quyền hiện có nếu chưa seed. Dãy là danh sách TRẮNG có lý do: quên một dòng thì kết quả là
# CHẶN (thấy ngay), không phải CHO QUA (hỏng im lặng) — đúng ngoại lệ §12.2 đã nêu.
QUYEN_TC = {
    "xem":  ("tenant.taichinh.xem", "tenant.billing.xem"),
    "ghi":  ("tenant.taichinh.ghi", "tenant.don.duyet"),
    "duyet": ("tenant.taichinh.duyet", "tenant.don.duyet"),
}


def _can_quyen_tc(tenant_id, user_id, viec):
    """Cưỡng chế quyền NGAY TRONG tầng nghiệp vụ (nếp `don_hang._can_quyen`)."""
    ds = QUYEN_TC.get(viec)
    if not ds:
        raise LoiTaiChinh(f"việc tài chính lạ: {viec!r}", 500)
    vt = don_hang.vai_tro_trong_tenant(tenant_id, user_id)
    if not vt:
        raise LoiTaiChinh("người dùng không thuộc doanh nghiệp này", 403)
    for hd in ds:
        if quyen.co_quyen(vt, hd):
            return vt
    raise LoiTaiChinh(f"vai trò {vt} không có quyền tài chính '{viec}' (cần một trong {ds})", 403)


# ============================================================================
# NHẬT KÝ TÀI CHÍNH BẤT BIẾN — móc băm theo tenant
# ============================================================================
def _bam_dong(tenant_id, luc, hanh_dong, doi_tuong, chi_tiet, nguoi, bam_truoc):
    tho = "|".join(str(x) for x in (bam_truoc, tenant_id, luc, hanh_dong, doi_tuong,
                                    chi_tiet, "" if nguoi is None else nguoi))
    return hashlib.sha256(tho.encode("utf-8")).hexdigest()


def ghi_nhat_ky(tenant_id, hanh_dong, doi_tuong, chi_tiet="", nguoi=None):
    """Nối một dòng vào nhật ký bất biến. Băm dòng trước nằm trong băm dòng này.

    Nhờ móc băm, sửa/bỏ một dòng giữa sổ (dù có cách vòng qua trigger, ví dụ mở CSDL bằng
    sqlite3 CLI) làm `kiem_nhat_ky()` phát hiện ra — nghiệm thu không chỉ dựa vào trigger.
    """
    _dam_bao_bang()
    with csdl.khoa_ghi:
        truoc = csdl.mot("SELECT bam FROM tc_nhat_ky WHERE tenant_id=? ORDER BY id DESC LIMIT 1",
                         (tenant_id,))
        bam_truoc = truoc["bam"] if truoc else ""
        luc = csdl.bay_gio()
        bam = _bam_dong(tenant_id, luc, hanh_dong, doi_tuong, chi_tiet, nguoi, bam_truoc)
        return csdl.ghi(
            "INSERT INTO tc_nhat_ky (tenant_id, luc, hanh_dong, doi_tuong, chi_tiet, nguoi,"
            " bam_truoc, bam) VALUES (?,?,?,?,?,?,?,?)",
            (tenant_id, luc, hanh_dong, doi_tuong, chi_tiet, nguoi, bam_truoc, bam)).lastrowid


def kiem_nhat_ky(tenant_id) -> dict:
    """Kiểm toàn vẹn móc băm. Trả {ok, so_dong, dong_hong}. Không ném lỗi — để màn hình hiện."""
    _dam_bao_bang()
    truoc = ""
    hong = []
    ds = csdl.nhieu("SELECT * FROM tc_nhat_ky WHERE tenant_id=? ORDER BY id", (tenant_id,))
    for r in ds:
        mong = _bam_dong(r["tenant_id"], r["luc"], r["hanh_dong"], r["doi_tuong"],
                         r["chi_tiet"], r["nguoi"], truoc)
        if r["bam_truoc"] != truoc or r["bam"] != mong:
            hong.append(r["id"])
        truoc = r["bam"]
    return {"ok": not hong, "so_dong": len(ds), "dong_hong": hong}


# ============================================================================
# BÚT TOÁN — bất biến, và là nguồn duy nhất của công nợ
# ============================================================================
# loai bút toán → (sổ công nợ, dấu). `None` = không động công nợ (chỉ ghi nhận).
# Danh sách TRẮNG: `loai` lạ bị TỪ CHỐI, không ghi vào sổ với tác động không xác định.
TAC_DONG_CONG_NO = {
    # COD: hãng thu tiền hộ → hãng NỢ mình
    "cod_hang_bao_thu":     ("phai_thu", +1),
    "cod_hang_tra":         ("phai_thu", -1),
    "cod_dieu_chinh_tang":  ("phai_thu", +1),
    "cod_dieu_chinh_giam":  ("phai_thu", -1),
    "cod_mat":              ("phai_thu", -1),   # hãng làm mất tiền, xoá khỏi phải thu
    # Phí: hãng tính phí → mình NỢ hãng
    "phi_hang_tinh":        ("phai_tra", +1),
    "phi_hoan":             ("phai_tra", -1),
    "phi_dieu_chinh_tang":  ("phai_tra", +1),
    "phi_dieu_chinh_giam":  ("phai_tra", -1),
    "phi_da_tra":           ("phai_tra", -1),
    # Ghi nhận không động công nợ
    "phi_bao_gia":          None,               # hãng báo giá, chưa phát sinh nợ
    "phi_du_kien_thu_khach": None,              # số mình dự kiến thu của khách
    "cod_du_kien":          None,
}

CHIEU_THEO_DAU = {+1: "ghi_no", -1: "ghi_co"}
NGUON_HOP_LE = ("hang", "nguoi", "he_thong")


def _doi_tac_cua(tenant_id, carrier_account_id):
    """Đối tác của một bút toán: 'hang:<ma>' nếu gắn tài khoản hãng, else 'noi_bo'.

    CỐ Ý suy ra từ `carrier_account_id` thay vì thêm cột `doi_tac` — hợp đồng §17 đã khoá
    khung bút toán, và một cột dữ liệu lặp lại là một cột sẽ lệch với bảng gốc.
    """
    if not carrier_account_id:
        return "noi_bo"
    r = csdl.mot("SELECT hang FROM carrier_accounts WHERE id=? AND tenant_id=?",
                 (carrier_account_id, tenant_id))
    return f"hang:{r['hang']}" if r else "noi_bo"


def _cap_nhat_cong_no(tenant_id, so, doi_tac, delta):
    """Cộng `delta` vào số dư. Một câu UPSERT — không đọc-rồi-ghi."""
    csdl.ghi("INSERT INTO tc_cong_no (tenant_id, so, doi_tac, so_du_dong, cap_nhat_luc)"
             " VALUES (?,?,?,?,?) ON CONFLICT(tenant_id, so, doi_tac) DO UPDATE SET"
             " so_du_dong = so_du_dong + excluded.so_du_dong, cap_nhat_luc = excluded.cap_nhat_luc",
             (tenant_id, so, doi_tac, delta, csdl.bay_gio()))


def ghi_but_toan(tenant_id, loai, so_tien_dong, nguon, can_cu, tao_boi=None,
                 don_id=None, carrier_account_id=None, batch_id=None, dao_cua=None):
    """Ghi MỘT bút toán + cập nhật công nợ trong CÙNG một giao dịch (`csdl.giao_dich`).

    `so_tien_dong` phải >= 0 — hướng nằm ở `loai` (xem `TAC_DONG_CONG_NO`). Truyền số âm là
    lỗi của người gọi, không phải cách diễn đạt thứ hai: hai cách diễn đạt cùng một việc là
    chỗ sinh ra bút toán ngược dấu mà không ai thấy.
    """
    _dam_bao_bang()
    if loai not in TAC_DONG_CONG_NO:
        raise LoiTaiChinh(f"loại bút toán không khai báo: {loai!r} "
                          f"(hợp lệ: {sorted(TAC_DONG_CONG_NO)})", 400)
    if nguon not in NGUON_HOP_LE:
        raise LoiTaiChinh(f"nguồn phải thuộc {NGUON_HOP_LE}, nhận {nguon!r}")
    st = so_tien(so_tien_dong, "số tiền bút toán")
    if st < 0:
        raise LoiTaiChinh("số tiền bút toán phải >= 0; hướng nằm ở `loai`, không ở dấu")
    if not str(can_cu or "").strip():
        raise LoiTaiChinh("bút toán phải có căn cứ (ai · lúc nào · vì sao)")
    if don_id is not None and not don_hang.lay_don(tenant_id, don_id):
        raise LoiTaiChinh("đơn không thuộc doanh nghiệp này", 404)

    td = TAC_DONG_CONG_NO[loai]
    chieu = CHIEU_THEO_DAU[td[1]] if td else "ghi_no"
    # `giao_dich()` chứ không `khoa_ghi` trần: khoá chỉ chặn hai thread giẫm nhau, nó KHÔNG
    # làm hai câu dưới đây thành một đơn vị. Trước 15/10/2026 chỗ này dùng khoá trần và
    # docstring vẫn ghi "CÙNG một transaction" — đo ra thì không phải: ép bước công nợ hỏng,
    # bút toán 777.000đ vẫn vào sổ còn công nợ đứng yên, lệch đúng 777.000đ.
    with csdl.giao_dich():
        bt = csdl.ghi(
            "INSERT INTO tc_but_toan (tenant_id, loai, don_id, carrier_account_id, so_tien_dong,"
            " chieu, nguon, can_cu, tao_boi, tao_luc, batch_id, dao_cua)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (tenant_id, loai, don_id, carrier_account_id, st, chieu, nguon, can_cu, tao_boi,
             csdl.bay_gio(), batch_id, dao_cua)).lastrowid
        if td:
            _cap_nhat_cong_no(tenant_id, td[0], _doi_tac_cua(tenant_id, carrier_account_id),
                              td[1] * st)
    return bt


# Bút toán nào ĐẢO bút toán nào. Danh sách TRẮNG — loại không có cặp đảo thì từ chối,
# chứ không tự suy ra một loại ngược dấu chưa ai nghĩ tới.
CAP_DAO = {
    "cod_hang_bao_thu": "cod_dieu_chinh_giam",
    "cod_hang_tra": "cod_dieu_chinh_tang",
    "cod_dieu_chinh_tang": "cod_dieu_chinh_giam",
    "cod_dieu_chinh_giam": "cod_dieu_chinh_tang",
    "cod_mat": "cod_dieu_chinh_tang",
    "phi_hang_tinh": "phi_dieu_chinh_giam",
    "phi_hoan": "phi_dieu_chinh_tang",
    "phi_dieu_chinh_tang": "phi_dieu_chinh_giam",
    "phi_dieu_chinh_giam": "phi_dieu_chinh_tang",
    "phi_da_tra": "phi_dieu_chinh_tang",
}


def dao_but_toan(tenant_id, but_toan_id, ly_do, tao_boi=None):
    """Sửa một bút toán sai = ghi bút toán ĐẢO. Không `UPDATE`, không `DELETE` (§17).

    `UNIQUE(dao_cua)` chặn đảo hai lần cùng một dòng — đảo hai lần là cộng ngược hai lần.
    """
    _dam_bao_bang()
    goc = csdl.mot("SELECT * FROM tc_but_toan WHERE id=? AND tenant_id=?", (but_toan_id, tenant_id))
    if not goc:
        raise LoiTaiChinh("không có bút toán này trong doanh nghiệp", 404)
    if goc["dao_cua"]:
        raise LoiTaiChinh("không đảo một bút toán đảo — hãy ghi bút toán mới", 409)
    loai_dao = CAP_DAO.get(goc["loai"])
    if not loai_dao:
        raise LoiTaiChinh(f"loại {goc['loai']!r} không khai cặp đảo — bàn giao người xử", 400)
    if not str(ly_do or "").strip():
        raise LoiTaiChinh("đảo bút toán phải có lý do")
    try:
        bt = ghi_but_toan(tenant_id, loai_dao, goc["so_tien_dong"], "nguoi",
                          f"ĐẢO bút toán #{but_toan_id} ({goc['loai']}): {ly_do}",
                          tao_boi=tao_boi, don_id=goc["don_id"],
                          carrier_account_id=goc["carrier_account_id"],
                          batch_id=goc["batch_id"], dao_cua=but_toan_id)
    except Exception as e:
        if "ux_tc_bt_dao" in str(e) or "UNIQUE" in str(e).upper():
            raise LoiTaiChinh(f"bút toán #{but_toan_id} đã được đảo một lần rồi", 409)
        raise
    ghi_nhat_ky(tenant_id, "dao_but_toan", f"tc_but_toan:{but_toan_id}",
                f"đảo bằng #{bt}: {ly_do}", tao_boi)
    return bt


def cong_no(tenant_id) -> dict:
    """Số dư công nợ đang lưu (bảng tổng hợp)."""
    _dam_bao_bang()
    ra = {"phai_thu": {}, "phai_tra": {}}
    for r in csdl.nhieu("SELECT so, doi_tac, so_du_dong FROM tc_cong_no WHERE tenant_id=?"
                        " ORDER BY so, doi_tac", (tenant_id,)):
        ra[r["so"]][r["doi_tac"]] = r["so_du_dong"]
    ra["tong_phai_thu"] = sum(ra["phai_thu"].values())
    ra["tong_phai_tra"] = sum(ra["phai_tra"].values())
    return ra


def tinh_lai_cong_no(tenant_id) -> dict:
    """Dựng lại công nợ TỪ ĐẦU bằng `tc_but_toan`. Dùng để đối chiếu với bảng tổng hợp.

    Có hàm này thì câu "công nợ đúng" là một phép ĐO, không phải một lời tin. Ca thử so hai
    con số sau mỗi luồng — lệch là bộ thử hỏng.
    """
    _dam_bao_bang()
    ra = {"phai_thu": {}, "phai_tra": {}}
    for r in csdl.nhieu("SELECT loai, so_tien_dong, carrier_account_id FROM tc_but_toan"
                        " WHERE tenant_id=? ORDER BY id", (tenant_id,)):
        td = TAC_DONG_CONG_NO.get(r["loai"])
        if not td:
            continue
        dt = _doi_tac_cua(tenant_id, r["carrier_account_id"])
        ra[td[0]][dt] = ra[td[0]].get(dt, 0) + td[1] * r["so_tien_dong"]
    ra["tong_phai_thu"] = sum(ra["phai_thu"].values())
    ra["tong_phai_tra"] = sum(ra["phai_tra"].values())
    return ra


# ============================================================================
# COD — sáu trạng thái, MỘT hàm chuyển, bảng chuyển hợp lệ
# ============================================================================
TRANG_THAI_COD = ("COD_EXPECTED", "COD_COLLECTED", "COD_RECONCILED", "COD_SETTLED",
                  "COD_DISPUTED", "COD_ADJUSTED")

# Danh sách TRẮNG có lý do (§12.2 nêu đúng ngoại lệ này): thiếu một dòng thì CHẶN một chuyển
# hợp lệ — mất tiện, thấy ngay. Dùng danh sách đen là mở cửa cho mọi chuyển chưa nghĩ tới,
# và ở sổ tiền thì "chưa nghĩ tới" nghĩa là doanh thu không có thật.
CHUYEN_COD = {
    "COD_EXPECTED":   {"COD_COLLECTED", "COD_DISPUTED", "COD_ADJUSTED"},
    "COD_COLLECTED":  {"COD_RECONCILED", "COD_DISPUTED", "COD_ADJUSTED"},
    "COD_RECONCILED": {"COD_SETTLED", "COD_DISPUTED", "COD_ADJUSTED"},
    "COD_SETTLED":    {"COD_DISPUTED", "COD_ADJUSTED"},   # phát hiện sai sau khi đã trả tiền
    "COD_DISPUTED":   {"COD_RECONCILED", "COD_ADJUSTED", "COD_COLLECTED"},
    "COD_ADJUSTED":   {"COD_RECONCILED", "COD_SETTLED", "COD_DISPUTED"},
}

# Bút toán kèm theo mỗi chuyển. None = chuyển trạng thái không sinh dòng tiền.
BUT_TOAN_THEO_CHUYEN = {
    ("COD_EXPECTED", "COD_COLLECTED"): "cod_hang_bao_thu",
    ("COD_DISPUTED", "COD_COLLECTED"): "cod_hang_bao_thu",
}


def mo_so_cod(tenant_id, don_id, so_tien_du_kien=None, tao_boi=None):
    """Mở sổ COD cho một đơn ở `COD_EXPECTED`. Idempotent: gọi lại trả dòng đang có.

    `COD_EXPECTED` CỐ Ý không sinh bút toán: chưa ai thu đồng nào, ghi vào sổ nợ là tạo ra
    một khoản phải thu không có thật.
    """
    _dam_bao_bang()
    don = don_hang.lay_don(tenant_id, don_id)
    if not don:
        raise LoiTaiChinh("không có đơn này trong doanh nghiệp", 404)
    st = so_tien(don["cod"] if so_tien_du_kien is None else so_tien_du_kien, "COD dự kiến")
    if st < 0:
        raise LoiTaiChinh("COD dự kiến không được âm")
    luc = csdl.bay_gio()
    with csdl.khoa_ghi:
        csdl.ghi("INSERT OR IGNORE INTO tc_cod (don_id, tenant_id, carrier_account_id,"
                 " so_tien_du_kien, trang_thai, tao_luc, cap_nhat_luc)"
                 " VALUES (?,?,?,?, 'COD_EXPECTED', ?, ?)",
                 (don_id, tenant_id, don["carrier_account_id"], st, luc, luc))
    return cod_cua_don(tenant_id, don_id)


def cod_cua_don(tenant_id, don_id):
    _dam_bao_bang()
    return csdl.mot("SELECT * FROM tc_cod WHERE don_id=? AND tenant_id=?", (don_id, tenant_id))


def chuyen_cod(tenant_id, don_id, den, nguon, can_cu, nguoi=None, so_tien_hang_bao=None,
               ly_do_tranh_chap=None, carrier_account_id=None, batch_id=None,
               user_id=None, kiem_quyen=False):
    """MỘT cửa duy nhất để đổi trạng thái COD (hợp đồng §18).

    Không có đường nào khác trong hệ được `UPDATE tc_cod SET trang_thai=...`. Lý do: trạng
    thái COD quyết định số tiền báo lên, nên mỗi lối đi riêng là một lối có thể quên ghi bút
    toán, quên kiểm bảng chuyển, hoặc quên cách ly tenant.

    Đổi trạng thái bằng MỘT câu `UPDATE ... WHERE trang_thai=<cũ>` rồi xét `rowcount`: hai
    lượt song song thì đúng một lượt thắng. KHÔNG đọc-rồi-ghi.

    CHÚ Ý: `COD_SETTLED` KHÔNG đi qua đây — nó chỉ đến từ `ghi_nhan_thanh_toan()`, tức phải
    có tiền thật của một đợt thanh toán. Đó là chốt chặn của luật "giao thành công ≠ đã trả
    tiền" (§18): không có đường nào từ trạng thái giao sang settled.
    """
    _dam_bao_bang()
    if den not in TRANG_THAI_COD:
        raise LoiTaiChinh(f"trạng thái COD lạ: {den!r} (hợp lệ: {TRANG_THAI_COD})")
    if den == "COD_SETTLED":
        raise LoiTaiChinh("COD_SETTLED chỉ đến từ một đợt thanh toán có tiền thật "
                          "— gọi ghi_nhan_thanh_toan()", 409)
    if kiem_quyen:
        _can_quyen_tc(tenant_id, user_id if user_id is not None else nguoi, "ghi")
    if not str(can_cu or "").strip():
        raise LoiTaiChinh("chuyển trạng thái COD phải có căn cứ")

    cur = cod_cua_don(tenant_id, don_id)
    if not cur:
        cur = mo_so_cod(tenant_id, don_id, tao_boi=nguoi)
    tu = cur["trang_thai"]
    if den not in CHUYEN_COD.get(tu, set()):
        raise LoiTaiChinh(f"không được chuyển COD {tu} → {den} "
                          f"(hợp lệ: {sorted(CHUYEN_COD.get(tu, set())) or 'không còn gì'})", 409)

    stb = None if so_tien_hang_bao is None else so_tien(so_tien_hang_bao, "COD hãng báo")
    if stb is not None and stb < 0:
        raise LoiTaiChinh("COD hãng báo không được âm")
    ca_id = carrier_account_id or cur["carrier_account_id"]

    with csdl.khoa_ghi:
        dat = ["trang_thai=?", "cap_nhat_luc=?"]
        ts = [den, csdl.bay_gio()]
        if stb is not None:
            dat.append("so_tien_hang_bao=?"); ts.append(stb)
        if den == "COD_RECONCILED":
            dat.append("so_tien_doi_soat=?")
            ts.append(stb if stb is not None else
                      (cur["so_tien_hang_bao"] if cur["so_tien_hang_bao"] is not None
                       else cur["so_tien_du_kien"]))
        if ly_do_tranh_chap is not None:
            dat.append("ly_do_tranh_chap=?"); ts.append(ly_do_tranh_chap)
        if ca_id:
            dat.append("carrier_account_id=?"); ts.append(ca_id)
        ts += [don_id, tenant_id, tu]
        con = csdl.ghi(f"UPDATE tc_cod SET {', '.join(dat)}"
                       f" WHERE don_id=? AND tenant_id=? AND trang_thai=?", ts)
        if con.rowcount != 1:
            raise LoiTaiChinh(f"COD của đơn {don_id} vừa được một lượt khác đổi "
                              f"(không còn ở {tu}) — không đổi lần hai", 409)
        csdl.ghi("INSERT INTO tc_cod_chuyen (tenant_id, don_id, tu, den, nguon, can_cu, nguoi, luc)"
                 " VALUES (?,?,?,?,?,?,?,?)",
                 (tenant_id, don_id, tu, den, nguon, can_cu, nguoi, csdl.bay_gio()))

    loai_bt = BUT_TOAN_THEO_CHUYEN.get((tu, den))
    if loai_bt:
        tien_bt = stb if stb is not None else cur["so_tien_du_kien"]
        ghi_but_toan(tenant_id, loai_bt, tien_bt, nguon, can_cu, tao_boi=nguoi,
                     don_id=don_id, carrier_account_id=ca_id, batch_id=batch_id)
    ghi_nhat_ky(tenant_id, "chuyen_cod", f"don:{don_id}", f"{tu} → {den}: {can_cu}", nguoi)
    return cod_cua_don(tenant_id, don_id)


def tong_hop_cod(tenant_id) -> dict:
    """Bảng COD của tenant: dự kiến · hãng báo đã thu · đã đối soát · đã thanh toán · còn chờ
    · chênh lệch · hoàn/điều chỉnh. Mọi số là `INTEGER` đồng, lấy bằng `SUM` của CSDL."""
    _dam_bao_bang()
    r = csdl.mot(
        "SELECT COUNT(*) so_don,"
        " COALESCE(SUM(so_tien_du_kien),0) du_kien,"
        " COALESCE(SUM(CASE WHEN so_tien_hang_bao IS NOT NULL THEN so_tien_hang_bao ELSE 0 END),0) hang_bao,"
        " COALESCE(SUM(CASE WHEN trang_thai IN ('COD_RECONCILED','COD_SETTLED')"
        "   THEN COALESCE(so_tien_doi_soat,0) ELSE 0 END),0) da_doi_soat,"
        " COALESCE(SUM(so_tien_da_tt),0) da_thanh_toan"
        " FROM tc_cod WHERE tenant_id=?", (tenant_id,))
    theo_tt = {t: 0 for t in TRANG_THAI_COD}
    tien_tt = {t: 0 for t in TRANG_THAI_COD}
    for x in csdl.nhieu("SELECT trang_thai, COUNT(*) c, COALESCE(SUM(so_tien_du_kien),0) t"
                        " FROM tc_cod WHERE tenant_id=? GROUP BY trang_thai", (tenant_id,)):
        theo_tt[x["trang_thai"]] = x["c"]
        tien_tt[x["trang_thai"]] = x["t"]
    lech = csdl.mot(
        "SELECT COALESCE(SUM(so_tien_hang_bao - so_tien_du_kien),0) lech, COUNT(*) so_don"
        " FROM tc_cod WHERE tenant_id=? AND so_tien_hang_bao IS NOT NULL"
        " AND so_tien_hang_bao <> so_tien_du_kien", (tenant_id,))
    dc = csdl.mot("SELECT COALESCE(SUM(so_tien_dong),0) t, COUNT(*) c FROM tc_dieu_chinh"
                  " WHERE tenant_id=? AND loai='cod'", (tenant_id,))
    return {
        "so_don": r["so_don"],
        "du_kien": r["du_kien"],
        "hang_bao_da_thu": r["hang_bao"],
        "da_doi_soat": r["da_doi_soat"],
        "da_thanh_toan": r["da_thanh_toan"],
        # Còn chờ = hãng đã báo thu mà chưa trả về. Không lấy `du_kien` làm gốc: đơn chưa giao
        # thì chưa ai thu, cộng vào "còn chờ hãng trả" là báo một khoản không tồn tại.
        "con_cho": r["hang_bao"] - r["da_thanh_toan"],
        "chenh_lech_hang_bao_vs_du_kien": lech["lech"],
        "so_don_chenh_lech": lech["so_don"],
        "hoan_dieu_chinh": dc["t"],
        "so_lan_dieu_chinh": dc["c"],
        "theo_trang_thai": theo_tt,
        "tien_theo_trang_thai": tien_tt,
    }


# ============================================================================
# ĐỢT THANH TOÁN CỦA HÃNG — cửa DUY NHẤT dẫn tới COD_SETTLED
# ============================================================================
def tao_dot_thanh_toan(tenant_id, user_id, hang, ma_dot, so_tien_hang_bao=0,
                       carrier_account_id=None, ky_tu=None, ky_den=None, kiem_quyen=True):
    """Tạo đợt thanh toán. `UNIQUE(tenant_id, hang, ma_dot)` chặn nạp trùng ở tầng CSDL."""
    _dam_bao_bang()
    if kiem_quyen:
        _can_quyen_tc(tenant_id, user_id, "ghi")
    if not str(ma_dot or "").strip():
        raise LoiTaiChinh("đợt thanh toán phải có mã đợt của hãng")
    st = so_tien(so_tien_hang_bao, "số tiền đợt")
    try:
        did = csdl.ghi("INSERT INTO tc_dot_tt (tenant_id, hang, carrier_account_id, ma_dot,"
                       " ky_tu, ky_den, so_tien_hang_bao, tao_boi, tao_luc)"
                       " VALUES (?,?,?,?,?,?,?,?,?)",
                       (tenant_id, hang, carrier_account_id, ma_dot, ky_tu, ky_den, st,
                        user_id, csdl.bay_gio())).lastrowid
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            raise LoiTaiChinh(f"đợt thanh toán {ma_dot!r} của hãng {hang} đã có "
                              f"— không tạo lần hai", 409)
        raise
    ghi_nhat_ky(tenant_id, "tao_dot_thanh_toan", f"tc_dot_tt:{did}",
                f"hãng {hang} mã {ma_dot} số tiền {st}", user_id)
    return did


def ghi_nhan_thanh_toan(tenant_id, user_id, dot_id, don_id, so_tien_dong, kiem_quyen=True):
    """Hãng TRẢ TIỀN cho một đơn. Đây là cửa DUY NHẤT dẫn tới `COD_SETTLED`.

    Ba chốt, cả ba ở tầng CSDL chứ không phải phép kiểm trong mã:
      1) `UNIQUE(dot_id, don_id)` — một đơn chỉ nhận tiền MỘT lần trong MỘT đợt (chặn
         thanh toán trùng do bấm hai lần hoặc worker thử lại).
      2) `UPDATE ... WHERE so_tien_da_tt + ? <= <số phải trả>` — tổng đã trả không bao giờ
         vượt số hãng báo thu. Điều kiện nằm trong `WHERE` nên không có khe hở đồng thời.
      3) Chỉ `COD_SETTLED` khi đã trả ĐỦ. Trả thiếu thì giữ `COD_RECONCILED` và cộng dồn —
         đó là thanh toán một phần, không phải đã tất toán.

    Đơn phải ở `COD_RECONCILED` hoặc `COD_ADJUSTED` (đã đối soát / đã chốt lại số). Đơn mới
    `COD_COLLECTED` mà nhận tiền là áp số của hãng vào sổ khi chưa ai duyệt đối soát.
    """
    _dam_bao_bang()
    if kiem_quyen:
        _can_quyen_tc(tenant_id, user_id, "duyet")
    dot = csdl.mot("SELECT * FROM tc_dot_tt WHERE id=? AND tenant_id=?", (dot_id, tenant_id))
    if not dot:
        raise LoiTaiChinh("không có đợt thanh toán này trong doanh nghiệp", 404)
    if dot["trang_thai"] != "MOI":
        raise LoiTaiChinh(f"đợt thanh toán đang ở {dot['trang_thai']}, không ghi nhận thêm", 409)
    st = so_tien(so_tien_dong, "số tiền thanh toán")
    if st <= 0:
        raise LoiTaiChinh("số tiền thanh toán phải > 0")
    c = cod_cua_don(tenant_id, don_id)
    if not c:
        raise LoiTaiChinh("đơn chưa có sổ COD", 404)
    if c["trang_thai"] not in ("COD_RECONCILED", "COD_ADJUSTED"):
        raise LoiTaiChinh(
            f"COD của đơn đang ở {c['trang_thai']} — phải ĐỐI SOÁT xong mới nhận tiền. "
            f"Giao hàng thành công KHÔNG làm COD thành đã thanh toán (hợp đồng §18).", 409)
    phai_tra = c["so_tien_doi_soat"] if c["so_tien_doi_soat"] is not None else (
        c["so_tien_hang_bao"] if c["so_tien_hang_bao"] is not None else c["so_tien_du_kien"])

    # MỘT giao dịch cho CẢ SÁU bước: dòng đợt · cộng đã-trả · chuyển COD_SETTLED · dòng
    # chuyển trạng thái · bút toán · nhật ký. Trước 15/10/2026 đây là `khoa_ghi` trần, nên
    # mỗi `csdl.ghi()` tự commit. Đo được hậu quả: đơn COD 100.000 đã trả 50.000, đợt mới trả
    # 90.000 → câu 2 từ chối đúng (50+90 > 100), nhưng câu 1 ĐÃ COMMIT: tc_dot_tt_dong mang
    # một dòng 90.000 MỒ CÔI, tổng đợt 140.000 trong khi tc_cod ghi đã trả 50.000. Tệ hơn:
    # UNIQUE(dot_id, don_id) chặn làm lại, nên đợt đó kẹt vĩnh viễn, phải sửa tay dưới CSDL.
    with csdl.giao_dich():
        try:
            csdl.ghi("INSERT INTO tc_dot_tt_dong (dot_id, tenant_id, don_id, so_tien_dong)"
                     " VALUES (?,?,?,?)", (dot_id, tenant_id, don_id, st))
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                raise LoiTaiChinh(f"đơn {don_id} đã được ghi nhận thanh toán trong đợt này "
                                  f"— không cộng tiền lần hai", 409)
            raise
        con = csdl.ghi("UPDATE tc_cod SET so_tien_da_tt = so_tien_da_tt + ?, cap_nhat_luc=?"
                       " WHERE don_id=? AND tenant_id=? AND so_tien_da_tt + ? <= ?",
                       (st, csdl.bay_gio(), don_id, tenant_id, st, phai_tra))
        if con.rowcount != 1:
            raise LoiTaiChinh(
                f"trả {st} làm tổng đã trả vượt số phải trả {phai_tra} "
                f"(đã trả {c['so_tien_da_tt']}) — từ chối", 409)
        moi = csdl.mot("SELECT so_tien_da_tt, trang_thai FROM tc_cod WHERE don_id=? AND tenant_id=?",
                       (don_id, tenant_id))
        du = moi["so_tien_da_tt"] >= phai_tra
        if du:
            csdl.ghi("UPDATE tc_cod SET trang_thai='COD_SETTLED', cap_nhat_luc=?"
                     " WHERE don_id=? AND tenant_id=? AND trang_thai IN ('COD_RECONCILED','COD_ADJUSTED')",
                     (csdl.bay_gio(), don_id, tenant_id))
            csdl.ghi("INSERT INTO tc_cod_chuyen (tenant_id, don_id, tu, den, nguon, can_cu, nguoi, luc)"
                     " VALUES (?,?,?,?,?,?,?,?)",
                     (tenant_id, don_id, moi["trang_thai"], "COD_SETTLED", "hang",
                      f"đợt thanh toán #{dot_id} trả đủ {phai_tra}", user_id, csdl.bay_gio()))

        # Bút toán và nhật ký NẰM TRONG cùng giao dịch. Để ngoài thì có ca: tiền đã áp vào
        # tc_cod mà sổ cái không có bút toán nào — và bút toán thì không ghi bù được bằng
        # UPDATE (trigger bất biến), nên chênh đó nằm lại vĩnh viễn.
        # `giao_dich()` lồng nhau được (SAVEPOINT), nên ghi_but_toan gọi trong đây vẫn đúng.
        ghi_but_toan(tenant_id, "cod_hang_tra", st, "hang",
                     f"đợt thanh toán #{dot_id} ({dot['ma_dot']}) trả {st} cho đơn {don_id}",
                     tao_boi=user_id, don_id=don_id,
                     carrier_account_id=c["carrier_account_id"] or dot["carrier_account_id"],
                     batch_id=dot_id)
        ghi_nhat_ky(tenant_id, "ghi_nhan_thanh_toan", f"don:{don_id}",
                    f"đợt #{dot_id} trả {st}; đủ={du}", user_id)
    return {"da_tra": moi["so_tien_da_tt"], "phai_tra": phai_tra, "du": du,
             "con_lai": phai_tra - moi["so_tien_da_tt"],
             "trang_thai": "COD_SETTLED" if du else moi["trang_thai"]}


def dong_dot_thanh_toan(tenant_id, user_id, dot_id, kiem_quyen=True):
    """Chốt đợt: `UPDATE ... WHERE trang_thai='MOI'` + rowcount — hai lượt thì một thắng."""
    _dam_bao_bang()
    if kiem_quyen:
        _can_quyen_tc(tenant_id, user_id, "duyet")
    con = csdl.ghi("UPDATE tc_dot_tt SET trang_thai='DA_AP', ap_luc=?"
                   " WHERE id=? AND tenant_id=? AND trang_thai='MOI'",
                   (csdl.bay_gio(), dot_id, tenant_id))
    if con.rowcount != 1:
        raise LoiTaiChinh("đợt thanh toán không còn ở trạng thái MOI — không chốt lần hai", 409)
    ghi_nhat_ky(tenant_id, "dong_dot_thanh_toan", f"tc_dot_tt:{dot_id}", "", user_id)
    return True


# ============================================================================
# PHÍ VẬN CHUYỂN — mỗi khoản có LOẠI · NGUỒN · THỜI ĐIỂM GHI NHẬN
# ============================================================================
# Loại phí → loại bút toán tương ứng. `None` = chỉ ghi nhận, không động công nợ.
LOAI_PHI = {
    "bao_gia":           "phi_bao_gia",            # hãng báo giá trước khi gửi
    "du_kien_thu_khach": "phi_du_kien_thu_khach",  # số mình dự kiến thu của khách
    "thuc_te_hang":      "phi_hang_tinh",          # phí hãng tính thật → phát sinh nợ
    "phu_phi":           "phi_hang_tinh",
    "hoan":              "phi_hoan",               # phí hãng hoàn lại
    "dieu_chinh_tang":   "phi_dieu_chinh_tang",
    "dieu_chinh_giam":   "phi_dieu_chinh_giam",
}


def ghi_phi(tenant_id, don_id, loai, so_tien_dong, nguon, can_cu, tao_boi=None,
            carrier_account_id=None, batch_id=None, ghi_nhan_luc=None):
    """Ghi một khoản phí. `so_tien_dong` luôn >= 0; hướng nằm ở `loai`.

    `ghi_nhan_luc` cho phép truyền mốc của hãng (bảng kê ghi ngày khác ngày mình nạp file).
    Không có thì lấy giờ hệ — và `nguon` nói rõ số đó do ai đưa ra.
    """
    _dam_bao_bang()
    if loai not in LOAI_PHI:
        raise LoiTaiChinh(f"loại phí không khai báo: {loai!r} (hợp lệ: {sorted(LOAI_PHI)})")
    if nguon not in NGUON_HOP_LE:
        raise LoiTaiChinh(f"nguồn phí phải thuộc {NGUON_HOP_LE}, nhận {nguon!r}")
    st = so_tien(so_tien_dong, f"phí {loai}")
    if st < 0:
        raise LoiTaiChinh("số tiền phí phải >= 0; giảm thì dùng loai='dieu_chinh_giam'/'hoan'")
    if not str(can_cu or "").strip():
        raise LoiTaiChinh("khoản phí phải có căn cứ")
    if don_id is not None:
        don = don_hang.lay_don(tenant_id, don_id)
        if not don:
            raise LoiTaiChinh("không có đơn này trong doanh nghiệp", 404)
        carrier_account_id = carrier_account_id or don["carrier_account_id"]
    loai_bt = LOAI_PHI[loai]
    bt = ghi_but_toan(tenant_id, loai_bt, st, nguon, can_cu, tao_boi=tao_boi, don_id=don_id,
                      carrier_account_id=carrier_account_id, batch_id=batch_id)
    # Dấu lưu trong `tc_phi` theo hướng kinh tế, để cộng tổng đọc thẳng được.
    dau = -1 if loai in ("hoan", "dieu_chinh_giam") else 1
    pid = csdl.ghi("INSERT INTO tc_phi (tenant_id, don_id, carrier_account_id, loai, so_tien_dong,"
                   " nguon, can_cu, ghi_nhan_luc, tao_boi, but_toan_id, batch_id)"
                   " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (tenant_id, don_id, carrier_account_id, loai, dau * st, nguon, can_cu,
                    ghi_nhan_luc or csdl.bay_gio(), tao_boi, bt, batch_id)).lastrowid
    return {"phi_id": pid, "but_toan_id": bt}


def phi_cua_don(tenant_id, don_id) -> dict:
    """Mọi khoản phí của một đơn + chênh lệch giữa số hãng tính và số đã báo giá/thu khách."""
    _dam_bao_bang()
    ds = csdl.nhieu("SELECT * FROM tc_phi WHERE tenant_id=? AND don_id=? ORDER BY id",
                    (tenant_id, don_id))
    tong = {k: 0 for k in LOAI_PHI}
    for r in ds:
        tong[r["loai"]] += r["so_tien_dong"]
    thuc_te = tong["thuc_te_hang"] + tong["phu_phi"] + tong["hoan"] \
        + tong["dieu_chinh_tang"] + tong["dieu_chinh_giam"]
    return {
        "khoan": [dict(r) for r in ds],
        "tong_theo_loai": tong,
        "phi_thuc_te": thuc_te,
        # Hai chênh lệch KHÁC NHAU, cố ý không gộp: một cái là hãng tính khác báo giá (mình
        # bị tính thêm), một cái là mình thu khách khác phí thật (lãi/lỗ trên đơn).
        "lech_so_bao_gia": thuc_te - tong["bao_gia"],
        "lech_so_thu_khach": tong["du_kien_thu_khach"] - thuc_te,
    }


def tong_hop_phi(tenant_id) -> dict:
    _dam_bao_bang()
    ra = {k: 0 for k in LOAI_PHI}
    for r in csdl.nhieu("SELECT loai, COALESCE(SUM(so_tien_dong),0) t FROM tc_phi"
                        " WHERE tenant_id=? GROUP BY loai", (tenant_id,)):
        ra[r["loai"]] = r["t"]
    ra["phi_thuc_te"] = (ra["thuc_te_hang"] + ra["phu_phi"] + ra["hoan"]
                         + ra["dieu_chinh_tang"] + ra["dieu_chinh_giam"])
    ra["lech_so_bao_gia"] = ra["phi_thuc_te"] - ra["bao_gia"]
    ra["lech_so_thu_khach"] = ra["du_kien_thu_khach"] - ra["phi_thuc_te"]
    return ra


# ============================================================================
# ĐIỀU CHỈNH — lý do + người + lịch sử, cả ba BẮT BUỘC
# ============================================================================
def dieu_chinh(tenant_id, user_id, loai, so_tien_dong, ly_do, don_id=None, kiem_quyen=True):
    """Điều chỉnh tay. `so_tien_dong` ÂM = giảm. Không có lý do thì không có điều chỉnh.

    Điều chỉnh KHÔNG sửa bút toán cũ — nó ghi bút toán MỚI ngược chiều (§17). Nhờ vậy nhìn
    lại vẫn thấy cả số sai lẫn số sửa, và dựng lại được chuỗi sự việc.
    """
    _dam_bao_bang()
    if kiem_quyen:
        _can_quyen_tc(tenant_id, user_id, "duyet")
    if loai not in ("cod", "phi"):
        raise LoiTaiChinh("loại điều chỉnh phải là 'cod' hoặc 'phi'")
    if not str(ly_do or "").strip():
        raise LoiTaiChinh("điều chỉnh tài chính PHẢI có lý do")
    st = so_tien(so_tien_dong, "số tiền điều chỉnh")
    if st == 0:
        raise LoiTaiChinh("điều chỉnh 0 đồng không có nghĩa gì")
    if not csdl.mot("SELECT 1 x FROM users WHERE id=?", (user_id,)):
        raise LoiTaiChinh("người điều chỉnh không tồn tại", 400)
    ca_id = None
    if don_id is not None:
        don = don_hang.lay_don(tenant_id, don_id)
        if not don:
            raise LoiTaiChinh("không có đơn này trong doanh nghiệp", 404)
        ca_id = don["carrier_account_id"]
    loai_bt = {("cod", 1): "cod_dieu_chinh_tang", ("cod", -1): "cod_dieu_chinh_giam",
               ("phi", 1): "phi_dieu_chinh_tang", ("phi", -1): "phi_dieu_chinh_giam"}[
        (loai, 1 if st > 0 else -1)]
    bt = ghi_but_toan(tenant_id, loai_bt, abs(st), "nguoi", f"điều chỉnh tay: {ly_do}",
                      tao_boi=user_id, don_id=don_id, carrier_account_id=ca_id)
    did = csdl.ghi("INSERT INTO tc_dieu_chinh (tenant_id, don_id, loai, so_tien_dong, ly_do,"
                   " nguoi, but_toan_id, luc) VALUES (?,?,?,?,?,?,?,?)",
                   (tenant_id, don_id, loai, st, ly_do, user_id, bt, csdl.bay_gio())).lastrowid
    if loai == "phi":
        csdl.ghi("INSERT INTO tc_phi (tenant_id, don_id, carrier_account_id, loai, so_tien_dong,"
                 " nguon, can_cu, ghi_nhan_luc, tao_boi, but_toan_id)"
                 " VALUES (?,?,?,?,?, 'nguoi', ?, ?, ?, ?)",
                 (tenant_id, don_id, ca_id,
                  "dieu_chinh_tang" if st > 0 else "dieu_chinh_giam", st,
                  f"điều chỉnh tay #{did}: {ly_do}", csdl.bay_gio(), user_id, bt))
    ghi_nhat_ky(tenant_id, "dieu_chinh", f"tc_dieu_chinh:{did}",
                f"{loai} {st:+d}đ: {ly_do}", user_id)
    return {"dieu_chinh_id": did, "but_toan_id": bt}


def lich_su_dieu_chinh(tenant_id, gioi_han=200):
    _dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT dc.*, u.ho_ten nguoi_ten FROM tc_dieu_chinh dc"
        " LEFT JOIN users u ON u.id = dc.nguoi"
        " WHERE dc.tenant_id=? ORDER BY dc.id DESC LIMIT ?", (tenant_id, int(gioi_han)))]


def lich_su_cod(tenant_id, don_id):
    _dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM tc_cod_chuyen WHERE tenant_id=? AND don_id=? ORDER BY id",
        (tenant_id, don_id))]


def but_toan_cua_don(tenant_id, don_id):
    _dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM tc_but_toan WHERE tenant_id=? AND don_id=? ORDER BY id",
        (tenant_id, don_id))]


def bang_cod(tenant_id, loc=None, gioi_han=200):
    """Bảng COD cho màn hình. `loc` nhận {'trang_thai', 'hang', 'q'}."""
    _dam_bao_bang()
    loc = loc or {}
    sql = ("SELECT c.*, d.ma_don, d.ma_van_don, d.trang_thai trang_thai_don,"
           " d.trang_thai_giao, ca.hang FROM tc_cod c"
           " JOIN don_hang d ON d.id = c.don_id AND d.tenant_id = c.tenant_id"
           " LEFT JOIN carrier_accounts ca ON ca.id = c.carrier_account_id"
           " WHERE c.tenant_id=?")
    ts = [tenant_id]
    if loc.get("trang_thai"):
        if loc["trang_thai"] not in TRANG_THAI_COD:
            raise LoiTaiChinh(f"trạng thái COD lạ: {loc['trang_thai']!r}")
        sql += " AND c.trang_thai=?"; ts.append(loc["trang_thai"])
    if loc.get("hang"):
        sql += " AND ca.hang=?"; ts.append(loc["hang"])
    if loc.get("q"):
        sql += " AND (d.ma_don LIKE ? OR d.ma_van_don LIKE ?)"
        ts += [f"%{loc['q']}%"] * 2
    sql += " ORDER BY c.don_id DESC LIMIT ?"
    ts.append(int(gioi_han))
    return [dict(r) for r in csdl.nhieu(sql, ts)]


def tong_so_tai_chinh(tenant_id) -> dict:
    """Mọi tổng số tài chính của một tenant, trong MỘT chỗ. Giao diện và bộ thử đọc cùng đây.

    Phạm vi: chỉ tenant này, chỉ các bảng `tc_*`. KHÔNG bao gồm doanh thu SaaS (bảng của
    AG-02) và KHÔNG bao gồm tiền ngoài hệ (chuyển khoản tay không nhập vào sổ).
    """
    cn = cong_no(tenant_id)
    cn_lai = tinh_lai_cong_no(tenant_id)
    return {
        "cod": tong_hop_cod(tenant_id),
        "phi": tong_hop_phi(tenant_id),
        "cong_no": cn,
        "cong_no_tinh_lai": cn_lai,
        "cong_no_khop": (cn["tong_phai_thu"] == cn_lai["tong_phai_thu"]
                         and cn["tong_phai_tra"] == cn_lai["tong_phai_tra"]),
        "nhat_ky": kiem_nhat_ky(tenant_id),
        "so_but_toan": csdl.mot("SELECT COUNT(*) c FROM tc_but_toan WHERE tenant_id=?",
                                (tenant_id,))["c"],
    }


def json_an_toan(o):
    """JSON cho route: ép mọi số về int, không để float lọt ra ngoài API tiền."""
    return json.dumps(o, ensure_ascii=False, default=str)
