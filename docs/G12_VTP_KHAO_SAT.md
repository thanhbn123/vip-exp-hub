# G12 — KHẢO SÁT LẠI VIETTEL POST TRÊN BẢN MỚI NHẤT, VÀ CHỐT CHẶN D-9

**Tác tử:** AG-03 CARRIER ENGINEER · **Ngày đo:** 15/10/2026
**Worktree:** `~/code/veh4-g12-carrier`, nhánh `agent/g12-carrier`, nền `714fd76`
**Máy đo:** MacBook Pro · `python3` 3.9.6 (Command Line Tools) · `gh` CLI · Chrome qua công cụ
trình duyệt của phiên

---

## 0. PHẠM VI CỦA PHÉP ĐO — đọc trước mọi con số (§12.1 luật 3 và luật "0")

| Đo cái gì | Bằng công cụ nào | Phạm vi nó thực sự phủ |
|---|---|---|
| Khoảng cách commit | `gh api .../compare/<a>...<b>` | Chỉ ba điểm `4df8ce7`, `main`, `develop`. Không phủ 20 nhánh còn lại |
| Nội dung lớp VTP | bản clone **MỚI** `--depth=50 --branch develop` trong scratchpad của phiên | Chỉ cây làm việc của `develop` tại `68e9642`. Không phủ lịch sử trước đó |
| Tài liệu J&T | Chrome, `document.body.innerText` của trang `apiDoc/orderserve/create` | Đúng một trang, đúng lúc 15/10/2026. Không phủ trang khác |
| Chốt chặn D-9 | `python3 app/thu/thu_anh_xa_area.py` | Logic chốt chặn ở **bản tham chiếu**. **KHÔNG** phủ `adapter_jt.py` — xem mục 5 |

**NẰM NGOÀI TOÀN BỘ phạm vi, nói thẳng:** không một lượt gọi API hãng nào được thực hiện trong
lượt này — `V-G09-01` và `V-13906-05` **CHƯA CẤP**. Mọi dòng dưới đây nói về **mã và tài liệu**,
không nói về việc hãng có chấp nhận hay không.

### Bản clone `~/code/vip-viettelpost` — KHÔNG CHẠM

Khảo sát làm trên bản clone mới trong scratchpad. Bản clone của phiên khác giữ nguyên:

```
On branch feature/shp-database
Your branch is up to date with 'origin/feature/shp-database'.
nothing to commit, working tree clean
4df8ce7b699bf02890ed831c1383e11eb153aef5
```

Đo **trước** lượt khảo sát và **sau** lượt khảo sát, hai lần giống nhau. Không `pull`, không
`checkout`, không ghi gì vào thư mục đó.

---

## 1. KHOẢNG CÁCH COMMIT — ĐÍNH CHÍNH CẢ CON SỐ CỦA G09

G09 đo `4df8ce7...main` = **174 commit** và kết luận `main` là bản mới nhất. Đo lại hôm nay:

| Phép so | Kết quả | Lệnh |
|---|---|---|
| `4df8ce7...main` | **ahead 174**, behind 0 | `gh api .../compare/4df8ce7...main` |
| `4df8ce7...develop` | **ahead 194**, behind 0 | `gh api .../compare/4df8ce7...develop` |
| `main...develop` | **ahead 21, behind 1 — DIVERGED** | `gh api .../compare/main...develop` |

- `main` = `677cba9`, ngày **2026-10-07**, nhánh mặc định.
- `develop` = `68e9642`, ngày **2026-10-14** — đây mới là **đỉnh thật** của repo.
- Repo có **20 nhánh**; `pushed_at` = 2026-10-14.

### Con số 174 của G09 vẫn ĐÚNG, nhưng nó đo nhầm đích

`main` chưa nhúc nhích từ 07/10, nên 174 hôm nay vẫn là 174. Nhưng **`main` không phải bản mới
nhất** — `develop` đi trước nó 21 commit và `main` đi sau `develop` 1 commit. G09 viết *"`origin/main`
là bản mới nhất"* là **chưa kiểm `develop` trước khi tin `main`** — đúng cái bài học mà chính
G09 rút ra về bản clone cũ, lặp lại ở một tầng khác.

### Nhưng 21 commit đó KHÔNG đổi kết luận nghiệp vụ — và đây là chỗ phải nói đúng phạm vi

Đo nội dung 21 commit bằng `gh api .../compare/main...develop --jq '.files[].filename'`:

| Nhóm file | Có gì |
|---|---|
| `requirements*.txt` / `*.lock`, `.github/workflows/*` | dependabot: `fastapi` 0.141.1→0.142.2, `sqlalchemy` 2.0.36→2.1.3, `ruff` 0.6.9→0.16.10, `actions/setup-python` 5.6.0→7.0.0… |
| `scripts/update-locks.sh`, `tests/unit/test_dependency_lock.py` | hạ tầng khoá phiên bản |
| `app/providers/viettel_post/events.py` | **+0 / −1 dòng** — xoá đúng một dòng trống giữa hai `import` |

⇒ **Toàn bộ chênh lệch nghiệp vụ giữa `main` và `develop` là MỘT DÒNG TRỐNG.** Lớp tích hợp VTP
mà G09 mô tả trên `main` là **cùng một lớp** đang nằm trên `develop`. Khảo sát của G09 về nội
dung **không sai**; chỗ cần đính chính chỉ là câu "`main` là mới nhất".

---

## 2. LỚP TÍCH HỢP VTP CÓ GÌ — ĐO TRÊN `develop` (`68e9642`)

`wc -l` trên bản clone mới: **2.391 dòng** trong `app/providers/viettel_post/` (1.174),
`app/providers/base/` (217) và `app/webhooks/` (1.000).

