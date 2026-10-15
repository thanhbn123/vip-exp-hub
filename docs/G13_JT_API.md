# G13 — TÍCH HỢP API J&T EXPRESS: KIỂM KÊ, VIỆC ĐÃ LÀM, VÀ DANH SÁCH BLOCKED

**Người làm:** AG-02 · J&T API ENGINEER · **ngày** 15/10/2026 · **nền:** `de740dc` (worktree Orca)
**Tệp được ghi trong lượt này:** `app/adapter_jt.py` · `app/thu/thu_hop_dong_jt.py` (mới) ·
`app/thu/thu_adapter_jt.py` (mới) · `docs/G13_JT_API.md` (tệp này) ·
**cuối lượt, theo quyết định + cấp quyền của AG-00:** `app/don_hang.py` · `app/thu/thu_don_hang.py`
(hai chỗ vá F1/F2 ở §6) · `app/harness_hang.py` (dọn nốt bí danh `ma`, §6.1 bước 5 — ghi theo
quyền được cấp, làn AG-03 đã nhả tệp theo hợp đồng §23).

> **KẾT LUẬN NGẮN, ĐỌC TRƯỚC:** adapter J&T nay chạy **đầy đủ ở MOCK** và **bị chặn cứng ở mọi
> môi trường khác** — nhưng G13 **KHÔNG** phải "LIVE VERIFIED" và **không thể** là như vậy:
> `V-G09-01` (gọi API hãng) và `V-13906-05` (credentials sandbox J&T) **CHƯA CẤP**, và
> **lớp transport HTTP thật chưa được viết** (`TRANSPORT_THAT_DA_VIET = False`). Mọi con số
> trong tài liệu này đo trên **máy này, cục bộ, KHÔNG có lượt gọi mạng nào**.

---

## 1. J01 — KIỂM KÊ: CÁI GÌ ĐÃ CÓ, CÁI GÌ LÀ VỎ, CÁI GÌ CÒN THIẾU

Đo bằng cách đọc `app/adapter_jt.py` ở `de740dc` (313 dòng) và gọi thử từng thao tác ở `mock`.
Cột "trước G13" là hiện trạng **đo được**, không phải ấn tượng.

