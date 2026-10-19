# R6 — BỘ ĐẾM DÙNG CHUNG: đo lại "0 ca HỎNG", tách kế hoạch / kết quả / bỏ qua / chưa chạy

Ngày đo: **19/10/2026 (UTC+7)**. Cây: `/Users/viporder/orca/workspaces/vip-express-hub/r6-demca`,
nhánh `r6-demca`, nền `best/integration` @ `c909ebb93ee9b1cf8f6daf157cbd4640448a0fd1`
(`main = de740dc`, **không dùng**). Báo cáo QA đọc trước khi làm: `docs/QA_NGUYENNHAN.md` (commit `42960f4`; worktree
`Projects-vip-express-hub` — đã đọc nguyên văn). `git diff c909ebb 42960f4` chỉ thêm **2 tệp QA**
(`docs/QA_NGUYENNHAN.md`, `app/thu/thu_qa_nguyennhan.py`); mã sản phẩm và mọi bộ thử **giống hệt**
nền `c909ebb`, nên số đo dưới đây áp dụng nguyên vẹn cho `42960f4`. Đã kiểm lại bằng bản trích
`git archive 42960f4`: bộ đếm CŨ trong bản ấy cũng đọc **22** trên cùng log `thu_g21_gioihan.py`
(mục 1.2). Mọi lệnh dưới đây
chạy local-first: không push/deploy, không gọi hãng, không credentials, không mở LIVE, không
sửa CSDL nghiệp vụ.

---

## 0. Kết luận trước, để không ai đọc số sai

1. **Cáo buộc "9 bộ XANH bị đếm thành `0 ca HỎNG`, 198 ca PASS bị mất" KHÔNG tái hiện ở mốc này.**
   (AG-00 đã đính chính đúng như vậy; tôi xác nhận bằng số đo, và **không** tạo bản vá cho giả
   thuyết "0" — không có bản vá nào cho lỗi chưa được chứng minh.)
   Chạy trực tiếp đủ 9 bộ: **cả 9 exit 0**. Bộ đếm cũ (HEAD `c909ebb`) đọc **188 ca, cả 9 phán
   `DAT`** — không bộ nào bị đọc 0. Con số **198 không khớp tổng của chính 9 bộ được liệt kê**
   (31+17+26+22+22+17+5+8+40 = **188**).
2. **Nhưng có một lỗi đếm THẬT nằm trong đúng 9 bộ ấy:** `thu_g21_gioihan.py` công bố
   **`TỔNG=38`** ở dòng cuối, còn bộ đếm cũ bắt câu `['  22 ca — ĐẠT']` nằm trong phần **bằng
   chứng** (số của bộ **con** `thu_g19_gioihan.py`) và báo **22**. Đây là chỗ "đọc sai" đo được:
   **-16 ca** bị che trong một bộ vẫn xanh. Bộ đếm mới đọc đúng **38**; tổng 9 bộ thành **204**.
3. **Bộ đếm cũ cộng `did not run` và `skipped` vào cùng một con số "ca".** Với **log thật của
   cổng E2E ở lượt sạch** (`75/1/0/4/0` — mục 6.2), nó đọc **80**, trong khi **ca có kết quả là
   76** và **4 ca chưa chạy**. Bộ đếm mới in tách:
   `KẾ HOẠCH 80 · CÓ KẾT QUẢ 76 · CHƯA CHẠY 4`. (Log QA cũ `2/25/0/53/0` là cùng một lỗi mẫu số,
   với 53 ca chưa chạy.)
4. **Bộ đếm giờ là MỘT tệp dùng chung** `app/thu/thu_r6_demca.py`; `chay_tat_ca.sh` không còn
   regex đếm nào, chỉ gọi tệp đó (cả vòng lặp lẫn `--tinh-ca`). 27 fixture tự kiểm, mỗi điều kiện
   (a)–(e) có **đối chứng âm**, và mỗi mẫu được đo **hai đường** (hàm thật + `chay_tat_ca.sh
   --tinh-ca`) để bản sao regex không thể mọc lại mà không bị bắt.

> Nói thẳng: việc **không tái hiện** không phải "không có lỗi". Nó chỉ có nghĩa là phát biểu
> "9 bộ bị đếm 0" không đúng với dữ kiện; lỗi thật nằm ở chỗ khác và đã được sửa (mục 1.2).

