# BEST EXPRESS — NGHIỆM THU TÀI KHOẢN THẬT (BEST-09 · BEST-10)

**Vai:** B5 · QA/E2E/Security · **Ngày lập:** 19/10/2026 · **Nền:** `cb23312dc702`
**Chế độ hiện tại:** LOCAL · MOCK — **KHÔNG PHẢI REAL PASS**
**Trạng thái:** `BEST-09 = BLOCKED` · `BEST-10 = PENDING`

> Tài liệu này là **quy trình và danh mục bằng chứng** cho lượt nghiệm thu bằng tài khoản BEST
> THẬT. Bản thân nó **không phải** bằng chứng đã nghiệm thu, và **không được** dùng để ghi PASS.
> Chỉ chủ doanh nghiệp (Owner) được xác nhận BEST-10.

---

## 0. LUẬT CỨNG — áp dụng cho mọi bước trong tài liệu này

1. **Không credentials thật trong repo, tài liệu, log, audit, ảnh chụp, chat.** Credentials chỉ
   vào kho mã hoá của hệ (AES-256-GCM, định dạng `v3$…`) qua kênh do Owner duyệt.
2. **Không gọi API BEST khi chưa có phê duyệt bằng văn bản của Owner.** Kể cả test host.
3. **Không tạo đơn thật trên production.** Sandbox/test account trước; production chỉ sau khi
   BEST-09 và BEST-10 đã PASS và có phê duyệt riêng.
4. **Chỉ HTTPS.** Không hạ TLS, không `-k`, không tắt xác minh chứng chỉ, không HTTP cho dữ
   liệu thật. Hostname phải khớp SAN của chứng chỉ.
5. **Tenant là bắt buộc.** Mọi truy vấn theo `tenant_id`; không xác định được tenant ⇒ DENY.
6. **Không đoán endpoint/request schema.** Tài liệu BEST là Google Docs; nếu chưa đọc được thì
   chỉ dùng đặc tả đã xác nhận trong đề bài, mọi mục khác ghi `CHƯA KIỂM CHỨNG`.
7. **MOCK PASS ≠ REAL PASS.** Một bộ thử xanh trên mock không chứng minh được kết nối tài
   khoản thật, chứng chỉ, hay hợp đồng dữ liệu thật.

---

## 1. ĐIỀU KIỆN VÀO CỔNG (entry criteria) — thiếu một dòng là BLOCKED

| # | Điều kiện | Bằng chứng phải có | Ai cấp |
|---|---|---|---|
| E1 | Tài liệu API BEST đã đọc được, có phiên bản/ngày | Liên kết Google Docs + ngày đọc + người đọc + ảnh/trích lục đã che bí mật | Owner / đơn vị tích hợp |
| E2 | Danh sách endpoint đã đối chiếu: **8 endpoint**, method, content-type, timeout | Bảng đối chiếu 8 dòng, mỗi dòng có nguồn tài liệu | Owner |
| E3 | Hợp đồng trường: **21 trường**, kiểu, bắt buộc/không, độ dài | Bảng 21 dòng + mẫu request đã che | Owner |
| E4 | `ServiceId = 12491` và `District = " "` (đúng một dấu cách) được xác nhận bằng tài liệu | Trích dẫn nguyên văn + ngày | Owner |
| E5 | Giới hạn **10 / 50** (theo lô / theo trang) đã xác nhận | Trích dẫn + cách đo | Owner |
| E6 | Credentials sandbox/test cấp qua kênh an toàn | Biên nhận bàn giao (không chứa giá trị), người nhận, ngày | Owner |
| E7 | Endpoint HTTPS + chứng chỉ + hostname đã xác minh | Mục 3 của tài liệu này, có bản ghi TLS | Kỹ thuật + Owner |
| E8 | Phê duyệt bằng văn bản cho phép gọi sandbox/test | Quyết định có chữ ký, phạm vi, thời hạn | **Owner** |
| E9 | Tài khoản test + địa chỉ nhận callback công khai (nếu webhook) | Mã tài khoản (không kèm secret), URL callback | Owner |
| E10 | Kế hoạch rollback và người trực | Tên, số liên lạc nội bộ, thời điểm | Owner |

