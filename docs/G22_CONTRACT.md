# G22 · AGENT 02 — HỢP ĐỒNG TEST CHO NHÓM F · G · Z6 (STALE → ĐÚNG HỢP ĐỒNG ĐÃ DUYỆT)

> **Vai:** AGENT 02 · G22 TEST CONTRACT · `task_82754aae6280` · dispatch `ctx_18447e83eb9b`.
> **Nền đo:** `integration/g20 @ a76ec51c9931b62451721302446d7c3b74b9c81f` (worktree `g22-a2-contract`).
> **KHÔNG** dùng `main` (`de740dc` — không chứa G13–G22). **KHÔNG** mở G23.
> **Phạm vi ghi (đã giữ đúng):** `app/thu/thu_qa_g22.py` (sửa) · `docs/G22_CONTRACT.md` (mới).
> Không sửa một dòng mã sản phẩm nào; không sửa `app/thu/thu_g22_*.py`, `app/thu/thu_qa_g21.py`,
> `app/thu/thu_qa_g20.py`, `app/thu/thu_g20_dahang.py`.
> **CAM KẾT:** không push · không deploy · không gọi API hãng · không tạo đơn thật · không sửa dữ
> liệu thật · không xoá CSDL · không tự merge `main` · không tự đổi quyết định OWNER.
> **D-8 / `OWNER_ACTIONS C4` (PostgreSQL) = BLOCKED OWNER — KHÔNG thực hiện, không ép xanh.**
> Việc local `G19-C6` (route `truy_van` + DDL vào migration) là việc KHÁC C4; lượt này không đụng.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

Năm ca HỎNG/ERROR thuộc phạm vi lượt này (`F1`, `F2`, `F3`, `G1`, `Z6`) **không phải lỗi nghiệp
vụ**: cả năm đều là **lỗi TEST đã STALE** so với hợp đồng đã được duyệt và mã nguồn hiện tại.
Sản phẩm đã đúng ở hai chỗ then chốt (`sao_luu`/`khoi_phuc` nhận **mốc thời gian qua tham số**
`luc=`; `test_c2a` đã được viết lại theo bất biến **không rò credential NGẮN**), nhưng bộ kiểm vẫn
đo theo cách cũ. Đã sửa **cách đo** — không sửa sản phẩm, không nới cổng, không xoá ca.

| | TRƯỚC (Controller đo lại, `baseline.log`) | SAU (lượt này, `lan2.log` · `chot.log` (lượt chốt)) |
|---|---|---|
| Lệnh | `python3 app/thu/thu_qa_g22.py` | `python3 app/thu/thu_qa_g22.py` |
| `Ran` | **24** | **24** |
| PASS (tính) | **14** = 24 − 7 FAIL − 1 ERROR − 2 SKIP | **19** = 24 − 3 FAIL − 2 SKIP |
| FAIL | **7** | **3** (đều NGOÀI phạm vi: `A1`, `B2`, `B3`) |
| ERROR | **1** | **0** |
| SKIP | **2** (`E1` môi trường · `Z9` mồi) | **2** (`E1` môi trường · `Z9` mồi) |
| **EXIT CODE** | **1** | **1** (vì 3 lỗi ngoài phạm vi còn nguyên — **không giả xanh**) |

> `EXIT 1` sau khi sửa **không phải** thất bại của lượt này: ba lỗi còn lại thuộc AGENT 03
> (`A1` — sandbox chặn `git write-tree`) và AGENT 01 (`B2`/`B3` — thiếu nhị phân Chromium). Bảng
> §5 ghi rõ. Bộ kiểm **không** hạ cổng, **không** thêm `skipTest`, **không** xoá ca để `EXIT 0`.

---

## 1. LỆNH THẬT + MÃ THOÁT THẬT (đọc NGAY sau lệnh, không qua ống)

