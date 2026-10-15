# G19 · AG-05 — MÀN QUẢN TRỊ KHÔNG TỒN TẠI (V-13910)

**Làn:** `g19-ag05-manma` · **Nền:** `integration/g18` @ `6e61fc1` (`HEAD` của worktree = `6e61fc1`)
· **Ngày đo:** 16/10/2026 · **Người đo:** AG-05

**Tệp đã ghi (đúng danh sách được cấp):**

| Tệp | Trước | Sau | Ghi chú |
|---|---|---|---|
| `admin/admin.js` | `fdb7230…cd35` · 1.871 dòng | `ae20216…9c9f` · 2.814 dòng | `+950 / −7` |
| `admin/billing.js` | `…` → `abf62f4…8505` | không đổi dòng mã | **CHỈ thay khối chú thích** (`+15 / −1`); 0 dòng mã thi hành đổi |
| `docs/G19_MAN_MA.md` | (mới) | `e0e8395…bb2d` | tài liệu này |

`git status --short` → `M admin/admin.js`, `M admin/billing.js`, `?? docs/G19_MAN_MA.md`.
**Không** chạm `pages/*.html`, `admin/logic.js`, `admin/ai.js`, `admin/carrier_health.js`,
`admin/finance.js`, `admin/health.js`, `thu_giao_dien/`, `app/**`.
(Căn Chromium ghép tạm nằm trong `node_modules/` — `.gitignore` dòng 29 chặn, **không** vào bản giao.)

---

## 0. TÓM TẮT

Đo được: **16/17 màn khai ở đợt 3 không có đường vào** — khớp `BAN_GIAO.md` §6.1 và V-13910.
Bốn module `finance/billing/ai/health.js` bị `admin.js` tham chiếu **0 lần** (đo bằng mã, đã bỏ
chú thích và chuỗi). Nguyên nhân gốc **không phải** thiếu mã nghiệp vụ: cả bốn module đều xuất
đủ hàm dựng màn, và **mọi đường HTTP chúng cần đều đã có thật** — đo bằng HTTP thật, không đọc
mã rồi đoán. Thiếu đúng một thứ: **không ai gọi chúng**.

Đã cắm **20 màn** vào menu + bảng điều phối, mỗi màn đọc **đường HTTP đã đo là có thật**, mỗi
màn có hộp "Nguồn số liệu" nói rõ đường nào đã dùng. Sau khi cắm: **15/15 màn tự khai SỐNG**,
tầng 3 **37 ca đạt / 0 hỏng / 0 bỏ qua** (trước: 3 ca đạt — vì 14 màn kia chưa có gì để đo).

Bắt được **một XANH GIẢ** mà cả bộ đếm của tầng 3 lẫn bộ đo tĩnh của tôi đều mắc: mã màn `goi`
của `billing.js` **trùng tên** với màn `goi` sẵn có của `admin.js`, nên bộ đếm tưởng màn của
`billing.js` đã được cắm. Số đúng là **1 SỐNG / 16 CHẾT**, không phải 2/15. §2.5.

Bắt được **một bảng khai sai đường**: `admin/billing.js → API_CHO_BACKEND` trỏ 5 đường
`/api/v2/billing/{goi,dang-ky,muc-dung,canh-bao,lich-su}` — **cả 5 đều HTTP 404**; chức năng ấy
nằm ở `/api/v2/goi`, `/api/v2/dang-ky`, `/api/v2/usage…`. `billing.js` **không có ca thử nào
canh bảng này** (đo: `grep -rn "billing.js" app/thu/*.py` → **0 dòng**), trong khi `finance.js`
thì có (`app/thu/thu_tai_chinh.py::test_j4`). Đó là lý do bảng sai ấy sống sót. §5 mục 3.

---

## 1. PHẠM VI — CÁI ĐÃ ĐO VÀ CÁI NẰM NGOÀI

**Đã đo (có lệnh + mã thoát thật):** đường vào của từng màn; mã HTTP thật của từng đường;
hình dạng JSON thật của từng payload; số dòng DOM so với số dòng API trong cùng một phiên;
tràn ngang ở 375/768/1280; lỗi console do trang sinh.

**Nằm NGOÀI phạm vi làn này (không đo, không sửa):**

- **Route mới.** `app/server.py` là tệp của AG-00. Làn này **không thêm, không sửa** đường nào.
  Hệ quả: thao tác GHI nào chưa có đường thì **không vẽ nút** — xem §5 mục 1.
- **`admin/logic.js`.** Bảng `API_CHO_BACKEND` của nó là nguồn của nhãn "CHỜ BACKEND" và của ca
  thử tầng 3; làn này của AG-06. Không chạm.
