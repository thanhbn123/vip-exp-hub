# BEST EXPRESS — NỐI ROUTE HTTP + E2E LOCAL (AG-00)

**Trạng thái bằng chứng: `LOCAL E2E PASS` — KHÔNG phải `REAL PASS`.**
Toàn bộ phép đo chạy trên máy chủ loopback `127.0.0.1`, cổng do OS cấp, CSDL tạm
`tempfile.mkdtemp`. **Không có lời gọi nào tới `800best.com`**, kể cả test host; không có
credentials thật, không có đơn thật, không push/deploy, không đổi `CHO_PHEP_LIVE`.
**BEST-09 giữ `BLOCKED`; BEST-10 giữ `PENDING`, chỉ Owner xác nhận.**

| Hạng mục | Giá trị |
|---|---|
| Agent | AG-00 — tích hợp webhook BEST |
| Nền | `best/integration` @ `5429c6d` |
| Commit gộp | `dd42fdf` trên `best/integration`; `main` = `de740dc`; không push |
| Tệp sửa | `app/server.py` (nhánh phân luồng BEST) · `app/webhook_best.py` (ba lỗi QA: `modified_at` dị dạng/mốc xa, hủy đơn xen giữa đọc/cập nhật) |
| Tệp mới | `app/thu/thu_best_e2e_http.py` · `docs/BEST_EXPRESS_HTTP_E2E.md` |
| Không sửa | `main` · `app/webhook.py` · `app/adapter_best.py` · `app/xac_thuc_best.py` |
| Bộ E2E | `python3 app/thu/thu_best_e2e_http.py` |
| Bộ 51 ca B3 | `python3 app/thu/thu_best_webhook.py` |
| Hồi quy hub | `python3 app/thu/thu_webhook.py` · `python3 app/thu/thu_webhook_jt.py` |

---

## 0. BA CÂU PHẢI ĐỌC TRƯỚC

1. **Hợp đồng hãng BEST CHƯA được xác minh.** Workspace không có URL Google Docs, không có bản
   PDF/trích lục tài liệu BEST. Vì vậy mọi kết luận dưới đây chỉ nói về **hành vi nội bộ đã chọn**
   và **đặc tả đã có trong đề bài B3**, không phải "BEST thật sẽ làm thế".
2. **MOCK PASS ≠ REAL PASS.** Bộ E2E chứng minh route nối đúng bộ xử lý, tenant lấy đúng từ
   account, ACK chỉ sau khi lưu bền, và các nhánh từ chối hoạt động. Nó **không** chứng minh
   tương thích với tài khoản BEST thật.
3. **Đề bài nói 24 mã nhưng chỉ liệt kê 23 con số.** Không bịa mã thứ 24. Bộ xử lý phủ đúng 23 mã
   đã liệt kê + 1 ca "mã lạ" làm đối chứng (24 **lượt kịch bản**, không phải 24 mã hãng).

---

## 1. XÁC MINH HỢP ĐỒNG HÃNG — KẾT QUẢ VÀ PHẦN THIẾU

### 1.1 Nguồn đã tìm/đọc

| Nguồn | Kết quả | Dùng được? |
|---|---|---|
| `docs/BEST_EXPRESS_API_CONTRACT.md` (B1) | Ghi rõ tài liệu BEST là Google Docs **không đọc được**; 8 endpoint/21 trường là phân rã nội bộ, mọi mục U1–U12 `CHƯA XÁC MINH` | Chỉ làm bối cảnh nội bộ |
| `docs/BEST_EXPRESS_INTEGRATION.md` (B3) | Ghi 18 trường payload/23 mã/11 bước là **đặc tả trong đề bài**, không phải tài liệu hãng; mục 11 liệt kê BLOCKED | Chỉ dùng phần "đề bài đã xác nhận" |
| `docs/BEST_EXPRESS_REAL_ACCEPTANCE.md` (B5) | E1–E10 đều chưa có; BEST-02/BEST-05 BLOCKED; BEST-09 BLOCKED | Dùng làm danh mục thiếu |
| `docs/BEST_EXPRESS_SECURITY_REVIEW.md` (B2) | Xác nhận `docs.google.com` không có trong cây; U1–U14 `CHƯA KIỂM CHỨNG` | Dùng làm danh mục thiếu |
| Tìm trong lịch sử git (`git log --all -S docs.google`) | Không có URL tài liệu nào | – |
| `https://open.800best.com/doc` (công khai) | Trang SPA, nội dung rỗng khi fetch; là nền tảng Trung Quốc, **không phải** API VietnamV3 | Không dùng |

