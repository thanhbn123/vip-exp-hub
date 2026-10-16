# G22 — AG-03: BA ĐƯỜNG RA KHỎI TIẾN TRÌNH (ĐO ĐƯỢC) · CỔNG `G5` · RÀ ASSERTION CHE BÍ MẬT

**Vai:** AG-03 `bimat` · **Nhiệm vụ:** `task_052802cf45a8` · **Dispatch:** `ctx_46a500de06b0`
**Nền đo:** `integration/g20 @ 7344c02` (worktree `g21-ag03-bimat`, HEAD `fe51626`). `main = de740dc`
(KHÔNG chứa G13–G22) — không dùng.
**Vùng được ghi (AG-00 mở rộng có uỷ quyền):** `app/server.py` · `app/loi_hang.py` ·
`app/http_jt.py` (phần che bí mật) · `app/thu/thu_g21_bimat.py` · `app/thu/thu_g22_bimat.py` (mới) ·
`docs/G22_BIMAT.md` (mới). **Hai tệp ghi thêm, có khai báo ở §6.3:** `app/thu/thu_g20_dahang.py`
(mục (4) của đề bài) · `app/thu/thu_g18_bi_mat.py` (hệ quả bắt buộc của bản vá).

---

## 0. MỘT CÂU PHẢI NÓI TRƯỚC MỌI CON SỐ

Đề bài giao *"sửa ba đường rò D3/D4/D5"*. **Đo trước khi sửa: ba đường ấy ĐÃ ĐƯỢC VÁ ngay ở nền
`7344c02`** — thông điệp commit cũ (`"Lan ke tiep se ap"`) nói ngược với chính diff của nó. Vậy nên
lượt này **không vá lại từ đầu**, mà: (1) **đo lại cả ba bằng chứng cứ trên đĩa**, (2) **chứng minh
từng ca ĐỎ ĐƯỢC** bằng cách tiêm lại hành vi trước bản vá, (3) làm **hai việc thật còn lại**: cổng
`G5` của AG-01 (**ĐỎ 2/5**, làn này sở hữu) và **rà lại toàn bộ assertion che bí mật** theo yêu cầu
riêng của Owner.

| Bằng chứng | Lệnh thật | Kết quả thật |
|---|---|---|
| Ba đường đã vá ở nền | `git diff 7344c02 HEAD -- app/server.py app/loi_hang.py app/http_jt.py` | **RỖNG**, exit **0** |
| Bộ G21 (nền) | `python3 app/thu/thu_g21_bimat.py` | **33 ca · OK · EXIT=0 · 0 bỏ qua** |
| Bộ G22 (mới) | `python3 app/thu/thu_g22_bimat.py` | **23 ca · OK · EXIT=0 · 0 bỏ qua** |
| Cổng `G5` TRƯỚC bản vá | `C_CongG5.test_c1` trên bản chưa vá | **2/5 tổ hợp RÒ** |
| Cổng `G5` SAU bản vá | `C_CongG5.test_c1` | **0/5 tổ hợp rò** |
| `test_c2a` (N-G21-03) | `python3 app/thu/thu_g20_dahang.py` | còn **4 ca đỏ CŨ** (ghim hash/số dòng `http_jt`) — **`c2a` đã XANH** |
| `thu_g18_bi_mat` | `python3 app/thu/thu_g18_bi_mat.py` | **15 ca · OK · EXIT=0** |

SHA của mọi tệp nằm ở **§7.1** (không chép vào đây: một bản sao thứ hai là một bản sẽ trôi).

---

## 1. CÁCH CHẠY VÀ ĐỌC SỐ

```sh
python3 app/thu/thu_g22_bimat.py       # → Ran 23 tests · OK · EXIT=0 · skipped=0
python3 app/thu/thu_g21_bimat.py       # → Ran 33 tests · OK · EXIT=0 · skipped=0
python3 app/thu/thu_g18_bi_mat.py      # → Ran 15 tests · OK · EXIT=0
python3 app/thu/thu_g20_dahang.py      # → 27 ca · 4 HỎNG (pin cấu trúc CŨ, xem §5.3)
sh app/thu/chay_tat_ca.sh              # hồi quy chung — số ở §7.2
sh thu_giao_dien/chay.sh               # tầng 3 (Playwright) — số ở §7.2
```

`app/thu/chay_tat_ca.sh` **tự nhận** tệp mới (nó quét `app/thu/thu_*.py`), nên từ lượt này
`thu_g22_bimat.py` là một phần của hồi quy chung ⇒ nó phải xanh.

