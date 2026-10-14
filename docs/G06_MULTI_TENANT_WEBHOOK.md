# G06 — MULTI-TENANT WEBHOOK GATEWAY (AG-03)

Mở rộng `app/webhook.py` (đã nghiệm thu ở G01), **không xây lại**. `gateway/` giữ nguyên.
Bộ thử riêng: `app/thu/thu_webhook.py` — **68 ca**, chạy `python3 app/thu/thu_webhook.py`.

Đường đi một sự kiện:

```
VERIFY (sơ đồ theo hãng) → PERSIST RAW → QUEUE → NORMALIZE (quyet_dinh)
  → RESOLVE TENANT+ORDER (từ carrier_account) → GUARD (mốc hãng → thứ hạng)
  → UPDATE (don_hang.ap_trang_thai_giao) → AUDIT
```

---

## 1. W06 — Mã `110` của J&T: tài liệu TỰ MÂU THUẪN

### Mâu thuẫn, nguyên văn

| Nơi trong tài liệu | `110` nghĩa gì | Dẫn tới trạng thái nào |
|---|---|---|
| **Bảng tham số** `scanTypeCode` | `Arrival / 到件扫描` (hàng đến kho) | `dang_giao` (hạng 3) |
| **Ví dụ trả lời** của `/logistics/query` **và** `/logistics/statusFeedback` | `Quét kiện có vấn đề` | *chưa rõ* — ví dụ không nói đây là thất bại giao hay chỉ một lần quét bất thường |

Nguồn: `open.jtexpress.vn/apiDoc/logistics/query` + `/logistics/statusFeedback`, đọc bằng trình
duyệt **14/10/2026** (trang là SPA, `curl` không đọc được). Phiên bản tài liệu ghi là
`doc-2026-10-14`.

### Cách xử — KHÔNG chọn nghĩa

Bản trước **chọn theo bảng tham số** và cập nhật đơn sang `dang_giao`. Đó là tự chọn một nghĩa,
trái §12. Bản này:

1. `110` nằm trong **sổ mã nhập nhằng** `trang_thai_hang.NHAP_NHANG`, kèm **cả hai nghĩa**, lý do
   mâu thuẫn và nguồn của từng nghĩa.
2. Đường cập nhật đơn đi qua **một hàm duy nhất** `trang_thai_hang.quyet_dinh()`. Với mã nhập
   nhằng chưa chốt nghĩa, nó trả `trang_thai_ap = None` ⇒ **đơn không đổi trạng thái**, sự kiện
   được gắn nhãn **`AMBIGUOUS`** và `can_soat = True` (`NEEDS_REVIEW`).
3. **Chặn cứng hai lớp**: `chot_nghia()` từ chối mọi nghĩa dẫn tới `giao_thanh_cong`/`hoan_hang`;
   và `quyet_dinh()` kiểm lại lần nữa — nhồi thẳng vào sổ chốt cũng không đẩy được đơn sang hoàn
   tất (ca `test_e06`).
4. `anh_xa()` **giữ nghĩa cũ** cho bên chỉ ĐỌC/hiển thị (để không phá 53 ca của `thu_g03`), nhưng
   nay khai rõ `nhap_nhang=True`, `do_tin_cay='nhap_nhang'`, `can_soat=True`, và
   `trang_thai_ap = None`. Chốt chặn cấu trúc `test_i02` cấm đường GHI dùng `.trang_thai` của
   `anh_xa`/`normalizeTrackingStatus`.

### Dấu vết lưu cho mỗi sự kiện

mã gốc · mô tả gốc của hãng · **sự kiện hãng gốc** (nguyên văn `bizContent`) · nguồn tài liệu +
phiên bản · **độ tin cậy ánh xạ** (`cao` · `trung_binh` · `nhap_nhang` · `ma_la`) · nhãn
(`OK`/`NEEDS_REVIEW`/`AMBIGUOUS`) · **thời điểm nhận** · các nghĩa có thể · nghĩa đã chốt (nếu có).

