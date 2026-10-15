# G18 — ĐA TIẾN TRÌNH (AG-02): lớp nào dùng chung được qua tiến trình, lớp nào **KHÔNG**

> **Một dòng phán quyết.** Đo bằng **tiến trình thật** (`subprocess`, không phải luồng):
> **trần tần suất `gioi_han` PHẦN A nhân đúng theo số bản** — N = 1 · 2 · 4 · 8 cho
> **20 · 40 · 80 · 160** lượt cho qua (khai báo 20), cả khi N bản **dùng chung một CSDL** và cả khi
> **chạy đồng thời thật** (B-G11-10 **tái lập**, nay có số của cả 4 mức N).
> **Lớp HTTP `app/http_jt.py` thì AN TOÀN**: nó **không có trạng thái dùng chung nào** — 0 dấu hiệu
> ghi trạng thái mức mô-đun, 0 ghi tệp, mỗi lượt một kết nối TCP tự mở tự đóng, và 4 tiến trình thật
> không lẫn dữ liệu của nhau. **`csdl.khoa_ghi` (RLock) KHÔNG phủ tiến trình**: đọc-sửa-ghi ngây thơ
> 4 tiến trình × 25 lượt = 100 lượt tăng mà bộ đếm chỉ lên **25** — mất **75** lượt, **im lặng**
> (0 ngoại lệ).

* **Nền**: `integration/g17` @ **`7b741c8`** (đúng mốc G18 chỉ định) · nhánh `g18-ag02-multiprocess`
* **Bộ đo**: `app/thu/thu_g18_multiprocess.py` (**mới**) · **26 ca · 0 hỏng · 0 bỏ qua · exit 0**
* **Máy đo**: macOS 15 · Python 3.9.6 · SQLite 3.51.0 · MỘT máy · loopback · CSDL **tạm**

---

## 0. CÁI GÌ ĐƯỢC ĐÓNG Ở ĐÂY

Lượt nghiệm thu G17 ghi hai mục **CHƯA ĐO** (AG-01):

| Nguồn | Nguyên văn | Nay |
|---|---|---|
| `docs/G17_SECURITY_ISOLATION.md` §9.2 | *"Nhiều tiến trình: trần tần suất sống trong bộ nhớ MỘT tiến trình; `csdl.khoa_ghi` là RLock của Python. Lượt này chạy MỘT tiến trình ⇒ KHÔNG đo được tranh chấp liên tiến trình"* | **ĐÃ ĐO** — §2 và §4 dưới đây |
| `docs/G17_TRANSPORT.md` §8.3 | *"Đa luồng được đo trong MỘT tiến trình, trên MỘT máy. Chưa đo nhiều tiến trình"* | **ĐÃ ĐO** — §3 dưới đây |

Và **B-G11-10** (`docs/G13_G15_ACCEPTANCE.md`, đo bằng hai máy chủ AG-04) nay được **đo lại độc lập**
bằng `subprocess` với **bốn mức N**, không mượn lại bộ đo cũ.

**KHÔNG làm lại** những mục đã đạt: ba cổng G16-A vẫn nguyên trạng; hồi quy G17 (1460 ca · 38 bộ ·
exit 0) **không bị chạm** — xem §6.

---

## 1. LỆNH THẬT · MÃ THOÁT THẬT · SỐ CA · SỐ BỎ QUA

Mọi lệnh dưới đây chạy tại gốc cây làm việc. **Mã thoát in TRƯỚC mọi pipe** (`; echo "EXIT=$?"`),
không lấy mã thoát của `tail`/`grep`.

```sh
export GIT_CONFIG_COUNT=0            # N-G17-00: biến GIT_CONFIG_* hỏng thì MỌI lệnh git hỏng
git rev-parse HEAD; echo "EXIT=$?"
#   7b741c88b3b280d65f80b5e11301f17ebd767b26
#   EXIT=0
```

