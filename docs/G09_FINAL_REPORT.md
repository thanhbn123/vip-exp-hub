# G09 — BÁO CÁO NGHIỆM THU: J&T / VIETTEL POST READINESS

**Tác tử:** AG-03 CARRIER INTEGRATION ENGINEER · **Ngày:** 15/10/2026
**Worktree:** `~/code/veh3-g09-carrier`, nhánh `agent/g09-carrier`, nền `143084b`
**Máy đo:** MacBook Pro (macOS, `python3` của Command Line Tools, `node` của Homebrew)

---

## 0. KẾT LUẬN — ba dòng bắt buộc

```
G09 LOCAL READY = PASS
G09 SANDBOX     = BLOCKED
G09 LIVE        = BLOCKED
```

### `G09 LOCAL READY = PASS` — đo bằng gì, và cái gì NẰM NGOÀI

- **Đo bằng:** `python3 app/harness_hang.py` (bộ harness mới, chế độ MOCK) → **95 ca đạt · 0
  hỏng · 3 bỏ qua**; cộng với `python3 app/thu/thu_harness_hang.py` → **57/57 đạt**; và toàn bộ
  bộ thử sẵn có của dự án chạy lại không hỏng dòng nào (số đo ở mục 7).
- **Phạm vi:** mã Python trong `app/` của dự án này, chạy cục bộ, **không có mạng**, trên CSDL
  thử riêng (`VIP_HUB_DATA` trỏ thư mục tạm).
- **NẰM NGOÀI phạm vi — nói thẳng:** hãng thật có chấp nhận chữ ký không · tài liệu hãng có
  đúng không · sandbox hãng có sống không · callback hãng ký bằng khoá nào · địa danh thật có
  khớp danh mục hãng không. **Không một dòng nào trong báo cáo này được đọc là "J&T/VTP đã chạy
  được".**

### `G09 SANDBOX = BLOCKED` — thiếu chính xác bốn thứ, mỗi hãng

Đo bằng `harness_hang.thieu_gi_de_chay("SANDBOX", hang)` — cùng một hàm mà harness dùng để từ
chối chạy, nên báo cáo và lúc chạy không thể nói hai điều khác nhau.

| # | Thiếu gì | Xin ai |
|---|---|---|
| 1 | mã việc **`V-G09-01`** (gọi API hãng) — `SHARED_CONTRACTS.md` mục 25 ghi **CHƯA CẤP**; J&T còn cần thêm **`V-13906-05`** | anh Thành |
| 2 | `VIP_HUB_HARNESS_NGUOI_DUYET` — tên người chịu trách nhiệm lượt chạy | — |
| 3 | file credentials (`VIP_HUB_HARNESS_CRED_FILE`): J&T cần `apiAccount`+`privateKey`+`customerCode`+`password`; VTP cần `vtp_token` **hoặc** `vtp_username`+`vtp_password` | J&T: bưu cục hợp tác · VTP: Viettel Post hoặc nội bộ |
| 4 | `CHO_PHEP_LIVE = False` trong `app/adapter*.py` — khoá chốt cứng, **G09 CHỈ ĐỌC file đó và không đề nghị mở ở đợt này** | chỉ Owner, qua AG-00 |

### `G09 LIVE = BLOCKED` — bốn thứ trên, cộng thêm

| # | Thiếu gì |
|---|---|
| 5 | **`PhieuDuyetLive` riêng cho TỪNG thao tác ghi** (`createOrder`, `cancelOrder`): người duyệt · mã việc · mã tham chiếu · hạn dùng. Một cờ môi trường là **không đủ**, và phiếu dùng được đúng một lần |
| 6 | hợp đồng dịch vụ thật với từng hãng |
| 7 | URL công khai cho callback — thuộc **V-G11-01, CHƯA CẤP** |

**G09 KHÔNG hoàn thành LIVE, và không có phần nào của G09 được đánh dấu là hoàn thành LIVE.**

---

## 1. G09.1 — KHẢO SÁT CÁI ĐANG CÓ

Đọc toàn bộ: `app/adapter.py`, `adapter_jt.py`, `adapter_vtp.py`, `transport.py`,
`loi_hang.py`, `trang_thai_hang.py`, `webhook.py`, `polling.py`, `gioi_han.py`, phần
`gui_don`/`doi_soat_don`/`thao_tac_doi_soat` của `don_hang.py`, bốn hàm cred của `bao_mat.py`.

| Thành phần | Trạng thái | Đo bằng gì |
|---|---|---|
| **CarrierAdapter** (hợp đồng chung) | **ĐẠT CHUẨN — không viết lại** | 6 hàm chuẩn + `getCapabilities()` + `normalizeTrackingStatus()`; ba kết cục ok/từ-chối/không-biết tách hẳn; `CHO_PHEP_LIVE` chặn ngay trong `__init__`. Ca A1–A6 của harness |
| **J&T Adapter** | **ĐẠT CHUẨN ở phần chữ ký**, **THIẾU ở phần tham số nghiệp vụ** | chữ ký/headers/timestamp đúng tài liệu (ca B1–B8). Nhưng `bizContent` thiếu/sai 5 trường — mục 9, bản vá P1 |
| **VTP Adapter** | **MOCK hoàn toàn; phần chú thích đang NÓI SAI** | mọi hàm chỉ có nhánh mock; khối chú thích đầu file kết luận repo `vip-viettelpost` là khung rỗng — kết luận đó dựa trên bản clone **đi sau 174 commit**. Mục 5 |
| **CarrierAccount + dịch vụ credentials** | **ĐẠT CHUẨN — không viết lại** | bản mã `v3$<key_id>$…`, cách ly theo `(tenant_id, hang)`; tenant khác và hãng khác không giải mã được. Ca F1–F6 |
| **CarrierCapabilities** | **ĐẠT CHUẨN**, một chỗ khai quá | `getCapabilities()` trả bản sao, khai đủ 7 khoá, `capability=False` trả lời tử tế. Nhưng `adapter_vtp` khai `getOrder=True` mà **không có tài liệu nào** chống lưng — mục 9, bản vá P5 |
| **OrderService** (`gui_don` / `doi_soat_don`) | **ĐẠT CHUẨN — và là phần chắc nhất của hệ** | chiếm đơn bằng **một** `UPDATE` có điều kiện (không đọc-rồi-ghi); timeout ⇒ giữ `dang_gui` + cờ đối soát; **chỉ** mã `KHONG_TIM_THAY` mới kết luận "hãng chưa nhận". Ca H1–H4 |
| **Webhook Gateway** | **ĐẠT CHUẨN** | sơ đồ xác thực chọn ở **phía máy chủ** theo (hãng, môi trường) — chữ ký hàm `chon_so_do(tk_row)` không nhận header/payload nên người gửi không có đường chọn; mốc thời gian của hãng; DLQ; replay có trần. Ca I1–I5 |
| **transport** (timeout/retry) | **ĐẠT CHUẨN — xác minh lại còn đúng** | `createOrder`/`cancelOrder` mặc định `so_lan=1, duoc_thu_lai=False`; chỉ mở thử lại khi hãng có khoá chống trùng riêng. Ca C1–C7 |
| **polling** | **ĐẠT CHUẨN** | lô 30 cho J&T, trần riêng từng tenant, ngắt mạch, khoảng cách tối thiểu 30 s. Ca G3–G6 |
| **loi_hang** | **ĐẠT CHUẨN cho J&T, RỖNG cho VTP** | `JT_MA_LOI` có **27 mục** (26 mã lỗi + mã `1` thành công); `BANG_MA_LOI` **không có khoá `vtp`**. Ca D0–D9 |

