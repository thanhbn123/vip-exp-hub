# G12 — HỒ SƠ ĐĂNG KÝ J&T EXPRESS: LÀM GÌ, Ở ĐÂU, THEO THỨ TỰ NÀO

**Soạn:** AG-03 CARRIER ENGINEER, 15/10/2026 · **Trạng thái việc:** D-5 — *"Chưa cấp; chuẩn bị
tài liệu đăng ký và kiểm thử."*

> **Người đi đăng ký KHÔNG cần biết gì về hệ thống VIP EXPRESS HUB.** File này viết cho người
> đó. Mỗi bước ghi đủ: làm ở đâu, ai làm được, cần gì, xong thì có gì trong tay.
>
> **File này KHÔNG chứa và KHÔNG BAO GIỜ được chứa một credentials nào** — §15.2 của
> `CLAUDE.md`. Chỗ điền ở mục 4 là để ghi **đã có hay chưa**, không phải để ghi giá trị.

---

## 0. HIỂU ĐÚNG MỘT ĐIỀU TRƯỚC KHI BẮT ĐẦU — có hai lớp tài khoản, không phải một

Đây là chỗ hầu hết mọi người nhầm, và nhầm ở đây thì đi hết quy trình vẫn **không gọi được API**.

| Lớp | Hai trường | Ai cấp | Lấy bằng cách nào |
|---|---|---|---|
| **Lớp A — nền tảng** | `apiAccount`, `privateKey` | J&T Open Platform | Tự xem trong **控制台 (Console)** sau khi xong bước 3. Tài liệu: *"apiAccount和privateKey可在控制台内查看"* |
| **Lớp B — hợp đồng khách** | `customerCode`, `password` | **BƯU CỤC HỢP TÁC của J&T** | Phải liên hệ bưu cục. Tài liệu ghi: *"客户编码（客户合作网点提供）"* — mã khách do **bưu cục hợp tác cấp** |

**Có lớp A mà không có lớp B thì vẫn không tạo được đơn nào.** `customerCode` và `password` nằm
trong `bizContent` của mọi yêu cầu nghiệp vụ, và chúng **không có trên trang tài liệu**.

⇒ **Hai việc này chạy SONG SONG, không nối tiếp.** Đừng đợi xong lớp A rồi mới đi hỏi bưu cục —
lớp B là đường chậm nhất và phụ thuộc người ngoài.

---

## 1. NĂM BƯỚC CHÍNH THỨC — chép nguyên văn từ trang `极兔API简介`

Đọc bằng trình duyệt tại `open.jtexpress.vn/apiDoc/index`, ngày **15/10/2026** (trang là SPA,
`curl` không đọc được nội dung). Mục **对接流程** (quy trình đối tiếp):

| # | Nguyên văn | Dịch | Ai làm được | Cần gì | Mất bao lâu |
|---|---|---|---|---|---|
| 1 | *注册用户，注册成为极兔开放平台的一员* | Đăng ký tài khoản, thành thành viên J&T Open Platform | **Anh Thành tự làm được.** Nút *注册* góc phải trên `open.jtexpress.vn` | Email + số điện thoại công ty | **Tài liệu KHÔNG nói** |
| 2 | *申请成为开发者，完善开发者信息，成为极兔开放平台普通开发者* | Xin làm nhà phát triển, điền thông tin, thành **nhà phát triển thường** | **Anh Thành tự làm được** | Thông tin nhà phát triển — tài liệu **không liệt kê cụ thể** gồm những gì | **Tài liệu KHÔNG nói** |
| 3 | *开发者认证，完善开发者信息，获取全部接口权限，可使用订单服务、电子面单服务等* | **Chứng thực nhà phát triển.** Xong bước này mới **mở đủ quyền** dùng dịch vụ đơn hàng và nhãn điện tử | **Cần J&T duyệt.** Không tự phục vụ | Hồ sơ chứng thực doanh nghiệp — tài liệu **không liệt kê giấy tờ**. Dự phòng: giấy phép kinh doanh, mã số thuế, người đại diện | **Tài liệu KHÔNG nói** |
| 4 | *联调测试，调试测试环境接口服务，与具体的接口服务人员沟通解决问题* | **Chạy thử trên môi trường test**, *"trao đổi với nhân viên phụ trách interface cụ thể"* | **Bắt buộc có người của J&T đi kèm** | Đã xong bước 3 **và** đã có lớp B | **Tài liệu KHÔNG nói** |
| 5 | *发布上线，联调测试通过后，联系具体的接口服务人员，确认上线细节* | Lên thật, sau khi bước 4 đạt, liên hệ nhân viên phụ trách chốt chi tiết | Cần J&T | Bước 4 đạt | **Tài liệu KHÔNG nói** |

