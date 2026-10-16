# G21 / AG-04 — CỔNG ĐỐI CHIẾU **ĐỘC LẬP**: GIỚI HẠN TẦN SUẤT QUA TIẾN TRÌNH

**Làn:** AG-04 · **Nền:** `integration/g20` @ `a3400a8` · **Cổng đóng:** phần **giới hạn tần suất**
của **C5** trong `docs/QA_G20.md` (AG-01) · **Bộ đo:** `app/thu/thu_g21_gioihan.py` (**mới**)

---

## 0. PHÁN QUYẾT + BẰNG CHỨNG — ĐỌC KHỐI NÀY TRƯỚC MỌI CON SỐ

| Phép đo | Số THẬT |
|---|---|
| Lệnh | `sh trien_khai/g21-gioihan/chay.sh` |
| **Mã thoát** (in **TRƯỚC mọi pipe**) | **`EXIT_BO_DO=0`** |
| Cây đo | `HEAD = a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1` |
| **Số ca** | **38 ĐẠT · 0 HỎNG · 0 BỎ QUA (skip) · 0 KHUYẾT** |
| Thời gian | **67,4 giây** |
| Lệnh thật đã chạy | **66 lượt** (31× `migrate.py` · 31× `khoi_tao.py` · 1× con chốt · 1× `thu_gioi_han.py` · 1× `thu_han_muc_nguyen_tu.py` · 1× `thu_g19_gioihan.py`), **mã thoát khác 0 đã gặp: KHÔNG CÓ** |
| `sha256` bộ đo | `ac36bf2ffd5d3b0424116512f83768c3f56b2624f1afc429041bde93542ae1ef` |
| Nhật ký đầy đủ | `${TMPDIR}/veh_g21_ag04/gioihan.log` (**cố ý ngoài cây mã nguồn** — xem §9) |

### BẢNG N / TỔNG LƯỢT QUA / TRẦN KHAI BÁO (in nguyên văn từ log)

```
  BẢNG N / TỔNG LƯỢT QUA / TRẦN KHAI BÁO
  chiều      N    tổng lượt qua  trần khai báo  phán
  chung      1    20             20             ĐẠT
  chung      2    20             20             ĐẠT
  chung      4    20             20             ĐẠT
  chung      8    20             20             ĐẠT
  rieng      1    20             20             ĐẠT
  rieng      2    40             20             ĐẠT
  rieng      4    80             20             ĐẠT
  rieng      8    160            20             ĐẠT
  dot_bien   1    20             20             ĐẠT
  dot_bien   2    40             20             HỎNG
  dot_bien   4    80             20             HỎNG
  dot_bien   8    160            20             HỎNG
```

### CHẠY LẶP — một cổng chập chờn thì không phải cổng

Ba lượt chạy liên tiếp **cùng một `sha256` bộ đo**, cùng cây:

| Lượt | Lệnh | Mã thoát | Ca |
|---|---|---|---|
| 1 | `sh trien_khai/g21-gioihan/chay.sh` | `EXIT_BO_DO=0` | 38 ĐẠT · 0 HỎNG · 0 skip |
| 2 | `sh trien_khai/g21-gioihan/chay.sh` | `EXIT_BO_DO=0` | 38 ĐẠT · 0 HỎNG · 0 skip |
| 3 | `sh trien_khai/g21-gioihan/chay.sh` | `EXIT_BO_DO=0` | 38 ĐẠT · 0 HỎNG · 0 skip |

**Cả 12 dòng của bảng N giống nhau từng ô** ở cả ba lượt. Và ca nhạy thời gian nhất (`A6b`) cho
**cùng một con số `Retry-After` = 50 = dự đoán độc lập từ CSDL** ở cả ba lượt — nó không phải một
phép đo may rủi.

**Đọc bảng này thế nào — ba khối, ba câu khác nhau, và cả ba đều cần:**

| Khối | Nói điều gì | Vì sao không bỏ được |
|---|---|---|
| `chung` | N tiến trình **dùng chung một CSDL** ⇒ TỔNG **luôn = 20**, không nhân theo số bản | Đây là **bất biến chính** — cái `N-G20-01`/C5 nói là **chưa ai kiểm chứng độc lập** |
| `rieng` | N tiến trình **mỗi bản một CSDL** ⇒ TỔNG **= N × 20** | **ĐỐI CHỨNG DƯƠNG**: chứng minh bộ đo **NHÌN THẤY** được việc nhân. Không có khối này thì một bộ đo **MÙ** (luôn in "20") vẫn xanh ở khối `chung` |
| `dot_bien` | Bản quay lại *kho bộ nhớ một tiến trình* ⇒ **= N × 20** và luật phán **PHẢI trả HỎNG** | **TỰ KIỂM**: chứng minh cổng này **có răng**, không phải cổng hỏng sẵn. `N = 1` ở khối này là **đối chứng dương riêng** (một tiến trình thì hai lớp kho là một ⇒ phải ra đúng 20, tức bản đột biến chỉ đổi **đúng một biến**) |

---

## 1. VÌ SAO CÓ TỆP NÀY — CỔNG C5 CỦA AG-01, VÀ CHỖ NÓ ĐỨNG

`docs/QA_G20.md` §2.5 (AG-01) kết luận:

> con số **"1733 ca · 47 bộ"** mà mọi báo cáo trích dẫn **KHÔNG chứa một cổng G19-tổng-hợp nào**.
> … Các bộ **của từng làn** (`thu_g19_gioihan.py` 22 ca · `thu_g19_route.py` 49 ca ·
> `thu_g19_vtp.py` 31 ca) **có** chạy — nhưng đó là bộ **do người viết viết**, không phải cổng
> **đối chiếu độc lập**.

Đo lại **trên chính cây này**, nguyên văn (chạy 2026-10-16):

```sh
ls app/thu/thu_qa_g19*.py
# → app/thu/thu_qa_g19.py            (đúng MỘT tệp)

ls app/thu/thu_qa_g19_tich_hop.py
# → No such file or directory         EXIT=1

python3 app/thu/thu_qa_g19.py
# → EXIT_QA19=0  ·  OK (skipped=1)    ← 0 ca chạy
```

⇒ Khoảng trống C5 **vẫn còn nguyên** trên `a3400a8`. Làn này đóng **một phần** của nó: cổng
**giới hạn tần suất**. Bộ đo viết bởi **làn khác**, đo bằng **cách khác**, và **tự chứng minh có
răng** — đó đúng là định nghĩa "đối chiếu độc lập" mà C5 đòi.

---

## 2. HAI CHIỀU — VÌ SAO **BẮT BUỘC** PHẢI ĐO CẢ HAI

Đây là chỗ dễ tự lừa mình nhất, nên nói thẳng bằng một câu hỏi:

