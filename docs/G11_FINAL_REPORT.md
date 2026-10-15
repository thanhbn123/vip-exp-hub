# G11 — STAGING READINESS: BÁO CÁO CUỐI

| | |
|---|---|
| Tác tử | AG-05 DEVOPS ENGINEER |
| Nhánh | `agent/g11-devops` · worktree `~/code/veh3-g11-devops` |
| Nền | `143084b` · schema **v7** |
| Ngày | 15/10/2026 |
| Máy đã đo | MacBook — `python3 3.9.6` · `node v26.7.0` · **Docker: KHÔNG CÓ** |

---

## 0. KẾT LUẬN MỘT DÒNG

**Hệ CHƯA sẵn sàng cho staging, và lý do lớn nhất không phải thiếu tài liệu — là 4 cổng kỹ
thuật chưa mở (P-1 … P-4) cộng với việc chưa có lượt Docker build nào trên máy nào.**

Lớp quan sát, lớp kiểm cấu hình, diễn tập khôi phục và runbook **đã chạy thật và đạt**. Lớp
container **đã viết xong nhưng chưa build lượt nào** — ghi là **BLOCKED**, không ghi PASS.

---

## 1. BẢNG NGHIỆM THU G11 — 7 DÒNG

| # | Mục | Kết quả | ĐO BẰNG GÌ (lệnh thật + kết quả thật) |
|---|---|---|---|
| 1 | **Docker build** | **BLOCKED** | `docker --version` → `(eval):1: command not found: docker` trên MacBook, 15/10/2026. Máy không có Docker ⇒ **chưa build lượt nào**. Thay bằng: `sh trien_khai/kiem_cu_phap.sh` (cú pháp) + `python3 trien_khai/kiem_cau_hinh.py` (nội dung tĩnh: không `COPY .env`, có `USER hub`, `FROM` ghim phiên bản, HEALTHCHECK dùng health chứ không readiness). **Cú pháp đạt KHÔNG phải build đạt.** Thiếu: một máy có Docker. |
| 2 | **Compose local** | **BLOCKED** | `docker compose version` → `command not found`. `docker compose config -q` chưa chạy được lượt nào. `kiem_cau_hinh.py` kiểm được: không bind `0.0.0.0`, không bí mật trực tiếp, có `env_file`, có `max-size` cho log. Thiếu: Docker. |
| 3 | **Health check** | **PASS (trong phạm vi nêu)** | `python3 app/thu/thu_quan_sat.py` → `Ran 45 tests … OK`. Lớp `D_HealthKhacReadiness` đo bằng cách **làm hỏng thật**: trỏ CSDL vào đường không mở được thì `suc_khoe()` vẫn `ok` (health không chạm CSDL); đặt `PHIEN_BAN_SCHEMA + 99` thì `san_sang()` chuyển `ok: False`. **NGOÀI phạm vi:** `HEALTHCHECK` của Docker chưa chạy lượt nào (dòng 1), và route HTTP `/api/v2/suc-khoe` **chưa được cắm** (bản vá P-2) — hiện chỉ gọi được qua CLI `python3 app/quan_sat.py suc-khoe`. |
| 4 | **Ca thử khôi phục CSDL** | **PASS** | `sh trien_khai/dien_tap_khoi_phuc.sh` → **mã thoát 0**. Chạy thật 12 bước trên thư mục tạm. Số đo ở mục 2. |
| 5 | **Cách ly bí mật** | **PASS (trong phạm vi nêu)** | `thu_quan_sat.B_QuetBiMatBaDang.test_b2`: dựng log thật từ bản ghi có SĐT người gửi/nhận, COD, api_key, webhook secret, passphrase; quét toàn chuỗi log ở **3 dạng** (thô · hex · base64, cộng base64 không đệm và base64url) → **rỗng**. `test_b1` đo chính bộ quét trước khi tin nó. `H_CauHinhTrienKhai`: `.env.example` không có giá trị trông như bí mật; `Dockerfile` không `COPY .env`, không `ENV` dài như secret. **NGOÀI phạm vi:** chỉ bắt được bí mật mà bộ thử **đưa vào danh sách**; không bắt bí mật rò qua stderr của thư viện khác, core dump, hay tên file tạm. |
| 6 | **Kiểm tra cấu hình** | **FAIL — 1 lỗi thật** | `python3 trien_khai/kiem_cau_hinh.py` → **mã thoát 1**, `1 loi, 7 canh bao`. Lỗi: **`.gitignore` không chặn `.env`** → một lượt `git add .` là rò cấu hình triển khai. AG-00 giữ `.gitignore`, AG-05 **không sửa** — bản vá **P-3**. 7 cảnh báo đều là P-1/P-2 (bind + header + cookie `Secure`). |
| 7 | **Diễn tập lùi local** | **PASS** | Bước B12 của diễn tập: thêm tenant `SAU-BACKUP` **sau** mốc backup → `migrate.py --rollback` → đo lại, dòng đó **đã mất đúng như mong đợi**. `migrate.py` cất bản hiện tại trước khi đè (`hub-truoc-rollback-20261015-064213.db`) nên lùi vẫn lùi lại được. |

### Hồi quy — đo bằng lệnh, không bằng trí nhớ

| Bộ | Lệnh | Kết quả |
|---|---|---|
| Python (12 bộ, gồm 45 ca mới) | `for f in app/thu/thu_*.py; do python3 "$f"; done` | **466 phép kiểm, mọi bộ `OK`** |
| E2E qua HTTP thật | `sh app/thu/chay_e2e.sh` | **41/41 đạt**, mã thoát 0 |
| `admin/health.js` | `node --check` + 5 phép đo logic bằng `node -e` | đạt |
| Cú pháp | `sh trien_khai/kiem_cu_phap.sh` | 24 `.py` + 4 `.sh` + 5 `.js` đạt; **Dockerfile/compose BLOCKED** |

> **Phạm vi câu "mọi bộ OK"** (§12.1 luật 5): con số 466 do `unittest` đếm, trên 12 file
> `app/thu/thu_*.py`, **không gồm** `thu_e2e.py` (chạy qua `chay_e2e.sh`, đếm riêng 41).
> **NGOÀI phạm vi:** 56 ca Node và 36 ca HTTP frontend của các đợt trước — AG-05 **không chạy
> lượt nào**, nên không nói gì về chúng. Con số "563" trong chỉ thị **không được kiểm lại** ở
> lượt này.

