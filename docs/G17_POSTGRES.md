# G17 · AG-05 — PostgreSQL: GIAO DỊCH · MIGRATION · DIỄN TẬP

> **AI-ASSISTED, KHÔNG PHẢI NGƯỜI SOÁT.** Mọi số trong tài liệu này do một tác tử AI chạy
> trên máy này. `docs/BAN_GIAO.md` §2: **"AI review không phải human review. Bộ thử xanh
> không phải lời cho phép."** Tài liệu này **không** cho phép chuyển kho.

**Tác tử:** AG-05 (DeepSeek, trong Orca) · **Ngày đo:** 15/10/2026
**Nền:** `integration/g16` @ `98baeb357214d41a9380467fde2fee2b94fd31cc`
**Máy đo:** Darwin arm64 · Python 3.9.6 · SQLite 3.51.0 · PostgreSQL 16.15 (Homebrew)

> **MỐC CÂY — tự đo, đừng tin tài liệu** (`BAN_GIAO.md` §7.3: tệp này không ghi SHA của
> chính commit chứa nó). Người đọc tự chạy:
> ```bash
> find app gateway thu_frontend thu_giao_dien trien_khai -type f \
>   \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
>   | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
> ```
> Vân tay cây lúc đo: `d9f1e19fb72a8b57d8a4e897fbf82ee843105367048b08949005c83da738f48f`

---

## 0. ĐÂY LÀ CÁI GÌ — và KHÔNG phải cái gì

**Quyết định D-8 vẫn nguyên vẹn.** Tài liệu này là **số đo để quyết**, không phải một lượt
chuyển kho. `app/csdl.py`, `app/migrate.py`, `app/server.py` **không bị sửa một dòng nào**.
`app/du-lieu/hub.db` **không bị đọc, không bị ghi, không bị chuyển**. **CSDL nghiệp vụ vẫn là
SQLite.**

| Tài liệu này LÀ | KHÔNG phải |
|---|---|
| Số đo cho ba hạng mục G17/AG-05: giao dịch · migration · diễn tập | Một lượt chuyển CSDL |
| Danh sách ca thử **chạy được trong hồi quy** và **làm đỏ được** | Một bản kế hoạch đã thực hiện |
| Bằng chứng cụm `:5432` **không bị đụng** | Một đề xuất mở cổng hay lên production |

Ba tệp được ghi trong lượt này (`git status --short`):

```
 M app/thu/thu_postgres.py            (thêm lớp F…K: 17 ca mới, 25 → 42 ca)
?? trien_khai/postgres/van_tay_cum.py  (MỚI: vân tay cụm, chỉ đọc)
?? trien_khai/postgres/thu_dot_bien.py (MỚI: chứng minh ca thử làm đỏ được)
```
Không tệp nào khác bị đụng. Không push, không deploy, không mở cổng ra Internet.

---

## 1. CHỐT CHẶN: CỤM `:5432` KHÔNG BỊ ĐỤNG — và đây là PHÉP ĐO, không phải lời khai

Máy này đang chạy một cụm PostgreSQL hệ thống ở `:5432` giữ CSDL của **dự án khác**. Mọi
phép đo của lượt này chạy trên **cụm riêng**, và điều đó được **đo bằng vân tay TRƯỚC/SAU**,
không bằng câu "tôi không đụng".

### 1.1 Cụm riêng — tham số cụ thể

| Thứ | Giá trị | Ở đâu |
|---|---|---|
| Cổng cụm thử | **55432** (đối chứng dương của lớp F: **55433**) | `VHPG_CONG`, mặc định trong `Cum.__init__` |
| Thư mục dữ liệu | `mkdtemp(prefix="vhpg-thu-")` — **không** phải `/opt/homebrew/var` | `app/thu/thu_postgres.py::Cum.dung` |
| Socket Unix | `mkdtemp(prefix="vhpg.", dir="/tmp")` → `/tmp/vhpg.XXXX` | như trên |
| TCP | **KHÔNG MỞ CỔNG NÀO** — `listen_addresses=''`, chỉ nói qua socket Unix | `pg_ctl -o "-p … -k … -c listen_addresses=''"` |
| `initdb` | `LANG=C LC_ALL=C initdb --locale=C --encoding=UTF8` | đã vấp 2 lần ở G12, ghi lại trong `dung_cum_thu.sh` |
| Dọn | `pg_ctl stop` rồi `shutil.rmtree` — **KHÔNG `pkill`/`killall`** | `CLAUDE.md` §16.7: `pkill -f postgres` sẽ giết luôn cụm `:5432` |

Đo cuối lượt: `/tmp/vhpg.*` còn **0**, `vhdt-*`/`vhpg-thu-*` còn **0** — cụm thử tự dọn sạch.

### 1.2 Vân tay cụm `:5432` — TRƯỚC = SAU

Công cụ: `trien_khai/postgres/van_tay_cum.py` (**CHỈ ĐỌC** — mọi câu lệnh là `SELECT`/`SHOW`).
Vân tay gồm: PID postmaster · `data_directory` · giờ postmaster khởi động · phiên bản máy chủ
· **danh sách CSDL** · số CSDL · PID đang nghe TCP.

