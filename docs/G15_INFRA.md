# G15 — HẠ TẦNG: đo được gì, và cái gì **BLOCKED**

Mã việc: **I01 · I02 · I03 · I04** · người làm: **AG-04 (INFRASTRUCTURE ENGINEER)** ·
ngày **15/10/2026** · HEAD lúc làm: `de740dc` (worktree Orca).

> **Kho nghiệp vụ VẪN LÀ SQLITE.** Lượt này **KHÔNG** chuyển gì. Quyết định **D-8** của anh
> Thành: *tiếp tục SQLite local; **thử** PostgreSQL trước khi quyết định triển khai SaaS nhiều
> người dùng.* Chỉ thị G12 mục 8: **KHÔNG** tự chuyển CSDL nghiệp vụ. Mọi số về PostgreSQL
> dưới đây đến từ một **cụm dùng-một-lần, cổng riêng, đã dọn sạch**.

---

## 0. TRẢ LỜI NGẮN

| Việc | Kết quả |
|---|---|
| **I01** trạng thái G12 | **KHÔNG có hồi quy.** Hồi quy đầy đủ **1.133 ca · 34 bộ · 0 hỏng · mã thoát 0**. Playwright tầng 3: **26 đạt · 1 bỏ qua · mã thoát 0**. Đồng thời 8 tiến trình × 400 phép × 3 ca = **9.600 lượt: 0 khoá hết giờ · 0 giao dịch hỏng · 0 mất cập nhật** |
| **I02** bốn kết cục | **Tách được cả bốn, và kết cục thứ tư thì IM LẶNG.** Phát hiện chính: cùng một khuôn đọc-rồi-ghi, **SQLite TỪ CHỐI ỒN ÀO** (0 mất cập nhật) còn **PostgreSQL IM LẶNG MẤT 70%** |
| **I03** an toàn migration | Migration **nguyên tử** trên cả hai kho · **đúng 1 tiến trình** nâng cấp (khoá SQLite 8 tiến trình + khoá tư vấn PostgreSQL) · DDL lùi **sạch** khi hỏng giữa khối · sao lưu/khôi phục giữ **số dòng · số cột · tổng tiền · md5 nhị phân** |
| **I04** hạ tầng cục bộ | Health/readiness **chạy thật qua HTTP** + **đối chứng âm** · bí mật là tệp `0600`, không vào log · log có cấu trúc **nay ĐÃ nối vào đường HTTP** (P-G15-01 — 20 đạt · 0 hỏng · 1 BLOCKED · 0 khiếm khuyết) · trần tần suất **nhân theo số bản** (B-G11-10) · **Docker = BLOCKED** |

**Cụm PostgreSQL `:5432` KHÔNG BỊ ĐỤNG.** Bằng chứng ở §2.3.

---

## 1. I01 — TRẠNG THÁI G12: XÁC MINH LẠI, KHÔNG LÀM LẠI

Không suy từ tài liệu. Mỗi dòng dưới đây là một lượt chạy thật ngày 15/10/2026 trong worktree
Orca, `VIP_HUB_DATA=/tmp/veh_data_ag04/…`.

### 1.1 Bốn lệnh của `docs/BAN_GIAO.md` §4

```bash
sh app/thu/chay_tat_ca.sh          # 1.133 ca · 34 bộ · 0 hỏng · mã thoát 0
sh thu_giao_dien/chay.sh           # 26 passed · 1 skipped · mã thoát 0 · 33,8 giây
python3 app/thu/dong_thoi/chay.py  # 8 tiến trình × 400 phép × 3 ca
```

| Bộ | Số ca | Kết quả |
|---|---|---|
| Hồi quy python | **1.133 ca / 34 bộ** | 0 hỏng · mã thoát **0** |
| Frontend tầng 1 (logic thuần) | 56 ca | đạt |
| Frontend tầng 2 (HTTP + tệp tĩnh) | 36 ca | đạt |
| Frontend tầng 3 (Chromium thật) | 27 ca | **26 đạt · 1 bỏ qua** · mã thoát **0** |
| E2E qua HTTP thật | 41 phép | **41/41** |

**So với mốc bàn giao:** `BAN_GIAO.md` ghi *927 ca · 29 bộ*. Nay **1.133 ca · 34 bộ** — phần lớn
mức tăng là do các làn G13–G15 viết song song trong cùng thư mục này; **lượt này thêm 12 ca**:
4 ca PostgreSQL (lớp `E`) + 8 ca P-G15-01. **0 hỏng ở cả hai mốc.**

> **Con số 1.133 là DỮ KIỆN ĐO ĐƯỢC, không phải hằng số.** Các làn khác đang ghi cùng thư mục,
> nên số ca sẽ còn đổi. Đọc **`bộ hỏng: KHÔNG` và mã thoát**, đừng đọc mỗi tổng số.

### 1.2 Bàn đo đồng thời — bốn kết cục, đúng yêu cầu I02

```bash
VIP_HUB_DATA=/tmp/veh_data_ag04 python3 app/thu/dong_thoi/chay.py
```

