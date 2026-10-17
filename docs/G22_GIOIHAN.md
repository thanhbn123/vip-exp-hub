# G22 — ĐIỂM VƯỚNG **TÊN TỆP** CỦA CỔNG C5/G7: ĐO HAI CHIỀU QUA CHÍNH C5

Làn **AG-04** · wave **G22** · cây `g21-ag04-gioihan`
Nền: `integration/g21` · **HEAD đo được: `9ded4a5cee269c02998a0d0181051e3ed1de720b`**
`main` = `de740dc` (**KHÔNG** chứa G13–G22) — không dùng.
Lượt **AG-04 MỚI** (§8): **HEAD `44314301ed01223bb15108e2685aff8878802cc2`** + 2 tệp của lượt này (chưa commit)
— cây này **CHƯA** gộp hợp đồng §1 của AG-02 (xem §8.7).

| Tệp | sha256 | Vai |
|---|---|---|
| `app/thu/thu_g19_tich_hop.py` | `ea0fe8646714de67fa2a7be1fd19993c237cc8cd992ba86e6352248ebfc4b86c` | **MỘT bản logic** — cổng tổng hợp G19 (8 ca tự kiểm + gọi runner thật) |
| `app/thu/thu_qa_g19_tich_hop.py` | `bcd440e34d292d6d519b5291b253193f24849baa4b05bf4bd5db571856d6eeea` | **Bản uỷ quyền MỎNG** — tên tệp khớp khuôn C5/G7, **không** chứa logic thứ hai |
| `app/thu/thu_g22_gioihan.py` | `a4191fa41c9be50f6e4f8bb518598fbfb502ae80cbdb4206a54f6ef107cdbade` | Cổng G22 — đo hai chiều **qua chính C5**, + khối `B7` (hợp đồng tenant · phủ tuyến · phân trang — §8) |
| `trien_khai/g21-gioihan/chay_g22.sh` | `e392c1daa1b53b58dce424eb2f8a2ddc0f74c1202a948f52417fcfad350aee39` | Bộ chạy G22 (log ra thư mục tạm · in mã thoát trước mọi pipe) |
| `trien_khai/g21-gioihan/chay_hopdong.sh` | `09439ca17d758713851c768540b0511963dc07e81b84f7213e96f220fcf76d4c` | Bộ chạy khối `B7` trên **HAI CÂY** (đối chứng ÂM/DƯƠNG) — §8 |
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

---

## 8. LƯỢT AG-04 MỚI — HỢP ĐỒNG TENANT + PHỦ TUYẾN + PHÂN TRANG (khối `B7`)

> Supervisor giao thẳng: **KHÔNG nhận `assertIn(200, 400)`**. Một điều kiện nhận cả `200` LẪN `400`
> là điều kiện **không phân biệt được hai hành vi trái ngược nhau** — trong đó một hành vi
> (`200` = máy chủ **bỏ qua im lặng** tham số chọn tenant) chính là dạng hỏng mà cả nhiệm vụ G12
> sinh ra để diệt. Nên lượt này mỗi vế là **MỘT mã**, và mỗi vế ÂM đều có vế DƯƠNG.

Hợp đồng đóng băng của AG-02: `docs/G22_TRUYVAN.md` §1 (bản ở làn `g21-ag02-backup` — làn này
**chưa** có tệp đó; xem §8.7). Cây đo: HEAD **`4431430`** + hai tệp của lượt này (chưa commit).

### 8.1 Fixture và cách đo — ba thứ KHÔNG được lẫn

