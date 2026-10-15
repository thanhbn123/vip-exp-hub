# G19 · AG-06 — BÀN PHÍM (V-13911) + CA E2E CHẬP CHỜN (N-G18-01) + LỖ HỔNG CSP 9 TRANG

Làn: **AG-06** · nhánh `g19-ag06-banphim` · nền: `integration/g18` @ **6e61fc1**
Người làm: AG-06 (DeepSeek trong Orca) · ngày 15/10/2026
Quyết định mở phạm vi: **AG-00** (xem mục 5 — AG-00 chốt phương án (1) và mở thêm `pages/*.js`)

---

## 0. TÓM TẮT — ba việc, ba phép đo

| Việc | Trước | Sau | Bằng chứng |
|---|---|---|---|
| **`V-13911`** giao diện quản trị không dùng được bằng bàn phím | **25/25** lượt Tab giữ nguyên `body`; cả tài liệu có **1** phần tử focusable (`#nut-menu`, lại `display:none` ở ≥768px); **11** thẻ menu + Đăng xuất là `<a>` **0 `href`/`tabindex`/`role`** | Tab đi hết **11 mục menu + Đăng xuất** đúng thứ tự; **Enter đổi màn thật**; mọi điểm dừng có `outline 2px solid rgb(124,156,245)` | `thu_giao_dien/06_ban_phim.spec.js` — 6 ca, có ca tự kiểm gỡ bản vá |
| **`N-G18-01`** ca tầng 3 chập chờn | 4/5 lượt xanh, 1/5 đỏ (`docs/QA_G18.md` §373). Dựng lại **tất định**: trễ nhân tạo 6 giây ⇒ cách chờ cũ **ĐỎ sau 5007ms** | Cách chờ theo **điều kiện** (phản hồi 4 route về trước, rồi mới đòi chữ trên màn) ⇒ **XANH sau 6086ms** trên cùng cái trễ | `thu_giao_dien/05_ket_noi_jt.spec.js` ca 08 (đã sửa) + ca 11 (tự kiểm) |
| **Lỗ hổng CSP 9 trang** `pages/*.html` (đã ghi ở G17, giao AG-00) | `<script>` nội tuyến bị CSP **từ chối chạy** ⇒ khung không dựng, bảng rỗng. Đo: `settings.html` → `#bang-nd` **0 dòng**, `.khung` **không tồn tại** | Mã chuyển ra `pages/*.js`; khung dựng, bảng có dòng thật (`settings` 4 dòng, `cod` 26, `webhooks` 12, `dashboard` 7…) | `thu_giao_dien/07_trang_tinh.spec.js` — 6 ca, có 2 ca tự kiểm |

**Không có tính năng mới nào được thêm.** Ba việc trên đều là lỗ hổng ĐÃ ĐƯỢC ĐO và ghi lại
(`BAN_GIAO.md` §6.1 · §10, `docs/QA_G18.md` §373, `docs/G17_FRONTEND_E2E.md` §CSP).

---

## 1. `V-13911` — GIAO DIỆN QUẢN TRỊ KHÔNG DÙNG ĐƯỢC BẰNG BÀN PHÍM

### 1.1 Đo trước khi sửa (lệnh thật)

```
$ VIP_GD_GOC=http://127.0.0.1:<cổng> PLAYWRIGHT_BROWSERS_PATH=0 \
    npx playwright test thu_giao_dien/zz_do.spec.js -g "vết Tab" ; echo "EXIT=$?"
[đo] {"menu_a":11,"menu_co_href":0,"nut_thoat":true,"nut_thoat_href":false,"nut_thoat_tabindex":null,"tong_focusable":1}
[đo] vết Tab:
  1. body     2. body     …     25. body
[đo] số lượt ở body: 25/25
EXIT=0
```

