# G20 · AG-02 — FRONTEND J&T + E2E: BA KHOẢNG TRỐNG CÒN LẠI

**Làn:** `g20-ag02-frontend` · **Nền:** `integration/g19` @ `148ecd3` (`git log --oneline -1` →
`148ecd3 Merge branch 'g19-ag06-banphim' into integration/g19`) · **Ngày đo:** 16–17/10/2026 ·
**Người đo:** AG-02.

**Tệp đã ghi (đúng danh sách được cấp):**

| Tệp | Trước | Sau | Ghi chú |
|---|---|---|---|
| `admin/billing.js` | `d68e2a18dccc` · 224 dòng | `a4b88ee3b2d1` · 242 dòng | `+39 / −21`; **chỉ** khối bảng đường + chú thích |
| `admin/admin.js` | `0f38739c34ed` · 2814 dòng | `f99008e8d02a` · 2821 dòng | `+19 / −12`; **chỉ** chú thích và câu chữ trong hộp "Nguồn số liệu" |
| `thu_giao_dien/06_ban_phim.spec.js` | `b3edcfa806f2` · 277 dòng | `7e636859bab3` · 328 dòng | `+54 / −3`; ca 04 sửa ngân sách Tab, thêm ca 04b TỰ KIỂM |
| `thu_giao_dien/08_bang_duong_billing.spec.js` | (mới) | `488eec550d05` · 254 dòng | ca canh bảng khai đường |
| `thu_giao_dien/09_man_ag05.spec.js` | (mới) | `434245786dbf` · 415 dòng | 20 màn AG-05: bấm được + đọc dữ liệu thật |
| `thu_giao_dien/10_trang_tinh_du_lieu.spec.js` | (mới) | `c1974296fa72` · 279 dòng | `pages/*.html`: nguồn dữ liệu thật |
| `docs/G20_FRONTEND.md` | (mới) | tài liệu này | |

SHA là **blob** (`git hash-object`), không phải commit — làn này **không commit** (xem §8.2).

`git status --short` → `M admin/admin.js`, `M admin/billing.js`, `M thu_giao_dien/06_ban_phim.spec.js`,
`?? thu_giao_dien/08…`, `?? thu_giao_dien/09…`, `?? thu_giao_dien/10…`, `?? docs/G20_FRONTEND.md`.
**Không** chạm `pages/*.html`, `pages/*.js`, `admin/logic.js`, `admin/ban_phim.js`,
`admin/carrier_health.js`, `admin/finance.js`, `admin/health.js`, `admin/ai.js`, `app/**`,
`thu_giao_dien/tien_ich.js`, `thu_giao_dien/chay.sh`, `playwright.config.js`.
`pages/*.html` và `pages/*.js` **nằm trong** danh sách được cấp ghi nhưng **không cần sửa** —
đo ra chúng vốn đã đúng; khoảng trống của mục (c) nằm ở **ca thử**, không ở trang (§5).

---

## 0. TÓM TẮT

Ba khoảng trống nêu trong nhiệm vụ **đều có thật và đều đã đo được**; cả ba đã đóng, mỗi cái
kèm một ca TỰ KIỂM chứng minh ca thử **ĐỎ ĐƯỢC**:

| # | Khoảng trống | Đo được | Đã làm |
|---|---|---|---|
| (a) | `billing.js → API_CHO_BACKEND` sai đường 5 dòng | cả 5 đường → **HTTP 404** | sửa 5 đường + **1 dòng thứ sáu** (xem §3.2); thêm ca canh hai chiều |
| (b) | 20 màn AG-05 chưa có ca E2E "bấm được + đọc dữ liệu thật" | `04_nhan…` chỉ canh *mở được · không lỗi console · không tràn ngang* | ca mới: 20/20 bấm được, 20/20 gọi API thật, **8 màn CÓ DỮ LIỆU**, 12 màn vào sổ **CHƯA ĐO** |
| (c) | `pages/*.html` | 10 trang, **0** script nội tuyến | **7 trang CÓ DỮ LIỆU THẬT** · **3 trang CHƯA ĐO** (settings · create-order · pricing) |

**Bắt được hai việc NGOÀI ba khoảng trống, đều là hậu quả của 20 màn AG-05 cắm ở G19** (§7):

- `06_ban_phim.spec.js` ca 04 **ĐỎ** vì bấm CỨNG 30 lượt Tab — menu nay có 31 mục. Đây là
  **phép đo hỏng**, không phải sản phẩm hỏng. **Đã sửa** (ngân sách Tab co giãn theo menu) và
  thêm ca 04b chứng minh phép đếm ấy vẫn đỏ được.
- `06_ban_phim.spec.js` ca 07 **ĐỎ** và đây là **lỗi SẢN PHẨM có thật, chưa sửa**: ở 375px khi
  thanh bên đóng, điểm dừng Tab ĐẦU TIÊN nằm ở `nav.menu-quan-tri` với `x=-260` — ngoài khung
  nhìn. Nguyên nhân đo được: 31 mục menu làm `<nav>` **cuộn được** (`scrollHeight=1368` >
  `clientHeight=602`), Chromium cho phần tử cuộn được **nhận tiêu điểm ngầm**, mà
  `ban_phim.js → dongBoTabindex()` chỉ gỡ `tabindex` của các **thẻ `<a>`**, không gỡ của
  **thẻ `<nav>`**. Bản vá là **một dòng trong `admin/ban_phim.js`** — **ngoài danh sách tệp
  làn này được cấp ghi**, nên **không sửa**; xem §7.2.

---

## 1. PHẠM VI — CÁI ĐÃ ĐO VÀ CÁI NẰM NGOÀI

**Đã đo (mọi khẳng định dưới đây có lệnh thật + mã thoát thật, xem §8):** mã HTTP thật của
từng đường khai trong `billing.js`; đường nào `server.py` thật sự phục vụ (đọc mã nguồn VÀ
bắn HTTP); menu thật và tiêu đề thật của 20 màn; phản hồi `/api/v2/**` thật của từng màn;
giá trị lấy từ payload có xuất hiện trên DOM hay không; script nội tuyến trên 10 trang tĩnh;
nguồn dữ liệu thật của từng trang.

