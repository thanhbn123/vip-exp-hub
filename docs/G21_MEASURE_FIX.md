# G21 · SỬA BỘ ĐO `thu_qa_g21.py` — STALE SO VỚI CÂY ĐÃ GỘP

**Vai:** Agent U3 (worker Orca) · **Task:** `task_5528e61854f9` · **Dispatch:** `ctx_2b07a694bd9d`
**Nền giao:** clone `b1c5205`, chế độ **`gop`** · **Cây đo thật:** `HEAD = 2f4c3d1402c1222633207cfc483796c09f3df0f9`
(`b1c5205` + commit nghiệm thu của AG-00) · python 3.9.6 · SQLite 3.51.0 · Darwin arm64.

**Phạm vi ghi (đúng hai tệp):**

| Tệp | Loại |
|---|---|
| `app/thu/thu_qa_g21.py` | sửa |
| `docs/G21_MEASURE_FIX.md` | **mới** (tệp này) |

**KHÔNG** sửa tệp của agent khác: `app/gioi_han.py`, `trien_khai/g18/*`, `app/cau_hinh.py`,
`app/migrate.py`, `thu_giao_dien/*`, `app/thu/thu_qa_g1*.py` đều giữ nguyên.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

Lệnh của đề bài, chạy đúng nguyên văn:

```sh
$ VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
```

| Chỉ tiêu | **TRƯỚC khi sửa** | **SAU khi sửa** |
|---|---|---|
| `Ran N tests` | **24** | **24** |
| **PASS** | **15** (24 − 5 FAIL − 4 SKIP) | **20** (24 − 1 FAIL − 3 SKIP) |
| **failures** | **5** (G1 · G2 · G3 · G6 · Z1) | **1** (G6 — lỗi THẬT, không sửa ca) |
| **skipped** | **4** (G4 · H1 · Z8 · Z9) | **3** (H1 · Z8 · Z9 — bỏ qua THEO THIẾT KẾ) |
| **mã thoát** | **1** | **1** (vì G6 còn ĐỎ) |
| Tầng 3 bàn phím | 0 ca (migrate từ chối) | **8/8 ĐẠT · 0 hỏng · 0 không chạy · ca 04 = 13 điểm dừng** |
| G4 sao lưu | **SKIP** | **ĐO THẬT: 0/4 đầu vào độc hại được nhận** + đối chứng dương/âm |
| Z1 đối chứng | ĐỎ (thiếu dương `cong-cay-sach`) | **15 nhóm · 0 nhóm thiếu dương** |

> **Đối chiếu với con số điều phối giao:** bản tham chiếu ghi **failures=4** (G1, G3, G6, Z1) và
> `skipped=5`. Lượt của tôi đo được **failures=5** vì **G2 cũng ĐỎ**: môi trường shell của phiên
> này có `GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0/1` (N-G18-00) — xem §2.2. Đó không
> phải lỗi sản phẩm (docs/OWNER_ACTIONS §F; `docs/G22_A1_GIT.md` §1.1a) và G2 đã được viết lại
> theo bất biến đúng, nên nó **XANH ở cả hai loại môi trường**. Chênh lệch `skipped` (5 so với 4)
> giải thích được bằng đúng ca G2: bản cũ **bỏ qua** khi phiên không đặt `GIT_CONFIG_COUNT`, còn
> phiên này đặt biến dị dạng nên nó **chạy và ĐỎ** thay vì bỏ qua.

---

## 1. BẢNG PHÂN LOẠI — STALE / LỖI THẬT / THIẾT LẬP ĐO

