# G18 · AG-05 — PostgreSQL: ĐƯỜNG GHI THẬT (`csdl.ghi`, `rowcount`)

> **AI-ASSISTED, KHÔNG PHẢI NGƯỜI SOÁT.** Mọi số trong tài liệu này do một tác tử AI chạy trên
> máy này. `docs/BAN_GIAO.md` §2: **"AI review không phải human review. Bộ thử xanh không phải
> lời cho phép."** Tài liệu này **không** cho phép chuyển kho.

**Tác tử:** AG-05 (DeepSeek, trong Orca) · **Ngày đo:** 15/10/2026
**Nền:** `integration/g17` @ `7b741c88b3b280d65f80b5e11301f17ebd767b26`
**Máy đo:** Darwin arm64 26.6.2 · Python 3.9.6 · SQLite 3.51.0 · PostgreSQL 16.15 (Homebrew) ·
libpq 160015 (`/opt/homebrew/lib/libpq.dylib`)

> **MỐC CÂY — tự đo, đừng tin tài liệu** (`BAN_GIAO.md` §7.3: tệp này không ghi SHA của chính
> commit chứa nó). Người đọc tự chạy:
> ```bash
> find app gateway thu_frontend thu_giao_dien trien_khai -type f \
>   \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
>   | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
> ```
> Vân tay cây lúc đo: `c19bf349335204c395d7386b245f4febcf0b79c78ed49b1bf386f4acc49f0952`
> (lệnh này **không** phủ `docs/`, nên tệp bạn đang đọc không làm nó đổi.)

---

## 0. ĐÂY LÀ CÁI GÌ — và KHÔNG phải cái gì

**Quyết định D-8 vẫn nguyên vẹn.** `app/csdl.py` **không bị sửa một dòng nào**;
`app/du-lieu/hub.db` **không bị đọc, không bị ghi**; **CSDL nghiệp vụ vẫn là SQLite**. Tài liệu
này là **số đo để quyết**, không phải một lượt chuyển kho.

| Tài liệu này LÀ | KHÔNG phải |
|---|---|
| Số đo `rowcount` của **đường ghi thật** (`csdl.ghi`) trên cả hai kho | Một lượt chuyển CSDL |
| Một lớp ca thử **chạy được trong hồi quy** và **làm đỏ được** (12/12 đột biến) | Một bản kế hoạch đã thực hiện |
| Bằng chứng cụm `:5432` **không bị đụng** + cụm thử tự dọn | Một đề xuất mở cổng hay lên production |

### 0.1 Lỗ hổng được bịt — nguyên văn của AG-01

AG-01 ghi ở mục **CHƯA ĐỎ** của lượt nghiệm thu G17:

> "PostgreSQL: đường GHI (csdl.ghi, rowcount) — AG-05 chỉ dùng SCHEMA"

Đọc kèm `docs/G17_POSTGRES.md` §8 (NẰM NGOÀI PHẠM VI): *"Lớp phương ngữ `csdl.py` — CHƯA làm ⇒
mã nghiệp vụ **chưa chạy được** trên PostgreSQL"*. Lượt G17 đã nạp schema, đã đo bốn kết cục
**bằng SQL viết tay / bằng `psql`**, nhưng **hàm `csdl.ghi()` và giá trị `rowcount` nó trả về
chưa bao giờ chạy trên PostgreSQL**. Đó là thứ lượt này đo.

### 0.2 NĂM tệp được ghi trong lượt này

```
 M app/thu/thu_postgres.py                      (thêm lớp L: 13 ca mới, 42 → 55 ca)
?? trien_khai/postgres/libpq_ctypes.py          (MỚI: cầu nối libpq qua ctypes — không cài gói nào)
?? trien_khai/postgres/duong_ghi_pg.py          (MỚI: bản sao khuôn csdl.ghi/mo/giao_dich cho PostgreSQL)
?? trien_khai/postgres/do_ghi_that.py           (MỚI: bộ chạy bằng chứng — 4 bảng W/T/M/D)
?? trien_khai/postgres/thu_dot_bien_ghi.py      (MỚI: 12 đột biến cho lớp L)
?? docs/G18_PG_WRITE.md                         (MỚI: tài liệu này)
```
Không tệp nào khác bị đụng. Không push, không deploy, không tunnel, không mở cổng.

---

## 1. ĐO BẰNG CÁCH NÀO — và vì sao cách đó ĐO ĐƯỢC

`app/csdl.py` không được sửa (và nằm ngoài danh sách được ghi). Nên phép đo có hai vế, **vế nào
cũng là đường ghi thật**:

| Vế | Là gì | Vì sao tin được |
|---|---|---|
| **SQLite** | Gọi **CHÍNH `csdl.ghi()`** của sản phẩm, chỉ trỏ `cau_hinh.DUONG_DAN_CSDL` sang tệp TẠM | Không phải bản chép: cùng hàm, cùng `mo()`, cùng `giao_dich()` |
| **PostgreSQL** | **Bản sao ĐÚNG KHUÔN** của `mo()`/`ghi()`/`giao_dich()`, chỉ đổi **ranh giới trình điều khiển** | Thân hàm giữ nguyên hình dạng (khoá ghi, trả con trỏ, tự chốt ngoài giao dịch). Phép so là so **ranh giới driver**, không phải so hai đoạn mã của hai người |

### 1.1 Không cài thêm gói nào — và vì sao điều đó quan trọng

Máy đo **không có** `psycopg2`/`psycopg`. Ba đường, chọn đường thứ ba:

| Đường | Vì sao không dùng |
|---|---|
| `pip install psycopg2-binary` | Sửa môi trường Python ngoài khu được cấp quyền ghi, và trên máy thiếu gói thì lớp ca mới **BỎ QUA** — tức hiện dấu ✓ mà chạy 0 ca, đúng cái bẫy đã ghi ở đầu `app/thu/thu_postgres.py` |
| `psql` rồi đọc nhãn lệnh | **ĐO ĐƯỢC**: `psql -q` KHÔNG in nhãn `INSERT 0 1`/`UPDATE 3` — cột `out` rỗng ở **mọi** câu DML (xem `docs/G17_POSTGRES.md` không có mục này; đây là phát hiện mới của lượt này). Muốn có số thì phải tự phân tích chuỗi — lúc đó con số là do *bộ phân tích của tôi* sinh ra |
| **`ctypes` + `libpq`** | **CHỌN.** `libpq` đã có sẵn trên máy, và `PQcmdTuples` chính là **nguồn số mà `psycopg2.rowcount` đọc**. Đo qua đây là đo đúng con số sản phẩm sẽ nhận, không qua một bản diễn giải trung gian |

Cầu nối `trien_khai/postgres/libpq_ctypes.py` cố ý **mô phỏng đúng những chỗ đã đo được của
`psycopg2`**, và điều đó được ghi thành lời hứa kiểm được:

* `rowcount` ← `PQcmdTuples`; chuỗi rỗng (lệnh không có số dòng, ví dụ `CREATE TABLE`) → **`-1`**;
* câu có tập kết quả (`SELECT`) → `rowcount` = **số dòng trả về** (khác `sqlite3`! xem §2);
* **KHÔNG có `lastrowid`** — `psycopg2` không có thuộc tính đó, nên ở đây cũng không định nghĩa:
  `cur.lastrowid` ném `AttributeError` **y như thật**. Đó là phép đo, không phải thiếu sót;
* lỗi `23xxx` → `LoiToanVen`, còn lại → `LoiVanHanh` (hai cái tên **nghiệp vụ** của `csdl.py`);
* `tu_dong_chot=False` mô phỏng **chế độ mặc định của `psycopg2`** (`BEGIN` ngầm, chốt khi `commit()`).

### 1.2 Vế "SỰ THẬT" — mỗi ca đều có

Một `rowcount` là **lời khai của trình điều khiển**. Nên mỗi ca, sau lượt ghi, còn một lượt
**ĐỌC KIỂM CHỨNG trên kết nối KHÁC**: đếm/đọc thẳng trạng thái thật trong kho. Ca nào khai
`rowcount=1` mà kho không có dòng nào thì bị bắt ngay, không cần tin lời khai. **23/23 ca có vế
này ĐẠT ở CẢ HAI kho** (`do_ghi_that.py` tự phán; thiếu vế nào là tự phán HỎNG).

---

## 2. BẢNG W — 23 DẠNG GHI, `rowcount` CỦA HAI KHO

```bash
python3 trien_khai/postgres/do_ghi_that.py            ; echo "EXIT=$?"    # → EXIT=0
```
```bash
python3 app/thu/thu_postgres.py L_DuongGhiSanPham     ; echo "EXIT=$?"    # → EXIT=0 · Ran 13 tests · OK
```

| # | Ca | SQLite | đọc lại | PostgreSQL | kiểm chứng |
|---|---|---|---|---|---|
| N0 | `SELECT` qua chính `ghi()` — 0 dòng | **-1** | -1 | **0** | OK/OK |
| W1 | INSERT 1 dòng | 1 | 1 | 1 | OK/OK |
| W2 | INSERT 3 dòng trong MỘT câu | 3 | 3 | 3 | OK/OK |
| N1 | `SELECT` qua chính `ghi()` — 4 dòng | **-1** | -1 | **4** | OK/OK |
| W3 | INSERT trùng khoá (phải NÉM LỖI) | `IntegrityError` | — | `LoiToanVen` `23505` | OK/OK |
| W4 | `INSERT OR IGNORE` khi ĐÃ có khoá | 0 | 0 | 0 | OK/OK |
| W5 | `INSERT OR IGNORE` khi CHƯA có khoá | 1 | 1 | 1 | OK/OK |
| W6 | `INSERT OR REPLACE` khi ĐÃ có khoá | 1 | 1 | 1 | OK/OK |
| W7 | UPDATE khớp ĐÚNG 1 dòng | 1 | 1 | 1 | OK/OK |
| W8 | UPDATE khớp 3 dòng | 3 | 3 | 3 | OK/OK |
| W9 | UPDATE KHÔNG khớp dòng nào | 0 | 0 | 0 | OK/OK |
| W10 | UPDATE đặt LẠI đúng giá trị đang có | 1 | 1 | 1 | OK/OK |
| W11 | DELETE khớp 1 dòng | 1 | 1 | 1 | OK/OK |
| W12 | DELETE KHÔNG khớp dòng nào | 0 | 0 | 0 | OK/OK |
| W13 | DELETE khớp 2 dòng | 2 | 2 | 2 | OK/OK |
| W14 | DDL qua chính `ghi()` | -1 | -1 | -1 | OK/OK |
| W15 | `INSERT … RETURNING id` | **2** | **2** | **1** | OK/OK |
| W16 | `INSERT … SELECT` không chọn được dòng nào | 0 | 0 | 0 | OK/OK |
| W16b | ĐỐI CHỨNG PHƯƠNG NGỮ: `WHERE 0` | 0 | 0 | **LỖI `42804`** | OK/OK |
| W17 | INSERT vào bảng **NGHIỆP VỤ** thật (`tenants`) | 1 | 1 | 1 | OK/OK |
| W18 | UPDATE nghiệp vụ khớp 1 dòng | 1 | 1 | 1 | OK/OK |
| W19 | UPDATE nghiệp vụ KHÔNG khớp | 0 | 0 | 0 | OK/OK |
| W20 | DELETE nghiệp vụ khớp 1 dòng | 1 | 1 | 1 | OK/OK |

**19/23 ca GIỐNG NHAU. 4 ca LỆCH** — và cả bốn đã được khai báo, chốt cứng trong bộ thử
(`test_l2`): thêm một ca lệch MỚI là **ĐỎ**, vì một lệch mới chưa ai khai báo chính là thứ đổi
nghĩa `rowcount` sau lưng mã nghiệp vụ.

