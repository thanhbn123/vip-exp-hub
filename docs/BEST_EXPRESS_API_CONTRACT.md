# BEST EXPRESS — HỢP ĐỒNG ADAPTER (B1)

**Trạng thái lượt này: `MOCK_VERIFIED` — KHÔNG phải `REAL PASS`.**
Mọi phép đo chạy trên **stub loopback `127.0.0.1`, cổng do OS cấp**. Không có lượt gọi nào tới
`800best.com`, kể cả test host. Không có credentials thật, không có đơn thật, không có CSDL
nghiệp vụ nào bị ghi.

| Hạng mục | Giá trị |
|---|---|
| Agent | B1 — BEST API Adapter Core |
| Nền mã | `best/integration` @ `cb23312`; `main` = `de740dc` |
| Tệp mới | `app/adapter_best.py` · `app/http_best.py` · `app/thu/thu_best_adapter.py` · `docs/BEST_EXPRESS_API_CONTRACT.md` |
| Tệp dùng chung đã sửa | **KHÔNG có** — `adapter.py`, `adapter_jt.py`, `adapter_vtp.py`, `http_jt.py`, `server.py`, `webhook.py` giữ nguyên |
| Bằng chứng thử | `python3 app/thu/thu_best_adapter.py` → **exit 0 · 118 ca · 0 skip · 0 fail · 0 error** |
| Thời điểm đo | 2026-10-19 10:18 +07 |

---

## 0. BA CÂU PHẢI ĐỌC TRƯỚC

1. **Đây là MOCK PASS.** Adapter không được coi là "đã tích hợp BEST" cho tới khi có
   **REAL PASS** trên sandbox với tài liệu + credentials thật. Mọi câu trong tài liệu này chỉ
   nói về hợp đồng nội bộ và đường gửi trên stub.
2. **Tài liệu API BEST là Google Docs, KHÔNG đọc được trong lượt này.** Đề bài không kèm URL,
   workspace không có bản sao. Vì vậy **tên trường wire, hình dạng gói trả lời, mã trạng thái,
   mã lỗi, cách gửi token đều CHƯA XÁC MINH**. Đường LIVE bị chặn bằng mã
   (`SCHEMA_DA_XAC_MINH = False`), không phải bằng lời dặn.
3. **Đề bài xác nhận có 21 trường bắt buộc nhưng KHÔNG liệt kê tên 21 trường.** Agent đã hỏi
   coordinator qua `orca orchestration ask` (messageId `msg_8a78d82c3441`), chờ 600 giây, không
   có trả lời. Vì bị cấm đoán schema, tài liệu này ghi rõ: danh sách 21 trường dưới đây là
   **cách phân rã NỘI BỘ** dùng cho hợp đồng MOCK, **không phải schema BEST**. Khi có danh sách
   thật, phải thay `TRUONG_BAT_BUOC_ORDER_ADD` rồi mới được lật cờ xác minh.

---

## 1. BASE URL — SỰ THẬT QUAN TRỌNG NHẤT

| Môi trường | Base URL (nguyên văn đề bài) | Scheme | Ghi chú |
|---|---|---|---|
| production | `http://sgp-seaedi.800best.com/VietNamV3/v3/api/process/sears` | **HTTP** | **CHƯA MÃ HOÁ** |
| test / sandbox | `http://sgp-seaedi-test.800best.com/VietNamV3/v3/api/process/sears` | **HTTP** | **CHƯA MÃ HOÁ** |

**Đây là HTTP, chưa mã hoá.** Gửi credential (mật khẩu, token) hoặc dữ liệu đơn thật qua kênh
này là gửi bản rõ qua mạng. Adapter **TỪ CHỐI** scheme `http` cho host hãng, trừ khi người gọi
bật **đồng thời** cờ lớp `CHO_PHEP_HTTP_KHONG_MA_HOA=True` **và** tham số `cho_phep_http_khong_ma_hoa=True` của lượt dựng; **mặc định là CHẶN**.

Ba lớp chặn độc lập, mở một lớp không mở hai lớp kia:

| # | Cửa | Giá trị hiện tại | Chặn ở đâu |
|---|---|---|---|
| 1 | `CarrierAdapter.CHO_PHEP_LIVE` (lớp nền, dùng chung) | `False` | `CarrierAdapter.__init__` |
| 2 | `AdapterBEST.CHO_PHEP_SANDBOX` / `CHO_PHEP_PRODUCTION` | `False` / `False` | `AdapterBEST.__init__` và `_kiem_cua_live` |
| 3 | `AdapterBEST.SCHEMA_DA_XAC_MINH` | `False` | `_goi_that` — chặn **trước khi mở socket** |
| 4 | `CHO_PHEP_HTTP_KHONG_MA_HOA` | `False` | `http_best.tach_url` + `__init__` |

