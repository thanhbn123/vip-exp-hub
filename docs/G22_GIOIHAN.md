# G22 — ĐIỂM VƯỚNG **TÊN TỆP** CỦA CỔNG C5/G7: ĐO HAI CHIỀU QUA CHÍNH C5

Làn **AG-04** · wave **G22** · cây `g21-ag04-gioihan`
Nền: `integration/g21` · **HEAD đo được: `9ded4a5cee269c02998a0d0181051e3ed1de720b`**
`main` = `de740dc` (**KHÔNG** chứa G13–G22) — không dùng.

| Tệp | sha256 | Vai |
|---|---|---|
| `app/thu/thu_g19_tich_hop.py` | `ea0fe8646714de67fa2a7be1fd19993c237cc8cd992ba86e6352248ebfc4b86c` | **MỘT bản logic** — cổng tổng hợp G19 (8 ca tự kiểm + gọi runner thật) |
| `app/thu/thu_qa_g19_tich_hop.py` | `bcd440e34d292d6d519b5291b253193f24849baa4b05bf4bd5db571856d6eeea` | **Bản uỷ quyền MỎNG** — tên tệp khớp khuôn C5/G7, **không** chứa logic thứ hai |
| `app/thu/thu_g22_gioihan.py` | `775b860092127389bf4310fb62ee9500b1f61b9925dc41203b148352f5a506d5` | Cổng G22 — đo hai chiều **qua chính C5** |
| `trien_khai/g21-gioihan/chay_g22.sh` | `e392c1daa1b53b58dce424eb2f8a2ddc0f74c1202a948f52417fcfad350aee39` | Bộ chạy G22 (log ra thư mục tạm · in mã thoát trước mọi pipe) |
| `docs/G22_GIOIHAN.md` | *(tệp này)* | Báo cáo |

---

## 1. Điểm vướng — và nó **KHÔNG** nằm ở chỗ tưởng

Đề bài lượt này phát biểu: *"C5 vẫn đỏ 0/1 vì sai tên tệp — **bộ đếm của `chay_tat_ca.sh`** không
nhận ra tệp của bạn."* Tôi **đo trước khi tin**, và nửa sau của câu đó **SAI**:

```
$ grep -n "find app/thu gateway/thu" app/thu/chay_tat_ca.sh
for t in $(find app/thu gateway/thu -name 'thu_*.py' -type f ! -name 'thu_e2e.py' | sort); do
```

Bộ đếm của `chay_tat_ca.sh` dò theo `-name 'thu_*.py'` — **`thu_g19_tich_hop.py` khớp khuôn đó**,
và nó **đã được đếm từ lượt trước**: `✓ thu_g19_tich_hop.py  8 ca` (xem §5, cả TRƯỚC lẫn SAU).
Vậy chỗ vướng thật nằm ở một bộ đếm KHÁC.

Bộ đếm thật của **C5** nằm trong tệp của AG-01, và nó đếm bằng **KHUÔN TÊN**, không bằng nội dung:

```
app/thu/thu_qa_g20.py:710-712   (cổng C5)
    ung_vien = sorted(t for t in os.listdir(GOC_THU)
                      if re.match(r"thu_qa_g19.*\.py$", t))
app/thu/thu_qa_g21.py:899       (cổng G7 — cùng một khuôn, bản sao)
```

`re.match` neo ở **ĐẦU** chuỗi, nên `app/thu/thu_g19_tich_hop.py` **không bao giờ** khớp
`thu_qa_g19.*\.py$`. Đo được (G22/B1, đọc từ chính mã nguồn AG-01 rồi chạy trên `app/thu` thật):

