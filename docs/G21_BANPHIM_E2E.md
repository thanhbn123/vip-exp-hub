# G21 · AG-06 — BÀN PHÍM TRONG MÀN + E2E (CỔNG C2 CỦA AG-01)

**Nền đo:** `integration/g20` @ `a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1` (cây SẠCH, `git status
--porcelain` RỖNG trước mọi lượt chạy).
**Người làm:** AG-06 · wave G21 · 5 làn SỬA. **Vùng được ghi:** `admin/ban_phim.js`,
`thu_giao_dien/06_ban_phim.spec.js`, `docs/G21_BANPHIM_E2E.md` (mới). **Hai tệp mã bị sửa, không
tệp nào khác.**

**Lệnh duy nhất dựng lại toàn bộ số trong tài liệu này** — **số hiện hành là của LƯỢT GỘP
AG-02, xem §12**: cả tầng 3 **65 ca**, cổng C2 **8 ca**. Mục §1–§11 là **lượt gốc** (51 ca,
C2 = 7 ca) và được **giữ nguyên làm lịch sử**, không sửa lại số cũ:

```sh
sh thu_giao_dien/chay.sh                       # cả tầng 3, 65 ca (§12)
sh thu_giao_dien/chay.sh 06_ban_phim.spec.js    # cổng C2, 8 ca (§12)
```

---

## 1. NỀN ĐÃ XÁC LẬP — CA NÀO HỎNG SẴN, CA NÀO HỎNG MỚI

Đề bài yêu cầu **chạy RIÊNG từng ca** trước khi kết luận. Đã làm đúng thế: mỗi ca một lượt
`chay.sh` riêng, vì ở chế độ `serial` một ca hỏng làm **các ca sau trong cùng tệp KHÔNG HỀ CHẠY**
— và đúng vì thế mà trên nền G20 có một ca hỏng **bị che hoàn toàn** (xem `06:231` dưới đây).

| # | Ca (theo dòng trên nền) | Lệnh chạy riêng | Mã thoát | Số ca | Kết luận |
|---|---|---|---|---|---|
| 1 | `02_bo_cuc.spec.js:18` @ **1280px** | `sh thu_giao_dien/chay.sh 02_bo_cuc.spec.js` | **0** | 8 đạt · 0 hỏng · 0 bỏ qua | **KHÔNG tái hiện** |
| 2 | `06_ban_phim.spec.js:153` — ca **04** | `sh thu_giao_dien/chay.sh 06_ban_phim.spec.js` | **1** | 3 đạt · **1 hỏng** · **3 KHÔNG CHẠY** | **HỎNG SẴN** |
| 3 | `06_ban_phim.spec.js:231` — ca **07** | `sh thu_giao_dien/chay.sh 06_ban_phim.spec.js -g "07 —"` | **1** | 0 đạt · **1 hỏng** | **HỎNG SẴN — BỊ CHE** |
| 4 | `06_ban_phim.spec.js:175` — ca **05** | `... -g "05 —"` | **0** | 1 đạt | Đạt sẵn |
| 5 | `06_ban_phim.spec.js:191` — ca **06** | `... -g "06 —"` | **0** | 1 đạt | Đạt sẵn |
| 6 | `09_man_ag05.spec.js:116` | **tệp KHÔNG TỒN TẠI trên nền** | — | — | Không đo được trên nền |

Ba dòng đầu là **toàn bộ** bằng chứng của mục "hỏng sẵn / hỏng mới"; ba dòng sau là phần phải
nói ra để bảng không nói rộng hơn phạm vi.

### 1.1 Lượt chạy TRỌN BỘ trên nền — tái hiện đúng con số của AG-00

```sh
sh thu_giao_dien/chay.sh
# → === EXIT CODE THẬT = 1
#   1 failed
#     [chromium] › thu_giao_dien/06_ban_phim.spec.js:153:1 › 04 — Tab vào được các điều khiển TRONG màn, không chỉ quanh menu
#   3 did not run
#   47 passed (2.0m)
```

Trùng **đúng** bảng của AG-00 (`1 failed · 3 did not run · 47 passed`). Không có ca bỏ qua
(`0 skipped`) ở bất kỳ lượt nào trong tài liệu này.

### 1.2 `02_bo_cuc.spec.js:18` @ 1280px — **KHÔNG TÁI HIỆN ĐƯỢC**, ở CẢ HAI cây

AG-00 báo ca này hỏng trên cây AG-02. Tôi đo ba lần, ba nơi khác nhau:

| Nơi đo | Lệnh | Mã thoát | Kết quả |
|---|---|---|---|
| `a3400a8` (nền đóng băng) | `sh thu_giao_dien/chay.sh 02_bo_cuc.spec.js` | **0** | 8 đạt · 0 hỏng |
| `a3400a8` + **thay `admin/admin.js` + `admin/billing.js` của AG-02** | phép đo riêng, phục vụ hai tệp ấy qua `page.route` (xác nhận chuỗi `"Bảng khai của module ĐÃ KHỚP"` **có** hiện trên màn `goi`) | — | 30 màn @1280: **0 màn tràn** |
| **cây AG-02** (`g20-ag02-frontend`, có đủ thay đổi chưa commit của họ) | `sh thu_giao_dien/chay.sh 02_bo_cuc.spec.js --reporter=line --output=/tmp/...` | **0** | **8 passed (41.4s)** |

Thêm một dữ kiện loại trừ được giả thuyết "do cây G19 khác cây G20": **bảy tệp giao diện then chốt
GIỐNG HỆT NHAU** giữa `148ecd3` (cây AG-02) và `a3400a8` — đo bằng `git show <sha>:<tệp> | shasum`:

```
SAME  admin/admin.js   SAME  admin/billing.js   SAME  admin/ban_phim.js   SAME  pages/dashboard.html
SAME  assets/css/style.css   SAME  thu_giao_dien/tien_ich.js
SAME  thu_giao_dien/02_bo_cuc.spec.js   SAME  thu_giao_dien/06_ban_phim.spec.js
```

⇒ **Ca này KHÔNG phải một khuyết tật sản phẩm trên nền đóng băng, và cũng không tái hiện trên
chính cây AG-02.** Nó cần được AG-00 **đo lại ở đúng nơi đã thấy nó** trước khi tính vào bảng nợ;
tôi **không** kết luận nó là "hỏng giả" — tôi chỉ nói nó **không tái hiện được** bằng ba đường
đo trên, và ghi rõ ba đường đo ấy.

