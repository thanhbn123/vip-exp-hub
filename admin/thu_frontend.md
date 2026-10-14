# Kiểm thử giao diện quản trị — AG-06 FRONTEND

Ngày đo: **14/10/2026**. Nhánh `agent/frontend`, worktree `~/code/veh-frontend`.
Máy: MacBook Pro (macOS, Python 3.9.6 của Command Line Tools).

## 0. Cách kiểm — nói rõ phạm vi trước khi đọc kết quả

Ba cách đã dùng, **không** cách nào bị báo thay cho cách khác:

| Cách | Dùng cho | Hạn chế |
|---|---|---|
| **Đọc mã** | rà lại luồng lỗi, chỗ nào còn `await api()` trần không bắt lỗi | không chứng minh được chạy đúng |
| **`node --check admin/admin.js`** | cú pháp JS | chỉ cú pháp, không chạy logic |
| **Chạy server + `curl`** | hình dạng thật của API, mã HTTP thật | không thấy giao diện |
| **Mở trình duyệt thật** (Chromium trong Browser pane, điều khiển bằng công cụ) | dựng màn, bấm nút, đo bề rộng bằng DOM | **không** phải mắt người soi từng pixel; kết luận bố cục dựa trên số đo `clientWidth` / `scrollWidth` và ảnh chụp màn hình, không dựa trên cảm nhận thẩm mỹ |

**Nói thẳng:** có mở trình duyệt thật và có bấm thật — không phải chỉ đọc mã. Nhưng
phần "đẹp/xấu, chữ có chen nhau không" thì chỉ xem qua vài ảnh chụp, **chưa** soi hết mọi màn
ở mọi cỡ bằng mắt. Phần bố cục dưới đây là **số đo**, không phải nhận xét thẩm mỹ.

Server dùng để kiểm: `python3 app/server.py 8921`.
**Cổng 8921 chứ không phải 8899** — lúc bắt đầu, 8899 đã có hai tiến trình Python khác
chiếm (`lsof -nP -iTCP:8899`), server của lượt này **không bind được** và báo
`OSError: [Errno 48] Address already in use`. Lần đầu `curl http://127.0.0.1:8899/admin/`
trả 200 là **trả lời của tiến trình khác**, không phải của bản đang sửa — ghi ra đây để
không ai đọc lại rồi tưởng đã nghiệm thu trên 8899.

## 1. Nền chạy thử

```
python3 app/migrate.py        → phiên bản 3, bảo toàn ĐẠT
python3 app/khoi_tao.py       → seed, ghi app/du-lieu/TAI-KHOAN-DEMO.md
python3 app/server.py 8921
```

Dữ liệu tạo thêm để có cái mà hiển thị (tạo qua chính API của app, không chèn tay vào CSDL):
1 batch import từ CSV 3 dòng (2 dòng hợp lệ, 1 dòng sai SĐT/cân nặng/COD âm),
2 đơn sinh từ batch, mỗi đơn gửi qua một tài khoản hãng mock khác nhau (`vtp`, `jt`).

`gateway/du-lieu/gateway.db` ban đầu **chưa có**, làm `thu_saas.test_16` hỏng từ trước khi
sửa gì. Đã tạo bằng `gateway/csdl.mo()` (chỉ tạo **file dữ liệu**, không sửa mã trong `gateway/`).

## 2. Bộ thử backend

| Bộ | Trước khi sửa | Sau khi sửa |
|---|---|---|
| `python3 app/thu/thu_saas.py` | 19 test — FAILED 1 (`test_16`, thiếu `gateway.db`), sau khi tạo file: **OK 19/19** | **OK 19/19** |
| `python3 app/thu/thu_g01_g02.py` | **OK 21/21** | **OK 21/21** |

`thu_saas.test_13` là test quét mã `admin/` không chứa secret — nó `os.listdir("admin")` rồi
mở **từng file** bằng UTF-8. Vì vậy **cấm tạo thư mục con trong `admin/`** (sẽ `IsADirectoryError`),
và chính file này cũng bị quét. Đã chạy lại sau khi thêm file này: vẫn ĐẠT.