> Nếu bộ đo chỉ in ra `20` cho mọi N, làm sao biết đó là **"trần dùng chung"** hay **"bộ đo không
> nhìn thấy gì"**?

Hai câu trả lời đó **cho cùng một con số**. Nên bộ đo này **không** khẳng định "không nhân" bằng
cách so với một hằng số — nó **tự dựng tình huống mà trần PHẢI nhân**, và bắt buộc tình huống đó
phải ra đúng `N × 20`.

**Đo được (`A4.8`), nguyên văn:**

```
✓ [A4.8] N=8 bản RIÊNG CSDL: TỔNG qua = 160 = 8 × 20 — trần CÓ nhân
   từng bản qua [20, 20, 20, 20, 20, 20, 20, 20] ⇒ TỔNG 160 (mong 160) · mã lạ: [[], [], [], [], [], [], [], []]
```

Và **chiều ngược lại** — cùng bộ bắn, cùng trần, cùng số bản, **chỉ khác chỗ trạng thái nằm**
(`A2.8`):

```
✓ [A2.8] N=8 bản CHUNG CSDL: TỔNG qua = 20 (trần 20) — KHÔNG nhân theo số bản
   từng bản qua [3, 2, 3, 2, 2, 3, 2, 3] ⇒ TỔNG 20 · tổng lượt đã bắn 28
   · pid con [59185, 59203, 59216, 59222, 59230, 59239, 59247, 59255]
```

**8 `pid` KHÁC NHAU** đã thực sự phục vụ lượt — đây không phải 8 luồng trong một tiến trình, mà 8
tiến trình máy chủ thật (`subprocess`), cùng một CSDL, cùng IP `127.0.0.1`. Tám bản chia nhau
`20` suất (2–3 suất mỗi bản) chứ **không** bản nào có trần riêng.

### Vì sao phép bắn này MẠNH HƠN cách bắn lần lượt

`thu_g19_gioihan.bom_tuan_tu` bắn **lần lượt** từng bản một. Bộ đo này bắn **ĐỒNG THỜI**: mỗi
vòng, mọi bản còn sống nhận đúng một lượt, cùng một **hàng rào** (`threading.Barrier`) rồi mới
đi. Nghĩa là các lượt **chồng lên nhau thật** ở phía CSDL. Bất biến không đổi (TỔNG = đúng trần),
nhưng kịch bản đua — `BEGIN IMMEDIATE` + `INSERT … SELECT … WHERE COUNT(*) < trần` — được đo
trong đúng điều kiện nó được thiết kế để chịu.

Và đây là **kênh độc lập** (`A3`): bộ đo **không tin lời máy chủ**, nó mở thẳng tệp CSDL bằng
`sqlite3` và đếm:

```
✓ [A3] KÊNH ĐỘC LẬP: đếm thẳng `gioi_han_luot` bằng `sqlite3` khớp số qua HTTP
   đọc đĩa: 20 dòng `auth.dang_nhap|ip|127.0.0.1` trong cửa sổ 300 giây · qua HTTP: 20 · trần: 20
```

---

## 3. TỰ KIỂM — BỘ ĐO **PHẢI ĐỎ** KHI QUAY LẠI KHO BỘ NHỚ

Yêu cầu số 5 của nhiệm vụ, và đây là ca quan trọng nhất trong cả tệp.

Bộ đo tự sinh một **bản đột biến** của `app/gioi_han.py`: **giữ nguyên từng dòng phần QUYẾT ĐỊNH**
(chính sách · thứ tự kiểm hai chiều · luật 4 *"kiểm hết rồi mới ghi"* · cửa sổ trượt · thời gian
phạt) và **chỉ thay LỚP KHO** về đúng khuôn trước khi vá — trạng thái trong bộ nhớ **một tiến
trình**. Rồi nó chạy **ĐÚNG phép đo của A2** trên bản đó.

```
✓ [A5.1] ĐỐI CHỨNG DƯƠNG N=1: bản đột biến cho ĐÚNG 20 — nó chỉ đổi LỚP KHO, không đổi phần quyết định
   từng bản qua [20] ⇒ TỔNG 20 · luật phán: ĐÚNG trần khai báo (20) · đối chiếu A2.1 (bản THẬT, N=1) = 20

✓ [A5.2] N=2 bản ĐỘT BIẾN (kho bộ nhớ): TỔNG = 40 = 2 × 20, luật phán trả HỎNG
   luật phán: TRẦN NHÂN THEO SỐ BẢN: 40 lượt qua > trần 20 (thừa 20) · đối chiếu A2.2 = 20

✓ [A5.8] N=8 bản ĐỘT BIẾN (kho bộ nhớ): TỔNG = 160 = 8 × 20, luật phán trả HỎNG
   luật phán: TRẦN NHÂN THEO SỐ BẢN: 160 lượt qua > trần 20 (thừa 140) · đối chiếu A2.8 = 20
```

Hai điều được khẳng định **bằng máy**, không bằng lời:

1. **`N = 1` cho ĐÚNG 20.** Nếu bản đột biến đổi nhiều hơn "chỗ giữ trạng thái", con số này sẽ
   lệch — nó là **chốt cô lập biến**.
2. **`N ≥ 2` ra `N × 20` và luật phán trả HỎNG.** Bộ đo **thấy** việc nhân, và **cổng này đỏ**
   trên đúng hành vi cũ. Nếu `A5` xanh thì cổng này là **cổng hỏng sẵn** và mọi dòng xanh ở A2
   **không chứng minh gì**.

### 3.1 Hệ quả lên **MÃ THOÁT** — kiểm bằng máy, không bằng lời hứa

"Bộ đo PHẢI đỏ" chỉ có nghĩa nếu nó đổi **mã thoát**. `A5.TK` cho chính những con số **đo được
trên bản đột biến** đi qua **ĐÚNG luật phán** mà `A2` dùng, rồi đếm xem bao nhiêu ca sẽ HỎNG:

```
✓ [A5.TK] HỆ QUẢ MÃ THOÁT: nếu sản phẩm quay lại kho bộ nhớ, bộ đo trả mã thoát 1
   đưa các tổng ĐO ĐƯỢC TRÊN BẢN ĐỘT BIẾN ([20, 40, 80, 160]) qua ĐÚNG luật phán của A2
   ⇒ ca sẽ HỎNG: [2, 4, 8] ⇒ `main()` trả 1
```

`N = 1` **không** nằm trong danh sách đó, và **đó là điều phải đúng**: một tiến trình thì hai lớp
kho là một, nên nó **không phân biệt được** — đúng lý do bất biến này **buộc phải** đo ở `N ≥ 2`.

