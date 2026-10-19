> **CẬP NHẬT 2026-10-19 — TÀI LIỆU HÃNG ĐÃ ĐỌC ĐƯỢC.** Owner cung cấp Google Docs chính thức;
> toàn văn đã tải và đối chiếu trong `docs/BEST_EXPRESS_VERIFIED_CONTRACT.md`. Các câu trong tệp
> này nói “Google Docs không đọc được”/“schema chưa xác minh” là **trạng thái lịch sử**, không
> còn đúng. Schema Order/Add, auth Bearer, Query test host và bảng 23 mã đã được sửa theo tài liệu.
> REAL PASS vẫn **BLOCKED** vì chưa có credential/phê duyệt.

> **CẬP NHẬT 2026-10-19 — BÀN NGHIỆM THU THẬT.** `pages/best-uat.html` +
> `admin/best_uat.js` đã được hoàn thiện cho tài khoản BEST thật: phê duyệt phiên, nhập
> Username/Password/`ems-key` qua HTTPS, kiểm tra đăng nhập, báo cước, tạo đơn sandbox,
> tracking + `traceLogs`, tải PDF qua backend, Order/Update, UpdateAddress (1/2/3), Cancel,
> webhook URL + Bearer. Hai màn cấu hình/kiểm tra trong SPA cũ dẫn sang bàn này thay vì dùng
> form credential sai. URL và quy trình: `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md`.
> Bộ Playwright BEST: **15/15 pass**.

# BEST EXPRESS — GIAO DIỆN 12 MÀN (AGENT B4)

> Trạng thái: **LOCAL ONLY · MOCK PASS (phần cần backend BEST) + REAL PASS (các đường đọc đã có)**
> Ngày đo: 2026-10-19 · nhánh `b4-frontend` · nền `best/integration @ cb23312` (main `de740dc`)
> Không push GitHub · không deploy VPS · không gọi API hãng BEST · không tạo đơn thật · không dùng credential thật.

---

## 1. Phạm vi đã ghi

| Tệp | Loại | Ghi chú |
|---|---|---|
| `admin/best.js` | **mới** | Toàn bộ 12 màn + logic 5 trạng thái + form credential an toàn. Không chứa secret. |
| `admin/admin.js` | sửa **chỉ phần đăng ký menu** | Thêm nhóm menu `BEST Express` (12 mục) và khối nạp `admin/best.js` theo yêu cầu. Không sửa màn khác. |
| `pages/best.html` | **mới** | Trang riêng 12 tab; không script nội tuyến (CSP `script-src 'self'`). |
| `thu_giao_dien/best_express.spec.js` | **mới** | E2E Playwright, 15 ca, mỗi ca có đối chứng âm. |
| `docs/BEST_EXPRESS_UI.md` | **mới** | Tài liệu này. |

**Không sửa:** `admin/billing.js` · `admin/logic.js` · `admin/ban_phim.js` · `app/**` (kể cả `app/server.py`) · `app/adapter*.py` · `assets/css/style.css` · các trang demo khác.

### 1.1. Trạng thái git — CHƯA COMMIT ĐƯỢC

Lượt này **không commit được**: `git add` trả
`fatal: Unable to create '…/.git/worktrees/b4-frontend/index.lock': Operation not permitted`
(worktree `.git` nằm ngoài vùng ghi của phiên). **Không tự vượt chốt, không xoá lock.**
Năm tệp ở trên đang là thay đổi chưa commit trong worktree `b4-frontend`; **nhờ AG-00 commit hộ**.

---

## 2. Mười hai màn hình

Mã màn (dùng trong `hash` và menu) · tiêu đề · đường đọc/ghi · trạng thái bằng chứng.

