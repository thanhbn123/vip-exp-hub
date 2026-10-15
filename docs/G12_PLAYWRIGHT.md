# G12 — TẦNG 3 KIỂM GIAO DIỆN BẰNG PLAYWRIGHT (AG-02)

Trước đợt này dự án có ba tầng kiểm giao diện, trong đó **tầng 3 chưa tự động hoá được**: repo
cấm thư viện ngoài, nên DOM · CSS · bố cục · luồng bấm trong trình duyệt thật chỉ được nhìn
bằng mắt một lần rồi ghi lại (`docs/FRONTEND_AUTOMATION.md` mục 4, `admin/thu_frontend.md`
mục "Tầng 3"). Hệ quả: lớp mắt-thấy **không có chặn hồi quy chạy-lại-được**.

Quyết định **D-1** (anh Thành duyệt 15/10/2026): *"Đồng ý Playwright, cài riêng trong dự án."*
Tài liệu này là phần việc sinh ra từ đó.

**Đo ngày 15/10/2026, trên MacBook Pro** — `node v26.7.0` · `npm 11.19.0` ở `/opt/homebrew/bin`
(Mac mini M4 cài Node theo đường khác, xem `CLAUDE.md` §14.6 — **chưa đo** lượt nào trên Mac
mini). Mọi số trong tài liệu là số lượt chạy thật.

---

## 1. Chạy

```sh
sh thu_giao_dien/chay.sh                       # cả bộ
sh thu_giao_dien/chay.sh 02_bo_cuc.spec.js     # một tệp
```

Lần đầu trên một máy mới:

```sh
npm install
PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium
```

**Không chạy `npx playwright test` trực tiếp.** `playwright.config.js` **từ chối chạy** khi
thiếu biến `VIP_GD_GOC` — cố ý: bộ thử này tạo đơn THẬT, và chạy nó vào CSDL đang dùng là
làm bẩn dữ liệu thật. `chay.sh` là chỗ duy nhất dựng nền cô lập rồi đặt biến ấy.

### `chay.sh` làm gì

| Bước | Vì sao |
|---|---|
| `mktemp -d` làm nền, `rm -rf` trong `trap … EXIT INT TERM` | Bộ thử tạo tenant · đơn · sự kiện THẬT. Nền tạm xoá sạch kể cả khi hỏng giữa đường |
| Cổng **ngẫu nhiên 18000–19999, thử `nc -z` trước** | Cổng cố định đã làm bộ thử của dự án **báo hỏng giả** khi hai worktree chạy cùng lúc. Hỏng giả là kiểu sai tệ nhất với một cổng chặn hồi quy |
| **Poll `nc -z`** chờ máy chủ mở, kèm `kill -0` kiểm tiến trình còn sống | `sleep 3` rồi tin là đã mở thì một lượt máy chậm sẽ ra "hỏng" không liên quan gì tới sản phẩm |
| Tắt theo **đúng PID giữ lúc khởi động** | `CLAUDE.md` §16.7. **Cấm `pkill`/`killall` theo mẫu tên** — `pkill -f cat` đã giết cả Ollama và Synology Drive vì chữ "cat" nằm trong "Appli**cat**ion" |

### `thu_giao_dien/chuan_bi.py` — hai pha, cố ý

- **pha `mk`** (trước khi mở máy chủ): đặt lại mật khẩu các tài khoản demo về một giá trị biết
  trước. `khoi_tao.py` sinh mật khẩu ngẫu nhiên rồi ghi ra `TAI-KHOAN-DEMO.md`; đọc ngược file
  đó là dựng thêm một nguồn chân lý thứ hai.
- **pha `don`** (sau khi máy chủ mở): tạo 8 đơn **qua HTTP thật**, rồi **đếm lại bằng chính
  máy chủ** và dừng nếu lệch. Cố ý không `INSERT` thẳng vào bảng: dữ liệu mẫu dựng theo giả
  định của chính mình là thứ làm bộ thử ĐẠT trong khi hệ thật HỎNG.

---

## 2. Kết quả lượt chạy chính thức — 15/10/2026