**Kết luận nguồn:** không có tài liệu chính thức của BEST Express Việt Nam trong workspace hoặc
được cấp trong lượt này. Mọi mục ở §1.4 là **CHƯA XÁC MINH** theo đúng nghĩa.

### 1.2 Truy vết từng hạng mục đề bài yêu cầu

| Hạng mục đề bài yêu cầu | Nguồn thực tế | Phiên bản / mục | Trạng thái |
|---|---|---|---|
| Cách xác thực callback: chữ ký/token, header, dữ liệu ký | **KHÔNG CÓ** tài liệu hãng | – | **THIẾU / BLOCKED** |
| Payload, trường bắt buộc, kiểu dữ liệu, thời gian | Đề bài B3 (không phải tài liệu hãng) | `docs/BEST_EXPRESS_INTEGRATION.md` §2, bảng 18 trường; mã `b3-best-webhook-2026-10-19` | **CHƯA XÁC MINH với hãng** |
| Định danh sự kiện, chống trùng, thứ tự sự kiện | Thiết kế nội bộ | `app/webhook_best.py` §4–§5 (`_khoa_su_kien`, `_moc_da_ap`); UNIQUE `(carrier_account_id,event_id)` trong `app/csdl.py` | **NỘI BỘ**, không phải đặc tả hãng |
| Nghĩa từng mã trạng thái, đặc biệt 605→606 | Đề bài B3 chỉ cho **danh sách 23 số** và nghĩa 606 "mở lại chiều giao" | `docs/BEST_EXPRESS_INTEGRATION.md` §3–§4; `app/webhook_best.py` `BANG_MA` | **CHƯA XÁC MINH**; 605 là giả thuyết |
| HTTP status và body ACK/NACK; điều kiện gửi lại | ACK thành công: đề bài B3. Phần còn lại: nội bộ | `docs/BEST_EXPRESS_INTEGRATION.md` §8 (`{"Result":1,"Message":""}`) | ACK **đã có căn cứ đề bài**; HTTP/NACK/retry **CHƯA XÁC MINH** |
| Số lượng mã 23 vs 24 | Đề bài B3 liệt kê 23; không có mã thứ 24 | `docs/BEST_EXPRESS_INTEGRATION.md` §3; `app/webhook_best.py` `SO_MA_DE_BAI=24`, `SO_MA_LIET_KE=23` | **ĐÃ ĐỐI CHIẾU**: 23 mã, không bịa thêm |

**Kết luận truy vết:** không hạng mục nào trong 5 hạng mục hợp đồng hãng có nguồn tài liệu BEST
chính thức. Chỉ ACK thành công và danh sách 23 mã là **đặc tả của đề bài**, không phải tài liệu
hãng. Mọi tuyên bố "đã xác minh BEST" là sai cho tới khi Owner cấp tài liệu.

### 1.3 Phần đã có căn cứ (từ đề bài B3, không phải tài liệu hãng)

| Hạng mục | Giá trị | Nguồn |
|---|---|---|
| Endpoint nhận callback | `POST /api/v2/webhook/nhan/<webhook_ma>` (route hub hiện có) | `server.py` + G06 |
| Payload | JSON object 18 trường snake_case; bắt buộc `code_best`, `merchant_order_code`, `status`, `modified_at` | Đề bài B3 |
| ACK thành công | `{"Result": 1, "Message": ""}` — đúng hai khóa | Đề bài B3 (mục 8) |
| Mã 606 | Mở lại chiều giao | Đề bài B3 |
| Danh sách mã | 23 số: 211/203/202/301/302/303/304/309/601/604/666/605/606/701/702/703/704/705/707/708/777/1000/2 | Đề bài B3 |
| Tenant | Chỉ từ `carrier_accounts.tenant_id` của dòng account tra theo `webhook_ma` | Đề bài B3 + G06 |

### 1.4 Phần CHƯA XÁC MINH — không được coi là đặc tả hãng

