# G16_TRANSPORT — LỚP HTTP THẬT CHO J&T (làn AG-02)

> **Trạng thái: ĐÃ VIẾT + ĐÃ ĐO — nhưng CHỈ đo trên STUB CỤC BỘ `127.0.0.1`.**
> **CHƯA từng có một lượt gọi hãng nào, kể cả sandbox.** `V-G09-01` và `V-13906-05` **CHƯA ĐƯỢC CẤP**
> (`SHARED_CONTRACTS.md` §37, §40), credentials **CHƯA TỒN TẠI** (§38), `CHO_PHEP_LIVE` **CHƯA mở**.
> Tài liệu này **KHÔNG** nói — và không được đọc thành — "LIVE VERIFIED", "chạy được với hãng",
> hay "sẵn sàng production". G16-A **không thể** đạt mức đó. Xem §8.
>
> Đây là soát **do một làn AI** thực hiện, không phải người. Bộ thử xanh **không phải** lời cho phép.

**Nền:** `integration/g13-g15` @ `449bb2d` (KHÔNG phải `main`). **Làn:** AG-02 HTTP TRANSPORT, cổng G16-A.

---

## 1. ĐÃ LÀM GÌ — và cái gì CỐ Ý KHÔNG làm

| Tệp | Trạng thái | Nội dung |
|---|---|---|
| `app/http_jt.py` | **MỚI** (705 dòng) | `gui_form()` — MỘT lượt POST form thật, danh sách trắng máy chủ, phân loại 3 kết cục, che bí mật |
| `app/thu/stub_jt.py` | **MỚI** (340 dòng) | Máy chủ J&T giả trên `127.0.0.1` cổng 0, 12 chế độ trả lời, ghi lại **byte thật** đã nhận |
| `app/thu/thu_http_jt.py` | **MỚI** (1078 dòng) | **37 ca** + chốt chặn mạng toàn cục + 4 bộ dò tự kiểm (3 đột biến tiến trình con + 1 soát AST) |
| `docs/G16_TRANSPORT.md` | **MỚI** | Tài liệu này |

**KHÔNG sửa một tệp nào của làn khác.** Đo được (`git status --porcelain`, 15/10/2026): ba tệp của
tôi là `??` (mới hoàn toàn); các tệp ` M` trong cây (`adapter_jt.py`, `webhook.py`, `thu_adapter_jt.py`,
`thu_hop_dong_jt.py`, `thu_webhook_jt.py`) là của **AG-03/AG-04**. `transport.py`, `csdl.py`,
`migrate.py`, `server.py`, `cau_hinh.py`, `chay_tat_ca.sh`: **không đụng**.

**CỐ Ý KHÔNG làm:** không thêm phụ thuộc ngoài (máy này **không có** `requests` — đo được:
`ModuleNotFoundError: No module named 'requests'`; lớp này dùng `http.client`/`ssl`/`socket` của
stdlib); không tự thử lại; không đi theo chuyển hướng; không ghi log; không mở cổng ra Internet;
không mở `CHO_PHEP_LIVE`; không gọi hãng.

---

## 2. HỢP ĐỒNG §36 — MẶT TIẾP XÚC (đúng nguyên văn, không thêm không bớt)

```python
MOCK = "mock"; SANDBOX = "sandbox"; PRODUCTION = "production"

class TraLoiHTTP:            # ĐÚNG BA trường, đúng thứ tự hợp đồng
    ma_http: int             # mã HTTP; 0 nếu không có phản hồi
    than: bytes              # thân thô, NGUYÊN VĂN
    headers: dict

def gui_form(url, headers, body: dict, *, timeout: float) -> TraLoiHTTP
```

`TraLoiHTTP` dùng `__slots__ = ("ma_http", "than", "headers")` — có ca thử khẳng định **đúng ba
trường** (`test_a4`), để một bản vá sau này không lặng lẽ nhét thêm trường vào hợp đồng đã đóng băng.

**Thêm vào (KHÔNG phá hợp đồng — chỉ là tên mới, không tên nào bị đổi):**