### 3.2 Luật phán cũng có răng — và có cả nhánh "chưa kết luận được"

`A0d` đo ba nhánh, nguyên văn:

```
qua=20 ⇒ (True,  ĐÚNG trần khai báo (20))
qua=80 ⇒ (False, TRẦN NHÂN THEO SỐ BẢN: 80 lượt qua > trần 20 (thừa 60))
qua=19 ⇒ (False, CHƯA CHẠM TRẦN: chỉ 19/20 lượt qua — phép đo thiếu lượt, KHÔNG kết luận)
```

Nhánh thứ ba là chỗ dễ nới lỏng nhất: **`tổng < trần` KHÔNG phải "đạt"**. Một phép đo bắn thiếu
lượt cũng ra "không nhân" — và kết luận đó là kết luận **rỗng**. Bộ đo coi nó là **HỎNG**.

---

## 4. CỬA SỔ TRƯỢT — CHỨNG MINH BẰNG DỮ LIỆU, KHÔNG BẰNG LỜI

Cách đo: **đẩy mốc thời gian của TỪNG DÒNG** trong `gioi_han_luot` rồi hỏi lại máy chủ. Đây là
phép **ĐO**, không phải bản vá: nó không đổi `gioi_han.py` một dòng nào, chỉ mô phỏng **thời gian
trôi qua** trên đúng dữ liệu mà cửa sổ đọc.

### 4.1 `Retry-After` bám theo DÒNG CŨ NHẤT, không bám theo mốc cửa sổ

Đẩy **cả 20 dòng** lùi **250 giây** (vẫn trong cửa sổ 300 giây), rồi gọi một lượt. Bộ đo **tự
tính độc lập** từ CSDL: `dòng cũ nhất còn trong cửa sổ + 300 − bây giờ + 1`.

```
✓ [A6b] Cửa sổ TRƯỢT: sau khi đẩy MỌI dòng lùi 250 giây, `Retry-After` co còn ~50 giây (KHÔNG phải ~300)
   đã lùi 20 dòng · vẫn 429: True · `Retry-After` máy chủ trả = 50
   · bộ đo ĐỘC LẬP tính từ CSDL = 50 · lệch ≤ 3 giây
```

**Vì sao `50` là con số quyết định:** một **cửa sổ CỐ ĐỊNH** neo ở lượt đầu sẽ trả `~300` ở đây.
Một bộ đếm **không có mốc từng dòng** thì **không thể** trả `50`. Con số `50` chỉ ra được từ một
cửa sổ **trượt trên từng mốc riêng của từng lượt**.

### 4.2 Nhả **ĐÚNG PHẦN ĐÃ TRÔI**, không nhả cả kho

Đẩy **7 dòng cũ nhất** ra hẳn khỏi cửa sổ ⇒ trong cửa sổ còn 13 ⇒ phải cho qua **đúng 7** rồi chặn:

```
✓ [A6a] Cửa sổ TRƯỢT: đẩy ĐÚNG 7 dòng cũ nhất ra khỏi cửa sổ ⇒ nhả ĐÚNG 7 suất rồi chặn lại
   đã lùi 7 dòng · bộ đo tự đếm trong cửa sổ: 13 dòng (trần 20)
   · máy chủ cho qua ĐÚNG 7 lượt rồi 429
```

Một bộ đếm **nguyên khối** theo cửa sổ sẽ nhả **0** hoặc **cả 20** — **không bao giờ đúng 7**.

### 4.3 Nhả hết, và **đối chứng ÂM** cho chính hai ca trên

```
✓ [A6c] đẩy HẾT ra khỏi cửa sổ ⇒ bộ đo tự đếm: 0 dòng · máy chủ cho qua 20 lượt rồi 429
✓ [A6d] ĐỐI CHỨNG ÂM: KHÔNG đẩy mốc ⇒ trong cửa sổ: 20 dòng · lượt gọi trả mã 429
```

`A6d` tồn tại để chặn kịch bản *"A6a/A6c xanh vì bộ đo vô tình xoá sạch kho trước mỗi lượt"*.
Không đẩy mốc thì **0 suất** — đó là điều phải đúng.

---

## 5. HAI CHIỀU ĐẾM, KHỞI ĐỘNG LẠI, VÀ HÌNH DẠNG PHẢN HỒI

### 5.1 Trần theo **IP** (20) và theo **ĐỊNH DANH** (12), cùng cửa sổ 300 giây

```
✓ [A1a] Chiều `ip`: đúng 20 lượt qua rồi 429 · `X-RateLimit-Limit`=20 · cửa sổ=300 giây
   từng lượt dùng một tên đăng nhập KHÁC NHAU ⇒ chỉ chiều `ip` cộng
   · `chieu`='ip' · `X-RateLimit-Window`=300

✓ [A1b] Chiều `dinh_danh` (cùng một tên): đúng 12 lượt qua rồi 429 · cửa sổ=300 giây
   `chieu`='dinh_danh' · `X-RateLimit-Limit`=12 · `X-RateLimit-Window`=300
   · HAI CHIỀU KHÁC NHAU (20 vs 12), CÙNG một cửa sổ 300 giây
```

Hai phép đo nằm trên **hai CSDL tạm khác nhau**, vì chiều `ip` đếm **mọi** lượt vào endpoint bất
kể tên — chạy chung một nền thì phép đo thứ hai đọc nhầm chiều. (Đây là chính bài học G18/AG-02
đã ghi lại, và bộ đo này **hành động theo nó** thay vì chỉ trích dẫn.)

### 5.2 Khởi động lại ⇒ trạng thái **CÒN**

```
✓ [A7a] Tiến trình MỚI (pid 60433 ≠ 60422) trên CSDL CŨ: lượt ĐẦU TIÊN đã bị chặn 429
   bản cũ tiêu hết 20/20 suất rồi bị tắt · bộ đo tự đếm lại từ đĩa: 20 dòng còn trong cửa sổ
   · bản MỚI trả mã 429, `Retry-After`=300

✓ [A7b] ĐỐI CHỨNG DƯƠNG: tiến trình mới trên CSDL MỚI TINH ⇒ lượt đầu QUA (401)
   kho đếm ĐỘC LẬP bằng `sqlite3`: TRƯỚC khi bắn 0 dòng, SAU khi bắn 1 dòng (mong 0 rồi 1)
   · `Retry-After`=None (mong None)
```

`A7b` cần thiết vì nếu thiếu nó, `A7a` có thể xanh chỉ vì *"máy chủ này luôn trả 429"*.

### 5.3 Phản hồi khi chạm trần