```bash
python3 trien_khai/postgres/van_tay_cum.py ; echo "EXIT=$?"      # → EXIT=0
```

| Trường | TRƯỚC | SAU |
|---|---|---|
| PID postmaster | `58873` | `58873` |
| `data_directory` | `/opt/homebrew/var/postgresql@16` | *(giống)* |
| postmaster bắt đầu | `2026-10-09 10:24:22.104803+07` | *(giống)* |
| phiên bản máy chủ | `16.15 (Homebrew)` | *(giống)* |
| số CSDL | `6` | `6` |
| danh sách CSDL | `postgres template0 template1 vip_customs vip_customs_g16 vip_customs_test` | *(giống)* |
| PID nghe TCP `:5432` | `['58873']` | `['58873']` |

**Phép đo này được bọc quanh TOÀN BỘ lượt hồi quy**, không chỉ quanh một phép lẻ:

```bash
python3 trien_khai/postgres/van_tay_cum.py --vong -- \
  env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_KEY_1 \
      -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
  sh app/thu/chay_tat_ca.sh
echo "EXIT=$?"        # → EXIT=0
```
Kết quả in ra: `VÂN TAY :5432 — TRƯỚC = SAU. Lượt đo KHÔNG đụng cụm hệ thống.`

### 1.3 TỰ KIỂM BỎ ĐỒ cho chính phép đo vân tay

Một `so_sanh` luôn trả `True` thì bảng ở §1.2 là **đồ trang trí**. Ba ca canh điều đó:

| Ca | Phá gì | Kết quả |
|---|---|---|
| `G.test_g2_van_tay_phai_doc_duoc_that` | cụm không đọc được ⇒ hai vân tay rỗng "bằng nhau" vô nghĩa | đòi phải có PID + `data_directory` + danh sách CSDL chứa `vip_customs*` |
| `G.test_g3_phep_so_phat_hien_duoc_khac_biet` | tiêm khác biệt vào bản sao vân tay | đổi `pid`, `danh_sach_csdl`, `postmaster_bat_dau`, `phien_ban_may_chu` — **cả 4 đều bị phát hiện**; và một lượt chụp không đọc được cụm **không** được phán "giống" |
| `thu_dot_bien.py` đột biến 7 | `so_sanh` sửa thành `return True, []` | ca `g3` **ĐỎ** — đúng |

Đo trực tiếp ngoài bộ thử (`--so` hai tệp JSON): thêm một CSDL vào bản sao → `exit=1`;
đổi PID → `exit=1`; một bên không đọc được cụm → `exit=1`.

### 1.4 Ca TỪ CHỐI cổng 5432 — chạy THẬT, không chỉ kiểm hàm

`D.test_d1` chỉ kiểm hàm `_kiem_cong_an_toan` ở tầng đơn vị. Lớp `F` chạy **đúng lệnh đó
trong một tiến trình riêng** với `VHPG_CONG=5432`:

```bash
env -u VHPG_SOCKET VHPG_CONG=5432 python3 app/thu/thu_postgres.py
echo "EXIT=$?"     # → EXIT=1
```
```
AssertionError: TỪ CHỐI chạy trên cổng 5432: đó là cụm PostgreSQL hệ thống của máy này,
đang giữ CSDL của dự án khác (vip_customs…). Bộ thử phải dùng cụm riêng.
Ran 0 tests in 0.070s
FAILED (errors=1)
```

Đo được đầy đủ trong `F.test_f1`: thoát **khác 0** · có chữ `TỪ CHỐI` · có chữ `vip_customs`
(lời từ chối **nói rõ** cụm đó giữ CSDL của ai) · `Ran 0 tests` (từ chối **trước** khi chạy ca
nào) · `TMPDIR` riêng **rỗng** (không dựng thư mục dữ liệu) · không có `/tmp/vhpg.*` mới ·
**vân tay `:5432` không đổi**.

**ĐỐI CHỨNG DƯƠNG** (`F.test_f2`): CÙNG lệnh đó, chỉ đổi cổng sang `55433` → **không** từ chối,
`Ran 4 tests`, `EXIT=0`. Thiếu vế này thì `f1` chỉ nói được "lệnh đó thoát khác 0" — mà một
lỗi cú pháp cũng thoát khác 0. Đột biến 1 của `thu_dot_bien.py` (bỏ `_kiem_cong_an_toan`) làm
`f1` **ĐỎ** — chứng minh chốt chặn là thứ đang chịu lực.

---

## 2. GIAO DỊCH — BỐN KẾT CỤC, ĐO RIÊNG TỪNG CÁI

Bốn thứ này hay bị gọi chung là "lỗi CSDL", nhưng cách xử lý khác hẳn nhau. Ba cái đầu
**tự báo**; cái thứ tư **im lặng** — nên nó là thứ đáng đo nhất, và mọi phép đo ở đây đều làm
**đối chiếu cuối lượt** (số lượt *tin* đã chốt so với số *thật* trong CSDL), không chỉ đếm lỗi.

