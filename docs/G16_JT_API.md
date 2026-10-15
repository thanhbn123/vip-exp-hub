# G16-A — ADAPTER J&T NỐI VÀO LỚP HTTP THẬT: ĐÃ LÀM GÌ · ĐO ĐƯỢC GÌ · CÒN CHẶN GÌ

**Người làm:** AG-03 · J&T BUSINESS API ENGINEER · **ngày** 15/10/2026
**Nền:** `integration/g13-g15` @ **`449bb2d`** (G13–G15 **CHƯA** merge vào `main`; `main` = `de740dc`)
**Tệp được ghi trong lượt này:** `app/adapter_jt.py` · `app/thu/thu_adapter_jt.py` ·
`app/thu/thu_hop_dong_jt.py` · `docs/G16_JT_API.md` (tệp này)
**KHÔNG ghi** (theo §39): `app/http_jt.py` · `app/thu/stub_jt.py` · `app/thu/thu_http_jt.py`
(AG-02) · `app/webhook.py` (AG-04) · `app/csdl.py` · `app/migrate.py` · `app/server.py` ·
`app/cau_hinh.py` · `app/transport.py` (AG-00). Bốn làn chạy **đồng thời trong CÙNG một cây**.

> **KẾT LUẬN NGẮN, ĐỌC TRƯỚC.** Adapter J&T nay **GỌI ĐƯỢC** lớp HTTP thật qua đúng hợp đồng §36,
> và đường gửi đó **đã được đo trên socket thật** — nhưng **chỉ tới stub cục bộ `127.0.0.1`**.
> **KHÔNG có lượt gọi nào ra hãng, kể cả sandbox:** `V-G09-01` + `V-13906-05` **CHƯA CẤP**, và
> `sandbox`/`production` bị **TỪ CHỐI** ở một cửa riêng. G16-A **KHÔNG phải** và **không thể** là
> "LIVE VERIFIED" — xem §7 (BLOCKED) và §8 (NẰM NGOÀI).

---

## 1. VÌ SAO CÓ LƯỢT NÀY

G13 để lại `TRANSPORT_THAT_DA_VIET = False` và một câu nói thẳng: *"mở `CHO_PHEP_LIVE` cũng
KHÔNG chạy được vì chưa có lớp HTTP"*. G16 giao việc viết lớp đó (AG-02) và nối adapter vào nó
(làn này). Ba câu hỏi phải trả lời được bằng MÁY, không bằng chú thích:

1. Adapter có gọi **đúng** lớp HTTP theo hợp đồng §36 không, và **ba kết cục** có bị gộp không?
2. `mock` / `sandbox` / `production` đã **tách** chưa — và viết xong lớp HTTP có **vô tình mở**
   hai mức dưới không?
3. Mốc thời gian còn **lệ thuộc múi giờ máy** không (`L2-N2`), và chữ ký có phải **một** cài đặt
   đúng công thức `base64(md5_BYTES(bizContent + privateKey))` không?

---

## 2. ĐÃ LÀM — SÁU VIỆC, VÀ LÝ DO CỦA TỪNG VIỆC

### 2.1 (A) Nối vào `http_jt` — **một chỗ gửi duy nhất**

`AdapterJT._chuan_bi_goi_that(thao_tac)` kiểm **ba cửa độc lập**, theo thứ tự, mỗi cửa ném đúng
loại lỗi của nó:

| # | Cửa | Ném gì | Nguồn chân lý |
|---|---|---|---|
| 1 | Môi trường đã được Owner cấp quyền chưa | `PermissionError` | `cau_hinh.jt_kiem_moi_truong` (AG-00) |
| 2 | Đường dẫn API đã xác minh chưa | `ChuaXacNhanTaiLieu` | bảng `DUONG_API` (tệp này) |
| 3 | Lớp HTTP thật đã có trên đĩa chưa | `ChuaXacNhanTaiLieu` | dò `app/http_jt.py` mỗi lượt |
| 4 | *(không nằm ở đây)* chốt **D-9** `area` | `NormalizedCarrierError` | chỗ dựng `bizContent` |

Cửa 4 **cố ý** không nằm trong hàm này: đặt ở chỗ DỰNG `bizContent` thì nó canh được **mọi**
đường dẫn tới gói yêu cầu, kể cả đường chưa đi qua cửa gửi.

`AdapterJT._goi_that(http, thao_tac, yc)` là **chỗ duy nhất** chạm mạng:

```python
cs = transport.chinh_sach_cho(thao_tac, co_khoa_chong_trung=bool(self.KHOA_CHONG_TRUNG))
tra_loi, so_lan, nhat_ky = transport.goi(_mot_lan, thao_tac, chinh_sach=cs)
```

