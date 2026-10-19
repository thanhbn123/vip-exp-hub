# BEST EXPRESS — QA · E2E · SECURITY (B5)

**Vai:** B5 — QA/E2E/Security · **Ngày:** 19/10/2026 · **Nền:** `cb23312dc702`
**Chế độ:** LOCAL · MOCK — **KHÔNG PHẢI REAL PASS**
**Phạm vi ghi của B5:** `app/thu/thu_best_qa.py` · `docs/BEST_EXPRESS_QA.md` ·
`docs/BEST_EXPRESS_REAL_ACCEPTANCE.md` (3 tệp MỚI; 0 dòng mã sản phẩm bị sửa)

---

## 0. TÓM TẮT ĐIỀU HÀNH

- **Cây nền sạch và đúng mốc:** `b5-qa` @ `cb23312dc702`, `git diff HEAD` = **0 đường**,
  `git status -uall` = **0 dòng** lúc bắt đầu; `PHIEN_BAN_SCHEMA = 10`; **415** tệp theo dõi;
  **72** bộ thử tự dò (71 chạy thật + 1 bỏ qua).
- **Cây này KHÔNG có mã tích hợp BEST Express.** `app/adapter_best.py` không tồn tại;
  `git grep 12491` @ HEAD = **0 hit**; adapter đã đăng ký chỉ là **`jt`, `vtp`**.
  BEST chỉ xuất hiện dưới dạng **nhãn demo**: `mock/carriers.json`, vài dòng trong
  `pages/*`, và một mục HMAC demo trong `gateway/cau_hinh.py` (gateway demo riêng).
- **10 cổng:** PASS **3** (BEST-01, BEST-07, BEST-08) · BLOCKED **6** (02, 03, 04, 05, 06, 09) ·
  PENDING **1** (BEST-10) · FAIL **0**. **REAL PASS = 0.**
- **Bộ thử B5:** `python3 app/thu/thu_best_qa.py --giao-dien` → mã thoát **0**,
  `Ran 10 tests`, `OK (skipped=7)` — 7 skip là 6 BLOCKED + 1 PENDING, **không phải ĐẠT**.
- **Frontend E2E thật:** `sh thu_giao_dien/chay.sh` → mã thoát **0**, **65 đạt · 0 hỏng**,
  2,2 phút. Lượt đầu **HỎNG** vì thiếu nhị phân Chromium trong `node_modules` (lỗi môi trường,
  đã nối bằng symlink theo `docs/BAN_GIAO.md` §1; không sửa sản phẩm).
- **Chạy toàn bộ dự án:** exit **1** · **1990 ca / 71 bộ** · **22 bộ Python hỏng** =
  **20 bộ nền** + **2 bộ va chạm phạm vi** (`thu_qa_g21`, `thu_qa_g22` đỏ vì 3 tệp B5 chưa
  commit nằm ngoài danh sách miễn trừ cứng) · **E2E hỏng**. Chi tiết + cảnh báo của chính bộ
  chạy ở §3. B5 không sửa bộ nào trong số đó.

> **CẢNH BÁO ĐỌC BÁO CÁO:** mọi kết quả ở đây là LOCAL/MOCK. BEST-09 **BLOCKED** vì chưa có
> credentials thật / endpoint HTTPS / xác minh TLS; BEST-10 **PENDING** vì chỉ chủ doanh nghiệp
> được xác nhận. Không có dòng nào trong tài liệu này là REAL PASS.

---

## 1. VÂN TAY CÂY — TRƯỚC VÀ SAU

### 1.1 Lúc bắt đầu (09:58, trước khi B5 ghi bất cứ thứ gì)

Lệnh và kết quả THẬT:

```text
$ git rev-parse --abbrev-ref HEAD
b5-qa                                                        # rc=0
$ git rev-parse HEAD
cb23312dc702a6a1bf51e9cb53c7397770cd9637                     # rc=0
$ git status --porcelain -uall | wc -l
0                                                            # rc=0
$ git diff HEAD --name-only | wc -l
0                                                            # rc=0
$ git remote -v | wc -l
0                                                            # rc=0 (không có remote ⇒ không thể push)
$ python3 app/thu/thu_g21_chotcay.py --van-tay
{"head":"cb23312dc702a6a1bf51e9cb53c7397770cd9637","che_do":"GIT","sach":true,
 "thu_muc":{"theo_doi":"62a256667fb68df4427424146feb739c81b4877eb67782db06e02e6a1a9c3299",
            "chua_theo_doi":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "so_theo_doi":415,"so_chua_theo_doi":0}}           # rc=0
```

So với vân tay đề bài ghim: **khớp tuyệt đối** — HEAD `cb23312dc702` · chế độ `GIT` ·
diff `0` đường · status `0` dòng · **415** tệp theo dõi = `62a256667fb68df4` ·
**0** tệp mới = `e3b0c44298fc1c14`.

### 1.2 Lúc kết thúc (sau khi B5 ghi đúng 3 tệp trong phạm vi)

`git status --porcelain -uall` **không còn 0 dòng** — và đó là **đúng thiết kế**, không phải
cây bẩn:

```text
$ git status --porcelain -uall
?? app/thu/thu_best_qa.py
?? docs/BEST_EXPRESS_QA.md
?? docs/BEST_EXPRESS_REAL_ACCEPTANCE.md
$ git diff HEAD --name-only | wc -l
0                                                            # rc=0 — 0 tệp ĐÃ THEO DÕI bị sửa
$ python3 app/thu/thu_g21_chotcay.py --van-tay
... "che_do":"THU_MUC","sach":false,
    "theo_doi":"62a256667fb68df4427424146feb739c81b4877eb67782db06e02e6a1a9c3299",   # KHÔNG ĐỔI
    "chua_theo_doi":"<băm của đúng 3 tệp B5>","so_theo_doi":415,"so_chua_theo_doi":3 ...
```

