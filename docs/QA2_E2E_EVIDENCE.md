# QA2_E2E_EVIDENCE — AG-05, Q05 end-to-end

> **AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW** — **KHÔNG** phải independent human review.
> Xem `docs/QA2_FINDINGS.md` mục 8.

**Ngày chạy:** 15/10/2026 · **Commit:** `4016eef8d558d13049ba56a64e219c13c7f1c3f5`
**Máy chủ:** `http://127.0.0.1:8942` (cổng riêng của AG-05, tránh đụng 4 agent song song)
**CSDL THẬT:** `/Users/viporder/code/veh2-qa-verification/app/du-lieu/qa2-e2e/hub.db`
— **200.704 byte**, nằm **trong worktree này** (`.gitignore` loại `*.db` và `app/du-lieu/`, nên
file không vào git — đúng ý: CSDL không phải thứ để commit)

**Kết quả: 14/14 bước ĐẠT.**

## Mô phỏng đến đâu, thật từ đâu

| Thật | Mô phỏng |
|---|---|
| Máy chủ HTTP `app/server.py` chạy thật, định tuyến thật, middleware tenant thật | **Chỉ** lớp gọi API hãng: `adapter_jt` ở `moi_truong="mock"` — chế độ sẵn có trong mã sản phẩm, **không** vá gì để chạy lượt này |
| CSDL SQLite thật, schema v6, mọi hàng đọc lại được bằng SQL | Webhook do bộ thử tự đẩy vào — nhưng **ký bằng HMAC-SHA256 với secret thật** lấy từ `carrier_accounts`, qua đúng cửa `POST /api/v2/webhook/nhan/{ma}` |
| File `.xlsx` **thật**: zip + OOXML, 2 byte đầu là `PK`, đi qua parser thật `nhap_file` | — |
| Mã hóa AES-256-GCM thật, khóa thật ở `app/du-lieu/qa2-e2e/khoa/` | — |
| Phiên, cookie, CSRF header, RBAC tra CSDL — thật | — |

**Nguyên tắc nghiệm thu (§12.1):** không bước nào được tin chỉ vì HTTP 200. Sau **mỗi** bước,
đọc lại hàng trong CSDL và so với kết quả mong đợi. Cột "Đo được trong CSDL" dưới đây là dữ
liệu đọc ra từ `hub.db`, không phải thân phản hồi API.

---

## Bằng chứng từng bước

### 1. TẠO TENANT — PASS
`POST /api/v2/platform/tenants` bằng `PLATFORM_OWNER` → **HTTP 201**
Đo trong CSDL, bảng `tenants`:
```json
{"id": 1, "code": "e2e-dn", "ten": "Công ty E2E", "goi_id": "pro", "trang_thai": "hoat_dong"}
```

### 2. TẠO USER — PASS
`POST /api/v2/memberships` bằng `TENANT_OWNER` → **HTTP 201**
Đo trong CSDL, bảng `tenant_memberships` join `users`:
```json
{"id": 2, "role": "TENANT_STAFF", "trang_thai": "hoat_dong", "ten_dang_nhap": "e2e-staff"}
```

### 3. ĐĂNG NHẬP — PASS
`POST /api/v2/auth/dang-nhap` bằng user vừa tạo → **HTTP 200** + cookie `phien` HttpOnly.
Đo trong CSDL, bảng `sessions` (tra bằng `sha256(token)` — **token thô không được lưu**):
```json
{"user_id": 3, "active_tenant_id": 1, "thu_hoi": 0}
```
`GET /api/v2/auth/toi` → `{"vai_tro": "TENANT_STAFF", "tenant": {"id": 1, "ten": "Công ty E2E"}}`
⇒ ngữ cảnh tenant do backend tự giải, không do client khai.

### 4. UPLOAD EXCEL (.xlsx THẬT) — PASS
File 4 dòng (1 tiêu đề + 3 bản ghi), tiêu đề tiếng Việt có dấu
(`Người nhận`, `SĐT`, `Địa chỉ`, `Sản phẩm`, `Khối lượng`, `COD`) để đo luôn bộ chuẩn hoá tên cột.
`POST /api/v2/import` (base64) → **HTTP 201**

| Kiểm | Giá trị |
|---|---|
| 2 byte đầu là `PK` (zip thật, không phải CSV đổi đuôi) | **true** |
| `sha256` file (16 ký tự đầu) | `00da91dd8e39c764` |
| `import_batch` trong CSDL | `{"id": 1, "ten_file": "don-e2e.xlsx", "loai_file": "xlsx", "trang_thai": "READY", "loi": null}` |

### 5. VALIDATE IMPORT — PASS
`GET /api/v2/import/1` → **HTTP 200**, `trang_thai` batch = `READY`
Đo trong CSDL, bảng `import_dong`:
```json
[{"id": 1, "stt": 1, "trang_thai": "VALID",   "loi": null},
 {"id": 2, "stt": 2, "trang_thai": "VALID",   "loi": null},
 {"id": 3, "stt": 3, "trang_thai": "INVALID", "loi": "SĐT phải 10 số bắt đầu bằng 0"}]
```
Dòng 3 **cố ý** thiếu SĐT. Hệ bắt đúng, **không** tự đoán, **không** tự loại — dòng vẫn còn đó
để người xem, đúng luật "không tự chấp nhận thay người bấm".

