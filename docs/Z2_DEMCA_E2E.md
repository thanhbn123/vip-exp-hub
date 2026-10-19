# G22/Z2 — BỘ ĐẾM ĐỌC 32 CA THÀNH 0, VÀ CHROMIUM "KHÔNG TÌM THẤY" DÙ CÓ TRÊN MÁY

> **Vai:** Z2 (worker vá) · **Task:** `task_9850634c7564` · **Dispatch:** `ctx_2bc07a5324c7`
> **Nền đo:** cây `z2-demca-e2e` @ **`cb23312dc702a6a1bf51e9cb53c7397770cd9637`**
> **Chẩn đoán gốc:** X1 — `docs/G22_ZERO_CA_DIAG.md` (§6.2 bộ đếm · §4.1 thiếu Chromium)
> **Soi gương:** `docs/G21_BANPHIM_E2E.md` §10 · `docs/G22_CAUHINH.md` §6.4 · `docs/QA_G21.md`
> §4.1 (`N-G21-04`) — bước hạ tầng symlink `.local-browsers`, đúng đường đã ghi.

**Phạm vi ghi của làn này (đúng 4 tệp):**

| Tệp | Loại | Nội dung |
|---|---|---|
| `app/thu/chay_tat_ca.sh` | sửa — **CHỈ phần bộ đếm** | hàm `tinh_ca()` dùng chung + chế độ `--tinh-ca` |
| `thu_giao_dien/chay.sh` | sửa — **CHỈ phần symlink/đường dẫn browser** | tự nối `.local-browsers` + `--kiem-browser` |
| `app/thu/thu_g22_demca2.py` | **mới** | fixture chứng minh bộ đếm không đếm sai |
| `docs/Z2_DEMCA_E2E.md` | **mới** | tài liệu này |

**KHÔNG sửa** `app/thu/thu_g22_gioihan.py` và `app/thu/thu_g22_e2e.py` — hai bộ đo thuộc làn khác.
Mọi thay đổi đều **local-first**: không push, không deploy, không gọi API hãng, không chạm CSDL thật.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

| # | Việc | TRƯỚC (đo được) | SAU (đo được) | Bằng chứng |
|---|---|---|---|---|
| 1 | Bộ đếm `chay_tat_ca.sh` | `thu_g22_gioihan.py` **chạy 32 ca** mà bảng ghi **`0 ca`** | **`32 ca`** (vẫn HỎNG, đúng bản chất) | §1.4 · §4 |
| 2 | Đường dẫn Chromium | `thu_g22_e2e.py` **thoát 2**, `"ton_tai": false` | **thoát 0**, binary + sha256 + `thuc_su_spawn` đúng ghim; cả cổng E2E **65 ca ĐẠT** | §2.4 · §4 |
| 3 | Chống tái phát | không có phép đo riêng cho bộ đếm | `thu_g22_demca2.py`: **12 mẫu · 12 KHỚP · EXIT=0** | §3 |

Điểm quan trọng nhất, nói trước: **cả hai lỗi đều là lỗi ĐO, không phải lỗi sản phẩm.**
`thu_g22_gioihan.py` không hề chết — nó chạy 32 ca rồi hỏng 3 ca + khuyết 2 ca; còn Chromium
**có sẵn trên máy** ở ba cây khác, chỉ thiếu đường dẫn trong cây này. Vì thế bản vá **không đổi
một dòng sản phẩm nào**, và **không nới một điều kiện đạt nào** — ngược lại còn siết thêm một vế
(§1.3).

---

## 1. VIỆC 1 — BỘ ĐẾM SAI (32 ca → 0 ca)

### 1.1 Triệu chứng, nguyên văn

`docs/G22_ZERO_CA_DIAG.md` §0, dòng 7 của bảng 12 bộ:

```
| 7 | thu_g22_gioihan.py | 1 | 32 ← KHÔNG phải 0 | ✗ B3.a_bo_goc_tra_ma_khac_0 — C5 ĐỎ LẠI … | KHÔNG CHẾT — lỗi ĐẾM |
```

Chạy trực tiếp bộ thử, dòng cuối là:

```
  TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)
```

Nhưng bảng của `sh app/thu/chay_tat_ca.sh` ghi `thu_g22_gioihan.py  0 ca  HỎNG`. Hai con số
**cùng một lượt chạy**, lệch nhau 32 ca — chênh lệch nằm ở **bộ đếm**, không ở bộ thử.