Việc **thử lại** do `transport.goi()` quyết định, không phải adapter và không phải lớp HTTP
(§36 luật 1). `TraLoiHTTP` → `doc_than_tra_loi(than)` → `doc_goi_tra_loi(goi, thao_tac, ma_http)`
→ `KetQuaHang`. Ngoại lệ của `transport`/`http_jt` → `KetQuaHang` **giữ nguyên ba kết cục**.

**Một chỗ lệch ĐÃ ĐƯỢC AG-00 CHỐT (15/10/2026): `408` và `429`.** `loi_hang.tu_http` nói
`408 → HET_GIO`, `429 → QUA_HAN_MUC`, **cả hai `co_the_thu_lai=True`**; còn `http_jt` (bản đầu)
xếp **mọi** 4xx là `LoiVinhVien`. Hai lớp phát hai câu trả lời cho cùng một lượt là đúng khuôn
"lệch im lặng": một lượt lẽ ra thành công — sau khi chờ đủ — bị **bỏ im lặng**.

Bản đầu của làn này chữa ở **lớp trên** (ép `co_the_thu_lai=False`). AG-00 bác đúng: đó là **chữa
triệu chứng**, và nó chỉ đổi chiều lệch. **Chốt cuối cùng:**

| Mã | Quyết định |
|---|---|
| `408` | **TẠM THỜI** — máy chủ không nhận kịp yêu cầu ⇒ chắc chắn CHƯA xử lý gì |
| `429` | **TẠM THỜI** — vượt hạn mức ⇒ "thử lại sau", KHÔNG phải "yêu cầu sai" |
| 4xx khác | **VĨNH VIỄN** — không nới |

AG-02 đã tách hai mã đó ra khỏi luật "4xx = vĩnh viễn" (`LoiTamThoi` + gợi ý `cho_giay` lấy từ
`Retry-After`); AG-00 đã làm phần enabler ở `transport.py` (`cho_giay` + trần `CHO_TOI_DA = 60.0`,
`transport.goi()` lấy **max** với backoff rồi **kẹp trần**). Làn này gỡ chỗ ép và ghim ngoại lệ
bằng **một nguồn duy nhất**:

```python
MA_HTTP_HAI_LOP_PHAI_DONG_Y = (408, 429)   # adapter KHÔNG được ép chặt hai mã này
```

Hằng này khoá theo **MÃ HTTP** — tức theo **sự thật giao thức** — chứ không theo *loại ngoại lệ*
của lớp dưới, nên nó đứng vững kể cả khi `http_jt` đổi cách cài. Nguyên tắc §5 (chỉ ép True→False)
**giữ nguyên** cho các trường hợp thật sự vĩnh viễn.

**Một ghi chú ngữ nghĩa, để không ai phải đoán:** với `429` adapter phát `timeout=False` (hãng từ
chối lượt này rõ ràng); với `408`, `loi_hang` xếp vào `HET_GIO` nên adapter phát `timeout=True`
("KHÔNG BIẾT kết quả"). Vế thứ hai là phía **THẬN TRỌNG có chủ ý**: Order Service giữ đơn ở
`dang_gui` + bật cờ đối soát, thay vì hoàn suất rồi gửi lại. Muốn đổi thì đổi ở `loi_hang.tu_http`
(tệp của AG-00), **không** đổi ở adapter — có ca thử ghim đúng bảng mong đợi này.

**Một cảnh báo kỹ thuật làn này nêu và AG-00 đã xử lý:** nếu lớp HTTP **ngủ bên trong `gui_form`**
để tôn trọng `Retry-After`, thì `transport.goi()` gọi lại tới **3 lượt** ⇒ tổng chờ = 3 × trần
(trần 30 s ⇒ 90 s treo trong một yêu cầu). AG-00 chọn đúng phương án "chỉ ném, không chờ": lớp HTTP
ném `LoiTamThoi(..., cho_giay=…)`, còn việc chờ thuộc **`transport.goi()`** — giữ đúng §36 luật 1,
và `createOrder` + gợi ý vẫn gọi **đúng 1 lần**. Làn này thêm một vế **đo hành vi**: ca `h5b`
khẳng định một lượt 408/429 (stub **không** gửi `Retry-After`) xong trong **< 5 giây**, để một hồi
quy "tự ngủ ở lớp HTTP" phải đỏ.

### 2.2 (B) Môi trường — **ba cửa ĐỘC LẬP**, `mock` là mặc định

