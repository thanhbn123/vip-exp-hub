# G17 — WEBHOOK: REPLAY CÓ UỶ QUYỀN + CHỐNG TRÙNG Ở TẦNG CSDL (AG-04)

Làn: **AG-04** · nhánh `g17-ag04-webhook` · nền: `integration/g16` @ **98baeb3** · `main` = `de740dc`
(**không** chứa G13–G16, đã đối chiếu lại bằng `git log --oneline -1 main`).
Tệp được phép ghi: `app/webhook.py` · `app/thu/thu_webhook_jt.py` · `trien_khai/g17/` (mới) ·
`docs/G17_WEBHOOK.md`. **Không** tệp nào khác bị sửa (`git status --short` chỉ có bốn đường ấy).

---

## 0. SỐ LIỆU LƯỢT CHẠY — lệnh thật, mã thoát thật, số ca thật

| # | Lệnh | Mã thoát | Kết quả ĐO ĐƯỢC |
|---|---|---|---|
| 1 | `python3 app/thu/thu_webhook_jt.py` | **0** | `Ran 99 tests` · `OK` (trước lượt này: **77** ca) |
| 2 | `python3 app/thu/thu_webhook.py` (G06, tệp của làn khác) | **0** | `Ran 68 tests` · `OK` — không bị đụng |
| 3 | `sh trien_khai/g17/chay_harness.sh` | **0** | **đạt 17 · ĐẠT (MOCK) 3 · hỏng 0 · BLOCKED 1 · bỏ qua 0** |
| 4 | `python3 trien_khai/g17/chot_an_toan.py --tu-kiem` | **0** | **12/12 ca đạt · 0 hỏng** (1 đủ chốt + 11 hỏng, mỗi ca bị bắt bởi ĐÚNG chốt) |
| 5 | `python3 trien_khai/g17/harness_webhook.py --tu-kiem` | **0** | **5/5 ca đạt** (bộ đếm phán quyết: `BLOCKED` nằm ô riêng) |
| 6 | `VIP_G17_CHO_PHEP_GOI_HANG=1 python3 trien_khai/g17/harness_webhook.py` | **4** | `TỪ CHỐI CHẠY` · `V-G09-01` · **không** tạo `hub.db` |
| 7 | `VIP_G17_GIAY_PHEP=V-G09-01,V-13906-05 … harness_webhook.py` | **4** | `TỪ CHỐI CHẠY` · không tạo `hub.db` |
| 8 | `sh app/thu/chay_tat_ca.sh` | **1** | **1306 ca · 36 bộ chạy thật** · `thu_webhook_jt.py` **99 ca ✓** · `thu_webhook.py` **68 ca ✓** · frontend 56+36 · **E2E 41/41** · **2 bộ hỏng** (`thu_bao_mat.py`, `thu_tich_hop.py`) — **cả hai vì MÔI TRƯỜNG git của phiên, không phải mã** (§9) |

Báo cáo máy đọc được của harness: `$VIP_HUB_DATA/g17_harness/bao-cao-g17.json`.

---

## 1. NHIỆM VỤ VÀ ĐÃ LÀM GÌ

1. **REPLAY** — làm rõ và đo bốn nhánh: đang xử lý · đã xong · DLQ · **ai được replay**.
2. **IDEMPOTENCY** — khẳng định chống trùng ở **TẦNG CSDL** bằng SQL nhồi thẳng (không qua hàm
   nghiệp vụ), và gửi lại N lần ⇒ đúng 1 dòng, cùng `sk_id`.
3. **HARNESS CỤC BỘ** — `trien_khai/g17/`: MOCK trên nền tạm, CHỈ loopback, tự từ chối chạy khi
   mất chốt, chặng SANDBOX ghi `BLOCKED` kèm đúng giấy phép còn thiếu, tắt máy chủ theo ĐÚNG PID.
4. **GIỮ NGUYÊN bất biến đã nghiệm thu** — không đụng đường tenant/mã 110/watermark (§7).

---

## 2. REPLAY — BỐN NHÁNH, ĐO QUA HTTP THẬT (`server.py`, loopback, cổng 0)

