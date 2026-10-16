# G20 — AG-05: BẢY LỖI TÁI DIỄN (regression security) + KHOÁ SỐ/CHUỖI

**Làn:** AG-05 · **Nền:** `integration/g19 @ 148ecd3` · **Nhánh:** `g20-ag05-baomat`
**Nền đối chiếu:** `main = de740dc` (KHÔNG chứa G13–G20 — đo lại, xem `A_Nen.test_a2`)

## 0. Wave này KHÔNG làm lại việc đã đạt

G16-A (ba cổng) · G17 (1460 ca / 38 bộ) · G18 (1631 / 44) · G19 (1733 ca / 47 bộ, nghiệm thu độc
lập 7/7 lời khai khớp) — **không mục nào được đo lại**. Wave G20 chỉ ĐÓNG KHOẢNG TRỎNG CÒN LẠI.
Hai khoảng trỏng được giao cho AG-05, cả hai đều do AG-01 ghi bằng số:

| Mã | Mức | Nội dung | Việc của AG-05 |
|---|---|---|---|
| `N-G19-03` / `N-G18-03` | **TRUNG BÌNH** (tái diễn nhiều lần) | cổng "cây sạch" của `thu_qa_g17.py` và `thu_qa_g18.py` chỉ miễn trừ tệp của CHÍNH NÓ ⇒ làn khác giao tệp là cổng ĐỎ | sửa cho đúng định nghĩa "cây sạch", **và đo RĂNG của bản vá** |
| `N-G19-01` | **TRUNG BÌNH** | mã hãng gửi dạng **SỐ** trượt khoá bảng dạng **CHUỖI**; AG-03 vá một phần ở G19 | đo lại, khoá bằng khẳng định cho **CẢ HAI DẠNG**, kèm chốt `D-4` |

**Chỉ được ghi 4 tệp** (đúng danh sách được cấp): `app/thu/thu_qa_g17.py` · `app/thu/thu_qa_g18.py` ·
`app/thu/thu_g20_baomat.py` (mới) · `docs/G20_BAOMAT.md` (mới). **Không một dòng mã sản phẩm nào bị
sửa** — vì thế `D-4`, `D-8`, `D-9` và mọi chốt cũ giữ nguyên giá trị.

## 1. `N-G19-03` / `N-G18-03` — TÁI HIỆN, ĐỊNH NGHĨA LẠI, VÀ ĐO RĂNG

### 1.1 Tái hiện (TRƯỚC bản vá) — lệnh thật, mã thoát thật

Bản gốc lấy thẳng từ git (`git show HEAD:…`), đặt **cạnh tệp gốc** để nó vẫn suy đúng gốc cây, và
đặt tên KHỚP mẫu miễn trừ của chính nó (`thu_qa_g17_goc_tam.py`) để **loại trừ nguyên nhân "chính
bản sao làm cây bẩn"**:

```sh
git show HEAD:app/thu/thu_qa_g17.py > app/thu/thu_qa_g17_goc_tam.py   # exit 0
python3 app/thu/thu_qa_g17_goc_tam.py A_Nen                           # EXIT 1
#   Ran 7 tests in 0.840s · FAILED (failures=1)
#   AssertionError: Lists differ: [' M app/thu/thu_qa_g18.py',
#                                  '?? app/thu/thu_g20_baomat.py', '?? docs/G20_BAOMAT.md'] != []
git show HEAD:app/thu/thu_qa_g18.py > app/thu/thu_qa_g18_goc_tam.py   # exit 0
python3 app/thu/thu_qa_g18_goc_tam.py A_Nen                           # EXIT 1
#   Ran 7 tests in 0.757s · FAILED (failures=1)
#   AssertionError: Lists differ: [' M app/thu/thu_qa_g17.py',
#                                  '?? app/thu/thu_g20_baomat.py', '?? docs/G20_BAOMAT.md'] != []
```

⇒ Lỗi tái diễn **đúng như AG-01 mô tả**: cổng ĐỎ vì làn này giao tệp, **không** vì cây bẩn. Chú ý
dòng `' M app/thu/thu_qa_g18.py'` trong lỗi của G17: hai bộ thử **làm đỏ lẫn nhau** — đúng cơ chế
đã sinh ra `N-G18-03` rồi `N-G19-03`.

### 1.2 Định nghĩa lại "cây sạch"

