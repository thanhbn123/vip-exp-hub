# G09 — KẾ HOẠCH KIỂM THỬ SANDBOX

**Soạn:** AG-03 CARRIER, 15/10/2026 · **Trạng thái:** **CHƯA CHẠY — BLOCKED.**
Điều kiện mở khoá: `docs/G09_CREDENTIALS_CHECKLIST.md`.

> Kế hoạch này viết **trước** khi có quyền, có chủ đích: viết sau khi đã cầm credentials thì
> người viết luôn bị cám dỗ đặt tiêu chí vừa khít với cái mình vừa chạy được.

---

## 0. Luật của lượt sandbox — bốn điều, đọc trước mọi bước

1. **Phép đo không đụng tới thứ cần đo thì kết quả ĐẠT của nó vô nghĩa.** Ca đã xảy ra thật:
   repo `vip-viettelpost` ngày 01/10/2026 báo `G08 PASS` rồi phải **rút lại** — vì với token
   tĩnh thì bước `authenticate` không gọi mạng, và `getPriceAll`/`getPrice` của `partnerdev`
   không kiểm token, nên **token bịa cũng PASS** (`CR-STG-007`). Mỗi bước dưới đây phải trả lời
   được: *nếu credentials sai, bước này có hỏng không?* Không hỏng ⇒ bước đó **không** được
   tính vào kết luận xác thực.
2. **Mỗi kết luận đi kèm phạm vi.** Không viết "sandbox ĐẠT". Viết "bước 1–3 đạt trên
   `demoopenapi.jtexpress.vn` ngày …; bước 4–5 chưa chạy".
3. **Không thử lại bước nào, kể cả bước chỉ đọc.** Bằng chứng phải phản ánh đúng **một** lượt
   gọi. Thao tác ghi thì tuyệt đối không tự thử lại (`app/transport.py` đã chặn).
4. **Dọn sạch những gì đã tạo.** Đơn thử tạo ra phải huỷ ngay trong cùng lượt; huỷ hỏng thì ghi
   mã vận đơn vào bằng chứng để người huỷ tay.

---

## 1. Trình tự — bảy bước, tăng dần mức nguy hiểm

Nguyên tắc xếp thứ tự: **bước nào không tạo dữ liệu ở hãng thì chạy trước.** Bước tạo dữ liệu
chỉ chạy khi mọi bước trước đã đạt.

| # | Bước | J&T endpoint | VTP endpoint | Tạo dữ liệu ở hãng? | Mặc định |
|---|---|---|---|---|---|
| 1 | Xác thực | — (ký từng lượt, không có bước login riêng) | `POST /v2/user/Login` → `POST /v2/user/ownerconnect` | không | chạy |
| 2 | Báo giá | `POST /api/spmComCost/getComCost` | `POST /v2/order/getPrice` | không | chạy |
| 3 | Danh sách dịch vụ | *(J&T không có API riêng)* | `POST /v2/order/getPriceAll` | không | chạy |
| 4 | Tra vận đơn **không tồn tại** | `POST /api/logistics/trace` | *(chưa biết endpoint — B7)* | không | chạy |
| 5 | **Tạo đơn thử** | `POST /api/order/addOrder` | `POST /v2/order/createOrder` | **CÓ** | **không** chạy, trừ khi có phiếu duyệt |
| 6 | **Huỷ đơn vừa tạo** | `POST /api/order/cancelOrder` | `POST /v2/order/UpdateOrder` `TYPE=4` | đưa đơn về huỷ | tự chạy ngay sau bước 5 |
| 7 | Nhận callback thật | hãng gọi vào URL của mình | như trên | không | chỉ khi có URL công khai (**V-G11-01, CHƯA CẤP**) |

### Bước 1 — cái bẫy cần tránh ở mỗi hãng

- **J&T:** không có API đăng nhập. Chữ ký được kiểm ở **mọi** lượt gọi, nên bước 2 đã là một
  phép thử xác thực thật. Nếu `apiAccount`/`privateKey` sai, bước 2 phải trả `145003030` (chữ
  ký sai) hoặc `145003010` (tài khoản không tồn tại). **Không thấy một trong hai mã đó mà vẫn
  đạt ⇒ nghi phép đo không đụng tới xác thực, dừng lại và xem lại.**