**Nằm NGOÀI phạm vi làn này (không đo, không sửa):**

- **`app/server.py`.** Không thêm, không sửa đường nào. Làn này chỉ **đọc** tệp ấy để đối chiếu.
- **`admin/ban_phim.js`.** Lỗi ở §7.2 nằm trong tệp này; **không được cấp ghi** ⇒ chỉ báo cáo.
- **`admin/logic.js`, `admin/ai.js`, `admin/finance.js`, `admin/health.js`,
  `admin/carrier_health.js`.** Không sửa một dòng nào.
- **`thu_giao_dien/tien_ich.js`, `chay.sh`, `playwright.config.js`.** Không sửa. Vì
  `tien_ich.js` không nằm trong danh sách được cấp, mọi hàm dùng chung của ba tệp mới đều
  **nằm trong chính tệp ấy**, không nhét thêm vào tệp dùng chung.
- **CSDL, PostgreSQL, sandbox, hãng vận chuyển.** Không chạm. Mọi phép đo chạy trên nền **cô
  lập** (`VIP_HUB_DATA` = thư mục tạm, xoá khi xong), máy chủ bind `127.0.0.1` cổng rỗng,
  chế độ hãng là **mock**, **không một lời gọi ra hãng**, không tunnel, không mở cổng ra ngoài.
- **Thao tác GHI trên các màn mới.** Không vẽ nút, không đo — giữ nguyên quyết định của AG-05.
- **Trình duyệt khác Chromium; thiết bị cảm ứng thật; trình đọc màn hình; in thật.** Đúng
  phạm vi mà `chay.sh` tự khai.

---

## 2. VIỆC ĐẦU TIÊN: BỘ THỬ TẦNG 3 KHÔNG CHẠY ĐƯỢC — SỬA MÔI TRƯỜNG

**Phải ghi ra vì nó chặn mọi phép đo, và vì nó KHÔNG phải lỗi của sản phẩm.**

Lượt chạy đầu tiên: **0 ca đạt** — cả 7 tệp spec chết ở `browserType.launch`:

```
Error: browserType.launch: Executable doesn't exist at
  …/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
```

`playwright.config.js` và `chay.sh` đặt `PLAYWRIGHT_BROWSERS_PATH=0` ⇒ Playwright 1.56.1 tìm
bản dựng **1194** trong `node_modules/`, không dùng kho chung `~/Library/Caches/ms-playwright/`
(kho ấy có 1148 và 1243 — **không bản nào khớp 1194**). `npx playwright install chromium` chạy
13 phút rồi **đứng** ở 624 KB đã giải nén. Nên đã cài tay:

```sh
unzip -q -o <zip chromium 1194 đã tải> -d node_modules/playwright-core/.local-browsers/chromium-1194
curl -sSL -o /tmp/ag02/hs.zip \
  https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1194/chromium-headless-shell-mac-arm64.zip
unzip -q -o /tmp/ag02/hs.zip -d node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194
```

`node_modules/` bị `.gitignore` chặn ⇒ **không vào bản giao**. Nhưng **người chạy lại phải biết**:
máy nào chưa có bản dựng 1194 thì bộ thử tầng 3 **không chạy được**, và triệu chứng là 7 tệp
spec cùng chết ở `browserType.launch` chứ không phải một ca hỏng.

**Lượt nền sau khi sửa môi trường (trước mọi thay đổi của làn này):**
`47 đạt / 1 hỏng / 3 không chạy` — ca hỏng là `06_ban_phim.spec.js:153` (ca 04), và vì tệp ấy
`mode: "serial"`, ba ca 05–07 **không chạy**. Nói cách khác: **ca 07 chưa từng được chạy ở nền
này** — nó bị ca 04 che. Xem §7.

---

## 3. KHOẢNG TRỐNG (a) — BẢNG KHAI ĐƯỜNG CỦA `admin/billing.js`

### 3.1 Đo lại: năm dòng sai đường, và đường thật

Bộ đo: `/tmp/ag02/do_duong.py` — dựng nền cô lập, bind `127.0.0.1` cổng rỗng, đăng nhập, bắn
HTTP thật. **Mã thoát `1`** (còn dòng không khớp — đúng như thiết kế của bộ đo).

```
== API_CHO_BACKEND khai trong billing.js (kỳ vọng: 404) ==
  GET    /api/v2/billing/goi                            HTTP 404
  GET    /api/v2/billing/dang-ky                        HTTP 404
  GET    /api/v2/billing/muc-dung                       HTTP 404
  GET    /api/v2/billing/canh-bao                       HTTP 404
  GET    /api/v2/billing/lich-su                        HTTP 404
  GET    /api/v2/billing/du-thao                        HTTP 200  <<< ĐÃ CẮM mà vẫn khai CHỜ
  POST   /api/v2/billing/du-thao                        HTTP 404
  POST   /api/v2/billing/usage                          HTTP 404
  POST   /api/v2/platform/goi/phien-ban                 HTTP 404
  POST   /api/v2/platform/tenants/{id}/doi-goi          HTTP 404
  POST   /api/v2/platform/tenants/{id}/tam-ngung        HTTP 404

== ĐƯỜNG THẬT mà 5 dòng sai đường ĐÁNG LẼ phải trỏ tới ==
  GET /api/v2/goi 200 · /api/v2/dang-ky 200 · /api/v2/usage 200
  GET /api/v2/usage/bao-cao 200 · /api/v2/usage/su-kien 200
```