Phải có **cả hai** cờ (`CHO_PHEP_HTTP_KHONG_MA_HOA` của lớp và tham số `cho_phep_http_khong_ma_hoa=True` khi dựng) mới mở HTTP; chỉ được dùng cho môi trường **đã được duyệt**. Nó không
làm cho schema thành đúng, và không mở `CHO_PHEP_LIVE`.

### 1.1 Hostname test Order/Query — CHƯA XÁC MINH, KHÔNG DÙNG

Đề bài nói endpoint test của Order/Query dùng hostname khác:
`sea-edi-hxtest.800best.com`. Hostname này:

- **KHÔNG** nằm trong danh sách trắng `HOST_HANG`;
- **KHÔNG** được dùng trong bất kỳ nhánh mã nào;
- được khai thành hằng số `HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH` chỉ để người sau thấy nó **đã
  được biết tới và cố ý không dùng**.

Muốn dùng phải: đọc tài liệu BEST, xác nhận hostname và endpoint, thêm vào danh sách trắng có
kiểm soát, rồi có test âm/dương. Không được "thấy tên trong đề bài" rồi ghép URL.

---

## 2. TÁM ENDPOINT — HẰNG SỐ CÓ TÊN

Mọi đường dẫn nằm trong `adapter_best.DUONG_API`; **không rải chuỗi trong hàm**.

| # | Tên nội bộ | Method | Đường dẫn | Trạng thái |
|---|---|---|---|---|
| 1 | `authenticate` | POST | `/User/Login` | Đường dẫn ĐÃ XÁC NHẬN; request/response schema **CHƯA XÁC MINH** |
| 2 | `createOrder` | POST | `/Order/Add` | Đường dẫn ĐÃ XÁC NHẬN; field wire **CHƯA XÁC MINH** |
| 3 | `updateOrder` | POST | `/Order/Update` | Đường dẫn ĐÃ XÁC NHẬN; field wire **CHƯA XÁC MINH** |
| 4 | `updateAddress` | POST | `/Order/UpdateAddress` | Đường dẫn ĐÃ XÁC NHẬN; field wire **CHƯA XÁC MINH** |
| 5 | `cancelOrder` | POST | `/Order/Cancel` | Đường dẫn ĐÃ XÁC NHẬN; field wire **CHƯA XÁC MINH** |
| 6 | `queryTracking` | POST | `/Order/Query` | Đường dẫn ĐÃ XÁC NHẬN; tối đa **10 mã/lần**; host test khác **CHƯA XÁC MINH** |
| 7 | `estimateFee` | POST | `/Service/EstimateFee` | Đường dẫn ĐÃ XÁC NHẬN; field wire **CHƯA XÁC MINH** |
| 8 | `printWaybill` | POST | `/Print/PrintWayBill` | Đường dẫn ĐÃ XÁC NHẬN; tối đa **50 mã/lần**; URL tải **KHÔNG ĐƯỢC TIN** |

Đường dẫn đầy đủ = `base_url.rstrip("/") + DUONG_API[thao_tác]`.

---

## 3. MƯỜI CHỨC NĂNG

| Chức năng đề bài | Hàm trong adapter | Ghi chú |
|---|---|---|
| `authenticate` | `authenticate()` | Không trả token ra ngoài; chỉ `co_token=True` |
| `createOrder` | `createOrder(don)` | 21 trường; `ServiceId=12491`; chống trùng 5 khoá |
| `updateOrder` | `updateOrder(don, ma_van_don=None)` | Dùng lại 21 trường + `WaybillCode` (hợp đồng MOCK) |
| `updateAddress` | `updateAddress(don, ma_van_don=None)` | Áp dụng luật `District=" "` |
| `cancelOrder` | `cancelOrder(ma_van_don, ly_do="")` | Không thử lại mù; timeout ⇒ UNKNOWN |
| `queryTracking` | `queryTracking(danh_sách_mã)` | Tối đa 10; nhận 1 chuỗi hoặc list |
| `estimateFee` | `estimateFee(don)` | Mock trả phí theo công thức MOCK, không phải giá hãng |
| `printWaybill` | `printWaybill(danh_sách_mã)` | Tối đa 50; tải PDF qua chốt SSRF |
| `parseWebhook` | `parseWebhook(goi, tenant_id=None, xac_thuc=None)` | Không mạng; mặc định `da_xac_thuc=False` |
| `normalizeStatus` | `normalizeStatus(ma)` | Bảng rỗng ⇒ mọi mã là "chưa biết", không đoán |