| Tên | Việc |
|---|---|
| `chan_moi_truong(mt)` | §37: `mock` mở; `sandbox`/`production` ném `PermissionError` kèm **lý do đọc được** (nêu đúng mã việc còn thiếu) |
| `CHO_PHEP_MOI_TRUONG` | `{mock: True, sandbox: False, production: False}` — chốt chặn ĐỌC ĐƯỢC, không phải chỗ để mở |
| `host_duoc_phep(host)` / `tach_url(url)` | Danh sách trắng máy chủ; `tach_url` chạy **trước mọi thao tác mạng** |
| `che_bi_mat(du_lieu, can_che)` | Che mọi giá trị **đã gửi đi** nếu hãng echo lại |
| `KET_CUC_QUA_HAN_MUC` | Kết cục riêng của `429`: hãng bảo chờ — **không lẫn với 5xx** (`khong-biet`) trong log |
| `TRUONG_CREDENTIAL` | Bốn **TÊN** trường credentials (§38) — giá trị của chúng bị che **bất kể độ dài** (§5.1) |
| `KET_CUC_HANG_TU_CHOI` / `KET_CUC_KHONG_BIET` / `KET_CUC_KHONG_GUI_DI` | Ba kết cục, **không gộp** (§4) |
| `HET_GIO_KET_NOI_TOI_DA = 5.0` | Hạn NỐI riêng, tường minh |
| `.cho_giay` (trên ngoại lệ) | Gợi ý chờ (giây) đã **kẹp trần `transport.CHO_TOI_DA`**; đi vào đúng tham số `transport.LoiTamThoi(…, cho_giay=…)` |

### Ngoại lệ: luôn là `transport.LoiTamThoi` hoặc `transport.LoiVinhVien`, kèm thuộc tính máy đọc được

| Tình huống | Loại | `.loai` | `.ket_cuc` | `.timeout` | `.ma_http` |
|---|---|---|---|---|---|
| **2xx — hãng trả lời** | *trả về* `TraLoiHTTP` | — | — | — | 200–299 |
| 3xx — chuyển hướng (**không đi theo**) | `LoiVinhVien` | `http-3xx` | `hang-tu-choi` | False | 3xx |
| 4xx — **TRỪ 408/429** | `LoiVinhVien` | `http-4xx` | `hang-tu-choi` | False | 4xx |
| **429** — bị giới hạn tần suất (hãng bảo chờ) | `LoiTamThoi` | `http-429` | **`qua-han-muc`** | **True** | 429 |
| **408** — hãng không nhận kịp yêu cầu | `LoiTamThoi` | `http-408` | **`khong-gui-di`** | **True** | 408 |
| 5xx | `LoiTamThoi` | `http-5xx` | `khong-biet` | **True** | 5xx |
| Mã HTTP ngoài mọi nhóm | `LoiVinhVien` | `http-la` | `khong-biet` | False | mã |
| Hết giờ **chờ phản hồi** | `LoiTamThoi` | `het-gio` | `khong-biet` | **True** | 0 |
| Hết giờ **đọc thân** (thân đứt giữa chừng) | `LoiTamThoi` | `than-doc-do` | `khong-biet` | **True** | mã **đã** nhận |
| Hãng đóng kết nối giữa lượt | `LoiTamThoi` | `ket-noi-dut` | `khong-biet` | **True** | 0 |
| Từ chối kết nối (cổng đóng) | `LoiTamThoi` | `tu-choi-ket-noi` | **`khong-gui-di`** | **True** | 0 |
| Không phân giải được tên | `LoiTamThoi` | `phan-giai-ten` | `khong-gui-di` | **True** | 0 |
| Chứng thư TLS sai | `LoiVinhVien` | `tls-chung-that` | `khong-gui-di` | False | 0 |
| Host ngoài danh sách trắng | `LoiVinhVien` | `host-bi-tu-choi` | `khong-gui-di` | False | 0 |
| URL/tham số sai (kể cả `timeout` ≤ 0, NaN) | `LoiVinhVien` | `url-sai`/`tham-so-sai` | `khong-gui-di` | False | 0 |
| Ngoại lệ KHÔNG RÕ loại | `LoiVinhVien` | `loi-khong-ro` | `khong-biet` nếu đã gửi, else `khong-gui-di` | False | 0 |

**Vì sao "từ chối kết nối" vẫn `timeout=True`:** `ket_cuc='khong-gui-di'` là sự thật CHÍNH XÁC (biết
chắc yêu cầu chưa ra khỏi máy ⇒ thử lại an toàn). Nhưng cờ thô `timeout` cố ý giữ `True`, vì ở tầng
`KetQuaHang` (§4) chỉ có BA kết cục: `ok` / *hãng từ chối* / *không biết*. Hãng **chưa hề nói gì**,
nên gán nó vào "hãng từ chối" là **làm mất một đơn** — hướng sai nguy hiểm hơn. Người gọi đọc
`ket_cuc` khi cần phân biệt; đừng bao giờ gộp `khong-gui-di` vào "hãng từ chối".

**Ngoại lệ lạ ⇒ VĨNH VIỄN (cố ý):** một lỗi chưa từng gặp mà đem thử lại mù quáng là cách tạo đơn
trùng. Thà mất một lượt còn hơn gửi lại một đơn đã vào hãng.

### Hai hạn thời gian, đều TƯỜNG MINH

