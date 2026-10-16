# G21 / AG-02 — SAO LƯU & KHÔI PHỤC: **FAIL-CLOSED** HAY KHÔNG?

**Nền:** `integration/g20` @ `a3400a8` · worktree `g21-ag02-backup` · schema `v9` (51 bảng)
**Người làm:** AG-02 (SAO LƯU / KHÔI PHỤC) · **Ngày đo:** 16/10/2026
**Tệp của lượt này:** `trien_khai/g20-saoluu/fail_closed.py` (mới) · `trien_khai/g20-saoluu/ban_va.py` (mới) ·
`app/thu/thu_g21_saoluu.py` (mới) · `app/thu/thu_g20_saoluu.py` (viết lại 8 ca) · tài liệu này (mới)
**KHÔNG sửa:** `app/csdl.py` · `app/migrate.py` (tệp của AG-00) · `app/cau_hinh.py` · `app/sao_luu_khoa.py`

---

## 0. KẾT LUẬN TRƯỚC, CHỨNG CỨ SAU

| # | Câu hỏi | Trả lời **ĐO ĐƯỢC** |
|---|---|---|
| 1 | Khi sao lưu/khôi phục HỎNG, hệ có **DỪNG LẠI VÀ BÁO RÕ** không? | **KHÔNG — 9/10 kịch bản FAIL_OPEN.** Hệ im lặng đi tiếp và để lại trạng thái nửa vời. |
| 2 | Bộ 41 ca của AG-04 XANH nghĩa là gì? | **KHÔNG có nghĩa gì.** Tám ca mang nhãn `ĐỘC HẠI ĐÃ BIẾT` **PIN HÀNH VI FAIL-OPEN** — chúng khẳng định ĐÚNG cái sai. Xem §1. |
| 3 | Hết đĩa giữa lúc **KHÔI PHỤC** thì CSDL đích ra sao? | **MẤT SẠCH.** Còn 280.576 byte với `database disk image is malformed`; **20 bảng → 0 bảng**, 1.298.000 → 0 đồng. Mã thoát 1 và một traceback **không cứu được gì**. Đây là phát hiện nặng nhất của lượt này — **AG-04 chưa hề đo nó**. |
| 4 | Hết đĩa giữa lúc **SAO LƯU**? | Mã thoát 1 (tốt), CSDL nguồn nguyên (tốt), nhưng **để lại một tệp 0 byte mang tên `hub-truoc-migrate-*.db`** và KHÔNG dọn — một đường lùi GIẢ. |
| 5 | Tệp sao lưu **0 byte**? | **Được NHẬN, mã thoát 0.** `integrity_check` trả **"ok"** cho nó (tệp 0 byte LÀ CSDL rỗng hợp lệ) ⇒ CSDL đích thành **0 byte, 0 bảng**, 34.336.000 → 0 đồng. |
| 6 | Ba lượt khôi phục trong cùng một giây? | **0 bản cất nào giữ được dữ liệu vừa mất.** Tên đặt theo GIÂY nên lượt sau xoá lượt trước — đúng khuôn lỗi `sao_luu()` đã bị bắt và đã vá, `khoi_phuc()` thì chưa. |
| 7 | Khôi phục bản **schema thấp hơn**? | **TỤT IM LẶNG**: v9 → v6, 51 → 20 bảng, mất **33.038.000 đồng**, mã thoát 0, không một lời cảnh báo. |
| 8 | PostgreSQL (P-G15-02)? | **IM LẶNG BÁO THÀNH CÔNG với ĐƯỜNG LÙI GIẢ.** Tệp 4.096 byte / **0 bảng** / `integrity_check = ok`, trong khi PostgreSQL giữ 6 đơn + 9.324.000 đồng. |
| 9 | Đã có bản vá chưa? | **CÓ, và ĐÃ ĐO.** `trien_khai/g20-saoluu/ban_va.py` — cùng bộ đo trên bản vá: **9/10 FAIL_CLOSED**, 1 khoảng trống còn lại **có tên** (§8). `app/migrate.py` là tệp của AG-00 nên làn này **KHÔNG tự sửa** — bản vá ở dạng dựng được + đo được, chờ AG-00 áp. |
| 10 | Bộ đo có RĂNG không? | **CÓ, chứng minh bằng máy.** Bốn phép tiêm (D1…D4), mỗi phép gỡ ĐÚNG MỘT chốt khỏi bản vá, và mỗi phép bị **đúng kịch bản phải bắt nó** bắt được. Xem §7. |

**Phán tổng:** đây **KHÔNG** phải "đường lành chạy được nên yên tâm". Đường lành chạy đúng
(đối chứng đường `DC`: **FAIL_CLOSED**). Nhưng **mọi** đường hỏng đều đi tiếp trong im lặng, và
hai trong số đó **phá huỷ CSDL đích**. Một quy trình sao lưu không fail-closed thì tệ hơn không
có quy trình sao lưu: nó làm người trực TIN rằng có đường lùi.

---

## 1. VÌ SAO 41 CA XANH MÀ NGHIỆM THU G20 LẠI **FAILED**

`app/thu/thu_g20_saoluu.py` (AG-04) có tám ca mang nhãn `ĐỘC HẠI ĐÃ BIẾT`. Chúng không canh
một bất biến — chúng **ghi lại hành vi hiện có** và khẳng định nó:

```python
# NGUYÊN VĂN bản G20, ca D4:
self.assertEqual(self.kq["so_lan_khoi_phuc_NHAN_tat_ca"], len(self.kq["cac_lan_sua"]),
                 "khoi_phuc() đã bắt đầu từ chối tệp bị sửa — hành vi đã đổi")
```

