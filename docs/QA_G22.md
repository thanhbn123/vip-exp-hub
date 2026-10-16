# NGHIỆM THU G22 — AG-01 (QA/VERIFIER) · BASELINE ĐỘC LẬP TRÊN `7344c02` + KẾ HOẠCH CÓ CỔNG FAIL

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_6b5a1611cd28` · **Dispatch:** `ctx_dfc5af670515`
**Nền đo:** `7344c020abad562dafb593c4234d5e1f9ecfd18c` — cây `8fc624deb0330dc8846a3337bf9a76fc90e253b0`
**KHÔNG** dùng `main` (`de740dc`) — `main` **không** chứa G13–G22.
**Hai tệp AG-01 G22 được phép tạo:** `docs/QA_G22.md` (tài liệu này) · `app/thu/thu_qa_g22.py`
(bộ kiểm, **22 ca**, `sha256 1040d92bb04b1c2e6d24e00bb38d678add6946424cb11cec1c4bbc06992c71a7`).

> **Vì sao ghim SHA của BỘ KIỂM mà không phải của tài liệu này:** một tệp **không tự ghi được SHA của
> chính nó** (`BAN_GIAO.md` §7.3). Mọi con số ở §0–§6 đều đo bằng **đúng bản `1040d92b…`** đó; nhật
> ký thô của lượt chạy cuối: `qa_g22_bo_kiem_cuoi.log`,
> `sha256 cead6078a2f74aa358e139af16605cff3fcf6478e59dc97bd92ac4031e39da2e`.
Tôi **không sửa một dòng mã sản phẩm nào** — §8 chứng minh bằng `git status` + `git write-tree`.

**Lệnh chạy bộ kiểm của tôi:**

```sh
python3 app/thu/thu_qa_g22.py                       # làn MẶC ĐỊNH — đo, in bảng, KHÔNG tự cho qua
VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py    # NGHIỆM THU BẢN ĐÃ GỘP: nợ còn ⇒ ĐỎ
VIP_G22_DAY_DU=1 python3 app/thu/thu_qa_g22.py      # + chạy lại `chay_tat_ca.sh` (11 phút)
```

**Lượt chạy cuối của bộ kiểm (số của MỌI khẳng định dưới đây sinh ra từ đây):**

```sh
$ cd "$CP" && python3 app/thu/thu_qa_g22.py
# === EXIT CODE THAT = 1
# Ran 22 tests in 123.644s · FAILED (failures=1, skipped=1)
#   [A2] `status --porcelain -uall`: 2 đường = 2 tệp được phép + 0 delta HEAD↔nền + 0 NGOÀI phép
#   [B2] sh thu_giao_dien/chay.sh                     → mã thoát 0 · 92.5s · (51, 0, 0, 0) · DONG
#   [B3] sh thu_giao_dien/chay.sh 06_ban_phim.spec.js → mã thoát 0 · 12.4s · ( 7, 0, 0, 0) · DONG
#   [E1] ba cổng `cây sạch`: g17 XANH · g18 XANH · g20_baomat DO_THAT  → NUA_VOI (2/3)   ← 1 ca HỎNG
#   [F1] E3 đồng hồ ĐÓNG BĂNG: sao_luu() → 3 tệp · khoi_phuc() → 1 bản cất            → NEN
#   [G1] test_c2a rc=0 (CÒN GHIM RÒ) · bộ đo độc lập G5: tổ hợp RÒ=2/5                → NEN
#   ca: 22 · hỏng/loi: 1 · bỏ qua: 1 · MÃ THOÁT = 1
#   vân tay SAU: write-tree=8fc624deb033 (KHÔNG ĐỔI) · ngoài hai tệp được phép: KHÔNG
#   tệp chép TẠM của bàn đo G20 còn lại trong cây: không
```

> **Vì sao `EXIT 1` là ĐÚNG ở đây:** cổng `3-bản-sao` ĐO ĐƯỢC **2/3** — một giá trị **NỬA VỜI**,
> không rơi vào ô `nền` (0) cũng không rơi vào ô `đóng` (3), nên nó **ĐỎ ở mọi chế độ**. Bộ kiểm
> **không** hạ cổng xuống cho vừa và **không** nới điều kiện.

---

## 0. BẢNG PHÁN QUYẾT — TÁM CỔNG, ĐO TRÊN `7344c02`

| # | Cổng | Giá trị ĐO ĐƯỢC | Cổng FAIL (điều kiện ĐỎ, viết ra chứ không hứa) | Phán quyết |
|---|---|---|---|---|
| **G-nền** | cây đang đo = cây của nền | `write-tree` = `8fc624de…` = `7344c02^{tree}` | `write-tree` ≠ `7344c02^{tree}` | **XANH** |
| **E2E-7** | `06_ban_phim.spec.js`, 7 ca | **(7 đạt · 0 hỏng · 0 bỏ qua · 0 KHÔNG CHẠY)** | < 7 đạt, hoặc hỏng > 0, hoặc 0 đạt (="KHÔNG CHẠY ĐƯỢC") | **XANH** |
| **E2E-51** | cả bộ tầng 3, 51 ca | **CHẬP CHỜN** — 5 lượt: 4 × (51,0,0,0) · 1 × (49,1,**1**,0) | khác `(51,0,0,0)` | **KHÔNG TẤT ĐỊNH** — `N-G22-01` |
| **C1** | cổng cây sạch wave trước (bàn đo G20) | **2/2 XANH · phán quyết DONG** | < 2/2 | **XANH** |
| **C2** | bàn phím TRONG màn, tầng 3 | **(7, 0, 0)** | ≠ (7,0,0) | **XANH** |
| **C3** | `git` môi trường NGUYÊN BẢN | **mã thoát 128** | ≠ 0 | **ĐỎ** |
| **C4** | route `truy_van` + migration v9 | **(True, False)** | ≠ (True, True) | **ĐỎ — KHÔNG CHỦ SỞ HỮU** |
| **C5** | có bộ `thu_qa_g19*.py` chạy thật | **0/1** | < 1 | **ĐỎ** |
| **3-bản-sao** | ba bản sao cổng "cây sạch" | **2/3** (`g20_baomat` ĐỎ) | < 3/3 | **ĐỎ** — `N-G22-02` |
| **E3-đồng-hồ** | bản cất sau 3 lượt `khoi_phuc()` cùng giây | **1** (đồng hồ ĐÓNG BĂNG) | < 3 | **ĐỎ** |
| **N-G21-03** | ca `test_c2a` còn ghim hành vi RÒ? | **1 (còn ghim)** · bộ đo độc lập: **2/5 tổ hợp RÒ** | ≠ 0 | **ĐỎ** |

> **Đọc bảng này cho đúng.** `XANH` nghĩa là **đo được và đạt**; `ĐỎ` nghĩa là **đo được và không đạt**.
> Không có ô nào là "bỏ qua". Chỗ **không đo được** nằm ở §7 — đó là **LỖ HỔNG PHẠM VI**, và nó
> **không** được cộng vào cột XANH.

---

## 1. NỀN ĐO — NHÃN VÀ SHA KHÔNG KHỚP NHAU, VÀ MÔI TRƯỜNG GIT BỊ CHẶN

### 1.1 `L-G22-A` — đề bài ghi `integration/g21 @ 7344c02`, nhưng **nhãn đó SAI**

Đo trực tiếp, không suy diễn:

```sh
git rev-parse integration/g21   # → 218fec408741a5c3e0d5c9cb558725cbb36ecd43
git rev-parse integration/g20   # → 7344c020abad562dafb593c4234d5e1f9ecfd18c
git merge-base --is-ancestor 7344c02 integration/g21 ; echo $?   # → 1  (KHÔNG phải tổ tiên)
git rev-list --count 218fec4..7344c02                            # → 7
```

| Nhãn | SHA thật | Quan hệ |
|---|---|---|
| `integration/g21` | `218fec408741a5c3e0d5c9cb558725cbb36ecd43` | **SAU** `7344c02` **7 commit**; KHÔNG chứa `7344c02` |
| `integration/g20` | `7344c020abad562dafb593c4234d5e1f9ecfd18c` | **đúng là** `7344c02` |

⇒ **SHA là thẩm quyền, nhãn thì không.** Bộ kiểm này đo trên `7344c02` và **CHỨNG MINH** điều đó
bằng bất biến **NỘI DUNG** (`git write-tree` = `7344c02^{tree}`), không bằng một cái tên nhánh.
Với một dự án mà cả một wave đã từng lệch nhau vì "hai nhiệt kế đo hai thứ" (`N-G18-00`), một cái
nhãn trỏ sai chỗ là đúng loại lỗi phải ghi thành tên.

### 1.2 `L-G22-B` — sandbox CHẶN ghi `.git`, và **hai đường "chữa" đều đã HỎNG**

```sh
$ git checkout -B g21-ag01-qa 7344c02
fatal: Unable to create '/Users/viporder/Projects/vip-express-hub/.git/worktrees/g21-ag01-qa/index.lock':
       Operation not permitted