### 6. DUYỆT IMPORT — PASS
`POST /api/v2/import/1/duyet` với `dong_ids` = 2 dòng `VALID` → **HTTP 200**
```json
{"SUCCESS": 2, "FAILED": 0, "bo_qua": 0, "trang_thai_batch": "PARTIAL_FAILED"}
```
Đo trong CSDL: hai dòng `VALID` → `SUCCESS` kèm `don_id` **1** và **2**; dòng `INVALID` giữ
nguyên, `don_id = null`.
`PARTIAL_FAILED` là **đúng**, không phải lỗi: batch còn một dòng chưa xử lý xong.

### 7. TẠO ĐƠN NHÁP — PASS
`POST /api/v2/don` kèm `Idempotency-Key: e2e-d2a280d2` → **HTTP 201**
Đo trong CSDL, bảng `don_hang`:
```json
{"id": 3, "ma_don": "T1-000003", "trang_thai": "nhap", "idem_key": "e2e-d2a280d2", "tenant_id": 1}
```
Gửi **lại** cùng `Idempotency-Key` → **HTTP 200**, `idempotent_trung: true`, **không** sinh đơn
thứ hai.

### 8. DUYỆT ĐƠN — PASS
`POST /api/v2/don/3/duyet` → **HTTP 200**, `trang_thai` = `da_duyet`
Đo trong CSDL, bảng `don_lich_su`: `[{"nguon": "user:2", "noi_dung": "tạo đơn nháp"}, {"nguon": "user:2", "noi_dung": "duyệt đơn"}]`

### 9. CHỌN HÃNG MOCK — PASS
`POST /api/v2/tai-khoan-hang` (`hang: "jt"`, `moi_truong: "mock"`,
`credentials.privateKey = "E2E-PRIVATE-KEY"`) → **HTTP 201**

| Kiểm | Giá trị |
|---|---|
| `carrier_accounts` trong CSDL | `{"id": 1, "hang": "jt", "moi_truong": "mock", "credentials_duoi": "CUST", "webhook_ma": "cvtRTxC9RL3bhlwe"}` |
| Tiền tố cột bản mã | `v3$goc$cd2068d…` ⇒ AES-256-GCM **có `key_id`** (xoay khóa được) |
| Chuỗi `E2E-PRIVATE-KEY` **rõ** có trong `credentials_ma_hoa` không? | **không** |

### 10. GỬI ĐƠN — PASS
`POST /api/v2/don/3/gui` → **HTTP 200**
Đo trong CSDL, bảng `don_hang`:
```json
{"trang_thai": "da_gui", "ma_van_don": "JTVN3699694739", "phi_van_chuyen": 41000,
 "carrier_account_id": 1, "trang_thai_giao": "cho_lay", "hang_trang_thai_giao": 1}
```
`da_gui` chỉ được đặt **sau khi** adapter trả `ok=True` kèm mã vận đơn.

### 11. NHẬN WEBHOOK MOCK (ký ĐÚNG) — PASS
Secret lấy bằng `bao_mat.giai_ma_wh(carrier_accounts.webhook_secret_ma_hoa, webhook_ma)` —
tức **giải mã AES-GCM thật** từ CSDL, không phải secret bộ thử tự đặt.

| Lượt | Mã | Ghi chú |
|---|---:|---|
| Chữ ký **rác** (`"chu-ky-rac"`) | **401** | Đối chứng âm: cửa có thật sự kiểm chữ ký |
| Chữ ký **đúng** (HMAC-SHA256) | **202** | — |

Đo trong CSDL, bảng `wh_su_kien`:
`{"id": 1, "event_id": "e2e-wh-1", "trang_thai": "xong", "so_lan_thu": 0, "loi_cuoi": null}`

### 12. CẬP NHẬT TRẠNG THÁI — PASS
Đẩy chuỗi 4 sự kiện, tất cả ký đúng:

| `event_id` | `event` | Mục đích |
|---|---|---|
| `e2e-wh-1` | `lay_hang` | tiến bình thường |
| `e2e-wh-2` | `dang_giao` | tiến bình thường |
| `e2e-wh-3` | `giao_thanh_cong` | tiến bình thường |
| `e2e-wh-3` (lần 2) | `giao_thanh_cong` | **replay y nguyên** |
| `e2e-wh-4` | `lay_hang` | **đến muộn**, hạng thấp hơn |

Kết quả đo trong CSDL:
- `don_hang`: `{"trang_thai_giao": "giao_thanh_cong", "hang_trang_thai_giao": 5}`
- Replay `e2e-wh-3` → **HTTP 200** `{"ket_qua": "da_nhan_truoc_do", "su_kien_id": 3}` —
  chống trùng do `UNIQUE(carrier_account_id, event_id)` **trong CSDL** cưỡng chế, không phải `if`
