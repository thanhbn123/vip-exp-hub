# G20 / AG-04 — SAO LƯU VÀ KHÔI PHỤC: VÒNG TRÒN ĐÃ ĐƯỢC ĐO

**Nền:** `integration/g19` @ `148ecd3` · worktree `g20-ag04-backup` · schema `v9` (51 bảng)
**Người làm:** AG-04 (VẬN HÀNH) · **Ngày đo:** 16/10/2026
**Tệp của lượt này:** `trien_khai/g20-saoluu/` (mới) · `app/thu/thu_g20_saoluu.py` (mới) · tài liệu này (mới)
**KHÔNG sửa:** `app/csdl.py` · `app/migrate.py` (tệp của AG-00) · `app/cau_hinh.py`

---

## 0. KẾT LUẬN TRƯỚC, CHỨNG CỨ SAU

| # | Câu hỏi | Trả lời ĐO ĐƯỢC |
|---|---|---|
| 1 | Vòng tròn `sao_luu()` → `khoi_phuc()` vào CSDL MỚI có ra ĐÚNG dữ liệu không? | **CÓ.** 51/51 bảng khớp cả **số dòng** lẫn **tổng tiền**; 34.336.000 đồng khớp từng cột; băm toàn kho khớp; `integrity_check = ok`. |
| 2 | ĐỐI CHỨNG ĐƯỜNG: khôi phục ngược lại chính CSDL gốc? | **Y NGUYÊN.** 0 lệch. Và phép so ĐỎ được: ghi thêm dữ liệu → 8 lệch ngay. |
| 3 | `khoi_phuc()` có kiểm tệp trước khi đè lên CSDL đang chạy không? | **KHÔNG.** Nhận **5/5** tệp cắt giữa đường và **5/5** tệp bị sửa 1 byte, kể cả tệp **0 byte** và tệp `pg_dump`. |
| 4 | Bản cất `hub-truoc-rollback-*.db` có an toàn không? | **CÓ với 1 lượt, MẤT với ≥2 lượt trong cùng một giây.** Tên đặt theo GIÂY và **ghi đè im lặng**. |
| 5 | Khôi phục bản sao lưu schema THẤP hơn thì sao? | **TỤT IM LẶNG.** v6 đè lên v9: còn 20/51 bảng, mã thoát 0, không một lời cảnh báo. |
| 6 | `sao_luu()` làm gì khi kho là PostgreSQL (P-G15-02)? | **IM LẶNG BÁO THÀNH CÔNG với ĐƯỜNG LÙI GIẢ.** Mã thoát 0, tệp 4.096 byte, **0 bảng**, `integrity_check = "ok"`. |
| 7 | Bản sao lưu CSDL có TỰ ĐỦ không? | **KHÔNG.** Khóa mã hóa credentials không đi kèm. May là hệ **NÉM `LoiKhoa` ỒN ÀO** chứ không tự sinh khóa mới. |

**Phán tổng:** đường lành chạy **ĐÚNG**. Sáu khuyết điểm nằm cả ở **đường khôi phục**, không ở đường sao lưu — và cả sáu đều thuộc loại **im lặng**. Chúng không làm hỏng lượt khôi phục nào đã chạy đúng; chúng làm hỏng **lượt khôi phục trong sự cố**, đúng lúc không được phép hỏng.

---

## 1. CÁCH CHẠY LẠI — MỘT LỆNH, MÃ THOÁT THẬT

```sh
sh trien_khai/g20-saoluu/chay_do.sh              # 9 kịch bản, có PostgreSQL
sh trien_khai/g20-saoluu/chay_do.sh --nhanh      # 8 kịch bản, bỏ PostgreSQL
python3 app/thu/thu_g20_saoluu.py                # bộ thử tự động (vào lượt hồi quy chung)
```

**Mã thoát của lượt đo dùng cho tài liệu này:**

| Bước | Lệnh | Mã thoát | Số ca |
|---|---|---|---|
| B1 | `python3 -c "ast.parse(...)"` trên 6 tệp | **0** | — |
| B2 | `python3 trien_khai/g20-saoluu/do_vong_tron.py` | **0** | 8/8 kịch bản đo được |
| B3 | `python3 app/thu/thu_g20_saoluu.py` | **0** | **Ran 41 tests · OK · 0 skip** |
| B4 | `python3 trien_khai/g20-saoluu/do_postgres.py` | **0** | 1 cụm riêng, 3 phép đo |

`chay_do.sh` lấy mã thoát **TRƯỚC** mọi ống dẫn (`MA=$?` rồi mới in) — `lệnh | tee` trả mã thoát của `tee`, không phải của `lệnh` (`docs/QA_G18.md`, N-01).

### 1.1 Bối cảnh hồi quy — bốn bộ hỏng, cả bốn đều KHÔNG do AG-04