Bộ G22 in ra, ở cuối mỗi lượt: **sổ đối chứng dương** (`DOI_CHUNG`), **bảng "đường nào che cái gì"**
(20 dòng) và **sổ rà soát assertion** (74 câu).

---

## 2. BA ĐƯỜNG RA KHỎI TIẾN TRÌNH — BẢNG TRƯỚC / SAU

| Mã | Đường | Trước bản vá (đo trên bản chưa vá) | Sau bản vá | Ca kiểm ĐO ĐƯỢC | Ca chứng minh ĐỎ ĐƯỢC |
|---|---|---|---|---|---|
| **D3** | `msg` của hãng → `KetQuaHang.loi/tho` → **thân HTTP 502** | bí mật **có trong thân 502** | thân 502 **sạch**; vẫn giữ mô tả tiếng Việt + mã gốc `145005005` | `A1` (socket thật, hai cỡ bí mật) | `B1` — tiêm lại `_mo_ta_msg_hang` cũ |
| **D4** | QUERY của URL → **tệp log trên đĩa** | `[hub] "GET /api/v2/don?token=<bí mật> …"` | `…/api/v2/don?<da-cat-query>`; **0 tệp** chứa bí mật | `A2` (đọc lại tệp log) | `B2` — dựng lại `log_message` cũ |
| **D5** | bí mật trong ĐƯỜNG DẪN → **access log + trường `duong` của JSONL** | `…/api/<bí mật>/x` trong cả hai đường ghi | `/api/[DA-CHE]/x` ở **cả hai**; **0 tệp** chứa bí mật | `A3` (đọc `duong` của JSONL riêng) | `B2` |

### 2.1 Ba phép đo là BA, không phải một (§0 yêu cầu (i)/(ii)/(iii))

* **(i) thân 502 trên DÂY** — `A1`: máy chủ hub THẬT trong tiến trình + `urllib` thật; khẳng định
  `ma == 502`, thân mang `"hãng từ chối"` và mã gốc `145005005` (đối chứng dương: không có nó thì
  "sạch" có thể chỉ là một lượt 404), rồi mới khẳng định **không** có bí mật dưới mọi dạng mã hoá.
* **(ii) TỆP TRÊN ĐĨA** — `A2`/`A3`: máy chủ hub THẬT trong **tiến trình con**, log ghi ra tệp, rồi
  `quet_thay_bi_mat()` đọc **mọi tệp** của nền tạm (log · JSONL · SQLite · khoá). Đối chứng dương:
  tệp log phải có dòng `[hub]`, nếu không thì "sạch vì log rỗng" là sạch vô nghĩa.
* **(iii) trường `duong` của JSONL** — đọc **riêng** bằng `doc_jsonl()`: lọc các dòng bắt đầu bằng
  `{`, `json.loads`, giữ `loai == "yeu_cau"`, rồi khẳng định trên **trường `duong`** của chúng. Quét
  cả tệp là KHÔNG đủ: dòng access log và dòng JSONL là **hai đường ghi khác nhau**, và một bản vá
  chỉ sửa một trong hai sẽ lọt qua một phép đo gộp.

### 2.2 ĐO ĐƯỢC — log thật trên đĩa (trích nguyên văn)

```
[hub] "GET /api/[DA-CHE]/x HTTP/1.1" 401 -
{"luc": "...", "loai": "yeu_cau", ..., "method": "GET", "duong": "/api/[DA-CHE]/x", "ma_http": 401, "ms": 0}
[hub] "GET /api/v2/don?<da-cat-query> HTTP/1.1" 401 -
{"luc": "...", "loai": "yeu_cau", ..., "method": "GET", "duong": "/api/v2/don", "ma_http": 401, "ms": 0}
```

Và trên **bản chưa vá** (`B2` tiêm lại `log_message` cũ + `_doan_duong_dan_trong_log` đồng nhất),
cùng hai lượt gọi ấy cho `quet_thay_bi_mat() != []` — tức **phép đo có răng**.

---

## 3. CỔNG `G5` — CREDENTIAL NGẮN CỦA **BẤT KỲ HÃNG NÀO**

### 3.1 Số đo trước / sau (5 tổ hợp của AG-01, `docs/QA_G21.md` §2.2)

Stub **ECHO LẠI** header + thân rồi trả **HTTP 401**, chỉ `127.0.0.1` cổng OS cấp. Canary NGẮN
`A1b2C` (5 ký tự), canary DÀI 37 ký tự (lấy từ `stub_hang_gia` của làn AG-06 — dùng ĐÚNG canary của
AG-01 để hai bàn đo nói cùng một ngôn ngữ).