### 2.1 Lệch 1 — câu ĐỌC: SQLite `-1`, PostgreSQL = số dòng thật (`N0`, `N1`)

`sqlite3.Cursor.rowcount` trả **`-1`** cho câu trả về tập kết quả; `psycopg2` trả **số dòng**.
Mã kiểu `if cur.rowcount == 1` hoặc `if cur.rowcount > 0` sau một câu ĐỌC **đổi nghĩa hoàn toàn**
khi đổi kho — không một dòng lỗi nào. Hôm nay chưa chỗ nào trong `app/` đọc `rowcount` sau một
câu ĐỌC (§2.5), nên đây là **mìn chưa nổ**, không phải sự cố đang xảy ra.

### 2.2 Lệch 2 — `INSERT … RETURNING`: SQLite trả con số CŨ (`W15`) — **lỗi phía SQLite**

Ca `W15` chèn **1** dòng và SQLite trả `rowcount = 2`. Số `2` là **số dòng của câu DML TRƯỚC ĐÓ**
(`W13`: `DELETE … WHERE id IN (3,4)` → 2 dòng).

Cơ chế, và nó được kiểm bằng một phép phá riêng: câu `RETURNING` **chưa chạy tới `DONE`** khi ta
đọc `rowcount`, nên CPython đọc `sqlite3_changes()` — mà con số đó vẫn là của **câu trước**.
Đột biến *"ca W13 xoá 1 dòng thay vì 2"* làm `test_l4` **ĐỎ** ⇒ ca thử bám vào **CƠ CHẾ**, không
bám vào một hằng số. `PostgreSQL` trả **1**, đúng.

Đo riêng để loại trừ khả năng "số 2 là do bộ đo của tôi": trên một CSDL sạch, `INSERT` thường rồi
`INSERT … RETURNING` → SQLite trả `1` (trùng PostgreSQL, không thấy gì); **sau một `DELETE` 2 dòng**
→ trả `2`; **sau một `UPDATE` 3 dòng** → trả `3`. Đọc lại sau khi hút hết dòng vẫn là con số cũ.

> **Đây là lỗ hổng PHÍA SQLITE, không phải phía PostgreSQL** — và nó chỉ lộ ra khi chạy đường ghi
> trên **cả hai** kho. Nó cũng là lý do kỹ thuật để **không** đọc `rowcount` trên câu `RETURNING`.

### 2.3 Lệch 3 — phương ngữ: `WHERE 0` (`W16b`)

SQLite nhận `WHERE 0`; PostgreSQL từ chối: `42804 argument of WHERE must be type boolean, not type
integer`. Lệch này **KÊU TO** (câu lệnh hỏng ngay, không có `rowcount`), nên nó thuộc nhóm "phải
sửa khi chuyển kho", không thuộc nhóm "sai im lặng".

### 2.4 NGUY CƠ 4 — `rowcount = 1` mà KHÔNG có gì trong kho (chế độ mặc định của `psycopg2`)

Không phải một lệch `rowcount`, mà là chỗ **`rowcount` không nói lên điều gì về tính BỀN**.

`csdl.mo()` chạy `isolation_level=None`: **mỗi câu tự chốt**. Chế độ **mặc định của `psycopg2`**
thì ngược lại: `BEGIN` ngầm, chỉ chốt khi `commit()`. Nếu ai đó chuyển kho mà giữ nguyên `ghi()`:

| | `rowcount` | lỗi ném ra | kho (đọc từ kết nối KHÁC) |
|---|---|---|---|
| `csdl.ghi()` trên SQLite | 1 | **không** | **1 dòng** |
| `ghi()` trên PostgreSQL, chế độ mặc định | 1 | **không** | **0 dòng** — và bốc hơi khi đóng kết nối |

Đo bằng `test_l8`, có **đối chứng dương** ở dòng đầu. Đây là kịch bản "logic *ghi được hay không*
sai **IM LẶNG**" đúng nghĩa nhất trong cả lượt đo.

### 2.5 VÌ SAO ĐIỀU NÀY QUAN TRỌNG — 19 chỗ đang đọc `rowcount`

```bash
grep -rn "\.rowcount" --include=*.py app/ | grep -v "^app/thu/" | wc -l    # → 19
grep -rn "\.lastrowid" --include=*.py app/ | grep -v "^app/thu/" | wc -l   # → 23
grep -rn "RETURNING" --include=*.py app/ | grep -v "^app/thu/" | wc -l     # → 0
```

19 chỗ đọc `.rowcount` trong mã chạy thật (`doi_soat` 4 · `billing` 5 · `tai_chinh` 3 · `webhook` 2
· `gioi_han` 2 · `don_hang` 1 · `usage` 1 · `migrate` 1). **Đã soát từng chỗ**: tất cả đều đọc
`rowcount` **sau một câu GHI** (`UPDATE`/`DELETE` có `WHERE`), và ở đó hai kho **GIỐNG NHAU**
(0 · 1 · N — bảng §2). Nghĩa là:

* **Hôm nay chưa có chỗ nào trong mã nghiệp vụ đọc `rowcount` sai** trên PostgreSQL.
* Mìn nằm ở **đường chuyển kho**: `app/` có **23 chỗ dùng `.lastrowid`**, mà `psycopg2` **không có**
  thuộc tính đó (§1.1). Cách thay chuẩn là `INSERT … RETURNING id` — **và khi đó `rowcount` của
  chính những câu ấy rơi vào lệch §2.2 nếu đọc ở phía SQLite**. Hai việc này phải làm cùng nhau,
  không tách được.

---

## 3. BẢNG T — BỐN KẾT CỤC, LẦN NÀY QUA **CHÍNH ĐƯỜNG GHI**

G17 §2 đã đo bốn kết cục bằng `psql`. Lượt này đo lại bằng `ghi()`/`giao_dich()` của sản phẩm
(`test_l6`, `test_l7`, `test_l8`):