> **CÂY SẠCH = KHÔNG có thay đổi NÀO ngoài các tệp mà WAVE đang làm.**

Đây **KHÔNG** phải "bỏ qua hết", và cũng **KHÔNG** phải "bỏ qua mọi thứ trông giống bộ thử". Mỗi bộ
nay khai hai danh sách:

* `PHAM_VI_LAN_NHA` — mẫu của **chính làn đó** (`app/thu/thu_qa_g17*.py`, `docs/QA_G17*.md`).
* `PHAM_VI_LAN_KHAC` — **đường ĐÍCH DANH** của các làn khác đang làm trong cùng wave. Cố ý KHÔNG
  dùng mẫu (`app/thu/thu_qa_g18*.py`): mẫu sẽ nuốt luôn bộ thử của làn khác một cách vô hình.

Thay đổi cấu trúc: hàm lọc được tách thành **hàm THUẦN** `_loc_cay_ban(dong, …)` (nhận thẳng các
dòng `git status --porcelain`), còn `_cay_ban(…)` chỉ là phần chạy git. Nhờ vậy đối chứng âm đo được
**không cần chạm cây thật**, và `_git(…, goc=…)` cho phép trỏ vào **cây git tạm**.

### 1.3 Ba cổng tự kiểm canh CHÍNH DANH SÁCH MIỄN TRỪ (mới, trong cả hai bộ)

| Ca | Khẳng định | Vì sao không thể bỏ |
|---|---|---|
| `test_a1b` | mọi mục miễn trừ phải nằm trong `app/thu/` hoặc `docs/`; **mục của làn khác không được chứa ký tự mẫu** (`*?[`) | chặn nước đi "nới cho rộng ra" — cách chữa rẻ nhất và sai nhất |
| `test_a1c` | mọi mục miễn trừ phải KHỚP một đường **có thật** (git theo dõi hoặc có trên đĩa) | một miễn trừ gõ sai vẫn nằm đó trông như đang canh gác |
| `test_a1d` | **ĐỐI CHỨNG ÂM BẮT BUỘC**: tệp SẢN PHẨM bẩn ⇒ cổng PHẢI ĐỎ (3 tầng) | nếu không, cổng thành "cây nào cũng sạch" |

`test_a1d` chồng **ba tầng**, cố ý:
1. **hàm thuần** — dòng porcelain của `app/webhook.py`, `app/server.py`, `mock/tep_moi.json`,
   `app/cau_hinh.py` không được lọc mất;
2. **git THẬT trên cây tạm** — `app/webhook.py` (đã commit) bị sửa ⇒ ĐỎ; chỉ tệp của wave bẩn ⇒ XANH;
3. **git THẬT trên CÂY ĐANG ĐO** — một tệp mới xuất hiện trong `app/` ⇒ ĐỎ; xoá đi ⇒ **XANH LẠI**.

> **Không tệp sản phẩm nào của cây thật bị sửa nội dung.** Tầng (3) chỉ TẠO RỒI XOÁ một tệp tạm
> trong `finally`; tầng (2) sửa trên **cây sao chép** trong thư mục tạm. Đây là lựa chọn có ý thức:
> sửa-rồi-khôi-phục một tệp sản phẩm thật sẽ để lại cây bẩn nếu tiến trình bị giết giữa chừng, và
> như thế chính phép đo lại trở thành nguồn của `N-G19-03`.

### 1.4 Số đo (SAU bản vá) — lệnh thật, mã thoát thật

```sh
python3 app/thu/thu_qa_g17.py A_Nen     # EXIT 0 · Ran 10 tests in 1.347s · OK
python3 app/thu/thu_qa_g18.py A_Nen     # EXIT 0 · Ran 10 tests in 0.834s · OK
python3 app/thu/thu_g20_baomat.py       # EXIT 0 · Ran 27 tests in 6.544s · OK
```

**Đối chứng âm chạy THẲNG bằng lệnh, ngoài bộ thử** (`app/_ag05_bc_tam_san_pham.py` — tạo, đo, xoá):

```sh
python3 app/thu/thu_qa_g17.py A_Nen.test_a1_cay_sach_va_head            # EXIT 1 (FAILED, 1 ca)
python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_theo_pham_vi_wave # EXIT 1 (FAILED, 1 ca)
rm app/_ag05_bc_tam_san_pham.py
python3 app/thu/thu_qa_g17.py A_Nen.test_a1_cay_sach_va_head            # EXIT 0 (OK, 1 ca) — XANH LẠI
```

