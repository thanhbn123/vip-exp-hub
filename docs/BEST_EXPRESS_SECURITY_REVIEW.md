# BEST EXPRESS — SECURITY REVIEW: AUTH + CREDENTIAL (AGENT B2)

- **Dự án:** VIP EXPRESS HUB
- **Nhánh:** `b2-auth` · **HEAD:** `cb23312dc702a6a1bf51e9cb53c7397770cd9637` (= `best/integration @ cb23312`)
- **Ngày đo:** 2026-10-19 (giờ máy: +07)
- **Phạm vi ghi:** `app/xac_thuc_best.py` (mới) · `app/thu/thu_best_auth.py` (mới) · `docs/BEST_EXPRESS_SECURITY_REVIEW.md` (mới)
- **Trạng thái bằng chứng:** **MOCK PASS** — **KHÔNG PHẢI REAL PASS**
- **REAL PASS:** **CHƯA THỰC HIỆN — BLOCKED** (không được phép gọi BEST; không có credential thật; tài liệu Google Docs không đọc được trong môi trường local-only)

> Câu quan trọng nhất trong báo cáo này: mọi con số dưới đây đo một **stub loopback 127.0.0.1**.
> Không có lời gọi nào — kể cả test host/sandbox — tới BEST Express trong lượt làm việc này.
> MOCK PASS không chứng minh tương thích với BEST thật. Hai kết quả là hai kết quả khác nhau.

---

## 1. TÓM TẮT ĐIỀU HÀNH

1. Viết `app/xac_thuc_best.py`: đăng nhập BEST bằng `POST /User/Login` `{Username, Password}` → `{token}`,
   token hạn **30 ngày**, cache theo `(tenant, tài khoản)`, chỉ làm mới khi hết hạn / bị 401 / cache hỏng,
   có khóa liên tiến trình chống đồng loạt re-login.
2. Tách **hai lớp secret không dùng lẫn**: (A) credential đăng nhập BEST; (B) Bearer token nhận webhook.
   Hai tệp kho riêng, hai bộ hàm riêng, trường `loai` nằm **trong bản mã** để chặn dùng lẫn.
3. Lưu trữ bằng `bao_mat.ma_hoa_cred/giai_ma_cred` (AES-256-GCM, `v3$<key_id>$...`, AAD `cred:<tenant>:BEST`).
   Không plaintext password, không token trong log/response/audit, không hardcode token.
4. Bộ thử MOCK 47 ca, **0 bỏ qua, 0 hỏng**, exit 0 (chạy 3 lần liên tiếp đều 0). Quét thật: không thấy
   plaintext trong toàn bộ thư mục dữ liệu; không thấy token/password trong log + response + audit.
   Mỗi ca phủ định đều có **đối chứng dương**.
5. **Còn lại / BLOCKED:** xác minh với BEST thật, URL/host thật, header webhook thật, schema lỗi,
   refresh endpoint (không đoán), chứng chỉ/rate limit. Không có REAL PASS.

---

## 2. PHẠM VI VÀ RÀNG BUỘC ĐÃ TUÂN THỦ

| Ràng buộc | Cách tuân thủ | Bằng chứng |
|---|---|---|
| Local only, không push/deploy/production | Không chạy git push/commit, không deploy | `git status` chỉ có 3 tệp mới; HEAD vẫn `cb23312` |
| Không gọi API BEST, kể cả test host | Mặc định **không có transport**; mọi ca thử dùng stub `127.0.0.1` | `Test06.test_07`: chưa cấu hình ⇒ `CHUA_CAU_HINH_TRANSPORT`, 0 request |
| Không tạo đơn thật, không credential thật | Module chỉ đăng nhập/webhook; test sinh secret ngẫu nhiên | Không có mã tạo đơn; canary ngẫu nhiên mỗi lần chạy |
| Không xóa dữ liệu, không reset DB | Không xóa bản ghi nghiệp vụ; test dùng thư mục tạm | `huy_token` chỉ xóa cache token; test DB là temp |
| Không phá adapter hiện có | Không sửa `adapter_jt.py`, `adapter_vtp.py`, `adapter.py` | `git status` không có các tệp này |
| Không đổi kiến trúc multi-tenant | Mọi hàm bắt buộc `tenant_id`; thiếu ⇒ DENY trước khi chạm đĩa/mạng | `Test03.test_02`: 6 dạng tenant xấu ⇒ `THIEU_TENANT`, 0 request |
| Không đoán endpoint/schema | Chỉ dùng 4 dữ kiện đã xác nhận; mọi thứ khác ghi CHƯA KIỂM CHỨNG (§3) | §3 |
| Không ghi secret vào log/audit/response | Log/audit chỉ có mã + hash tham chiếu; status không có token | `Test02`: quét + đối chứng dương |
| Không hạ TLS, không tắt xác minh | `ssl.create_default_context()`; HTTP chỉ loopback + cờ test | `Test06.test_02`: `CERT_REQUIRED`, `check_hostname=True`; `Test06.test_11`: **handshake thật** với cert tự ký bị `KHONG_KET_NOI_DUOC`, 0 request |
| Không sửa `bao_mat.py`/`server.py`/`webhook.py`/`adapter_best.py` | Chỉ đọc/gọi hợp đồng | Danh sách tệp thay đổi ở §12 |

---

## 3. ĐẶC TẢ ĐÃ XÁC NHẬN vs CHƯA KIỂM CHỨNG

### 3.1 Đã xác nhận (chỉ dùng đúng những dòng này)

