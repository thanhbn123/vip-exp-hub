# NGHIỆM THU G16-A — VIP EXPRESS HUB · J&T API CONNECTIVITY

> **AI-ASSISTED, KHÔNG PHẢI NGƯỜI SOÁT.** Mọi số trong tài liệu này do tác tử AI chạy trên máy này.
> Làn kiểm thử AG-01 là một tác tử AI **độc lập**, không phải người.
> `docs/BAN_GIAO.md` §2: **"AI review không phải human review. Bộ thử xanh không phải lời cho phép."**
> **Hệ này CHƯA production-ready.**

**Controller:** AG-00 (DeepSeek, trong Orca) · **Ngày:** 15/10/2026
**Mốc mã G16-A:** `c9fcaef` trên `integration/g16` · **`main` = `de740dc` (KHÔNG đổi, CHƯA gộp G13–G16)**

> **MỐC CÂY — tự đo, đừng tin tài liệu.** Theo bài học `BAN_GIAO.md` §7.3, tệp này **không** ghi SHA
> của chính commit chứa nó. Người đọc tự chạy:
> ```bash
> cd ~/Projects/vip-express-hub && git log --oneline -1 integration/g16
> ```
> **VÂN TAY CÂY của mốc `c9fcaef`:**
> `9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df`
> ```bash
> find app gateway thu_frontend thu_giao_dien -type f \
>   \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
>   | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
> ```

---

## 1. PHÁN QUYẾT CỔNG

| Cổng | Phán quyết |
|---|---|
| **G16-A HTTP TRANSPORT** | **PASS** |
| **G16-A CREDENTIAL CONFIGURATION** | **PASS** |
| **G16-A CONTRACT TESTS** | **PASS** |
| **G16-B SANDBOX** | **BLOCKED UNTIL APPROVED** |
| **G16 PRODUCTION** | **NOT AUTHORIZED** |

**KHÔNG có mức `LIVE VERIFIED`.** Chưa từng có một lượt gọi hãng nào — kể cả sandbox. Không tài
liệu nào trong đợt này được viết theo hướng đọc như đã xác minh với hãng.

---

## 2. ĐO ĐƯỢC — trên ĐÚNG cây đã commit

Vân tay **trước = sau** ở lượt chốt (`9a72ec87…`), tức con số **ghim được vào một mốc mã**. Sáu
lượt trước đó vân tay **đổi giữa lượt chạy** vì bốn làn ghi chung một cây.

| Phép đo | Kết quả THẬT |
|---|---|
| Hồi quy đầy đủ | **1284 ca · 36 bộ · 0 hỏng · 0 bỏ qua · exit 0** |
| Frontend 2 tầng | 56 + 36 |
| Frontend tầng 3 (Chromium thật) | **26 passed · 1 skipped** |
| E2E qua HTTP thật | **41/41** |
| Harness nghiệm thu G16 | **32 đạt · 12 `ĐẠT (MOCK)` · 0 hỏng · 2 BLOCKED** |
| Đồng thời 8 tiến trình × 400 phép | 3200/3200 · **0 mất cập nhật** · 0 khoá hết giờ |

**Bộ thử của G16 (mới):** `thu_http_jt` **37** · `thu_qa_g16` **61** · `thu_adapter_jt` **71** ·
`thu_hop_dong_jt` **64** · `thu_webhook_jt` **77** · `thu_tich_hop` **12**.

---

## 3. G16-A/1 — HTTP TRANSPORT (mới hoàn toàn)

`app/http_jt.py` (705 dòng) là **lớp HTTP thật đầu tiên** của dự án. `gui_form()` gửi **một** lượt
POST `application/x-www-form-urlencoded`. Ba luật cứng, cả ba đều có phép đo:

**1. Danh sách TRẮNG máy chủ — so KHỚP CHÍNH XÁC, không so chuỗi con.** AG-00 tự đo 12 trường hợp:
```
127.0.0.1 ✓ · localhost ✓ · demoopenapi.jtexpress.vn ✓ · ylopenapi.jtexpress.vn ✓
demoopenapi.jtexpress.vn.kẻ-tấn-công.example  -> TỪ CHỐI  (bẫy so chuỗi con)
169.254.169.254 (metadata cloud)             -> TỪ CHỐI
jtexpress.vn (tên miền cha)                  -> TỪ CHỐI
"" / None                                    -> TỪ CHỐI
```
Từ chối **TRƯỚC khi mở socket**. AG-01 đo độc lập bằng **bộ đếm `Connection.connect`**: 13 ca phủ
định đều từ chối với **bộ đếm nối = 0**; cả hai host J&T **đi qua được cổng mà không gửi một byte nào
ra ngoài**. `302` **không** bị đi theo (đi theo là phá danh sách trắng).

**2. Hết giờ thật.** AG-00 đo: stub chậm **3 giây**, hạn **0,5 giây** ⇒ cắt đúng **0,50 giây**, ném
`LoiTamThoi` = **đáng thử lại / CHƯA BIẾT**. Cắt kết nối giữa chừng ⇒ `LoiTamThoi`. **Treo không
bao giờ bị đọc thành công.**

**3. Ba kết cục không gộp** (`ok` / hãng TỪ CHỐI / KHÔNG BIẾT) — hợp đồng §4.

**Che bí mật:** giá trị của bốn trường credential bị che **theo TÊN TRƯỜNG, bất kể độ dài**.
*(AG-01 phát hiện `G16-05`: ngưỡng cũ "độ dài ≥ 8" để lộ credential **ngắn** — và **hai đường cho
hai câu trả lời khác nhau**: qua thân form thì không rò, qua header thì rò. AG-00 tự đo lại: bí mật
4 ký tự + 3 ký tự nay đều thành `[DA-CHE]` ở **cả hai** đường.)*

**Không tự thử lại:** `http_jt` chỉ **ném đúng loại lỗi**; việc thử lại thuộc `transport.goi()`.

---

## 4. G16-A/2 — CREDENTIAL CONFIGURATION

**Bề mặt cấu hình TRƯỚC ĐỢT NÀY CHƯA TỒN TẠI.** Đo được: không có tệp `.env` nào, và `.env.example`
**không khai một khoá J&T nào**. Nay:

| Hạng mục | Cách làm |
|---|---|
| Mặc định | `JT_MOI_TRUONG = "mock"` — không đặt gì thì hệ **không chạm mạng** |
| Cổng gọi hãng | Hai hằng số **CỐ Ý không đọc từ biến môi trường**: *một biến bật được là một biến bật NHẦM được*, và nó nằm trong môi trường tiến trình — thứ `docker inspect` đọc ra |
| Tên trường | `apiAccount` · `privateKey` (nền tảng) · `customerCode` · `password` (bưu cục) — **CHỈ TÊN**, khai trong `cau_hinh.JT_TRUONG_CREDENTIALS` |
| Hỏi "còn thiếu gì" | `jt_thieu_truong()` **chỉ trả TÊN**, không bao giờ trả giá trị (ca canh có gieo bí mật giả rồi khẳng định nó không xuất hiện) |
| Đường lưu | **DUY NHẤT** `carrier_accounts.credentials_ma_hoa` qua `bao_mat.ma_hoa_cred` (AES-256-GCM, `v3$…`) |
| `.env.example` | Khai **TÊN** và **cố ý KHÔNG khai biến** cho bốn trường — *một đường plaintext thứ hai là một đường RÒ thứ hai, và nó sẽ bị dùng vì nó tiện hơn* |

**Không hard-code · không vào Git · không in ra log.** Có ca canh cho cả ba, và ca canh bộ dò
hard-code đã được **đột biến chứng minh** (tiêm secret thật vào bản sao ⇒ bộ dò **bắt được**).

> **AG-01 phát hiện cổng này kêu nhầm 5/5** (2 khoá dict tài liệu ở `ai_job.py`, 3 fixture giả ở
> `harness_hang.py` như `"KHOA-THU-MOCK"`). Một cổng CRITICAL kêu nhầm 5/5 thì **bị học cách bỏ
> qua** — đã sửa theo 4 luật: chỉ quét mô-đun sản phẩm · chỉ literal ở vế phải phép gán · đòi dấu
> hiệu bí mật thật · giữ đối chứng dương.

---

## 5. G16-A/3 — CONTRACT TESTS

