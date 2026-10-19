> ## CẬP NHẬT SAU WAVE 8 (2026-10-19, HEAD tích hợp 19a9244)
>
> Báo cáo dưới đây là **hiện trạng trước khi AG-04 vá**. Lỗi chặn cứng đã được sửa:
> commit `7edf47b` (nhánh ag04-fix) thêm ô địa chỉ đường gửi/nhận và gửi
> `nguoi_gui_dia_chi`/`nguoi_nhan_dia_chi` trong payload Báo cước; merge vào
> `best/integration` tại `19a9244`. Playwright trên nhánh fix: **84/84 đạt** (trước 83/83).
> Vì vậy mục "Báo cước FAIL / thiếu Source.Address" bên dưới là **lịch sử**, không còn là
> blocker local.
>
> Kết luận mới: **LOCAL READY FOR OWNER UAT**, nhưng **CHƯA READY FOR PUBLIC OWNER
> ACCEPTANCE** vì VPS vẫn BLOCKED ở DNS `best-uat.viporder.vn`, chưa thêm site Caddy, chưa chạy
> service, chưa có credential BEST sandbox và chưa có public webhook. Không tuyên bố REAL PASS
> hoặc OWNER APPROVED.
>
# BEST EXPRESS — BÁO CÁO READINESS CHO OWNER ACCEPTANCE (AG-08)

**Ngày đo:** 2026-10-19 (khoảng 20:29–20:45 +07)
**Vai:** AG-08 — System Integration + Acceptance (wave 8)
**Nền:** `c04c6191f077a6225d54733cabde7e813b0bb886` (nhánh `ag08`)
**Phạm vi:** LOCAL + VPS PREP · **không** gửi credential BEST, **không** gọi API nghiệp vụ của hãng,
**không** tạo đơn, **không** push.
**Tệp báo cáo:** `docs/BEST_EXPRESS_READINESS_2026-10-19.md` (tệp duy nhất được tạo/sửa)

> ## KẾT LUẬN: CHƯA READY FOR OWNER ACCEPTANCE
>
> **Lý do chặn cứng:** nút **Báo cước BEST** trên bàn nghiệm thu `pages/best-uat.html`, khi đã
> chọn tài khoản và tick phê duyệt, **luôn trả HTTP 502 — `thiếu Source.Address`** với đúng
> payload mà giao diện gửi. Đây là lỗi cục bộ tái hiện được, không phải BLOCKED ngoài. Phần còn
> lại của bàn UAT local đã có bằng chứng PASS hoặc có cổng chặn đúng; VPS/public vẫn BLOCKED vì
> DNS/Caddy/service/credential.
>
> **REAL PASS = BLOCKED. OWNER APPROVED = PENDING.** Báo cáo này **không** tuyên bố hai mục đó.

| Câu hỏi | Kết luận | Vì sao |
|---|---|---|
| READY FOR OWNER ACCEPTANCE (LOCAL)? | **CHƯA** | Báo cước FAIL; các mục còn lại phần lớn PASS/có guard |
| READY CHO PUBLIC/VPS UAT? | **CHƯA** | Chưa có DNS, Caddy site, service/DB/admin, public webhook |
| REAL PASS? | **BLOCKED** | Thiếu credential BEST sandbox + phê duyệt bàn giao; chưa có callback thật |
| OWNER APPROVED? | **PENDING** | Chỉ Owner được ký; agent không được tự ghi |

**Cách đọc kết luận:** bàn UAT local **có thể dùng để Owner bắt đầu UAT** các mục URL, đăng nhập,
nhập credential, kiểm kết nối, tạo đơn, tracking, PDF, webhook local; nhưng **không thể chốt
acceptance** khi một mục bắt buộc (Báo cước) còn FAIL. Không có chuyện “PASS 5 cổng QA” thay thế
cho phép đo giao diện thật.

---

## 1. BẰNG CHỨNG CHẠY BỘ THỬ

| Bộ thử | Lệnh | Kết quả | Exit |
|---|---|---|---:|
| UAT HTTP BEST | `python3 app/thu/thu_best_uat.py` | `Ran 14 tests` · `OK` · 14/14 · 0 lỗi · 0 hỏng · 0 skip | **0** |
| E2E HTTP webhook BEST | `python3 app/thu/thu_best_e2e_http.py` | `Ran 59 tests` · `OK` · 59/59 · 0 lỗi · 0 hỏng · 0 skip | **0** |
| QA 10 cổng BEST | `python3 app/thu/thu_best_qa.py` | `PASS=5 · BLOCKED=2 · NOT TESTED=2 · PENDING=1` · FAIL=0 · REAL PASS=0 | **0** |
| QA 10 cổng — chế độ nghiệm thu | `python3 app/thu/thu_best_qa.py --nghiem-thu` | `NGHIỆM THU: HỎNG — còn cổng không PASS` | **1** |
| Hợp đồng BEST (đối chiếu) | `python3 app/thu/thu_best_hop_dong.py` | 35/35 | **0** |
| Webhook BEST (mock) | `python3 app/thu/thu_best_webhook.py` | 52/52 · `MOCK PASS` | **0** |
| Adapter BEST (mock) | `python3 app/thu/thu_best_adapter.py` | 118/118 | **0** |
| Auth/credential BEST (mock) | `python3 app/thu/thu_best_auth.py` | 47/47 | **0** |