| Thành phần | Làm thế nào | Vì sao không được làm khác |
|---|---|---|
| **CSDL** | SQLite trong thư mục `tempfile` do chính bộ đo dựng; `python3 app/migrate.py` chạy THẬT trên thư mục đó | **D-8**: KHÔNG migration CSDL nghiệp vụ. Bộ đo **TỪ CHỐI ĐO (mã thoát 9)** nếu `cau_hinh.DUONG_DAN_CSDL` không nằm trong thư mục tạm |
| **Dữ liệu** | Hai tenant A/B dựng bằng **CHÍNH `don_hang.tao_don`** của sản phẩm: A = 60 đơn (một **đơn MỐC** `cod=900000111`, `nguoi_nhan_ten` chứa `A-MOC`), B = 1 đơn | `don_hang` có 40 cột sau v7 — fixture tự chế ba cột thì không bắt được lỗi nào thuộc cột thứ tư |
| **Phủ tuyến** | Bộ đếm cắm vào `truy_van.chay` / `truy_van.tim_don` **TRONG CHÍNH TIẾN TRÌNH CÓ MÁY CHỦ**, rồi bắn HTTP thật (`127.0.0.1`, cổng do hệ điều hành cấp) | Đọc mã nguồn chỉ nói tên mô-đun **có xuất hiện**; nó không chứng minh đường ấy **đi qua**. Tệp nguồn chỉ dùng để biết CẦN DÒ những đường nào |

CSDL nghiệp vụ được **đọc dấu vân tay** (`sha256` · `mtime` · cỡ) TRƯỚC và SAU; lệch là HỎNG (ca
`B7o`). Cây đối chứng được đo **CHỈ ĐỌC** (`PYTHONDONTWRITEBYTECODE=1`) — đã kiểm: **không** rơi
`__pycache__` vào cây AG-02.

Lệnh chạy lại (hai cây, một lệnh):

```sh
sh trien_khai/g21-gioihan/chay_hopdong.sh        # cây nhà (ÂM) + cây AG-02 (DƯƠNG), in cả hai bảng
python3 app/thu/thu_g22_gioihan.py               # cây nhà, đầy đủ B0…B7
VIP_G22_CAY_APP=<cây>/app python3 app/thu/thu_g22_gioihan.py   # đo CHỈ ĐỌC trên cây khác
```

### 8.2 Bằng chứng: **mã thoát · số ca · số bỏ qua** — HAI CÂY

| Cây đo | Lệnh | **Mã thoát** | Số ca | ĐẠT | HỎNG | **BỎ QUA** | KHUYẾT | Thời gian |
|---|---|---|---|---|---|---|---|---|
| **Cây nhà** (`4431430` + 2 tệp lượt này) | `python3 app/thu/thu_g22_gioihan.py` | **1** | **32** | 22 | **8** | **0** | **2** | 168,4 s |
| **Cây đối chứng** (làn AG-02, tuyến đã cắm) | `VIP_G22_CAY_APP=…/g21-ag02-backup/app python3 …` | **0** | **20** | **19** | **0** | **1** | **0** | 1,0 s |

* **8 HỎNG ở cây nhà = 8 GHIM HỢP ĐỒNG** (`B7c`·`B7d`·`B7e`·`B7f`·`B7g`·`B7h`·`B7i`·`B7p`), và cả 8
  đều **XANH trên cây đối chứng** ⇒ chúng đo **đúng thứ cần đo**, không phải cổng đỏ mù.
* **2 KHUYẾT**: `B3.d` (**`N-G22-01`** — lỗ hổng bộ đếm của AG-01, đã ghi ở §3) và `B7n`
  (**hợp đồng §1 chưa được cắm vào cây này** — xem §8.6/§8.7).
* **1 BỎ QUA ở cây đối chứng** là `B.cay-khac`: lượt đo cây khác **cố ý** không chạy lại B1–B5
  (C5/G7 là phép đo của **cây này**; chạy lại trên cây khác là đo nhầm đối tượng). Nó **không**
  phải một ca đạt — và vì thế nó nằm ở cột BỎ QUA, không nằm ở cột ĐẠT.
* `sh trien_khai/g21-gioihan/chay_hopdong.sh` → **`exit 0`**: runner chỉ xanh khi cặp kết quả ĐÚNG
  kỳ vọng (nhà `1` · đối chứng `0`). Một cây đối chứng đỏ = phép đo sai **hoặc** hợp đồng bị vi
  phạm — cả hai đều phải đỏ, nên runner không được phép xanh. Log: `${TMPDIR}/veh_g22_ag04/`.
