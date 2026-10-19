# BÀN GIAO NGHIỆM THU BEST EXPRESS — URL, TÀI KHOẢN, QUY TRÌNH

**Ngày:** 2026-10-19 · **Phạm vi:** LOCAL HTTPS, sandbox; production **không** được ghi.
**Trạng thái:** hệ thống đã sẵn sàng để Owner tự đăng nhập BEST. Chưa có REAL PASS trọn vẹn vì
chưa có tài khoản test do BEST cấp và chưa có URL webhook công khai.

---

## 1. URL đang chạy

Máy chủ đã được khởi động bằng `trien_khai/best_nghiem_thu.sh` với dữ liệu tách riêng:

| Mục | URL |
|---|---|
| Bàn nghiệm thu BEST | **https://localhost:8897/pages/best-uat.html** |
| Đăng nhập quản trị | **https://localhost:8897/admin/** |
| Trạng thái hợp đồng | `GET /api/v2/best/trang-thai?tls=1` |
| Webhook nhận callback | `POST /api/v2/webhook/nhan/<webhook_ma>` |

Chứng chỉ là **tự ký cho localhost** (SAN `DNS:localhost, IP:127.0.0.1`). Trình duyệt sẽ cảnh
báo; chọn “Advanced → Proceed” một lần. Kênh vẫn là TLS, không phải HTTP bản rõ.

Nếu cổng 8897 bận, chạy lại với `VIP_HUB_PORT=...`; script in URL mới.

---

## 2. Đăng nhập hub (tài khoản demo local)

Mật khẩu sinh ngẫu nhiên, nằm ngoài repo:

```sh
grep 'shopa-owner' /tmp/vip-best-uat-data/TAI-KHOAN-DEMO.md
```

Dùng dòng đó để đăng nhập `https://localhost:8897/admin/`, rồi mở bàn nghiệm thu. Không gửi
mật khẩu này cho ai; đây là tài khoản demo của máy, không phải tài khoản BEST.

Nếu muốn khởi động lại từ đầu:

```sh
rm -rf /tmp/vip-best-uat-data /tmp/vip-best-uat-tls
VIP_HUB_DATA=/tmp/vip-best-uat-data ./trien_khai/best_nghiem_thu.sh 'OWNER-UAT-2026-10-19'
```

Script tự tạo CSDL demo, tự chạy migration schema và tự sinh chứng chỉ localhost. Không cần
chạy `khoi_tao.py`/`migrate.py` bằng tay.

---

## 3. Nhập tài khoản BEST an toàn

1. Mở bàn nghiệm thu, mục **0** → tick ô phê duyệt phiên sandbox.
2. Mục **2** → chọn môi trường **sandbox (TEST)**.
3. Nhập `Username` + `Password` do **BEST cấp cho bạn** (không phải tài khoản hub).
   `ems-key` để trống nếu BEST không cấp.
4. Tick xác nhận đã có phê duyệt; bấm **Lưu tài khoản**.
5. Trang tự chặn nếu không phải HTTPS. Backend mã hoá credential; API đọc lại **không trả**
   username/password/token.

**Không dùng tài khoản test công khai trong DOCX** (`V9Cus60437573`): đã đo ngày 2026-10-19,
BEST trả `[404] The account not found or have been locked`. Cần tài khoản test do BEST cấp.

**Không nhập tài khoản production** trong lượt này. Mọi thao tác ghi production bị chặn trong
mã (`cua_phe_duyet` + server), kể cả khi bạn cố chọn production.

---

## 4. Trình tự nghiệm thu nghiệp vụ