- **`thu_giao_dien/*.spec.js`.** Không thêm ca E2E nào. Tầng 3 sẵn có **tự bắt đầu đo** màn nào
  được cắm vào menu (§4) — đó là kênh chứng minh, không phải viết thêm ca.
- **`admin/ai.js`, `admin/finance.js`, `admin/health.js`, `admin/carrier_health.js`.** KHÔNG
  sửa một dòng nào. Cả bốn đã đủ dùng đúng như đang có.
- **CSDL, PostgreSQL, sandbox, hãng vận chuyển.** Không chạm. Mọi phép đo chạy trên nền
  **cô lập** (`VIP_HUB_DATA` = thư mục tạm, xoá khi xong), máy chủ bind `127.0.0.1` cổng rỗng,
  chế độ hãng là **mock**, **không một lời gọi ra hãng**, không tunnel, không mở cổng ra ngoài.

---

## 2. BẢNG ĐO ĐƯỢC

### 2.1 Bốn module bị tham chiếu 0 lần

Bộ đo: `/tmp/ag05/do_man.js` — đọc `admin/admin.js`, **bỏ khối chú thích, chú thích dòng và mọi
chuỗi** rồi mới đếm. Vì sao phải bỏ: `admin.js` **nhắc `admin/carrier_health.js` trong một chú
thích**; đếm thô là đếm ra "có tham chiếu" trong khi không có lời gọi nào.

```
$ node /tmp/ag05/do_man.js /tmp/ag05/goc    # bản sao admin/ tại 6e61fc1
$ node /tmp/ag05/do_man.js "$PWD"           # worktree AG-05
cả hai: exit=0
```

| Module | Biến | Tham chiếu trong **MÃ** (trước → sau) | Tham chiếu **thô** (trước → sau) |
|---|---|---|---|
| `finance.js` | `VIPFINANCE` | **0 → 1** | 0 → 3 |
| `billing.js` | `VIPBILLING` | **0 → 1** | 0 → 2 |
| `carrier_health.js` | `VIPCARRIERHEALTH` | 1 → 1 | 2 → 2 |
| `ai.js` | `VIPAI` | **0 → 1** | 0 → 2 |
| `health.js` | `VIPHEALTH` | **0 → 1** | 0 → 2 |

`carrier_health.js` = 1 ở **cả hai** chiều: đúng màn `ket-noi-jt` mà AG-06 cắm ở G17. Mọi màn
AG-05 cắm đều **đọc ở mức NẠP MUỘN** (`window.VIPX` gọi *trong thân hàm màn*), nên con số là 1
chứ không phải 20 — cố ý: `admin/index.html` nạp `admin.js` TRƯỚC bốn module, đọc ở mức nạp tệp
là `undefined`.

### 2.2 Màn tự khai × menu × `CAC_MAN`

| | Trước | Sau |
|---|---|---|
| Màn **module tự khai** (`MAN_HINH` / `MAN`) | 15 (finance 7 · billing 7 · carrier_health 1) | 15 |
| … **SỐNG** (có mục menu **và** có nhánh `CAC_MAN`) | **2** (trong đó **1 là XANH GIẢ**, §2.5) | **15** |
| … **CHẾT** | **13** (thật ra **14**, §2.5) | **0** |
| Mục **menu** | 15 (11 tenant + 4 platform) | **35** (30 + 5) |
| Khóa **`CAC_MAN`** | 14 + 0 gắn thêm | 14 + **20** gắn thêm |
| Màn **suy ra** cho `ai.js` / `health.js` (cách đếm của tầng 3) | 2, cả hai CHẾT | 2, cả hai SỐNG |

**Đối chiếu V-13910:** theo cách đếm của `thu_giao_dien/04_nhan_va_man_dot3.spec.js` (15 màn tự
khai + 2 màn suy ra cho `ai.js`/`health.js` = **17**), trước khi sửa: **1 SỐNG / 16 CHẾT** —
khớp đúng con số "16/17" của `BAN_GIAO.md` §6.1. Sau khi sửa: **17 SỐNG / 0 CHẾT**.

### 2.3 Đường HTTP thật — đo, không đọc mã rồi đoán

Bộ dò: `/tmp/ag05/do_route.py` — dựng nền cô lập, đăng nhập `shopa-owner`, bắn HTTP thật.
```
$ python3 /tmp/ag05/do_route.py     # exit=0
[nền] pid=43869 cổng=53730 đăng nhập shopa-owner → HTTP 200
[tự kiểm] đường BỊA /api/v2/khong-ton-tai-ag05-xyz → HTTP 404 (phải là 404)
[tổng] 18/29 đường trả 2xx
```