Đọc thẳng: **5/5 tệp hỏng PHẢI được nhận thì ca này mới xanh**. Tức bộ thử đang **đòi** hành vi
fail-open. Đó là lý do bộ 41 ca XANH (`Ran 41 tests · OK · EXIT=0`) trong khi `docs/QA_G20.md`
§4.1 gọi bộ đỏ duy nhất là một lỗ hổng sản phẩm và §5 ghi thẳng phần lớn phạm vi là **CHƯA ĐO**.

**AG-02 đã VIẾT LẠI tám ca đó theo BẤT BIẾN ĐÚNG.** Chúng giờ **ĐỎ trên cây này**, và ĐỎ là
TÌNH TRẠNG ĐÚNG — lỗi nằm ở `app/migrate.py`, ngoài vùng được ghi của làn này. Tám ca đó:

| Ca | Bất biến ĐÚNG nó pin |
|---|---|
| `C3` | tệp dở LÀM KHÁC BẢN GỐC phải bị TỪ CHỐI; lượt hết-chỗ-ghi phải có rc ≠ 0 |
| `D4` | bản sửa LÀM KHÁC BẢN GỐC phải bị TỪ CHỐI |
| `E3` | ba lượt khôi phục cùng giây KHÔNG được xoá nhau; ≥ 1 bản cất giữ được dữ liệu vừa mất |
| `F2` | bản schema THẤP hơn phải bị TỪ CHỐI kèm hai phiên bản; CSDL đích phải nguyên |
| `G2` | tệp KHÔNG phải SQLite phải bị TỪ CHỐI; CSDL đích phải nguyên |
| `K3` | kho là PostgreSQL ⇒ `sao_luu()` không được thoát 0 với 0 bảng |
| `K4` | `hub.db` CŨ không được coi là dữ liệu đang chạy (**còn hở**, xem §8) |
| `K5` | bản `pg_dump -Fc` THẬT phải bị TỪ CHỐI |

**KHÔNG nới điều kiện cho tám ca này xanh.** Nới ra là quay lại đúng thứ đã làm G20 FAILED.

---

## 2. CÁCH CHẠY LẠI — MÃ THOÁT THẬT, SỐ CA, SỐ SKIP

```sh
python3 trien_khai/g20-saoluu/fail_closed.py             # bảng cho người đọc, 10 kịch bản
python3 trien_khai/g20-saoluu/fail_closed.py --nhanh     # bỏ PostgreSQL
python3 trien_khai/g20-saoluu/fail_closed.py --json F    # số đo thô cho máy đọc
python3 app/thu/thu_g21_saoluu.py                        # bộ thử fail-closed (mới)
python3 app/thu/thu_g20_saoluu.py                        # bộ AG-04, 8 ca đã viết lại
```

| Lệnh | Mã thoát | Số ca | Skip | Ghi chú |
|---|---|---|---|---|
| `python3 trien_khai/g20-saoluu/fail_closed.py` | **1** | 10/10 kịch bản | **0** | mã thoát 1 = còn kịch bản FAIL_OPEN; đây là **phán quyết**, không phải lỗi chạy |
| `python3 app/thu/thu_g21_saoluu.py` | **1** | **Ran 21 tests** · **9 hỏng** · 0 skip | **0** | đúng **9 ca lớp A** = lỗi sản phẩm. Lớp B (đối chứng đường) và lớp C (tự kiểm bộ đo, 8 ca) **đều XANH** |
| `python3 app/thu/thu_g20_saoluu.py` | **1** | **Ran 41 tests** · 8 hỏng · 0 skip | **0** | đúng 8 ca đã viết lại |

### 2.1 VÂN TAY — NỀN VÀ TỆP CỦA LƯỢT NÀY

**Nền:** `integration/g20` @ **`a3400a8`** (`a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1`) ·
`main` = `de740dc` · worktree `g21-ag02-backup`.

| Tệp | SHA-256 (20 ký tự đầu) |
|---|---|
| `app/thu/thu_g20_saoluu.py` | `c4ba47dc8555540a374d` |
| `app/thu/thu_g21_saoluu.py` | `8b2d23b7c0ddb7fe68f1` |
| `trien_khai/g20-saoluu/kich_ban.py` | `d4a2c664e20139eb2f2e` |
| `trien_khai/g20-saoluu/fail_closed.py` | `d5b9ab5834e50ff77def` |
| `trien_khai/g20-saoluu/ban_va.py` | `0137444889e3bd67d7e2` |
| `trien_khai/g20-saoluu/gieo.py` | `6939bffcc3042d866a64` |
| `trien_khai/g20-saoluu/do_postgres.py` | `8601fb2b704efb15278d` |
| `docs/G21_BACKUP_RESTORE.md` | `b13074fbb842cd11605d` |
| `app/migrate.py` · `app/csdl.py` · `app/cau_hinh.py` | **KHÔNG ĐỔI** — `git diff --stat` rỗng cho cả ba |

`app/thu/chay_tat_ca.sh` dò bộ thử bằng `find app/thu gateway/thu -name 'thu_*.py'`, nên
`thu_g21_saoluu.py` **tự vào lượt hồi quy chung**.

**Vì sao lớp A và 8 ca G20 PHẢI đỏ:** chúng khẳng định bất biến fail-closed; sản phẩm chưa
fail-closed. Đây là tín hiệu ĐÚNG. Đổi lại, `test_c4` của lớp C chứng minh các ca đó **SỬA ĐƯỢC**:
chạy đúng bộ đo trên `migrate.py` đã vá ⇒ **9/10 FAIL_CLOSED**.

---

## 3. TIÊU CHÍ ĐẠT — KHAI TRƯỚC KHI ĐO

Một trường hợp HỎNG là **FAIL_CLOSED** khi và chỉ khi:

* **(a)** mã thoát **KHÁC 0** — tiến trình dừng lại;
* **(b)** có một dòng thông báo **NÓI RA chỗ hỏng** (dài ≥ 15 ký tự + chứa dấu hiệu hỏng; lấy
  dòng khớp **CUỐI CÙNG**, vì dòng đầu của một traceback là `Traceback (most recent call last):`
  — khớp chữ nhưng KHÔNG cho biết hỏng ở đâu);