## 3. Kịch bản kiểm tay — đã chạy thật trong trình duyệt

### 3.1 Phiên hết hạn (401) — ĐẠT

1. Đăng nhập `shopa-owner`, sau đó đăng nhập lại bằng `shopa-viewer`.
2. Gọi thẳng `POST /api/v2/auth/dang-xuat` ở tầng mạng (không bấm nút Đăng xuất) để **thu hồi
   phiên thật** trong khi giao diện vẫn tưởng mình đang đăng nhập.
3. Bấm menu **Khách hàng**.

Kết quả đo: màn **"Phiên đăng nhập đã hết hạn"** hiện ra, có nêu `HTTP 401`, nêu thông điệp
gốc của máy chủ (*"chưa đăng nhập hoặc phiên hết hạn"*), cảnh báo dữ liệu đang nhập không được
giữ, và câu *"Đăng nhập lại xong, hệ thống mở lại màn Khách hàng."*
Bấm **Đăng nhập lại** → form đăng nhập vẫn giữ dòng nhắc *"Đăng nhập xong sẽ mở lại màn Khách hàng."*
Đăng nhập xong → mở đúng màn **Khách hàng**, kèm toast báo đã mở lại.

Trước thay đổi này, cùng kịch bản chỉ rơi về **màn đăng nhập trống**, không nói lý do, mất màn đang xem.

### 3.2 Không đủ quyền (403) — ĐẠT, bằng 403 THẬT của backend

Không dùng 403 giả. Cách tạo ca thật:

1. Đăng nhập `shopa-viewer` (vai trò `TENANT_VIEWER`, có `tenant.khach.xem`).
2. Trong lúc phiên đang mở, **xóa quyền trong CSDL**:
   `DELETE FROM role_permissions WHERE role_ma='TENANT_VIEWER' AND perm_ma='tenant.khach.xem'`.
   Giao diện vẫn còn danh sách quyền cũ lấy lúc đăng nhập ⇒ menu vẫn hiện, nhưng backend sẽ từ chối.
3. Bấm menu **Khách hàng** → `GET /api/v2/khach-hang` trả **403 thật**.

Kết quả đo (trích nguyên văn từ trang): khối 🔒 **"Không đủ quyền"** với
*"máy chủ trả HTTP 403 — quyết định chặn nằm ở backend, không ở giao diện"*, bảng nêu
**việc vừa làm** (mở màn Khách hàng), **vai trò hiện tại** (`TENANT_VIEWER` tại Shop Demo A),
**quyền còn thiếu** (`tenant.khach.xem`), **thông điệp máy chủ**, và **cách mở**.
Khối nằm lại trên màn hình, không phải toast trôi 3 giây như trước.

4. **Đã trả quyền về như cũ** sau khi đo:
   `INSERT OR IGNORE INTO role_permissions VALUES ('TENANT_VIEWER','tenant.khach.xem')` —
   kiểm lại: 5 quyền của `TENANT_VIEWER` đúng như ban đầu.

Với hành động ghi (tạo đơn, rotate khóa, mời thành viên…), 403 mở **hộp thoại** cùng nội dung
đó thay vì khối toàn màn — đã gắn tên việc + tên quyền cho 12 chỗ gọi quan trọng.

### 3.3 Ánh xạ cột import — ĐẠT cả hai nhánh

**Nhánh A — backend CHƯA có (đây là tình trạng thật hôm nay).**
`curl -b ck.txt http://127.0.0.1:8921/api/v2/import/1/anh-xa-cot` → **404**.
Giao diện mở batch #1 hiện thẻ **"Ánh xạ cột <span>CHỜ BACKEND</span>"**, nói rõ đã gọi
`GET /api/v2/import/1/anh-xa-cot` và nhận `HTTP 404`, rồi hiện bảng chẩn đoán **suy từ dữ liệu thật
của batch**: trường nào bắt buộc, trường nào trống ở mọi dòng (đo được: `so_luong`,
`gia_tri_khai`, `ghi_chu` trống toàn bộ ⇒ nhiều khả năng chưa ánh xạ), giá trị dòng đầu.
Bảng này **không** tự xưng là ánh xạ thật — ghi rõ *"suy ra từ dữ liệu batch, không phải từ API ánh xạ"*,
vì backend hiện **không** trả tên cột gốc trong file.

