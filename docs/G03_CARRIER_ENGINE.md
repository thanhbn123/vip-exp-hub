# G03 — CARRIER INTEGRATION ENGINE (phần thuần local)

Làm được mà **không cần quyết định nào của Owner**. Phần cần credentials thật vẫn BLOCKED.

## 1. Hợp đồng adapter

`app/adapter.py::CarrierAdapter` — 7 hàm chuẩn: `createOrder` · `cancelOrder` · `getOrder` ·
`trackOrder` · `getShippingFee` · `getShippingLabel` · `normalizeTrackingStatus`.

Mỗi adapter khai `CAPABILITIES` (7 khóa + `webhook`), `CHO_PHEP_LIVE` và **`KHOA_CHONG_TRUNG`**
(hãng có khóa chống trùng riêng cho createOrder hay không — quyết định việc được thử lại hay không).

Ba kết cục phân biệt rõ, không gộp:

| Kết cục | Nghĩa | Order Service làm gì |
|---|---|---|
| `ok=True` | hãng xác nhận | `da_gui` + lưu mã vận đơn |
| `ok=False, timeout=False` | hãng **từ chối** (biết chắc hỏng) | lùi về `da_duyet`, báo lỗi |
| `ok=False, timeout=True` | **không biết** kết quả | giữ `dang_gui` + bật cờ `can_doi_soat_ket_qua` |

## 2. Bảng ánh xạ trạng thái (`app/trang_thai_hang.py`)

**J&T — mã thật, chép từ tài liệu** `open.jtexpress.vn/apiDoc/logistics/statusFeedback` và
`/apiDoc/logistics/query` (đọc bằng trình duyệt 14/10/2026; trang là SPA nên fetch tĩnh không đọc được):

| scanTypeCode | Ý nghĩa | → trạng thái chuẩn |
|---|---|---|
| 103 | Order Placed | `cho_lay` |
| 106 | Picked Up | `lay_hang` |
| 109 / 110 / 112 | Departure / Arrival / On Delivery | `dang_giao` |
| 113 | Delivered | `giao_thanh_cong` |
| 118 | Delivery Problem | `giao_that_bai` |
| 116 / 117 | Returning / Returned Sign | `hoan_hang` |
| 104 / 105 / 120 / 121 | Pickup Failure / Cancel / Return Problem / FINISH | **chỉ ghi nhận**, không đổi trạng thái |

Nguyên tắc: mã **chưa chắc nghĩa thì không đổi trạng thái** — thà thiếu còn hơn cập nhật sai đơn.
Mã **lạ** (không có trong tài liệu) cũng không ném lỗi và không đổi gì, chỉ ghi audit `polling_ma_la`.

**Viettel Post:** chưa có tài liệu trong tay (repo `vip-viettelpost` chưa được phép đọc) → chỉ ánh xạ
các mã do **bộ mô phỏng của chính dự án này** sinh ra. Không bịa mã của hãng thật.

### Cần xác minh khi có tài khoản thật
- Ví dụ request trong tài liệu J&T dùng `scanTypeCode = 10`, **không** có trong danh sách mã được liệt kê.
- Ý nghĩa chính xác của `121 FINISH` (kết thúc theo hướng giao thành công hay hoàn hàng).

### Đính chính capability J&T
Lần đọc đầu em khai `webhook: False` vì chỉ nhìn menu cấp 1. Đọc kỹ thì mục 物流轨迹 có trang con
**轨迹回传** — hãng chủ động đẩy hành trình về URL do khách cung cấp. Đã sửa thành `webhook: True`,
và cho `seed_providers()` chạy lúc khởi động server để đổi capability lan được xuống CSDL.

## 3. Khung retry/timeout (`app/transport.py`)

Điểm quan trọng nhất: **không phải thao tác nào cũng thử lại được.**

- Chỉ đọc (`getOrder`, `trackOrder`, `getShippingFee`, `getShippingLabel`) → thử lại 2–3 lần, backoff nhân đôi.
- `createOrder` / `cancelOrder` → **mặc định KHÔNG thử lại**, vì thử lại mù có thể tạo đơn trùng ở hãng.
  Chỉ mở thử lại khi hãng có khóa chống trùng của chính nó. J&T: `txlogisticId` — tài liệu ghi
  *"不支持重复"* (không hỗ trợ trùng) → `KHOA_CHONG_TRUNG = True`. VTP chưa có tài liệu → `False`.
- `LoiVinhVien` (sai tham số/chữ ký) → không thử lại lần nào.

## 4. Tracking polling fallback (`app/polling.py`)

Dùng khi hãng không đẩy webhook, hoặc webhook đang hỏng.

- Chỉ hỏi đơn **đang chạy** (`da_gui` + có mã vận đơn + hành trình ∈ cho_lay/lay_hang/dang_giao).
- Gom lô theo giới hạn thật của hãng: **J&T tối đa 30 vận đơn mỗi lượt tra** (theo tài liệu);
  hãng chưa rõ thì dùng mức dè dặt 20.
- Đi qua **đúng đường cập nhật của webhook**: normalize → resolve tenant+đơn → rank guard → audit.
  Không có đường tắt, nên không thể kéo lùi trạng thái.
- `chi_hang_khong_webhook=True` → bỏ qua hãng đã có webhook (đúng nghĩa fallback).
- **Không tự chạy theo lịch.** Phải có người gọi `POST /api/v2/polling/chay` (quyền
  `tenant.hang.quan_ly`) hoặc bật `BatDauNen` thủ công.

## 5. Bộ thử (`app/thu/thu_g03.py`) — 23 test

Nhóm **A (8 test)** chạy với **mọi adapter đã đăng ký**, nên thêm hãng mới mà khai thiếu là hỏng ngay:
đủ 7 hàm chuẩn · khai đủ capability · capability khai `False` thì trả "không hỗ trợ" tử tế (không
ném lỗi, không giả vờ làm được) · capability `True` thì chạy được ở mock · LIVE bị khóa ở mọi hãng ·
mock **tự nhận là mock** · phân biệt được ba kết cục · normalize trả trạng thái hợp lệ và mã lạ
không đổi trạng thái.

Nhóm **B (3)** bảng ánh xạ · **C (6)** retry/timeout · **D (6)** polling.

## 6. Còn BLOCKED

Adapter thật cho J&T và Viettel Post — cần Owner cấp credentials và cho phép đọc repo
`vip-viettelpost`. Khung đã sẵn: chỉ cần thay lớp transport mock bằng lớp gọi HTTP thật, giữ nguyên
interface, bảng ánh xạ và bộ thử hợp đồng.
