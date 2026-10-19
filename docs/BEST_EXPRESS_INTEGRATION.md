# BEST EXPRESS — WEBHOOK + TRACKING (AGENT B3)

**Trạng thái bằng chứng: MOCK PASS — KHÔNG phải REAL PASS.**
Chưa gọi API BEST lần nào, kể cả test host. Không dùng credentials thật, không tạo đơn thật,
không push GitHub, không deploy VPS, không chạy production. Toàn bộ "đơn" trong bộ thử là dòng
CSDL tạm trong `tempfile.mkdtemp`.

| Hạng mục | Kết quả |
|---|---|
| Nền | `best/integration` @ `cb23312` (main `de740dc`) |
| Nhánh làm việc | `b3-webhook` |
| Tệp mới | `app/webhook_best.py` · `app/thu/thu_best_webhook.py` · `docs/BEST_EXPRESS_INTEGRATION.md` |
| Tệp KHÔNG sửa | `app/webhook.py` · `app/server.py` · `app/csdl.py` · `app/adapter.py` · `app/adapter_jt.py` · `app/adapter_vtp.py` |
| Bộ thử MOCK | `python3 app/thu/thu_best_webhook.py` → **exit 0 · 51 ca · 0 lỗi · 0 hỏng · 0 skip** |
| Hồi quy hub | `python3 app/thu/thu_webhook.py` → **exit 0 · 68 ca · 0 lỗi · 0 hỏng** |
| BLOCKED | 2 mục: (1) sơ đồ xác thực BEST thật; (2) nối route trong `server.py` (AG-00 sở hữu) |

---

## 1. Kiến trúc: mô-đun MỚI dùng CHUNG hub, không dựng service độc lập

`webhook.py` đã là hub đa hãng có sẵn: tra `carrier_accounts` theo `webhook_ma` trên URL, chọn
sơ đồ xác thực theo hãng + môi trường, bảng `wh_su_kien` với `UNIQUE(carrier_account_id, event_id)`,
audit, và `don_hang.ap_trang_thai_giao()` làm cửa cập nhật trục giao vận. `webhook.py` đã có
người sở hữu (AG-04/AG-00), nên B3 **không sửa** tệp đó.

`app/webhook_best.py` là lớp đặc thù BEST **gọi lại** các thành phần hub:

- `hub.chon_so_do()` / `hub.xac_thuc_hub_hmac()` — xác thực do hub quyết định, không cho người
  gửi chọn sơ đồ;
- `hub.tim_account_theo_webhook_ma()` — định danh endpoint → tài khoản hãng → tenant;
- bảng `wh_su_kien` — cùng kho thô, cùng UNIQUE chống trùng, cùng cột dấu vết nếu đã migrate;
- `don_hang.ap_trang_thai_giao()` — mọi bước trạng thái **thường**;
- `hub.cot_co()` — dò cột tùy chọn để chạy được trên CSDL chưa migrate;
- `hub._moc_chuan()` — chuẩn hoá `modified_at` về chuỗi 14 chữ số so sánh được.

Chỉ có **một** ngoại lệ: mã `606` mở lại chiều giao phải hạ hạng trạng thái, mà
`ap_trang_thai_giao()` cố ý chặn hạ hạng. Ngoại lệ này nằm trong `_mo_lai_chieu_giao()` với
đúng **một** câu `UPDATE don_hang`, canh bởi `test_f11`. Mọi đường khác không được tự UPDATE.

### Nối route — BLOCKED, cần AG-00

Route hiện có `POST /api/v2/webhook/nhan/<webhook_ma>` trong `app/server.py` đang gọi thẳng
`webhook.kiem_chu_ky()` + `webhook.nhan_su_kien()` (đường J&T/hub). Muốn BEST chạy qua HTTP thật,
AG-00 cần thêm **một nhánh** ngay sau khi đọc `body`, trước lời gọi `webhook.kiem_chu_ky()`:

```python
# server.py — AG-00 sở hữu; B3 KHÔNG tự sửa.
import webhook_best

# ... trong _api(), sau: body = self._doc_body()
if tk["hang"] == "best":
    kq = webhook_best.xu_ly_voi_account(tk, body, self._headers_thuong())
    return self._tra(kq.http, kq.body)
```

