# G08 — SaaS Commercialization — BÁO CÁO BÀN GIAO (AG-02 SAAS BILLING ENGINEER)

Ngày: **15/10/2026** · Worktree: `~/code/veh3-g08-billing` · Nhánh: `agent/g08-billing` · Nền: `143084b`
Máy đo: **MacBook Pro** (`python3`, `sqlite 3.51.0`, `node v26.7.0`). Mọi số trong tài liệu này
**lấy từ lệnh đã chạy**, không điền từ trí nhớ (CLAUDE.md §12.1 luật 4).

---

## 0. Một trang tóm tắt

| Mục | Làm được | Chỗ CHƯA phủ (đọc mục 8) |
|---|---|---|
| G08.1 Mô hình đăng ký | 9 bảng mới, phiên bản gói ghim được, lịch sử đầy đủ | `billing.py` chưa đọc phiên bản đã ghim |
| G08.2 Hạn mức | 8 loại, backend chốt, body tự khai bị bỏ | `request API/phút` vẫn do `gioi_han` lo |
| G08.3 Usage nguyên tử | `UNIQUE` ở CSDL + trần trong `WHERE`, đo thật | `kiem_va_tang_ai` của AG-00 còn đọc-rồi-ghi |
| G08.4 Máy tính phí | prorate theo ngày, dự thảo idempotent | không phát hành hoá đơn, không nối thanh toán (đúng chỉ thị) |
| G08.5 Giao diện | `admin/billing.js` logic thuần, 7 màn | 11 route **CHỜ BACKEND** — AG-00 cắm |

**Phép kiểm:** 78 ca Python mới (`Ran 37 ... OK` + `Ran 41 ... OK`) + 20 phép kiểm Node trên
`admin/billing.js`. 421 ca Python có từ trước **vẫn đạt**, không ca nào đổi.

---

## 1. File đã đổi

| File | Việc | Dòng |
|---|---|---|
| `app/goi_dich_vu.py` | MỚI — `DDL_G08`, phiên bản gói, đăng ký, hạn mức hiệu lực, đổi gói, chia tiền | 696 |
| `app/usage.py` | MỚI — sự kiện dùng, bộ đếm nguyên tử, kỳ tính phí, máy tính phí, dự thảo | 516 |
| `app/thu/thu_goi_dich_vu.py` | MỚI — 37 ca | 372 |
| `app/thu/thu_usage.py` | MỚI — 41 ca | 588 |
| `admin/billing.js` | MỚI — logic thuần màn billing (UMD, Node + trình duyệt) | 210 |
| `docs/G08_FINAL_REPORT.md` | MỚI — tài liệu này | 675 |

**Không chạm** `app/billing.py`, `app/csdl.py`, `app/migrate.py`, `app/server.py`,
`app/gioi_han.py`, `docs/SHARED_CONTRACTS.md`, và không file nào của agent khác.
`admin/` **không có thư mục con**.

---

## 2. G08.1 — Mô hình đăng ký, và cách giữ hạn mức KHÔNG đổi hồi tố

### 2.1 Vấn đề phải giải

`goi_dich_vu` chỉ giữ hạn mức **hiện tại** của mỗi gói. Sửa `basic.han_muc_don_thang` từ 1000
xuống 800 là siết luôn mọi tenant đang chạy `basic`: họ mất hạn mức đã thoả thuận, không có
thông báo nào, và **không còn cách nào dựng lại con số cũ** vì nó đã bị ghi đè.

### 2.2 Cách làm: ảnh chụp + ghim

- `goi_phien_ban(goi_id, phien_ban, …)` là **ảnh chụp đầy đủ** hạn mức + giá của một gói tại
  một thời điểm. Một dòng đã ghi thì **không bao giờ sửa**. Đổi hạn mức = `phat_hanh_phien_ban`
  → thêm dòng `phien_ban = max+1`.
- `dang_ky(tenant_id, goi_id, goi_phien_ban, …)` **GHIM** cặp (gói, phiên bản). Đây là "thoả
  thuận" của tenant đó.
- `han_muc_hieu_luc(tenant_id)` đọc hạn mức **từ ảnh chụp đã ghim**, rồi áp `han_muc_rieng`
  (nâng/hạ lẻ cho một tenant) nếu có. Mỗi con số trả ra kèm trường `nguon` nói nó từ đâu.
- Chuyển tenant sang phiên bản mới là **hành động riêng** (`chuyen_phien_ban` / `doi_goi`), có
  dòng trong `dang_ky_lich_su`.
- Tenant **chưa có** `dang_ky` (mọi tenant có từ trước đợt này) vẫn đọc được hạn mức qua
  `tenants.goi_id`, kèm cờ `tu_dang_ky=False` để người đọc biết con số đó **chưa được ghim**.
  Không agent nào được phép làm tenant cũ mất hạn mức.

**Ca thử canh điều này:** `thu_goi_dich_vu.A_PhienBanGoi.test_a4` — ghim `basic` v1, phát hành
v2 với `han_muc_don_thang=99999` và giá `777000`, rồi đo lại: phiên bản của tenant **không
nhảy**, hạn mức **không đổi**, giá **không đổi**. Nếu ai sửa mã để đọc hạn mức từ
`goi_dich_vu` thì ca này hỏng ngay.

### 2.3 Chín bảng (đủ mười mục chỉ thị yêu cầu)

| Mục chỉ thị | Bảng / chỗ giữ |
|---|---|
| gói dịch vụ | `goi_dich_vu` (đã có, **chỉ đọc**) |
| phiên bản gói | `goi_phien_ban` |
| đăng ký của tenant | `dang_ky` |
| lịch sử đổi gói | `dang_ky_lich_su` |
| sự kiện sử dụng | `su_kien_dung` |
| bộ đếm sử dụng | `bo_dem_dung` (chỉ loại chưa ai đếm) + `usage_thang` + `han_muc_nhap_thang` |
| hạn mức | `goi_phien_ban.*` + `han_muc_rieng` |
| kỳ tính phí | `ky_tinh_phi` |
| dự thảo hoá đơn | `du_thao_hoa_don` |
| nhật ký tính phí | `nhat_ky_tinh_phi` |

---

## 3. G08.2 — Hạn mức: tám loại, và chỗ nối vào cái CÓ SẴN