> **Tài liệu không nêu thời hạn cho bất kỳ bước nào, cũng không liệt kê giấy tờ cần nộp.** Ghi
> ra để không ai lập kế hoạch dựa trên một con số tự nghĩ. Hỏi thời hạn ngay ở bước 1–2.
>
> **Không có đường tự phục vụ.** Bước 3 và bước 4 đều cần người của J&T. Việc cần làm sớm nhất
> là **có được một người liên hệ phía J&T** — xem mục 2.

---

## 2. THỨ TỰ LÀM THỰC TẾ — ba việc, hai đường song song

```
         ┌─ ĐƯỜNG A (tự làm, bắt đầu ngay) ────────────────────────┐
  HÔM    │ A1 đăng ký tài khoản → A2 xin làm dev → A3 chứng thực   │→ apiAccount + privateKey
  NAY ───┤                                            (J&T duyệt)  │
         ├─ ĐƯỜNG B (phụ thuộc người ngoài — CHẬM NHẤT) ───────────┤
         │ B1 liên hệ bưu cục J&T → B2 ký hợp đồng khách hàng      │→ customerCode + password
         │                        → B3 xin cấp mã môi trường TEST  │
         └─────────────────────────────────────────────────────────┘
                                   ↓ (cần ĐỦ CẢ HAI)
                       C. 联调测试 — chạy thử cùng người của J&T
                                   ↓
                       D. 发布上线 — lên thật
```

**Việc nên làm đầu tiên trong ngày đầu tiên:** gọi/đến **bưu cục J&T đang hợp tác** và hỏi đúng
ba câu — đây là đường dài nhất:

1. Công ty tôi muốn tích hợp API J&T. Ai bên J&T phụ trách việc này cho khách doanh nghiệp?
2. Để có `customerCode` và `password` (mã khách hàng dùng cho API) thì cần làm gì, ký gì?
3. Có cấp `customerCode`/`password` cho **môi trường thử** (`demoopenapi.jtexpress.vn`) không,
   hay chỉ cấp cho môi trường thật?

Có tên và số điện thoại của **một người phụ trách** là đã gỡ được nút thắt lớn nhất, vì bước 3,
bước 4 và cả 29 câu hỏi kỹ thuật đều cần người đó.

---

## 3. HAI MÔI TRƯỜNG — đừng nhầm, và đừng chạm cái thứ hai

| Môi trường | Host | Dùng khi nào |
|---|---|---|
| **Thử (test)** | `demoopenapi.jtexpress.vn` | Toàn bộ việc kiểm thử. **Chỉ được dùng cái này** |
| **Thật (production)** | `ylopenapi.jtexpress.vn` | Chỉ sau bước 5, và chỉ khi Owner duyệt riêng |

> Trang tài liệu **in sẵn một `apiAccount` và một `privateKey` của môi trường thử** ở mục
> *接口信息* của mỗi trang API. Chúng tôi **cố ý không chép giá trị đó vào bất kỳ file nào của
> dự án**: dù là giá trị công khai, chép khoá vào kho tri thức là tạo tiền lệ sai, và đến khi có
> khoá thật thì không ai phân biệt được nữa. Ai cần thì mở đúng trang tài liệu mà xem.
> Và **có hai trường đó vẫn chưa tạo được đơn thử** — vẫn thiếu lớp B (mục 0).

---

## 4. DANH SÁCH THÔNG TIN PHẢI XIN — checklist điền được

In ra, điền cột *Đã có?* bằng **có / chưa**. **Không điền giá trị vào đây.**

### 4.1 Credentials — bốn trường

