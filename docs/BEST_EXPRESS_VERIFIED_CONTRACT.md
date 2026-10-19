# BEST EXPRESS — HỢP ĐỒNG ĐÃ ĐỌC TỪ TÀI LIỆU CHÍNH THỨC

**Nguồn:** Google Docs do Owner cung cấp — “Tài liệu API của Best Express Việt Nam”
<https://docs.google.com/document/d/1O9PXBeSSHNLNUnKTZ7NvSzBSagW8IMUW5Pj1BHfVgHs/edit>

**Cách đọc:** `.../mobilebasic` và `.../export?format=txt` (tải về 2026-10-19, 1.467 dòng,
34.004 byte). Bản `edit` chỉ trả vỏ HTML; bản `mobilebasic`/`export` trả toàn văn.

**Trạng thái:** `DOC_VERIFIED` — đã đọc toàn văn và đối chiếu. **Chưa phải REAL PASS**:
chưa có credentials, chưa gọi API có xác thực, chưa tạo đơn thật.

> **CẬP NHẬT 2026-10-19 — ĐỐI CHIẾU TỆP DOCX VÀ SỬA ADAPTER.** Owner cung cấp tệp
> `Tài liệu API của Best Express Việt Nam.docx`; đã đọc `word/document.xml` (824 dòng trích
> xuất). Các mục “schema SAI” bên dưới nay đã được sửa trong `app/best_hop_dong.py` và
> `app/adapter_best.py`. Đo thật: login endpoint trả `Result=2` + HTTP 200 khi sai; EstimateFee
> trả `data.TotalFee`/`Cod`; test account công khai trong tài liệu đã bị khoá. Bằng chứng đầy
> đủ ở `docs/BEST_EXPRESS_DOCX_AUDIT.md`; quy trình nghiệm thu ở
> `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md`. Các dòng “adapter hiện tại…” trong tài liệu này
> là **trạng thái lịch sử**, không còn đúng.

---

## 0. KẾT LUẬN NGẮN

1. Tài liệu **đọc được**. Mọi mục trước đây ghi “Google Docs không đọc được” nay đã có nguồn.
2. Tài liệu dùng **HTTP** trong ví dụ, nhưng **HTTPS hoạt động** trên cả 3 host; chứng chỉ hợp lệ
   (`*.800best.com`, GlobalSign, hết hạn 2026-11-28). Vì vậy đường thật sẽ dùng **HTTPS**;
   HTTP plaintext tiếp tục bị chặn.
3. **Schema Order/Add hiện tại của adapter SAI** so với tài liệu: tên trường, cách gửi token và
   hình dạng phản hồi đều khác. Phải sửa trước khi gọi thật.
4. **Bảng 23 mã trạng thái hiện tại SAI phần lớn nghĩa**. Phải thay bằng bảng dưới đây.
5. Webhook xác thực bằng **JWT Bearer token**, không phải HMAC. Mock HMAC được giữ riêng.
6. Tài liệu liệt kê **23 mã**, không phải 24. Không bịa mã thứ 24.

---

## 1. TÁM ENDPOINT

Base path: `/VietNamV3/v3/api/process/sears`

| # | Tác vụ | Method | Đường dẫn | Production | Test |
|---|---|---|---|---|---|
| 1 | Login | POST | `/User/Login` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 2 | CreateOrder | POST | `/Order/Add` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 3 | UpdateOrder | POST | `/Order/Update` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 4 | UpdateAddress | POST | `/Order/UpdateAddress` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 5 | CancelOrder | POST | `/Order/Cancel` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 6 | Query | POST | `/Order/Query` | `sgp-seaedi.800best.com` | **`sea-edi-hxtest.800best.com`** |
| 7 | EstimateFee | POST | `/Service/EstimateFee` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |
| 8 | PrintWayBill | POST | `/Print/PrintWayBill` | `sgp-seaedi.800best.com` | `sgp-seaedi-test.800best.com` |

**Query test host khác biệt đã xác nhận:** `sea-edi-hxtest.800best.com` (không phải
`sgp-seaedi-test.800best.com`). Đây là mục §6 của Phase 1.

---

## 2. XÁC THỰC

### 2.1 Login

`POST /User/Login`, `Content-Type: application/json`.

Request:
```json
{"Username": "<USERNAME>", "Password": "<PASSWORD>"}
```