| # | Thao tác | Trước G13 | Nay |
|---|---|---|---|
| 1 | **Kiểm kết nối** | **THIẾU HOÀN TOÀN** — không có hàm nào | `kiem_ket_noi()` — **kiểm CẤU HÌNH cục bộ**, tự khai `chung_minh_ket_noi: False`. Tài liệu J&T **không nêu endpoint ping/health** nào, nên không có "kiểm kết nối" thật ở mock; muốn thật thì phải chạy harness chế độ SANDBOX (đang BLOCKED) |
| 2 | **Báo giá cước** (`getShippingFee`) | **VỎ**: trả `15000 + (kl//500)*5200`, không dựng yêu cầu, không có đường dẫn, không nói giá đó từ đâu | Giữ công thức (không đổi số để không phá đường đang chạy) nhưng **tự khai** `la_gia_hang: False` + `nguon_gia`; ngoài `mock` **DỪNG** vì chưa xác minh đường dẫn `apiDoc/fees/calculatingFees` |
| 3 | **Tạo đơn** (`createOrder`) | **CHẠY ĐƯỢC Ở MOCK**: đủ url/headers/body, ký đúng công thức, ba kết cục, COD ở `codMoney` | Thêm: từ chối tiền thập phân/bool/âm, chặn cân nặng ≤ 0, kịch bản ép **đơn trùng**, sổ mô phỏng chống trùng (bật tường minh), gắn `thieu_truong` (chú thích cũ nói có gắn mà mã **không** gắn), **bỏ** tiền tố digest khỏi kết quả (dữ liệu suy ra từ khoá) |
| 4 | **Huỷ đơn** (`cancelOrder`) | **VỎ**: `return KetQuaHang(True,...)`, không dựng yêu cầu, không URL | Có `yeu_cau_huy_don` (ký + thân form). Ngoài `mock`: **DỪNG** — đường dẫn chỉ đọc được ở dạng **tương đối**, và **tên trường lý do huỷ chưa đọc được** (hãng bắt buộc có lý do: mã lỗi `145003089`) |
| 5 | **Tra hành trình** (`trackOrder`) | **VỎ CÓ KHIẾM KHUYẾT**: trả `tho["trang_thai"] = "dang_giao"` — một **trạng thái CHUẨN** đặt vào chỗ `polling.py` chờ **mã CỦA HÃNG** (`trang_thai_hang.quyet_dinh(hang, ma)`). Đo được: `quyet_dinh("jt","dang_giao").biet_ma is False` ⇒ **mọi vòng polling đếm "mã lạ"** ở mock. Không dựng yêu cầu, không ai kiểm trần 30 mã | `yeu_cau_tra_hanh_trinh` (billcodes, trần 30 → lỗi `145003502`), mock trả **mã thật `112`** (On Delivery → `dang_giao`), có ca canh `biet_ma is True`. Ngoài `mock`: dừng ở cửa transport |
| 6 | **Nhãn vận đơn** (`getShippingLabel`) | **VỎ**: trả chuỗi `"MOCK-PDF"` | Giữ kết quả nhưng **tự khai** `la_nhan_hang: False`; ngoài `mock` **DỪNG** (chưa xác minh `apiDoc/vip/printOrder`) |
| 7 | **`getOrder`** | `capability=False`, lớp nền trả "không hỗ trợ" | **GIỮ NGUYÊN False** — tài liệu công khai **chưa nêu** API tra theo `txlogisticId` (câu hỏi 26). Đối soát đi bằng `trackOrder` |
| 8 | **Ánh xạ địa chỉ (`prov`/`area`)** | Chốt D-9 **đã cắm** (G12): `area` ← quận/huyện, chặn cứng mọi môi trường ≠ `mock` | Giữ nguyên chốt (D-9 **KHOÁ**). Thêm `CITY_CO_GUI = False` + ca kiểm ghim giả định và khẳng định **mở `CHO_PHEP_LIVE` KHÔNG gỡ được chốt** |
| 9 | **COD** | Đúng `codMoney`, nhưng `int(...)` trần ⇒ **`15000.7` bị nuốt thành `15000`** không báo gì | `tien_nguyen_vnd`: thập phân/bool/âm/chuỗi lạ ⇒ **NỔ** `THAM_SO_SAI`; `itemsValue` có ca canh **cấm dùng cho COD** |
| 10 | **Chuẩn hoá lỗi hãng** | Chỉ có **một** đường: `ghi_chu=demo_force_fail` ở `createOrder` → `doc_tra_loi_jt`. **Không có hàm đọc gói trả lời** | `doc_goi_tra_loi` (code `"1"` = thành công; mã lạ ⇒ `KHONG_RO`; 5xx ⇒ `HET_GIO` + `timeout=True`; 429 ⇒ `QUA_HAN_MUC`). Gói lỗi mang đủ 4 trường hợp đồng §5 với tên khoá chuẩn **`ma_chuan`**; đầu kia (`don_hang`) đã được vá theo §6.1 |
| 11 | **`KHOA_CHONG_TRUNG`** | Cờ `True` + chính sách `transport.py` | Thêm: mock **tạo ra được** `145003204`, sổ mô phỏng chống trùng **bật tường minh** + **ca đối chứng** (sổ tắt thì cùng `ma_don` tạo được hai lượt) |
| 12 | **Cách ly tenant** | Đường nối credentials theo tenant đã đúng (`carrier_accounts` + AAD) | Thêm ca: hai tài khoản khác nhau ⇒ chữ ký khác; `tho` và **biến cấp module** không chứa bí mật; sổ chống trùng khoá theo `apiAccount + customerCode` |
| 13 | **Ràng buộc "không gọi mạng"** | Có ca ở `thu_g03.py` | Thêm ca riêng + **tự kiểm bộ dò** (nhóm F của `thu_hop_dong_jt.py`) |

**Tóm tắt kiểm kê:** chỉ **1** thao tác (`createOrder`) đã thật sự có hợp đồng yêu cầu.
**6 hạng mục là VỎ HOẶC THIẾU** (kiểm kết nối · báo giá · huỷ đơn · tra hành trình · nhãn ·
đọc gói trả lời). **2 chỗ có mã nhưng KHIẾM KHUYẾT đo được**: mock tra hành trình trả *trạng thái
chuẩn* vào chỗ chờ *mã hãng*; tiền thập phân bị `int()` **nuốt im lặng**. **4 hạng mục đã đúng và
được GIỮ NGUYÊN** (chốt D-9 · cờ `KHOA_CHONG_TRUNG` + chính sách `transport.py` · đường nối
credentials theo tenant · guard không gọi mạng).

---

## 2. J02 — XÁC THỰC: TÀI LIỆU NÓI GÌ, VÀ CÁI GÌ CHƯA XÁC MINH ĐƯỢC