- `git rev-parse HEAD` = `c04c6191f077a6225d54733cabde7e813b0bb886`; `git status --porcelain -uall`
  = **0 dòng** trước khi tạo báo cáo. Không sửa mã/test.
- `thu_best_qa.py --json` cho cùng tổng: `{"PASS":5,"FAIL":0,"BLOCKED":2,"NOT TESTED":2,"PENDING":1}`.
- `--nghiem-thu` exit 1 là **đúng thiết kế** khi còn cổng BLOCKED/PENDING; nó **không** chứng minh
  sản phẩm hỏng, nhưng cũng **không** được dùng để nói “đã nghiệm thu”.

---

## 2. BẰNG CHỨNG LIVE LOCAL (cùng commit)

Server local đang chạy tại `127.0.0.1:8897`; worktree vận hành ở cùng commit `c04c619` và 9 tệp
chính (`server.py`, `best_hop_dong.py`, `http_best.py`, `adapter_best.py`, `webhook_best.py`,
`best_uat.js`, `best-uat.html`, compose, Caddyfile) có SHA-256 **khớp** worktree `ag08`.

| Phép đo | Kết quả |
|---|---|
| `GET https://localhost:8897/pages/best-uat.html` | **200** `text/html` |
| `GET https://localhost:8897/admin/` | **200** `text/html` |
| `GET /api/v2/suc-khoe` | **200** |
| `GET /api/v2/san-sang` | **200** |
| `GET /api/v2/best/hop-dong` khi chưa đăng nhập | **401** |
| `POST /api/v2/auth/dang-nhap` bằng tài khoản demo local | **200**; phiên cookie dùng được |
| `GET /api/v2/best/trang-thai` sau đăng nhập | **200** |
| `co_phe_duyet_owner` / `co_ma_phe_duyet` | `true` / `true` (cờ phiên do script bật) |
| `production_ghi` | `false` |
| `public_base_url` | `""` — **chưa có URL webhook công khai** |
| Số tài khoản BEST trong dữ liệu UAT live | **0** — Owner sẽ tạo tài khoản sandbox |
| TLS local | tự ký `CN=localhost`, SAN `DNS:localhost, IP:127.0.0.1`, TLSv1.2 |
| Hiệu lực chứng chỉ local | `2026-10-19 12:50 UTC` → **`2026-10-21 12:50 UTC`** (2 ngày) |
| Quyền tệp tài khoản demo / khoá TLS | `TAI-KHOAN-DEMO.md` mode `600`; `best-uat.key` mode `600` |

**Lưu ý chứng chỉ:** script chỉ tạo chứng chỉ khi tệp **chưa có**, không tự gia hạn. Nếu Owner UAT
sau `2026-10-21 12:50 UTC`, phải xoá `/tmp/vip-best-uat-tls` rồi chạy lại script để sinh chứng chỉ
mới; nếu không trình duyệt sẽ từ chối.

---

## 3. MA TRẬN YÊU CẦU OWNER

Ký hiệu: **PASS** = đã đo trong lượt này; **FAIL** = đo được lỗi; **BLOCKED** = thiếu phụ thuộc
ngoài; **PENDING** = chỉ Owner.