| Màn | Đường | HTTP |
|---|---|---|
| finance `cod` | `GET /api/v2/tai-chinh/cod` | **200** |
| finance `dot` | `GET /api/v2/doi-soat/dot` | **200** |
| finance `bang_ke` | `GET /api/v2/doi-soat/dot/<id>/bang-ke` | 404 → **200** khi có đợt (§2.4) |
| finance `phai_thu` + `phai_tra` | `GET /api/v2/tai-chinh/cong-no` | **200** |
| finance `chenh_lech` | `GET /api/v2/doi-soat/dot/<id>/chenh-lech` | **200** |
| finance `dieu_chinh` | `GET /api/v2/tai-chinh/dieu-chinh` | **200** |
| (cảnh báo tài chính) | `GET /api/v2/tai-chinh/tong-so` | **200** |
| billing `goi` | `GET /api/v2/goi` | **200** |
| billing `dang-ky` | `GET /api/v2/dang-ky` | **200** |
| billing `muc-dung` | `GET /api/v2/usage` | **200** |
| billing `canh-bao` | `GET /api/v2/usage/bao-cao` | **200** |
| billing `lich-su` | `GET /api/v2/usage/su-kien` · `/tinh-phi` | **200** · **200** |
| billing `du-thao` | `GET /api/v2/billing/du-thao` | **200** |
| billing `quan-tri-goi` | `GET /api/v2/platform/goi` | 403 tenant (**200** nền tảng, §4.3) |
| ai (6 màn) | `GET /api/v2/ai/job` · `/su-kien` · `/thong-ke` | **200** ×3 |
| ai `lo` | `GET /api/v2/ai/lo/<id>` | 404 → **200** khi có lô (§2.4) |
| health | `GET /api/v2/suc-khoe` · `/san-sang` | **200** · **200** |
| health metric | `GET /api/v2/platform/quan-sat/metric` | 403 tenant (**200** nền tảng) |

### 2.4 HAI CA TỰ KIỂM BỘ DÒ — và hai lần chúng CỨU tôi khỏi kết luận sai

**(a) Đối chứng âm:** một đường **BỊA** phải trả 404. Nếu nó trả 2xx thì bộ dò đang nói dối và
mọi dòng 2xx ở trên vô nghĩa → bộ dò thoát mã **3** và không in bảng. Đo được: **404**. ✅
**(b) Đối chứng dương:** một mã màn **BỊA** phải đếm **đúng 0** lần tham chiếu. Đo được: **0**. ✅

Hai chỗ bộ dò **suýt nói dối**, ghi lại vì đúng kiểu `BAN_GIAO` §7.1:

1. **`bang_ke` trả 404 — nhưng KHÔNG phải thiếu route.** Cùng một nhánh `re.fullmatch` phục vụ
   `bang-ke|chenh-lech|xuat-csv`; `chenh-lech` và `xuat-csv` trả **200** với cùng `id` sai.
   404 ấy là *"không có đợt"*. Đối chứng dương: **nạp một bảng kê thật** rồi bắn lại —
   `POST /api/v2/doi-soat/nap` → **201**, `GET …/dot/1/bang-ke` → **200** (`/tmp/ag05/do_route2.py`,
   exit=0). Kết luận đúng: **đường CÓ thật**, chỉ thiếu dữ liệu.
2. **`POST /api/v2/dang-ky/doi-goi` trả 404 — nhưng cũng KHÔNG phải thiếu route.** Thân lỗi là
   `{"loi": "gói '' không tồn tại"` — một **404 nghiệp vụ**. Nếu tin "404 = thiếu đường" thì đã
   kết luận sai và bỏ sót một đường đang chạy. Ghi vào §5 mục 3 vì ca thử tầng 3 dùng đúng
   heuristic ấy ("2xx ⇒ nhãn nói dối"), và heuristic đó **không** phân biệt được hai loại 404.

### 2.5 MỘT XANH GIẢ bắt được: mã màn `goi` bị dùng cho hai màn khác nhau

`admin/billing.js` khai màn `["goi", "Danh sách gói", "tenant.billing.xem"]`.
`admin/admin.js` đã có sẵn màn `goi` — **"Gói & usage"**, nội dung khác (gói hiện tại + usage).
Vì **mã màn trùng nhau**, cả hai bộ đếm (bộ đo tĩnh của tôi **và**
`thu_giao_dien/04_nhan_va_man_dot3.spec.js`) đều kết luận "màn `goi` của billing.js đã được
cắm" — trong khi nó **chưa từng tồn tại**. Đó là **+1 xanh giả**: bộ đếm nói 2 SỐNG, sự thật là
**1**.

Cách đóng, và vì sao đóng như thế: **không** đổi mã màn cho khác đi (đổi là xoá dấu vết, và
`billing.js` không nằm trong phần tôi được sửa để "cho vừa bộ đếm"), mà **làm cho cái tên ấy
ĐÚNG**: màn `goi` nay đọc thêm `GET /api/v2/goi` và hiện **đúng danh sách gói** như
`billing.js` khai. Không có màn thứ hai, không có mã màn thứ hai — xanh giả thành xanh thật.