Ghi **hai nơi**: vào cột `wh_su_kien` khi CSDL đã migrate, và **luôn luôn** một dòng audit
`webhook_anh_xa`. Cột là nơi truy vấn nhanh; audit là nơi không thể mất. Mã dò schema bằng
`PRAGMA table_info` (`webhook.cot_co`) nên **chạy được trên CSDL chưa migrate** — ca `test_g01`
kiểm nhánh chưa migrate, `test_g02` tự `ALTER TABLE` theo đúng DDL đề xuất rồi kiểm nhánh có cột.

### Khi nào mới được chốt nghĩa

`trang_thai_hang.chot_nghia(hang, ma, khoa_nghia, nguoi_chot, can_cu)` — bắt buộc có người chốt
và căn cứ, nếu không thì `ValueError`. **Hiện `NGHIA_DA_CHOT` rỗng**: chưa ai đối chiếu được với
hãng. Việc cần làm khi có người đối tiếp J&T: hỏi `110` nghĩa gì, hãng đẩy bộ mã nào
(`103…121` của bảng, hay `10/50/92/94/100/110` của ví dụ), rồi chốt.

Bộ thử phủ **cả hai hướng**: `test_e04` (nếu `110` = Arrival ⇒ đơn tiến lên `dang_giao`),
`test_e05` (nếu `110` = quét kiện có vấn đề ⇒ đơn **không** tiến), `test_e02` (chưa chốt ⇒ không
đổi gì), `test_e06` (không bao giờ hoàn tất ở cả ba tình huống).

---

## 2. W02/W03 — Resolve tenant & xác thực theo từng hãng

**Tenant chỉ đến từ `carrier_account`.** Payload có khai `tenant_id`/`tenantId`/`tenant` thì bị
**bỏ qua** và ghi audit `webhook_claim_tenant_bi_bo_qua` (`ket_qua=tu_choi`). Đơn được giải quyết
bằng `ma_van_don + tenant_id + carrier_account_id` — một tài khoản hãng không cập nhật được đơn
không thuộc nó, kể cả đơn của **account khác trong cùng tenant** (`test_b05`).

Sơ đồ xác thực chọn ở **phía máy chủ** theo `(hãng, môi trường)`; người gửi không có cách nào
chọn. Gửi kèm header của sơ đồ khác cũng không mở được cửa (`test_a05`).

### Bảng mức xác thực

| Hãng | `mock` | `sandbox`/`production` | Căn cứ |
|---|---|---|---|
| **J&T** (`jt`) | `hub_hmac` — **MOCK VERIFIED** | `jt_digest` — **DOCUMENTED** | tài liệu callback 轨迹回传: `apiAccount`/`digest`/`timestamp` + form `bizContent`, `digest = base64(md5-BYTES(bizContent + privateKey))` |
| **Viettel Post** (`vtp`) | `hub_hmac` — **MOCK VERIFIED** | **BLOCKED** | chưa có tài liệu Partner API; repo `vip-viettelpost` cũng rỗng (xem `VIETTELPOST_REUSE_AUDIT.md`) |
| hãng chưa khai | — | **BLOCKED** | không có sơ đồ mặc định nào |

Chưa có mức nào đạt `SANDBOX VERIFIED` hay `LIVE VERIFIED`: cần Owner cấp credentials.
`jt_digest` **không phát minh gì** — dùng đúng công thức của tài liệu. Hai điểm **cần xác minh**
khi có tài khoản thật: hãng ký riêng `bizContent` hay ký cả thân form, và khóa callback có đúng là
`privateKey` của tài khoản hay một khóa riêng. Vì vậy mức là `DOCUMENTED`, không hơn.

