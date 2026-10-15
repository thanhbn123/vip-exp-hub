# CÂU HỎI CHÍNH THỨC GỬI J&T EXPRESS VIỆT NAM

**Ai gửi:** bộ phận kỹ thuật VIP ORDER · **Gửi cho:** nhân viên phụ trách tích hợp API của J&T
Express Việt Nam (người liên hệ ở bước *联调测试* — bước 4 của quy trình đối tiếp trên
`open.jtexpress.vn`).
**Ngày soạn:** 15/10/2026 · **Căn cứ:** tài liệu công khai tại `open.jtexpress.vn/apiDoc`, đọc
bằng trình duyệt ngày 15/10/2026 (trang là SPA nên tải tĩnh bằng `curl` không đọc được nội dung).

> **Người gửi không cần biết hệ thống của chúng tôi.** Mỗi câu hỏi dưới đây đã ghi đủ: hỏi về
> cái gì, tài liệu hiện nói gì, chỗ nào mâu thuẫn, và cần J&T trả lời chính xác điều gì. Chỉ
> cần chép nguyên phần "CÂU HỎI" gửi đi.

---

## CÂU HỎI 1 — QUAN TRỌNG NHẤT: mã `scanTypeCode = 110` có hai nghĩa ngược nhau

### Tài liệu đang nói gì

Trên **cùng một trang** `open.jtexpress.vn/apiDoc/logistics/query`, hai chỗ nói hai nghĩa khác
nhau cho con số `110`:

| Chỗ trong tài liệu | `110` nghĩa là gì |
|---|---|
| **Bảng tham số** của trường `scanTypeCode` | `Arrival(110, "到件扫描")` — *hàng đã đến kho trung chuyển*, tức là hàng vẫn đang đi bình thường |
| **Ví dụ trả lời** ngay dưới bảng đó | `"scanTypeCode": 110, "scanTypeName": "Quét kiện vấn đề"`, `desc` ghi *"đã quét mã bất thường … Nguyên nhân vấn đề【】"* — tức là **kiện hàng có vấn đề** |

Trang `open.jtexpress.vn/apiDoc/logistics/statusFeedback` (轨迹回传) lặp lại bảng tham số với
nghĩa *Arrival*.

### Vì sao chúng tôi không tự chọn một nghĩa

Hai nghĩa này **ngược chiều nhau về nghiệp vụ**:

| Nếu `110` nghĩa là *Arrival* | Nếu `110` nghĩa là *kiện có vấn đề* |
|---|---|
| Đơn đang đi bình thường. Hệ thống đẩy đơn sang trạng thái "đang giao". Không ai cần làm gì. | Đơn đang gặp sự cố. Nhân viên phải xem ngay, liên hệ người nhận, có thể phải hoàn hàng. |
| Chọn sai hướng này ⇒ **đơn có vấn đề bị coi là bình thường và không ai xử lý**. | Chọn sai hướng này ⇒ báo động giả cho mọi kiện hàng đi qua kho. |

Loại sai đắt hơn là loại thứ nhất, nên hiện tại hệ thống của chúng tôi **không áp trạng thái
nào** cho mã `110` và đánh dấu đơn là "cần soát bằng người".

### Một dữ kiện nữa khiến chúng tôi nghi có HAI BỘ MÃ khác nhau

Ví dụ trả lời trong tài liệu dùng một loạt mã **không có trong bảng tham số**, và nội dung
tiếng Việt trông như dữ liệu thật của môi trường Việt Nam:

| Mã trong ví dụ | `scanTypeName` trong ví dụ | Mã tương ứng trong bảng tham số |
|---|---|---|
| `10` | Nhận hàng | bảng ghi `106` = 快件揽收 (Picked Up) |
| `50` | Gửi hàng | bảng ghi `109` = 发件扫描 (Departure) |
| `92` | Hàng đến | bảng ghi `110` = 到件扫描 (Arrival) |
| `94` | Quét phát hàng | bảng ghi `112` = 出仓扫描 (On Delivery) |
| `100` | Ký nhận | bảng ghi `113` = 快件签收 (Delivered) |
| `110` | **Quét kiện vấn đề** | bảng ghi `110` = **到件扫描 (Arrival)** |

