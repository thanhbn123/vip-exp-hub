# BEST EXPRESS — UAT LIVE TRÊN VPS (2026-10-20)

**Trạng thái:** dịch vụ đã chạy trên VPS, **HTTPS công khai tạm qua Cloudflare Tunnel**;
chưa có chứng chỉ cho tên miền chính vì DNS chưa đúng. Không có REAL PASS/OWNER APPROVED.

## 1. URL VÀ ĐĂNG NHẬP

| Mục | Giá trị |
|---|---|
| Bàn nghiệm thu | **https://enforcement-disciplines-salon-describes.trycloudflare.com/pages/best-uat.html** |
| Quản trị | **https://enforcement-disciplines-salon-describes.trycloudflare.com/admin/** |
| Tài khoản | `anh-thanh` (theo tài khoản VIP GROUP ID) |
| Mật khẩu | đọc tại `VIP GROUP ID/cowork/secrets/owner-anh-thanh.txt` trên máy Owner — **không dán vào chat** |
| Backend | container `vip-express-hub` · `127.0.0.1:18897` · image `vps-a7a98dc` |
| Health | 200 · `/san-sang` 200 · trang UAT 200 · API chưa đăng nhập 401 |

URL tunnel là **tạm**; nếu process cloudflared restart, URL đổi. Process đang chạy:
`/home/deploy/bin/cloudflared tunnel --url http://127.0.0.1:18897`, PID lưu tại
`/home/deploy/vip-express-hub/cloudflared.pid`, log `.../logs/cloudflared.log`.

## 2. VÌ SAO CHƯA DÙNG `best-uat.viporder.vn`

- `best-uat.viporder.vn` hiện **NXDOMAIN** ở cả hai NS của `viporder.vn`
  (`ninhbinh.vclouddns.com`, `hoalu.vclouddns.com`). Bản ghi A **chưa được tạo đúng zone**.
- `best-uat.vipgroup.com.vn` có A `160.22.170.20` và resolver công cộng thấy, nhưng zone
  `vipgroup.com.vn` có **hai nhà NS** (VCloudDNS + ZoneDNS); một NS không trả bản ghi nên
  Let's Encrypt **secondary validation** thất bại (`DNS problem: networking error`).
- `best-uat.viporder.com.vn` trỏ **103.159.50.70**, không phải VPS này — không dùng.

**Cần Owner/DNS admin:**
1. Vào zone **`viporder.vn`** (VCloudDNS), tạo `best-uat` A `160.22.170.20`, DNS-only.
2. Kiểm cả hai NS:
   `dig +short @ninhbinh.vclouddns.com best-uat.viporder.vn A` và
   `dig +short @hoalu.vclouddns.com best-uat.viporder.vn A` → phải trả `160.22.170.20`.
3. Báo lại; hệ sẽ reload Caddy và kiểm cert, rồi chuyển URL chính thức.
Nếu muốn dùng `best-uat.vipgroup.com.vn`, phải tạo cùng bản ghi ở **cả VCloudDNS và ZoneDNS**.

## 3. OWNER NHẬP TÀI KHOẢN BEST SANDBOX

1. Mở URL bàn nghiệm thu ở §1, đăng nhập `anh-thanh`.
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
     `https://enforcement-disciplines-salon-describes.trycloudflare.com/api/v2/webhook/nhan/<webhook_ma>`.
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

- Chưa có chứng chỉ Let's Encrypt cho tên miền chính; đang dùng tunnel tạm.
- Chưa có credential BEST sandbox → chưa thể đăng nhập/kiểm tra hãng; **REAL PASS BLOCKED**.
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