```
✓ [A8]  mã 429 · `Retry-After`='300' · `X-RateLimit-Limit`='20' · `X-RateLimit-Remaining`='0'
        · `X-RateLimit-Window`='300' · thân: chieu='ip' cho_bao_lau_giay=300
✓ [A8b] ĐỐI CHỨNG DƯƠNG: lượt ĐƯỢC QUA (401) KHÔNG mang `Retry-After`
```

### 5.4 MỘT SỰ THẬT ĐO ĐƯỢC, GHI LẠI — **KHÔNG** phải lời khen

```
✓ [A8c] SỰ THẬT ĐO ĐƯỢC: lượt ĐƯỢC QUA **KHÔNG** mang nhóm `X-RateLimit-*` — chỉ lượt 429 mới mang
   trên lượt 401: `X-RateLimit-Limit`=None · `X-RateLimit-Window`=None · `X-RateLimit-Remaining`=None
```

**GHI CHÚ CHO AG-00 — KHÔNG phải lỗi tôi tự sửa (ngoài phạm vi được cấp):** với hợp đồng hiện có,
bên gọi **không biết được ngân sách còn lại TRƯỚC khi bị chặn**; muốn biết phải chạm trần.
Hệ quả trực tiếp lên **cách viết bộ đo**: trần và cửa sổ **buộc phải** đọc từ chính lượt `429`
(lần đầu tôi đọc từ lượt `401` và nhận `None` — đó là một lỗi **của bộ đo tôi**, đã sửa, ghi ở
§7). Đây là **mô tả trung thực** hành vi đang có, không phải một khiếm khuyết được suy diễn.

---

## 6. `408 → timeout=True` — Ý ĐỊNH §42, ĐO QUA STUB LOOPBACK

`docs/SHARED_CONTRACTS.md` §42 chốt: `408` và `429` là **lỗi TẠM THỜI**, và **`408` phát ra
`timeout=True`** ("KHÔNG BIẾT kết quả") — **CỐ Ý**, vì trong thực tế `408` không rõ nghĩa (nhiều
proxy phát `408` khi *thượng nguồn* quá hạn, lúc đó yêu cầu **có thể đã được xử lý**).

Đo qua **stub J&T cục bộ của dự án** (`app/thu/stub_jt.py`, bind `127.0.0.1` + cổng do hệ điều
hành cấp) — **đây là đường DUY NHẤT được phép chạm tới một "hãng", và nó là stub**:

```
✓ [A9a] `408` ⇒ adapter phát `timeout=True` (KHÔNG BIẾT kết quả) — đúng ý định §42
   adapter: `ok`=False · `timeout`=True · `ma_chuan`='HET_GIO' · `co_the_thu_lai`=True
   · `http_status`=408 · mất 0,61 giây (lớp HTTP KHÔNG được tự ngủ)
   · lớp `http_jt`: tam-thoi mã 408  ·  `loi_hang.tu_http(408)`: ma_chuan='HET_GIO' co_the_thu_lai=True
```

**HAI đối chứng dương** — vì một ca "`408` ⇒ `timeout=True`" xanh được vì nhiều lý do sai:

```
✓ [A9b] `429` ⇒ adapter `timeout`=False · `co_the_thu_lai`=True
        (hai mã CÙNG "tạm thời" nhưng KHÁC nhau ở `timeout` — gộp chúng là khuôn lệch §42 đã bác)
✓ [A9c] `400` VẪN là VĨNH VIỄN · `loi_hang.tu_http(400)`: ma_chuan='THAM_SO_SAI' co_the_thu_lai=False
        (chặn kịch bản "A9a xanh vì MỌI 4xx đều bị coi là tạm thời")
```

---

## 7. HAI LỖI CỦA CHÍNH BỘ ĐO TÔI — ghi lại vì chúng dạy đúng một điều

| Lỗi | Triệu chứng | Nguyên nhân thật | Đã sửa |
|---|---|---|---|
| **Đọc trần từ lượt ĐƯỢC QUA** | `A1a`/`A1b` đỏ với `X-RateLimit-Window=None` dù số lượt qua **đúng 20/12** | Máy chủ chỉ gắn nhóm `X-RateLimit-*` lên lượt **429**; lượt `401` không mang header nào | đọc từ chính lượt `429`; **và** biến phát hiện đó thành ca `A8c` thay vì giấu đi |
| **Đếm ca bằng MỘT khuôn** | `A10.thu_g19_gioihan.py` hiện `None ca` | `unittest` in `Ran N tests`, bộ làn G19 in `N ca — ĐẠT`. Bộ đếm chỉ nhận khuôn thứ nhất | nhận **cả hai** khuôn; và **từ chối** một bộ có `0 ca` (đếm ra 0 là HỎNG, không phải ĐẠT) |

> **Bài học giống hệt bài học AG-01 tự ghi ở `QA_G20.md` §4.4:** một con số **trông như đo được**
> (`None ca`, `None giây`) nguy hiểm hơn một con số thiếu. Vì vậy `A10` nay **HỎNG** nếu đếm ra
> `0 ca`, và `A0d` coi `tổng < trần` là **HỎNG** chứ không phải ĐẠT.

---

## 8. SỔ ĐỐI CHỨNG — MỌI CA ÂM PHẢI CÓ CA DƯƠNG

```
  [sổ] 408-timeout            âm=1 dương=2
  [sổ] cua-so-truot           âm=1 dương=4
  [sổ] hinh-dang-429          âm=1 dương=1
  [sổ] hoi-quy                âm=0 dương=3
  [sổ] khoi-dong-lai          âm=1 dương=1
  [sổ] tran-dung-chung        âm=0 dương=4
  [sổ] tran-ip                âm=0 dương=2
  [sổ] tran-nhan-theo-ban     âm=0 dương=4
  [sổ] tu-kiem-dot-bien       âm=4 dương=1

✓ [A11a] Phép kiểm 'thiếu đối chứng dương' có RĂNG và KHÔNG báo động giả
   nhóm ÂM cố ý thiếu DƯƠNG ⇒ bắt được ['nhom-gia-thieu-duong'] · nhóm đủ hai chiều / chỉ DƯƠNG / rỗng ⇒ []
✓ [A11b] MỌI nhóm có ca ÂM trên cây này đều có ca DƯƠNG đi kèm · nhóm thiếu DƯƠNG: KHÔNG CÓ
```

Năm nhóm có ca ÂM (`408-timeout` · `cua-so-truot` · `hinh-dang-429` · `khoi-dong-lai` ·
`tu-kiem-dot-bien`) đều có ca DƯƠNG đi kèm. Bốn nhóm `âm=0` chỉ toàn khẳng định dương — hợp lệ,
và sổ **không** báo động vì chúng.

