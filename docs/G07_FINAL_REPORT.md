# G07 — COD & RECONCILIATION — BÁO CÁO BÀN GIAO

**Tác tử:** AG-01 FINANCE ENGINEER · **Nhánh:** `agent/g07-finance` · **Nền:** `143084b`
**Ngày:** 15/10/2026 · **Máy đo:** MacBook Pro (xem mục PHẠM VI ĐO)

---

## 1. FILE ĐÃ ĐỔI

| File | Dòng | Việc |
|---|---|---|
| `app/tai_chinh.py` | 1061 | `DDL_G07` (13 bảng) · bút toán bất biến · sổ COD 6 trạng thái · phí · đợt thanh toán · công nợ · điều chỉnh · nhật ký móc băm |
| `app/doi_soat.py` | 594 | ánh xạ cột theo hãng có phiên bản · nạp bảng kê CSV/XLSX · đối chiếu · 7 loại chênh lệch · phê duyệt · xuất CSV |
| `app/thu/thu_tai_chinh.py` | 730 | 51 ca thử |
| `app/thu/thu_doi_soat.py` | 472 | 27 ca thử |
| `admin/finance.js` | 369 | logic thuần 7 màn hình, tự khai CHỜ BACKEND |
| `docs/G07_FINAL_REPORT.md` | — | file này |

`git status` cho thấy **5 file mới, 0 file bị sửa**. KHÔNG chạm `app/csdl.py`,
`app/migrate.py`, `app/server.py`, `app/cau_hinh.py`, `app/don_hang.py`, `app/billing.py`,
`docs/SHARED_CONTRACTS.md`, hay file của agent khác.

---

## 2. HẰNG `DDL_G07` — ĐỀ XUẤT MIGRATION v8 CHO AG-00

Nguyên văn SQL nằm trong `app/tai_chinh.py` ở hằng `DDL_G07` (một nguồn duy nhất — bộ thử
chạy đúng chuỗi đó qua `_dam_bao_bang()`, nên bản trong tài liệu không thể lệch với bản
đang chạy). Nội dung:

**13 bảng** (toàn bộ `CREATE TABLE IF NOT EXISTS`):

| # | Bảng | Việc |
|---|---|---|
| 1 | `tc_but_toan` | FinancialEntry §17 — bút toán bất biến, có cột `dao_cua` trỏ dòng bị đảo |
| 2 | `tc_nhat_ky` | nhật ký tài chính bất biến, móc băm theo tenant (`bam_truoc` → `bam`) |
| 3 | `tc_cod` | sổ COD, một dòng một đơn, 6 trạng thái §18 |
| 4 | `tc_cod_chuyen` | lịch sử chuyển trạng thái COD |
| 5 | `tc_phi` | khoản phí: loại · nguồn · thời điểm ghi nhận · bút toán gắn kèm |
| 6 | `tc_dot_tt` | đợt thanh toán của hãng |
| 7 | `tc_dot_tt_dong` | dòng của đợt thanh toán |
| 8 | `tc_cong_no` | công nợ phải thu / phải trả theo đối tác |
| 9 | `tc_dieu_chinh` | điều chỉnh tài chính: lý do · người · bút toán |
| 10 | `ds_dot` | đợt đối soát (một lượt nạp bảng kê) |
| 11 | `ds_dong` | dòng bảng kê của hãng |
| 12 | `ds_chenh_lech` | chênh lệch, phân loại riêng 7 loại |
| 13 | `ds_anh_xa_cot` | ánh xạ cột theo hãng, có phiên bản (ghi đè bản trong mã) |

**11 index** (gồm `ux_tc_bt_dao` là UNIQUE partial index trên `tc_but_toan(dao_cua)`).

**4 trigger** chặn `UPDATE`/`DELETE` trên `tc_but_toan` và `tc_nhat_ky` bằng `RAISE(ABORT)`.

### Có `DROP` / `DELETE` / đổi kiểu cột không?

**KHÔNG.**