Nếu đúng là có hai bộ mã thì trong bộ của ví dụ, "hàng đến" là `92`, còn `110` thật sự là
"kiện có vấn đề" — và bảng tham số đang mô tả một bộ mã khác.

### CÂU HỎI

1. **Mã `scanTypeCode = 110` mà hệ thống J&T đẩy về cho khách hàng Việt Nam có nghĩa chính xác
   là gì:** "hàng đến kho trung chuyển" (Arrival / 到件扫描) hay "quét kiện có vấn đề"?
2. **Có phải đang tồn tại HAI bộ mã `scanTypeCode` khác nhau không** (bộ `103…121` trong bảng
   tham số, và bộ `10/50/92/94/100/110` trong ví dụ)? Nếu có:
   - Bộ nào áp dụng cho tài khoản khách hàng tại Việt Nam?
   - Bộ nào áp dụng cho API tra hành trình (`/api/logistics/trace`), bộ nào cho callback
     (轨迹回传)? Hai cửa này có dùng chung bộ mã không?
3. Xin cho **danh sách đầy đủ, chính thức** mọi giá trị `scanTypeCode` mà J&T có thể đẩy về, kèm
   tên tiếng Việt và tên tiếng Anh của từng mã.
4. Mã `121` (FINISH / 完结) phát sinh **sau khi giao thành công** hay **sau khi hoàn hàng về
   người gửi**, hay cả hai? Sau `121` còn mã nào nữa không?
5. Mã `104` (Pickup Failure / 取件失败) và `118` (Delivery Problem / 派件问题件) khác nhau thế
   nào khi cùng là "không lấy/giao được"?

---

## CÂU HỎI 2 — Callback (轨迹回传) ký bằng khoá nào

### Tài liệu đang nói gì

Trang `open.jtexpress.vn/apiDoc/logistics/statusFeedback` ghi callback dùng **đúng ba header
như mọi API khác**: `apiAccount`, `digest`, `timestamp`; thân yêu cầu là form có trường
`bizContent`. Trang giới thiệu (`极兔API简介`) ghi công thức ký là
`digest = base64( md5( <chuỗi JSON của bizContent> + privateKey ) )`, md5 ra **mảng byte** rồi
mới base64.

### Chỗ chưa rõ

Tài liệu **không nói** phía nhận phải dùng khoá nào để kiểm chữ ký của callback.

### CÂU HỎI

6. Khi J&T gọi callback về URL của chúng tôi, **trường `digest` được tính bằng khoá nào**:
   - `privateKey` của chính tài khoản API của chúng tôi (giống chiều chúng tôi gọi J&T), hay
   - một khoá riêng dành cho chiều callback do J&T cấp?
7. **Chuỗi đem đi ký** là gì: chỉ chuỗi JSON `bizContent`, hay toàn bộ thân form
   (`bizContent=...`), hay một chuỗi khác? Xin cho một ví dụ có đủ ba thứ: chuỗi gốc, khoá dùng
   để ký (có thể che bớt), và `digest` kết quả — để chúng tôi đối chiếu từng byte.
8. Trường `apiAccount` trong header callback là **tài khoản API của chúng tôi** hay tài khoản
   của J&T?
9. J&T **thử lại** callback bao nhiêu lần khi chúng tôi trả về mã khác `code=1` hoặc khi máy
   chủ chúng tôi không trả lời? Khoảng cách giữa các lần thử là bao lâu?
10. J&T có đẩy **trùng** một sự kiện hành trình không? Nếu có, chúng tôi nên dùng trường nào
    làm **khoá chống trùng** (hiện trong `details` không thấy trường mã sự kiện duy nhất nào —
    chỉ có `billCode` + `scanTime` + `scanTypeCode`)?
11. Khi J&T đẩy nhiều sự kiện cùng lúc, thứ tự có **bảo đảm theo thời gian** không, hay chúng
    tôi phải tự sắp theo `scanTime`?

