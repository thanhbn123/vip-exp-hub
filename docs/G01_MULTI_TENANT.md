# G01 — MULTI-TENANT CORE

## 1. Mô hình

Một **user** có thể thuộc **nhiều tenant**. Vai trò không nằm trên user mà nằm trên **membership**:

```
users ──< tenant_memberships >── tenants
  │              (role)
  │
  └─ platform_role (NULL | PLATFORM_OWNER | PLATFORM_ADMIN)
```

- `users.platform_role` — vai trò cấp nền tảng (NULL với người dùng thường).
- `tenant_memberships.role` — vai trò **trong một tenant cụ thể**.
- Một nguồn chân lý duy nhất: schema v2 đã **xóa hẳn** `users.tenant_id` và `users.vai_tro` sau khi
  chuyển dữ liệu sang membership (xem `MIGRATION_REPORT.md`).

## 2. Database schema (app/du-lieu/hub.db, schema v2)

| Bảng | Vai trò | Ràng buộc chính |
|---|---|---|
| `tenants` | doanh nghiệp/shop | `code` UNIQUE, `trang_thai` hoat_dong/khoa |
| `users` | tài khoản đăng nhập | `ten_dang_nhap` UNIQUE |
| `tenant_memberships` | user ↔ tenant + role | UNIQUE(user_id, tenant_id); index theo user và theo tenant |
| `roles` / `permissions` / `role_permissions` | RBAC trong CSDL | FK; PK(role_ma, perm_ma) |
| `sessions` | phiên đăng nhập | PK = SHA-256(token); `active_tenant_id` |
| `reset_tokens` | token quên mật khẩu | dùng một lần, hết hạn 30 phút |
| `khach_hang` | khách của tenant | `tenant_id` NOT NULL + index |
| `carrier_providers` | hãng + capabilities | PK `ma` |
| `carrier_accounts` | tài khoản hãng của tenant | `tenant_id` NOT NULL, `webhook_ma` UNIQUE, credentials mã hóa |
| `don_hang` | đơn | UNIQUE(tenant_id, ma_don), UNIQUE(tenant_id, idem_key) |
| `don_lich_su` | order_events | FK don_id |
| `wh_su_kien` | raw webhook events | UNIQUE(carrier_account_id, event_id) |
| `import_batch` / `import_dong` | lô import | FK, trạng thái từng dòng |
| `usage_thang` | usage theo tháng | PK(tenant_id, thang) |
| `audit` | audit_logs | actor/tenant/action/resource_type/resource_id/ket_qua |

Ánh xạ tên theo brief: `user_sessions`→`sessions`, `customers`→`khach_hang`, `orders`→`don_hang`,
`order_events`→`don_lich_su`, `audit_logs`→`audit`. Giữ tên cũ để không phá mã đang chạy.

## 3. Tenant Context Middleware

Mọi API nghiệp vụ đi qua `bao_mat.ngu_canh(token)` trong `app/server.py::_api`:

```
AUTHENTICATE USER   → sessions (chưa thu hồi, chưa hết hạn) + users.trang_thai = hoat_dong
RESOLVE MEMBERSHIP  → tenant_memberships.trang_thai = hoat_dong AND tenants.trang_thai = hoat_dong
SELECT ACTIVE TENANT→ sessions.active_tenant_id (đổi bằng /auth/doi-tenant)
AUTHORIZE           → role_permissions (tra CSDL, theo từng endpoint)
EXECUTE             → mọi câu SQL kèm WHERE tenant_id = <từ ngữ cảnh>
```

**Luật cứng:** `tenant_id` không bao giờ đọc từ body/query. Nếu client gửi `tenant_id`, backend bỏ qua
(TEST-010 chứng minh). Resource truy cập theo id luôn kèm `AND tenant_id=?` → sai tenant trả 404
(không trả 403, để không lộ sự tồn tại của resource).

Nếu membership hoặc tenant bị vô hiệu giữa chừng, **phiên mất quyền ngay ở request kế tiếp** vì
ngữ cảnh được dựng lại mỗi lần, không cache (TEST-006, test_021).

## 4. API

| Method | Đường dẫn | Quyền | Việc |
|---|---|---|---|
| POST | `/api/v2/platform/tenants` | `platform.tenant.tao` | Tạo tenant + owner (user đã có thì chỉ thêm membership) |
| GET | `/api/v2/platform/tenants` | `platform.tenant.xem` | Liệt kê mọi tenant |
| GET | `/api/v2/platform/tenants/{id}` | `platform.tenant.xem` | Chi tiết + thành viên |
| PUT | `/api/v2/platform/tenants/{id}` | `platform.tenant.sua` | Đổi tên |
| POST | `/api/v2/platform/tenants/{id}/khoa` \| `/mo` | `platform.tenant.khoa` | Suspend / Activate |
| POST | `/api/v2/platform/tenants/{id}/goi` | `platform.goi.doi` | Đổi gói |
| GET | `/api/v2/auth/toi` | (đăng nhập) | Hồ sơ + **danh sách tenant truy cập được** + quyền |
| POST | `/api/v2/auth/doi-tenant` | (đăng nhập) | Switch tenant — xác minh membership trước |
| GET/PUT | `/api/v2/tenant` | `tenant.xem` / `tenant.sua` | Thông tin tenant đang thao tác |

## 5. Cách ly dữ liệu (G01.4)

Kiểm ở backend, không lọc ở frontend. Các ca IDOR/BOLA đã kiểm: đọc, sửa, xóa resource của tenant
khác; dùng carrier account của tenant khác; đổi `tenant_id` trong request; đổi resource id; xem audit
của tenant khác; webhook của tenant A cập nhật đơn tenant B. Xem `SECURITY_TEST_REPORT.md`.

## 6. Chạy local

```bash
python3 app/migrate.py        # nâng schema (có backup + kiểm bảo toàn)
python3 app/khoi_tao.py       # seed demo (chỉ khi CSDL trống)
python3 app/server.py         # http://127.0.0.1:8897/admin/
```