| # | Mã màn | Tiêu đề tiếng Việt | Đường dùng | Bằng chứng |
|---|---|---|---|---|
| 1 | `best-danh-sach-hang` | BEST · Danh sách hãng | `GET /api/v2/hang` · `GET /api/v2/tai-khoan-hang` | **REAL** trên nền cô lập: đọc được J&T + Viettel Post; BEST được thêm vào danh sách mục tiêu với nhãn `CHƯA CÓ PROVIDER · CHỜ BACKEND` khi backend chưa có `carrier_providers.ma='best'` |
| 2 | `best-cau-hinh-tai-khoan` | BEST · Cấu hình tài khoản | `POST /api/v2/tai-khoan-hang` · `POST /api/v2/tai-khoan-hang/<id>/rotate` | **MOCK PASS** cho BEST (backend từ chối `hang='best'` tới khi có adapter). Form credential là HTML password, không hiện lại secret |
| 3 | `best-kiem-tra-ket-noi` | BEST · Kiểm tra kết nối | `POST /api/v2/tai-khoan-hang/<id>/kiem-ket-noi` | **MOCK PASS** — route **CHƯA CÓ** trong `app/server.py` (đã khai trong `admin/logic.js → API_CHO_BACKEND`) |
| 4 | `best-tao-don` | BEST · Tạo đơn | `POST /api/v2/don/kiem` | **REAL** cho phần kiểm dữ liệu (route đã có, chỉ đọc). Gửi BEST **BỊ KHOÁ** — không đoán endpoint/request schema của hãng |
| 5 | `best-van-don` | BEST · Danh sách vận đơn | `GET /api/v2/don?gioi_han=200&hang=best` (hoặc bỏ `hang` khi chọn *Tất cả*) | **REAL**: mặc định BEST = 0 đơn + câu giải thích; chọn *Tất cả* đọc được 8 đơn mẫu thật của nền cô lập |
| 6 | `best-chi-tiet-don` | BEST · Chi tiết đơn | `GET /api/v2/don/<id>` | **REAL**: dữ liệu khớp `GET /api/v2/don?gioi_han=5`; ID không tồn tại trả 404 rõ ràng |
| 7 | `best-lich-su-van-chuyen` | BEST · Lịch sử vận chuyển | `GET /api/v2/don/<id>/hanh-trinh` | **REAL**: số mốc và mã đơn khớp API |
| 8 | `best-tra-cuu-hanh-trinh` | BEST · Tra cứu hành trình | `GET /api/v2/don?q=<từ khoá>&gioi_han=20` | **REAL**: tìm đúng `ma_don`; từ khoá rác trả rỗng có lý do |
| 9 | `best-tinh-cuoc` | BEST · Tính cước | Không gọi mạng | **KHÔNG BỊA GIÁ**: chỉ tính khối lượng quy đổi thể tích (công thức 6000 cm³/kg, ghi rõ không phải biểu cước BEST). Không có số tiền nào |
| 10 | `best-in-van-don` | BEST · In vận đơn | `GET /api/v2/don/<id>/nhan` | **MOCK PASS** cho metadata nhãn; luật thật: chỉ mở nút in khi `nhan_that=true` **và** `la_mock=false`; nhãn mock bị watermark + khoá nút |
| 11 | `best-theo-doi-webhook` | BEST · Theo dõi webhook | `GET /api/v2/webhook/su-kien?gioi_han=200` | **MOCK PASS** cho payload BEST (nền cô lập không có webhook BEST thật). Bộ lọc `hang='best'` được đo: 2/3 sự kiện, J&T không lọt |
| 12 | `best-nhat-ky-loi` | BEST · Nhật ký lỗi đồng bộ | `GET /api/v2/audit` | **MOCK PASS** cho payload audit; màn nói rõ **CHƯA CÓ endpoint nhật ký đồng bộ BEST riêng**, chỉ lọc audit chung |

### 2.1. BEST trong danh sách hãng

`GET /api/v2/hang` hiện trả **J&T Express** (`jt`) và **Viettel Post** (`vtp`) — đo thật trên nền cô lập. Khi backend chưa có provider `best`, màn **Danh sách hãng** tự bổ sung một dòng **BEST Express** với nhãn:

- `CHƯA CÓ PROVIDER · CHỜ BACKEND` (không phải "đã kết nối"),
- tài khoản `chưa cấu hình`,
- trạng thái lấy từ cùng bộ quyết định 5 trạng thái (mục 3), **không** suy ra từ việc "có tài khoản".

Đây là cách "thêm BEST vào danh sách hãng" mà không bịa rằng backend đã hỗ trợ BEST.