| Ca | CHỐT THÀNH CÔNG | TỪ CHỐI NGHIỆP VỤ | **KHOA_HET_GIO** | **GIAO_DICH_HONG** | Đối chiếu cuối lượt |
|---|---|---|---|---|---|
| 1. Sổ cái tài chính | 3200 | 0 | **0** | **0** | sổ 3.200.000đ = tiến trình tin = công nợ |
| 2. Đọc–sửa–ghi cùng hàng | 3200 | 0 | **0** | **0** | **MẤT CẬP NHẬT = 0** |
| 3. Trần hạn mức (trần 400) | 400 | 2800 | **0** | **0** | bộ đếm CSDL = 400, không vượt |

Thời gian mỗi tiến trình: ca 1 `0,5s` · ca 2 `0,3–0,4s` · ca 3 `0,1s`. **Không hồi quy** so với
`DATABASE_CONCURRENCY_REPORT.md` §4.

### 1.3 Giao dịch · khoá migration · sao lưu khoá

| Bộ thử | Số ca | Kết quả | Nó canh cái gì |
|---|---|---|---|
| `app/thu/thu_giao_dich.py` | **17** | OK · mã thoát 0 | hai câu ghi cùng vào hoặc cùng không · SAVEPOINT lồng · bậc lồng về 0 sau khi hỏng · COD không nhảy trạng thái khi bút toán hỏng |
| `app/thu/thu_migrate_dong_thoi.py` | **8** | OK · mã thoát 0 | 8 tiến trình hệ điều hành → **đúng 1** nâng cấp · `executescript` tự COMMIT · không cắt trigger theo `;` · không tự khoá chính mình |
| `app/thu/thu_bien_driver.py` | **5** | ĐẠT | chỉ `csdl.py` nạp driver (dò bằng AST) · 0 chỗ `kn.commit()/rollback()` |
| `app/thu/thu_xoay_khoa.py` | **30** | OK · mã thoát 0 | khoá: sao lưu/khôi phục/diễn tập trên nền cô lập, **không** xoay khoá thật |

**Không có hồi quy ở bất kỳ mục nào.** Ba bộ này là chốt chặn của `SHARED_CONTRACTS.md` §30.

### 1.4 Một lượt HỎNG GIẢ đã gặp, và nó KHÔNG phải hồi quy

Trong lượt hồi quy lúc `14:35`, `thu_webhook_jt.py` báo hỏng ca
`test_i05_phan_hoi_HTTP_THIEU_truong_code_da_biet_tu_cau_9`. Chạy lại **một mình** hai phút sau:
**67 ca · OK · mã thoát 0** — và tên ca đã đổi thành `..._CO_truong_code_bang_1...`.

Nguyên nhân: **AG-03 đang sửa chính tệp đó trong lúc bộ chạy đọc nó** (cùng thư mục, việc song
song có chủ ý). Đây không phải hồi quy của hệ và không phải của lượt này.
**Luật rút ra:** hồi quy chạy trong thư mục có agent khác đang ghi thì một lượt đỏ **chưa đủ**
để kết luận — phải chạy lại tệp đó một mình trước khi báo hỏng.

### 1.5 Phép đo phụ thuộc TẢI MÁY — một lớp hỏng giả, và cách sửa

Trong ba lượt hồi quy đầy đủ ở máy đang có agent khác chạy, **hai lượt đỏ ở hai bộ KHÁC NHAU**,
và cả hai đều **xanh khi chạy một mình**:

| Lượt | Bộ báo đỏ | Chạy một mình | Chạy lại dưới tải nhân tạo |
|---|---|---|---|
| 1 | `thu_webhook_jt.py` (`test_i05_…`) | **OK · 67 ca** | — (nguyên nhân: AG-03 đang sửa chính tệp đó, §1.4) |
| 2 | `thu_migrate_dong_thoi.py` (`test_a1_…`) | **OK · 8 ca** | **4 bản song song + tải nền: 4/4 OK** |
| 3 | `thu_postgres.py` (lớp `E`, ca e2/e3 **bản đầu**) | **OK · 25 ca** | — |

**Lượt 3 là lỗi của CHÍNH TÔI, và đã sửa.** Bản đầu của ca e2/e3 đo bằng **cách chạy đua**: hai
tiến trình cùng đọc–ghi, đếm xem mất bao nhiêu lượt. Nó **đúng về bản chất** nhưng **hỏng khi máy
tải**: nếu hệ điều hành xếp hai tiến trình chạy nối đuôi thì không mất lượt nào, và ca thử báo
HỎNG trong khi hệ làm đúng — đúng loại "báo hỏng giả" mà `BAN_GIAO.md` §7.1 cảnh báo.

