# VIETTEL POST — DANH SÁCH YÊU CẦU BỔ SUNG CỤ THỂ

**Soạn:** AG-03 CARRIER, 15/10/2026 · **Nền:** `143084b`, nhánh `agent/g09-carrier`.

> **Đính chính trước khi đọc tiếp — và đây là phát hiện lớn nhất của G09.4.**
>
> Tài liệu `docs/VIETTELPOST_REUSE_AUDIT.md` và phần chú thích đầu `app/adapter_vtp.py` kết
> luận rằng repo `thanhbn123/vip-viettelpost` là **khung rỗng**: `STATUS_MAP = {}`,
> `auth.py raise NotImplementedError`, `docs/VIETTEL_POST_INTEGRATION.md` ghi *"Scaffold cố ý
> không điền endpoint"*. **Kết luận đó đúng với thứ đã đo, nhưng thứ đã đo là sai bản.**
>
> Phép đo ngày 15/10/2026: bản clone cục bộ `~/code/vip-viettelpost` đang đứng ở commit
> `4df8ce7`, trong khi `origin/main` là `677cba9` — **đi sau 174 commit**
> (`gh api repos/thanhbn123/vip-viettelpost/compare/4df8ce7...main` → `"ahead": 174`,
> `"behind": 0`). Nhánh `main` hiện tại **có một lớp tích hợp Viettel Post hoàn chỉnh**, đối
> chiếu với tài liệu Partner chính thức ngày 29/09/2026.
>
> Đây đúng dạng §12.1 của `CLAUDE.md`: **thứ dùng để kiểm chứng (bản clone cục bộ) tự nó không
> đáng tin, và không ai kiểm nó trước khi tin.** Bản clone không báo lỗi gì — nó chỉ cũ.
> Bài học đưa vào quy trình: *đo một repo thì phải đo CẢ KHOẢNG CÁCH tới remote trước, không
> chỉ đọc file.*

---

## 1. Thứ KHÔNG còn thiếu nữa (đã có, chỉ là chưa ai mang sang)

Đo bằng `gh api repos/thanhbn123/vip-viettelpost/contents/<đường dẫn>?ref=main`, CHỈ ĐỌC,
không clone, không sửa, không push — 15/10/2026.

| Hạng mục | Có ở đâu trên `main` | Nguồn tài liệu hãng mà nó dẫn |
|---|---|---|
| **Xác thực** | `app/providers/viettel_post/auth.py` | `partner2.viettelpost.vn/document/token-authen` — ba đường: `POST /v2/user/Login` (USERNAME/PASSWORD → token ngắn hạn), `POST /v2/user/ownerconnect` (header `Token` → token dài hạn, tài liệu ghi 1 năm), `POST /v2/user/LoginVTP` (đổi token bí mật tạo trên viettelpost.vn) |
| **Bảng giá / báo giá** | `app/providers/viettel_post/mapping.py` | `POST /v2/order/getPriceAll` (danh sách dịch vụ), `POST /v2/order/getPrice` (tính cước) |
| **Tạo đơn** | cùng file | `POST /v2/order/createOrder` |
| **Huỷ đơn** | cùng file | `POST /v2/order/UpdateOrder` với `TYPE=4`; chỉ huỷ được khi `ORDER_STATUS < 200` |
| **Mã trạng thái** | `app/providers/viettel_post/status_mapper.py` + `docs/STATUS_MAPPING.md` | `partner2.viettelpost.vn/document/webhook`, mục *"Bảng danh sách trạng thái"* — **21 mã chính thức**, trong đó 15 mã có ánh xạ rõ và 6 mã (102, 202, 503, 505, 508, 550) cố ý **không** ánh xạ |
| **Webhook: thân yêu cầu** | `app/webhooks/viettel_post_payload.py` | `POST`, `application/json;charset=UTF-8`, thân `{"DATA": {"ORDER_NUMBER", "ORDER_STATUS", "ORDER_STATUSDATE", …}, "TOKEN"}` |
| **Webhook: xác thực** | `app/webhooks/processor.py` | Trường **`TOKEN` trong THÂN**, so sánh **hằng thời gian** với secret chung. Tài liệu **không công bố sơ đồ HMAC/chữ ký nào** |
| **Webhook: chống trùng** | `app/webhooks/fingerprint.py` | VTP **không** công bố mã sự kiện; dấu vân tay dựng từ `provider \| ORDER_NUMBER \| ORDER_STATUS \| ORDER_STATUSDATE` |
| **Webhook: thử lại** | `app/webhooks/processor.py` | VTP thử lại **tối đa 5 lần** tới khi nhận HTTP 200 |
| **Mã lỗi** | `app/providers/viettel_post/errors.py` | Phong bì trả lời mang `"error": true`; phân loại thêm theo HTTP 4xx/5xx |
| **Môi trường dev** | `docs/VTP_DEV_E2E.md` | Host dev: **`https://partnerdev.viettelpost.vn`**. `partner.viettelpost.vn` **301 chuyển hướng** sang `partner2.viettelpost.vn` |

### Hệ quả cho câu "chữ ký webhook VTP là BLOCKED"

