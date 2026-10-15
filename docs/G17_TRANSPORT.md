# G17_TRANSPORT — LỚP HTTP J&T: ĐA LUỒNG · HAI TẦNG HẠN THỜI GIAN · CỔNG CHE BÍ MẬT MỞ RỘNG

> **Trạng thái: ĐÃ ĐO — nhưng CHỈ trên STUB CỤC BỘ `127.0.0.1`.**
> **CHƯA từng có một lượt gọi hãng nào, kể cả sandbox.** `V-G09-01` và `V-13906-05` **CHƯA ĐƯỢC CẤP**
> (`docs/SHARED_CONTRACTS.md` §37), credentials hãng **CHƯA TỒN TẠI** (§38), `CHO_PHEP_LIVE` **CHƯA mở**.
> **TLS thật tới `*.jtexpress.vn` CHƯA ĐO.** Tài liệu này **KHÔNG** nói — và không được đọc thành —
> "LIVE VERIFIED", "chạy được với hãng", hay "sẵn sàng production".
>
> Toàn bộ số liệu do **một làn AI** (AG-02, G17) chạy trên máy này. **Chưa người nào soát lại.**
> `docs/BAN_GIAO.md` §2: *"AI review không phải human review. Bộ thử xanh không phải lời cho phép."*

**Nền:** `integration/g16` @ `98baeb3` — **worktree riêng** `g17-ag02-transport`.
**`main` = `de740dc` và KHÔNG chứa G13–G16** (đã xác minh); tài liệu này **không** nói gì về `main`.

**Làn này chỉ ghi 4 tệp:** `app/http_jt.py`, `app/thu/stub_jt.py`, `app/thu/thu_http_jt.py`,
`docs/G17_TRANSPORT.md`. Không đụng tệp nào của làn khác (xem §9).

---

## 1. ĐÃ LÀM GÌ — và cái gì CỐ Ý KHÔNG làm

| Tệp | Trạng thái | Nội dung G17 |
|---|---|---|
| `app/http_jt.py` | **SỬA** | Vá 4 đường rò bí mật (mục §5) · `tach_url` chặn ký tự điều khiển + bọc `urlsplit` · ném ngoại lệ ở NGOÀI khối `except` ⇒ `__context__` sạch · `timeout` ghi rõ là hạn TỪNG lần đọc (§4.4) |
| `app/thu/stub_jt.py` | **SỬA (thêm)** | 3 chế độ mới: `VONG_LAP` (200 dựng TỪ yêu cầu) · `DOI_DAU_LAP` (401 echo LẶP + echo dòng yêu cầu) · `NHO_GIO` (nhỏ giọt từng byte) · `HoDenKetNoi` (hố đen TCP loopback, TỰ KIỂM độ no) · đếm `so_ket_noi` / `cao_nhat_dang_xu_ly` |
| `app/thu/thu_http_jt.py` | **SỬA (thêm)** | **+20 ca** (37 → 57): 18 ca đo mới — `CaDongThoi` (i1–i4) · `CaHetGioNhieuTang` (k1–k6) · `CaBiMatMoRong` (j1–j8) — cộng `CaTuKiemG17` (l1–l2: **20 dòng đột biến mã sản phẩm** + 3 đối chứng dương) |
| `docs/G17_TRANSPORT.md` | **MỚI** | Tài liệu này |

**KHÔNG sửa một tệp nào khác.** Ba tệp mã trên đều đã được Git theo dõi và **chỉ ba tệp đó** là ` M`
trong `git status --porcelain` (§9). `transport.py`, `cau_hinh.py`, `csdl.py`, `migrate.py`,
`server.py`, `don_hang.py`, `adapter_jt.py`, `chay_tat_ca.sh`: **không đụng một byte**.

**CỐ Ý KHÔNG làm:**

- **KHÔNG gọi API hãng, kể cả sandbox.** Mọi lượt gửi trong tệp thử đi tới stub `127.0.0.1` cổng 0,
  và điều đó được **ÉP BẰNG MÃ**: chốt chặn mạng của bộ thử chỉ cho loopback đi qua.
- **KHÔNG push, KHÔNG deploy, KHÔNG mở cổng ra Internet.** Hố đen TCP mới cũng chỉ bind `127.0.0.1`.
- **KHÔNG mở `CHO_PHEP_LIVE`**, không sửa cảng sandbox/production trong `app/cau_hinh.py`.
- **KHÔNG credentials thật**, không `.env`, không in bí mật ra log (bí mật trong bộ thử là chuỗi GIẢ
  ĐỊNH sống trong tiến trình).
- **KHÔNG đoán mã trạng thái `110`** (D-4): làn này không chạm bảng mã trạng thái; mã chưa xác minh
  vẫn phải là `NEEDS_REVIEW`.
- **KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8): vẫn SQLite, làn này không chạm CSDL.
- **KHÔNG đổi mô hình** (không dùng Claude, không đổi sang mô hình khác).

---

## 2. BA LỖ HỔNG "CHƯA ĐO" (§8 mục 4 của G16) — ĐÓNG BẰNG CÁCH NÀO

`docs/G16_ACCEPTANCE.md` §8 mục 4 ghi nguyên văn: *"**Đa luồng trên `http_jt`** — bộ thử chạy tuần
tự."* Làn này nhận đúng khoảng trống đó và mở rộng thành ba việc: **đa luồng**, **hai tầng hạn thời
gian**, **cổng che bí mật**. Ba việc ấy không tách rời: cả ba đều được đo trên CÙNG một stub cục bộ,
và cả ba đều là chỗ một lớp vận chuyển có thể nói dối người gọi.