**Cách đọc đúng:**

| Vế | Trước | Sau | Ý nghĩa |
|---|---|---|---|
| HEAD | `cb23312dc702` | `cb23312dc702` | không nhích |
| `git diff HEAD` | 0 đường | **0 đường** | **không một tệp sản phẩm nào bị sửa** |
| `status -uall` | 0 dòng | **3 dòng** | đúng 3 tệp MỚI của B5, không có gì khác |
| băm nội dung 415 tệp theo dõi | `62a256667fb68df4…` | **`62a256667fb68df4…`** | nội dung cây sản phẩm **không đổi** |
| băm tệp chưa theo dõi | `e3b0c442…` (rỗng) | băm của **đúng 3 tệp** | 3 tệp mới nằm đúng phạm vi ghi |

> **ĐÍNH CHÍNH so với con số ghim trong đề bài:** đề bài ghi "VÂN TAY SAU … status -uall=0
> dòng". Con số `0` đó là của **cây nền trước khi B5 ghi**. Sau khi B5 tạo 3 tệp được giao,
> status **phải** là 3 — nếu vẫn 0 thì mới là bất thường (B5 chưa ghi gì). Bằng chứng "không
> phá cây" nằm ở **`git diff HEAD` = 0** và **băm 415 tệp theo dõi không đổi**, không nằm ở
> status của tệp chưa theo dõi. Không có tệp nào ngoài 3 tệp B5 xuất hiện.

Băm từng tệp B5 (sha256, đo lúc kết thúc) được ghi ở §11.

---

## 2. NỀN ĐO VÀ LỆNH CHẠY

| Thành phần | Giá trị đo |
|---|---|
| Hệ điều hành | Darwin arm64 (macOS) |
| Python | 3.9.6 |
| SQLite | 3.51.0 |
| Máy chủ đo | bind `127.0.0.1`, cổng do hệ điều hành cấp |
| Adapter hãng | **2 đăng ký: `jt`, `vtp`** — cả hai ở chế độ MOCK; `CHO_PHEP_LIVE = False` |
| Hãng LIVE đang mở | **0** |
| Nền CSDL của bộ đo B5 | SQLite trong `$TMPDIR/veh-b5-best-qa-*` (tự xoá khi thoát) |
| Mạng | **0 kết nối ra ngoài loopback**; không gọi API BEST |
| Credentials | **0** (không đọc, không dùng, không ghi) |

Các lệnh chính (đều chạy thật, mã thoát đọc ngay sau lệnh):

```text
$ python3 app/thu/thu_best_qa.py --giao-dien
... Ran 10 tests ... OK (skipped=7)
rc=0
$ sh thu_giao_dien/chay.sh
... 65 passed (2.2m) ... mã thoát THẬT 0
rc=0
$ sh app/thu/chay_tat_ca.sh
... xem §3 ...
rc=1
```

---

## 3. CHẠY TOÀN BỘ DỰ ÁN — VÀ HAI CÁI ĐỎ DO VA CHẠM PHẠM VI

### 3.1 Lượt chạy thật (Run A) — trên cây đang giao

**Lệnh:** `sh app/thu/chay_tat_ca.sh` · **mã thoát: `1`** · bắt đầu 09:58, kết thúc 10:26
(19/10/2026), trên `cb23312`.

```text
══════════ FRONTEND ══════════
  tầng 1 (logic thuần, node):    56 ca
  tầng 2 (HTTP + tệp tĩnh):      40 ca
  tầng 3 (DOM/CSS trong Chromium thật): CÓ, nhưng KHÔNG chạy ở đây
     → chạy riêng: sh thu_giao_dien/chay.sh   (đo 15/10/2026: 26 đạt · 1 bỏ qua)

══════════ E2E QUA HTTP THẬT ══════════
  ✗ E2E HỎNG (mã thoát 1): 

══════════════════════════════════════════════════════════
  python:   1990 ca · 71 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_nhat_ky_yeu_cau.py
  frontend: 56 + 40 ca (hai tầng tự động)
  E2E:      
  bộ hỏng:  thu_g01_g02.py thu_g17_baomat.py thu_g18_maysrv.py thu_g18_multiprocess.py
            thu_g19_gioihan.py thu_g19_route.py thu_g20_dahang.py thu_g20_saoluu.py
            thu_g21_bimat.py thu_g21_gioihan.py thu_g21_saoluu.py thu_g22_chotcay.py
            thu_g22_e2e.py thu_g22_gioihan.py thu_giao_dich.py thu_han_muc_nguyen_tu.py
            thu_header_bao_mat.py thu_qa_g21.py thu_qa_g22.py thu_qa_soat.py
            thu_truy_van.py chay_e2e.sh
══════════════════════════════════════════════════════════
EXIT=1
```

**Đọc số:** **1990 ca** · **71 bộ chạy thật** + 1 bộ bỏ qua · **22 bộ Python hỏng** + `chay_e2e.sh` ·
frontend tự động **56 + 40** · E2E **HỎNG** (exit 1) · **mã thoát toàn bộ: 1**.

> **CẢNH BÁO CỦA CHÍNH BỘ CHẠY (nguyên văn trong log):** *"có làn giao tệp CHƯA THEO DÕI giữa
> lượt chạy ⇒ con số '1990 ca · 71 bộ' KHÔNG tái lập nguyên vẹn; chạy lại khi cây đứng yên nếu
> cần con số ghim."* B5 đã ghi 3 tệp trong lúc lượt chạy đang chạy — **đây là lỗi kỷ luật đo của
> B5, đã ghi nhận**. Vì vậy 1990/71 là **tham chiếu**, không phải số ghim của cây sau B5.