- **VTP:** nếu dùng `vtp_token` tĩnh thì bước 1 **không gọi mạng** — đúng cái bẫy đã nêu. Phải
  chạy ít nhất một lượt bằng `vtp_username` + `vtp_password`.

### Ca kiểm NGƯỢC bắt buộc (chứng minh phép đo có răng)

Trước khi tin bất kỳ kết quả ĐẠT nào, chạy **một lượt với credentials CỐ Ý SAI** và khẳng định
nó **HỎNG**. Phép đo nào không hỏng với credentials sai thì phép đo đó không đo xác thực.

| Ca | Làm gì | Phải ra gì |
|---|---|---|
| N1 | J&T: đổi một ký tự trong `privateKey` | `code = 145003030` hoặc `145003031` |
| N2 | J&T: `apiAccount` không tồn tại | `code = 145003010` |
| N3 | J&T: `customerCode`/`password` sai | `code = 999001030` |
| N4 | VTP: mật khẩu sai ở `POST /v2/user/Login` | phong bì `"error": true`, adapter phân loại `ViettelPostAuthError` |
| N5 | J&T: `timestamp` lệch 1 giờ | ghi lại hãng **có** từ chối hay không — đây chính là câu hỏi 13 gửi J&T |

---

## 2. Dữ liệu dùng để thử

- **Người gửi / người nhận:** dùng **địa chỉ và số điện thoại THẬT của công ty**, không dùng tên
  người thật khác, không dùng dữ liệu khách hàng. Đơn thử có thể bị bưu tá gọi điện thật.
- **Trọng lượng:** 0,5 kg. **Giá trị hàng:** 0 đồng. **COD: 0 đồng** — không để hãng đi thu tiền
  của ai trong một lượt thử.
- **`txlogisticId`:** `G09-SANDBOX-<YYYYMMDD-HHMMSS>` — mang giờ nên không bao giờ trùng, và
  nhìn là biết đơn thử.
- **Địa danh:** `prov`/`area` phải lấy từ danh mục của hãng (câu hỏi 28 gửi J&T, B11 gửi VTP).
  Chưa có danh mục thì bước 5 **không chạy** — đoán địa danh sẽ ra `1450033315` và làm hỏng cả
  lượt mà không học được gì.

---

## 3. Bằng chứng phải thu — và cái gì CẤM ghi vào bằng chứng

### Phải có

Một file JSON cho mỗi lượt chạy, gồm: URL gốc · giờ bắt đầu (có múi giờ) · với từng bước
`PASS/FAIL/SKIPPED/NOT_SAFE` + thời lượng ms + `code`/`msg` của hãng · `txlogisticId` và mã vận
đơn nếu bước 5 chạy · kết quả bước 6 · mã thoát.

Thêm hai thứ mà §12.1 đòi: **đo bằng công cụ nào** và **cái gì nằm ngoài phạm vi lượt này**.

### Cấm ghi

`privateKey`, `password`, `vtp_token`, nội dung header `digest` đầy đủ, số điện thoại người
thật. Lỗi chỉ ghi **tên lớp lỗi và mã của hãng**, không ghi nguyên văn trả lời nếu trong đó có
bí mật.

---

## 4. Tiêu chí ĐẠT — định nghĩa trước, không nới sau

| Mức kết luận | Điều kiện |
|---|---|
| `SANDBOX VERIFIED` cho **xác thực** | bước 1–2 đạt **và** ít nhất một ca N1–N4 hỏng đúng mã dự kiến |
| `SANDBOX VERIFIED` cho **báo giá** | bước 2 trả `code=1` và có `price` là số nguyên dương |
| `SANDBOX VERIFIED` cho **tạo đơn** | bước 5 trả `code=1` kèm `billCode`, **và** bước 6 huỷ được đơn đó |
| `SANDBOX VERIFIED` cho **huỷ đơn** | bước 6 trả `code=1` |
| `SANDBOX VERIFIED` cho **tra vận đơn** | bước 4 trả `code=1` với danh sách rỗng, **hoặc** mã "không tìm thấy" rõ ràng |
| `SANDBOX VERIFIED` cho **mã lỗi** | ít nhất 3 mã trong `loi_hang.JT_MA_LOI` quan sát được thật từ hãng |
| `SANDBOX VERIFIED` cho **callback** | bước 7 nhận được ít nhất một callback và **kiểm chữ ký đạt** |
| **`BLOCKED`** | bất kỳ bước nào không chạy được vì thiếu quyền/credentials/URL |