Tương thích hợp đồng cũ: `getOrder`, `trackOrder`, `getShippingFee`, `getShippingLabel`,
`normalizeTrackingStatus` là bí danh mỏng gọi các hàm trên. `tao_adapter("best", ...)` hoạt động
qua `@dang_ky`.

---

## 4. ORDER/ADD — 21 TRƯỜNG

### 4.1 Cảnh báo nguồn

Đề bài xác nhận **21 trường bắt buộc** và các **nhóm dữ liệu** (người gửi, người nhận, địa chỉ
2 cấp, khối lượng, kích thước, COD/ProductPrice, ServiceId, JourneyType, hàng hoá, ghi chú),
nhưng **không liệt kê tên trường**. Google Docs không đọc được. Danh sách dưới đây là **cách
phân rã nội bộ đúng 21 trường**, dùng làm hợp đồng của bộ MOCK.

> **Tên trường WIRE của BEST: CHƯA XÁC MINH.** Không được coi bảng này là schema BEST. Đường
> LIVE bị `SCHEMA_DA_XAC_MINH=False` chặn trước khi gửi.

### 4.2 Bảng 21 trường

| # | Trường nội bộ | Nguồn từ đơn hiện có | Đơn vị / giá trị | Tên wire BEST |
|---|---|---|---|---|
| 1 | `MerchantOrderCode` | `ma_don` / `merchant_order_code` | chuỗi, không rỗng | **CHƯA XÁC MINH** |
| 2 | `ServiceId` | `service_id` / `dich_vu_id` | **12491**; nếu thiếu thì 12491; nếu khác ⇒ TỪ CHỐI | **CHƯA XÁC MINH** |
| 3 | `JourneyType` | `journey_type` / `loai_hanh_trinh` | **1 / 2 / 3**; thiếu ⇒ TỪ CHỐI, **không tự mặc định** | **CHƯA XÁC MINH** |
| 4 | `SenderName` | `nguoi_gui_ten` | chuỗi | **CHƯA XÁC MINH** |
| 5 | `SenderPhone` | `nguoi_gui_sdt` | chuỗi | **CHƯA XÁC MINH** |
| 6 | `SenderProvince` | `nguoi_gui_tinh` | chuỗi | **CHƯA XÁC MINH** |
| 7 | `SenderDistrict` | `nguoi_gui_quan` | thiếu ⇒ **`" "`** (một khoảng trắng) | **CHƯA XÁC MINH** |
| 8 | `SenderAddress` | `nguoi_gui_dia_chi` (+ `nguoi_gui_xa`) | chuỗi | **CHƯA XÁC MINH** |
| 9 | `ReceiverName` | `nguoi_nhan_ten` | chuỗi | **CHƯA XÁC MINH** |
| 10 | `ReceiverPhone` | `nguoi_nhan_sdt` | chuỗi | **CHƯA XÁC MINH** |
| 11 | `ReceiverProvince` | `nguoi_nhan_tinh` | chuỗi | **CHƯA XÁC MINH** |
| 12 | `ReceiverDistrict` | `nguoi_nhan_quan` | thiếu ⇒ **`" "`** (một khoảng trắng) | **CHƯA XÁC MINH** |
| 13 | `ReceiverAddress` | `nguoi_nhan_dia_chi` (+ `nguoi_nhan_xa`) | chuỗi | **CHƯA XÁC MINH** |
| 14 | `Weight` | `khoi_luong_gram` | **GRAM**, số nguyên > 0 | **CHƯA XÁC MINH** |
| 15 | `Length` | `chieu_dai_mm` | **MILIMET**, số nguyên > 0 | **CHƯA XÁC MINH** |
| 16 | `Width` | `chieu_rong_mm` | **MILIMET**, số nguyên > 0 | **CHƯA XÁC MINH** |
| 17 | `Height` | `chieu_cao_mm` | **MILIMET**, số nguyên > 0 | **CHƯA XÁC MINH** |
| 18 | `GoodsName` | `hang_hoa` / `goods_name` | chuỗi, không rỗng | **CHƯA XÁC MINH** |
| 19 | `Cod` | `cod` | **VND**, số nguyên ≥ 0 | **CHƯA XÁC MINH** |
| 20 | `ProductPrice` | `gia_tri_khai` | **VND**, số nguyên ≥ 0 | **CHƯA XÁC MINH** |
| 21 | `Remark` | `ghi_chu` | chuỗi (có thể rỗng) | **CHƯA XÁC MINH** |

Kiểm tra bằng mã: `len(TRUONG_BAT_BUOC_ORDER_ADD) == 21`; gói dựng ra phải có **đúng** tập 21
khoá này (thiếu/thừa đều ném lỗi nội bộ).

