# G22 — AGENT 04 · REGRESSION & SECURITY: BẢY MẶT AN TOÀN, ĐO ĐƯỢC, CÓ ĐỐI CHỨNG VÀ CÓ TIÊM LỖI

> **Vai:** AGENT 04 · REGRESSION & SECURITY (G22) · **Task:** `task_22ea1da0f162` · **Dispatch:** `ctx_28c01622403e`
> **Nền đo:** `integration/g20` @ **`a76ec51c9931b62451721302446d7c3b74b9c81f`** — đo bằng
> `git rev-parse HEAD` (mã thoát 0). **KHÔNG** dùng `main` (`de740dc` — không chứa G13–G22).
> **Hai tệp làn này được phép tạo:** `app/thu/thu_g22_regression.py` (mới · 1.438 dòng ·
> `sha256 29da2842bddada0938a2582c66d67ea840b9daa8ab23f4f209793b6f097132cc`) ·
> `docs/G22_REGRESSION.md` (tài liệu này).
> **Không sửa một dòng mã sản phẩm nào.** §9 chứng minh bằng `git status --porcelain -uall`.

**Lệnh chạy bộ kiểm (một lệnh, không biến môi trường, không phụ thuộc shell):**

```sh
python3 app/thu/thu_g22_regression.py
```

**Lượt chạy cuối — MỌI con số trong tài liệu này sinh ra từ đây:**

```sh
$ cd /Users/viporder/orca/workspaces/vip-express-hub/g22-a4-regression
$ PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_g22_regression.py > /tmp/g22_a4_final.log 2>&1
# === EXIT CODE THAT = 0
# Ran 35 tests in 13.702s
# OK
# PASS = 35 · FAIL = 0 · SKIP = 0     (`grep -c skipped /tmp/g22_a4_final.log` → 0)
# BLOCKED = 1 phép đo: `git write-tree` rc=128 (sandbox chặn .git) — AG-00 commit hộ (§9.2, §10.1)
# bảng tự in : 7/7 mặt có bằng chứng · 32 ca ghi sổ · 7/7 mặt đã tiêm lỗi
# tiêm ngoài : 7/7 phép tiêm làm bộ kiểm ĐỎ ĐÚNG CA
# sha256(tệp kiểm) = 29da2842bddada0938a2582c66d67ea840b9daa8ab23f4f209793b6f097132cc
# sha256(log)      = e49923e0789cf2d71de99aa1c4e49a4befa233e3dd52c898e247e5cd5a99fb69
```

Đọc con số cho đúng: **35 ca** = 31 ca đo bảy mặt + 4 ca tổng kết (`z1` bảng, `z2` máy dò,
`z3` tiêm lỗi ngoài, `z9` in bảng cuối). **BỎ QUA = 0**: không có ca nào skip, nên không cần
viện dẫn lý do hợp đồng nào. Mọi khẳng định phủ định đều có **đối chứng dương**, và cả bảy mặt
đều có **phép tiêm lỗi** — xem §8.

---

## 0. BẢNG PHÁN QUYẾT — BẢY MẶT