| Kết cục | SQLite | PostgreSQL |
|---|---|---|
| **T1 `CHỐT_THÀNH_CÔNG`** — `giao_dich()` rồi chốt | `rowcount=1` · kho **1 dòng** | `rowcount=1` · kho **1 dòng** |
| **T2 `GIAO_DỊCH_HỎNG`** — ném lỗi giữa khối | `rowcount=1` (đã trả) · kho **0 dòng** | `rowcount=1` (đã trả) · kho **0 dòng** |
| **T3 `CHƯA_CHỐT`** (§2.4) | `rowcount=1` · kho **1 dòng** | `rowcount=1` · kho **0 dòng** — **im lặng** |
| **T4 câu SAU một câu hỏng, trong cùng giao dịch** | `rowcount=1` · **BỀN** | **`25P02`** · **không bền** |
| **T5 `KHOA_HẾT_GIỜ`** — kết nối khác giữ khoá HÀNG | `database is locked` | **`55P03`** `lock_not_available` |
| | `rowcount` = **không có** · `x` không đổi | `rowcount` = **không có** · `x` không đổi |

Hai chỗ đáng chú ý nhất:

* **T2**: `rowcount` **đã trả 1** ở cả hai kho, mà sau khi lùi kho **trống**. `rowcount` không phải
  bằng chứng của tính bền — ở **cả hai** kho. Đây là lý do mọi ca trong bộ đo đều có vế đọc kiểm chứng.
* **T4**: khác biệt **thật** và đã biết từ G17 (`thu_postgres.test_c2`), nay đo qua đường ghi:
  SQLite huỷ **CÂU**, PostgreSQL huỷ **CẢ GIAO DỊCH**. Hệ quả thực tế: một khối `giao_dich()` có
  `try/except` bên trong chạy đúng trên SQLite và **hỏng toàn bộ** trên PostgreSQL.

**T5 đo được ở cả hai kho** trong cùng một ca: bên giữ khoá là một kết nối khác, bên ghi là chính
`ghi()`. Phía SQLite phải hạ `PRAGMA busy_timeout` xuống 400ms **chỉ cho phép đo** (mặc định
`csdl.mo()` là 30 giây) — nói ra để không ai tưởng đó là hành vi sản phẩm.

---

## 4. BẢNG M/D — MẤT CẬP NHẬT: một câu của G17 KHÔNG ĐÚNG VỚI ĐƯỜNG GHI THẬT

`docs/G17_POSTGRES.md` §2.1 kết luận: *"**PostgreSQL im lặng mất; SQLite từ chối ồn ào**"* (PG: 120
chốt / 55 thật / mất 65 / **0 lỗi**; SQLite: 30 chốt / 30 thật / mất 0 / **90 lượt `database is
locked`**). Câu đó **đúng với khuôn G17 đã dùng** — khuôn SQLite của họ có **giao dịch tường minh**
(`BEGIN IMMEDIATE`), nên lượt ghi thứ hai bị **từ chối ồn ào**.

**Nhưng đường ghi THẬT của sản phẩm thì khác.** `csdl.mot()` đọc ở chế độ tự chốt, `csdl.ghi()`
ghi ở chế độ tự chốt — **không có giao dịch nào bao quanh**. Đo lại đúng khuôn đó, 4 tiến trình
THẬT × 30 vòng:

| Lượt đo | PostgreSQL (đọc-rồi-ghi) | SQLite (đọc-rồi-ghi) | PostgreSQL (nguyên tử) | SQLite (nguyên tử) |
|---|---|---|---|---|
| 1 | 120 chốt · 65 thật · **mất 55 (45,8%)** · lỗi 0 | 120 · 91 · **mất 29 (24,2%)** · lỗi 0 | mất **0** | mất **0** |
| 2 | 120 · 48 · **mất 72 (60,0%)** · lỗi 0 | 120 · 77 · **mất 43 (35,8%)** · lỗi 0 | mất **0** | mất **0** |
| 3 | 120 · 59 · **mất 61 (50,8%)** · lỗi 0 | 120 · **120** · **mất 0** · lỗi 0 | mất **0** | mất **0** |

> **Tỉ lệ phần trăm của SQLite KHÔNG tất định (0 → 43 trên 120).** Đó chính là lý do bảng này
> **không** được dùng làm chốt trong bộ thử. Chỉ hai thứ là bất biến: **PostgreSQL mất > 0** ở cả
> ba lượt, và **khuôn nguyên tử mất = 0** ở cả hai kho (đối chứng dương của đồng hồ đo).

### 4.1 BẢN TẤT ĐỊNH — con số chắc chắn, và nó là chốt của bộ thử

Bản đua phụ thuộc lịch trình hệ điều hành. Nên có thêm một bản **BẮT TAY qua tệp mốc**: hai tiến
trình thật cùng ĐỌC một giá trị, **chờ nhau đọc xong**, rồi cùng GHI `giá_trị + 1`.

| Kho | hai bên đã đọc | lượt chốt | giá trị THẬT | **MẤT** | lỗi |
|---|---|---|---|---|---|
| PostgreSQL | `{A: 0, B: 0}` | 2 | 1 | **1** | **0** |
| SQLite | `{A: 0, B: 0}` | 2 | 1 | **1** | **0** |

**SQLite cũng mất cập nhật, và cũng IM LẶNG — y hệt PostgreSQL.** Kịch bản tự kiểm bỏ đồ của
chính nó: nếu hai bên không đọc cùng một giá trị thì lượt đo bị phán HỎNG (một "bắt tay" hỏng
cho ra con số vô nghĩa). Đây là ca được chốt cứng trong bộ thử (`test_l9`) vì nó **tất định**.