Response thành công:
```json
{"token": "<JWT>"}
```

- Token sống **30 ngày**.
- `ems-key` là header tuỳ chọn: “Best Customer Identity Key”.
- Không có `TenantId` trong request chính thức. Adapter hiện gửi thêm `TenantId` — phải bỏ.

### 2.2 Các API còn lại

Header:
```text
Content-Type: application/json
Authorization: Bearer <API_TOKEN>
ems-key: <optional>
```

Không dùng `Username`/`Password` trong từng API. Chỉ `/User/Login` nhận mật khẩu.

---

## 3. CREATE ORDER — `/Order/Add`

### 3.1 Trường chính thức

| Trường | Kiểu | Bắt buộc | Ghi chú |
|---|---|:---:|---|
| `Code` | string | * | Mã đơn của đối tác (`merchant_order_code`) |
| `ProductName` | string(1024) | * | Tên sản phẩm |
| `ProductPrice` | decimal | | Giá trị khai giá/bảo hiểm |
| `CollectAmount` | decimal | | Tiền thu hộ COD |
| `JourneyType` | int | * | 1 giao hàng, 2 thu hồi, 3 đổi hàng |
| `PickupType` | int | | 1 DropOff, 2 Postman |
| `ServiceId` | int | * | **12491** (Eco); 12490 Express chỉ được nêu, hiện chỉ hỗ trợ 12491 |
| `Weight` | int | * | **gram** |
| `Width` | int | | **mm** |
| `Height` | int | | **mm** |
| `Length` | int | | **mm** |
| `Note` | string(1024) | | Ghi chú |
| `NumberOfProducts` | int | | Số kiện; Express = 1/null, Cargo = số kiện |
| `BonusProductName1` | string(1024) | | Tên khuyến mãi 1 |
| `BonusProductName2` | string(1024) | | Tên khuyến mãi 2 |
| `SourceCity` | string(255) | * | Tỉnh/thành người gửi |
| `SourceDistrict` | string(255) | * | Quận/huyện người gửi; **địa chỉ 2 cấp mới: `" "`** |
| `SourceWard` | string(255) | * | Phường/xã người gửi |
| `SourceAddress` | string(1024) | * | Địa chỉ chi tiết người gửi |
| `SourceName` | string(255) | * | Tên người gửi |
| `SourcePhoneNumber` | string(255) | * | SĐT người gửi |
| `DestCity` | string(255) | * | Tỉnh/thành người nhận |
| `DestDistrict` | string(255) | * | Quận/huyện; **2 cấp mới: `" "`** |
| `DestWard` | string(255) | * | Phường/xã người nhận |
| `DestAddress` | string(1024) | * | Địa chỉ chi tiết người nhận |
| `DestName` | string(255) | * | Tên người nhận |
| `DestPhoneNumber` | string(255) | * | SĐT người nhận |
| `ReturnCity` | string(255) | * | Tỉnh/thành nhận hàng trả |
| `ReturnDistrict` | string(255) | * | Quận/huyện; **2 cấp mới: `" "`** |
| `ReturnWard` | string(255) | * | Phường/xã nhận hàng trả |
| `ReturnAddress` | string(1024) | * | Địa chỉ chi tiết nhận hàng trả |
| `ReturnName` | string(255) | * | Tên người nhận hàng trả |
| `ReturnPhoneNumber` | string(255) | * | SĐT người nhận hàng trả |
| `ShipmentPayer` | int | | 0 người gửi trả, 1 người nhận trả; mặc định người gửi |

Request mẫu chính thức có 31 khoá (không phải “21 trường” như đề bài B1 cũ). Tài liệu không đánh
dấu `*` cho `ProductPrice`, `CollectAmount`, `Width`, `Height`, `Length`, `PickupType`, `Note`,
`NumberOfProducts`, `BonusProductName1/2`, `ShipmentPayer`.

### 3.2 Phản hồi

```json
{"Result": 1, "Message": null, "Code": "84855006048931", "RouteCode": "SG905-00-00-02"}
```

- `Result`: 1 thành công, 2 thất bại.
- `Message`: null/rỗng khi thành công; lý do khi thất bại.
- `Code` là mã tra cứu hành trình Best (waybill).
- **Không có envelope `success`/`data`** — adapter hiện tại đang chờ envelope đó, nên sẽ coi
  phản hồi thật là “KHÔNG BIẾT”.

