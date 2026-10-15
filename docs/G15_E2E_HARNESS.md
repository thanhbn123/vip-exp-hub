# G15 — HARNESS E2E: KỊCH BẢN 10 BƯỚC, CHẠY Ở CHẾ ĐỘ **MOCK**

Mã việc: **I06** · người làm: **AG-04 (INFRASTRUCTURE ENGINEER)** · ngày **15/10/2026**.
Chạy: `sh trien_khai/g15/chay_harness.sh`

> **Kết quả lượt chạy 15/10/2026: đạt 29 · hỏng 0 · BLOCKED 2 · bỏ qua 0** (mã thoát **0**).
> Hai mục **BLOCKED** là chặng J&T sandbox và callback `jt_digest` — **không được tính là đạt**.

---

## 0. VÌ SAO CÓ HARNESS NÀY, KHI ĐÃ CÓ `thu_e2e.py` (41 phép)

`app/thu/thu_e2e.py` kiểm **route**: mỗi phép là một khẳng định về một đường API. Nó rất tốt ở
việc đó và **không** thay thế được.

Harness này kiểm **kịch bản nghiệp vụ đi hết một vòng đời đơn hàng**, theo đúng mười bước có
tên, và mỗi bước ghi một phán quyết **kèm bằng chứng**. Khác biệt quan trọng nhất không nằm ở
số phép đo, mà ở chỗ harness **được phép nói `BLOCKED`**:

> Một bộ thử chỉ có hai phán quyết là ĐẠT/HỎNG sẽ **buộc** chặng sandbox phải chọn một trong
> hai — và cả hai đều sai: báo ĐẠT là nói dối, báo HỎNG là báo hỏng giả (chặng đó *không thể*
> chạy, không phải *chạy không được*). `BLOCKED` là phán quyết **thứ ba**, và nó mang theo
> **chính xác cái còn thiếu**.

### Ba chốt chặn an toàn — harness **TỪ CHỐI CHẠY** nếu mất một cái

| # | Chốt | Vì sao |
|---|---|---|
| 1 | `VIP_HUB_DATA` phải nằm trong thư mục **tạm**, và **không** được là `app/du-lieu/` | Kịch bản này TẠO tenant, tài khoản hãng, đơn, sự kiện webhook **thật** trong CSDL. Chạy lên dữ liệu thật là làm bẩn dữ liệu đang dùng |
| 2 | `CHO_PHEP_LIVE` phải `is False` ở **mọi** adapter trong sổ đăng ký `adapter._DANG_KY` | Một harness "thử" mà mở được cửa gọi hãng thật là thứ **nguy hiểm hơn** không có harness |
| 3 | Chỉ nói chuyện với `127.0.0.1` | Không tên miền, không IP ngoài, không tunnel |

**Chốt số 2 đã TỪ CHỐI OAN một lượt chạy thật** — và đó là dấu hiệu nó hoạt động: bản đầu đọc
`adapter_jt.CHO_PHEP_LIVE`, nhưng hằng đó là của **LỚP** (`AdapterJT.CHO_PHEP_LIVE`) chứ không
phải của mô-đun, nên nó thấy `'<thiếu>'` và dừng cả lượt. Đã sửa sang dò **đúng sổ đăng ký** mà
mã chạy dùng. **Bài học:** chốt chặn cũng là một thứ dùng để kiểm chứng, nên nó cũng phải được
kiểm — và nó phải **TỪ CHỐI ỒN ÀO** chứ không được đoán.

---

## 1. KỊCH BẢN 10 BƯỚC — kết quả thật