```sh
# TRƯỚC khi sửa — Controller tái hiện, tôi đo lại đúng bằng lệnh này:
$ python3 app/thu/thu_qa_g22.py
# → Ran 24 tests in 29.272s · FAILED (failures=7, errors=1, skipped=2)
# → EXIT 1

# SAU khi sửa — toàn bộ bộ kiểm:
$ python3 app/thu/thu_qa_g22.py
# → Ran 24 tests in 27.726s · FAILED (failures=3, skipped=2)
# → EXIT 1   (3 lỗi còn lại: A1, B2, B3 — ngoài phạm vi, xem §5)

# Nhóm F + G chạy riêng — chế độ nền (đo hợp đồng):
$ python3 app/thu/thu_qa_g22.py F_DongHo G_NG2103
# → Ran 4 tests in 1.831s · OK
# → EXIT 0

# Nhóm F + G chạy riêng — chế độ nghiệm thu bản đã gộp:
$ VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py F_DongHo G_NG2103
# → Ran 4 tests in 1.832s · OK
# → EXIT 0

# Lớp E (đối chứng CLONE chạy TRƯỚC khi E1 skip vì môi trường):
$ python3 app/thu/thu_qa_g22.py E_CaySach
# → Ran 2 tests in 8.086s · OK (skipped=1)
# → EXIT 0
```

Log thô của từng lượt (đường dẫn máy đo): `/tmp/g22_a2/baseline.log`, `lan2.log` · `chot.log` (lượt chốt),
`fg_lan1.log`, `fg_gop.log`, `e1_lan1.log`, `g5.log`, `g5_tiem.log`, `c2a.log`, `c2a_tiem.log`.
Tệp bộ kiểm sau khi sửa: `sha256 ccc8320f750fbaffdb47d3f9d31cd8bd9be2b3ffa975b1770a17acc9599f8095`.

---

## 2. BẢNG PHÂN LOẠI — CA NÀO **STALE**, CA NÀO **LỖI THẬT**

Tiêu chí phân loại:

* **Lỗi TEST (STALE)** — ca đo ghim một hành vi/đoạn mã/giả định **đã được thay đổi hợp pháp**;
  sản phẩm đúng theo hợp đồng đã duyệt, ca đo sai.
* **Lỗi NGHIỆP VỤ** — sản phẩm sai so với bất biến đã duyệt; sửa sản phẩm (KHÔNG thuộc lượt này).
* **MÔI TRƯỜNG** — phép đo không dựng được vì sandbox/nhị phân/HEAD; không kết luận về sản phẩm.