| Hạng mục | Giá trị đã xác nhận | Nơi dùng |
|---|---|---|
| Endpoint đăng nhập | `POST /User/Login` | `TransportDangNhapHTTPS`, hằng `DUONG_DAN_DANG_NHAP` |
| Thân yêu cầu | `{"Username": ..., "Password": ...}` | `TransportDangNhapHTTPS.dang_nhap` |
| Phản hồi thành công | `{"token": ...}` | Bóc đúng khóa `token`; không đọc trường khác |
| Hạn token | **30 ngày** | `HAN_TOKEN_GIAY = 30*24*60*60` |

### 3.2 CHƯA KIỂM CHỨNG — không được dùng như sự thật

Tài liệu API BEST là **Google Docs**. Trong repo không tìm thấy URL Google Docs nào
(không có `docs.google.com` trong cây làm việc) và đề bài không cung cấp URL. Môi trường là
local-only, không mở tài liệu. Vì vậy **toàn bộ mục dưới đây là CHƯA KIỂM CHỨNG**, không phải
"đã đọc tài liệu":

| # | Hạng mục | Trạng thái | Hệ quả trong mã |
|---|---|---|---|
| U1 | Host/domain API BEST | **CHƯA KIỂM CHỨNG** | Không hardcode host. `TransportDangNhapHTTPS` bắt buộc URL HTTPS tường minh, không đọc env |
| U2 | Header phụ (Content-Type, Accept, User-Agent, tenant/partner id...) | **CHƯA KIỂM CHỨNG** | Chỉ gửi JSON + Accept + UA. Nếu BEST đòi thêm header, REAL sẽ hỏng — chưa biết |
| U3 | Bảng chữ/độ dài token | **CHƯA KIỂM CHỨNG** | Chỉ nhận ASCII in được, không khoảng trắng, 1..8192 byte (an toàn header), không suy đoán thêm |
| U4 | Nghĩa "30 ngày": từ lúc phát hành, từ lúc nhận, hay trượt? | **CHƯA KIỂM CHỨNG** | Tính 30 ngày từ lúc NHẬN token; không refresh sớm; 401 ⇒ `lam_moi_token` có kiểm soát |
| U5 | Server có trả trường hạn token không? | **CHƯA KIỂM CHỨNG** | Bỏ qua mọi trường ngoài `token`; không đoán tên trường |
| U6 | Endpoint refresh token | **KHÔNG ĐOÁN** | Không gọi endpoint lạ; hết hạn ⇒ đăng nhập lại đúng `/User/Login` |
| U7 | Schema lỗi / mã lỗi nghiệp vụ | **CHƯA KIỂM CHỨNG** | Chỉ dùng HTTP status; **không đọc thân lỗi** (tránh echo secret) |
| U8 | Rate limit / 429 / Retry-After | **CHƯA KIỂM CHỨNG** | Không tự retry vòng lặp; trả lỗi mã hoá để bên gọi quyết định |
| U9 | Tên header + định dạng webhook Bearer | **CHƯA KIỂM CHỨNG** | Nhận **giá trị** header; chấp nhận `Bearer <token>` không phân biệt hoa/thường. Tên header do B3 quyết định |
| U10 | Chữ ký/timestamp/chống replay của webhook | **NGOÀI PHẠM VI B2** | B3 xử lý; B2 chỉ xác thực Bearer |
| U11 | BEST có thu hồi/xoay webhook Bearer không? | **CHƯA KIỂM CHỨNG** | Có hàm ghi đè; không có endpoint thu hồi |
| U12 | Password có cho phép Unicode/khoảng trắng? | **CHƯA KIỂM CHỨNG** | Không thu hẹp bảng chữ: chỉ chặn rỗng/quá 1024/NUL. Username chặn ký tự điều khiển |
| U13 | Chứng chỉ/CA của BEST, IP allowlist | **CHƯA KIỂM CHỨNG** với BEST thật | Dùng CA mặc định của hệ điều hành; không tắt xác minh, không pin cert. Đã đo phía client: cert tự ký bị từ chối (`Test06.test_11`); đường HTTPS hợp lệ với CA tin cậy CHƯA đo |
| U14 | Múi giờ/đồng hồ server | **CHƯA KIỂM CHỨNG** | Dùng đồng hồ máy; nếu lùi > 300 giây so với lúc phát hành ⇒ coi token không hợp lệ, làm mới |

**Kết luận §3:** chỉ 4 dòng ở §3.1 là đặc tả đã xác nhận. Mọi hành vi khác của BEST **chưa được
đo**. Báo cáo này không được dùng để nói "tương thích BEST".

---

## 4. HAI LỚP SECRET — TÁCH TÊN, TÁCH KHO, TÁCH HÀM

| | **LỚP A — Credential đăng nhập** | **LỚP B — Bearer nhận webhook** |
|---|---|---|
| Bản chất | `Username` + `Password` để gọi `/User/Login` | Token BEST gửi kèm webhook để hub xác thực |
| Hằng loại | `LOAI_CREDENTIAL = "credential_dang_nhap_best"` | `LOAI_WEBHOOK = "bearer_webhook_best"` |
| Hàm ghi | `luu_credential_dang_nhap()` | `luu_bearer_webhook()` |
| Hàm đọc/kiểm | `_doc_credential()` (nội bộ) · `trang_thai_credential()` (không secret) | `kiem_bearer_webhook()` · `trang_thai_bearer_webhook()` |
| Tệp kho | `best_auth/credential_dang_nhap.enc.json` | `best_auth/bearer_webhook.enc.json` |
| AAD | `cred:<tenant_id>:BEST` | `cred:<tenant_id>:BEST` + `loai` trong bản mã + tệp riêng |
| Vòng đời | Đến khi tenant đổi credential | Đến khi tenant đổi Bearer |
| Ai dùng | B1/adapter/provisioning | B3/webhook route |
| Trả ra ngoài? | **KHÔNG** (password không bao giờ ra khỏi module) | **KHÔNG** (chỉ trả `True/False` + mã lý do) |

