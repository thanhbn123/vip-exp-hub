# G18/AG-06 — TIẾN TRÌNH BỊ TẮT GIỮA GIAO DỊCH (`V-13914(a)`)

**Làn:** G18 · AG-06 CRASH · **Nền:** `integration/g17` @ `7b741c8` · **Nhánh:** `g18-ag06-crash`
**Câu hỏi:** *nếu tiến trình chết giữa một giao dịch ghi nhiều bảng (đơn hàng + COD + bút toán),
CSDL thật có bị bỏ lại NỬA VỜI không?*
**Trả lời đo được:** **KHÔNG** — với SQLite đang dùng thật, và với PostgreSQL trên cụm riêng.
Câu trả lời đó chỉ có giá trị trong đúng phạm vi đo được ở mục 8.

---

## 0. KẾT LUẬN GỌN — đọc mục này trước, mục 8 trước khi trích dẫn

| # | Kết luận | Số đo |
|---|---|---|
| 1 | Tiến trình bị `SIGKILL` giữa giao dịch 5 bảng ⇒ CSDL mở lại **NGUYÊN VẸN ở vết TRƯỚC** | 6/6 điểm giết trong giao dịch · 0 dòng mồ côi · `integrity_check=ok` |
| 2 | `SIGKILL` **ngay sau** `COMMIT` ⇒ việc đã chốt **SỐNG SÓT** | 1/1 điểm · vết bằng đúng đối chứng dương |
| 3 | Không giết ⇒ cùng kịch bản ra **đủ cả năm chỗ ghi** (đối chứng dương) | `Ran 31 tests … OK`, mã thoát 0 |
| 4 | Bộ đo **ĐỎ ĐƯỢC**: bỏ `csdl.giao_dich()` (mã trước V-13912) ⇒ **NỬA VỜI** thật | COD=`COD_COLLECTED` · chuyển=1 · **bút toán=0** · công nợ=0 |
| 5 | WAL cứu **tính NGUYÊN VẸN**, KHÔNG cứu **giao dịch dang dở** — và đó là điều phải xảy ra | lúc chết `-wal` = **885.832 byte** khung chưa chốt; mở lại bị bỏ qua sạch |
| 6 | PostgreSQL trên cụm riêng: giết **client** (7 điểm) và giết **backend** (2 điểm) — cùng kết quả | 9/9 lượt nguyên vẹn · cụm chạy **khôi phục WAL** thật |
| 7 | **Không có** cơ chế nào của sản phẩm tự phát hiện & dọn một giao dịch nửa vời — vì **không có gì để dọn** | xem mục 6: thứ tự ngăn là `csdl.giao_dich()`, không phải một bộ dọn |

---

## 1. LỖ HỔNG NÀY LÀ GÌ, VÀ AI GHI RA

`docs/BAN_GIAO.md` §6.1, dòng `V-13914`:

> Đo 3 ca đồng thời chưa phủ: **(a) tiến trình bị tắt GIỮA giao dịch** · (b) máy chủ HTTP thật
> dưới tải · (c) trần chống lạm dụng nhiều tiến trình

Lượt này đóng **(a)**. (b) và (c) **vẫn chưa đo** — mục 8.

Đường ghi được chọn làm vật đo là `tai_chinh.chuyen_cod()` — **MỘT** giao dịch ghi **NĂM** chỗ,
đúng khuôn "đơn hàng + COD + bút toán" mà đề bài nêu:

| # | Câu ghi | Bảng | Nếu chết sau chỗ này mà CSDL bị bỏ lại |
|---|---|---|---|
| 1 | `UPDATE tc_cod` | trạng thái COD | hệ nói COD đã thu, không có vết chuyển |
| 2 | `INSERT tc_cod_chuyen` | vết chuyển trạng thái | có vết, **sổ cái trống** ← kịch bản §18 |
| 3 | `INSERT tc_but_toan` | bút toán (BẤT BIẾN §17) | bút toán vào sổ, công nợ không đổi |
| 4 | `UPSERT tc_cong_no` | số dư công nợ | công nợ lệch khỏi sổ cái |
| 5 | `INSERT tc_nhat_ky` | nhật ký móc băm | móc băm đứt |

---

## 2. CÁCH ĐO — VÀ CÁI KHÓ NHẤT: GIẾT MÀ KHÔNG SỬA MÃ ĐANG ĐO

### 2.1 Cách dễ (và SAI)

Chèn `os.kill(os.getpid(), 9)` vào `csdl.py` tại đúng câu cần chết. Đó là cách **sai**: nó sửa
chính mã đang được đo, nên kết quả đo nói về một phiên bản mã **không ai chạy**.

### 2.2 Cách dùng ở đây: móc có SẴN của driver

`sqlite3.Connection.set_trace_callback` — móc của **thư viện chuẩn**, không phải của dự án.
`csdl.py`, `tai_chinh.py`, `don_hang.py` **không bị sửa một ký tự** (`git status` chỉ có 2 đường
dẫn MỚI, xem mục 9).

Nhưng phải trả lời một câu trước khi tin nó: **móc bắn TRƯỚC hay SAU khi câu lệnh chạy?** Lệch
một nhịp thì "ngay trước COMMIT" hoá thành "ngay sau COMMIT" — hai kết luận trái ngược từ cùng
một phép đo.

```
$ python3 trien_khai/g18-crash/do_giet.py --tu-kiem-moc
  ✓ móc bắn TRƯỚC khi câu chạy: trong lượt gọi COMMIT, kết nối khác còn thấy 1 dòng  (thấy 1)
  ✓ sau COMMIT thì kết nối này thấy 2 dòng  (thấy 2)
  ✓ móc bắn cho CẢ câu điều khiển giao dịch (BEGIN/COMMIT)  (đã quan sát được lượt gọi COMMIT)

3/3 ca tự kiểm cái móc ĐẠT
   >>> mã thoát = 0
```

Từ sự thật đó, ánh xạ điểm giết là chính xác:

* giết **ngay trong** lượt gọi của câu X ⇒ chết **TRƯỚC** khi X chạy;
* đặt cờ ở lượt gọi của câu X, giết ở lượt gọi **KẾ TIẾP** ⇒ chết **ngay SAU** khi X chạy.

### 2.3 Chuỗi câu lệnh thật của `chuyen_cod` (đo, không suy)

```
 1 | SELECT * FROM tc_cod …                              ← đọc trước giao dịch
 2 | BEGIN IMMEDIATE                                     ← điểm giết "truoc_begin"
 3 | UPDATE tc_cod …                                     ← GHI 1
 4 | INSERT INTO tc_cod_chuyen …                         ← GHI 2   (điểm "sau_ghi_1")
 5 | SELECT * FROM don_hang …
 6 | SAVEPOINT gd1
 7 | INSERT INTO tc_but_toan …                           ← GHI 3   (điểm "sau_ghi_2")
 8 | INSERT INTO tc_cong_no …                            ← GHI 4   (điểm "sau_ghi_3")
 9 | RELEASE gd1
10 | SAVEPOINT gd1
11 | SELECT bam FROM tc_nhat_ky …
12 | INSERT INTO tc_nhat_ky …                            ← GHI 5   (điểm "sau_ghi_4")
13 | RELEASE gd1
14 | COMMIT                                              ← điểm "truoc_commit"
15 | SELECT * FROM tc_cod …                              ← điểm "sau_commit"
```

### 2.4 Bộ đo — VẾT chứ không chỉ ĐẾM DÒNG

Đếm dòng trả lời *"có bao nhiêu"*, không trả lời *"có KHỚP nhau không"*. Kịch bản §18 có số dòng
hai bảng đều "đúng" mà chúng nói hai chuyện khác nhau. Nên phép đo chính là **VẾT 9 TRƯỜNG** lấy
từ 5 bảng: `cod_trang_thai` · `cod_hang_bao` · `cod_du_kien` · `so_chuyen` · `so_but_toan` ·
`tong_but_toan` · `cong_no_phai_thu` · `so_nhat_ky` · `so_don`.

Sau khi giết, vết phải bằng **ĐÚNG vết TRƯỚC** hoặc **ĐÚNG vết SAU**. Không bằng vết nào ⇒
**NỬA VỜI**. Kèm theo, mỗi lượt còn đo: `PRAGMA integrity_check` · `PRAGMA foreign_key_check` ·
4 phép dò **dòng MỒ CÔI** (bút toán / sổ COD / vết chuyển / lịch sử trỏ tới đơn không tồn tại) ·
1 phép dò bút toán **lệch chủ thể** (tenant của bút toán ≠ tenant của đơn).

### 2.5 ĐỐI CHỨNG ÂM — ca quan trọng nhất của cả lượt này

Một bộ đo **chưa từng kêu "NỬA VỜI"** thì lời khai *"mọi ca đều NGUYÊN VẸN"* không có giá trị:
nó chỉ nói rằng bộ đo chưa bao giờ chạy đúng chỗ.

Nên `tien_trinh_giao_dich.py` có chế độ `--che-do khong_giao_dich`: **đúng năm câu ghi ấy,
KHÔNG bọc `csdl.giao_dich()`** — bản dựng lại của mã **trước** bản vá V-13912 (mỗi `csdl.ghi()`
tự chốt ngay). Giết ở cùng điểm `sau_ghi_2`, bộ đo **BẮT BUỘC** phải kêu NỬA VỜI. Kết quả thật:

```
mã thoát -9 · COD=COD_COLLECTED · chuyển=1 · bút toán=0 · công nợ=0   ⇒ NỬA VỜI
```

Đây **đúng** kịch bản §18: *hệ báo tiền đã về trong khi sổ cái không có dòng nào*. Và vì
`tc_but_toan` là bất biến (§17), chênh đó **không sửa được bằng UPDATE** — chỉ chữa được bằng
bút toán đảo. Ca `A.test_a3` khẳng định cả ba con số này, không chỉ khẳng định chữ "NỬA VỜI".

---

## 3. KẾT QUẢ SQLITE — CSDL ĐANG DÙNG THẬT

Môi trường: `Python 3.9.6` · `SQLite 3.51.0` · `journal_mode=wal` · `synchronous=1 (NORMAL)`.

```
$ python3 app/thu/thu_g18_crash.py
Ran 31 tests in 6.050s
OK
   >>> mã thoát = 0
```

```
BẢNG BẰNG CHỨNG — SQLite: 7 điểm giết + đối chứng dương + đối chứng âm
  điểm giết                   mã  ghi    -wal B  COD             ch  bt  công nợ  nk  phán loại
  khong                        0    -         0  COD_COLLECTED    1   1   250000   1  NGUYEN_VEN_SAU
  sau_commit                  -9    5    935272  COD_COLLECTED    1   1   250000   1  NGUYEN_VEN_SAU
  sau_ghi_1                   -9    1    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC
  sau_ghi_2                   -9    2    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC
  sau_ghi_3                   -9    3    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC
  sau_ghi_4                   -9    4    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC
  truoc_begin                 -9    0    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC
  truoc_commit                -9    5    885832  COD_EXPECTED     0   0        0   0  NGUYEN_VEN_TRUOC

  ch = tc_cod_chuyen · bt = tc_but_toan · nk = tc_nhat_ky
  BẤT BIẾN chung cho MỌI lượt: integrity_check=ok · foreign_key_check=[] · mồ côi=0
```

`mã = -9` là **SIGKILL thật** (`returncode == -signal.SIGKILL`), không phải `sys.exit(9)`.
`ghi` = số câu GHI **đã chạy xong** tại thời điểm chết — cột này là chỗ một lỗi của chính bộ đo
đã bị bắt (mục 7.1).

Đọc bảng này ra ba điều:

1. **Chết ở bất cứ đâu TRONG giao dịch** (kể cả `truoc_commit` — cả năm câu ghi đã chạy, chỉ
   thiếu một chữ `COMMIT`) ⇒ CSDL mở lại **y như chưa hề có giao dịch**. Không nửa vời.