Đọc con số: `menu_a=11` thẻ menu, `menu_co_href=0` — **không thẻ nào vào được thứ tự Tab**
(`<a>` không `href` không phải điểm dừng Tab); `tong_focusable=1` là `#nut-menu`, mà nút ấy
`display:none` ở bề rộng ≥ 768px nên cũng không nhận được tiêu điểm ⇒ **không có gì để Tab tới**.
Trên màn "Đơn hàng" (24 điều khiển trong `#man`) thì Tab đi được trong màn nhưng **không bao giờ
tới được menu** — nghĩa là người dùng bàn phím **không đổi được màn nào**.

### 1.2 Sửa ở đâu, và vì sao không ở `admin.js` / `logic.js`

| Chỗ | Vì sao KHÔNG |
|---|---|
| `admin/admin.js::dungKhung()` (dòng 274 `menu.map(... <a data-man=…>)`) | Là tệp của **AG-05** — làn ấy đang sửa **chính hàm này** cho `V-13910`. Hai làn cùng một hàm là đúng thứ luật quyền sở hữu sinh ra để chặn |
| `admin/logic.js` | **Tầng 1 ca 53** (`thu_frontend/thu_logic.mjs:485`) cấm chuỗi `document.` · `window.` · `innerHTML` · `setTimeout` trong tệp ấy, vì nó phải là **logic thuần** để `require()` bằng Node. Luật ấy ĐÚNG và **được giữ nguyên** |
| Sửa tay trong trình duyệt | Không phải bản vá |

**Cách đã chọn (AG-00 chốt):** một **mô-đun riêng** `admin/ban_phim.js` + **một dòng**
`<script src="ban_phim.js"></script>` trong `admin/index.html`. Mô-đun **gắn hành vi SAU** khi
khung đã dựng (MutationObserver), nên **không sửa một dòng nào của `admin.js`**.

Việc nó làm, gọn:
1. `.menu-quan-tri a[data-man]` → thêm `href="#<mã màn>"`. Liên kết thật ⇒ vào thứ tự Tab,
   Enter kích hoạt theo luật trình duyệt, địa chỉ nói đúng màn đang xem (SPA đã nghe `hashchange`).
   Trình xử lý `click` của `admin.js` **không bị gỡ, không bị bọc**.
2. `#nut-thoat` (Đăng xuất) → `href="#dang-xuat"` (hash lạ: `admin.js` bỏ qua, không mở màn nào).
3. `aria-current="page"` cho mục đang xem — trạng thái "đang xem" không chỉ nói bằng màu.
4. Một thẻ `<style>` phủ `:focus-visible` cho **mọi** phần tử trong `.khung` (đặc biệt
   `#nut-thoat` nằm trong `.chan`, không khớp luật nào của `style.css`), dùng đúng token
   `#7C9CF5` của `assets/css/style.css`. CSP cho phép: `style-src 'self' 'unsafe-inline'`.
5. **Bố cục hẹp (≤768px)** — lỗ do chính bản vá đầu tiên của tôi mở ra, đo được rồi mới sửa:
   thanh bên là `position:fixed; left:-260px`, **nằm ngoài khung nhìn nhưng vẫn trong DOM**,
   nên 12 điểm dừng Tab đầu nằm ở `x=-252` — tiêu điểm có mà không thấy gì. Nay thanh bên
   ĐANG ĐÓNG thì các mục của nó mang `tabindex="-1"`; mở ra (`.mo`) thì **trả lại ngay trong
   cùng lượt bấm** (nghe thêm sự kiện `click` của nút ☰, **không** gỡ/bọc trình xử lý của
   `admin.js`). Nhận biết "bố cục hẹp" bằng chính nút ☰ (`display:none` ở bố cục rộng) —
   **không chép số 768 vào mã**, CSS đổi thì phép đo đổi theo.

### 1.3 Đo sau khi sửa — cùng phép đo, cùng lệnh

