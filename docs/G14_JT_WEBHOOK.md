# G14 — TÍCH HỢP WEBHOOK J&T: KIỂM CHỨNG, MỘT LỖI ĐÃ VÁ, VÀ DANH SÁCH CHỜ HÃNG

**Người làm:** AG-03 WEBHOOK ENGINEER · **Ngày:** 15/10/2026 · **Mốc mã khi bắt đầu:** `de740dc`
**Phạm vi đo:** worktree Orca `Projects-vip-express-hub`, CSDL thử riêng `VIP_HUB_DATA=/tmp/veh_data_ag03`.
**CSDL THẬT:** không đụng tới. `gateway/` (bản G01 đã nghiệm thu): **không sửa một dòng nào**.
**Hãng thật:** không gọi. `CHO_PHEP_LIVE` của mọi adapter: không đụng.

> Câu quan trọng nhất của tài liệu này nằm ở **§4**: một lỗi thật, đo được, đã vá — và nó chỉ
> hiện ra trên **CSDL đã migrate**, tức là CSDL thật, nên bộ thử cũ (chạy trên CSDL chưa
> migrate) xanh suốt trong khi hệ thống thật sai.

---

## 0. PHẠM VI — ĐỌC TRƯỚC KHI ĐỌC SỐ

| Đã đo | Chưa đo / nằm NGOÀI |
|---|---|
| `app/webhook.py` + `app/trang_thai_hang.py` trên CSDL SQLite schema v8, một tiến trình | Đa tiến trình dưới tải (đo riêng ở `app/thu/dong_thoi/`) |
| Máy chủ HTTP thật `app/server.py` bind `127.0.0.1`, cổng do hệ điều hành cấp | Callback THẬT của J&T (không có credentials — `V-13906-05` CHƯA CẤP) |
| Chữ ký `jt_digest` theo **công thức trong tài liệu** | Chữ ký thật của J&T: **khoá ký và chuỗi đem đi ký CHƯA có tài liệu** (§2, §8) |
| Mã trạng thái J&T theo bảng tham số `103…121` đã đọc | Nghĩa mã `110` (`V-13906-04`), bộ mã thứ hai `10/50/92/94/100`, mã `121` |
| Chống trùng cưỡng chế bằng `UNIQUE(carrier_account_id, event_id)` | J&T có đẩy trùng hay không (câu hỏi 10) |
| Chính sách thử lại **của phía nhận** (trần + backoff + DLQ) | Chính sách thử lại **của J&T** (câu hỏi 9) — CHƯA có |

---

## 1. W01 — KHẢO SÁT: CÁI GÌ ĐÃ CÓ, VÀ CÁI GÌ **KHÔNG** DỰNG LẠI

Đã có sẵn và **được giữ nguyên** (khảo sát, không viết lại):

| Thành phần | Ở đâu | Vai trò |
|---|---|---|
| Gateway G01 đa hãng | `gateway/` (7 tệp, CSDL riêng `gateway/du-lieu/gateway.db`) | Bản demo đã nghiệm thu. **Không sửa.** Nó KHÔNG tenant-aware (khoá chống trùng theo `(hang, event_id)`, không có `tenant_id`) — đó là lý do đường nghiệp vụ là `app/webhook.py`, không phải chỗ này |
| Cổng webhook tenant-aware | `app/webhook.py` (695 dòng ở `de740dc`) | Đường ĐANG CHẠY: `server.py` gọi `tim_account_theo_webhook_ma` → `kiem_chu_ky` → `nhan_su_kien` |
| Định tuyến theo tài khoản hãng | `webhook_ma` trên URL + `carrier_accounts.webhook_ma UNIQUE` | Định danh công khai, khoanh đúng MỘT tài khoản |
| Ánh xạ trạng thái | `app/trang_thai_hang.py` | Một chỗ duy nhất quyết định nghĩa mã hãng (`quyet_dinh`) |
| Chống trùng | `UNIQUE(carrier_account_id, event_id)` trong `csdl.SCHEMA` | Cưỡng chế bằng CSDL (hợp đồng §12) |
| Hàng đợi / retry / DLQ / replay | `webhook._vong_lap`, `_chay_mot`, `yeu_cau_replay` | Trần số lần thử + backoff có trần + DLQ + replay có trần |
| Máy trạng thái đơn | `don_hang.ap_trang_thai_giao` + `don_lich_su` | Hai trục tách rời (hợp đồng §10, §11) |
| Polling dự phòng | `app/polling.py` | Cùng một chỗ quyết định nghĩa mã, hạn mức theo tenant |

**Kết luận W01: KHÔNG dựng lại gateway.** G14 chỉ sửa `app/webhook.py` (1 tệp) + thêm bộ thử.
Ca `thu_webhook_jt.test_j04` canh `gateway/` còn nguyên 7 tệp và còn dùng CSDL riêng.

Đường đi hiện tại của một callback (đo bằng mã, không bằng đọc tài liệu):

```
POST /api/v2/webhook/nhan/<webhook_ma>
  ├─ server.py: _gioi_han("webhook.nhan")            → trần thô theo webhook_ma
  ├─ webhook.tim_account_theo_webhook_ma(ma)         → carrier_accounts WHERE kich_hoat=1
  ├─ webhook.kiem_chu_ky(tk, headers, body)          → chọn sơ đồ theo (hãng, môi trường)
  │     sai → ghi audit `webhook_chu_ky_tu_choi`, trả 401, KHÔNG lưu
  ├─ webhook.nhan_su_kien(tk, body, headers)         → INSERT wh_su_kien (UNIQUE cưỡng chế)
  └─ webhook._chay_mot → _xu_ly
        ├─ doc_su_kien_hang    → khung chung, nói rõ mã đến từ đâu
        ├─ tenant_tu_account   → tenant CHỈ từ carrier_accounts        ← G14 gọi tên ra
        ├─ tth.quyet_dinh      → mã hãng → trạng thái chuẩn (hoặc None)
        ├─ SELECT don_hang WHERE ma_van_don=? AND tenant_id=? AND carrier_account_id=?
        ├─ watermark()         → chặn bản tin cũ bằng mốc CỦA HÃNG      ← G14 vá (§4)
        ├─ don_hang.ap_trang_thai_giao(tenant_id, don_id, ...)          → rank guard
        ├─ luu_dau_vet         → cột + audit (mã gốc, mô tả gốc, nguồn tài liệu, độ tin cậy)
        └─ csdl.audit          → mọi nhánh đều để lại dấu vết
```