Câu đó **cần sửa cho đúng phạm vi**. Đo được: Viettel Post **không có** sơ đồ chữ ký cho
webhook — không phải "chúng ta chưa tìm ra cách ký", mà **hãng không ký**. Cơ chế xác thực
chính thức là so khớp một **bí mật chung đặt trong thân yêu cầu** (`TOKEN`).

- Hạng mục **"chữ ký request"** của VTP trong bảng sáu mức ⇒ **BLOCKED**, lý do: *không áp
  dụng — hãng không có sơ đồ ký*. Ghi BLOCKED thay vì bỏ trống để không ai tưởng đã làm xong.
- Hạng mục **"callback/webhook"** ⇒ **DOCUMENTED**, vì cơ chế đã rõ nhưng cửa webhook của dự
  án này (`app/webhook.py`, `SO_DO_THEO_HANG["vtp"] = None`) **chưa cài** sơ đồ đó.

---

## 2. YÊU CẦU BỔ SUNG — từng mục một, nói rõ cần GÌ và XIN AI

Không có mục nào dạng "cần thêm tài liệu". Mỗi mục: thiếu chính xác cái gì · xin ở đâu · để
làm gì · chặn việc gì nếu không có.

### Nhóm A — xin từ **anh Thành / chủ dự án** (nội bộ, không cần Viettel Post)

| # | Cần chính xác cái gì | Để làm gì | Không có thì chặn việc gì |
|---|---|---|---|
| A1 | **Cấp mã việc `V-G09-01`** (gọi API hãng, dù chỉ sandbox) | mở chế độ `SANDBOX` của `app/harness_hang.py` | mọi hạng mục VTP đứng yên ở `DOCUMENTED`, không bao giờ lên `SANDBOX VERIFIED` |
| A2 | **Quyết định đường lấy credentials dev VTP**: (a) xin Viettel Post cấp bộ mới cho VIP EXPRESS HUB, hay (b) dùng lại bộ đang nằm trong GitHub Environment `staging` của repo `vip-viettelpost` | có `VTP_USERNAME`/`VTP_PASSWORD` hoặc `VTP_TOKEN` của `partnerdev` | không chạy được bước 1–3 của kế hoạch sandbox |
| A3 | **Xác nhận có được mang mã từ repo `vip-viettelpost` sang không**, và nếu được thì mang theo kiểu nào: chép mã (hai repo khác hẳn ngăn xếp — bên đó FastAPI + SQLAlchemy + async, bên này `sqlite3` + thư viện chuẩn + đồng bộ) hay chỉ **chép BẢNG DỮ KIỆN** (21 mã trạng thái, danh sách endpoint, khuôn thân webhook) | quyết định khối lượng của G09 bước tiếp | adapter VTP đứng nguyên ở mức MOCK |
| A4 | **Cập nhật bản clone `~/code/vip-viettelpost`** lên `origin/main`, hoặc ghi rõ là bản đông lạnh có chủ đích | lần đo sau không lặp lại đúng cái sai của lần này | mọi khảo sát sau đều đo nhầm bản |
| A5 | **Duyệt bản vá đề xuất** cho `app/adapter_vtp.py` và `app/trang_thai_hang.py` (liệt kê ở `docs/G09_FINAL_REPORT.md` mục 9) — hai file này G09 CHỈ ĐỌC | sửa phần chú thích đang nói sai về repo VTP, và điền 21 mã trạng thái thật | tài liệu trong mã tiếp tục nói sai; đơn VTP không bao giờ đổi trạng thái |

### Nhóm B — xin từ **Viettel Post** (người phụ trách đối tác kỹ thuật)

Ba câu đầu là các điểm mà **chính tài liệu Partner tự mâu thuẫn hoặc bỏ trống**, đã được repo
`vip-viettelpost` ghi lại ở `docs/STATUS_MAPPING.md` mục *"Điểm cần xác minh"* — chép sang đây
để hỏi một lượt.