- 4 hàng `wh_su_kien`, cả 4 `trang_thai = "xong"`
- Sự kiện đến muộn **không** kéo lùi trạng thái

### 13. XEM TRACKING TIMELINE — PASS
`GET /api/v2/don/3` → **HTTP 200**, **7 mục** lịch sử:

```
2026-10-15 00:18:55+0700 · user:2     · tạo đơn nháp
2026-10-15 00:18:55+0700 · user:2     · duyệt đơn
2026-10-15 00:18:55+0700 · user:2     · hãng J&T Express (mock) xác nhận, mã vận đơn JTVN3699694739
2026-10-15 00:18:55+0700 · webhook:1  · trạng thái giao → lay_hang
2026-10-15 00:18:55+0700 · webhook:2  · trạng thái giao → dang_giao
2026-10-15 00:18:55+0700 · webhook:3  · trạng thái giao → giao_thanh_cong
2026-10-15 00:18:55+0700 · webhook:4  · sự kiện lay_hang đến muộn/out-of-order — KHÔNG áp (giữ giao_thanh_cong)
```

Hai điều đáng ghi:
- Mốc thời gian **mang múi giờ** (`+0700`), đúng `CLAUDE.md` §12.2.
- Mục cuối: sự kiện bị từ chối **vẫn để lại dấu vết**. Hệ không im lặng bỏ qua — đây là ngược
  với kiểu hỏng im lặng, và là chỗ `app/webhook.py` làm **đúng** (so với R-03, chỗ nó làm sai).

### 14. DỮ LIỆU NẰM TRONG CSDL THẬT — PASS
```
duong_dan_csdl: /Users/viporder/code/veh2-qa-verification/app/du-lieu/qa2-e2e/hub.db
file_ton_tai:   true
so_byte:        200704
```
Đếm hàng:

| Bảng | Số hàng |
|---|---:|
| `tenants` | 1 |
| `users` | 3 |
| `tenant_memberships` | 2 |
| `sessions` | 3 |
| `carrier_accounts` | 1 |
| `don_hang` | **3** (2 từ import + 1 tạo tay) |
| `don_lich_su` | 9 |
| `import_batch` | 1 |
| `import_dong` | 3 |
| `wh_su_kien` | 4 |
| `audit` | 14 |

---

## Giới hạn của lượt E2E này — nói rõ để không tưởng là đã phủ hết

1. **Mọi lượt gọi hãng là mock.** `CHO_PHEP_LIVE=False` ở mọi adapter, và
   `POST /tai-khoan-hang` từ chối `moi_truong != "mock"` (403 BLOCKED). Lượt này **không** nói
   gì về hành vi với hãng thật.
2. **Webhook do bộ thử đẩy.** Chữ ký thật, cửa thật, secret thật từ CSDL — nhưng **không** phải
   J&T gửi, và **không** mang `scanTypeCode` riêng của hãng. Chính chỗ đó là phát hiện **R-03**:
   nếu đẩy `{"event": "106"}` (mã J&T thật) thì hệ nhận, ghi `xong`, mà **không** đổi trạng thái
   đơn. Lượt E2E ở trên dùng tên nội bộ (`lay_hang`…) nên **đi qua được** — đây là lý do E2E
   xanh **không** đủ để kết luận webhook đã sẵn sàng.
3. **Một tenant, một người gửi, một hãng, chạy tuần tự.** Không đo đồng thời (xem R-01, R-08),
   không đo nhiều tenant trong cùng lượt E2E (việc đó ở `r13`, `r44` của bộ thử).
4. **Một lượt chạy.** Khác với bộ gateway (24 lượt), E2E chạy 1 lượt vì nó dựng dữ liệu tích
   luỹ; lượt thứ hai cần CSDL sạch.
5. **CSDL E2E bị xoá đầu mỗi lượt** (`hub.db`, `-wal`, `-shm`) để số đếm hàng ở bước 14 có nghĩa.
   File hiện tại là của lượt **ngày 15/10/2026**.

## Chạy lại

Mã chạy lượt này nằm ngoài vùng sở hữu của AG-05 (chỉ được tạo
`app/thu/thu_qa2_soat.py` và `docs/QA2_*.md`), nên script giữ ở thư mục tạm của phiên. Để dựng
lại: đặt `VIP_HUB_DATA=<worktree>/app/du-lieu/qa2-e2e`, khởi `server.ThreadingHTTPServer` trên
cổng `8942`, rồi đi đúng 13 bước theo thứ tự ở trên, **đọc lại CSDL sau từng bước**. Mọi lệnh
gọi đều qua `/api/v2/*`; chỉ bước lấy webhook secret đi trực tiếp qua `bao_mat.giai_ma_wh`, vì
API **cố ý không** trả secret ra ngoài (đúng thiết kế — xem ca `r47`).