* **(c)** CSDL ĐÍCH còn **NGUYÊN VẸN**: so **TỪNG BẢNG**, cả **SỐ DÒNG** lẫn **TỔNG TIỀN từng cột
  tiền**, cộng `integrity_check` · `phien_ban` · `bam_toan_kho` · `so_byte`.

**Hai chỗ tôi cố ý KHÔNG làm chặt hơn thực tế — nói ra để không ai đọc quá:**

1. Khi hỏng, `khoi_phuc()` để một **traceback Python** thoát ra. Traceback CÓ nói ra chỗ hỏng
   (tên hàm + đường dẫn nguồn và đích), nên vế (b) tính là ĐẠT — nhưng nó KHÔNG phải thông báo
   cho người trực. Khác nhau đó ghi thành trường riêng `la_traceback_tho` và **in ra ở bảng**,
   **KHÔNG trộn vào phán quyết**: trộn vào là làm hỏng phép đo, vì người sau sẽ đọc "FAIL_OPEN vì
   traceback" và tưởng lỗi nằm ở văn phong thông báo, trong khi lỗi thật nằm ở vế (c).
2. **`S1`/`S2` chỉ tính những lượt THẬT SỰ làm hỏng.** Đo được: một lượt `SIGKILL` ở 90% thời gian
   vẫn cho ra bản sao lưu **trọn vẹn**; ba trong năm chỗ lật byte rơi vào **vùng trang trống** nên
   dữ liệu KHÔNG đổi. Nhận những tệp đó là **ĐÚNG**. Đếm chúng là thổi phồng con số và làm mất
   lòng tin vào cả bảng. `fail_closed.py` tách `cat_hong_that` / `cat_vo_hai` và in **cả hai**.

---

## 4. BẢNG PHÁN QUYẾT — 10 KỊCH BẢN TRÊN `app/migrate.py` NGUYÊN BẢN

| Mã | Kịch bản | rc | (b) thông báo | Trạng thái CUỐI của CSDL đích | Phán |
|---|---|---|---|---|---|
| **DC** | đối chứng đường: sao lưu → khôi phục lại chính CSDL gốc | 0 | — | **y nguyên từng bảng**, 0 lệch | **FAIL_CLOSED** |
| **S1** | sao lưu bị cắt giữa đường (5 cách) | 0 | **không có** | 4/5 lượt cắt bị **NHẬN** ⇒ 0 bảng / malformed | FAIL_OPEN |
| **S2** | tệp sao lưu bị sửa 1 byte (5 chỗ) | 0 | **không có** | 2/5 bản sửa **có hại** đều bị NHẬN | FAIL_OPEN |
| **S3** | tệp sao lưu **rỗng 0 byte** | 0 | **không có** | **0 byte · 0 bảng · 0 đồng** | FAIL_OPEN |
| **S4** | khôi phục ĐÈ lên CSDL đã có dữ liệu | 0 | **không có** | **0 bản cất** giữ được dữ liệu vừa mất | FAIL_OPEN |
| **S5** | khôi phục bản **schema thấp hơn** (v6 đè v9) | 0 | **không có** | v6 · **20 bảng** · 1.298.000 đồng | FAIL_OPEN |
| **S6a** | **hết đĩa** giữa lúc SAO LƯU | **1** | có (traceback) | nguồn nguyên ✓ · **tệp 0 byte bỏ lại** | FAIL_OPEN |
| **S6b** | **hết đĩa** giữa lúc KHÔI PHỤC | **1** | có (traceback) | **malformed · 0 bảng · 0 đồng** | FAIL_OPEN |
| **S7** | khôi phục nhầm tệp không phải SQLite | 0 | **không có** | 561.152 → **65.544 byte, không đọc được** | FAIL_OPEN |
| **S8** | PostgreSQL: `sao_luu()` (P-G15-02) | 0 | **không có** | bản sao **4.096 byte / 0 bảng** | FAIL_OPEN |

**KẾT LUẬN: 1/10 FAIL_CLOSED · 9 FAIL_OPEN.** (Kịch bản duy nhất đạt là ĐỐI CHỨNG ĐƯỜNG —
đúng như thiết kế: nó là vế chứng minh bộ đo không phải một cái ĐỎ cứng đơ.)

---

## 5. CHI TIẾT TỪNG TRƯỜNG HỢP HỎNG — MÃ THOÁT THẬT · THÔNG BÁO THẬT · TRẠNG THÁI CUỐI

### S6b · HẾT ĐĨA GIỮA LÚC KHÔI PHỤC — **phát hiện nặng nhất, AG-04 chưa đo**

Cách dựng để giới hạn ghi rơi **ĐÚNG** vào lần chép thứ hai (chỗ dễ đo sai nhất, nên nói rõ):
`khoi_phuc()` chép HAI lần — (1) CSDL hiện tại → `hub-truoc-rollback-*.db`, (2) bản sao lưu →
CSDL hiện tại. Muốn rơi vào lần 2 thì phải có `co(đích) < giới hạn < co(bản sao lưu)`.

```
co(CSDL đích) = 200.704  <  giới hạn = 280.576  <  co(bản sao lưu) = 561.152
   ⇒ giới hạn rơi vào LẦN CHÉP THỨ HAI           (tien_quyet_dat = True, khẳng định trong ca thử)
```

| Vế | Số đo thật |
|---|---|
| Mã thoát | **1** |
| Thông báo thật | `OSError: [Errno 27] File too large: '…/A/sao-luu/hub-truoc-migrate-20261016-142823-1.db' -> '…/B/hub.db'` |
| CSDL đích TRƯỚC | 200.704 byte · **20 bảng** · 1.298.000 đồng · `integrity_check = ok` |
| CSDL đích SAU | 280.576 byte · `DatabaseError: database disk image is malformed` · **0 bảng đọc được** · 0 đồng |
| Bản cất để lại | `hub-truoc-rollback-20261016-142823.db` (200.704 byte) — cứu được, nhưng phải làm TAY |
| **Phán** | **FAIL_OPEN — vế (c) trượt.** Mã thoát 1 và traceback KHÔNG cứu được CSDL đích. |