**Đã đổi cấu trúc, không vá thêm** (§12.2): hai phiên **BẮT TAY BẰNG TỆP MỐC** — mỗi bên đọc
xong thì chạm tệp mốc của mình rồi chờ tệp mốc của bên kia, **cả hai đã đọc xong mới cho ghi**.
Không còn phụ thuộc lịch trình của hệ điều hành, và phép đo **mạnh hơn**: nó chỉ ra thẳng **cơ
chế** thay vì đếm xác suất.

| | Bản đầu (chạy đua) | Bản nay (bắt tay) |
|---|---|---|
| Phép đo | đếm số lượt mất trên 50 lượt | hai phiên cùng đọc `0`, cùng ghi `1` → giá trị cuối **phải là 1** |
| Phụ thuộc tải | **có** | **không** |
| Kiểm chứng | chạy riêng 3/3 đạt | **4 bản song song + tải nền: 4/4 đạt** |

**Phép đo thống kê vẫn giữ**, nhưng ở đúng chỗ của nó: `trien_khai/postgres/dien_tap_chuyen.py`
(chạy **theo yêu cầu**, không nằm trong hồi quy) — ở đó một lượt lệch tải chỉ làm con số nhỏ đi,
không làm đỏ cổng chặn.

**Một lớp hỏng giả CÒN LẠI, không thuộc tệp của tôi — báo lại, không tự sửa:**
`app/thu/thu_migrate_dong_thoi.py` ca `a1` dùng **vạch xuất phát hẹn giờ**:
`BAT_DAU = time.time() + 2.0` đặt ở tiến trình cha, rồi 8 tiến trình con tự `import migrate`
**rồi mới** chờ tới `BAT_DAU`. Nếu một tiến trình con nạp mô-đun **lâu hơn 2 giây** (máy tải),
nó khởi động **sau** vạch và về sớm theo đường "đọc ngoài khoá đã thấy phiên bản đích" — nên
`nhuong_trong` giảm, và nếu **mọi** tiến trình đều trễ thì ca `assertGreaterEqual(nhuong_trong, 1)`
đỏ với thông điệp *"không tiến trình nào chờ khoá rồi nhường"*. **Đo được: 1/3 lượt hồi quy đầy
đủ, 0/6 lượt chạy riêng, 0/4 lượt chạy 4 bản song song.** Đây là **hỏng giả của phép đo**, không
phải lỗi của `migrate.py`. **Đề xuất (không tự làm, tệp không thuộc quyền tôi):** thay hẹn giờ
bằng **vạch xuất phát THẬT** — mỗi con ghi một tệp "sẵn sàng", cha đợi đủ 8 tệp rồi mới đặt mốc
giờ. Hẹn giờ là đoán; tệp báo sẵn sàng là đo.

---

## 2. I02 — BỐN KẾT CỤC, VÀ KẾT CỤC THỨ TƯ THÌ IM LẶNG

### 2.1 Bảng đối chiếu — SQLite so với PostgreSQL

Cùng **một** khuôn đọc-rồi-ghi ngây thơ (đọc ở kết nối riêng, ghi lại giá trị đã đọc), chạy
bằng **tiến trình hệ điều hành thật**, 4 tiến trình:

| Kết cục | SQLite 3.51.0 | PostgreSQL 16.15 | Phân biệt bằng gì |
|---|---|---|---|
| **CHỐT_THÀNH_CÔNG** (cộng ở tầng câu `x = x + 1`) | 160/160 chốt · 0 lỗi | 480/480 chốt · 0 lỗi | đối chiếu cuối lượt: TIN = THẬT |
| **KHOA_HET_GIO** | 18–51 lượt `OperationalError: database is locked` | SQLSTATE **`55P03`** (`lock_not_available`) | SQLSTATE / tên ngoại lệ |
| **GIAO_DICH_HONG** | `RAISE(ABORT)` huỷ **CÂU**, câu sau vẫn chốt | **`P0001`** + **`25P02`** — huỷ **CẢ giao dịch**, câu sau bị chối | SQLSTATE |
| **MẤT_CẬP_NHẬT** | **0** — nó TỪ CHỐI thay vì mất | **84/120 lượt chốt (70%) — 0 lượt nào báo lỗi** | **chỉ** đối chiếu cuối lượt |

```bash
# Tái hiện (tự dựng cụm riêng, tự dọn; TỪ CHỐI cổng 5432)
python3 app/thu/thu_postgres.py -v            # 25 ca · ~2 giây
python3 trien_khai/postgres/dien_tap_chuyen.py --so-tien-trinh 4 --so-phep 120
```

### 2.2 Vì sao đây là phát hiện quan trọng nhất của lượt này

Câu đang được báo là *"SQLite đọc-rồi-ghi hỏng khi nhiều tiến trình"*. Đo ra thì **đúng một
nửa, và nửa đúng đó lại là tin tốt**: SQLite **không mất dữ liệu** — nó **từ chối ồn ào**
(`database is locked`), người gọi thấy ngay và thử lại được.

**PostgreSQL với cùng khuôn mã đó thì mất 70% số lượt ghi, im lặng hoàn toàn.** Nghĩa là:

> **Chuyển CSDL mà giữ nguyên khuôn đọc-rồi-ghi là ĐỔI một lỗi ỒN ÀO lấy một lỗi IM LẶNG.**
> Với sổ tiền thì đó là đổi một lỗi nhìn thấy được lấy một lỗi không ai thấy.

PostgreSQL **không tự sửa** kết cục thứ tư. Chỉ hai cách sửa, và cả hai đều là sửa **MÃ**, không
phải sửa **KHO**:
1. cộng ở **tầng câu** (`UPDATE … SET x = x + 1`), hoặc
2. `SELECT … FOR UPDATE` / `REPEATABLE READ` + xử `40001`.

**Hệ quả cho kế hoạch migration:** chặng 1 (lớp phương ngữ `csdl.py`) **không được** đi tách rời
khỏi việc soát từng chỗ đọc-rồi-ghi. Chặng 1 một mình **làm hệ TỆ HƠN** ở đúng 5 khối ghi còn
lại mà `BAN_GIAO.md` §6.1 đã liệt kê (`don_hang.py:944` · `tai_chinh.py:673` · `usage.py:220` ·
`don_hang.py:854` · `tai_chinh.py:385`).

### 2.3 Cụm PostgreSQL RIÊNG — và cụm `:5432` KHÔNG BỊ ĐỤNG

**Cụm thử** (`trien_khai/postgres/dien_tap_chuyen.py` §0 in ra, và nó tự kiểm bằng `lsof`):

```
datadir = /var/folders/…/T/vhdt-xxxx/data     ← KHÁC /opt/homebrew/var/postgresql@16
port    = 55432                                ← KHÁC 5432 (chốt chặn TỪ CHỐI nếu là 5432)
listen_addresses = (rỗng)                      ← KHÔNG mở cổng TCP nào
unix_socket_directories = /tmp/vhpg.XXXX       ← đường NGẮN (giới hạn sun_path 103 byte)
lsof -iTCP:55432 -sTCP:LISTEN → rỗng           ← bằng chứng, không phải lời hứa
```

**Vân tay cụm `:5432` TRƯỚC và SAU toàn bộ lượt diễn tập:**

| Trường | Trước | Sau |
|---|---|---|
| PID postmaster (`lsof -iTCP:5432`) | `58873` | `58873` |
| `pg_postmaster_start_time()` | `2026-10-09 10:24:22.104803+07` | `2026-10-09 10:24:22.104803+07` |
| Danh sách CSDL | `postgres, template0, template1, vip_customs, vip_customs_g16, vip_customs_test` | **y nguyên** |
| Số kết nối tới `vip_customs*` | 0 | **0** |

PID và giờ khởi động không đổi ⇒ cụm **không hề bị restart**; danh sách CSDL không đổi ⇒
**không** CSDL nào bị tạo/xoá ở đó. Cụm thử đã **dừng bằng `pg_ctl stop -m immediate`** và
**xoá sạch** thư mục dữ liệu + socket (kiểm lại: `lsof -iTCP:55432` rỗng, không còn
`/tmp/vhpg.*`, không còn `vhdt-*`). **KHÔNG dùng `pkill`/`killall`** (`CLAUDE.md` §16.7 — một
lệnh `pkill -f postgres` ở đây sẽ giết luôn cụm `:5432` của dự án khác).

### 2.4 Mã đã dùng

| Tệp | Vai trò |
|---|---|
| `app/thu/thu_postgres.py` lớp `E_BonKetCuc` **MỚI** | **4 ca** canh bảng §2.1 **ngay trong hồi quy** — gồm ca đối chứng SQLite. Bỏ ca e2/e3 đi là mất bằng chứng cho phát hiện chính |
| `trien_khai/postgres/dien_tap_chuyen.py` **MỚI** | diễn tập đầy đủ trên cụm riêng: danh tính cụm · bốn kết cục · khoá migration · DDL nguyên tử + đối chứng âm · sao lưu/khôi phục |
| `trien_khai/postgres/sinh_ddl_pg.py` (có sẵn) | sinh DDL PostgreSQL **từ chính schema SQLite đang chạy** — không có bản sao thứ hai để lệch |
| `trien_khai/postgres/do_ghi_dong_thoi.py` (có sẵn) | so thông lượng SQLite ↔ PostgreSQL (khác mục đích: **thông lượng**, không phải bốn kết cục) |

---

## 3. I03 — AN TOÀN MIGRATION

### 3.1 Bốn tính chất, và chốt chặn của từng cái

