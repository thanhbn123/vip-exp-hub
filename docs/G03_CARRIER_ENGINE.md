# G03 — CARRIER INTEGRATION ENGINE (phần thuần local)

Làm được mà **không cần quyết định nào của Owner**. Phần cần credentials thật vẫn BLOCKED.

## 1. Hợp đồng adapter

`app/adapter.py::CarrierAdapter` — 8 hàm chuẩn: `createOrder` · `cancelOrder` · `getOrder` ·
`trackOrder` · `getShippingFee` · `getShippingLabel` · `normalizeTrackingStatus` ·
**`getCapabilities`** (thêm 14/10/2026 — hợp đồng SHARED_CONTRACTS mục 4 đòi mà trước đó chưa có).

`getCapabilities()` mô tả **một thể hiện** adapter: `ma_hang` · `ten_hang` · `chuc_nang` ·
`moi_truong` · `la_mock` · `live_mo` · `khoa_chong_trung` · `createOrder_duoc_thu_lai` ·
`ma_trang_thai_da_biet` · `so_ma_loi_da_biet`. Hai hàm cũ **giữ nguyên**, không phá code đang
gọi: `capability(ten)` hỏi một khóa, `danh_sach_hang()` xem mọi **lớp** đã đăng ký. Test F2 bắt
ba đường này phải nói giống nhau — lệch nhau là hỏng im lặng. `chuc_nang` trả **bản sao**: sửa
vào đó không đụng `CAPABILITIES` của lớp.

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

**Viettel Post:** chưa có tài liệu hãng trong tay → chỉ ánh xạ các mã do **bộ mô phỏng của chính
dự án này** sinh ra. Không bịa mã của hãng thật.
*Sửa 14/10/2026:* câu cũ ghi lý do là *"repo `vip-viettelpost` chưa được phép đọc"*. Owner đã cho
phép và repo **đã đọc** (chỉ đọc) — trong đó `STATUS_MAP = {}`, không có mã trạng thái VTP nào.
Nút thắt thật là **tài liệu Partner API + credentials**, không phải quyền đọc repo. Xem
[docs/VIETTELPOST_REUSE_AUDIT.md](VIETTELPOST_REUSE_AUDIT.md).

### Cần xác minh khi có tài khoản thật
- **Tài liệu J&T tự mâu thuẫn với ví dụ của chính nó** (đọc lại 14/10/2026). Bảng tham số liệt kê
  bộ mã 103…121; nhưng ví dụ trả lời ngay dưới bảng — ở cả `/logistics/query` lẫn
  `/logistics/statusFeedback` — dùng một bộ mã khác hẳn: `10` "Nhận hàng/快件揽收", `50` "Gửi hàng",
  `92` "Hàng đến", `94` "Quét phát hàng", `100` "Ký nhận", `110` "Quét kiện vấn đề".
  Nguy nhất là **`110`**: bảng ghi *Arrival* (đang giao), ví dụ ghi *kiện vấn đề* — hai nghĩa ngược
  chiều trên cùng một số. Hiện **giữ theo bảng tham số** (phần chuẩn tắc), vì bộ mã trong ví dụ rõ
  ràng là hệ đánh số khác (ví dụ ghi `10` = đã lấy hàng, bảng ghi `106`).
  *Rủi ro cố ý chịu, ghi ra theo §12.1:* nếu hãng thật đẩy theo bộ mã của ví dụ thì đơn có vấn đề
  sẽ bị hiểu thành "đang giao". Rank guard không bị kéo lùi (hạng 3 < hạng 4) nên không hỏng dữ
  liệu, nhưng đơn có vấn đề **sẽ không nổi lên**.
- Ý nghĩa chính xác của `121 FINISH` (kết thúc theo hướng giao thành công hay hoàn hàng).
- Mã lỗi cho **vượt hạn mức gọi**: bảng mã lỗi công khai không có mã nào cho rate limit, nên
  `QUA_HAN_MUC` của J&T hiện chỉ đến từ HTTP 429.

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

## 3b. Lỗi hãng chuẩn hóa (`app/loi_hang.py`) — thêm 14/10/2026

`NormalizedCarrierError`: `ma_chuan` · `ma_goc_hang` · `thong_diep` · `co_the_thu_lai`, kèm
`hang` · `thao_tac` · `http_status` · `tho`. Order Service chỉ cần đọc hai trường đầu tiên và
`co_the_thu_lai` — nó **không** phải biết mã riêng của hãng nào.

Tám mã chuẩn: `XAC_THUC_HONG` · `THAM_SO_SAI` · `QUA_HAN_MUC` · `HET_GIO` · `HANG_TU_CHOI` ·
`DON_TRUNG` · `KHONG_TIM_THAY` · `KHONG_RO`. Mã chuẩn lạ **ném `ValueError`** chứ không đi tiếp.

**`co_the_thu_lai` dùng danh sách TRẮNG** — chỉ `HET_GIO` và `QUA_HAN_MUC`. Đây là *ngoại lệ chính
đáng* mà chính §12.2 nêu sẵn; câu hỏi phân biệt của §12.2 trả lời rõ: quên một loại khỏi danh sách
trắng ⇒ không thử lại ⇒ chỉ mất tiện; dùng danh sách đen mà quên một loại ⇒ thử lại mù thao tác
ghi ⇒ **đơn trùng ở hãng**. `KHONG_RO` mặc định **không** thử lại. Hàm dựng cho phép siết chặt
(True→False) nhưng **cấm nới lỏng** (False→True).