| Ca | Hiện tượng TRƯỚC | Đối chiếu mã nguồn/hợp đồng HIỆN TẠI | Phân loại | Việc đã làm |
|---|---|---|---|---|
| `F1` `test_f1_do_that_bang_dong_ho_dong_bang` | FAIL: `KHÔNG ĐO ĐƯỢC E3 (rc=1)` — `sao_luu()` TỪ CHỐI vì **chưa khai kho** | `migrate.sao_luu()` từ G22 **đòi khai `VIP_KHO_DANG_CHAY`** (chốt `do2b`); ca cũ không khai, không truyền `luc=`, và dùng bản `nguon.db` **không có `.sha256`** nên `khoi_phuc()` cũng từ chối. Sản phẩm ĐÚNG. | **Lỗi TEST (STALE)** — không phải lỗi nghiệp vụ | Khai `VIP_KHO_DANG_CHAY=sqlite` trong tiến trình đo; tạo backup hợp lệ bằng `sao_luu(luc=)`; gọi `khoi_phuc(..., luc=)`; đòi 3 bản cất + đúng mốc + mở được + giữ dữ liệu |
| `F2` `test_f2_doi_chung_duong_ban_da_va` | ERROR: `RuntimeError: không vá được khoi_phuc: đoạn gốc không khớp nguyên văn` | `_app_tam(va_khoi_phuc=True)` tìm đoạn `cat_di = os.path.join(..., "hub-truoc-rollback-" + datetime.now()...)` — đoạn này **đã bị xoá** từ G22, thay bằng `_duong_chua_dung("hub-truoc-rollback", ".db", luc)`. | **Lỗi TEST (STALE)** — vá chuỗi vào mã đã đổi | Bỏ hẳn cách vá chuỗi; dùng **bản đóng băng thật** `trien_khai/g20-saoluu/migrate_nguyenban.py` (md5 ghim `611182a621fd279c3816d5fc5d2785e3`) làm vế TRƯỚC |
| `F3` `test_f3_vi_sao_phai_dong_bang_dong_ho` | FAIL: `assertIsNotNone` — không còn tìm thấy regex đặt tên bản cất | Regex cũ tìm `"hub-truoc-rollback-" + datetime.now().strftime(...)` **trong `migrate.py`**; tên nay do `_duong_chua_dung(..., luc)` đặt. | **Lỗi TEST (STALE)** — ghim hình dạng mã cũ | Đo HÀNH VI trên bản đóng băng: cùng giây → 1 bản cất; đồng hồ nhích → 3 bản cất (XANH GIẢ); bản thật + `luc=` → 3 bản cất **bất kể** đồng hồ. Kèm vế source: `khoi_phuc` có `luc=` và chuyển xuống `_duong_chua_dung` |
| `G1` `test_g1_ca_thu_con_ghim_ro` | FAIL: `0 not greater than 0` — G5 báo **0/5 tổ hợp RÒ** | `thu_g20_dahang.py::test_c2a` **đã được viết lại ở G22** (`assertFalse` thay `assertTrue` — xem §3.1). G5 trên cây thật = **0/5**, đúng hợp đồng `N-G21-03`. Ca cũ lại đòi **>0** ⇒ coi "hết rò" là "bộ dò mù". | **Lỗi TEST (STALE)** — giả định NGƯỢC với hợp đồng đã duyệt | Đòi **0/5** trên cây thật; thêm **đối chứng tiêm**: tắt luật ECHO THEO TÊN trên bản sao TẠM ⇒ G5 phải **2/5** VÀ `test_c2a` phải **ĐỎ** |
| `Z6` `test_z6_moi_ca_phu_dinh_deu_co_doi_chung_duong` | FAIL: `ĐỐI CHỨNG DƯƠNG CHƯA CHẠY THẬT cho: ['cay-sach-3-ban-sao']` | `E1` skip vì `HEAD ≠ NEN` **trước khi** chạy phép tiêm ⇒ đối chứng dương của nhóm **không hề chạy**. `Z6` bắt đúng — đây là **lỗ hổng thật của bộ kiểm**, không phải của sản phẩm. | **Lỗi TEST (thiếu đối chứng thật)** | Thêm `_doi_chung_cong_cay_sach_o_clone_nen()`: clone thật tại nền, (a) cây sạch ⇒ 3/3 XANH, (b) tiêm `admin/__tiem_g22.js` ⇒ 3/3 ĐỎ-THẬT; chạy **trước** khi `E1` skip |
| `A1` `test_a1_cay_dung_bang_cay_cua_nen` | FAIL: `'LỖI(rc=128)' != TREE_NEN` | `git write-tree` bị sandbox chặn ghi `.git` (`index.lock`); thêm nữa ghim nền `3b7e93b` khác worktree `a76ec51`. | **MÔI TRƯỜNG** — ngoài phạm vi (AGENT 03) | Không sửa. Ghi thẳng, không giả xanh |
| `B2`/`B3` | FAIL `(3,10,52)` / `0 ca ĐẠT` — `Executable doesn't exist ... chromium_headless_shell-1194` | Thiếu nhị phân Chromium revision 1194 trong `.local-browsers`; không phải lỗi sản phẩm. | **MÔI TRƯỜNG** — ngoài phạm vi (AGENT 01) | Không sửa. Ghi thẳng |

