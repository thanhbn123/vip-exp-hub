# G21 / AG-02 — SAO LƯU & KHÔI PHỤC: **BẢN VÁ ĐÃ ÁP VÀO `app/migrate.py`**

**Nền:** `integration/g20` @ `e02383f` · worktree `g21-ag02-backup` · schema `v9` (51 bảng)
**Người làm:** AG-02 · **Ngày đo:** 16/10/2026 · lượt 2 (lượt 1 chỉ ĐO, lượt này **ÁP** và đo lại)
**Tệp của lượt này:** `app/migrate.py` (**sửa — bản vá đã áp**) · `trien_khai/g20-saoluu/` · `app/thu/thu_g21_saoluu.py` · tài liệu này · `docs/G20_BACKUP_RESTORE.md` §1 (bổ sung cảnh báo)
**KHÔNG sửa:** `app/csdl.py` · `app/cau_hinh.py`

---

## 0. KẾT LUẬN TRƯỚC, CHỨNG CỨ SAU

| # | Câu hỏi | Trả lời ĐO ĐƯỢC |
|---|---|---|
| 1 | Bản vá đã vào **TỆP THẬT** chưa, hay vẫn chỉ là bản dựng trong thư mục tạm? | **ĐÃ VÀO.** `app/migrate.py` 951 dòng, `sha256[:16]=c90ff7b9dbd4ad66`. `ban_va.xac_nhan()` kiểm **16 mảnh mã** của bản vá (có mặt đúng 1 lần) + **3 mảnh mã fail-open CŨ** (phải VẮNG) + **5 mốc tiêm**; thiếu một mảnh là **TỪ CHỐI chạy**. |
| 2 | Đo lại trên tệp thật, không tin kết quả cũ? | **CÓ.** `B2` chạy trên bản **đóng băng** (md5 `611182a621fd279c3816d5fc5d2785e3`) → **1/10 FAIL_CLOSED · rc 1 · 10 ca · 0 skip**. `B3` chạy trên **tệp thật đã vá** → **9/10 FAIL_CLOSED · rc 1 · 10 ca · 0 skip**. |
| 3 | `S8` (PostgreSQL fail-open, P-G15-02) đã đóng chưa? | **3/4 vế ĐÓNG, 1 vế CÒN HỞ và có tên.** `do1` (không có `hub.db`) → TỪ CHỐI · `do2a` (khai `postgresql`) → TỪ CHỐI · `do3` (nhầm `pg_dump -Fc`) → TỪ CHỐI. `do2b` (**chưa khai** kho đang chạy) → **vẫn thoát 0 với đường lùi giả** ⇒ `S8` = FAIL_OPEN, còn **đúng một** lý do. |
| 4 | Vậy cái còn thiếu là **mã** hay **quyết định**? | **QUYẾT ĐỊNH.** Đo trên biến thể `chinh_sach_tu_choi` (chỉ đổi `CHINH_SACH_CHUA_KHAI`): `S8` → **FAIL_CLOSED 1/1**. Chốt (4) đóng được **cả bốn** vế ở tầng mã. Cái giá nằm NGOÀI `S8` — xem §10 mục 1. |
| 5 | Đối chứng âm có răng không? | **CÓ.** Gỡ **đúng một** chốt khỏi **tệp thật** rồi chạy lại **chính bộ đo**: `D1`→`S6b` đỏ · `D2`→`S4` đỏ · `D3`→`S5` đỏ · `D4`→`S3`+`S7` đỏ. **4/4 phép tiêm bị đúng kịch bản của nó bắt**, không phép nào trượt. |
| 6 | Bộ thử của lượt này? | `python3 app/thu/thu_g21_saoluu.py` → **rc 0 · Ran 23 tests · OK · 0 skip**. |
| 7 | Con số `41 ca OK` trong `docs/G20_BACKUP_RESTORE.md` §1? | **Là MÀU XANH GIẢ** (8 ca pin hành vi fail-open). Đã bổ sung cảnh báo + bảng thay thế ngay tại §1 tài liệu đó; đo được hôm nay: **`Ran 41 tests · FAILED (failures=1)` · rc 1**, ca đỏ là cái PIN của khoảng hở `do2b`. |

**Phán tổng:** đường lành vẫn chạy đúng, và **9/10** kịch bản hỏng nay **DỪNG LẠI VÀ BÁO RÕ**.
Kịch bản thứ mười (`S8`) đã đóng **ba trong bốn** vế; vế còn lại **không phải một dòng mã thiếu**
— nó chờ một quyết định sản phẩm, và quyết định đó đã được **ĐO** chứ không chỉ được đề nghị.

---

## 1. LƯỢT NÀY KHÁC LƯỢT TRƯỚC Ở ĐÚNG MỘT CHỖ

Lượt 1 (G21) **đo** và **viết** bản vá, nhưng `app/migrate.py` khi đó là **tệp của AG-00** nằm
ngoài vùng được ghi, nên bản vá chỉ tồn tại dưới dạng một `app/` **dựng trong thư mục tạm**. Kết
quả 9/10 khi đó là kết quả **TRÊN BẢN SAO** — nó chứng minh bản vá ĐÚNG, **không** chứng minh
TỆP THẬT đúng.

