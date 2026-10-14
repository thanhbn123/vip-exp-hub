# PROJECT_AUDIT — VIP Express Hub (khảo sát G00, 14/10/2026)

**Thư mục dự án:** `~/Projects/vip-express-hub` (MacBook, local-first).
**Git:** trước khảo sát CHƯA có; đã `git init` local (không remote) và chốt baseline `fd79d74` làm mốc rollback. DB gateway đã sao lưu ra scratchpad phiên.

## Hiện trạng theo hạng mục

| Hạng mục | Trạng thái | Chi tiết |
|---|---|---|
| Frontend | **DONE** (mức demo) | 11 file HTML (index + 10 trang), design system dùng chung `assets/css/style.css` + `assets/js/app.js` (sidebar, modal, toast, biểu đồ canvas, không CDN). Nghiệm thu G00 cũ: `docs/G00_ACCEPTANCE.md` |
| Backend | **PARTIAL** | Mới có 1 dịch vụ: webhook gateway G01 (`gateway/`, Python stdlib + SQLite, cổng 8898). Chưa có backend nghiệp vụ (đơn, khách, người dùng) |
| Database | **PARTIAL** | SQLite `gateway/du-lieu/gateway.db`: `su_kien_tho`, `van_don`, `hanh_trinh`, `audit`. Chưa có schema tenant/user/order/billing |
| API | **PARTIAL** | Gateway: webhook 5 hãng mô phỏng, su-kien/dlq/van-don/audit/replay. Chưa có API nghiệp vụ |
| Webhook | **DONE** (phạm vi G01, single-tenant) | Xác thực riêng từng hãng, lưu bền thô, queue/worker, idempotency UNIQUE CSDL, out-of-order, retry/backoff, DLQ, replay RBAC + audit. Bộ thử 9/9. **Chưa gắn tenant** |
| Authentication | **NOT STARTED** | Chỉ có khóa API tĩnh demo (viewer/admin) của gateway; chưa có đăng nhập/phiên/người dùng |
| Customer management | **NOT STARTED** | — |
| Order management | **NOT STARTED** (backend) | Frontend có form tạo đơn demo lưu localStorage; chưa có Order Service |
| Carrier integration | **NOT STARTED** (adapter thật) | Chỉ có bộ mô phỏng hãng của gateway. Repo `vip-viettelpost` là DỰ ÁN KHÁC (ngoài thư mục này), G05 sẽ khảo sát riêng khi được phép đọc |
| Existing tests | **PARTIAL** | `gateway/thu/thu_gateway.py` 9 ca (PASS). Frontend kiểm tay có biên bản |
| Environment config | **PARTIAL** | `gateway/cau_hinh.py` (khóa demo trong mã — chấp nhận local, phải chuyển env khi lên máy chủ). Chưa có file env mẫu |

## Chức năng đã hoàn thành — KHÔNG làm lại

1. 10 trang HTML demo + design system (tái sử dụng cho G11).
2. Webhook gateway G01 single-tenant — **nâng cấp lên tenant-aware trong `app/` mới, giữ `gateway/` nguyên trạng** làm bản tham chiếu G01 đã nghiệm thu.
3. Mock data + bộ mô phỏng hãng.

## Khoảng trống chính (đối chiếu brief G01–G13 mới)

Multi-tenant (toàn bộ), auth/RBAC, carrier adapter interface, adapter J&T/VTP, order service + idempotency, import server-side, AI gateway, billing, màn quản trị, bộ thử bảo mật chéo tenant.

## Khảo sát J&T (G04) — đo 14/10/2026 bằng trình duyệt (trang là SPA, fetch tĩnh không đọc được)

| Mục | Trạng thái | Nguồn |
|---|---|---|
| Tài liệu API công khai | **DOCUMENTED** | `open.jtexpress.vn/apiDoc/index` (giao diện tiếng Trung): mục Đơn hàng (tạo/hủy), Tính cước, Nhãn, Tracking, Mã lỗi |
| Cơ chế ký | **DOCUMENTED** | `digest = base64(md5(bizContent-JSON + privateKey))`; headers `apiAccount`, `digest`, `timestamp` (ms, UTC+7); body `bizContent` JSON-string, `application/x-www-form-urlencoded` |
| Endpoint tạo đơn | **DOCUMENTED** | test `https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder`, prod `https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder` (POST) |
| Credentials sandbox | **DOCUMENTED** (công bố ngay trên docs) | apiAccount/privateKey test in sẵn trong tài liệu; nhưng tạo đơn cần thêm `customerCode` + `password` của khách ký hợp đồng |
| Chạy LIVE | **REQUIRES ACCESS** | Cần đăng ký đối tác (đăng ký → xác thực developer → liên调 test → lên sóng) + duyệt của Owner |
| Webhook/callback J&T | **CHƯA ĐỌC HẾT** | Chưa thấy mục webhook ở menu công khai (chỉ 物流轨迹 = tra hành trình); cần đọc thêm/hỏi khi có tài khoản |

## Rủi ro & ràng buộc giữ nguyên

Không ghi đè mã đang chạy; `gateway/` giữ nguyên; DB cũ không xóa; không GitHub remote, không VPS, không API thật khi chưa duyệt.