| Việc | Ca | Câu hỏi phải trả lời được bằng số |
|---|---|---|
| **1. Đồng thời** | `CaDongThoi` i1–i4 | N luồng thì có N kết quả ĐÚNG của mình không? Có bị tuần tự hoá không? Ràng buộc thật là gì (pool? khoá? `getdefaulttimeout`?) |
| **2. Hết giờ nhiều tầng** | `CaHetGioNhieuTang` k1–k6 | Hạn NỐI và hạn ĐỌC có TÁCH không? Treo có bao giờ bị đọc thành CÔNG không? |
| **3. Che bí mật** | `CaBiMatMoRong` j1–j8 | Bí mật NGẮN · trong HEADER · trong THÂN · bị DỚP LẶP · trong CHUỖI LỖI — có lọt không? |

---

## 3. ĐA LUỒNG — ĐO ĐƯỢC, VÀ RÀNG BUỘC THẬT

### 3.1 Kết quả đo (ca i1, i2)

```bash
python3 app/thu/thu_http_jt.py CaDongThoi -v
```

| Phép đo | Số thật | Nghĩa |
|---|---|---|
| 24 luồng × 1 lượt gọi, stub `VONG_LAP` (thân dựng TỪ yêu cầu) | **24/24 OK**, 24/24 nhận ĐÚNG dữ liệu của mình, 0 lẫn | Không có socket/bộ đệm dùng chung giữa các lượt |
| `cao_nhat_dang_xu_ly` (số yêu cầu chồng nhau nhiều nhất ở stub) | **24** | Song song THẬT, không có khoá nào tuần tự hoá |
| Cùng phép đo, chạy TUẦN TỰ 6 lượt (đối chứng) | **1**, và mất **1,514s** | Con số 24 ở trên không phải hằng số của stub |
| 24 luồng, stub ngủ 0,25s/lượt | **0,262s** | Tuần tự sẽ là 6,0s ⇒ nhanh hơn ~23× |
| 12 lượt gọi (song song) → số kết nối TCP được chấp nhận | **12** | **MỘT lượt = MỘT kết nối**, không dùng lại |
| Đối chứng cho chính máy đếm: 3 yêu cầu trên MỘT `HTTPConnection` | **+1 kết nối** | Máy đếm đếm KẾT NỐI, không đếm yêu cầu |
| fd trước/sau **20 lượt gọi tuần tự** | **7 → 7** | Không rò fd |
| 16 lượt đang bay (stub ngủ 1,0s) | **1,01s**, fd đỉnh **+32**, sau khi xong **+0** | Mỗi lượt đang bay giữ fd (16 phía client + 16 phía stub trong cùng tiến trình); gọi xong TRẢ LẠI HẾT |

### 3.2 Ràng buộc TÌM ĐƯỢC — trả lời đúng ba câu hỏi đã đặt ra

**a) Connection pool: KHÔNG CÓ, và đó là sự thật được đo, không phải suy đoán.** Mỗi lượt gọi mở một
kết nối TCP mới rồi đóng. Hệ quả ĐO ĐƯỢC: `N` lượt gọi đồng thời ⇒ `N` socket ⇒ **trần đồng thời của
lớp này là trần file descriptor của tiến trình, không phải một con số của chính nó.** Trên máy này
`RLIMIT_NOFILE` mềm = **1048575** (không phải chỗ nghẽn trên máy này); trong một container mặc định
(giới hạn 1024) trần thực tế **suy ra** sẽ vào khoảng **~1000 lượt đang bay** — con số đó là SUY RA,
**chưa đo trên container nào**, và lớp này **không** có van nào để hãm trước ngưỡng
đó. Van hãm (nếu cần) **không** nằm ở đây — nó phải nằm ở lớp trên (`app/gioi_han.py`), nơi có hạn mức
theo tenant. **Đây là điều làn này KHÔNG sửa: thêm một pool là thêm trạng thái dùng chung — đúng thứ
mà mục 3.2b nói đang KHÔNG có, và là một quyết định thiết kế của AG-00, không phải của một làn đo.**

**b) Thread-safety: ĐẠT, và đạt theo cách dễ kiểm nhất — KHÔNG CÓ TRẠNG THÁI DÙNG CHUNG.** Lớp HTTP
không có biến toàn cục bị ghi trong lúc gọi, không có khoá, không có bộ đệm, không có pool. Phép đo
i1 (24 luồng, mỗi luồng nhận lại ĐÚNG `bizContent` của mình, 0 lẫn) là bằng chứng trực tiếp. Đổi lại:
**không có gì để tái dùng giữa các lượt** — xem (a) và (d).

**c) `socket.getdefaulttimeout()`: KHÔNG ảnh hưởng, và KHÔNG bị đổi (ca i3).** Hai chiều đều được đo:

- Đặt mặc định toàn cục **30,0s** rồi gọi 6 luồng với `timeout=0,3` vào stub ngủ 1,5s ⇒ **cả 6 lượt
  hết giờ theo hạn CỦA NÓ**, tổng thời gian < 2s. Hạn tường minh thắng mặc định toàn cục.
- Một luồng khác **đổi mặc định toàn cục liên tục** (0,001s ↔ 45,0s) trong lúc 4 lượt đang bay ⇒
  vẫn không lượt nào thành công, tổng thời gian vẫn < 1,5s.
