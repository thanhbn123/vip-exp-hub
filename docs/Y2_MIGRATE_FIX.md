# Y2 — SỬA HAI LỖI THẬT TRONG `app/migrate.py`

**Trạng thái:** đã sửa · đã đo lại · đối chứng âm cho CẢ HAI lỗi
**Phạm vi ghi:** `app/migrate.py` · `app/thu/thu_migrate_dong_thoi.py` · `docs/Y2_MIGRATE_FIX.md` (mới)
**Không sửa:** `app/cau_hinh.py` (Agent 01 đã có `khai_kho_kiem_thu`) · `app/csdl.py` · `trien_khai/g20-saoluu/ban_va.py`

---

## 0. TÓM TẮT

Hai lỗi X2 đo được trên cây này (xem `docs/G22_PHAN_LOAI_DO.md` §3-F):

| Mã | Lỗi | Trước khi sửa | Sau khi sửa |
|---|---|---|---|
| **L1** | race trong `migrate.sao_luu()` | 8 tiến trình migrate đồng thời ⇒ **7/8 chết** với `disk I/O error` / `FileNotFoundError … .dang-ghi` | **18/18 lượt xanh** · 8 tiến trình ⇒ 1 nâng cấp, 0 lỗi |
| **L2** | `app/migrate.py` nạp thẳng `sqlite3` | `thu_bien_driver.py` exit **1**, `migrate.py dòng [26]` | exit **0**, **5 ca — ĐẠT**, `migrate.py` không còn `import sqlite3` |

Không hạ ngưỡng, không xoá ca, không nới điều kiện. Ca `a1`/`a2` của
`thu_migrate_dong_thoi.py` giữ nguyên mọi khẳng định; chỉ thêm dòng khai kho (bắt buộc từ G22)
và **thêm ca `a3`** đo trực tiếp tên bản sao.

---

## 1. LỖI L1 — RACE TRONG `sao_luu()`

### 1.1 Tái hiện TRƯỚC khi sửa (số đo thật)

```sh
VIP_KHO_DANG_CHAY=sqlite python3 app/thu/thu_migrate_dong_thoi.py
# exit=1 · Ran 8 tests · FAILED (failures=1)
```

```
FAIL: test_a1_dung_mot_tien_trinh_nang_cap
AssertionError: 7 != 0 : tiến trình hỏng: [
  ('tt0|LOI|disk I/O error|…'),
  ("tt1|LOI|[Errno 2] No such file or directory:
    '/…/vh-migdt-…/sao-luu/hub-truoc-migrate-…db.dang-ghi'"),
  …
]
```

Đúng 1 tiến trình sống, **7 tiến trình chết**. Hai kiểu lỗi đúng như X2 ghi:
`disk I/O error` và `FileNotFoundError … .dang-ghi`. Race không tất định — X2 đo 14/18 lượt
chạy lại vẫn đỏ.

### 1.2 Nguyên nhân (hai vế, phải sửa CẢ HAI)

1. **Cả 8 tiến trình gọi `sao_luu()` TRƯỚC khoá `BEGIN IMMEDIATE`.** Khoá chỉ bảo vệ phần
   nâng cấp, không bảo vệ bước sao lưu.
2. **Tên bản sao chỉ có độ phân giải GIÂY và tệp tạm dùng chung `".dang-ghi"`.** Hai tiến
   trình trong cùng một giây tính ra cùng `dich`, cùng `tam`; một tiến trình `os.replace`
   xong thì tiến trình khác còn đang mở/ghi đúng tệp đó ⇒ `FileNotFoundError` / `disk I/O error`.
   Ngay cả khi tên cuối khác nhau, bước `_duong_chua_dung` cũng có khe TOCTOU giữa
   `os.path.exists()` và lúc tạo tệp.

### 1.3 Bản vá (trong `app/migrate.py`)

**(a) Sao lưu nằm TRONG khoá.** `chay()` gọi `sao_luu()` **sau** `BEGIN IMMEDIATE` và **sau**
lượt đọc lại `schema_version`. Tiến trình thắng khoá mới sao lưu; 7 tiến trình còn lại đã về
ở nhánh `nhuong` (hoặc về sớm vì đọc ngoài khoá thấy việc đã xong). Hỏng ở bước sao lưu thì
`ROLLBACK` + `close()` trước khi ném — không giữ khoá tới lúc tiến trình chết.

**(b) Tên duy nhất, không tạo tệp giữ chỗ.**