### 1.2 Nguyên nhân: hai `grep` chỉ biết hai khuôn

Bộ đếm cũ (dòng 99–103) chỉ nhận:

```sh
grep -oE 'Ran [0-9]+'          # unittest
grep -oE '[0-9]+ ca — ĐẠT'     # bộ viết tay, LƯỢT ĐẠT
```

Bộ thử viết tay khi **có ca hỏng/khuyết** lại in `TỔNG: 32 ca — HỎNG (…)` — không khớp khuôn
nào ⇒ `N=0`. Hệ quả không chỉ là một con số sai: nhãn `0 ca` **gộp "chết trước khi chạy ca nào"
với "chạy 32 ca rồi hỏng"** vào cùng một ô, đúng thứ `§12.1 luật 3` cấm (kết luận phải nói đúng
phạm vi đã đo). Người trực đọc `0 ca` thành "bộ chết" sẽ chẩn đoán sai 1/12 bộ.

### 1.3 Bản vá — nhận đúng khuôn, KHÔNG nới điều kiện đạt

Đưa bộ đếm + luật phán vào **một hàm `tinh_ca()`** ở đầu `app/thu/chay_tat_ca.sh`, dùng cho cả
vòng lặp chính lẫn chế độ `--tinh-ca` (bộ tự kiểm §3 gọi đúng hàm này). Thứ tự ưu tiên **giữ
nguyên như cũ**, thêm ba khuôn ở cuối:

| # | Khuôn | Ý nghĩa | Lấy lần |
|---|---|---|---|
| 1 | `Ran N` | unittest | CUỐI |
| 2 | `N ca — ĐẠT` | bộ viết tay, lượt đạt | CUỐI |
| 3 | **`N ca — HỎNG`** | bộ viết tay, lượt hỏng | CUỐI |
| 4 | **`TỔNG: N ca`** | tổng kết tự công bố | CUỐI |
| 5 | **`số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : a/b/c/d/e`** | cổng E2E (`thu_g22_e2e.py`), N = a+b+c+d+e | CUỐI |

Khuôn 5 là **cùng một lớp lỗi, khác khuôn**: sau khi vá Chromium (§2), cổng E2E chạy THẬT nhưng
output của nó không có `Ran`/`N ca — ĐẠT`/`TỔNG:` ⇒ bộ đếm cũ vẫn đọc 0 và còn phán HỎNG oan một
lượt đã thoát 0. Đọc đúng khuôn của nó là **đếm đúng**, không phải nới luật.

Giữ `Ran N` đứng đầu là **có chủ đích**: B5 của `thu_g22_gioihan.py` canh đúng thứ tự "dòng
`Ran` CUỐI phải là số thật" — đổi ưu tiên sẽ làm hỏng phép canh đó.

**Luật phán không bị nới, mà siết thêm một vế.** Ba điều kiện ĐẠT cũ giữ nguyên (mã thoát 0 +
có dấu vết đã chạy + N > 0), và thêm: **dòng CUỐI CÙNG là `ca — HỎNG` ⇒ ĐỎ, kể cả khi thoát 0**.
Nếu không, một bộ vừa tự in "HỎNG" vừa được bảng ghi ✓ — đúng kiểu xanh giả mà cả bộ chạy này canh.

Vế siết này **đã được đo bằng một đối chứng âm đến từ cây thật**, và bản đầu tiên của nó SAI:
đọc "có `ca — HỎNG` ở đâu đó" đã gắn HỎNG oan cho `thu_g22_zeroca.py` — bộ này thoát 0, 17/17 ca
đạt, nhưng docstring của ca 04 trích nguyên văn `TỔNG: 32 ca — HỎNG`, và `unittest -v` in
docstring ra. Vì thế luật được thu hẹp còn **dòng cuối cùng** (sau khi bỏ dòng trống) — dòng phán
quyết của chính bộ thử; chữ HỎNG nằm giữa bài là TRÍCH DẪN. Đo lại sau khi thu hẹp:
`sh app/thu/chay_tat_ca.sh --tinh-ca 0 <log zeroca>` ⇒ `N=17 · PHAN=DAT`. Fixture §3 có thêm ca
`d3` ghim đúng tình huống này, để lần sau không ai "siết" lại kiểu cũ.