**Vì sao đây là lỗi sản phẩm, không phải "hết đĩa thì đành chịu":** `shutil.copy2` ghi **THẲNG**
lên `cau_hinh.DUONG_DAN_CSDL`. Chép qua một tệp TẠM cùng thư mục rồi `os.replace` là **nguyên tử**
— hết đĩa thì tệp tạm bị dọn và CSDL đang chạy **không bị đụng**. Cùng một tình huống, hai kết
cục khác hẳn nhau, và vế thứ hai đo được (§6).

### S6a · HẾT ĐĨA GIỮA LÚC SAO LƯU

| Vế | Số đo thật |
|---|---|
| Giới hạn ghi | 224.460 byte = 40% của CSDL 561.152 byte |
| Mã thoát | **1** |
| Thông báo thật | `sqlite3.OperationalError: disk I/O error` (kèm traceback) |
| CSDL NGUỒN sau lượt hỏng | **nguyên vẹn**: 561.152 byte · 51 bảng · 34.336.000 đồng · `integrity_check = ok` |
| Tệp bỏ lại trong `sao-luu/` | **1 tệp**: `hub-truoc-migrate-20261016-142823.db` — **0 byte**, `integrity_check = "ok"`, 0 bảng, KHÔNG dọn |
| **Phán** | **FAIL_OPEN — vế "để lại đường lùi giả" trượt.** |

Chốt `so_byte <= 0` **có** trong `sao_luu()` nhưng nằm **SAU** lời gọi `nguon.backup(ban)`; khi
lời gọi đó ném thì chốt không bao giờ chạy, và tệp dở ở lại. Người trực thấy một tệp trong
`sao-luu/`, tin là có đường lùi — và chỉ phát hiện khi đã quá muộn (`S3` đo đúng kết cục đó).

### S3 · TỆP SAO LƯU RỖNG 0 BYTE — cái bẫy `integrity_check`

| Vế | Số đo thật |
|---|---|
| Tệp đưa vào | 0 byte |
| `PRAGMA integrity_check` trên nó | **`"ok"`** ← tệp SQLite dài 0 byte LÀ một CSDL rỗng **HỢP LỆ** |
| Số bảng của nó | **0** |
| Mã thoát `khoi_phuc()` | **0** — **NHẬN** |
| Thông báo thật | `[migrate] Đã khôi phục từ …/ban-sao-luu-0-byte.db. Bản trước khi khôi phục cất ở …` |
| CSDL đích TRƯỚC → SAU | 561.152 → **0 byte** · 51 → **0 bảng** · 34.336.000 → **0 đồng** · băm toàn kho → băm của rỗng |
| **Phán** | **FAIL_OPEN.** |

**Bài học đo được, không suy đoán:** một bước "kiểm bản sao lưu bằng `integrity_check`" —
cách kiểm ai cũng nghĩ tới trước tiên — **KHÔNG bắt được ca này**. Bất biến đúng phải là **SỐ
BẢNG** (hoặc số byte). Bản vá dùng số bảng, và đó là lý do nó đóng được `S3`.

### S1 · SAO LƯU BỊ CẮT GIỮA ĐƯỜNG — 5 cách cắt, 4 làm hỏng thật

| Cách cắt | Tệp dở | `khoi_phuc()` | CSDL đích sau khi nhận |
|---|---|---|---|
| `a-het-cho-ghi` (RLIMIT_FSIZE 40%) | **0 byte** | **NHẬN** (rc 0) | **0 bảng** · 0 đồng |
| `b-bi-giet-40%` (SIGKILL) | 33.992.704 byte | **NHẬN** (rc 0) | `database disk image is malformed` |
| `b-bi-giet-70%` | 56.803.328 byte | **NHẬN** (rc 0) | `database disk image is malformed` |
| `b-bi-giet-90%` | 72.994.816 byte | **NHẬN** (rc 0) | `database disk image is malformed` |
| `c-cat-cut-40%` (`truncate`) | 32.345.292 byte | **NHẬN** (rc 0) | `database disk image is malformed` |
| **Đối chứng đường** | **trọn vẹn** 80.863.232 byte | rc 0 | **khớp gốc, 0 lệch** ✓ |

**Một chỗ AG-02 phải SỬA CÁCH ĐO, không phải sửa sản phẩm:** bản G20 giết tiến trình sau khi
ngủ `giay_tron * f`, với `giay_tron` đo từ MỘT lượt sao lưu trước đó. Đo lại thấy nó **KHÔNG TẤT
ĐỊNH** — lượt đo đầu chịu chi phí khởi động + đệm đĩa nên các lượt sau nhanh hơn hẳn, và có lượt
cả ba mốc giết đều rơi SAU lúc ghi xong: chốt chống phép-đo-rỗng `so_cach_tep_de_that_su_cut >= 3`
báo **2**, cả kịch bản đỏ vì một lý do không liên quan gì tới sản phẩm. Nay bộ đo **GIỠ TỚI KHI
TỆP ĐỦ LỚN** rồi mới giết (`moc_giet_byte`), nên cùng một mốc kích thước trên mọi máy. Lượt nào
giết quá muộn được đánh dấu `cat_truot` và **không** tính là tệp dở (`so_luot_cat_truot`).

Kết luận **không** phụ thuộc con số byte: mọi tệp dở đều được nhận với rc 0, và **5/5** lượt cắt
đều là ca hỏng thật.

### S2 · TỆP SAO LƯU BỊ SỬA 1 BYTE — 5 chỗ, 2 chỗ có hại

