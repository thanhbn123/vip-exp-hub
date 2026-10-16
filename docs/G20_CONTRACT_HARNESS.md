# G20 — HARNESS HỢP ĐỒNG LỚP HTTP (AG-03)

> **Câu lượt này trả lời:** *hợp đồng lớp HTTP của dự án này đang GIỮ ĐƯỢC gì, và đang HỞ gì —
> và ai đó có thể chạy HẾT nó bằng MỘT lệnh không?*

Trước lượt này câu trả lời là **không**, và tệp này dựng chỗ để trả lời.

---

## 1. Khoảng trống có thật

Năm harness rời rạc cho lớp HTTP — `trien_khai/g16`, `g17`, `g18`, `g18-crash`, `g19` — mỗi
cái một kiểu tham số, một kiểu báo cáo, một kiểu chốt an toàn. Không có chỗ nào chạy HẾT
chúng. Ba kiểu báo cáo khác nhau, đo được:

| Harness | Khoá trong báo cáo | Có `blocked`? | Có `dem.BLOCKED`? | Báo cáo máy đọc được? |
|---|---|---|---|---|
| G16 | `gate · buoc · dem · blocked · chot_an_toan · hop_dong_callback` | **có** | có (2) | có (`--json`) |
| G17 | `goc · buoc · dem · blocked · stub · pid_may_chu` | **có** | có (1) | có (`--json`) |
| G18 | `nen · cau_hinh · buoc · dem` | **KHÔNG** | có (1) | có (`--json`) |
| G18-crash | — | — | — | **KHÔNG có `--json`** |
| G19 | `route · ung_vien · cap · chi_tiet · …` | — | — | có (`--ra`) |

Hai chỗ hở của chính các báo cáo ấy, ghi ra chứ không giấu:

* **G18 thiếu khoá `blocked`.** G16/G17 khai danh sách chặng bị chặn; G18 chỉ có con số trong
  `dem.BLOCKED`, nên muốn biết *chặng nào* bị chặn phải đọc `buoc`. G20 bắc cầu bằng
  `_dem_blocked()` và **nói ra** rằng nó đang bắc cầu.
* **G18-crash không có báo cáo máy đọc được.** `app/thu/thu_g18_crash.py` không có `--json`.
  Chặng ấy chỉ phán được bằng **mã thoát + dấu vết stdout**. Hợp đồng khai `"bao_cao_json": ""`
  và `"so_blocked": null` — tức là *"chặng này không đối chiếu được bằng dữ liệu"* — chứ không
  giả vờ rằng nó đã đối chiếu.

Hệ quả của việc không có chỗ chạy hết: một harness có thể HỎNG trong nhiều tuần mà không ai
thấy, vì bộ chạy toàn cục (`app/thu/chay_tat_ca.sh`) **không** gọi các harness trong
`trien_khai/`. Đó không phải giả thuyết — mục 5 dưới đây là một ca thật.

---

## 2. Hợp đồng là DỮ LIỆU, không phải văn xuôi

`trien_khai/g20/hop_dong.json` liệt kê **13 chặng**. Mỗi chặng THỰC THI khai:

```json
{
  "ma": "G19",
  "loai": "harness",
  "trang_thai_mong_doi": "CHAY_DUOC",
  "chot_can": ["N1", "N2", "N3", "N4", "N6", "N7"],
  "cham_hang": false,
  "giay_phep_can": [],
  "buoc": [
    {"ten": "…", "lenh": ["…"], "ma_thoai": 0}
  ],
  "bao_cao_json": "${NEN}/g19_liet_ke.json",
  "mong_doi": {
    "khoa_bat_buoc": ["route", "ung_vien", "cap", "chi_tiet"],
    "so_route_toi_thieu": 80,
    "so_buoc_toi_thieu": 2,
    "dem_hong_toi_da": 0,
    "so_blocked": null,
    "stdout_bat_buoc": ["Ran "],
    "stdout_cam": ["FAILED"]
  }
}
```

`mong_doi` là **các phép kiểm máy thi hành được**, không phải lời mô tả: thiếu khoá bắt buộc,
mã thoát lệch, số ca HỎNG vượt ngưỡng, số bước dưới ngưỡng, số route dưới ngưỡng, số BLOCKED
lệch khai báo, thiếu dấu vết stdout, có dấu vết bị cấm — mỗi thứ là một lý do HỎNG cụ thể.

