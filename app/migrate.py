# G01.5 — Migration có quản lý phiên bản, backup và kiểm chứng bảo toàn dữ liệu.
# Chạy: python3 app/migrate.py            (nâng cấp, có backup + verify)
#       python3 app/migrate.py --kiem     (chỉ xem phiên bản, không sửa gì)
#       python3 app/migrate.py --rollback <file-backup>   (khôi phục từ backup)
#
# Nguyên tắc: KHÔNG xóa dữ liệu, KHÔNG đụng gateway.db, KHÔNG gán tenant cho dữ liệu chưa rõ chủ.
import json
import os
import shutil
import sys
from datetime import datetime

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

import cau_hinh   # noqa: E402
import csdl       # noqa: E402
import quyen      # noqa: E402

THU_MUC_SAO_LUU = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "sao-luu")

# Các bảng phải bảo toàn số dòng qua migration (dữ liệu nghiệp vụ đã có).
BANG_PHAI_GIU = ("tenants", "users", "khach_hang", "carrier_accounts", "don_hang",
                 "don_lich_su", "wh_su_kien", "import_batch", "import_dong", "audit")


def _co_bang(kn, ten):
    return kn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (ten,)).fetchone() is not None


def _cot(kn, bang):
    return [r[1] for r in kn.execute(f"PRAGMA table_info({bang})")]


def dem_dong(kn):
    ra = {}
    for b in BANG_PHAI_GIU:
        if _co_bang(kn, b):
            ra[b] = kn.execute(f"SELECT COUNT(*) FROM {b}").fetchone()[0]
    return ra


def sao_luu():
    """Chụp một bản CSDL trước khi nâng cấp. Trả đường dẫn bản sao.

    AG-05 phát hiện ở đợt 3, AG-00 đo lại: bản cũ đặt tên theo GIÂY, nên hai lượt gọi trong
    cùng một giây trả **đúng cùng một đường dẫn** và lượt sau **ghi đè im lặng** — đo được 2
    lượt gọi liền nhau chỉ để lại **1 file** trên đĩa.

    Hậu quả thật: migration hỏng rồi chạy lại ngay sẽ **xoá mất bản "trước khi hỏng"** — đúng
    thứ cần nhất lúc đó. Và nó không báo gì; người vận hành chỉ thấy có một file sao lưu và
    tưởng đó là bản mình cần.

    Nay: trùng tên thì **thêm hậu tố**, không bao giờ ghi đè. Và **kiểm bản sao > 0 byte**
    trước khi tin nó — một file sao lưu rỗng còn tệ hơn không có file, vì nó làm người ta
    tưởng đã có đường lùi (§12.1: thứ dùng để kiểm chứng phải được kiểm trước khi tin).
    """
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    goc = os.path.join(THU_MUC_SAO_LUU,
                       "hub-truoc-migrate-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    dich, n = goc + ".db", 1
    while os.path.exists(dich):
        dich = f"{goc}-{n}.db"      # KHÔNG ghi đè bản đã có, dù cùng giây
        n += 1
        if n > 1000:
            raise RuntimeError(f"quá 1000 bản sao lưu cùng giây tại {goc} — có gì đó sai")
    # Dùng API backup của SQLite để lấy bản nhất quán kể cả khi có WAL.
    nguon = csdl.ket_noi()
    ban = csdl.ket_noi(dich)
    with ban:
        nguon.backup(ban)
    ban.close()
    nguon.close()
    co = os.path.getsize(dich)
    if co <= 0:
        raise RuntimeError(f"bản sao lưu {dich} rỗng ({co} byte) — KHÔNG có đường lùi, "
                           f"dừng trước khi nâng cấp")
    return dich


def _slug(s, dung):
    co_ban = "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")
    co_ban = "-".join(p for p in co_ban.split("-") if p) or "tenant"
    ma, i = co_ban, 2
    while ma in dung:
        ma = f"{co_ban}-{i}"
        i += 1
    dung.add(ma)
    return ma