Cùng lý do, fixture §3 tự "che khuôn" khi in nguyên văn output mẫu (§3.4) — nếu không, nó sẽ tự
đầu độc phép đo của chính nó.

### 1.4 Bằng chứng TRƯỚC / SAU — trên **cùng một log thật**

Log thật của `thu_g22_gioihan.py` (230 dòng, `EXIT=1`, dòng cuối
`TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)`):

```sh
# BỘ ĐẾM CŨ — đúng hai grep cũ:
$ grep -oE 'Ran [0-9]+'            /tmp/z2_gioihan_out.txt | tail -1   → (rỗng)
$ grep -oE '[0-9]+ ca — ĐẠT'       /tmp/z2_gioihan_out.txt | tail -1   → (rỗng)
  ⇒ N = 0

# BỘ ĐẾM MỚI:
$ sh app/thu/chay_tat_ca.sh --tinh-ca 1 /tmp/z2_gioihan_out.txt
N=32
KHUON=N ca — HỎNG
PHAN=HONG
LY_DO=mã thoát 1
```

Đúng 0 → 32 ca, phán quyết **không đổi** (vẫn HỎNG, vì thoát 1 và có 3 ca hỏng + 2 khuyết).
Đây là điều đề bài yêu cầu: **đếm ĐÚNG hơn, không phải cho xanh**.

Bảng đầy đủ của lượt chạy toàn bộ ở §4.

---

## 2. VIỆC 2 — THIẾU CHROMIUM (exit 2 dù binary CÓ trên máy)

### 2.1 Triệu chứng, nguyên văn

`thu_g22_e2e.py` ghim **cứng** đường dẫn tương đối theo cây (`BIN_CHROMIUM_TUONG_DOI`, dòng 71–73):

```
node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
```

Trên cây này, `node_modules/playwright-core/.local-browsers` **không tồn tại** ⇒ `ghim_chromium()`
trả `ton_tai: false` ⇒ cổng `return MA_NEN` (2) với dòng "KHÔNG có binary Chromium". Đây là
**fail-closed ĐÚNG** (không xanh giả), nhưng là **thiếu nhị phân**, không phải lỗi sản phẩm —
đúng như `docs/QA_G21.md` §4.1 / `N-G21-04` đã đo.

### 2.2 Binary CÓ trên máy — ba kho, cùng một sha256

| Kho `.local-browsers` | `chromium_headless_shell-1194/chrome-mac/headless_shell` | sha256 |
|---|---|---|
| `…/Projects-vip-express-hub/node_modules/playwright-core/.local-browsers` | có | `a9752d88…fa3040` |
| `…/v2-g22-pins/node_modules/playwright-core/.local-browsers` | có | `a9752d88…fa3040` |
| `…/g20-ag02-frontend/node_modules/playwright-core/.local-browsers` | có | `a9752d88…fa3040` |
| `~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers` | có | `a9752d88…fa3040` |

Chỉ `Projects-vip-express-hub` là đường `docs/G22_CONTRACT.md` §544 chỉ định; đó là đường được
chọn. `playwright-core` trong cây là **1.56.1** — đúng bản cần build `1194` (không phải 1148/1243
trong cache hệ thống, và **không** dùng cache hệ thống — §10 G21).

### 2.3 Bản vá — hai đường, cùng một kết quả

`thu_giao_dien/chay.sh` nay **tự chuẩn bị đường dẫn browser** trước khi dựng máy chủ:

1. Nếu `<cây>/node_modules/playwright-core/.local-browsers/…/headless_shell` đã có ⇒ dùng luôn.
2. Nếu chưa: dò theo thứ tự **`VIP_PLAYWRIGHT_KHO`** (biến môi trường) → kho
   `Projects-vip-express-hub` → các worktree anh em → `~/code/veh4-g12-playwright`; kho đầu tiên
   có đúng binary thì **nối symlink** `.local-browsers` vào cây. Symlink hỏng được nối lại;
   thư mục THẬT thiếu binary **không bị xoá** — chuyển sang đường (3).
3. Nếu không tạo được symlink (vd. `node_modules` chỉ-đọc): dùng
   `PLAYWRIGHT_BROWSERS_PATH=<kho>` cho lời gọi Playwright cuối.
4. Không tìm được kho nào: in **đường đã tìm + cách cài**, thoát 2 — **không skip, không lặng lẽ**.

