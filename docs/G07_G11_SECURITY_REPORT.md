# BÁO CÁO BẢO MẬT — WAVE 3 (G07 → G11)

Mỗi dòng kèm **đo bằng gì**. Không dòng nào được đọc là "đã an toàn" ngoài phạm vi đã đo.

## 1. Mười lỗ hổng tìm được trong đợt này

| # | Lỗ hổng | Mức | Đo được | Đã vá |
|---|---|---|---|---|
| 1 | `billing.kiem_va_tang_ai` đọc-rồi-ghi | **CAO** | 28/40 lượt (16 luồng tranh 1 suất) vượt trần; `so_ai` cao nhất **30 trên trần 20** | ✅ |
| 2 | `kiem_han_muc_tai_khoan_hang` đọc-rồi-ghi | **CAO** | **12/12 luồng qua, 12 tài khoản hãng trên trần 1** | ✅ |
| 3 | `kiem_han_muc_nhan_vien` cùng khuôn | TRUNG BÌNH | **không tái hiện** (khoá ghi tình cờ che) — nhưng cấu trúc vẫn hở | ✅ |
| 4 | Phiên bản gói bị bỏ qua ở 4 chốt chặn thật | TRUNG BÌNH | tenant ghim `free` v1 (trần 50) bị áp trần v2 (9999) | ✅ |
| 5 | **COD của J&T gán vào `itemsValue`** thay vì `codMoney` | **CAO** | đọc mã; `itemsValue` không có trong bảng tham số | ✅ |
| 6 | `prov`/`area` của J&T gửi chuỗi rỗng dù bắt buộc | **CAO** | đọc mã; 4 cột dữ liệu có từ v7, chưa ai nối | ✅ |
| 7 | **0 header bảo mật** trên mọi phản hồi | TRUNG BÌNH | `curl -D -` chỉ thấy `Server/Date/Content-*/Cache-Control` | ✅ |
| 8 | Cookie phiên thiếu `Secure` | THẤP | đọc mã `server.py` dòng cookie | ✅ (theo cờ) |
| 9 | `.env` không bị gitignore chặn | TRUNG BÌNH | tạo `.env` → `git status` cho `?? .env` | ✅ |
| 10 | `sao_luu()` ghi đè im lặng | TRUNG BÌNH | 2 lượt cùng giây → **1 file** trên đĩa | ✅ |

**Lỗ hổng 5 nặng nhất về hậu quả nghiệp vụ**, không phải về kỹ thuật: nếu đơn lọt qua thì hãng
**không biết phải thu COD** — hàng đi, tiền không về, và **không có lỗi nào báo**. Đúng dạng
hỏng im lặng mà §12.2 sinh ra để chặn.

**Lỗ hổng 2 nặng nhất về mặt mở cửa**: mỗi tài khoản hãng là **một bộ credentials được mã hoá
và một cửa webhook**, nên lách hạn mức ở đó là **mở thêm cửa**, không chỉ là dùng quá gói.

## 2. Bốn chốt hạn mức — nay đều nguyên tử

| Chốt | Khuôn | Đo sau khi vá |
|---|---|---|
| `kiem_va_tang_don` | `UPDATE ... WHERE dem+1 <= tran`, xét `rowcount` | 8 luồng tranh 1 suất → **đúng 1 qua** |
| `kiem_va_tang_ai` | cùng helper `_cong_bo_dem_co_tran` | đúng 1 qua |
| `chen_membership_co_tran` | `INSERT ... SELECT ... WHERE (SELECT COUNT(*)) < tran` | đúng 1 qua |
| `chen_tai_khoan_hang_co_tran` | cùng khuôn chèn có điều kiện | đúng 1 qua |

**Bài học cấu trúc:** đợt 2 vá **một** chốt (r35) rồi dừng, không hỏi *"cấu trúc này còn hỏng
kiểu đó ở đâu nữa?"* (§12.2 bước 4). Bỏ một bước, sót ba chốt. Nay cả bốn dùng **chung một
helper**, và `thu_han_muc_nguyen_tu.py` có ca soát tĩnh chống thoái hoá: chốt thứ năm mọc theo
khuôn đọc-rồi-ghi thì ca đó hỏng.

## 3. Cách ly tenant

| Phép đo | Kết quả |
|---|---|
| TEST-011 — đổi resource id không lộ dữ liệu tenant khác | PASS |
| `r40` — soát tĩnh mọi SQL chạm bảng có `tenant_id` | PASS (có 1 dòng miễn chính đáng: `sao_luu_khoa.py` cố ý chạy trên mọi tenant, **không có cửa HTTP** — đo bằng `grep sao_luu_khoa app/server.py` = rỗng) |
| `r41` — mọi nhánh API tenant đều tra quyền | PASS |
| `ap_trang_thai_giao(tenant_id, ...)` | `tenant_id` là tham số **BẮT BUỘC** từ đợt 2; gọi thiếu là `TypeError` ngay, không phải ghi chéo im lặng |
| G07 — 7 ca cách ly chéo tenant | PASS (AG-01) |
| G08 — tính phí chéo tenant | PASS, đo 10 luồng / 2 tenant → 5+5, không trộn |
| G10 — 8 ca cách ly tenant cho AIJob | PASS; `tenant_id` từ phiên, body tự khai bị bỏ qua |