```
nguồn bộ kiểm AG-01 (chỉ ĐỌC): …/g20-ag01-qa/app/thu/thu_qa_g20.py
sha256: 5a4b3c83c45f2f2c465d2eed380f1f6f
✓ B1a  Bộ đếm của C5 dùng KHUÔN TÊN `thu_qa_g19.*\.py$` trên `os.listdir(app/thu)`
ứng viên C5 thấy trên cây này (2): ['thu_qa_g19.py', 'thu_qa_g19_tich_hop.py']
✓ B1b  Bản uỷ quyền `thu_qa_g19_tich_hop.py` NẰM TRONG danh sách ứng viên của C5
✓ B1c  Bộ gốc `thu_g19_tich_hop.py` KHÔNG khớp khuôn
       `re.match(r'thu_qa_g19.*\.py$', 'thu_g19_tich_hop.py')` → False
```

**Đây là lỗi ĐẶT TÊN, không phải lỗi sản phẩm.** Phép đo của C5 đúng; chỉ có chỗ nó nhìn là trống.

Vì sao C5 vẫn đỏ dù đã có ứng viên: `thu_qa_g19.py` (tệp của AG-01) **tự bỏ qua** vì HEAD không
khớp nền đóng băng, và nó in `Ran 0 tests` + `OK (skipped=1)` + thoát 0 ⇒ `n = 0` ⇒ không tính.

---

## 2. Cách chốt: bản uỷ quyền MỎNG, không nhân đôi logic

Lượt trước tôi dựng thử một bản uỷ quyền 23 dòng rồi **XOÁ** — đúng, vì khi đó tệp nằm **ngoài
vùng được cấp**. Lượt này tôi **ĐO RỒI HỎI** thay vì tự vượt (đây là lần thứ ba liên tiếp một điểm
vướng ownership của làn này được gỡ bằng đo-rồi-hỏi). AG-00 chốt: cấp tường minh
`app/thu/thu_qa_g19_tich_hop.py` cho AG-04, đã báo AG-01 + AG-05 **không sửa trùng**, và yêu cầu
đây là **bản uỷ quyền mỏng, KHÔNG phải bản logic thứ hai**.

Ba chốt của tệp uỷ quyền:

1. **MỘT bản logic duy nhất.** Nó chạy `app/thu/thu_g19_tich_hop.py` trong tiến trình con, in
   NGUYÊN VĂN stdout+stderr, rồi **thoát bằng ĐÚNG mã thoát của bộ gốc**. Không viết lại, không
   nuốt, không đổi thành 1.
2. **Không mất bảo đảm nào.** Vì mã thoát chuyển nguyên văn, cả 8 ca tự kiểm của bộ gốc còn nguyên
   hiệu lực. Tệp uỷ quyền chỉ **thêm** một chỗ siết: bộ gốc **không tồn tại** ⇒ trả `127` +
   in `KHÔNG CHẠY ĐƯỢC` (không được thoát 0).
3. **Không nới điều kiện, không bịa số.** Không sửa `thu_qa_g20.py`/`thu_qa_g21.py` (tệp AG-01),
   không sửa `chay_tat_ca.sh`, và **không tự in dòng `Ran N tests` hay `N ca — ĐẠT` giả** — in
   khống khuôn của bộ đếm là làm bộ đếm đọc một con số không do phép đo nào sinh ra.

---

## 3. ĐO HAI CHIỀU **QUA CHÍNH C5** — không qua runner

Chạy `thu_g19_tich_hop.py` rồi tự khen nó xanh là **vô nghĩa**: đó là đối chứng dương của chính bộ
đo, không phải của cổng C5. Nên mọi phép đo dưới đây gọi **CHÍNH phương thức của C5** —
`C4_C5_NoKhac.test_c5_co_bo_thu_g19_tong_hop_chay_duoc` trong tệp AG-01 — ở chế độ
`VIP_G20_CHE_DO=gop`, và đọc **câu cổng tự in ra**.

### 3.1 Chiều XANH — và đối chứng âm của chính nó

| Trạng thái `app/thu/thu_qa_g19_tich_hop.py` | Câu C5 tự in | Mã thoát | Phán |
|---|---|---|---|
| **BỎ RA** (đổi tên thành tệp chấm-đầu) | `0/1 · phán quyết=chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN` | **1** | **ĐỎ** |
| **CÓ MẶT** (bản uỷ quyền lành) | `1/2 · phán quyết=DONG` | **0** | **XANH** |