```

Nên trong worktree `g21-ag01-qa`, `HEAD` **đứng yên** ở `601718e` (commit lượt G21 của tôi) trong
khi **CÂY đã được đưa về đúng nội dung `7344c02`** (bằng chỉ mục tạm trong `TMP`, không ghi `.git`).

**Hệ quả ĐO ĐƯỢC, và nó suýt thành một báo cáo sai:** cổng "cây sạch" chạy `git diff HEAD` thấy
**13 đường bẩn NGOÀI vùng thử** — nhưng đó là **delta GIỮA HAI COMMIT**, không phải thay đổi của
người đo. Lượt chạy `qa_g22_lan1_nhiem.log` vì thế có những cái ĐỎ **hoàn toàn không thuộc về sản
phẩm**. Tôi **không** gỡ cổng đó đi; tôi dựng lại **đúng môi trường đo**. Hai đường đã thử:

| Đường | Kết quả ĐO ĐƯỢC | Kết luận |
|---|---|---|
| (1) `GIT_DIR` **BÓNG** trong `TMP` (HEAD=nền, index=nền, mượn `refs/` kho chung) | Chạy tốt ~6 phút, rồi **HỎNG**: một bộ thử KHÁC gọi `git init <thư-mục-tạm>`, mà `GIT_DIR` **ĐÈ** lên đích của `git init` ⇒ nó `init` thẳng vào `GIT_DIR` bóng và ghi `bare = true`. Từ đó MỌI `git ls-files --others` trả **128** (`fatal: unable to set up work tree using invalid config`) và `thu_g21_chotcay.py` lỗ **8/13 ca**. | **HỎNG** — ghi lại ở `qa_g22_lan4_gitdir_bi_de.log` |
| (2) **BẢN SAO THẬT** — `git clone --shared --no-checkout <kho> $CP && git -C $CP checkout --detach 7344c02` | Một kho **BÌNH THƯỜNG**: `HEAD` = nền, cây SẠCH, `main` đọc được, và `git init` của bộ khác **không chạm tới** nó. | **ĐÚNG** — mọi số ở §2 đo bằng đường này |

Bộ kiểm vì thế **TỰ ĐO** môi trường và, khi `HEAD` không phải nền, nó **TỪ CHỐI phán quyết** trên
ba cổng "cây sạch" kèm lý do — thay vì bỏ qua im lặng hoặc báo đỏ giả.

---

## 2. BASELINE ĐỘC LẬP TRÊN `7344c02`

### 2.0 Vân tay cây — chụp **TRƯỚC và SAU** mọi lượt chạy

```sh
CÂY ĐO         : /var/folders/…/T/qa_g22_cay   (bản sao THẬT, KHÔNG phải worktree g21-ag01-qa)
cách dựng      : git clone --shared --no-checkout <kho> "$CP" && git -C "$CP" checkout --detach 7344c02
HEAD           : 7344c020abad562dafb593c4234d5e1f9ecfd18c
write-tree     : 8fc624deb0330dc8846a3337bf9a76fc90e253b0     ← TRƯỚC
tree(7344c02)  : 8fc624deb0330dc8846a3337bf9a76fc90e253b0
main           : de740dcd16617328f49f5ab97fac3ceb741e39fa
status -uall   : []                                          ← TRƯỚC (RỖNG)
sha256(ls-files -s): e79a8d364c8a8970670cafe6e76b71a367de40f614ec0049d63fa319b43bb564   ← TRƯỚC
so tep theo doi: 333
tai may        : 16.75 12.42 9.09        (máy dùng chung — xem §7 về phạm vi)
```

```sh
# === SAU ===
write-tree     : 8fc624deb0330dc8846a3337bf9a76fc90e253b0     ← KHÔNG ĐỔI
status -uall   : []                                          ← KHÔNG ĐỔI
sha256(ls-files -s): e79a8d364c8a8970670cafe6e76b71a367de40f614ec0049d63fa319b43bb564   ← KHÔNG ĐỔI
```

⇒ Lượt đo **không để lại dấu vết** trên cây. Con số dưới đây ghim được vào **đúng** cây đó.

### 2.1 Lượt chạy — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA, SỐ SKIP

```sh
$ sh app/thu/chay_tat_ca.sh
# BAT DAU : 2026-10-16T16:38:27+0700
# KET THUC: 2026-10-16T16:49:52+0700          (11 phút 25 giây)
# === EXIT CODE THAT = 1
# sha256 log: 3ebe0f3189970a747137a47b40043888d740d201d71521805a561205eb08951b
```

| Chỉ tiêu | **Số TÔI đo trên `7344c02`** | Lượt G21 của tôi trên `a3400a8` | Δ |
|---|---|---|---|
| **Mã thoát** | **1** | 1 | = |
| Số **ca** python | **1984** | 1870 | **+114** |
| Số **bộ** chạy thật | **56** | 51 | **+5** |
| Số bộ **BỎ QUA** (0 ca) | **1** — `thu_qa_g19.py` | 1 — cùng bộ | = |
| Số bộ **HỎNG** | **7** | **2** | **+5** |
| Frontend tầng 1 + 2 | **56 + 36** ca | 56 + 36 | = |
| E2E qua HTTP thật | **41/41** | 41/41 | = |
| Môi trường | `Darwin arm64` · python 3.9.6 · SQLite 3.51.0 | như trên | = |

**Năm bộ mới** (đếm bằng `git ls-tree` ở cả hai nền, không đếm bằng mắt):
`thu_g21_bimat.py` · `thu_g21_chotcay.py` · `thu_g21_gioihan.py` · `thu_g21_saoluu.py` · `thu_qa_g21.py`.

**Bảy bộ đỏ trên `7344c02`** (nguyên văn dòng tổng kết):

```
bộ hỏng:  thu_g20_dahang.py thu_g20_hop_dong.py thu_g20_saoluu.py thu_g21_saoluu.py
          thu_qa_g18.py thu_qa_g21.py thu_webhook_jt.py