**Không viết lại gì trong số trên.** G09 chỉ thêm `app/harness_hang.py`,
`app/thu/thu_harness_hang.py`, `admin/carrier_health.js` và tài liệu.

---

## 2. G09.2 — J&T EXPRESS: BẢNG PHÂN LOẠI SÁU MỨC

**Nguồn:** `open.jtexpress.vn/apiDoc`, đọc bằng **trình duyệt thật** ngày **15/10/2026** (trang
là SPA, `curl` trả về khung rỗng — xác nhận lại hiện tượng đã ghi ở đợt trước).

Mức trong bảng do `harness_hang.bang_san_sang()` **sinh ra từ phép đo**, không gõ tay: mức nền
suy từ dữ kiện trong mã, và chỉ được nâng lên `MOCK VERIFIED` khi lượt chạy có **đúng các ca
kiểm phủ hạng mục đó** đạt. Có ca thử canh điều này (`E_BangSauMuc.test_e3`, `test_e5`).

| Hạng mục | Mức | ĐO BẰNG GÌ |
|---|---|---|
| **Xác thực** | `DOCUMENTED` | Đọc `apiDoc/orderserve/create` 15/10/2026: hai lớp tài khoản — `apiAccount`/`privateKey` ở header (xem trong 控制台), `customerCode`/`password` trong `bizContent` (bưu cục cấp). **Chưa có lượt xác thực thật nào**, nên không hơn `DOCUMENTED` |
| **Chữ ký request** | `MOCK VERIFIED` | Ca **B1–B5, B7** đạt ở chế độ MOCK. B1 **tính lại công thức ngay trong ca kiểm** (`base64(md5-bytes(bizContent+privateKey))`) chứ không gọi lại hàm của adapter; B2 dựng bản **sai cố ý** (base64 của md5-hex) và khẳng định adapter không ra bản đó; B5 dựng mốc UTC+7 cố định rồi so |
| **Tạo đơn** | `MOCK VERIFIED` | Ca **A4, B8, C3** đạt. Phạm vi hẹp: chỉ chứng minh adapter **dựng đúng gói yêu cầu** và **phân biệt đúng ba kết cục**. **KHÔNG** chứng minh hãng chấp nhận gói đó — xem bản vá P1, `bizContent` còn thiếu trường bắt buộc |
| **Huỷ đơn** | `DOCUMENTED` | `apiDoc/orderserve/cancel`: `POST /webopenplatformapi/api/order/cancelOrder`, `bizContent` cần `customerCode`+`password`+`txlogisticId`+`reason` (`billCode` tuỳ chọn). Adapter **chỉ có nhánh mock**, chưa dựng yêu cầu thật ⇒ **không** có ca kiểm nào nâng được |
| **Tra vận đơn** | `MOCK VERIFIED` | Ca **G3, H1** đạt. `POST /api/logistics/trace`, `billcodes` ngăn cách bằng dấu phẩy, **tối đa 30 mã/lượt** — hằng `SO_VAN_DON_MOI_LUOT = 30` khớp tài liệu và khớp mã lỗi `145003502` |
| **Báo giá** | `DOCUMENTED` | `apiDoc/fees/calculatingFees`: `POST /api/spmComCost/getComCost`, trả `price`/`codFee`/`insuranceFee` (VND). **Hằng endpoint này CHƯA có trong `adapter_jt.py`**; `getShippingFee` hiện là công thức bịa của bộ mô phỏng (`15000 + (kl//500)*5200`) — bản vá P2 |
| **Nhãn vận đơn** | `DOCUMENTED` | `apiDoc/vip/printOrder`: `POST /api/order/printOrder`, 10 khổ giấy (A4/A5/A6/A7/K80 và bản dành cho một-phiếu-nhiều-kiện), trả `base64EncodeContent` + `urlContent`. Adapter trả chuỗi `"MOCK-PDF"` ⇒ không nâng. *(Trang `批量打印面单` có trong trình đơn nhưng **chưa mở được nội dung** — ghi ra để không ai tưởng đã đọc)* |
| **Mã lỗi** | `MOCK VERIFIED` | Ca **D1, D4, D7, D8, D9** đạt. `loi_hang.JT_MA_LOI` có **27 mục** đo bằng `len()`: **23 dòng** chép từ `apiDoc/errorCode/index` (gồm mã `1` = thành công), cộng 4 mã lấy từ bảng riêng của từng API (`0`, `145003031`, `145003082`, `145003089`). **NẰM NGOÀI:** đây là số mã **đã đọc được từ tài liệu công khai**, **không phải** số mã J&T thực sự có |
| **Callback / webhook** | `DOCUMENTED` | `apiDoc/logistics/statusFeedback` (轨迹回传): hãng chủ động POST về URL khách cung cấp, **cùng ba header** `apiAccount`/`digest`/`timestamp`, thân form có `bizContent`. `webhook.xac_thuc_jt_digest` cài theo đúng công thức đó. **Không lên được MOCK VERIFIED** vì tài liệu **không nói callback ký bằng khoá nào** — câu hỏi 6–8 gửi hãng |
| **Giới hạn tần suất** | **`BLOCKED`** | Đọc hết 23 dòng của `apiDoc/errorCode/index`: **không có mã nào** cho vượt hạn mức gọi. Giới hạn duy nhất tìm được là `145003502` (quá 30 mã vận đơn/lượt) — đó là trần **kích thước một lượt**, **không phải** trần tần suất. `QUA_HAN_MUC` của J&T hiện chỉ đến từ HTTP 429 |

---

## 3. G09.3 — MÃ J&T `110`

### Hai nghĩa, đo trực tiếp hôm nay trên CÙNG MỘT TRANG

`open.jtexpress.vn/apiDoc/logistics/query`:

| Chỗ | `110` là gì |
|---|---|
| Bảng tham số `scanTypeCode` | `Arrival(110, "到件扫描")` — hàng đến kho, **đang đi bình thường** |
| Ví dụ trả lời ngay dưới bảng | `"scanTypeCode": 110, "scanTypeName": "Quét kiện vấn đề"`, `desc` = *"đã quét mã bất thường … Nguyên nhân vấn đề【】"* |

### Dữ kiện MỚI đo được hôm nay (đợt trước chưa có)

Ví dụ trả lời trên trang `/logistics/query` dùng **một bộ mã khác hẳn** bảng tham số, và nội
dung là **tiếng Việt, trông như dữ liệu thật của môi trường Việt Nam** (tên bưu cục, tên nhân
viên, số điện thoại, mã vận đơn `842800765741`):

