# G16-A — HỢP ĐỒNG CALLBACK J&T: CHỐT LẠI, VÀ CHỖ **CÒN BLOCKED**

Mã việc: **directive mục 13** · làn: **AG-04 (WEBHOOK)** · ngày **15/10/2026**.
Nền: `integration/g13-g15` @ `449bb2d`. Tài liệu này **kế thừa** `docs/G14_JT_WEBHOOK.md` —
không thay thế nó.

> ## ĐỌC DÒNG NÀY TRƯỚC
> **Mức của hợp đồng callback là `DOCUMENTED`, và KHÔNG có trường nào đạt mức cao hơn.**
> `webhook.HOP_DONG_MUC = "DOCUMENTED"` · `HOP_DONG_XAC_MINH_VOI_HANG = False` ·
> `PHAN_HOI_XAC_MINH = False`.
>
> **Một bản vá làm đường mã chạy được KHÔNG PHẢI là hợp đồng đã xác minh.** Lượt này **không**
> có lượt gọi hãng nào (kể cả sandbox), nên **không được** viết `SANDBOX VERIFIED`, **không
> được** viết `LIVE VERIFIED`, và **không câu nào** trong tài liệu này được đọc thành "hợp đồng
> đã được hãng xác nhận".

---

## 1. LƯỢT NÀY ĐÃ CHỐT ĐƯỢC GÌ (phần BIẾT ĐƯỢC)

Nguồn sự thật là **trích lục trong repo**, không phải trang web: `open.jtexpress.vn` là **SPA**,
`fetch` tĩnh chỉ trả về vỏ rỗng. Hai trích lục: `docs/JT_CAU_HOI_CHINH_THUC.md` (câu 2–15) và
`docs/G12_JT_DANG_KY.md` mục 5.

Hợp đồng nằm trong mã, **máy đọc được**: `app/webhook.py` → `HOP_DONG_CALLBACK`,
`bao_cao_hop_dong_callback()`, `kiem_hop_dong_khong_tu_nang_muc()`.

| Trường | Mức | Nội dung |
|---|---|---|
| `than_yeu_cau` | `DA_TAI_LIEU` | form `application/x-www-form-urlencoded`, một trường `bizContent` |
| `header_bat_buoc` | `DA_TAI_LIEU` | đúng ba header: `apiAccount` · `digest` · `timestamp` |
| `cong_thuc_chu_ky` | `DA_TAI_LIEU` | `digest = base64( md5-BYTES( <chuỗi JSON của bizContent> + privateKey ) )` — md5 ra **mảng byte** rồi mới base64 |
| `moc_thoi_gian_scan` | `DA_TAI_LIEU` | `scanTime` trong `details`; hai định dạng đã thấy: `YYYY-MM-DD HH:MM:SS` và `YYYY-MM-DDTHH:MM:SS` |
| `dinh_danh_su_kien` | `SUY_RA` | khoá tổ hợp `billCode \| scanTime \| scanTypeCode` (băm SHA-256, 24 hex) — **do mình chọn**, hãng chưa xác nhận |
| `dinh_danh_url_phia_nhan` | `SUY_RA` | `/api/v2/webhook/nhan/<webhook_ma>` — đường **của hub**, chưa đăng ký với hãng (`V-G11-01`) |

**18 trường** trong hợp đồng; **12** trường `CHUA_TAI_LIEU`; **10** trong số đó nằm trong bảng
chặn (`CHAN_HOP_DONG_CALLBACK`) kèm câu hỏi gửi hãng và đường mã đang bị chặn.

Lượt này **không đổi thuật toán ký** và **không thêm sơ đồ xác thực nào**. Ca thử `test_k03`
canh đúng điều đó: `xac_thuc_jt_digest` phải còn `hashlib.md5` + `base64.b64encode`, **không**
được có `hmac.new`/`sha256`, và `BO_XAC_THUC` phải vẫn đúng hai sơ đồ `hub_hmac` + `jt_digest`.

---

## 2. NĂM CHỖ HỞ OWNER CHỈ ĐÍCH DANH — **BLOCKED**, KÈM ĐÚNG CÁI CÒN THIẾU