---

## 3. Năm trạng thái — luật quyết định

Nguồn duy nhất: `admin/best.js → trangThaiKetNoi({ provider, tai_khoan })`.

| Mã | Nhãn | Điều kiện vào | Không bao giờ được vào khi |
|---|---|---|---|
| `chua_cau_hinh` | **CHƯA CẤU HÌNH** | Không có tài khoản BEST, hoặc có tài khoản nhưng **không có credential** | — |
| `cho_xac_minh` | **CHỜ XÁC MINH** | Có credential, **chưa có** `ok=true` kèm thời điểm | Backend chỉ khai `trang_thai_ket_noi='da_ket_noi'` mà thiếu bằng chứng (khi ấy vẫn CHỜ XÁC MINH + cảnh báo) |
| `da_ket_noi` | **ĐÃ KẾT NỐI** | `kiem_ket_noi.ok === true` **và** có `luc` **và** tài khoản đang bật | Chỉ lưu credential; backend khai suông; `ok=true` nhưng thiếu `luc` (→ CẦN XỬ LÝ) |
| `mat_ket_noi` | **MẤT KẾT NỐI** | Từng kết nối (`da_tung_ket_noi`/`truoc_do.ok`) rồi lượt mới `ok=false`, **hoặc** đã `ok=true` nhưng tài khoản bị khoá | Lỗi xác thực lần đầu (→ CẦN XỬ LÝ) |
| `can_xu_ly` | **CẦN XỬ LÝ** | Lượt kiểm tra đầu thất bại / lỗi xác thực (401·403) / trạng thái lạ / dữ liệu mâu thuẫn / tài khoản khoá trước khi xác minh | — |

Bảng 5 trạng thái được **hiện ngay trên màn Kiểm tra kết nối** (mã `#best-bang-trang-thai`), kèm cột *Điều kiện vào* và đánh dấu **ĐANG Ở ĐÂY** — người vận hành không phải suy luận từ một nhãn duy nhất. E2E ca 04 đòi bảng có **đúng 5 dòng** và **đúng một** dòng đang ở.

### 3.1. Bằng chứng hiển thị kèm

Mọi màn có khối trạng thái đều hiện **ba dòng bằng chứng**, không chỉ nhãn:

- `Credential`: đã lưu / chưa lưu — **không giá trị, không độ dài, không 4 ký tự cuối**;
- `Đăng nhập API thành công gần nhất`: thời điểm + HTTP + số ms, hoặc `CHƯA CÓ lượt đăng nhập API nào`;
- `Tài khoản đang bật`: có / không / chưa rõ.

Câu chốt trên giao diện: *“Lưu credential một mình KHÔNG đủ — khi ấy trạng thái là CHỜ XÁC MINH.”*

### 3.2. Hợp đồng dữ liệu trạng thái (đề xuất — **CHƯA KIỂM CHỨNG**)

`GET /api/v2/tai-khoan-hang` cần trả, cho tài khoản BEST:

```json
{
  "id": 77, "hang": "best", "ten": "...", "moi_truong": "mock",
  "kich_hoat": 1,
  "credentials_doi_luc": "2026-10-19 10:00:00+0700",
  "co_credentials": true,
  "da_tung_ket_noi": true,
  "kiem_ket_noi": { "ok": true, "luc": "2026-10-19 10:05:00+0700", "tre_ms": 42, "ma_http": 200, "loi": null, "loai": null }
}
```

Giao diện đọc được cả dạng phẳng cũ (`ket_noi_ok`, `ket_noi_luc`, `ket_noi_ma_http`, `ket_noi_loi`). **Không** đọc/không hiện `credentials_ma_hoa`, `webhook_secret_ma_hoa`, token.

---

## 4. Cấu hình credential an toàn