| Mã trong ví dụ | Tên trong ví dụ | Mã tương đương ở bảng tham số |
|---|---|---|
| `10` | Nhận hàng | `106` 快件揽收 |
| `50` | Gửi hàng | `109` 发件扫描 |
| `92` | **Hàng đến** | `110` 到件扫描 |
| `94` | Quét phát hàng | `112` 出仓扫描 |
| `100` | Ký nhận | `113` 快件签收 |
| `110` | **Quét kiện vấn đề** | `110` **到件扫描** |

**Điều này làm yếu hẳn lập luận "bảng tham số là phần chuẩn tắc nên tin bảng"** đang ghi trong
`app/trang_thai_hang.py`. Trong bộ mã của ví dụ, "hàng đến" đã là `92`, nên `110` ở đó **thật
sự** là kiện có vấn đề. Và bộ mã của ví dụ mới là bộ trông giống dữ liệu production Việt Nam.

### Hệ thống đang xử thế nào — xác minh lại, còn đúng

Đo bằng ca **E2, E3, E4, E5** (đạt):

- `tth.quyet_dinh("jt", 110)` → `trang_thai_ap = None`, `nhan = "AMBIGUOUS"`, `can_soat = True`,
  `do_tin_cay = "nhap_nhang"`. **Đơn mang mã 110 KHÔNG tiến trạng thái.**
- Giữ đủ dấu vết: `ma_goc` · `mo_ta_goc` · `su_kien_hang_goc` · `nguon_tai_lieu` ·
  `phien_ban_tai_lieu` (`doc-2026-10-14`) · `do_tin_cay` · `nhan_luc` (có múi giờ +07) ·
  `ghi_chu` · cả **hai nghĩa** với nguồn của từng nghĩa.
- `NGHIA_DA_CHOT` **rỗng** — đúng hiện trạng, chưa ai đối chiếu được với hãng.
- `chot_nghia()` đòi `nguoi_chot` + `can_cu`, và **chặn cứng** mọi nghĩa dẫn tới trạng thái
  hoàn tất.
- Giao diện **không** cho bấm chốt nghĩa (`cho_phep_chot_tren_man: false` trong
  `admin/carrier_health.js`).

**Không tự chọn nghĩa. Không cập nhật trạng thái cuối theo suy đoán.** Câu hỏi để gửi hãng:
`docs/JT_CAU_HOI_CHINH_THUC.md` câu 1–5.

### RỦI RO CỐ Ý BỎ QUA — ghi ra theo §12.1

**Nếu hãng thật đẩy theo bộ mã của ví dụ** (`10/50/92/94/100/110`), thì năm mã `10`, `50`, `92`,
`94`, `100` hiện **không có trong `JT_MA`** ⇒ hệ thống coi là **mã lạ** ⇒ **không đổi trạng
thái gì cả**, chỉ ghi nhận và đánh dấu cần soát.

- Mặt an toàn: không có đơn nào bị cập nhật sai.
- **Mặt hỏng:** mã `100` ("Ký nhận" = đã giao) sẽ **không bao giờ** đưa đơn về
  `giao_thanh_cong`. Đơn đã giao xong vẫn nằm ở "đang giao" **vĩnh viễn**, và việc này **không
  báo lỗi gì** — đúng dạng hỏng im lặng của §12.2.
- Vì sao vẫn bỏ qua đợt này: thêm bộ mã thứ hai vào `JT_MA` là **sửa `app/trang_thai_hang.py`**,
  file G09 **CHỈ ĐỌC**. Đề xuất bản vá **P4** ở mục 9, ưu tiên **CAO**.

---

## 4. G09.4 — VIETTEL POST: BẢNG PHÂN LOẠI SÁU MỨC

> **PHÁT HIỆN LỚN NHẤT CỦA G09.** Bản clone `~/code/vip-viettelpost` đứng ở `4df8ce7`, còn
> `origin/main` là `677cba9` — **đi sau 174 commit**. Đo bằng
> `gh api repos/thanhbn123/vip-viettelpost/compare/4df8ce7...main` → `{"ahead": 174,
> "behind": 0}`. Nhánh `main` **có một lớp tích hợp Viettel Post hoàn chỉnh**, đối chiếu tài
> liệu Partner chính thức ngày 29/09/2026, và **đã chạy thật trên `partnerdev` ngày
> 02/10/2026** (tạo đơn thử `303296591832` rồi huỷ).
>
> `docs/VIETTELPOST_REUSE_AUDIT.md` và chú thích đầu `app/adapter_vtp.py` nói repo đó là **khung
> rỗng**. Câu đó **đúng với `4df8ce7`, sai với `main`** — và không ai kiểm bản clone trước khi
> tin nó. Đúng dạng §12.1: *thứ dùng để kiểm chứng phải được kiểm trước khi tin.*
> Chi tiết + danh sách yêu cầu bổ sung: `docs/VTP_YEU_CAU_BO_SUNG.md`.

Mọi dòng dưới đây đọc bằng `gh api .../contents/<file>?ref=main` — **CHỈ ĐỌC**, không clone,
không sửa, không commit, không push, không lấy token nào.

| Hạng mục | Mức | ĐO BẰNG GÌ |
|---|---|---|
| **Xác thực** | `DOCUMENTED` | `app/providers/viettel_post/auth.py` trên `main` dẫn `partner2.viettelpost.vn/document/token-authen`: `POST /v2/user/Login` (USERNAME/PASSWORD → token ngắn), `POST /v2/user/ownerconnect` (header `Token` → token dài, tài liệu ghi 1 năm), `POST /v2/user/LoginVTP`. **`app/adapter_vtp.py` của dự án NÀY chưa cài đặt gì** |
| **Chữ ký request** | **`BLOCKED`** | Đo được: VTP **không có** sơ đồ ký request — xác thực bằng header `Token`. Không phải "chưa tìm ra cách ký" mà là **hãng không ký**. Ghi `BLOCKED` thay vì bỏ trống để không ai tưởng đã xong |
| **Tạo đơn** | `DOCUMENTED` | `POST /v2/order/createOrder` (`mapping.CREATE_ORDER_PATH`), nguồn `partner2.../create-order-id-address`. `adapter_vtp` là MOCK hoàn toàn |
| **Huỷ đơn** | `DOCUMENTED` | `POST /v2/order/UpdateOrder` với `TYPE = 4`; tài liệu chỉ cho huỷ khi `ORDER_STATUS < 200` |
| **Tra vận đơn** | `DOCUMENTED` | Trạng thái về **chủ yếu qua webhook**. Repo kia **không** cài `get_shipment` theo endpoint tài liệu nào ⇒ chưa rõ VTP có API tra theo mã không (câu B7). `adapter_vtp.getOrder/trackOrder` là mock |
| **Báo giá** | `DOCUMENTED` | `POST /v2/order/getPrice` (tính cước) và `POST /v2/order/getPriceAll` (danh sách dịch vụ) |
| **Nhãn vận đơn** | **`BLOCKED`** | **Chưa đọc được** trang tài liệu nào của VTP về in nhãn, repo `vip-viettelpost` cũng không có. Không suy đoán. Ghi chú: `adapter_vtp` đang khai `getShippingLabel=True` — khai quá thứ chứng minh được (bản vá P5) |
| **Mã lỗi** | **`BLOCKED`** | `loi_hang.BANG_MA_LOI` **không có khoá `vtp`** (đo bằng `"vtp" in loi_hang.BANG_MA_LOI` → `False`). Lỗi VTP hiện **chỉ** phân loại được theo HTTP status. Repo kia có phân loại theo phong bì `"error": true` — mang sang được (bản vá P6) |
| **Callback / webhook** | `DOCUMENTED` | `partner2.viettelpost.vn/document/webhook`: `POST`, `application/json;charset=UTF-8`, thân `{"DATA": {"ORDER_NUMBER", "ORDER_STATUS", "ORDER_STATUSDATE", …}, "TOKEN"}`. **Xác thực = so sánh hằng thời gian trường `TOKEN` trong THÂN với secret chung; không có HMAC/chữ ký.** 21 mã trạng thái chính thức. Cửa webhook của dự án này đặt `SO_DO_THEO_HANG["vtp"] = None` ⇒ **chưa cài**, nên không lên mức cao hơn |
| **Giới hạn tần suất** | `DOCUMENTED` | Tài liệu webhook nêu VTP **thử lại tối đa 5 lần** tới khi nhận HTTP 200. Không thấy trần tần suất gọi API (câu B9) |

