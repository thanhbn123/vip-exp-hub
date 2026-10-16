# G22 — AG-05: ĐO **CẢ N BẢN SAO** CỦA CHỐT "CÂY SẠCH" (TỰ DÒ) — ĐÓNG `N-G21-02`

**Làn:** AG-05 · **Wave:** G22 · **Nền:** `integration/g21` @ `7344c02` (nhánh làm việc `g21-ag05-chotcay`)
**HEAD lúc đo:** `7a60385a02deb1b65cf3cca72a7aa8ee83cc7524` (toàn bộ số đo dưới đây thuộc **đúng** mốc này)
**Vùng được ghi (7 đường):** `app/thu/thu_qa_g19.py` (phần phạm vi miễn trừ — AG-00 đã cho phép) ·
`app/thu/thu_qa_g17.py` · `app/thu/thu_qa_g18.py` · `app/thu/thu_g21_chotcay.py` ·
`app/thu/thu_g20_baomat.py` · `app/thu/thu_g22_chotcay.py` (**mới**) · `docs/G22_CHOTCAY.md` (**mới**).

**Ba việc được giao:** (1) vá **bản sao thứ ba** của `N-G19-03` trong `thu_qa_g19.py` và làm nó
**ĐO ĐƯỢC**; (2) tìm nguyên nhân và vá **bản sao thứ tư** trong `thu_g20_baomat.py::A_Nen`;
(3) báo AG-00 **`N-G21-02` nằm ở tệp nào** — không tự vượt phạm vi.

> **Kết quả gọn:** số bản sao thật là **4**, không phải 2 (G21 báo) và cũng không phải 3 (QA yêu cầu).
> Cả **4/4** nay XANH, còn **RĂNG**, và miễn trừ đến từ **luật vùng dùng chung**.
> `N-G21-02` **đã đóng**: hai đường còn lại đều **nằm trong vùng được ghi của lượt này** — xem §5.

---

## 0. TÓM TẮT — CÁI GÌ ĐỎ, CÁI GÌ ĐÃ XANH

| # | Khoản | Trước | Sau |
|---|---|---|---|
| **C1** | Tệp **ĐƯỢC PHÉP TẠO** của làn khác không được làm cổng "cây sạch" của wave trước ĐỎ | **2/4** bản sao xanh (G17, G18) · 1 bản **ĐỎ** (`thu_g20_baomat.py::A_Nen`, làm `chay_tat_ca.sh` exit 1 trên **mọi** cây có tệp mới) · 1 bản **DORMANT** (`thu_qa_g19.py::A_Nen`, chạy **0 ca**) | **4/4** bản sao XANH, mỗi bản **> 0 ca**, trên cây **đang có** tệp mới của làn khác (xem §1, §2) |
| **RĂNG** | Bản vá **không** được là "bỏ qua hết" | chỉ đo được ở G17/G18 | **4/4** bản sao ĐỎ khi có tệp **SẢN PHẨM** tạm, XANH LẠI sau khi xoá (`D3`, §2) |
| **N-G21-02** | Ba bản sao còn lại của cùng lỗi | 1 ĐỎ + 1 DORMANT + 1 ngoài vùng được ghi | **ĐÓNG** — cả hai đều trong vùng được ghi của G22 (§5); quét toàn kho **không** còn bản sao thứ năm |
| **ĐẾM** | Cách đếm bản sao | một **danh sách tên** viết trong báo cáo (`0/2 → 2/2`) | **QUY TẮC tự dò trên cây** (`thu_g22_chotcay.py --bang`): bản sao thứ năm tự vào bảng, không ai phải nhớ |

**Nói thẳng phần KHÔNG làm được — một điều, không giấu:**

`git rev-parse HEAD` gọi **trần** (không qua bộ chạy/bộ kiểm) vẫn thoát **128** trên máy này, vì
`GIT_CONFIG_COUNT=2` mà thiếu `GIT_CONFIG_KEY_0`/`_1` là **biến của PHIÊN**, không phải thứ trong
cây mã (`N-G18-00` §5.1 của `docs/G21_CHOTCAY.md`). Từ trong repo **không** sửa được gốc; mọi bộ
thử ở đây đều đi qua `thu_g21_chotcay.env_git()` (chuẩn hoá **kèm cảnh báo**, không nuốt lỗi thật).

---

## 1. LỆNH ĐO + MÃ THOÁT THẬT + SỐ CA + SỐ SKIP

Mọi mã thoát được bắt **NGAY SAU LỆNH, TRƯỚC MỌI PIPE** (`out=$(lệnh 2>&1); ma=$?`). Mọi lệnh
chạy tại gốc cây, HEAD `7a60385a02deb1b65cf3cca72a7aa8ee83cc7524`.

| # | Lệnh | Mã thoát | Số ca | Skip |
|---|---|---|---|---|
| 1 | `python3 app/thu/thu_qa_g17.py A_Nen` | **0** | **10** | 0 |
| 2 | `python3 app/thu/thu_qa_g18.py A_Nen` | **0** | **11** | 0 |
| 3 | `python3 app/thu/thu_qa_g19.py A_Nen` (bản sao **thứ ba** — nay chạy THẬT) | **0** | **7** | 0 |
| 4 | `python3 app/thu/thu_g20_baomat.py A_Nen` (bản sao **thứ tư**) | **0** | **8** | 0 |
| 5 | `python3 app/thu/thu_qa_g19.py` (trọn bộ) | **0** | **29** | **18** |
| 6 | `python3 app/thu/thu_g20_baomat.py` (trọn bộ) | **0** | **28** | 0 |
| 7 | `python3 app/thu/thu_g21_chotcay.py` | **0** | **13** | 0 |
| 8 | `python3 app/thu/thu_g22_chotcay.py` (bộ mới) | **0** | **11** | 0 |
| 9 | `python3 app/thu/thu_g21_chotcay.py --chot` | **0** | — | — |
| 10 | `python3 app/thu/thu_g22_chotcay.py --bang` | **0** | — | — |