### 3.2 Hai cái đỏ THÊM là VA CHẠM PHẠM VI, không phải lỗi sản phẩm

Chạy lại RIÊNG hai bộ nghi vấn trên **cây đứng yên** (không sửa gì trong lúc chạy):

```text
$ python3 app/thu/thu_qa_g21.py
FAIL: test_z2_cay_khong_doi_trong_luot_do
AssertionError: Lists differ: ['?? app/thu/thu_best_qa.py', '?? docs/BES…'] != []
Ran 24 tests in 160.370s
FAILED (failures=1, skipped=3)                                  rc=1

$ python3 app/thu/thu_qa_g22.py
FAIL: test_a1_cay_dung_bang_cay_cua_nen
AssertionError: A1 ĐỎ: CÂY BẨN NGOÀI PHẠM VI:
  app/thu/thu_best_qa.py, docs/BEST_EXPRESS_QA.md, docs/BEST_EXPRESS_REAL_ACCEPTANCE.md
FAIL: test_a2_khong_sua_ma_san_pham
AssertionError: có thay đổi NGOÀI danh sách tệp được phép
Ran 24 tests in 207.103s
FAILED (failures=2, skipped=1)                                  rc=1
```

**Nguyên nhân:** `thu_qa_g21.py` (Z2) và `thu_qa_g22.py` (A_Nen/A2) miễn trừ thay đổi theo
**DANH SÁCH TÊN CỨNG** (`TEP_DUOC_PHEP`), không theo QUY TẮC vùng thử/tài liệu. 3 tệp B5 nằm
ngoài danh sách đó ⇒ 2 cổng đỏ. Đây đúng là khuôn `N-G19-03` mà chính tài liệu dự án đã ghi
(danh sách tên cứng làm làn khác giao tệp bị đỏ), **không phải** lỗi sản phẩm. B5 **không được
sửa** hai bộ đó (đề bài: không sửa bộ thử của làn khác).

**Nền sản phẩm trong đề bài (trước B5):** **20** bộ Python hỏng + E2E hỏng, exit 1, 1990 ca/71 bộ.
Run A tái hiện **đúng 20 bộ đó**; 2 bộ thêm là va chạm ở trên.

**Tổng sau B5 — phép cộng từ phép đo thành phần, KHÔNG phải một lượt chạy toàn bộ sạch:**
1990 + 10 ca B5 = **2000 ca** · 71 + 1 bộ = **72 bộ chạy thật** · **22 bộ hỏng** (20 nền + 2 va
chạm) + E2E. Muốn con số ghim duy nhất cho cây sau B5 thì AG-00 phải commit 3 tệp B5 (hoặc nới
miễn trừ theo quy tắc) rồi chạy lại toàn bộ **một lượt sạch** — B5 không tự làm được (không được
ghi `.git`).

### 3.3 Danh sách 22 bộ Python hỏng + E2E

**20 bộ nền (có sẵn từ trước B5):**

```text
thu_g01_g02.py · thu_g17_baomat.py · thu_g18_maysrv.py · thu_g18_multiprocess.py
thu_g19_gioihan.py · thu_g19_route.py · thu_g20_dahang.py · thu_g20_saoluu.py
thu_g21_bimat.py · thu_g21_gioihan.py · thu_g21_saoluu.py · thu_g22_chotcay.py
thu_g22_e2e.py · thu_g22_gioihan.py · thu_giao_dich.py · thu_han_muc_nguyen_tu.py
thu_header_bao_mat.py · thu_qa_soat.py · thu_truy_van.py · chay_e2e.sh
```

**2 bộ thêm do va chạm phạm vi (mục 3.2):**

```text
thu_qa_g21.py  (Z2 — cây có thay đổi ngoài danh sách cứng)
thu_qa_g22.py  (A_Nen/A2 — cùng lý do)
```

B5 **không sửa** bộ nào trong danh sách này (đề bài: "KHÔNG sửa bộ thử của làn khác").

### 3.4 E2E qua HTTP thật — HỎNG ở nền

```text
══════════ E2E QUA HTTP THẬT ══════════
  ✗ E2E HỎNG (mã thoát 1): 
```

Bộ chạy không in thêm kết quả `KẾT QUẢ: n/m` (chuỗi rỗng), nên **không có số ca E2E** để báo —
chỉ có mã thoát **1**. B5 không sửa `chay_e2e.sh` (ngoài phạm vi). Đây là nợ có sẵn của nền.

### 3.5 Frontend tầng 3 — con số trong bộ chạy đã CŨ

Dòng `(đo 15/10/2026: 26 đạt · 1 bỏ qua)` trong `chay_tat_ca.sh` là **số cũ**. Đo lại ngày
19/10/2026: **65 đạt · 0 hỏng · 0 bỏ qua**, mã thoát 0 (xem BEST-08). Không dùng số 26/1 để
kết luận cho hôm nay.

---

## 4. BẢNG 10 CỔNG