`A11a` **tự kiểm chính phép kiểm**: nó dựng một nhóm ÂM cố ý thiếu DƯƠNG và đòi phép kiểm **bắt
được**, đồng thời đòi phép kiểm **không báo động giả** trên nhóm đã đủ hai chiều. Một phép kiểm
chưa từng bắt được gì là một phép kiểm chưa chứng minh được gì.

---

## 9. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY

| # | Điều bị cấm | Cách bộ đo tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng **kể cả sandbox** (`V-G09-01`, `V-13906-05` CHƯA CẤP) | Mọi HTTP chỉ chạm `127.0.0.1` cổng do hệ cấp. Phần `408` dùng `app/thu/stub_jt.py` — stub này **tự chặn** mọi `host` khác `127.0.0.1`/`localhost` | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | Không một lệnh `git push`/`ssh`/tunnel. `VIP_HUB_BIND=127.0.0.1` đặt **TƯỜNG MINH** cho mọi tiến trình con (không trông cậy mặc định — biến thừa hưởng có thể mở cổng). Cổng lấy từ `bind(('127.0.0.1', 0))` | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; credentials thật; `.env`; in bí mật | `A0c`: tiến trình con **đọc thẳng thuộc tính lớp** của ba adapter ⇒ cả ba `False`. Bí mật trong bộ đo là chuỗi **GIẢ** hậu tố `GIA`; không đọc `.env` | ✓ |
| 4 | Đoán mã trạng thái hãng (D-4) | Bộ đo chỉ chạm mã HTTP của **máy chủ nhà** và của **stub**; không gán một mã nào cho hãng | ✓ |
| 5 | Chốt `D-9` (`city`/`area`) | **Không** chạm ánh xạ `area`; giữ nguyên chốt cứng | ✓ |
| 6 | Chuyển CSDL sang PostgreSQL (D-8), cấm `:5432` | `A0b`: 16 byte đầu của `hub.db` = `b'SQLite format 3\x00'`. `VIP_THU_POSTGRES` bị **GỠ** khỏi môi trường mọi tiến trình con. **Không** mở kết nối nào tới `:5432`. Tiến trình con **TỰ CHỐI** (mã 9) nếu CSDL ngoài thư mục tạm | ✓ |
| 7 | Dùng Claude/mô hình khác; tự bấm duyệt sandbox | Không một lời gọi mô hình; không thao tác duyệt nào | ✓ |
| 8 | Xoá hàng loạt; sửa ngoài phạm vi | `git status --porcelain` = **đúng ba mục**, tất cả nằm trong vùng được ghi (xem §10). **Không** sửa một dòng mã sản phẩm. Tắt tiến trình theo **ĐÚNG PID** (không `pkill`/`killall`); thư mục tạm `vh-g21-ag04-*` đã dọn **rỗng** sau mỗi lượt chạy | ✓ |

**Vì sao log KHÔNG nằm trong repo:** ghi log vào cây mã nguồn làm cây **BẨN**, và trên cây này có
các cổng *"cây sạch"* (`thu_qa_g17.py::A_Nen`, `thu_qa_g18.py::A_Nen`) sẽ **ĐỎ vì một tệp rác** —
đỏ vì lý do không liên quan tới sản phẩm. Nên `chay.sh` ghi vào `${TMPDIR}/veh_g21_ag04/`.

---

## 10. TỆP ĐÃ THÊM + `sha256`

| Tệp | Vai trò | `sha256` |
|---|---|---|
| `app/thu/thu_g21_gioihan.py` | **Bộ đo** (mới, 1258 dòng) | `ac36bf2ffd5d3b0424116512f83768c3f56b2624f1afc429041bde93542ae1ef` |
| `trien_khai/g21-gioihan/chay.sh` | Cách chạy lại, in `EXIT_BO_DO` **trước mọi pipe** | `b7422aed90c40c6a715c67daee0e3b529627c0bdb21051e058ae59bda9e6bd29` |
| `trien_khai/g21-gioihan/README.md` | Chỉ dẫn làn | `7aafb7291b6ce43309258bb4baf36f35ae2957dacbea6e323c0c70a373800485` |
| `docs/G21_GIOIHAN.md` | Tài liệu này | (không tự băm chính mình — băm tự thân đổi mỗi lần sửa; `sha256` ở thời điểm đóng là `49221f24f225cfaf9cb042aa3ab11a5be9d6ba87d1072c59bb83e7583bb867f2`) |

```sh
$ git status --porcelain
?? app/thu/thu_g21_gioihan.py
?? docs/G21_GIOIHAN.md
?? trien_khai/g21-gioihan/
```

**KHÔNG** sửa `app/gioi_han.py`, `app/server.py`, `app/csdl.py`, `thu_qa_g17.py`, `thu_qa_g18.py`
hay bất kỳ tệp nào ngoài phạm vi được cấp.

---

## 11. CÒN LẠI — NÓI THẲNG, ĐÂY LÀ **PHẠM VI** KHÔNG PHẢI LỜI HỨA

| # | Chưa đóng | Vì sao | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Cổng C5 chưa tự chuyển xanh** | Cổng C5 của AG-01 khớp `thu_qa_g19*.py`; tệp của làn này là `thu_g21_gioihan.py`. **Phạm vi được cấp của tôi không gồm tệp `thu_qa_g19_tich_hop.py`** | **AG-00**: hoặc nới khuôn khớp của C5 cho `thu_g21_*.py`, hoặc thêm `app/thu/thu_qa_g19_tich_hop.py` gọi `sh trien_khai/g21-gioihan/chay.sh`. **Lượt 2 đã ĐO CẢ HAI CHIỀU của lựa chọn này — xem §12.4** |
| 2 | **Nhiều MÁY, hoặc sau bộ cân bằng tải** | Mỗi máy một CSDL ⇒ trần **VẪN NHÂN** — chính `app/gioi_han.py` dòng 42-43 tự khai. Chỗ đó cần Redis hoặc một CSDL chung | **CHƯA LÀM, CHƯA ĐO** — quyết định của anh Thành |
| 3 | **Tấn công phân tán nhiều IP** | Ngoài phạm vi giới hạn tần suất theo IP; cần WAF/gateway | ngoài phạm vi |
| 4 | **Tải lớn** (ngoài trần tần suất) | G18 đã đo 8 tiến trình × 400 phép; lượt này **không chạy lại** | giữ nguyên phạm vi G18 |
| 5 | **PostgreSQL / Redis** | **BỊ CẤM** (D-8); cụm `:5432` là của dự án khác | quyết định của anh Thành |
| 6 | **Đoán mã trạng thái 110 của hãng** (D-4) | Ngoài phạm vi bộ đo này | `NEEDS_REVIEW` tới khi hãng xác minh |
| 7 | **Ba cổng C5 khác** (`route` · `21 mã VTP` · các bộ G19-tổng-hợp còn lại) | Làn này chỉ đóng phần **giới hạn tần suất** | các làn AG-02/03/05/06 của G21 + lượt 2 của AG-01 |
| 8 | **Một tiến trình mồ côi KHÔNG phải của làn này** | `lsof` cho thấy `app/server.py` pid **41082** trên `127.0.0.1:19449`, `cwd = …/g21-ag06-e2e`, CSDL tạm `veh-chan-doan.87rDui` ⇒ **của AG-06**. Chỉ bind loopback (không mở ra ngoài) | **AG-06** dọn. Tôi **không** đụng vào vì nó ngoài phạm vi được cấp |

