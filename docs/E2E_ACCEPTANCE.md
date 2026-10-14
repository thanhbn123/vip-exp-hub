# NGHIỆM THU E2E — luồng đầu-đến-cuối qua HTTP thật

Đo ngày **15/10/2026**, MacBook. `app/thu/chay_e2e.sh` → **41/41 phép đo đạt**, mã thoát 0.

## 1. Luồng được đo — đúng sơ đồ chủ dự án vẽ

```
ĐĂNG NHẬP ──► CHỌN TENANT ──► IMPORT CSV ──► KIỂM TRA DỮ LIỆU ──► TẠO ĐƠN NHÁP
                                                                        │
                        ┌───────────────────────────────────────────────┘
                        ▼
                  DUYỆT / TỪ CHỐI ──► CHỌN HÃNG (J&T / Viettel Post)
                        │
                        ▼
              GỬI QUA ADAPTER MOCK ──► NHẬN WEBHOOK MOCK ──► CẬP NHẬT TRẠNG THÁI
                        │                                             │
                        └──────────────► HIỂN THỊ LỊCH SỬ VẬN ĐƠN ◄───┘
```

## 2. Vì sao phải có bộ thử này — bộ thử cũ không phủ chỗ nào

430 ca unittest gọi **hàm trực tiếp**. Chúng không đi qua `server.py`, nên **không phủ**: bảng
định tuyến, mã HTTP trả về, chốt CSRF, chốt quyền ở tầng HTTP, thứ tự nhánh route, và việc
`_doc_json` có chặn đúng kiểu hay không. Cắm 12 route mà không đo qua HTTP chính là thứ
`CLAUDE.md` §12.1 cấm: tin một thứ mà chưa kiểm nó.

## 3. Nền cô lập — và vì sao phải cô lập

`chay_e2e.sh` tạo một thư mục tạm riêng (`mktemp -d`), chạy migration + seed trong đó, mở máy
chủ trên **một cổng rỗi lấy ngẫu nhiên** (thử trước xem có rỗi không), chạy bộ thử, rồi tắt máy
chủ **theo đúng PID đã giữ lúc khởi động** (`CLAUDE.md` §16.7 — không bao giờ tắt theo mẫu tên)
và xoá sạch thư mục tạm.

Bộ thử này tạo tenant, tài khoản hãng, đơn và sự kiện webhook **thật**. Chạy nó lên
`app/du-lieu/` là làm bẩn dữ liệu đang dùng.

## 4. Những gì phép đo này bắt được — kể cả lỗi của chính nó

Trước khi tin kết quả, bộ thử này đã tự phơi ra **5 lỗi của chính nó**. Ghi lại vì đây đúng là
§12.1: thứ dùng để kiểm chứng phải được kiểm trước khi tin.

| # | Bộ thử tưởng | Thật ra |
|---|---|---|
| 1 | "Tạo tài khoản hãng thứ 2 hỏng" | HTTP **402** là **hạn mức gói Miễn phí đang chạy đúng** (1 kết nối hãng). Nay đo luôn điều đó rồi mới nâng gói |
| 2 | Trạng thái dòng import là `hop_le`/`canh_bao` | Tên thật là `VALID` / `NEEDS_REVIEW` / `INVALID` — lấy từ máy, không từ trí nhớ |
| 3 | "Không chặn tiêm công thức" | Hàm gọi của chính bộ thử **cắt body còn 80 byte** nên mất ô công thức |
| 4 | "`tu-choi` trả 200 mà không đổi gì" | "Bị từ chối" **không** là giá trị `trang_thai` mới — AG-02 cố ý mô hình hoá là `trang_thai='nhap'` + `ly_do_tu_choi` khác NULL. CSDL có `ly_do_tu_choi`, `tu_choi_boi`, `tu_choi_luc` đủ cả |
| 5 | "Webhook hợp lệ bị 429 — trần sai" | **Thứ tự bộ thử sai**: 14 lượt sai chữ ký trước đó đã cạn ngân sách của chính mã webhook đó. Trần chạy đúng. Nay đo lượt hợp lệ **trước** đợt lụt |