---

## CÂU HỎI 3 — Trường `timestamp`: mốc thời gian thật hay giờ UTC+7 quy đổi

### Tài liệu đang nói gì

Bảng Headers của mọi API ghi: `timestamp` — `时间戳，毫秒 / 时区：UTC+7`.

### Chỗ chưa rõ

Một mốc thời gian Unix tính bằng mili giây **không phụ thuộc múi giờ**. Việc tài liệu ghi thêm
"múi giờ UTC+7" có thể hiểu theo hai cách, và hai cách lệch nhau đúng **7 tiếng**:

| Cách hiểu | Giá trị gửi lên |
|---|---|
| (a) Mốc Unix thật, ghi chú UTC+7 chỉ để nói giờ hiển thị | `1760000000000` |
| (b) Lấy **giờ treo tường** ở UTC+7 rồi quy đổi như thể đó là giờ UTC | `1760000000000 + 25 200 000` |

Chúng tôi đang làm theo cách (a). Nếu J&T dùng cách (b) thì mọi chữ ký sẽ **vẫn đúng** (vì
`timestamp` không nằm trong chuỗi ký) nhưng mọi lượt kiểm chống phát-lại sẽ **lệch 7 tiếng** và
bị từ chối sạch.

### CÂU HỎI

12. Giá trị `timestamp` cần gửi là **(a)** hay **(b)** ở trên? Xin cho một ví dụ: một giá trị
    `timestamp` cụ thể và giờ Việt Nam tương ứng của nó.
13. J&T **chấp nhận lệch giờ tối đa bao nhiêu** giữa `timestamp` và giờ máy chủ J&T trước khi
    từ chối yêu cầu?
14. Câu hỏi tương tự cho `timestamp` trong header **callback** mà J&T gửi về chúng tôi.
15. Trường `scanTime` trong `details` (ví dụ `"2024-06-05 15:57:04"` và
    `"2024-06-21T13:23:56"` — hai định dạng khác nhau trong hai trang tài liệu) là **giờ Việt
    Nam** hay giờ UTC? Định dạng chuẩn là cái nào?

---

## CÂU HỎI 4 — Giới hạn tần suất gọi API

### Tài liệu đang nói gì

Bảng mã lỗi (`open.jtexpress.vn/apiDoc/errorCode/index`) có 23 dòng và **không có dòng nào** về
vượt hạn mức gọi. Giới hạn duy nhất tìm được là `145003502 — 运单号数量超过30个` (gửi quá 30 mã
vận đơn trong một lượt tra hành trình), đó là giới hạn **kích thước một lượt**, không phải giới
hạn tần suất.

### CÂU HỎI

16. Mỗi tài khoản API được gọi **tối đa bao nhiêu lượt mỗi giây / mỗi phút / mỗi ngày**, tính
    riêng cho từng API hay tính chung?
17. Khi vượt hạn mức, J&T trả **mã HTTP nào** và **`code` nào** trong thân trả lời? Chúng tôi
    cần biết chính xác để phân biệt "vượt hạn mức, chờ rồi thử lại" với "sai tham số, thử lại
    vô ích".
18. Có hạn mức riêng cho **môi trường thử** (`demoopenapi.jtexpress.vn`) khác với môi trường
    thật (`ylopenapi.jtexpress.vn`) không?
19. Giới hạn 30 mã vận đơn/lượt của API tra hành trình có áp cho các API khác không?

---

## CÂU HỎI 5 — Hai lớp tài khoản và điều kiện để chạy thử

### Chỗ chưa rõ

Tài liệu công khai in sẵn `apiAccount` và `privateKey` của **môi trường thử** ngay trên trang
(mục *接口信息* của từng API). Nhưng mọi `bizContent` còn đòi thêm `customerCode` và `password`,
mà tài liệu ghi là *"客户编码（客户合作网点提供）"* — do **bưu cục hợp tác của khách hàng cấp**,
không có trên trang.

### CÂU HỎI