### 4.3 Quy tắc giá trị

- **`ServiceId = 12491`**, không phải `12490`. Nếu đơn truyền `service_id=12490` ⇒ **TỪ CHỐI**,
  không gửi. Không có nhánh "mặc định 12490".
- **`JourneyType` ∈ {1, 2, 3}**. Không tự chọn mặc định; thiếu ⇒ TỪ CHỐI.
- **Khối lượng là GRAM**, kích thước là **MILIMET**, tiền là **VND nguyên**. Float bị TỪ CHỐI
  (kể cả `1500.0`) để không có phép làm tròn im lặng.
- Tên/điện thoại/tỉnh/địa chỉ/hàng hoá thiếu ⇒ TỪ CHỐI, không bịa giá trị.
- `District` thiếu ⇒ đúng `" "`; **không** đổi thành `None`/`""`. Đây là luật đã xác nhận.

### 4.4 Bốn khoá chống trùng đi kèm gói

Ngoài 21 trường, gói ghi còn mang:

| Khoá | Nguồn | Ghi chú |
|---|---|---|
| `TenantId` | `don.tenant_id` hoặc credentials | thiếu/không khớp ⇒ **DENY** |
| `CarrierId` | `don.carrier_id`/`carrier_account_id` hoặc credentials | thiếu ⇒ **DENY** thao tác ghi |
| `IdempotencyKey` | `don.idempotency_key` / `don.idem_key` | thiếu ⇒ **DENY** |
| `RequestId` | `don.request_id` hoặc UUID mới mỗi lượt | chỉ chữ/số `._:-`, ≤128 |

`MerchantOrderCode` đã nằm trong 21 trường, nên tổng gói có **25 khoá** (21 + 4). Tên các khoá
này cũng là **hợp đồng MOCK nội bộ**, **CHƯA XÁC MINH** với BEST.

---

## 5. ĐỊA CHỈ 2 CẤP — `BestAddressAdapter`

Lớp riêng trong `app/adapter_best.py`, **không hardcode danh sách tỉnh/quận**.

| Đầu vào | Xử lý |
|---|---|
| `tinh` rỗng/None | **TỪ CHỐI** (không bịa tỉnh) |
| `quan` rỗng/None/toàn khoảng trắng | gửi đúng **`" "`** |
| `quan` có giá trị | giữ nguyên (đã qua `strip`) |
| `dia_chi` rỗng/None | **TỪ CHỐI** |
| `xa` có giá trị | nối vào dòng địa chỉ dạng `"<địa chỉ>, <xã>"` nếu chưa có, để không mất dữ liệu |

- Không có bảng địa giới trong lớp này. Nếu cần đối chiếu, truyền callable
  `tra_cuu_dia_gioi(tinh, quan) -> bool` từ ngoài vào; dữ liệu địa giới thuộc CSDL/dịch vụ.
- `updateAddress` cũng đi qua cùng lớp, nên `ReceiverDistrict=" "` được áp dụng nhất quán.

---

## 6. GIỚI HẠN 10 / 50

| Thao tác | Giới hạn | Hành vi khi vượt | Bằng chứng |
|---|---|---|---|
| `queryTracking` | **10 mã/lần** | **TỪ CHỐI trước khi mở socket**, không cắt bớt | `test_f1`, `test_f2`, `test_f7` |
| `printWaybill` | **50 mã/lần** | **TỪ CHỐI trước khi mở socket**, không cắt bớt | `test_f5`, `test_f6`, `test_f7` |

- Mã rỗng, mã trùng trong cùng lượt, danh sách rỗng ⇒ TỪ CHỐI.
- Mã vận đơn ≤128 ký tự, không ký tự điều khiển.
- Hãng trả về nhiều hơn giới hạn ⇒ TỪ CHỐI đọc, không đoán.

---

## 7. PRINT WAYBILL — KHÔNG TIN URL TRẢ VỀ (SSRF)

`/Print/PrintWayBill` trả URL PDF. URL đó là **dữ liệu NGOÀI**, có thể bị sửa để trỏ vào mạng nội
bộ. Adapter chỉ tải khi thoả **tất cả**:

1. Scheme `http`/`https`; không userinfo (`user@host`), không fragment, không ký tự điều khiển.
2. Host **khớp chính xác** danh sách trắng: `sgp-seaedi.800best.com`,
   `sgp-seaedi-test.800best.com` — hoặc đúng host+cổng của stub trong MOCK.
3. Host hãng: kiểm IP sau khi phân giải; **mọi** địa chỉ phải là IP công khai. DNS trỏ về
   `127.0.0.1`/`10.x`/`169.254.x` ⇒ TỪ CHỐI.
