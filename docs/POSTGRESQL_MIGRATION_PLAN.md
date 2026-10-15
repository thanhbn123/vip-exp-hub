# KẾ HOẠCH CHUYỂN SANG PostgreSQL — trạng thái từng chặng

Chỉ thị G12 mục 6. Cập nhật **15/10/2026** bởi AG-00.
Khảo sát và phương án gốc: **[G12_POSTGRES.md](G12_POSTGRES.md)** (480 dòng, AG-04) — tài
liệu này **không chép lại** nó, chỉ ghi **trạng thái** và **những gì đã đổi** sau mục 5 của G12.

## 0. CHƯA ĐƯỢC PHÊ DUYỆT CHUYỂN

Quyết định **D-8** của anh Thành: *"Tiếp tục SQLite local; thử PostgreSQL trước khi quyết
định triển khai SaaS nhiều người dùng"*. Chỉ thị G12 mục 8: *"Không tự chuyển database
nghiệp vụ đang dùng sang PostgreSQL"*.

**Kho nghiệp vụ hiện tại vẫn là SQLite** (`app/du-lieu/hub.db`) và không có bước nào trong
tài liệu này được chạy lên nó.

## 1. Điều kiện kích hoạt — đừng chuyển vì "nên hiện đại hoá"

Chỉ bắt đầu khi **một trong ba** điều sau thành thật, có bằng chứng:

1. Có **từ hai tiến trình/bản trở lên** ghi vào cùng một CSDL (kể cả một `cron` ghi nền).
2. Cần trần chống lạm dụng **dùng chung** giữa các bản (blocker **B-G11-10** — trần hiện
   sống trong bộ nhớ MỘT tiến trình).
3. Cần replica đọc, **sau khi** đã đo tải đọc thật.

**Phép đo 15/10/2026 củng cố việc GIỮ SQLite, không bác nó:** 8 tiến trình hệ điều hành thật
× 400 phép ghi = 9.600 lượt, **0 khoá hết giờ · 0 giao dịch hỏng · 0 mất cập nhật**
(xem [DATABASE_CONCURRENCY_REPORT.md](DATABASE_CONCURRENCY_REPORT.md)). SQLite chịu được mức
đồng thời này. Chưa chạm điều kiện nào ở trên thì mọi lượt chuyển chỉ là rủi ro không đổi lấy gì.

## 2. Bảy chặng — trạng thái

| Chặng | Việc | Trạng thái 15/10/2026 | Lùi được |
|---|---|---|---|
| **0** | Gom driver về một chỗ | **XONG** — xem §3 | luôn |
| **1** | Lớp phương ngữ trong `csdl.py` (`?`→`$n`, `lastrowid`→`RETURNING`, `INSERT OR IGNORE`→`ON CONFLICT`) | **CHƯA** | luôn |
| **2** | Bộ thử chạy được trên **cả hai** kho | **CHƯA** — hiện 927 ca chỉ chạy trên SQLite | luôn |
| **3** | Migration schema (4 phép sửa, `sinh_ddl_pg.py`) | **một phần** — DDL sinh được, `thu_postgres.py` 21/21 đạt; chưa có lớp phương ngữ nên chưa chạy mã thật trên đó | luôn |
| **4** | Chuyển dữ liệu — chạy khô trên **bản sao**, đối chiếu số dòng từng bảng và tổng tiền từng sổ | **CHƯA** | **ranh giới**: trước dễ, sau khó |
| **5** | Chạy song song chỉ-đọc | **CHƯA** | tắt PostgreSQL |
| **6** | Đổi kho ghi | **CHƯA — cần anh Thành duyệt** | mất dữ liệu ghi từ lúc đổi |

## 3. Chặng 0 — ĐÃ XONG, và nó hoá ra là nợ kiến trúc chứ không phải nợ PostgreSQL

Đo trước: **7 tệp** nạp `import sqlite3`, nhưng **5 trong số đó không mở kết nối nào** —
chúng nạp cả driver chỉ để gọi tên ba kiểu của nó (`Row`, `IntegrityError`, `Error`).
10 chỗ dùng, 6 tệp.

Đã gom về **biên driver** trong `csdl.py`, với tên **nghiệp vụ** chứ không phải tên driver:

| Tên | Là gì | Ánh xạ sang PostgreSQL |
|---|---|---|
| `csdl.Row` | một hàng truy cập theo tên cột | `psycopg.rows.dict_row` |
| `csdl.LoiCSDL` | gốc mọi lỗi tầng CSDL | `psycopg.Error` |
| `csdl.LoiToanVen` | vi phạm UNIQUE/FK/CHECK/NOT NULL | `psycopg.errors.IntegrityError` |
| `csdl.LoiVanHanh` | CSDL bị khoá, hết giờ chờ | **KHÔNG một-một** — ca "database is locked" của SQLite tương ứng `SerializationFailure`/`LockNotAvailable`. **Phải đo lại, không suy ra** |
| `csdl.ket_noi()` | kết nối thô cho migrate/công cụ | `psycopg.connect()` |
| `csdl.cau_sql_du()` | một câu SQL đã trọn chưa | không có tương đương — xem §4 |

Nghiệm thu: `grep "^import sqlite3" app/*.py` chỉ còn `csdl.py`.
Chốt chặn: `app/thu/thu_bien_driver.py` (5 ca, dò bằng AST). Gỡ vá ra thì ca a1 hỏng.

## 4. Những gì mục 5 của G12 ĐỔI trong kế hoạch này

### 4.1 Rủi ro "trigger huỷ cả giao dịch" — đã có lớp chắn

AG-04 ghi rủi ro: SQLite `RAISE(ABORT)` huỷ **câu**, PostgreSQL `RAISE EXCEPTION` huỷ **cả
giao dịch** — nên câu ghi sau một trigger-chặn sẽ **im lặng không vào** bên PostgreSQL.
AG-04 đề xuất chặn bằng *"`SAVEPOINT` quanh mọi lượt ghi có thể bị trigger chặn"*.

**Lớp đó nay đã có:** `csdl.giao_dich()`. Tầng ngoài dùng `BEGIN IMMEDIATE`, tầng lồng dùng
`SAVEPOINT`, lồng bao nhiêu tầng cũng được. Ca `thu_giao_dich.b2` **ghi ra điểm vấp** (nuốt
`LoiToanVen` rồi đi tiếp thì câu sau vẫn commit trên SQLite) và ca `b3` ghi cách dùng đúng.

Việc còn lại ở chặng 1–2: **đi soát từng chỗ ghi có thể bị trigger chặn** và bọc `giao_dich()`.
§12.2 bước 4 đã quét: 30 khối ghi, đã vá 2 khối tài chính nặng nhất; **còn lại chưa vá** —
`don_hang.py:944` (3 câu) · `tai_chinh.py:673` (2 câu) · `usage.py:220` · `don_hang.py:854`
(gọi `_ghi_lich_su`) · `tai_chinh.py:385` `ghi_nhat_ky` (đọc-rồi-ghi móc băm).

### 4.2 Chặng 3 phải mang theo `chay_ddl_trong_giao_dich`

Phát hiện 15/10: `kn.executescript()` **tự COMMIT** giao dịch đang mở. Migration cũ nạp 5
khối DDL G07–G11 qua nó, nên **chưa bao giờ nguyên tử**. Đã thay bằng
`migrate.chay_ddl_trong_giao_dich()`, tách câu bằng `csdl.cau_sql_du`
(`sqlite3.complete_statement`), **không** bằng `ddl.split(";")` — khối
`CREATE TRIGGER ... BEGIN ...; END;` có `;` bên trong.

**Việc cho chặng 1:** `psycopg` không có `complete_statement`. Lớp phương ngữ phải thay nó
bằng một bộ tách khác, và bộ tách đó phải **xử đúng `$$ ... $$`** của hàm/trigger PostgreSQL
— chỗ này khó hơn `BEGIN ... END` của SQLite. Ca `thu_migrate_dong_thoi.b3` là khuôn để viết
ca tương đương bên kia.

### 4.3 Khoá migration xuyên tiến trình — đã có, nhưng là khoá của SQLite

`migrate.chay()` nay lấy khoá bằng `BEGIN IMMEDIATE` trên chính CSDL: nó vừa là khoá xuyên
tiến trình, vừa là ranh giới lùi cho cả DDL, vừa là chốt đọc-rồi-làm (đọc lại phiên bản
**bên trong** khoá). Nghiệm thu: 8 tiến trình → đúng 1 nâng cấp, 7 nhường, 0 lỗi.

**Bên PostgreSQL phải đổi cách:** dùng `pg_advisory_lock` hoặc một bảng khoá, vì
`BEGIN IMMEDIATE` là cú pháp SQLite. Và PostgreSQL **có DDL giao dịch thật**, nên phần
"ranh giới lùi cho DDL" tự nhiên có — nhưng phần "khoá" thì phải viết lại.