Vì sao phải đặt **trước** `webhook.kiem_chu_ky()`: hub chỉ có sơ đồ BEST cho `mock`; với
`sandbox`/`production`, `chon_so_do()` trả `None` (BLOCKED) và `kiem_chu_ky()` sẽ từ chối trước
khi nhánh BEST kịp chạy. Nhánh trên để mô-đun tự trả lời bằng chính sách fail-closed của nó.
Cho tới khi AG-00 cắm nhánh, **đường HTTP end-to-end của BEST là BLOCKED**; bộ thử gọi thẳng
hàm, đúng cách các bộ thử hub hiện có đang làm.

---

## 2. Hợp đồng payload đã xác nhận

Đề bài xác nhận 18 trường. `doc_payload()` chỉ nhận JSON object với đúng các tên snake_case
này; trường lạ được giữ trong payload thô nhưng **không** được dùng để quyết định tenant hay
trạng thái.

| # | Trường | Bắt buộc | Kiểu / kiểm |
|---|---|---|---|
| 1 | `code_best` | CÓ | chuỗi ≤128, không khoảng trắng/ký tự điều khiển |
| 2 | `merchant_order_code` | CÓ | như trên; **không dùng để giải tenant** |
| 3 | `cod` | không | số ≥0 |
| 4 | `product_price` | không | số ≥0 |
| 5 | `status` | CÓ | số nguyên ≥0; ánh xạ ở mục 3 |
| 6 | `status_content` | không | chuỗi ≤4000, giữ nguyên |
| 7 | `freight_fee` | không | số ≥0 |
| 8 | `cod_fee` | không | số ≥0 |
| 9 | `insurance_fee` | không | số ≥0 |
| 10 | `vat_fee` | không | số ≥0 |
| 11 | `return_fee` | không | số ≥0 |
| 12 | `discount` | không | số ≥0 |
| 13 | `modified_at` | CÓ | mốc thời gian đọc được (ISO/numeric); chuẩn hoá 14 chữ số |
| 14 | `total_fee` | không | số ≥0 |
| 15 | `weight` | không | số ≥0; **không tự quy đổi đơn vị** |
| 16 | `length` | không | số ≥0; không tự quy đổi |
| 17 | `width` | không | số ≥0; không tự quy đổi |
| 18 | `height` | không | số ≥0; không tự quy đổi |

Không trường nào được dùng để ghi sổ COD/tài chính. `total_fee` và các phí chỉ được lưu thô;
đối soát tài chính là việc của AG-07, không phải webhook.

---

## 3. Chuẩn hoá trạng thái — 23 mã LIỆT KÊ, không phải 24

**Đề bài ghi "24 mã" nhưng danh sách chỉ có 23 con số.** Không bịa thêm mã thứ 24. Bảng dưới
đây phủ đúng 23 mã liệt kê; bộ thử thêm **1 ca mã lạ** (99999) làm đối chứng, tức **24 lượt
kịch bản**, không phải 24 mã hãng.

**Mọi dòng là `CHUA_KIEM_CHUNG`.** Tài liệu API BEST là Google Docs và chưa đọc được trong môi
trường này. Đề bài chỉ cung cấp **danh sách mã**, không cung cấp nghĩa từng mã. Cột "trạng thái
chung" dưới đây là **giả thuyết phân nhóm** để dựng máy trạng thái — không phải bảng của hãng,
không dùng để tuyên bố đã hiểu tài liệu BEST, không dùng để đối soát tài chính. Khi có tài liệu
thật, thay `BANG_MA` và chạy lại bộ thử.

