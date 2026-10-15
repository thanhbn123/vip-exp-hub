# G12 — ĐỒNG THỜI Ở TẦNG CSDL: đo được gì, và cái gì NẰM NGOÀI

Ngày đo: **15/10/2026**. Người đo: AG-00. Chỉ thị G12 mục 5, 11, 12, 13.

## 0. Trả lời ngắn

Đo **8 tiến trình hệ điều hành thật × 400 phép ghi × 3 ca = 9.600 lượt**:
**0 khoá hết giờ · 0 giao dịch hỏng · 0 mất cập nhật**, ba phép đối chiếu sổ sách đều khớp.

Nhưng con số 0 đó **không có sẵn**. Phải vá bốn lỗi mới có, trong đó **ba lỗi làm lệch tiền
hoặc mất tiền ngay hôm nay trên SQLite một máy** — không phải nợ dành cho PostgreSQL.

## 1. Bốn lỗi đã vá, kèm phép đo phơi ra chúng

### L1 — Bút toán mồ côi: sổ cái lệch công nợ 777.000đ

`tai_chinh.ghi_but_toan` có docstring ghi *"ghi bút toán + cập nhật công nợ trong **CÙNG một
transaction**"*. Mã thì không: cả hai bước gọi `csdl.ghi()`, mà hàm đó **commit sau mỗi câu**.
`with csdl.khoa_ghi:` chỉ chặn hai thread giẫm nhau — nó **không** gộp hai câu thành một đơn vị.

| Phép đo | Trước vá | Sau vá |
|---|---|---|
| ép bước cập nhật công nợ hỏng | bút toán 777.000đ **vào sổ**, công nợ đứng yên, lệch 777.000đ | 0 bút toán mồ côi, sổ khớp công nợ |

Nặng hơn một lỗi thường: bút toán **không xoá được** (trigger `BEFORE UPDATE/DELETE →
RAISE(ABORT)`), nên sai nằm lại vĩnh viễn, chỉ chữa được bằng bút toán đảo.

### L2 — Dòng thanh toán mồ côi, KẸT VĨNH VIỄN

`tai_chinh.ghi_nhan_thanh_toan` ghi 4 câu, mỗi câu tự chốt.

| Phép đo | Trước vá | Sau vá |
|---|---|---|
| đơn COD 100.000 đã trả 50.000, đợt mới trả 90.000 | câu 2 **từ chối đúng** (50+90 > 100) nhưng câu 1 đã commit → `tc_dot_tt_dong` có dòng 90.000 mồ côi, tổng đợt 140.000 trong khi `tc_cod` ghi đã trả 50.000 | 1 dòng, tổng khớp |

Và `UNIQUE(dot_id, don_id)` **chặn làm lại**, nên đợt đó kẹt vĩnh viễn, phải sửa tay dưới CSDL.

### L3 — Sự kiện hạn mức mồ côi: mất tiền một chiều

Lộ ra **sau khi** đổi kết nối sang chế độ tường minh. `usage.ghi_su_kien` gọi `kn.rollback()`
để bỏ sự kiện vừa ghi khi vượt trần — lệnh đó thành **rỗng**, rỗng mà không báo lỗi.

Sự kiện mồ côi ở đây không vô hại: lần thử lại cùng `idem_key` bị coi là **TRÙNG** rồi lặng
lẽ không thu gì. `thu_usage.test_d2` bắt được ngay (`1 != 0 : còn sự kiện mồ côi`).
Vá: **xoá thẳng theo id**, không dựa vào giao dịch ngầm nào.

### L4 — Migration CHƯA BAO GIỜ nguyên tử

`kn.executescript()` **tự COMMIT** giao dịch đang mở, lặng lẽ. Lượt nâng cấp nạp 5 khối DDL
G07–G11 qua `executescript`, nên hỏng sau khối đầu là để lại CSDL nâng cấp nửa vời — trong
khi thông báo lỗi vẫn ghi *"CSDL giữ nguyên trạng thái trước (transaction rollback)"*.
Hệ thống nói sai về chính nó (§12.2).

Thêm một nửa: `with kn:` của python **không** mở giao dịch cho `CREATE`/`ALTER`, chỉ cho DML.
Nên câu rollback kia đúng với DML và sai với DDL.

## 2. Lỗi khoá: một thread tự khoá chính mình qua HAI kết nối