---

## 2. SỐ ĐO LƯỢT DIỄN TẬP KHÔI PHỤC

`sh trien_khai/dien_tap_khoi_phuc.sh` — chạy 15/10/2026 06:42:12 +0700, nền tạm
`/var/folders/.../veh-dientap.6LZ1Xf/du-lieu`, **mã thoát 0**.

> **Chốt an toàn đã thi hành bằng CẤU TRÚC, không bằng lời dặn:** script tự dựng thư mục tạm và
> **từ chối chạy** (mã thoát 9) nếu nền tạm hoặc `VIP_HUB_DATA` trỏ vào `~/Projects/vip-express-hub`.
> CSDL thật `~/Projects/vip-express-hub/app/du-lieu/hub.db` **không bị chạm**.

### 2.1 CSDL — trước / sau

| Phép đo | TRƯỚC (B3) | SAU khôi phục (B10) | Nhận xét |
|---|---|---|---|
| `integrity_check` | `ok` | `ok` | |
| `foreign_key_check` | 0 vi phạm | 0 vi phạm | |
| `journal_mode` | `wal` | `wal` | |
| Số bảng | 22 | 22 | |
| Phiên bản schema | v7 | v7 | |
| Kích thước | 245 760 byte | 245 760 byte | |
| SHA-256 CSDL | `2166d175f332108b…80d9fb3a` | `53114e7ec126e7a3…bdda2f67` | **KHÁC là bình thường** — backup/restore qua API SQLite không giữ nguyên byte vì WAL |
| **Tổng dòng** | **122** | **123** | lệch +1, đã khai trước, xem 2.2 |

**Số dòng từng bảng — khớp tuyệt đối trừ một bảng đã khai:**
`audit 1→2` · `carrier_accounts 5` · `carrier_providers 2` · `goi_dich_vu 3` · `khach_hang 2` ·
`permissions 24` · `role_permissions 59` · `roles 6` · `schema_version 1` ·
`tenant_memberships 8` · `tenants 2` · `users 9`.

### 2.2 Lệch +1 dòng `audit` — khai trước, có lý do ĐO ĐƯỢC

`sao_luu_khoa.khoi_phuc()` tự ghi **một** dòng audit (`app/sao_luu_khoa.py` dòng 454,
`ghi_audit=True`). Đó là hành vi **đúng** — lượt khôi phục khóa phải để lại dấu vết.

Công cụ so sánh **cố ý bắt khai con số chính xác, không cho khai cả bảng**: khai cả bảng là tắt
phép đo cho bảng đó, và từ đó một lượt mất 500 dòng `audit` cũng đi qua im lặng. Lượt đầu diễn
tập **đã FAIL** đúng ở chỗ này (mã thoát 1) trước khi delta được khai — tức là phép đo có tác
dụng thật, không phải phép đo luôn xanh.

### 2.3 Gói khóa

| Phép đo | Giá trị |
|---|---|
| Kích thước gói `.vipkb` | 1 960 byte |
| Số khóa trong gói | 1 (`key_id: goc`) |
| Số bản mã kèm theo | 5 |
| `sao_luu_khoa.py kiem` **trước** khi tin gói | `"dat": true`, `"loi": []`, `key_id_thieu: []` |
| `khoi-phuc` | `"dat": true`, `da_ghi: ["goc"]`, `bo_qua: []`, `loi: []` |
| Quyền file gói | `0o600` |

### 2.4 Phép đo quan trọng nhất — B11

Số dòng khớp **không** chứng minh khôi phục thành công: CSDL về đủ mà khóa lệch thì mọi
credentials thành rác và **không có gì báo** cho tới lượt gọi hãng đầu tiên. Nên đo riêng:

- `bao_mat.giai_ma_cred(...)` → nội dung khớp nguyên văn ✔
- `bao_mat.giai_ma_wh(...)` → nội dung khớp nguyên văn ✔

Đo **cả hai** đường vì chúng là hai hàm với AAD khác nhau. Đo một đường rồi kết luận cho cả hai
là đúng kiểu vượt phạm vi §12.1 luật 3 — và rủi ro **R-h** của dự án ghi rõ `ban_ma[]` của gói
backup **chỉ phủ `carrier_accounts`**.

### 2.5 PHẠM VI của cả lượt diễn tập — nói rõ để không ai suy rộng

**ĐO:** backup + restore CSDL · backup + kiểm + restore khóa · giải mã lại credentials và
webhook secret · rollback · `integrity_check` · số dòng từng bảng.

**NGOÀI PHẠM VI:** lượt này chạy trên **máy dựng**, trên **dữ liệu thử**, bằng **passphrase
diễn tập sinh tại chỗ**. Nó **KHÔNG** thay cho một lượt khôi phục thật trên **máy chủ sạch**
bằng **passphrase thật** — **blocker B-2 của dự án vẫn còn nguyên**. Nó cũng không đo tính
**đúng** của nội dung dữ liệu nghiệp vụ: một bảng bị ghi trắng vẫn cho `integrity_check = ok`,
nên số dòng phải so **từng bảng**, không so tổng.

---

## 3. BẢN VÁ ĐỀ XUẤT — MÔ TẢ, KHÔNG SỬA

AG-00 giữ `server.py`, `migrate.py`, `.gitignore`. AG-05 **không chạm**. Bốn bản vá dưới đây
xếp theo mức chặn.

### P-1 — `server.py`: địa chỉ bind lấy từ biến môi trường (CHẶN staging)

**Vấn đề đã đo:** `app/server.py` dòng 1009 ghim cứng
`sv = ThreadingHTTPServer(("127.0.0.1", cong), BoXuLy)`.
Trong container, `127.0.0.1` là loopback **của chính container** — Docker port mapping không với
tới được. Dịch vụ sẽ khởi động, báo health xanh **từ bên trong**, mà **không ai gọi được từ
ngoài**. Đây là hỏng im lặng: không có lỗi nào, chỉ là không ai nối được.