## 4. Toàn vẹn tài chính (G07)

| Yêu cầu | Đo bằng gì |
|---|---|
| Tiền là `INTEGER` đồng, cấm float | **0 cột REAL/FLOAT** trong 27 bảng mới (quét DDL **sau khi bỏ lời bình**); ca `A_Tien.test_a2` quét `PRAGMA table_info` trên **schema thật** |
| Bút toán **bất biến** | 4 trigger `BEFORE UPDATE/DELETE ... RAISE(ABORT)`. **Đo thật**: chèn bút toán hợp lệ rồi thử UPDATE và DELETE → **cả hai bị chặn** kèm thông điệp rõ, số dòng không đổi |
| Không silent overwrite | Sai thì ghi bút toán **ĐẢO**, không `UPDATE` |
| Import idempotent | `UNIQUE(tenant_id, hang, ky_thanh_toan, van_tay_dong)` — ràng buộc **CSDL**, gỡ ra thì 3 ca hỏng |
| Đối soát có phê duyệt | `duyet_dot` đòi trạng thái `CHO_DUYET`; `UPDATE ... WHERE trang_thai='CHO_DUYET'` — gỡ điều kiện thì 3 ca hỏng |
| An toàn khi đồng thời | 4 ca đối soát đồng thời |
| Điều chỉnh có lý do + người + lịch sử | Route trả **400** khi thiếu lý do (đo qua HTTP) |

**Giới hạn đã ghi ra:** móc băm nhật ký **không chống được** việc xoá cả đuôi sổ rồi ghi lại —
chống việc đó cần neo băm **ra ngoài CSDL**, chạm `V-13906-03` chưa cấp. Và `tc_cong_no` vẫn có
thể lệch nếu ai ghi `tc_but_toan` bằng SQL trực tiếp (trigger chặn UPDATE/DELETE, không chặn
INSERT — chặn INSERT là chặn luôn đường ghi hợp lệ). Vá: `tinh_lai_cong_no()` dựng lại từ bút
toán + cờ `cong_no_khop`, giao diện cảnh báo mức **nặng** khi lệch.

## 5. Bảo mật AI (G10)

| Yêu cầu | Đo bằng gì | Phạm vi — cái NẰM NGOÀI |
|---|---|---|
| Không gọi mạng | Quét từng dòng `import` + quét URL trong phần mã | Chỉ phủ `ai_job.py` + `ai_validator.py`; `ai_gateway.py` đọc bằng mắt, không phải ca thử |
| Kết quả AI là **dữ liệu không phải lệnh** | `loc_khoa_lenh` quét 40 khoá nghi lệnh ở mọi độ sâu, chuẩn hoá `grant-role`/`grant role`/`GRANT_ROLE` về một khoá | — |
| Chống tiêm prompt | **14 mẫu × 2 đường** (thẳng vào `vao`, và qua **file CSV thật** của G05), gồm mẫu thoát hàng rào và ký tự điều khiển | **Không** phủ: ngôn ngữ khác, chữ đồng hình Unicode, tiêm ghép mảnh nhiều lượt, tiêm qua ảnh/PDF, và **tiêm vào chính một mô hình thật** |
| Không bí mật trong prompt | **12 mẫu × 3 dạng** (thô/hex/base64) = 36 phép đo; có bí mật ⇒ **không gọi** nhà cung cấp, job `loi`, **mức dùng không tăng** | **Không** phủ: bí mật không mang từ khoá và không khớp mẫu (ví dụ `trungthu2026`), mã hoá nhiều lớp, tách qua nhiều lượt |
| Tối giản dữ liệu | **Danh sách TRẮNG** theo từng loại việc. Đo trên prompt THẬT: SĐT `0904444444` và COD `9123456` **không có trong prompt** | — |
| Khoá kép cho nối thật | `MOCK=True` **và** `DA_DUYET_NOI_THAT=False` — phải mở **cả hai** | — |

**Ba câu trả lời cụ thể** (chỉ thị hỏi thẳng): **số điện thoại đầy đủ → KHÔNG** (chỉ dạng che
`090****444`) · **địa chỉ đầy đủ → CÓ, cho đúng hai việc** cần nó; `goi_y_hang` chỉ nhận TỈNH ·
**COD → KHÔNG số chính xác**, gửi **khoảng**.

**Hệ quả phải nói rõ:** vì SĐT/COD không rời máy, kết quả trích xuất không thể chứa chúng, nên
kiểm bản nháp từ kết quả AI sẽ **luôn báo "thiếu SĐT"** — lỗi GIẢ do chính phép tối giản sinh
ra. Vì vậy `de_xuat_cho_nguoi_duyet` **gộp** gợi ý AI lên dòng gốc nằm ở máy **trước** khi kiểm.

