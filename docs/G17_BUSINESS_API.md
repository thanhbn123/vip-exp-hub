# G17 / AG-03 — J&T BUSINESS API: CA PHỦ ĐỊNH, BIÊN, VÀ CHỐT CỨNG BỐN ĐƯỜNG CHƯA XÁC MINH

Làn: **AG-03** · WAVE **G17** · nền: `integration/g16` @ `98baeb3`
Tệp được phép ghi: `app/adapter_jt.py` · `app/thu/thu_adapter_jt.py` · `app/thu/thu_hop_dong_jt.py` ·
`docs/G17_BUSINESS_API.md` (tệp này).

---

## 0. TÓM TẮT CHO NGƯỜI ĐỌC BẬN

| Việc | Trước | Sau |
|---|---|---|
| Số ca `thu_adapter_jt.py` | 71 | **84** |
| Số ca `thu_hop_dong_jt.py` | 64 | **84** |
| Nhánh **MÃ LẠ** đo được qua đường adapter thật | không (chỉ gọi thẳng hàm đọc gói) | **có** — 5/5 thao tác |
| Chốt bốn đường chưa xác minh | ca kiểm đọc `duong is None` | **ca canh + chốt trong MÃ**, đã chứng minh ĐỎ khi gán bừa URL |
| Biên `tien_nguyen_vnd` với chữ số không-ASCII | `"²"` ⇒ **ValueError TRẦN**; `"١٢٣"` ⇒ **đổi im lặng thành "123"** | cả hai ⇒ `THAM_SO_SAI`, không đổi giá trị |
| Số đột biến bộ thử bắt được | chưa đo | **10/10** |

**Không có lượt gọi hãng nào — kể cả sandbox.** Mọi phép đo dùng mã trong bộ nhớ, tệp trên đĩa,
và stub cục bộ `127.0.0.1` cổng 0 (nhóm H của AG-02). `V-G09-01` + `V-13906-05` **CHƯA CẤP**.

---

## 1. NHIỆM VỤ 2 — CHỐT CỨNG BỐN ĐƯỜNG CHƯA XÁC MINH

### 1.1 Bốn thao tác và tình trạng tài liệu

| Thao tác | Tên trang tài liệu | `duong` | `muc` | Còn thiếu gì |
|---|---|---|---|---|
| `cancelOrder` | `cancelOrder` | `None` | `chua-xac-nhan` | **tiền tố cổng** (`/webopenplatformapi`?) + **TÊN trường lý do huỷ** |
| `getShippingFee` | `calculatingFees` | `None` | `chua-xac-nhan` | đường dẫn yêu cầu + bảng tham số |
| `getShippingLabel` | `printOrder` | `None` | `chua-xac-nhan` | đường dẫn yêu cầu (`apiDoc/vip/printOrder`) |
| `getOrder` | *(chưa có trang nào)* | `None` | `chua-xac-nhan` | tài liệu công khai chưa nêu API tra đơn theo `txlogisticId` (câu hỏi 26) |

`cancelOrder` là ca nguy hiểm nhất vì nó **gần đúng**: câu 27 của
`docs/JT_CAU_HOI_CHINH_THUC.md` chép được đường dẫn ở dạng **tương đối**
(`/api/order/cancelOrder`). Ghép tiền tố cổng vào là một phép **đoán** — và đoán sai thì hãng trả
404/mã lỗi khó tra, rồi người trực ca đi chẩn đoán nhầm hướng. Đường dẫn tương đối vẫn được **GHI
LẠI** (`DUONG_API["cancelOrder"]["duong_tuong_doi_da_doc"]`) và ca `HĐ.K5` ghim nó lại, nhưng nó
**không bao giờ** được dùng để dựng URL.

### 1.2 Chốt nằm ở BA tầng, không phải một