| Chỗ sửa | Vị trí | Băm khớp gốc | Số lệch | SQLite tự báo | `khoi_phuc()` |
|---|---|---|---|---|---|
| `e-trang-dung` (byte đầu mã đơn `SHOP-A-002`) | 138.836 | **False** | **2** | `row 2 missing from index sqlite_autoindex_don_hang_1` | **NHẬN** rc 0 |
| `a-25%` | 140.288 | True | 0 | `ok` | NHẬN rc 0 — **vô hại** |
| `b-50%` | 280.576 | True | 0 | `ok` | NHẬN rc 0 — **vô hại** |
| `c-75%` | 420.864 | True | 0 | `ok` | NHẬN rc 0 — **vô hại** |
| `d-byte0` (magic tệp) | 0 | **False** | **57** | `NGOAI-LE DatabaseError: file is not a database` | **NHẬN** rc 0 |
| **Đối chứng đường** | — | — | 0 | `ok` | rc 0 · **khớp gốc** ✓ |

### S4 · KHÔI PHỤC ĐÈ LÊN CSDL ĐÃ CÓ DỮ LIỆU

Bất biến ở đây **KHÔNG** phải "đích không đổi" — khôi phục đè thành công thì đích PHẢI đổi. Bất
biến là: **dữ liệu TRƯỚC khi đè còn CỨU ĐƯỢC**, và ba lượt trong cùng một giây không xoá nhau.

| Vế | Số đo thật |
|---|---|
| Mã thoát 3 lượt | **0 · 0 · 0** |
| Bản cất sau **1** lượt | **1** tệp, băm `506d55f2…` **= băm dữ liệu lúc chụp** ✓ |
| Bản cất sau **3** lượt | **vẫn 1** tệp, băm `443313bd…` ✗ |
| Số bản cất giữ được dữ liệu vừa mất | **0** |
| **Phán** | **FAIL_OPEN.** Bản cất của lượt ĐẦU — thứ DUY NHẤT chứa dữ liệu thật — đã bị lượt SAU **xoá im lặng**. |

### S5 · KHÔI PHỤC BẢN SCHEMA THẤP HƠN

| Vế | Số đo thật |
|---|---|
| Mã thoát | **0** |
| Thông báo thật (duy nhất) | `[migrate] Đã khôi phục từ …` — **không một lời cảnh báo** |
| Phiên bản | v9 → **v6** |
| Số bảng | 51 → **20** (mất **31 bảng**) |
| Tổng tiền | 34.336.000 → 1.298.000 (mất **33.038.000 đồng**) |
| Sau đó hệ có chạy được không | **CÓ**, rc 0, trên schema cũ |
| **Phán** | **FAIL_OPEN.** |

### S7 · KHÔI PHỤC NHẦM TỆP KHÔNG PHẢI SQLITE

| Vế | Số đo thật |
|---|---|
| Tệp đưa vào | 65.544 byte, magic `PGDMP` (bản `pg_dump -Fc` giả) |
| Mã thoát | **0** — **NHẬN** |
| CSDL đích | 561.152 → **65.544 byte**, `DatabaseError: file is not a database`, **0 bảng đọc được** |
| **Đối chứng đường** | cùng lệnh, bản sao lưu SQLite THẬT → rc 0 · **0 lệch** ✓ |
| **Phán** | **FAIL_OPEN.** |

### S8 · POSTGRESQL — P-G15-02 (cụm RIÊNG, cổng 55.432, **TỪ CHỐI :5432**)

Ba phép đo, cùng một câu hỏi: `sao_luu()` có phải một ĐƯỜNG LÙI THẬT không?

| # | Tình huống | Kết quả ĐO ĐƯỢC | Phán |
|---|---|---|---|
| 1 | `hub.db` **không tồn tại** (kho đã chuyển sang PostgreSQL) | rc **0** · **4.096 byte** · **0 bảng** · `integrity_check = "ok"` · `stderr` **rỗng** — trong khi PostgreSQL giữ **6 đơn** và **9.324.000 đồng** | **FAIL_OPEN** — đường lùi GIẢ, im lặng |
| 2 | `hub.db` **CŨ còn sót** (dữ liệu SQLite không còn chạy) | rc 0 · **51 bảng** · **34.336.000 đồng** · băm khớp đúng tệp SQLite đó — trông HOÀN TOÀN hợp lệ, mà **không chứa một dòng nào** của dữ liệu đang chạy | **FAIL_OPEN** — **còn hở**, xem §8 |
| 3 | `khoi_phuc()` nhận một bản `pg_dump -Fc` **THẬT** | `pg_dump` rc 0 · **124.700 byte** · `khoi_phuc()` **NHẬN** rc 0 · CSDL SQLite → không đọc được | **FAIL_OPEN** |
| — | Đối chứng đường: CÙNG hàm với kho SQLite có dữ liệu | rc 0 · băm khớp gốc · ≥ 45 bảng | ✓ ĐẠT |

Vế đối chứng đường là vế quyết định cách đọc: kết luận là **"hàm không có nhánh PostgreSQL"**,
KHÔNG phải **"hàm hỏng"**. Hai câu đó khác nhau, và chỉ phép đo này phân biệt được.

---

## 6. BẢN VÁ ĐỀ XUẤT CHO `app/migrate.py` — VÀ KẾT QUẢ ĐO TRÊN NÓ

`app/migrate.py` là **tệp của AG-00**. Làn AG-02 **KHÔNG sửa nó**. Thay vào đó,
`trien_khai/g20-saoluu/ban_va.py` **DỰNG RA** một `app/` ứng viên trong thư mục tạm (mọi tệp là
symlink trỏ về cây thật, riêng `migrate.py` là bản dựng tại chỗ) rồi chạy **ĐÚNG bộ đo** trên đó
qua `G21_APP_DIR`. Cách vá: chèn các định nghĩa MỚI vào **ngay trước** khối
`if __name__ == "__main__":` — trong Python định nghĩa sau thắng, nên không phải cắt dán thân hàm
(dễ trượt, dễ hỏng im lặng). Bản dựng **TỪ CHỐI chạy** nếu không thấy mốc chèn.