```
26 passed · 1 skipped · 0 failed      (33.7s phần test; 36.2s cả lượt kể cả dựng nền)
```

| Nhóm | Tệp | Ca |
|---|---|---|
| Luồng chính | `01_luong_chinh.spec.js` | 10 |
| Bố cục / tràn ngang | `02_bo_cuc.spec.js` | 8 |
| Phân biệt quyền (D-7) | `03_quyen.spec.js` | 6 (1 bỏ qua có lý do) |
| Nhãn CHỜ BACKEND + màn đợt 3 | `04_nhan_va_man_dot3.spec.js` | 3 |

**49 phép đo tràn ngang**: 10 màn SPA × 3 bề rộng (30) · 4 tab modal chi tiết đơn @375 ·
modal tạo đơn @375 · màn đăng nhập @375 · 10 trang demo tĩnh @375 · màn `goi` × 3 bề rộng.

**Ca bị bỏ qua** (`D-7 — màn tài chính`) bỏ qua **kèm lý do in ra**, không im lặng: trên menu
hiện **không có màn tài chính nào** để đo — xem phát hiện **P-1** ở mục 5.

### Câu "0" của lượt này — kèm phạm vi, theo §12.1 luật 5

> **0 tràn ngang** trong 49 phép đo bằng `scrollWidth − clientWidth` trên `<html>` và trên mọi
> phần tử `body *` **ngoài `.cuon-ngang`**, ở **ba bề rộng 375 / 768 / 1280**, trên **Chromium
> 141.0.7390.37** (Playwright build 1194), 10 màn SPA của vai trò doanh nghiệp + 2 modal +
> màn đăng nhập + 10 trang demo tĩnh.
>
> **NGOÀI phạm vi** — câu trên không nói gì về: 4 màn vai trò nền tảng · Safari · Firefox ·
> WebKit · bề rộng < 375px · thiết bị cảm ứng thật · trình đọc màn hình · in ra giấy hoặc PDF
> thật · phần tử **nằm trong** `.cuon-ngang` (loại trừ có chủ ý — bảng rộng *phải* cuộn ngang
> trong vùng của nó) · 16 màn đợt 3 chưa cắm vào giao diện.

> **0 lỗi trang** = 0 `pageerror` và 0 `console.error` **do mã của trang gọi**, trên các màn
> ca 01/02/06/08 đi qua. **NGOÀI phạm vi:** dòng `console.error: Failed to load resource …` do
> **trình duyệt** tự ghi cho mọi phản hồi khác 2xx bị loại trừ có chủ ý — 401 ở `/auth/toi`
> khi chưa đăng nhập là đường chạy BÌNH THƯỜNG của sản phẩm, gom nó vào thì câu "0 lỗi" vừa
> sai vừa vô dụng. Lỗi tải **tệp tĩnh** không bị loại: đo riêng bằng `thuTepTinhHong`.

---

## 3. Luật viết ca ở tầng này

### 3.1 Chốt theo Ý ĐỊNH, không chốt theo trạng thái hiện tại

Dự án đã **ba lần** viết ca khoá vào trạng thái hiện tại của một việc chưa xong: một ca đòi
"route phải CHƯA có", hai ca đòi "mọi màn phải mang nhãn CHỜ BACKEND". Backend làm xong thì ca
HỎNG — ca thử đứng chắn đường tiến bộ, và người sửa sẽ học cách tắt ca thay vì tin nó.

Nên ở đây:

| Chốt SAI | Chốt ĐÚNG |
|---|---|
| "màn X phải mang nhãn CHỜ BACKEND" | "nhãn phải **khớp thực tế**: đường nào còn nhãn thì phải thật sự chưa dùng được" |
| "route `/tu-choi` phải trả 404" | "máy chủ trả 2xx ⇒ giao diện phải báo đã từ chối; trả khác ⇒ giao diện phải hiện hộp CHỜ BACKEND và khoá nút — **tuyệt đối không có kết cục thứ ba**" |
| "12 màn đợt 3 phải chưa có" | "màn nào **đã** có trên menu thì phải mở được, 0 lỗi trang, 0 tràn ngang; in ra con số khai-bao-nhiêu / có-bao-nhiêu để khoảng cách luôn nhìn thấy" |

