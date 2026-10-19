# BEST EXPRESS — BÀN GIAO OWNER UAT

> **CẬP NHẬT 2026-10-19 20:00 — UI ĐÃ MỞ THÊM.** Bàn nghiệm thu có thêm mục 8:
> Order/Update, UpdateAddress (1/2/3), Order/Cancel; nút **Tải PDF (qua HTTPS)**; nút copy URL
> webhook + trạng thái Bearer. Tài khoản test công khai trong DOCX đã **đo là bị khoá**
> (`[404] The account not found or have been locked`). Bằng chứng và quy trình đầy đủ:
> `docs/BEST_EXPRESS_DOCX_AUDIT.md` và `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md`.

**Trạng thái:** `READY FOR OWNER UAT (LOCAL)` — **KHÔNG phải REAL PASS**, **KHÔNG phải OWNER
APPROVED**. Mọi thao tác thật còn phụ thuộc credential, phê duyệt Owner và URL webhook công khai.

**HEAD mã:** `80e2c60` trên `best/integration` (commit tài liệu này nối tiếp; xem `git log`).
`main` = `de740dc`, không push/deploy.

---

## 1. URL ĐĂNG NHẬP HỆ THỐNG NGHIỆM THU

Chạy script (tự tạo chứng chỉ tự ký localhost, bật HTTPS, bật cổng Owner):

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub
./trien_khai/best_nghiem_thu.sh 'OWNER-UAT-2026-10-19'
```

Script in ra:

- **Quản trị:** `https://localhost:8897/admin/`
- **Bàn nghiệm thu BEST:** `https://localhost:8897/pages/best-uat.html`
- **Tài khoản hub demo:** đọc `$VIP_HUB_DATA/TAI-KHOAN-DEMO.md` — **không in mật khẩu ra chat/log**.
- **Webhook:** nếu khai `VIP_HUB_PUBLIC_BASE_URL=https://<tunnel-host>` thì URL công khai; nếu
  không, script nói thẳng URL chỉ là đường dẫn nội bộ và BEST không gọi được `127.0.0.1`.

Chứng chỉ tự ký: trình duyệt sẽ cảnh báo; chọn “tiếp tục đến localhost”. Không dùng chứng chỉ này
cho Internet.

Nếu chỉ thử mock/local, có thể chạy `python3 app/server.py` và mở `http://127.0.0.1:8897/...`;
**credential thật bị chặn trên HTTP** (xem §7).

---

## 2. CHỨC NĂNG CÓ THỂ THAO TÁC

Trang `/pages/best-uat.html` (gọi backend nội bộ, không gọi thẳng hãng):

| # | Chức năng | Trạng thái |
|---|---|---|
| 1 | Xem trạng thái hợp đồng/TLS/quyền | **HOẠT ĐỘNG** — `GET /api/v2/best/trang-thai?tls=1` |
| 2 | Tạo tài khoản BEST mock/sandbox | **HOẠT ĐỘNG** — `POST /api/v2/tai-khoan-hang` |
| 3 | Nhập Username/Password, mã hoá khi lưu | **HOẠT ĐỘNG** — AES-256-GCM qua `bao_mat.ma_hoa_cred` |
| 4 | Chọn môi trường mock/sandbox | **HOẠT ĐỘNG**; production chỉ đọc, ghi bị khoá |
| 5 | Kiểm tra kết nối/đăng nhập thật | **HOẠT ĐỘNG sau phê duyệt** — `POST /api/v2/best/kiem-ket-noi` |
| 6 | Hiển thị lỗi cụ thể | **CÓ** — mã lỗi/HTTP/Endpoint/TLS; không trả token |
| 7 | Trạng thái quyền API | **CÓ** — 8 endpoint, 23 mã, giới hạn 10/50, token 30 ngày |
| 8 | Cấu hình webhook Bearer | **HOẠT ĐỘNG** — `POST /api/v2/best/webhook-bearer` |
| 9 | Báo cước/COD/phí | **HOẠT ĐỘNG sau phê duyệt** — `POST /api/v2/best/bao-gia` |
| 10 | Tạo đơn sandbox | **HOẠT ĐỘNG sau phê duyệt** — `POST /api/v2/best/tao-don` |
| 11 | Tra cứu vận đơn | **HOẠT ĐỘNG sau phê duyệt** — `POST /api/v2/best/tra-cuu` |
| 12 | In PDF | **HOẠT ĐỘNG sau phê duyệt** — `POST /api/v2/best/in` |
| 13 | Cập nhật đơn/địa chỉ/hủy | **HOẠT ĐỘNG** — mục 8 của bàn nghiệm thu; `cap-nhat`/`sua-dia-chi`/`huy` |
| 14 | Lịch sử đồng bộ/nhật ký lỗi | **HOẠT ĐỘNG** — `GET /api/v2/best/lich-su` |