### Đính chính câu "chữ ký webhook VTP là BLOCKED"

Câu cũ đúng về kết luận (chưa mở được cửa), **sai về lý do**. Lý do thật: **Viettel Post không
ký webhook.** Cơ chế chính thức là bí mật chung đặt trong thân yêu cầu. Điều này có hệ quả thiết
kế riêng (bí mật đi qua thân ⇒ lộ trong log mọi lớp trung gian) — câu hỏi B5/B6.

### 21 mã trạng thái VTP — có sẵn, chưa mang sang

Repo kia ghi đủ: **15 mã có ánh xạ rõ**, **6 mã cố ý không ánh xạ** (102, 202, 503, 505, 508,
550), và **một mâu thuẫn nội tại của chính tài liệu VTP**: bảng trạng thái đánh dấu `104` là
trạng thái cuối, nhưng đoạn *"Lưu ý"* liệt kê trạng thái cuối là 101/107/201/501/503/504 —
**không có 104**, trong khi 104 đứng trước 200 theo nghiệp vụ. Đây là **một ca mã nhập nhằng
thứ hai**, cùng họ với J&T 110, và nên vào sổ `NHAP_NHANG` khi mang sang (bản vá P4b).

---

## 5. G09.5 — VẬN HÀNH API

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **Chính sách timeout** | **ĐÃ CÓ** | `transport.MAC_DINH`, mọi thao tác có `het_gio > 0` (ca C7): createOrder/cancelOrder 10 s, đọc 10 s |
| **Chính sách thử lại** | **ĐÃ CÓ, và xác minh lại CÒN ĐÚNG** | ca C1–C6. `createOrder` mặc định `so_lan=1, duoc_thu_lai=False`; chỉ mở lên 3 lần khi `KHOA_CHONG_TRUNG=True`. J&T True (`txlogisticId` *"不支持重复"*), VTP False |
| **Xử lý giới hạn tần suất** | **ĐÃ CÓ phía mình, THIẾU phía hãng** | `gioi_han.py` hai trần cho cửa webhook, `polling` trần riêng từng tenant. Nhưng **J&T không công bố trần nào** ⇒ ta không biết đang chạm ngưỡng nào của hãng |
| **Circuit breaker** | **ĐÃ CÓ** | `polling.NGUONG_NGAT_MACH = 5` lỗi liên tiếp/hãng/lượt, có audit. Ca G6 |
| **Chuẩn hoá lỗi** | **ĐÃ CÓ cho J&T, RỖNG cho VTP** | `NormalizedCarrierError`, danh sách **TRẮNG** cho `co_the_thu_lai` (chỉ `HET_GIO`+`QUA_HAN_MUC`), `KHONG_RO` mặc định không thử lại. Ca D1–D9. Ca **D6** canh hai lớp `transport` và `loi_hang` **không lệch nhau** |
| **Theo dõi sức khoẻ hãng** | **MỚI THÊM ở G09** | `harness_hang.bao_cao_san_sang()` + `admin/carrier_health.js`. Ghi rõ: đây là *sức khoẻ của lượt chạy harness và chỗ đang bị chặn*, **không phải** "hãng có sống không" — chưa gọi hãng lần nào thì không ai biết điều đó |
| **Hỗ trợ xoay credentials** | **ĐÃ CÓ ở tầng lưu trữ** | bản mã mang `key_id` (`v3$<key_id>$<nonce>$<ct>`), ca F2. **Xoay khoá thật là V-13906-02, CHƯA CẤP** |
| **Đối soát sau kết quả không rõ** | **ĐÃ CÓ, và là phần chắc nhất** | `don_hang.doi_soat_don`: ba kết luận `da_vao`/`chua_vao`/`van_chua_ro` **không gộp**; **chỉ** mã `KHONG_TIM_THAY` mới ra `chua_vao`; timeout **không bao giờ** ra `chua_vao` (ca H2, H3) |

### Xác minh lại luật "cấm tự động thử lại createOrder" — CÒN ĐÚNG

Đo bằng ca C1, C2, C3 trên **cả hai** hãng:

- `transport.chinh_sach_cho("createOrder", False)` → `so_lan=1`, `duoc_thu_lai=False`. ✓
- `transport.chinh_sach_cho("cancelOrder", False)` → `duoc_thu_lai=False`. ✓
- J&T (`KHOA_CHONG_TRUNG=True`) → mở lên 3 lần. ✓ Căn cứ: tài liệu tạo đơn ghi `txlogisticId`
  *"不支持重复"*, và mã lỗi `145003204` *"订单重复：请将 txlogisticId 更新为唯一值"* tồn tại
  thật ⇒ hãng tự chặn đơn trùng.
- VTP (`KHOA_CHONG_TRUNG=False`) → **không** thử lại. ✓ Đúng mức an toàn, vì chưa đọc được
  khẳng định tương đương từ tài liệu VTP.

**Lưu ý phạm vi:** điều này mới chỉ đúng **ở tầng chính sách**. Nó chưa được kiểm chứng rằng
J&T thật sự chặn trùng — đó là câu hỏi 25 gửi hãng và bước kiểm `txlogisticId` lặp trong kế
hoạch sandbox.

---

## 6. G09.6 — HARNESS `app/harness_hang.py`

### Ba chế độ

| Chế độ | Chạy được chưa | Cổng chặn |
|---|---|---|
| `MOCK` (mặc định) | **có, ngay** | không cần gì |
| `SANDBOX` | **không** | 4 điều kiện ở mục 0 |
| `LIVE` | **không** | 4 điều kiện trên + phiếu duyệt từng thao tác ghi |

### Bốn ổ khoá chặn LIVE — phải mở hết bốn