1. **Lời khai** — `THAO_TAC_CHUA_XAC_MINH` + `duong=None` + `muc=chua-xac-nhan`.
2. **Mã chạy** — `duong_da_xac_minh(thao_tac)` đòi **đồng thời** `muc == MUC_DA_DOC` **và** có
   `duong` bắt đầu bằng `/`. `url_cua()` đi qua hàm này ở **mọi** nhánh, kể cả nhánh ghi-đè điểm
   cuối của bộ thử. Trước AG-03, nhánh ghi-đè đọc thẳng `DUONG_API[..]["duong"]` — nên **một dòng
   `duong` điền nhầm là đủ** để thao tác chưa xác minh có URL thật trong lúc chạy bộ thử.
3. **Bộ dò** — `vi_pham_chot_duong_dan(bang=None)` trả về danh sách **lời khai sai**; nó bắt ba
   kiểu hỏng: gán `duong`, đổi `muc` mà không có đường dẫn, và **xoá hẳn dòng** khỏi bảng.
   Khi bảng tự mâu thuẫn, `chan_duong_chua_xac_nhan` còn **nói ra mâu thuẫn đó** trong lý do chặn
   (dòng `BẢNG TỰ MÂU THUẪN: …`) thay vì chỉ nói "chưa xác minh".

### 1.3 BẰNG CHỨNG: ca canh ĐỎ thật khi ai đó gán bừa một URL

Đây là điều kiện của nhiệm vụ ("ca này phải ĐỎ nếu ai đó gán bừa một URL"), nên nó được đo bằng
cách **gán bừa thật rồi chạy lại**, không phải bằng lời hứa:

```
$ python3 - <<'PY'      # gán bừa URL vào bảng THẬT của module
...  DUONG_API["cancelOrder"]["duong"] = "/webopenplatformapi/api/order/cancelOrder"
PY
$ python3 app/thu/thu_hop_dong_jt.py ; echo "mã thoát $?"
```

Kết quả thật (7 ca ĐỎ, mã thoát `1`):

```
FAIL: test_b2_muc_xac_nhan_tung_thao_tac (B_DuongDanDaXacMinh)
FAIL: test_e11_khong_them_duong_dan_nao_moi (E_ChotChanDuongDanChuaXacMinh)
FAIL: test_k1_bang_that_hien_tai_sach (K_ChotCungBonDuongChuaXacMinh)
FAIL: test_k2_TU_KIEM_bo_do_THAT_SU_bat_duoc_URL_bua (K_ChotCungBonDuongChuaXacMinh)
FAIL: test_k3_bom_URL_bua_vao_MODULE_DANG_CHAY_thi_duong_chay_VAN_tu_choi (K_ChotCungBonDuongChuaXacMinh)
FAIL: test_k4_bon_thao_tac_giu_None_va_muc_chua_xac_nhan (K_ChotCungBonDuongChuaXacMinh)
FAIL: test_k5_khong_moi_truong_nao_co_URL_cho_bon_thao_tac_nay (K_ChotCungBonDuongChuaXacMinh)
```

Sau khi trả lại bảng gốc: `Ran 84 tests … OK`, `sha256` của `app/adapter_jt.py` **khớp bản gốc**
(`453b2f6b8965c57da5ac0ad17db53d16a1dfc79e8631cdd703946186a1f02817`).

`HĐ.test_k3` là ca mạnh nhất: nó sửa **chính bảng của module đang chạy** rồi đo **đường chạy**, và
đòi hai điều cùng lúc — bộ dò phải kêu, **và** `url_cua()` vẫn phải trả `None` (kể cả dưới
`DungDiemCuoiTam`). Nghĩa là: chưa kịp có ai chạy bộ thử thì cũng đã không có lượt gọi nào đi ra.

`HĐ.test_k7` quét thêm **NGUỒN** (`quet_url_bua`): một URL dán thẳng vào một hàm, không đi qua bảng,
cũng bị bắt. Bộ dò có ca TỰ KIỂM bơm URL bừa để chứng minh nó thật sự dò được.

---

## 2. NHIỆM VỤ 1 — CA PHỦ ĐỊNH VÀ BIÊN, MỖI CA CÓ ĐỐI CHỨNG DƯƠNG

### 2.1 Nguyên tắc: mỗi phủ định đi KÈM đối chứng, cùng một chỗ gọi