**Dòng 3 + 5 đọc cho đúng:** `A_Nen` của `thu_qa_g19.py` **chạy 7 ca** (trước: **0 ca**, `OK
(skipped=1)`); 18 ca bị bỏ qua ở dòng 5 là **sáu khoản nợ C1..C6 + bốn phép đột biến + hồi quy +
tầng 3** — chúng khẳng định nợ G19 **còn nguyên**, nên trên cây đã gộp **phải** bỏ qua, và chúng
**vẫn bỏ qua y như trước**. `test_z4` in ra đúng danh sách nhóm CHẠY / nhóm BỎ QUA, nên
`OK (skipped=18)` không thể bị đọc nhầm thành "tất cả đều xanh".

**Dòng 6 so với G21:** `docs/G21_CHOTCAY.md` ghi `thu_g20_baomat.py` **27 ca, ĐỎ** (`N-G21-02`).
Nay **28 ca, XANH**: 27 ca cũ + `B8` (đối chứng âm cho chính bản sao thứ tư).

SHA256 của các tệp **đã sửa/tạo**, tại đúng mốc đo này:

```
app/thu/thu_qa_g19.py        761f104dd457c1a09da227dd7d41cc768a1775ce371e7062edca1f942ace0ebf
app/thu/thu_g20_baomat.py    91de6da7e3463fa24a32111c088497974db29f0fac53748d70bffb587908228f
app/thu/thu_g22_chotcay.py   363a3e02885a64093e50ebe32b861910c212015cef7fe3ecd6b8bc6115f7eed3
app/thu/thu_qa_g17.py        20edb919e74371dd793ba77702a48f33b91eb850bf1e49d08a8640219a749926   (KHÔNG đổi)
app/thu/thu_qa_g18.py        bc10bd43884572bdf811e98dd9b749e1f90aa0f12724f701a9b2749987850bcf   (KHÔNG đổi)
app/thu/thu_g21_chotcay.py   2680ee65c517629cc1346d469ffdd0896de21c405b501e2d7252693cb134f84b   (KHÔNG đổi)
```

Ba tệp cuối **không đổi một byte** so với G21 — vùng được ghi cho 7 đường, nhưng chỉ **3** đường
thật sự cần sửa: `thu_qa_g17.py`/`thu_qa_g18.py`/`thu_g21_chotcay.py` **đã đúng** từ lượt trước.

Cây lúc kết thúc — **đúng 4 đường**, không đường nào khác (3 đường mã + 1 tài liệu này):

```
 M app/thu/thu_g20_baomat.py
 M app/thu/thu_qa_g19.py
?? app/thu/thu_g22_chotcay.py
?? docs/G22_CHOTCAY.md
```

---

## 1.1 LƯỢT CHẠY TRỌN BỘ (`sh app/thu/chay_tat_ca.sh`) — và vân tay ĐỨNG YÊN

Chạy trên cây **đã đứng yên** (mọi tệp mã đã xong; chỉ còn mục này được ghi **sau** lượt chạy —
nên lượt chạy tự in vân tay **TRƯỚC = SAU**, xem dưới):

```
$ sh app/thu/chay_tat_ca.sh
  ✓ thu_g20_baomat.py          28 ca
  ✓ thu_g21_chotcay.py         13 ca
  ✓ thu_g22_chotcay.py         11 ca
  ✓ thu_qa_g17.py              56 ca
  ✗ thu_qa_g18.py              47 ca  HỎNG (mã thoát 1)
  ✓ thu_qa_g19.py              29 ca
  python:   1925 ca · 54 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  thu_qa_g18.py
=== EXIT_CODE_THAT=1

VÂN TAY TRƯỚC: HEAD=7a60385a02de · chế độ=THU_MUC · diff HEAD=2 đường · status -uall=4 dòng
VÂN TAY SAU:   HEAD=7a60385a02de · chế độ=THU_MUC · diff HEAD=2 đường · status -uall=4 dòng
  ✓ vân tay KHÔNG ĐỔI (trước = sau) — con số ghim được vào ĐÚNG cây này
```

**So với G21 (cùng lệnh, cùng bộ chạy) — ba chỗ đổi, đúng ba chỗ được sửa:**

| Bộ | G21 | G22 |
|---|---|---|
| `thu_g20_baomat.py` | **27 ca · HỎNG** (`N-G21-02`) | **28 ca · ✓** |
| `thu_qa_g19.py` | **BỎ QUA (0 ca)** | **29 ca · ✓** |
| `thu_g22_chotcay.py` | (chưa có) | **11 ca · ✓** |
| `python:` | 1884 ca · 52 bộ | **1925 ca · 54 bộ** (+29 +11 +1 = +41) |

### `exit 1` của lượt chạy — ĐỌC LOG TRƯỚC KHI PHÁN, và nó **không** do lượt này

Bộ chạy còn **đúng một** bộ đỏ: `thu_qa_g18.py`. Đọc log của chính ca đỏ
(`.../veh_g18_ag01_qa_log/tang3.log`):

