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

## 8. GITHUB VÀ DEPLOY VPS

| Mục | Giá trị |
|---|---|
| Repo | **https://github.com/thanhbn123/vip-exp-hub** |
| Nhánh chuẩn | `main` |
| Checkout VPS | `/home/deploy/vip-express-hub/app` (clone từ repo) |
| Deploy | `cd /home/deploy/vip-express-hub/app && ./trien_khai/vps/deploy.sh` |
| `.env` | `app/trien_khai/vps/.env` — **không commit**, đã giữ từ bản trước |
| Dữ liệu | `/home/deploy/vip-express-hub/data` (bind mount, không nằm trong repo) |
| Image hiện tại | `vip-express-hub:vps-1832a25` |

`deploy.sh` pull fast-forward, build image tag theo commit, `docker compose up -d`, kiểm
`/api/v2/suc-khoe`. Không dùng `docker compose down -v`; không commit `.env`/DB/khoá.
Thư mục `src` cũ đã đổi tên thành `src-backup-before-git-20261020`; **sửa trong `app`**.

Quy trình sửa tiếp:
```sh
# trên máy code
git pull --ff-only
# sửa, test, commit, push main
# trên VPS
cd /home/deploy/vip-express-hub/app
./trien_khai/vps/deploy.sh
```

## 10. PRODUCTION LIVE — TRẠNG THÁI 2026-10-21

- Tài khoản **#3 `BEST Production`** đã được cập nhật credential production; **đăng nhập BEST thật
  thành công** (HTTP 200, `/User/Login`).
- **Báo cước production thật thành công**: 500 g, 100×100×100 mm, HCM → HCM:
  `FreightFee 19.800`, `TotalFeeVAT 21.780` VND.
- Tài khoản #1/#2 vẫn là mock; UI đã ẩn mock khỏi ô kiểm tra/báo cước/tạo đơn.
- **Chưa tạo đơn production**: cần Owner điền thông tin đơn thật và phê duyệt rõ; mã hiện
  **khoá ghi production** (`cua_phe_duyet`). Không tự tạo giao dịch thật.
- Webhook Bearer: **chưa có token**; cần BEST cấp hoặc Owner cho phép sinh token để gửi BEST V9.
  → **Đã xong từ 2026-10-21 09:25** (xem §11).
- Không ghi mật khẩu/token vào tài liệu này.

## 11. CALLBACK VÀ PRODUCTION — TRẠNG THÁI 2026-10-25

**Phiên bản đang chạy:** image `vip-express-hub:vps-5669f45`, commit `5669f45`, healthy.
Khôi phục: `cd /home/deploy/vip-express-hub/app/trien_khai/vps && VIP_HUB_IMAGE_TAG=vps-2941638
docker compose up -d` (image cũ còn trong registry; **không** `down -v`, không đụng `data/`).
Bản sao DB trước deploy: `backups/20261025-105858-bHdlAh`.

### 11.1 URL callback — đã định tuyến đúng tài khoản #3

| Mục | Đo được |
|---|---|
| URL BEST đã cấu hình | `https://best-uat.viporder.vn/api/v2/webhook/nhan/-kHhef2ep7_Yei5U` |
| `carrier_accounts` khớp | **#3 `BEST Production`** · `moi_truong=production` · `kich_hoat=1` · `tenant_id=1` |
| Bearer webhook | đã lưu (mã hoá) lúc `2026-10-21 09:25:53`; `webhook_ma` trong gói mã hoá **khớp** URL |
| Tenant | đọc từ dòng `carrier_accounts`, **không** từ payload |

### 11.2 BEST ĐÃ GỬI CALLBACK CHƯA? — **CHƯA**

Đọc toàn bộ log container (liên tục từ `2026-10-21 00:48` tới nay) và bảng `wh_su_kien`:

| Phép đo | Kết quả |
|---|---|
| Số lượt **POST** tới URL callback từ hạ tầng BEST | **0** |
| Số lượt **GET** tới đúng URL callback | **2** — `2026-10-21 09:29:53` và `09:51:00`, cả hai **HTTP 401** |
| `wh_su_kien` trước lượt kiểm chứng này | **0 dòng** |