Lượt này vùng được ghi đã mở rộng, nên:

* bản vá **nằm trong `app/migrate.py`**;
* mọi phép đo dưới đây chạy trên **tệp đó**, không phải trên bản dựng;
* bản **NGUYÊN BẢN** được đóng băng thành `trien_khai/g20-saoluu/migrate_nguyenban.py`
  (md5 **ghim cứng** trong `ban_va.MD5_NGUYENBAN`) — không có nó thì bảng "TRƯỚC/SAU" không
  dựng lại được sau khi đã vá, và một bảng TRƯỚC của tệp khác sẽ bị đem so với bảng SAU của tệp
  này mà không ai thấy.

Cách vá **không phải** chèn đè: `sao_luu()` và `khoi_phuc()` cũ được **thay tại chỗ**, nên
`app/migrate.py` chỉ còn **MỘT** định nghĩa mỗi hàm. Hai định nghĩa trong cùng một tệp là một
cái bẫy: người sau "sửa" bản chết rồi tự hỏi vì sao hành vi không đổi.

---

## 2. CÁCH CHẠY LẠI — MỘT LỆNH, MÃ THOÁT THẬT, SỐ CA, SỐ SKIP

```sh
python3 trien_khai/g20-saoluu/chay_do.py            # TOÀN BỘ bằng chứng của lượt này
python3 trien_khai/g20-saoluu/chay_do.py --nhanh    # bỏ mọi bước cần PostgreSQL
python3 app/thu/thu_g21_saoluu.py                   # bộ thử fail-closed (vào hồi quy chung)
```

**Mã thoát THẬT của lượt chạy dùng cho tài liệu này** (`ket_qua/chay_do.json`, driver rc **0**):

| Bước | Việc | rc | Số ca | Skip | Kết quả |
|---|---|---|---|---|---|
| B0 | `ast.parse` 6 tệp | **0** | 6 | 0 | cú pháp sạch |
| B1 | `ban_va.py` tự xác nhận bản vá đã áp | **0** | — | — | 16 mảnh vá · 3 mảnh cũ phải vắng · 5 mốc tiêm |
| B2 | 10 kịch bản trên **bản đóng băng** (`goc`) | **1** | 10 | 0 | **1/10 FAIL_CLOSED** (ĐỎ: S1 S2 S3 S4 S5 S6a S6b S7 S8) |
| B3 | 10 kịch bản trên **TỆP THẬT đã vá** | **1** | 10 | 0 | **9/10 FAIL_CLOSED** (ĐỎ: S8) |
| B4.D1 | tiêm `D1` (bỏ tệp tạm) | 0 | 1 | 0 | `S6b` **đỏ** — bắt được |
| B4.D2 | tiêm `D2` (tên bản cất theo giây) | 0 | 1 | 0 | `S4` **đỏ** — bắt được |
| B4.D3 | tiêm `D3` (bỏ chốt tụt schema) | 0 | 1 | 0 | `S5` **đỏ** — bắt được |
| B4.D4 | tiêm `D4` (bỏ mọi kiểm chứng) | 0 | 2 | 0 | `S3` + `S7` **đỏ** — bắt được |
| B5 | biến thể `chinh_sach_tu_choi` · đo `S8` | 0 | 1 | 0 | **1/1 FAIL_CLOSED** — chính sách `tu_choi` đóng hết |
| B6 | `app/thu/thu_g21_saoluu.py` | **0** | **23** | **0** | `OK` |
| B7 | `app/thu/thu_g20_saoluu.py` (AG-04) | 1 | **41** | **0** | `FAILED (failures=1)` — ca `test_k4`, xem §10 mục 1 |
| B8 | bảng số dòng/tổng tiền từng bảng | **0** | — | — | `ket_qua/bang_tung_bang_{truoc,sau}.md` |

`rc 1` ở **B2/B3/B4** KHÔNG phải bước hỏng: đó là **bộ đo kết luận ĐỎ**, tức kết quả ĐÚNG của
một lượt đo fail-closed (mã thoát ĐẠT của kịch bản hỏng là *khác 0*). Driver chỉ tính là hỏng
khi **B0/B1/B6/B8** khác 0, khi một **đối chứng âm không bắt được** phép tiêm, hoặc khi **B5**
không đóng được `S8`. Lượt này: **không có mục nào trong số đó**.

---

## 3. TIÊU CHÍ ĐẠT — KHAI TRƯỚC KHI ĐO

Giữ nguyên từ lượt 1, không nới một chữ. Một trường hợp HỎNG là `FAIL_CLOSED` khi và chỉ khi:

* **(a)** `rc != 0` — tiến trình thoát KHÁC 0;
* **(b)** có một dòng thông báo **NÓI RA chỗ hỏng** (>= 15 ký tự, chứa một dấu hiệu hỏng);
* **(c)** CSDL ĐÍCH còn **NGUYÊN VẸN** đúng như trước lượt hỏng — so **TỪNG BẢNG** (số dòng +
  **tổng tiền**), cộng `bam_toan_kho`.