**Nguồn chân lý là bản trích tài liệu TRONG REPO**, không phải trang web: `open.jtexpress.vn` là
**SPA** nên `web_fetch`/`curl` trả về vỏ rỗng. Đã thử `web_search` để đối chiếu chéo trong lượt
này: kết quả chỉ là các SDK bên thứ ba (Packagist, một repo nội bộ của bên khác) — **không dùng
làm căn cứ** vì đó không phải tài liệu của hãng, và một lượt `web_fetch` vào repo bên thứ ba
**thất bại**. Không có dữ kiện mới nào được thêm từ web.

### 2.1 Sơ đồ ký — ĐÃ ĐỌC ĐƯỢC, giữ nguyên công thức G04

| Thành phần | Giá trị | Nguồn trong repo |
|---|---|---|
| Header bắt buộc | `apiAccount` · `digest` · `timestamp` | `docs/JT_CAU_HOI_CHINH_THUC.md` câu 6; `app/adapter_jt.py` (G04) |
| `digest` | `base64( md5-BYTES( bizContent-JSON + privateKey ) )` — **md5 ra mảng byte rồi mới base64** | trang *极兔API简介*, nguyên văn trong `app/adapter_jt.py:37-42` |
| `timestamp` | mili giây, ghi chú *时区：UTC+7* | cùng nguồn |
| Thân yêu cầu | `application/x-www-form-urlencoded`, **một** trường `bizContent` là **chuỗi** JSON | cùng nguồn |
| `bizContent` bắt buộc | `customerCode` · `password` (+ `txlogisticId` khi tạo/huỷ đơn) | `docs/G09_CREDENTIALS_CHECKLIST.md` §1; `docs/JT_CAU_HOI_CHINH_THUC.md` câu 22 |

Ba điểm **CHƯA xác minh được** (đã nằm trong bộ 29 câu hỏi gửi J&T — **không tự chọn một nghĩa**):

1. **`timestamp`**: câu hỏi **12** — mốc Unix thật **(a)** hay giờ treo tường UTC+7 quy đổi **(b)**?
   Hai cách lệch **đúng 7 tiếng**. Hệ đang làm theo **(a)**. Chữ ký **không** chứa `timestamp`
   nên sai cách này thì **chữ ký vẫn đúng** mà mọi lượt bị từ chối ở lớp chống phát-lại —
   hỏng theo kiểu rất khó nhìn ra.
2. **Dạng `password`**: câu hỏi **22** — tài liệu cho **BA** dạng mâu thuẫn (MD5 ở ví dụ yêu cầu,
   *明文密码* ở bảng tham số, base64 ở API tra hành trình). Hệ **gửi nguyên giá trị cấu hình**,
   không băm — và **không đoán**.
3. **Callback ký bằng khoá nào**: câu hỏi **6–8**. Thuộc G14 (AG-03), ghi ra đây để không ai
   tưởng G13 đã trả lời.

### 2.2 Bảng đường dẫn — cái gì ĐÃ đọc được, cái gì CHƯA

Đây là thay đổi cấu trúc quan trọng nhất của G13: **"chưa đọc được tài liệu" nay là một trạng
thái có thật trong mã** (`DUONG_API[...]["muc"]`), không còn là một câu trong chú thích.

| Thao tác | Đường dẫn | Mức | Nguồn |
|---|---|---|---|
| `createOrder` | `/webopenplatformapi/api/order/addOrder` | **da-doc** | `apiDoc/orderserve/create`, đọc 14/10/2026 (có trong `adapter_jt.py` từ G04) |
| `trackOrder` | `/webopenplatformapi/api/logistics/trace` | **da-doc** | `apiDoc/logistics/query`, đọc lại 14/10/2026 |
| `cancelOrder` | `/api/order/cancelOrder` — **chỉ dạng TƯƠNG ĐỐI** | **chua-xac-nhan** | `docs/JT_CAU_HOI_CHINH_THUC.md` câu 27 (chép từ `apiDoc/orderserve/cancel`, 15/10/2026). **Tiền tố cổng chưa xác minh ⇒ KHÔNG tự ghép URL** |
| `getShippingFee` | — | **chua-xac-nhan** | trang `apiDoc/fees/calculatingFees` có trong trình đơn; **chưa chép được đường dẫn và bảng tham số** |
| `getShippingLabel` | — | **chua-xac-nhan** | trang `apiDoc/vip/printOrder` có trong trình đơn; **chưa chép được đường dẫn**; trang 批量打印面单 còn chưa mở được |
| `getOrder` | — | **chua-xac-nhan** | tài liệu công khai chưa nêu API tra theo `txlogisticId` — câu hỏi **26** |

