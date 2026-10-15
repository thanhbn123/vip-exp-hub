# G18 — MÁY CHỦ HTTP THẬT DƯỚI TẢI (làn AG-04)

**Việc:** đóng lỗ hổng **`V-13914(b)`** — *"máy chủ HTTP thật **dưới tải**"* — ghi ở
`docs/BAN_GIAO.md` §6.1. **Nền:** `integration/g17` @ `7b741c8`. **Không** dùng `main`.

| | |
|---|---|
| Mốc đo (HEAD lúc chạy) | `7b741c88b3b280d65f80b5e11301f17ebd767b26` |
| Máy | Darwin arm64 · Python **3.9.6** · SQLite 3.51.0 · `os.cpu_count()=10` |
| Tệp **mới** của lượt này | `app/thu/thu_g18_maysrv.py` · `trien_khai/g18/{chot_an_toan,harness_tai,tiem_loi}.py` · `trien_khai/g18/chay_harness.sh` · `trien_khai/g18/README.md` · tệp này |
| Tệp **KHÔNG** sửa | `app/webhook.py` (đã chốt ở G17) · `app/server.py` · `app/gioi_han.py` · `app/cau_hinh.py` · mọi tệp khác |
| Mã thoát của lượt chạy đầy đủ | `sh trien_khai/g18/chay_harness.sh` → **0** (5/5 lượt) |
| Số ca | harness: **18/20 đạt · 0 hỏng · 0 BLOCKED · 2 bỏ qua** (5/5 lượt y hệt) · bộ hồi quy mới: **17 ca đạt** |
| Số ca **bỏ qua** | **2**, và cả hai nói thẳng ra một chỗ **không đo được** (xem §7) |

---

## 1. Lỗ hổng: đo MỘT ĐƯỜNG, kết luận về ĐƯỜNG KHÁC

`docs/BAN_GIAO.md` §6.1 ghi thẳng: *"bàn đo hiện gọi thẳng hàm, không qua `ThreadingHTTPServer`"*.
Hệ quả không nhỏ: mọi con số về **đồng thời**, về **hạn chế tốc độ**, về **khoá** đều đo trên một
đường **khác** với đường chạy thật. Ba câu hỏi của lượt này, và câu trả lời đo được:

1. Bao nhiêu **yêu cầu/giây**, bao nhiêu **lỗi**, bao nhiêu **5xx**? → §4
2. **Hạn chế tốc độ** (`app/gioi_han.py`) còn đúng khi đi qua HTTP thật không? → §5 (đúng, và
   khớp với đường gọi hàm)
3. **Nhiều tiến trình máy chủ** ⇒ trần thực có **nhân** theo số bản không (`B-G11-10`)? → §6
   (**có: 2,0×**)

---

## 2. Cách chạy lại

```bash
sh trien_khai/g18/chay_harness.sh              # đầy đủ: 4 tầng tự kiểm + đo + tự tắt theo PID
python3 trien_khai/g18/chot_an_toan.py --tu-kiem   # 14 cấu hình chốt an toàn
python3 trien_khai/g18/harness_tai.py  --tu-kiem   # bộ đo tải + bộ phán quyết trần
python3 trien_khai/g18/tiem_loi.py                 # chứng minh ngược (tiêm lỗi)
python3 app/thu/thu_g18_maysrv.py                  # bộ hồi quy: 17 ca, ~6 giây
```

| Lệnh | Mã thoát | Số ca |
|---|---|---|
| `chot_an_toan.py --tu-kiem` | **0** | 14/14 |
| `harness_tai.py --tu-kiem` | **0** | 8/8 |
| `tiem_loi.py` | **0** | 4/4 phép tiêm cho kết quả mong đợi |
| `harness_tai.py` (chạy thật) | **0** | 18/20 đạt · 0 hỏng · 2 bỏ qua |
| `thu_g18_maysrv.py` | **0** | `Ran 17 tests` · `OK` |

Mọi lượt đo đi qua **loopback, cổng 0** (hệ điều hành cấp): máy chủ bind `127.0.0.1`, CSDL là
**SQLite trong thư mục tạm**, adapter hãng ở **MOCK**. **Không** gọi hãng kể cả sandbox
(`V-G09-01` + `V-13906-05` CHƯA CẤP), **không** tunnel, **không** deploy, **không** mở cổng.
Tắt máy chủ theo **ĐÚNG PID**; `pkill`/`killall` bị **canh bằng máy** (chốt `G18-11`).