**MỘT CHI TIẾT ĐO SAI ĐÃ BẮT ĐƯỢC Ở CHÍNH BỘ ĐO NÀY, ghi lại vì nó rất dễ lặp lại:**
`/api/v2/platform/**` có **cổng riêng** ở `server.py:566` — người không phải nhân sự nền tảng
nhận **403 TRƯỚC KHI tới bảng route**. Bản đầu của bộ đo dùng `shopa-owner` cho cả 11 dòng và
đọc ra **403** ở ba đường nền tảng; đọc thô thì 403 trông như "đường CÓ mà thiếu quyền". Đo lại
bằng `platform-owner` thì cả ba là **404** — tức **chưa cắm**, đúng như AG-05 đã ghi. Cùng cái
bẫy ấy làm ca 03 của tệp `08` **ĐỎ GIẢ** ở lượt chạy đầu (§3.3).

### 3.2 Sửa gì — năm dòng, và **một dòng thứ sáu**

Năm đường được sửa về đúng đường, và **chuyển từ `API_CHO_BACKEND` sang `API_DANG_DUNG`** —
chứ không phải chỉ đổi chữ rồi để nguyên trong bảng CHỜ. Lý do: đổi chữ mà giữ nhãn
"CHỜ BACKEND" là **đổi một lời nói dối này thành một lời nói dối khác**, và ca canh hai chiều
ở §3.3 sẽ bắt đúng điều đó.

| Dòng | Trước | Sau |
|---|---|---|
| 1 | `GET /api/v2/billing/goi` | `GET /api/v2/goi` |
| 2 | `GET /api/v2/billing/dang-ky` | `GET /api/v2/dang-ky` |
| 3 | `GET /api/v2/billing/muc-dung` | `GET /api/v2/usage` |
| 4 | `GET /api/v2/billing/canh-bao` | `GET /api/v2/usage/bao-cao` |
| 5 | `GET /api/v2/billing/lich-su` | `GET /api/v2/usage/su-kien` |
| **6** | **`GET /api/v2/billing/du-thao` · khai CHỜ BACKEND** | **`GET /api/v2/billing/du-thao` · ĐANG DÙNG** (đường **không đổi**; chỉ nhãn đổi) |

**Dòng thứ sáu là phát hiện MỚI, AG-05 chưa nêu.** Nó nói dối theo **chiều ngược lại**: đường
**đã cắm** (`HTTP 200`, đo ở §3.1) mà vẫn nằm trong bảng CHỜ. Màn `du-thao` của `admin.js` đã
đọc chính đường ấy từ G19 và ghi ngay trên màn *"Đường ĐỌC thì có"* — tức bảng khai và giao
diện **mâu thuẫn nhau**, và không ca nào bắt. Ca canh mới bắt được nó ngay lượt chạy đầu.

`trangThaiRoute()` vì thế đổi từ `1 đang dùng / 11 chờ` thành **`7 đang dùng / 5 chờ`**. Tổng
vẫn **12** nên không màn nào mất dòng. **Đã đo trước khi sửa**: `trangThaiRoute()` **không được
gọi ở đâu ngoài chính `billing.js`** (`grep -rn "trangThaiRoute"` toàn kho → chỉ `billing.js`
và một dòng trong `docs/G19_MAN_MA.md`), nên đổi con số này **không đổi hành vi màn nào**.

### 3.3 CA CANH — `thu_giao_dien/08_bang_duong_billing.spec.js` (3 ca, mới)

Đây là bản tương đương `app/thu/thu_tai_chinh.py::test_j4` đang canh `finance.js`. **Nhà ĐÚNG
của nó là `app/thu/`** — nhưng `app/thu/**` không nằm trong danh sách tệp làn này được cấp ghi,
nên ca được đặt ở `thu_giao_dien/` cho chạy được ngay lượt này. **Việc còn lại cho AG-00:**
chuyển nó về `app/thu/` nếu muốn nó chạy trong bộ Python (§9).

**Ca 01 — hai chiều, đọc tệp thật.** Rút đường từ `app/server.py` (**91 đường** ở lượt này)
rồi đối chiếu bảng khai. Hai chiều vì một bảng khai nói dối theo hai cách, và cách thứ hai
**tệ hơn**: khai ĐANG DÙNG cho đường không có ⇒ giao diện gọi đường chết rồi báo lỗi lạ cho
người dùng.

**Ca 02 — TỰ KIỂM, bộ đo phải ĐỎ được.** Đưa vào chính hai bảng sai của bản trước G20:

```
[đo] tự kiểm chiều 1: thua=1 thieu=0        ← GET /api/v2/billing/du-thao nằm trong bảng CHỜ
[đo] tự kiểm chiều 2: thua=0 thieu=5        ← đúng năm đường sai của bản cũ
[đo] tự kiểm lỗ chuỗi con: thua=0 (kỳ vọng 0)
```

Vế (c) là **đối chứng dương**: thay năm đường THẬT vào chỗ năm đường sai thì bộ đo phải XANH —
thiếu vế này thì một bộ đo "luôn đỏ" cũng qua được hai vế đầu. Vế (d) đóng **một lỗ đã biết của
bản `test_j4`**: nó so bằng **chuỗi con**, nên `POST /api/v2/platform/goi/phien-ban` khớp chuỗi
con `/api/v2/platform/goi` (đường **CÓ** thật) và bị kết luận nhầm là "đã cắm". Bộ đo ở đây
khớp **toàn phần** nên đường 404 vẫn nằm đúng ở bảng chờ.

**Ca 03 — đo bằng HTTP THẬT, đúng vai cho từng nhóm đường.** Ca 01 khớp **mã nguồn**; mã nguồn
và máy chủ đang chạy có thể lệch (route bị cổng chặn, bị RBAC chặn), nên ca 03 bắn thật:

```
[đo] ĐANG DÙNG GET /api/v2/billing → 200 · /api/v2/goi → 200 · /api/v2/dang-ky → 200
[đo] ĐANG DÙNG GET /api/v2/usage → 200 · /usage/bao-cao → 200 · /usage/su-kien → 200
[đo] ĐANG DÙNG GET /api/v2/billing/du-thao → 200
[đo] CHỜ  POST /api/v2/billing/du-thao → 404  (shopa-owner)
[đo] CHỜ  POST /api/v2/billing/usage → 404  (shopa-owner)
[đo] CHỜ  POST /api/v2/platform/goi/phien-ban → 404  (platform-owner)
[đo] CHỜ  POST /api/v2/platform/tenants/{id}/doi-goi → 404  (platform-owner)
[đo] CHỜ  POST /api/v2/platform/tenants/{id}/tam-ngung → 404  (platform-owner)
[đo] đo được 7 đường ĐANG DÙNG + 5 đường CHỜ = 12
```

**GHI RÕ RỦI RO CỐ Ý:** ca này bắn đúng method khai trong bảng, **kể cả POST**. Trên nền cô lập
của `chay.sh` thì vô hại (nền xoá khi xong, và cả năm đường POST đều 404 nên không ghi gì).
**ĐỪNG chạy bộ thử này vào CSDL đang dùng** — `playwright.config.js` đã từ chối chạy khi thiếu
`VIP_GD_GOC` đúng vì thế.

### 3.4 `admin/admin.js` — gỡ ba câu đã thành SAI sau khi sửa bảng

AG-05 ghi **ngay trên màn** rằng bảng khai của module sai đường:
`goi` ("…ghi màn này cần `GET /api/v2/billing/goi` — đo ra HTTP 404"), `dang-ky`, `muc-dung`,
cộng hai khối chú thích ở đầu nhóm. Sửa `billing.js` mà **để nguyên những câu ấy** là tạo ra
**một lời nói dối mới**: màn sẽ khai một điều về tệp kia mà tệp kia không còn đúng nữa.

Nên ba câu ấy được đổi thành *"Bảng khai của module ĐÃ KHỚP: trước G20 … đo ra HTTP 404; G20 ·
AG-02 đã sửa về …"* — giữ lại **vết đo cũ** thay vì xoá, và hai khối chú thích nói rõ bản sửa
**chỉ đổi LỜI KHAI, không đổi lời gọi**, nên không hành vi nào của màn thay đổi theo.
`node --check admin/admin.js` → **exit 0**.

---

## 4. KHOẢNG TRỐNG (b) — 20 MÀN AG-05: BẤM ĐƯỢC **VÀ** ĐỌC DỮ LIỆU THẬT

### 4.1 Vì sao đây là khoảng trống thật

`thu_giao_dien/04_nhan_va_man_dot3.spec.js` (G19) canh 12 màn đợt 3 bằng ba điều kiện:
**mở được · không lỗi console · không tràn ngang**. Ba điều kiện ấy **không nói gì** về việc màn
có đọc dữ liệu hay không — một màn dựng ra đúng cái khung rỗng, **không gọi đường nào**, vẫn qua
sạch cả ba. Đo được: `04` ca 03 in `[đo] đợt 3 khai … màn; … đã có trên menu; …` rồi **chỉ** đo
ba điều kiện trên. Mười sáu màn mới của AG-05 vì thế chưa từng được khẳng định ở bất kỳ ca nào.

### 4.2 Ba điều kiện của ca mới — `thu_giao_dien/09_man_ag05.spec.js` (5 ca, mới)

- **C1 BẤM ĐƯỢC** — có mục menu thật, **một cú bấm** mở ra màn, tiêu đề khớp tên khai.
- **C2 ĐỌC THẬT** — trong lượt mở màn có phản hồi `/api/v2/**` **2xx thật**, và **không** 5xx.
- **C3 GẮN VÀO NHAU** — DOM phải **chứng minh** nó dựng từ phản hồi ấy, theo **đúng một** trong
  hai vế: **(a)** `#man` chứa một **giá trị chỉ có thể đến từ payload** (neo), hoặc số dòng bảng
  bằng độ dài một mảng trong payload; **(b)** màn hiện ô trạng thái rỗng **NÓI RÕ LÝ DO** và
  **không bịa dòng nào**.

Neo lấy **lúc chạy** từ chính phản hồi nên **không mã cứng trước được**; ngưỡng "đủ đặc thù"
(chuỗi ≥ 4 ký tự và không phải từ chung, hoặc số ≥ 100) để `0` / `1` / `"Không"` không khớp bừa
ở mọi màn — ngưỡng thấp hơn thì ca thử xanh vô nghĩa.

**VẾ (b) KHÔNG PHẢI KẼ HỞ, và đây là chỗ dễ hiểu sai nhất:** nền cô lập **không có** đợt đối
soát, lô import, hay việc AI. Bắt những màn ấy phải "có dòng" là **bắt chúng BỊA dữ liệu** —
đúng thứ luật 1 của AG-05 cấm. Vế (b) là **ĐẠT THẬT**, với điều kiện màn **phải NÓI RA** là
chưa đo được; màn nào **im lặng** thì **HỎNG**.

### 4.3 Kết quả — 20/20 bấm được, **8 màn CÓ DỮ LIỆU**, **12 màn vào sổ CHƯA ĐO**