| Thành phần | File | Nội dung đo được |
|---|---|---|
| **Đường xác thực** | `viettel_post/auth.py` (141) | Ba đường, dẫn `partner2.viettelpost.vn/document/token-authen`: `POST /v2/user/Login` (USERNAME/PASSWORD → token ngắn) → `POST /v2/user/ownerconnect` (header `Token` → token dài, tài liệu ghi 1 năm); và `POST /v2/user/LoginVTP` (đổi secret token của viettelpost.vn). Có đệm token, `invalidate()`, `can_refresh`. `token` để `repr=False`. Trường `data.expired` luôn `0` trong mọi mẫu ⇒ **cố ý không diễn giải là hạn dùng** |
| **Endpoint** | `viettel_post/mapping.py` (276) | `getPriceAll` (dịch vụ) · `getPrice` (cước) · `createOrder` · `UpdateOrder` với `TYPE=4` (huỷ). Mỗi endpoint dẫn đúng một trang tài liệu, ngày kiểm 2026-09-29. Khoá payload không có ánh xạ thì **`ValueError`**, không rơi im lặng |
| **Client HTTP** | `viettel_post/client.py` (174) | Token đi ở header **`Token`** (không phải `Authorization`); `Content-Type: application/json;charset=UTF-8`; phong bì `{status,error,message,data}`; timeout 20 s; `httpx.AsyncClient` tạo lười |
| **Bảng mã trạng thái** | `viettel_post/status_mapper.py` (148) | **21 mã** chính thức từ trang webhook. **15 mã có ánh xạ**, **6 mã cố ý `None`** (102, 202, 503, 505, 508, 550) kèm lý do từng mã. Mã lạ **không bao giờ** mặc định về `IN_TRANSIT` |
| **Bảng lỗi** | `viettel_post/errors.py` (81) | Cây lỗi 10 lớp (timeout · network · 4xx · 401/403 · 5xx · sai khuôn · nghiệp vụ · auth). `redact()` che secret đã biết **và** mọi chuỗi dạng JWT (`eyJ…`), cắt 200 ký tự |
| **Khuôn webhook** | `webhooks/viettel_post_payload.py` (155) | Thân `{"DATA": {...}, "TOKEN": str}`. Xác thực = **so chuỗi `TOKEN` trong THÂN với bí mật chung**, bằng `hmac.compare_digest` (`processor.py:201`, `provider.py:293`). **Không có HMAC, không có chữ ký** |
| **Dấu vân tay chống trùng** | `webhooks/fingerprint.py` (70) | SHA-256 trên `provider\|ORDER_NUMBER\|ORDER_STATUS\|ORDER_STATUSDATE`. Thiếu `ORDER_STATUSDATE` thì băm **toàn bộ** `DATA` — có chủ đích, và có ghi lý do: thu hẹp lại (CR-READY-002) làm hai lần giao khác nhau cùng trạng thái **đụng nhau và mất im lặng**; băm cả cụm thì hỏng theo kiểu **nhìn thấy được**. Chọn cái hỏng nhìn thấy được, dẫn đúng `CLAUDE.md` 12.2 |
| **Đường xử lý webhook** | `webhooks/processor.py` (247) + `sql_sink.py` (189) | Chuỗi: kiểm cỡ → giải JSON → kiểm `TOKEN` → kiểm trường → vân tay → giành khoá chống trùng → lưu bản thô → ánh xạ → ACK. Trùng ⇒ `DUPLICATE` + HTTP 200 |

### Bằng chứng chạy thật của repo nguồn — và vì sao nó KHÔNG nâng mức của chúng ta

`docs/VTP_DEV_E2E.md` của repo đó ghi: **2026-10-02 14:44 +07, G08 PASS**, run `36978332181`
(`aa5c4c0`) — Login + ownerconnect bằng tài khoản Partner dev, services, fee, **tạo đơn thử
`303296591832` rồi huỷ**, trên `partnerdev.viettelpost.vn`.

Cũng trong file đó, đọc kỹ phần "Lịch sử", là **một ca §12.1 mẫu mực của chính họ**: bản
`G08 PASS` ngày 01/10 **đã bị rút lại** (CR-STG-007) vì với token tĩnh thì bước `authenticate`
**không gọi mạng**, và `getPriceAll`/`getPrice` của `partnerdev` **không kiểm token** — nên
**token bịa cũng PASS**.

> **Bằng chứng này là của repo khác, trên credentials của họ, ngày của họ.** Nó chứng minh
> *đường đó đi được*, **không** chứng minh gì về `app/adapter_vtp.py` của VIP EXPRESS HUB.
> Không một dòng nào trong báo cáo này được đọc là "VTP đã chạy được ở bên mình".

---

## 3. BẢNG SÁU MỨC — VIETTEL POST, CHO VIP EXPRESS HUB

Mức được gán cho **dự án này** (`~/code/veh4-g12-carrier`), không cho repo nguồn.
`SANDBOX VERIFIED` và `LIVE VERIFIED` **không xuất hiện ở bất kỳ dòng nào** — chưa gọi hãng lượt
nào, nên không có dòng nào được phép mang hai mức đó.

| # | Hạng mục | Mức | ĐO BẰNG GÌ |
|---|---|---|---|
| 1 | Đường xác thực | `DOCUMENTED` | `auth.py` trên `develop` dẫn `partner2.../document/token-authen`; bên mình `grep -n "Login\|ownerconnect" app/adapter_vtp.py` → **0 dòng**. Tài liệu có, mã bên mình chưa có |
| 2 | Chữ ký request | `BLOCKED` | VTP **không ký request** — xác thực bằng header `Token` (`client.py:TOKEN_HEADER`). Ghi `BLOCKED` thay vì bỏ trống để không ai tưởng đã làm xong. Cái còn thiếu: **không có gì để làm** — cần ghi rõ trong adapter là hãng không ký |
| 3 | Endpoint nghiệp vụ | `DOCUMENTED` | 4 hằng `*_PATH` trong `mapping.py`, mỗi cái dẫn một trang tài liệu. `app/adapter_vtp.py` bên mình: **mock toàn bộ**, không có hằng endpoint nào |
| 4 | Bảng mã trạng thái | `DOCUMENTED` (hãng) + `MOCK VERIFIED` (bộ mô phỏng) | 21 mã của hãng nằm ở `status_mapper.py` repo nguồn. Bên mình `app/trang_thai_hang.py` **CÓ** bảng `vtp` nhưng là `VTP_MA_MOCK` — 6 khoá do **chính dự án bịa ra để chạy mock**, và file tự khai đúng như vậy (`NGUON_BANG["vtp"] = "bộ mô phỏng của chính dự án (KHÔNG có tài liệu hãng)"`, `PHIEN_BAN_TAI_LIEU["vtp"] = "chua-co-tai-lieu"`). **Không một mã THẬT nào của VTP có trong hệ** — đo bằng `grep -n "VTP" app/trang_thai_hang.py` |
| 5 | Khuôn webhook | `DOCUMENTED` | `viettel_post_payload.py` + trang `partner2.../document/webhook`. Cửa webhook bên mình: `grep -n "SO_DO_THEO_HANG" app/webhook.py` → dòng 150 `"vtp": None` ⇒ **chưa cài**, không nhận callback thật |
| 6 | Dấu vân tay chống trùng | `DOCUMENTED` | Công thức + hai nhánh dự phòng đọc được nguyên văn ở `fingerprint.py`. Bên mình `app/webhook.py` có chống trùng riêng, **chưa đối chiếu** với công thức này |
| 7 | Bảng mã lỗi | `BLOCKED` | `loi_hang.BANG_MA_LOI` bên mình chỉ có khoá `jt` (`grep -n 'BANG_MA_LOI =' app/loi_hang.py` → `{"jt": JT_MA_LOI}`). Cái còn thiếu: **VTP không công bố bảng mã lỗi dạng số**; repo nguồn phân loại theo phong bì `error:true` + 4 chuỗi thông điệp auth, **không phải** bảng mã |
| 8 | Nhãn vận đơn | `BLOCKED` | Không có trang tài liệu VTP nào về in nhãn đọc được; repo nguồn **không có** `get_label`. Cái còn thiếu: tài liệu in nhãn của VTP. Ghi chú: `adapter_vtp` bên mình đang khai `getShippingLabel=True` — khai quá thứ chứng minh được |
| 9 | Tra vận đơn theo mã | `BLOCKED` | Repo nguồn **không cài** `get_shipment` theo endpoint nào; trạng thái về **chủ yếu qua webhook**. Cái còn thiếu: xác nhận VTP có API tra theo mã hay không (câu B7) |
| 10 | Giới hạn tần suất | `DOCUMENTED` | Trang webhook nêu VTP **thử lại tối đa 5 lần** tới khi nhận HTTP 200. Không thấy trần tần suất gọi API |
| 11 | Chạy thật trên `partnerdev` | `BLOCKED` | **Của repo khác, không của mình.** Cái còn thiếu, chính xác bốn thứ: `V-G09-01` · `VIP_HUB_HARNESS_NGUOI_DUYET` · file credentials · `CHO_PHEP_LIVE` (chỉ Owner mở) |

