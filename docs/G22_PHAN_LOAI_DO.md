# G22 — PHÂN LOẠI 20 BỘ ĐỎ: BỘ ĐO NỀN HAY LỖI THẬT

**Làn:** X2 · **Ngày đo:** 18–19/10/2026 · **Nhánh:** `x2-phan-loai` · **HEAD:** `6949d8c`
**Phạm vi ghi:** chỉ `docs/G22_PHAN_LOAI_DO.md` (tệp này) + `app/thu/thu_g22_phanloai.py` (mới).
**Không sửa** bộ thử, mã sản phẩm, `.git`, DB thật. **Không** push/deploy/gọi hãng.

---

## 0. TÓM TẮT CHO NGƯỜI VỘI

| Nhãn | Nghĩa | Số bộ |
|---|---|---:|
| **(N)** | Bộ đo nền — đỏ vì khẳng định khoản nợ CÒN, chế độ gộp XANH | **0** |
| **(S)** | Stale — ghim hành vi/sự thật cũ; đã đo được đường sửa | **17** |
| **(L)** | Lỗi thật — bắt được lỗi sản phẩm | **2** |
| **(C)** | Chưa rõ — thiếu môi trường để đo vế quyết định | **1** |
| | **Tổng** | **20** |

**Ba kết luận, mỗi kết luận có số đo:**

1. **Giả thuyết AG-00 SAI ở phần "phần lớn là bộ đo nền".** Không bộ nào trong **17 bộ đề bài nêu
   tên** có công tắc `VIP_*_CHE_DO`; cơ chế "BỘ ĐO NỀN — HEAD != nền đóng băng" chỉ nằm ở
   `thu_qa_g20.py` / `thu_qa_g21.py` / `thu_qa_g22.py`, và **không bộ nào trong ba bộ đó** đỏ vì
   "nợ còn nguyên". Trong 20 bộ, chỉ `thu_qa_g22.py` có công tắc riêng — và cả hai chế độ đều đỏ
   vì **thiếu trình duyệt Playwright**, nên xếp (C), không phải (N).
