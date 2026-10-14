# Bảo mật: băm mật khẩu, phiên đăng nhập, RBAC, mã hóa credentials, chống rò secret.
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta

import cau_hinh
import csdl


# ====== Mật khẩu ======
def bam_mat_khau(mat_khau: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", mat_khau.encode(), salt, cau_hinh.PBKDF2_VONG)
    return f"pbkdf2${cau_hinh.PBKDF2_VONG}${salt.hex()}${h.hex()}"


def kiem_mat_khau(mat_khau: str, luu: str) -> bool:
    try:
        _, vong, salt_hex, h_hex = luu.split("$")
        h = hashlib.pbkdf2_hmac("sha256", mat_khau.encode(), bytes.fromhex(salt_hex), int(vong))
        return hmac.compare_digest(h.hex(), h_hex)
    except (ValueError, TypeError):
        return False


# ====== Phiên đăng nhập ======
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def dang_nhap(ten_dang_nhap, mat_khau, dia_chi=None):
    """Trả (token, user_row) hoặc (None, lý_do). Sai 5 lần → khóa tài khoản."""
    u = csdl.mot("SELECT * FROM users WHERE ten_dang_nhap=?", (ten_dang_nhap,))
    if not u:
        return None, "sai tên đăng nhập hoặc mật khẩu"
    if u["trang_thai"] == "khoa":
        return None, "tài khoản đã bị khóa"
    if u["tenant_id"] is not None:
        t = csdl.mot("SELECT trang_thai FROM tenants WHERE id=?", (u["tenant_id"],))
        if not t or t["trang_thai"] != "hoat_dong":
            return None, "doanh nghiệp đã bị khóa"
    if not kiem_mat_khau(mat_khau, u["mat_khau_hash"]):
        so_sai = u["so_lan_sai"] + 1
        if so_sai >= cau_hinh.KHOA_SAU_SO_LAN_SAI:
            csdl.ghi("UPDATE users SET so_lan_sai=?, trang_thai='khoa' WHERE id=?", (so_sai, u["id"]))
            csdl.audit("khoa_tai_khoan_tu_dong", f"user:{u['id']}", f"sai mật khẩu {so_sai} lần",
                       tenant_id=u["tenant_id"], dia_chi=dia_chi)
            return None, "sai mật khẩu nhiều lần — tài khoản đã bị khóa"
        csdl.ghi("UPDATE users SET so_lan_sai=? WHERE id=?", (so_sai, u["id"]))
        return None, "sai tên đăng nhập hoặc mật khẩu"
    csdl.ghi("UPDATE users SET so_lan_sai=0 WHERE id=?", (u["id"],))
    token = secrets.token_urlsafe(32)
    het_han = (datetime.now() + timedelta(hours=cau_hinh.PHIEN_SONG_GIO)).strftime("%Y-%m-%d %H:%M:%S")
    csdl.ghi("INSERT INTO sessions (token_hash, user_id, tao_luc, het_han, dia_chi) VALUES (?,?,?,?,?)",
             (_hash_token(token), u["id"], csdl.bay_gio(), het_han, dia_chi))
    csdl.audit("dang_nhap", f"user:{u['id']}", "", tenant_id=u["tenant_id"], user_id=u["id"], dia_chi=dia_chi)
    return token, u


def phien_hien_tai(token):
    """Trả user_row của phiên hợp lệ, hoặc None."""
    if not token:
        return None
    s = csdl.mot("SELECT * FROM sessions WHERE token_hash=?", (_hash_token(token),))
    if not s or s["thu_hoi"]:
        return None
    if s["het_han"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return None
    u = csdl.mot("SELECT * FROM users WHERE id=?", (s["user_id"],))
    if not u or u["trang_thai"] != "hoat_dong":
        return None
    if u["tenant_id"] is not None:
        t = csdl.mot("SELECT trang_thai FROM tenants WHERE id=?", (u["tenant_id"],))
        if not t or t["trang_thai"] != "hoat_dong":
            return None
    return u


def dang_xuat(token):
    csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE token_hash=?", (_hash_token(token),))


def thu_hoi_moi_phien(user_id, tru_token=None):
    """Thu hồi mọi phiên của user (dùng khi đổi mật khẩu / admin thu hồi)."""
    if tru_token:
        csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE user_id=? AND token_hash<>?",
                 (user_id, _hash_token(tru_token)))
    else:
        csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE user_id=?", (user_id,))


# ====== RBAC ======
# Ma trận quyền: hành động → các vai trò được phép. Backend kiểm, frontend chỉ ẩn/hiện nút.
QUYEN = {
    # platform
    "platform.tenant.quan_ly": ("PLATFORM_OWNER", "PLATFORM_ADMIN"),
    "platform.goi.quan_ly": ("PLATFORM_OWNER",),
    "platform.admin.quan_ly": ("PLATFORM_OWNER",),
    "platform.audit.xem": ("PLATFORM_OWNER", "PLATFORM_ADMIN"),
    # tenant
    "tenant.user.quan_ly": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.khach.xem": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "tenant.khach.ghi": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF"),
    "tenant.don.xem": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "tenant.don.ghi": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF"),
    "tenant.don.duyet": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.hang.xem": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "tenant.hang.quan_ly": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.import.ghi": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF"),
    "tenant.import.duyet": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.webhook.xem": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "tenant.webhook.replay": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.billing.xem": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.audit.xem": ("TENANT_OWNER", "TENANT_ADMIN"),
    "tenant.ai.dung": ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF"),
}