⇒ **BỐN thao tác bị chặn ở mọi môi trường khác `mock`**, kèm thông điệp nêu đúng cái còn thiếu
(`ChuaXacNhanTaiLieu.thieu`). Hai thao tác còn lại đi qua được cửa đường dẫn nhưng dừng ở cửa
**transport HTTP chưa viết**.

---

## 3. J03 — CREDENTIALS: THIẾU CHÍNH XÁC NHỮNG GÌ (CHỈ TÊN TRƯỜNG)

Tài liệu này **không chứa và sẽ không bao giờ chứa giá trị credentials nào**. Bốn trường dưới
đây là **tên**, không phải giá trị; hai lớp cấp khác nhau, và **có lớp A vẫn không tạo được đơn**:

| # | Tên trường | Lớp | Ai cấp | Trạng thái 15/10/2026 |
|---|---|---|---|---|
| 1 | `apiAccount` | nền tảng | Console J&T, sau bước 开发者认证 | **CHƯA CÓ** |
| 2 | `privateKey` | nền tảng | như trên | **CHƯA CÓ** |
| 3 | `customerCode` | hợp đồng khách | **bưu cục hợp tác J&T** | **CHƯA CÓ** |
| 4 | `password` | hợp đồng khách | như trên | **CHƯA CÓ** — và còn phải hỏi **gửi dạng nào** (câu hỏi 22) |

Danh sách này là hằng số **trong mã** (`adapter_jt.TRUONG_CREDENTIAL`) nên `kiem_ket_noi()`
trả về đúng bốn **tên** còn thiếu, không bao giờ trả giá trị.

### 3.1 Đường nối — ĐÃ ĐO, dùng đúng bốn hàm hợp đồng (§14)

```
carrier_accounts.credentials_ma_hoa   (bản mã, do server.py ghi bằng bao_mat.ma_hoa_cred)
        │
        ├─ app/server.py  (tuyến tạo/sửa tài khoản hãng)   bao_mat.ma_hoa_cred(cred, tenant_id, hang)
        ↓
app/don_hang.py  _adapter_cua_account → bao_mat.giai_ma_cred(ban_ma, tenant_id, hang)
                                      → adapter.tao_adapter(hang, cred, moi_truong)
        ↓
app/adapter_jt.py  AdapterJT.__init__  →  dùng cred["customerCode"], ["password"] (bizContent)
                                          cred["apiAccount"], ["privateKey"] (headers/digest)
```
*(số dòng cụ thể: `server.py:769/790` · `don_hang.py:562/563` — đo ở `de740dc`, các làn khác đang
sửa hai tệp đó nên tra theo TÊN HÀM nếu số dòng đã lệch.)*

Bằng chứng chạy thật (rút gọn; giá trị là **giả**, do bộ thử tự dựng):

```
$ python3 -c '...'                     # mã hoá → giải mã → đưa vào adapter, KHÔNG ra mạng
tien to: v3$goc | so $: 3 | duoi: A1
lo bi mat: []
round trip: True
tenant khac -> chan: ValueError
adapter nhan dung cred: True
apiAccount vao header: A1
ket qua mock khong lo bi mat: True
```

⇒ Bản mã mang `key_id` dạng **`v3$<key_id>$<nonce>$<ct>`** (AES-256-GCM, §14), **giải mã sai
tenant hoặc sai hãng thì bị chặn** (AAD), và `adapter_jt.py` **không tự gọi** `bao_mat.ma_hoa`/
`giai_ma` trần (có ca canh bằng regex + tự kiểm bộ dò).

---

## 4. J04 — ĐÃ CÀI GÌ TRONG `app/adapter_jt.py`

`649 dòng thêm · 68 dòng bớt` (`git diff --stat`, 313 → 894 dòng). Không đổi công thức chữ ký,
không đổi tên hàm nào đang có người gọi.

1. **Bảng `DUONG_API`** + `url_cua()` + `chan_duong_chua_xac_nhan()` + lớp lỗi
   `ChuaXacNhanTaiLieu` (khác `PermissionError` = khoá an toàn, khác `NormalizedCarrierError`
   = lỗi của hãng; đây là **lỗi của chính mình: chưa biết đủ để gọi**).