`jt_digest` còn kiểm `apiAccount` khớp credentials của **chính** account, và `timestamp` lệch quá
15 phút thì từ chối (chống phát lại bản ghi cũ). **Mọi lượt từ chối đều ghi audit**
`webhook_chu_ky_tu_choi` — chữ ký sai im lặng là chỗ không ai thấy việc dò secret.

---

## 3. W05 — Sự kiện đến sai thứ tự

Trước: chỉ dựa vào **thứ hạng** trạng thái. Thứ hạng một mình bỏ lọt ca thật này:

> Hãng quét `112 On Delivery` lúc **12:00** (đã áp ⇒ `dang_giao`, hạng 3).
> Bản tin `113 Delivered` của **08:00** đến muộn. Hạng 5 > 3 ⇒ rank guard **cho áp**.
> Đơn nhảy sang `giao_thanh_cong` bằng một bản tin cũ hơn.

Nay chặn bằng **mốc thời gian của hãng** (`scanTime` của J&T), kiểm **trước** rank guard. Mốc
được chuẩn hóa về chuỗi **14 chữ số epoch mili giây** (`webhook._moc_chuan`) để so sánh được bằng
cả `<` của chuỗi lẫn `MAX()` của SQL. Mốc không có hậu tố múi giờ được hiểu là **UTC+7** theo khai
báo của J&T, tính tường minh — không mượn múi giờ của máy (§12.2).

Watermark theo từng đơn, hai nguồn, cả hai là dấu vết do **chính đường cập nhật này** ghi ra:
cột `wh_su_kien.hang_moc_thoi_gian` + `don_id` khi đã migrate, và audit `webhook_moc_hang` (chạy
ngay trên CSDL chưa migrate). Mốc cũ hơn watermark ⇒ không áp, ghi `webhook_den_muon`.

Payload **không có** mốc hãng (callback mô phỏng của hub) thì lùi về rank guard, không bị chặn oan
(`test_d06`). `details[]` nhiều bản quét thì lấy bản **mới nhất theo `scanTime`** (`test_d07`).

---

## 4. W04/W07 — Chống trùng, idempotent, retry, DLQ, replay

- **Định danh bền** `dinh_danh_su_kien()`: `event_id` do bên gửi cấp → **khóa tổ hợp của hãng**
  (J&T: `billCode|scanTime|scanTypeCode`) → băm nội dung (`noid-…`) là phương án cuối. J&T không
  cấp `event_id`, nên không có khóa tổ hợp thì hai bản quét khác nhau sẽ bị coi là một.
- **Chống trùng do CSDL cưỡng chế**: `UNIQUE(carrier_account_id, event_id)`, không bằng `if`
  (`test_c02` chèn tay để chứng minh CSDL chặn thật).
- **Nhận việc NGUYÊN TỬ** `_nhan_viec()`: `UPDATE … WHERE id=? AND trang_thai IN ('moi',
  'cho_thu_lai')` rồi kiểm `rowcount`. Bản trước `SELECT` rồi `UPDATE` vô điều kiện ⇒ hai worker
  cùng xử lý **một dòng**; chống trùng ở tầng nhận không cứu được chỗ đó (`test_c06`).
- **Poison message** → `LoiVinhVien` → vào DLQ **ngay**, không đốt lượt thử nào (`test_f02`:
  không phải JSON · JSON thiếu trường · JSON là mảng · thiếu mã vận đơn · rỗng).
- **Retry có trần**: `WEBHOOK_SO_LAN_THU = 3`, backoff nhân đôi **có trần**
  `BACKOFF_TRAN_GIAY = WEBHOOK_BACKOFF_GOC × 64`. Không trần thì lượt thử thứ 20 hẹn lại sau 6
  ngày — việc coi như mất mà không báo lỗi gì.
- **Replay không vô hạn**: `yeu_cau_replay()` kiểm lại tenant + **trần `REPLAY_TOI_DA = 5`** (đếm
  từ audit `webhook_replay`) + ghi audit mỗi lần. Không có replay tự động ở bất kỳ đâu.