> **KẾT LUẬN PHÂN LOẠI:** trong 5 ca thuộc phạm vi, **0 lỗi nghiệp vụ**, **5 lỗi TEST** (4 STALE +
> 1 thiếu đối chứng thật). Không có ca nào bị xoá, bị `skip`, hay bị hạ assert.

---

## 3. ĐỐI CHIẾU VỚI HỢP ĐỒNG ĐÃ DUYỆT (không sửa hợp đồng cho khớp test sai)

### 3.1 `N-G21-03` — `test_c2a` đã được viết lại TRƯỚC lượt này

**Quan trọng:** ở `HEAD a76ec51`, `app/thu/thu_g20_dahang.py::CaGanChat::test_c2a` **không còn**
`assertTrue(ket_qua["gia_ngan"])`. Tệp đã có ghi chú "ĐÃ VIẾT LẠI Ở G22" và dùng:

```python
self.assertFalse(ket_qua["gia_ngan"], "RÒ: credential NGẮN của hãng giả lọt ra ngoài ...")
self.assertFalse(ket_qua["gia_ngan_2"], "RÒ: ...")
```

Đo trực tiếp (lệnh thật, mã thoát thật):

```sh
$ python3 app/thu/thu_g20_dahang.py CaGanChat.test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia
# → Ran 1 test in 0.119s · OK          EXIT 0
```

Vì thế **không sửa tệp đó** (ngoài phạm vi). Việc của lượt này là sửa **ca kiểm** `G1` trong
`thu_qa_g22.py`, ca này đang đòi một hành vi RÒ phải tồn tại — trái với hợp đồng đã duyệt.

### 3.2 E3 — mốc thời gian là THAM SỐ (`docs/G22_SAOLUU.md` §5)

| Bất biến đã duyệt | Ca đo tương ứng | Cách đo sau khi sửa |
|---|---|---|
| `sao_luu(luc=)` / `khoi_phuc(..., luc=)` nhận mốc qua **tham số**; `luc=None` mới đọc `datetime.now()` | `F1` | `inspect.signature` trong tiến trình con + đòi `nhan_luc_*` là `True` |
| Ba lượt khôi phục **CÙNG MỘT MỐC** ⇒ **3** bản cất, không xoá nhau | `F1` | truyền `luc="20261016-120000"` cho cả ba lượt; đếm đúng **3**; cả ba tên bắt đầu bằng `hub-truoc-rollback-20261016-120000` |
| Bản cất phải **giữ được dữ liệu** vừa mất | `F1` | ghi `x=2` trước khi khôi phục; mở từng bản cất `immutable=1`, đòi mở được và ≥1 bản có `MAX(x)=2` |
| Kết quả **tất định**, không phụ thuộc tốc độ máy | `F3` | chạy lại với `G22_LEO_THANG=1` (mỗi lượt đọc nhích 1 giây): bản thật + `luc=` vẫn **3** và **cùng mốc** |
| Bản TRƯỚC G22 phải **ĐÈ** (1 bản cất) để chứng minh lỗ hổng CÓ THẬT | `F2` | chạy cùng script trên `migrate_nguyenban.py` (md5 ghim, **không nhận `luc`**): **1** bản cất |

### 3.3 `N-G21-03` — bất biến "credential NGẮN của BẤT KỲ hãng nào không được rò"

| Vế | Đo bằng | Điều kiện ĐẠT |
|---|---|---|
| Ca trong cây không ghim rò | đọc `thu_g20_dahang.py` | **KHÔNG** có `self.assertTrue(ket_qua["gia_ngan"...])`; **CÓ** `self.assertFalse(...)` cho cả `gia_ngan` và `gia_ngan_2` |
| Ca còn chạy được | `python3 app/thu/thu_g20_dahang.py CaGanChat.test_c2a...` | `rc=0`, `Ran 1 test`, `OK`, **không** `skipped=` |
| Lỗ rò đã đóng (bộ đo độc lập) | `python3 app/thu/thu_qa_g21.py G5_CredentialNgan` | `rc=0`, **`tổ hợp RÒ=0/5`** |
| Bộ dò KHÔNG mù (đối chứng tiêm) | bản sao TẠM, tắt `_gia_tri_echo_theo_ten` | G5 đọc **2/5** (>0) **VÀ** `test_c2a` trên bản tiêm **rc=1**, lỗi có chữ `RÒ` |