Thiếu bất kỳ vế nào ⇒ `FAIL_OPEN`. **KHÔNG nới tiêu chí để lấy màu xanh** — nới ra là quay lại
đúng thứ đã làm nghiệm thu G20 kết luận `FAILED`.

---

## 4. BẢNG 10 KỊCH BẢN: TRƯỚC / SAU

Cùng một bộ đo, cùng tiêu chí, cùng một lượt chạy (`B2` và `B3`).

| Mã | Kịch bản | `rc` TRƯỚC → SAU | TRƯỚC (đóng băng) | SAU (**tệp thật đã vá**) |
|---|---|---|---|---|
| S1 | sao lưu bị cắt giữa đường (5 cách cắt) | 0 → 0 | FAIL_OPEN | **FAIL_CLOSED** |
| S2 | tệp sao lưu bị sửa 1 byte (5 chỗ) | 0 → 0 | FAIL_OPEN | **FAIL_CLOSED** |
| S3 | tệp sao lưu rỗng 0 byte | 0 → **1** | FAIL_OPEN | **FAIL_CLOSED** |
| S4 | khôi phục đè lên CSDL đang chạy | 0 → 0 | FAIL_OPEN | **FAIL_CLOSED** |
| S5 | khôi phục bản schema thấp hơn (v6 đè v9) | 0 → **1** | FAIL_OPEN | **FAIL_CLOSED** |
| S6a | hết đĩa giữa đường khi **sao lưu** | 1 → 1 | FAIL_OPEN | **FAIL_CLOSED** |
| S6b | hết đĩa giữa đường khi **khôi phục** | 1 → 1 | FAIL_OPEN | **FAIL_CLOSED** |
| S7 | khôi phục nhầm `pg_dump -Fc` | 0 → **1** | FAIL_OPEN | **FAIL_CLOSED** |
| S8 | PostgreSQL (P-G15-02) — **bốn vế** | 0 → **1** | FAIL_OPEN | **FAIL_OPEN — còn ĐÚNG MỘT vế có tên (§5)** |
| DC | đối chứng đường: sao lưu → khôi phục ngược | 0 → 0 | FAIL_CLOSED | **FAIL_CLOSED** |
| | **TỔNG** | | **1/10** | **9/10** |

Đọc cột `rc`: **S3 · S5 · S7** đổi từ `0` sang `1` — đó chính là "DỪNG LẠI VÀ BÁO RÕ" thay cho
"im lặng đi tiếp". Ba kịch bản còn `rc 0` (S1 · S2 · S4) **không phải chưa vá**: mã thoát của
chúng là của **lượt khôi phục lành** (`khoi_phuc()` TỪ CHỐI tệp hỏng ⇒ rc 1; lượt đối chứng
lành ⇒ rc 0), còn bất biến của chúng nằm ở vế (c). Ví dụ `S1`/`S2`: **0** tệp dở/hỏng nào được
`khoi_phuc()` nhận, và CSDL đích **Y NGUYÊN** — xem §9.

---

## 5. `S8` — BỐN VẾ, BA ĐÓNG, MỘT HỞ CÓ TÊN

Cụm PostgreSQL **RIÊNG** (socket Unix, `listen_addresses=''`, **TỪ CHỐI cổng 5432**), dữ liệu
gieo: **6 đơn hàng · 6 bút toán · 9.324.000 đồng**. Vân tay cụm `:5432` chụp TRƯỚC/SAU:
**KHÔNG ĐỔI** (`van_tay_5432_khong_doi = True`), và vẫn thấy `vip_customs*`.

| Vế | Tình huống | `rc` | Phán |
|---|---|---|---|
| `do1` | `hub.db` **KHÔNG tồn tại** (kho đã chuyển sang PostgreSQL) | **1** | **ĐÓNG** — TỪ CHỐI, thông báo nói rõ "không thấy CSDL tại …/hub.db nên KHÔNG có gì để sao lưu", và nói luôn rằng bản cũ vẫn "thành công" ở đây bằng cách **TẠO RA** một CSDL rỗng |
| `do2a` | `hub.db` **CŨ còn sót** + deployment **ĐÃ KHAI `postgresql`** | **1** | **ĐÓNG** — TỪ CHỐI, thông báo nêu thẳng: *"kho đang chạy là PostgreSQL (khai ở VIP_KHO_DANG_CHAY) nhưng `sao_luu()` KHÔNG CÓ NHÁNH PostgreSQL"* |
| `do2b` | Y HỆT `do2a` nhưng **CHƯA KHAI** | **0** | **CÒN HỞ** — trả một bản sao **51 bảng / 34.336.000 đồng**, băm khớp đúng tệp SQLite cũ, mà **không chứa một dòng nào** của 9.324.000 đồng đang chạy |
| `do3` | `khoi_phuc()` nhận một bản `pg_dump -Fc` **THẬT** (124.700 byte, pg_dump rc 0) | **1** | **ĐÓNG** — TỪ CHỐI; CSDL SQLite đích còn **51 bảng**, `integrity = ok` (trước bản vá: nhận, và CSDL chết) |

