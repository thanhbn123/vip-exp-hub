# G20 / AG-06 — ĐÃ HÃNG: lớp HTTP dùng chung đã dùng lại được cho hãng thứ hai chưa?

**Câu hỏi.** `app/http_jt.py` được viết ở G16 cho **RIÊNG** J&T. Dự án tự khai là "trung tâm chuyển
phát **ĐA HÃNG**", nhưng **chưa ai ĐO** xem lớp đó có dùng lại được cho hãng thứ hai hay không — hay
nó đã gắn chặt vào J&T (tên trường, định dạng chữ ký, danh sách host).

**Trả lời ngắn.** Lớp đó **dùng lại được** cho hãng thứ hai, **không phải sửa một ký tự nào** — với
điều kiện hãng đó nói `POST` + `x-www-form-urlencoded`, và **điểm đến của nó nằm trên loopback**.
Nhưng có **đúng hai chỗ gắn chặt thật**, cả hai **đo được**, và cả hai đều **chỉ mở được bằng SỬA
MÃ**, không phải bằng cấu hình:

| # | Chỗ gắn chặt | Hệ quả đo được |
|---|---|---|
| **1** | Danh sách trắng host là hằng số ĐÓNG `http_jt.HOST_HANG` | Địa chỉ **thật** của hãng thứ hai bị `TỪ CHỐI`, `ket_cuc='khong-gui-di'`, **0 lượt nối** |
| **2** | Bảng tên credential là bảng của J&T `http_jt.TRUONG_CREDENTIAL` | Credential **ngắn (5 ký tự)** của hãng thứ hai **RÒ nguyên văn** vào `than_da_che`, `headers_da_che` **và** `str(e)` |

