# BÁO CÁO KIỂM THỬ — WAVE 3 (G07 → G11)

Đo ngày **15/10/2026**, MacBook · Darwin arm64 · Python 3.9.6 · SQLite 3.51.0 · Node v26.7.0.

## 1. Bảng từng bộ — số đo, không phải số nhớ

| Bộ thử | Ca | Gate | Mới? |
|---|---|---|---|
| `thu_ai_job.py` | 87 | G10 | **mới** |
| `thu_bao_mat.py` | 57 | G02 | |
| `thu_doi_soat.py` | 27 | G07 | **mới** |
| `thu_don_hang.py` | 63 | G04 | |
| `thu_g01_g02.py` | 21 | G01+G02 | |
| `thu_g03.py` | 53 | G03 | |
| `thu_gioi_han.py` | 34 | bảo mật | |
| `thu_goi_dich_vu.py` | 37 | G08 | **mới** |
| `thu_han_muc_nguyen_tu.py` | 5 | G08/bảo mật | **mới (AG-00)** |
| `thu_harness_hang.py` | 57 | G09 | **mới** |
| `thu_header_bao_mat.py` | 8 | G11/bảo mật | **mới (AG-00)** |
| `thu_ma_la_hang.py` | 6 | G09 | **mới (AG-00)** |
| `thu_nhap_file.py` | 21 | G05 | |
| `thu_qa2_soat.py` | 49 | soát độc lập | |
| `thu_qa_soat.py` | 30 | soát độc lập | |
| `thu_quan_sat.py` | 45 | G11 | **mới** |
| `thu_saas.py` | 19 | SaaS | |
| `thu_tai_chinh.py` | 51 | G07 | **mới** |
| `thu_tich_hop.py` | 6 | cấu trúc | |
| `thu_usage.py` | 41 | G08 | **mới** |
| `thu_webhook.py` | 68 | G06 | |
| `thu_gateway.py` | 9 | gateway cũ | |
| **TỔNG python** | **794** (22 bộ) | | |

Cộng thêm: **56** ca Node (`thu_logic.mjs`) · **36** ca HTTP frontend (`thu_http.py`) · **41**
phép đo E2E (`chay_e2e.sh`) = **927 phép kiểm, 0 hỏng, 1 bỏ qua**.

Không tính vào tổng: **95 ca harness MOCK** (`python3 app/harness_hang.py` — `thu_harness_hang`
đã bao) và **20 phép kiểm `billing.js`** của AG-02.

## 2. Bộ chạy thử TỰ DÒ — và vì sao phải tự dò

`app/thu/chay_tat_ca.sh` **tự dò** `thu_*.py` thay vì liệt kê cứng. Danh sách viết cứng là chỗ
một bộ thử mới bị **quên im lặng**: thêm `thu_abc.py` mà quên thêm vào danh sách thì nó không
bao giờ chạy, và không có gì báo. Đợt này 5 agent viết 7 bộ thử mới — đó là chỗ chắc chắn sẽ
quên.

Đổi lại phải canh ngược: dò được **ít hơn ngưỡng** (mặc định 12) thì script **hỏng mã thoát 2**,
chứ không lặng lẽ chạy 0 bộ rồi báo đạt. Hai chốt đã đo là load-bearing:

| Chốt | Gỡ ra | Kết quả |
|---|---|---|
| ngưỡng tối thiểu | `VIP_TOI_THIEU_BO=99` (thực có 22) | mã thoát **2** + thông điệp "phép dò đang nhìn sai chỗ" |
| phát hiện bộ hỏng | thêm một bộ thử hỏng cố ý | mã thoát **1** + in **đúng tên** bộ |

Script in **PHẠM VI** ở cuối mỗi lượt (hệ điều hành, phiên bản Python/SQLite, chế độ adapter,
và danh sách cái gì NẰM NGOÀI) — trước đây phải gõ tay vào từng báo cáo nên dễ thiếu hoặc nói
rộng hơn thực tế.