Một ca phủ định đứng một mình chỉ chứng minh **"có ném"**. Nó vẫn xanh kể cả khi nhánh đó chặn
nhầm mọi thứ. Nên mỗi phủ định ở đây được gói với **đối chứng dương của chính nó**, chỉ khác
đúng một que kích hoạt (helper `J_PhuDinhVaDoiChungDuong._cap`).

**Chú giải tên ca** (hai tệp đều có lớp `I`/`J`/`K`, nên mọi tham chiếu ở đây mang tiền tố):
`HĐ.` = `app/thu/thu_hop_dong_jt.py` · `AD.` = `app/thu/thu_adapter_jt.py`.

### 2.2 Sáu nhánh được yêu cầu — và chúng được đo ở đâu

| Nhánh | Ở mock, qua đường adapter thật | Đối chứng dương |
|---|---|---|
| **Thiếu trường hành chính** | `HĐ.I1..I3` (thiếu TỪNG cột, rỗng/khoảng trắng/`None`), `HĐ.I4`, `HĐ.I6` | `HĐ.I1` điền lại đúng cột đó; `HĐ.I3` đơn đủ ⇒ **không có** khoá `thieu_truong`; `HĐ.I5` đơn đủ đi QUA cửa hành chính |
| **Sai định dạng tiền** | `HĐ.J1` (14 dạng hỏng), `HĐ.J6` (cả 3 trường tiền), `HĐ.J7` (mock không dễ dãi hơn) | `HĐ.J1` dạng hợp lệ **gần nhất** đi qua, ra đúng chuỗi; `HĐ.J4` biên 0 và số nguyên lớn |
| **Đơn trùng** | `AD.J6` (sổ mô phỏng), `AD.J1` (que `demo_force_trung`) | `AD.J6` **tắt sổ** ⇒ cùng `ma_don` tạo được **hai** lượt |
| **Hãng từ chối thật** | `AD.J1..J5` — cả 5 thao tác | cùng chỗ gọi, bỏ que ⇒ `ok=True`, `timeout=False` |
| **Hết giờ** | `AD.J1..J5` — cả 5 thao tác | như trên; và mã `HET_GIO` là mã **duy nhất** có `co_the_thu_lai=True` |
| **Mã lạ** | `AD.J1..J5` (5/5 thao tác) + `AD.K1`, `AD.K3`, `AD.K5` | `AD.K2`: sáu mã **đã đọc được** ra đúng nghĩa, không rơi vào `KHONG_RO` |

### 2.3 MÃ LẠ: nhánh mới, và vì sao nó phải mới

Trước AG-03, "mã lạ" chỉ đo được bằng cách gọi **thẳng** `aj.doc_goi_tra_loi({...})`. Đó là đo
hàm đọc gói, **không** đo nhánh mà một mã lạ thật sẽ đi qua: `createOrder`/`cancelOrder`/… có tự
chuyển mã lạ thành một kết cục đúng không, có thử lại không, có gộp nó vào "không tìm thấy" không.
AG-03 thêm một que kích hoạt (`demo_force_ma_la` / tiền tố `MOCK-MALA`) chạy qua **chính**
`loi_hang.doc_tra_loi_jt` — không có nhánh tắt nào cho bộ thử.

Ghim lại:

* mã lạ ⇒ `KHONG_RO`, `co_the_thu_lai=False` (thử lại một mã chưa hiểu là gửi thêm lượt mà không
  học được gì), `ma_van_don=None`, và **không** bị gán cho `DON_TRUNG` / `KHONG_TIM_THAY` /
  `HANG_TU_CHOI` / `XAC_THUC_HONG` / `THAM_SO_SAI`;
* `AD.K3` chứng minh mã dùng cho kịch bản **thật sự** không có trong `loi_hang.JT_MA_LOI` — nếu không
  thì "mã lạ" chỉ là một mã đã biết đội lốt;
* `MA_LA_DU_LIEU_THU = "999999999"` là **dữ liệu thử**, không phải lời khai về mã của J&T, và được
  ghi rõ như vậy trong mã.

