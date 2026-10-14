# SECURITY_TEST_REPORT — VIP Express Hub (14/10/2026, local)

Môi trường đo: MacBook, Python 3.9 (stdlib), SQLite 3.51, server thật bind 127.0.0.1 trên cổng tạm,
CSDL tạm riêng cho mỗi lượt chạy. **Không** mock lớp HTTP: mọi test bắn request thật.

## Lệnh chạy

```bash
python3 app/thu/thu_g01_g02.py     # 21 test — bảo mật G01+G02 (TEST-001..015 + bổ sung)
python3 app/thu/thu_saas.py        # 19 test — nghiệp vụ (webhook, đơn, import, billing, secret)
python3 gateway/thu/thu_gateway.py #  9 test — regression gateway G01 cũ
```

## Kết quả: 49/49 PASS · 0 FAIL · 0 SKIP

### Các ca bắt buộc theo brief

| Mã | Nội dung | Test | Kết quả |
|---|---|---|---|
| TEST-001 | Tenant A không đọc được tenant B | `test_001` (đơn, khách, audit, tài khoản hãng) | PASS |
| TEST-002 | Tenant A không sửa được tenant B | `test_002` (PUT + duyệt → 404, dữ liệu B không đổi) | PASS |
| TEST-003 | Tenant A không xóa được resource B | `test_003` (DELETE đơn, khóa carrier account → 404) | PASS |
| TEST-004 | Tenant A không dùng được carrier account B | `test_004` (gửi đơn bằng account B → 404, không sinh mã vận đơn) | PASS |
| TEST-005 | User vô hiệu không đăng nhập được | `test_005` | PASS |
| TEST-006 | Membership vô hiệu mất quyền truy cập | `test_006` (phiên đang mở mất hiệu lực + không đăng nhập lại được) | PASS |
| TEST-007 | Viewer không tạo/sửa dữ liệu | `test_007` (đơn, khách, sửa, duyệt → 403; vẫn xem được) | PASS |
| TEST-008 | Staff không đổi được role | `test_008` | PASS |
| TEST-009 | Tenant Admin không cấp được quyền Platform | `test_009` (4 vai trò đều 403; PLATFORM_ADMIN cũng không tạo tenant/đổi gói) | PASS |
| TEST-010 | Đổi `tenant_id` trong request không vượt quyền | `test_010` (body + query + switch-tenant) | PASS |
| TEST-011 | Đổi resource ID không lộ dữ liệu tenant khác | `test_011` | PASS |
| TEST-012 | Session đã revoke hết hiệu lực | `test_012` | PASS |
| TEST-013 | Không lộ password/token trong log | `test_013` (quét log server, API, CSDL, cookie phiên) | PASS |
| TEST-014 | Migration bảo toàn dữ liệu | `test_014` (dựng CSDL v1 thật → migrate → kiểm → rollback) | PASS |
| TEST-015 | Gateway cũ vẫn đạt 9/9 | `test_015` (chạy bộ thử gateway bằng tiến trình con) | PASS |

### Ca bổ sung phát sinh trong lúc triển khai

| Test | Nội dung | Kết quả |
|---|---|---|
| `test_016` | Switch tenant đúng membership; không mang dữ liệu tenant cũ sang | PASS |
| `test_017` | Reset mật khẩu: token một lần, hết hạn, thu hồi phiên cũ, không lộ tài khoản tồn tại | PASS |
| `test_018` | Audit đủ trường + ghi cả lượt **bị từ chối**; không chứa mật khẩu | PASS |
| `test_019` | RBAC lấy từ CSDL: xóa một dòng `role_permissions` → endpoint từ chối ngay | PASS |
| `test_020` | Carrier account: rotate/revoke credentials; tenant khác không rotate được | PASS |
| `test_021` | Tenant bị khóa → thành viên mất quyền ngay, không đăng nhập được | PASS |

### Nghiệp vụ (thu_saas.py, 19 test)

Webhook: giả mạo bị từ chối và **không lưu**; trùng không cập nhật hai lần; sai thứ tự không kéo lùi
trạng thái; sự kiện của account tenant B không đụng đơn tenant A (đánh dấu `khong_khop`); retry 3 lần
→ DLQ → replay. Đơn: idempotency theo `Idempotency-Key`; hãng lỗi → đơn lùi `da_duyet`; hãng timeout
→ giữ `dang_gui` + cờ `can_doi_soat_ket_qua`, **không** nhận là thành công. Import: CSV + XLSX, dòng
lỗi không hỏng batch, duyệt lại không nhân đôi đơn. Secret: không ra API/log/CSDL. CSRF: thiếu header
`X-Requested-With` → 403. LIVE adapter bị khóa. Chữ ký J&T khớp công thức tài liệu.

## Lỗi thật phát hiện và đã sửa trong đợt này

1. **Segfault trong `gateway/`** (nghiêm trọng). Bộ thử gateway chết hẳn (`SIGSEGV`, exit 139) ở
   khoảng **1/5 lượt chạy** — đo thật: 5 lượt liên tiếp có 1 lượt exit 139. Nguyên nhân: một kết nối
   SQLite dùng chung cho mọi thread. Đây **đúng cấu trúc** đã gây lỗi đọc sai byte ở `app/` trước đó,
   nên sửa bằng cách **đổi cấu trúc** (kết nối theo từng thread) chứ không vá riêng.
   Kiểm lại: **0/20 lượt hỏng**.
   *Ghi nhận trung thực:* con số "gateway 9/9 PASS" báo ở đợt trước là **đúng nhưng may rủi** — bộ thử
   khi đó không chạy đủ nhiều lượt để lộ ca hỏng.
2. **Đọc sai dữ liệu khi có request đồng thời** ở `app/` — cùng nguyên nhân trên; đã sửa trước đó và
   kiểm bằng 40 request song song (0 lỗi).
3. **Lỗi của chính bộ thử** (không phải sản phẩm): `test_012` thu hồi phiên của user dùng chung làm
   các test sau 401. Đã tách user riêng cho ca đó.

## Giới hạn phạm vi đã đo (nói rõ để không suy rộng)

- Số liệu trên đo **trên MacBook, một tiến trình, CSDL SQLite local**. Chưa đo tải đồng thời lớn,
  chưa đo trên máy khác, chưa đo với CSDL khác SQLite.
- "49/49 PASS" là phạm vi **ba bộ thử nêu trên**, không phải "toàn hệ thống không còn lỗi".
- Chưa có: rate-limit cổng webhook, TLS, quét phụ thuộc, kiểm thử thâm nhập độc lập.
- Mã hóa credentials là encrypt-then-MAC tự dựng trên stdlib — đủ cho local, **chưa đạt chuẩn
  production** (cần AES-GCM/KMS).