Thêm chế độ `--kiem-browser` (chỉ kiểm đường dẫn, không dựng máy chủ) để đo bản vá trên cây mới
mà không phải chạy cả tầng 3.

Vì `thu_g22_e2e.py` **không đi qua** `chay.sh` cho lượt chạy chính (nó tự dựng nền và tự gọi
`npx playwright test`), bước hạ tầng **symlink trong cây** cũng được làm thật (không chỉ để
`chay.sh` tự vá): đó là đường `ghim_chromium()` đọc.

### 2.4 Bằng chứng

```sh
$ sh thu_giao_dien/chay.sh --kiem-browser        # lượt ĐẦU trên cây chưa có .local-browsers
[giao-dien] ĐÃ NỐI symlink .local-browsers -> …/Projects-vip-express-hub/node_modules/playwright-core/.local-browsers
[giao-dien] Chromium tìm thấy: …/chromium_headless_shell-1194/chrome-mac/headless_shell
[giao-dien] Chromium phiên bản: Chromium 141.0.7390.37
[giao-dien] Chromium sha256: a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040 (KHỚP ghim)
[giao-dien] mã thoát THẬT 0
```

```sh
$ python3 app/thu/thu_g22_e2e.py --ghim-chromium
{
  "ghim": {
    "duong": "…/z2-demca-e2e/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell",
    "ton_tai": true,
    "phien_ban": "Chromium 141.0.7390.37",
    "sha256": "a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040",
    "byte": 146794928,
    "playwright": "1.56.1"
  },
  "thuc_su_spawn": {
    "duong": "…/z2-demca-e2e/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell",
    "phien_ban": "141.0.7390.37",
    "loi": null
  }
}
EXIT=0
```

Hai điều đáng chú ý: `"thuc_su_spawn"` là **hỏi thẳng Playwright binary nó spawn**
(`DEBUG=pw:browser`), không phải suy từ tài liệu — nên đường dẫn này là đường **thật dùng**;
và `sha256` khớp **đúng** ghim `a9752d88…fa3040` mà đề bài đưa.

### 2.5 Không che bằng skip

`chay.sh` **không** bỏ qua khi thiếu binary: nó in đường đã tìm + cách cài rồi `exit 2` (giữ
nguyên hành vi fail-closed). `thu_g22_e2e.py` cũng không bị sửa — nó vẫn `skipTest` hai ca phụ
thuộc Chromium khi thiếu binary, và vẫn `return MA_NEN` khi `ghim_chromium()` không thấy; cái
thay đổi là **đường dẫn có thật** nên hai nhánh đó không còn bị chạm.

---

## 3. VIỆC 3 — FIXTURE `thu_g22_demca2.py` (chống tái phát)

### 3.1 Đo CHÍNH bộ đếm, không đo bản chép

Fixture gọi chế độ thật của bộ chạy:

```sh
sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>
```

Chế độ này gọi **đúng hàm `tinh_ca()`** mà vòng lặp chính dùng (một nguồn duy nhất). Fixture tạo
**bộ thử GIẢ** trong thư mục tạm, chạy chúng bằng `python3`, đưa output + mã thoát thật cho bộ
đếm, rồi so với kỳ vọng. **Không có bản sao thứ hai** của luật đếm để trôi khỏi bản thật.

### 3.2 Bảng 4 nhóm — mỗi nhóm có vế CHÍNH và ĐỐI CHỨNG ÂM

```
nhóm mẫu                            đ.chứng mã    khuôn khớp       N (cũ→mới)  phán       kết quả
a    a1_17ca_viet_tay               dương  0     N ca — ĐẠT          17 → 17    DAT/DAT    ✓
a    a2_doi_chung_am_4ca_unittest   âm     0     Ran [0-9]+           4 → 4     DAT/DAT    ✓
b    b1_khuon_TONG_32ca_HONG        dương  1     N ca — HỎNG          0 → 32    HONG/HONG  ✓
b    b2_doi_chung_am_TONG_0ca       âm     1     N ca — HỎNG          0 → 0     HONG/HONG  ✓
b    b3_khuon_cong_E2E             dương  1     số ca ĐẠT/HỎNG/…     0 → 65    HONG/HONG  ✓
b    b4_doi_chung_am_cong_E2E_0ca  âm     0     số ca ĐẠT/HỎNG/…     0 → 0     HONG/HONG  ✓
c    c1_khong_ca_nao_van_DAT        dương  0     N ca — ĐẠT           0 → 0     HONG/HONG  ✓
c    c2_ran_0_tests_OK              dương  0     Ran [0-9]+           0 → 0     HONG/HONG  ✓
c    c3_doi_chung_am_bo_qua         âm     0     Ran [0-9]+           0 → 0     BO_QUA/BO_QUA ✓
d    d1_thoat_0_van_in_HONG         dương  0     Ran [0-9]+           5 → 5     HONG/HONG  ✓
d    d2_doi_chung_am_thoat_0_DAT    âm     0     Ran [0-9]+           5 → 5     DAT/DAT    ✓
d    d3_doi_chung_am_trich_dan_HONG âm     0     Ran [0-9]+           1 → 1     DAT/DAT    ✓
```

