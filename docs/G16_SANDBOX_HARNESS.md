# G16-A — HARNESS NGHIỆM THU SANDBOX: **MOCK**, LOOPBACK, VÀ HAI CHẶNG `BLOCKED`

Mã việc: **directive mục 15** · làn: **AG-04 (WEBHOOK)** · ngày **15/10/2026**.
Mã nguồn: `trien_khai/g16/` (`chot_an_toan.py` · `harness_nghiem_thu.py` · `chay_harness.sh`).
Chạy: `sh trien_khai/g16/chay_harness.sh`

> **Kết quả lượt chạy 15/10/2026: đạt 32 · ĐẠT (MOCK) 12 · hỏng 0 · `BLOCKED` 2 · bỏ qua 0**
> (mã thoát **0**). Hai mục `BLOCKED` là chặng **gửi sang J&T sandbox** và **callback theo sơ đồ
> của hãng** — **không được tính là đạt**, và báo cáo JSON ghi chúng thành một mục riêng.

---

## 1. VÌ SAO CÓ HARNESS NÀY, KHI ĐÃ CÓ BỘ THỬ

Bộ thử (`app/thu/thu_webhook_jt.py`) kiểm **hành vi từng điểm**: mỗi ca là một khẳng định hẹp,
chạy thuần trong tiến trình. Nó rất tốt ở việc đó và **không** thay thế được.

Harness này kiểm **một vòng đời đi hết đường**: đăng nhập → chọn tenant → tài khoản hãng → tạo
đơn → gửi → callback → hành trình → COD → huỷ → đối chiếu, **qua HTTP thật** trên `127.0.0.1`,
với **CSDL tạm** và **adapter MOCK**. Khác biệt quan trọng nhất không nằm ở số phép đo, mà ở chỗ
harness **được phép nói `BLOCKED`**:

> Một bộ thử chỉ có hai phán quyết ĐẠT/HỎNG sẽ **buộc** chặng sandbox phải chọn một trong hai —
> và cả hai đều sai: báo ĐẠT là nói dối, báo HỎNG là báo hỏng giả (chặng đó *không thể* chạy,
> không phải *chạy không được*). `BLOCKED` là phán quyết **thứ ba**, và nó mang theo **chính xác
> cái còn thiếu**.

Và `ĐẠT (MOCK)` **không phải** `ĐẠT`: nó chỉ chứng minh **đường mã phía sau adapter** đúng, không
chứng minh đường sandbox chạy được.

---

## 2. SÁU CHỐT AN TOÀN — harness **TỪ CHỐI CHẠY** nếu mất một cái

| # | Chốt | Vì sao |
|---|---|---|
| 1 | `VIP_HUB_DATA` phải nằm trong thư mục **TẠM**, và **không** được là `app/du-lieu/` | Kịch bản TẠO tenant, tài khoản hãng, đơn, sự kiện webhook **thật** trong CSDL. Chạy lên dữ liệu thật là làm bẩn dữ liệu đang dùng |
| 2 | `VIP_HUB_BIND` phải **trống** hoặc là loopback | `server.py` mặc định bind `127.0.0.1`, nhưng biến môi trường đổi được — mở cổng ra Internet là `V-G11-01`, **CHƯA CẤP** |
| 3 | Mọi adapter trong `adapter._DANG_KY` phải có `CHO_PHEP_LIVE is False` | Một harness "thử" mà mở được cửa gọi hãng thật là thứ **nguy hiểm hơn** không có harness |
| 4 | `cau_hinh.JT_CHO_PHEP_SANDBOX` và `JT_CHO_PHEP_PRODUCTION` phải `False`, **và** `adapter_jt.moi_truong_duoc_chay()` phải nói **cùng điều** | Hai nguồn lệch nhau là lúc một trong hai đã bị sửa mà không ai thấy. Đọc **nguồn sự thật**, không đọc bản sao |
| 5 | Cờ `VIP_G16_CHO_PHEP_GOI_HANG` phải **không** bật | Có mặt để một lượt chạy "quên" **không thể** biến harness MOCK thành harness gọi hãng |
| 6 | Đích phải là loopback (`127.0.0.1`/`localhost`/`::1`) | Không tên miền, không IP ngoài, không tunnel |