`do1` đóng được **mà không cần cờ nào** — bản cũ ở đây thoát 0 và trả một tệp **4.096 byte /
0 BẢNG / `integrity_check = "ok"`**, đúng dạng hỏng tệ nhất: *không ném lỗi, không làm đúng, mà
im lặng*. Nay nó **TỪ CHỐI trước khi tạo ra tệp nào**, nên **không còn tệp 4.096 byte nào để
người trực tưởng là đường lùi**.

### Vì sao `do2b` KHÔNG phải một dòng mã còn thiếu

Hệ **không có cách nào tự biết** kho nào đang chạy: `app/csdl.py` thuần SQLite, **không có**
`KHO_DANG_CHAY` / `DATABASE_URL` / nhánh PostgreSQL ở đâu trong cây. Bịa một phép đoán
(mtime, kích thước tệp, tên tệp) là **vi phạm nguyên tắc "không đoán"**, và nó sẽ im lặng đúng
vào lúc cần nhất. Nên bản vá **đọc một KHAI BÁO**:

```
cau_hinh.KHO_DANG_CHAY   (chỗ chính thức — do AG-00/AG-05 thêm)
VIP_KHO_DANG_CHAY        (biến môi trường, cùng ngữ nghĩa)
  'sqlite' | 'sqlite3'  ⇒ đi tiếp
  'pg' | 'postgres' | 'postgresql' | 'psql' ⇒ TỪ CHỐI
  giá trị LẠ            ⇒ TỪ CHỐI (KHÔNG coi là "chưa khai" — sai chính tả mà bị coi là chưa
                          khai là âm thầm quay về đúng chỗ đang muốn tránh)
  VẮNG                  ⇒ theo `CHINH_SACH_CHUA_KHAI`
```

`CHINH_SACH_CHUA_KHAI = "sqlite"` — **đây là quyết định sản phẩm, khai ở MỘT chỗ có tên**, và
§10 mục 1 nói rõ cái giá của cả hai lựa chọn bằng SỐ ĐO, không bằng tranh luận.

---

## 6. MỘT TÀI LIỆU ĐÃ LỆCH SỐ — NAY ĐÃ SỬA

Lượt 1 ghi nhận `docs/G20_BACKUP_RESTORE.md` §1 còn dòng *"`python3 app/thu/thu_g20_saoluu.py`
· rc 0 · Ran 41 tests · OK · 0 skip"*, và **không được sửa** tệp đó.

Lượt này tệp đó **nằm trong vùng được ghi theo chỉ đạo trực tiếp**, nên §1 đã được bổ sung một
khối **CẢNH BÁO** ngay dưới bảng mã thoát, gồm: vì sao con số đó là **màu xanh giả** (8 ca
`ĐỘC HẠI ĐÃ BIẾT` khẳng định ĐÚNG cái sai, ví dụ `assertEqual(khoi_phuc_NHAN_tat_ca, 5)`), và
**bảng ba mốc thay thế**:

| Mốc | `thu_g20_saoluu.py` | Vì sao |
|---|---|---|
| Bản gốc | `Ran 41 · OK · 0 skip` · rc 0 | 8 ca pin hành vi fail-open ⇒ **xanh giả** |
| AG-02 lượt 1 (vá chưa áp) | `Ran 41 · FAILED (failures=8)` · rc 1 | 8 ca viết lại theo bất biến ⇒ **đỏ thật** |
| **AG-02 lượt 2 (vá ĐÃ ÁP)** | **`Ran 41 · FAILED (failures=1)` · rc 1** | 7/8 ca nay xanh vì hành vi ĐÚNG; còn **1** ca — cái **PIN** của khoảng hở `do2b` |

Nội dung **đo lường** của tài liệu G20 (§2–§8) **vẫn đúng nguyên**: nó mô tả hành vi của **bản
gốc**, và bản gốc vẫn đo lại được ở `migrate_nguyenban.py`. Chỉ **dòng mã thoát** là đã lệch.

---

## 7. BẢN VÁ GỒM NHỮNG GÌ — VÀ "ĐÃ ÁP" LÀ MỘT KHẲNG ĐỊNH KIỂM ĐƯỢC

`trien_khai/g20-saoluu/ban_va.py` khai bản vá thành **mảnh**, và `xac_nhan()` **TỪ CHỐI chạy
tiếp** nếu bất kỳ mảnh nào thiếu (hoặc xuất hiện ≠ 1 lần), nếu còn mảnh mã fail-open cũ, hoặc
nếu mốc của một phép tiêm đã đổi. `test_c0` gọi nó trước mọi lượt đo.