| # | Yêu cầu Owner | Local | REAL/PUBLIC | Bằng chứng chính |
|---:|---|---|---|---|
| 1 | **URL** mở được | **PASS (LOCAL)** | **BLOCKED** | `best-uat.html` 200, `/admin/` 200, health/ready 200. VPS: `best-uat.viporder.vn` **NXDOMAIN**; `best-uat.viporder.com.vn` trỏ `103.159.50.70` (sai VPS); chưa có Caddy site/service. |
| 2 | **Đăng nhập hub** | **PASS (LOCAL)** | **BLOCKED** | Login demo 200; không cookie → `hop-dong` 401; có cookie → 200. VPS chưa có DB/admin nên chưa đăng nhập được. |
| 3 | **Nhập credential BEST** | **PASS (LOCAL, cơ chế)** | **BLOCKED** | UI có `Username`/`Password`/`ems-key`, chọn mock/sandbox, checkbox phê duyệt; JS chặn credential thật qua HTTP và chặn production; backend AES-256-GCM; UAT 14/14 + QA BEST-03 PASS; API không trả secret. Live đang **0 tài khoản** — Owner tự tạo bằng credential BEST cấp. |
| 4 | **Kiểm kết nối/đăng nhập BEST** | **PASS (LOCAL, guard)** | **BLOCKED** | `POST /api/v2/best/kiem-ket-noi` có route; mock bị 400; sandbox chưa xác nhận bị 403; response không có token/Bearer (UAT ca 06/07). Real login chưa chạy vì chưa có credential. |
| 5 | **Báo cước / COD / phí** | **FAIL** | **BLOCKED** | Đúng payload UI → **HTTP 502 `thiếu Source.Address`** (`blocked=false`, `ma=thieu-truong`). Xem mục 4. Real cũng chưa có credential; sau khi fix vẫn cần credential. |
| 6 | **Tạo đơn sandbox** | **PASS (LOCAL, builder + guard)** | **BLOCKED** | Payload UI dựng đủ **31 khoá** Order/Add (ServiceId 12491, District `" "`, Return mặc định người gửi); production bị khoá; cần `xac_nhan_that` + `TOI_DONG_Y_GOI_BEST_TEST`. Probe cùng setup: order đi qua builder, chỉ dừng ở ranh giới mạng (`AG08_NETWORK_BLOCKED`). Không tạo đơn thật. |
| 7 | **Tracking** | **PASS (LOCAL, builder/parser)** | **BLOCKED** | `POST /api/v2/best/tra-cuu`; `dung_query` giới hạn **10** mã; parser lấy phần tử cuối `traceLogs` theo `modified_at`, map 23 mã, `customer Cancel`→2; UI hiển thị status/hành trình. Chưa có waybill thật. |
| 8 | **PDF** | **PASS (LOCAL, route/SSRF)** | **BLOCKED** | UI có **Lấy URL PDF** + **Tải PDF (qua HTTPS)**; backend `in-pdf` tải qua allowlist, chặn HTTP/IP nội bộ/redirect, kiểm Content-Type PDF; QA BEST-06 PASS; UAT ca 13 chặn khi chưa phê duyệt. Chưa có cách vận đơn thật. |
| 9 | **Webhook** | **PASS (LOCAL E2E)** | **BLOCKED** | `thu_best_e2e_http.py` **59/59** + `thu_best_webhook.py` **52/52**: Bearer đúng → 200 + ACK, thiếu/sai → 401, chống trùng, tenant, sự kiện muộn, 605→606, 23 mã, không lộ secret. Live `public_base_url=""`; chưa có URL công khai/Bearer/BEST V9. |
| 10 | **COD / phí** | **PASS (LOCAL, hợp đồng)** | **BLOCKED** | UI quote/order có COD, khai giá; payload gửi `COD`/`CollectAmount`/`ProductPrice`; response chuẩn hoá `Cod`/`COD`, đọc `TotalFee`, `FreightFee`, `CODFee`, `InsuranceFee`, VAT; QA BEST-06 PASS (tách 3 loại phí). Chưa có phản hồi hãng thật trong lượt này. |
| 11 | **Lỗi cụ thể** | **PASS (LOCAL)** | **NOT TESTED (REAL)** | Lỗi trả `loi`, `blocked`, `http_status`, `endpoint`, TLS; không trả token/password/Bearer (UAT 02/04/06/07/08/13/14; E2E J01). Lỗi thật của hãng khi có credential chưa đo trong lượt này. |
| 12 | **Update / UpdateAddress / Cancel** (có trên bàn UAT) | **PASS (LOCAL, builder + guard)** | **BLOCKED** | UI dựng payload Update 9 trường, UpdateAddress 9 trường (1/2/3), Cancel 1 trường; production bị khoá; UAT ca 13 chặn khi chưa phê duyệt; hợp đồng 35/35. Chưa có waybill thật. |

---

## 4. LỖI CHẶN CỨNG — NÚT BÁO CƯỚC

### 4.1 Hiện tượng

Bấm **Báo cước BEST** trên `pages/best-uat.html` (mục 5), giao diện nhận:

```text
KHÔNG BÁO ĐƯỢC CƯỚC: thiếu Source.Address
```

### 4.2 Tái hiện ở mức HTTP

Dựng server tạm, tạo tài khoản BEST `sandbox`, bật phê duyệt phiên, **chặn mọi lời gọi mạng**
(`best_hop_dong._goi_co_token` bị stub), rồi gửi đúng payload mà `admin/best_uat.js` gửi:

```json
{
  "tai_khoan_id": 1,
  "xac_nhan_that": true,
  "don": {
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Bình Thạnh",
    "nguoi_gui_xa": "Phường 12",
    "nguoi_nhan_tinh": "Hồ Chí Minh", "nguoi_nhan_quan": "Tân Bình",
    "nguoi_nhan_xa": "Phường 10",
    "khoi_luong_gram": 120, "chieu_dai_mm": 100, "chieu_rong_mm": 100,
    "chieu_cao_mm": 100, "cod": 0, "gia_tri_khai": 0
  }
}
```

Kết quả đo:

```text
POST /api/v2/best/bao-gia  → HTTP 502
{"ok": false, "blocked": false, "loi": "thiếu Source.Address", "ma": "thieu-truong"}
```

Không có lời gọi mạng nào được thực hiện — lỗi xảy ra **trước** `_goi_co_token`.

### 4.3 Nguyên nhân gốc

1. Form báo cước `pages/best-uat.html:98-118` chỉ có tỉnh/quận/phường, cân, kích thước, COD,
   khai giá — **không có ô địa chỉ chi tiết** gửi/nhận.
2. `admin/best_uat.js:232-243` dựng payload báo cước **không có** `nguoi_gui_dia_chi` /
   `nguoi_nhan_dia_chi`.
3. `app/best_hop_dong.py:404-405` (`dung_estimate`) gọi `_nguoi_gui()` / `_nguoi_nhan()`;
   các hàm này đi qua `_dia_chi()` tại `app/best_hop_dong.py:189`, nơi **bắt buộc** `Address`.
4. Nhưng `dung_estimate()` chỉ gửi `City/District/Ward` (đúng hợp đồng EstimateFee), và **bỏ**
   address ở `src_city, src_dist, src_ward, _` / `dst_*`. Tức builder đòi một trường mà nó
   không hề gửi đi — lỗi validation nội bộ, không phải yêu cầu của hãng.

### 4.4 Đối chứng dương

Cùng payload, chỉ bổ sung `nguoi_gui_dia_chi` và `nguoi_nhan_dia_chi`:

```text
dung_estimate(...) → OK, 15 khoá:
COD, DestCity, DestDistrict, DestWard, DiscountCode, Height, Length, ProductPrice,
ServiceId, SourceCity, SourceDistrict, SourceWard, UserName, Weight, Width
```

Vậy phần parse/parse-response của báo cước **không hỏng**; lỗi nằm ở yêu cầu address thừa trong
builder và payload UI thiếu address.

### 4.5 Vì sao bộ thử xanh vẫn bỏ sót

- `thu_best_uat.py` ca 09 dùng fixture **có đủ địa chỉ** (`nguoi_gui_dia_chi: "1"`,
  `nguoi_nhan_dia_chi: "2"`), nên builder qua và chỉ kiểm 403; ca này **không** dùng đúng payload
  UI thật (thiếu address).
- `thu_best_hop_dong.py` và `thu_best_adapter.py` dùng fixture **có đủ địa chỉ**, nên builder qua.
- `thu_best_qa.py` BEST-06 kiểm tách 3 loại phí của nền tảng, **không** kiểm nút báo cước BEST.
- Playwright `best_express.spec.js` kiểm credential/kết nối, **không** submit form báo cước.

### 4.6 Ảnh hưởng và hướng sửa (chưa áp dụng — ngoài phạm vi AG-08)

- **Ảnh hưởng:** Owner không thể thực hiện bước “Báo cước” bắt buộc trong ma trận nghiệm thu;
  đây là lý do chính khiến kết luận tổng là **CHƯA READY**.
- **Hướng sửa đề xuất:** cho `dung_estimate()` dựng City/District/Ward **không bắt buộc Address**
  (ví dụ thêm tham số `bat_buoc_address=False` cho `_dia_chi`, hoặc dựng trực tiếp 3 trường địa
  chỉ), và thêm **regression test** dùng đúng payload UI (không address) → builder phải thành công.
  Có thể bổ sung ô địa chỉ vào form báo cước nếu muốn giữ ràng buộc address cho mục đích khác.
- **Sau khi sửa:** chạy lại `thu_best_uat.py`, `thu_best_e2e_http.py`, `thu_best_qa.py`, và thêm
  ca UI gửi form báo cước thật (mock API) để không tái diễn.

---

## 5. BLOCKER NGOÀI (không phải lỗi mã cục bộ)