---

## 2. W02 — HỢP ĐỒNG CALLBACK J&T: TÀI LIỆU NÓI GÌ, VÀ CHỖ NÀO **CHƯA** NÓI

Nguồn: trích lục **trong repo** — `docs/JT_CAU_HOI_CHINH_THUC.md` (câu 1–5) và
`docs/G12_JT_DANG_KY.md` mục 5. Cả hai chép từ `open.jtexpress.vn/apiDoc/logistics/statusFeedback`
đọc bằng trình duyệt 14–15/10/2026. Trang là SPA nên `fetch` tĩnh trả vỏ rỗng ⇒ **trích lục
trong repo là nguồn sự thật**, không phải trang web.

Bảng dưới đây **cũng nằm trong mã** (`webhook.HOP_DONG_CALLBACK`), máy đọc được, và có ca thử
canh (`test_a01`–`test_a02`). Ba mức: `DA_TAI_LIEU` · `SUY_RA` · `CHUA_TAI_LIEU`.

| Trường | Tài liệu nói gì | Mức |
|---|---|---|
| Endpoint phía nhận | URL do **mình** khai cho J&T. Đường của hub: `POST /api/v2/webhook/nhan/<webhook_ma>` | `SUY_RA` — URL công khai **CHƯA CẤP** (`V-G11-01`) |
| **Phương thức HTTP** | **KHÔNG NÓI** | **`CHUA_TAI_LIEU`** |
| Thân yêu cầu | form (`application/x-www-form-urlencoded`) có trường `bizContent` | `DA_TAI_LIEU` |
| Header bắt buộc | `apiAccount` · `digest` · `timestamp` ("đúng ba header như mọi API khác") | `DA_TAI_LIEU` |
| **Công thức chữ ký** | `digest = base64( md5-BYTES( <chuỗi JSON của bizContent> + privateKey ) )` — md5 ra **mảng byte** rồi mới base64 | `DA_TAI_LIEU` |
| **Khoá ký chiều callback** | **KHÔNG NÓI** (câu 6): `privateKey` của mình hay khoá riêng J&T cấp? | **`CHUA_TAI_LIEU`** |
| **Chuỗi đem đi ký** | **KHÔNG NÓI** (câu 7): chỉ `bizContent`, hay cả thân form `bizContent=...`? | **`CHUA_TAI_LIEU`** |
| **Ví dụ đối chiếu** | **KHÔNG CÓ** (câu 7 xin: chuỗi gốc · khoá che bớt · digest kết quả) | **`CHUA_TAI_LIEU`** |
| Định danh sự kiện | Trong `details` **không có** mã sự kiện duy nhất; chỉ có `billCode` + `scanTime` + `scanTypeCode` (câu 10) | `SUY_RA` — khoá tổ hợp **do mình chọn**, hãng chưa xác nhận |
| Mốc thời gian bản quét | `scanTime` trong `details`; hai định dạng đã thấy: `"2024-06-05 15:57:04"` và `"2024-06-21T13:23:56"` (câu 15) | `DA_TAI_LIEU` (định dạng chuẩn: chưa) |
| **`timestamp` ở header** | "毫秒 / 时区：UTC+7" (câu 14 như câu 12): mốc Unix thật **(a)** hay giờ treo tường UTC+7 quy đổi **(b)**? Lệch **đúng 7 tiếng**, mà chữ ký vẫn đúng | **`CHUA_TAI_LIEU`** — mã đang hiểu theo **(a)** |
| **Chính sách thử lại của J&T** | **KHÔNG NÓI** (câu 9) | **`CHUA_TAI_LIEU`** |
| **Phản hồi xác nhận** | Chỗ DUY NHẤT nhắc tới: câu 9 — *"khi chúng tôi trả về mã khác `code=1`"* ⇒ phản hồi là JSON có trường `code`, `code=1` là được nhận | **`CHUA_TAI_LIEU`** — mã HTTP nào, còn trường nào, 200/202 có bị coi là hỏng: CHƯA có |
| Dữ liệu tiền trong callback | `codMoney`/`goodsValue`/`itemsValue` (câu 29) và ánh xạ `area` (D-9) chưa chốt | **`CHUA_TAI_LIEU`** ⇒ **không suy ra tiền từ callback** (§18) |

### 2.1 Khoảng hở THẬT tìm được ở tầng phản hồi (không sửa được ở làn này)

Route trước đây trả `202 {"ket_qua": "da_nhan", "su_kien_id": N}` và
`200 {"ket_qua": "da_nhan_truoc_do", ...}` — **không có trường `code`**. Nếu J&T đúng như câu 9
(chỉ chấp nhận `code=1`) thì **mọi callback của họ bị coi là hỏng và bị đẩy lại**; chống trùng ở
tầng CSDL cứu được dữ liệu nhưng không cứu được tải.

**ĐÃ ĐÓNG 15/10/2026** — AG-00 cắm `webhook.phan_hoi_xac_nhan()` vào route `app/server.py`:
lượt mới `202` và lượt trùng `200` đều mang thêm `code=1` + `msg`, `ket_qua` cũ **giữ nguyên**
(không phá ai đang đọc). AG-00 **cố ý giữ nguyên mã HTTP cũ** vì trích lục không nói mã HTTP nào
là đúng — đổi nó là đoán.