Đo lại sau khi sửa: `/tmp/ag05/thu_du_lieu.js` → *"goi: bảng danh sách gói **3** dòng = API **3**"*.

---

## 3. QUYẾT ĐỊNH TỪNG MÀN

Luật chung: **CẮM VÀO** cho mọi màn có đường đọc thật (đo được 2xx). Không màn nào bị **BỎ** —
bỏ một màn đã có mã nghiệp vụ đầy đủ là xoá việc đã làm, không phải dọn dẹp. Không màn nào chỉ
để "tệp tồn tại": mỗi màn có mã màn, mục menu, nhánh `CAC_MAN`, một đường HTTP thật, và một ca
đo số dòng DOM = số dòng API.

### 3.1 Nhóm TÀI CHÍNH — 7 màn (`admin/finance.js`)

| Mã màn | Menu | Đường đọc | Quyết định |
|---|---|---|---|
| `cod` | 💰 Bảng COD | `GET /api/v2/tai-chinh/cod` + `/tong-so` | CẮM VÀO |
| `dot` | 📑 Đợt đối soát | `GET /api/v2/doi-soat/dot` | CẮM VÀO |
| `bang_ke` | 📃 Bảng kê của hãng | `GET /api/v2/doi-soat/dot/<id>/bang-ke` | CẮM VÀO (có ô chọn ĐỢT) |
| `chenh_lech` | ⚖️ Chênh lệch đối soát | `GET /api/v2/doi-soat/dot/<id>/chenh-lech` | CẮM VÀO (đủ 7 nhóm, kể cả nhóm rỗng) |
| `phai_thu` | 📥 Công nợ phải thu | `GET /api/v2/tai-chinh/cong-no` | CẮM VÀO |
| `phai_tra` | 📤 Công nợ phải trả | **cùng một đường** `…/cong-no` | CẮM VÀO (hai màn, một đường — ghi rõ trên màn) |
| `dieu_chinh` | ✍️ Lịch sử điều chỉnh | `GET /api/v2/tai-chinh/dieu-chinh` | CẮM VÀO |

### 3.2 Nhóm GÓI & TÍNH PHÍ — 7 màn (`admin/billing.js`)

| Mã màn | Menu | Đường đọc | Quyết định |
|---|---|---|---|
| `goi` | 💳 Gói & usage | `GET /api/v2/billing` + **`GET /api/v2/goi`** | CẮM VÀO — màn sẵn có được **làm cho đúng tên** (§2.5) |
| `dang-ky` | 📋 Chi tiết đăng ký | `GET /api/v2/dang-ky` | CẮM VÀO |
| `muc-dung` | 📈 Bảng mức dùng | `GET /api/v2/usage` → `dungBangMucDung()` | CẮM VÀO |
| `canh-bao` | ⏳ Cảnh báo hạn mức | `GET /api/v2/usage` → `canh_bao` | CẮM VÀO |
| `lich-su` | 🧾 Lịch sử tính phí | `GET /api/v2/usage/tinh-phi` + `/su-kien` | CẮM VÀO |
| `du-thao` | 📄 Dự thảo hoá đơn | `GET /api/v2/billing/du-thao` + `/usage/tinh-phi` | CẮM VÀO (ĐỌC; không có nút lập dự thảo — §5) |
| `quan-tri-goi` | 🎛️ Quản trị gói (**menu nền tảng**) | `GET /api/v2/platform/goi` | CẮM VÀO |

### 3.3 Nhóm TRỢ LÝ AI — 6 màn (`admin/ai.js`)

`ai.js` **không khai bảng màn**; nó xuất sáu hàm dựng **mô hình** màn (trả dữ liệu, không trả
HTML). Tầng 3 vì thế coi module này là **MỘT** màn và suy mã màn từ tên tệp → màn đầu mang đúng
mã `ai`; năm màn còn lại là màn phụ có mã riêng. Cắm **cả sáu**, vì cắm một rồi để năm hàm kia
không ai gọi là **đúng cái lỗi đang đi sửa**, chỉ nhỏ hơn.

| Mã màn | Hàm dựng mô hình | Đường đọc | Quyết định |
|---|---|---|---|
| `ai` | `manTroLyImport` | `GET /import` → `/ai/lo/<id>` → `/ai/job` | CẮM VÀO |
| `ai-goi-y` | `manGoiY` | `GET /ai/job` → `POST /ai/job/<id>/de-xuat` | CẮM VÀO |
| `ai-canh-bao` | `manCanhBao` | như trên (gom `de_xuat[].kiem`) | CẮM VÀO |
| `ai-trang-thai` | `manTrangThai` | `GET /ai/job` (có ô lọc trạng thái) | CẮM VÀO |
| `ai-lich-su-duyet` | `manLichSuDuyet` | `GET /ai/su-kien` + `/ai/job` | CẮM VÀO |
| `ai-thong-ke` | `manThongKe` | `GET /ai/thong-ke` | CẮM VÀO |