**Nối với `transport.py` hai chiều**, để hai lớp không thể lệch chính sách:
`tu_ngoai_le(LoiTamThoi|LoiVinhVien) → NormalizedCarrierError` và
`thanh_ngoai_le_transport(loi) → LoiTamThoi nếu co_the_thu_lai, ngược lại LoiVinhVien`.

**Bảng mã lỗi J&T — 26 mã lỗi + 1 mã thành công, có nguồn.** Đọc bằng **trình duyệt thật**
14/10/2026 tại `open.jtexpress.vn/apiDoc/errorCode/index` (trang là SPA, `curl` không đọc được),
đối chiếu thêm bảng riêng của `/orderserve/cancel` và `/logistics/query`. Ghi chú cũ *"chưa đọc
được tài liệu mã lỗi"* nay **đã gỡ** vì đọc được rồi. Vài mã đáng chú ý:

| Mã gốc | Nghĩa | → mã chuẩn |
|---|---|---|
| `1` | 成功 | **thành công** (chỉ `"1"` mới là thành công; `"0"` tài liệu ghi rõ là *fail*) |
| `145003030` / `145003031` | sai chữ ký header / sai chữ ký bizContent | `XAC_THUC_HONG` |
| `999001030` | sai `customerCode` hoặc `password` | `XAC_THUC_HONG` |
| `145003502` | gửi quá 30 mã vận đơn một lượt | `THAM_SO_SAI` |
| `145003204` | **`txlogisticId` trùng** — lượt trước đã vào hãng | `DON_TRUNG`, không bao giờ thử lại |
| `999010010` | trạng thái đơn hiện tại không hủy được | `HANG_TU_CHOI` |
| `999002000` | không tìm thấy dữ liệu | `KHONG_TIM_THAY` |

Mã không có trong bảng ⇒ `KHONG_RO` + không thử lại (không đoán nghĩa mã lạ).

**Viettel Post: bảng mã lỗi để RỖNG** — không có tài liệu, và repo `vip-viettelpost` cũng không có
(xem audit). Lỗi VTP hiện chỉ phân loại được theo HTTP status qua `tu_http()`.

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

## 5. Bộ thử (`app/thu/thu_g03.py`) — 53 test

Nhóm **A (8 test)** chạy với **mọi adapter đã đăng ký**, nên thêm hãng mới mà khai thiếu là hỏng ngay:
đủ 8 hàm chuẩn (kể cả `getCapabilities`) · khai đủ capability · capability khai `False` thì trả "không hỗ trợ" tử tế (không
ném lỗi, không giả vờ làm được) · capability `True` thì chạy được ở mock · LIVE bị khóa ở mọi hãng ·
mock **tự nhận là mock** · phân biệt được ba kết cục · normalize trả trạng thái hợp lệ và mã lạ
không đổi trạng thái.

Nhóm **B (3)** bảng ánh xạ · **C (6)** retry/timeout · **D (6)** polling · **E (7)** mã hóa
AES-256-GCM · **F (4)** `getCapabilities` · **G (11)** lỗi hãng chuẩn hóa · **H (8)** hợp đồng
chữ ký J&T.

Nhóm **H** đối chiếu với **tài liệu**, không đối chiếu với mã của chính mình (§12.1: thứ dùng để
kiểm chứng phải độc lập): `digest = base64(md5-BYTES(bizContent + privateKey))` và phải **khác**
biến thể sai hay gặp là base64 của chuỗi hex · dài đúng 24 ký tự · đổi bizContent hoặc privateKey
thì chữ ký phải đổi · tiếng Việt có dấu ký theo UTF-8 · `bizContent` là **chuỗi JSON** và thân
form chỉ có đúng trường đó · đủ ba header `apiAccount`/`digest`/`timestamp` + Content-Type
`application/x-www-form-urlencoded` · timestamp **mili giây, UTC+7 tính tường minh** (13 chữ số) ·
chữ ký ký đúng chuỗi nằm trong thân yêu cầu · môi trường mock **không có URL thật** · và không
file adapter nào chứa mã gọi mạng (`requests`/`httpx`/`urllib.request`/`http.client`/`socket`).

Mock transport tách bạch: `AdapterJT.yeu_cau_tao_don(don)` dựng **trọn gói** url + headers + body
mà **không gửi đi đâu**, nên bộ thử kiểm được đúng thứ sẽ gửi, không cần mạng và không cần
credentials thật. Ở môi trường `mock`, `url` cố ý là `None`.

## 6. Còn BLOCKED

Adapter thật cho J&T và Viettel Post — cần Owner cấp credentials.
Khung đã sẵn: chỉ cần thay lớp transport mock bằng lớp gọi HTTP thật, giữ nguyên interface, bảng
ánh xạ, bảng mã lỗi và bộ thử hợp đồng.

*Sửa 14/10/2026:* mục này từng ghi còn cần *"cho phép đọc repo `vip-viettelpost`"*. Owner đã cho
phép, repo đã đọc, và **trong đó không có gì tái dùng được cho lớp tích hợp hãng** —
`STATUS_MAP = {}`, `auth.py` và `provider.py` đều `NotImplementedError`. Nút thắt còn lại của VTP
là **tài liệu Partner API + credentials**. Chi tiết và bằng chứng:
[docs/VIETTELPOST_REUSE_AUDIT.md](VIETTELPOST_REUSE_AUDIT.md).
