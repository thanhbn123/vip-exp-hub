# G21 — AG-05: CHỐT "CÂY SẠCH" (TỰ DÒ) + VÂN TAY (GIT LÀ CHÍNH) + MÔI TRƯỜNG GIT (N-G18-00)

**Làn:** AG-05 · **Wave:** G21 · **Nền:** `integration/g20` @ `a3400a8` (cây ĐÃ GỘP)
**Vùng được ghi (đúng 5 đường):** `app/thu/thu_qa_g17.py` · `app/thu/thu_qa_g18.py` ·
`app/thu/thu_g21_chotcay.py` (mới) · `app/thu/chay_tat_ca.sh` (**chỉ phần vân tay**) ·
`docs/G21_CHOTCAY.md` (mới).

**Nhiệm vụ:** đóng **CỔNG C1** và **CỔNG C3** trong bản nghiệm thu G20 của AG-01
(`docs/QA_G20.md` §2.1 và §2.3), cả hai đang **ĐỎ** trên bản đã gộp.

---

## 0. TÓM TẮT — CÁI GÌ ĐỎ, CÁI GÌ ĐÃ XANH, CÁI GÌ CÒN ĐỎ

| # | Khoản | Trước (bản đã gộp `a3400a8`) | Sau (bản vá này) |
|---|---|---|---|
| **C1** | Tệp **ĐƯỢC PHÉP TẠO** không được làm cổng cây sạch của wave trước ĐỎ | **0/2** cổng xanh | **2/2** cổng xanh |
| **C3** | `git` **môi trường nguyên bản** | **128** (`fatal: unable to parse command-line config`) | **vẫn 128 — GỐC chưa vá được từ trong repo**; nhưng nay **PHÂN BIỆT ĐƯỢC** "môi trường hỏng" với "cây hỏng thật", có cảnh báo, và **chứng minh không nuốt lỗi thật** (xem §5) |
| — | Tên ca `A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` mà **chính bộ nghiệm thu AG-01 gọi** | **KHÔNG TỒN TẠI** trên bản đã gộp ⇒ cổng g18 đỏ vì `AttributeError`, không phải vì cây bẩn | **đã trả lại** (hai tên cho cùng một phép đo) — phát hiện `N-G21-01`, xem §6 |
| — | Vân tay (`G16-09`) | mù với `docs/` và `*.md` | Git là CHÍNH, thư mục (băm **nội dung**) là DỰ PHÒNG — **cả hai đều bắt** (xem §4) |
| — | **Bản sao THỨ TƯ** của chốt cây sạch: `thu_g20_baomat.py::A_Nen` | (trên cây G21) **ĐỎ** vì tệp mới của làn khác | **VẪN ĐỎ — ngoài vùng được ghi của làn này.** Xem `N-G21-02` (§6). Đây là lý do `chay_tat_ca.sh` còn `exit 1` |

**Nói thẳng phần CÒN ĐỎ — hai điều, không giấu:**

1. `git rev-parse HEAD` gọi **trực tiếp** (không qua bộ chạy/bộ kiểm) vẫn thoát **128** trên máy này,
   vì `GIT_CONFIG_COUNT=2` mà thiếu `GIT_CONFIG_KEY_0`/`_1` là **biến môi trường của PHIÊN**, không
   phải thứ trong cây mã. Từ trong repo **không** sửa được gốc (§5.1 — đã báo AG-00). Điều tệ hơn đã
   được chặn: **hai nhiệt kế cho hai kết quả khác nhau trên CÙNG một cây**.
2. `sh app/thu/chay_tat_ca.sh` còn **`exit 1`** — vì **hai** bộ đỏ, và **cả hai đều KHÔNG do làn này**:
   `thu_g20_baomat.py` (bản sao thứ tư của danh sách cứng, **ngoài vùng được ghi** — `N-G21-02`) và
   `thu_qa_g18.py::B_Tang3` (khoản nợ `C2` có sẵn, số đo trùng khít nền đóng băng). **Cả hai cổng của
   C1 đều XANH trong chính lượt chạy đó** (`thu_qa_g17.py` 56 ca ✓).

---

## 1. LỆNH ĐO + MÃ THOÁT THẬT + SỐ CA + SỐ SKIP

Mọi mã thoát dưới đây được bắt **NGAY SAU LỆNH, TRƯỚC MỌI PIPE** (`out=$(lệnh 2>&1); ma=$?`).
Mọi lệnh chạy tại gốc cây `g21-ag05-chotcay`, HEAD `a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1`.