| Hạng mục | Kết quả đo |
|---|---|
| **Chữ ký** | Một cài đặt duy nhất `base64(md5_BYTES(bizContent + privateKey))`. **Vector tính tay NGOÀI bộ thử** + đối chiếu `openssl`. AG-00 tự kiểm: **3/3 vector KHỚP**, và phương pháp SAI (`hexdigest` rồi base64) ra **giá trị khác hẳn** |
| **Bằng chứng TRÊN DÂY** | Digest **tính lại ở phía máy chủ** từ chuỗi nhận được rồi mới khớp; `privateKey` **không rời đi** |
| **Mốc thời gian** | 13 chữ số, UTC+7, **độc lập múi giờ máy**. `L2-N2` (tồn từ G13–G15) **đã vá**: naive nay gắn UTC+7 tường minh — AG-00 đo ở **3 múi giờ**, cả ba cho **cùng một số** `1792033200000` |
| **COD** | Đi **`codMoney`** = `'150000'` (chuỗi số nguyên đồng); **`itemsValue` KHÔNG có mặt**; thập phân/NaN/inf/**bool**/dict bị **TỪ CHỐI**, không làm tròn |
| **Chốt D-9 (city/area)** | Vẫn **CHẶN CỨNG** ngoài `mock`; `mock` đi qua (đối chứng dương). Có ca **ĐẾM** chứng minh khi chốt nổ thì số byte rời đi = **0** |
| **Mã `110`** | `quyet_dinh("jt","110")` → **`None [AMBIGUOUS]`** — **KHÔNG áp trạng thái**, `can_soat=1`. Đối chứng dương `113 → giao_thanh_cong`. **Không đoán `110`** (D-4) |
| **Đơn trùng** | `DON_TRUNG` giữ `dang_gui` + cờ đối soát, **không hoàn suất**; đối chứng: từ chối thật **vẫn** hoàn suất |
| **Cách ly tenant** | Tenant **CHỈ** từ `carrier_account`; payload khai tenant khác bị audit và bỏ qua |

### 5.1 Quyết định hợp đồng `408`/`429` — sửa một chỗ LỆCH IM LẶNG

**Trước:** `loi_hang.tu_http` nói 408/429 **thử lại được**, `http_jt` nói **vĩnh viễn**. Cùng một
lượt gửi, **hai lớp trả lời ngược nhau** — đúng khuôn lệch im lặng.

**Chốt:** cả hai là **TẠM THỜI** (là tín hiệu *"thử lại sau"*, không phải *"yêu cầu sai"*).
**400/401/403/404 VẪN vĩnh viễn** — có **đối chứng âm** để bản vá không nới cả 4xx.

`Retry-After` được tôn trọng **và LUÔN bị chặn trần** `transport.CHO_TOI_DA = 60.0`. AG-00 tự đo:
```
5 -> 5.0 · 86400 -> 60.0 (KẸP TRẦN) · 0 -> 0.0 · -3 -> 0.0 (kẹp) · rác -> None · 408+7 -> 7.0
```
**`gui_form` CẤM ngủ** (đo bằng **AST** và bằng **hành vi**). *(AG-03 bắt được: nếu lớp HTTP tự ngủ
thì `transport.goi()` gọi lại tới `so_lan=3` lượt ⇒ tổng chờ **3 × trần** — trần 30s thành 90 giây
treo trong một yêu cầu.)*

**`408` phát ra `timeout=True` là CỐ Ý:** trong thực tế `408` không rõ nghĩa (proxy có thể phát khi
*thượng nguồn* quá hạn ⇒ yêu cầu **có thể đã được xử lý**), và chi phí hai chiều **lệch nhau** —
đoán sai theo chiều thận trọng chỉ tốn **một lượt đối soát**, chiều kia tốn **một vận đơn thật**.

---

## 6. HỢP ĐỒNG CALLBACK WEBHOOK — HOÀN THIỆN (vẫn `DOCUMENTED`, không hơn)