Ca `nhãn CHỜ BACKEND khớp thực tế` còn đọc cờ `mot_phan` từ `admin/logic.js`: đường **đã có
nhưng chưa đủ** thì nhãn chờ là ĐÚNG dù máy chủ trả 200. Không có ngoại lệ này thì ca thử sẽ
ép gỡ nhãn của một đường còn thiếu thật, tức là ép giao diện tuyên bố làm được việc nó chưa
làm được.

### 3.2 Ảnh chụp màn hình KHÔNG phải phép đo

`screenshot: "only-on-failure"` — ảnh và trace để **người** xem khi đã hỏng. Không ca nào lấy
ảnh làm điều kiện đạt. Điều kiện đạt luôn là một khẳng định trên số đo: `scrollWidth −
clientWidth`, số dòng trong `#d-bang`, số lượt `POST /api/v2/don`, mã HTTP của phản hồi, danh
sách quyền trong `/auth/toi`.

### 3.3 Chạy tuần tự, không retry

`workers: 1`, `fullyParallel: false` — bộ thử dựng dữ liệu thật trên một nền dùng chung; chạy
song song thì hai ca cùng đếm bảng đơn và đạp số của nhau. `retries: 0` — một ca chập chờn
phải **lộ ra**, không được giấu bằng lượt thử lại.

---

## 4. Bằng chứng ca thử load-bearing (§12.1: kiểm thứ dùng để kiểm chứng TRƯỚC khi tin nó)

Một ca thử xanh chưa chứng minh gì. Đã **phá giao diện 6 lần có chủ ý** trên một **bản sao
riêng** (`~/code/veh4-g12-pha`, symlink `node_modules`, xoá sau khi xong — **không lần nào ghi
vào `admin/**` của worktree này**), rồi xem ca nào kêu:

| # | Phá gì | Ca kêu | Thông điệp |
|---|---|---|---|
| 1 | Gỡ `L.kiemTraDon` khỏi nút Lưu của form tạo đơn | 01 ca 04 | *form trống mà không ô nào bị đánh dấu lỗi* |
| 2 | `style="width:1700px"` cho hàng công cụ màn Đơn hàng | 02 @375px | *tài liệu lệch **1337px**; 4 phần tử tràn ngoài `.cuon-ngang`* |
| 3 | Cho `TENANT_STAFF` thêm `tenant.taichinh.ghi` (phá ma trận D-7) | 03 ca shopa-staff | *shopa-staff: taichinh.ghi* |
| 4 | Khai `GET /api/v2/hang` (đường ĐÃ CÓ) là CHỜ BACKEND, không cờ `mot_phan`, cắm nhãn vào màn Hãng | 04 ca nhãn | *GET /api/v2/hang (màn hang) trả HTTP 200 — đường ĐÃ CHẠY mà màn vẫn dán nhãn CHỜ BACKEND* |
| 5 | Gỡ chốt `duoc("tenant.don.ghi")` khỏi nút ➕ Tạo đơn | 03 ca người chỉ xem | *người chỉ xem vẫn thấy nút ➕ Tạo đơn* |
| 6 | Bỏ `<script src="finance.js">` khỏi `admin/index.html` | 04 ca module | *window.VIPFINANCE không nạp được — sai thứ tự script?* |

**6/6 bắt được.** Ca nào không bắt được thì là ca vô dụng và phải viết lại.

### 4.1 Ba lỗi của CHÍNH BỘ THỬ, lộ ra trong lúc dựng — ghi lại vì đều là hỏng im lặng

Đây là phần đáng đọc nhất của tài liệu: cả ba đều cho kết quả **"đạt"** hoặc **"bỏ qua"**,
không báo lỗi gì, trong khi không đo đúng thứ chúng nói.