**Hiện trạng 19/10/2026:** E1–E10 **đều chưa có**. Vì vậy BEST-09 BLOCKED, BEST-10 PENDING.

---

## 2. MA TRẬN 10 CỔNG — điều kiện chuyển trạng thái

| Cổng | Hiện tại | Để chuyển sang PASS cần |
|---|---|---|
| BEST-01 Repository Baseline | **PASS** | Giữ cây sạch; mọi thay đổi đi qua AG-00; vân tay khớp |
| BEST-02 API Contract | **BLOCKED** | Có mã BEST + đối chiếu 8 endpoint / 21 trường / 12491 / `" "` / 10/50 với tài liệu E1–E5 |
| BEST-03 Authentication | **BLOCKED** | 2 secret BEST tách rời (credentials ≠ webhook secret), AES-256-GCM, token không lộ — đo trên mã BEST thật |
| BEST-04 Create/Update/Cancel | **BLOCKED** | Idempotency, timeout ⇒ UNKNOWN, không retry mù — đo trên adapter BEST |
| BEST-05 Webhook + Tracking | **BLOCKED** | 11 bước, 24 mã, 605→606, sự kiện đến muộn, tenant — đo trên webhook BEST |
| BEST-06 Fee + PDF | **BLOCKED** | Estimated/Actual/Contract tách rời; PDF chỉ từ hostname cho phép (SSRF) |
| BEST-07 Multi-tenant Security | **PASS (hiện trạng)** | Đã đạt 6/6 điều cấm trên cây chưa có mã BEST; **phải chạy lại** sau hợp nhất |
| BEST-08 Frontend E2E | **PASS (DEMO)** | `sh thu_giao_dien/chay.sh` thật: 65 đạt · 0 bỏ qua · mã thoát 0 (19/10/2026) — nhưng BEST chỉ là dữ liệu demo |
| BEST-09 Real Account Connectivity | **BLOCKED** | E1–E10 + kết nối thật đo được, không tạo đơn production |
| BEST-10 Owner Acceptance | **PENDING** | Chữ ký của chủ doanh nghiệp ở mục 7 |

---

## 3. QUY TRÌNH XÁC MINH TLS / HOSTNAME (E7) — làm thật, ghi bằng chứng

Chỉ chạy sau khi có E8. **Không** dùng `curl -k`, **không** đặt `verify=False`, **không** dùng
`http://`. Mỗi bước ghi: lệnh, mã thoát, đầu ra đã che bí mật, ngày, người chạy.

1. **Chuỗi chứng chỉ:** kết nối TLS tới đúng host BEST, lưu chuỗi chứng chỉ (không kèm khóa).
2. **Hostname:** kiểm tra SAN/CN khớp hostname sẽ dùng. Ghi rõ nếu là wildcard.
3. **Hiệu lực:** `notBefore` / `notAfter`; cảnh báo nếu còn < 30 ngày.
4. **Giao thức:** TLS ≥ 1.2; ghi phiên bản đã thương lượng; từ chối TLS 1.0/1.1.
5. **Chuỗi tin cậy:** xác minh bằng CA tin cậy của hệ điều hành; không bỏ qua lỗi.
6. **Chuyển hướng:** nếu endpoint trả redirect, chỉ cho phép redirect **cùng hostname và HTTPS**;
   redirect sang host khác ⇒ DỪNG, báo Owner.
7. **PDF/nhãn:** nếu BEST trả URL PDF, chỉ tải khi hostname nằm trong danh sách trắng của hệ;
   từ chối `http://`, IP thô, `@` trong URL, cổng lạ, host lạ. Đây là chống SSRF, không phải
   tính năng phụ.