| Nhóm chốt | Mảnh | Vá ca nào |
|---|---|---|
| **Dấu kiểm** | `_bam_tep` · ghi `<bản-sao-lưu>.sha256` · **BẮT BUỘC** kiểm khi khôi phục · so băm thật/mong đợi | S2 |
| **Nguyên tử** | `_chep_nguyen_tu` (tệp tạm + `os.replace`) · `sao_luu()` qua tệp tạm rồi `os.replace` · `khoi_phuc()` ghi bản mới ra tệp tạm rồi mới `os.replace` | S6a · S6b |
| **Tên không đè + schema** | `_duong_chua_dung` · `khoi_phuc()` TỪ CHỐI khi TỤT SCHEMA · đường thoát `toi_da_biet_chua_kiem_duoc` | S4 · S5 |
| **Cấu trúc** | `_kiem_cau_truc`: magic 16 byte · `integrity_check` · **SỐ BẢNG** (chốt chống bẫy 0 byte) | S3 · S7 |
| **Kho đang chạy** | `kho_dang_chay()` · `_kiem_kho_truoc_khi_sao_luu()` · `CHINH_SACH_CHUA_KHAI` · `hub.db` không tồn tại ⇒ TỪ CHỐI | S8 (`do1` `do2a` `do3`) |

**Hai cái bẫy đã đo được, và cách bản vá tránh — ghi lại vì chúng suýt làm hỏng cả bản vá:**

```
mode=ro              -> OperationalError: unable to open database file   ← TỪ CHỐI NHẦM mọi bản sao lưu TỐT
mode=ro&immutable=1  -> integrity_check = ok · 51 bảng                   ← cách mở ĐÚNG
```

Bản sao lưu do `sao_luu()` sinh ra **mang chế độ WAL**, nên `mode=ro` thuần thất bại. Bản vá
dùng `immutable=1` và **nói ra cái giá**: nó bỏ qua tệp `-wal` đi kèm, nên phép kiểm này chỉ đặt
trên **BẢN SAO LƯU**, không đặt trên CSDL đang chạy.

**Hai lỗ do chính bản vá tạo ra, đo được và đã vá trong cùng lượt này:**

1. **Đường thoát không tới được bằng dòng lệnh.** Mọi bản sao lưu sinh ra **TRƯỚC** bản vá đều
   **không có** `.sha256`, nên `migrate.py --rollback <tệp cũ>` bị TỪ CHỐI — và đường thoát
   `toi_da_biet_chua_kiem_duoc=True` chỉ gọi được từ Python. Một chốt không có đường thoát sẽ bị
   gỡ bằng cách tệ nhất: sửa mã lúc 3 giờ sáng. Nay có cờ
   `--toi-da-biet-chua-kiem-duoc`, đã đo: không cờ → **rc 1**; có cờ → **rc 0**.
2. **TỪ CHỐI NHẦM CSDL hợp lệ thiếu `schema_version`.** `_kiem_cau_truc` truy vấn thẳng bảng đó;
   một CSDL SQLite **hợp lệ** của hệ **trước G01.5** làm nó ném `OperationalError` → bị báo là
   *"KHÔNG ĐỌC ĐƯỢC như CSDL SQLite"*. Đó đúng cùng loại lỗi với bẫy `mode=ro`. Nay thiếu bảng ⇒
   phiên bản là **0**, và chốt TỤT SCHEMA tự so tiếp.

**Một chỗ cố ý KHÔNG làm chặt hơn, và nói ra:** trong `khoi_phuc()`, nếu CSDL đang chạy **có
nhưng không đọc được** (đang hỏng / đang bị khoá), chốt TỤT SCHEMA bị **bỏ qua** và lượt khôi
phục **đi tiếp** — kèm một dòng nói rõ. Lý do: khôi phục **chính là** đường cứu một CSDL hỏng,
nên từ chối ở đây là chặn đúng lúc cần nhất.

---

## 8. ĐỐI CHỨNG ÂM BẮT BUỘC — TIÊM LẠI LỖI, BỘ ĐO PHẢI ĐỎ

Không có lớp này thì mọi dòng `FAIL_CLOSED` ở §4 không chứng minh gì: một bộ đo luôn trả ĐỎ,
hoặc một bộ đo đọc nhầm `migrate.py`, đều cho ra cùng một bảng.

**Vế 1 — tiêm TỔNG HỢP** (`C1`, `C2`, `C3` của `thu_g21_saoluu.py`): tiêm vào hàm phán quyết
`phan_quyet()` — hàm THUẦN TÚY — các bản ghi đã biết là fail-open và đã biết là ĐẠT, đòi nó phán
đúng cho **mọi** mã, ở **cả ba** vế (a)(b)(c), **từng nhánh riêng**, cộng chốt "mã kịch bản lạ
KHÔNG được tính là ĐẠT". Lượt này bổ sung **ba nhánh mới của `S8`** (`do1`, `do2a`, `do2b`) —
thiếu chúng thì "khai cờ" là một tính năng **không ai canh**.

**Vế 2 — tiêm THẬT** (`B4`): gỡ **ĐÚNG MỘT** chốt khỏi **TỆP THẬT**, chạy lại **CHÍNH bộ đo**:

| Phép tiêm | Gỡ chốt gì | Kịch bản PHẢI bắt | Kết quả ĐO |
|---|---|---|---|
| **D1** | bỏ tệp tạm, chép THẲNG lên CSDL đang chạy | `S6b` | **BẮT ĐƯỢC** — `S6b` FAIL_OPEN |
| **D2** | tên bản cất theo GIÂY, cho phép đè | `S4` | **BẮT ĐƯỢC** — `S4` FAIL_OPEN |
| **D3** | bỏ chốt TỤT SCHEMA | `S5` | **BẮT ĐƯỢC** — `S5` FAIL_OPEN |
| **D4** | bỏ MỌI phép kiểm chứng bản sao lưu | `S3` **và** `S7` | **BẮT ĐƯỢC** — cả hai FAIL_OPEN |

