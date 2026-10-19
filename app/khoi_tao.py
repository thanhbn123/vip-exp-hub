# Khởi tạo dữ liệu demo cho local (schema v2): platform owner + 2 tenant + membership + tài khoản hãng mock.
# Mật khẩu demo SINH NGẪU NHIÊN và ghi vào app/du-lieu/TAI-KHOAN-DEMO.md (ngoài git) —
# không in ra màn hình, không dán vào hội thoại.
import json
import os
import secrets

import adapter
import adapter_best  # noqa: F401 — để carrier_providers có BEST
import adapter_jt   # noqa: F401
import adapter_vtp  # noqa: F401
import bao_mat
import cau_hinh
import csdl
import quyen


def seed_providers():
    for ma, h in adapter.danh_sach_hang().items():
        csdl.ghi("INSERT INTO carrier_providers (ma, ten, capabilities_json, live_mo, cap_nhat_luc)"
                 " VALUES (?,?,?,?,?) ON CONFLICT(ma) DO UPDATE SET ten=excluded.ten,"
                 " capabilities_json=excluded.capabilities_json, live_mo=excluded.live_mo,"
                 " cap_nhat_luc=excluded.cap_nhat_luc",
                 (ma, h["ten"], json.dumps(h["capabilities"]), 1 if h["live_mo"] else 0, csdl.bay_gio()))


def chay():
    csdl.mo()
    quyen.seed()
    seed_providers()
    if csdl.mot("SELECT id FROM users LIMIT 1"):
        print("[khoi-tao] CSDL đã có người dùng — không seed lại (an toàn, không ghi đè).")
        return
    duong_ghi = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "TAI-KHOAN-DEMO.md")
    dong = ["# Tài khoản demo local — VIP Express Hub SaaS (schema v2)", "",
            "Sinh tự động bởi `khoi_tao.py`. File nằm ngoài git. Toàn bộ là tài khoản demo local.", ""]

    def tao_user(ten_dn, ho_ten, platform_role=None):
        mk = secrets.token_urlsafe(9)
        uid = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                       " VALUES (?,?,?,?,?)",
                       (ten_dn, bao_mat.bam_mat_khau(mk), ho_ten, platform_role, csdl.bay_gio())).lastrowid
        dong.append(f"- `{ten_dn}` / `{mk}`" + (f" — {platform_role}" if platform_role else ""))
        return uid

    def gan(uid, tid, role):
        csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc) VALUES (?,?,?,?)",
                 (uid, tid, role, csdl.bay_gio()))

    tao_user("platform-owner", "Chủ nền tảng (demo)", "PLATFORM_OWNER")
    tao_user("platform-admin", "Quản trị nền tảng (demo)", "PLATFORM_ADMIN")

    # Một user thuộc NHIỀU tenant để minh họa switch-tenant
    uid_da_tenant = None
    for ten_tenant, code, tien_to in (("Shop Demo A", "shop-a", "shopa"), ("Shop Demo B", "shop-b", "shopb")):
        tid = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                       (code, ten_tenant, "basic", csdl.bay_gio())).lastrowid
        dong.append(f"\n## {ten_tenant} (tenant {tid}, code `{code}`)")
        gan(tao_user(f"{tien_to}-owner", f"Chủ {ten_tenant}"), tid, "TENANT_OWNER")
        gan(tao_user(f"{tien_to}-staff", f"Nhân viên {ten_tenant}"), tid, "TENANT_STAFF")
        gan(tao_user(f"{tien_to}-viewer", f"Chỉ xem {ten_tenant}"), tid, "TENANT_VIEWER")
        if uid_da_tenant is None:
            uid_da_tenant = tao_user("da-tenant", "Người dùng thuộc hai doanh nghiệp")
            dong.append("  (tài khoản `da-tenant` thuộc CẢ hai tenant — dùng để thử switch tenant)")
        gan(uid_da_tenant, tid, "TENANT_ADMIN" if code == "shop-a" else "TENANT_VIEWER")
        for hang in ("vtp", "jt"):
            cred = {"ghi_chu": "credentials demo mock", "ma_demo": secrets.token_hex(6)}
            wh_secret, wh_ma = secrets.token_urlsafe(24), secrets.token_urlsafe(12)
            cred_mh, duoi = bao_mat.ma_hoa_cred(cred, tid, hang)
            csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
                     " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
                     " VALUES (?,?,?,?,?,?,?,?,?)",
                     (tid, hang, f"{hang.upper()} mock của {ten_tenant}", "mock", cred_mh, duoi,
                      wh_ma, bao_mat.ma_hoa_wh(wh_secret, wh_ma), csdl.bay_gio()))
            dong.append(f"  - hãng `{hang}`: webhook_ma=`{wh_ma}` · webhook_secret=`{wh_secret}`")
        csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                 (tid, f"Khách demo của {ten_tenant}", "0900000000", "Địa chỉ demo", csdl.bay_gio()))

    os.makedirs(cau_hinh.THU_MUC_DU_LIEU, exist_ok=True)
    with open(duong_ghi, "w", encoding="utf-8") as f:
        f.write("\n".join(dong) + "\n")
    os.chmod(duong_ghi, 0o600)
    csdl.audit("seed_demo", "he_thong:1", "khởi tạo platform owner + 2 tenant demo")
    print(f"[khoi-tao] Xong. Tài khoản demo ghi tại: {duong_ghi}")


if __name__ == "__main__":
    chay()