> ⚠️ **Bản vá này KHÔNG có nghĩa "hợp đồng phản hồi đã được xác minh".** Cái đã biết chỉ là một
> mảnh của câu 9: phản hồi có trường `code`, `code=1` là được nhận. `B3` **vẫn CHƯA có trả lời**:
> mã HTTP nào là đúng, còn trường nào khác, `200`/`202` có bị J&T coi là hỏng không. Mức của
> trường `phan_hoi_xac_nhan` trong `webhook.HOP_DONG_CALLBACK` vẫn là `CHUA_TAI_LIEU` và ca
> `test_a02` canh đúng điều đó; ca `test_i05` khẳng định `code=1` ở **cả hai nhánh** và khẳng
> định luôn rằng mức tài liệu KHÔNG được nâng lên.

### 2.2 Điều KHÔNG làm: không đoán thuật toán ký

Công thức `base64(md5(bizContent + privateKey))` **là của tài liệu**, không phải của người viết.
Nhưng nó chưa đủ để nghiệm thu: thiếu **khoá** và thiếu **chuỗi đem đi ký**. Vì vậy:

- mức xác thực của `jt_digest` giữ nguyên **`DOCUMENTED`**, không tự nâng lên `SANDBOX VERIFIED`
  hay `LIVE VERIFIED` (ca `test_a05` canh: không nhánh nào được khai mức cao hơn thực tế);
- khoá dùng để kiểm là `webhook_secret` của chính `carrier_account` — **một giả định có ghi
  chú**, và `test_b04` ghim cách hiểu `timestamp` theo (a) để nếu ai đổi sang (b) thì bộ thử đỏ
  và buộc phải trưng căn cứ từ hãng;
- `test_a03` kiểm **từng byte**: biến thể `hexdigest`-rồi-base64 bị **từ chối**, đúng như tài
  liệu ("md5 ra mảng byte rồi mới base64"). Đây là chỗ dễ sai nhất và sai thì im lặng.

---

## 3. W03 — GIẢI TENANT: MỘT NGUỒN, VÀ BỐN LỚP CHẶN CHÉO TENANT

`tenant_id` **chỉ** đến từ dòng `carrier_accounts` tra được trên URL (hợp đồng §1, §12). G14 gọi
tên bước ấy ra thành `webhook.tenant_tu_account(tenant_id, account_id)` để soi được, và `_xu_ly`
dùng nó cho **mọi** câu truy vấn về sau.

Payload có khai `tenant_id` thì: **ghi lại một dòng audit** `webhook_claim_tenant_bi_bo_qua` rồi
**bỏ qua**. Ca `test_d07` chứng minh: payload khai tenant B, đơn của tenant A **vẫn được cập nhật
đúng** — tức là lời khai trong payload không có trọng lượng nào.

Bốn lớp chặn chéo tenant, mỗi lớp có ca thử riêng:

| Lớp | Chặn cái gì | Ca thử |
|---|---|---|
| ① Truy vấn đơn có `tenant_id` **và** `carrier_account_id` | Đơn của tenant khác, hoặc đơn gắn sai tài khoản hãng | `test_d04`, `test_d05` |
| ② Khoá chống trùng theo **account**, không theo hãng | Hai tenant cùng hãng không nuốt sự kiện của nhau | `test_c04` |
| ③ Hàm `ap_trang_thai_giao(tenant_id, ...)` — `tenant_id` là tham số **bắt buộc đứng đầu** | Gọi thiếu là `TypeError`, không hỏng im lặng | `thu_webhook.test_i03` (G06) |
| ④ `doi_chieu_hanh_trinh` kiểm **bất biến** trên toàn bộ sự kiện đã xử lý | Rò chéo tenant ở tầng dữ liệu, kể cả dòng bị nhồi thẳng bằng SQL | `test_h04` |

Ca `test_h04` là **phép kiểm tự chứng minh** (§12.1): nhồi thẳng
`UPDATE wh_su_kien SET don_id=<đơn của tenant khác>` rồi xem phép đối chiếu có bắt được không.
Không có ca này thì `lech_tenant == []` không chứng minh được gì. Đo được: bắt đúng 1 dòng, nêu
đúng cả hai tenant. Và báo cáo của tenant B **không** phơi dòng của A ra (cách ly giữ nguyên).

---

## 4. W04 — MÃ `110`, BỘ MÃ THỨ HAI, VÀ MỘT LỖI THẬT ĐÃ VÁ

### 4.1 Chặn cứng mã `110` (vẫn nguyên trạng, có thêm ca thử)

`110` nằm trong sổ `trang_thai_hang.NHAP_NHANG`: tài liệu tự mâu thuẫn (bảng tham số ghi
*Arrival*, ví dụ trả lời ghi *Quét kiện có vấn đề* — hai nghĩa ngược chiều). Hệ thống **không
chọn một nghĩa**: `quyet_dinh("jt", 110).trang_thai_ap is None`, nhãn `AMBIGUOUS`, `can_soat=1`,
và một chốt cứng độc lập với mọi nhánh: mã nhập nhằng **không bao giờ** ra `giao_thanh_cong` /
`hoan_hang`, kể cả khi ai đó nhồi thẳng vào sổ `NGHIA_DA_CHOT` (`test_f03`).

### 4.2 Bộ mã THỨ HAI cũng chưa kiểm — nên nó cũng bị chặn

Tài liệu còn một bộ mã khác trong **ví dụ trả lời** của chính nó: `10/50/92/94/100/110`. Trong
bộ đó `100` = "Ký nhận" (đã giao) và `92` = "Hàng đến". Bộ này **chưa được hãng xác nhận**
(câu hỏi 13), nên nó phải đi đúng đường của **mã lạ**: giữ nguyên đơn + `NEEDS_REVIEW`.
Ca `test_f05` gửi cả năm mã `10/50/92/94/100` và khẳng định đơn **không nhúc nhích** và cả năm
đều bị đánh dấu cần soát. Đây là chỗ dễ mất tiền nhất nếu ai đó "tiện tay" thêm `100` vào bảng
ánh xạ vì nó trông có nghĩa.

### 4.3 LỖI ĐÃ VÁ — mã KHÔNG ĐƯỢC ÁP vẫn đầu độc watermark của đơn