- Tên đích tạm `.dang-dat-<PID>-<bộ-đếm>.db` — **không phải** tên bản sao lưu, nên trong lúc
  ghi không ai thấy một `hub-truoc-migrate-*.db` rỗng/nửa vời.
- Tệp tạm `.dang-ghi-<PID>-<bộ-đếm>` — PID tách tiến trình, `itertools.count()` nguyên tử
  tách thread trong cùng tiến trình.
- Sau khi bản sao đã trọn + đã kiểm, `_dat_ten_ban_sao()` đặt tên thật bằng **`os.link()`**:
  tạo tên NGUYÊN TỬ, tên đã có ⇒ `FileExistsError` ⇒ thử `-1`, `-2`, … **Không đè**, và
  **không cần tệp rỗng giữ tên** (một tệp như thế là "đường lùi giả" nếu tiến trình bị kill).
- `_duong_chua_dung()` giữ nguyên chữ ký và hành vi cũ cho `khoi_phuc()` — mảnh
  `ban_va.MANH_VA` (chốt 0b, 5, 6) vẫn khớp **đúng một lần**; đã tự kiểm bằng
  `ban_va.xac_nhan()`.

### 1.4 Đối chứng âm (race PHAI tái hiện)

Ba bản sao tạm, cùng bộ thử **mới** (9 ca), cùng máy:

| Biến thể | Lệnh | Kết quả |
|---|---|---|
| **Sản phẩm CŨ** (`git show HEAD:app/migrate.py`) | `python3 thu/thu_migrate_dong_thoi.py` | **exit 1** · `FAILED (failures=2)` · a1 `7 != 0`; a3 `7/8` tiến trình chết |
| **Chỉ trả TÊN về kiểu cũ**, vẫn giữ sao lưu trong khoá | như trên | **exit 1** · a3 ĐỎ (`7/8` chết: `[Errno 2] … hub-truoc…dang-ghi`); a1 XANH |
| **Sản phẩm đã sửa** | như trên | **exit 0** · `Ran 9` · `OK` |

Dòng thứ hai là vế quan trọng: nó chứng minh **tên duy nhất** là mảnh chịu lực riêng, không
phải chỉ nhờ khoá mà xanh. Dòng thứ nhất chứng minh bộ thử mới bắt được đúng lỗi cũ.

### 1.5 Đo lại: 18/18 lượt

```sh
for i in $(seq 1 18); do python3 app/thu/thu_migrate_dong_thoi.py; done
```

```
luot 01: exit=0 · Ran=9 · OK
…
luot 18: exit=0 · Ran=9 · OK
XANH=18/18
```

Mỗi lượt gồm: 8 tiến trình migrate thật (a1), 8 tiến trình migrate trên CSDL thật (a2), **8
tiến trình gọi THẲNG `sao_luu()` cùng lúc (a3)**, 4 ca DDL, 2 ca thread. a3 đòi:
8 đường dẫn khác nhau · 8 tệp `.db` · mỗi tệp có `.sha256` khớp nội dung · 0 tệp `-wal`/`-shm`
lạc trong `sao-luu/`.

---

## 2. LỖI L2 — VI PHẠM BIÊN DRIVER

### 2.1 Tái hiện TRƯỚC khi sửa

```sh
python3 app/thu/thu_bien_driver.py
# exit=1 · 0 ca (dừng ở a1)
```

```
AssertionError: tệp nạp trực tiếp sqlite3
(phải dùng csdl.Row/LoiToanVen/ket_noi): migrate.py dòng [26]
```

`git blame` chỉ đúng dòng 26 được thêm bởi commit `bf8696d` (bản vá G22/S8). Bốn chỗ dùng
driver trong `migrate.py`: `connect` chỉ-đọc, `OperationalError`, `DatabaseError`,
`complete_statement`. (Trong mã hiện tại `complete_statement` đã đi qua `csdl.cau_sql_du`.)

### 2.2 Bản vá — không nới biên, không mở ngoại lệ

`app/migrate.py` **bỏ hẳn `import sqlite3`**. Ba chỗ còn lại đi qua API đã bọc của `csdl`:

| Chỗ dùng cũ | Thay bằng |
|---|---|
| `sqlite3.OperationalError` | `csdl.LoiVanHanh` |
| `sqlite3.DatabaseError` | `csdl.LoiCSDL` |
| `sqlite3.connect("file:…?mode=ro&immutable=1", uri=True)` | `csdl.ket_noi(":memory:")` + `ATTACH DATABASE ? AS kiem` với URI `mode=ro&immutable=1` |

