# G18 — ĐƯỜNG RÒ BÍ MẬT: ECHO CỦA HÃNG VÀ ĐƯỜNG DẪN URL

Làn: **AG-03** (WAVE G18). Nền: `integration/g17` @ `7b741c8`. Nhánh: `g18-ag03-secretpaths`.

Tệp được cấp để ghi — và CHỈ những tệp này:

| Tệp | Trạng thái | Ghi chú |
|---|---|---|
| `app/http_jt.py` | sửa (nhỏ, tập trung vào che bí mật) | **AG-02 cũng ghi tệp này** — xem §8 |
| `app/thu/thu_http_jt.py` | **KHÔNG SỬA MỘT DÒNG NÀO** | cố ý, để AG-00 gộp không phải giải tranh chấp |
| `app/thu/thu_g18_bi_mat.py` | **mới** | toàn bộ bằng chứng của làn này |
| `docs/G18_SECRET_PATHS.md` | **mới** | tệp này |

---

## 0. VIỆC NÀY LÀM GÌ — VÀ KHÔNG LÀM GÌ

WAVE G18 **chỉ đóng lỗ hổng đã ghi ra**. Ba cổng G16-A đã ĐẠT; wave G17 đã ĐẠT với 1460 ca / 38 bộ /
exit 0. Làn này **không làm lại** những mục đó.

Hai lỗ hổng được AG-01 ghi ở mục **CHƯA ĐỎ** của lượt nghiệm thu G17 (`docs/G17_TRANSPORT.md` §5.3):

* **(a)** *"bí mật hãng ECHO LẠI mà ta chưa từng gửi"* — AG-02 chỉ che thứ **TA** gửi.
* **(b)** *"bí mật nằm trong ĐƯỜNG DẪN URL"* — AG-02 in `phan.path` **nguyên văn, có chủ ý**.

Cả hai đều là **che THIẾU**, không phải che sai. Không có chốt nào của G16/G17 bị nới.

---

## 1. LỖ HỔNG (a) — BÍ MẬT CỦA HÃNG, TA CHƯA TỪNG GỬI

### 1.1 Cơ chế

`_gia_tri_can_che()` (G16/G17) dựng tập che từ **header + thân form + query của yêu cầu** — tức là
chỉ những giá trị **TA** gửi đi. Một máy chủ trả về **bí mật của chính nó** (khoá riêng trong JSON
lỗi, `X-Api-Key`, `Set-Cookie` phiên) thì giá trị đó **không nằm trong tập che**, nên nó đi thẳng
vào `than_da_che` / `headers_da_che` / thông điệp ngoại lệ — tức là vào log.

### 1.2 ĐO ĐƯỢC TRƯỚC KHI VÁ (nền `7b741c8`, chưa sửa gì)

Stub cục bộ (`127.0.0.1`, cổng 0) trả **HTTP 401** với thân
`{"code":"145003030","data":{"privateKey":"HANG-GIUKHOA-9f3ac21b7d4e-KHONG-PHAI-CUA-TA"}}`
và header `X-PrivateKey-Echo` mang **đúng chuỗi đó**.

| Cửa | Trước khi vá |
|---|---|
| `str(e)` chứa bí mật của hãng | **True** ← RÒ |
| `than_da_che` chứa bí mật của hãng | **True** ← RÒ |
| `headers_da_che` chứa bí mật của hãng | **True** ← RÒ |

### 1.3 Cách vá — luật THEO TÊN, cố ý HẸP

`TRUONG_CREDENTIAL_PHAN_HOI` = bốn trường hợp đồng J&T **+ 24 tên** nữa
(`authorization`, `token`, `access_key`, `x-api-key`, `set-cookie`, `secret`, `signature`…).

Ba đường nhận diện, **cùng một luật**:

| Hàm | Đường |
|---|---|
| `_gia_tri_bi_mat_trong_json()` | khoá JSON trong thân phản hồi (đi đệ quy cả cây) |
| `_gia_tri_bi_mat_trong_vb()` | `ten=giá_trị` / `"ten":"giá_trị"` trong thân **KHÔNG phải JSON** (trang lỗi HTML của proxy, văn bản thuần) |
| vòng lặp header trong `_gia_tri_bi_mat_tu_phan_hoi()` | tên header phản hồi |

