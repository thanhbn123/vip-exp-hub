# G04 — ORDER SERVICE (AG-02 ORDERS)

Tài liệu của **một** file mã: `app/don_hang.py`, kèm bộ thử `app/thu/thu_don_hang.py`.
Viết cho hai người đọc: AG-00 (để cắm route + chạy migration) và người bảo trì sau này.

Nền: nhánh `agent/g04-orders`, nền `4016eef`. **MỞ RỘNG mã đang chạy, không xây lại** — directive
đợt này ghi G04 "NOT STARTED", điều đó **sai**: `don_hang.py` đã có `tao_don · sua_don · duyet_don
· gui_don · huy_don · lay_don · ap_trang_thai_giao` từ trước.

---

## 1. Hai bất biến không được phá

1. **Hai trục trạng thái tách nhau.** `trang_thai` là NGHIỆP VỤ (người điều khiển),
   `trang_thai_giao` là GIAO VẬN (hãng báo về). Vòng đời "mở rộng" được **suy ra** từ hai trục,
   không thêm giá trị enum mới vào cột nào. Có ca thử canh: `test_c01_hai_truc_khong_bi_gop`
   đòi tập giá trị hai trục **không giao nhau** và bảng ánh xạ khớp `cau_hinh.HANG_TRANG_THAI_GIAO`.
2. **Chỉ vào `da_gui` khi hãng XÁC NHẬN.** Hết giờ ⇒ giữ `dang_gui` + `can_doi_soat_ket_qua=1`.
   "Không rõ" không phải thành công, cũng không phải thất bại.

## 2. Bảng ánh xạ: vòng đời directive ↔ hai trục hiện có

| Directive | `trang_thai` | `trang_thai_giao` | Điều kiện phụ |
|---|---|---|---|
| `DRAFT` | `nhap` | NULL | dữ liệu **chưa** hợp lệ (`kiem_don` còn lỗi) |
| `VALIDATED` | `nhap` | NULL | dữ liệu hợp lệ — **đồng nghĩa** `PENDING_APPROVAL` |
| `PENDING_APPROVAL` | `nhap` | NULL | dữ liệu hợp lệ, chưa có lý do từ chối |
| `REJECTED` | `nhap` | NULL | `ly_do_tu_choi IS NOT NULL` |
| `APPROVED` | `da_duyet` | NULL | — |
| `SUBMITTING` | `dang_gui` | NULL | `can_doi_soat_ket_qua=0` |
| `SUBMIT_UNKNOWN` **(thêm)** | `dang_gui` | NULL | `can_doi_soat_ket_qua=1` |
| `SUBMITTED` | `da_gui` | `cho_lay` | — |
| `PICKED_UP` | `da_gui` | `lay_hang` | — |
| `IN_TRANSIT` | `da_gui` | `dang_giao` | — |
| `DELIVERY_FAILED` | `da_gui` | `giao_that_bai` | — |
| `DELIVERED` | `da_gui` | `giao_thanh_cong` | — |
| `RETURNED` | `da_gui` | `hoan_hang` | — |
| `CANCELLED` | `huy` | bất kỳ | — |

Ba điều cần nói rõ, vì chúng là **quyết định**, không phải chi tiết kỹ thuật:

- **`VALIDATED` và `PENDING_APPROVAL` nhập một.** Hệ này không có bước "bấm nút validate" lưu vào
  CSDL; một đơn nháp đã hợp lệ thì đương nhiên đang chờ duyệt. `MO_RONG_DONG_NGHIA` ánh xạ
  `VALIDATED → PENDING_APPROVAL` nên lọc bằng tên nào cũng ra cùng kết quả
  (`test_f02`). Nói ra để người đọc không đi tìm một cột không tồn tại.
- **`REJECTED` không là giá trị enum mới.** Nó là `nhap` + `ly_do_tu_choi`. Thêm `tu_choi` vào
  `trang_thai` là phá hợp đồng mục 10 và làm mọi truy vấn cũ `trang_thai='nhap'` đọc thiếu.
  `sua_don` xóa lý do cũ, nên sửa xong đơn quay về `PENDING_APPROVAL` (`test_c02`).