**Vì sao lớp B cũng dùng AAD `cred:<tenant>:BEST` thay vì `ma_hoa_wh`?**
Yêu cầu của đề bài là AAD buộc **tenant + hãng**. `ma_hoa_wh` chỉ buộc `webhook_ma` — nếu hai tenant
lỡ trùng `webhook_ma`, AAD không tách được tenant. Dùng `ma_hoa_cred` giữ đúng ràng buộc tenant+hãng;
việc tách lớp được bảo vệ bằng **tệp riêng** + **`loai` nằm trong bản mã đã xác thực**. Chép bản mã
lớp B sang kho lớp A (hoặc ngược lại) sẽ giải mã được nhưng bị `SAI_LOP_SECRET` từ chối — có ca thử.

**Token truy cập là lớp dẫn xuất, không phải lớp B:**
`token_truy_cap_best` nằm ở tệp thứ ba `token_truy_cap.enc.json`. Nó sinh ra từ lớp A, sống 30 ngày,
được cache. Gọi nó là "lớp B" sẽ là mô tả sai và dễ dẫn tới dùng lẫn token webhook với token đăng nhập.

---

## 5. LƯU TRỮ VÀ MÃ HÓA

### 5.1 Định dạng

Mỗi tệp kho:

```json
{
  "phien_ban": 1,
  "loai": "credential_dang_nhap_best",
  "ban_ghi": {
    "<tenant_id>": {
      "<tai_khoan>": {
        "ban_ma": "v3$<key_id>$<nonce_hex>$<ciphertext_hex>",
        "cap_nhat_luc": 1792378946.19,
        "phien_ban": 1
      }
    }
  }
}
```

Bản rõ **bên trong** bản mã (không bao giờ ghi trực tiếp):

- Lớp A: `{loai, tenant_id, tai_khoan, username, password, phien_ban}`
- Lớp B: `{loai, tenant_id, tai_khoan, webhook_ma, bearer, phien_ban}`
- Token: `{loai, tenant_id, tai_khoan, token, phat_hanh_luc, het_han_luc, credential_bam, nguon, phien_ban}`

`credential_bam = sha256(bản mã credential)[:32]` — buộc token cache vào **đúng phiên bản credential**.
Đổi credential ⇒ token cũ không còn khớp, kể cả khi lượt vô hiệu cache bị lỡ.

### 5.2 Thuộc tính an toàn

| Thuộc tính | Cách làm |
|---|---|
| Mã hóa | `bao_mat.ma_hoa_cred` / `giai_ma_cred` — AES-256-GCM, `v3$<key_id>$...`, AAD `cred:<tenant>:BEST` |
| Không plaintext | Username/password/token/bearer chỉ nằm trong bản mã; test quét nhị phân toàn thư mục |
| Quyền | Thư mục `best_auth/` 0700; tệp kho + khóa 0600 (tự `chmod` nếu lệch) |
| Ghi nguyên tử | Tệp tạm cùng thư mục → `fsync` → `os.replace`; người đọc không thấy bản ghi nửa vời |
| Chống symlink | Kiểm tra `islink`/`S_ISREG`; khóa tệp mở bằng `O_NOFOLLOW` |
| Chống phình bộ nhớ | Trần tệp kho 1 MiB; trần phản hồi login 64 KiB; trần token 8192 byte |
| Khóa ghi | `flock` toàn cục `kho.lock` (trong tiến trình: `RLock`) |
| Khóa làm mới | `flock` theo `(tenant, tài khoản)` + `threading.Lock`; giữ **qua cả lượt gọi mạng** |
| Không đổi schema | Không tạo bảng, không sửa `migrate.py`/`csdl.py`; kho là tệp riêng dưới `VIP_HUB_DATA` |

### 5.3 Vì sao không ghi vào `carrier_accounts`?

- `migrate.py`/`csdl.py` thuộc AG-00; B2 không được sửa schema.
- `adapter_best.py` (B1) chưa tồn tại ở mốc `cb23312`; ràng buộc cứng vào bảng sẽ khóa B1 vào một
  thiết kế chưa chốt.
- Kho tệp riêng cho phép B2 hoàn thành đúng phạm vi, không đụng dữ liệu hãng hiện có, và vẫn dùng
  đúng hợp đồng mã hóa của dự án. Giao diện cho B1 là `lay_token` — không cần B1 đọc password.

**Hệ quả tích hợp:** ba tệp này là **nguồn duy nhất** cho credential/token/webhook Bearer của BEST
trong phạm vi B2. Module KHÔNG đọc `carrier_accounts`; B1 không được tự lưu credential BEST vào một
bảng/kho khác rồi mong module đọc thấy. Nếu sau này cần hợp nhất với `carrier_accounts`, phải có
một dispatch riêng của AG-00 + migration có sao lưu, không tự làm trong B2.

---

## 6. VÒNG ĐỜI TOKEN — CÓ KIỂM SOÁT

### 6.1 Trạng thái

```
CHƯA CÓ TOKEN
   │ lay_token: giải mã credential trước (thiếu ⇒ THIEU_CREDENTIAL, KHÔNG gọi mạng)
   ▼
ĐỌC CACHE ── còn hạn + đúng credential_bam ──► TRẢ TOKEN (không gọi mạng)
   │ hết hạn / cache hỏng / sai credential_bam / đồng hồ lùi
   ▼
KHÓA (tenant, tài khoản) [thread + flock]
   │ đọc lại cache: worker khác vừa làm mới ⇒ dùng luôn, không đăng nhập
   ▼
POST /User/Login  (một lần) ──► token ──► kiểm tra định dạng
   │
   ├─ credential đổi giữa chừng ⇒ TỪ CHỐI token vừa lấy (`CREDENTIAL_DA_DOI_KHONG_LUU`);
   │  không trả token của credential cũ, lượt sau dùng credential mới
   └─ credential không đổi ⇒ ghi cache (AES-GCM), hạn = now + 30 ngày
```