- Ô `Mã đối tác`, `Khóa bí mật`, `Token` là `type="password"`, `autocomplete="off"/"new-password"`, **không có value**, không lưu localStorage/sessionStorage.
- Tên trường credential của BEST **CHƯA KIỂM CHỨNG** (tài liệu Google Docs chưa đọc được). Ba khóa `ma_doi_tac` · `khoa_bi_mat` · `token` là **đề xuất nội bộ**, ghi rõ trên form.
- Trang chạy HTTP loopback (local): **chặn gửi** credential cho tới khi người dùng tick xác nhận *“đây là credential MOCK, không phải credential thật”*. Khi chặn, form **không bị dựng lại** — không mất dữ liệu đã gõ.
- Ngay trước khi gửi, các ô password bị xoá giá trị; sau khi gửi, form mới rỗng.
- Phản hồi `webhook_secret_mot_lan` (nếu backend trả) **không được in ra**; E2E dùng canary để chứng minh.
- Mật khẩu/token không vào `console`, không vào audit, không vào response của giao diện.

---

## 5. E2E — bằng chứng đo được

**Lệnh thật:**

```sh
sh thu_giao_dien/chay.sh thu_giao_dien/best_express.spec.js
```

**Kết quả (2026-10-19, lượt `/tmp/best-e2e-final5.log`):**

- **exit code THẬT: 0** (in bởi trap của `chay.sh`: `[giao-dien] mã thoát THẬT 0`)
- **15 passed · 0 failed · 0 skipped** (Playwright list reporter)
- Thời gian: **22.2s** (log `/tmp/best-e2e-final5.log`)
- Nền: SQLite tạm, cổng ngẫu nhiên `19680`, bind `127.0.0.1`; máy chủ tắt đúng PID, mã `143 = SIGTERM(15)` do chính bộ dọn gửi.
- Chromium đã ghim: `node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell`
  - **sha256 `a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040`** — ca 00 đo lại và khớp
  - **version `141.0.7390.37`** — ca 00 đo `browser.version()`
  - Đối chứng âm: hash của `icudtl.dat` trong cùng gói **khác** hash binary ⇒ phép đo hash không phải hằng số dán.

### 5.1. Mười lăm ca

| Ca | Nội dung | Loại bằng chứng |
|---|---|---|
| 00 | Binary ghim (sha256 + version) + đối chứng hash tệp khác | REAL |
| 01 | 12 màn có trên menu thật, mở đủ 12, tiêu đề khớp; bảng hãng có BEST + J&T + Viettel Post; không lỗi console | REAL |
| 02 | 5 trạng thái; payload credential-only khai `da_ket_noi` **không** được hiện ĐÃ KẾT NỐI | REAL UI logic, payload MOCK |
| 03 | Credential: chặn HTTP khi chưa xác nhận; request mang canary; DOM không lộ canary/secret webhook; ô password rỗng sau gửi | MOCK POST |
| 04 | Kiểm tra kết nối: 401 → CẦN XỬ LÝ; `ok=true` → ĐÃ KẾT NỐI; 404 → giữ nguyên | MOCK route |
| 05 | Tính cước: 30×20×10 cm, 800 g → 1000 g; không có số tiền bịa | REAL UI, no network |
| 05b | Tạo đơn: `POST /api/v2/don/kiem` THẬT — hợp lệ/chưa hợp lệ; **không** POST tạo đơn, nút gửi BEST khoá | REAL |
| 06 | Vận đơn BEST rỗng có lý do; *Tất cả* đọc 8 đơn thật; chi tiết/hành trình khớp API; ID sai báo 404 | REAL |
| 07 | Tra cứu mã đơn thật ra kết quả; mã rác rỗng có lý do | REAL |
| 08 | Nhãn `nhan_that=false` → watermark + nút khoá; `true` → mở | MOCK metadata |
| 09 | Webhook lọc đúng BEST (2/3), J&T không lọt | MOCK payload |
| 10 | Audit lọc đúng liên quan (2/3), `dang_nhap` không lọt | MOCK payload |
| 11 | Không secret nào lên DOM (5 màn); mọi request ở `127.0.0.1`; không ô password có value | REAL request + MOCK payload |
| 12 | `pages/best.html`: 12 tab, mở được, **0 script nội tuyến** | REAL |
| 13 | 12 màn không tràn ngang ở 375px; đối chứng dương: cố ý tạo 900px thì phép đo **bắt được** | REAL |

### 5.2. Đối chứng âm tiêu biểu