Và một ca nữa không phải lỗi mà là thiết kế đúng: chạy bằng `python3 -I` thì `cryptography`
không nạp được, và hệ **từ chối chạy** kèm thông điệp rõ thay vì âm thầm hạ xuống mã hoá yếu.

## 5. 41 phép đo — nhóm theo bước

| Bước | Phép đo | Điểm đáng nêu |
|---|---|---|
| 0. Dựng nền | 7 | Ngữ cảnh tenant giải từ **phiên**, không từ body; hạn mức gói chặn kết nối hãng thứ 2 (402) |
| 3–4. Import | 3 | CSV 3 dòng → `VALID`/`VALID`/`NEEDS_REVIEW`; xuất ra **0 ô** còn mở đầu bằng `= + - @` |
| 5. Đơn nháp | 8 | Phủ R04 R05 R06 R09 R10 R11; `PUT mat-hang` ra tổng 500 g / 250 000 đ (số nguyên, cấm float) |
| 6. Duyệt / từ chối | 3 | Thiếu lý do → **400**; từ chối ghi đủ lý do + người + mốc |
| 7–8. Gửi hãng | 4 | Mã vận đơn mock sinh ra; `/nhan` trả `nhan_that=False` — giao diện không dám in thứ không phải vận đơn |
| 9. Webhook | 8 | Chữ ký đúng → **202** → xử `xong` → đơn đổi sang `dang_giao`; gửi lại cùng `event_id` → **1** sự kiện, không phải 2; sự kiện **đến muộn** không đẩy trạng thái lùi; 14 lượt sai chữ ký → **429**; trần khoanh theo **từng** mã webhook |
| 10–11. Trạng thái + lịch sử | 5 | Đối soát máy ra `da_vao` qua `getOrder`; đối soát **tay** ghi `nguon=nguoi`; đối soát tay đơn đã gửi → **409**; hành trình **7 mốc, hai trục** `nghiep_vu` + `giao_van` |
| G06 | 3 | Cột soát phơi ra; lọc `?can_soat=1`; replay ID không có → **404** (không phải 409 — 409 sẽ cho dò ID) |

## 6. Cái gì NẰM NGOÀI phép đo này

- **Adapter MOCK toàn bộ.** Cả 5 hãng `CHO_PHEP_LIVE=False`. Chưa gọi API thật, chưa tạo đơn vận chuyển thật.
- **Một tiến trình, SQLite, `127.0.0.1`.** Không phủ VPS, PostgreSQL, nhiều worker, proxy thật.
- **Không có trình duyệt.** Bộ thử này bắn HTTP; DOM/CSS/bố cục là tầng 3 của `thu_frontend`, **chưa tự động hoá**.
- **Dữ liệu nhỏ**: 3 đơn, 1 batch 3 dòng, 2 sự kiện webhook.
- **Timeout của hãng phải ép bằng SQL** để dựng ca đơn mắc ở `dang_gui` — không có cách nào bắt adapter mock timeout từ bên ngoài. Ghi ra vì đó là chỗ bộ thử chạm vào CSDL thay vì đi qua cửa thật.
- **4 đường còn khai `CHỜ BACKEND`** nên đo được là **404**, cố ý: `GET /webhook/su-kien/<id>` · `GET/PUT /import/<id>/anh-xa-cot` · `GET /import/tong-hop` · `POST /tai-khoan-hang/<id>/kiem-ket-noi`.

## 7. Chạy lại

```sh
cd ~/Projects/vip-express-hub && sh app/thu/chay_e2e.sh
```

Mã thoát 0 là đạt. Nền tạm tự xoá, kể cả khi bộ thử hỏng giữa đường (`trap ... EXIT`).