**Ngoài phạm vi đã đo — nói thẳng:** bộ đo này là một **phép đo**, không phải một yêu cầu sửa.
Nó **không** thay thế nghiệm thu của làn G19/AG-02; nó là **cổng đối chiếu thứ hai** trên **bản
đã gộp**. Và nó **không** phải một cổng luôn xanh: xem §3 — nó **đã đỏ** trên bản đột biến, và
đó là điều duy nhất khiến những dòng xanh ở trên có nghĩa.

---

## 12. LƯỢT 2 — NỐI CỔNG VÀO BỘ CHẠY CHUNG, VÀ CHỨNG MINH CỔNG **ĐO ĐƯỢC**

Lượt 1 (§1–§11) đóng **phép đo**. Lượt 2 này đóng **cái nối** — và một cái nối chỉ có nghĩa nếu
nó **đỏ được**. *"Nối cho nó xanh"* là chưa đủ: một cổng không bao giờ đỏ thì không chứng minh gì.

| | |
|---|---|
| **Tệp mới** | `app/thu/thu_g19_tich_hop.py` (bộ tổng hợp, 538 dòng) |
| **Việc của nó** | gọi `sh trien_khai/g21-gioihan/chay.sh` và **trả về ĐÚNG mã thoát của runner** |
| **Cây đo** | `HEAD = 9ded4a5cee269c02998a0d0181051e3ed1de720b` |
| **Vùng được ghi** | `app/thu/thu_g19_tich_hop.py` · `trien_khai/g21-gioihan/*` · `docs/G21_GIOIHAN.md`. **KHÔNG** sửa `app/thu/thu_qa_g19*.py` (tệp của AG-01) |

### 12.1 KHUÔN MÀ BỘ ĐẾM CỦA `chay_tat_ca.sh` NHẬN RA — BA ĐIỀU KIỆN, VÀ CÁCH TỆP NÀY KHỚP

`app/thu/chay_tat_ca.sh` tự dò (`find app/thu gateway/thu -name 'thu_*.py'`) rồi phán **bằng mã
thoát**, đòi thêm **dấu vết đã chạy** và **số ca > 0**:

```sh
if printf '%s' "$OUT" | grep -qE '^OK( |$)|ca — ĐẠT'; then CO_DAU_VET=1; else CO_DAU_VET=0; fi
if [ "$MA" -eq 0 ] && [ "$CO_DAU_VET" = 1 ] && [ "$N" -gt 0 ]; then   # ✓
```

| Điều kiện | Tệp này thoả thế nào |
|---|---|
| được **tự dò** | tên khớp `thu_*.py` ⇒ `find` thấy, không cần thêm vào danh sách nào |
| **mã thoát 0** | mã thoát của cổng = **mã thoát nguyên văn của runner**; runner thoát 0 thì cổng thoát 0 |
| **dấu vết đã chạy** | phần tự kiểm in bằng `unittest` (`OK`) — cùng khuôn với mọi bộ khác |
| **số ca > 0** | `Ran 8 tests` của phần tự kiểm. **Cố ý KHÔNG in TỔNG của runner ở đây:** `thu_g21_gioihan.py` cũng là tệp `thu_*.py` nên **bộ chạy chung đã tự dò và đếm nó riêng**; in thêm là ĐẾM HAI LẦN |

**Bằng chứng lượt chạy thật của bộ chạy chung** (`sh app/thu/chay_tat_ca.sh`, HEAD `9ded4a5`):

```
  ✓ thu_g19_tich_hop.py         8 ca
```

Tệp được **tự dò**, chạy, và ghi nhận **8 ca · mã thoát 0** — đúng khuôn, không phải sửa
`chay_tat_ca.sh` một dòng nào (và cũng **không được phép** sửa).

Toàn cảnh lượt chạy chung đó (**12 phút · 1908 ca · 54 bộ chạy thật** + 1 bộ BỎ QUA là
`thu_qa_g19.py` 0 ca): **`thu_g19_tich_hop.py` nằm trong danh sách ĐẠT**. Ba bộ HỎNG của lượt đó
là chuyện khác — xem §12.7.

### 12.2 BẰNG CHỨNG CỔNG **ĐO ĐƯỢC** — TÁM CA TỰ KIỂM: BỐN CA **TIÊM LỖI THẬT** + HAI CA **KHÔNG CHẠY ĐƯỢC** + HAI **ĐỐI CHỨNG DƯƠNG**

Mỗi ca dưới đây **chạy một tiến trình thật** trên **bản sao thật của `chay.sh`**, rồi hỏi **đúng
hàm phán mà cổng dùng cho runner thật** (`do_runner()` → `phan_quyet()`). Lỗi được tiêm vào bản
sao, **không** vào runner gốc; mỗi ca còn khẳng định bản sao **khác bản gốc ĐÚNG MỘT DÒNG** và
bản sao bị **xoá ngay** sau ca đó (`(z)` canh không còn rác).

| Ca | Lỗi được tiêm vào **bản sao** của runner | Mã thoát **THẬT** | Cổng phán | Lý do cổng đưa ra |
|---|---|---|---|---|
| **(a)** | gọi bộ đo sai đường dẫn (`thu_g21_khong_ton_tai_GIA.py`) | **2** | **ĐỎ** | `runner HỎNG: mã thoát 2 (KHÁC 0)` |
| **(b1)** | runner **không tồn tại** (không tiêm gì — trỏ vào đường dẫn lạ) | *(không chạy)* | **ĐỎ** | `KHÔNG CHẠY ĐƯỢC: … không phải TỆP THƯỜNG` |
| **(b2)** | runner là **thư mục** | *(không chạy)* | **ĐỎ** | `KHÔNG CHẠY ĐƯỢC: … không phải TỆP THƯỜNG` |
| **(c)** | thay bộ đo bằng **suite `unittest` RỖNG** ⇒ in `Ran 0 tests` + `OK`, thoát **0** | **0** | **ĐỎ** | `runner thoát 0 nhưng 0 ca (0 ca KHÔNG phải là đạt)` |
| **(c2)** | thay runner bằng **tệp rỗng** (chạy trót lọt, không in gì) | **0** | **ĐỎ** | `runner thoát 0 nhưng output KHÔNG có dấu vết đã chạy ca nào` |
| **(d)** | bản sao in dòng tổng kết `TỔNG=5 · BỎ QUA=5` rồi thoát 0 | **0** | **ĐỎ** | `MỌI ca đều BỎ QUA (5/5) ⇒ 0 ca ĐO THẬT` |
| **(e1)** | *đối chứng DƯƠNG, dữ liệu tổng hợp*: `TỔNG=7`, thoát 0 | **0** | **ĐẠT** | `runner thoát 0 · 7 ca đo thật` |
| **(e2)** | *đối chứng DƯƠNG của kênh thứ hai*: stdout `TỔNG=7`, log `TỔNG=9` | **0** | **ĐỎ** | `HAI KÊNH LỆCH NHAU` |