| Mã | Cổng | Kết quả | Bằng chứng chính (chi tiết ở §5) |
|---|---|---|---|
| **BEST-01** | Repository Baseline | **PASS** | HEAD `cb23312dc702`; diff `0`; status `0` lúc đầu; schema `10`; **72** bộ nền; **415** tệp; đối chứng dương bắt cây bẩn = CÓ |
| **BEST-02** | API Contract | **BLOCKED** | 0 mã BEST; `git grep 12491` @HEAD = 0; đặc tả 8/21/12491/`" "`/10/50 đã ghim nhưng **chưa có mã để đối chiếu**; tên 8 endpoint/21 trường **CHƯA KIỂM CHỨNG** |
| **BEST-03** | Authentication | **BLOCKED** | Nền tảng đạt AES-256-GCM (v3, nonce 12B, AAD sai hỏng), 2 cột secret tách rời, che token; **chưa có secret/adapter BEST** |
| **BEST-04** | Create/Update/Cancel | **BLOCKED** | Nền tảng: create/cancel không retry mù (1 lần), đọc retry 3 lần, timeout ⇒ `timeout=True`, idempotency cùng id; **chưa có adapter BEST** |
| **BEST-05** | Webhook+Tracking | **BLOCKED** | Nền tảng chỉ có `jt` (13 mã), `vtp` (19 mã), sơ đồ `jt/vtp`; **BEST 0 mã, 0 sơ đồ** ⇒ không đo được 24 mã/605→606/11 bước/đến muộn |
| **BEST-06** | Fee+PDF | **BLOCKED** | Nền tảng tách 3 loại phí 30000/35000/40000, lệch 5000; SSRF chặn http + host lạ; **BEST chưa có host PDF được phép** |
| **BEST-07** | Multi-tenant Security | **PASS (hiện trạng)** | **6/6 điều cấm** có ca + đối chứng dương: local-only, không phá adapter, tenant DENY, không đoán đặc tả, che token, TLS. **Phải chạy lại sau khi hợp nhất mã BEST** |
| **BEST-08** | Frontend E2E | **PASS (DEMO)** | `sh thu_giao_dien/chay.sh` **rc=0 · 65 đạt · 0 hỏng · 2,2 phút**; BEST chỉ là **dữ liệu demo**, không phải tích hợp thật |
| **BEST-09** | Real Account Connectivity | **BLOCKED** | 0 credentials · 0 endpoint HTTPS · 0 bản ghi TLS/hostname · 0 phê duyệt Owner · 0 adapter BEST |
| **BEST-10** | Owner Acceptance | **PENDING** | Chưa có bản ký của chủ doanh nghiệp; tài liệu này **không phải** bản ký |

**Tổng:** PASS **3** · BLOCKED **6** · PENDING **1** · FAIL **0** · **REAL PASS 0.**
Bộ đo B5: `Ran 10` · `OK (skipped=7)` · mã thoát **0**. 7 skip = 6 BLOCKED + 1 PENDING —
**skip KHÔNG phải ĐẠT**.

---

## 5. CHI TIẾT TỪNG CỔNG

### BEST-01 — Repository Baseline · **PASS**

Đo bằng `thu_best_qa.py` (hàm `_gate_01`) và lệnh tay:

```text
git rev-parse --abbrev-ref HEAD   → b5-qa                              rc=0
git rev-parse HEAD                → cb23312dc702a6a1bf51e9cb53c7397770cd9637  rc=0
git status --porcelain -uall      → 0 dòng (trước khi B5 ghi)          rc=0
git diff HEAD --name-only         → 0 đường                            rc=0
git ls-files                      → 415 tệp theo dõi                   rc=0
grep '^PHIEN_BAN_SCHEMA' app/csdl.py → PHIEN_BAN_SCHEMA = 10           rc=0
find app/thu gateway/thu -name 'thu_*.py' ! -name thu_e2e.py | wc -l
                                  → 72 (chưa kể B5) · 73 (gồm B5)      rc=0
```

**Đối chứng dương:** bộ đo tạo một repo git TẠM, commit một tệp, sửa tệp đó rồi hỏi
`git status --porcelain` — phép dò **phải** thấy dòng bẩn. Kết quả: **CÓ**. Nếu không thấy,
BEST-01 tự FAIL (phép đo cây sạch là mù).

Kết luận: cây đúng mốc, không thay đổi đã theo dõi, schema 10, 415 tệp, 72 bộ nền.

### BEST-02 — API Contract · **BLOCKED**

**Đặc tả đã xác nhận (từ đề bài, không phải Google Docs):** 8 endpoint · 21 trường ·
`ServiceId = 12491` · `District = " "` (đúng một dấu cách) · giới hạn **10/50**.

**Bằng chứng KHÔNG có mã BEST để đối chiếu:**

```text
$ git grep -n '12491' HEAD -- app gateway pages mock
(0 dòng)                                                               rc=1
$ git grep -n 'adapter_best\|ma_hang *= *"best"' HEAD -- app gateway
(0 dòng)                                                               rc=1
$ git cat-file -e HEAD:app/adapter_best.py
fatal: path 'app/adapter_best.py' does not exist in 'HEAD'             rc=128
$ python3 -c "... import adapter_jt, adapter_vtp; print(sorted(adapter._DANG_KY))"
['jt', 'vtp']                                                          rc=0
```

**BEST có mặt ở đâu?** Chỉ **nhãn demo**, không phải tích hợp:
`mock/carriers.json` (1 mục BEST demo), `mock/shipments.json` + `mock/webhook-events.json`
(dữ liệu mẫu), `pages/*` (option/pricing), `gateway/cau_hinh.py` (mục HMAC demo của
**gateway demo riêng**). Không có endpoint, không có `ServiceId`, không có adapter.

**Tự kiểm đặc tả:** bộ đo kiểm lại 8/21/12491/`" "`/10/50 và bắt được một mục "tự phong đã
kiểm chứng" mà không có bằng chứng (**đối chứng dương = CÓ**). Vì tài liệu Google Docs chưa
đọc được, **tên** 8 endpoint và **tên** 21 trường **không được đoán** — ghi thẳng là
`CHƯA KIỂM CHỨNG`.