```sh
python3 app/thu/thu_g18_multiprocess.py > /tmp/g18.log 2>&1; echo "EXIT=$?"
#   EXIT=0
grep -E "ca ĐẠT:|ca — " /tmp/g18.log; echo "EXIT=$?"
#     ca ĐẠT: 26 · HỎNG: 0 · BỎ QUA: 0 · KHÔNG KẾT LUẬN: 0 · TỔNG: 26
#     26 ca — ĐẠT
#   EXIT=0
```

**Số ca: 26 · Số bỏ qua: 0 · Số hỏng: 0 · exit 0.** Thời gian thật: **~30 giây** (mỗi lượt đo dựng
nền tạm riêng rồi dọn sạch).

Băm tệp (bằng chứng "đúng bản đã đo"):

```sh
shasum -a 256 app/thu/thu_g18_multiprocess.py app/thu/stub_jt.py app/http_jt.py; echo "EXIT=$?"
```

Hồi quy toàn bộ (bộ chạy tự dò `app/thu/thu_*.py` nên bộ mới **tự vào**, không phải sửa danh sách):

```sh
sh app/thu/chay_tat_ca.sh; echo "EXIT=$?"          # số ở §6
```

---

## 2. B-G11-10 — TRẦN TẦN SUẤT QUA **N TIẾN TRÌNH MÁY CHỦ THẬT**

### 2.1 Cách đo (và hai cái bẫy đã sập vào)

* **N tiến trình thật**: N bản `app/server.py` chạy bằng `subprocess`, mỗi bản một PID, **cùng một
  `VIP_HUB_DATA`** (⇒ **cùng một tệp `hub.db`**), cùng IP `127.0.0.1`, mỗi bản một cổng do hệ cấp.
* **Luật đang áp** đọc từ **chính máy chủ**, không chép từ tài liệu: header `X-RateLimit-Limit`
  trên lượt **429** ⇒ **20**; thân 429 tự khai `chieu = "ip"`, `Retry-After = 300`.
  (`app/gioi_han.py`: `"auth.dang_nhap": (Luat("ip", 20, 300), Luat("dinh_danh", 12, 300, chan_giay=900))`.)
* **Tên đăng nhập KHÁC NHAU mỗi lượt** ⇒ chỉ chiều `ip` cộng; chiều `dinh_danh` mỗi bucket chỉ 1 lượt
  nên không bao giờ chặn. Đăng nhập sai 5 lần cho **cùng** một tài khoản sẽ khoá tạm tài khoản đó.
* **Hai cách bắn**: (a) **vòng tròn tuần tự** — mỗi vòng một lượt cho mỗi bản còn sống, TẤT ĐỊNH;
  (b) **đồng thời thật** — `N × (20+5)` yêu cầu bắn cùng lúc bằng luồng ở phía client, trên **bộ máy
  chủ mới** (bộ cũ đã tiêu hết ngân sách).
* **Đối chứng đồng thời** ở hai phía: phía client (số lượt đang bay chồng nhau, và bao nhiêu **bản**
  khác nhau cùng bay) + phía máy chủ (log JSON của chính các tiến trình: bao nhiêu **pid khác nhau**
  phục vụ trong **cùng một giây**).

> **BẪY 1 — đọc trần bằng máy chủ đang đo.** Header `X-RateLimit-Limit` **chỉ có trên lượt 429**;
> muốn đọc phải để máy chủ từ chối một lượt, mà mỗi lượt đều tiêu một suất. Bản đầu của bộ đo đọc
> trần bằng một lượt gọi vào **chính bản sắp đo** ⇒ N=1 ra **19** thay vì 20 (HỎNG GIẢ). Nay trần
> đọc trên một **máy chủ dùng một lần rồi tắt**.
>
> **BẪY 2 — đo nhầm chiều.** Bản đầu dùng **cùng một tên đăng nhập** cho mọi lượt của máy chủ dò
> ⇒ chiều `dinh_danh` (trần **12**, `chan_giay=900`) chặn trước chiều `ip`, và bộ đo đọc ra trần
> **12**. Số vòng bắn bị chặn trần theo con số sai đó ⇒ mọi bản "cho qua" đúng bằng **số vòng** mà
> **không hề bị chặn** — tức *"không thấy chặn"* bị đọc thành *"trần rộng"*. Đây đúng khuôn **HỎNG
> GIẢ N-05** và là lý do bộ đo nay **bắt buộc mỗi bản phải kết thúc bằng một lượt 429** mới tính ĐẠT.