| # | Blocker | Bằng chứng | Ai gỡ |
|---:|---|---|---|
| 1 | **Credential BEST sandbox** | Live UAT có **0 tài khoản BEST**; tài khoản test công khai trong DOCX đã đo bị khoá `[404]` (theo `docs/BEST_EXPRESS_DOCX_AUDIT.md`), không được dùng | BEST + Owner cấp qua kênh an toàn |
| 2 | **Phê duyệt bằng văn bản / bàn giao credential** | Cờ `VIP_BEST_OWNER_APPROVED=1` + mã phiên chỉ là cổng vận hành; không thay thế phê duyệt/phạm vi của Owner | Owner |
| 3 | **DNS public** | `best-uat.viporder.vn` **NXDOMAIN**; `best-uat.viporder.com.vn` → `103.159.50.70` (sai VPS); `cpn.viporder.vn` / `qua.viporder.vn` → `160.22.170.20` (mẫu đúng) | Owner/DNS admin tạo `A best-uat.viporder.vn → 160.22.170.20`, DNS-only |
| 4 | **Caddy site** | `docker exec vip-staging-caddy ... grep best-uat /etc/caddy/Caddyfile` → **NO_BEST_SITE**; block đã soạn nhưng chưa dán/reload | Owner duyệt; kỹ thuật backup + validate + reload |
| 5 | **Service/DB/admin trên VPS** | Không có container `vip-express-hub`; `127.0.0.1:18897` **NOT_LISTENING**; `/home/deploy/vip-express-hub/data` **rỗng**; chưa migrate/bootstrap | Owner duyệt; kỹ thuật chạy runbook |
| 6 | **Webhook công khai + Bearer + V9** | `public_base_url=""`; chưa có tunnel/reverse proxy công khai; chưa có Bearer BEST cấu hình; chưa gửi URL cho BEST V9 | Owner + BEST |
| 7 | **Production** | `production_ghi=false`; tạo/sửa/huỷ production bị khoá có chủ ý | Không mở ở lượt này; cần nghiệm thu riêng |
| 8 | **Backup/restore VPS** | Chưa cài cron backup; chưa diễn tập restore trên VPS | Owner duyệt; kỹ thuật chạy |
| 9 | **Hạn chứng chỉ local** | Cert local hết hạn `2026-10-21 12:50 UTC`; script không tự gia hạn | Xoá `/tmp/vip-best-uat-tls` + chạy lại script trước UAT |

---

## 6. VPS PREP — ĐÃ CÓ GÌ, CHƯA CÓ GÌ

Đo read-only qua SSH `deploy@160.22.170.20` (không thay đổi gì trên VPS):

| Hạng mục | Kết quả |
|---|---|
| Source trên VPS | `/home/deploy/vip-express-hub/src` có mặt; **SHA-256 9 tệp chính khớp** worktree `c04c619` |
| Image | `vip-express-hub:vps-c04c619` và `vip-express-hub:2026-10-19`, **232 MB**, build lúc ~20:23–20:25 |
| Compose | `docker compose config -q` → **exit 0**; `.env` mode `600` |
| Container | **Không có** container `vip-express-hub` |
| Cổng app | `127.0.0.1:18897` **chưa listen**; cổng 80/443 của Caddy mở; 18897 public **đóng** |
| Data | `/home/deploy/vip-express-hub/data` **rỗng** (chưa migrate/DB/khoá) |
| Caddy | Block `Caddyfile.best-uat` có trong source; **chưa có site** trong Caddyfile đang chạy |
| Backup/restore | `backup.sh` / `restore.sh` có; **chưa cài cron**, **chưa diễn tập** |
| Self-test image | Theo `docs/VPS_DEPLOYMENT_SURVEY.md` §4 đã healthy/restart healthy; **lượt này không chạy lại** |
| Công cụ kiểm tra sau deploy | `trien_khai/vps/kiem_tra.sh` có **lỗi tham số** — xem mục 7.2 |

**Kết luận VPS prep:** phần *chuẩn bị* (image + source + compose + Caddy block + runbook) đã có
bằng chứng; phần *triển khai public* **chưa xảy ra** và đang chờ Owner duyệt từng mục. Không được
gọi đây là “VPS UAT đã sẵn sàng”.

---

## 7. QA 10 CỔNG — ĐỌC ĐÚNG KẾT QUẢ

Chạy tại `c04c619`:

| Cổng | Kết quả | Ghi chú |
|---|---|---|
| BEST-01 Repository Baseline | **NOT TESTED** | Script ghim nền `cb23312dc702`; HEAD thực `c04c6191f077`; cây sạch, không phải cây bẩn. Cần cập nhật baseline. |
| BEST-02 API Contract | **PASS** | 8 endpoint · 23 mã · ServiceId 12491 · District `" "` · giới hạn 10/50; vẫn là đối chiếu hằng đã xác nhận, chưa gọi hãng. |
| BEST-03 Authentication | **PASS** | AES-256-GCM, nonce 12 byte, AAD sai hỏng, không lộ bản rõ; 2 cột secret tách rời. |
| BEST-04 Create/Update/Cancel | **PASS** | Chính sách không retry mù, timeout ⇒ UNKNOWN, idempotency; adapter BEST có mặt. |
| BEST-05 Webhook+Tracking | **BLOCKED (false negative do harness)** | Gate chỉ đọc `trang_thai_hang.BANG` (jt/vtp), **không** đọc `webhook_best.BANG_MA` / `best_hop_dong.BANG_MA` nơi có 23 mã BEST. E2E 59/59 và webhook 52/52 đã đo được 23 mã, 605→606, đến muộn, tenant. **Không phải lỗi sản phẩm.** |
| BEST-06 Fee+PDF | **PASS** | Tách 3 loại phí nền tảng; SSRF chặn HTTP/host lạ; **không phủ** nút báo cước BEST (xem mục 4.5). |
| BEST-07 Multi-tenant Security | **PASS** | 6/6 điều cấm trên hiện trạng; ghi chú “chưa có mã BEST” đã lỗi thời, cần chạy lại sau hợp nhất. |
| BEST-08 Frontend E2E | **NOT TESTED** | Lượt này không chạy `--giao-dien`; UI mới chỉ smoke HTTP + đọc mã, không chạy Chromium. |
| BEST-09 Real Account Connectivity | **BLOCKED** | Không credential, không endpoint đã xác minh, không phê duyệt; **không được ghi PASS**. |
| BEST-10 Owner Acceptance | **PENDING** | Không có bản ký Owner; agent không được tự điền. |

**Tổng:** PASS 5 · BLOCKED 2 · NOT TESTED 2 · PENDING 1 · **FAIL 0** · **REAL PASS 0**.
`--nghiem-thu` exit **1** vì còn cổng không PASS — đúng thiết kế, không phải bằng chứng sản phẩm
hỏng; nhưng cũng **không** được dùng để tuyên bố “đã nghiệm thu”.

### 7.1 Lỗi harness cần sửa (không sửa trong lượt này)

- `app/thu/thu_best_qa.py:613,618`: gate BEST-05 đọc `trang_thai_hang.BANG`; bảng BEST nằm ở
  `app/webhook_best.py:127` (`BANG_MA`) và `app/best_hop_dong.py:96` (`BANG_MA`). Vì vậy gate báo
  BLOCKED dù sản phẩm đã có bảng 23 mã. Sửa gate để đọc đúng nguồn, hoặc thêm adapter đăng ký
  `best` vào `trang_thai_hang.BANG`.
- `app/thu/thu_best_qa.py:149`: `NEN_HEAD = "cb23312dc702..."` — baseline cũ. Cập nhật theo commit
  được giao hoặc truyền HEAD qua tham số.
- `thu_best_qa.py` ghi chú BEST-07 “chưa có mã BEST” đã lỗi thời; cần cập nhật khi chạy lại.

### 7.2 Lỗi `kiem_tra.sh` (VPS post-deploy)

`trien_khai/vps/kiem_tra.sh:26` gọi sai thứ tự:

```sh
check "webhook thiếu Bearer bị chặn" 401 -X POST "$LOCAL/api/v2/webhook/nhan/khong-co" \
  -H 'Content-Type: application/json' -d '{}'
```

Hàm `check` nhận `ten mong url`, nên `url` bị gán thành `-X`; `POST` và URL thật rơi vào phần
`curl` opts. Kết quả: `curl` nhận `POST` như một URL, mã HTTP bị ghép/không khớp 401 ⇒ script báo
**✗ webhook** và exit 1 dù dịch vụ đúng. Cần đổi thành:

```sh
check "webhook thiếu Bearer bị chặn" 401 "$LOCAL/api/v2/webhook/nhan/khong-co" \
  -X POST -H 'Content-Type: application/json' -d '{}'
```

Đây là lỗi công cụ kiểm tra, không phải lỗi app; nhưng nếu không sửa, VPS sẽ bị báo FAIL giả sau
deploy.

### 7.3 Độ lệch tài liệu cần đồng bộ

- `docs/BEST_EXPRESS_QA.md` và `docs/BEST_EXPRESS_HTTP_E2E.md` là **snapshot theo HEAD cũ**
  (`cb23312` / `cced0f5`), ghi 3 PASS/6 BLOCKED và 57/57; hiện trạng `c04c619` là
  **5 PASS/2 BLOCKED/2 NOT TESTED/1 PENDING** và E2E **59/59**. Dùng bảng ở mục 7, không dùng
  số cũ để kết luận.