| # | Lệnh | Mã thoát | Số ca | Skip |
|---|---|---|---|---|
| 1 | `python3 app/thu/thu_g21_chotcay.py` | **0** | **13** | 0 |
| 2 | `python3 app/thu/thu_qa_g17.py A_Nen.test_a1_cay_sach_va_head` | **0** | **1** | 0 |
| 3 | `python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` | **0** | **1** | 0 |
| 4 | `python3 app/thu/thu_qa_g17.py A_Nen Z_TongKet.test_z2_cay_khong_doi_trong_luot_do` | **0** | **11** | 0 |
| 5 | `python3 app/thu/thu_qa_g18.py A_Nen Z_TongKet.test_z2_cay_khong_doi_trong_luot_do` | **0** | **12** | 0 |
| 6 | `python3 app/thu/thu_g20_baomat.py B_ChotCaySach` (bộ **của wave TRƯỚC**, KHÔNG sửa) | **0** | **7** | 0 |
| 7 | `python3 app/thu/thu_g21_chotcay.py --chot` | **0** | — | — |
| 8 | `python3 app/thu/thu_qa_g18.py B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong` | **1** | **1** | 0 |

Dòng 8 **không phải** hồi quy của làn này: nó là **khoản nợ `C2` có sẵn** (bàn phím trong màn —
`V-13911`), và số đo **trùng khít** bản đóng băng của AG-01:

```
[B1] nhị phân: chỉ định BAN_GIAO §1 (chromium-1194) · mã thoát=1 · 47 đạt · 1 hỏng · 3 bỏ qua
```

(AG-01 G20 §1.4 đo trên nền `148ecd3`: `47 đạt · 1 hỏng · 3 bỏ qua` — **y hệt**.)

### 1.1 Lượt chạy TRỌN BỘ (`sh app/thu/chay_tat_ca.sh`) — và vân tay đứng yên

```
python:   1884 ca · 52 bộ chạy thật
          + 1 bộ BỎ QUA (0 ca): thu_qa_g19.py
frontend: 56 + 36 ca (hai tầng tự động)
E2E:      KẾT QUẢ: 41/41
bộ hỏng:  thu_g20_baomat.py thu_qa_g18.py
=== EXIT_CODE_THAT=1
```

Trong 52 bộ: `thu_qa_g17.py` **56 ca ✓** · `thu_g21_chotcay.py` **13 ca ✓** · `thu_qa_g18.py` 47 ca
(chỉ `B_Tang3` đỏ — khoản nợ `C2` ở trên) · `thu_g20_baomat.py` 27 ca (đỏ vì `N-G21-02`, ngoài vùng
được ghi — xem §6).

Khối vân tay ở **cuối** lượt chạy (chuỗi **giống hệt** trước và sau):

```
VÂN TAY TRƯỚC: HEAD=a3400a8f8e2e · chế độ=THU_MUC · diff HEAD=3 đường · status -uall=5 dòng
  Thư mục (DỰ PHÒNG, băm nội dung): 317 tệp theo dõi = 669b69406d0a2429 · 2 tệp mới = 4d62b801dafe96aa
VÂN TAY SAU:   HEAD=a3400a8f8e2e · chế độ=THU_MUC · diff HEAD=3 đường · status -uall=5 dòng
  Thư mục (DỰ PHÒNG, băm nội dung): 317 tệp theo dõi = 669b69406d0a2429 · 2 tệp mới = 4d62b801dafe96aa
  ✓ vân tay KHÔNG ĐỔI (trước = sau) — con số ghim được vào ĐÚNG cây này
```

**`1884 ca · 52 bộ` ghim được vào `HEAD=a3400a8f8e2e` và vào một cây có băm NỘI DUNG không đổi** —
kể cả băm nội dung của 317 tệp theo dõi. Đây là điều luật §41 đòi, và là thứ lệnh vân tay `G16-09`
**không** làm được.

SHA256 của các tệp đã sửa/tạo tại **đúng mốc đo này**:

```
app/thu/thu_g21_chotcay.py   2680ee65c517629cc1346d469ffdd0896de21c405b501e2d7252693cb134f84b
app/thu/thu_qa_g17.py        20edb919e74371dd793ba77702a48f33b91eb850bf1e49d08a8640219a749926
app/thu/thu_qa_g18.py        bc10bd43884572bdf811e98dd9b749e1f90aa0f12724f701a9b2749987850bcf
app/thu/chay_tat_ca.sh       3ae82e670efb94fa19c44cc4dc93dda0aeafb73a4a162610287cf503195d202e
```

Cây lúc kết thúc — **đúng 5 đường được cấp**, không đường nào khác:

```
 M app/thu/chay_tat_ca.sh
 M app/thu/thu_qa_g17.py
 M app/thu/thu_qa_g18.py
?? app/thu/thu_g21_chotcay.py
?? docs/G21_CHOTCAY.md
```

---

## 2. CỔNG C1 — "TỆP ĐƯỢC PHÉP TẠO KHÔNG ĐƯỢC LÀM CỔNG CŨ ĐỎ" (ĐÓNG)

### 2.1 Lỗi là gì (đo lại được, không chép lời AG-01)

Bản G20 chữa `N-G19-03` bằng cách **liệt kê ĐÍCH DANH tên tệp của làn khác**:

```python
PHAM_VI_LAN_KHAC = (
    "app/thu/thu_qa_g18.py", "app/thu/thu_g20_baomat.py", "docs/G20_BAOMAT.md",
)
PHAM_VI_WAVE = PHAM_VI_LAN_NHA + PHAM_VI_LAN_KHAC
```

Danh sách ấy phủ **đúng wave G20**. Wave G21 giao tệp mới ⇒ cổng ĐỎ **lần thứ ba** — không phải
vì cây bẩn, mà vì một làn khác vừa làm ĐÚNG việc của mình.

### 2.2 ĐỐI CHỨNG A/B — CÙNG MỘT CÂY, CÙNG TỆP MỚI, CHỈ KHÁC BẢN CỔNG

Dựng cây tạm là **bản sao nguyên trạng** của cây này, đưa **hai cổng về đúng bản ĐÃ GỘP (`HEAD`)**
rồi commit (để chúng SẠCH, không bị chính việc sửa cổng làm đỏ), sau đó giao **hai tệp mới hợp lệ
của một làn khác trong wave** chưa ai khai tên ở bất kỳ danh sách nào:

```
$ git status --porcelain=v1 -uall
?? app/thu/thu_qa_g21.py
?? docs/QA_G21.md
```

| Lượt | `thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` | `thu_qa_g18.py::A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` | Cổng XANH |
|---|---|---|---|
| **(A) bản ĐÃ GỘP (`HEAD`)** | **exit 1** · `Ran 1 test … FAILED (failures=1)` | **exit 1** · `Ran 1 test … FAILED (errors=1)` | **0/2** |
| **(B) bản ĐÃ VÁ (AG-05 G21)** | **exit 0** · `Ran 1 test … OK` | **exit 0** · `Ran 1 test … OK` | **2/2** |

Dòng lỗi của (A) — **chính là phép đo của AG-01**, không phải diễn giải:

```
AssertionError: Lists differ: ['?? app/thu/thu_qa_g21.py', '?? docs/QA_G21.md'] != []
```

Và (A) còn cho thấy một lỗi **thứ hai**, độc lập: cổng g18 đỏ trong **0.000 giây** với
`FAILED (errors=1)`, thông điệp thật là

```
AttributeError: type object 'A_Nen' has no attribute 'test_a1_cay_sach_mien_tru_dung_hai_tep_ag01'
```

⇒ tên ca mà **chính bộ nghiệm thu AG-01 gọi** đã bị bản G20 **đổi tên** mà không giữ bí danh. Cổng
g18 "đỏ" ở đó **không đo gì cả**. Xem `N-G21-01` (§6).

### 2.3 ĐỐI CHỨNG ÂM BẮT BUỘC — BẢNG "TRƯỚC/SAU KHI SỬA TỆP SẢN PHẨM"

Trên **cùng cây tạm đó**, sau khi đã vá:

| Bước | Tệp | g17 | g18 |
|---|---|---|---|
| **TRƯỚC** (không có tệp sản phẩm nào bị đụng) | — | exit **0** | exit **0** |
| **TẠO TỆP SẢN PHẨM** `app/_ag05_ab_tam_san_pham.py` | tệp MỚI ngoài vùng | exit **1** | exit **1** |
| **SAU KHI XOÁ** | — | exit **0** | exit **0** |

Đường bị bắt xuất hiện **nguyên văn** trong thông điệp lỗi: `'?? app/_ag05_ab_tam_san_pham.py'`.

Cùng phép đo ấy nằm **thường trực** trong bộ kiểm, chạy trên **CÂY THẬT**, bốn tầng (`test_a1d`):
hàm thuần · git thật trên cây tạm (sửa `app/webhook.py` đã commit) · git thật trên cây đang đo
(tạo rồi xoá `app/_ag05_doi_chung_am_tam_g1{7,8}.py`) · và **đối chứng DƯƠNG**: tệp mới **TRONG
VÙNG THỬ** ⇒ cổng **vẫn XANH** (đúng `N-G19-03`, đo được chứ không suy luận).

### 2.4 Miễn trừ nay theo **QUY TẮC**, không theo tên tệp

`thu_g21_chotcay` **TỰ DÒ** vùng thử/tài liệu từ cây (`git ls-files`, kể cả tệp chưa theo dõi):
mọi thư mục có tên bắt đầu bằng `thu`, cộng `docs/`. Trên cây này đo được **5 vùng**:

```
('app/thu/', 'docs/', 'gateway/thu/', 'thu_frontend/', 'thu_giao_dien/')
```

`PHAM_VI_LAN_KHAC = ()` — **RỖNG**, và `test_a1b` **canh nó phải rỗng** (đỏ nếu ai đó lại liệt kê
tên tệp). Không ai phải sửa một danh sách nào ở wave sau.

### 2.5 "KHÔNG NỚI LỎNG THÀNH BỎ QUA HẾT" — ba chốt, đo được

