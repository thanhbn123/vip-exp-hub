# BEST EXPRESS — ĐỐI CHIẾU DOCX CHÍNH THỨC VỚI ADAPTER (2026-10-19)

**Nguồn chính:** `Tài liệu API của Best Express Việt Nam.docx` — Owner cung cấp tại
`/Users/viporder/Downloads/`. Đã giải nén `word/document.xml` và trích cả bảng:
**824 dòng văn bản · 30.023 ký tự**. Bản Google Docs cùng nội dung
(<https://docs.google.com/document/d/1O9PXBeSSHNLNUnKTZ7NvSzBSagW8IMUW5Pj1BHfVgHs/edit>,
`export?format=txt` 1.467 dòng) được dùng để đối chiếu chéo, không thay thế tệp DOCX.

**Kết luận ngắn:** đã sửa các sai lệch wire lớn (auth, 8 endpoint, 31 trường tạo đơn, envelope
`Result/Message`, 23 mã trạng thái + `customer Cancel`, webhook Bearer, tracking `traceLogs`,
phí `data.TotalFee`, in `codes/Url`). **Chưa có REAL PASS trọn vẹn**: cần tài khoản test do BEST
cấp và một URL webhook HTTPS công khai. Không tạo đơn production, không dùng HTTP bản rõ.

> Ghi chú lịch sử: một bản nháp trước trong tệp này nói “DOCX không có trong workspace”. Câu đó
> đúng với lượt chạy cũ, **sai với tệp Owner vừa cung cấp**. Tệp thật đã được đọc trong lượt
> này; mọi tên trường dưới đây lấy từ tệp đó.

---

## 1. TÁM ENDPOINT — ĐỐI CHIẾU

Base path: `/VietNamV3/v3/api/process/sears`. Tài liệu in `http://`; hệ thống dùng `https://`
vì TLS đã đo được trên cả ba host (mục 6). Đây là sai lệch **có chủ ý** so với tài liệu.

| Tác vụ | Method | Đường dẫn | Host test | Trạng thái code |
|---|---|---|---|---|
| Login | POST | `/User/Login` | `sgp-seaedi-test.800best.com` | `best_hop_dong.dung_login`, `xac_thuc_best` |
| CreateOrder | POST | `/Order/Add` | `sgp-seaedi-test...` | `dung_order_add` |
| UpdateOrder | POST | `/Order/Update` | `sgp-seaedi-test...` | `dung_update` |
| UpdateAddress | POST | `/Order/UpdateAddress` | `sgp-seaedi-test...` | `dung_update_address` |
| CancelOrder | POST | `/Order/Cancel` | `sgp-seaedi-test...` | `dung_cancel` |
| Query (Trace) | POST | `/Order/Query` | **`sea-edi-hxtest.800best.com`** | `_url()` chọn host riêng |
| EstimateFee | POST | `/Service/EstimateFee` | `sgp-seaedi-test...` | `dung_estimate` |
| PrintWayBill | POST | `/Print/PrintWayBill` | `sgp-seaedi-test...` | `dung_print` |

Giới hạn tài liệu: Query **≤ 10 mã**, Print **≤ 50 mã**. Code từ chối trước khi gửi, không cắt
bớt im lặng.

---

## 2. XÁC THỰC — SỬA TỪ SAI SANG ĐÚNG

| Hạng mục | Trước | DOCX / thực tế | Đã sửa |
|---|---|---|---|
| Body Login | `{TenantId, Username, Password}` | `{Username, Password}` | Bỏ `TenantId` khỏi body |
| Envelope Login | chờ `success/data` | `{token, Result, Message}` | `boc_ket_qua` đọc `Result` + `token` cấp ngoài |
| Token | đọc `data.Token` | `token` cấp ngoài | `boc_token` |
| API khác | header Bearer | `Authorization: Bearer <token>` | `_headers` |
| `ems-key` | không dùng | header tuỳ chọn | nhận từ credentials/UI |
| Hạn token | không cache | 30 ngày | không cache; mỗi lượt đăng nhập lại (an toàn) |

**Đo thật 2026-10-19 (không dùng credential thật):**

```text
POST https://sgp-seaedi-test.800best.com/.../User/Login  body {}
→ HTTP/2 200  {"token":null,"Result":2,"Message":"[401] Invalid username or password"}

POST .../User/Login  body {"Username":"__vip_probe_not_a_user__", ...}
→ HTTP/2 200  {"token":null,"Result":2,"Message":"[404] The account not found or have been locked..."}
```

Điều này xác nhận: (a) HTTPS/HTTP2 hoạt động; (b) lỗi xác thực vẫn trả **HTTP 200** với
`Result=2`; (c) parser phải đọc `Result`, không chỉ HTTP status.

**Tài khoản test công khai trong tài liệu đã bị khoá** — đo cùng ngày:

```text
V9Cus60437573 / <mật khẩu công khai trong DOCX>
→ {"token":null,"Result":2,"Message":"[404] The account not found or have been locked..."}
```

Cần tài khoản test do BEST cấp. Không dùng tài khoản này để tạo đơn.

Qua backend thật (tài khoản sandbox giả, chỉ để đo giao thức):

```text
POST /api/v2/best/kiem-ket-noi  {"tai_khoan_id":5,"xac_nhan_that":true}
→ HTTP 401; body BEST: Result=2, "[404] The account not found or have been locked"
→ meta.http_status=200; TLS ok, cn=*.800best.com, issuer=GlobalSign, hết hạn 2026-11-28
```

Không có token nào trả về UI/response/audit.

**Lỗi UI thật đã sửa:** bàn nghiệm thu từng hiểu mọi HTTP 401 là “phiên hub hết hạn”, nên khi
BEST từ chối mật khẩu (server trả 401 kèm `ok:false`) trang lại báo “mở /admin/ để đăng nhập”.
Giờ phân biệt bằng cờ `ok` của phản hồi BEST; ca Playwright 04 canh đúng.

---

## 3. ORDER/ADD — 31 TRƯỜNG NỀN + 3 TRƯỜNG TUỲ CHỌN

Tài liệu liệt kê **34 thuộc tính**. 31 trường luôn gửi; `NumberOfProducts`,
`BonusProductName1/2` chỉ thêm khi có dữ liệu.

| Nhóm | Trường chính thức | Ghi chú |
|---|---|---|
| Đơn | `Code`* | Mã đối tác; response trả `Code` là mã Best |
| Hàng | `ProductName`*, `ProductPrice`, `CollectAmount`, `Note` | tiền là decimal |
| Hành trình | `JourneyType`* (1/2/3), `PickupType` (1/2), `ServiceId`* | chỉ hỗ trợ 12491 |
| Kiện | `Weight`* (gram), `Length/Width/Height` (mm), `NumberOfProducts` | Cargo >1 kiện chỉ JourneyType=1 |
| Gửi | `SourceCity`*, `SourceDistrict`*, `SourceWard`*, `SourceAddress`*, `SourceName`*, `SourcePhoneNumber`* | 2 cấp: District = `" "` |
| Nhận | `DestCity`*, `DestDistrict`*, `DestWard`*, `DestAddress`*, `DestName`*, `DestPhoneNumber`* | như trên |
| Trả | `ReturnCity`*, `ReturnDistrict`*, `ReturnWard`*, `ReturnAddress`*, `ReturnName`*, `ReturnPhoneNumber`* | thiếu thì mặc định người gửi |
| Phí | `ShipmentPayer` (0/1) | 0 người gửi, 1 người nhận |
| Khuyến mãi | `BonusProductName1/2` | tuỳ chọn |

**Đã sửa:** tên trường cũ `MerchantOrderCode/SenderName/SenderProvince/Receiver*/GoodsName/Cod/
Remark` → đúng tên tài liệu. Bốn khoá nội bộ `TenantId/CarrierId/IdempotencyKey/RequestId`
**không còn gửi trong body** (tài liệu không có).

**Đã sửa lỗi im lặng:** `_so(None)` trả 0, nên thiếu `Weight` từng gửi **0 gram**. `_nguyen`
giờ từ chối trường có sàn > 0 khi thiếu.

Response đúng: `{"Result":1,"Message":null,"Code":"848...","RouteCode":"SG905..."}`.
`ma_van_don` đọc `Code`, không đọc `data.WaybillCode` nữa.

---

## 4. UPDATE / UPDATE ADDRESS / CANCEL

| API | Trường tài liệu | Đã sửa |
|---|---|---|
| Update | `Code`*, `ProductName`*, `ProductPrice`, `CollectAmount`, `ServiceId`*, `Length/Height/Width/Weight` | bỏ 21 trường cũ + `WaybillCode` |
| UpdateAddress | `Code`*, `AddressTypeId`* (1/2/3), `Address`*, `CityName`*, `DistrictName`*, `WardName`*, `ContactName`*, `PhoneNumber1`*, `PhoneNumber2` | **chọn đúng người theo loại** |
| Cancel | `Code`* | bỏ `WaybillCode` + `Reason` khỏi body |

**Lỗi thật đã sửa:** `UpdateAddress` cũ luôn lấy địa chỉ **người nhận**, kể cả khi
`AddressTypeId=1` (lấy hàng) hoặc `3` (trả hàng). Giờ:
`1 → Source*`, `2 → Dest*`, `3 → Return*` (mặc định người gửi), kèm đúng `ContactName`/`PhoneNumber1`.
Có ca thử `test_39_update_address_chon_dung_nguoi_theo_loai`.

---

## 5. QUERY / ESTIMATE / PRINT