| # | Mặt | Giá trị ĐO ĐƯỢC | Đối chứng dương (bắt buộc) | Tiêm lỗi | Phán quyết |
|---|---|---|---|---|---|
| **1** | Tenant isolation | A→đơn B = **404** · B→đơn A = **404** · thân KHÔNG mang dấu hiệu bên kia | A→đơn A = **200** + đúng dấu hiệu A · B→đơn B = 200 | bỏ điều kiện tenant trong `lay_don` ⇒ **ĐỎ đúng ca** | **XANH** |
| **2** | RBAC | viewer→POST /don = **403** · viewer→DELETE = **403** · staff→POST /memberships = **403** · số đơn KHÔNG tăng | staff→POST /don = **201** · admin→DELETE = **200** · owner→POST /memberships = **201** | gỡ dòng quyền trong CSDL ⇒ **403**; chèn lại ⇒ **201** | **XANH** |
| **3** | Fail-closed | thiếu khai kho: **rc=1** · bản sao rác: **rc=1** · dấu kiểm sai: **rc=1** · không có hub.db: **rc=1** · vân tay CSDL KHÔNG đổi | khai `sqlite`: **rc=0** + tệp thật · khôi phục bản TỐT: **rc=0**, dữ liệu về đúng | bỏ chốt "chưa khai" ⇒ **ĐỎ đúng ca** | **XANH** |
| **4** | Idempotency | cùng `Idempotency-Key` ×2 ⇒ **(201, 200)**, **cùng id**, số đơn **+1** · 2 luồng song song ⇒ **1 id**, **+1** | khoá KHÁC ×2 ⇒ **201+201**, **+2** · `UNIQUE(tenant_id, idem_key)` ⇒ `IntegrityError` | bỏ khoá chống trùng ⇒ **ĐỎ đúng ca** | **XANH** |
| **5** | Webhook security | sai chữ ký ⇒ **401**, **0 sự kiện**, audit `webhook_chu_ky_tu_choi` +1 · thiếu header ⇒ **401** · secret của B vào URL của A ⇒ **401** | chữ ký ĐÚNG ⇒ **202**, **1 sự kiện** · phát lại ⇒ **200** `da_nhan_truoc_do`, **+0** | buộc `kiem_chu_ky` trả True ⇒ **ĐỎ đúng ca** | **XANH** |
| **6** | Không rò rỉ chéo tenant | **11 đường** của A: **0** phản hồi mang dấu hiệu B · 2 tệp log trên đĩa: **0** dấu hiệu B · **15 tệp** bằng chứng: **0** | phiên B đọc B **thấy** dấu hiệu B · log CÓ dấu hiệu A khi A nằm trong ĐƯỜNG DẪN | ghi cả query vào log ⇒ **ĐỎ đúng ca** | **XANH** |
| **7** | Không gửi đơn production | 2/2 adapter `live_mo=False` · sandbox/production ⇒ `PermissionError` · HTTP production ⇒ **403 BLOCKED** · **toàn lượt chạy: 74 kết nối, 0 ngoài loopback, 0 tới `:5432`** | mock dựng được · mock gửi đơn ⇒ `da_gui` + vận đơn GIẢ `VTP##########` · HTTP mock ⇒ **201** | tiêm đích `203.0.113.7` ⇒ bị BẮT và CHẶN; mở `CHO_PHEP_LIVE` ⇒ **ĐỎ đúng ca** | **XANH** |

> **Đọc bảng này cho đúng.** `XANH` = đã ĐO được và ĐẠT bằng log thật ở lượt chạy trên.
> Không có ô nào là "bỏ qua" hay "suy luận". Mọi chỗ **không đo được** nằm ở §10 và **không**
> được cộng vào cột XANH.

---

## 1. MẶT 1 — TENANT ISOLATION

**Nền giả lập:** hai tenant RIÊNG (`Tenant A` id trong lượt = 1 · `Tenant B` id = 2), mỗi bên một
chủ; mỗi bên có khách hàng + đơn hàng + tài khoản hãng mang **dấu hiệu riêng**:
`MATADANHDAU` (A) và `MATBDANHDAU` (B). Dấu hiệu **toàn chữ cái** là cố ý — bộ che đường dẫn của
log chỉ che đoạn trộn chữ+số trông như credential, nên dấu hiệu đi qua nguyên văn và **đối chứng
log ở §6** mới có nghĩa.

### 1.1 Phép đo và đối chứng (cùng một lượt chạy)

| Vế | Lệnh HTTP | Mã đo được | Thân phản hồi |
|---|---|---|---|
| **ĐỐI CHỨNG DƯƠNG** | `GET /api/v2/don/{don_a}` (phiên A) | **200** | đúng `id=1`, **có** `MATADANHDAU` |
| **PHÉP ĐO** | `GET /api/v2/don/{don_b}` (phiên A) | **404** | `{"loi":"không có đơn này"}` — **không** có `MATBDANHDAU` |
| **ĐỐI CHỨNG ÂM chéo tenant** | `GET /api/v2/don/{don_a}` (phiên B) | **404** | **không** có `MATADANHDAU` |
| **ĐỐI CHỨNG ÂM chéo tenant** | `GET /api/v2/khach-hang/{kh_a}` (phiên B) | **404** | **không** có `MATADANHDAU` |
| Đối chứng dương của vế B | `GET /api/v2/don/{don_b}` (phiên B) | **200** | **có** `MATBDANHDAU` |