Đối chiếu với 4 điều kiện đề bài:

| Điều | Mẫu chính | Kết quả | Đối chứng âm |
|---|---|---|---|
| (a) in `N ca` đúng ⇒ đếm đúng N | `a1` (17 ca) | 17 · ĐẠT | `a2`: khuôn khác, N khác (4) — bộ đếm không được trả hằng số |
| (b) khuôn lạ ⇒ đếm đúng, không 0 | `b1` (`TỔNG: 32 ca — HỎNG`), `b3` (khuôn cổng E2E 62/1/0/2/0) | **32** và **65** · HỎNG (cũ: 0) | `b2`/`b4`: cùng khuôn, số thật 0 — không bịa số |
| (c) 0 ca thật ⇒ KHÔNG được ĐẠT | `c1` (`0 ca — ĐẠT`), `c2` (`Ran 0` + OK) | 0 · HỎNG | `c3`: bỏ qua có chủ đích vẫn là `BO_QUA` — không gộp vào HỎNG |
| (d) thoát 0 mà in HỎNG ⇒ ĐỎ | `d1` (`OK` + `TỔNG: 5 ca — HỎNG`, rc 0) | 5 · HỎNG | `d2`: cùng hình dạng, ĐẠT thật; `d3`: chữ HỎNG nằm trong TRÍCH DẪN giữa bài — đều không được đỏ oan |

**Vì sao có vế âm:** thiếu nó thì một bộ đếm "luôn trả 0" hoặc "luôn trả HỎNG" cũng qua được bài
kiểm. Vế âm là thứ phân biệt "đếm đúng" với "đoán cho khớp kỳ vọng".

### 3.3 Exit code + nguyên văn bốn mẫu

`python3 app/thu/thu_g22_demca2.py` ⇒ **EXIT=0**, dòng cuối `12 ca — ĐẠT` (để chính bộ chạy chung
đọc được số mẫu đã chạy). Nguyên văn bốn mẫu chính (rút từ output thật):

```
┌ a1_17ca_viet_tay — bộ thử giả thoát 0
│ 17 ca — ĐẠT
└ bộ đếm CŨ: 17 ca · bộ đếm MỚI: 17 ca · phán DAT (N ca — ĐẠT)

┌ b1_khuon_TONG_32ca_HONG — bộ thử giả thoát 1
│   ca ĐẠT=27 · HỎNG=5 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=32
│   TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=5 · KHUYẾT=0)
└ bộ đếm CŨ: 0 ca · bộ đếm MỚI: 32 ca · phán HONG (N ca — HỎNG)

┌ c1_khong_ca_nao_van_DAT — bộ thử giả thoát 0
│ 0 ca — ĐẠT
└ bộ đếm CŨ: 0 ca · bộ đếm MỚI: 0 ca · phán HONG (N ca — ĐẠT)

┌ d1_thoat_0_van_in_HONG — bộ thử giả thoát 0
│ Ran 5 tests in 0.01s
│ OK
│   TỔNG: 5 ca — HỎNG (ĐẠT=4 · HỎNG=1 · KHUYẾT=0)
└ bộ đếm CŨ: 5 ca · bộ đếm MỚI: 5 ca · phán HONG (Ran [0-9]+)
```

Cột **"bộ đếm CŨ"** là bản chép trung thành hai `grep` cũ, chỉ để thấy đúng chỗ 32 ca bị đọc
thành 0 — không phải thứ được kiểm. Mọi phán quyết lấy từ `chay_tat_ca.sh --tinh-ca`.

### 3.4 Fixture tự bảo vệ khỏi chính nó

