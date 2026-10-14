# G10 — VIP AI BRAIN GATEWAY · BÁO CÁO NGHIỆM THU + HỢP ĐỒNG TÍCH HỢP AI

Tác tử: **AG-04 AI INTEGRATION ENGINEER** · Nhánh `agent/g10-ai` · Nền `143084b`
Ngày: **15/10/2026** · Worktree: `~/code/veh3-g10-ai`

---

## 0. ĐỌC TRƯỚC — ĐỢT NÀY KHÔNG NỐI AI THẬT

**`app/ai_gateway.py` giữ `MOCK = True`. Không ai đặt `False`.** Không một file nào của G10
gọi OpenAI / Claude / DeepSeek / VIP AI Brain hay bất kỳ API AI nào. Quyền nối thật là
**V-G10-01, CHƯA ĐƯỢC CẤP** (`SHARED_CONTRACTS` §25).

Dự án VIP AI Brain **không bị sửa, không bị đọc** trong đợt này.

Ba phép đo chứng minh, không phải lời hứa:

| Phép đo | Công cụ | Kết quả |
|---|---|---|
| Không module G10 nào `import` thư viện mạng | ca `A_CongViecMock.test_03` quét từng dòng `import`/`from` của hai file | không có `urllib`, `http.client`, `requests`, `httpx`, `socket`, `ssl`, `aiohttp`, `openai`, `anthropic`, `transport` |
| Không có URL `http(s)://` trong phần mã (ngoài chú thích) | cùng ca, quét từng dòng không phải chú thích | không có |
| `VIPAIBrainConnector` gọi vào là ném | ca `A_CongViecMock.test_02` | `ChuaCapQuyen` |

**Phạm vi của ba phép đo này** (CLAUDE.md §12.1 luật 3): chúng chỉ phủ `app/ai_job.py` và
`app/ai_validator.py`. **NẰM NGOÀI phạm vi:** `app/ai_gateway.py` (AG-00 giữ — đã đọc, nó
cũng không có lượt gọi mạng nào, nhưng đó là đo bằng mắt chứ không bằng ca thử của tôi),
`app/transport.py`, `app/adapter*.py`, và mọi module khác của repo.

---

## 1. BÀN GIAO — TÓM TẮT

| Hạng mục | Giá trị |
|---|---|
| Commit SHA (local, **KHÔNG push**) | `da401a2` (`da401a2148121b8c4f6195091b076cb02a122aa1`) |
| Số phép kiểm G10 | **87 ca, 87 đạt, 0 bỏ qua** |
| Hồi quy nền | 13 bộ thử cũ: **không ca nào hỏng** (mục 9) |
| File tôi tạo | 4 file, mục 2 |
| File của người khác tôi chạm | **không có** |
| Schema | hằng `DDL_G10` trong `app/ai_job.py`, in nguyên văn ở mục 5 |
| Route | bảng ở mục 6 — AG-00 cắm |

---

## 2. FILE ĐÃ ĐỔI — VÀ XÁC NHẬN KHÔNG CHẠM FILE NGƯỜI KHÁC

Bốn file **tạo mới**, đúng đủ quyền sở hữu AG-04 ở `SHARED_CONTRACTS` §22:

| File | Dòng | Việc |
|---|---|---|
| `app/ai_job.py` | 893 | `AIJobService` · `NhaCungCapAI` · `MockAIProvider` · `VIPAIBrainConnector` · `DDL_G10` · tối giản dữ liệu · chính sách duyệt |
| `app/ai_validator.py` | 448 | `AIResultValidator` (kiểm schema đầu ra) · quét bí mật 3 dạng · hàng rào chống tiêm prompt |
| `app/thu/thu_ai_job.py` | 1188 | 87 phép kiểm |
| `admin/ai.js` | 351 | sáu màn giao diện |

**KHÔNG chạm:** `app/ai_gateway.py` · `app/csdl.py` · `app/migrate.py` · `app/server.py` ·
`app/nhap_file.py` · `app/don_hang.py` · `docs/SHARED_CONTRACTS.md` · `app/bao_mat.py` ·
`app/quyen.py` · `app/billing.py` · `app/gioi_han.py` · `admin/admin.js` · `admin/logic.js`.
Kiểm bằng `git status --short` (mục 11).

**Một việc AG-00 phải làm ở file của mình, tôi KHÔNG tự làm:** thêm một dòng
`<script src="ai.js"></script>` vào `admin/index.html` (sau `logic.js`, trước `admin.js`).
`admin/index.html` không thuộc quyền tôi đợt này. Chưa có dòng đó thì `window.VIPAI` không
tồn tại trong trình duyệt — mã vẫn đúng, chỉ là chưa nạp.

---

## 3. G10.1 — HỢP ĐỒNG CONNECTOR

### 3.1 Nhà cung cấp AI (`NhaCungCapAI`)

```python
class NhaCungCapAI:
    ma: str                       # 'mock' | 'vip_ai_brain'
    ten: str
    phien_ban_hop_dong: str       # 'g10.v1'
    san_sang: bool
    def chay(self, loai, prompt, du_lieu_gui, tenant_id) -> dict   # kết quả THÔ
```

`tenant_id` là **tham số**, không phải biến toàn cục hay thread-local. Lý do cụ thể: lượt gọi
chạy trong một thread khác (`_chay_co_timeout`), nên thread-local sẽ về `None` **một cách im
lặng** — đúng dạng hỏng im lặng §12.2. Lỗi này đã xảy ra thật khi viết bản đầu, bộ thử bắt
được, và cách sửa là **đổi cấu trúc** (truyền tường minh) chứ không phải chép giá trị thêm
một lần.

Nhà cung cấp **không được tự khai là mình hợp lệ** — `chay_viec` tự kiểm schema (§12.1 luật 1).

### 3.2 Công việc AI (`AIJob`) — theo đúng `SHARED_CONTRACTS` §21

Mười sáu cột của §21 có đủ (ca `I_LoiVaTimeout.test_08` đối chiếu `PRAGMA table_info`). Tôi
**thêm** sáu cột, **không đổi** cột nào của §21: `loi`, `mock`, `dau_hieu_tiem`, `ms_chay`,
`batch_id`, `dong_id`.

### 3.3 Sự kiện dùng AI (`ai_su_kien`)

Mười loại: `tao` · `goi_nha_cung_cap` · `xong` · `cho_duyet` · `duyet` · `tu_choi` · `loi` ·
`timeout` · `chan_bi_mat` · `chan_lenh`. Mỗi dòng mang `so_luot_ai` — lượt tính phí của đúng
sự kiện đó. Đây là dấu vết để đối chiếu với bộ đếm hạn mức của `billing`.