### 2.2 Số đo

| N | trần khai báo | **tuần tự** (mỗi bản cho qua) | **tổng** | **đồng thời thật** (mỗi bản) | **tổng** | bản cùng bay | pid khác nhau trong 1 giây |
|---|---|---|---|---|---|---|---|
| 1 | 20 | `[20]` | **20** | `[20]` | **20** | 1 | 1 |
| 2 | 20 | `[20, 20]` | **40** | `[20, 20]` | **40** | 2 | 2 |
| 4 | 20 | `[20, 20, 20, 20]` | **80** | `[20, 20, 20, 20]` | **80** | 4 | 4 |
| 8 | 20 | `[20]×8` | **160** | `[20]×8` | **160** | 8 | 8 |

* **Mỗi bản có ngân sách RIÊNG đúng bằng khai báo** ⇒ trần thực **nhân theo số bản**, KHÔNG phải
  chia sẻ một ngân sách 20 cho cả cụm.
* **Dùng chung CSDL không cứu được**: cả 4 mức N đều chạy trên **một tệp `hub.db`** (N tiến trình
  cùng `VIP_HUB_DATA`).
* **Biến thể "mỗi bản một CSDL riêng" (N=4)**: `[20, 20, 20, 20]` ⇒ tổng **80**. Việc nhân **không
  phải** vì CSDL tách rời — thủ phạm là **bộ đếm trong bộ nhớ tiến trình** (`gioi_han._lan`).
* **Đồng thời là THẬT, không phải nối đuôi**: N=8 có lúc **161 lượt đang bay** thuộc **8 bản khác
  nhau**, và log JSON của chính 8 tiến trình máy chủ cho thấy **8 pid khác nhau** phục vụ trong
  **cùng một giây**.

**ĐỐI CHỨNG ÂM (bắt buộc, và nó ĐẠT):** N=1 ⇒ đo được **20 = khai báo**, và chính máy chủ tự khai
chiều chặn `ip`, `Retry-After = 300`, `X-RateLimit-Limit = 20`. Nếu ca này lệch thì mọi kết luận
"nhân theo số bản" ở trên vô nghĩa — nó là phép kiểm **bộ đếm lượt của bộ đo**, không phải của
`gioi_han`.

**HỆ QUẢ VẬN HÀNH.** Chạy N bản sau một bộ cân bằng tải thì trần chống dò mật khẩu / chống spam
**trở thành N × khai báo**: kẻ tấn công có N lần ngân sách cho mỗi IP. Trần **vẫn** chặn lạm dụng
tự động ở một bản, nhưng **không còn là** "20 lượt/300 giây" như văn bản khai. Cửa lách thứ hai,
độc lập với số tiến trình: khởi động lại là **mất sạch** bộ đếm (đã ghi trong `gioi_han.py`).

---

## 3. LỚP HTTP `app/http_jt.py` — CÓ TRẠNG THÁI DÙNG CHUNG NÀO KHÔNG?

Hai đường đo **độc lập**: quét **cấu trúc** (AST) và đo **hành vi** bằng tiến trình thật.

### 3.1 Quét cấu trúc (AST) — `P3a`

* `http_jt` có **20 tên mức mô-đun**; trong đó **2 là dict HẰNG số cấu hình**
  (`CHO_PHEP_MOI_TRUONG` dòng 54, `LY_DO_CHAN_MOI_TRUONG` dòng 55) — dict, nhưng **không ai ghi**.
* **0 dấu hiệu GHI trạng thái mức mô-đun**: không `global`, không `X[…] = …`, không
  `append/update/pop/…`, không `del X[…]`; **0 ghi tệp**: không `open(…, "w"/"a"/"x"/"+")`, không
  `tempfile`, không `shutil`, không `write_text`.