**Đề xuất:**
```python
# cau_hinh.py (AG-00)
# Mặc định PHẢI là 127.0.0.1: mặc định an toàn, mở ra ngoài là việc có chủ đích.
BIND_MAC_DINH = os.environ.get("VIP_HUB_BIND", "127.0.0.1")

# server.py, trong chay():
def chay(cong=cau_hinh.CONG_MAC_DINH, dia_chi=None):
    dia_chi = dia_chi or cau_hinh.BIND_MAC_DINH
    ...
    sv = ThreadingHTTPServer((dia_chi, cong), BoXuLy)
    print(f"[hub] bind {dia_chi}:{cong}")   # IN RA địa chỉ thật — đừng để ai phải đoán
```
**Kèm chốt chặn, vì mở bind là mở mặt tấn công:** khi `dia_chi` không phải loopback mà
`VIP_HUB_RESET_TOKEN=1`, hãy `SystemExit`. Hiện cờ đó bật là **lỗ hổng chiếm tài khoản**
(AG-07 ca q01b), và `trien_khai/khoi_dong.sh` đã tự chặn ở tầng container (mã thoát 5) — nhưng
chặn ở container **không** phủ lượt chạy `python3 app/server.py` trực tiếp.

### P-2 — `server.py`: header bảo mật + cookie `Secure` + route quan sát

**Vấn đề đã đo:** `grep` trên `app/server.py` cho thấy **không có** `X-Content-Type-Options`,
`Content-Security-Policy`, `Referrer-Policy`, `X-Frame-Options`. Cookie phiên (dòng 290) có
`HttpOnly; SameSite=Lax` nhưng **không** `Secure`.

**Đề xuất 2a — một chỗ duy nhất đặt header,** cắm vào `_tra()` và `_phuc_vu_tinh()`:
```python
HEADER_BAO_MAT = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Dự án KHÔNG dùng CDN và KHÔNG có thư viện ngoài, nên 'self' là chặt được thật, không phải
    # CSP trang trí. `script-src 'self'` chặn luôn inline script — đã kiểm: admin/index.html
    # chỉ nạp file .js ngoài, không có inline.
    "Content-Security-Policy": ("default-src 'self'; script-src 'self'; style-src 'self'; "
                                "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
                                "base-uri 'none'; form-action 'self'"),
}
```
Đặt ở **một chỗ** (`_tra` + `_phuc_vu_tinh`), không rải ra từng endpoint — §12.2: *lọc một chỗ,
không lọc hai chỗ*. CSP cần đo thật bằng console trình duyệt trước khi chốt: một CSP chặn mất
giao diện còn tệ hơn không có CSP, vì nó sẽ bị tắt đi cho xong.

**Đề xuất 2b — cookie `Secure` theo sơ đồ HTTPS,** không bật cứng:
```python
# cau_hinh.py: VIP_HUB_HTTPS = os.environ.get("VIP_HUB_HTTPS", "0") == "1"
cookie = (f"phien={token}; HttpOnly; SameSite=Lax; Path=/"
          + ("; Secure" if cau_hinh.VIP_HUB_HTTPS else "")
          + f"; Max-Age={cau_hinh.PHIEN_SONG_GIO * 3600}")
```
Bật cứng `Secure` làm **mọi lượt đăng nhập local qua HTTP hỏng** — trình duyệt bỏ cookie, và
màn hình chỉ nói "sai tên đăng nhập hoặc mật khẩu" trong khi mật khẩu chưa bao giờ sai. Đó
chính là ca sinh ra §12.2 của chủ dự án (mất gần ba tiếng cho một dòng thiếu). Nên gắn cờ.

**Đề xuất 2c — ba route quan sát.** Bảng route ở mục 5.

### P-3 — `.gitignore`: chặn `.env` (ĐANG LÀM `kiem_cau_hinh.py` FAIL)

**Vấn đề đã đo:** `.gitignore` hiện có `app/du-lieu/`, `*.db`, `*.db-shm`, `*.db-wal`,
`__pycache__/`, `*.pyc`, `gateway/du-lieu/`, `.DS_Store` — **không có `.env`**.

**Đề xuất:** thêm đúng ba dòng.
```gitignore
.env
.env.*
!.env.example
```
**CỐ Ý không đề xuất thêm `*.vipkb`.** Rủi ro **R-i** của dự án ghi rõ: mã hiện **từ chối** ghi
gói khóa vào mọi chỗ trong repo mà gitignore **không** chặn — đó là lớp **mạnh hơn** gitignore.
Thêm `*.vipkb` vào gitignore sẽ **làm yếu đi** và làm ca `h6` của AG-01 **hỏng**.

### P-4 — `migrate.py`: tên bản sao lưu trùng theo GIÂY ⇒ ghi đè im lặng

**Vấn đề đã ĐO BẰNG LỆNH**, không suy từ đọc mã. Hai lượt `migrate.sao_luu()` liên tiếp:
```
luot 1: hub-truoc-migrate-20261015-064137.db
luot 2: hub-truoc-migrate-20261015-064137.db
TRUNG TEN: True
```
`sao_luu()` (dòng 44–56) đặt tên theo `%Y%m%d-%H%M%S`. Hai lượt trong **cùng một giây** trả
**cùng một đường dẫn**, và `sqlite3.Connection.backup` ghi đè file đích **không báo gì**.

**Hậu quả thật:** một lượt migration hỏng, người vận hành chạy lại ngay → bản sao lưu **"trước
khi hỏng"** bị đè bằng trạng thái **sau lượt hỏng**. Đây đúng là họ hỏng mà §16.3 và §19 của
CLAUDE.md sinh ra để chặn: *ghi đè im lặng* lên thứ duy nhất dùng để lùi.