```
  ✘  42 [chromium] › thu_giao_dien/06_ban_phim.spec.js:153:1 › 04 — Tab vào được các điều khiển
     TRONG màn, không chỉ quanh menu (1.1s)
    Error: 30 lượt Tab chỉ vào được 1 điều khiển trong màn
  1 failed · 3 did not run · 47 passed (2.0m)
```

Đây là **khoản nợ `C2` có sẵn** (`V-13911` — điều hướng bàn phím trong màn), đã được AG-01 ghi ở
G20 và G21: số đo **trùng khít** bản đóng băng (`47 đạt · 1 hỏng · 3 bỏ qua`, AG-01 G20 §1.4 đo
trên nền `148ecd3`). Ba điều được kiểm riêng để loại trừ "đỏ GIẢ do sandbox chặn ghi":

1. đây **không** phải lỗi ghi tệp — `thu_giao_dien/_bao-cao/` và `_ket-qua/` **có** tệp mới
   (`06_ban_phim-04-…/test-failed-1.png`, `error-context.md`, `.last-run.json`);
2. ca đỏ là **một** spec bàn phím, không phải một loạt ca cùng đỏ vì hạ tầng;
3. `thu_qa_g19.py` (bộ từng bị **BỎ QUA**) nay **29 ca ✓**, và `thu_g20_baomat.py` (bộ từng **ĐỎ**
   vì `N-G21-02`) nay **28 ca ✓** — hai chỗ đỏ cũ **đã hết**, nên `exit 1` còn lại **không** thể
   quy cho lượt này.

**Kết luận:** `chay_tat_ca.sh` **exit 1 chỉ vì `C2`** — nợ có sẵn, ngoài phạm vi lượt này và
ngoài cả vùng được ghi (không tệp nào của lượt này chạm `06_ban_phim.spec.js` hay `thu_qa_g18.py`).

---

## 2. BỐN BẢN SAO — BẢNG TRƯỚC/SAU VÀ BA PHÉP ĐO CHO MỖI BẢN

### 2.1 Số bản sao là **4** — đo bằng QUY TẮC, không bằng danh sách

`python3 app/thu/thu_g22_chotcay.py --bang` (exit **0**):

```
BẢNG BẢN SAO CHỐT "CÂY SẠCH" — TỰ DÒ, KHÔNG LIỆT KÊ TÊN
VÙNG THỬ/TÀI LIỆU (tự dò): ('app/thu/', 'docs/', 'gateway/thu/', 'thu_frontend/', 'thu_giao_dien/')
MẪU VÙNG (tự dò): ('app/thu/**', 'docs/**', 'gateway/thu/**', 'thu_frontend/**', 'thu_giao_dien/**')
BẢN SAO                        SỐ CA  XANH       BẢN CŨ BỊ BẮT QUY TẮC   NGUỒN VÙNG
app/thu/thu_g20_baomat.py      1      ✓          ✓ (9df7bee8) ✓         gọi `mau_vung_chuan` trong `_mau_chot`
app/thu/thu_qa_g17.py          1      ✓          ✓ (9df7bee8) ✓         tuple khai trong mô-đun: PHAM_VI_WAVE
app/thu/thu_qa_g18.py          2      ✓          ✓ (9df7bee8) ✓         tuple khai trong mô-đun: PHAM_VI_WAVE
app/thu/thu_qa_g19.py          1      ✓          ✓ (a42c1d79) ✓         tuple khai trong mô-đun: PHAM_VI_WAVE
KẾT LUẬN: 4/4 bản sao ĐẠT cả XANH lẫn QUY TẮC · 0 bản HỎNG
```

Cách dò (`bo_ung_vien`) **không** chứa tên tệp nào: nó quét mọi `thu_*.py` trong VÙNG THỬ/TÀI LIỆU
(vùng cũng tự dò) và giữ những mô-đun có lớp `A_Nen` với ca tên chứa `cay_sach`. Quy tắc này có
**đối chứng dương** (`D5`: bản sao giả dựng trong cây tạm **phải** được tìm ra) và **đối chứng âm**
(`D6`: nguồn theo danh sách cứng **phải** bị bắt). Không có hai đối chứng ấy thì "4/4" chỉ là một
con số của một bộ dò có thể đang mù.

### 2.2 Ba phép đo cho mỗi bản sao — **3/3** mỗi bản, **12/12** toàn bộ

| Bản sao | ① XANH (ca cổng trên cây thật) | ② RĂNG (tệp SẢN PHẨM tạm ⇒ ĐỎ) | ③ QUY TẮC (nguồn) | Tỉ lệ |
|---|---|---|---|---|
| `thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` | exit **0** · 1 ca | exit **1** (`FAIL:`) ⇒ xoá ⇒ **0** | ✓ | **3/3** |
| `thu_qa_g18.py::A_Nen.test_a1_cay_sach_theo_pham_vi_wave` (+ bản tên cũ) | exit **0** · 2 ca | exit **1** ⇒ xoá ⇒ **0** | ✓ | **3/3** |
| `thu_qa_g19.py::A_Nen.test_a1_head_dung_ghim_va_cay_sach` | exit **0** · 1 ca | exit **1** ⇒ xoá ⇒ **0** | ✓ | **3/3** |
| `thu_g20_baomat.py::A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | exit **0** · 1 ca | exit **1** ⇒ xoá ⇒ **0** | ✓ | **3/3** |

Phép đo ② chạy trong `D3` (bộ mới) trên **cả bốn** bản sao trong cùng một lượt:

```
  [D3] RĂNG — tệp sản phẩm tạm ⇒ 4/4 bản sao ĐỎ (thu_g20_baomat.py=1 · thu_qa_g17.py=1 ·
       thu_qa_g18.py=1 · thu_qa_g19.py=1) · xoá đi ⇒ XANH LẠI