Trang 12 màn cũ `pages/best.html` vẫn là bản demo/mock; banner có liên kết sang bàn UAT.

---

## 3. TÌNH TRẠNG API BEST VÀ QUYỀN TÀI KHOẢN

- **Hợp đồng:** đã đọc toàn văn Google Docs (2026-10-19), xem
  `docs/BEST_EXPRESS_VERIFIED_CONTRACT.md` và `docs/BEST_EXPRESS_DOCX_AUDIT.md`.
- **8 endpoint:** Login, Add, Update, UpdateAddress, Cancel, Query, EstimateFee, PrintWayBill.
- **Auth:** Login `{Username, Password}` → `{token}`; API khác `Authorization: Bearer`; token
  **30 ngày**. `ems-key` tuỳ chọn.
- **ServiceId:** **12491** (Eco); 12490 không dùng.
- **Đơn vị:** gram / mm / VND decimal.
- **Địa chỉ:** 2 cấp mới — `District = " "`, City + Ward bắt buộc.
- **Query:** tối đa **10** mã; host TEST **`sea-edi-hxtest.800best.com`**.
- **Print:** tối đa **50** mã; trả `Guid/Url`.
- **23 mã trạng thái:** đã đồng bộ, gồm nhãn chữ `customer Cancel` tương đương `2`.
- **Quyền tài khoản:** **CHƯA CÓ** credential sandbox/production. Tài khoản test công khai trong
  tài liệu **không được dùng** (có thể đã khoá; không phải credential của Owner).
- **REAL PASS:** **BLOCKED** — chưa có lượt gọi có xác thực, chưa có phản hồi thật của 8 API.

---

## 4. TÌNH TRẠNG HTTPS

- Đã đo TLS **không gửi credential** (2026-10-19):
  - `sgp-seaedi-test.800best.com:443` — TLS 1.2, cert `*.800best.com`, GlobalSign, hết hạn
    2026-11-28.
  - `sgp-seaedi.800best.com:443` — TLS 1.2, cùng cert.
  - `sea-edi-hxtest.800best.com:443` — TLS 1.2, cùng cert.
  - `curl -I https://<host>/` trả 405 (chỉ POST) — TLS/HTTP hoạt động.
- **Đường thật dùng HTTPS**, không dùng HTTP plaintext. Tài liệu ghi HTTP nhưng TLS đã được đo;
  đây là khác biệt có bằng chứng.
- **UI local:** script bật HTTPS tự ký; credential thật chỉ nhận qua HTTPS. Nếu chạy HTTP, UI
  chặn credential thật.
- **Chưa đo:** chứng chỉ/hostname của một endpoint production đã được Owner duyệt; HTTP status
  thật của 8 API.

---

## 5. TÌNH TRẠNG WEBHOOK

- **Xác thực thật:** JWT **Bearer** theo tài liệu; token lưu mã hoá theo `tenant_id + account_id`
  (`xac_thuc_best.luu_bearer_webhook` / `kiem_bearer_webhook`).