- **Hạn ĐỌC** = `timeout` (tham số hợp đồng) — siết lên socket **sau khi đã nối**.
- **Hạn NỐI** = `min(timeout, HET_GIO_KET_NOI_TOI_DA=5.0)` — độc lập, để một host nuốt SYN không treo
  giao dịch tới hạn của hệ điều hành.
- Không có nhánh nào chờ vô hạn. `timeout` ≤ 0 / NaN / vô cùng / không phải số ⇒ `LoiVinhVien`
  (`tham-so-sai`) **trước khi** mở socket.

---

## 3. BA LUẬT CỨNG §36 — mỗi luật có ca thử đo được

| Luật | Ca thử đo nó |
|---|---|
| **1. Thao tác GHI không tự thử lại.** `http_jt` không có vòng lặp; nó chỉ ném đúng loại lỗi | `test_b1/b2/b5/b6`: sau mỗi lượt hỏng, stub đếm được **đúng 1** yêu cầu. `test_b5` chạy `transport.goi()` THẬT: `trackOrder` → 3 lượt + backoff `[0.2, 0.4]`; `createOrder` → **1 lượt**, không chờ backoff; `createOrder` + `co_khoa_chong_trung=True` (khóa `txlogisticId` của J&T) → 3 lượt; `so_lan=3` nhưng `duoc_thu_lai=False` → vẫn **1 lượt** |
| **2. Danh sách trắng máy chủ.** Chỉ 2 host J&T + `127.0.0.1`/`localhost` | `test_d1` (đếm số lần `connect()`: **0** khi bị từ chối, **>0** khi host hợp lệ), `test_d2` (host na đuôi, `http://` trên host hãng, cổng 8443 ⇒ chặn), `test_d3` (canh hai host không trôi khỏi `adapter_jt.HOST_API` bằng **AST**, không import), `test_b4` (302 sang host khác: không có lượt nối nào ra ngoài loopback) |
| **3. Ba kết cục KHÔNG gộp.** Kết cục thứ ba không bao giờ là thành công | `test_f1` (ok vs hãng từ chối: phân biệt bằng `code` trong thân **nguyên văn**), `test_f2` (hết giờ / đứt / thân đọc dở ⇒ **ném**, không có `TraLoiHTTP` nào), `test_c2` (**then chốt**: HTTP 200 + `Content-Length` lớn hơn số byte thật ⇒ thân đọc dở ⇒ **ném**, không trả về thân cắt khúc), `test_c3` (đứt giữa lượt: yêu cầu ĐÃ tới nơi ⇒ `khong-biet`), `test_c4` (từ chối kết nối ⇒ `khong-gui-di`, **khác** hết giờ và **khác** hãng từ chối), `test_b7`/`test_b8` (429 ⇒ `qua-han-muc`, 408 ⇒ `khong-gui-di`: cùng `LoiTamThoi` nhưng **khác** 5xx và **khác** nhau) |

---

## 4. BẰNG CHỨNG — lệnh thật, kết quả thật

### 4.1 Bộ thử của làn này

```bash
cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
rm -rf /tmp/veh_g16_ag02 && mkdir -p /tmp/veh_g16_ag02
VIP_HUB_DATA=/tmp/veh_g16_ag02 python3 app/thu/thu_http_jt.py -v
```

**Kết quả thật (dán nguyên văn phần cuối):**

```
Ran 37 tests in 6.269s

OK
EXIT=0
```

37 ca, chia 9 nhóm:

| Nhóm | Ca | Đo cái gì |
|---|---|---|
| A — gói yêu cầu | a1–a6 | 4 header bắt buộc đúng **tên và thứ tự** trên dây · thân form đúng **byte** (UTF-8, đếm `+`, `%2B`, `%26`, `%C6%AF`, vòng tròn `parse_qs`) · **chữ ký tính lại từ chính chuỗi stub đã nhận** · thân trả lời nguyên văn · `Content-Type` tự thêm khi thiếu · `Content-Length` do lớp HTTP đặt |
| B — phân loại | b1–b6 | 5xx/4xx/3xx · không tự thử lại · `transport.goi()` thật: đọc thử lại, ghi thì không |
| **B2 — 408/429** | **b7–b12** | 429 ⇒ `LoiTamThoi` + `qua-han-muc` (khác 5xx) · 408 ⇒ `LoiTamThoi` + `khong-gui-di` · `Retry-After` (số giây, HTTP-date, rác, mốc đã qua) + **kẹp trần** · **hai lớp ĐỒNG Ý** với `loi_hang` trên 7 mã · **soát AST: không `sleep`** · **đầu-cuối qua `transport.goi()`**: chờ `[5.0, 5.0]` / `[0.2, 0.4]` / `[60.0, 60.0]`, `createOrder` 1 lượt |
| C — "không biết" | c1–c5 | hạn ĐỌC ép đúng · **thân đọc dở** · đứt giữa lượt · từ chối kết nối · `goi()` thử lại ca hết giờ |
| D — danh sách trắng | d1–d4 | từ chối **trước khi mở socket** · host na đuôi · không trôi khỏi `adapter_jt` (AST) · tham số sai |
| E — bí mật | e1–e3 | hãng echo lại header+thân+digest: **không** rò ra `str/repr/args/stdout/stderr`, thân gắn ngoại lệ **đã che** · **credential NGẮN hơn ngưỡng vẫn bị che** (e3) |
| F — ba kết cục | f1–f2 | ok vs từ chối · kết cục thứ ba **ném**, không trả về |
| G — tự kiểm bộ dò | g1–g4 | 3 đột biến trong **tiến trình con** + đối chứng dương + tự kiểm chốt chặn mạng (bộ dò `sleep` ở `b11` có đối chứng dương riêng: tiêm `time.sleep`/`sleep`/`transport.ngu` đều bị bắt, `sleep` trong chú thích/chuỗi thì không) |
| H — môi trường §37 | h1 | `mock` mở; `sandbox`/`production` **TỪ CHỐI** kèm mã việc còn thiếu |