| Mã | Mô tả giả thuyết | Trạng thái chung | Mở lại? | Mức |
|---:|---|---|:---:|---|
| 211 | Đang vận chuyển/trên đường | `dang_giao` | – | CHUA_KIEM_CHUNG |
| 203 | Đã lấy hàng | `lay_hang` | – | CHUA_KIEM_CHUNG |
| 202 | Đã tiếp nhận đơn | `cho_lay` | – | CHUA_KIEM_CHUNG |
| 301 | Đang giao hàng | `dang_giao` | – | CHUA_KIEM_CHUNG |
| 302 | Giao hàng thành công | `giao_thanh_cong` | – | CHUA_KIEM_CHUNG |
| 303 | Giao hàng thất bại | `giao_that_bai` | – | CHUA_KIEM_CHUNG |
| 304 | Giao thất bại/khách hẹn lại | `giao_that_bai` | – | CHUA_KIEM_CHUNG |
| 309 | Giao hàng thất bại | `giao_that_bai` | – | CHUA_KIEM_CHUNG |
| 601 | Yêu cầu chuyển hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 604 | Đang chuyển hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 666 | Đã hoàn về người gửi | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 605 | Đóng/hoàn tất chiều giao cũ | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| **606** | **MỞ LẠI CHIỀU GIAO** (đặc tả đã xác nhận) | `dang_giao` | **CÓ** | CHUA_KIEM_CHUNG |
| 701 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 702 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 703 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 704 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 705 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 707 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 708 | Đang xử lý hoàn | `hoan_hang` | – | CHUA_KIEM_CHUNG |
| 777 | Hủy đơn | `da_huy` | – | CHUA_KIEM_CHUNG |
| 1000 | Hoàn tất | `giao_thanh_cong` | – | CHUA_KIEM_CHUNG |
| 2 | Đơn mới/tiếp nhận | `cho_lay` | – | CHUA_KIEM_CHUNG |
| *99999* | *Mã lạ ngoài danh sách — ĐỐI CHỨNG, không phải mã hãng* | `None` (chỉ ghi nhận) | – | CHUA_KIEM_CHUNG |

Tổng cộng **24 dòng**: 23 mã liệt kê + 1 dòng đối chứng mã lạ. Dòng 99999 cố ý **không** được
đếm là mã hãng thứ 24.

`777` (`da_huy`) chỉ **ghi nhận**: hủy đơn là quyết định nghiệp vụ của Order Service, không
phải một hạng trong trục giao vận. Webhook không tự đặt `don_hang.trang_thai='huy'`.

Mã lạ (ví dụ 99999): lưu thô, `chung=None`, `can_soat=1`, **không** đổi trạng thái đơn. Không
ném lỗi làm sập đường nhận — mã mới của hãng không được biến thành mất sự kiện.

---

## 4. Máy trạng thái và cặp 605 → 606

Thứ tự đến/đi do **`modified_at`** quyết định, không do số mã và không do thứ hạng. Máy trạng
thái chỉ chặn bước phi lý.

```
None ──► cho_lay ──► lay_hang ──► dang_giao ──► giao_thanh_cong
                                  │                ▲
                                  ├──► giao_that_bai ──► giao_thanh_cong
                                  └──► hoan_hang
606 (mở lại) ──► dang_giao, từ BẤT KỲ trạng thái nào (trừ đơn nghiệp vụ đã hủy)
```

- Ba trạng thái cuối `giao_thanh_cong` / `hoan_hang` / `da_huy` **chỉ** mở lại bằng 606.
- Không có cạnh thường `giao_that_bai → dang_giao`: hạ hạng phải đi 606.
- `605` là trạng thái trước của cặp; `606` là ngoại lệ duy nhất được hạ hạng.

### Bảng 605 → 606 (dữ liệu từ lần chạy thật của bộ thử)

| Ca | Trước | Mã | `modified_at` | Sau | Hạng sau | Lịch sử | Test |
|---|---|---|---|---|---:|---:|---|
| 605 rồi 606 | `dang_giao` | 605 → 606 | 10:00 → 11:00 | `hoan_hang` → `dang_giao` | 3 | 2 dòng, dòng cuối "mở lại chiều giao" | `test_e01` |
| 606 từ trạng thái cuối | `giao_thanh_cong` | 606 | 10:00 | `dang_giao` | 3 | 1 dòng | `test_e02` |
| 606 cũ đến muộn | `hoan_hang` | 606 (11:00) rồi 606 (10:00) | 11:00 → 10:00 | giữ `dang_giao` | 3 | 1 dòng | `test_e03` |
| 606 trên đơn đã hủy nghiệp vụ | `trang_thai='huy'` | 606 | 10:00 | không đổi | – | 0 | `test_e04` |

---

## 5. Chống "cũ đến muộn" — so `modified_at`, không so số mã

Mốc đã áp của mỗi đơn là `MAX(modified_at)` của các sự kiện **thật sự đã áp**, đọc từ audit
`webhook_best_moc_hang`. Sự kiện không được áp (đến muộn, mã lạ, trạng thái cuối, xung đột mốc)
**không** đẩy mốc — đúng bài học G14 của hub.