Mã trạng thái được **ghim cụ thể** (`assertEqual(404)`), không dùng `assertIn(200,400)`.

### 1.2 Chứng minh phép đo KHÔNG mù (dòng dữ liệu của B có thật)

Một `404` có thể chỉ vì "đơn không tồn tại" — kết luận đúng nhưng không đo điều mình tưởng.
Bộ kiểm đo thêm ở tầng lõi, trong cùng ca:

```
don_hang.lay_don(tenant B, don_b)  →  KHÁC None   (dòng của B CÓ THẬT)
don_hang.lay_don(tenant A, don_b)  →  None       (tách tenant là thứ tạo ra 404)
SELECT id FROM don_hang WHERE id=? →  có dòng
```

### 1.3 Các đường khác đã đo

| Đường | Kết quả |
|---|---|
| `GET /api/v2/don` (danh sách A) | có đơn A, **không** có id đơn B, **không** dấu hiệu B |
| `POST /api/v2/don/tim {"q": MAT_B}` | `tong = 0` — **đối chứng**: `{"q": MAT_A}` ⇒ `tong ≥ 1` |
| `GET /api/v2/don/xuat-csv` (A) | **có** `MATADANHDAU`, **không** `MATBDANHDAU` |
| `POST /api/v2/tai-khoan-hang/{tk_b}/rotate` (A) | **404** — **đối chứng**: rotate tài khoản A ⇒ **200** |
| `GET /api/v2/tai-khoan-hang` (A) | danh sách có tài khoản A, **không** có tài khoản B |
| `POST /api/v2/auth/doi-tenant {tenant_id: B}` (A) | **403** · ngữ cảnh vẫn là tenant A — **đối chứng**: đổi sang tenant A ⇒ **200** |

---

## 2. MẶT 2 — RBAC

| Vế | Lệnh | Mã | Ghi chú |
|---|---|---|---|
| **ĐỐI CHỨNG ÂM** | `TENANT_VIEWER` → `POST /api/v2/don` | **403** | thân `{"loi":"không đủ quyền"}` · **số đơn KHÔNG tăng** (đếm CSDL trước/sau) |
| **ĐỐI CHỨNG DƯƠNG** | `TENANT_STAFF` → **cùng payload, cùng đường** | **201** | số đơn **+1** |
| **ĐỐI CHỨNG ÂM** | `TENANT_VIEWER` → `DELETE /api/v2/don/{id}` | **403** | đơn **giữ** trạng thái `nhap` |
| **ĐỐI CHỨNG DƯƠNG** | `TENANT_ADMIN` → `DELETE` đơn khác | **200** | đơn thành `huy` |
| **ĐỐI CHỨNG ÂM** | `TENANT_STAFF` → `POST /api/v2/memberships` | **403** | **không** tạo user |
| **ĐỐI CHỨNG DƯƠNG** | `TENANT_OWNER` → `POST /api/v2/memberships` | **201** | user được tạo |

### 2.1 Quyền tra từ CSDL, không hard-code — đo bằng PHÉP TIÊM

```
DELETE FROM role_permissions WHERE role_ma='TENANT_STAFF' AND perm_ma='tenant.don.ghi'
→  CÙNG phiên staff, POST /don  =  403     (nếu RBAC hard-code: 201 và ca này ĐỎ)
INSERT lại dòng quyền
→  CÙNG phiên staff, POST /don  =  201
```

Đây vừa là đối chứng dương vừa là phép tiêm: quyết định đọc từ CSDL, và bộ kiểm **thấy** được
sự đổi chiều. Dòng quyền được chèn lại trong `finally`.

---

## 3. MẶT 3 — FAIL-CLOSED

**Phạm vi, nói thẳng:** làn AGENT 01 sở hữu `app/cau_hinh.py` / `app/migrate.py` (chốt
`KHO_DANG_CHAY`). Làn này **KHÔNG sửa** hai tệp đó; nó chỉ **gọi** chúng trong **tiến trình con**
và đo **mã thoát thật + thông điệp thật + tệp trên đĩa**. Mọi biến `VIP_*` kế thừa bị bộ đo xoá
trước khi chạy con — một biến lọt vào từ shell sẽ làm nhánh "chưa khai" không bao giờ chạy.