- Sau mọi lượt gọi, `socket.getdefaulttimeout()` **vẫn là giá trị mà người khác đặt** ⇒ lớp này không
  sở hữu và không đổi biến toàn cục của tiến trình.

**d) Chi phí ẩn ĐO ĐƯỢC: `ssl.create_default_context()` dựng MỚI mỗi lượt gọi HTTPS.** Ba lượt đo,
mỗi lượt 300 mẫu (không cần mạng):

```
ssl.create_default_context()              1,74 – 1,95 ms/lượt   (ba lượt: 1,74 · 1,89 · 1,86)
http_jt._mo_ket_noi("https", host, 443)   1,71 – 1,80 ms/lượt   (chưa connect, chưa TLS handshake)
```

Nghĩa là **mỗi lượt gọi J&T trả ~1,8 ms CPU chỉ để dựng lại ngữ cảnh TLS**, rồi mới tới một TLS
handshake đầy đủ (không keep-alive). **Làn này KHÔNG sửa** (không cache `SSLContext`): cache là thêm
trạng thái toàn cục + một khoá, tức đánh đổi đúng tính chất ở (b), và nó kéo theo câu hỏi xoay vòng
CA của tiến trình dài sống — **thuộc quyết định của AG-00**. Số ở đây để quyết định đó có dữ liệu.

---

## 4. HAI TẦNG HẠN THỜI GIAN — TÁCH RÕ, ĐO CẢ HAI

Cách đo hạn NỐI mà không ra Internet: `HoDenKetNoi` — một socket `listen(1)` trên loopback **không
bao giờ `accept`**. Hàng đợi đầy thì nhân hệ điều hành **im lặng bỏ qua SYN**, nên `connect()` TREO
THẬT ở tầng TCP. Fixture **TỰ KIỂM** độ no (một lượt nối thăm dò phải hết giờ, nếu không nó NÉM) —
để một "hố đen" không thật không âm thầm làm ca đo xanh vô nghĩa.

### 4.1 Hạn NỐI = `min(timeout, HET_GIO_KET_NOI_TOI_DA = 5,0)` (ca k1, k3)

| Hố đen + `timeout` | Thời gian tới lúc ném | `loai` | `ket_cuc` | `timeout` |
|---|---|---|---|---|
| `0,3s` | **0,3012s** | `het-gio` | **`khong-gui-di`** | `True` |
| `7,0s` (xin 7, trần 5) | **5,0015s** | `het-gio` | **`khong-gui-di`** | `True` |

Đối chứng dương: **cùng hạn 0,3s**, một máy chủ loopback SỐNG trả lời trong < 0,3s ⇒ 0,3s là đủ, không
phải "mọi thứ đều hết giờ". Đối chứng âm: trần 5,0s bị vượt tới 7,0s ⇒ trần **có** tác dụng.

### 4.2 Hạn ĐỌC = `timeout`, KHÔNG bị trần 5,0s kẹp (ca k2, k4)

| Stub | `timeout` | Kết quả |
|---|---|---|
| ngủ 1,5s | `0,35s` | ném sau **0,3524s** · `het-gio` · **`khong-biet`** · `timeout=True` · stub nhận **đúng 1** yêu cầu |
| ngủ 1,5s | `4,0s` | **THÀNH CÔNG** sau ~1,5s, thân đúng (đối chứng dương) |
| ngủ **5,4s** (dài hơn trần NỐI 5,0s) | `7,0s` | **THÀNH CÔNG** sau **5,405s** — hạn ĐỌC không bị trần NỐI cắt |

### 4.3 Kết cục KHÁC NHAU, KHÔNG GỘP — đây là phần quan trọng nhất của việc "tách rõ"

| Hỏng ở tầng nào | Yêu cầu đã ra khỏi máy? | `ket_cuc` | Thử lại |
|---|---|---|---|
| **NỐI** (SYN không hoàn tất) | **KHÔNG** — chưa byte nào | **`khong-gui-di`** | **AN TOÀN** |
| **ĐỌC** (đã gửi, chờ phản hồi) | **CÓ** — hãng có thể đã xử lý | **`khong-biet`** | **KHÔNG được coi là an toàn** |

Gộp hai dòng này là **hỏng theo cả hai hướng**: gộp NỐI vào `khong-biet` thì mất một đường thử lại
an toàn; gộp ĐỌC vào `khong-gui-di` thì **báo an toàn cho một lượt CÓ THỂ đã tạo đơn**. Hai đột biến
trong bảng §7.2 đo đúng hai hướng đó.

### 4.4 Treo KHÔNG BAO GIỜ được đọc thành công — và MỘT GIỚI HẠN ĐÃ BIẾT

Bốn hình dạng treo (ca k5), tất cả đều **NÉM**, không bao giờ trả `TraLoiHTTP`:

| Hình dạng | `loai` | `than_dut` | `ket_cuc` |
|---|---|---|---|
| Stub ngủ trước khi trả lời | `het-gio` | — | `khong-biet` |
| **HTTP 200 + `Content-Length` lớn hơn số byte thật gửi** | `than-doc-do` | `True` | `khong-biet` |
| Hãng nhận yêu cầu rồi ĐÓNG, không trả lời | `ket-noi-dut` | — | `khong-biet` |
| **HTTP 200 rồi NHỎ GIỌT, khe giữa hai byte lớn hơn hạn đọc** | `than-doc-do` | `True` | `khong-biet` |

Thân đọc dở **không** xuất hiện ở bất kỳ luồng ra nào (`str`, `repr`, `than_da_che`): khẳng định
"`billCode` không có trong cả ba" là khẳng định trực tiếp rằng một thân 200 nhận được MỘT PHẦN không
đi tiếp.