- **Không** `DROP` bất kỳ dạng nào.
- **Không** `ALTER TABLE` — `DDL_G07` chỉ tạo bảng mới, không sửa bảng đang có.
- **Không** đổi kiểu cột nào của bảng cũ.
- **Không** câu `DELETE` nào xoá dữ liệu. Chữ `DELETE` xuất hiện **đúng hai lần**, cả hai trong
  `CREATE TRIGGER ... BEFORE DELETE ON ... BEGIN SELECT RAISE(ABORT, ...); END;` — đó là
  **chốt chặn xoá**, ngược với xoá. AG-00 đọc qua thì đừng bắt nhầm hai dòng này.

### Ba điểm AG-00 cần biết khi gộp

1. **Tiền toàn bộ là `INTEGER`** (§16). Có `CHECK (so_tien_dong >= 0)` trên `tc_but_toan`:
   hướng nằm ở cột `loai`, không ở dấu. `tc_phi.so_tien_dong` **được phép âm** (phí hoàn,
   điều chỉnh giảm) — cố ý, để cộng tổng đọc thẳng.
2. **Trigger là phần không được bỏ.** Bỏ trigger thì ba ca thử `thu_tai_chinh` (`b1`, `b2`,
   `g2`) HỎNG — đã đo bằng mutation (mục 5).
3. **`UNIQUE(tenant_id, hang, ky_thanh_toan, van_tay_dong)` trên `ds_dong` là chốt idempotent**.
   Bỏ nó thì 3 ca thử `thu_doi_soat` HỎNG. Đây là ràng buộc CSDL, không phải phép kiểm trong mã.

---

## 3. BẢNG ROUTE CẦN AG-00 CẮM VÀO `server.py`

Chưa có route nào trong 15 dòng dưới đây. `admin/finance.js` đang khai cả 15 là **CHỜ BACKEND**
(bảng `API_CHO_BACKEND_TC`), và ca thử `j4` đọc `server.py` thật để đường nào đã cắm mà vẫn
khai chờ thì bộ thử HỎNG.

Quy ước quyền: hàm nghiệp vụ đã tự cưỡng chế qua `tai_chinh._can_quyen_tc()`, tra **quyền đã
có trong CSDL** (`tenant.billing.xem` cho đọc, `tenant.don.duyet` cho ghi/duyệt). Nếu AG-00
seed thêm `tenant.taichinh.xem|ghi|duyet` thì mã tự ưu tiên quyền riêng đó, không cần sửa.