```
goi               CÓ DỮ LIỆU   neo: /api/v2/billing.goi.ten="Cơ bản" · .han_muc_don_thang=1000
dang-ky           CÓ DỮ LIỆU   neo: /api/v2/dang-ky.han_muc.goi_ten="Cơ bản"
muc-dung          CÓ DỮ LIỆU   neo: /api/v2/usage.trang_thai.dong.don_thang.ten="Đơn gửi hãng mỗi tháng"
canh-bao          CÓ DỮ LIỆU   neo: /api/v2/usage.trang_thai.dong.nhan_vien.ten="Tài khoản nhân viên"
lich-su           CÓ DỮ LIỆU   neo: /api/v2/usage/tinh-phi.chang[0].ten="Cơ bản"
du-thao           CÓ DỮ LIỆU   neo: /api/v2/usage/tinh-phi.nhan_phap_ly="BẢN NHÁP NỘI BỘ — KHÔNG PHẢI HOÁ ĐƠN…"
ai-thong-ke       CÓ DỮ LIỆU   neo: /api/v2/ai/thong-ke.han_muc_ai_thang=500
health            CÓ DỮ LIỆU   neo: /api/v2/suc-khoe.phien_ban_ma="0.3-SaaS" · .pham_vi="chi do tien trinh…"

[đo] tổng kết: 8 màn CÓ DỮ LIỆU · 12 màn CHƯA CÓ DỮ LIỆU (nói rõ lý do) · 0 màn HỎNG
[đo] CHƯA ĐO ĐƯỢC của lượt này: cod, dot, bang_ke, chenh_lech, phai_thu, phai_tra,
     dieu_chinh, ai, ai-goi-y, ai-canh-bao, ai-trang-thai, ai-lich-su-duyet
```

Mười hai màn ấy **không hỏng** — chúng hiện đúng ô "🕳️ CHƯA ĐO ĐƯỢC" kèm **lý do cụ thể**,
nguyên văn từ màn, ví dụ: *"Chưa có ĐỢT ĐỐI SOÁT nào, mà bảng kê là dòng CỦA MỘT ĐỢT. Đường
`GET /api/v2/doi-soat/dot/<id>/bang-ke` đã đo được HTTP 200 khi có đợt thật — ở đây thiếu DỮ
LIỆU, không phải thiếu đường."* Theo đúng luật của làn: **chúng được ghi vào CHƯA ĐO, không
tính là đạt.**

### 4.4 Ba ca còn lại của tệp `09`

- **Ca 02 — ĐỐI CHỨNG ĐƯỜNG (sàn đếm).** Ca 01 "đạt" theo hai cách rất khác nhau: 20 màn đều
  có dữ liệu, hoặc 20 màn đều rỗng. Ca này chốt sàn: ba màn `goi` / `muc-dung` / `health`
  **chắc chắn có dữ liệu** (seed sẵn) phải chứng minh được neo — đo được **13 / 39 / 6 neo**.
  Nếu không màn nào có neo thì ca thử **HỎNG**, để không ai trích lượt chạy làm bằng chứng
  "đọc dữ liệu thật" khi thực ra mọi màn đều rỗng.
- **Ca 03 — TỰ KIỂM bộ đo C3.** Trên màn `goi` (13 neo): **(a)** xoá sạch `#man` ⇒ `neo=0`,
  `trạng thái rỗng=false`; **(b)** chỉ để lại `<div class="trang-thai-rong">Không có</div>` ⇒
  `co=true ro=false` — **câu rỗng cụt KHÔNG được tính là "nói rõ lý do"**, nếu không thì màn chỉ
  cần in "Không có" là qua.
- **Ca 04 — màn NỀN TẢNG `quan-tri-goi`.** Nằm ở menu nền tảng, `shopa-owner` **không thấy**;
  đo bằng tài khoản tenant sẽ ra kết luận **SAI** về sản phẩm. Đo bằng `platform-owner`:
  `200 /api/v2/platform/goi` · **9 neo** · neo `goi[1].ten="Cơ bản"`.
- **Ca 05 — ĐỐI CHIẾU `ket-noi-jt`.** Nhiệm vụ nêu màn này trong cùng nhóm "chưa có ca E2E nào
  khẳng định bấm được và đọc dữ liệu thật". **ĐO LẠI THÌ KHÔNG ĐÚNG:**
  `05_ket_noi_jt.spec.js` đã có **ca 01** (menu thật + một cú bấm) và **ca 02** (từng con số
  trên màn đối chiếu payload thật), cộng ca 11 TỰ KIỂM về ngân sách chờ. Ca 05 ở đây **không
  viết lại** việc ấy — nó chỉ đo lại bằng chính bộ đo của tệp này ở **lượt này**: tiêu đề
  `"Kết nối J&T"`, **3 phản hồi 2xx**, **72 neo khớp payload**. Kết luận: **đã đạt, không cần
  ca mới** — và câu ấy là một **phép đo**, không phải câu chép từ báo cáo cũ.

---

## 5. KHOẢNG TRỐNG (c) — `pages/*.html`: NGUỒN DỮ LIỆU THẬT

### 5.1 Đo lại: hai kẽ hở thật, và một điều KHÔNG phải kẽ hở

`thu_giao_dien/07_trang_tinh.spec.js` (G19 · AG-06) **đã canh rất đúng** hai điều: không trang
nào còn `<script>` nội tuyến hay thuộc tính sự kiện nội tuyến (**kèm ca 05 TỰ KIỂM chứng minh
CSP chặn thật và phép đếm thấy nó**), và mỗi trang dựng được khung với bộ chọn dữ liệu có phần
tử. **Đo lại ở lượt này: 10/10 trang sạch mã nội tuyến, 10/10 trang dựng được `.khung`.** Phần
"không còn script nội tuyến" của mục (c) vì thế **đã đạt từ trước** — tệp `10` **không viết
lại**, chỉ **đo lại độc lập** ở ca 02.

Hai kẽ hở **còn lại**, cả hai đều đo được:

**KẼ 1 — "bộ chọn có phần tử" KHÔNG PHẢI là "có dữ liệu".** Tệp 07 đếm `#bang-nd tr` = 4 và ghi
`settings` là ĐẠT. Nhưng bốn dòng ấy do một **mảng viết cứng trong `pages/settings.js`** vẽ ra
— trang **không đọc ở đâu cả**. Cùng cảnh: `create-order` (**localStorage**, rỗng lúc mới mở) và
`pricing` (**bảng cước TÍNH từ công thức**). Ba trang ấy **hiện đúng như thiết kế**, nhưng gọi
chúng là "có dữ liệu" là **đọc sai phép đo**.