- **`SUBMIT_UNKNOWN` là tên directive KHÔNG có.** Phải thêm, vì directive chỉ có `SUBMITTING` và
  `SUBMITTED` — không có tên nào cho "đã gọi hãng mà không biết kết quả". Gộp nó vào
  `SUBMITTING` là che mất đúng cái tình trạng nguy hiểm nhất.

**Máy trạng thái trục nghiệp vụ** (`CHUYEN_DUOC`, danh sách TRẮNG — quên một dòng thì CHẶN một
chuyển hợp lệ, thấy ngay; dùng danh sách đen thì CHO QUA một chuyển sai, hỏng im lặng):

```
nhap     → nhap · da_duyet · huy
da_duyet → nhap (sửa / bị từ chối) · dang_gui · huy
dang_gui → da_gui (hãng xác nhận) · da_duyet (CHỈ qua đối soát "hãng chưa nhận") · huy
da_gui   → huy
huy      → (cuối, không đi đâu)
```

`QUYEN_CHUYEN` khai quyền cho **từng cặp**; `test_c05` hỏng nếu thêm một cặp mà quên khai quyền.

## 3. Quy ước tiền và khối lượng (O01)

Tiền là **số nguyên theo đồng** (đơn vị nhỏ nhất của VND): `cod`, `gia_tri_khai`,
`phi_van_chuyen`, `don_mat_hang.don_gia`. Khối lượng là **số nguyên gram**.

**Cấm float.** `_so_nguyen_tien()` **chặn** số có phần thập phân thay vì cắt cụt:
`int(float("150000.7"))` = 150000 — mất tiền mà không báo gì. Số thực nguyên (JSON hay gửi
`150000.0`) thì nhận. `test_b01` kiểm chặn, `test_b02` kiểm cột trong CSDL là `INTEGER` chứ không
`REAL` — canh ngay ở schema, vì `REAL` là cửa cho float lọt vào từ đường khác.

## 4. Hàm mới và hàm đã đổi

| Hàm | Việc | Quyền |
|---|---|---|
| `kiem_don(tenant_id, don_id=…\|d=…)` | O03 validate riêng, **chỉ đọc** | — |
| `tu_choi_don(tid, uid, don_id, ly_do)` | O03 từ chối duyệt, lý do **bắt buộc** | `tenant.don.duyet` |
| `tim_don(tid, loc)` | O03 tìm nâng cao + phân trang | `tenant.don.xem` |
| `dong_thoi_gian(tid, don_id)` | O03 hành trình hai trục, **không gọi hãng** | `tenant.don.xem` |
| `sieu_du_lieu_nhan_van_don(tid, uid, don_id)` | O03 siêu dữ liệu nhãn | `tenant.don.xem` |
| `lay_don_day_du(tid, don_id)` | gom đơn + mặt hàng + hành trình + kiểm | `tenant.don.xem` |
| `doi_soat_don(tid, uid, don_id)` | O04 đối soát bằng `getOrder`/`trackOrder` | `tenant.don.duyet` |
| `doi_soat_tay(tid, uid, don_id, ket_luan, …)` | O04 NGƯỜI kết luận khi máy không tra được | `tenant.don.duyet` |
| `don_can_doi_soat(tid)` | danh sách đơn treo "không rõ" | `tenant.don.xem` |
| `luu_mat_hang(tid, uid, don_id, cac_mon)` | O01 thay toàn bộ mặt hàng | `tenant.don.ghi` |
| `lay_mat_hang` · `co_tinh_nang_mat_hang` | đọc mặt hàng / hỏi CSDL đã migrate chưa | — |
| `trang_thai_mo_rong(don)` · `kiem_chuyen(cu, moi)` | ánh xạ + cưỡng chế chuyển trạng thái | — |

**Đổi hành vi (AG-00 đọc kỹ ba dòng này):**

1. `gui_don` **không còn nhận đơn ở `dang_gui`**. Trước đây nhận cả `('da_duyet','dang_gui')`;
   giờ `dang_gui` trả **409**: có cờ đối soát thì bắt đi `doi_soat_don`, không có cờ thì "đang gửi
   ở lượt khác". Đây là cách giết hẳn đường sinh vận đơn trùng, không phải nới thêm `if`.
2. `gui_don` **chiếm đơn bằng một câu `UPDATE … WHERE trang_thai='da_duyet'`** rồi đọc `rowcount`,
   thay cho đọc-rồi-ghi. Đo thật: bản đọc-rồi-ghi cho **4/4** lượt song song gọi `createOrder`
   (4 vận đơn); bản này cho đúng **1**, ba lượt kia nhận 409 (`test_d05`).