**Vì sao có một lời gọi POST trong nhóm này** (ghi ra vì đây là chỗ dễ bị hiểu là vi phạm):
`ai_job.de_xuat_cho_nguoi_duyet()` là hàm **duy nhất** biết ghép gợi ý AI với dòng gốc nằm ở
máy (SĐT và COD **không hề được gửi** cho nhà cung cấp), và nó chỉ được phơi ra ở
`POST /api/v2/ai/job/<id>/de-xuat`. Docstring của chính hàm ghi *"KHÔNG ghi CSDL"*;
`app/server.py` cấp cho nó quyền **đọc** `tenant.ai.dung`, không phải quyền ghi. Chép phép ghép
ấy vào giao diện là tạo **bản thứ hai sẽ lệch**. Nếu AG-00 muốn có đường GET cho nó thì đó là
việc của AG-00 — ghi ở §6.

### 3.4 Nhóm HỆ THỐNG — 1 màn (`admin/health.js`)

| Mã màn | Menu | Đường đọc | Quyết định |
|---|---|---|---|
| `health` | 🩺 Sức khoẻ hệ thống | `/suc-khoe` · `/san-sang` · `/platform/quan-sat/metric` | CẮM VÀO |

Chú thích cũ trong `admin/health.js` ghi *"ROUTE NÀY CHƯA ĐƯỢC CẮM"* — **đã cũ**: đo lại cả ba
đường đều **CÓ**. Màn đọc thẳng, hiện mã HTTP thật, và giữ nguyên luật của module: **health và
readiness là HAI câu hỏi, không gộp thành một ô "tổng quan"**; `null` là **XÁM** (chưa đo),
không mượn màu xanh; thiếu quyền metric thì hiện **"CHƯA ĐO ĐƯỢC — thiếu quyền"**, không hiện 0.

---

## 4. BẰNG CHỨNG SAU KHI CẮM

### 4.1 Tầng 3 — trình duyệt thật (Chromium)

```
$ sh thu_giao_dien/chay.sh --reporter=list          # chạy TRỌN BỘ, không lọc
$ echo $?                                            # 0
```
| | Trước | Giữa đường (lần 1) | **Sau** |
|---|---|---|---|
| Ca đạt | 3 | 30 | **37** |
| Ca hỏng | 0 | 2 | **0** |
| Ca không chạy | 0 | 5 | **0** |
| Mã thoát | 0 | — | **0** |

**Lượt xác nhận cuối** (sau khi thêm khối chú thích vào `admin/billing.js`), chạy lại từ đầu:
`sh thu_frontend/chay.sh` → exit **0** (tầng 1 `pass 56 / fail 0 / skipped 0`, tầng 2 `Ran 36 tests … OK`);
`sh thu_giao_dien/chay.sh --reporter=list` → exit **0**, `37 passed`, `0 failed`, `0 did not run`.

Lần chạy giữa đường **HỎNG 2 ca** và đó là **bằng chứng bộ thử còn khả năng đỏ**: `02_bo_cuc`
và `04_nhan_va_man_dot3` bắt được **tràn ngang 1280px** ở hai màn mới (`dang-ky`, `muc-dung`) —
`div.so(73px)`. Nguyên nhân thật: tôi đặt một **huy hiệu dài** ("Chưa có đăng ký (đang dùng gói
của tenant)") vào ô KPI, mà `.huy-hieu` có `white-space: nowrap`. Đã sửa bằng cách cho huy hiệu
**xuống dòng được** (`hh(d, them, xuongDong)` ghi đè bằng style nội tuyến, **không** sửa
`assets/css/style.css` — CSS ấy dùng chung cho cả mười trang demo, sửa nó là ra ngoài phạm vi).
Sau khi sửa: 37/37, và **0 phần tử tràn** ở cả ba bề rộng cho cả 30 màn.

`[đo] đợt 3 khai 17 màn; 16 đã có trên menu; 1 CHƯA cắm: billing.js → quan-tri-goi` — dòng này
**đúng và không phải lỗi**: ca thử chạy bằng tài khoản **tenant**, mà `quan-tri-goi` là màn
**nền tảng**. Màn ấy có đo riêng ở §4.3.

### 4.2 Tầng 1 + tầng 2 — logic thuần và HTTP + tệp tĩnh

```
$ sh thu_frontend/chay.sh ; echo $?      # 0
TẦNG 1 (node --test): tests 56 · pass 56 · fail 0 · skipped 0
TẦNG 2 (python):       Ran 36 tests … OK
```

