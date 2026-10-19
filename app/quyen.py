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
    # D-2 — anh Thành duyệt 15/10: "Đồng ý [xoay khoá], nhưng khoá bằng quyền quản trị đặc
    # biệt và kiểm thử trên bản sao trước." Quyền này CHỈ cấp cho PLATFORM_OWNER, KHÔNG cấp
    # PLATFORM_ADMIN — xoay khoá sai là mọi credentials của mọi tenant thành rác, và không
    # có gì báo cho tới lượt gọi hãng đầu tiên.
    # Hai lớp kiểm cố ý: hằng `VAI_TRO_DUOC_XOAY` trong mã CỘNG quyền này trong CSDL. Nghĩa
    # là một dòng INSERT seed nhầm KHÔNG biến ADMIN thành người xoay được khoá.
    "platform.khoa.xoay": "Xoay khoá mã hoá nền tảng",
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
    # D-7 — anh Thành duyệt 15/10 "Đồng ý, làm ngay". Ba quyền tài chính RIÊNG, tách khỏi
    # `tenant.don.duyet`. Trước đó G07 phải dùng `tenant.billing.xem` để đọc và
    # `tenant.don.duyet` để ghi/duyệt, nên:
    #   (a) TENANT_STAFF KHÔNG xem được màn tài chính nào — kể cả COD của đơn nó đang giao;
    #   (b) **ai duyệt đơn thì duyệt được cả đối soát TIỀN** — hai việc khác hẳn nhau về hậu
    #       quả. Duyệt đơn sai thì sửa đơn; duyệt đối soát sai thì áp số của hãng vào sổ tiền.
    # `tai_chinh.QUYEN_TC` đã ưu tiên ba quyền này sẵn, nên seed là đủ, không sửa dòng mã nào.
    "tenant.taichinh.xem": "Xem COD, phí, công nợ, đối soát",
    "tenant.taichinh.ghi": "Ghi điều chỉnh tài chính, nạp bảng kê của hãng",
    "tenant.taichinh.duyet": "DUYỆT đợt đối soát và ghi nhận thanh toán của hãng",
    "tenant.audit.xem": "Xem nhật ký của doanh nghiệp",
    "tenant.ai.dung": "Dùng AI gateway",
}

# Ma trận vai trò → quyền (nguồn để seed vào CSDL).
MA_TRAN = {
    "PLATFORM_OWNER": ["platform.tenant.xem", "platform.tenant.tao", "platform.tenant.sua",
                       "platform.tenant.khoa", "platform.goi.doi", "platform.audit.xem",
                       "platform.khoa.xoay"],
    # PLATFORM_ADMIN: quản trị theo quyền được phân công — không đổi gói, không tạo tenant
    "PLATFORM_ADMIN": ["platform.tenant.xem", "platform.tenant.sua", "platform.tenant.khoa",
                       "platform.audit.xem"],
    "TENANT_OWNER": ["tenant.xem", "tenant.sua", "tenant.membership.xem", "tenant.membership.quan_ly",
                     "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem", "tenant.don.ghi",
                     "tenant.don.duyet", "tenant.hang.xem", "tenant.hang.quan_ly",
                     "tenant.import.ghi", "tenant.import.duyet", "tenant.webhook.xem",
                     "tenant.webhook.replay", "tenant.billing.xem", "tenant.audit.xem", "tenant.ai.dung",
                     # D-7: chủ doanh nghiệp có cả ba quyền tài chính
                     "tenant.taichinh.xem", "tenant.taichinh.ghi", "tenant.taichinh.duyet"],
    "TENANT_ADMIN": ["tenant.xem", "tenant.membership.xem", "tenant.membership.quan_ly",
                     "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem", "tenant.don.ghi",
                     "tenant.don.duyet", "tenant.hang.xem", "tenant.hang.quan_ly",
                     "tenant.import.ghi", "tenant.import.duyet", "tenant.webhook.xem",
                     "tenant.webhook.replay", "tenant.billing.xem", "tenant.audit.xem", "tenant.ai.dung",
                     # D-7: ADMIN giữ NGUYÊN năng lực đang có (nó vốn duyệt tiền được qua
                     # `tenant.don.duyet`), nhưng nay là MỘT NÚM RIÊNG — chủ doanh nghiệp có
                     # thể thu `tenant.taichinh.duyet` của ADMIN mà KHÔNG mất quyền duyệt đơn
                     # của nó. Đó mới là cái D-7 mua được: một cái dial tách rời, chứ không
                     # phải đổi ngay ai làm được gì.
                     "tenant.taichinh.xem", "tenant.taichinh.ghi", "tenant.taichinh.duyet"],
    "TENANT_STAFF": ["tenant.xem", "tenant.khach.xem", "tenant.khach.ghi", "tenant.don.xem",
                     "tenant.don.ghi", "tenant.hang.xem", "tenant.import.ghi",
                     "tenant.webhook.xem", "tenant.ai.dung",
                     # D-7: nhân viên XEM được tài chính — trước đây không xem được gì, kể cả
                     # COD của chính đơn nó đang giao. KHÔNG cho ghi, KHÔNG cho duyệt.
                     # GIỚI HẠN đã ghi ra: `xem` hiện là MỘT quyền phủ CẢ HAI thứ — COD từng
                     # đơn (nhân viên cần) và công nợ toàn doanh nghiệp (nhân viên không cần).
                     # Tách nó thành `taichinh.don.xem` / `taichinh.tong.xem` là việc V-13910.
                     "tenant.taichinh.xem"],
    "TENANT_VIEWER": ["tenant.xem", "tenant.khach.xem", "tenant.don.xem", "tenant.hang.xem",
                      "tenant.webhook.xem",
                      # D-7: vai trò chỉ-xem thì xem được tài chính, đúng tên của nó
                      "tenant.taichinh.xem"],
}

