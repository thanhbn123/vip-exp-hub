# G15 — WEBHOOK HTTPS: THIẾT KẾ, KHÔNG TRIỂN KHAI

Mã việc: **I05** · người viết: **AG-04 (INFRASTRUCTURE ENGINEER)** · ngày **15/10/2026**
Trạng thái: **THIẾT KẾ** — không có cổng nào được mở, không có tunnel nào được dựng, không
có lượt deploy nào. Chỉ thị `V-G11-01` (triển khai staging) **CHƯA CẤP**.

> **Đây không phải một lượt triển khai và không được đọc như một lượt triển khai.**
> Mọi cấu hình dưới đây là **bản mẫu để anh Thành duyệt**, không phải thứ đang chạy. Máy này
> vẫn chỉ có máy chủ bind `127.0.0.1`, không TLS, không tên miền, không reverse proxy.

---

## 0. Vì sao webhook cần HTTPS, và vì sao KHÔNG được tự dựng

J&T đẩy sự kiện hành trình tới `POST /api/v2/webhook/nhan/<webhook_ma>`. Đường đó **vô danh**
(không phiên đăng nhập) và xác thực bằng chữ ký của chính tài khoản hãng — xem
`app/webhook.py` mục `BO_XAC_THUC`. Hệ quả trực tiếp:

1. **Chữ ký bảo vệ tính TOÀN VẸN, không bảo vệ tính BÍ MẬT.** Không có TLS thì `bizContent`
   (mã vận đơn, số COD, tên và địa chỉ người nhận) đi trên đường công khai dạng đọc được.
2. **`jt_digest` là MD5, không phải HMAC.** `digest = base64(md5(bizContent + privateKey))`.
   Với MD5 trần, kẻ đứng giữa có thể **dò `privateKey` bằng tấn công từ điển** nếu thấy được
   một cặp `(bizContent, digest)`. TLS không phải "nên có" — nó là thứ giữ cho khoá ký không rò.
3. **Không có TLS thì `Secure` không được đặt trên cookie phiên** (`server.py::_dung_https`
   chỉ thêm `; Secure` khi `VIP_HUB_HTTPS=1`). Cookie phiên đi trên HTTP là chiếm phiên.

⇒ **TLS là điều kiện CẦN để bật webhook thật.** Nhưng dựng TLS công khai trên máy anh Thành
là mở một cửa ra Internet — việc **CẤM**. Nên tài liệu này dừng ở thiết kế.

---

## 1. HỢP ĐỒNG ĐƯỜNG DẪN — giữ nguyên, không đổi

| Thành phần | Giá trị HIỆN TẠI (đã có mã) | Ghi chú |
|---|---|---|
| Đường nhận | `POST /api/v2/webhook/nhan/{webhook_ma}` | `webhook_ma` do hệ sinh, UNIQUE, **không phải bí mật** (nó nằm trong URL) |
| Xác thực mock | `X-Webhook-Signature: hex(HMAC-SHA256(secret, body))` | `xac_thuc_hub_hmac` |
| Xác thực J&T | header `apiAccount` · `digest` · `timestamp` | `xac_thuc_jt_digest`, mức **DOCUMENTED**, chưa gặp hãng thật |
| Trả lời | `202` đã nhận · `200` trùng · `401` chữ ký sai · `404` webhook lạ · `429` quá tải | đã đo |
| Chống trùng | `UNIQUE(carrier_account_id, event_id)` trên `wh_su_kien` | chống trùng ở **CSDL**, không ở bộ nhớ |

**Ba điều CẤM ĐỔI trong thiết kế này:**
- **Không** đổi `webhook_ma` thành bí mật rồi dựa vào nó để xác thực. URL nằm trong log của
  mọi lớp trung gian; bí mật nằm trong URL là bí mật đã lộ.
- **Không** gộp `401` và `404` thành một. `404` là "không có tài khoản này"; `401` là "có tài
  khoản, chữ ký sai". Gộp lại làm mất khả năng chẩn đoán mà không tăng bảo mật.
- **Không** bỏ `timestamp` để "cho dễ tích hợp". `LECH_GIO_TOI_DA_MS` là lớp chống phát lại
  duy nhất hiện có; bỏ nó là nhận lại được mọi bản ghi cũ.

