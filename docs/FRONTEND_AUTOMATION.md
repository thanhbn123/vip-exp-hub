# BỘ THỬ FRONTEND TỰ ĐỘNG (F04) — AG-04

Trước đợt này, **mọi kết quả frontend đều là bấm tay** (`admin/thu_frontend.md`). Không có gì
chặn hồi quy: sửa một dòng ở `admin.js` thì không ai biết màn nào vừa gãy cho tới khi có người
mở lại đúng màn đó. Tài liệu này mô tả bộ thử dựng để lấp lỗ hổng ấy.

**Đo ngày 15/10/2026, trên MacBook Pro** (node v26.7.0 ở `/opt/homebrew/bin`, python 3.9.6,
Chrome của máy). Số trong tài liệu là số lượt chạy thật, không ước lượng.

---

## 1. Ba tầng — và tầng nào KHÔNG tự chạy được

Chia ba tầng vì ba thứ khác nhau bị hỏng theo ba cách khác nhau. Gộp lại thành một con số
"bao nhiêu test đạt" là đúng dạng §12.1 luật 3: nói rộng hơn phạm vi đã đo.

| Tầng | Công cụ | Số ca | Trình duyệt thật? | Phủ cái gì | KHÔNG phủ cái gì |
|---|---|---|---|---|---|
| **1 — logic thuần** | `node --test` | **56** | **không** | quyết định nhãn trạng thái, chế độ dữ liệu MOCK/LOCAL/LIVE, bộ lọc đơn, dựng dòng thời gian, kiểm form, chọn tài khoản hãng, metadata phiếu in, gom nhóm webhook, bảng API chờ backend, canh cấu trúc file | DOM, CSS, bố cục, fetch, quyền thật |
| **2 — HTTP + tệp tĩnh** | `python3` + `unittest`, server THẬT | **36** | **không** | tệp tĩnh phục vụ được, mọi endpoint giao diện gọi có thật, mọi nhãn "CHỜ BACKEND" có đúng là chưa có, 401/403/404/400, chuyển tenant, tạo → duyệt → gửi → mốc timeline, preview import, xuất CSV, rò secret | cái mắt thấy: có hiện nhãn không, có bấm được không, có tràn ngang không |
| **3 — trình duyệt thật** | Chrome qua công cụ điều khiển trình duyệt của phiên Claude | **30 phép đo tràn ngang + 9 kịch bản** | **có** | bố cục ở 375/768/1280, luồng bấm thật, modal, in, 401 giữa chừng, chuyển tenant trên giao diện | **chưa tự động hoá** — xem mục 4 |

**Tầng 1 và tầng 2 chạy bằng một lệnh:**

```sh
sh thu_frontend/chay.sh
```

Hoặc riêng từng tầng:

```sh
node --test thu_frontend/thu_logic.mjs      # tầng 1
python3 thu_frontend/thu_http.py            # tầng 2
```

**Tầng 3 KHÔNG nằm trong `chay.sh`** và script nói thẳng điều đó khi chạy xong. Lý do ở mục 4.

---

## 2. Vì sao tách `admin/logic.js`

`admin/admin.js` là một IIFE dựng HTML — không xuất gì ra ngoài, nên Node không với tới được.
Có hai đường: kéo cả DOM vào Node (thêm thư viện, trái ràng buộc "không thư viện ngoài"), hoặc
**kéo logic ra khỏi DOM**. Chọn đường thứ hai.

`admin/logic.js` là **file phẳng trong `admin/`** (không phải thư mục con — `thu_saas.py::test_13`
dùng `os.listdir('admin/')` rồi `open()` từng mục, gặp thư mục là `IsADirectoryError`; tầng 1 ca
56 và tầng 2 ca 07 canh đúng điều này). Nó:

- không chạm DOM, không fetch, không timer — **tầng 1 ca 53 quét mã để cưỡng chế**;
- không giữ secret — **ca 54**;
- là **chỗ khai duy nhất** các bảng trạng thái; `admin.js` không được giữ bản sao — **ca 55**.
  (Hai bản nội dung là hai bản sẽ lệch nhau.)
- xuất qua `window.VIPLOGIC` cho trình duyệt và `module.exports` cho Node. Đây là hai dòng guard,
  không phải thư viện mới.

`admin/index.html` nạp theo thứ tự `app.js` → `logic.js` → `admin.js`. Sai thứ tự thì SPA chết
ngay dòng đầu mà không có thông báo nào dễ hiểu — **tầng 2 ca 02 canh thứ tự này**.

---

## 3. Ca đáng chú ý — và vì sao nó tồn tại

### 3.1 Nhãn "CHỜ BACKEND" không nói dối được (tầng 2, ca 09)