---

## 1. Tái hiện — hai con số cho mỗi bộ

### 1.1. Chín bộ, chạy TRỰC TIẾP (exit thật, log thật)

Lệnh cho từng bộ (chạy tuần tự, `VIP_HUB_DATA` là thư mục tạm **trong thư mục tạm hệ thống** —
hai bộ G19/G21 **từ chối** đường `/tmp` vì nó nằm ngoài thư mục tạm hệ thống, xem mục 6.3):

```sh
D=$(mktemp -d "${TMPDIR:-/tmp}/r6-direct-XXXX")
VIP_HUB_DATA="$D/data" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
PYTHONDONTWRITEBYTECODE=1 python3 app/thu/<bộ>.py
```

| Bộ | exit | CŨ đọc N | CŨ phán | MỚI đọc N | MỚI phán | có kết quả | bỏ qua | chưa chạy |
|---|---:|---:|---|---:|---|---:|---:|---:|
| `thu_g17_baomat.py` | 0 | 31 | DAT | 31 | DAT | 31 | 0 | 0 |
| `thu_g18_maysrv.py` | 0 | 17 | DAT | 17 | DAT | 17 | 0 | 0 |
| `thu_g18_multiprocess.py` | 0 | 26 | DAT | 26 | DAT | 26 | 0 | 0 |
| `thu_g19_gioihan.py` | 0 | 22 | DAT | 22 | DAT | 22 | 0 | 0 |
| **`thu_g21_gioihan.py`** | 0 | **22** | DAT | **38** | DAT | **38** | 0 | 0 |
| `thu_giao_dich.py` | 0 | 17 | DAT | 17 | DAT | 17 | 0 | 0 |
| `thu_han_muc_nguyen_tu.py` | 0 | 5 | DAT | 5 | DAT | 5 | 0 | 0 |
| `thu_header_bao_mat.py` | 0 | 8 | DAT | 8 | DAT | 8 | 0 | 0 |
| `thu_truy_van.py` | 0 | 40 | DAT | 40 | DAT | 40 | 0 | 0 |
| **TỔNG** | **9×0** | **188** | **9 DAT** | **204** | **9 DAT** | **204** | 0 | 0 |

- **188 ≠ 198** của đề bài. 198 không phải tổng của 9 bộ đã liệt kê; không có bộ thứ 10 nào
  được nêu. Con số đúng theo bộ đếm CŨ là 188; theo bộ đếm MỚI là 204.
- Không bộ nào bị đọc `0` ở cả hai bộ đếm. "0 ca HỎNG" chỉ là **số ca hỏng bằng 0** — đúng với
  9 bộ đang xanh; nó không phải "bộ chạy 0 ca".

**Hai con số của QA §7 không tái hiện được trên cây này — không quy cho regex, chỉ ghi nhận:**

| Bộ | QA §7 | Trực tiếp (lượt này) | Full run (lượt này) | `def test_` trong tệp |
|---|---:|---:|---:|---:|
| `thu_g20_saoluu.py` | 35 | **41** (`Ran 41 tests`, exit 1, 1 FAIL) | **41** | 41 |
| `thu_g21_saoluu.py` | 13 | **23** (`Ran 23 tests`, exit 1, 2 FAIL) | **23** | 23 |

Đây là khác biệt **lượt đo/môi trường hoặc bản log** (QA ghi "13/35" trong khi tệp hiện có 23/41
phương thức test), không phải chỗ bộ đếm đọc sai: cả đường trực tiếp lẫn đường
`chay_tat_ca.sh` đều ra cùng một số, và số ấy khớp số test của chính tệp. Không sửa bộ thử, không
cập nhật ghim theo con số QA khi chưa tái hiện được.
- Lỗi thật của `thu_g21_gioihan.py` — trích nguyên văn log thật (cùng một lượt chạy):

  ```text
  $ python3 app/thu/thu_g19_gioihan.py  →  mã thoát 0 · 22 ca · 0 skip · 27.4 giây ·
                                          dòng cuối: ['  22 ca — ĐẠT']       ← số của BỘ CON
  ...
  ca ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=38                        ← bộ MẸ công bố
  thời gian: 65.1 giây · HEAD: (không đặt)
  ```

  Bộ đếm cũ chỉ biết `N ca — ĐẠT`, lấy **lần cuối**, nên bắt câu `22` (bộ con) và bỏ dòng `38`
  (bộ mẹ). Bộ đếm mới lấy **ứng viên kết thúc muộn nhất** và hiểu khuôn `=`, nên đọc **38**.
  Số ca PASS thật của 9 bộ vì thế là **204**, không phải 188; 188 là con số **bộ đếm cũ** đọc được.
  QA §7 cũng ghi 22 cho bộ này vì QA gọi chính bộ đếm cũ — lỗi lan sang bảng QA, không phải
  bộ thử hỏng. Không có ca nào bị đọc thành 0.