**KẼ 2 — danh sách trang CHÉP TAY.** Tệp 07 liệt kê mười trang thành **một mảng trong mã**.
Thêm một `pages/*.html` mới thì nó **không được canh ở cả hai điều kiện**, và bộ thử **vẫn
XANH** — không một dòng nào nói rằng có trang vừa thoát khỏi vòng canh. Đây đúng loại "chỗ hỏng
im lặng" mà dự án đang dọn.

### 5.2 Ca mới — `thu_giao_dien/10_trang_tinh_du_lieu.spec.js` (5 ca, mới)

- **Ca 01 — danh sách trang ĐỌC TỪ ĐĨA** (`readdirSync("pages")`) rồi đối chiếu bảng khai:
  **trang lạ ⇒ HỎNG**, **trang khai mà không có trên đĩa ⇒ HỎNG**. Đo được:
  `trên đĩa 10 trang: ai-import, carriers, cod, create-order, dashboard, pricing, reports,
  settings, shipments, webhooks` = `bảng khai 10 trang`.
- **Ca 02** — đo lại độc lập điều 07 đã khai: `0` script nội tuyến, `0` thuộc tính sự kiện,
  `10/10` trang có `.khung`.
- **Ca 03 — "có nguồn thật" đo bằng NEO, không đọc mã trang rồi tin.** Trong lượt mở trang, ghi
  lại **mọi phản hồi không phải html/css/js**, rồi đòi một **giá trị lấy từ chính phản hồi ấy**
  xuất hiện trên màn:

```
dashboard   nguồn 2/2 2xx · 160 neo · ← 200 /api/v2/audit, 200 /mock/shipments.json
shipments   nguồn 1/1 2xx · 203 neo · ← 200 /mock/shipments.json
cod         nguồn 1/1 2xx · 120 neo · ← 200 /mock/shipments.json
reports     nguồn 1/1 2xx · 133 neo · ← 200 /mock/shipments.json
webhooks    nguồn 1/1 2xx · 202 neo · ← 200 /mock/webhook-events.json
ai-import   nguồn 1/1 2xx ·  21 neo · ← 200 /mock/import-sample.csv
carriers    nguồn 3/3 2xx ·  32 neo · ← 200 /api/v2/hang, /tai-khoan-hang, /g09/suc-khoe-hang
[đo] 7 trang CÓ DỮ LIỆU THẬT · 3 trang CHƯA ĐO (create-order, pricing, settings)
```

- **Ca 04 — ba trang KHÔNG có nguồn: ghi vào CHƯA ĐO, không tính là đạt.** Ca này **không** hỏi
  ba trang kia có hỏng không (chúng hiện đúng thiết kế) — nó chốt rằng chúng **không được lẫn
  vào nhóm "có dữ liệu thật"**, và khẳng định **danh sách CHƯA ĐO đúng bằng bảng khai** — để
  một trang **lặng lẽ MẤT nguồn dữ liệu** (ví dụ ai đó bỏ `taiMock` khỏi `cod.js`) cũng **HỎNG**
  theo chiều ngược lại.
- **Ca 05 — TỰ KIỂM.** **(a)** không chặn gì: `shipments` có **203 neo**; **(b)** chặn
  `mock/shipments.json` (trả 404): **`2xx=0`, `neo=0`**, `#bang tr=1`; **(c)** và trang **phải
  NÓI RA** — `body` khớp `/Không tải được/`, không im lặng hiện bảng rỗng. Nếu neo vẫn "khớp"
  khi nguồn bị chặn thì phép đo đang khớp **thứ có sẵn trong HTML**, và cả tệp là công dựng chuyện.

### 5.3 Một lỗi ĐO của chính tệp này, bắt được ở lượt chạy ĐẦY ĐỦ

Chạy riêng tệp `10`: **5/5 đạt**. Chạy cả bộ: ca 04 **ĐỎ** với
*"settings: khai KHÔNG có nguồn mà đọc 1 nguồn (/api/v2/tai-khoan-hang)"*.

**Không phải sản phẩm hỏng — là bộ thu của tôi bắt nhầm.** `/api/v2/tai-khoan-hang` là lời gọi
của trang **`carriers`** mở ngay trước đó; phản hồi ấy **còn bay** và rơi vào bộ thu vừa gắn cho
trang `settings`. Chạy riêng tệp thì không thấy, vì lúc ấy **chưa có trang trước**. Đã đóng
bằng **hai** chốt, ghi lại trong mã: (1) `page.goto("about:blank")` **trước khi gắn bộ thu**;
(2) bỏ qua `/api/v2/auth/**` — đó là lời gọi **phiên**, có mặt ở mọi trang động, **không phải
nguồn dữ liệu**; tính nó là nguồn thì mọi trang đều thành "có dữ liệu". Chạy lại `09`+`10`:
**10/10 đạt**.

---

## 6. SỔ "CHƯA ĐO" CỦA LƯỢT NÀY — NÓI THẲNG

Đây là những thứ **không** được tính là đạt, kèm lý do đo được:

| Chưa đo | Lý do |
|---|---|
| 12 màn AG-05: `cod` `dot` `bang_ke` `chenh_lech` `phai_thu` `phai_tra` `dieu_chinh` `ai` `ai-goi-y` `ai-canh-bao` `ai-trang-thai` `ai-lich-su-duyet` | Nền cô lập không có đợt đối soát / lô import / việc AI ⇒ payload rỗng. Màn hiện đúng ô "CHƯA ĐO ĐƯỢC" kèm lý do; **không** chứng minh được "có dòng". Muốn đo phải seed đợt đối soát + lô import + việc AI — **việc của AG-00**. |
| 3 trang: `settings` `create-order` `pricing` | Trang **không đọc ở đâu**: mảng viết cứng trong chính tệp · localStorage rỗng lúc mới mở · bảng cước tính từ công thức. Ba trang hiện đúng thiết kế; **không** phải bằng chứng cho "mỗi trang có dữ liệu thật". |
| Thao tác GHI trên mọi màn mới | Không vẽ nút (giữ nguyên quyết định AG-05). Bốn đường ghi vẫn 404. |
| `POST /api/v2/ai/job/<id>/de-xuat` dưới tải đồng thời | Nằm ngoài phạm vi G19, làn này không đo thêm. |
| Trình duyệt khác Chromium · thiết bị cảm ứng thật · trình đọc màn hình · in thật | Đúng phạm vi `chay.sh` tự khai. |