Vì sao **không** mở thẳng `csdl.ket_noi(duong)`: mở đọc-ghi một CSDL WAL sẽ tạo `-wal`/`-shm`
cạnh tệp — với bản sao lưu đó là **sửa thứ đang được kiểm**, và với `sao_luu()` là tệp giả
trong `sao-luu/` (đúng cái `thu_g20_saoluu` ca i7 đã bắt được). URI `immutable=1` giữ đúng
ngữ nghĩa của bản vá G21, nhưng không cần driver ở tệp này.

Hai chốt an toàn của đường mở mới:

1. **Kiểm `PRAGMA database_list`**: chỉ tin URI khi đường mở trỏ ĐÚNG tệp đang kiểm. Nếu bản
   SQLite không hiểu URI ở `ATTACH` (compile-time `USE_URI` tắt), nó có thể mở/tạo một CSDL
   rỗng khác; lệch đường ⇒ rơi xuống đường chép-ra-tạm, **không đo trên tệp khác**.
2. **Đường lùi chép-ra-tạm** khi không hiểu URI: `shutil.copyfile` (KHÔNG `copy2`, để không bê
   quyền 0444 làm bản chép không mở đọc-ghi được), `chmod 0600`, kiểm trên bản chép, xoá thư
   mục tạm sau khi xong.

`_kiem_cau_truc()` vẫn giữ đủ các chốt cũ: 16 byte đầu phải là `SQLite format 3\0`, tệp > 0
byte, `integrity_check`, số bảng tối thiểu; `_kiem_ban_sao_luu()` vẫn **bắt buộc** `.sha256`.

### 2.3 Đối chứng âm (thêm lại driver ⇒ PHẢI đỏ)

Trên bản sao sạch của `app/`, thêm đúng một dòng `import sqlite3` vào `migrate.py`:

```sh
python3 thu/thu_bien_driver.py
# exit=1
# AssertionError: tệp nạp trực tiếp sqlite3 (…): migrate.py dòng [23]
```

Bản không thêm: **exit 0 · 5 ca — ĐẠT** (`a1` 33 tệp `app/*.py`, chỉ `csdl.py` nạp driver).

---

## 3. BẰNG CHỨNG TỔNG HỢP