```
[đo] module: {"co":true,"phien_ban":"G19-AG06","href":11,"tong_menu":11,
              "nut_thoat_href":"#dang-xuat","focusable":13,"css":true}
[đo] vết Tab:
  1. a[data-man=tong-quan]  …  11. a[data-man=cai-dat]
  12. a#nut-thoat          13. body          14. a[data-man=tong-quan] …
[đo] Enter trên mục Đơn hàng: "Tổng quan" → "Đơn hàng"; hash=#don
[đo] tiêu điểm: a[data-man=khach]: outline 2px solid rgb(124, 156, 245)   (…14/14 điểm dừng)
```

**Không nhân đôi lượt gọi:** đo số lượt gọi `/api/v2/don` sau cú Enter = **1**
(`/api/v2/don?q=&trang_thai=&gioi_han=100`) — thêm `href` không làm màn nạp hai lần.

### 1.4 Ca canh — và ca TỰ KIỂM bộ đo

`thu_giao_dien/06_ban_phim.spec.js` (mới, 6 ca):

| Ca | Đo cái gì |
|---|---|
| 01 | 11 mục menu vào thứ tự Tab **đúng thứ tự đang hiện**, rồi tới `#nut-thoat`; số đích khác nhau ≥ menu+1 |
| 02 | Tab tới mục "Đơn hàng" rồi **Enter** ⇒ `#tieu-de` đổi, `#man` đổi nội dung, `aria-current="page"`, hash `#don` |
| 03 | **14/14** điểm dừng Tab có `outline` nhìn thấy được (`getComputedStyle`, không đo bằng cảm nhận) |
| 04 | Tab vào sâu được các điều khiển TRONG màn (12 điểm dừng là điều khiển; chỉ 1 lượt ở `body`) |
| 05 | Đăng xuất bằng bàn phím: Tab tới `#nut-thoat`, Enter ⇒ về màn đăng nhập |
| **06** | **TỰ KIỂM**: trả về một `ban_phim.js` **RỖNG** (đúng trạng thái trước bản vá) ⇒ phép đo của ca 01 và 02 **PHẢI ĐỎ**. Kết quả: `menu_co_href=0` và **15/15 lượt Tab ở `body`** — đúng câu chữ của `BAN_GIAO.md` §6.1 |
| 07 | **Bố cục hẹp 375px**: thanh bên ĐÓNG ⇒ 14 điểm dừng Tab đều **trong khung nhìn** (không Tab vào chỗ khuất); mở ☰ bằng **Enter** ⇒ đi ngược vào thanh bên được, các mục ở `x=8…16` (trong khung nhìn) |

Ca 06 là thứ trả lời câu *"gỡ phần xử lý bàn phím thì ca có đỏ không?"*: **có**, và nó đỏ đúng
ở chỗ đã ghi trong bàn giao.

**NẰM NGOÀI PHẠM VI ĐÃ ĐO** (nói rõ để không ai đọc thành "bàn phím đã xong hết"):
- Chỉ **Chromium** (bản trong `node_modules/`, `PLAYWRIGHT_BROWSERS_PATH=0`). Không Safari, không Firefox.
- **Không** trình đọc màn hình thật: `aria-current` chỉ được kiểm là **có mặt**, không kiểm NVDA/VoiceOver đọc gì.
- **Không** kiểm bẫy tiêu điểm trong hộp thoại (focus trap) và **không** kiểm việc trả tiêu điểm
  về chỗ cũ sau khi đóng hộp thoại — đó là việc của `assets/js/app.js` (`moModal`), không nằm
  trong tệp được cấp của làn này.
- **Không** thêm "bỏ qua tới nội dung chính" (skip link): đó là **tính năng mới**, mà G19 chỉ vá lỗ hổng đã đo.

---

## 2. `N-G18-01` — CA TẦNG 3 CHẬP CHỜN, ĐÃ LÀM CHO TẤT ĐỊNH

### 2.1 Nguyên nhân (đọc từ `docs/QA_G18.md` §373, rồi dựng lại)