| Nhánh | Chặng | Số đo |
|---|---|---|
| **ĐANG XỬ LÝ** | `G17-07` | `HTTP 409` · lý do `sự kiện đang được xử lý — đợi xong rồi replay` · trạng thái **giữ nguyên** `dang_xu_ly` · audit từ chối `0→1` · audit replay thành công `0` |
| **ĐÃ XONG** | `G17-08` | `HTTP 202` · chạy lại THẬT · đơn `dang_giao → dang_giao` (**không đổi**) · lượt áp lại bị rank guard chặn (`ap_dung=0`) **1 lần** · audit replay `=1` |
| **DLQ — lỗi tạm, đã sửa nguyên nhân** | `G17-09` | trước `dlq` (thử **3** lần) · `HTTP 202` · sau `xong`, `so_lan_thu=0`, đơn `dang_giao` |
| **DLQ — lỗi vĩnh viễn** | `G17-10` | trước `dlq` (thử **0**) · `HTTP 202` · sau `dlq` (thử **0**) · audit DLQ `1→2` — replay **không** đốt lượt thử nào |
| **KHÔNG uỷ quyền** (`TENANT_VIEWER`) | `G17-11` | `HTTP 403` · trạng thái `xong→xong` · audit replay thành công **không tăng** · audit `tu_choi_quyen` `1` · và người đó **ĐỌC được** sự kiện (`HTTP 200`) |
| **CÓ uỷ quyền** (`TENANT_OWNER`) | `G17-12` | `HTTP 202` · chạy lại · audit replay `2` |
| **CHÉO TENANT** | `G17-13` | `HTTP 404` cho sự kiện của tenant khác — **giống hệt** `HTTP 404` cho ID không tồn tại (không dò được ID) |
| **VƯỢT TRẦN** | `G17-14` | tổng **5 lượt** replay ghi nhận (`5/5` trần) rồi lượt kế tiếp `HTTP 409` (`đã replay 5 lần (trần 5)`) |

### 2.1 Một chỗ hỏng THẬT tìm được ở đường replay, và cách vá

`yeu_cau_replay` bản cũ kiểm `trang_thai == 'dang_xu_ly'` bằng một lượt **ĐỌC**, rồi ghi bằng câu
`UPDATE … WHERE id=?` **không điều kiện**. Giữa hai câu ấy, `_nhan_viec()` có thể đã nhận sự kiện
(đặt `dang_xu_ly`) — và câu ghi **giật sự kiện khỏi tay worker**. Đo được hai kết cục:

* **(a)** việc trong hàng đợi được `_nhan_viec` nhận ⇒ **HAI worker cùng xử lý MỘT sự kiện**, đúng
  thứ mà `_nhan_viec` dựng ra để chặn;
* **(b)** worker thứ nhất xong trước ⇒ việc trong hàng đợi thấy trạng thái cuối và bỏ qua ⇒
  **một lượt replay mất im lặng**.

Vá: điều kiện nằm **TRONG câu ghi** (`… WHERE id=? AND trang_thai<>'dang_xu_ly'`) và đọc
`rowcount`; không đổi được gì ⇒ **TỪ CHỐI** (`409`) thay vì giật sự kiện. Ca
`thu_webhook_jt.test_l02` dựng đúng khe hở này (sự kiện ở `cho_thu_lai`, chèn một lượt "nhận việc"
ngay trước câu ghi) và có **ĐỐI CHỨNG BỎ ĐO**: cùng phép dò chạy trên hàm **đã bị đột biến** sinh
từ chính mã nguồn (`inspect.getsource`, bỏ điều kiện khỏi câu ghi) **PHẢI** thấy lỗi — và nó thấy:
`duoc=True`, trạng thái bị đè thành `moi`, `_nhan_viec` nhận thêm được ⇒ worker thứ hai cùng chạy.