### 3.4 Chính sách phê duyệt

| Loại việc | Cần người duyệt | Vì sao |
|---|---|---|
| `trich_don_tu_file` | **có** | kết quả thành dữ liệu đơn |
| `chuan_hoa_truong` | **có** | kết quả thay giá trị trường |
| `goi_y_hang` | **có** | chọn sai hãng là đơn đi sai, phải có người ký tên |
| `phat_hien_bat_thuong` | không | chỉ sinh câu nhắc để đọc |
| `giai_thich_loi_kiem` | không | chỉ sinh văn bản giải thích |
| `tom_tat_lo_import` | không | chỉ sinh câu tóm tắt |

**Một luật đè lên bảng trên:** dữ liệu vào có **dấu hiệu tiêm** thì bắt buộc người duyệt, kể
cả ba loại cuối. Dòng đó đã là dòng đáng ngờ. (Ca `E_TiemPrompt.test_04`.)

### 3.5 Hợp đồng lỗi

Ba kết cục **KHÔNG gộp**, theo đúng khuôn §4/§5 của hãng vận chuyển:

| Kết cục | `trang_thai` | Dấu vết |
|---|---|---|
| **được** | `xong` hoặc `cho_duyet` | `ra_json` + `ms_chay` |
| **từ chối** (lỗi rõ ràng, schema lệch, có bí mật, có khoá như lệnh) | `loi` | `loi` ghi nguyên văn, `ra_json` để **NULL** |
| **KHÔNG BIẾT** (hết hạn chờ) | `loi` kèm chữ "KHÔNG BIẾT" trong `loi` | sự kiện `timeout` |

Chữ "KHÔNG BIẾT" ở trong thông điệp là cố ý: một lượt hết hạn chờ **không phải** thất bại
xác nhận, và lẫn hai thứ là cách nhanh nhất để sau này ai đó coi nó là "đã thử, không được".

---

## 4. G10.2 — LUỒNG ĐẦU VÀO

```
TẢI FILE → IMPORT ENGINE G05 → CHUẨN HOÁ → AI GATEWAY → GỢI Ý AI
         → KIỂM TRA → NGƯỜI DUYỆT → ĐƠN NHÁP G04
```

Mũi nối G05 → AI là `ai_job.vao_tu_lo_import(tenant_id, batch_id)` — **chỉ đọc**,
`tenant_id` nằm trong `WHERE`.

### Bằng chứng không có đường nào tới `createOrder`

**Bốn ca, hai loại bằng chứng độc lập** (`D_KhongTaoDonThat`):

1. **Chạy thật, gài bẫy** (`test_01`): thay `don_hang.tao_don`, `gui_don`, `duyet_don`,
   `sua_don`, `luu_mat_hang`, `huy_don` bằng hàm **nổ**; rồi chạy trọn vòng: tạo lô CSV thật
   → `vao_tu_lo_import` → `tao_viec` → `chay_viec` → `de_xuat_cho_nguoi_duyet` →
   `duyet_viec`, cộng một việc `tom_tat_lo_import`. **Không bẫy nào nổ.**
2. **Bẫy có nổ thật không** (`J_CaThuTuHong.test_05`): gọi thẳng vào bẫy, nó nổ. Không có ca
   này thì ca 1 có thể xanh vì bẫy chết, không vì mã sạch.
3. **Đếm đơn trước/sau duyệt** (`test_02`): duyệt gợi ý AI không sinh thêm một đơn nào.
4. **Chốt cấu trúc** (`test_03`, `test_04`): mã của G10 chỉ dùng **đúng ba thứ** của
   `don_hang` — `kiem_don`, `vai_tro_trong_tenant`, `LoiNghiepVu`. `test_04` so bằng
   `assertEqual` trên tập hợp, nên **thêm** một hàm `don_hang.*` nào khác là ca này hỏng
   ngay, không cần ai nhớ luật.

**Ranh giới cứng:** đơn nháp chỉ sinh ra ở `nhap_file.duyet_batch` (G05) khi **người dùng tự
bấm**. `admin/ai.js` vẽ bước cuối "Đơn nháp" **luôn là chưa xong** kèm câu *"Trợ lý AI không
tạo đơn"* — ca `K_GiaoDien.test_07` canh điều đó.

---

## 5. G10.3 — CÁCH LY TENANT + HẰNG `DDL_G10`

### 5.1 Sáu thứ mỗi yêu cầu AI phải có

| Thứ | Lấy từ đâu |
|---|---|
| danh tính đã xác thực | `user_id` — tham số, do `server.py` lấy từ `bao_mat.ngu_canh(token)` |
| ngữ cảnh tenant | `tenant_id` — **tham số, từ PHIÊN**, không bao giờ từ body |
| mã công việc | `ai_job.id` + `idem_key` (`UNIQUE(tenant_id, idem_key)`) |
| phạm vi quyền | `tenant.ai.dung` để dùng, `tenant.don.duyet` để duyệt — tra bảng `role_permissions` |
| ngữ cảnh mức dùng | `billing.kiem_va_tang_ai` + `ai_su_kien.so_luot_ai` |
| ngữ cảnh audit | `csdl.audit(...)` + `ai_su_kien` cho từng bước |

### 5.2 `tenant_id` từ phiên — và cái xảy ra khi body tự khai

`_don_vao()` **GỠ HẲN** mọi khoá tự khai định danh/quyền khỏi `vao`:
`tenant_id` · `user_id` · `token` · `role` · `platform_role` · `quyen` · `nha_cung_cap` ·
`mock`. Không chỉ "bỏ qua" — gỡ, để không có đường nào ở dưới đọc lại được.

Và **ghi lại** mưu toan đó vào audit (`ai_bo_khoa_tu_khai`), gồm cả giá trị `tenant_id` mà
body khai, để sau còn đối chiếu. Ca `C_CachLyTenant.test_01` kiểm cả hai nửa: giá trị không
được dùng, **và** dấu vết có thật.

### 5.3 Dữ liệu tenant A không ra tenant B

| Ca | Kiểm |
|---|---|
| `C_02` | `lay_viec`, `ds_viec`, `chay_viec`, `de_xuat_cho_nguoi_duyet` của B đều không với tới việc của A |
| `C_03` | B không duyệt được việc của A; việc của A giữ nguyên `cho_duyet` |
| `C_04` | gắn dấu `XIN-CHAO-TENANT-A-9f3c` vào dữ liệu A, rồi tìm nó trong kết quả B, trong `ds_viec(B)`, `ds_su_kien(B)`, `thong_ke_dung(B)` — **không có** |
| `C_05` | lô import của A không đọc được từ B |
| `C_06` | `tenant_id` kiểu lạ (`None`, `"1"`, `0`, `-3`, `True`, dict) đều bị chặn |