3. `huy_don` **chặn hủy đơn `dang_gui` còn cờ đối soát** (409): hủy khi chưa biết hãng có đơn hay
   không là có thể bỏ lại một vận đơn sống ở hãng.
4. Mọi hàm ghi **tự tra quyền trong CSDL** qua `tenant_memberships` + `role_permissions`. Trước
   đây chỉ `server.py` kiểm, nên mọi người gọi không qua HTTP (import engine, polling, script)
   đi vòng qua lớp quyền. Hai lớp này **cùng tra một bảng** nên không lệch nhau được — khác với
   "lọc hai chỗ" mà §12.2 cấm (hai *bộ lọc khác nhau* chồng lên nhau).

## 5. O04 — Đối soát: ba kết luận, không gộp

| Kết luận | Khi nào | Làm gì |
|---|---|---|
| `da_vao` | hãng trả `ok` **và có** mã vận đơn | → `da_gui`, lấy mã vận đơn của hãng, tắt cờ |
| `chua_vao` | hãng nói **RÕ** là không tìm thấy (`loi_hang.KHONG_TIM_THAY`) | → `da_duyet`, tắt cờ, **mới** được gửi lại |
| `van_chua_ro` | mọi trường hợp còn lại | **giữ nguyên** `dang_gui` + cờ, không mở đường gửi lại |

Luật an toàn ở đây: **chỉ lỗi "không tìm thấy" mới kết luận là hãng chưa nhận.** Sai chữ ký, quá
hạn mức, lỗi lạ, hết giờ — tất cả là `van_chua_ro`. Coi "lỗi nào cũng là chưa vào" là đường ngắn
nhất tới vận đơn trùng. `test_d13` canh đúng chỗ này.

**Không giả định hãng có idempotency key.** Thao tác đối soát chọn theo capability **thật**:
J&T khai `getOrder=False` ⇒ dùng `trackOrder` (`test_d10`); VTP khai `getOrder=True` ⇒ dùng
`getOrder` (`test_d09`). Cờ `KHOA_CHONG_TRUNG` (J&T `True` vì có `txlogisticId`, VTP `False` vì
chưa có tài liệu) được tôn trọng qua `transport.chinh_sach_cho` — `test_d11` canh.

Khóa tra khi chưa có mã vận đơn là **`ma_don` nội bộ**, vì với J&T đó đúng là `txlogisticId` đã
gửi lên. Hãng nào không có cả `getOrder` lẫn `trackOrder` thì máy **không** đối soát được: hàm
raise 409 và người dùng `doi_soat_tay()`, vết ghi rõ **"NGƯỜI kết luận"** chứ không để dấu vết
nói sai ai đã quyết (`test_d14`).

## 6. DDL + migration cần AG-00 chạy

Nguồn duy nhất: hằng `don_hang.DDL_G04` trong `app/don_hang.py`. Bộ thử chạy đúng hằng đó, nên
tài liệu/bộ thử/đề xuất **không thể lệch nhau**. AG-00 chép vào `csdl.SCHEMA` (phần
`CREATE TABLE don_hang` + bảng mới) và thêm một bước `migrate` cho CSDL đang chạy.

- 14 cột thêm vào `don_hang`: `external_reference`, `approved_by`, `approved_luc`,
  `ly_do_tu_choi`, `tu_choi_boi`, `tu_choi_luc`, và 8 cột địa chỉ có cấu trúc
  (`nguoi_{gui,nhan}_{tinh,quan,xa,buu_chinh}`). **Tất cả NULL được** ⇒ `ALTER TABLE ADD COLUMN`
  thuần, không cần dựng lại bảng, không có đường mất dữ liệu.
- 1 bảng mới `don_mat_hang` — có `tenant_id` **và** `don_id` (phòng thủ tại câu SQL, không chỉ
  dựa vào khóa ngoài), `UNIQUE(don_id, stt)`, tiền/khối lượng `INTEGER`.
- 3 index: `ix_don_extref`, `ix_mh_don`, `ix_mh_tenant`.