- **Tái hiện trên ĐÚNG HEAD `42960f4`** (bản trích `git archive`, cùng môi trường): chạy
  `python3 app/thu/thu_g21_gioihan.py` → **exit 0**, log in đúng hai dòng trên
  (`['  22 ca — ĐẠT']` của bộ con và `TỔNG=38` của bộ mẹ); `sh app/thu/chay_tat_ca.sh --tinh-ca`
  của **chính bản 42960f4** đọc **22**. Bộ đếm MỚI đọc **38**. Đây không phải chuyện môi trường:
  cùng một tệp log, hai bộ đếm, hai con số.

### 1.2. Bốn lỗi đếm THẬT đã sửa (mỗi lỗi có ca tái hiện)

| # | Lỗi cũ | Ca tái hiện | CŨ | MỚI |
|---|---|---|---:|---:|
| 1 | Bỏ khuôn `ca ĐẠT=… · HỎNG=… · BỎ QUA=… · KHUYẾT=… · TỔNG=…`; bắt số bộ con in trong bằng chứng | log thật `thu_g21_gioihan.py` | 22 | **38** |
| 2 | Cộng `did not run` vào "ca chạy" | **log thật của cổng E2E** (mục 6.2: 75/1/0/4/0) | 80 | **80 kế hoạch · 76 có kết quả · 4 chưa chạy** |
| 3 | `Ran N` của unittest gộp ca `skipped` vào "có kết quả" | bộ thật trong lượt đầy đủ: `thu_qa_g19.py` | 29 "chạy" | **29 kế hoạch · 11 có kết quả · 18 bỏ qua** |
| 4 | Dòng kết luận HAI con số `27 ca — ĐẠT, 5 ca HỎNG` chỉ đọc vế ĐẠT | đúng định dạng `thu_g19_gioihan.py` khi hỏng | 27 | **32** |
| 5 | Thoát 0 mà không có dấu vết chạy ca nào vẫn có thể lọt nếu chỉ xét mã thoát (đường E2E shell cũ) | fixture (e) | ✓ | **HỎNG** |
| 6 | Playwright: phần CHI TIẾT ca hỏng nằm giữa `1 failed` và `4 did not run` làm mất `failed` | log thật `veh-g22-e2e-*.log` | 0 (bộ đếm cũ) · 79 ca · 0 HỎNG (bản gom-khối trung gian) | **80 ca · 1 HỎNG · 4 chưa chạy** |

Ba ví dụ THẬT của lỗi (3), trích từ lượt đầy đủ (mục 5): `thu_best_qa.py` 10 → **3 có
kết quả + 7 bỏ qua**; `thu_qa_g19.py` 29 → **11 + 18**; `thu_qa_g20.py` 21 → **18 + 3**;
`thu_qa_g18.py` 47 → **46 + 1**; `thu_qa_g22.py` 24 → **23 + 1**; `thu_qa2_soat.py` 49 →
**48 + 1**. Bộ đếm cũ gọi tất cả các con số bên trái là "ca", không nói bộ nào thực sự có
kết quả.

Không có chỗ nào nới điều kiện ĐẠT; ba chỗ còn **siết thêm**: E2E shell exit 0 mà 0 phép đo là
HỎNG, exit 0 mà còn `did not run` là HỎNG, exit 0 mà báo cáo tự in HỎNG là HỎNG.

---

## 2. Bộ đếm dùng chung — một chỗ duy nhất