| Đường | Method | Quyền | Vào | Ra | Mã lỗi |
|---|---|---|---|---|---|
| `/api/v2/tai-chinh/cod` | GET | `tenant.billing.xem` | `trang_thai?` `hang?` `q?` `gioi_han?` | `{cod: [], tong_hop: {}}` | 400 trạng thái lạ · 403 |
| `/api/v2/tai-chinh/tong-so` | GET | `tenant.billing.xem` | — | `tai_chinh.tong_so_tai_chinh()` | 403 |
| `/api/v2/tai-chinh/cong-no` | GET | `tenant.billing.xem` | — | `{phai_thu:{}, phai_tra:{}, tong_*}` | 403 |
| `/api/v2/tai-chinh/cod/<don_id>` | GET | `tenant.billing.xem` | — | `{cod, lich_su, phi, but_toan}` | 404 không thuộc tenant |
| `/api/v2/tai-chinh/dieu-chinh` | GET | `tenant.billing.xem` | `gioi_han?` | `{dieu_chinh: []}` | 403 |
| `/api/v2/tai-chinh/dieu-chinh` | POST | `tenant.don.duyet` | `loai` `so_tien_dong` `ly_do` `don_id?` | `{dieu_chinh_id, but_toan_id}` | 400 thiếu lý do / 0đ / số thập phân · 403 · 404 |
| `/api/v2/tai-chinh/dot-thanh-toan` | POST | `tenant.don.duyet` | `hang` `ma_dot` `so_tien_hang_bao` `carrier_account_id?` `ky_tu?` `ky_den?` | `{dot_id}` | 409 trùng mã đợt · 403 |
| `/api/v2/tai-chinh/dot-thanh-toan/<id>/ghi-nhan` | POST | `tenant.don.duyet` | `don_id` `so_tien_dong` | `{da_tra, phai_tra, du, con_lai, trang_thai}` | 409 trùng / vượt / chưa đối soát · 404 |
| `/api/v2/tai-chinh/dot-thanh-toan/<id>/chot` | POST | `tenant.don.duyet` | — | `{ok: true}` | 409 không còn MOI |
| `/api/v2/doi-soat/nap` | POST | `tenant.don.duyet` | multipart: `hang` `ten_file` `tep` `ky_thanh_toan?` `carrier_account_id?` `phien_ban?` | `{dot_id, so_nap, so_trung, anh_xa_phien_ban, cot_nhan_ra, loi_dong}` | 400 chưa có ánh xạ / không nhận ra cột / định dạng khác · 413 quá dung lượng · 403 |
| `/api/v2/doi-soat/dot` | GET | `tenant.billing.xem` | `gioi_han?` | `{dot: []}` | 403 |
| `/api/v2/doi-soat/dot/<id>/bang-ke` | GET | `tenant.billing.xem` | `gioi_han?` | `{dong: []}` | 404 |
| `/api/v2/doi-soat/dot/<id>/doi-chieu` | POST | `tenant.don.duyet` | — | `{so_khop, tong_chenh_lech, theo_loai}` | 409 không ở `DOI_CHIEU` · 404 |
| `/api/v2/doi-soat/dot/<id>/chenh-lech` | GET | `tenant.billing.xem` | `loai?` | `{chenh_lech: []}` | 400 loại lạ · 404 |
| `/api/v2/doi-soat/dot/<id>/duyet` | POST | `tenant.don.duyet` | — | `{da_ap, bo_qua, loi}` | **409 đã áp rồi** · 403 · 404 |
| `/api/v2/doi-soat/dot/<id>/tu-choi` | POST | `tenant.don.duyet` | `ly_do` | `{ok: true}` | 400 thiếu lý do · 409 |
| `/api/v2/doi-soat/dot/<id>/xuat-csv` | GET | `tenant.billing.xem` | — | `text/csv` đã làm sạch công thức | 404 |
| `/api/v2/doi-soat/chenh-lech/<id>/xu-ly` | POST | `tenant.don.duyet` | `xu_ly` `ghi_chu` | `{ok: true}` | 400 bỏ qua không ghi lý do · 409 không còn mở |

Mọi lỗi đều là `tai_chinh.LoiTaiChinh` (kế thừa `don_hang.LoiNghiepVu`) với `.ma` là mã HTTP,
nên `server.py` map được bằng đường bắt lỗi đã có, **không cần thêm nhánh mới**.

`tenant_id` **chỉ lấy từ phiên đã xác thực**, không bao giờ từ body/query (§1). Mọi hàm nghiệp
vụ nhận `tenant_id` làm tham số đầu.

---

## 4. KIẾN TRÚC — BẢY QUYẾT ĐỊNH VÀ LÝ DO

### 4.1 `giao_thanh_cong` không có đường nào tới `COD_SETTLED`

Không phải "chúng tôi nhớ không nối" — **cấu trúc không có đường đó**:

- `chuyen_cod()` là cửa duy nhất đổi trạng thái COD, và nó **từ chối** `den="COD_SETTLED"` (409).
- `COD_SETTLED` chỉ được đặt trong `ghi_nhan_thanh_toan()`, hàm bắt buộc có một `tc_dot_tt`
  với số tiền thật và đơn phải đang ở `COD_RECONCILED`/`COD_ADJUSTED`.
- Ca thử `c3` dựng một đơn `giao_thanh_cong` thật (gọi `don_hang.ap_trang_thai_giao`), rồi đòi
  COD vẫn `COD_EXPECTED` và cửa thanh toán **từ chối**.

### 4.2 Bất biến do CSDL cưỡng chế, không do lời dặn

Trigger `BEFORE UPDATE`/`BEFORE DELETE` trên `tc_but_toan` + `tc_nhat_ky`. Sửa sai thì ghi bút
toán ĐẢO (`dao_but_toan`), và `UNIQUE(dao_cua)` chặn đảo hai lần.

Thêm một lớp nữa: nhật ký có **móc băm** (`bam` của dòng n chứa `bam` của dòng n−1). Ca thử `g3`
**gỡ trigger rồi sửa ngầm** và đòi `kiem_nhat_ky()` tố giác — tức là kiểm chứng của kiểm chứng:
cả khi trigger bị vô hiệu, vẫn có đường phát hiện.