- Trạng thái sự kiện giữ **đúng 6 giá trị** của hợp đồng đóng băng mục 12 — `test_f10` quét cả mã
  nguồn, thêm giá trị lạ là hỏng.

---

## 5. W08 — Polling fallback

Giữ nguyên phần đã nghiệm thu: chỉ hỏi đơn đang chạy · gom lô theo giới hạn thật (**J&T 30 vận
đơn/lượt**) · đi qua đúng đường cập nhật của webhook · `chi_hang_khong_webhook` · **không tự chạy**.

Thêm:

- **Hạn mức theo TỪNG tenant** (`GIOI_HAN_HOI_MOI_PHUT = 600`, token bucket trượt 60 giây). Cách
  ly tenant phải có cả ở tầng hạn mức, không chỉ ở tầng truy vấn — một tenant nhiều đơn không được
  ăn hết lượt của tenant khác (`test_h03`). Vượt ⇒ hoãn + audit `polling_qua_han_muc`.
- **Ngắt mạch theo hãng**: `NGUONG_NGAT_MACH = 5` lỗi liên tiếp thì dừng hỏi hãng đó trong lượt
  này, audit `polling_ngat_mach`. Đập tiếp cho hết danh sách khi hãng đang hỏng là tự đốt hạn mức.
- **Vòng nền có khoảng cách tối thiểu** `MOI_GIAY_TOI_THIEU = 30`; muốn nhanh hơn phải truyền
  `cho_phep_nhanh=True` tường minh. `moi_giay_thuc` nói rõ con số đang dùng.
- Mã nhập nhằng qua polling cũng đi `quyet_dinh()` ⇒ **không đổi trạng thái**, audit
  `polling_nhap_nhang`. Không có bảng ánh xạ thứ hai.

Vẫn chỉ mock/local. Không bật polling production.

---

## 6. DDL + migration cần AG-00 làm

Mã **chạy được mà không cần** phần này (dấu vết đi vào audit). Có cột thì truy vấn nhanh hơn và
màn hình soát làm được bằng SQL thẳng.

```sql
-- migration schema v7 — thêm cột cho wh_su_kien. Toàn bộ là ADD COLUMN, tương thích ngược:
-- bản ghi cũ nhận NULL / 0, không bản ghi nào phải viết lại.
ALTER TABLE wh_su_kien ADD COLUMN hang_ma_goc         TEXT;      -- mã trạng thái NGUYÊN của hãng
ALTER TABLE wh_su_kien ADD COLUMN hang_mo_ta_goc      TEXT;      -- mô tả nguyên văn của hãng
ALTER TABLE wh_su_kien ADD COLUMN hang_su_kien_goc    TEXT;      -- JSON sự kiện hãng gốc
ALTER TABLE wh_su_kien ADD COLUMN anh_xa_do_tin_cay   TEXT;      -- cao|trung_binh|nhap_nhang|ma_la
ALTER TABLE wh_su_kien ADD COLUMN anh_xa_nguon        TEXT;      -- nguồn tài liệu + phiên bản
ALTER TABLE wh_su_kien ADD COLUMN can_soat            INTEGER NOT NULL DEFAULT 0;  -- NEEDS_REVIEW
ALTER TABLE wh_su_kien ADD COLUMN hang_moc_thoi_gian  TEXT;      -- epoch ms, 14 chữ số zero-pad
ALTER TABLE wh_su_kien ADD COLUMN don_id              INTEGER REFERENCES don_hang(id);
ALTER TABLE wh_su_kien ADD COLUMN trang_thai_chuan    TEXT;      -- trạng thái đã áp (NULL = không áp)
CREATE INDEX IF NOT EXISTS ix_wh_don  ON wh_su_kien(don_id, hang_moc_thoi_gian);
CREATE INDEX IF NOT EXISTS ix_wh_soat ON wh_su_kien(can_soat, id);
```