| Ca | Phép đo | Kết quả ĐO ĐƯỢC | Đối chứng dương |
|---|---|---|---|
| `C1` | KHÔNG khai kho đang chạy ⇒ `migrate.sao_luu()` | **rc = 1** · stderr `TỪ CHỐI: CHƯA KHAI kho đang chạy…` · **không** có tệp bản sao | khai `VIP_KHO_DANG_CHAY=sqlite` ⇒ **rc = 0** · bản sao + `.sha256` tồn tại |
| `C2` | khôi phục từ tệp **KHÔNG phải SQLite** | **rc = 1** · `TỪ CHỐI: … KHÔNG PHẢI CSDL SQLite (16 byte đầu: b'KHONG-PHAI-SQLIT')` · **vân tay `hub.db*` KHÔNG đổi** | `C4` |
| `C3` | khôi phục với **dấu kiểm `.sha256` SAI** | **rc = 1** · `TỪ CHỐI: … KHÁC dấu kiểm … mong đợi 000…0 · thực tế d8fd018d…` · **vân tay KHÔNG đổi** | `C4` |
| `C4` | khôi phục bản sao **TỐT** (đối chứng dương cho C2/C3) | **rc = 0** · dữ liệu về đúng: `DEM_KHACH=0 → 1` | — (chính là vế dương) |
| `C5` | `sao_luu()` khi **KHÔNG có `hub.db`** | **rc = 1** · `TỪ CHỐI: không thấy CSDL …` · **KHÔNG tạo** CSDL rỗng | dựng `hub.db` ⇒ cùng kịch bản **rc = 0** |

**Vân tay CSDL** trong C2/C3 là băm của **mọi** tệp `hub.db*` (kể cả `-wal`/`-shm`). Băm mỗi tệp
chính là một đối chứng mù: ở chế độ WAL, dữ liệu vừa ghi nằm ở `-wal`, nên "không đổi" có thể là
giả.

**Nguyên văn thông điệp (tái hiện độc lập, không qua bộ kiểm):**

```sh
D=$(mktemp -d)
env -u VIP_KHO_DANG_CHAY VIP_HUB_DATA="$D" python3 -c \
  "import sys;sys.path.insert(0,'app');import csdl,migrate;csdl.mo();csdl.dong();migrate.sao_luu()"
# [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này
#           có chứa dữ liệu đang phục vụ hay không (chưa có nguồn nào khai).
# === rc = 1

VIP_HUB_DATA="$D" VIP_KHO_DANG_CHAY=sqlite python3 -c \
  "import sys;sys.path.insert(0,'app');import csdl,migrate;csdl.mo();csdl.dong();print(migrate.sao_luu())"
# → /tmp/…/sao-luu/hub-truoc-migrate-<giờ>.db
# === rc = 0
```

---

## 4. MẶT 4 — IDEMPOTENCY (CHỨNG MINH BẰNG SỐ)

| Vế | Lệnh | Đo được |
|---|---|---|
| **PHÉP ĐO** | `POST /api/v2/don` ×2, **cùng** `Idempotency-Key: idem-a4-1` | `(201, 200)` · lượt 2 `idempotent_trung=True` · **cùng `don.id`** · số đơn **+1** · **1** dòng `idem_key` trong CSDL |
| **ĐỐI CHỨNG ÂM** | ×2, **hai khoá KHÁC nhau** | `(201, 201)` · **hai id khác nhau** · số đơn **+2** — phép đếm của vế trên **nhìn thấy** được sự nhân đôi |
| **HAI LUỒNG SONG SONG** | 2 thread, `Barrier`, cùng khoá | **1 id duy nhất** · số đơn **+1** · kết quả đo được: `[(200, 10, True), (201, 10, False)]` |
| **TẦNG CSDL** | `INSERT` thẳng dòng thứ hai cùng `(tenant_id, idem_key)` | `IntegrityError` — ràng buộc `UNIQUE (tenant_id, idem_key)` có thật (khoá không chỉ nằm ở tầng mã) |

---