| # | Hỏi gì | Vì sao cần | Hệ quả nếu đoán sai |
|---|---|---|---|
| B1 | **Mã `104` (Lấy hàng điều phối bưu tá) có phải trạng thái CUỐI không?** Bảng trạng thái đánh dấu "Y" cho 104, nhưng đoạn *"Lưu ý"* ngay dưới liệt kê trạng thái cuối là 101/107/201/501/503/504 — **không có 104** | 104 đứng **trước** 200 (lấy hàng thành công) theo nghiệp vụ | coi 104 là cuối ⇒ **chặn mọi sự kiện sau đó** ⇒ đơn đứng im ở "chờ lấy hàng" trong khi hàng đã đi |
| B2 | **`ORDER_STATUSDATE` theo múi giờ nào?** Tài liệu ghi định dạng `dd/MM/yyyy HH:mm:ss` nhưng không nói múi giờ | cần để sắp thứ tự sự kiện và chặn sự kiện đến muộn | lệch 7 tiếng ⇒ sự kiện mới bị coi là cũ và **bị bỏ im lặng** |
| B3 | **Danh sách 21 mã đã đầy đủ chưa?** Thực tế có thể xuất hiện mã ngoài bảng | quyết định chính sách cho mã lạ | hiện đang xử an toàn: mã lạ ⇒ không đổi trạng thái, đánh dấu cần soát |
| B4 | **Nghĩa nghiệp vụ của 505 / 508 / 550 / 503** — bốn mã đang cố ý để trống ánh xạ. 505 "Yêu cầu chuyển hoàn" dùng cho **cả** "khách từ chối" lẫn "người gửi yêu cầu hoàn" (lý do 43); 503 "Tiêu huỷ theo yêu cầu khách hàng" không trùng nghĩa với huỷ hay hoàn | để điền ánh xạ mà không phải đoán | đoán sai 505 ⇒ đơn bị đẩy sang "hoàn hàng" khi thực ra khách chỉ đổi lịch |
| B5 | **Có sơ đồ chữ ký nào cho webhook không** (HMAC header…), hay `TOKEN` trong thân là cơ chế duy nhất? Tài liệu có ví dụ kèm header `Authorization` nhưng **không nêu cách kiểm** | quyết định cửa webhook cho VTP có được mở ra ngoài mock không | mở cửa mà chỉ so `TOKEN` trong thân thì **bí mật đi qua thân yêu cầu**, lộ trong log của mọi lớp trung gian |
| B6 | **Header `Authorization` trong ví dụ webhook** mang giá trị gì và kiểm thế nào? | như trên | như trên |
| B7 | **API tra cứu vận đơn theo mã** — có endpoint nào ngoài webhook không? Repo `vip-viettelpost` cài `get_services`/`calculate_fee`/`create_order`/`cancel_order`, **không có** `get_shipment` theo tài liệu | cần để **đối soát** khi lượt tạo đơn đứt giữa chừng, và để polling dự phòng khi webhook hỏng | không có ⇒ đơn VTP "không rõ kết quả" **chỉ người mới soát được**, máy không tự soát |
| B8 | **In nhãn vận đơn** — Partner API có endpoint lấy nhãn không? Chưa tìm được trang tài liệu nào | `adapter_vtp.getShippingLabel` hiện khai `True` nhưng chỉ trả `"MOCK-PDF"` | capability đang khai quá thứ chứng minh được |
| B9 | **Hạn mức gọi API** (lượt/giây, lượt/ngày) và mã lỗi khi vượt | đặt trần phía mình cho đúng | đặt bừa ⇒ hoặc bị hãng chặn, hoặc tự bóp mình |
| B10 | **Token dài hạn `ownerconnect`** sống bao lâu thật? Tài liệu ghi 1 năm nhưng trường `data.expired` luôn bằng `0` trong mọi mẫu và **không được giải thích** | lập lịch xoay token | token chết giữa đêm, đơn không gửi được, không ai biết vì sao |
| B11 | **Mã địa danh (`SENDER_DISTRICT`, `RECEIVER_WARD`…)** lấy ở đâu, có API tra theo tên không? Repo kia ghi đây là rủi ro R-006 | tạo đơn cần ID số, hệ thống mình lưu tên | không tra được ⇒ không tạo được đơn nào |

---

## 3. Những điều ĐÃ ĐO ĐƯỢC về môi trường dev của VTP (để không hỏi lại)

Từ `docs/VTP_DEV_E2E.md` trên `main` của repo `vip-viettelpost`, đọc 15/10/2026:

- Môi trường dev **tồn tại và đã chạy được**: ngày 02/10/2026, run `36978332181`, đã đăng nhập
  `Login` + `ownerconnect` bằng tài khoản Partner dev, lấy dịch vụ, tính cước, **tạo một đơn
  thử `303296591832` rồi huỷ** — kết luận `G08 PASS`.
- Trước đó ngày 01/10 từng có một lần báo `PASS chỉ-đọc` và **đã bị rút lại** (`CR-STG-007`),
  vì với token tĩnh thì bước `authenticate` **không gọi mạng** và hai API `getPriceAll`/
  `getPrice` của `partnerdev` **không kiểm token** — token giả cũng PASS. Đây là một ca §12.1
  rất sạch, đáng chép vào kế hoạch sandbox của chúng ta: **phép đo không đụng tới thứ cần đo
  thì kết quả đạt của nó vô nghĩa.**
- `scripts/vtp_dev_e2e.py` **từ chối** mọi `VTP_BASE_URL` khác `https://partnerdev.viettelpost.vn`
  (thoát mã 2, không gửi yêu cầu nào) và **không thử lại** bước nào.

⇒ Khi xin credentials (mục A2), xin **đúng bộ của `partnerdev`**, không phải production.

---

## 4. Thứ tự nên làm

1. **A4** cập nhật bản clone (rẻ nhất, chặn sai lặp lại).
2. **A3 + A5** chốt phạm vi mang sang và duyệt bản vá tài liệu-trong-mã (không cần Viettel Post).
3. **B1, B2, B5, B7** gửi Viettel Post — bốn câu chặn nhiều việc nhất.
4. **A1 + A2** cấp quyền và credentials dev.
5. Chạy kế hoạch ở `docs/G09_SANDBOX_TEST_PLAN.md`.