| Bộ | Trước | Sau | Ca mới |
|---|---|---|---|
| `thu_qa_g17.py::A_Nen` | 7 ca · **FAILED (failures=1)** · thoát **1** | **10 ca · OK · thoát 0** | `a1b`, `a1c`, `a1d` |
| `thu_qa_g18.py::A_Nen` | 7 ca · **FAILED (failures=1)** · thoát **1** | **10 ca · OK · thoát 0** | `a1b`, `a1c`, `a1d` |

**Vân tay cây của G17 KHÔNG đổi** (`ad19a3320eb428ce…` trước và sau): thêm tệp của làn trong wave
không làm vân tay nhúc nhích — đúng ý đồ thiết kế. Một tệp sản phẩm bẩn thì vân tay **đổi ngay**
(chứng minh ở `B_ChotCaySach` của bộ mới).

### 1.5 RĂNG của bản vá — đối chứng âm ở quy mô toàn dự án (`thu_g20_baomat.py::B_ChotCaySach`)

| Ca | Phép đo | Kết quả đo được |
|---|---|---|
| `B1` | chạy THẬT `A_Nen` của hai bộ cũ trên cây ĐANG có 4 tệp của wave | cả hai **exit 0** (10 ca · 10 ca) |
| `B2` | dựng tệp sản phẩm mới `app/_ag05_g20_tam_san_pham.py` ⇒ chạy ĐÍCH DANH ca cây sạch | cả hai **exit 1**, có dòng `FAIL:`; xoá tệp ⇒ **exit 0 lại** |
| `B3` | tệp lạ ở `mock/` **và** `gateway/` | cả hai **exit 1**, thông báo có nhắc đúng đường |
| `B4` | đọc phạm vi **KHAI TRONG NGUỒN** của hai cổng bằng AST (không `import`) | phủ đủ 4/4 tệp của wave |
| `B5` | **ĐỘT BIẾN** `_loc_cay_ban → return []` ("bỏ qua hết") trên bản sao của chính cổng | `test_a1d` **ĐỎ** (bản gốc XANH) — đối chứng âm không phải trang trí |
| `B6` | **ĐỘT BIẾN** nhét `app/webhook.py` vào danh sách miễn trừ | `test_a1b` **ĐỎ** (bản gốc XANH) |
| `B7` | đo bản sao thứ ba (xem §3.1) | `thu_qa_g19.py::A_Nen` **exit 0 · 0 ca · 1 bỏ qua** |

Máy đột biến **từ chối chạy nếu phép thay không gieo được** (`dem != 1` ⇒ `AssertionError`): một
đột biến rỗng ruột sẽ biến ca tự kiểm thành đồ trang trí, và chỗ đó bị chặn thẳng.

## 2. `N-G19-01` — KHOÁ SỐ / CHUỖI: ĐO LẠI VÀ KHOÁ LẠI

### 2.1 Đo lại: lỗ hổng đã ĐÓNG trên cả hai bảng

AG-03 đã vá `_khoa_ma` cho `vtp` (chuỗi toàn số ⇒ quy về số). Đo lại **toàn bộ** bảng, không lấy mẫu:

```sh
python3 app/thu/thu_g20_baomat.py C_KhoaMaSoChuoi
# [C1] 26 khoá số {'jt': 13, 'vtp': 13} · kiểu khoá bảng={'jt': ['int'], 'vtp': ['int', 'str']} · lệch SỐ↔CHUỖI = 0
```

Phép đo so **sáu trường** cho từng mã (`biet_ma`, `trang_thai`, `chua_xac_minh`, `nhap_nhang`,
`nhan`, `trang_thai_ap`) giữa dạng SỐ và dạng CHUỖI. **0 lệch trên 26/26 khoá.** Đoạn `_do_hai_dang`
nhận **cả hai kiểu khoá** (`200` và `"200"`) — nếu chỉ nhận `int` thì phép tự kiểm ở §2.3 sẽ "không
thấy gì" và hoá ra là phép đo rỗng ruột.

### 2.2 Chốt `D-4`: mã chưa xác minh ⇒ `NEEDS_REVIEW`, KHÔNG ánh xạ bừa