* Tiêu chí quét là **"có ai GHI vào tên mức mô-đun không"**, không phải "có biến toàn cục không":
  chỉ đếm biến toàn cục thì một hằng số cũng bị tố (HỎNG GIẢ), còn chỉ tìm `global` thì
  `_KHO[k] = v` (đột biến **không cần** `global`) lại lọt. Xem §5 — bản đột biến ở đó bị bắt **đúng
  bằng** phép quét này.

### 3.2 Đo hành vi — 4 tiến trình THẬT, stub `127.0.0.1` cổng 0 — `P3b`–`P3f`

| Ca | Đo gì | Kết quả |
|---|---|---|
| `P3b` | 4 **tiến trình** (pid khác nhau), nối đuôi, cùng URL | mỗi tiến trình nhận **đúng** `txlogisticId` + `apiAccount` của mình · **0** lượt nhận dấu vết của tiến trình khác · mã thoát các con `[0,0,0,0]` |
| `P3c` | bao nhiêu **kết nối TCP** cho 4 lượt gọi | **+4** kết nối, **+4** yêu cầu — **một kết nối cho một lượt, KHÔNG pool** (đo từ **tiến trình stub**, không phải client tự khai) |
| `P3d` | **đối chứng dương** cho máy đếm kết nối | 3 yêu cầu **trên MỘT kết nối** ⇒ kết nối **+1**, yêu cầu **+3** ⇒ máy đếm đếm **kết nối**, không đếm yêu cầu |
| `P3e` | 4 tiến trình × 4 luồng, song song | stub báo **cao nhất 16 yêu cầu cùng lúc** · 16 kết nối cho 16 lượt · **0,39 s** (nếu tuần tự hoá hết phải ≥ 4,8 s) |
| `P3f` | **đối chứng âm** cho "song song" | cùng stub, 4 tiến trình **nối đuôi** ⇒ cao nhất **= 1** (nên con số 16 ở `P3e` không phải hằng số) |

**Trả lời trực tiếp câu hỏi đặt ra** — bốn thứ được hỏi, từng thứ một:

| Thứ được hỏi | `http_jt` có không? | Bằng chứng |
|---|---|---|
| **connection** dùng chung / pool | **KHÔNG** | `P3c`: 4 lượt gọi ⇒ stub nhận **+4** kết nối · `P3d` (đối chứng dương): 3 yêu cầu trên MỘT kết nối ⇒ **+1** kết nối, **+3** yêu cầu ⇒ máy đếm đếm **kết nối** thật · mã: `_mo_ket_noi`/`_dong` mỗi lượt một kết nối |
| **counter** (bộ đếm toàn cục) | **KHÔNG** | `P3a`: 0 dấu hiệu **GHI** vào tên mức mô-đun (không `global`, không ghi chỉ số, không `append/update/pop`) |
| **cache** (đệm phản hồi) | **KHÔNG** | `P3b`: 4 tiến trình **cùng URL**, mỗi tiến trình nhận **đúng** dấu vết của mình, **0** lượt nhận của người khác · `P4b`: bản đột biến **có** đệm theo URL thì bị bắt (3/4 lượt lẫn) ⇒ phép đo **có răng** |
| **tệp tạm** | **KHÔNG** | `P3a`: 0 lần `open(…, "w"/"a"/"x"/"+")`, 0 `tempfile`, 0 `shutil`, 0 `write_text` · `P4a`: bản đột biến ghi tệp dùng chung thì bị quét bắt (`mo-tep-de-ghi`) |

**Kết luận**: lớp HTTP **không** có connection dùng chung, **không** có bộ đếm, **không** có cache,
**không** có tệp tạm. Mỗi lượt gọi tự mở một kết nối và tự đóng, nên **không có gì để dùng chung —
và cũng không có gì để hỏng** khi chạy nhiều tiến trình.