---

## 7. HAI VIỆC NGOÀI BA KHOẢNG TRỐNG — HẬU QUẢ CỦA VIỆC CẮM 20 MÀN

Cả hai đều nằm trong `06_ban_phim.spec.js`, và cả hai **đều bị che ở nền**: ca 04 hỏng ⇒
`mode: "serial"` ⇒ ca 05–07 **không chạy**. Nên **ca 07 chưa từng được chạy** ở nền `148ecd3`.

### 7.1 Ca 04 — PHÉP ĐO hỏng, **đã sửa**

Bản cũ bấm **CỨNG 30 lượt Tab**. Lúc viết, menu có 10 mục nên 30 lượt đi hết menu rồi còn dư
~19 lượt vào trong màn. G19 · AG-05 cắm thêm 20 màn ⇒ menu còn **31 mục + Đăng xuất**; 30 lượt
Tab **không ra khỏi menu**, `vao_man=1`, ca ĐỎ. **Sản phẩm không hỏng — phép đo hỏng**: nó khoá
vào kích thước menu của một thời điểm, đúng kiểu mà đầu `04_nhan_va_man_dot3.spec.js` đã cảnh
báo. Ca 01 **cùng tệp** đã làm đúng từ đầu (`menu.length + 5`); ca 04 nay theo cùng luật:
ngân sách = **(số điểm dừng trước màn) + 30**, nên 30 lượt cuối luôn là lượt **trong màn** và
**hai ngưỡng cũ (`> 10`, `>= 15`) giữ NGUYÊN**, không bị nới. Đo được:
`31 điểm dừng trước màn + 30 lượt trong màn = 61 lượt Tab: 12 điểm dừng là điều khiển trong màn`.

