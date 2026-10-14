# VIP Express Hub — G00 (HTML FIRST)

Trung tâm quản lý chuyển phát nhanh đa hãng cho hệ sinh thái VIP ORDER.
**Đây là bản G00: chỉ giao diện HTML/CSS/JS với dữ liệu mô phỏng (demo), chưa kết nối API nào.**

- Đặc tả gốc: `docs/PROJECT_SPEC_G00.md`
- Báo cáo nghiệm thu G00: `docs/G00_ACCEPTANCE.md`
- **G01 — Universal Webhook Gateway (local)**: mã ở `gateway/`, báo cáo `docs/G01_ACCEPTANCE.md`.
  Chạy: `python3 gateway/server.py` (cổng 8898) → bắn demo `python3 gateway/mo_phong_hang.py` → bộ thử `python3 gateway/thu/thu_gateway.py`.
  Trang Webhook Center có ô "Nguồn" để đọc gateway thật (khóa demo: `demo-viewer-key` / `demo-admin-key`).

## Cách mở demo trên máy local

Trang dùng `fetch` đọc JSON trong `mock/`, nên **phải chạy qua local server**, không mở file trực tiếp:

```bash
cd ~/Projects/vip-express-hub
python3 -m http.server 8899
```

Rồi mở trình duyệt tại: `http://localhost:8899/` (tự chuyển vào Dashboard).
Nếu cổng 8899 bận, đổi số cổng khác còn trống.

## 10 màn hình

| Trang | Đường dẫn |
|---|---|
| Dashboard | `pages/dashboard.html` |
| Vận đơn | `pages/shipments.html` |
| Tạo đơn | `pages/create-order.html` |
| AI Import (5 bước) | `pages/ai-import.html` |
| Webhook Center | `pages/webhooks.html` |
| Nhà vận chuyển | `pages/carriers.html` |
| So sánh cước | `pages/pricing.html` |
| Đối soát COD | `pages/cod.html` |
| Báo cáo | `pages/reports.html` |
| Cấu hình | `pages/settings.html` |

## Những gì là THẬT và những gì là DEMO ở G00

**Chạy thật (frontend):** điều hướng, tìm kiếm, lọc, phân trang, validation form, sửa dòng import,
**đọc nội dung tệp CSV thật bằng JS**, vẽ biểu đồ canvas (không CDN), lưu nháp đơn vào localStorage,
xuất CSV kết quả duyệt demo.

**Chỉ mô phỏng (có nhãn DEMO trên giao diện):** tạo đơn, duyệt đơn, retry/replay webhook,
đối soát COD, cấu hình hãng, bảng cước (số liệu hư cấu), tài khoản/quyền, thông báo.
Tệp XLSX/XLS/PDF/ảnh **chưa được đọc nội dung** — luồng chạy bằng dữ liệu minh họa và ghi rõ
"MÔ PHỎNG — CHƯA ĐỌC NỘI DUNG TỆP".

## Ranh giới an toàn

- Không gọi API hãng vận chuyển nào; không tạo đơn thật.
- Không mở endpoint webhook công khai; không đụng callback Viettel Post hiện có.
- Không chứa khóa API, token hay dữ liệu khách hàng thật — mọi tên, SĐT, địa chỉ là hư cấu.
- Không đẩy GitHub, không triển khai VPS ở G00.

## Cấu trúc

```text
index.html            — trang vào, chuyển hướng Dashboard
pages/                — 10 màn hình
assets/css/style.css  — bộ khung giao diện dùng chung
assets/js/app.js      — sidebar/header, modal, toast, biểu đồ canvas, tiện ích
mock/                 — shipments.json, carriers.json, webhook-events.json, import-sample.csv
docs/                 — đặc tả, nghiệm thu, bước kế tiếp
```
