# SAAS_ACCEPTANCE — VIP Express Hub (nghiệm thu Multi-Tenant, local, 14/10/2026)

PROJECT: VIP EXPRESS HUB

CURRENT PROJECT PATH: `~/Projects/vip-express-hub` (MacBook, local-first; git local, không remote)
CURRENT ARCHITECTURE: backend `app/` (Python 3 stdlib + SQLite, 127.0.0.1:8897) phục vụ cả API `/api/v2/*` lẫn giao diện tĩnh `admin/`, `pages/`, `assets/`. Gateway G01 cũ giữ nguyên ở `gateway/`. Chi tiết: `docs/ARCHITECTURE.md`.
CURRENT DATABASE: SQLite `app/du-lieu/hub.db` (WAL, kết nối theo-thread). CSDL G01 `gateway/du-lieu/gateway.db` KHÔNG bị đụng.
CURRENT FRONTEND: SPA quản trị `admin/` (tiếng Việt, responsive, tái dùng design system `assets/`); 10 trang demo G00 còn nguyên.
CURRENT BACKEND: auth/phiên/RBAC, order service, carrier adapter interface + 2 adapter, webhook gateway tenant-aware, import engine, AI gateway (mock), billing.

COMPLETED (local):
- G00 khảo sát + 4 tài liệu (`PROJECT_AUDIT`, `ARCHITECTURE`, `IMPLEMENTATION_PLAN`, `ACCEPTANCE_CHECKLIST`); git baseline + backup DB.
- G01 Multi-tenant isolation: tenant lấy từ phiên, mọi truy vấn kèm `tenant_id`, resource ownership; test chéo tenant đạt.
- G02 Auth/RBAC: 6 vai trò, pbkdf2-200k, khóa TK sau 5 lần sai, phiên thu hồi được, đổi mật khẩu thu hồi phiên khác, audit.
- G03 Carrier Adapter Interface + registry + capabilities.
- G04 Adapter J&T dựng theo tài liệu công khai (digest = base64(md5(bizContent+privateKey)), endpoint test/prod, bizContent) — transport MOCK, LIVE khóa.
- G05 Adapter VTP (MOCK) qua cùng interface; nhiều tenant mỗi tenant tài khoản riêng.
- G06 Webhook gateway tenant-aware: verify chữ ký theo account → lưu thô → queue → normalize → resolve đúng tenant+đơn → update + audit; idempotency, out-of-order, retry/DLQ, replay RBAC.
- G07 Order service: vòng đời nháp→duyệt→gửi→đã gửi/hủy, idempotency UNIQUE, lịch sử, xuất CSV; chỉ `da_gui` khi hãng xác nhận; timeout giữ `dang_gui` + cờ kiểm lại.
- G08 Import engine: CSV + XLSX (parser stdlib) + PDF text (best-effort, báo giới hạn); batch, preview, sửa dòng, duyệt, trạng thái từng dòng, idempotency import.
- G09 AI gateway: interface + mock, policy chặn vượt auth/tenant/approval, tính usage.
- G10 Billing: gói/hạn mức/usage đo backend, chặn vượt (đơn, AI, nhân viên, kết nối hãng).
- G11 Admin UI: đăng nhập + 10 màn tenant + 3 màn platform, responsive, không hiện secret.
- G12 Testing & security: `app/thu/thu_saas.py` **19/19 PASS**; regression G01 `gateway/thu/thu_gateway.py` **9/9 PASS**.

PARTIAL:
- PDF import chỉ đọc PDF có lớp văn bản (scan/OCR chưa) — đã báo lỗi rõ, không đoán.
- Mã hóa credentials là encrypt-then-MAC trên stdlib (đủ local) — production cần AES-GCM/KMS (ghi rõ trong ARCHITECTURE).

BLOCKED (cần Owner):
- Credentials J&T thật + cho phép gọi API thật → mới test LIVE VERIFIED (hiện `CHO_PHEP_LIVE=False`, test `test_17` chứng minh LIVE bị khóa).
- Cho đọc repo `vip-viettelpost` để tái dùng tích hợp VTP thật.
- Mọi deploy (GitHub/VPS/production), đổi domain, tạo đơn vận chuyển thật.

NOT STARTED: thanh toán thật (G10 cố ý dừng ở gói/hạn mức theo brief).

MULTI-TENANT STATUS: ĐẠT (local) — test 01,02,03,08 chứng minh không xem/sửa/dùng-credentials/cập-nhật chéo tenant.
J&T INTEGRATION: DOCUMENTED + adapter MOCK theo docs; LIVE BLOCKED.
VIETTEL POST INTEGRATION: adapter MOCK; tái dùng mã thật BLOCKED.
WEBHOOK GATEWAY: ĐẠT (local) — verify/persist/queue/normalize/resolve/idempotency/out-of-order/retry/DLQ/replay-RBAC đều có test.
ORDER MANAGEMENT: ĐẠT (local) — idempotency + không nhận thành công khi hãng chưa xác nhận, có test.
IMPORT ENGINE: ĐẠT (CSV/XLSX; PDF text best-effort) — test 11.
AI BRAIN INTEGRATION: interface + mock + policy; chưa nối AI thật (đúng brief).

TEST RESULTS: 19/19 (SaaS) + 9/9 (gateway regression). Lệnh: `python3 app/thu/thu_saas.py`, `python3 gateway/thu/thu_gateway.py`.
SECURITY RESULTS: 15 ca bắt buộc G12 đều có test tương ứng và PASS (xem ACCEPTANCE_CHECKLIST.md). Bổ sung: khóa TK, thu hồi phiên, không rò secret trong API/log/CSDL, CSRF header guard, LIVE khóa.
MIGRATION STATUS: schema mới nằm ở `hub.db` riêng; `gateway.db` không đụng (test 16); git baseline `fd79d74` lùi được.
REGRESSION RESULTS: gateway 9/9; 10 trang demo G00 vẫn mở được (phục vụ qua cùng server).

LOCAL ACCEPTANCE: ĐẠT trong phạm vi local đã đo. Bằng chứng live: đơn T1-000001 tạo→duyệt→gửi(mock VTP5845644359)→webhook ký→giao_thanh_cong, sự kiện muộn bị từ chối đúng.
PRODUCTION READINESS: CHƯA — còn BLOCKED ở trên; credentials demo trong `cau_hinh.py`, mã hóa mức local, chưa TLS/rate-limit cổng webhook.

NEXT ACTIONS (khi Owner duyệt):
- Cấp credentials J&T sandbox → bật `CHO_PHEP_LIVE` có kiểm soát, liên调 test theo quy trình open.jtexpress.vn.
- Cho đọc `vip-viettelpost` để chuyển logic VTP thật vào adapter.
- Thêm rate-limit cổng webhook, TLS, chuyển secret sang biến môi trường/kho bí mật, nâng mã hóa lên AES-GCM.

OWNER DECISIONS REQUIRED:
1. Có cấp credentials J&T thật và cho phép liên调 sandbox không?
2. Có cho đọc repo `vip-viettelpost` để tái dùng tích hợp VTP không?
3. Khi nào chuyển sang bàn chuyện deploy (vẫn đang local theo đúng brief).