2. **Ba hàm dựng yêu cầu**: `yeu_cau_tao_don` (đã có), `yeu_cau_tra_hanh_trinh` (trần 30 mã,
   `billcodes` ngăn cách phẩy), `yeu_cau_huy_don` (`txlogisticId`). Không gửi đi đâu cả.
3. **`doc_goi_tra_loi`** + `ket_qua_tu_loi` + `ket_qua_het_gio` + `lay_ma_van_don`: đọc
   `{code,msg,data}` → `KetQuaHang`; **`HET_GIO` ⇒ `timeout=True`** (5xx/408 = KHÔNG BIẾT kết quả);
   thành công mà không đọc được mã vận đơn ⇒ **`ok=True`, `ma_van_don=None`, cờ
   `thieu_ma_van_don`** — **không bịa mã, cũng không gọi sai thành thất bại**.
4. **`tien_nguyen_vnd`**: INTEGER đồng, từ chối thập phân/bool/âm/chuỗi lạ.
5. **`kiem_ket_noi`**: nói thẳng `chung_minh_ket_noi: False` + việc còn phải làm.
6. **Kịch bản mock**: `ghi_chu=demo_force_fail|demo_force_timeout|demo_force_trung` và tiền tố
   mã `MOCK-HONG…` · `MOCK-HETGIO…` · `MOCK-KHONGCO…` (đi qua **bảng mã lỗi thật**, không bịa
   chuỗi lỗi).
7. **`SoDonMock`** (mô phỏng khoá chống trùng phía hãng) — **mặc định TẮT**, bật tường minh,
   khoá theo `apiAccount + customerCode + txlogisticId`.
8. **Bỏ `digest_da_ky`** khỏi kết quả mock: `digest = f(bizContent + privateKey)` nên một tiền tố
   của nó **vẫn là dữ liệu suy ra từ khoá**. Thay bằng `da_ky: True` + `do_dai_digest`.

**Ba ổ khoá chặn LIVE, ĐỘC LẬP** (mở một ổ không mở ổ khác — có ca kiểm cho từng cặp):
`CHO_PHEP_LIVE=False` (chặn trong `__init__`) · chốt **D-9** `area` (chặn tại chỗ dựng
`bizContent`) · `TRANSPORT_THAT_DA_VIET=False` + bảng `DUONG_API` (chặn tại chỗ gọi).

---

## 5. J06 — BỘ THỬ: LỆNH, KẾT QUẢ THẬT, VÀ CÁI GÌ NẰM NGOÀI

Hai tệp **mới**, không giẫm tệp của ai: `app/thu/thu_hop_dong_jt.py` (47 ca) và
`app/thu/thu_adapter_jt.py` (51 ca). **98 ca**, mỗi tệp in số ca và thoát khác 0 khi hỏng.

```bash
cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
export VIP_HUB_DATA=$(mktemp -d)
python3 app/thu/thu_hop_dong_jt.py
python3 app/thu/thu_adapter_jt.py
```

Kết quả thật:

```
$ python3 app/thu/thu_hop_dong_jt.py
Ran 47 tests in 0.024s
OK
Tổng: 47 ca · hỏng 0 · lỗi 0 · bỏ qua 0

$ python3 app/thu/thu_adapter_jt.py
Ran 51 tests in 0.003s
OK
Tổng: 51 ca · hỏng 0 · lỗi 0 · bỏ qua 0
```

Cả hai tệp có **ca tự kiểm bộ dò** (nhóm F mỗi tệp) — bộ dò gọi mạng và bộ dò bí mật phải
**chứng minh nó dò được** trên đầu vào dựng sẵn, nếu không thì ca "sạch" chỉ là ca luôn-đúng.
Nhóm E có **ca đối chứng**: tắt sổ mô phỏng chống trùng thì cùng `ma_don` tạo được **hai** lượt —
chứng minh "phát hiện trùng" không phải phép kiểm luôn-đúng.

### 5.1 Hồi quy — chạy toàn bộ bộ thử của dự án

```bash
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1   # git trong môi trường harness bị hỏng
sh app/thu/chay_tat_ca.sh
```

Kết quả thật (15/10/2026, sau khi G13 + vá F1/F2 + dọn nốt bí danh `ma`):

```
  ✓ thu_adapter_jt.py          51 ca
  ✓ thu_hop_dong_jt.py         47 ca
  ✓ thu_don_hang.py            66 ca
  ...
  python:   1111 ca · 33 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  KHÔNG
```