Nguyên văn (đo cùng lượt, cùng cây):

```
       thu_qa_g19.py → mã thoát 0 · 0 ca
  [C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: 0/1 · phán quyết=chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN
EXIT_C5_KHONG_CO_BAN_UY_QUYEN=1
── TRẢ LẠI ──
bản uỷ quyền: có · sha256 bcd440e34d292d6d519b5291b253193f24849baa4b05bf4bd5db571856d6eeea
KHỚP sha256 TRƯỚC
bản sao AG-01: đã xoá
tệp tạm: không còn
```

```
       thu_qa_g19.py → mã thoát 0 · 0 ca
       thu_qa_g19_tich_hop.py → mã thoát 0 · 8 ca
  [C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: 1/2 · phán quyết=DONG
```

⇒ **Bản uỷ quyền CHÍNH LÀ thứ làm C5 chuyển xanh** — không phải trùng hợp, không phải nới điều
kiện. Tỷ lệ đúng là **`1/2`** (không phải `1/1`): `ung_vien` nay có **HAI** tệp — `thu_qa_g19.py`
của AG-01 (tự bỏ qua ⇒ 0 ca) và bản uỷ quyền của tôi. Điều kiện của C5 là **tử số ≥ 1**.

### 3.2 Chiều ĐỎ — năm phép tiêm lỗi, mỗi phép ĐÚNG MỘT DÒNG, đo qua chính C5

Bản gốc giữ trong bộ nhớ, trả lại trong `finally` + `atexit`, **đối chiếu sha256** sau mỗi phép.

| # | Phép tiêm (1 dòng) | Hình dạng bộ gốc in ra | C5 phán | Kỳ vọng |
|---|---|---|---|---|
| — | (không tiêm) bản uỷ quyền lành | `Ran 8 tests` + `OK` + thoát 0 | **`1/2 · DONG`** · exit 0 | XANH ✓ |
| a | `return [… "-c", "import sys; sys.exit(7)"]` | thoát **7**, không có `Ran` | **`0/2`** · exit 1 | ĐỎ ✓ |
| b | `BO_THU = … "thu_g19_khong_ton_tai_GIA.py"` | uỷ quyền tự trả **127** + `KHÔNG CHẠY ĐƯỢC` | **`0/2`** · exit 1 | ĐỎ ✓ |
| c | suite RỖNG | `Ran 0 tests` + `OK` + thoát 0 | **`0/2`** · exit 1 | ĐỎ ✓ |
| d | MỌI CA BỎ QUA ở mức **PHƯƠNG THỨC** (`@unittest.skip`) | `Ran 3 tests` + `OK (skipped=3)` + thoát 0 | **`1/2 · DONG`** · exit 0 | ĐỎ ✗ **LỖ HỔNG** |
| d′ | MỌI CA BỎ QUA ở mức **MÔ-ĐUN** (`setUpModule` ném SkipTest) | `Ran 0 tests` + `OK (skipped=1)` + thoát 0 | **`0/2`** · exit 1 | ĐỎ ✓ |

Tổng kết cổng G22: **`ca ĐẠT=15 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=1 · TỔNG=16`** · **exit 1** ·
169.4 giây. Sổ đối chứng: `khuon-ten âm=1 dương=2` · `c5-chieu-xanh âm=1 dương=1` ·
`c5-chieu-do âm=4 dương=1` · `khuon-bao-cao âm=1 dương=1` · `chot-an-toan âm=1 dương=1` —
**không nhóm ÂM nào thiếu DƯƠNG**.