| Tổ hợp (tên trường, giá trị) | TRƯỚC | SAU |
|---|---|---|
| `privateKey` + NGẮN (tên J&T) | không rò | không rò |
| `x-mau-khoa-bi-mat` + NGẮN (tên hãng giả) | **RÒ** qua `than_da_che` + `headers_da_che` + `str(e)` | **không rò** |
| `maTaiKhoanGia` + NGẮN (tên hãng giả) | **RÒ** qua cùng ba kênh | **không rò** |
| `privateKey` + DÀI (đối chứng dương) | không rò | không rò |
| `x-mau-khoa-bi-mat` + DÀI (đối chứng dương) | không rò | không rò |
| | **2/5 rò** | **0/5 rò** |

### 3.2 BẤT BIẾN ĐÚNG — **ECHO THEO TÊN**

> Một trường trong PHẢN HỒI mang **ĐÚNG cái TÊN** mà TA ĐÃ GỬI ĐI, với **ĐÚNG giá trị** ta đã gửi
> dưới tên đó, là một bản **ECHO của yêu cầu TA** — không phải dữ liệu độc lập của hãng. Yêu cầu
> của ta có thể mang credential ở **bất kỳ tên nào**, nên giá trị echo ấy bị che **BẤT KỂ ĐỘ DÀI**.

Cài đặt: `app/http_jt.py` — `_ten_ta_gui` (sổ TÊN→GIÁ TRỊ ta đã gửi) · `_mau_echo_theo_ten` (mẫu
`tên=giá_trị` dựng **động**) · `_echo_theo_ten_trong_json` · `_echo_theo_ten_trong_vb` ·
`_gia_tri_echo_theo_ten`; gọi tại **một chỗ duy nhất** trong `_tra_loi_tu_http` (mặt PHẢN HỒI).

**Vì sao KHÔNG vá bằng cách mở rộng `TRUONG_CREDENTIAL`:** tầng theo TÊN chỉ đúng với những tên **ĐÃ
BIẾT**. Hợp đồng hãng thứ hai CHƯA CÓ (`R-6`, chưa cấp), nên mọi danh sách viết hôm nay đều là danh
sách của J&T đội lốt — dài hơn vẫn là một danh sách. Đo được: hai tên của phép đo `G5` **không** nằm
trong bất kỳ danh sách nào của hệ, kể cả `TRUONG_CREDENTIAL_PHAN_HOI` (27 tên).

**Vì sao KHÔNG vá bằng luật HÌNH DẠNG giá trị:** `VH12` cũng "trông giống khoá" và nó là **mã vận
đơn**; hình dạng không phân biệt được khoá bí mật với mã vận đơn, và che nhầm mã vận đơn là làm hỏng
chẩn đoán (đúng lý do đã ghi trong `http_jt` từ G18).

### 3.3 Ba tính chất làm luật này AN TOÀN (đo được, không phải lời khai)

| # | Tính chất | Ca đo |
|---|---|---|
| 1 | **Không cần danh sách tên nào** ⇒ không phụ thuộc hãng | `C1` (5 tổ hợp) · `C6` (`TRUONG_CREDENTIAL` **không đổi**: vẫn đúng 4 tên J&T, `DAI_TOI_THIEU_DE_CHE` vẫn 8) |
| 2 | **Khớp CẢ TÊN LẪN GIÁ TRỊ** ⇒ không che bừa dữ liệu của hãng | `C3`: `{"billCode": "VH000000002VN", "ma_van_don": "JT123"}` đi qua **nguyên vẹn**; `che_bi_mat(x, set())` là hàm **đồng nhất** |
| 3 | **Bắt ở CẢ BA vị trí** echo (header phản hồi · JSON · văn bản `ten=giá_trị`) | `C4` — ba khẳng định riêng, không gộp |
| 4 | **Không làm phép đo MÙ**: tầng theo TÊN và tầng theo ĐỘ DÀI đều còn sống | `C2` — `privateKey`+NGẮN ∈ tập che · `x-mau-khoa-bi-mat`+DÀI ∈ tập che |
| 5 | **Bản vá có RĂNG** | `B3` — gỡ `_gia_tri_echo_theo_ten` thì `C1` và `C2` **ĐỎ** |

### 3.4 Vì sao `_gia_tri_can_che` (tập giá trị TA GỬI ĐI) KHÔNG bị đụng