2. **Chết ngay SAU `COMMIT`** ⇒ đủ cả năm chỗ ghi, **không mất một đồng**. Tính BỀN giữ.
3. **Không giết** ⇒ cũng đủ cả năm chỗ ghi. Đối chứng dương, mã thoát 0.

---

## 4. WAL / JOURNAL — NÓ CÓ CỨU ĐƯỢC KHÔNG

**Có, nhưng cứu đúng thứ nó phải cứu.** Đây là câu dễ bị trả lời sai nhất, nên nói theo hai vế:

| Vế | Trả lời | Số đo |
|---|---|---|
| WAL có cứu **tính NGUYÊN VẸN** không? | **CÓ** | mọi lượt: `integrity_check=ok`, `foreign_key_check=[]`, mồ côi = 0 |
| WAL có cứu **giao dịch dang dở** không? | **KHÔNG — và không được cứu** | lúc chết `-wal` = 885.832 byte khung chưa chốt; mở lại thấy vết TRƯỚC |
| WAL có cứu **giao dịch ĐÃ COMMIT** không? | **CÓ** | `sau_commit`: vết = vết SAU đầy đủ |

Cơ chế: khung WAL của một giao dịch **chưa chốt** không có bản ghi commit. SQLite mở lại, thấy
đuôi WAL không kết thúc bằng một commit hợp lệ, và **bỏ qua** phần đuôi ấy. Giao dịch dang dở
biến mất **trọn vẹn**, không phải "biến mất một nửa".

### 4.1 Phép đo mạnh hơn: mở lại từ ẢNH NGUYÊN TRANG trên đĩa

"Mở lại tệp cũ" vẫn có thể bị nghi là còn thứ gì trong bộ nhớ. Nên ca `C.test_c2` **chép
nguyên trạng** `hub.db` + `hub.db-wal` + `hub.db-shm` **ngay sau khi giết, TRƯỚC khi mở lần
nào**, sang một thư mục khác rồi mở **LẦN ĐẦU**. Kết quả: vết giống hệt lần đo đầu, `integrity
ok`, không mồ côi. Thứ quyết định là **BYTE TRÊN ĐĨA lúc chết**.

Thứ tự này là bắt buộc, không phải cho đẹp: **chỉ một lượt mở kết nối cũng đủ để SQLite
checkpoint WAL và xoá `-wal`** — và khi đó "WAL có cứu được không" không còn đo được nữa, vì
thứ cần đo đã bị chính phép đo xoá mất.

### 4.2 `synchronous = 1 (NORMAL)` — VÀ ĐÂY LÀ RANH GIỚI

Đo được trên CSDL đang chạy: `PRAGMA synchronous` = **1 (NORMAL)**. Đây là giá trị mặc định khi
chuyển sang WAL. Ý nghĩa:

* `SIGKILL` tiến trình (lượt đo này) — **không mất gì**, vì page cache của hệ điều hành vẫn
  sống và mọi thứ đã `write()` đều đọc lại được.
* **MẤT ĐIỆN / máy chủ vật lý chết** — giao dịch **đã COMMIT** có thể **MẤT** (chưa `fsync`
  xong), nhưng CSDL **không hỏng**. Muốn mất 0 thì phải `synchronous=FULL`.

Lượt này **KHÔNG đo được vế mất điện** (mục 8). Con số `synchronous=1` được ghi ra ở đây đúng
để không ai đọc "mọi ca đều nguyên vẹn" rồi suy rộng sang mất điện.

---

## 5. KẾT QUẢ POSTGRESQL — CỤM RIÊNG, KHÔNG PHẢI `:5432`

### 5.1 Ba chốt cứng, và bằng chứng chúng đã giữ

| Chốt | Cách giữ | Bằng chứng |
|---|---|---|
| Không đụng cụm `:5432` | cổng riêng `55718`, `chot_an_toan` TỪ CHỐI nếu thấy 5432 | **vân tay TRƯỚC = SAU**, xem dưới |
| Cụm thử KHÔNG mở TCP | `listen_addresses=''`, socket Unix ở `/tmp/vhpg.XXXX` | ca `D.test_d1` hỏi **`lsof`**, không hỏi cấu hình: không có listener |
| Dừng bằng `pg_ctl stop`, không `kill` theo tên | `Cum.dong()` + ca `E.test_e3` hỏi lại **từng PID postmaster** | postmaster đã chết, thư mục dữ liệu + socket đã xoá |

Vân tay cụm `:5432`, chụp bằng chính công cụ của dự án (`trien_khai/postgres/van_tay_cum.py`,
**chỉ đọc**), **TRƯỚC và SAU** một lượt `chay_do.sh` đầy đủ:

```
── TRƯỚC                              ── SAU
   PID postmaster  : 58873               PID postmaster  : 58873
   postmaster bắt đầu: 2026-10-09 …      postmaster bắt đầu: 2026-10-09 …   (y hệt)
   số CSDL         : 6                   số CSDL         : 6
   danh sách CSDL  : postgres template0 template1 vip_customs vip_customs_g16 vip_customs_test
   PID nghe TCP    : ['58873']           PID nghe TCP    : ['58873']

KẾT LUẬN :5432 TRƯỚC = SAU: ĐÚNG          (chay_do.sh mã thoát = 0)
```

Ba CSDL của dự án khác — `vip_customs` · `vip_customs_g16` · `vip_customs_test` — **còn nguyên**,
cùng postmaster, cùng thời điểm khởi động. Đây là phép đo, không phải lời khai.

Ngoại lệ duy nhất của "không `kill`" là **chính phép đo**: `os.kill(SIGKILL)` vào **đúng PID
backend của cụm thử**, lấy từ `pg_backend_pid()` ghi ra tệp **từ bên trong chính kịch bản** —
gọi nó ở một phiên `psql` khác thì trả về PID của phiên khác, và giết nhầm backend là giết nhầm
phiên của người khác.

### 5.2 Hai KIỂU giết, hai CƠ CHẾ khác nhau — không gộp làm một