20. Để chạy thử trên `demoopenapi.jtexpress.vn`, chúng tôi cần J&T cấp thêm **`customerCode` và
    `password` của môi trường thử** phải không? Xin cho biết thủ tục và người phụ trách.
21. `apiAccount`/`privateKey` in trên trang tài liệu là **dùng chung cho mọi đối tác** hay mỗi
    đối tác sẽ được cấp một bộ riêng sau khi hoàn tất *开发者认证* (bước 3)?
22. `password` trong `bizContent` có được **băm/mã hoá** không? Tài liệu cho hai ví dụ khác
    hẳn nhau trên cùng một API tạo đơn: `"password":"AF798EA591C460FC633D4567EC88E3FB"` (trông
    như MD5) ở ví dụ yêu cầu, nhưng bảng tham số lại ghi *"明文密码：H5CD3zE6"* (mật khẩu dạng
    rõ); còn API tra hành trình dùng `"password":"FbuEF5bDUc65+TN0HxnO+g=="` (trông như base64).
    **Phải gửi dạng nào?**
23. Dữ liệu tạo trên môi trường thử có **tự xoá** không, hay chúng tôi phải huỷ từng đơn thử?
24. Môi trường thử có **đẩy callback** về không, hay chỉ môi trường thật mới có?

---

## CÂU HỎI 6 — Tạo đơn, huỷ đơn, chống trùng

25. Tài liệu ghi `txlogisticId` *"不支持重复"* (không hỗ trợ trùng). Khi chúng tôi gửi lại **đúng
    một `txlogisticId` đã dùng**, J&T luôn trả `145003204 — 订单重复` và **không tạo đơn thứ
    hai**, đúng không? Đây là điều chúng tôi dựa vào để thử lại an toàn khi mạng đứt giữa
    chừng — xin xác nhận rõ.
26. Nếu yêu cầu tạo đơn **đứt giữa chừng** (chúng tôi không nhận được trả lời), cách đúng để
    biết đơn đã vào hay chưa là gì? Có API tra theo `txlogisticId` không, hay phải dùng
    `/api/logistics/trace`?
27. Huỷ đơn (`/api/order/cancelOrder`) được phép **đến trạng thái nào**? Sau khi đã lấy hàng
    (`106`) thì còn huỷ được không? Tài liệu chỉ có mã lỗi `999010010 — 当前订单状态无法取消`,
    không nói rõ ngưỡng.
28. Trường `prov` và `area` của `sender`/`receiver` được đánh dấu bắt buộc, còn `city` ghi là
    *"新的两级行政区划地址无需填写该字段，可以设置为 null"*. Với địa chỉ hành chính **hai cấp**
    mới của Việt Nam (từ 2025), `prov` và `area` phải điền **chính xác chuỗi nào**? Có bảng
    danh mục địa danh chuẩn để tải về không (ví dụ ví dụ trong tài liệu ghi
    `"Phường Nguyễn Thái Bình-028QQ107"` — có mã hậu tố)?
29. `codMoney` (tiền thu hộ) và `goodsValue` (giá trị khai) khác nhau ở chỗ nào, và `itemsValue`
    xuất hiện trong ví dụ nhưng **không có trong bảng tham số** — trường này còn dùng không?

---

## PHỤ LỤC — các trang tài liệu chúng tôi đã đọc

| Trang | Ngày đọc |
|---|---|
| `open.jtexpress.vn/apiDoc/index` (极兔API简介) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/orderserve/create` (创建订单) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/orderserve/cancel` (取消订单) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/fees/calculatingFees` (算费接口) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/vip/printOrder` (打印面单) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/logistics/query` (轨迹查询) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/logistics/statusFeedback` (轨迹回传) | 15/10/2026 |
| `open.jtexpress.vn/apiDoc/errorCode/index` (错误代码) | 15/10/2026 |

Trang `批量打印面单` (in nhãn hàng loạt) có trong trình đơn nhưng **chúng tôi chưa mở được nội
dung** — ghi ra để không ai tưởng đã đọc.