**Câu "0" bắt buộc nêu phạm vi:** *Không có hạng mục nào ở mức `SANDBOX VERIFIED` hoặc
`LIVE VERIFIED`* — đo bằng chính bảng trên, phạm vi là 11 hạng mục VTP của dự án này, công cụ là
đọc mã + `gh api` + `grep`. **NẰM NGOÀI:** mọi hạng mục J&T, mọi hạng mục của repo nguồn, và mọi
thứ chỉ hãng mới trả lời được.

---

## 4. TÁI DÙNG ĐƯỢC GÌ — VÀ KHÔNG TÁI DÙNG ĐƯỢC GÌ

Nền kỹ thuật hai bên khác hẳn: VIP EXPRESS HUB dùng `sqlite3` + thư viện chuẩn, **đồng bộ**;
repo nguồn dùng FastAPI + SQLAlchemy + Alembic + `httpx`, **bất đồng bộ**.

### Tái dùng được — DỮ KIỆN, chép thẳng được vì nó là sự thật về hãng

| Thứ | Vì sao chép được |
|---|---|
| **21 mã trạng thái + 6 mã cố ý không ánh xạ** | Là bảng của hãng, không dính nền kỹ thuật. Kèm theo cả **lý do** từng mã bị bỏ — thứ đắt nhất, vì nó là phán đoán đã có người cân nhắc |
| **4 endpoint + `TYPE=4` huỷ + ngưỡng `ORDER_STATUS < 200`** | Dữ kiện tài liệu |
| **Ba đường xác thực và thứ tự Login → ownerconnect** | Dữ kiện tài liệu, đã có người chạy thật |
| **Header `Token`, `Content-Type`, khuôn phong bì `{status,error,message,data}`** | Dữ kiện tài liệu |
| **4 chuỗi thông điệp auth** (`Header Token is required`, `Token invalid`, `Token invalid or expired`, `Invalid owner account or password!`) | Là thứ duy nhất thay cho bảng mã lỗi VTP |
| **Mâu thuẫn nội tại của tài liệu VTP:** bảng trạng thái đánh dấu `104` là trạng thái cuối, đoạn *"Lưu ý"* lại liệt kê 101/107/201/501/503/504 — **không có 104**, mà 104 đứng trước 200 | **Ca mã nhập nhằng thứ hai**, cùng họ với J&T `110`. Phải vào sổ `NHAP_NHANG` khi mang sang |
| **Công thức vân tay + lý do chọn nhánh dự phòng băm cả cụm** | Là lập luận, chép được nguyên vẹn |

### KHÔNG tái dùng được — MÃ

| Thứ | Vì sao không |
|---|---|
| `client.py`, `auth.py`, `api.py`, `provider.py` | `async`/`httpx`. Bên mình `transport.py` đồng bộ, có chính sách thử lại/timeout riêng đã được kiểm 95 ca. Chép sang kéo theo cả một nền phụ thuộc mới |
| `processor.py`, `sql_sink.py`, `stores.py` | SQLAlchemy + Alembic. Bên mình `csdl.py` dùng `sqlite3` trần |
| `errors.py` cây 10 lớp | Bên mình đã có `NormalizedCarrierError` + danh sách **trắng** `DUOC_THU_LAI`, đã kiểm ca D1–D9. Hai hệ lỗi song song là hai hệ sẽ lệch nhau |
| Bằng chứng `G08 PASS` ngày 02/10 | Credentials của họ, lượt chạy của họ. **Không chuyển nhượng được** |

### Một ý tưởng đáng mượn, không phải mã

`redact()` che **mọi chuỗi dạng JWT** chứ không chỉ các secret đã biết — tức là một lớp danh sách
**đen theo HÌNH DẠNG**, bắt được cả token mà người viết chưa kịp khai báo. Đáng soi vào chỗ ghi
audit của hệ mình. *(Đề xuất cho AG-00, AG-03 không tự làm.)*

---

## 5. D-9 — BIẾN GIẢ ĐỊNH THÀNH CHỐT CHẶN CỨNG

### 5.1 Vấn đề

`adapter_jt.TRUONG_HANH_CHINH` map `area` ← **quận/huyện**. AG-00 đã ghi rõ trong docstring rằng
đó là **giả định**. Nhưng docstring không chặn được máy: ngày nào đó Owner mở `CHO_PHEP_LIVE`,
giả định này **lặng lẽ thành dữ kiện** và không ai phải đọc lời bình để điều đó xảy ra.