**Ca (c) là ca đáng giá nhất**: nó dựng lại **đúng hình dạng "xanh giả"** — `unittest` in `OK`,
tiến trình thoát **0**, và một luật chỉ nhìn mã thoát (hoặc chỉ nhìn chữ `OK`) sẽ **cho qua**.
Cổng này **không** cho qua, vì nó đòi **số ca > 0** — cùng luật với `chay_tat_ca.sh`.

**Vì sao (e1) không bỏ được:** không có nó thì (a)–(d) chỉ chứng minh *"cổng luôn đỏ"*, và một
cổng luôn đỏ cũng **không đo được gì**. Đối chứng dương **mạnh nhất** là chính lượt chạy thật ở
§12.3: runner thật ⇒ cổng **ĐẠT**, mã thoát 0.

### 12.3 LƯỢT CHẠY THẬT QUA CỔNG

| Phép đo | Số THẬT |
|---|---|
| Lệnh | `python3 app/thu/thu_g19_tich_hop.py` |
| Tự kiểm cổng | `Ran 8 tests` · `OK` · 0 hỏng · 0 lỗi |
| Mã thoát **TIẾN TRÌNH** của runner | **0** |
| Mã thoát runner **TỰ KHAI** (`EXIT_BO_DO=`) | **0** (khớp — lệch là ĐỎ) |
| Ca (kênh 1 — stdout runner) | **TỔNG=38 · ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0** |
| Ca (kênh 2 — **tệp log**, mtime trong chính lượt này) | **TỔNG=38** (khớp) |
| Thời gian | **68,2 giây** |
| **Mã thoát CỔNG** | **0** (= nguyên văn mã thoát của runner) |

In nguyên văn khối kết luận của cổng (rút gọn phần bảng N của runner):

```
Ran 8 tests in 0.158s
OK
EXIT_BO_DO=0
  ca ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=38
  BẢNG BẰNG CHỨNG — CỔNG TỔNG HỢP G19 (G21/AG-04)
  mã thoát TIẾN TRÌNH runner             : 0
  mã thoát runner TỰ KHAI (EXIT_BO_DO)   : 0
  kênh 1 (stdout runner)                 : TỔNG=38 · ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0
  kênh 2 (tệp log, mtime trong lượt này): TỔNG=38
  KÊNH QUYẾT ĐỊNH số ca                  : kênh 1 (stdout runner) ⇒ TỔNG=38 · ĐẠT=38 · BỎ QUA=0
  thời gian                              : 68.2 giây
  PHÁN QUYẾT CỔNG                        : ĐẠT — runner thoát 0 · 38 ca đo thật (ĐẠT 38 · BỎ QUA 0)
  MÃ THOÁT CỔNG                          : 0  ← trùng mã thoát của runner
  KẾT LUẬN: 38 ca ĐO THẬT · cổng ĐẠT · bộ chạy chung ghi nhận bộ này là ĐẠT.
```

### 12.4 CỔNG C5 CỦA AG-01 — **CÒN ĐỎ**, VÀ ĐO ĐƯỢC **CHÍNH XÁC VÌ SAO**

Chạy lại **nguyên văn** lệnh nghiệm thu (bản `thu_qa_g20.py` **chép tạm** từ worktree `g20-ag01-qa`,
đã **XOÁ** sau khi đo):

```sh
VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py     # → EXIT_C5=1
Ran 21 tests in 40.187s
FAILED (failures=7, skipped=2)
       thu_qa_g19.py → mã thoát 0 · 0 ca
  [C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: 0/1 · phán quyết=chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN
```

**C5 = ĐỎ.** Và lý do **không** phải "cổng chưa nối": lý do là **KHUÔN TÊN**.

```python
ung_vien = sorted(t for t in os.listdir(GOC_THU) if re.match(r"thu_qa_g19.*\.py$", t))
```

C5 chỉ nhìn họ tên `thu_qa_g19*`. Trên cây này họ đó có **đúng một** tệp — `thu_qa_g19.py` — và
chính nó **tự bỏ qua** trên cây đã gộp (0 ca) kèm lời nhắc *"Nghiệm thu cây ĐÃ GỘP thuộc bộ riêng
`thu_qa_g19_tich_hop.py`"*. Bộ tổng hợp của làn này tên là **`thu_g19_tich_hop.py`** (vùng được
cấp) — **không khớp khuôn đó** ⇒ C5 **vẫn Đỏ dù cổng đã nối xong**. Đây là **lỗi phối hợp tên**,
không phải lỗi của phép đo.

**Đã ĐO CẢ HAI CHIỀU của lựa chọn "thêm tệp đúng khuôn tên"** (để quyết định của AG-00 có số, chứ
không phải phỏng đoán). Tôi tạo **tạm** một bản uỷ quyền 23 dòng `app/thu/thu_qa_g19_tich_hop.py`
(**chỉ là cái tên** — `runpy` sang `thu_g19_tich_hop.py`, giữ **một bản logic**), chạy **đúng ca C5**,
rồi **XOÁ**:

| Lượt | `app/thu/thu_qa_g19_tich_hop.py` | Kết quả C5 |
|---|---|---|
| Nghiệm thu (nguyên văn) | **KHÔNG có** | `0/1 · phán quyết=chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN` ⇒ **ĐỎ** |
| Đo thử (bản uỷ quyền tạm, sau đó **đã xoá**) | có | `thu_qa_g19_tich_hop.py → mã thoát 0 · 8 ca` · `1/2 · phán quyết=DONG` ⇒ **XANH** (`Ran 1 test in 65.272s` · `OK` · `EXIT=0`) |

⇒ **Một tệp 23 dòng chỉ-để-có-tên là đủ để C5 chuyển Xanh**, và nó **không** sửa một dòng nào của
AG-01 (`thu_qa_g19.py` giữ nguyên). Bản uỷ quyền tạm đó cũng **tự đi qua bộ chạy chung** như một bộ
thử bình thường: `✓ thu_qa_g19_tich_hop.py 8 ca`.