## 3. SÁU LẦN "thứ dùng để kiểm chứng tự nó sai" — trong MỘT ngày

Đây là phần đáng đọc nhất của báo cáo này. Cả sáu đều là **công cụ kiểm chứng nói sai**, không
phải sản phẩm hỏng. `CLAUDE.md` §12.1 nói đúng một điều: *thứ dùng để kiểm chứng phải được kiểm
trước khi tin.*

| # | Công cụ | Nó nói sai thế nào | Ai bắt |
|---|---|---|---|
| 1 | Ca `h5` của AG-01 (quét SQL thiếu `tenant_id`) | Đọc từng chuỗi literal **rời** nên đọc được **một mảnh** câu SQL f-string rồi báo lỗi sai | AG-01 tự bắt |
| 2 | `kiem_cau_hinh.py` của AG-05 | Cắt tại chữ "HEALTHCHECK" trong một dòng **ghi chú**, báo LỖI cho `Dockerfile` **đúng** | AG-05 tự bắt |
| 3 | Phép soát `r40` (thu_qa2_soat) | Nối literal liền nhau nhưng **không tính tiền tố `f`** của f-string ⇒ đọc một mảnh, báo thiếu `tenant_id` cho câu SQL **có** `tenant_id` | AG-00 |
| 4 | Phép quét DDL của AG-00 | Đọc chữ "float" trong **lời bình** `(§16: cấm float)` rồi báo có cột `REAL` — cột thật là `INTEGER` | AG-00 |
| 5 | Phép đo trigger của AG-00 | Báo "SỬA/XOÁ không bị chặn" — thực ra lượt **chèn hỏng** nên không có dòng nào, và `BEFORE UPDATE` không kích hoạt khi không khớp dòng nào | AG-00 |
| 6 | Ca `b1` của AG-00 (chốt header bảo mật) | Nhìn lùi **16 dòng**, cửa sổ **vượt ranh giới hàm** nên thấy lượt gọi của hàm khác ⇒ **cho hàm sai đi qua** | AG-00 |

Ca 6 nguy hiểm nhất: nó là chốt được xây để chặn đường thứ tư quên header, mà nó **tự nó vô
dụng**. AG-00 chỉ biết vì đã **gỡ bản vá ra để đo** — thêm một hàm trả phản hồi không header và
ca thử **vẫn đạt**.

**Đổi cấu trúc theo §12.2** (hỏng lần thứ hai cùng kiểu thì đổi cấu trúc):
- Ca 3 → mẫu nối literal nhận tiền tố `f/r/b/u`
- Ca 4 → **bỏ lời bình trước khi quét**
- Ca 6 → **bỏ hẳn cửa sổ dòng, dùng AST** để biết chính xác lượt gọi nào thuộc hàm nào, và thêm
  ca `b1b` **kiểm chính phép soát** (dựng một hàm sai trong bộ nhớ, đòi phép soát tố giác đúng
  tên nó)

## 4. BA ca thử KHOÁ CHIỀU TIẾN BỘ — và cách sửa

Dạng này khác dạng trên: ca thử **đúng lúc viết**, nhưng nó chốt **trạng thái việc chưa xong**,
nên khi việc xong thì ca hỏng.

| Ca | Chốt gì | Vì sao thành cửa khoá chết |
|---|---|---|
| `thu_frontend` ca 52 (đợt 2) | `/tu-choi` **phải nằm trong** danh sách CHỜ BACKEND | Cắm route xong là ca hỏng |
| `thu_tai_chinh::j3` | **Mọi** màn phải mang nhãn "CHỜ BACKEND" | Cắm 18 route xong là ca hỏng |
| `thu_tai_chinh::j4` | Bảng chờ phải có **≥ 10 mục** | Cắm hết route thì bảng chờ phải RỖNG, và rỗng bị tính là hỏng |