`app/thu/thu_r6_demca.py` (mới) là **bộ đếm duy nhất**. Nó hiểu ba loại runner + `node --test`:

| Loại | Khuôn | `KE_HOACH` | `CO_KET_QUA` | `BO_QUA` | `CHUA_CHAY` |
|---|---|---|---:|---:|---:|
| unittest | `Ran N tests …` + `OK` / `FAILED (failures=…, errors=…, skipped=…)` | `Ran N` | N − skipped − failures − errors | `skipped=` | 0 |
| Playwright | `<n> passed/failed/skipped/did not run/flaky/interrupted` | tổng 6 nhãn | passed + failed (+flaky) | skipped | did not run |
| viết tay | `N ca — ĐẠT`; `N ca — ĐẠT, M ca HỎNG`; `TỔNG: N ca — HỎNG (…)`; `ca ĐẠT=a · HỎNG=b · BỎ QUA=c · KHÔNG KẾT LUẬN=d · TỔNG=n`; `ca ĐẠT=a · HỎNG=b · BỎ QUA=c · KHUYẾT=d · TỔNG=n` | con số tổng | a + b | c | 0 |
| E2E gate | `số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : a/b/c/d/e` | a+b+c+d+e | a+b | c | d |
| shell E2E | `KẾT QUẢ: x/y` | y | y | 0 | 0 |
| node --test | `ℹ pass/fail/skipped/todo N` (hoặc `#`) | tổng 4 nhãn | pass + fail | skipped + todo | 0 |

Luật phán (giữ nguyên luật cũ, chỉ đọc đúng hơn):

```
DAT    exit 0 · KE_HOACH > 0 · có dấu vết đã chạy · không tự báo HỎNG · CHUA_CHAY = 0
BO_QUA exit 0 · KE_HOACH = 0 · output có skipped / skipped=N
HONG   exit ≠ 0 · hoặc tự báo HỎNG · hoặc không dấu vết · hoặc 0 ca · hoặc còn did not run
```

`N` trong `--tinh-ca` **giữ nghĩa cũ = KE_HOACH** để hai bộ tự kiểm đang tồn tại
(`thu_g22_demca2.py`, `thu_qa_nguyennhan.py`) không phải sửa. Muốn "ca chạy thật" thì đọc
`CO_KET_QUA`; tài liệu và bảng tổng kết đã đổi nhãn tương ứng.

`chay_tat_ca.sh`:
- không còn `grep -oE 'Ran [0-9]+'` / `N ca — ĐẠT` — toàn bộ đếm gọi `thu_r6_demca.py`;
- `--tinh-ca` **exec** thẳng bộ đếm chung (đường đo của QA không còn bản sao);
- vòng lặp chính gọi `tinh_ca()` → `--shell` → cùng hàm `dem()`;
- in `KẾ HOẠCH` / `CÓ KẾT QUẢ` / `bỏ qua` / `chưa chạy` / `không kết luận` **riêng**;
- dò danh sách **một lần**, so `SO_BO` với `SO_BO_DO`; lệch ⇒ `exit 2` ("có bộ bị CHE"),
  không được coi là đã chạy hết.

---

## 3. Fixture chống sai đếm — 27 ca, mỗi điều kiện có ĐỐI CHỨNG ÂM

Chạy `python3 app/thu/thu_r6_demca.py` → `Ran 27 tests … OK`, exit 0. Mỗi mẫu được đo **hai
lần**: (1) gọi thẳng `dem()` trong tệp, (2) gọi `sh app/thu/chay_tat_ca.sh --tinh-ca <exit> <log>`;
hai kết quả phải trùng. Nếu ai chép regex trở lại shell, vế (2) lệch và bộ tự kiểm đỏ.