### 4.3 Công nợ dựng lại được từ sổ

`tc_cong_no` là bảng tổng hợp cập nhật trong cùng transaction với bút toán. Nhưng **có thêm**
`tinh_lai_cong_no()` dựng lại hoàn toàn từ `tc_but_toan`, và ca thử `i1` so hai con số sau mọi
luồng. Nên câu "công nợ đúng" ở đây là một **phép đo**, không phải một lời tin. `tong_so_tai_chinh()`
trả cờ `cong_no_khop`, và `admin/finance.js` hiện cảnh báo mức **nặng** khi cờ đó `false`.

### 4.4 Đồng thời: `UPDATE ... WHERE <trạng thái>` + `rowcount`, không đọc-rồi-ghi

Bốn chỗ: `chuyen_cod`, `ghi_nhan_thanh_toan`, `dong_dot_thanh_toan`, `duyet_dot`.
Hai ca thử đo bằng **thread thật đua nhau** (không bằng đọc mã): `d5` (10 thread trả tiền,
đúng 3 lượt qua, tổng không vượt) và `c5` (8 thread duyệt cùng một đợt, đúng 1 lượt áp, đúng
1 bút toán).

### 4.5 Import idempotent bằng ràng buộc CSDL

`UNIQUE(tenant_id, hang, ky_thanh_toan, van_tay_dong)` trên `ds_dong`, `van_tay_dong` là
sha256 của dòng đã chuẩn hoá. Nạp lại cùng file → `INSERT` ném `IntegrityError` → dòng ghi là
**`dong_trung`** (một trong bảy loại), không cộng tiền lần hai. Ca thử `D_Idempotent.d1` đo
bằng cách nạp→duyệt→nạp lại→duyệt rồi **đếm tiền trong sổ**, không bằng đọc DDL.

Kỳ thanh toán nằm trong khoá: cùng vận đơn ở **kỳ khác** là giao dịch khác (truy thu tháng
sau), không bị coi là trùng — ca `d3`.

### 4.6 Phê duyệt: chỉ áp dòng `KHOP`

Dòng lệch là chỗ hệ và hãng **không đồng ý**. Áp tự động là chọn tin hãng mà không ai quyết
định — đúng cái §18 cấm. Dòng lệch ở lại `ds_chenh_lech` với `xu_ly='mo'`; muốn áp thì ghi
`tai_chinh.dieu_chinh()` có lý do và người. Ca `c6` đòi `da_ap == 0` cho đợt toàn dòng lệch.

### 4.7 Bảy loại chênh lệch, không gộp thành "lỗi"

`thieu_don_he` · `thieu_dong_hang` · `dong_trung` · `cod_lech` · `phi_lech` ·
`dieu_chinh_bat_thuong` · `khong_khop_duoc`. Mỗi loại có **cách xử** khác nhau, khai ngay trong
`doi_soat.LOAI_CHENH_LECH` và `finance.js` để màn hình hiện được. Ngưỡng "bất thường": lệch
≥ 500.000đ hoặc ≥ 2000 **điểm cơ bản** (20%) — tính bằng số nguyên (`lech * 10000 >= so_he * bps`),
**không chia ra số thực ở bất kỳ bước nào** (§16).

---

## 5. KẾT QUẢ THỬ — SỐ THẬT, LỆNH THẬT

### 5.1 Hai bộ thử mới

```
$ python3 app/thu/thu_tai_chinh.py
Ran 51 tests in 0.225s
OK

$ python3 app/thu/thu_doi_soat.py
Ran 27 tests in 0.036s
OK
```

**78 ca mới, 0 hỏng.** Phủ đủ 9 hạng mục nghiệm thu yêu cầu:

| Hạng mục nghiệm thu | Ca thử |
|---|---|
| vòng đời COD | `C_VongDoiCOD` c1–c6 (6 ca) |
| thanh toán trùng | `d1` (UNIQUE), `d2` (trùng mã đợt), `d6` (chốt đợt hai lần) |
| thanh toán một phần | `d3` (60/100 → vẫn `COD_RECONCILED`; trả nốt → `COD_SETTLED`), `d4` (trả vượt bị từ chối) |
| phí lệch | `e1`, `e2`; `B_PhanLoai.b2` (`phi_lech` tách khỏi `cod_lech`) |
| nhật ký điều chỉnh | `F_DieuChinh` f1–f5, `G_NhatKy` g1–g3 |
| đối soát đồng thời | `c5` (8 thread), `d5` (10 thread), `c4`, `c8` |
| cách ly chéo tenant | `H_CachLyTenant` h1–h5, `E_CachLy` e1–e2 |
| tổng số tài chính | `I_TongSo` i1–i4 |
| import idempotent | `D_Idempotent` d1–d3 |

Thêm: `A_Tien` (3 ca, gồm quét `PRAGMA table_info` trên **schema thật** để không cột tiền nào
là `REAL`/`FLOAT`), `B_ButToanBatBien` (6), `A_AnhXaCot` (9, hai hãng hai định dạng + XLSX),
`J_GiaoDien` (9, chạy `node` thật trên `admin/finance.js`).

### 5.2 Mutation test — ca thử có load-bearing hay không

Gỡ từng bản vá rồi chạy lại. Nếu bộ thử vẫn ĐẠT thì ca thử đó vô dụng. Kết quả thật:

| Gỡ cái gì | Bộ thử | Kết quả |
|---|---|---|
| Chốt chặn `den == "COD_SETTLED"` trong `chuyen_cod` | `thu_tai_chinh` | **FAILED (1)** |
| Chốt chặn "phải `COD_RECONCILED` mới nhận tiền" | `thu_tai_chinh` | **FAILED (1)** |
| Trigger bất biến còn đó nhưng không `RAISE` | `thu_tai_chinh` | **FAILED (3)** |
| Bỏ `WHERE trang_thai='CHO_DUYET'` khi chiếm đợt | `thu_doi_soat` | **FAILED (3)** |
| `UNIQUE(...van_tay_dong)` → `CHECK (1=1)` | `thu_doi_soat` | **FAILED (3)** (`b2`, `d1`, `d2`) |
| `duyet_dot` áp cả dòng `LECH` | `thu_doi_soat` | **FAILED (1)** (`c6`) |

Phục hồi mã gốc rồi chạy lại: cả hai bộ **OK**.

### 5.3 Không làm hỏng cái cũ

| Bộ | Ca | Kết quả |
|---|---|---|
| `thu_bao_mat` | 57 | OK |
| `thu_gioi_han` | 34 | OK |
| `thu_g03` | 53 | OK |
| `thu_nhap_file` | 21 | OK |
| `thu_don_hang` | 63 | OK |
| `thu_g01_g02` | 21 | OK |
| `thu_saas` | 19 | OK |
| `thu_tich_hop` | 6 | OK |
| `thu_webhook` | 68 | OK |
| `thu_qa_soat` | 30 | OK |
| `thu_qa2_soat` | 49 | OK (1 skipped, như nền) |
| `thu_gateway` | 9 | OK |
| **`thu_tai_chinh`** | **51** | **OK (mới)** |
| **`thu_doi_soat`** | **27** | **OK (mới)** |
| **Tổng python** | **508** | **0 bộ hỏng** |

Frontend và E2E:

```
$ node --test thu_frontend/thu_logic.mjs   → tests 56 · pass 56 · fail 0
$ python3 thu_frontend/thu_http.py         → Ran 36 tests · OK
$ sh app/thu/chay_e2e.sh                   → KẾT QUẢ: 41/41 phép đo đạt · mã thoát 0
```

**Tổng: 508 + 56 + 36 + 41 = 641 phép kiểm, 0 hỏng** (nền 563 + 78 mới).

### 5.4 Phạm vi của con số 641 — cái gì NẰM NGOÀI (§12.1 luật số "0")

Câu "0 hỏng" ở trên **chỉ nói về**: 14 bộ `unittest` Python đã liệt kê, tầng 1 logic Node,
tầng 2 HTTP trên máy chủ thật, và 41 phép đo E2E mock — tất cả trên **MacBook Pro, SQLite,
CSDL thử trong `mktemp -d`, ngày 15/10/2026**.