**Kết luận:** BLOCKED — thiếu mã BEST, không phải FAIL của hợp đồng.

### BEST-03 — Authentication · **BLOCKED**

**Nền tảng (đo thật, PASS 4/4):**

| Phép kiểm | Kết quả |
|---|---|
| AES-256-GCM thật | bản mã `v3$…`, nonce **12 byte**, giải lại đúng bản rõ |
| AAD sai (tenant/hãng khác) | **ném lỗi** — không giải được |
| Bản rõ nằm trong bản mã | **Không** |
| 2 loại secret tách rời | cột `credentials_ma_hoa` **và** `webhook_secret_ma_hoa` cùng tồn tại |
| Đối chứng dương tách secret | bảng giả chỉ có 1 cột ⇒ phép kiểm **bắt được** |
| Che token | `che_bi_mat` thay token bằng `[DA-CHE]`; không đưa token vào danh sách che ⇒ token còn nguyên (**đối chứng dương**) |

**BEST-specific:** 0 tài khoản hãng `best`, 0 adapter `best` ⇒ **chưa có secret BEST nào để
đo**. Vì vậy BLOCKED; **không ghi PASS cho nền tảng thay cho BEST**.

### BEST-04 — Create/Update/Cancel · **BLOCKED**

**Nền tảng (đo thật, PASS 3/3):**

```text
createOrder: chính sách so_lan=1 · duoc_thu_lai=False · gọi thật 1 lần · ném lỗi tạm thời
getOrder:    chính sách so_lan=3 · gọi thật 3 lần · kết quả 'ok'
mock VTP:    ghi_chu=demo_force_timeout ⇒ ok=False, timeout=True
             ghi_chu bình thường        ⇒ ok=True
idempotency: cùng idem_key ⇒ cùng id (1=1) · lần 2 trả da_trung=True
```

- **Không retry mù:** create/cancel dừng sau 1 lần; chỉ thao tác ĐỌC mới retry.
- **Timeout ⇒ UNKNOWN:** `timeout=True`, không bị coi là thành công.
- **Idempotency:** khoá trùng trả đúng đơn cũ, không tạo đơn thứ hai.

**BEST-specific:** chưa có adapter BEST ⇒ **BLOCKED**. Ba phép kiểm trên là của nền tảng,
không phải bằng chứng cho hành vi create/update/cancel của BEST.

### BEST-05 — Webhook + Tracking · **BLOCKED**

```text
bảng mã trạng thái: {'jt': 13, 'vtp': 19}     # BEST: KHÔNG có
bảng mã lỗi:        {'jt': 27}                 # BEST: KHÔNG có
sơ đồ xác thực webhook: ['jt', 'vtp']          # BEST: KHÔNG có
ánh xạ thử: anh_xa('vtp', 605) → biet_ma=False, trang_thai=None
            anh_xa('vtp', 606) → biet_ma=False, trang_thai=None
```

Không có bảng mã BEST ⇒ **không thể** kiểm 24 mã, **không thể** kiểm 605→606, không có sơ đồ
chữ ký BEST, không có đường đo sự kiện đến muộn / tenant của BEST. 11 bước webhook: đề bài
nêu **số bước**, không nêu tên bước; tài liệu chưa đọc được ⇒ **CHƯA KIỂM CHỨNG**, không đoán.

**Kết luận:** BLOCKED.

### BEST-06 — Fee + PDF · **BLOCKED**

**Nền tảng (đo thật, PASS 2/2):**

```text
phí 3 loại tách rời: bao_gia=30000 · thuc_te_hang=35000 · du_kien_thu_khach=40000
chênh lệch không gộp: lệch báo giá=5000 · lệch thu khách=5000
SSRF: http://<host hãng> bị chặn (url-sai) · https://<host hãng> nhận
      https://evil.example.com bị chặn (host-bi-tu-choi)   ← đối chứng dương
      host BEST 'api.bestexpress.vn' KHÔNG nằm trong danh sách trắng
```

Ba loại phí của nền tảng (`bao_gia` · `thuc_te_hang` · `du_kien_thu_khach`) được đối chiếu
tạm với **Estimated / Actual / Contract** của đề bài — **đây là ánh xạ tạm, CHƯA KIỂM CHỨNG**
với tài liệu BEST (tên trường thật chưa đọc được).

**BEST-specific:** chưa có phí BEST, chưa có hostname PDF BEST ⇒ **BLOCKED**. Không có đường
tải PDF từ URL nào cho BEST, nên cũng chưa có SSRF guard BEST để PASS.

### BEST-07 — Multi-tenant Security · **PASS (hiện trạng)**

**6 điều cấm — mỗi điều một ca + đối chứng dương:**