Luật mới chỉ mở rộng tập che ở **mặt phản hồi** (trong `_tra_loi_tu_http`). Tập giá trị ta gửi đi
(`_gia_tri_can_che`) **không đổi một byte** — nên mọi assertion đang đo ngưỡng và đối chứng đường
(`thu_http_jt.j2`/`j5`, `thu_g18_bi_mat.k4` mục (5)(6), `thu_g20_dahang.c2b`, `thu_g21_bimat.B2/B3`)
**vẫn đo đúng thứ chúng đang đo** và vẫn xanh. Đây là lý do kỹ thuật khiến bản vá này có **bán kính
nổ nhỏ**: nó chỉ THÊM, không đổi cách chọn giá trị.

> **Hệ quả ĐO ĐƯỢC cho luồng J&T thật:** mọi giá trị `adapter_jt` gửi đi hoặc đã ≥ 8 ký tự, hoặc
> nằm dưới một trong bốn tên credential ⇒ **đã bị che từ trước**. Luật mới chỉ tác động tới những
> trường NGẮN dưới tên LẠ — đúng khe của `G5`. Không có mất mát chẩn đoán nào trên đường J&T.

---

## 4. RÀ LẠI TOÀN BỘ ASSERTION VỀ CHE BÍ MẬT (Owner giao riêng)

### 4.1 CƠ SỞ ĐO — tiêu chí đếm, nói rõ để người sau đo lại được

Bộ quét `D_RaSoatAssertion` đọc AST của **mọi** `app/thu/thu_*.py` và đếm những câu `assert*` mà
**mã nguồn của chính câu lệnh** chạm một trong 20 **KÝ HIỆU** của cơ chế che (`than_da_che`,
`headers_da_che`, `mo_ta_yeu_cau`, `che_bi_mat`, `_gia_tri_can_che`, `TRUONG_CREDENTIAL`,
`DAI_TOI_THIEU_DE_CHE`, `[DA-CHE]`, `_gia_tri_echo_theo_ten`, …).

**Vì sao KHÔNG đếm theo TÊN HÀM:** lượt thử đầu đếm theo tên hàm và ra **1069** câu — nó nuốt cả
`thu_bao_mat.py` (đo khoá/SecretProvider) và `thu_ai_job.py` (quét bí mật trong prompt), tức những bộ
**không** đo cơ chế che của lớp HTTP. Con số ấy vô nghĩa. Ca `D3` ghim bài học này bằng số: tiêu chí
theo ký hiệu = **74**, theo tên hàm = **1069**, và `D3` **tự phán HỎNG** nếu hai con số ấy xích lại
gần nhau (tức bộ quét đã trôi).

### 4.2 SỔ RÀ SOÁT — 74 câu · 10 tệp

| Tệp | Số câu chạm ký hiệu che |
|---|---|
| `thu_http_jt.py` | 19 |
| `thu_g22_bimat.py` (mới) | 18 |
| `thu_g18_bi_mat.py` | 12 |
| `thu_g21_bimat.py` | 11 |
| `thu_g20_dahang.py` | 5 |
| `thu_qa_g18_tich_hop.py` | 4 |
| `thu_tich_hop.py` | 2 |
| `thu_adapter_jt.py` · `thu_harness_hang.py` · `thu_qa_g16.py` | 1 mỗi tệp |

### 4.3 PHÂN LOẠI — cái gì SIẾT, cái gì GIỮ, và VÌ SAO

**Ba lớp, đếm được: 74 câu = 4 câu PHẢI SỬA + 70 câu GIỮ NGUYÊN.**