**Mã này chạy được trên CSDL CHƯA migrate** — cột dò bằng `PRAGMA table_info`, bảng dò bằng
`co_bang()`, có nhớ đệm và `quen_cache_schema()` để gọi lại sau migration. Lớp thử `A_ChuaMigrate`
chạy **trước** khi áp DDL, đúng để chứng minh câu này bằng phép đo chứ không bằng lời: thiếu cột
thì `tu_choi_don` trả **501** chứ không âm thầm bỏ lý do, `luu_mat_hang` trả **501**, và `tim_don`
**nói ra** điều kiện nào đã bị bỏ trong `loc_bo_qua`.

## 7. Route AG-00 cần cắm

AG-02 **không sửa `server.py`**. Bảng dưới đủ chi tiết để cắm ngay. Mẫu chung: `self._can(nc, …)`
trước, `don_hang.*` sau, bọc trong `except don_hang.LoiNghiepVu` đã có ở dòng 165 (dùng `e.ma`).
Tenant lấy từ phiên (`tenant_id`), **không bao giờ** từ body.

| # | Method | Đường | Quyền `_can` | Body / query vào | Ra (200 nếu không ghi khác) |
|---|---|---|---|---|---|
| 1 | POST | `/api/v2/don/{id}/tu-choi` | `tenant.don.duyet` | `{"ly_do": str}` **bắt buộc** | `{"don": {...}}` · 400 nếu thiếu lý do · 409 nếu đơn đã gửi · **501** nếu CSDL chưa migrate |
| 2 | POST | `/api/v2/don/{id}/doi-soat` | `tenant.don.duyet` | `{}` | `{"ket_luan": "da_vao\|chua_vao\|van_chua_ro\|khong_can", "thao_tac": "getOrder\|trackOrder", "hang": str, "moi_truong": str, "la_mock": bool, "don": {...}}` · 409 nếu hãng không tra được |
| 3 | POST | `/api/v2/don/{id}/doi-soat-tay` | `tenant.don.duyet` | `{"ket_luan": "da_vao\|chua_vao", "ma_van_don": str (bắt buộc khi da_vao), "ghi_chu": str}` | `{"ket_luan": …, "nguon": "nguoi", "don": {...}}` |
| 4 | POST | `/api/v2/don/tim` | `tenant.don.xem` | toàn bộ `loc` (xem §8) | `{"don": [...], "tong": n, "gioi_han": n, "lech": n, "loc_bo_qua": [...], "ghi_chu_tong": str}` |
| 5 | POST | `/api/v2/don/kiem` | `tenant.don.ghi` | dữ liệu đơn **chưa lưu** | `{"hop_le": bool, "loi": [...], "canh_bao": [...]}` |
| 6 | GET | `/api/v2/don/{id}/kiem` | `tenant.don.xem` | — | như trên + `trang_thai_mo_rong` |
| 7 | GET | `/api/v2/don/{id}/hanh-trinh` | `tenant.don.xem` | — | `{"don_id", "ma_don", "ma_van_don", "trang_thai", "trang_thai_giao", "hang_trang_thai_giao", "trang_thai_mo_rong", "can_doi_soat_ket_qua", "moc": [{"luc","nguon","noi_dung","truc":"nghiep_vu\|giao_van","trang_thai_giao","hang"}], "so_moc", "nguon_du_lieu"}` |
| 8 | GET | `/api/v2/don/{id}/nhan` | `tenant.don.xem` | — | `{"ho_tro_nhan": bool, "la_mock": bool, "nhan_that": bool, "dinh_dang", "do_lon_byte", "canh_bao": [...]}` · 409 nếu chưa có mã vận đơn |
| 9 | GET | `/api/v2/don/{id}/day-du` | `tenant.don.xem` | — | `{"don", "mat_hang", "hanh_trinh", "kiem", "chuyen_duoc_sang", "co_tinh_nang_mat_hang"}` |
| 10 | GET | `/api/v2/don/{id}/mat-hang` | `tenant.don.xem` | — | `{"mat_hang": [...]}` (`[]` nếu chưa migrate) |
| 11 | PUT | `/api/v2/don/{id}/mat-hang` | `tenant.don.ghi` | `{"mat_hang": [{"ten"(bắt buộc), "ma_sku", "so_luong"≥1, "don_gia"≥0, "khoi_luong_gram"≥0, "ghi_chu"}]}` tối đa 200 dòng | `{"mat_hang", "tong_khoi_luong_gram", "tong_gia_tri_dong", "don"}` · 409 nếu đơn đã gửi · 501 nếu chưa migrate |
| 12 | GET | `/api/v2/don/can-doi-soat` | `tenant.don.xem` | `?gioi_han=` | `{"don": [...]}` |

