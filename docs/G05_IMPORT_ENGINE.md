# G05 — Import Engine (AG-04)

File sở hữu: `app/nhap_file.py` · `app/thu/thu_nhap_file.py` · tài liệu này.
Contract: `docs/SHARED_CONTRACTS.md` mục 6 (ImportBatch/ImportRow) và mục 7 (OrderDraft).

---

## 1. Máy trạng thái batch

```
UPLOADED → PARSING → VALIDATING → READY → APPROVED → PROCESSING
                                                       ├→ COMPLETED
                                                       ├→ PARTIAL_FAILED
                                                       └→ FAILED
```

Bảng chuyển hợp lệ nằm ở hằng `CHUYEN_BATCH` trong `app/nhap_file.py` — **một chỗ duy nhất**.
Mọi lượt đổi trạng thái đi qua `chuyen_batch(batch_id, moi)`; chuyển sai thứ tự thì **nổ lỗi**,
không im lặng ghi đè (trạng thái đi lùi mà không báo là hỏng im lặng — `CLAUDE.md` §12.2).

Ghi chú từng nhánh:

| Từ | Đi được tới | Vì sao |
|---|---|---|
| `UPLOADED` | `PARSING`, `FAILED` | vừa nhận file |
| `PARSING` | `VALIDATING`, `FAILED` | parse xong mới validate |
| `VALIDATING` | `READY`, `FAILED` | |
| `READY` | `READY`, `VALIDATING`, `APPROVED`, `FAILED` | sửa dòng rồi validate lại vẫn ở `READY` |
| `APPROVED` | `PROCESSING`, `FAILED` | |
| `PROCESSING` | `COMPLETED`, `PARTIAL_FAILED`, `FAILED` | |
| `COMPLETED` | `APPROVED` | duyệt lại được, nhưng **idempotent** — không nhân đôi đơn |
| `PARTIAL_FAILED` | `APPROVED`, `VALIDATING`, `READY` | sửa dòng lỗi rồi duyệt lại |
| `FAILED` | *(không đi đâu)* | parse hỏng thì không có gì để duyệt |

Trạng thái cuối sau `PROCESSING` tính từ **số dòng đếm trong CSDL**, không từ biến đếm trong
vòng lặp (§12.1 luật 4 — dữ kiện đo được thì phải lấy từ phép đo):

- `COMPLETED`: có ≥ 1 `SUCCESS`, 0 `FAILED`, 0 dòng còn việc.
- `FAILED`: không dòng nào làm được gì (ví dụ batch chỉ có `UNSUPPORTED`).
- `PARTIAL_FAILED`: còn lại.

## 2. Trạng thái dòng

`VALID INVALID READY SUBMITTED SUCCESS FAILED UNSUPPORTED NEEDS_REVIEW`

- `INVALID` — lỗi **chặn** (`kiem_dong`): thiếu trường, SĐT sai, cân nặng ≤ 0, COD âm.
- `NEEDS_REVIEW` — **cần người xem** (`canh_bao_dong` + phát hiện trùng): ô nghi công thức,
  dòng trùng trong cùng batch. Không tự tạo đơn, **không tự loại**. Người bấm
  `xac_nhan_dong()` → `READY`.
- `UNSUPPORTED` — file đọc được nhưng tầng này không đọc nổi nội dung (PDF scan).
  Batch → `FAILED` và để lại **một dòng** `UNSUPPORTED` làm dấu vết thay vì biến mất.
- Dòng được tạo đơn nháp: `VALID`, `READY`, `FAILED` (`DONG_LAM_DUOC`).

## 3. Di cư dữ liệu cũ

Giá trị batch cũ `moi` / `da_duyet_mot_phan` / `xong` **đọc được** qua
`trang_thai_batch()` (bảng `BATCH_CU`) → `READY` / `PARTIAL_FAILED` / `COMPLETED`.
Mã **không cần** migration dữ liệu để chạy; migration chỉ để làm sạch (xem mục 6).
Hàm `_ghi_trang_thai()` còn tự dò bằng `PRAGMA table_info(import_batch)` xem CSDL đã có cột
`loi` chưa, nên chạy được cả trên CSDL chưa nâng cấp schema.

## 4. Lỗ hổng đã bịt

### 4.1 CSV formula injection

Excel/LibreOffice/Google Sheets **thực thi** ô bắt đầu bằng `=` `+` `-` `@`, kể cả khi các ký
tự đó đứng sau tab/CR (bộ đọc bỏ khoảng trắng đầu). Vector thật: `=cmd|'/C calc'!A0` (DDE),
`=HYPERLINK(...)` dụ người bấm, `=WEBSERVICE(...)` gửi dữ liệu ra ngoài.

Hai lớp, **cả hai đều cần**:

1. **Phát hiện khi validate** — `rui_ro_cong_thuc()` → dòng `NEEDS_REVIEW`.
2. **Làm sạch khi xuất** — `lam_sach_o_xuat()` thêm tiền tố `'` và bỏ CR/LF.
   `xuat_csv()` là **đường ghi CSV duy nhất** trong file này và nó bắt buộc đi qua
   `lam_sach_o_xuat`, nên không có lối xuất nào quên làm sạch (§12.2: lọc một chỗ).