def co_quyen(user_row, hanh_dong) -> bool:
    return user_row["vai_tro"] in QUYEN.get(hanh_dong, ())


# ====== Mã hóa credentials (mức local) ======
# Encrypt-then-MAC trên stdlib: keystream = SHA256(key || nonce || counter), MAC = HMAC-SHA256.
# GIỚI HẠN GHI RÕ: đủ cho demo local; production phải dùng AES-GCM/KMS (thư viện vetted).
def _khoa_noi_bo() -> bytes:
    duong = cau_hinh.DUONG_DAN_KHOA
    if not os.path.exists(duong):
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "wb") as f:
            f.write(secrets.token_bytes(32))
        os.chmod(duong, 0o600)
    with open(duong, "rb") as f:
        return f.read()


def _keystream(key: bytes, nonce: bytes, dai: int) -> bytes:
    ra = b""
    dem = 0
    while len(ra) < dai:
        ra += hashlib.sha256(key + nonce + dem.to_bytes(4, "big")).digest()
        dem += 1
    return ra[:dai]


def ma_hoa(ro: str) -> str:
    key = _khoa_noi_bo()
    nonce = secrets.token_bytes(16)
    data = ro.encode()
    ct = bytes(a ^ b for a, b in zip(data, _keystream(key, nonce, len(data))))
    mac = hmac.new(key, nonce + ct, hashlib.sha256).hexdigest()
    return nonce.hex() + "$" + ct.hex() + "$" + mac


def giai_ma(goi: str) -> str:
    key = _khoa_noi_bo()
    nonce_hex, ct_hex, mac = goi.split("$")
    nonce, ct = bytes.fromhex(nonce_hex), bytes.fromhex(ct_hex)
    mac_dung = hmac.new(key, nonce + ct, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, mac_dung):
        raise ValueError("MAC sai — dữ liệu mã hóa đã bị sửa")
    return bytes(a ^ b for a, b in zip(ct, _keystream(key, nonce, len(ct)))).decode()


def che_credentials(cred: dict) -> dict:
    """Bản hiển thị an toàn: mọi giá trị chỉ còn 4 ký tự cuối."""
    return {k: ("…" + str(v)[-4:] if v else "") for k, v in cred.items()}


def luu_credentials(cred: dict):
    """Trả (bản_mã_hóa, đuôi_hiển_thị)."""
    ro = json.dumps(cred, ensure_ascii=False)
    duoi = next((str(v)[-4:] for v in cred.values() if v), "")
    return ma_hoa(ro), duoi
