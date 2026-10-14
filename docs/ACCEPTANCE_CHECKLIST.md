# ACCEPTANCE_CHECKLIST — nghiệm thu Multi-Tenant SaaS (local)

Chỉ tick khi có bằng chứng chạy thật (tên bộ thử / lệnh / biên bản). Trạng thái cập nhật ở cột cuối.

## Bảo mật & cách ly (G12 bắt buộc)

| # | Tiêu chí | Bằng chứng cần | Trạng thái |
|---|---|---|---|
| 1 | Tenant A không XEM được dữ liệu tenant B (khách, đơn, sự kiện, hãng) | test cross-tenant GET → 404/403 | ✅ test_01 |
| 2 | Tenant A không SỬA được đơn tenant B | test PUT/POST chéo → 404/403 | ✅ test_02 |
| 3 | Tenant A không dùng được carrier account của B khi tạo/gửi đơn | test resource ownership | ✅ test_03 |
| 4 | Nhân viên không vượt quyền admin (staff không tạo user, viewer không ghi) | test RBAC | ✅ test_04 |
| 5 | Webhook giả mạo (sai chữ ký) bị từ chối, không lưu | test 401 | ✅ test_05 |
| 6 | Webhook trùng không cập nhật hai lần | test UNIQUE event | ✅ test_06 |
| 7 | Event sai thứ tự không làm sai trạng thái | test rank guard | ✅ test_07 |
| 8 | Gửi lại createOrder không sinh đơn trùng (idempotency) | test UNIQUE idem_key | ✅ test_09 |
| 9 | API hãng lỗi/timeout không mất dữ liệu đơn (đơn giữ `dang_gui` + cờ kiểm lại) | test adapter lỗi | ✅ test_10 |
| 10 | Import file lỗi không hỏng batch (dòng lỗi INVALID, batch vẫn xử lý được) | test import | ✅ test_11 |
| 11 | Không rò secret trong log và API (chỉ 4 ký tự cuối) | test quét log + body | ✅ test_12 |
| 12 | Không rò PII sang tenant khác | gộp trong 1,2 | ✅ test_01/02/08 |
| 13 | Frontend không cầm secret hãng (mọi gọi hãng đi qua backend) | soát mã admin/ | ✅ test_13 |
| 14 | Migration/rollback: schema tạo mới không đụng `gateway.db`; git baseline lùi được | kiểm file + git | ✅ test_16 + git fd79d74 |
| 15 | Toàn bộ chức năng cũ còn chạy (regression: bộ thử gateway 9/9, trang demo mở được) | chạy lại bộ thử | ✅ gateway 9/9 |

## Chức năng

| # | Tiêu chí | Trạng thái |
|---|---|---|
| F1 | Đăng nhập/đăng xuất, khóa TK sau 5 lần sai, đổi mật khẩu, thu hồi phiên | ✅ test_14 |
| F2 | Platform quản lý tenant (tạo/khóa), tenant không gọi được API platform | ✅ test_04 |
| F3 | CRUD người dùng theo vai trò; nhật ký truy cập | ✅ test_04 + audit |
| F4 | CRUD khách hàng theo tenant | ✅ test_01 |
| F5 | Đơn: tạo/sửa nháp → duyệt → gửi hãng (mock) → có mã vận đơn; hủy; lịch sử; lọc/tìm; xuất CSV | ✅ test_09/10 + live T1-000001 |
| F6 | Carrier adapter: 2 adapter (VTP, J&T) qua interface chung, capability khai báo rõ, MOCK gắn nhãn | ✅ test_17/18 |
| F7 | Webhook tenant-aware: thô→queue→normalize→resolve→update+audit; DLQ + replay | ✅ test_05-08b |
| F8 | Import: upload CSV/XLSX → preview → sửa lỗi → approve → tạo đơn theo batch, trạng thái từng dòng | ✅ test_11 |
| F9 | AI gateway mock + policy (AI không vượt auth/tenant/approval) | ✅ test_15 + ai_gateway |
| F10 | Billing: gói + hạn mức chặn thật từ backend + usage | ✅ test_15 |
| F11 | Admin UI đủ màn chính, tiếng Việt, responsive, không hiện secret | ✅ kiểm trình duyệt 14/10 |

## BLOCKED (cần Owner)

- [ ] Credentials J&T thật + lệnh cho phép gọi API thật → mới được test LIVE VERIFIED.
- [ ] Cho phép đọc repo `vip-viettelpost` để tái dùng adapter VTP thật (G05 phần thật).
- [ ] Mọi quyết định deploy/production.