Ca `05_ket_noi_jt.spec.js` số 08 mở lối vào sâu `admin/index.html#ket-noi-jt`. Đường ấy phải qua
`GET /api/v2/auth/toi` **rồi BA route của màn** (`g09/suc-khoe-hang` · `hang` · `tai-khoan-hang`)
mới có chữ trên `#tieu-de`. Nhưng phép chờ dùng **ngân sách 5 giây** của
`playwright.config.js` (`expect: { timeout: 5000 }`) — một con số **áp cho mọi phép đo**, không
liên quan gì tới việc sản phẩm đã làm xong hay chưa. Ngày 15/10 lượt nghiệm thu G18 chạy 6 làn
trên cùng một máy: chuỗi ấy vượt 5 giây ⇒ **ca ĐỎ dù sản phẩm ĐÚNG** (4/5 lượt xanh 36/0/1,
1 lượt đỏ 33/1/2).

### 2.2 Dựng lại TẤT ĐỊNH (không cần làm máy bận)

Trễ nhân tạo đúng ba route của màn **6 giây** (dài hơn ngân sách cũ 5 giây) bằng `page.route`:

```
[đo] khung=36ms tiêu-đề=-1ms → tieu-de quá 5 giây      (cách chờ CŨ: ĐỎ)
```

Đây là **cùng một cơ chế** với lượt đỏ của G18, nhưng không phụ thuộc máy bận.

### 2.3 Sửa: chờ ĐIỀU KIỆN, không chờ đồng hồ

Trong `thu_giao_dien/05_ket_noi_jt.spec.js`:
- Hằng `CHO_MAN = 20_000` — **ngân sách của CA**, có ghi rõ vì sao (`expect` 5 giây là ngân sách
  chung, không phải ngân sách của một phép đo phải qua 4 vòng HTTP).
- `moLoiVaoSau(page, đường)`: đăng ký `waitForResponse` cho **bốn route** TRƯỚC khi điều hướng,
  nạp một **tài liệu mới** (`about:blank` rồi `goto` — vì `goto` sang một hash khác trên cùng
  tài liệu KHÔNG nạp lại, đo được: bản đầu của ca này đã treo đủ 20 giây), chờ bốn phản hồi về,
  **rồi** mới đòi chữ trên màn. Trả về số mili-giây thật và ca in ra.
- Ca 08 vẫn giữ **đường thứ hai** vào cùng màn: đổi hash NGAY TRONG TRANG (`#don` → `#ket-noi-jt`,
  đi qua nhánh `hashchange`) — đường mà bản G17 đo, không bị bản vá làm rơi.
- `waitUntil: "networkidle"` trong ca 08 được thay bằng **chờ đúng thứ ca cần** (`#c-credential
  [data-truong]` đủ 4) — "mạng im 500ms" cũng là chờ đồng hồ.

### 2.4 Ca TỰ KIỂM (ca 11) — và số đo của cả hai cách chờ

```
[đo] cách chờ CŨ (ngân sách 5 giây) dưới trễ 6 giây → đỏ sau 5007ms
[đo] cách chờ MỚI (điều kiện, ngân sách 20000ms) dưới trễ 6 giây → xanh sau 6086ms
```

Ca 11 **bắt buộc** cách chờ cũ phải đỏ (nếu nó xanh thì phép dựng lại không chạm tới nguyên nhân
và ca 08 chỉ là một ca xanh vô nghĩa), và **bắt buộc** cách chờ mới phải mất **ít nhất bằng độ
trễ** (nhanh hơn nghĩa là nó không thật sự chờ dữ liệu).

### 2.5 Tỷ lệ sau khi sửa

Xem mục 6 (bảng `RUN1…RUN5`) — mỗi lượt là **một lượt chạy đầy đủ qua `thu_giao_dien/chay.sh`**,
nền cô lập mới, cổng ngẫu nhiên, `retries: 0`.

---

## 3. LỖ HỔNG CSP: CHÍN TRANG `pages/*.html` HIỆN RA RỖNG

### 3.1 Đo (lỗ hổng đã được ghi ở G17, việc còn lại giao AG-00)

