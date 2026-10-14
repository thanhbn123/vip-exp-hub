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