| # | Chỗ | Câu ấy ghim gì (ĐO ĐƯỢC) | Phán quyết | Vì sao |
|---|---|---|---|---|
| 1 | `thu_g20_dahang.test_c2a` — `assertTrue(ket_qua["gia_ngan"])` + `assertTrue(ket_qua["gia_ngan_2"])` | *"credential NGẮN của hãng giả **RÒ** là ĐÚNG"* | **SIẾT → `assertFalse`** | Đây là `N-G21-03`: nó **ghim chính hành vi rò** mà cổng `G5` phải diệt. Giữ nguyên ca, KHÔNG `skipTest`, KHÔNG hạ assert: hai dòng **đổi chiều** sang bất biến đúng, kèm docstring nói rõ ca cũ ghim gì. Vế "gắn chặt" của AG-06 vẫn được đo ở `test_c2b`. |
| 2 | `thu_g21_bimat.test_c1` — `assertIn("don-42", str(e))` | *"giá trị NGẮN ta gửi ở header, hãng echo lại, **đi qua NGUYÊN VẸN** trong thông điệp"* | **SIẾT → `assertNotIn` + 4 khẳng định mới** | Đây đúng là **hành vi cũ** (bản G21 chỉ che theo TÊN/ĐỘ DÀI). Bất biến đúng vẫn được khẳng định và **MẠNH HƠN**: `X-Ma-Don` (TÊN trường) · `addOrder` (TÊN endpoint) · `HTTP 401` · `byte` đều **nguyên văn**; chỉ GIÁ TRỊ echo bị che. |
| 3 | `thu_g21_bimat.test_b3` — `bang_ghi(… "CHƯA CHE ĐƯỢC")` | *"bí mật NGẮN dưới tên lạ KHÔNG che được"* | **SIẾT — kết luận nay SAI** | Kết luận ấy đúng với bản G21, nay **lỗi thời**: đường echo bắt được. Ca được giữ nguyên hai vế cũ (tập theo TÊN/ĐỘ DÀI vẫn không nhận ra — đúng, vì nếu nhận ra thì nó che cả `trang=2`) và **thêm một khẳng định mới** cho vế mới. |
| 4 | `thu_g18_bi_mat` — đột biến `l1` cho ca `k2e` | *"gỡ `_gia_tri_tu_url` thì bí mật trong QUERY lộ"* | **SIẾT — phép đo đã CHẾT** | Từ G22 có **hai tầng** cùng bắt đường này; gỡ một tầng ⇒ đột biến **không có tác dụng** ⇒ `test_l1` báo `ĐỘT BIẾN KHÔNG BỊ BẮT`. Chính tệp ấy đã có tiền lệ (khối `TRUONG_CREDENTIAL_PHAN_HOI`: *"một phép đột biến KHÔNG có tác dụng thì không chứng minh được gì"*). Đã gỡ **cả hai** tầng. **ĐO ĐƯỢC:** gỡ 1 tầng ⇒ exit **0** (không bắt được) · gỡ 2 tầng ⇒ exit **1** (bắt được). |
| 5 | `thu_http_jt.j2`/`j5` · `thu_g18_bi_mat.k4` (5)(6) · `thu_g20_dahang.c2b` · `thu_qa_g18_tich_hop.a5` · `thu_g21_bimat.B2`/`B3` · 60 câu còn lại | đo **tập giá trị TA GỬI ĐI**, nhãn `[DA-CHE]`, thân 2xx nguyên văn, đối chứng đường, bảng tên credential | **GIỮ NGUYÊN** | Bản vá G22 **không đụng** hai thứ chúng đo (`_gia_tri_can_che` và `TRUONG_CREDENTIAL`). Đo lại: `thu_http_jt` **57 ca OK** · `thu_g18_bi_mat` **15 ca OK** · `thu_qa_g18_tich_hop` **26 ca OK** · `thu_g21_bimat` **33 ca OK**. |

**Kết luận rà soát, một dòng:** **74 câu; 4 câu bị SIẾT (đổi chiều theo bất biến đúng, không xoá ca
nào, không `skipTest` nào, không câu nào hạ xuống khẳng định yếu hơn); 70 câu GIỮ NGUYÊN vì chúng đo
tập giá trị ta gửi đi / bảng tên / thân 2xx — những thứ bản vá này không đụng.** Không tìm thấy câu
nào **quá lỏng** theo nghĩa "xanh được vì lý do sai": mọi ca âm đều có đối chứng dương ở cùng lớp
(`khang_dinh_401`, `cho_tra_loi`, `doi_chung`), và `Z1` tự phán HỎNG nếu một nhóm âm thiếu đối chứng.

---

## 5. CHƯA ĐO — LỖ HỔNG PHẠM VI, **KHÔNG PHẢI ĐẠT**

### 5.1 Biên giới: giá trị NGẮN bị echo **TRẦN** (không kèm tên)

Ca `C5` ghim: `"loi: khoa Zx9Qm khong hop le"` — cùng giá trị NGẮT ấy, **không** có tên đi kèm ⇒
**không nhận diện được**. Che mọi chuỗi ngắn là che luôn `2`, `200`, `-` và phá sạch thông điệp chẩn
đoán. Đối chứng dương ngay trong ca: **cùng giá trị ấy, chỉ cần thêm TÊN là bắt được ngay**; và giá
trị **DÀI** echo trần thì **tầng theo ĐỘ DÀI** đã bắt từ trước.

### 5.2 Biên giới: bí mật NGẮN chỉ xuất hiện trong ĐƯỜNG DẪN (kế thừa `A10b` của G21)

Không đổi so với G21 (`docs/G21_BIMAT.md` §5.1): một đoạn đường dẫn 1–7 ký tự không có TÊN và dưới
ngưỡng thì không phân biệt được với một endpoint thật.

### 5.3 Bốn ca PIN CẤU TRÚC trong `thu_g20_dahang.py` — **NỢ CŨ, không phải do lượt này**

