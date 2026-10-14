# VIP EXPRESS HUB — PROJECT BLUEPRINT

**Project:** VIP EXPRESS HUB  
**Gate:** G00 — HTML FIRST / UI PROTOTYPE  
**Owner:** VIP ORDER  
**Date:** 2026-10-14  
**Status:** SPECIFICATION — NOT IMPLEMENTED  
**Mode:** LOCAL-FIRST (MacBook), no GitHub, no VPS, no real carrier API  
**Language:** Tiếng Việt

## 1. Mục tiêu sản phẩm

Phát triển trung tâm quản lý chuyển phát nhanh đa hãng dùng chung cho hệ sinh thái VIP ORDER. Bắt đầu bằng Viettel Post, thiết kế có thể mở rộng GHN, GHTK, J&T, BEST và hãng khác mà không phải xây lại lõi. Về sau hỗ trợ nhận file Excel/CSV/PDF/ảnh, trích xuất thông tin và tạo đơn sau bước kiểm tra, duyệt; webhook nhận trạng thái và COD đối soát.

**G00 chỉ dựng giao diện HTML/CSS/JS có dữ liệu mô phỏng và chức năng frontend kiểm chứng được.** Không được mô tả nút demo là kết nối thật.

## 2. Phạm vi G00

Xây 10 màn hình:

| # | Route HTML | Chức năng |
|---|---|---|
| 1 | `pages/dashboard.html` | KPI đơn hàng, giao thành công/thất bại, COD, đồ thị, bộ lọc ngày |
| 2 | `pages/shipments.html` | Danh sách vận đơn đa hãng; tìm kiếm, lọc, phân trang, chi tiết |
| 3 | `pages/create-order.html` | Form người gửi/nhận, hàng hóa, cân nặng, COD, lựa chọn hãng, kiểm tra và lưu nháp demo |
| 4 | `pages/ai-import.html` | Upload → phân tích → ánh xạ cột → kiểm tra/sửa → duyệt tạo đơn demo |
| 5 | `pages/webhooks.html` | Thống kê sự kiện, nhật ký, payload đã che PII, bộ lọc, retry/replay mô phỏng |
| 6 | `pages/carriers.html` | Thẻ nhà vận chuyển, nhiều tài khoản, trạng thái **demo**, cấu hình giả lập |
| 7 | `pages/pricing.html` | So sánh cước minh họa; không nhận là báo giá thực |
| 8 | `pages/cod.html` | COD phải thu, đã nhận, phí, chênh lệch, đối soát demo |
| 9 | `pages/reports.html` | Thống kê và biểu đồ đa hãng, lọc ngày |
| 10 | `pages/settings.html` | Giao diện cấu hình, tài khoản và quyền demo |

`index.html` là trang vào/điều hướng dashboard.

## 3. Thiết kế UI/UX

- Nhận diện VIP ORDER: đỏ `#CC0000`, nền sáng, sidebar tối; không lạm dụng màu đỏ.
- Giao diện tiếng Việt; sidebar, header, tìm kiếm, thông báo, trạng thái, bảng, modal.
- Responsive desktop/tablet/mobile; trạng thái loading, lỗi, rỗng và thành công.
- Thao tác nào mới là mô phỏng phải gắn nhãn **DEMO — CHƯA KẾT NỐI API**.
- Dữ liệu mẫu là hư cấu, không dùng dữ liệu khách hàng thật. Không sử dụng ảnh/logo hãng khi không có tài sản hợp lệ; tên hãng dạng text là đủ.
- Accessibility cơ bản: label input, focus visible, điều khiển bàn phím, độ tương phản phù hợp.

## 4. AI Import — hành trình ưu tiên

### 4.1 Các bước
1. **Tải file:** kéo thả/chọn tệp. UI chấp nhận XLSX/XLS/CSV/PDF/PNG/JPG với kiểm tra tên, loại, dung lượng; không khẳng định hỗ trợ đọc nội dung nếu chưa có parser.
2. **Phân tích:** G00 có thể **đọc CSV thật bằng JS**; dùng bộ dữ liệu fixture minh họa cho định dạng khác và ghi rõ "MÔ PHỎNG — CHƯA ĐỌC NỘI DUNG TỆP".
3. **Ánh xạ cột:** chuẩn hóa `recipient_name`, `recipient_phone`, `recipient_address`, `product_name`, `quantity`, `weight_grams`, `cod_amount`, `declared_value`, `note`.
4. **Kiểm tra/sửa:** kiểm tra trường bắt buộc, số điện thoại định dạng, số tiền không âm, cân nặng >0, tô màu dòng hợp lệ/cần xem xét/lỗi, sửa từng dòng, lọc lỗi, cảnh báo nghi trùng.
5. **Duyệt:** chọn hãng cho từng đơn hoặc nhiều đơn; chọn nhiều dòng; xác nhận duyệt **demo**; không gửi bất kỳ API nào, xuất kết quả CSV demo.