Cưỡng chế bằng **câu truy vấn** (`tenant_id` luôn trong `WHERE`), không bằng một phép `if` ở
tầng trên.

### 5.4 Kết quả AI không tự cấp quyền

Ca `C_07` đẩy bốn tài liệu dạng lệnh qua đường kết quả:
`{"grant_role":"PLATFORM_OWNER"}` · `{"action":"delete_all"}` ·
`{"tool_call":{"name":"createOrder"}}` · `{"quyen":["tenant.don.duyet"]}`.
Cả bốn: job thành `loi`, `ra_json` **NULL** (không lưu), và sau đó `tenant_memberships.role`
cùng `users.platform_role` **không đổi**.

Hai lớp chặn độc lập: danh sách trắng schema đầu ra, và `loc_khoa_lenh` (quét 40 khoá nghi
lệnh ở mọi độ sâu, chuẩn hoá `grant-role`/`grant role`/`GRANT_ROLE` về cùng một khoá — nếu
không chuẩn hoá thì đổi một dấu gạch là lách được).

### 5.5 `DDL_G10` — nguyên văn

AG-00 chép khối này vào `csdl.SCHEMA` + migration **v8**. Toàn bộ là `IF NOT EXISTS`, không
có `ALTER` (ca `I_07` canh điều đó), nên chạy lại vô hại. `ai_job.bao_dam_bang()` chạy đúng
khối này để mã và bộ thử chạy được **trước** khi AG-00 làm migration.

```sql
CREATE TABLE IF NOT EXISTS ai_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  loai TEXT NOT NULL,
  -- moi · dang_chay · xong · loi · cho_duyet · tu_choi  (SHARED_CONTRACTS §21)
  trang_thai TEXT NOT NULL DEFAULT 'moi',
  vao_json TEXT NOT NULL,
  ra_json TEXT,
  nha_cung_cap TEXT NOT NULL,
  phien_ban_hop_dong TEXT NOT NULL,
  do_tin_cay INTEGER,                              -- 0..100, số NGUYÊN (§16: cấm float)
  can_nguoi_duyet INTEGER NOT NULL DEFAULT 1,
  duyet_boi INTEGER REFERENCES users(id),
  duyet_luc TEXT,
  idem_key TEXT NOT NULL,
  tao_luc TEXT NOT NULL,
  xong_luc TEXT,
  -- các cột dưới đây THÊM so với §21 (không đổi cột nào của §21):
  loi TEXT,                                        -- lý do khi trang_thai='loi'
  mock INTEGER NOT NULL DEFAULT 1,                 -- kết quả có phải mô phỏng không
  dau_hieu_tiem TEXT,                              -- chỉ số mẫu tiêm khớp được, dạng JSON
  ms_chay INTEGER,                                 -- thời gian chạy, mili-giây
  batch_id INTEGER REFERENCES import_batch(id),    -- lô import nguồn (nếu có)
  dong_id INTEGER REFERENCES import_dong(id),      -- dòng import nguồn (nếu có)
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_aijob_tenant ON ai_job(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_aijob_tt ON ai_job(tenant_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_aijob_batch ON ai_job(batch_id);
CREATE TABLE IF NOT EXISTS ai_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  job_id INTEGER REFERENCES ai_job(id),
  user_id INTEGER REFERENCES users(id),
  loai_su_kien TEXT NOT NULL,   -- tao · goi_nha_cung_cap · xong · loi · timeout
                                -- · cho_duyet · duyet · tu_choi · chan_bi_mat · chan_lenh
  so_luot_ai INTEGER NOT NULL DEFAULT 0,           -- lượt tính phí của sự kiện này
  chi_tiet TEXT NOT NULL DEFAULT '',
  luc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_aisk_tenant ON ai_su_kien(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_aisk_job ON ai_su_kien(job_id);
```

`UNIQUE(tenant_id, idem_key)` là **ràng buộc CSDL**, không phải phép kiểm trong mã — ca
`A_05` chèn thẳng câu `INSERT` thứ hai và khẳng định CSDL ném `IntegrityError`. Đúng nếp §13
và §20.

---

## 6. BẢNG ROUTE — AG-00 CẮM

Tôi không ghi `app/server.py`. Chín đường dưới đây là đề xuất, **cùng một bảng** với
`admin/ai.js` (`API_CHO_BACKEND`) — ca `K_GiaoDien.test_15` đối chiếu hai bản để chúng không
lệch nhau.

| Phương thức | Đường | Quyền | Trần tần suất | Gọi hàm |
|---|---|---|---|---|
| POST | `/api/v2/ai/job` | `tenant.ai.dung` | `ai.goi` | `ai_job.tao_viec(tenant_id, nc.user_id, loai, vao, idem_key, batch_id, dong_id)` |
| POST | `/api/v2/ai/job/<id>/chay` | `tenant.ai.dung` | `ai.goi` | `ai_job.chay_viec(tenant_id, id)` |
| GET | `/api/v2/ai/job` | `tenant.ai.dung` | mặc định | `ai_job.ds_viec(tenant_id, trang_thai, loai)` |
| GET | `/api/v2/ai/job/<id>` | `tenant.ai.dung` | mặc định | `ai_job.de_xuat_cho_nguoi_duyet(tenant_id, id, nguoi_gui)` |
| POST | `/api/v2/ai/job/<id>/duyet` | `tenant.don.duyet` | mặc định | `ai_job.duyet_viec(tenant_id, nc.user_id, id)` |
| POST | `/api/v2/ai/job/<id>/tu-choi` | `tenant.don.duyet` | mặc định | `ai_job.tu_choi_viec(tenant_id, nc.user_id, id, ly_do)` |
| GET | `/api/v2/ai/su-kien` | `tenant.audit.xem` | mặc định | `ai_job.ds_su_kien(tenant_id, job_id)` |
| GET | `/api/v2/ai/thong-ke` | `tenant.billing.xem` | mặc định | `ai_job.thong_ke_dung(tenant_id)` |
| GET | `/api/v2/ai/lo/<batch_id>` | `tenant.import.ghi` | mặc định | `ai_job.vao_tu_lo_import(tenant_id, batch_id)` |

**Ba lưu ý khi cắm:**