**Bằng chứng tối thiểu phải lưu:** hostname · ngày giờ · mã thoát lệnh · phiên bản TLS ·
nhà cấp chứng chỉ · hạn · kết quả khớp SAN · người chạy. **Không lưu** private key, token,
cookie, hay toàn bộ request có Authorization.

---

## 4. QUY TRÌNH ĐO 8 ENDPOINT / 21 TRƯỜNG (E2–E5) — sau khi có phê duyệt

Với **từng** endpoint trong 8 endpoint đã xác nhận:

| Việc | Cách đo | Đạt khi |
|---|---|---|
| Tồn tại | Gọi sandbox bằng tài khoản test | Trả mã HTTP có nghĩa, không 404/405 |
| Schema | Đối chiếu request với 21 trường đã xác nhận | Đúng tên/kiểu/bắt buộc; không thêm trường đoán |
| `ServiceId` | Kiểm trong request thật | Luôn `12491`, không hard-code chỗ khác |
| `District` | Kiểm trong request thật | Đúng **một dấu cách** `" "`, không rỗng, không `null` |
| Giới hạn 10/50 | Gửi lô 10 và trang 50; thử 11/51 | 10/50 được nhận; vượt bị từ chối **có kiểm soát** |
| Lỗi | Gửi một request sai chủ đích | Lỗi được đọc/ánh xạ, không nuốt, không retry mù |
| Timeout | Ngắt kết nối có kiểm soát | Kết quả là **UNKNOWN**, không phải thành công |
| Ngoài phạm vi | Không gọi API | Không có lệnh nào gọi BEST ngoài phạm vi được duyệt |

**Không được** ghi PASS cho endpoint chỉ vì mock trả `ok=True`. Mock không chứng minh được
hợp đồng thật.

---

## 5. QUY TRÌNH WEBHOOK (BEST-05) — 11 bước / 24 mã / 605→606

Chỉ sau khi có URL callback công khai (E9) và phê duyệt (E8):

1. Đăng ký webhook ở sandbox; lưu `webhook_ma` (không lưu secret dạng rõ).
2. Xác thực chữ ký bằng so sánh hằng thời gian (`hmac.compare_digest`), không `==`.
3. Chống trùng bằng khoá bền; replay cùng sự kiện phải không đổi đơn lần hai.
4. Ánh xạ **24 mã** trạng thái; mã lạ ⇒ ghi nhận + `NEEDS_REVIEW`, **không đoán**.
5. Kiểm **605 → 606** đúng chiều; ghi mã gốc + mã chuẩn.
6. Sự kiện **đến muộn**: mốc hãng cũ hơn mốc đã áp ⇒ không đổi trạng thái, có audit.
7. Tenant: chỉ lấy từ `carrier_accounts`; `tenant_id` trong payload chỉ ghi lại, không dùng.
8. Sai chữ ký: 401/403 + audit, không xử lý nội dung.
9. Quá tải: hàng đợi/backoff có trần; không treo tiến trình.
10. DLQ/replay có phân quyền; mọi lượt replay có audit + người thực hiện.
11. Đo lại toàn bộ sau khi bật sandbox; lưu bằng chứng từng bước.

**Hiện trạng:** chưa có mã BEST ⇒ chưa có bảng mã, chưa có sơ đồ chữ ký BEST. BLOCKED.

---

## 6. DANH MỤC BẰNG CHỨNG PHẢI NỘP (evidence pack)

| Mã | Bằng chứng | Định dạng | Bắt buộc |
|---|---|---|---|
| EV-01 | Xác nhận tài liệu API + phiên bản | PDF/ảnh đã che | Có |
| EV-02 | Bảng 8 endpoint + 21 trường + 12491 + `" "` + 10/50 | Bảng có nguồn | Có |
| EV-03 | Biên nhận bàn giao credentials (không giá trị) | Biên bản | Có |
| EV-04 | Bản ghi TLS/hostname (mục 3) | Log đã che | Có |
| EV-05 | Kết quả mock local (bộ 10 cổng) | `thu_best_qa.py --json` | Có |
| EV-06 | Kết quả sandbox 8 endpoint | Log đã che + mã thoát | Có |
| EV-07 | Kết quả webhook 11 bước/24 mã/605→606 | Log + ảnh | Có |
| EV-08 | Kết quả phí 3 loại + PDF hostname | Log | Có |
| EV-09 | 6/6 điều cấm chạy lại trên mã BEST | Log | Có |
| EV-10 | Chữ ký Owner (mục 7) | Bản ký | Có |