Ban đầu làn này tự dựng một bảng quyền trong `adapter_jt.py`. **AG-00 chốt giữa kỳ 15/10/2026:**
*"đang chạy ở môi trường nào" và "được phép gọi tới đâu" là quyết định của NGƯỜI VẬN HÀNH, không
phải của mã adapter*. Bảng đó đã **GỠ**; `adapter_jt` chỉ còn hai hàm bọc mỏng gọi sang
`cau_hinh.jt_kiem_moi_truong`. **Hai bảng quyền song song là hai bảng sẽ lệch nhau.**

Ba cửa, và **mở một cửa KHÔNG mở hai cửa kia** — có ca thử cho từng cặp:

| Cửa | Ở đâu | Đang |
|---|---|---|
| 1. `CHO_PHEP_LIVE` (lớp nền, chặn lúc DỰNG adapter) | `app/adapter.py` | **False** |
| 2. `JT_CHO_PHEP_SANDBOX` / `JT_CHO_PHEP_PRODUCTION` (chặn lúc GỬI) | `app/cau_hinh.py` | **False** / **False** |
| 3. Lớp HTTP thật (§36) có trên đĩa chưa | `app/http_jt.py` | **đã có** ⇒ cờ `True` |

Cửa 2 **cố ý không đọc từ biến môi trường** (AG-00): một biến bật được là một biến bật NHẦM được.
`TRANSPORT_THAT_DA_VIET` nay là **phép DÒ**, không phải hằng viết tay:

```python
def _co_http_jt():
    try:
        import http_jt
    except ImportError:
        return None
    return http_jt if callable(getattr(http_jt, "gui_form", None)) else None

TRANSPORT_THAT_DA_VIET = _co_http_jt()     # ẢNH CHỤP lúc nạp module …
http = http_jt_dang_dung()                 # … còn đường CHẠY hỏi lại TỪNG LƯỢT
```

`import http_jt` nằm **TRONG hàm**, không ở đầu tệp: nạp ở cấp module thì lúc AG-02 chưa viết
xong, **cả adapter chết vì một tệp của làn khác**. Có ca thử soi AST để canh đúng điều đó.

### 2.3 (C) Thao tác — **hoàn thiện theo tài liệu ĐÃ XÁC NHẬN, không đoán thêm**

Bảng `DUONG_API` **không đổi một dòng nào**: `createOrder` và `trackOrder` là `da-doc`;
`cancelOrder` (tiền tố cổng chưa xác minh), `getShippingFee`, `getShippingLabel`, `getOrder`
vẫn **`duong=None` + `chua-xac-nhan`** và bị chặn ở mọi môi trường khác `mock`. Có ca thử ghim
cả sáu dòng để cám dỗ "đoán một URL cho đủ sáu thao tác" phải đỏ.

`getShippingFee` / `getShippingLabel` nay đi qua `_chuan_bi_goi_that` như mọi thao tác khác — nên
lý do DỪNG của chúng thống nhất, và nếu sau này đường dẫn được xác minh thì chúng dừng ở cửa
"chưa có hàm dựng bizContent" kèm đúng cái còn thiếu, thay vì gửi một yêu cầu rỗng.

### 2.4 (D) Chữ ký + mốc thời gian — **một cài đặt, và một phép KIỂM ĐỘC LẬP**

`ky_digest` vẫn là **nơi duy nhất** cài công thức `base64(md5_BYTES(bizContent + privateKey))`.
Thêm `kiem_chu_ky(goi_yeu_cau, credentials, luc_goi_ms=None, sai_so_ms=None)`: phép kiểm **độc
lập**, tính lại digest từ **chính chuỗi `bizContent` NẰM TRONG GÓI** rồi kiểm luôn mốc thời gian.
Nhờ vậy nó bắt được ca **"ký một chuỗi rồi gửi một chuỗi khác"** — ca mà một hàm ký tự-kiểm-chính-
mình không bao giờ thấy, và là ca làm hãng trả `145003031` (业务参数签名失败) trong khi mọi ca thử
"chữ ký đúng công thức" vẫn xanh.

**Vá `L2-N2`** (`docs/QA_G13_G15.md` §L2.2): `dau_thoi_gian_ms` gặp một `datetime` **naive** thì
nay **gắn UTC+7 tường minh** thay vì lặng lẽ theo múi giờ tiến trình. Vì sao gắn chứ không ném:
mọi lời gọi trong mã đều truyền mốc **có** `tzinfo` (đã soát), nên không ca nào đang sống bị đổi
hành vi; còn ném lỗi chỉ đổi "im lặng sai" thành "nổ ở một chỗ khác" mà không nói được mốc ĐÚNG
là gì. Gắn UTC+7 chính là điều docstring vẫn luôn hứa.

