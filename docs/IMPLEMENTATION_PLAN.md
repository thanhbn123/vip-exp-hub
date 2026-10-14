# IMPLEMENTATION_PLAN — thứ tự triển khai theo phụ thuộc kỹ thuật

Mốc rollback: git local `fd79d74` + bản sao `gateway.db`. Mỗi bước xong đều commit local.

| Bước | Gate | Nội dung | Phụ thuộc | Trạng thái vào 14/10 |
|---|---|---|---|---|
| 1 | G00 | Khảo sát, audit, git local, backup | — | DONE (tài liệu này + PROJECT_AUDIT) |
| 2 | G01+G02 | `app/`: schema multi-tenant + auth (phiên, pbkdf2, khóa TK) + RBAC 6 vai trò + audit + seed | 1 | làm ngay |
| 3 | G03 | Carrier Adapter Interface + registry + capabilities | 2 | làm ngay |
| 4 | G04/G05 | Adapter J&T (theo docs công khai, transport MOCK, live khóa chờ duyệt) + Adapter VTP (MOCK; khảo sát repo `vip-viettelpost` để riêng — ngoài thư mục dự án, cần anh gật mới đọc) | 3 | J&T docs DONE; adapter làm ngay |
| 5 | G06 | Webhook Gateway tenant-aware trong `app/` (kế thừa thiết kế G01: thô → queue → normalize → resolve tenant+đơn → rank guard → audit; retry/DLQ) | 2,3 | làm ngay |
| 6 | G07 | Order Service: tạo/sửa nháp/duyệt/gửi hãng/hủy + idempotency UNIQUE + lịch sử + xuất CSV | 2,3 | làm ngay |
| 7 | G08 | Import batch server-side: CSV + XLSX (parser stdlib) + PDF text (best-effort, ghi giới hạn); preview → sửa → approve → tạo đơn | 6 | làm ngay |
| 8 | G09 | AI Integration Gateway (interface + mock, policy chặn vượt quyền) | 2 | làm ngay |
| 9 | G10 | Billing: gói, hạn mức, usage backend, chặn vượt hạn mức | 2 | làm ngay |
| 10 | G11 | Admin UI (`admin/`): đăng nhập + dashboard + tenants + users + khách + đơn + import + hãng + webhook monitor + gói + nhật ký + cài đặt; tái dùng design system | 2–9 | làm ngay |
| 11 | G12 | Bộ thử bảo mật: 15 ca bắt buộc của brief + regression gateway cũ | 2–10 | làm ngay |
| 12 | G13 | Nghiệm thu local + FINAL REPORT | 11 | cuối |

**BLOCKED (cần Owner):** credentials J&T thật + cho phép gọi API thật (G04 LIVE); đọc repo `vip-viettelpost` cho G05 phần thật; mọi deploy.


## Đợt 2 — brief Multi-Tenant Core + Auth/RBAC (14/10/2026)

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 13 | G01.1 schema v2: `tenant_memberships`, `roles`/`permissions`/`role_permissions`, `carrier_providers`, `tenants.code` | DONE |
| 14 | G01.2 Tenant Context Middleware (authenticate → membership → active tenant → authorize) | DONE |
| 15 | G01.3 Tenant Management API (create/get/update/list/activate/suspend) | DONE |
| 16 | G01.5 Migration có phiên bản + backup + verify + rollback (`app/migrate.py`) | DONE |
| 17 | G02.1 reset mật khẩu (provider giả lập), chống brute-force, không lộ tài khoản | DONE |
| 18 | G02.2 RBAC trong CSDL + chống leo thang đặc quyền | DONE |
| 19 | G02.3 Membership management + switch tenant | DONE |
| 20 | G02.4 Audit đủ trường (actor/resource/result), ghi cả lượt bị từ chối | DONE |
| 21 | G03-PREP carrier account isolation + rotate/revoke + secret storage abstraction | DONE |
| 22 | Frontend: đăng nhập, quên mật khẩu, tenant switcher, thành viên, vai trò & quyền, rotate khóa | DONE |
| 23 | TEST-001..015 + 6 ca bổ sung; regression gateway | DONE (49/49) |
| 24 | Tài liệu G01/G02/SECURITY/MIGRATION/ACCEPTANCE | DONE |

**Còn BLOCKED (cần Owner):** credentials J&T thật; đọc repo `vip-viettelpost`; mọi quyết định deploy.
**G03 kế tiếp:** Carrier Integration Engine — đã có interface + 2 mock adapter + capability;
phần còn lại (adapter thật) phụ thuộc Owner.


## Đợt 3 — G03 Carrier Integration Engine, phần thuần local (14/10/2026)

| Bước | Nội dung | Trạng thái |
|---|---|---|
| 25 | Bảng ánh xạ trạng thái từng hãng — mã J&T THẬT từ tài liệu công khai | DONE |
| 26 | Sửa capability J&T `webhook` False→True (đọc sót trang con 轨迹回传) | DONE |
| 27 | Khung retry/timeout; createOrder chỉ thử lại khi hãng có khóa chống trùng | DONE |
| 28 | Tracking polling fallback (gom lô 30/lượt theo tài liệu, qua rank guard, không tự chạy) | DONE |
| 29 | Bộ thử hợp đồng adapter chạy với MỌI hãng + ánh xạ + retry + polling | DONE (23 test) |
| 30 | Tài liệu `G03_CARRIER_ENGINE.md` | DONE |

**Tổng test sau đợt 3: 72** (23 G03 + 21 G01/G02 + 19 nghiệp vụ + 9 gateway).


## Đợt 4 — quyết định của Owner 14/10/2026

| Việc | Quyết định | Kết quả |
|---|---|---|
| Credentials J&T thật | Chưa cần, để khi kiểm thử LIVE | giữ BLOCKED, `CHO_PHEP_LIVE=False` |
| Đọc repo `vip-viettelpost` | **Cho phép ngay** | ĐÃ ĐỌC — repo là scaffold rỗng, **không có gì tái dùng được**; ghi lại trong `adapter_vtp.py` |
| Deploy VPS | Chưa, sau nghiệm thu local | không đụng |
| Mã hóa AES-256-GCM | **Làm ngay** | DONE — `docs/MA_HOA.md`, migration v3, 7 test |

**Tổng test sau đợt 4: 79** (30 G03 + 21 G01/G02 + 19 nghiệp vụ + 9 gateway).