**Mọi hạng mục không có bước tương ứng ĐẠT thì giữ nguyên mức cũ.** Cấm nâng theo đà: tạo đơn
đạt **không** làm cho in nhãn thành đạt.

---

## 5. Câu hỏi được trả lời luôn trong lượt sandbox (khỏi phải chờ hãng)

| Câu hỏi | Bước nào trả lời | Cách đọc kết quả |
|---|---|---|
| J&T #12–13: `timestamp` là mốc Unix thật hay giờ UTC+7 quy đổi | ca N5 | gửi mốc Unix thật mà bị từ chối ⇒ hãng dùng cách (b) |
| J&T #22: `password` gửi dạng rõ hay băm | bước 2 với từng dạng | dạng nào không ra `999001030` thì dạng đó đúng |
| J&T #25: `txlogisticId` trùng có chặn thật không | gửi **lại** đúng `txlogisticId` của bước 5 | phải ra `145003204` và **không** sinh vận đơn thứ hai |
| J&T #1: `110` nghĩa là gì | bước 4 trên một vận đơn thật đã đi qua kho | đọc `scanTypeName` đi kèm `110` trong trả lời thật |
| J&T #16–17: hạn mức tần suất | gọi bước 2 liên tục 60 lượt/phút | ghi lại mã HTTP và `code` khi bị chặn |
| VTP B1: `104` có phải trạng thái cuối | chỉ trả lời được khi có callback thật (bước 7) | xem có sự kiện nào đến **sau** 104 không |

Riêng câu J&T #1: **kết quả quan sát một lượt KHÔNG đủ để chốt nghĩa.** Nó chỉ là một bằng
chứng để đính kèm khi hỏi hãng. Chốt nghĩa vẫn phải đi qua
`trang_thai_hang.chot_nghia(..., nguoi_chot, can_cu)` với văn bản trả lời của J&T làm căn cứ.

---

## 6. Chạy thế nào

```sh
export VIP_HUB_DATA=$(mktemp -d)              # CSDL thử riêng, KHÔNG dùng app/du-lieu/
export VIP_HUB_HARNESS_CHE_DO=SANDBOX
export VIP_HUB_HARNESS_DUYET=V-G09-01
export VIP_HUB_HARNESS_NGUOI_DUYET="<tên người duyệt>"
export VIP_HUB_HARNESS_CRED_FILE="$HOME/.config/vip-hub/g09-cred.json"
python3 app/migrate.py && python3 app/khoi_tao.py
python3 app/harness_hang.py SANDBOX
```

Hôm nay lệnh trên **sẽ từ chối chạy** và in ra đúng 4 điều kiện còn thiếu cho mỗi hãng. Đó là
hành vi đúng, không phải lỗi.

Bước 5 (tạo đơn thật) **không có đường chạy từ dòng lệnh**: nó đòi `PhieuDuyetLive` truyền trong
mã, mang người duyệt · thao tác · mã đơn · hạn dùng, và mỗi phiếu dùng được **một lần**.

---

## 7. Sau khi chạy

1. Ghi kết quả vào `docs/G09_FINAL_REPORT.md` mục 4, **sửa đúng những ô đã đo**, không sửa ô
   khác.
2. Nếu có hạng mục lên `SANDBOX VERIFIED`, thêm ca kiểm tương ứng vào `app/harness_hang.py` để
   lần sau máy canh được, chứ không dựa vào trí nhớ.
3. Đơn thử còn sót ở hãng thì ghi mã vận đơn vào báo cáo cho tới khi huỷ xong.
4. Ghi một dòng vào `wiki/log.md` và một mục vào `nhat-ky/ngay/` (luật §15 của `CLAUDE.md`).