---

## 2. TLS — yêu cầu tối thiểu

| Hạng mục | Yêu cầu | Vì sao |
|---|---|---|
| Phiên bản | TLS 1.2 sàn, **TLS 1.3 ưu tiên** | 1.0/1.1 đã bị coi là hỏng |
| Bộ mã | chỉ nhóm AEAD (AES-GCM, ChaCha20-Poly1305) | CBC + MAC-then-encrypt là nguồn lỗi padding-oracle |
| Chứng chỉ | **DV qua ACME (Let's Encrypt)**, tự động gia hạn | không mua, không tự ký |
| Tên miền | **một** tên riêng cho webhook, ví dụ `hook.<miền>` | tách khỏi giao diện quản trị |
| HSTS | `max-age=31536000; includeSubDomains` **sau khi** đã chạy ổn | HSTS sai là tự khoá mình |
| OCSP | stapling bật | giảm lượt hỏi ra ngoài |
| Khoá riêng | **0600**, không nằm trong Git, không nằm trong ảnh Docker | cùng luật với khoá mã hoá |
| Cipher cho hãng | hãng cũ có thể chỉ hỗ trợ TLS 1.2 — **đo trước khi siết**, đừng đoán | J&T chưa xác nhận |

**Điều KHÔNG làm:** không dùng chứng chỉ tự ký cho đường webhook thật. Chữ ký tự ký làm mọi
lượt gọi thất bại ở tầng TLS mà thông báo lỗi phía hãng thường chỉ ghi "connection error" —
chẩn đoán sai hướng mất rất nhiều thời gian.

---

## 3. Reverse proxy — bản mẫu (CHƯA CHẠY)

Chọn **Caddy** làm bản mẫu vì ACME tự động là mặc định của nó, nên ít đường cấu hình sai hơn.
Nginx cũng được; cả hai đều **chưa được chạy lượt nào trên máy này**.

```caddy
# BẢN MẪU — CHƯA CHẠY. Không dùng nguyên văn mà không đọc mục 3.2.
hook.vi-du.example {
    encode zstd gzip

    # 3.1 Giới hạn thân yêu cầu Ở TẦNG PROXY, khớp với trần của ứng dụng.
    request_body {
        max_size 1MB
    }

    # 3.2 Chỉ nhận đúng một đường; mọi đường khác trả 404 KHÔNG chạm ứng dụng.
    @webhook path_regexp ^/api/v2/webhook/nhan/[A-Za-z0-9_-]+$
    handle @webhook {
        reverse_proxy 127.0.0.1:8897 {
            # Hạn giờ phải NGẮN HƠN hạn giờ của hãng, để bên gọi nhận lỗi rõ ràng
            # thay vì bị cắt lặng lẽ.
            transport http {
                read_timeout  15s
                write_timeout 15s
            }
            # Địa chỉ thật của bên gọi: PHẢI khai đúng, nếu không `gioi_han.dia_chi_that`
            # hoặc là bỏ qua toàn bộ X-Forwarded-For (mặc định, an toàn) hoặc là tin một
            # header do kẻ gọi tự đặt (nguy hiểm).
            header_up X-Real-IP {remote_host}
            header_up X-Forwarded-For {remote_host}
        }
    }
    handle {
        respond 404
    }

    log {
        output file /var/log/caddy/hook.log {
            roll_size 50MB
            roll_keep 10
        }
        format json
    }
}
```

### 3.1 Trần thân yêu cầu — ba lớp, ba con số KHÁC NHAU và phải khớp

| Lớp | Trần | Nguồn |
|---|---|---|
| Proxy | **1 MB** | bản mẫu trên |
| Ứng dụng — đường thường | **64 KB** | `server.py::GIOI_HAN_BODY_MAC_DINH` |
| Ứng dụng — đường upload | **20 MB** | `server.py::GIOI_HAN_BODY_IMPORT` (chỉ `/import`, `/doi-soat/nap`) |

Đường webhook **KHÔNG** được dùng trần 20 MB. Nó đi qua `GIOI_HAN_BODY_MAC_DINH` (64 KB) —
sự kiện hành trình thật nhỏ hơn nhiều. **Việc cần làm khi triển khai:** đo kích thước lớn nhất
của một gói callback J&T thật rồi đặt trần proxy bằng ~4× số đó, không đặt 1 MB theo thói quen.

### 3.2 Vì sao `handle` chặn mọi đường khác

Webhook là đường **vô danh**. Mỗi đường vô danh mở thêm là một bề mặt không có phiên bảo vệ.
Proxy chỉ nên chuyển tiếp đúng đường webhook ra Internet; giao diện quản trị (`/admin/`) và
API có phiên **không** được lộ ra cùng tên miền đó.

---

## 4. Hạn giờ và hành vi khi hãng chậm

| Tình huống | Hành vi ĐÚNG | Vì sao |
|---|---|---|
| Hãng gửi, hệ xử lý nhanh | `202` + `{"ket_qua":"da_nhan"}` | đã đo |
| Hãng gửi trùng `event_id` | `200` + `{"ket_qua":"da_nhan"}` | UNIQUE chặn, **không** nhân đôi tiền |
| Hãng chậm, proxy hết hạn giờ | proxy trả `504` — hãng **phải** thử lại | **KHÔNG** để ứng dụng tự hết hạn giờ rồi trả `202`: hãng tưởng đã nhận, sự kiện mất |
| Hệ quá tải | `429` + header `Retry-After` | hãng thử lại; `webhook.nhan` có trần riêng, rộng, để không chặn oan lưu lượng thật |
| Chữ ký sai | `401` | và **chỉ** đếm vào `webhook.chu_ky_sai` |
| Webhook lạ | `404` | không tiết lộ tài khoản nào tồn tại |

**Nguyên tắc:** ứng dụng phải trả lời **NHANH** rồi xử lý sau (đã đúng: `nhan_su_kien` ghi
`wh_su_kien` rồi trả `202`, worker xử lý nền). Việc cần làm khi triển khai là **đo** thời gian
trả lời ở tầng proxy dưới tải — hiện **chưa đo** (xem `DATABASE_CONCURRENCY_REPORT.md` §6:
"máy chủ HTTP thật dưới tải" nằm ngoài phạm vi).

---

## 5. Hạn chế theo địa chỉ IP — chỉ khi hãng CÔNG BỐ dải IP

| | |
|---|---|
| **J&T có công bố dải IP callback không?** | **CHƯA XÁC NHẬN.** `docs/JT_CAU_HOI_CHINH_THUC.md` có câu hỏi này; chưa có trả lời |
| **Có bật chặn theo IP không?** | **KHÔNG**, cho tới khi hãng trả lời bằng văn bản |
| **Vì sao không đoán** | Đoán sai dải IP = chặn sạch callback thật. Triệu chứng là "đơn không cập nhật trạng thái", không phải "webhook bị chặn" — chẩn đoán sai hướng |
| **Nếu hãng công bố** | cho phép danh sách trắng ở tầng proxy, **giữ nguyên** xác thực chữ ký phía sau (hai lớp, không thay nhau) |
| **Địa chỉ thật** | `gioi_han.dia_chi_that()` chỉ đọc `X-Forwarded-For` khi `VIP_HUB_PROXY_TIN_CAY` khai **đúng** địa chỉ proxy. Để **RỖNG** là mặc định đúng: không tin header nào. **Điền sai = mở đường cho kẻ gọi tự khai địa chỉ và lách sạch trần tần suất** |

---

## 6. Quan sát (observability) — cái gì phải nhìn thấy được

| Chỉ số | Nguồn | Ngưỡng cần báo động (đề xuất, chưa đo đường nền) |
|---|---|---|
| `wh_su_kien` ở trạng thái `moi` quá lâu | bảng `wh_su_kien` | > 5 phút ⇒ **worker chết hoặc kẹt** |
| `so_lan_thu > 0` | `wh_su_kien.so_lan_thu` | tăng đều ⇒ xử lý đang hỏng |
| `loi_cuoi` khác NULL | `wh_su_kien.loi_cuoi` | bất kỳ ⇒ đọc ngay |
| `401` trên `/webhook/nhan/*` | `webhook.chu_ky_sai` | > 10/phút cho một `webhook_ma` ⇒ **có người dò khoá** |
| `404` trên `/webhook/nhan/*` | log proxy | tăng vọt ⇒ có người quét `webhook_ma` |
| `429` | log proxy | tăng vọt ⇒ nghi lụt hoặc hãng thử lại dồn |
| Lệch giờ `timestamp` | `LECH_GIO_TOI_DA_MS` | nhiều lượt ⇒ đồng hồ máy chủ lệch, **sửa NTP trước khi nới ngưỡng** |

**Điều còn THIẾU và phải làm trước khi triển khai:** hiện **không có** dòng log JSON nào trên
đường yêu cầu HTTP — `server.py` chỉ gọi `quan_sat` cho `/suc-khoe`, `/san-sang`, `/metric`.
Nghĩa là `401`/`404`/`429` **không** để lại dấu vết có cấu trúc nào. Xem khiếm khuyết **P5d**
và đề xuất **P-G15-01** trong [`G15_INFRA.md`](G15_INFRA.md). **Đây là việc chặn trước khi
triển khai**, không phải việc "sau này".

---

## 7. Kiểm toán callback (audit) — cái gì phải giữ, giữ bao lâu

| Thứ | Đang giữ ở đâu | Đủ chưa |
|---|---|---|
| Thân yêu cầu NGUYÊN VẸN | `wh_su_kien.payload_tho` (**BLOB/BYTEA**) | **đủ** — đây là bằng chứng gốc, không phải bản chép lại |
| Header | `wh_su_kien.headers_json` | đủ |
| Mã sự kiện bền | `wh_su_kien.event_id` | đủ — khoá chống trùng |
| Ai/cái gì đã đổi trạng thái | `don_lich_su` + `wh_dau_vet` | đủ |
| Lượt replay | `webhook.yeu_cau_replay` + audit | đủ |
| **Bản ghi ở tầng proxy** | **chưa có** | **THIẾU** — phải bật `log` của proxy |
| **Thời hạn lưu** | **chưa khai** | **THIẾU** — `payload_tho` là dữ liệu cá nhân (tên, địa chỉ, SĐT người nhận) |

**Hai việc bắt buộc trước khi bật webhook thật:**
1. **Khai thời hạn lưu** cho `wh_su_kien.payload_tho` và một đường **xoá theo tuổi**. Không
   khai là giữ dữ liệu cá nhân vô thời hạn mà không ai quyết định.
2. **Không bao giờ ghi `payload_tho` vào log.** `quan_sat.che()` đã che theo *tên trường*
   (`mat_khau`, `token`…); một trường tên `body` chứa `bizContent` **sẽ không bị che**. Nếu
   nối log vào đường webhook, phải chủ động **bỏ** trường thân yêu cầu, đừng dựa vào bộ che.

---

## 8. Danh sách CHẶN (BLOCKED) — cái gì thiếu để I05 thành triển khai được

| # | Cái thiếu | Mã | Chặn cái gì |
|---|---|---|---|
| 1 | Quyền triển khai staging/VPS | **V-G11-01** | mọi thứ trong tài liệu này |
| 2 | Credentials sandbox J&T | **V-13906-05** | không có `webhook_ma` thật để hãng gọi vào |
| 3 | Quyền gọi API hãng thật | **V-G09-01** | đăng ký URL callback với hãng |
| 4 | J&T xác nhận có công bố dải IP không | `JT_CAU_HOI_CHINH_THUC.md` | mục 5 |
| 5 | Tên miền + DNS | — | ACME cần tên miền công khai |
| 6 | `server.py` nối log có cấu trúc | **P-G15-01** | mục 6 — không có dấu vết `401/404/429` |
| 7 | Đo thời gian trả lời dưới tải thật | **V-13914(b)** | mục 4 — chưa biết webhook chịu được bao nhiêu |

**Cho tới khi cả bảy dòng trên được giải, KHÔNG có cổng nào được mở, KHÔNG có tunnel nào được
dựng, KHÔNG có lượt deploy nào.** Tài liệu này là bản thiết kế để anh Thành duyệt, không phải
một lượt triển khai đã làm.
