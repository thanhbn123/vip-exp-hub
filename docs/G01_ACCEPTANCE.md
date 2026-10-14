# G01_ACCEPTANCE — VIP Express Hub

- **PROJECT:** VIP EXPRESS HUB
- **GATE:** G01 — UNIVERSAL WEBHOOK GATEWAY (local-first)
- **STATUS:** PASS (bộ thử 9/9 + đầu-cuối qua UI) — chờ Owner nghiệm thu
- **Ngày kiểm:** 14/10/2026 trên MacBook. Python 3 stdlib + SQLite, **không thư viện ngoài**, bind `127.0.0.1` — không mở ra internet, không gọi hãng thật nào. Mọi "hãng" trong G01 là **bộ mô phỏng** `gateway/mo_phong_hang.py`.

## Cách chạy

```bash
cd ~/Projects/vip-express-hub
python3 gateway/server.py            # gateway tại http://127.0.0.1:8898
python3 gateway/mo_phong_hang.py     # bắn 24 sự kiện mô phỏng 5 hãng (có ca lỗi + sai thứ tự)
python3 gateway/thu/thu_gateway.py   # bộ thử 9 ca (CSDL tạm riêng, không đụng dữ liệu demo)
```

Xem trên giao diện: mở Webhook Center (G00) → đổi **Nguồn** sang "Gateway local G01" → khóa đọc `demo-viewer-key`, khóa replay `demo-admin-key` (khóa demo local, ghi trong `gateway/cau_hinh.py`).

## IMPLEMENTED (đối chiếu yêu cầu G01 trong đặc tả mục 5)

| Yêu cầu đặc tả | Hiện thực |
|---|---|
| Gateway đa hãng | `POST /api/webhook/{vtp\|ghn\|ghtk\|jt\|best}` |
| Per-carrier authentication, không giả định chung một sơ đồ | 4 sơ đồ khác nhau: HMAC-SHA256 (VTP, BEST — khác header), Bearer (GHN), header token (GHTK), Basic (J&T) — `gateway/xac_thuc.py` |
| Durable raw event persistence | Lưu **byte thô + headers** vào SQLite TRƯỚC khi xử lý; payload hỏng JSON vẫn được lưu bền rồi mới vào DLQ |
| Queue/worker | Hàng đợi + worker nền tuần tự (`gateway/hang_doi.py`); khởi động lại tự nạp việc dở, sự kiện `dang_xu_ly` mồ côi được trả về `moi` |
| Idempotency | `UNIQUE(hang, event_id)` **cưỡng chế bằng CSDL**; lần gửi trùng trả `da_nhan_truoc_do`, không xử lý lại (có test chứng minh hành trình không nhân đôi) |
| Out-of-order handling | Thứ hạng trạng thái (`cau_hinh.HANG_TRANG_THAI`); sự kiện muộn KHÔNG lùi trạng thái vận đơn nhưng vẫn vào sổ `hanh_trinh` với `ap_dung=0` + lý do |
| Retry/backoff | Lỗi tạm thời retry tối đa 3 lần, backoff 0.5→1→2s; lỗi vĩnh viễn (định dạng/thiếu trường) đi thẳng DLQ, không retry vô ích |
| DLQ | `GET /api/dlq`; sự kiện giữ nguyên payload thô + lý do + số lần thử |
| Replay với RBAC và audit | `POST /api/su-kien/{id}/replay` chỉ `admin`; `viewer` bị 403; mỗi replay ghi bảng `audit` (ai · vai trò · lúc · đối tượng · trạng thái trước) |
| Tách trạng thái hành trình / COD | Bảng `van_don` (trạng thái hiện hành + COD) tách khỏi `hanh_trinh` (mọi sự kiện, kể cả không áp dụng); đối soát COD để gate sau |
| Không đụng callback Viettel Post hiện tại | Toàn bộ chạy local 127.0.0.1, không endpoint công khai, không sửa gì ở `vip-viettelpost` |

## TEST_EVIDENCE

**Bộ thử tự động `gateway/thu/thu_gateway.py`: 9/9 OK (0.698s)** — chạy server thật trên cổng 18898, CSDL tạm:
1. Xác thực từng hãng: sai chữ ký/token → 401 và **không lưu**; đúng sơ đồ → 202 cho cả 5 hãng.
2. Idempotency: gửi trùng → 1 dòng trong CSDL, 1 dòng hành trình, phản hồi `da_nhan_truoc_do`.
3. Out-of-order: `giao_thanh_cong` rồi `dang_giao` → trạng thái không lùi, sự kiện muộn ghi `ap_dung=0`.
4. Lưu bền thô: byte đọc lại == byte đã gửi (có tiếng Việt).
5. Lỗi vĩnh viễn (thiếu trường) → DLQ ngay, `so_lan_thu=0`.
6. Lỗi tạm thời → đúng 3 lần thử → DLQ → sửa nguồn → replay admin → `xong`.
7. RBAC: không khóa 401, viewer đọc 200, viewer replay 403, admin replay 202 + có vết audit.
8. Payload không phải JSON → vẫn 202 + lưu bền → DLQ với lý do.
9. Hãng lạ 404; `/api/suc-khoe` không cần khóa.

**Đầu-cuối bằng mô phỏng (14/10 ~21:00):** 24 sự kiện 5 hãng (1 ca ép lỗi, 2 vận đơn bắn sai thứ tự) → 23 `xong`, 1 DLQ sau 3 lần thử, 6/6 vận đơn về đúng trạng thái cuối. UI Webhook Center nguồn gateway hiển thị đúng 24/23/1/0; replay bằng khóa viewer bị chặn "can quyen admin", đổi khóa admin thì `da_nap_lai` và bảng audit có dòng `replay · su_kien:3 · trang thai truoc: dlq`.

Phạm vi kiểm: đúng các ca nêu trên, trên MacBook, một tiến trình gateway; **chưa đo** tải đồng thời lớn, chưa kiểm trên máy khác.

## DEMO_ONLY / GIỚI HẠN

- Khóa hãng + khóa API là **giá trị demo nằm trong `cau_hinh.py`** — chấp nhận ở local; lên máy chủ thật phải chuyển sang biến môi trường/kho bí mật và đổi khóa.
- Replay sự kiện vẫn còn `demo_force_fail` trong payload sẽ lỗi lại và quay về DLQ — đúng thiết kế (nguồn chưa sửa thì replay không cứu), đã ghi ở test 6 cách xử đúng.
- Chưa có: rate-limit cổng webhook, xoay vòng dung lượng CSDL, đối soát COD (gate sau), TLS (local không cần).

## NEXT_GATE

G02 — tái dùng adapter/API Viettel Post thật (đọc mã `vip-viettelpost`, không ảnh hưởng production). **Chỉ làm khi Owner có lệnh mới.**