- `docs/BEST_EXPRESS_QA.md` còn ghi “21 trường” theo đề bài cũ; hợp đồng đã xác minh
  (`docs/BEST_EXPRESS_VERIFIED_CONTRACT.md` §3) có **31 khoá Order/Add luôn gửi** (34 tên gồm
  3 trường Cargo/khuyến mãi tuỳ chọn). Không phải lỗi sản phẩm nhưng phải đồng bộ khi nghiệm thu.
- `docs/BEST_EXPRESS_OWNER_UAT.md:56,159-160` nói Báo cước “HOẠT ĐỘNG”; kết quả đo ở mục 4 cho
  thấy **chưa đúng**. Phải sửa tài liệu sau khi fix mã, kèm ngày/commit.
- `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md:74` yêu cầu thu `TotalFee`/`CODFee`… từ mục 5; chỉ có
  thể đạt sau khi lỗi Báo cước được sửa và có credential.

---

## 8. ĐIỀU KIỆN ĐỂ CHUYỂN SANG READY

### 8.1 Việc kỹ thuật phải làm trước khi gọi Owner acceptance

- [ ] **Sửa lỗi Báo cước** (mục 4.6) + thêm regression test đúng payload UI; chạy lại 3 bộ thử.
- [ ] Sửa gate BEST-05 và baseline BEST-01 của `thu_best_qa.py` (hoặc ghi rõ ngoại lệ có kiểm
      chứng); chạy `--giao-dien` nếu cần BEST-08.
- [ ] Sửa `kiem_tra.sh` (mục 7.2) trước khi dùng cho VPS post-deploy.
- [ ] Cập nhật `docs/BEST_EXPRESS_OWNER_UAT.md:56,159-160` và
      `docs/BEST_EXPRESS_ACCEPTANCE_HANDOFF.md:74`: hiện đang nói Báo cước “HOẠT ĐỘNG”, trái với
      kết quả đo; sau khi sửa mã thì cập nhật lại kèm ngày/commit.
- [ ] Ghi rõ trong tài liệu: chứng chỉ local hết hạn sau 2 ngày; quy trình xoá/tạo lại.

### 8.2 Việc Owner/BEST phải làm

- [ ] Cấp **credential BEST sandbox** qua kênh an toàn (không chat/log/repo) và phê duyệt phạm vi
      UAT.
- [ ] Duyệt **DNS** `best-uat.viporder.vn → 160.22.170.20` (DNS-only) và **Caddy site** (backup,
      validate, reload; không restart).
- [ ] Duyệt **service VPS**: tạo data dir, migrate, bootstrap admin, `docker compose up -d` trên
      loopback `18897`.
- [ ] Cấp **Bearer webhook** do BEST cấu hình trên V9; cung cấp URL public sau khi có DNS/Caddy
      (hoặc tunnel) để điền `VIP_HUB_PUBLIC_BASE_URL`.
- [ ] Duyệt **backup cron** + lịch diễn tập restore trước khi dùng production.
- [ ] Chạy ma trận UAT trên URL đã chọn; lưu bằng chứng (không lưu secret); ký BEST-10.

### 8.3 Định nghĩa “READY” cho lượt này

Chỉ được ghi **READY FOR OWNER ACCEPTANCE** khi:
1. Tất cả mục LOCAL trong ma trận (trừ mục REAL/PUBLIC) **PASS** hoặc có ngoại lệ được Owner chấp
   nhận bằng văn bản; **không còn FAIL** như Báo cước.
2. Có đường public (DNS/Caddy/service hoặc tunnel) và webhook URL/Bearer nếu muốn nghiệm thu
   webhook thật.
3. Có credential sandbox + phê duyệt; các mục REAL chạy được hoặc được Owner tuyên bố ngoài phạm
   vi.
4. Báo cáo không có dòng nào ghi REAL PASS/OWNER APPROVED khi thiếu bằng chứng tương ứng.

---

## 9. GIỚI HẠN VÀ KHÔNG TUYÊN BỐ

- **Không REAL PASS, không OWNER APPROVED.** Mọi kết quả trong báo cáo là LOCAL/MOCK hoặc đọc
  trạng thái; chưa có lượt gọi API BEST có xác thực, chưa có callback BEST thật.
- **Không tạo đơn**, không gửi credential, không dùng tài khoản test công khai, không ghi
  production, không push.