**Cái NẰM NGOÀI**: trần đồng thời của lớp này là trần **file descriptor của TỪNG tiến trình**
(không pool). Chạy N bản thì trần đó **nhân lên**, không phải một trần chung bị chia.
`docs/G17_TRANSPORT.md` §8.4 đã ghi điều này cho MỘT tiến trình; ở đây chỉ xác nhận nó **không**
trở thành trạng thái dùng chung khi có N bản.

---

## 4. TẦNG CSDL — `csdl.khoa_ghi` (RLock) **KHÔNG PHỦ TIẾN TRÌNH**

`app/csdl.py` tự ghi: *"Giữ `khoa_ghi` suốt khối: trong MỘT tiến trình thì mỗi lúc chỉ một người
ghi. **KHÔNG phủ nhiều tiến trình** — chỗ đó phải đo riêng"*. Đây là phép đo riêng đó: **4 tiến
trình thật × 25 lượt** đọc-sửa-ghi trên **một CSDL tạm** (WAL), cùng một hàng `_g18_dem`, xuất
phát đồng thời qua hàng rào thời gian; khe hở giữa `SELECT` và `UPDATE` được nới **2 ms** (có chủ
ý) để tranh chấp lộ ra **tất định**.

| Cách viết | Kỳ vọng | Bộ đếm thật | Mất | Ngoại lệ |
|---|---|---|---|---|
| **ngây thơ**: `SELECT` → `UPDATE`, **không** giao dịch | 100 | **25** | **75** | **0** |
| bọc `csdl.giao_dich()` (`BEGIN IMMEDIATE`) | 100 | **100** | 0 | 0 |
| một câu nguyên tử `UPDATE … SET dem = dem + 1` | 100 | **100** | 0 | 0 |

* **Mất cập nhật là hỏng IM LẶNG**: 300 lượt ghi, **0 ngoại lệ**, không log, không dấu vết.
* `khoa_ghi` là **RLock** nên nó chỉ giữ cho **kết nối của một tiến trình** không bị hai luồng dùng
  cùng lúc; nó **không** tạo ra tính nguyên tử cho một chuỗi đọc-rồi-ghi, và **không** vươn qua
  tiến trình. Thứ phủ được tiến trình là **khoá ghi của SQLite ở tầng TỆP** (`BEGIN IMMEDIATE`),
  hoặc một câu SQL nguyên tử.
* **Cách chữa đã có sẵn trong nhà**: `gioi_han` PHẦN B (hạn mức nhập) đếm trong CSDL bằng
  `UPDATE … WHERE cot + ? <= trần` — xem §5.2, nó **giữ nguyên trần** qua 4 tiến trình.

---

## 4B. BẢNG KẾT LUẬN — LỚP NÀO AN TOÀN QUA TIẾN TRÌNH

| Lớp | Trạng thái nằm ở đâu | Qua nhiều tiến trình? | Ca đo |
|---|---|---|---|
| `app/http_jt.py` (lớp HTTP) | **không có trạng thái nào** (không pool, không đệm, không ghi tệp) | **AN TOÀN** — không có gì để dùng chung; mỗi lượt một kết nối, tự mở tự đóng | `P3a`–`P3f`, `P4a`/`P4b` |
| `gioi_han` **PHẦN A** (trần tần suất: `auth.*`, `webhook.*`, `khoa.xoay`, …) | bộ đếm trong **BỘ NHỚ tiến trình** + `threading.Lock` | **KHÔNG AN TOÀN** — trần thực = khai báo **× số bản** | `P1.*` (20·40·80·160) |
| `gioi_han` **PHẦN B** (hạn mức nhập file) | bảng CSDL + `UPDATE … WHERE cot + ? <= trần` (nguyên tử) | **AN TOÀN** — trần giữ nguyên, không nhân | `P2b` (5/16 lượt đặt được, trần 5) |
| `csdl.khoa_ghi` (RLock) + đọc-sửa-ghi ngây thơ | RLock chỉ phủ **MỘT** tiến trình; SQLite khoá ở tầng **TỆP** | **KHÔNG** — mất cập nhật, **im lặng** | `P5a` (25/100) |
| `csdl.giao_dich()` (`BEGIN IMMEDIATE`) / câu lệnh nguyên tử | khoá ghi của SQLite ở tầng **TỆP** | **AN TOÀN** | `P5b`, `P5c` (100/100) |