**NẰM NGOÀI phạm vi, không được suy rộng:**

- **Tầng 3 giao diện** (DOM, CSS, bố cục, tràn ngang trong trình duyệt thật) — repo cấm thư
  viện ngoài (V-13906-01 CHƯA CẤP), nên 7 màn tài chính **chưa được nhìn bằng trình duyệt**.
  `J_GiaoDien` chỉ phủ **quyết định logic**, không phủ hiển thị.
- **Route HTTP của G07** — chưa có đường nào, nên không có ca thử HTTP nào cho tài chính.
  Mọi ca thử gọi **thẳng hàm nghiệp vụ**. Tầng route còn là giả thiết chưa đo.
- **PostgreSQL** — chưa thử. `DDL_G07` viết cho SQLite; partial unique index
  (`CREATE UNIQUE INDEX ... WHERE`) và cú pháp trigger `RAISE(ABORT)` **không chạy trên
  PostgreSQL** nguyên văn. Xem mục 6.
- **Gọi API hãng thật** — không gọi, không mở (V-G09-01 CHƯA CẤP). Bảng kê trong bộ thử là
  **file CSV/XLSX tự dựng**, không phải file thật của Viettel Post hay J&T.
- **Giao dịch ngân hàng** — không tạo, không nối. "Đợt thanh toán" là một bản ghi trong CSDL,
  không có đường nào ra ngân hàng.
- **Dữ liệu thật** — mọi lượt chạy dùng `VIP_HUB_DATA` trỏ vào `mktemp -d`. KHÔNG chạy
  migration lên `~/Projects/vip-express-hub/app/du-lieu/` (§24).

---

## 6. GIỚI HẠN CÒN LẠI — NÓI THẲNG

### 6.1 Chưa làm được

1. **Không có route nào.** `app/server.py` do AG-00 giữ (§22). Bảy màn hình giao diện hiện
   **không đọc được dữ liệu thật** và tự khai đúng như vậy. Đây là giới hạn lớn nhất của G07:
   nghiệp vụ xong, đường vào chưa có.

2. **Chưa seed quyền tài chính riêng.** `app/quyen.py` không nằm trong danh sách sở hữu đợt 3,
   nên mã **rơi về quyền đã có**: đọc dùng `tenant.billing.xem`, ghi/duyệt dùng
   `tenant.don.duyet`. Hệ quả thật: **`TENANT_STAFF` không xem được màn tài chính**
   (vai trò đó không có `tenant.billing.xem`), và **ai duyệt được đơn thì duyệt được đối
   soát tiền** — hai việc đó nên tách.
   *Cách vá đúng:* AG-00 thêm `tenant.taichinh.xem|ghi|duyet` vào `quyen.QUYEN` + `MA_TRAN`;
   `tai_chinh.QUYEN_TC` đã ưu tiên quyền riêng nên **không cần sửa một dòng mã nào**.

3. **PostgreSQL chưa thử, và `DDL_G07` sẽ KHÔNG chạy nguyên văn.** Ba chỗ phải đổi khi di cư:
   `CREATE UNIQUE INDEX ... WHERE dao_cua IS NOT NULL` (Postgres có partial index nhưng cú
   pháp `IF NOT EXISTS` khác), `CREATE TRIGGER ... BEGIN SELECT RAISE(ABORT, ...)` (Postgres
   cần `CREATE FUNCTION ... RAISE EXCEPTION` + trigger gọi hàm), và `ON CONFLICT ... DO UPDATE`
   (cú pháp giống nhưng cần kiểm). **Chưa đo** — đây là giả thiết chưa kiểm, không phải kết luận.

4. **`doi_chieu()` quét toàn bộ đơn của hãng để tìm "hãng không báo".** Chưa phân trang, chưa
   giới hạn theo kỳ. Tenant có hàng trăm nghìn đơn sẽ chậm. **Chưa đo** ngưỡng chậm.
   *Cách vá:* thêm điều kiện khoảng ngày của đợt vào `sql_thieu`, cần cột ngày trong `ds_dot`
   mà bảng kê hãng không luôn có.