| Kết cục | Nghĩa | Xử thế nào | Ca thử | Đo được |
|---|---|---|---|---|
| `CHỐT_THÀNH_CÔNG` | đã ghi thật, thấy được từ tiến trình khác | xong | `e1`, `j1`, `j4` | 120 lượt chốt / **120** thật / **mất 0** / lỗi 0 |
| `KHOA_HẾT_GIỜ` | **chưa** ghi gì, giành khoá thất bại | thử lại được, an toàn | `e4` | SQLSTATE **`55P03`** `lock_not_available`; hàng vẫn nguyên mốc `7` ⇒ **không ghi gì** |
| `GIAO_DỊCH_HỎNG` | **chưa** ghi gì, vi phạm ràng buộc/trigger | thử lại **VÔ ÍCH** | `e4` | **`P0001`** rồi **`25P02`**; câu SAU trigger **không chạy**; **0** dòng vào bảng (cả dòng chèn TRƯỚC trigger cũng bị lùi) |
| `MẤT_CẬP_NHẬT` | **đã ghi** nhưng mất một lượt ghi khác | **KHÔNG TỰ BÁO** | `e2`, `j2` | xem §2.1 |

Phán bằng **SQLSTATE**, không bằng chữ trong thông báo: `psql -v VERBOSITY=verbose` để stderr
mang mã, vì chữ đổi theo phiên bản/locale còn mã thì không.

### 2.1 PHÁT HIỆN LỚN — và nó đứng vững qua NĂM lượt đo độc lập

Cùng **một khuôn đọc-rồi-ghi ngây thơ** (đọc ở một kết nối, ghi lại giá trị đã đọc), chạy
bằng **TIẾN TRÌNH THẬT** — không bằng thread, vì khoá ghi của Python chỉ phủ MỘT tiến trình,
đo bằng thread là đo chính cái khoá đó rồi kết luận "an toàn" cho cả nó không phủ:

| Kho | Tham số | Chốt thành công | Giá trị THẬT | **MẤT CẬP NHẬT** | Lỗi báo ra |
|---|---|---|---|---|---|
| **PostgreSQL 16.15** | 4 tiến trình × 30 phép = 120, hàng `g17_dem(id=1)` | 120 | 55 | **65 (54,2%)** | **0** |
| **SQLite 3.51.0** | 4 tiến trình × 30 phép = 120, CÙNG khuôn | 30 | 30 | **0** | **90 lượt từ chối ồn ào** (`database is locked`) |

**PostgreSQL im lặng mất; SQLite từ chối ồn ào.** Nghĩa là chuyển kho mà giữ nguyên khuôn
đọc-rồi-ghi là **đổi một lỗi ồn ào lấy một lỗi im lặng** — tệ hơn cho tiền.

**Tỉ lệ mất KHÔNG tất định — và tài liệu này nói rõ điều đó.** Năm lượt đo cùng ngày, cùng
cụm, mỗi lượt **120 phép**:

| Lượt đo | Tiến trình × phép | Chốt | Thật | Mất | % | Lỗi |
|---|---|---|---|---|---|---|
| `thu_postgres.py` j2 | 3 × 40 | 120 | 51 | 69 | 57,5% | 0 |
| `thu_postgres.py` j2 | 3 × 40 | 120 | 68 | 52 | 43,3% | 0 |
| `thu_postgres.py` j2 | 4 × 30 | 120 | 62 | 58 | 48,3% | 0 |
| `thu_postgres.py` j2 (lượt chốt, §2.1) | 4 × 30 | 120 | 55 | 65 | 54,2% | 0 |
| `dien_tap_chuyen.py` §1b | 4 × 30, **đọc bằng tiến trình `psql` RIÊNG** | 120 | 35 | 85 | **70,8%** | 0 |

Con số **70,8%** trong chỉ thị G17 đến từ dòng cuối — nó cao hơn vì `dien_tap_chuyen.py` dùng
khuôn **ngây thơ hơn nữa**: mỗi lượt ĐỌC là một tiến trình `psql` RIÊNG (tự chốt ngay), rồi
lượt GHI mở một tiến trình khác, nên cửa sổ tranh chấp rộng hơn hẳn.

> **Điều bất biến qua cả năm lượt: `mất > 0` và `lỗi == 0`.** Tỉ lệ phần trăm là số của một
> cuộc đua, **đừng trích nó như một hằng số**. Ca thử `j2` khẳng định đúng hai điều bất biến
> đó, không khẳng định phần trăm.

### 2.2 ĐỐI CHỨNG ÂM cho đồng hồ đo — HAI khuôn ĐÚNG

Một đồng hồ luôn báo "mất" thì cũng "đạt" ở bảng trên. Nên có hai vế đối chứng, đúng hai
khuôn mà chỉ thị G17 nêu tên:

| Ca | Khuôn ĐÚNG | Tham số | Mất cập nhật |
|---|---|---|---|
| `j1` | cộng ở **TẦNG CÂU**: `UPDATE … SET x = x + 1` | 4 tiến trình × 30 phép | **0** (chốt 120 / thật 120) |
| `j4` | **`SELECT … FOR UPDATE`** giữ khoá HÀNG trước khi đọc | 4 tiến trình × 30 phép | **0** (chốt 120 / thật 120) |

`j4` quan trọng hơn `j1` ở một điểm: `j1` sửa được vì phép cộng nằm gọn trong **MỘT câu**;
`FOR UPDATE` sửa được cả những chỗ **luật nghiệp vụ nằm giữa lượt đọc và lượt ghi** (đối soát,
tính phí, trừ hạn mức) — những chỗ `x = x + 1` không thay thế được.