1. `VIP_HUB_HARNESS_CHE_DO=LIVE` (cờ môi trường)
2. `VIP_HUB_HARNESS_DUYET` khớp mã việc đã cấp + `VIP_HUB_HARNESS_NGUOI_DUYET`
3. **`PhieuDuyetLive` cho TỪNG thao tác ghi** — truyền trong mã, không lấy được từ môi trường;
   mang người duyệt · thao tác · mã tham chiếu · hạn dùng; **dùng một lần**
4. **`CarrierAdapter.CHO_PHEP_LIVE = True`** — hằng chốt cứng trong `app/adapter.py`, file G09
   **CHỈ ĐỌC**

Ổ số 4 là ổ quan trọng nhất: kể cả khi ba ổ kia bị mở nhầm **và** mã harness có lỗi,
`adapter.tao_adapter(..., "production")` vẫn ném `PermissionError` ngay trong `__init__`
(ca A6). Harness **không có cách nào** tự mở đường live — ca `G_AnToan.test_g2` đọc harness
bằng **AST** và báo hỏng nếu có bất kỳ lệnh gán nào vào `CHO_PHEP_LIVE`/`KHOA_CHONG_TRUNG`/
`CAPABILITIES`, hoặc bất kỳ lời gọi `setattr()` nào.

### Ca thử bắt buộc: KHÔNG âm thầm rơi về MOCK

Đây là yêu cầu nặng nhất của chỉ thị, và là kiểu hỏng nguy hiểm nhất của một bộ nghiệm thu:
được gọi ở chế độ SANDBOX, thiếu credentials, rồi **âm thầm chạy MOCK và báo ĐẠT**.

Luật của harness: **không có đường rơi về MOCK.** Thiếu gì thì ném `ThieuCauHinh` kèm danh sách
chính xác. `KetQuaLanChay.che_do` **luôn là chế độ ĐÃ CHẠY**, không phải chế độ đã xin.

| Ca | Canh điều gì |
|---|---|
| `C_...test_c1` | SANDBOX không có gì ⇒ ném `ThieuCauHinh` |
| `C_...test_c2` | **ca canh thẳng**: nếu SANDBOX thiếu credentials mà vẫn trả về kết quả, ca này `fail()` kèm lời giải thích |
| `C_...test_c3` | thông điệp từ chối nói **chính xác** tên từng biến còn thiếu |
| `C_...test_c5` | thiếu `customerCode`/`password` thì nói đúng tên hai trường đó |
| `C_...test_c7` | đủ hết điều kiện mềm **vẫn** bị `CHO_PHEP_LIVE` chặn |
| `C_...test_c10` | LIVE có đủ cờ môi trường **vẫn** chưa đủ |
| `A_...test_a5` | xin SANDBOX qua môi trường nhưng gọi MOCK ⇒ `che_do` trả về là `MOCK`, không nói dối |

### 95 ca kiểm MOCK, chia 9 nhóm

| Nhóm | Mã ca | Canh gì |
|---|---|---|
| A hợp đồng | A1–A6 | capabilities đủ/trung thực, bản sao, ba kết cục, khoá live, chặn môi trường |
| B chữ ký | B0–B8 | công thức digest, ba header, Content-Type, timestamp UTC+7 ms, không URL thật ở mock |
| C timeout | C1–C7 | không thử lại thao tác ghi, có thử lại thao tác đọc, lỗi vĩnh viễn, hạn giờ |
| D ánh xạ lỗi | D0–D9 | danh sách trắng, mã lạ, đơn trùng, HTTP, hai lớp không lệch, 3 mã J&T thật |
| E trạng thái | E1–E7 | mã lạ, **J&T 110 AMBIGUOUS**, dấu vết, cấm chốt về hoàn tất, đòi căn cứ |
| F cách ly cred | F1–F6 | không lộ bí mật, `key_id`, cách ly theo tenant và theo hãng |
| G giới hạn | G1–G6 | hai trần webhook, lô 30 của J&T, trần theo tenant, ngắt mạch |
| H đối soát | H1–H4 | chọn thao tác theo capability, chỉ `KHONG_TIM_THAY`, timeout không phải "chưa vào" |
| I webhook | I1–I5 | sơ đồ theo hãng, mức DOCUMENTED/BLOCKED, người gửi không chọn được sơ đồ |

**Mỗi ca mang một trường `do_bang_gi`**, và có ca thử (`A_...test_a3`) báo hỏng nếu ca nào để
trống nó.

### Ba ca BỎ QUA — nói rõ, không giấu

`B0` (VTP chưa có công thức chữ ký công khai), `D0` (VTP chưa có bảng mã lỗi), `E7` (bảng ánh
xạ VTP chỉ có mã của bộ mô phỏng). **Bỏ qua không phải đạt.**

---

## 7. NGHIỆM THU — SỐ ĐO THẬT

Mọi lượt chạy dùng `VIP_HUB_DATA` trỏ thư mục tạm riêng. **Không lượt nào chạy migrate lên
`app/du-lieu/` của repo chính** (mục 24 của `SHARED_CONTRACTS.md`).

| Bộ thử | Kết quả |
|---|---|
| `app/thu/thu_g01_g02.py` | Ran 21 — OK |
| `app/thu/thu_g03.py` | Ran 53 — OK |
| `app/thu/thu_bao_mat.py` | Ran 57 — OK |
| `app/thu/thu_don_hang.py` | Ran 63 — OK |
| `app/thu/thu_webhook.py` | Ran 68 — OK |
| `app/thu/thu_gioi_han.py` | Ran 34 — OK |
| `app/thu/thu_nhap_file.py` | Ran 21 — OK |
| `app/thu/thu_saas.py` | Ran 19 — OK |
| `app/thu/thu_tich_hop.py` | Ran 6 — OK |
| `app/thu/thu_qa_soat.py` | Ran 30 — OK |
| `app/thu/thu_qa2_soat.py` | Ran 49 — OK (1 skipped) |
| **`app/thu/thu_harness_hang.py` (MỚI)** | **Ran 57 — OK** |
| `sh app/thu/chay_e2e.sh` (HTTP thật, nền cô lập) | **41/41 đạt**, mã thoát 0 |
| `node --test thu_frontend/thu_logic.mjs` | **tests 56** — OK |
| `python3 thu_frontend/thu_http.py` | Ran 36 — OK |
| **`python3 app/harness_hang.py` (MỚI)** | **95 đạt · 0 hỏng · 3 bỏ qua** (jt 56/0/0 · vtp 39/0/3) |

**Cộng Python: 478 phép kiểm** (421 sẵn có + 57 mới), **cộng tất cả các tầng: 611** (478 Python
+ 56 Node + 36 HTTP frontend + 41 E2E). Số này đo bằng cách **chạy lại từng bộ và đọc dòng
`Ran N`**, không cộng từ trí nhớ. 95 ca của harness **không** tính vào tổng — chúng là một lượt
đo riêng, và `thu_harness_hang.py` đã bao chúng.

### Đối chiếu danh sách nghiệm thu của chỉ thị

