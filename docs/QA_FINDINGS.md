# QA_FINDINGS — AG-07 QA, WAVE 1

**Ngày đo:** 14/10/2026 · **Worktree:** `~/code/veh-qa`, nhánh `agent/qa`
**Nền chạy:** macOS Darwin 25.6.0 (MacBook Pro), `Python 3.9.6`
**Gốc soát:** commit `a1dea69` (*AG-00: khoa shared contracts truoc khi chia 5 agent*)

> **Đây là QA bằng AI, KHÔNG phải independent human review.** Mọi phát hiện dưới đây do một
> tác tử đọc mã và chạy ca thử tự sinh ra; chưa ai ngoài hệ thống soát lại. Phần "đã kiểm,
> không phải lỗ hổng" chỉ đúng trong **phạm vi ca thử đã ghi**, không phải lời bảo đảm chung.
>
> **Chưa soát bởi người.** Trước khi mở ra Internet, bốn mục CRITICAL/HIGH dưới đây cần một
> người đọc lại bản vá, không chỉ cần ca thử chuyển xanh.

Bằng chứng nằm ở **`app/thu/thu_qa_soat.py`** (30 ca). Quy ước tên:

| Tiền tố | Ý nghĩa | Trạng thái mong muốn hôm nay |
|---|---|---|
| `test_qXX_LOHONG_…` | chứng minh một lỗ hổng chưa vá | **FAIL** (vá xong phải tự PASS, không sửa assert) |
| `test_qXX_ANTOAN_…` | chốt một mối lo đã kiểm, kết luận không phải lỗ hổng | **PASS** |

Lượt đo 14/10/2026: **30 ca · 16 PASS · 14 FAIL** — đúng 14 ca `LOHONG`, 0 ca `ANTOAN` hỏng.

---

## 1. Bảng phát hiện

| Mã | Mức | Vấn đề | Bằng chứng | Vá? |
|---|---|---|---|---|
| **Q-01** | **CRITICAL** | API trả token đặt lại mật khẩu ở cấu hình **mặc định** → chiếm mọi tài khoản, kể cả `PLATFORM_OWNER`, không cần đăng nhập | `test_q01_…`, `test_q01b_…`, `test_q01c_…` | **CHƯA** |
| **Q-02** | **HIGH** | Bộ phục vụ static trả **mã nguồn Python** cho người chưa đăng nhập (`/app/bao_mat.py`, `/gateway/cau_hinh.py` — file sau chứa secret HMAC/token demo của 5 hãng) | `test_q02_…` | **CHƯA** |
| **Q-03** | **MEDIUM** | `/api/v2/platform/vai-tro` và `/api/v2/platform/goi` **không gọi `self._can()`** → `TENANT_VIEWER` đọc trọn ma trận RBAC + bảng giá nền tảng | `test_q03_…`, `test_q03b_…` | **CHƯA** |
| **Q-04** | **LOW** | 404-vs-403 trên `/platform/tenants/{id}` làm máy dò sự tồn tại/đếm doanh nghiệp | `test_q04_…` | **CHƯA** |
| **Q-05** | **MEDIUM** | `gioi_han=-1` → `LIMIT -1` = **không giới hạn**, phá chính mức chặn 500 của mã | `test_q05_…` | **CHƯA** |
| **Q-05b** | **LOW** | `gioi_han=abc` → **HTTP 500** thay vì 400 | `test_q05b_…` | **CHƯA** |
| **Q-05c** | **LOW** | `cod` không phải số ở `/ai/phat-hien-bat-thuong` → **HTTP 500** | `test_q05c_…` | **CHƯA** |
| **Q-06** | **MEDIUM** | 5 yêu cầu vô danh **khóa vĩnh viễn** một tài khoản bất kỳ; "quên mật khẩu" **không** mở khóa | `test_q06_…` | **CHƯA** |
| **Q-07** | **MEDIUM** | `/api/v2/import` **không chặn số dòng** (20.000 dòng/1 yêu cầu được nhận; body tới 20 MB) | `test_q07_…` | **CHƯA** |
| **Q-07b** | **MEDIUM** | `duyet_batch` lặp `dong_ids` của client **không chặn độ dài** (50.000 id = 50.000 truy vấn) | `test_q07b_…` | **CHƯA** |
| **Q-07c** | **MEDIUM** | Mức chặn body 20 MB áp cả cho đường **vô danh** (`/auth/dang-nhap`) và cho webhook **trước khi** kiểm HMAC | `test_q07c_…` | **CHƯA** |
| **Q-08** | **LOW** | `/don/xuat-csv` không vô hiệu `= + - @` đầu ô → tiêm công thức vào bảng tính người đọc | `test_q08_…` | **CHƯA** |
| **Q-10** | **LOW** | *Rủi ro cấu trúc:* `don_hang.ap_trang_thai_giao()` nhận `don_id` trần, **không tự kiểm tenant** | ghi trong `SQL_DUOC_MIEN` của `test_q09g_…` | **CHƯA** (không lỗi hôm nay) |
| **Q-11** | **LOW** | *Lỗi bộ thử, không phải lỗi sản phẩm:* `thu_saas.py::test_16` FAIL trong worktree mới vì đòi file `gateway/du-lieu/gateway.db` mà `.gitignore` loại khỏi git | lượt baseline | **CHƯA** |
| **Q-12** | **LOW** | *Lỗi bộ thử:* cả 4 bộ thử bind **cổng cố định** → chạy chồng hai bộ là `Address already in use`, trông như lỗi ngắt quãng | quan sát 1/41 lượt | **CHƯA** |