### 1.3 `06_ban_phim.spec.js:231` — ca 07 hỏng SẴN, **bị ca 04 che**

Đây là phát hiện quan trọng nhất của mục 1. Trên nền, lượt chạy trọn bộ in `3 did not run`, và ca
07 nằm trong số đó ⇒ **không ai thấy nó đỏ**. Chạy RIÊNG nó:

```sh
sh thu_giao_dien/chay.sh 06_ban_phim.spec.js -g "07 —"
# → === EXIT CODE THẬT = 1
#   Error: Tab dừng ở chỗ NGOÀI khung nhìn:
#     [{"ai":"nav","x":-260,"y":67,"trong":false},{"ai":"nav","x":-260,"y":67,"trong":false}]
#   1 failed
```

**NGUYÊN NHÂN GỐC — đo được, và nó là lỗi do chính bản vá G19 tự sinh ra:**

Từ Chromium 127, một **vùng cuộn** (`overflow:auto`, nội dung cao hơn khung) **TỰ vào thứ tự Tab
khi bên trong nó không còn gì vào được**. `ban_phim.js` (G19) đặt `tabindex="-1"` cho 30 mục menu
lúc thanh bên đóng — ĐÚNG — và đúng vì thế `<nav class="menu-quan-tri">` trở thành **điểm dừng Tab
ĐẦU TIÊN**, tại `x=-260` (thanh bên là `position:fixed; left:-260px`).

Đo trực tiếp trên `a3400a8`, module G19, 375×760, sau khi nạp lại trang:

```
nav: scrollHeight=1368  clientHeight=602  overflowY=auto
  1  nav.menu-quan-tri @-260,67 236x602      ← tiêu điểm có, NHÌN KHÔNG THẤY
  2  button#nut-menu @14,64
  3  body
  4  nav.menu-quan-tri @-260,67 …            ← vòng lặp 3 nhịp
```

và **đối chứng dương của chính chuỗi nhân quả ấy** — cùng cây, cùng bề rộng, **gỡ `ban_phim.js`**
(thay bằng tệp rỗng), ca 06 in ra:

```
[đo] sau khi gỡ module, điểm dừng Tab đầu tiên: nav.menu-quan-tri
```

Tức: **không có bản vá thì `<nav>` cũng là điểm dừng đầu tiên** — nó chỉ *đổi vai*: khi còn module
nó là điểm dừng **khuất**, khi mất module nó là điểm dừng **duy nhất** của thanh bên.

---

## 2. SỬA GÌ — HAI KHUYẾT TẬT SẢN PHẨM, KHÔNG PHẢI HAI CA THỬ

### 2.1 Khuyết tật A — 30 mục menu thành cái giá, và **không có lối đi tắt** (WCAG 2.4.1)

`G19 · AG-05` cắm thêm 20 màn vào menu (V-13910) ⇒ menu của `TENANT_OWNER` còn **30 mục**. Bản vá
`href` của AG-06 (G19) làm 30 mục ấy vào được thứ tự Tab — ĐÚNG — nhưng cái giá là người dùng bàn
phím phải bấm **31 lượt Tab** mới tới điều khiển ĐẦU TIÊN trong màn, và **cái giá ấy TĂNG THEO
MENU**. Đó là khuyết tật thật, không phải chỉ là phép đo hỏng.

**Sửa:** thêm **LỐI ĐI TẮT** (WCAG 2.4.1 *Bypass Blocks*) là **điểm dừng Tab ĐẦU TIÊN** của khung
— `admin/ban_phim.js::ganLoiTat()` + `diToiMan()`:

* `<a class="bo-qua-menu" href="#man" data-bo-qua="man">` chèn làm **con đầu tiên** của `.khung`.
* `position:fixed` ⇒ **nằm ngoài luồng bố cục**, không đẩy `scrollWidth` của tài liệu: bố cục ba
  bề rộng của tầng 3 **không đổi một pixel** (đo ở §4).
* Ẩn ở `top:-3rem`, hiện ở `top:0` khi có tiêu điểm — **không `transition`**, vì phép đo đọc toạ độ
  ngay sau lượt Tab và không được bắt gặp khung hình giữa đường.
* `preventDefault()` + `history.replaceState` ⇒ lối đi tắt **không ghi `#man` vào hash**: thanh địa
  chỉ vẫn nói ĐÚNG màn đang xem. Một lối tắt làm địa chỉ nói sai màn thì nó vừa tiện vừa nói dối.
* Idempotent, và **chỉ dựng khi trong khung THẬT SỰ có `#man`** — lối tắt dẫn vào chỗ trống là một
  lời hứa sai.

### 2.2 Khuyết tật B — bản vá tự sinh một điểm dừng KHUẤT

Xem §1.3. **Sửa:** `admin/ban_phim.js::dongBoTabindex()` áp **CÙNG luật** đang áp cho mục menu
sang **các vùng cuộn trong thanh bên** (`laVungCuon()`: `overflow` + có cuộn được **thật**).
Nhận biết bằng chính thứ quyết định hành vi, **không bằng tên lớp** — CSS đổi thì phép đo đổi
theo. Thuộc tính đánh dấu `data-bp-khoa` để lúc mở lại **chỉ gỡ đúng thứ tệp này đã thêm**, không
đụng `tabindex` của người viết khác.

**Không sửa một dòng nào của `admin/admin.js`** — giữ nguyên chốt của AG-00 (làn AG-02 cũng đang
sửa vùng ấy) và giữ nguyên `thu_giao_dien/chay.sh`.

---

## 3. ĐO TRƯỚC / ĐO SAU — ĐÚNG BẤT BIẾN CỦA CỔNG C2

Cùng một phép đo, cùng một nền, cùng một vai (`shopa-owner`), cùng một màn (`don`), 1280×900,
**từ ĐẦU tài liệu** (nạp lại trang — `blur()` KHÔNG đặt lại điểm xuất phát của thứ tự Tab):

| Phép đo | **TRƯỚC** — module G19 `8b893fab` | **SAU** — module G21 `21af46fa` |
|---|---|---|
| Số mục menu | 30 | 30 |
| Lối đi tắt có mặt | **0** | **1** |
| Điểm dừng Tab ĐẦU TIÊN | `a[data-man=tong-quan]` | **`a.bo-qua-menu`** |
| Điểm dừng đầu tiên NHÌN THẤY được | true | true |
| Số lượt Tab tới điểm dừng TRONG `#man` đầu tiên | 32 | 33 |
| Số lượt Tab vào `#man` trong **30 lượt đầu** | **0** | 0 |
| `Enter` trên điểm dừng đầu tiên → tiêu điểm vào `#man` | **false** | **true** |
| Số lượt Tab vào `#man` trong 30 lượt **SAU lối đi tắt** | **0** | **13** |

