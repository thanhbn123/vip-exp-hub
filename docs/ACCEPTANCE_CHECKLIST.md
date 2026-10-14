# ACCEPTANCE_CHECKLIST — nghiệm thu Multi-Tenant SaaS (local)

Chỉ tick khi có bằng chứng chạy thật (tên bộ thử / lệnh / biên bản). Trạng thái cập nhật ở cột cuối.

## Bảo mật & cách ly (G12 bắt buộc)

| # | Tiêu chí | Bằng chứng cần | Trạng thái |
|---|---|---|---|
| 1 | Tenant A không XEM được dữ liệu tenant B (khách, đơn, sự kiện, hãng) | test cross-tenant GET → 404/403 | ☐ |
| 2 | Tenant A không SỬA được đơn tenant B | test PUT/POST chéo → 404/403 | ☐ |
| 3 | Tenant A không dùng được carrier account của B khi tạo/gửi đơn | test resource ownership | ☐ |
| 4 | Nhân viên không vượt quyền admin (staff không tạo user, viewer không ghi) | test RBAC | ☐ |
| 5 | Webhook giả mạo (sai chữ ký) bị từ chối, không lưu | test 401 | ☐ |
| 6 | Webhook trùng không cập nhật hai lần | test UNIQUE event | ☐ |
| 7 | Event sai thứ tự không làm sai trạng thái | test rank guard | ☐ |
| 8 | Gửi lại createOrder không sinh đơn trùng (idempotency) | test UNIQUE idem_key | ☐ |
| 9 | API hãng lỗi/timeout không mất dữ liệu đơn (đơn giữ `dang_gui` + cờ kiểm lại) | test adapter lỗi | ☐ |
| 10 | Import file lỗi không hỏng batch (dòng lỗi INVALID, batch vẫn xử lý được) | test import | ☐ |
| 11 | Không rò secret trong log và API (chỉ 4 ký tự cuối) | test quét log + body | ☐ |
| 12 | Không rò PII sang tenant khác | gộp trong 1,2 | ☐ |
| 13 | Frontend không cầm secret hãng (mọi gọi hãng đi qua backend) | soát mã admin/ | ☐ |
| 14 | Migration/rollback: schema tạo mới không đụng `gateway.db`; git baseline lùi được | kiểm file + git | ☐ |
| 15 | Toàn bộ chức năng cũ còn chạy (regression: bộ thử gateway 9/9, trang demo mở được) | chạy lại bộ thử | ☐ |

## Chức năng

| # | Tiêu chí | Trạng thái |
|---|---|---|
| F1 | Đăng nhập/đăng xuất, khóa TK sau 5 lần sai, đổi mật khẩu, thu hồi phiên | ☐ |
| F2 | Platform quản lý tenant (tạo/khóa), tenant không gọi được API platform | ☐ |
| F3 | CRUD người dùng theo vai trò; nhật ký truy cập | ☐ |
| F4 | CRUD khách hàng theo tenant | ☐ |
| F5 | Đơn: tạo/sửa nháp → duyệt → gửi hãng (mock) → có mã vận đơn; hủy; lịch sử; lọc/tìm; xuất CSV | ☐ |
| F6 | Carrier adapter: 2 adapter (VTP, J&T) qua interface chung, capability khai báo rõ, MOCK gắn nhãn | ☐ |
| F7 | Webhook tenant-aware: thô→queue→normalize→resolve→update+audit; DLQ + replay | ☐ |
| F8 | Import: upload CSV/XLSX → preview → sửa lỗi → approve → tạo đơn theo batch, trạng thái từng dòng | ☐ |
| F9 | AI gateway mock + policy (AI không vượt auth/tenant/approval) | ☐ |
| F10 | Billing: gói + hạn mức chặn thật từ backend + usage | ☐ |
| F11 | Admin UI đủ màn chính, tiếng Việt, responsive, không hiện secret | ☐ |

## BLOCKED (cần Owner)

- [ ] Credentials J&T thật + lệnh cho phép gọi API thật → mới được test LIVE VERIFIED.
- [ ] Cho phép đọc repo `vip-viettelpost` để tái dùng adapter VTP thật (G05 phần thật).
- [ ] Mọi quyết định deploy/production.