Mỗi dòng dưới đây có mặt trong `webhook.CHAN_HOP_DONG_CALLBACK` với năm khoá:
`cau_hoi` · `thieu` · `doan_thi_hong` · `dang_chan` · `go_khi`.

| # | Chỗ hở | Câu hỏi | **Chính xác cái còn thiếu** | Đoán thì hỏng thế nào |
|---|---|---|---|---|
| **1** | `khoa_ky_chieu_callback` | câu 6 · G14 §8 **B1** | Tài liệu **không nói** chiều callback ký bằng `privateKey` của tài khoản API của mình hay bằng một **khoá riêng** J&T cấp cho chiều callback | Đoán khoá ⇒ chữ ký **đúng** của hãng vẫn bị từ chối: **mất sạch callback**, lỗi hiện ra chỉ là "digest không khớp" |
| **2** | `chuoi_dem_di_ky` | câu 7 · G14 §8 **B1** | Chuỗi đem đi ký: **chỉ** chuỗi JSON `bizContent`, hay **toàn bộ thân form** (`bizContent=...`), hay chuỗi khác. Chưa có ví dụ đối chiếu từng byte | Đoán chuỗi ký ⇒ **từ chối sạch** mọi callback thật, không lỗi nào chỉ đúng nguyên nhân |
| **3** | `phuong_thuc_http` | câu 2 · G14 §8 **B2** | **Phương thức HTTP** của callback (`轨迹回传`). Trích lục chỉ tả THÂN và HEADER | Ghi `POST` thành dữ kiện là bịa; nếu hãng dùng phương thức khác thì cửa ingest **không có route**, callback rơi vào 404/405 |
| **4** | `phan_hoi_xac_nhan` | câu 9 · G14 §8 **B3** | **Hình dạng ĐẦY ĐỦ** của thân phản hồi: mã HTTP nào là "đã nhận", còn trường nào ngoài `code`, `200`/`202` có bị coi là hỏng không. Biết đúng **một mảnh**: có trường `code`, `code=1` là được nhận | Đoán mã HTTP ⇒ hãng coi **mọi** callback là hỏng và **đẩy lại vô hạn**: chống trùng ở CSDL cứu **dữ liệu**, không cứu **tải** |
| **5** | `chinh_sach_thu_lai` | câu 9 · G14 §8 **B4** | Số lần J&T **thử lại**, khoảng cách giữa các lần, và J&T có **đẩy trùng** một sự kiện không | Không biết thì không chọn được trần thử lại của phía nhận, và không biết khoá chống trùng của mình có che đúng ca trùng thật |

### Năm chỗ hở CÙNG LOẠI, tìm thêm khi rà lại trích lục

| Chỗ hở | Câu hỏi | Còn thiếu |
|---|---|---|
| `y_nghia_apiaccount` | câu 8 | `apiAccount` trong header callback là tài khoản của **mình** hay của **J&T** — quyết định phép kiểm phụ trong `xac_thuc_jt_digest` có nghĩa hay không |
| `sandbox_co_day_callback` | câu 24 | Môi trường **THỬ** có đẩy callback không, hay chỉ môi trường thật |
| `thu_tu_nhieu_su_kien` | câu 11 | Nhiều sự kiện cùng lúc có **bảo đảm thứ tự** không |
| `do_lech_gio_chap_nhan` | câu 13 | J&T chấp nhận **lệch giờ tối đa** bao nhiêu |
| `moc_du_lieu_them` | câu 29 + **D-9** | `codMoney`/`goodsValue`/`itemsValue` khác nhau chỗ nào; ánh xạ `area`/`city` cho địa chỉ hai cấp Việt Nam |

**`header_timestamp`** vẫn `CHUA_TAI_LIEU` nhưng **được giữ giá trị nguyên văn** (`mili giây;
tài liệu ghi '时区：UTC+7'`) — chép nguyên văn thì kiểm được, diễn giải lại thì không. Đây là
trường **duy nhất** được phép có `gia_tri` mà vẫn ở mức `CHUA_TAI_LIEU`, và danh sách đó nằm
trong mã (`GIA_TRI_NGUYEN_VAN_DUOC_PHEP`).