Chặng KHÔNG BAO GIỜ CHẠY (`cham-hang`, `ngoai-pham-vi`) khai `ly_do_blocked` + `giay_phep_can`
và **bắt buộc** `buoc: []` — có lệnh nghĩa là nó SẼ chạy khi ai đó gỡ chốt. Bộ thử `a11` canh
đúng điều đó.

### Bộ thử canh chính hợp đồng

`app/thu/thu_g20_hop_dong.py`, lớp `A`, canh hợp đồng **tự nhất quán**: đủ khoá, mã không trùng,
`loai` hợp lệ, mọi `chot_can` đều có định nghĩa, không dùng biến thay thế `${…}` lạ, và năm
harness con đều có mặt.

---

## 3. Bảy chốt an toàn — và vì sao harness ĐIỀU PHỐI cần chốt riêng

| Mã | Chốt |
|---|---|
| N1 | nền chạy phải là thư mục TẠM, ngoài `app/du-lieu/` |
| N2 | `CHO_PHEP_LIVE is False` trên MỌI adapter + cổng môi trường J&T ĐÓNG |
| N3 | `VIP_HUB_BIND` trống hoặc loopback |
| N4 | cờ cho phép gọi hãng KHÔNG bật |
| N5 | `VHG18_CONG_PG` ≠ 5432 |
| N6 | nguồn của làn G20 không chứa lệnh giết theo TÊN tiến trình |
| N7 | không ai khai `V-G09-01`/`V-13906-05` là đã cấp |

Một harness điều phối không có chốt riêng thì **khuếch đại** một chốt bị gỡ ở một làn thành
năm lượt chạy mất chốt: chỉ cần đặt `VIP_HUB_BIND=0.0.0.0` một lần là cả năm lượt cùng mở cổng.
Vì thế `chay_hop_dong.py` kiểm chốt **HAI LẦN** — một lần trên môi trường của chính nó, và một
lần trên **môi trường THẬT SẮP ĐƯA CHO TIẾN TRÌNH CON** (sau khi đã áp `bien_moi_truong` của
chặng). Khe hở giữa hai lần ấy là khe hở thật: `F09` dưới đây đo đúng nó.

### N6 — chốt tự soi, và ba lần nó tự bắt lỗi của chính tác giả

N6 đọc **chính mã của làn này**. Ba vòng lặp có thật trong lượt làm việc này:

1. Bản đầu lọc chú thích nhưng **không lọc chuỗi**, nên nó bắt dòng
   `echo "dọn dẹp = theo ĐÚNG PID · không pkill/killall"` của chính `chay_tat_ca.sh` và **TỪ
   CHỐI MỌI LƯỢT CHẠY** (mã thoát 4, 0 chặng nào chạy). Một bộ dò đỏ vì lời cảnh báo của chính
   nó là một bộ dò hỏng.
2. Bản vá "lọc thêm chuỗi" lại **bỏ sót** `subprocess.run(["pkill", "-f", "server.py"])` —
   đúng lời gọi nó sinh ra để bắt — vì tên lệnh nằm trong một hằng chuỗi.
3. Bản đang dùng phân biệt bằng **AST**: hằng chuỗi nằm TRƠ là dữ liệu; cùng hằng ấy nằm trong
   ĐỐI SỐ của `system`/`run`/`Popen` là một DÒNG LỆNH. Với shell thì bỏ chú thích, và với chuỗi
   trích dẫn thì **giữ lại nếu nội dung BẮT ĐẦU bằng tên lệnh** (`sh -c "pkill -f x"` là lời gọi,
   `echo "… không pkill …"` là văn xuôi).

Ba ca tự kiểm canh đúng ba mặt ấy: `J` (mã chứa lệnh ⇒ phải bắt), `O`/`P` (lời gọi thật trong
Python và trong shell ⇒ phải bắt), `M`/`N`/`Q` (chú thích, chuỗi cảnh báo, docstring ⇒ KHÔNG
được coi là vi phạm). **17/17 ca đạt.**

---

## 4. Bốn trạng thái, và vì sao phải là bốn