| Ca | TRƯỚC | Phân loại | ĐÃ LÀM |
|---|---|---|---|
| **G1** `G1_CaySach` | FAIL: `g17 không thấy tệp AG-01 G21 trong cây: []` | **STALE** — đối chứng dương của bản cũ đòi hai tệp QA phải đang là `?? …` (chưa theo dõi). Trên cây đã gộp chúng là tệp **ĐÃ THEO DÕI** và cây SẠCH, nên `q17._cay_ban()` rỗng. | Viết lại: đọc **tại chỗ** bộ lọc vùng của cả ba cổng; đối chứng bằng **dòng porcelain TỔNG HỢP** (tệp thử/tài liệu phải được miễn trừ, `app/webhook.py` phải bị giữ). Cổng đo **số cổng còn ĐỎ** = 0. |
| **G2** `G2_GitTho` | FAIL (riêng phiên này): `git… mã thoát=128` | **STALE + MÔI TRƯỜNG** — bản cũ ghim mã thoát của môi trường **NGUYÊN VĂN** vào cổng sản phẩm. `GIT_CONFIG_*` dị dạng là lỗi **máy**, không phải mã sản phẩm; `chay_tat_ca.sh` đã tự gỡ từ G18. | Viết lại theo đúng ba luật của `thu_g21_chotcay`: (1) dị dạng ⇒ chuẩn hoá **kèm cảnh báo**; (2) hợp lệ ⇒ **không** gỡ; (3) lỗi THẬT vẫn nổi lên. Cổng đo `git` **đã chuẩn hoá** = 0. |
| **G3** `G3_Tang3BanPhim` | FAIL: `bộ đếm không đọc ra ca nào` (migrate từ chối vì **chưa khai kho**) | **THIẾT LẬP ĐO + STALE** — thiếu `VIP_KHO_DANG_CHAY` (G22) ⇒ Playwright không được gọi; **và** spec đã thành **8 ca** trong khi bản cũ ghim `(7,0,0)`. | `do_tang_3()` khai kho bằng `cau_hinh.khai_kho_kiem_thu()`; G3 **đọc số ca từ chính spec** (`^test\(`), đòi `đạt == spec`, `hỏng + không_chạy == 0`, ca 04 > 10 điểm dừng. |
| **G4** `G4_SaoLuu` | **SKIP**: `dựng nền hỏng: migrate.py → TỪ CHỐI: CHƯA KHAI kho đang chạy` | **THIẾT LẬP ĐO + STALE** — thiếu khai kho; **và** "tệp LÀNH" cũ là `shutil.copy2` trần, nay bị bản vá fail-closed TỪ CHỐI vì thiếu `.sha256` (đúng thiết kế). | Khai kho qua `cau_hinh`; đối chứng dương dùng **chính `migrate.sao_luu()`** (có dấu kiểm); thêm đối chứng âm: `copy2` không dấu kiểm bị TỪ CHỐI, đường thoát `--toi-da-biet-chua-kiem-duoc` nhận được. |
| **G6** `G6_HarnessGioiHan` | FAIL: `harness … mã thoát=3` | **LỖI THẬT — KHÔNG SỬA CA** (đề bài chỉ định). Xem §3: `rc=3` là *thiết lập đo của harness*, còn bên dưới là **N-G20-01 vẫn mở** (`gioi_han.xoa_het()` xoá kho đếm dùng chung ⇒ G18-05 ĐỎ). | **Không đụng một dòng nào** trong ca G6. Báo AG-00 + ghi rõ chủ sở hữu/đường đóng ở §3. |
| **Z1** `Z_ChotChan` | FAIL: `THIẾU ĐỐI CHỨNG DƯƠNG cho: ['cong-cay-sach']` | **CASCADE** — G1 hỏng trước dòng `_dc_duong("cong-cay-sach")`, nên sổ đối chứng thiếu vế dương. | Không sửa Z1; G1 xanh ⇒ Z1 tự xanh. Bằng chứng: 15 nhóm, 0 nhóm thiếu dương. |

---

## 2. BA CA STALE — SỬA THEO BẤT BIẾN ĐÚNG, KHÔNG GHIM SỐ CŨ

### 2.1 G1 — cổng "cây sạch" của wave trước

**Sự thật cũ (STALE):** bản G21 đo `q17._cay_ban()` trên cây thật và đòi thấy `docs/QA_G21.md` +
`app/thu/thu_qa_g21.py` trong `git status`. Điều đó chỉ đúng khi hai tệp **chưa được commit**.
Trên cây đã gộp, `git status` sạch ⇒ `_cay_ban()` trả `[]` ⇒ đối chứng dương tự phá.

**Bất biến đúng:** trên cây chỉ có tệp hợp lệ của làn QA, **mọi** cổng cây sạch của wave trước
phải XANH; bộ lọc của từng cổng phải **miễn trừ vùng thử/tài liệu** và **KHÔNG** miễn trừ tệp sản
phẩm. Đo bằng dòng porcelain tổng hợp, không phụ thuộc trạng thái git thật:

```python
gia_lanh = ["?? docs/QA_G21.md", "?? app/thu/thu_qa_g21.py", "?? docs/G21_MEASURE_FIX.md"]
gia_ban  = ["?? app/webhook.py"]
# q17._loc_cay_ban(d, q17._mau_chot())   → []            (miễn trừ đúng)
# q18._loc_cay_ban(...)                  → []
# qb._loc_cay_ban(...)                   → []
# … cùng ba bộ lọc với gia_ban           → ["?? app/webhook.py"]   (KHÔNG miễn trừ sản phẩm)
```

Đo được sau sửa:

```
thu_qa_g17.py       → mã thoát 0 · XANH
thu_qa_g18.py       → mã thoát 0 · XANH
thu_g20_baomat.py   → mã thoát 0 · XANH
[G1] cổng cây sạch wave trước: 3/3 XANH · còn ĐỎ=0 · phán quyết=DONG
```

Cổng `cong-cay-sach` đổi đơn vị đo từ "số cổng XANH" (ghim 3) sang **"số cổng còn ĐỎ"** (nền 3 ·
đóng 0), đo bằng `len(CONG_CAY_SACH) - xanh` — thêm/bớt cổng không làm cổng ĐỎ vì lý do giả.

### 2.2 G2 — môi trường `GIT_CONFIG_*` dị dạng (N-G18-00)

**Sự thật cũ (STALE):** ca đo `git rev-parse HEAD` với môi trường **thừa hưởng** và ghim `128`
vào cổng sản phẩm. Trên máy này `env | grep GIT_CONFIG` cho:

```
GIT_CONFIG_COUNT=2
GIT_CONFIG_VALUE_0=false
GIT_CONFIG_VALUE_1=false
# KHÔNG có GIT_CONFIG_KEY_0 / GIT_CONFIG_KEY_1
```

Đây là lỗi **môi trường của máy** (docs/OWNER_ACTIONS §F; đo độc lập trong
`docs/G22_A1_GIT.md` §1.1a), không phải mã sản phẩm. Bộ chạy chung `chay_tat_ca.sh` đã tự gỡ
gia đình biến từ G18; `thu_qa_g17.py`/`thu_qa_g18.py`/`thu_g20_baomat.py` chuẩn hoá qua
`thu_g21_chotcay.env_git()`.

**Bất biến đúng, ba vế — cả ba đều được đo:**

| Vế | Phép đo | Kết quả |
|---|---|---|
| (1) Dị dạng ⇒ chuẩn hoá + cảnh báo | `thu_g21_chotcay.soi_gia_dinh_git(os.environ)` + `git` nguyên văn | `dị dạng=True` · `git nguyên văn=128` · cảnh báo N-G18-00 in ra |
| (2) Hợp lệ ⇒ KHÔNG gỡ | `COUNT=1, KEY_0=user.name, VALUE_0=g21-do` | `di_dang=False` · `env_git()` giữ nguyên `KEY_0`/`COUNT` |
| (3) Lỗi THẬT vẫn nổi lên | `chotcay._git("rev-parse","HEAD", goc=<thư mục không phải repo>)` | mã thoát ≠ 0 **và** có stderr |

```
[G2] môi trường máy: COUNT=2 · KEY_*=0 · VALUE_*=2 · dị dạng=True
     · git nguyên văn=128 · git đã chuẩn hoá=0 · git môi trường sạch=0 · phán quyết=DONG
```

Cổng `git-tho` nay đo `git` **sau chuẩn hoá** (0 = đóng). `128` vẫn là ô "nền" trong sổ, nhưng
nó là *triệu chứng môi trường*, không phải giá trị đem ra phán sản phẩm.

### 2.3 G3 — tầng 3 bàn phím: thiếu khai kho **và** số ca đã đổi

**Hai sự thật cũ, cả hai đều STALE:**

1. `do_tang_3()` chạy `app/migrate.py` mà **không khai kho**. Từ G22, `migrate.py` TỪ CHỐI khi
   chưa khai (`docs/G22_CAUHINH.md` §0) ⇒ Playwright **không được gọi** ⇒ 0 ca.
2. Kỳ vọng ghim `(7, 0, 0)` theo spec cũ. Spec hiện có **8** `test(...)`.

**Đã sửa:** `do_tang_3()` dựng môi trường bằng `_moi_truong_kho(nen)` → gọi
`cau_hinh.khai_kho_kiem_thu()` (từ chối nếu thư mục dữ liệu không cô lập). G3 **đọc số ca tại
chỗ** từ `thu_giao_dien/06_ban_phim.spec.js`:

```
[G3] tầng 3 bàn phím: mã thoát=0 · (đạt, hỏng, KHÔNG CHẠY)=(8, 0, 0) · bỏ qua=0 · spec khai 8 ca
     ca 04 vào được 13 điều khiển TRONG màn (đặc tả đòi > 10)
```

Cổng `tang3-ban-phim` đổi đơn vị đo từ bộ ba `(đạt, hỏng, không_chạy)` (ghim `(7,0,0)`) sang
**`hỏng + không_chạy`** (nền 4 · đóng 0); vế "đạt đủ số ca spec" và "ca 04 > 10" được khẳng định
riêng, nên **thêm ca vào spec không làm cổng ĐỎ giả**, còn **mất ca** vẫn bị bắt.

### 2.4 G4 — sao lưu: khai kho + đối chứng dương đi qua đường CHÍNH THỨC

**Hai sự thật cũ:**

1. `_dung_nen_du_lieu()` không khai kho ⇒ migrate từ chối ⇒ ca bị **SKIP**.
2. "Bản sao lưu LÀNH" cũ là `shutil.copy2` trần. Bản vá fail-closed G21/G22 bắt buộc
   `<tệp>.sha256` (`app/migrate.py::_kiem_ban_sao_luu`), nên bản copy2 **bị TỪ CHỐI theo đúng
   thiết kế** — nghĩa là đối chứng dương cũ đã sai, không phải sản phẩm sai.

**Đã sửa:** khai kho qua `_moi_truong_kho()`; đối chứng dương tạo bằng **chính `migrate.sao_luu()`**
(ghi kèm `.sha256`); thêm hai vế đối chứng cho chốt mới:

```
[G4] đầu vào ĐỘC HẠI được NHẬN (rc=0): 0/4
     rong-0-byte              rc=1 … CSDL sau={'so_bang': 52, 'tong_dong': 140, 'integrity': 'ok'}
     cat-cut-40-phan-tram     rc=1 …
     byte-0-magic-hong        rc=1 …
     khong-phai-sqlite-PGDMP  rc=1 …
     ĐỐI CHỨNG DƯƠNG: bản `sao_luu()` rc=0 · dữ liệu nguyên vẹn=True · nền sạch={52 bảng, 140 dòng, ok}
     ĐỐI CHỨNG ÂM: `copy2` không dấu kiểm bị TỪ CHỐI rc=1 · đường thoát rc=0 (dữ liệu nguyên vẹn=True)
```

---

## 3. G6 — LỖI THẬT, **KHÔNG SỬA CA**; ĐÃ TRUY ĐẾN CÙNG

Đề bài chỉ định: ca bắt **lỗi thật** thì **không sửa ca**, báo AG-00. Tôi giữ nguyên G6 và đo hai
tầng của lỗi:

### 3.1 `rc=3` — tầng THIẾT LẬP ĐO (harness không khai kho)

```sh
$ sh trien_khai/g18/chay_harness.sh
…
  ✗ migrate hỏng: [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …
# === mã thoát = 3
```

`trien_khai/g18/harness_tai.py` (dòng 634) chạy `migrate.py` mà **không** đặt
`VIP_KHO_DANG_CHAY`. Từ G22 đây là chốt fail-closed. Đây là **lỗi của harness** (và của cách bộ
đo gọi harness), **không phải lỗi của ca G6**: ca chỉ đọc mã thoát.

### 3.2 `rc=1` — tầng LỖI THẬT: **N-G20-01 vẫn mở**

Khi cấp đủ môi trường cho harness (nền tạm + khai `sqlite`), harness **chạy hết** nhưng vẫn ĐỎ:

```sh
$ VIP_HUB_DATA=$(mktemp -d) VIP_KHO_DANG_CHAY=sqlite sh trien_khai/g18/chay_harness.sh
…
  ✗ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
        HTTP=401 · Retry-After=None · X-RateLimit-Limit=None · X-RateLimit-Window=None
KẾT LUẬN: 16/20 ca đạt · 1 hỏng · 1 BLOCKED · 2 bỏ qua
# === mã thoát = 1
```

**Chuỗi nhân quả (đọc từ mã, không suy đoán):**

1. `trien_khai/g18/harness_tai.py` gọi `gioi_han.xoa_het()` ở chặng `G18-04b` (dòng ~876);
2. `app/gioi_han.py::xoa_het()` (dòng 337–340) xoá **TOÀN BỘ** `gioi_han_luot` + `gioi_han_chan`
   — kho đếm **DÙNG CHUNG** với tiến trình máy chủ;