1. **`tenant_id` truyền từ `nc.tenant_id`**, tuyệt đối không từ body. Tầng nghiệp vụ đã gỡ
   khoá tự khai, nhưng đó là lớp thứ hai; lớp đầu là chỗ cắm này.
2. **Ba đường AI cũ (`/api/v2/ai/chuan-hoa-dia-chi`, `/phat-hien-bat-thuong`, `/goi-y-hang`)
   giữ nguyên, đừng nối lại qua tầng job.** Hai đường song song cho cùng một việc là hai
   đường sẽ lệch nhau (§12.2: lọc một chỗ, không lọc hai chỗ). `admin/ai.js` ghi rõ nó
   **không** dùng ba đường cũ.
3. **Trần `ai.goi` đã có** trong `gioi_han.py` (120/60s theo tenant và theo định danh) — dùng
   lại, đừng thêm trần thứ hai. Hai đường ghi (`/job`, `/job/<id>/chay`) nên dùng nó; các
   đường đọc để trần mặc định.

---

## 7. G10.4 — RIÊNG TƯ & BẢO MẬT

### 7.1 TRƯỜNG NÀO ĐƯỢC GỬI / KHÔNG GỬI — kèm lý do

Danh sách **TRẮNG** theo từng loại việc (`ai_job.TRUONG_GUI`). Đây là **ngoại lệ chính đáng**
mà §12.2 đã nêu sẵn: quên khai một trường ⇒ trường đó không được gửi ⇒ kết quả AI kém hơn,
nhưng dữ liệu khách không rò. Dùng danh sách đen mà quên chặn một trường ⇒ số điện thoại thật
rời khỏi hệ ⇒ **hỏng thật, không thu lại được**. Bỏ sót ở đây phải là AN TOÀN.

| Loại việc | Trường ĐƯỢC gửi |
|---|---|
| `trich_don_tu_file` | `nguoi_nhan_ten` · `nguoi_nhan_dia_chi` · `hang_hoa` · `so_luong` · `khoi_luong_gram` · `ghi_chu` · `sdt_che` · `cod_khoang` · `stt` |
| `chuan_hoa_truong` | `truong` · `gia_tri` (đúng một trường, không gì khác) |
| `goi_y_hang` | `khoi_luong_gram` · `tinh` · `cod_khoang` |
| `phat_hien_bat_thuong` | `khoi_luong_gram` · `cod_khoang` · `so_luong` · `gia_tri_khoang` |
| `giai_thich_loi_kiem` | `loi` · `canh_bao` (chỉ danh sách lỗi, **không một trường dữ liệu khách nào**) |
| `tom_tat_lo_import` | `ten_file` · `so_dong` · `so_valid` · `so_invalid` · `so_needs_review` · `ly_do_pho_bien` (chỉ số đếm) |

**KHÔNG GỬI, ở mọi loại việc:**

| Trường | Vì sao |
|---|---|
| **Số điện thoại đầy đủ?** → **KHÔNG.** | Dữ liệu cá nhân nhận dạng trực tiếp. AI không cần nó để chuẩn hoá địa chỉ hay chọn hãng. Chỉ gửi dạng che `090****444` (3 số đầu + 3 số cuối) để người duyệt đối chiếu được dòng mà không ai gọi được số. |
| **COD?** → **KHÔNG số chính xác.** | Dữ liệu tài chính của khách. Phát hiện bất thường chỉ cần **ĐỘ LỚN**, nên gửi khoảng: `0` · `<=500k` · `<=2tr` · `<=5tr` · `>5tr` · `am` · `khong_ro`. |
| `gia_tri_khai` | Cùng lý do với COD — gửi khoảng. |
| `nguoi_gui_*` | Thông tin của chính doanh nghiệp, không cần cho sáu việc đã khai. |
| credentials hãng · khoá · token · mật khẩu · hash | Cấm tuyệt đối (§14, §21). Có phép quét canh. |
| `tenant_id` · `user_id` · token phiên | Không giúp gì cho sáu việc, và gửi ra ngoài là mở đường tương quan giữa các tenant. |

**Địa chỉ đầy đủ?** → **CÓ, cho đúng hai việc**: `trich_don_tu_file` và `chuan_hoa_truong` —
hai việc này **không làm được** mà thiếu nó. `goi_y_hang` chỉ nhận **TỈNH** (phần sau dấu
phẩy cuối), vì chọn hãng không cần số nhà. Bốn việc còn lại không nhận địa chỉ. Đây là đánh
đổi có chủ ý, ghi ra để kiểm lại được.

**Đo trên prompt THẬT, không trên lời hứa** (ca `F_07`): dựng prompt cho năm loại việc với
SĐT `0904444444` và COD `9123456` trong đầu vào, rồi tìm hai chuỗi đó trong prompt — **không
có**. Và `goi_y_hang` chỉ thấy `"Hà Nội"`, không thấy `"4 Hẻm A"`.

**Một hệ quả phải nói rõ:** vì SĐT và COD không rời máy, kết quả `trich_don_tu_file` **không
thể** chứa chúng. Nếu lấy kết quả AI làm bản nháp thì phép kiểm luôn báo "thiếu SĐT" — một
**lỗi GIẢ do chính phép tối giản sinh ra**. Vì vậy `de_xuat_cho_nguoi_duyet` **gộp** gợi ý AI
lên **dòng gốc nằm ở máy** trước khi kiểm; màn hình đánh dấu trường nào do AI đổi
(`truong_tu_ai`). Dữ liệu cá nhân vẫn chưa từng rời máy, mà phép kiểm vẫn chạy trên dữ liệu
đủ.

### 7.2 Kiểm dữ liệu vào · kiểm schema dữ liệu ra

- **Vào:** loại việc phải nằm trong `LOAI_VIEC`; `tenant_id` phải là số nguyên dương; khoá tự
  khai bị gỡ; mọi ô văn bản qua `lam_sach_van_ban`.
- **Ra:** `ai_validator.kiem_ra(loai, ra)` — **danh sách trắng** khoá, kiểm kiểu từng ô, trần
  cỡ (256 KiB), trần độ sâu (6 tầng), trần số phần tử (5 000), `enum` đúng danh mục, `bool`
  không lọt qua ô "số nguyên", `float` không lọt qua ô "số nguyên".
- **Lệch schema ⇒ `loi`, không phải `xong` với dữ liệu méo** (§21). Ca `B_10` kiểm: trạng
  thái `loi`, **và** `ra_json` là `NULL` — kết quả méo không được lưu.
