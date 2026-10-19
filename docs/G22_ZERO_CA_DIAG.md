# G22/X1 — CHẨN ĐOÁN 12 BỘ THỬ "0 CA": BỘ CHẾT, BỘ CHẠY RỒI HỎNG, VÀ BỘ ĐẾM SAI

> **Vai:** X1 (worker chẩn đoán) · **Task:** `task_3574a3da6404` · **Dispatch:** `ctx_daccb040940e`
> **Nền đo:** `integration/g20` @ **`6949d8c567320993d72bb8156dc226acf90bddfe`**
> (`git rev-parse HEAD`, mã thoát 0 — sau khi gỡ gia đình `GIT_CONFIG_*` dị dạng, xem §1.1)
> **Hai tệp làn này được phép tạo:** `app/thu/thu_g22_zeroca.py` (mới · 730 dòng ·
> `sha256 72619bb00e86b9ae05c655cc594314c255aed2b33154e2fd73c00749d57583f1`) ·
> `docs/G22_ZERO_CA_DIAG.md` (tệp này).
> **KHÔNG sửa một dòng mã sản phẩm / bộ thử nào.** §10 chứng minh bằng `git status --porcelain -uall`.
> **Chỉ chẩn đoán và báo cáo.** Mọi chỗ đề nghị sửa đều ghi rõ "AG-00 giao lần khác", không tự sửa.

**Lệnh đo gốc (một lệnh):**

```sh
sh app/thu/chay_tat_ca.sh          # EXIT=1 · 1961 ca · 69 bộ · 30 bộ đỏ
```

**Lệnh chạy bộ kiểm của làn này (một lệnh, không cần biến môi trường):**

```sh
python3 app/thu/thu_g22_zeroca.py                  # tự kiểm bộ dò: 17 ca · OK · EXIT=0
python3 app/thu/thu_g22_zeroca.py --do-lai         # đo lại 12 bộ: 12/12 KHỚP · EXIT=0
python3 app/thu/thu_g22_zeroca.py --do-lai --khai-kho   # sau khi khai kho: 12/12 KHỚP · EXIT=0
```

---

## 0. TÓM TẮT MỘT MÀN HÌNH

Mười hai bộ in ra `0 ca` **không phải mười hai bộ chết cùng một kiểu**. Đo trực tiếp từng bộ
(`python3 app/thu/<tên>.py`, cwd = gốc repo) cho ra bốn nguyên nhân khác hẳn nhau:

| # | Bộ thử | Exit thật | Số ca thật | Dòng lỗi đầu tiên (rút gọn) | Nhóm |
|---|---|---|---|---|---|
| 1 | `thu_bien_driver.py` | **1** | **0** | `AssertionError: tệp nạp trực tiếp sqlite3 …: migrate.py dòng [26]` | **(c)** lỗi thật |
| 2 | `thu_g17_baomat.py` | **1** | **0** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` (ca `e4`) | **(a)** tự chối |
| 3 | `thu_g18_maysrv.py` | **1** | **0** | `ERROR: setUpModule` → `RuntimeError: migrate.py hỏng` | **(a)** tự chối |
| 4 | `thu_g18_multiprocess.py` | **1** | **0** | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` …` | **(a)** tự chối |
| 5 | `thu_g19_gioihan.py` | **1** | **0** | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` …` | **(a)** tự chối |
| 6 | `thu_g21_gioihan.py` | **1** | **0** | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` …` | **(a)** tự chối |
| 7 | `thu_g22_gioihan.py` | **1** | **32** ← KHÔNG phải 0 | `✗ B3.a_bo_goc_tra_ma_khac_0 — C5 ĐỎ LẠI …` | **KHÔNG CHẾT** — lỗi ĐẾM |
| 8 | `thu_giao_dich.py` | **1** | **0** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` | **(a)** tự chối |
| 9 | `thu_han_muc_nguyen_tu.py` | **1** | **0** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` | **(a)** tự chối |
| 10 | `thu_header_bao_mat.py` | **1** | **0** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` | **(a)** tự chối |
| 11 | `thu_truy_van.py` | **1** | **0** | `ERROR: setUpClass` → `RuntimeError: migrate hỏng` | **(a)** tự chối |
| 12 | `thu_g22_e2e.py` | **2** | **0** | `KHÔNG có binary Chromium … chromium_headless_shell-1194 …` | **(b)** thiếu phụ thuộc |

Đọc bảng này cho đúng:

* **9/12 bộ chết vì MỘT dòng khai thiếu**: `VIP_KHO_DANG_CHAY=sqlite`. Đó là chốt fail-closed
  của sản phẩm (`app/migrate.py::_tu_choi_chua_khai`), không phải bộ thử hỏng. Đặt biến rồi
  chạy lại: **cả 9 bộ đều chạy ca** (5–40 ca) — §3.2 có bảng TRƯỚC/SAU.
* **1/12 chết vì thiếu phụ thuộc**: binary Chromium **ghim cứng `1194`** không có trên máy.
  Bộ thoát **2** = `KHONG_DUNG_DUOC_NEN` — fail-closed ĐÚNG, không phải xanh giả.
* **1/12 là LỖI THẬT**: `migrate.py` nạp trực tiếp `sqlite3` ở dòng 26, vi phạm biên driver mà
  `thu_bien_driver.py` canh. Bộ canh đang làm đúng việc của nó — §5.1.
* **1/12 KHÔNG CHẾT**: `thu_g22_gioihan.py` chạy **32 ca**, in `TỔNG: 32 ca — HỎNG`. Bảng của
  `chay_tat_ca.sh` đọc ra 0 vì hai `grep` của nó không có khuôn `TỔNG: N ca` — §6.