4. Chặn dứt khoát `localhost`, `127.0.0.1`, `::1`, IP private/link-local, và metadata endpoint
   (`169.254.169.254`, `metadata.google.internal`, ...).
5. **Không đi theo redirect** (3xx ⇒ TỪ CHỐI). `http.client` không tự follow; adapter cũng không.
6. Phản hồi ≤ 5 MiB; `Content-Type` phải là `application/pdf` hoặc
   `application/octet-stream` (nếu có).
7. Loopback chỉ mở cho **đúng host+cổng của stub** trong MOCK. URL trả về trỏ `localhost` khác
   stub ⇒ vẫn bị chặn.

Khi tải PDF hỏng sau khi lệnh in **đã gửi thành công**, kết quả là **UNKNOWN**
(`timeout=True`, `can_doi_soat=True`, `in_da_gui=True`, `tai_pdf_that_bai=True`), **không phải**
"in thất bại chắc chắn". Không đưa URL (có thể chở token) vào kết quả; chỉ đưa số byte/host.

Nội dung PDF (khi tải được) nằm ở `KetQuaHang.tho["pdf"]` (một tệp) hoặc
`tho["danh_sach_pdf"]` (nhiều tệp), kèm `dinh_dang="pdf"` và `do_lon_byte`. Đây là **bytes thô**,
không phải chuỗi JSON. `don_hang.sieu_du_lieu_nhan_van_don` hiện chỉ đọc khoá `label`; MOCK có
`label="MOCK-PDF"`, còn đường HTTP/REAL cần một lượt nối metadata riêng (ngoài phạm vi B1) trước
khi màn nhãn đọc được PDF thật.

| Ca phá | Kết quả | Test |
|---|---|---|
| URL `169.254.169.254` | `ssrf-metadata` | `test_g3`, `test_g11` |
| URL `10.0.0.1` | `ssrf-ip-noi-bo` | `test_g2`, `test_g12` |
| URL `localhost` khác stub | `host-cuc-bo` | `test_g13` |
| URL host lạ | `host-bi-tu-choi` | `test_g4`, `test_g14` |
| URL redirect | `chuyen-huong`, không follow | `test_g8`, `test_g15` |
| URL trả HTML | `waybill-khong-phai-pdf` | `test_g9` |
| URL hợp lệ trên stub | tải PDF thật (bytes `%PDF`) | `test_g10`, `test_g16` |

---

## 8. CHỐNG TRÙNG VÀ TIMEOUT

### 8.1 Chống trùng

- Mỗi lệnh ghi mang đủ **5 khoá**: `tenant_id`, `carrier_id`, `merchant_order_code`,
  `idempotency_key`, `request_id`.
- Sổ trong tiến trình giữ kết quả theo
  `(thao_tác, tenant_id, carrier_id, merchant_order_code, idempotency_key)`.
- Cùng khoá ⇒ trả **nguyên kết quả cũ**, gắn `phat_lai_idempotent=True`, **không gửi lượt hai**.
- Tenant khác ⇒ khoá khác; không có đường đọc/ghi chéo tenant.
- Sổ này **không bền qua tiến trình**. Lớp bền là `UNIQUE(tenant_id, idem_key)` của Order Core —
  adapter không thay thế lớp đó, chỉ thêm một chốt.
- `KHOA_CHONG_TRUNG = False` vì tài liệu BEST **CHƯA xác nhận** hãng tự chặn mã đơn trùng.

### 8.2 Timeout / không biết kết quả

Ba kết cục **không gộp**:

| Kết cục | `KetQuaHang` | Ví dụ |
|---|---|---|
| Hãng xác nhận | `ok=True` | 2xx + envelope success |
| Hãng TỪ CHỐI / bị chặn trước khi gửi | `ok=False, timeout=False` | 400/401/403/404/409/422; thiếu tenant; sai 21 trường |
| **KHÔNG BIẾT** | `ok=False, timeout=True` | hết giờ, mạng đứt, 5xx, 408, 2xx không đọc được |

`createOrder` gặp **KHÔNG BIẾT** sẽ:

1. **KHÔNG thử lại mù.** `transport.ChinhSach(so_lan=1, duoc_thu_lai=False)` cho mọi thao tác
   ghi; `KHOA_CHONG_TRUNG=False`.
2. Gọi `queryTracking(merchant_order_code)` **một lần** để kiểm tra.
3. Chỉ khi tra cứu thấy **mã vận đơn** mới nâng thành `ok=True` (`da_kiem_tra_sau_timeout=True`,
   `ket_qua_sau_timeout="da_vao"`).
4. Mọi kết cục khác — kể cả "không tìm thấy" — giữ **UNKNOWN** + `can_doi_soat=True`. Đây là
   chiều an toàn: một lượt đối soát thừa rẻ hơn một vận đơn trùng.