### Ba chốt mới, và mỗi chốt ứng với một phép đo ĐỎ

| Chốt | Vá ca nào | Vì sao ĐÚNG chốt này |
|---|---|---|
| **1. Dấu kiểm `<bản-sao-lưu>.sha256`**, `sao_luu()` ghi và `khoi_phuc()` BẮT BUỘC kiểm | `S2` | Đây là vế DUY NHẤT bắt được "sửa 1 byte trong trang dữ liệu đang dùng" trong trường hợp `integrity_check` không thấy. Thiếu dấu kiểm ⇒ TỪ CHỐI (trừ khi người trực nói rõ đã biết chưa kiểm được). |
| **2. Ghi qua TỆP TẠM rồi `os.replace`** | `S6b` | Nguyên tử. Hỏng giữa đường thì CSDL đang chạy KHÔNG bị đụng — đúng vế (c). |
| **3. Tên bản cất KHÔNG BAO GIỜ ĐÈ + KIỂM PHIÊN BẢN SCHEMA + `_kiem_cau_truc` (magic · `integrity_check` · **SỐ BẢNG**)** | `S4` `S5` `S3` `S7` `S6a` | Số bảng là vế bắt được tệp 0 byte mà `integrity_check` bỏ qua. Không đè tên là vế giữ bản cất. |

**Một cái bẫy đã đo được, và cách bản vá tránh nó — ghi lại vì nó suýt làm hỏng cả bản vá:**

```
mode=ro              -> OperationalError: unable to open database file     ← TỪ CHỐI NHẦM mọi bản sao lưu TỐT
mode=ro&immutable=1  -> integrity_check = ok · 51 bảng                     ← cách mở ĐÚNG
```

Bản sao lưu do `sao_luu()` sinh ra **mang chế độ WAL** (byte 18–19 của phần đầu = 2), nên
`mode=ro` thuần **thất bại** — SQLite cần tạo được tệp `-shm` cạnh nó. Một bản vá ngây thơ dùng
`mode=ro` sẽ từ chối **mọi** bản sao lưu tốt. Bản vá dùng `immutable=1`, và **nói ra cái giá**:
`immutable=1` bỏ qua tệp `-wal` đi kèm, nên phép kiểm này chỉ đặt trên BẢN SAO LƯU (đúng, vì API
backup của SQLite ghi thẳng nội dung vào tệp chính), KHÔNG đặt trên CSDL đang chạy.

### Kết quả đo trên bản vá — cùng bộ đo, cùng tiêu chí

| Mã | `app/migrate.py` nguyên bản | `migrate.py` **đã vá** |
|---|---|---|
| S1 sao lưu bị cắt giữa đường | FAIL_OPEN | **FAIL_CLOSED** |
| S2 tệp bị sửa 1 byte | FAIL_OPEN | **FAIL_CLOSED** |
| S3 tệp rỗng 0 byte | FAIL_OPEN | **FAIL_CLOSED** |
| S4 khôi phục đè lên CSDL đang chạy | FAIL_OPEN | **FAIL_CLOSED** |
| S5 khôi phục bản schema thấp hơn | FAIL_OPEN | **FAIL_CLOSED** |
| S6a hết đĩa khi sao lưu | FAIL_OPEN | **FAIL_CLOSED** |
| S6b hết đĩa khi khôi phục | FAIL_OPEN | **FAIL_CLOSED** |
| S7 nhầm tệp không phải SQLite | FAIL_OPEN | **FAIL_CLOSED** |
| **S8 PostgreSQL** | FAIL_OPEN | **FAIL_OPEN — còn ĐÚNG MỘT khoảng trống có tên (§8)** |
| DC đối chứng đường | FAIL_CLOSED | **FAIL_CLOSED** |
| **TỔNG** | **1/10** | **9/10** |

---

## 7. TỰ KIỂM BỘ ĐO — TIÊM LỖI FAIL-OPEN, BỘ ĐO PHẢI BẮT ĐƯỢC

Không có lớp này thì mọi dòng `FAIL_OPEN` ở trên không chứng minh gì: một bộ đo luôn trả ĐỎ,
hoặc một bộ đo đọc nhầm `migrate.py`, đều cho ra cùng một bảng.

**Hai vế.** Vế 1 (`C1`, `C2`, `C3` trong `app/thu/thu_g21_saoluu.py`) tiêm vào hàm phán quyết
`phan_quyet()` — hàm THUẦN TÚY — các bản ghi TỔNG HỢP đã biết là fail-open và đã biết là ĐẠT,
và đòi nó phán đúng cho **mọi** mã kịch bản, ở **cả ba** vế (a)(b)(c) và ở **từng nhánh riêng**;
cộng chốt "mã kịch bản lạ KHÔNG được tính là ĐẠT".

**Vế 2 (`C5`…`C8`) là vế nặng:** gỡ **ĐÚNG MỘT** chốt khỏi bản vá, chạy lại **CHÍNH bộ đo** trên
đó, và đòi **đúng kịch bản phải bắt nó** bắt được. Kết quả đo:

| Phép tiêm | Gỡ chốt gì | Kịch bản PHẢI bắt | Kết quả ĐO |
|---|---|---|---|
| **D1** | bỏ tệp tạm, chép THẲNG lên CSDL đang chạy (đúng lỗi gốc) | `S6b` | **BẮT ĐƯỢC** — `S6b` FAIL_OPEN, các ca khác vẫn FAIL_CLOSED |
| **D2** | tên bản cất đặt theo GIÂY, cho phép đè (đúng lỗi gốc) | `S4` | **BẮT ĐƯỢC** — `S4` FAIL_OPEN |
| **D3** | bỏ chốt TỤT SCHEMA (đúng lỗi gốc) | `S5` | **BẮT ĐƯỢC** — `S5` FAIL_OPEN |
| **D4** | bỏ MỌI phép kiểm chứng bản sao lưu | `S3` và `S7` | **BẮT ĐƯỢC** — cả hai FAIL_OPEN |