Không phát hiện nào được vá trong worktree này: **QA phát hiện, không vá** (ràng buộc nhiệm vụ).

---

## 2. Chi tiết bốn phát hiện nặng nhất

### Q-01 — CRITICAL · chiếm tài khoản không cần đăng nhập

`app/cau_hinh.py`:

```python
HIEN_TOKEN_RESET = os.environ.get("VIP_HUB_RESET_TOKEN", "1") == "1"
```

Mặc định **"1" = BẬT**. Khi bật, `POST /api/v2/auth/quen-mat-khau` trả thẳng
`token_gia_lap` cho **người gọi vô danh**, và token đó dùng được ngay ở
`POST /api/v2/auth/dat-lai-mat-khau`.

Chuỗi đã chạy được thật trong `test_q01c_…` (3 yêu cầu HTTP, không có thông tin đăng nhập nào):

1. `POST /auth/quen-mat-khau {"ten_dang_nhap": "po3"}` → `200` kèm `token_gia_lap`
2. `POST /auth/dat-lai-mat-khau {token, mat_khau_moi}` → `200`
3. `POST /auth/dang-nhap` → `200`, và `GET /auth/toi` trả `platform_role: "PLATFORM_OWNER"`

**Vì sao nó lọt qua ba bộ thử hiện có:** `thu_g01_g02.py::test_017` **dựa vào** `token_gia_lap`
để chạy luồng của nó (`token = kq["token_gia_lap"]`). Bộ thử không chỉ bỏ sót lỗ hổng — nó
**chốt cứng cấu hình mất an toàn làm hành vi mong đợi**. Vá Q-01 sẽ làm `test_017` hỏng; đó là
dấu hiệu đúng, và `test_017` phải được viết lại để tự bật `VIP_HUB_RESET_TOKEN=1` cho riêng nó.

**Đây đúng dạng §12.2 về danh sách trắng/đen.** Câu hỏi phân biệt: *quên một dòng thì kết quả
là an toàn hay hỏng?* Ở đây quên đặt `VIP_HUB_RESET_TOKEN=0` là **hỏng** — nên mặc định phải
là **TẮT**, và bật mới là việc của người triển khai. `docs/G01_G02_ACCEPTANCE.md` mục 4 có ghi
lời dặn "phải đặt `VIP_HUB_RESET_TOKEN=0` trước khi dùng ngoài local" — nhưng **lời dặn không
chặn được máy**: không có cổng nào từ chối khởi động khi biến đó bật ngoài `127.0.0.1`.

**Hướng vá đề nghị:** đổi mặc định sang tắt (`os.environ.get("VIP_HUB_RESET_TOKEN", "0")`), và
thêm cổng chặn khởi động: bật cờ này mà không bind `127.0.0.1` thì dừng hẳn, không chạy tiếp.

### Q-02 — HIGH · lộ mã nguồn cho người chưa đăng nhập

`server.py::_phuc_vu_tinh` chạy **trước** mọi lớp xác thực (mọi `GET` không bắt đầu bằng
`/api/`), và lọc bằng **danh sách đen**:

```python
if an_toan.startswith(("..", "app/du-lieu", "gateway/du-lieu", ".git")):
```