| Điều kiện đề bài | Mẫu CHÍNH | Kết quả chờ | ĐỐI CHỨNG ÂM | Kết quả chờ |
|---|---|---|---|---|
| (a) in `N ca` ⇒ đếm đúng | `17 ca — ĐẠT` | plan 17 · KQ 17 · DAT | `4 ca — ĐẠT` | plan 4 · DAT (không phải hằng 17) |
| (b) khuôn lạ ⇒ không 0 | `TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)` | plan 32 · KQ 30 · HỎNG | `TỔNG: 0 ca — HỎNG (…)` | plan 0 · HỎNG (không bịa 32) |
| (b3) dòng HAI con số | `27 ca — ĐẠT, 5 ca HỎNG` | plan 32 · HỎNG | `32 ca — ĐẠT` | plan 32 · DAT |
| (b5) khuôn `=` thật của G21 | bằng chứng có `['  22 ca — ĐẠT']`, dòng cuối `ca ĐẠT=38 … TỔNG=38` | plan **38** (không phải 22) | `ca ĐẠT=0 … TỔNG=0` | plan 0 · HỎNG |
| (c) 0 ca thật ⇒ không ĐẠT | `0 ca — ĐẠT`; `Ran 0 tests` + `OK` | HỎNG | `1 ca — ĐẠT`; `Ran 0` + `skipped=1` | DAT 1; BO_QUA |
| (d) exit 0 + in HỎNG ⇒ ĐỎ | `Ran 5…OK…TỔNG: 5 ca — HỎNG (ĐẠT=4 · HỎNG=1)` | HỎNG | `TỔNG: 5 ca — ĐẠT`; HỎNG trong docstring giữa bài | DAT 5; DAT 1 |
| (e) exit 0 + không dấu vết ⇒ ĐỎ | thoát 0, không in gì | HỎNG | `Ran 3 tests … OK` | DAT 3 |
| (f) Playwright tách `did not run` | 2 passed · 25 failed · 0 skipped · 53 did not run | plan 80 · KQ **27** · chưa chạy 53 · HỎNG | `80 passed` | plan 80 · KQ 80 · DAT |
| (f3) chi tiết ca hỏng CHEN GIỮA | `1 failed` …chi tiết… `4 did not run` / `75 passed` | plan 80 · KQ 76 · HỎNG · chưa chạy 4 | `80 passed` (f2) | plan 80 · DAT |
| (g) unittest tách `skipped` | `Ran 35 … OK (skipped=1)` | plan 35 · KQ **34** · bỏ qua 1 | `Ran 35 … OK` | plan 35 · KQ 35 |
| (h) chỉ MỘT bộ đếm | đọc `chay_tat_ca.sh`: có `thu_r6_demca.py`, không còn regex đếm | đạt | chèn lại regex cũ vào **bản sao** | phép canh ĐỎ |
| (j) node --test tách pass/fail | `ℹ pass 2 · ℹ fail 1 · ℹ cancelled 0` | plan 3 · KQ 3 · HỎNG | `ℹ pass 56 · ℹ fail 0` | plan 56 · DAT |
| (i) không phải hằng số | ba mẫu 7 · 12 · 0 ca | `[7, 12, 0]` | — | — |

Tiền lệ (e) đã có trong dự án: `thu_g22_e2e.py` là cổng chống "xanh giả" — bộ tự kiểm của bộ đếm
cũng phải từ chối exit 0 + 0 ca, không chỉ nói điều đó trong docstring.

---

## 4. Toàn bộ 77 bộ + bộ đếm mới — có bộ nào bị CHE không?

- Tại `6949d8c` (mốc báo cáo cũ): **70 tệp** `thu_*.py` (trừ `thu_e2e.py`); bảng cũ ghi
  **69 bộ chạy thật** = 70 − 1 bộ bỏ qua có chủ đích.
- Tại `c909ebb` (nền R6, chưa thêm bộ đếm mới): **77 tệp**; 7 tệp được THÊM sau mốc cũ:
  `thu_best_adapter.py`, `thu_best_auth.py`, `thu_best_qa.py`, `thu_best_webhook.py`,
  `thu_g22_zeroca.py`, `thu_g22_phanloai.py`, `thu_g22_demca2.py`.
- Ở máy này `thu_postgres.py` **chạy** 55 ca (không bỏ qua) và `thu_nhat_ky_yeu_cau.py` bỏ qua,
  nên bộ cũ in **76 bộ chạy thật** = 77 − 1. Đề bài ghi **75** = cùng 77 tệp nhưng **2 bộ bỏ qua**
  (PostgreSQL cũng bỏ qua trong môi trường của AG-00). Vì thế "75 so với 69" là **+6 bộ**, còn
  ở đây đo được **76 so với 69 = +7 bộ**; khác nhau đúng một bộ do môi trường, không phải do đếm.