### 6.2 Làm mới khi bị 401 — không phải mỗi request

B1 gọi `lam_moi_token(tenant, tài khoản, token_cu=<token vừa bị 401>)`:

- Nếu cache đã có token **khác** `token_cu` và còn hạn ⇒ trả token đó, **không đăng nhập lại**
  (chống bão 401 / nhiều worker).
- Nếu cache đúng bằng `token_cu` ⇒ **xóa cache TRƯỚC** rồi mới thử đăng nhập. Nếu lượt đăng nhập
  hỏng, cache rỗng chứ không tiếp tục phục vụ token vừa bị 401 (nếu giữ, `lay_token` sẽ trả token
  chết tới 30 ngày).
- Nếu không ⇒ đăng nhập lại một lần dưới khóa.

`lay_token` **không** tự thử lại khi mạng lỗi. Không có vòng retry ẩn — tránh biến một lỗi BEST
thành hàng loạt lượt đăng nhập.

### 6.3 Xoay credential

`luu_credential_dang_nhap` ghi credential mới và **vô hiệu token cache trong cùng lượt khóa ghi**.
Ngoài ra token cache còn mang `credential_bam`, nên kể cả khi bước vô hiệu bị lỡ, token cũ vẫn bị
coi là không hợp lệ. Đây là hai lớp bảo vệ độc lập cho cùng một rủi ro.

Nếu credential đổi **đúng giữa lúc gọi mạng**, token vừa lấy thuộc credential cũ. Module không
cache và cũng **không trả** token đó: `_cache_token_sau_dang_nhap` ném
`CREDENTIAL_DA_DOI_KHONG_LUU`. Lượt sau đọc credential mới và đăng nhập lại. Đây là fail-closed
có chủ đích: thà một lượt lỗi còn hơn dùng token của credential đã bị thay.

### 6.4 Bằng chứng đồng thời (MOCK)

| Phép đo | Kết quả | Ca thử |
|---|---|---|
| 16 thread cùng lúc hết hạn, stub trễ 0,20 s | Tổng lượt đăng nhập = 2 (1 ban đầu + **đúng 1** làm mới); 16 thread nhận cùng token | `Test05.test_02` |
| 3 tiến trình cùng lúc hết hạn, stub trễ 0,40 s | Tổng lượt đăng nhập = **1**; cả 3 tiến trình thoát 0, không in token | `Test05.test_03` |
| 5 lượt gọi liên tiếp tại đúng mốc hết hạn | **1** lượt làm mới | `Test05.test_07` |
| Hai lượt `lam_moi_token` với cùng `token_cu` (mô phỏng bão 401) | Lượt thứ hai dùng token của worker trước, **0** đăng nhập thêm | `Test05.test_04` |

**Giới hạn:** `flock` chỉ đáng tin trên hệ tệp cục bộ. Nếu `VIP_HUB_DATA` nằm trên NFS/SMB, cơ chế
khóa liên tiến trình không được bảo đảm. Chưa đo trên NFS — ghi nhận là rủi ro, không phải PASS.

---

## 7. MA TRẬN TỪ CHỐI (DENY RÕ RÀNG, KHÔNG ĐOÁN)

| Mã | Khi nào | Có gọi mạng? |
|---|---|---|
| `THIEU_TENANT` | `tenant_id` None/rỗng/khoảng trắng/sai kiểu/quá dài/ký tự điều khiển | **KHÔNG** |
| `THIEU_TAI_KHOAN` | mã tài khoản tương tự | **KHÔNG** |
| `THIEU_CREDENTIAL` | Chưa lưu credential cho đúng `(tenant, tài khoản)` | **KHÔNG** |
| `CREDENTIAL_KHONG_HOP_LE` | Username rỗng/sai kiểu/ký tự điều khiển; Password rỗng/sai kiểu/quá dài/NUL | **KHÔNG** |
| `CREDENTIAL_DA_DOI_KHONG_LUU` | Credential đổi giữa lượt đăng nhập — token của credential cũ bị bỏ | Có (đã cố) |
| `KHONG_DOC_DUOC_CREDENTIAL` | Sai khóa/AAD, bản mã bị sửa, chép từ tenant khác | **KHÔNG** |
| `SAI_LOP_SECRET` | Bản mã lớp B nằm trong kho lớp A (hoặc ngược lại) | **KHÔNG** |
| `KHO_HONG` | Tệp kho sai JSON/cấu trúc; **không ghi đè** | **KHÔNG** |
| `KHO_KHONG_AN_TOAN` | Symlink/không phải tệp thường/không tạo được thư mục kho | **KHÔNG** |
| `KHOA_KHONG_HO_TRO` | `flock` không dùng được (ví dụ hệ tệp mạng) | **KHÔNG** |
| `CHUA_CAU_HINH_TRANSPORT` | Chưa đặt transport tường minh | **KHÔNG** |
| `HTTP_KHONG_DUOC_PHEP` | HTTP tới host không loopback, hoặc loopback nhưng chưa bật cờ test | **KHÔNG** |
| `URL_KHONG_HOP_LE` | URL sai scheme/có userinfo/query/path/port sai | **KHÔNG** |
| `DANG_NHAP_THAT_BAI` | HTTP 4xx/5xx (chỉ mã status) | Có (đã cố) |
| `KHONG_KET_NOI_DUOC` | Lỗi mạng/TLS/timeout | Có (đã cố) |
| `PHAN_HOI_KHONG_HOP_LE` | JSON sai/thiếu `token` | Có (đã cố) |
| `TOKEN_KHONG_HOP_LE` | `token` rỗng/sai kiểu/chứa ký tự không an toàn | Có (đã cố) |
| `THIEU_HEADER` / `SAI_DINH_DANG_BEARER` / `BEARER_KHONG_KHOP` | Webhook không hợp lệ | **KHÔNG** (chỉ đọc kho) |
| `KHONG_CO_BEARER_DA_LUU` | Tenant/tài khoản chưa cấu hình Bearer | **KHÔNG** |