```
$ curl -s -D - -o /dev/null http://127.0.0.1:<cổng>/pages/settings.html | grep -i content-security
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; …

[đo] settings.html: {"so_dong_bang_nd":0,"khung_dung":false,"tab_nut":3}
[đo] lỗi console: ["Refused to execute inline script because it violates the following
                    Content Security Policy directive: \"script-src 'self'\"…"]
```

`thu_frontend/thu_http.py` (tầng 2) và bộ E2E cũ **không bắt được** lỗi này: bộ E2E cũ chỉ đo
**tràn ngang** trên mười trang ấy, mà một trang rỗng thì không tràn ngang. `pages/carriers.html`
là trang duy nhất đã được sửa (G17) và chính chú thích trong nó ghi rõ CSP chặn script nội tuyến.

### 3.2 Sửa

- Chín khối `<script>` nội tuyến → **chuyển nguyên văn** sang `pages/<tên>.js` (tệp mới), HTML
  trỏ `<script src="<tên>.js"></script>`. **Không sửa logic** — chỉ đổi chỗ ở.
  **Bằng chứng "nguyên văn":** đối chiếu từng tệp bằng `difflib` giữa khối `<script>` cũ
  (`git show HEAD:pages/<tên>.html`) và tệp `.js` mới — **7/9 tệp KHỚP TỪNG KÝ TỰ** (chỉ khác
  phần đầu tệp là chú thích giải thích + dòng `VIP.dungKhung(...)`); 2 tệp còn lại khác **đúng
  ba chỗ đã định** (thêm bộ nghe uỷ nhiệm, `onclick` → `data-dong-hop`) — in ra bằng `diff`.
- Ba thuộc tính `onclick="VIP.dongModal()"` (`pages/shipments.html` 1, `pages/webhooks.html` 2 —
  nằm trong chuỗi HTML của hộp thoại): CSP chặn **cả** thuộc tính sự kiện nội tuyến, nên nút
  "Đóng" ở chân hộp thoại là **nút chết**. Thay bằng `data-dong-hop` + **một bộ nghe uỷ nhiệm**
  trong tệp `.js` của trang.
- Sửa một lỗi do chính bản vá đầu tiên của tôi gây ra (ghi lại để không ai lặp): chèn bộ nghe
  vào **dòng đầu tiên chứa chuỗi `VIP.dungKhung(`** — chuỗi ấy nằm trong **khối chú thích** ở
  đầu tệp, nên mã bị chèn vào giữa chú thích và `node --check` báo lỗi cú pháp. Đã sửa và
  **kiểm cú pháp bằng `node --check`** cho cả hai tệp.

### 3.3 Ca canh — `thu_giao_dien/07_trang_tinh.spec.js` (mới, 6 ca)

| Ca | Đo cái gì |
|---|---|
| 01 | **0** `<script>` không `src` và **0** thuộc tính sự kiện nội tuyến trên cả mười trang |
| 02 | Mỗi trang có `.khung` **và** dữ liệu do **chính mã trang** vẽ (`create-order` `#bang-nhap` và `ai-import` `#vung-buoc` là RỖNG trong HTML ⇒ số dòng > 0 là bằng chứng) |
| 03 | Hộp thoại chi tiết của `shipments` / `webhooks`: mở được, nút **Đóng bấm được** |
| 04 | Ba trang chỉ có kết quả SAU thao tác: form trống báo lỗi tại chỗ **và không gửi dữ liệu đi**; bấm "Tính cước" ⇒ bảng đầy kết quả, dòng hướng dẫn có sẵn trong HTML **biến mất**; "Dùng tệp CSV mẫu" ⇒ sang bước 2 |
| **05** | **TỰ KIỂM**: chèn một `<script>` nội tuyến vào trang đang chạy ⇒ nó **KHÔNG chạy** (CSP chặn thật) và phép đếm **thấy** nó |
| **06** | **TỰ KIỂM**: trả 404 cho `pages/settings.js` ⇒ `.khung=0`, `#bang-nd tr=0` — đúng trạng thái trước bản vá |