Đọc bảng này cho đúng, gồm cả phần **bất lợi cho bản sửa**: đường VÒNG dài thêm **đúng 1 lượt**
(32 → 33) vì lối đi tắt chen vào đầu. Cái mua được là: **13 lượt Tab vào được điều khiển trong màn
sau 2 thao tác (Tab + Enter)** thay vì **0 lượt sau 30 thao tác**. Con số 13 KHÔNG phụ thuộc menu;
con số 33 thăng theo menu.

### 3.1 Lượt chạy TRỌN BỘ sau khi sửa

```sh
sh thu_giao_dien/chay.sh
# → === EXIT CODE THẬT = 0
#   51 passed (1.7m)
#   0 failed · 0 skipped · 0 did not run
```

`47 + 3 (trước đây không chạy) + 1 (trước đây hỏng) = 51` — khớp từng ca, không thêm không bớt.

Chạy **lần thứ hai** trên cây đã khôi phục nguyên trạng (sau mọi lượt hạ cấp thử ở §6), để con số
này không phải kết quả của một lần may: `=== EXIT CODE THẬT = 0` · **`51 passed (2.3m)`** ·
`0 failed · 0 skipped · 0 did not run`. **Hai lượt độc lập, cùng một con số.**

### 3.2 Cổng C2 chạy riêng — **đúng ô "ĐÓNG" của sổ hai ô AG-01**

```sh
sh thu_giao_dien/chay.sh 06_ban_phim.spec.js
# → === EXIT CODE THẬT = 0
#   7 passed (13.4s)
```

| | Nền AG-01 đo | Sau bản sửa này |
|---|---|---|
| Bộ ba C2 `(ĐẠT, HỎNG, KHÔNG CHẠY)` | `(3, 1, 3)` | **`(7, 0, 0)`** |

`thu_qa_g20.py::SO_DO["tang3-ban-phim"] = {"nen": (3,1,3), "dong": (7,0,0)}` ⇒ **rơi đúng ô ĐÓNG**,
không phải `NUA_VOI`. Đây là ràng buộc CỨNG, xem §7.

---

## 4. TRÀN NGANG Ở 1280px — ĐO TỪNG MÀN

`02_bo_cuc.spec.js` đo `scrollWidth - clientWidth` của `<html>` cho **từng màn trên menu thật**
(không phải bảng chép tay), ở cả ba bề rộng. **30 màn**, đo trên `a3400a8`:

```
1280px · tong-quan          tài liệu lệch 0px; 0 phần tử tràn ngoài .cuon-ngang
1280px · don                tài liệu lệch 0px; 0 phần tử tràn
1280px · khach              tài liệu lệch 0px; 0 phần tử tràn
1280px · import             tài liệu lệch 0px; 0 phần tử tràn
1280px · hang               tài liệu lệch 0px; 0 phần tử tràn
1280px · ket-noi-jt         tài liệu lệch 0px; 0 phần tử tràn
1280px · webhook            tài liệu lệch 0px; 0 phần tử tràn
1280px · thanh-vien         tài liệu lệch 0px; 0 phần tử tràn
1280px · goi                tài liệu lệch 0px; 0 phần tử tràn
1280px · dang-ky            tài liệu lệch 0px; 0 phần tử tràn
1280px · muc-dung           tài liệu lệch 0px; 0 phần tử tràn
1280px · canh-bao           tài liệu lệch 0px; 0 phần tử tràn
1280px · lich-su            tài liệu lệch 0px; 0 phần tử tràn
1280px · du-thao            tài liệu lệch 0px; 0 phần tử tràn
1280px · cod                tài liệu lệch 0px; 0 phần tử tràn
1280px · dot                tài liệu lệch 0px; 0 phần tử tràn
1280px · bang_ke            tài liệu lệch 0px; 0 phần tử tràn
1280px · chenh_lech        tài liệu lệch 0px; 0 phần tử tràn
1280px · phai_thu           tài liệu lệch 0px; 0 phần tử tràn
1280px · phai_tra           tài liệu lệch 0px; 0 phần tử tràn
1280px · dieu_chinh         tài liệu lệch 0px; 0 phần tử tràn
1280px · ai                 tài liệu lệch 0px; 0 phần tử tràn
1280px · ai-goi-y           tài liệu lệch 0px; 0 phần tử tràn
1280px · ai-canh-bao        tài liệu lệch 0px; 0 phần tử tràn
1280px · ai-trang-thai      tài liệu lệch 0px; 0 phần tử tràn
1280px · ai-lich-su-duyet   tài liệu lệch 0px; 0 phần tử tràn
1280px · ai-thong-ke        tài liệu lệch 0px; 0 phần tử tràn
1280px · health             tài liệu lệch 0px; 0 phần tử tràn
1280px · nhat-ky            tài liệu lệch 0px; 0 phần tử tràn
1280px · cai-dat            tài liệu lệch 0px; 0 phần tử tràn
```

**Màn nào tràn: KHÔNG MÀN NÀO. Bao nhiêu pixel: 0px, ở cả 30 màn.** 375px và 768px cũng **0/30**.
Lượt chạy SAU khi sửa cũng **0/30 ở cả ba bề rộng** — lối đi tắt `position:fixed` không thêm một
pixel tràn nào.

**Đối chiếu chéo:** cùng phép đo ấy, chạy trên **cây AG-02**, cũng ra **0/30 màn tràn ở 1280px**
(§1.2). Vậy con số "tràn ngang ở 1280px" mà AG-00 thấy **không tái hiện được ở nơi nào tôi đo
được**; bảng trên là con số của nền đóng băng, và nó là **0**.

---

## 5. CA THỬ VIẾT LẠI — CA ĐÓ PIN GÌ, NAY KHẲNG ĐỊNH GÌ

`06_ban_phim.spec.js` ca **04** — tiêu đề **giữ nguyên từng chữ** (AG-01 đọc tiêu đề này để phân
loại log, xem §7).

### 5.1 Ca cũ pin gì — và vì sao KHÔNG được nới ngân sách Tab

Bản G19 bấm **CỨNG 30 lượt Tab** rồi đòi `> 10` điểm dừng là điều khiển trong màn. Lúc viết, menu
có **10 mục** nên 30 lượt đi hết menu rồi còn dư ~19 lượt vào trong màn. Sau khi AG-05 cắm thêm 20
màn, đo được trên `a3400a8`:

```
[đo] 30 lượt Tab: 1 điểm dừng là điều khiển trong màn · 0 lượt ở body · 30 đích khác nhau
```

Con số `30` ấy **không phải một bất biến của sản phẩm** — nó là **kích thước menu của một thời
điểm**. Nhưng sự thật đầy đủ **không chỉ có thế**, và đây là chỗ dễ sửa sai nhất:

> Cách sửa "cho ngân sách Tab co giãn theo menu" làm ca thử **càng dài menu càng dễ xanh**, trong
> khi khuyết tật WCAG 2.4.1 **càng dài menu càng nặng**. Đó là **nới điều kiện cho qua**, không
> phải viết lại theo bất biến. Tôi **không** làm thế.

### 5.2 Ca mới khẳng định gì — bốn vế, mỗi vế có ngân sách nói rõ

| Vế | Khẳng định | Ngân sách | Vì sao ngân sách ấy |
|---|---|---|---|
| **(a)** | Điểm dừng Tab ĐẦU TIÊN **là lối đi tắt**, nó **nhìn thấy được** khi giữ tiêu điểm, `Enter` đưa tiêu điểm **vào `#man`**, và hash **KHÔNG đổi** | **hằng số: 1 lượt Tab + 1 Enter** | Cái giá để vào nội dung **không được** phụ thuộc menu |
| **(b)** | Từ trong màn, 30 lượt Tab đi qua **`> 10`** điều khiển TRONG màn | hằng số 30 | **Ngưỡng `> 10` của G19 giữ NGUYÊN**, không nới |
| **(c)** | Đường VÒNG (không dùng lối tắt) **không nhốt tiêu điểm**: ra được khỏi thanh bên, 0 lượt ở `body`, `≥ 15` đích khác nhau | `so_menu + 5` = 1 + `so_menu` + 1 (Đăng xuất) + 2 dư | Vế này chỉ nói **không nhốt tiêu điểm**; nới nó **không làm ca dễ xanh hơn** vì (a) đã chặn cứng cái giá ấy |
| **(d)** | **ĐỐI CHỨNG ÂM:** gỡ khả năng nhận tiêu điểm của mọi điều khiển trong `#man` (`inert` — phần tử **vẫn còn trong DOM**) ⇒ phép đếm của (b) **PHẢI ĐỎ** | — | Không có vế này thì (b) chỉ đang đếm phần tử **CÓ MẶT** |

**Phép đếm ở (b) cũng được sửa cho ĐÚNG — và CHẶT HƠN:** bản cũ chỉ nhận
`/^input|^select|^textarea|^button/`, nên một điều khiển là `<a href>` trong màn (`a.nut`) hay một
vùng cuộn (`div.cuon-ngang`) do bàn phím tới được đều **không được tính**. Câu hỏi của ca là *"Tab
có vào được điều khiển TRONG màn không"*, nên phép đếm đúng là đếm theo `closest("#man")`.

### 5.3 Chi tiết phải giữ để AG-01 còn đọc được log

`thu_qa_g20.py::B2` đòi log **phải nhắc** chuỗi `04 — Tab vào được các điều khiển TRONG màn` **và**
phải đọc ra một con số từ dòng `lượt Tab: N điểm dừng là điều khiển trong màn`. Cả hai được giữ
nguyên; ca 04 in **đúng một** dòng khớp mẫu ấy:

```
[đo] 30 lượt Tab: 13 điểm dừng là điều khiển trong màn · 1 lượt ở body · 22 đích khác nhau
```

---

## 6. CHỨNG MINH CA THỬ **ĐO ĐƯỢC** — BỐN MỨC ĐỐI CHỨNG ÂM

Một ca thử chỉ đáng tin nếu chứng minh được nó **ĐỎ khi mã nguồn hỏng**. Bốn mức, từ thô tới tinh:

| Mức | Cách làm | Kết quả ĐO ĐƯỢC |
|---|---|---|
| **1. Gỡ cả mô-đun** | ca 06 chặn `**/admin/ban_phim.js` trả về **tệp rỗng** — đúng trạng thái trước bản vá | `{"co_module":false,"menu_co_href":0,"tong_menu":30,"nut_thoat_href":null,"lo_di_tat":0}` · 15 lượt Tab: `["body","nav.menu-quan-tri", …]` — **không tới được mục menu nào**, tiêu đề màn không đổi |
| **2. Hạ mô-đun về bản G19** | `git show a3400a8:admin/ban_phim.js > admin/ban_phim.js` (sha `8b893fab`), chạy **đặc tả MỚI** | `=== EXIT CODE THẬT = 1` · `1 failed · 3 did not run · 3 passed` · `Error: \`ban_phim.js\` không khai bộ chọn lối đi tắt` |
| **3. Đối chứng âm trong ca 04(d)** | `#man` mang `inert`: **24 điều khiển VẪN CÓ MẶT**, chỉ **0 lượt Tab vào được** (ngưỡng (b): `> 10`) | `[đo] đối chứng âm: 24 điều khiển VẪN CÓ MẶT trong #man, nhưng chỉ 0 lượt Tab vào được` |
| **4. Đối chứng dương của (b)** | Trước khi gỡ `inert` | `13 > 10` — phép đếm **có** đạt được, nên (d) không phải "đỏ vì bẩm sinh" |

Mức 2 và 3 khác nhau ở chỗ quan trọng: mức 2 chứng minh **vế (a)** đo bản vá; mức 3 chứng minh
**vế (b)** đo *thứ Tab tới được*, không đo **sự có mặt** trong DOM.

**Cây được khôi phục và KIỂM LẠI BẰNG SHA sau mỗi lần hạ cấp:** `admin/ban_phim.js` =
`21af46facc060cf0ceb17552b2ce9d94d6315fe1` trước và sau, `admin/admin.js` + `admin/billing.js`
không đổi sha sau lượt thử ở §1.2.

---

## 7. CẢNH BÁO CHO AG-00 — SỔ HAI Ô CỦA C2 LÀ MỘT RÀNG BUỘC CỨNG

`thu_qa_g20.py::SO_DO["tang3-ban-phim"]` chỉ có **hai ô**: `nen = (3,1,3)` và `dong = (7,0,0)`.
Giá trị nào **khác cả hai** bị phán `NUA_VOI` ⇒ **ĐỎ ở MỌI chế độ**, kể cả `VIP_G20_CHE_DO=gop`.