| # | Trường | Lớp | Xin ai | Đã có? | Ngày có | Ghi chú |
|---|---|---|---|---|---|---|
| 1 | `apiAccount` | A | Console, sau bước 3 | ☐ chưa | | |
| 2 | `privateKey` | A | Console, sau bước 3 | ☐ chưa | | |
| 3 | `customerCode` | B | Bưu cục hợp tác | ☐ chưa | | |
| 4 | `password` | B | Bưu cục hợp tác | ☐ chưa | | **Hỏi luôn: gửi dạng nào?** (câu hỏi 22 — tài liệu cho **ba** dạng mâu thuẫn) |

### 4.2 Người liên hệ — không có người thì không qua được bước 3 và 4

| # | Cần gì | Đã có? | Nội dung |
|---|---|---|---|
| 5 | Tên nhân viên J&T phụ trách tích hợp API (接口服务人员) | ☐ chưa | |
| 6 | Số điện thoại / email / kênh chat của người đó | ☐ chưa | |
| 7 | Tên và liên hệ bưu cục hợp tác | ☐ chưa | |
| 8 | Bước 3 và 4 cần nộp giấy tờ gì, mất bao lâu | ☐ chưa | Tài liệu **không nói** — phải hỏi |

### 4.3 Dữ kiện kỹ thuật phải xin kèm — thiếu là không chạy thử được

| # | Cần gì | Đã có? | Vì sao chặn |
|---|---|---|---|
| 9 | **Danh mục địa danh chuẩn** của J&T (tải về được không?) | ☐ chưa | **Chặn cứng việc tạo đơn.** Xem mục 6 |
| 10 | `customerCode`/`password` cho **môi trường thử** | ☐ chưa | Không có thì không chạy thử được lượt nào |
| 11 | Môi trường thử **có đẩy callback** không | ☐ chưa | Quyết định có kiểm được webhook trước khi lên thật hay không |
| 12 | Dữ liệu tạo trên môi trường thử **có tự xoá** không | ☐ chưa | Quyết định có phải huỷ tay từng đơn thử không |
| 13 | URL công khai để J&T gọi callback về | ☐ chưa | **`V-G11-01` CHƯA CẤP** — việc của anh Thành, không phải của J&T |

---

## 5. 29 CÂU HỎI — SẮP LẠI THEO THỨ TỰ ƯU TIÊN

Nội dung đầy đủ từng câu: `docs/JT_CAU_HOI_CHINH_THUC.md` (giữ nguyên số thứ tự gốc, **không
đánh số lại** — đánh số lại làm hỏng mọi con trỏ đang trỏ tới).

**Tiêu chí xếp:** câu nào mà **không có trả lời thì không làm tiếp được việc gì** đứng trước.
Không xếp theo mức thú vị, cũng không theo thứ tự tài liệu.

### NHÓM 1 — CHẶN MỌI THỨ. Thiếu một câu là không gọi nổi lượt API đầu tiên

| Thứ tự hỏi | Câu gốc | Hỏi về | Không có thì hỏng thế nào |
|---|---|---|---|
| **1** | **20** | Môi trường thử có cần `customerCode`/`password` riêng không, thủ tục và người phụ trách | **Không chạy được lượt thử nào.** Đây là nút thắt số một |
| **2** | **22** | `password` gửi dạng **rõ, MD5 hay base64**? Tài liệu cho **ba ví dụ mâu thuẫn nhau** trên cùng một API | Sai dạng ⇒ **mọi** lượt gọi bị từ chối, và thông điệp lỗi sẽ chỉ nói "sai mật khẩu" — mất hàng giờ chẩn đoán nhầm hướng |
| **3** | **21** | `apiAccount`/`privateKey` in trên trang là **dùng chung** hay mỗi đối tác một bộ riêng | Quyết định có phải chờ xong bước 3 mới thử được hay không |
| **4** | **12** | `timestamp` là mốc Unix thật **(a)** hay giờ treo tường UTC+7 quy đổi **(b)** — hai cách lệch **7 tiếng** | Sai ⇒ bị từ chối sạch ở lớp chống phát-lại, mà chữ ký vẫn đúng nên **rất khó nhìn ra** |
| **5** | **13** | J&T chấp nhận lệch giờ tối đa bao nhiêu | Không biết thì không đặt nổi ngưỡng đồng bộ giờ máy chủ |

### NHÓM 2 — CHẶN ĐƯỜNG TẠO ĐƠN. Có nhóm 1 rồi vẫn không tạo nổi đơn nếu thiếu nhóm này