---

## 4. UPDATE / UPDATE ADDRESS / CANCEL

### 4.1 `/Order/Update`

Body: `Code`*, `ProductName`*, `ProductPrice`, `CollectAmount`, `ServiceId`*, `Length`, `Height`,
`Width`, `Weight`.

- `Code` nhận mã Best Tracking **hoặc** mã đối tác.
- `Result` 1/2, `Message`.

### 4.2 `/Order/UpdateAddress`

Body: `Code`*, `AddressTypeId`* (1 Pickup, 2 Delivery, 3 Return), `Address`*, `CityName`*,
`DistrictName`*, `WardName`*, `ContactName`*, `PhoneNumber1`*, `PhoneNumber2`.

- Chỉ sửa được trước trạng thái Inbound Sort Center (303).
- `Result`, `Message`, `Code`, `RouteCode`, `AddressTypeId`.

### 4.3 `/Order/Cancel`

Body: `{"Code": "<mã đối tác hoặc mã Best>"}`.
Chỉ hủy được khi đơn chưa lấy hàng thành công (202).
`Result` 1/2, `Message`. Ví dụ lỗi: `Result=2` nếu đơn đã hủy.

---

## 5. QUERY — `/Order/Query`

Body:
```json
{"LangType": "en-US", "Codes": ["<mã>"]}
```

- `Codes`: mảng, **tối đa 10**.
- `LangType`: `zh-CN` hoặc `en-US`.
- Host TEST: `sea-edi-hxtest.800best.com`.

Response:
```json
{"Result":1,"Message":null,"data":[{
  "merchant_order_code":"...","code_best":"...",
  "traceLogs":[{"status":"211","modified_at":1672887427946,...}]
}]}
```

- `status` trong `traceLogs` là **chuỗi** (`"211"`).
- `modified_at` là **long epoch ms**.
- Mỗi `traceLogs` có thể có `cod`, `product_price`, phí, `weight/length/width/height`.
- Trạng thái hiện tại là phần tử cuối của `traceLogs` (theo thời gian), không phải `Status` cấp
  ngoài. Adapter hiện tại đọc `Status`/`Items` — sai.

---

## 6. ESTIMATE FEE — `/Service/EstimateFee`

Body: `UserName` (tuỳ chọn), `ServiceId`*, `DestCity`*, `DestDistrict`*, `DestWard`,
`SourceCity`*, `SourceDistrict`*, `SourceWard`, `Cod`*, `ProductPrice`*, `DiscountCode`, `Weight`*
(gram), `Length`, `Height`, `Width` (mm).

Response `data`: `IsDefaultPrice`, `ServiceId`, `ServiceType`, `OrderType`, `SourceCity/District/Ward`,
`DestCity/District/Ward`, `Weight`, `Length`, `Height`, `Width`, `COD`, `Discount`, `ProductPrice`,
`FreightFee`, `FreightFeeVAT`, `CODFee`, `CODFeeVAT`, `InsuranceFee`, `InsuranceFeeVAT`,
`TotalFee`, `TotalFeeVAT`, `TotalFeeWithDiscount`, `TotalFeeVATWithDiscount`.

Adapter hiện tại đọc `Fee`/`TotalFee` ở cấp ngoài — sai; phải đọc `data.TotalFee` (hoặc
`TotalFeeVAT`, tùy hợp đồng tài chính; chưa chốt loại nào là “phí cuối”).

---

## 7. PRINT — `/Print/PrintWayBill`

Body: `{"codes": ["<mã Best>", ...]}` — **tối đa 50**.

Response: `Guid`, `Url`, `Result`, `Message`. `Url` là URL PDF, ví dụ
`http://sgp-seaedi-test.800best.com/.../ExportAt_....pdf`.

Adapter hiện tại gửi `WaybillCodes` và đọc `Urls`/`Url` — phải đổi sang `codes`, đọc `Url`.
URL PDF phải bị kiểm SSRF như hiện tại; tài liệu dùng HTTP cho URL PDF, nhưng HTTPS cũng có.

---

## 8. WEBHOOK

### 8.1 Xác thực

Tài liệu: “Best Express chỉ hỗ trợ phương thức xác thực thông qua **JWT(Bearer) token**.”
Trưởng bưu cục/Sale cấu hình URL webhook và Bearer token trong V9 (`https://v9.800best.com`).
Không có chữ ký HMAC trong tài liệu.