| Trạng thái | Nghĩa |
|---|---|
| `CHAY_DUOC` | chạy xong, mã thoát khớp, báo cáo khớp MỌI khai báo trong `mong_doi` |
| `KHONG_CHAY_DUOC` | KHÔNG chạy được: thiếu chốt an toàn (kèm ĐÚNG mã chốt), hoặc thiếu điều kiện môi trường |
| `BLOCKED` | khai báo là bị chặn (thiếu giấy phép / ngoài phạm vi). **KHÔNG tính là đạt.** |
| `HONG` | ĐÃ CHẠY nhưng kết quả VI PHẠM khai báo |

Ba trạng thái đầu là ba câu hỏi của đề bài. Trạng thái thứ tư tồn tại vì yêu cầu "tiêm một
chặng hỏng vào bản sao ⇒ harness PHẢI báo đỏ": **thiếu `HONG` thì một chặng hỏng vẫn "xanh"**.

`BLOCKED` KHÔNG phải `HONG`. Một chặng bị chặn **đúng như đã khai** là hợp đồng ĐANG ĐÚNG,
không phải hợp đồng bị vi phạm — nên nó không làm lượt chạy đỏ, nhưng nó cũng **không bao giờ**
được cộng vào cột "đạt".

### Bộ tự kiểm của bộ phán: 14 phép tiêm + 1 đối chứng dương

`tiem_loi.py` lấy hợp đồng THẬT, giữ nguyên **mọi chặng chạm hãng và ngoài phạm vi** (chúng
không thực thi gì, nên giữ lại là miễn phí), và thay ĐÚNG MỘT chặng harness bằng một chặng giả
lập nhanh. Nhờ vậy mỗi phép tiêm vẫn đi qua đúng bảy chốt thật, đúng bộ đọc báo cáo thật, đúng
bộ đối chiếu `mong_doi` thật — chỉ có thân của chặng là giả.

| Mã | Tiêm gì | Phải ra | Ra |
|---|---|---|---|
| **P0** | **ĐỐI CHỨNG DƯƠNG** — chặng lành | `CHAY_DUOC`, exit 0 | ✓ |
| F01 | mã thoát 3 trong khi hợp đồng đòi 0 | `HONG` | ✓ |
| F02 | không ghi báo cáo | `HONG` | ✓ |
| F03 | ghi JSON hỏng | `HONG` | ✓ |
| F04 | báo cáo thiếu khoá bắt buộc | `HONG` | ✓ |
| F05 | báo cáo có 1 ca HỎNG (hợp đồng cho tối đa 0) | `HONG` | ✓ |
| F06 | số BLOCKED lệch khai báo | `HONG` | ✓ |
| F07 | số bước dưới ngưỡng khai báo | `HONG` | ✓ |
| F08 | thiếu dấu vết stdout bắt buộc | `HONG` | ✓ |
| F09 | **chặng tự khai biến môi trường PHÁ chốt của chính nó** | `KHONG_CHAY_DUOC` | ✓ |
| F09b | gỡ chốt ở TẦNG TRÊN (`VIP_HUB_BIND=0.0.0.0`) | cả lượt TỪ CHỐI, exit 4 | ✓ |
| F10 | tự cấp giấy phép (`VIP_G20_GIAY_PHEP=V-G09-01`) | cả lượt TỪ CHỐI, exit 4 | ✓ |
| F11 | một chặng CHẠM HÃNG bị đổi thành `loai: harness` | LỆCH khai báo ⇒ exit 1 | ✓ |
| F12 | hợp đồng RỖNG (0 chặng) | exit 2 | ✓ |

**P0 là ca quan trọng nhất và dễ bị bỏ nhất**: thiếu nó thì một bộ phán `return HONG` cho mọi
thứ cũng "bắt được" cả 13 ca hỏng và trông như đang hoạt động. **14/14 ca đạt.**

`F12` canh luật "chạy 0 chặng mà báo đạt là hỏng": hợp đồng khai `so_chang_toi_thieu` và bộ chạy
**từ chối** khi số chặng ít hơn ngưỡng.

---

## 5. KẾT QUẢ LƯỢT NÀY

### Bằng chứng (lệnh thật, mã thoát thật)