| Mã | Bước | Phán quyết | Bằng chứng đo được |
|---|---|---|---|
| **B01** | ĐĂNG NHẬP | ✅ ĐẠT | `HTTP 200` · tạo tenant thử + owner `HTTP 201 · tenant_id=3` |
| **B02** | CHỌN TENANT | ✅ ĐẠT | `tenant=3` đến **từ PHIÊN**, không từ body · `vai_tro=TENANT_OWNER` |
| **B03** | CHỌN TÀI KHOẢN J&T | ✅ ĐẠT | `HTTP 201 · id=5 · hãng=jt · môi trường=mock` |
| **B03b** | môi trường tài khoản phải là `mock` | ✅ ĐẠT | nếu là `sandbox`/`production` thì harness **dừng cả lượt** |
| **B03c** | credentials mã hoá at-rest | ✅ ĐẠT | hai trường bí mật có dạng `v3$<key_id>$…` — **chỉ kiểm dạng, KHÔNG in giá trị** |
| **B04** | TẠO ĐƠN THỬ | ✅ ĐẠT | `HTTP 201 · id=1 · mã=T3-000001 · COD=250000` |
| **B04b** | duyệt đơn | ✅ ĐẠT | `trạng thái=da_duyet` |
| **B05** | **GỬI SANG J&T SANDBOX** | ⛔ **BLOCKED** | thiếu: `V-13906-05` (credentials sandbox) · `V-G09-01` (gọi API hãng, kể cả sandbox) · `CHO_PHEP_LIVE=False` |
| **B05-MOCK** | gửi qua adapter **MOCK** | ✅ ĐẠT **(MOCK)** | `HTTP 200 · mã vận đơn=JTVN… · trạng thái=da_gui` |
| **B05b** | nhãn KHÔNG phải nhãn thật | ✅ ĐẠT | `nhan_that=False · la_mock=True` |
| **B06-MOCK** | callback MOCK, chữ ký ĐÚNG (`hub_hmac`) | ✅ ĐẠT | `HTTP 202 · {"ket_qua":"da_nhan","su_kien_id":1}` |
| **B06b** | gửi lại cùng `event_id` | ✅ ĐẠT | `HTTP 200` · **1** sự kiện trong CSDL — idempotent, không nhân đôi |
| **B06c** | callback chữ ký **SAI** | ✅ ĐẠT | `HTTP 401` |
| **B06-SANDBOX** | callback theo sơ đồ **`jt_digest`** của hãng | ⛔ **BLOCKED** | cần header digest thật + credentials sandbox; `webhook.SO_DO_THEO_HANG['jt']` |
| **B07a** | sự kiện xử xong | ✅ ĐẠT | `trạng thái=xong · lỗi=None` |
| **B07b** | trục GIAO VẬN cập nhật từ callback | ✅ ĐẠT | `trục giao vận=dang_giao (hạng 3)` · mã vận đơn khớp |
| **B07c** | có dấu vết lịch sử | ✅ ĐẠT | 5 dòng `don_lich_su` |
| **B07d** | đường polling (fallback) | ✅ ĐẠT | `HTTP 200` · `da_hoi=0` (không có đơn nào cần hỏi — đúng) |
| **B08a** | số COD khai trên đơn giữ nguyên | ✅ ĐẠT | `don_hang.cod=250000` |
| **B08b** | sổ COD **chưa** mở ở bước tạo đơn | ✅ ĐẠT | **0** dòng `tc_cod` trước đối soát — **đúng thiết kế**, xem §2 |
| **B08c-am** | **ĐỐI CHỨNG ÂM:** bảng kê khai phí **SAI** (+1.000đ) | ✅ ĐẠT | `khớp=0 · phi_lech=1 · đã áp=0` — bị bắt, **không** áp vào sổ |
| **B08c** | nạp bảng kê J&T | ✅ ĐẠT | `HTTP 201 · đợt=2 · nạp=1 · cột nhận ra=[cod_hang_bao, ky_thanh_toan, ma_van_don, phi_hang_bao, trang_thai_hang]` |
| **B08d** | đối chiếu đợt | ✅ ĐẠT | `khớp=1` · mọi nhóm lệch = 0 |
| **B08e** | duyệt đợt → **ÁP VÀO SỔ** | ✅ ĐẠT | `đã áp=1 · bỏ qua=0 · lỗi=[]` |
| **B08f** | sổ COD sau đối soát | ✅ ĐẠT | `dự kiến=250000 · hãng báo=250000 · trạng thái=COD_RECONCILED` |
| **B08g** | bảng COD qua HTTP | ✅ ĐẠT | `1` dòng, đúng đơn thử |
| **B08h** | kiểm nhật ký tài chính (móc băm) | ✅ ĐẠT | `{"ok": true, "so_dong": 8, "dong_hong": []}` |
| **B09** | HUỶ ĐƠN THỬ | ✅ ĐẠT | `HTTP 200 · trạng thái=huy` |
| **B10** | đối chiếu cuối lượt — audit | ✅ ĐẠT | 13 dòng audit |
| **B10b** | không đơn nào đi ra ngoài hệ | ✅ ĐẠT | mọi lượt qua loopback · không tunnel |