2. **Nhưng phần KẾT LUẬN của giả thuyết đúng một nửa:** 17/20 bộ là **bộ đo chưa cập nhật theo
   trạng thái mới** — chỉ khác là trạng thái mới ấy là **cổng fail-closed `VIP_KHO_DANG_CHAY`**
   của G22, không phải một "chế độ gộp". Một dòng khai `VIP_KHO_DANG_CHAY=sqlite` làm **9 bộ
   xanh hoàn toàn** (tổng **286 ca**), và làm 2 bộ (#3, #20) hết lỗi dựng nền — chỉ còn ghim
   số/route.
3. **Có 2 LỖI THẬT, không được đóng bằng nhãn "nền":**
   * `thu_migrate_dong_thoi.py` — **race trong `migrate.sao_luu()`**: 8 tiến trình migrate đồng
     thời (sau khi đã khai kho) thì **6–7 tiến trình chết** (`FileNotFoundError … .dang-ghi` / `disk I/O error`) vì cả
     8 gọi `sao_luu()` TRƯỚC khoá `BEGIN IMMEDIATE` và dùng chung tên bản sao theo GIÂY. Race
     **không tất định**: 14/18 lượt chạy lại có khai kho vẫn đỏ; 4 lượt xanh khi lịch tiến trình
     không chồng đủ.
   * `thu_bien_driver.py` — `app/migrate.py` **nạp thẳng `sqlite3`** (dòng 26, từ commit
     `bf8696d`), vi phạm biên driver "chỉ `csdl.py` được nạp driver" đã ghim từ 15/10.

**Một dòng không được rút ra:** "20 bộ đỏ là nợ nền nên bỏ qua". 2 bộ trong đó bắt lỗi thật; 17 bộ
kia cũng phải **sửa thiết lập/ghim**, không phải hợp thức hoá bằng nhãn.

---

## 1. PHƯƠNG PHÁP — ĐO CÁI GÌ, VÀ VÌ SAO CÓ HAI LƯỢT

### 1.1 "Bộ đo nền" nghĩa là gì trong repo này

Trong `docs/QA_G22.md` và `app/thu/thu_qa_g19.py`, "BỘ ĐO NỀN" là bộ **tự bỏ qua ở mức mô-đun**
khi `HEAD` khác một **nền đóng băng**; nó đo trạng thái **trước khi gộp**. Bộ nghiệm thu bản ĐÃ
GỘP là bộ riêng, có công tắc `VIP_G20_CHE_DO` / `VIP_G21_CHE_DO` / `VIP_G22_CHE_DO`:

```python
CHE_DO = os.environ.get("VIP_G22_CHE_DO", "nen")      # app/thu/thu_qa_g22.py:136
```

Vì thế, muốn gọi một bộ là (N) theo đúng định nghĩa, phải chỉ ra **công tắc nền/gộp của chính nó**
và đo được **nền ĐỎ + gộp XANH**. Đây là phép thử AG-00 đề nghị, và tôi giữ nguyên tiêu chí ấy.

### 1.2 Hai lượt đo cho mỗi bộ

| Lượt | Lệnh | Dùng để |
|---|---|---|
| **Mặc định** | `python3 app/thu/<bộ>.py` | ghi exit · số ca · dòng `FAIL:`/`ERROR:` cụ thể |
| **Thay thế** | `VIP_KHO_DANG_CHAY=sqlite python3 app/thu/<bộ>.py` — hoặc `VIP_G22_CHE_DO=gop` nếu bộ có công tắc | kiểm giả thuyết "chỉ là bộ đo chưa cập nhật trạng thái mới" |

`VIP_KHO_DANG_CHAY=sqlite` **không phải** một chế độ nền/gộp. Nó là **một dòng khai thiết lập**
đã được `docs/G22_SAOLUU.md` §4 đo là đủ đưa 8 bộ thử ngoài vùng được ghi trở lại mức nền của
chính chúng:

> "Mọi bộ bị ảnh hưởng đều trở lại mức nền của chính nó bằng MỘT dòng khai
> (`VIP_KHO_DANG_CHAY=sqlite` …). Không phải bằng cách nới chốt, không phải bằng cách sửa ca."
> — `docs/G22_SAOLUU.md` §4

Vì 17 bộ đề bài nêu tên **không có** `VIP_*_CHE_DO`, lượt thay thế này là **phép thử trung thực
nhất** cho câu hỏi "đỏ vì sản phẩm hay vì bộ đo chưa cập nhật". Nó KHÔNG đủ để gán (N): (N) đòi
công tắc nền/gộp thật. Nó đủ để phân biệt **(S) với (L)**.

### 1.3 Môi trường và các phép chuẩn hoá

```sh
# Môi trường có GIT_CONFIG_COUNT=2 nhưng THIẾU GIT_CONFIG_KEY_* (N-G18-00):
# MỌI lệnh git thoát 128. Gỡ gia đình biến trước khi đo — bộ chạy chung cũng làm vậy.
unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_KEY_1 \
      GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
```

| Hạng mục | Giá trị |
|---|---|
| Python | 3.9.6 · macOS arm64 · SQLite 3.51.0 |
| HEAD | `6949d8c567320993d72bb8156dc226acf90bddfe` (`x2-phan-loai`) |
| Mạng | **không** — mọi HTTP chỉ loopback, không gọi hãng |
| CSDL | SQLite trong thư mục TẠM; **không** đụng `app/du-lieu`, không PostgreSQL |
| Playwright | **thiếu** `chromium_headless_shell-1194` (xem §8.2) |
| Số bộ chạy toàn cây | **70** (`thu_e2e.py` cố ý loại — cần máy chủ riêng) |

### 1.4 Lượt chạy toàn cây (để biết 20 bộ nằm ở đâu)

```sh
$ # mỗi bộ chạy tuần tự, ghi exit + `Ran N` + dòng FAIL/ERROR
# KẾT QUẢ: 70 bộ · 40 XANH · 30 ĐỎ · 485 ca nằm trong các bộ đỏ
```

> **Mốc đo:** lượt toàn cây chạy khi cây CHƯA có 2 tệp của dispatch này. Sau khi tạo 2 tệp,
> `thu_g22_chotcay.py` (#11) chuyển XANH — đã đo lại: `exit 0 · Ran 11 · OK`. Vì thế 30 đỏ là
> con số của **cây sạch**, không phải của cây sau khi lượt này ghi tệp.

Trong 30 bộ đỏ: **18 bộ có `Ran > 0`**, 12 bộ còn lại là bộ đo tự viết (không in `Ran`) hoặc
dừng trước unittest. 17 bộ đề bài nêu tên nằm trong nhóm `Ran > 0`; bộ thứ 18 là `thu_qa_g22.py`
(chính là bộ nền/gộp). 3 bộ bổ sung của bảng 20 được chọn vì mang bằng chứng khác loại:
`thu_bien_driver.py` (L), `thu_g22_gioihan.py` (kỳ vọng cổng C5), `thu_qa_g22.py` (C, môi trường).
9 bộ đỏ còn lại nằm ở **Phụ lục A** — không bỏ sót bộ nào.

> **Tên tệp lệch trong đề bài:** đề bài ghi `thu_g18_tich_hop.py(26)`, nhưng cây này **không có**
> tệp đó; bộ khớp đúng số **26 ca** là `thu_qa_g18_tich_hop.py` (đã đo). Tương tự
> `thu_qa_g19_tich_hop.py` là bản uỷ quyền 8 ca (chuyển nguyên văn mã thoát của bộ gốc).

---

## 2. BẢNG 20 BỘ — TỔNG QUAN

| # | Bộ | Mặc định | Chạy lại ở chế độ thay thế | Nhãn |
|---:|---|---|---|---|
| 1 | `thu_bao_mat.py` | exit **1** · **57** ca · 1 FAIL | `VIP_KHO_DANG_CHAY=sqlite` → exit **0** · 57 ca | **S** |
| 2 | `thu_g01_g02.py` | exit **1** · **21** ca · 2 FAIL | khai kho → exit **1** · 21 ca · 2 FAIL (đổi lý do) | **S** |
| 3 | `thu_g19_route.py` | exit **1** · **14** ca · 13 ERROR | khai kho → exit **1** · **49** ca · 2 FAIL | **S** |
| 4 | `thu_g19_tich_hop.py` | exit **1** · **8** ca · 0 FAIL (cổng ĐỎ) | khai kho → exit **0** · 8 ca | **S** |
| 5 | `thu_g20_baomat.py` | exit **1** · **28** ca · 2 FAIL | khai kho → exit **0** · 28 ca | **S** |
| 6 | `thu_g20_dahang.py` | exit **1** · **27** ca · 3 FAIL | khai kho → exit **1** · 27 ca · 3 FAIL | **S** |
| 7 | `thu_g20_saoluu.py` | exit **1** · **41** ca · 1 FAIL | khai kho → exit **1** · 41 ca · 1 FAIL | **S** |
| 8 | `thu_g21_bimat.py` | exit **1** · **33** ca · 6 FAIL | khai kho → exit **0** · 33 ca | **S** |
| 9 | `thu_g21_saoluu.py` | exit **1** · **23** ca · 2 FAIL | khai kho → exit **1** · 23 ca · 2 FAIL | **S** |
| 10 | `thu_g22_bimat.py` | exit **1** · **23** ca · 6 FAIL | khai kho → exit **0** · 23 ca | **S** |
| 11 | `thu_g22_chotcay.py` | exit **1** · **11** ca · 1 FAIL (cây sạch) | khai kho → exit **1** · 11 ca · 1 FAIL; **trên cây có 2 tệp mới → exit 0 · Ran 11 · OK** | **S** |
| 12 | `thu_migrate_dong_thoi.py` | exit **1** · **8** ca · 2 FAIL/ERROR | khai kho → exit **1** · 8 ca · **1 FAIL (race)** | **L** |
| 13 | `thu_qa_g17.py` | exit **1** · **56** ca · 25 FAIL/ERROR | khai kho → exit **0** · 56 ca | **S** |
| 14 | `thu_qa_g18_tich_hop.py` | exit **1** · **26** ca · 3 FAIL | khai kho → exit **0** · 26 ca | **S** |
| 15 | `thu_qa_g18.py` | exit **1** · **47** ca · 20 FAIL/ERROR | khai kho → exit **0** · 47 ca | **S** |
| 16 | `thu_qa_g19_tich_hop.py` | exit **1** · **8** ca · 0 FAIL (cổng ĐỎ) | khai kho → exit **0** · 8 ca | **S** |
| 17 | `thu_qa_soat.py` | exit **1** · **30** ca · 1 FAIL | khai kho → exit **1** · 30 ca · 1 FAIL | **S** |
| 18 | `thu_qa_g22.py` | exit **1** · **24** ca · 2 FAIL | `VIP_G22_CHE_DO=gop` → exit **1** · 24 ca · 2 FAIL | **C** |
| 19 | `thu_bien_driver.py` | exit **1** · **0** ca (dừng ở a1) | khai kho → exit **1** · 0 ca | **L** |
| 20 | `thu_g22_gioihan.py` | exit **1** · **32** mục · ĐẠT 25 · HỎNG 5 | khai kho → ĐẠT 27 · **HỎNG 3** | **S** |

> **Đọc số ca cho đúng:** với bộ chạy được unittest, `Ran N` là số ca THẬT SỰ chạy. Nó **phụ
> thuộc môi trường**: `thu_g19_route.py` chỉ chạy **14** ca khi thiếu khai kho (13 ERROR) và **49**
> ca khi khai kho. Vì thế bảng ghi cả hai. Các con số trong đề bài — `(57)`, `(21)`, `(14)`,
> `(8)`… — khớp lượt MẶC ĐỊNH, đúng như đã đo.

---

## 3. BẰNG CHỨNG TỪNG BỘ — DÒNG FAIL/ERROR CỤ THỂ

### 3.1 Nhóm A — 9 bộ đỏ HOÀN TOÀN vì `migrate` fail-closed (thiếu khai kho)

(#3 `thu_g19_route.py` và #20 `thu_g22_gioihan.py` cũng có lỗi này ở lượt mặc định, nhưng sau
khi khai kho vẫn còn ghim số nên được xếp vào nhóm C/D bên dưới.)

**Gốc chung (một dòng):** `app/migrate.py` từ G22 gọi `_kiem_kho_truoc_khi_sao_luu()` trước khi
sao lưu; `cau_hinh.KHO_DANG_CHAY` mặc định `None` ⇒ **TỪ CHỐI**:

```
[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này
          có chứa dữ liệu đang phục vụ hay không (chưa có nguồn nào khai).
```

Đây là **thay đổi CÓ CHỦ ĐÍCH** của G22 (`docs/G22_SAOLUU.md` §3, `docs/G22_CAUHINH.md`): không
có mặc định, không đoán từ mtime/kích thước/tên tệp. Bộ thử nào gọi `migrate.chay()` mà chưa khai
kho đều đỏ ở **bước dựng nền**, trước khi đo thứ nó muốn đo.

| # | Bộ | Exit · ca | Dòng FAIL/ERROR cụ thể | Chạy lại `VIP_KHO_DANG_CHAY=sqlite` |
|---:|---|---|---|---|
| 1 | `thu_bao_mat.py` | 1 · 57 | `FAIL: test_e1_migrate_v4_dua_moi_secret_sang_v3` → `AssertionError: 1 != 0 : [migrate] Phiên bản hiện tại: 3 → đích: 10` + `TỪ CHỐI: CHƯA KHAI kho đang chạy` | **exit 0 · 57 ca · 0 FAIL** |
| 4 | `thu_g19_tich_hop.py` | 1 · 8 | `EXIT_BO_DO=1` · `PHÁN QUYẾT CỔNG: ĐỎ — runner HỎNG: mã thoát 1`; log runner: `RuntimeError: migrate.py hỏng (mã 1)` | **exit 0 · 8 ca** |
| 5 | `thu_g20_baomat.py` | 1 · 28 | `FAIL: test_b1_hai_bo_thu_cu_deu_xanh…` → `1 != 0 : app/thu/thu_qa_g17.py::A_Nen ĐỎ` · `ERROR: test_a6_khong_co_ket_noi_ra_ngoai` | **exit 0 · 28 ca** |
| 8 | `thu_g21_bimat.py` | 1 · 33 | `FAIL: test_e1/e2/e3_bi_mat_trong_{THÂN,QUERY,ĐƯỜNG DẪN}…` → `máy chủ thật không mở cổng … [hub] DỪNG: CSDL ở schema v0, mã nguồn cần v10`; kéo theo `test_g2` (E2,E3) và `test_z1` (nhóm E) | **exit 0 · 33 ca** |
| 10 | `thu_g22_bimat.py` | 1 · 23 | `FAIL: test_a2_D4… / test_a3_D5…` → `máy chủ thật không mở cổng 56752 … CSDL ở schema v0`; kéo theo `test_b2`, `test_b4` | **exit 0 · 23 ca** |
| 13 | `thu_qa_g17.py` | 1 · 56 | `ERROR: test_a6_khong_co_ket_noi_ra_ngoai` → `File "app/thu/thu_qa_g17.py", line 396, in moi_truong / migrate.chay(im_lang=True) / line 886, in chay / ban_sao = sao_luu() / line 371 … _kiem_kho_truoc_khi_sao_luu()`; 24 lỗi còn lại (`b0…b9`, `c1…c8`, `d1…d7`, `f7`) cùng gốc | **exit 0 · 56 ca** |
| 14 | `thu_qa_g18_tich_hop.py` | 1 · 26 | `FAIL: test_c3_http_mot_tien_trinh_bang_goi_thang_ham` → `máy chủ cổng 59996 không lên được`; `test_c4` → `cổng 60345 không lên được`; `test_c5` → `12 != None` | **exit 0 · 26 ca** |
| 15 | `thu_qa_g18.py` | 1 · 47 | `ERROR: test_a6_khong_co_luot_ket_noi_ra_ngoai_loopback` → `moi_truong() / migrate.chay(im_lang=True) / sao_luu() / _kiem_kho_truoc_khi_sao_luu()`; 19 lỗi còn lại (`e2…e9`, `f1…f3`, `b1/c2/d1`, `j3…j7`) cùng gốc | **exit 0 · 47 ca** |
| 16 | `thu_qa_g19_tich_hop.py` | 1 · 8 | `mã thoát bộ gốc = 1` · `PHÁN QUYẾT CỔNG: ĐỎ — runner HỎNG` (bộ gốc `thu_g19_tich_hop.py` chết ở `migrate.py hỏng`) | **exit 0 · 8 ca** |

### 3.2 Nhóm B — 2 bộ đỏ vì API/tham số mới của G22

| # | Bộ | Exit · ca | Dòng FAIL/ERROR cụ thể | Chạy lại |
|---:|---|---|---|---|
| 2 | `thu_g01_g02.py` | 1 · 21 | `ERROR: test_010_doi_tenant_id_trong_request_khong_vuot_quyen` → `KeyError: 'don'` vì `GET /api/v2/don?tenant_id=…` bị lớp truy vấn **TỪ CHỐI 400** (không còn bỏ qua tham số lạ); `FAIL: test_014_migration_bao_toan_du_lieu` → `1 != 0 : [migrate] TỪ CHỐI: CHƯA KHAI kho` (khai kho xong đổi thành `TỪ CHỐI: TỤT SCHEMA — bản sao lưu v0, CSDL v10`) | exit **1** · 21 ca · 2 FAIL |
| 17 | `thu_qa_soat.py` | 1 · 30 | `FAIL: test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh` → `AssertionError: 400 != 200` (dòng cuối đòi 200 cho `GET /api/v2/don?tenant_id=…`) | exit **1** · 30 ca · 1 FAIL |

### 3.3 Nhóm C — 4 bộ ghim sự thật số học cũ

| # | Bộ | Exit · ca | Dòng FAIL/ERROR cụ thể | Vì sao là ghim cũ |
|---:|---|---|---|---|
| 3 | `thu_g19_route.py` | 1 · 14 | 13 `ERROR` khi chưa khai kho (xem A); khai kho → `FAIL: test_a6_bo_trich_ba_phu_31_muc_con_thieu_cua_AG01` → `31 != 32` và `FAIL: test_d1_con_so_phu` → `103 != 104` | G22 thêm route `/api/v2/don/loc-mo-ta`; ghim 103 route / khoảng trống 31 là ảnh trước G22 |
| 6 | `thu_g20_dahang.py` | 1 · 27 | `test_a2` → `{'CHUNG': 38, 'DAC_THU_JT': 7} != {'CHUNG': 30, 'DAC_THU_JT': 7}` · `test_a6` → `831 not found in [108, 115, 116, 1035]` · `test_a7` → `[285, 311, 344, 946] != [285, 311, 343, 742]` | Ghim số hàm CHUNG và **số dòng** của `http_jt.py`; mã đã dài ra |
| 7 | `thu_g20_saoluu.py` | 1 · 41 | `FAIL: test_a5_ban_sao_luu_co_byte_va_mo_duoc` → `AssertionError: 10 != 9 : phiên bản schema sau khôi phục khác 9` | `PHIEN_BAN_SCHEMA` nay là **10**; ca vẫn ghim 9 |
| 9 | `thu_g21_saoluu.py` | 1 · 23 | `FAIL: test_a5_khoi_phuc_ban_schema_thap_hon` → `'(c) sau khi tụt schema, hệ VẪN CHẠY được (rc=0) trên schema cũ — không một lời cảnh báo' != []`; `test_c4` cùng lỗi | Bộ đo `trien_khai/g20-saoluu/fail_closed.py:329` ghim `phien_ban_sau_khoi_phuc != 9`; schema đích 10 ⇒ điều kiện luôn đúng **dù sản phẩm đã TỪ CHỐI khôi phục** |

### 3.4 Nhóm D — 2 bộ có tiền điều kiện phép đo cũ

| # | Bộ | Exit · ca | Dòng FAIL/ERROR cụ thể | Vì sao |
|---:|---|---|---|---|
| 11 | `thu_g22_chotcay.py` | 1 · 11 | `FAIL: test_d2_moi_ban_sao_xanh_tren_cay_co_tep_moi_cua_lan_khac` → `AssertionError: 0 not greater than or equal to 1 : cây SẠCH TRƠN ⇒ phép đo rỗng` | Ca đòi `git status` có ≥1 dòng của làn KHÁC; cây nghiệm thu SẠCH nên phép đo rỗng — đúng như chính nó cảnh báo. Lượt đo chạy **trước** khi tạo 2 tệp của dispatch này; **đã đo lại trên cây có 2 dòng mới: exit 0 · Ran 11 · OK** — đó chính là bằng chứng nó đo **CÂY**, không đo sản phẩm |
| 20 | `thu_g22_gioihan.py` | 1 · 32 mục | `✗ B3.a_bo_goc_tra_ma_khac_0` / `✗ B3.b_bo_goc_khong_ton_tai` / `✗ B3.c_suite_rong_0_ca` → `C5 … 1/2 · phán quyết=DONG`; kèm `✗ B5.thu_g19_tich_hop` + `✗ B5.thu_qa_g19_tich_hop` khi chưa khai kho | B3 giả định C5 chỉ có **1** ứng viên; nay `thu_qa_g19*.py` khớp **2** tệp và cả hai chạy thật, nên tiêm lỗi vào 1 ứng viên không còn làm C5 đỏ |

### 3.5 Nhóm E — 1 bộ có công tắc nền/gộp nhưng KHÔNG đo được vế quyết định

| # | Bộ | Exit · ca | Dòng FAIL/ERROR cụ thể | Hai chế độ |
|---:|---|---|---|---|
| 18 | `thu_qa_g22.py` | 1 · 24 | `FAIL: test_b2_chay_e2e_toan_bo_that` → `chay.sh rc=1 (3 đạt, 10 hỏng, 52 không chạy)`; `FAIL: test_b3_e2e_tam_ca_ban_phim_chay_that` → `0 ca ĐẠT: Executable doesn't exist at … chromium_headless_shell-1194/…/headless_shell` | mặc định: exit 1 · 24 ca · 2 FAIL · `VIP_G22_CHE_DO=gop`: **cùng 2 FAIL** |

Đây là **bộ duy nhất trong 20 có công tắc nền/gộp riêng**. Nhưng cả hai chế độ đỏ vì **cùng một
lý do môi trường**: bản `playwright-core` trong repo đòi `chromium_headless_shell-1194`, máy này
chỉ có `1148`/`1243`. Vế "gộp phải XANH" **không đo được** ⇒ nhãn (C). Không được gán (N) chỉ vì
nó *có* công tắc.

### 3.6 Nhóm F — 2 LỖI THẬT

#### F.1 `thu_migrate_dong_thoi.py` — race trong `sao_luu()` (L)

| Lượt | Exit · ca | Dòng FAIL |
|---|---|---|
| Mặc định | 1 · 8 | `FAIL: test_a1_dung_mot_tien_trinh_nang_cap` → `8 != 0 : tiến trình hỏng: TỪ CHỐI: CHƯA KHAI kho đang chạy` (cả 8 tiến trình); `ERROR: test_a2_csdl_sau_cung_dung_mot_ban` cùng gốc |
| Khai kho | 1 · 8 | `FAIL: test_a1…` → `6–7 != 0 : tiến trình hỏng: FileNotFoundError … hub-truoc-migrate-20261019-000426.db.dang-ghi` / `sqlite3.OperationalError: disk I/O error` |

Khai kho chỉ bỏ được **lỗi đầu tiên**. Lỗi thật còn lại là một **race không tất định**: trong 18
lượt chạy lại có khai kho, **14 lượt vẫn đỏ** (4 lượt xanh khi 8 tiến trình không chồng đủ lên
nhau). Lượt dựng tay 8 tiến trình cùng vạch xuất phát cho traceback đầy đủ và **6–7/8 tiến trình
chết**:

```
File "app/migrate.py", line 886, in chay
    ban_sao = sao_luu()
File "app/migrate.py", line 387, in sao_luu
    nguon.backup(ban)
sqlite3.OperationalError: disk I/O error

File "app/migrate.py", line 391, in sao_luu
    with open(tam, "rb+") as f:
FileNotFoundError: [Errno 2] No such file or directory:
    '…/sao-luu/hub-truoc-migrate-20261019-000426.db.dang-ghi'
```

**Cơ chế (đọc mã, không đoán):**

1. `chay()` đọc `pb` NGOÀI khoá rồi gọi `sao_luu()` **trước** `BEGIN IMMEDIATE` (`migrate.py:886`).
   Cả 8 tiến trình cùng thấy `pb = 0` và cùng vào `sao_luu()`.
2. `_duong_chua_dung()` đặt tên bản sao theo **GIÂY** (`…-20261019-000426`). Cả 8 tiến trình tính
   ra **CÙNG một tên** `dich` ⇒ **CÙNG một tệp tạm** `dich + ".dang-ghi"`.
3. Một tiến trình `os.replace(tam, dich)` thành công; 7 tiến trình còn lại đang `open(tam, "rb+")`
   hoặc `nguon.backup(ban)` trên tệp vừa biến mất ⇒ `FileNotFoundError` / `disk I/O error`.

**Đề xuất (không sửa ở lượt này):** chuyển `sao_luu()` vào **TRONG** khoá `BEGIN IMMEDIATE` (chỉ
một tiến trình sao lưu — đúng việc mà khoá được khai là để làm), hoặc đặt tên duy nhất bằng
`pid`/`uuid` + `O_EXCL` và không dùng chung `.dang-ghi`. Đây là **lỗi sản phẩm**, không phải bộ đo
cũ: bộ thử đo đúng bất biến "8 tiến trình migrate → 1 nâng cấp, 7 nhường, **0 lỗi**".

#### F.2 `thu_bien_driver.py` — biên driver bị vi phạm (L)

| Lượt | Exit · ca | Dòng FAIL |
|---|---|---|
| Mặc định | 1 · 0 | `AssertionError: tệp nạp trực tiếp sqlite3 (phải dùng csdl.Row/LoiToanVen/ket_noi): migrate.py dòng [26]` |
| Khai kho | 1 · 0 | y nguyên |

Bộ thử canh bất biến đã ghim từ 15/10: **chỉ `csdl.py` được nạp `sqlite3`** (`DUOC_NAP =
{"csdl.py"}`). `git blame` chỉ ra dòng 26 được thêm bởi commit **`bf8696d`** — chính bản vá G22
"S8/do2b" (`AG-02 (G22) DONG S8/do2b: 1/10 -> 10/10 FAIL_CLOSED`). `migrate.py` dùng driver ở 4
chỗ: `connect` chỉ-đọc, `OperationalError`, `DatabaseError`, `complete_statement`.

**Đề xuất (không sửa ở lượt này):** đưa 4 chỗ dùng driver vào `csdl.py` (thêm hàm mở chỉ-đọc,
alias lỗi, wrapper `complete_statement`), hoặc khai ngoại lệ **có lý do** và cập nhật danh sách
CHO PHÉP của bộ thử. Đây là vi phạm **thật** (mức kiến trúc), không phải bộ đo cũ.

---

## 4. TỔNG HỢP N/S/L/C

```text
N = 0   (không bộ nào có công tắc nền/gộp + nền đỏ + gộp xanh)
S = 17  (#1,2,3,4,5,6,7,8,9,10,11,13,14,15,16,17,20)
L = 2   (#12 thu_migrate_dong_thoi.py · #19 thu_bien_driver.py)
C = 1   (#18 thu_qa_g22.py — thiếu chromium-1194)
TỔNG = 20
```

Phân bố nguyên nhân của 17 bộ (S):

| Nguyên nhân (mỗi bộ xếp đúng MỘT dòng) | Số bộ | Gồm |
|---|---:|---|
| Thiếu khai `VIP_KHO_DANG_CHAY` — đơn thuần | **9** | #1,4,5,8,10,13,14,15,16 |
| Thiếu khai kho + còn ghim số/route | 2 | #3, #20 |
| Ghim schema = 9 (mã nguồn nay là 10) | 2 | #7, #9 |
| Ghim số hàm / số dòng | 1 | #6 |
| Kỳ vọng API cũ (200 thay vì 400; rollback schema cũ) | 2 | #2, #17 |
| Tiền điều kiện "cây bẩn" | 1 | #11 |
| **Tổng** | **17** | |

**Đường sửa đã đo cho nhóm lớn nhất:** thêm **một dòng** vào môi trường chạy bộ thử
(`VIP_KHO_DANG_CHAY=sqlite`, cùng khuyến nghị đã có ở `docs/G22_SAOLUU.md` §4/§7) làm **9 bộ
xanh hoàn toàn**, tổng **286 ca**:

```text
57 + 8 + 28 + 33 + 23 + 56 + 26 + 47 + 8 = 286 ca (9 bộ: #1,4,5,8,10,13,14,15,16)
#3 và #20: hết ERROR dựng nền, chỉ còn ghim số/route (2 FAIL và 3 HỎNG).
```

Sau khi khai kho, 11 bộ còn đỏ trong bảng 20 gồm: **8 bộ (S) còn ghim cũ**, **2 bộ (L)** và
**1 bộ (C)**.

---

## 5. KIỂM CHỨNG GIẢ THUYẾT AG-00

**Giả thuyết nguyên văn (AG-00):** *"Phần lớn các bộ đỏ là BỘ ĐO NỀN — chúng khẳng định 'khoản nợ
X còn nguyên'. Nợ đã đóng trong wave G22 ⇒ chạy ở chế độ nền thì ĐỎ là ĐÚNG, còn chạy ở
`..._CHE_DO=gop` thì phải XANH."*

| Vế của giả thuyết | Kết quả | Bằng chứng |
|---|---|---|
| "Phần lớn là bộ đo nền" | **SAI** | 0/20 có `VIP_*_CHE_DO` riêng cho chính nó, trừ `thu_qa_g22.py` (và nó là C). 17 bộ đề bài nêu tên: **0** công tắc. `test_02` của `thu_g22_phanloai.py` quét tệp và khẳng định điều này. |
| "Khẳng định khoản nợ X còn nguyên" | **SAI** | Không bộ nào assert một khoản nợ. 9 bộ chết ở **bước dựng nền** (migrate từ chối) trước khi đo bất cứ điều gì; 2 bộ vừa dựng nền vừa ghim số (#3, #20); 6 bộ còn lại ghim số/route/schema/tiền điều kiện (#2, #6, #7, #9, #11, #17). |
| "Chạy `..._CHE_DO=gop` thì phải XANH" | **KHÔNG ĐO ĐƯỢC cho 19/20** | 19 bộ không có chế độ gộp. Bộ duy nhất có (`thu_qa_g22.py`) đỏ ở **cả hai** chế độ vì thiếu `chromium-1194` ⇒ (C). |
| "Không phải lỗi sản phẩm, mà là bộ đo chưa cập nhật" | **ĐÚNG một nửa** | 17/20 là bộ đo chưa cập nhật — nhưng theo **cổng fail-closed `KHO_DANG_CHAY`** của G22, không theo "chế độ gộp". 2/20 là **lỗi sản phẩm thật** (race `sao_luu`, biên driver). |

**Điều đúng của giả thuyết:** các bộ đỏ phần lớn KHÔNG phải lỗi sản phẩm mới. **Điều sai nguy
hiểm:** gọi chúng là "bộ đo nền" sẽ dẫn tới kết luận "đỏ là đúng, không cần sửa". Sai, vì:

* 9 bộ sẽ xanh HOÀN TOÀN bằng **một dòng thiết lập** (286 ca) và 2 bộ nữa hết lỗi dựng nền —
  cái giá của việc không thêm dòng đó là **286 ca đang không được đo** trên mỗi lượt hồi quy;
* 2 bộ đang bắt **lỗi thật**; nếu bị gộp vào "nợ nền" thì lỗi race và lỗi biên driver sẽ bị bỏ qua.

**Vị trí thật của cơ chế nền/gộp:** `thu_qa_g20.py`, `thu_qa_g21.py`, `thu_qa_g22.py`. Ở HEAD này
`thu_qa_g20.py` và `thu_qa_g21.py` **XANH** khi chạy đúng chế độ của chúng (đo được: G20 `Ran 21 ·
OK (skipped=3)` · G21 `Ran 24 · OK (skipped=3)`); `thu_qa_g22.py` chỉ vướng E2E. Không có "nợ
còn nguyên" nào trong ba bộ này ở HEAD.

---

## 6. TỰ KIỂM PHÉP PHÂN LOẠI — `app/thu/thu_g22_phanloai.py`

Bảng trên có thể đúng vì tôi dán nhãn khéo. Để chứng minh nó **có răng**, script làm một **đối
chứng tiêm lỗi thật** trên **bản sao**:

```sh
python3 app/thu/thu_g22_phanloai.py -v
# KẾT QUẢ ĐO ĐƯỢC (lượt cuối):
#   Ran 6 tests in ~0,4 giây
#   OK
#   [S] bản sạch: exit=1 · 0 ca · TỪ CHỐI: CHƯA KHAI kho đang chạy
#       khai kho : exit=0 · 5 ca (đối chứng đường) ⇒ (S): thiếu THIẾT LẬP, không phải lỗi sản phẩm
#   [L] bản tiêm: exit=1 · 5 ca · tệp sản phẩm đổi: ['app/billing.py']
#       đối chứng sạch (cùng thiết lập): exit=0 ⇒ lỗi do SẢN PHẨM, không do thiết lập ⇒ (L)
```

**Sáu ca tự kiểm:**

| Ca | Chứng minh |
|---|---|
| `test_01` | 20 nhãn trong bảng **tự nhất quán** với `chan_doan()` (không có nhãn dán tay lệch luật) |
| `test_02` | 17 bộ đề bài **không** có `VIP_*_CHE_DO`; chỉ `thu_qa_g22.py` có công tắc riêng; ba bộ QA G20/G21/G22 mới là nơi có cơ chế nền/gộp |
| `test_03` | Bản sao **sạch** + không khai kho → **ĐỎ đúng lý do**; khai kho → **XANH 5/5 ca**; bản sao **không bị lượt chạy sửa** ⇒ phép phân loại xếp **(S)** |
| `test_04` | Tiêm lỗi thật vào `billing._cong_bo_dem_co_tran` của bản sao (bỏ chốt trần) ⇒ bộ thử **ĐỎ**; đối chứng sạch cùng thiết lập **XANH**; băm cây chứng minh **chỉ `app/billing.py` đổi** ⇒ xếp **(L)** |
| `test_05` | Luật **(N)** và **(C)** cũng có đối chứng — nếu không, "luật" chỉ là hai chữ |
| `test_06` | Bảng tổng hợp đúng `N=0 · S=17 · L=2 · C=1 · tổng=20` |

**Phép tiêm chỉ chạm bản sao trong `tempfile.mkdtemp()`; cây thật được băm và đối chiếu.** Đây là
lý do tôi dám nói phép phân loại không phải "mọi thứ đỏ đều là bộ đo cũ".

---

## 7. PHỤ LỤC A — 9 BỘ ĐỎ CÒN LẠI (ngoài bảng 20)

Tất cả đều **cùng nhóm A** (thiếu khai kho) trừ ghi chú; **không bộ nào là lỗi thật mới**:

| Bộ | Mặc định | Sau `VIP_KHO_DANG_CHAY=sqlite` | Ghi chú |
|---|---|---|---|
| `thu_g17_baomat.py` | exit 1 · 0 ca (chết ở e4) | exit 1 · **31 ca · 1 FAIL** | Sau khai kho còn `test_v1…` thiếu route `GET /api/v2/don/loc-mo-ta (server.py:945)` trong bảng khai — **S**, cùng nhóm #3 |
| `thu_g18_maysrv.py` | exit 1 · 0 ca (`setUpModule` migrate) | **exit 0 · 17 ca** | S |
| `thu_g18_multiprocess.py` | exit 1 · 0 ca (tự viết, dừng ở dựng nền) | **exit 0** | S |
| `thu_g19_gioihan.py` | exit 1 · 0 ca | **exit 0** (28,3 giây) | S |
| `thu_g21_gioihan.py` | exit 1 · 0 ca | **exit 0** (60,0 giây) | S |
| `thu_giao_dich.py` | exit 1 · 0 ca | **exit 0 · 17 ca** | S |
| `thu_han_muc_nguyen_tu.py` | exit 1 · 0 ca | **exit 0 · 5 ca** | S |
| `thu_header_bao_mat.py` | exit 1 · 0 ca | **exit 0 · 8 ca** | S |
| `thu_truy_van.py` | exit 1 · 0 ca (5 ERROR `setUpClass`) | **exit 0 · 40 ca** | S |

`thu_g22_e2e.py` (exit 2) **không tính**: nó cần máy chủ + Playwright, đã cố ý loại khỏi
`chay_tat_ca.sh`.

**Tổng toàn cây:** 70 bộ · 40 xanh · 30 đỏ. Sau khi khai kho, số đỏ giảm còn **12 bộ** = 11 bộ
đo lại được + `thu_qa_g22.py` (E2E, không đo lại trong lượt khai kho). Trong 12 bộ: **9 bộ (S)**
còn ghim số/schema/route/cây bẩn, **2 bộ (L)**, **1 bộ (C)** — tất cả có đường sửa đã đo.

---

## 8. PHỤ LỤC B — GIỚI HẠN PHÉP ĐO (nói thẳng)

### 8.1 Môi trường git dị dạng (N-G18-00)

Phiên này có `GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0/1` và có
`GIT_CONFIG_VALUE_0/1`. Nếu giữ nguyên, **mọi** lệnh git thoát 128. Tôi gỡ gia đình biến trước
mọi lượt đo, đúng như `chay_tat_ca.sh` đã tự vá. Không có dòng mã nào bị sửa vì việc này. Ghi ở
đây để lượt sau đối chiếu được: **cùng cây, cùng HEAD, khác môi trường ⇒ khác số đo** (xem
N-G18-00).

### 8.2 Playwright thiếu `chromium-1194`

`node_modules/playwright-core/.local-browsers/` **không tồn tại**; cache máy chỉ có
`chromium_headless_shell-1148/1243`. Vì thế:

* `thu_qa_g22.py` → **C**: hai FAIL E2E ở **cả hai** chế độ;
* `thu_g22_e2e.py` → exit 2, không đo được;
* toàn bộ vế "giao diện/bàn phím" của G22 **CHƯA ĐO**, không được tính là ĐẠT.

### 8.3 Một lượt đo cho mỗi bộ

Tôi chạy mỗi bộ **một lượt mặc định + một lượt thay thế**. Riêng `thu_migrate_dong_thoi.py` chạy
**18 lượt có khai kho + 1 lượt dựng tay 8 tiến trình**: 14/18 lượt đỏ (race phụ thuộc lịch tiến
trình), lượt dựng tay cho traceback đầy đủ. `thu_bao_mat.py` chạy 2 lượt. Các bộ khác có thể còn
đỏ **không ổn định** (temp-dir) — chưa đo được xác suất.

### 8.4 Không PostgreSQL (D-8)

Mọi phép đo trên SQLite trong thư mục tạm. Không có cụm PostgreSQL, không `pg_dump` thật. Các ca
liên quan PostgreSQL trong `thu_g20_saoluu`/`thu_g21_saoluu`/`thu_qa_g18` vẫn **CHƯA ĐO**, đúng
giới hạn đã ghi trong `docs/G22_SAOLUU.md`.

### 8.5 Chọn 3 bộ bổ sung

17 bộ đầu là danh sách đề bài. 3 bộ còn lại tôi chọn theo **loại bằng chứng**, không theo thứ
tự: `thu_bien_driver.py` (L — lỗi kiến trúc), `thu_qa_g22.py` (C — bộ nền/gộp duy nhất), và
`thu_g22_gioihan.py` (S — kỳ vọng cổng C5). **Không bỏ sót bộ đỏ nào**: 9 bộ còn lại ở Phụ lục A.

---

## 9. VIỆC CÒN LẠI — ĐỀ XUẤT, KHÔNG SỬA Ở LƯỢT NÀY

| # | Việc | Vì sao | Đề xuất cụ thể |
|---:|---|---|---|
| 1 | Thêm một dòng khai kho cho môi trường chạy bộ thử | 11 bộ có lỗi thiếu khai; trong đó 9 bộ / 286 ca đang không được đo | `export VIP_KHO_DANG_CHAY=sqlite` trong `app/thu/chay_tat_ca.sh` (chỉ cho tiến trình thử, **không** cho production) |
| 2 | **Sửa race `sao_luu()`** | 6–7/8 tiến trình migrate đồng thời chết (14/18 lượt) | Chuyển `sao_luu()` vào trong `BEGIN IMMEDIATE`; hoặc tên duy nhất `pid`/`uuid` + `O_EXCL` |
| 3 | **Sửa biên driver** | `migrate.py` nạp `sqlite3` từ `bf8696d` | Đưa 4 chỗ dùng driver vào `csdl.py`; hoặc khai ngoại lệ có lý do + cập nhật danh sách CHO PHÉP |
| 4 | Ghim schema 9 → `PHIEN_BAN_SCHEMA` | #7, #9 | `thu_g20_saoluu.py:110`, `trien_khai/g20-saoluu/fail_closed.py:329` |
| 5 | Cập nhật ghim route/số hàm/số dòng | #3, #6 | 103→104, 31→32; bỏ ghim literal số dòng, đối chiếu với bảng đọc từ tệp |
| 6 | Nhận 400 là ĐẠT (hoặc kiểm bằng body) | #2, #17 | `thu_g01_g02.py:270`, `thu_qa_soat.py:587` |
| 7 | Rollback schema cũ kèm cờ đã biết | #2 | `test_014` gọi `--rollback … --toi-da-biet-chua-kiem-duoc` và khẳng định mặc định TỪ CHỐI là ĐẠT |
| 8 | Cập nhật bảng khai route | Phụ lục A | Thêm `GET /api/v2/don/loc-mo-ta` vào bảng của `thu_g17_baomat.py` |
| 9 | Bỏ tiền điều kiện "cây bẩn" | #11 | Tự tạo tệp mới trong **bản sao** của phép đo (như `test_d3` đã làm) |
| 10 | Sửa kỳ vọng C5 hai ứng viên | #20 | B3 vô hiệu hoá **cả hai** `thu_qa_g19*.py`, hoặc chạy trên bản sao chỉ còn 1 ứng viên |
| 11 | Cài `chromium-1194` (hoặc ghim phiên bản có sẵn) | #18 + E2E | Chạy lại `VIP_G22_CHE_DO=gop`; nếu vẫn đỏ mới kết luận N/S/L cho `thu_qa_g22` |
| 12 | Chạy lại toàn cây sau khi sửa | Xác nhận | Kỳ vọng: 0 đỏ ngoài `thu_qa_g22`/E2E; ghi lại số ca từng bộ |

**Không được làm:** nới cổng fail-closed `KHO_DANG_CHAY` để bộ thử xanh. Chốt ấy đóng khoảng hở
P-G15-02 (`docs/G22_SAOLUU.md` §3) — bộ thử phải khai, không phải cổng phải nới. Tương tự, không
nới `TỤT SCHEMA`, không bỏ 400 của lớp truy vấn.

---

## 10. TỆP ĐÃ TẠO / KHÔNG SỬA

| Tệp | Trạng thái |
|---|---|
| `docs/G22_PHAN_LOAI_DO.md` | **mới** — báo cáo này |
| `app/thu/thu_g22_phanloai.py` | **mới** — bảng + `chan_doan()` + 6 ca tự kiểm (chạy `Ran 6 · OK`, exit 0) |
| Bộ thử khác / mã sản phẩm / `.git` / DB thật | **KHÔNG sửa** |

**Tự kiểm cuối:** `python3 app/thu/thu_g22_phanloai.py` → `Ran 6 tests · OK · exit 0`.