```

Phép đo ① **có chống rỗng**: `D2` khẳng định cây **thật sự** có thay đổi **ngoài làn** của từng bản
sao (`thay_doi_ngoai_lan`), nếu không thì "xanh" không chứng minh được gì — đúng cách G21 đếm ra
`2/2` trên một cây mà hai bản sao kia **không hề được chạy**.

```
  [D1] TỰ DÒ 4 bản sao của chốt cây sạch:
        · app/thu/thu_g20_baomat.py    A_Nen.test_a1_cay_sach_theo_pham_vi_wave
        · app/thu/thu_qa_g17.py        A_Nen.test_a1_cay_sach_va_head
        · app/thu/thu_qa_g18.py        A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01, A_Nen.test_a1_cay_sach_theo_pham_vi_wave
        · app/thu/thu_qa_g19.py        A_Nen.test_a1_head_dung_ghim_va_cay_sach
  [D2] C1 — 4/4 bản sao XANH trên cây có tệp mới của làn khác:
        · app/thu/thu_g20_baomat.py    mã thoát 0 · 1 ca · 0 bỏ qua
        · app/thu/thu_qa_g17.py        mã thoát 0 · 1 ca · 0 bỏ qua
        · app/thu/thu_qa_g18.py        mã thoát 0 · 2 ca · 0 bỏ qua
        · app/thu/thu_qa_g19.py        mã thoát 0 · 1 ca · 0 bỏ qua
        cây có 4 dòng `git status` (ngoài làn của từng bản sao ⇒ phép đo không rỗng)
```

### 2.3 Bảng TRƯỚC/SAU — đo trên **nguồn thật trong lịch sử git**, không phải nguồn tự bịa

`D4` lấy bản **ngay trước lần vá gần nhất** của từng tệp bằng `git log` + `git show` (không ghim
SHA nào), rồi chạy **cùng một hàm đo** `kiem_quy_tac` lên cả hai bản:

```
  [D4] QUY TẮC — 4/4 bản sao ĐẠT; bản NGAY TRƯỚC khi vá của từng tệp đều BỊ BẮT:
        · app/thu/thu_g20_baomat.py    cũ 9df7bee8 bị bắt (chuỗi gọi của ca cổng KHÔNG lấy miễn trừ
                                       từ luật vùng dùng chung, và mô-đun không khai tuple mẫu vùng)
        · app/thu/thu_qa_g17.py        cũ 9df7bee8 bị bắt (...)
        · app/thu/thu_qa_g18.py        cũ 9df7bee8 bị bắt (...)
        · app/thu/thu_qa_g19.py        cũ a42c1d79 bị bắt (...)