### 4.3 Phép đo RIÊNG cho màn nền tảng — vì tầng 3 KHÔNG phủ vai trò nền tảng

Đo được: `grep -rn "platform" thu_giao_dien/*.spec.js` → **0 dòng**. Nghĩa là `quan-tri-goi` là
màn "đã cắm" mà **chưa ca thử nào bấm vào**. Nên có phép đo riêng (không thêm vào
`thu_giao_dien/` — thư mục ấy của AG-06):

```
$ sh /tmp/ag05/chay_nen_tang.sh ; echo $?     # 0
[đo] menu nền tảng: tenants quan-tri-goi vai-tro audit-nen-tang cai-dat
  ĐẠT  menu nền tảng CÓ mục `quan-tri-goi`
[đo] GET /api/v2/platform/goi trả 3 gói
  ĐẠT  tiêu đề màn = "Quản trị gói"
  ĐẠT  bảng hiện ĐÚNG 3 dòng = số gói API trả (3)
  ĐẠT  375px · 768px · 1280px: tài liệu lệch 0px · 0 phần tử tràn
  ĐẠT  ĐỐI CHỨNG ÂM: menu TENANT KHÔNG có `quan-tri-goi`
  ĐẠT  menu TENANT có các màn mới (cod/muc-dung/ai) — tức phép đo không rỗng
  ĐẠT  0 lỗi do trang sinh
KẾT QUẢ: ĐẠT (0 ca hỏng)
```

### 4.4 "KHÔNG CHỈ LÀ TỆP TỒN TẠI" — đối chiếu SỐ DÒNG DOM với SỐ DÒNG API

Tầng 3 kiểm màn **mở được**, **không lỗi console**, **không tràn ngang**. Một màn dựng toàn ô
rỗng — hoặc một bảng **viết cứng trong JS** — vẫn ĐẠT cả ba. Nên có phép đo thứ ba: đếm số dòng
DOM và số dòng **API trả về trong cùng một phiên**, hai con số **phải bằng nhau**.

```
$ sh /tmp/ag05/chay_du_lieu.sh ; echo $?     # 0
[đo] API trả: {"so_goi":3,"so_lich_su":0,"so_canh_bao":1,"so_loai_han_muc":8,"so_du_thao":0,
               "so_chang":1,"han_muc_ai":500,"so_phep_kiem":5,"so_cod":0,"so_dot":0}
  ĐẠT  goi        · bảng danh sách gói 3 dòng = API 3
  ĐẠT  muc-dung   · bảng 8 dòng = API 8 loại hạn mức
  ĐẠT  dang-ky    · lịch sử 0 dòng = API 0
  ĐẠT  canh-bao   · 1 dòng = API 1 loại cảnh báo
  ĐẠT  du-thao    · bảng "đã lưu" 0 dòng = API 0; bảng tóm tắt kỳ có 4 dòng
  ĐẠT  dot        · 0 dòng dữ liệu = API 0 đợt (hiện trạng thái rỗng, KHÔNG bịa)
  ĐẠT  bang_ke    · không có đợt ⇒ hiện CHƯA ĐO ĐƯỢC kèm lý do, KHÔNG bịa bảng
  ĐẠT  ai-thong-ke· 4 ô KPI (trần AI=500)
  ĐẠT  health     · bảng readiness 5 dòng = API 5 phép kiểm
  ĐẠT  cod        · 0 dòng COD = API 0
  ĐẠT  phai_thu   · "Công nợ phải thu" — hai màn công nợ dùng chung một đường
  ĐẠT  ai         · hiện 6 bước khi có lô, CHƯA ĐO ĐƯỢC khi không có — cả hai đều trung thực
KẾT QUẢ: ĐẠT (0 ca hỏng)
```

**Bộ đếm này cũng đã nói dối một lần và tôi bắt được:** bản đầu đếm `tbody tr` nên tính cả
**dòng "trạng thái rỗng"** (`<td colspan>`) là dữ liệu → báo HỎNG oan cho `dang-ky` (1 dòng =
chính dòng "Chưa có lần đổi gói nào") và `dot` (0 đợt). Luật đếm nay là *"trừ mọi hàng có ô
`colspan`"*. Ghi lại vì **cái sai nằm ở phép đo, không nằm ở sản phẩm**.

### 4.5 Ca an toàn của dự án vẫn xanh

- `app/thu/thu_saas.py::test_13` cấm `admin/` chứa `privateKey` / `jtexpress.vn`:
  `grep -rn "privateKey\|jtexpress.vn" admin/` → **exit 1** (không có dòng nào) = ĐẠT.
- Cả 5 ca `05_ket_noi_jt.spec.js` (màn J&T của AG-06) **vẫn đạt** sau khi tôi sửa `admin.js`:
  không giá trị credential nào lọt ra, chốt D-9 vẫn khớp hằng trong mã nguồn backend.