| # | Hạng mục | Trạng thái | Hệ quả trong mã |
|---|---|---|---|
| U1 | Cách xác thực callback: header, chữ ký/token, dữ liệu ký, secret | **CHƯA XÁC MINH** | Mock dùng HMAC `X-Webhook-Signature` của hub; sandbox/production BEST **BLOCKED** (fail-closed) |
| U2 | Tên/kiểu/độ dài 18 trường payload | **CHƯA XÁC MINH** | Dùng đúng 18 tên trong đề bài B3; không tự nhận là schema hãng |
| U3 | Định danh sự kiện của hãng | **CHƯA XÁC MINH** | Khoá nội bộ `sha256(code_best|moc|status|merchant_order_code)` |
| U4 | Nghĩa 23 mã trạng thái | **CHƯA XÁC MINH** | Mỗi dòng `muc=CHUA_KIEM_CHUNG`; bảng chỉ là giả thuyết phân nhóm |
| U5 | Nghĩa mã 605 và quan hệ 605→606 | **CHƯA XÁC MINH** (chỉ biết 606 mở lại chiều giao) | 605 ánh xạ `hoan_hang` theo giả thuyết; test đo hành vi nội bộ, không đo hãng |
| U6 | HTTP status cho ACK/NACK | **CHƯA XÁC MINH** | Nội bộ: 200 ACK/trùng, 401 xác thực, 403 tenant/account, 404 định danh, 409 xung đột, 413 quá lớn, 422 payload, 500 lỗi lưu/xử lý |
| U7 | Thân NACK và điều kiện hãng gửi lại | **CHƯA XÁC MINH** | NACK của bộ xử lý giữ hai khóa `{"Result":0,"Message":...}`; giả định gửi lại khi không nhận ACK thành công. **Ngoại lệ:** trần chung `webhook.nhan` (429) và lỗi bất ngờ trước nhánh BEST trả `{"loi":...}` — không phải NACK BEST |
| U8 | Thứ tự sự kiện của hãng | **CHƯA XÁC MINH** | Nội bộ so `modified_at`; không dựa vào số mã/thứ hạng |
| U9 | Múi giờ khi `modified_at` không có hậu tố; cửa sổ thời gian hợp lệ | **CHƯA XÁC MINH** | Kế thừa `hub._moc_chuan()`: hiểu là UTC+7 (quy ước hub). Cửa sổ +1 ngày/−5 năm là **chốt an toàn nội bộ**, không phải đặc tả hãng |
| U10 | Đơn vị `weight`/`length`/`width`/`height` | **CHƯA XÁC MINH** | Không tự quy đổi; chỉ kiểm số ≥0 |
| U11 | Rate limit/retry của BEST | **CHƯA XÁC MINH** | Không đặt giả định của hãng; dùng trần nội bộ của hub |

> **Không được đọc bảng §1.2 thành "hợp đồng BEST đã xác minh".** Nó là **đặc tả của đề bài**.
> Muốn nâng mức phải có URL Google Docs/bản PDF, đọc đúng phiên bản, đối chiếu từng mục, rồi
> ghi nguồn + ngày + người đọc.

### 1.5 Chính xác phần còn thiếu — cần Owner cấp

1. **URL Google Docs (hoặc PDF) tài liệu API BEST Express Việt Nam**, quyền đọc cho môi trường này.
2. **Phiên bản/ngày tài liệu** và mục tham chiếu cho: xác thực callback, payload, mã trạng thái,
   ACK/NACK/retry.
3. **Danh sách 24 mã** đầy đủ (nếu đúng là 24) — hiện chỉ có 23 con số trong đề bài.
4. **Nghĩa từng mã**, đặc biệt 605 và 606.
5. **Cơ chế xác thực callback thật** (header/chữ ký/token, dữ liệu ký, secret).
6. **HTTP status + body ACK/NACK + điều kiện gửi lại**.
7. **Môi trường sandbox** + credentials cấp qua kênh an toàn (chỉ sau phê duyệt bằng văn bản).

Cho tới khi có đủ 1–6, **không được mở LIVE** và không được ghi BEST-02/BEST-05 là PASS.

---

## 2. NỐI ROUTE HTTP

### 2.1 Vị trí nhánh

Trong `app/server.py`, route `POST /api/v2/webhook/nhan/<webhook_ma>`:

```text
_gioi_han("webhook.nhan")               ← trần chung, giữ nguyên
tim_account_theo_webhook_ma(url)        ← account + tenant theo ĐỊNH DANH URL
  ├─ tk["hang"] == "best"  → đọc body bằng trần BEST (256 KiB)
  │                          → webhook_best.xu_ly_voi_account(tk, body, headers)
  │                          → trả đúng kq.http / kq.body
  └─ hãng khác             → _doc_body() 64 KiB → webhook.kiem_chu_ky() → nhan_su_kien() (J&T/hub)
```

Nhánh BEST đặt **trước** `webhook.kiem_chu_ky()` và `webhook.nhan_su_kien()`, nên callback BEST
không đi qua HMAC, ACK hay hàng đợi của J&T. Đường J&T/VTP không đổi.

### 2.2 Tenant

- `tk` là dòng `carrier_accounts` tra từ `webhook_ma` trên URL.
- `webhook_best.xu_ly_voi_account(tk, body, headers)` tự đọc `tenant_id` từ `tk`; **không** nhận
  tenant từ payload/query. Payload có `tenant_id`/`tenantId`/`tenant` chỉ bị ghi audit là "claim
  bị bỏ qua".
- Route không truyền tham số tenant nào.

### 2.3 Fail-closed và chốt LIVE

- BEST `mock`: dùng HMAC của hub (`X-Webhook-Signature`) — sơ đồ của chính bộ mô phỏng dự án.
- BEST `sandbox`/`production`: `hub.chon_so_do()` trả `None` ⇒ `webhook_best` trả 401, **không**
  đoán header/chữ ký. Đây là chốt bằng mã, không phải lời dặn.
- `AdapterBEST.CHO_PHEP_LIVE`, `CHO_PHEP_SANDBOX`, `CHO_PHEP_PRODUCTION`,
  `CHO_PHEP_HTTP_KHONG_MA_HOA`, `SCHEMA_DA_XAC_MINH` đều **False**; bộ E2E canh lại (`test_k02`).
- Trần thân BEST là 256 KiB. Nếu vượt, route trả 413 với thân hai khóa `Result/Message`; không
  lưu, không ACK thành công.

### 2.4 ACK chỉ sau khi lưu bền

`webhook_best` INSERT `wh_su_kien` **commit xong** mới cập nhật đơn và ACK. Nếu INSERT nổ, trả
HTTP 500 + `Result=0`, không cập nhật đơn, không ghi lịch sử. Bộ E2E `test_h01` tiêm lỗi đúng
câu INSERT và có đối chứng dương `test_h02`.

### 2.5 Ba lỗi QA độc lập đã vá trong `webhook_best.py`

1. **`modified_at` dị dạng** (`NaN`, `Infinity`, offset `+99:99`): trước đây `hub._moc_chuan()`
   ném `ValueError`/`OverflowError`, lọt ra ngoài `LoiDuLieu`, và route trả 500 `{"loi":...}`.
   Nay `doc_payload()` bắt lỗi, kiểm độ dài mốc 14 chữ số, và trả 422 `{"Result":0,"Message":...}`;
   không chép giá trị thô vào thông điệp. Ca `c12`–`c14`; đối chứng âm N5.
2. **Hủy đơn xen giữa `tim_don()` và bước cập nhật**: trước đây quyết định dựa trên bản đọc cũ,
   nên 606 (hoặc bước thường) có thể ghi đè đơn vừa bị hủy. Nay `_cap_nhat_don_quyet_dinh()` đọc
   lại đơn **trong cùng giao dịch**, và câu UPDATE 606 có thêm `trang_thai!='huy'`. Ca `f07`/`f08`;
   đối chứng âm N6.
3. **Mốc 14 chữ số nhưng xa** (`99999999999999` = năm ~5138, hoặc quá cũ): nếu nhận, watermark
   của đơn bị đẩy lên mốc đó và mọi sự kiện sau bị coi là "đến muộn". Nay `doc_payload()` chỉ nhận
   trong cửa sổ **+1 ngày tương lai / −5 năm quá khứ** (chốt an toàn nội bộ, không phải đặc tả
   hãng). Ca `c15`/`c16`; đối chứng âm N5.

**Hai ngoại lệ hình dạng phản hồi, cố ý không giả vờ là NACK BEST:**
1. Trần chung `webhook.nhan` (429) chạy **trước** khi biết hãng, nên trả `{"loi": ...}` của nền
   tảng. Callback BEST có thể gặp nó khi bị lụt; đây là chốt tải, không phải đặc tả hãng.