**Nguyên nhân 401 đã tìm ra và đã sửa.** Route chỉ nhận `POST`; lượt `GET` rơi xuống đường API
chung và nhận `401 {"loi":"chưa đăng nhập hoặc phiên hết hạn"}`. Đọc từ phía BEST thì đó là
"URL của bạn đòi đăng nhập" — thông tin **sai** về một endpoint vốn không dùng phiên, và rất có
thể là lý do BEST dừng ở bước thử URL. Sau bản vá `5669f45`:

```text
GET  https://best-uat.viporder.vn/api/v2/webhook/nhan/-kHhef2ep7_Yei5U
  → 405 · Allow: POST · {"Result":0,"Message":"dùng POST cho callback; GET không được hỗ trợ"}
```

405 **không** tra CSDL trước khi trả, nên nó giống nhau cho mọi định danh và không tiết lộ
`webhook_ma` nào có thật.

### 11.3 Xác thực Authorization — hai lớp khoá RỜI NHAU

| | Token đăng nhập API | Bearer webhook |
|---|---|---|
| Lấy từ đâu | hub gọi `POST /User/Login` bằng credential | **BEST cấp**, cấu hình trên V9 |
| Dùng ở đâu | header hub **gửi đi** cho BEST | header BEST **gửi tới** hub |
| Kho | kho token trong tiến trình (§11.5) | `data/best_auth/bearer_webhook.enc.json` (AES-256-GCM) |
| So sánh | — | `hmac.compare_digest` trên SHA-256, có kiểm `webhook_ma` khớp |

Hai thứ này **không** thay thế nhau được — đã đo: dùng token `/User/Login` làm Bearer webhook thì
`kiem_bearer_webhook` trả `BEARER_KHONG_KHOP` và cửa webhook trả 401
(`thu_best_production.py::test_d05`).

### 11.4 Kiểm chứng cửa callback từ Internet (2026-10-24 → 25)

Gửi từ ngoài vào qua đúng URL công khai. **Tất cả đều là lượt MÔ PHỎNG NỘI BỘ**, không phải
callback của BEST — nhận ra bằng `code_best` tiền tố `SIM-`, `user-agent:
vip-hub-mo-phong-noi-bo`, và `x-forwarded-for` là IP nội bộ VPS:

| Ca | Kết quả |
|---|---|
| Bearer **sai** | **401** · `{"Result":0,...BEARER_KHONG_KHOP...}` · **không** lưu sự kiện |
| Bearer **đúng**, sự kiện mới | **200** · `{"Result":1,"Message":""}` · lưu `wh_su_kien` rồi mới ACK |
| Gửi **lại cùng sự kiện** (×2, ×3) | **200** · cùng ACK · `wh_su_kien` vẫn **1 dòng** (chống trùng) |
| Sự kiện **đến muộn** (mốc cũ hơn) | **200** · lưu thô, **không** đổi trạng thái |
| ACK | đúng đặc tả `{"Result":1,"Message":""}` — không thêm trường |
| Secret trong bản ghi | `headers_json` **không** có `authorization`; `payload_tho` không có Bearer |

Thứ tự bắt buộc đã được canh: **lưu bền `wh_su_kien` TRƯỚC khi ACK 200**. Lưu thất bại ⇒ 500,
không ACK, để hãng gửi lại (`webhook_best.py` bước 7).

**Phân biệt mô phỏng với callback thật:** bản vá thêm `x-forwarded-for`/`x-real-ip` vào
`headers_json`. Trước đó không có trường nào ghi nguồn, nên hai loại lượt là **không phân biệt
được** khi đọc lại bằng chứng. Callback thật của BEST sẽ có IP công khai của BEST; mọi dòng
`SIM-*` + IP `172.28.0.2`/`160.22.170.20` là lượt của ta.

Ba dòng `SIM-*` hiện có trong `wh_su_kien` là **bằng chứng kiểm chứng, không phải đơn thật**.

### 11.5 Token đăng nhập — đã sửa chỗ đăng nhập lại mỗi lượt