Nhưng tệp đó nằm trong **họ tên của AG-01** — **ngoài vùng được ghi** của làn này
(`app/thu/thu_g19_tich_hop.py` + `trien_khai/g21-gioihan/*` + `docs/G21_GIOIHAN.md`) — nên tôi
**đã XOÁ** nó và **báo AG-00 quyết** (câu hỏi dispatch `msg_219b576dad5b`; hết hạn 15 phút **chưa
có trả lời** ⇒ chọn **mặc định AN TOÀN**: không giữ một tệp ngoài vùng được ghi).

**Nếu AG-00 trả lời "có"**, việc đóng C5 là **23 dòng** (nội dung ở `sha256`
`b60a63980d7196ba51b1915a5ce9b283b84f5af4dc3ceb402bfec9094e149964`) — **đã đo là Xanh**, không
phải phỏng đoán. Phần chức năng của tệp đó chỉ có **bốn dòng**:

```python
import os, runpy, sys
DUONG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thu_g19_tich_hop.py")
sys.argv[0] = DUONG
runpy.run_path(DUONG, run_name="__main__")
```

Cách còn lại (nới khuôn C5 cho `thu_g19_*.py`) là sửa **tệp của AG-01**, cũng ngoài vùng được ghi
của tôi.

### 12.5 MÃ THOÁT CỦA CỔNG

| Mã | Khi nào | Là mã của ai |
|---|---|---|
| **0** | runner thoát 0 **và** có ca ĐO THẬT | **nguyên văn của runner** |
| **x ≠ 0** | runner thoát x | **nguyên văn của runner** |
| **127** | runner **KHÔNG CHẠY ĐƯỢC** (không tồn tại / là thư mục) | riêng của cổng (POSIX "không thấy lệnh") |
| **124** | runner **QUÁ HẠN** | riêng của cổng (quy ước `timeout(1)`) |
| **4** | runner thoát 0 nhưng **0 ca ĐO THẬT** | riêng của cổng — **chỗ DUY NHẤT siết hơn runner**, và (c)/(c2)/(d) chứng minh vì sao |
| **3** | **TỰ KIỂM của cổng hỏng** | riêng của cổng — cổng không đáng tin thì không được phép xanh |

Ngoài hai chỗ siết đó, mã thoát của cổng là **mã thoát nguyên văn của runner**: không viết lại,
không nuốt, không đổi thành `1` cho tiện.

### 12.6 TỆP CỦA LƯỢT 2 + `sha256`

| Tệp | Vai trò | `sha256` |
|---|---|---|
| `app/thu/thu_g19_tich_hop.py` | **Bộ tổng hợp** (mới, 538 dòng): tự kiểm tiêm lỗi + chạy runner thật | `4e9360adc78fedaae913fea8279f5382a7d50cb9a30b07e81368f41aa08f1585` |
| `trien_khai/g21-gioihan/README.md` | + mục "Bộ tổng hợp" | `47fff9799ebfc76104af373d7d2861cc23bb10902a91bc50e8fb9557924e4272` |
| `docs/G21_GIOIHAN.md` | Tài liệu này (+ §12) | (không tự băm chính mình) |

**KHÔNG** sửa `app/thu/chay_tat_ca.sh`, **KHÔNG** sửa `app/thu/thu_qa_g19*.py` (tệp của AG-01),
**KHÔNG** sửa một dòng mã sản phẩm nào.

### 12.7 MỘT HỆ QUẢ PHẢI NÓI RÕ: **TỆP MỚI** LÀM CỔNG "CÂY SẠCH" ĐỎ

`git status --porcelain` trên cây này — đúng **ba mục**, **tất cả nằm trong vùng được ghi của làn**:

```
 M docs/G21_GIOIHAN.md
 M trien_khai/g21-gioihan/README.md
?? app/thu/thu_g19_tich_hop.py
```

(Bản uỷ quyền tạm `app/thu/thu_qa_g19_tich_hop.py` ở §12.4 **đã bị xoá** — nó **không** còn trên
cây, nên không có trong danh sách này; lúc đo thì nó có, và đó là mục `??` thứ tư.)

Hai cổng **"cây sạch"** (`thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` và bản tương ứng của
`thu_qa_g18.py`) đòi `git status --porcelain` **RỖNG**, nên chúng **ĐỎ** khi có tệp chưa được
commit — **bất kể tệp đó là gì**:

```
AssertionError: Lists differ: [' M docs/G21_GIOIHAN.md', ' M trien_khai/…README.md',
 '?? app/thu/thu_g19_tich_hop.py', '?? app/thu/thu_qa_g19_tich_hop.py'] != []
       : CÂY BẨN tại mốc đo (F0-a) ⇒ mọi số đo vô hiệu
```

Đây là **hệ quả của việc THÊM TỆP**, không phải của mã. Ba tệp của lượt 1 cũng ở đúng tình trạng
này cho tới khi chúng được commit ở `9ded4a5` — sau đó chúng **không còn** trong danh sách bẩn.
Trong lượt chạy chung, vì lý do đó:

```
  ✓ thu_g19_tich_hop.py         8 ca
  ✗ thu_g20_baomat.py          27 ca  HỎNG (mã thoát 1)
        FAIL: test_a1_cay_sach_theo_pham_vi_wave (__main__.A_Nen)
        FAIL: test_b1_hai_bo_thu_cu_deu_xanh_tren_cay_co_tep_cua_wave (__main__.B_ChotCaySach)
  ✗ thu_qa_g17.py              56 ca  HỎNG (mã thoát 1)
        FAIL: test_a1_cay_sach_va_head (__main__.A_Nen)
        FAIL: test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO (__main__.A_Nen)
  ✗ thu_qa_g18.py              46 ca  HỎNG (mã thoát 1)
        FAIL: test_a1_cay_sach_theo_pham_vi_wave (__main__.A_Nen)
        FAIL: test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO (__main__.A_Nen)
        FAIL: test_b1_tang_3_chay_duoc_va_khong_co_ca_hong (__main__.B_Tang3)
```

(`thu_qa_g18.py` còn một ca HỎNG **không liên quan** tới làn này: `B_Tang3` — tầng 3 Chromium; nó
không nằm trong chuỗi nhân quả "cây bẩn" và tôi **không** nhận nó là của mình.)

Tôi **không** commit (deliverable để AG-00 gộp) và **không** sửa hai cổng đó — chúng ngoài vùng
được ghi. Cách đóng: commit tệp của làn này, hoặc (AG-00) cho hai cổng đó miễn trừ đúng đường dẫn
của làn.