---

## 3. Bộ đo cũng phải được đo — bốn tầng, và tầng thứ tư là tầng quyết định

Một bộ đo **không phân biệt được** máy chủ lành với máy chủ hỏng thì mọi con số nó in ra là số đo
của **chính nó**. Và một bộ tự kiểm **luôn in "đạt"** thì dòng "đạt" ấy không có nghĩa.

| Tầng | Kiểm gì | Kết quả |
|---|---|---|
| 1. Chốt an toàn | 14 cấu hình tổng hợp: 1 đủ chốt (phải ĐI QUA) + 13 hỏng, mỗi cái phải bị bắt bởi **ĐÚNG chốt** | 14/14 |
| 2. Bộ đo tải | máy chủ giả LÀNH ⇒ 0 lỗi · máy chủ giả trả 500 theo chu kỳ ⇒ **phải thấy 5xx** · máy chủ giả cắt kết nối ⇒ **phải thấy lỗi** · 0 yêu cầu ⇒ **KHÔNG được coi là lành** | 4/4 |
| 3. Bộ phán quyết trần | 1 chuỗi mã trạng thái ĐÚNG + 3 dạng SAI (không chặn · chặn rồi cho qua lại · chặn sớm hơn khai báo) | 4/4 |
| 4. **Chứng minh ngược** | **tiêm lỗi vào chính bộ đo** rồi đòi tầng 2 và tầng 3 phải **ĐỎ** | **4/4** |

Kết quả tầng 4 — đây là thứ duy nhất chứng minh ba tầng trên **ĐỎ ĐƯỢC**:

| Phép tiêm | Bộ tự kiểm |
|---|---|
| T0 — không tiêm gì (đối chứng dương) | 8/8 đạt, **0 hỏng** ✔ |
| T1 — `do_lanh` luôn trả `True` (bộ đo mù) | 7/8 · **1 HỎNG** ✔ (ca `BD4`: 0 yêu cầu) |
| T2 — `phan_quyet_tran` luôn trả ĐẠT | 5/8 · **3 HỎNG** ✔ (`T2`,`T3`,`T4`) |
| T3 — máy chủ giả không bao giờ hỏng | 6/8 · **2 HỎNG** ✔ (`BD2`,`BD3`) |

Thiếu T0 thì T1–T3 vô nghĩa (một bộ tự kiểm luôn báo hỏng cũng "bắt" được cả ba). Thiếu T1–T3 thì
dòng *"8/8 ca đạt"* là một dòng in sẵn.

---

## 4. Cửa ĐỌC và cửa GHI dưới tải

Cửa đo: **ĐỌC** `GET /api/v2/webhook/su-kien` (có phiên, có JOIN + `ORDER BY … LIMIT 200`) ·
**GHI** `POST /api/v2/webhook/nhan/{webhook_ma}` (chữ ký HMAC **ĐÚNG**, `event_id` khác nhau từng
lượt). Bộ đo **đóng vòng**, mỗi luồng một kết nối HTTP. **5 lượt chạy độc lập:**

| Lượt | Đọc · 0 dòng · 8 luồng | Đọc · 0 dòng · 1 luồng | Ghi 300 · 8 luồng | Đọc · **900 dòng** · 8 luồng |
|---|---|---|---|---|
| 1 | 1342,2 | 829,4 | 564,2 | 324,2 |
| 2 | 1438,5 | 1581,4 | 1410,3 | 288,8 |
| 3 | 1394,8 | 1290,5 | 1630,9 | 328,8 |
| 4 | 1173,3 | 1417,8 | 1908,9 | 230,2 |
| 5 | 1296,9 | 1356,5 | 2104,0 | 294,4 |
| **khoảng** | **1173 – 1439** | **829 – 1581** | **564 – 2104** | **230 – 329** |

*(đơn vị: yêu cầu/giây)*

**Lỗi kết nối = 0 và 5xx = 0 ở MỌI lượt, mọi cửa.** Số dòng `wh_su_kien` sau lượt ghi = **đúng**
số yêu cầu (300) — một máy chủ trả 202 mà không ghi được gì thì mọi phép đo tốc độ ở trên đang đo
một đường ống rỗng.

### 4.1 Con số yêu cầu/giây **KHÔNG có nghĩa** nếu bỏ số dòng của bảng