Điểm nối: `_tra_loi_tu_http()` mở rộng tập che **trước khi** che —
`can_che = can_che | _gia_tri_bi_mat_tu_phan_hoi(than, headers_tra_loi)`. Thứ tự có ý nghĩa: phải
nhận diện trên thân/header **THÔ**, vì sau khi che thì không còn gì để nhận diện.

**KHÔNG có luật nào che theo HÌNH DẠNG giá trị.** Hình dạng không phân biệt được một khoá bí mật
với một mã vận đơn, và che nhầm mã vận đơn là làm hỏng chẩn đoán — xem đối chứng đường §4.

**Ranh giới hợp đồng §36 vẫn nguyên:** thân của một lượt **2xx** trả về **NGUYÊN VĂN** cho người
gọi. Chỉ **HEADER** của lượt 2xx được che (vì `TraLoiHTTP.headers` là thứ hay bị đem đi log nhất).
Ca `k1c` canh đúng ranh giới này — nếu ai đó che luôn thân 2xx cho "chắc", `k1c` ĐỎ.

---

## 2. LỖ HỔNG (b) — BÍ MẬT NẰM TRONG ĐƯỜNG DẪN URL

### 2.1 QUYẾT ĐỊNH — và vì sao không chọn hai đường còn lại

G17 để lại một **quyết định có ghi chép**: in `phan.path` nguyên văn, vì đường dẫn là thứ duy nhất
cho biết lượt gọi đi tới endpoint nào. AG-01 ghi việc đó vào mục CHƯA ĐỎ. Làn này phải **quyết
định lại**. Ba lựa chọn:

| Lựa chọn | Vì sao không chọn |
|---|---|
| **Che cả đường dẫn** | Bịt thứ duy nhất cho biết lượt gọi đi tới endpoint nào. Sự cố `addOrder` hỏng mà thông điệp chỉ nói `/…` thì người trực không có gì để lần. Mitigation cũ ("credentials không đi qua URL") là **quy tắc vận hành**, không phải **chốt chặn trong mã** — mà lỗ hổng là chuyện mã không chặn được. |
| **Giữ nguyên văn** | Đúng lỗ hổng (b) mà lượt nghiệm thu G17 đã ghi. |
| **CHE TỪNG ĐOẠN** ← chọn | `/api/[DA-CHE]/order/addOrder` vẫn nói được endpoint, mà không nói ra bí mật. Đối chứng đường vẫn đo được (§4). |

### 2.2 Hai luật che một đoạn

`_duong_dan_da_che(url, headers, than)` → `(đường_dẫn_đã_che, số_đoạn_đã_che)`. Một đoạn bị che khi:

1. **`_doan_chua_bi_mat()`** — đoạn **LÀ** hoặc **CHỨA** một giá trị ta đã gửi đi. Hai mức:
   * **BẰNG NHAU cả đoạn** → áp cho **MỌI độ dài**. Bí mật 1–3 ký tự đặt nguyên một đoạn
     (`/api/j/order`) phải bị che, và so bằng nhau thì **không có tác dụng phụ nào**.
   * **NẰM TRONG đoạn** → chỉ áp khi bí mật **đủ dài** (≥ `DAI_TOI_THIEU_DE_CHE` = 8). So chuỗi con
     với bí mật 1 ký tự là che gần hết đường dẫn vì trùng một chữ cái — che nhầm mà không thêm an
     toàn, vì một ký tự đơn không mang thông tin.
2. **`_la_doan_bi_mat()`** — đoạn **trông như** một credential. Ba điều kiện **cùng lúc**: dài ≥ 20,
   chỉ gồm ký tự hợp lệ của một đoạn URL, và **trộn chữ-số** với ≥ 10 ký tự khác nhau. Nhờ vậy
   `webopenplatformapi`, `api`, `order`, `addOrder`, `v1` đều **KHÔNG** bị che.

So khớp chạy trên **cả dạng thô lẫn dạng đã `unquote`**, nên bí mật có dấu tiếng Việt đi qua
percent-encoding vẫn khớp.

### 2.3 CỬA SAU — điều mà lượt vá đầu tiên đã bỏ sót, và ĐO ĐƯỢC