**Phát hiện:** `luu_dau_vet()` ghi cột `wh_su_kien.hang_moc_thoi_gian` cho **mọi** sự kiện đọc
được — kể cả sự kiện **không được áp** (mã nhập nhằng `110`, mã chỉ ghi nhận như `121`, mã lạ).
`watermark()` lại ưu tiên đọc từ cột đó. Nguồn thứ hai (audit `webhook_moc_hang`) thì chỉ ghi khi
**đã áp** — **hai nguồn nói khác nhau, và nguồn được ưu tiên là nguồn sai.**

**Hậu quả (đo được, không suy đoán):** một bản quét `110` lúc 10:00 (không đổi trạng thái đơn —
đúng như thiết kế) đẩy watermark lên 10:00. Bản quét `113 Delivered` lúc 09:00 đến sau bị chặn
với lý do *"đến muộn"* ⇒ **đơn đã giao mà hệ thống KHÔNG BAO GIỜ biết**. Mã nhập nhằng một mình
không đổi trạng thái đơn, nhưng nó **rò ra ngoài chính nó** bằng đường này — tức là chốt chặn
W04 trước G14 **chưa kín**.

**Vì sao bộ thử cũ xanh suốt:** lỗi chỉ hiện khi CSDL có các cột mở rộng của G06 (schema v7+).
`thu_webhook.py` chạy trên CSDL **chưa** migrate nên `watermark()` rơi xuống nguồn audit (nguồn
đúng) và mọi ca đều xanh. **CSDL thật thì đã migrate.**

**Phép đo TRƯỚC/SAU** — cùng kịch bản, cùng tiến trình; `watermark_cu` là bản sao **nguyên văn**
của hàm ở `HEAD` (lấy bằng `git show HEAD:app/webhook.py`), nên phép đo không phụ thuộc việc lùi mã:

```
$ rm -rf /tmp/veh_ag03/data2
$ VIP_HUB_DATA=/tmp/veh_ag03/data2 python3 /tmp/veh_ag03/probe_truoc_sau.py
KỊCH BẢN: mã 110 (KHÔNG được áp) lúc 10:00, rồi một bản quét CÓ THẬT lúc 09:00 đến sau.
TRƯỚC bản vá (watermark() nguyên văn ở HEAD):
  TRUOC1 mã 106 lúc 09:00:00 đến sau mã 110 lúc 10:00:00 → trạng thái đơn = cho_lay          watermark=01792033200000 số lượt chặn 'đến muộn'=1
  TRUOC2 mã 113 lúc 09:00:00 đến sau mã 110 lúc 10:00:00 → trạng thái đơn = cho_lay          watermark=01792033200000 số lượt chặn 'đến muộn'=1
SAU bản vá (watermark() chỉ tính sự kiện ĐÃ ÁP):
  SAU1   mã 106 lúc 09:00:00 đến sau mã 110 lúc 10:00:00 → trạng thái đơn = lay_hang         watermark=01792029600000 số lượt chặn 'đến muộn'=0
  SAU2   mã 113 lúc 09:00:00 đến sau mã 110 lúc 10:00:00 → trạng thái đơn = giao_thanh_cong  watermark=01792029600000 số lượt chặn 'đến muộn'=0
```

**Bản vá — HAI tầng, và tầng thứ hai để cứu DỮ LIỆU ĐANG CÓ** (không đổi schema, không cần
migration):

1. `_ghi_watermark(sk_id, don_id, moc, tenant_id)` nay là nơi **DUY NHẤT** ghi cột
   `wh_su_kien.hang_moc_thoi_gian`, và nó **chỉ được gọi khi `ap_dung=1`**. `luu_dau_vet()` không
   ghi cột mốc nữa. ⇒ sự kiện không đổi được trạng thái — mã nhập nhằng, mã chỉ ghi nhận, mã lạ,
   **và sự kiện bị rank guard chặn** — không còn đẩy mốc.
2. `watermark()` **vẫn giữ** bộ lọc `trang_thai_chuan IS NOT NULL` khi đọc từ cột. Đây không
   phải điều kiện thừa: những dòng do mã CŨ ghi đã nằm trong CSDL thật rồi, và chúng phải tiếp
   tục bị bỏ qua. Bỏ bộ lọc này là lỗi cũ sống lại **trên đúng dữ liệu đang có** (ca `test_e09`
   dựng một dòng như thế bằng SQL rồi khẳng định nó không đẩy được mốc).

Dấu vết **không mất một mẩu nào**: mốc gốc của hãng vẫn nằm trong `hang_su_kien_goc` (cột) và
trong audit `webhook_anh_xa → su_kien_hang_goc` (dòng), chỉ **quyền ĐẨY MỐC** của sự kiện không
được áp là bị bỏ. CSDL chưa migrate thì tự lùi về nguồn audit thay vì nổ.

#### 4.3.1 Đo lại lần hai (B12) — sự kiện bị RANK GUARD chặn

Bản vá đầu (chỉ lọc ở chỗ ĐỌC) chưa phủ ca này. AG-00 giao lại và cấp quyền sửa cả
`thu_webhook.py`; phép đo dưới đây chạy TRƯỚC/SAU trong cùng một tiến trình, với `watermark()` và
`luu_dau_vet()` là **bản sao nguyên văn** của `HEAD`:

```
$ rm -rf /tmp/veh_ag03/data3
$ VIP_HUB_DATA=/tmp/veh_ag03/data3 python3 /tmp/veh_ag03/probe_b12.py
KỊCH BẢN: đơn đang giao (mốc áp 09:00) → 106 lúc 11:00 bị RANK GUARD chặn → 113 Delivered lúc 10:00 đến sau.
TRƯỚC bản vá B12 (watermark() + luu_dau_vet() nguyên văn ở HEAD):
  TRUOC  mốc sau sự kiện BỊ CHẶN = 01792036800000 | sau khi nhận 113 lúc 10:00: trạng thái = dang_giao        | số lượt chặn 'đến muộn' = 1
SAU bản vá B12 (mốc chỉ ghi khi ap_dung=1):
  SAU    mốc sau sự kiện BỊ CHẶN = 01792029600000 | sau khi nhận 113 lúc 10:00: trạng thái = giao_thanh_cong  | số lượt chặn 'đến muộn' = 0
```