| Tính chất | Cách chứng minh | Kết quả |
|---|---|---|
| **Nguyên tử** | nạp DDL THẬT (47 bảng, 431 cột) trong MỘT giao dịch | đạt. **Đối chứng âm:** chèn một câu sai vào cuối khối → **0/47 bảng** còn lại, kể cả bảng đứng TRƯỚC câu sai. Đối chứng **dương** cùng khối không chèn gì → **47 bảng** |
| **Hai tiến trình không bao giờ migration cùng lúc** | SQLite: 8 tiến trình thật (`thu_migrate_dong_thoi.py` a1) → **đúng 1** nâng cấp. PostgreSQL: 2 tiến trình tranh `pg_advisory_xact_lock` → **nâng=1 · nhường=1 · lỗi=0**, phiên bản cuối = 8 | đạt cả hai kho |
| **Lùi được** | `SAVEPOINT` lồng bao nhiêu tầng cũng được (`thu_giao_dich.py` a4–a7); `migrate.chay_ddl_trong_giao_dich()` tách câu bằng `csdl.cau_sql_du` **chứ không** `split(";")` — khối `CREATE TRIGGER … BEGIN …; END;` có `;` bên trong | đạt |
| **Sao lưu / khôi phục** | `pg_dump -Fc` → `pg_restore` sang CSDL khác → so **từng bảng** về số dòng, so **431 cột**, so **số bút toán + tổng tiền**, so **md5 của payload nhị phân** | khớp **tất cả** |

### 3.2 Bảy cái bẫy SQLite của `BAN_GIAO.md` §5 — lượt này CHẠM LẠI ba cái

Không suy lại từ tài liệu; ba cái dưới đây được **đo lại** trong lớp `E`/`B` của
`thu_postgres.py`:

- **`RAISE(ABORT)` huỷ CÂU, không huỷ giao dịch** — đo lại trên PostgreSQL để thấy vế đối
  diện: `P0001` + **`25P02`**, câu sau trigger **không chạy**, và bút toán 777.000đ **bị lùi**.
  Đây là chỗ **nguy hiểm nhất khi chuyển kho**: mã nào đang nuốt `LoiToanVen` rồi đi tiếp thì
  trên SQLite câu sau **vẫn vào**, còn trên PostgreSQL nó **im lặng không vào**.
- **`executescript()` tự COMMIT** — chốt chặn `thu_migrate_dong_thoi.py` b1 vẫn xanh.
- **`SAVEPOINT` trần mở giao dịch HOÃN** → `SQLITE_BUSY_SNAPSHOT` trả **ngay**, `busy_timeout`
  không chờ. Chốt chặn: `csdl.giao_dich()` tầng ngoài dùng `BEGIN IMMEDIATE`; lớp `E` ca e3
  đo lại hệ quả "SQLite từ chối ồn ào" ở tầng tiến trình.

### 3.3 Đường lùi GIẢ phải bị chặn trước khi chuyển

`migrate.sao_luu()` hiện là `sqlite3.Connection.backup()`. Trên PostgreSQL hàm đó **vô dụng mà
vẫn chạy trót lọt** — nó tạo ra một tệp "bản sao" **không chứa gì** của PostgreSQL, và hệ vẫn
báo sao lưu thành công. Đây là **đường lùi giả**, nguy hiểm hơn không có đường lùi vì nó làm
người vận hành tin rằng mình có thể khôi phục.

**Đề xuất P-G15-02 (chưa làm, cần AG-00 duyệt vì chạm `migrate.py`):** khi (và chỉ khi) kho
đổi sang PostgreSQL, `sao_luu()` phải **ném `NotImplementedError`** thay vì chạy
`Connection.backup()`. Một hàm không làm được việc của nó thì phải **nổ**, không được im lặng
thành công.

---

## 4. I04 — HẠ TẦNG CỤC BỘ

Chạy: `python3 trien_khai/g15/kiem_ha_tang.py` → **20 đạt · 0 hỏng · 1 BLOCKED · 0 KHIẾM KHUYẾT**.