---

## 5. CHƯA ĐO / CHƯA LÀM — NÓI THẲNG

**1. Các thao tác GHI trên những màn mới: KHÔNG vẽ nút, nên KHÔNG đo được đường đi của người
dùng.** Lý do: G19 chỉ cắm phần **ĐỌC**, và vẽ một cái nút rồi để nó báo lỗi là dạy người dùng
rằng nút hỏng là chuyện bình thường. Mã HTTP đo được của từng đường GHI (nền cô lập):

| Đường GHI | HTTP đo được | Đọc ra |
|---|---|---|
| `POST /api/v2/doi-soat/nap` | 400 khi thiếu thân | đường **CÓ**, chỉ thiếu dữ liệu |
| `POST /api/v2/dang-ky/doi-goi` | 404 kèm *"gói '' không tồn tại"* | đường **CÓ** — **404 nghiệp vụ**, không phải thiếu route (§2.4) |
| `POST /api/v2/ai/job` | 400 khi thiếu thân | đường **CÓ** |
| `POST /api/v2/tai-chinh/dieu-chinh` | 403 với vai trò nền tảng | đường **CÓ** (RBAC chặn) |
| `POST /api/v2/billing/du-thao` | **404** `{"loi":"không có đường này"}` | **CHƯA CẮM** — cố ý: cần quyền `tenant.billing.lap_du_thao` chưa có (V-13909) |
| `POST /api/v2/platform/goi/phien-ban` | **404** | **CHƯA CẮM** |
| `POST /api/v2/platform/tenants/<id>/doi-goi` | **404** | **CHƯA CẮM** |
| `POST /api/v2/platform/tenants/<id>/tam-ngung` | **404** | **CHƯA CẮM** |

Bốn đường **404 ở trên là lý do màn `du-thao` và `quan-tri-goi` chỉ có phần ĐỌC**; mỗi màn ghi
rõ ngay trên màn đường nào chưa có, kèm mã HTTP đo được.

**2. Không ca E2E nào cho thao tác GHI ở những màn mới** — vì không có nút thì không có gì để
bấm. Nếu lượt sau cắm nút, **phải thêm ca cùng lượt** (luật của dự án).

**3. `admin/billing.js → API_CHO_BACKEND` SAI ĐƯỜNG ở 5 dòng đầu — đã đính chính bằng chú
thích, CHƯA sửa dữ liệu.** Năm đường
`/api/v2/billing/{goi,dang-ky,muc-dung,canh-bao,lich-su}` **đều 404**; chức năng nằm ở
`/api/v2/goi`, `/api/v2/dang-ky`, `/api/v2/usage…`. Tôi **giữ nguyên** mảng vì `trangThaiRoute()`
đang đếm theo nó và làn khác có thể đang đọc; sửa dữ liệu bảng là việc của AG-00. **Điều đáng
ghi nhất:** `grep -rn "billing.js\|VIPBILLING" app/thu/*.py` → **0 dòng**, tức **không ca thử
nào canh bảng này**, trong khi `finance.js` có hẳn một ca (`app/thu/thu_tai_chinh.py::test_j4`
canh cả hai chiều). Bảng sai sống sót chính vì **không ai canh**.

**4. Nhãn "CHỜ BACKEND" trên màn mới: KHÔNG thêm cái nào.** Tầng 3 bắt mọi nhãn ấy phải khớp
thực tế máy chủ (2xx ⇒ nhãn nói dối). Màn mới chỉ có nhãn `DỮ LIỆU LOCAL / HÃNG MOCK` (không
khớp mẫu `CHỜ BACKEND`) và các câu "CHƯA ĐO ĐƯỢC" bằng chữ thường — cố ý để không tạo nhãn chờ
giả. Ba nhãn CHỜ BACKEND cũ vẫn nguyên và vẫn đúng (đo lại: `don` 200 khai `mot_phan`,
`g09/ket-noi-hang` 404, `webhook/su-kien/<id>` 404).

**5. `POST /api/v2/ai/job/<id>/de-xuat` là POST dùng để VẼ màn.** Đã đo là **chỉ đọc**
(docstring `ai_job.py` ghi rõ; `server.py` cấp quyền `tenant.ai.dung`), nhưng nó vẫn là một
POST trong luồng đọc — chưa đo được **dưới tải đồng thời** (nhiều người mở màn cùng lúc). Nằm
ngoài phạm vi G19.

**6. Chưa đo trên trình duyệt nào khác Chromium, chưa đo thiết bị cảm ứng thật, chưa đo trình
đọc màn hình, chưa in thật.** Đúng phạm vi mà `thu_giao_dien/chay.sh` tự khai.