| Ca | Đến trước | Đến sau | Kết quả | Test |
|---|---|---|---|---|
| Số mã lớn hơn nhưng mốc cũ | 301 @10:00 (`dang_giao`, hạng 3) | 302 @09:00 (`giao_thanh_cong`, hạng 5) | **giữ `dang_giao`**; audit `bo_qua` lý do "đến muộn" | `test_d01` |
| Cùng mốc, khác trạng thái | 301 @10:00 | 302 @10:00 | **giữ `dang_giao`**; lý do "xung đột mốc", cần soát | `test_d03` |
| Số mã nhỏ hơn nhưng mốc mới | 606 @10:00 (`dang_giao`) | 605 @11:00 (`hoan_hang`) | **áp `hoan_hang`** — không giả định mã tăng dần | `test_d02` |
| 606 lặp lại với mốc cũ | 606 @11:00 | 606 @10:00 | giữ `dang_giao` | `test_e03` |

---

## 6. Mười một bước bắt buộc

Tên bước là hợp đồng trong `webhook_best.TEN_BUOC`; `test_f05` canh đúng **thứ tự** cho một
sự kiện hợp lệ, không chỉ canh "có chạy".

| # | Bước | Cài đặt | Bằng chứng |
|---:|---|---|---|
| 1 | `xac_thuc_webhook` | hub chọn sơ đồ; mock dùng HMAC `X-Webhook-Signature`; sandbox/production BEST → **BLOCKED**, không đoán header/chữ ký | `test_f01`, `test_f06` |
| 2 | `xac_dinh_tai_khoan_hang` | phải là `hang='best'`, `kich_hoat=1`, môi trường hợp lệ | `test_f07` |
| 3 | `xac_dinh_tenant` | **chỉ** từ `carrier_accounts.tenant_id`; kiểm tenant tồn tại + `hoat_dong`; thiếu → DENY | `test_b01`, `test_b04` |
| 4 | `kiem_tracking_code` | JSON object, 18 trường, `code_best` bắt buộc, kích thước ≤256 KB | `test_f09`, `test_f10` |
| 5 | `kiem_merchant_order_code` | bắt buộc; đối chiếu `don_hang.ma_don` trong **đúng tenant + account**; không dùng để giải tenant | `test_b02`, `test_b03` |
| 6 | `kiem_trung_su_kien` | khóa bền `code_best|moc_chuẩn|status|merchant_order_code`; UNIQUE của hub là chốt cuối | `test_c01`, `test_c02` |
| 7 | `luu_raw_event_an_toan` | INSERT `wh_su_kien` **commit xong mới ACK**; header lọc danh sách trắng, payload che khóa nhạy cảm | `test_f02`, `test_f03` |
| 8 | `chuan_hoa_trang_thai` | 23 mã + mã lạ; giữ `status`/`status_content` thô | 23 ca `test_a02_*`, `test_a03` |
| 9 | `cap_nhat_don` | so `modified_at`, máy trạng thái, `don_hang.ap_trang_thai_giao` cho bước thường, đặc cách 606 | `test_d01`–`test_e04` |
| 10 | `ghi_lich_su_trang_thai` | Order Service ghi lịch sử cho bước thường; 606 ghi trong cùng giao dịch | `test_a02_*`, `test_e01` |
| 11 | `ghi_audit` | một dòng audit mỗi lượt; không token/secret/chữ ký/nội dung nhạy cảm | `test_f03`, `test_f05` |

---

## 7. Tenant: không dùng `merchant_order_code` để xác định tenant

Luồng bắt buộc:

```
URL /api/v2/webhook/nhan/<webhook_ma>
  → carrier_accounts (webhook_ma, kich_hoat=1)
  → tenant_id CỦA CHÍNH DÒNG ACCOUNT
  → kiểm tenants(id) tồn tại + đang hoạt động
  → tìm đơn: ma_van_don = code_best AND tenant_id = <tenant của account>
  → đối chiếu merchant_order_code = don_hang.ma_don
```

Payload có `tenant_id`/`tenantId`/`tenant` thì **ghi audit là có người cố khai rồi bỏ qua**;
không có đường nào dùng nó để truy vấn. `merchant_order_code` chỉ được dùng **sau** khi đã có
tenant, để đối chiếu cặp mã — không bao giờ là nguồn tenant.