Một ghi nhận giữa lượt: lần chạy đầu tiên (trước khi làn G14 viết xong tài liệu) có
`✗ thu_webhook_jt.py 65 ca HỎNG` vì ca `test_j01` đòi `docs/G14_JT_WEBHOOK.md` **chưa tồn tại**.
Cuối lượt, tệp đó **đã xanh** — bộ hỏng duy nhất của lượt chạy đầu **không phải** của G13.

**Năm bộ liên quan trực tiếp tới G13 đều xanh:** `thu_g03.py` 53 ca · `thu_anh_xa_area.py` 16 ca
(chốt D-9, gồm nhóm C "đã cắm vào adapter") · `thu_harness_hang.py` 57 ca (gồm A5 canh
`CHO_PHEP_LIVE is False`) · `thu_don_hang.py` **66 ca** (thêm `d12b` adapter thật, `d17` DON_TRUNG,
`d18` đối chứng hoàn suất).

### 5.2 PHẠM VI — nói thẳng cái gì NẰM NGOÀI

- **Không có lượt gọi mạng nào.** `V-G09-01` và `V-13906-05` CHƯA CẤP; `CHO_PHEP_LIVE=False`.
  Bộ thử chỉ chạy `mock` + gọi hàm đọc gói trả lời trên **JSON tự dựng theo quy ước tài liệu**.
- Vì vậy 98 ca xanh **KHÔNG** chứng minh: hãng chấp nhận chữ ký; mã lỗi thật khớp bảng đã đọc;
  sandbox hãng sống; `timestamp` hiểu theo (a) hay (b); dạng `password` nào đúng; đường dẫn
  `cancelOrder`/`calculatingFees`/`printOrder` đúng.
- **G13 KHÔNG được báo "LIVE VERIFIED".** Trạng thái đúng: **MOCK_VERIFIED** cho adapter,
  **BLOCKED** cho mọi thứ chạm hãng.

---

## 6. PHÁT HIỆN ĐÃ BÁO AG-00 — F1/F2 nay ĐÃ VÁ (AG-00 cấp quyền ghi `don_hang.py`)

> **Cập nhật cuối lượt 15/10/2026:** AG-00 chốt **`ma_chuan` là tên CHUẨN** và cấp quyền cho AG-02
> ghi `app/don_hang.py` + `app/thu/thu_don_hang.py`. **F1 và F2 đã được vá**, kèm ca thử và ca đối
> chứng. Nội dung phát hiện ban đầu giữ nguyên bên dưới để còn dấu vết.

### 6.1 [ĐÃ VÁ] Hai tên khoá cho cùng một thứ: `ma_chuan` (§5) và `ma` (Order Service)

**Phát hiện:** `loi_hang.NormalizedCarrierError.nhu_dict()` phát **`ma_chuan`**;
`don_hang._la_khong_tim_thay()` lại đọc **`tho["loi_chuan"]["ma"]`**. Không có ngoại lệ nào báo —
nhánh đối soát `chua_vao` chỉ chạy được vì `thu_don_hang.test_d12` **dựng adapter giả** với đúng
khoá `ma`. **Quyết định của AG-00: bên SAI là `don_hang.py`, không phải `loi_hang.py`.**

**Đã làm:**
1. `don_hang._ma_chuan_cua(kq)` — đọc **`ma_chuan`**. (Bước 1 ban đầu còn giữ `ma` làm **lớp lùi
   tạm**; lớp lùi đó **đã được GỠ HẲN** ở bước 5 — xem dưới.)
2. `thu_don_hang.test_d12` nay dựng gói lỗi **BẰNG chính `nhu_dict()`** (khoá `ma_chuan`), nên ca
   thử đi qua hình dạng THẬT của hợp đồng. Ca cũ chỉ chứng minh "bộ dò khớp với chính bộ dò".
3. **Ca đối chứng mới `test_d12b`**: dùng **adapter THẬT** `adapter_jt` (kịch bản `MOCK-KHONGCO…`
   ⇒ hãng trả `999002000`) đi hết đường `doi_soat_don` ⇒ `chua_vao` + hoàn 1 suất. Không adapter
   giả, không dict tự chế.
4. `adapter_jt.goi_y_loi_chuan()` **đã GỠ bí danh `ma`** — adapter chỉ phát hình dạng hợp đồng.
   `thu_adapter_jt.test_d2` khẳng định `"ma" not in loi_chuan` **và** Order Service nhận ra mã lỗi
   của adapter THẬT (cả `KHONG_TIM_THAY` lẫn `DON_TRUNG`).