Cùng một câu truy vấn, cùng 8 luồng, chỉ khác **số dòng**: `0` → **1173–1439**, `900` →
**230–329**. Tỉ lệ **0,20–0,24×** — nghĩa là chậm đi **hơn 4 lần**. Con số "~1400 yêu cầu/giây"
đo trên bảng **rỗng** là con số đẹp nhất và vô dụng nhất. Đây là chỗ dễ trích dẫn sai nhất của cả
báo cáo, nên nó được ghi thành một **ca riêng** (`G18-03c`) và in ra **kèm số dòng**.

### 4.2 8 luồng **không** cho 8 lần

`8 luồng / 1 luồng` (bảng 0 dòng): **0,83 – 1,62×**, trung bình **1,08×**. Trên bảng 900 dòng thì
rõ hơn: xem §6.2 — **gấp đôi luồng trong một tiến trình làm CHẬM đi**.

---

## 5. Hạn chế tốc độ qua HTTP thật — và đối chiếu với đường gọi hàm

Cửa `webhook.chu_ky_sai`: **10 lượt/tài khoản/60 giây**, rồi **chặn 300 giây**. Đo **tuần tự một
luồng** qua HTTP thật (đây đồng thời là **ĐỐI CHỨNG ÂM** của cả lượt):

```
chuỗi mã HTTP = [401×10, 429, 429, 429, 429]
```

| | HTTP thật | Gọi thẳng `gioi_han.kiem` |
|---|---|---|
| Số lượt được qua trước lượt chặn đầu tiên | **10** | **10** |
| **5/5 lượt chạy** | 10 | 10 |

**Hai đường cho CÙNG một trần.** Đây là câu trả lời trực tiếp cho `V-13914(b)`: bàn đo cũ đi đường
hàm, và đường hàm **không** lệch với đường HTTP — nên các số đo trần cũ vẫn dùng được. Ca
`G18-04c` canh đúng điều này: lệch một lượt là **ĐỎ**.

Kèm theo, đo được: lượt bị chặn trả **`Retry-After: 300`**, **`X-RateLimit-Limit: 10`**,
**`X-RateLimit-Window: 60`** — bên gọi biết phải chờ bao lâu. Cổng **CHỈ XEM**
(`ghi_nhan=False`) **không** tiêu lượt (ca `b3`): nếu nó tiêu, mỗi sự kiện hợp lệ bị đếm hai lần và
trần chặt sẽ chặn hãng thật.

### 5.1 Trần của **chính cửa GHI**: `webhook.nhan` chặn ở lượt thứ **601**

Gửi **640 sự kiện có chữ ký ĐÚNG** trong một phút qua HTTP thật:

| | 5/5 lượt chạy |
|---|---|
| Nhận (202) | **600** |
| Chặn (429) | **40** |
| Lượt 429 đầu tiên ở vị trí | **600** |
| Mã khác | không có |

Trần `webhook.nhan` = `600/60s` theo tài khoản **và** `1200/60s` theo IP — và nó đếm **MỌI** lượt,
kể cả lượt có chữ ký hợp lệ. Chính chú thích trong `app/gioi_han.py` lo điều này: *"hãng thật bắn
dồn hàng loạt sự kiện sau một đợt quét kho và lượt bị chặn oan là sự kiện giao hàng bị MẤT"*.

**Đo được, không suy đoán:** quá 600 sự kiện/phút/tài khoản thì sự kiện **hợp lệ** bị trả 429 và
**không được nhận** ở lượt đó.

**Chưa đo được, và KHÔNG được suy đoán:** lượt 429 ấy có làm **mất** sự kiện vĩnh viễn hay không
phụ thuộc việc **hãng có gửi lại hay không** — mà điều đó là **câu hỏi cho J&T**, chưa có trả lời.
Đây là việc tiếp theo, không phải một kết luận.

---

## 6. Nhiều tiến trình máy chủ

### 6.1 `B-G11-10` — trần thực **NHÂN** theo số bản: **2,0×** (đo lại qua HTTP)

Hai tiến trình `app/server.py`, **cùng một CSDL tạm**, **cùng IP** `127.0.0.1`, bắn **xen kẽ** vào
cửa `webhook.chu_ky_sai` với một `webhook_ma` MỚI:

| | 5/5 lượt chạy |
|---|---|
| Một tiến trình cho qua | **10** |
| Hai tiến trình cho qua (tổng) | **20** |
| Tỉ lệ | **2,0×** |
| Chia theo tiến trình | `may-chu-1: (10 qua, 10 chặn)` · `may-chu-2: (10 qua, 10 chặn)` |

**Kết luận:** trần khai báo **10** thành trần thực **20** khi chạy hai bản. `B-G11-10` **tái hiện
được qua HTTP thật**, không chỉ qua lời khai cấu trúc.

Cơ chế được canh trong **bộ hồi quy** (ca `b6`), để nó không hỏng im lặng ở lượt sau:
(a) trần nằm trong **bộ nhớ tiến trình** — "khởi động lại" là trần **đầy lại**; (b) **không** bảng
nào trong CSDL giữ bộ đếm. Mệnh đề (b) là mệnh đề dễ bị bỏ: ai thêm một bảng đếm dùng chung mà
quên sửa ca này thì bộ hồi quy vẫn xanh trong khi con số 2× đã hết đúng.

### 6.2 Mở rộng: thêm **TIẾN TRÌNH** được, thêm **LUỒNG** thì **mất**

Ba nhánh chạy **liền nhau** (bảng 900 dòng), để điều kiện máy là như nhau:

| Nhánh | Tải mỗi tiến trình | Lượt 1 | 2 | 3 | 4 | 5 | khoảng |
|---|---|---|---|---|---|---|---|
| **A** · 4 luồng, 1 tiến trình | 4 luồng | 499,8 | 682,4 | 614,9 | 541,8 | 630,0 | 500 – 682 |
| **A2** · 8 luồng, 1 tiến trình | 8 luồng | 337,4 | 282,5 | 314,6 | 344,4 | 315,2 | 283 – 344 |
| **B** · 8 luồng, **2 tiến trình** | 4 luồng | 882,3 | 1063,7 | 990,6 | 830,8 | 1114,6 | 831 – 1115 |

| Phép so | 5 lượt | Trung bình |
|---|---|---|
| **A2 / A** — gấp đôi **LUỒNG** trong một tiến trình | **0,41 – 0,68×** | **0,55×** |
| **B / A** — thêm **TIẾN TRÌNH**, tải mỗi tiến trình **y hệt** A | **1,53 – 1,77×** | **1,65×** |

**Kết luận:** gấp đôi số luồng trong **một** tiến trình làm băng thông **giảm ~45%**; thêm một
tiến trình (với tải mỗi tiến trình **không đổi**) cho **+65%**. Vậy hướng mở rộng đúng là **thêm
tiến trình**, và **thêm luồng là đi lùi**.

**Cái KHÔNG đo được, và không được đoán:** *vì sao*. `cpu_giay()` đọc CPU bằng `ps`, và trên máy
này `ps` bị sandbox chặn (`/bin/ps: Operation not permitted`) ⇒ ca `G18-02c` là **BỎ QUA**, không
phải ĐẠT. Kết luận ở trên **chỉ** nói tới số đo (băng thông), **không** khẳng định nguyên nhân
(GIL · khoá · `sqlite3.connect` mỗi thread HTTP…). Ai cần nguyên nhân thì phải đo CPU time ở môi
trường cho phép.

### 6.3 Một quan sát, chưa đủ chặt để gọi là lỗi

`webhook.khoi_dong()` của tiến trình thứ hai chạy trên **cùng** CSDL và có câu
`UPDATE wh_su_kien SET trang_thai='moi' WHERE trang_thai='dang_xu_ly'` — tức là nó **giành lại**
mọi sự kiện mà tiến trình thứ nhất đang xử lý dở. Lượt này đếm được `dang_xu_ly` **trước = 0**,
**sau = 0**, nên **không dựng được ca** chứng minh xử lý trùng. Ghi ra ở ca `G18-06d` với phán
quyết **BỎ QUA** — **không** phải một lỗi đã chứng minh. Cần một lượt riêng.

---

## 7. Cái gì NẰM NGOÀI phạm vi (và không được coi là đã đo)