**GIỚI HẠN ĐÃ BIẾT (ca k6) — `timeout` KHÔNG phải hạn TỔNG.** `http.client` đặt hạn lên **từng lần
đọc socket**, nên một máy chủ nhỏ giọt giữ được lượt gọi lâu hơn `timeout`:

```
stub gửi 1 byte mỗi 0,2s;  timeout = 0,6s
ĐO ĐƯỢC: lượt gọi trả về sau 1,228s (> 0,6s gấp đôi) — THÀNH CÔNG, thân TRỌN VẸN (69 byte)
chiều ngược lại: khe 0,9s > timeout 0,5s ⇒ hết giờ NGAY GIỮA thân HTTP 200, than_dut=True
```

Đây **không** phải "đạt": đó là một **giới hạn của lớp này**, ghi lại để (i) người gọi không đọc
`timeout` thành "hạn chót của cả lượt", và (ii) nếu AG-00 muốn một hạn TỔNG thì đó là một quyết định
thiết kế mới (hạn tổng sẽ cắt cả những lượt gọi hợp lệ đang chậm mà vẫn trả về đủ thân). Điều **vẫn
được bảo đảm** và đã đo: thân trả về luôn TRỌN VẸN — thân đọc dở không bao giờ thành công.

---

## 5. CHE BÍ MẬT — BỐN ĐƯỜNG RÒ ĐO ĐƯỢC, VÀ CÁI ĐÃ VÁ

Cổng che của G16 che theo **giá trị đã gửi**, hai mức (theo TÊN credential bất kể độ dài; theo ĐỘ DÀI
≥ 8 ký tự). Làn này đo **bốn đường nữa** — cả bốn đều **RÒ THẬT** trước khi vá, và mỗi đường nay có
ca riêng + một dòng đột biến chứng minh ca đó có răng.

### 5.1 Bốn đường rò, và cách vá

| # | Đường rò (ĐO ĐƯỢC trước khi vá) | Vì sao lọt | Cách vá |
|---|---|---|---|
| **R1** | Bí mật `aB?cd&e=f` ở `bizContent.password` hiện lại **nguyên văn dạng `aB%3Fcd%26e%3Df`** trong `than_da_che` | Phép che so khớp chuỗi Python; hãng echo lại **byte trên dây** đã percent-encode | `_bien_the()`: mọi giá trị được che ở **MỌI dạng** nó có thể mang (percent-encode 1–2 lớp) |
| **R2** | Bí mật phi-ASCII gửi bằng `ensure_ascii=True` hiện lại thành `m%5Cu1eadt-…` | JSON escape ASCII rồi percent-encode — hai lớp mã hoá nữa | cùng `_bien_the()`: bao đóng 2 lớp của {percent-encode, JSON-escape} |
| **R3** | Token trong **QUERY của URL** (`?tk=…`): (a) RÒ vào `str(e)` qua `InvalidURL` của `http.client` — ngoại lệ đó **mang theo cả URL**; (b) **không nằm trong tập che** nên hãng echo lại là lộ | `_gia_tri_can_che` chỉ nhìn header + thân form; URL không được đưa vào | `tach_url` **TỪ CHỐI ký tự điều khiển TRƯỚC khi mở socket** (thông điệp chỉ nêu VỊ TRÍ + MÃ ký tự) · `_gia_tri_tu_url()` đưa giá trị query vào tập che · `str(e)` thô đi qua phép che |
| **R4** | Bí mật nằm NHẦM ở **vị trí TÊN** header/trường form bị in nguyên văn (`str(ten)[:40]`) — đúng chỗ chú thích cũ khẳng định là "giá trị thì không được in ra" | Thông điệp lỗi dựng trước khi có tập che | `_mo_ta_ten()`: tên KHÔNG hợp lệ chỉ được mô tả bằng **số ký tự + vị trí + U+XXXX**, không in giá trị; tên HỢP LỆ vẫn in nguyên văn để chẩn đoán không mất thông tin |