## 5. MẶT 5 — WEBHOOK SECURITY

Tài khoản hãng mock của A trả **một lần** `webhook_secret_mot_lan`; bộ kiểm tự tính
`HMAC-SHA256(secret, body)` và gửi header `X-Webhook-Signature`.

| Vế | Yêu cầu | Mã | Sự kiện trong `wh_su_kien` | Ghi chú |
|---|---|---|---|---|
| **ĐỐI CHỨNG DƯƠNG** | thân đúng + chữ ký **ĐÚNG** của A | **202** | **+1** | `code=1` |
| Phát lại y nguyên | cùng thân + cùng chữ ký | **200** | **+0** | `ket_qua=da_nhan_truoc_do` (chống trùng bền) |
| **ĐỐI CHỨNG ÂM** | cùng thân + **secret khác** | **401** | **+0** | audit `webhook_chu_ky_tu_choi` **+1** |
| **ĐỐI CHỨNG ÂM** | **thiếu** header chữ ký | **401** | **+0** | |
| **CHÉO TENANT** | ký bằng **secret của B**, gửi vào **URL của A** | **401** | **+0** | **đối chứng**: cùng thân, secret của A ⇒ **202**, **+1** |

Bốn vế phủ định đều có cùng một vế dương (dòng đầu) làm đối chứng đường.

---

## 6. MẶT 6 — KHÔNG RÒ RỈ DỮ LIỆU CHÉO TENANT

Ba đường RA được quét, mỗi đường có đối chứng dương **trên cùng bộ đọc**:

### 6.1 Thân phản hồi — 11 đường, mã trạng thái ghim cụ thể

```
GET  /don=200 · /don/{A}=200 · /don/{B}=404 · /don/xuat-csv=200 · /khach-hang/{B}=404
GET  /tai-khoan-hang=200 · /audit=200 · /webhook/su-kien=200 · /billing=200 · /auth/toi=200
POST /don/tim {q=B}=200
→ 0/11 phản hồi chứa MATBDANHDAU; 3/11 chứa MATADANHDAU (dữ liệu của chính A)
ĐỐI CHỨNG: phiên B đọc /don ⇒ THẤY MATBDANHDAU
```

### 6.2 Log trên đĩa — hai kênh có thật trong hệ

| Kênh | Nguồn | Phép đo |
|---|---|---|
| JSONL có cấu trúc | `quan_sat.ghi` (trường `duong`) | `GET /don?q=MATBDANHDAU` ⇒ query **bị cắt**, dấu hiệu B **không** xuống log |
| Access log | `server.log_message` → stderr | cùng yêu cầu ⇒ **không** có dấu hiệu B |

**Đối chứng dương, cùng hai tệp:** `GET /api/v2/khong-co-duong-nay/MATADANHDAU` ⇒ dấu hiệu A
**XUẤT HIỆN** trong cả hai log. Hai tệp được **ghi ra đĩa rồi đọc lại** — phép đo chạy trên TỆP,
không chỉ trên `StringIO`.

### 6.3 Tệp bằng chứng bộ đo sinh ra trên đĩa

Quét **15 tệp** trong thư mục bằng chứng của lượt chạy: **0 tệp** chứa `MATBDANHDAU`;
**2 tệp** chứa `MATADANHDAU` (đối chứng: cùng bộ đọc, cùng tiêu chí).

**Phạm vi, nói ra:** `hub.db`, `hub.db-wal`, `hub.db-shm` và tệp khoá được **loại trừ có chủ ý** —
CSDL là nơi LƯU dữ liệu của **cả hai** tenant (thiết kế), không phải đường rò rỉ. Phép quét áp
lên **tệp log/báo cáo do bộ đo sinh ra**, không phải lên kho dữ liệu.

---

## 7. MẶT 7 — KHÔNG GỬI ĐƠN PRODUCTION NGOÀI Ý MUỐN

### 7.1 Mọi lệnh gọi hãng ở môi trường thật đều bị TỪ CHỐI