Che lúc **IN** là chưa đủ. Stub echo lại **đường dẫn yêu cầu** trong thân phản hồi — và thân đó đi
vào `than_da_che` rồi vào thông điệp. Sau khi `mo_ta` đã che, `str(e)` **VẪN** chứa bí mật đường dẫn.

Vì vậy đường dẫn còn được đưa vào **TẬP CHE**: `_gia_tri_tu_duong_dan(url, moc)` thêm mọi đoạn nguy
hiểm vào `_gia_tri_ta_gui()` (nguồn thứ **TƯ**, sau header · thân form · query). Đây là ca `k2`, và
nó có **hai phép đột biến riêng** (§5) để hai cơ chế không che lẫn nhau.

### 2.4 BIÊN GIỚI ĐÃ BIẾT — nói thẳng, không giấu

**Một token ≤ 3 ký tự CHỈ có mặt trong đường dẫn thì KHÔNG nhận diện được.** `zq` trong
`/api/zq/order/addOrder` không phân biệt được với `v1` trong `/api/v1/order` — và **bất kỳ** luật nào
che được `zq` cũng che luôn `v1`, tức là che mất chính endpoint. Đây là **giới hạn thông tin**,
không phải chỗ có thể vá thêm.

Ca `k2d` **đo đúng hiện trạng đó** và đo luôn đối chứng đường (token **dài** trong đường dẫn thì
**CHE**), để không ai đọc sự im lặng thành "đã phủ". Nó **không** phải một lời khẳng định rằng hiện
trạng là an toàn.