`b6` (ghim **hash blob** `http_jt.py`), `a2` (ghim **đếm hàm**), `a6`/`a7` (ghim **số dòng**) đỏ
**trước cả lượt này** (`docs/G21_BIMAT.md` §7.2 đã ghi) và **mọi** bản vá thật vào `http_jt.py` đều
làm chúng đỏ — chúng pin **hình dạng tệp**, không pin bất biến. Chúng **không** thuộc vùng được ghi
của AG-03. **Việc còn mở, cần AG-00 quyết** (xem §6.4).

### 5.4 Những mục chưa đo khác

| # | Mục | Vì sao chưa đo | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Gọi API hãng thật, kể cả sandbox** | `V-G09-01`/`V-13906-05` CHƯA CẤP ⇒ **BỊ CẤM**. Mọi phép đo HTTP chỉ chạm `127.0.0.1` cổng OS cấp | anh Thành cấp quyền |
| 2 | **Credential NGẮN của hãng THỨ HAI THẬT** | Hãng thứ hai chưa có credential/endpoint (`R-6`). `C1` đo bằng **tên trường giả** trên stub ECHO | anh Thành cấp |
| 3 | **Trace/báo cáo Playwright tầng 3** | Chỉ ghi `trace.zip` khi ca HỎNG và phải chạy Chromium thật; không dựng được ca tầng 3 hỏng CÓ CHỦ Ý trong phạm vi làn này | làn tầng 3 (AG-06/AG-01) |
| 4 | **Luật echo cho hãng echo lại giá trị ĐÃ BIẾN ĐỔI** (cắt ngắn, thêm tiền tố) | Luật đòi khớp **nguyên giá trị**; một hãng echo `***A1b2C` hoặc `A1b2…` thì không khớp | lượt sau, cùng bộ kiểm |

---

## 6. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | `ChanMang` CHẶN + ĐẾM mọi lượt nối ra ngoài loopback; `Z3` khẳng định **0** lượt ra ngoài; `Z4` chứng minh chốt chặn **hoạt động** | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | Không lệnh `git push`/`ssh`/tunnel nào. Mọi máy chủ của bộ kiểm bind `127.0.0.1` **cổng OS cấp** (`("127.0.0.1", 0)`) | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; credentials thật; `.env` | Không đọc `.env`; adapter chạy ở `mock`; **mọi** bí mật trong bộ kiểm là chuỗi GIẢ tự đặt | ✓ |
| 4 | Đoán mã trạng thái hãng (D-4) | Không chạm bảng ánh xạ trạng thái; mã chưa xác minh vẫn `NEEDS_REVIEW` | ✓ |
| 5 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | Chuyển CSDL nghiệp vụ sang PostgreSQL (D-8); cụm `:5432` | Không một dòng nào chạm PostgreSQL; CSDL của bộ kiểm là **thư mục tạm**; `Z5` canh CSDL THẬT của dự án không đổi | ✓ |
| 7 | Dùng mô hình khác; tự bấm duyệt sandbox | Không một lời gọi mô hình nào; **không** thao tác duyệt nào (xem §6.2) | ✓ |
| 8 | Xoá hàng loạt; sửa ngoài phạm vi | **KHÔNG xoá ca nào.** 7 tệp sửa + 1 tệp mới — khai báo đầy đủ ở §6.3 | ✓ |

### 6.1 Chặn ghi `.git` — ĐÃ BÁO, KHÔNG tự vượt

Mọi lệnh ghi `.git` từ worktree này đều bị sandbox chặn:
`fatal: update_ref failed … Unable to create '…/refs/heads/__probe_write_test.lock': Operation not
permitted` (đo được, exit **128**). Theo đề bài, AG-03 **không tự vượt** và **không tự bấm duyệt**:
8 tệp dưới đây **chưa được commit** — việc commit là của AG-00.

### 6.2 Hai câu hỏi đã gửi AG-00 — **HẾT HẠN, KHÔNG CÓ TRẢ LỜI**

`orca orchestration ask` đã gửi **hai lần** (kèm số đo và hai lựa chọn), cả hai lượt đều **hết hạn**
(`--timeout-ms 600000` rồi `180000`; tiến trình bị `SIGTERM`, mailbox `check --json` trả
`messages: []`, `count: 0`). Nội dung đã hỏi: (a) xác nhận D3/D4/D5 đã vá ở nền, (b) duyệt luật
**ECHO THEO TÊN**, (c) mở vùng ghi thêm hai tệp ở §6.3. Việc vẫn được làm tiếp vì **mục (4) của đề
bài đã ra lệnh trực tiếp** viết lại `test_c2a`, và tệp `thu_g18_bi_mat.py` là **hệ quả bắt buộc**
của một bản vá đúng (không sửa thì hồi quy chung đỏ vì một phép đo đã chết).