Trước: sự kiện bị chặn (không đổi được gì) kéo mốc lên `11:00`, nên `113 Delivered` lúc `10:00`
bị chặn oan ⇒ **đơn đã giao mà vẫn nằm ở `dang_giao`**. Sau: mốc đứng ở `09:00`, `113` được áp.
Ca thử giữ hành vi này: `thu_webhook_jt.test_e08`.

#### 4.3.2 Ca thử `thu_webhook.test_g02` đã GHIM HÀNH VI SAI — nay đã sửa

Ca đó (viết ở đợt G06) có dòng:

```python
self.assertEqual(r["hang_moc_thoi_gian"], wh._moc_chuan("2026-10-15 10:00:00"))   # mã 110
```

Nó **khẳng định đúng cái sai**: rằng một sự kiện KHÔNG được áp vẫn ghi cột mốc. Ca xanh vì nó
**kiểm nhầm chỗ**, không phải vì mã đúng. Nay ca được sửa theo hành vi đúng, **không phải nới ra
cho vừa mã** — và sửa theo hướng CHẶT HƠN:

- `hang_moc_thoi_gian` của sự kiện `110` phải là `None`, và `watermark()` của đơn phải là `None`;
- mốc gốc **vẫn phải tra được** trong audit `webhook_anh_xa → su_kien_hang_goc.moc_hang`
  (bỏ quyền đẩy mốc mà xoá luôn dấu vết là hỏng theo hướng khác);
- với sự kiện **ĐÃ ÁP**: cột và nguồn audit phải nói **cùng một con số**.

Không có ca thử nào khác của `thu_webhook.py` phải sửa: các ca `d02`/`d03`/`d04` đều dùng sự kiện
**đã áp** nên vẫn đúng ở cả hai hành vi.

### 4.4 Không đụng vào tiền — có ca thử canh

`webhook.py` **không có** một dòng nào chạm COD: `test_f08` dò mã nguồn (`import tai_chinh`,
`chuyen_cod`, `ghi_but_toan`, `tc_cod`, `UPDATE don_hang` — không có cái nào).
Và có ba ca **đo trên sổ thật** (`tc_cod`, `tc_cod_chuyen`, `tc_but_toan`), chụp TRƯỚC/SAU:

- `test_f06` — `110` và mã lạ `999`: sổ COD **không đổi một dòng nào**;
- `test_f07` — `113 Delivered` (mã **rõ nghĩa**, được áp): đơn sang `giao_thanh_cong` nhưng sổ COD
  **vẫn `COD_EXPECTED`**, 0 lượt chuyển trạng thái, 0 bút toán. Đây là hợp đồng §18 — *giao hàng
  ≠ tiền COD đã về* — được canh bằng số, không bằng lời.

---

## 5. W05 — ĐỘ TIN CẬY: TỪNG ĐIỀU, VÀ CHỖ ĐỨNG CỦA NÓ

| Điều | Cơ chế | Ca thử |
|---|---|---|
| Xác thực chữ ký | Chọn sơ đồ ở **phía máy chủ** theo (hãng, môi trường); người gửi không chọn được | `test_b05`, `thu_webhook.test_a*` |
| Chống phát lại | `timestamp` lệch quá `LECH_GIO_TOI_DA_MS` (15 phút) → từ chối; thiếu `timestamp` cũng từ chối | `test_b04` (+ ghim cách hiểu (a)) |
| Chống trùng | `UNIQUE(carrier_account_id, event_id)` — **CSDL cưỡng chế**; ca thử nhồi thẳng bằng SQL để chứng minh không phải `if` | `test_c01`, `test_c02` |
| Sai thứ tự | Hai tầng: **mốc của hãng** (watermark) trước, **thứ hạng** sau | `test_e01`–`test_e07` |
| Thử lại | Trần `WEBHOOK_SO_LAN_THU`, backoff `2^n` **có trần** (`BACKOFF_TRAN_GIAY`) | `test_g01` |
| DLQ | Lỗi vĩnh viễn → DLQ **ngay, 0 lượt thử**; lỗi tạm → DLQ sau trần | `test_g01`, `test_g02` |
| Nhận việc nguyên tử | `UPDATE ... WHERE trang_thai IN ('moi','cho_thu_lai')` rồi xét `rowcount` | `test_g03` |
| Replay có phép | Đúng tenant + quyền `tenant.webhook.replay` + **trần `REPLAY_TOI_DA`** + audit | `test_g04`, `test_g05`, `test_g07` |
| Replay không mất im lặng | **VÁ G14**: từ chối replay khi sự kiện đang `dang_xu_ly` | `test_g06` |
| Audit | Mọi nhánh đều ghi: chữ ký sai, không khớp đơn, cần soát, đến muộn, cập nhật, DLQ, replay | xuyên suốt |
| Đối chiếu hành trình | `doi_chieu_hanh_trinh(tenant_id)` — chỉ đọc, chỉ một tenant | `test_h01`–`test_h08` |

### 5.1 Vá thứ hai: replay khi sự kiện ĐANG xử lý là một lượt replay MẤT IM LẶNG

`yeu_cau_replay` cũ đặt `trang_thai='moi'` rồi xếp hàng. Nếu worker đang giữ sự kiện đó, nó chạy
xong và đặt lại `'xong'`; lượt trong hàng đợi tới `_nhan_viec` thì thấy `'xong'` nên **bỏ qua**.
Người bấm thấy **HTTP 202 "đã nạp lại"** nhưng không có gì chạy lại — đúng kiểu hỏng không báo lỗi
mà §12.2 cấm. Nay từ chối thẳng kèm lý do (`test_g06`).

### 5.2 `doi_chieu_hanh_trinh` trả về gì