Mỗi phép tiêm bị **đúng** kịch bản của nó bắt ⇒ bộ đo **PHÂN BIỆT ĐƯỢC**, không phải một cái ĐỎ
cứng đơ. Phép thay phải **KHỚP TỪNG KÝ TỰ**; không khớp thì **NÉM** — một phép tiêm "trượt" mà
vẫn chạy tiếp là kiểu hỏng tệ nhất, vì bộ đo sẽ báo ĐỎ trên một bản vá còn nguyên.

**Một phép tiêm tôi đã BỎ, và vì sao:** định tiêm *"gỡ chốt bắt buộc dấu kiểm `.sha256`"* và kỳ
vọng `S2` bắt được. ĐO RỒI THÌ SAI: gỡ chốt đó **không tạo ra fail-open nào quan sát được**, vì
`khoi_phuc()` còn lớp kiểm cấu trúc trên chính tệp tạm, và lớp đó bắt được **cả hai** bản sửa có
hại thật. Một phép tiêm không tạo ra khác biệt quan sát được thì không chứng minh được gì; giữ
nó lại chỉ làm bảng tự kiểm trông đẹp hơn thực tế.

**Hai lỗi của chính bộ đo, đo được trong lúc làm (giữ nguyên từ lượt 1, vì chúng dạy đúng một
điều):** (1) lượt tự kiểm GIẢ — gán `kich_ban.APP` **sau khi** nạp mô-đun không dựng lại chuỗi
lệnh, nên lượt chạy vẫn đo **mã GỐC** trong khi tưởng đang đo bản vá; nay `G21_APP_DIR` đặt ở
**dòng đầu** và tiến trình con **in ra cả ba nơi** giữ đường dẫn `app/`. (2) hai ĐỎ GIẢ do phép
đếm (lọc bản cất bằng `"rollback" in f` bắt luôn `-wal`/`-shm`; và chỉ băm bản cất **CUỐI** theo
thứ tự chữ cái, mà bản giữ dữ liệu vừa mất là bản của lượt **ĐẦU**).

---

## 9. BẰNG CHỨNG TỪNG BẢNG: SỐ DÒNG + TỔNG TIỀN

Sinh **thẳng từ số đo thô**, không chép tay:

```sh
python3 trien_khai/g20-saoluu/bang_tung_bang.py trien_khai/g20-saoluu/ket_qua/sau.json --md /tmp/b.md
```

Vì sao phải là **từng bảng**: `tong_tien_toan_kho` không đổi là điều kiện **CẦN**, không phải
điều kiện **ĐỦ** — hai bảng đổi cho nhau vẫn cho ra cùng một tổng. Nên `fail_closed._ghi` nay
giữ lại **phép chụp ĐẦY ĐỦ** (`chup_day_du`), và tệp markdown ở trên in ra từng bảng.

Kết quả trên **tệp thật đã vá** (`ket_qua/bang_tung_bang_sau.md`):

| Kịch bản | Số bảng LỆCH | `integrity_check` | `bam_toan_kho` | Ghi chú |
|---|---|---|---|---|
| **S3** tệp 0 byte | **0** | ok → ok | `dcc288ff…` → `dcc288ff…` | CSDL đích **không bị thay** bằng CSDL rỗng |
| **S6a** hết đĩa khi sao lưu | **0** | ok → ok | `ab98337e…` → `ab98337e…` | CSDL **NGUỒN** nguyên vẹn |
| **S6b** hết đĩa khi khôi phục | **0** | ok → ok | `9ed8acc6…` → `9ed8acc6…` | CSDL **ĐÍCH** không bị để lại nửa vời (20 bảng · 1.298.000 đ, nguyên) |
| **DC** đối chứng đường | **0** | ok → ok | `808bd09c…` → `808bd09c…` | 51 bảng · 34.336.000 đồng Y NGUYÊN |

Bảng đầy đủ **51 bảng × (số dòng, tổng tiền) × (trước, sau)** cho cả bốn kịch bản nằm ở
`trien_khai/g20-saoluu/ket_qua/bang_tung_bang_sau.md` (và `_truoc.md` cho lượt TRƯỚC).
Đường lành cũng có vế chứng minh phép so **LÀM ĐỎ ĐƯỢC**: ghi thêm dữ liệu sau mốc sao lưu ⇒
**8 lệch** ngay, ví dụ `tong_tien_toan_kho 34336000 -> 37333000`.

---

## 10. CÒN HỞ — NÓI THẲNG, KHÔNG TÔ HỒNG