Chạy **đúng vòng lặp bộ thử Python** của `app/thu/chay_tat_ca.sh` (không chạy mục E2E/tầng 3 trong vòng lặp đó vì chúng ghi báo cáo ra `thu_giao_dien/_bao-cao/`, ngoài phạm vi ghi của AG-04):

```
TONG_CA=1774  SO_BO=49  SO_BO_QUA=1   (mã thoát vòng lặp: 1)
  ✓ thu_g20_saoluu.py              41 ca     ← bộ của lượt này
```

| Bộ hỏng | Nguyên nhân ĐO ĐƯỢC | Bằng chứng |
|---|---|---|
| `thu_bao_mat.py` (57 ca) | Môi trường `GIT_CONFIG_COUNT=2` **thiếu `GIT_CONFIG_KEY_*`** → mọi lệnh git thoát 128 (N-G18-00). **Không liên quan AG-04.** | Chạy lại sau `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1` → **exit 0 · Ran 57 · OK** |
| `thu_tich_hop.py` (12 ca) | Cùng nguyên nhân trên. | Chạy lại sau khi gỡ biến → **exit 0 · Ran 12 · OK** |
| `thu_qa_g17.py` (53 ca) | `test_a1_cay_sach_va_head` — cây **BẨN** vì 3 tệp MỚI của lượt này chưa được commit. Bộ đó khẳng định "cây sạch tại mốc đo". **Sẽ hết hỏng sau khi AG-00 commit.** AG-04 **KHÔNG** tự commit (`.git` do AG-00 giữ). | `AssertionError: Lists differ: ['?? app/thu/thu_g20_saoluu.py', '?? docs/…', '?? trien_khai/g20-saoluu/'] != []` |
| `thu_qa_g18.py` (43 ca) | Hai ca: `test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` (cùng nguyên nhân cây bẩn) và `test_b1_tang_3_chay_duoc_va_khong_co_ca_hong`. **KHÔNG phải EPERM do sandbox**: log ghi `1 failed · 47 passed`, ca hỏng là `thu_giao_dien/06_ban_phim.spec.js` — *"30 lượt Tab chỉ vào được 1 điều khiển trong màn"* (G19 bàn phím, **không thuộc AG-04**). | `tang3.log`: `✘ 42 [chromium] › 06_ban_phim.spec.js:153` · `1 failed · 47 passed (1.9m)` |

`thu_qa_g19.py` **BỎ QUA có lý do**, và lý do được in ra: *"HEAD 148ecd3 != nền đóng băng 6e61fc1 … Nghiệm thu cây ĐÃ GỘP thuộc bộ riêng `thu_qa_g19_tich_hop.py`"* — đúng thiết kế.

**Kiểm tra phạm vi ghi:** sau toàn bộ lượt đo, `git status --porcelain` chỉ có **đúng 3 đường được cấp** (`trien_khai/g20-saoluu/`, `app/thu/thu_g20_saoluu.py`, `docs/G20_BACKUP_RESTORE.md`), tất cả là tệp **MỚI**. `HEAD` vẫn là `148ecd380a9009c7b01dc0c268a3f1a97327a164` — **không commit, không push, không deploy**.

---

## 2. PHÉP ĐO — VÌ SAO PHẢI CÓ **TỔNG TIỀN**, KHÔNG CHỈ SỐ DÒNG

`trien_khai/do_csdl.py` (G11) đếm **số dòng** và tự khai giới hạn của nó:

> *"NGOÀI PHẠM VI: tính ĐÚNG của dữ liệu nghiệp vụ. `integrity_check` nói CSDL không hỏng về cấu trúc; nó KHÔNG nói dữ liệu đúng. Một bảng bị ghi trắng vẫn `integrity_check = ok`."*

Đúng — và còn một lớp hỏng mà phép đếm dòng **không bao giờ** thấy: **số dòng y nguyên, số tiền sai**. Trong hệ này tiền là số nguyên VND trong 18 cột thuộc 12 bảng. Khung đo mới đo thêm **TỔNG TIỀN từng cột tiền của từng bảng**, cộng **băm toàn kho** (SHA-256 trên nội dung logic mọi bảng) để bắt cả những thay đổi không đụng số dòng lẫn tiền (tên khách, payload webhook nhị phân).

### 2.1 Danh sách cột tiền là KHAI BÁO TƯỜNG MINH, có chốt chống MỤC

`khung_do.COT_TIEN` viết tay — không dò bằng regex (`gia` bắt luôn `trang_thai_giao`, `tt` bắt luôn `stt`). Đổi lại, danh sách viết tay **mục được**, nên `kiem_danh_sach()` **NÉM** nếu thấy một cột số tên-dạng-tiền chưa khai. Chốt này **đã nổ thật** trong lượt làm này: nó bắt được 3 cột tiền còn thiếu (`du_thao_hoa_don.tien_goi_dong`, `tien_vuot_dong`, `goi_phien_ban.gia_thang_dong`) và 2 báo động giả (`han_muc_rieng.gia_tri` là **hạn mức**; `quan_sat_su_kien.tien_trinh` là **tiến trình**).