### 2.5 (E) COD — **`codMoney`, INTEGER đồng**

Không đổi công thức (G13 đã đúng); G16-A **đo lại trên dây** (§6.2): `codMoney` là **chuỗi chữ
số**, `itemsValue` **không có mặt**, `goodsValue` và `isInsured` vẫn bắt buộc. Thập phân / NaN /
inf / bool / dict / âm / chuỗi lạ ⇒ `THAM_SO_SAI`, **không làm tròn**.

### 2.6 (F) D-9 `city`/`area` — **GIỮ NGUYÊN chốt chặn cứng**

Không đổi ánh xạ, không gửi `city`, `ANH_XA_AREA_DA_XAC_NHAN = False`. Thêm ca thử **đếm**: khi
chốt D-9 nổ thì bộ đếm lượt gửi phải bằng **0** — chứng minh chốt nằm **TRƯỚC** mọi byte rời đi,
chứ không phải một lời hứa trong chú thích.

---

## 3. BỘ THỬ — CÁI GÌ ĐƯỢC ĐO, VÀ CÁI GÌ THỰC SỰ ĐO NÓ

| Nhóm | Nội dung | Ở tệp |
|---|---|---|
| A | chữ ký (vector biết trước · **byte-exactness** · `kiem_chu_ky` độc lập · mốc naive theo UTC+7 ở 3 `TZ`) | `thu_hop_dong_jt` |
| B | bảng đường dẫn: 2 mục `da-doc`, **4 mục `duong=None`** — ghim để không ai đoán URL | `thu_hop_dong_jt` |
| C | tiền/COD: `codMoney`, **cấm** `itemsValue`, thập phân/bool/âm bị TỪ CHỐI | `thu_hop_dong_jt` |
| D | D-9: giả định được GHIM, `city` không gửi, LIVE bị chặn | `thu_hop_dong_jt` |
| E | cửa đường dẫn + cửa transport, kèm **đối chứng dương** | `thu_hop_dong_jt` |
| F | adapter sạch mã gọi mạng (**AST** cho `http_jt` cấp module) + **tự kiểm bộ dò** | `thu_hop_dong_jt` |
| H | **§37**: ba cửa độc lập · môi trường lạ bị TỪ CHỐI · seam điểm cuối chỉ nhận loopback | `thu_hop_dong_jt` |
| G | credentials: `v3$…` → adapter, không tự mã hoá | `thu_hop_dong_jt` |
| A–G | hành vi mock: ba kết cục · đọc gói trả lời · chống trùng · cách ly tenant · khoá LIVE | `thu_adapter_jt` |
| **H** | **ĐƯỜNG GỬI THẬT** trên stub `127.0.0.1:0` (13 ca) — gồm **ca canh chống lệch 408/429** | `thu_adapter_jt` |
| **I** | **lớp HTTP GIẢ** đúng §36 (6 ca) — chạy được cả khi AG-02 chưa giao tệp | `thu_adapter_jt` |

**Hai chốt chặn bắt buộc của dự án (`docs/QA_G13_G15.md` §6.3) — cả hai đều có:**

1. **Tự kiểm bộ dò.** Bộ dò rò bí mật, bộ dò mã gọi mạng, bộ dò `http_jt` cấp module, bộ đếm lượt
   gửi, và phép kiểm chữ ký — **mỗi cái** có một ca chứng minh nó **bắt được** đầu vào dựng sẵn.
   Không có những ca đó thì mọi ca "sạch" chỉ là ca luôn-đúng.
2. **Đối chứng dương cho mọi ca phủ định.** Ví dụ: cửa đường dẫn chặn 4 thao tác ⇒ có ca khẳng
   định 2 thao tác đã xác minh **đi qua**; môi trường `production` bị từ chối ⇒ có ca khẳng định
   `mock` **chạy được**; "không có khoá chống trùng thì không thử lại" ⇒ có ca khẳng định **5xx
   thì thử lại đủ 3 lượt**.

**Vì sao có CẢ nhóm H lẫn nhóm I:** H là bằng chứng mạnh nhất (byte thật trên dây, do AG-02 dựng
stub); I chạy được **kể cả khi tệp của AG-02 chưa có**, và chứng minh adapter chỉ phụ thuộc **hình
dạng** §36 chứ không phụ thuộc một bản cài đặt cụ thể. Một bộ thử "xanh vì thiếu thứ để đo" là
đúng thứ §12.1 cấm.

---