**KHÔNG báo thất bại chỉ vì timeout.** `timeout=True` nghĩa là "chưa biết", không phải "hãng
từ chối". Order Service phải giữ đơn `dang_gui` + cờ đối soát.

---

## 9. XÁC THỰC, BÍ MẬT, TLS

- `authenticate` gửi `Username`/`Password` trong thân JSON tới `/User/Login` (hợp đồng MOCK;
  **CHƯA XÁC MINH** với BEST). Token chỉ giữ trong bộ nhớ, không trả ra `KetQuaHang`, không ghi
  log/audit/response.
- `tho` của mọi kết quả **không chứa** username/password/token. `authenticate()` chỉ trả
  `co_token=True`.
- Thông điệp lỗi **không chép URL/query/thân yêu cầu**; `message` của hãng chỉ được ghi **độ dài**,
  không chép nguyên văn (văn bản ngoài có thể echo credential).
- `http_best.py` dùng `ssl.create_default_context()` — **không** `verify=False`, **không**
  `_create_unverified_context`, **không** `CERT_NONE`, **không** hạ TLS. Có test quét mã nguồn
  (`test_k8`).
- `http_best.py` **không** import `time`, **không** `sleep`; việc chờ thuộc `transport.goi()`.
- Header cấm người gọi ghi đè: `Host`, `Content-Length`, `Transfer-Encoding`; giá trị header
  chứa CR/LF bị TỪ CHỐI.

---

## 10. WEBHOOK VÀ TRẠNG THÁI — CHƯA CÓ BẢNG

### 10.1 `parseWebhook`

- Nhận `dict`, `bytes`, `str`; tối đa 1 MiB; phải là JSON object.
- Bắt buộc có mã vận đơn và trạng thái; thiếu ⇒ `ok=False`.
- **Không tự nhận đã xác thực.** Mặc định `da_xac_thuc=False`. Nếu nơi gọi (B3) truyền
  `xac_thuc=callable`, kết quả mới có `da_xac_thuc=True/False` theo callable đó.
- Không echo payload thô; không trả `Password`/`Token` nếu gói có.
- Sai tenant ⇒ `ok=False`.

### 10.2 `normalizeStatus`

- `BANG_TRANG_THAI_BEST = {}` — **CHƯA CÓ bảng mã BEST**.
- Mọi mã (kể cả `1`, `99`, `"DELIVERED"`) trả `biet_ma=False`, `trang_thai_ap=None`,
  `can_soat=True`, `do_tin_cay="ma_la"`.
- **Không** ánh xạ bừa vào `giao_thanh_cong`/`hoan_hang`; đây là loại sai đắt nhất.
- Muốn điền bảng: đọc tài liệu BEST, đối chiếu từng mã, điền `BANG_TRANG_THAI_BEST`, lật
  `TRANG_THAI_DA_XAC_MINH=True`, thêm test. Chưa làm thì mọi sự kiện là `NEEDS_REVIEW`.

---

## 11. BẰNG CHỨNG CHẠY THẬT

### 11.1 Lệnh và kết quả

```text
$ python3 app/thu/thu_best_adapter.py
...
Ran 118 tests in 1.777s

OK
$ echo $?
0
```

Đo lại bằng `unittest` result (đếm skip chính xác):

```text
TOTAL=118 SKIPPED=0 FAILURES=0 ERRORS=0
EXIT=0
```

- **Số ca: 118.**
- **Số skip: 0.**
- **Số fail: 0.**
- **Số error: 0.**
- **Exit code: 0.**
- Stub: `ThreadingHTTPServer(("127.0.0.1", 0), ...)` — cổng do OS cấp.
- **Không có lượt gọi nào tới `800best.com`.** Test `test_c2` kiểm mọi path; test `test_l3`,
  `test_l5` chặn `http_best.gui_json`/`tai_waybill` bằng mock và chứng minh mock mặc định không
  mở socket.

### 11.2 Bảng 8 endpoint — bằng chứng đường đi

`test_c1` gọi đủ 8 thao tác qua stub và ghim **đúng tập 8 POST path**:

| Endpoint | Test | Kết quả |
|---|---|---|
| `POST /User/Login` | `test_c1`, `test_c4` | 1 lượt, token không trả ra |
| `POST /Order/Add` | `test_c1`, `test_d*`, `test_h*` | 1 lượt; 21 trường; 12491 |
| `POST /Order/Update` | `test_c1` | 1 lượt |
| `POST /Order/UpdateAddress` | `test_c1`, `test_e3` | 1 lượt; District `" "` |
| `POST /Order/Cancel` | `test_c1` | 1 lượt |
| `POST /Order/Query` | `test_c1`, `test_f1` | 1 lượt; 10 mã |
| `POST /Service/EstimateFee` | `test_c1` | 1 lượt; phí VND |
| `POST /Print/PrintWayBill` | `test_c1`, `test_f5`, `test_g*` | 1 lượt; 50 mã; tải PDF qua SSRF |