**Đề xuất:** đừng chọn tên rồi hy vọng không trùng — **từ chối trùng**.
```python
def sao_luu():
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    goc = "hub-truoc-migrate-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    dich = os.path.join(THU_MUC_SAO_LUU, goc + ".db")
    n = 1
    while os.path.exists(dich):          # trùng thì thêm hậu tố, KHÔNG ghi đè
        dich = os.path.join(THU_MUC_SAO_LUU, f"{goc}-{n:02d}.db")
        n += 1
    ...
```
Dùng `os.O_CREAT | os.O_EXCL` còn chắc hơn (nguyên tử, chặn cả hai tiến trình đua nhau), nhưng
`sqlite3.backup` cần một đường dẫn nên vòng lặp trên là mức vá nhỏ nhất đủ dùng. **Khuyến nghị
thêm:** `sao_luu()` trả về đường dẫn thì nên `assert` file vừa tạo có kích thước > 0 — một bản
sao lưu 0 byte là một bản sao lưu đã mất mà không ai biết (ca 17 của `hong-im-lang`).

---

## 4. HẰNG `DDL_G11`

Khai trong `app/quan_sat.py`. **AG-00 cắm vào migration v8.** Module **chạy được khi bảng chưa
tồn tại** — `ghi_su_kien()` trả `False` và chỉ ghi log; lớp quan sát không được tự thành nguyên
nhân sự cố mà nó định quan sát. Có ca thử canh cả hai phía (`G_GhiSuKien.test_g1`/`g2`/`g3`).

```sql
CREATE TABLE IF NOT EXISTS quan_sat_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  luc TEXT NOT NULL,                 -- giờ địa phương VN KÈM múi giờ (csdl.bay_gio)
  loai TEXT NOT NULL,                -- khoi_dong | san_sang_that_bai | trien_khai | dung
  muc TEXT NOT NULL DEFAULT 'tin',   -- tin | canh_bao | loi
  request_id TEXT,
  correlation_id TEXT,
  chi_tiet TEXT,                     -- JSON đã qua `che()`; CẤM chứa bí mật
  phien_ban_schema INTEGER,
  tien_trinh INTEGER                 -- PID, để dựng lại trình tự khi đối chiếu log máy chủ
);
CREATE INDEX IF NOT EXISTS ix_quan_sat_luc ON quan_sat_su_kien(luc);
CREATE INDEX IF NOT EXISTS ix_quan_sat_loai ON quan_sat_su_kien(loai, luc);
```

**Hai lựa chọn thiết kế, nói ra để AG-00 không phải đoán:**
1. **Không có cột `tenant_id`.** Đây là bảng **vận hành hệ**, không phải dữ liệu tenant. Thêm
   `tenant_id` sẽ mời người ta ghi việc của tenant vào đây, và lúc đó nó thành một đường rò dữ
   liệu giữa tenant mà RBAC không canh.
2. **`luc` là TEXT có múi giờ**, đúng khuôn `csdl.bay_gio()`. §12.2: mốc thời gian không nhãn
   múi giờ đã làm vault chủ dự án **kết luận ngược ba lần trong một ngày**.

---

## 5. BẢNG ROUTE — AG-00 CẮM VÀO `server.py`

| Method | Đường | Quyền | Mã trả | Gọi gì | Vì sao thế |
|---|---|---|---|---|---|
| `GET` | `/api/v2/suc-khoe` | **vô danh**, không CSRF | `200` luôn khi tiến trình sống | `quan_sat.suc_khoe()` | Bộ giám sát tiến trình và Docker `HEALTHCHECK` gọi nó. Đòi xác thực ở đây là biến một cổng health thành một cổng có thể hỏng vì lý do xác thực. Nó **không** trả gì về CSDL/khóa nên không lộ gì. |
| `GET` | `/api/v2/san-sang` | **vô danh**, không CSRF | `200` nếu sẵn sàng, **`503`** nếu không | `quan_sat.san_sang()` | **Chi tiết CHỈ cho người đã xác thực.** Người vô danh nhận `{"ok": bool}` + danh sách **tên** phép kiểm hỏng, **không** thông điệp lỗi — thông điệp có đường dẫn và tên file. Mã `503` là bắt buộc: bộ cân tải đọc **mã HTTP**, không đọc JSON. |
| `GET` | `/api/v2/platform/quan-sat/metric` | **`PLATFORM_OWNER` / `PLATFORM_ADMIN`** | `200` / `403` | `quan_sat.metric()` | Số đếm toàn hệ, vượt ranh giới tenant ⇒ chỉ vai trò platform. Dùng `self._can(nc, …)` như mọi đường platform khác. |

**Hai điều AG-00 nên cắm kèm, vì không có chúng thì request ID vô dụng:**

```python
# trong _chay(), BỌC TOÀN BỘ lượt yêu cầu:
rid, cid = quan_sat.bat_dau_yeu_cau(self._headers_thuong())
try:
    ...                       # thân _chay() hiện tại
finally:
    ms = quan_sat.ket_thuc_yeu_cau()      # XOÁ ngữ cảnh là BẮT BUỘC
    quan_sat.ghi("yeu_cau", method=method, duong=duong, ms=ms)
```
`ket_thuc_yeu_cau()` trong `finally` **không phải tuỳ chọn**: `ThreadingHTTPServer` **dùng lại
thread**, nên ID sót lại sẽ gán **sai** cho lượt sau — và một ID gán sai còn tệ hơn không có ID,
vì nó làm người chẩn đoán tin vào một chuỗi việc không tồn tại. Có ca thử canh (`C_RequestId.test_c4`).

```python
# và trả request_id ra header, để người báo lỗi đọc được nó mà không cần vào log máy chủ:
self.send_header("X-Request-Id", rid)
```

---

## 6. G11.1 … G11.8 — TỪNG MỤC, CÁI GÌ ĐÃ CÓ / CÁI GÌ THIẾU

### G11.1 Đóng gói container
| Việc | Trạng thái | Ghi chú |
|---|---|---|
| `Dockerfile` | **viết xong, CHƯA BUILD** | non-root `hub`, mã chỉ-đọc, `FROM` ghim `python:3.11-slim-bookworm`, `cryptography==43.0.1`, `COPY` **liệt kê từng đường** (không `COPY . .`) |
| `.dockerignore` | **viết xong** | **file này nằm NGOÀI danh sách sở hữu của AG-05** — mới, không của ai, xem mục 9 |
| `docker-compose.yml` | **viết xong, CHƯA CHẠY** | bind `127.0.0.1:8897`, volume có tên, `read_only`, `cap_drop: ALL`, `no-new-privileges`, trần log |
| `.env.example` | **xong** | không bí mật nào; 4 biến KMS là chỗ dành sẵn, điền cũng vô tác dụng |
| Health vs readiness | **TÁCH RỜI** | `HEALTHCHECK` cố ý gọi **health**, không gọi readiness — nó điều khiển restart, và readiness ở đó biến "CSDL chưa nâng" thành vòng lặp restart xoá luôn log khởi động |
| Script khởi động | **xong, đã soát `sh -n`** | `khoi_dong.sh`: 4 chốt (thư mục ghi được bằng **ghi thật**, cờ nguy hiểm, schema, readiness một lượt), `exec` để nhận `SIGTERM` |
| Tôn trọng `SystemExit(3)` | **có** | `khoi_dong.sh` **không tự chạy migration**, dừng với mã 3 và nói đúng lệnh phải chạy |