Đột biến 4 của `thu_dot_bien.py` (viết lại khuôn ngây thơ thành nguyên tử) làm `j2` **ĐỎ** —
chứng minh `j2` thật sự nhìn vào khuôn đọc-rồi-ghi, không phải vào một hằng số.

### 2.3 Bản TẤT ĐỊNH — để kết luận không phụ thuộc tải máy

`e2`/`e3` ép thứ tự thay vì đua: hai phiên CÙNG đọc `gia_tri=0`, **bắt tay qua tệp mốc** cho
chắc cả hai đã đọc xong, rồi cả hai ghi `0 + 1 = 1`.

* **PostgreSQL**: hai giao dịch chốt thành công, giá trị cuối **1** ⇒ **mất đúng một cập nhật,
  không một dòng lỗi nào**.
* **SQLite**: **1 lượt chốt · 1 lượt bị TỪ CHỐI** (`SQLITE_BUSY_SNAPSHOT` — trả NGAY,
  `busy_timeout` không chờ) · giá trị cuối **1** · **mất 0**.

Bản đua (`j2`) phụ thuộc lịch trình của hệ điều hành; bản bắt tay (`e2`/`e3`) thì không. Có cả
hai là để một bên canh bên kia.

---

## 3. MIGRATION — BA TÍNH CHẤT, MỖI CÁI CÓ ĐỐI CHỨNG

### 3.1 Khoá tư vấn: đúng MỘT tiến trình migration

Hai tiến trình `psql` **THẬT**, chạy chồng nhau. Phép đo **TẤT ĐỊNH**, không dựa vào may rủi
lịch trình: hai tiến trình **bắt tay qua một bảng hàng rào** (`hang_rao`) trước khi vào giao
dịch nâng cấp, và `pg_sleep(0.4)` giữ cửa sổ đọc-rồi-ghi mở đủ rộng.

| Ca | Kịch bản | nâng cấp | nhường | lỗi | phiên bản cuối | bảng `bang_v8` |
|---|---|---|---|---|---|---|
| `h1` | **CÓ** `pg_advisory_xact_lock(991204)` | **1** | **1** | **không** | `2\|8` | 1 |
| `h2` (ĐỐI CHỨNG ÂM) | **BỎ** đúng một dòng xin khoá, giữ nguyên mọi thứ khác | 1 | **0** | **`23505`** unique_violation | `2\|8` | 1 |

Hai kết quả **KHÁC NHAU** ⇒ phép đo ở `h1` thật sự chạm tới khoá. Đột biến 2 của
`thu_dot_bien.py` (bỏ dòng xin khoá) làm `h1` **ĐỎ** — cùng kết luận, kiểm độc lập.

**Vì sao phải xin khoá:** `migrate.chay()` đọc phiên bản rồi mới nâng. Trên SQLite chuyện hai
tiến trình cùng nâng bị chặn bằng khoá ghi của **tệp**; trên PostgreSQL **không có gì chặn** —
phải xin khoá tường minh. Bản dịch `migrate.py` sang PostgreSQL **chưa làm** (xem §6).

### 3.2 DDL lùi sạch khi hỏng giữa khối

Nạp **DDL THẬT của dự án** (sinh từ chính `csdl.SCHEMA` + 5 hằng `DDL_G07…G11` đang chạy,
không chép tay) trong MỘT giao dịch, rồi chèn một câu SAI vào **cuối** khối:

| Ca | Kịch bản | Số bảng | Số cột | `tenants` (đứng TRƯỚC câu sai) |
|---|---|---|---|---|
| `i1` (ĐỐI CHỨNG DƯƠNG) | `BEGIN; DDL; COMMIT;` | **47** | **431** | có |
| `i2` (ĐỐI CHỨNG ÂM) | `BEGIN; DDL; CREATE TABLE cau_sai_co_y (id int, ); COMMIT;` | **0** | **0** | **KHÔNG còn** |

SQLSTATE của câu sai: **`42601`** syntax_error. Bảng `tenants` đứng **TRƯỚC** câu sai mà cũng
biến mất ⇒ rollback **nguyên tử**, không nửa vời.

> **Đừng phán bằng mã thoát `psql` ở đây.** `ON_ERROR_STOP=0` nên `psql` báo lỗi rồi đi tiếp và
> `COMMIT` trên giao dịch đã hỏng trở thành `ROLLBACK` — **mã thoát là 0**. Phán bằng mã thoát
> ở chỗ này là phán sai.

### 3.3 Sao lưu / khôi phục — số dòng TỪNG BẢNG, TỔNG TIỀN, payload NHỊ PHÂN

`pg_dump -Fc` → `pg_restore` sang một CSDL khác. **Không đếm bảng** — một bản khôi phục RỖNG
cũng khớp số bảng. Phép so gồm bốn thứ:

| Thứ đo | Bản gốc | Bản khôi phục |
|---|---|---|
| Số dòng **từng bảng** (47 bảng) | 47 mục | **giống hệt** |
| Số **cột** | 431 | **431** |
| Bút toán: `count\|sum(so_tien_dong)` | `1\|777000` | **`1\|777000`** |
| `md5(payload_tho)` của một payload **NHỊ PHÂN** | `c372dcc8d171…` | **giống hệt** |