3. bucket của `webhook.chu_ky_sai` vừa đầy ở `G18-04a` bị xoá sạch;
4. `G18-05` gửi lượt kế tiếp ⇒ đếm lại từ 1 ⇒ `401` thay vì `429`, không có `Retry-After`.

Đúng mô tả `N-G20-01` trong `docs/QA_G20.md` §6 / `docs/QA_G21.md` §2 (G6). `G21_GIOIHAN.md`
của làn AG-04 ghi rõ làn đó **không sửa `app/gioi_han.py`**, nên khoản nợ này **chưa có ai đóng**.

**Chủ sở hữu / đường đóng (đề nghị AG-00 giao):**

| Việc | Tệp | Chủ |
|---|---|---|
| Khai `VIP_KHO_DANG_CHAY=sqlite` cho nền tạm của harness (hoặc wrapper gọi nó) | `trien_khai/g18/chay_harness.sh` / `harness_tai.py` | AG-04 (G18/G21-gioihan) |
| `xoa_het()` chỉ xoá khoá của **chính nó**, hoặc harness dùng `dat_lai()` có phạm vi | `app/gioi_han.py` · `trien_khai/g18/harness_tai.py` | AG-02 (G19) + AG-04 |
| Quyết định mở/đóng N-G20-01 trong nghiệm thu G21 | — | **AG-00** |

**Không được đọc nhầm:** G6 ĐỎ **không** phải vì ca viết sai điều kiện. Ca đang đo đúng thứ nó
tuyên bố ("harness phải chạy HẾT và XANH") và đang bắt đúng một khoản nợ thật. Vì thế tôi **không**
thêm `VIP_KHO_DANG_CHAY` vào lời gọi harness trong ca G6: làm vậy sẽ **che** lỗi harness độc lập
(§3.1) và biến một cổng đỏ thật thành một cổng chỉ còn đỏ vì lý do khác.

---

## 4. BẰNG CHỨNG — LỆNH, MÃ THOÁT, SỐ CA

### 4.1 TRƯỚC khi sửa (nguyên văn dòng tổng kết)

```sh
$ VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
FAIL: test_g1_cong_cay_sach_wave_truoc … AssertionError: g17 không thấy tệp AG-01 G21 trong cây: []
FAIL: test_g2_git_voi_moi_truong_nguyen_ban … CỔNG `git-tho` ĐỎ: chế độ GỘP: khoản nợ 128 VẪN CÒN NGUYÊN
FAIL: test_g3_tang_3_ban_phim_trong_man … bộ đếm không đọc ra ca nào (migrate TỪ CHỐI vì CHƯA KHAI kho)
FAIL: test_g6_harness_gioi_han_tan_suat … NỬA VỜI — giá trị 3
FAIL: test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong … thiếu dương: ['cong-cay-sach']
test_g4_sao_luu_fail_closed ... skipped 'CHƯA ĐO: dựng nền hỏng: migrate.py → TỪ CHỐI: CHƯA KHAI kho'
Ran 24 tests in 19.863s
FAILED (failures=5, skipped=4)
# === EXIT CODE THẬT = 1
```

### 4.2 SAU khi sửa (nguyên văn dòng tổng kết)

```sh
$ VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
FAIL: test_g6_harness_gioi_han_tan_suat … CỔNG `harness-gioi-han` ĐỎ: NỬA VỜI — giá trị 3 …
Ran 24 tests in 69.769s
FAILED (failures=1, skipped=3)
# === EXIT CODE THẬT = 1   (một failure duy nhất: G6 — lỗi THẬT, không sửa ca)
```

Ba ca bỏ qua còn lại đều **theo thiết kế**, không phải che lỗi:

| Ca | Lý do bỏ qua | Có phải lỗ hổng phạm vi? |
|---|---|---|
| `H1` hồi quy toàn phần | chỉ chạy khi `VIP_G21_DAY_DU=1` | Không — làn đầy đủ, ngoài lệnh nghiệm thu này |
| `Z8` mồi ĐẠT cho T2 | chỉ chạy trong tiến trình con của T2 | Không — mồi tự kiểm |
| `Z9` mồi HỎNG cho T2 | chỉ chạy trong tiến trình con của T2 | Không — mồi tự kiểm |