**Hệ quả vận hành, đọc kỹ trước khi chạy nhiều bản:**

1. **Trần chống dò mật khẩu nhân theo số bản.** Một kẻ tấn công đi qua bộ cân bằng tải có **N lần**
   ngân sách cho mỗi IP. Trần vẫn chặn lạm dụng tự động ở **một** bản, nhưng **không còn** là
   "20 lượt/300 giây" như khai. Cộng thêm cửa lách **khởi động lại là mất sạch bộ đếm**.
2. **Cách chữa đã có sẵn trong nhà**: khuôn của `gioi_han` PHẦN B — bộ đếm trong CSDL với
   `UPDATE … WHERE … + ? <= trần`. Đo được ở `P2b` là nó **giữ nguyên trần** qua 4 tiến trình.
   Việc chuyển PHẦN A sang khuôn đó là **thay đổi mã của AG-01** (không thuộc làn này, xem §7).
3. **Với SQLite**: mọi đọc-sửa-ghi phải nằm trong `csdl.giao_dich()` hoặc là **một câu nguyên tử**.
   **Đừng tin `khoa_ghi`**: nó chỉ giữ cho kết nối của MỘT tiến trình không bị hai luồng dùng cùng
   lúc — nó không tạo tính nguyên tử cho chuỗi đọc-rồi-ghi, và không vươn qua tiến trình.
4. **Lớp HTTP không cần sửa gì** cho nhiều tiến trình; trần đồng thời của nó là trần **fd của từng
   tiến trình** (nhân lên theo số bản, không phải chia).
5. **Trước khi chạy N bản trên một CSDL MỚI**: nạp trước bằng MỘT tiến trình (`migrate.py` +
   `khoi_tao.py`) rồi mới bật N bản — xem §8.4.

---

## 5. TỰ KIỂM BỘ ĐO — mỗi khẳng định đều có ĐỐI CHỨNG

Luật của dự án (§12.1 luật 3): một ca xanh chỉ có nghĩa nếu có **ca tự kiểm bộ đo** làm nó đỏ được.

### 5.1 Đột biến hàm đếm — `P2a`

Trên **chính dữ liệu thật** của P1 (N=8, 168 lượt đã ghi lại): bộ đếm thật = **160**, bộ đếm
đột biến (đếm cả lượt 429) = **168**. Hai số **khác nhau** ⇒ phép đếm ở P1 phân biệt được
"cho qua" với "bị chặn". Nếu chúng bằng nhau thì mọi con số ở §2 vô nghĩa.

### 5.2 Đối chứng dương — trần **CÓ dùng chung** thì **KHÔNG** nhân — `P2b`

Cùng bộ đếm-lượt, nhưng đo một trần **đếm trong CSDL** (`gioi_han.dat_truoc_don_nhap`, khuôn
`UPDATE … WHERE … + ? <= trần`): **4 tiến trình × 4 lượt = 16 lượt xin suất**, trần ép về **5**
(`VIP_HUB_TRAN_DON_NHAP_MIN=5`, `VIP_HUB_BOI_SO_DON_NHAP=1`) ⇒ **đặt được 5, bị chặn 11**.

⇒ Kết quả **NGƯỢC** với P1 trên **cùng một bộ đo**. Vì vậy "nhân theo số bản" ở §2 là tính chất
của **bộ đếm trong bộ nhớ**, không phải của phép đo. Đây cũng là **cách chữa** đã có sẵn trong nhà
cho PHẦN A.

### 5.3 Đột biến mô-đun — bộ dò ở §3 **PHẢI** bắt được trạng thái dùng chung — `P4a`/`P4b`