Số âm thuần (`-5`, `-1.5`, `+7`) **không** bị coi là rủi ro. Cố ý: nếu tính thì mọi cột
COD/tiền đều báo động giả, và cảnh báo nào cũng kêu thì người dùng học cách bỏ qua nó.

### 4.2 Giới hạn tài nguyên

Hằng số ở đầu `app/nhap_file.py` — đổi ở đó, không rải ra nơi khác:

| Hằng | Giá trị | Chặn gì |
|---|---|---|
| `GIOI_HAN_BYTE_FILE` | 10 MiB | file tải lên quá lớn |
| `GIOI_HAN_SO_DONG` | 5 000 | số dòng dữ liệu |
| `GIOI_HAN_SO_O_MOI_DONG` | 100 | số ô một dòng |
| `GIOI_HAN_DAI_O` | 10 000 | độ dài một ô |
| `ZIP_TONG_GIAI_NEN` | 64 MiB | tổng dung lượng sau giải nén của xlsx |
| `ZIP_TI_LE_TOI_DA` | 120× | tỉ lệ nén của một thành viên zip |
| `ZIP_SO_THANH_VIEN` | 300 | số file bên trong zip |
| `PDF_GIOI_HAN_CHUOI` | 200 000 | số khối văn bản rút từ PDF |

Giới hạn dòng/ô được chốt **hai lần**: trong vòng lặp `doc_csv`/`doc_xlsx` (dừng sớm, không
nạp hết vào bộ nhớ) và trong `_kiem_bang()` dùng chung cho cả ba parser — thêm parser mới
cũng không lọt.

### 4.3 Zip bomb

Đọc `file_size`/`compress_size` từ **bảng mục lục zip**, chặn theo tổng và theo tỉ lệ
**trước khi giải nén** → không bao giờ nạp quả bom vào bộ nhớ. Khi đọc thật thì vẫn
`read(ZIP_TONG_GIAI_NEN + 1)` để không tin mục lục (mục lục do kẻ gửi file viết).

### 4.4 Path traversal trong zip