**Hai điều AG-00 phải để ý khi cắm:**

- Route 4 (`/api/v2/don/tim`) phải khớp **TRƯỚC** `re.fullmatch(r"/api/v2/don/(\d+)")`, và route 12
  (`/api/v2/don/can-doi-soat`) cũng vậy — `tim`/`can-doi-soat` không phải số nên không đụng, nhưng
  đặt sau nhánh `/api/v2/don` GET thì nó bị nhánh đó ăn trước. Đặt cùng chỗ với
  `/api/v2/don/xuat-csv` đang có.
- `tao_don` nay nhận thêm `external_reference`, 8 cột địa chỉ, và `mat_hang` **trong cùng body**
  (tạo đơn kèm mặt hàng một lượt). Không cần đổi route POST `/api/v2/don` đang có.
- Route 1–3, 11 nên `csdl.audit(...)` như các nhánh `don_{duyet,gui,huy}` đang làm.
  `tu_choi_don` và `doi_soat*` **đã tự ghi audit** trong hàm, nên đừng ghi thêm lần hai.

## 8. Tham số `loc` của `tim_don`

`trang_thai` · `trang_thai_giao` (chuỗi **hoặc** danh sách) · `trang_thai_mo_rong` (tên ở §2) ·
`carrier_account_id` · `khach_hang_id` · `can_doi_soat_ket_qua` · `ma_don` · `ma_van_don` ·
`external_reference` · `q` (tìm mờ trên `ma_don`, `ma_van_don`, `nguoi_nhan_ten`,
`nguoi_nhan_sdt`, `hang_hoa`) · `tu_ngay` / `den_ngay` (`YYYY-MM-DD`, so theo giờ VN) ·
`cod_tu` / `cod_den` (đồng) · `sap_xep` ∈ `moi_nhat · cu_nhat · cap_nhat_moi · cap_nhat_cu ·
cod_cao · cod_thap · nang_nhat` · `gioi_han` (trần **500**) · `lech`.

Hai chỗ cố ý:

- **`sap_xep` là danh sách trắng.** Tên cột không tham số hóa được bằng `?`, nên nhận tên tự do là
  mở cửa SQL injection — đây là **ngoại lệ chính đáng** của luật "dùng danh sách đen" (§12.2 đã
  nêu sẵn ngoại lệ: quên một dòng ở đây là mất một kiểu sắp xếp, không phải cho qua thứ nguy
  hiểm). `test_f04` thử cả `"id; DROP TABLE don_hang"`.
- **`trang_thai_mo_rong` lọc ở tầng Python, không ở `WHERE`**, vì nó là giá trị suy ra (có trường
  hợp phải chạy cả hàm kiểm dữ liệu). Hệ quả: `tong` đếm theo điều kiện SQL và **chưa** trừ phần
  lọc đó — nên trả về kèm `ghi_chu_tong` nói rõ. Giao diện phải đọc `ghi_chu_tong`, đừng hiển thị
  `tong` như tổng cuối.

## 9. O06 — Import → Order (đã có, đã kiểm lại)

`nhap_file.duyet_batch` tạo **đơn nháp** qua `don_hang.tao_don` với
`idem_key=f"import-{batch_id}-{dong_id}"`. Kiểm lại trong `G_ImportSangDon`:

- `test_g01`: đơn sinh ra ở `trang_thai='nhap'`, `ma_van_don` và `carrier_account_id` đều NULL —
  **import KHÔNG tự gửi hãng**.
- `test_g02`: duyệt lại cùng batch **không** sinh thêm đơn, và gọi thẳng `tao_don` với đúng
  `idem_key` cũ trả `trung=True`.
- `test_g03`: canh **định dạng** khóa trong `nhap_file.py` — nó là thứ duy nhất chống trùng giữa
  hai lượt duyệt batch, đổi định dạng mà không ai biết là hỏng im lặng.
- `test_g04`: dòng `INVALID` bị bỏ qua, không sinh đơn.