→ Với môi trường thật, hub phải xác thực `Authorization: Bearer <token>` bằng so sánh hằng thời
gian với token đã lưu cho **đúng carrier_account**. Mock HMAC của hub giữ riêng cho bộ thử.

### 8.2 Payload (18 trường)

`code_best`, `merchant_order_code`, `cod`, `product_price`, `status`, `status_content`,
`freight_fee`, `cod_fee`, `insurance_fee`, `vat_fee`, `return_fee`, `discount`, `modified_at`,
`total_fee`, `weight`, `length`, `width`, `height`.

- `status` trong ví dụ là **chuỗi** (`"2"`), không phải int.
- `modified_at` là `long` epoch ms.
- Các trường phí/COD là decimal.
- Trường lạ: tài liệu không nói; giữ nguyên trong payload thô nhưng không dùng để quyết định.

### 8.3 ACK

Mẫu phản hồi từ đối tác:
```json
{"Result": 1, "Message": ""}
```
- `Result=1` là ACK. `Result=2`/khác là NACK.
- Tài liệu không nói HTTP status, thời gian timeout hay điều kiện gửi lại. Giữ NACK 4xx/5xx nội
  bộ; ghi rõ CHƯA XÁC MINH.

---

## 9. BẢNG 23 MÃ TRẠNG THÁI CHÍNH THỨC

| Mã | Nghĩa chính thức | Trạng thái chung đề xuất |
|---:|---|---|
| 211 | Đang đi lấy hàng | `cho_lay` (đang lấy) |
| 203 | Lấy hàng không thành công | `lay_hang`? / `giao_that_bai`? — cần chốt nội bộ: **lấy thất bại** |
| 202 | Lấy hàng thành công | `lay_hang` |
| 301 | Nhận hàng vào bưu cục Nguồn | `lay_hang` / trung chuyển |
| 302 | Xuất hàng đến trung tâm khai thác | `dang_giao` (trung chuyển) |
| 303 | Nhận hàng vào trung tâm khai thác | `dang_giao` |
| 304 | Xuất hàng khỏi trung tâm khai thác | `dang_giao` |
| 309 | Nhận hàng vào bưu cục phát hàng | `dang_giao` |
| 601 | Xuất hàng để đi giao | `dang_giao` |
| 604 | Giao hàng không thành công | `giao_that_bai` |
| 666 | Giao hàng thành công | `giao_thanh_cong` |
| 605 | Xác nhận chuyển hoàn | `hoan_hang` |
| 606 | Hủy trạng thái trả hàng, mở lại chiều giao | `dang_giao` (mở lại) |
| 701 | Xuất hàng khỏi bưu cục phát để trả về | `hoan_hang` |
| 702 | Nhận hàng vào trung tâm khai thác để trả về | `hoan_hang` |
| 703 | Xuất hàng khỏi trung tâm khai thác để trả về | `hoan_hang` |
| 704 | Nhận hàng vào bưu cục trả hàng | `hoan_hang` |
| 705 | Xuất hàng để trả về | `hoan_hang` |
| 707 | Trả hàng không thành công | `hoan_hang` |
| 708 | Trả hàng thành công | `hoan_hang` |
| 777 | Thất lạc | `giao_that_bai` (cần soát) |
| 1000 | Hư hỏng (Damage) | `giao_that_bai` (cần soát) |
| 2 | Hủy đơn (customer Cancel) | `da_huy` |

**Tổng: 23 mã.** Không có mã thứ 24. `777`/`1000` không phải “đã hủy/đã giao thành công” như
bảng cũ; phải ánh xạ là sự cố và cần soát.

**Lưu ý 605 → 606:** 605 là “Xác nhận chuyển hoàn”; 606 là “Hủy trạng thái trả hàng, mở lại
chiều giao”. Đây là cặp đúng nghĩa: 605 đóng chiều giao cũ, 606 mở lại chiều giao.

---

## 10. KHÁC BIỆT VỚI MÃ HIỆN TẠI