1. **Chống "nói dối là đã kết nối":** payload có `credentials_doi_luc` + `trang_thai_ket_noi='da_ket_noi'` nhưng không có `kiem_ket_noi` → E2E đòi `cho_xac_minh`, cấm `da_ket_noi`, và đòi cảnh báo “thiếu bằng chứng”.
2. **Chống lộ secret:** canary nằm trong request POST và trong phản hồi mock (chứng minh bộ dò có việc để dò), nhưng **không** được có trong `innerHTML`/`innerText` của 5 màn.
3. **Chống in nhãn giả:** `nhan_that=false` ⇒ watermark + nút in `disabled`; chỉ `nhan_that=true && la_mock=false` mới mở.
4. **Chống bịa cước:** khu báo giá không khớp regex số tiền `₫`; không gọi đường `tinh-cuoc` đoán trước.
5. **Chống bịa dòng:** webhook 3 sự kiện → bảng BEST đúng 2; audit 3 mục → bảng đúng 2; đơn BEST rỗng → đúng 1 dòng `.trang-thai-rong` có lý do.
6. **Chống "tràn ngang 0 vì phép đo hỏng":** ca 13 cố ý thêm phần tử 900px và đòi phép đo phát hiện.
7. **Chống "hash ghim là hằng số":** hash tệp khác phải khác.

### 5.3. Hồi quy bộ cũ (12 mục menu mới không được làm hỏng bộ đang có)

```sh
sh thu_giao_dien/chay.sh \
  thu_giao_dien/01_luong_chinh.spec.js \
  thu_giao_dien/02_bo_cuc.spec.js \
  thu_giao_dien/03_quyen.spec.js \
  thu_giao_dien/04_nhan_va_man_dot3.spec.js
```

Kết quả đo được: **exit code 0 · 27 passed · 0 failed · 0 skipped** (1.2m, log `/tmp/best-regression-1.log`).
Trong đó `02_bo_cuc` đo **cả 42 màn trên menu** (30 màn cũ + 12 màn BEST) ở **375 / 768 / 1280px**: mọi màn BEST đều `tài liệu lệch 0px; 0 phần tử tràn ngoài .cuon-ngang`.

Sau khi thêm bảng 5 trạng thái vào màn Kiểm tra kết nối, chạy lại riêng `02_bo_cuc.spec.js`: **8 passed · 0 failed · exit 0** (46.5s, log `/tmp/best-regression-3.log`); màn `best-kiem-tra-ket-noi` vẫn `0px` ở cả 375 / 768 / 1280px.

---

## 6. MOCK PASS ≠ REAL PASS

**Đây là MOCK PASS cho phần lõi tích hợp BEST.** Cụ thể:

- **MOCK:** "kiểm tra kết nối BEST", "lưu credential BEST", "metadata nhãn BEST", "webhook BEST", "audit BEST", "5 trạng thái với dữ liệu BEST". Các ca này dùng `page.route` để giả lập phản hồi backend. **Không có lời gọi nào tới API hãng BEST.**
- **REAL:** danh sách hãng `GET /api/v2/hang`; tài khoản hãng `GET /api/v2/tai-khoan-hang`; đơn `GET /api/v2/don`; chi tiết/hành trình `GET /api/v2/don/<id>`; tìm kiếm `GET /api/v2/don?q=`; kiểm dữ liệu `POST /api/v2/don/kiem`. Tất cả chạy trên nền cô lập `chay.sh`, bind `127.0.0.1`. Riêng **payload BEST** của webhook/audit là MOCK; đường đọc thật của chúng được đo ở ca 01 khi mở màn.
- **Không claim REAL PASS với BEST Express** vì backend chưa có adapter/provider BEST và chưa có credential thật.

---

## 7. Chưa kiểm chứng / BLOCKED