**Hệ quả trực tiếp lên làn AG-02:** bản sửa của AG-02 trong
`g20-ag02-frontend/thu_giao_dien/06_ban_phim.spec.js` **thêm một ca thứ 8** (`04b — TỰ KIỂM: điều
khiển trong màn mất khả năng nhận tiêu điểm …`). Với 8 ca, bộ ba đọc được là **`(8, 0, 0)`** —
**không rơi vào ô nào** ⇒ **cổng C2 ĐỎ VĨNH VIỄN**, dù cả 8 ca đều xanh. Đây **không phải** lỗi của
AG-02: họ không được cho biết AG-01 đã chốt ô "đóng" là `(7,0,0)` trước khi họ viết.

**Việc AG-06 đã làm để không rơi vào bẫy ấy:** bản sửa này giữ `06_ban_phim.spec.js` **ĐÚNG 7 ca**.
Đối chứng âm của ca 04 được đặt **BÊN TRONG** ca 04 (vế (d)) và đối chứng âm của lối đi tắt được
đặt **BÊN TRONG** ca 06, thay vì thêm ca thứ 8.

**Đề nghị cho AG-00 (không nằm trong vùng được ghi của tôi, `app/thu/**`):** nếu AG-02 gộp `04b`
thành ca riêng thì phải **sửa ô `dong` thành `(8,0,0)`** — sửa **sổ**, không phải bỏ ca. Cách còn
lại là gộp `04b` vào ca 04 như tôi đã làm. **AG-06 không tự sửa bộ kiểm của AG-01.**

---

## 8. `09_man_ag05.spec.js` (CA MỚI CỦA AG-02) — ĐÃ ĐO, **KHÔNG QUÁ CHẶT**

Đề bài yêu cầu nói rõ nếu ca này quá chặt. **Đo rồi: nó KHÔNG quá chặt.** Tệp **không tồn tại** trên
nền `a3400a8` (AG-02 chưa commit), nên tôi chạy nó ở **ba** cấu hình:

| Cấu hình | Lệnh | Mã thoát | Kết quả |
|---|---|---|---|
| `a3400a8` + bản sửa AG-06 | `sh thu_giao_dien/chay.sh zz_ag02_09_tam.spec.js` (bản sao tạm, **đã xoá**) | **0** | **5 passed (15.3s)** |
| `a3400a8` + bản sửa AG-06 + **`admin/admin.js` + `admin/billing.js` của AG-02** | như trên, sau khi thay tạm hai tệp | **0** | **5 passed (15.6s)** |

Log ca 01: `[đo] tổng kết: 8 màn CÓ DỮ LIỆU · 12 màn CHƯA CÓ DỮ LIỆU (nói rõ lý do) · 0 màn HỎNG`.