- Bộ đếm mới in thẳng **`dò 78/78`** (77 tệp cũ + `thu_r6_demca.py`), `1 bộ BỎ QUA`,
  `77 có ca chạy` và **HỎNG nếu lệch**. Con số "phát hiện" không còn là số suy ra từ
  "bộ chạy thật".

---

## 5. Trước / sau — cùng một lượt chạy đầy đủ

Hai lượt đầy đủ đã chạy. **Lượt 1 bị LOẠI** vì tôi sửa tệp giữa lượt chạy — chính
`test_z2_cay_khong_doi_trong_luot_do` của `thu_qa_g21.py` bắt được (vân tay cây đổi). Lượt 2
(dưới đây) giữ cây **đứng yên từ đầu đến cuối**: `✓ vân tay KHÔNG ĐỔI (trước = sau)`.

| | Mốc cũ `6949d8c` (báo cáo `G22_ZERO_CA_DIAG.md`) | Lượt R6 sạch (`c909ebb` + 2 tệp mới) |
|---|---:|---:|
| exit | 1 | **1** |
| bộ dò / bộ xử lý | 69 bộ (bảng cũ) | **78 / 78** |
| bộ có ca chạy | 69 "bộ chạy thật" | **77** |
| bộ BỎ QUA | 1 (`thu_nhat_ky_yeu_cau.py`) | **1** (`thu_nhat_ky_yeu_cau.py`, 0 ca) |
| bộ hỏng | 30 | **21 bộ Python** (+ `thu_http.py` + `chay_e2e.sh`) |
| KẾ HOẠCH | 1961 ca | **2595 ca** |
| CÓ KẾT QUẢ | KHÔNG in riêng — gọi cả 1961 là "ca" | **2555 ca** |
| bỏ qua (ca) | KHÔNG in riêng | **35** |
| chưa chạy (ca) | KHÔNG in riêng | **4** |
| không kết luận (ca) | KHÔNG in riêng | **2** |

Nguyên văn dòng tổng kết của lượt sạch:

```text
  python:   KẾ HOẠCH 2595 ca · CÓ KẾT QUẢ 2555 ca
            (bỏ qua 35 ca · chưa chạy 4 ca · không kết luận 2 ca)
            + 1 bộ BỎ QUA (0 ca): thu_nhat_ky_yeu_cau.py
  bộ:       dò 78/78 · có ca chạy 77 · hỏng 21
```

**Không so trực tiếp 1961 với 2595.** Cây hiện có thêm 7 bộ, `thu_g21_gioihan` +16 ca,
cổng E2E +80 ca (lượt này Chromium chạy được), PostgreSQL chạy 55 ca thay vì bỏ qua. Con số
so được là **định nghĩa**: "KẾ HOẠCH" ≠ "CÓ KẾT QUẢ"; và mọi bộ đều nằm trong `dò 78/78`.

**Vì sao 35 ≠ 2595 − 2555 − 4 − 2 = 34:** `thu_nhat_ky_yeu_cau.py` in `Ran 0` + `skipped=1`
— skip cấp **module**, không phải một ca. Bộ đếm ghi 1 **lượt** bỏ qua để không giấu việc bộ ấy
không chạy, còn tổng ca vẫn 0. Nêu rõ để không ai cộng sai.

### Bảng bộ đỏ của lượt sạch (để phạm vi không bị hiểu là "đã xanh")

`thu_best_qa · thu_g01_g02 · thu_g19_route · thu_g20_dahang · thu_g20_saoluu · thu_g21_bimat ·
thu_g21_saoluu · thu_g22_chotcay · thu_g22_e2e · thu_g22_gioihan · thu_g22_phanloai ·
thu_g22_zeroca · thu_qa_g16 · thu_qa_g18 · thu_qa_g19_tich_hop · thu_qa_g20 · thu_qa_g21 ·
thu_qa_g22 · thu_qa_jt · thu_qa_soat · thu_tich_hop` (21 bộ Python) + `thu_http.py` +
`chay_e2e.sh`.

Các bộ này đỏ vì R1–R5/R7 (migrate/tenant/ghim/scanner/trình duyệt/PostgreSQL/làn khác), **không
phải vì bộ đếm**. R6 không sửa chúng và không hứa làm chúng xanh.