| Kiểu | Giết cái gì | Máy chủ làm gì | Số lượt |
|---|---|---|---|
| `client` | tiến trình `psql` | backend thấy client chết ⇒ **huỷ giao dịch** | 7 điểm |
| `backend` | tiến trình máy chủ đang phục vụ | postmaster dừng **cả cụm** ⇒ **KHÔI PHỤC WAL** | 2 điểm |

`client` là tương ứng đúng nhất với bên SQLite (ở đó cũng giết tiến trình **ứng dụng**).
`backend` là ca nặng hơn — "CSDL chết giữa giao dịch" — và nó là ca duy nhất chạy khôi phục WAL
thật.

**Dấu vết khôi phục do CHÍNH PostgreSQL ghi** (`pg.log`, không phải bộ thử viết):

```
2026-10-15 18:53:43.174 +07 [26751] LOG:  terminating any other active server processes
2026-10-15 18:53:43.175 +07 [26751] LOG:  all server processes terminated; reinitializing
```

Ca `D.test_d10` **bắt buộc** phải thấy một trong các dòng ấy, nếu không thì ĐỎ. Không có nó thì
"giết backend" chỉ là một lời khai: cụm có thể chưa hề ngã, và phép đo nói về một lượt chưa bao
giờ xảy ra.

### 5.3 Kết quả

**9/9 lượt nguyên vẹn**: 7 điểm giết kiểu `client` + 2 điểm kiểu `backend`:
`truoc_begin` · `sau_ghi_1` · `sau_ghi_2` · `sau_ghi_3` · `sau_ghi_4` · `truoc_commit` → vết
**TRƯỚC**; `sau_commit` → vết **SAU**. Mọi lượt: 4 phép dò mồ côi = 0.

Bản dịch DDL có **81 khoá ngoại** — nghĩa là phép dò "mồ côi" ở đây có ràng buộc thật đứng sau.
(Ca `D.test_d11` khẳng định `> 50`.) Chính việc gieo nền **hỏng ở dòng đầu** vì thiếu
`goi_dich_vu` là bằng chứng khoá ngoại `tenants.goi_id` đang **cưỡng chế**, không chỉ tồn tại
trên giấy.

### 5.4 PHẠM VI CỦA MỤC 5 — ĐỌC TRƯỚC KHI TRÍCH DẪN

Phép đo này chạy **NĂM CÂU GHI CÙNG HÌNH DẠNG** với `tai_chinh.chuyen_cod`, trên DDL do
`sinh_ddl_pg.py` dịch **từ chính schema SQLite đang chạy**.

Nó **KHÔNG** chạy `tai_chinh.py`. Mô-đun đó chỉ nói SQLite (`import csdl` → `sqlite3`), và quyết
định **D-8** là *chưa chuyển CSDL nghiệp vụ sang PostgreSQL*. Nên đây là phép đo **TẦNG CSDL**,
**không** phải phép đo mã nghiệp vụ trên PostgreSQL.

> Câu **"sản phẩm chạy đúng trên PostgreSQL"** KHÔNG được rút ra từ mục này.

Một chi tiết kỹ thuật phải nói ra: backend bị giết trong lúc đang `pg_sleep` — mà `pg_sleep` là
**dụng cụ chèn của bộ đo**, không phải hành vi sản phẩm. Với kiểu `client`, bộ đo gọi
`pg_terminate_backend()` để máy chủ **thấy ngay** điều nó sẽ tự thấy khi backend rảnh. Lệnh ấy
chỉ **huỷ phiên của một client đã chết** — nó KHÔNG chốt giao dịch, KHÔNG ghi thêm gì, nên nó
không thể biến một giao dịch nửa vời thành nguyên vẹn.

---

## 6. CƠ CHẾ NÀO CỦA SẢN PHẨM PHÁT HIỆN VÀ DỌN DẸP?

Câu trả lời trung thực gồm hai vế, và vế thứ nhất quan trọng hơn:

### Vế 1 — KHÔNG có gì để dọn, vì giao dịch là MỘT ĐƠN VỊ

Thứ ngăn CSDL nửa vời **không phải** một bộ dọn dẹp, mà là `csdl.giao_dich()`
(`app/csdl.py:384`): tầng ngoài `BEGIN IMMEDIATE`, tầng lồng `SAVEPOINT`, và nhánh
`except BaseException` lùi sạch. `chuyen_cod` bọc **cả năm câu ghi** trong một khối
(`app/tai_chinh.py:685`), có ghi chú V-13912 ngay tại chỗ.

Đo được hệ quả: **không có trạng thái nửa vời nào tồn tại để mà dọn.** Sau 7 lượt giết, số dòng
mồ côi = 0 và vết luôn bằng đúng một trong hai vết.

### Vế 2 — Lớp phát hiện hiện có là **thủ công / nghiệp vụ**, không tự động

| Cơ chế | Ở đâu | Phát hiện được gì | Tự chạy? |
|---|---|---|---|
| Khôi phục WAL của SQLite | chính SQLite, lúc mở kết nối | đuôi WAL chưa chốt | **CÓ — tự động, không cần mã dự án** |
| `tai_chinh.kiem_nhat_ky(tenant)` | `app/tai_chinh.py:401` | móc băm `tc_nhat_ky` đứt (dòng bị sửa/bỏ) | không — phải gọi |
| `tai_chinh.tinh_lai_cong_no(tenant)` | `app/tai_chinh.py:565` | công nợ lệch khỏi `tc_but_toan` | không — phải gọi |
| `don_hang.don_can_doi_soat(tenant)` | `app/don_hang.py:856` | đơn treo "không rõ kết quả" | không — phải gọi |
| `doi_soat.py` | đối soát TIỀN với bảng kê hãng | COD hãng báo lệch sổ | không — nạp file thủ công |
| `trien_khai/do_csdl.py` | công cụ vận hành | `integrity_check`, `foreign_key_check`, số dòng từng bảng, SHA-256 | không — chạy tay |
| `trien_khai/dien_tap_khoi_phuc.sh` + `migrate.khoi_phuc()` | diễn tập G11 | khôi phục từ bản sao lưu | không — chạy tay |

**Đo được, và đây là một lỗ hổng thật:**