| Ca phủ định | Đối chứng dương | Test |
|---|---|---|
| Account trỏ tenant không tồn tại → 403, không lưu, không ACK 1 | Cùng payload với account tenant thật → áp `cho_lay` | `test_b01` |
| Tracking của A + mã đơn của B → lưu thô, **không** áp đơn A/B | – | `test_b02` |
| Tracking của B + mã đơn của B nhưng callback account A → không đụng B | – | `test_b02` |
| Hai tenant cùng `ma_van_don` → chỉ đơn tenant sở hữu callback đổi | – | `test_b03` |
| Payload khai tenant B → vẫn dùng tenant A, audit "claim bị bỏ qua" | – | `test_b04` |

---

## 8. Phản hồi và tính bền vững của ACK

Đặc tả đã xác nhận **chỉ** ca thành công:

```json
{"Result": 1, "Message": ""}
```

Mô-đun trả đúng hai khóa này, không thêm trường, cho cả lượt mới và lượt trùng. Chỉ ACK `Result=1`
**sau khi** dòng `wh_su_kien` đã commit. Nếu INSERT thô nổ (ví dụ `disk I/O error`), trả HTTP 500
với `Result != 1`, không cập nhật đơn, không ghi lịch sử — `test_f02` có **đối chứng dương**
(cùng payload chạy thật thì ACK) và **đối chứng âm** (chỉ câu INSERT `wh_su_kien` nổ).

Hình dạng phản hồi lỗi (`{"Result": 0, "Message": "..."}`) **CHƯA có trong đặc tả**; đề bài chỉ
chốt ca thành công. Mô-đun giữ đúng hai khóa, không bịa thêm trường, và ghi rõ đây là lựa chọn
triển khai chưa được hãng xác nhận.

Mã HTTP đang dùng: 200 ACK/trùng · 401 xác thực · 403 tenant/tài khoản · 409 xung đột account ·
413 quá lớn · 422 payload sai · 500 không lưu được/lỗi xử lý. Đây là **lựa chọn nội bộ**, không
phải đặc tả BEST.

---

## 9. Bảo mật

- **Không gọi mạng.** Tệp không import `requests`, `httpx`, `urllib.request`, `http.client`,
  `socket`; không có đường LIVE. Đường BEST sandbox/production hiện **BLOCKED**.
- **Không ghi secret/token/chữ ký** vào `payload_tho`, `headers_json`, audit hay response.
  Header chỉ lưu danh sách trắng (`content-type`, `content-length`, `user-agent`, `host`,
  `x-request-id`, `x-best-timestamp`, `timestamp`); `X-Webhook-Signature`, `Authorization`,
  `Cookie` bị bỏ. Payload che mọi khóa chứa `token`/`secret`/`password`/`signature`/`cookie`.
- **Tenant fail-closed:** không xác định được tenant ⇒ DENY; mọi truy vấn đơn đều kèm
  `tenant_id`; truy vấn `wh_su_kien` JOIN `carrier_accounts` để tenant nằm trong điều kiện;
  đường đặc cách 606 kèm thêm `carrier_account_id`.
- **Không hạ TLS, không tắt xác minh chứng chỉ, không dùng HTTP cho dữ liệu thật:** mô-đun
  không mở kết nối nào, nên không có cấu hình TLS nào bị thay đổi.
- **Không xóa dữ liệu, không reset DB.** Bộ thử dùng CSDL tạm.

---

## 10. Bảng chứng chạy thật

### 10.1 Bộ thử mới

```console
$ python3 app/thu/thu_best_webhook.py
...
Ran 51 tests in 0.150s

OK
Ca chạy: 51 · lỗi: 0 · hỏng: 0 · skip: 0
KẾT QUẢ: MOCK PASS
```

- **Exit code: 0** (đo bằng `PIPESTATUS[0]` khi chạy qua pipe).
- **51 ca**, **0 skip** (không có ca bị bỏ). Các mục BLOCKED ở mục 11 là giới hạn bằng chứng,
  không phải ca test bị bỏ.
- 23 ca riêng cho 23 mã + 1 ca mã lạ (tổng 24 lượt kịch bản).
- Bảng 23 mã in ra từ chính `BANG_MA`, không chép tay.
- Bảng 605→606 và bảng "cũ đến muộn" in từ dữ liệu của các ca thử đã chạy.
- Các ca phủ định đều có **đối chứng dương**: sai chữ ký → cùng thân đúng chữ ký thì ACK
  (`test_f01`); BEST sandbox BLOCKED → cùng payload vào tài khoản mock thì ACK (`test_f06`);
  sai hãng → cùng thân qua định danh BEST thì ACK (`test_f07`); thiếu tenant → cùng payload với
  tenant thật thì áp (`test_b01`); lưu thất bại → cùng payload chạy thật thì ACK (`test_f02`).