| # | Mục | Vì sao chưa đóng | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **`S8`/`do2b` — `hub.db` CŨ còn sót trong khi kho đang chạy là PostgreSQL, và deployment CHƯA KHAI kho đang chạy.** Ba vế kia đã đóng. | Hệ **không tự biết** kho nào đang chạy, nên phải có KHAI BÁO. Chính sách khi chưa khai hiện là `"sqlite"` (giữ nguyên hành vi cũ). **ĐO ĐƯỢC cái giá của việc đổi nó:** `migrate.chay()` trên thư mục dữ liệu MỚI **có** gọi `sao_luu()` (`csdl.mo()` tạo `schema_version` rỗng ⇒ `MAX(phien_ban)=0` ⇒ chạy nâng cấp), và **8 bộ thử NGOÀI vùng được ghi của AG-02** gọi `migrate.chay()`: `thu_giao_dich` · `thu_han_muc_nguyen_tu` · `dong_thoi/do_dong_thoi` · `thu_qa_g18` · `thu_header_bao_mat` · `thu_qa_g19` · `thu_g17` · `thu_g17_baomat`. Đổi mặc định thành `"tu_choi"` là **làm đỏ cả 8 bộ đó**. | **QUYẾT ĐỊNH SẢN PHẨM của AG-00/AG-05**, đã báo (`msg_f12dea468ee2`): (1) chốt cờ `KHO_DANG_CHAY` nằm ở `app/cau_hinh.py` + `.env.example`, mặc định `'sqlite'`; (2) có đổi `CHINH_SACH_CHUA_KHAI` sang `"tu_choi"` không — nếu CÓ thì phải kèm sửa 8 bộ thử trên. **Đo được: đổi sang `"tu_choi"` ⇒ `S8` FAIL_CLOSED 1/1** (`B5`), tức mã đã sẵn sàng, chỉ còn quyết định. |
| 2 | **Sao lưu CSDL KHÔNG TỰ ĐỦ: khóa mã hoá credentials không đi kèm.** | `khoi_phuc()` báo thành công trong khi bản khôi phục không dùng được cho lời gọi hãng nào. Ranh giới giữa "khôi phục CSDL" và "khôi phục khóa" là **có thật**; bản vá cố ý **không** mở rộng phạm vi sang tệp khóa — mở rộng là một quyết định sản phẩm. | `app/sao_luu_khoa.py` + `trien_khai/sao_luu_ngoai/` đã có; cần **buộc** quy trình hai bước thành MỘT. |
| 3 | **`SIGKILL` giữa lúc sao lưu vẫn để lại tệp tạm `*.db.dang-ghi`.** | Không thể dọn sau `SIGKILL` — không còn tiến trình nào để dọn. Giảm nhẹ đo được: tên nó **không** kết thúc bằng `.db` và **không** có `.sha256`, nên `khoi_phuc()` đã vá **TỪ CHỐI** nó. | Không đóng được hoàn toàn. Có thể thêm bước dọn `*.dang-ghi` cũ lúc khởi động. |
| 4 | **Cửa sổ nhỏ giữa lúc xoá `-wal`/`-shm` và `os.replace`.** | Nguyên tử trên MỘT tệp thì được; trên BA tệp thì cần đổi cả thư mục. Bản vá **giảm** cửa sổ (bản mới đã ghi xong và đã kiểm TRƯỚC khi xoá WAL) và **bảo toàn** `-wal` bằng cách chép nó cạnh bản cất. | Chấp nhận được; ghi ra để người sau biết nó CÒN. |
| 5 | **Bộ thử AG-04 (`thu_g20_saoluu.py`) còn 1 ca đỏ.** | Ca `test_k4` **PIN** khoảng hở `do2b` — nó đỏ vì khoảng hở CÓ THẬT, không vì bản vá hỏng. 7/8 ca `ĐỘC HẠI ĐÃ BIẾT` đã xanh trở lại vì hành vi nay ĐÚNG. | Tự xanh khi mục 1 được quyết. **KHÔNG** xoá/nới ca này: nó là vế nhìn thấy thứ hai của khoảng hở. |
| 6 | **`app/cau_hinh.py` KHÔNG thuộc vùng được ghi của AG-02.** | Cờ `KHO_DANG_CHAY` cần một chỗ CHÍNH THỨC; bản vá đọc nó qua `getattr` nên **không cần** sửa tệp đó để chạy, nhưng deployment cần một chỗ khai. | AG-00/AG-05 (mục 1). |
| 7 | **Chốt `D-9` (`city`/`area`)** · **chuyển CSDL nghiệp vụ sang PostgreSQL (D-8)** · **E2E/tầng 3 · gọi API hãng kể cả sandbox · deploy/push/tunnel** | Lượt này **không** chạm ánh xạ `area`; D-8 **BỊ CẤM**; `V-G09-01` + `V-13906-05` CHƯA CẤP. | anh Thành / làn có quyền |

---

## 11. TỆP CỦA LƯỢT NÀY