```
$ grep -rn "foreign_key_check\|integrity_check" app/*.py
app/xoay_khoa.py:182:    đủ mà khóa lệch thì credentials thành rác, `integrity_check` vẫn `ok`, và không gì báo cho
```

**Đúng MỘT dòng, và nó là một CHÚ THÍCH** — không một lệnh gọi nào. Nghĩa là **mã sản phẩm không
tự kiểm toàn vẹn CSDL lúc khởi động**, và cũng **không có bộ dọn rác tự động** nào. Thứ duy nhất
tự chạy là khôi phục WAL của chính SQLite, và nó chỉ chạy khi có ai đó mở kết nối.

Lượt này cho thấy điều đó **hiện chưa gây hậu quả** — vì thứ tự ngăn nằm ở `giao_dich()`, tức ở
**thời điểm GHI**, chứ không ở thời điểm đọc lại. Nhưng nó là một **giả định chưa có lưới**:
nếu một ngày có đường ghi nào đi vòng qua `giao_dich()` (đúng loại lỗi V-13912 đã vá **5 khối**
và `BAN_GIAO` §6.1 ghi còn **5 khối nữa**), thì **không có gì** trên hệ thống phát hiện ra.

> **ĐỀ XUẤT (chưa làm, cần anh Thành quyết):** một lượt `PRAGMA foreign_key_check` +
> `integrity_check` lúc khởi động, ghi kết quả vào `audit`. Nó KHÔNG thay được `giao_dich()`;
> nó chỉ biến "không ai biết" thành "có một dòng audit".

---

## 7. HAI LỖI CỦA CHÍNH BỘ ĐO — ghi ra để không lặp lại

### 7.1 Bộ đếm câu ghi lệch một nhịp

`test_b9` phán: `sau_ghi_1`: *số câu GHI đã chạy là 2, mong đợi 1*.

Nguyên nhân: `_moc()` **tăng bộ đếm trước khi xét** câu đang đi qua móc. Móc bắn TRƯỚC khi câu
chạy, nên câu **đang chờ** bị tính là **đã chạy**. Với `sau_ghi_1` và `sau_ghi_3`, câu kế tiếp
**cũng là một câu ghi** nên bộ đếm vọt lên 2 và 4; với `sau_ghi_2` và `sau_ghi_4` câu kế tiếp là
`SELECT`/`RELEASE` nên nó **tình cờ đúng**.

Đây là loại lỗi tệ nhất: **đúng một nửa**. Nếu chỉ có bốn ca `sau_ghi_2/4/truoc_commit/sau_commit`
thì nó đã đi qua. Vá: tách **HAI** con số — `so_ghi_da_chay` (dùng để phán) và `so_ghi_moc` (tính
cả câu đang chờ) — và ca `test_b9` khẳng định **cả bảy** điểm, kèm một phép kiểm *"không có hai
điểm nào chết ở cùng một câu"*.

### 7.2 Một chốt an toàn tự bắt chính nó

Chốt `C4` ("nguồn không được chứa `pkill`/`killall`") ban đầu dò bằng **grep**. `chot_an_toan.py`
**tự chứa** hai chữ ấy (trong docstring và trong chính mẫu dò) ⇒ nó **tự bắt mình**. Cách "sửa"
hay gặp là thêm tệp này vào danh sách miễn trừ — tức **khoét một lỗ đúng ở chỗ canh**.

Vá: dò bằng **AST**, hỏi đúng câu cần hỏi — *chuỗi ấy có được ĐƯA CHO một lệnh chạy tiến trình
không*, chứ không phải *chuỗi ấy có xuất hiện ở đâu đó không*. Bộ dò còn **ghép chuỗi nối bằng
`+`** (`subprocess.run(["pk" + "ill"])`), vì một bộ dò bỏ sót cách viết thứ hai là một bộ dò
**dạy người ta cách lách nó**. Ba ca tổng hợp canh đúng chỗ này: có lệnh thật ⇒ C4; ghép chuỗi ⇒
C4; chỉ nhắc trong chú thích ⇒ **sạch**.

---

## 8. NẰM NGOÀI PHẠM VI ĐÃ ĐO — nói ra để không ai suy rộng

| Không đo | Vì sao | Hệ quả |
|---|---|---|
| **Mất điện / máy chủ vật lý chết** | `SIGKILL` không xoá page cache của hệ điều hành | **KHÔNG** kiểm được `fsync`. `synchronous=1` ⇒ giao dịch đã COMMIT **có thể mất** khi mất điện (CSDL không hỏng) |
| **Mã nghiệp vụ chạy trên PostgreSQL** | D-8: chưa chuyển; `tai_chinh.py` chỉ nói SQLite | Mục 5 là phép đo **tầng CSDL**, không phải "sản phẩm chạy đúng trên PG" |
| **Máy chủ HTTP thật dưới tải** — `V-13914(b)` | ngoài nhiệm vụ được giao | vẫn chưa đo |
| **Trần chống lạm dụng nhiều tiến trình** — `V-13914(c)` | ngoài nhiệm vụ được giao | vẫn chưa đo (là điều kiện kích hoạt số 2 của kế hoạch PostgreSQL) |
| **Giao dịch ghi nhiều bảng KHÁC** | chỉ đo `chuyen_cod` (5 chỗ ghi) | `BAN_GIAO` §6.1 ghi **còn 5 khối ghi khác** chưa bọc `giao_dich()`; chúng **chưa được đo ở đây** |
| **Gọi API hãng, kể cả sandbox** | `V-G09-01` + `V-13906-05` CHƯA CẤP | lượt này **không mở một kết nối mạng nào** |
| **Chuyển CSDL sang PostgreSQL** | D-8 | vẫn SQLite; PostgreSQL chỉ trên cụm riêng, **cấm `:5432`** |

Một điểm nữa phải nói: **bảy điểm giết là bảy điểm trong MỘT giao dịch của MỘT hàm.** Nó chứng
minh `giao_dich()` đúng ở đó; nó **không** chứng minh mọi đường ghi khác đều đã bọc
`giao_dich()`. Đó là việc của `V-13912`, và `BAN_GIAO` §6.1 ghi nó **còn 5 khối**.