### 4.2 Hồi quy toàn dự án (bộ chạy tự dò, có tệp mới của tôi trong đó)

```bash
cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
VIP_HUB_DATA=/tmp/veh_g16_ag02 sh app/thu/chay_tat_ca.sh
```

**Kết quả thật — lượt ĐÓNG BĂNG (15/10/2026 16:04 +07, mã đã đứng yên, xem §9):**

```
  ✓ thu_http_jt.py             37 ca
  ✓ thu_qa_g16.py              61 ca
  ...
  python:   1284 ca · 36 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41 phép đo đạt
  bộ hỏng:  KHÔNG
EXIT=0
```

Con số này khớp **độc lập** với lượt AG-00 tự chạy (`1284 ca · 36 bộ · 0 hỏng · E2E 41/41 · exit 0`).

**Nói thẳng về các lượt TRƯỚC ĐÓ trong cùng buổi (cùng lệnh, cùng cây):** một lượt cho
`1268 ca · bộ hỏng: thu_qa_g16.py thu_qa_jt.py` và một lượt cho `1269 ca · 0 hỏng`. Truy vết lượt
đỏ: cả hai bộ của làn **AG-01** đỏ bên trong `app/adapter_jt.py` (D-9 `chot_chan_anh_xa_area`, làn
**AG-03** đang ghi dở) và trong **tự kiểm bộ dò của chính AG-01** (`test_c5`) — **không** phải bộ của
tôi. Ghi lại cả ba lượt vì "lượt sạch" một mình không cho người đọc biết cây này đang được nhiều làn
ghi đồng thời, và vì `1268`/`1269`/`1284` **đều đúng** — chúng là ba CÂY KHÁC NHAU (§41).

### 4.3 Bộ QA ĐỘC LẬP của AG-01 chạy trên lớp này — 32/32 ĐẠT

`app/thu/thu_qa_g16.py` (làn AG-01, **không phải tôi viết**) có nhóm `T_Transport` đo trực tiếp
`app/http_jt.py` bằng stub riêng của họ:

```bash
VIP_HUB_DATA=/tmp/veh_g16_ag02 python3 app/thu/thu_qa_g16.py T_Transport
→ Ran 32 tests in 19.756s / OK
```

Đây là **đối chứng độc lập** cho lớp này (người viết khác, stub khác, ca khác): t1 vòng lặp nối nội
bộ · t4–t9 danh sách trắng (host ngoài, hậu tố, userinfo, host hãng giả, host trong query, IP viết
kiểu khác) · t17a–t17c chính sách thao tác ghi · t18a canary dài không rò · **t19 thân nguyên văn
từng byte** · t20 không đổi trạng thái toàn cục · t21 `repr` không in thân · **t22 `429`/`408` là TẠM THỜI, 4xx khác vẫn VĨNH VIỄN** — ca của họ khớp đúng hai hằng số `KET_CUC_QUA_HAN_MUC`/`KET_CUC_KHONG_GUI_DI` của tôi, và họ cũng đo đường `Retry-After` + trần.

**Một phát hiện của họ đã được vá trong làn này** (xem §5.1): ca `t18b` của họ **ĐO** cái biên
"credential ngắn hơn ngưỡng che". Đo **TRƯỚC** bản vá:

```
[ĐO] ngưỡng che=8 · giá trị 5 ký tự · rò qua thân=False · rò qua header=True
```

Đo **SAU** bản vá (cùng ca, cùng stub của họ):