### Bộ dò chốt **có tự kiểm** — `--tu-kiem`, 10 cấu hình tổng hợp

```bash
python3 trien_khai/g16/chot_an_toan.py --tu-kiem
```

```
TỰ KIỂM: 10/10 ca đạt · 0 hỏng
Bộ dò bắt ĐÚNG chốt ở cả 10 cấu hình ⇒ lời khai 'TỪ CHỐI CHẠY' mới có nghĩa.
Dữ kiện lớp vận chuyển: {'http_jt_co_that': True, 'cau_hinh.JT_CHO_PHEP_SANDBOX': False,
 'cau_hinh.JT_CHO_PHEP_PRODUCTION': False, 'adapter_cho_phep_live': {'jt': False, 'vtp': False}}
```

Một ca **ĐỐI CHỨNG DƯƠNG** (cấu hình đủ chốt phải **đi qua**) + **9 ca hỏng**. Thiếu ca đối chứng
dương thì một bộ dò `return ["từ chối"]` cũng "bắt được" cả 9 ca hỏng và trông như đang hoạt động.

Mỗi ca hỏng còn phải bị bắt bởi **ĐÚNG chốt đang muốn đo** — chỉ kiểm "có bị từ chối không" là
chưa đủ.

### ⚠️ Bài học THẬT của lượt này — bắt đúng kết quả, **sai lý do**

Trong lúc lượt này đang chạy, làn AG-03 đổi chữ ký `adapter_jt.moi_truong_duoc_chay()` từ **hai**
tham số xuống **một**. Ngay lập tức ba ca `G`/`H`/`I` của bộ tự kiểm **"đạt"** — nhưng vì bị bắt
bởi một `TypeError`, **không phải** bởi chốt mà chúng định đo:

```
✗ [A] cấu hình ĐỦ CHỐT (đối chứng dương) — phải ĐI QUA
      MONG ĐỢI từ chối=False · THỰC TẾ=True · lý do=không kiểm được cửa môi trường của
      adapter_jt (TypeError: moi_truong_duoc_chay() takes 1 positional argument but 2 were given)
```

Bộ tự kiểm đã **thoát khác 0** và **chặn cả lượt chạy** — đúng việc nó phải làm. Đã sửa: chốt 4
đọc thẳng `cau_hinh` (nguồn sự thật), hàm dẫn xuất của adapter chỉ là phép **đối chiếu chéo**, và
phép kiểm "bắt đúng chốt" được **thêm vào** để lần sau không có ca nào đạt nhờ lý do khác.

**Đây là lý do tồn tại của một bộ tự kiểm:** nếu chỉ đếm "mấy ca đạt", lượt đó đã được đọc là
*"9/9, chốt an toàn hoạt động tốt"* — trong khi ba chốt trong số đó **không hề được đo**.

---

## 3. KỊCH BẢN — KẾT QUẢ THẬT