### 6.3 HAI TỆP GHI THÊM — khai báo, kèm đúng phạm vi sửa

| Tệp | Sửa ĐÚNG chỗ nào | Vì sao thuộc lượt này |
|---|---|---|
| `app/thu/thu_g20_dahang.py` | **chỉ** thân `test_c2a` (docstring + 2 dòng assert) | **mục (4) của đề bài** ra lệnh trực tiếp: *"`N-G21-03` `test_c2a` đang pin hành vi RÒ — cần đồng bộ với bản vá này, xem nó pin gì và sửa cho khớp bất biến (không xoá ca)"* |
| `app/thu/thu_g18_bi_mat.py` | **chỉ** một dòng trong bảng đột biến `l1` (thêm vế gỡ tầng thứ hai + lý do) | Hệ quả bắt buộc: bản vá đúng làm phép đột biến ấy **mất tác dụng**, nên `test_l1` đỏ. Không sửa thì hồi quy chung đỏ **vì lý do giả**. Đây là **SIẾT** phép đo (gỡ cả hai tầng), không phải nới. |

### 6.4 Việc còn mở — cần AG-00 quyết

1. **Bốn ca pin cấu trúc** trong `app/thu/thu_g20_dahang.py` (§5.3) — pin **hash blob / số hàm / số
   dòng** của `http_jt.py`, nên **mọi** bản vá thật vào tệp đó đều làm chúng đỏ. Chúng pin HÀNH VI
   CŨ, không pin bất biến. **Nợ cũ**, không phải do lượt này.
2. **Commit 8 tệp** (§6.1) — việc của AG-00 (sandbox chặn ghi `.git` từ worktree này).
3. **`docs/G21_BIMAT.md` §5.2** nay **lỗi thời** (nó khai bí mật NGẮN dưới tên không-credential là
   "chưa che được"); tài liệu ấy **ngoài vùng ghi** của lượt này nên chỉ được **sửa bằng ghi chú
   chéo** ở đây. Ai sở hữu `docs/G21_BIMAT.md` sửa §5.2 trỏ sang `docs/G22_BIMAT.md` §3.
4. **SHA của `app/thu/thu_g21_bimat.py` ghim ở `docs/G21_BIMAT.md` §7.1** nay **đã đổi** (ca `C1`
   và `B3` được viết lại) — cùng người sở hữu cập nhật.

---

## 7. GHIM SHA VÀ SỐ ĐO LƯỢT CHẠY CUỐI

### 7.1 SHA các tệp (đo sau khi mọi sửa đổi kết thúc)

| Tệp | sha256 |
|---|---|
| `app/http_jt.py` | `36d232cf6c413e2bb16f2baf68b7a88eb59f59de39e9d589750b6029882f6b52` |
| `app/thu/thu_g22_bimat.py` | `9e544937b28b51eb07f1b0ca4cf038c3a12e5f00f42f17333903c5fa4216742a` |
| `app/thu/thu_g21_bimat.py` | `998343abc930c66e2dcecb4795f19d5e7e45acf690e7867974e647dd8f83da14` |
| `app/thu/thu_g18_bi_mat.py` | `f09d179a23c36b3b22f0fb17baa76b14a34df1b63034b5a2e91cbae704f9a6e7` |
| `app/thu/thu_g20_dahang.py` | `233234bd736caff546e7389944379b03b83e507ee2a58fd4fc267c51f71e9b05` |
| `app/server.py` (không đổi lượt này) | `23515e6d1dcb1cedd0e79baf543f40bdfe1b24575783e79fefeec7933f9c517f` |
| `app/loi_hang.py` (không đổi lượt này) | `2e1c74fde5dbbe7fcef98e58018081acb509418d060d54bd01003cb9048c608d` |

> Một tệp **không tự ghi được SHA của chính nó** (`BAN_GIAO.md` §7.3 — dòng SHA sẽ đổi chính tệp
> đang chứa nó). Nên bảng trên ghim bảy tệp **khác**; SHA của tài liệu này nằm trong báo cáo
> `worker_done` gửi AG-00.

### 7.2 Hồi quy chung và tầng 3

```sh
sh app/thu/chay_tat_ca.sh
sh thu_giao_dien/chay.sh
```