Mỗi phép tiêm bị **đúng** kịch bản của nó bắt, và các kịch bản khác **vẫn xanh** ⇒ bộ đo **PHÂN
BIỆT ĐƯỢC**, không phải một cái ĐỎ cứng đơ.

### Hai lỗi của chính bộ đo, đo được trong lúc làm — ghi lại vì chúng dạy đúng một điều

1. **Lượt tự kiểm GIẢ.** Bản đầu của `_chay_bien_the` gán `kich_ban.APP = <biến thể>` **sau khi**
   nạp mô-đun. `kich_ban` dựng các chuỗi lệnh `_MA_SAO_LUU`/`_MA_KHOI_PHUC` **một lần, lúc nạp**,
   từ `APP` — nên gán sau **không** dựng lại chúng, và lượt chạy vẫn đo **mã GỐC** trong khi
   tưởng đang đo bản vá. `test_c4` bắt được (nó đòi `ban_va` phải xanh, mà kết quả y hệt mã gốc).
   Nay `G21_APP_DIR` được đặt ở **dòng đầu**, trước mọi `import`, và tiến trình con **in ra cả ba
   nơi giữ đường dẫn `app/`** để ca thử khẳng định chúng cùng trỏ vào biến thể đang đo.
2. **Hai ĐỎ GIẢ do chính phép đếm.** (a) `ca_khoi_phuc_de_len_csdl_dang_chay` lọc bản cất bằng
   `"rollback" in f` — một bản vá fail-closed cất kèm `-wal`/`-shm` nên bộ đếm trả **3** thay vì
   **1**; (b) phép đếm chỉ băm bản cất **CUỐI** theo thứ tự chữ cái, mà bản giữ dữ liệu vừa mất
   là bản của lượt **ĐẦU**. Cả hai đã sửa, và chú thích tại chỗ nói rõ vì sao.

**Một phép tiêm tôi đã BỎ, và vì sao:** tôi định tiêm "gỡ chốt bắt buộc dấu kiểm `.sha256`" và
kỳ vọng `S2` bắt được. ĐO RỒI THÌ SAI: gỡ chốt đó **không tạo ra fail-open nào quan sát được**,
vì `khoi_phuc()` còn lớp kiểm cấu trúc trên chính tệp tạm, và lớp đó bắt được **cả hai** bản sửa
có hại thật (`e-trang-dung` hỏng chỉ mục, `d-byte0` mất magic). Một phép tiêm không tạo ra khác
biệt quan sát được thì không chứng minh gì; giữ nó lại chỉ làm bảng tự kiểm trông đẹp hơn thực tế.

---

## 8. CÒN HỞ — NÓI THẲNG, KHÔNG TÔ HỒNG

| # | Mục | Vì sao chưa đóng | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **`S8`/`do2` — `hub.db` CŨ còn sót trong khi kho đang chạy là PostgreSQL.** Bản vá đóng được `do1` (không có `hub.db`) và `do3` (nhập nhầm `pg_dump`), nhưng **không** đóng được `do2`. | Hệ **KHÔNG có khái niệm "kho đang chạy là kho nào"**, nên không có gì để đối chiếu. Bịa một phép đoán (mtime, kích thước tệp) là **vi phạm nguyên tắc "không đoán"** — và nó sẽ im lặng đúng vào lúc cần nhất. | **QUYẾT ĐỊNH SẢN PHẨM**: một cờ cấu hình nói rõ kho đang chạy (`SQLite` / `PostgreSQL`), rồi `sao_luu()` TỪ CHỐI khi kho đang chạy không phải SQLite. AG-00/AG-05 chốt. |
| 2 | **Sao lưu CSDL KHÔNG TỰ ĐỦ: khóa mã hoá credentials không đi kèm.** | `khoi_phuc()` báo thành công trong khi bản khôi phục không dùng được cho lời gọi hãng nào. Ranh giới giữa "khôi phục CSDL" và "khôi phục khóa" là **có thật**; bản vá G21 cố ý **không** mở rộng phạm vi sang tệp khóa — mở rộng là một quyết định sản phẩm. | `app/sao_luu_khoa.py` + `trien_khai/sao_luu_ngoai/` đã có; cần **buộc** quy trình hai bước thành MỘT (hoặc một lệnh nhắc). |
| 3 | **`SIGKILL` giữa lúc sao lưu vẫn để lại tệp tạm `*.db.dang-ghi`.** | Không thể dọn sau `SIGKILL` — không còn tiến trình nào để dọn. Giảm nhẹ đo được: tên nó **không** kết thúc bằng `.db` và **không** có `.sha256`, nên `khoi_phuc()` đã vá **TỪ CHỐI** nó. | Không đóng được hoàn toàn. Có thể thêm bước dọn tệp `*.dang-ghi` cũ lúc khởi động. |
| 4 | **Cửa sổ nhỏ giữa lúc xoá `-wal`/`-shm` và `os.replace`.** | Nguyên tử trên MỘT tệp thì được; nguyên tử trên BA tệp thì cần đổi cả thư mục. Bản vá **giảm** cửa sổ này (bản mới đã ghi xong và đã kiểm TRƯỚC khi xoá WAL) và **bảo toàn** `-wal` bằng cách chép nó cạnh bản cất. | Chấp nhận được; ghi ra để người sau biết nó CÒN. |
| 5 | **E2E / tầng 3 · gọi API hãng kể cả sandbox · deploy/push/tunnel** | `V-G09-01` + `V-13906-05` CHƯA CẤP ⇒ **BỊ CẤM**. Mọi phép đo của lượt này chỉ chạm tệp trong thư mục TẠM và cụm PostgreSQL RIÊNG. | anh Thành cấp quyền |
| 6 | **Chuyển CSDL nghiệp vụ sang PostgreSQL (D-8)** | **BỊ CẤM.** Cụm `:5432` chỉ được **ĐỌC** vân tay; cụm đo là cụm riêng cổng **55.432**, socket Unix. | quyết định của anh Thành |
| 7 | **Chốt `D-9` (`city`/`area`)** | Lượt này **không** chạm ánh xạ `area`. Giữ nguyên chốt cứng ngoài mock. | làn có quyền sửa ánh xạ |