| Mã | Bước | Phán quyết | Bằng chứng đo được |
|---|---|---|---|
| **G01** | ĐĂNG NHẬP | ✅ ĐẠT | `HTTP 200` · tạo **hai** tenant thử + owner qua cửa platform (`HTTP 201`) |
| **G02** | CHỌN TENANT | ✅ ĐẠT | `tenant=3` đến **từ PHIÊN**, không từ body · `vai_tro=TENANT_OWNER` |
| **G03** | CHỌN TÀI KHOẢN J&T | ✅ ĐẠT | `HTTP 201 · id=5 · hãng=jt · môi trường=mock` |
| **G03b** | môi trường tài khoản phải là `mock` | ✅ ĐẠT (MOCK) | nếu là `sandbox`/`production` thì harness **DỪNG cả lượt** |
| **G03c** | credentials + secret mã hoá at-rest | ✅ ĐẠT | dạng `v3$<key_id>$…` — **chỉ kiểm dạng, KHÔNG in giá trị** |
| **G04** | TẠO ĐƠN THỬ | ✅ ĐẠT | `HTTP 201 · id=1 · mã=T3-000001 · COD=250000` |
| **G05** | **GỬI SANG J&T SANDBOX** | ⛔ **BLOCKED** | thiếu: `V-13906-05` (credentials sandbox) · `V-G09-01` (gọi API hãng, kể cả sandbox) |
| **G05-MOCK** | chặng MOCK của **cùng đường mã** | ✅ ĐẠT (MOCK) | `HTTP 200 · mã vận đơn=JTVN… · trạng thái=da_gui` |
| **G05b** | nhãn KHÔNG phải nhãn thật | ✅ ĐẠT (MOCK) | `nhan_that=False · la_mock=True` |
| **G06a** | **ĐỐI CHỨNG DƯƠNG**: callback hợp lệ được nhận | ✅ ĐẠT (MOCK) | `HTTP 202 · su_kien_id=1 · {"code":1,…}` |
| **G06a2** | sự kiện xử xong, trục GIAO VẬN đổi | ✅ ĐẠT (MOCK) | `trạng thái=xong · trục=lay_hang` |
| **G06b** | gửi lại y nguyên ⇒ idempotent | ✅ ĐẠT (MOCK) | `HTTP 200` · sự kiện **1→1** · cùng `sk_id` |
| **G06b2** | chống trùng ở **TẦNG CSDL** | ✅ ĐẠT | nhồi thẳng bằng SQL vẫn `IntegrityError` |
| **G06c** | chữ ký **SAI** | ✅ ĐẠT | `HTTP 401` · số sự kiện **không đổi** |
| **G06d** | **CHÉO TENANT** | ✅ ĐẠT (MOCK) | payload khai tenant B ⇒ đơn của A **đi tiếp**, `webhook_claim_tenant_bi_bo_qua` 0→1 |
| **G06d2** | tenant B không bị chạm | ✅ ĐẠT | tenant B: **0 đơn · 0 sự kiện** |
| **G06e-110** | mã `110` (D-4) | ✅ ĐẠT (MOCK) | `can_soat=1 · trang_thai_chuan=None` · đơn **giữ nguyên** |
| **G06e-9999** | mã lạ | ✅ ĐẠT (MOCK) | như trên |
| **G06e2** | mã chưa xác minh **không chạm sổ COD** | ✅ ĐẠT | `tc_cod`/`tc_cod_chuyen`/`tc_but_toan` **0→0** |
| **G06e3** | không bị đánh dấu giao thành công | ✅ ĐẠT | trục giao vận ≠ `giao_thanh_cong` |
| **G06-SANDBOX** | **callback theo sơ đồ `jt_digest` của hãng** | ⛔ **BLOCKED** | `V-G09-01` + `V-13906-05` · **và** câu 24 (sandbox có đẩy callback không) · **và** câu 6–7 (khoá ký + chuỗi ký) |
| **G06-SANDBOX2** | mức xác thực không bị tự nâng | ✅ ĐẠT | `sơ đồ=jt_digest · mức=DOCUMENTED` |
| **G07a** | sự kiện đến **MUỘN** không kéo lùi | ✅ ĐẠT (MOCK) | trục=`dang_giao` (hạng 3) sau khi bản tin cũ đến sau |
| **G07b** | đồng bộ **hành trình** | ✅ ĐẠT (MOCK) | 7 mốc, **3 mốc nguồn `webhook:…`** · `nguon_du_lieu=don_lich_su (CSDL nội bộ) — KHÔNG gọi hãng` |
| **G07c** | mỗi lượt đổi trạng thái có dòng lịch sử (§11) | ✅ ĐẠT | 7 dòng `don_lich_su` |
| **G07d** | cửa xem sự kiện webhook | ✅ ĐẠT | `HTTP 200 · 6 sự kiện` |
| **G07e** | đường polling dự phòng | ✅ ĐẠT (MOCK) | `HTTP 200 · da_hoi=0` |
| **G08a** | số COD trên đơn không bị callback làm đổi | ✅ ĐẠT | `don_hang.cod=250000` |
| **G08b** | sổ COD **chưa** mở vì callback | ✅ ĐẠT | **0** dòng `tc_cod` cho đơn — **đúng thiết kế** |
| **G08c** | **ĐỐI CHỨNG DƯƠNG**: sổ COD **chỉ** mở qua đường đối soát | ✅ ĐẠT | nạp bảng kê → duyệt ⇒ `dự kiến=250000 · hãng báo=250000 · COD_RECONCILED` |
| **G08d** | bảng COD qua HTTP | ✅ ĐẠT | 1 dòng, đúng đơn thử |
| **G08e** | kiểm nhật ký tài chính (móc băm) | ✅ ĐẠT | `{"ok": true, "so_dong": 5, "dong_hong": []}` |
| **G09** | HUỶ ĐƠN THỬ | ✅ ĐẠT | `HTTP 200 · trạng thái=huy` |
| **G10a** | đối chiếu hành trình: bất biến chéo tenant | ✅ ĐẠT | `lech_tenant=[]` · `bat_bien_tenant_dat=True` |
| **G10b** | đối chiếu **thấy đúng** sự kiện cần người soát | ✅ ĐẠT | 2 sự kiện `can_soat=1`: `110`, `9999` |
| **G10c** | audit ghi vòng đời lượt thử | ✅ ĐẠT | 23 dòng audit |
| **G10d** | không lượt nào ra ngoài loopback | ✅ ĐẠT | 29 lượt HTTP, **tất cả** tới `http://127.0.0.1:<cổng>` |
| **G11a** | **đúng MỘT** nơi ghi watermark, chỉ khi ĐƯỢC ÁP | ✅ ĐẠT | 1 câu `UPDATE` cột mốc + điều kiện `ap_dung and moc` |
| **G11b** | tầng đọc còn lọc `trang_thai_chuan IS NOT NULL` | ✅ ĐẠT | bộ lọc còn nguyên (cứu dữ liệu do **mã CŨ** ghi) |
| **G11c** | webhook không có cửa gọi mạng, không mở LIVE | ✅ ĐẠT | không `urllib.request`/`socket`/`http.client`/`CHO_PHEP_LIVE = True` |
| **G11d** | ràng buộc `UNIQUE` có thật **trong CSDL đang chạy** | ✅ ĐẠT | `sqlite_master.wh_su_kien` |
| **G11e** | hợp đồng callback ở mức `DOCUMENTED` | ✅ ĐẠT | 18 trường · **10 chỗ BLOCKED** · 0 vi phạm bất biến trung thực |
| **G11f** | **năm chỗ hở Owner chỉ đích danh** đều BLOCKED | ✅ ĐẠT | khoá ký · chuỗi ký · phương thức HTTP · hình dạng phản hồi · chính sách thử lại |
| **G11g** | không câu nào đọc như "đã xác minh với hãng" | ✅ ĐẠT | cảnh báo trong báo cáo máy đọc được |