Sinh trong **thư mục tạm** (KHÔNG nằm trong mã sản phẩm) một bản đột biến của lớp HTTP có **đệm
phản hồi theo URL** — lỗi thật và hay gặp: đệm ở (a) dict **toàn cục** và (b) **tệp dùng chung**
giữa mọi tiến trình, và **quên thân yêu cầu** trong khoá đệm.

* `P4a` — **quét cấu trúc** bắt được: `['ghi-chi-so', 'goi-update', 'mo-tep-de-ghi']`.
  Cùng phép quét đó trả **"(không có)"** cho `http_jt` ⇒ phép quét ở `P3a` **không phải** một phép
  quét luôn-rỗng.
* `P4b` — **đo hành vi** bắt được: 4 tiến trình nối đuôi, **3/4 lượt nhận dấu vết của tiến trình
  KHÁC** (tiến trình thứ hai trở đi nhận thân trả lời của tiến trình đầu).

⇒ Bộ dò ở §3 **có răng**: nếu `http_jt` có đệm dùng chung, `P3b` sẽ đỏ. Nó xanh vì **không có**,
không phải vì bộ đo mù.

---

## 6. HỒI QUY — KHÔNG CHẠM CÁI ĐÃ ĐẠT

`app/thu/stub_jt.py` **có** được sửa (thêm đường điều khiển chỉ-loopback + chế độ chạy như tiến
trình riêng, xem §7), nên phải chứng minh hai bộ thử đang dùng nó không bị chạm:

```sh
python3 app/thu/thu_http_jt.py;    echo "EXIT=$?"     # exit 0 — Ran 57 tests — OK
python3 app/thu/thu_adapter_jt.py; echo "EXIT=$?"     # exit 0 — 84 ca · hỏng 0 · bỏ qua 0
python3 app/thu/thu_hop_dong_jt.py;echo "EXIT=$?"     # exit 0 — 84 ca · hỏng 0 · bỏ qua 0
python3 app/thu/thu_qa_jt.py;      echo "EXIT=$?"     # exit 0 — 22 ca · hỏng 0 · bỏ qua 0
```

Toàn bộ bộ chạy hồi quy (tự dò bộ thử mới, không sửa danh sách):

```sh
sh app/thu/chay_tat_ca.sh; echo "EXIT=$?"             # exit 0
#   python: 1486 ca · 39 bộ chạy thật   (+ 26 ca của bộ G18 này so với mốc 1460/38)
#   bộ hỏng: KHÔNG
```

> Con số ở trên lấy từ **lượt chạy đóng băng** — xem §8 để biết mốc băm chính xác của cây lúc chạy.

---

## 7. TỆP ĐÃ ĐỔI

| Tệp | Loại | Vì sao |
|---|---|---|
| `app/thu/thu_g18_multiprocess.py` | **MỚI** | Bộ đo P0–P6: 26 ca, tiến trình thật, tự kiểm bộ đo |
| `docs/G18_MULTIPROCESS.md` | **MỚI** | Tài liệu này |
| `app/thu/stub_jt.py` | sửa **thêm** | (1) đường điều khiển `GET /__stub/thong-ke` (chỉ loopback) để **tiến trình khác** đọc được số đo `so_ket_noi`/`so_yeu_cau`/`cao_nhat_dang_xu_ly` mà không làm bẩn chính con số đang đọc; (2) `python3 app/thu/stub_jt.py --che-do … --ghi-cong <tệp>` để stub sống trong **tiến trình riêng**, vẫn bind `127.0.0.1` **cổng 0** và ghi cổng thật ra tệp. Không đổi hành vi nào của các chế độ cũ; 247 ca của 4 bộ thử dùng stub đều còn xanh (§6) |
| `app/http_jt.py` | sửa **chú thích** | Ghi kết quả đo nhiều tiến trình vào đầu tệp (mục "NHIỀU TIẾN TRÌNH"), thay cho dòng *"CHƯA ĐO nhiều tiến trình"* ở `G17_TRANSPORT.md` §8.3. **Không đổi một dòng mã nào** |