```
[ĐO] ngưỡng che=8 · giá trị 5 ký tự · rò qua thân=False · rò qua header=False
```

### 4.4 PHẠM VI — cái gì NẰM NGOÀI mọi con số trên

- **Chưa từng có lượt gọi hãng nào.** Mọi lượt trong bộ thử đi tới stub trên `127.0.0.1`. Điều đó
  được **ÉP BẰNG MÃ**, không bằng lời dặn: `setUpModule` thay `socket.socket.connect` bằng chốt chặn
  chỉ cho loopback đi qua, cộng máy đếm; ca `g4` tự kiểm chính chốt chặn đó (nối ra host ngoài ⇒
  `AssertionError: CHẶN MẠNG`).
- **Chưa đo được:** chữ ký có được J&T chấp nhận không · mã lỗi thật của hãng · TLS/thời gian thật của
  `demoopenapi`/`ylopenapi` · hạn mức gọi (rate limit) thật · proxy · IPv6 · HTTP/2 · keep-alive dùng
  lại giữa các lượt (mỗi lượt một kết nối, đóng sau khi xong).
- **Chưa đo được:** hành vi của hãng khi chữ ký SAI ở tầng thật (stub trả `145003030` theo bảng mã đã
  đọc, nhưng đó là dữ liệu do tôi dựng, không phải hãng nói).
- **Không phải kiểm thử tải/đồng thời:** bộ thử chạy tuần tự trong một tiến trình.

---

## 5. BÍ MẬT — BA LỚP CHẶN, VÀ MỘT CHỖ CỐ Ý KHÔNG CHE

1. **Thông điệp lỗi:** chỉ nêu **TÊN** header, tên trường form, độ dài thân, host/đường dẫn. Mọi
   thông điệp đi qua **một hàm duy nhất** `mo_ta_yeu_cau()` — có ca đột biến riêng (`g3`) chứng minh
   rằng nếu hàm đó in giá trị header ra thì ca rò rỉ **ĐỎ**.
2. **Thân/header gắn vào NGOẠI LỆ** (`than_da_che`, `headers_da_che`): đã **CHE** mọi giá trị **đã gửi
   đi** thay bằng `[DA-CHE]`. **Hai mức** (xem §5.1): giá trị của trường có **TÊN là credential**
   (`TRUONG_CREDENTIAL`: `apiAccount`·`privateKey`·`customerCode`·`password`, cả trong header lẫn
   trong khoá JSON của `bizContent`) bị che **BẤT KỂ ĐỘ DÀI**; giá trị khác che khi dài ≥
   `DAI_TOI_THIEU_DE_CHE = 8` ký tự. Ngưỡng 8 để không phá thông điệp chẩn đoán bằng những giá trị
   ngắn vô hại. Biến thể của phép che có ca đột biến riêng (`g2`).
3. **`repr()`** của `TraLoiHTTP` in **độ dài**, không in thân và không in giá trị header — vì `repr`
   là thứ hay bị nhét vào log nhất. `test_a4`/`test_e2` khẳng định điều đó.

**Đối chứng dương của các ca phủ định này:** `test_e1` chứng minh **trước** rằng bí mật THẬT SỰ đã đi
trên dây (`stub.yeu_cau[-1].header("digest") == digest`) **và** hãng giả THẬT SỰ echo nó lại (thân thô
của stub còn nguyên digest). Không có hai khẳng định đó thì "không thấy bí mật" đúng một cách vô nghĩa.

**CHỖ CỐ Ý KHÔNG CHE — nói thẳng:** `TraLoiHTTP.than` là thân **NGUYÊN VĂN** theo hợp đồng §36; nếu
hãng echo `digest` vào thân của một lượt **2xx** thì nó nằm trong `.than`. Đây là lựa chọn có ý thức:
`.than` là **bằng chứng**, và luật thật sự quan trọng là *không được để bí mật đi vào LOG/ngoại lệ* —
chỗ đó đã che. Rủi ro còn lại: một người gọi tự đem `.than` đi log. Ghi ra đây để không ai tưởng lớp
này che được cả đường đó. `HEADER_KHONG_CHE` (content-type/accept/host…) là các header giao thức,
không đưa vào tập che vì che chúng chỉ làm hỏng chẩn đoán mà không thêm an toàn.

**Không có bí mật nào tồn tại để mà rò:** `gui_form` **không nhận** `privateKey` — nó không bao giờ
giữ khóa riêng, nên không thể in nó. Bốn giá trị dùng trong bộ thử (`KHOA_GIA_DINH`, `ACC_GIA_DINH`,
`TS_GIA_DINH`, `digest`) là **giả định**, chỉ sống trong tiến trình chạy thử.