| Thứ tự hỏi | Câu gốc | Hỏi về | Không có thì hỏng thế nào |
|---|---|---|---|
| **6** | **28** | **`prov`/`area` điền chính xác chuỗi nào** với địa chỉ hành chính **hai cấp** của Việt Nam từ 2025, và có **danh mục địa danh chuẩn** tải về không | **Đây là D-9.** Xem mục 6 — câu này hiện đang có **chốt chặn cứng** trong mã chặn đường LIVE |
| **7** | **29** | `codMoney` và `goodsValue` khác nhau chỗ nào; `itemsValue` còn dùng không | Nhầm cột COD ⇒ **hàng đi, tiền không về, và không có lỗi nào báo** — hỏng im lặng đúng nghĩa |
| **8** | **25** | Gửi lại đúng một `txlogisticId` đã dùng thì J&T **luôn** trả `145003204` và **không tạo đơn thứ hai**, đúng không | Toàn bộ chính sách thử lại an toàn đang **dựa vào** điều này. Sai ⇒ mạng đứt một lần là **đơn đôi** |
| **9** | **26** | Yêu cầu tạo đơn đứt giữa chừng thì tra bằng gì — có API tra theo `txlogisticId` không | Không có ⇒ không đối soát được, đơn treo ở trạng thái "không rõ" |
| **10** | **27** | Huỷ đơn được đến trạng thái nào; sau khi đã lấy hàng (`106`) còn huỷ được không | Không biết ⇒ không dọn được đơn thử, và không biết lúc nào nút Huỷ phải tắt |
| **11** | **23** | Dữ liệu môi trường thử có tự xoá không | Quyết định quy trình dọn sau mỗi lượt thử |

### NHÓM 3 — CHẶN VIỆC ĐỌC ĐÚNG TRẠNG THÁI (D-4). Đơn đi được rồi nhưng không biết nó đang ở đâu

| Thứ tự hỏi | Câu gốc | Hỏi về |
|---|---|---|
| **12** | **1** | **`scanTypeCode = 110`** nghĩa là *hàng đến kho* hay *kiện có vấn đề* — tài liệu nói **hai nghĩa ngược nhau trên cùng một trang** |
| **13** | **2** | Có phải đang tồn tại **hai bộ mã** khác nhau (`103…121` và `10/50/92/94/100/110`)? Bộ nào cho khách Việt Nam, bộ nào cho API tra hành trình, bộ nào cho callback |
| **14** | **3** | Xin **danh sách đầy đủ, chính thức** mọi `scanTypeCode`, kèm tên tiếng Việt và tiếng Anh |
| **15** | **4** | Mã `121` (FINISH) phát sinh sau giao thành công hay sau hoàn hàng, hay cả hai |
| **16** | **5** | `104` (Pickup Failure) và `118` (Delivery Problem) khác nhau thế nào |

> Hiện hệ thống **không áp trạng thái nào** cho `110` và đánh dấu "cần soát bằng người". Đó là
> mức an toàn, nhưng nó biến mọi kiện đi qua kho thành việc cho người — **không dùng lâu dài
> được**. Có câu 1–3 là gỡ được. **Cho tới lúc đó: không thêm mã nào vào bảng ánh xạ** (D-4).

### NHÓM 4 — CHẶN CALLBACK. Hiện đằng nào cũng đang bị chặn bởi `V-G11-01`, nên xếp sau

| Thứ tự hỏi | Câu gốc | Hỏi về |
|---|---|---|
| **17** | **6** | Callback J&T gửi về được ký bằng **khoá nào** — `privateKey` của mình hay khoá riêng J&T cấp |
| **18** | **7** | **Chuỗi nào** được đem đi ký; xin một ví dụ đủ: chuỗi gốc, khoá (che bớt), `digest` kết quả |
| **19** | **8** | `apiAccount` trong header callback là tài khoản của mình hay của J&T |
| **20** | **24** | **Môi trường thử có đẩy callback không**, hay chỉ môi trường thật |
| **21** | **10** | Dùng trường nào làm **khoá chống trùng** — `details` không có mã sự kiện duy nhất |
| **22** | **9** | J&T thử lại callback mấy lần, cách nhau bao lâu |
| **23** | **11** | Nhiều sự kiện cùng lúc có **bảo đảm thứ tự** không |
| **24** | **14** | `timestamp` trong header callback theo cách hiểu nào (như câu 12) |
| **25** | **15** | `scanTime` là giờ Việt Nam hay UTC; định dạng chuẩn là cái nào (tài liệu cho **hai** định dạng) |