Đo **trước** bản vá, trên production thật: một lần Báo cước = **1 lượt `/User/Login` + 1 lượt
`/Service/EstimateFee`**. Tức mỗi thao tác nghiệp vụ là một lần đăng nhập mới, dù tài liệu hãng
ghi token sống **30 ngày**. `app/xac_thuc_best.py` đã có kho token mã hoá trên đĩa nhưng
`best_hop_dong` **không** dùng nó (kho đó đòi credential nằm trong kho riêng của nó, còn nguồn
sự thật của hub là `carrier_accounts.credentials_ma_hoa`).

**Sau** bản vá, đo lại trên production thật (2026-10-25):

```text
3 lần Báo cước + 1 lần Tra cứu
  → TONG LUOT HTTP TOI BEST: {'/User/Login': 1, '/Service/EstimateFee': 3, '/Order/Query': 1}
```

Luật của kho token:

- khoá = băm `(môi trường, username, password, ems_key)` — đổi mật khẩu ⇒ token cũ không dùng lại;
- hết hạn sớm **12 giờ** trước mốc 30 ngày, không trả token sắp chết vào giữa một lượt nghiệp vụ;
- hãng từ chối token (`[401]`, `token`, `expire`…) ⇒ bỏ token, đăng nhập lại, thử lại **một** lần —
  **chỉ cho thao tác ĐỌC**. Thao tác **GHI** chỉ bỏ token và trả lỗi: lượt đầu có thể đã được hãng
  nhận, gửi lại là đường tạo đơn trùng;
- `[404] The account not found or have been locked` **không** bị coi là lỗi token — đó là lỗi tài
  khoản, đăng nhập lại chỉ nhận đúng lỗi đó lần thứ hai;
- **không ghi đĩa**: khởi động lại container là đăng nhập lại một lần; đổi lại không có hai nơi
  cùng giữ token;
- rotate/revoke/khoá tài khoản BEST ⇒ bỏ token đã nhớ (nếu không, credential đã rút vẫn dùng được
  tới 30 ngày);
- nút **Kiểm tra kết nối** luôn gọi `/User/Login` thật — trả "THÀNH CÔNG" từ cache là nói sai.

### 11.6 Phạm vi production — mở đúng chỗ, khoá đúng chỗ

Chặn cũ ở giao diện (`admin/best_uat.js`) **từ chối tuyệt đối** việc lưu credential production.
Đó là sai phạm vi: nó khoá cả **đăng nhập** và **tra cứu** production — hai thao tác chỉ đọc mà
backend vốn cho phép (`cua_phe_duyet` chỉ từ chối production khi `ghi=True`).

| Thao tác | production | Chốt |
|---|---|---|
| Đăng nhập · Báo cước · Tra cứu · In nhãn/PDF | **CHO PHÉP** | cần tick phê duyệt phiên + `VIP_BEST_OWNER_APPROVED=1` + `VIP_BEST_OWNER_APPROVAL_ID` |
| Tạo đơn · Cập nhật · Sửa địa chỉ · Hủy | **KHOÁ CỨNG** | hai lớp: hàm bọc trả `blocked` ngay, và `cua_phe_duyet(ghi=True)` từ chối |

Đã đo: `POST /api/v2/best/tao-don` với tài khoản production trả **403 `blocked`** và **không
chạm tới lớp mạng** (`thu_best_production.py::test_b03`).

### 11.7 Đã kiểm chứng được gì bằng DỮ LIỆU THẬT (2026-10-25)

| Mục | Kết quả thật |
|---|---|
| Đăng nhập production | **ĐẠT** — `POST /User/Login` HTTP 200, có token |
| TLS host hãng | `sgp-seaedi.800best.com` · TLSv1.2 · `CN=*.800best.com` · GlobalSign · hạn `2026-11-28` |
| Báo cước production 500 g, 100×100×100 mm, HCM→HCM | **ĐẠT** — `FreightFee 19.800` · `FreightFeeVAT 21.780` · `TotalFee 19.800` · `TotalFeeVAT 21.780` · `ServiceId 12491` "Giao hàng tiết kiệm" (khớp số đo 2026-10-21) |
| Tra cứu production | **endpoint ĐẠT, không có vận đơn để đối chiếu** — mã bịa `79000000000000` → hãng trả `[501] The order not found`. Chứng minh `/Order/Query` gọi được bằng token đã nhớ; **không** chứng minh được parse hành trình. |
| Tái dùng token | **ĐẠT** — 4 thao tác / 1 lượt đăng nhập |
| Cửa callback công khai | **ĐẠT** — 401 với Bearer sai, 200 + ACK đúng đặc tả với Bearer đúng, chống trùng |
| TLS hub | `CN=best-uat.viporder.vn` · Let's Encrypt YE1 · hạn `2027-01-18` |