### 5.1 HAI LỖI TỰ TÌM RA TRONG LÀN NÀY — và đã vá

Ghi lại vì cả hai đều thuộc khuôn "hỏng mà không ai thấy", và vì một trong hai do **làn khác đo**.

**(a) Rò rỉ credential NGẮN hơn ngưỡng che — do bộ QA độc lập AG-01 ĐO được.**
`thu_qa_g16.t18b` đặt một canary **5 ký tự** vào header `apiAccount` và vào `bizContent.password`, cho
stub echo lại, rồi đo. Trước bản vá: `rò qua header=True`. Nguyên nhân: chỉ một ngưỡng 8 ký tự cho MỌI
giá trị, nên `customerCode`/`apiAccount` ngắn (ví dụ `669` trong chính fixture của họ) đi qua **nguyên
văn** vào thân gắn ngoại lệ và vào header phản hồi. **Vá:** tách hai mức theo **TÊN trường** —
`TRUONG_CREDENTIAL` bị che bất kể độ dài; các giá trị khác giữ ngưỡng 8 (để không che vô tội vạ những
con số ngắn). Đánh đổi có ý thức: một credential 1–3 ký tự sẽ làm thông điệp chẩn đoán bị che nhiều —
**thà thông điệp khó đọc còn hơn một credential đi vào log**. Ca `e3` giữ chốt chặn này, kèm đối chứng
dương rằng giá trị 5 ký tự **không** thuộc trường credential thì **vẫn không** bị che (ngưỡng còn tác
dụng). Sau bản vá, chính ca `t18b` của AG-01 đo `rò qua header=False`.

**(b) Một ca HỎNG GIẢ khi hai bản bộ thử chạy song song — tôi tự tìm ra, đã vá.**
Lượt chạy 2 bản song song: một bản `OK`, một bản `FAILED (failures=1)` ở `test_c2`, vì
`stub.than_tra_loi_cuoi` là `None`. Nguyên nhân **không phải mã sản phẩm**: stub ghi bản ghi phản hồi
**sau** khi đã gửi byte (đó mới là bản ghi trung thực), nên client có thể quay về trước khi luồng máy
chủ kịp ghi lại. Đúng khuôn HỎNG GIẢ của N-05, và nếu bỏ qua thì mọi lượt chạy chung cây đều có xác
suất đỏ giả. **Vá:** `CaGoc.cho_tra_loi()` chờ (có hạn 3s) bản ghi xuất hiện rồi mới so. **Đã đo lại:**
3 vòng × 2 bản song song = **6/6 `EXIT=0`**, và 2 bản song song **trong lúc bộ chạy toàn dự án đang
chạy** cũng `EXIT=0` — đúng tình huống đã gây ra lượt đỏ giả.

---

## 6. STUB CỤC BỘ (`app/thu/stub_jt.py`) — vì sao cổng 0, và nó đo được gì

- **Bind `127.0.0.1` + cổng `0`** (hệ điều hành cấp). Bốn làn G16 chạy **đồng thời trong CÙNG một
  cây**; cổng cố định là `Address already in use` khi hai làn trùng nhau — và lỗi đó **trông y hệt**
  một lỗi ngắt quãng của mã sản phẩm (N-05 / R-13). Cổng 0 thì mỗi lượt chạy có cổng riêng.
- **12 chế độ:** thành công (`code:"1"`) · hãng từ chối bằng **mã lỗi thật** (`145005005`,
  `145003030`, … theo bảng đã đọc) · 500 (thân **không** phải JSON) · 400 · 401 · 408 · 429 · 302 sang
  host khác · **echo lại** header+thân (để đo rò rỉ) · **chậm** (ép hết giờ ĐỌC) · **đóng kết nối**
  giữa lượt · **thân thiếu byte** (`Content-Length` lớn hơn số byte thật).
- **Nói đúng giao thức J&T:** trường form `bizContent` chứa **chuỗi** JSON; header
  `apiAccount`/`digest`/`timestamp`; `application/x-www-form-urlencoded`; UTF-8.
- **Đo được ĐÚNG byte đã gửi:** mỗi lượt nhận được ghi lại `than_tho` (bytes), `headers_goc` (tên
  **nguyên chữ hoa/thường + đúng thứ tự**), `phuong_thuc`, `duong_dan`. `da_tra_loi` giữ thân đã trả
  về để so **nguyên văn** với `TraLoiHTTP.than`.
- **`xep_hang_doi(500, 500, thanh_cong)`** — chế độ cho từng lượt kế tiếp, để đo thử lại thật.
- `loi_may_chu` ghi lỗi phía stub (client bỏ đi là chuyện thường ở ca hết giờ) — **không** in ra
  stdout/stderr, để "không rò rỉ qua log" đo được thật.