**Nhánh B — backend ĐÃ có.** Chưa có backend nên nhánh này được kiểm bằng cách **thay tạm
`window.fetch` trong trình duyệt** để trả về đúng hình dạng JSON đề xuất (ghi rõ: đây là
**stub trong trình duyệt**, không phải endpoint thật, và **không** đụng mã nguồn). Đo được:

- 7 cột trong file hiện đủ, kèm giá trị mẫu, mỗi cột một ô chọn trường nội bộ;
- ánh xạ sẵn từ máy chủ được chọn đúng: cột 0→`nguoi_nhan_ten` … cột 4→`khoi_luong_gram`, cột 5–6 để trống;
- huy hiệu **"đủ trường bắt buộc"** tính đúng;
- chốt chặn trùng: đặt hai cột cùng trỏ `nguoi_nhan_ten` → báo *"Một trường chỉ nhận một cột. Trùng: nguoi_nhan_ten"*, **không** gửi đi;
- lưu hợp lệ → `PUT` và hiện *"Đã lưu ánh xạ — kiểm lại: {"VALID":2,"INVALID":1}"*;
- nếu `PUT` trả 404 → báo *"Máy chủ chưa có endpoint lưu ánh xạ (404) — CHỜ BACKEND"*, không giả vờ đã lưu.

Sau khi đo đã **gỡ stub**, trả `window.fetch` về bản gốc.

**Trạng thái mới:** `UPLOADED…FAILED` cho batch và `UNSUPPORTED` / `NEEDS_REVIEW` cho dòng đã có
nhãn tiếng Việt + màu. Trạng thái **lạ** (chưa có trong bảng) hiện **nguyên văn** với huy hiệu xám
thay vì bị bỏ qua im lặng. Dữ liệu thật hiện đang là bộ cũ (`moi`, `xong`, `da_duyet_mot_phan`) —
cũng đã có nhãn. Trong hộp duyệt: dòng `UNSUPPORTED` bị loại và nói rõ, dòng `NEEDS_REVIEW` chỉ gửi
khi người dùng tự tick.

### 3.4 Dashboard F05 — ĐẠT

Số liệu thật đo được trên nền thử (2 đơn, 2 hãng, 1 batch):

- **Theo hãng**: ghép `carrier_account_id` của đơn với `GET /api/v2/tai-khoan-hang`. Bảng ra
  `J&T Express jt: 1 đơn / 1 đã gửi / 0 ₫`, `Viettel Post vtp: 1 đơn / 1 đã gửi / 250.000 ₫`,
  kèm biểu đồ cột (canvas tự vẽ, không CDN).
- **Theo trạng thái**: biểu đồ tròn.
- **Theo ngày**: biểu đồ đường theo `tao_luc`.
- **Thống kê import**: đếm batch theo trạng thái từ `GET /api/v2/import`.
- **Hoạt động gần đây**: 12 mục mới nhất từ `GET /api/v2/audit`; vai trò không có
  `tenant.audit.xem` thì nói thẳng là không có quyền, **không** hiện bảng rỗng cho giống có dữ liệu.

Về nhãn DEMO (§12 chống bịa): **không có con số nào bịa trên màn này.** Thay vì rắc chữ DEMO lên
số thật, màn có hộp **"Nguồn số liệu màn này"** ghi từng chỉ số lấy từ API nào và **phạm vi**
tới đâu (ví dụ *"toàn bộ 2 đơn của doanh nghiệp"*, hoặc *"500 đơn mới nhất — chạm trần API"*),
kèm nhãn **`DỮ LIỆU LOCAL / HÃNG MOCK`** cho toàn màn. Chỉ số **chưa có backend** (tỷ lệ giao
thành công theo thời gian, SLA, đối soát COD, tổng số dòng import) có thẻ riêng
**`CHỜ BACKEND`** và **để trống, không hiện số minh họa**.