* **Con số "0 ca" là đúng như bảng in ra, nhưng nhãn "chết vì NỀN" chỉ đúng cho 10/12**
  (9 tự chối + 1 thiếu phụ thuộc). `thu_bien_driver.py` chết trước ca đầu vì **một lỗi thật
  của mã sản phẩm**; `thu_g22_gioihan.py` thì **không chết** — nó chạy 32 ca và bị ĐẾM sai.

> **Một chỗ đề bài nói khác số đo:** đề bài ghi `thu_g22_e2e.py` "thoát 0 nhưng KHÔNG có dấu
> vết đã chạy ca nào". Trên máy này, tại đúng SHA `6949d8c`, chạy **không tham số** (đúng cách
> `chay_tat_ca.sh` gọi) cho **exit = 2**, không phải 0 — §4.2 có cả ba chế độ đo. Không có
> đường nào ở đây cho ra "exit 0 + 0 ca"; nếu lượt khác đo được 0 thì môi trường khác (có
> Chromium) chứ không phải mã này.

---

## 1. CÁCH ĐO VÀ MÔI TRƯỜNG

### 1.1 Môi trường git hỏng — phải gỡ trước khi đo (`N-G18-00`)

Phiên làm việc này có `GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0/1`. Hệ quả đo được:
**mọi lệnh git thoát 128**, kể cả `git rev-parse HEAD`:

```
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
```

`app/thu/chay_tat_ca.sh` đã tự chuẩn hoá (dòng 27–43) nên bảng tổng vẫn đo được. Trong báo cáo
này, mọi lệnh đo trực tiếp đều **gỡ gia đình `GIT_CONFIG_*` trước**:

```sh
unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
```

Đây là **một cái bẫy tái lập** đã được ghi ở `docs/QA_G18.md` (`N-G18-00`): cùng cây, cùng HEAD,
mà lượt có biến hỏng cho exit 1 còn lượt đã gỡ cho exit 0. Mọi con số dưới đây đo trong môi
trường **đã gỡ**.

### 1.2 Lệnh đo trực tiếp từng bộ

```sh
cd <gốc repo>
python3 app/thu/<tên>.py > /tmp/x1_zeroca/direct/<tên>.txt 2>&1; echo $?
```

Ghi lại: mã thoát thật · stdout+stderr thật · dòng lỗi đầu tiên · có phải lỗi import không ·
có phải bộ/migrate TỰ CHỐI vì thiếu khai báo không. Không bộ nào trong 12 bộ là lỗi import
(`ModuleNotFoundError`/`ImportError`): **0/12**.

### 1.3 Bộ chạy chung — số đo gốc

`sh app/thu/chay_tat_ca.sh` (bảng đầy đủ ở đầu ra, tệp tạm `/tmp/x1_zeroca/full_baseline.txt`):

```
  python:   1961 ca · 69 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_nhat_ky_yeu_cau.py
  E2E:      (rỗng)
  bộ hỏng:  … 30 bộ .py … + chay_e2e.sh
FULL_EXIT=1
```

Vân tay cây TRƯỚC và SAU cùng là `HEAD=6949d8c56732 · diff HEAD=0 · status -uall=0` — số đo
ghim đúng vào một mốc mã.

> **1961 là con số của BẢNG ĐẾM, không phải số ca thật.** `thu_g22_gioihan.py` chạy **32 ca**
> nhưng bảng đếm đọc 0 (§6.2), nên số ca thật của lượt gốc **ít nhất là 1993**. Con số 1961 vẫn
> được dùng xuyên suốt vì đó là con số bảng tổng công bố — so sánh TRƯỚC/SAU phải cùng một
> nhiệt kế.

---

## 2. MƯỜI HAI BỘ — BẰNG CHỨNG TỪNG BỘ

Bảng dưới đây là **số đo trực tiếp**, không phải trích bảng tổng. Cột "import?" hỏi đúng câu
của đề bài: lỗi có phải `ModuleNotFoundError`/`ImportError` không.