### NHÓM 5 — ĐIỀU CHỈNH, KHÔNG CHẶN. Thiếu thì chạy chậm/kém tối ưu, không phải chạy sai

| Thứ tự hỏi | Câu gốc | Hỏi về |
|---|---|---|
| **26** | **17** | Vượt hạn mức trả **mã HTTP nào** và `code` nào — cần để phân biệt "chờ rồi thử lại" với "thử lại vô ích" |
| **27** | **16** | Trần gọi mỗi giây/phút/ngày, tính riêng từng API hay tính chung |
| **28** | **18** | Môi trường thử có hạn mức riêng khác môi trường thật không |
| **29** | **19** | Giới hạn 30 mã vận đơn/lượt có áp cho API khác không |

> Câu **17** xếp trước câu **16** tuy số lớn hơn: biết **cách nhận ra** mình bị chặn quan trọng
> hơn biết **con số** trần là bao nhiêu. Không nhận ra thì hệ thống sẽ thử lại vào một bức tường.

### Gộp khi gửi

Gửi **nhóm 1 + nhóm 2 trước, trong một email** (11 câu) — chúng cùng thuộc về người làm bước
联调测试. Nhóm 3 gửi cùng lúc nếu người đó nhận, vì câu 1–3 cần người **kỹ thuật** chứ không
phải người kinh doanh. Nhóm 4 và 5 để lượt sau.

---

## 6. CÂU 28 ĐANG CÓ CHỐT CHẶN CỨNG TRONG MÃ — đọc trước khi chạy thử

Anh Thành chốt (**D-9**): *"Chưa chốt cách ánh xạ `area` cho đến khi hãng xác nhận."*

Đo ngày 15/10/2026 trên chính trang `apiDoc/orderserve/create`:

| Trường | Bắt buộc | Chú thích của hãng | **Ví dụ của hãng** |
|---|---|---|---|
| `prov` | **Y** | 寄件人省 (tỉnh) | `"Hồ Chí Minh"` |
| `city` | N | 寄件人市 · *"địa chỉ hành chính HAI CẤP mới thì không cần điền, để null được"* | **`"Quận 1"`** |
| `area` | **Y** | 寄件人区 | **`"Phường Nguyễn Thái Bình-028QQ107"`** |

⇒ Theo **ví dụ của chính hãng**, **quận nằm ở `city`, phường nằm ở `area`**. Hệ thống hiện đặt
**quận** vào `area` — **ngược lại**. Chi tiết: `docs/G12_VTP_KHAO_SAT.md` §5.2.

**Hệ quả thực tế cho người đi đăng ký:**