| Vế | Phép đo | Kết quả |
|---|---|---|
| Mọi adapter đã đăng ký | `adapter.danh_sach_hang()` | **2/2** có `live_mo = False` |
| Dựng adapter `sandbox` / `production` | `adapter.tao_adapter(ma, {}, mt)` | `PermissionError` cho **cả 2 adapter × 2 môi trường** |
| Cổng cấu hình J&T | `cau_hinh.jt_kiem_moi_truong("sandbox"/"production")` | `(False, lý do)`; lý do nêu đúng `V-G09-01` / "chưa duyệt" |
| Tầng HTTP J&T | `http_jt.chan_moi_truong(...)` | `PermissionError` |
| Đường HTTP tạo tài khoản hãng | `POST /api/v2/tai-khoan-hang {moi_truong:"production"}` | **403** · `"BLOCKED"` · **0 dòng** trong `carrier_accounts` |
| **ĐỐI CHỨNG DƯƠNG** | dựng `mock` / `POST` tài khoản mock / gửi đơn mock | dựng được; **201**; đơn `da_gui` + vận đơn **GIẢ** `VTP##########` |

### 7.2 Toàn bộ lượt chạy: chỉ loopback

Bộ kiểm vá `socket.socket.connect` **trước khi mở socket**: mọi đích được ghi lại; đích **không**
loopback bị **ghi nhận rồi NÉM trước syscall** ⇒ không một byte nào ra khỏi máy.

```
toàn lượt chạy: 74 kết nối đã mở · 0 đích ngoài loopback · 0 kết nối tới :5432
có kết nối tới 127.0.0.1:<cổng OS cấp của máy chủ bộ đo>
PHÉP TIÊM: socket.create_connection(("203.0.113.7", 443))  →  ChanMangNgoai
           bộ ghi THẤY đích 203.0.113.7  (nếu không thấy: bộ ghi mù, ca này ĐỎ)
```

`203.0.113.7` là TEST-NET-3 (RFC 5737) — không định tuyến được, và bộ ghi ném **trước** khi
syscall, nên phép tiêm không tạo lưu lượng thật.

---

## 8. TIÊM LỖI NGOÀI — CHỨNG MINH BỘ KIỂM "ĐỎ ĐƯỢC"

Phép tiêm nội bộ ở §1–§7 chứng minh **phép đo** phân biệt được hai giá trị. Mục này chứng minh
điều mạnh hơn: **nếu sản phẩm hồi quy, cả bộ kiểm ĐỎ ĐÚNG CA**. Mỗi mặt: dựng **bản sao cây**
trong `$TMP`, sửa **đúng một đoạn** trong bản sao, chạy **CHÍNH bộ kiểm này** trên bản sao.

```
MẶT                            TỆP BỊ TIÊM      rc   CA BẮT ĐƯỢC (ĐỎ)
1-tenant-isolation             don_hang.py      1    test_a2_a_khong_doc_duoc_don_cua_b
2-rbac                         server.py        1    test_b1_viewer_tao_don_bi_chan_403_va_khong_tao_dong_nao
3-fail-closed                  migrate.py       1    test_c1_sao_luu_tu_choi_khi_chua_khai_kho
4-idempotency                  don_hang.py      1    test_d1_cung_idempotency_key_hai_lan_chi_mot_don
5-webhook-security             webhook.py       1    test_e2_chu_ky_sai_bi_tu_choi_401_va_khong_tao_su_kien
6-khong-ro-ri-cheo-tenant      server.py        1    test_f2_log_tren_dia_khong_mang_du_lieu_b_va_query_bi_cat
7-khong-gui-don-production     adapter_jt.py    1    test_g1_moi_adapter_dong_cho_phep_live
TỰ PHÁN: 7/7 phép tiêm ngoài làm bộ kiểm ĐỎ ĐÚNG CA
```

Nội dung từng phép tiêm (đúng một đoạn, có kiểm `ast.parse` sau khi sửa):

| Mặt | Đoạn bị tiêm | Ý nghĩa |
|---|---|---|
| 1 | `lay_don` bỏ `AND tenant_id=?` | đọc chéo tenant |
| 2 | `_can` thành no-op | mất kiểm quyền |
| 3 | `if kho is None: pass` | mất chốt fail-closed |
| 4 | `if idem_key:` → `if False:` (cả hai chỗ) | mất khoá chống trùng |
| 5 | `kiem_chu_ky` → luôn `True` | nhận mọi chữ ký |
| 6 | dòng log ghi `self.path` (cả query) | query rò xuống log |
| 7 | `CHO_PHEP_LIVE = True` | mở đường live |

