#!/usr/bin/env python3
"""Tạo MỘT tenant + một chủ doanh nghiệp trên CSDL TRỐNG (VPS bootstrap).

KHÔNG ghi mật khẩu ra stdout/log. Mật khẩu đọc từ stdin (khuyến nghị) hoặc biến
VIP_BOOTSTRAP_PASSWORD. Script TỪ CHỐI nếu CSDL đã có bất kỳ user nào — không bao giờ
đè hay tạo thêm quyền trên hệ đang chạy.

Dùng trong container:
  printf '%s\\n' "$MAT_KHAU" | docker compose run --rm -T --entrypoint python3 hub \\
      /app/trien_khai/vps/bootstrap_admin.py
"""
import getpass
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, "app"))

import bao_mat  # noqa: E402
import csdl     # noqa: E402
import quyen    # noqa: E402


def _chuoi_bat_buoc(ten, mac_dinh="", toi_da=200):
    v = str(os.environ.get(ten, mac_dinh) or "").strip()
    if not v:
        raise SystemExit(f"thiếu {ten}")
    if len(v) > toi_da:
        raise SystemExit(f"{ten} quá dài")
    return v


def _doc_mat_khau():
    env = os.environ.get("VIP_BOOTSTRAP_PASSWORD")
    if env:
        sys.stderr.write("[bootstrap] CẢNH BÁO: dùng VIP_BOOTSTRAP_PASSWORD trong môi trường; "
                         "ưu tiên pipe qua stdin để không nằm trong docker inspect.\n")
        return env
    if sys.stdin.isatty():
        return getpass.getpass("Mật khẩu chủ doanh nghiệp (≥12 ký tự): ")
    dong = sys.stdin.readline()
    return dong.rstrip("\r\n")


def main():
    tenant_code = _chuoi_bat_buoc("VIP_BOOTSTRAP_TENANT_CODE", "vip-express", 64)
    tenant_name = _chuoi_bat_buoc("VIP_BOOTSTRAP_TENANT_NAME", "VIP Express Hub", 200)
    username = _chuoi_bat_buoc("VIP_BOOTSTRAP_USERNAME", "owner", 64)
    fullname = _chuoi_bat_buoc("VIP_BOOTSTRAP_FULLNAME", "Chủ doanh nghiệp", 200)
    plan = _chuoi_bat_buoc("VIP_BOOTSTRAP_PLAN", "pro", 32)
    password = _doc_mat_khau()
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,64}", username):
        raise SystemExit("username chỉ nhận chữ/số/._- (3–64 ký tự)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", tenant_code):
        raise SystemExit("tenant code chỉ nhận chữ thường/số/gạch ngang (2–64 ký tự)")
    if len(password) < 12:
        raise SystemExit("mật khẩu phải ≥12 ký tự")
    if password == username:
        raise SystemExit("mật khẩu không được trùng username")

    csdl.mo()
    quyen.seed()
    if csdl.mot("SELECT COUNT(*) AS n FROM users")["n"]:
        raise SystemExit("CSDL đã có user — bootstrap TỪ CHỐI (không tạo thêm quyền)")
    if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (plan,)):
        raise SystemExit(f"gói dịch vụ {plan!r} không tồn tại")
    if csdl.mot("SELECT id FROM tenants WHERE code=?", (tenant_code,)):
        raise SystemExit("tenant code đã tồn tại")

    with csdl.giao_dich():
        tid = csdl.ghi(
            "INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)",
            (tenant_code, tenant_name, plan, csdl.bay_gio())).lastrowid
        uid = csdl.ghi(
            "INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,platform_role,tao_luc)"
            " VALUES (?,?,?,?,?)",
            (username, bao_mat.bam_mat_khau(password), fullname, "PLATFORM_OWNER",
             csdl.bay_gio())).lastrowid
        csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc)"
                 " VALUES (?,?,?,?)", (uid, tid, "TENANT_OWNER", csdl.bay_gio()))
        csdl.audit("bootstrap_admin", f"tenant:{tid}", "tạo platform owner + tenant owner; "
                   "mật khẩu KHÔNG ghi vào audit", tenant_id=tid, user_id=uid)
    print(f"[bootstrap] tenant_id={tid} code={tenant_code} plan={plan}")
    print(f"[bootstrap] user_id={uid} username={username} platform_role=PLATFORM_OWNER")
    print("[bootstrap] KHÔNG in mật khẩu. Đổi mật khẩu ngay sau lần đăng nhập đầu.")


if __name__ == "__main__":
    main()