---

## 8. KẾT QUẢ ĐO MOCK — BẢNG 5 MỤC

**Lệnh đo (chạy từ gốc repo):**

```sh
python3 -B app/thu/thu_best_auth.py
```

**Kết quả thật (3 lần liên tiếp):**

| Lần | Exit code | Số ca | Bỏ qua | Hỏng | Thời gian |
|---|---|---|---|---|---|
| 1 | **0** | **47** | **0** | **0** | 3,782 s |
| 2 | **0** | **47** | **0** | **0** | 3,851 s |
| 3 | **0** | **47** | **0** | **0** | 3,779 s |

Dòng cuối chương trình in: `MOCK PASS — KHÔNG PHẢI REAL PASS`.

### 8.1 Bảng 5 mục bắt buộc

| # | Yêu cầu | Cách đo (thật) | Kết quả MOCK | Đối chứng dương | Ca thử |
|---|---|---|---|---|---|
| (a) | Không plaintext trong CSDL/kho | Quét **nhị phân** mọi tệp dưới `VIP_HUB_DATA` (gồm `hub.db`, `-wal`, `-shm`, tệp kho) tìm password + username | **KHÔNG THẤY** (None) | Cấy tệp plaintext vào chính thư mục dữ liệu ⇒ phép quét **tìm thấy đúng tệp**, rồi xóa | `Test01.test_01` |
| (b) | Token/password không trong log + response + audit | Ghi log thật ở DEBUG trong suốt vòng đời; serialize mọi hàm mô tả; đọc bảng `audit` thật trong SQLite | **KHÔNG THẤY** token/password/username | • Ghi canary khác vào logger ⇒ bắt được<br>• Chèn canary khác vào `audit` ⇒ bắt được<br>• Dict chứa token ⇒ phép quét bắt được | `Test02.test_01..05` |
| (c) | Hết hạn ⇒ làm mới đúng 1 lần | Đếm số request `/User/Login` ở stub; đo tại `t0+30d-1`, `t0+30d`; 16 thread; 3 tiến trình | **ĐÚNG 1** lượt làm mới mỗi lượt hết hạn; 16 thread = 1; 3 tiến trình = 1 | Lượt trước hạn **0** đăng nhập; sau làm mới cache dùng lại **0** thêm | `Test05.test_01,02,03,07` |
| (d) | Thiếu credential ⇒ TỪ CHỐI rõ ràng | Gọi `lay_token` khi chưa lưu credential; đếm request stub | `THIEU_CREDENTIAL`, **0 request** | Lưu credential xong, cùng lượt gọi **thành công**, 1 request | `Test03.test_01` |
| (e) | Credential tenant A không dùng cho tenant B | (1) B chưa có credential; (2) chép **nguyên bản mã** A sang bản ghi B | (1) `THIEU_CREDENTIAL`, 0 request<br>(2) `KHONG_DOC_DUOC_CREDENTIAL`, 0 request | A vẫn đăng nhập được sau cả hai ca; B có credential riêng vẫn chạy | `Test03.test_04,05,06` |

> `lay_token`/`lam_moi_token` trả token cho adapter **nội bộ** — đó là thiết kế, không phải "API
> response". Trong phạm vi B2 KHÔNG có HTTP route nào; mọi hàm mô tả trạng thái
> (`trang_thai_*`) đã được quét và không chứa token. Bên tích hợp phải theo §12.

### 8.2 Kết quả quét "token có trong log không?"

**KHÔNG.** Phép đo không chỉ `assertNotIn` trên chuỗi log:
- Dựng stub, chạy trọn vòng đời chính: lưu credential → cấp token → đọc cache → làm mới với
  `token_cu` (mô phỏng 401) → hủy → cấp lại. Ca hết hạn/đa tiến trình nằm ở `Test05`.
- Bắt log thật của logger `vip.best_auth` ở mức DEBUG.
- **Đối chứng dương:** ghi một canary *khác* (`CANARY-LOG-DOI-CHUNG-…`) qua cùng logger; khẳng định
  bộ quét **thấy** canary đó. Nếu bộ ghi log/assertLogs hỏng, ca đối chứng sẽ hỏng trước.
- Sau đó khẳng định token thật, password, username **không** xuất hiện.
- Log còn được kiểm tra "có ích": phải thấy `su_kien=token_cap`, `su_kien=token_lam_moi`,
  `su_kien=token_huy`, `lop=token_truy_cap_best`, `ma_ly_do=OK` — tránh trường hợp bộ lọc an toàn
  biến mọi thứ thành rỗng/`KHAC` rồi "qua" một cách vô nghĩa.

Audit cũng được quét tương tự, với canary chèn riêng vào bảng `audit`.

### 8.3 Vì sao 0 ca bỏ qua?

Không có `skipTest`, không có `@unittest.skip`, không phụ thuộc mạng ngoài, không cần credential.
Stub chạy trong tiến trình; 3 tiến trình con dùng `subprocess` + `127.0.0.1`. Trên máy đo (macOS,
Python 3.9.6, `cryptography 50.0.1`) tất cả chạy thật. Nếu chạy trên nền không có `flock`/`fcntl`,
bộ thử sẽ **hỏng**, không tự bỏ qua — đó là lựa chọn có chủ đích: không che giấu môi trường thiếu.

---