Giao diện khai mọi endpoint còn thiếu ở **một chỗ duy nhất**: `admin/logic.js → API_CHO_BACKEND`.
Tầng 2 **đọc đúng bảng đó ra khỏi file JS** (không chép lại sang Python) rồi **bắn thật** vào máy
chủ. Backend làm xong mà giao diện vẫn dán nhãn chờ ⇒ ca HỎNG, buộc phải gỡ nhãn và nối màn vào.

Nhãn chờ-backend là dạng câu dễ mục nhất: viết hôm nay đúng, ba tuần sau sai mà không ai thấy.

### 3.2 Khóa an toàn LIVE (tầng 1 ca 13–16, tầng 2 ca 22–23)

`CHO_PHEP_LIVE=False` và `live_mo=0`. Giao diện chỉ được dán **LIVE CARRIER DATA** khi đúng **cả
hai**: tài khoản hãng khác môi trường `mock` **và** hãng mở `live_mo`. Có ca riêng cho từng nửa
điều kiện, vì chỗ này sai một nửa là người dùng tưởng đang gửi hàng thật.

Tầng 2 đo lại nguồn mà giao diện dựa vào (`GET /api/v2/hang`) và chặn luôn đường tạo tài khoản
hãng ở môi trường thật từ giao diện.

### 3.3 Timeline không bịa mốc giờ (tầng 1 ca 28–31, tầng 2 ca 20)

Dòng thời gian dựng từ `don_lich_su` (§11). Trạng thái giao hiện tại **không** có trong lịch sử
thì nút cuối gắn cờ `suy_ra` và `luc = null` — hiện ra giấy là *"không có mốc giờ — suy ra từ
trường `trang_thai_giao`"*. Bịa giờ là đúng ca 9 của §12.1.

Tầng 2 kiểm phía backend: duyệt + gửi phải sinh đủ mốc, mốc nào cũng phải có giờ, và `nguon`
phải khớp `user:<id> | webhook:<id> | polling | he_thong`.

### 3.4 Trạng thái lạ hiện nguyên văn (tầng 1 ca 02, 04, 05, 09, 10)

AG-03 đang thêm `NEEDS_REVIEW` / `AMBIGUOUS` cho mã J&T 110. Giao diện **không** gộp chúng vào
"lỗi", **không** đổi tên: hiện nguyên văn kèm dấu ⚠ và gom vào khối cảnh báo riêng. Trạng thái lạ
cũng **không được bịa `rank`**.

### 3.5 Phiên dùng chung là thứ kiểm chứng không đáng tin (tầng 2)

Lượt chạy đầu có **3 ca hỏng `401 ≠ 403`**. Nguyên nhân: ca 12 vô hiệu membership của người chỉ
xem, backend **thu hồi phiên** của người đó (đúng hành vi), nhưng phiên dùng chung `cls.viewer`
chết âm thầm và ba ca sau đo nhầm thứ. Đã sửa thành property đăng nhập lại mỗi lần, và ghi lý do
ngay tại chỗ để lần sau không ai gom lại.

### 3.6 Cổng cố định đụng nhau giữa các worktree

Lượt chạy nền đầu tiên, `python3 app/thu/thu_g01_g02.py` **HỎNG** vì
`gateway/thu/thu_gateway.py` bind cứng cổng `18898` và một worktree khác đang giữ. Chạy lại là
đạt. `thu_frontend/thu_http.py` **bind cổng 0** để hệ cấp cổng trống — nhiều phiên chạy song song
không đụng nhau.

> **Việc cho AG-00:** `thu_saas.py` (18897), `thu_g01_g02.py` (18896), `thu_gateway.py` (18898)
> nên chuyển sang bind 0. Đây là lỗi hạ tầng bộ thử, không phải lỗi sản phẩm, nhưng nó làm bộ thử
> **báo hỏng giả** — kiểu sai tệ nhất với một cổng chặn hồi quy.

---

## 4. Tầng 3 — trình duyệt thật, và vì sao CHƯA tự động hoá

Repo cấm thêm thư viện ngoài và CDN. Không có Playwright/Puppeteer, và kéo chúng vào chỉ để chạy
test là đổi ràng buộc của dự án — việc đó phải do AG-00 quyết, không phải AG-04 tự làm.

Nên tầng 3 ở lượt này **do phiên Claude điều khiển Chrome thật**, không phải script chạy lại
được. **Nói thẳng: đây chưa phải chặn hồi quy tự động.** Nó là phép đo có thật, một lần, ngày
15/10/2026 — ghi số đo lại ở `admin/thu_frontend.md` mục "Tầng 3".

### Phép đo tràn ngang (F05)