> Ghi chú trung thực: lượt chạy ĐẦU của ca này dựng sự kiện ở trạng thái `xong` — ở trạng thái đó
> worker **không** nhận được việc, nên phép chèn không tái hiện gì và ca thử "xanh" mà **không đo**.
> Nó chỉ có giá trị sau khi dựng đúng trạng thái `cho_thu_lai`. Đây là lý do ca thử phải có đối
> chứng bỏ đo, không chỉ có `assert`.

### 2.2 "Gửi lại" KHÔNG phải "replay" — đo cả hai chiều (`test_l08`)

Sự kiện ở DLQ, gửi lại **y nguyên** qua đường HTTP ⇒ `200 da_nhan_truoc_do`, **cùng `sk_id`**,
trạng thái vẫn `dlq`, `so_lan_thu` không đổi, **không** thêm dòng audit DLQ — tức là **không chạy
lại**. Đường duy nhất chạy lại là cửa replay có uỷ quyền. (Đối chứng dương: sau khi sửa payload,
`replay_co_uy_quyen` cho nó chạy lại và về `xong`.)

### 2.3 Phản hồi xác nhận — đo được gì, và cái gì vẫn CHƯA có tài liệu

| Đo gì | Số đo |
|---|---|
| Callback hợp lệ | `HTTP 202` · thân: `ket_qua=da_nhan` · **`code=1`** · `su_kien_id=…` (`G17-03`) |
| Callback gửi lại | `HTTP 200` · `ket_qua=da_nhan_truoc_do` · `code=1` · **cùng** `su_kien_id` (`G17-04`) |

`code=1` là mảnh DUY NHẤT tài liệu nói tới về phản hồi. Mã HTTP (`202`/`200`) **cố ý giữ nguyên**,
và hình dạng ĐẦY ĐỦ của phản hồi vẫn ở mức `CHUA_TAI_LIEU` (câu B3) — lượt này **không** nâng mức,
không thêm trường mới, không đổi mã HTTP. Việc phải hỏi hãng vẫn nằm nguyên trong
`CHAN_HOP_DONG_CALLBACK["phan_hoi_xac_nhan"]`.

---

## 3. AI ĐƯỢC REPLAY — uỷ quyền gọi TÊN RA ĐƯỢC

Trước lượt này, quyền replay **chỉ** được kiểm ở tầng HTTP (`server.py` → `_can(nc,
"tenant.webhook.replay")`), còn `webhook.yeu_cau_replay` là hàm GHI mà **bất kỳ** ai gọi thẳng cũng
chạy. Nay trong `app/webhook.py`:

| Tên | Việc |
|---|---|
| `QUYEN_REPLAY` | khoá tra quyền (`"tenant.webhook.replay"`) — tra CSDL, **không** chép bảng quyền vào mã |
| `vai_tro_duoc_replay(vai_tro)` | hỏi `quyen.co_quyen` — nguồn chân lý duy nhất |
| `uy_quyen_replay(sk_id, tenant_id, vai_tro, user_id)` | chốt uỷ quyền, **ghi audit mọi lượt từ chối** |
| `replay_co_uy_quyen(sk_id, tenant_id, vai_tro, user_id)` | **ĐƯỜNG HỢP LỆ** cho người gọi mới: kiểm tenant trước (im lặng), rồi uỷ quyền, rồi mới xếp hàng |
| `trang_thai_replay(sk_id, tenant_id, vai_tro=None)` | **CHỈ ĐỌC**: trả lời trước một lượt replay có chạy được không, và vì sao — **không** ghi audit |
| `yeu_cau_replay(..., vai_tro=None)` | truyền `vai_tro` ⇒ **tự kiểm quyền, fail-closed**; không truyền ⇒ ghi **rõ hệ uỷ quyền của tầng gọi** vào audit (`vai trò X có …` hoặc `tầng gọi đã uỷ quyền (route HTTP: _can)`) |

Vai trò: `TENANT_OWNER` / `TENANT_ADMIN` **được**; `TENANT_VIEWER` / `TENANT_STAFF` / vai trò rỗng
/ vai trò lạ **không** (`test_l03`).