```
$ python3 trien_khai/g20/chot_an_toan.py --tu-kiem     # TẦNG 1
TỰ KIỂM: 17/17 ca đạt · 0 hỏng
EXIT=0

$ python3 trien_khai/g20/tiem_loi.py                   # TẦNG 2
TIÊM LỖI: 14/14 ca đạt · 0 hỏng
EXIT=0

$ python3 app/thu/thu_g20_hop_dong.py                  # BỘ THỬ
Ran 36 tests in 13.6s
OK
EXIT=0

$ sh trien_khai/g20/chay_tat_ca.sh                     # CẢ BA TẦNG
   tự kiểm chốt (1) : mã thoát 0  ĐẠT
   tiêm lỗi      (2) : mã thoát 0  ĐẠT
   hợp đồng      (3) : mã thoát 1  CHƯA ĐẠT
EXIT=1
```

### Bảng hợp đồng — 13 chặng

| # | Chặng | Loại | Trạng thái | Mã thoát | Số ca (báo cáo con) |
|---|---|---|---|---|---|
| 1 | `G16` | harness | ✓ CHẠY ĐƯỢC | 0 | 46 bước · DAT 32 · ĐẠT(MOCK) 12 · **BLOCKED 2** |
| 2 | `G17` | harness | ✓ CHẠY ĐƯỢC | 0 | 21 bước · DAT 17 · ĐẠT(MOCK) 3 · HỎNG 0 · **BLOCKED 1** |
| 3 | `G18` | harness | **✗ HỎNG** | **1** (đòi 0) | 12 bước · DAT 12 · ĐẠT(MOCK) 4 · **HỎNG 1** · BLOCKED 1 · BỎ QUA 2 |
| 4 | `G18-CRASH` | harness | ✓ CHẠY ĐƯỢC | 0 | không có báo cáo máy đọc được |
| 5 | `G19` | harness | ✓ CHẠY ĐƯỢC | 0 · 0 | 103 route · 144 cặp (đường, phương thức) |
| 6 | `G16-G05` | cham-hang | ⊘ BLOCKED | — | thiếu `V-G09-01` · `V-13906-05` |
| 7 | `G16-G06-SANDBOX` | cham-hang | ⊘ BLOCKED | — | thiếu `V-G09-01` · `V-13906-05` |
| 8 | `G17-SANDBOX` | cham-hang | ⊘ BLOCKED | — | thiếu `V-G09-01` · `V-13906-05` |
| 9 | `G19-VTP-21-MA` | cham-hang | ⊘ BLOCKED | — | thiếu `V-13906-05` (0/21 mã thật) |
| 10 | `TLS-THAT` | ngoai-pham-vi | ⊘ BLOCKED | — | thiếu `V-G11-01` |
| 11 | `D4-MA-110` | ngoai-pham-vi | ⊘ BLOCKED | — | thiếu `V-13906-04` ⇒ `NEEDS_REVIEW` |
| 12 | `D9-AREA` | ngoai-pham-vi | ⊘ BLOCKED | — | chốt D-9 chặn cứng |
| 13 | `PG-NGHIEP-VU-D8` | ngoai-pham-vi | ⊘ BLOCKED | — | D-8: vẫn SQLite |

**TỔNG: 13 chặng · 4 CHẠY ĐƯỢC · 0 KHÔNG CHẠY ĐƯỢC · 8 BLOCKED · 1 HỎNG · 49 giây.**

Chốt an toàn: **0 PID còn sống** sau lượt chạy (`pid_con_song: []`), 6 PID đã spawn và đã tắt
theo ĐÚNG PID.

### Hợp đồng lớp HTTP đang GIỮ ĐƯỢC gì

* **Webhook J&T trên adapter MOCK** (G16): 44 bước ĐẠT ở các nhánh không chạm hãng.
* **Replay + chống trùng** (G17): 20 bước ĐẠT, gồm 4 nhánh replay và tầng chống trùng CSDL.
* **Máy chủ HTTP thật dưới tải** (G18): 16/20 ca — trần tần suất đúng ở cả đường HTTP lẫn đường
  gọi thẳng hàm, log JSON có `X-Request-Id`, hai tiến trình trên cùng CSDL.
* **SIGKILL giữa giao dịch** (G18-crash): SQLite 7 điểm giết + PostgreSQL 9 lượt, bất biến
  `integrity_check=ok · foreign_key_check=[] · mồ côi=0`.
* **Cách ly tenant** (G19): 103/103 route THẬT đã có bằng chứng cách ly (73 của AG-01 + 30 của
  AG-04); 0 route còn thiếu.

### Hợp đồng lớp HTTP đang HỞ gì

