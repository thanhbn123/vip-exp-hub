# G02.2 — RBAC lưu trong CSDL: roles / permissions / role_permissions.
# Quyền KHÔNG hard-code ở giao diện: backend tra bảng role_permissions ở từng endpoint.
# Vai trò nền tảng nằm ở users.platform_role; vai trò trong tenant nằm ở tenant_memberships.role.
import csdl

VAI_TRO = [
    ("PLATFORM_OWNER", "Chủ nền tảng", "platform"),
    ("PLATFORM_ADMIN", "Quản trị nền tảng", "platform"),
    ("TENANT_OWNER", "Chủ doanh nghiệp", "tenant"),
    ("TENANT_ADMIN", "Quản trị doanh nghiệp", "tenant"),
    ("TENANT_STAFF", "Nhân viên", "tenant"),
    ("TENANT_VIEWER", "Chỉ xem", "tenant"),
]

QUYEN = {
    # nền tảng
    "platform.tenant.xem": "Xem mọi tenant",
    "platform.tenant.tao": "Tạo tenant",
    "platform.tenant.sua": "Sửa tenant",
    "platform.tenant.khoa": "Khóa/mở tenant",
    "platform.goi.doi": "Đổi gói dịch vụ của tenant",
    "platform.audit.xem": "Xem audit toàn nền tảng",
    # trong tenant
    "tenant.xem": "Xem thông tin doanh nghiệp",
    "tenant.sua": "Sửa thông tin doanh nghiệp",
    "tenant.membership.xem": "Xem danh sách thành viên",
    "tenant.membership.quan_ly": "Mời/đổi vai trò/vô hiệu thành viên",
    "tenant.khach.xem": "Xem khách hàng",
    "tenant.khach.ghi": "Thêm/sửa khách hàng",
    "tenant.don.xem": "Xem đơn hàng",
    "tenant.don.ghi": "Tạo/sửa đơn hàng",
    "tenant.don.duyet": "Duyệt/gửi/hủy đơn",
    "tenant.hang.xem": "Xem tài khoản hãng",
    "tenant.hang.quan_ly": "Thêm/khóa/rotate tài khoản hãng",
    "tenant.import.ghi": "Upload và sửa dòng import",
    "tenant.import.duyet": "Duyệt batch import",
    "tenant.webhook.xem": "Xem sự kiện webhook",
    "tenant.webhook.replay": "Replay sự kiện webhook",
    "tenant.billing.xem": "Xem gói và usage",
    "tenant.audit.xem": "Xem nhật ký của doanh nghiệp",
    "tenant.ai.dung": "Dùng AI gateway",
}

# Ma trận vai trò → quyền (nguồn để seed vào CSDL).
MA_TRAN = {
    "PLATFORM_OWNER": ["platform.tenant.xem", "platform.tenant.tao", "platform.tenant.sua",
                       "platform.tenant.khoa", "platform.goi.doi", "platform.audit.xem"],
    # PLATFORM_ADMIN: quản trị theo quyền được phân công — không đổi gói, không tạo tenant
    "PLATFORM_ADMIN": ["platform.tenant.xem", "platform.tenant.sua", "platform.tenant.khoa",
                       "platform.audit.xem"],
    "TENANT_OWNER": ["tenant.xem", "tenant.sua", "tenant.membership.xem", "tenant.membership.quan_ly",
                     "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem", "tenant.don.ghi",
                     "tenant.don.duyet", "tenant.hang.xem", "tenant.hang.quan_ly",
                     "tenant.import.ghi", "tenant.import.duyet", "tenant.webhook.xem",
                     "tenant.webhook.replay", "tenant.billing.xem", "tenant.audit.xem", "tenant.ai.dung"],
    "TENANT_ADMIN": ["tenant.xem", "tenant.membership.xem", "tenant.membership.quan_ly",
                     "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem", "tenant.don.ghi",
                     "tenant.don.duyet", "tenant.hang.xem", "tenant.hang.quan_ly",
                     "tenant.import.ghi", "tenant.import.duyet", "tenant.webhook.xem",
                     "tenant.webhook.replay", "tenant.billing.xem", "tenant.audit.xem", "tenant.ai.dung"],
    "TENANT_STAFF": ["tenant.xem", "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem",
                     "tenant.don.ghi", "tenant.hang.xem", "tenant.import.ghi",
                     "tenant.webhook.xem", "tenant.ai.dung"],
    "TENANT_VIEWER": ["tenant.xem", "tenant.khach.xem", "tenant.don.xem", "tenant.hang.xem",
                      "tenant.webhook.xem"],
}

# Vai trò nào được phép CẤP vai trò nào (chặn leo thang đặc quyền).
CAP_DUOC = {
    "TENANT_OWNER": ("TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "TENANT_ADMIN": ("TENANT_STAFF", "TENANT_VIEWER"),
}


def seed():
    """Nạp vai trò/quyền vào CSDL (idempotent)."""
    for ma, ten, pv in VAI_TRO:
        csdl.ghi("INSERT OR IGNORE INTO roles (ma, ten, pham_vi) VALUES (?,?,?)", (ma, ten, pv))
    for ma, mo_ta in QUYEN.items():
        csdl.ghi("INSERT OR IGNORE INTO permissions (ma, mo_ta) VALUES (?,?)", (ma, mo_ta))
    for role, ds in MA_TRAN.items():
        for p in ds:
            csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma) VALUES (?,?)", (role, p))


def quyen_cua_vai_tro(role_ma):
    return {r["perm_ma"] for r in csdl.nhieu(
        "SELECT perm_ma FROM role_permissions WHERE role_ma=?", (role_ma,))}


def co_quyen(role_ma, hanh_dong) -> bool:
    """Tra CSDL — nguồn chân lý duy nhất cho quyền."""
    if not role_ma:
        return False
    return csdl.mot("SELECT 1 x FROM role_permissions WHERE role_ma=? AND perm_ma=?",
                    (role_ma, hanh_dong)) is not None