| Mã | Điều cấm | Kết quả đo | Đối chứng dương |
|---|---|---|---|
| C1 | Local-only; không gọi API BEST; không credentials thật | remote git **0**; biến môi trường chứa `best` **0**; mọi adapter `CHO_PHEP_LIVE=False`; tạo adapter `production` **bị chặn**; host BEST **bị chặn** | tạo adapter `mock` **mở được**; `host_duoc_phep('api.bestexpress.vn')` = False |
| C2 | Không xoá dữ liệu / phá adapter | `git diff HEAD` cho 3 adapter = **0**; blob y HEAD = **đúng**; bảng nền `tenants=2 · users=9 · carrier_accounts=4` **không giảm**; CSDL tạm **ngoài cây** | sửa 1 byte trong tệp tạm ⇒ băm **đổi** (phép dò không mù) |
| C3 | Tenant_id; không xác định tenant ⇒ DENY | đọc chéo tenant A→đơn B = **None**; đọc đúng tenant B = **có**; `tenant_tu_account(None)` **ném**; tenant lấy từ `carrier_account`, **không** từ payload; payload tenant **không** vào SQL | tenant hợp lệ trả **7**; chuỗi SQL giả dùng payload tenant ⇒ phép dò **bắt được** |
| C4 | Không đoán endpoint/schema | 9/9 mục đặc tả còn `da_kiem_chung=False`; 0 hit host BEST; tự kiểm đặc tả **ĐẠT** | mục "tự phong" ⇒ tự kiểm **bắt được** |
| C5 | Không ghi secret/token vào log/audit/response | token đã **bị che**; token **không** có trong bản mã; token **không** có trong thông điệp lỗi | không đưa token vào danh sách che ⇒ token **còn nguyên** (thấy được) |
| C6 | Không hạ TLS / tắt xác minh / dùng HTTP | `http://<host hãng>` **bị chặn**; `https://<host hãng>` **nhận**; dùng `ssl.create_default_context`; **0** dấu hiệu `verify=False`/`CERT_NONE`/`_create_unverified_context` | regex dò trên chuỗi giả `_create_unverified_context()` ⇒ **bắt được** |

**Phạm vi của PASS này — phải đọc:** đây là PASS của **hiện trạng cây chưa có mã BEST**.
Không có nghĩa là tích hợp BEST tương lai sẽ an toàn. **Khi B1–B4 hợp nhất, phải chạy lại
BEST-07 trên mã BEST**; PASS này không thay thế được lần chạy đó.

### BEST-08 — Frontend E2E · **PASS (DEMO)**

**Lượt 1 — HỎNG vì môi trường (không phải sản phẩm):**

```text
$ sh thu_giao_dien/chay.sh
... 10 failed · 3 passed · 52 did not run ...
Error: browserType.launch: Executable doesn't exist at
  .../node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
mã thoát THẬT 1
```

`node_modules/` của worktree này thiếu thư mục `.local-browsers`. Theo `docs/BAN_GIAO.md` §1,
trình duyệt của dự án nằm ở `~/code/veh4-g12-playwright/node_modules/...`. B5 đã **nối symlink**
`node_modules/playwright-core/.local-browsers` trỏ tới bản đó — **không sửa mã sản phẩm**,
`node_modules` nằm ngoài git nên **không đổi vân tay**.

**Lượt 2 — chạy thật, ĐẠT:**

```text
$ sh thu_giao_dien/chay.sh
... Running 65 tests using 1 worker ...
... 65 passed (2.2m) ...
mã thoát THẬT 0
```

| Vế | Giá trị |
|---|---|
| Mã thoát | **0** |
| Playwright | **65 passed · 0 failed · 0 skipped · 0 did not run** |
| Thời gian | 2,2 phút |
| Trình duyệt | Chromium đóng gói trong `node_modules` (không dùng cache hệ thống) |
| Phạm vi | 375/768/1280 · không Safari/Firefox · không thiết bị cảm ứng thật |

**Nhưng đây là PASS của giao diện DEMO:** BEST chỉ xuất hiện ở `mock/carriers.json`,
option trong `pages/create-order.html`, bảng giá `pages/pricing.js`, dropdown
`pages/settings.html` — **không có màn hình tích hợp BEST thật**, không có luồng tạo đơn BEST
qua API BEST. Vì vậy ghi **PASS (DEMO)**, không phải REAL PASS.

### BEST-09 — Real Account Connectivity · **BLOCKED**

Danh sách **THIẾU** (đo thật):

```text
credentials BEST trong môi trường: 0
tài khoản BEST trong CSDL tạm:     0
host/endpoint BEST trong mã:       0 hit
adapter BEST:                      KHÔNG
remote git:                        0 (không thể push)
bằng chứng TLS/hostname endpoint:  0 (không có endpoint nào)
```

Cụ thể còn thiếu: **credentials thật** · **endpoint HTTPS đã xác minh** · **bản ghi chứng chỉ
+ hostname (TLS)** · **phê duyệt của chủ doanh nghiệp** · **tài khoản test** · **tài liệu API
BEST đã đọc**. Theo đúng đề bài: **KHÔNG được ghi PASS**. Xem quy trình ở
`docs/BEST_EXPRESS_REAL_ACCEPTANCE.md`.

### BEST-10 — Owner Acceptance · **PENDING**

Chưa có bản ký của chủ doanh nghiệp cho BEST. Hai tài liệu do B5 viết **không phải** bản ký
và bộ đo **không đếm chúng** là bằng chứng. Chỉ chủ doanh nghiệp được xác nhận; agent không
được tự quyết. Trạng thái: **PENDING**.

---

## 6. ĐỐI CHỨNG DƯƠNG — BẢNG TỔNG