Fixture **in nguyên văn output mẫu** làm bằng chứng. Nếu in thẳng, chính bộ đếm — khi chạy
fixture như một bộ thử — sẽ đọc câu `32 ca — HỎNG` của **mẫu giả** như phán quyết của **fixture**.
Vì thế fixture có hàm `an()` đổi ` ca — ` thành ` ca ~ ` và `Ran ` thành `Ran· ` **khi in**.
Kiểm lại: output fixture chỉ còn đúng **một** dòng khớp KHUÔN PHÁN QUYẾT (`12 ca — ĐẠT` ở cuối).
Hai dòng bảng có chữ `số ca ĐẠT/HỎNG/…` chỉ là **nhãn khuôn**, không kèm dãy `a/b/c/d/e`, nên
không được đếm. Bộ đếm đọc fixture là **12 ca · ĐẠT** — không phải 65, không phải 32, không phải 0.

Đây cũng là lý do bộ đếm lấy **dòng phán quyết CUỐI** thay vì "có HỎNG ở đâu đó" (§1.3): một bộ
tự kiểm hợp lệ có thể in lại output của bộ khác, và bộ đếm không được bắt nhầm.

### 3.5 ĐỘT BIẾN: fixture có ĐỎ ĐƯỢC không, hay chỉ luôn xanh?

Một fixture luôn xanh thì vô dụng. Đo bằng cách **tái phát đúng lỗi cũ trong một bản sao** của bộ
chạy (chỉ đổi ba khuôn mới thành chuỗi không bao giờ khớp), rồi trỏ fixture vào bản sao ấy qua
`VIP_CHAY_TAT_CA`:

```sh
cp app/thu/chay_tat_ca.sh /tmp/z2_chay_dot_bien.sh
sed -i '' 's/\[0-9\]+ ca — HỎNG/KHONG_KHOP_1/g; s/TỔNG: \[0-9\]+ ca/KHONG_KHOP_2/g; \
           s/số ca +ĐẠT/KHONG_KHOP_3/g' /tmp/z2_chay_dot_bien.sh
VIP_CHAY_TAT_CA=/tmp/z2_chay_dot_bien.sh python3 app/thu/thu_g22_demca2.py
```

Kết quả đo: **EXIT=1**, `TỔNG KẾT: 12 mẫu · 9 KHỚP · 3 LỆCH`, đúng ba chỗ cần bắt:

```
✗ b1_khuon_TONG_32ca_HONG        N đo 0 ≠ chờ 32
✗ b3_khuon_cong_E2E              N đo 0 ≠ chờ 65
✗ d1_thoat_0_van_in_HONG         phán DAT ≠ chờ HONG
KẾT LUẬN: BỘ ĐẾM SAI — 3 mẫu lệch. Đây là lỗi của bộ đếm, không phải của bộ thử.
```

Tức fixture **không phải con dấu cao su**: nó đỏ đúng khi bộ đếm tái phát lỗi `32 ca → 0 ca`
(`b1`), lỗi khuôn cổng E2E (`b3`), VÀ lỗi cho qua một bộ thoát 0 mà tự in HỎNG (`d1` — vì bản
đột biến gỡ luôn vế phán quyết). Chạy với bộ chạy thật thì xanh lại: EXIT=0, 12/12. Biến
`VIP_CHAY_TAT_CA` chỉ dùng cho phép đo đột biến — làn thường không đặt, mặc định luôn là bộ chạy
thật của cây.

---

## 4. CHẠY TOÀN BỘ — TRƯỚC / SAU

**Lượt cuối — cây ĐÓNG BĂNG (HEAD `cb23312` + đúng 4 tệp của làn này), một lệnh:**

```sh
$ sh app/thu/chay_tat_ca.sh
...
  python:   2099 ca · 72 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_nhat_ky_yeu_cau.py
  frontend: 56 + 40 ca (hai tầng tự động)
  E2E:
  bộ hỏng:  thu_g01_g02.py … thu_truy_van.py chay_e2e.sh     ← 21 dòng
  ...
  ✓ vân tay KHÔNG ĐỔI (trước = sau) — con số ghim được vào ĐÚNG cây này
RUNNER_EXIT=1
```

Ba dòng đáng đối chiếu, rút từ chính log đó:

```
  ✓ thu_g22_demca2.py          12 ca
  ✓ thu_g22_e2e.py             65 ca
  ✗ thu_g22_gioihan.py         32 ca  HỎNG (mã thoát 1)
```

