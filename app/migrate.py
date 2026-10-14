# G01.5 — Migration có quản lý phiên bản, backup và kiểm chứng bảo toàn dữ liệu.
# Chạy: python3 app/migrate.py            (nâng cấp, có backup + verify)
#       python3 app/migrate.py --kiem     (chỉ xem phiên bản, không sửa gì)
#       python3 app/migrate.py --rollback <file-backup>   (khôi phục từ backup)
#
# Nguyên tắc: KHÔNG xóa dữ liệu, KHÔNG đụng gateway.db, KHÔNG gán tenant cho dữ liệu chưa rõ chủ.
import json
import os
import shutil
import sqlite3
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
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    dich = os.path.join(THU_MUC_SAO_LUU,
                        "hub-truoc-migrate-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")
    # Dùng API backup của SQLite để lấy bản nhất quán kể cả khi có WAL.
    nguon = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL)
    ban = sqlite3.connect(dich)
    with ban:
        nguon.backup(ban)
    ban.close()
    nguon.close()
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


def chay(im_lang=False):
    def noi(*a):
        if not im_lang:
            print(*a)

    csdl.mo()  # tạo bảng mới (IF NOT EXISTS) nếu thiếu
    kn_kiem = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL)
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

    kn = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL)
    kn.execute("PRAGMA foreign_keys=OFF")
    try:
        with kn:
            buoc = nang_len_v2(kn)
            kn.execute("INSERT OR REPLACE INTO schema_version (phien_ban, ap_dung_luc, ghi_chu)"
                       " VALUES (?,?,?)",
                       (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio(), "; ".join(buoc)))
    except Exception as e:
        kn.close()
        noi(f"[migrate] HỎNG: {type(e).__name__}: {e}")
        noi(f"[migrate] CSDL giữ nguyên trạng thái trước (transaction rollback). Backup: {ban_sao}")
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