### 5.2 DỮ KIỆN MỚI ĐO ĐƯỢC HÔM NAY — giả định này nhiều khả năng SAI

Đọc `open.jtexpress.vn/apiDoc/orderserve/create` bằng trình duyệt (SPA, `curl` không đọc được),
**bảng tham số** và **ví dụ yêu cầu** trên cùng trang, nguyên văn:

| Trường | Kiểu | Bắt buộc | Chú thích của hãng | Ví dụ của hãng |
|---|---|---|---|---|
| `prov` | String(40) | **Y** | 寄件人省 (tỉnh người gửi) | `"Hồ Chí Minh"` |
| `city` | String(40) | **N** | 寄件人市 · *"新的两级行政区划地址无需填写该字段，可以设置为 null。"* | **`"Quận 1"`** |
| `area` | String(40) | **Y** | 寄件人区 (khu vực người gửi) | **`"Phường Nguyễn Thái Bình-028QQ107"`** |

Dịch dòng chú thích của `city`: *"địa chỉ hành chính HAI CẤP mới thì không cần điền trường này,
để null được"*.

**Hai cách đọc, và cả hai đều KHÔNG ra "quận":**

- Đọc theo **ví dụ** (ba cấp cũ): quận nằm ở `city`, **phường nằm ở `area`**.
- Đọc theo **hai cấp mới** (cải cách hành chính Việt Nam 2025, bỏ cấp huyện): `city` để null,
  `prov` = tỉnh/thành, ⇒ **`area` = phường/xã**.

⇒ Ánh xạ đang nằm trong mã (`area` ← quận/huyện) **ngược với ví dụ của chính hãng**, và hệ
**không gửi `city`** lượt nào (đo bằng ca thử A2).

**Đây là dữ kiện, không phải kết luận.** D-9 nói chưa chốt tới khi hãng xác nhận, và
`app/adapter_jt.py` không thuộc quyền ghi của AG-03 — nên lượt này **không đổi một ký tự nào**
của ánh xạ. Việc cần làm là **chặn**, và **nâng câu hỏi 28 lên ưu tiên cao nhất** (mục 7).

> **Đối chiếu để thấy mức độ nghiêm trọng:** Viettel Post phân biệt rạch ròi **ba** cấp và dùng
> **ID số** chứ không dùng chuỗi tên — `SENDER_PROVINCE` / `SENDER_DISTRICT` / `SENDER_WARD`
> (`mapping.py:_ROUTE_FIELDS`). Tức là cấp huyện và cấp xã **là hai thứ khác nhau** trong cùng
> thị trường, cùng thời điểm. Nhét nhầm cấp vào `area` của J&T không phải lỗi làm tròn — nó là
> **sai tuyến giao hàng**, và hãng có thể nhận đơn rồi mới giao sai.

### 5.3 Chốt chặn — thiết kế

Ba cửa, mọi môi trường khác `mock` phải qua đủ cả ba:

1. `ANH_XA_AREA_DA_XAC_NHAN` còn `False` ⇒ **chặn**. Mặc định là chặn, không phải cho qua kèm
   cảnh báo — D-9 nói "chưa chốt", nên trạng thái mặc định phải là từ chối.
2. Cờ `True` nhưng `NGUON_XAC_NHAN_AREA` rỗng / là chuỗi giữ chỗ / ngắn hơn 20 ký tự ⇒ **chặn**.
   Không có cửa này thì chốt tự vô hiệu hoá: sửa một chữ `False` → `True` là xong, không để lại
   dấu vết nào về việc hãng đã nói gì.
3. `CAP_HANH_CHINH_CHO_AREA` không thuộc `("quan-huyen", "phuong-xa")` ⇒ **chặn**.

`mock` **luôn đi qua** — bộ thử và dữ liệu demo cần chạy, và ở mock không có đơn thật nào bị
định tuyến sai.

**Vì sao cửa 2 dùng danh sách ĐEN còn cửa 3 dùng danh sách TRẮNG** (§12.2, câu hỏi phân biệt
*quên một dòng thì an toàn hay hỏng?*):

- Cửa 2: quên một từ giữ chỗ ⇒ lọt một chuỗi trông lạ nhưng vẫn do người thật gõ vào ⇒ **vô hại**.
  Còn danh sách trắng các trích dẫn "hợp lệ" thì không viết nổi, và quên một dạng là **chặn nhầm
  người đang làm đúng**. ⇒ danh sách đen.
- Cửa 3: quên một cấp khỏi danh sách ⇒ **bị chặn ⇒ an toàn**. Cho qua một cấp lạ ⇒ đơn đi sai
  tuyến, không ai báo. ⇒ danh sách trắng. Đây đúng ngoại lệ mà §12.2 đã nêu sẵn.

### 5.4 BẢN VÁ D-9 — đề xuất cho `app/adapter_jt.py` (AG-03 KHÔNG tự sửa file này)

Thân hàm dưới đây đã **chạy thật và kiểm thật** hôm nay: nó được chép nguyên văn vào
`app/thu/thu_anh_xa_area.py` làm **bản tham chiếu** và 9 ca nhóm B đều đạt. Cắm vào adapter thì
4 ca nhóm C tự bật và kiểm lại chính bản trong adapter.

**(a) Thêm vào `app/adapter_jt.py`, sau khối hằng đầu file:**