Ba vế **TỰ KIỂM BỎ ĐỒ** cho phép so này (`k2`, `k3`):

* Thêm một bảng vào bản khôi phục → phép so **thấy** (đột biến 5 làm `k1` **ĐỎ**).
* Xoá một dòng `wh_su_kien` ở bản khôi phục → phép so **thấy** cả số dòng lẫn md5
  (đột biến 6 làm `k1` **ĐỎ**).
* Lệch **đúng 1 đồng** ở trường tiền, hoặc đổi md5 → phép so **thấy**.

Và `k3`: bất biến bút toán (§17) **đi qua được `pg_dump`/`pg_restore`** — `UPDATE` và `DELETE`
trên `tc_but_toan` ở **bản khôi phục** đều **BỊ TỪ CHỐI**. Nghĩa là nếu bản khôi phục lệch
tiền thì **không có đường sửa lén**; phải khôi phục lại. Đó là vế làm cho phép so tiền ở `k1`
có nghĩa.

**Đường lùi GIẢ phải bị chặn trước khi chuyển:** `migrate.sao_luu()` hiện là
`sqlite3.Connection.backup()`. Trên PostgreSQL nó **không có tương đương**, và tệ hơn — nó
vẫn chạy trót lọt rồi để lại một tệp "bản sao" không chứa gì của PostgreSQL. Việc thay nó
bằng `pg_dump` **chưa làm** (xem §6).

---

## 4. DIỄN TẬP — SCHEMA THẬT 47 BẢNG TRONG MỘT GIAO DỊCH

| Bước | Số bảng | Số cột |
|---|---|---|
| **TRƯỚC** (CSDL mới tinh) | **0** | **0** |
| **SAU** (`BEGIN; DDL; COMMIT;`) | **47** | **431** |
| SQLite đang chạy (đối chiếu) | **47** | **431** |

Đối chiếu **tên bảng** và **tên cột** giữa hai kho — `a3`/`a4` so **tập tên**; **KHÔNG** so
kiểu, **KHÔNG** so ràng buộc, **KHÔNG** so giá trị mặc định, **KHÔNG** so ngữ nghĩa.

**Chốt chống ca "DDL rỗng cũng đạt":** `i1` đòi `b_sau >= 40`. Đột biến 3 của
`thu_dot_bien.py` (đặt `DDL_PG = ""`) làm `i1` **ĐỎ** — một khối DDL rỗng nạp bao giờ cũng
"đạt" nếu thiếu chốt này.

### 4.1 PHẠM VI ĐO ĐƯỢC: 47 ≠ 49

`i3` ghim một con số mà các báo cáo trước chỉ nói bằng lời:

```
47 bảng trong bộ DDL · 49 bảng toàn bộ app/ · NGOÀI bộ DDL: don_mat_hang, han_muc_nhap_thang
```

Hai bảng `don_mat_hang` và `han_muc_nhap_thang` do **`app/migrate.py`** tạo ở **đường ALTER**
(`nang_len_v7`/`nang_len_v8`), **không** nằm trong 6 hằng DDL mà `sinh_ddl_pg.py` đọc. Nghĩa là:

* Phép diễn tập 47 bảng là **schema NỀN** — đúng như chỉ thị G17 ghi.
* Một lượt diễn tập **đầy đủ** phải là **49 bảng**, và đường migration phải được diễn tập
  riêng. **Lượt này CHƯA làm.**
* `i3` **KÊU** nếu ai thêm bảng mới mà quên đưa vào một trong hai đường — phạm vi không trôi lặng.

---

## 5. BẰNG CHỨNG — LỆNH · MÃ THOÁT · SỐ CA · SỐ BỎ QUA

Mọi mã thoát dưới đây lấy **ngay sau lệnh, trước mọi đường ống**. `set -e` không được dùng để
che: mỗi lệnh ghi kết quả ra tệp rồi mới `echo "EXIT=$?"`.

| # | Lệnh | Mã thoát | Số ca | Bỏ qua |
|---|---|---|---|---|
| 1 | `python3 app/thu/thu_postgres.py` | **0** | **42** (`Ran 42 tests … OK`) | **0** |
| 2 | `python3 trien_khai/postgres/van_tay_cum.py --vong -- env -u GIT_CONFIG_* sh app/thu/chay_tat_ca.sh` | **0** | python **1301**/36 bộ · frontend **56 + 36** · E2E **41/41** · **0 bộ hỏng** | 0 |
| 3 | `python3 trien_khai/postgres/dien_tap_chuyen.py` | **0** | **26** đạt · 0 hỏng · 0 bỏ qua | 0 |
| 4 | `python3 trien_khai/postgres/thu_dot_bien.py` | **0** (×3 lượt liên tiếp) | **7/7** đột biến làm đỏ đúng ca | 0 |
| 5 | `python3 trien_khai/postgres/van_tay_cum.py` | **0** | vân tay `:5432` (bảng §1.2) | — |
| 6 | `env -u VHPG_SOCKET VHPG_CONG=5432 python3 app/thu/thu_postgres.py` | **1** *(đúng: phải từ chối)* | `Ran 0 tests` | — |
| 7 | `python3 trien_khai/postgres/thu_dot_bien.py` — đối chứng bản chép nguyên bản | **0** | 6/6 lớp mới xanh trước khi đột biến | 0 |