---

### 8.1 MỘT TÀI LIỆU ĐÃ LỆCH SỐ, VÀ TÔI **KHÔNG** ĐƯỢC SỬA NÓ

`docs/G20_BACKUP_RESTORE.md` §1 ghi **"`python3 app/thu/thu_g20_saoluu.py` · mã thoát 0 · Ran 41
tests · OK · 0 skip"**. Con số đó **đã hết đúng** sau lượt này: cùng tệp, cùng 41 ca, nay là
**8 hỏng · mã thoát 1** — vì tám ca `ĐỘC HẠI ĐÃ BIẾT` đã được viết lại theo bất biến fail-closed
(§1). Nội dung **đo lường** của tài liệu G20 vẫn đúng nguyên; chỉ dòng mã thoát là lệch.

`docs/G20_BACKUP_RESTORE.md` **KHÔNG nằm trong vùng được ghi** của làn này, nên tôi **không sửa**.
Đây là việc của **AG-00**: hoặc cập nhật dòng đó, hoặc trỏ nó sang tài liệu này. Để nguyên thì
người đọc sau sẽ thấy một tài liệu nói "41 ca OK" trong khi lệnh đó trả về 1.

---

## 9. TỆP CỦA LƯỢT NÀY

| Tệp | Trạng thái | Vai |
|---|---|---|
| `trien_khai/g20-saoluu/fail_closed.py` | **mới** | Bộ đo fail-closed: 10 kịch bản, hàm phán quyết thuần túy, hai phép đo MỚI (hết đĩa khi sao lưu / khi khôi phục) |
| `trien_khai/g20-saoluu/ban_va.py` | **mới** | Bản vá đề xuất cho `app/migrate.py` + 4 phép tiêm lỗi + bộ dựng `app/` ứng viên |
| `app/thu/thu_g21_saoluu.py` | **mới** | Bộ thử fail-closed: 21 ca, 3 lớp (bất biến · đối chứng đường · tự kiểm bộ đo) |
| `app/thu/thu_g20_saoluu.py` | **sửa** | 8 ca `ĐỘC HẠI ĐÃ BIẾT` viết lại theo bất biến ĐÚNG; giữ nguyên mọi đối chứng đường và chốt chống phép-đo-rỗng |
| `trien_khai/g20-saoluu/kich_ban.py` | **sửa** | `G21_APP_DIR`; lọc `.db` khi đếm bản cất; bắt `stderr` của `khoi_phuc()`; băm MỌI bản cất; chịu được "không để lại tệp nào" |
| `trien_khai/g20-saoluu/gieo.py` · `do_postgres.py` | **sửa** | `G21_APP_DIR` |
| `docs/G21_BACKUP_RESTORE.md` | **mới** | Tài liệu này |
| `app/migrate.py` · `app/csdl.py` · `app/cau_hinh.py` | **KHÔNG sửa** | Tệp của AG-00 — bản vá ở dạng DỰNG ĐƯỢC + ĐO ĐƯỢC, chờ AG-00 áp |

---

## 10. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY, KHÔNG BẰNG LỜI

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng **kể cả sandbox** | Không một lời gọi mạng nào trong `fail_closed.py`, `ban_va.py`, `thu_g21_saoluu.py`; mọi HTTP của bộ AG-04 chỉ chạm `127.0.0.1` cổng OS cấp | ✓ |
| 2 | Push / deploy / tunnel / mở cổng ra ngoài | Không một lệnh `git push`/`ssh`/tunnel. PostgreSQL: socket Unix, `listen_addresses=''`, **TỪ CHỐI cổng 5432** | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | Không đọc `.env`; CSDL và log nằm trong thư mục TẠM; cụm PG là cụm thử tự dựng | ✓ |
| 4 | Không đoán mã trạng thái chưa hãng xác minh (D-4) | Lượt này **không** chạm bảng ánh xạ trạng thái | ✓ |
| 5 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8) · **CẤM dùng `:5432`** | Cụm đo là cụm RIÊNG cổng **55.432**; `van_tay_cum` chụp vân tay `:5432` TRƯỚC/SAU và ca `k1` khẳng định vân tay KHÔNG ĐỔI, còn thấy `vip_customs*` ⇒ nhìn đúng cụm hệ thống | ✓ |
| 7 | Không dùng Claude/mô hình khác · không tự bấm duyệt sandbox | Không một lời gọi mô hình nào; không thao tác duyệt nào | ✓ |
| 8 | Không xoá hàng loạt · không sửa ngoài phạm vi | Vùng được ghi đúng 4 mục được cấp; `app/migrate.py` và `app/csdl.py` **không đổi**; mọi `chot_an_toan()` TỪ CHỐI vùng dữ liệu thật | ✓ |
| 9 | **Mọi khẳng định có LỆNH THẬT + MÃ THOÁT THẬT + SỐ CA + SỐ SKIP** | §2; mã thoát ghi **trước mọi ống dẫn** | ✓ |
| 10 | **Mọi ca PHỦ ĐỊNH có ĐỐI CHỨNG ĐƯỜNG** · chứng minh ca thử ĐỎ ĐƯỢC | §5 (mỗi lớp có vế đối chứng) · §7 (4 phép tiêm) | ✓ |