- **Hai chốt thêm ở tầng kiểm:** kết quả tự khai `mock=False` bị **từ chối** đợt này (dấu
  hiệu có đường nối thật đã mở mà chưa được cấp quyền), và `phien_ban_hop_dong` lạ bị từ chối.

Tầng kiểm nằm ở **file riêng** và **không import `ai_job`** — cố ý, một chiều, không vòng:
thứ dùng để kiểm chứng phải độc lập với thứ được kiểm chứng (§12.1 luật 1).

### 7.3 Chống tiêm prompt

**Chặn bằng CẢ BA lớp**, và đây **không** phải cái §12.2 cấm. §12.2 cấm hai **bộ lọc cùng
loại** chồng nhau rồi lệch nhau; ba lớp dưới đây làm **ba việc khác nhau** ở **ba thời điểm
khác nhau**, và không lớp nào giả định lớp kia đã chạy:

1. **Ngăn cách rõ đầu vào + đánh dấu nguồn.** Dữ liệu người dùng nằm giữa hàng rào có nhãn
   `<<<DU_LIEU_KHONG_TIN_CAY … DU_LIEU_KHONG_TIN_CAY>>>`. Câu dặn hệ thống là **hằng số của
   mã**, không bao giờ ghép từ dữ liệu. Chuỗi hàng rào xuất hiện **trong** dữ liệu thì bị vô
   hiệu hoá ở **hai chỗ** (`lam_sach_van_ban` cho từng ô, và một lượt thay chuỗi trên thân
   JSON trong `dung_prompt`) nên dữ liệu không thoát rào được. Ký tự điều khiển bị bỏ (chúng
   dùng để che chỉ thị khỏi mắt người soát); thẻ phân vai của mô hình chat (`<|im_start|>`,
   `<system>`) bị vô hiệu hoá.
2. **Kiểm schema đầu ra.** Dù mô hình có bị dụ, kết quả lệch schema vẫn bị chặn.
3. **Kết quả là dữ liệu.** `loc_khoa_lenh` phát hiện khoá trông như lệnh ở mọi độ sâu, kể cả
   khi nó lọt qua lớp 1.

Ngoài ba lớp trên, `dau_hieu_tiem` (10 mẫu) **ghi nhận** để bắt buộc người duyệt — đây là
phép **ghi nhận**, không phải phép chặn.

#### Phạm vi ca thử chống tiêm — nói chính xác (CLAUDE.md luật "0")

**Đã thử: 14 mẫu tiêm**, mỗi mẫu qua **hai đường**:
(a) đưa thẳng vào `vao` của công việc AI (ca `E_02`), và
(b) đi qua một **file CSV thật** của import engine G05 rồi mới vào AI (ca `E_03`).

14 mẫu: bỏ qua chỉ thị (tiếng Việt) · bỏ qua chỉ thị (tiếng Anh) · `### HỆ THỐNG:` ·
`SYSTEM:` · `disregard the prior rules` · `<|im_start|>system` · `</system><system>` ·
`{"tool_call":{"name":"createOrder"}}` · SQL `DROP TABLE` · giả vai `Assistant:` ·
`developer:` · **thoát hàng rào** (`DU_LIEU_KHONG_TIN_CAY>>>`) · ký tự điều khiển `\x00\x1b` ·
`pretend to be the system`.

**Cái được chứng minh:** 14 mẫu này được coi là **văn bản** (nằm trong hàng rào, không thoát
rào), kết quả vẫn đúng schema, vẫn tự khai `mock`, `loc_khoa_lenh` sạch, không vai trò nào
đổi, và việc **bị bắt buộc** qua người duyệt.

**NẰM NGOÀI phạm vi đã thử — không suy rộng:**

- tiêm bằng **ngôn ngữ khác** (Trung, Nhật, Ả Rập) và bằng **chữ đồng hình Unicode**;
- tiêm **nhiều lượt** (ghép mảnh qua nhiều công việc liên tiếp);
- tiêm qua **ảnh / PDF scan** — import engine đã chặn ở tầng dưới (batch → `FAILED`), nên
  chưa tới được tầng AI, nhưng đó là phép chặn của G05, không phải của tôi;
- **tiêm vào CHÍNH một mô hình thật** — **không đo được**, vì chưa có mô hình thật
  (V-G10-01). Phép thử ở đây chứng minh phần **CẤU TRÚC** (hàng rào + kiểm schema), **KHÔNG**
  chứng minh một mô hình thật sẽ không bị dụ. Đây là **giới hạn cốt lõi của đợt này** và
  phải đọc lại trước khi mở `MOCK=False`.

Ca `E_06` kiểm mặt còn lại: bốn chuỗi lành (tên hàng, ghi chú giao hàng, địa chỉ) **không**
bị báo động giả.

### 7.4 Cấm bí mật trong prompt

`ai_validator.quet_bi_mat(prompt)` quét **ba dạng**: thô · hex · base64. Chạy **trước** lượt
gọi — quét sau khi đã gửi thì không cứu được gì.

Có bí mật ⇒ **KHÔNG gọi nhà cung cấp**, job thành `loi`, sự kiện `chan_bi_mat`, và **mức dùng
không tăng**. Ca `F_05` kiểm cả bốn điều đó bằng cách gài bẫy vào `MockAIProvider.chay`.

Ca `F_06`: audit và `ai_su_kien` ghi **mô tả**, không ghi **giá trị** — gài một chuỗi đặc
trưng rồi tìm nó trong 20 dòng audit gần nhất + toàn bộ sự kiện của job: **không có** (§8).

**Phạm vi phép quét** (§12.1 luật 3): phủ 24 từ khoá, 5 mẫu cấu trúc (bản mã `v3$` của vault,
PEM, hash mật khẩu, khoá `sk-…`, JWT), và chuỗi hex ≥ 20 ký tự / base64 ≥ 16 ký tự giải ra
chứa một trong hai nhóm trên. 12 mẫu bí mật × 3 dạng = **36 phép đo** (ca `F_01`–`F_03`).
**NẰM NGOÀI:** bí mật không mang từ khoá nào và không khớp mẫu nào (ví dụ mật khẩu người dùng
tự đặt như `trungthu2026`), bí mật mã hoá/nén nhiều lớp, bí mật tách rời qua nhiều lượt gọi,
từ khoá bằng ngôn ngữ khác.

**Vì thế đây KHÔNG phải phép chứng minh "prompt không có bí mật".** Chốt gốc là danh sách
trắng `TRUONG_GUI`; phép quét là **lưới an toàn thứ hai**, không phải lưới duy nhất.