* **Vá thêm trong lượt này (đã vấp thật):** hai lượt chạy ĐỒNG THỜI trên cùng một cây tranh nhau
  tệp mượn `app/thu/thu_qa_g20.py` ⇒ lượt tới muộn chết vì `FileNotFoundError` **trước khi** tới
  `B7`. Nay chỗ mượn tệp ném `LoiMuonBanSao` **nói rõ nguyên nhân**, phần B1–B5 được bọc lại
  (một sự cố MÔI TRƯỜNG ở đó ghi thành KHUYẾT rồi **vẫn chạy tiếp `B7`**), và bản sao DỞ bị xoá
  thay vì để lại rác.

### 8.3 BẢNG TENANT A/B (fixture SQLite TẠM — không dữ liệu thật)

```
  ┌ BẢNG TENANT A/B — fixture SQLite TẠM (`…/T/g22-ag04-hopdong-<ngẫu nhiên>/hub.db`)
  │ tenant mã        id   người dùng       số đơn   cod mốc      dấu vết mốc
  │ A    g22hd-a   1    g22hd-a-owner    60       900000111    nguoi_nhan_ten ~ 'A-MOC'
  │ B    g22hd-b   2    g22hd-b-owner    1        1000         nguoi_nhan_ten ~ 'B-MOC'
  └ phiên đăng nhập: A 200 · B 200 · mã đơn MỐC của A: T1-000001
```

### 8.4 ĐỐI CHỨNG DƯƠNG (A đọc A) + CROSS-TENANT (B đòi dữ liệu của A)

Vế **DƯƠNG** — A đọc dữ liệu của A, ghim **đúng `200`** *kèm hình dạng phản hồi*, vì một `200`
suông không phân biệt được đường mới với đường cũ:

| | Cây nhà (chưa gộp tuyến) | Cây đối chứng (AG-02) |
|---|---|---|
| mã | `200` | `200` |
| bảng khoá | `['don']` — **LỆCH** (thiếu 10 khoá §1.5) | **11/11 khoá KHỚP** |
| khoá dữ liệu | `don` (đường cũ) | `dong` (§1.5) |
| `gioi_han` · `trang` · `lech` | `None` · `None` · `None` | `50` · `1` · `0` |
| số dòng · `tong` · `con_nua` | 0 (không có khoá `dong`) · `None` · `None` | 50 · 60 · `True` |

Vế **ÂM** — B đòi dữ liệu của A:

```
  ┌ BẢNG CROSS-TENANT — B đòi dữ liệu của A (kèm vế DƯƠNG của chính A)
  │                                            CÂY NHÀ (chưa gộp)        CÂY ĐỐI CHỨNG (AG-02)
  │ B: ?tenant_id=<A> (tự chọn tenant)         200 · don · KHÔNG mốc A   400 · —   · KHÔNG mốc A
  │ B: ?ma_don=<đơn MỐC của A>                 200 · don · KHÔNG mốc A   200 · dong · KHÔNG mốc A
  │ A: ?ma_don=<đơn MỐC của A>  (DƯƠNG)        200 · don · CÓ mốc A      200 · dong · CÓ mốc A
  └
```

Ba điều **đo được**, không suy diễn:

1. **Cách ly dữ liệu VẪN GIỮ trên đường cũ** — B không nhận được dòng nào của A (thân phản hồi
   không chứa mã đơn lẫn `cod` mốc của A; `?q=A-MOC` ⇒ 0 dòng; danh sách B chỉ có 1 đơn của B).
   Đây là vế **DƯƠNG** của chính phép đo cách ly: nếu nó cũng đỏ thì "B không thấy dữ liệu A" chỉ
   là hệ quả của một máy chủ hỏng.