**Hệ quả cho G17 §7 (khuyến nghị #2 "soát từng chỗ đọc-rồi-ghi"):** việc phải soát **không chỉ**
nằm ở đường chuyển sang PostgreSQL. Khuôn đọc-rồi-ghi **không bọc `giao_dich()`** đã mất cập nhật
im lặng **ngay trên SQLite hôm nay**. Có chỗ như vậy trong mã chạy thật — ví dụ
`app/bao_mat.py` đọc `users.so_lan_sai` rồi ghi lại **giá trị tuyệt đối** (`UPDATE users SET
so_lan_sai=?`), nên hai lượt đăng nhập sai song song làm bộ đếm sai; và
`app/thu/dong_thoi/nguoi_chay.py` đọc `dem` rồi ghi `dem+1`. Đếm được bao nhiêu chỗ như thế thì
lượt này **chưa làm** (xem §8).

---

## 5. BẪY THỨ NĂM — `IDENTITY` không biết lượt chèn `id` TƯỜNG MINH

Phát hiện **ngoài dự kiến**, lộ ra khi lớp `L` chạy chung với lớp `B` (lớp `B` chèn
`tenants (id=1)` tường minh rồi lượt chèn kiểu sản phẩm của `L` nhận `23505`).

Đo riêng thành `do_bay_identity` / `test_l13`, trên bảng dịch từ chính schema sản phẩm
(`INTEGER PRIMARY KEY AUTOINCREMENT` → `BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY`):

| Bước | SQLite | PostgreSQL |
|---|---|---|
| 1. `INSERT INTO w_idt (id,x) VALUES (1,10)` | 1 dòng | 1 dòng |
| 2. `INSERT INTO w_idt (x) VALUES (20)` — **khuôn của `csdl.ghi`** | **`rowcount=1`** | **`23505`** trùng khoá `w_idt_pkey` |
| kho sau cùng | **2 dòng** | **1 dòng** |

**Vì sao:** SQLite lấy id tự sinh = `max(rowid)+1` — nó *nhìn thấy* lượt chèn tường minh.
PostgreSQL lấy từ **sequence**, mà sequence **không biết** lượt nào chèn `id` tường minh.

**Hệ quả cho D-8:** mọi đường chèn `id` tường minh khi chuyển kho — **di trú dữ liệu, seed, phục
hồi sao lưu** — **PHẢI** `setval` lại sequence, nếu không thì lượt ghi kế tiếp của **mã nghiệp vụ**
hỏng. Loại hỏng này **KÊU TO** (khác ba lệch `rowcount` ở §2), nhưng nó chỉ lộ ra **sau** khi dữ
liệu đã vào — tức là lúc hệ đã chạy.

---

## 6. CHỐT CHẶN: CỤM `:5432` KHÔNG BỊ ĐỤNG — đo, không khai

Cụm riêng: cổng **55432** · dữ liệu `mkdtemp("vhpg-thu-")` · socket `mkdtemp("/tmp/vhpg.XXXX")` ·
`listen_addresses=''` (**KHÔNG mở TCP nào**) · dừng bằng `pg_ctl stop -m fast -w` rồi `rmtree`
(**KHÔNG `pkill`/`killall`** — `CLAUDE.md` §16.7).

Vân tay cụm `:5432` (`trien_khai/postgres/van_tay_cum.py`, CHỈ ĐỌC) — TRƯỚC = SAU:

| Trường | TRƯỚC | SAU |
|---|---|---|
| PID postmaster | `58873` | `58873` |
| `data_directory` | `/opt/homebrew/var/postgresql@16` | *(giống)* |
| postmaster bắt đầu | `2026-10-09 10:24:22.104803+07` | *(giống)* |
| phiên bản máy chủ | `16.15 (Homebrew)` | *(giống)* |
| số CSDL | `6` | `6` |
| danh sách CSDL | `postgres template0 template1 vip_customs vip_customs_g16 vip_customs_test` | *(giống)* |
| PID nghe TCP `:5432` | `['58873']` | `['58873']` |

**Tự dọn — và một chỗ suýt báo động giả.** Lượt chạy đầu của `do_ghi_that.py` báo
`/tmp/vhpg-thu-XXXX còn 1`. Kiểm ra: thư mục đó có mốc **10:19**, tức **8 tiếng trước** lượt này —
nó là rác của **làn khác** trên máy, không phải của tôi (máy này đang chạy nhiều làn song song:
`/tmp` có sẵn hàng trăm thư mục `vh-dt1-*`, `vh-giaodich-*`, `vh-migdt-*` của các làn khác).
Đếm thô "có thư mục là hỏng" là **phép đo sai**. Bộ chạy nay **chụp danh sách thư mục tạm TRƯỚC**
rồi chỉ kêu phần **MỚI XUẤT HIỆN**:

```
Thư mục tạm MỚI XUẤT HIỆN trong lượt này = 0 []
Thư mục tạm CÓ SẴN TỪ TRƯỚC (của làn khác, KHÔNG phải của lượt này) = 1 ['vhpg-thu-bmkugtqh']
Cụm thử tự dọn: /tmp/vhpg.* = 0 []
```
Lượt này **không xoá** thư mục của làn khác — nó chỉ nói ra.

---

## 7. BẰNG CHỨNG — LỆNH · MÃ THOÁT · SỐ CA · SỐ BỎ QUA

Mọi mã thoát lấy **ngay sau lệnh, trước mọi đường ống**.

| # | Lệnh | Mã thoát | Số ca | Bỏ qua |
|---|---|---|---|---|
| 1 | `python3 app/thu/thu_postgres.py` | **0** | **55** (`Ran 55 tests … OK`) — trước lượt này: 42 | **0** |
| 2 | `python3 app/thu/thu_postgres.py L_DuongGhiSanPham` | **0** | **13** (`Ran 13 tests … OK`) | **0** |
| 3 | `python3 trien_khai/postgres/do_ghi_that.py` | **0** | **23** ca W (×2 kho) · **5** kết cục T · **2** lượt M (4 khuôn) · **1** ca D (×2 kho) | **0** |
| 4 | `python3 trien_khai/postgres/thu_dot_bien_ghi.py` | **0** | **12/12** đột biến làm đỏ ĐÚNG ca canh nó | **0** |
| 5 | `python3 trien_khai/postgres/do_ghi_that.py --ra /tmp/kq.json` | **0** | JSON bằng chứng đầy đủ | — |
| 6 | `python3 trien_khai/postgres/van_tay_cum.py --vong -- env -u GIT_CONFIG_* sh app/thu/chay_tat_ca.sh` | **1** *(xem §7.1)* | python **1473** ca / **38** bộ · frontend **56 + 36** · E2E **41/41** | 0 |

**SHA tệp (sha256):**

```
0e45322b3e8ad7fb582ae86ebe6cd73e0fe8e6f097017c64cf599596dc786b6c  app/thu/thu_postgres.py
f6ea060c7f1120c60ac98e3dca09066702f1a1efcc03b548060b33cb7eeed6e5  trien_khai/postgres/libpq_ctypes.py
150d81936a7573a2dca1ee274e63b4b7e4ffd6c6ae5179f65ca8193fc97fb285  trien_khai/postgres/duong_ghi_pg.py
27f535cebe7ffc028fe427b0f8f1a41a181a2d9dd6dc60c78535ce1179a73abf  trien_khai/postgres/do_ghi_that.py
b7845f8052e7e4183b1697d193acdc5c0a15dc11296d385130d6a9ba32025d56  trien_khai/postgres/thu_dot_bien_ghi.py
```
Vân tay cây: `c19bf349335204c395d7386b245f4febcf0b79c78ed49b1bf386f4acc49f0952`. Nền:
`integration/g17` @ `7b741c88b3b280d65f80b5e11301f17ebd767b26` (`main = de740dc`, không chứa G13–G18).

### 7.1 BỘ HỒI QUY: 38 bộ · 1473 ca · **một bộ ĐỎ, và nó không phải của tôi**

```
python:   1473 ca · 38 bộ chạy thật
bộ hỏng:  thu_qa_g17.py
        FAIL: test_a1_cay_sach_va_head (__main__.A_Nen)
```
`thu_postgres.py` **55 ca · ✓**. Bộ đỏ là **cổng "cây sạch" của chính AG-01** (`thu_qa_g17.py`),
nó đòi `git status --porcelain` **rỗng** trừ hai mẫu `app/thu/thu_qa_g17*.py` và `docs/QA_G17*.md`.
Đo lại đúng hàm đó:

```
Số dòng `git status` KHÔNG thuộc quyền AG-01/G17: 5
     M app/thu/thu_postgres.py
    ?? trien_khai/postgres/do_ghi_that.py
    ?? trien_khai/postgres/duong_ghi_pg.py
    ?? trien_khai/postgres/libpq_ctypes.py
    ?? trien_khai/postgres/thu_dot_bien_ghi.py
```
**Đúng 5 tệp của lượt này.** Cổng đó đỏ với **mọi** làn đang có việc chưa commit — nó là cổng
*"đo lúc cây sạch"*, không phải một ca thử về mã. Lượt này **không** `git commit` (không được giao
việc đó); commit/merge xong thì cổng xanh trở lại. **Nói ra thay vì im lặng sửa cổng của làn khác.**

### 7.2 Đột biến — 12/12, và ĐỐI CHỨNG bản nguyên bản vẫn XANH

```bash
python3 trien_khai/postgres/thu_dot_bien_ghi.py   ; echo "EXIT=$?"    # → EXIT=0
```
```
── ĐỐI CHỨNG: bản chép nguyên bản, chạy lớp L_DuongGhiSanPham
   ✓ mã thoát 0 · ['Ran 13 tests in 2.247s']
   ✓ Bỏ `setval` sequence cho `tenants`            → ĐỎ (test_l1)   [bẫy IDENTITY §5]
   ✓ Phép so hai kho luôn phán 'giống nhau'        → ĐỎ (test_l11)
   ✓ Trình điều khiển PG trả -1 cho câu ĐỌC        → ĐỎ (test_l2)
   ✓ Ca W13 xoá 1 dòng thay vì 2                   → ĐỎ (test_l4)
   ✓ Giao dịch hỏng thì CHỐT thay vì LÙI           → ĐỎ (test_l6)
   ✓ Trình điều khiển TỰ LÙI rồi THỬ LẠI (25P02)   → ĐỎ (test_l7)
   ✓ Đường ghi PG ép chế độ TỰ CHỐT                → ĐỎ (test_l8)
   ✓ Kịch bản bắt tay đổi sang khuôn NGUYÊN TỬ     → ĐỎ (test_l9)
   ✓ Đồng hồ đo dùng khuôn NGÂY THƠ cả hai nhánh    → ĐỎ (test_l10)
   ✓ Phép so BỎ vế ĐỌC KIỂM CHỨNG                  → ĐỎ (test_l11)
   ✓ Chốt chặn cổng 5432 không từ chối nữa         → ĐỎ (test_l12)
   ✓ DDL bảng đo mất IDENTITY                      → ĐỎ (test_l13)
ĐẠT: 12/12 đột biến làm ĐỎ ĐÚNG ca canh nó, và bản chép nguyên bản vẫn XANH.
```
Vài đột biến làm đỏ **nhiều hơn một** ca (ví dụ đột biến 1 làm đỏ `l1` *và* `l2`; đột biến "phép so
luôn xanh" làm đỏ `l11` *và* `l2`) — điều kiện của bộ chạy là **ca được khai báo phải nằm trong
danh sách đỏ**, không phải "chỉ duy nhất ca đó đỏ".

### 7.3 HAI LỖI TRONG CHÍNH CÁC PHÉP ĐO CỦA TÔI — ghi lại vì chúng suýt cho kết luận sai

**(a) Đếm thư mục tạm thô ⇒ báo động giả.** Xem §6. Đã sửa thành chụp-trước/so-sau.

**(b) Cổng "cây sạch" của tôi đỏ vì lý do KHÁC ca thử.** Ở lượt chạy đầu, lớp `L` hỏng ở các ca
`W17…W20` với `23505`, và tôi suýt kết luận "đường ghi nghiệp vụ hỏng". Nguyên nhân thật: lớp `B`
đã chèn `tenants (id=1)` tường minh ⇒ bẫy IDENTITY (§5). **Lớp `L` chạy một mình thì XANH** — tức
là ca thử chỉ nhìn thấy bẫy khi có lớp khác chạy trước. Đã sửa theo hai hướng: fixture **dựng bẫy
lên rồi `setval`** (để lớp `L` chạy một mình vẫn đo được), và bẫy được **đo riêng** thành `test_l13`.

> Bài học chung, lặp lại của G17: **một phép đo hỏng và một ca thử yếu trông GIỐNG NHAU** — cùng
> cho ra một dòng xanh. Cách phân biệt duy nhất vẫn là **phá thứ đang canh rồi xem nó có đỏ lên không.**

---

## 8. PHẠM VI — ĐÃ ĐO GÌ, VÀ CÁI GÌ NẰM NGOÀI

**ĐÃ ĐO** (macOS arm64 · Python 3.9.6 · SQLite 3.51.0 · PostgreSQL 16.15 · cụm thử qua **socket
Unix nội máy**, **không mở cổng TCP nào**):

* **23 dạng ghi** qua chính `csdl.ghi()` (vế SQLite) và bản sao khuôn (vế PostgreSQL), **mỗi ca có
  vế đọc kiểm chứng trên kết nối khác**; 19 giống · **4 lệch, cả bốn đã khai báo**.
* Lệch `SELECT` (`-1` vs số dòng) · lệch `RETURNING` (con số CŨ của câu trước, **lỗi phía SQLite**)
  · lệch phương ngữ `WHERE 0` (`42804`).
* **Nguy cơ "`rowcount=1` mà kho trống"** ở chế độ mặc định của `psycopg2` — có đối chứng dương.
* **Bốn kết cục** đo lại qua `ghi()`/`giao_dich()`; **T5 đo được ở cả hai kho**, phán bằng SQLSTATE.
* **Mất cập nhật**: 3 lượt đua (4 tiến trình × 30) + **1 bản TẤT ĐỊNH** (mất đúng 1 ở **cả hai** kho,
  0 lỗi) + **đối chứng dương khuôn nguyên tử** (mất = 0 ở cả hai kho).
* **Bẫy `IDENTITY`** §5, đo trên bảng dịch từ schema sản phẩm.
* 19 chỗ đọc `.rowcount` và 23 chỗ dùng `.lastrowid` trong mã chạy thật — **đã soát từng chỗ**.
* **12/12 đột biến** làm đỏ đúng ca canh nó; bản chép nguyên bản vẫn xanh.
* Vân tay `:5432` TRƯỚC = SAU; cụm thử tự dọn; không xoá rác của làn khác.

**NẰM NGOÀI PHẠM VI** (nói rõ để không ai đọc quá số đo):

* **Lớp phương ngữ `csdl.py` — VẪN CHƯA LÀM** ⇒ **mã nghiệp vụ vẫn chưa chạy được trên
  PostgreSQL**. Lượt này chỉ dịch đúng chừng nào đủ để **đo**: `?` → `$n` (có bỏ qua `?` trong
  chuỗi/định danh/chú thích). **846 dấu `?` trong 294 chuỗi SQL**, `INSERT OR IGNORE`/`REPLACE`,
  `PRAGMA` — **chưa** xử lý.
* **Chưa chuyển một dòng dữ liệu nghiệp vụ nào.** `app/du-lieu/hub.db` không bị đọc/ghi
  (**D-8 nguyên vẹn**).
* **`lastrowid`**: đo được là **vắng mặt** trên `psycopg2` (23 chỗ dùng), nhưng **chưa** đo đường
  thay thế `RETURNING id` trong toàn bộ 23 chỗ đó.
* **Chưa đếm** bao nhiêu chỗ trong `app/` dùng khuôn đọc-rồi-ghi **ngoài** `giao_dich()` (tức là
  đã mất cập nhật im lặng trên SQLite **hôm nay**). §4.1 nêu **hai ví dụ đọc được**, không phải
  một danh sách đầy đủ.
* Bản sao khuôn `ghi()` **không phải** lớp phương ngữ: nó chưa xử lý `PRAGMA`, `OR IGNORE/REPLACE`
  (các ca W4/W6 phải viết SQL riêng cho PostgreSQL), kiểu dữ liệu, `executemany`.
* **Cầu nối `libpq` qua `ctypes` là để ĐO, không phải để dùng làm trình điều khiển sản phẩm.**
  Nó không hỗ trợ tham số nhị phân, `COPY`, `LISTEN/NOTIFY`, pool.
* Chỉ **một hàng** bị tranh chấp; **không** đo deadlock, `NOWAIT`, `SKIP LOCKED`, nhiều hàng, tải
  trộn đọc/ghi, hiệu năng, nhiều máy, replica.
* Tỉ lệ mất cập nhật của bản đua **không tất định** (SQLite 0 → 43 trên 120 qua 3 lượt) — bộ thử
  chốt bằng **bản tất định**, không chốt bằng tỉ lệ.

**KHÔNG LÀM, theo chỉ thị:** không gọi API hãng kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP;
mọi phép đo lớp HTTP chỉ dùng stub `127.0.0.1` cổng 0) · không credentials thật, không `.env`,
không in bí mật ra log · không push, không deploy, không tunnel · không mở `CHO_PHEP_LIVE`, không
sửa cổng sandbox/production trong `app/cau_hinh.py` · không đoán mã trạng thái `110` (D-4) · giữ
chốt D-9 city/area chặn cứng ngoài mock · không chuyển CSDL nghiệp vụ sang PostgreSQL (D-8) ·
**cấm dùng cụm `:5432`** · không dùng Claude, không đổi mô hình · không tự bấm duyệt sandbox.

---

## 9. KẾT LUẬN VÀ KHUYẾN NGHỊ

**D-8 KHÔNG ĐỔI. CSDL NGHIỆP VỤ VẪN LÀ SQLITE. Lượt này KHÔNG chuyển gì.**

Bốn kết luận có số:

1. **`rowcount` của đường ghi thật giống nhau ở 19/23 dạng ghi** — kể cả toàn bộ nhóm `INSERT`,
   `UPDATE` khớp/không khớp, `DELETE`, `OR IGNORE`/`OR REPLACE`, và ghi trong giao dịch bị huỷ.
   **19 chỗ đọc `.rowcount` trong mã chạy thật chưa chỗ nào sai.**
2. **Bốn chỗ lệch, và MỘT trong đó là lỗi phía SQLite**: `INSERT … RETURNING` trả `rowcount` của
   **câu DML trước đó** (đo: sau `DELETE` 2 dòng thì trả `2`). Cộng thêm `SELECT` (`-1` vs số dòng)
   và `WHERE 0` (`42804`).
3. **Nguy cơ lớn nhất không nằm ở con số mà ở chỗ con số ấy không nói lên tính BỀN**: chế độ mặc
   định của `psycopg2` trả `rowcount = 1`, không lỗi, mà kho trống. Và khuôn đọc-rồi-ghi của
   **chính sản phẩm** (`mot()` + `ghi()`) mất cập nhật **im lặng ở CẢ HAI kho** (tất định: mất
   đúng 1, 0 lỗi) — **câu "SQLite từ chối ồn ào" của G17 §2.1 không đúng với đường ghi thật**.
4. **Bẫy `IDENTITY`** biến mọi đường chèn `id` tường minh (di trú/seed/phục hồi) thành một quả mìn
   cho lượt ghi kế tiếp của mã nghiệp vụ (`23505`).

**Việc phải làm TRƯỚC KHI chuyển kho** (lượt này **chưa** làm):

| # | Việc | Vì sao — số ở đâu |
|---|---|---|
| 1 | Lớp phương ngữ `csdl.py` (chặng 1) | §8: 846 dấu `?` / 294 chuỗi, `PRAGMA`, `OR IGNORE/REPLACE` — **mã vẫn chưa chạy được** |
| 2 | Thay **23 chỗ** `.lastrowid` bằng `RETURNING id` | §2.5 — và **đọc `rowcount` của câu `RETURNING` là sai** ở phía SQLite (§2.2) |
| 3 | **Quyết định chế độ chốt** cho `ghi()` trên PostgreSQL | §2.4: mặc định `psycopg2` cho `rowcount=1` mà kho trống |
| 4 | Soát khuôn đọc-rồi-ghi **ngoài `giao_dich()`** — trên **SQLite trước đã** | §4.1: mất cập nhật im lặng **hôm nay**, tất định, ở cả hai kho |
| 5 | `setval` cho mọi sequence sau khi nạp dữ liệu có `id` tường minh | §5: nếu không, lượt ghi kế tiếp `23505` |
| 6 | Giữ nguyên `RETURNING` ra khỏi đường ghi cho tới khi (2) xong | §2.2 |

**Chạy lại toàn bộ bằng chứng của lượt này:**

```bash
python3 app/thu/thu_postgres.py                    ; echo "EXIT=$?"   # → 0 · Ran 55 · OK
python3 trien_khai/postgres/do_ghi_that.py         ; echo "EXIT=$?"   # → 0
python3 trien_khai/postgres/thu_dot_bien_ghi.py    ; echo "EXIT=$?"   # → 0 · 12/12
python3 trien_khai/postgres/van_tay_cum.py         ; echo "EXIT=$?"   # → 0 · vân tay :5432

python3 trien_khai/postgres/van_tay_cum.py --vong -- \
  env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_KEY_1 \
      -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
  sh app/thu/chay_tat_ca.sh                        ; echo "EXIT=$?"   # → 1 vì cổng cây sạch §7.1
```

> Bốn biến `GIT_CONFIG_*` bị bỏ vì môi trường harness xuất chúng **thiếu khoá** (đã ghi ở
> `docs/G17_POSTGRES.md` §5.1): không bỏ thì **mọi** lệnh `git` thoát `128` và `thu_bao_mat.py`
> đỏ giả.

---

## 10. MÃ ĐÃ DÙNG

| Tệp | Trạng thái | Vai trò |
|---|---|---|
| `trien_khai/postgres/libpq_ctypes.py` | **MỚI** (410 dòng) | Cầu nối `libpq` qua `ctypes`: `rowcount` ← `PQcmdTuples`, SQLSTATE, hai chế độ chốt. **Không cài gói nào** |
| `trien_khai/postgres/duong_ghi_pg.py` | **MỚI** (1034 dòng) | Bản sao khuôn `mo/ghi/giao_dich` cho PostgreSQL · cụm thử riêng · 23 ca W · 5 kịch bản T · 2 khuôn mất-cập-nhật · bản bắt tay tất định · bẫy IDENTITY |
| `trien_khai/postgres/do_ghi_that.py` | **MỚI** (296 dòng) | Bộ chạy bằng chứng: 4 bảng W/T/M/D, vân tay `:5432` TRƯỚC/SAU, tự dọn, tự phán (mã thoát) |
| `trien_khai/postgres/thu_dot_bien_ghi.py` | **MỚI** (250 dòng) | 12 đột biến, mỗi cái đòi đúng ca canh nó phải ĐỎ |
| `app/thu/thu_postgres.py` | **sửa** — thêm lớp `L` | **13 ca mới** (42 → **55**), chạy trong hồi quy chung |
| `trien_khai/postgres/van_tay_cum.py` | có sẵn | Vân tay cụm `:5432` (CHỈ ĐỌC) — dùng nguyên, không sửa |
| `trien_khai/postgres/sinh_ddl_pg.py` | có sẵn | Sinh DDL PostgreSQL **từ chính schema đang chạy** — dùng nguyên, không sửa |

`app/csdl.py` · `app/cau_hinh.py` · `app/migrate.py` · `app/server.py` · `app/du-lieu/hub.db`:
**không bị đọc/ghi/sửa** trong lượt này (trừ `cau_hinh.DUONG_DAN_CSDL` được trỏ sang tệp TẠM
trong tiến trình đo, và được trả lại ngay khi `dong()`).