1. **`moMan()` đọc nội dung của màn TRƯỚC ĐÓ.** Bản đầu chờ "menu có lớp `hien-tai`" +
   "`#tieu-de` khác rỗng". Cả hai điều kiện ấy đã đúng **ngay lúc bấm**, vì `moMan()` của
   `admin.js` gắn lớp và đặt `MAN_HIEN_TAI` **trước** khi gọi hàm dựng màn. Lộ ra vì nhãn CHỜ
   BACKEND của màn **Đơn hàng** bị ghi là của màn **Khách hàng** — lệch đúng một bậc trong
   menu. Nếu ba nhãn ấy đã đúng chỗ thì mọi phép đo tràn ngang của lượt đó cũng sai một bậc
   mà không ai thấy. **Vá:** đặt một **dấu hiệu không thể có sẵn** (`<!--G12-CHO-MAN-x-->`)
   vào `#man` rồi chờ nó bị thay — so nội dung cũ/mới thì chưa đủ, vì mở lại chính màn đang
   xem cho nội dung y hệt và phép chờ sẽ treo.
2. **Ca "từ chối đơn" TỰ BỎ QUA chính nó.** Bản đầu đếm `#ct-tu-choi` ngay sau cú bấm;
   `count()` **không chờ**, nên nó luôn thấy 0 và ca gọi `test.skip`. Một ca bỏ qua trông y
   hệt một ca không áp dụng — và không ai biết luồng từ chối chưa bao giờ được kiểm. **Vá:**
   chờ `#ct-tab` hiện, rồi `expect(count).toBe(1)` — thiếu nút là HỎNG, không phải bỏ qua.
3. **Dò mẫu lỏng trên mã định danh.** `/khac/i` để tìm lý do "Lý do khác" đã trúng
   `khach_huy` — mã đứng trước trong danh mục và **không** đòi ghi chú. Ca đo một thứ khác
   thứ nó nói. **Vá:** so bằng `x === "khac"`, và `expect` ngay nếu danh mục không còn mã đó.

Thêm một điều cùng họ, ở `04`: `billing.js` khai màn dạng **mảng** `[ma, ten, quyen]` còn
`finance.js` dạng **object** `{ma, ten}`. `String(x)` trên mảng cho ra
`"goi,Danh sách gói,tenant.billing.xem"` — một mã màn không tồn tại, nên mọi phép so với menu
sau đó vô nghĩa mà vẫn chạy trơn.

---

## 5. Phát hiện về giao diện (AG-02 **không sửa** — `admin/**` không thuộc quyền tôi)

### P-1 — **16/17 màn khai ở đợt 3 KHÔNG tồn tại trong giao diện.** Mức: **cao**

Nhiệm vụ giao viết *"12 màn mới của đợt 3 chưa được nhìn bằng mắt lượt nào"*. Đo lại thì
không phải chưa được nhìn — mà **không có gì để nhìn**:

- `admin/finance.js` · `billing.js` · `carrier_health.js` · `ai.js` · `health.js` là **logic
  thuần, 0 dòng chạm DOM**. Đo được: `grep -c "innerHTML\|document\." admin/{finance,billing,carrier_health,ai,health}.js`
  → **0 ở cả năm file**.
- `admin/admin.js` có **13 hàm dựng màn** trong `CAC_MAN`, và **không hàm nào** tham chiếu
  `VIPFINANCE` / `VIPBILLING` / `VIPCARRIERHEALTH` / `VIPAI` / `VIPHEALTH`. Đo được:
  `grep -c "VIPFINANCE\|VIPBILLING\|VIPCARRIERHEALTH\|VIPAI\|VIPHEALTH" admin/admin.js` → **0**.
- `MAN_TENANT` có 10 mục, `MAN_PLATFORM` có 4. Không mục nào là màn tài chính.
- Ca `12 màn khai ở đợt 3` in ra: **khai 17 màn, 1 đã có trên menu** (`goi` của `billing.js`
  trùng mục menu sẵn có), **16 CHƯA cắm**: 7 màn tài chính của `finance.js`; `dang-ky` ·
  `muc-dung` · `canh-bao` · `lich-su` · `du-thao` · `quan-tri-goi` của `billing.js`; và một
  màn mỗi module cho `carrier_health` · `ai` · `health` (ba module này **không khai** bảng
  màn — con số 1 màn/module là **suy ra**, không phải khai báo, và ca thử ghi rõ `suy_ra`).