**7. Chưa đo bàn phím.** V-13911 (menu `<a>` không `href`/`tabindex`/`role`, 15 lượt Tab không
rời `body`) là **lỗi có thật, vẫn còn**, và **20 mục menu mới làm nó nặng thêm** — mọi mục mới
đều là `<a data-man>` cùng kiểu. Cố ý **không** sửa: V-13911 là việc riêng, và bản vá của nó
phải đi **cùng lượt** với ca canh bàn phím (luật dự án: *"Thêm ca canh cùng lượt với bản vá,
không trước"*). **Đây là nợ đã biết, không phải nợ mới phát sinh.**

---

## 6. VIỆC CÒN LẠI — cho AG-00 / làn khác

1. **Cắm 3 đường ghi của nền tảng** (`/platform/goi/phien-ban`, `/platform/tenants/<id>/doi-goi`,
   `/platform/tenants/<id>/tam-ngung`) nếu muốn màn `quan-tri-goi` làm được việc chứ không chỉ xem.
2. **Cắm `POST /api/v2/billing/du-thao`** cùng quyền `tenant.billing.lap_du_thao` (V-13909).
3. **Sửa `admin/billing.js → API_CHO_BACKEND`** cho khớp đường thật, **kèm một ca thử kiểu
   `thu_tai_chinh.py::test_j4`** — nếu chỉ sửa bảng mà không thêm ca canh thì lần sau nó lệch lại.
4. **Cân nhắc một đường GET cho `de_xuat_cho_nguoi_duyet`** để luồng đọc không phải dùng POST.
5. **`admin/health.js`**: chú thích *"ROUTE NÀY CHƯA ĐƯỢC CẮM"* nay **sai** (đo: cả ba đường đều
   có). Tệp ấy không thuộc danh sách tôi được ghi nên tôi **không sửa** — để lại cho làn giữ tệp.
6. **V-13911 (bàn phím)** — xem §5 mục 7.

---

## 7. CHẠY LẠI TẤT CẢ

```sh
cd <worktree g19-ag05-manma>

# Bảng đo tĩnh: tham chiếu module + màn SỐNG/CHẾT (có 2 ca tự kiểm bộ dò)
node /tmp/ag05/do_man.js "$PWD"

# Đường HTTP thật trên nền cô lập (có đối chứng âm)
python3 /tmp/ag05/do_route.py

# Tầng 1 + tầng 2
sh thu_frontend/chay.sh ; echo "exit=$?"

# Tầng 3 — TRÌNH DUYỆT THẬT, chạy trọn bộ
sh thu_giao_dien/chay.sh --reporter=list ; echo "exit=$?"

# Phép đo riêng: màn nền tảng `quan-tri-goi` + đối chứng âm RBAC
sh /tmp/ag05/chay_nen_tang.sh ; echo "exit=$?"

# Phép đo riêng: số dòng DOM phải BẰNG số dòng API
sh /tmp/ag05/chay_du_lieu.sh ; echo "exit=$?"
```

**Ba tệp đo riêng nằm ở `/tmp/ag05/`** (`do_man.js`, `do_route.py`, `do_route2.py`, `do_nen_tang.py`,
`thu_nen_tang.js`, `thu_du_lieu.js`, `chay_nen_tang.sh`, `chay_du_lieu.sh`) — **cố ý KHÔNG** đặt
trong repo: `thu_giao_dien/` là phần của AG-06, và tôi không được ghi ở đó. Muốn giữ chúng lâu
dài thì phải có người nhận chúng vào một thư mục có chủ.

**Ghi chú môi trường (để phiên sau không mất thời gian đo lại):** máy này **không tải được**
Chromium revision `1194` mà `playwright-core@1.56.1` đòi (`npx playwright install chromium`
đứng ở 628 KB rồi thôi — mạng CDN không thông). Bản chạy được là bản **có sẵn trong cache**
`~/Library/Caches/ms-playwright/chromium_headless_shell-1148`, ghép vào chỗ 1194 bằng một liên
kết tượng trưng trong `node_modules/playwright-core/.local-browsers/`. `node_modules` không nằm
trong git nên việc này **không đi vào bản giao**; nhưng **ai chạy tầng 3 trên máy này cũng phải
làm lại bước ấy**, hoặc cài được mạng.

**Một cái bẫy đã sập, ghi lại:** lần chạy tầng 3 đầu tiên tôi viết
`sh chay.sh … | tail -60` — `$?` khi ấy là mã thoát của **`tail`** (`0`), không phải của bộ thử.
Bộ thử **hỏng** (Chromium không tồn tại) mà Terminal báo **thành công**. Mọi lần chạy sau đều
ghi `> file 2>&1` rồi đọc `$?` riêng. Đúng cái bẫy `BAN_GIAO` §7.1 đã ghi: *"hai bộ thử che mã
thoát của chính nó"*.