| Cổng | Phép đo phủ định | Đối chứng dương (chứng minh phép đo KHÔNG mù) | Kết quả |
|---|---|---|---|
| 01 | "cây không bẩn" | repo tạm bị sửa ⇒ `git status` thấy dòng bẩn | **CÓ** |
| 02 | "không có mã BEST" | tự kiểm bắt mục khai khống; bộ quét vẫn đếm được **nhãn demo** `BEST Express` trong `pages/*` ⇒ "0 hit endpoint" là vắng thật, không phải mù | **CÓ** |
| 03 | "BEST chưa có secret" | bảng giả thiếu cột secret bị bắt; token không che thì còn nguyên | **CÓ** |
| 04 | "create không retry" | thao tác đọc retry đúng 3 lần (cùng bộ đếm) | **CÓ** |
| 05 | "BEST chưa có bảng mã" | bảng `jt`/`vtp` vẫn đọc được (bộ quét registry không mù) | **CÓ** |
| 06 | "BEST chưa có host PDF" | https host hãng nhận; host lạ bị chặn | **CÓ** |
| 07 | 6 điều cấm | 6 đối chứng dương riêng (bảng §5) | **CÓ** |
| 08 | "E2E chạy được" | lượt 1 HỎNG thật vì thiếu Chromium (bộ đo thấy lỗi), lượt 2 ĐẠT | **CÓ** |
| 09 | "chưa kết nối thật" | bộ quét vẫn thấy nhãn `BEST Express` demo trong mock/UI ⇒ 0 hit endpoint là thật | **CÓ** |
| 10 | "chưa có chữ ký Owner" | không có bản ký nào trong repo; tài liệu quy trình bị loại khỏi phép đếm | **CÓ** |

---

## 7. MOCK PASS KHÁC REAL PASS — CÁCH ĐỌC

| Loại | Đã đo được gì | Chưa đo được gì |
|---|---|---|
| **MOCK/LOCAL (báo cáo này)** | Nền tảng: AES-GCM, tách secret, retry/timeout/idempotency, tenant DENY, che token, SSRF guard, phí 3 loại, frontend E2E | Hành vi **của BEST**: 8 endpoint, 21 trường, 24 mã, 11 bước webhook, PDF BEST, chữ ký BEST |
| **REAL (BEST-09/10)** | **0** | Tất cả: credentials thật, endpoint HTTPS, TLS/hostname, chứng chỉ, tài khoản test, phê duyệt Owner |

**Vì vậy:** 3 PASS trong báo cáo này = 1 PASS baseline + 1 PASS hiện trạng bảo mật nền tảng +
1 PASS giao diện DEMO. **Không có REAL PASS nào.** Bất kỳ ai đọc "PASS=3" mà bỏ chữ
"LOCAL/MOCK/DEMO" là đọc sai báo cáo.

---

## 8. CÁI GÌ CHƯA ĐO ĐƯỢC (ngoài phạm vi)

| Hạng mục | Lý do |
|---|---|
| API BEST thật (8 endpoint/21 trường/12491/`" "`/10/50) | Không có mã BEST trong cây; tài liệu Google Docs chưa đọc được |
| 11 bước webhook / 24 mã / 605→606 của BEST | Không có bảng mã/sơ đồ BEST |
| PDF BEST + SSRF của BEST | Không có hostname PDF BEST được phép |
| Credentials thật, endpoint HTTPS, TLS/hostname | Không có; và **không được dùng** ở lượt này |
| Đơn thật / production | Cấm tuyệt đối |
| PostgreSQL nghiệp vụ | Ngoài phạm vi B5; mới thử schema trên cụm tạm |
| Nhiều tiến trình / rate limit liên tiến trình | Ngoài phạm vi B5 |
| Safari/Firefox/thiết bị thật | Ngoài phạm vi frontend |
| Chữ ký Owner | Chỉ Owner được làm |
| 20 bộ thử hỏng sẵn | Ngoài phạm vi sửa của B5; ghi nhận ở §3 |

---

## 9. PHÁT HIỆN & RỦI RO

1. **BLOCKER LỚN NHẤT: nền `cb23312` không có mã tích hợp BEST.** Các nhánh `b1-adapter`,
   `b2-auth`, `b3-webhook`, `b4-frontend` đều đang ở đúng `cb23312` (đo `git rev-parse`).
   **Tại thời điểm kết thúc (10:30), `best/integration` vẫn SẠCH**, nhưng worktree của bốn làn
   kia đã có tệp MỚI **CHƯA COMMIT** (đo `git status --porcelain -uall`: b1=4 · b2=3 · b3=3 ·
   b4=5 dòng), gồm `app/adapter_best.py`, `app/http_best.py`, `app/xac_thuc_best.py`,
   `app/webhook_best.py`, `pages/best.html`, `admin/best.js`… **Chưa một tệp nào vào
   `best/integration` hay vào cây B5.** Vì vậy 6/10 cổng BLOCKED. Đây là **thiếu phụ thuộc
   chờ AG-00 hợp nhất**, không phải lỗi sản phẩm — nhưng nghĩa là **chưa thể nghiệm thu BEST**.
2. **Nhãn BEST trong giao diện demo có thể gây hiểu nhầm.** `pages/create-order.html`,
   `pages/pricing.js`, `pages/settings.html`, `mock/carriers.json` có "BEST Express" như một
   lựa chọn/bảng giá demo. Người dùng có thể tưởng đã tích hợp. **Đề nghị** (không tự sửa vì
   ngoài phạm vi): gắn nhãn "DEMO — chưa tích hợp" hoặc ẩn cho tới khi B1–B4 xong.
3. **Gateway demo có mục BEST HMAC với secret demo hard-code** (`gateway/cau_hinh.py`). Đây là
   **gateway demo riêng**, không phải adapter hub, nhưng là một secret nằm trong mã. Không
   được dùng cho production; nếu chuyển sang thật phải đưa vào kho mã hoá.
4. **Frontend E2E phụ thuộc nhị phân Chromium ngoài git.** Worktree này thiếu
   `node_modules/playwright-core/.local-browsers`; B5 đã nối **tạm** theo `BAN_GIAO` §1 để đo
   (65 đạt), rồi **gỡ symlink** để không để lại thay đổi ngoài 3 tệp được ghi. Đây là lỗi
   môi trường lặp lại được — nên đưa vào bước chuẩn bị CI/local.