`lech_tenant` (bất biến — phải luôn rỗng) · `su_kien_mo_coi` · `khong_khop` · `cho_nguoi_soat`
(`can_soat=1`) · `ket_dinh` (DLQ + chờ thử lại) · `don_treo` (đơn đang chạy mà không có sự kiện
nào trong `giay_gan_nhat` giây ⇒ ứng viên cho polling) · `don_khong_su_kien` · `can_polling`.
CSDL chưa migrate thì trả `None` + ghi rõ vào `bo_qua` — **`None` khác `[]`**: trả `[]` khi chưa
kiểm được là nói dối rằng đã kiểm (`test_h08`).

**Đánh đổi có ý thức:** replay **chéo tenant** bị từ chối nhưng **cố ý KHÔNG ghi audit kèm số sự
kiện**. Tầng HTTP đã cố tình trả 404 giống hệt "không có" để không ai dò được ID bằng cách so 404
với 409 (TEST-011); ghi một dòng audit nói *"ID này có nhưng không phải của bạn"* là mở lại đúng
kênh dò ấy ở tầng đọc audit. `test_g04` ghim cả hai vế: từ chối **và** không thêm dòng audit nào.

---

## 6. W06 — BỘ THỬ: LỆNH THẬT VÀ KẾT QUẢ THẬT

```
$ cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA=/tmp/veh_data_ag03 python3 app/thu/thu_webhook_jt.py
Ran 67 tests in 0.608s

OK                                    (mã thoát 0)
```

Bộ thử **mới** `app/thu/thu_webhook_jt.py` (tệp riêng của AG-03, không giẫm `thu_webhook.py`).
Nó dựng **đúng schema thật** (có các cột mở rộng của G06) — đó là điều kiện để lỗi §4.3 hiện ra.
Máy chủ HTTP trong lớp `I_HTTPThat` bind **`127.0.0.1`** và xin **cổng do hệ điều hành cấp**
(`port 0`) nên không giành cổng với phiên nào đang chạy song song.

| Nhóm | Nội dung | Số ca |
|---|---|---|
| A | Hợp đồng callback: đủ trường, mức `BLOCKED`, công thức ký từng byte, phản hồi `code=1`, không tự nâng mức | 5 |
| B | Chữ ký sai/thiếu, `apiAccount` lạ, lệch 7 tiếng, không cho người gửi chọn sơ đồ, hãng chưa có sơ đồ | 6 |
| C | Chống trùng: ràng buộc trong DDL, nhồi SQL bị CSDL chặn, gửi lại idempotent, khoá theo account | 5 |
| D | `webhook_ma` lạ, tài khoản đã tắt, không khớp đơn, **chéo tenant**, đơn gắn sai account, payload khai tenant | 9 |
| E | Sai thứ tự: rank guard, mốc hãng, **bốn ca vá G14** (`e03`/`e04`/`e08`/`e09`), phương án lùi khi chưa migrate | 9 |
| F | Mã `110` (3 ca), mã lạ, **bộ mã thứ hai**, **không đụng COD** (3 ca) | 8 |
| G | Retry, DLQ (tạm thời + vĩnh viễn), nhận việc nguyên tử, replay (tenant/trần/đang xử lý/quyền/từ DLQ) | 8 |
| H | Đối chiếu hành trình, gồm **phép kiểm tự chứng minh** và cách ly tenant | 8 |
| I | HTTP thật trên `127.0.0.1`: 404, 401-không-lưu, 202/200, **`code=1` ở cả hai nhánh** | 5 |
| J | Chốt chặn cấu trúc: tài liệu G14, không gọi mạng, không mở LIVE, `gateway/` còn nguyên | 4 |

**Hồi quy — bộ thử G06 phải vẫn xanh (sau khi sửa `test_g02`, xem §4.3.2):**

```
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA=/tmp/veh_data_ag03 python3 app/thu/thu_webhook.py
Ran 68 tests in 0.101s

OK                                    (mã thoát 0)
```

Các bộ liên quan khác, chạy cùng CSDL thử:

| Bộ | Kết quả |
|---|---|
| `app/thu/thu_g01_g02.py` | 21 ca — OK |
| `app/thu/thu_g03.py` | 53 ca — OK |
| `app/thu/thu_qa_soat.py` | 30 ca — OK |
| `app/thu/thu_bien_driver.py` | 5 ca — ĐẠT |
| `app/thu/thu_tich_hop.py` | 6 ca — OK **khi đã `unset GIT_CONFIG_COUNT …`**; chạy trần thì `test_04` hỏng vì git của môi trường harness (`missing config key GIT_CONFIG_KEY_0`) — **lỗi môi trường, không phải lỗi mã G14** |

**Toàn tầng python** (đúng cách bộ chạy tự dò: `for t in $(find app/thu gateway/thu -name
'thu_*.py' ! -name 'thu_e2e.py')`, có `unset GIT_CONFIG*`):

```
TỔNG: 1106 ca
HỎNG: (rỗng)              ← 32 bộ, mã thoát 0 mọi bộ
```

`thu_migrate_dong_thoi.py` từng hỏng một lượt trong lúc bốn làn dùng chung một cây; lượt này
xanh — khớp kết luận **hỏng GIẢ** của AG-00 (N-05), không phải lỗi của G14.

---

## 7. ĐÃ ĐỔI NHỮNG GÌ