Bản tiêm chỉ nằm trong `TMP` (`tempfile.mkdtemp`); cây thật không bị chạm.

### 3.4 `Z6` — mọi ca phủ định phải có ĐỐI CHỨNG DƯƠNG **ĐÃ CHẠY THẬT**

`Z6` không được nới. Thay vào đó, nhóm thiếu đối chứng (`cay-sach-3-ban-sao`) nay có đối chứng
**chạy thật** trên clone tại nền:

| Vế | Đo trên clone `--shared` tại `NEN_SHA` | Kết quả |
|---|---|---|
| Cây SẠCH | 3 cổng `thu_qa_g17` / `thu_qa_g18` / `thu_g20_baomat` | `g17 rc=0 XANH` · `g18 rc=0 XANH` · `g20_baomat rc=0 XANH` |
| TIÊM `admin/__tiem_g22.js` | cùng 3 cổng | `g17 rc=1 DO_THAT` · `g18 rc=1 DO_THAT` · `g20_baomat rc=1 DO_THAT` |

Chỉ khi **cả hai vế** đúng thì `DA_CHAY` và `DA_TIEM` của nhóm mới được bật. Nếu phép tiêm trượt,
`E1` **FAIL** (không phải skip) và `Z6` tiếp tục ĐỎ — không có cờ suông.

---

## 4. BẢNG TRƯỚC / SAU Ở MỨC TỪNG CA

| Ca | TRƯỚC | SAU | Số đo quyết định sau khi sửa |
|---|---|---|---|
| `F1` | **FAIL** (`rc=1`, không đo được E3) | **PASS** | `sao_luu(luc=)` 3 tệp · `khoi_phuc(luc=)` **3** bản cất · cả 3 mở được · 1 bản giữ `x=2` · cùng mốc |
| `F2` | **ERROR** (`RuntimeError` vá chuỗi) | **PASS** | TRƯỚC (đóng băng): nhận `luc`=**False**, **1** bản cất · SAU: nhận `luc`=**True**, **3** bản cất |
| `F3` | **FAIL** (regex cũ) | **PASS** | bản cũ: cùng giây **1** / nhích giây **3** (XANH GIẢ) · bản thật + `luc=`, nhích giây **3**, cùng mốc **True** |
| `G1` | **FAIL** (đòi rò >0) | **PASS** | cây thật **0/5** · tiêm **2/5** · `test_c2a` cây thật `rc=0 OK`, bản tiêm `rc=1 RÒ` |
| `Z6` | **FAIL** (thiếu `cay-sach-3-ban-sao`) | **PASS** | 10/10 nhóm `đã chạy đối chứng=True` · 3 nhóm bắt buộc `đã tiêm lỗi=True` |
| `A1` | FAIL | **FAIL** (không đổi) | `write-tree=LỖI(rc=128)` — sandbox chặn ghi `.git`; ngoài phạm vi |
| `B2` | FAIL | **FAIL** (không đổi) | `(3,10,52)` — thiếu Chromium; ngoài phạm vi |
| `B3` | FAIL | **FAIL** (không đổi) | `0 ca ĐẠT` — thiếu `chromium_headless_shell-1194`; ngoài phạm vi |

Không ca nào bị xoá. Số ca vẫn là **24** (bằng đúng mốc Controller đo). Không thêm `skipTest` mới.

---

## 5. CÒN LẠI — NÓI THẲNG, KHÔNG GIẢ XANH