- **Không chạy bước tạo đơn thử cho tới khi có trả lời câu 28 + danh mục địa danh (mục 4.3 #9).**
  Đoán địa danh sẽ ra lỗi `1450033315` và làm hỏng cả lượt thử mà **không học được gì**.
- Mã đã có **chốt chặn cứng** (bản vá ở `docs/G12_VTP_KHAO_SAT.md` §5.4): đường LIVE **tự từ
  chối** khi ánh xạ chưa được xác nhận. Không gỡ chốt bằng cách sửa một chữ — chốt đòi **ghi rõ
  ai xác nhận, ngày nào, bằng kênh nào**, và có ca thử canh đúng điều đó.
- Có trả lời rồi thì cập nhật ba hằng trong `app/adapter_jt.py`:
  `ANH_XA_AREA_DA_XAC_NHAN=True` · `NGUON_XAC_NHAN_AREA="<ai · ngày · kênh>"` ·
  `CAP_HANH_CHINH_CHO_AREA="quan-huyen"` hoặc `"phuong-xa"`.

---

## 7. CÓ CREDENTIALS RỒI THÌ CHẠY GÌ

### 7.1 Trước hết: BA KHOÁ NGOÀI credentials vẫn phải mở

Có đủ bốn trường credentials **vẫn chưa chạy được**. `app/harness_hang.py` đòi đủ bốn thứ, và
nó dùng **cùng một hàm** `thieu_gi_de_chay("SANDBOX", hang)` để từ chối chạy và để báo cáo — nên
báo cáo và lúc chạy không thể nói hai điều khác nhau.

| # | Khoá | Mở thế nào | Xin ai |
|---|---|---|---|
| 1 | Mã việc **`V-G09-01`** (gọi API hãng) + **`V-13906-05`** (credentials sandbox J&T) | `SHARED_CONTRACTS.md` mục 25 ghi **CHƯA CẤP** | **anh Thành** |
| 2 | `VIP_HUB_HARNESS_NGUOI_DUYET` | Tên người chịu trách nhiệm lượt chạy | — |
| 3 | `VIP_HUB_HARNESS_CRED_FILE` | Đường dẫn file JSON credentials | mục 7.2 |
| 4 | `CHO_PHEP_LIVE = False` trong `app/adapter_jt.py` | **Chỉ Owner mở**, qua AG-00 | anh Thành |

**Và với J&T còn khoá thứ 5:** chốt chặn D-9 ở mục 6. Nó **độc lập** với bốn khoá trên — cố ý.

### 7.2 Đặt credentials ở đâu

Harness đọc từ **một file JSON** mà `VIP_HUB_HARNESS_CRED_FILE` trỏ tới, **không** nhận trực
tiếp từ biến môi trường. Lý do đo được: biến môi trường trần hiện trong `ps -E`, trong log bộ
lập lịch, và trong ảnh chụp màn hình khi ai đó dán `env` vào hội thoại. File chỉ lộ **đường dẫn**.

Khuôn file (giá trị dưới là **chỗ trống**, không phải giá trị thật):

```json
{
  "jt":  {"apiAccount": "", "privateKey": "", "customerCode": "", "password": ""},
  "vtp": {"vtp_token": "", "vtp_username": "", "vtp_password": "",
          "vtp_base_url": "https://partnerdev.viettelpost.vn"}
}
```

Đặt **ngoài repo** (ví dụ `~/.config/vip-hub/g09-cred.json`), quyền `600`. `.gitignore` **không**
phải lớp bảo vệ duy nhất — đừng đặt trong cây làm việc. Chi tiết:
`docs/G09_CREDENTIALS_CHECKLIST.md`.

### 7.3 Chạy gì để nghiệm thu

Kế hoạch đầy đủ: **`docs/G09_SANDBOX_TEST_PLAN.md`** — bảy bước xếp theo mức nguy hiểm tăng dần,
bước nào **không tạo dữ liệu ở hãng** chạy trước. Không chép lại ở đây.

Hai điều của kế hoạch đó cần nhắc lại vì dễ bỏ qua nhất:

1. **Ca kiểm NGƯỢC (N1–N5) chạy TRƯỚC khi tin bất kỳ kết quả ĐẠT nào.** Chạy một lượt với
   credentials **cố ý sai** và khẳng định nó **HỎNG**. Phép đo nào không hỏng với credentials
   sai thì **phép đo đó không đo xác thực**. Ca đã xảy ra thật: repo `vip-viettelpost` ngày
   01/10/2026 báo `G08 PASS` rồi phải **rút lại** vì token bịa cũng PASS (CR-STG-007).
2. **Không thử lại bước nào, kể cả bước chỉ đọc.** Bằng chứng phải phản ánh đúng **một** lượt.

### 7.4 BỔ SUNG cho kế hoạch sandbox — ba chỗ lượt này thấy còn thiếu

Ba điểm dưới đây **chưa có** trong `docs/G09_SANDBOX_TEST_PLAN.md`. AG-03 không sở hữu file đó
nên **không sửa**; đây là đề xuất cho AG-00.

| # | Bổ sung | Vì sao |
|---|---|---|
| **S1** | **Bước 0 — kiểm chốt chặn D-9 trước mọi lượt gọi.** Chạy `python3 app/thu/thu_anh_xa_area.py`, phải ra **16 ca đạt, 0 bỏ qua**. Còn ca bỏ qua ⇒ chốt chưa cắm ⇒ **dừng, không chạy bước 5** | Kế hoạch hiện chỉ dặn *"chưa có danh mục thì bước 5 không chạy"* — bằng **lời dặn**. Lời dặn không chặn được máy (§12.2) |
| **S2** | **Ca ngược N6 — ánh xạ `area` sai cố ý.** Gửi một đơn thử với `area` = tên **quận** và một đơn với `area` = tên **phường**, ghi lại hãng nhận cái nào, từ chối cái nào | Đây là cách **rẻ nhất và chắc nhất** để trả lời câu 28 bằng phép đo thay vì chờ email. Chỉ chạy **sau** khi đã có `customerCode` test và đã duyệt tạo đơn thử |
| **S3** | **Ca ngược N7 — `password` ba dạng.** Thử lần lượt dạng rõ, MD5, base64, ghi lại dạng nào được chấp nhận | Trả lời câu 22 bằng phép đo. Tài liệu mâu thuẫn ba chỗ nên **không đoán được**; mỗi lần đoán sai tốn một lượt chẩn đoán nhầm hướng |

> **Rủi ro cố ý ghi ra:** S2 và S3 **tạo đơn thử thật** ở môi trường test của hãng và tốn mỗi ca
> một lượt gọi. Chấp nhận được vì đổi lại là một dữ kiện đo được thay cho một giả định. Nhưng
> **chỉ chạy khi đã có phiếu duyệt**, và **phải huỷ ngay** đơn vừa tạo trong cùng lượt.

---

## 8. BLOCKED HIỆN TẠI — nêu chính xác cái còn thiếu

| # | Việc | Thiếu chính xác cái gì | Ai gỡ |
|---|---|---|---|
| 1 | Bắt đầu bước 1–2 (đăng ký, xin làm dev) | **Không thiếu gì.** Làm được ngay hôm nay | anh Thành |
| 2 | Bước 3 — 开发者认证 | Danh sách giấy tờ (tài liệu **không liệt kê**) + J&T duyệt | J&T |
| 3 | `customerCode` / `password` | Liên hệ bưu cục hợp tác, có thể phải ký hợp đồng khách hàng | bưu cục J&T |
| 4 | Chạy lượt API đầu tiên | Mã việc **`V-G09-01`** + **`V-13906-05`** — `SHARED_CONTRACTS.md` mục 25 ghi **CHƯA CẤP** | anh Thành |
| 5 | Tạo đơn thử | Trả lời **câu 28** + **danh mục địa danh** + chốt chặn D-9 đã cắm + phiếu duyệt | J&T + AG-00 + anh Thành |
| 6 | Nhận callback thật | URL công khai — **`V-G11-01` CHƯA CẤP** | anh Thành |
| 7 | Lên môi trường thật `ylopenapi` | Bước 5 của J&T + Owner duyệt riêng | J&T + anh Thành |

---

## 9. PHẠM VI CỦA FILE NÀY — và cái gì NẰM NGOÀI

**Đo bằng:** đọc hai trang `open.jtexpress.vn/apiDoc/index` và `/apiDoc/orderserve/create` bằng
trình duyệt ngày 15/10/2026 (`document.body.innerText`); đọc `docs/JT_CAU_HOI_CHINH_THUC.md`,
`docs/G09_CREDENTIALS_CHECKLIST.md`, `docs/G09_SANDBOX_TEST_PLAN.md`.

**NẰM NGOÀI phạm vi — nói thẳng:**

- **Không gọi một lượt API nào**, kể cả sandbox. `V-G09-01` và `V-13906-05` CHƯA CẤP.
- **Không đăng nhập, không đăng ký, không nhập thông tin gì** trên trang J&T. Chỉ đọc trang
  công khai.
- **Thời hạn mỗi bước và giấy tờ cần nộp: tài liệu KHÔNG nói, và file này KHÔNG đoán.** Mọi ô
  "mất bao lâu" ghi *"Tài liệu KHÔNG nói"* đúng như đo được.
- Sáu trang tài liệu J&T còn lại không đọc lại trong lượt này — lấy theo
  `docs/JT_CAU_HOI_CHINH_THUC.md` ngày 15/10/2026.
- Quy trình đăng ký có thể đã đổi sau 15/10/2026. Trang là SPA và không ghi ngày sửa đổi, nên
  **không có cách nào biết** ngoài việc mở lại trang.