### 2.2 Chốt chống phép đo RỖNG

`kiem_khong_rong()` **NÉM** nếu một cột tiền khai báo bằng 0 ở **bản gốc** — vì hai số 0 thì "khớp", và một bản khôi phục đánh rơi cả bảng vẫn cho ra "khớp" nếu bảng đó rỗng ở cả hai vế. Chốt này cũng đã nổ thật trong lượt làm này.

Một cột tiền **rỗng có chủ đích** được khai tường minh ở `khung_do.TIEN_RONG_CHAP_NHAN` kèm lý do đo được:

> `du_thao_hoa_don.tien_vuot_dong` — luôn 0: `usage.tinh_phi()` trả cứng 0 vì hệ **CHẶN** khi hết hạn mức chứ không cho dùng quá rồi thu thêm, và đơn giá phần vượt **chưa có ai chốt** (`app/usage.py`, khoá `ly_do_khong_thu_vuot`). Muốn cột này khác 0 thì phải có một quyết định về **GIÁ** — không phải việc của bộ đo.

### 2.3 Dữ liệu gieo — CỐ Ý TẤT ĐỊNH

3 tenant · 15 đơn COD · 57 bút toán · 15 dòng COD · 330.000 phí · 3 đợt thanh toán · 5 tài khoản hãng (credentials **mã hóa thật**) · 10 payload webhook **nhị phân** · 3 bảng kê đối soát. Tổng tiền toàn kho: **34.336.000 đồng**.

Gieo qua **hàm sản phẩm** (`tai_chinh.ghi_but_toan`, `ghi_phi`, `mo_so_cod`, `chuyen_cod`, `tao_dot_thanh_toan`, `ghi_nhan_thanh_toan`, `dieu_chinh`, `doi_soat.nap_bang_ke`, `usage.lap_du_thao`, `goi_dich_vu.phat_hanh_phien_ban`) chứ không `INSERT` thẳng — vì `tc_but_toan` có **hai trigger** chặn UPDATE/DELETE và ba `CHECK`; `INSERT` thẳng sẽ bỏ qua đúng những bất biến mà lượt khôi phục phải bảo toàn.

---

## 3. KỊCH BẢN 1 — VÒNG TRÒN ĐẦY ĐỦ (ĐẠT)

`sao_luu()` ở CSDL gốc → `khoi_phuc()` vào một thư mục dữ liệu **TRỐNG**.

```
rc_gieo 0 · rc_sao_luu 0 · rc_khoi_phuc 0
bản sao lưu : 561152 byte · 51 bảng
tổng tiền   : 34336000 → 34336000
băm toàn kho: d916343d4794e16b → d916343d4794e16b   (KHỚP)
lệch TỪNG BẢNG: 0
CSDL gốc bị đổi vì một lượt sao lưu: 0 lệch
integrity: ok → ok · phiên bản schema 9 → 9
```

Từng bảng, cả hai trục — trích 12 bảng có cột tiền (đủ 51 bảng ở `do_vong_tron.py`):

| BẢNG | DÒNG (gốc→kp) | TIỀN (gốc→kp) |
|---|---|---|
| `don_hang` | 15 → 15 | `cod` 3.180.000→3.180.000 · `gia_tri_khai` 6.360.000→6.360.000 · `phi_van_chuyen` 330.000→330.000 |
| `tc_but_toan` | 57 → 57 | `so_tien_dong` 8.177.000→8.177.000 |
| `tc_cod` | 15 → 15 | `so_tien_du_kien` 3.180.000 · `so_tien_hang_bao` 1.272.000 · `so_tien_doi_soat` 1.272.000 · `so_tien_da_tt` 212.000 — **tất cả khớp** |
| `tc_cong_no` | 10 → 10 | `so_du_dong` 4.567.000→4.567.000 |
| `tc_phi` | 15 → 15 | `so_tien_dong` 330.000→330.000 |
| `tc_dieu_chinh` | 3 → 3 | `so_tien_dong` −3.000→−3.000 |
| `tc_dot_tt` | 3 → 3 | `so_tien_hang_bao` 424.000→424.000 |
| `tc_dot_tt_dong` | 3 → 3 | `so_tien_dong` 212.000→212.000 |
| `ds_dong` | 15 → 15 | `phi_hang_bao` 330.000→330.000 |
| `goi_dich_vu` | 3 → 3 | `gia_thang` 1.298.000→1.298.000 |
| `goi_phien_ban` | 4 → 4 | `gia_thang_dong` 2.597.000→2.597.000 |
| `du_thao_hoa_don` | 2 → 2 | `tien_goi_dong` 598.000→598.000 · `tien_vuot_dong` 0→0 *(rỗng có chủ đích — §2.2)* |