| Mục nghiệm thu | Ca phủ | Kết quả |
|---|---|---|
| Ca thử adapter local | A1–A6, `thu_g03` | ĐẠT |
| Contract test | A1–A6 (chạy với **mọi** adapter đã đăng ký) | ĐẠT |
| Ca thử chữ ký | B1–B8 | ĐẠT (chỉ J&T; VTP không có sơ đồ ký — `B0` bỏ qua) |
| Ca thử timeout | C1–C7 | ĐẠT |
| Ánh xạ lỗi | D0–D9 | ĐẠT cho J&T; VTP **BLOCKED** (không có bảng mã lỗi) |
| Cách ly credentials | F1–F6 | ĐẠT |
| Giới hạn tần suất | G1–G6 | ĐẠT ở tầng mình; trần phía hãng **BLOCKED** |
| Idempotency / đối soát | H1–H4, C1–C3 | ĐẠT |

---

## 8. G09.7 — `admin/carrier_health.js`

`admin/` **không có thư mục con** — ca `H_...test_h9` canh điều đó.

Màn hiện: sức khoẻ từng hãng · trạng thái ngắt mạch · **bảng sáu mức theo từng hạng mục, kèm
câu "đo bằng gì" của từng dòng** · danh sách `NEEDS_REVIEW`/`AMBIGUOUS` · ba dòng kết luận ·
danh sách điều kiện còn thiếu để lên sandbox/live.

Nguyên tắc, giống `admin/logic.js`: **phần logic không chạm DOM, không fetch**, nạp được cả ở
trình duyệt (`window.VIPCARRIERHEALTH`) lẫn Node (`module.exports`).

Bốn luật đáng nói:

1. **Giao diện KHÔNG tự tính mức sẵn sàng.** Mức do backend đo; màn chỉ tô màu. Hai bản sự thật
   là hai bản sẽ lệch — ca `H_...test_h2` chạy carrier_health.js bằng Node và đối chiếu bộ sáu
   mức của màn với hằng của backend.
2. **Mức lạ hiện nguyên văn** kèm `la=true`, không nuốt im.
3. **Ngắt mạch chưa đo thì nói "Chưa đo"**, không mặc định "bình thường". Mặc định xanh khi
   chưa biết là hỏng im lặng. Ca `H_...test_h6`.
4. **Không cho chốt nghĩa mã nhập nhằng trên màn** (`cho_phep_chot_tren_man: false`) — chốt
   nghĩa phải có căn cứ thật từ hãng và đi qua backend.

Thêm lớp chặn lộ bí mật thứ hai (`locBiMat()`) lọc mọi khoá khớp
`password|privatekey|secret|token|apikey|credential`. Ca `H_...test_h7`.

---

## 9. BẢN VÁ ĐỀ XUẤT CHO CÁC FILE CHỈ-ĐỌC — MÔ TẢ, KHÔNG SỬA

G09 **không chạm một dòng nào** trong `app/adapter*.py`, `app/transport.py`,
`app/trang_thai_hang.py`, `app/webhook.py`, `app/polling.py`, `app/loi_hang.py`,
`app/don_hang.py`, `app/gioi_han.py`, `app/server.py`, `app/csdl.py`, `app/migrate.py`.
Xác nhận bằng `git status` ở mục 11.

| # | File | Ưu tiên | Vấn đề đo được | Đề xuất |
|---|---|---|---|---|
| **P1** | `app/adapter_jt.py` `_dung_bizcontent_tao_don` | **CAO** | So với bảng tham số của `apiDoc/orderserve/create` (đọc 15/10/2026): (a) `sender.prov` và `sender.area` (và của `receiver`) đánh dấu **bắt buộc** nhưng đang gửi **chuỗi rỗng** ⇒ hãng sẽ trả `1450033315`; (b) thiếu hai trường **bắt buộc** `isInsured` và `goodsValue`; (c) **COD đang gán vào `itemsValue`**, trong khi tài liệu dùng `codMoney` cho tiền thu hộ — và `itemsValue` **không có trong bảng tham số**, chỉ xuất hiện trong ví dụ | Lấy `prov`/`area` từ các cột G04 **đã có sẵn** trong `don_hang` (đo bằng `PRAGMA table_info`: `nguoi_gui_tinh` · `nguoi_gui_quan` · `nguoi_gui_xa` · `nguoi_gui_buu_chinh` và bốn cột tương ứng của người nhận); thêm `isInsured: 0` + `goodsValue: 0` mặc định; **đổi `itemsValue` → `codMoney`** cho tiền COD. **Cần một quyết định đi kèm:** bên mình lưu **ba cấp** (tỉnh/quận/xã), J&T nhận **hai cấp** `prov`+`area` với `city` cho phép `null` — phải chốt `area` lấy từ `quan` hay từ `xa`, và cần danh mục địa danh của hãng (B-12). **Hậu quả nếu không vá: đơn thật bị hãng từ chối, và nếu lọt thì COD không được thu.** |
| **P2** | `app/adapter_jt.py` | VỪA | Chỉ có hằng URL cho tạo đơn và tra hành trình. Thiếu ba endpoint đã đọc được: huỷ `/api/order/cancelOrder`, báo giá `/api/spmComCost/getComCost`, nhãn `/api/order/printOrder` | Thêm ba hằng `URL_HUY_DON`, `URL_BAO_GIA`, `URL_NHAN` theo khuôn `URL_TAO_DON` (sandbox/production) |
| **P3** | `app/adapter_jt.py` + `app/don_hang.py` | THẤP | Trả lời tạo đơn của J&T **đã mang** `inquiryFee` (tổng cước), `codFee`, `insuranceFee`. `gui_don` lại gọi thêm `getShippingFee` một lượt nữa | Khi chạy thật, đọc phí **từ chính trả lời tạo đơn**; bớt một lượt gọi và bớt một chỗ hai số có thể lệch nhau |
| **P4** | `app/trang_thai_hang.py` | **CAO** | Bộ mã thứ hai trong ví dụ của `/logistics/query` (`10/50/92/94/100/110`) **không có** trong `JT_MA`. Mã `100` = "Ký nhận" (đã giao) sẽ bị coi là **mã lạ** ⇒ đơn đã giao **không bao giờ** về `giao_thanh_cong`, và **không báo lỗi gì** (mục 3) | Thêm bộ mã thứ hai vào `JT_MA` với nghĩa theo đúng `scanTypeName` của ví dụ, **và** đưa `110` của bộ đó vào sổ `NHAP_NHANG` (đã có). Hoặc tối thiểu: thêm 10/50/92/94/100 để đơn chạy được, giữ 110 nhập nhằng |
| **P4b** | `app/trang_thai_hang.py` | VỪA | VTP có **mâu thuẫn nội tại thứ hai**: bảng trạng thái đánh `104` là trạng thái cuối, đoạn *"Lưu ý"* thì không (mục 4) | Khi mang 21 mã VTP sang, đưa `104` vào sổ `NHAP_NHANG` **ngay**, cùng họ với J&T 110 |
| **P5** | `app/adapter_vtp.py` | **CAO** (tính trung thực) | (a) Khối chú thích đầu file kết luận repo `vip-viettelpost` là khung rỗng — **sai**, đo trên bản đi sau 174 commit; (b) `VTP_HOST_CHUA_XAC_MINH = "https://partner.viettelpost.vn"` — host đó **301 chuyển hướng** sang `partner2.viettelpost.vn`, và host **dev** là `partnerdev.viettelpost.vn`; (c) khai `getOrder=True` và `getShippingLabel=True` mà **không có tài liệu nào** chống lưng | (a) viết lại khối chú thích theo `docs/VTP_YEU_CAU_BO_SUNG.md`; (b) sửa hằng host, thêm hằng host dev; (c) hạ `getOrder`/`getShippingLabel` xuống `False` **hoặc** ghi rõ là khai theo bộ mô phỏng. **Hạ `getOrder` sẽ đổi hành vi `thao_tac_doi_soat`** (chuyển sang `trackOrder`) ⇒ cần AG-02 xem cùng |
| **P6** | `app/loi_hang.py` | VỪA | `BANG_MA_LOI` không có khoá `vtp`; lỗi VTP chỉ phân loại được theo HTTP | Thêm lớp phân loại theo **phong bì** của VTP (`"error": true` + `message`), theo khuôn `app/providers/viettel_post/errors.py` của repo kia. **Vẫn không bịa mã lỗi nào** |
| **P7** | `app/webhook.py` | VỪA | `SO_DO_THEO_HANG["vtp"] = None` ⇒ BLOCKED. Nhưng cơ chế xác thực webhook VTP **đã rõ**: so hằng thời gian trường `TOKEN` trong thân với secret của account | Thêm sơ đồ `vtp_token_than` ở mức **`DOCUMENTED`**. Kèm cảnh báo thiết kế: bí mật đi qua **thân yêu cầu** nên lộ trong log mọi lớp trung gian — nên bật kèm việc che thân trong log |
| **P8** | `app/adapter_jt.py` / `app/webhook.py` | VỪA | Tài liệu J&T ghi `timestamp` là *"毫秒 / 时区：UTC+7"*. Mốc Unix mili giây **không phụ thuộc múi giờ**, nên câu đó mơ hồ: có thể hãng gửi giá trị **lệch 7 tiếng**. `webhook.LECH_GIO_TOI_DA_MS` là 15 phút ⇒ nếu đúng vậy thì **mọi callback bị từ chối sạch** | Chưa vá vội — hỏi hãng trước (câu 12–14). Khi vá: cho phép chấp nhận cả hai cách diễn giải **trong một lượt chuyển tiếp có ghi log rõ**, rồi chốt một cách sau khi hãng trả lời |
| **P9** | `docs/VIETTELPOST_REUSE_AUDIT.md` | **CAO** (tính trung thực) | Toàn bộ kết luận của tài liệu đó đo trên bản clone sai | Thêm hộp đính chính ở đầu, trỏ sang `docs/VTP_YEU_CAU_BO_SUNG.md`. *(File này không thuộc quyền ghi của G09 ở đợt 3)* |