5. **20 bộ thử hỏng sẵn + E2E hỏng** ở nền. B5 không sửa; nhưng "nền có sạch không?" câu trả
   lời là: **git sạch, bộ thử thì KHÔNG sạch** — 1990 ca, 20 bộ hỏng (22 nếu tính 2 va chạm
   phạm vi của chính B5). Không được báo "toàn bộ xanh".
6. **Hai cổng "cây sạch" miễn trừ theo TÊN CỨNG, không theo QUY TẮC.** 3 tệp B5 nằm ngoài
   `TEP_DUOC_PHEP` ⇒ `thu_qa_g21::Z2` và `thu_qa_g22::A_Nen` đỏ. Đây là lỗi cấu trúc đã tái
   diễn (`N-G19-03`), không phải lỗi sản phẩm. **Đề nghị AG-00**: commit 3 tệp B5 (để `git
   status` sạch) hoặc đổi miễn trừ sang quy tắc vùng `docs/` + `app/thu/`. B5 không được sửa
   hai bộ đó.
7. **Vân tay sau khác status 0** vì 3 tệp mới của B5 — đúng phạm vi; `git diff HEAD` = 0 và
   băm 415 tệp theo dõi không đổi chứng minh không phá cây. Xem §1.

---

## 10. CÁCH CHẠY LẠI

```sh
# 1) Vân tay TRƯỚC (phải là GIT, status 0 nếu chưa có tệp B5)
python3 app/thu/thu_g21_chotcay.py --van-tay

# 2) Ba lệnh git chính
git rev-parse HEAD
git diff HEAD --name-only
git status --porcelain -uall

# 3) Bộ 10 cổng B5 (không chạy frontend)
python3 app/thu/thu_best_qa.py
python3 app/thu/thu_best_qa.py --json

# 4) Bộ 10 cổng + frontend E2E thật.
#    Worktree thiếu Chromium: nối TẠM theo BAN_GIAO §1 rồi chạy, sau đó gỡ symlink:
#      ln -s ~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers \
#            node_modules/playwright-core/.local-browsers
python3 app/thu/thu_best_qa.py --giao-dien
#      rm node_modules/playwright-core/.local-browsers      # gỡ sau khi đo

# 5) Nghiệm thu nghiêm: thoát 1 trừ khi CẢ 10 cổng PASS
python3 app/thu/thu_best_qa.py --nghiem-thu

# 6) Toàn bộ dự án (11 phút; ghi nhận 20 bộ hỏng sẵn + E2E hỏng)
sh app/thu/chay_tat_ca.sh

# 7) Frontend tầng 3 riêng
sh thu_giao_dien/chay.sh
```

**Yêu cầu môi trường:** Python 3.9+; với frontend cần `node_modules` + Chromium của dự án
(`node_modules/playwright-core/.local-browsers`), **không** dùng cache hệ thống.

---

## 11. TỰ KIỂM BÁO CÁO — BĂM TỆP VÀ PHẠM VI

Băm sha256 (đo ngay trước khi điền mục này):

```text
app/thu/thu_best_qa.py                  c8b9c914825014e642a56731550cb4610567c43c52f1f7abb55b73aedece05dc   58610 byte
docs/BEST_EXPRESS_REAL_ACCEPTANCE.md    ff0e1abe4b88c1e34a0fff2546c31f2cc356145eb6caf2ba99e863ae71662148   13055 byte
docs/BEST_EXPRESS_QA.md                 (tự băm: shasum -a 256 docs/BEST_EXPRESS_QA.md — hash đổi khi sửa chính tệp này)
```

- `git diff HEAD` = **0** ⇒ không tệp sản phẩm nào bị sửa.
- `git status --porcelain -uall` = **đúng 3 dòng** ⇒ không có tệp lạ.
- Băm 415 tệp theo dõi = `62a256667fb68df4…` **không đổi** từ đầu đến cuối.
- Vân tay ngay trước khi điền mục này: HEAD `cb23312dc702` · chế độ `THU_MUC` · diff `0` ·
  status `3` · 3 tệp mới băm `9b6379e0bed59bde…` (điền báo cáo sau đó sẽ đổi băm 3 tệp, nhưng
  **HEAD / diff / status không đổi**; lấy lại bằng `python3 app/thu/thu_g21_chotcay.py --van-tay`).
- Bộ đo `thu_best_qa.py` không ghi ra ngoài `$TMPDIR`; tự xoá nền đo khi thoát.

---

## 12. BÀN GIAO

| Việc | Ai làm | Khi nào |
|---|---|---|
| Hợp nhất B1–B4 (đang có tệp mới chưa commit trong worktree) vào `best/integration` | AG-00 / coordinator | trước lượt QA kế tiếp |
| Chạy lại `thu_best_qa.py --giao-dien` + 6 điều cấm | B5 (lượt mới) | ngay sau hợp nhất |
| Commit/nới miễn trừ `TEP_DUOC_PHEP` để `thu_qa_g21`/`thu_qa_g22` hết đỏ do tệp B5 | AG-00 | sau khi nhận 3 tệp B5 |
| Đọc tài liệu API BEST, cập nhật 8/21/12491/`" "`/10/50 | Owner + kỹ thuật | trước BEST-09 |
| Cấp credentials qua kênh an toàn | Owner | sau khi duyệt |
| Xác minh TLS/hostname, lưu bằng chứng | Kỹ thuật | trước BEST-09 |
| Ký BEST-10 | **Owner** | cuối cùng |

**Trạng thái bàn giao:** LOCAL/MOCK đã đo xong; **REAL chưa bắt đầu**; 6 cổng BLOCKED chờ mã
BEST; 1 cổng PENDING chờ Owner.