> **Đo TRƯỚC khi vá P-G15-01: 19 đạt · 0 hỏng · 1 BLOCKED · 1 KHIẾM KHUYẾT.** Mục `P5d` ("đường
> phục vụ HTTP ghi log có cấu trúc") là mục **KHIẾM KHUYẾT** đó; nay nó **ĐẠT**. Phán quyết
> `KHIẾM KHUYẾT` được giữ lại trong bộ kiểm vì nó vẫn cần cho các lượt sau: nó tách khỏi `HỎNG`
> (bộ kiểm chạy đúng) và khỏi `ĐẠT` (không giấu khoảng trống đi).

### 4.1 Docker — **BLOCKED**, và KHÔNG cài

```
docker = KHÔNG CÓ · podman = KHÔNG CÓ · colima = KHÔNG CÓ · docker-compose = KHÔNG CÓ
brew   = /opt/homebrew/bin/brew   (CÓ — nên cài được, NHƯNG cài là ĐỔI MÁY CỦA ANH THÀNH)
```

Cài đặt cần anh Thành duyệt (`V-13913`, `SHARED_CONTRACTS.md` §27/§29). **Lượt này KHÔNG cài.**

> **`Dockerfile` (4.681 byte) + `docker-compose.yml` (3.485 byte) + `.dockerignore` (1.744 byte)
> ĐÃ VIẾT nhưng CHƯA CHẠY LƯỢT NÀO.** Ở đây chỉ kiểm **sự tồn tại và kích thước** ở mức tĩnh.
> **KHÔNG có và KHÔNG được có dòng "Docker build PASS" nào trong tài liệu này.**
> Hệ quả kèm theo: `HEALTHCHECK` trong `Dockerfile`, `read_only: true`, `tmpfs`, `security_opt`
> của compose — **chưa được chứng minh bằng lượt chạy nào**.

### 4.2 Health và readiness — đo từ NGOÀI, và có ĐỐI CHỨNG ÂM

| Phép đo | Kết quả |
|---|---|
| `GET /api/v2/suc-khoe` trên nền đã migrate | **200** · `{"ok":true, "song_giay":…, "pid":…}` |
| `GET /api/v2/san-sang` trên nền đã migrate | **200** |
| `sh trien_khai/kiem_san_sang.sh` (cổng do AG-05 viết, gọi từ ngoài) | **mã thoát 0** · `SAN SANG (HTTP 200) sau 1 luot thu` |
| Readiness (đã đăng nhập) chạy HẾT phép kiểm | `csdl · khoa · schema · thu_muc_du_lieu · worker` + trường `pham_vi` nói rõ cái gì NGOÀI phạm vi |
| **ĐỐI CHỨNG ÂM:** nền migrate ĐỦ nhưng **THIẾU KHOÁ** | **503**, và **chỉ** `khoa` hỏng, 4 phép kia vẫn chạy (**không ngắn mạch**) |
| **CÙNG nền đó:** `suc-khoe` | vẫn **200** — đúng chủ ý: health điều khiển restart, readiness điều khiển nhận việc |

**Một vấp đáng ghi:** định dựng đối chứng âm bằng một nền **chưa migrate** thì máy chủ **từ chối
khởi động** (`CSDL ở schema v0, mã nguồn cần v8`, mã thoát 3) — nên `readiness` **không có dịp**
trả 503 cho ca đó. Đó là hành vi **tốt** (chặn sớm hơn), nhưng nghĩa là phép đo phải đổi chỗ
vấp: làm hỏng thứ mà máy chủ **không** kiểm lúc khởi động (khoá). Tệp khoá được **CHUYỂN** sang
đuôi `.bo` trong nền tạm, **không xoá cứng** (`CLAUDE.md` §19).

> Không có đối chứng âm thì mục 4.2 vô nghĩa: một cổng luôn trả `ok` **trông y hệt** một cổng
> đang chạy đúng (§12.1 luật 1).

### 4.3 Quản lý bí mật

| Phép đo | Kết quả |
|---|---|
| Khoá mã hoá là **TỆP trên đĩa**, mode `0600` | đạt (`goc.key`, `0o600`) — **nội dung khoá KHÔNG bị in ra** |
| `.env.example` không chứa master key | đạt — không có dòng `VIP_HUB_MASTER_KEY/SECRET/KHOA` nào |
| Log khởi động không chứa mật khẩu / bản mã | đạt — đã quét, 0 dòng khớp |
| Bí mật hãng mã hoá at-rest | đạt — xem `docs/G15_E2E_HARNESS.md` bước **B03c** (chỉ kiểm **tiền tố dạng** `v3$<key_id>$…`, **không** in giá trị) |

### 4.4 Log có cấu trúc — **P-G15-01 ĐÃ VÁ** (AG-00 cấp quyền ghi `app/server.py`)

**Đo được TRƯỚC khi vá:** `quan_sat` có đủ mô-đun (JSONL, `request_id`, bộ che, metric) nhưng
`server.py` **chỉ** gọi nó cho `/suc-khoe`, `/san-sang`, `/metric`. `bat_dau_yeu_cau()` /
`ket_thuc_yeu_cau()` / `ghi()` **không được gọi ở đâu trong đường yêu cầu** ⇒ log máy chủ thật
có **0 dòng JSON**, không lượt HTTP nào có `request_id`. Cùng đúng một khuôn với **V-13910**
("mã có, nhưng không ai gọi").

**Đã vá** (một chỗ bao **mọi** route, không rải từng route):

| Chỗ sửa | Nội dung |
|---|---|
| `BoXuLy._chay()` | mở `quan_sat.bat_dau_yeu_cau()` → chạy `_chay_that()` → **`finally`** `ket_thuc_yeu_cau()` + `quan_sat.ghi("yeu_cau", …)`. `finally` vì **lượt HỎNG là lượt cần dấu vết nhất** |
| `BoXuLy.send_response()` | ghi lại mã trạng thái **đã trả thật** + gắn header **`X-Request-Id`**. Đây là chỗ **duy nhất** `BaseHTTPRequestHandler` ghi dòng trạng thái, nên `_tra`, `_tra_tep`, `send_error` và đường **tĩnh** đều có header — vá ở `_tra` là bỏ sót chỗ thứ tư |

**Dòng log chỉ mang:** `method` · `duong` (**đã CẮT query** — query có thể mang token) ·
`ma_http` · `ms` · `request_id` · `correlation_id` · `luc` · `pid` · `thread`.
**KHÔNG** body · **KHÔNG** header · **KHÔNG** cookie.

**Vấp đã gặp và nó chỉ ra một chốt chặn tốt:** lượt vá đầu dùng tên trường `phuong_thuc`/`ma`.
`quan_sat.che()` dùng **DANH SÁCH TRẮNG** tên trường (`TRUONG_CHO_PHEP`), nên cả hai bị thay
bằng `***` — dòng log ra `"ma": "***"`. Ca `a2` bắt được ngay. **Tên trường đúng là `method`
và `ma_http`**, đã có sẵn trong danh sách trắng. Đây là ví dụ đúng của nguyên tắc: danh sách
**trắng** sai thì hỏng ồn ào; danh sách **đen** sai thì rò im lặng.

**Ca thử mới** — `app/thu/thu_nhat_ky_yeu_cau.py`, **8 ca**, mã thoát 0:

| Ca | Khẳng định |
|---|---|
| a1 | gọi 3 route THẬT → log có **> 0** dòng JSON (ca này **đỏ** trước khi vá) |
| a2 | mọi dòng `yeu_cau` đủ trường, `request_id` đúng dạng, `ma_http` là **số** (không bị che) |
| a3 | header `X-Request-Id` **khớp** một dòng log — đối chiếu được log ↔ yêu cầu |
| a4 | lượt **401/404 vẫn có dòng log** (canh `finally`; đổi thành cuối hàm là ca này đỏ) |
| a5 | đường dẫn khớp thật, và **query bị cắt** (token giả không lọt) |
| a6 | **mật khẩu trong body KHÔNG lọt vào log** (chuỗi GIẢ), không có trường `mat_khau`/`headers`/`cookie` |
| a7 | mỗi dòng là **một JSON parse được**, dưới 8 KB |
| a8 | đường **TĨNH** cũng có `X-Request-Id` (canh việc vá chỉ ở `_tra`) |

### 4.5 Trần tần suất — **B-G11-10 nay có SỐ, không còn là suy luận**

```
Luật của auth.dang_nhap: [Luat(ip, 20/300s), Luat(dinh_danh, 12/300s, chặn 900s)]
```

| Phép đo | Kết quả |
|---|---|
| **MỘT** tiến trình | cho qua **20** lượt rồi **429** — trần khai đúng |
| **HAI** tiến trình, **cùng IP**, **cùng CSDL**, khác PID | bản A chặn ở 20 · bản B **vẫn cho qua 20 lượt nữa** ⇒ **trần thực tế 40 = gấp đôi khai báo** |

`gioi_han` giữ bộ đếm trong **bộ nhớ MỘT tiến trình** (`_lan`, `_chan_den`). Nhiều bản ⇒ trần
**nhân theo số bản**.

**Ảnh hưởng cụ thể khi chạy nhiều tiến trình máy chủ:**
- Mọi trần đều yếu đi **tuyến tính theo số bản**: 4 bản ⇒ `auth.dang_nhap` thành 80 lượt/IP/5
  phút; `auth.quen_mat_khau` (5/900s) thành 20.
- `Luat(..., chan_giay=900)` **cũng** theo từng bản: một IP bị bản A chặn vẫn vào được bản B.
- `webhook.nhan` và `webhook.chu_ky_sai` cũng vậy — cửa **vô danh** lại là chỗ dễ bị lạm dụng nhất.
- **Trần hạn mức gói thì KHÔNG bị** ảnh hưởng: nó nằm trong CSDL (`usage.ghi_su_kien`, trần đếm
  bằng câu `UPDATE` có trần). Đây là **hai cơ chế khác nhau** và chỉ một cái hỏng khi nhân bản.

**Việc phải làm TRƯỚC khi chạy nhiều bản** (không phải sau): đưa bộ đếm trần vào CSDL **hoặc**
một kho dùng chung. Đây đúng là **điều kiện kích hoạt số 2** của `POSTGRESQL_MIGRATION_PLAN.md` §1.

**NGOÀI phạm vi phép đo này:** nhiều MÁY (cùng IP qua NAT) · IPv6 · proxy thật · tải đồng thời.
Ở đây chỉ đo **số lượt được cho qua theo số tiến trình**.

---

## 5. TỆP ĐÃ THÊM / SỬA TRONG LƯỢT NÀY

| Tệp | Trạng thái | Ghi chú |
|---|---|---|
| `app/thu/thu_postgres.py` | **sửa** | +lớp `E_BonKetCuc` (4 ca): bảng bốn kết cục, **có** ca đối chứng SQLite. 21 → **25 ca**. Vá kèm: `import time`, gọi `q()` thay `Cum.psql`, đóng ống `Popen` |
| `app/thu/thu_nhat_ky_yeu_cau.py` | **MỚI** | 8 ca đối chứng dương cho P-G15-01. Tệp **mới, tên riêng** — không đè tệp của làn nào |
| `app/server.py` | **sửa — AG-00 CẤP QUYỀN riêng cho P-G15-01** | `_chay` → `_chay_that` + `send_response` gắn `X-Request-Id`. Không đổi hợp đồng route nào |
| `trien_khai/postgres/dien_tap_chuyen.py` | **MỚI** | diễn tập chuyển, cụm riêng, 26 phép |
| `trien_khai/g15/harness_e2e.py` + `chay_harness.sh` | **MỚI** | harness E2E 10 bước (I06) |
| `trien_khai/g15/kiem_ha_tang.py` | **MỚI** | kiểm hạ tầng cục bộ (I04), 5 phần |
| `docs/G15_INFRA.md` · `docs/G15_E2E_HARNESS.md` · `docs/G15_WEBHOOK_HTTPS.md` | **MỚI** | tài liệu G15 |

**KHÔNG sửa:** `app/csdl.py` · `app/migrate.py` (P-G15-02 chỉ là **đề xuất**) · `app/adapter_jt.py`
· `app/webhook.py` · `Dockerfile` · `docker-compose.yml` · `.gitignore`.

---

## 6. DANH SÁCH **BLOCKED** — CHÍNH XÁC CÁI CÒN THIẾU

| # | Việc | Mã | Thiếu chính xác cái gì |
|---|---|---|---|
| 1 | **Docker build / `docker compose up`** | `V-13913` | Không có `docker`/`podman`/`colima`/`docker-compose` trên PATH. Cài được bằng `brew` nhưng **cài là đổi máy anh Thành ⇒ phải anh duyệt**. **KHÔNG cài.** `Dockerfile` + compose **chưa chạy lượt nào**; `HEALTHCHECK`/`read_only`/`tmpfs`/`security_opt` chưa được chứng minh |
| 2 | **Triển khai staging / VPS** | `V-G11-01` | Chưa cấp. Không deploy, không tunnel, không mở cổng |
| 3 | **Gọi API hãng thật (kể cả sandbox)** | `V-G09-01` + `V-13906-05` | Chưa cấp credentials J&T sandbox. Nên chặng **sandbox** của harness E2E là **BLOCKED** (xem `G15_E2E_HARNESS.md`) |
| 4 | **Callback J&T theo sơ đồ `jt_digest`** | `V-13906-05` | Cần header digest thật của hãng. Chỉ chứng minh được sơ đồ `hub_hmac` (mock) |
| 5 | **Webhook HTTPS ra Internet** | `V-G11-01` | Không có tên miền, không TLS, không reverse proxy. **Chỉ có thiết kế** — `G15_WEBHOOK_HTTPS.md` |
| 6 | **Chuyển CSDL nghiệp vụ sang PostgreSQL** | **D-8 / chỉ thị G12 mục 8** | **KHÔNG PHẢI VIỆC CÒN THIẾU — ĐÂY LÀ ĐIỀU CẤM.** Kho nghiệp vụ **vẫn là SQLite** |
| 7 | Đo máy chủ HTTP thật **dưới tải** | `V-13914(b)` | Chưa đo. Bàn đo đồng thời gọi thẳng hàm, và `kiem_ha_tang.py` chỉ đo **số lượt được cho qua**, không đo **tải** |
| 8 | Tiến trình bị **tắt giữa giao dịch** | `V-13914(a)` | Chưa dựng ca đo trên schema này |
| 9 | Ghi thật ra **VIP Vault** | `V-13906-03` | Chưa cấp. Lượt ghi thật đầu tiên phải hỏi anh Thành |

---

## 7. PHẠM VI — VÀ CÁI GÌ **NẰM NGOÀI**

**Đã đo:** macOS arm64 (MacBook) · python 3.9.6 · SQLite 3.51.0 (module 2.6.0) · PostgreSQL
**16.15** Homebrew trên **cụm riêng** · ổ nội bộ · máy chủ bind `127.0.0.1` · adapter MOCK
(`CHO_PHEP_LIVE=False` cả hai hãng đã đăng ký: `jt`, `vtp`) · tối đa **2–8 tiến trình** thật.

**NẰM NGOÀI, chưa đo, đừng suy ra:**
- **Chuyển dữ liệu thật** (chặng 4) — chưa làm, và **không được làm** ở lượt này.
- **Lớp phương ngữ `csdl.py`** (chặng 1) — **chưa có**, nên **MÃ NGHIỆP VỤ CHƯA CHẠY ĐƯỢC**
  trên PostgreSQL. Mọi số PostgreSQL ở đây là của **schema + SQL thô**, không phải của mã app.
- **Docker** — không có. **VPS / staging / TLS thật / tên miền** — không có.
- **Nhiều MÁY**, mạng thật, ổ mạng/NFS (khoá SQLite **không đáng tin** ở đó), replica đọc.
- **Dữ liệu lớn** (CSDL đo dưới 3.200 bút toán), **tải đọc**, **hãng thật**, **AI thật**.
- **Safari / Firefox** (tầng 3 chỉ Chromium).

**Hệ này CHƯA production-ready** (chỉ thị mục 20). Lượt này **không** tuyên bố điều ngược lại.
