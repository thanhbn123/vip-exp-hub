# BEST EXPRESS — UAT LIVE TRÊN VPS (2026-10-20)

**Trạng thái:** dịch vụ đã chạy trên VPS; **HTTPS chính thức `best-uat.viporder.vn`** đã có
chứng chỉ Let's Encrypt hợp lệ. Chưa có REAL PASS/OWNER APPROVED vì chưa có credential BEST
sandbox và chưa có webhook thật do BEST cấu hình.

## 1. URL VÀ ĐĂNG NHẬP

| Mục | Giá trị |
|---|---|
| Bàn nghiệm thu | **https://best-uat.viporder.vn/pages/best-uat.html** |
| Quản trị | **https://best-uat.viporder.vn/admin/** |
| Tài khoản | `anh-thanh` (theo tài khoản VIP GROUP ID) |
| Mật khẩu tạm | `/Users/viporder/VIP-EXPRESS-UAT-anh-thanh.txt` — đúng **20 ký tự, không newline**; **không dán vào chat**; đổi và xoá sau khi vào |
| Backend | container `vip-express-hub` · `127.0.0.1:18897` · image `vps-a7a98dc` |
| Health | 200 · `/san-sang` 200 · trang UAT 200 · API chưa đăng nhập 401 |

DNS `best-uat.viporder.vn` đã trỏ đúng `160.22.170.20`; Caddy đã cấp cert
`CN=best-uat.viporder.vn` (Let's Encrypt YE1, hạn 2027-01-18). Tunnel tạm đã dừng.
Nếu cert hết hạn, Caddy tự gia hạn; kiểm bằng `openssl s_client` ở §5.

## 2. DNS / HTTPS ĐÃ XONG

- `best-uat.viporder.vn` → `160.22.170.20` ở cả hai NS VCloudDNS.
- Cert Let's Encrypt hợp lệ: `CN=best-uat.viporder.vn`, issuer `Let's Encrypt YE1`,
  hiệu lực 2026-10-20 → 2027-01-18; HTTP tự chuyển 308 sang HTTPS.
- Caddy chỉ còn site `best-uat.viporder.vn`; tên phụ `best-uat.vipgroup.com.vn` đã bỏ khỏi block
  để tránh ACME lỗi.
- Không cần đổi DNS/firewall nữa cho tên chính thức.

## 3. OWNER NHẬP TÀI KHOẢN BEST SANDBOX

> Hiện DB đã có **1 tài khoản tên “BEST mock”** (môi trường `mock`). Tài khoản này **không**
> dùng để kiểm tra hãng thật. Cần tạo **một tài khoản mới, môi trường `sandbox`**.

1. Mở URL bàn nghiệm thu ở §1, đăng nhập `anh-thanh` (mật khẩu tạm ở §1).
2. Mục **0**: tick xác nhận đã được Owner phê duyệt sandbox.
3. Mục **2 — Tài khoản BEST**:
   - Môi trường: **sandbox (TEST)**.
   - Nhập `Username` + `Password` do **BEST cấp**; `ems-key` chỉ nhập nếu BEST cấp.
   - Tick “đã có phê duyệt của Owner”, bấm **Lưu tài khoản**.
   - Credential được mã hoá AES-256-GCM; API không trả lại secret.
4. Mục **3 — Kiểm tra kết nối**: chọn tài khoản, “Tôi đã phê duyệt kiểm tra thật”, bấm kiểm tra.
   - Thành công: `ĐĂNG NHẬP THÀNH CÔNG`, HTTP 200, không hiện token.
   - Thất bại: đọc đúng mã lỗi/HTTP; không đoán.
5. Mục **4 — Webhook Bearer**: dán Bearer token do BEST cấp, bấm lưu.
   - UI hiện **URL webhook đầy đủ** dạng
     `https://best-uat.viporder.vn/api/v2/webhook/nhan/<webhook_ma>`.
6. Mục **5 — Báo cước**: nhập địa chỉ đường gửi/nhận (đã có ô), cân gram, kích thước mm, COD.
7. Mục **6 — Tạo đơn sandbox**: nhập đơn duy nhất, câu xác nhận **`TOI_DONG_Y_GOI_BEST_TEST`**,
   bấm gửi. Production luôn bị khoá.
8. Mục **7 — Tra cứu/in PDF**; mục **8 — Update/UpdateAddress/Cancel**; mục **9 — lịch sử**.

## 4. THÔNG TIN GỬI BEST EXPRESS (V9)

Sau khi tạo tài khoản BEST trong UI, gửi Sale/bưu cục đúng thông tin **lấy từ màn hình**:

```text
Webhook URL : <copy nguyên URL trong mục 4>
Method      : POST
Header      : Authorization: Bearer <token BEST cấp>
Content-Type: application/json
ACK mong đợi: {"Result":1,"Message":""}
```

- Không gửi mật khẩu/username BEST qua chat; chỉ gửi URL + Bearer do BEST cấp.
- BEST phải gọi được URL HTTPS công khai ở trên. Nếu tunnel đổi URL, phải cập nhật lại V9.
- Kiểm tra nội bộ trước khi nhờ BEST:
  ```sh
  curl -sS -X POST '<URL webhook>' \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer <token>' \
    -d '{"code_best":"TEST","merchant_order_code":"TEST","status":"211",
         "modified_at":1790000000000,"cod":0,"product_price":0,"status_content":"kiểm tra"}' -i
  ```
  Kỳ vọng 200 + `{"Result":1,"Message":""}`; sai/thiếu Bearer 401 và không lưu sự kiện.

## 5. BACKUP / VẬN HÀNH

- Backup DB thật đã chạy: `/home/deploy/vip-express-hub/backups/20261020-072502-IjJWkT/`
  gồm `hub.db` + `hub.db.sha256` (568 KB), kiểm checksum.
- Cron đã cài: `17 2 * * * .../backup.sh >> .../logs/backup.log 2>&1` (giữ 14 ngày).
- **Chưa có gói khoá `.vipkb`** vì chưa có passphrase Owner. DB backup một mình **không đủ**
  khôi phục credential nếu mất `data/khoa`. Cần Owner chọn passphrase và chạy:
  ```sh
  ssh viporder-staging
  cd /home/deploy/vip-express-hub/src/trien_khai/vps
  read -s VIP_HUB_BACKUP_PASSPHRASE; export VIP_HUB_BACKUP_PASSPHRASE
  ./backup.sh
  unset VIP_HUB_BACKUP_PASSPHRASE
  ```
  Cất gói `.vipkb` + passphrase ở hai nơi khác nhau, không cùng chỗ với DB.
- Restore: `restore.sh <thư-mục-backup>` yêu cầu `TOI_DONG_Y_PHUC_HOI`; **chưa diễn tập thật**.
- Log container: `docker logs --tail 100 vip-express-hub`; tunnel: `.../logs/cloudflared.log`.

## 6. GIỚI HẠN HIỆN TẠI

- HTTPS chính thức đã có; không còn dùng tunnel tạm.
- Tài khoản hiện tại là **mock**; chưa có credential BEST sandbox → **REAL PASS BLOCKED**.
- Chưa có Bearer/BEST cấu hình V9 → webhook thật **BLOCKED**.
- `VIP_BEST_OWNER_APPROVED=1` đang bật cho phiên UAT; gỡ (`0`) sau khi nghiệm thu xong.
- Production writes vẫn bị khoá trong mã; không tạo đơn production.
- Hồi quy toàn bộ vẫn còn 20 bộ đỏ (test harness + 2 lỗi sản phẩm có sẵn G21/doi_soat); không
  tuyên bố full green.

## 7. ROLLBACK

```sh
cd /home/deploy/vip-express-hub/src/trien_khai/vps
docker compose down            # KHÔNG dùng -v
# Caddy: khôi phục backup đã lưu, nạp lại JSON qua admin API hoặc reload
```
Không xoá `data/`; không `docker compose down -v`; không đụng container khác.