**KHÔNG sửa**: `app/gioi_han.py`, `app/csdl.py`, `app/server.py` — việc chuyển PHẦN A sang bộ đếm
dùng chung là **thay đổi mã của AG-01**, không thuộc làn này. Tài liệu này chỉ **đo** và **chỉ chỗ**.

---

## 8. CÁI NẰM NGOÀI PHẠM VI — **CHƯA ĐO**, ĐỪNG ĐỌC THÀNH ĐÃ ĐO

1. **Nhiều MÁY / sau bộ cân bằng tải thật.** Mọi số ở đây là **một máy**, loopback, `127.0.0.1`.
   Cùng một IP qua NAT, IPv6, sticky session, `X-Forwarded-For` của proxy thật — **chưa đo**.
   (`gioi_han.PROXY_TIN_CAY` mặc định RỖNG nên mọi phép đo ở đây đi đúng đường "IP thật".)
2. **Tải lớn / thời gian dài.** Bộ đo bắn tối đa **8 tiến trình × 25 yêu cầu**; chưa đo N=16/32,
   chưa đo dưới tải liên tục, chưa đo khi bộ đếm chạm trần dọn `TOI_DA_KHOA`.
3. **PostgreSQL — D-8, KHÔNG đụng.** Cụm `:5432` đang giữ dữ liệu dự án khác
   (`vip_customs`, `vip_customs_g16`, `vip_customs_test`); **không một kết nối nào** tới đó trong
   lượt này. Mọi kết luận ở đây là **SQLite**. (Số của PostgreSQL đã có ở `docs/G17_POSTGRES.md`.)
4. **Đua đặt WAL khi mở một CSDL MỚI bằng nhiều tiến trình** — đã ghi trong `csdl._dat_wal`
   (8 tiến trình mở CSDL mới ⇒ có tiến trình chết ở `PRAGMA journal_mode=WAL`). Bộ đo ở đây
   **nạp trước** bằng một tiến trình (`migrate.py` + `khoi_tao.py`) rồi mới chạy N bản, nên phép đo
   **không** lẫn cuộc đua đó. Đây là **cố ý**, không phải bỏ sót — và nó **không** được đo lại ở đây.
5. **Hãng thật / sandbox J&T.** `V-G09-01` + `V-13906-05` **CHƯA CẤP**. Mọi phép đo lớp HTTP đi tới
   **stub cục bộ `127.0.0.1` cổng 0**; **không một byte ra mạng**. TLS, chứng thư, SNI, `Retry-After`
   thật — **chưa đo**.
6. **Mã trạng thái 110 (D-4)** — không đoán, không suy ra; lượt này không chạm tới.
7. **`CHO_PHEP_LIVE`** — không mở, không sửa `app/cau_hinh.py`.
8. **Mã nguồn của PHẦN A** — bộ đo **không** sửa `gioi_han.py`; đề xuất chữa (bộ đếm trong CSDL
   theo khuôn PHẦN B) là **đề xuất**, chưa được cài.
9. **Giao diện / DOM / Chromium** — không chạm (tầng 3 có bộ chạy riêng).

---

## 9. CHỐT AN TOÀN CỦA CHÍNH BỘ ĐO

* Mọi nền dữ liệu là `tempfile.mkdtemp(prefix="vh-g18-…")`; bộ đo **từ chối chạy** nếu nền không
  nằm trong thư mục tạm của hệ hoặc trùng `app/du-lieu`.
* **Mỗi tiến trình con tự chốt lại lần nữa**: đọc `cau_hinh.DUONG_DAN_CSDL`, nếu không nằm trong
  thư mục tạm thì in `TỪ CHỐI` và thoát **mã 9**.
* Tắt tiến trình con **theo ĐÚNG PID** (`terminate` → `kill`), **không** `pkill`/`killall`.
* Dọn sạch nền tạm trong `finally`, kể cả khi có ca hỏng.
* Không đặt `CHO_PHEP_LIVE`, không chạm `.env`, không in bí mật (mọi chuỗi trong bộ đo là chuỗi GIẢ).
