# Cấu hình backend Multi-Tenant SaaS — local-first. Không secret thật trong file này.
import os

THU_MUC_APP = os.path.dirname(os.path.abspath(__file__))
THU_MUC_GOC = os.path.dirname(THU_MUC_APP)
THU_MUC_DU_LIEU = os.environ.get("VIP_HUB_DATA", os.path.join(THU_MUC_APP, "du-lieu"))
DUONG_DAN_CSDL = os.path.join(THU_MUC_DU_LIEU, "hub.db")
DUONG_DAN_KHOA = os.path.join(THU_MUC_DU_LIEU, "khoa-noi-bo.key")  # khóa mã hóa credentials, 0600, ngoài git
CONG_MAC_DINH = int(os.environ.get("VIP_HUB_PORT", "8897"))

PHIEN_SONG_GIO = 12            # phiên đăng nhập sống 12 giờ
KHOA_SAU_SO_LAN_SAI = 5        # sai mật khẩu 5 lần liên tiếp → khóa TẠM
# Khóa TẠM, không khóa vĩnh viễn: khóa vĩnh viễn bằng mật khẩu sai là đường cho người lạ
# vô hiệu hóa tài khoản bất kỳ (AG-07 QA, ca q06 — 5 yêu cầu vô danh là khóa chết một tài khoản).
# Khóa vĩnh viễn chỉ do QUẢN TRỊ đặt (users.trang_thai='khoa').
KHOA_TAM_PHUT = 15
PBKDF2_VONG = 200_000
# Provider reset mật khẩu GIẢ LẬP: trả token thẳng qua API để kiểm thử luồng khi chưa có SMTP.
# MẶC ĐỊNH TẮT. Bật là lỗ hổng chiếm tài khoản: người VÔ DANH gọi /auth/quen-mat-khau cho bất kỳ
# tên đăng nhập nào sẽ nhận token hợp lệ rồi đặt lại mật khẩu — chiếm được cả PLATFORM_OWNER
# trong 3 yêu cầu HTTP (AG-07 QA chứng minh được thật ngày 14/10/2026, ca q01b).
# Chỉ bật có chủ đích khi chạy bộ thử: VIP_HUB_RESET_TOKEN=1.
HIEN_TOKEN_RESET = os.environ.get("VIP_HUB_RESET_TOKEN", "0") == "1"

VAI_TRO_PLATFORM = ("PLATFORM_OWNER", "PLATFORM_ADMIN")
VAI_TRO_TENANT = ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER")
VAI_TRO_HOP_LE = VAI_TRO_PLATFORM + VAI_TRO_TENANT

# Thứ hạng trạng thái giao vận — chống out-of-order (kế thừa G01)
HANG_TRANG_THAI_GIAO = {
    "cho_lay": 1, "lay_hang": 2, "dang_giao": 3,
    "giao_that_bai": 4, "giao_thanh_cong": 5, "hoan_hang": 6,
}

# Gói dịch vụ mặc định (G10) — hạn mức đo và chặn từ backend
GOI_MAC_DINH = [
    {"id": "free", "ten": "Miễn phí", "gia_thang": 0,
     "han_muc_don_thang": 50, "han_muc_ai_thang": 20, "so_nhan_vien": 2, "so_tai_khoan_hang": 1},
    {"id": "basic", "ten": "Cơ bản", "gia_thang": 299000,
     "han_muc_don_thang": 1000, "han_muc_ai_thang": 500, "so_nhan_vien": 5, "so_tai_khoan_hang": 3},
    {"id": "pro", "ten": "Chuyên nghiệp", "gia_thang": 999000,
     "han_muc_don_thang": 10000, "han_muc_ai_thang": 5000, "so_nhan_vien": 20, "so_tai_khoan_hang": 10},
]

WEBHOOK_SO_LAN_THU = 3
WEBHOOK_BACKOFF_GOC = float(os.environ.get("VIP_HUB_BACKOFF", "0.5"))