`goi_dich_vu.LOAI_HAN_MUC` khai mỗi loại kèm **`nguon_dem`** — bộ đếm nằm ở đâu. Đây là chỗ
chặn "hai bộ đếm cho một việc":

| Loại | Trần đọc từ | **Bộ đếm nằm ở** | G08 có đếm lại? |
|---|---|---|---|
| `don_thang` | `goi_phien_ban.han_muc_don_thang` | `usage_thang.so_don` — `app/billing.py` | **KHÔNG** |
| `ai_thang` | `goi_phien_ban.han_muc_ai_thang` | `usage_thang.so_ai` — `app/billing.py` | **KHÔNG** |
| `nhan_vien` | `goi_phien_ban.so_nhan_vien` | `COUNT tenant_memberships ⋈ users` | **KHÔNG** |
| `tai_khoan_hang` | `goi_phien_ban.so_tai_khoan_hang` | `COUNT carrier_accounts` | **KHÔNG** |
| `file_nhap_thang` | `gioi_han.tran_cua` | `han_muc_nhap_thang.so_file` — `app/gioi_han.py` | **KHÔNG** |
| `dong_nhap_thang` | `gioi_han.tran_cua` | `han_muc_nhap_thang.so_dong` — `app/gioi_han.py` | **KHÔNG** |
| `byte_luu_tru_thang` | `gioi_han.tran_cua` | `han_muc_nhap_thang.so_byte` — `app/gioi_han.py` | **KHÔNG** |
| `api_thang` | `goi_phien_ban.han_muc_api_thang` | `bo_dem_dung` — **G08** | CÓ (chưa ai đếm) |

**Nối vào `gioi_han.py` PHẦN B thế nào:** `usage.muc_dang_dung` gọi `gioi_han.da_dung()` để
đọc số thật; `usage.trang_thai_han_muc` trả kèm trọn `gioi_han.trang_thai()` ở khoá
`gioi_han_nhap`, và để `tran=None` cho ba loại đó — **`None` nghĩa là "trần do nơi khác
quyết", không phải "không giới hạn"**. `gdv.tran_cua_loai` **từ chối** trả trần cho ba loại
này thay vì bịa một con số (ca `test_d4`). `usage.ghi_su_kien` **từ chối** ghi ba loại đó qua
G08 kèm thông điệp chỉ sang đúng hàm của `gioi_han` (ca `test_b8`).

**Chỗ chưa phủ:** *số request API mỗi phút* vẫn do `gioi_han` rate-limit theo endpoint; G08
chỉ đếm **mỗi tháng** (`api_thang`). Không có bộ đếm thứ hai theo phút.

### 3.1 Backend chốt hạn mức — frontend KHÔNG được tự quyết

`usage.ghi_tu_yeu_cau(tenant_id, body)` chỉ đọc **bốn** trường (`loai`, `so_luong`,
`idem_key`, `tham_chieu`). Mọi trường khác bị **bỏ hoàn toàn** và trả lại ở `truong_bi_bo` để
người gọi thấy mình vừa khai thứ không có tác dụng. `tenant_id` đến từ **tham số của phiên**,
không từ body.

**Đo thật** (`thu_usage.B_ChanHanMuc.test_b2`): tenant có trần `api_thang=2`, gửi body

```json
{"loai":"api_thang","so_luong":1,"idem_key":"b2-3","tran":1000000000,
 "han_muc_don_thang":1000000000,"api_thang":1000000000,"goi_id":"pro",
 "phien_ban":99,"bo_dem":0,"tenant_id":99999}
```

→ lượt thứ 3 **bị chặn** `billing.VuotHanMuc`; `tran_cua_loai` vẫn trả **2**; 7 trường tự khai
nằm trong `truong_bi_bo`. Ca `test_b3` đo thêm: body khai `tenant_id` của tenant khác thì bộ
đếm tenant kia **vẫn bằng 0**.

---

## 4. G08.3 — Usage nguyên tử: SỐ ĐO THẬT

### 4.1 Hai chốt chặn, cả hai ở tầng CSDL

1. **Chống trùng:** `UNIQUE (tenant_id, idem_key)` trên `su_kien_dung` — ràng buộc CSDL, không
   phải `if` trong mã (ca `test_f5` đọc `sqlite_master` để canh câu ràng buộc còn đó).
2. **Chống vượt trần:** một câu
   `UPDATE bo_dem_dung SET so_luong=so_luong+? WHERE … AND so_luong+? <= ?`, xét `rowcount`.
   Không có lượt đọc nào trước nó.

Sự kiện và lượt cộng nằm **trong cùng một giao dịch**: vượt trần thì `rollback` bỏ cả hai, nên
lần thử lại (sau khi nâng hạn mức) **vẫn ghi được** — không để lại "sự kiện đã ghi mà chưa
được đếm", thứ sẽ làm lần thử lại bị coi là trùng rồi lặng lẽ không thu gì (ca `test_d2`).

### 4.2 Kiểm chính phép đo TRƯỚC khi tin nó (§12.1 luật 1)

`thu_usage.C_KiemChinhPhepDo.test_c1` dựng lại **đúng khuôn đọc-rồi-ghi đã vỡ ở đợt 2** rồi đòi
phép đo phải thấy nó vượt trần. Số đo:

```
c1_doc_roi_ghi: {'luong': 8, 'qua': 8, 'bi_chan': 0, 'bo_dem_cuoi': 17, 'tran': 10}
```