| Không đo | Vì sao |
|---|---|
| **TLS/HTTPS thật** | `V-G11-01` CHƯA CẤP. Không tunnel, không deploy. Mọi lượt là `http://` trên loopback |
| **MẠNG thật** | Mọi lượt qua **loopback**: không qua dây, không qua proxy, không qua `X-Forwarded-For`. Luật trusted-proxy của `gioi_han` **không** được chạm tới |
| **Nhiều MÁY** | Hai tiến trình nằm **cùng một máy, cùng một ổ đĩa**. "Nhiều bản" ở đây là nhiều **tiến trình**, không phải nhiều **máy chủ** |
| **Gọi hãng thật, kể cả sandbox** | `V-G09-01` + `V-13906-05` CHƯA CẤP. Adapter MOCK; mọi chữ ký do harness tự ký bằng secret trong CSDL tạm |
| **Dữ liệu lớn** | Bảng lớn nhất đo được là **900 dòng**. `B-G11-11` vẫn mở. Con số 293 yêu cầu/giây ở 900 dòng **không** suy ra được cho 10⁶ dòng |
| **Docker / `mem_limit` / `pids_limit`** | Docker **CHƯA CÀI** trên máy này |
| **CPU time** (`G18-02c`) | `ps` bị sandbox chặn ⇒ nguyên nhân của §6.2 **không** được khẳng định |
| **Xử lý trùng khi tiến trình thứ hai khởi động** (`G18-06d`) | Chưa dựng được ca đủ chặt |
| **Số phận sự kiện bị 429 ở §5.1** | Phụ thuộc việc hãng có gửi lại hay không — **câu hỏi cho J&T** |
| **PostgreSQL** (D-8) | CSDL nghiệp vụ **vẫn là SQLite**. Cổng 5432 **không** bị chạm; chốt `G18-10` chặn mọi biến môi trường trỏ tới nó |
| **Ánh xạ `area`/`city`** (D-9) | Không liên quan lượt này: mọi phép đo ở chế độ `mock`, và chốt cứng D-9 **giữ nguyên** |

---

## 8. Bộ hồi quy — để lượt sau không làm hỏng nó mà không ai biết

`app/thu/thu_g18_maysrv.py` — **17 ca**, `Ran 17 tests`, `OK`, ~6 giây. Tự dựng nền tạm, tự tắt
máy chủ. **Nạp bộ đo THẬT** từ `trien_khai/g18/harness_tai.py` theo đường dẫn, **không** chép lại:
chép là kiểm một bộ đo khác với bộ đo đã in ra các con số ở trên.

| Nhóm | Ca | Canh gì |
|---|---|---|
| `A_BoDo` (6) | a1–a6 | Bộ đo **phải đỏ được**: máy chủ lành ⇒ 0 lỗi · 500 ⇒ thấy 5xx · cắt kết nối ⇒ thấy lỗi · **0 yêu cầu KHÔNG được coi là lành** · 4 chuỗi trần đúng/sai · **đưa số đo GIẢ và đòi `do_lanh` trả `False`** |
| `B_Tran` (7) | b1–b7 | Trần qua HTTP = trần qua hàm · cổng CHỈ XEM không tiêu lượt · header 429 · **hợp đồng** `webhook.nhan` (600/1200) · **cơ chế** nhân trần (a)+(b) · cửa sổ trượt + **đối chứng dương** "IP khác không bị chặn" |
| `C_Tai` (4) | c1–c4 | Cửa ĐỌC 8 luồng · cửa GHI 8 luồng **và đếm dòng CSDL** · **ĐỐI CHỨNG ÂM một luồng** · `X-Request-Id` + log JSON |

**Hai ca thử của chính tôi đã đỏ ở lượt chạy đầu, và cả hai đều là lỗi THẬT của bộ thử — ghi lại
để không lặp:**
1. `test_c3` gửi lại đúng `event_id` của `test_c2` (bộ đếm nằm trong hàm thay vì trong mô-đun) ⇒
   `UNIQUE(carrier_account_id, event_id)` chặn ở tầng CSDL nên cả 30 lượt trả **200** thay vì
   **202**. Ca đỏ vì một lý do **không liên quan** tới thứ nó muốn đo.
2. `--tu-kiem` của harness: ca `BD4` viết `lambda sd: sd["tong"] == 0 and False` — một ca **luôn
   sai**, nên nó bị tính là HỎNG và `--tu-kiem` thoát 1. Một bộ tự kiểm không diễn đạt được *"ca
   này phải bị bác"* thì nó buộc người viết phải viết ra một ca luôn-đúng hoặc luôn-sai.

### 8.1 Hồi quy đầy đủ