2. Một exception ngoài `LoiDuLieu`/`LoiLuuTru` (ví dụ lỗi CSDL bất ngờ trước khi bộ xử lý kịp bọc)
   đi qua `server._chay_that` và trả 500 `{"loi": ...}`. Không có đường nào biến nó thành ACK
   thành công.

---

## 3. E2E QUA HTTP THẬT — PHẠM VI VÀ KẾT QUẢ

### 3.1 Cách dựng

- `ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)` — cổng OS cấp.
- `VIP_HUB_DATA = tempfile.mkdtemp(...)` — CSDL tạm, có đủ cột dấu vết của hub.
- Mọi callback gửi bằng `http.client.HTTPConnection` tới route thật; **không** gọi thẳng
  `webhook_best.xu_ly_voi_account()` trong các ca E2E (bộ 51 ca B3 mới gọi thẳng).
- Fixture payload ghi rõ **giả lập**, không phải dữ liệu BEST thật.

### 3.2 Ma trận ca

| Nhóm | Nội dung | Ca |
|---|---|---|
| A | Callback hợp lệ → ACK đúng, event, đơn, lịch sử, audit | `a01`–`a03` |
| B | Thiếu/sai chữ ký, secret tài khoản khác, sandbox/production BLOCKED, định danh lạ, tài khoản khóa, sai hãng, phân luồng theo account | `b01`–`b10` |
| C | JSON hỏng, thiếu trường, sai kiểu, quá dài, quá lớn, sai UTF-8, không phải object, mã có khoảng trắng, tiền âm, `modified_at` NaN/Inf/offset sai/mốc xa | `c01`–`c16` |
| D | Payload khai tenant khác, tracking/mã đơn chéo tenant, cùng mã hai tenant, tenant hỏng, tracking thuộc account khác cùng tenant | `d01`–`d06` |
| E | Gửi trùng tuần tự, 5 luồng đồng thời, cùng mốc khác định dạng | `e01`–`e03` |
| F | Cũ đến muộn, cùng mốc khác trạng thái, mã nhỏ mốc mới, trạng thái cuối chỉ mở bằng 606, đơn đã hủy, mã lạ, hủy đơn xen giữa đọc/cập nhật | `f01`–`f08` |
| G | 605→606 qua HTTP; bảng 23 mã không bịa 24, mức bằng chứng không bị nâng | `g01`–`g02` |
| H | INSERT `wh_su_kien` nổ → 500, không ACK; đối chứng dương sau khi gỡ lỗi | `h01`–`h02` |
| I | J&T mock vẫn 202/`code=1` và xử lý; J&T sai chữ ký vẫn 401 | `i01`–`i02` |
| J | Không rò token/secret trong response, event, audit, stderr, log, tệp dữ liệu | `j01` |
| K | Nhánh BEST trước HMAC/ACK J&T; tenant không lấy từ payload; chốt LIVE đóng; bộ thử chỉ loopback | `k01`–`k03` |
| L | Tài liệu bàn giao nói đúng phần CHƯA XÁC MINH | `l01` |

**Tổng: 57 ca.** Không có ca bị bỏ qua (`skip`) trừ khi máy không dựng được HTTP server — khi đó
bộ thử phải **HỎNG**, không được im lặng coi là đạt.

### 3.3 Lệnh chạy

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub
python3 app/thu/thu_best_e2e_http.py
echo $?
```

### 3.4 Kết quả đo

> Mục này được điền bằng **output thật** của lượt chạy cuối. Không chép tay số liệu.

Lượt đo cuối trên workspace (HEAD `5429c6d` + vá chưa commit), chạy bằng
`PYTHONDONTWRITEBYTECODE=1`:

```text
$ python3 app/thu/thu_best_e2e_http.py
Ran 57 tests in 0.673s