**Chưa đo:** digest SHA-256 của image gốc (cần `docker manifest inspect`); `cryptography` có
wheel sẵn cho `linux/arm64` hay phải biên dịch; trần `mem_limit: 512m` **là ước lượng**, chưa
đo bằng lượt tải thật.

### G11.2 Cơ sở dữ liệu
| Hạng mục | ĐÃ CÓ | THIẾU |
|---|---|---|
| Migration có phiên bản | v1→v7, backup trước khi nâng, **kiểm bảo toàn số dòng**, `--kiem`, `--rollback` | — |
| Backup | API `backup()` của SQLite (nhất quán cả khi có WAL) | **tên trùng theo giây ⇒ ghi đè im lặng** — P-4 |
| Restore | diễn tập đạt, mã thoát 0 | lượt thật trên máy chủ sạch (B-2) |
| Toàn vẹn | `integrity_check` + `foreign_key_check`, đo trước và sau | `integrity_check` **không** nói dữ liệu đúng — nên phải so **số dòng từng bảng** |
| Kết nối | **thread-local** (đã sửa SIGSEGV), WAL, `busy_timeout=10000`, `foreign_keys=ON` | — |
| Ghi đồng thời | `khoa_ghi` (RLock) serialize mọi lượt ghi — đúng mô hình WAL một writer | **Chặn chỉ trong MỘT tiến trình.** Nhiều tiến trình/bản thì `RLock` vô tác dụng; lúc đó chỉ còn `busy_timeout` của SQLite. Chưa đo ca này. |
| Đường nâng cấp | ENTRYPOINT **không** tự nâng; migration là bước riêng có người nhìn | khoá chống hai lượt migration đua nhau (hiện dựa vào "chỉ chạy một bản") |

**Về đề xuất chuyển SQLite → PostgreSQL: AG-05 KHÔNG đề xuất chuyển ở đợt này, và KHÔNG tự
chuyển.** Lý do nói rõ chứ không để treo: SQLite hiện **chưa phải** chỗ chặn. Chỗ chặn thật là
P-1…P-4 cộng 10 cổng ở RUNBOOK 10.1. Chuyển CSDL khi chưa chạy nổi một container là đổi thứ
chưa đo để chữa một bệnh chưa chẩn đoán.

Dấu hiệu **sẽ** cần Postgres, ghi ra để lần sau nhận mặt: (a) cần **nhiều tiến trình/bản** ghi
cùng lúc — `khoa_ghi` chỉ phủ một tiến trình; (b) cần **rate limit chung** giữa các bản (rủi ro
R-a); (c) cần replica đọc. Khi chạm một trong ba, lập **phương án migration RIÊNG** — đó là
quyết định của **anh Thành**, không phải của tác tử.

### G11.3 Quản lý bí mật
| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| `SecretProvider` | **có** — `SecretProvider` · `LocalSecretProvider` · `KMSSecretProvider` | đọc `app/secret_provider.py` |
| `KMSSecretProvider` | **GIAO DIỆN RỖNG CÓ CHỦ Ý — mỗi hàm ném `NotImplementedError`. CHƯA nối tới KMS nào.** AG-05 **giữ nguyên chủ ý đó**, không dựng KMS giả. | dòng 190–228 |
| Cách ly môi trường | mỗi worktree `VIP_HUB_DATA` riêng; container dùng volume riêng; diễn tập có chốt **từ chối chạy** nếu trỏ vào vùng dữ liệu thật | mã thoát 9 của `dien_tap_khoi_phuc.sh` |
| Backup khóa | **có** — gói `.vipkb`, KEK từ passphrase (PBKDF2), kiểm toàn vẹn, quét byte thô tìm bí mật | diễn tập B5/B5b, `"dat": true` |
| Xoay khóa | `tao_khoa_moi()` / `dat_khoa_hien_hanh()` **có**; bản mã mang `key_id` (`v3$…`) nên xoay được | — |
| **Xoay khóa THẬT** | **KHÔNG LÀM** — `V-13906-02` chưa cấp | — |
| Tiêm bí mật | lúc **CHẠY** qua `env_file` / volume. **Không** `COPY .env`, **không** `ENV` mang khóa | `thu_quan_sat.test_h3` |
| Master key trong Git | **KHÔNG CÓ, và sẽ không có** | khóa là **file** `$VIP_HUB_DATA/khoa/*.key` mode `0600`; đưa vào biến môi trường là đưa vào `docker inspect` và `/proc/<pid>/environ` |

### G11.4 Siết bảo mật — mỗi dòng kèm "đo bằng gì"