Số dòng thật đo được ở ca 02 (nền cô lập của `chay.sh`):
`dashboard` `#khay-kpi .the`=4 · `#bang-moi-nhat tr`=7 · `shipments` `#bang tr`=10 ·
`create-order` `#bang-nhap tr`=1 · `ai-import` `#vung-buoc .the`=1 · `webhooks` `#bang-sk tr`=12 ·
`carriers` `[data-truong]`=4 · `cod` `#bang-cod tr`=26 · `reports` `#bang-tong tr`=6 ·
`settings` `#bang-nd tr`=4.

**Bỏ qua KHÔNG phải đạt:** trang `pricing` **không** được tính ở ca 02 vì bảng cước của nó chỉ
hiện sau khi bấm (dòng có sẵn trong HTML không phải bằng chứng) — nó được đo bằng **thao tác thật**
ở ca 04. Ghi ra để không ai đọc bảng trên thành "mười trang đều đã đo bằng bảng".

---

## 4. CA NÀO CÒN BỎ QUA, VÀ VÌ SAO

| Ca bỏ qua | Vì sao | Bỏ qua có phải ĐẠT không |
|---|---|---|
| `03_quyen.spec.js` — "D-7 màn tài chính: ai xem được thì vào được…" (`test.skip` khi menu **không có màn tài chính nào**) | Menu hiện **chưa có** màn tài chính: 15 màn đợt 3 chưa được cắm vào giao diện (`V-13910`, việc của **AG-05** trong chính wave này) | **KHÔNG**. Ca tự ghi `CHƯA ĐO ĐƯỢC` kèm lý do; nó **không** được tính là đạt |

Ngoài ra **không ca nào khác bị bỏ qua** trong 5 lượt chạy ở mục 6.

---

## 5. QUYẾT ĐỊNH CỦA AG-00 (trích)

AG-00 chốt **phương án (1)** cho `V-13911`: *"cho phép thêm tệp mới `admin/ban_phim.js` + 1 dòng
`<script src>` trong `admin/index.html`"*, kèm bốn yêu cầu bắt buộc: (a) ca E2E phải chứng minh
Tab tới được menu **và đổi màn được**, (b) ca phải **đỏ được** khi gỡ phần xử lý bàn phím,
(c) **giữ nguyên** tầng 1 ca 53 (không nới luật thuần cho `logic.js`), (d) **không làm hỏng**
`admin/carrier_health.js`. AG-00 đồng thời **mở rộng phạm vi** sang `pages/*.js` (mới) cho lỗ
hổng CSP. Cả bốn yêu cầu đều được đáp: (a) ca 02, (b) ca 06, (c) `logic.js` **không bị sửa một
dòng nào** (tầng 1 ca 53 vẫn xanh), (d) `carrier_health.js` không bị chạm.

---

## 6. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA

### 6.1 Bộ tầng 3 (Playwright, Chromium thật) — 5 lượt đầy đủ

<!--BANGCHAY-->

### 6.2 Các tầng khác (chạy lại sau khi sửa)

| Bộ thử | Lệnh | Kết quả |
|---|---|---|
| Tầng 1 — logic thuần (Node) | `node --test thu_frontend/thu_logic.mjs` | `EXIT=0` · **fail 0** · 56 ca (gồm ca 53 cấm DOM trong `logic.js` — vẫn xanh) |
| Tầng 2 — HTTP + tệp tĩnh (Python) | `python3 thu_frontend/thu_http.py` | `EXIT=0` · **OK** (quét secret tệp tĩnh vẫn sạch sau khi thêm 10 tệp `.js`) |
| `thu_saas.py` (quét secret/`admin/`) | `python3 app/thu/thu_saas.py` | `EXIT=0` · **Ran 19 tests — OK** (`admin/` không có thư mục con, quét secret vẫn sạch) |