Hợp đồng nay là **dữ liệu MÁY ĐỌC ĐƯỢC**: `CHAN_HOP_DONG_CALLBACK` = **10 chỗ hở**, mỗi chỗ gắn
**câu hỏi gửi hãng** cụ thể và **đường mã đang bị chặn**. Năm mục Owner chỉ định danh đều có mặt:
khoá ký chiều callback (câu 6) · chuỗi đem đi ký (câu 7) · phương thức HTTP (câu 2) · hình dạng
phản hồi (câu 9) · chính sách thử lại (câu 9) — cộng 5 chỗ nữa.

**Không tự nâng mức:** `HOP_DONG_MUC = "DOCUMENTED"` · `HOP_DONG_XAC_MINH_VOI_HANG = False` ·
`PHAN_HOI_XAC_MINH = False` · `kiem_hop_dong_khong_tu_nang_muc()` trả `[]`. Có ca canh chống tự
nâng mức. **Không đoán thuật toán ký.**

**Bất biến an toàn giữ nguyên, có phép đo lặp lại:** tenant chỉ từ `carrier_account` · chống trùng
ở **TẦNG CSDL** · `110`/mã lạ ⇒ `NEEDS_REVIEW` với **0 dòng** đụng `tc_cod`/`tc_cod_chuyen`/
`tc_but_toan` · **đúng MỘT** nơi ghi cột mốc và chỉ khi `ap_dung=1` · tầng đọc còn lọc dữ liệu cũ.

---

## 7. BLOCKED — CHÍNH XÁC CÁI CÒN THIẾU

| # | Việc | Thiếu chính xác cái gì |
|---|---|---|
| 1 | **Mọi lượt gọi hãng, kể cả sandbox** | `V-G09-01` **CHƯA CẤP** |
| 2 | **Credentials J&T** | `V-13906-05` **CHƯA CẤP**; cần 4 **tên** trường; **chưa có `.env` nào** |
| 3 | **Mở `sandbox` / `production`** | Hai hằng số trong mã đang `False`; mở phải **SỬA MÃ** + có phiếu duyệt của anh Thành |
| 4 | **Nghĩa mã `110`** | D-4 — hệ **không thêm mã nào**; mọi mã chưa xác minh ⇒ `NEEDS_REVIEW` |
| 5 | **Ánh xạ `area` (D-9)** | Câu hỏi 28 + danh mục địa danh chuẩn |
| 6 | **Huỷ đơn** | Tiền tố cổng của `/api/order/cancelOrder` + **TÊN trường lý do huỷ** |
| 7 | **`calculatingFees`** | Đường dẫn + bảng tham số |
| 8 | **`printOrder`** | Đường dẫn + tham số |
| 9 | **`getOrder`** | Câu hỏi 26 |
| 10 | **`timestamp` (a)/(b) · dạng `password`** | Câu hỏi 12 và 22 |
| 11 | **Callback thật** | `V-G11-01` CHƯA CẤP (URL công khai) |
| 12 | **Bốn thao tác giữ `duong=None`** | Xem 6–9: **không dựng bừa URL** |

---

## 8. ĐIỀU **CHƯA** ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

**Danh sách này do AG-01 lập** (`docs/QA_G16.md` §5) và AG-00 **giữ nguyên, không rút gọn** — rút
gọn một danh sách "chưa đo" là cách biến nó thành "đã đo":

1. **Gọi hãng thật, kể cả sandbox** — `V-G09-01` + `V-13906-05` CHƯA CẤP.
   **TLS thật tới `*.jtexpress.vn` CHƯA ĐO.**
2. **`cancelOrder` / `getShippingFee` / `getShippingLabel` / `getOrder` đầu-cuối** — đường dẫn
   **CHƯA ĐỌC ĐƯỢC**, adapter **cố ý DỪNG** (`duong=None`).
3. **V5/V6/V7 toàn cục** — cách ly tenant ngoài đường webhook · RBAC · AES-256-GCM đầy đủ —
   **vẫn mở** từ `QA_G13_G15.md` §L2.8.
4. **Đa luồng trên `http_jt`** — bộ thử chạy tuần tự.
5. **Harness SANDBOX của AG-04** (`trien_khai/g16/**`) — AG-00 có chạy riêng (*đạt 32 ·
   `ĐẠT (MOCK)` 12 · BLOCKED 2*), nhưng **AG-01 chưa dựng phép đo độc lập** ⇒ **không** tính là
   AG-01 đã nghiệm thu.