def nang_len_v2(kn):
    """v1 → v2: tách vai trò tenant ra tenant_memberships, thêm code/platform_role/active_tenant_id,
    RBAC vào CSDL, carrier_providers, audit có resource_type/resource_id/ket_qua."""
    buoc = []

    # 1. tenants.code
    if "code" not in _cot(kn, "tenants"):
        kn.execute("ALTER TABLE tenants ADD COLUMN code TEXT")
        buoc.append("tenants.code")
    if "cap_nhat_luc" not in _cot(kn, "tenants"):
        kn.execute("ALTER TABLE tenants ADD COLUMN cap_nhat_luc TEXT")
        buoc.append("tenants.cap_nhat_luc")
    dung = set()
    for r in kn.execute("SELECT id, ten, code FROM tenants ORDER BY id"):
        if r[2]:
            dung.add(r[2])
    for r in kn.execute("SELECT id, ten, code FROM tenants ORDER BY id").fetchall():
        if not r[2]:
            kn.execute("UPDATE tenants SET code=? WHERE id=?", (_slug(r[1], dung), r[0]))
    kn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_tenant_code ON tenants(code)")

    # 2. users.platform_role
    cot_user = _cot(kn, "users")
    if "platform_role" not in cot_user:
        kn.execute("ALTER TABLE users ADD COLUMN platform_role TEXT")
        buoc.append("users.platform_role")
    if "vai_tro" in cot_user:
        kn.execute("UPDATE users SET platform_role=vai_tro WHERE vai_tro LIKE 'PLATFORM_%'")

    # 3. sessions.active_tenant_id
    if "active_tenant_id" not in _cot(kn, "sessions"):
        kn.execute("ALTER TABLE sessions ADD COLUMN active_tenant_id INTEGER")
        buoc.append("sessions.active_tenant_id")

    # 4. audit: resource_type / resource_id / ket_qua
    cot_audit = _cot(kn, "audit")
    for c, kieu in (("resource_type", "TEXT"), ("resource_id", "TEXT"),
                    ("ket_qua", "TEXT NOT NULL DEFAULT 'thanh_cong'")):
        if c not in cot_audit:
            kn.execute(f"ALTER TABLE audit ADD COLUMN {c} {kieu}")
            buoc.append("audit." + c)
    kn.execute("UPDATE audit SET resource_type = substr(doi_tuong, 1, instr(doi_tuong, ':')-1),"
               " resource_id = substr(doi_tuong, instr(doi_tuong, ':')+1)"
               " WHERE resource_type IS NULL AND instr(doi_tuong, ':') > 0")

    # 5. Chuyển vai trò tenant của user → tenant_memberships (KHÔNG mất ai)
    if "tenant_id" in cot_user and "vai_tro" in cot_user:
        chuyen = 0
        for r in kn.execute("SELECT id, tenant_id, vai_tro, tao_luc FROM users"
                            " WHERE tenant_id IS NOT NULL").fetchall():
            kn.execute("INSERT OR IGNORE INTO tenant_memberships"
                       " (user_id, tenant_id, role, trang_thai, tao_luc) VALUES (?,?,?,'hoat_dong',?)",
                       (r[0], r[1], r[2], r[3]))
            chuyen += 1
        buoc.append(f"tenant_memberships ← {chuyen} user")
        # phiên đang sống: đặt active_tenant_id theo tenant cũ của user
        kn.execute("UPDATE sessions SET active_tenant_id = ("
                   "SELECT u.tenant_id FROM users u WHERE u.id = sessions.user_id)"
                   " WHERE active_tenant_id IS NULL")

    # 6. carrier_providers — nạp từ registry adapter (không có secret)
    import adapter, adapter_jt, adapter_vtp  # noqa: F401
    for ma, h in adapter.danh_sach_hang().items():
        kn.execute("INSERT INTO carrier_providers (ma, ten, capabilities_json, live_mo, cap_nhat_luc)"
                   " VALUES (?,?,?,?,?) ON CONFLICT(ma) DO UPDATE SET"
                   " ten=excluded.ten, capabilities_json=excluded.capabilities_json,"
                   " live_mo=excluded.live_mo, cap_nhat_luc=excluded.cap_nhat_luc",
                   (ma, h["ten"], json.dumps(h["capabilities"]), 1 if h["live_mo"] else 0, csdl.bay_gio()))
    buoc.append("carrier_providers")

    if "credentials_doi_luc" not in _cot(kn, "carrier_accounts"):
        kn.execute("ALTER TABLE carrier_accounts ADD COLUMN credentials_doi_luc TEXT")
        buoc.append("carrier_accounts.credentials_doi_luc")

    # 7. Bỏ cột cũ SAU khi đã chuyển hết — một nguồn chân lý duy nhất cho vai trò
    cot_user = _cot(kn, "users")
    for c in ("tenant_id", "vai_tro"):
        if c in cot_user:
            kn.execute(f"ALTER TABLE users DROP COLUMN {c}")
            buoc.append(f"bỏ users.{c}")
    return buoc