---

## 10. SCHEMA ĐỀ XUẤT VÀ BẢNG ROUTE

### Hằng `DDL_G09`

Khai trong `app/harness_hang.py` (hằng `DDL_G09`). **AG-00 viết migration v8** — G09 không
chạm `app/migrate.py`. Hai bảng: `g09_harness_lan_chay` và `g09_harness_ca`.

- `g09_harness_lan_chay`: `id · tenant_id · hang · che_do (CHECK MOCK/SANDBOX/LIVE) · bat_dau ·
  ket_thuc · so_ca · so_dat · so_hong · so_bo_qua · ket_luan (CHECK dang_chay/dat/hong/tu_choi)
  · ly_do_tu_choi · nguoi_chay · phieu_duyet · pham_vi_do (NOT NULL)`
- `g09_harness_ca`: `id · lan_chay_id → lan_chay(id) · ma_ca · nhom · mo_ta · ket_qua (CHECK
  dat/hong/bo_qua) · chi_tiet · do_bang_gi (NOT NULL) · UNIQUE(lan_chay_id, ma_ca)`

Ba điều cố ý:

1. **`pham_vi_do` và `do_bang_gi` là `NOT NULL`.** Ghi một kết quả mà không ghi đo bằng gì thì
   CSDL từ chối — §12.1 cưỡng chế bằng ràng buộc, không bằng lời dặn.
2. **Không có cột tiền nào** ⇒ không có chỗ cho `REAL` lọt vào (mục 16). Ca `G_...test_g4` canh.
3. **`UNIQUE(lan_chay_id, ma_ca)`** chống ghi trùng bằng CSDL, không bằng `if`.

`harness_hang.co_bang_harness()` kiểm bảng đã tồn tại chưa; chưa có thì `luu_lan_chay()` trả
`None` và **nói ra**, không giả vờ đã ghi (ca `G_...test_g6`). Hiện trên nền `143084b`: **bảng
chưa có**, vì migration v8 chưa viết.

### Bảng route đề xuất — AG-00 cắm vào `app/server.py`

| Phương thức | Đường | Gọi hàm nào | Quyền | Ghi gì |
|---|---|---|---|---|
| `GET` | `/api/g09/suc-khoe-hang` | `harness_hang.bao_cao_san_sang(ket_qua_chay)` | `tenant.hang.xem` | không ghi gì — chỉ đọc |
| `POST` | `/api/g09/harness/chay` | `harness_hang.chay_tat_ca(MOCK)` rồi `luu_lan_chay()` | **PLATFORM_ADMIN** | một dòng `g09_harness_lan_chay` + N dòng `g09_harness_ca` + audit |
| `GET` | `/api/g09/can-soat` | `harness_hang.danh_sach_can_soat(hang)` | `tenant.hang.xem` | không ghi gì |
| `GET` | `/api/g09/lan-chay/<id>` | đọc hai bảng trên | **PLATFORM_ADMIN** | không ghi gì |

Ba ràng buộc đề nghị AG-00 giữ khi cắm:

1. **Route `/harness/chay` ép cứng `che_do = MOCK`.** Không nhận `che_do` từ thân yêu cầu.
   Chạy SANDBOX/LIVE **chỉ** từ dòng lệnh trên máy người, có phiếu duyệt — không bao giờ qua
   HTTP. Mở một cửa HTTP chạy được LIVE là đưa ổ khoá ra ngoài tầm kiểm soát.
2. Route `/harness/chay` nên đi qua `gioi_han.kiem("platform.quan_tri", ...)`.
3. Trả về phải đi qua một lớp lọc bí mật phía backend (tương đương `locBiMat()` của giao diện).

---

## 11. BÀN GIAO

### File đã thêm (8) — không file nào có trước; **không sửa một file nào đang có**

Đo bằng `git status --short` (8 dòng `??`, không dòng nào `M`) và `git diff --stat 143084b`
(**rỗng**).

```
app/harness_hang.py              (mới)
app/thu/thu_harness_hang.py      (mới)
admin/carrier_health.js          (mới)
docs/G09_FINAL_REPORT.md         (mới, file này)
docs/G09_SANDBOX_TEST_PLAN.md    (mới)
docs/G09_CREDENTIALS_CHECKLIST.md(mới)
docs/JT_CAU_HOI_CHINH_THUC.md    (mới)
docs/VTP_YEU_CAU_BO_SUNG.md      (mới)
```

### File KHÔNG chạm — xác nhận bằng `git status`, không bằng trí nhớ