6. **Frontend tầng 3 (Chromium)** — AG-00 đo *26 passed · 1 skipped*; AG-01 **không** chạy lại.
7. **`integration/g16` chưa gộp `main`** — đúng thiết kế; việc gộp **không** thuộc G16-A.

Và: chưa deploy · chưa push · chưa HTTPS thật · chưa tunnel · chưa VPS · chưa chuyển CSDL nghiệp
vụ sang PostgreSQL (D-8, **vẫn SQLite**) · **chưa có người đọc lại** — toàn bộ là tác tử AI.

---

## 8b. HAI PHÁT HIỆN VỀ CHÍNH **BỘ DÒ** — và cả hai đều được sửa

Đáng ghi riêng, vì cả hai đều là *"thứ dùng để kiểm chứng tự nó nói sai"* (`BAN_GIAO.md` §7.1):

**`G16-05` · cổng che bí mật kêu nhầm và hở.** Ngưỡng che đặt theo **ĐỘ DÀI ≥ 8** ⇒ credential
**ngắn** lộ nguyên văn. AG-01 tìm ra bằng cách đo **HAI đường** và thấy **hai câu trả lời khác nhau**
(qua thân form thì không rò vì bị percent-encode, qua **header** thì rò) ⇒ *"kết luận 'không rò' chỉ
từ một đường là SAI"*. Đã vá **theo TÊN TRƯỜNG, bất kể độ dài**; AG-00 tự đo lại: bí mật 4 ký tự và
3 ký tự nay đều thành `[DA-CHE]` ở **cả hai** đường.

**`G16-09` · LUẬT VÂN TAY §41 MÙ với `docs/` — kể cả với chính bản hợp đồng.** Lệnh vân tay chỉ quét
`app/ gateway/ thu_frontend/ thu_giao_dien` với 4 đuôi `.py/.mjs/.sh/.json` ⇒ **`docs/` và `.md` nằm
ngoài phạm vi**. Đo được: thêm một dòng vào **chính `docs/SHARED_CONTRACTS.md`** mà vân tay **không
đổi một ký tự** — tức sửa bản hợp đồng định nghĩa ba cổng nghiệm thu vẫn **lọt qua**. Bằng chứng
sống: `docs/G16_ACCEPTANCE.md` ra đời lúc **16:15:11**, **giữa** lượt đo, mà vân tay trước = sau; chỉ
`git status` mới thấy. **AG-01 tự nhận đây là lỗi của chính nó** (nó viết lệnh đó, AG-00 chép nguyên
văn vào luật) rồi tự kiểm cái mình viết — và nó hổng. **Đã sửa:** khoá **bằng Git là CHÍNH**
(`HEAD` + `git diff HEAD` rỗng + `git status -uall` rỗng), vân tay chỉ còn là **dự phòng** cho lúc
cây bẩn; lệnh vân tay cũng đổi sang dạng phủ mọi tệp được theo dõi.

**Cả hai đều là cổng do AG-00 hoặc AG-01 tạo ra, và cả hai đều hổng cho tới khi có người thử phá.**
Ghi lại vì đó là bài học, không phải vì nó đã xong.

---

## 9. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY

- Mọi số đo **có kèm vân tay cây + mốc giờ** theo luật §41, vì bốn làn ghi chung một cây.
- **Lượt 5 = 1270 ca và lượt 7 = 1284 ca, CÙNG `HEAD=6d05c74`** — chênh 14 ca mà không đổi mốc.
  Nếu chỉ báo "1284 ca ở `6d05c74`" mà không kèm vân tay thì **không ai kiểm được**, và lượt 5 sẽ
  trông như **sai**. Nó không sai; nó là **cây khác**.
- Phán quyết ba cổng do **AG-01 đo độc lập** (`docs/QA_G16.md`, `app/thu/thu_qa_g16.py` 61 ca), có
  **hai phép đột biến** chứng minh cổng có răng: phá danh sách trắng ⇒ **đỏ**; phá
  `if ma_http in (408, 429)` ⇒ **đỏ**.
- AG-01 tự sửa **bộ dò của chính nó** khi AG-00 chỉ ra nó kêu nhầm 5/5 — ghi lại vì đó là điều
  đáng ghi.
