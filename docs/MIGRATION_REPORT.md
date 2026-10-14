# MIGRATION_REPORT — schema v1 → v2 (14/10/2026)

## Mục tiêu

Tách vai trò tenant ra khỏi `users` để một user thuộc được nhiều tenant, đưa RBAC vào CSDL, thêm
`carrier_providers`, và bổ sung trường audit — **không mất dữ liệu nào**.

## Công cụ

`app/migrate.py` — có quản lý phiên bản (bảng `schema_version`), backup trước khi chạy, kiểm chứng
bảo toàn sau khi chạy, và lệnh rollback.

```bash
python3 app/migrate.py              # nâng cấp
python3 app/migrate.py --kiem       # chỉ xem phiên bản
python3 app/migrate.py --rollback <file-backup>
```

## Các bước v1 → v2

1. `tenants` + `code` (backfill slug từ tên, UNIQUE index) và `cap_nhat_luc`.
2. `users` + `platform_role`; backfill từ `vai_tro` với các giá trị `PLATFORM_*`.
3. `sessions` + `active_tenant_id`; backfill theo `users.tenant_id` cho phiên đang sống.
4. `audit` + `resource_type`, `resource_id`, `ket_qua`; backfill tách từ `doi_tuong`.
5. **Chuyển vai trò tenant → `tenant_memberships`** cho mọi user có `tenant_id`.
6. Nạp `carrier_providers` từ registry adapter (không chứa secret); thêm `credentials_doi_luc`.
7. **Sau khi đã chuyển xong**: `DROP COLUMN users.tenant_id`, `DROP COLUMN users.vai_tro`
   (SQLite 3.51 hỗ trợ; đo được trên máy chạy migration).
8. Seed `roles`/`permissions`/`role_permissions`.

Toàn bộ bước 1–8 chạy trong **một transaction**; hỏng ở bất kỳ bước nào thì CSDL giữ nguyên.

## Kết quả lượt chạy thật trên CSDL đang dùng

- Backup: `app/du-lieu/sao-luu/hub-truoc-migrate-20261014-222328.db`
- Số dòng **trước**: tenants 2 · users 7 · khach_hang 2 · carrier_accounts 4 · don_hang 1 ·
  don_lich_su 7 · wh_su_kien 4 · import_batch 0 · import_dong 0 · audit 10
- Số dòng **sau**: giống hệt từng bảng → **bảo toàn ĐẠT** (migrate.py tự so và sẽ tự khôi phục nếu lệch)
- Chuyển được 6 membership; `platform-owner` giữ `platform_role=PLATFORM_OWNER` và **không** bị gán tenant nào
- Đơn cũ `T1-000001` / `VTP5845644359` còn nguyên trạng thái `da_gui` + `giao_thanh_cong`
- `schema_version` = 2

## Kiểm chứng tự động

`TEST-014` trong `app/thu/thu_g01_g02.py` dựng **một CSDL v1 mới có dữ liệu** (tenant, 2 user,
khách, carrier account, đơn, sự kiện webhook, audit), chạy `migrate.py` thật bằng tiến trình con, rồi
kiểm: số dòng giữ nguyên · vai trò đã thành membership · `platform_role` đúng · user nền tảng
**không** bị gán tenant · `schema_version`=2. Sau đó chạy `--rollback` và kiểm CSDL trở lại schema v1
(cột `vai_tro` xuất hiện lại, dữ liệu còn đủ).

## Ràng buộc đã giữ

- Không xóa dữ liệu webhook cũ (wh_su_kien giữ nguyên 4 dòng; TEST-014 kiểm riêng điều này).
- Không đụng `gateway/du-lieu/gateway.db` — CSDL nghiệp vụ là file riêng `app/du-lieu/hub.db`.
- Không tạo tenant giả cho dữ liệu chưa rõ chủ: user nền tảng không được gán membership nào.

## Kế hoạch rollback

1. Dừng server.
2. `python3 app/migrate.py --rollback app/du-lieu/sao-luu/<file>` (bản hiện tại được cất lại trước khi đè).
3. Lùi mã nguồn: `git checkout <SHA trước khi nâng cấp>`.
4. Mốc git an toàn: `fd79d74` (trước toàn bộ SaaS), `3ab3ee8` (trước v2).