## 9. CHI TIẾT CÁC NHÓM CA THỬ

| Nhóm | Số ca | Đo cái gì |
|---|---:|---|
| `Test01_KhoVaPlaintext` | 5 | Plaintext trong toàn kho; quyền 0700/0600; hai tệp hai lớp; kho hỏng không bị ghi đè; cache bị sửa ⇒ đăng nhập lại đúng 1 lần |
| `Test02_KhongRoRiToken` | 5 | Log/response/audit không token; lỗi HTTP không echo secret; AST chỉ dùng 4 hàm hợp đồng `bao_mat`; không hardcode token |
| `Test03_CredentialVaTenant` | 9 | Thiếu credential/tenant; credential sai không lưu; A không dùng cho B; AAD chặn chép bản mã; xoay credential vô hiệu token; dùng lẫn hai lớp; password Unicode/khoảng trắng |
| `Test04_BearerWebhook` | 6 | Bearer đúng/sai/thiếu/sai dạng/né newline; tenant isolation; `webhook_ma` binding; không rò bearer; ciphertext bị sửa ⇒ từ chối; không gọi mạng |
| `Test05_VongDoiToken` | 11 | Hạn 30 ngày + cache; 16 thread; 3 tiến trình; làm mới sau 401; lỗi login không cache; đồng hồ lùi; 5 lượt tại hạn; cache token không dùng chéo tài khoản; 401 thất bại xóa token chết; xoay credential giữa chừng bị từ chối; hủy token đua với login |
| `Test06_Transport` | 11 | URL/TLS; đúng request `/User/Login`; phản hồi sai; lỗi HTTP; redirect bị chặn; chưa cấu hình transport; transport sai; token được kiểm tra lại; transport độc hại không nhét secret vào lỗi; **handshake TLS thật với cert tự ký bị từ chối** |
| **Tổng** | **47** | |

Mọi ca phủ định đều có ít nhất một đối chứng dương trong cùng ca hoặc ca liền kề (bảng §8.1 ghi rõ).

---

## 10. REAL PASS — BLOCKED, VÀ ĐIỀU KIỆN MỞ KHÓA

**REAL PASS = CHƯA CÓ.** Không có lời gọi mạng nào tới BEST trong lượt này (kể cả sandbox/test host).
Không có credential thật. Không đọc được Google Docs. Vì vậy:

| Hạng mục | Trạng thái |
|---|---|
| Đăng nhập BEST thật | **BLOCKED** — thiếu duyệt + credential + host |
| Xác nhận header/webhook thật | **BLOCKED** — thiếu tài liệu/callback thật |
| Xác nhận hạn token thực tế | **BLOCKED** — chỉ có đặc tả 30 ngày |
| Kiểm tra TLS/cert/IP allowlist của BEST | **BLOCKED** — không được gọi |
| Chạy sandbox | **BLOCKED** — `V-G09-01`/`V-13906-05` chưa cấp (theo `docs/SHARED_CONTRACTS.md` §37) |
| Production | **KHÔNG ĐƯỢC PHÉP** |

**Điều kiện để chuyển MOCK → REAL (không làm trong lượt này):**
1. Owner cấp quyền gọi đúng môi trường (sandbox trước), cấp credential thật qua kênh an toàn.
2. Có URL Google Docs/đặc tả chính thức; đối chiếu 4 dòng §3.1 và **bổ sung** các mục U1–U14.
3. Chạy lại bộ ca với stub → thay stub bằng sandbox; ghi **exit code + số ca + số skip** riêng.
4. Tuyệt đối không dùng chung báo cáo MOCK và REAL; không ghi "REAL PASS" khi chưa có log thật.

---

## 11. RỦI RO CÒN LẠI (đã biết, chưa xử lý trong phạm vi B2)

1. **Tương thích BEST thật chưa đo.** Header, charset token, schema lỗi, rate limit, hạn token thực
   tế đều CHƯA KIỂM CHỨNG. MOCK PASS chỉ đo hành vi nội bộ + stub.
2. **Token 30 ngày là bearer sống lâu.** Nếu lộ, kẻ tấn công dùng được tới 30 ngày. Chưa biết endpoint
   thu hồi. Giảm thiểu hiện có: mã hóa khi nghỉ, không log, cache theo tenant, hủy cache khi đổi credential.
3. **Kho khóa cục bộ.** `secret_provider` giữ khóa trên cùng máy/thư mục dữ liệu. Ai đọc được cả
   bản mã lẫn khóa sẽ giải mã. Chưa có HSM/KMS. Ranh giới bảo vệ là quyền truy cập hệ tệp + quyền máy.
4. **Kho tệp không có RBAC cấp CSDL.** Cách ly tenant nằm trong mã (AAD + kiểm tra tenant/tài khoản),
   không phải hàng rào SQL. Một lỗi ghi tệp của tiến trình khác có thể ảnh hưởng kho.
5. **`flock` trên hệ tệp mạng không đáng tin.** Chưa đo NFS/SMB; nếu triển khai kiểu đó, cơ chế
   chống đồng loạt re-login có thể mất tác dụng.
6. **Đồng hồ.** Hạn token dựa trên đồng hồ máy. Đã xử lý lùi > 300 giây, nhưng chưa đo lệch thuận
   lớn (đồng hồ chạy nhanh làm token bị coi là hết hạn sớm — chỉ gây đăng nhập lại, không rò secret).
7. **Audit có thể bị sửa bởi người có quyền CSDL.** Audit là bằng chứng vận hành, không phải bằng
   chứng mật mã. Chưa có chữ ký chuỗi audit.
8. **Bộ nhớ tiến trình/core dump.** Password/token tồn tại trong RAM khi dùng; module không kiểm soát
   core dump, swap, hay công cụ gỡ lỗi của máy chủ.