Cách sửa: **chốt theo Ý ĐỊNH, không theo trạng thái lúc viết.**
- ca 52 → "không đường nào được biến mất im lặng khỏi **cả hai** danh sách"
- j3 → "màn nào chờ thì PHẢI có nhãn + phạm vi; màn nào không chờ thì KHÔNG được mang nhãn chờ"
- j4 → sàn đếm **tổng hai bảng** (chờ + đang dùng), giữ đúng tác dụng chống-vô-nghĩa mà không
  chặn tiến bộ; **thêm chiều ngược**: khai ĐANG DÙNG mà route không có cũng là nhãn nói dối,
  theo hướng tệ hơn — giao diện sẽ gọi thật rồi báo lỗi lạ cho người dùng

## 5. Ca thử có load-bearing — gỡ bản vá ra để đo

Ca thử ĐẠT chưa chứng minh gì: nó có thể đạt vì không thật sự kiểm cái nó nói.

| Gỡ cái gì | Ca tương ứng |
|---|---|
| Chốt `den == "COD_SETTLED"` trong `chuyen_cod` | HỎNG (AG-01 đo) |
| Chốt "phải `COD_RECONCILED` mới nhận tiền" | HỎNG (AG-01) |
| Trigger còn đó nhưng không `RAISE` | HỎNG 3 ca (AG-01) |
| `UNIQUE(...van_tay_dong)` → `CHECK (1=1)` | HỎNG 3 ca (AG-01) |
| Dòng vá `r29` (token reset) | HỎNG (AG-00, đợt 2) |
| Trần khỏi `WHERE` của `r35` | HỎNG (AG-00, đợt 2) |
| `tenant_id` khỏi câu `UPDATE` của `_cong_bo_dem_co_tran` | HỎNG `r40` (AG-00) |
| Thêm một hàm trả phản hồi không header | HỎNG `b1` (AG-00, **sau khi** đổi sang AST) |

AG-02 dùng cách khác, cũng hợp lệ: **bản đối chứng cố ý sai**. Ca `c1_doc_roi_ghi` chạy khuôn
đọc-rồi-ghi và đo được **8/8 luồng lọt, bộ đếm 17 trên trần 10** — chứng minh phép đo **bắt
được** lỗi, trước khi tin kết luận "đúng 1 luồng qua" ở ca `d1`.

## 6. Cái gì CHƯA được kiểm

- **Tầng 3 giao diện** (DOM/CSS/bố cục trong trình duyệt thật) — `V-13906-01` chưa cấp. **12
  màn mới của đợt này chưa được nhìn bằng mắt lượt nào.**
- **Docker** — `docker --version` → `command not found`. `Dockerfile` và `docker-compose.yml`
  **chưa build lượt nào**; nghiệm thu thay bằng soát cú pháp, và **soát cú pháp đạt KHÔNG PHẢI
  build đạt**.
- **PostgreSQL** — `DDL_G07` dùng partial unique index và `RAISE(ABORT)`, **sẽ không chạy nguyên
  văn** trên Postgres. Đây là giả thiết chưa kiểm.
- **Nhiều tiến trình** — `csdl.khoa_ghi` chỉ phủ MỘT tiến trình; trần rate limit sống trong bộ
  nhớ MỘT tiến trình. Chốt chèn-có-điều-kiện đưa điều kiện vào CSDL nên khoẻ hơn, **nhưng chưa
  đo**.
- **Dữ liệu lớn** — đo trên 2 đơn, 1 batch 3 dòng, 6 sự kiện webhook.
- **API hãng thật, mô hình AI thật, HTTPS thật, proxy thật, giao dịch ngân hàng** — không lượt nào.
- **Ca tiêm prompt chứng minh CẤU TRÚC, không chứng minh MÔ HÌNH.** AG-04 nói rõ: 14 mẫu × 2
  đường chứng minh hàng rào và phép kiểm schema hoạt động; **không** chứng minh một mô hình thật
  sẽ không bị dụ. Phải chạy lại trên mô hình thật ngay sau khi `V-G10-01` được cấp.
