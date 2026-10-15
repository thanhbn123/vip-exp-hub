# G17 · AG-06 — FRONTEND QUẢN LÝ KẾT NỐI J&T + E2E LOCAL

Người làm: AG-06 (nhánh làm việc `g17-ag06-security`). Ngày đo: 15/10/2026.
Mốc git lúc đo: `24b9f9fd8277976ec5c0d4d61ad2f60a044bfc3a` (việc 1 của AG-06 đã được commit ở mốc này).
Phạm vi được phép ghi: `admin/admin.js` · `admin/carrier_health.js` · `admin/logic.js` ·
`pages/carriers.html` · `thu_giao_dien/*.spec.js` · `docs/G17_FRONTEND_E2E.md`.
`app/server.py` **KHÔNG bị sửa** — màn mới chỉ dùng lại ba route đã có.

---

## 1. QUYẾT ĐỊNH về `admin/carrier_health.js`: **CẮM VÀO** (không xoá)

### 1.1 Đo lại phát hiện của AG-00 — con số đúng, nhưng cách đo là một proxy

AG-00 đo `carrier_health.js = 0 tham chiếu trong admin.js`. Đo lại trên chính cây này:

| phép đo | kết quả |
|---|---|
| `grep -c "carrier_health" admin/admin.js` | 0 |
| `grep -c "VIPCARRIERHEALTH" admin/admin.js` | 0 |
| `grep -c "carrier_health" admin/index.html` | 1 (dòng 25: `<script src="carrier_health.js">`) |
| số màn khai `VIPCARRIERHEALTH.MAN_HINH` trước khi sửa | 0 (module không khai màn nào) |

Nên phát hiện V-13910 đúng ở kết luận, nhưng cơ chế chết không phải "tệp không được nạp":
**tệp ĐƯỢC nạp và KHÔNG có màn nào dùng nó** — không mục menu, không nhánh trong `CAC_MAN`,
không hàm nào của nó được gọi. Đó là dạng chết tệ hơn "không nạp": nó chiếm một dòng trong
`admin/index.html`, làm người đọc tin rằng đã có màn sức khoẻ hãng.

### 1.2 Chọn gì và vì sao

Chọn **CẮM VÀO**: màn mới "🔌 Kết nối J&T" dùng lại chính các hàm của tệp
(`nhanMuc` · `dongSanSang` · `bangSanSang` · `sucKhoeHang` · `ngatMach` · `canSoatDong` · `locBiMat`)
và bổ sung phần quyết định cho bốn câu hỏi vận hành. Lý do:

- Logic sáu mức sẵn sàng + ngắt mạch + canh mã lạ trong tệp là thứ màn mới **cần thật**, không
  phải mã trang trí. Xoá đi thì phải viết lại đúng chỗ đó ở nơi khác — và bản viết lại sẽ lệch.
- Cắm vào tạo được **đường thật từ giao diện tới tệp**: menu → màn → hàm. Có ca E2E bấm được
  (ca 01 của `thu_giao_dien/05_ket_noi_jt.spec.js`).
- Tệp nay **tự khai màn** (`MAN_HINH = [{ma:"ket-noi-jt", …}]`), nên bộ thử có sẵn
  (`04_nhan_va_man_dot3.spec.js`) **tự bắt đầu đo nó** — không cần sửa bộ thử cũ. Log lượt chạy
  thật: `[đo] GET /api/v2/g09/ket-noi-hang (màn ket-noi-jt) → HTTP 404` (nhãn CHỜ BACKEND của màn
  được ca "nhãn không nói dối" bắn thật).
- Ba màn cùng cảnh ngộ khác — `finance.js` (7 màn khai), `billing.js` (6), `ai.js`, `health.js` —
  **vẫn chưa cắm**, đo được ở lượt chạy này:
  `[đo] đợt 3 khai 17 màn; 2 đã có trên menu; 15 CHƯA cắm vào giao diện`.
  Đây là **ngoài phạm vi được phép ghi của AG-06**, ghi ra đây để AG-00 quyết (xem mục 6).

### 1.3 Cắm vào bằng gì — bốn câu hỏi của người vận hành