## 4. BẰNG CHỨNG — LỆNH THẬT, KẾT QUẢ THẬT

`VIP_HUB_DATA=/tmp/veh_g16_ag03` cho mọi lượt dưới đây. Không lượt nào chạm mạng ra ngoài.

**VÂN TAY CÂY + MỐC GIỜ (luật §41 — bốn làn ghi đồng thời vào MỘT cây, nên con số không kèm vân
tay là con số không đối chiếu được).** Lấy bằng đúng lệnh §41, **trước và sau** mỗi lượt đo:

```
lệnh: find app gateway thu_frontend thu_giao_dien -type f \
        \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
        | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256

hai bộ thử của làn này (16:04:00 → 16:04:03 +07):
  TRƯỚC  9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df
  SAU    9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df   (KHÔNG đổi)
  ⇒ hai con số 64 và 71 ghim được vào ĐÚNG cây này.

bộ chạy tổng (16:04:07 → 16:05:17 +07), exit 0:
  TRƯỚC  9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df
  SAU    9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df   (KHÔNG đổi)
  ⇒ con số 1284 ghim được vào ĐÚNG cây này.

Đối chiếu mốc mã: `integration/g13-g15` @ `449bb2d` (nền), `main` = `de740dc` (KHÔNG chứa G13–G15).

### 4.1 Hai bộ thử của làn này

```
$ python3 app/thu/thu_hop_dong_jt.py
$ python3 app/thu/thu_hop_dong_jt.py     -> exit 0
Ran 64 tests in 0.127s
OK
Tổng: 64 ca · hỏng 0 · lỗi 0 · bỏ qua 0        (G13: 47 ca)

$ python3 app/thu/thu_adapter_jt.py      -> exit 0
Ran 71 tests in 2.928s
OK
Tổng: 71 ca · hỏng 0 · lỗi 0 · bỏ qua 0        (G13: 51 ca)
```

Nhóm H **chạy thật**, không bị bỏ qua — kiểm bằng `-v`:

```
test_h0_url_di_qua_bang_duong_dan_cua_adapter ... ok
test_h1_createOrder_thanh_cong_va_do_DUNG_BYTE_tren_day ... ok
test_h2_ba_ket_cuc_tren_day_KHONG_bi_gop ... ok
test_h3_don_trung_KHONG_thu_lai_va_Order_Service_nhan_ra ... ok
test_h4_DOI_CHUNG_khong_co_khoa_chong_trung_thi_KHONG_thu_lai ... ok
test_h5_ma_HTTP_duoc_phan_loai_chu_khong_gop_vao_THAM_SO_SAI ... ok
test_h6_danh_sach_trang_chan_host_la_va_KHONG_gui_gi ... ok
test_h7_cach_ly_tenant_tren_day_va_khong_ro_bi_mat ... ok
test_h8_COD_di_dung_truong_tren_day ... ok
test_h9_trackOrder_di_that_va_ton_trong_tran_30 ... ok
test_h10_ket_qua_that_KHONG_tu_nhan_la_mock ... ok
```

Và **ba ca canh chống lệch `408`/`429`** (AG-00 chốt 15/10/2026) — đây là thứ giữ cho chỗ lệch
không quay lại:

```
test_h5_ma_HTTP_4xx_VINH_VIEN_duoc_phan_loai_chu_khong_gop_vao_THAM_SO_SAI ... ok
test_h5b_HAI_LOP_DONG_Y_ve_408_va_429 ... ok
test_h5c_danh_sach_HAI_LOP_DONG_Y_phu_DUNG_hai_ma_va_khong_rong_hon ... ok
test_h5d_DOI_CHUNG_DUONG_co_che_ep_chat_van_con ... ok
```

`h5b` đo **cả hai lớp** cho **cả hai mã**: `http_jt` ném `LoiTamThoi` mang đúng `ma_http` **VÀ**
`loi_hang.tu_http` nói thử lại được ⇒ **ĐỒNG Ý**; rồi đo vế thứ ba ở tầng adapter (phát ra
`HET_GIO`/`QUA_HAN_MUC` với `co_the_thu_lai=True`, **không** bị ghi đè) và vế **thời gian**
(< 5 giây, chống hồi quy "tự ngủ ở lớp HTTP"). `h5d` là **đối chứng dương**: cơ chế ép chặt §5
phải **còn** — đo ở ranh giới bằng `LoiVinhVien` tổng hợp với `ma_http=503` (một mã `loi_hang`
nói thử lại được) ⇒ phải bị ép về `False`; nếu ai **gỡ hẳn** cơ chế thì ca này đỏ.

**Tự kiểm bộ dò (đột biến, đo thật):** tiêm `503` vào `MA_HTTP_HAI_LOP_PHAI_DONG_Y` — mô phỏng
đúng một bản sửa SAI — thì `ma_http=503` chuyển từ `co_the_thu_lai=False` sang `True`, tức `h5d`
**đỏ**. Không có phép đo này thì "ca canh chống lệch" chỉ là một ca luôn-đúng.

### 4.2 Một lượt gửi THẬT trên dây (stub `127.0.0.1`, cổng do hệ điều hành cấp)

```
TRANSPORT_THAT_DA_VIET = True (do tu app/http_jt.py)
cau_hinh.jt_kiem_moi_truong('sandbox')   = (False, 'sandbox CHƯA ĐƯỢC CẤP QUYỀN — cần V-G09-01…')
cau_hinh.jt_kiem_moi_truong('production')= (False, 'production KHÔNG ĐƯỢC PHÉP — cần anh Thành…')

