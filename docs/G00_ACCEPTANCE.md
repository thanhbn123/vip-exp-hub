# G00_ACCEPTANCE — VIP Express Hub

- **PROJECT:** VIP EXPRESS HUB
- **GATE:** G00 — HTML FIRST / UI PROTOTYPE
- **STATUS:** PASS (frontend demo, local-first) — chờ Owner nghiệm thu
- **Ngày kiểm:** 14/10/2026, trên MacBook, chạy qua `python3 -m http.server 8899 --bind 127.0.0.1`, kiểm bằng trình duyệt Chromium nhúng của Claude Code (desktop ~800px, mobile 375×812).

## IMPLEMENTED (chạy thật ở frontend)

- 11 file HTML: `index.html` (chuyển hướng Dashboard) + 10 trang theo đặc tả mục 2.
- Khung dùng chung (`assets/js/app.js`, `assets/css/style.css`): sidebar, header, banner DEMO, toast, modal (đóng bằng nút/nhấn nền/Escape), biểu đồ canvas tự vẽ — **không dùng CDN**, xem demo không cần mạng ngoài.
- Dashboard: 4 KPI, biểu đồ đường/tròn/cột, bộ lọc 7/14/30 ngày + lọc hãng, bảng đơn mới nhất.
- Vận đơn: tìm kiếm (mã đơn/vận đơn/người nhận/SĐT), lọc hãng + trạng thái, phân trang rút gọn, modal chi tiết; nhận tham số `?q=` từ ô tìm kiếm toàn cục.
- Tạo đơn: validation từng trường (SĐT 10 số đầu 0, cân nặng >0, COD/giá trị khai không âm), lưu nháp vào localStorage, danh sách nháp, xóa nháp.
- AI Import 5 bước: kéo thả/chọn tệp (kiểm tên, loại, ≤10MB) → phân tích (**CSV đọc nội dung thật bằng parser JS tự viết**, hỗ trợ ô trong nháy kép) → ánh xạ cột 9 trường chuẩn (tự khớp theo tên, chặn khi thiếu trường bắt buộc) → kiểm tra/sửa từng dòng qua modal, tô màu hợp lệ/cần xem/lỗi, cảnh báo nghi trùng (SĐT+địa chỉ), lọc dòng lỗi, loại dòng lỗi → duyệt demo: chọn nhiều dòng, gán hãng lẻ/hàng loạt, modal xác nhận, xuất `ket-qua-duyet-demo.csv`.
- Webhook Center: 4 KPI, bảng 60 sự kiện mô phỏng, lọc hãng/trạng thái xử lý/mã vận đơn, phân trang, modal payload JSON **đã che PII**, Retry/Replay mô phỏng (Retry đổi trạng thái lỗi→thành công trong phiên).
- Đối soát COD: KPI phải thu/đã nhận/phí/chênh lệch, lọc, nút chạy đối soát demo.
- So sánh cước: tính theo cân nặng + tuyến từ biểu hệ số **hư cấu**, xếp hạng rẻ nhất, cảnh báo "không phải báo giá thực".
- Báo cáo: biểu đồ sản lượng + COD theo hãng, bảng tổng hợp, lọc ngày.
- Nhà vận chuyển: 5 thẻ hãng (text, không dùng logo hãng), nhiều tài khoản sandbox giả lập, modal cấu hình giả lập.
- Cấu hình: 3 tab (chung / tài khoản & quyền / thông báo), thêm/khóa người dùng demo.
- Accessibility cơ bản: label cho input, `aria-label`/`aria-current`/`role=dialog`, focus-visible, đóng modal bằng Escape, `aria-live` cho toast.

## DEMO_ONLY (mô phỏng, có nhãn trên giao diện)

Tạo đơn thật, duyệt đơn, retry/replay webhook, đối soát COD, lưu cấu hình, bảng cước, tài khoản/quyền, thông báo. Tệp **XLSX/XLS/PDF/ảnh chưa được đọc nội dung** — luồng chạy bằng fixture và hiện cảnh báo đỏ "MÔ PHỎNG — CHƯA ĐỌC NỘI DUNG TỆP". Mọi nút mô phỏng gắn nhãn "DEMO — CHƯA KẾT NỐI API".