| Ca | Phép đo | Kết quả |
|---|---|---|
| `C2` | **12** mã `CHUA_XAC_MINH` × **2** dạng = 24 lượt | 0 lượt bị ánh xạ bừa; mọi lượt `NEEDS_REVIEW` · `trang_thai_ap = None` |
| `C2` (đối chứng dương) | mã `200` — mã DUY NHẤT có nghĩa đã xác minh | cả hai dạng ⇒ `nhan=OK` · `trang_thai_ap='lay_hang'` (nếu không, "luôn NEEDS_REVIEW" chỉ là hằng số) |
| `C3` | **4** mã lạ × **2** hãng × **2** dạng = 8 lượt | `biet_ma=False` · `NEEDS_REVIEW` · `trang_thai_ap=None` |
| `C4` | **6** khoá MÔ PHỎNG dạng chuỗi-không-số (`cho_lay`, …) | vẫn nguyên nghĩa ⇒ chuẩn hoá số KHÔNG đụng tới bộ mô phỏng |
| `C6` | mã NHẬP NHẰNG × 2 dạng | không mã nào rơi vào `('giao_thanh_cong', 'hoan_hang')` |

Ca `C3` là chỗ `D-4` được canh: mã **không có trong tài liệu** đi vào `NEEDS_REVIEW` ở **cả hai
dạng**, **không** bị ánh xạ bừa sang một trạng thái nào. Không mã trạng thái hãng nào bị **đoán**
trong tệp này.

### 2.3 TỰ KIỂM BỘ ĐO: dựng lại ĐÚNG `N-G19-01` ⇒ phép đo PHẢI ĐỎ

`C5` dựng lại **đúng hình dạng gốc** của lỗi, trên **bản sao trong bộ nhớ** (không sửa tệp sản phẩm):

* `_khoa_ma` trả nguyên giá trị cho `vtp` — đúng mã trước G19;
* `BANG["vtp"]` dựng lại bằng khoá **CHUỖI** — đúng kịch bản "AG-04 mang 21 mã sang bằng khoá chuỗi".

```sh
# [C5] đột biến `N-G19-01` dựng lại: phép đo thấy 13 mã lệch ⇒ C1 CÓ RĂNG
#      mẫu: {"hang": "vtp", "ma": 101,
#            "dang_so":    [false, null, "NEEDS_REVIEW", null],
#            "dang_chuoi": [true,  null, "OK",            null]}
```

⇒ **13 mã lệch** được phát hiện, và mẫu in ra đúng cái `N-G19-01` mô tả: payload **SỐ** trượt khoá
**CHUỖI**. Sau đó bảng được khôi phục và `C1` đo lại **0 lệch** — nếu khôi phục hỏng, ca này ĐỎ,
nên các ca sau không thể đo trên cây bẩn.

### 2.4 Các chốt AN TOÀN được ĐO LẠI trong lượt này (`thu_g20_baomat.py::A_Nen`)

Hai khoảng trỏng được giao là (a) và (b) ở §1 và §2. Ngoài ra bộ mới **đo lại** — không phải kể
lại — các chốt an toàn mà làn này có thể vô tình chạm tới, mỗi chốt kèm **đối chứng dương** để
chứng minh bộ dò không mù:

| Ca | Chốt được đo | Cách đo | Kết quả |
|---|---|---|---|
| `A3` | **`CHO_PHEP_LIVE` khoá** | đọc ĐỘNG từ `adapter._DANG_KY` + lớp giả đã mở | 2 lớp adapter · LIVE mở: **0** · bộ dò bắt được lớp giả |
| `A4` | **ổ khoá LIVE không được thành cần gạt config** | AST trên `app/cau_hinh.py` + mọi `app/adapter*.py` | `cau_hinh.py`: **0** khai báo · `adapter.py`/`adapter_jt.py`/`adapter_vtp.py`: `CHO_PHEP_LIVE = False` · git xác nhận `cau_hinh.py` **không bị đụng** |
| `A5` | **`D-8`: CSDL nghiệp vụ vẫn SQLite** | AST (import + chuỗi), **không grep** | nhập `sqlite3` · **0** driver PostgreSQL · **0** chuỗi kết nối (chú thích nhắc `psycopg` không bị tính) |
| `A6` | **tệp mới không chạm mạng** | tự quét AST **trên chính nó** + tìm URL | **0** import mạng · **0** URL · bộ quét bắt được ca giả |
| `A7` | **cụm PostgreSQL của dự án khác CHẶN CỨNG** | số cổng **ghép lúc chạy** để tệp không chứa nó | **0** tham chiếu · CSDL đo dùng SQLite tạm |
| `A2` | **nền không lấy từ `main`** | `git cat-file -e main:<đường>` + `merge-base --is-ancestor` | `main=de740dc` · là tổ tiên của HEAD · **không** chứa `docs/G16_ACCEPTANCE.md` lẫn `docs/G20_BAOMAT.md` |