### 6.3 Cách chạy lại

```sh
cd <worktree>
ln -sfn ~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers \
        node_modules/playwright-core/.local-browsers     # nếu chưa có (xem BAN_GIAO.md §1)
sh thu_giao_dien/chay.sh                                  # cả bộ tầng 3
sh thu_giao_dien/chay.sh thu_giao_dien/06_ban_phim.spec.js        # riêng bàn phím
sh thu_giao_dien/chay.sh thu_giao_dien/05_ket_noi_jt.spec.js      # riêng ca chập chờn cũ
node --test thu_frontend/thu_logic.mjs                    # tầng 1
python3 thu_frontend/thu_http.py                          # tầng 2
```

---

## 7. TỆP ĐÃ ĐỔI

| Tệp | Việc |
|---|---|
| `admin/ban_phim.js` **(mới)** | Mô-đun bàn phím của khung quản trị (V-13911) |
| `admin/index.html` | **+1 dòng** `<script src="ban_phim.js"></script>` (không sửa gì khác) |
| `pages/*.js` **(9 tệp mới)** | Mã của chín trang, chuyển nguyên văn khỏi HTML (`ai-import`, `cod`, `create-order`, `dashboard`, `pricing`, `reports`, `settings`, `shipments`, `webhooks`) |
| `pages/*.html` (9 tệp) | `<script>` nội tuyến → `<script src>`; `onclick` → `data-dong-hop` (2 tệp) |
| `thu_giao_dien/05_ket_noi_jt.spec.js` | `N-G18-01`: chờ theo điều kiện + ca tự kiểm 11 |
| `thu_giao_dien/06_ban_phim.spec.js` **(mới)** | 6 ca canh `V-13911`, có ca tự kiểm gỡ bản vá |
| `thu_giao_dien/07_trang_tinh.spec.js` **(mới)** | 6 ca canh lỗ hổng CSP, có 2 ca tự kiểm |
| `docs/G19_BAN_PHIM.md` **(mới)** | Tài liệu này |

**KHÔNG đổi:** `admin/admin.js` · `admin/logic.js` · `admin/finance.js` · `admin/billing.js` ·
`admin/carrier_health.js` · `admin/ai.js` · `admin/health.js` · `assets/**` · `app/**` ·
`thu_giao_dien/{01,02,03,04}*.spec.js` · `thu_giao_dien/tien_ich.js` · `thu_giao_dien/chay.sh`.

---

## 8. RÀNG BUỘC ĐÃ GIỮ

- **Không gọi hãng** ở bất kỳ môi trường nào; mọi phép đo lớp HTTP chỉ trên `127.0.0.1`. Ca 07
  của `05_ket_noi_jt.spec.js` vẫn canh đúng điều đó (nó vẫn xanh sau bản vá).
- **Không** push · **không** deploy · **không** tunnel · bind `127.0.0.1`.
- **Không** mở `CHO_PHEP_LIVE`; **không** sửa căng sandbox/production trong `app/cau_hinh.py`.
- **Không** credentials thật, **không** `.env`, **không** in bí mật ra log. Ca 03 của
  `05_ket_noi_jt.spec.js` (canary rò rỉ credential) vẫn xanh.
- **Không** đoán mã trạng thái nào chưa được hãng xác minh.
- **Không** chuyển CSDL nghiệp vụ sang PostgreSQL; **không** đụng cụm `:5432`.
- **Không** xoá hàng loạt; **không** sửa tệp ngoài danh sách được cấp (và đã **hỏi AG-00** trước
  khi mở rộng sang `admin/index.html` + `pages/*.js`).
- Node trong worktree dùng lại trình duyệt của `~/code/veh4-g12-playwright` qua **một symlink**
  trong `node_modules/` (thư mục bị `.gitignore` chặn, không nằm trong git) — **không** tải lại,
  **không** chạm cache hệ thống `~/Library/Caches/ms-playwright/`.