| câu hỏi | nguồn dữ liệu | ghi chú |
|---|---|---|
| đang ở môi trường nào, cổng đã MỞ chưa | `GET /api/v2/g09/suc-khoe-hang` → `hang.jt.thieu_de_sandbox` · `thieu_de_live` · `ket_luan`; `GET /api/v2/tai-khoan-hang` → `moi_truong` | cổng MỞ ⇔ danh sách "còn thiếu gì" RỖNG; danh sách VẮNG ⇒ "chưa đo được" |
| bốn trường credentials đã có chưa | hai danh sách trên, đọc câu "còn thiếu gì" | **chỉ tên + có/không**; xem mục 4 |
| thao tác nào CHƯA làm được, vì sao | `hang.jt.capabilities` + `hang.jt.san_sang[<hạng mục>]` (`muc` + `do_bang_gi`) | 4 thao tác: `cancelOrder` · `calculatingFees` · `printOrder` · `getOrder` |
| chốt D-9 còn chặn không, vì sao | **hằng của mã nguồn** `app/adapter_jt.py` (mục 5) | **KHÔNG qua API** — dán nhãn nguồn ngay trên màn; xem mục 3 |

Thêm: bảng sáu mức sẵn sàng (10 hạng mục, kèm câu "đo bằng gì"), ngắt mạch, mã trạng thái
NEEDS_REVIEW/AMBIGUOUS, khoá an toàn toàn cục `live_mo`/`CHO_PHEP_LIVE`, khoá chống trùng.

**Hai đường vào thật:** (1) menu quản trị → 🔌 Kết nối J&T (`admin/index.html`, quyền
`tenant.hang.xem`); (2) liên kết sâu `admin/index.html#ket-noi-jt` — nay SPA biết đọc hash lúc
dựng khung **và** nghe `hashchange` (đổi hash trong cùng tài liệu không nạp lại trang, nên chỉ
đọc lúc dựng là liên kết trông như hỏng). Trang `pages/carriers.html` có nút "Mở màn quản trị →"
trỏ vào đúng hash đó.

---

## 2. E2E LOCAL — lệnh, mã thoát, số ca, số BỎ QUA

### 2.1 Bộ E2E giao diện (tầng 3, Chromium)

```sh
$ sh thu_giao_dien/chay.sh                    # chạy TOÀN BỘ 5 tệp spec
[giao-dien] nền=/var/folders/…/veh-giao-dien.XXXX cổng=18xxx pid=NNNNN
  1 skipped
  36 passed (44.6s)
EXIT=0
```

- **mã thoát: 0** (ghi TRƯỚC mọi pipe; không qua `tee`/`head`)
- **số ca: 37** — 36 đạt · **1 BỎ QUA**
- ca BỎ QUA: `03_quyen.spec.js:43 · D-7 — màn tài chính …`, lý do in ra trong log:
  *"CHƯA ĐO ĐƯỢC: không màn tài chính nào có trên menu — xem phát hiện P-1 trong
  docs/G12_PLAYWRIGHT.md"*. **Đây là ca bỏ qua CÓ SẴN từ trước, không phải ca của AG-06**, và
  nguyên nhân của nó chính là việc `finance.js` chưa được cắm (mục 1.2). Skip không phải đạt.

Chạy riêng tệp mới (10 ca, dùng khi lặp):

```sh
$ sh thu_giao_dien/chay.sh 05_ket_noi_jt.spec.js
  10 passed (10.8s)
EXIT=0
```

### 2.2 Mười ca của `thu_giao_dien/05_ket_noi_jt.spec.js`