| Mục | Trạng thái | Lý do |
|---|---|---|
| Tài liệu API BEST (Google Docs) | **CHƯA ĐỌC ĐƯỢC** | Không truy cập trong lượt này. Tên trường credential và endpoint của hãng **CHƯA KIỂM CHỨNG** |
| `POST /api/v2/tai-khoan-hang/<id>/kiem-ket-noi` | **CHỜ BACKEND** | Chưa có route trong `app/server.py`; đã khai ở `admin/logic.js → API_CHO_BACKEND` |
| Adapter/provider BEST (`carrier_providers.ma='best'`) | **CHỜ BACKEND** | `POST /api/v2/tai-khoan-hang` từ chối `hang='best'` với “hãng chưa có adapter” |
| Gửi đơn BEST thật | **BLOCKED** | Không có adapter, không có route đã xác nhận; giao diện không đoán endpoint. Nút gửi bị khoá và ghi rõ lý do |
| Nhãn vận đơn BEST thật | **BLOCKED** | Backend chỉ trả siêu dữ liệu; mọi adapter `CHO_PHEP_LIVE=False` |
| Biểu cước BEST | **CHƯA KIỂM CHỨNG** | Không có biểu cước/đường báo giá đã xác nhận; giao diện không hiện số tiền |
| Nhật ký lỗi đồng bộ BEST riêng | **CHỜ BACKEND** | Chưa có endpoint; màn đọc audit chung và nói rõ |
| Credential thật / môi trường sandbox–production | **BLOCKED** | Cấm dùng credential thật; backend khoá `moi_truong != 'mock'` |

### 7.1. Đo trực tiếp backend hiện tại (curl, tài khoản `shopa-owner`, nền cô lập)

| Lệnh | Kết quả THẬT |
|---|---|
| `POST /api/v2/tai-khoan-hang` với `{"hang":"best","moi_truong":"mock",...}` | **HTTP 400** · `{"loi":"hãng chưa có adapter"}` — không tạo tài khoản, không lưu credential |
| `POST /api/v2/tai-khoan-hang/1/kiem-ket-noi` | **HTTP 404** · `{"loi":"không có đường này"}` — màn hiện CHỜ BACKEND, không tự nâng trạng thái |

Hai phép đo này là lý do giao diện **không** được phép coi "đã lưu credential" là "đã kết nối", và là lý do nút gửi BEST bị khoá.

---

## 8. Cách chạy lại

```sh
# 1) Toàn bộ ca BEST (dựng nền cô lập, tắt máy chủ đúng PID)
sh thu_giao_dien/chay.sh thu_giao_dien/best_express.spec.js

# 2) Chỉ một ca
sh thu_giao_dien/chay.sh thu_giao_dien/best_express.spec.js -g "03 —"

# 3) Hồi quy menu/bố cục/quyền (12 mục BEST mới không được làm hỏng bộ cũ)
sh thu_giao_dien/chay.sh \
  thu_giao_dien/01_luong_chinh.spec.js \
  thu_giao_dien/02_bo_cuc.spec.js \
  thu_giao_dien/03_quyen.spec.js \
  thu_giao_dien/04_nhan_va_man_dot3.spec.js
```

Yêu cầu môi trường:

- `node_modules/@playwright/test` (1.56.1),
- Chromium ghim ở trên (sha256 đã ghi),
- **không** đặt `VIP_GD_GOC` bằng tay; `chay.sh` tự dựng nền và tắt máy chủ.

---

## 9. Ghi chú kỹ thuật

- `admin/best.js` được nạp **một lần** khi màn BEST đầu tiên được bấm; `admin/admin.js` chỉ thêm menu + khối đăng ký. Lý do: `admin/index.html` ngoài phạm vi ghi của làn B4.
- Màn BEST dùng chung `#tieu-de` và `#man` của SPA, nên mọi bộ thử cũ đo được chúng như màn thường (không có "màn ma").
- `pages/best.html` tự dựng 12 tab, cùng logic `VIPBEST.MAN` — không có bản sao thứ hai của quyết định trạng thái.
- Không thay đổi kiến trúc multi-tenant: mọi request đều là `/api/v2/*` cùng origin; `tenant_id` do backend lấy từ phiên, giao diện không gửi và không chọn tenant.
- Không hạ TLS, không tắt xác minh chứng chỉ, không dùng HTTP cho dữ liệu thật. Local loopback chỉ dùng cho credential MOCK và có chốt xác nhận.
- Không xoá dữ liệu, không reset DB, không đụng adapter hiện có.