```

Và **phép đo HÀNH VI** của bản cũ — chạy CHÍNH mã cũ (đọc bằng `git show`, đặt cạnh tệp gốc để nó
tự suy đúng gốc cây) trên cây **đang có tệp mới hợp lệ của làn khác**:

| Bản sao | Bản CŨ (rev) | Lệnh | Mã thoát | Số ca | Kết quả |
|---|---|---|---|---|---|
| `thu_qa_g17.py` | `9df7bee` | `A_Nen.test_a1_cay_sach_va_head` | **1** | 1 | `AssertionError: Lists differ: [...] != []` |
| `thu_qa_g18.py` | `9df7bee` | `A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **1** | 1 | `AssertionError: Lists differ: [...] != []` |
| `thu_qa_g19.py` | `7a60385` | `A_Nen.test_a1_head_dung_ghim_va_cay_sach` | 0 | **0** | `OK (skipped=1)` — **DORMANT**, không đo gì |
| `thu_g20_baomat.py` | `7a60385` | `A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **1** | 1 | `AssertionError: Lists differ: [...] != []` |

Nguyên văn danh sách ĐỎ của bản `thu_g20_baomat.py` cũ (đầy đủ, `maxDiff=None`):

```
AssertionError: Lists differ: [...] != []
First list contains 6 additional elements.
+ []
- [' M app/thu/thu_qa_g19.py',
-  '?? app/thu/_ag05_chay_truoc.py',
-  '?? app/thu/_ag05_truoc_g20.py',
-  '?? app/thu/thu_g22_chotcay.py',
-  '?? app/thu/thu_qa_g22.py',
-  '?? docs/QA_G22.md'] : CÂY BẨN ngoài phạm vi wave (F0) ⇒ mọi số đo vô hiệu: [...]
Ran 1 test in 0.013s        (mã thoát 1)
```

Bốn đường trong danh sách ấy là **tệp mới hợp lệ của làn khác** (` M app/thu/thu_qa_g19.py` = bản vá
thứ ba; `?? app/thu/thu_g22_chotcay.py` = bộ đo mới của G22; `?? app/thu/thu_qa_g22.py` + `?? docs/QA_G22.md`
= hai tệp **mô phỏng làn G22** dựng ra cho phép đo này). Hai đường còn lại (`_ag05_chay_truoc.py`,
`_ag05_truoc_g20.py`) là **dụng cụ của chính phép đo** — và chúng cũng là tệp mới trong vùng thử,
nên chúng cũng đúng là loại đường làm cổng cũ ĐỎ. Cả 6 đường **đều nằm trong VÙNG THỬ/TÀI LIỆU**,
và sau bản vá cả 6 đều được tha — xem `D2`.

---

## 3. VIỆC 1 — BẢN SAO **THỨ BA** (`thu_qa_g19.py`): HAI lỗi, không phải một

### 3.1 Lỗi thứ nhất: miễn trừ bằng danh sách hai tên

```python
TEP_CUA_AG01_G19 = ("app/thu/thu_qa_g19.py", "docs/QA_G19.md")     # dòng 79 — BẢN CŨ
...
return duong in TEP_CUA_AG01_G19                                   # `_la_tep_ag01`
```

Cùng một lỗi `N-G18-03`/`N-G19-03`: một làn KHÁC giao tệp mới là cổng ĐỎ. **Đã vá** đúng như cách
đã làm cho `g17`/`g18`: miễn trừ theo **QUY TẮC VÙNG** (`PHAM_VI_WAVE` + `_chot_do()`), tệp mới do
`git status -uall` **TỰ TÌM**, kèm phép **CHỨNG MINH VÙNG** (không tệp sản phẩm nào import vùng;
`app/server.py::THU_MUC_CHO_PHEP` không phục vụ vùng) — chứng minh hỏng thì chốt **TỪ CHỐI tha**.

Hai câu hỏi được tách ra như ở `g17`/`g18`, **không trộn**:
`PHAM_VI_LAN_NHA` + `_la_tep_ag01` = câu hỏi **HẸP** ("tệp của CHÍNH làn AG-01 G19", dùng cho
`do_cong_cay_sach_wave_truoc` + `test_h2` — giữ nguyên độ hẹp, nới ra là làm phép đo ấy trả lời SAI
câu hỏi); `PHAM_VI_WAVE` + `_chot_do()` = câu hỏi **RỘNG** (chốt "cây sạch").

### 3.2 Lỗi thứ hai — **và đây mới là lý do QA chỉ đếm được 2**: bản sao thứ ba **DORMANT**

`setUpModule` cũ `raise unittest.SkipTest` khi `HEAD != 6e61fc1`, tức **bỏ qua CẢ BỘ** — kể cả
`A_Nen`, vốn là một **TÍNH CHẤT** (cây sạch) phải đúng trên **mọi** cây. Hệ quả đo được:

```
$ python3 app/thu/thu_qa_g19.py A_Nen          # BẢN CŨ
skipped 'BỘ ĐO NỀN — HEAD 7a60385 != nền đóng băng 6e61fc1. ...'
Ran 0 tests in 0.008s
OK (skipped=1)                                  # mã thoát 0 — và KHÔNG đo gì
```

Một cổng "xanh" mà chạy **0 ca** là một cổng **không tồn tại**: bản sao thứ ba nằm im trong đó, và
mọi báo cáo dựa trên việc chạy nó đều là báo cáo về một phép đo chưa từng xảy ra.

**Đã vá:** chốt "nền đóng băng" chuyển từ `setUpModule` (bỏ qua **cả bộ**) sang **từng nhóm**
(`_chi_tren_nen`, gắn cho `B..J`). Sáu khoản nợ C1..C6 + bốn phép đột biến + hồi quy/tầng 3 **vẫn
bỏ qua y như cũ** (18 ca, §1 dòng 5); `A_Nen` (cây sạch · chốt an toàn · D-8) và `Z_TongKet` (sổ
đối chứng · vân tay) nay **chạy trên mọi cây**. Đây **không phải** nới điều kiện cho qua: không
nhóm nợ nào được tha — chỉ một nhóm **trước đây bị bỏ qua OAN** nay được đo.

### 3.3 Bản sao thứ ba nay có đủ ba cổng tự kiểm như hai bản kia

| Ca | Đo cái gì | Kết quả |
|---|---|---|
| `test_a1_head_dung_ghim_va_cay_sach` | chốt "cây sạch" theo QUY TẮC + chứng minh vùng | exit 0 |
| `test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu` | mẫu KHAI BÁO **bằng** mẫu TỰ DÒ; `PHAM_VI_LAN_KHAC` **rỗng** | exit 0 |
| `test_a1c_ban_du_phong_khop_ban_dung_chung` | bản DỰ PHÒNG tại chỗ **khớp** `thu_g21_chotcay` + bắt được vi phạm cố ý | exit 0 |
| `test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO` | tệp SẢN PHẨM ⇒ ĐỎ (4 tầng); tệp trong VÙNG ⇒ vẫn XANH | exit 0 |

**Vì sao có bản DỰ PHÒNG (`test_a1c`)**: bộ này còn phải chạy trên NỀN ĐÓNG BĂNG
(`VIP_G19_HEAD=6e61fc1`), nơi `thu_g21_chotcay.py` (ra đời ở G21) **không tồn tại**. Bản dự phòng
cài **đúng một quy tắc** ấy tại chỗ, và ca `a1c` **ĐO** rằng hai bản khớp nhau (vùng + phép chứng
minh) — nếu không thì lại là "hai nhiệt kế, hai kết quả" (`N-G18-00`). Thiếu tệp là trạng thái
**hợp lệ** (có lý do in ra); tệp **có** mà import hỏng thì **nổi lên**, không bị nuốt.

### 3.4 MỘT LỖI THẬT do chính ĐỐI CHỨNG ÂM bắt được — ghi lại, không giấu

Khi kiểm đường DỰ PHÒNG (tạm chuyển `thu_g21_chotcay.py` ra chỗ khác rồi chạy
`python3 app/thu/thu_qa_g19.py A_Nen`), **`test_a1d` ĐỎ**:

```
AssertionError: Lists differ: [...] != [...]
Second list contains 1 additional elements.
First extra element 4:
'R  app/gioi_han.py -> thu_giao_dien/gioi_han.py'
  ... : hàm lọc NUỐT tệp sản phẩm ⇒ cổng mất răng