5. **Dọn nốt để chỉ còn MỘT tên khoá trên toàn hệ** (AG-00 cấp quyền ghi `app/harness_hang.py`,
   làn AG-03 đã nhả theo §23):
   · fixture H2 của harness nay dựng gói lỗi qua `NormalizedCarrierError.nhu_dict()` — trước đây
     nó tự gõ tay `{"ma": …}`, tức chính **thứ dùng để kiểm chứng** cũng đang dùng tên sai;
   · `don_hang._ma_chuan_cua` **gỡ hẳn** lớp lùi ⇒ chỉ còn `ma_chuan`;
   · fixture `thu_don_hang.test_d13` cũng đổi sang `nhu_dict()`;
   · **ca canh mới `harness_hang` H5** — *"tên khoá lỗi chỉ có MỘT: `ma_chuan` — bí danh `ma` đã
     chết"*: dựng `loi_chuan` CHỈ có khoá `ma` và khẳng định Order Service **KHÔNG** nhận ra.
     Không có ca này thì lần sau ai thêm lại một dòng dự phòng cũng không ai biết (§14.6).
     Đo được: harness `TỔNG: 97 đạt · 0 hỏng · 3 bỏ qua` (H5 chạy cho **cả hai** hãng).

### 6.2 [ĐÃ VÁ] `DON_TRUNG` bị Order Service xử như "hãng từ chối"

**Phát hiện:** `don_hang.gui_don()` nhánh `else` (không `ok`, không `timeout`) trả đơn về `da_duyet`
+ **hoàn suất**. Với J&T, `145003204` nghĩa là **lượt trước ĐÃ VÀO**: trả về `da_duyet` là nói sai
sự thật (vận đơn ĐANG Ở HÃNG), và gửi lại cùng `txlogisticId` ⇒ lại `DON_TRUNG` ⇒ **mắc vòng**.
**AG-00: "anh đúng, và đây là lỗi TIỀN."**