**Cách lưu:** ngoài repo, trong kho bằng chứng nội bộ; mỗi tệp có sha256 + ngày. Không đưa
credentials/token vào evidence pack.

---

## 7. CHỮ KÝ CHỦ DOANH NGHIỆP — BEST-10 (đang PENDING)

> Chỉ chủ doanh nghiệp được điền mục này. Agent không được tự điền, không được suy ra.

| Trường | Giá trị |
|---|---|
| Người xác nhận | ........................................ |
| Vai trò | Chủ doanh nghiệp / người được uỷ quyền bằng văn bản |
| Ngày | ........................................ |
| Phạm vi xác nhận | BEST-09 kết nối thật + BEST-02…08 trên môi trường ................ |
| Quyết định | ☐ CHẤP NHẬN  ☐ TỪ CHỐI  ☐ CHẤP NHẬN CÓ ĐIỀU KIỆN |
| Điều kiện / lý do | ........................................ |
| Mã băm evidence pack | ........................................ |
| Chữ ký | ........................................ |

**Trạng thái:** `PENDING` — chưa có chữ ký. Bất kỳ báo cáo nào ghi BEST-10 PASS mà thiếu mục
này là **báo cáo sai**.

---

## 8. VÌ SAO HIỆN TẠI BLOCKED — danh sách THIẾU, không phải lời phàn nàn

Tại `cb23312dc702` (đo 19/10/2026, xem `docs/BEST_EXPRESS_QA.md`):

- **Không có mã tích hợp BEST:** không `app/adapter_best.py`; 0 hit `12491`; 0 đăng ký
  `ma_hang="best"`; 0 host BEST trong mã. (Lệnh + mã thoát ghi trong QA doc.)
- **Không có credentials thật:** 0 biến môi trường BEST; 0 tài khoản BEST trong CSDL tạm.
- **Không có endpoint HTTPS nào để xác minh:** do đó không có bản ghi TLS/hostname.
- **Không có phê duyệt của Owner** cho việc gọi API BEST (kể cả test host).
- **Tài liệu Google Docs chưa đọc được** trong môi trường này: 9/9 mục đặc tả còn
  `CHƯA KIỂM CHỨNG`.

⇒ **BEST-09 = BLOCKED. BEST-10 = PENDING.** Không có đường nào để bộ đo local ghi PASS cho
hai cổng này, và tài liệu này không được dùng để thay thế bằng chứng thật.

---

## 9. SAU KHI OWNER DUYỆT — thứ tự bắt buộc

1. Đọc tài liệu (E1) → cập nhật bảng 8/21/12491/`" "`/10/50 nếu có sai khác.
2. Nạp credentials qua kho mã hoá; kiểm tra **không** có bản rõ trong log/audit/response.
3. Xác minh TLS/hostname (mục 3) và lưu EV-04.
4. Chạy mock local (EV-05) — phải xanh trước khi chạm sandbox.
5. Sandbox: 8 endpoint (EV-06), webhook (EV-07), phí/PDF (EV-08). **Không** tạo đơn production.
6. Chạy lại 6 điều cấm trên mã BEST (EV-09).
7. Owner ký (EV-10). Chỉ khi đó BEST-09/BEST-10 mới được ghi PASS — và phải ghi kèm ngày,
   phạm vi, mã băm bằng chứng.

---

*Tài liệu này do B5 lập trong phạm vi LOCAL. Không có kết nối mạng, không có credentials, không
có thay đổi mã sản phẩm. Mọi số đo thật nằm trong `docs/BEST_EXPRESS_QA.md`.*