Ran 7 tests ... FAILED (failures=1, skipped=1)      # mã thoát 1
```

**Nguyên nhân:** bản đầu của `_duong_porcelain` (đường dự phòng) chỉ trả **đường ĐÍCH** của một
dòng đổi tên, nên dòng `R  app/gioi_han.py -> thu_giao_dien/gioi_han.py` bị coi là "nằm trong vùng
thử" và bị **lọc mất** — đúng ca "kéo một tệp SẢN PHẨM vào thư mục thử" mà chú thích của chính hàm
ấy nói là phải ĐỎ. Khi **có** `thu_g21_chotcay.py`, `_loc_cay_ban` mượn
`chotcay.duong_tu_dong_porcelain` (trả **cả hai** đường) nên lỗi **ẩn**; nó chỉ lộ ra trên đường
dự phòng, tức trên **nền đóng băng**.

**Đã sửa:** `_duong_porcelain` trả **cả hai** đường, và `_loc_cay_ban` **luôn** dùng bản tại chỗ
(một luật, không mượn bản ngoài cho câu hỏi này); `test_a1c` thêm phép so **trực tiếp** hai bộ đọc
trên sáu dòng mẫu (kể cả hai chiều của một dòng đổi tên, và một đường có dấu cách trong ngoặc kép).
Đo lại **cả hai** đường:

| Đường | Lệnh | Mã thoát | Số ca | Skip |
|---|---|---|---|---|
| CÓ `thu_g21_chotcay.py` | `python3 app/thu/thu_qa_g19.py A_Nen` | **0** | **7** | 0 |
| **THIẾU** `thu_g21_chotcay.py` (dự phòng) | `python3 app/thu/thu_qa_g19.py A_Nen` | **0** | **7** | **1** (`a1c` tự bỏ qua, có in lý do) |

Đây là điều đáng ghi lại nhất của lượt này: **đối chứng âm không phải thủ tục trang trí** — nó bắt
được một lỗi thật mà mọi phép đo "xanh" khác đều không thấy, vì lỗi chỉ tồn tại trên một đường
chạy hiếm khi được dùng tới.

---

## 4. VIỆC 2 — BẢN SAO **THỨ TƯ** (`thu_g20_baomat.py::A_Nen`)

### 4.1 Nguyên nhân — đo được, không suy đoán

```python
TEP_CUA_WAVE_G20 = ("app/thu/thu_qa_g17.py", "app/thu/thu_qa_g18.py",
                    "app/thu/thu_g20_baomat.py", "docs/G20_BAOMAT.md")     # BỐN TÊN CỨNG