| Bước | Thao tác trên bàn nghiệm thu | Kỳ vọng / bằng chứng cần lưu |
|---:|---|---|
| 1 | Mục 1 — tải trạng thái + TLS | `TLSv1.2`, `CN=*.800best.com`, hạn 2026-11-28; 8 endpoint; 23 mã |
| 2 | Mục 3 — Kiểm tra đăng nhập BEST | `ĐĂNG NHẬP THÀNH CÔNG`; HTTP 200; **không** có token trên màn |
| 3 | Mục 5 — Báo cước | `TotalFee`, `TotalFeeVAT`, `FreightFee`, `CODFee`, `InsuranceFee`, `Cod`/`COD` |
| 4 | Mục 6 — Tạo đơn sandbox | nhập mã đơn **duy nhất** (ví dụ `UAT-2026-10-19-01`), câu xác nhận `TOI_DONG_Y_GOI_BEST_TEST`; kỳ vọng `Code` (mã Best), `RouteCode` |
| 5 | Mục 7 — Tra cứu mã vừa tạo | trạng thái mới nhất trong `traceLogs`; `customer Cancel`/`2` → đã hủy |
| 6 | Mục 7 — Lấy URL PDF / Tải PDF | PDF tải qua backend HTTPS; không mở URL `http://` trực tiếp |
| 7 | Mục 8 — Update / UpdateAddress / Cancel | thử lần lượt; AddressTypeId 1/2/3 phải đổi đúng người liên hệ; Cancel chỉ trước khi lấy hàng (202) |
| 8 | Mục 9 — Lịch sử | thấy audit `best_*`, sự kiện webhook (nếu có) |

**Lưu bằng chứng:** chụp màn hình từng bước, ghi mã đơn/mã vận đơn, HTTP status, thông điệp lỗi
nguyên văn. Không chụp/không dán mật khẩu, token, `Authorization`, hay toàn bộ payload có địa
chỉ/SĐT thật.

---

## 5. Webhook thật — điều kiện bắt buộc

Local `127.0.0.1` **không cho BEST gọi vào**. Ba bước:

1. Dựng một URL HTTPS công khai trỏ về máy này (reverse proxy/tunnel). Ví dụ nếu có
   `cloudflared`:
   ```sh
   cloudflared tunnel --url http://localhost:8897
   ```
   Lấy URL `https://<tên>.trycloudflare.com`.
2. Khởi động lại server với:
   ```sh
   VIP_HUB_PUBLIC_BASE_URL='https://<tên>.trycloudflare.com' \
   VIP_HUB_DATA=/tmp/vip-best-uat-data \
   ./trien_khai/best_nghiem_thu.sh 'OWNER-UAT-2026-10-19'
   ```
3. Trong bàn nghiệm thu, mục 2 hiển thị **URL webhook đầy đủ**. Gửi URL đó + Bearer token
   (do BEST cấp) cho Sale/bưu cục để cấu hình trong V9. Sau đó dán Bearer vào mục 4 và lưu.

Kiểm tra callback nội bộ trước khi nhờ BEST cấu hình:

```sh
curl -sk -X POST 'https://localhost:8897/api/v2/webhook/nhan/<webhook_ma>' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <bearer-do-BEST-cap>' \
  -d '{"code_best":"...","merchant_order_code":"...","status":"211",
       "modified_at":1790000000000,"cod":0,"product_price":0,
       "status_content":"kiểm tra"}' -i
```

Kỳ vọng: `HTTP 200` + `{"Result":1,"Message":""}`. Sai/thiếu Bearer: 401 và không lưu sự kiện.
Đây là kiểm **cục bộ**; chỉ khi BEST gọi thật mới là REAL webhook pass.

---

## 6. Dừng, dọn, và giới hạn

- Dừng: `Ctrl+C` ở terminal chạy server, hoặc `job_kill <job_id>` nếu chạy nền.
- Dữ liệu nghiệm thu nằm ở `/tmp/vip-best-uat-data` (DB, khoá, tài khoản demo). Xoá bằng
  `rm -rf /tmp/vip-best-uat-data /tmp/vip-best-uat-tls` sau khi lưu bằng chứng.
- **Không** commit `TAI-KHOAN-DEMO.md`, không đưa mật khẩu vào chat, không đưa credential vào
  biến môi trường của tiến trình web.
- Production **chưa mở**: cần một lượt phê duyệt riêng, tài khoản production, và kiểm tra lại
  toàn bộ trường/hợp đồng trước khi bỏ khoá ghi. Không dùng “sandbox pass” để tuyên bố
  production pass.

---

## 7. Câu chốt trạng thái

> Hệ thống đã sẵn sàng cho Owner đăng nhập BEST sandbox và nghiệm thu nghiệp vụ.
> Những gì đã đo được: HTTPS/TLS, login endpoint thật (âm tính), EstimateFee thật, lỗi
> `Result=2` + HTTP 200, tài khoản test trong DOCX đã khoá.
> Những gì **chưa** đo được: login thành công bằng tài khoản của Owner, tạo/tracking/in thật,
> webhook callback thật. Đó là các bước Owner thực hiện trên URL ở mục 1.