1. **Chứng minh vùng không chạy trong sản phẩm** (`chung_minh_vung`), hai phép đo độc lập:
   * (A1) **AST**: không tệp sản phẩm nào `import` / `importlib.import_module` một mô-đun nằm trong
     vùng — đo trên **mọi** tệp `.py`/`.js`/`.mjs` **được theo dõi** nằm ngoài vùng;
   * (A2) **danh sách thư mục TĨNH của máy chủ** (`app/server.py::THU_MUC_CHO_PHEP`) không chứa
     vùng nào ⇒ vùng không đi ra được tới người dùng qua HTTP.
   Chứng minh **hỏng ⇒ `chot_cay_sach()` NÉM LỖI** (không tha mù). Và bộ chứng minh **có răng**:
   `_co_rang_chung_minh_vung()` bơm một vi phạm cố ý và khẳng định nó **thấy được** — nếu không thì
   "0 vi phạm" chỉ là một bộ dò mù.
2. **Đối chứng âm cấp HÀM** (`test_b1`): 9 dòng porcelain giả, gồm cả dòng **ĐỔI TÊN**
   `R  app/gioi_han.py -> thu_giao_dien/gioi_han.py` — dòng đổi tên bị ĐỎ nếu **một trong hai**
   đường nằm ngoài vùng (kéo tệp sản phẩm vào thư mục thử vẫn là thay đổi sản phẩm). Kết quả:
   **6 dòng sản phẩm ĐỎ · 3 dòng trong vùng được tha**.
3. **Bộ đột biến của WAVE TRƯỚC vẫn bắt được** — `thu_g20_baomat.py::B_ChotCaySach`, tệp **KHÔNG
   sửa** trong làn này, `Ran 7 tests … OK`:

```
[B1] thu_qa_g17.py 10 ca ✓ · thu_qa_g18.py 11 ca ✓    (cây ĐANG có 4 tệp của wave)
[B2] tệp SẢN PHẨM mới ⇒ cả hai cổng ĐỎ (mã thoát 1) · xoá ⇒ xanh lại
[B3] tệp lạ ở `mock/` + `gateway/` ⇒ cả hai cổng ĐỎ: thu_qa_g17.py=1 · thu_qa_g18.py=1
[B4] AST trên nguồn hai cổng: phạm vi khai phủ đủ 4 tệp của wave
[B5] đột biến `_loc_cay_ban → []` ở CẢ HAI cổng: `test_a1d` ĐỎ (bản gốc XANH)
[B6] đột biến nhét `app/webhook.py` vào miễn trừ: `test_a1b` ĐỎ (bản gốc XANH)
[B7] `thu_qa_g19.py::A_Nen` mã thoát 0 · 0 ca · 1 bỏ qua
```

`B5` là chốt quan trọng nhất: nó **đột biến chính hàm lọc thành "bỏ qua hết"** và bắt bộ kiểm phải
ĐỎ. Nghĩa là "cây sạch" ở đây **có răng**, không phải một hằng số `[]`.

---

## 3. CỔNG C3 / `N-G18-00` — HAI NHIỆT KẾ TRÊN CÙNG MỘT CÂY (ĐÓNG PHẦN PHÂN BIỆT)

### 3.1 Đo trực tiếp môi trường nguyên bản

```
GIT_CONFIG_COUNT=2 · GIT_CONFIG_KEY_* = 0 · GIT_CONFIG_VALUE_* = 2
$ git rev-parse HEAD                      # KHÔNG gỡ biến
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
→ exit 128
$ git rev-parse HEAD                      # ĐÃ gỡ gia đình biến
→ exit 0 · a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1
```

Đây là **cùng một cây, cùng một `HEAD`, hai kết quả**. Đó là lý do C3 tồn tại.

### 3.2 Bốn luật của bản chuẩn hoá (`thu_g21_chotcay.env_git`)

| Luật | Khẳng định | Ca đo |
|---|---|---|
| (a) **Dị dạng ⇒ chuẩn hoá + CẢNH BÁO** | Thấy `COUNT=2` thiếu `KEY_0`/`KEY_1`, gỡ **cả** gia đình `GIT_CONFIG_*`, in 3 dòng cảnh báo ra `stderr` | `test_e1` |
| (b) **Hợp lệ ⇒ KHÔNG được gỡ** | `COUNT=1, KEY_0=user.name, VALUE_0=ag05` giữ **nguyên 3/3** biến — gỡ nó là **nuốt một cấu hình thật** | `test_e4` |
| (c) **KHÔNG nuốt lỗi thật** | Sau chuẩn hoá: git **ngoài cây git** vẫn hỏng (128) · `rev` không tồn tại vẫn hỏng (128) · `_git_hoac_chet` **NÉM** `RuntimeError` kèm mã thoát + `stderr` nguyên văn | `test_e3`, `test_e2` |
| (d) **Một chỗ duy nhất** | `thu_qa_g17.py`, `thu_qa_g18.py`, `chay_tat_ca.sh` đều gọi `thu_g21_chotcay`; ba bản sao của cùng một luật chính là khuôn `N-G18-00` | `thu_g20_baomat.py::_git` là bản thứ tư **của wave trước, không sửa**; nó vẫn xanh |