### 11.8 CÒN THIẾU — **KHÔNG được coi là đã thông tuyến**

1. **Chưa có callback THẬT nào từ BEST.** Mọi lượt 200 ở §11.4 là ta tự gửi. Việc BEST đã cấu
   hình URL và ta đã lưu Bearer **không** chứng minh BEST gọi được tới đây.
2. **Chưa có vận đơn thật** (`don_hang` = **0 dòng**). Vì vậy **chưa kiểm chứng được**: ánh xạ
   `code_best` → đơn, cập nhật trạng thái theo 23 mã, hành trình `traceLogs`, nhãn in/PDF, và
   thứ tự đến muộn trên đơn có thật. Các mục này hiện chỉ xanh ở bộ thử (mock), không phải dữ
   liệu hãng.
3. **Chưa có gói khoá `.vipkb`** — chưa có passphrase Owner. DB backup một mình **không** khôi
   phục được credential production + Bearer nếu mất `data/khoa`.
4. **Chưa diễn tập restore** trên VPS.
5. `thu_g19_route.py` còn đỏ (1 hỏng + 2 lỗi) — **đỏ sẵn từ trước bản vá này**, là ghim số của bộ
   trích route, không phải lỗi sản phẩm.

### 11.9 GỬI BEST ĐỂ XIN MỘT CALLBACK THỬ

Cấu hình phía hub đã sẵn sàng nhận. Gửi Sale/kỹ thuật BEST đúng nội dung dưới đây:

```text
Webhook URL : https://best-uat.viporder.vn/api/v2/webhook/nhan/-kHhef2ep7_Yei5U
Method      : POST   (GET sẽ trả 405 + Allow: POST — đúng thiết kế)
Header      : Authorization: Bearer <token BEST đã cấu hình trên V9>
              Content-Type: application/json
ACK          : HTTP 200 + {"Result":1,"Message":""}
Thân mẫu    : {"code_best":"<mã vận đơn>","merchant_order_code":"<mã đơn>",
               "status":"211","modified_at":<epoch ms>,"status_content":"...",
               "cod":0,"product_price":0}
```

Đề nghị BEST:

1. Bật lại cấu hình callback trên V9 cho tài khoản production này và **gửi một lượt thử**.
   Lượt thử **không cần đơn thật** — hub vẫn ACK `{"Result":1,"Message":""}` và lưu sự kiện; nó
   chỉ không cập nhật đơn nào.
2. Nếu BEST đã từng gửi mà không thấy 200, cho biết **thời điểm (giờ VN) + HTTP code + thân
   phản hồi** mà hệ thống BEST nhận được, để đối chiếu với log hub.
3. Nếu trước đó BEST thử bằng **GET** và thấy 401: lỗi đó đã được sửa, nay là 405 + `Allow: POST`.

Sau khi BEST gửi, đối chiếu bằng:

```sh
ssh viporder-staging 'docker logs vip-express-hub --since 2h 2>&1 | grep "webhook/nhan"'
# và trong UI: mục 9 "lịch sử" trên bàn nghiệm thu, hoặc:
#   SELECT id, nhan_luc, hang_ma_goc, trang_thai, headers_json FROM wh_su_kien ORDER BY id DESC;
# callback THẬT có x-forwarded-for là IP công khai của BEST và code_best KHÔNG có tiền tố SIM-.
```

### 11.10 KHÔNG TUYÊN BỐ

- **Không** tuyên bố "kết nối callback thành công": chưa có một lượt POST nào từ BEST.
- **Không** tuyên bố tracking/hành trình/nhãn in đã đúng: chưa có vận đơn thật.
- **Không** tạo/sửa/hủy đơn production, không phát sinh lấy hàng hay phí.
- REAL PASS (callback) = **BLOCKED chờ BEST gửi**. OWNER APPROVED = **PENDING**.