---

## 3. VÌ SAO **KHÔNG** ĐƯỢC ĐOÁN THUẬT TOÁN KÝ

Ba lý do, và cả ba đều đã đo được chứ không phải suy đoán:

1. **Công thức là của tài liệu, nhưng hai ĐẦU VÀO thì không.** `base64(md5(bizContent +
   privateKey))` chỉ nói *cách trộn*. Nó **không** nói (a) khoá nào, (b) chuỗi nào. Hai ẩn số,
   một phương trình — đoán một trong hai là **từ chối sạch** hoặc **nhận sạch**.
2. **Sai ở đây không có thông báo nào chỉ đúng chỗ.** Chữ ký sai ⇒ `digest không khớp`, một câu
   giống nhau cho mọi nguyên nhân. Không có cách nào phân biệt "sai khoá" với "sai chuỗi ký" từ
   phía nhận.
3. **Tin vào một ví dụ tự nghĩ ra là tự lừa.** Nếu ta tự ký rồi tự kiểm (đúng như bộ thử MOCK
   đang làm), ta chỉ chứng minh **đường mã của mình** khớp với **giả định của mình**. Đó là lý
   do bộ thử ghi rõ `ĐẠT (MOCK)`, không ghi `ĐẠT`.

Vì vậy `xac_thuc_jt_digest()` giữ nguyên, **có ghi chú giả định ngay trong docstring**, và mức
của nó ở lại `DOCUMENTED`. Gỡ được chỉ khi hãng trả lời **B1** kèm **ví dụ đủ ba thứ**.

---

## 4. BẤT BIẾN AN TOÀN — GIỮ NGUYÊN, VÀ CÁCH ĐO LẠI ĐƯỢC

AG-01 đã nghiệm thu độc lập năm tính chất dưới đây (`docs/QA_G13_G15.md` §L2.5). Lượt này
**không sửa hành vi nào của đường cập nhật**, và mỗi tính chất đều có **phép đo lặp lại được** —
cả trong bộ thử lẫn trong harness:

| # | Bất biến | Ca thử canh | Phép đo trong harness G16 |
|---|---|---|---|
| 1 | **Tenant CHỈ đến từ `carrier_account`**; payload khai tenant khác thì **ghi audit rồi bỏ qua** | `test_d07`, `test_d08`, `test_k08` | **G06d/G06d2** — payload khai tenant B, account thuộc tenant A: đơn của A đi tiếp, `webhook_claim_tenant_bi_bo_qua` tăng, tenant B **0 đơn · 0 sự kiện** |
| 2 | **Chống trùng do CSDL cưỡng chế** (`UNIQUE(carrier_account_id, event_id)`), không bằng `if` | `test_c01`, `test_c02`, `test_c03`, `test_c04` | **G06b/G06b2** — gửi lại y nguyên ⇒ 1 dòng; **nhồi thẳng bằng SQL** vẫn bị `IntegrityError`; `sqlite_master` chứa ràng buộc |
| 3 | Mã `110` / mã lạ ⇒ `NEEDS_REVIEW`, **0 dòng** ở `tc_cod`/`tc_cod_chuyen`/`tc_but_toan`, không `DELIVERED` | `test_f01`–`test_f07` | **G06e-110/G06e-9999/G06e2/G06e3** — `can_soat=1`, `trang_thai_chuan=None`, ba bảng sổ **0→0**, trục giao vận không thành `giao_thanh_cong` |
| 4 | **Đúng MỘT nơi** ghi cột watermark, và **chỉ khi sự kiện ĐƯỢC ÁP** | `test_e03`, `test_e04`, `test_e05`, `test_e08`, `test_e09` | **G11a** — đếm trong `webhook.py`: **đúng 1** câu `UPDATE wh_su_kien SET hang_moc_thoi_gian`, và điều kiện `if ap_dung and moc:` có mặt |
| 5 | Tầng ĐỌC vẫn lọc `trang_thai_chuan IS NOT NULL` (cứu dữ liệu do **mã CŨ** ghi trong CSDL THẬT) | `test_e09` | **G11b** — bộ lọc còn nguyên trong `watermark()` |