### 2.4 BIÊN tiền — hai lỗi THẬT đã đo được và đã vá

Đo bằng lệnh thật trên chính Python đang chạy (`HĐ.J2` ghim lại tiền đề này):

```
'²'.isdigit()  → True      int('²')  → ValueError: invalid literal for int() with base 10: '²'
'١٢٣'.isdigit() → True     int('١٢٣') → 123        (chữ số Ả Rập)
'１５００'.isdigit() → True  int('１５００') → 1500   (chữ số toàn phần)
```

Hệ quả trên **đường cũ** `if not chuoi.isdigit(): … else: n = int(chuoi)`:

1. `tien_nguyen_vnd("²", "cod")` ném **`ValueError` TRẦN** — phá hợp đồng §5 (mọi lỗi tham số phải
   ra `NormalizedCarrierError` / `THAM_SO_SAI`). Nơi gọi bắt đúng loại ngoại lệ theo hợp đồng sẽ
   **để lọt** nó ra ngoài.
2. `tien_nguyen_vnd("١٢٣", "cod")` trả **123** — tiền bị **ĐỔI IM LẶNG** rồi gửi lên hãng. Đúng
   khuôn "sửa im lặng" mà chính hàm này sinh ra để chặn.

Bản vá: đòi **chữ số ASCII**. Không-ASCII ⇒ `THAM_SO_SAI` kèm lý do đọc được, **không** tự đổi
sang số. `HĐ.J1` để dạng hỏng ngay cạnh dạng hợp lệ (`"²"` ↔ `"2"`, `"١٢٣"` ↔ `"123"`), nên nếu ai
gỡ bản vá thì ca **ĐỎ** — đã chứng minh bằng đột biến **M3** (2 hỏng + 2 lỗi).

### 2.5 GIỚI HẠN ĐÃ ĐO, ghi lại thay vì giấu (`HĐ.J5`)

`tien_nguyen_vnd(9007199254740993.0)` **KHÔNG** ném: giá trị đã thành `…992.0` từ **trước**, ở chỗ
gọi, và thông tin đã mất — không hàm nào đọc lại được. Hàm kiểm vẫn đúng (nó nhận được một số
nguyên); chỗ hở nằm ở **đường ống**: tiền đi vào bằng `float` có thể lệch 1 đồng mà không ai báo.

* Đường **đúng** (`int`, hoặc chuỗi) được đo ngay cạnh và **giữ nguyên** giá trị.
* `float` **có phần lẻ** vẫn bị chặn như cũ.
* Việc còn lại: chặn `float` ở tầng nhập liệu là việc của Order Service — **NẰM NGOÀI** phạm vi
  `app/adapter_jt.py`. Ghi vào mục **NEEDS_REVIEW** (§6).

---

## 3. NHIỆM VỤ 3 — CÁC BẤT BIẾN ĐƯỢC GIỮ NGUYÊN (không sửa một dòng nào)

| Bất biến | Chỗ giữ | Ca ghim |
|---|---|---|
| `digest = base64(md5_BYTES(bizContent + privateKey))` | `ky_digest` | `HĐ.A1` (vector đáp án biết trước, tính ngoài bộ thử), `HĐ.A2`, `HĐ.A9`, `HĐ.A10` |
| Mốc **ms UTC+7 độc lập múi giờ MÁY** | `dau_thoi_gian_ms` — naive được gắn UTC+7 tường minh | `HĐ.A5`, `HĐ.A13` (đo bằng **tiến trình con** với `TZ=Asia/Ho_Chi_Minh` / `UTC` / `America/New_York`, đòi **cùng một con số**) |
| **COD đi `codMoney`**, KHÔNG BAO GIỜ `itemsValue` | `_dung_bizcontent_tao_don` | `HĐ.C1..C3` |
| Chốt **D-9** `city`/`area` CHẶN CỨNG ngoài mock | `chot_chan_anh_xa_area`, gọi tại chỗ dựng `bizContent` | `HĐ.D1..D7`, `HĐ.I5` (đối chứng **phân biệt**: đơn đủ địa chỉ đi **qua** cửa hành chính rồi mới dừng ở D-9) |
| **Không đoán mã `110`** (D-4) | adapter **không** phát `110`; `110` vẫn nằm trong sổ `NHAP_NHANG` của `trang_thai_hang` | `AD.K4`, `AD.K5`, `AD.K6` |
| Adapter KHÔNG chuyển CSDL sang PostgreSQL (D-8) | không đụng gì tới CSDL | — |
| Không mở `CHO_PHEP_LIVE`, không sửa cờ sandbox/production | `adapter_jt.py` chỉ **đọc** `cau_hinh` | `AD.G1..G5`, `HĐ.H1..H9` |

