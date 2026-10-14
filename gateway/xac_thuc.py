# Xác thực webhook theo TỪNG hãng (mỗi hãng một sơ đồ riêng) + RBAC cho API quản trị.
import base64
import hashlib
import hmac

from cau_hinh import HANG, KHOA_API


def kiem_webhook(ma_hang, headers, body: bytes):
    """Trả (dat, ly_do). headers là dict đã hạ chữ thường."""
    ch = HANG.get(ma_hang)
    if not ch:
        return False, "hang khong ton tai"
    kieu = ch["kieu_xac_thuc"]
    if kieu == "hmac_sha256":
        ten_header = ch.get("header_chu_ky", "X-VTP-Signature").lower()
        chu_ky = headers.get(ten_header, "")
        dung = hmac.new(ch["secret"].encode(), body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(chu_ky, dung):
            return True, ""
        return False, f"chu ky {ten_header} sai hoac thieu"
    if kieu == "bearer":
        if headers.get("authorization", "") == f"Bearer {ch['token']}":
            return True, ""
        return False, "bearer token sai hoac thieu"
    if kieu == "header_token":
        if hmac.compare_digest(headers.get(ch["header"].lower(), ""), ch["token"]):
            return True, ""
        return False, f"token {ch['header']} sai hoac thieu"
    if kieu == "basic":
        mong = "Basic " + base64.b64encode(f"{ch['user']}:{ch['mat_khau']}".encode()).decode()
        if hmac.compare_digest(headers.get("authorization", ""), mong):
            return True, ""
        return False, "basic auth sai hoac thieu"
    return False, f"kieu xac thuc chua ho tro: {kieu}"


def vai_tro_api(headers):
    """Trả vai trò từ header X-API-Key, hoặc None nếu khóa sai/thiếu."""
    return KHOA_API.get(headers.get("x-api-key", ""))


def ky_hmac(ma_hang, body: bytes):
    """Tiện ích cho bộ mô phỏng + bộ thử: sinh chữ ký đúng của hãng dùng HMAC."""
    ch = HANG[ma_hang]
    return hmac.new(ch["secret"].encode(), body, hashlib.sha256).hexdigest()