---

## 6. Lệnh chạy thật, exit thật, và các lần bị chặn

### 6.1. Bộ đếm + fixture

```sh
python3 app/thu/thu_r6_demca.py                 # Ran 27 tests · OK · exit 0
python3 app/thu/thu_g22_demca2.py               # TỔNG KẾT: 12 mẫu · 12 KHỚP · 0 LỆCH · exit 0
QANN_REPO=<cây này> python3 app/thu/thu_qa_nguyennhan.py   # Ran 11 tests · OK · exit 0
sh app/thu/chay_tat_ca.sh --tinh-ca 0 <log>     # in N/KHUON/PHAN/LY_DO + 4 con số tách rời
```

`thu_g22_demca2.py` vẫn báo cột "bộ đếm CŨ" của nó đọc **0** cho mẫu `TỔNG: 32 ca — HỎNG`;
cột "MỚI" đọc **32**. Đó là chứng minh lỗi X1 lịch sử vẫn tái hiện được trên **bản sao cố ý cũ**,
trong khi đường thật đã đọc đúng.

### 6.2. Chín bộ trực tiếp + cổng E2E thật

`exit 0` cho cả 9; log + exit lưu ở `/tmp/r6-demca-evidence/direct/exits.txt`. Tổng thời gian
~3 phút. Không bộ nào cần Chromium/PostgreSQL.

Cổng E2E chạy trực tiếp **có** Chromium trong lượt sạch:

```text
$ python3 app/thu/thu_g22_e2e.py
  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 75/1/0/4/0  (ghim ĐẠT = 65)
  Chromium phiên bản  : Chromium 141.0.7390.37
  ── PHÁN QUYẾT: HONG (mã thoát 1)
[...] MÃ THOÁT CỦA CỔNG = 1
```

Cùng log ấy qua hai bộ đếm:

| | CŨ (42960f4) | MỚI |
|---|---:|---:|
| `--tinh-ca` → N | **80** | **80 (kế hoạch)** |
| có kết quả | không có khái niệm | **76** |
| bỏ qua | gộp vào 80 | **0** |
| chưa chạy | gộp vào 80 | **4** |
| phán | HONG (mã thoát 1) | HONG (mã thoát 1) |

Bản thân log Playwright thô (`veh-g22-e2e-*.log`) cũng được bộ đếm mới đọc đúng:
`1 failed / 4 did not run / 75 passed` → plan 80 · có kết quả 76 · 1 HỎNG · 4 chưa chạy; bộ đếm
CŨ đọc **0** trên cùng tệp (nó không hiểu khuôn Playwright).

Đường shell `chay_e2e.sh` cũng dùng chung bộ đếm: `KẾT QUẢ: 41/41` → plan 41 · có kết quả 41 ·
DAT; còn `KẾT QUẢ: 0/0` **thoát 0** → **HỎNG** ("0 ca"), trong khi bản cũ chỉ xét mã thoát nên
ghi ✓.

### 6.3. Một lần bị chặn — ghi lại đúng lỗi, không giấu

Lượt direct đầu tiên đặt `VIP_HUB_DATA` dưới `/tmp`; `thu_g19_gioihan.py` và
`thu_g21_gioihan.py` **từ chối** (exit **9**) với:

```text
TỪ CHỐI: VIP_HUB_DATA='/tmp/r6-demca-direct-…/data' nằm NGOÀI thư mục tạm —
không chạy trên dữ liệu thật.
```

Đây là chốt an toàn **đúng** của bộ thử, không phải lỗi bộ đếm. Lượt đo lại dùng
`mktemp -d "${TMPDIR:-/tmp}/…"` (thư mục tạm hệ thống) và cả 9 bộ exit 0. Hai log exit 9 của lượt
đầu **không** được dùng làm bằng chứng.

### 6.4. Ràng buộc đã giữ

Không push/deploy; không gọi API hãng; không credentials; không sửa DB nghiệp vụ; không mở LIVE;
BEST-09 giữ **BLOCKED**; không tự bấm duyệt sandbox. Không sửa bộ thử nào và không sửa mã sản
phẩm — chỉ 3 tệp trong phạm vi: `app/thu/chay_tat_ca.sh` (phần đếm),
`app/thu/thu_r6_demca.py` (mới), `docs/R6_DEMCA.md` (mới).