Dòng cảnh báo in ra (nguyên văn, `stderr`):

```
[cảnh báo N-G18-00] GIT_CONFIG_COUNT=2 nhưng THIẾU KEY_0, KEY_1 ⇒ MỌI lệnh git thoát 128
[cảnh báo N-G18-00] đã GỠ 3 biến: GIT_CONFIG_COUNT, GIT_CONFIG_VALUE_0, GIT_CONFIG_VALUE_1
[cảnh báo N-G18-00] đây là MÔI TRƯỜNG hỏng, KHÔNG phải cây hỏng — lệnh git hỏng vì lý do THẬT
                    vẫn sẽ hỏng và được báo nguyên văn.
```

### 3.3 `chay_tat_ca.sh` — phần vân tay (được phép sửa)

Bộ chạy **đã** tự chuẩn hoá từ G18 (khối giữ nguyên). Nay phần **vân tay** được thêm vào, và nó
dùng **cùng một** hiện thực:

* trước khi chạy: `--van-tay-ghi <tệp>` — ghi vân tay + in chế độ đang dùng;
* sau khi chạy: `--van-tay-so <tệp>` — so và **mã thoát NÓI RÕ cái gì đã đổi**:

| Mã thoát | Nghĩa | Xử lý trong `chay_tat_ca.sh` |
|---|---|---|
| 0 | không đổi | ✓ |
| 1 | `HEAD` đổi | **HỎNG** (số đo thuộc hai mốc mã) |
| 2 | **nội dung tệp ĐÃ THEO DÕI** đổi (kể cả `docs/*.md`) | **HỎNG** |
| 3 | chỉ tập tệp **CHƯA theo dõi** đổi (một làn giao tệp giữa lượt chạy) | **CẢNH BÁO** + liệt kê đường |
| 4 | không đo được vân tay | **HỎNG** (số đo không ghim được) |

**Vì sao 2 ≠ 3:** một lượt sửa `docs/*.md` giữa lúc đo làm **số đo vô hiệu** (đúng `G16-09`); một
làn khác giao thêm tệp giữa lượt chạy thì số đo vẫn đúng cho những gì **đã chạy**, nhưng con số
"`N` bộ · `M` ca" **không tái lập nguyên vẹn** — nên nó là cảnh báo **có tên đường**, không phải
một dòng im lặng.

---

## 4. VÂN TAY — GIT LÀ CHÍNH, THƯ MỤC (BĂM NỘI DUNG) LÀ DỰ PHÒNG

### 4.1 Ba tầng, và tầng thứ ba là tầng đáng giá

| Tầng | Phủ gì | Mù với gì |
|---|---|---|
| **CHÍNH** — `git rev-parse HEAD` + `git diff HEAD` + `status --porcelain -uall` | mọi tệp **được theo dõi** (kể cả `docs/**`, `*.md`, `.gitignore`) + mọi thay đổi **chưa commit** | nội dung của một tệp **đã bẩn sẵn** (tên không đổi) |
| **theo TÊN** — `{ git ls-files -s; git status --porcelain -uall; } \| sha256` | rẻ, cùng phạm vi như trên | như trên |
| **THƯ MỤC (DỰ PHÒNG)** — sha256 **NỘI DUNG** mọi tệp **không bị `.gitignore`** (theo dõi **và** chưa theo dõi) | **mọi** thay đổi nội dung, kể cả trên tệp đã bẩn sẵn | — (đắt hơn: băm ~300 tệp) |

Vì sao **không** băm cả cây làm việc: `thu_giao_dien/_bao-cao/**`, `_ket-qua/**`,
`app/du-lieu/khoa-noi-bo.key`, `__pycache__/**` **đổi sau MỖI lượt chạy** (đo được ở
`docs/QA_G20.md` §1.0); băm chúng thì vân tay báo "cây đã đổi" mỗi lần và người đọc sẽ học cách bỏ
qua nó. Vân tay thư mục ở đây lọc bằng chính `.gitignore` của dự án.

### 4.2 CHỨNG MINH BẰNG CÁCH SỬA MỘT TỆP `.md` RỒI ĐO LẠI (đúng yêu cầu)

Tệp bị sửa: `docs/SHARED_CONTRACTS.md` — **chính bản hợp đồng**, đúng chỗ bản mù `G16-09` để lọt.
Tệp được khôi phục **nguyên byte** trong `finally` + `atexit`, và việc khôi phục được **kiểm lại
bằng git** (`git diff --exit-code` → 0).

| Vân tay | Trước | Sau khi sửa | Kết luận |
|---|---|---|---|
| **Git (CHÍNH)** | `diff HEAD` không có `docs/SHARED_CONTRACTS.md` | `diff HEAD` **+1 đường**, đúng tên tệp | **BẮT ĐƯỢC** |
| **THƯ MỤC (băm nội dung)** | `theo_doi = …` | **đổi** | **BẮT ĐƯỢC** |
| **theo TÊN** | `…` | **đổi** | **BẮT ĐƯỢC** |
| **bản MÙ `G16-09`** (`find app gateway thu_frontend thu_giao_dien` + 4 đuôi tệp) | `…` | **KHÔNG ĐỔI** | **MÙ** — đúng lỗi cũ, giữ lại làm **đối chứng âm** |