**Thêm ca 04b TỰ KIỂM** — một ca thử vừa sửa mà không chứng minh được nó **còn đỏ được** là một
ca thử vừa được làm cho vừa. Ca 04b gỡ khả năng nhận tiêu điểm của **24 điều khiển trong `#man`**
(bằng `tabindex="-1"` + `disabled`, **không xoá phần tử** — chúng vẫn CÓ MẶT để phân biệt "đếm
phần tử có mặt" với "đếm thứ Tab tới được"):
`(a) nguyên vẹn: 12` → `(c) sau khi gỡ: 0`.

### 7.2 Ca 07 — LỖI SẢN PHẨM CÓ THẬT, **CHƯA SỬA** (ngoài phạm vi được cấp ghi)

```
✘ 07 — bố cục hẹp: thanh bên ĐÓNG thì không Tab vào chỗ khuất; MỞ ra thì Tab vào được
  Error: Tab dừng ở chỗ NGOÀI khung nhìn:
    [{"ai":"nav","x":-260,"y":67,"trong":false},{"ai":"nav","x":-260,"y":67,"trong":false}]
```

**Chứng minh nó KHÔNG do làn này gây ra:** `git diff -U0 -- thu_giao_dien/06_ban_phim.spec.js`
cho thấy các hunk **chỉ** rơi vào vùng ca 04 (dòng 159–186); ca 07 ở **dòng 282 trở đi KHÔNG
BỊ CHẠM**. Và chạy **một mình** ca 07 (`--grep "07 —"`) vẫn **ĐỎ** — nó không phụ thuộc ca nào
khác, chỉ bị ca 04 **che** ở nền.

**Nguyên nhân, đo được (đo trong trình duyệt thật, 375px):**

```json
{"muc":30,"nav_overflow":"auto","nav_scroll":1368,"nav_client":602,
 "nav_tabindex":null,"sb_lop":"sidebar","sb_left":"-260px","nut_menu_display":"block"}
```

Chuỗi nhân quả: **20 màn mới ⇒ `<nav class="menu-quan-tri">` có 30 mục ⇒ `scrollHeight=1368` >
`clientHeight=602` ⇒ `<nav>` thành phần tử CUỘN ĐƯỢC ⇒ Chromium cho nó nhận tiêu điểm NGẦM**
⇒ ở 375px với thanh bên đóng (`left:-260px`), **điểm dừng Tab ĐẦU TIÊN nằm ở `x=-260`, ngoài
khung nhìn** — người dùng bàn phím bấm Tab và **không thấy gì xảy ra**. `nav_tabindex` là
`null`: **không ai đặt** thuộc tính ấy, đây là hành vi ngầm của trình duyệt.

**Đây đúng là thứ ca 07 sinh ra để chặn** (đầu tệp: *"tiêu điểm có mà không thấy gì"*), và nó
là **hồi quy của G19**, không phải nợ cũ.

**Bản vá nằm ở `admin/ban_phim.js`** — hàm `dongBoTabindex()` (dòng 97–110) đã tính sẵn biến
`ngoaiKhungNhin` và đã gỡ `tabindex` của các **thẻ `<a>`**; thiếu đúng **thẻ `<nav>`**. Bản vá
là **một dòng** trong vòng lặp ấy (thêm `sb.querySelector("nav")` vào tập được gỡ). **Tệp
`admin/ban_phim.js` KHÔNG nằm trong danh sách làn này được cấp ghi** ⇒ **không sửa**, chỉ báo
cáo. Bản vá **phải đi cùng lượt** với ca 07 đang có sẵn (luật dự án: *"thêm ca canh cùng lượt
với bản vá"* — ở đây ca đã có trước, chỉ chờ bản vá).

---

## 8. LỆNH THẬT + MÃ THOÁT THẬT

Mọi phép đo dưới đây chạy trên nền **cô lập**, bind `127.0.0.1`, **không gọi ra hãng**.
`${PIPESTATUS[0]}` ghi **mã thoát của lệnh thật**, không phải của `grep`/`tail` đứng sau ống.

```sh
# (A) Bộ đo đường của billing.js — HTTP thật, nền cô lập, cổng rỗng
python3 /tmp/ag02/do_duong.py
# exit=1  (còn 1 dòng không khớp: GET /api/v2/billing/du-thao trả 200 mà khai CHỜ BACKEND)
#   sau khi sửa bảng: exit=0

# (B) Ba tệp ca mới — chạy riêng
sh thu_giao_dien/chay.sh thu_giao_dien/08_bang_duong_billing.spec.js --reporter=list
# 3 passed ; exit=0
sh thu_giao_dien/chay.sh thu_giao_dien/09_man_ag05.spec.js --reporter=list
# 5 passed ; exit=0
sh thu_giao_dien/chay.sh thu_giao_dien/10_trang_tinh_du_lieu.spec.js --reporter=list
# 5 passed ; exit=0

# (C) Ca 07 chạy MỘT MÌNH — chứng minh nó đỏ độc lập, không do làn này
sh thu_giao_dien/chay.sh thu_giao_dien/06_ban_phim.spec.js --grep "07 —" --reporter=list
# 1 failed ; exit=1

# (D) Cả bộ thử tầng 3
sh thu_giao_dien/chay.sh --reporter=list
# xem §0/§8.1

# (E) Cú pháp hai tệp mã sản phẩm đã sửa
node --check admin/billing.js ; node --check admin/admin.js
# exit=0 ; exit=0
```

### 8.1 Kết quả cả bộ thử — trước và sau

| Lượt | đạt | hỏng | không chạy | mã thoát | ghi chú |
|---|---|---|---|---|---|
| Nền `148ecd3`, môi trường **hỏng** | 0 | 7 tệp | — | 1 | `browserType.launch` — **không phải lỗi sản phẩm** (§2) |
| Nền `148ecd3`, môi trường **đã sửa** | 47 | **1** (`06` ca 04) | **3** (`06` ca 05–07) | 1 | ca 07 bị **che**, chưa từng chạy |
| **Sau làn này** | **64** | **1** (`06` ca 07) | **0** | **1** | ca đỏ duy nhất là lỗi sản phẩm ở §7.2, **cố ý không sửa** |

Lượt cuối: `sh thu_giao_dien/chay.sh --reporter=list` → `64 passed`, `1 failed`,
`0 did not run`, **`exit=1`**. Nhật ký đầy đủ ở `/tmp/ag02/luot-cuoi.log` (thư mục tạm — đọc lại
được ngay lượt này; các dòng `[đo]` của mọi ca mới nằm trong đó).

**Số ca thêm:** `08` **3** + `09` **5** + `10` **5** + `06` ca 04b **1** = **14 ca mới**
(51 → 65). **Đạt 64/65; ca đỏ duy nhất là `06` ca 07** — lỗi sản phẩm ở §7.2, **cố ý không
sửa** vì bản vá nằm ngoài danh sách tệp được cấp ghi.

### 8.2 Làn này **KHÔNG commit**

`git status --short` để lại đúng bảy dòng ở §0 (ba `M`, bốn `??`), tất cả **chưa commit** —
theo đúng cách các làn trước đã làm (xem `docs/G19_MAN_MA.md` §0). Không có thao tác nào ghi
vào `.git`, nên **không gặp `index.lock`**. **Việc commit là việc của AG-00.**

Mọi phép đo ở §8 chạy trên **cây làm việc đang có** (chưa commit); nếu AG-00 commit rồi chạy
lại, kết quả phải **giống hệt** — không phép đo nào phụ thuộc trạng thái git.

---

## 9. VIỆC CÒN LẠI — CHO AG-00 / LÀN KHÁC

1. **`admin/ban_phim.js` — một dòng (§7.2).** Thêm `<nav>` của thanh bên vào tập được gỡ
   `tabindex` khi thanh bên ở ngoài khung nhìn. Ca 07 đang đỏ và **sẽ xanh khi vá xong** —
   không cần viết ca mới.
2. **Chuyển `thu_giao_dien/08_bang_duong_billing.spec.js` về `app/thu/`** nếu muốn ca canh bảng
   khai đường chạy trong bộ Python cùng `thu_tai_chinh.py::test_j4`. Nhà đúng của nó là
   `app/thu/`; `app/thu/**` ngoài danh sách được cấp ghi của làn này.
3. **Seed để đo 12 màn còn lại của AG-05 (§6).** Cần một **đợt đối soát**, một **lô import** và
   một **việc AI** để `cod` `dot` `bang_ke` `chenh_lech` `dieu_chinh` `ai*` `ai-trang-thai`
   `ai-lich-su-duyet` rời sổ CHƯA ĐO. Hiện chúng chỉ chứng minh được "bấm được + gọi API thật",
   **chưa** chứng minh được "có dòng dữ liệu thật".
4. **Bốn đường GHI vẫn 404** — nguyên trạng từ G19, không đổi ở làn này:
   `POST /api/v2/billing/du-thao` (cần quyền `tenant.billing.lap_du_thao`, V-13909) ·
   `POST /api/v2/billing/usage` · `POST /api/v2/platform/goi/phien-ban` ·
   `POST /api/v2/platform/tenants/{id}/doi-goi` · `POST /api/v2/platform/tenants/{id}/tam-ngung`.
   **Màn đọc được thì làm, nút ghi chưa có đường thì KHÔNG vẽ ra nút** — giữ nguyên luật AG-05.
5. **Máy nào chưa có bản dựng Chromium 1194 thì tầng 3 không chạy được** (§2). Triệu chứng là
   **cả 7 tệp spec cùng chết** ở `browserType.launch`, không phải một ca hỏng — đừng đọc nhầm
   thành hồi quy.