5. **Chưa đọc `.xls` cũ và PDF.** `nap_bang_ke` từ chối rõ ràng (400) chứ không đọc nửa vời.
   `nhap_file.doc_pdf_text` có sẵn nhưng bảng kê PDF cần tách bảng — chưa làm.

6. **`_so_tien_o` suy luận dấu phân cách nghìn.** `"1.234"` được hiểu là 1234 (ba số sau dấu
   chấm), `"1.23"` bị **CHẶN** là số thập phân. Đúng với mẫu VN, nhưng nếu hãng nào xuất file
   theo quy ước Anh–Mỹ với 2 số thập phân thì sẽ bị chặn — **chặn là đúng** (§16: thà báo lỗi
   hơn cắt cụt), nhưng người nạp sẽ không nạp được và cần khai ánh xạ/tiền xử lý.

### 6.2 Rủi ro cố ý bỏ qua, ghi ra để không bị bỏ quên

| Rủi ro | Vì sao bỏ qua | Cách vá đúng |
|---|---|---|
| Móc băm nhật ký **không** chống được người xoá cả đuôi sổ rồi ghi lại từ một dòng cũ | Chống việc đó cần neo băm ra ngoài CSDL (ký số, hoặc đẩy băm cuối ngày sang nơi khác) — vượt phạm vi G07 và chạm V-13906-03 CHƯA CẤP | Cuối mỗi ngày ghi `bam` cuối cùng của mỗi tenant vào một nơi chỉ-ghi-thêm ngoài CSDL |
| `tc_cong_no` vẫn **có thể** lệch nếu một ngày nào đó ai ghi `tc_but_toan` bằng SQL trực tiếp (trigger chỉ chặn UPDATE/DELETE, không chặn INSERT) | Chặn INSERT trực tiếp là chặn luôn đường ghi hợp lệ | Đã có `tinh_lai_cong_no()` + cờ `cong_no_khop` hiện cảnh báo **nặng** trên màn hình. Nên thêm một lượt đối chiếu định kỳ |
| `duyet_dot` áp từng dòng trong **nhiều** transaction nhỏ, không phải một transaction lớn | SQLite WAL một writer; gói cả đợt vào một transaction giữ khoá ghi quá lâu, chặn mọi phiên khác | Dòng nào hỏng được ghi thành `ds_chenh_lech` loại `khong_khop_duoc` kèm nguyên văn lỗi, **không** làm cả đợt hỏng im lặng. Đợt vẫn `DA_AP` nhưng `bo_qua > 0` và `loi` không rỗng — giao diện phải hiện |
| Ngưỡng bất thường (500.000đ / 20%) là **số do tác tử chọn**, không có nguồn nghiệp vụ | Chưa ai cho số thật | Anh Thành hoặc AG-00 chốt số; đổi hai hằng `NGUONG_LECH_DONG` / `NGUONG_LECH_BPS` ở đầu `doi_soat.py`, có ca thử `b3` canh |
| Ánh xạ cột `vtp`/`jt` phiên bản `2026-10` dựng từ **tên cột phỏng đoán**, chưa đối chiếu file thật của hãng | Không có file bảng kê thật (V-G09-01 CHƯA CẤP) | Có file thật thì thêm biến thể vào `ANH_XA_COT` hoặc khai qua `doi_soat.dat_anh_xa()` **không cần sửa mã** — đó là lý do có bảng `ds_anh_xa_cot` |

---

## 7. CÁCH CHẠY LẠI

```bash
cd ~/code/veh3-g07-finance
export VIP_HUB_DATA=$(mktemp -d)     # BẮT BUỘC — §24, không chạm CSDL thật
python3 app/thu/thu_tai_chinh.py     # 51 ca
python3 app/thu/thu_doi_soat.py      # 27 ca
```

Hai bộ thử **tự tạo `mktemp -d`** riêng ngay khi nạp module, nên không phụ thuộc biến môi
trường ở ngoài và không bao giờ ghi vào CSDL thật. `DDL_G07` chưa vào `migrate.py` nên bộ thử
tự chạy nó qua `tai_chinh._dam_bao_bang()` (khuôn `gioi_han._dam_bao_bang`).