**Cây thật KHÔNG bị sửa.** Mọi bản sao nằm dưới `$TMP/veh-g22-a4-regression-*/ghe-*`.
Chốt của **BỘ ĐO**, nói ra cho minh bạch: cây gương chạy với
`VIP_G22_A4_KHONG_TIEM_NGOAI=1` nên `Z3` tự quay về (không tiêm lồng nhau → không đệ quy).
Đó là chốt của dụng cụ đo, **không** phải một ca nghiệm thu bị bỏ qua: bản gương vẫn chạy
34 ca ĐO còn lại (Z3 quay về ngay), và ca hỏng mong đợi vẫn ĐỎ đúng tên.

---

## 9. PHẠM VI GHI + TUÂN THỦ TUYỆT ĐỐI

### 9.1 `git status` trên cây thật (sau khi thêm tài liệu này)

> **Môi trường:** máy này có `GIT_CONFIG_COUNT=2` với `GIT_CONFIG_KEY_0` RỖNG (lỗi môi trường
> `N-G18-00`/`N-G22-03`), nên **mọi** lệnh `git` nguyên bản thoát 128. Các lệnh dưới đây chạy với
> gia đình biến dị dạng đó đã gỡ — đúng cách `app/thu/chay_tat_ca.sh` tự chuẩn hoá. Không có
> thao tác GHI `.git` nào.

```sh
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git status --porcelain -uall
?? app/thu/thu_g22_regression.py
?? docs/G22_REGRESSION.md
# === rc = 0 · ĐÚNG 2 đường, cả hai nằm trong phạm vi được ghi
```

### 9.2 `git write-tree` — **BLOCKED**, không tự vượt

```sh
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git write-tree
fatal: Unable to create '…/.git/worktrees/g22-a4-regression/index.lock': Operation not permitted
# === EXIT CODE THAT = 128
```

Sandbox chặn ghi `.git`. Tôi **không** tự vượt (đúng chỉ thị; xem `docs/QA_G22.md` §8.1 và
`N-G22-03`). **Việc của AG-00:** commit hộ hai tệp ở §9.1. Vì `write-tree` không đo được trong
worktree, mọi con số ở đây ghim vào **`HEAD a76ec51`** và **sha256 của tệp kiểm** — hai thứ đọc
được bằng lệnh chỉ-đọc.

### 9.3 Bảng tuân thủ

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Push GitHub / deploy VPS / tunnel | **0** lệnh `git push`/`ssh`/deploy nào được chạy | ✓ |
| 2 | Gọi API production (kể cả sandbox) | mọi kết nối trong lượt chạy là **loopback** (§7.2); `CHO_PHEP_LIVE` không mở | ✓ |
| 3 | Tạo đơn vận chuyển thật | chỉ adapter **mock**; vận đơn dạng GIẢ `VTP##########`; 0 byte ra ngoài | ✓ |
| 4 | Sửa dữ liệu thật / xoá database / D-8 PostgreSQL | CSDL là `mktemp`; **0** kết nối `:5432` (ĐO ở `G5`, không phải khai); **không** làm gì thuộc `OWNER_ACTIONS C4` | ✓ |
| 5 | Sửa tệp ngoài phạm vi | `git status` = đúng 2 tệp; **không** sửa `app/cau_hinh.py`/`app/migrate.py` (làn AGENT 01) | ✓ |
| 6 | Sửa chính sách bảo mật / quyết định OWNER | không đổi hằng số nào của sản phẩm | ✓ |
| 7 | Kết luận PASS không có log | mọi số ở §0–§8 lấy từ `/tmp/g22_a4_final.log` (sha256 ghim ở đầu) | ✓ |
| 8 | Bỏ qua lỗi / xoá ca để xanh | **0 skip**; ca nào không dựng được phép đo thì báo HỎNG | ✓ |
| 9 | Đụng tệp của làn khác | tiêm lỗi chỉ trên **bản sao** trong `$TMP`; §8 | ✓ |