**SHA tệp (sha256):**

```
eda19f6e00874768ce78693b1a99d0b59c1f8be08b5285c8e0eb627b4471cc02  app/thu/thu_postgres.py
a5da78f26e3ae1e2af3eabb725a9a74aa620a7aa0482cda670a4465c23736f25  trien_khai/postgres/van_tay_cum.py
b49d4ad3888ab03e8e2aaca4fbac13d8ef130032e63cfb6c43fa40c70f1e117e  trien_khai/postgres/thu_dot_bien.py
```
Nền: `integration/g16` @ `98baeb357214d41a9380467fde2fee2b94fd31cc`.

### 5.1 MỘT PHÁT HIỆN VỀ MÔI TRƯỜNG, KHÔNG PHẢI VỀ MÃ

Lượt chạy `chay_tat_ca.sh` **đầu tiên** trong phiên này trả **`EXIT=1`**, hỏng đúng một ca:

```
FAIL: test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git (thu_bao_mat.F_KhongTutVeSoDoYeu)
AssertionError: 128 != 0 : git KHÔNG chặn app/du-lieu/khoa-noi-bo.key — khóa có thể lọt vào git
```

**Nguyên nhân là môi trường harness, không phải mã.** Hợp công cụ Orca xuất
`GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0`/`GIT_CONFIG_KEY_1` (chỉ có
`GIT_CONFIG_VALUE_0/1=false`), nên **mọi** lệnh `git` thoát **128**:

```bash
git check-ignore app/du-lieu/khoa-noi-bo.key ; echo "EXIT=$?"
#  VỚI env harness   → EXIT=128
#  KHÔNG có env      → app/du-lieu/khoa-noi-bo.key   EXIT=0
```

Bỏ đúng bốn biến đó thì `thu_bao_mat.py` **57 ca · OK · EXIT=0**, và toàn bộ hồi quy **xanh**
(dòng 2 ở bảng trên). Đây là **vấn đề của môi trường chạy**, không phải của mã dự án — nhưng
nó làm mọi lượt hồi quy trong phiên này **đỏ giả** cho tới khi được nhận ra.

---

## 6. TỰ KIỂM BỎ ĐỒ — ĐỘT BIẾN

`trien_khai/postgres/thu_dot_bien.py` chép dự án sang thư mục **TẠM** (bỏ `node_modules`,
`.git`), phá **đúng MỘT** thứ, rồi đòi **đúng lớp ca thử canh thứ đó** phải **ĐỎ**.

```
── ĐỐI CHỨNG: bản chép nguyên bản, chạy cả 6 lớp mới
   ✓ F_ChotChanCong5432ThatSu · G_VanTayCumHeThong · H_MigrationKhoaTuVan
   ✓ I_DDLNguyenTuTruocSau · J_DoiChieuMatCapNhat · K_SaoLuuKhoiPhuc
── ĐỘT BIẾN
   ✓ Bỏ chốt chặn cổng 5432                          → ĐỎ, đúng
   ✓ Bỏ dòng xin khoá tư vấn khi migration           → ĐỎ, đúng
   ✓ DDL rỗng (nạp 'đạt' mà không tạo gì)            → ĐỎ, đúng
   ✓ Khuôn đọc-rồi-ghi viết lại thành nguyên tử      → ĐỎ, đúng
   ✓ Khôi phục bị MẤT một bảng                       → ĐỎ, đúng
   ✓ Khôi phục bị MẤT dòng và mất payload nhị phân   → ĐỎ, đúng
   ✓ Phép so vân tay luôn trả 'giống nhau'           → ĐỎ, đúng
ĐẠT: 7/7 … và bản chép nguyên bản vẫn XANH.
```

**Chạy 3 lượt liên tiếp: cả 3 đều `7/7`, `EXIT=0`.** Điều đó quan trọng hơn một lượt xanh —
ba trong bốn lỗi ở §6.1 chỉ lộ ra ở lượt thứ hai.

### 6.1 BỐN LỖI TRONG CHÍNH CÁC PHÉP ĐO CỦA TÔI — ghi lại vì chúng suýt cho kết luận SAI

**(a) `SELECT phien_ban INTO v` thiếu `max()` ⇒ suýt kết luận "khoá tư vấn không tác dụng".**
Bảng phiên bản **tích luỹ dòng** (7 rồi 8), nên `SELECT phien_ban INTO v` lấy một dòng **BẤT
KỲ** — và nó đọc trúng dòng CŨ `7` sau khi tiến trình kia đã nâng lên `8`. Phép đo báo "tiến
trình thứ hai đụng độ thay vì NHƯỜNG", trong khi **khoá vẫn tốt**. Sửa thành
`SELECT max(phien_ban) INTO v`: `h1` xanh ngay. Đo lại độc lập bằng hai phiên `psql` giữ
`pg_advisory_xact_lock`: phiên sau **chờ 2,02 giây** — khoá có tác dụng thật.