**Hệ quả thứ hai, chấp nhận có ý thức:** một mã vận đơn dài ≥ 20 ký tự trộn chữ-số đặt trong đường
dẫn **SẼ bị che**. Cùng đánh đổi mà `TRUONG_CREDENTIAL` đã chọn ở G16 ("thà thông điệp khó đọc còn
hơn một credential đi vào log"), và mã vận đơn thật của J&T nằm trong **THÂN**, không nằm trong
đường dẫn (`adapter_jt.DUONG_*` là hằng số).

Một chỗ in đường dẫn nguyên văn **thứ hai** đã bị đóng luôn: thông điệp `"đường dẫn … không bắt đầu
bằng '/'"` trong `tach_url()`. Nhánh đó gần như không tới được (`urlsplit` đã bảo đảm đường dẫn của
URL tuyệt đối bắt đầu bằng `/`) — nhưng "gần như" chính là lý do nó từng nằm lại.

### 2.5 QUERY — đo lại trong cùng bộ thân

Đề bài nêu *"query string / path"*. Query đã được **G17 (AG-02)** che bằng `_gia_tri_tu_url`; ca
`k2e` **đo lại** nó trong cùng bộ thân với đường dẫn, để một chỗ chạy được trọn câu chuyện "bí mật
trong URL". Ca nặng nhất là lượt **vừa có bí mật ở query, vừa có bí mật ở đường dẫn** — hai cơ chế
che khác nhau cùng phải làm việc, nên ca khẳng định **từng bí mật một**, không gộp: gộp lại thì một
cơ chế hỏng vẫn có thể cho `than_da_che` sạch nhờ cơ chế kia, và ca sẽ xanh một cách vô nghĩa.

---

## 3. MỞ RỘNG BỘ DÒ — SÁU DẠNG × BA VỊ TRÍ

G16/G17 chỉ phủ **bốn TÊN trường credential** với chuỗi **ASCII**. Ca `k3` chạy một ma trận:

| Dạng | Giá trị | header | thân form | đường dẫn |
|---|---|:--:|:--:|:--:|
| ngắn 1 ký tự | `j` | ✔ | ✔ | ✔ |
| ngắn 2 ký tự | `zq` | ✔ | ✔ | ✔ |
| ngắn 3 ký tự, có ký tự đặc biệt | `a%b` | ✔ | ✔ | ✔ |
| **có dấu tiếng Việt** | `mật-khẩu-Ộ-Ước` | — | ✔ | ✔ |
| ký tự đặc biệt | `aB?cd&e=f` | ✔ | ✔ | ✔ |
| ký tự đặc biệt 2 | `p@ss+w%rd#1` | ✔ | ✔ | ✔ |

Mỗi ô đều có **ĐỐI CHỨNG DƯƠNG theo từng vị trí**: bí mật phải **thật sự** đi trên dây ở đúng vị trí
đó (đọc thân **THÔ** của stub) trước khi khẳng định nó không rò.

**Hai chỗ KHÔNG có ca, kèm lý do** — để không ai đọc thiếu sót thành đã phủ:

* **Dấu tiếng Việt ở HEADER**: `http.client` mã hoá header bằng **latin-1**, nên `ậ` (U+1EAD)
  **không lên được dây**. Đó là giới hạn của **HTTP**, không phải của phép che. `http_jt` từ chối
  nó bằng `LoiVinhVien` kèm câu *"chữ có dấu phải nằm trong THÂN (UTF-8)"*.
* **Token ≤ 3 ký tự chỉ có trong đường dẫn**: xem §2.4 — biên giới thông tin.

---

## 4. ĐỐI CHỨNG ĐƯỜNG — CHUỖI KHÔNG PHẢI BÍ MẬT ĐI QUA NGUYÊN VĂN

Một cổng che **mọi thứ** là một cổng **vô dụng**: nó làm thông điệp chẩn đoán không đọc được, và
người trực sẽ tắt nó đi. Ca `k4` khẳng định, trên cùng một thông điệp lỗi:

| # | Chuỗi | Kỳ vọng |
|---|---|---|
| 1 | `VH000000001VN` — dữ liệu **hãng** trả về, ta **chưa từng gửi**, tên không phải credential | **NGUYÊN VĂN** |
| 2 | `"hãng không cấp được mã vận đơn"` — câu chữ của hãng | **NGUYÊN VĂN** |
| 3 | `145003030` — mã lỗi của hãng | **NGUYÊN VĂN** |
| 4 | `/webopenplatformapi/api/order/addOrder` — đường dẫn endpoint | **NGUYÊN VĂN từng đoạn** |
| 5 | `X-Ma-Don: VH12` — giá trị **ngắn** ở tên **không** phải credential | **KHÔNG** vào tập che |
| 6 | `X-Ma-Don: VH123456` — giá trị **dài** ở tên không phải credential | **CÓ** vào tập che |
| 7 | tên header/trường trong mô tả | **NGUYÊN VĂN** |

Hàng 5 và 6 là **cặp đối chứng của nhau**: nếu chỉ có hàng 5 thì nó chỉ đang chứng minh "tập che
rỗng", chứ không chứng minh ngưỡng còn tác dụng.

---

## 5. TỰ KIỂM BỘ DÒ — ĐỘT BIẾN MÃ SẢN PHẨM TRONG TIẾN TRÌNH CON

Luật 1 của `docs/QA_G13_G15.md` §6.3. Mỗi dòng là một **hồi quy có thật**, không phải một phép đột
biến cho vui. Ca `l1` chạy **11 phép đột biến**, mỗi phép trong một **tiến trình con**; ca phải **ĐỎ**.

| # | Đột biến | Hồi quy được canh |
|---|---|---|
| 1 | `_gia_tri_bi_mat_tu_phan_hoi = lambda than, h: set()` | tắt nhận diện bí mật của hãng ⇒ (a) quay lại nguyên vẹn |
| 2 | `TRUONG_CREDENTIAL_PHAN_HOI = ()` **+** `_MAU_CAP_TEN_BI_MAT` vô hiệu | gỡ danh sách TÊN ở cả ba đường |
| 3 | `_gia_tri_bi_mat_trong_json` + `_gia_tri_bi_mat_trong_vb` → rỗng | chỉ còn nhận diện theo tên HEADER, bỏ đọc THÂN |
| 4 | `_gia_tri_bi_mat_trong_vb = lambda vb, ra: None` | chỉ còn đọc JSON ⇒ trang lỗi HTML lộ nguyên văn |
| 5 | `_gia_tri_bi_mat_tu_phan_hoi = lambda than, h: set()` | bỏ che header phản hồi của lượt 2xx |
| 6 | `_duong_dan_da_che` → trả `urlsplit(url).path` | quay lại in **NGUYÊN VĂN** đường dẫn |
| 7 | như #6, nhưng chạy ca `k2b` | cửa `mo_ta` **một mình** cũng đủ rò |
| 8 | `_gia_tri_tu_duong_dan = lambda url, moc: set()` | che lúc IN mà không đưa vào **TẬP CHE** ⇒ cửa sau |
| 9 | `_la_doan_bi_mat = lambda d: False` | bỏ luật HÌNH DẠNG |
| 10 | `_doan_chua_bi_mat = lambda d, c: False` | bỏ luật "cả đoạn BẰNG NHAU" ⇒ bí mật NGẮN trong đường dẫn lộ |
| 11 | `_gia_tri_tu_url = lambda u: set()` | bỏ giá trị **QUERY** khỏi tập che ⇒ bí mật trong query lộ khi hãng echo lại |

Hai điều đáng ghi lại, vì cả hai đều là **bẫy thật** gặp phải trong lượt làm này:

* **Đột biến #2 phải gỡ CẢ mẫu đã biên dịch.** `_MAU_CAP_TEN_BI_MAT` là **bản sao** của danh sách
  tại lúc nạp mô-đun. Chỉ đặt danh sách về rỗng là một phép đột biến **KHÔNG có tác dụng** — và một
  phép đột biến không tác dụng thì **không chứng minh được gì**. Lượt chạy đầu đã ĐỎ vì đúng lý do
  này, và nó được ghi lại thay vì lặng lẽ sửa cho xanh.
* **HỎNG GIẢ do stub ghi bản ghi SAU khi gửi byte.** Client nhận đủ thân rồi quay về **trước** khi
  luồng máy chủ kịp ghi `da_tra_loi` ⇒ ca đỏ dù mã đúng. Đây đúng khuôn HỎNG GIẢ đã xảy ra THẬT ở
  G17 (`thu_http_jt.cho_tra_loi` ghi lại sự cố 15/10). Tệp này dùng `cho_tra_loi()` **chờ có hạn**
  trước mọi phép so thân.

Ca `l2` là **ĐỐI CHỨNG ĐƯỜNG** của chính cổng tự kiểm: chạy **nguyên** bốn lớp ca, **không** đột
biến, trong tiến trình con — phải **XANH**. Không có nó thì "đột biến làm ca đỏ" không chứng minh
được gì, vì một bộ chạy con **luôn-đỏ** cũng làm mọi dòng ở bảng trên "đạt".

Chốt ngược: `l1` khẳng định `len(CA) >= 11` và `l2` khẳng định `len(LOP_CA) >= 4` — một danh sách
**rỗng** cũng làm vòng lặp "đạt" một cách vô nghĩa (đúng khuôn hỏng mà `chay_tat_ca.sh` đã gặp với
`VIP_TOI_THIEU_BO`).

---

## 6. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SHA

### 6.1 Chốt chặn mạng của chính bộ thử này

Ca `l3` khẳng định: nối ra host ngoài **BỊ CHẶN** trước khi mở socket; nối loopback **ĐI QUA**; và
**mọi** lượt nối của tệp này là loopback, trừ **đúng một** lượt cố ý của ca tự kiểm (nó nằm ở vị trí
đã biết và đã bị chặn). Đó là bằng chứng cho **"không gọi hãng"** — không phải một lời khai.

### 6.2 Lỗ hổng ĐO ĐƯỢC TRƯỚC VÀ SAU — cùng một phép đo, hai bản `http_jt.py`

Phép đo dưới đây lấy **bản `http_jt.py` của nền `7b741c8`** bằng `git show`, đặt vào một thư mục
tạm **cùng** `transport.py`, rồi chạy **đúng một kịch bản** hai lần với `PYTHONPATH` khác nhau.
`sys.path[0]` của một script là thư mục chứa script, nên script phải nằm ở thư mục **khác** với
mô-đun — lượt chạy đầu đã cho hai kết quả **giống hệt nhau** vì lỗi đó, và nó được sửa chứ không
được đọc thành "không có gì để vá".

```
===== TRUOC KHI VA (http_jt.py @ 7b741c8) =====
  module dang do: …/nencu/http_jt.py
  (a) HANG_RIENG trong str(e)       : True
  (a) HANG_RIENG trong than_da_che  : True
  (a) HANG_RIENG trong headers_che  : True
  (b) DUONG_BI_MAT trong str(e)     : True
  ĐỐI CHỨNG ĐƯỜNG (msg+code nguyen van): True
  mo_ta: POST http://127.0.0.1/api/DUONG-DAN-CHUA-BI-MAT-c41f9a2b7e/order/addOrder · …

===== SAU KHI VA (cay lam viec) =====
  module dang do: …/moi/http_jt.py
  (a) HANG_RIENG trong str(e)       : False
  (a) HANG_RIENG trong than_da_che  : False
  (a) HANG_RIENG trong headers_che  : False
  (b) DUONG_BI_MAT trong str(e)     : False
  ĐỐI CHỨNG ĐƯỜNG (msg+code nguyen van): True
  mo_ta: POST http://127.0.0.1/api/[DA-CHE]/order/addOrder (1 đoạn đường dẫn đã che) · …
```

**Bốn cửa rò đổi từ `True` sang `False`; đối chứng đường (`msg` + `code` của hãng) vẫn `True` ở cả
hai lượt.** Đó là toàn bộ tuyên bố của làn này, ở dạng đo được.

### 6.3 CHI PHÍ của phép nhận diện mới — đo, không đoán

`_gia_tri_bi_mat_tu_phan_hoi()` chạy trên **mọi** phản hồi. Hai phép đo, ghi lại để người sau không
phải đo lại:

| Thân phản hồi | Chi phí |
|---|---|
| 69 B (một phản hồi J&T điển hình) | **11,2 µs** |
| 355 KB (trang lỗi proxy, giả định xấu) | **12,9 ms** cho một lượt quét `re`; 0,5 ms cho `json.loads` cùng thân |

Một bộ lọc thô (`lower()` + 28 phép `in`) trước khi quét đã được **viết ra, đo, rồi GỠ BỎ**: nó tốn
**9,5 ms** cho cùng thân 355 KB, tức là chỉ có lợi khi văn bản **không** chứa tên nào và có hại khi
có — một đánh đổi **hoà**, không đáng thêm mã. Đường này chỉ chạy trên thân **phản hồi lỗi** (vài
trăm byte ⇒ ≈ 18 µs), và nó luôn nằm cạnh một lượt đi-về mạng tốn hàng mili-giây.

### 6.4 Lệnh đã chạy — mã thoát TRƯỚC ống

> Chạy từ gốc worktree. `GIT_CONFIG_*` hỏng sẵn trong máy này (khóa rỗng) nên mọi lệnh `git` dùng
> `env GIT_CONFIG_COUNT=0`; `chay_tat_ca.sh` được gọi kèm biến đó.

```sh
# 1. Bộ thử của làn này — 15 ca
python3 app/thu/thu_g18_bi_mat.py > /tmp/g18.log 2>&1 ; echo "EXIT=$?" ; tail -4 /tmp/g18.log

# 2. Không hồi quy trên các bộ đang canh http_jt
python3 app/thu/thu_http_jt.py > /tmp/jt.log 2>&1 ; echo "EXIT=$?" ; tail -4 /tmp/jt.log
python3 app/thu/thu_qa_g16.py  > /tmp/q16.log 2>&1 ; echo "EXIT=$?" ; tail -2 /tmp/q16.log

# 3. Cổng toàn dự án (tự dò app/thu/thu_*.py, nên tệp mới TỰ VÀO cổng)
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g18_ag03_data \
    sh app/thu/chay_tat_ca.sh > /tmp/veh_g18_ag03_gate.log 2>&1 ; echo "EXIT=$?"
```

| Lệnh | Số ca | Bỏ qua | Mã thoát |
|---|---|---|---|
| `python3 app/thu/thu_g18_bi_mat.py` | **15** | 0 | **0** |
| `python3 app/thu/thu_http_jt.py` | **57** | 0 | **0** |
| `python3 app/thu/thu_qa_g16.py` | **61** | 0 | **0** |
| `env GIT_CONFIG_COUNT=0 … sh app/thu/chay_tat_ca.sh` | **1474** · 39 bộ | 0 | **0** |

`thu_g18_bi_mat.py` xuất hiện trong bảng của cổng với dòng
`✓ thu_g18_bi_mat.py  15 ca` — **không phải sửa danh sách viết cứng nào**, vì `chay_tat_ca.sh`
**tự dò** (`find app/thu -name 'thu_*.py'`).

### 6.5 SHA

| Vật | Trước | Sau |
|---|---|---|
| Nhánh | `g18-ag03-secretpaths` | `g18-ag03-secretpaths` |
| Commit nền | `7b741c88b3b280d65f80b5e11301f17ebd767b26` | commit của làn — xem §6.6 |
| `app/http_jt.py` — sha256 | `7f8d8949bf381c889aa2d349e20f8710e32175e0dbd17d1af04d4c1539923c92` | xem §6.6 |
| `app/thu/thu_g18_bi_mat.py` — sha256 | *(không tồn tại)* | xem §6.6 |
| `app/thu/thu_http_jt.py` | — | **KHÔNG SỬA MỘT DÒNG NÀO** |
| `main` | `de740dcd16617328f49f5ab97fac3ceb741e39fa` | **không đụng tới** |

### 6.6 LƯỢT ĐÓNG BĂNG

Ba commit, tất cả **trên nhánh riêng** `g18-ag03-secretpaths`. **KHÔNG push, KHÔNG deploy, KHÔNG
tunnel, KHÔNG đụng `main`.**

| Commit | Nội dung | Vì sao tách |
|---|---|---|
| `7b741c88b3b280d65f80b5e11301f17ebd767b26` | **nền** (`integration/g17`) | điểm rẽ của làn |
| `d23d875b47cc4696efbe2bd488181fb881721779` | mã + bộ thử + tài liệu | lượt chạy cổng **XANH** đầu tiên (§8) |
| *(commit kế)* | + ca `k2e` (query) và các số cuối | xem §6.7 |

Xem §6.7 cho bảng số cuối cùng của lượt chạy đóng băng.

### 6.7 BẢNG SỐ CUỐI CÙNG

*(điền ở commit chứa chính tệp này — xem khối "LƯỢT ĐÓNG BĂNG" ở cuối tệp)*

---

## 7. NGOÀI PHẠM VI — những gì làn này **KHÔNG** đo

1. **KHÔNG có lượt gọi hãng nào.** V-G09-01 + V-13906-05 **CHƯA CẤP**. Mọi phép đo đi tới stub cục
   bộ `127.0.0.1` cổng 0. Chưa từng có lượt gọi sandbox hay production nào, kể cả một lượt.
   Bộ thử xanh ở đây **KHÔNG** phải lời cho phép gọi sandbox, và **KHÔNG** được đọc thành
   "LIVE VERIFIED".
2. **KHÔNG đo được hành vi thật của J&T.** Cụ thể: hãng thật **có** echo bí mật của chính nó hay
   không. Cái **đo được** là: **NẾU** hãng làm vậy thì lớp HTTP của ta có chặn hay không.
3. **KHÔNG đo được** chữ ký thật, mã lỗi thật, TLS của hãng, giới hạn hạn mức, `Retry-After` thật.
4. **KHÔNG chạm CSDL nghiệp vụ** (D-8: vẫn SQLite). Không đụng cụm PostgreSQL `:5432` (đang giữ dữ
   liệu dự án khác: `vip_customs`, `vip_customs_g16`, `vip_customs_test`).
5. **KHÔNG mở** `CHO_PHEP_LIVE`, không sửa cảng sandbox/production trong `app/cau_hinh.py`.
6. **KHÔNG đoán mã trạng thái 110** (D-4). Mã chưa xác minh ⇒ `NEEDS_REVIEW`.
7. **KHÔNG đụng** chốt D-9 (city/area chặn cứng ngoài mock).
8. **KHÔNG push, KHÔNG deploy, KHÔNG tunnel.**
9. **KHÔNG có credentials thật**, không `.env`, không in bí mật ra log. Mọi "bí mật" trong bộ thử là
   chuỗi **GIẢ ĐỊNH** sống trong tiến trình — chính vì thế mà phép đo rò rỉ mới **ĐO ĐƯỢC**: ta biết
   **chính xác** chuỗi cần tìm.
10. **Tầng 3 (DOM/CSS trong Chromium)** và **E2E** không thuộc làn này.
11. **Biên giới §2.4**: token ≤ 3 ký tự **chỉ** có trong đường dẫn — **KHÔNG nhận diện được**, và
    làn này **không** tuyên bố đã phủ nó.

---

## 8. PHÁT HIỆN KHI CHẠY CỔNG — "CÂY SẠCH" LÀ MỘT CỔNG CHẶN THẬT, VÀ NÓ ĐÃ KÊU

Lượt chạy cổng **đầu tiên** của làn này cho kết quả: **1474 ca · 39 bộ chạy thật · exit 1**, và bộ
hỏng **duy nhất** là `thu_qa_g17.py`, ca `test_a1_cay_sach_va_head`:

```
  ✗ thu_qa_g17.py              53 ca  HỎNG (mã thoát 1)
        FAIL: test_a1_cay_sach_va_head (__main__.A_Nen)
```

Đây **không** phải lỗi của mã sản phẩm. `thu_qa_g17._cay_ban()` đọc `git status --porcelain -uall`
và **chỉ** miễn trừ hai đường của làn AG-01/G17 (`app/thu/thu_qa_g17*.py`, `docs/QA_G17*.md`). Hai
thay đổi **chưa `git add`** của làn này (`M app/http_jt.py`, `?? app/thu/thu_g18_bi_mat.py`) làm cây
**BẨN**, nên cổng "cây sạch" kêu — và nó kêu **đúng**: mọi số đo của một bộ thử đọc cây làm việc
đều vô hiệu nếu cây đang dở dang.

**Xử lý:** `git add` + `git commit` **trên nhánh riêng** `g18-ag03-secretpaths`. Việc này **không**
vi phạm chốt nào: **không `push`, không `deploy`, không `tunnel`**, và `main` **không bị đụng tới**.
Bản ghi đáng giữ lại ở đây là: **một làn giao tệp mới mà không commit thì cổng toàn dự án ĐỎ** —
người sau gặp lại đúng dòng `FAIL: test_a1_cay_sach_va_head` này nên đọc mục này trước khi đi tìm
lỗi trong mã.

---

## 9. GHI CHÚ GỘP NHÁNH — `app/http_jt.py` CÓ HAI LÀN CÙNG GHI

**AG-02 cũng ghi `app/http_jt.py` và `app/thu/thu_http_jt.py`.** Hai làn ở hai worktree riêng nên
không ghi đè nhau về mặt vật lý, nhưng **AG-00 sẽ phải gộp**. Vì vậy làn này giữ thay đổi **nhỏ và
tập trung vào che bí mật**:

* **`app/thu/thu_http_jt.py`: KHÔNG SỬA MỘT DÒNG NÀO.** Toàn bộ ca mới nằm ở tệp **mới**
  `app/thu/thu_g18_bi_mat.py`. Nhờ vậy, tệp của AG-02 không có xung đột nào từ phía này.
  (`chay_tat_ca.sh` **tự dò** `app/thu/thu_*.py`, nên tệp mới **tự vào** cổng — không phải sửa
  danh sách.)
* **`app/http_jt.py`**: thay đổi **cộng thêm** (`git diff --stat`: **275 dòng thêm / 16 dòng sửa**),
  không đổi chữ ký hàm nào mà AG-02 đang dùng:
  * `_gia_tri_can_che(headers, than_gui, url=None)` — **giữ nguyên chữ ký và ngữ nghĩa**, nay là vỏ
    mỏng gọi `_mo_rong_bien_the(_gia_tri_ta_gui(...))`. `thu_http_jt.j2` gọi thẳng hàm này và vẫn
    XANH (đã đo: 57/57).
  * `mo_ta_yeu_cau(url, headers, than)` — **giữ nguyên chữ ký 3 tham số** (ca tự kiểm `test_g3`
    thay thế nó bằng một `lambda` 3 tham số, nên arity **không được đổi**).
  * Hàm mới: `_gia_tri_ta_gui`, `_gia_tri_tu_duong_dan`, `_gia_tri_bi_mat_trong_json`,
    `_gia_tri_bi_mat_trong_vb`, `_gia_tri_bi_mat_tu_phan_hoi`, `_la_doan_bi_mat`, `_doan_chua_bi_mat`,
    `_duong_dan_da_che`. Hằng mới: `TRUONG_CREDENTIAL_PHAN_HOI`, `DOAN_DUONG_DAN_DAI_TOI_THIEU`,
    `DOAN_DUONG_DAN_KHAC_NHAU_TOI_THIEU`.
* `tach_url()` đổi **một thông điệp lỗi** (bỏ giá trị đường dẫn khỏi câu chữ, giữ nguyên loại lỗi,
  `ket_cuc` và thuộc tính `host`).
