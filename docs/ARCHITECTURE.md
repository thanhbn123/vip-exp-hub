# ARCHITECTURE — VIP Express Hub Multi-Tenant SaaS (local-first)

> **Cập nhật 14/10/2026 — schema v2.** Một user thuộc NHIỀU tenant qua `tenant_memberships`;
> RBAC chuyển vào CSDL (`roles`/`permissions`/`role_permissions`); thêm `carrier_providers`,
> `reset_tokens`, `schema_version`. Chi tiết: `G01_MULTI_TENANT.md`, `G02_AUTH_RBAC.md`,
> `MIGRATION_REPORT.md`. Kết nối SQLite là **theo từng thread** (dùng chung một connection giữa
> các thread đã gây đọc sai dữ liệu ở `app/` và SIGSEGV ở `gateway/` — xem SECURITY_TEST_REPORT).

Nguyên tắc: Python 3 stdlib + SQLite (không thư viện ngoài — chạy được trên mọi máy Mac của VIP ORDER), bind `127.0.0.1`, mã mới nằm trong `app/` — **không ghi đè** `gateway/` (bản G01 đã nghiệm thu) và các trang demo G00.

```text
                    ┌──────────────────────────────────────────┐
                    │  app/server.py  (127.0.0.1:8897)          │
                    │  - Phục vụ tĩnh: admin/ + pages/ + assets │
                    │  - API /api/v2/*  (JSON, cookie session)  │
                    └───────┬──────────────────────────────────┘
        ┌───────────────────┼───────────────────────┐
        │                   │                        │
  bao_mat.py          don_hang.py              webhook.py
  đăng nhập/phiên     Order Service            Webhook Gateway tenant-aware
  RBAC 6 vai trò      idempotency, duyệt,      verify → lưu thô → queue →
  khóa TK, audit      gửi hãng, lịch sử        normalize → resolve tenant+đơn
  mã hóa credentials        │                   → cập nhật → audit; retry/DLQ
        │                   │                        │
        │             adapter.py  ◄── adapter_vtp.py / adapter_jt.py (MOCK)
        │             Carrier Adapter Interface: createOrder/cancelOrder/
        │             getOrder/trackOrder/getShippingFee/getShippingLabel/
        │             normalizeTrackingStatus + capabilities
        │                   │
        └────────────► csdl.py (SQLite app/du-lieu/hub.db, WAL, FK)
                            │
     nhap_file.py      billing.py        ai_gateway.py
     Import batch      gói/hạn mức/      AI Integration Gateway (MOCK)
     CSV/XLSX/PDF*     usage backend     interface, policy: AI không vượt
                                          auth/tenant/approval
```

## Cách ly tenant (luật cứng)

- `tenant_id` KHÔNG BAO GIỜ nhận từ client. Mọi API nghiệp vụ lấy tenant từ **phiên đăng nhập** (bảng `sessions` → `users.tenant_id`).
- Mọi câu SELECT/UPDATE nghiệp vụ đều có `WHERE tenant_id = ?` từ phiên; truy cập theo id phải kiểm `resource.tenant_id == session.tenant_id` (resource ownership).
- Vai trò platform (`tenant_id IS NULL`) dùng nhóm API `/api/v2/platform/*` riêng; tenant thường không gọi được.
- Webhook resolve tenant từ **carrier_account** (định danh trong URL + chữ ký bằng secret của chính account đó), không từ nội dung payload.

## Vai trò (G02)

`PLATFORM_OWNER > PLATFORM_ADMIN` (toàn nền tảng) · `TENANT_OWNER > TENANT_ADMIN > TENANT_STAFF > TENANT_VIEWER` (trong tenant). Ma trận quyền cứng trong `bao_mat.py::QUYEN`, kiểm ở backend từng route.

## Bảng dữ liệu chính (app/du-lieu/hub.db)

`tenants` (có `code`) · `goi_dich_vu` · `users` (UNIQUE ten_dang_nhap; `platform_role`; pbkdf2-sha256 200k; khóa sau 5 lần sai) · `tenant_memberships` (user↔tenant+role) · `roles`/`permissions`/`role_permissions` · `sessions` (lưu SHA-256 của token; thu hồi được) · `khach_hang` · `carrier_accounts` (credentials **mã hóa** bằng khóa file `app/du-lieu/khoa-noi-bo.key`, 0600, ngoài git) · `don_hang` (UNIQUE(tenant_id, idem_key); trạng thái nghiệp vụ tách trạng thái giao) · `don_lich_su` · `wh_su_kien` (UNIQUE(account_id, event_id); thô + retry + DLQ) · `import_batch` / `import_dong` · `usage_thang` · `audit`.

## Trạng thái đơn

Nghiệp vụ: `nhap → da_duyet → dang_gui → da_gui → (huy)`. Chỉ `da_gui` khi adapter trả xác nhận + mã vận đơn; timeout → giữ `dang_gui` + cờ `can_doi_soat_ket_qua` (phải getOrder kiểm lại, không tự nhận thành công).
Giao vận (từ webhook, tách riêng): `cho_lay → lay_hang → dang_giao → giao_that_bai/giao_thanh_cong → hoan_hang` với thứ hạng chống out-of-order (kế thừa thiết kế G01).

## Mã hóa credentials (mức local)

Encrypt-then-MAC tự dựng trên stdlib: keystream SHA-256(key‖nonce‖counter) + HMAC-SHA256; khóa ở file 0600 ngoài git. **Giới hạn ghi rõ:** đủ cho demo local; lên production phải thay bằng AES-GCM/KMS (thư viện vetted). Secret không bao giờ trả ra frontend, không ghi vào log; API chỉ trả 4 ký tự cuối.

## Những gì là MOCK (không nhận là thật)

- `adapter_vtp.py`, `adapter_jt.py`: transport MOCK — mô phỏng phản hồi hãng (có ca lỗi/timeout). `adapter_jt.py` dựng **đúng theo tài liệu công khai** (headers/digest/bizContent như docs); đường LIVE để sẵn nhưng **khóa** (`cho_phep_live=False`) tới khi Owner cấp credentials + duyệt.
- `ai_gateway.py`: toàn bộ là MOCK interface chờ VIP AI Brain.
- Billing: chưa nối thanh toán thật — chỉ gói/hạn mức/usage.