### 11.3 Bảng đối chứng âm/dương

| Luật | Ca phá (âm) | Đối chứng dương |
|---|---|---|
| `ServiceId=12491` | `test_d3` 12490 ⇒ từ chối | `test_d2` 12491 đi qua |
| `JourneyType 1/2/3` | `test_d4` 0/4/"abc"/thiếu ⇒ từ chối | `test_d4` 1/2/3 đi qua |
| 21 trường | `test_d8` thiếu từng trường ⇒ từ chối, 0 gửi | `test_d1` đủ 21 đi qua |
| Đơn vị GRAM/MILIMET/VND | `test_d5`, `test_d6`, `test_d7` float/0/âm/bool ⇒ từ chối | `test_d5` 1500 g, `test_d6` 200×100×50 mm, `test_d7` 15000/200000 VND |
| `District=" "` | `test_e1`, `test_e2`, `test_e3` thiếu ⇒ `" "` | `test_e9` có giá trị ⇒ giữ nguyên |
| Giới hạn 10 | `test_f2`, `test_f3`, `test_f4`, `test_f7` ⇒ từ chối, 0 gửi | `test_f1` 10 mã đi qua |
| Giới hạn 50 | `test_f6`, `test_f7` ⇒ từ chối, 0 gửi | `test_f5` 50 mã đi qua |
| SSRF | `test_g1`–`test_g9`, `test_g11`–`test_g15`, `test_g17`, `test_g18` | `test_g10`, `test_g16` tải PDF hợp lệ |
| Chống trùng | `test_h1` gọi hai lần ⇒ 1 lượt | `test_h2` tenant khác ⇒ từ chối, `test_h3`–`test_h6` thiếu khoá ⇒ 0 gửi |
| Timeout ⇒ UNKNOWN | `test_h8`, `test_h9`, `test_h12` ⇒ `timeout=True` | `test_h7` tra cứu thấy ⇒ `ok=True`; `test_h10` 500 rồi tra cứu thấy ⇒ `ok=True` |
| HTTP chưa mã hoá | `test_b4`, `test_g7` ⇒ từ chối | `test_b5` bật cờ tường minh ⇒ dựng được, nhưng schema vẫn chặn |
| TLS | `test_k8` không có `verify=False`/`CERT_NONE` | `test_k7` HTTPS đúng cổng được nhận |
| Bí mật | `test_i1`–`test_i6` không thấy secret | `test_c4` token có trong bộ nhớ, không trong kết quả |
| Webhook | `test_j3`–`test_j6`, `test_j11` ⇒ từ chối | `test_j1`, `test_j2` parse hợp lệ |

### 11.4 Trạng thái cây

Trước khi viết tài liệu này:

```text
$ git status --porcelain -uall
?? app/adapter_best.py
?? app/http_best.py
?? app/thu/thu_best_adapter.py
```

Sau khi thêm tài liệu: đúng 4 tệp mới, **không tệp dùng chung nào bị sửa**. Không commit, không
push, không deploy.

---

## 12. BẢNG CHƯA XÁC MINH (bắt buộc đọc trước khi mở LIVE)

| # | Hạng mục | Vì sao chưa xác minh | Đang xử lý thế nào | Cần gì để xác minh |
|---|---|---|---|---|
| U1 | Tên trường wire của `/Order/Add` | Google Docs không đọc được; đề bài chỉ nói "21 trường" | Dùng 21 tên nội bộ; LIVE bị chặn | Danh sách 21 tên từ tài liệu BEST |
| U2 | Hình dạng gói trả lời (`success`, `data`, `Items`, `Url`, ...) | Không có tài liệu | Parser mock; LIVE bị chặn | Response schema từ tài liệu |
| U3 | Cách gửi token (`Authorization: Bearer`) | Không có tài liệu | Quy ước nội bộ cho mock | Header/token scheme thật |
| U4 | Mã trạng thái BEST | Không có bảng | `normalizeStatus` trả "chưa biết" | Bảng mã trạng thái |
| U5 | Mã lỗi BEST | Không có bảng | Chỉ phân loại theo HTTP | Bảng mã lỗi |
| U6 | Hostname test Order/Query `sea-edi-hxtest.800best.com` | Đề bài nói "hostname khác" nhưng chưa xác minh | Không dùng; không nằm trong allowlist | Tài liệu + xác nhận host |
| U7 | Field wire của `/User/Login`, `/Order/Update`, `/Order/UpdateAddress`, `/Order/Cancel`, `/Order/Query`, `/Service/EstimateFee`, `/Print/PrintWayBill` | Không có tài liệu | Hợp đồng mock nội bộ | Tài liệu từng endpoint |
| U8 | Giới hạn tần suất (rate limit) thật | Không có tài liệu | Không tự đặt; chỉ có giới hạn 10/50 đã cho | Tài liệu hãng |
| U9 | Ý nghĩa mã 408/429/5xx của BEST | Không có tài liệu | Dùng quy ước chung của dự án (`loi_hang`) | Tài liệu hãng |
| U10 | Chữ ký webhook | Không có tài liệu | `da_xac_thuc=False`; chờ B3 | Tài liệu + secret |
| U11 | Kích thước/định dạng PDF waybill thật | Chưa gọi hãng | Stub trả PDF giả | Sandbox thật |
| U12 | Có được dùng HTTP cho sandbox không | Đề bài nói test URL là HTTP | Mặc định CHẶN; chỉ mở bằng cờ | Owner duyệt môi trường |