**Phép đo phụ quan trọng:** một lượt `sao_luu()` **không** làm đổi CSDL nguồn (0 lệch). Một `sao_luu()` ghi vào chính CSDL nguồn thì "bản sao" đúng mà CSDL thì hỏng — phép đo rẻ nhất và hay bị bỏ nhất.

---

## 4. KỊCH BẢN 2 — ĐỐI CHỨNG ĐƯỜNG (ĐẠT)

Không có vế này thì **mọi** khẳng định "khôi phục khớp" ở trên đều vô nghĩa: một `so_sanh()` luôn trả `[]` cũng "đạt" hết.

| Vế | Số đo |
|---|---|
| (a) ghi thêm 1 tenant + 1 đơn 999.000đ → phép so **PHẢI ĐỎ** | **8 lệch** ngay (`tong_tien_toan_kho 34336000 → 37333000`; `DÒNG don_hang 15 → 16`; `TIỀN don_hang.cod 3180000 → 4179000`) |
| (b) `khoi_phuc()` ngược lại chính CSDL gốc → phải **Y NGUYÊN** | **0 lệch** |
| tenant tạo SAU mốc sao lưu còn lại | **0** (khôi phục thật sự lùi thời gian) |
| bản cất `hub-truoc-rollback-*.db` | **có**, và nội dung khớp dữ liệu lúc chụp |

---

## 5. SÁU KHUYẾT ĐIỂM ĐO ĐƯỢC

Mọi mục dưới đây đều có **ca thử đặc tả hành vi** trong `app/thu/thu_g20_saoluu.py` (nhãn `ĐỘC HẠI ĐÃ BIẾT`). Nếu ai vá `migrate.khoi_phuc()`, các ca đó **sẽ đỏ** và buộc cập nhật tài liệu này — một khuyết điểm không có ca thử thì lần sau không ai biết nó còn hay mất.

### K-1 · `khoi_phuc()` KHÔNG kiểm tệp trước khi đè — nhận cả tệp 0 byte

`migrate.khoi_phuc()` chỉ `shutil.copy2`. Nó không `PRAGMA integrity_check`, không đếm bảng, không kiểm phần đầu tệp, không kiểm số byte.

**Tệp sao lưu bị CẮT GIỮA ĐƯỜNG — ba cách cắt, cả ba đều bị NHẬN:**

| Cách cắt | Tệp dở (byte) | `khoi_phuc()` NHẬN? | CSDL sau khi khôi phục |
|---|---|---|---|
| (a) hết chỗ ghi (`RLIMIT_FSIZE`) | **0** | **CÓ** (rc 0) | 0 byte · **0 bảng** · `integrity_check = "ok"` |
| (b) `SIGKILL` @40% thời gian ghi | 4.530.176 | **CÓ** | `database disk image is malformed` |
| (b) `SIGKILL` @70% | 41.705.472 | **CÓ** | `database disk image is malformed` |
| (b) `SIGKILL` @90% | 80.863.232 *(đủ byte — giết quá muộn)* | **CÓ** | khớp gốc |
| (c) cắt cụt 40% sau khi ghi xong | 32.345.292 | **CÓ** | `database disk image is malformed` |
| **ĐỐI CHỨNG ĐƯỜNG** — tệp LÀNH | 80.863.232 | CÓ | **0 lệch · 34.336.000 đồng** |

> **Chi tiết đắt nhất:** tệp **0 byte** qua được `PRAGMA integrity_check` với kết quả **`"ok"`** — vì tệp SQLite dài 0 byte **LÀ** một CSDL rỗng **hợp lệ**. Nghĩa là một bước "kiểm bản sao lưu bằng `integrity_check`" **cũng không bắt được** ca này. Chỉ kiểm **số byte** / **số bảng** mới bắt.
>
> Ở vế ngược lại: `sao_luu()` **có** chốt `so_byte <= 0` và chốt đó **đúng** — nhưng nó nằm ở **đường SAO LƯU**, không ở đường KHÔI PHỤC. Đường khôi phục chưa ai đo. (Lượt cắt (a) còn cho thấy `sao_luu()` **báo lỗi ỒN ÀO**: `rc=1`, `sqlite3.OperationalError: disk I/O error` — hỏng đúng kiểu nên hỏng.)

### K-2 · Tệp bị sửa 1 BYTE — 5/5 được NHẬN

| Chỗ sửa | Vị trí | SQLite **tự** báo | `khoi_phuc()` | Băm khớp gốc |
|---|---|---|---|---|
| **trong trang dữ liệu ĐANG DÙNG** | 138.836 | `row 2 missing from index sqlite_autoindex_don_hang_1` | **CÓ** (rc 0) | **KHÔNG** |
| 25% tệp | 140.288 | `ok` | **CÓ** | có |
| 50% tệp | 280.576 | `ok` | **CÓ** | có |
| 75% tệp | 420.864 | `ok` | **CÓ** | có |
| byte 0 (magic `SQLite format 3`) | 0 | `DatabaseError: file is not a database` | **CÓ** | **KHÔNG** |
| **ĐỐI CHỨNG ĐƯỜNG** — tệp không sửa | — | `ok` | CÓ | có · **0 lệch** |