| Hạng mục | ĐÃ CÓ / THIẾU | Đo bằng gì |
|---|---|---|
| **HTTPS (thiết kế)** | **THIẾU** | không có TLS trong mã; `server.py` là `ThreadingHTTPServer` trần. Thiết kế đúng: proxy (Caddy/nginx) chấm dứt TLS, hub nghe loopback **sau** proxy. Cần **P-1** để bind được. Lý do 4 của PRODUCTION READINESS: **chưa đo sau proxy thật** |
| **Cookie an toàn** | **MỘT PHẦN** — có `HttpOnly; SameSite=Lax; Path=/; Max-Age`; **thiếu `Secure`** | `grep -n "Set-Cookie" app/server.py` → dòng 290 |
| **CORS** | **KHÔNG CÓ header CORS — và đó là ĐÚNG** | `grep -i "Access-Control" app/server.py` → **không có dòng nào**. Không gửi CORS = trình duyệt chặn cross-origin theo mặc định. Đây là mặc định **an toàn**; thêm CORS là **nới** ra, chỉ làm khi có nhu cầu thật |
| **CSRF** | **CÓ** — bắt header `X-Requested-With: VIPHub`, thiếu thì `403` | dòng 126–127; smoke test S5 |
| **Xác thực** | **CÓ** — PBKDF2 200 000 vòng, cookie phiên 12 giờ, khóa **TẠM** 15 phút sau 5 lần sai (cố ý **không** khóa vĩnh viễn: khóa vĩnh viễn bằng mật khẩu sai là đường cho người lạ vô hiệu hoá tài khoản bất kỳ — AG-07 ca q06) | `app/cau_hinh.py`, `app/bao_mat.py`; 57 ca `thu_bao_mat.py` |
| **RBAC** | **CÓ** — 6 vai trò, quyền tra **trong CSDL** (`role_permissions`), từ chối thì ghi audit rồi `403` | `_can()` dòng 171–179; 24 permission + 59 role_permission đo trong diễn tập |
| **Rate limit** | **CÓ** — 11 điểm, `X-Forwarded-For` **không tin mặc định** | 34 ca `thu_gioi_han.py`. **Giới hạn phải nói ra:** trần sống trong bộ nhớ **một tiến trình** ⇒ restart là mất bộ đếm, nhiều worker là trần **nhân lên** theo số worker (R-a). **Không thay WAF**, không chặn tấn công phân tán |
| **Static allowlist** | **CÓ** — danh sách trắng thư mục + đuôi, chặn `..` | dòng 180–212; smoke test S4 — ngày 14/10 AG-07 chứng minh `/app/bao_mat.py` từng trả **200** cho người vô danh, lộ secret HMAC của 5 hãng |
| **Header bảo mật** | **THIẾU HẾT 4 header** | `grep` cho `X-Content-Type-Options`/`CSP`/`Referrer-Policy`/`X-Frame-Options` → **0 dòng**. Bản vá **P-2** |
| **Xác thực webhook** | **MỘT PHẦN** — `webhook.kiem_chu_ky()` chạy **trước** khi nhận; secret mã hóa; `UNIQUE(carrier_account_id, event_id)` chống trùng **do CSDL cưỡng chế**; tenant resolve từ `carrier_account`, **không** từ payload | dòng 265–269; 68 ca `thu_webhook.py`. **THIẾU:** chữ ký webhook Viettel Post (**B-5**, tài liệu công khai không nói rõ — **không bịa cách ký**); `jt_digest` ở mức DOCUMENTED, chưa ai ký thật (**B-4**) |
| **Mã hóa credentials** | **CÓ** — AES-256-GCM + AAD, bản mã mang `key_id`; chỉ **4 hàm** được chạm secret, có ca canh (`thu_tich_hop.test_02`) | diễn tập B11 giải mã lại đạt cả hai đường |
| **Che nhạy cảm trong log** | **CÓ (mới, G11)** — `quan_sat.che()` danh sách trắng + lớp hình dạng | `thu_quan_sat` lớp `A_` và `B_`, 14 ca. `server.log_message` cũng đã cố ý chỉ in dòng request chuẩn |
| **Giới hạn body** | **CÓ** — 64 KB mặc định / 20 MB cho import, **rút hết body trước khi trả 413** (đóng ngay thì bên gửi nhận "Broken pipe" và **không đọc được mã lỗi**) | dòng 64–88 |
| **Chặn kiểu sai ở biên** | **CÓ** — `_doc_json` chặn list/dict ở chỗ chờ vô hướng | **Phạm vi chưa đóng (R-b):** số ở chỗ chờ chuỗi (`ten=5` vẫn làm `.strip()` nổ), và kiểu sai ở **tầng sâu** trong một khóa đã khai. Việc **V-13904** |

### G11.5 Khả năng quan sát — `app/quan_sat.py` (603 dòng, 45 ca thử)
| Yêu cầu | Trạng thái |
|---|---|
| Log có cấu trúc | **có** — JSONL, một dòng một bản ghi, khoá chống xen dòng (đo bằng 6 thread × 40 dòng = 240 dòng, **mọi dòng parse được**) |
| Request ID | **có** — luôn do **hệ** sinh, không nhận từ client |
| Correlation ID | **có** — nhận `X-Correlation-Id` nếu khớp mẫu; **không khớp thì BỎ và tự sinh**, không "làm sạch rồi dùng" (chuỗi đã cắt gọt không còn truy vết được sang hệ bên kia) |
| Metric sức khoẻ | **có** — `suc_khoe()` + `san_sang()` 5 phép kiểm |
| Metric lỗi | **có** — `cong()` nguyên tử (đo bằng 8 thread × 500 = **4000**, khớp đúng) |
| Sức khoẻ worker | **có** — hỏi thread thật `is_alive()`, đọc **phòng xa** vì `webhook.py` là của AG-03 |
| Metric webhook / hàng đợi | **có** — `qsize`, `dang_xu_ly`, `wh_dlq`, `wh_cho_thu_lai` |
| Dấu vết audit | **có** — `ghi_su_kien()` ghi `quan_sat_su_kien` (sau v8); dùng `csdl.audit()` sẵn có cho audit nghiệp vụ |
| **Ca thử rò bí mật 3 dạng** | **CÓ, ĐÃ CHẠY, RỖNG** — dòng 5 của bảng nghiệm thu |

**Hai điều quan trọng về cách che:**
1. **Danh sách TRẮNG trường được vào log**, không danh sách đen. Câu hỏi phân biệt của §12.2:
   *quên một dòng thì kết quả là an toàn hay hỏng?* Đen quên một tên ⇒ mật khẩu nằm trong log
   mãi (**mất im lặng**). Trắng quên một tên ⇒ log hiện `***` ở chỗ vô hại (**hỏng ồn ào**).
   Đây đúng là ngoại lệ mà §12.2 đã nêu sẵn: khi đang **chặn thứ nguy hiểm** thì bỏ sót phải là
   **an toàn**. Có ca thử canh (`test_a2`: trường mới chưa ai biết vẫn bị che).