- **Mock HMAC** vẫn giữ riêng cho tài khoản `moi_truong=mock`; không dùng cho thật.
- **Đã đo:** E2E 59 ca, gồm Bearer đúng → 200 + event + đơn; Bearer sai → 401, không ghi.
- **ACK:** `{"Result":1,"Message":""}` sau khi lưu bền; lỗi lưu → 500 `Result=0`.
- **Chống trùng/tennat:** UNIQUE CSDL, tenant từ account, 23 mã, 605→606.
- **BLOCKED:** chưa có URL công khai để BEST gọi (`VIP_HUB_PUBLIC_BASE_URL`/tunnel), chưa có
  Bearer token thật do BEST cấu hình, chưa có callback thật.

---

## 6. DANH SÁCH LỖI CÒN LẠI

| # | Lỗi / khoảng trống | Loại | Ảnh hưởng |
|---|---|---|---|
| 1 | Chưa có credential sandbox/production | **BLOCKED ngoài** | Không kiểm tra đăng nhập thật |
| 2 | Chưa có phê duyệt Owner bằng văn bản/mã | **BLOCKED ngoài** | Các nút thật trả 403 |
| 3 | Chưa có URL webhook công khai | **BLOCKED ngoài** | BEST không gọi được callback |
| 4 | Chưa có Bearer webhook thật | **BLOCKED ngoài** | Callback thật sẽ 401 |
| 5 | Chưa đo phản hồi thật 8 API | **CHƯA ĐO** | Schema đọc tài liệu, chưa đối chiếu runtime |
| 6 | HTTP status/timeout/retry của hãng | **CHƯA XÁC MINH** | Nội bộ đang 4xx/5xx; không đoán |
| 7 | `thu_g19_route.py` lệch ghim do thêm 7 route BEST | **TEST HARNESS** | Không phải lỗi sản phẩm; cần cập nhật bộ đếm route |
| 8 | Hồi quy toàn bộ còn bộ đỏ có sẵn | **CÓ SẴN** | Xem `docs/QA_NGUYENNHAN.md` §3; không do BEST |
| 9 | Production tạo/sửa/hủy đơn | **KHOÁ CÓ CHỦ Ý** | Chỉ sandbox sau phê duyệt |

---

## 7. CÁCH OWNER NHẬP TÀI KHOẢN AN TOÀN

1. Chạy `./trien_khai/best_nghiem_thu.sh 'OWNER-UAT-...'`.
2. Mở `https://localhost:8897/admin/`, đăng nhập bằng tài khoản demo đọc từ
   `$VIP_HUB_DATA/TAI-KHOAN-DEMO.md` (không dán mật khẩu vào chat).
3. Mở `https://localhost:8897/pages/best-uat.html`.
4. Mục **2. Tài khoản BEST**:
   - Chọn `sandbox`.
   - Nhập **Username/Password** do BEST cấp.
   - Tick “Tôi xác nhận đã có phê duyệt của Owner…”.
   - Bấm **Lưu tài khoản**.
5. Mục **4. Webhook Bearer**: chọn tài khoản, nhập Bearer token do BEST cấu hình, bấm lưu.
6. Mục **3. Kiểm tra kết nối**: chọn tài khoản, chọn “Tôi đã phê duyệt kiểm tra thật”, bấm kiểm
   tra. Xem kết quả/SQL; **không có token nào hiện ra**.
7. Không nhập credential production trong lượt UAT này; production bị khoá ghi.

**Không** gửi credential qua chat, email, log, ảnh chụp, hay `localStorage`. Backend mã hoá
AES-256-GCM; trang xoá ô mật khẩu/Bearer ngay sau khi gửi.

---

## 8. CÁC BƯỚC THỬ MỘT ĐƠN THẬT (SANDBOX) SAU PHÊ DUYỆT

Điều kiện: Owner đã cấp credential sandbox + chạy script với mã phê duyệt; `VIP_BEST_OWNER_APPROVED=1`
và `VIP_BEST_OWNER_APPROVAL_ID` có giá trị (script làm việc này). **Không dùng production.**

1. Mở bàn UAT, chọn tài khoản sandbox.
2. Mục **5. Báo cước**: nhập tỉnh/quận/phường gửi–nhận, cân gram, kích thước mm, COD/khai giá;
   bấm **Báo cước BEST**. Kiểm tra `TotalFee`, `FreightFee`, `CODFee`, `InsuranceFee`, VAT.