8/8 luồng lọt, bộ đếm **17 trên trần 10**. Nghĩa là: khi mục 4.3 nói "đúng 1 luồng qua", câu đó
có giá trị — phép đo đã chứng minh nó **bắt được** bản sai. (Đây là ca "thử gỡ bản vá xem bộ
thử có hỏng không", làm bằng bản đối chứng thay vì gỡ mã sản phẩm.)

### 4.3 Số đo thật, dán nguyên từ output

```
d1_tranh_suat_cuoi:     {'luong': 8, 'qua': 1, 'bi_chan': 7, 'bo_dem_cuoi': 10, 'tran': 10}
d4_cung_idem_key:       {'luong': 8, 'duoc_tinh': 1, 'bao_trung': 7, 'loi': 0, 'bo_dem_cuoi': 1}
d6_cheo_tenant:         {'luong': 10, 'qua': 10, 'loi': 0, 'a': 5, 'b': 5}
d9_don_thang_suat_cuoi: {'luong': 8, 'qua': 1, 'bi_chan': 7, 'so_don_cuoi': 50, 'tran': 50}
d12_ai_thang_suat_cuoi: {'luong': 8, 'qua': 1, 'bi_chan': 7, 'so_ai_cuoi': 20, 'tran': 20,
                         'vuot_tran': 0}
```

| Rủi ro chỉ thị nêu | Ca thử | Kết quả đo |
|---|---|---|
| sự kiện trùng | `d3`, `d4` | 1 lượt được tính / 8 luồng cùng `idem_key`; 4 lượt thử lại tuần tự đều `trung=True`, bộ đếm vẫn 5 |
| yêu cầu đồng thời | `d1`, `d9` | đúng **1/8** luồng qua, bộ đếm chạm trần, không vượt |
| thu phí hai lần | `d3`, `d4`, `f5` | 1 dòng `su_kien_dung`; lập dự thảo 4 lần → 1 dòng `du_thao_hoa_don` |
| tràn bộ đếm | `b5` | `so_luong=10**15` bị từ chối, bộ đếm vẫn 0 |
| lách hạn mức | `b1`, `b2`, `b9` | body tự khai trần không có tác dụng |
| cập nhật chéo tenant | `b3`, `d5`, `d6`, `f6` | 10 luồng xen kẽ hai tenant → đúng 5/5; `idem_key` trùng giữa hai tenant là **hợp lệ** |
| worker thử lại | `d3`, `d4`, `f5` | không thu lần hai |

### 4.4 Cái đang KHÔNG đếm qua G08 (nói rõ để không tưởng đã phủ)

`don_hang.gui_don` gọi **thẳng** `billing.kiem_va_tang_don`, không đi qua `usage.ghi_su_kien`.
Nên `su_kien_dung` **không phải** sổ đầy đủ của mọi đơn đã gửi. `usage.doi_soat_su_kien` nói
đúng điều đó: nó chỉ so 1:1 với `api_thang` (`so_sanh_duoc`), và liệt mọi loại khác vào
`ngoai_pham_vi` kèm lý do (ca `test_d10` canh chính câu này). Muốn phủ hết thì AG-00 cho
`gui_don` gọi qua `usage.ghi_su_kien` — xem mục 7.

---

## 5. G08.4 — Máy tính phí. CHỈ DỰ THẢO NỘI BỘ

**Không phát hành hoá đơn điện tử pháp lý. Không tự trừ tiền. Không nối cổng thanh toán.**
Trong mã không có một lệnh gọi mạng nào.

- Mỗi dòng `du_thao_hoa_don` có `la_du_thao=1` và cột `nhan_phap_ly` ghi **trên chính dòng dữ
  liệu** (không chỉ trên giao diện):
  > BẢN NHÁP NỘI BỘ — KHÔNG PHẢI HOÁ ĐƠN. Không có giá trị pháp lý, không phải chứng từ thuế,
  > không trừ tiền tự động.
  `admin/billing.js` **từ chối hiển thị như hoá đơn** nếu thiếu câu đó (`tomTatDuThao.canh_bao`).
- `UNIQUE (tenant_id, ky)` chặn **thu phí hai lần cho một kỳ** ở tầng CSDL. Gọi lại trả đúng
  dự thảo cũ kèm `trung=True`.
- **Phí vượt hạn mức = 0 đồng, có chủ đích.** Hệ này **chặn** khi hết hạn mức chứ không cho
  dùng quá rồi tính thêm tiền. Muốn bán phần vượt thì cần **đơn giá do anh Thành chốt**; G08
  không tự bịa đơn giá nào (§12 chống bịa). Lý do ghi thẳng trong payload
  (`ly_do_khong_thu_vuot`).

### 5.1 Nâng/hạ gói — phần kỳ dở dang

**Có prorate, nhưng chỉ trên DỰ THẢO, không thu và không hoàn tiền tự động.** Kỳ có nhiều
chặng gói thì tiền chia theo **số ngày** từng gói có hiệu lực, dựng từ `dang_ky_lich_su`.

`chia_tien_theo_ngay(gia, so_ngay, so_ngay_ky)` trả `(so_tien, phan_du)` với bất biến
**`so_tien * so_ngay_ky + phan_du == gia * so_ngay`**. Phần dư làm tròn **không biến mất**: nó
đi vào cột `phan_du_bo_dong` của dự thảo (§16: "không bao giờ để phần dư biến mất").
Ca `test_e1` kiểm bất biến trên **620 bộ số** (5 giá × 4 độ dài kỳ × mọi số ngày);
`chia_deu` kiểm `sum(phan) == tong` trên 25 bộ số.

**Đo thật** (`test_f2`): tenant `free` ngày 1–10, `pro` từ ngày 11, kỳ 31 ngày →
hai chặng, `so_ngay` 10 + 21 = 31, tổng tiền **< 999 000 đ** (không trả cả tháng gói `pro` cho
hơn nửa kỳ), và tổng tiền các chặng bằng đúng `tien_goi_dong`.

### 5.2 Hạ gói khi đã dùng QUÁ hạn mức gói mới

**Không im lặng xoá dữ liệu vượt hạn mức.** Hai đường, cả hai đo được:

1. **Mặc định: CHẶN.** `doi_goi` ném `HaGoiVuotHanMuc` kèm `.vuot` nói rõ vượt cái gì, bao
   nhiêu, trần mới là bao nhiêu. Gói **không đổi** (ca `test_c2`: 3 nhân viên, hạ về `free`
   (2 nhân viên) → bị chặn, gói vẫn `pro`).
2. **`cho_phep_vuot=True`: vẫn hạ, nhưng không xoá gì.** Phần vượt ghi vào
   `dang_ky_lich_su.vuot_json`. Dữ liệu cũ **giữ nguyên** (ca `test_c3` đếm lại sau khi hạ: vẫn
   4 nhân viên). Phần vượt **tự nguội theo kỳ**: bộ đếm đang lớn hơn trần nên câu
   `UPDATE … WHERE so_luong+? <= tran` không cộng thêm được; nhân viên / kết nối hãng vượt số
   thì bị chặn **thêm mới**, không ai bị gỡ (ca `test_c4` đo
   `billing.kiem_han_muc_nhan_vien` ném `VuotHanMuc` sau khi hạ).

### 5.3 Tạm ngưng đăng ký

`tam_ngung` → mọi thao tác **có tính phí** bị chặn với mã **403** (`DangKyTamNgung`), **không**
402 "cần trả tiền"; dữ liệu và sổ sự kiện **không bị xoá**; `mo_lai` cho chạy tiếp từ đúng bộ
đếm cũ (ca `test_e1`, `test_e2`).

---

## 6. G08.5 — Giao diện `admin/billing.js`

Theo đúng khuôn `admin/logic.js`: **không DOM, không fetch, không sinh HTML**, UMD nạp được ở
cả trình duyệt (`window.VIPBILLING`) và Node. `admin/` **không có thư mục con**.

7 màn: danh sách gói · chi tiết đăng ký · bảng mức dùng · cảnh báo sắp hết hạn mức · lịch sử
tính phí · dự thảo hoá đơn · quản trị gói (nền tảng).

Bốn luật đã cài vào chính logic giao diện:

- **Tiền thập phân thì BÁO LẠ, không tự làm tròn** (`dinhDangDong(1234.5).la === true`). Làm
  tròn im lặng là cách một đồng lệch đi mà không ai thấy.
- **`tran = null` hiện là "Trần do nơi khác quyết"**, không vẽ ô vô hạn.
- **Bảng mức dùng hiện cả `nguon_do` và `nguon_tran` lên giao diện**, không chỉ trong mã.
- **Dự thảo thiếu nhãn pháp lý thì không được hiện như hoá đơn** — trả `canh_bao` để
  `admin.js` dựng khối lỗi; và không có nút thanh toán nào.

**Đo thật:** 20 phép kiểm Node chạy trên **payload thật** sinh từ `usage.trang_thai_han_muc` /
`usage.lap_du_thao` của một CSDL thử (không phải dữ liệu bịa theo giả định của bộ thử —
memory "dữ liệu mẫu phải soi dữ liệu thật"):

```
NODE: 20 phep kiem, 0 hong
```

Lệnh đã chạy nằm ở mục 9.3. **Chưa làm:** chưa cắm `billing.js` vào `admin/index.html` và
`admin/admin.js` — hai file đó thuộc AG-04/AG-00, không phải của tôi (§22).

---

## 7. VIỆC CẦN AG-00 LÀM — ba bản vá `app/billing.py` + một route

### 7.1 🔴 `billing.kiem_va_tang_ai` CÒN ĐỌC-RỒI-GHI — đã đo được lọt

Đây là **cùng một lỗi đã vá cho `kiem_va_tang_don` ở đợt 2**, còn nguyên ở hàm bên cạnh. Theo
CLAUDE.md §12.2: *"một cấu trúc hỏng LẦN THỨ HAI theo cùng một kiểu thì ĐỔI CẤU TRÚC"*.

**Phép đo** (ad-hoc, trên CSDL thử, MacBook, 15/10/2026): 40 lượt × 16 luồng tranh 1 suất
cuối, trần `free` = 20 lượt AI:

```
40 lan x 16 luong, tran=20: so lan VUOT tran = 30, so_ai lon nhat do duoc = 35
```

**30/40 lượt vượt trần, cao nhất 35 trên trần 20.** Phạm vi của con số này: đường gọi **trực
tiếp** `billing.kiem_va_tang_ai` (đúng đường `server.py` đang dùng), trên SQLite WAL, một tiến
trình, 16 thread. Ngoài phạm vi: nhiều tiến trình, PostgreSQL.

> Ca `test_d12` trong bộ thử của tôi đo **1/8 luồng qua, không vượt trần** — vì đường qua
> `usage.ghi_su_kien` giữ `csdl.khoa_ghi` suốt lượt gọi nên nó tình cờ che được khe hở. **Hai
> con số không mâu thuẫn, chúng đo hai đường khác nhau.** Nói "0 vượt trần" mà không nêu đường
> nào là đúng dạng §12.1 luật 5.

**Bản vá đề xuất** (nguyên văn, cùng khuôn `kiem_va_tang_don`):

```python
def kiem_va_tang_ai(tenant_id):
    """Vượt hạn mức AI của gói → chặn. NGUYÊN TỬ — trần nằm trong WHERE của MỘT UPDATE.

    Bản cũ đọc `usage_hien_tai` rồi mới `_tang`: đo 15/10/2026 trên CSDL thử, 40 lượt × 16
    luồng tranh 1 suất cuối (trần 20) → 30/40 lượt VƯỢT trần, cao nhất 35/20. Cùng lỗi đã vá
    cho `kiem_va_tang_don` ở r35.
    """
    goi = goi_cua_tenant(tenant_id)
    tran = goi["han_muc_ai_thang"]
    thang = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        kn.execute("INSERT OR IGNORE INTO usage_thang (tenant_id, thang) VALUES (?,?)",
                   (tenant_id, thang))
        cur = kn.execute(
            "UPDATE usage_thang SET so_ai=so_ai+1"
            " WHERE tenant_id=? AND thang=? AND so_ai+1 <= ?", (tenant_id, thang, tran))
        duoc = cur.rowcount == 1
        kn.commit()
    if not duoc:
        u = usage_hien_tai(tenant_id)
        raise VuotHanMuc(
            f"đã dùng {u['so_ai']}/{tran} lượt AI của gói {goi['ten']} tháng này")
```

Sửa xong thì `test_d12` sẽ đo `qua=1, vuot_tran=0` ở **cả hai** đường; ca đó không khẳng định
chiều nào nên **không hỏng** khi vá.

### 7.2 🟡 `billing.goi_cua_tenant` không thấy PHIÊN BẢN đã ghim

`goi_cua_tenant` đọc hạn mức **hiện tại** từ `goi_dich_vu`. Nên chốt chặn thật (`kiem_va_tang_don`,
`kiem_va_tang_ai`, `kiem_han_muc_nhan_vien`, `kiem_han_muc_tai_khoan_hang`) **không** tôn trọng
phiên bản tenant đã ghim: phát hành v2 rồi có ai sửa `goi_dich_vu` thì tenant ghim v1 bị áp số
mới. **Đây là giới hạn còn lại của G08.1**, và tôi không vá được từ ngoài vì `billing.py` là
file của AG-00.

**Bản vá đề xuất** — một lớp mỏng, giữ nguyên chữ ký và vẫn chạy khi G08 chưa bật:

```python
def goi_cua_tenant(tenant_id):
    """Gói đang áp cho tenant. Ưu tiên PHIÊN BẢN đã ghim ở `dang_ky` (G08).

    Ảnh chụp `goi_phien_ban` là hạn mức tenant đã thoả thuận; `goi_dich_vu` chỉ là hạn mức
    HIỆN TẠI của gói. Đọc `goi_dich_vu` ở đây làm mọi lần sửa hạn mức gói thành một lần đổi
    hồi tố, lặng lẽ, với mọi tenant đang chạy gói đó.
    """
    r = csdl.mot(
        "SELECT v.goi_id id, v.ten ten, v.gia_thang_dong gia_thang, v.han_muc_don_thang,"
        " v.han_muc_ai_thang, v.so_nhan_vien, v.so_tai_khoan_hang, v.phien_ban"
        " FROM dang_ky d JOIN goi_phien_ban v"
        "   ON v.goi_id=d.goi_id AND v.phien_ban=d.goi_phien_ban"
        " WHERE d.tenant_id=? AND d.trang_thai<>'da_huy'", (tenant_id,))
    if r:
        return r
    return csdl.mot(
        "SELECT g.* FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id WHERE t.id=?",
        (tenant_id,))
```

Lưu ý khi vá: bảng `dang_ky`/`goi_phien_ban` chỉ có sau migration v8, nên phải để lượt đọc
thứ nhất **chịu được bảng chưa tồn tại** (bắt `sqlite3.OperationalError` → đi nhánh cũ), hoặc
cắm sau khi v8 đã chạy. `thu_saas.py` 19 ca vẫn đạt với nhánh cũ.

### 7.3 🟡 Route platform đổi gói đang đi sau lưng `dang_ky`

`PUT /api/v2/platform/tenants/{id}` (và đường tạo tenant) `UPDATE tenants SET goi_id` trực
tiếp → `dang_ky` không biết, lịch sử không có dòng nào, và hai nguồn nói hai câu khác nhau.
**Đề xuất:** route đó gọi `goi_dich_vu.doi_goi(tenant_id, goi_id, boi=nc.user_id)` (nó tự đồng
bộ `tenants.goi_id`, tự ghi lịch sử, tự chặn hạ gói khi đang vượt). Trong khi chờ, phép đo
`goi_dich_vu.doi_soat_goi(tenant_id)` **phát hiện** được lệch — ca `test_c4c` canh rằng phép đo
đó thật sự thấy, không phải phép đo vô dụng.

### 7.4 🟢 (Tuỳ chọn) cho `don_hang.gui_don` ghi qua sổ sự kiện

Hiện `gui_don` gọi thẳng `billing.kiem_va_tang_don`, nên `su_kien_dung` không phủ đơn. Nếu
muốn sổ sự kiện là sổ đầy đủ (và có `idem_key` chống thu hai lần cho lượt gửi lại timeout):
`usage.ghi_su_kien(tenant_id, "don_thang", 1, idem_key=f"don-{don_id}", tham_chieu=f"don:{don_id}")`.
**Tôi không đổi `don_hang.py`** (của AG-02 ORDERS đợt trước / AG-00 hợp nhất). Việc này thay
đổi hành vi `hoan_don` nên cần AG-00 quyết: hoàn suất thì sự kiện xử lý sao (xoá, hay ghi
sự kiện đảo như §17 FinancialEntry). **Tôi không tự chọn.**

---

## 8. Bảng route cần AG-00 cắm

`tenant_id` **luôn** lấy từ phiên (`nc.tenant_id`), **không** từ body — §1 hợp đồng.

| Method | Đường | Quyền | Gọi hàm |
|---|---|---|---|
| GET | `/api/v2/billing/goi` | `tenant.billing.xem` | `goi_dich_vu.danh_sach_goi()` |
| GET | `/api/v2/billing/dang-ky` | `tenant.billing.xem` | `goi_dich_vu.dang_ky_hien_tai` + `han_muc_hieu_luc` |
| GET | `/api/v2/billing/muc-dung?ky=` | `tenant.billing.xem` | `usage.trang_thai_han_muc(tenant_id, ky)` |
| GET | `/api/v2/billing/canh-bao` | `tenant.billing.xem` | `usage.canh_bao_sap_het(tenant_id)` |
| GET | `/api/v2/billing/lich-su` | `tenant.billing.xem` | `goi_dich_vu.lich_su` + `goi_dich_vu.nhat_ky` |
| GET | `/api/v2/billing/du-thao?ky=` | `tenant.billing.xem` | `usage.doc_du_thao` / `danh_sach_du_thao` |
| POST | `/api/v2/billing/du-thao` | `tenant.billing.xem` *(xem ghi chú)* | `usage.lap_du_thao(tenant_id, ky, boi)` |
| GET | `/api/v2/billing/bao-cao?ky=` | `tenant.billing.xem` | `usage.bao_cao_dung(tenant_id, ky)` |
| POST | `/api/v2/billing/usage` | quyền của nghiệp vụ gọi nó | `usage.ghi_tu_yeu_cau(nc.tenant_id, body)` |
| POST | `/api/v2/platform/goi/phien-ban` | `platform.goi.doi` | `goi_dich_vu.phat_hanh_phien_ban` |
| POST | `/api/v2/platform/tenants/{id}/doi-goi` | `platform.goi.doi` | `goi_dich_vu.doi_goi` |
| POST | `/api/v2/platform/tenants/{id}/tam-ngung` | `platform.goi.doi` | `goi_dich_vu.tam_ngung` / `mo_lai` |
| GET | `/api/v2/platform/billing/doi-soat/{id}` | `platform.goi.doi` | `goi_dich_vu.doi_soat_goi` + `usage.doi_soat_su_kien` |

**Ghi chú về quyền cần AG-00 quyết (tôi KHÔNG tự quyết):** `POST /billing/du-thao` lập một
bản nháp có số tiền. Quyền `tenant.billing.xem` là quyền **xem** — dùng nó cho một lệnh GHI là
nới quyền một cách im lặng. Đề xuất thêm `tenant.billing.lap_du_thao` (hoặc giới hạn cho
`platform.goi.doi`). Trong khi chờ, **đừng cắm route này**.

**Ánh xạ lỗi → HTTP** (cần cắm ở `_api_*`; không kế thừa `billing.VuotHanMuc` nên không tự ra 402):

| Lỗi | HTTP | Vì sao |
|---|---|---|
| `billing.VuotHanMuc` | 402 | đã có ở `server.py` — hết hạn mức gói là chuyện trả tiền |
| `usage.DangKyTamNgung` (`.ma=403`) | 403 | tạm ngưng **không phải** mời nâng gói |
| `goi_dich_vu.HaGoiVuotHanMuc` (`.ma=409`) | 409 | xung đột trạng thái, trả kèm `.vuot` cho giao diện |
| `goi_dich_vu.LoiGoi` / `usage.LoiUsage` (`.ma`) | theo `.ma` (400/404) | dùng `e.ma` như `gioi_han.VuotHanMucNhap` |

---

## 9. Nghiệm thu — lệnh đã chạy và output thật

### 9.1 Bộ thử mới của G08

```
$ python3 app/thu/thu_goi_dich_vu.py
Ran 37 tests in 0.007s
OK

$ python3 app/thu/thu_usage.py
Ran 41 tests in 0.086s
OK
```

Phủ đúng chín mục nghiệm thu chỉ thị yêu cầu:

| Mục nghiệm thu | Ca |
|---|---|
| đo mức dùng | `A_DoMucDung` a1–a6 |
| chặn hạn mức | `B_ChanHanMuc` b1–b9 |
| hạn mức khi chạy đồng thời | `D_NguyenTu` d1, d6, d9 (+ `C_KiemChinhPhepDo` c1 kiểm chính phép đo) |
| nâng gói | `C_DoiGoi` c1, c4b, c6 |
| hạ gói | `C_DoiGoi` c2, c3, c4 |
| tính phí | `F_TinhPhi` f1, f2, f3, f10 |
| sự kiện dùng trùng | `D_NguyenTu` d3, d4, d5 |
| tính phí chéo tenant | `F_TinhPhi` f6 (+ `b3`, `d6`) |
| tạm ngưng đăng ký | `E_TamNgung` e1, e2 |

### 9.2 Bộ thử CÓ TỪ TRƯỚC — vẫn đạt, không ca nào đổi

```
thu_saas         Ran 19 tests  OK
thu_gioi_han     Ran 34 tests  OK
thu_don_hang     Ran 63 tests  OK
thu_bao_mat      Ran 57 tests  OK
thu_webhook      Ran 68 tests  OK
thu_nhap_file    Ran 21 tests  OK
thu_g01_g02      Ran 21 tests  OK
thu_g03          Ran 53 tests  OK
thu_tich_hop     Ran  6 tests  OK
thu_qa_soat      Ran 30 tests  OK
thu_qa2_soat     Ran 49 tests  OK (skipped=1)
```

Tổng **421 ca Python có từ trước đạt** + **78 ca mới** = **499 ca Python**.

**Phạm vi — cái NẰM NGOÀI phép đo này** (§12.1 luật 5):
- `app/thu/thu_e2e.py` **chưa chạy** (cần `chay_e2e.sh` dựng máy chủ) — không đưa vào con số nào.
- **56 phép kiểm Node** của `admin/logic.js` và **36 phép kiểm HTTP frontend** của các đợt
  trước **chưa chạy lại** trong lượt này; tôi không đổi file nào của chúng, nhưng **chưa đo**
  nên không khẳng định.
- Con số "563 phép kiểm" ở hợp đồng là tổng của bốn nhóm; lượt này tôi chỉ đo nhóm Python +
  nhóm Node của riêng `billing.js`.
- Mọi phép đo trên **SQLite WAL, một tiến trình, MacBook Pro**. Chưa đo nhiều tiến trình,
  chưa đo PostgreSQL.

### 9.3 Node — `admin/billing.js` trên payload thật

```
$ node -e '<20 phép kiểm, nạp payload sinh từ usage.trang_thai_han_muc / lap_du_thao>'
NODE: 20 phep kiem, 0 hong
```

Phủ: 8 dòng hạn mức · `api_thang` 9/10 ra `sap_het` và `"90 %"` · `tran=null` ra
`khong_ro` (không phải vô hạn) · định dạng `299.000 đ` · tiền thập phân bị gắn cờ `la` ·
`chuTyLe(9050) === "90,50 %"` · dự thảo thật không cảnh báo, dự thảo thiếu nhãn thì cảnh báo ·
trạng thái lạ gắn cờ `la` · 11 route đều ghi `CHỜ BACKEND` · 7 màn.
**Phép kiểm `kiemTruocKhiGoi` trong lượt đo đó rỗng** (tenant mẫu không vượt hạn mức nào), nên
nhánh "có vượt" của hàm đó chỉ được đo **phía Python** (`test_c2`). Ghi ra chứ không gộp vào
con số "0 hỏng" như thể đã phủ.

---

## 10. `DDL_G08` — nguyên văn, và xác nhận an toàn

Hằng `DDL_G08` nằm ở đầu `app/goi_dich_vu.py`. **Xác nhận bằng ca thử `F_DDL.test_f1`,
không bằng mắt:**

- Không `ALTER`, không `DROP`, không `DELETE`, không `UPDATE `, không `INSERT ` trong `DDL_G08`.
- Mọi `CREATE TABLE` đều là `CREATE TABLE IF NOT EXISTS`; mọi `CREATE INDEX`/`CREATE UNIQUE
  INDEX` đều `IF NOT EXISTS`.
- **Không đổi kiểu cột nào**, vì không có câu nào sửa bảng đang có. Mọi tiền là `INTEGER`
  (ca `test_a2`, `test_f10` đọc `PRAGMA table_info`).
- **Không đụng ba dòng gói đang chạy.** `goi_dich_vu` chỉ bị `SELECT`. Ca `test_f4` canh ba mã
  `free`/`basic`/`pro` còn đó; ca `test_a8` dựng gói thứ tư rồi so **từng cột** của ba gói cũ
  trước/sau — khác một chữ là hỏng.
- `goi_dich_vu` được tham chiếu bằng `REFERENCES goi_dich_vu(id)` (khoá ngoài, chỉ đọc).

```sql
-- Ảnh chụp hạn mức + giá của một gói tại một thời điểm. KHÔNG BAO GIỜ sửa một dòng đã có:
-- đổi hạn mức = thêm dòng phiên bản mới. Đây là thứ giữ cho hạn mức không đổi hồi tố.
CREATE TABLE IF NOT EXISTS goi_phien_ban (
  goi_id             TEXT    NOT NULL REFERENCES goi_dich_vu(id),
  phien_ban          INTEGER NOT NULL,
  ten                TEXT    NOT NULL,
  gia_thang_dong     INTEGER NOT NULL,            -- ĐỒNG, INTEGER (§16)
  han_muc_don_thang  INTEGER NOT NULL,
  han_muc_ai_thang   INTEGER NOT NULL,
  so_nhan_vien       INTEGER NOT NULL,
  so_tai_khoan_hang  INTEGER NOT NULL,
  han_muc_api_thang  INTEGER NOT NULL DEFAULT 0,  -- 0 = chưa áp trần (xem GIA_TRI_KHONG_TRAN)
  ghi_chu            TEXT,
  tao_boi            INTEGER,
  tao_luc            TEXT    NOT NULL,
  PRIMARY KEY (goi_id, phien_ban)
);

-- Đăng ký của một tenant. GHIM (goi_id, goi_phien_ban) — đây là "thoả thuận" của tenant đó.
CREATE TABLE IF NOT EXISTS dang_ky (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
  goi_id         TEXT    NOT NULL REFERENCES goi_dich_vu(id),
  goi_phien_ban  INTEGER NOT NULL,
  trang_thai     TEXT    NOT NULL DEFAULT 'dang_hoat_dong', -- dang_hoat_dong|tam_ngung|da_huy
  ky_bat_dau     TEXT    NOT NULL,                          -- YYYY-MM
  ky_ket_thuc    TEXT,                                      -- NULL = còn hiệu lực
  tao_luc        TEXT    NOT NULL,
  cap_nhat_luc   TEXT,
  FOREIGN KEY (goi_id, goi_phien_ban) REFERENCES goi_phien_ban(goi_id, phien_ban)
);
-- Một tenant chỉ được MỘT đăng ký còn sống. Ràng buộc ở CSDL, không phải phép kiểm trong mã.
CREATE UNIQUE INDEX IF NOT EXISTS ux_dang_ky_song
  ON dang_ky(tenant_id) WHERE trang_thai <> 'da_huy';

-- Lịch sử đổi gói. CHỈ GHI THÊM. Dữ liệu vượt hạn mức khi hạ gói ghi vào `vuot_json`,
-- KHÔNG xoá dữ liệu nào (§19 luật thùng rác + "đừng im lặng xoá").
CREATE TABLE IF NOT EXISTS dang_ky_lich_su (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
  dang_ky_id      INTEGER REFERENCES dang_ky(id),
  loai            TEXT    NOT NULL,   -- kich_hoat|nang_goi|ha_goi|doi_phien_ban|tam_ngung|mo_lai|huy
  tu_goi          TEXT, tu_phien_ban INTEGER,
  den_goi         TEXT, den_phien_ban INTEGER,
  tu_gia_dong     INTEGER, den_gia_dong INTEGER,
  vuot_json       TEXT,               -- hạn mức đang bị vượt lúc hạ gói (ghi ra, không xoá dữ liệu)
  ly_do           TEXT,
  boi             INTEGER,
  luc             TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_dkls_tenant ON dang_ky_lich_su(tenant_id, id);

-- Hạn mức RIÊNG cho một tenant (nâng/hạ lẻ không cần phát hành gói mới). Không bắt buộc.
CREATE TABLE IF NOT EXISTS han_muc_rieng (
  tenant_id  INTEGER NOT NULL REFERENCES tenants(id),
  loai       TEXT    NOT NULL,
  gia_tri    INTEGER NOT NULL,
  ly_do      TEXT,
  boi        INTEGER,
  luc        TEXT    NOT NULL,
  PRIMARY KEY (tenant_id, loai)
);

-- Sổ SỰ KIỆN SỬ DỤNG (§20 UsageEvent). `UNIQUE(tenant_id, idem_key)` là ràng buộc CSDL.
CREATE TABLE IF NOT EXISTS su_kien_dung (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  loai         TEXT    NOT NULL,
  so_luong     INTEGER NOT NULL,
  idem_key     TEXT    NOT NULL,
  nguon        TEXT    NOT NULL,      -- he_thong|nguoi|hang
  tham_chieu   TEXT,
  ky           TEXT    NOT NULL,      -- YYYY-MM, chốt lúc ghi
  tao_luc      TEXT    NOT NULL,
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_skd_ky ON su_kien_dung(tenant_id, ky, loai);

-- Bộ đếm sử dụng cho những loại mà KHÔNG module nào khác đang đếm. Cộng bằng MỘT `UPDATE`
-- có trần trong `WHERE`. Loại nào đã có bộ đếm ở nơi khác thì KHÔNG đếm lại ở đây
-- (xem LOAI_HAN_MUC: `nguon_dem`) — hai bộ đếm cho một việc là hai bộ sẽ lệch nhau.
CREATE TABLE IF NOT EXISTS bo_dem_dung (
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  ky           TEXT    NOT NULL,
  loai         TEXT    NOT NULL,
  so_luong     INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT,
  PRIMARY KEY (tenant_id, ky, loai)
);

-- Kỳ tính phí. `trang_thai='dong'` = đã lập dự thảo, không nhận thêm thay đổi tính phí.
CREATE TABLE IF NOT EXISTS ky_tinh_phi (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
  ky          TEXT    NOT NULL,
  bat_dau     TEXT    NOT NULL,
  ket_thuc    TEXT    NOT NULL,
  trang_thai  TEXT    NOT NULL DEFAULT 'mo',    -- mo | dong
  tao_luc     TEXT    NOT NULL,
  dong_luc    TEXT,
  UNIQUE (tenant_id, ky)
);

-- DỰ THẢO hoá đơn — BẢN NHÁP NỘI BỘ. KHÔNG phải hoá đơn pháp lý, KHÔNG trừ tiền.
-- `UNIQUE(tenant_id, ky)` chặn thu phí hai lần cho cùng một kỳ ở tầng CSDL.
CREATE TABLE IF NOT EXISTS du_thao_hoa_don (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
  ky             TEXT    NOT NULL,
  dang_ky_id     INTEGER REFERENCES dang_ky(id),
  la_du_thao     INTEGER NOT NULL DEFAULT 1,     -- luôn 1; có ca thử canh
  nhan_phap_ly   TEXT    NOT NULL,               -- câu cảnh báo in trên chính dự thảo
  tien_goi_dong  INTEGER NOT NULL,
  tien_vuot_dong INTEGER NOT NULL DEFAULT 0,
  tong_dong      INTEGER NOT NULL,
  phan_du_bo_dong INTEGER NOT NULL DEFAULT 0,    -- phần dư làm tròn — ghi ra, không để mất im lặng
  chi_tiet_json  TEXT    NOT NULL,
  trang_thai     TEXT    NOT NULL DEFAULT 'nhap', -- nhap | da_gui_xem | huy
  tao_boi        INTEGER,
  tao_luc        TEXT    NOT NULL,
  UNIQUE (tenant_id, ky)
);

-- Nhật ký tính phí. CHỈ GHI THÊM.
CREATE TABLE IF NOT EXISTS nhat_ky_tinh_phi (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id  INTEGER REFERENCES tenants(id),
  ky         TEXT,
  hanh_dong  TEXT NOT NULL,
  ket_qua    TEXT NOT NULL DEFAULT 'thanh_cong',
  chi_tiet   TEXT,
  boi        INTEGER,
  luc        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_nktp_tenant ON nhat_ky_tinh_phi(tenant_id, id);
```

**Một chỗ G08 CÓ ghi vào bảng đang chạy — nói rõ ra:** `goi_dich_vu._dong_bo_tenant_goi` chạy
`UPDATE tenants SET goi_id=? … WHERE id=? AND goi_id<>?` khi kích hoạt hoặc đổi gói. Đây là
ghi một **dòng dữ liệu** (đúng đường route platform đang dùng), **không** đổi schema, và
**không** chạm `goi_dich_vu`. Lý do bắt buộc phải có: `billing.py` lấy gói qua `tenants.goi_id`,
nên nếu `doi_goi` chỉ sửa `dang_ky` thì **hạ gói trên giấy mà chốt chặn thật vẫn dùng gói cũ**
— phát hiện bằng ca `test_c4` lúc viết bộ thử, không phải bằng suy luận.

---

## 11. Giới hạn còn lại + rủi ro cố ý bỏ qua (§12.1: rủi ro không ghi là rủi ro bị bỏ quên)

| # | Giới hạn / rủi ro | Mức | Đã làm gì / cần ai |
|---|---|---|---|
| 1 | `kiem_va_tang_ai` còn đọc-rồi-ghi — **đo được 30/40 lượt vượt trần** | 🔴 | bản vá ở 7.1, **AG-00** |
| 2 | Phiên bản gói **chưa được `billing.py` tôn trọng** → sửa `goi_dich_vu` vẫn đổi hồi tố chốt chặn | 🟡 | bản vá ở 7.2, **AG-00** |
| 3 | Route platform đổi gói đi sau lưng `dang_ky` | 🟡 | `doi_soat_goi` phát hiện; sửa ở 7.3 |
| 4 | `su_kien_dung` **không phủ** đơn gửi hãng (`gui_don` gọi thẳng `billing`) | 🟡 | `doi_soat_su_kien.ngoai_pham_vi` nói rõ; 7.4 |
| 5 | Prorate dựa trên `dang_ky_lich_su`, nên **kỳ trước khi G08 bật** tính là một chặng duy nhất | 🟢 | ghi trong docstring `_chang_goi_trong_ky` |
| 6 | Hai lần đổi gói **trong cùng một ngày** → chặng rỗng bị bỏ; prorate tính theo NGÀY, không theo giờ | 🟢 | cố ý, ghi ra; tiền không mất vì chặng rỗng có 0 ngày |
| 7 | Dự thảo lập xong rồi mức dùng còn đổi được (`dong_ky` không chặn ghi usage) | 🟡 | cố ý bỏ qua: chặn ghi theo kỳ đóng cần quyết định nghiệp vụ của anh Thành. **Rủi ro: dự thảo có thể lệch với mức dùng cuối kỳ.** Lập dự thảo sau khi `dong_ky` thì hết lệch |
| 8 | `bo_dem_dung` tăng, **không có đường hoàn** (kiểu `billing.hoan_don`) | 🟡 | cố ý: hoàn suất cho `api_thang` chưa có nghiệp vụ nào cần. Thêm thì phải theo §17 (ghi sự kiện đảo, không `UPDATE` ngược) |
| 9 | Không nối cổng thanh toán, không phát hành hoá đơn pháp lý, không tự trừ tiền | ✅ | **đúng chỉ thị** — không phải thiếu sót |
| 10 | Giá gói mới: **chưa điền giá nào**; ba gói đang chạy giữ nguyên giá | ✅ | §19: giá bán do anh Thành quyết |
| 11 | Chưa cắm `billing.js` vào `admin/index.html` / `admin/admin.js` | 🟢 | hai file đó không thuộc tôi (§22) |
| 12 | Chưa chạy `thu_e2e.py`, 56 phép kiểm Node của `logic.js`, 36 phép kiểm HTTP frontend | 🟢 | không đổi file nào của chúng, nhưng **chưa đo** nên không khẳng định |
| 13 | Mọi phép đo trên SQLite WAL, **một tiến trình**, MacBook Pro | 🟡 | trần-trong-`WHERE` đúng cả khi nhiều tiến trình, nhưng **chưa đo**. PostgreSQL chưa đo |
| 14 | Quyền cho `POST /billing/du-thao` chưa có | 🟡 | dùng `tenant.billing.xem` cho một lệnh GHI là nới quyền im lặng → **AG-00 quyết**, xem mục 8 |

**Tám dòng "CHƯA ĐƯỢC CẤP QUYỀN" ở §25: G08 không chạm dòng nào.** Không gọi hãng, không nối
AI thật, không deploy, không xoay khoá, không đưa khoá API vào vault.