> **Vì sao cổng G22 vẫn ĐỎ (exit 1) dù bản uỷ quyền chạy đúng.** Chỗ `KHUYẾT` là `N-G22-01` —
> một **lỗ hổng của bộ đếm C5**, không phải của bản uỷ quyền. Yêu cầu (ii) của đề bài
> (*"tiêm lỗi vào bản sao ⇒ C5 PHẢI ĐỎ lại"*) **không đúng với mọi hình dạng tiêm lỗi**: hàng `d`
> cho thấy C5 vẫn XANH. Một cổng biết có ca ÂM không giữ được mà vẫn thoát 0 là **xanh giả** —
> đúng thứ dự án này cấm. Nên nó ĐỎ, và nó **nói rõ lý do** thay vì gộp vào một dòng HỎNG chung.

### 3.3 `N-G22-01` — **lỗ hổng ĐO ĐƯỢC của cổng C5** (mức: TRUNG BÌNH, đang TIỀM ẨN)

C5 tự khai hợp đồng: *"phải có ÍT NHẤT một bộ G19-tổng-hợp **CHẠY THẬT**"*. Nhưng luật phán chỉ là:

```python
m = re.findall(r"Ran (\d+) tests?", ra)
n = int(m[-1]) if m else 0
chay = min(sum(1 for _, ma, n in chi_tiet if ma == 0 and n > 0), 1)
```

`unittest` in `Ran N tests` với **N = số ca ĐÃ NẠP**, kể cả ca bị `@unittest.skip`. Nên một bộ mà
**mọi ca đều bỏ qua** vẫn cho `ma == 0` và `n > 0` ⇒ C5 phán **XANH**. Đo được ở hàng `d`: C5 in
`1/2 · DONG` trong khi bộ được đo **không chạy ca nào**.

**Hiện TIỀM ẨN, không đang hoạt động**: trên cây này chỉ `thu_qa_g19.py` khớp khuôn tên, và nó bỏ
qua ở mức **MÔ-ĐUN** (⇒ `Ran 0 tests`, an toàn). Lỗ hổng chỉ kích hoạt nếu có tệp `thu_qa_g19*.py`
bỏ qua ở mức **phương thức** — ví dụ ai đó thêm `@unittest.skipUnless(...)` cho từng ca.