| Chỉ số / bộ | TRƯỚC (X1 @ `6949d8c`) | SAU (lượt này @ `cb23312`) | Đọc thế nào |
|---|---|---|---|
| tổng ca Python | 1961 | **2099** | +138; trong đó **+109** là 3 bộ dưới, phần còn lại do nền mới |
| bộ chạy thật | 69 | **72** | +`thu_g22_demca2.py` và các bộ mới của nền `cb23312` |
| bộ đỏ (Python) | 30 | **20** | giảm một phần vì nền mới, KHÔNG phải thành tích của làn này |
| `thu_g22_gioihan.py` | **0 ca** (đọc sai) | **32 ca** · HỎNG | **đúng lỗi X1 — nay đếm đúng, phán quyết KHÔNG đổi** |
| `thu_g22_e2e.py` | **0 ca** · exit 2 | **65 ca** · **ĐẠT** · exit 0 | thiếu Chromium → nay chạy thật cả 65 ca |
| `thu_g22_demca2.py` | — (chưa có) | **12 ca** · ĐẠT | fixture chống tái phát |
| vân tay cây | — | **KHÔNG ĐỔI** (trước = sau) | số đo ghim vào đúng cây `cb23312` |

**CẢNH BÁO so sánh:** `6949d8c` ≠ `cb23312`, nên tổng ca/bộ và số đỏ **không so trực tiếp từng
ô** với X1; chỉ hai ô `g22_gioihan` và `g22_e2e` là so được (cùng lệnh, cùng bộ, cùng khuôn đọc).

**21 dòng đỏ của lượt này — đọc đúng phạm vi, không quy kết oan:**

* **9 bộ 0 ca vì thiếu `VIP_KHO_DANG_CHAY=sqlite`** (`thu_g17_baomat`, `thu_g18_maysrv`,
  `thu_g18_multiprocess`, `thu_g19_gioihan`, `thu_g21_gioihan`, `thu_giao_dich`,
  `thu_han_muc_nguyen_tu`, `thu_header_bao_mat`, `thu_truy_van`) — chốt fail-closed của
  `app/migrate.py`; X1 §3.2 đã đo: khai kho thì cả 9 bộ chạy 17–40 ca. **Ngoài phạm vi làn này.**
* **`thu_bien_driver.py`** — X1 §5.1: `migrate.py` nạp trực tiếp `sqlite3`, vi phạm biên driver.
  Lỗi thật của mã sản phẩm, đã báo AG-00; **không sửa ở đây**.
* **`thu_qa_g21.py` / `thu_qa_g22.py` / `thu_g22_chotcay.py`** — chốt "cây phải đúng cây của nền"
  / "git status ngoài tệp được phép phải RỖNG". 4 tệp của làn Z2 (và tệp của các làn khác) không
  nằm trong danh sách miễn trừ của các bộ đó ⇒ đỏ **theo thiết kế**, không phải lỗi hành vi.
  Đây đúng là loại chốt cần giữ: nó không được nới để tự xanh.
* **`thu_g01_g02.py`**, **`thu_g19_route.py`**, **`thu_g20_dahang.py`**, **`thu_g20_saoluu.py`**,
  **`thu_g21_bimat.py`**, **`thu_g21_saoluu.py`**, **`thu_qa_soat.py`** — đỏ sẵn trên nền
  `cb23312`, ngoài hai việc được giao; **không kết luận gì từ chúng**.
* **`chay_e2e.sh`** (tầng E2E HTTP thật) — hỏng ở lượt này (`E2E:` rỗng), và X1 cũng đã ghi
  `E2E: (rỗng)` + `chay_e2e.sh` trong danh sách đỏ **từ trước** hai bản vá; nó không đi qua mã của
  làn này. Làn Z2 chỉ vá tầng 3 (`thu_g22_e2e.py`), không sửa `chay_e2e.sh`.

Tóm lại: `RUNNER_EXIT=1` là **đúng** — cây này còn 20 bộ Python đỏ vì các lý do trên. Điều làn
này chứng minh chỉ là: **hai chỗ đếm/đường dẫn đã hết sai**, và chúng không làm bộ nào khác đỏ
thêm (vân tay trước = sau, `thu_g22_zeroca.py` từ đỏ-đọc-nhầm thành **✓ 17 ca**).