Và ca thứ tư — chỗ mà "theo TÊN" **mù** còn "THƯ MỤC" **không** (`test_d3`): tạo một tệp **chưa
theo dõi**, ghi nội dung `A`, đo; ghi nội dung `B` (**cùng tên**), đo lại:

```
vân tay theo TÊN  : KHÔNG đổi   (dòng porcelain `?? X` trước và sau y hệt)
vân tay THƯ MỤC   : ĐỔI
```

### 4.3 Mã thoát thật của bộ so vân tay (đo trên cây này)

```
$ python3 app/thu/thu_g21_chotcay.py --van-tay-ghi /tmp/vt.json      → exit 0
$ python3 app/thu/thu_g21_chotcay.py --van-tay-so  /tmp/vt.json      → exit 0  "✓ vân tay KHÔNG ĐỔI"
$ printf '\n' >> docs/SHARED_CONTRACTS.md
$ python3 app/thu/thu_g21_chotcay.py --van-tay-so  /tmp/vt.json      → exit 2
    ✗ NỘI DUNG tệp ĐÃ THEO DÕI ĐỔI … : docs/SHARED_CONTRACTS.md
$ <khôi phục nguyên byte>
$ python3 app/thu/thu_g21_chotcay.py --van-tay-so  /tmp/vt.json      → exit 0  "✓ vân tay KHÔNG ĐỔI"
```

---

## 5. NHỮNG GÌ **KHÔNG** ĐƯỢC ĐÓNG (lỗ hổng phạm vi, KHÔNG phải ĐẠT)

### 5.1 Gốc của `N-G18-00` **chưa vá được từ trong repo**

`GIT_CONFIG_COUNT=2` + `GIT_CONFIG_VALUE_0/1` mà **thiếu** `GIT_CONFIG_KEY_0/1` là **biến môi
trường của PHIÊN chạy** (do terminal/harness đặt), không phải một tệp trong cây. Không tệp nào
trong repo có thể làm `git` gọi **trực tiếp** bởi người khác thoát 0. Vì thế C3 chỉ đóng được phần
**phân biệt + chứng minh không nuốt lỗi thật**; phần "`git` trần thoát 0" **thuộc AG-00/harness**
(gỡ `GIT_CONFIG_COUNT` và `GIT_CONFIG_VALUE_*` khỏi môi trường spawn agent, hoặc đặt đủ cặp
`GIT_CONFIG_KEY_i`/`VALUE_i`). **Đã báo AG-00** — không tự vượt.

### 5.2 Hai khẳng định trong `app/thu/thu_qa_g20.py` đang **PIN HÀNH VI CŨ**

`thu_qa_g20.py` là **bộ nghiệm thu của wave trước**, **ngoài vùng được ghi của làn này** ⇒ tôi
**KHÔNG sửa**, tôi **ĐO** và ghi lại. Hai khẳng định dưới đây mô tả **khoản nợ**, nên trên một cây
ĐÃ VÁ chúng **phải được đảo lại** (việc của AG-01 ở lượt 2):

```python
# thu_qa_g20.py:640  — mô tả LỖI: "g18 KHÔNG miễn trừ tệp AG-01 G20"
self.assertFalse(q18._la_tep_ag01("?? %s" % TEP_CUA_AG01_G20[0]), ...)
# thu_qa_g20.py:650  — mô tả LỖI: "g17 KHÔNG thấy tệp AG-01 G20 là bẩn"
self.assertTrue(all(any(t in d for d in ban) for t in dang_co), ...)
```

Trên cây đã vá, `docs/QA_G20.md` **được tha theo QUY TẮC** (nó nằm trong `docs/`) — đó chính là
điều **phải** xảy ra. Hai dòng trên pin đúng cái **ngược lại**, nên `test_g1` sẽ vẫn ĐỎ dù `dat_cong`
đã đạt **2/2**. Nói rõ để không ai đọc "2/2 mà vẫn đỏ" thành "bản vá không có tác dụng".

Để **giảm thiểu** thiệt hại, hai tên hàm cũ được giữ **nguyên ngữ nghĩa HẸP** có chủ ý:
`_la_tep_ag01(x)` = "x có thuộc **họ bộ kiểm nghiệm thu** của wave này không" (KHÁC chốt), và
`_cay_ban(ngoai=())` = **hàm thuần** trả về **mọi** dòng bẩn (không có chính sách ẩn). Nhờ vậy các
phép đo **cấu trúc** còn lại của AG-01 vẫn chạy đúng câu hỏi của chúng; chỉ hai dòng **mô tả khoản
nợ** ở trên là phải viết lại.