| Tệp | Thay đổi | Vì sao |
|---|---|---|
| `app/webhook.py` | `HOP_DONG_CALLBACK` + `CALLBACK_CHUA_TAI_LIEU` + `phan_hoi_xac_nhan()` | W02 — hợp đồng callback thành dữ liệu máy đọc được; phản hồi `code=1` (AG-00 đã cắm vào route, §2.1) |
| `app/webhook.py` | `tenant_tu_account()`; `_xu_ly` dùng nó cho mọi truy vấn | W03 — nguồn tenant có TÊN để soi được |
| `app/webhook.py` | `watermark()` lọc `trang_thai_chuan IS NOT NULL` | **W04/W05 — vá lỗi §4.3, tầng ĐỌC (cứu cả dữ liệu cũ)** |
| `app/webhook.py` | `_ghi_watermark()` là nơi DUY NHẤT ghi cột mốc, chỉ khi `ap_dung=1`; `luu_dau_vet()` thôi ghi cột mốc | **W05 — vá lỗi §4.3, tầng GHI (B12, ca rank-guard)** |
| `app/webhook.py` | `yeu_cau_replay` từ chối khi `dang_xu_ly` | **W05 — vá lỗi §5.1** |
| `app/webhook.py` | `doi_chieu_hanh_trinh()` + `_cu_hon()` + `DANG_CHAY` | W05 — đối chiếu hành trình |
| `app/thu/thu_webhook_jt.py` | **MỚI** — 67 ca | W06 |
| `app/thu/thu_webhook.py` | sửa **1 ca** (`test_g02`) — ca cũ ghim hành vi SAI (§4.3.2) | B12 — quyền sửa do AG-00 cấp 15/10/2026 |
| `docs/G14_JT_WEBHOOK.md` | **MỚI** — tài liệu này | W01–W06 |

**Không sửa:** `gateway/` (7 tệp nguyên vẹn) · `app/adapter_jt.py` (AG-02) · `app/csdl.py`,
`app/migrate.py`, `app/server.py` (AG-00) · `app/trang_thai_hang.py` (không cần đổi).
**Không đổi schema, không cần migration mới:** bản vá chỉ đổi **nơi ghi** và **cách đọc** cột mốc
đã có sẵn.

---

## 8. DANH SÁCH BLOCKED — BẢNG GỬI HÃNG

Bảng dưới đây để AG-00 gộp thẳng vào danh sách câu hỏi chính thức. Cột cuối là chỗ **mã đang bị
chặn** vì chưa có câu trả lời — để thấy mỗi câu hỏi không phải câu hỏi suông.

| # | Câu hỏi gửi J&T | Vì sao KHÔNG được đoán | Mã / đường dẫn đang bị chặn |
|---|---|---|---|
| **B1** | Khi J&T gọi callback về URL của chúng tôi, `digest` được tính bằng **khoá nào** — `privateKey` của tài khoản API của chúng tôi, hay một khoá riêng do J&T cấp cho chiều callback? **Chuỗi đem đi ký** là gì: chỉ chuỗi JSON `bizContent`, hay toàn bộ thân form (`bizContent=...`)? Xin một **ví dụ đủ ba thứ**: chuỗi gốc · khoá (che bớt) · `digest` kết quả | Công thức `base64(md5(bizContent + privateKey))` là của tài liệu, nhưng **hai đầu vào chưa biết**. Đoán khoá ⇒ chữ ký đúng vẫn bị từ chối (mất sạch callback); đoán chuỗi ký ⇒ **từ chối sạch mọi callback thật** mà không có lỗi nào chỉ đúng chỗ | `webhook.xac_thuc_jt_digest()` — mức giữ ở `DOCUMENTED`; `HOP_DONG_CALLBACK["khoa_ky_chieu_callback"]`, `["chuoi_dem_di_ky"]`, `["vi_du_doi_chieu"]` = `CHUA_TAI_LIEU` |
| **B2** | Callback (`轨迹回传`) dùng **phương thức HTTP** nào? | Trích lục chỉ tả THÂN và HEADER. Đoán `POST` rồi ghi thành dữ kiện là bịa — mà nếu hãng dùng `PUT` thì cửa ingest hiện tại **không có route** cho nó | Route `POST /api/v2/webhook/nhan/<webhook_ma>` trong `app/server.py`; `HOP_DONG_CALLBACK["phuong_thuc_http"]` |
| **B3** | **Thân phản hồi đầy đủ** khi nhận callback là gì? Mã HTTP nào là "đã nhận"? `200`/`202` có bị coi là hỏng không, hay chỉ `code=1` trong thân mới tính? | Chỉ có **một mảnh** trong câu 9: "khi chúng tôi trả về mã khác `code=1`" ⇒ biết có trường `code`, `code=1` = nhận. Nhưng mã HTTP, các trường còn lại, và ngữ nghĩa `200` vs `202` thì **chưa có**. Đoán ⇒ hãng coi mọi callback là hỏng và **đẩy lại vô hạn** | `webhook.phan_hoi_xac_nhan()` + route ingest; `HOP_DONG_CALLBACK["phan_hoi_xac_nhan"]` **vẫn** `CHUA_TAI_LIEU` — bản vá §2.1 KHÔNG phải nghiệm thu |
| **B4** | J&T **thử lại** callback bao nhiêu lần khi chúng tôi trả `code≠1` hoặc khi máy chủ không trả lời? Khoảng cách giữa các lần? J&T có **đẩy trùng** một sự kiện không? | Không biết thì không chọn được trần thử lại của phía nhận, và không biết khoá chống trùng của mình có che đúng ca trùng thật hay không | `HOP_DONG_CALLBACK["chinh_sach_thu_lai"]`, `["dinh_danh_su_kien"]`; trần `WEBHOOK_SO_LAN_THU`, `REPLAY_TOI_DA` |
| **B5** | Mã `scanTypeCode = 110` mà hệ thống J&T đẩy về cho khách Việt Nam nghĩa **chính xác** là gì: "hàng đến kho trung chuyển" (Arrival / 到件扫描) hay "quét kiện có vấn đề"? | Bảng tham số và ví dụ trả lời **trên cùng một trang** nói hai nghĩa **ngược chiều nhau**. Chọn hướng "đang đi bình thường" ⇒ đơn có vấn đề **không ai xử lý**; chọn hướng "có vấn đề" ⇒ báo động giả mọi kiện qua kho | `trang_thai_hang.NHAP_NHANG[("jt", 110)]`; mã `110` **không bao giờ** được áp trạng thái ⇒ đi vào `NEEDS_REVIEW` |
| **B6** | Có đang tồn tại **HAI BỘ MÃ** `scanTypeCode` không (bộ `103…121` trong bảng tham số và bộ `10/50/92/94/100/110` trong ví dụ)? Nếu có: bộ nào cho khách Việt Nam, bộ nào cho API tra hành trình, bộ nào cho callback? Xin **danh sách đầy đủ chính thức** kèm tên Việt/Anh từng mã | Trong bộ thứ hai, `100` = "Ký nhận" (đã giao). Thêm `100` vào bảng ánh xạ mà chưa có xác nhận là **đánh dấu đã giao cho một mã chưa ai kiểm** ⇒ mở đường tới tiền COD | `trang_thai_hang.JT_MA` (cố ý KHÔNG có `10/50/92/94/100`); ca `test_f05` gửi cả năm mã và khẳng định đơn không nhúc nhích |
| **B7** | `timestamp` ở header là **(a)** mốc Unix thật (ghi chú UTC+7 chỉ để nói giờ hiển thị) hay **(b)** giờ treo tường UTC+7 rồi quy đổi như thể là UTC? Xin một ví dụ: một giá trị `timestamp` cụ thể và giờ Việt Nam tương ứng. J&T chấp nhận lệch tối đa bao nhiêu? | Hai cách hiểu lệch **đúng 7 tiếng**, và `timestamp` **không nằm trong chuỗi ký** ⇒ chữ ký vẫn đúng, chỉ lớp chống phát lại từ chối sạch. Hỏng ở chỗ không có thông báo nào chỉ đúng nguyên nhân | `webhook.xac_thuc_jt_digest()` (nhánh `LECH_GIO_TOI_DA_MS` = 15 phút); ca `test_b04` ghim cách hiểu (a) |
| **B8** | `scanTime` trong `details` là **giờ Việt Nam hay UTC**? Định dạng chuẩn là cái nào — tài liệu cho hai dạng: `"2024-06-05 15:57:04"` và `"2024-06-21T13:23:56"` | Mốc này là **thứ tự hành trình** và là watermark chặn bản tin cũ. Hiểu sai múi giờ ⇒ bản tin cũ/mới so sai ⇒ chặn oan hoặc cho qua bản cũ | `webhook._moc_chuan()`; `HOP_DONG_CALLBACK["moc_thoi_gian_scan"]` |
| **B9** | — (không phải câu hỏi cho hãng) | URL công khai do **phía mình** khai. Chưa có thì J&T không gọi được vào đâu cả | Route ingest có thật và đã đo qua HTTP, nhưng **chưa được đăng ký**. `V-G11-01` CHƯA CẤP |
| **B10** | Để chạy thử trên `demoopenapi.jtexpress.vn`, chúng tôi cần J&T cấp thêm `customerCode` và `password` của môi trường thử không? Thủ tục và người phụ trách? `apiAccount`/`privateKey` in trên trang là dùng chung hay mỗi đối tác một bộ? | Không có credentials thì **không chạy được lượt nào** — kể cả một callback thử. Và `apiAccount` dùng chung hay riêng quyết định phép kiểm PHỤ trong `xac_thuc_jt_digest` có nghĩa hay không | Toàn bộ `app/adapter_jt.py` (AG-02) và `xac_thuc_jt_digest()`; `V-13906-05` CHƯA CẤP |
| **B11** | — (không phải câu hỏi cho hãng) | Cần `server.py` (file của AG-00) gọi `phan_hoi_xac_nhan()`. **AG-00 đã cắm xong 15/10/2026** — giữ dòng này để dấu vết đầy đủ | — (ĐÓNG) |
| **B12** | — (không phải câu hỏi cho hãng) | Sự kiện bị **rank guard** chặn vẫn đẩy watermark. Cần sửa `thu_webhook.py` — tệp không thuộc làn G14 lúc đó. **AG-00 đã cấp quyền và việc đã xong 15/10/2026** | — (ĐÓNG, xem §4.3.1) |