Thêm hai chốt cấu trúc được đo trong **G11c/G11d**: `webhook.py` không có `urllib.request` /
`socket.socket` / `http.client` / `CHO_PHEP_LIVE = True`, và ràng buộc `UNIQUE` có thật trong
schema CSDL **đang chạy** (không chỉ trong DDL).

> **Vì sao phải đo lại thay vì tin lời khai:** ba trong năm tính chất trên từng **sai thật** ở
> G14 (watermark bị mã không-được-áp đầu độc, hai tầng). Một tài liệu nói "đã vá" không phải
> bằng chứng; một phép đo lặp lại được thì có.

---

## 5. BỘ THỬ — LỆNH THẬT, KẾT QUẢ THẬT

```bash
VIP_HUB_DATA=/tmp/veh_g16_ag04 python3 app/thu/thu_webhook_jt.py
```

```
Ran 77 tests in 0.775s

OK
CSDL thử G14: /tmp/veh_g16_ag04/g14-fcz48yl2
```

67 ca của G14 **giữ nguyên và vẫn xanh**; lượt này thêm **nhóm `K_G16_HopDongVaChotAnToan`**
(10 ca) phủ đúng các mục directive yêu cầu:

| Ca | Đo gì |
|---|---|
| `k01` | báo cáo hợp đồng máy đọc được · mức `DOCUMENTED` · bất biến trung thực không vi phạm |
| `k02` | **năm chỗ hở Owner chỉ đích danh** đều `CHUA_TAI_LIEU`, `gia_tri=None`, đủ 5 khoá, trỏ đúng câu hỏi |
| `k03` | **không đoán thuật toán ký**: vẫn `md5`+`base64`, không `hmac.new`/`sha256`, không sơ đồ thứ hai — **kèm đối chứng dương** (công thức tài liệu vẫn được chấp nhận) |
| `k04` | callback sandbox vẫn `BLOCKED` kèm `V-G09-01` + `V-13906-05`; hai môi trường dưới `mock` chưa được cấp quyền |
| `k05` | **harness THẬT từ chối chạy** khi một chốt bị mở (mã thoát 4, và **không** dựng CSDL) |
| `k06` | **tự kiểm bộ dò chốt an toàn**: 10/10 cấu hình, mỗi ca hỏng bị bắt bởi **đúng chốt** |
| `k07` | **tự kiểm bộ thử**: ca cố ý hỏng ⇒ mã thoát ≠ 0 và **không** có `OK`; ca lành ⇒ thoát 0 + `OK` |
| `k08` | **tenant không tồn tại**: sự kiện đi `khong_khop`, 0 dòng đơn bị đụng — **kèm đối chứng dương** (cùng payload qua account đúng tenant thì **áp được**) |
| `k09` | account mất tenant (dữ liệu hỏng) ⇒ `LoiVinhVien` ⇒ **DLQ**, không nổ |
| `k10` | **bảng phủ**: 20 hành vi directive yêu cầu đều có một ca THẬT canh; đọc danh sách ca bộ chạy nạp, nên xoá/đổi tên ca canh là hỏng ngay |

### Ba lỗi của CHÍNH BỘ THỬ trong lượt này — ghi lại, không giấu

1. `k07` bản đầu chỉ đọc `stdout`, mà `unittest` in bảng tổng kết ra **`stderr`** ⇒ ca HỎNG vì lý
   do của chính nó. Đã sửa bằng cách gộp hai luồng. Đúng bài học: **thứ dùng để kiểm chứng phải
   được kiểm trước khi tin.**