def nang_len_v3(kn):
    """v3: mã hóa lại mọi secret từ định dạng v1 (XOR+HMAC) sang AES-256-GCM, kèm AAD.
    Giải bằng đường cũ rồi mã lại bằng đường mới — KHÔNG đụng nội dung secret."""
    import bao_mat
    buoc = []
    kn.row_factory = csdl.Row
    doi_cred = doi_wh = 0
    hong = []
    for r in kn.execute("SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                        " webhook_secret_ma_hoa FROM carrier_accounts").fetchall():
        # Một hàng hỏng KHÔNG được làm nổ cả migration — ghi lại rồi đi tiếp, nhưng phải BÁO RA,
        # không im lặng bỏ qua (secret đó sẽ còn ở định dạng cũ cho tới khi người xử lý).
        if bao_mat.la_dinh_dang_cu(r["credentials_ma_hoa"]):
            try:
                ro = bao_mat.giai_ma(r["credentials_ma_hoa"])    # đọc định dạng v1
                kn.execute("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                           (bao_mat.ma_hoa(ro, bao_mat.aad_credentials(r["tenant_id"], r["hang"])), r["id"]))
                doi_cred += 1
            except Exception as e:
                hong.append(f"carrier_account {r['id']} credentials: {type(e).__name__}")
        if bao_mat.la_dinh_dang_cu(r["webhook_secret_ma_hoa"]):
            try:
                ro = bao_mat.giai_ma(r["webhook_secret_ma_hoa"])
                kn.execute("UPDATE carrier_accounts SET webhook_secret_ma_hoa=? WHERE id=?",
                           (bao_mat.ma_hoa(ro, bao_mat.aad_webhook(r["webhook_ma"])), r["id"]))
                doi_wh += 1
            except Exception as e:
                hong.append(f"carrier_account {r['id']} webhook_secret: {type(e).__name__}")
    buoc.append(f"AES-256-GCM: {doi_cred} credentials + {doi_wh} webhook secret")
    if hong:
        buoc.append("KHÔNG mã hóa lại được (giữ nguyên định dạng cũ, CẦN NGƯỜI XỬ): " + "; ".join(hong))
    return buoc


def nang_len_v4(kn):
    """v4: đưa mọi secret sang định dạng `v3$<key_id>$...` để từ nay XOAY KHÓA ĐƯỢC.

    Bản mã v2 không mang định danh khóa, nên trước v4 đổi khóa là mọi bản mã cũ thành rác.
    Lượt này giải bằng đúng đường của định dạng đang có rồi mã lại bằng khóa HIỆN HÀNH, kèm AAD
    như cũ — KHÔNG đụng nội dung secret, KHÔNG sinh khóa mới (khóa mới là việc của bao_mat.xoay_khoa).
    Một hàng không giải được thì ghi ra rồi đi tiếp, giữ nguyên bản cũ cho người xử.
    """
    import bao_mat
    kq = bao_mat.ma_hoa_lai_carrier_accounts(kn)
    buoc = [f"key_id (v3) khóa '{kq['key_id']}': {kq['so_credentials']} credentials"
            f" + {kq['so_webhook_secret']} webhook secret trên {kq['so_hang_da_doc']} tài khoản hãng"]
    if kq["hong"]:
        buoc.append("KHÔNG mã hóa lại được (giữ nguyên định dạng cũ, CẦN NGƯỜI XỬ): "
                    + "; ".join(kq["hong"]))
    return buoc


def nang_len_v5(kn):
    """v5: đổi giá trị trạng thái import_batch cũ sang bộ chuẩn của SHARED_CONTRACTS mục 6.
    Mã đã tự đọc được giá trị cũ, lượt này chỉ để dọn cho nhất quán."""
    buoc = []
    cot = [r[1] for r in kn.execute("PRAGMA table_info(import_batch)")]
    if "loi" not in cot:
        kn.execute("ALTER TABLE import_batch ADD COLUMN loi TEXT")
        buoc.append("import_batch.loi")
    doi = 0
    for cu, moi in (("moi", "READY"), ("da_duyet_mot_phan", "PARTIAL_FAILED"), ("xong", "COMPLETED")):
        con = kn.execute("UPDATE import_batch SET trang_thai=? WHERE trang_thai=?", (moi, cu))
        doi += con.rowcount
    buoc.append(f"trang_thai import_batch: đổi {doi} dòng sang bộ chuẩn")
    la = [r[0] for r in kn.execute(
        "SELECT DISTINCT trang_thai FROM import_batch WHERE trang_thai NOT IN"
        " ('UPLOADED','PARSING','VALIDATING','READY','APPROVED','PROCESSING','COMPLETED',"
        "'PARTIAL_FAILED','FAILED')")]
    if la:
        buoc.append("CÒN giá trị lạ (CẦN NGƯỜI XỬ): " + ", ".join(map(str, la)))
    return buoc


def nang_len_v6(kn):
    """v6: thêm users.khoa_den (khóa TẠM) và gỡ các tài khoản đang bị khóa vĩnh viễn
    DO ĐOÁN SAI MẬT KHẨU. Không đụng tài khoản do quản trị cố ý khóa — nhưng schema cũ
    không phân biệt được hai loại, nên chỉ thêm cột và để nguyên trạng thái hiện có."""
    buoc = []
    if "khoa_den" not in [r[1] for r in kn.execute("PRAGMA table_info(users)")]:
        kn.execute("ALTER TABLE users ADD COLUMN khoa_den TEXT")
        buoc.append("users.khoa_den (khóa tạm thay cho khóa vĩnh viễn khi đoán sai)")
    so_khoa = kn.execute("SELECT COUNT(*) FROM users WHERE trang_thai='khoa'").fetchone()[0]
    if so_khoa:
        buoc.append(f"GHI CHÚ: còn {so_khoa} tài khoản ở trạng thái 'khoa' — schema cũ không phân "
                    "biệt được do quản trị khóa hay do đoán sai, người vận hành tự xem và mở")
    return buoc


def nang_len_v7(kn):
    """v7: gộp ba đợt WAVE 1 — AG-02 ORDERS (G04), AG-03 WEBHOOK (G06), AG-01 hạn mức nhập.

    TOÀN BỘ là thao tác THÊM: `ADD COLUMN`, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX
    IF NOT EXISTS`. Không `DROP`, không `DELETE`, không `UPDATE` dữ liệu sẵn có, không đổi
    kiểu hay ràng buộc cột cũ — nên dòng cũ giữ nguyên và mã cũ vẫn đọc được bảng.

    Cột `NOT NULL` duy nhất (`wh_su_kien.can_soat`) có `DEFAULT 0`, nên SQLite điền được
    cho dòng đã có. Mọi cột khác để NULL cố ý: NULL ở đây nghĩa là "sự kiện có trước đợt
    này, hãng không gửi thông tin đó" — khác hẳn với 0 hay chuỗi rỗng.
    """
    buoc = []

    # ---- AG-02 ORDERS (G04): don_hang + don_mat_hang -------------------------
    co = [r[1] for r in kn.execute("PRAGMA table_info(don_hang)")]
    them_don = [
        ("external_reference", "TEXT"),
        ("approved_by", "INTEGER REFERENCES users(id)"),
        ("approved_luc", "TEXT"),
        ("ly_do_tu_choi", "TEXT"),
        ("tu_choi_boi", "INTEGER REFERENCES users(id)"),
        ("tu_choi_luc", "TEXT"),
        ("nguoi_gui_tinh", "TEXT"), ("nguoi_gui_quan", "TEXT"),
        ("nguoi_gui_xa", "TEXT"), ("nguoi_gui_buu_chinh", "TEXT"),
        ("nguoi_nhan_tinh", "TEXT"), ("nguoi_nhan_quan", "TEXT"),
        ("nguoi_nhan_xa", "TEXT"), ("nguoi_nhan_buu_chinh", "TEXT"),
    ]
    n = 0
    for ten, kieu in them_don:
        if ten not in co:
            kn.execute(f"ALTER TABLE don_hang ADD COLUMN {ten} {kieu}")
            n += 1
    if n:
        buoc.append(f"don_hang +{n} cột (G04: duyệt/từ chối/địa chỉ hành chính/mã đối chiếu)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_don_extref ON don_hang(tenant_id, external_reference)")

    if not _co_bang(kn, "don_mat_hang"):
        kn.execute("""
            CREATE TABLE don_mat_hang (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tenant_id INTEGER NOT NULL REFERENCES tenants(id),
              don_id INTEGER NOT NULL REFERENCES don_hang(id),
              stt INTEGER NOT NULL,
              ten TEXT NOT NULL,
              ma_sku TEXT NOT NULL DEFAULT '',
              so_luong INTEGER NOT NULL DEFAULT 1,
              don_gia INTEGER NOT NULL DEFAULT 0,
              khoi_luong_gram INTEGER NOT NULL DEFAULT 0,
              ghi_chu TEXT NOT NULL DEFAULT '',
              tao_luc TEXT NOT NULL,
              UNIQUE (don_id, stt)
            )""")
        buoc.append("bảng MỚI don_mat_hang (tiền là số nguyên ĐỒNG, khối lượng là GRAM — cấm float)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_mh_don ON don_mat_hang(don_id)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_mh_tenant ON don_mat_hang(tenant_id)")

    # ---- AG-03 WEBHOOK (G06): wh_su_kien ------------------------------------
    cw = [r[1] for r in kn.execute("PRAGMA table_info(wh_su_kien)")]
    them_wh = [
        ("hang_ma_goc", "TEXT"),
        ("hang_mo_ta_goc", "TEXT"),
        ("hang_su_kien_goc", "TEXT"),
        ("anh_xa_do_tin_cay", "TEXT"),
        ("anh_xa_nguon", "TEXT"),
        ("can_soat", "INTEGER NOT NULL DEFAULT 0"),
        ("hang_moc_thoi_gian", "TEXT"),
        ("don_id", "INTEGER REFERENCES don_hang(id)"),
        ("trang_thai_chuan", "TEXT"),
    ]
    m = 0
    for ten, kieu in them_wh:
        if ten not in cw:
            kn.execute(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
            m += 1
    if m:
        buoc.append(f"wh_su_kien +{m} cột (G06: mã gốc hãng, độ tin cậy ánh xạ, cần soát, mốc hãng)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_wh_don  ON wh_su_kien(don_id, hang_moc_thoi_gian)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_wh_soat ON wh_su_kien(can_soat, id)")

    # ---- AG-01: hạn mức nhập ------------------------------------------------
    # `gioi_han.py` tự tạo bảng này khi dùng lần đầu, nên hệ chạy được dù chưa migrate.
    # Tạo sẵn ở đây để schema khai báo đủ ở một chỗ, không phụ thuộc lượt gọi đầu tiên.
    if not _co_bang(kn, "han_muc_nhap_thang"):
        kn.execute("""
            CREATE TABLE han_muc_nhap_thang (
              tenant_id INTEGER NOT NULL REFERENCES tenants(id),
              thang TEXT NOT NULL,
              so_don_nhap INTEGER NOT NULL DEFAULT 0,
              so_dong INTEGER NOT NULL DEFAULT 0,
              so_file INTEGER NOT NULL DEFAULT 0,
              so_byte INTEGER NOT NULL DEFAULT 0,
              cap_nhat_luc TEXT,
              PRIMARY KEY (tenant_id, thang)
            )""")
        buoc.append("bảng MỚI han_muc_nhap_thang (bộ đếm hạn mức nhập, sống qua restart)")

    return buoc


def chay_ddl_trong_giao_dich(kn, ddl):
    """Chạy một khối DDL mà KHÔNG chốt giao dịch đang mở. Dùng thay `executescript`.

    `kn.executescript()` tự COMMIT giao dịch đang mở trước khi chạy — lặng lẽ, không báo gì.
    Đo được ngày 15/10/2026 (py 3.9.6): sau `BEGIN IMMEDIATE` thì `in_transaction` là True,
    sau một `executescript` thành True→False, và `COMMIT` sau đó nổ "cannot commit - no
    transaction is active". Hậu quả nặng hơn một lỗi cú pháp: lượt nâng cấp nạp 5 khối DDL
    của G07–G11 qua `executescript`, nên migration CHƯA BAO GIỜ nguyên tử — hỏng sau khối
    đầu là để lại CSDL nâng cấp nửa vời, trong khi thông báo lỗi vẫn hứa "rollback". Đúng
    dạng §12.2: hệ thống nói sai về chính nó.

    Tách câu bằng `sqlite3.complete_statement`, KHÔNG bằng `ddl.split(";")`: khối
    `CREATE TRIGGER ... BEGIN SELECT RAISE(ABORT,'...'); END;` có dấu `;` BÊN TRONG, nên cắt
    theo dấu `;` là sinh ra những câu cụt vẫn "chạy được" một phần — hỏng im lặng.
    """
    cau, dem = "", 0
    for dong in ddl.splitlines(True):
        cau += dong
        if csdl.cau_sql_du(cau) and cau.strip():
            kn.execute(cau)
            dem += 1
            cau = ""
    con = cau.strip()
    if con and not con.lstrip().startswith("--"):
        raise ValueError(f"DDL còn câu chưa trọn sau khi tách: {con[:120]!r}")
    return dem


def nang_len_v8(kn):
    """v8: gộp năm hằng DDL của đợt 3 — G07 tài chính · G08 gói dịch vụ · G09 harness hãng
    · G10 công việc AI · G11 quan sát.

    **Không viết lại DDL ở đây.** Năm hằng nằm trong module của chính nó
    (`tai_chinh.DDL_G07`, `goi_dich_vu.DDL_G08`, `harness_hang.DDL_G09`, `ai_job.DDL_G10`,
    `quan_sat.DDL_G11`) và migration CHẠY ĐÚNG CHUỖI ĐÓ. Chép sang đây là tạo bản thứ hai,
    và hai bản nội dung là hai bản sẽ lệch nhau — lúc đó bộ thử của agent chạy một chuỗi còn
    CSDL thật mang một chuỗi khác, không ai thấy cho tới khi có cột thiếu.

    AG-00 đã đo trên cả năm chuỗi (bỏ lời bình trước khi quét): **27 bảng · 21 index ·
    4 trigger · 0 DROP · 0 ALTER · 0 DELETE ngoài trigger · 0 cột REAL/FLOAT · 0 trùng tên**
    — cả giữa các agent với nhau và với 23 bảng đang có. Toàn bộ là `IF NOT EXISTS` nên chạy
    lại vô hại.

    Bốn trigger của G07 là **chốt chặn SỬA/XOÁ bút toán** (`BEFORE UPDATE/DELETE ... RAISE
    (ABORT)`) — tức là ngược với xoá. Đừng bắt nhầm chữ `DELETE` trong đó: §17 đòi bút toán
    bất biến, và trigger là cách cưỡng chế bằng CSDL thay vì bằng lời dặn.
    """
    buoc = []
    # Nạp muộn, trong hàm: năm module này không cần có mặt lúc `migrate` được import, và
    # một module hỏng không được làm chết cả đường migration.
    import ai_job
    import goi_dich_vu
    import harness_hang
    import quan_sat
    import tai_chinh

    for ten, ddl in (("G07 tài chính + đối soát", tai_chinh.DDL_G07),
                     ("G08 gói dịch vụ + mức dùng", goi_dich_vu.DDL_G08),
                     ("G09 harness hãng", harness_hang.DDL_G09),
                     ("G10 công việc AI", ai_job.DDL_G10),
                     ("G11 quan sát", quan_sat.DDL_G11)):
        truoc = {r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index','trigger')")}
        chay_ddl_trong_giao_dich(kn, ddl)
        sau = {r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index','trigger')")}
        them = sorted(sau - truoc)
        buoc.append(f"{ten}: +{len(them)} đối tượng" + (f" ({', '.join(them[:4])}…)" if them else ""))
    return buoc


def nang_len_v9(kn):
    """v9: bảng trạng thái của GIỚI HẠN TẦN SUẤT — G19/AG-02.

    **Không viết lại DDL ở đây.** Hằng nằm trong module của chính nó (`gioi_han.DDL_GIOI_HAN`) và
    migration CHẠY ĐÚNG HẰNG ĐÓ — cùng lý do đã ghi ở `nang_len_v8`: chép sang đây là tạo bản thứ
    hai, và hai bản nội dung là hai bản sẽ lệch nhau.

    Vì sao cần bước này (không chỉ để `CREATE TABLE IF NOT EXISTS` trong module tự lo):
    PHẦN A trước G19 giữ bộ đếm **trong bộ nhớ MỘT tiến trình**, nên trần thực = khai báo × số bản
    (đo được: khai 20 ⇒ **20/40/80/160** với N=1/2/4/8) và **mất sạch khi khởi động lại**. Nay
    trạng thái nằm trong CSDL. Module tự tạo bảng khi chạy, nhưng CSDL **đã tồn tại** phải được
    nâng cấp TƯỜNG MINH: để nó tự lo thì lần ghi đầu tiên mới phát hiện thiếu bảng, và lúc đó
    đường ghi đang nằm trong giao dịch nghiệp vụ — hỏng ở giữa đường chứ không hỏng lúc nâng cấp.

    `moc` là **epoch giây** (`time.time()`), KHÔNG phải `monotonic`: monotonic là thang riêng của
    từng tiến trình, không so sánh được qua tiến trình — dùng nó làm mốc thì trần lại thủng im lặng,
    đúng cái lỗi bước này đóng.
    """
    buoc = []
    import gioi_han

    truoc = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    chay_ddl_trong_giao_dich(kn, gioi_han.DDL_GIOI_HAN)
    sau = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    them = sorted(sau - truoc)
    buoc.append("G19 giới hạn tần suất (kho trong CSDL): "
                f"+{len(them)} đối tượng" + (f" ({', '.join(them)})" if them else " (đã có sẵn)"))
    return buoc


# Chờ tối đa bao lâu để lấy khoá nâng cấp. 60 giây: đủ cho một lượt nâng cấp thật
# (lượt v1→v8 trên CSDL rỗng đo được dưới 1 giây; CSDL có dữ liệu thì lâu hơn), và ngắn hơn
# mọi ngưỡng chờ của người. Hết giờ thì NÉM, không chạy chồng — §13 của chỉ thị G12:
# thử lại vô hạn không phải là phương án xử lý.
KHOA_CHO_GIAY = 60


# `BEGIN IMMEDIATE` trong `chay()` làm BA việc cùng lúc, nên không tách ra được:
#   1. KHOÁ XUYÊN TIẾN TRÌNH. `csdl.khoa_ghi` là RLock của Python — nó chỉ phủ MỘT tiến
#      trình, nên hai lượt `python3 -m migrate` song song đi xuyên qua nó như không có gì.
#      SQLite khoá ở tầng tệp nên chặn được thật (đo ca L: tiến trình hai nhận
#      "database is locked", và vào được ngay khi bên kia nhả).
#   2. RANH GIỚI LÙI CHO CẢ DDL. `with kn:` của python KHÔNG mở giao dịch cho
#      `CREATE`/`ALTER` — chỉ cho DML (đo ca J: ép hỏng giữa chừng thì INSERT lùi, còn
#      bảng vừa CREATE Ở LẠI). Nên câu cũ "CSDL giữ nguyên trạng thái trước (transaction
#      rollback)" ĐÚNG VỚI DML và SAI VỚI DDL — một lời nói sai về chính hệ thống, đúng
#      dạng §12.2. `BEGIN` tường minh thì lùi sạch cả DDL (đo ca K).
#   3. CHỐT ĐỌC-RỒI-LÀM. Phiên bản đọc ở đầu hàm nằm ngoài mọi khoá; đọc lại bên trong
#      khoá thì tiến trình đến sau thấy việc đã xong và nhường, thay vì nâng cấp lần hai.
def chay(im_lang=False):
    def noi(*a):
        if not im_lang:
            print(*a)

    csdl.mo()  # tạo bảng mới (IF NOT EXISTS) nếu thiếu
    kn_kiem = csdl.ket_noi()
    pb = kn_kiem.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
    truoc = dem_dong(kn_kiem)
    kn_kiem.close()

    if pb >= csdl.PHIEN_BAN_SCHEMA:
        noi(f"[migrate] CSDL đã ở phiên bản {pb} — không cần nâng cấp.")
        return {"phien_ban": pb, "da_nang": False}

    noi(f"[migrate] Phiên bản hiện tại: {pb} → đích: {csdl.PHIEN_BAN_SCHEMA}")
    ban_sao = sao_luu()
    noi(f"[migrate] Đã backup: {ban_sao}")
    noi(f"[migrate] Số dòng trước: {truoc}")

    kn = csdl.ket_noi(timeout=KHOA_CHO_GIAY, tuong_minh=True)
    # THỨ TỰ BẮT BUỘC: `PRAGMA foreign_keys` phải đặt TRƯỚC `BEGIN`. Đo được (ca M):
    # trong giao dịch, SQLite BỎ QUA lệnh này không báo lỗi gì — đổi thứ tự là chạy cả
    # migration với khoá ngoại BẬT mà không ai thấy.
    kn.execute("PRAGMA foreign_keys=OFF")
    kn.execute("PRAGMA busy_timeout=%d" % (KHOA_CHO_GIAY * 1000))
    # `BEGIN IMMEDIATE` làm BA việc cùng lúc — xem khối chú thích ở KHOA_CHO_GIAY.
    try:
        kn.execute("BEGIN IMMEDIATE")
    except csdl.LoiVanHanh as e:
        kn.close()
        noi(f"[migrate] KHÔNG lấy được khoá sau {KHOA_CHO_GIAY}s: {e}")
        noi("[migrate] Có tiến trình khác đang nâng cấp CSDL này. KHÔNG chạy chồng.")
        raise
    # ĐỌC LẠI phiên bản BÊN TRONG khoá. Lượt đọc ở đầu hàm nằm ngoài mọi khoá, nên giữa nó
    # và chỗ này một tiến trình khác có thể đã nâng xong. Đây là đua đọc-rồi-làm kinh điển.
    pb_trong = kn.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
    if pb_trong >= csdl.PHIEN_BAN_SCHEMA:
        kn.execute("ROLLBACK")
        kn.close()
        noi(f"[migrate] Tiến trình khác đã nâng lên {pb_trong} trong lúc chờ khoá — không làm lại.")
        return {"phien_ban": pb_trong, "da_nang": False, "nhuong": True}
    pb = pb_trong
    try:
        buoc = []
        if pb < 2:
            buoc += nang_len_v2(kn)
        if pb < 3:
            buoc += nang_len_v3(kn)
        if pb < 4:
            buoc += nang_len_v4(kn)
        if pb < 5:
            buoc += nang_len_v5(kn)
        if pb < 6:
            buoc += nang_len_v6(kn)
        if pb < 7:
            buoc += nang_len_v7(kn)
        if pb < 8:
            buoc += nang_len_v8(kn)
        if pb < 9:
            buoc += nang_len_v9(kn)
        kn.execute("INSERT OR REPLACE INTO schema_version (phien_ban, ap_dung_luc, ghi_chu)"
                   " VALUES (?,?,?)",
                   (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio(), "; ".join(buoc)))
        kn.execute("COMMIT")
    except Exception as e:
        try:
            kn.execute("ROLLBACK")
        except csdl.LoiCSDL:
            pass        # đã tự lùi rồi; không che lỗi gốc bằng lỗi lùi
        kn.close()
        noi(f"[migrate] HỎNG: {type(e).__name__}: {e}")
        noi(f"[migrate] Đã ROLLBACK — kể cả CREATE/ALTER (BEGIN tường minh, đo ca K). Backup: {ban_sao}")
        raise
    sau = dem_dong(kn)
    kn.close()

    # KIỂM CHỨNG bảo toàn dữ liệu — không bảng nào được mất dòng
    mat = {b: (truoc.get(b, 0), sau.get(b, 0)) for b in truoc if sau.get(b, 0) < truoc.get(b, 0)}
    if mat:
        noi(f"[migrate] CẢNH BÁO MẤT DỮ LIỆU: {mat} — khôi phục từ {ban_sao}")
        khoi_phuc(ban_sao)
        raise SystemExit(2)

    csdl.dong()
    quyen.seed()
    # Quên mọi cache SCHEMA sau khi nâng cấp. Thiếu bước này thì một tiến trình đang chạy
    # vẫn nhớ "bảng chưa có" và tiếp tục đi đường lùi — hỏng im lặng, vì đường lùi vẫn trả
    # kết quả hợp lệ, chỉ là kết quả của schema cũ.
    for mod, ham in (("billing", "quen_cache_phien_ban"), ("webhook", "xoa_cache_cot"),
                     ("don_hang", "quen_cache_schema"), ("tai_chinh", "quen_cache_bang"),
                     ("goi_dich_vu", "nap_lai_bang")):
        try:
            __import__(mod)
            f = getattr(sys.modules[mod], ham, None)
            if f:
                f()
        except Exception as e:
            noi(f"[migrate] bỏ qua {mod}.{ham}: {type(e).__name__}: {e}")
    noi(f"[migrate] Bước đã làm: {'; '.join(buoc)}")
    noi(f"[migrate] Số dòng sau: {sau}  → bảo toàn ĐẠT")
    noi(f"[migrate] Xong, phiên bản {csdl.PHIEN_BAN_SCHEMA}. Rollback nếu cần: "
        f"python3 app/migrate.py --rollback {ban_sao}")
    return {"phien_ban": csdl.PHIEN_BAN_SCHEMA, "da_nang": True, "backup": ban_sao,
            "truoc": truoc, "sau": sau, "buoc": buoc}


def khoi_phuc(duong_backup):
    """Rollback: đưa CSDL về đúng file backup (có cất bản hiện tại trước khi đè)."""
    if not os.path.exists(duong_backup):
        raise SystemExit(f"Không thấy file backup: {duong_backup}")
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    cat_di = os.path.join(THU_MUC_SAO_LUU,
                          "hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")
    if os.path.exists(cau_hinh.DUONG_DAN_CSDL):
        shutil.copy2(cau_hinh.DUONG_DAN_CSDL, cat_di)
    for duoi in ("-wal", "-shm"):
        p = cau_hinh.DUONG_DAN_CSDL + duoi
        if os.path.exists(p):
            os.remove(p)
    shutil.copy2(duong_backup, cau_hinh.DUONG_DAN_CSDL)
    print(f"[migrate] Đã khôi phục từ {duong_backup}. Bản trước khi khôi phục cất ở {cat_di}")


if __name__ == "__main__":
    if "--kiem" in sys.argv:
        csdl.mo()
        print(f"Phiên bản schema trong CSDL: {csdl.phien_ban_hien_tai()} (mã nguồn: {csdl.PHIEN_BAN_SCHEMA})")
    elif "--rollback" in sys.argv:
        khoi_phuc(sys.argv[sys.argv.index("--rollback") + 1])
    else:
        chay()