| Lượt đo | Lệnh | Exit | Ca | Kết quả |
|---|---|---:|---:|---|
| Race TRƯỚC | `VIP_KHO_DANG_CHAY=sqlite python3 app/thu/thu_migrate_dong_thoi.py` | **1** | 8 | `7 != 0` tiến trình chết (`disk I/O error` / `FileNotFoundError … .dang-ghi`) |
| Race SAU × 18 | cùng lệnh, 18 lượt | **0** ×18 | 9/lượt | **18/18 OK** |
| Driver TRƯỚC | `python3 app/thu/thu_bien_driver.py` | **1** | 0 | `migrate.py dòng [26]` |
| Driver SAU | cùng lệnh | **0** | 5 | `5 ca — ĐẠT` |
| ĐCÂ L1 (sản phẩm cũ) | bộ mới trên bản `HEAD` | **1** | 9 | a1 + a3 đỏ, 7/8 chết |
| ĐCÂ L1 (chỉ tên cũ) | bộ mới, sao lưu vẫn trong khoá | **1** | 9 | a3 đỏ, a1 xanh |
| ĐCÂ L2 | thêm `import sqlite3` vào bản sao | **1** | 0 | `migrate.py dòng [23]` |
| G22 sao lưu | `python3 app/thu/thu_g22_saoluu.py` | **0** | 14 | `OK` |
| G21 sao lưu | `python3 app/thu/thu_g21_saoluu.py` | **1** | 23 | **2 FAIL đã biết trước, ngoài phạm vi**: `S5` + `C4` ghim schema 9 trong khi `PHIEN_BAN_SCHEMA = 10` (X2 #9; sửa ở `trien_khai/g20-saoluu/fail_closed.py:329`, không thuộc Y2) |
| `ban_va.xac_nhan()` | tự kiểm mảnh bản vá | **0** | — | `MANH_VA OK` (chốt 0b/5/6 vẫn khớp đúng một lần) |
| Hồi quy đầy đủ | `VIP_KHO_DANG_CHAY=sqlite sh app/thu/chay_tat_ca.sh` | **1** | **2236 ca · 71 bộ** | **18 bộ thử đỏ + `van-tay-cay`** — tất cả là ghim cũ / điều kiện cây sạch / E2E, không có bộ nào đỏ vì `migrate`; xem §4 |

---

## 4. HỒI QUY ĐẦY ĐỦ — `sh app/thu/chay_tat_ca.sh`

Chạy với `VIP_KHO_DANG_CHAY=sqlite` (một dòng khai cho nền kiểm thử, đúng đường
`cau_hinh.khai_kho_kiem_thu()`; **không** dùng cho production):

```
python:   2236 ca · 71 bộ chạy thật
frontend: 56 + 40 ca (hai tầng tự động)
E2E:      KẾT QUẢ: 41/41 phép đo đạt
exit=1
```

**Hai bộ mục tiêu của Y2, trong CHÍNH lượt chạy này:**

| Bộ | Kết quả |
|---|---|
| `thu_bien_driver.py` | **✓ exit 0 · 5 ca** |
| `thu_migrate_dong_thoi.py` | **✓ exit 0 · 9 ca** |

**Các bộ sao lưu/khôi phục liên quan, cũng trong lượt này:**

| Bộ | Kết quả |
|---|---|
| `thu_g22_saoluu.py` | ✓ 14 ca |
| `thu_g22_cauhinh.py` | ✓ 17 ca |
| `thu_g22_regression.py` | ✓ 35 ca |
| `thu_g22_gioihan.py` | ✓ 32 ca |
| `thu_g20_saoluu.py` | ✗ 41 ca — **1 FAIL đã biết**: `10 != 9` (ghim schema 9, X2 #7) |
| `thu_g21_saoluu.py` | ✗ 23 ca — **2 FAIL đã biết**: `S5` + `C4` (cùng gốc ghim schema 9, X2 #9) |

**18 bộ thử đỏ + `van-tay-cay`, phân nhóm — KHÔNG bộ nào là lỗi `migrate`/sao lưu mới:**

1. **Ghim số/route/schema cũ (đã có trước Y2):** `thu_g01_g02.py` (21 ca),
   `thu_g17_baomat.py` (31), `thu_g19_route.py` (49), `thu_g20_dahang.py` (27),
   `thu_g20_saoluu.py` (41), `thu_g21_saoluu.py` (23), `thu_qa_g19.py` (29),
   `thu_qa_g19_tich_hop.py` (8), `thu_qa_soat.py` (30).
2. **Điều kiện "cây SẠCH so với HEAD" / "cây KHÔNG ĐỔI trong lượt đo":** `thu_g20_baomat.py`
   (28), `thu_g21_chotcay.py` (13), `thu_g22_chotcay.py` (11), `thu_qa_g17.py` (56),
   `thu_qa_g18.py` (47), `thu_qa_g20.py` (21), `thu_qa_g21.py` (24).
   Y2 sửa `app/migrate.py` + `app/thu/thu_migrate_dong_thoi.py`, thêm `docs/Y2_MIGRATE_FIX.md`,
   nên cây làm việc **bẩn có chủ đích**; các ca đó đo "HEAD sạch" hoặc "chỉ tệp trong danh sách
   cho phép được đổi", không đo sản phẩm. Đã chạy lại **riêng** `thu_qa_g21` trên cây ĐỨNG YÊN:
   `Ran 24 · FAILED (failures=1, skipped=3)` — đúng một FAIL `test_z2_cay_khong_doi_trong_luot_do`
   với lý do `[' M app/migrate.py', ' M app/thu/thu_migrate_dong_thoi.py', '?? docs/Y2_MIGRATE_FIX.md']`
   NGOÀI danh sách được phép của nó. Tức đây là **tiền đề "cây sạch"**, không phải hồi quy
   sản phẩm.
3. **Cần máy chủ/Chromium (E2E):** `thu_g22_e2e.py` (0 ca, exit 2 — cần máy chủ sống),
   `thu_qa_g22.py` (29 ca — 2 FAIL E2E/Chromium, X2 #18; bộ này cũng đòi cây sạch).
4. **`van-tay-cay`:** lượt chạy ghi vân tay TRƯỚC, rồi Y2 tạo/sửa `docs/Y2_MIGRATE_FIX.md` và
   phần đầu `thu_migrate_dong_thoi.py` **trong lúc bộ chạy đang chạy** ⇒ vân tay SAU khác
   TRƯỚC. Đây là **hạn chế của lượt đo**, đã nói ra: các con số ca vẫn là số đo thật của từng
   bộ, nhưng chúng không ghim được vào một mốc cây duy nhất. Lượt chạy lại trên cây ĐỨNG YÊN
   chỉ có thể làm mất mục 4; nhóm 1/2/3 vẫn đỏ vì ghim cũ, vì cây Y2 bẩn có chủ đích, và vì
   thiếu máy chủ/Chromium — những thứ nằm ngoài phạm vi Y2.

E2E qua HTTP thật trong cùng lượt: **41/41 phép đo đạt**; frontend tầng 1 **56 ca**, tầng 2
**40 ca**.

---

## 5. NHỮNG GÌ KHÔNG LÀM

- **Không** sửa `app/cau_hinh.py` (đã có `khai_kho_kiem_thu` từ Agent 01) hay `app/csdl.py`.
- **Không** thêm ngoại lệ cho `migrate.py` trong `thu_bien_driver.DUOC_NAP` — biên driver
  "chỉ `csdl.py` được nạp driver" giữ nguyên.
- **Không** sửa `trien_khai/g20-saoluu/*` để làm xanh `S5`/`C4`; đó là ghim schema 9 → 10,
  việc của làn sửa ghim (X2 #7/#9), không phải Y2.
- **Không** đụng `hub.db` thật, không chạy production, không push/deploy.

---

## 6. RỦI RO CÒN LẠI (nói ra, không giấu)

1. **`khoi_phuc()` vẫn dùng `_duong_chua_dung()` kiểu cũ** — khe TOCTOU tên bản cất còn đó
   (hai lượt `khoi_phuc()` cùng giây có thể chọn cùng tên). Đây là hành vi **có trước** Y2,
   không phải hồi quy; `khoi_phuc()` không nằm trong lỗi L1. Muốn đóng thì chuyển nó sang
   `_dat_ten_ban_sao()` ở một lượt riêng, kèm đo lại G21/G22.
2. **SIGKILL giữa lúc ghi** để lại tệp `.dang-ghi-<PID>-<n>` (không mang tên bản sao lưu).
   Đây là hành vi cũ; tệp đó không được `khoi_phuc()` nhận (không có `.sha256`, **không** phải
   `hub-truoc-migrate-*.db`). `sao_luu()` dọn nó ở mọi đường lỗi Python.
3. **Ổ mạng/NFS**: `os.link()` có thể không hỗ trợ; khi đó mã rơi về `_duong_chua_dung()` +
   `os.replace()` (đường cũ). SQLite cũng đã bị khai là **không đáng tin trên ổ mạng**
   (`csdl._dat_wal`), nên đây là giới hạn đã biết, không phải đường chạy được khuyến nghị.
4. **SQLite không có `USE_URI`**: `_mo_chi_doc()` kiểm `database_list` rồi chép ra tệp tạm —
   chậm hơn nhưng vẫn đúng; không đo trên tệp khác.
5. **Sao lưu nằm TRONG khoá nên thời gian giữ khoá = thời gian sao lưu.** Trên CSDL lớn, bảy
   tiến trình đang chờ có thể vượt `KHOA_CHO_GIAY = 60` và nhận "không lấy được khoá" thay vì
   nhường. Đây là **đánh đổi có chủ đích** để loại tám bản sao đồng thời; đo trên nền kiểm thử
   (CSDL vài trăm KB) mỗi lượt migration dưới 1 giây. Nếu sau này có CSDL rất lớn, cách đúng là
   một khoá riêng cho bước sao lưu (không giữ khoá ghi của schema), kèm đo lại — **chưa làm**
   ở lượt này vì chưa có số đo CSDL lớn.

---

## 7. LỆNH TÁI LẬP

```sh
# 1) Bộ thử L1 (18 lượt)
for i in $(seq 1 18); do python3 app/thu/thu_migrate_dong_thoi.py || echo "LUOT $i HONG"; done

# 2) Bộ thử L2
python3 app/thu/thu_bien_driver.py

# 3) Hai bộ sao lưu liên quan
python3 app/thu/thu_g22_saoluu.py
python3 app/thu/thu_g21_saoluu.py   # 2 FAIL đã biết: S5/C4 (ghim schema 9), ngoài phạm vi

# 4) Hồi quy đầy đủ (khai kho cho nền kiểm thử)
VIP_KHO_DANG_CHAY=sqlite sh app/thu/chay_tat_ca.sh
```