```

| Bộ | Ca | Ca hỏng (nguyên văn) | Đỏ mới so với `a3400a8`? |
|---|---|---|---|
| `thu_g20_dahang.py` | 27 | `CaRanhGioi::test_a2_hai_ham_giu_chot_chan_hang_bi_gan_nhan_dung` · `test_a6_nhan_hieu_hang_trong_thong_diep_chi_tinh_chuoi_CHAY_DUOC` · `test_a7_bon_nhanh_ma_bi_rang_buoc_hang` | **MỚI** |
| `thu_g20_hop_dong.py` | 36 | `B_ChotAnToan::test_b01` · `test_b03` · `C_TiemLoi::test_c01` · `test_c02` · `test_c03_(P0,F01,F02,F03)` | **MỚI** |
| `thu_g20_saoluu.py` | 41 | `C::test_c3` · `D::test_d4` · **`E::test_e3`** · `F::test_f2` · `G::test_g2` · `K::test_k3` · `test_k4` · `test_k5` | cũ (đã đỏ ở `a3400a8`) |
| `thu_g21_saoluu.py` | 21 | `A_FailClosed::test_a1..test_a8` (8 ca) | **MỚI** |
| `thu_qa_g18.py` | 47 | `C_HarnessG16::test_c1_bo_do_chot_an_toan_tu_kiem_dat` · `test_c2_harness_chay_het_va_hai_chang_cham_hang_la_BLOCKED` | cũ |
| `thu_qa_g21.py` | 24 | `G1_CaySach::test_g1_cong_cay_sach_wave_truoc` · `Z_ChotChan::test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong` | **MỚI** |
| `thu_webhook_jt.py` | 99 | `K_G16::test_k06_tu_kiem_bo_do_chot_an_toan_bat_DUNG_chot` · `N_G17::test_n03_tu_kiem_bo_do_chot_an_toan_G17_bat_DUNG_chot` | **MỚI** |

**Ba bộ đỏ mới đã được chạy LẠI MỘT MÌNH để loại trừ chập chờn** (`thu_g20_dahang.py`,
`thu_webhook_jt.py`, `thu_qa_g18.py`): cả ba đều `EXIT=1` và **đúng những ca đó** ⇒ **ĐỎ TẤT ĐỊNH**,
không phải một lượt xui.

> ⚠ **ĐỌC KÈM `docs/QA_G21.md` §1.4.** Lượt trước tôi ghi `H1` phải cho "**bộ hỏng ít hơn** và vẫn
> **0 bộ đỏ vô danh**". Đo trên bản đã gộp: bộ hỏng **TĂNG 2 → 7**. Năm làn G21 **không** làm hồi quy
> sạch hơn; chúng thêm 5 bộ thử, và **5 bộ đỏ mới** — trong đó có **bộ thử của chính làn QA G21**
> (`thu_qa_g21.py`, hai ca) và **bộ của chính làn SAO LƯU G21** (`thu_g21_saoluu.py`, 8 ca).

---

## 3. VIỆC (b) — ĐO LẠI NĂM CỔNG G20 (`C1`..`C5`) TRÊN BẢN ĐÃ GỘP

```sh
$ VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
# === EXIT CODE THAT = 1
# Ran 21 tests in 21.300s · FAILED (failures=4, skipped=2)
# sha256 bản chép : 5a4b3c83c45f2f2c465d2eed380f1f6f69583878ca9e3a5f910bd01c1a0ddcd0  (= đúng bản QA_G20.md ghim)
# sha256 log      : 26bba19ff05651c81761be34677ad7441441091941c5d488d6e7000178c6a7fe
```

**Về tệp `app/thu/thu_qa_g20.py` — KHAI THẲNG:** nó **KHÔNG có trong cây** này và **KHÔNG có trong
bất kỳ commit nào** (`git log --all -- '*thu_qa_g20.py'` → **RỖNG**). Nó chỉ tồn tại như **tệp CHƯA
COMMIT** trong worktree `g20-ag01-qa`. AG-00 đã cho phép **chép TẠM** để đo rồi **XOÁ trước khi kết
thúc**; tôi làm đúng vậy, và `test_d1` của bộ kiểm G22 **tự khẳng định** tệp chép tạm đã bị xoá.

| Cổng G20 | Khoản nợ | `a3400a8` (lượt G21) | **`7344c02` (lượt này)** | Kết luận |
|---|---|---|---|---|
| **C1** | `N-G19-03` cổng cây sạch miễn trừ tên cứng | ĐỎ — 0/2 | **XANH — 2/2 · `phán quyết=DONG`** | **ĐÃ ĐÓNG** |
| **C2** | `V-13911` bàn phím trong màn | ĐỎ — (3,1,3), ca 04 = 1 | **XANH — (7, 0, 0)** · ca 04 = **13** điểm dừng (đòi >10) | **ĐÃ ĐÓNG** |
| **C3** | `N-G18-00` git môi trường nguyên bản | ĐỎ — 128 | **ĐỎ — 128** | **CÒN NGUYÊN** |
| **C4** | C6 của G19 nửa vời (route `truy_van`) | ĐỎ — (True, False) | **ĐỎ — (True, False)** | **CÒN NGUYÊN** — không chủ sở hữu |
| **C5** | `N-G20-01` không bộ G19-tổng-hợp nào chạy | ĐỎ — 0/1 | **ĐỎ — 0/1** | **CÒN NGUYÊN** |

Nguyên văn dòng bàn đo tự in (không suy diễn lại):

```
[C2] GIT_CONFIG_COUNT=2 · KEY_*=0 · VALUE_*=2
[G1] cổng cây sạch wave trước XANH: 2/2 · phán quyết=DONG
[B1] nhị phân: chỉ định BAN_GIAO §1 (chromium-1194) · mã thoát=0 · 7 đạt · 0 hỏng · 0 bỏ qua · 0 KHÔNG CHẠY
[B2] ca 04 trên nền: 13 điểm dừng là điều khiển TRONG màn (ngưỡng đặc tả: >10)
[C4] PHIEN_BAN_SCHEMA=9 · nang_len_v9=True · tệp SẢN XUẤT import truy_van=0
[C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: 0/1 · phán quyết=chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN
```

`C3` được **đo độc lập** (không qua bàn đo G20):

```sh
$ git rev-parse HEAD          # môi trường NGUYÊN BẢN, KHÔNG gỡ biến
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
# === EXIT CODE THAT = 128
# GIT_CONFIG_COUNT=2 · GIT_CONFIG_KEY_0='' (RỖNG) · GIT_CONFIG_VALUE_0 dài 5
```

### 3.1 `failures=4`, không phải 3 — **hai** trong bốn lỗi là **của chính bàn đo G20**

| Lỗi | Loại | Nội dung |
|---|---|---|
| `test_c4_route_truy_van_va_migration_v9` | **nợ thật** | `CỔNG C4 ĐỎ: chế độ GỘP: khoản nợ (True, False) VẪN CÒN NGUYÊN` |
| `test_c5_co_bo_thu_g19_tong_hop_chay_duoc` | **nợ thật** | `CỔNG C5 ĐỎ: chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN` |
| `test_c1_git_voi_moi_truong_NGUYEN_BAN` | **lỗi bàn đo (`L-G20-A`)** | `AssertionError: '7344c020abad…' != '148ecd380a90…'` — dòng 520 **ghim cứng nền `148ecd3`** vào đối chứng dương. Cổng C3 **không** vì thế mà xanh: dòng 513 (mã thoát git ∈ {128, 0}) đã qua trước đó, và **tôi đo lại bằng tay: 128**. |
| `test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong` | **lỗi bàn đo (`L-G20-B`)** | `THIẾU ĐỐI CHỨNG DƯƠNG cho: ['git-tho']` — chốt chặn của chính nó báo thiếu. |

⇒ **C1 và C2 đã XANH** (hai làn `chotcay` và `banphim` đã đóng nợ). **C3, C4, C5 còn ĐỎ.**
Bàn đo G20 **vẫn không dùng lại được nguyên trạng** cho lượt sau: hai lỗi `L-G20-A`/`L-G20-B` vẫn
nằm đó, y như lượt G21 đã ghi.

---

## 4. BỐN ĐIỂM SUPERVISOR GIAO — ĐO, KHÔNG KHAI

### 4.1 `N-G21-04` / điểm 1 — **E2E ĐÃ CHẠY ĐƯỢC**, bằng nhị phân CHỈ ĐỊNH; **KHÔNG skip**

**Đường dẫn + phiên bản (đề bài đòi ghi rõ):**

```
ĐƯỜNG DẪN : /Users/viporder/orca/workspaces/vip-express-hub/g21-ag01-qa/node_modules/
            playwright-core/.local-browsers/chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium
realpath  : /Users/viporder/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers/
            chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium
PHIÊN BẢN : Chromium 141.0.7390.37          (`"$P" --version` · exit 0)
NGUỒN     : symlink `.local-browsers` → `Projects-vip-express-hub` — đúng đường `BAN_GIAO.md` §1 đã
            ghim và `docs/G21_BANPHIM_E2E.md` §10 ghi là **AG-06 đã chạy THÀNH CÔNG**
```

**Vì sao lượt trước không chạy được, và vì sao "cài thêm trình duyệt" là đường SAI:**
`thu_giao_dien/chay.sh` ghim `PLAYWRIGHT_BROWSERS_PATH=0`, tức nó chỉ tìm trong
`node_modules/playwright-core/.local-browsers`. Cache hệ thống `~/Library/Caches/ms-playwright` có
chromium **1148** và **1243** — **cả hai đều SAI revision**: `playwright-core` trong repo là
**1.56.1**, `browsers.json` của nó đòi **revision 1194**. Đo lại bằng chính Playwright:

```sh
$ PLAYWRIGHT_BROWSERS_PATH=0 node -e "console.log(require('playwright-core').chromium.executablePath())"
…/node_modules/playwright-core/.local-browsers/chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium
ton tai = true · thuc thi duoc = true
```

**Kết quả chạy THẬT — và đây là chỗ tôi phải nói thẳng:**

| Lượt | Lệnh | Mã thoát | (đạt, hỏng, bỏ qua, KHÔNG CHẠY) |
|---|---|---|---|
| A (trong bộ kiểm) | `sh thu_giao_dien/chay.sh` | **0** | **(51, 0, 0, 0)** |
| B (trong bộ kiểm) | `sh thu_giao_dien/chay.sh` | **1** | **(49, 1, 0, 1)** |
| C | `sh thu_giao_dien/chay.sh` | **0** | **(51, 0, 0, 0)** |
| D | `sh thu_giao_dien/chay.sh` | **0** | **(51, 0, 0, 0)** |
| E, F, G (riêng) | `sh thu_giao_dien/chay.sh 06_ban_phim.spec.js` | **0 · 0 · 0** | **(7, 0, 0, 0)** ba lượt |
| H (trong bộ kiểm, lượt cuối) | `sh thu_giao_dien/chay.sh` | **0** | **(51, 0, 0, 0)** |

⇒ **KHÔNG CHẠY ĐƯỢC** là **SAI** ở lượt này: bộ 7 ca chạy **3/3 lượt · 7/7 ca · exit 0**.
⇒ **Nhưng "E2E đạt" cũng KHÔNG đúng**: lượt đầy đủ **CHẬP CHỜN 1/5 lượt** — xem `N-G22-01` (§6.1).
Cả bảy lượt đều để lại cây **nguyên vẹn** (`admin/ban_phim.js` còn nguyên, `write-tree` không đổi).

### 4.2 Điểm 2 — cổng "cây sạch": **2/3, KHÔNG phải 3/3**

**Ba bản sao ĐANG SỐNG** của cùng một luật (đo bằng cách chạy từng cái trong **tiến trình con**):

| Cổng | Mã thoát | Phân loại | Vì sao |
|---|---|---|---|
| `thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` | **0** | **XANH** | đã chuyển sang `thu_g21_chotcay` — vùng TỰ DÒ theo QUY TẮC (`docs/`, thư mục bắt đầu bằng `thu`) |
| `thu_qa_g18.py::A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **0** | **XANH** | như trên |
| `thu_g20_baomat.py::A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **1** | **`DO_THAT`** | **vẫn dùng danh sách CỨNG `TEP_CUA_WAVE_G20`** (4 tên của wave G20) ⇒ hai tệp hợp lệ của AG-01 G22 làm nó ĐỎ |

**ĐỐI CHỨNG DƯƠNG BẮT BUỘC (không có nó thì "2/3" chỉ là một con số):** tôi **TIÊM** một tệp bẩn
NGOÀI vùng thử (`admin/__tiem_g22.js`), chạy lại cổng `g17`:

```
TIÊM `__tiem_g22.js` → cổng g17 phải ĐỎ: ĐỎ (rc=1)
```

⇒ Ba cổng này **CÓ RĂNG**. Con số `2/3` là **thật**: **AG-05 đã sửa HAI bản, còn HAI bản chưa sửa.**

**Bản sao thứ TƯ là DORMANT — đo được, không suy đoán:**

```sh
$ python3 app/thu/thu_qa_g19.py
# → rc=0 · Ran 0 tests · OK (skipped=1)
```

`thu_qa_g19.py` tự BỎ QUA khi `HEAD` ≠ nền đóng băng `6e61fc1`. Nó **không** làm đỏ hồi quy chung,
nên nó không vào được phép đếm "3 bản sao đang sống" — nhưng nó vẫn là **bản sao thứ tư của cùng
một luật**, còn nguyên, và nó chỉ ĐỎ khi ai đó chạy `VIP_G19_HEAD=<HEAD>`. **Đây là khoảng trống
phạm vi, không phải ĐẠT.**

### 4.3 Điểm 3 — ca `E3` **phụ thuộc ĐỒNG HỒ**: đo bằng ĐỒNG HỒ ĐÓNG BĂNG, có ĐỐI CHỨNG ĐƯỜNG

**Cơ chế, đọc từ mã sản phẩm (`app/migrate.py`):**

```python
# sao_luu()  — dòng 61-66: ĐÃ VÁ, thêm hậu số, KHÔNG BAO GIỜ ghi đè
dich, n = goc + ".db", 1
while os.path.exists(dich):
    dich = f"{goc}-{n}.db"

# khoi_phuc() — dòng 606-607: CHƯA VÁ, tên đặt theo GIÂY, ghi đè im lặng
cat_di = os.path.join(THU_MUC_SAO_LUU,
                      "hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")
```

**Vì sao phải ĐÓNG BĂNG đồng hồ, và vì sao KHÔNG được chấp nhận một lượt "may mắn":** ba lượt
`khoi_phuc()` rơi vào **HAI giây khác nhau** sẽ để lại ≥2 tệp **dù lỗi còn nguyên** ⇒ ca thử XANH
GIẢ, phụ thuộc **TỐC ĐỘ MÁY**. Đó đúng là "xanh khi chung, đỏ khi riêng". Cách đo ở đây **không**
dựa vào may rủi và **không** che bằng retry: nó tiêm một `migrate` có `datetime.now()` **ĐÓNG BĂNG**
tại `2026-10-16 12:00:00`, nên ba lượt gọi **CHẮC CHẮN** cùng một giây.

```sh
# A) BẢN THẬT (chưa vá) — đồng hồ đóng băng
__JSON__={"so_sao_luu_khac_nhau": 3, "so_ban_cat_rollback": 1,
          "ten_ban_cat": ["hub-truoc-rollback-20261016-120000.db"], "luc_dong_bang": "20261016-120000"}
# B) ĐỐI CHỨNG ĐƯỜNG — CÙNG đồng hồ, `khoi_phuc()` ĐÃ VÁ (thêm hậu số)
__JSON__={"so_sao_luu_khac_nhau": 3, "so_ban_cat_rollback": 3,
          "ten_ban_cat": ["…-120000-1.db", "…-120000-2.db", "…-120000.db"]}
```

| Vế | Đo được | Vai |
|---|---|---|
| `sao_luu()` (ĐÃ VÁ) · cùng đồng hồ đóng băng | **3 tệp khác nhau** | **ĐỐI CHỨNG DƯƠNG** — chứng minh (i) đồng hồ đóng băng **có hiệu lực**, (ii) phép đếm **NHÌN THẤY** được sự khác nhau |
| `khoi_phuc()` (CHƯA VÁ) · cùng đồng hồ | **1 tệp** | **PHÉP ĐO** — ba lượt ghi đè lên nhau |
| `khoi_phuc()` ĐÃ VÁ · cùng đồng hồ | **3 tệp** | **ĐỐI CHỨNG ĐƯỜNG** — phép đo **PHÂN BIỆT ĐƯỢC** bản vá với bản chưa vá |

⇒ **Bàn đo E3 nay TẤT ĐỊNH và ĐỌC ĐƯỢC**, không phụ thuộc đồng hồ hệ thống. **Lỗi sản phẩm thì
CÒN**: `khoi_phuc()` vẫn đặt tên theo giây. Và nó **tất định ĐỎ** dưới đồng hồ đóng băng — nên
`thu_g20_saoluu.py::E::test_e3` ĐỎ **là TÌNH TRẠNG ĐÚNG**, không phải chập chờn.

### 4.4 Điểm 4 — `N-G21-03`: ca `test_c2a` **VẪN GHIM hành vi RÒ**

```sh
$ python3 app/thu/thu_g20_dahang.py CaGanChat.test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia
# === EXIT CODE THAT = 0 · OK
# còn khẳng định `assertTrue(ket_qua["gia_ngan"])` (tức CÒN GHIM RÒ): True
```

Nguyên văn còn nằm trong tệp (`app/thu/thu_g20_dahang.py`, dòng 661-663):

```python
self.assertTrue(ket_qua["gia_ngan"],
                "ĐỔI HÀNH VI: credential ngắn của hãng giả nay ĐƯỢC che — nếu ai đó vừa mở "
                "rộng `TRUONG_CREDENTIAL`, hãy cập nhật tài liệu và ca này")
```

**ĐỐI CHỨNG DƯƠNG ĐỘC LẬP** (một bộ đo KHÁC, không phải ca đang bị nghi):

```sh
$ python3 app/thu/thu_qa_g21.py G5_CredentialNgan
# → rc=0 · tổ hợp RÒ=2/5
```

⇒ Bộ đo độc lập **NHÌN THẤY** 2 tổ hợp rò, nên kết luận "ca kia còn ghim rò" **không** phải là kết
luận từ một bộ đo mù. `app/thu/thu_g20_dahang.py` **không** bị sửa giữa `a3400a8` và `7344c02`
(`git diff --stat a3400a8 7344c02 -- app/thu/thu_g20_dahang.py` → **RỖNG**), nên **AG-03 đã KHÔNG
đồng bộ ca này**. Đây là **việc còn nợ**, không phải việc đã xong.

### 4.5 `C4` — **VẪN CHƯA CÓ CHỦ SỞ HỮU**

```sh
$ python3 app/thu/thu_qa_g22.py H_C4
# [H1] C4 — `PHIEN_BAN_SCHEMA`=9 (đòi 9) · tệp SẢN XUẤT import `truy_van`: 0
#      cặp đo được = (True, False) · nền=(True, False) · đóng=(True, True)
```

Đo độc lập, không qua bàn đo G20: quét AST **mọi** tệp `.py` ngoài vùng thử/tài liệu (luật vùng
giống `thu_g21_chotcay`: thư mục tên `docs` hoặc bắt đầu bằng `thu`), đếm tệp SẢN XUẤT `import
truy_van` ⇒ **0**. AG-00 đã ghi thẳng vào backlog **G22–G25** và **sẽ giao khi có làn rảnh**.
**Bộ kiểm này KHÔNG nhận C4 là đã đóng**, và nếu ai đó đóng nó thì `H1` sẽ **HỎNG** và bắt cập nhật
tài liệu — đó là mục đích của ca.

---

## 5. HAI CHỐT CHẶN — CHẠY THẬT, KHÔNG KHAI

### 5.1 Chốt (a) — ca TỰ KIỂM BỘ ĐO chạy trong **TIẾN TRÌNH CON**

`Z2` chạy một ca tự kiểm trong tiến trình con và khẳng định **BỐN** vế, cả bốn **ĐO ĐƯỢC**:

```
(i)   PID bộ kiểm=5870 · PID tiến trình con=13062 · KHÁC NHAU=True
(ii)  chiều XUỐNG — con thấy biến môi trường của cha: True  ('THAY_CUA_CHA=cha-dat-truoc')
(iii) chiều LÊN — cha thấy biến môi trường của con: False  (trước khi gọi=None, sau khi gọi=None)
      đối chứng âm của (iii): cùng phép đọc, chạy Ở CHA → thấy=True
(iv)  mã thoát của tiến trình con đọc RA được: 3 (đòi 3)
```

**Vế (ii) là chỗ nhiều "chốt chặn" khác chết:** một phép đo chỉ có chiều LÊN ("con đặt thì cha không
thấy") vẫn XANH được với một tiến trình con **KHÔNG HỀ CHẠY** — vì cha cũng chẳng thấy gì. Vế (ii)
chứng minh kênh **có chạy thật**, nên (iii) mới có nghĩa. Vế (iii) còn có **đối chứng âm**: cùng
phép đọc, chạy ở CHA thì **PHẢI** thấy.

Và `Z5` áp cùng chốt đó lên **CHÍNH BỘ CHẠY**: chạy lại tệp này trong tiến trình con với một **ca
mồi CỐ Ý HỎNG** (`VIP_G22_CHAY_MOI=1`):

```
[Z5] chạy CHÍNH bộ kiểm này trong TIẾN TRÌNH CON (pid=13069), có mồi hỏng:
     mã thoát THẬT của tiến trình con = 1 (đòi KHÁC 0)
```

### 5.2 Chốt (b) — **ĐỐI CHỨNG DƯƠNG cho MỌI ca phủ định**

`Z6` in sổ và **TỰ PHÁN HỎNG** nếu một nhóm phủ định thiếu đối chứng, **hoặc** đối chứng chưa chạy
thật, **hoặc** nhóm đó chưa được **TIÊM LỖI**:

```
cay-sach-3-ban-sao     đã chạy đối chứng=True   đã tiêm lỗi=True
cay-sach-bo-do         đã chạy đối chứng=True   đã tiêm lỗi=True
e2e-chromium           đã chạy đối chứng=True   đã tiêm lỗi=-
e3-ba-luot-cung-giay   đã chạy đối chứng=True   đã tiêm lỗi=True
g20-c1-cay-sach        đã chạy đối chứng=True   đã tiêm lỗi=-
ng21-03-ca-ghim-ro     đã chạy đối chứng=True   đã tiêm lỗi=True
nua-voi                đã chạy đối chứng=True   đã tiêm lỗi=-
tien-trinh-con         đã chạy đối chứng=True   đã tiêm lỗi=-
```

**"Đã tiêm lỗi" là vế mà một lời khai không có được.** `Z3` tiêm lỗi vào **chính bộ đo**:

```
cổng ĐỎ-THẬT giả  → bộ phân loại gọi: DO_THAT (đòi DO_THAT)
'3 passed · 1 failed · 3 did not run' → bộ đếm: (3, 1, 0, 3) (đòi đạt=3, không_chạy=3)
giá trị NỬA VỜI 2 (nền=1, đóng=3) → sổ: NUA_VOI (đòi NUA_VOI)
```

`Z4` khẳng định **ô thứ ba** của sổ giá trị: một giá trị **NỬA VỜI** là **ĐỎ ở CẢ HAI chế độ** —
"0 lỗi" chỉ được tin khi đã chứng minh bộ đo **NHÌN THẤY** lỗi.

> `Z6` mang tên `z6` chứ không phải `z1` là **CỐ Ý**: `unittest` chạy các ca trong một lớp theo
> **thứ tự chữ cái**, nên `z1` chạy **TRƯỚC** `z2`..`z5` và tự phán hỏng vì cờ đối chứng chưa bật —
> đo được ở lượt chạy thứ hai: `AssertionError: ['cay-sach-bo-do', 'nua-voi', 'tien-trinh-con'] != []`.
> Chốt chặn phải chạy **CUỐI** thì nó mới phán được.

---

## 6. PHÁT HIỆN

### 6.1 `N-G22-01` — **CAO**: ca TỰ KIỂM tầng 3 **phụ thuộc THỨ TỰ** — xanh khi chạy riêng, đỏ khi chạy chung

`thu_giao_dien/06_ban_phim.spec.js` ca 06 (**TỰ KIỂM: gỡ `ban_phim.js` ⇒ menu KHÔNG vào được thứ
tự Tab và Enter không đổi màn**) **XOÁ một tệp SẢN PHẨM ngay giữa lượt chạy** để chứng minh ca 02
đo bản vá. Đo được:

| Lượt | Kết quả | Mã thoát |
|---|---|---|
| Chạy **RIÊNG** `06_ban_phim.spec.js` (3 lượt) | **7 passed** · 7 passed · 7 passed | 0 · 0 · 0 |
| Chạy **CHUNG** cả bộ 51 ca (5 lượt) | (51,0,0,0) · (49,1,**1**,0) · (51,0,0,0) · (51,0,0,0) · (51,0,0,0) | 0 · **1** · 0 · 0 · 0 |

Nguyên văn lượt đỏ:

```
✘ 44 [chromium] › 06_ban_phim.spec.js:325:1 › 06 — TỰ KIỂM: gỡ `ban_phim.js` …
  Error: gỡ module mà Enter VẪN đổi màn ⇒ ca 02 không đo bản vá
  Expected: false   Received: true
  Test timeout of 30000ms exceeded.
```

**Vì sao đây là phát hiện chứ không phải "một lượt xui":** cùng một cây, cùng một nhị phân, cùng
một lệnh — chỉ khác **vị trí trong lượt chạy**. Cơ chế khớp với triệu chứng: ca tự kiểm gỡ tệp
**sau khi** máy chủ đã phục vụ ~43 ca trước đó, nên trang đang đo có thể đã nạp sẵn `ban_phim.js`
(hoặc máy chủ đã đệm) ⇒ việc gỡ **không có hiệu lực** ⇒ "Enter VẪN đổi màn" ⇒ ĐỎ.

**Vì sao nó nguy hiểm hơn một ca chập chờn thường:** nó **làm đỏ cả bộ E2E** — và bộ E2E là **cổng
chặn hồi quy chính thức của dự án**. Một cổng chặn lúc xanh lúc đỏ thì không chặn được gì; tệ hơn,
nó dạy người trực bỏ qua màu đỏ. `playwright.config.js` đã đặt `retries: 0` với lý do rất đúng
(*"một ca chập chờn phải LỘ RA, không được giấu"*) — nên **cách chữa KHÔNG được là thêm retry.**

**Đề xuất (không tự làm — `thu_giao_dien/**` ngoài vùng được ghi của tôi):** ca tự kiểm phải kiểm
**sự gỡ có hiệu lực** trước khi kết luận (ví dụ: tải lại trang sau khi gỡ, hoặc khẳng định máy chủ
đã trả 404 cho `ban_phim.js`), và phải **khôi phục tệp trong `finally`** kể cả khi ca hỏng — hiện
tệp được khôi phục (đo được: `admin/ban_phim.js` còn nguyên, `write-tree` không đổi), nhưng tính
chất "sửa cây sản phẩm giữa lượt đo" vẫn là mầm của `N-G22-01`.

### 6.2 `N-G22-02` — **CAO**: khoản nợ "cây sạch" đã đóng **2/3**, không phải 3/3

Xem §4.2. Bản sao **còn sống** chưa sửa: `app/thu/thu_g20_baomat.py` — vẫn dùng danh sách **CỨNG**
`TEP_CUA_WAVE_G20`. Bản sao **dormant** chưa sửa: `app/thu/thu_qa_g19.py` dòng 83-86
(`CONG_CAY_SACH_WAVE_TRUOC` + `TEP_CUA_AG01_G19`).
**Hệ quả ĐO ĐƯỢC:** `thu_qa_g21.py::G1_CaySach::test_g1_cong_cay_sach_wave_truoc` **ĐỎ** trong
lượt chạy chung — tức **bộ thử của chính làn QA G21 đang đỏ vì khoản nợ này**, và nó là một trong
**bảy bộ đỏ** của baseline (§2.1).

### 6.3 `N-G22-03` — **TRUNG BÌNH**: cổng `git-tho` (`C3`) vẫn đỏ, và nó đỏ **trong mọi tiến trình con**

`GIT_CONFIG_COUNT=2` mà `GIT_CONFIG_KEY_0` **RỖNG** ⇒ mọi lệnh `git` **nguyên bản** thoát **128**.
Đo được cả trong lượt chạy chung (`thu_g20_saoluu.py`, `thu_qa_g18.py`, `thu_webhook_jt.py` đều có
ca tự kiểm gọi git) lẫn bằng tay (§3). `chay_tat_ca.sh` **tự gỡ** gia đình biến dị dạng trước khi
chạy (vá `N-G18-00`), nên bộ chạy chung không chết — nhưng **bất kỳ ai gọi `git` trực tiếp** vẫn
nhận 128. Đây là **lỗi môi trường của máy**, không phải của sản phẩm, và nó **vẫn chưa đóng**.

### 6.4 `L-G22-A` và `L-G22-B` — hai lỗi **của chính lượt đo này**, ghi lại vì chúng suýt làm sai báo cáo

- **`L-G22-A`**: nhãn `integration/g21 @ 7344c02` **sai** — `integration/g21` = `218fec4` (§1.1).
- **`L-G22-B`**: đường "chữa" `GIT_DIR` bóng **hỏng** vì `git init` của bộ khác đè lên nó (§1.2).
  Nếu tôi không phát hiện, `thu_g21_chotcay.py` sẽ được báo là **8/13 ca HỎNG** — một phát hiện
  **bịa hoàn toàn**, do chính môi trường đo của tôi.

---

## 7. CHƯA ĐO — NÓI THẲNG, KHÔNG CỘNG VÀO CỘT XANH

| # | Chưa đo | Vì sao | Ai cần |
|---|---|---|---|
| 1 | **C4** (`truy_van` vào migration v9) | **không có chủ sở hữu**; AG-00 đã ghi vào backlog G22–G25 | AG-00 giao làn |
| 2 | **C5** (bộ `thu_qa_g19*.py` chạy thật) | `thu_qa_g19.py` tự bỏ qua (`HEAD` ≠ nền đóng băng); bộ `thu_qa_g19_tich_hop.py` mà nó trỏ tới **KHÔNG TỒN TẠI** | AG-00 |
| 3 | **Tầng 3 trong Safari / Firefox · trình đọc màn hình · cảm ứng thật · in PDF thật** | ngoài phạm vi thiết kế (`thu_giao_dien/chay.sh` tự khai) | Owner |
| 4 | **CSDL nghiệp vụ trên PostgreSQL** (`D-8`) | **0** kết nối; cụm `:5432` **không bị đụng tới** | Owner |
| 5 | **Credentials hãng thật · API hãng kể cả sandbox · AI thật · dữ liệu lớn** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM** | Owner |
| 6 | **Mã trạng thái hãng (`D-4`)** | không chạm bảng ánh xạ; mã chưa xác minh ⇒ `NEEDS_REVIEW` | Owner |
| 7 | **Nhiều tiến trình thật** (trần rate limit trong bộ nhớ MỘT tiến trình) | ngoài phạm vi lượt này | AG-00 |
| 8 | **`thu_g20_hop_dong.py` (8 ca) và `thu_g21_saoluu.py` (8 ca)**: nguyên nhân gốc từng ca | tôi **đã đo** chúng đỏ **tất định** (chạy lại một mình, `EXIT=1`, đúng những ca đó) nhưng **chưa** truy tới hàm hỏng | làn sở hữu |
| 9 | **Máy dùng chung**: load trung bình **9–17** trong suốt lượt đo (nhiều tiến trình của agent khác cùng chạy) | ảnh hưởng tới các ca **phụ thuộc thời gian**; đây là lý do `E3` **phải** đo bằng đồng hồ đóng băng | — |

---

## 8. TUÂN THỦ TUYỆT ĐỐI + BÀN GIAO CHO AG-00

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | **0** lời gọi ra hãng. Mọi máy chủ là `app/server.py` trên nền tạm, `127.0.0.1`, cổng OS cấp | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | **0** lệnh `git push`/`ssh`/tunnel. Không mở `CHO_PHEP_LIVE` | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | **Không đọc `.env`.** Nền dữ liệu là `mktemp -d`; không giá trị bí mật nào vào log | ✓ |
| 4 | Đoán mã trạng thái hãng (`D-4`) | Không chạm bảng ánh xạ; không mã nào được gán | ✓ |
| 5 | Chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | Chuyển CSDL nghiệp vụ sang PostgreSQL (`D-8`) | `[A3] PHIEN_BAN_SCHEMA=9` · CSDL nghiệp vụ **SQLite** · `[A4]` cổng 5432 **CÓ** người nghe trên máy nhưng bộ kiểm mở **0** kết nối tới nó | ✓ |
| 7 | Dùng Claude/mô hình khác · tự bấm duyệt sandbox | **0** lời gọi mô hình; **0** thao tác duyệt | ✓ |
| 8 | Xoá hàng loạt · sửa ngoài phạm vi | Xem §8.1 | ✓ |

### 8.1 Phạm vi ghi — và **một việc AG-00 PHẢI LÀM HỘ**

`git status --porcelain -uall` trên cây đo (`$CP`) **sau** mọi lượt:

```
?? app/thu/thu_qa_g22.py
?? docs/QA_G22.md
```

Đúng **hai** tệp được phép. `write-tree` **KHÔNG ĐỔI** (`8fc624de…`). Bản chép **TẠM** của bàn đo
G20 **đã bị xoá** (bộ kiểm tự khẳng định: `còn tồn tại = False`).

**`index.lock` — sandbox chặn ghi `.git`, tôi KHÔNG tự vượt:**

```sh
$ git checkout -B g21-ag01-qa 7344c02
fatal: Unable to create '…/.git/worktrees/g21-ag01-qa/index.lock': Operation not permitted
```

⇒ Trong worktree `g21-ag01-qa`, `HEAD` **vẫn là** `601718e42ea23a30b849d606890070d4816cbf0b`
(nhánh `g21-ag01-qa`), trong khi **CÂY đã là `7344c02`**. AG-00 commit hộ theo đúng thứ tự sau:

```sh
git -C /Users/viporder/orca/workspaces/vip-express-hub/g21-ag01-qa reset --mixed 7344c02
git -C /Users/viporder/orca/workspaces/vip-express-hub/g21-ag01-qa add docs/QA_G22.md app/thu/thu_qa_g22.py
git -C /Users/viporder/orca/workspaces/vip-express-hub/g21-ag01-qa commit \
    -m "AG-01 (G22) QA BASELINE: 7344c02 1984 ca/56 bo/7 bo hong · C1+C2 XANH · E3 do bang dong ho dong bang"
```

`reset --mixed 7344c02` an toàn: `601718e` **là cha** của `7344c02`, nên không mất commit nào; nó chỉ
đưa `HEAD` + index về đúng nền mà cây đang có. **Thông điệp commit đề xuất:**

```
AG-01 (G22) QA BASELINE: 7344c02 1984 ca/56 bo/7 bo hong · C1+C2 XANH · E3 do bang dong ho dong bang
```