Cộng thêm **hai ràng buộc HÌNH DẠNG** (không phải "gắn vào J&T" mà là "gắn vào một khuôn giao
thức"): chỉ `POST`, và thân chỉ `x-www-form-urlencoded`. Một hãng thứ hai dùng `GET` hoặc JSON body
sẽ **không** dùng lại được lớp này.

---

## 1. Phạm vi — NÓI THẲNG CÁI NẰM NGOÀI

Ghi trước, vì đây là chỗ dễ bị đọc quá lời nhất.

| Khẳng định | Có đo được không |
|---|---|
| Lớp HTTP chạy được cho một hãng thứ hai **cùng khuôn giao thức** | **CÓ** — đo trên hãng GIẢ MẪU, stub loopback |
| Chỗ nào trong `http_jt.py` là cơ chế chung, chỗ nào là đặc thù J&T | **CÓ** — đo bằng AST, bảng ở §3 |
| Hành vi **thật** của J&T (chữ ký có được chấp nhận, mã lỗi thật, TLS, hạn mức) | **KHÔNG** — V-G09-01 / V-13906-05 CHƯA CẤP, chưa từng có lượt gọi hãng nào |
| Hành vi **thật** của bất kỳ hãng thứ hai có thật nào | **KHÔNG** — "hãng thứ hai" ở đây là hãng **BỊA** (§2) |
| Ánh xạ mã trạng thái / mã lỗi của hãng thứ hai | **KHÔNG** — đó là việc của **adapter**, không phải lớp HTTP (D-4: mã chưa xác minh ⇒ `NEEDS_REVIEW`) |
| Tầng nghiệp vụ: đối soát, tính phí, in nhãn cho hãng thứ hai | **KHÔNG** — ngoài phạm vi AG-06 |

> Bộ thử XANH ở đây **KHÔNG** phải lời cho phép gọi sandbox, và **KHÔNG** được đọc thành
> `LIVE VERIFIED`. Nó đo **RÀNG BUỘC CỦA LỚP HTTP**, không đo một API cụ thể nào.

---

## 2. "Hãng thứ hai" là hãng GIẢ — nói rõ để không ai đọc nhầm

**HÃNG GIẢ MẪU** (`hang-gia-mau`) do AG-06 **tự đặt ra**. Nó **không tồn tại**. Mọi tên trường,
đường dẫn, tên host và công thức chữ ký đều là **BỊA có chủ ý** — không chép, không suy đoán, không
"đoán gần đúng" từ API thật của bất kỳ hãng nào (yêu cầu 3 của AG-06).

Tên host dùng đuôi **`.invalid`** — RFC 6761 §6.4 dành riêng đuôi này và bảo đảm nó **không bao giờ
phân giải được**. Nhờ vậy, kể cả khi ai đó dán nhầm tên host giả vào một URL thật, lượt gọi **đổ ở
tầng DNS** chứ không đi đâu cả. Đây là chốt chặn **thứ hai**, độc lập với danh sách trắng.

### Hãng giả khác J&T ở ĐÚNG BA CHỖ AG-06 nêu — và giống ở mọi chỗ còn lại

| tầng | J&T (thật, đã đọc tài liệu) | HÃNG GIẢ MẪU (BỊA) |
|---|---|---|
| **(1) trường thân** | `bizContent` | `duLieuDon` |
| **(1) header tài khoản** | `apiAccount` | `X-Mau-Tai-Khoan` |
| **(1) header chữ ký** | `digest` | `X-Mau-Chu-Ky` |
| **(1) mốc thời gian** | `timestamp` | `X-Mau-Thoi-Diem` |
| **(1) khoá bí mật** | `privateKey` (trong `bizContent`) | `khoaBiMatGia` (trong `duLieuDon`) |
| **(2) công thức chữ ký** | `base64(md5(bizContent + privateKey))` | `base64(HMAC-SHA256(khoá, "<đường>\|<mốc>\|<thân>"))` |
| **(3) host** | `demoopenapi.jtexpress.vn` | `api.hang-gia-mau.invalid` |
| **(3) đường dẫn** | `/webopenplatformapi/api/order/addOrder` | `/cong-van/2/don/tao` |
| *giống*: phương thức | `POST` | `POST` |
| *giống*: kiểu thân | `x-www-form-urlencoded` | `x-www-form-urlencoded` |
| *giống*: hình dạng thân | 1 trường form chứa chuỗi JSON | 1 trường form chứa chuỗi JSON |

**Giống ở phần còn lại là CHỦ Ý.** Nếu hãng giả khác cả giao thức thì phép đo sẽ nói *"khác giao
thức"* chứ không nói được gì về chỗ **gắn chặt**. Muốn đo dây ràng buộc thì phải giữ mọi thứ khác
cố định.

Chữ ký khác ở **ba** điểm (thuật toán, nguyên liệu, khoá) — có ca thử khẳng định hai chữ ký **khác
nhau thật** (`test_b2`), nếu không phép đo "lớp chung không quan tâm chữ ký" là vô nghĩa.

---

## 3. BẢNG: CƠ CHẾ CHUNG vs ĐẶC THÙ J&T

Đo bằng AST trên `app/http_jt.py`; **nguồn dấu hiệu thân phận hãng đọc từ chính `app/adapter_jt.py`**
(`HOST_API`, `TRUONG_CREDENTIAL`), không chép tay — chép tay thì mai kia adapter đổi mà bảng này
không đổi.

Lệnh: `python3 trien_khai/g20-dahang/phan_tich_gan_chat.py` → **exit 0**
Bản đầy đủ: `trien_khai/g20-dahang/bang_chung_ast.txt` · JSON: `trien_khai/g20-dahang/bang_chung_ast.json`

### 3.1 Hằng mức mô-đun — 25 hằng: **3 đặc thù**, **3 dẫn xuất**, **19 chung**

| dòng | hằng | phân loại | vì sao |
|---:|---|---|---|
| 115 | `HOST_HANG_SANDBOX` | **ĐẶC THÙ J&T** | tên host `demoopenapi.jtexpress.vn` |
| 116 | `HOST_HANG_PRODUCTION` | **ĐẶC THÙ J&T** | tên host `ylopenapi.jtexpress.vn` |
| 117 | `HOST_HANG` | **DẪN XUẤT** | chỉ là hai hằng trên gộp lại |
| 138 | `TRUONG_CREDENTIAL` | **ĐẶC THÙ J&T** | CHÍNH LÀ bảng tên credential của hãng (4 tên, khớp 100% với `adapter_jt`) |
| 159 | `TRUONG_CREDENTIAL_PHAN_HOI` | **DẪN XUẤT** | `TRUONG_CREDENTIAL + (…)` |
| 169 | `_MAU_CAP_TEN_BI_MAT` | **DẪN XUẤT** | regex dựng từ bảng trên |
| 118 | `CONG_HANG = 443` | CHUNG | giá trị vendor-neutral; **nhánh dùng nó** mới là chuyện của J&T (§3.3) |
| 119 | `HOST_CUC_BO` | CHUNG | loopback |
| 123 | `HET_GIO_KET_NOI_TOI_DA` | CHUNG | hạn nối |
| 128 | `DAI_TOI_THIEU_DE_CHE = 8` | CHUNG | ngưỡng che theo độ dài — **vendor-neutral** |
| 142 | `HEADER_KHONG_CHE` | CHUNG | header giao thức |
| 182–184, 193 | `KET_CUC_*` | CHUNG | bốn kết cục |
| 203 | `CONTENT_TYPE_FORM` | CHUNG | `x-www-form-urlencoded` |
| 572–574 | `DOAN_DUONG_DAN_*`, `_CHUOI_DOAN_HOP_LE` | CHUNG | luật che đường dẫn |
| 82–91 | `MOCK`/`SANDBOX`/`PRODUCTION`/`CHO_PHEP_MOI_TRUONG`/`LY_DO_CHAN_MOI_TRUONG` | CHUNG | cổng môi trường |

> **Ghi chú phương pháp — một luật đã THỬ và đã BỎ.** Bản đầu phân loại thêm theo "dùng chung chỗ":
> hằng nào được cùng hàm đọc với `TRUONG_CREDENTIAL` thì gọi là đặc thù. Nó nuốt ngay
> `DAI_TOI_THIEU_DE_CHE = 8` — một ngưỡng **hoàn toàn chung** — chỉ vì nó nằm cạnh bảng tên
> credential trong `_dang_che`. Luật đó đã bị bỏ; nay phân loại chỉ dựa trên **giá trị** và **dẫn
> xuất**, còn "chỗ dùng bị ràng buộc hãng" được ghi riêng ở §3.3 — đo ở **chỗ dùng**, không gán cho
> hằng một thân phận nó không có.

### 3.2 Hàm — **7/37 hàm chạm đặc thù; 30 hàm vendor-neutral**

**ĐẶC THÙ J&T (7)** — đây là toàn bộ bề mặt gắn chặt:

| hàm | chạm |
|---|---|
| `host_duoc_phep` · `tach_url` | `HOST_HANG` |
| `_gia_tri_trong_json` · `_dang_che` | `TRUONG_CREDENTIAL` |
| `_gia_tri_bi_mat_trong_json` · `_gia_tri_bi_mat_tu_phan_hoi` | `TRUONG_CREDENTIAL_PHAN_HOI` |
| `_gia_tri_bi_mat_trong_vb` | `_MAU_CAP_TEN_BI_MAT` |

**CHUNG (30)** — toàn bộ lõi gửi/nhận/phân loại:
`gui_form` · `TraLoiHTTP` · `_loi_tam_thoi` · `_loi_vinh_vien` ·
`_bien_the` · `_mo_rong_bien_the` · `_escape_json` · `che_bi_mat` · `_gia_tri_ta_gui` ·
`_gia_tri_can_che` · `_gia_tri_tu_url` · `_gia_tri_tu_duong_dan` · `_duong_dan_da_che` ·
`_doan_chua_bi_mat` · `_la_doan_bi_mat` · `mo_ta_yeu_cau` · `_ten_truong_form` · `_che_chuoi` ·
`_mo_ta_ten` · `_kiem_tra_het_gio` · `_chuan_bi_headers` · `_ma_hoa_form` · `_mo_ket_noi` · `_dong` ·
`_loi_tu_ngoai_le` · `_doc_retry_after` · `_cho_theo_retry_after` · `_loi_cho_lai` · `_tra_loi_tu_http`

**Đọc bảng này thế nào:** *cơ chế* che bí mật là CHUNG — nhưng **dữ liệu đầu vào** của nó
(`TRUONG_CREDENTIAL`) là của J&T. Đó chính xác là gắn chặt số 2, và nó giải thích vì sao ma trận 2×2
ở §5 ra kết quả như đo được.

### 3.3 Bốn NHÁNH MÃ bị ràng buộc hãng (đo ở chỗ dùng)

| dòng | hàm | điều kiện |
|---:|---|---|
| 285 | `_gia_tri_trong_json` | `… str(khoa).lower() in TRUONG_CREDENTIAL` |
| 311 | `_gia_tri_bi_mat_trong_json` | `… str(khoa).strip().lower() in TRUONG_CREDENTIAL_PHAN_HOI` |
| 343 | `_gia_tri_bi_mat_tu_phan_hoi` | `str(ten).strip().lower() in TRUONG_CREDENTIAL_PHAN_HOI` |
| **742** | **`tach_url`** | **`if host in HOST_HANG:`** ← chốt chặn của gắn chặt số 1 |

### 3.4 ĐIỂM TIÊM — **KHÔNG CÓ** (bằng chứng trung tâm)

Mỗi bảng đặc thù được soát **ba đường ghi**, cộng một phép đo "bảng có bị trao cho ai không":

| bảng | số lần gán | truyền cho hàm NỘI BỘ | bị biến đổi tại chỗ | chỉ xuất hiện trong phép toán | **ĐÓNG?** |
|---|---:|---|---|---|---|
| `HOST_HANG` | 1 | KHÔNG | KHÔNG | `in`/`not in`; `', '.join(…)` để in | **CÓ** |
| `HOST_HANG_SANDBOX` | 1 | KHÔNG | KHÔNG | dựng tuple | **CÓ** |
| `HOST_HANG_PRODUCTION` | 1 | KHÔNG | KHÔNG | dựng tuple | **CÓ** |
| `TRUONG_CREDENTIAL` | 1 | KHÔNG | KHÔNG | `in`/`not in`; phép nối bảng mới | **CÓ** |
| `TRUONG_CREDENTIAL_PHAN_HOI` | 1 | KHÔNG | KHÔNG | `in`/`not in`; `sorted(…)` để dựng regex | **CÓ** |
| `_MAU_CAP_TEN_BI_MAT` | 1 | KHÔNG | KHÔNG | `re.Pattern.finditer` | **CÓ** |

Và **chữ ký hàm** đọc thẳng từ AST — chúng chỉ nhận **GIÁ TRỊ**, không nhận **BẢNG**:

```
gui_form(url, headers, body, timeout)
tach_url(url)
host_duoc_phep(host)
chan_moi_truong(moi_truong)
_ma_hoa_form(body)
```

> **Kết luận suy ra từ dữ liệu, không từ lời khai:** hai bảng này là **HẰNG SỐ ĐÓNG**. Thêm hãng
> thứ hai vào danh sách trắng **chỉ còn đúng một đường: sửa chính văn bản nguồn của
> `app/http_jt.py`**. Không tham số, không biến môi trường, không sổ đăng ký.

*Hai lần bộ dò này từng báo SAI, ghi lại để người sau không lặp:* (a) bản dò theo **tên tham số**
gọi `host_duoc_phep(host)` là "điểm tiêm" — nhưng `host` chính là **giá trị đang bị kiểm**;
(b) bản soi **cả cây con** của đối số báo `HOST_HANG` "có điểm tiêm" ở dòng 731, nơi nó chỉ được
`', '.join(...)` để **in ra thông điệp**. Cả hai đã sửa; cả hai đều có ca tự kiểm (§7).

### 3.5 Nhãn hiệu hãng lộ trong thông điệp — **4 chỗ, chỉ là CHỮ**

`test_a6` khẳng định đúng 4 dòng (108, 115, 116, 831), và **loại docstring** khỏi phép đếm.

| dòng | trích |
|---:|---|
| 108 | `J&T/` — tiền tố thông điệp của `chan_moi_truong` |
| 115–116 | hai tên host (hằng số, không phải thông điệp) |
| 831 | `thân RỖNG — J&T luôn cần trường \`bizContent\`` — `_ma_hoa_form` |

> Docstring là literal trong cây cú pháp nhưng **KHÔNG BAO GIỜ** được in ra cho ai. Bản đầu của bộ
> dò tính cả docstring và báo **10 dòng** trong khi thực tế chỉ **4**. Đây đúng là bài học
> `thu_bien_driver.py` ca a4 ("grep đọc cả chú thích") lặp lại ở tầng AST.

---

## 4. SƠ ĐỒ — chỗ gắn chặt nằm ở đâu

```
                        gui_form(url, headers, body, timeout)
                                        │
   ┌────────────────────────────────────┼────────────────────────────────────┐
   │ LÕI DÙNG CHUNG (vendor-neutral)    │                                    │
   │                                    ▼                                    │
   │  _kiem_tra_het_gio → _chuan_bi_headers → _ma_hoa_form                   │
   │  _gia_tri_can_che ──► che_bi_mat ◄── _bien_the                          │
   │  _mo_ket_noi → connect → request("POST") → getresponse → read           │
   │  _loi_tu_ngoai_le · _doc_retry_after · _loi_cho_lai · _tra_loi_tu_http  │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │
        ┌───────────────────────────────┴───────────────────────────────┐
        ▼                                                               ▼
 ╔═══════════════════════════╗                          ╔═══════════════════════════════╗
 ║ GẮN CHẶT 1 — HOST         ║                          ║ GẮN CHẶT 2 — TÊN CREDENTIAL   ║
 ║ tach_url() dòng 742:      ║                          ║ _gia_tri_trong_json  dòng 285 ║
 ║   if host in HOST_HANG:   ║                          ║ _gia_tri_bi_mat_*    dòng 311 ║
 ║        ↑                  ║                          ║ _gia_tri_bi_mat_tu_ph dòng 343║
 ║   HOST_HANG = (2 host J&T)║                          ║        ↑                      ║
 ║   KHÔNG tham số, KHÔNG sổ ║                          ║  TRUONG_CREDENTIAL = 4 tên J&T║
 ║   đăng ký (BẢNG 3.4)      ║                          ║  → PHAN_HOI → regex           ║
 ║                           ║                          ║  KHÔNG điểm tiêm (BẢNG 3.4)   ║
 ║ ⇒ host THẬT của hãng #2   ║                          ║ ⇒ credential NGẮN của hãng #2 ║
 ║   bị TỪ CHỐI, 0 lượt nối  ║                          ║   RÒ vào than/headers/str(e)  ║
 ╚═══════════════════════════╝                          ╚═══════════════════════════════╝
        │                                                               │
        │        ┌──────────────────────────────────────────┐           │
        └───────►│ RÀNG BUỘC HÌNH DẠNG (không phải J&T)      │◄──────────┘
                 │ · chỉ POST   (dòng 1133)                  │
                 │ · chỉ x-www-form-urlencoded (_ma_hoa_form)│
                 └──────────────────────────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────────┐
                    │ HÃNG GIẢ MẪU chạy được ở đây          │
                    │ — CHỈ vì stub của nó trên 127.0.0.1   │
                    └───────────────────────────────────────┘
```

---

## 5. PHÉP ĐO SẮC NHẤT — ma trận 2×2 (gắn chặt số 2)

Stub **ECHO LẠI** nguyên header + thân nhận được, kèm **HTTP 401** ⇒ mọi thứ ta gửi đi đều có cơ
hội xuất hiện trong `than_da_che` / `headers_da_che` / `str(e)`. Canary `A1b2C` (5 ký tự, dưới
ngưỡng `DAI_TOI_THIEU_DE_CHE = 8`).

| | **tên của J&T** (`privateKey`) | **tên của HÃNG GIẢ** (`x-mau-khoa-bi-mat`, `maTaiKhoanGia`) |
|---|---|---|
| **NGẮN** (5 ký tự) | ✅ **che** — nhờ tầng *theo TÊN* | ❌ **RÒ** `than_da_che` + `headers_da_che` + `str(e)` ← **GẮN CHẶT** |
| **DÀI** (35 ký tự) | ✅ **che** — nhờ tầng *theo ĐỘ DÀI* | ✅ **che** — nhờ tầng *theo ĐỘ DÀI* |

Ca thử: `CaGanChat.test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia`

**Đọc bảng này:** tầng che **theo ĐỘ DÀI** thì vendor-neutral — cả hai hãng đều được che. Tầng che
**theo TÊN** — tầng **BẮT BUỘC** để che credential ngắn (`_dang_che`: "*ngưỡng độ dài một mình bỏ sót
credential NGẮN*") — **chỉ đúng cho bốn tên của J&T**. Hãng thứ hai **không được thừa hưởng** nó.

**Đối chứng đường cho phép đo này:** `test_c2b` khẳng định bảng **không rỗng** và khớp 100% với
`adapter_jt.TRUONG_CREDENTIAL` — nếu không, ca trên có thể xanh vì bảng rỗng (một cách xanh sai).
`test_e4` vá **tạm trong bộ nhớ** bảng tên và khẳng định vụ rò **biến mất** — chứng minh phép đo
đang đo **đúng bảng tên**, không phải một thứ khác.

---

## 6. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA, SỐ SKIP

`HEAD = 148ecd3` (`integration/g19`). Mọi lệnh chạy trong worktree riêng
`g20-ag06-dahang`, tại `app/`.

### 6.1 Bộ đo mới của AG-06

```sh
$ PYTHONPATH=app:app/thu:trien_khai/g20-dahang python3 app/thu/thu_g20_dahang.py
Ran 27 tests in 98.774s
OK
exit 0        # 27 ca, 0 hỏng, 0 lỗi, 0 BỎ QUA (skip)
```

### 6.2 Bộ dò ranh giới (AST)

```sh
$ python3 trien_khai/g20-dahang/phan_tich_gan_chat.py
… 5 bảng bằng chứng in ra stdout …
exit 0
$ python3 trien_khai/g20-dahang/phan_tich_gan_chat.py --json trien_khai/g20-dahang/bang_chung_ast.json
exit 0
```

### 6.3 ĐỐI CHỨNG ĐƯỜNG — không hồi quy

Bộ thử J&T của G16, chạy **trước** khi AG-06 thêm bất cứ gì, để lấy mốc:

```sh
$ PYTHONPATH=app:app/thu python3 app/thu/thu_http_jt.py
Ran 57 tests in 95.923s
OK
exit 0        # MỐC: 57 ca, 0 hỏng
```

Rồi chạy lại **bên trong** bộ đo mới (`CaDoiChungDuong.test_d2`), trên cùng cây, sau khi AG-06 đã
thêm 3 tệp:

```
[đối chứng đường] thu_http_jt: 57 ca, 0 hỏng, exit 0
```

**57 → 57. Không hồi quy.** Ca thử đếm **cả SỐ CA**, không chỉ mã thoát: một bộ thử bị ai đó **rút
bớt ca** vẫn thoát 0, và mã thoát một mình là một lời khai không đủ (§12.1 luật 5). Hằng số mốc
`MOC_THU_HTTP_JT = 57` nằm trong tệp bộ thử, kèm `assertGreaterEqual`.

### 6.4 BẰNG CHỨNG TRUNG TÂM — `http_jt.py` KHÔNG BỊ SỬA

```sh
$ sha256sum app/http_jt.py
ae2bb05d05a0f8e8f8a0d5ad89145f49dc5c4d28dc2a91dcef23f364527a661b  app/http_jt.py

$ git hash-object app/http_jt.py
93ac1e036f1e42e743c7f53afa36c35be1f2e837

$ git rev-parse HEAD:app/http_jt.py
93ac1e036f1e42e743c7f53afa36c35be1f2e837
```

**Blob trên đĩa TRÙNG blob ở `HEAD`** ⇒ tệp này chưa từng bị đụng vào, không chỉ "không bị sửa
thêm". `CaHangGiaChayDuoc.test_b6` khẳng định cả hai vế (SHA ổn định trong suốt lượt chạy **và**
trùng blob `HEAD`), kèm đối chứng dương rằng hàm băm **bắt được** một thay đổi thật.

### 6.5 Số ca PHỦ ĐỊNH đều có ĐỐI CHỨNG ĐƯỜNG

| ca phủ định | đối chứng dương đi kèm |
|---|---|
| `c1a` host thật của hãng giả bị từ chối, 0 lượt nối | `c1b` **cùng URL đó trên loopback thì MỞ** (200); `host_duoc_phep("127.0.0.1")` là `True` |
| `c2a` tên hãng giả thì rò | `c2b` bảng không rỗng, khớp 100% `adapter_jt`; `e4` vá bảng ⇒ hết rò |
| `c3` chuỗi JSON không gửi được | `c3` `{"duLieuDon": "{}"}` (dict) thì gửi được |
| `c4` sandbox/production bị chặn | `c4` **`mock` MỞ** (`chan_moi_truong(MOCK) is None`) |
| `b5` chậm quá hạn ⇒ không biết | `b5` **cùng chế độ chậm, chờ đủ ⇒ 200** |
| `a1` hằng hãng được nhận | `a1` `DAI_TOI_THIEU_DE_CHE`/`HOST_CUC_BO`/… phải là `CHUNG` |
| `a2` hai hàm chốt chặn là đặc thù | `a2` `gui_form`/`che_bi_mat`/`_tra_loi_tu_http` phải vendor-neutral |
| `a3` bảng ĐÓNG | `e3` **nguồn có sổ đăng ký thật ⇒ bộ dò báo MỞ** |

### 6.6 TỰ KIỂM BỘ DÒ (bắt buộc, docs/QA_G13_G15.md §6.3)

| ca | đột biến | kỳ vọng |
|---|---|---|
| `e2` (a) | nguồn sạch, `GIOI_HAN = 5` | `CHUNG` — **đối chứng đường** |
| `e2` (b) | nhét `"demoopenapi.jtexpress.vn"` | `DAC_THU_JT` — **đỏ** |
| `e2` (c) | `BANG_MO_RONG = TRUONG_CREDENTIAL + (…)` | `DAN_XUAT_TU_DAC_THU` — **đỏ** |
| `e3` | `HOST_HANG = dang_ky_host(HOST_HANG + (…,))` | `dong_bang = False` — **đỏ** |
| `e3` | nguồn THẬT của `http_jt.py` | `dong_bang = True` — **đối chứng đường** |
| `e4` | vá `TRUONG_CREDENTIAL_PHAN_HOI` trong bộ nhớ | vụ rò **biến mất** — **đỏ** |
| `a4` | adapter giả có host hoàn toàn khác | `canh_lech` **khác rỗng** — **đỏ** |
| `a5` | nguồn có `.request('GET', …)` | bộ dò đọc ra `GET` — **đỏ** |
| `a6` | `"J&T"` trong docstring vs trong `raise` | `[]` vs `[2]` — **hai chiều** |
| `e1` | `connect(("example.com", 80))` | `AssertionError: CHẶN MẠNG` — **đỏ**, máy đếm ghi nhận |

---

## 7. Hãng giả chạy được — CHI TIẾT

`CaHangGiaChayDuoc` (6 ca). Mọi lượt đi tới stub loopback; cổng do hệ điều hành cấp (bind `0`) nên
không đụng làn nào khác.

| ca | đo gì | kết quả |
|---|---|---|
| `b1` | gửi đầu-cuối: `duLieuDon`, `X-Mau-*`, chữ ký HMAC | 200, thân **NGUYÊN VĂN**, stub nhận đúng byte; **không** có `digest`/`bizContent` |
| `b2` | chữ ký hãng giả ≠ chữ ký J&T, và đi lên dây nguyên văn | hai chữ ký **khác nhau**; lớp chung không sửa |
| `b3` | ba kết cục trên hãng giả | 500→`LoiTamThoi`/`khong-biet` · 400/401→`LoiVinhVien`/`hang-tu-choi` · 429→`qua-han-muc` · 408→`khong-gui-di` · cắt kết nối→`khong-biet` |
| `b4` | `Retry-After: 7` và `86400` | `cho_giay=7.0` và `CHO_TOI_DA` (kẹp trần); lớp **KHÔNG NGỦ** (< 3s) |
| `b5` | hết giờ đọc | `LoiTamThoi`, `khong-biet`, `timeout=True`; đối chứng dương ⇒ 200 |
| `b6` | `http_jt.py` không bị sửa | blob trùng `HEAD` |

### ĐỐI CHỨNG ĐƯỜNG — CÙNG một hàm đo, HAI hãng, CÙNG bảng kết cục

`CaDoiChungDuong.test_d1` chạy **đúng một** hàm `do_mot_luot()` trên cả hai hồ sơ, cho **9 chế độ**,
và khẳng định **hai cột BẰNG NHAU**:

| chế độ | J&T (`stub_jt`) | HÃNG GIẢ (`stub_hang_gia`) | bằng? |
|---|---|---|---|
| `thanh_cong` | `TraLoiHTTP` 200 | `TraLoiHTTP` 200 | ✅ |
| `hang_tu_choi` | `TraLoiHTTP` 200 (mã lỗi nằm trong thân) | y hệt | ✅ |
| `http_400` | `LoiVinhVien` / `hang-tu-choi` | y hệt | ✅ |
| `http_401` | `LoiVinhVien` / `hang-tu-choi` | y hệt | ✅ |
| `http_408` | `LoiTamThoi` / `khong-gui-di` | y hệt | ✅ |
| `http_429` | `LoiTamThoi` / `qua-han-muc` | y hệt | ✅ |
| `http_500` | `LoiTamThoi` / `khong-biet` | y hệt | ✅ |
| `cham` (0.4s hạn, 2.0s trễ) | `LoiTamThoi` / `khong-biet`, `timeout=True` | y hệt | ✅ |
| `cat_ket_noi` | `LoiTamThoi` / `khong-biet` | y hệt | ✅ |

**Vì sao đây là bằng chứng mạnh:** hai hồ sơ **khác nhau ở đúng ba thứ** AG-06 nêu (tên trường, chữ
ký, host/đường dẫn). Nếu lớp chung có **nhánh riêng cho J&T** ở phần phân loại kết cục, hai cột sẽ
lệch ngay. **Hai cột giống nhau ⇒ phần phân loại kết cục là vendor-neutral.**

---

## 8. VIỆC CÒN LẠI — cái AG-06 KHÔNG làm, và cái cần làm tiếp

AG-06 **được cấp ghi đúng ba đường**: `app/thu/thu_g20_dahang.py`, `trien_khai/g20-dahang/`,
`docs/G20_DA_HANG.md`. Mọi thứ dưới đây **NẰM NGOÀI phạm vi được cấp** — ghi ra để người sau quyết,
**không tự làm**.

| # | Việc | Vì sao chưa làm |
|---|---|---|
| **R-1** | Mở `HOST_HANG` thành sổ đăng ký (tham số `cho_phep_them` hoặc bảng theo hãng) | **Sửa tệp của làn khác** (`app/http_jt.py`). AG-06 bị cấm. Cần một làn sở hữu tệp đó quyết định |
| **R-2** | Tách `TRUONG_CREDENTIAL` theo hãng | Như trên. Đánh đổi: mở rộng bảng là **che thừa** ⇒ thông điệp chẩn đoán khó đọc hơn; giữ nguyên là **rò** credential ngắn của hãng #2 |
| **R-3** | Hỗ trợ JSON body / phương thức khác `POST` | Sửa `_ma_hoa_form` + `gui_form` — tệp của làn khác. Hiện **không có** đường nào |
| **R-4** | Bỏ nhãn `J&T` khỏi thông điệp (dòng 108, 831) | Sửa tệp của làn khác. Chỉ là chữ, **không phải chặn kỹ thuật** — nhưng người trực đọc log sẽ tưởng sự cố của J&T |
| **R-5** | Ánh xạ mã lỗi / mã trạng thái của hãng thứ hai | Việc của **adapter**. **D-4:** mã chưa xác minh ⇒ `NEEDS_REVIEW`, **KHÔNG đoán** |
| **R-6** | Credential thật của hãng thứ hai, endpoint thật | **CHƯA CẤP.** AG-06 tuyệt đối (1): không gọi API hãng kể cả sandbox |
| **R-7** | Commit | AG-00 sở hữu. AG-06 **không** chạy `git add`/`commit` |

**Khuyến nghị xếp hạng** (dựa trên số đo, không dựa trên cảm nhận):

1. **R-1** — chặn cứng nhất: không sửa thì hãng thứ hai **không thể** chạy thật, kể cả khi mọi thứ
   khác đã sẵn sàng.
2. **R-2** — rủi ro **an toàn**: rò credential vào log. Cùng mức với các lỗ hổng G18 đã vá.
3. **R-3** — quyết định kiến trúc: nếu hãng thứ hai dùng JSON thì phải viết lớp mới, và **biết điều
   đó từ bây giờ** rẻ hơn nhiều so với biết sau khi đã hứa "đa hãng".
4. **R-4** — vệ sinh vận hành, không chặn ai.

---

## 9. Tệp của AG-06

| đường | là gì |
|---|---|
| `app/thu/thu_g20_dahang.py` | **MỚI** — 27 ca: ranh giới AST · hãng giả chạy được · hai chỗ gắn chặt · đối chứng đường · tự kiểm bộ dò |
| `trien_khai/g20-dahang/stub_hang_gia.py` | **MỚI** — stub HÃNG GIẢ MẪU, loopback/cổng 0, host `.invalid` |
| `trien_khai/g20-dahang/phan_tich_gan_chat.py` | **MỚI** — bộ dò ranh giới bằng AST (5 bảng) |
| `trien_khai/g20-dahang/bang_chung_ast.txt` · `.json` | **MỚI** — bằng chứng AST của lượt chạy này |
| `trien_khai/g20-dahang/README.md` | **MỚI** — cách chạy lại mọi phép đo |
| `docs/G20_DA_HANG.md` | **MỚI** — tài liệu này |

**KHÔNG đụng vào:** `app/http_jt.py` · `app/adapter_jt.py` · `app/gioi_han.py` (tệp của làn khác) ·
`main` · `.git`. Không push, không deploy, không tunnel, không mở cổng ra ngoài, không mở
`CHO_PHEP_LIVE`, không credentials thật, không `.env`, không PostgreSQL (D-8: vẫn SQLite; cụm
`:5432` là của dự án khác — **cấm đụng**).

**Trạng thái commit:** AG-06 **KHÔNG** commit. Ba tệp mới nằm trong worktree riêng
`g20-ag06-dahang`, chờ AG-00 gộp.