### 4.4 `migrate.sao_luu()` vẫn là `Connection.backup()` của SQLite

Chưa đổi. AG-04 đã cảnh báo đúng: sau chuyển, hàm này **vô dụng mà vẫn chạy trót lọt** → tưởng
có đường lùi, thật ra không. Chặng 3 phải đổi sang `pg_dump` và **giữ phép kiểm bản sao > 0
byte** như bản hiện tại đang làm (phép kiểm đó sinh ra sau một ca ghi đè im lặng).

## 5. Ba thứ dễ mất nhất khi chuyển dữ liệu (chặng 4)

1. **Bút toán `tc_but_toan` / `tc_nhat_ky`** — bất biến theo §17, không ghi lại được. Mất là mất.
2. **Bí mật đã mã hoá** (`credentials_ma_hoa`, `webhook_secret_ma_hoa`) — `TEXT` mang
   `v3$<key_id>$nonce$ct`. Chuyển sai mã hoá ký tự là **hỏng không khôi phục được**: khoá còn
   đó nhưng bản mã thành rác. **Chặng 4 phải giải thử một bản ở đầu bên kia trước khi tin
   bất cứ gì.**
3. **`wh_su_kien.payload_tho`** — `BLOB`→`BYTEA`, chỗ nhị phân dễ bị hiểu thành chuỗi nhất.

Thêm hai thứ không mất dữ liệu nhưng làm hỏng ngay sau chuyển:
`AUTOINCREMENT`→`IDENTITY` phải `setval` mọi chuỗi sinh số (thiếu thì bản ghi mới đụng khoá
chính của bản ghi cũ), và **mọi mốc thời gian đang là `TEXT`** — giữ nguyên `TEXT` ở chặng 4,
đổi sang `timestamptz` là **một việc riêng về sau**, không gộp.

## 6. Môi trường PostgreSQL để thử — đã dựng, hoàn toàn rời

`app/thu/thu_postgres.py` tự `initdb` một cụm **tạm**, tự `pg_ctl stop`, tự xoá.
**Hai chốt chặn** để không chạm cụm hệ thống: ca `d1` từ chối cổng 5432, ca `d2` từ chối cụm
hệ thống. Chỉ thị G12 mục 9 (*"không sửa `vip_customs*` hoặc database khác"*) được giữ bằng
hai ca đó, không bằng lời dặn.

**Đổi 15/10:** bộ này trước đây **TẮT mặc định** (phải đặt `VIP_THU_POSTGRES=1`), lý do ghi là
*"~1,5–3 giây"*. Hậu quả đo được: nó hiện dấu ✓ trong **mọi** lượt hồi quy mà chạy **đúng 0
ca** — ai đọc "27 bộ đạt" đều tưởng PostgreSQL đã được phủ. Đo lại: cả 21 ca chạy hết trong
**1,405 giây**. Nay **BẬT mặc định**; ai cần nhanh thì `VIP_THU_POSTGRES=0`.
Và bộ chạy nay có phán quyết thứ ba **BỎ QUA**, không gộp vào ĐẠT.

Hai lệnh cần có trên máy: `initdb`, `pg_ctl`, `psql`. Thiếu thì bộ thử tự bỏ qua kèm lý do
(`brew install postgresql@16`). Đo được trên Mac mini 15/10/2026: có đủ.

## 7. Cần anh Thành quyết trước khi đi tiếp

| Việc | Vì sao cần anh |
|---|---|
| Chạy chặng 1–2 (lớp phương ngữ + bộ thử hai kho) | Không đụng dữ liệu, nhưng là **vài ngày việc**. Chỉ nên làm nếu đã thấy một trong ba điều kiện §1 |
| Chạy chặng 4 (chuyển dữ liệu, dù chỉ trên bản sao) | Đây là **ranh giới lùi**. Cần anh biết trước |
| Đổi kho ghi (chặng 6) | Chỉ thị mục 8 cấm tự làm |

**Khuyến nghị của AG-00:** chưa chuyển. Số đo đồng thời cho thấy SQLite còn dư sức cho mô
hình hiện tại, và chặng 0 vừa xong đã mang lại gần hết lợi ích kiến trúc mà không mang theo
bất kỳ rủi ro dữ liệu nào.
