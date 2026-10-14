# G01_G02_ACCEPTANCE — VIP Express Hub (14/10/2026, local)

PROJECT: VIP EXPRESS HUB
WORKSPACE: `~/Projects/vip-express-hub`
CURRENT BRANCH: `master` (git **local**, không remote — đúng ràng buộc không push GitHub)
BASELINE SHA: `fd79d74`
FINAL SHA: `934f29e`

## Trạng thái từng hạng mục

| Hạng mục | Kết quả |
|---|---|
| G01 MULTI-TENANT | **PASS** (local) |
| G02 AUTHENTICATION | **PASS** (local) |
| RBAC | **PASS** (quyền trong CSDL, TEST-019 chứng minh không hard-code) |
| TENANT ISOLATION | **PASS** (TEST-001,002,003,004,010,011) |
| CARRIER ACCOUNT ISOLATION | **PASS** (TEST-004, test_020 rotate/revoke) |
| FRONTEND INTEGRATION | **PASS** (đăng nhập, quên mật khẩu, tenant switcher, thành viên, vai trò & quyền, rotate khóa) |
| MIGRATION | **PASS** (chạy thật trên CSDL đang dùng, 0 dòng mất; TEST-014 kiểm cả rollback) |
| GATEWAY REGRESSION | **PASS** 9/9 — và đã **sửa một segfault thật** phát hiện trong đợt này |
| LOCAL ACCEPTANCE | **PASS** |
| PRODUCTION READINESS | **CHƯA** — còn BLOCKED, xem dưới |

## SECURITY TESTS

PASSED: **49** · FAILED: **0** · SKIPPED: **0**

- `app/thu/thu_g01_g02.py` — 21 test (TEST-001..015 + 6 ca bổ sung)
- `app/thu/thu_saas.py` — 19 test nghiệp vụ (webhook, đơn, import, billing, secret, CSRF)
- `gateway/thu/thu_gateway.py` — 9 test regression

Chi tiết từng ca + giới hạn phạm vi: `SECURITY_TEST_REPORT.md`.

## QUALITY GATES

| Gate | Kết quả | Bằng chứng |
|---|---|---|
| A — Architecture | ĐẠT | `G01_MULTI_TENANT.md`, schema v2 không xung đột hệ cũ (CSDL riêng, gateway.db không đụng) |
| B — Functional | ĐẠT | API tenant/membership/switch chạy thật; đã thao tác qua UI |
| C — Security | ĐẠT | 49/49, mọi ca cross-tenant PASS |
| D — Regression | ĐẠT | gateway 9/9; nghiệp vụ 19/19; đơn cũ T1-000001 còn nguyên sau migration |
| E — Local acceptance | ĐẠT | chuỗi 7 bước dưới đây chạy được thật |
| F — Documentation | ĐẠT | 5 tài liệu mới + 3 tài liệu cập nhật, phản ánh đúng mã nguồn |

### Gate E — chuỗi nghiệm thu đã chạy thật

1. Khởi động backend: `python3 app/server.py` → http://127.0.0.1:8897/admin/
2. Đăng nhập: OK (cookie HttpOnly)
3. Tạo tenant: OK (PLATFORM_OWNER tạo "Tenant A"/"Tenant B" trong bộ thử)
4. Tạo user: OK (qua mời thành viên — user mới hoặc user đã có)
5. Gán vai trò: OK (TENANT_OWNER cấp ADMIN/STAFF/VIEWER; vượt cấp bị 403)
6. Chuyển tenant: OK — đo trên UI thật: Shop Demo A (TENANT_ADMIN, thấy T1-000001) → Shop Demo B
   (TENANT_VIEWER, thấy 0 đơn)
7. Bị từ chối khi vượt quyền: OK — VIEWER tạo đơn → 403; switch sang tenant không thuộc → 403

## FILES CHANGED (so với `3ab3ee8`)

 18 files changed, 2169 insertions(+), 460 deletions(-)

Mã nguồn chính thêm/sửa: `app/csdl.py` (schema v2), `app/quyen.py` (mới), `app/migrate.py` (mới),
`app/bao_mat.py` (tenant context + reset), `app/server.py` (middleware + API mới), `app/khoi_tao.py`,
`app/billing.py`, `app/cau_hinh.py`, `admin/admin.js`, `gateway/csdl.py` (sửa segfault),
`app/thu/thu_g01_g02.py` (mới), `app/thu/thu_saas.py` (cập nhật lên API v2).

## TEST COMMANDS

```bash
python3 app/migrate.py --kiem
python3 app/thu/thu_g01_g02.py
python3 app/thu/thu_saas.py
python3 gateway/thu/thu_gateway.py
```

## ROLLBACK PLAN

1. Dừng server.
2. CSDL: `python3 app/migrate.py --rollback app/du-lieu/sao-luu/<file-backup>`
   (migration tự tạo backup trước khi chạy; bản hiện tại cũng được cất lại trước khi đè).
3. Mã nguồn: `git checkout 3ab3ee8` (trước v2) hoặc `git checkout fd79d74` (trước toàn bộ SaaS).
4. Kiểm sau rollback: `python3 gateway/thu/thu_gateway.py` và mở `pages/dashboard.html`.

## UNRESOLVED RISKS

1. **Mã hóa credentials** là encrypt-then-MAC tự dựng trên stdlib — đủ local, **không đạt chuẩn
   production**; phải thay bằng AES-GCM/KMS trước khi chạm dữ liệu thật.
2. **Chưa có rate-limit** cho cổng webhook và cho đăng nhập (mới chỉ khóa theo số lần sai/tài khoản).
3. **Chưa có TLS** (local nên chưa cần, nhưng là điều kiện bắt buộc khi rời máy).
4. **Token reset trả thẳng qua API** khi `HIEN_TOKEN_RESET=1` (mặc định local) — phải đặt
   `VIP_HUB_RESET_TOKEN=0` và nối SMTP thật trước khi dùng ngoài local.
5. Chưa đo tải đồng thời lớn và chưa kiểm thử thâm nhập độc lập.
6. Tài khoản demo nằm ở `app/du-lieu/TAI-KHOAN-DEMO.md` (quyền 600, ngoài git) — chỉ dùng local.

## OWNER DECISIONS

1. **Credentials J&T thật** + cho phép liên调 sandbox → mới bật được `CHO_PHEP_LIVE` và test LIVE.
2. **Cho đọc repo `vip-viettelpost`** để tái dùng tích hợp Viettel Post thật vào adapter.
3. **Khi nào bàn deploy** (hiện tuân thủ: không push GitHub, không VPS, không production).
4. Có muốn nâng mã hóa credentials lên chuẩn production ngay ở giai đoạn này không.

## NEXT PHASE — G03 CARRIER INTEGRATION ENGINE

Đã có sẵn: `adapter.CarrierAdapter` (interface 7 hàm + capabilities + chặn LIVE),
2 adapter mock (VTP, J&T dựng theo tài liệu công khai), bảng `carrier_providers`,
carrier account theo tenant có rotate/revoke.

Phần local làm tiếp được ngay khi Owner cho lệnh: chuẩn hóa bảng mã trạng thái từng hãng
(`normalizeTrackingStatus`), tracking polling fallback cho hãng không có webhook, bộ thử hợp đồng
adapter dùng chung, và khung retry/timeout cho lớp transport. Phần cần Owner: credentials thật.