**Tổng: đạt 29 · hỏng 0 · BLOCKED 2.** Mã thoát **0**. Báo cáo JSON:
`$VIP_HUB_DATA/g15_harness/bao-cao-g15.json`.

---

## 2. HAI CHỖ HARNESS ĐO RA ĐIỀU NGƯỢC VỚI ĐIỀU DỄ TƯỞNG

### 2.1 `tc_cod` **KHÔNG** có dòng ngay khi tạo đơn — và đó là ĐÚNG

Lượt chạy đầu của harness khẳng định "đơn thử phải có dòng COD trong sổ" và **HỎNG**. Đọc mã
thì thấy phép khẳng định của **harness** sai, không phải hệ:

`tai_chinh.mo_so_cod()` chỉ được gọi từ đường **ĐỐI SOÁT** (`doi_soat.duyet_dot`). Lý do nằm
ngay trong docstring của chính hàm đó: *"`COD_EXPECTED` CỐ Ý không sinh bút toán: chưa ai thu
đồng nào, ghi vào sổ nợ là tạo ra một khoản phải thu không có thật."*

Nên B08 đã được viết lại để đi **ĐÚNG đường nghiệp vụ**: khai COD trên đơn → nạp **bảng kê của
hãng** → đối chiếu → duyệt → **lúc đó** sổ COD mới mở, và mới kiểm số tiền. Đây là ví dụ đúng
của luật §12.1: **sửa phép đo, không sửa hệ** — và phải đọc mã để biết bên nào sai.

### 2.2 Đối chứng âm của đường đối chiếu — chọn sai độ lệch là ĐO SAI NHÓM

Để chứng minh đường đối chiếu **thật sự so số** (chứ không phải chạy qua rồi báo khớp), harness
nạp một bảng kê khai **phí sai** và khẳng định nó bị bắt là `phi_lech`, `khớp=0`, `đã áp=0`.

Bản đầu chọn độ lệch **+5.000đ** → ca **HỎNG**, vì hệ xếp nó vào nhóm
**`dieu_chinh_bat_thuong`**, không phải `phi_lech`:

```
NGUONG_LECH_DONG = 500_000        # lệch tuyệt đối trên 500.000đ
NGUONG_LECH_BPS  = 2000           # hoặc trên 20% số của hệ
```

So với phí hệ `20.200đ`, mức +5.000đ là **~25%** ⇒ vượt ngưỡng 20% ⇒ **đúng nhóm "bất thường"**.
Hệ làm đúng; **phép đo của harness sai nhóm**. Đã đổi sang **+1.000đ** (~5%) → `phi_lech=1`.

**Luật rút ra:** một đối chứng âm phải chọn giá trị rơi vào **đúng nhóm đang muốn đo**. Chọn
sai nhóm thì ca thử báo hỏng trong khi hệ làm đúng — và người ta sẽ đi "sửa" mã đang chạy đúng.

---

## 3. VÌ SAO BƯỚC 5 LÀ `BLOCKED` CHỨ KHÔNG PHẢI "ĐẠT (MOCK)"

Hai chặng **khác nhau về bản chất**, không chỉ khác về cấu hình:

| | Chặng MOCK (đã chạy) | Chặng SANDBOX (BLOCKED) |
|---|---|---|
| Adapter | `mock` | HTTP thật tới hãng — **mã HTTP thật CHƯA được viết** (`TRANSPORT_THAT_DA_VIET = False`) |
| Xác thực | chữ ký của chính hệ | `apiAccount` + `digest` + `timestamp` của hãng |
| Callback | `hub_hmac` (HMAC-SHA256, bí mật của hệ) | **`jt_digest`** = `base64(md5(bizContent + privateKey))` |
| Credentials | chuỗi demo bất kỳ | **`V-13906-05` CHƯA CẤP** |
| Quyền gọi hãng | không cần | **`V-G09-01` CHƯA CẤP** |

Một lượt **mock xanh KHÔNG** là bằng chứng rằng đường sandbox chạy được. Nó chỉ là bằng chứng
rằng **đường mã phía sau adapter** đúng. Nên nó được ghi là `B05-MOCK`, **không** phải `B05`.

**Điểm khác biệt nguy hiểm nhất là sơ đồ ký callback.** `hub_hmac` dùng HMAC-SHA256; `jt_digest`
dùng **MD5 trần**. Hai thứ này **không** thay thế được cho nhau, và cái đã chứng minh được là
cái **yếu hơn**. Ghi ra để không ai đọc "callback ĐẠT" rồi tưởng đường của hãng đã được kiểm.

---

## 4. CHẠY LẠI

```bash
sh trien_khai/g15/chay_harness.sh
# hoặc, khi cần giữ nền để soi:
sh trien_khai/g15/chay_harness.sh --giu-nen
```

`chay_harness.sh` tạo nền riêng dưới `$VIP_HUB_DATA/g15_harness` (mặc định
`/tmp/veh_data_ag04/g15_harness`), **xoá nền cũ của chính nó** trước khi chạy, và **tắt máy
chủ theo ĐÚNG PID** đã giữ — **không** `pkill`, **không** `killall` (`CLAUDE.md` §16.7).

| Thông số | Giá trị |
|---|---|
| Bind | `127.0.0.1`, cổng **ngẫu nhiên 18000–19999** (cổng cố định gây HỎNG GIẢ khi hai worktree chạy cùng lúc) |
| CSDL | Nền **tạm** riêng, `migrate.py` + `khoi_tao.py` tự chạy |
| Adapter | **MOCK** · `CHO_PHEP_LIVE=False` |
| Thời gian | ~4–6 giây |

---

## 5. PHẠM VI — VÀ CÁI GÌ **NẰM NGOÀI**

**Đã đo:** 10 bước qua **HTTP thật** trên `127.0.0.1` · CSDL SQLite tạm · adapter MOCK ·
callback `hub_hmac` · đường đối soát thật (nạp bảng kê → đối chiếu → duyệt → sổ COD) ·
idempotency `event_id` · chữ ký sai bị từ chối · đối chứng âm của đối chiếu · kiểm mật khẩu
không lọt log (ở bộ khác).

**NẰM NGOÀI:**
- **J&T sandbox thật** — `V-13906-05` + `V-G09-01` chưa cấp. **BLOCKED.**
- **Callback `jt_digest` thật** — chưa có header digest của hãng. **BLOCKED.**
- **Deploy · VPS · staging · TLS thật · tunnel** — `V-G11-01` chưa cấp.
- **Mã HTTP thật của adapter J&T chưa được viết** (`TRANSPORT_THAT_DA_VIET = False`).
- Nhiều tiến trình · tải · dữ liệu lớn · Safari/Firefox · hãng khác (VTP/GHN/GHTK/Ninja).

**Không tạo một đơn vận chuyển thật nào.** Mọi đơn trong harness nằm trong CSDL **tạm** đã bị
xoá khi lượt chạy kết thúc, và mọi lượt gọi hãng đều dừng ở adapter MOCK.