**Tổng: đạt 32 · ĐẠT (MOCK) 12 · hỏng 0 · `BLOCKED` 2.** Mã thoát **0**.
Báo cáo JSON: `$VIP_HUB_DATA/g16_harness/bao-cao-g16.json`.

---

## 4. VÌ SAO HAI CHẶNG ĐÓ LÀ `BLOCKED` CHỨ KHÔNG PHẢI "ĐẠT (MOCK)"

Hai chặng **khác nhau về bản chất**, không chỉ khác cấu hình:

| | Chặng MOCK (đã chạy) | Chặng SANDBOX (`BLOCKED`) |
|---|---|---|
| Adapter | `mock` | HTTP thật tới hãng — cần `V-G09-01` |
| Xác thực callback | `hub_hmac` (HMAC-SHA256, bí mật của **chính hệ**) | **`jt_digest`** = `base64(md5(bizContent + privateKey))` |
| Credentials | chuỗi demo bất kỳ | **`V-13906-05` CHƯA CẤP** |
| Khoá ký chiều callback | bí mật của hệ, mình tự biết | **CHƯA CÓ TÀI LIỆU** (câu 6–7) |
| Sandbox có đẩy callback không | không áp dụng | **CHƯA BIẾT** (câu 24) |

Hai sơ đồ ký **không thay thế được cho nhau**, và cái đã chứng minh được là cái **yếu hơn**
(`hub_hmac`). Ghi ra để không ai đọc "callback ĐẠT" rồi tưởng đường của hãng đã được kiểm.