**Đã làm:** nhánh `elif _la_don_trung(kq)` trong `gui_don`, đứng TRƯỚC nhánh từ chối:
giữ `dang_gui` + `can_doi_soat_ket_qua=1`, **KHÔNG hoàn suất**, ghi `don_lich_su` nêu rõ
*"hãng báo ĐƠN ĐÃ TỒN TẠI … lượt trước ĐÃ VÀO hãng, cần đối soát … KHÔNG gửi lại mù"*.
**Không ném ngoại lệ** — cùng loại kết cục với nhánh timeout (§10: *"tuyệt đối không coi là thành
công"*, và ở đây **cũng tuyệt đối không coi là thất bại**), nên nơi gọi đọc TRẠNG THÁI chứ không
đọc một lỗi ám chỉ "hãng từ chối".
Ca thử `thu_don_hang.test_d17`: trạng thái · cờ đối soát · **suất KHÔNG hoàn** · có trong
`don_can_doi_soat` · vết lịch sử · gửi lại bị chặn 409. **Ca đối chứng `test_d18`**: hãng từ chối
THẬT vẫn lùi `da_duyet` + **hoàn suất** + 502 — thiếu ca này thì một bản vá "giữ tất cả ở
`dang_gui`" cũng làm `d17` xanh.

### 6.3 `thu_tich_hop.py` hỏng vì môi trường harness, không vì mã

`test_04_khoa_ma_hoa_khong_duoc_vao_git` gọi `git check-ignore` **không** `unset GIT_CONFIG_*`
⇒ trong phiên này `git` trả **128** ⇒ ca đỏ giả (`app/du-lieu/khoa KHÔNG bị gitignore`). Đã đo
lại: `unset` ba biến rồi chạy thì **6 ca đạt**. Bộ chạy `app/thu/chay_tat_ca.sh` cũng cần `unset`
tương tự nếu muốn nó không báo hỏng giả.

---

## 7. BLOCKED — CHÍNH XÁC CÁI GÌ CÒN THIẾU, AI GỠ

| # | Việc bị chặn | Thiếu CHÍNH XÁC cái gì | Ai gỡ |
|---|---|---|---|
| 1 | **Mọi lượt gọi hãng (kể cả sandbox)** | Mã việc **`V-G09-01`** + **`V-13906-05`** — `SHARED_CONTRACTS.md` §25 ghi **CHƯA CẤP** | anh Thành |
| 2 | **Credentials sandbox** | 4 **tên** trường: `apiAccount` · `privateKey` · `customerCode` · `password` (2 lớp, 2 nguồn cấp — `docs/G09_CREDENTIALS_CHECKLIST.md`) | J&T + bưu cục |
| 3 | **Lớp transport HTTP thật** | **Chưa ai viết.** `TRANSPORT_THAT_DA_VIET=False`; viết xong phải đi kèm harness SANDBOX + phiếu duyệt. Mở `CHO_PHEP_LIVE` **một mình không đủ** | làn G13 kế tiếp / AG-00 xếp việc |
| 4 | **Ánh xạ `area` (D-9)** | Trả lời **câu hỏi 28** + danh mục địa danh chuẩn. Đo được: ví dụ của hãng đặt **quận vào `city`**, **phường vào `area`** — ngược ánh xạ đang dùng, và hệ **không gửi `city`** | J&T + anh Thành (D-9 KHOÁ) |
| 5 | **Huỷ đơn** | (a) **tiền tố cổng** của `/api/order/cancelOrder`; (b) **TÊN trường lý do huỷ** (hãng bắt buộc có lý do — mã lỗi `145003089`) | đọc lại SPA `apiDoc/orderserve/cancel` có người của J&T |
| 6 | **Báo giá cước** | **Đường dẫn + bảng tham số** của `apiDoc/fees/calculatingFees` (trang có trong trình đơn, chưa chép được) | như trên |
| 7 | **Nhãn vận đơn** | **Đường dẫn + tham số** của `apiDoc/vip/printOrder`; trang 批量打印面单 chưa mở được | như trên |
| 8 | **Nghĩa mã trạng thái** | Câu hỏi **1–5**: mã `110` có **hai nghĩa ngược nhau** trên cùng một trang; nghi có **HAI bộ mã** (`103…121` vs `10/50/92/94/100/110`). Hệ **không áp trạng thái nào** cho `110` và đánh dấu "cần soát" (D-4: **không thêm mã nào vào bảng**) | J&T |
| 9 | **`getOrder`** | Câu hỏi **26**: có API tra theo `txlogisticId` không. Chưa có ⇒ đối soát bằng `trackOrder` | J&T |
| 10 | **`timestamp` / dạng `password`** | Câu hỏi **12** và **22** — sai thì **chữ ký vẫn đúng** mà mọi lượt bị từ chối | J&T |
| 11 | **Callback thật** | `V-G11-01` (URL công khai) CHƯA CẤP — thuộc G14 | anh Thành |
| 12 | **Lên môi trường thật** `ylopenapi` | Bước 5 của J&T + Owner duyệt riêng | J&T + anh Thành |

---

## 8. PHẠM VI CỦA CHÍNH TÀI LIỆU NÀY

**Đo bằng:** đọc `app/adapter_jt.py` ở `de740dc` và bản sau khi sửa; chạy
`python3 app/thu/thu_hop_dong_jt.py` (47 ca), `python3 app/thu/thu_adapter_jt.py` (51 ca),
`python3 app/thu/thu_don_hang.py` (66 ca), `sh app/thu/chay_tat_ca.sh`
(**1111 ca python · 33 bộ** + 2 tầng frontend + 41 E2E), cùng vài đoạn `python3` một lượt cho
đường nối credentials (mục 3.1). Mọi con số đều **chép từ output thật**, không điền tay (§12.1 luật 4).

**NẰM NGOÀI:** không gọi API hãng (mọi chế độ); không đăng ký/đăng nhập gì trên trang J&T;
không mở `CHO_PHEP_LIVE`; không viết lớp transport; không sửa `app/adapter.py` (đề xuất cho AG-00
nếu cần). `app/don_hang.py` và `app/thu/thu_don_hang.py` **chỉ được ghi ở cuối lượt**, sau khi
AG-00 chốt quyết định F1/F2 và **cấp quyền riêng cho đúng hai tệp đó**; ngoài hai tệp ấy, các tệp
`webhook.py`/`csdl.py`/`server.py`/`migrate.py` vẫn **không bị chạm**. Không chạm CSDL PostgreSQL
`:5432`; không commit/push (git của harness hỏng và `.git` nằm ngoài vùng ghi).

**ĐÍNH CHÍNH ĐÃ GHI:** chú thích trong `yeu_cau_tao_don` (G04) nói "gắn danh sách thiếu vào
payload" nhưng mã **không gắn gì** — nay gắn thật vào **gói yêu cầu** (`thieu_truong`), **không**
vào `bizContent`, để thông tin không bị gửi lên hãng như một trường lạ.