Đo bằng `scrollWidth` vs `clientWidth` trên `document`, **không đo bằng cảm nhận**. Phần tử nằm
trong `.cuon-ngang` được loại trừ có chủ ý: bảng rộng **phải** cuộn ngang trong vùng của nó.

- 10 màn SPA quản trị × 3 bề rộng (375 / 768 / 1280) = **30 phép đo, tràn = 0 ở cả 30**.
- Modal chi tiết đơn × 4 tab (Thông tin / Dòng thời gian / Lịch sử / Phiếu in) ở **375px**:
  tràn = 0 ở cả 4.
- 10 trang demo G00 ở **375px**: tràn = 0 ở cả 10 (CSS dùng chung, phải không bị phá).

### Chín kịch bản đã chạy bằng Chrome thật

1. Đăng nhập → dashboard dựng, 6 lượt gọi API đều 200.
2. Điều hướng 10 màn SPA, mỗi màn có tiêu đề đúng, không lỗi JS.
3. Bộ lọc nâng cao: COD ≥ 300.000 (8→3), theo hãng `vtp` (8→4), chưa có mã vận đơn (8→4), xóa
   lọc về 8/8. Dòng "phạm vi lọc" cập nhật đúng số điều kiện.
4. Chế độ dữ liệu: 4 đơn **LOCAL REAL DATA** + 4 đơn **MOCK DATA**, **0 đơn LIVE**.
5. Tạo đơn trên UI: form trống → **8 ô báo lỗi tại chỗ, không gọi API**; cân nặng 0 → chặn;
   sửa đúng → tạo thật `T1-000009`, bảng từ 8 lên 9 dòng, nhãn LOCAL REAL DATA.
6. Chi tiết đơn: 4 tab chạy, timeline có 2 nút, phiếu in hiện đúng tiêu đề
   **"PHIẾU NỘI BỘ — KHÔNG PHẢI NHÃN VẬN ĐƠN"**.
7. Từ chối đơn: thiếu lý do → báo tại chỗ; chọn "Lý do khác" không ghi chú → báo tại chỗ; chọn lý
   do hợp lệ → gọi thật → **HTTP 404** → hiện hộp CHỜ BACKEND, khóa nút, **không** tuyên bố đã
   từ chối.
8. Webhook monitor: KPI 3 sự kiện / 1 DLQ / 8 lần thử lại / 1 nhập nhằng; `AMBIGUOUS` hiện nguyên
   văn kèm ⚠ trong khối riêng; chi tiết sự kiện mở ra kèm hộp CHỜ BACKEND.
9. 401 giữa chừng (thu hồi phiên ngầm rồi bấm menu) → màn "Phiên đăng nhập đã hết hạn", bấm đăng
   nhập lại thì hiện *"Đăng nhập xong sẽ mở lại màn Đơn hàng"*.
   Chuyển tenant: A (OWNER, 8 đơn) → B (ADMIN, 0 đơn), vai trò và phạm vi dữ liệu đổi hẳn.

### Cái tầng 3 CHƯA kiểm

- Hộp **"Không đủ quyền" (403)** chưa dựng lại được bằng mắt trong lượt này: người chỉ xem không
  có nút nào trên giao diện dẫn tới 403 (menu đã ẩn đúng, nút đã ẩn đúng). Đã đo được phía HTTP:
  `GET /api/v2/memberships` với vai trò `TENANT_VIEWER` trả **403 + `{"loi": "không đủ quyền"}`},
  đúng thứ khối 403 cần. Mã dựng khối này **không bị đợt F04 sửa**.
- In thật ra máy in / PDF (chỉ kiểm CSS `@media print` tồn tại và khung `#pi-giay` dựng đúng).
- Safari, Firefox, máy thật cỡ nhỏ hơn 375px.

---

## 5. Thêm ca mới thì thêm ở đâu

| Thứ muốn canh | Thêm vào |
|---|---|
| Một quyết định (nhãn gì, lọc ra sao, hợp lệ hay không) | hàm thuần ở `admin/logic.js` + ca ở `thu_frontend/thu_logic.mjs` |
| Một endpoint mới giao diện gọi | thêm vào `API_DANG_DUNG` — tầng 2 ca 08 tự bắn |
| Một endpoint còn thiếu | thêm vào `API_CHO_BACKEND` — tầng 2 ca 09 tự canh, giao diện tự hiện nhãn |
| Một hành vi HTTP (mã lỗi, trường trả về) | ca mới ở `thu_frontend/thu_http.py` |
| Một thứ chỉ thấy bằng mắt | mục "Tầng 3" ở `admin/thu_frontend.md`, ghi rõ ngày đo |

**Cấm viết logic mới thẳng vào `admin.js`** nếu nó là một *quyết định* — viết ở `logic.js` thì
mới có ca thử. `admin.js` chỉ nên dựng HTML và gắn sự kiện.