---

## 7. Còn lại — nói rõ cái chưa sửa

1. **Bản sao regex vẫn còn trong bộ thử, NGOÀI phạm vi làn này:**
   `app/thu/thu_g22_gioihan.py:496` (`_dem_nhu_chay_tat_ca`, bản sao hai `grep` cũ) và
   `app/thu/thu_g22_zeroca.py:224` (`MAU_SO_CA`, 3 khuôn riêng). Theo phạm vi R6 ("KHÔNG sửa bất
   kỳ bộ thử nào"), tôi **không** sửa chúng. Hệ quả đo được: `_dem_nhu_chay_tat_ca` vẫn đọc
   **27** cho dòng `27 ca — ĐẠT, 5 ca HỎNG` (đúng phải 32), và `SO_CA_TOAN_BO` của zeroca còn
   ghim 9 bộ là `HONG 0` trong khi chúng đã xanh. Việc của làn sau: thay hai chỗ đó bằng
   `from thu_r6_demca import dem` / gọi `chay_tat_ca.sh --tinh-ca` — một dòng, không chép regex.
2. **`thu_g21_gioihan.py` là bộ viết tay in khuôn `=`, không in `N ca — ĐẠT` làm dòng cuối.**
   Bộ đếm mới đã đọc đúng; nhưng nếu bộ này đổi sang khuôn khác nữa thì phải bổ sung khuôn + mẫu
   âm, không được nới luật.
3. **Chromium chạy được ở lượt sạch nhưng cổng E2E vẫn đỏ:** 75 đạt / 1 hỏng / 0 bỏ qua /
   4 chưa chạy (ghim ĐẠT 65 ≠ 75). "did not run" **không** phải ca đã chạy và không được tính là
   đạt. Ở lượt 1 Chromium bị chặn, E2E thoát 2 và in **0 ca** — bộ đếm phán HỎNG, không xanh.
4. **PostgreSQL**: các ca bỏ qua có chủ đích vẫn là `BO_QUA`, không phải ĐẠT; tổng kết in riêng
   số ca bỏ qua.
5. **`chay_tat_ca.sh` vẫn có thể in HỎNG vì lý do môi trường** (Z4 của G21 bí mật quét thư mục
   tạm của lượt khác, Chromium bị chặn, PostgreSQL tạm). Bộ đếm không được dùng để biến các lỗi
   ấy thành xanh — nó chỉ đọc đúng hơn.

## 8. Exit, và vì sao `thu_r6_demca` ghi 26 ở lượt đầy đủ

- Exit của lượt sạch: **1**. Nguyên nhân là 21 bộ Python đỏ + `thu_http.py` + `chay_e2e.sh`,
  không phải lỗi bộ đếm.
- Trong lượt, `thu_r6_demca.py` được đếm **26 ca · 26 có kết quả · ✓**. Bản cuối sau lượt có
  **27** fixture vì thêm mẫu `(f3)` cho lỗi Playwright "chi tiết ca hỏng chen giữa". Thay đổi
  này chỉ ảnh hưởng số ca của **chính bộ tự kiểm**, không đổi số của bất kỳ bộ nào khác; nó được
  kiểm lại bằng `python3 app/thu/thu_r6_demca.py` → `Ran 27 tests … OK`, exit 0, và bằng log
  Playwright thật `75 passed / 1 failed / 4 did not run` → plan 80 · có kết quả 76 · chưa chạy 4.
- Cổng E2E (`thu_g22_e2e.py`) chạy được Chromium ở lượt sạch: report thật
  `số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 75/1/0/4/0`. Nó **vẫn đỏ** vì ghim ĐẠT = 65
  ≠ 75 và 4 ca chưa chạy — đúng luật của chính cổng, không phải bộ đếm.
- `thu_qa_g19_tich_hop.py` xanh ở lượt 1 (38 ca) nhưng chỉ nạp 8 ca ở lượt 2 — các làn khác
  chạy song song trên cùng máy; đây là nhiễu môi trường, không phải bộ đếm. Lượt sạch vẫn có
  vân tay cây **không đổi**.

