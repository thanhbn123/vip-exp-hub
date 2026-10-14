# G01 — Việc kế tiếp (CHƯA triển khai, chờ Owner duyệt)

G00 dừng ở giao diện demo. Theo đặc tả mục 5 và 10, G01 là **Universal Webhook Gateway**:

1. Gateway đa hãng, xác thực riêng từng hãng (không giả định chung một sơ đồ xác thực).
2. Lưu bền sự kiện thô (durable raw event persistence) trước khi xử lý.
3. Queue/worker, idempotency, xử lý sự kiện đến sai thứ tự (out-of-order).
4. Retry/backoff, DLQ (hàng đợi sự kiện chết), replay có RBAC + audit.
5. Tách trạng thái hành trình, COD và đối soát thành luồng riêng.

Việc kỹ thuật nối tiếp từ G00:

- Thay mock JSON bằng API nội bộ; giữ nguyên hợp đồng dữ liệu các trường đã dùng ở frontend.
- Parser thật cho XLSX/PDF/ảnh (hiện chỉ CSV đọc thật); lưu mẫu ánh xạ theo khách hàng, có version.
- Tạo đơn thật phải có phê duyệt, phân quyền, idempotency, và kiểm tra lại kết quả khi API timeout.
- Thiết kế bảng dữ liệu theo mục 7 đặc tả (tenant isolation, không coi tracking number là duy nhất toàn hệ).

**Ràng buộc:** chỉ bắt đầu G01 khi Owner có lệnh mới. Không đụng dự án `vip-viettelpost` đang chạy.