Về `110`: `polling.py` đọc thẳng `kq.tho["trang_thai"]` (mã **thô** của hãng) rồi đưa vào
`trang_thai_hang.quyet_dinh`. Nên bất biến của **adapter** là: phát mã thô, **không** tự dịch.
`AD.K5` ghim "adapter chỉ phát `112`", `AD.K6` ghim "phát **số**, không phát tên chuẩn" (đã từng có lỗi
này: mock trả `"dang_giao"` ⇒ mọi vòng polling thành "mã lạ"), `AD.K4` ghim rằng nếu hãng đẩy `110`
vào thì tầng ánh xạ **từ chối** áp trạng thái và **đánh dấu cần soát**.

---

## 4. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA THẬT

```
$ python3 app/thu/thu_hop_dong_jt.py ; echo "mã thoát $?"
Ran 84 tests in 0.151s
OK
Tổng: 84 ca · hỏng 0 · lỗi 0 · bỏ qua 0
mã thoát 0

$ python3 app/thu/thu_adapter_jt.py ; echo "mã thoát $?"
Ran 84 tests in 2.879s
OK
Tổng: 84 ca · hỏng 0 · lỗi 0 · bỏ qua 0
mã thoát 0
```

Trước AG-03 (cùng hai tệp, đo lại trên nền `98baeb3`): `thu_adapter_jt.py` **71 ca**,
`thu_hop_dong_jt.py` **64 ca**. Chênh lệch khớp đúng số ca thêm vào:

* `thu_hop_dong_jt.py`: `I` 6 ca + `J` 7 ca + `K` 7 ca = **20** → 64 + 20 = 84 ✔
* `thu_adapter_jt.py`: `J` 7 ca + `K` 6 ca = **13** → 71 + 13 = 84 ✔

Bộ chạy tự do toàn dự án: xem §4.3.

### 4.1 ĐỘT BIẾN — chứng minh các ca MỚI có răng

Một ca thử xanh không chứng minh nó **đo được** gì; nó chỉ chứng minh chưa ai sửa sai. Cách duy
nhất để biết một ca có răng là **làm nó đỏ được**: sửa mã theo đúng khuôn sai mà ca đó tuyên bố
canh, chạy lại, đòi nó hỏng. Đã chạy **10 đột biến**, **10/10 bị bắt**:

| # | Đột biến bơm vào `app/adapter_jt.py` | Bộ thử phải ĐỎ | Kết quả đo được |
|---|---|---|---|
| M1 | gán bừa URL cho `cancelOrder` (giữ `muc` = chưa xác nhận) | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **7 hỏng** |
| M2 | khai `getOrder` là ĐÃ xác minh mà không có đường dẫn | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **6 hỏng** |
| M3 | bỏ vá biên chữ số không-ASCII | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **2 hỏng + 2 lỗi** |
| M4 | thôi chặn thiếu trường hành chính | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **2 hỏng + 1 lỗi** |
| M5 | bỏ nhánh MÃ LẠ của `createOrder` | `thu_adapter_jt` | ĐỎ · mã thoát 1 · **2 hỏng** |
| M6 | mock phát mã trạng thái `110` (D-4) | `thu_adapter_jt` | ĐỎ · mã thoát 1 · **4 hỏng** |
| M7 | đổi COD sang `itemsValue` | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **2 hỏng + 21 lỗi** |
| M8 | bỏ chốt D-9 cho mọi môi trường | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **3 hỏng + 1 lỗi** |
| M9 | đổi chữ ký sang `md5 hexdigest` rồi base64 | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **3 hỏng** |
| M10 | bỏ mốc UTC+7 tường minh cho mốc naive | `thu_hop_dong_jt` | ĐỎ · mã thoát 1 · **1 hỏng** |