1. **`A1` (AGENT 03):** sandbox chặn ghi `.git` nên `git write-tree` trả **128**; ngoài ra hằng
   `NEN_SHA=3b7e93b` đang là mốc của lượt trước, còn worktree này ở `a76ec51`. Tôi **không** sửa
   ghim nền (việc của AGENT 03) và **không** cho `A1` qua bằng cách nới điều kiện.
2. **`B2`/`B3` (AGENT 01):** thiếu `node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194`.
   Kết quả `B2=(3,10,52)` là **NỬA VỜI** theo sổ, không được tính ĐẠT.
3. **Commit:** sandbox chặn ghi `.git` (`index.lock`). Hai tệp của lượt này cần Controller commit
   vào `integration/g20`:
   * `app/thu/thu_qa_g22.py` — `sha256 ccc8320f750fbaffdb47d3f9d31cd8bd9be2b3ffa975b1770a17acc9599f8095`
   * `docs/G22_CONTRACT.md` — tài liệu này
   `git status` tại thời điểm bàn giao: `M app/thu/thu_qa_g22.py` + `?? docs/G22_CONTRACT.md`.
   **Không push.**
4. **`C4` / D-8:** giữ nguyên trạng thái **BLOCKED OWNER**; lượt này không đo, không sửa, không ép
   xanh phần đó.

---

## 6. NHỮNG GÌ **KHÔNG** BỊ THAY ĐỔI (chống nới cổng)

* `SO_DO`: **không đổi một giá trị nào** — `e3-ba-luot-cung-giay` nền `1` / đóng `3`;
  `ng21-03-ca-ghim-ro` nền `1` / đóng `0`; `cay-sach-3-ban-sao` nền `0` / đóng `3`.
* `dat_cong` / `phan_quyet`: không sửa. Giá trị "nửa vời" vẫn ĐỎ ở cả hai chế độ.
* Không thêm `skipTest`; không xoá ca; không đổi tên ca; `Ran` vẫn 24.
* Không chạm mã sản phẩm (`git status` chỉ có tệp của lượt này).
* Không chạm kiểm tra tenant isolation / phạm vi; các ca `A3`/`A4`/`H` giữ nguyên.
* Không sửa `thu_g20_dahang.py` dù `G1` nói về nó; chỉ **đọc** và **chạy** nó.
* Không `retry` để xanh; mọi phép đo đều tất định nhờ tham số, không nhờ may mắn.

---

## 7. CÁCH TỰ KIỂM LẠI (cho lượt sau)

```sh
# 1) Nhóm F + G — phải OK ở cả hai chế độ:
python3 app/thu/thu_qa_g22.py F_DongHo G_NG2103                    # EXIT 0
VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py F_DongHo G_NG2103 # EXIT 0

# 2) Đối chứng CLONE của nhóm cây sạch (E1 vẫn skip phần "3/3 trên cây này" nếu HEAD≠nền):
python3 app/thu/thu_qa_g22.py E_CaySach                            # EXIT 0, skipped=1

# 3) Toàn bộ — kỳ vọng hiện tại: Ran 24 · failures=3 · skipped=2 · EXIT 1
#    (3 lỗi A1/B2/B3 ngoài phạm vi; đọc §5 trước khi kết luận)
python3 app/thu/thu_qa_g22.py

# 4) Muốn thấy phép đo BẮT ĐƯỢC lỗi (đối chứng âm), xem log in ra của F2/F3/G1:
#    F2: TRƯỚC → 1 bản cất · SAU → 3
#    F3: bản cũ cùng giây → 1 · nhích giây → 3 (XANH GIẢ)
#    G1: cây thật 0/5 · bản tiêm 2/5 · test_c2a bản tiêm rc=1
```

**Ba luật bằng chứng đã giữ:** mọi khẳng định đi kèm lệnh thật + mã thoát thật + số ca + số
skip; không đoán mã trạng thái hãng (không có lời gọi hãng nào); mọi ca phủ định trong phạm vi
đều có đối chứng dương **chạy thật**.