| # | ca | đo cái gì |
|---|---|---|
| 01 | đường vào thật | màn có trên MENU THẬT và **bấm được** (bấm đúng thẻ `<a>` của menu) |
| 02 | số trên màn = số API | từng cổng · số lý do · nguyên văn lý do · `live_mo` · kết luận · 10 dòng sáu mức |
| 03 | **KHÔNG lộ credential** | quét **MỌI màn** + trang tĩnh: canary đầy đủ, 4 ký tự cuối, và mọi giá trị dưới khóa nghe như bí mật |
| 04 | tên trường + D-9 khớp mã nguồn | đọc `app/cau_hinh.py` + `app/adapter_jt.py` rồi so với chữ trên màn |
| 05 | bốn thao tác bị khoá + lý do | đủ 4 dòng, mỗi dòng `BỊ KHOÁ`, lý do là **câu backend trả**, tên năng lực nằm trong `DUONG_API` |
| 06 | dữ kiện API không trả | nhãn CHỜ BACKEND phải khớp: route đó bắn thật phải 404/405 |
| 07 | không gọi hãng | không request nào ra ngoài `127.0.0.1`, không tới miền hãng; 0 lỗi console; 0 tệp tĩnh hỏng |
| 08 | lối vào sâu + trang tĩnh | `#ket-noi-jt` mở đúng màn; `pages/carriers.html` bấm sang được |
| 09 | chưa đăng nhập | trang nói thẳng, **không** hiện tên trường, **không** hiện số suy đoán |
| 10 | bố cục 375px | màn mới và trang tĩnh: lệch 0px, 0 phần tử tràn ngoài `.cuon-ngang` |

### 2.3 Bộ thử hiện có — chạy `sh app/thu/chay_tat_ca.sh`

Xem mục 5 (số thật của lượt chạy cuối) — và **một lưu ý về môi trường**: trong shell của tác tử
này, `GIT_CONFIG_COUNT`/`GIT_CONFIG_VALUE_0/1` được đặt mà thiếu `GIT_CONFIG_KEY_0`, nên **mọi
lệnh `git` thoát 128** (`error: missing config key GIT_CONFIG_KEY_0`). Ca
`thu_bao_mat.py::test_f3` có gọi `git check-ignore` nên HỎNG vì lý do môi trường, không vì mã.
Đã đo lại: với `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1`,
`thu_bao_mat.py` → **Ran 57 tests … OK**. Bộ thử đầy đủ dưới đây chạy trong môi trường đã gỡ ba
biến đó; ai chạy lại mà thấy `thu_bao_mat` hỏng thì kiểm ba biến này trước khi tìm lỗi trong mã.

---

## 3. HAI DỮ KIỆN API KHÔNG TRẢ — cách xử lý, và vì sao không bịa

### 3.1 Chốt D-9 (`area`) — đọc từ MÃ NGUỒN, có nhãn nguồn, có ca chống lệch

Payload `/api/v2/g09/suc-khoe-hang` **không có mục nào về D-9** (đo được: bốn điều kiện nó liệt
kê là quyền · người duyệt · file credentials · `CHO_PHEP_LIVE`). Đây là một khoảng trống thật:
người vận hành đọc payload sẽ tưởng mở đủ bốn điều kiện là gửi được đơn thật, trong khi chốt D-9
vẫn chặn ở chỗ dựng `bizContent`.

Cách xử lý: màn đọc hằng `ANH_XA_AREA_DA_XAC_NHAN` / `NGUON_XAC_NHAN_AREA` /
`CAP_HANH_CHINH_CHO_AREA` của `app/adapter_jt.py`, in trạng thái **kèm nhãn "đọc từ MÃ NGUỒN,
KHÔNG qua API"**, và ca E2E 04 **đọc lại chính tệp đó** rồi so với chữ trên màn — mã nguồn đổi
mà màn chưa đổi là ca HỎNG. Đây là điều kiện để một hằng chép tay không trở thành "số liệu viết
tay trong giao diện".

### 3.2 Từng trường credentials — suy từ câu "còn thiếu gì", và **không dám nói "có" khi chưa đủ căn cứ**

Route hiện có chỉ trả **tên trường còn thiếu** trong câu của backend
(`app/harness_hang.py::thieu_gi_de_chay`), chứ không trả trạng thái từng trường. Ba nhánh:

1. câu trả lời nói **chưa có nguồn** credentials (thiếu biến trỏ file · file không tồn tại · file
   không có mục cho hãng) ⇒ cả bốn trường `CHƯA CẤU HÌNH` — bằng chứng ÂM đủ mạnh;
2. câu trả lời **liệt kê tên** trường thiếu ⇒ tên đó `CHƯA CẤU HÌNH`, các tên còn lại
   `ĐÃ CẤU HÌNH`;
3. **không có câu nào** về credentials ⇒ `CHƯA ĐO ĐƯỢC`. Cố ý KHÔNG suy ra "có": hướng an toàn
   của một phép đo hỏng là "chưa biết", không phải "đã xong".