```python
# ── CHỐT CHẶN D-9: ánh xạ `area` CHƯA ĐƯỢC HÃNG XÁC NHẬN ──────────────────────
# Anh Thành chốt: "Chưa chốt cách ánh xạ `area` cho đến khi hãng xác nhận."
# Đo 15/10/2026 trên apiDoc/orderserve/create: ví dụ của hãng đặt QUẬN vào `city`
# và PHƯỜNG vào `area` — NGƯỢC với ánh xạ đang dùng. Xem docs/G12_VTP_KHAO_SAT.md §5.2.
ANH_XA_AREA_DA_XAC_NHAN = False
NGUON_XAC_NHAN_AREA = ""          # ai nói · ngày nào · kênh nào. Rỗng = chưa xác nhận.
CAP_HANH_CHINH_CHO_AREA = "quan-huyen"

CAP_HOP_LE = ("quan-huyen", "phuong-xa")
DAI_NGUON_TOI_THIEU = 20
TU_GIU_CHO = ("todo", "tbd", "n/a", "na", "?", "chua biet", "chưa biết", "xxx", "...",
              "sau", "updating", "fixme")


def chot_chan_anh_xa_area(moi_truong, da_xac_nhan=None, nguon=None, cap=None):
    """Chặn đường LIVE khi ánh xạ `area` chưa được J&T xác nhận (D-9).

    MOCK luôn đi qua. Mọi môi trường khác phải qua đủ ba cửa — lý do từng cửa và lý do
    chọn danh sách đen/trắng: docs/G12_VTP_KHAO_SAT.md §5.3.

    Tham số để None ⇒ đọc hằng của module (đường chạy thật). Truyền tường minh ⇒ dùng
    giá trị truyền vào (đường bộ thử), nhờ vậy ca thử không phải vá hằng toàn cục.
    """
    if moi_truong == "mock":
        return

    da = ANH_XA_AREA_DA_XAC_NHAN if da_xac_nhan is None else da_xac_nhan
    ng = NGUON_XAC_NHAN_AREA if nguon is None else nguon
    cp = CAP_HANH_CHINH_CHO_AREA if cap is None else cap

    def _chan(ly_do):
        raise loi_hang.NormalizedCarrierError(
            loi_hang.THAM_SO_SAI,
            thong_diep=(
                "CHỐT CHẶN D-9 — ánh xạ trường `area` của J&T CHƯA ĐƯỢC HÃNG XÁC NHẬN, "
                "nên không được gửi đơn thật. " + ly_do + " "
                "Cần J&T trả lời câu hỏi 28 (docs/JT_CAU_HOI_CHINH_THUC.md): với địa chỉ "
                "hành chính HAI CẤP của Việt Nam từ 2025, `prov` và `area` phải điền chính "
                "xác chuỗi nào, và có danh mục địa danh chuẩn tải về được không. "
                "Lưu ý: ví dụ trong chính tài liệu tạo đơn đặt QUẬN vào `city` và "
                "PHƯỜNG vào `area` — ngược với ánh xạ đang dùng. "
                "Có trả lời rồi thì đặt ANH_XA_AREA_DA_XAC_NHAN=True, điền "
                "NGUON_XAC_NHAN_AREA (ai nói · ngày nào · ở đâu) và CAP_HANH_CHINH_CHO_AREA."),
            hang="jt", thao_tac="createOrder")

    if not da:
        _chan("Cờ ANH_XA_AREA_DA_XAC_NHAN đang là False.")
    chuoi = str(ng or "").strip()
    if not chuoi:
        _chan("Cờ đã đặt True nhưng NGUON_XAC_NHAN_AREA còn RỖNG — "
              "không có nguồn thì không có xác nhận.")
    thap = chuoi.lower()
    if len(chuoi) < DAI_NGUON_TOI_THIEU or any(t == thap for t in TU_GIU_CHO):
        _chan("NGUON_XAC_NHAN_AREA đang là chuỗi giữ chỗ hoặc quá ngắn "
              f"({len(chuoi)} ký tự, cần tối thiểu {DAI_NGUON_TOI_THIEU}) — "
              "phải ghi rõ ai xác nhận, ngày nào, bằng kênh nào.")
    if cp not in CAP_HOP_LE:
        _chan(f"CAP_HANH_CHINH_CHO_AREA = {cp!r} không thuộc danh sách hợp lệ "
              f"{CAP_HOP_LE}.")
```

**(b) Gọi chốt ở ĐÚNG MỘT CHỖ** — ngay đầu `AdapterJT._dung_bizcontent_tao_don`, là hàm **duy
nhất** ghi `area` vào payload. Đặt ở đây chứ không ở `__init__` có lý do: `__init__` chỉ chặn
được lúc dựng adapter, còn chốt ở chỗ dùng thì **mọi đường mới** dẫn tới `bizContent` sau này
đều tự bị canh — kể cả khi ai đó mở `CHO_PHEP_LIVE` cho riêng thao tác chỉ-đọc.

```python
     def _dung_bizcontent_tao_don(self, don):
         """Dựng bizContent theo bảng tham số docs.
         ...
         """
+        # D-9: giả định `area` ← quận/huyện CHƯA được hãng xác nhận ⇒ không ra LIVE.
+        chot_chan_anh_xa_area(self.moi_truong)
         g = lambda k: str(don.get(k) or "").strip()      # noqa: E731
```

**(c) Sửa docstring** của `_dung_bizcontent_tao_don`: đoạn *"Em map `area` ← quận/huyện, vì đó
là cấp J&T dùng để chia tuyến ở Việt Nam"* nay đã có dữ kiện ngược lại. Đề nghị thay bằng:
*"`area` hiện lấy từ quận/huyện. Ví dụ của chính hãng đặt quận vào `city` và phường vào `area`
(đo 15/10/2026) ⇒ ánh xạ này nhiều khả năng SAI. Chốt chặn `chot_chan_anh_xa_area` không cho nó
ra LIVE cho tới khi J&T trả lời câu hỏi 28."*

**(d) KHÔNG làm trong bản vá này:** không đổi `TRUONG_HANH_CHINH`, không thêm `city`. Đổi ánh xạ
khi chưa có xác nhận chỉ là thay một giả định bằng một giả định khác — D-9 cấm đúng điều đó.

### 5.5 Nghiệm thu chốt chặn — số đo thật

```
$ python3 app/thu/thu_anh_xa_area.py
Ran 16 tests in 0.001s
OK (skipped=4)

==============================================================================
!! CHỐT CHẶN D-9 CHƯA ĐƯỢC CẮM VÀO app/adapter_jt.py
!! Logic đã kiểm ĐẠT trên bản tham chiếu (nhóm B), nhưng đường LIVE thật
!! VẪN CHƯA ĐƯỢC CANH. Nhóm C bỏ qua — bỏ qua không phải là đạt.
!! Bản vá: docs/G12_VTP_KHAO_SAT.md, mục 'Bản vá D-9'.
Tổng: 16 ca · hỏng 0 · lỗi 0 · bỏ qua 4
==============================================================================
```

| Nhóm | Ca | Kết quả | Kiểm cái gì |
|---|---|---|---|
| A — hiện trạng | 3 | **đạt** | Ghim `area` ← quận/huyện · hệ không gửi `city` · giả định mới chỉ được canh bằng docstring |
| B — logic chốt chặn | 9 | **đạt** | mock qua · cờ False chặn sandbox+production · thông điệp nêu đủ D-9/area/câu 28/HAI CẤP/city · True mà nguồn rỗng vẫn chặn · nguồn giữ chỗ chặn · nguồn quá ngắn chặn · cấp lạ chặn · đủ ba cửa thì **mở được** · mặc định module là chặn |
| C — đã cắm chưa | 4 | **BỎ QUA** | Chưa cắm. **Bỏ qua không phải đạt** |