**Đọc kỹ vì sao nó không quá chặt — đây là chỗ đáng học:** vế "DOM gắn với phản hồi" của ca 01 có
**HAI** đường đứng vững (giá trị đặc thư của payload xuất hiện trên màn, **hoặc** số dòng bảng khớp
độ dài một mảng trong payload), cộng **đường thứ ba** cho màn chưa có dữ liệu (phải có ô trạng thái
rỗng **nói rõ lý do**, dài ≥ 20 ký tự), và tệp còn có **ca 02** làm sàn đếm ("phải có ít nhất một
màn chứng minh được dữ liệu thật") cùng **ca 03** tự kiểm bộ đo. Đó là **ba đường**, không phải một
cách ghép DOM cụ thể — đúng khuôn "bất biến, không phải hình dạng".

⇒ **Kết luận: giữ nguyên `09_man_ag05.spec.js`. Không đề xuất ca thay thế.** Việc
`09:116` hỏng trên cây AG-02 **không tái hiện được** ở cả hai cấu hình trên, nên nó thuộc cùng nhóm
với `02_bo_cuc:18` — cần AG-00 **đo lại tại chỗ** trước khi tính vào bảng nợ.

---

## 9. CHƯA ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

| # | Mục | Vì sao chưa đo |
|---|---|---|
| 1 | Gọi API hãng thật, **kể cả sandbox** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM**. Mọi phép đo HTTP ở đây chỉ chạm `127.0.0.1`, cổng do OS cấp |
| 2 | Bàn phím trên màn **NỀN TẢNG** (`MAN_PLATFORM`), bẫy tiêu điểm trong hộp thoại, bảng bên trong màn | Ca 04 chỉ đo màn **Đơn hàng** của vai trò tenant với **30** lượt Tab; các màn khác **CHƯA ĐO** |
| 3 | `did not run` ở tầng bộ chạy chung | `app/thu/thu_qa_g18.py::B_Tang3` **vẫn** chỉ khẳng định `ma == 0 · hong == 0 · dat > 0` — `bo`/`không chạy` **không vào điều kiện nào**. `app/thu/**` **ngoài vùng được ghi** của AG-06; đã báo AG-00. Cổng C2 của AG-01 **có** đếm `did not run` nên khoản nợ này **đã được canh ở một nơi** |
| 4 | Điểm dừng Tab ở **1280px** khi thanh bên **cuộn được** | `nav` là vùng cuộn ở mọi bề rộng, nhưng ở bố cục RỘNG nó **không** thành điểm dừng (bên trong còn 30 liên kết vào được) ⇒ luật "vùng cuộn" chỉ kích hoạt ở bố cục hẹp. Các vùng cuộn **bên trong `#man`** (`div.cuon-ngang`) thì **có** vào thứ tự Tab và **được tính** là điểm dừng TRONG màn (đúng) |
| 5 | Safari · Firefox · trình đọc màn hình · cảm ứng thật · in PDF thật · dữ liệu lớn · credentials thật | Ngoài phạm vi theo thiết kế (`thu_giao_dien/chay.sh` tự khai) |
| 6 | `D-4` mã trạng thái hãng · `D-8` PostgreSQL · `D-9` `city`/`area` | **Không chạm** — xem §10 |

---

## 10. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | Mọi máy chủ là `app/server.py` trên nền tạm; client chỉ mở `http://127.0.0.1:<cổng OS cấp>` | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | **0** lệnh `git push`/`ssh`/tunnel. `chay.sh` bind `127.0.0.1`, cổng thử-trước-khi-dùng | ✓ |
| 3 | Credentials thật · `.env` · in bí mật | **Không đọc `.env`.** Mật khẩu dùng là hằng **đã có sẵn trong repo** (`thu_giao_dien/tien_ich.js`) cho 9 tài khoản demo do `chuan_bi.py` đặt lại; CSDL + log nằm trong `mktemp -d` | ✓ |
| 4 | Đoán mã trạng thái hãng (`D-4`) | **Không chạm** bảng ánh xạ trạng thái; không mã nào được gán | ✓ |
| 5 | Chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | **Không chạm** ánh xạ `area` | ✓ |
| 6 | Chuyển CSDL nghiệp vụ sang PostgreSQL (`D-8`) | **0** kết nối; **0** lần chạm `:5432`; mọi nền là SQLite trong thư mục tạm | ✓ |
| 7 | Dùng Claude/mô hình khác · tự bấm duyệt sandbox | **0** lời gọi mô hình; **0** thao tác duyệt | ✓ |
| 8 | Xoá hàng loạt · sửa ngoài phạm vi | `git status --porcelain` = **ĐÚNG HAI tệp** (`M admin/ban_phim.js`, `M thu_giao_dien/06_ban_phim.spec.js`) + tài liệu mới. Bản sao tạm của `09_man_ag05.spec.js` **đã xoá** (`ls thu_giao_dien/ \| grep zz` → rỗng) | ✓ |

**Một việc hạ tầng đã làm, khai rõ:** `node_modules/playwright-core/.local-browsers` trong worktree
này là **symlink tới `chromium-1194` của worktree `g17-ag06-security`** (chính đường mà
`BAN_GIAO §1` chỉ định). `node_modules` **không được git theo dõi**; `git status` không đổi.
**KHÔNG** dùng cache hệ thống `~/Library/Caches/ms-playwright` (chromium 1148/1243 của dự án khác).

---

## 11. TỆP ĐÃ SỬA + CÁCH DỰNG LẠI

| Tệp | Trước | Sau | Nội dung |
|---|---|---|---|
| `admin/ban_phim.js` | `8b893fab…` | `21af46facc060cf0ceb17552b2ce9d94d6315fe1` | `ganLoiTat()`/`diToiMan()` (lối đi tắt) · `laVungCuon()` + `dongBoTabindex()` mở rộng cho vùng cuộn · `PHIEN_BAN = "G21-AG06"` · lộ `CHON_BO_QUA`, `diToiMan`, `laVungCuon` |
| `thu_giao_dien/06_ban_phim.spec.js` | `5516c622…` | `b52b6c21c1ebc3f9b05b83f2fe2f293cdc3fb031` | Ca 04 viết lại 4 vế · `vetTabTrongMan()` · `napLai()` · ca 06 thêm đối chứng âm cho lối đi tắt. **Vẫn ĐÚNG 7 ca** |
| `docs/G21_BANPHIM_E2E.md` | — | mới | Tài liệu này |

```sh
# dựng lại TOÀN BỘ số trong tài liệu này
sh thu_giao_dien/chay.sh                                  # 51 passed, exit 0
sh thu_giao_dien/chay.sh 06_ban_phim.spec.js               # 7 passed, exit 0
```

### 11.1 **AG-00 PHẢI COMMIT HỘ** — sandbox CHẶN ghi `.git`

AG-06 **đã thử** commit và **bị chặn**, không tự vượt (đúng luật của đề bài):

```
$ git add admin/ban_phim.js thu_giao_dien/06_ban_phim.spec.js docs/G21_BANPHIM_E2E.md
fatal: Unable to create '/Users/viporder/Projects/vip-express-hub/.git/worktrees/g21-ag06-e2e/index.lock':
       Operation not permitted
```

⇒ `HEAD` **vẫn là** `a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1`; ba tệp nằm ở **cây làm việc chưa
commit**. `git status --porcelain` trên worktree này:

```
 M admin/ban_phim.js
 M thu_giao_dien/06_ban_phim.spec.js
?? docs/G21_BANPHIM_E2E.md
```

**Mọi số trong tài liệu này đo trên ĐÚNG nội dung cây làm việc ấy** (đã kiểm bằng sha từng tệp ở
§11), nên commit của AG-00 **không** làm số nào sai đi. Thông điệp commit đề nghị:

```
AG-06 (G21) BAN PHIM TRONG MAN + E2E: loi di tat WCAG 2.4.1, bit diem dung khuat cua vung cuon
```

---

## 12. LƯỢT GỘP AG-02 (DISPATCH MỚI) — 65 CA, C2 = 8 CA

Mục §1–§11 ở trên là **lượt gốc** (51 ca · C2 = 7 ca) và được **giữ nguyên làm lịch sử**. Mục này
ghi **lượt gộp**: đưa 4 tệp spec của AG-02 (`g20-ag02-frontend`) vào cây này.

### 12.1 DỌN TIẾN TRÌNH MỒ CÔI — pid 41082, và **không có gì để giết**

AG-04 báo một tiến trình mồ côi: `app/server.py` pid **41082** trên `127.0.0.1:19449`, nghi thuộc
worktree này. **Đã kiểm chứng TRƯỚC, và KHÔNG gửi một lệnh `kill` nào** — vì nó không còn tồn tại:

| Phép kiểm | Lệnh | Kết quả |
|---|---|---|
| Tiến trình còn sống? | `kill -0 41082` | **`No such process` (ESRCH)** — hai lượt, cách nhau nhiều phút |
| Cổng còn ai nghe? | `lsof -nP -iTCP:19449 -sTCP:LISTEN` | **0 dòng** |
| Cổng còn ai nghe? (chéo) | `netstat -an -p tcp \| grep -c 19449` | **0** |
| Cổng còn trả lời? | `curl -m 3 http://127.0.0.1:19449/` | **`code=000`** |
| Có tiến trình nào của cây này? | `pgrep -fl g21-ag06-e2e` | **rỗng (`rc=1`)** |
| `cwd` của MỌI `app/server.py` đang sống | `lsof -a -p <pid> -d cwd -Fn` | chỉ `g21-ag04-gioihan` và `g21-ag05-chotcay` — **không có cây này** |

**Công cụ quan sát đã được chứng minh là KHÔNG bị chặn im lặng** — đây là phần quan trọng nhất của
bảng trên: cùng lúc ấy `lsof -nP -iTCP -sTCP:LISTEN` liệt kê được **20+** tiến trình/cổng thật của
máy (rapportd, ControlCenter, FinderSync, node, Python…) và `netstat` thấy `127.0.0.1:52868` /
`52891`. Nên "0 dòng cho 19449" là **kết quả đo**, không phải lỗi quyền bị đọc thành "sạch".

⇒ **Chủ sở hữu của 41082 không thể xác minh** vì PID đã biến mất trước lượt kiểm tra này. Dải cổng
`19449` **nằm trong dải `18000–19999`** mà `chay.sh` dùng để chọn cổng, nên nhiều khả năng nó
**chính là** một `app/server.py` của lượt chạy trước bị mồ côi. Nhưng "nhiều khả năng" **không
phải** xác minh, nên không có lệnh đóng nào được gửi — đúng luật *xác minh TRƯỚC khi đóng*, và
đúng bài học `pkill` theo khuôn đã giết nhầm tiến trình của người khác.

### 12.2 GIA CỐ PHẦN DỌN CỦA `chay.sh` — CHỐNG MỒ CÔI TÁI DIỄN

Đây là **nguyên nhân gốc** khả dĩ của một tiến trình mồ côi: bản cũ `kill "$PID"; sleep 1` **tin**
là đã chết mà không hề kiểm, và `trap` **không bắt `HUP`** nên đóng terminal là mất luôn đường
dọn. Đã sửa **chỉ phần dọn tiến trình** (đúng vùng được ghi):

| Trước | Sau |
|---|---|
| `sleep 1` rồi tin là đã chết | chờ tới **5 giây**, `kill -0` sau mỗi 0,2s, thoát vòng khi chết **THẬT** |
| không có bước mạnh tay | còn sống ⇒ **XÁC MINH `ps -o comm=` vẫn là Python** rồi mới `kill -9`; tên khác thì **KHÔNG đóng**, chỉ cảnh báo (đề phòng PID được cấp lại) |
| im lặng nếu vẫn còn sống | in `CẢNH BÁO: pid … VẪN SỐNG sau khi dọn` ra `stderr` |
| `trap don_dep EXIT INT TERM` | thêm **`HUP`**; `INT/TERM/HUP` đi qua `exit` để trap `EXIT` dọn |
| — | **KHÔNG** `pkill` / **KHÔNG** khớp mẫu tên ở bất kỳ đâu (giữ nguyên luật §16.7) |

Kiểm chứng sau khi sửa: `sh -n thu_giao_dien/chay.sh` **OK** ·
`sh thu_giao_dien/chay.sh 06_ban_phim.spec.js -g "05 —"` → **1 passed, mã thoát 0** · sau lượt
chạy: **0** `app/server.py` thuộc cây này · **0** thư mục nền tạm còn lại.

### 12.3 GỘP 4 TỆP SPEC CỦA AG-02 → 65 CA

| Tệp | Nguồn | Trước | Sau | Cách gộp |
|---|---|---|---|---|
| `08_bang_duong_billing.spec.js` | AG-02 | không có | **3 ca** | chép nguyên bản (sha `f1546ad5…` khớp nguồn) |
| `09_man_ag05.spec.js` | AG-02 | không có | **5 ca** | chép nguyên bản (sha `81212608…` khớp nguồn) |
| `10_trang_tinh_du_lieu.spec.js` | AG-02 | không có | **5 ca** | chép nguyên bản (sha `94859a07…` khớp nguồn) |
| `06_ban_phim.spec.js` | AG-02 | **7 ca** | **8 ca** | thêm ca `04b` — xem §12.4 |
| `tien_ich.js` · `chuan_bi.py` · thân `chay.sh` | AG-02 | — | — | **giống hệt từng byte** ⇒ không phải gộp |

`3 + 5 + 5 + 1 = 14` ca mới; `51 + 14 = 65`. **Không ca nào bị xoá.**

### 12.4 C2 TỪ 7 LÊN 8 — ĐÚNG DÒNG DANH TÍNH, VÀ MỘT CHỖ **PHẢI VIẾT LẠI**

Ca mới **`04b`** nằm **trong `06_ban_phim.spec.js`** — tệp **chính là cổng C2** — và nó đo bằng
**Tab thật** (`vetTab`/`vetTabTrongMan` + `document.activeElement`), **không** đo bằng thuộc tính.
⇒ **Nó THUỘC C2**, không phải ca khác bị đếm nhầm. Bộ ba C2 đọc được là **`(8, 0, 0)`**, và chạy
riêng cổng C2 ra **`8 passed`, mã thoát 0**.

**Bảng "ca nào thuộc C2" — đủ 8, không thừa không thiếu.** C2 là **cổng bàn phím**, chạy bằng
`sh thu_giao_dien/chay.sh 06_ban_phim.spec.js`; một ca thuộc C2 khi và chỉ khi nó **đo bằng bàn
phím thật** (`document.activeElement` sau từng lượt `Tab`/`Enter` thật), chứ không đọc thuộc tính:

| # | Ca (dòng trong `06_ban_phim.spec.js`) | Đo bằng gì | Thuộc C2 |
|---|---|---|---|
| 1 | `01` — Tab đi hết menu theo ĐÚNG thứ tự, rồi tới Đăng xuất (115) | `vetTab` + `activeElement` | ✓ |
| 2 | `02` — Tab tới mục menu rồi Enter: màn ĐỔI THẬT (145) | `Tab` + `Enter` thật | ✓ |
| 3 | `03` — mỗi điểm dừng Tab đều có dấu hiệu tiêu điểm nhìn thấy được (175) | `getComputedStyle(outline)` của phần tử đang giữ tiêu điểm | ✓ |
| 4 | `04` — Tab vào được điều khiển TRONG màn, không chỉ quanh menu (215) | `vetTabTrongMan` + `inert` | ✓ |
| 5 | **`04b`** — TỰ KIỂM: điều khiển trong màn mất tiêu điểm ⇒ phép đếm của ca 04 ĐỎ (325) | `vetTabTrongMan` + gỡ `tabindex`/`disabled` | ✓ **(mới)** |
| 6 | `05` — Đăng xuất bấm được bằng bàn phím (374) | `focus()` + `Enter` thật | ✓ |
| 7 | `06` — TỰ KIỂM: gỡ `ban_phim.js` ⇒ Tab/Enter hỏng (390) | chặn `ban_phim.js` rồi đo lại `Tab` | ✓ |
| 8 | `07` — bố cục hẹp: thanh bên ĐÓNG/MỞ và thứ tự Tab (454) | `Tab` thật ở 375px | ✓ |

Ba tệp mới `08`/`09`/`10` **KHÔNG** thuộc C2 — chúng canh **bảng khai đường billing**, **20 màn
AG-05**, và **nguồn dữ liệu của `pages/*.html`**; chúng vào tầng 3 chung (65 ca) chứ không vào cổng
C2 (8 ca). Đó là lý do hai con số **65** và **8** cùng tồn tại và không mâu thuẫn.

**Nhưng nó KHÔNG được gộp nguyên bản — và đây là chỗ phải đọc kỹ.** Bản AG-02 tự kiểm phép đếm
`/^input|^select|^textarea|^button/` — **phép đếm THEO TÊN THẺ của ca 04 BẢN CŨ**, đúng thứ mà ca
04 ở đây đã **thay thế** bằng `vetTabTrongMan()` (`closest("#man")`) vì nó đếm thiếu `<a href>` và
vùng cuộn (xem khối chú thích đầu ca 04). Gộp nguyên bản thì `04b` sẽ tự kiểm **một phép đếm không
còn tồn tại ở đâu trong bộ** — một **ca giả**: xanh vĩnh viễn mà không canh gì. Nên ca được viết
lại về **đúng phép đếm đang chạy** (vế (b) của ca 04), **giữ nguyên tên, mục đích, vị trí**; khối
chú thích trong tệp ghi rõ việc này để lượt sau không "sửa lại cho giống bản gốc".

**Đối chứng âm — đo thật, `-g "04b"`, mã thoát 0:**

```
[đo] tự kiểm (a) nguyên vẹn: 13 điểm dừng là điều khiển TRONG màn
[đo] tự kiểm (b) gỡ tiêu điểm của 24 điều khiển trong #man
[đo] tự kiểm (c) sau khi gỡ: 1 điểm dừng là điều khiển trong màn (24 điều khiển VẪN CÓ MẶT trong DOM)
```

Đọc ba dòng ấy: **13 → 1** điểm dừng, trong khi **24 phần tử vẫn còn nguyên trong DOM**. Nếu phép
đếm chỉ đếm sự **có mặt** thì nó vẫn ra 13 ⇒ ca 04 **ĐỎ**. Đó là bằng chứng ca `04b` **đo được**,
không phải ca trang trí. `04b` khác ca 04 vế (d) ở **cơ chế gỡ** — `tabindex="-1"` + `disabled`
cho **từng phần tử**, so với `inert` trên **cả `#man`** — nên hai đường độc lập, không phải bản sao.

### 12.5 KẾT QUẢ CHẠY TRỌN BỘ — **65 ca, và MỘT ca hỏng vì một tệp NGOÀI vùng được ghi**

```sh
sh thu_giao_dien/chay.sh
# → === EXIT CODE THẬT = 1
#   1 failed · 2 did not run · 62 passed (2.0m)
#   failed: thu_giao_dien/08_bang_duong_billing.spec.js:114 · ca 01
```

**Nguyên nhân gốc — đo được, không phải suy đoán:** ca 01 của AG-02 đối chiếu bảng khai trong
`admin/billing.js` với `app/server.py` ở **cả hai chiều**, và nó báo:

```
Error: billing.js khai CHỜ BACKEND cho đường ĐÃ CẮM
+ "GET /api/v2/billing/du-thao — ĐÃ cắm trong server.py mà vẫn khai CHỜ BACKEND"
```

Đối chiếu hai cây: `app/server.py` **GIỐNG HỆT** (sha `31521ab8…` ở cả hai), còn `admin/billing.js`
**KHÁC** — AG-02 **đã sửa tệp ấy** (sha `00e8d4cd…`, cây này còn bản G19 `abf62f42…`).

**Phép đo quyết định, làm TẠI CHỖ và có hoàn tác:** tạm hoán `admin/billing.js` của AG-02 vào cây
này, chạy riêng ca 08 → **`3 passed`, mã thoát 0**; rồi **khôi phục ngay** và **xác minh bằng sha**
(`abf62f421f7c9606bc8d8ac2f4b15c1a49730412a24539cb8aca5a75d3f88505` trước **và** sau — khớp).
⇒ Cây này **không** giữ thay đổi nào của `admin/billing.js`; con số `3 passed` chỉ là **phép đo**.

**Việc còn lại, và vì sao AG-06 không tự làm:** `admin/billing.js` **KHÔNG nằm trong vùng được ghi**
của lượt này (`admin/ban_phim.js` · `admin/admin.js` · `thu_giao_dien/*.spec.js` ·
`thu_giao_dien/chay.sh` · `app/thu/thu_g21_e2e.py` · `docs/G21_BANPHIM_E2E.md`). Đã **hỏi
coordinator** và **không tự vượt**. Hai đường đóng, chọn một:

1. **Cho phép gộp `admin/billing.js` của AG-02** vào cây này ⇒ chạy lại `sh thu_giao_dien/chay.sh`
   ⇒ kỳ vọng **65 passed, mã thoát 0** (đã đo được đúng bằng phép hoán đổi ở trên).
2. **AG-00 gộp hộ** `admin/billing.js` rồi AG-06 chạy lại.

Cho tới lúc ấy, con số trung thực của lượt này là **`62 đạt · 1 hỏng · 2 không chạy`** — **không**
phải 65 đạt. Hai ca "không chạy" là **hệ quả của `serial`** trong `08`: ca 01 hỏng nên ca 02 và 03
của **cùng tệp ấy** bị chặn — đúng cái bẫy đã ghi ở §1 (một ca hỏng **che** các ca sau).

### 12.6 TRẠNG THÁI CÂY SAU LƯỢT GỘP

```
HEAD = 0d55255   (AG-00 đã commit hộ 3 tệp của lượt gốc)

 M thu_giao_dien/06_ban_phim.spec.js      ← thêm ca 04b
 M thu_giao_dien/chay.sh                  ← gia cố phần dọn tiến trình (§12.2)
?? thu_giao_dien/08_bang_duong_billing.spec.js
?? thu_giao_dien/09_man_ag05.spec.js
?? thu_giao_dien/10_trang_tinh_du_lieu.spec.js
```

`app/server.py`, `admin/billing.js`, `admin/admin.js`, `admin/ban_phim.js` **không đổi** trong lượt
này (phép hoán ở §12.5 đã được hoàn tác và xác minh bằng sha). **AG-00 cần commit hộ 5 tệp trên**
— sandbox vẫn chặn ghi `.git`, AG-06 **không tự vượt**. Thông điệp commit đề nghị:

```
AG-06 (G21) GOP AG-02: 65 ca (C2 = 8, ca 04b tu kiem), gia co don tien trinh chay.sh
```