Nên **17**, không phải 12. Con số 12 ở brief không khớp thứ đo được trong mã.

Hệ quả thực tế: năm module đợt 3 đang là **mã chưa ai gọi**. Tầng 1 kiểm chúng như hàm thuần
nên chúng xanh; nhưng không người dùng nào với tới được. Đây đúng dạng `CLAUDE.md` §14.6 ghi
về `archify`: *skill tự nó không biết mã có tồn tại hay không — nó vẽ đúng thứ mình mô tả, kể
cả khi thứ đó không có thật.*

**Hướng xử (việc của người giữ `admin/**`):** cắm 16 màn vào `MAN_TENANT`/`MAN_PLATFORM` +
`CAC_MAN`, mỗi màn một hàm dựng HTML gọi module tương ứng. Cắm xong thì **không cần sửa bộ
thử này** — ba ca ở `04` và ca `D-7 màn tài chính` ở `03` tự bắt đầu đo chúng.

### P-2 — **Giao diện quản trị không dùng được bằng bàn phím.** Mức: **cao** (nhưng là nợ cũ, không phải của đợt 3)

Đo bằng Chromium thật, màn Tổng quan, sau đăng nhập `shopa-owner`:

```
[chẩn đoán] menu: {"so":10,"co_href":0,"co_tabindex":0,"co_role":0}
[chẩn đoán] chuỗi Tab: body → body → body → … (15 lượt Tab, KHÔNG rời body lần nào)
[chẩn đoán] nút Đăng xuất: {"the":"A","href":false,"tabindex":false}
```

Cả 10 mục menu và liên kết Đăng xuất đều là `<a>` **không `href`, không `tabindex`, không
`role`** — theo chuẩn HTML thì không phần tử nào trong số đó nhận được tiêu điểm. Trên màn
Tổng quan, bấm Tab 15 lần **không ra khỏi `body`**: không có cách nào điều hướng giữa các màn
mà không dùng chuột. Các màn có `<input>`/`<select>`/`<button>` (Đơn hàng, Cài đặt…) thì bên
trong vẫn Tab được — vấn đề nằm ở **thanh điều hướng và nút Đăng xuất**.

**Hướng xử:** thêm `role="link" tabindex="0"` + xử `keydown` Enter/Space cho `[data-man]` và
`#nut-thoat`, hoặc đổi sang `<button>`.

**Chưa có ca thử canh điều này** — cố ý. Thêm vào là bộ thử đỏ ngay, và tôi không có quyền vá
`admin/**` để làm nó xanh. Đề nghị thêm ca **cùng lượt** với bản vá, không trước.

### P-3 — `admin/finance.js`: chú thích đầu file nói ngược với dữ liệu trong file. Mức: **vừa**

Chú thích dòng 19–20 viết: *"Toàn bộ bảy màn hình G07 hiện **CHƯA có đường API nào** trên máy
chủ — AG-00 chưa cắm route."* Nhưng `API_CHO_BACKEND_TC` trong cùng file **rỗng**
(`const API_CHO_BACKEND_TC = [];`) và `API_DANG_DUNG_TC` có **17 dòng** route đã cắm. Chú
thích là bản còn lại từ trước lượt AG-00 cắm route 15/10.

Đây đúng dạng `CLAUDE.md` §14.6: *tài liệu nói về chính hệ thống thì cũng phải nghi; việc dọn
chỉ được coi là xong khi ĐO lại.* Chú thích sai không làm hỏng gì hôm nay, nhưng nó là câu
người sửa sau sẽ tin.

### P-4 — `admin/finance.js`: `API_DANG_DUNG_TC` có 2 dòng trùng. Mức: **thấp**

`["POST", "/api/v2/tai-chinh/dieu-chinh"]` và `["POST", "/api/v2/tai-chinh/dot-thanh-toan"]`
mỗi đường xuất hiện **hai lần** (dòng 178/192 và 179/193). Vô hại về chạy (bảng chỉ dùng để
tra), nhưng nó làm con số "17 route đã cắm" ở mọi báo cáo đếm từ bảng này **cao hơn thực tế 2**
— thật ra là **15 route rời nhau**.