`sh app/thu/chay_tat_ca.sh` — **1477 ca Python · 39 bộ chạy thật** (trước lượt này: 1460 ca / 38
bộ ⇒ **+17 ca, +1 bộ**, đúng bằng bộ thử mới) · frontend 56 + 36 ca · E2E `41/41`.

Trong lượt chạy đầu, **3 bộ báo hỏng**: `thu_bao_mat.py`, `thu_qa_g17.py`, `thu_tich_hop.py`.
**Cả ba là nguyên nhân MÔI TRƯỜNG, không phải mã của lượt này** — và điều đó được chứng minh
riêng, không suy đoán:

| Bộ | Ca hỏng | Nguyên nhân ĐO ĐƯỢC |
|---|---|---|
| `thu_bao_mat.py` | `test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git` | `git check-ignore …` trả **128**. Biến môi trường `GIT_CONFIG_COUNT=2` đi kèm `GIT_CONFIG_VALUE_0/1` nhưng **THIẾU `GIT_CONFIG_KEY_0/1`** ⇒ mọi lệnh `git` chết với `error: missing config key GIT_CONFIG_KEY_0`. Bỏ ba biến ấy đi thì `git check-ignore` trả **0** và in đúng đường bị chặn |
| `thu_tich_hop.py` | `test_04_…`, `test_11_…` | **cùng một nguyên nhân**: `returncode 128 != 0` |
| `thu_qa_g17.py` | `test_a1_cay_sach_va_head` | **cổng "cây sạch"** làm đúng việc của nó: 6 tệp **mới** của lượt này còn ở trạng thái `??` (chưa commit) ⇒ `CÂY BẨN tại mốc đo`. Hết bẩn là hết hỏng |

---

## 9. Việc tiếp theo (đề xuất, KHÔNG tự làm)

1. **`webhook.nhan` 600/phút và sự kiện hợp lệ bị 429** (§5.1): cần một quyết định của người vận
   hành — nới trần, hay thêm đường nhận riêng cho hãng, hay để nguyên và trông cậy vào việc hãng
   gửi lại. Trước khi quyết: **hỏi J&T** có gửi lại khi nhận 429 hay không.
2. **Mở rộng theo TIẾN TRÌNH, không theo luồng** (§6.2): mọi tài liệu vận hành đang nói "nhiều
   luồng" cần được sửa theo số đo này.
3. **`B-G11-10` vẫn CHƯA VÁ** — lượt này chỉ **đo lại và xác nhận** nó đúng qua HTTP thật. Muốn vá
   thì phải có kho đếm dùng chung, và đó là **quyết định hạ tầng của anh Thành** (điều kiện kích
   hoạt số 2 của kế hoạch PostgreSQL). Lượt này **không** tự làm.
4. **Ca `G18-06d`** (§6.3): dựng một ca đủ chặt cho xử lý trùng khi tiến trình thứ hai khởi động.
5. **CPU time** (§6.2): đo ở môi trường cho phép `ps` để trả lời *vì sao* thêm luồng lại chậm đi.

---

## 10. Bằng chứng

| Thứ | Ở đâu |
|---|---|
| Báo cáo máy đọc được | `$VIP_HUB_DATA/g18_tai/bao-cao-g18.json` (mặc định `/tmp/veh_g18_ag04/g18_tai/…`) |
| 5 lượt chạy đầy đủ của bản cuối | `/tmp/g18c_{1..5}.txt` — `KẾT LUẬN: 18/20 đạt · 0 hỏng · 0 BLOCKED · 2 bỏ qua`, thoát **0** cả 5 |
| 5 lượt chạy bản trước | `/tmp/g18_luot_{1..5}.txt` — thoát **0** cả 5 (đối chiếu độ ổn định) |
| Hồi quy đầy đủ | `/tmp/g18_hoiquy.txt` |
| Bộ thử mới | `python3 app/thu/thu_g18_maysrv.py` → `Ran 17 tests … OK`, thoát **0** |
| Tự kiểm + chứng minh ngược | `chot_an_toan.py --tu-kiem` (14/14) · `harness_tai.py --tu-kiem` (8/8) · `tiem_loi.py` (4/4), thoát **0** cả ba |

**Chưa có người đọc lại.** Toàn bộ là tác tử AI. `BAN_GIAO.md` §2 vẫn nguyên hiệu lực.