**Bằng chứng nằm ngoài cây (đúng phạm vi):** thư mục `mktemp` của lượt chạy cuối —
`/var/folders/…/T/veh-g22-a4-regression-*` — chứa log JSONL/access đã ghi ra đĩa, các thư mục
`con/fc*` (tiến trình con fail-closed), và `ghe-*` (7 bản sao cho tiêm lỗi ngoài). Log của lượt
cuối: `/tmp/g22_a4_final.log` (`sha256 e49923e0…`). **Không** chép chúng vào repo vì chúng nằm
ngoài phạm vi được ghi.

---

## 10. CHƯA ĐO / BLOCKED — NÓI THẲNG, KHÔNG CỘNG VÀO CỘT XANH

| # | Chưa đo | Vì sao | Ai cần |
|---|---|---|---|
| 1 | **`git write-tree`** (vân tay cây TRƯỚC/SAU) | sandbox chặn `.git/index.lock` ⇒ **rc 128** (§9.2). Không tự vượt | **AG-00** commit hộ |
| 2 | **Webhook `jt_digest` ở môi trường thật** | tạo tài khoản hãng `moi_truong != mock` bị chặn **403** (đúng thiết kế §7.1). Chỉ đo được `hub_hmac` của account **mock** | chờ `V-G09-01`/`V-13906-05` (Owner) |
| 3 | **Idempotency nhiều TIẾN TRÌNH** | đo 2 **luồng** trong 1 tiến trình; khoá ghi `csdl.khoa_ghi` là lock Python, **không** phủ qua tiến trình (hạn chế đã biết của dự án) | AG-00/AG-05 nếu cần |
| 4 | **Bộ ghi mạng trong TIẾN TRÌNH CON** | con của §3 (fail-closed) có ghi mạng riêng không được bộ ghi trong tiến trình cha thấy. Nhưng các con đó chỉ mở CSDL tạm, **không** gọi mạng — phạm vi câu "0 đích ngoài loopback" là **tiến trình chính** | đã nói rõ phạm vi |
| 5 | **Quét tệp bằng chứng gồm `hub.db`/khoá** | loại trừ có chủ ý: CSDL chứa dữ liệu cả hai tenant là thiết kế; quét nó sẽ "báo rò" giả | — |
| 6 | **Trình duyệt/E2E tầng 3** | ngoài phạm vi làn REGRESSION & SECURITY; các làn G22 khác sở hữu | làn E2E |
| 7 | **`OWNER_ACTIONS C4` (PostgreSQL, D-8)** | **BLOCKED OWNER** — không thực hiện, không ép cổng xanh. Khác với `G19-C6` (việc local của làn AG-02) | Owner |

---

## 11. CÁCH TÁI HIỆN (không cần biến môi trường)

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/g22-a4-regression

# 1) Toàn bộ bảy mặt + bảng bằng chứng + 7 phép tiêm ngoài (≈14 giây)
PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_g22_regression.py

# 2) Chỉ một mặt (unittest lọc theo tên lớp)
python3 app/thu/thu_g22_regression.py A_TenantIsolation
python3 app/thu/thu_g22_regression.py B_RBAC
python3 app/thu/thu_g22_regression.py C_FailClosed
python3 app/thu/thu_g22_regression.py D_Idempotency
python3 app/thu/thu_g22_regression.py E_WebhookSecurity
python3 app/thu/thu_g22_regression.py F_CrossTenantLeak
python3 app/thu/thu_g22_regression.py G_NoProductionOrder

# 3) Chỉ các chốt tổng kết (bảng + tiêm lỗi ngoài)
python3 app/thu/thu_g22_regression.py Z_TongKet

# 4) Toàn bộ dự án (bộ này tự được dò vì tên khớp `thu_*.py`)
sh app/thu/chay_tat_ca.sh
```

**Ghi chú môi trường:** bộ kiểm không gọi `git`, không đọc `.env`, không đọc biến `VIP_*` kế
thừa; nó đặt `VIP_HUB_DATA` vào `mktemp` **trước khi** nạp mô-đun sản phẩm. Bởi vậy gia đình
`GIT_CONFIG_*` dị dạng (`N-G18-00`/`N-G22-03`) **không** ảnh hưởng bộ kiểm này — nó chưa từng
gọi git.