### 4.2 Quy tắc nghiệp vụ
- AI không được tự bịa địa chỉ, số điện thoại, COD hoặc giá trị hàng hóa.
- Tách trạng thái đọc file, kiểm tra, phê duyệt và tạo đơn; G00 chỉ mô phỏng.
- Thiết kế để sau này lưu mapping mẫu file theo từng khách hàng, có version.
- Khi xây backend, tạo đơn thật phải có phê duyệt, quyền hạn, idempotency và kiểm tra kết quả nếu API timeout.

## 5. Webhook Center — UI G00 và yêu cầu cho G01

Trong G00 chỉ hiển thị mock event list, chi tiết JSON đã che thông tin cá nhân, bộ lọc hãng/mã vận đơn/trạng thái, retry/replay demo. Không mở public endpoint và không sửa callback Viettel Post hiện tại.

Yêu cầu kiến trúc cho G01 sau nghiệm thu: Gateway đa hãng, per-carrier authentication, durable raw event persistence, queue/worker, idempotency, out-of-order handling, retry/backoff, DLQ, replay với RBAC và audit. Tách trạng thái hành trình, COD và đối soát. Không giả định cùng một sơ đồ xác thực webhook cho mọi hãng.

## 6. Kiến trúc dài hạn theo 4 tầng

| Tầng | Vai trò |
|---|---|
| **BRAIN** | VIP AI Brain: hiểu file khó, đánh giá chất lượng dữ liệu, dự báo rủi ro; không tự gọi API tạo đơn nếu chưa được cấp quyền |
| **MAIN** | Vận đơn chuẩn hóa, khách hàng, tenant, lô import, phê duyệt, COD, công nợ, phân quyền |
| **TOOL** | Parser CSV/Excel/PDF/OCR, Address Validator, Carrier Adapter, Webhook Gateway, Batch Order Creator, Audit |
| **EXTERNAL** | Viettel Post, GHN, GHTK, J&T, BEST, dịch vụ bản đồ/địa chỉ nếu cần và được phê duyệt |

VIP Express Hub không bị gắn cứng với một mô hình AI. Khi tích hợp VIP AI Brain dùng API/service contract độc lập.

## 7. Định hướng dữ liệu tương lai (chưa làm database ở G00)

`carriers`, `carrier_accounts`, `shipments`, `shipment_tracking`, `webhook_events`, `webhook_deliveries`, `webhook_dead_letters`, `import_batches`, `import_files`, `import_rows`, `mapping_templates`, `order_approvals`, `cod_settlements`, `audit_logs`. Cần thiết kế tenant/company isolation, reference giữa đơn nội bộ và vận đơn hãng, không coi tracking number duy nhất toàn hệ thống.

## 8. Cấu trúc thư mục

```text
vip-express-hub/
├── index.html
├── pages/
│   ├── dashboard.html
│   ├── shipments.html
│   ├── create-order.html
│   ├── ai-import.html
│   ├── webhooks.html
│   ├── carriers.html
│   ├── pricing.html
│   ├── cod.html
│   ├── reports.html
│   └── settings.html
├── assets/
│   ├── css/
│   ├── js/
│   └── images/
├── mock/
│   ├── shipments.json
│   ├── carriers.json
│   ├── webhook-events.json
│   └── import-sample.csv
├── docs/
│   ├── G00_ACCEPTANCE.md
│   └── G01_NEXT_STEPS.md
└── README.md
```

Có thể tổ chức CSS/JS thành module chia sẻ; tránh copy cùng logic ở 10 trang. Khuyến nghị chạy bằng local static server để `fetch` JSON hoạt động. Không được yêu cầu dịch vụ cloud để xem demo.

## 9. Cổng nghiệm thu G00

1. Có 10 trang theo danh sách, điều hướng đúng và không link gãy.
2. Layout đẹp, đồng bộ và responsive ở tối thiểu 3 kích thước màn hình.
3. Dashboard dùng dữ liệu fixture nhất quán.
4. Danh sách vận đơn có search/filter/pagination hoạt động bằng JS.
5. Form tạo đơn có validation và lưu nháp demo, không gọi API.
6. AI Import có 5 bước; CSV đọc thực tế nếu triển khai parser; các định dạng chưa đọc ghi nhãn mô phỏng rõ.
7. Mapping, sửa dòng, kiểm tra lỗi, chọn hãng, phê duyệt demo hoạt động.
8. Webhook Center có chi tiết sự kiện, lọc, retry/replay mô phỏng.
9. COD, hãng, báo cáo, cấu hình có dữ liệu minh họa dễ hiểu.
10. Console không có lỗi nghiêm trọng; không lộ bí mật; không lưu PII thật.
11. Có hướng dẫn mở local, test report, danh sách nút chưa kết nối và ảnh chụp màn hình nếu môi trường cho phép.
12. **DỪNG TẠI G00**, không tự đi G01, không GitHub, không VPS, không production.