Ca `A6` là chỗ đáng chú ý nhất về phương pháp: thay vì **dặn lòng** "không gọi mạng", tệp tự quét
AST trên chính nó. Một lời dặn thì người sau quên; một dòng mã thì không.

## 3. Phát hiện CÒN LẠI (ghi ra, KHÔNG tự sửa)

### 3.1 `N-G20-01` — **THẤP (tiềm ẩn)**: bản sao THỨ BA của cùng lỗi ở `thu_qa_g19.py`

`app/thu/thu_qa_g19.py:79` khai `TEP_CUA_AG01_G19 = ("app/thu/thu_qa_g19.py", "docs/QA_G19.md")` —
**đúng hai tệp**, cùng khuôn `N-G18-03`/`N-G19-03` mà tôi vừa vá ở hai bộ kia.

**Hôm nay nó DORMANT, và đó là số đo chứ không phải suy đoán:**
`thu_qa_g19.py::A_Nen` ⇒ **exit 0 · 0 ca · 1 bỏ qua**, vì `setUpModule` tự bỏ qua khi HEAD
(`148ecd3`) khác nền đóng băng (`6e61fc1`) — bộ này là **bộ đo nợ nền**, nó không thể và không nên
xanh trên cây đã gộp. Nên nó **không** làm đỏ hồi quy chung, và tôi để nguyên.

**Nó thành lỗi thật khi:** ai đó chạy `VIP_G19_HEAD=<HEAD hiện tại>` (ghim chủ động ⇒ `setUpModule`
không bỏ qua nữa) — lúc đó `A_Nen.test_a1` sẽ ĐỎ vì hai tệp mới của G20, y hệt hai lần trước.

`thu_qa_g19.py` **NGOÀI danh sách 4 tệp được cấp**, nên tôi **KHÔNG sửa**; tôi ĐO (`B7`) và ghi ra
đây. Bản vá tương ứng là 1 khối ~6 dòng, cùng khuôn đã áp cho G17/G18. **Quyết định thuộc AG-00.**

### 3.2 `N-G20-02` — **THẤP (an toàn theo hướng đúng)**: vài hình dạng "gần đúng" của mã

Đo được (không đoán mã nào; chỉ đo các mã **đã có trong bảng của dự án**):

| Đầu vào | `biet_ma` | `trang_thai_ap` | Nhận xét |
|---|---|---|---|
| `200` (int) · `"200"` (str) | True | `lay_hang` | đúng |
| `" 200 "` · `"0200"` | True | `lay_hang` | chuẩn hoá `int()` chấp nhận — chấp nhận được |
| `200.0` (float) | True | `lay_hang` | JSON có thể ra float; `hash(200.0)==hash(200)` nên khớp **đúng** mã |
| `101` · `"101"` | True | `None` · `NEEDS_REVIEW` | `D-4` giữ đúng |
| `999904` · `"999904"` | False | `None` · `NEEDS_REVIEW` | mã lạ ⇒ không ánh xạ bừa |

Không có hình dạng nào bị ánh xạ **sai**; hướng hỏng duy nhất có thể hình dung là một float không
nguyên (vd `200.5`) — nó rơi vào mã lạ ⇒ `NEEDS_REVIEW`, tức hướng **an toàn**. Ghi ra, không sửa
(và không được sửa: **không có dòng mã sản phẩm nào trong phạm vi làn này**).

## 4. HỒI QUY TOÀN BỘ

```sh
sh app/thu/chay_tat_ca.sh        # EXIT 1
```

```
  ✓ thu_g20_baomat.py          27 ca      ← bộ MỚI của làn này, tự được bộ dò nhận ra
  ✓ thu_qa_g17.py              56 ca      ← TRƯỚC bản vá: bộ này ĐỎ (N-G19-03)
  ✗ thu_qa_g18.py              46 ca  HỎNG (mã thoát 1)
        FAIL: test_b1_tang_3_chay_duoc_va_khong_co_ca_hong (__main__.B_Tang3)
  ⊘ thu_qa_g19.py               BỎ QUA  (bộ đo NỀN — HEAD khác nền đóng băng, xem §3.1)

══════════════════════════════════════════════════
  python:   1766 ca · 48 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_qa_g19.py
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  thu_qa_g18.py
```

