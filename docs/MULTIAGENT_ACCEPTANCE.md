# MULTIAGENT_ACCEPTANCE — VIP EXPRESS HUB (14/10/2026, local)

PROJECT: VIP EXPRESS HUB
CONTROLLER: AG-00
AGENTS: AG-01 SECURITY · AG-02 CARRIER · AG-04 IMPORT · AG-06 FRONTEND · AG-07 QA
PROJECT PATH: `~/Projects/vip-express-hub`
BASELINE SHA: `fd79d74` · FINAL LOCAL SHA: `fb61ec2` (nhánh `main`, **không push**)

## Cổng chất lượng

| Gate | Kết quả | Bằng chứng |
|---|---|---|
| G01 Tenant isolation | **PASS** | TEST-001..004, 010, 011 + 16 ca soát mới của AG-07 |
| G02 Authentication/RBAC | **PASS** | TEST-005..009, 012 + khóa tạm theo thời gian (q06) |
| G03 Carrier Adapter | **PASS** | 53 ca; getCapabilities, NormalizedCarrierError, 26 mã lỗi J&T thật |
| G03 AES-256-GCM | **PASS** | 25 ca; key_id/version, xoay khóa chạy thật trên dữ liệu sống |
| G04 Order Service | **NOT STARTED** | không được giao đợt này |
| G05 Import Engine | **PASS** | 21 ca; formula injection, zip bomb, XXE, giới hạn tài nguyên |
| G06 Webhook multi-tenant | **PARTIAL** | đã có từ đợt trước và còn đạt; **không** được giao mở rộng đợt này |
| FRONTEND | **PASS (kiểm tay)** | 14 màn ở 3 cỡ, không tràn ngang; **không có bộ thử tự động** |
| SECURITY | **PASS sau khi vá** | 14 phát hiện của AG-07 → đã vá hết, 30/30 ca soát ĐẠT |
| REGRESSION | **PASS** | 184 test, 0 hỏng; gateway 0/20 lượt hỏng |

## Kết quả test (đo thật, 8 bộ)

```
thu_tich_hop.py    6   OK      thu_saas.py       19  OK
thu_bao_mat.py    25   OK      thu_nhap_file.py  21  OK
thu_g03.py        53   OK      thu_qa_soat.py    30  OK
thu_g01_g02.py    21   OK      thu_gateway.py     9  OK
TỔNG 184 PASSED · 0 FAILED · 0 SKIPPED
```

## Phát hiện bảo mật — AG-07 tìm 14, AG-00 vá hết

| Mã | Mức | Vấn đề | Trạng thái |
|---|---|---|---|
| Q-01 | **CRITICAL** | Người vô danh xin được token đặt lại mật khẩu của bất kỳ ai → chiếm PLATFORM_OWNER trong 3 yêu cầu | **ĐÃ VÁ** (cờ mặc định TẮT) |
| Q-02 | **HIGH** | Server trả mã nguồn Python cho người vô danh, lộ secret HMAC của 5 hãng | **ĐÃ VÁ** (danh sách TRẮNG) |
| Q-03 | MEDIUM | 2 đường `/platform/*` quên kiểm quyền | **ĐÃ VÁ** (một cổng chung) |
| Q-04 | LOW | 404-vs-403 làm dò được tenant nào tồn tại | **ĐÃ VÁ** (authorize trước) |
| Q-05/b/c | MEDIUM | `gioi_han=-1` ⇒ LIMIT không giới hạn; sai kiểu ⇒ HTTP 500 | **ĐÃ VÁ** |
| Q-06 | MEDIUM | 5 yêu cầu vô danh khóa chết tài khoản bất kỳ, không có đường tự mở | **ĐÃ VÁ** (khóa TẠM 15 phút) |
| Q-07b/c | MEDIUM | Không chặn độ dài `dong_ids`; body 20 MB cho đường vô danh | **ĐÃ VÁ** |
| Q-08 | LOW | Xuất CSV đơn hàng không vô hiệu công thức | **ĐÃ VÁ** (dùng chung hàm làm sạch) |
| Q-09g/Q-10 | LOW | `chuyen_batch` ghi theo id trần, chỉ an toàn nhờ caller | **ĐÃ VÁ** (bắt buộc tenant_id) |
| Q-11/Q-12 | LOW | Nợ bộ thử: đòi file ngoài git; cổng cố định | Q-11 **ĐÃ VÁ**; Q-12 còn |

## Migration

Chạy thật trên CSDL đang dùng: v3 → v4 → v5 → v6. **Mỗi lượt có backup + kiểm bảo toàn số dòng.**
Không bảng nào mất dòng. Xoay khóa AES-GCM chạy thật: 4/4 tài khoản sang khóa mới, vẫn đọc được,
khóa cũ giữ lại.

## Việc còn lại / Owner quyết

1. **Credentials J&T thật** — chờ, theo quyết định của anh (khi bắt đầu kiểm thử LIVE).
2. **Deploy VPS** — chờ, sau nghiệm thu local.
3. **Tài liệu Partner API Viettel Post** — nút thắt THẬT của VTP (repo không có gì tái dùng).
4. **Mâu thuẫn trong tài liệu J&T**: mã `110` vừa là *Arrival* vừa là *quét kiện có vấn đề* ở hai
   chỗ của cùng tài liệu. Đang theo bảng tham số; hậu quả nếu sai: đơn có vấn đề không nổi lên.
5. **Hạn mức gói chưa chạm bước import** — một batch tạo được nhiều đơn nháp không tính hạn mức.
6. **Khóa mã hóa chưa vào đường sao lưu** — mất thư mục `app/du-lieu/khoa/` là mất sạch secret.
7. **Chưa có rate-limit theo IP**, chưa có TLS, chưa đo tải đồng thời thật.

## Nói rõ về chất lượng nghiệm thu

QA do **tác tử AI** thực hiện, **không phải independent human review**. Bốn mục CRITICAL/HIGH nên
có người đọc lại bản vá, không chỉ nhìn ca thử chuyển xanh. Frontend **không có bộ thử tự động**;
kết quả là một lượt bấm tay trên một trình duyệt.