| Bộ | Exit | Ca | Import? | Tự chối vì thiếu khai? | Dòng lỗi đầu tiên |
|---|---|---|---|---|---|
| `thu_bien_driver.py` | 1 | 0 | **KHÔNG** | KHÔNG | `AssertionError: tệp nạp trực tiếp sqlite3 (phải dùng csdl.Row/LoiToanVen/ket_noi): migrate.py dòng [26]` |
| `thu_g17_baomat.py` | 1 | 0 | KHÔNG | **CÓ** (ca `e4`) | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này` — 3 ca đầu (`e1`–`e3`) vẫn `ok` |
| `thu_g18_maysrv.py` | 1 | 0 | KHÔNG | **CÓ** (đuôi thông báo bị cắt) | `ERROR: setUpModule` → `RuntimeError: migrate.py hỏng: … khai `sqlite` …` |
| `thu_g18_multiprocess.py` | 1 | 0 | KHÔNG | **CÓ** (đuôi bị cắt) | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` cho môi trường KIỂM THỬ CÔ LẬP …` |
| `thu_g19_gioihan.py` | 1 | 0 | KHÔNG | **CÓ** (đuôi bị cắt) | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` …` |
| `thu_g21_gioihan.py` | 1 | 0 | KHÔNG | **CÓ** (đuôi bị cắt) | `RuntimeError: migrate.py hỏng (mã 1): khai `sqlite` …` |
| `thu_g22_gioihan.py` | 1 | **32** | KHÔNG | KHÔNG | `✗ B3.a_bo_goc_tra_ma_khac_0 — C5 ĐỎ LẠI khi bản uỷ quyền bị tiêm lỗi` |
| `thu_giao_dich.py` | 1 | 0 | KHÔNG | **CÓ** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` (in ngay dòng 3) |
| `thu_han_muc_nguyen_tu.py` | 1 | 0 | KHÔNG | **CÓ** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` (dòng 1) |
| `thu_header_bao_mat.py` | 1 | 0 | KHÔNG | **CÓ** | `[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …` (dòng 1) |
| `thu_truy_van.py` | 1 | 0 | KHÔNG | **CÓ** | `ERROR: setUpClass` → `RuntimeError: migrate hỏng: [migrate] TỪ CHỐI …`; cuối: `Ran 0 tests … FAILED (errors=5)` |
| `thu_g22_e2e.py` | **2** | 0 | KHÔNG | KHÔNG | `KHÔNG có binary Chromium của Playwright: …/chromium_headless_shell-1194/chrome-mac/headless_shell` |

**Ghi chú về "đuôi bị cắt":** bốn bộ (`g18_maysrv`, `g18_multiprocess`, `g19_gioihan`,
`g21_gioihan`) nhúng **400 ký tự CUỐI** của stderr vào `RuntimeError`, nên chữ `TỪ CHỐI:` ở
đầu thông báo bị mất; chỉ còn câu hướng dẫn `khai `sqlite`…`. Đó vẫn là **cùng một sự kiện**.
Bộ dò `thu_g22_zeroca.py` nhận cả hai dạng (xem §7.3).

---

## 3. NHÓM (a) — TỰ CHỐI CÓ CHỦ ĐÍCH: CHỨNG MINH BẰNG CÁCH ĐẶT BIẾN

### 3.1 Cơ chế — đọc từ mã, không từ trí nhớ

* `app/cau_hinh.py:37` — `KHO_DANG_CHAY = (os.environ.get("VIP_KHO_DANG_CHAY") or "").strip().lower() or None`
* `app/migrate.py::kho_dang_chay()` đọc `cau_hinh.KHO_DANG_CHAY` rồi tới biến môi trường ở
  **mỗi lượt gọi**; chưa khai ⇒ `_tu_choi_chua_khai()` ⇒ `SystemExit` mã 1.
* `migrate.chay()` trên thư mục dữ liệu **mới** có gọi `sao_luu()` ⇒ gặp chốt trên.
* Chín bộ dưới đây dựng nền bằng `migrate.py` trong thư mục TẠM nhưng **không khai kho**; bộ
  chạy chung cũng **không export** biến. Vì thế chúng chết ngay ở bước dựng nền.
* Đây là **lựa chọn fail-closed của sản phẩm**, đã được ghi là cái giá đo được ở
  `docs/G22_SAULUU.md` §4: "mọi bộ thử gọi `chay()` mà không khai kho đều TỪ CHỐI".

### 3.2 Chứng minh: đặt biến rồi chạy lại (số đo thật)

```sh
VIP_KHO_DANG_CHAY=sqlite python3 app/thu/<tên>.py
```

| Bộ | Không khai (exit · ca) | **Khai `VIP_KHO_DANG_CHAY=sqlite`** (exit · ca) | Kết luận |
|---|---|---|---|
| `thu_g17_baomat.py` | 1 · **0** | 1 · **31** | chạy được; còn **1 đỏ thật** (route `loc-mo-ta`, §5.2) |
| `thu_g18_maysrv.py` | 1 · **0** | **0 · 17** | `OK` |
| `thu_g18_multiprocess.py` | 1 · **0** | **0 · 26** | `26 ca — ĐẠT` |
| `thu_g19_gioihan.py` | 1 · **0** | **0 · 22** | `22 ca — ĐẠT` |
| `thu_g21_gioihan.py` | 1 · **0** | **0 · 22** | `22 ca — ĐẠT` |
| `thu_giao_dich.py` | 1 · **0** | **0 · 17** | `OK` |
| `thu_han_muc_nguyen_tu.py` | 1 · **0** | **0 · 5** | `OK` |
| `thu_header_bao_mat.py` | 1 · **0** | **0 · 8** | `OK` |
| `thu_truy_van.py` | 1 · **0** | **0 · 40** | `OK` |
| `thu_g22_gioihan.py` | 1 · **32** | 1 · **32** (5 đỏ → 3 đỏ) | không đổi bản chất: **chạy rồi hỏng**, không phải 0 ca |
| **thêm** `thu_g19_tich_hop.py` | 1 · 8 | **0 · 8** | đỏ chỉ vì runner `g21_gioihan` chết |
| **thêm** `thu_qa_g19_tich_hop.py` | 1 · 8 | **0 · 8** | như trên — mở luôn cổng C5 cho `g22_gioihan` |

**8/9 bộ nhóm (a) trở lại XANH hoàn toàn; 1 bộ (`g17`) chạy 31 ca và lộ ra một lỗi THẬT khác.**
Không bộ nào phải sửa một dòng ca thử. Đây là bằng chứng đủ mạnh để kết luận: "0 ca" của 9 bộ
này **không phải bộ thử hỏng**, mà là **một dòng khai thiếu trong môi trường chạy**.

### 3.3 Một phát hiện phụ: bảng "cái giá" trong `docs/G22_SAULUU.md` §4 ĐẾM THIẾU

Bảng §4 của tài liệu đó liệt kê **8 bộ + 1 diễn tập**. Đo lại trên cây này, **riêng trong 12 bộ
"0 ca" đã có 9 bộ** chết vì cùng nguyên nhân; **năm bộ** không có tên trong bảng đó:
`thu_g18_maysrv.py` · `thu_g18_multiprocess.py` · `thu_g19_gioihan.py` · `thu_g21_gioihan.py` ·
`thu_truy_van.py`. Ngoài 12 bộ, biến này còn làm xanh `thu_bao_mat`, `thu_g19_tich_hop`,
`thu_g21_bimat`, `thu_g22_bimat`, `thu_g22_chotcay`, `thu_qa_g17`, `thu_qa_g18`,
`thu_qa_g18_tich_hop`, `thu_qa_g19_tich_hop` và cả **E2E 41/41** (§8). Bảng §4 là **bảng mẫu,
không phải bảng đầy đủ** — nên sửa lời văn, đừng dùng nó như sổ kiểm kê.

---

## 4. NHÓM (b) — THIẾU PHỤ THUỘC: CHROMIUM GHIM `1194`

### 4.1 Thiếu gì, ở đường nào

`thu_g22_e2e.py:71–73` ghim **cứng** đường dẫn:

```
node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
```

Đo trên máy này:

```sh
$ ls node_modules/playwright-core/.local-browsers
ls: … No such file or directory                      # ← cả thư mục .local-browsers KHÔNG có
$ ls ~/Library/Caches/ms-playwright
chromium_headless_shell-1148  chromium_headless_shell-1243  chromium-1148  chromium-1243 …
```

⇒ Có **1148** và **1243** trong cache hệ thống, **không có 1194**; và bộ thử chỉ tìm trong
`node_modules`, không tìm trong cache. `playwright` phiên bản 1.56.1.

### 4.2 Ba chế độ đo — con số thật, không suy luận

| Lệnh | Exit | Dấu vết | Ý nghĩa |
|---|---|---|---|
| `python3 app/thu/thu_g22_e2e.py` (cách `chay_tat_ca.sh` gọi) | **2** | `PHÁN QUYẾT: None (mã thoát None)`; `[g22] MÃ THOÁT CỦA CỔNG = 2` | **KHÔNG DỰNG ĐƯỢC NỀN** — fail-closed đúng |
| `python3 app/thu/thu_g22_e2e.py --tu-kiem` | **0** | `Ran 31 tests … OK (skipped=2)`; `TỰ KIỂM: 31 ca · hỏng 0 · lỗi 0 · bỏ qua 2` | chỉ tự kiểm bộ dò, **KHÔNG chạy cổng** |
| `python3 app/thu/thu_g22_e2e.py --ghim-chromium` | **2** | `"ton_tai": false`, `"thuc_su_spawn": {"duong": null}` | ghim binary — không có |

**Không có chế độ nào cho "exit 0 + 0 ca"** ở môi trường này. `--tu-kiem` thoát 0 nhưng in rõ
31 ca tự kiểm (có dấu vết), và `chay_tat_ca.sh` không truyền `--tu-kiem`.

### 4.3 Cách sửa (đề nghị, CHƯA làm — cần mạng/duyệt)

```sh
PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium      # tải đúng 1194
```

Hoặc ghim lại binary đã có (`1243`) — nhưng đổi ghim là **quyết định của AG-00/QA**, không phải
của làn chẩn đoán. Việc tải Chromium cần mạng; lượt này **không tải** (local-first).

---

## 5. NHÓM (c) — LỖI THẬT: BÁO AG-00, KHÔNG SỬA

### 5.1 `migrate.py` nạp trực tiếp `sqlite3` — vi phạm biên driver

`thu_bien_driver.py` giữ danh sách **CHO PHÉP** `DUOC_NAP = {"csdl.py"}`: chỉ `csdl.py` được
`import sqlite3`; quên một tệp trong danh sách thì bộ thử **HỎNG** (an toàn), không cho qua.
Đo được:

```
AssertionError: tệp nạp trực tiếp sqlite3 (phải dùng csdl.Row/LoiToanVen/ket_noi): migrate.py dòng [26]
```

`git blame` chỉ đúng nguồn: dòng `import sqlite3` của `app/migrate.py` được thêm ở commit
**`bf8696d`** ("AG-02 (G22) DONG S8/do2b…", 16/10/2026). `migrate.py` dùng nó cho
`sao_luu()`/`khoi_phuc()`: `sqlite3.connect("file:…?mode=ro&immutable=1", uri=True)` (dòng 152),
`sqlite3.OperationalError` (162), `sqlite3.DatabaseError` (170), `sqlite3.complete_statement`
(702) — tức **có lý do kỹ thuật**, nhưng lý do đó chưa được KHAI trong danh sách cho phép.

Hai đường sửa, AG-00 chọn (lượt này **không sửa**):

1. **Khai minh bạch**: thêm `migrate.py` vào `DUOC_NAP` kèm chú thích vì sao (sao lưu cần
   `mode=ro&immutable=1` và `complete_statement` mà `csdl.py` không phơi ra); **hoặc**
2. **Gom về `csdl.py`**: đưa các phép đọc/kiểm tra đó thành hàm của `csdl.py` rồi `migrate.py`
   gọi lại — đúng tinh thần biên driver ban đầu.

Đây là lỗi **của mã sản phẩm so với bất biến kiến trúc**, không phải lỗi của bộ thử. Bộ thử
đang làm đúng việc của nó.

### 5.2 `thu_g17_baomat.py` — route mới chưa được khai trong bảng cửa

Sau khi khai kho (31 ca), còn **1 ca đỏ**:

```
FAIL: test_v1_bang_cua_phu_moi_route_trong_server (__main__.V_QuetCua)
+ ['GET /api/v2/don/loc-mo-ta (server.py:945)'] : route trong server.py CHƯA được khai trong bảng cửa
```

`server.py:945` có route này; `git log -S` chỉ commit **`146500b`** ("AGENT 06 (G22) B2 XANH: ca
03/09 la LOI BACKEND … da va route"). Tức là một làn khác thêm route để sửa lỗi sản phẩm nhưng
**không cập nhật bảng khai** của bộ thử — bộ thử canh đúng. Đường sửa: thêm route vào bảng cửa
của `thu_g17_baomat.py` (ngoài phạm vi ghi của làn này).

### 5.3 `thu_g22_gioihan.py` — cổng chống XANH GIẢ có một lỗ XANH GIẢ

Bộ này **chạy 32 ca** (không phải 0). Với kho đã khai: `ĐẠT=27 · HỎNG=3 · KHUYẾT=2 · TỔNG=32`,
exit 1. Ba ca đỏ đều là chiều ĐỎ của cổng C5: tiêm lỗi vào **bản sao của bản uỷ quyền**
`thu_qa_g19_tich_hop.py` rồi đo qua `thu_qa_g20.py C4_C5_NoKhac.test_c5_co_bo_thu_g19_tong_hop_chay_duoc`:

| Phép tiêm (một dòng) | Kỳ vọng | Đo được | Vì sao C5 vẫn XANH |
|---|---|---|---|
| `return [sys.executable, "-c", "import sys; sys.exit(7)"]` | C5 ĐỎ | `1/2 · phán quyết=DONG` | C5 đạt khi **MỘT TRONG HAI** ứng viên `thu_qa_g19*.py` chạy được; bản gốc còn xanh nên che bản sao chết |
| `BO_THU = …thu_g19_khong_ton_tai_GIA.py` | C5 ĐỎ | `1/2 · DONG` | như trên |
| suite rỗng 0 ca | C5 ĐỎ | `1/2 · DONG` | như trên |
| mọi ca BỎ QUA (`skip`) | C5 ĐỎ | `1/2 · DONG` | C5 chỉ đòi `Ran N` > 0, **không trừ `skipped=N`** |

Đây là **lỗ hổng xanh-giả nằm trong chính bộ dò xanh-giả** — đúng chủ đề của làn này. Đường
sửa đề nghị: C5 đòi **2/2** ứng viên tồn tại đều đạt (hoặc chỉ đòi đúng bản uỷ quyền), và trừ
`skipped` khỏi số ca "chạy thật". **Không sửa ở đây** (ngoài phạm vi ghi).

---

## 6. CÁI BẪY "0 CA" — BỘ ĐẾM CỦA `chay_tat_ca.sh`

### 6.1 Nó làm ĐÚNG gì (phải nói trước, để không "sửa" chỗ không hỏng)

`app/thu/chay_tat_ca.sh` phán **bằng mã thoát**, và đòi thêm **dấu vết đã chạy + số ca > 0**
(dòng 120–121). Vì thế:

* một bộ thoát 0 mà **không chạy ca nào** bị bắt: dòng 134 in `thoát 0 nhưng KHÔNG có dấu vết
  đã chạy ca nào` ⇒ HỎNG. **Không có đường xanh giả ở tầng này.**
* `skipped` là phán quyết THỨ BA (`⊘ BỎ QUA`), không gộp vào ĐẠT.
* bộ chạy 0 ca vì chết vẫn bị đánh đỏ — nên ở mức "đỏ/xanh", bảng tổng **không bỏ sót**.

### 6.2 Nó làm CHƯA ĐÚNG gì

Bộ đếm ca (dòng 99–103) chỉ nhận **hai khuôn**:

```sh
grep -oE 'Ran [0-9]+'                       # unittest
grep -oE '[0-9]+ ca — ĐẠT'                  # bộ viết tay
```

Hệ quả đo được: `thu_g22_gioihan.py` in `TỔNG: 32 ca — HỎNG` ⇒ bộ đếm đọc **0**, dù bộ đã chạy
**32 ca**. Nó vẫn bị đánh HỎNG (đúng phán quyết), nhưng nhãn `0 ca` là **SAI** — và nếu người
trực đọc "0 ca" thành "chết trước khi chạy" thì họ đang chẩn đoán sai 1/12 bộ.

Hướng sửa rẻ (AG-00 giao lần khác): thêm **một** khuôn `TỔNG: ([0-9]+) ca` vào bộ đếm.

### 6.3 Bảng đối chiếu: bộ chạy chung đọc gì · đo trực tiếp ra gì

| Bộ | `chay_tat_ca.sh` đọc | Đo trực tiếp | Lệch? |
|---|---|---|---|
| 9 bộ nhóm (a) + `thu_bien_driver` | 0 | 0 | **không** — chết thật/nền |
| `thu_g22_e2e.py` | 0 (exit 2) | 0 (exit 2) | **không** — nhưng "0" ở đây là *không đủ nền*, không phải chết mã |
| `thu_g22_gioihan.py` | **0** | **32** | **CÓ** — lỗi khuôn báo cáo |

---

## 7. BỘ KIỂM `app/thu/thu_g22_zeroca.py`

### 7.1 Nó giải quyết đúng câu hỏi gì

Không phải "bắt thêm bộ đỏ" (bảng tổng đã đỏ rồi), mà **đo lại được khi một bộ chết mà không ai
biết**, và **tách "chết" khỏi "chạy rồi mới hỏng"**. Nó giữ **sổ ghim** số ca đo được tại SHA
`6949d8c` cho 12 bộ (hai cột: nguyên văn / đã khai kho) và cho **toàn bộ 70 bộ** ở chế độ
`--tat-ca`.

### 7.2 Tám phán quyết + luật so sánh BẤT ĐỐI XỨNG

| Phán quyết | Điều kiện |
|---|---|
| `DAT` | exit 0 · số ca > 0 |
| `HONG` | exit ≠ 0 · số ca > 0 (**chạy rồi mới hỏng**, KHÔNG phải 0 ca) |
| `BO_QUA` | exit 0 · 0 ca · output có `skipped` |
| `TU_CHOI` | exit ≠ 0 · 0 ca · output có `TỪ CHỐI`/`CHƯA KHAI`, **hoặc** đuôi bị cắt `khai `sqlite`` |
| `THIEU_PHU_THUOC` | exit ≠ 0 · 0 ca · `ModuleNotFoundError`/`.local-browsers`/Chromium |
| `CHET_0CA` | exit ≠ 0 · 0 ca · các trường hợp chết còn lại (không khớp hai mẫu trên) |
| `XANH_GIA_0CA` | exit 0 · 0 ca · không `skipped` — **luôn HỎNG** |
| `QUA_HAN` | vượt thời gian chờ |

Luật so sánh **cố ý bất đối xứng**: bộ **từng chạy > 0 ca nay còn 0** ⇒ **FAIL**; bộ **từng 0 ca
nay chạy > 0** ⇒ `HOI_SINH` (mốc cũ, không phải lỗi); số ca đổi nhưng vẫn > 0 ⇒ cảnh báo. Hướng
"nhiều ca hơn" không bị phạt; hướng "0 ca" bị phạt.

### 7.3 Chế độ chạy

| Lệnh | Việc | Mã thoát |
|---|---|---|
| `python3 app/thu/thu_g22_zeroca.py` | **tự kiểm** bộ dò — 17 ca, ~0,7 giây, không cần Chromium | 0 đạt · 1 hỏng |
| `--do-lai` | đo lại **12 bộ** và so sổ ghim nguyên văn (~25 giây) | 0 khớp · 1 có bộ chết mới/xanh giả · 2 mốc cũ (hồi sinh) |
| `--do-lai --khai-kho` | như trên nhưng đặt `VIP_KHO_DANG_CHAY=sqlite` — chứng minh nhóm (a) | như trên |
| `--tat-ca` | đo lại **toàn bộ** bộ thử theo sổ ghim 70 bộ (chậm) | 0 khớp · 1 có bộ chết mới |
| `--bo <tên>` | đo **một** bộ, in 40 dòng cuối | 0 (chẩn đoán) |
| `--json <tệp>` | ghi báo cáo JSON | — |

### 7.4 Tự kiểm 17 ca — có ĐỐI CHỨNG ÂM

| Nhóm ca | Ca | Chứng minh |
|---|---|---|
| **Đối chứng âm** (bộ dò KHÔNG được bắt nhầm) | `01`, `02` | bộ khoẻ in `Ran 3 … OK` / `17 ca — ĐẠT` ⇒ `DAT`, đúng số ca |
| **Đối chứng âm** | `03`, `04` | chạy 5 ca rồi hỏng ⇒ `HONG 5`, **không** bị gọi "0 ca"; in `TỔNG: 32 ca — HỎNG` ⇒ `HONG 32` (đúng ca `g22_gioihan`) |
| **Đối chứng dương** (phải bắt) | `05`–`10` | import hỏng ⇒ `THIEU_PHU_THUOC`; `TỪ CHỐI` ⇒ `TU_CHOI`; chết trước ca đầu ⇒ `CHET_0CA`; **exit 0 không in gì** ⇒ `XANH_GIA_0CA`; `Ran 0 tests … OK` ⇒ `XANH_GIA_0CA`; thiếu Chromium ⇒ `THIEU_PHU_THUOC` |
| **Đối chứng bộ so sánh** | `11`–`13` | mốc 17 ca · đo 0 ⇒ `FAIL`; mốc 17 · đo 17 ⇒ `KHOP`; mốc 0 · đo 17 ⇒ `HOI_SINH` |
| **ĐO THẬT trên bộ thật** | `14` | `thu_giao_dich.py`: không khai ⇒ **0 ca / `TU_CHOI`**; khai `sqlite` ⇒ **17 ca / `DAT` / exit 0**. Đây là cặp đối chứng (a) chạy lại được ở mọi lượt |
| **ĐO THẬT** | `15` | `thu_g22_e2e.py` **không được** rơi vào `XANH_GIA_0CA` |
| **Sổ ghim** | `16`, `17` | đủ 12 tệp, đủ hai cột ghim; sổ toàn bộ ≥ 60 bộ, phán quyết hợp lệ |

Chạy thật:

```
$ python3 app/thu/thu_g22_zeroca.py
Ran 17 tests in 0.721s
OK
TỰ KIỂM: 17 ca · hỏng 0 · lỗi 0 · bỏ qua 0      # EXIT=0
```

Vì tệp tên `thu_g22_zeroca.py` nằm trong `app/thu/`, `chay_tat_ca.sh` **tự dò** nó ở lượt sau
(`find app/thu gateway/thu -name 'thu_*.py'`) và sẽ ghi `✓ thu_g22_zeroca.py 17 ca`. Lượt đo
tổng ở §8 **chưa** có dòng ấy: vòng lặp `for` chụp danh sách tệp **một lần lúc bắt đầu**, mà
tệp này được tạo trong lúc lượt đó đang chạy — vân tay cuối lượt đã bắt đúng
`status -uall=1 dòng` và cảnh báo.

### 7.5 Đo lại 12 bộ — kết quả thật

```
$ python3 app/thu/thu_g22_zeroca.py --do-lai
TỔNG KẾT: KHOP=12                                  # EXIT=0
```

```
$ python3 app/thu/thu_g22_zeroca.py --do-lai --khai-kho
thu_bien_driver.py             1      0     CHET_0CA         KHOP
thu_g17_baomat.py              1      31    HONG             KHOP
thu_g18_maysrv.py              0      17    DAT              KHOP
thu_g18_multiprocess.py        0      26    DAT              KHOP
thu_g19_gioihan.py             0      22    DAT              KHOP
thu_g21_gioihan.py             0      22    DAT              KHOP
thu_g22_gioihan.py             1      32    HONG             KHOP
thu_giao_dich.py               0      17    DAT              KHOP
thu_han_muc_nguyen_tu.py       0      5     DAT              KHOP
thu_header_bao_mat.py          0      8     DAT              KHOP
thu_truy_van.py                0      40    DAT              KHOP
thu_g22_e2e.py                 2      0     THIEU_PHU_THUOC  KHOP
TỔNG KẾT: KHOP=12                                  # EXIT=0
```

### 7.6 Chế độ `--tat-ca` — chứng minh "chết mà không ai biết" bị bắt

Smoke test bằng **bộ giả** trong thư mục tạm (không đụng bộ thật): một bộ khoẻ 4 ca, một bộ
chết 0 ca, một bộ thoát 0 không in gì. Sổ ghim cả ba là 4 ca.

```
thu_khoe_gia.py   0   4  DAT           KHOP
thu_chet_gia.py   1   0  CHET_0CA      FAIL — từng chạy 4 ca, NAY 0 CA — chết im lặng
thu_xanh_gia.py   0   0  XANH_GIA_0CA  FAIL — thoát 0 mà không có dấu vết chạy ca nào
TỔNG KẾT: 3 bộ · 4 ca · FAIL=2 · KHOP=1            # EXIT=1
```

Đây là **đối chứng dương của cả bộ kiểm**: bộ chết im lặng và bộ xanh giả đều bị bắt, bộ khoẻ
không bị bắt oan.

---

## 8. TÁC ĐỘNG TỔNG KHI CHỈ ĐẶT BIẾN (không sửa một dòng mã nào)

```sh
VIP_KHO_DANG_CHAY=sqlite sh app/thu/chay_tat_ca.sh
```

| | Nguyên văn | **+ `VIP_KHO_DANG_CHAY=sqlite`** |
|---|---|---|
| Python (bảng đếm) | **1961 ca · 69 bộ** | **2192 ca · 70 bộ** (69 bộ gốc + `thu_nhat_ky_yeu_cau` lần đầu chạy 8 ca) |
| E2E qua HTTP | HỎNG (mã thoát 1, kết quả rỗng) | **41/41 đạt** |
| Bộ đỏ (`.py`) | **30** | **14** |
| `EXIT` | 1 | 1 |

**17 bộ `.py` + mục E2E chuyển từ đỏ sang xanh chỉ bằng một biến môi trường**: `thu_bao_mat`, `thu_g18_maysrv`,
`thu_g18_multiprocess`, `thu_g19_gioihan`, `thu_g19_tich_hop`, `thu_g21_bimat`, `thu_g21_gioihan`,
`thu_g22_bimat`, `thu_g22_chotcay`, `thu_giao_dich`, `thu_han_muc_nguyen_tu`,
`thu_header_bao_mat`, `thu_qa_g17`, `thu_qa_g18`, `thu_qa_g18_tich_hop`, `thu_qa_g19_tich_hop`,
`thu_truy_van`, `chay_e2e.sh`.

**Đọc con số 14 cho đúng:** trong 14 bộ còn đỏ, **2 bộ đỏ vì CÂY BẨN — tệp mới của lượt này
chưa commit**: `thu_qa_g21.py` (ca `test_z2_cay_khong_doi_trong_luot_do`) và
`thu_g20_baomat.py` (các ca "cây sạch"). Đo lại **hai bộ đó trên cây sạch** (tạm chuyển tệp mới
ra ngoài):

```
thu_qa_g21.py     Ran 24 tests … OK (skipped=3)
thu_g20_baomat.py Ran 28 tests … OK
```

⇒ Trên cây sạch, còn **12 bộ đỏ** (không phải 30): 1 lỗi thật biên driver (`thu_bien_driver`),
1 route chưa khai (`thu_g17_baomat`), 1 lỗi đếm + cổng C5 (`thu_g22_gioihan`), 2 thiếu Chromium
(`thu_g22_e2e`, `thu_qa_g22`), và **7 đỏ có sẵn từ trước** (`thu_g01_g02`, `thu_g19_route`,
`thu_g20_dahang`, `thu_g20_saoluu`, `thu_g21_saoluu`, `thu_migrate_dong_thoi`, `thu_qa_soat`) —
nhóm cuối **ngoài phạm vi** chẩn đoán 12 bộ của làn này.

> **Cảnh báo về con số 2192/70:** bảng tổng in `VÂN TAY SAU` với `status -uall=1 dòng`
> (`?? app/thu/thu_g22_zeroca.py`) và tự cảnh báo con số **không tái lập nguyên vẹn** khi cây có
> tệp mới chưa theo dõi. Đó là hiệu ứng của chính lượt này, không phải sản phẩm.

---

## 9. ĐỀ NGHỊ CHO AG-00 (mỗi cái một dòng, **chưa làm**)

| # | Việc | Tệp | Vì sao (số đo) |
|---|---|---|---|
| 1 | `export VIP_KHO_DANG_CHAY=sqlite` ngay sau khối chuẩn hoá git, trước vòng lặp bộ thử | `app/thu/chay_tat_ca.sh` | 9 bộ "0 ca" chạy lại được; 30 → 12 bộ đỏ trên cây sạch; E2E 41/41 |
| 2 | Thêm khuôn `TỔNG: ([0-9]+) ca` vào bộ đếm ca | `app/thu/chay_tat_ca.sh` (dòng 99–103) | `thu_g22_gioihan.py` đang bị ghi `0 ca` dù chạy **32 ca** |
| 3 | Khai route `GET /api/v2/don/loc-mo-ta` vào bảng cửa | `app/thu/thu_g17_baomat.py` | ca `test_v1` đỏ sau khi kho đã khai; route thêm ở `146500b` |
| 4 | Quyết `migrate.py:26` — cho phép có lý do, hoặc gom về `csdl.py` | `app/migrate.py` / `app/thu/thu_bien_driver.py` | `thu_bien_driver` chết trước ca đầu; dòng thêm ở `bf8696d` |
| 5 | Cổng C5 đòi **2/2** ứng viên và trừ `skipped` | `app/thu/thu_qa_g20.py` (`C4_C5_NoKhac`) | 3 đỏ + 2 KHUYẾT của `thu_g22_gioihan`; phép tiêm `exit 7` vẫn cho C5 `DONG` |
| 6 | Cài Chromium ghim `1194` (cần mạng) hoặc ghim lại `1243` | `app/thu/thu_g22_e2e.py` / `node_modules` | `thu_g22_e2e` exit 2; cache có 1148/1243, không có 1194 |

**Luật giữ nguyên:** KHÔNG nới chốt fail-closed của `migrate.py`. Việc khai `VIP_KHO_DANG_CHAY`
chỉ dành cho **nền kiểm thử cô lập**; đặt ở production là biến mọi bản sao lưu thành đường lùi
giả (`docs/G22_SAOLUU.md` §4, `docs/G22_CAUHINH.md` §5).

---

## 10. PHẠM VI VÀ BẤT BIẾN CỦA LƯỢT NÀY

* `git rev-parse HEAD` = `6949d8c567320993d72bb8156dc226acf90bddfe` — **không đổi**.
* `git status --porcelain -uall` chỉ có **đúng hai** đường, cả hai `??` (tệp mới):

```
?? app/thu/thu_g22_zeroca.py
?? docs/G22_ZERO_CA_DIAG.md
```

* **Không** sửa mã sản phẩm, **không** sửa bộ thử, **không** sửa `chay_tat_ca.sh`, **không**
  đụng `app/du-lieu/` (mọi bộ thử dùng thư mục tạm; các lần chạy có sẵn của dự án cũng vậy).
* **Không** gọi mạng/hãng/AI; không API hãng kể cả sandbox. **Không** push/deploy.
* **Không** ghi `.git` (không chạy lệnh nào ghi vào đó); không tự bấm duyệt sandbox.
* `sha256(app/thu/thu_g22_zeroca.py)` = `72619bb00e86b9ae05c655cc594314c255aed2b33154e2fd73c00749d57583f1`
  (730 dòng). Tệp này không tự ghi được sha256 của chính nó (`BAN_GIAO.md` §7.3).

---

## 11. CHƯA ĐO / GIỚI HẠN — NÓI THẲNG

1. **18 bộ đỏ KHÁC (ngoài 12 bộ "0 ca") của bảng tổng gốc chưa được chẩn đoán từng bộ.** Lượt
   này chỉ chẩn đoán 12 bộ "0 ca"; các đỏ khác (`thu_g01_g02`, `thu_g20_dahang`,
   `thu_g21_saoluu`, `thu_qa_soat`, …) chỉ được ghi nhận là **có sẵn**, không kết luận nguyên
   nhân.
2. **Chưa cài Chromium** ⇒ cổng E2E tầng 3 vẫn chưa đo được sản phẩm trên trình duyệt thật.
3. **Chưa sửa gì**, kể cả các lỗi "một dòng" — theo đúng đề bài: ghi rõ để AG-00 giao lần khác.
4. `--tat-ca` mới được smoke test bằng bộ giả + chạy các bộ trong `--do-lai`; **chưa** chạy trọn
   70 bộ một lượt bằng chính bộ kiểm (bảng tổng §8 là của `chay_tat_ca.sh`, không phải của
   `--tat-ca`).
5. Số ca là con số bộ thử **tự công bố**; bộ nào in sai thì bộ kiểm đọc sai theo — cùng giới hạn
   với `chay_tat_ca.sh`, chỉ khác là bộ kiểm đọc thêm khuôn `TỔNG: N ca`.
6. Máy đo: Darwin arm64 · Python 3.9.6 · SQLite 3.51.0 · Playwright 1.56.1. Con số ca có thể
   khác trên máy khác nếu bộ thử phụ thuộc môi trường.

---

## 12. LỆNH CHẠY LẠI TOÀN BỘ BẰNG CHỨNG

```sh
cd <gốc repo>
unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1

# 1) số đo gốc
sh app/thu/chay_tat_ca.sh                                   # 1961 ca · 69 bộ · EXIT=1 · 30 đỏ

# 2) đo trực tiếp 12 bộ (mã thoát + ca + phân loại)
python3 app/thu/thu_g22_zeroca.py --do-lai                  # 12/12 KHỚP · EXIT=0

# 3) chứng minh nhóm (a): đặt biến rồi chạy lại
python3 app/thu/thu_g22_zeroca.py --do-lai --khai-kho       # 12/12 KHỚP · EXIT=0

# 4) tự kiểm bộ dò + đối chứng âm
python3 app/thu/thu_g22_zeroca.py                           # 17 ca · OK · EXIT=0

# 5) tác động tổng (không sửa mã)
VIP_KHO_DANG_CHAY=sqlite sh app/thu/chay_tat_ca.sh          # 2192 ca · 70 bộ · EXIT=1 · 14 đỏ
```

**Kết luận một câu:** "0 ca" của 12 bộ tại SHA `6949d8c` gồm **9 bộ chỉ thiếu một dòng khai
`VIP_KHO_DANG_CHAY=sqlite`**, **1 bộ thiếu Chromium ghim `1194`**, **1 bộ lỗi thật
(`migrate.py` nạp `sqlite3` trực tiếp)**, và **1 bộ KHÔNG CHẾT** (`thu_g22_gioihan` chạy 32 ca
nhưng bộ đếm của bảng tổng không nhận khuôn `TỔNG: N ca`) — sửa một dòng khai và một khuôn đếm
sẽ đưa 10/12 bộ về đúng chỗ, hai bộ còn lại là việc thật của AG-00.