---

## 9. CHỐT AN TOÀN, LỆNH CHẠY, VÀ BẰNG CHỨNG

### 9.1 Bảy chốt — và bộ dò của chính chúng

```
$ python3 trien_khai/g18-crash/chot_an_toan.py --tu-kiem
  ✓ đủ chốt                                    mong đợi=sạch  thấy=sạch
  ✓ C1 nền trong cây dự án                     mong đợi=C1    thấy=C1
  ✓ C1 nền trùng thư mục dữ liệu thật          mong đợi=C1    thấy=C1
  ✓ C1 nền rỗng                                mong đợi=C1    thấy=C1
  ✓ C2 cổng 5432                               mong đợi=C2    thấy=C2
  ✓ C3 cụm thử mở TCP                          mong đợi=C3    thấy=C3
  ✓ C4 nguồn có lệnh dọn theo tên              mong đợi=C4    thấy=C4
  ✓ C4 nguồn ghép chuỗi để lách                mong đợi=C4    thấy=C4
  ✓ C4 tệp SẠCH chỉ nhắc trong chú thích       mong đợi=sạch  thấy=sạch
  ✓ C5 PID không được ghi lại                  mong đợi=C5    thấy=C5
  ✓ C7 CSDL ngoài nền                          mong đợi=C7    thấy=C7
  ✓ C7 CSDL trong thư mục dữ liệu THẬT         mong đợi=C7    thấy=C7
  ✓ C6 cổng hãng sandbox đang MỞ               mong đợi=C6    thấy=C6
  ✓ C6 cổng hãng production đang MỞ             mong đợi=C6    thấy=C6

14/14 ca chốt an toàn ĐẠT
   >>> mã thoát = 0
```

Mỗi cấu hình hỏng phải bị bắt bởi **ĐÚNG chốt mang tên nó**. "Bắt được nhưng bởi chốt khác"
tính là **HỎNG**: nếu C1 bắt được lỗi cổng PG thì lúc đó C2 đang không làm việc, và lượt chạy
thật sẽ lọt qua khe ấy.

| Mã | Chốt | Bắt cái gì |
|---|---|---|
| C1 | Nền CSDL phải là thư mục TẠM, ngoài cây dự án | ghi vào `app/du-lieu/hub.db` thật |
| C2 | Cổng PostgreSQL ≠ 5432 | đụng cụm hệ thống giữ `vip_customs*` |
| C3 | Cụm PG thử KHÔNG mở TCP | mở cửa mạng cho một cụm dùng một lần |
| C4 | Nguồn của làn này không chứa `pkill`/`killall` | dọn tiến trình theo TÊN, giết cả làn khác |
| C5 | Không tiến trình con nào chạy mà không có PID ghi lại | bỏ lại tiến trình mồ côi |
| C6 | `JT_CHO_PHEP_SANDBOX`/`PRODUCTION` vẫn ĐÓNG | gọi API hãng khi chưa được cấp phép |
| C7 | Mọi tệp CSDL bị đụng đều nằm dưới nền tạm | đo nhầm CSDL của làn khác |

### 9.2 Chạy

```sh
sh trien_khai/g18-crash/chay_do.sh                          # chốt + móc + bộ đo đầy đủ
sh trien_khai/g18-crash/chay_do.sh --giu-bang-chung /tmp/g18.txt
VIP_THU_POSTGRES=0 sh trien_khai/g18-crash/chay_do.sh       # chỉ phần SQLite
python3 trien_khai/g18-crash/chot_an_toan.py --tu-kiem       # tự kiểm 7 chốt (14 cấu hình)
python3 trien_khai/g18-crash/do_giet.py --tu-kiem-moc        # tự kiểm cái móc (3 ca)
```

### 9.3 Bộ chạy hồi quy toàn dự án

`app/thu/chay_tat_ca.sh` **TỰ DÒ** `app/thu/thu_*.py`, nên `thu_g18_crash.py` **tự vào** lượt
chạy chung — không phải sửa danh sách nào. Bộ đo chạy hết trong **~5–6 giây** (các lượt đo: 4,777 · 5,324 · 6,050 · 6,424 giây).

Một điều phải nói trước: nếu máy **thiếu** `initdb`/`pg_ctl`/`psql` (hoặc đặt
`VIP_THU_POSTGRES=0`), phần PostgreSQL **BỎ QUA** và bộ chạy chung vẫn phán **✓** cho phần
SQLite đã chạy. Bộ đo in một dòng `!!! BỎ QUA PHẦN PostgreSQL — <lý do>` để **nói ra**, nhưng
**phán quyết của bộ chạy chung không tách được hai phần** — đây là hạn chế đã biết, không phải
tính năng. Máy đo lượt này **có đủ** ba lệnh ấy (`PostgreSQL 16.15`), nên phần PG **đã chạy
thật**: 9/9 lượt giết.

### 9.3b Lượt chạy hồi quy TOÀN DỰ ÁN — và hai tương tác LIÊN LÀN phải khai ra

```
$ sh app/thu/chay_tat_ca.sh
  ✓ thu_g18_crash.py           31 ca
  python:   1491 ca · 39 bộ chạy thật      (G17 ghi: 1460 ca · 38 bộ)
  bộ hỏng:  thu_bao_mat.py thu_qa_g17.py thu_tich_hop.py
  EXIT_HOIQUY=1
```

**+31 ca · +1 bộ so với G17** — bộ đo tự vào lượt chạy chung, đúng như thiết kế tự dò.
Nhưng ba bộ kia đỏ, và **cả ba đều KHÔNG phải lỗi sản phẩm**:

**(1) `thu_tich_hop.py` và `thu_bao_mat.py` — môi trường git của phiên, không phải mã dự án.**
Cả hai hỏng ở `git check-ignore` trả **128**, vì phiên này có `GIT_CONFIG_COUNT` /
`GIT_CONFIG_VALUE_0` / `GIT_CONFIG_VALUE_1` trong môi trường **mà thiếu `GIT_CONFIG_KEY_0`**:

```
$ git status
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
```

Đo lại với môi trường git sạch (`GIT_CONFIG_COUNT=0`):

```
$ GIT_CONFIG_COUNT=0 python3 app/thu/thu_tich_hop.py   →  EXIT=0  OK
$ GIT_CONFIG_COUNT=0 python3 app/thu/thu_bao_mat.py    →  EXIT=0  OK
```

⇒ Hai bộ này **ĐẠT** khi git không bị biến môi trường của phiên làm hỏng. Đây là hiện tượng
**có trước** lượt này, không do lượt này.

**(2) `thu_qa_g17.py` — cổng "cây sạch" (F0-a) đếm tệp CHƯA `git add` của làn NÀY.**
`A_Nen.test_a1_cay_sach_va_head` đòi `git status --porcelain` phải **rỗng**, chỉ miễn trừ tệp
thuộc làn AG-01/G17 (`MAU_TEP_CUA_AG01_G17`). Bảy tệp MỚI của làn G18/AG-06 không nằm trong
danh sách miễn trừ ấy, nên cổng đỏ. Đo lại bằng chính hàm của cổng:

```
CÂY BẨN (theo cổng F0-a của thu_qa_g17) = 7 dòng
    ?? app/thu/thu_g18_crash.py
    ?? docs/G18_CRASH.md
    ?? trien_khai/g18-crash/{chay_do.sh,chot_an_toan.py,do_giet.py,do_postgres.py,tien_trinh_giao_dich.py}
Sau khi trừ ĐÚNG 7 đường của làn G18/AG-06: []
KẾT LUẬN: cổng F0-a chỉ phàn nàn về tệp CHƯA `git add` của làn này.
```

Đây **đúng** nếp đã ghi ở `docs/QA_G17.md:395`: *"Hai tệp AG-01 G17 là tệp MỚI, chưa `git add`;
cổng 'cây sạch' của bộ thử miễn trừ đúng hai…"*. Cách xử theo nếp ấy là thêm một mẫu quyền sở
hữu cho làn G18/AG-06 — nhưng mẫu đó nằm trong `app/thu/thu_qa_g17.py`, **ngoài danh sách tệp
được cấp của làn này**, nên lượt này **không sửa** và **khai ra ở đây**.

> **KHÔNG** `git add`, **KHÔNG** commit: nếp của dự án là tệp của làn đang làm thì để nguyên
> trạng cho làn đó / người gộp quyết. Việc còn lại: hoặc thêm `trien_khai/g18-crash/*` +
> `app/thu/thu_g18_crash.py` + `docs/G18_CRASH.md` vào mẫu miễn trừ, hoặc commit khi gộp.

### 9.4 Bằng chứng: lệnh thật, mã thoát thật, SHA thật

Mã thoát được ghi **TRƯỚC mọi pipe** — trong bộ đo, `subprocess.Popen` + `communicate()` trả
`returncode` trực tiếp; trong `chay_do.sh`, `python3 … >"$BANG_CHUNG"` rồi mới `cat`, vì
`| tee` nuốt mã thoát của `python3` và một bộ đo HỎNG sẽ được phán ĐẠT (đúng khuôn lỗi
§7.1 BAN_GIAO).

```
$ sh trien_khai/g18-crash/chay_do.sh
 TỔNG KẾT — phán bằng MÃ THOÁT, không bằng chữ trong output
   chốt an toàn (0)      : mã thoát 0  ĐẠT
   móc giết     (0b)     : mã thoát 0  ĐẠT
   bộ đo        (1)      : mã thoát 0  ĐẠT
EXIT RUNNER = 0
```

13 lệnh con, mã thoát thật (`-9` = SIGKILL, `0` = không giết):

```
  [01] mã thoát -9   | SIGKILL tai sau_ghi_2 (khong_giao_dich)   ← ĐỐI CHỨNG ÂM
  [02] mã thoát 0    | SIGKILL tai khong (that)                  ← ĐỐI CHỨNG DƯƠNG
  [04] mã thoát -9   | SIGKILL tai truoc_begin (that)
  [05] mã thoát -9   | SIGKILL tai sau_ghi_1 (that)
  [06] mã thoát -9   | SIGKILL tai sau_ghi_2 (that)
  [07] mã thoát -9   | SIGKILL tai sau_ghi_3 (that)
  [08] mã thoát -9   | SIGKILL tai sau_ghi_4 (that)
  [09] mã thoát -9   | SIGKILL tai truoc_commit (that)
  [10] mã thoát -9   | SIGKILL tai sau_commit (that)
  [11] mã thoát -9   | SIGKILL tai sau_ghi_2 (that)              ← ca WAL
  [12] mã thoát -9   | SIGKILL tai truoc_commit (that)           ← ca WAL
  [13] mã thoát -9   | SIGKILL tai sau_commit (that)             ← ca WAL
```

SHA-256 (16 ký tự đầu) của các tệp **đang được đo** và tệp **đo**:

| SHA-256 (16) | Tệp | Vai |
|---|---|---|
| `90f0980779135cc4` | `app/csdl.py` | **mã đang được đo** (KHÔNG sửa) |
| `70dea30723bd431e` | `app/tai_chinh.py` | **mã đang được đo** (KHÔNG sửa) |
| `dd844fe1c54ac684` | `app/thu/thu_g18_crash.py` | bộ đo (31 ca) |
| `2e984cf63f424aba` | `trien_khai/g18-crash/chot_an_toan.py` | 7 chốt + tự kiểm |
| `2c8e34260333804b` | `trien_khai/g18-crash/do_giet.py` | động cơ giết + bộ đo toàn vẹn |
| `daf88714d8dfe536` | `trien_khai/g18-crash/do_postgres.py` | cụm PG riêng + kịch bản |
| `9d697d6643e23636` | `trien_khai/g18-crash/tien_trinh_giao_dich.py` | tiến trình con bị giết |
| `4050fc5a66fd1829` | `trien_khai/g18-crash/chay_do.sh` | bộ chạy |