Một lỗi tự bắt được khi nhìn ảnh chụp: chú giải biểu đồ cột ban đầu tô **2 màu** cho 2 hãng
trong khi biểu đồ vẽ **1 màu** (một chuỗi dữ liệu). Chú giải nói sai về chính hình nó chú thích —
đã sửa thành một dòng *"Số đơn — tên hãng ghi dưới trục ngang"*.

### 3.5 Carrier UI F03 — ĐẠT

Mỗi hãng hiện: mã hãng, **trạng thái kết nối**, cờ `live_mo`, và **capabilities** dạng
✓/✕ có tên tiếng Việt. Đo thật từ `GET /api/v2/hang`: `jt` có `getOrder: false` ⇒ hiện
**✕ Tra đơn** gạch ngang; `vtp` đủ 7 khả năng ⇒ 7 dấu ✓.

Trạng thái kết nối **suy từ `GET /api/v2/tai-khoan-hang`** (có tài khoản hãng không, đang bật hay
khóa) — đo được *"Đã kết nối (1/1 đang bật)"* cho cả hai hãng. Ghi chú ngay dưới nói rõ đây
**không** phải phép ping hãng: giao diện không gọi hãng, muốn biết hãng có trả lời thật hay không
thì cần API kiểm kết nối ở backend (`CHỜ BACKEND`).

**Secret:** bảng tài khoản vẫn chỉ hiện `…mock` (đuôi do backend trả) kèm *"mã hóa, không xem lại được"*.
Không thêm chỗ nào hiện secret. `thu_saas.test_13` vẫn ĐẠT.

## 4. Bố cục ba cỡ — số đo, không phải cảm nhận

Phép đo: với từng cỡ, bấm lần lượt **mọi** mục menu của `shopa-owner` rồi so
`document.documentElement.scrollWidth` với `clientWidth`. Lớn hơn = trang tràn ngang.

| Cỡ | `clientWidth` | Nút ☰ | 10 màn tenant (`shopa-owner`) | Kết quả |
|---|---|---|---|---|
| Điện thoại | 375 | hiện | tong-quan · don · khach · import · hang · webhook · thanh-vien · goi · nhat-ky · cai-dat | **không màn nào tràn** |
| Tablet | 768 | hiện | 10 màn như trên | **không màn nào tràn** |
| Desktop | 1280 | ẩn | 10 màn như trên | **không màn nào tràn** |

Bốn màn phạm vi nền tảng cũng đã đăng nhập `platform-owner` và bấm lại (phần sửa 401/403 là mã
dùng chung nên ảnh hưởng tới chúng):

| Cỡ | `tenants` | `vai-tro` | `audit-nen-tang` | `cai-dat` |
|---|---|---|---|---|
| 375 | ok | ok | ok | ok |
| 1280 | ok | ok | ok | ok |

Ở 375px còn mở thêm **batch import** và **hộp thoại sửa dòng**: không tràn, modal rộng 355/375.

**Một lỗi THẬT bắt được nhờ phép đo này:** lần đo đầu ở 375px ra
`scrollWidth 562 > clientWidth 375` — cả trang tràn ngang. Nguyên nhân: ô của `display:grid`
mặc định `min-width:auto`, nên bảng rộng bên trong `.cuon-ngang` đẩy phình cả cột lưới, làm
vùng cuộn ngang mất tác dụng. Đã vá bằng `.luoi > * { min-width: 0 }` trong
`assets/css/style.css`. Đo lại: 375 = 375, hết tràn.

**Lưu ý khi đo lại:** pane trình duyệt báo `innerWidth` là **562** trong khi `clientWidth` là **375**
(pane có scale riêng). Media query chạy theo `clientWidth` — kiểm bằng `matchMedia("(max-width:560px)")`
trả `true` mới chắc. Đừng kết luận cỡ màn hình bằng `innerWidth` ở môi trường này.