Trước và sau mỗi đột biến, hai bộ thử đều **XANH** (mã thoát 0) — nếu không thì phép đo vô nghĩa.
Script tự so `sha256` và in `hoàn tác OK — sha256=453b2f6b…` (khớp bản gốc); **không đột biến nào
được để lại trên đĩa**.

M10 đáng chú ý: ca `A13` bắt được nó vì ca đó chạy **tiến trình con** với ba múi giờ khác nhau —
tức bất biến "độc lập múi giờ máy" có bằng chứng, không chỉ có docstring.

### 4.2 CÁC CA TỰ KIỂM (chống "xanh vì bộ dò hỏng")

Mọi bộ dò mới đều có ca chứng minh **nó dò được**, để ca chính không xanh một cách vô nghĩa:

* `K2` — bơm URL bừa / bơm `muc` sai / xoá dòng khỏi bảng **GIẢ** ⇒ bộ dò phải kêu; và bảng giả
  **không** bơm gì ⇒ bộ dò phải im.
* `K7` — `quet_url_bua` phải bắt được URL tuyệt đối của `cancelOrder` và `printOrder`, và phải
  **im** với URL của `addOrder` (đối chứng âm).
* `J2` — chứng minh ba dạng hỏng của `J1` **thật sự** đánh lừa được `isdigit()`.
* `J7` — năm que kích hoạt của `createOrder` phải cho **năm dấu vết khác nhau**; nếu hai que rơi
  vào một nhánh thì mọi ca phủ định ở nhóm J xanh mà không đo gì.
* `J4` — chứng minh tiền đề số học (`int(float(2**53+1)) != 2**53+1`) trước khi kết luận từ nó.

### 4.3 BỘ CHẠY TỰ DO TOÀN DỰ ÁN

`app/thu/chay_tat_ca.sh` là **script shell** (`#!/bin/sh`) — chạy bằng `sh`, không phải `python3`
(`python3 app/thu/chay_tat_ca.sh` chết ngay bằng `SyntaxError`, đã đo).

```
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 \
      -u GIT_CONFIG_KEY_1 -u GIT_CONFIG_VALUE_1 sh app/thu/chay_tat_ca.sh ; echo "mã thoát $?"
  ✓ thu_adapter_jt.py          84 ca
  ✓ thu_hop_dong_jt.py         84 ca
  …
  python:   1317 ca · 36 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41 phép đo đạt
  bộ hỏng:  KHÔNG
mã thoát 0
```

Ghi chú trung thực về **số ca**: hai lượt chạy trên **cùng cây mã** cho `python: 1299 ca` và
`python: 1317 ca`. Chênh lệch nằm ở `thu_bao_mat.py` (**39 ca** một lượt, **57 ca** lượt khác —
chạy riêng cũng ra 57), tức bộ đó sinh ca theo môi trường/thời điểm. **Cả hai lượt đều xanh** và
`bộ hỏng: KHÔNG`; đây là quan sát của làn AG-03 về một bộ thử **của làn khác**, ghi lại chứ không
sửa. Con số của hai bộ thuộc làn này thì ổn định: **84 ca** mỗi bộ, ở mọi lượt đo.

#### 4.3.1 MỘT LỖI CỦA MÔI TRƯỜNG CHẠY, KHÔNG PHẢI CỦA MÃ — ghi lại để không ai đo lại

Chạy y hệt lệnh trên nhưng **giữ nguyên** biến môi trường của harness thì kết quả là `mã thoát 1`,
với **đúng hai** bộ hỏng và **cả hai đều hỏng vì `git` trả mã thoát 128**:

```
  ✗ thu_bao_mat.py             57 ca  HỎNG (mã thoát 1)
        FAIL: test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git
        AssertionError: 128 != 0 : git KHÔNG chặn app/du-lieu/khoa-noi-bo.key
  ✗ thu_tich_hop.py            12 ca  HỎNG (mã thoát 1)
        FAIL: test_04_khoa_ma_hoa_khong_duoc_vao_git
        FAIL: test_11_khong_co_secret_that_trong_cay_lam_viec
        AssertionError: 128 != 0 : .env KHÔNG bị gitignore
```

Nguyên nhân, đo bằng lệnh thật:

```
$ env | grep '^GIT_CONFIG'
GIT_CONFIG_VALUE_0=false
GIT_CONFIG_VALUE_1=false
GIT_CONFIG_COUNT=2          # khai 2 mục nhưng THIẾU GIT_CONFIG_KEY_0 / _1

$ git check-ignore -q .env ; echo "exit=$?"
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
exit=128
```

Harness đặt `GIT_CONFIG_COUNT=2` mà **không** đặt `GIT_CONFIG_KEY_0`/`GIT_CONFIG_KEY_1`, nên **mọi**
lượt gọi `git` đều chết với 128 — kể cả `git status`. Hai bộ thử kia đọc 128 thành "git KHÔNG
chặn".

Đây là lỗi **của MÔI TRƯỜNG, không phải của mã** — và chứng minh được mà không cần chạm vào tệp
nào. Đo cùng một lệnh trên **ba đường dẫn khác nhau**, trong đó `README.md` là tệp làn này
**không hề sửa** và hiển nhiên không bị ignore:

```
$ for f in README.md .env app/du-lieu/khoa-noi-bo.key; do
      printf '%-34s env hỏng -> '  "$f"; git check-ignore -q "$f" 2>/dev/null; printf '%s' "$?"
      printf ' | env sạch -> '; env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 \
          -u GIT_CONFIG_KEY_1 -u GIT_CONFIG_VALUE_1 git check-ignore -q "$f" 2>/dev/null; echo "$?"
  done
README.md                          env hỏng -> 128 | env sạch -> 1
.env                               env hỏng -> 128 | env sạch -> 0
app/du-lieu/khoa-noi-bo.key        env hỏng -> 128 | env sạch -> 0
```

`128` cho **cả ba**, kể cả `README.md` ⇒ mã thoát đó không nói gì về gitignore; nó là `git` không
chạy được. Với môi trường `git` sạch, **cả hai bộ đều xanh**:

```
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_KEY_0 -u GIT_CONFIG_VALUE_0 \
      -u GIT_CONFIG_KEY_1 -u GIT_CONFIG_VALUE_1 python3 app/thu/thu_bao_mat.py
Ran 57 tests in 5.043s
OK                    → mã thoát 0

$ env -u … python3 app/thu/thu_tich_hop.py
Ran 12 tests in 0.260s
OK                    → mã thoát 0
```

Cách chạy đúng trong harness này là gỡ năm biến `GIT_CONFIG_*` trước khi chạy — **không** sửa hai
bộ thử của làn khác để chúng chấp nhận `128`, vì như vậy là dạy bộ thử coi "git không chạy được"
là "git đã chặn".

---

## 5. CÁI GÌ NẰM NGOÀI PHẠM VI ĐÃ ĐO

Nói thẳng, để không ai đọc bảng xanh ở §4 rồi suy rộng:

* **J&T thật có chấp nhận chữ ký / tham số này không** — CHƯA ĐO. Không có lượt gọi hãng nào.
* **Mã lỗi thật của hãng có đúng như bảng đã đọc không**, và **sandbox hãng có sống không** —
  CHƯA ĐO (`V-G09-01` + `V-13906-05` chưa cấp).
* **Đường dẫn của `cancelOrder` / `calculatingFees` / `printOrder` / `getOrder`** — vẫn CHƯA xác
  minh. AG-03 **không** thêm đường dẫn nào; nó làm chốt **chặt hơn**, không nới.
* **TÊN trường lý do huỷ** — vẫn RỖNG (`TRUONG_LY_DO_HUY = ""`); `cancelOrder` ở mock ghi nó vào
  `thieu_truong`, ngoài mock DỪNG.