Chú thích đầu `server.py` nói hệ chỉ phục vụ `admin/`, `pages/`, `assets/`. Mã thì phục vụ
**mọi file trong repo**. Đo được: `GET /app/server.py`, `/app/bao_mat.py`, `/app/cau_hinh.py`,
`/gateway/cau_hinh.py`, `/app/thu/thu_saas.py` đều trả `200` kèm nội dung đầy đủ.
`gateway/cau_hinh.py` còn chứa cả `secret`/`token` HMAC của 5 hãng (dù mang nhãn demo) và
`KHOA_API` của gateway.

Cho dữ liệu **đi ra** thì phải dùng **danh sách trắng** (§12.2): bỏ sót một tên trong danh sách
đen là **mất im lặng**. Hiện khóa AES và `.git` chặn được **chỉ nhờ hai dòng hằng chuỗi** —
`test_q02b_…` chốt lại điều đó, và nêu rõ: đổi `VIP_HUB_DATA` sang thư mục khác trong repo là
danh sách đen hết tác dụng. Vì vậy **không vá bằng cách thêm dòng đen**.

**Hướng vá đề nghị:** chỉ phục vụ file nằm trong đúng ba thư mục `admin/`, `pages/`, `assets/`
cộng `index.html` ở gốc; mọi đường khác trả 404.

*Đã kiểm, KHÔNG phải lỗ hổng:* thoát **ra ngoài** gốc repo không được —
`os.path.normpath` + `lstrip("/")` chặn `..`, và `self.path` không được urldecode nên `%2e%2e`
cũng vô hiệu (`test_q09l_…`, 4 biến thể).

### Q-06 — MEDIUM · khóa tài khoản vĩnh viễn từ xa

`bao_mat.dang_nhap` khóa tài khoản sau `KHOA_SAU_SO_LAN_SAI = 5` lần sai, **không** chặn theo
IP, **không** có cửa sổ thời gian, **không** tự mở lại. Và `dat_lai_mat_khau` chỉ xóa
`so_lan_sai`, **không** xóa `trang_thai='khoa'`.

Hệ quả đo được: 5 yêu cầu HTTP vô danh khóa một `PLATFORM_OWNER`; sau đó chính chủ đi hết
luồng "quên mật khẩu" thành công mà vẫn **không đăng nhập được** (`401`). Nếu khóa đúng người
quản trị cuối cùng thì không còn ai mở được từ trong hệ.

### Q-07 · Q-07b · Q-07c — MEDIUM · giới hạn tài nguyên

Ba đường cùng một gốc: **không có mức chặn nào do client cấp bị kiểm lại**.

- `_doc_body(gioi_han=20*1024*1024)` là mặc định cho **mọi** endpoint. Đường vô danh
  (`/auth/dang-nhap`) dùng chung mức này: body 4 MB được nhận (ca thử dùng 4 MB cho nhanh;
  mức thật là 20 MB).
- Webhook `/api/v2/webhook/nhan/{ma}` đọc **hết** body **trước** khi kiểm HMAC. Ai biết
  `webhook_ma` (giá trị công khai trên URL) là đẩy được 20 MB/yêu cầu dù không có secret.
- `nhap_file.tao_batch` chèn một dòng CSDL cho **mỗi** dòng file, không chặn. 20.000 dòng nhận
  gọn trong một yêu cầu, giữ `csdl.khoa_ghi` suốt lượt ghi → làm đứng mọi phiên khác.
- `nhap_file.duyet_batch` lặp `dong_ids` của client, mỗi phần tử một truy vấn. 50.000 id rác
  được xử hết, trả `{"bo_qua": 50000}` kèm `HTTP 200`.

---

## 3. Đã kiểm, KHÔNG phải lỗ hổng (16 ca PASS)

Ghi lại để lần sau không soát lại từ đầu. Mỗi dòng chỉ đúng **trong phạm vi ca thử của nó**.