`app/adapter.py` · `app/adapter_jt.py` · `app/adapter_vtp.py` · `app/transport.py` ·
`app/trang_thai_hang.py` · `app/webhook.py` · `app/polling.py` · `app/loi_hang.py` ·
`app/don_hang.py` · `app/gioi_han.py` · `app/bao_mat.py` · `app/server.py` · `app/csdl.py` ·
`app/migrate.py` · `admin/admin.js` · `admin/logic.js` · `admin/index.html` · `gateway/` ·
`thu_frontend/` · mọi `docs/` khác.

Repo `thanhbn123/vip-viettelpost`: **CHỈ ĐỌC** qua `gh api .../contents`. Không clone, không
sửa, không commit, không push, không merge, không deploy, **không lấy token nào**.

---

## 12. DANH SÁCH BLOCKED — mỗi mục nêu CHÍNH XÁC cái còn thiếu

| # | Mục | Thiếu chính xác cái gì | Mã việc |
|---|---|---|---|
| B-01 | Gọi API hãng (sandbox) | mã việc `V-G09-01` chưa cấp | V-G09-01 |
| B-02 | Credentials sandbox J&T | `customerCode` + `password` của môi trường thử — **chỉ bưu cục hợp tác của J&T cấp được**, không có trên trang tài liệu | V-13906-05 |
| B-03 | Tài khoản nền tảng J&T | `apiAccount` + `privateKey` riêng cho VIP EXPRESS HUB, lấy trong 控制台 **sau khi hoàn tất 开发者认证** (bước 3) — bước này cần người của J&T | — |
| B-04 | Nghĩa mã J&T `110` | văn bản trả lời của J&T cho câu hỏi 1–2 của `docs/JT_CAU_HOI_CHINH_THUC.md` | V-13906-04 |
| B-05 | Bộ mã `scanTypeCode` thứ hai của J&T | xác nhận của hãng về việc có hai bộ mã và bộ nào áp cho Việt Nam | V-13906-04 |
| B-06 | Khoá ký callback J&T | hãng nói rõ callback ký bằng `privateKey` hay khoá riêng, và chuỗi nào đem đi ký | — |
| B-07 | Trần tần suất J&T | tài liệu công khai **không công bố**; cần hãng trả lời câu 16–18 | — |
| B-08 | Nhãn vận đơn VTP | **chưa tìm được trang tài liệu nào** của Viettel Post về in nhãn | — |
| B-09 | Bảng mã lỗi VTP | hãng chưa công bố bảng mã; hiện chỉ có phong bì `"error": true` | — |
| B-10 | API tra vận đơn VTP | chưa biết có endpoint tra theo mã không ⇒ **đơn VTP "không rõ kết quả" chỉ người mới đối soát được** | — |
| B-11 | Credentials dev VTP | `VTP_USERNAME`+`VTP_PASSWORD` của `partnerdev.viettelpost.vn`; **cấm** lấy từ GitHub Environment của repo khác | — |
| B-12 | Mã địa danh của cả hai hãng | danh mục `prov`/`area` của J&T và ID địa danh của VTP; **không có thì không tạo nổi một đơn nào** | — |
| B-13 | Mở `CHO_PHEP_LIVE` | chỉ Owner, qua AG-00. **G09 không đề nghị mở ở đợt này** | — |
| B-14 | URL công khai nhận callback | thuộc triển khai staging | V-G11-01 |
| B-15 | Migration v8 cho `DDL_G09` | AG-00 viết; G09 không chạm `migrate.py` | — |

---

## 13. RỦI RO CỐ Ý BỎ QUA — ghi ra theo §12.1

| # | Rủi ro | Vì sao bỏ qua đợt này | Cách vá đúng |
|---|---|---|---|
| R1 | **Mã J&T `100` ("Ký nhận") hiện là mã lạ** ⇒ nếu hãng dùng bộ mã của ví dụ thì đơn đã giao **không bao giờ** về `giao_thanh_cong`, và **không báo lỗi gì** | sửa `trang_thai_hang.py` — file G09 CHỈ ĐỌC | bản vá **P4**, ưu tiên CAO |
| R2 | **`bizContent` tạo đơn J&T thiếu/sai 5 trường** so với tài liệu, trong đó **COD gán nhầm cột** | sửa `adapter_jt.py` — CHỈ ĐỌC | bản vá **P1**, ưu tiên CAO |
| R3 | **Chú thích trong `adapter_vtp.py` đang nói sai** về repo VTP | sửa `adapter_vtp.py` — CHỈ ĐỌC | bản vá **P5** + đính chính `VIETTELPOST_REUSE_AUDIT.md` (**P9**) |
| R4 | **`timestamp` UTC+7 có thể lệch 7 tiếng** ⇒ callback J&T có thể bị từ chối sạch | chưa đủ dữ kiện; đoán rồi vá là vá mù | hỏi hãng câu 12–14, rồi **P8** |
| R5 | **Chưa chạy migration v8** ⇒ `luu_lan_chay()` luôn trả `None`, kết quả harness **không được lưu** | `migrate.py` là của AG-00 | **B-15**; hiện harness đã **nói ra** khi không lưu được |
| R6 | **`admin/carrier_health.js` chưa được nạp vào màn nào** — `admin/index.html` là của AG-04, G09 không sửa | giữ làn | AG-00/AG-04 thêm một thẻ `<script>` và một mục menu |
| R7 | **Chưa có lượt kiểm bằng trình duyệt thật** cho màn sức khoẻ hãng (tầng 3 của `FRONTEND_AUTOMATION.md`) | tầng 3 không tự chạy được | chạy tay theo tài liệu đó sau khi màn được nạp |
| R8 | **Trang `批量打印面单` của J&T chưa mở được** | thử ba đường dẫn, trang chuyển về trang chủ | mở lại bằng trình duyệt ở lượt sau |
| R9 | **Toàn bộ kết luận của G09 đo trên MOCK.** Không có một byte nào thật sự đi tới hãng | **đúng chủ đích** — V-G09-01 chưa cấp | chạy `docs/G09_SANDBOX_TEST_PLAN.md` sau khi được cấp quyền |

---

## 14. VIỆC NÊN LÀM TIẾP, theo thứ tự

1. **AG-00 duyệt bản vá P1 và P4** — hai lỗi có hậu quả thật: đơn bị hãng từ chối, COD không
   thu được, đơn đã giao đứng im.
2. **AG-00 viết migration v8** cho `DDL_G09`, cắm 4 route ở mục 10 với ràng buộc "ép cứng MOCK".
3. **Gửi `docs/JT_CAU_HOI_CHINH_THUC.md`** cho J&T — câu 1–5 (mã 110) chặn nhiều việc nhất.
4. **Cập nhật bản clone `~/code/vip-viettelpost`** lên `origin/main`; đính chính P9.
5. **Anh Thành quyết** phạm vi mang mã/dữ kiện VTP sang (mục A3 của `VTP_YEU_CAU_BO_SUNG.md`).
6. Cấp `V-G09-01` + credentials ⇒ chạy `docs/G09_SANDBOX_TEST_PLAN.md`.