**Đánh đổi đã chọn, ghi ra:** ngưỡng hex hạ từ 32 xuống 20 ký tự vì ngưỡng cao bỏ lọt
`X-API-KEY: zzz` (28 ký tự hex) — đo thật lúc viết bộ thử. Ngưỡng thấp hơn ⇒ khả năng **báo
động giả** cao hơn; báo động giả ở đây làm job thành `loi` để người xem, **mất tiện, không
mất an toàn**.

### 7.5 Phê duyệt tường minh · chi phí · lỗi · timeout

- **Phê duyệt:** `duyet_viec` **không áp kết quả vào đâu cả** — nó chỉ ghi nhận người đã xem
  và đồng ý. Sau đó người dùng tự nhập/xác nhận qua màn đơn hàng, **cùng đường mọi người dùng
  khác đi, cùng mọi phép kiểm, cùng mọi dòng audit**. Ca `G_01`–`G_07`.
- **Mức dùng:** mỗi lượt gọi nhà cung cấp đúng **một** lượt. Ba việc đi qua `ai_gateway`
  (`chuan_hoa_truong`, `goi_y_hang`, `phat_hien_bat_thuong`) đã được `ai_gateway._goi()` tính,
  nên `chay_viec` **không tính lần nữa** — đếm hai lần là báo mức dùng sai, mà mức dùng sai
  thì hạn mức gói chặn oan người đang dùng đúng. Ca `H_01` đo năm loại việc, mỗi loại tăng
  đúng 1. Ca `H_02`: `tao_viec` không tính lượt. Ca `H_03`: vượt hạn mức thì chặn và job thành
  `loi`.
- **Chi phí:** `thong_ke_dung()["chi_phi_dong"]` là **`None`** kèm lý do *"chưa có đơn giá nhà
  cung cấp (V-G10-01 chưa cấp) — không bịa số"*. Giao diện hiện đúng lý do đó, **không hiện
  "0 đ"** — "0 đ" là một con số, và một con số bịa thì tệ hơn một ô trống. Ca `H_04` và
  `K_09`.
- **Lỗi:** nhà cung cấp nổ ⇒ `loi` kèm tên ngoại lệ; trả về **không phải dict** (chuỗi, danh
  sách, số) ⇒ `loi` có thông điệp, **không** vọt thành HTTP 500. Lỗi này bộ thử bắt được thật
  (ca `I_04`), không phải đề phòng trên giấy.
- **Timeout:** ca `I_03` đo **bằng đồng hồ**: trần 0,3 giây cho một nhà cung cấp ngủ 5 giây —
  trả về trong dưới 3 giây, không chờ 5 giây.

---

## 8. G10.5 — TƯƠNG THÍCH VIP AI BRAIN

### 8.1 Khảo sát hợp đồng kết nối: KHÔNG CÓ

Khảo sát ngày 15/10/2026: dự án này **không được cung cấp hợp đồng kết nối nào** của VIP AI
Brain — không endpoint, không dạng xác thực, không schema request/response. Theo chỉ thị
G10.5 và §12 (chống bịa): **không bịa URL, không bịa dạng request.** Vì vậy
`VIPAIBrainConnector` **không có một đường mạng nào**.

### 8.2 Bốn thứ đã tạo

| Tên | Ở đâu | Trạng thái |
|---|---|---|
| `VIPAIBrainConnector` | `app/ai_job.py` | **giao diện RỖNG CÓ CHỦ Ý** — gọi vào là `ChuaCapQuyen`. Đây không phải mã chưa viết xong; đây là cái chốt. |
| `MockAIProvider` | `app/ai_job.py` | chạy hoàn toàn trong tiến trình, sáu loại việc |
| `AIJobService` | `app/ai_job.py` | `tao_viec` · `chay_viec` · `duyet_viec` · `tu_choi_viec` · `lay_viec` · `ds_viec` · `ds_su_kien` · `thong_ke_dung` · `de_xuat_cho_nguoi_duyet` · `vao_tu_lo_import` |
| `AIResultValidator` | `app/ai_validator.py` → `kiem_ra` | danh sách trắng + trần cỡ/sâu + quét khoá lệnh |

### 8.3 ⚠️ CẦN GÌ ĐỂ NỐI VIP AI BRAIN THẬT — danh sách cho anh Thành

**Sáu nhóm. Thiếu bất kỳ mục nào thì vẫn là `ChuaCapQuyen`.**

1. **Endpoint**
   - scheme + host + path đầy đủ, cho **từng** môi trường (thử / thật);
   - có cần đi qua proxy / mạng riêng không; dải IP cần mở nếu có.
2. **Xác thực**
   - loại: Bearer token · HMAC chữ ký · mTLS · khoá trong header riêng — **tên header chính
     xác**;
   - **ai cấp credentials**, cấp cho ai, và credentials là **của nền tảng** hay **của từng
     tenant** (quyết định này đổi cả thiết kế: của từng tenant thì phải đi qua
     `bao_mat.ma_hoa_cred` như credentials hãng, và chỉ bốn hàm của §14 được chạm nó);
   - cơ chế **xoay khoá** và cách hệ biết khoá đã đổi.
3. **Schema REQUEST** cho từng loại việc trong `ai_validator.LOAI_VIEC` (6 loại).
4. **Schema RESPONSE + bảng mã lỗi**
   - mã nào là **được**, mã nào là **từ chối**, mã nào là **KHÔNG BIẾT** — ba kết cục này
     **không được gộp** (khuôn §4/§5). Thiếu bảng này thì không biết lượt nào được thử lại,
     và thử lại một lượt "từ chối" là tốn tiền vô ích còn không thử lại một lượt "không biết"
     là mất việc.
5. **Hợp đồng vận hành**
   - trần tần suất (lượt/giây, lượt/phút) để tôi đặt đúng `gioi_han`;
   - **timeout cam kết** của nhà cung cấp — và timeout phải đặt ở **tầng HTTP của chính lượt
     gọi** (`timeout=` của socket), không phải lớp thread ở `_chay_co_timeout`;
   - hạn mức tháng;
   - **đơn giá** để `thong_ke_dung()["chi_phi_dong"]` có số thật thay vì `None`.
6. **Cơ sở xử lý dữ liệu cá nhân** — *mục này không phải thủ tục giấy tờ, nó quyết định có
   được gửi hay không*
   - ai là bên xử lý dữ liệu;
   - dữ liệu lưu ở đâu, **bao lâu**;
   - có dùng để **huấn luyện** không;
   - có hợp đồng xử lý dữ liệu không;
   - **phê duyệt của anh Thành** cho đúng cấu hình đó.