1. **N-G20-01 — chặng `G18` HỎNG.** Chi tiết ở mục 6. Đây là lỗi THẬT, đã truy nguyên, **ngoài
   phạm vi được cấp của AG-03** nên lượt này chỉ báo cáo.
2. **`TLS-THAT`** — `V-G11-01` CHƯA CẤP. Mọi phép đo đi qua loopback, không qua dây, không qua
   proxy. Một lượt loopback xanh KHÔNG phải bằng chứng TLS chạy được.
3. **Bốn chặng chạm hãng** (`G16-G05`, `G16-G06-SANDBOX`, `G17-SANDBOX`, `G19-VTP-21-MA`) —
   `V-G09-01` / `V-13906-05` CHƯA CẤP. **MỘT LƯỢT MOCK XANH KHÔNG PHẢI BẰNG CHỨNG ĐƯỜNG
   SANDBOX CHẠY ĐƯỢC.**
4. **`D4-MA-110`** — nghĩa mã trạng thái J&T `110` chưa xác minh ⇒ **`NEEDS_REVIEW`**.
   `quyet_dinh("jt", 110)` trả `None [AMBIGUOUS]`, `can_soat=1`. **KHÔNG đoán.**
5. **`D9-AREA`** — ánh xạ `city`/`area` ngoài mock vẫn **chặn cứng**. Không nới một ly.
6. **`G19-VTP-21-MA`** — **0/21** mã trạng thái VTP thật; nguồn duy nhất hiện có là bộ mô phỏng
   của chính dự án (nợ mở đã ghi ở `docs/QA_G19.md` mục 3).
7. **`G18-crash` không có báo cáo máy đọc được** — khoảng trống của hợp đồng: chặng ấy chỉ
   phán được bằng mã thoát.
8. **`PG-NGHIEP-VU-D8`** — CSDL nghiệp vụ vẫn là SQLite. PostgreSQL chỉ là **CỤM RIÊNG** của
   phép đo G18/AG-06, **CẤM cổng 5432**.

---

## 6. PHÁT HIỆN N-G20-01 — chặng `G18` HỎNG: `gioi_han.xoa_het()` xoá kho đếm DÙNG CHUNG

### 6.1 Đo được gì

`sh trien_khai/g18/chay_harness.sh` → **mã thoát 1**, `16/20 ca đạt · 1 hỏng · 1 BLOCKED ·
2 bỏ qua`. Ca hỏng:

```
✗ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
      HTTP=401 · Retry-After=None · X-RateLimit-Limit=None · X-RateLimit-Window=None
```

**Không phải lỗi sandbox.** Đã kiểm nhật ký trước khi kết luận: không có `EPERM`, không có
`Permission denied` nào trong lượt này. Và **không phải nhiễu tải**: chạy sạch ba lần liên tiếp
(2 lần lúc dò, 1 lần sau khi mọi tiến trình khác đã dừng) đều cho **đúng một ca hỏng là G18-05**,
exit 1 cả ba lần.

### 6.2 Truy nguyên

`app/gioi_han.py` — khối `KhoCSDL` — ghi rõ trong chú thích đầu tệp rằng G19/AG-02 đã **chuyển
kho đếm tần suất từ BỘ NHỚ MỘT TIẾN TRÌNH sang BẢNG CSDL dùng chung** (`gioi_han_luot`,
`gioi_han_chan`), để bịt hai lỗ: trần nhân theo số bản, và cửa lách khởi động lại.

```python
def xoa_het(self):
    self._dam_bao_bang()
    csdl.ghi("DELETE FROM gioi_han_luot")     # ← CSDL DÙNG CHUNG, không phải bộ nhớ riêng
    csdl.ghi("DELETE FROM gioi_han_chan")
```

`trien_khai/g18/harness_tai.py` — bước **G18-04b** — gọi `gioi_han.xoa_het()` **trong tiến trình
HARNESS**, với ý định "dọn bộ nhớ của chính mình trước khi đo lại bằng đường gọi thẳng hàm".
Dưới ngữ nghĩa CŨ (bộ nhớ tiến trình) điều đó vô hại. Dưới ngữ nghĩa MỚI nó **xoá kho đếm mà
TIẾN TRÌNH MÁY CHỦ đang dùng** — nên tới G18-05, chặng mong đợi một lượt `429` lại nhận `401`:
bucket vừa bị xoá sạch.