**Chốt CẤU TRÚC** (`test_l04`): trong `server.py` chỉ có **đúng một** lời gọi `yeu_cau_replay(`,
và nó nằm **SAU** `_can(nc, "tenant.webhook.replay")`; mọi tệp `.py` khác trong `app/` bị cấm gọi
thẳng cửa ghi ấy (phải dùng `replay_co_uy_quyen` hoặc truyền `vai_tro=`). Một route thứ hai quên
`_can` sẽ làm ca này hỏng ngay.

Cửa ĐỌC và cửa GHI nói **cùng một lý do** cho cùng một điều kiện, và cửa ĐỌC **không ghi audit**
(`test_l09`) — hai chỗ trả lời lệch nhau là lỗi, không phải chi tiết.

---

## 4. IDEMPOTENCY — KHẲNG ĐỊNH Ở TẦNG CSDL, BẰNG SQL NHỒI THẲNG

| Đo gì | Chặng / ca | Số đo |
|---|---|---|
| Gửi lại **5 lần** cùng sự kiện qua HTTP | `G17-04` · `test_m02` | `HTTP [202,200,200,200,200]` · `ket_qua [da_nhan, da_nhan_truoc_do ×4]` · **1 dòng** trong CSDL · **cùng `sk_id`** · đúng **1** dòng audit cập nhật đơn |
| **NHỒI THẲNG SQL** (kết nối riêng, không qua `nhan_su_kien`) | `G17-05` · `test_m01` | `IntegrityError: UNIQUE constraint failed: wh_su_kien.carrier_account_id, wh_su_kien.event_id` · số dòng sau khi nhồi **= 1** |
| **ĐỐI CHỨNG ĐƯỜNG**: cùng câu INSERT, bảng lấy y DDL của `wh_su_kien` nhưng **bỏ đúng dòng UNIQUE** | `G17-06` · `test_m03` | **2 dòng lọt** ⇒ thứ đang chặn trùng là **CSDL**, không phải một `if` trong mã nghiệp vụ |
| Cùng `event_id`, **khác account** | `test_m04` | **2 dòng** ⇒ khoá chống trùng theo **ACCOUNT**, không bị làm phẳng theo hãng |
| **8 luồng** cùng nhận một sự kiện | `test_m05` | **1 dòng** · cùng `sk_id` · đúng **1** luồng coi là MỚI · không luồng nào nổ |

Ràng buộc nằm trong SCHEMA (`app/csdl.py`: `UNIQUE (carrier_account_id, event_id)`), và ca `m03`
là thứ chứng minh nó **chịu lực** — không có nó thì "CSDL chặn" chỉ là suy đoán.

---

## 5. HARNESS CỤC BỘ — `trien_khai/g17/`

| Tệp | Việc |
|---|---|
| `chot_an_toan.py` | **BẢY chốt**. Từ chối chạy nếu mất một chốt. `--tu-kiem`: 12 cấu hình tổng hợp |
| `harness_webhook.py` | Kịch bản **G17-00 … G17-16** qua HTTP thật, CSDL tạm, adapter MOCK, callback qua **stub** |
| `chay_harness.sh` | Tự kiểm chốt + tự kiểm bộ đếm → nền riêng → chạy → tắt máy chủ theo **ĐÚNG PID** |
| `README.md` | Cách chạy và ba loại phán quyết |

**Bảy chốt**: (1) nền TẠM, không phải `app/du-lieu/` · (2) `VIP_HUB_BIND` loopback · (3) mọi
adapter `CHO_PHEP_LIVE is False` · (4) cổng J&T sandbox/production **đóng** ở cả `cau_hinh` lẫn hàm
dẫn xuất của `adapter_jt` · (5) cờ `VIP_G17_CHO_PHEP_GOI_HANG` không bật · (6) mọi đích là loopback
· (7) **chặng chạm hãng phải KHAI mã giấy phép, và giấy phép phải CHƯA được cấp** — ai "cấp" bằng
`VIP_G17_GIAY_PHEP` thì harness từ chối ngay.