| Tệp | Trạng thái | Vai |
|---|---|---|
| `app/migrate.py` | **SỬA — bản vá đã áp** (951 dòng) | Bốn nhóm chốt §7; `sao_luu()`/`khoi_phuc()` thay **tại chỗ**, chỉ còn một định nghĩa mỗi hàm |
| `trien_khai/g20-saoluu/migrate_nguyenban.py` | **mới** (625 dòng, md5 ghim) | Bản ĐÓNG BĂNG trước khi vá — để lượt "TRƯỚC" đo lại được |
| `trien_khai/g20-saoluu/ban_va.py` | **viết lại** | Bản vá khai thành **16 mảnh** + 3 mảnh cũ phải vắng + 4 phép tiêm + 1 biến thể chính sách; `xac_nhan()` TỪ CHỐI nếu thiếu |
| `trien_khai/g20-saoluu/fail_closed.py` | **sửa** | `S8` nay **bốn vế, đo riêng, không gộp**; giữ `chup_day_du` (phép chụp đầy đủ từng bảng) |
| `trien_khai/g20-saoluu/do_postgres.py` | **sửa** | Tách `do2a` (khai) / `do2b` (chưa khai); hình dạng kết quả **cố định** + bí danh khoá cũ để không phá `thu_g20_saoluu.py` |
| `trien_khai/g20-saoluu/kich_ban.py` | **sửa** | `sao_luu(dir, khai_kho=…)` — `None` nghĩa là **KHÔNG khai**, cố ý không lấy từ `os.environ` |
| `trien_khai/g20-saoluu/chay_do.py` | **mới** | Driver một lệnh: B0…B8, ghi mã thoát + số ca + số skip |
| `trien_khai/g20-saoluu/bang_tung_bang.py` | **mới** | Sinh bảng số dòng/tổng tiền TỪNG BẢNG từ JSON số đo |
| `app/thu/thu_g21_saoluu.py` | **sửa** (23 ca) | `c0` chốt "bản vá đã áp" · `c4` đo trên **tệp thật** · `c9` đo **cái giá của quyết định** · `a9` khẳng định `S8` còn **đúng một** lý do |
| `docs/G21_BACKUP_RESTORE.md` | **viết lại** | Tài liệu này |
| `docs/G20_BACKUP_RESTORE.md` | **sửa §1** | Bổ sung cảnh báo **màu xanh giả** + bảng ba mốc thay thế |
| `app/csdl.py` · `app/cau_hinh.py` | **KHÔNG sửa** | Tệp của AG-00 |

Bằng chứng thô: `trien_khai/g20-saoluu/ket_qua/` — `chay_do.json` · `chay_do.log` ·
`truoc.json` · `sau.json` · `tiem_d{1,2,3,4}.json` · `chinh_sach_tu_choi.json` ·
`bang_tung_bang_{truoc,sau}.md`.

---

## 12. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY, KHÔNG BẰNG LỜI

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng **kể cả sandbox** | Không một lời gọi mạng nào trong `fail_closed.py` · `ban_va.py` · `chay_do.py` · `bang_tung_bang.py`; mọi phép đo chỉ chạm thư mục TẠM | ✓ |
| 2 | Push / deploy / tunnel / mở cổng ra ngoài | Không một lệnh `git push`/`ssh`/tunnel. PostgreSQL: socket Unix, `listen_addresses=''`, **TỪ CHỐI cổng 5432** | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | Không đọc `.env`; CSDL và log nằm trong thư mục TẠM; cụm PG là cụm thử tự dựng | ✓ |
| 4 | Không đoán mã trạng thái chưa hãng xác minh (D-4) | Lượt này **không** chạm bảng ánh xạ trạng thái | ✓ |
| 5 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area` | ✓ |
| 6 | **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8) · **CẤM dùng `:5432`** | Cụm đo là cụm RIÊNG cổng **55.432**, socket Unix; vân tay `:5432` chụp TRƯỚC/SAU, `van_tay_5432_khong_doi = True`, vẫn thấy `vip_customs*` | ✓ |
| 7 | Không dùng Claude/mô hình khác · không tự bấm duyệt sandbox | Không một lời gọi mô hình nào; không thao tác duyệt nào | ✓ |
| 8 | Không xoá hàng loạt · không sửa ngoài phạm vi | `app/csdl.py` **không đổi**; `app/cau_hinh.py` **không đổi**; `app/migrate.py` sửa **theo uỷ quyền**; `docs/G20_BACKUP_RESTORE.md` sửa **§1 theo chỉ đạo trực tiếp**; mọi `chot_an_toan()` TỪ CHỐI vùng dữ liệu thật | ✓ |
| 9 | **Mọi khẳng định có LỆNH THẬT + MÃ THOÁT THẬT + SỐ CA + SỐ SKIP** | §2 — sinh từ `ket_qua/chay_do.json` | ✓ |
| 10 | **Mọi ca PHỦ ĐỊNH có ĐỐI CHỨNG ĐƯỜNG** · chứng minh ca thử ĐỎ ĐƯỢC | §4 có `DC` cho mọi lượt · §8 có **4 phép tiêm trên tệp thật**, và `test_c2` tiêm **từng nhánh riêng** kể cả ba nhánh mới của `S8` | ✓ |
| 11 | **Không tự bịa quyết định sản phẩm** (`dùng tuỳ nghi`) | Khoảng hở `do2b` được **BÁO CÁO** kèm số đo hai phương án, không tự chốt | ✓ |