Đây đúng là khuôn "xanh giả" mà chính `chay_tat_ca.sh` đã có luật chặn (*"BỎ QUA là phán quyết
THỨ BA, không gộp vào ĐẠT"*) — C5 và G7 thì chưa.

**Bản vá đề xuất (2 dòng, tệp của AG-01, tôi KHÔNG tự sửa):**

```python
m  = re.findall(r"Ran (\d+) tests?", ra)
n  = int(m[-1]) if m else 0
sk = re.findall(r"skipped=(\d+)", ra)                 # THÊM
n -= int(sk[-1]) if sk else 0                         # THÊM: trừ ca BỎ QUA
chay = min(sum(1 for _, ma, n in chi_tiet if ma == 0 and n > 0), 1)
```

Áp cho **cả hai** tệp: `thu_qa_g20.py` (C5) và `thu_qa_g21.py` (G7 — khuôn y hệt).

### 3.4 Một phép tiêm của TÔI đã SAI, và tôi ghi lại cái sai đó

Bản đầu của phép tiêm `d′` gán `setUpModule` lên **class** rồi gọi `loadTestsFromTestCase`. Nhưng
`unittest` chỉ chạy mô-đun-fixture qua `loadTestsFromModule`, nên phép tiêm đó **không bỏ qua ca
nào** — đo lại được `Ran 1 test` + `OK`, tức ca vẫn CHẠY. Kết quả khi đó (C5 xanh) là do **phép
tiêm hỏng**, KHÔNG phải lỗ hổng của C5. Ghi nhầm nó thành lỗ hổng của AG-01 là **vu oan**. Đã sửa
phép tiêm và đo lại; dòng `d′` trong bảng trên là kết quả của bản **đã sửa**.

### 3.5 `N-G22-02` — khuôn báo cáo: bộ đếm lấy dòng **CUỐI**

`chay_tat_ca.sh` lấy `grep -oE 'Ran [0-9]+' | tail -1`; C5/G7 lấy phần tử **cuối** của
`re.findall`. Nghĩa là: **dòng `Ran N tests` cuối cùng phải là con số THẬT**. G22/B5 đo cái bẫy:

```
✓ B5a  Bộ đếm QUẢ THẬT mù được bởi một dòng `Ran` in SAU (bẫy: 12 ca ⇒ đọc ra 0)
✓ B5b  Cùng bộ đếm, output SẠCH ⇒ đọc ĐÚNG 12 ca (đối chứng dương của B5a)
✓ B5.thu_g19_tich_hop.py      mã thoát 0 · 57.2s · bộ đếm đọc 8 ca · dấu vết OK=True
✓ B5.thu_qa_g19_tich_hop.py   mã thoát 0 · 52.3s · bộ đếm đọc 8 ca · dấu vết OK=True
```

Hai việc đã làm để bịt mặt này **trong phạm vi được cấp**:

1. `thu_g19_tich_hop.py`: docstring của ca `(c)` **in ra** dưới `verbosity=2` có chứa một dòng
   khuôn — một **DÒNG MỒI** nằm trước con số thật. Đã viết lại để không còn chữ số nào trong đó.
2. `thu_g19_tich_hop.py` nay **TỰ ĐỌC LẠI toàn bộ stdout của chính nó** (qua một `_Tee`) và khẳng
   định con số cuối cùng đúng bằng số ca tự kiểm thật; lệch ⇒ thoát `3` (tự kiểm hỏng). Đo được:

```
TỰ KIỂM KHUÔN BÁO CÁO: 1 lần khớp `Ran <số> tests?` · lần CUỐI = 8 · số ca tự kiểm thật = 8 ⇒ KHỚP
```

Toàn bộ output của bản uỷ quyền chỉ còn **ĐÚNG MỘT** dòng khớp `Ran [0-9]+` — con số thật:

```
$ python3 app/thu/thu_qa_g19_tich_hop.py    →   EXIT=0
$ grep -oE 'Ran [0-9]+' <output>            →   1 lần: "Ran 8"
```

---

## 4. Đo lại C5 bằng CHÍNH bộ kiểm AG-01 ở chế độ `gop`

`thu_qa_g20.py` được chép **TẠM** từ worktree `g20-ag01-qa` vào `app/thu/`, chạy, rồi **XOÁ** và
khẳng định đã xoá (mọi thứ nằm trong `trap` của `sh`). Nguồn:
`sha256 = 5a4b3c83c45f2f2c465d2eed380f1f6f…`

```
$ VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
…
       thu_qa_g19.py → mã thoát 0 · 0 ca
       thu_qa_g19_tich_hop.py → mã thoát 0 · 8 ca
  [C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: 1/2 · phán quyết=DONG
…
Ran 21 tests in 134.767s
EXIT_BO_KIEM_AG01=1
[DỌN] đã xoá …/app/thu/thu_qa_g20.py — còn lại: KHÔNG
```

**Trả lời câu hỏi "C5 còn ĐỎ hay đã XANH": `C5` đã chuyển từ `0/1` (ĐỎ) sang `1/2 · DONG`
(XANH)** — và xanh vì một bộ **chạy thật 8 ca**, không phải vì nới điều kiện.

Mã thoát của **cả bộ kiểm AG-01** vẫn là `1`, do **bảy cổng khác của chính nó** đỏ trên cây này —
**không** cổng nào trong số đó đỏ vì bản uỷ quyền của tôi (xem §7). Dòng `… ok` của `C5` nằm trong
số ít cổng xanh.

---

## 5. Bộ chạy chung `chay_tat_ca.sh` — TRƯỚC / SAU

Cùng cây, cùng HEAD, chỉ khác **hai tệp mới** của lượt này. Lệnh: `sh app/thu/chay_tat_ca.sh`.

| | **TRƯỚC** | **SAU** |
|---|---|---|
| `thu_g19_tich_hop.py` | `✓ 8 ca` | `✓ 8 ca` |
| `thu_g21_gioihan.py` | `✓ 22 ca` | `✓ 22 ca` |
| `thu_qa_g19_tich_hop.py` | *(chưa có)* | **`✓ 8 ca`** |
| `thu_g22_gioihan.py` | *(chưa có)* | `✗ 0 ca  HỎNG (mã thoát 1)` — vì `N-G22-01` |
| `thu_qa_g19.py` | `⊘ BỎ QUA (0 ca)` | `⊘ BỎ QUA (0 ca)` |
| python **TỔNG** | **1900 ca · 53 bộ chạy thật** + 1 BỎ QUA | **1908 ca · 55 bộ chạy thật** + 1 BỎ QUA |
| frontend | `56 + 36 ca` | `56 + 36 ca` |
| E2E | `KẾT QUẢ: 41/41` | `KẾT QUẢ: 41/41` |
| bộ hỏng | `thu_g20_baomat.py` `thu_qa_g17.py` `thu_qa_g18.py` | `thu_g20_baomat.py` **`thu_g22_gioihan.py`** `thu_qa_g17.py` `thu_qa_g18.py` |
| mã thoát | `1` | `1` |

**Chênh lệch: `+8 ca` · `+2 bộ dò được`.** Con số `+8` **đúng bằng** số ca của bản uỷ quyền
(`thu_qa_g19_tich_hop.py ✓ 8 ca`) — tức bộ chạy chung **đếm thêm ĐÚNG số ca của làn này**, và
frontend/E2E **không đổi một ca nào** ⇒ không hồi quy.

### 5.1 `N-G22-03` — bộ chạy chung KHÔNG có khuôn cho "N ca — HỎNG"

`thu_g22_gioihan.py` đo **16 ca** nhưng bộ chạy chung ghi **0 ca**, vì hai khuôn nó chấp nhận là
`Ran [0-9]+` (của `unittest`) và `[0-9]+ ca — ĐẠT` (của bộ viết tay) — **không có khuôn nào cho
"N ca — HỎNG"**. Nên một bộ viết tay ĐỎ bị đếm 0 ca, còn một bộ `unittest` ĐỎ
(`thu_g20_baomat.py`) vẫn được đếm 27 ca. Bất đối xứng này làm TỔNG **hụt** đúng phần việc đã chạy
nhưng đỏ. **Không thuộc vùng được cấp của tôi** ⇒ ghi lại, không sửa.

---

## 6. Cái NẰM NGOÀI phạm vi — và vì sao tôi KHÔNG tự sửa

### 6.1 Rác của làn AG-04 làm đỏ cổng "cây sạch" của các wave trước

`thu_qa_g17.py` · `thu_qa_g18.py` · `thu_g20_baomat.py` đỏ, và **cả ba** vì cùng một lý do:

```
AssertionError: Lists differ: [' M docs/G21_GIOIHAN.md', ' M trien_khai/g21-gioihan/README.md',
 '?? app/thu/thu_g19_tich_hop.py', '?? app/thu/thu_g22_gioihan.py',
 '?? app/thu/thu_qa_g19_tich_hop.py', '?? docs/G22_GIOIHAN.md',
 '?? trien_khai/g21-gioihan/chay_g22.sh'] != []
```

Đây là họ lỗi `N-G19-03`/`N-G18-03` đã ghi trong dự án: danh sách miễn trừ của mỗi wave là **đích
danh** và không chứa tệp của làn AG-04. **Hai trong ba tệp đã bẩn từ TRƯỚC lượt này**
(`docs/G21_GIOIHAN.md`, `trien_khai/g21-gioihan/README.md` + `app/thu/thu_g19_tich_hop.py`) ⇒
cổng đã đỏ sẵn; lượt này chỉ **thêm** vào danh sách, không đổi phán quyết.

Ba tệp đó **KHÔNG thuộc vùng được cấp của tôi** ⇒ tôi **ĐO, GHI LẠI, KHÔNG SỬA**. Cách sửa rẻ
nhất — nới miễn trừ — chính là nước đi mà **ba cổng tự kiểm của chúng đã dựng ra để CHẶN**
(`test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu`).

### 6.2 Cổng C1/Z2 của AG-01 **BẤT KHẢ THI** khi làn AG-04 còn tệp chưa `git add`

```
FAIL: test_g1_cong_cay_sach_wave_truoc_khong_do_vi_tep_AG01_hop_le
AssertionError: … : miễn trừ đúng hai tệp mà g17 vẫn báo bẩn ⇒ giá trị 'đóng' BẤT KHẢ THI
FAIL: test_z2_cay_khong_doi_ngoai_hai_tep_duoc_phep
AssertionError: cây có thay đổi NGOÀI hai tệp AG-01 G20: [7 tệp]
```

`Z2` đòi vân tay cây **chỉ** đổi ở đúng hai tệp của AG-01. Trong một repo chạy **nhiều làn song
song**, điều đó **không thể đạt** khi làn khác còn tệp chưa commit. Đây là **quyết định của AG-00**
(gộp rồi commit, hoặc khai đích danh tệp AG-04 vào miễn trừ của từng wave) — không phải việc tôi
tự làm.

### 6.3 Bốn cổng AG-01 đỏ vì nợ của chính wave G20 — **không liên quan tới làn này**

| Cổng | Đo được | Nguyên nhân |
|---|---|---|
| `C2` | `(3, 1, 3)` VẪN CÒN NGUYÊN | tầng 3 `06_ban_phim.spec.js`: ca 04 chỉ vào được 1 điều khiển TRONG màn (đặc tả đòi > 10) |
| `C3` | `9ded4a5…` ≠ `148ecd3…` | `git` gọi với môi trường NGUYÊN BẢN: `GIT_CONFIG_COUNT=2` thiếu `KEY_*` (N-G18-00) và HEAD đã trôi khỏi nền đóng băng |
| `C4` | `(True, False)` VẪN CÒN NGUYÊN | `PHIEN_BAN_SCHEMA=9` + `nang_len_v9=True` nhưng **0** tệp SẢN XUẤT import `truy_van` |
| `Z1` | thiếu dương: `['cong-cay-sach', 'git-tho']` | sổ đối chứng của chính bộ AG-01 |

---

## 7. CÒN LẠI / BLOCKED

| # | Việc | Chủ | Trạng thái |
|---|---|---|---|
| `N-G22-01` | C5/G7 không trừ `skipped=N` ⇒ một bộ chạy **0 ca** vẫn XANH | **AG-01** | **MỞ** — bản vá 2 dòng ở §3.3, áp cho cả `thu_qa_g20.py` và `thu_qa_g21.py` |
| `N-G22-03` | `chay_tat_ca.sh` không có khuôn `N ca — HỎNG` ⇒ bộ viết tay ĐỎ bị đếm 0 ca | **AG-00** | **MỞ** — §5.1 |
| §6.1 | Ba cổng cây sạch đỏ vì rác làn AG-04 | **AG-00** | **MỞ** — cần commit, hoặc khai đích danh |
| §6.2 | `C1`/`Z2` của AG-01 bất khả thi khi làn khác còn tệp chưa commit | **AG-00** | **MỞ** |
| §6.3 | Bốn cổng nợ G20 của AG-01 | **AG-01** | **MỞ** — ngoài phạm vi làn này |

**TỰ ĐÁNH GIÁ:** phần **được giao** của lượt này đã xong và **đo được hai chiều** — C5 chuyển
`0/1` → `1/2 · DONG`, và bốn hình dạng tiêm lỗi làm nó ĐỎ lại, tất cả **qua chính C5**. Chỗ
**chưa xanh** là `N-G22-01`, một **lỗ hổng của bộ đếm AG-01** mà tôi **không có quyền sửa**; cổng
G22 vì thế **cố ý thoát 1** thay vì tự nới điều kiện cho qua.