**Số ca:** `Ran 31 tests … OK` (mã thoát 0) · 14 ca chốt an toàn · 3 ca tự kiểm cái móc ·
**0 ca BỎ QUA** trong lượt này (PostgreSQL có mặt và đã chạy).

### 9.5 Dọn dẹp — không để lại tiến trình mồ côi

| Việc | Cách | Ca canh |
|---|---|---|
| Nền tạm SQLite | `tempfile.mkdtemp` ngoài cây dự án, `shutil.rmtree` trong `tearDownClass` | `E.test_e2` |
| Cụm PostgreSQL | `pg_ctl stop -m fast` theo **đúng PID postmaster**, xoá thư mục dữ liệu + socket | `E.test_e3` (hỏi lại từng PID) |
| Tiến trình con | hỏi **TỪNG PID đã spawn** bằng `os.kill(pid, 0)` | `E.test_e1` |

`E.test_e1` hỏi từng PID chứ không `ps | grep`: `ps` tìm theo **TÊN**, và trên máy nhiều làn thì
"còn tiến trình tên X" không nói được nó là của làn nào. (Ở môi trường đo, `ps` còn bị chốt của
sandbox chặn — `PermissionError: 'ps'` — nhưng cách hỏi từng PID là cách **chặt hơn**, không
phải cách lách.)

**CSDL thật không bị đụng.** Sự thật này được ghi kèm MỐC THỜI GIAN, vì nó đã đổi giữa lượt:

* **Lúc bắt đầu lượt đo:** `app/du-lieu/` **không tồn tại** (`ls app/du-lieu/` → `No such file or
  directory`). Lượt đo không thể ghi vào một thư mục không có, kể cả khi chốt C1 hỏng.
* **Sau khi chạy `chay_tat_ca.sh`:** thư mục ấy **đã được tạo**, chứa **đúng một tệp**
  `khoa-noi-bo.key` (32 byte, mốc 18:56:18) — do các bộ thử KHÁC của dự án sinh ra khi nạp
  `bao_mat`, không phải do làn này.
* **Điều quan trọng, và vẫn đúng:** `app/du-lieu/hub.db` — **CSDL NGHIỆP VỤ** — **KHÔNG hề tồn
  tại**. `ls app/du-lieu/` chỉ ra `khoa-noi-bo.key`. Không có CSDL nghiệp vụ nào được tạo, được
  mở, hay được ghi trong suốt lượt này.

Và cụm `:5432` vẫn là postmaster **58873**, cùng thời điểm khởi động, cùng 6 CSDL — xem mục 5.1.

**Nền tạm:** lượt chạy bình thường **không để lại gì** — đo bằng cách chạy bộ đo với
`TMPDIR=/tmp/vhg18-audit` rồi đếm: thư mục tạm rỗng. Một lượt **đứt giữa đường** thì
`tearDownClass` không chạy tới; `atexit` (`_don_nen_con_lai`) hứng được mọi đường thoát
**trừ `SIGKILL`** — và nói ra giới hạn đó là một phần của phép đo, không phải một lời xin lỗi.

---

## 10. TỆP CỦA LƯỢT NÀY

| Tệp | Vai |
|---|---|
| `app/thu/thu_g18_crash.py` | **bộ đo** — 31 ca: tự kiểm bộ đo · SQLite 7 điểm giết · WAL · PostgreSQL 9 lượt · dọn dẹp |
| `trien_khai/g18-crash/chot_an_toan.py` | **bảy chốt an toàn** + `--tu-kiem` trên 14 cấu hình tổng hợp |
| `trien_khai/g18-crash/do_giet.py` | động cơ giết (`set_trace_callback`) · bộ đo toàn vẹn · `--tu-kiem-moc` |
| `trien_khai/g18-crash/tien_trinh_giao_dich.py` | **tiến trình con bị giết** — chạy `tai_chinh.chuyen_cod` thật rồi tự `SIGKILL` |
| `trien_khai/g18-crash/do_postgres.py` | cụm PostgreSQL riêng · kịch bản 5 câu ghi · giết client/backend · đo |
| `trien_khai/g18-crash/chay_do.sh` | bộ chạy: chốt → móc → bộ đo → tổng kết bằng mã thoát |
| `docs/G18_CRASH.md` | tệp này |

**KHÔNG sửa tệp nào đang có.** `git status --porcelain` trên nhánh `g18-ag06-crash` chỉ ra **hai
đường dẫn MỚI**, không một dòng `M`:

```
?? app/thu/thu_g18_crash.py
?? trien_khai/g18-crash/
```

`app/csdl.py` (AG-00 sở hữu) **không bị đụng** — SHA `90f0980779135cc4` ở mục 9.4 là SHA của
bản `7b741c8` nguyên trạng.

---

## 11. VIỆC CÒN LẠI

| Việc | Vì sao |
|---|---|
| `V-13914(b)` — máy chủ HTTP thật dưới tải | chưa đo; bàn đo hiện gọi thẳng hàm |
| `V-13914(c)` — trần chống lạm dụng nhiều tiến trình | chưa đo; là **điều kiện kích hoạt số 2** của kế hoạch PostgreSQL |
| `V-13912` — **5 khối ghi còn lại** chưa bọc `csdl.giao_dich()` | lượt này chỉ chứng minh `giao_dich()` đúng ở **một** giao dịch. Năm khối kia chưa được đo bằng khuôn này |
| Lượt kiểm toàn vẹn lúc khởi động (mục 6) | đề xuất, cần anh Thành quyết |
| Đo **mất điện** (`synchronous`) | cần cắt nguồn thật hoặc `kill -9` cả máy ảo — ngoài phạm vi một worktree |
| Cổng "cây sạch" F0-a của `thu_qa_g17.py` (mục 9.3b) | cần thêm mẫu quyền sở hữu cho làn G18/AG-06, **hoặc** commit khi gộp. Tệp đó **ngoài danh sách được cấp**, nên lượt này không sửa |
| Môi trường git của phiên (`GIT_CONFIG_KEY_0` thiếu) | làm đỏ `thu_tich_hop.py` + `thu_bao_mat.py`; **có trước** lượt này, ngoài phạm vi làn |