Chạy trong bộ thử chung của dự án (`app/thu/chay_tat_ca.sh` tự dò `thu_*.py`):
`✓ thu_anh_xa_area.py  16 ca`, tổng dự án **810 ca · 23 bộ · không bộ nào hỏng**.

**Phạm vi của câu "0 hỏng":** công cụ là `unittest` chạy cục bộ, phạm vi là mã Python trong
`app/` + `gateway/`, chế độ MOCK, SQLite, một tiến trình. **NẰM NGOÀI:** `adapter_jt.py` thật
(chốt chưa cắm — nhóm C bỏ qua), mọi lượt gọi hãng, PostgreSQL, VPS, nhiều tiến trình, DOM.

---

## 6. ĐÍNH CHÍNH `docs/VIETTELPOST_REUSE_AUDIT.md`

> **AG-03 không sở hữu file này** (SHARED_CONTRACTS mục 22) nên **không sửa**. Dưới đây là từng
> câu sai và câu đúng thay thế, để AG-00 sửa.

**Gốc rễ của mọi câu sai dưới đây là một dòng duy nhất trong mục 0 của file đó:** nó khai phạm vi
là *"bản `4df8ce7` trên MacBook"* và **tổng số commit = 2**. Khai phạm vi là đúng luật — nhưng
**không ai kiểm bản clone trước khi tin nó**. Repo thật có 2 commit ở nhánh đó và **194 commit**
ở `develop`. Đúng dạng §12.1: *thứ dùng để kiểm chứng phải được kiểm TRƯỚC khi tin* — và bản
clone cũ **không báo lỗi gì, nó chỉ cũ**.

| # | Câu SAI (nguyên văn) | Ở đâu | Câu ĐÚNG thay thế |
|---|---|---|---|
| 1 | *"Lớp TÍCH HỢP HÃNG: không tái dùng được gì — nó là khung rỗng."* | mục 1 | "Trên `4df8ce7` lớp tích hợp là khung rỗng. Trên `develop` (`68e9642`) và `main` (`677cba9`) nó **hoàn chỉnh**: 2.391 dòng, đối chiếu tài liệu Partner 29/09/2026, có 21 mã trạng thái, 4 endpoint, 3 đường xác thực, xử lý webhook đầy đủ. **Tái dùng được DỮ KIỆN, không tái dùng được MÃ** (nền async khác hẳn) — chi tiết `docs/G12_VTP_KHAO_SAT.md` §4" |
| 2 | *"Commit mới nhất: `4df8ce7` … Tổng số commit: 2"* | mục 0 | "`4df8ce7` là đỉnh của nhánh `feature/shp-database`, **đi sau `develop` 194 commit** và sau `main` 174 commit. Repo có 20 nhánh. Đo bằng `gh api .../compare/…`" |
| 3 | *"**Authentication** ❌ KHUNG RỖNG — `auth.py` (11 dòng) … `raise NotImplementedError`"* | bảng mục 2 | "`auth.py` **141 dòng**: `POST /v2/user/Login` → `POST /v2/user/ownerconnect` (token dài, tài liệu ghi 1 năm) và `POST /v2/user/LoginVTP`; có đệm token, `invalidate()`, `can_refresh`" |
| 4 | *"**Vòng đời token** ❌ KHÔNG CÓ … Token chỉ là một biến cấu hình tĩnh"* | bảng mục 2 | "Có vòng đời: đệm trong tiến trình, `invalidate()` khi hãng trả `Token invalid`, **làm mới đúng một lần** (`api.py::_with_token`), và `can_refresh=False` khi dùng token tĩnh. Trường `data.expired` cố ý **không** diễn giải là hạn dùng vì tài liệu không định nghĩa" |
| 5 | *"**Services / Tính cước / Tạo đơn / Hủy đơn / Tracking** ❌ KHUNG RỖNG — `NotImplementedError`"* (5 dòng) | bảng mục 2 | "Bốn cái đầu **đã cài**: `getPriceAll` · `getPrice` · `createOrder` · `UpdateOrder TYPE=4`. **Tracking vẫn đúng là chưa có** — repo không cài `get_shipment` theo endpoint nào; trạng thái về chủ yếu qua webhook (câu B7)" |
| 6 | *"**Ánh xạ trạng thái** ❌ RỖNG HOÀN TOÀN — `STATUS_MAP = {}` … **Không có một mã trạng thái VTP nào**"* | bảng mục 2 | "`status_mapper.py` **148 dòng** với **21 mã chính thức**: 15 mã có ánh xạ, 6 mã (102, 202, 503, 505, 508, 550) **cố ý để `None`** kèm lý do từng mã; mã lạ không bao giờ mặc định về `IN_TRANSIT`" |
| 7 | *"**Webhook** ⚠️ CÓ CỬA, KHÔNG CÓ RUỘT — thân hàm là 6 dòng TODO … nhận gì cũng báo đã nhận"* | bảng mục 2 | "Đường webhook **đầy đủ, 1.000 dòng**: kiểm cỡ → giải JSON → so `TOKEN` bằng `hmac.compare_digest` → kiểm trường → vân tay SHA-256 → giành khoá chống trùng → lưu bản thô → ánh xạ → ACK; kèm migration `shp_0002` và job phát lại" |
| 8 | *"**Xử lý lỗi** ❌ KHÔNG CÓ … ném thẳng `httpx.HTTPStatusError`"* | bảng mục 2 | "`errors.py` 81 dòng, cây **10 lớp** (timeout · network · 4xx · 401/403 · 5xx · sai khuôn · nghiệp vụ · auth), `client.py` phân loại theo mã HTTP **và** theo phong bì `error:true`, có `redact()` che secret + mọi chuỗi dạng JWT" |
| 9 | *"**Client HTTP** ⚠️ KHUNG TỐI THIỂU (23 dòng) … header `Bearer`"* | bảng mục 2 | "`client.py` **174 dòng**. Token đi ở header **`Token`**, **không phải `Bearer`** — đây là dữ kiện về hãng, và câu cũ nói sai nó" |
| 10 | *"**Endpoint thật** ❌ KHÔNG CÓ … Scaffold cố ý không điền endpoint"* | bảng mục 2 | "Bốn endpoint có thật trong `mapping.py`, mỗi cái dẫn một trang tài liệu Partner, ngày kiểm 29/09/2026" |
| 11 | *"**Tests** ⚠️ CHIA HAI NỬA — `test_health_contract.py` = `assert True`"* | bảng mục 2 | "Có bộ thử thật cho lớp tích hợp: `test_vtp_status_mapper.py`, `test_vtp_provider_typed.py`, `test_webhook_vtp.py`, `test_webhook_to_shipment.py`, `test_webhook_production_wiring.py`, `test_webhook_persistence.py`" |
| 12 | *"`vtp_base_url = "https://partner.viettelpost.vn"` … Đây là **phỏng đoán của repo đó**, không phải trích từ tài liệu Partner"* | mục 3 | "Repo đó nay có **hai** hằng host: `VTP_DEV_BASE_URL = "https://partnerdev.viettelpost.vn"` và `VTP_PRODUCTION_BASE_URL = "https://partner.viettelpost.vn"`; `.env.example` mặc định trỏ **dev**. Không còn là phỏng đoán — host dev đã được gọi thật 02/10/2026" |
| 13 | *"Nút thắt thật: TÀI LIỆU PARTNER API chính thức của Viettel Post + credentials test. Không có hai thứ đó thì adapter VTP phải ở nguyên mức mock"* | mục 5 | "**Tài liệu không còn là nút thắt** — `partner2.viettelpost.vn/document/*` đã đọc được và đã được đối chiếu từng trang. Nút thắt còn lại **chỉ là credentials** + `V-G09-01`. Vế 'phải ở nguyên mức mock' vẫn đúng, nhưng vì lý do khác" |
| 14 | *"VTP: **0 và 0** — và con số 0 đó là 'chưa đọc được tài liệu'"* | mục 5 | "**0 mã trạng thái và 0 mã lỗi là đúng VỚI DỰ ÁN NÀY**, nhưng lý do sai: không phải 'chưa đọc được tài liệu' mà là **chưa mang sang**. 21 mã trạng thái đã có sẵn, chép được ngay. Riêng mã lỗi thì VTP **không công bố bảng mã dạng số** — chỉ có phong bì `error:true` + 4 chuỗi thông điệp auth" |
| 15 | *"Chốt: repo `vip-viettelpost` có còn là nguồn tham chiếu nữa không — Nó dừng ở commit 29/09/2026 và lớp provider chưa từng được điền"* | mục 6 việc 4 | "Repo đó **đang sống**: `pushed_at` 14/10/2026, `develop` 14/10, 20 nhánh. Lớp provider **đã được điền** và đã chạy thật trên `partnerdev` 02/10/2026. Nó **là** nguồn tham chiếu tốt nhất hiện có cho VTP" |