**(b) Đối chứng âm `h2` ban đầu GIỐNG HỆT `h1` ⇒ đối chứng mất tác dụng.** Bỏ khoá ra mà kết
quả vẫn "nâng=1 · nhường=1 · lỗi=không" — vì hai tiến trình chạy **nối đuôi nhau**. Thêm
`PERFORM pg_sleep(0.4)` vào giữa lượt ĐỌC và lượt GHI để giữ cửa sổ tranh chấp mở: `h2` cho
`nâng=1 · nhường=0 · lỗi=['23505']`, **khác hẳn** `h1`.

**(c) Đột biến `DROP TABLE khach_hang` HỎNG LẶNG LẼ vì khoá ngoại** ⇒ suýt kết luận "ca `k1`
yếu". `don_hang` tham chiếu `khach_hang`, nên `DROP` bị chối; đột biến không hề chạm vào bản
khôi phục, và `k1` xanh trở lại — trông y như một ca thử không nhìn thấy gì. Đổi sang bảng LÁ
`audit` (không bảng nào tham chiếu) và thêm đột biến thứ hai `DELETE FROM wh_su_kien`: cả hai
làm `k1` **ĐỎ**.

**(d) Ca `f1` ĐỆ QUY khi chốt chặn bị gỡ ⇒ nó XANH vì lý do SAI.** `f1` chạy bộ thử trong
một tiến trình con. Bản đầu truyền **không** tên lớp, nên tiến trình con chạy **cả bộ thử** —
mà trong đó có chính lớp `F`, nó lại sinh một tiến trình con nữa, và cứ thế. Khi chốt chặn
còn nguyên thì con **từ chối ngay** nên không ai thấy gì. Khi đột biến gỡ chốt chặn, lượt chạy
đệ quy: `f1` bắt được **một** dòng khác 0 (do tầng sâu chết) và — tệ hơn — chữ `TỪ CHỐI` lọt
vào output **qua thông báo lỗi của chính tầng đệ quy**, nên `assertIn("TỪ CHỐI", …)` **đạt**.
Đo được: đột biến 1 cho ra **`VẪN XANH`** ở lượt này và **`ĐỎ, đúng`** ở lượt khác — tức là
**không tất định**. Sửa: `_chay_bo_thu` nay **BẮT BUỘC** nhận tên lớp, `f1` chạy đúng lớp `D`
(4 ca, không sinh tiến trình con). Sau khi sửa: 3 lượt liên tiếp đều `7/7`.

> Bài học chung của cả bốn: **một phép đo hỏng và một ca thử yếu trông GIỐNG NHAU** — cùng cho
> ra một dòng xanh. Cách phân biệt duy nhất là **phá thứ đang canh rồi xem nó có đỏ lên không**,
> và **chạy lượt phá đó NHIỀU LẦN** — ba trong bốn lỗi trên chỉ lộ ra ở lượt thứ hai.

---

## 7. KẾT LUẬN VÀ KHUYẾN NGHỊ

**D-8 KHÔNG ĐỔI. CSDL NGHIỆP VỤ VẪN LÀ SQLITE. Lượt này KHÔNG chuyển gì.**

Ba kết luận có số:

1. **Bốn kết cục phân biệt được và đo riêng được**, bằng SQLSTATE chứ không bằng chữ. Ba cái
   tự báo; `MẤT_CẬP_NHẬT` **im lặng** và chỉ hiện ra khi đối chiếu cuối lượt.
2. **Migration cần khoá tư vấn tường minh trên PostgreSQL** — SQLite chặn bằng khoá ghi của
   tệp, PostgreSQL thì không. Đo được: có khoá → `nâng=1 · nhường=1 · lỗi=0`; bỏ khoá →
   `lỗi=23505`.
3. **Schema nền 47 bảng nạp trọn trong MỘT giao dịch**, lùi sạch khi hỏng giữa khối, và
   `pg_dump`/`pg_restore` giữ nguyên số dòng từng bảng, tổng tiền và payload nhị phân.

**Việc phải làm TRƯỚC KHI chuyển kho** (lượt này **chưa** làm):

| # | Việc | Vì sao |
|---|---|---|
| 1 | Lớp phương ngữ `csdl.py` (chặng 1) | **MÃ NGHIỆP VỤ CHƯA CHẠY ĐƯỢC trên PostgreSQL.** 846 dấu `?` trong 294 chuỗi SQL (`c5`), `INSERT OR IGNORE`/`REPLACE` (`c5`), `PRAGMA` (`c3`) |
| 2 | Soát từng chỗ **đọc-rồi-ghi** | §2.1: chuyển kho mà giữ nguyên khuôn này là **đổi lỗi ồn ào lấy lỗi im lặng** |
| 3 | Thay `migrate.sao_luu()` bằng `pg_dump` | §3.3: bản hiện tại là một **đường lùi GIẢ** trên PostgreSQL |
| 4 | Diễn tập **49** bảng, gồm đường ALTER của `migrate.py` | §4.1 |
| 5 | So **kiểu cột, ràng buộc, giá trị mặc định** | §4: lượt này chỉ so **tên** |

---

## 8. PHẠM VI — ĐÃ ĐO GÌ, VÀ CÁI GÌ NẰM NGOÀI