OK
Ca chạy: 57 · lỗi: 0 · hỏng: 0 · skip: 0
KẾT QUẢ: ĐẠT
$ echo $?
0
```

- **57 ca**, **0 lỗi**, **0 hỏng**, **0 skip**, **exit 0**.
- Không có ca nào bị bỏ qua. Nếu HTTP server loopback không dựng được, `setUpModule` ném lỗi và
  bộ thử ĐỎ — không có đường "skip rồi coi là đạt".
- 57 ca gồm 56 ca hành vi + 1 ca biên body 100 KiB (`c11`) để phân biệt trần 256 KiB của BEST
  với trần 64 KiB mặc định của server.

---

## 4. ĐỐI CHỨNG ÂM / DƯƠNG

### 4.1 Đối chứng dương

- Callback hợp lệ → 200 `{"Result":1,"Message":""}`, event `xong`, đơn đổi trạng thái, 1 dòng
  lịch sử, audit `webhook_best_cap_nhat_don` + `webhook_best_moc_hang` (`test_a01`).
- Sau khi gỡ tiêm lỗi INSERT, cùng payload → 200 và dữ liệu cập nhật (`test_h02`).
- Sandbox/production bị chặn, nhưng cùng payload vào account `mock` thì ACK (`test_b04`/`a01`).

### 4.2 Đối chứng âm — tiêm lỗi trên BẢN SAO

QA độc lập phải sao chép cây sang thư mục tạm, tiêm lỗi, chạy lại **chính bộ E2E**, và xác nhận
test **ĐỎ**. Sáu phép tiêm:

| # | Tiêm lỗi | Ca phải đỏ |
|---|---|---|
| N1 | Bỏ nhánh `if tk["hang"] == "best"` (BEST rơi vào đường J&T) | `a01` (401/ACK sai), `k01` (thứ tự) |
| N2 | Đọc body BEST bằng trần mặc định 64 KiB thay vì 256 KiB | `c11` (thân 100 KiB hợp lệ bị chặn oan); `c06` chỉ đo >256 KiB |
| N3 | Trả ACK trước khi INSERT `wh_su_kien` (hoặc bỏ kiểm `LoiLuuTru`) | `h01` (500 → 200) |
| N4 | Lấy tenant từ payload thay vì `tk` | `d01` (đơn của tenant A không còn được cập nhật; B vẫn không bị đụng nhờ kiểm account) |
| N5 | Bỏ guard `try/except` + cửa sổ thời gian quanh `hub._moc_chuan()` | `c12`–`c16` (NaN/Inf/offset sai/mốc xa phải là 422) |
| N6 | Bỏ đọc lại đơn trong giao dịch + bỏ `trang_thai!='huy'` ở câu UPDATE 606 | `f07`, `f08` (hủy đơn xen giữa đọc/cập nhật) |

**Điều kiện đạt:** mỗi phép tiêm làm ít nhất một ca chuyển từ xanh sang đỏ; gỡ tiêm thì bộ thử
xanh lại. Nếu tiêm mà vẫn xanh, ca đó **không đo** điều nó tuyên bố.

### 4.3 Kết quả đối chứng (đo thật trên bản sao)

Bản sao sạch: `rsync -a --exclude=du-lieu app docs <tmp>/`; mỗi phép tiêm sửa `app/server.py`
hoặc `app/webhook_best.py` trên bản sao, chạy `python3 app/thu/thu_best_e2e_http.py`, rồi khôi phục
từ bản gốc.

| Phép | Kết quả | Ca đỏ thực tế | Kết luận |
|---|---|---|---|
| N1 — bỏ nhánh BEST | **ĐỎ** 47 ca | `a01`–`a03`, `b01`–`b05`, `b10`, `c01`–`c16`, `d01`–`d06`, `e01`–`e03`, `f01`–`f08`, `g01`, `h01`, `h02`, `j01`, `k01` | Nhánh BEST là thứ giữ E2E xanh; bỏ đi là hỏng ngay |
| N2 — trần body 64 KiB | **ĐỎ** 1 ca | `c11` (100 KiB bị chặn oan) | Ca biên phân biệt được trần BEST 256 KiB với trần mặc định 64 KiB |
| N3 — ACK giả khi lưu lỗi | **ĐỎ** 2 ca | `h01`, `h02` | Test thật sự bắt được "ACK thành công khi lưu bền thất bại" |
| N4 — tenant lấy từ payload | **ĐỎ** 2 ca | `d01` (đơn A không được cập nhật — tenant đã bị lấy sai nguồn), `k01` (chốt tĩnh) | Test bắt được việc đổi nguồn tenant; `d01` KHÔNG chứng minh B bị ghi chéo vì lớp kiểm `carrier_account_id` vẫn chặn |
| N5 — bỏ guard `modified_at` | **ĐỎ** 5 ca | `c12` (NaN), `c13` (Infinity), `c14` (offset +99:99), `c15` (năm ~5138), `c16` (quá cũ) | Guard biến lỗi 500 generic thành 422 và chặn mốc xa đóng băng watermark |
| N6 — bỏ đọc lại/hủy | **ĐỎ** 2 ca | `f07` (606), `f08` (bước thường) | Đọc lại trong giao dịch + điều kiện `trang_thai!='huy'` thật sự chặn ghi đè đơn đã hủy |
| Gỡ tiêm (đối chứng dương) | **XANH** 57/57 | – | Cùng bộ thử, cùng môi trường, chỉ khác một yếu tố |

Ghi chú: N4 làm `k01` đỏ vì `k01` soát nguyên văn lời gọi trong `server.py`; đây là hiệu ứng phụ
có chủ ý của chốt tĩnh. Bằng chứng chéo tenant thật nằm ở `d01`.

---

## 5. HỒI QUY BẮT BUỘC

```sh
python3 app/thu/thu_best_webhook.py      # 51 ca B3
python3 app/thu/thu_best_e2e_http.py     # 57 ca E2E
python3 app/thu/thu_webhook.py           # 68 ca hub
python3 app/thu/thu_webhook_jt.py        # 99 ca J&T
python3 app/thu/thu_best_adapter.py      # 118 ca adapter
python3 app/thu/thu_best_auth.py         # 47 ca auth/credential
sh app/thu/chay_tat_ca.sh                # sau khi gộp — xem §7 về các bộ đỏ có sẵn
```

Không đặt biến môi trường trỏ tới BEST thật. Không gọi mạng ngoài loopback.

---

## 6. RÀNG BUỘC ĐÃ GIỮ

- Không mở LIVE/sandbox BEST; không đổi `CHO_PHEP_LIVE` hay cờ xác minh.
- Không push/deploy; không credentials thật; không đơn thật; không sửa CSDL nghiệp vụ.
- Không sửa `main`; không sửa `app/webhook.py` (hub dùng chung).
- Không đoán tài liệu hãng; mọi mục thiếu ghi `CHƯA XÁC MINH`/`BLOCKED`.

---

## 7. BÀN GIAO

| Hạng mục | Giá trị |
|---|---|
| HEAD nền | `5429c6d` (`best/integration`) |
| Tệp sửa | `app/server.py` · `app/webhook_best.py` |
| Tệp mới | `app/thu/thu_best_e2e_http.py` · `docs/BEST_EXPRESS_HTTP_E2E.md` |
| Hợp đồng + nguồn | §1 — chỉ có đề bài B3; tài liệu hãng **THIẾU** |
| Lệnh chạy | §3.3 + §5 |
| Exit / số ca | E2E `57/57` exit 0 · B3 `51/51` exit 0 · hub `68/68` exit 0 · J&T `99/99` exit 0 · adapter `118/118` exit 0 · auth `47/47` exit 0 |
| Đối chứng âm | N1 ĐỎ (47 ca) · N2 ĐỎ (`c11`) · N3 ĐỎ (`h01`,`h02`) · N4 ĐỎ (`d01`,`k01`) · N5 ĐỎ (`c12`–`c16`) · N6 ĐỎ (`f07`,`f08`) · gỡ tiêm xanh lại 57/57 |
| Chưa chạy / chưa đo | REAL PASS; sandbox BEST; TLS/credentials thật; hồi quy toàn bộ đang chạy trên checkout `dd42fdf` |
| Gộp/commit | **ĐÃ COMMIT** `dd42fdf` trên `best/integration`; `main` = `de740dc`; không push/deploy |

### 7.1 Bảng đo cuối (workspace, 19/10/2026)

| Bộ | Lệnh | Exit | Chạy | Đạt | Hỏng | Lỗi | Skip | Ghi chú |
|---|---|---:|---:|---:|---:|---:|---:|---|
| E2E BEST | `python3 app/thu/thu_best_e2e_http.py` | 0 | 57 | 57 | 0 | 0 | 0 | LOCAL+MOCK, HTTP thật |
| B3 webhook | `python3 app/thu/thu_best_webhook.py` | 0 | 51 | 51 | 0 | 0 | 0 | MOCK PASS |
| Hub | `python3 app/thu/thu_webhook.py` | 0 | 68 | 68 | 0 | 0 | 0 | – |
| J&T | `python3 app/thu/thu_webhook_jt.py` | 0 | 99 | 99 | 0 | 0 | 0 | – |
| Adapter BEST | `python3 app/thu/thu_best_adapter.py` | 0 | 118 | 118 | 0 | 0 | 0 | – |
| Auth BEST | `python3 app/thu/thu_best_auth.py` | 0 | 47 | 47 | 0 | 0 | 0 | – |
| G22 regression | `python3 app/thu/thu_g22_regression.py` | 0 | 35 | 35 | 0 | 0 | 0 | – |
| G19 tích hợp | `python3 app/thu/thu_g19_tich_hop.py` | 0 | 8 | 8 | 0 | 0 | 0 | – |
| Header bảo mật | `python3 app/thu/thu_header_bao_mat.py` | 0 | 8 | 8 | 0 | 0 | 0 | – |
| B5 10 cổng | `python3 app/thu/thu_best_qa.py` | 0 | 10 | 2 | 0 | 0 | 8 | Sau commit: BEST-01 `NOT TESTED` (HEAD khác nền B5 `cb23312`); BEST-03…10 BLOCKED/PENDING có lý do |
| Hồi quy toàn bộ | `sh app/thu/chay_tat_ca.sh` trên checkout sạch của `dd42fdf` (`VIP_KHO_DANG_CHAY=sqlite`) | **chờ** | – | – | – | – | – | đang chạy; kết quả điền sau |

**Ghi chú B5 (sau commit):** `python3 app/thu/thu_best_qa.py` → **exit 0 · Ran 10 · 2 đạt · 8 skip**.
`BEST-01` là `NOT TESTED` vì HEAD `dd42fdf` khác nền B5 `cb23312`; đây không phải PASS. Các cổng
phụ thuộc tài liệu/credentials thật vẫn `BLOCKED`/`PENDING`.

**Hồi quy toàn bộ — đọc đúng phạm vi:** chạy trên **bản sao sạch có commit tạm** (vì workspace
thật không cho ghi `.git`), `VIP_KHO_DANG_CHAY=sqlite`, `PYTHONDONTWRITEBYTECODE=1`. Kết quả:
**exit 1 · 2559 ca · 79 bộ chạy thật · 24 bộ đỏ**. E2E shell 41/41, frontend 56+40, E2E BEST
57/57. Danh sách 24 bộ đỏ:

```text
thu_g01_g02.py thu_g19_route.py thu_g20_baomat.py thu_g20_dahang.py thu_g20_hop_dong.py
thu_g20_saoluu.py thu_g21_bimat.py thu_g21_saoluu.py thu_g22_chotcay.py thu_g22_e2e.py
thu_g22_gioihan.py thu_g22_phanloai.py thu_g22_zeroca.py thu_qa_g16.py thu_qa_g17.py
thu_qa_g18.py thu_qa_g20.py thu_qa_g21.py thu_qa_g22.py thu_qa_jt.py thu_qa_soat.py
thu_tich_hop.py thu_webhook_jt.py thu_http.py
```

Các bộ này **không phải hồi quy của vá BEST**: `docs/QA_NGUYENNHAN.md` §3 đã ghi nhận G01/G02,
G19 route, G20, G21, G22, QA G16–G22 và `thu_tich_hop` là đỏ có sẵn ở nền trước đó (cùng loại
lỗi ghim số/khai kho/Chromium/PostgreSQL). `thu_http.py` là bộ **frontend** (ghim trang/Chromium),
không đi qua route webhook BEST. Riêng `thu_webhook_jt.py` trong bản sao `/tmp`
có đúng 2 ca đỏ (`test_k06`, `test_n03`) vì bộ tự kiểm G16/G17 giả định dự án **ngoài** thư mục
tạm; trên workspace thật nó **99/99, exit 0** (đo trực tiếp, xem §7.1). Không dùng 24 bộ đỏ này
để nói vá BEST làm đỏ hồi quy, cũng không dùng chúng để nói toàn bộ hồi quy xanh.

- **BLOCKED:** U1–U11 (§1.4); BEST-09 `BLOCKED`; BEST-10 `PENDING`. Không có REAL PASS.

**Không tuyên bố hoàn tất tích hợp BEST khi tài liệu hãng còn chưa xác minh.**