URL gui di        : /webopenplatformapi/api/order/addOrder
phuong thuc       : POST | so luot tren day: 1
TEN header nguyen van tren day: ['Host','Accept-Encoding','Content-Length','apiAccount','digest','timestamp','Content-Type']
apiAccount        : ACC-DEMO
timestamp         : 1792054650790 (13 chu so: True)
digest tren day   : IhcgmPWU75/20htVPEOQhw==
digest tinh lai   : IhcgmPWU75/20htVPEOQhw== | KHOP: True     ← tính Ở PHÍA MÁY CHỦ, từ chuỗi nhận được
privateKey tren day: False                                    ← khoá ký KHÔNG BAO GIỜ rời đi
codMoney          : '150000' | itemsValue co mat: False
khoa chong trung  : 'G16-EVID-1'
-> ket qua        : ok = True | ma_van_don = VH000000777VN | so_lan_goi = 1 | transport = app/http_jt.py
```

### 4.3 `L2-N2` — trước và sau, đo bằng tiến trình con với ba `TZ`

```
# BẢN Ở HEAD (trước bản vá) — mốc NAIVE đổi theo múi giờ MÁY
TZ=Asia/Ho_Chi_Minh   naive(10:00) = 1792033200000
TZ=UTC                naive(10:00) = 1792058400000     ← lệch ĐÚNG 7 tiếng
TZ=America/New_York   naive(10:00) = 1792072800000     ← lệch 11 tiếng (EDT)