- Stub **chỉ nghe**, không bao giờ gọi ra ngoài.

---

## 7. `408`/`429` — ĐÃ CHỐT VÀ ĐÃ THI HÀNH (AG-00, 15/10/2026); HAI LỚP NAY ĐỒNG Ý

**Chỗ lệch cũ (do tôi báo, không im lặng):** lớp này gộp **mọi** 4xx vào "vĩnh viễn", trong khi
`loi_hang.tu_http` (dòng 157–177) coi `408 → HET_GIO` và `429 → QUA_HAN_MUC` là **thử lại được** —
cùng MỘT lượt gửi mà hai lớp nói ngược nhau. AG-00 chốt: **cả hai là LỖI TẠM THỜI**; tôi thi hành.

| Mã | `loi_hang.tu_http` nói | `http_jt` (nay) nói |
|---|---|---|
| `429` | `QUA_HAN_MUC`, thử lại được | `LoiTamThoi`, `loai='http-429'`, `ket_cuc='qua-han-muc'`, `gioi_han_tan_suat=True` |
| `408` | `HET_GIO`, thử lại được | `LoiTamThoi`, `loai='http-408'`, `ket_cuc='khong-gui-di'` (hãng không nhận kịp ⇒ chắc chắn CHƯA xử lý gì) |
| 400/401/403/404 | không thử lại | `LoiVinhVien` — **KHÔNG nới** |
| 3xx · 5xx · mã lạ | không đổi | không đổi |

**Ca canh chống lệch (`test_b10`):** so `loi_hang.tu_http(ma).co_the_thu_lai` với lớp lỗi mà `http_jt`
ném ra cho **bảy mã** (400/401/403/404/408/429/500) — phải khớp cả bảy, kèm **đối chứng dương** rằng
bảng phân loại thật sự có CẢ HAI giá trị (nếu mọi mã đều "thử lại được" thì phép so vô nghĩa).

**`Retry-After`:** đọc **cả** số giây **và** HTTP-date; **kẹp trần `transport.CHO_TOI_DA`** — dùng
hằng của AG-00, **không khai trần thứ hai**; không có header (hoặc rác) ⇒ `cho_giay=None` để
`transport.goi()` dùng backoff chính sách; mốc đã qua ⇒ `0.0` (không bao giờ ra số âm).
`gui_form` **KHÔNG BAO GIỜ NGỦ** (`test_b11`, soát bằng AST + mô-đun không nạp `time`): nếu ngủ thì
`createOrder` (`so_lan=3`) treo `3 × trần` trong MỘT yêu cầu HTTP của hệ này và phá §36 luật 1.

**Đo đầu-cuối (`test_b12`, `ngu=` ghi lại thay vì ngủ thật):** `429 + Retry-After: 5` ⇒ `goi()` chờ
`[5.0, 5.0]` · không header ⇒ `[0.2, 0.4]` · `86400` ⇒ `[60.0, 60.0]` · `createOrder` ⇒ **1 lượt**, chờ `[]`.

**AG-00 đo lại độc lập, khớp:** `429 → LoiTamThoi/qua-han-muc · 408 → LoiTamThoi/khong-gui-di ·
400/401/302 → LoiVinhVien · Retry-After: 5 → 5.0 · 86400 → 60.0 · 0 → 0.0 · -3 → 0.0 · rác → None ·
408 + 7 → 7.0 · sleep trong http_jt.py (AST): 0`.

---

## 8. BLOCKED — CHÍNH XÁC CÁI GÌ CÒN THIẾU, AI GỠ