**Kiểm tra chéo số ca:** lượt này 1766 ca, G19 đo 1733 ca ⇒ **+33**. Làn này thêm đúng **33** ca:
27 ca của `thu_g20_baomat.py` + 3 ca ở `thu_qa_g17.py` + 3 ca ở `thu_qa_g18.py`. Khớp.

**Mã thoát 1 KHÔNG phải của làn này** — và đây là bằng chứng, không phải lời khai:

```sh
git show HEAD:app/thu/thu_qa_g18.py > app/thu/thu_qa_g18_goc_tam.py   # bản GỐC, chưa hề có AG-05
python3 app/thu/thu_qa_g18_goc_tam.py B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong
#   EXIT 1 · Ran 1 test in 123.657s · FAILED (failures=1)
#   [B1] mã thoát=1 · 47 đạt · 1 hỏng · 3 bỏ qua
```

⇒ Với **bản gốc nguyên vẹn** của tệp, tầng 3 hỏng **y hệt**. Xem `N-G20-03` dưới đây.

**Số ca bỏ qua của `thu_qa_g18.py`: 1** — `H_Postgres.test_h3_chay_tron_tren_cum_rieng`, tự bỏ qua
kèm lý do *"CHƯA ĐO trong làn mặc định: bật `VIP_G18_DAY_DU=1` để chạy trọn"*. Đây là **skip có
sẵn từ trước**, không phải do làn này; ba ca mới của AG-05 **không ca nào bỏ qua**.

### 3.3 `N-G20-03` — **TRUNG BÌNH, SẴN CÓ ở nền `148ecd3`, NGOÀI phạm vi làn này**