9. **Webhook chưa chống replay/chữ ký.** B2 chỉ xác thực Bearer. Nếu BEST yêu cầu timestamp/chữ ký,
   B3 phải bổ sung; hiện CHƯA KIỂM CHỨNG.
10. **Không có rate limit phía module.** `lay_token` không tự retry, nhưng bên gọi có thể gọi lặp.
    Cần giới hạn ở tầng HTTP/route (ngoài phạm vi B2).
11. **Chưa có quy trình mã hóa lại kho tệp khi xoay khóa.** Bản mã là `v3$<key_id>$...`, nên vẫn
    đọc được khi khóa cũ còn trong `secret_provider`. Nếu xóa khóa cũ trước khi mã hóa lại kho,
    bản ghi cũ sẽ không giải mã được. `ma_hoa_lai_carrier_accounts()` của dự án chỉ phủ
    `carrier_accounts`, KHÔNG phủ ba tệp của B2. Cần một lượt xoay khóa riêng có sao lưu + đối chứng
    (ngoài phạm vi lượt này; không tự thêm để tránh rủi ro mất dữ liệu).

---

## 12. GIAO DIỆN TÍCH HỢP CHO B1 / B3 / SERVER

```python
import xac_thuc_best as best

# ── Provisioning (admin, một lần; KHÔNG gọi mạng) ─────────────────────────────
best.luu_credential_dang_nhap(tenant_id, tai_khoan, username, password)
best.luu_bearer_webhook(tenant_id, tai_khoan, bearer_webhook, webhook_ma=webhook_ma)

# ── Adapter (B1) — đặt transport TƯỜNG MINH sau khi Owner duyệt host ──────────
best.dat_transport_mac_dinh(
    best.TransportDangNhapHTTPS("https://<host-BEST-CHUA-XAC-MINH>")
)
token = best.lay_token(tenant_id, tai_khoan)          # NỘI BỘ — không serialize
headers["Authorization"] = "Bearer " + token
# ... gọi API nghiệp vụ của BEST ...
# nếu BEST trả 401:
token = best.lam_moi_token(tenant_id, tai_khoan, token_cu=token)

# ── Webhook (B3) — tenant/tài khoản phải được xác định TRƯỚC ─────────────────
kq = best.kiem_bearer_webhook(
    tenant_id, tai_khoan,
    headers.get("Authorization"),      # tên header: CHƯA KIỂM CHỨNG với BEST
    webhook_ma=webhook_ma,             # nếu có
)
if not kq:
    return 401, {"loi": "webhook khong hop le", "ma": kq.ma_ly_do}

# ── Dashboard (không secret) ─────────────────────────────────────────────────
best.trang_thai_credential(tenant_id, tai_khoan)
best.trang_thai_token(tenant_id, tai_khoan)
best.trang_thai_bearer_webhook(tenant_id, tai_khoan)
```

**Quy tắc bắt buộc cho bên tích hợp:**
- Không đưa `token` vào JSON response, log, audit, thông báo lỗi, hay URL.
- Không gọi `lay_token` khi chưa xác định `tenant_id`; không suy ra tenant từ dữ liệu không tin cậy.
- Không dùng Bearer webhook làm token đăng nhập (và ngược lại).
- `TransportDangNhapHTTPS` chỉ nhận host HTTPS; không thêm tham số tắt xác minh chứng chỉ.

---

## 13. TỆP THAY ĐỔI / TUÂN THỦ QUYỀN GHI

```
?? app/xac_thuc_best.py                    (mới)
?? app/thu/thu_best_auth.py                 (mới)
?? docs/BEST_EXPRESS_SECURITY_REVIEW.md     (mới)
```

- **Không sửa:** `app/bao_mat.py`, `app/adapter_best.py` (chưa tồn tại), `app/server.py`,
  `app/webhook.py`, `app/adapter*.py`, `app/csdl.py`, `app/migrate.py`, `app/cau_hinh.py`.
- **Không commit/push:** HEAD vẫn `cb23312`; không tạo commit. AG-00 commit hộ.
- **`app/adapter_best.py` chưa tồn tại ở mốc `cb23312`** (nhánh B1 cùng mốc). Vì vậy lượt này
  KHÔNG có ca tích hợp với adapter BEST; giao diện để B1 gọi nằm ở §12. Không tự tạo adapter_best.py
  vì tệp đó thuộc phạm vi B1.
- **Không tạo dữ liệu thật:** mọi thư mục đo là `tempfile.mkdtemp`; xóa sau khi chạy.
- **Không có secret thật trong mã/tệp:** test sinh canary ngẫu nhiên bằng `secrets.token_hex`.

---

## 14. PHỤ LỤC — LỆNH VÀ BẰNG CHỨNG THÔ

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/b2-auth

# 1) Kiểm cú pháp (không ghi __pycache__)
python3 -B -c "compile(open('app/xac_thuc_best.py',encoding='utf-8').read(),'x','exec'); \
               compile(open('app/thu/thu_best_auth.py',encoding='utf-8').read(),'y','exec')"
# exit 0

# 2) Chạy bộ thử MOCK
python3 -B app/thu/thu_best_auth.py
# Ran 47 tests ... OK
# MOCK PASS — KHÔNG PHẢI REAL PASS
# Số ca: 47 · Bỏ qua: 0 · Hỏng: 0
# Quét token/password trong log + response + audit: KHÔNG THẤY
# Quét plaintext trong toàn bộ thư mục dữ liệu: KHÔNG THẤY
# exit 0