| # | Việc bị chặn | Thiếu CHÍNH XÁC cái gì | Ai gỡ |
|---|---|---|---|
| 1 | **Mọi lượt gọi hãng, kể cả sandbox** | `V-G09-01` **VÀ** `V-13906-05` **CHƯA CẤP** (§37) | anh Thành |
| 2 | **Credentials** | 4 tên trường `apiAccount`·`privateKey`·`customerCode`·`password`, **hai lớp hai nguồn** (§38); đo được: **không có tệp `.env` nào**, `.env.example` không khai khoá J&T nào | J&T + bưu cục |
| 3 | **Xác minh chữ ký thật** | Chưa lượt nào để hãng nói "chữ ký đúng"; câu hỏi **12** (`timestamp`) và **22** (dạng `password`) còn treo | J&T |
| 4 | **TLS/đường mạng thật của hãng** | Chưa đo `demoopenapi.jtexpress.vn` / `ylopenapi.jtexpress.vn` (proxy, chứng thư, IPv6, hạn nối thật) | lượt sau, khi (1) được cấp |
| 5 | **Hạn mức gọi (rate limit) thật** | Tài liệu công khai **không** liệt kê mã vượt hạn mức; `loi_hang` ghi rõ `QUA_HAN_MUC` của J&T hiện chỉ đến từ HTTP 429 | J&T |
| 6 | **`getOrder` / huỷ đơn / tính phí / in nhãn** | Đường dẫn đầy đủ chưa xác minh (`DUONG_API` mức `chua-xac-nhan`) — `http_jt` **không** tự ghép URL, adapter chặn trước | J&T (docs/G13_JT_API.md §7) |
| 7 | **Mã trạng thái `110`** (D-4) | Chưa xác minh ⇒ vẫn `NEEDS_REVIEW`; lớp HTTP này **không** đụng tới trạng thái | J&T |
| 8 | **`TRANSPORT_THAT_DA_VIET`** | Trong `app/adapter_jt.py` (làn **AG-03**) hiện vẫn `False`. Lớp HTTP đã có, **nhưng chưa lượt gọi thật nào** ⇒ cờ đó **chưa có gì để chứng minh**. Việc đổi cờ thuộc AG-03, và **không** thay thế được (1) | AG-03 + anh Thành |
| 9 | **`CHO_PHEP_LIVE`** | **Không agent nào được mở** (§39). Lớp này cũng không có đường nào mở nó | anh Thành |

**Không có mức "LIVE VERIFIED" ở G16-A.** Điều kiện để được nói câu đó là **một lượt gọi API thật
thành công** — chưa từng xảy ra. Tài liệu này không viết câu nào đọc như đã đạt, và bộ thử xanh
**không phải** lời cho phép gọi sandbox.

---

## 9. ĐÓNG BĂNG G16-A — VÂN TAY, MỐC GIỜ, VÀ CAM KẾT DỪNG

| | |
|---|---|
| **Mốc giờ đóng băng mã** | **2026-10-15 16:04 +07** (kiểm lại lúc 16:05: ba sha256 **không đổi**) |
| **`HEAD`** | `6d05c74` — `449bb2d` là **tổ tiên** (`git merge-base --is-ancestor` = CÓ). `app/transport.py` đang có **+26 dòng chưa commit** (phần `cho_giay`/`CHO_TOI_DA` của AG-00) |
| **Vân tay cây (§41)** | `9a72ec8739320de8f25cfb9ddcdc7d22e337320f9c665edccbb3fb74117134df` |
| `app/http_jt.py` | `3d9d8f0a416b5f4e5d54ec8f8788370e590a7ff1b72f2d8b3f9149310bb0ba57` |
| `app/thu/stub_jt.py` | `8872274d24e3117047e696d9eaf834820825367d384af53580d23cfaf0bf8235` |
| `app/thu/thu_http_jt.py` | `45a16f235c65f5fe3478da7551d9efeb87b852b6f15289e64b1c25fe75303f17` |

Lệnh lấy vân tay (§41, chép nguyên văn từ hợp đồng):

```bash
cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
find app gateway thu_frontend thu_giao_dien -type f \
  \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
  | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
```

**Từ mốc 16:04 +07, tôi KHÔNG sửa thêm một dòng MÃ nào.** Lý do AG-00 yêu cầu dừng dứt khoát: AG-01
đếm được `app/http_jt.py` đã đổi **sáu bản** trong lúc nó nghiệm thu
(`c0d21201 → 1c862635 → 58fa6523 → 97e38a49 → 50d8301c → 3d9d8f0a`), và *"xanh trên sáu bản tôi đã đo"*
**không** phải *"xanh trên bản cuối"*. Sau mốc này, tệp duy nhất tôi còn sửa là **chính tài liệu này**
(không có mã, không có ca thử). Mọi thay đổi mã sau mốc phải do **AG-00** chủ trì, và khi đó vân tay
cây ở trên **hết hiệu lực** — phải đo lại.

**Ba tệp của làn này CHƯA được Git theo dõi** (`git ls-files | grep http_jt` = RỖNG, AG-01 `G16-08`):
một `git clean -fd` sẽ xoá sạch G16-A. Việc commit mốc G16-A thuộc **AG-00** (hạ tầng chặn ghi `.git`
từ làn này).

---

## 10. PHẠM VI CỦA CHÍNH TÀI LIỆU NÀY

- Mọi số ở §4 do **một làn AI** chạy trên máy này (macOS, Python 3.9.6), trên nền `449bb2d`.
  **Chưa người nào soát lại.**
- Cây làm việc **đang được ba làn khác ghi đồng thời** ⇒ con số hồi quy ở §4.2 là ảnh chụp tại một
  thời điểm, không phải một thuộc tính ổn định của cây.
- §4.4 nói thẳng cái gì nằm ngoài. Không có kết luận nào ở đây được phép đọc rộng hơn phạm vi đó.