2. **Lớp hình dạng là lớp THỨ HAI, không thay lớp thứ nhất.** Hai lớp lọc theo **hai tiêu chí
   khác nhau** (tên trường / hình dạng giá trị) nên **không che nhau** — khác với hai lớp lọc
   cùng loại mà §12.2 cấm. `thong_diep` là trường **được phép** nhưng số điện thoại trong giá
   trị vẫn bị che (`test_a4`).

**Rủi ro cố ý còn lại, ghi ra kèm cách vá:**
- Mẫu thẻ ngân hàng che bằng **chốt chữ cái + Luhn**. Lượt đầu nó **che quá tay**: biến
  `VD0987654321234567890` thành `VD<the>` — ca `test_a9` **bắt được thật**. Còn lại xác suất
  ~1/10 che sai một mã số thuần chữ số 13–19 ký tự không đứng sau chữ cái mà tình cờ qua Luhn.
  Hệ này không lưu số thẻ ở đâu (COD là `INTEGER` đồng, §16) nên đánh đổi nghiêng về **che**.
- Số đếm **mất khi khởi động lại** và **không gộp giữa nhiều tiến trình** — cùng họ với R-a.
  Vá đúng: kho đếm ngoài (Postgres hoặc Redis). **Chưa làm.** `metric()` tự in phạm vi này ra
  trong chính kết quả nó trả về, và có ca thử canh câu đó (`test_f2`).

### G11.6 Backup / Restore
`RUNBOOK` mục 7 (4 thứ, 4 chỗ) và mục 8 (3 ca thảm hoạ). Diễn tập **đã chạy**, số đo ở mục 2.
**Thiếu:** bản ngoài nhà cho gói khóa (`V-13906-03`); lượt khôi phục thật trên máy chủ sạch (B-2).

### G11.7 Runbook — `trien_khai/RUNBOOK.md`, 306 dòng
Đủ 7 phần chỉ thị yêu cầu: checklist trước triển khai (7 bước có lệnh + điều kiện đạt) · triển
khai staging · migration (bước riêng, có cảnh báo P-4) · smoke test (**6 phép đo**) · lùi (tách
**lùi mã** / **lùi CSDL**) · khắc phục thảm hoạ (3 ca) · cổng phê duyệt production (**10 cổng**,
tất cả **CHƯA**). Thêm: bảng tra nhanh 7 triệu chứng, và 3 điều tuyệt đối không làm.
**Không có bước nào tự nối lên VPS.**

### G11.8 Giao diện — `admin/health.js`
`admin/` **không có thư mục con** ✔. Logic thuần, tách khỏi DOM, nạp được ở cả `window` và Node
(cùng khuôn `admin/logic.js`). Hiện: health · readiness từng phép kiểm · phiên bản schema ·
trạng thái worker · hàng đợi/webhook/DLQ. Đã đo bằng `node --check` + 5 phép đo logic.

**Ba lựa chọn thiết kế:**
1. **Health và readiness hiện HAI dòng riêng.** `tomTat()` cố ý **không có** trường "tổng quan
   một màu" — hai câu hỏi khác nhau và câu trả lời **có thể ngược nhau** (tiến trình sống mà
   schema cũ ⇒ health xanh, readiness đỏ).
2. **Phép kiểm bị bỏ qua hiện XÁM kèm chữ "CHƯA ĐO", không hiện XANH.** Cho cái chưa đo mượn
   màu của cái đã đạt là chỗ dễ hỏng nhất của một màn sức khoẻ.
3. **"Chưa cắm route" (404) KHÁC "hệ hỏng".** Bản đầu trả "CHƯA sẵn sàng" cho cả hai trong khi
   lời bình lại nói là có phân biệt — **lời bình nói khác mã thì lời bình là thứ sẽ được tin**.
   Đã sửa; `404` → xám "Chưa cắm route", lỗi mạng → đỏ.

**DLQ > 0 là VÀNG, không XANH:** sự kiện vào DLQ là sự kiện **không tự xử lý được nữa**, phải
có người nhìn. Để nó xanh là để nó bị quên.

---

## 7. DANH SÁCH BLOCKED — mỗi mục nêu chính xác cái còn thiếu

| # | Việc | Thiếu chính xác cái gì |
|---|---|---|
| **B-G11-1** | Docker build + compose up | **Một máy có Docker.** `docker --version` và `docker compose version` đều `command not found` trên MacBook, 15/10/2026. Không có gì khác chặn — file đã viết xong và soát cú pháp. |
| **B-G11-2** | Ghim digest SHA-256 của image gốc | `docker manifest inspect python:3.11-slim-bookworm` — cần Docker. Hiện ghim **thẻ**, không ghim digest. |
| **B-G11-3** | Triển khai staging lên VPS | **`V-G11-01`, anh Thành chưa cấp quyền.** AG-05 **không** tự kết nối VPS nào, **không** chạy lệnh deploy nào. |
| **B-G11-4** | Xoay khóa mã hóa thật | **`V-13906-02` chưa cấp.** Mã **đã** xoay được (`tao_khoa_moi` + `dat_khoa_hien_hanh`, bản mã mang `key_id`), nhưng không chạy lượt nào. |
| **B-G11-5** | Nối `KMSSecretProvider` | **`KMSSecretProvider` là giao diện rỗng CÓ CHỦ Ý.** Thiếu: quyết định của anh Thành về nhà cung cấp KMS. **AG-05 KHÔNG dựng KMS giả** — dựng rồi báo production-ready là đúng kiểu hỏng §12.1. |
| **B-G11-6** | Gói khóa có bản ngoài máy | **`V-13906-03` chưa cấp.** Hậu quả: gói `.vipkb` nằm **cùng máy** với CSDL nó bảo vệ ⇒ một lượt mất ổ là mất **cả hai**. |
| **B-G11-7** | Khôi phục khóa thật trên máy chủ sạch | **Blocker B-2 của dự án.** Thiếu: passphrase thật (anh Thành giữ) + chỗ cất ngoài máy chủ + một máy chủ sạch. Diễn tập local **không thay** được. |
| **B-G11-8** | HTTPS + header bảo mật + bind ra ngoài | **Bản vá P-1 và P-2 — AG-00 cắm.** AG-05 giữ `server.py` ở mức **chỉ đọc** theo §22. |
| **B-G11-9** | `.env` nằm ngoài Git | **Bản vá P-3 — AG-00 giữ `.gitignore`.** Đang làm `kiem_cau_hinh.py` trả mã thoát **1**. |
| **B-G11-10** | Rate limit dùng được với nhiều bản | Rủi ro **R-a**: trần trong bộ nhớ một tiến trình. Thiếu: kho đếm ngoài, tức là một quyết định hạ tầng (và có thể là Postgres/Redis) — **quyết định của anh Thành**. |
| **B-G11-11** | Đo với dữ liệu lớn | Lý do 6 của PRODUCTION READINESS. `mem_limit: 512m` và `pids_limit: 512` hiện là **ước lượng**, chưa đo. |