Dữ liệu khách hàng chỉ được gửi tới nhà cung cấp khi **có cơ sở xử lý VÀ cấu hình đã được
phê duyệt**. Hiện **chưa có cả hai**, nên mọi thứ là mock.

### 8.4 Khi nối thật thì phải làm gì — việc của AG-00, không phải của tôi

1. Đặt `ai_gateway.MOCK = False` (**chỉ AG-00**, và chỉ sau khi đủ sáu nhóm trên).
2. **Gỡ chốt ở `ai_validator.kiem_ra`** đang từ chối kết quả `mock=False` — chốt đó cố ý ở đó
   để đợt này không ai vô tình mở đường.
3. Hiện thực `VIPAIBrainConnector.chay` **với timeout ở tầng HTTP**.
4. Chạy lại toàn bộ 87 ca; ít nhất ba ca sẽ hỏng **đúng như thiết kế** (`A_02`, `A_03`,
   `B_07`) — chúng là cái canh V-G10-01, hỏng là dấu hiệu khoá đã mở, không phải lỗi.
5. **Chạy lại bộ ca tiêm prompt trên mô hình THẬT.** Mục 7.3 đã nói rõ: bộ ca hiện tại chứng
   minh cấu trúc, không chứng minh mô hình.

---

## 9. NGHIỆM THU — SỐ CA VÀ OUTPUT THẬT

### 9.1 Bộ thử G10

```
$ cd ~/code/veh3-g10-ai && python3 app/thu/thu_ai_job.py
...
Ran 87 tests in 1.113s

OK (skipped=1)
```

Lượt chạy trên là lượt trước khi có tài liệu này, nên `K_GiaoDien.test_15` (đối chiếu bảng
route với **chính tài liệu này**) bị bỏ qua. Lượt chạy **cuối**, sau khi tài liệu đã có:

```
$ python3 -W error::ResourceWarning app/thu/thu_ai_job.py
Ran 87 tests in 1.124s

OK
```

**87 ca, 87 đạt, 0 bỏ qua.**

Phân bố theo tám mục nghiệm thu của chỉ thị:

| Mục nghiệm thu | Lớp ca | Số ca |
|---|---|---|
| ca thử công việc AI mock | `A_CongViecMock` | 8 |
| kiểm schema | `B_KiemSchema` | 12 |
| cách ly tenant | `C_CachLyTenant` | 8 |
| không có đường tới `createOrder` | `D_KhongTaoDonThat` | 4 |
| ca thử tiêm prompt | `E_TiemPrompt` | 6 (× 14 mẫu × 2 đường) |
| cấm bí mật trong prompt | `F_CamBiMat` | 8 (× 12 mẫu × 3 dạng) |
| bắt buộc phê duyệt | `G_PheDuyet` | 7 |
| đo mức dùng | `H_MucDung` | 5 |
| xử lý lỗi + timeout | `I_LoiVaTimeout` | 8 |
| **kiểm chính bộ kiểm** | `J_CaThuTuHong` | 6 |
| giao diện (Node) | `K_GiaoDien` | 15 |

### 9.2 Kiểm chính bộ kiểm — §12.1 luật 1

**Thứ dùng để kiểm chứng phải được kiểm trước khi tin.** Lớp `J_CaThuTuHong` **gỡ từng bản
vá** rồi khẳng định ca thử tương ứng bắt được:

| Ca | Gỡ gì | Khẳng định |
|---|---|---|
| `J_01` | gỡ `KHOA_NGHI_LENH` **và** nới schema cho `grant_role` | `kiem_ra` **cho qua** ⇒ hai lớp chặn là thật, không phải trùng hợp; bật lại thì chặn ngay |
| `J_02` | gỡ `KHOA_VAO_CAM` | `tenant_id` tự khai **còn lại** trong `vao_json` ⇒ ca `C_01` đang kiểm đúng thứ nó nói |
| `J_03` | gỡ hết từ khoá + mẫu bí mật | `quet_bi_mat` trả rỗng ⇒ phép quét dựa vào đúng hai bảng đó |
| `J_04` | gỡ `lam_sach_van_ban` | **hàng rào VẪN giữ** (còn một lượt thay chuỗi trong `dung_prompt`) — ca này khẳng định **đúng điều đó**, không khẳng định ngược |
| `J_05` | gọi thẳng vào bẫy của `D_01` | bẫy **nổ** ⇒ `D_01` xanh vì mã sạch, không vì bẫy chết |
| `J_06` | trần timeout với hàm ngủ 2 giây | cắt được; và hàm nhanh thì trả đúng giá trị |

Ngoài ra, **ba lỗi thật** đã bị chính bộ thử này bắt trong lúc viết, không phải tìm ra bằng
đọc lại:

1. `tenant_id` dùng thread-local trong khi nhà cung cấp chạy ở **thread khác** ⇒ `None` im
   lặng. Sửa bằng **đổi cấu trúc**: truyền tường minh.
2. `dict(kq)` nổ `ValueError` khi nhà cung cấp trả về chuỗi/danh sách ⇒ sẽ thành HTTP 500.
   Sửa thành lỗi nghiệp vụ có thông điệp.
3. Ngưỡng quét hex 32 ký tự **bỏ lọt** `X-API-KEY: zzz`. Hạ xuống 20, ghi đánh đổi.

### 9.3 Hồi quy nền — không ca nào hỏng

```
thu_ai_job.py        Ran 87 tests   OK (skipped=1)
thu_bao_mat.py       Ran 57 tests   OK
thu_don_hang.py      Ran 63 tests   OK
thu_g01_g02.py       Ran 21 tests   OK
thu_g03.py           Ran 53 tests   OK
thu_gioi_han.py      Ran 34 tests   OK
thu_nhap_file.py     Ran 21 tests   OK
thu_qa2_soat.py      Ran 49 tests   OK (skipped=1)
thu_qa_soat.py       Ran 30 tests   OK
thu_saas.py          Ran 19 tests   OK
thu_tich_hop.py      Ran  6 tests   OK
thu_webhook.py       Ran 68 tests   OK

$ sh app/thu/chay_e2e.sh      → KẾT QUẢ: 41/41 phép đo đạt · [e2e] mã thoát 0
$ sh thu_frontend/chay.sh     → HAI TẦNG TỰ ĐỘNG ĐẠT (56 node + 36 HTTP)
```