def _loc_cay_ban(dong, pham_vi=TEP_CUA_WAVE_G20): ...                       # mặc định = danh sách ấy
```

`A_Nen.test_a1` gọi `_loc_cay_ban(dong)` — **không truyền đối số thứ hai**, nên **mặc định** chính
là thứ đang lọc. Đo trực tiếp trên cây trước khi vá:

```
$ printf 'probe\n' > docs/_ag05_probe.md
$ python3 app/thu/thu_g20_baomat.py A_Nen.test_a1_cay_sach_theo_pham_vi_wave    # BẢN CŨ
AssertionError: Lists differ: ['?? docs/_ag05_probe.md'] != []
Ran 1 test ... FAILED (failures=1)          # mã thoát 1
```

**Hệ quả vận hành:** `A_Nen` nằm trong bộ chạy chung ⇒ `sh app/thu/chay_tat_ca.sh` **exit 1 trên
MỌI cây G21** có tệp mới của bất kỳ làn nào — kể cả khi mọi bộ thử đều xanh. Người nghiệm thu đọc
"bộ chạy đỏ" thành "G21 làm hỏng G20". Đây đúng cái bẫy `CỔNG C1` mô tả, chỉ đổi chỗ.

### 4.2 Bản vá — và hai điều CỐ Ý

- `_chot_do()` (mới) lấy mẫu miễn trừ từ **luật vùng dùng chung** (`thu_g21_chotcay.mau_vung_chuan`)
  và **chứng minh vùng vô hại** trước khi tha; `A_Nen.test_a1` gọi `_chot_do()`.
- `TEP_CUA_WAVE_G20` **GIỮ NGUYÊN**: `B4` đọc nó bằng AST, `Z3`/`VAN_TAY_CUOI` dùng nó làm phạm vi
  vân tay "đổi giữa lượt đo". Chỉ **CHỐT F0** đổi sang quy tắc vùng — không đụng phép đo khác.
- **Thiếu luật vùng ⇒ KHÔNG tha đường nào** (hướng AN TOÀN), và in lý do ra. Cổng chặt oan thì
  nhìn thấy được và sửa được; cổng tha oan thì im lặng. `B8` đo đúng cả hai hướng này.
- `B7` được **viết lại theo bất biến ĐÚNG**: bản cũ pin một phép **TUYỂN** ("g19 bỏ qua ĐƯỢC, hoặc
  chạy mà xanh") — tức nó pin **SỰ THẬT MÔI TRƯỜNG** (cây này có phải nền đóng băng không) chứ
  không pin **TÍNH CHẤT**, nên nó xanh kể cả khi bản sao thứ ba còn nguyên lỗi. Nay `B7` khẳng
  định: chạy **THẬT** (> 0 ca), mã thoát **0**, `PHAM_VI_WAVE` có thật và **toàn mẫu vùng**,
  `PHAM_VI_LAN_KHAC` **rỗng**. Không ca nào bị xoá.

### 4.3 Bản sao thứ tư nay có đối chứng âm của CHÍNH NÓ

`B8` (mới, 3 tầng): hàm thuần · **hướng an toàn** khi thiếu luật vùng · **git thật trên cây đang
đo** (tệp trong `app/` ⇒ chốt ĐỎ; xoá ⇒ XANH LẠI; tệp trong VÙNG THỬ ⇒ vẫn XANH). Trước đây bản
sao thứ tư chỉ được "đo" gián tiếp qua `B1`–`B6` (vốn đo **g17/g18**).

---

## 5. VIỆC 3 — `N-G21-02` Ở TỆP NÀO: BÁO CÁO CHO AG-00

`docs/G21_CHOTCAY.md` §6 định nghĩa `N-G21-02` = *"cùng một lỗi còn BA bản sao nữa"*. Vị trí chính
xác, đo trên cây:

| # | Đường | Trước G22 | Vùng được ghi của G22? | Nay |
|---|---|---|---|---|
| (1) | `app/thu/thu_g20_baomat.py` → `class A_Nen` → `test_a1_cay_sach_theo_pham_vi_wave`, qua `_loc_cay_ban` (mặc định `TEP_CUA_WAVE_G20`, 4 tên) | **ĐỎ** trên mọi cây G21 có tệp mới ⇒ `chay_tat_ca.sh` exit 1 | **CÓ** (đường thứ 5 trong danh sách được cấp) | **ĐÃ VÁ** (§4) |
| (2) | `app/thu/thu_qa_g19.py` → `class A_Nen` → `test_a1_head_dung_ghim_va_cay_sach`, qua `_la_tep_ag01` (`TEP_CUA_AG01_G19`, 2 tên) | **DORMANT** (0 ca) | **CÓ** — AG-00 cho phép rõ trong đề bài ("phần phạm vi miễn trừ") | **ĐÃ VÁ** (§3) |
| (3) | `app/thu/thu_g20_baomat.py` → `B_ChotCaySach.test_b4_...` (đọc AST hai cổng kia) | ✓ xanh — **không phải** bản sao của lỗi, chỉ là phép đo phụ thuộc | CÓ | giữ nguyên (vẫn xanh) |

**Nên `N-G21-02` KHÔNG còn phần nào nằm ngoài vùng được ghi — không cần AG-00 cấp thêm quyền.**
Để khẳng định điều đó bằng máy chứ không bằng lời, đã quét **toàn kho**:

```
$ python3 - <<'PY'   # quét 102 tệp .py trong app/ gateway/ thu_giao_dien/ admin/ mock/ pages/ thu_frontend/
   ... tệp nào có `--porcelain` VÀ một tuple literal các chuỗi ...
PY
  app/thu/thu_g20_baomat.py    tuple=3 ['TEP_CUA_WAVE_G20', 'BO_THU_DANG_DO', 'TEN_KHAI_PHAM_VI']
  app/thu/thu_g21_chotcay.py   tuple=2 ['DUOI_TEP_BAN_MU_G16_09', 'GOC_BAN_MU_G16_09']
  app/thu/thu_g22_chotcay.py   tuple=1 ['MAU_TEP_THU']
  app/thu/thu_qa_g17.py        tuple=3 ['PHAM_VI_LAN_NHA', 'PHAM_VI_WAVE', 'THU_MUC_PHAM_VI']   (có mẫu vùng)
  app/thu/thu_qa_g18.py        tuple=4 [...]                                                     (có mẫu vùng)
  app/thu/thu_qa_g19.py        tuple=7 [...]                                                     (có mẫu vùng)