Nặng nhất về mức độ khó thấy.

Ba thứ cộng lại: `dong()` xoá cờ `_da_khoi_tao` (biến **toàn cục**, không theo thread) ·
`mo()` xét cờ **trước** khi xét kết nối của thread · `_khoi_tao_schema` tự mở kết nối riêng.

Thread B đang mở giao dịch trên kết nối B1 → thread A gọi `dong()` xoá cờ → lượt ghi tiếp
của B vào `mo()` → thấy cờ trống → `_khoi_tao_schema` → mở kết nối **B2** → B2 ghi và chờ
khoá mà **chính B1** đang giữ. Một thread, hai kết nối, khoá nhau. `khoa_ghi` là RLock nên
B đi xuyên qua nó — B đã giữ nó rồi.

**Phép đo chỉ đúng chỗ khi đo THỜI GIAN TỪNG PHA**, không phải tổng:

| Thread | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| giây | 0,005 | 30,35 | 30,35 | 60,70 | 60,70 | 91,04 | 91,05 | 121,42 | 121,43 | 121,43 |

Lượng tử hoá theo đúng `busy_timeout`. Không phải "chậm" — là **chờ hết giờ theo từng đợt**.
4/10 thread nhận `database is locked`.

Sau vá (`_khoi_tao_schema(kn)` dùng chính kết nối của thread; `mo()` trả kết nối ngay khi
có): **tổng 0,01 giây**, 0 lỗi khoá, đúng 3/10 lượt đi qua — đúng số nghiệp vụ.

**Cách tìm ra, ghi lại vì đó là bài học:** vá mò **ba lần** trước khi đo đúng — tưởng
`journal_mode=WAL` là thủ phạm (sai) · tưởng `_khoi_tao_schema` thiếu `khoa_ghi` (đúng một
phần, 91s còn 61s) · nâng `busy_timeout` từ 5 lên 30 giây (**làm tệ hơn** — biến một lỗi
NHANH thành một lượt NGỒI CHỜ). `giao_dich()` không gây ra lỗi nào trong số đó; nó chỉ **làm
lộ ra** những thứ vốn đã sai.

## 3. Lỗi `SQLITE_BUSY_SNAPSHOT`: 14/30 lượt bị từ chối TỨC THÌ

Lượt đo thử đầu (2 tiến trình × 15 lượt đọc–sửa–ghi): **14/30 nhận `database is locked` ở
0,0 giây** — không phải chờ lâu rồi hết giờ.

`SAVEPOINT` trần mở giao dịch **HOÃN**: khoá đọc trước, tới câu ghi mới xin nâng lên khoá
ghi. Tiến trình khác đã commit kể từ ảnh đọc của mình thì SQLite trả `SQLITE_BUSY_SNAPSHOT`,
và **`busy_timeout` không chờ ca này** — nó trả ngay.

Vá: tầng **ngoài** của `csdl.giao_dich()` dùng `BEGIN IMMEDIATE` (xin khoá ghi từ đầu, không
còn lượt nâng nào để thất bại); tầng **lồng** vẫn `SAVEPOINT`. Kèm theo: kết nối của `mo()`
chuyển sang `isolation_level=None` để `BEGIN` tường minh có hiệu lực.

## 4. Phép đo chính — 8 tiến trình × 400 phép

Bàn đo: `app/thu/dong_thoi/chay.py`. Mỗi phép ghi xếp vào **đúng một** kết cục.

| Ca | CHỐT THÀNH CÔNG | TỪ CHỐI NGHIỆP VỤ | KHOÁ HẾT GIỜ | GIAO DỊCH HỎNG | Đối chiếu |
|---|---|---|---|---|---|
| 1. Sổ cái tài chính | 3200 | 0 | **0** | **0** | sổ 3.200.000đ = tiến trình tin đã ghi = công nợ |
| 2. Đọc–sửa–ghi | 3200 | 0 | **0** | **0** | **mất cập nhật = 0** |
| 3. Trần hạn mức (trần 400, nhu cầu 3200) | 400 | 2800 | **0** | **0** | bộ đếm CSDL = 400, không vượt |

Thời gian: ca 1 là 0,7s · ca 2 là 0,5s · ca 3 là 0,1s mỗi tiến trình.