* **Nghĩa mã `110`** (D-4) — vẫn chưa chốt; AG-03 **không** thêm mã nào vào bảng ánh xạ.
* **Cách ánh xạ `area`** (D-9) — vẫn là giả định, chốt chặn còn nguyên.
* **Tiền `float` mất độ chính xác TRƯỚC khi vào adapter** (§2.5) — đã đo, chưa vá; thuộc tầng nhập
  liệu của Order Service.
* **CSDL nghiệp vụ** — vẫn SQLite (D-8); AG-03 không đụng tới.
* **Callback/webhook của hãng ký bằng khoá nào**, **nhãn hãng thật**, **AI thật**, **dữ liệu lớn**,
  **nhiều tiến trình**, **DOM/CSS trong trình duyệt thật** — nằm ngoài phạm vi làn này.

**KHÔNG được báo "LIVE VERIFIED"** cho bất kỳ phần nào ở trên.

---

## 6. NEEDS_REVIEW

| # | Việc | Vì sao | Ai |
|---|---|---|---|
| 1 | Nghĩa mã trạng thái `110` | D-4: tài liệu J&T tự mâu thuẫn (bảng tham số vs. ví dụ trả lời). AG-03 **không** đoán, chỉ ghim lại | J&T |
| 2 | Tiền đi vào bằng `float` có thể lệch 1 đồng **trước** khi adapter kiểm (§2.5) | Đã đo; chặn ở tầng nhập liệu là việc của Order Service, không phải adapter | Order Service |
| 3 | Tiền là **chữ số ASCII** — dữ liệu vào có chữ số không-ASCII nay bị TỪ CHỐI thay vì đổi im lặng | Đây là **thay đổi hành vi** so với trước (trước: `"١٢٣"` ⇒ `123`). Nếu có nguồn dữ liệu hợp lệ dùng chữ số không-ASCII thì phải chuẩn hoá ở tầng nhập, **không** nới chỗ này | Order Service |
| 4 | Đường dẫn + tên trường của 4 thao tác còn thiếu | Cần tài liệu/hãng trả lời; có rồi thì điền `DUONG_API`, đổi `muc`, và **gỡ tên khỏi `THAO_TAC_CHUA_XAC_MINH`** — ca canh sẽ ĐỎ cho tới khi làm đủ cả ba | J&T |

---

## 7. PHẠM VI ĐÃ ĐO (nguyên văn từ bộ chạy tự do)

```
══════════ BỘ THỬ PYTHON (unittest) ══════════
  ✓ thu_adapter_jt.py          84 ca
  ✓ thu_hop_dong_jt.py         84 ca
  (34 bộ còn lại: xem nhật ký chạy — tất cả ✓)
══════════ FRONTEND ══════════
  tầng 1 (logic thuần, node):    56 ca
  tầng 2 (HTTP + tệp tĩnh):      36 ca
  tầng 3 (DOM/CSS trong Chromium thật): CÓ, nhưng KHÔNG chạy ở đây
══════════ E2E QUA HTTP THẬT ══════════
  ✓ KẾT QUẢ: 41/41 phép đo đạt
══════════════════════════════════════════════════════════
  python:   1317 ca · 36 bộ chạy thật
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

**PHẠM VI CỦA RIÊNG LÀN AG-03** (hẹp hơn nhiều, đọc đúng dòng này):

* **đo trên:** ba tệp của làn này, chạy trên Python 3.9.6 / Darwin arm64.
* **cách đo:** gọi hàm trong bộ nhớ + đọc tệp trên đĩa + **đột biến mã rồi chạy lại**.
* **KHÔNG đo:** bất kỳ lượt gọi hãng nào (kể cả sandbox) · chữ ký/tham số có được hãng chấp nhận
  không · bốn đường dẫn còn thiếu có đúng không · nghĩa mã `110` · cách ánh xạ `area` ·
  credentials thật.

**⇒ KHÔNG được báo "LIVE VERIFIED".** `V-G09-01` và `V-13906-05` **CHƯA CẤP**.