Hai lỗ **tìm thêm được trong lúc đo** (không nằm trong 4 đường bắt buộc, nhưng cùng một họ "hợp đồng
nói một đằng, mã làm một nẻo"):

| # | Lỗ | ĐO ĐƯỢC | Cách vá |
|---|---|---|---|
| **R5** | `tach_url("http://[abc/…")` để **`ValueError` TRẦN** nổi ra ngoài. `transport.goi()` chỉ bắt `LoiTamThoi`/`LoiVinhVien` ⇒ lỗi này nổi lên tận Order Service như **lỗi 500** | Trước khi vá: `ValueError: Invalid IPv6 URL` | Bọc `urlsplit` → `LoiVinhVien` + `ket_cuc='khong-gui-di'`, thông điệp chỉ nêu LOẠI lỗi |
| **R6** | Ngoại lệ THÔ còn nối được qua `__context__`. `IncompleteRead` **giữ nguyên thân đọc dở trong `.partial`** — mà thân đọc dở có thể chứa bí mật | `from None` chỉ che phần IN RA; `e.__context__` vẫn là ngoại lệ thô | Dựng ngoại lệ đã che trong `except` nhưng **NÉM ở NGOÀI khối `except`** ⇒ `__context__ is None` (ca j7 khẳng định trực tiếp) |

### 5.2 Bốn nhóm ca bắt buộc (§5.1 là cách vá, đây là cách ĐO)

| Nhóm | Ca | Đo gì | Đối chứng dương (bí mật THẬT SỰ đã đi và THẬT SỰ bị echo) |
|---|---|---|---|
| **(a) NGẮN 1–5 ký tự** | j1 | `"j"` (1) · `"a%b"` (3) · `"aB?cd"` (5) · `"ộ"` (1, phi-ASCII) — ở header credential VÀ trong thân form | cả 4 giá trị có trong thân echo, **và** dạng trên dây (`a%25b`, `%E1%BB%99`) cũng có |
| **(b) HEADER và THÂN** | j2 | bí mật ≥ 8 ký tự ở tên KHÔNG phải credential (`X-Ma-Noi-Bo`, `ghiChu`, `maNoiBo`) | đối chứng ngưỡng: `VH123456` (8) bị che, `VH12` (4) KHÔNG bị che ⇒ ngưỡng còn tác dụng |
| **(c) DỚP LẶP** | j4 | bí mật xuất hiện **≥ 3 lần** trong thân (stub echo lặp 3 khối) | đếm được ≥ 3 lần trong thân THÔ; sau khi che: **0** lần, `[DA-CHE]` ≥ 3 |
| **(d) CHUỖI LỖI / exception / repr** | j6, j7 | giá trị ở vị trí TÊN · `IncompleteRead.partial` chứa bí mật · `traceback.format_exception` · `__context__` | bí mật có trong thân echo; `str/repr/args/than_da_che/headers_da_che/traceback/__context__` đều KHÔNG |

Mỗi khẳng định phủ định ở trên chạy trên **MỌI dạng** của bí mật, và tập dạng được tính bằng một
**bản cài thứ hai** trong tệp thử (`cac_dang()`), **không** gọi `http_jt._bien_the` — nếu bộ thử lấy
chính hàm của sản phẩm để quyết định "phải tìm những dạng nào" thì nó chỉ đang tự kiểm chính nó.

### 5.3 NGOÀI PHẠM VI của cổng che — nói thẳng

- **`mo_ta` (mô tả yêu cầu) KHÔNG đi qua phép che, và đó là CHỦ Ý.** Nó chỉ nêu TÊN header/trường và
  **ĐƯỜNG DẪN**, không nêu query. Che nó đi sẽ làm hỏng chính ca tự kiểm `test_g3` (ca đó đột biến
  hàm dựng mô tả để in giá trị header ra và đòi ca rò rỉ phải ĐỎ) — tức là **làm cổng cũ mất răng**.
- **Bí mật đặt trong ĐƯỜNG DẪN của URL KHÔNG được che.** Đường dẫn được in nguyên văn vì nó là thứ
  duy nhất cho biết lượt gọi đi tới endpoint nào. Mitigation đã có: URL chứa `user@host` bị TỪ CHỐI,
  URL chứa ký tự điều khiển bị TỪ CHỐI TRƯỚC khi mở socket, và **query thì ĐƯỢC che**. Quy tắc vận
  hành: **credentials không đi qua URL** (đúng như chú thích `tach_url` đã có từ G16).
- **Thân của một lượt 2xx vẫn NGUYÊN VĂN, không che** — hợp đồng §36 ("thân trả về cho người gọi thì
  nguyên văn"). Nếu hãng echo bí mật vào một thân **200**, lớp này trả nguyên văn cho người gọi; việc
  che thuộc về nơi ghi log. Đây là ranh giới thiết kế, không phải lỗ hổng mới.
- **Giá trị NGẮN (< 8) ở tên KHÔNG phải credential vẫn KHÔNG bị che** (ngưỡng còn nguyên tác dụng —
  cố ý, để thông điệp chẩn đoán còn đọc được). Bí mật loại đó phải nằm ở một trong bốn tên credential.

---

## 6. GIỮ NGUYÊN NHỮNG GÌ ĐÃ CHỐT Ở G16 — và các ca canh chúng

Làn này **không** nới một chốt nào. Bốn chốt được nêu trong đề bài, kèm đúng ca đang canh chúng:

| Chốt | Ca canh (vẫn XANH) |
|---|---|
| **Danh sách trắng máy chủ** — chỉ 2 host J&T + loopback, so **KHỚP CHÍNH XÁC** | `d1` (từ chối TRƯỚC khi mở socket, máy đếm = 0) · `d2` (host na đuôi) · `d3` (không trôi khỏi `adapter_jt`, soát AST) · **`i4` (mới): chốt chặn vẫn bắt được TRONG LUỒNG, 3 host ngoài ⇒ 0 lượt nối)** |
| **Ba kết cục KHÔNG GỘP** | `f1` (ok vs hãng từ chối — phân biệt bằng `code` trong thân nguyên văn) · `f2` (kết cục thứ ba NÉM, không trả `TraLoiHTTP`) · `b1`/`b2` (5xx tạm thời vs 4xx vĩnh viễn) · **`k5` (mới): treo ⇒ NÉM ở cả 4 hình dạng, kể cả khi đã nhận HTTP 200** |
| **408/429 là TẠM THỜI + `Retry-After` KẸP TRẦN `transport.CHO_TOI_DA`** | `b7` (429 ⇒ `qua-han-muc`, KHÁC 5xx trong log) · `b8` (408 ⇒ `khong-gui-di`, KHÁC 429) · `b9` (`Retry-After` số giây + HTTP-date + rác + mốc đã qua, **kẹp trần 60,0s**) · `b10` (hai lớp `http_jt`/`loi_hang` ĐỒNG Ý trên 7 mã) · `b12` (chờ tới được `transport.goi()`) |
| **`gui_form` KHÔNG BAO GIỜ NGỦ** | `b11` — soát **AST** (`sleep`/`time.sleep`/`…ngu`), chú thích và chuỗi không tính. Làn này **không thêm một lời gọi ngủ nào** vào `http_jt.py`: `NHO_GIO` ngủ ở STUB, `VONG_LAP`/`DOI_DAU_LAP` ngủ ở STUB, hố đen không ngủ ở đâu cả — chỗ ngủ duy nhất trong mã sản phẩm vẫn là `transport.goi()` |
| **Chỉ gửi FORM `application/x-www-form-urlencoded`** | `a1` (4 header bắt buộc, đúng tên/thứ tự) · `a2` (thân form đúng BYTE: `%2B`, `%26`, `%C6%AF`, đếm `+`) · `a5`/`a6` (`Content-Type` tự thêm; `Content-Length` do `http.client` đặt) |

---

## 7. BẰNG CHỨNG — LỆNH THẬT, KẾT QUẢ THẬT

### 7.1 Bộ thử của làn này

```bash
cd ~/orca/workspaces/vip-express-hub/g17-ag02-transport
python3 app/thu/thu_http_jt.py -v
```

**Kết quả thật (lượt ĐÓNG BĂNG, xem §9):**

```
Ran 57 tests in 92.042s

OK
EXIT=0
```

**37 → 57 ca** (+20). Thời gian chạy 6,3s → ~92s: **đắt hơn 14 lần**, và đó là giá đã biết của
`CaTuKiemG17` — mỗi dòng đột biến là một tiến trình Python mới, và hai ca đo hạn thời gian THẬT
(k3, k4) tốn ~5s mỗi lượt chạy.

Phân bổ 20 ca mới (18 ca đo + 2 ca tự kiểm):

| Lớp | Ca | Đo cái gì |
|---|---|---|
| `CaDongThoi` | i1–i4 | 24 luồng không lẫn dữ liệu + song song thật (2 đường đo + đối chứng tuần tự) · MỘT kết nối/lượt + đối chứng máy đếm + fd trả lại hết · `getdefaulttimeout` hai chiều · chốt chặn mạng trong luồng |
| `CaHetGioNhieuTang` | k1–k6 | hạn NỐI (hố đen, tự kiểm độ no) · hạn ĐỌC · trần 5,0s · hạn ĐỌC KHÔNG bị trần kẹp · 4 hình dạng treo không bao giờ thành công · giới hạn "hạn từng lần đọc ≠ hạn tổng" |
| `CaBiMatMoRong` | j1–j8 | 4 đường rò + 2 lỗ hợp đồng (§5.1), mỗi ca có đối chứng dương và chạy trên MỌI dạng của bí mật |
| `CaTuKiemG17` | l1–l2 | 20 dòng đột biến mã sản phẩm (mỗi dòng phải làm ca canh nó ĐỎ) + đối chứng dương theo LỚP CA (mỗi lớp phải XANH khi không đột biến) |

### 7.2 TỰ KIỂM BỘ DÒ — 20 đột biến mã sản phẩm + 3 đối chứng dương

`CaTuKiemG17` chạy **20 dòng** (mỗi dòng: một đột biến **mã sản phẩm** + ĐÚNG ca canh nó, trong một
**tiến trình con**); mỗi dòng phải làm ca đó **ĐỎ**. Kèm **đối chứng dương**: mỗi LỚP ca chạy nguyên
vẹn, KHÔNG đột biến, trong tiến trình con và phải **XANH** — nếu không thì "đột biến làm ca đỏ" không
chứng minh được gì.

**Kết quả thật:**

```
Ran 2 tests in 56.826s

OK
```

20 dòng đột biến — mỗi dòng là một **hồi quy có thật**, không phải một phép đột biến cho vui:

| Ca bị đột biến | Đột biến (mã sản phẩm) | Hồi quy được mô phỏng |
|---|---|---|
| i1 | bọc `gui_form` bằng một `Lock` toàn cục | thêm khoá quanh mọi lượt gọi ⇒ 24 luồng bị tuần tự hoá |
| i2 | "pool" MỘT kết nối dùng chung, không khoá + `connect()` thành no-op | thêm pool ẩu ⇒ nhiều luồng chung một socket |
| i3 | `_mo_ket_noi` tự gọi `socket.setdefaulttimeout(7.0)` | lớp HTTP đổi mặc định TOÀN CỤC của tiến trình |
| i3 | `socket.socket.settimeout` thành no-op | hạn đọc bị bỏ, socket nghe theo mặc định toàn cục |
| i4 | `host_duoc_phep = lambda h: True` | danh sách trắng bị vô hiệu ⇒ một URL gõ sai thành lượt gọi ra Internet |
| k1 | `KET_CUC_KHONG_GUI_DI = KET_CUC_KHONG_BIET` | gộp "hết giờ NỐI" (chưa gửi đi) vào "không biết" |
| k1 | `HET_GIO_KET_NOI_TOI_DA = 0.0` | mất hạn NỐI: lượt nối không còn được chờ |
| k2 | `KET_CUC_KHONG_BIET = KET_CUC_KHONG_GUI_DI` | gộp "hết giờ ĐỌC" vào "chưa gửi đi" ⇒ báo an toàn cho lượt CÓ THỂ đã tạo đơn |
| k3 | `HET_GIO_KET_NOI_TOI_DA = 0.0` | trần hạn NỐI bị phá theo hướng ngược lại |
| k4 | kẹp `_kiem_tra_het_gio` bằng trần NỐI | "đơn giản hoá" sai: hạn ĐỌC bị trần NỐI cắt ⇒ lượt chậm > 5s bị cắt oan |
| k5 | mọi `LoiTamThoi` thành `TraLoiHTTP(200, …)` | TREO bị đọc thành THÀNH CÔNG — lỗi nặng nhất lớp này tồn tại để chặn |
| k6 | (như k5) | thân đọc dở giữa một HTTP 200 được trả về như lượt thành công |
| j1 | `TRUONG_CREDENTIAL = ()` | bỏ mức che THEO TÊN ⇒ credential 1–5 ký tự lộ (đúng lỗi G16-05) |
| j2 | `DA_TOI_THIEU_DE_CHE = 10**6` | bỏ mức che THEO ĐỘ DÀI ⇒ bí mật ≥ 8 ký tự lộ |
| j3 | `_bien_the = lambda s: {s}` | quay lại che theo CHUỖI GỐC ⇒ dạng percent-encode/JSON-escape lộ |
| j4 | `che_bi_mat` chỉ thay lần xuất hiện ĐẦU TIÊN | các bản DỚP LẠI lộ nguyên văn |
| j5 | `_gia_tri_tu_url = lambda u: set()` | bỏ giá trị QUERY của URL khỏi tập che |
| j6 | `_mo_ta_ten = lambda t: str(t)` | in thẳng TÊN không hợp lệ ⇒ giá trị ở vị trí tên lộ |
| j7 | nối lại `__context__ = e` và gắn `e.partial` vào `than_da_che` | ngoại lệ THÔ (chứa thân đọc dở) đi theo vào log |
| j8 | bỏ lớp bọc `urlsplit` | `ValueError` trần nổi lên tận Order Service như lỗi 500 |

### 7.3 Ba bộ thử phụ thuộc (chạy trên CÙNG cây, sau khi vá)

```bash
python3 app/thu/thu_qa_g16.py      # bộ QA ĐỘC LẬP của AG-01 trên lớp này
python3 app/thu/thu_adapter_jt.py  # AG-03
python3 app/thu/thu_hop_dong_jt.py # hợp đồng J&T
```

```
thu_qa_g16      exit=0   (bộ QA độc lập của AG-01 vẫn ĐẠT trên bản đã vá)
thu_adapter_jt  Tổng: 71 ca · hỏng 0 · lỗi 0 · bỏ qua 0      exit=0
thu_hop_dong_jt Tổng: 64 ca · hỏng 0 · lỗi 0 · bỏ qua 0      exit=0
```

### 7.4 Hồi quy TOÀN DỰ ÁN (bộ chạy tự dò)

```bash
cd ~/orca/workspaces/vip-express-hub/g17-ag02-transport
VIP_HUB_DATA=/tmp/veh_g17_ag02 sh app/thu/chay_tat_ca.sh
```

Xem §9 để có kết quả của lượt đóng băng (kèm mã thoát và bảng tổng kết nguyên văn).

**Kết quả thật** (`VIP_HUB_DATA=/tmp/veh_g17_final2`, mốc 17:09:23 +07, mã thoát **0**):

```
  ✓ thu_http_jt.py             57 ca
  ✓ thu_qa_g16.py              61 ca
  python:   1304 ca · 36 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  KHÔNG
EXIT=0
```

**37 bộ** chạy thật, **1304 ca** python, **0 bộ hỏng**. Làn này **không** làm hỏng bộ nào của làn
khác — kể cả `thu_qa_g16.py` (bộ QA độc lập của AG-01) và `thu_adapter_jt.py` (AG-03) chạy trên
chính lớp vừa được vá.

### 7.5 MỘT LỖI CỦA CHÍNH BỘ THỬ, do ca i4 phát hiện ra

`ChanMangNgoai.bat()` **không idempotent**: gọi hai lần thì mỗi lượt nối bị **ĐẾM HAI LẦN**. Lỗi có
thật và đo được: `chay_con` gọi `setUpModule()` thủ công, rồi `unittest` gọi nó **LẦN NỮA** khi chạy
suite ⇒ ca i4 thấy **16 lượt nối cho 8 lượt gọi**. Đã vá (`bat()` gọi lần hai là no-op), và ghi lại ở
đây vì đúng bài học `BAN_GIAO.md` §7.1: **bộ đếm là BẰNG CHỨNG, nên nó phải đúng cả khi bị gọi hai
lần.** Không có ca đếm-lượt-nối thì lỗi này vẫn nằm đó.

---

## 8. CÁI GÌ NẰM NGOÀI — ĐỌC KỸ TRƯỚC KHI TIN BẤT KỲ SỐ NÀO Ở TRÊN

1. **Không có lượt gọi hãng nào, kể cả sandbox.** `V-G09-01` + `V-13906-05` CHƯA CẤP. **TLS thật tới
   `*.jtexpress.vn` CHƯA ĐO**; chứng thư, SNI, ALPN, proxy công ty, IPv6 — **chưa đo gì**.
2. **Mọi con số về hạn thời gian là của STUB CỤC BỘ trên loopback.** Hành vi của J&T thật (thời gian
   phản hồi, `Retry-After` thật, mã lỗi thật) **CHƯA ĐO**.
3. **Đa luồng được đo trong MỘT tiến trình, trên MỘT máy.** Chưa đo nhiều tiến trình, chưa đo nhiều
   máy, chưa đo dưới tải lớn; hạn mức theo tenant sống trong bộ nhớ một tiến trình (`gioi_han.py`).
4. **Không có pool, không có van đồng thời ở lớp này** — đó là ĐO ĐƯỢC, không phải thiếu sót được vá.
   Trần thực tế ≈ trần file descriptor của tiến trình (máy này: 1048575; container 1024 ⇒ **suy ra**
   ~1000 lượt đang bay — chưa đo trên container).
5. **`timeout` không phải hạn TỔNG** (§4.4) — đo được, ghi lại, KHÔNG sửa.
6. **`SSLContext` dựng mới mỗi lượt HTTPS** (~1,8 ms/lượt, ba lượt đo độc lập) — đo được, KHÔNG sửa
   (thuộc quyết định AG-00).
7. **Che bí mật chỉ áp cho ngoại lệ/header/`repr`.** Thân 2xx vẫn nguyên văn (hợp đồng §36); bí mật
   trong ĐƯỜNG DẪN URL vẫn được in (§5.3).
8. **Bộ thử tự dò của dự án chạy 3 tầng + E2E**, nhưng tầng 3 (Chromium) **không** chạy trong
   `chay_tat_ca.sh`; nó có bộ chạy riêng. Làn này **không** chạm frontend.
9. **Chưa ai soát lại.** Toàn bộ là tác tử AI. `V5/V6/V7` toàn cục vẫn mở (`QA_G13_G15.md` §L2.8) —
   làn này không chạm webhook/RBAC/AES.

---

## 9. ĐÓNG BĂNG — VÂN TAY, MỐC GIỜ, VÀ CAM KẾT DỪNG

| | |
|---|---|
| **Mốc giờ đóng băng mã** | **15/10/2026 17:07:43 +07** (mtime của hai tệp mã sửa cuối; vân tay dưới đây chốt lúc 17:09, kiểm lại lúc 17:14 — **không đổi**) |
| **Nền** | `integration/g16` @ `98baeb3` |
| **Nhánh / worktree** | `g17-ag02-transport` (worktree riêng của làn AG-02) |
| **`git status --porcelain`** | ` M app/http_jt.py` · ` M app/thu/stub_jt.py` · ` M app/thu/thu_http_jt.py` · `?? docs/G17_TRANSPORT.md` — **không tệp nào khác** |

`main = de740dc` **KHÔNG** chứa G13–G16 (đã xác minh ở làn khác); làn này **không** push, **không**
merge, **không** đụng `main`.

### Vân tay (§41 — chép nguyên văn lệnh của hợp đồng)

```bash
find app gateway thu_frontend thu_giao_dien -type f \
  \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
  | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
```

| Tệp | sha256 |
|---|---|
| `app/http_jt.py` | `7f8d8949bf381c889aa2d349e20f8710e32175e0dbd17d1af04d4c1539923c92` |
| `app/thu/stub_jt.py` | `fff95bb49363ee4cb9dc72108683787380ac373989e78b1aaffc0f8ffefcb8c8` |
| `app/thu/thu_http_jt.py` | `77b208f12e87d41e1bf1499d9fb6c98c32b67b2b32331c9c4ef14ec4950ae21e` |
| **Vân tay cây** | `285f38f6db0ce76964f00e4cfbbd6063b2a97382d8b1c362a38e086d7fcd4b45` |

Kích thước: `app/http_jt.py` 872 dòng · `app/thu/stub_jt.py` 552 dòng · `app/thu/thu_http_jt.py`
1866 dòng. `HEAD` = `98baeb357214d41a9380467fde2fee2b94fd31cc`.

**Từ mốc này, làn AG-02 KHÔNG sửa thêm một dòng MÃ nào.** Lý do là bài học G16 (AG-01 đếm được
`app/http_jt.py` đổi **sáu bản** trong lúc nghiệm thu): *"xanh trên sáu bản tôi đã đo"* **không** phải
*"xanh trên bản cuối"*. Mọi thay đổi mã sau mốc này phải do **AG-00** chủ trì, và khi đó vân tay ở
trên **hết hiệu lực** — phải đo lại.

**Lượt đóng băng** (dán nguyên văn phần cuối của `chay_tat_ca.sh`, sau khi mã đã đứng yên):

```
  ✓ thu_http_jt.py             57 ca
  ✓ thu_qa_g16.py              61 ca
  python:   1304 ca · 36 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      KẾT QUẢ: 41/41
  bộ hỏng:  KHÔNG

  PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI:
    đo trên: Darwin arm64 · python 3.9.6 · SQLite 3.51.0
    máy chủ bind 127.0.0.1 · adapter hãng ở chế độ MOCK (2 hang dang ky (jt, vtp) - dang MO live: khong hang nao)
EXIT=0
```

---

## 10. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY

- Mọi số ở §3–§7 do **một làn AI** chạy trên máy này (macOS arm64 · Python 3.9.6 · SQLite 3.51.0), trên nền
  `98baeb3`. **Chưa người nào soát lại.**
- Cây làm việc **đang được các làn khác ghi đồng thời** (mỗi làn một worktree) ⇒ con số hồi quy ở
  §7.4 là **ảnh chụp tại một thời điểm**, không phải một thuộc tính ổn định của cây.
- §8 nói thẳng cái gì nằm ngoài. **Không kết luận nào ở đây được phép đọc rộng hơn phạm vi đó.**
- Bộ thử xanh **không phải** lời cho phép gọi sandbox hay production. Việc mở `ChoPhepLive` **không**
  thuộc làn này.