**Mất cập nhật là kết cục thứ năm, và nó KHÔNG tự báo** — chỉ phát hiện được bằng đối chiếu
cuối lượt (tổng tiến trình *tin* đã ghi so với tổng *thật* trong CSDL). Nên bàn đo luôn làm
phép đối chiếu đó, không chỉ đếm bốn kết cục kia.

**Đo bằng TIẾN TRÌNH, không bằng THREAD.** `csdl.khoa_ghi` là `threading.RLock` — nó chỉ phủ
**một** tiến trình. Đo bằng thread là đo chính cái khoá đó, rồi kết luận "an toàn" cho một ca
mà nó không hề phủ (§12.1 luật 3).

## 5. Không thử lại vô hạn (chỉ thị mục 13)

- `giao_dich()` **không** thử lại. Hết `busy_timeout` thì ném, người gọi quyết.
- Khoá migration chờ tối đa `migrate.KHOA_CHO_GIAY = 60` giây rồi **ném**, không chạy chồng.
- `csdl._dat_wal` thử lại có hạn: `HAN_DOI_WAL = 40` lượt giãn dần (~41 giây) rồi **ném**
  `LoiVanHanh` với thông điệp nói rõ phải xử gì. Lý do thử lại ở đây: `busy_timeout` không
  phủ lệnh đổi chế độ sổ ghi, và chỉ cần **một** tiến trình đặt được WAL là cả CSDL thành WAL.

## 6. PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI

**Đã đo:** 8 tiến trình hệ điều hành thật · 400 phép mỗi tiến trình · macOS arm64 ·
python 3.9.6 · SQLite 3.51.0 (module 2.6.0) · chế độ WAL · CSDL trên **ổ nội bộ** ·
3 ca ghi (sổ cái bất biến · đọc–sửa–ghi cùng hàng · trần hạn mức) · migration đồng thời
8 tiến trình (bộ `thu_migrate_dong_thoi.py`).

**NẰM NGOÀI, chưa đo, đừng suy ra:**

- **PostgreSQL.** Mọi số ở đây là của SQLite. Xem `POSTGRESQL_MIGRATION_PLAN.md`.
- **Ổ mạng / NFS / Synology Drive.** Khoá tệp của SQLite **không đáng tin** ở đó. CSDL của
  dự án này nằm ở `app/du-lieu/` trên ổ nội bộ; đặt nó lên ổ mạng là bỏ mọi kết luận ở trên.
- **Nhiều MÁY.** `BEGIN IMMEDIATE` khoá ở tầng tệp, trong một hệ tệp.
- **Tiến trình bị tắt GIỮA giao dịch.** Chưa dựng ca đo. SQLite tự lùi khi mở lại, nhưng
  chưa đo lượt lùi đó trên schema này.
- **Máy chủ HTTP thật dưới tải.** Bàn đo gọi thẳng hàm, không qua `ThreadingHTTPServer`.
- **Trần chống lạm dụng (rate limit)** — sống trong bộ nhớ MỘT tiến trình, nên nhiều tiến
  trình đi xuyên qua. Đã biết, chưa vá.
- **Dữ liệu lớn.** CSDL đo là CSDL mới, dưới 3.200 bút toán.
- **Hãng thật, AI thật, VPS.**

## 7. Chốt chặn để ba lỗi trên không mọc lại

| Luật | Chốt chặn |
|---|---|
| chỉ `csdl.py` được `import sqlite3` | `thu_bien_driver.py` a1 (AST, không grep) |
| nhiều câu ghi phải bọc `giao_dich()` | `thu_giao_dich.py` c1, c2 |
| cấm `kn.commit()`/`kn.rollback()` trên kết nối thread | `thu_bien_driver.py` a5 |
| migration đồng thời đúng 1 tiến trình nâng cấp | `thu_migrate_dong_thoi.py` a1, a2 |
| DDL lùi được, không cắt trigger theo `;` | `thu_migrate_dong_thoi.py` b2, b3 |
| không tự khoá chính mình | `thu_migrate_dong_thoi.py` c1, c2 (có hạn giờ, treo là HỎNG) |

Mỗi chốt đã chứng minh **có tải**: gỡ bản vá ra thì ca tương ứng hỏng; phục hồi thì đạt.

Bảy điều về SQLite đã đo, đừng suy lại: `SHARED_CONTRACTS.md` §30.4.