2. **Nhưng đường cũ BỎ QUA IM LẶNG tham số chọn tenant** — `?tenant_id=<A>` trả `200`. Đó **đúng
   là lý do `assertIn(200, 400)` bị bác**: điều kiện ấy gộp "từ chối tường minh" với "im lặng nhận
   rồi tự lọc hộ" thành một màu xanh, và người gọi không có cách nào biết tham số của mình bị nuốt.
3. **Hợp đồng ghim `400`** (`§1.4`: *không có đường nào để client chọn tenant*), cây đối chứng trả
   `400` + `loi` nêu **danh sách tên được nhận** — tức máy chủ **nói ra** thay vì nuốt.

### 8.5 PHÂN TRANG — mặc định 50 · trần 500 bị KẸP · **trang 2 KHÔNG lặp trang 1**

```
  ┌ BẢNG PHÂN TRANG (§1.3) — fixture 60 đơn của A
  │ yêu cầu                          CÂY NHÀ: gioi_han/lech/trang/số dòng/tong/con_nua (khoá)
  │ GET /api/v2/don (mặc định)       None/None/None/60/None/None (don)   ← 0 dòng ở khoá `dong`
  │ ?gioi_han=100000 (vượt trần)     None/None/None/60/None/None (don)
  │ ?gioi_han=25&trang=1             None/None/None/25/None/None (don)
  │ ?gioi_han=25&trang=2             None/None/None/25/None/None (don)
  │ ?gioi_han=25&trang=3             None/None/None/25/None/None (don)
  └ id trang 1 ∩ trang 2 = 25 id (36…60) · hợp trang 1+2 = 25 id  ⇒ **LẶP TRANG**
```

| | Cây nhà (đường cũ) | Cây đối chứng (AG-02) |
|---|---|---|
| mặc định | không khai `gioi_han`; trả **60** dòng (mặc định cũ **100**) | `gioi_han=50` · trang 1 · `lech=0` · **50** dòng · `tong=60` · `con_nua=True` |
| xin `gioi_han=100000` | trả **60** dòng, không khai giá trị thật | **kẹp về 500** và **trả ra** `gioi_han=500` (không 400) |
| trang 2 vs trang 1 | **giống hệt trang 1** (25/25 id trùng) — đường cũ không biết `trang`/`lech` | **giao = RỖNG**, hợp = 50 id khác nhau |
| trang 3 | 25 dòng (lặp) | **10** dòng · `con_nua=False` (60 = 25+25+10) |

Đây là lỗi **hỏng im lặng của phân trang** mà hợp đồng §1.3 nói tới: người dùng bấm "trang sau" và
nhận lại đúng những dòng vừa xem, không có gì báo.

### 8.6 PHỦ TUYẾN `/api/v2/don*` — bộ đếm trong tiến trình máy chủ

Cây nhà: **12 tuyến tồn tại · 0 đi qua `truy_van.chay()`**. Cây đối chứng (AG-02): **13 tuyến tồn
tại · 1 đi qua `truy_van.chay()`** — và tuyến ấy **đúng là `GET /api/v2/don`** (Δchay=1, Δtim_don=1).