# Vai trò nào được phép CẤP vai trò nào (chặn leo thang đặc quyền).
CAP_DUOC = {
    "TENANT_OWNER": ("TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"),
    "TENANT_ADMIN": ("TENANT_STAFF", "TENANT_VIEWER"),
}


def seed():
    """Nạp vai trò/quyền vào CSDL — **CHỈ CẤP PHẦN MỚI**, trong MỘT giao dịch.

    ====== VÌ SAO KHÔNG CÒN "INSERT OR IGNORE MỌI Ô MỖI LƯỢT" ======
    Bản cũ chạy lại TOÀN BỘ ma trận ở mỗi lần khởi động và sau mỗi lượt migration. Quyền là
    dữ liệu SỐNG: backend tra `role_permissions` ở từng yêu cầu (`co_quyen`), và đường duy nhất
    hiện có để THU một quyền là xoá đúng dòng trong bảng (không có endpoint sửa ma trận). Với
    bản cũ, lượt `seed()` kế tiếp CẤP LẠI đúng dòng vừa bị xoá — im lặng. Đo được:
        xoá (TENANT_STAFF, tenant.don.ghi) → co_quyen = False
        gọi seed()                        → co_quyen = True
    Cùng lớp lỗi ở chiều ngược lại: dòng cấp quyền đã bị gỡ khỏi `MA_TRAN` vẫn sống mãi trong
    CSDL cũ, vì bản cũ chỉ THÊM chứ không bao giờ bớt (privilege creep qua nhiều bản nâng cấp).

    ====== LUẬT MỚI — cấp khi và chỉ khi ======
      · role vừa được tạo trong lượt này, HOẶC
      · perm vừa được tạo trong lượt này (bản mới thêm quyền ⇒ vẫn tự seed được), HOẶC
      · bảng `role_permissions` đang RỖNG HOÀN TOÀN (CSDL chưa được seed lần nào).
    Hệ quả: CSDL mới nhận đủ ma trận · bản nâng cấp nhận quyền MỚI của bản mới · quyền đã bị
    thu KHÔNG sống lại sau restart. Bỏ một ô khỏi `MA_TRAN` cũng KHÔNG tự gỡ dòng đã có —
    muốn thu thì xoá dòng, và từ nay nó ở yên; đó là chủ ý: `MA_TRAN` là nguồn để CẤP, không
    phải lệnh xoá quyền của người vận hành. Hệ quả kèm theo phải nói rõ: **cấp thêm một quyền
    ĐÃ TỒN TẠI cho một vai trò khác** cũng không tự xảy ra, vì `seed()` không phân biệt được
    đó với một lần thu quyền; thay đổi kiểu đó cần người vận hành cấp chủ động (hoặc thêm
    permission mới, khi đó `moi_quyen` lo phần cấp).

    Toàn bộ nằm trong `csdl.giao_dich()`: hỏng giữa chừng (ví dụ một ô trỏ role không tồn tại)
    thì KHÔNG để lại ma trận nửa vời. Bản cũ chèn từng câu, mỗi câu tự chốt — hỏng ở ô thứ k
    là CSDL mang ma trận cụt mà không ai biết.
    """
    with csdl.giao_dich():
        moi_role = set()
        for ma, ten, pv in VAI_TRO:
            if csdl.ghi("INSERT OR IGNORE INTO roles (ma, ten, pham_vi) VALUES (?,?,?)",
                        (ma, ten, pv)).rowcount:
                moi_role.add(ma)
        moi_quyen = set()
        for ma, mo_ta in QUYEN.items():
            if csdl.ghi("INSERT OR IGNORE INTO permissions (ma, mo_ta) VALUES (?,?)",
                        (ma, mo_ta)).rowcount:
                moi_quyen.add(ma)
        # Đọc TRONG cùng giao dịch: một seed khác chen vào giữa thì không thể thấy nửa vời.
        chua_seed = csdl.mot("SELECT COUNT(*) c FROM role_permissions")["c"] == 0
        for role, ds in MA_TRAN.items():
            for p in ds:
                if chua_seed or role in moi_role or p in moi_quyen:
                    csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma)"
                             " VALUES (?,?)", (role, p))


def quyen_cua_vai_tro(role_ma):
    return {r["perm_ma"] for r in csdl.nhieu(
        "SELECT perm_ma FROM role_permissions WHERE role_ma=?", (role_ma,))}


def co_quyen(role_ma, hanh_dong) -> bool:
    """Tra CSDL — nguồn chân lý duy nhất cho quyền."""
    if not role_ma:
        return False
    return csdl.mot("SELECT 1 x FROM role_permissions WHERE role_ma=? AND perm_ma=?",
                    (role_ma, hanh_dong)) is not None