## 10. Giới hạn còn lại — ghi ra để không bị bỏ quên

| # | Giới hạn | Vì sao chưa làm |
|---|---|---|
| G04-L1 | Đối soát **chỉ chạy trên MOCK**. Mock trả `ok=True` và **echo** khóa tra, nên nhánh `da_vao` của mock là "echo", không phải bằng chứng. Adapter thật phải trả `ok=False` + `KHONG_TIM_THAY` khi hãng không có đơn, nếu không nhánh `chua_vao` sẽ không bao giờ chạy đúng. | `CHO_PHEP_LIVE=False` ở cả hai hãng, Owner chưa duyệt. Nhánh `chua_vao`/`van_chua_ro` đã được kiểm bằng adapter **giả** (`test_d12`, `test_d13`) chính vì mock thật không dựng được hai ca đó. |
| G04-L2 | `ap_trang_thai_giao(don_id, …)` **không nhận `tenant_id`** — an toàn hôm nay vì cả hai người gọi (`webhook._xu_ly`, `polling.chay_mot_luot`) đã giải quyết đơn theo tenant trước. Người gọi thứ ba quên là lỗi chéo tenant **không có gì báo**. | Đã là rủi ro ghi nhận của QA (Q-10) và đổi chữ ký ảnh hưởng `webhook.py`/`polling.py` — **không** thuộc quyền sở hữu của AG-02. Đề xuất AG-00: đổi thành `ap_trang_thai_giao(tenant_id, don_id, …)`. |
| G04-L3 | `billing.kiem_va_tang_don` tăng usage **lúc gọi hãng**, nên một đơn `van_chua_ro` rồi đối soát ra `chua_vao` rồi gửi lại sẽ **đếm hai lượt**. | Đổi chỗ tính usage là đổi hành vi `billing.py` (không thuộc AG-02) và đụng `test_09` của `thu_saas.py`. Sai lệch nhỏ và luôn theo hướng **đếm nhiều hơn thực**, không phải ít hơn. |
| G04-L4 | Chống chiếm đơn song song dựa trên `csdl.khoa_ghi` (RLock **trong một tiến trình**) + điều kiện `WHERE trang_thai='da_duyet'`. Câu `UPDATE` có điều kiện tự nó an toàn **cả khi nhiều tiến trình**; `khoa_ghi` chỉ là lớp thứ hai. | Đã đo bằng 4 luồng thật (`test_d05`). **Chưa đo** ca nhiều **tiến trình** — cần hai tiến trình Python cùng mở một `hub.db`. |
| G04-L5 | Nhãn vận đơn chỉ trả **siêu dữ liệu**, không trả nội dung nhãn, không lưu nhãn. | Nội dung nhãn là tệp nhị phân của hãng; nhét vào JSON là phình log và phình CSDL. Cần đường tải riêng, chưa có yêu cầu. |
| G04-L6 | `tim_don` không có chỉ mục riêng cho `q` (LIKE `%…%` quét bảng) và cho `cod`. | Lượng đơn hiện nhỏ. Thêm chỉ mục là việc của AG-00 (`csdl.py`), và nên đo trước khi thêm. |

## 11. Nghiệm thu

Bộ thử: `app/thu/thu_don_hang.py` — **63 ca**, 7 lớp:
`A_ChuaMigrate` (CSDL chưa migrate) · `B_MoHinhDuLieu` (tiền, mặt hàng, validate) ·
`C_VongDoi` (ánh xạ, chuyển sai bị chặn, từ chối, vết audit) · `D_IdemVaDoiSoat` (idempotency,
gửi đồng thời, kết quả không rõ, đối soát) · `E_CachLyVaQuyen` (cách ly tenant, RBAC, soát SQL
tĩnh) · `F_TimKiemVaTraCuu` (tìm, hành trình, nhãn) · `G_ImportSangDon`.

**Bộ thử đã được kiểm là có thật sự bắt lỗi**, không chỉ là đạt sẵn (§12.1): tạm hoàn nguyên
`_chiem_de_gui` về kiểu đọc-rồi-ghi thì `test_d05` **hỏng** với đúng triệu chứng của lỗi
(`4 != 1 : 4 lượt gửi thành công`), rồi hoàn nguyên lại và chạy đạt. Một ca canh không bao giờ
hỏng thì không chứng minh được gì.