### Query
Body đúng: `{"LangType":"en-US","Codes":["..."]}`. Response:
`data[].{merchant_order_code, code_best, traceLogs[]}`; mỗi `traceLogs` có `status` **chuỗi**,
`modified_at` long, phí, cân, kích thước. Trạng thái hiện tại = phần tử cuối theo `modified_at`.
Test host **riêng**: `sea-edi-hxtest.800best.com`.

**Đã sửa:** body cũ `WaybillCodes`; parser cũ đọc `Items/Status`; giờ đọc `data[].traceLogs[]`.
`status="customer Cancel"` được nhận, `status_so=2`, `trang_thai_chung="da_huy"`, giữ nguyên
nhãn gốc trong `status_raw`.

### EstimateFee
Body đúng: `UserName` (tuỳ chọn), `ServiceId`*, `DestCity/District/Ward`, `SourceCity/District/
Ward`, `COD`*, `ProductPrice`*, `DiscountCode`, `Weight`*, `Length/Height/Width`.
Phí nằm trong `data`: `TotalFee`, `TotalFeeVAT`, `TotalFeeWithDiscount`,
`TotalFeeVATWithDiscount`, `FreightFee`, `CODFee`, `InsuranceFee`, `Cod`/`COD`, `Discount`.

**Đo thật 2026-10-19 (HTTPS, không token):**

```text
POST https://sgp-seaedi-test.800best.com/.../Service/EstimateFee
body: ServiceId 12491, HCM/Bình Thạnh/P12 → HCM/Tân Bình/P10, 500 g, COD 100000
→ Result=1; FreightFee=19800; FreightFeeVAT=21780; TotalFee=19800; TotalFeeVAT=21780;
  "Cod":100000.0; "ProductPrice":100000.0
```

**Đã sửa:** bản cũ đọc `Fee` cấp ngoài → luôn None với phản hồi thật. Giờ đọc `data` và có
`phi_cuoi()` chọn `TotalFeeVATWithDiscount → TotalFeeWithDiscount → TotalFeeVAT → TotalFee`
(không tự cộng/trừ). Hãng trả **`Cod`** chữ d thường dù request gửi `COD`; code chuẩn hoá cả hai.

### Print
Body đúng: `{"codes":["848..."]}` (chữ thường), tối đa 50. Response:
`{Guid, Url, Result, Message}`. **Một** URL PDF cho cả lô.

**Đã sửa:** body cũ `WaybillCodes`, parser cũ `Urls[]`. Giờ `boc_print_full` đọc `Url` + `Guid`.
Tải PDF nâng `http://<host BEST>` lên **HTTPS** trước khi tải; `http_best.tai_waybill` vẫn áp
allowlist, chặn IP nội bộ/metadata/redirect, kiểm `Content-Type: application/pdf`.

---

## 6. TLS — ĐO ĐƯỢC, KHÔNG HẠ CHUẨN

```text
sgp-seaedi-test.800best.com:443  TLSv1.2  ECDHE-RSA-AES128-GCM-SHA256
  CN=*.800best.com · GlobalSign RSA OV SSL CA 2018 · hết hạn 2026-11-28
sgp-seaedi.800best.com:443       TLSv1.2  (cùng cert)
sea-edi-hxtest.800best.com:443   TLSv1.2  (cùng cert)
```

Qua backend thật (mục 2) TLS được xác minh mặc định, không tắt `check_hostname`, không
`verify=False`. Mọi giao tiếp backend→BEST dùng HTTPS.

---

## 7. BẢNG 23 MÃ + `customer Cancel`

Đã thay bảng rỗng/giả thuyết bằng đúng 23 mã DOCX:
`211, 203, 202, 301, 302, 303, 304, 309, 601, 604, 666, 605, 606, 701, 702, 703, 704, 705,
707, 708, 777, 1000, 2` + nhãn chữ **`customer Cancel`**.

- `606` = mở lại chiều giao; là ngoại lệ duy nhất được hạ hạng.
- `2` và `customer Cancel` = đã hủy; webhook **chỉ ghi nhận**, không tự đổi `don_hang.trang_thai`.
- `777` (thất lạc), `1000` (hư hỏng) = sự cố, `can_soat=True`.
- Mã lạ: lưu thô, `can_soat=True`, không đổi trạng thái.

---

## 8. WEBHOOK

Tài liệu: chỉ JWT/Bearer, cấu hình URL + token trong V9; payload 18 trường snake_case; ACK
`{"Result":1,"Message":""}`. Không có HMAC.

**Đã sửa:** nhánh sandbox/production dùng `xac_thuc_best.kiem_bearer_webhook`
(so sánh hằng thời gian), không dùng HMAC; `doc_payload` nhận `status` số **hoặc**
`"customer Cancel"`; `_khoa_su_kien` dùng nhãn gốc; `hang_ma_goc` giữ `"customer Cancel"`.
Nhánh mock vẫn dùng HMAC của hub để bộ thử cũ chạy được.