Lịch sử git khớp chính xác thứ tự ấy:

```
$ git log --oneline -S "gioi_han_luot" -- app/gioi_han.py
f04de21 AG-02 (G19) dong HAI lo hong gioi han tan suat PHAN A — 22 ca DAT, exit 0

$ git log --oneline -3 -- trien_khai/g18/harness_tai.py
8d58117 AG-04 (G18) V-13914(b): do may chu HTTP THAT duoi tai
```

`harness_tai.py` (`8d58117`) viết TRƯỚC `f04de21`. Hai lượt ấy chưa bao giờ gặp nhau trong một
lần chạy — cho tới khi G20 chạy chúng cạnh nhau.

### 6.3 ĐỐI CHỨNG ĐƯỜNG 1 — kho đếm là DÙNG CHUNG giữa hai tiến trình

Hai tiến trình KHÁC PID, cùng một `VIP_HUB_DATA`:

```
P1 pid 1732  ghi 3 lượt bằng gioi_han.kiem(...)  ⇒ so dong gioi_han_luot = 6
P2 pid 1735  TRUOC xoa = 6
P2 pid 1735  SAU  xoa = 0        ← TIẾN TRÌNH KHÁC xoá sạch kho của P1
```

Dưới ngữ nghĩa "bộ nhớ một tiến trình" thì con số thứ hai bắt buộc phải là **0** ngay từ đầu.
Nó là **6**. Kho đếm đã dùng chung thật.

### 6.4 ĐỐI CHỨNG ĐƯỜNG 2 — bỏ ĐÚNG MỘT dòng thì ca hỏng ĐỔI CHỖ

Sao chép nguyên `trien_khai/g18/` (kèm `trien_khai/g17/` vì chốt G18 thừa hưởng bảy chốt G17)
ra `/tmp/veh_g20_dc/`, rồi tạo thêm **một bản y hệt nhưng bỏ đúng một lời gọi**
`gioi_han.xoa_het()` trong G18-04b. Chạy cả hai:

| Bản | `G18-05` | `G18-07a` | Mã thoát |
|---|---|---|---|
| **A** — bản sao KHÔNG chửa | **✗ HỎNG** | ✓ ĐẠT | 1 |
| **B** — bản sao bỏ `xoa_het()` | **✓ ĐẠT** | **✗ HỎNG** | 1 |

Đọc hai cột ấy cùng nhau mới ra chẩn đoán: **harness G18 KHÔNG THỂ xanh dưới ngữ nghĩa mới**,
và hai ca hỏng là HAI MẶT của cùng một nguyên nhân:

* **G18-05** cần bucket `webhook.chu_ky_sai` VẪN CẠN (để lượt kế tiếp ra `429`). `xoa_het()`
  làm bucket đầy lại ⇒ ra `401`.
* **G18-07a** (`mã={429: 50}`) cần ngân sách `webhook.nhan` ĐÃ ĐƯỢC GIẢI PHÓNG. Trước đó
  G18-03b đã bắn **640 sự kiện** vào đúng cửa ấy (trần khai báo 600/60 giây) ⇒ hết ngân sách.
  Chỉ có `xoa_het()` mới mở lại được — mà dưới ngữ nghĩa mới nó không còn là "dọn nhà mình".

Harness ấy đã **ngầm dựa vào việc `xoa_het()` xoá kho dùng chung** ở chỗ này, và **ngầm dựa vào
việc nó KHÔNG xoá kho dùng chung** ở chỗ kia. Hai giả định ấy loại trừ nhau. Bỏ dòng lệnh đi
(đối chứng B) chỉ đổi ca nào đỏ, không làm lượt chạy xanh — đó chính là dấu hiệu của một giả
định đã hết hiệu lực, chứ không phải của một ca thử hỏng vặt.

### 6.5 Vì sao không ai thấy trước lượt này

`app/thu/chay_tat_ca.sh` — bộ chạy toàn cục — dò `app/thu/thu_*.py`. Các harness trong
`trien_khai/g16…g19` **không** nằm trong danh sách ấy. Nên 1631 ca / 44 bộ của G18 vẫn xanh
trong khi một harness lớp HTTP của chính G18 đỏ suốt. **Đây đúng là khoảng trống mà G20 dựng ra
để bịt**, và nó là bằng chứng tốt nhất rằng khoảng trống ấy có thật.