**Đo lại bốn vị từ ấy trên đúng đầu vào mà `thu_qa_g20.py` dùng** (`exit=0`):

```
TEP_CUA_AG01_G18 = ('docs/QA_G18*.md', 'app/thu/thu_qa_g18*.py')
A) q18._la_tep_ag01('?? docs/QA_G18*.md')              = True    ← assertTrue (dòng 638) PASS
B) q18._la_tep_ag01('?? docs/QA_G20.md')               = False   ← assertFalse (dòng 640) PASS
C) q17._cay_ban()  → 5 dòng (MỌI dòng bẩn, hàm thuần)  ← assertTrue (dòng 650) PASS trên cây AG-01
D) q17._cay_ban(ngoai=TEP_CUA_AG01_G20) → 5 đường của làn này
   (trên cây AG-01, nơi chỉ hai tệp của họ bẩn, biểu thức này trả [] ← assertEqual (dòng 652) PASS)
E) q17._loc_cay_ban(['?? docs/QA_G20.md']) = ['?? docs/QA_G20.md']   ← hàm thuần, không chính sách ẩn
```

⇒ Trên **cây của chính AG-01**, toàn bộ `test_g1` — kể cả hai dòng pin-hành-vi-cũ — vẫn **PASS**;
chúng chỉ mâu thuẫn với bất biến mới **khi chạy trên cây ĐÃ VÁ có tệp mới**. Nói cách khác: bản vá
này **không** làm hỏng bộ nghiệm thu cũ ở chỗ nó đo đúng.

### 5.3 Chưa đo

| # | Mục | Vì sao |
|---|---|---|
| 1 | `thu_qa_g20.py` chạy **toàn bộ** ở chế độ `VIP_G20_CHE_DO=gop` | Bộ đó gọi tầng 3 Chromium + hồi quy toàn phần (~11 phút) và `thu_qa_g20.py` **không nằm trong cây này** (nó thuộc worktree `g20-ag01-qa`). Lượt 2 của AG-01 sở hữu phép đo đó |
| 2 | Sửa `thu_qa_g20.py` cho khớp bất biến mới | **Ngoài vùng được ghi** — đã báo ở §5.2 |
| 3 | Gọi API hãng thật, kể cả sandbox (`V-G09-01`, `V-13906-05`) | **BỊ CẤM**. Mọi phép đo ở đây chỉ chạm `127.0.0.1` cổng OS cấp, hoặc không chạm mạng |
| 4 | Cổng `:5432` (dữ liệu dự án khác) | **CHẶN CỨNG** — không kết nối, không đụng |
| 5 | Vùng thử **mới** do wave sau tạo (ví dụ `thu_xyz/`) | Quy tắc tự khớp ⇒ **được tha ngay**; `test_a1b` sẽ ĐỎ nếu lời khai tĩnh trong nguồn **trôi** khỏi cây, để nó không trôi trong im lặng |
| 6 | Vùng thử bị **import bởi mã sản phẩm** trong tương lai | `chung_minh_vung()` sẽ **NÉM LỖI** ⇒ cổng ĐỎ. Đây là **hành vi thiết kế**, chưa có ca thật để đo |

---

## 6. PHÁT HIỆN MỚI

### `N-G21-01` · **CAO** · Bộ nghiệm thu gọi một tên ca **không còn tồn tại** — và không ai báo

`thu_qa_g20.py` (§`CONG_CAY_SACH`) gọi:

```python
["python3", "app/thu/thu_qa_g18.py", "A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01"]
```

Trên nền đóng băng `148ecd3` tên này **có** (đo được: `g20-ag01-qa` dòng 517). Bản G20 **đổi tên**
nó thành `test_a1_cay_sach_theo_pham_vi_wave` mà **không giữ bí danh**. Trên bản đã gộp, lệnh của
AG-01 vì thế **không đo cây** — nó đo **sự tồn tại của một cái tên**:

```
Ran 1 test in 0.000s · FAILED (errors=1)
AttributeError: type object 'A_Nen' has no attribute 'test_a1_cay_sach_mien_tru_dung_hai_tep_ag01'
```

Đây là dạng hỏng nguy hiểm nhất của một bộ kiểm: **ĐỎ vì lý do khác hẳn** lý do được báo, và dòng
tóm tắt (`exit 1`) trông y hệt một khoản nợ thật. **Đã vá:** cả hai tên cùng tồn tại, cùng một
phép đo (`thu_qa_g18.py::test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` gọi thẳng ca kia).

### `N-G21-02` · **CAO** · Cùng một lỗi còn **BA bản sao nữa**, và một trong ba bản ấy làm đỏ cả bộ chạy

`N-G18-03`/`N-G19-03` (miễn trừ bằng **danh sách tên cứng**) không chỉ nằm ở `thu_qa_g17.py` và
`thu_qa_g18.py`. Đo được **ba** chỗ nữa trên cây này:

| # | Tệp · ca | Danh sách cứng | Trạng thái đo được |
|---|---|---|---|
| 1 | `app/thu/thu_g20_baomat.py::A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | `TEP_CUA_WAVE_G20` (4 tên) | **ĐỎ** trên cây G21 — xem dưới |
| 2 | `app/thu/thu_qa_g19.py::A_Nen` | `TEP_CUA_AG01_G19` (2 tên) | **DORMANT** (tự bỏ qua: HEAD ≠ nền đóng băng) |
| 3 | `app/thu/thu_g20_baomat.py` (phạm vi tự thân, `B4`) | đọc AST hai cổng kia | ✓ xanh |

Đo trực tiếp bản (1) — **nó đỏ chỉ vì ba đường hợp lệ của làn này**:

```
$ python3 app/thu/thu_g20_baomat.py A_Nen          → exit 1
AssertionError: Lists differ:
  [' M app/thu/chay_tat_ca.sh', '?? app/thu/thu_g21_chotcay.py', '?? docs/G21_CHOTCAY.md'] != []
```

**Hệ quả vận hành, nói thẳng:** miễn là bản (1) còn danh sách cứng, `sh app/thu/chay_tat_ca.sh`
**exit 1 trên MỌI cây G21** có tệp mới của bất kỳ làn nào — kể cả khi mọi bộ thử đều xanh. Đây đúng
cái bẫy mà `CỔNG C1` mô tả, chỉ đổi chỗ: người nghiệm thu sẽ đọc "bộ chạy đỏ" thành "G21 làm hỏng G20".

**Tôi KHÔNG tự sửa** bản (1) và (2): cả hai **ngoài vùng được ghi** của làn này (`AG-00` giới hạn
đúng 5 đường). Bản vá đề nghị cho (1) là **2 dòng** — cho mặc định phạm vi của `_loc_cay_ban` dùng
`thu_g21_chotcay.mau_vung_chuan()` thay cho `TEP_CUA_WAVE_G20`, **giữ nguyên** hằng số cũ (để `B4`
đọc AST vẫn đúng) và **giữ nguyên** toàn bộ `B1`–`B7`. **Đã báo AG-00** kèm hai lựa chọn.

---

## 7. TUÂN THỦ TUYỆT ĐỐI — tự kiểm bằng máy, không bằng lời

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng, kể cả sandbox | Không một URL ngoài `127.0.0.1` nào được thêm; mọi phép đo HTTP của tệp này **không tồn tại** (không có lớp HTTP nào) | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | Không lệnh `git push`/`ssh`/tunnel nào. `chay_tat_ca.sh` giữ nguyên chế độ bind `127.0.0.1`; tệp này **không** bind cổng nào | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | Không đọc `.env`; CSDL tạm; log chỉ chứa đường dẫn + mã thoát | ✓ |
| 4 | Đoán mã trạng thái hãng (D-4) | Không chạm bảng ánh xạ trạng thái nào | ✓ |
| 5 | Chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | Chuyển CSDL nghiệp vụ sang PostgreSQL (D-8) | Không đọc/ghi cổng `:5432`; `thu_g20_baomat::B7` và `thu_qa_g18::Z3` vẫn đo cụm riêng | ✓ |
| 7 | Dùng Claude/mô hình khác · tự bấm duyệt sandbox | Không một lời gọi mô hình nào; **không** escalate sandbox lần nào (`.git` bị chặn ghi ⇒ dùng `git show` + ghi tệp trong workspace, **không** tự vượt) | ✓ |
| 8 | Xoá hàng loạt · sửa ngoài phạm vi | `git status --porcelain -uall` chỉ có đúng các đường được cấp (xem §1) | ✓ |

---

## 8. VIỆC CÒN LẠI CHO AG-00 / AG-01

1. **AG-00** — gỡ `GIT_CONFIG_COUNT` + `GIT_CONFIG_VALUE_0/1` khỏi môi trường spawn agent (gốc
   `N-G18-00`, §5.1). Nếu không thì C3 **không thể** đóng ở tầng "git trần".
2. **AG-00** — commit 5 đường của làn này (sandbox chặn ghi `.git` ⇒ tôi **không** tự commit).
3. **AG-00** — quyết `N-G21-02`: cho tôi (hoặc người khác) sửa **2 dòng** trong
   `app/thu/thu_g20_baomat.py`, hoặc chấp nhận `chay_tat_ca.sh` `exit 1` trên **mọi** cây G21 có tệp
   mới. Đã escalate kèm hai lựa chọn.
3. **AG-01 (lượt 2)** — đảo hai khẳng định pin-hành-vi-cũ trong `thu_qa_g20.py` (§5.2), và trong
   `thu_qa_g21.py` dùng **cả hai** tên ca của g18.
4. **AG-01 (lượt 2)** — khi chốt lại C1: đo bằng **exit code** của hai lệnh ở §1 (2) và (3), và
   giữ **đối chứng âm** (tạo một tệp sản phẩm ⇒ cả hai phải ĐỎ). Một cổng xanh mà không có đối
   chứng âm là một cổng **chưa biết có răng hay không**.