**Vì sao ca "byte trong trang đang dùng" là ca quan trọng nhất:** bốn chỗ theo tỉ lệ là **may rủi** — ba chỗ giữa tệp rơi vào vùng không dùng nên **không đổi gì**. Nếu chỉ đo bốn chỗ đó thì kết luận rút ra là *"sửa 1 byte vô hại"*, một kết luận **SAI**. Ca thứ năm tìm thẳng byte đầu của mã đơn `SHOP-A-002` trong `don_hang.ma_don` nên **chắc chắn** nằm trong trang có dữ liệu — và nó **đổi dữ liệu thật**, SQLite **tự phát hiện**, mà `khoi_phuc()` vẫn nhận.

### K-3 · Ba lượt khôi phục trong cùng một GIÂY xoá mất bản cất DUY NHẤT

```
1 lượt khôi phục            → 1 bản cất · băm 0b7cd1d3e61be8a047b9b82c  ← ĐÚNG dữ liệu vừa mất
3 lượt liên tiếp (cùng giây) → 1 bản cất · băm 83c77a559733f703900e7c04  ← KHÁC
băm dữ liệu lúc chụp         = 0b7cd1d3e61be8a047b9b82c
```

Tên bản cất đặt theo **GIÂY**: `hub-truoc-rollback-%Y%m%d-%H%M%S.db`. Lượt sau **ghi đè im lặng** lượt trước. Lượt khôi phục thứ hai cất chính *nội dung bản sao lưu* (vô dụng), còn bản cất của lượt **đầu** — thứ **duy nhất** chứa dữ liệu thật — **đã bị xoá**.

**Đây ĐÚNG khuôn lỗi mà `sao_luu()` đã bị bắt và đã sửa:** nó thêm hậu tố `-1`, `-2` khi trùng tên (đo được trong cùng lượt chạy: `hub-truoc-migrate-20261016-075229.db` **và** `hub-truoc-migrate-20261016-075229-1.db` cùng tồn tại). **Cùng một tệp `app/migrate.py`: một hàm đã vá, một hàm chưa.** AG-04 **KHÔNG** sửa `app/migrate.py` (tệp của AG-00) — báo cáo để AG-00 quyết.

### K-4 · Khôi phục bản schema THẤP hơn → TỤT IM LẶNG

Đưa bản sao lưu **v6** (20 bảng) cho `khoi_phuc()` đang chạy trên CSDL **v9** (51 bảng):

```
rc_khoi_phuc 0 · phiên bản sau khôi phục: 6 · số bảng: 20  (trước: 51)
thông báo duy nhất: "[migrate] Đã khôi phục từ …"
hệ VẪN CHẠY trên v6: rc_ghi_tren_v6 = 0
```

Không so phiên bản, không cảnh báo. **31 bảng và toàn bộ dữ liệu của chúng biến mất, im lặng** — người trực gõ đúng một lệnh `--rollback` với tệp cũ.

**Đường ra (đo được):** `migrate.chay()` nâng lại được **cấu trúc** → `phien_ban 9 · 51 bảng · integrity ok`. Nhưng **DỮ LIỆU thì không**: tổng tiền sau khi nâng = **1.298.000** (chỉ còn `goi_dich_vu.gia_thang` của bản v6), trong khi bản v9 trước đó là **34.336.000**. *Cấu trúc cứu được, dữ liệu thì không.*

### K-5 · `khoi_phuc()` nhận tệp KHÔNG phải SQLite → CSDL chết

| Tệp đưa vào | `khoi_phuc()` | CSDL sau |
|---|---|---|
| tệp mang magic `PGDMP` (giả lập `pg_dump -Fc`) | **NHẬN** (rc 0) | 65.544 byte · `file is not a database` |
| **`pg_dump -Fc` THẬT** (124.700 byte, rc 0) trên cụm riêng | **NHẬN** (rc 0) | 124.700 byte · `file is not a database` |
| **ĐỐI CHỨNG ĐƯỜNG** — bản sao SQLite thật | CÓ | **0 lệch** |

Kịch bản vận hành: cùng một thư mục có hai loại tệp sao lưu, gõ nhầm một cái → CSDL đang chạy chết ngay, không một lời cảnh báo.

### K-6 · Bản sao lưu CSDL KHÔNG TỰ ĐỦ: khóa không đi kèm

`sao_luu()` chỉ sao lưu `hub.db`. Khóa mã hóa credentials nằm ở tệp **KHÁC** trong cùng thư mục (`cau_hinh.DUONG_DAN_KHOA` → `khoa-noi-bo.key` + thư mục `khoa/`).