**Câu trong file đó vẫn ĐÚNG, giữ nguyên:** mục 4 vế *"Mã: không"* (nền kỹ thuật khác hẳn —
vẫn đúng, và nay còn đúng hơn vì lớp mới toàn `async`); và bốn ý tưởng ở mục 4 (secret là con
trỏ · chống trùng bằng ràng buộc CSDL · `redaction` đen/trắng có lý do · SAVEPOINT).

### Cùng một câu sai còn nằm ở BỐN chỗ nữa — đây mới là phần nguy hiểm

Sai trong một file tài liệu thì còn đỡ. Câu sai này đã **lan vào chú thích mã nguồn**, và chú
thích mã là thứ người sau đọc để quyết định có làm tiếp hay không.

| # | Chỗ | Câu sai | Sửa thành |
|---|---|---|---|
| 1 | `app/adapter_vtp.py`, khối chú thích đầu file | kết luận repo nguồn là khung rỗng | G09 đã nêu ở bản vá **P5**; lượt này xác nhận lại trên `develop`, **vẫn chưa sửa** |
| 2 | `app/trang_thai_hang.py` **dòng 49–53** | *"lớp tích hợp hãng ở repo đó là khung rỗng, `STATUS_MAP = {}`, không có mã trạng thái VTP nào"* — và nó **dẫn thẳng** `docs/VIETTELPOST_REUSE_AUDIT.md` làm căn cứ | "Repo đó có **21 mã trạng thái VTP** ở `app/providers/viettel_post/status_mapper.py` (`develop` `68e9642`), nguồn `partner2.viettelpost.vn/document/webhook`. Chép sang được — xem `docs/G12_VTP_KHAO_SAT.md` §4" |
| 3 | `app/trang_thai_hang.py` **dòng 52–53** | *"Nút thắt thật là TÀI LIỆU PARTNER API + credentials"* | "Nút thắt còn lại **chỉ là credentials** — tài liệu Partner đã đọc được và đã đối chiếu" |
| 4 | `app/webhook.py` **dòng 150** | `"vtp": None,  # chưa có tài liệu Partner API → không nhận callback thật` | "`"vtp": None,  # khuôn callback ĐÃ CÓ tài liệu (so TOKEN trong thân với bí mật chung, không HMAC) — chưa cài sơ đồ, không phải chưa có tài liệu`" |
| 5 | `docs/G09_FINAL_REPORT.md` mục 4 | câu *"`origin/main` … có một lớp tích hợp Viettel Post hoàn chỉnh"* **đúng**, nhưng câu ngầm định "`main` là bản mới nhất" **thiếu** | Đỉnh thật là `develop`. Đính chính ở mục 1 của file này |

AG-03 không sở hữu file nào trong năm dòng trên — đây là **đề xuất cho AG-00**.

> **Vì sao đáng ghi riêng:** chỗ 2 và 3 cho thấy một câu sai trong tài liệu **không nằm yên** —
> nó được trích dẫn, rồi bản trích dẫn trở thành căn cứ cho quyết định "chưa làm VTP được".
> Sửa mỗi file gốc là **sửa thiếu**. Đây đúng là bước 4 của §12.2: *sửa xong hỏi — cấu trúc này
> còn hỏng kiểu đó ở đâu nữa?*

---

## 7. D-4 — GIỮ NGUYÊN, KHÔNG THÊM MÃ NÀO

Mã J&T `110` và nghi vấn hai bộ mã: **không thêm một mã nào** vào `app/trang_thai_hang.py` trong
lượt này. Đo lại để xác nhận còn đúng: hệ vẫn **không áp trạng thái nào** cho `110` và đánh dấu
cần soát bằng người.

Thông tin mới tìm được trong lượt này **đi vào tài liệu câu hỏi, không vào mã**:

- Mâu thuẫn `104` của **Viettel Post** (bảng trạng thái nói là trạng thái cuối, đoạn "Lưu ý" nói
  không) — **ca mã nhập nhằng thứ hai**, cùng họ với J&T `110`. Thuộc VTP nên không chạm bảng
  J&T; ghi vào mục 4 của file này để khi mang 21 mã sang thì vào sổ `NHAP_NHANG` ngay từ đầu.

---

## 8. BLOCKED — mỗi mục nêu CHÍNH XÁC cái còn thiếu

| # | Việc | Thiếu chính xác cái gì | Xin ai |
|---|---|---|---|
| B1 | Gọi API J&T/VTP (sandbox hoặc live) | Mã việc **`V-G09-01`**; J&T cần thêm **`V-13906-05`**. SHARED_CONTRACTS mục 25 ghi **CHƯA CẤP** | anh Thành |
| B2 | Chốt ánh xạ `area` (D-9) | **Trả lời của J&T cho câu hỏi 28.** Không có nguồn nào khác thay được — hai cách đọc tài liệu cho hai kết quả khác nhau | J&T, qua bước 联调测试 |
| B3 | Cắm chốt chặn D-9 vào `adapter_jt.py` | Quyền ghi file đó. AG-03 không sở hữu. Bản vá đã viết + đã kiểm ở §5.4–5.5 | AG-00 |
| B4 | Credentials J&T | 4 trường, **2 nguồn khác nhau**: `apiAccount`+`privateKey` (nền tảng, sau 开发者认证) và `customerCode`+`password` (**bưu cục hợp tác cấp**). Xem `docs/G12_JT_DANG_KY.md` | J&T + bưu cục |
| B5 | Credentials VTP | `vtp_token` **hoặc** `vtp_username`+`vtp_password` cho `partnerdev.viettelpost.vn` | Viettel Post / nội bộ |
| B6 | Mang 21 mã trạng thái VTP sang | Không thiếu gì về dữ kiện — thiếu **quyền ghi** `app/trang_thai_hang.py` và một quyết định của AG-00 về 6 mã cố ý không ánh xạ | AG-00 |
| B7 | Bảng mã lỗi VTP | **VTP không công bố bảng mã lỗi dạng số.** Cái thay thế được: phong bì `error:true` + 4 chuỗi thông điệp auth. Cần AG-00 quyết có chấp nhận cách phân loại đó không | AG-00 |
| B8 | Nhãn vận đơn VTP | Trang tài liệu in nhãn của VTP — **chưa đọc được trang nào** | Viettel Post |
| B9 | Tra vận đơn VTP theo mã | Xác nhận VTP **có** API tra theo mã hay không (câu B7 của bộ câu hỏi VTP) | Viettel Post |
| B10 | URL công khai nhận callback | **`V-G11-01`** (triển khai staging lên VPS) — **CHƯA CẤP** | anh Thành |

---

## 9. RỦI RO CỐ Ý BỎ QUA — ghi ra theo §12.1

1. **Chốt chặn D-9 chưa cắm vào đường chạy thật.** Hôm nay `CHO_PHEP_LIVE=False` che cho nó, nên
   rủi ro bằng 0 **trong hôm nay**. Rủi ro thật nằm ở **ngày Owner mở `CHO_PHEP_LIVE`**: nếu lúc
   đó chốt vẫn chưa cắm, giả định `area` ra thẳng LIVE. Hai ổ khoá này **không độc lập**, và
   đó là điều cần sửa. Vá đúng: AG-00 cắm bản vá §5.4 **trước** mọi lượt mở `CHO_PHEP_LIVE`.
2. **Không đổi ánh xạ `area` dù có dữ kiện mạnh rằng nó sai.** Cố ý: D-9 cấm chốt khi hãng chưa
   xác nhận, và đổi sang `phuong-xa` lúc này chỉ là thay giả định này bằng giả định khác. Rủi ro
   bỏ qua: nếu hệ chạy LIVE trước khi hãng trả lời thì đơn đi sai tuyến — **chốt chặn ở §5.4
   chính là cách vá rủi ro này**.
3. **Chỉ đọc một trang tài liệu J&T trong lượt này** (`orderserve/create`). Bảy trang còn lại
   lấy theo `docs/JT_CAU_HOI_CHINH_THUC.md` ngày 15/10. Rủi ro: một trang khác có thể định nghĩa
   `area` khác nữa. Vá đúng: câu hỏi 28 hỏi thẳng hãng, không đọc thêm trang.
4. **Bản clone trong scratchpad là `--depth=50`.** Không đọc được lịch sử trước 50 commit. Không
   ảnh hưởng kết luận (mọi kết luận nói về cây làm việc hiện tại), nhưng ghi ra để ai cần đào
   lịch sử thì biết phải clone lại đầy đủ.
5. **Không kiểm 18 nhánh còn lại.** Chỉ đo `main`, `develop`, `4df8ce7`. Có thể có nhánh đi
   trước `develop`. Rủi ro thấp (`develop` là nhánh tích hợp, `pushed_at` khớp ngày của nó),
   nhưng **chưa đo** — và đây đúng là loại sai mà lượt này vừa đi sửa.

---

## 10. VIỆC NÊN LÀM TIẾP, theo thứ tự

1. **AG-00 cắm bản vá §5.4** vào `app/adapter_jt.py`. Rẻ, không đổi hành vi MOCK, và là thứ duy
   nhất chặn được D-9 bằng cấu trúc. Nghiệm thu: `python3 app/thu/thu_anh_xa_area.py` phải ra
   **16 ca đạt, 0 bỏ qua**.
2. **Gửi bộ câu hỏi J&T** theo thứ tự ưu tiên mới ở `docs/G12_JT_DANG_KY.md` §5 — câu 28 lên
   **nhóm 1**.
3. **AG-00 sửa 15 câu ở §6** trong `docs/VIETTELPOST_REUSE_AUDIT.md`, và khối chú thích đầu
   `app/adapter_vtp.py` (bản vá P5 của G09, vẫn chưa làm).
4. **Mang 21 mã trạng thái VTP sang** `app/trang_thai_hang.py`, kèm 6 mã cố ý `None` và ca `104`
   vào sổ `NHAP_NHANG`.
5. Bắt đầu thủ tục đăng ký J&T theo `docs/G12_JT_DANG_KY.md` — bước 1–2 làm được ngay, không
   cần chờ quyết định nào.