---

## 6. Rủi ro cố ý bỏ qua — ghi ra để không bị bỏ quên

1. **Ca `nhãn CHỜ BACKEND khớp thực tế` bắn ĐÚNG method khai trong nhãn, kể cả POST/DELETE.**
   Trên nền cô lập của `chay.sh` thì vô hại (nền xoá khi xong), nhưng nếu ai chạy bộ thử này
   vào nền thật thì nó **ghi dữ liệu**. Chốt chặn hiện có: `playwright.config.js` ném lỗi khi
   thiếu `VIP_GD_GOC`. Đây là **lời dặn có máy canh một nửa** — biến môi trường vẫn đặt tay
   được. Vá đúng hơn: cho máy chủ nhận một cờ "nền thử" và từ chối chạy bộ thử khi không có.
2. **Loại trừ `.cuon-ngang` là lỗ hổng đã biết** của phép đo tràn ngang: một bố cục hỏng mà
   lại nằm trong `.cuon-ngang` thì bộ thử này **không thấy**. Giữ loại trừ vì bảng rộng *phải*
   cuộn ngang; cái giá là vùng ấy không được canh.
3. **Chromium đã cài bằng tay** (xem mục 7) — không phải đường cài chuẩn. Nếu Playwright đổi
   bố cục thư mục trình duyệt ở bản sau, bản cài này sẽ hỏng theo cách khó đoán.
4. **`retries: 0`** nghĩa là một ca chập chờn sẽ làm cả lượt đỏ. Cố ý. Nhưng nó cũng nghĩa là
   một lượt mạng xấu có thể làm đỏ oan — chưa có lượt nào như thế trong 7 lượt chạy ngày 15/10.
5. **Chưa đo trên Mac mini M4.** `node` ở đó cài vào `~/.local` và **chỉ có trong shell tương
   tác**; script nền/`launchd` không thấy `node`. Chưa chạy lượt nào. Theo §12.1 luật 3, mọi
   số trong tài liệu này chỉ nói về **MacBook Pro**.
6. **Vai trò nền tảng (`platform-owner`, `platform-admin`) chưa được đo lượt nào ở tầng 3** —
   4 màn `MAN_PLATFORM` nằm ngoài mọi con số ở mục 2.

---

## 7. Cách Chromium được cài — và vì sao khác đường chuẩn

`PLAYWRIGHT_BROWSERS_PATH=0` đặt trình duyệt **trong `node_modules/` của repo**, không đụng gì
ở mức toàn cục (D-1: *"cài riêng trong dự án"*). **Không dùng `npm install -g`.**

Nhưng `npx playwright install chromium` **treo ở bước giải nén** trên máy này: hai lượt, mỗi
lượt **> 16 phút ở 0% CPU**, thư mục đích đứng ở 628KB. Phần tải xong trong **6 giây**
(`pw:install` ghi `total bytes: 135992119` → `download complete`); chỗ treo là
`extracting archive`. Đã tắt theo **đúng PID** (không `pkill`), rồi làm bằng tay:

```sh
curl -L -o /tmp/pwzip/chromium.zip \
  https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1194/chromium-mac-arm64.zip
unzip -q -o /tmp/pwzip/chromium.zip -d node_modules/playwright-core/.local-browsers/chromium-1194/
touch node_modules/playwright-core/.local-browsers/chromium-1194/INSTALLATION_COMPLETE

curl -L -o /tmp/pwzip/headless.zip \
  https://cdn.playwright.dev/dbazure/download/playwright/builds/chromium/1194/chromium-headless-shell-mac-arm64.zip
unzip -q -o /tmp/pwzip/headless.zip -d node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/
touch node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/INSTALLATION_COMPLETE
```

`unzip` làm xong trong **1,5 giây** — tức là không phải đĩa chậm hay quyền thiếu; chỗ treo nằm
trong bộ giải nén của chính Playwright.

Hai gói, không một: `chromium.launch()` ở chế độ headless dùng **`chromium_headless_shell`**,
một bản build riêng. Thiếu nó thì lỗi là *"Executable doesn't exist at …/chromium_headless_shell-1194/…"*,
rất dễ hiểu nhầm thành "cài hỏng".