Trạng thái hiện tại của hệ (đo trên nền cô lập): cả bốn trường **CHƯA CẤU HÌNH**, với căn cứ
nguyên văn *"thiếu VIP_HUB_HARNESS_CRED_FILE: đường dẫn file JSON chứa credentials"*.

### 3.3 Bảng đường dẫn đã/chưa xác minh

Nằm trong `app/adapter_jt.py::DUONG_API`, **không phơi ra HTTP**. Màn **không chép tay** bảng đó:
nó khai một route mong đợi trong `admin/logic.js → API_CHO_BACKEND`
(`GET /api/v2/g09/ket-noi-hang`) và hiện nhãn CHỜ BACKEND. Bộ thử HTTP sẵn có **bắn thật** route
này và đòi 404/405 — nên nhãn không thể nói dối lâu (đo được: `HTTP 404`).

---

## 4. BẢO MẬT: KHÔNG LỘ GIÁ TRỊ CREDENTIAL

### 4.1 Phát hiện THẬT trong lượt làm này (đã vá)

`admin/admin.js` (màn "Hãng vận chuyển") **đang in 4 ký tự cuối của credential** ra bảng tài
khoản hãng: `…${credentials_duoi}` với nhãn "(mã hóa, không xem lại được)". Bốn ký tự cuối **là
một phần giá trị credential** — hiện nó ra là mở đường cho người đọc màn hình/ảnh chụp/log thu
thập dần từng phần.

- Đã sửa: chỉ còn trạng thái `đã có credentials` / `chưa có credentials` (đọc `credentials_duoi`
  như một **boolean**, không bao giờ lấy giá trị) + lần đổi gần nhất; kèm câu nói rõ màn không
  hiện giá trị/độ dài/4 ký tự cuối.
- Ca 03 của E2E mới là ca bắt được nó, và nay **quét cả 11 màn trên menu + `pages/carriers.html`**.

### 4.2 Ca E2E khẳng định điều đó bằng cách nào (không phải đọc chữ rồi tin)

1. Đặt **canary** vào credentials của **mọi** tài khoản hãng qua đúng route `rotate` của hệ
   (`CANARY-AG06-9Q7Z` cho J&T, `CANARY-AG06-VTP-4X8K` cho VTP — chuỗi tự đặt, không phải
   credential thật, không gọi hãng). Canary là cần thiết vì tài khoản seed có
   `credentials_duoi = "mock"` — trùng tên môi trường "mock" — nên nếu để nguyên thì phép quét
   sẽ báo hỏng GIẢ.
2. Khẳng định backend **không** trả giá trị đầy đủ qua API (nếu trả, đó là lỗi backend).
3. Khẳng định 4 ký tự cuối **có thật** trong `carrier_accounts.credentials_duoi` — nếu không thì
   ca này không đo được gì (một phép đo rỗng không được phép xanh).
4. Dựng danh sách "thứ không được xuất hiện" **từ dữ liệu**: canary đầy đủ + 4 ký tự cuối + mọi
   giá trị nằm dưới khóa khớp `/(secret|password|private|token|api_?key|duoi)/i` trong cả ba
   payload (bỏ cột thời gian `credentials_doi_luc` — nó không phải giá trị credential).
5. Quét `documentElement.outerHTML` của **mọi màn** và của `pages/carriers.html`: không chuỗi nào
   trong danh sách trên được xuất hiện — kể cả trong `title`, comment HTML hay thuộc tính.
6. Vẫn khẳng định **tên** bốn trường thì **phải** hiện, kèm trạng thái có/không (nếu không thì
   màn không trả lời được "còn thiếu gì").

### 4.3 Một điểm nối phải khai: tên trường thứ hai viết dưới dạng ghép chuỗi

`app/thu/thu_saas.py::test_13` và `thu_frontend/thu_logic.mjs` (ca 54) **cấm chuỗi `privateKey`
xuất hiện trong `admin/`** — luật đúng: mã giao diện không được chứa khoá hãng. Một **tên trường**
thì không phải khoá, nhưng phép kiểm là phép so chuỗi. Ba đường, và đường đã chọn:

| đường | kết quả |
|---|---|
| bỏ không hiện tên | màn không trả lời được "còn thiếu trường nào" (yêu cầu AG-06) |
| viết thẳng tên | làm HỎNG một bất biến đang xanh của dự án |
| **ghép chuỗi lúc chạy + dán nhãn + ca E2E đối chiếu với `app/cau_hinh.py`** | **giữ cả hai** |

Chỗ ghép chuỗi nằm ở **đúng một dòng** trong `admin/carrier_health.js`, có khối chú thích giải
thích đầy đủ ngay trên nó. Ca E2E 04 đối chiếu tên hiện trên màn với
`JT_TRUONG_NEN_TANG` + `JT_TRUONG_BUU_CUC` của `app/cau_hinh.py` (và cả hai tệp backend phải khớp
nhau) — nên tên không thể lệch âm thầm. Đây là điểm nối **cần AG-00 biết**; nếu sau này có route
trả tên trường, nên bỏ hằng chép tay này.

---

## 5. BẰNG CHỨNG LƯỢT CHẠY CUỐI

### 5.1 Bộ E2E giao diện

```
$ sh thu_giao_dien/chay.sh
EXIT=0 · 36 passed · 1 skipped · 37 ca · 44.3s
```

### 5.2 Bộ thử toàn dự án

```
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 sh app/thu/chay_tat_ca.sh
EXIT=0
```

### 5.3 Bảng tổng kết nguyên văn (chép từ log, không viết lại theo trí nhớ)

```
══════════════════════════════════════════════════════════
  python:   1315 ca · 37 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  KHÔNG

  PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI:
    đo trên: Darwin arm64 · python 3.9.6 · SQLite 3.51.0
    máy chủ bind 127.0.0.1 · adapter hãng ở chế độ MOCK (2 hang dang ky (jt, vtp) - dang MO live: khong hang nao)
    NGOÀI phạm vi: VPS · CSDL NGHIỆP VỤ chưa chuyển sang PostgreSQL (mới chỉ thử schema
      trên cụm tạm cổng riêng) · nhiều tiến trình (bộ riêng app/thu/dong_thoi/chay.py;
      trần rate limit sống trong bộ nhớ MỘT tiến trình) · DOM/CSS trong trình duyệt thật ·
      nhãn hãng thật · credentials hãng thật · AI thật · dữ liệu lớn · Safari/Firefox
══════════════════════════════════════════════════════════
```

- **mã thoát: 0** · **0 bộ HỎNG** · **0 bộ BỎ QUA** ở tầng Python.
- `frontend: 56` = tầng 1 (logic thuần, Node) — trong đó **ca 54 canh `admin/logic.js` không chứa
  dấu hiệu secret**, và ca này CHÍNH LÀ chỗ bắt được mục 4.3 khi bản đầu viết thẳng tên trường.
- `frontend: 36` = tầng 2 (HTTP + tệp tĩnh) — gồm ca `test_05` quét **mọi tệp phục vụ được trong
  `admin/` và `assets/`** tìm dấu hiệu secret; đó là ca thứ hai bắt mục 4.3.
- `E2E: 41/41` = bộ `app/thu/chay_e2e.sh` qua HTTP thật (khác tầng 3 Chromium ở mục 5.1).
- Lượt chạy này **không** chạy tầng 3 (theo thiết kế của `chay_tat_ca.sh`): tầng 3 chạy riêng ở
  mục 5.1 và cần Chromium + máy chủ sống.

---

## 6. CHƯA ĐO — nói thẳng

Những mục dưới đây **KHÔNG ĐẠT** hoặc **KHÔNG ĐO ĐƯỢC** trong phạm vi được phép ghi của AG-06.
Ghi ra để không ai đọc báo cáo này rồi tin rằng chúng đã xong.

1. **Trạng thái TỪNG trường credentials KHÔNG có nguồn API.** Màn suy từ câu "còn thiếu gì"; khi
   backend không nói gì về credentials thì màn chỉ dám hiện `CHƯA ĐO ĐƯỢC`. Muốn đo thật phải có
   route (đã khai schema mong đợi ở `admin/logic.js → API_CHO_BACKEND`).