| Vế | Số đo |
|---|---|
| Khôi phục vào thư mục mới: khớp dữ liệu? | **0 lệch · 51 bảng · 34.336.000 đồng · integrity ok** |
| Khóa có đi kèm không? | **KHÔNG** (`co_khoa_o_ban_khoi_phuc = False`) |
| Giải mã credentials ở **bản gốc** | `CRED-DAT ['api_key','secret']` · `WH-DAT 15` — **ĐẠT** |
| Giải mã credentials ở **bản khôi phục** | **HỎNG** — `LoiKhoa` |
| Hệ có TỰ SINH khóa mới rồi giải mã ra rác không? | **KHÔNG** — không tệp khóa nào xuất hiện |

Thông báo thật của hệ:

> `LoiKhoa: không thấy khóa 'goc' trong …/B/khoa — bản mã dùng khóa này sẽ KHÔNG giải được. Khôi phục khóa từ bản sao lưu, đừng sinh khóa mới.`

**Đây là kiểu hỏng ỒN ÀO — đúng loại hỏng nên có, và là điểm TỐT cần ghi nhận.** Nhưng khoảng trống vẫn còn: `khoi_phuc()` **báo thành công** trong khi bản khôi phục **không dùng được cho lời gọi hãng nào**, và không có gì nhắc rằng còn một quy trình thứ hai (`app/sao_luu_khoa.py`, `trien_khai/sao_luu_ngoai/` — G12). Số dòng khớp, tổng tiền khớp, `integrity_check = ok`, và credentials thì không đọc được.

---

## 6. KỊCH BẢN 9 — POSTGRESQL: `sao_luu()` LÀM GÌ (P-G15-02)

Cụm **RIÊNG**, tự dựng, socket Unix, `listen_addresses=''` — **KHÔNG mở cổng TCP nào**. `_kiem_cong_an_toan` **TỪ CHỐI** cổng 5432. Vân tay cụm `:5432` chụp **trước** và **sau**: **KHÔNG ĐỔI** (`vip_customs`, `vip_customs_g16`, `vip_customs_test` vẫn nguyên 6 CSDL, cùng PID postmaster).

CSDL PostgreSQL có **dữ liệu thật**: 6 đơn · 6 bút toán · 2 tenant · 4 sự kiện webhook · **9.324.000 đồng**.

| Phép đo | Kết quả |
|---|---|
| **ĐO 1** — `hub.db` **không tồn tại** (đúng trạng thái máy chủ đã chuyển kho sang PostgreSQL) | `rc = 0` · `stderr = ""` · tệp **4.096 byte** · **0 BẢNG** · **0 đồng** · `integrity_check = "ok"` |
| **ĐO 2** — `hub.db` còn sót dữ liệu SQLite **CŨ** | `rc = 0` · tệp 561.152 byte · **51 bảng** · **31.141.000 đồng** · băm khớp đúng tệp SQLite đó — **nhưng không một dòng nào của dữ liệu PostgreSQL** |
| **ĐO 3** — `pg_dump -Fc` THẬT đưa cho `khoi_phuc()` | **NHẬN** (rc 0) → CSDL `file is not a database` |
| **ĐỐI CHỨNG ĐƯỜNG** — CÙNG hàm, kho SQLite có dữ liệu | `rc = 0` · 51 bảng · 31.141.000 đồng · **băm khớp gốc** |

### Phán: **SAI** — và sai theo kiểu tệ nhất trong ba kiểu

`migrate.sao_luu()` **không có nhánh PostgreSQL nào**. Nó luôn `sqlite3.connect(cau_hinh.DUONG_DAN_CSDL)`. Ba khả năng, và phép đo chọn đúng khả năng giữa:

1. *Ném lỗi ỒN ÀO* → người trực biết ngay không có đường lùi. **KHÔNG PHẢI** (`nem_loi_chi_tiet = false`).
2. **IM LẶNG BÁO THÀNH CÔNG với một ĐƯỜNG LÙI GIẢ.** ← **ĐÚNG CÁI NÀY** (`im_lang_bao_thanh_cong = true`).
3. *Làm đúng* → không thể, vì không có nhánh nào.

Đối chứng đường chứng minh đây **không phải** "hàm hỏng": cùng hàm, kho SQLite có dữ liệu, cho ra bản sao **hoàn hảo**. Kết luận đúng là: **hàm không có nhánh PostgreSQL** — và chốt `so_byte <= 0` của nó **không cứu được**, vì 4.096 byte > 0.

**ĐO 2 còn khó thấy hơn ĐO 1:** `hub.db` cũ còn sót lại cho ra một bản sao **trông hoàn toàn hợp lệ** (51 bảng, 31 triệu đồng, băm khớp). Người trực thấy một tệp sao lưu "đầy đủ" và **tin nó**. Không có phép kiểm nào trong hệ phân biệt được hai thứ này — vì **không có chỗ nào hỏi "kho đang chạy là kho nào"**.