---

## 13. BLOCKED — CÒN THIẾU GÌ ĐỂ REAL PASS

1. **Tài liệu API BEST**: cần URL Google Docs đọc được (hoặc bản PDF) để xác nhận:
   8 endpoint, 21 tên trường, response schema, mã trạng thái/lỗi, cách gửi token, hostname test
   Order/Query.
2. **Credentials sandbox**: chưa có. Không được dùng credentials thật trong lượt này.
3. **Duyệt môi trường**: `CHO_PHEP_SANDBOX`, `CHO_PHEP_PRODUCTION`, `CHO_PHEP_LIVE`,
   `cho_phep_http_khong_ma_hoa` đều đang đóng. Owner phải duyệt bằng văn bản.
4. **HTTPS**: base URL hiện là HTTP. Trước khi gửi credential thật, cần xác nhận BEST có HTTPS
   không; nếu không, phải có kênh bảo vệ khác được duyệt. Adapter **không** tự hạ TLS.
5. **Hợp đồng 21 trường**: cần danh sách chính thức. Hiện là cách phân rã nội bộ.
6. **Bảng trạng thái/lỗi**: cần tài liệu. Hiện mọi mã là `NEEDS_REVIEW`.
7. **Webhook signature**: B3 sở hữu; adapter mới chỉ parse an toàn, chưa xác thực.

**Không được đọc tài liệu này như "BEST đã tích hợp xong".** Đúng mức đang có là:
**MOCK PASS — hợp đồng nội bộ + đường gửi trên stub đã được đo; REAL PASS chưa có.**

---

## 14. NHỮNG VIỆC ĐÃ KHÔNG LÀM (ràng buộc tuyệt đối)

- Không push GitHub, không deploy VPS, không chạy production.
- Không gọi API BEST, kể cả test host; không tạo đơn thật; không dùng credentials thật.
- Không xoá dữ liệu, không reset DB.
- Không sửa `adapter.py`, `adapter_jt.py`, `adapter_vtp.py`, `http_jt.py`, `server.py`,
  `webhook.py`.
- Không thay đổi kiến trúc multi-tenant; mọi truy vấn theo `tenant_id`, thiếu tenant ⇒ **DENY**.
- Không đoán endpoint; 8 endpoint lấy nguyên văn từ đề bài.
- Không ghi secret/token vào log/audit/response; không trả token ra API công khai.
- Không hạ TLS, không tắt xác minh chứng chỉ, không dùng HTTP cho dữ liệu thật (mặc định CHẶN).
- Không commit. Nếu `.git/index.lock` chặn ghi, báo AG-00 — không tự vượt.

---

## 15. CÁCH CHẠY LẠI

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/b1-adapter
python3 app/thu/thu_best_adapter.py
echo $?     # phải là 0
```

Bộ thử tự dựng `VIP_HUB_DATA` tạm, tự dựng stub trên `127.0.0.1:0`, tự đóng stub. Không cần
mạng, không cần credentials, không cần dịch vụ ngoài.

> Ghi chú phạm vi: `app/thu/chay_tat_ca.sh` (AG-00 sở hữu) tự dò `app/thu/thu_*.py` nên tệp
> này sẽ được chạy; nhưng dòng tổng kết "số hãng đăng ký" của runner chỉ import `adapter_jt` và
> `adapter_vtp`, nên nó **không** liệt kê `best`. Đây là hạn chế của tệp dùng chung, không phải
> bằng chứng adapter BEST không tồn tại. B1 không sửa runner.