- **Không sửa mã/test.** Chỉ tạo tệp báo cáo này.
- **Chưa chạy frontend E2E Chromium** trong lượt này (BEST-08 = NOT TESTED); UI mới được smoke
  qua HTTP + đọc mã. Nếu cần bằng chứng UI đầy đủ, chạy `python3 app/thu/thu_best_qa.py
  --giao-dien` (~1 phút, cần Chromium trong `node_modules`).
- **Không chạy lại** các phép đo thật đã có trong tài liệu trước: TLS BEST, EstimateFee thật, tài
  khoản test công khai bị khoá. Các số đó được trích dẫn từ `docs/BEST_EXPRESS_DOCX_AUDIT.md` /
  `docs/BEST_EXPRESS_VERIFIED_CONTRACT.md`, không phải số đo mới của lượt này.
- **Không chạy lại self-test image trên VPS**; chỉ xác minh image tồn tại, source hash khớp,
  compose config hợp lệ. Self-test healthy/restart là bằng chứng của tài liệu VPS.
- Có một lượt đọc `GET /api/v2/best/trang-thai?tls=1` trên server local để kiểm tra UI; thao tác
  này chỉ mở TLS tới host BEST để đọc chứng chỉ, **không gửi credential, không gọi endpoint
  nghiệp vụ, không tạo đơn**. Báo cáo không dùng kết quả TLS đó làm REAL PASS.
- Dữ liệu UAT local nằm ở `/tmp/vip-best-uat-data`; nếu máy khởi động lại, phải chạy lại
  `trien_khai/best_nghiem_thu.sh` và tạo lại tài khoản/phiên.

---

## 10. PHỤ LỤC — LỆNH TÁI LẬP

```sh
# 1) Ba bộ bắt buộc
python3 app/thu/thu_best_uat.py
python3 app/thu/thu_best_e2e_http.py
python3 app/thu/thu_best_qa.py
python3 app/thu/thu_best_qa.py --json
python3 app/thu/thu_best_qa.py --nghiem-thu   # exit 1 khi còn BLOCKED/PENDING

# 2) Đối chiếu hợp đồng/webhook/adapter/auth
python3 app/thu/thu_best_hop_dong.py
python3 app/thu/thu_best_webhook.py
python3 app/thu/thu_best_adapter.py
python3 app/thu/thu_best_auth.py

# 3) Live local (chứng chỉ tự ký — dùng --cacert, không dùng -k cho dữ liệu thật)
CA=/tmp/vip-best-uat-tls/best-uat.crt
curl -sS -o /dev/null -w '%{http_code}\n' --cacert "$CA" https://localhost:8897/pages/best-uat.html
curl -sS -o /dev/null -w '%{http_code}\n' --cacert "$CA" https://localhost:8897/api/v2/best/hop-dong   # 401
```

Tái hiện lỗi báo cước ở mức builder (không gọi mạng):

```sh
python3 - <<'PY'
import sys, os, tempfile
sys.path.insert(0, "app")
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="ag08-estimate-"))
import best_hop_dong as b
don = {
  "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Bình Thạnh",
  "nguoi_gui_xa": "Phường 12",
  "nguoi_nhan_tinh": "Hồ Chí Minh", "nguoi_nhan_quan": "Tân Bình",
  "nguoi_nhan_xa": "Phường 10",
  "khoi_luong_gram": 120, "chieu_dai_mm": 100, "chieu_rong_mm": 100,
  "chieu_cao_mm": 100, "cod": 0, "gia_tri_khai": 0,
}
try:
    b.dung_estimate(don)
    print("KHÔNG TÁI HIỆN — builder đã chấp nhận payload UI")
except Exception as e:
    print(type(e).__name__, e)   # LoiHopDong thiếu Source.Address
PY
```

Kiểm tra VPS read-only:

```sh
ssh deploy@160.22.170.20 'docker images | grep vip-express-hub; \
  docker ps -a --filter name=vip-express-hub; \
  ls -la /home/deploy/vip-express-hub/data; \
  docker exec vip-staging-caddy sh -c "grep -n best-uat /etc/caddy/Caddyfile || echo NO_BEST_SITE"'
```

---

## 11. TỆP VÀ COMMIT

- **Tệp thay đổi:** chỉ `docs/BEST_EXPRESS_READINESS_2026-10-19.md`.
- **Không sửa:** `app/**`, `admin/**`, `pages/**`, `trien_khai/**`, test, tài liệu khác.
- **Commit:** `git log -1 --format=%H -- docs/BEST_EXPRESS_READINESS_2026-10-19.md`
  (hash thực được gửi kèm `worker_done`).

---

*Báo cáo do AG-08 lập trong wave 8, phạm vi LOCAL + VPS PREP. Không có REAL PASS, không có OWNER
APPROVED, không có thao tác production.*