`_ten_zip_an_toan()` từ chối tên tuyệt đối, `..`, và `C:\`. Tầng này **chỉ đọc theo tên**,
không ghi ra đĩa, nên traversal chưa gây hại trực tiếp — nhưng tên bẩn là dấu hiệu file dựng
để tấn công, và nếu sau này có ai thêm bước giải nén ra đĩa thì chốt đã có sẵn.
Thêm một chốt nữa: `_doc_xml_an_toan()` chỉ đọc tên **đã nằm trong tập đã kiểm**.

### 4.5 XML entity expansion (billion-laughs)

`xml.etree.ElementTree` (expat) **không** nạp entity ngoài, nhưng **có** nở entity nội bộ →
billion-laughs là thật. Chặn ở tầng byte: thấy `<!doctype` hoặc `<!entity` thì từ chối
**trước khi** đưa vào ElementTree. Không dựa vào niềm tin "ElementTree an toàn".

### 4.6 Không thực thi mã từ file tải lên

Chỉ đọc XML và văn bản thuần. Không `eval`, không nạp macro VBA (`xl/vbaProject.bin` nếu có
chỉ là một thành viên zip không ai đọc), không gọi thư viện ngoài.

## 5. OrderDraft

Import **chỉ** sinh đơn **nháp** qua `don_hang.tao_don(...)` với
`idem_key=f"import-{batch_id}-{dong_id}"`. Duyệt lại → `tao_don` trả đơn cũ (UNIQUE
`(tenant_id, idem_key)` trong CSDL), nên không nhân đôi. Tầng này **không** gọi hãng,
**không** tạo đơn vận chuyển thật, **không** tự xây Order Service (AG-03 không chạy đợt này).

Bộ thử `test_21` đo trực tiếp: đơn sinh ra có `trang_thai='nhap'`, `ma_van_don IS NULL`,
`carrier_account_id IS NULL`.

## 6. Việc cần AG-00 làm

### 6.1 Schema (`app/csdl.py` — file dùng chung, đã sửa TỐI THIỂU)

Hai thay đổi, cả hai trong `CREATE TABLE import_batch`:

1. `trang_thai TEXT NOT NULL DEFAULT 'moi'` → `DEFAULT 'UPLOADED'`
2. thêm cột `loi TEXT` (lý do khi batch ở `FAILED`)

Cộng ba dòng chú thích liệt kê giá trị hợp lệ của `import_batch.trang_thai` và
`import_dong.trang_thai`. **Không** đổi cột nào khác, **không** xoá gì.

### 6.2 Migration (MÔ TẢ, chưa sửa `app/migrate.py` — AG-01 cũng đang đụng file đó)

Lúc đo (14/10/2026, worktree `~/code/veh-import`) `import_batch` có **0 dòng**, nên CSDL mới
chỉ cần `CREATE TABLE` là đủ và mã đã chịu được CSDL chưa nâng cấp. Khi AG-00 gộp, bước
migration cần làm, theo khuôn `app/migrate.py` (sao lưu → transaction → kiểm bảo toàn số dòng):

```sql
ALTER TABLE import_batch ADD COLUMN loi TEXT;          -- bỏ qua nếu đã có
UPDATE import_batch SET trang_thai='READY'          WHERE trang_thai='moi';
UPDATE import_batch SET trang_thai='PARTIAL_FAILED' WHERE trang_thai='da_duyet_mot_phan';
UPDATE import_batch SET trang_thai='COMPLETED'      WHERE trang_thai='xong';
```

Kiểm sau migration: `COUNT(*)` của `import_batch` và `import_dong` không đổi, và
`SELECT DISTINCT trang_thai FROM import_batch` chỉ còn giá trị trong `TRANG_THAI_BATCH`.
Migration này **không bắt buộc** để mã chạy — chỉ để dọn giá trị cũ.

### 6.3 Endpoint mới (`app/server.py` — AG-04 KHÔNG sửa)

Hai hàm mới cần nối:

| Đường | Method | Hàm | Quyền đề nghị |
|---|---|---|---|
| `/api/v2/import/<batch_id>/xuat-csv` | `GET` | `nhap_file.xuat_csv(tenant_id, batch_id)` | `tenant.don.xem` |
| `/api/v2/import/dong/<dong_id>/xac-nhan` | `POST` | `nhap_file.xac_nhan_dong(tenant_id, user_id, dong_id)` | `tenant.import.ghi` |

`xuat_csv` trả **chuỗi CSV**, không phải JSON — cần `Content-Type: text/csv; charset=utf-8`
và `Content-Disposition: attachment`. Tên file tải về phải lọc, đừng ghép thẳng
`ten_file` do người dùng đặt vào header.

Endpoint cũ không đổi chữ ký: `tao_batch`, `sua_dong`, `duyet_batch` giữ nguyên tham số.
`duyet_batch` nay trả thêm khoá `trang_thai_batch` trong kết quả.

## 7. Nghiệm thu (đo ngày 14/10/2026, worktree `~/code/veh-import`, macOS, Python 3.9)

| Lệnh | Kết quả |
|---|---|
| `python3 app/thu/thu_nhap_file.py` | 21 tests, **OK** |
| `python3 app/thu/thu_g01_g02.py` | 21 tests, **OK** |
| `python3 app/thu/thu_g03.py` | 30 tests, **OK** |
| `python3 gateway/thu/thu_gateway.py` | 9 tests, **OK** |
| `python3 app/thu/thu_saas.py` | 19 tests, **1 FAIL** — `test_16_khong_dung_du_lieu_cu` |

`test_16` hỏng **không phải vì thay đổi này**: đã đo bằng `git stash` rồi chạy riêng ca đó
trên bản gốc — vẫn hỏng. Nó đòi `gateway/du-lieu/gateway.db` tồn tại, mà đường đó nằm trong
`.gitignore` nên worktree mới không có file. Ca về import của bộ thử đó
(`test_11_import_csv_va_xlsx`) **đạt**.

## 8. Giới hạn còn lại (ghi ra để không ai tưởng đã phủ hết)

- **PDF scan/OCR**: không hỗ trợ. Cố ý — không đoán nội dung ảnh.
- **PDF text**: chỉ đọc `Tj`/`TJ` không nén hoặc nén Flate, chuỗi giải mã theo `latin-1`.
  Font subset mã hoá riêng, PDF nhiều cột, bảng có ô gộp → đọc sai hoặc không đọc được.
  Chỉ nên coi PDF là đường phụ; CSV/XLSX là đường chính.
- **XLSX**: đọc **sheet đầu tiên**. Không đọc công thức đã tính (`<f>`), không đọc định dạng
  số (ngày tháng ra số serial), không đọc ô gộp, bỏ qua `xl/worksheets/sheet2+`.
- **Phát hiện trùng**: chỉ trong **cùng một batch**. Trùng với batch trước hoặc với đơn đã có
  trong `don_hang` thì **chưa** phát hiện.
- **Giới hạn ô/dòng** đo trên bảng đã parse, không đo bộ nhớ thật. File 10 MiB × 5 000 dòng
  vẫn nạp cả bảng vào RAM — chưa có đường đọc theo luồng.
- **`rui_ro_cong_thuc`** chỉ phủ `=` `+` `-` `@` ở đầu ô (và sau khoảng trắng/tab/CR). Không
  phủ DDE qua tên hàm đặt trong ô không bắt đầu bằng các ký tự đó, và không phủ công thức
  trong file **XLSX** xuất ra (tầng này chỉ xuất CSV).
- **Hạn mức gói** (`billing`) chỉ bị tính khi *gửi hãng*, không tính lúc import tạo đơn nháp —
  nên một batch 5 000 dòng tạo được 5 000 đơn nháp mà không chạm hạn mức. Cần AG-00 quyết
  có chặn ở bước import hay không.