---

## 5. CHẠY LẠI

```bash
sh trien_khai/g16/chay_harness.sh              # tự kiểm chốt → dựng nền tạm → chạy → dọn
sh trien_khai/g16/chay_harness.sh --giu-nen    # giữ nền để soi
python3 trien_khai/g16/chot_an_toan.py --tu-kiem
```

`chay_harness.sh` **tự kiểm bộ dò chốt trước** (bộ dò hỏng thì lượt chạy dừng ngay, vì mọi lời
khai "đã từ chối" khi đó vô nghĩa), rồi dựng nền riêng dưới `$VIP_HUB_DATA/g16_harness`
(mặc định `/tmp/veh_g16_ag04/g16_harness`), và **tắt máy chủ theo ĐÚNG PID** đã giữ —
**không** `pkill`, **không** `killall`.

| Thông số | Giá trị |
|---|---|
| Bind | `127.0.0.1`, cổng do **hệ điều hành cấp** (`bind` cổng **0**) — cổng cố định gây HỎNG GIẢ khi bốn làn chạy cùng lúc |
| CSDL | Nền **tạm** riêng; `migrate.py` + `khoi_tao.py` tự chạy |
| Adapter | **MOCK** · `CHO_PHEP_LIVE=False` |
| Báo cáo | JSON: `$VIP_HUB_DATA/g16_harness/bao-cao-g16.json` (bước · phán quyết · bằng chứng · mục `BLOCKED` riêng) |
| Thời gian | ~4–6 giây |

---

## 6. PHẠM VI — VÀ CÁI GÌ **NẰM NGOÀI**

**Đã đo:** 11 nhóm bước qua **HTTP thật** trên `127.0.0.1` · CSDL SQLite **tạm** · adapter MOCK ·
callback `hub_hmac` tự ký cục bộ · idempotency `event_id` · chữ ký sai bị từ chối · chéo tenant ·
mã `110` + mã lạ ⇒ `NEEDS_REVIEW` với **0 dòng** sổ COD · sự kiện đến muộn · đồng bộ hành trình ·
đường đối soát thật · huỷ đơn · audit · **năm bất biến an toàn** + bốn chốt cấu trúc · hợp đồng
callback ở mức `DOCUMENTED`.

**NẰM NGOÀI:**
- **J&T sandbox thật** — `V-G09-01` + `V-13906-05` chưa cấp. **`BLOCKED`.**
- **Callback `jt_digest` thật** — chưa có khoá ký/chuỗi ký (câu 6–7) và chưa biết sandbox có đẩy
  callback không (câu 24). **`BLOCKED`.**
- **Deploy · VPS · staging · TLS thật · tunnel** — `V-G11-01` chưa cấp.
- **Nhiều tiến trình · tải · dữ liệu lớn · hãng khác (VTP)**.
- **`app/http_jt.py`** (lớp HTTP thật, AG-02) **có tồn tại** trên đĩa nhưng harness **không gọi
  tới nó** — báo cáo JSON ghi dữ kiện này ở `moi_truong_van_chuyen` để người đọc không tưởng
  nhầm rằng có lớp đó nghĩa là đã gọi được hãng.

**Không tạo một đơn vận chuyển thật nào.** Mọi đơn trong harness nằm trong CSDL **tạm**, và mọi
lượt gọi hãng đều dừng ở adapter MOCK.
