# Cấu hình gateway G01 — toàn bộ khóa dưới đây là GIÁ TRỊ DEMO sinh cho môi trường local,
# không phải khóa thật của hãng nào. Khi có hãng thật, khóa nạp qua biến môi trường, không để trong mã.
import os

DUONG_DAN_CSDL = os.environ.get(
    "VIP_GATEWAY_DB",
    os.path.join(os.path.dirname(__file__), "du-lieu", "gateway.db"),
)
CONG_MAC_DINH = int(os.environ.get("VIP_GATEWAY_PORT", "8898"))

# Mỗi hãng một sơ đồ xác thực riêng (đúng yêu cầu đặc tả: không giả định chung một sơ đồ).
HANG = {
    "vtp": {
        "ten": "Viettel Post",
        "kieu_xac_thuc": "hmac_sha256",      # header X-VTP-Signature = HMAC-SHA256(secret, body)
        "secret": "demo-vtp-hmac-secret-g01",
    },
    "ghn": {
        "ten": "GHN",
        "kieu_xac_thuc": "bearer",            # Authorization: Bearer <token>
        "token": "demo-ghn-bearer-token-g01",
    },
    "ghtk": {
        "ten": "GHTK",
        "kieu_xac_thuc": "header_token",      # X-GHTK-Token: <token>
        "header": "X-GHTK-Token",
        "token": "demo-ghtk-token-g01",
    },
    "jt": {
        "ten": "J&T Express",
        "kieu_xac_thuc": "basic",             # HTTP Basic
        "user": "demo-jt-user",
        "mat_khau": "demo-jt-pass-g01",
    },
    "best": {
        "ten": "BEST Express",
        "kieu_xac_thuc": "hmac_sha256",       # header X-BEST-Sign
        "header_chu_ky": "X-BEST-Sign",
        "secret": "demo-best-hmac-secret-g01",
    },
}

# RBAC cho API đọc/replay — khóa demo local.
KHOA_API = {
    "demo-admin-key": "admin",    # đọc + replay/thu lại DLQ
    "demo-viewer-key": "viewer",  # chỉ đọc
}

# Thứ hạng trạng thái để xử lý sự kiện đến sai thứ tự (out-of-order):
# sự kiện có hạng thấp hơn hạng hiện tại của vận đơn thì GHI SỔ nhưng KHÔNG lùi trạng thái.
HANG_TRANG_THAI = {
    "don_moi": 1,
    "lay_hang": 2,
    "dang_giao": 3,
    "giao_that_bai": 4,
    "giao_thanh_cong": 5,
    "hoan_hang": 6,
}
# Sự kiện không đổi trạng thái hành trình (chỉ ghi hành trình):
SU_KIEN_KHONG_DOI_TRANG_THAI = {"cap_nhat_cod"}

SO_LAN_THU_TOI_DA = 3           # quá số này → DLQ
GIAY_BACKOFF_GOC = float(os.environ.get("VIP_GATEWAY_BACKOFF", "0.5"))  # 0.5 → 1 → 2 giây