`thu_giao_dien/06_ban_phim.spec.js` ca **04** ("Tab vào được các điều khiển TRONG màn, không chỉ
quanh menu") **HỎNG**:

```
Error: 30 lượt Tab chỉ vào được 1 điều khiển trong màn
  Expected: > 10      Received: 1
  at thu_giao_dien/06_ban_phim.spec.js:164
47 passed · 1 failed · 3 did not run
```

**Đây KHÔNG phải `EPERM` do sandbox chặn ghi** (đề bài dặn kiểm trước): log cho thấy ảnh chụp và
`thu_giao_dien/_ket-qua/` **ghi được bình thường**; đây là một khẳng định giao diện **hỏng thật**.
Cũng **KHÔNG** phải do làn này: chứng minh bằng bản gốc HEAD ở §4, và làn này **không ghi một dòng
nào** vào `thu_giao_dien/`, `pages/`, `admin/` hay bất kỳ mã giao diện nào.

Đo thêm (ghi ra, không kết luận vượt số đo): gọi **riêng** spec này bằng `sh thu_giao_dien/chay.sh
thu_giao_dien/06_ban_phim.spec.js` thì ca **01** hỏng ngay (2ms) vì **thiếu nhị phân Chromium**
(`Executable doesn't exist at …chromium_headless_shell-1194/…`) — đường gọi trực tiếp không đặt
`PLAYWRIGHT_BROWSERS_PATH` như `thu_qa_g18.py::B_Tang3` vẫn làm. Vì vậy **phép đo "chạy riêng" này
KHÔNG dùng được** để phán về thứ tự ca; nó chỉ nói về môi trường. Nói thẳng: ca 04 **có** hỏng trong
lượt đầy đủ, và tôi **không** xác định được nó hỏng độc lập hay phụ thuộc thứ tự ca.

**Đề xuất (thuộc AG-00, KHÔNG tự làm):** spec `06_ban_phim.spec.js` là sản phẩm của G19/AG-06
(`docs/G19_BAN_PHIM.md`), còn `B_Tang3` của `thu_qa_g18.py` **tự dò mọi spec** trong `thu_giao_dien/`
— nên một spec thêm ở wave sau có thể làm đỏ bộ thử của wave trước. Đó là **cùng một họ** với
`N-G18-03`/`N-G19-03` (lỗi TÍCH HỢP GIỮA CÁC LÀN bị đọc thành lỗi của làn sau). Cần một quyết định
của AG-00: sửa spec, hay cố định danh sách spec cho từng bộ.

## 5. KẾT LUẬN VỀ HAI KHOẢNG TRỎNG ĐƯỢC GIAO

| Khoảng trỏng | Trạng thái | Bằng chứng |
|---|---|---|
| `N-G19-03` / `N-G18-03` — cổng "cây sạch" | **ĐÓNG** | tái hiện EXIT 1 (2 bộ) → sau vá EXIT 0 (2 bộ, 10 ca mỗi bộ) · đối chứng âm 3 tầng ĐỎ đúng chỗ · 2 phép đột biến đều bị bắt (`B5`, `B6`) |
| `N-G19-01` — khoá SỐ/CHUỖI | **ĐÓNG (đã đóng từ G19, nay KHOÁ LẠI)** | 26/26 khoá số · **0 lệch** SỐ↔CHUỖI · 24 lượt mã chưa xác minh ⇒ `NEEDS_REVIEW` · 8 lượt mã lạ ⇒ `NEEDS_REVIEW`, không áp trạng thái · đột biến dựng lại `N-G19-01` ⇒ phép đo **thấy 13 mã lệch** |

**Số ca bỏ qua của làn này: 0** (`thu_g20_baomat.py` ⇒ `Ran 27 tests … OK`, không có `skipped=`)
khi chạy ở chế độ đầy đủ. Đặt `VIP_G20_NHANH=1` thì **3 ca** (`B5`, `B6`, `C5`) tự bỏ qua kèm lý do
— đó là chế độ chạy nhanh, **không** phải kết quả nghiệm thu.

## 6. CHƯA ĐO — nói thẳng cái NẰM NGOÀI phạm vi

* **Không gọi hãng, kể cả sandbox** (`V-G09-01` + `V-13906-05` CHƯA CẤP). Mọi phép đo lớp HTTP của
  dự án chỉ dùng stub `127.0.0.1` cổng `0`; **tệp mới của làn này không mở cổng nào** — có ca tự
  quét AST (`A_Nen.test_a6`) chứng minh, thay vì dặn lòng.
* Không push · không deploy · không tunnel · không mở `CHO_PHEP_LIVE` · không credentials thật ·
  không `.env`.
* **`D-8`**: CSDL nghiệp vụ vẫn SQLite; cụm PostgreSQL production của dự án khác **CHẶN CỨNG**
  (`A_Nen.test_a5`, `test_a7`). Không chạm cụm đó lần nào.
* **`D-9` city/area**: không tệp nào của làn này chạm tới ánh xạ tỉnh/quận ⇒ chốt cứng ngoài mock
  giữ nguyên. **Không đo lại** (ngoài phạm vi được giao).
* Không đo: TLS thật · webhook thật · hãng thứ ba ngoài `jt`/`vtp` · dữ liệu lớn · trình đọc màn
  hình · Safari/Firefox. Tầng 3 Chromium **có chạy** (trong hồi quy chung) nhưng **không thuộc làn
  này** — kết quả của nó ghi ở §3.3 dưới dạng phát hiện, không phải kết luận của AG-05.
* `thu_qa_g19.py` (bản sao thứ ba) — **chỉ ĐO**, không sửa; xem §3.1.

## 7. Tệp đã ghi & cách chạy lại

| Tệp | Việc |
|---|---|
| `app/thu/thu_qa_g17.py` | định nghĩa lại "cây sạch" theo PHẠM VI WAVE + `a1b`/`a1c`/`a1d` (đối chứng âm) |
| `app/thu/thu_qa_g18.py` | y hệt, cùng khuôn (hai bộ phải không lệch nhau về luật) |
| `app/thu/thu_g20_baomat.py` | **MỚI** — 27 ca: đo độc lập bản vá, đo RĂNG bằng đột biến, khoá số/chuỗi |
| `docs/G20_BAOMAT.md` | tài liệu này |

```sh
python3 app/thu/thu_g20_baomat.py                     # 27 ca · thoát 0
python3 app/thu/thu_g20_baomat.py B_ChotCaySach       # riêng nhóm đo RĂNG của bản vá
python3 app/thu/thu_g20_baomat.py C_KhoaMaSoChuoi     # riêng nhóm khoá SỐ/CHUỖI
VIP_G20_NHANH=1 python3 app/thu/thu_g20_baomat.py     # bỏ 3 ca đột biến (chạy nhanh)
sh app/thu/chay_tat_ca.sh                             # hồi quy TOÀN BỘ (xem §4)
```