```

Sáu tệp có `--porcelain` — **đúng bốn** là chốt cây sạch (`g17`, `g18`, `g19`, `g20`);
`thu_g21_chotcay.py` là **luật vùng dùng chung** (không miễn trừ tệp nào), `thu_g22_chotcay.py` là
**bộ đo** (danh sách đuôi tệp + quy tắc đặt tên, không miễn trừ đường nào). **Không có bản sao thứ năm.**
Script `app/thu/chay_tat_ca.sh` chỉ dùng `--porcelain` qua `thu_g21_chotcay.py --van-tay` (vân tay),
không có danh sách miễn trừ cứng nào.

**Đề nghị cho AG-00:** `N-G21-02` **đóng**. Việc còn lại chỉ là **commit 3 đường** của lượt này
(sandbox chặn ghi `.git` ⇒ tôi **không** tự commit, xem §7 dòng 7) — và gỡ `GIT_CONFIG_*` khỏi môi
trường spawn agent (`N-G18-00`, gốc chưa vá được từ trong repo).

---

## 6. BẢNG ĐỐI CHỨNG ÂM — mọi ca phủ định đều có đối chứng DƯƠNG

| Phép đo | Ca ÂM (phải TỪ CHỐI) | Đối chứng DƯƠNG (phải CHO QUA) |
|---|---|---|
| Chốt "cây sạch" của **từng** bản sao | tệp **SẢN PHẨM** tạm ⇒ **4/4 ĐỎ** (`D3`) | tệp mới trong **VÙNG THỬ** ⇒ **4/4 XANH** (`D2`) |
| Bộ **DÒ** bản sao (`bo_ung_vien`) | (không tìm ra ⇒ mù) | bản sao **GIẢ** trong cây tạm ⇒ **TÌM RA** (`D5`) |
| Hàm **QUY TẮC** (`kiem_quy_tac`) | nguồn **DANH SÁCH TÊN CỨNG** ⇒ **HỎNG** (`D6`) | nguồn **THEO QUY TẮC** ⇒ **ĐẠT** (`D6`) |
| Bảng **TRƯỚC/SAU** | bản **CŨ** trong git ⇒ **BỊ BẮT** (`D4`) | bản **ĐANG DÙNG** ⇒ **ĐẠT** (`D4`) |
| **CHỨNG MINH VÙNG** | vi phạm cố ý (sản phẩm import vùng) ⇒ **BẮT ĐƯỢC** (`D7`) | cây thật ⇒ **0 vi phạm** (`D7`) |
| **HƯỚNG AN TOÀN** của bản sao thứ tư | thiếu luật vùng ⇒ **KHÔNG tha** `docs/**` (`B8`) | có luật vùng ⇒ tha `docs/**`, ĐỎ với `app/**` (`B8`) |
| Bản sao **thứ ba** (g19) | `_loc_cay_ban(gia)` với `ngoai=()` ⇒ **trả MỌI dòng** (`a1d` tầng 1) | `_loc_cay_ban(["?? app/thu/thu_g22_chotcay.py"], PHAM_VI_WAVE)` ⇒ `[]` (`a1d` tầng 1) |
| Bản sao **thứ ba** không **DORMANT** trở lại | — | `g20::B7` khẳng định `> 0 ca` — chạy 0 ca là **ĐỎ** |

---

## 7. TUÂN THỦ TUYỆT ĐỐI — tự kiểm bằng máy, không bằng lời

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng, kể cả sandbox (`V-G09-01`, `V-13906-05` chưa cấp) | Ba tệp sửa/tạo **không mở cổng nào**, không URL nào ngoài `127.0.0.1`; bộ mới **không có** lớp HTTP | ✓ |
| 2 | Push / deploy / tunnel · bind ngoài loopback · mở `CHO_PHEP_LIVE` | Không lệnh `git push`/`ssh`/tunnel nào; `thu_g22_chotcay.py` chỉ chạy **các bộ thử khác** trong tiến trình con trên **cùng cây** | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | Không đọc `.env`; mọi bộ thử tự dùng CSDL tạm; log chỉ có đường dẫn + mã thoát | ✓ |
| 4 | Đoán mã trạng thái hãng (`D-4`) | Không chạm bảng ánh xạ trạng thái nào (không tệp nào trong lượt này nhắc `MA_VTP_*`) | ✓ |
| 5 | Chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | Chuyển CSDL nghiệp vụ sang PostgreSQL (`D-8`) · cấm cổng `:5432` | Không đọc/ghi `:5432`; `thu_g20_baomat::A5/A7` + `thu_qa_g19::A4/Z3` vẫn đo | ✓ |
| 7 | Dùng Claude/mô hình khác · **tự bấm duyệt sandbox** | Không một lời gọi mô hình nào; **không** escalate lần nào — chỗ nào sandbox chặn ghi `.git` thì **báo AG-00 commit**, không tự vượt | ✓ |
| 8 | Xoá hàng loạt · sửa ngoài phạm vi | `git status --porcelain -uall` **đúng 4 đường** (3 đường mã + tài liệu này), cả 4 nằm trong 7 đường được cấp; **không** tệp tạm nào còn sót (`Z2` của g20/g22) | ✓ |

**Không xoá ca nào.** `B7` của `thu_g20_baomat.py` được **viết lại** (không xoá) vì ca cũ pin một
phép tuyển đã sai; mọi ca khác giữ nguyên tên và nội dung.

---

## 8. VIỆC CÒN LẠI CHO AG-00 / AG-01

1. **AG-00** — commit **3 đường** của lượt này (`app/thu/thu_qa_g19.py`, `app/thu/thu_g20_baomat.py`,
   `app/thu/thu_g22_chotcay.py`) + `docs/G22_CHOTCAY.md`. Sandbox chặn ghi `.git` ⇒ tôi không tự commit.
2. **AG-00** — gỡ `GIT_CONFIG_COUNT` + `GIT_CONFIG_VALUE_0/1` khỏi môi trường spawn agent
   (`N-G18-00`): không gỡ thì `git` **trần** vẫn 128, và lại có nguy cơ "hai nhiệt kế".
3. **AG-01 (lượt sau)** — khi chốt lại **C1**, đếm bằng `python3 app/thu/thu_g22_chotcay.py --bang`
   (quy tắc, tự dò) thay vì bằng một danh sách tên trong báo cáo; và giữ **đối chứng âm** (tệp sản
   phẩm ⇒ ĐỎ). Một cổng xanh mà không có đối chứng âm là một cổng **chưa biết có răng hay không**.
4. **AG-01 (lượt sau)** — nếu viết bộ thử mới có cổng "cây sạch": đặt lớp `A_Nen` + ca tên chứa
   `cay_sach`, lấy miễn trừ từ `thu_g21_chotcay.mau_vung_chuan()`. Khi đó nó **tự vào** bảng của
   `thu_g22_chotcay.py` mà không ai phải sửa danh sách nào — đó là toàn bộ mục đích của lượt này.