**Loopback thật, không chỉ khai báo**: máy chủ `server.py` chạy với tham số cổng **0** (hệ điều
hành cấp), cổng thật đọc từ chính dòng log nó in ra; mọi callback đi qua `StubHang` — một máy chủ
HTTP bind `127.0.0.1` **cổng 0** đóng vai bên gửi của hãng, giữ bí mật ký trong bộ nhớ tiến trình
(bí mật **không** đi qua HTTP, **không** vào log), và có **chốt loopback riêng**: đích không phải
loopback thì nó từ chối chuyển tiếp. Lượt chạy đã chuyển tiếp **8** callback, tất cả qua loopback.

**Chặng `BLOCKED`** — `G17-SANDBOX` (gửi sang J&T sandbox + callback theo sơ đồ của hãng):
thiếu `V-G09-01` (gọi API hãng, kể cả sandbox) · `V-13906-05` (credentials sandbox J&T) · câu 24
(sandbox có đẩy callback không) · câu 6–7 (khoá ký + chuỗi đem đi ký). Bằng chứng ĐO ĐƯỢC:
`cau_hinh.JT_CHO_PHEP_SANDBOX=False` · `JT_CHO_PHEP_PRODUCTION=False` ·
`adapter_jt.moi_truong_duoc_chay('sandbox')=False`.

**`BLOCKED` KHÔNG được tính là đạt**: bộ đếm `dem_phuong_an()` xếp nó ô riêng, và
`harness_webhook.py --tu-kiem` tự kiểm chính bộ đếm ấy — ca `test_n04` còn **bẻ** bộ đếm thành
"BLOCKED cũng là đạt" và bắt buộc bộ tự kiểm phải **thấy** (đối chứng bỏ đo). Ca `test_n05` khẳng
định phán quyết `G17-SANDBOX` **vẫn là `BLOCKED`** kể cả khi tiêm cổng mở — nó không có đường
thành "đạt" bằng tham số.

**Tắt máy chủ theo ĐÚNG PID**: `sv.terminate()` → `sv.kill()`, PID ghi ra `$NEN/hub.pid` để `trap`
của `chay_harness.sh` hứng nếu harness chết giữa đường. Ca `test_n06` quét mã (bỏ chú thích, giữ
chuỗi) và **cấm** `pkill`/`killall`, đồng thời có đối chứng dương/âm cho chính bộ dò ấy.

---

## 6. ĐỐI CHỨNG BỎ ĐO — làm cho ca thử ĐỎ được

| Ca | Đối chứng |
|---|---|
| `test_l02` (khe hở ĐỌC-rồi-GHI) | đột biến **sinh từ chính mã nguồn** (bỏ điều kiện khỏi câu ghi) ⇒ phép dò **thấy** lỗi: `duoc=True`, trạng thái bị đè, worker thứ hai nhận được việc |
| `test_m03` · `G17-06` | cùng câu INSERT vào bảng **bỏ UNIQUE** ⇒ trùng **lọt** (2 dòng) |
| `test_n04` | bẻ `la_dat()` thành "BLOCKED cũng là đạt" ⇒ bộ tự kiểm **báo hỏng** |
| `test_n06` | bộ dò lệnh cấm phải bắt `pkill -f server.py` và `killall python3`, và **không** bắt `kill -TERM $P` |
| `chot_an_toan --tu-kiem` | ca **A** là đối chứng DƯƠNG (cấu hình đủ chốt phải ĐI QUA); thiếu nó thì một bộ dò `return ["từ chối"]` cũng "bắt" được cả 11 ca hỏng |
| `test_k07` (G16, giữ nguyên) | bộ chạy thật phải thấy một ca cố ý hỏng ⇒ mã thoát ≠ 0 + `FAILED` |

---

## 7. GIỮ NGUYÊN BẤT BIẾN ĐÃ NGHIỆM THU

Lượt này **không** sửa: `_xu_ly` · `luu_dau_vet` · `_ghi_watermark` · `doc_su_kien_hang` ·
`tenant_tu_account` · `nhan_su_kien` · `_nhan_viec` · `ap_trang_thai_giao`. Cụ thể:

* **tenant CHỈ từ `carrier_account`** — không có đường nào đọc tenant từ payload; các ca
  `test_b03`, `test_d07`, `test_d08`, `test_k08`, `test_k09` vẫn xanh trong cùng lượt chạy.
* **mã 110 / mã lạ ⇒ NEEDS_REVIEW, 0 dòng `tc_cod` / `tc_cod_chuyen` / `tc_but_toan`** — nhóm F
  và `test_f06` vẫn xanh; lượt này không đụng `trang_thai_hang`.
* **ĐÚNG MỘT nơi ghi cột mốc và chỉ khi `ap_dung=1`** — `_ghi_watermark` là nơi duy nhất; nhóm E
  (gồm `test_e08`, `test_e03`) vẫn xanh.
* **tầng đọc còn lọc `trang_thai_chuan IS NOT NULL`** — `watermark()` giữ nguyên.
* **D-9 (city/area chặn cứng ngoài mock)** và **D-8 (không chuyển PostgreSQL)** — không tệp nào
  liên quan bị sửa.

---

## 8. NẰM NGOÀI PHẠM VI ĐÃ ĐO (không được đọc thành "đã chạy")

* **J&T sandbox / production thật** — `V-G09-01` + `V-13906-05` CHƯA CẤP. `BLOCKED`.
* **Callback theo sơ đồ `jt_digest` của hãng** — cần câu 24 + câu 6–7. `BLOCKED`.
* TLS thật · tunnel/VPS · deploy · nhiều tiến trình · PostgreSQL (D-8) · dữ liệu thật.
* Hình dạng **đầy đủ** của phản hồi xác nhận vẫn ở mức `CHUA_TAI_LIEU` (B3): lượt này chỉ đo được
  rằng phản hồi **có** `code=1` và mã HTTP **giữ nguyên** 202/200 — **không** đổi, vì tài liệu
  chưa trả lời mã HTTP nào là đúng.
* Chỉ đo trên máy này (`uname -s` = Darwin) và SQLite của môi trường; **không** đo đa nền tảng.

## 9. MỘT HỎNG CỦA MÔI TRƯỜNG (không phải của mã) — ghi ra để không ai đọc nhầm

`sh app/thu/chay_tat_ca.sh` báo **hai** bộ hỏng: `thu_bao_mat.py`
(`test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git`) và `thu_tich_hop.py`
(`test_04_khoa_ma_hoa_khong_duoc_vao_git`, `test_11_khong_co_secret_that_trong_cay_lam_viec`).
Nguyên nhân **đã đo**: phiên Orca này đặt `GIT_CONFIG_COUNT=2` nhưng **thiếu**
`GIT_CONFIG_KEY_0/1`, nên **mọi** lệnh `git` thoát **128**; cả ba ca hỏng đều gọi
`git check-ignore` / `git ls-files` bằng tiến trình con:

```
$ git check-ignore -q app/du-lieu/khoa/goc.key            → exit 128
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
      git check-ignore -q app/du-lieu/khoa/goc.key        → exit 0
$ env -u GIT_CONFIG_COUNT … python3 app/thu/thu_bao_mat.py  → Ran 57 tests · OK (exit 0)
$ env -u GIT_CONFIG_COUNT … python3 app/thu/thu_tich_hop.py → Ran 12 tests · OK (exit 0)
```

Hai bộ ấy hỏng vì môi trường, **không** vì mã của làn này (lượt này không sửa `bao_mat.py` /
`secret_provider.py` / `thu_tich_hop.py` / `.gitignore`). Ca `test_n01` của tôi cũng gọi tiến
trình con nhưng **không** dùng `git`, nên không dính vấn đề này.

## 10. TỆP ĐÃ SỬA

```
 app/webhook.py            | +137  (W07: uỷ quyền replay + chốt nguyên tử trong câu ghi)
 app/thu/thu_webhook_jt.py | +617  (77 → 99 ca: L/M/N của G17)
 trien_khai/g17/           | mới   (chot_an_toan.py · harness_webhook.py · chay_harness.sh · README.md)
 docs/G17_WEBHOOK.md       | mới   (tài liệu này)
```