## 6. Bốn ổ khoá chặn LIVE (G09)

Phải mở **hết bốn**, không phải một:

1. Cờ môi trường
2. Mã việc + người duyệt
3. **`PhieuDuyetLive` riêng cho TỪNG thao tác ghi** — người duyệt · thao tác · mã tham chiếu ·
   hạn dùng, **dùng một lần**, truyền trong mã không lấy được từ môi trường
4. **`CHO_PHEP_LIVE` trong `adapter.py`** — ngoài tầm file harness

Ổ 4 là ổ thật: kể cả ba ổ kia mở nhầm **và** harness có lỗi, `tao_adapter(..., "production")`
vẫn ném `PermissionError` (ca `A6`).

**Không có đường rơi về MOCK.** Thiếu gì thì ném `ThieuCauHinh` kèm danh sách chính xác;
`KetQuaLanChay.che_do` luôn là chế độ **đã chạy**, không phải chế độ **đã xin**.

Cửa HTTP `POST /platform/g09/harness` **ép cứng `MOCK`**, không nhận `che_do` từ thân.

## 7. Siết bảo mật tầng HTTP (G11)

| Hạng mục | Trước | Sau | Đo bằng gì |
|---|---|---|---|
| `X-Content-Type-Options` | thiếu | `nosniff` | `curl -D -` trên tệp tĩnh **và** API, kể cả đường 401/404 |
| `X-Frame-Options` | thiếu | `DENY` | cùng trên |
| `Referrer-Policy` | thiếu | `no-referrer` | cùng trên |
| `Content-Security-Policy` | thiếu | có, `frame-ancestors 'none'` · `object-src 'none'` · `base-uri 'none'` · **không `unsafe-eval`** | cùng trên |
| `Strict-Transport-Security` | thiếu | **chỉ gửi khi `VIP_HUB_HTTPS=1`** | đo: HTTP → **0 dòng HSTS** |
| Cookie `Secure` | thiếu | theo cờ `VIP_HUB_HTTPS` | soát tĩnh: cờ phải đi qua điều kiện |
| Bind | ghim cứng `127.0.0.1` | `VIP_HUB_BIND`, **mặc định vẫn** `127.0.0.1` | soát tĩnh đòi mặc định không đổi |

**Vì sao `Secure` theo cờ chứ không bật cứng:** bật cứng thì mọi lượt đăng nhập qua
`http://127.0.0.1` **im lặng không nhận cookie**, và màn hình chỉ nói "sai tên đăng nhập hoặc
mật khẩu" trong khi mật khẩu **chưa bao giờ sai**. Đó đúng là ca sinh ra §12.2 của `CLAUDE.md`
— mất gần ba tiếng cho một lỗi mà thông báo nói sai hoàn toàn.

**Vì sao CSP còn `'unsafe-inline'` cho style:** giao diện dùng style nội tuyến nhiều chỗ. Siết
chặt hơn mà chưa đo bằng trình duyệt thật thì CSP sẽ chặn mất giao diện — và **một CSP làm hỏng
giao diện là một CSP sẽ bị tắt đi cho xong**, tức là tệ hơn không có. Siết tiếp là việc sau khi
tầng 3 chạy được (`V-13906-01`).

**Chốt chặn mới:** bind ra ngoài **+** cửa trả token đặt-lại-mật-khẩu đang mở = ai cũng chiếm
được tài khoản bất kỳ bằng ba lượt HTTP. Hai thứ riêng lẻ còn chấp nhận được, cùng lúc thì
không → `SystemExit(4)`, không cảnh báo rồi chạy tiếp.

**Chốt chống thoái hoá:** `thu_header_bao_mat::b1` dùng **AST**, xét trong phạm vi **từng hàm**.
Bản đầu nhìn lùi 16 dòng và **cửa sổ vượt ranh giới hàm** nên cho hàm sai đi qua — AG-00 chỉ
biết vì đã gỡ bản vá ra để đo. Thêm ca `b1b` **kiểm chính phép soát**.

## 8. Không có gì trong đợt này chạm vào tám việc chưa cấp quyền

Đo bằng cách đọc 5 báo cáo agent + diff 5 nhánh: **0 lượt** gọi API hãng (kể cả sandbox) · **0
lượt** nối AI thật · **0 lượt** deploy · **0 lượt** xoay khoá thật · **0** credentials thật vào
Git · **0** đơn vận chuyển thật · **0** giao dịch thanh toán · **0 push**.

Một ghi chú riêng từ AG-03: trang tài liệu J&T **in sẵn công khai** một `apiAccount` và
`privateKey` của môi trường thử. AG-03 **cố ý không chép giá trị đó vào bất kỳ file nào** — dù
công khai, chép khoá vào vault là tạo tiền lệ sai. Và có hai trường đó vẫn **không tạo được đơn
thử**, vì `customerCode`/`password` phải do bưu cục cấp.