> **ĐỀ XUẤT P-G15-02** (`docs/OWNER_ACTIONS.md` mục C3, `docs/G13_G15_ACCEPTANCE.md`): khi kho đổi sang PostgreSQL, `sao_luu()` phải **NÉM** thay vì trả về một tệp rỗng. Phép đo này **xác nhận đề xuất đó là cần**, và **định lượng được hậu quả**: `rc = 0`, 4.096 byte, 0 bảng, `integrity_check = "ok"`. **Cần anh Thành duyệt** — AG-04 **KHÔNG** sửa `app/migrate.py`.

> **NGOÀI PHẠM VI (đã có người làm, KHÔNG làm lại):** `pg_dump -Fc` → `pg_restore` — tức **đường ĐÚNG của PostgreSQL ở tầng công cụ** — đã được `app/thu/thu_postgres.py` **lớp K** đo (giữ số dòng từng bảng, tổng tiền, payload nhị phân; có ca `k2` tự kiểm bỏ đồ). Bộ đo này **không** đo lại việc đó; nó đo đúng chỗ lớp K không đo: **hàm sản phẩm `migrate.sao_luu()`**.

---

## 7. TỰ KIỂM BỎ ĐỒ — PHÉP SO PHẢI LÀM ĐỎ ĐƯỢC

Thiếu lớp này thì mọi khẳng định ở §3–§6 đều có thể là hệ quả của một `so_sanh()` luôn trả `[]`. Lớp `I_TuKiemBoDo` **sửa bản sao** rồi đòi phép so **PHẢI** thấy khác:

| Ca | Sửa gì | Phép so phải thấy |
|---|---|---|
| `i1` | `UPDATE don_hang SET cod = cod + 1` (đúng **1 đồng**) | lệch trục **TIỀN** (số dòng **không** đổi) |
| `i2` | xoá 3 dòng `don_lich_su` | lệch trục **DÒNG** |
| `i3` | `DROP TABLE ds_dong` | báo **MẤT BẢNG** |
| `i4` | đổi `khach_hang.ten` (không phải cột tiền) | số dòng **và** tổng tiền **y nguyên**, chỉ **băm** đổi |
| `i5` | `kiem_khong_rong` với cột tiền = 0 | **NÉM** (chống phép đo rỗng) |
| `i6` | khai một cột tiền **không tồn tại** | **NÉM** (chống danh sách mục) |
| `i7` | `chup()` trên CSDL WAL | **KHÔNG** tạo tệp nào trong thư mục đang đo |

**Ca `i7` bắt một lỗi của chính bộ đo:** bản sao lưu của `sao_luu()` mang chế độ **`wal`** (byte 18–19 phần đầu tệp = 2), nên mở `mode=ro` **thất bại** với `unable to open database file` — SQLite cần tạo được tệp `-shm` cạnh nó. Nếu lấy chính lỗi đó làm kết luận thì ra *"bản sao lưu không mở được ⇒ hỏng"*, trong khi bản sao lưu **TỐT**, chỉ có **cách mở là sai**. Nên `chup()` chép `db` (+ `-wal`) ra vùng tạm rồi mở ở đó: mở được CSDL WAL, **và không tạo `-wal`/`-shm` trong thư mục đang đo** (một `-shm` lạc vào `sao-luu/` sẽ thành "bản sao lưu ma" trong phép đếm tệp của kịch bản 3).

---

## 8. PHẠM VI ĐÃ ĐO — VÀ CÁI GÌ NẰM NGOÀI

**ĐÃ ĐO**
- `migrate.sao_luu()` và `migrate.khoi_phuc()` trên SQLite **có dữ liệu thật**, đối chiếu **51 bảng × (số dòng + tổng tiền)** × 18 cột tiền, cộng băm toàn kho.
- Sáu đường hỏng: tệp cắt giữa đường (3 cách) · tệp sửa 1 byte (5 chỗ) · khôi phục đè · khôi phục schema thấp hơn · khôi phục nhầm tệp · khôi phục thiếu khóa.
- `migrate.sao_luu()` khi kho là PostgreSQL (cụm riêng, 3 phép đo, có đối chứng đường).
- Bảy ca tự kiểm bỏ đồ + hai chốt chống phép đo rỗng/mục.
- Mã thoát **thật** của **mọi** lệnh con; vân tay cụm `:5432` trước/sau.