```
  ┌ BẢNG PHỦ TUYẾN (cây đối chứng AG-02) — cột Δ là BỘ ĐẾM, không phải suy luận
  │  #  method tuyến                                    mã   Δchay Δtim  phán quyết ĐO ĐƯỢC
  │  1  GET   /api/v2/don                               200   1     1    ĐI QUA `truy_van.chay()`   ← TRONG §1
  │  2  POST  /api/v2/don                               400   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  3  GET   /api/v2/don/(\d+)                         200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  4  POST  /api/v2/don/(\d+)                         200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  5  POST  /api/v2/don/(\d+)/(duyet|gui|huy)         200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  6  GET   /api/v2/don/(\d+)/(hanh-trinh|…-hang)     200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  7  POST  /api/v2/don/(\d+)/(tu-choi|doi-soat…)     400   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  8  GET   /api/v2/don/(\d+)/mat-hang                200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │  9  GET   /api/v2/don/can-doi-soat                  200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │ 10  POST  /api/v2/don/kiem                          200   0     0    KHÔNG ĐI QUA — LỖ HỔNG
  │ 11  GET   /api/v2/don/loc-mo-ta                     200   0     0    KHÔNG chạy truy vấn — ĐÚNG §1.7 (ghim B7p)
  │ 12  POST  /api/v2/don/tim                           200   0     0    KHÔNG ĐI QUA — LỖ HỔNG   (§1.8.5 khai ngoài phạm vi)
  │ 13  GET   /api/v2/don/xuat-csv                      200   0     0    KHÔNG ĐI QUA — LỖ HỔNG   (§1.8.5 khai ngoài phạm vi)
  └ tuyến TỒN TẠI: 13 · ĐI QUA `truy_van.chay()`: 1 · ĐÚNG §1.7 (mô tả, không chạy truy vấn): 1 · LỖ HỔNG (Δchay=0): 11
```

**Không giấu tuyến nào**: cả 13 tuyến đều nằm trong bảng với Δ in ra bằng số. Cột *phạm vi hợp đồng
§1* chỉ nói thêm rằng §1.8 đã **khai trước** 11 tuyến là ngoài phạm vi (CRUD theo id, cửa cũ
`POST /don/tim`, xuất CSV) — đó là **nợ đã biết**, không phải bất ngờ; còn tuyến `loc-mo-ta` **đứng
Δ=0 là ĐÚNG thiết kế** (§1.7: đường mô tả trả `mo_ta_bo_loc()`, không chạy truy vấn) và được ghim
bằng **đẳng thức** với chính hàm mô-đun ở `B7p`, không bằng lời.

### 8.7 Phát hiện của lượt này

| # | Phát hiện | Mức | Chủ |
|---|---|---|---|
| **TRẠNG THÁI** | **Hợp đồng §1 của AG-02 CHƯA được gộp vào làn này**: `PHIEN_BAN_SCHEMA=9` (AG-02: 10), `grep -c 'truy_van\.' app/server.py` = **0**, không có tuyến `loc-mo-ta`. Vì thế 8 ghim hợp đồng ĐỎ **trên cây nhà** — đỏ vì **cây thiếu tuyến**, và chúng XANH trên cây AG-02 (đối chứng). Việc cần: AG-00 gộp nhánh AG-02 rồi chạy lại `chay_hopdong.sh` (kỳ vọng khi đó: **nhà = 0**, và `B7n` chuyển ĐẠT) | — | **AG-00** |
| **`N-G22-04`** | **Câu chữ hợp đồng §1.5**: viết *"`200` trả về **đúng 10 khoá**"* nhưng bảng ngay dưới liệt kê **11** dòng, và §3.3 cũng liệt kê **11**. Đo được: `truy_van.chay()` trả **10** khoá (`B7m`), phản hồi HTTP trả **11** vì máy chủ thêm bí danh `don` (`B7c`). **Mã đúng, câu chữ lệch một khoá** ⇒ sửa câu thành *"10 khoá của lớp truy vấn + bí danh `don`"* | THẤP | **AG-02** |
| **PHỦ TUYẾN** | **1/13** tuyến `/api/v2/don*` đi qua lớp truy vấn. Trong 12 tuyến còn lại: **1** là đường mô tả §1.7 (đúng thiết kế), **11** là CRUD/ghi/cửa cũ mà §1.8 **đã khai** ngoài phạm vi. Không tuyến nào **âm thầm** nằm ngoài: cả 12 đều Δ=0 và in rõ | THẤP (nợ đã biết) | ghi nhận |
| **PHÂN TRANG ĐƯỜNG CŨ** | `?trang=2&gioi_han=25` trả về **đúng 25 dòng đầu** (trùng trang 1) vì đường cũ chỉ đọc `gioi_han`; `?gioi_han` mặc định cũ là **100**, hợp đồng mới là **50** | — | đóng khi gộp AG-02 |