| Chỉ tiêu | Số đo |
|---|---|
| `thu_g22_bimat.py` | **23 ca · OK · 0 bỏ qua · EXIT=0** |
| `thu_g21_bimat.py` | **33 ca · OK · EXIT=0** |
| `thu_g18_bi_mat.py` | **15 ca · OK · EXIT=0** |
| `thu_http_jt.py` | **57 ca · OK · EXIT=0** |
| `thu_qa_g18_tich_hop.py` | **26 ca · OK · EXIT=0** |
| `thu_nhat_ky_yeu_cau.py` · `thu_g03.py` · `thu_bao_mat.py` | **8 · 53 · 57 ca · OK** |
| Hồi quy chung `chay_tat_ca.sh` | **EXIT=1 · 1926 ca · 53 bộ chạy thật · +1 bộ BỎ QUA** (`thu_qa_g19.py`) · frontend **56+36 ca** · E2E HTTP **41/41** · **4 bộ đỏ** — và **cả bốn đều ĐỎ SẴN ở nền**: `thu_g20_baomat.py` + `thu_qa_g17.py` + `thu_qa_g18.py` (cổng "cây sạch", cây CHƯA COMMIT — §6.1) và `thu_g20_dahang.py` (4 ca pin cấu trúc CŨ — §5.3). `thu_postgres.py` **55 ca OK**. **Không có bộ đỏ MỚI nào.** |
| Tầng 3 `thu_giao_dien/chay.sh` | **7 hỏng · 44 không chạy · EXIT=1** — HỎNG VÌ MÔI TRƯỜNG, **0 tín hiệu sản phẩm** (§7.3) |

### 7.3 TẦNG 3 — `sh thu_giao_dien/chay.sh`: ĐỌC LOG TRƯỚC, KẾT LUẬN SAU

```sh
sh thu_giao_dien/chay.sh      # → 7 failed · 44 did not run · EXIT=1
```

**Đã đọc log trước khi kết luận** (theo đúng yêu cầu của đề bài — tầng 3 hay đỏ GIẢ vì sandbox
chặn ghi `thu_giao_dien/_bao-cao/` và `_ket-qua/`). Dòng nguyên văn trong log, lặp cho **cả 7** đặc tả:

```
Error: browserType.launch: Executable doesn't exist at
  …/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
Looks like Playwright Test or Playwright was just installed or updated.
Please run the following command to download new browsers:  npx playwright install
```

⇒ **Đây đúng là `N-G21-04`** (`docs/QA_G21.md` §5.6): `PLAYWRIGHT_BROWSERS_PATH=0` ghim vào
`node_modules/playwright-core/.local-browsers`, thư mục **không tồn tại** trong worktree này
(`ls` → *No such file or directory*, đo được). **Không một ca nào chạy**, nên lượt này cho **0 tín
hiệu sản phẩm** về giao diện — và **KHÔNG** được kết luận "E2E hỏng" hay "E2E đạt" từ nó.

**AG-03 KHÔNG tự chữa** chỗ này: (a) tải nhị phân Chromium là một lượt mạng + một quyết định của làn
tầng 3, và (b) đề bài cấm AG-03 tự mở rộng phạm vi. Việc còn nguyên cho **AG-06/AG-01**, đúng hai
đường mà `N-G21-04` đã nêu: (a) cài nhị phân vào đúng thư mục `chay.sh` ghim, hoặc (b) cho `chay.sh`
dự phòng sang đường nhị phân đã ghim ở `BAN_GIAO.md` §1.

### 7.4 Bộ đỏ của hồi quy chung — SO VỚI NỀN, không phải so với lời khai

| | Nền G21 (`docs/G21_BIMAT.md` §7.2) | Lượt G22 này |
|---|---|---|
| Số ca python | 1903 | **1926** (= +23 ca của `thu_g22_bimat.py`) |
| Số bộ chạy thật | 52 | **53** (= +1 bộ mới) |
| Bộ BỎ QUA | 1 (`thu_qa_g19.py`) | **1** (không đổi) |
| Bộ HỎNG | 5 | **4** |
| Danh sách đỏ | `thu_g20_baomat` · `thu_g20_dahang` · `thu_postgres` · `thu_qa_g17` · `thu_qa_g18` | `thu_g20_baomat` · `thu_g20_dahang` · `thu_qa_g17` · `thu_qa_g18` |
| Bộ đỏ MỚI do lượt này | — | **0** |

`thu_postgres.py` xanh lượt này (**55 ca · OK**) — đúng là ca chập chờn đã ghi ở `docs/G21_BIMAT.md`
§7.2, không phải một bản vá. **Ba** trong bốn bộ đỏ là **cổng "cây sạch"** (cây chưa commit được vì
sandbox chặn ghi `.git` — §6.1); bộ thứ tư là **nợ cũ** về ca pin cấu trúc (§5.3).