### 4.3 Các số đo phụ (đều in ra trong lượt chạy)

```
[G1] 3/3 XANH · còn ĐỎ=0
[G2] git nguyên văn=128 · git đã chuẩn hoá=0 · git môi trường sạch=0 · dị dạng=True
[G3] mã thoát=0 · (8, 0, 0) · spec khai 8 ca · ca 04 = 13 điểm dừng
[G4] 0/4 nhận · sao_luu rc=0 · copy2 không dấu kiểm rc=1 · đường thoát rc=0
[G5] 0/5 tổ hợp rò
[G7] 1/2 bộ G19-tổng-hợp CHẠY THẬT (≥1 ⇒ ĐÓNG)
[G8] PHIEN_BAN_SCHEMA=9 · nang_len_v9=True · tệp SẢN XUẤT import truy_van=1
[Z1] 15 nhóm · 0 nhóm thiếu đối chứng dương
[Z2] git status ngoài các tệp được phép: RỖNG · vân tay không đổi
[Z3] 0 URL ngoài 127.0.0.1
```

`X1` (đối chiếu chéo với bộ G20) **không phán quyết**: nó ghi lại `thu_qa_g20.py` rc=1 với
`failures=7`. Con số này **khác baseline (6 → 7)** vì cây đang có thay đổi của làn này
(`app/thu/thu_qa_g21.py` + tệp tài liệu mới) và danh sách miễn trừ của bộ G20 **không chứa**
chúng; X1 chỉ ghi, **không** dùng mã thoát của G20 để phán. Không sửa bộ G20 (ngoài phạm vi).

---

## 5. CÒN LẠI — NÓI THẲNG

| # | Việc | Vì sao chưa đóng | Ai |
|---|---|---|---|
| 1 | **G6 ĐỎ** (`failures=1`, `EXIT=1`) | Lỗi thật N-G20-01 (`xoa_het()` xoá kho đếm dùng chung ⇒ G18-05 ĐỎ) + harness không khai kho theo G22. Đề bài chỉ định **không sửa ca**; hai tệp liên quan ngoài phạm vi ghi. | **AG-00** giao AG-04/AG-02 (bảng §3.2) |
| 2 | Làn đầy đủ `VIP_G21_DAY_DU=1` sẽ thấy `thu_qa_g21.py` là **bộ đỏ vô danh** trong `H1` | `NHOM_HONG_DA_BIET` chưa có nhóm cho G6; thêm nhóm là việc của AG-00 khi quyết định số phận khoản nợ (thêm nhóm sớm sẽ che mọi ca đỏ khác của chính tệp này). | AG-00 |
| 3 | Commit hai tệp | `.git` ở đây là tệp con trỏ ra **ngoài** workspace; tôi **không thử ghi** `.git` và **không** tự vượt sandbox. | Controller / AG-00 |
| 4 | `docs/QA_G21.md` (bản G21 cũ) chưa được cập nhật | Tệp của lượt G21, không nằm trong phạm vi ghi của dispatch này; các kết luận stale của nó (nền `a3400a8`, G6 rc=1) được thay bằng tệp này. | AG-00 |

---

## 6. TUÂN THỦ

- **Local-first**: mọi phép đo chạy trên máy, chỉ `127.0.0.1` với cổng OS cấp; **0** URL ra ngoài
  (`Z3` đo được 0; `A4` chỉ đọc `lsof` cụm `:5432`, không kết nối).
- **Không** push/deploy/tunnel; **không** gọi API hãng kể cả sandbox (`CHO_PHEP_LIVE=False`);
  **không** đụng PostgreSQL/CSDL thật; `migrate` chỉ chạy trên các `tempfile.mkdtemp()`.
- **Không** sửa `.git`; không xoá ca, không hạ ngưỡng, không `skipTest` để né lỗi: ca G4 từ SKIP
  chuyển thành **ĐO THẬT**, ca G3 từ 0 ca chuyển thành **8/8**.
- Mọi thay đổi nằm trong **đúng hai tệp** ở đầu tài liệu.

---

## 7. LỆNH TÁI LẬP

```sh
cd <worktree>
VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
# kỳ vọng: Ran 24 · PASS 20 · FAIL 1 (G6, lỗi thật) · SKIP 3 · EXIT 1

# riêng các ca đã sửa:
VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py G1_CaySach G2_GitTho
VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py G3_Tang3BanPhim G4_SaoLuu
```