10 trang demo G00 (`pages/*.html`) dùng chung `style.css` nên cũng đo lại ở 375px bằng iframe:
cả 10 trang **không tràn**. Không trang nào bị sửa nội dung.

## 5. Chưa kiểm được / giới hạn còn lại

1. **Nhánh "backend đã có" của ánh xạ cột chạy trên stub**, không phải endpoint thật. Khi AG-04
   bật endpoint mà **hình dạng JSON khác đề xuất**, giao diện sẽ hiện sai hoặc trống — phải đo lại.
2. **Không có bộ thử tự động cho frontend.** Mọi kết quả trên là một lượt bấm tay; sửa sau này
   không có gì chặn hồi quy. Muốn chặn thì cần bộ thử trình duyệt tự động (chưa có trong dự án).
3. **Chỉ kiểm trên một trình duyệt** (Chromium trong Browser pane). Safari/Firefox chưa đo.
   Mã dùng `class`, template literal, optional chaining mức cơ bản — không có polyfill.
4. **Chưa đo với dữ liệu lớn**: nền thử chỉ có 2 đơn, 1 batch 3 dòng, 2 hãng. Bảng vài nghìn
   dòng, batch vài nghìn dòng, hay nhiều hãng chưa biết chạy thế nào (không phân trang phía
   giao diện — `GET /api/v2/don` trần 500).
5. **Chưa kiểm trên thiết bị cảm ứng thật**, chỉ là giả lập cỡ màn.
6. **Chưa kiểm tiếp cận (accessibility)** bằng trình đọc màn hình.
7. **Không có uncaught exception** nào trong console suốt các lượt bấm; các dòng đỏ trong
   console chỉ là trình duyệt ghi lại mã HTTP không-2xx (401 trước khi đăng nhập, 404 của
   endpoint ánh xạ chưa có, 403 của ca kiểm quyền) — đều là ca cố tình tạo ra và đã được mã bắt.

---

# ĐỢT F04 — 15/10/2026 (AG-04): đã có bộ thử tự động, và đây là lượt đo tầng 3

Mục 5.2 ở trên viết *"Không có bộ thử tự động cho frontend"* — **câu đó nay đã cũ**. Bộ thử
dựng ở `thu_frontend/`, mô tả đầy đủ ở `docs/FRONTEND_AUTOMATION.md`.

| Tầng | Lệnh | Số ca | Kết quả 15/10/2026 | Trình duyệt thật? |
|---|---|---|---|---|
| 1 — logic thuần | `node --test thu_frontend/thu_logic.mjs` | 56 | **56 đạt** | không |
| 2 — HTTP + tệp tĩnh | `python3 thu_frontend/thu_http.py` | 36 | **36 đạt** | không |
| 3 — trình duyệt thật | *(chưa tự động hoá — xem bên dưới)* | 30 phép đo + 9 kịch bản | đạt | **có** |

## Tầng 3 — số đo thật, đo bằng Chrome, ngày 15/10/2026

**Nền đo:** server `python3 app/server.py 8931`, `VIP_HUB_DATA` trỏ thư mục nháp của phiên
(không ghi vào `app/du-lieu/`), dữ liệu mồi: 9 đơn (4 đã gửi hãng mock, 1 hủy, phần còn lại
nháp/đã duyệt), 1 batch import 3 dòng, 3 sự kiện webhook (1 `khong_khop`, 1 `AMBIGUOUS` mô
phỏng AG-03, 1 `dlq` 5 lần thử).

### Tràn ngang — `scrollWidth` vs `clientWidth`, không đo bằng mắt

| Đối tượng | 375px | 768px | 1280px |
|---|---|---|---|
| 10 màn SPA quản trị | **0 tràn / 10 màn** | **0 / 10** | **0 / 10** |
| Modal chi tiết đơn, 4 tab | **0 / 4 tab** | — | — |
| 10 trang demo G00 | **0 / 10 trang** | — | — |