## TEST_EVIDENCE (đo thực tế 14/10/2026)

| # | Phép thử | Kết quả |
|---|---|---|
| 1 | 11 link tĩnh href/src quét bằng script — đối chiếu file tồn tại | 0 link gãy (phạm vi: link tĩnh trong index + 10 trang; link sinh bằng JS kiểm riêng ở #5) |
| 2 | Console lỗi khi mở từng trang (10 trang + index, qua localhost:8899) | 0 lỗi console trên mọi trang đã mở |
| 3 | Dashboard: KPI khớp mock (71 đơn/30 ngày, 30 thành công, 2 thất bại, COD 16.580.000 ₫ demo); đổi bộ lọc vẽ lại | Đạt |
| 4 | AI Import trọn luồng với mock/import-sample.csv (14 dòng, 3 lỗi cố ý: SĐT sai, thiếu tên, COD âm) | Phân tích 9 cột/14 dòng; kiểm tra báo đúng 11 hợp lệ · 3 lỗi; loại lỗi; chọn 11 dòng, gán Viettel Post hàng loạt; duyệt demo + xuất CSV |
| 5 | Vận đơn: `?q=VTP` từ tìm kiếm toàn cục | Lọc đúng 17 đơn VTP; phân trang/lọc hoạt động |
| 6 | Tạo đơn: submit form rỗng / SĐT "012" | Chặn với 9 trường lỗi, focus trường đầu; dữ liệu hợp lệ lưu 1 nháp localStorage |
| 7 | Webhook: modal chi tiết EVT-00055 | Payload hiện PII đã che (`09******68`, địa chỉ `***`) |
| 8 | COD: chạy đối soát demo | 9 dòng chưa đối soát → 0 dòng |
| 9 | So sánh cước: 500g nội miền | 5 hãng ra kết quả, gắn nhãn minh họa |
| 10 | Cấu hình: chuyển 3 tab, bảng 4 người dùng demo | Đạt |
| 11 | Responsive mobile 375×812 | KPI 1 cột, hamburger mở sidebar, bấm ngoài đóng; nhãn trục biểu đồ giãn theo bề rộng (đã sửa 1 lỗi chồng nhãn trong lúc kiểm) |
| 12 | index.html chuyển hướng | Về dashboard.html |

Phạm vi kiểm: các phép thử trên chạy trong trình duyệt Chromium nhúng ở 2 kích thước (~800px và 375px); **chưa đo** Safari/Firefox và kích thước tablet 768px riêng (CSS có breakpoint 768/1024 nhưng chỉ nghiệm bằng 2 cỡ trên).

## OPEN_ISSUES

1. Tablet 768px và Safari/Firefox chưa kiểm bằng mắt (chỉ có breakpoint CSS).
2. Parser CSV chưa hỗ trợ encoding ngoài UTF-8 (tệp Excel xuất CP1258 có thể lỗi dấu).
3. Nháp tạo đơn chỉ nằm trong localStorage của trình duyệt — xóa dữ liệu trình duyệt là mất (chấp nhận ở G00).
4. Dữ liệu mock cố định mốc 14/10/2026 — sau ngày này bộ lọc "7 ngày qua" vẫn tính quanh mốc đó (cố ý, để demo ổn định).

## RISKS

- Người xem có thể tưởng số liệu là thật → đã chặn bằng banner vàng mọi trang + nhãn DEMO từng khối + chữ trong footer sidebar.
- Không có rủi ro API/bí mật: không khóa API, không endpoint, không dữ liệu khách thật trong repo.

## NEXT_GATE

G01 — Universal Webhook Gateway (xem `docs/G01_NEXT_STEPS.md`). **Chỉ bắt đầu khi Owner có lệnh mới.**