---

## 5. PHẠM VI ĐÃ ĐO / NGOÀI PHẠM VI

**Đã đo:** bộ đếm (12 mẫu + log thật của `thu_g22_gioihan.py`) · đường dẫn Chromium (sha256 +
phiên bản + binary Playwright thật spawn) · chạy toàn bộ `chay_tat_ca.sh` trên cây này.

**Ngoài phạm vi (không sửa, không kết luận):**

* 9 bộ tự từ chối vì thiếu `VIP_KHO_DANG_CHAY=sqlite` (`thu_g17_baomat`, `thu_g18_maysrv`,
  `thu_g18_multiprocess`, `thu_g19_gioihan`, `thu_g21_gioihan`, `thu_giao_dich`,
  `thu_han_muc_nguyen_tu`, `thu_header_bao_mat`, `thu_truy_van`) — chốt fail-closed của
  `app/migrate.py`, thuộc làn khác (X1 §3.2 đã đo: khai kho thì cả 9 bộ chạy ca).
* `thu_bien_driver.py` đỏ vì `migrate.py` nạp trực tiếp `sqlite3` — lỗi thật của mã sản phẩm,
  X1 §5.1 đã báo AG-00.
* `thu_g22_gioihan.py` đỏ vì 3 ca + 2 khuyết **của chính nó** (C5/G7) — bộ đếm chỉ đọc đúng số,
  không làm nó xanh.
* `thu_qa_g21.py` / `thu_qa_g22.py` / `thu_g22_chotcay.py` đỏ vì chốt "cây phải đúng cây của
  nền" — 4 tệp của làn Z2 không nằm trong danh sách miễn trừ của làn khác; **không được nới chốt
  để tự xanh**.
* `chay_e2e.sh` (tầng E2E HTTP) đỏ sẵn ở lượt này; làn Z2 chỉ vá tầng 3 qua `thu_g22_e2e.py`.
* Tầng 3 Playwright **có** được phủ trong lượt toàn bộ — không qua `thu_giao_dien/chay.sh` (bộ
  chạy đó không được gọi), mà qua `thu_g22_e2e.py`: 65 ca Playwright thật, đọc ở §4. `chay.sh` chỉ
  được đo riêng bằng `--kiem-browser` (§2.4); muốn chạy trọn 7 đặc tả thì vẫn gọi thẳng
  `sh thu_giao_dien/chay.sh`.

---

## 6. TỆP ĐÃ SỬA + CÁCH DỰNG LẠI

```sh
# 1. Bộ đếm — đo log thật
sh app/thu/chay_tat_ca.sh --tinh-ca 1 /tmp/z2_gioihan_out.txt     # N=32 · PHAN=HONG

# 2. Fixture chống tái phát (12 mẫu, có đối chứng âm)
python3 app/thu/thu_g22_demca2.py                                  # EXIT=0 · "12 ca — ĐẠT"

# 3. Đường dẫn Chromium (tự nối symlink nếu cây mới)
sh thu_giao_dien/chay.sh --kiem-browser                            # EXIT=0 · sha256 khớp ghim
python3 app/thu/thu_g22_e2e.py --ghim-chromium                     # EXIT=0 · "ton_tai": true

# 4. Toàn bộ
sh app/thu/chay_tat_ca.sh
```

Symlink hạ tầng (không được git theo dõi — `node_modules/` đã bị `.gitignore` chặn):

```sh
ln -s /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub/node_modules/playwright-core/.local-browsers \
      node_modules/playwright-core/.local-browsers
```

---

## 7. TUÂN THỦ

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | Không lời gọi mạng nào; `chay.sh` bind `127.0.0.1`, cổng thử-trước-dùng | ✓ |
| 2 | Push / deploy / tunnel | 0 lệnh push/ssh/tunnel | ✓ |
| 3 | Sửa CSDL thật | Mọi nền là SQLite trong `mktemp -d`; không chạm `hub.db` | ✓ |
| 4 | Sửa `thu_g22_gioihan.py` / `thu_g22_e2e.py` | `git status` chỉ có 4 tệp trong phạm vi | ✓ |
| 5 | Che bằng skip | `chay.sh` thoát 2 + in cách cài khi thiếu binary; fixture đỏ khi bộ đếm sai | ✓ |
| 6 | Tự bấm duyệt sandbox | Không thao tác duyệt nào | ✓ |