Với B5/B6: hệ thống **không đoán**. Mọi mã chưa chốt đi vào `NEEDS_REVIEW`/`AMBIGUOUS`, đơn giữ
nguyên, và **không có đường nào từ một mã chưa xác minh tới `DELIVERED` hay tới tiền COD**.

---

## 9. RỦI RO CÒN LẠI — GHI RA, KHÔNG GIẤU

1. ~~Watermark và sự kiện bị rank guard chặn~~ — **ĐÃ VÁ 15/10/2026** (B12, §4.3.1: cả tầng GHI
   lẫn tầng ĐỌC, có phép đo trước/sau và bốn ca thử `e03`/`e04`/`e08`/`e09`).
2. **Một callback nhiều bản quét ⇒ chỉ bản MỚI NHẤT được xử lý.** `_doc_jt` chọn bản có `scanTime`
   lớn nhất trong `details[]` (ca `thu_webhook.test_d07` ghim hành vi này). Các bản cũ trong cùng
   một lần đẩy **không** sinh sự kiện riêng, nên hành trình trung gian có thể bị thiếu nếu hãng
   gộp nhiều bản quét vào một callback **và** không đẩy lại. Trạng thái CUỐI vẫn đúng, nên đây là
   mất mát về hành trình chứ không phải mất mát về trạng thái. **Chưa sửa** vì đổi chỗ này kéo
   theo định danh sự kiện (`§12`) và cần một lượt đo riêng với dữ liệu thật. Đã ghi vào câu hỏi
   cho hãng (câu 11: thứ tự nhiều sự kiện cùng lúc có bảo đảm không).
3. **`apiAccount` chỉ được kiểm khi `credentials` giải mã được và có trường ấy.** Không giải mã
   được thì phép kiểm PHỤ này bị bỏ qua (chữ ký chính vẫn đã đúng) — cố ý, và có ghi trong mã.
4. **Mã lạ hoàn toàn** (`999`) được ghi nhận và đánh dấu cần soát nhưng **không** sinh thông báo
   chủ động cho người vận hành. `doi_chieu_hanh_trinh` là chỗ nhìn thấy chúng; chưa có kênh đẩy.
5. **Chưa đo dưới tải nhiều tiến trình** cho đường webhook này (bàn đo đồng thời là bộ riêng,
   `app/thu/dong_thoi/`). Kết luận ở đây chỉ đúng cho **một tiến trình**.