Báo cáo theo cấu trúc: `PROJECT | GATE | STATUS | IMPLEMENTED | DEMO_ONLY | TEST_EVIDENCE | OPEN_ISSUES | RISKS | NEXT_GATE`. Chỉ tuyên bố PASS khi có bằng chứng kiểm thử.

## 10. Roadmap sau G00 (chưa triển khai)

- **G01:** Universal Webhook Gateway (xác thực, lưu sự kiện, queue, mapping, DLQ).
- **G02:** Tái dùng adapter/API Viettel Post; kiểm tra mã nguồn và webhook hiện hành, không ảnh hưởng production.
- **G03:** Shipment management chung và tạo đơn đa hãng.
- **G04:** Adapter GHN/GHTK/J&T/BEST theo quyền truy cập thực tế.
- **G05:** COD, phí, đối soát và cảnh báo tài chính.
- **G06:** Tích hợp VIP AI Brain phục vụ vận hành.
- **G07:** Import file thật (Excel, CSV, PDF, ảnh) → chuẩn hóa → duyệt → batch create qua Carrier API.

**Chú ý:** Có thể triển khai G07 sau G03 cho Viettel Post mà không cần chờ tất cả hãng ở G04.

---

# APPENDIX A — LỆNH DÁN VÀO CLAUDE DESKTOP

```text
Bạn là PROJECT CONTROLLER cho dự án VIP EXPRESS HUB.

Nhiệm vụ: Bắt đầu dự án mới hoàn toàn ở MacBook theo G00 — HTML FIRST.

1) Đọc file đặc tả VIP_EXPRESS_HUB_PROJECT_G00.md mà tôi đính kèm / chỉ đường dẫn. Đọc toàn bộ trước khi viết code và lấy file này làm yêu cầu nghiệm thu G00.
2) Khảo sát thư mục hiện hành và đề xuất vị trí workspace local phù hợp (ưu tiên ~/Projects nếu có, nếu chưa có thì tạo). Tạo MỘT thư mục mới tên `vip-express-hub`; kiểm tra tồn tại trước khi tạo. Nếu đã tồn tại, KHÔNG ghi đè hay xóa: kiểm tra trạng thái và báo cáo Owner trước khi tiếp tục.
3) Sao chép đặc tả vào `vip-express-hub/docs/PROJECT_SPEC_G00.md` để lưu cùng dự án. Không thay đổi nội dung đặc tả gốc.
4) Tạo cấu trúc thư mục theo mục 8; dựng HTML/CSS/JS hoạt động local, đồng bộ layout và mock data. Ưu tiên thực hiện dashboard, ai-import và webhooks trước, sau đó hoàn thành 7 màn hình còn lại.
5) Dùng JS để các nút demo có hành vi rõ ràng. Đọc CSV thật nếu có parser, các định dạng chưa đọc được phải thông báo không hỗ trợ trong G00 — tuyệt đối không giả vờ đã AI đọc tệp.
6) Tạo dữ liệu giả không chứa thông tin khách thật, có kiểm tra nhập liệu, lọc, phân trang, chỉnh sửa, demo duyệt đơn. Không gọi API hãng vận chuyển, không gọi VIP AI Brain, không tạo đơn thật, không sửa dự án `vip-viettelpost`.
7) Chạy local server (ví dụ python3 -m http.server trên localhost với port còn trống), tự kiểm thử các trang và thao tác, chụp ảnh UI nếu công cụ có hỗ trợ. Không sử dụng port dịch vụ hiện có nếu bị chiếm.
8) Viết README.md và docs/G00_ACCEPTANCE.md với kết quả thực tế; nếu test thất bại, sửa và kiểm thử lại. Không tự nhận PASS khi còn lỗi nghiêm trọng.
9) Không git push, không khởi tạo remote, không deploy VPS, không chỉnh production, không lưu API token/secret.
10) Khi G00 đạt, MỞ đường dẫn local để Owner xem và DỪNG. Báo cáo vị trí thư mục, URL local, trang đã có, test PASS/FAIL, những phần chỉ là demo và các tồn đọng. Chỉ triển khai G01 khi Owner có lệnh mới.

Bắt đầu bằng kiểm tra workspace và khởi tạo thư mục mới an toàn. Sau đó chủ động hoàn thành toàn bộ G00, không hỏi lại các quyết định đã được chốt trong đặc tả.
```