3. Mục **6. Tạo đơn sandbox**:
   - Nhập mã đơn đối tác duy nhất (ví dụ `UAT-2026-10-19-01`).
   - Nhập người gửi/nhận, địa chỉ 2 cấp, cân/kích thước, COD/khai giá.
   - Nhập câu xác nhận **`TOI_DONG_Y_GOI_BEST_TEST`**.
   - Bấm **Gửi tạo đơn sandbox**.
   - Kỳ vọng: `Result=1`, `Code` (waybill), `RouteCode`; nếu lỗi, hiển thị lý do hãng.
4. Mục **7. Tra cứu**: nhập waybill, bấm tra cứu; kiểm tra status/23 mã.
5. Bấm **Lấy URL PDF**; nếu URL là HTTP, không tự mở — cần backend tải qua HTTPS/allowlist.
6. Mục **8. Lịch sử**: kiểm tra event/audit.
7. Webhook: BEST gọi URL công khai; kiểm tra event + đơn + ACK. Nếu chưa có URL công khai,
   webhook thật vẫn **BLOCKED**.

**Không tạo đơn production. Không tự phát sinh giao dịch thật.**

---

## 9. COMMIT VÀ TỆP THAY ĐỔI

| Commit | Nội dung |
|---|---|
| `fb1357c` | Hợp đồng chính thức, Bearer webhook, backend UAT, bàn nghiệm thu |
| `fc06eb7` | Adapter DOCX, webhook URL công khai, trạng thái Bearer, UI UAT |
| `a4b666e` | 14 ca UAT HTTP + script nghiệm thu HTTPS |
| `74c961e` | Mở rộng bộ thử hợp đồng lên 35 ca |
| `80e2c60` | Ca thử `customer Cancel` |
| (commit tài liệu này) | Hướng dẫn Owner UAT + DOCX audit |

**Tệp chính:** `app/best_hop_dong.py` · `app/adapter_best.py` · `app/webhook_best.py` ·
`app/server.py` · `app/http_best.py` · `app/khoi_tao.py` · `app/thu/thu_best_*.py` ·
`admin/best_uat.js` · `pages/best-uat.html` · `trien_khai/best_nghiem_thu.sh` · các tài liệu BEST.

---

## 10. BẰNG CHỨNG PASS/FAIL/BLOCKED

| Hạng mục | Kết quả | Số đo |
|---|---|---|
| Hợp đồng chính thức | **PASS (DOC_VERIFIED)** | 8 endpoint · 34 trường · 23 mã · TLS |
| Builder/parser hợp đồng | **PASS** | `thu_best_hop_dong.py` 35/35 |
| Webhook BEST | **PASS (MOCK/LOCAL)** | `thu_best_webhook.py` 52/52 |
| E2E HTTP BEST | **PASS (LOCAL)** | `thu_best_e2e_http.py` 59/59 |
| Backend UAT HTTP | **PASS (LOCAL)** | `thu_best_uat.py` 14/14 |
| Adapter BEST | **PASS (MOCK)** | `thu_best_adapter.py` 118/118 |
| Auth/credential BEST | **PASS (MOCK)** | `thu_best_auth.py` 47/47 |
| Hub webhook | **PASS** | `thu_webhook.py` 68/68 |
| J&T webhook | **PASS** | `thu_webhook_jt.py` 99/99 |
| G22 regression | **PASS** | 35/35 |
| B5 10 cổng | **5 PASS · 2 BLOCKED · 2 NOT TESTED · 1 PENDING** | exit 0 |
| Đăng nhập/8 API thật | **BLOCKED** | chưa credential/phê duyệt |
| Webhook thật | **BLOCKED** | chưa URL công khai/Bearer/Best cấu hình |
| REAL PASS | **BLOCKED** | không tuyên bố |
| OWNER APPROVED | **PENDING** | chỉ Owner |

**Không tuyên bố REAL PASS hoặc OWNER APPROVED.** Các mục `BLOCKED` ngoài cần Owner/BEST giải
quyết; không phải lỗi mã cục bộ.
