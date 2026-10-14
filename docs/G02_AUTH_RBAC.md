# G02 — AUTHENTICATION / RBAC

## 1. Authentication (G02.1)

| Chức năng | Đường dẫn | Ghi chú |
|---|---|---|
| Đăng nhập | `POST /api/v2/auth/dang-nhap` | cookie `phien` HttpOnly + SameSite=Lax |
| Đăng xuất | `POST /api/v2/auth/dang-xuat` | thu hồi đúng phiên đó |
| Đổi mật khẩu | `POST /api/v2/auth/doi-mat-khau` | thu hồi **mọi phiên khác** |
| Thu hồi phiên | `POST /api/v2/auth/thu-hoi-phien` | giữ lại phiên hiện tại |
| Quên mật khẩu | `POST /api/v2/auth/quen-mat-khau` | provider **giả lập** (chưa có SMTP) |
| Đặt lại mật khẩu | `POST /api/v2/auth/dat-lai-mat-khau` | token dùng **một lần**, hạn 30 phút |
| Provision tài khoản | `POST /api/v2/memberships` | tạo user mới hoặc gắn user có sẵn vào tenant |
| Khóa/mở tài khoản | qua membership `trang_thai`, hoặc `users.trang_thai` | khóa → thu hồi hết phiên |

**Mật khẩu:** PBKDF2-HMAC-SHA256, 200.000 vòng, salt 16 byte ngẫu nhiên mỗi người
(`pbkdf2$vòng$salt$hash`). So sánh bằng `hmac.compare_digest`. Không lưu plaintext ở đâu.

**Phiên:** token 32 byte `secrets.token_urlsafe`; CSDL chỉ lưu **SHA-256 của token** nên đọc được DB
cũng không mạo danh được. Hết hạn 12 giờ. Thu hồi được từng phiên hoặc tất cả.

**Chống brute-force:** sai 5 lần → khóa tài khoản + thu hồi mọi phiên.

**Không lộ thông tin tài khoản:** mọi lỗi đăng nhập (không có user / sai mật khẩu / vừa bị tự khóa)
đều trả **đúng một câu**: `sai tên đăng nhập hoặc mật khẩu`. `quen-mat-khau` cũng luôn trả cùng một
thông báo dù tài khoản có thật hay không.

**Provider reset giả lập:** vì chưa cấu hình SMTP, token reset được trả thẳng trong phản hồi API khi
`HIEN_TOKEN_RESET=1` (mặc định ở local). Rời local phải đặt `VIP_HUB_RESET_TOKEN=0` — lúc đó API chỉ
trả thông báo chung, không trả token.

## 2. RBAC (G02.2)

Quyền nằm trong CSDL (`roles`, `permissions`, `role_permissions`), **không hard-code ở giao diện**.
Backend gọi `quyen.co_quyen(role, hanh_dong)` ở từng endpoint; frontend chỉ dùng danh sách quyền
trả về từ `/auth/toi` để ẩn/hiện nút cho gọn. TEST-019 xóa một dòng `role_permissions` và chứng minh
endpoint từ chối ngay → quyền thật sự đến từ CSDL.

### Permission matrix

| Quyền | P_OWNER | P_ADMIN | T_OWNER | T_ADMIN | T_STAFF | T_VIEWER |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| platform.tenant.xem | ✅ | ✅ | | | | |
| platform.tenant.tao | ✅ | | | | | |
| platform.tenant.sua | ✅ | ✅ | | | | |
| platform.tenant.khoa | ✅ | ✅ | | | | |
| platform.goi.doi | ✅ | | | | | |
| platform.audit.xem | ✅ | ✅ | | | | |
| tenant.xem | | | ✅ | ✅ | ✅ | ✅ |
| tenant.sua | | | ✅ | | | |
| tenant.membership.xem | | | ✅ | ✅ | | |
| tenant.membership.quan_ly | | | ✅ | ✅ | | |
| tenant.khach.xem | | | ✅ | ✅ | ✅ | ✅ |
| tenant.khach.ghi | | | ✅ | ✅ | ✅ | |
| tenant.don.xem | | | ✅ | ✅ | ✅ | ✅ |
| tenant.don.ghi | | | ✅ | ✅ | ✅ | |
| tenant.don.duyet | | | ✅ | ✅ | | |
| tenant.hang.xem | | | ✅ | ✅ | ✅ | ✅ |
| tenant.hang.quan_ly | | | ✅ | ✅ | | |
| tenant.import.ghi | | | ✅ | ✅ | ✅ | |
| tenant.import.duyet | | | ✅ | ✅ | | |
| tenant.webhook.xem | | | ✅ | ✅ | ✅ | ✅ |
| tenant.webhook.replay | | | ✅ | ✅ | | |
| tenant.billing.xem | | | ✅ | ✅ | | |
| tenant.audit.xem | | | ✅ | ✅ | | |
| tenant.ai.dung | | | ✅ | ✅ | ✅ | |

**Chống leo thang đặc quyền** (`quyen.CAP_DUOC`): TENANT_OWNER chỉ cấp được ADMIN/STAFF/VIEWER;
TENANT_ADMIN chỉ cấp được STAFF/VIEWER. Không vai trò tenant nào cấp được vai trò nền tảng
(TEST-009). PLATFORM_ADMIN hẹp hơn PLATFORM_OWNER: không tạo tenant, không đổi gói.

## 3. Membership management (G02.3)

| Method | Đường dẫn | Việc |
|---|---|---|
| GET | `/api/v2/memberships` | Danh sách thành viên của tenant đang thao tác |
| POST | `/api/v2/memberships` | Mời/thêm: user đã có → thêm membership; chưa có → tạo user + membership |
| PUT | `/api/v2/memberships/{id}` | Đổi `role` hoặc `trang_thai` (hoat_dong/vo_hieu) |
| DELETE | `/api/v2/memberships/{id}` | Gỡ khỏi tenant (thu hồi phiên của người đó) |
| POST | `/api/v2/auth/doi-tenant` | Switch tenant |

Ràng buộc: không thao tác lên `TENANT_OWNER`; không tự đổi vai trò/vô hiệu chính mình; vô hiệu hoặc
gỡ membership thì **thu hồi phiên ngay**. Switch tenant nạp lại toàn bộ giao diện nên **không mang
dữ liệu tenant cũ sang** (test_016 kiểm cả ở API lẫn UI).

## 4. Security audit (G02.4)

Bảng `audit` ghi: `luc` · `user_id` (actor) · `tenant_id` · `hanh_dong` (action) ·
`resource_type` + `resource_id` · `ket_qua` (thanh_cong/tu_choi/that_bai) · `chi_tiet` · `dia_chi`.

Sự kiện đã ghi: đăng nhập thành công/thất bại, tự khóa tài khoản, đăng xuất, đổi mật khẩu, đặt lại
mật khẩu, thu hồi phiên, tạo/sửa/khóa tenant, đổi gói, thêm/đổi/xóa membership, đổi tenant,
**từ chối quyền**, tạo/duyệt/gửi/hủy đơn, thao tác tài khoản hãng, replay webhook, import.

**Không bao giờ ghi** mật khẩu, token phiên, token reset hay credentials hãng — TEST-013 quét cả log
server lẫn bảng audit để chứng minh.