Phần tử nằm trong `.cuon-ngang` **cố ý loại khỏi phép đo**: bảng rộng phải cuộn ngang trong
vùng của nó, đó là thiết kế chứ không phải lỗi. Ngoài vùng cuộn: 0 phần tử tràn ở mọi lượt.

### Chín kịch bản bấm thật

| # | Kịch bản | Kết quả đo |
|---|---|---|
| 1 | Đăng nhập `shopa-owner` | dashboard dựng, 6 lượt gọi API đều 200 |
| 2 | Đi hết 10 màn SPA | tiêu đề đúng từng màn, không exception JS |
| 3 | Bộ lọc nâng cao | COD ≥ 300.000: 8→3 · hãng `vtp`: 8→4 · chưa có vận đơn: 8→4 · xóa lọc: 8/8. Dòng "phạm vi lọc" đếm đúng số điều kiện |
| 4 | Chế độ dữ liệu | 4 **LOCAL REAL DATA** + 4 **MOCK DATA** + **0 LIVE** |
| 5 | Tạo đơn trên UI | form trống → **8 ô báo lỗi tại chỗ, không gọi API** · cân nặng 0 → chặn · sửa đúng → tạo thật `T1-000009`, bảng 8→9 dòng |
| 6 | Chi tiết đơn | 4 tab chạy · timeline 2 nút · phiếu in đúng tiêu đề *"PHIẾU NỘI BỘ — KHÔNG PHẢI NHÃN VẬN ĐƠN"* |
| 7 | Từ chối đơn | thiếu lý do → chặn · "Lý do khác" thiếu ghi chú → chặn · hợp lệ → gọi thật → **HTTP 404** → hộp CHỜ BACKEND, nút bị khóa, **không** báo đã từ chối |
| 8 | Webhook monitor | KPI 3 / 1 DLQ / 8 lần thử lại / 1 nhập nhằng · `AMBIGUOUS` hiện **nguyên văn** kèm ⚠ trong khối riêng · chi tiết sự kiện kèm hộp CHỜ BACKEND |
| 9 | 401 + chuyển tenant | thu hồi phiên ngầm → màn "Phiên đăng nhập đã hết hạn", nhớ *"mở lại màn Đơn hàng"* · chuyển tenant A (OWNER, 8 đơn) → B (ADMIN, 0 đơn) |

### Tầng 3 chưa kiểm được gì

1. **Chưa tự động hoá.** Repo cấm thêm thư viện ngoài nên không có Playwright/Puppeteer; tầng 3
   là phiên Claude lái Chrome bằng tay, **không chạy lại được bằng một lệnh**. Đây vẫn là lỗ
   hổng hồi quy của lớp DOM/CSS — chỉ là nhỏ hơn trước, vì phần quyết định đã xuống tầng 1.
2. **Khối "Không đủ quyền" (403) chưa dựng lại bằng mắt ở lượt này**: người chỉ xem không còn
   nút nào trên giao diện dẫn tới 403 (menu ẩn đúng, nút ẩn đúng). Đã đo phía HTTP:
   `GET /api/v2/memberships` với `TENANT_VIEWER` trả **403 + `{"loi": "không đủ quyền"}`** —
   đúng thứ khối 403 cần. Mã dựng khối này không bị đợt F04 sửa.
3. **Chỉ Chrome.** Safari/Firefox chưa đo. Dưới 375px chưa đo.
4. **In thật** (ra máy in / PDF) chưa thử; chỉ kiểm có `@media print` và khung `#pi-giay`.
5. **Dữ liệu lớn vẫn chưa đo** — giới hạn 4 ở mục 5 phía trên còn nguyên: 9 đơn, 1 batch 3 dòng.
   Bộ lọc nâng cao chạy **tại giao diện trên tập đã tải**, nên với CSDL lớn nó lọc thiếu; giao
   diện có nói rõ phạm vi này nhưng đó là vá bằng lời, không phải vá bằng cấu trúc.