**Phạm vi câu "không ca nào hỏng"** (luật "0" của §12.1): đo bằng `python3 <từng file>` trên
**macOS, Python 3.9**, CSDL **tạm riêng** (`VIP_HUB_DATA` trỏ thư mục `mktemp -d`), schema
**v7**. **NẰM NGOÀI phạm vi:** tầng 3 của frontend (trình duyệt thật — DOM, CSS, bố cục, tràn
ngang) **chưa chạy**, và `thu_e2e.py` chỉ chạy qua `chay_e2e.sh` (gọi trực tiếp thì thiếu
`VIP_HUB_DATA`, đó là thiết kế của nó, không phải lỗi).

### 9.4 CSDL thử — không chạm CSDL thật

Mỗi lượt chạy đặt `VIP_HUB_DATA` trỏ một thư mục `mktemp -d` riêng. **Không lượt nào chạy
`migrate.py` lên `app/du-lieu/` của repo chính** (§24).

---

## 10. GIỚI HẠN CÒN LẠI — RỦI RO CỐ Ý BỎ QUA PHẢI GHI RA

| # | Giới hạn | Mức | Cách vá đúng |
|---|---|---|---|
| 1 | **Ca thử tiêm prompt chứng minh CẤU TRÚC, không chứng minh MÔ HÌNH.** Chưa có mô hình thật để thử. | **cao** — đây là giới hạn cốt lõi | Chạy lại bộ 14 mẫu (và mở rộng) trên mô hình thật **trước** khi tin, ngay sau khi V-G10-01 được cấp |
| 2 | **Timeout bằng thread không giết được thread.** Hết hạn chờ thì job thành `loi`, nhưng thread kia vẫn chạy tới khi tự xong. Với mock (thuần CPU, không mạng) thì vô hại. | trung bình | Khi nối thật, đặt timeout ở **tầng HTTP của chính lượt gọi**, không ở lớp thread. Đã ghi vào mục 8.3 nhóm 5 |
| 3 | **Không có `billing.hoan_ai`.** Lượt gọi tính phí **trước**, nhà cung cấp lỗi thì **không hoàn** suất. Mock không tốn tiền nên chưa đau; nối thật thì một chuỗi lỗi ăn mất hạn mức tháng. | trung bình | **Đề xuất AG-00** thêm `billing.hoan_ai(tenant_id)` theo đúng khuôn `hoan_don` (một `UPDATE` có trần trong `WHERE`, xét `rowcount`, không cho xuống âm). Tôi **không** tự viết vì `billing.py` là của AG-00 |
| 4 | **`admin/index.html` chưa nạp `ai.js`.** File đó không thuộc quyền tôi. | thấp | AG-00 thêm một dòng `<script src="ai.js">` |
| 5 | **Chín route chưa cắm.** `server.py` của AG-00. | thấp | Bảng ở mục 6 |
| 6 | **`DDL_G10` chưa vào migration v8.** Hiện `bao_dam_bang()` tự tạo bảng. | thấp | AG-00 chép khối mục 5.5 vào `csdl.SCHEMA` + migration |
| 7 | **Tầng 3 giao diện (trình duyệt thật) CHƯA chạy** cho màn AI. Phủ: logic nhãn/quyết định. Không phủ: DOM, CSS, bố cục, tràn ngang trên điện thoại. | trung bình | V-13906-01 (thư viện kiểm giao diện tự động) **chưa cấp**; trong lúc chờ thì soát bằng mắt theo `docs/FRONTEND_AUTOMATION.md` tầng 3 |
| 8 | **Phép quét bí mật có ngưỡng thấp hơn ⇒ báo động giả cao hơn.** | thấp | Chọn có chủ ý: báo động giả làm job thành `loi` để người xem — mất tiện, không mất an toàn. Theo dõi tỉ lệ `chan_bi_mat` sau khi chạy thật |
| 9 | **`quet_bi_mat` không phủ bí mật không mang từ khoá** (mật khẩu tự đặt kiểu `trungthu2026`). | thấp | Chốt gốc là danh sách trắng `TRUONG_GUI` — mật khẩu không có đường nào vào prompt. Phép quét là lưới thứ hai |
| 10 | **`_tinh_tu_dia_chi` lấy phần sau dấu phẩy cuối làm "tỉnh"** — thô, sai với địa chỉ không có dấu phẩy. | thấp | Cố ý: nó **không gửi số nhà ra ngoài**, đó là mục tiêu. Không đoán thêm; không có thì trả rỗng |
| 11 | **Không đo được `ai_gateway.py` bằng ca thử của tôi** (AG-00 giữ). Đã đọc bằng mắt: không có lượt gọi mạng. | thấp | AG-00 thêm ca canh trong `thu_tich_hop.py` nếu muốn khoá cứng |
| 12 | **`do_tin_cay` của bản mô phỏng là con số VÔ NGHĨA** (35, 40, 45…). | thấp | Giao diện nói thẳng *"số này do bộ mô phỏng gán, không phải phép đo thật"* (ca `K_12`). Khi nối thật, nhà cung cấp phải nói rõ con số này nghĩa là gì |

### Đề xuất gửi AG-00 cho `app/ai_gateway.py` (tôi KHÔNG sửa)

1. **Thêm một câu canh ở đầu file**: `MOCK` đổi thành `False` thì phải có một hằng
   `DA_DUYET_NOI_THAT` do người đặt — một khoá là một khoá có thể bị sửa vô ý; hai khoá ở hai
   chỗ thì khó hơn.
2. **`phat_hien_bat_thuong` nhận khoảng COD thay vì số COD.** Hiện nó cần số chính xác, nên
   tầng job phải tự suy từ khoảng và **không dùng được** hàm đó. Nếu nó nhận
   `cod_khoang ∈ {0, <=500k, <=2tr, <=5tr, >5tr, am, khong_ro}` thì tối giản dữ liệu và chất
   lượng kết quả không còn phải đánh đổi.
3. **`_goi()` nên trả về số lượt đã tính**, để tầng job đối chiếu thay vì phải biết trước ba
   việc nào đã tính rồi (hiện biết bằng hằng `_LOI_QUA_GATEWAY` — một danh sách phải nhớ cập
   nhật, tức là một chỗ sẽ lệch).

---

## 11. BÀN GIAO — SHA VÀ TRẠNG THÁI GIT

- **Không `push`.** Commit chỉ ở local, nhánh `agent/g10-ai`.
- SHA và `git status` của lượt bàn giao: xem phần cuối báo cáo gửi AG-00 (ghi theo **lệnh
  chạy thật**, không theo trí nhớ — §12.1 luật 4).