### 6.6 NẰM NGOÀI PHẠM VI CỦA AG-03

Lượt này **chỉ được ghi** vào `trien_khai/g20/`, `app/thu/thu_g20_hop_dong.py`,
`docs/G20_CONTRACT_HARNESS.md`. Bản vá thuộc `trien_khai/g18/harness_tai.py` (và có thể cả
`app/gioi_han.py`) — **không sửa ở đây**. Đề xuất cho lượt sửa: G18-04b phải **dọn theo KHOÁ**
(`gioi_han.xoa(khoa)`) thay vì `xoa_het()`, và G18-07a phải **tự giành ngân sách của mình**
(khoá riêng hoặc `dat_lai` tường minh trên khoá của nó) thay vì trông vào một lượt xoá sạch
toàn cục. Cả hai đều là quyết định của chủ sở hữu G18/G19, không phải của harness hợp đồng.

---

## 7. NẰM NGOÀI PHẠM VI — đã đo là KHÔNG đo được

* **Gọi API hãng, kể cả sandbox** — `V-G09-01` + `V-13906-05` CHƯA CẤP.
* **TLS/HTTPS thật · tunnel · VPS · deploy · push** — `V-G11-01` CHƯA CẤP. Bind `127.0.0.1`
  cổng 0.
* **MẠNG thật** — mọi lượt đi qua loopback, không qua dây, không qua proxy.
* **Nhiều MÁY** — hai tiến trình của G18 nằm CÙNG một máy, CÙNG một ổ đĩa.
* **Chuyển CSDL nghiệp vụ sang PostgreSQL** (`D-8`).
* **Nghĩa mã trạng thái hãng** (`D-4`) và **ánh xạ `city`/`area` ngoài mock** (`D-9`).
* **AI/LLM thật**, **credentials hãng thật**, **`.env`**, **in bí mật ra log**.
* **Docker / `mem_limit` / `pids_limit`** — Docker CHƯA CÀI trên máy này.
* **Mất điện / máy chủ vật lý chết** — page cache sống sót qua `SIGKILL`, nên `fsync` không đo
  được ở đây.

---

## 8. CPI — chạy lại

```sh
# cả ba tầng, ~50–90 giây, nền tạm riêng, dọn theo ĐÚNG PID
sh trien_khai/g20/chay_tat_ca.sh

# chỉ phán hợp đồng, không thực thi chặng nào
sh trien_khai/g20/chay_tat_ca.sh --khong-chay

# từng tầng
python3 trien_khai/g20/chot_an_toan.py --tu-kiem      # 17/17, exit 0
python3 trien_khai/g20/tiem_loi.py                    # 14/14, exit 0
python3 app/thu/thu_g20_hop_dong.py                   # 36 ca, exit 0

# xem hợp đồng mà không chạy
python3 trien_khai/g20/chay_hop_dong.py --danh-sach
```

Bằng chứng nằm dưới nền của lượt (`/tmp/veh_g20_ag03/lan-<PID>-<mốc>-<số>/`):
`bao-cao-g20-hop-dong.json` (báo cáo gom, máy đọc được) và `hop-dong/nhat-ky/<mã>.log`
(nhật ký nguyên văn từng chặng, **mã thoát ghi TRƯỚC mọi ống lệnh**).

---

## 9. NEEDS_REVIEW của lượt này

| # | Mục | Vì sao |
|---|---|---|
| 1 | **N-G20-01** — `trien_khai/g18/harness_tai.py` HỎNG dưới ngữ nghĩa `gioi_han` mới | Đã đo, đã truy nguyên, đã có hai đối chứng đường. Bản vá NGOÀI phạm vi được cấp của AG-03 |
| 2 | `G18-crash` không có báo cáo máy đọc được | Chặng ấy chỉ phán được bằng mã thoát — khoảng trống của hợp đồng, không phải của mã |
| 3 | Nghĩa mã J&T `110` (`D-4`) | Chưa xác minh ⇒ `NEEDS_REVIEW`. **Không đoán** |
| 4 | Ánh xạ `city`/`area` ngoài mock (`D-9`) | Chặn cứng. Chưa có nguồn hãng |
| 5 | 21 mã trạng thái VTP thật | 0/21. Nguồn duy nhất hiện có là bộ mô phỏng của chính dự án |