# BẢN ĐANG GIAO (sau bản vá) — mốc NAIVE được gắn UTC+7 tường minh
TZ=Asia/Ho_Chi_Minh   naive(10:00) = 1792033200000
TZ=UTC                naive(10:00) = 1792033200000
TZ=America/New_York   naive(10:00) = 1792033200000
```

### 4.4 Hồi quy toàn dự án

```
$ unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1; sh app/thu/chay_tat_ca.sh
  ✓ thu_adapter_jt.py          71 ca
  ✓ thu_hop_dong_jt.py         64 ca
  ✓ thu_http_jt.py             31 ca
  ✓ thu_qa_g16.py              56 ca
  ✓ thu_qa_jt.py               22 ca
  ✓ thu_webhook_jt.py          77 ca
  ...
  python:   1284 ca · 36 bộ chạy thật   (mã thoát 0)
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  KHÔNG
```

**Baseline trước lượt này** (đo sáng 15/10/2026, cùng lệnh): `1138 ca · 34 bộ · bộ hỏng: KHÔNG`.
Chênh lệch **+131 ca / +2 bộ** đến từ ba làn: làn này **+34 ca**, AG-02 `thu_http_jt.py` 31 ca,
AG-01 `thu_qa_g16.py` 56 ca.

---

## 5. TƯƠNG TÁC GIỮA CÁC LÀN (ghi lại để không ai phải đoán)

Bốn làn ghi **cùng một cây**. Ba chỗ chạm nhau, cả ba đều đã kín:

1. **AG-00 chốt giữa kỳ (§37):** cửa môi trường phải là **một** nguồn — `cau_hinh`. Làn này đã
   **gỡ** bảng quyền riêng và chỉ còn gọi sang `cau_hinh`. Đồng thời `test_g4` được viết lại
   **CHẶT HƠN** theo đúng yêu cầu của AG-00: nó nay khẳng định mở `CHO_PHEP_LIVE` **KHÔNG** làm
   `production` chạy được, lý do nêu đúng §37, **kèm đối chứng dương ở `mock`**. Bộ thử **không**
   mở `production` để tiện cho mình: đường gửi thật được đo ở **dưới** cửa môi trường.
2. **AG-02 giao `app/http_jt.py` + `app/thu/stub_jt.py` giữa lượt.** Nhóm H tự động chuyển từ
   "bỏ qua kèm lý do" sang **chạy trên tệp thật** — đúng thiết kế đã định trước. Làn này **chỉ
   gọi**, không sửa tệp của AG-02.
3. **Cờ `TRANSPORT_THAT_DA_VIET` lật `False → True`** khi tệp của AG-02 xuất hiện. Đây là **sự
   thật môi trường đổi**, không phải hồi quy — nhưng hai ca thử **ghim ảnh chụp cũ** đã đỏ trong
   lúc chuyển tiếp: `thu_qa_jt.test_a5` (AG-01) và `thu_hop_dong_jt.test_e3` (làn này).
   `test_e3` đã được thay bằng ca **đúng bất biến** ("cờ là ảnh chụp của phép dò, và **không**
   cửa nào trong ba cửa mở"), và AG-01 đã cập nhật `thu_qa_jt` tương tự — **cả hai bộ nay xanh**
   (§4.4). Bài học giữ lại: **đừng ghim một sự thật môi trường bằng hằng số**; hãy ghim **bất
   biến** đứng sau nó.
4. **`408`/`429` — một chỗ lệch được chốt bằng ĐO, không bằng tranh luận.** `http_jt` (bản đầu)
   xếp mọi 4xx là vĩnh viễn; `loi_hang.tu_http` nói `408`/`429` thử lại được. Làn này chữa ở lớp
   trên (ép `co_the_thu_lai=False`) và **đã báo AG-00**; AG-00 bác đúng — đó là chữa triệu chứng
   và chỉ đổi chiều lệch. Chốt cuối: **cả hai mã là TẠM THỜI**, sửa ở **lớp dưới** (`http_jt` +
   `transport.py`), còn làn này **gỡ chỗ ép** và ghim ngoại lệ bằng **một nguồn**
   (`MA_HTTP_HAI_LOP_PHAI_DONG_Y`). Làn này cũng nêu cảnh báo **"ngủ trong `gui_form` ⇒ 3 × trần"**
   (trần 30 s ⇒ 90 s treo) và AG-00 đã xử lý theo đúng hướng "chỉ ném, không chờ".
   **Bài học giữ lại:** khi hai lớp bất đồng, **sửa lớp phát ra quyết định**, đừng bọc lại ở lớp
   trên — bọc lại chỉ làm chỗ lệch khó thấy hơn.
5. **`L2-N2` và ca canh của AG-01.** Bản vá làm ca cũ `test_b4_..._la_diem_MO_can_va` trở thành
   **hỏng giả** trên máy đặt `TZ=UTC` (nó ghim hành vi CŨ). AG-01 đã thay bằng
   `test_b4_moc_naive_duoc_gan_UTC7_tuong_minh`, đo bất biến MỚI trên bốn `TZ`. Đo lại:
   `TZ=UTC python3 app/thu/thu_qa_jt.py` ⇒ **22 ca · hỏng 0**.

---

## 6. NHỮNG GÌ **KHÔNG** ĐƯỢC CHỨNG MINH (nói thẳng)

Mọi con số ở §4 đo **trên máy này, cục bộ, qua stub `127.0.0.1`**. Vì vậy chúng **KHÔNG** chứng
minh:

- J&T có **chấp nhận** chữ ký, tham số, định dạng `bizContent` này không;
- `timestamp` hiểu theo **(a)** mốc Unix thật hay **(b)** giờ treo tường UTC+7 quy đổi
  (câu hỏi 12 — hai cách lệch **đúng 7 tiếng**, và **chữ ký không chứa `timestamp`** nên sai cách
  này thì chữ ký vẫn đúng mà mọi lượt bị từ chối ở lớp chống phát-lại);
- dạng `password` nào đúng (câu hỏi 22 — tài liệu cho **ba** dạng mâu thuẫn);
- bảng mã lỗi đã đọc có khớp mã lỗi thật của hãng không;
- sandbox hãng có sống không;
- đường dẫn `cancelOrder` / `calculatingFees` / `printOrder` có đúng không;
- mã trạng thái `110` nghĩa là gì (D-4: **không đoán**, và G16-A **không thêm mã nào** vào bảng).

---

## 7. BLOCKED — CHÍNH XÁC CÒN THIẾU GÌ, AI GỠ

| # | Việc bị chặn | Thiếu CHÍNH XÁC cái gì | Ai gỡ |
|---|---|---|---|
| 1 | **Mọi lượt gọi hãng (kể cả sandbox)** | `V-G09-01` + `V-13906-05` — §25 ghi **CHƯA CẤP** | anh Thành |
| 2 | **Credentials** | 4 **TÊN** trường: `apiAccount` · `privateKey` (Console J&T) · `customerCode` · `password` (bưu cục). **CHƯA CÓ tệp `.env` nào**, và `.env.example` không khai khoá J&T nào (§38) | J&T + bưu cục |
| 3 | **Mở `sandbox`** | `cau_hinh.JT_CHO_PHEP_SANDBOX = False` — cần (1) + (2) + phiếu duyệt | anh Thành |
| 4 | **Mở `production`** | `cau_hinh.JT_CHO_PHEP_PRODUCTION = False` — cần duyệt **RIÊNG** | anh Thành |
| 5 | **Ánh xạ `area` (D-9)** | Trả lời **câu hỏi 28** + **danh mục địa danh chuẩn**. Ví dụ của chính hãng đặt **quận vào `city`**, **phường vào `area`** — ngược ánh xạ đang dùng — và hệ **không gửi `city`** | J&T + anh Thành |
| 6 | **Huỷ đơn** | (a) **tiền tố cổng** của `/api/order/cancelOrder`; (b) **TÊN trường lý do huỷ** (hãng bắt buộc có lý do — mã lỗi `145003089`) | đọc lại SPA `apiDoc/orderserve/cancel` |
| 7 | **Báo giá cước** | **đường dẫn + bảng tham số** của `apiDoc/fees/calculatingFees` | như trên |
| 8 | **Nhãn vận đơn** | **đường dẫn + tham số** của `apiDoc/vip/printOrder` | như trên |
| 9 | **`getOrder`** | câu hỏi **26**: có API tra theo `txlogisticId` không. Chưa có ⇒ đối soát bằng `trackOrder` | J&T |
| 10 | **Nghĩa mã trạng thái** | câu hỏi **1–5**: mã `110` có **hai nghĩa ngược nhau** trên cùng một trang; nghi có **HAI bộ mã**. Hệ **không áp trạng thái nào** cho `110` và đánh dấu "cần soát" (D-4) | J&T |
| 11 | **`timestamp` / dạng `password`** | câu hỏi **12** và **22** — sai thì **chữ ký vẫn đúng** mà mọi lượt bị từ chối | J&T |
| 12 | **Callback thật** | `V-G11-01` (URL công khai) CHƯA CẤP — thuộc G14 | anh Thành |
| 13 | **`GET ORDER`-level LIVE VERIFIED** | **Không thể đạt ở G16-A.** Cần một lượt gọi hãng THÀNH CÔNG có bằng chứng | — |

Nguồn chân lý cho tài liệu hãng vẫn là **bản trích TRONG REPO**: `open.jtexpress.vn` là **SPA**
nên `web_fetch`/`curl` trả về **vỏ rỗng**; `web_search` chỉ ra SDK bên thứ ba — **không dùng làm
căn cứ**. Lượt này **không** thêm dữ kiện mới nào từ web, và **không** suy diễn thêm URL nào.

---

## 8. PHẠM VI CỦA CHÍNH TÀI LIỆU NÀY

**Đo bằng:** `python3 app/thu/thu_hop_dong_jt.py` (64 ca) · `python3 app/thu/thu_adapter_jt.py`
(71 ca) · `sh app/thu/chay_tat_ca.sh` (**1284 ca python · 36 bộ** + 2 tầng frontend + 41 E2E) ·
các đoạn `python3` một lượt ở §4.2/§4.3. Mọi con số **chép từ output thật**.

**NẰM NGOÀI:** không gọi API hãng (mọi chế độ, kể cả sandbox) · không mở `CHO_PHEP_LIVE` · không
mở `sandbox`/`production` · không chạm `app/http_jt.py` hay `app/thu/stub_jt.py` của AG-02 (chỉ
**gọi**) · không sửa `adapter.py` · `transport.py` · `csdl.py` · `migrate.py` · `server.py` ·
`cau_hinh.py` · không chạm CSDL PostgreSQL `:5432` (đang giữ dữ liệu dự án KHÁC) · không
commit/push/branch (git của harness hỏng; `.git` ngoài vùng ghi) · không bind cổng cố định (stub
dùng `127.0.0.1` + cổng **0**) · không ghi `webhook.py` (AG-04).

**Trạng thái đúng, để không ai đọc quá:** adapter J&T = **MOCK_VERIFIED** + **đường gửi thật đã
đo trên stub cục bộ**; mọi thứ chạm hãng = **BLOCKED**.