| Hạng mục | Hiện tại | Tài liệu | Mức |
|---|---|---|---|
| Auth API | Login rồi Bearer; nhưng Login gửi thêm `TenantId`, response chờ envelope `success` | Login `{Username,Password}`, response `{token}`; API khác Bearer | **SAI / phải sửa** |
| Order/Add fields | 21 trường nội bộ `MerchantOrderCode/SenderName/...` | 31 trường `Code/ProductName/SourceCity/...` | **SAI / phải sửa** |
| Order/Add response | chờ `success/data` | `Result/Message/Code/RouteCode` | **SAI / phải sửa** |
| Update | gửi lại 21 trường + `WaybillCode` | 9 trường `Code/ProductName/...` | **SAI / phải sửa** |
| UpdateAddress | `WaybillCode/ReceiverName/...` | `Code/AddressTypeId/Address/CityName/...` | **SAI / phải sửa** |
| Cancel | `WaybillCode/Reason` | `Code` | **SAI / phải sửa** |
| Query body | `WaybillCodes` | `Codes` + `LangType` | **SAI / phải sửa** |
| Query response | `Items/Waybills/Status` | `data[].traceLogs[].status` | **SAI / phải sửa** |
| Query test host | không dùng `sea-edi-hxtest` | `sea-edi-hxtest.800best.com` | **ĐÃ XÁC NHẬN mới** |
| EstimateFee | `SenderProvince/Cod/...` + `data.Fee` | `SourceCity/COD/...` + `data.TotalFee` | **SAI / phải sửa** |
| Print body | `WaybillCodes` | `codes` | **SAI / phải sửa** |
| Print response | `Urls` | `Url` | **SAI / phải sửa** |
| Webhook auth | HMAC `X-Webhook-Signature` (mock) | JWT Bearer | **THIẾU cho thật** |
| Status map | 23 mã giả thuyết sai phần lớn | 23 mã chính thức | **SAI / phải sửa** |
| HTTPS | đề bài nói HTTP; adapter chặn HTTP | HTTPS hoạt động, cert hợp lệ | **ĐÃ XÁC MINH; dùng HTTPS** |

---

## 11. HTTPS/TLS — BẰNG CHỨNG ĐO ĐƯỢC

Đo 2026-10-19, không gửi credential, không gọi API có xác thực:

```text
sgp-seaedi-test.800best.com:443  TLSv1.2  ECDHE-RSA-AES128-GCM-SHA256
  subject CN=*.800best.com, O=百世物流科技（中国）有限公司
  issuer  GlobalSign RSA OV SSL CA 2018
  notAfter Nov 28 08:14:08 2026 GMT
sgp-seaedi.800best.com:443       TLSv1.2  ECDHE-RSA-AES256-GCM-SHA384  (cùng cert)
sea-edi-hxtest.800best.com:443   TLSv1.2  ECDHE-RSA-AES256-GCM-SHA384  (cùng cert)
```

- `curl -I https://<host>/` trả 405 (chỉ nhận POST) — chứng tỏ TLS + HTTP/1.1/2 hoạt động.
- Python `ssl.create_default_context()` xác minh chứng chỉ thành công; **không** tắt xác minh.
- Kết luận: dùng `https://` cho cả 3 host; không dùng `http://` plaintext cho credential/dữ liệu
  thật. Đây là thay đổi so với tài liệu (tài liệu ghi HTTP) nhưng có bằng chứng TLS.

---

## 12. CÒN THIẾU / BLOCKED

1. **Credentials test/production** — chưa có; không dùng test account công khai trong tài liệu.
2. **Owner approval** để gọi `/User/Login` thật — chưa có.
3. **Đo phản hồi thật** của 8 API — chưa có; mọi hình dạng phản hồi mới chỉ đọc tài liệu.
4. **HTTP status/timeout/retry** của hãng — tài liệu không nói; giữ nội bộ, ghi CHƯA XÁC MINH.
5. **webhook Bearer token thật** — chưa có; cần Owner/Best cấu hình.
6. **`ems-key`** — tuỳ chọn, chưa rõ khi nào cần.

---

## 13. CÁCH CHẠY LẠI VIỆC ĐỌC TÀI LIỆU

```sh
curl -sS -L -A 'Mozilla/5.0' \
  'https://docs.google.com/document/d/1O9PXBeSSHNLNUnKTZ7NvSzBSagW8IMUW5Pj1BHfVgHs/export?format=txt' \
  -o /tmp/best_doc.txt
wc -l /tmp/best_doc.txt   # 1467 dòng
```