# 3) Xác nhận mốc mã và tệp thay đổi
git rev-parse HEAD
# cb23312dc702a6a1bf51e9cb53c7397770cd9637
git status --short
# ?? app/thu/thu_best_auth.py
# ?? app/xac_thuc_best.py
# ?? docs/BEST_EXPRESS_SECURITY_REVIEW.md   (sau khi tạo báo cáo)
```

**Bảng đối chiếu 4 dữ kiện đã xác nhận với mã:**

| Dữ kiện | Hằng/vị trí | Ca thử chứng minh |
|---|---|---|
| `POST /User/Login` | `DUONG_DAN_DANG_NHAP` | `Test06.test_03`: `path == "/User/Login"` |
| `{"Username","Password"}` | `TransportDangNhapHTTPS.dang_nhap` | `Test06.test_03`: đúng 2 khóa, đúng giá trị |
| `{"token"}` | bóc khóa `token` | `Test06.test_03,04` |
| 30 ngày | `HAN_TOKEN_GIAY` | `Test05.test_01` |

---

## 15. VÒNG REVIEW ĐỘC LẬP — PHÁT HIỆN VÀ CÁCH SỬA

Một vòng review bảo mật độc lập (read-only) đã soi module + bộ thử + báo cáo này. Kết luận của
review: **FIX-BEFORE-DONE**, không có lỗi CRITICAL, nhưng có một lỗi HIGH về vòng đời token và
một số tuyên bố trong báo cáo chưa được đo. Tất cả đã được xử lý như sau:

| # | Phát hiện | Cách sửa | Bằng chứng |
|---|---|---|---|
| 1 | **HIGH** — refresh sau 401 thất bại vẫn để token vừa bị từ chối trong cache | `lam_moi_token` xóa đúng `token_cu` khỏi cache **trước** khi gọi mạng | `Test05.test_09`: login hỏng ⇒ `co_ban_ghi=False`; lượt sau không trả token chết |
| 2 | **MEDIUM** — credential đổi giữa lúc login, token của credential cũ vẫn được trả | `_cache_token_sau_dang_nhap` ném `CREDENTIAL_DA_DOI_KHONG_LUU`; không cache, không trả token cũ | `Test05.test_10`: token cũ bị từ chối; credential mới dùng được |
| 3 | **MEDIUM** — TLS mới chỉ kiểm thuộc tính context, chưa đo handshake | Thêm server TLS loopback dùng cert tự ký; client phải từ chối trước khi gửi credential | `Test06.test_11`: `KHONG_KET_NOI_DUOC`, 0 request; đối chứng HTTP loopback đăng nhập được |
| 4 | **MEDIUM** — chưa quét plaintext của **access token** trong kho | Thêm quét token ngay sau khi cache và sau khi làm mới, kèm đối chứng dương | `Test05.test_01`: cấy token plaintext ⇒ phép quét thấy; kho thật ⇒ không thấy |
| 5 | **MEDIUM/LOW** — báo cáo nói quét log/audit cả vòng đời nhưng test mới phủ một phần | Mở rộng sang làm mới + hủy + cấp lại; sửa lại câu chữ báo cáo cho đúng | `Test02.test_01,03`: có `token_cap`, `token_lam_moi`, `token_huy`; quét toàn bộ token |
| 6 | **LOW** — `LoiXacThucBest` nhận chuỗi tùy ý, transport lạ có thể nhét secret vào lỗi | Whitelist `MA_LOI` ngay trong constructor; mã lạ ⇒ `TRANSPORT_LOI` | `Test06.test_10`: transport ném canary ⇒ lỗi/log/audit không chứa canary |
| 7 | **LOW** — `huy_token` chỉ khóa toàn cục, login đang chạy có thể ghi lại token sau khi hủy | Lấy khóa theo cặp `(tenant, tài khoản)` trước khóa ghi toàn cục | `Test05.test_11`: login chạy 0,2 s, hủy trong lúc chạy ⇒ cache cuối rỗng |
| 8 | **LOW** — thông điệp/doc nói password bị chặn ký tự điều khiển, trong khi validator cố ý chỉ chặn NUL/quá dài | Sửa thông điệp `MA_LOI` + bảng §7 cho đúng; KHÔNG siết bảng chữ password vì chưa có đặc tả | `MA_LOI`; `Test03.test_09` (password Unicode/khoảng trắng vẫn hoạt động) |

**Điều review vẫn đúng và chưa thể xử lý trong local-only:** đường HTTPS **hợp lệ với CA tin cậy**
chưa được đo (chỉ đo được phía từ chối cert tự ký); mọi mục REAL với BEST vẫn BLOCKED. Báo cáo đã
sửa các câu tuyên bố quá mức tương ứng (§2, §3.2 U13, §6, §8.2).

---

## 16. KẾT LUẬN

- **Đã làm:** module xác thực BEST hai lớp secret, mã hóa AES-256-GCM qua hợp đồng `bao_mat`, vòng đời
  token 30 ngày có cache + khóa liên tiến trình, bộ thử MOCK 47 ca với quét thật và đối chứng dương.
- **Đã đo:** exit 0 · 47 ca · 0 bỏ qua · 0 hỏng · không plaintext trong kho (password, username,
  access token, webhook Bearer) · không token trong log/response/audit · hết hạn làm mới đúng 1 lần ·
  401 thất bại không để token chết trong cache · xoay credential giữa chừng bị từ chối · thiếu
  credential bị từ chối · tenant A không dùng được cho tenant B · TLS từ chối cert tự ký.
- **Chưa làm / BLOCKED:** REAL PASS với BEST; xác minh Google Docs; header webhook thật; schema lỗi;
  endpoint refresh (không đoán); TLS/cert/rate limit thật; sandbox/production.
- **Cảnh báo sử dụng:** mọi con số trong báo cáo này là **MOCK**. Không được trích dẫn như bằng chứng
  tương thích BEST thật. Không được chuyển sang REAL mà bỏ qua điều kiện ở §10.