| Mối lo | Kết luận | Ca thử |
|---|---|---|
| Khóa AES / `.git` tải được qua static? | Không — nằm trong danh sách đen (xem cảnh báo Q-02) | `test_q02b_…` |
| Thoát ra ngoài gốc repo qua `..` / `%2e%2e`? | Không, 4 biến thể đều chặn | `test_q09l_…` |
| Đường `/platform/*` khác thiếu `_can`? | Không — `tenants` (GET/POST) và `audit` đều chặn `TENANT_VIEWER` | `test_q03c_…` |
| Sửa/đọc **dòng import** chéo tenant? | Không — `sua_dong` nối sang `import_batch` lấy tenant rồi so | `test_q09_…` |
| `duyet_batch` nhận dòng của batch (và tenant) khác? | Không — lọc `id=? AND batch_id=?`, trả `bo_qua`, không gắn `don_id` | `test_q09b_…` |
| Webhook cập nhật đơn tenant khác khi **mã vận đơn trùng ở cả hai tenant**? | Không — resolve bằng `ma_van_don + tenant_id + carrier_account_id` lấy từ account trên URL, không từ payload | `test_q09c_…` |
| Có đường webhook nào **bỏ qua** chữ ký? | Không — thiếu header / header rỗng / chữ ký rác / secret của account khác đều `401` | `test_q09d_…` |
| Có cache ngữ cảnh tenant làm thu hồi quyền chậm? | Không — `ngu_canh()` tra CSDL mỗi yêu cầu; hạ `STAFF→VIEWER` là yêu cầu ghi tiếp theo **cùng cookie** đã `403` | `test_q09e_…` |
| `tenant_id` trong body/query ghi đè được ngữ cảnh? | Không — `POST /don`, `POST /khach-hang`, `GET /don?tenant_id=` đều giữ tenant của phiên | `test_q09f_…` |
| Còn câu SQL nào thiếu điều kiện tenant? | 6 câu thiếu, soát từng câu thấy đều có lượt đọc khóa tenant đứng ngay trên → vào `SQL_DUOC_MIEN` có lý do. Câu thứ 7 xuất hiện là ca thử hỏng | `test_q09g_…` |
| Rotate/revoke/khóa tài khoản hãng của tenant khác? | Không — cả 4 việc trả `404`, credentials của B không đổi | `test_q09m_…` |
| Secret lọt vào audit / lịch sử đơn / `loi_cuoi` / phản hồi API / log? | Không thấy — quét 5 secret do bộ thử nạp qua 3 bảng + 5 endpoint + log server | `test_q09h_…` |
| `wh_su_kien.headers_json` lưu chữ ký — có lộ ra API? | Không — mối lo thật nhưng chưa endpoint nào trả trường này; ca thử canh đúng điều đó | `test_q09i_…` |
| `TENANT_ADMIN` leo lên `TENANT_OWNER` / `PLATFORM_*`? | Không — `quyen.CAP_DUOC` chặn, cả 3 vai trò đều `403`, `platform_role` vẫn `NULL` | `test_q09j_…` |
| Đổi sang tenant không có membership? | Không — `403`, tenant đang hoạt động không đổi | `test_q09k_…` |

### Phạm vi của câu "không thấy secret lọt ra" (§12.1 luật 5)

Câu đó **chỉ** nói: 5 chuỗi secret **do chính bộ thử này nạp** không xuất hiện trong
`audit.chi_tiet/doi_tuong/hanh_dong`, `don_lich_su.noi_dung/nguon`,
`wh_su_kien.loi_cuoi/headers_json`, phản hồi của 5 endpoint liệt kê, và `stderr` của server
trong lượt chạy đó. **Ngoài phạm vi:** secret của luồng khác, đường ghi log ngoài `stderr`,
thông điệp ngoại lệ từ adapter hãng thật (`polling_loi` ghi `f"{type(e).__name__}: {e}"` —
chưa đo được vì ở mức mock không có credentials trong thông điệp lỗi).

---

## 4. Việc nên làm tiếp

1. **Vá Q-01 trước mọi thứ khác**, và sửa `thu_g01_g02.py::test_017` để nó tự bật cờ thay vì
   dựa vào mặc định. (Chủ sở hữu: AG-SECURITY.)
2. **Vá Q-02 bằng danh sách trắng**, không thêm dòng vào danh sách đen.
3. Q-03 cần **một cổng chung** cho cả nhánh `/api/v2/platform/*` (kiểm `platform_role` ở đầu
   `_api_platform`) thay vì sửa lẻ hai đường — §12.2: hỏng lần thứ hai cùng kiểu thì **đổi
   cấu trúc**, vì danh sách endpoint sẽ còn dài ra.
4. Q-05b/Q-05c gợi một việc chung: thêm một lớp đọc số có kiểm, dùng ở cả query và body, để
   dữ liệu người dùng sai luôn ra 400 chứ không thành 500.
5. Q-11, Q-12 là nợ của **bộ thử**, nên gộp làm một việc: bỏ phụ thuộc file ngoài git, và cho
   mọi bộ thử bind cổng 0 (hệ cấp cổng trống) thay vì cổng cố định.
6. **WAVE 2** (sau khi AG-00 hợp nhất): chạy lại cả 5 bộ thử, kiểm 14 ca `LOHONG` đã chuyển
   xanh ca nào, và soát phần mã mới của 4 agent kia — WAVE 1 **chưa đọc** mã đó.