**Nghiệm thu bản cài** — không tin `INSTALLATION_COMPLETE` mà tôi vừa `touch` (§12.1 luật 1:
thứ dùng để kiểm chứng phải độc lập với thứ được kiểm chứng):

```
$ node -e "… chromium.launch() → newPage → setContent → textContent …"
đọc được: chào
CHROMIUM CHẠY ĐƯỢC
```

Phiên bản đo được: **Chromium 141.0.7390.37**, Playwright build **1194**, `@playwright/test`
**1.56.1**.

---

## 8. Quan hệ với ba tầng sẵn có

| Tầng | Lệnh | Nằm trong `chay.sh` nào |
|---|---|---|
| 1 — logic thuần (56 ca) | `node --test thu_frontend/thu_logic.mjs` | `thu_frontend/chay.sh` |
| 2 — HTTP + tệp tĩnh (36 ca) | `python3 thu_frontend/thu_http.py` | `thu_frontend/chay.sh` |
| **3 — trình duyệt thật (27 ca)** | **`sh thu_giao_dien/chay.sh`** | **tệp này — KHÔNG gộp vào `thu_frontend/chay.sh`** |

**Cố ý không gộp.** Tầng 3 cần `node_modules` và một trình duyệt 308MB; `thu_frontend/chay.sh`
phải chạy được trên máy chưa cài gì. Gộp vào là làm hai tầng đầu **hỏng giả** ở mọi máy chưa
`npm install`. `thu_frontend/chay.sh` hiện in ra dòng *"CHƯA chạy: tầng 3"* — dòng đó nay nên
đổi thành con trỏ sang `sh thu_giao_dien/chay.sh`, nhưng `thu_frontend/**` không thuộc quyền
tôi đợt này nên **chỉ đề nghị**, không sửa.

**Thêm ca mới thì thêm ở đâu** (nối tiếp bảng mục 5 của `docs/FRONTEND_AUTOMATION.md`):

| Thứ muốn canh | Thêm vào |
|---|---|
| Một thứ chỉ thấy bằng mắt trong trình duyệt | ca mới ở `thu_giao_dien/*.spec.js` |
| Một bề rộng mới | `BE_RONG` trong `thu_giao_dien/tien_ich.js` — mọi ca bố cục tự chạy thêm |
| Một trình duyệt mới (WebKit/Firefox) | `projects` trong `playwright.config.js` + tải browser tương ứng; và **phải sửa lại mọi câu "0 …" ở mục 2** vì phạm vi đã đổi |

---

## 9. Tệp của G12

```
package.json                               devDependency duy nhất: @playwright/test 1.56.1
package-lock.json
playwright.config.js                       tuần tự · 1 worker · không retry · từ chối chạy khi thiếu VIP_GD_GOC
thu_giao_dien/chay.sh                      nền cô lập · cổng rỗi ngẫu nhiên · poll · tắt theo PID · trap dọn
thu_giao_dien/chuan_bi.py                  pha mk (mật khẩu) + pha don (8 đơn qua HTTP thật, đếm lại)
thu_giao_dien/tien_ich.js                  phép đo dùng chung — không có ca thử nào ở đây
thu_giao_dien/01_luong_chinh.spec.js       10 ca luồng chính
thu_giao_dien/02_bo_cuc.spec.js            8 ca bố cục / 46 phép đo tràn ngang
thu_giao_dien/03_quyen.spec.js             6 ca phân biệt quyền (D-7)
thu_giao_dien/04_nhan_va_man_dot3.spec.js  3 ca nhãn CHỜ BACKEND + màn đợt 3
docs/G12_PLAYWRIGHT.md                     tệp này
```

Thư mục `thu_giao_dien/_bao-cao/` và `thu_giao_dien/_ket-qua/` là **đầu ra của lượt chạy**
(báo cáo HTML, ảnh chụp khi hỏng, trace) — **không vào git**, xem bản vá `.gitignore` đề nghị
trong báo cáo bàn giao gửi AG-00.
