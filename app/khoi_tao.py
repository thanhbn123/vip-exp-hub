# Khởi tạo dữ liệu demo cho local: platform owner + 2 tenant mẫu + tài khoản hãng mock.
# Mật khẩu demo SINH NGẪU NHIÊN và ghi vào app/du-lieu/TAI-KHOAN-DEMO.md (ngoài git) —
# không in ra màn hình, không dán vào hội thoại.
import json
import os
import secrets

import bao_mat
import cau_hinh
import csdl


def chay():
    csdl.mo()
    if csdl.mot("SELECT id FROM users LIMIT 1"):
        print("[khoi-tao] CSDL đã có người dùng — không seed lại (an toàn, không ghi đè).")
        return
    duong_ghi = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "TAI-KHOAN-DEMO.md")
    dong = ["# Tài khoản demo local — VIP Express Hub SaaS",
            "", "Sinh tự động bởi `khoi_tao.py`. File nằm ngoài git. Toàn bộ là tài khoản demo local.", ""]

    def tao_user(tenant_id, ten_dn, ho_ten, vai_tro):
        mk = secrets.token_urlsafe(9)
        csdl.ghi("INSERT INTO users (tenant_id, ten_dang_nhap, mat_khau_hash, ho_ten, vai_tro, tao_luc)"
                 " VALUES (?,?,?,?,?,?)",
                 (tenant_id, ten_dn, bao_mat.bam_mat_khau(mk), ho_ten, vai_tro, csdl.bay_gio()))
        dong.append(f"- `{ten_dn}` / `{mk}` — {vai_tro}" + (f" (tenant {tenant_id})" if tenant_id else " (nền tảng)"))
        return mk

    tao_user(None, "platform-owner", "Chủ nền tảng (demo)", "PLATFORM_OWNER")

    for ten_tenant, tien_to in (("Shop Demo A", "shopa"), ("Shop Demo B", "shopb")):
        con = csdl.ghi("INSERT INTO tenants (ten, goi_id, tao_luc) VALUES (?,?,?)",
                       (ten_tenant, "basic", csdl.bay_gio()))
        t_id = con.lastrowid
        dong.append(f"\n## {ten_tenant} (tenant {t_id})")
        tao_user(t_id, f"{tien_to}-owner", f"Chủ {ten_tenant}", "TENANT_OWNER")
        tao_user(t_id, f"{tien_to}-staff", f"Nhân viên {ten_tenant}", "TENANT_STAFF")
        tao_user(t_id, f"{tien_to}-viewer", f"Chỉ xem {ten_tenant}", "TENANT_VIEWER")
        # tài khoản hãng mock + webhook secret (ghi vào file demo để bắn thử webhook)
        for hang in ("vtp", "jt"):
            cred = {"ghi_chu": "credentials demo mock", "ma_demo": secrets.token_hex(6)}
            cred_mh, duoi = bao_mat.luu_credentials(cred)
            wh_secret = secrets.token_urlsafe(24)
            wh_ma = secrets.token_urlsafe(12)
            csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
                     " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
                     (t_id, hang, f"{hang.upper()} mock của {ten_tenant}", "mock", cred_mh, duoi,
                      wh_ma, bao_mat.ma_hoa(wh_secret), csdl.bay_gio()))
            dong.append(f"  - hãng `{hang}`: webhook_ma=`{wh_ma}` · webhook_secret=`{wh_secret}`")
        csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                 (t_id, f"Khách demo của {ten_tenant}", "0900000000", "Địa chỉ demo", csdl.bay_gio()))

    os.makedirs(cau_hinh.THU_MUC_DU_LIEU, exist_ok=True)
    with open(duong_ghi, "w", encoding="utf-8") as f:
        f.write("\n".join(dong) + "\n")
    os.chmod(duong_ghi, 0o600)
    csdl.audit("seed_demo", "he_thong", "khởi tạo platform owner + 2 tenant demo")
    print(f"[khoi-tao] Xong. Tài khoản demo ghi tại: {duong_ghi}")


if __name__ == "__main__":
    chay()