**NGOÀI PHẠM VI — khai ra để không ai suy rộng**
- **`pg_dump`/`pg_restore`** (đường ĐÚNG của PostgreSQL ở tầng công cụ) — đã có `app/thu/thu_postgres.py` lớp K. Lượt này chỉ đo **hàm sản phẩm** `sao_luu()`.
- **Sao lưu KHÓA** (gói `.vipkb`, `app/sao_luu_khoa.py`, `trien_khai/sao_luu_ngoai/`) — đã có G12. Lượt này chỉ đo **sự thiếu liên kết** giữa hai nửa.
- **Sao lưu ra ngoài máy / đám mây / ổ ngoài / lịch tự động** — chưa có gì để đo.
- **Khôi phục trên MÁY CHỦ SẠCH bằng khóa THẬT** — blocker B-2 của dự án vẫn còn nguyên. Lượt này chạy trên **máy dựng**, dữ liệu **thử**, trong **thư mục tạm**.
- **Tính đúng của từng DÒNG ngoài các cột tiền** — `bam_toan_kho` phủ được mọi thay đổi byte của dữ liệu logic, nhưng nó là phép so **tổng thể**: nó nói "có gì đó khác", không nói "dòng nào".
- **`csdl.py` / `migrate.py`** — **KHÔNG sửa** (tệp của AG-00). Mọi khuyết điểm ở §5–§6 là **báo cáo**, không phải bản vá.
- **E2E / tầng 3 (DOM/CSS trong Chromium thật)** — không chạy trong lượt này: chúng ghi báo cáo ra `thu_giao_dien/_bao-cao/`, **ngoài** phạm vi ghi được cấp cho AG-04.
- **Mạng** — KHÔNG gọi API hãng nào (V-G09-01 + V-13906-05 chưa cấp). Cụm PostgreSQL thử **không mở cổng TCP**.

---

## 9. VIỆC CÒN LẠI — ĐỀ NGHỊ, KHÔNG TỰ LÀM

| # | Việc | Vì sao cần | Ai quyết |
|---|---|---|---|
| 1 | `khoi_phuc()` **thêm hậu tố khi trùng tên** (như `sao_luu()` đã làm) | K-3: 3 lượt cùng giây xoá mất bản cất duy nhất | **AG-00** (tệp `app/migrate.py`) |
| 2 | `khoi_phuc()` **kiểm tệp trước khi đè**: `integrity_check` + đếm bảng + số byte > 0 + magic SQLite | K-1, K-2, K-5: 10/10 tệp hỏng được nhận, có tệp làm CSDL chết hẳn | **AG-00** |
| 3 | `khoi_phuc()` **so phiên bản schema** và **CẢNH BÁO khi tụt** | K-4: v6 đè v9 mất 31 bảng, im lặng | **AG-00** + anh Thành |
| 4 | `sao_luu()` **NÉM khi kho là PostgreSQL** (P-G15-02) | §6: `rc 0`, 4.096 byte, 0 bảng, "đường lùi" giả | **anh Thành** (`docs/OWNER_ACTIONS.md` C3) |
| 5 | `sao_luu()` **buộc khóa đi kèm** hoặc **nhắc ồn ào** rằng còn quy trình thứ hai | K-6: khôi phục "thành công" mà credentials không đọc được | anh Thành |
| 6 | Đưa **chốt chống phép đo rỗng** (`kiem_khong_rong`) vào `trien_khai/do_csdl.py` của G11 | §2: G11 so **số dòng**; lượt này chứng minh cần thêm **tổng tiền** | AG-05 |
| 7 | Thêm cột tiền vào `COT_TIEN` mỗi khi DDL có cột tiền mới | §2.1: chốt **đã nổ thật** một lần trong lượt này | mọi agent chạm DDL |

---

## 10. TỆP CỦA LƯỢT NÀY

| Tệp | Dòng | SHA-256 (16 ký tự đầu) | Vai |
|---|---|---|---|
| `trien_khai/g20-saoluu/khung_do.py` | 377 | `b8075bac3d30cab4` | Khung đo: danh sách cột tiền · chụp · so sánh · hai chốt chống rỗng/mục |
| `trien_khai/g20-saoluu/gieo.py` | 250 | `5e878e8983b3644f` | Gieo dữ liệu thật (3 tenant · 15 đơn COD · 57 bút toán) bằng hàm sản phẩm |
| `trien_khai/g20-saoluu/kich_ban.py` | 815 | `56a7ef7048d587a6` | 8 kịch bản đo — **nguồn duy nhất**, hai vỏ cùng gọi |
| `trien_khai/g20-saoluu/do_vong_tron.py` | 239 | `ba5e328517650249` | Vỏ chạy tay, in cho người đọc, ghi JSON |
| `trien_khai/g20-saoluu/do_postgres.py` | 262 | `bc1980f79d2740be` | Kịch bản 9 — cụm PostgreSQL riêng |
| `trien_khai/g20-saoluu/chay_do.sh` | 85 | `5c7f5aec301b1482` | Vỏ chạy: mã thoát **trước** mọi ống dẫn |
| `app/thu/thu_g20_saoluu.py` | 678 | `604ba3fc771038c8` | Bộ thử 41 ca, vào lượt hồi quy chung |

*Kết quả tệp này: `python3 app/thu/thu_g20_saoluu.py` → **Ran 41 tests · OK · 0 skip · exit 0** (8,2 giây).*