Sau khi migrate, gọi `webhook.xoa_cache_cot()` (hoặc khởi động lại tiến trình) để dò lại schema —
`webhook.khoi_dong()` đã tự gọi.

**Hợp đồng đóng băng mục 12 KHÔNG đổi**: tập trạng thái `wh_su_kien.trang_thai` vẫn đúng 6 giá
trị. Nhãn `NEEDS_REVIEW` cố ý đặt ở **cột riêng `can_soat`**, không thêm trạng thái mới — thêm
trạng thái là phá hợp đồng và phá mọi chỗ đang đọc.

### Điểm cắm trong `server.py` (AG-00 sở hữu, AG-03 không sửa)

1. **Replay có trần** — thay khối `/api/v2/webhook/su-kien/{id}/replay` bằng:
   ```python
   ok, ly_do = webhook.yeu_cau_replay(int(m.group(1)), tenant_id, nc.user_id)
   return self._tra(202 if ok else 409, {"ok": True} if ok else {"loi": ly_do})
   ```
   Giữ `self._can(nc, "tenant.webhook.replay")` ở trên. Hàm tự kiểm tenant + trần + ghi audit, nên
   bỏ được ba câu SQL và dòng `csdl.audit` đang viết tay ở đó.
2. **Màn soát** — thêm `s.can_soat`, `s.hang_ma_goc`, `s.anh_xa_do_tin_cay`, `s.trang_thai_chuan`
   vào `SELECT` của `/api/v2/webhook/su-kien` (sau khi migrate), và một bộ lọc `?can_soat=1` để
   người vận hành thấy ngay các sự kiện `AMBIGUOUS`/`NEEDS_REVIEW`.
3. **Chốt nghĩa mã nhập nhằng** — chưa có cửa HTTP, cố ý. Khi có căn cứ từ hãng thì nên là cửa
   **PLATFORM_OWNER**, không phải quyền tenant: một tenant không được định nghĩa lại nghĩa mã của
   hãng cho cả hệ thống. Hiện chốt bằng `trang_thai_hang.chot_nghia()` trong mã, có người + căn cứ.

---

## 7. Giới hạn còn lại (ghi ra để không ai tưởng đã xong)

- **`110` vẫn chưa có nghĩa.** Hệ thống không đoán, nên đơn mang mã `110` **không tiến trạng thái**
  cho tới khi có người chốt. Đây là cái giá cố ý chịu: thà đứng còn hơn đi sai hướng.
- **Chưa có cửa UI/HTTP** để xem và xử danh sách `NEEDS_REVIEW` (điểm cắm 2 ở trên).
- **`jt_digest` mức DOCUMENTED** — chưa có sandbox/credentials nên chưa ai ký thật thử. Hai điểm
  cần xác minh đã ghi ở mục 2.
- **VTP BLOCKED** ở môi trường thật. Không bịa cách ký.
- **`NGHIA_DA_CHOT` sống trong tiến trình**, chưa có bảng CSDL. Nhiều tiến trình (`server.py` +
  một job khác) phải chốt riêng. Khi cần chốt thật thì nên thêm bảng và nạp lúc khởi động.
- **Mốc hãng chỉ J&T có.** Hãng nào không gửi mốc thì vẫn chỉ có rank guard — đã nói đúng phạm vi,
  không khai là "đã chặn hết sai thứ tự".
- **Watermark đọc từ audit** khi chưa migrate: `MAX(chi_tiet)` trên bảng audit, đúng vì chuỗi là
  14 chữ số zero-pad, nhưng chậm hơn cột có index. Migrate xong thì tự dùng cột.
- Bộ thử **không mở máy chủ HTTP** nên **không phủ** tầng router của `server.py` (mã trả về, CSRF,
  đọc body). Phần đó do `thu_saas.py` và `thu_qa_soat.py` phủ, và cả hai vẫn đạt sau thay đổi này.