---

## 8. RỦI RO CỐ Ý BỎ QUA — ghi ra kèm lý do và cách vá đúng

| # | Rủi ro | Vì sao chấp nhận lúc này | Cách vá đúng |
|---|---|---|---|
| r-1 | `.dockerignore` là **danh sách đen** | Lớp chặn thật là `Dockerfile` **liệt kê từng đường COPY**, không `COPY . .`. Hai lớp theo hai tiêu chí khác nhau nên không che nhau. | Giữ `COPY` liệt kê; nghiệm thu bằng **RUNBOOK 2.3** (`find` **trong image**) chứ không bằng việc đọc `.dockerignore` |
| r-2 | `quan_sat` đọc `webhook._worker` / `_hang_doi` (biến riêng của module khác) | `webhook.py` thuộc **AG-03**, AG-05 chỉ-đọc theo §22. Đã đọc **phòng xa** (`getattr`), thiếu thì báo `"CHUA DO"`, **không đoán là tốt**. | AG-03 mở một hàm công khai `webhook.trang_thai()`; AG-05 chuyển sang gọi nó |
| r-3 | Số đếm `metric()` mất khi restart, không gộp giữa tiến trình | Cùng họ R-a. Hệ hiện chạy **một bản**. | Kho đếm ngoài. `metric()` **tự in phạm vi** này ra, và có ca thử canh câu đó |
| r-4 | Mẫu thẻ còn ~1/10 che sai | Hệ không lưu số thẻ ở đâu; che sai một mã nội bộ nhẹ hơn rò một số thẻ | Bỏ hẳn mẫu thẻ nếu sau này xác nhận không có đường nào nhận số thẻ |
| r-5 | `khoi_dong.sh` bỏ qua phép kiểm `worker` | Worker do `server.chay()` bật, nên lượt readiness **trước** khi mở cổng chắc chắn thấy nó chưa sống | `san_sang()` ghi rõ `ok: null` + `"CO Y BO QUA"`; lượt readiness **sau** khởi động (`kiem_san_sang.sh`) **không** bỏ qua nó |
| r-6 | Không có khoá chống **hai lượt migration** đua nhau | ENTRYPOINT không tự nâng ⇒ chỉ có người chạy, mỗi lần một lượt | Khoá tư vấn trên file trong `$VIP_HUB_DATA` trước khi nâng — **chưa làm**, cần sửa `migrate.py` (AG-00) |
| r-7 | CSP của P-2 **chưa đo bằng trình duyệt** | Chỉ là **đề xuất**, không cắm. | Cắm xong phải mở console trình duyệt. Một CSP chặn mất giao diện **còn tệ hơn không có CSP**, vì nó sẽ bị tắt đi cho xong |

---

## 9. FILE ĐÃ ĐỔI + XÁC NHẬN QUYỀN SỞ HỮU

### Thuộc đúng danh sách AG-05 sở hữu

Cột **Dòng** đo bằng `wc -l` lúc 15/10/2026, không điền từ trí nhớ (§12.1 luật 4 — bản đầu của bảng này điền từ trí nhớ và **lệch 11/13 dòng**).

| File | Dòng | Việc |
|---|---|---|
| `Dockerfile` | 76 | mới |
| `docker-compose.yml` | 77 | mới |
| `.env.example` | 54 | mới |
| `trien_khai/RUNBOOK.md` | 306 | mới |
| `trien_khai/khoi_dong.sh` | 95 | mới |
| `trien_khai/kiem_san_sang.sh` | 55 | mới |
| `trien_khai/kiem_cu_phap.sh` | 67 | mới |
| `trien_khai/kiem_cau_hinh.py` | 248 | mới |
| `trien_khai/do_csdl.py` | 157 | mới |
| `trien_khai/dien_tap_khoi_phuc.sh` | 195 | mới |
| `app/quan_sat.py` | 603 | mới |
| `app/thu/thu_quan_sat.py` | 582 | mới |
| `admin/health.js` | 216 | mới |
| `docs/G11_FINAL_REPORT.md` | — | file này |

### MỘT file NGOÀI danh sách — khai ra để AG-00 quyết
`.dockerignore` (25 dòng, **mới**). **Không nằm trong danh sách sở hữu của AG-05** và **không
thuộc agent nào khác**; nó không tồn tại trước lượt này. Lý do tạo: `Dockerfile` không đúng được
nếu không có nó — build context sẽ mang theo `*.key`, `*.db` và `.env` của máy dựng. AG-00 giữ
hay chuyển đi thì tuỳ, nhưng **không được xoá mà giữ nguyên `Dockerfile`**.

### Xác nhận KHÔNG chạm file người khác sở hữu
`git status --short` **không** có dòng nào cho: `app/server.py` · `app/csdl.py` ·
`app/migrate.py` · `app/cau_hinh.py` · `app/bao_mat.py` · `app/sao_luu_khoa.py` ·
`app/secret_provider.py` · `app/gioi_han.py` · `app/webhook.py` · `app/don_hang.py` ·
`docs/SHARED_CONTRACTS.md` · `.gitignore` · `admin/admin.js` · `admin/logic.js` · `gateway/`.

Mọi thứ cần sửa trong các file đó đã thành **bản vá đề xuất P-1 … P-4** ở mục 3, **mô tả, không
sửa**. **Không push remote. Không deploy. Không kết nối VPS nào. Không xoá dữ liệu nào.**