**ĐÃ ĐO** (macOS arm64 · Python 3.9.6 · SQLite 3.51.0 · PostgreSQL 16.15 Homebrew · cụm thử
qua **socket Unix nội máy**, **không mở cổng TCP nào**):

* Bốn kết cục, đo riêng, có đối chứng âm cho từng cái.
* Mất cập nhật: PostgreSQL im lặng mất · SQLite từ chối ồn ào · hai khuôn ĐÚNG cho mất = 0.
* Khoá tư vấn cho migration: tất định, có đối chứng âm.
* DDL nguyên tử: 0→47 bảng, 0→431 cột, đối chứng âm lùi sạch.
* Sao lưu/khôi phục: số dòng từng bảng, số cột, tổng tiền, md5 payload nhị phân.
* Chốt chặn cổng `5432`: chạy thật, có đối chứng dương.
* Vân tay cụm `:5432` TRƯỚC = SAU, bọc quanh toàn bộ hồi quy.
* 7 đột biến, mỗi cái làm đỏ đúng ca canh nó.

**NẰM NGOÀI PHẠM VI** (nói rõ để không ai đọc quá số đo):

* **Lớp phương ngữ `csdl.py` — CHƯA làm** ⇒ **mã nghiệp vụ chưa chạy được trên PostgreSQL**.
* **Chuyển dữ liệu (chặng 4) — CHƯA làm.** Không một dòng dữ liệu nghiệp vụ nào đi qua đây.
* **`app/du-lieu/hub.db` không bị đọc/ghi.** CSDL nghiệp vụ vẫn là SQLite (**D-8 nguyên vẹn**).
* Đường **ALTER** của `migrate.py` (2 bảng) — chưa diễn tập.
* `migrate.sao_luu()` chưa thay.
* **Nhiều máy · mạng thật · replica · dữ liệu lớn · tải đọc** — chỉ một cụm, một máy.
* **Tỉ lệ phần trăm mất cập nhật không tất định** (43,3%–70,8% qua 5 lượt) — chỉ `mất > 0` và
  `lỗi == 0` là bất biến.
* **Một hàng duy nhất** bị tranh chấp; **không đo deadlock**, không đo `NOWAIT`,
  không đo `SKIP LOCKED`, không đo nhiều hàng, không đo tải trộn đọc/ghi.
* Chỉ so **tên** bảng/cột — **không** so kiểu, ràng buộc, giá trị mặc định, ngữ nghĩa.
* Không đo hiệu năng, không đo thông lượng (việc đó ở `trien_khai/postgres/do_ghi_dong_thoi.py`).

**KHÔNG LÀM, theo chỉ thị:**

* Không gọi API hãng thật, **kể cả sandbox** (`V-G09-01` + `V-13906-05` CHƯA CẤP).
* Không credentials thật, không `.env`, không in bí mật ra log.
* Không push, không deploy, không mở cổng ra Internet.
* Không mở `CHO_PHEP_LIVE`, không sửa cổng sandbox/production trong `app/cau_hinh.py`.
* Không đoán mã trạng thái `110` (D-4).
* Giữ chốt D-9 city/area chặn cứng ngoài mock.
* Không chuyển CSDL nghiệp vụ sang PostgreSQL (D-8).
* Không dùng Claude, không đổi sang mô hình khác.

---

## 9. MÃ ĐÃ DÙNG

| Tệp | Trạng thái | Vai trò |
|---|---|---|
| `app/thu/thu_postgres.py` | **sửa** — thêm lớp `F…K` | **17 ca mới** (25 → **42**), chạy trong hồi quy chung |
| `trien_khai/postgres/van_tay_cum.py` | **MỚI** | Vân tay cụm PostgreSQL (**chỉ đọc**) + `--so` + `--vong` |
| `trien_khai/postgres/thu_dot_bien.py` | **MỚI** | 7 đột biến, chứng minh mỗi ca xanh **làm đỏ được** |
| `trien_khai/postgres/sinh_ddl_pg.py` | có sẵn | Sinh DDL PostgreSQL **từ chính schema đang chạy** |
| `trien_khai/postgres/dien_tap_chuyen.py` | có sẵn | Diễn tập đầy đủ trên cụm riêng (**26** phép khẳng định) |
| `trien_khai/postgres/dung_cum_thu.sh` | có sẵn | Dựng/dọn cụm thử bằng `sh`; cũng từ chối cổng 5432 |

**Chạy lại toàn bộ bằng chứng:**

```bash
python3 app/thu/thu_postgres.py                    ; echo "EXIT=$?"
python3 trien_khai/postgres/dien_tap_chuyen.py     ; echo "EXIT=$?"
python3 trien_khai/postgres/thu_dot_bien.py        ; echo "EXIT=$?"
python3 trien_khai/postgres/van_tay_cum.py         ; echo "EXIT=$?"

python3 trien_khai/postgres/van_tay_cum.py --vong -- \
  env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_KEY_1 \
      -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
  sh app/thu/chay_tat_ca.sh                        ; echo "EXIT=$?"
```

> Bốn biến `GIT_CONFIG_*` bị bỏ ở lệnh cuối vì môi trường harness xuất chúng **thiếu khoá**
> (xem §5.1). Trên một máy không có vấn đề đó thì bỏ phần `env -u …` đi.