**Chưa nghiệm thu thật:** máy local `127.0.0.1` không cho BEST gọi vào. Cần URL HTTPS công khai
(tunnel/reverse proxy) và Bearer do BEST cấp. Xem `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md`.

---

## 9. FILE ĐÃ SỬA / THÊM

| Tệp | Thay đổi |
|---|---|
| `app/http_best.py` | base URL HTTPS; `nang_cap_https_cho_url_hang`; comment TLS |
| `app/best_hop_dong.py` | builder/parser theo DOCX; 31+3 trường; AddressTypeId; `customer Cancel`; `Cod`; `in_pdf_that`; update/cancel/address |
| `app/adapter_best.py` | wire layer dùng `best_hop_dong`; bỏ metadata khỏi body; status map thật; webhook official; print/estimate/query mới |
| `app/webhook_best.py` | nhận `customer Cancel`; giữ nhãn gốc; Bearer |
| `app/server.py` | route update/address/cancel/PDF; webhook URL đầy đủ; TLS detect; in URL đúng |
| `admin/best.js` | bỏ form credential sai; dẫn sang bàn nghiệm thu; sửa text CHỜ BACKEND cũ |
| `admin/best_uat.js`, `pages/best-uat.html` | bàn nghiệm thu thật: phê duyệt, account, login, fee, order, tracking, PDF, update/cancel, webhook |
| `trien_khai/best_nghiem_thu.sh` | HTTPS local + owner gate + cảnh báo public URL |
| `app/thu/thu_best_*.py` | cập nhật fixture/stub theo DOCX; thêm ca `customer Cancel`, `Cod`, AddressTypeId, route mới |

---

## 10. BẰNG CHỨNG CHẠY (2026-10-19)

| Bộ thử | Kết quả | Exit |
|---|---|---|
| `thu_best_adapter.py` | **118 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_best_hop_dong.py` | **35 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_best_webhook.py` | **52 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_best_uat.py` | **14 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_best_auth.py` | **47 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_best_e2e_http.py` | **59 ca · 0 lỗi · 0 hỏng** | 0 |
| `thu_webhook.py` (hồi quy hub) | **68 ca · 0 lỗi** | 0 |
| `thu_giao_dien/best_express.spec.js` (Playwright, Chromium ghim) | **15 ca · 15 passed · 0 failed** | 0 |
| `thu_tich_hop.py` (static kiến trúc) | **12 ca · 0 lỗi** | 0 |

`thu_best_qa.py::test_01_baseline` **cố ý đỏ** vì cây làm việc có thay đổi chưa commit (git
worktree nằm ngoài vùng ghi của phiên). Đây là trạng thái git, không phải lỗi chức năng.
Ma trận QA đọc được: **PASS=5 · FAIL=1 (baseline dirty tree) · BLOCKED=2 (credential/webhook
công khai) · NOT TESTED=1 (UI nay đã đo riêng 15/15) · PENDING=1 (Owner)**. `REAL PASS: 0` —
đúng như trạng thái bằng chứng, không nâng lời.

**REAL evidence đã có:** HTTPS + login endpoint thật (âm tính), EstimateFee thật (dương tính),
TLS verify, backend→BEST qua HTTPS, test account công khai đã khoá.
**REAL evidence còn thiếu:** login **thành công** bằng tài khoản do BEST cấp; tạo/tracking/in
thật; callback webhook thật. Cần Owner nhập tài khoản và cấu hình URL công khai.

---

## 11. CHƯA XÁC MINH / RỦI RO CÒN LẠI

1. **`ems-key`**: tài liệu chỉ ghi “Best Customer Identity Key (Optional)”, không nói khi nào
   cần. Hệ thống gửi nếu có, không suy đoán giá trị.
2. **HTTP status lỗi**: hãng trả 200 + `Result=2`; code coi `Result=2` là từ chối chắc chắn.
   5xx/408/429 vẫn là “KHÔNG BIẾT”.
3. **Tạo đơn Cargo > 1 kiện**: code chặn JourneyType≠1, nhưng chưa có tài khoản Cargo để đo.
4. **In PDF**: URL mẫu HTTP; code nâng HTTPS cho đúng host. Nếu host PDF thực tế khác
   allowlist, việc tải sẽ bị từ chối — đó là chủ ý.
5. **Webhook thật**: chưa có URL công khai/Bearer thật. Local chỉ kiểm bằng bộ thử.
6. **Production**: mọi thao tác ghi bị khoá trong `best_hop_dong.cua_phe_duyet` và server.
   Không có đường nào tạo đơn production trong lượt này.
7. **Test account trong DOCX đã khoá** — không dùng được để nghiệm thu.