2. Một câu chữ mới trong `webhook.py` nhắc tên ba bảng sổ COD, và ca `test_f08` (canh "webhook
   không có đường nào chạm vào tiền") **bắt được ngay**. Đã viết lại câu chữ. **Chốt chặn cũ
   hoạt động đúng** — đây là bằng chứng, không phải sự cố.
3. `test_k10` bản đầu dùng `TestSuite.iter_tests()` (không có trong Python 3.9) — đã thay bằng
   đệ quy `TestSuite` thuần.

---

## 6. BLOCKED — ĐIỀU KIỆN GỠ, VÀ AI GỠ

| Việc đang chặn | Còn thiếu **chính xác** | Gỡ khi |
|---|---|---|
| Xác minh chữ ký callback | câu 6 + câu 7 kèm **ví dụ đủ ba thứ** (chuỗi gốc · khoá che bớt · `digest`) | hãng trả lời |
| Nhận callback thật | **phương thức HTTP** (câu 2) + **URL công khai** (`V-G11-01` **CHƯA CẤP**) | hãng trả lời + Owner cấp `V-G11-01` |
| Phản hồi đúng hình dạng | **mã HTTP + các trường còn lại** của thân phản hồi (câu 9) | hãng trả lời |
| Trần thử lại của phía nhận | **số lần + khoảng cách** J&T thử lại (câu 9) và **cách họ chống trùng** (câu 10) | hãng trả lời |
| Chạy sandbox | `V-G09-01` (gọi API hãng, kể cả sandbox) + `V-13906-05` (credentials sandbox) — **cả hai CHƯA CẤP** | Owner cấp |
| Gỡ ký ức về `110` | câu 1–3 (D-4 / `V-13906-04`) | hãng trả lời |
| Callback sandbox có tồn tại không | câu 24 | hãng trả lời |

**Không có đường tắt nào trong bảng này.** Cả bảy dòng đều là "chờ một câu trả lời từ bên
ngoài", không phải "chờ ai đó viết thêm mã".

---

## 7. RỦI RO CÒN LẠI — GHI RA, KHÔNG GIẤU

1. **Phép kiểm `apiAccount` là phép kiểm PHỤ có thể bị bỏ qua**: nó chỉ chạy khi credentials
   giải mã được **và** account có lưu `apiAccount`. Không giải mã được thì bỏ qua (chữ ký chính
   vẫn đã đúng). Cố ý, có ghi trong mã — nhưng nghĩa là **câu 8 chưa trả lời thì nó không phải
   một chốt chặn**.
2. **Ngưỡng chống phát lại 15 phút là con số CỦA MÌNH.** Câu 12/13 chưa trả lời; nếu `timestamp`
   của hãng theo cách hiểu (b) thì lệch **đúng 7 tiếng** và mọi callback bị từ chối sạch — mà
   chữ ký vẫn đúng nên rất khó nhìn ra.
3. **`HOP_DONG_CALLBACK` là ảnh chụp của trích lục, không phải của hãng.** Nếu hãng đổi tài liệu,
   bảng này **không tự biết**. Nó chỉ ngăn được việc **tự nâng mức mà không có căn cứ**.
4. **Bốn làn chạy chung một cây**: `adapter_jt.py` đã đổi chữ ký hàm **trong lúc** lượt này chạy
   và bộ dò chốt an toàn bắt được ngay (xem `docs/G16_SANDBOX_HARNESS.md` §2). Kết luận trong
   tài liệu này có hiệu lực cho **nội dung tệp tại thời điểm đo**; tệp đổi thì phải đo lại.

---

## 8. NHỮNG CÂU **KHÔNG ĐƯỢC** ĐỌC RA TỪ TÀI LIỆU NÀY

- "Hợp đồng callback đã được xác minh với J&T" — **sai**. Mức là `DOCUMENTED`.
- "Callback J&T đã chạy thật" — **sai**. Chưa có lượt gọi hãng nào.
- "Sandbox đã đạt" — **sai**. `V-G09-01` + `V-13906-05` chưa cấp.
- "Hình dạng phản hồi đã đúng" — **sai**. Mới có **một mảnh** (`code=1`).
- "Đã hiểu mã `110`" — **sai**. `110` vẫn đi `NEEDS_REVIEW`, **không bao giờ** `DELIVERED`,
  **không** kích hoạt đối soát COD.