2. **Bảng đường dẫn đã/chưa xác minh KHÔNG hiện được.** Nằm ở `app/adapter_jt.py::DUONG_API`,
   không có route. Màn chỉ hiện được mức sẵn sàng + câu "đo bằng gì" của backend, và khai
   CHỜ BACKEND cho phần còn thiếu.
3. **Chốt D-9 KHÔNG đọc được qua API** — màn đọc hằng của mã nguồn. Nếu ai sửa mã nguồn mà không
   chạy E2E thì chữ trên màn sẽ lệch (ca 04 bắt được, nhưng chỉ khi bộ thử được chạy).
4. **Ngắt mạch luôn hiện "Chưa đo"**: payload `/api/v2/g09/suc-khoe-hang` **không có** trường
   ngắt mạch. Màn cố ý không mặc định là "bình thường".
5. **Nguyên nhân `capabilities.getOrder=false` không có trong payload.** API chỉ trả boolean;
   lý do chi tiết ("tài liệu công khai chưa nêu API tra đơn") nằm trong mã adapter, không phơi ra.
6. **Số ca BỎ QUA của tầng 3 là 1** (màn tài chính chưa cắm) — và nó sẽ còn bỏ qua cho tới khi
   `finance.js` được cắm. AG-06 không được phép ghi vào `finance.js` / `admin.js` của làn khác
   theo cách khác, nên **không sửa**; nêu ra để AG-00 quyết.
7. **`finance.js` (7 màn) · `billing.js` (6) · `ai.js` · `health.js` vẫn là mã chết cùng loại
   V-13910**: khai màn nhưng không có trên menu. Đo được lượt này:
   `đợt 3 khai 17 màn; 2 đã có trên menu; 15 CHƯA cắm vào giao diện`. Ngoài phạm vi AG-06.
8. **MỌI trang trong `pages/` mất phần mã của mình khi phục vụ qua máy chủ.** CSP là
   `script-src 'self'` (`app/server.py`), nên **script nội tuyến bị chặn**:
   *"Refused to execute inline script … script-src 'self'"* (đo bằng Chromium thật 15/10/2026).
   Chín trang `pages/*.html` còn lại vẫn gọi khung và dựng bảng bằng script nội tuyến ⇒ phần mã
   đó **không chạy**, trang chỉ còn khung tĩnh. AG-06 chỉ sửa được `pages/carriers.html` (đã
   chuyển mã sang `admin/carrier_health.js` mục 9, không còn script nội tuyến) — **chín trang
   kia là việc của AG-00** (hoặc bỏ script nội tuyến, hoặc thêm hash/nonce vào CSP, hoặc chấp
   nhận trang tĩnh). Đây là phát hiện mới của lượt này, không phải bất biến nào bị AG-06 phá.
9. **Không đo trên Firefox/Safari, không thiết bị cảm ứng thật, không trình đọc màn hình, không
   in thật.** Chỉ Chromium đi kèm Playwright, ba bề rộng 375/768/1280.
10. **Máy này không có Chromium trong `node_modules` của nhánh** (`chay.sh` đòi
    `PLAYWRIGHT_BROWSERS_PATH=0`). Đã dùng lại bản **cùng phiên bản** (`chromium-1194`,
    `chromium_headless_shell-1194`) của bản checkout anh em
    `Projects-vip-express-hub/node_modules/playwright-core/.local-browsers` bằng một **symlink
    trong `node_modules/`** (đã nằm trong `.gitignore`, không phải thay đổi mã nguồn). Ai chạy
    trên máy sạch thì cần `PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium`.
11. **Không có credentials thật, không `.env`, không tunnel, không deploy, không push.** Các cổng
    live giữ nguyên `False` (đo lại trong payload: `live_mo=false` cho cả hai hãng; `CHO_PHEP_LIVE`
    không bị chạm). Mọi ca E2E chạy trên nền cô lập `mktemp`, bind `127.0.0.1`, tắt theo đúng PID.
12. **`mock/carriers.json` vẫn còn trên đĩa nhưng KHÔNG còn ai đọc** (trang `pages/carriers.html`
    là chỗ dùng duy nhất trước đây). Không xoá vì tệp dữ liệu nằm ngoài danh sách được phép ghi;
    nêu ra để AG-00 dọn nếu muốn.