### 10.2 Hồi quy hub hiện có

```console
$ python3 app/thu/thu_webhook.py
Ran 68 tests in 0.093s

OK
```

**Exit code: 0**, 68 ca, 0 lỗi. Việc thêm mô-đun mới không đổi hành vi hub/J&T/VTP.

### 10.3 Phạm vi tệp

```console
$ git status --short
?? app/thu/thu_best_webhook.py
?? app/webhook_best.py
```

Sau khi thêm tài liệu này, danh sách có thêm `?? docs/BEST_EXPRESS_INTEGRATION.md`. Không có tệp
được bảo vệ nào bị sửa. Không commit/push (đề bài chỉ cho LOCAL).

---

## 11. Mục CHƯA KIỂM CHỨNG và BLOCKED

| # | Mục | Trạng thái | Vì sao / cần gì |
|---:|---|---|---|
| 1 | Nghĩa 23 mã trạng thái BEST | **CHUA_KIEM_CHUNG** | Tài liệu API BEST là Google Docs, chưa đọc được. Đề bài chỉ cho danh sách mã. Bảng ở mục 3 là giả thuyết phân nhóm. Cần: quyền đọc tài liệu + đối chiếu từng mã. |
| 2 | Số lượng "24 mã" | **CHÊNH LỆCH** | Đề bài ghi 24 nhưng liệt kê 23. Không bịa mã thứ 24; bộ thử phủ 23 + mã lạ. Cần: danh sách đầy đủ từ hãng. |
| 3 | Cơ chế xác thực callback BEST | **BLOCKED** | Đề bài không xác nhận header/chữ ký. Hub không có sơ đồ BEST cho sandbox/production ⇒ fail-closed. Cần: tài liệu BEST + secret thật (không dùng trong đợt này). Gateway demo cũ có `X-BEST-Sign` nhưng đó là **cấu hình demo của G01**, không phải tài liệu hãng — không dùng làm căn cứ. |
| 4 | Nối route HTTP | **BLOCKED** | `server.py` thuộc AG-00; B3 không sửa. Cần AG-00 cắm nhánh ở mục 1. Bộ thử gọi thẳng hàm. |
| 5 | REAL PASS | **BLOCKED** | Cấm gọi API BEST, kể cả test host. Chưa có credentials thật. Đây là MOCK PASS. |
| 6 | Endpoint/phương thức HTTP/content-type của BEST | **CHUA_KIEM_CHUNG** | Đề bài chỉ xác nhận payload/response/11 bước. Mô-đun nhận JSON POST tại route hub hiện có; không tự đặt endpoint của hãng. |
| 7 | Múi giờ của `modified_at` khi chuỗi không có hậu tố | **CHUA_KIEM_CHUNG** | Dùng `hub._moc_chuan()`: chuỗi không hậu tố được hiểu là UTC+7 (quy ước J&T của hub). Cần xác nhận BEST. |
| 8 | Đơn vị `weight`/`length`/`width`/`height` | **CHUA_KIEM_CHUNG** | Chỉ kiểm số ≥0, không tự quy đổi gram/cm/kg. Cần tài liệu BEST. |
| 9 | Hình dạng phản hồi lỗi | **CHUA_KIEM_CHUNG** | Đặc tả chỉ chốt `{"Result":1,"Message":""}`. Ca lỗi dùng cùng hai khóa, `Result=0`. |
| 10 | Tạo tài khoản BEST qua UI/API | **ngoài phạm vi B3** | Cần `carrier_providers`/adapter BEST (B1) và màn hình cấu hình (B4). B3 chỉ xử lý callback khi account đã tồn tại. |

---

## 12. Cách chạy lại

```bash
cd /Users/viporder/orca/workspaces/vip-express-hub/b3-webhook

# Bộ thử BEST (MOCK, in bảng chứng)
python3 app/thu/thu_best_webhook.py

# Hồi quy hub hiện có
python3 app/thu/thu_webhook.py
```

Không đặt biến môi trường nào để trỏ tới BEST thật. Bộ thử tự tạo `VIP_HUB_DATA` tạm; không
chạm CSDL thật, không gọi mạng. Nếu cần chạy trong CI, dùng đúng hai lệnh trên và đọc mã thoát.
