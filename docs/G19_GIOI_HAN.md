# G19/AG-02 — GIỚI HẠN TẦN SUẤT: ĐÓNG HAI LỖ HỔNG ĐÃ ĐO ĐƯỢC

Trần nhân theo số bản (lỗ hổng a) · mất bộ đếm khi khởi động lại (lỗ hổng b)

Nền: `integration/g18` @ `6e61fc1e1f1f9a6d64931464e4f40ed887192ab5` · nhánh `g19-ag02-gioihan`
Tệp được phép ghi: `app/gioi_han.py` · `app/thu/thu_g19_gioihan.py` (mới) · `docs/G19_GIOI_HAN.md` (mới)

Vân tay tệp (sha256):

| Tệp | Cây nền `6e61fc1` | Sau lượt này |
|---|---|---|
| `app/gioi_han.py` | `909761ae7c73f2c0ded3e97bfd98013f73bff64553699e0ca6d3cdf0a0ade7ba` | `a53b199e8bc77eab1361edef389b4c69d907e271ccf4b7054bbd4ccd522e9ba9` |
| `app/thu/thu_g19_gioihan.py` | (chưa có) | `53bb154d826ae3ef8901e733ef525c5043de7ec3f06756dd8d7bebde732681a0` |

---

## 1. Tóm tắt

PHẦN A của `app/gioi_han.py` (giới hạn tần suất) giữ bộ đếm trong **bộ nhớ một tiến trình**. Hai
lỗ hổng đã được đo bằng tiến trình thật:

| # | Lỗ hổng | Đo được (TRƯỚC) | Sau khi vá |
|---|---------|------------------|------------|
| a | Trần nhân theo số bản | khai 20 ⇒ cho qua **20 · 40 · 80 · 160** lượt với N = 1·2·4·8 tiến trình máy chủ | **20** ở mọi N (đúng một trần) |
| b | Mất bộ đếm khi khởi động lại | tiêu hết 20 suất, **tắt** tiến trình, tiến trình MỚI vẫn cho qua tiếp | tiến trình MỚI **bị chặn** (kể cả ở lớp HTTP) |

Cách vá: chuyển trạng thái PHẦN A sang **CSDL**, đúng khuôn PHẦN B đã có sẵn trong cùng tệp —
**trần nằm trong chính câu ghi**, CSDL tự so, kết quả xét qua `rowcount`. Không thêm tính năng nào
khác; không nới trần ở chỗ nào; PHẦN B không bị sửa một dòng.

**Đọc mục §4.5 trước khi tin "bộ thử toàn xanh":** sáu bộ thử ĐÃ ĐẠT của G17/G18 nay đổi kết luận,
vì chúng khẳng định chính cái hành vi vừa được vá (hoặc canh bảng mới chưa được khai báo). Đó là
hệ quả tất yếu của việc vá, và cần người sở hữu các tệp đó cập nhật.

---

## 2. Hai lỗ hổng và cách chúng được đo

### 2.1 (a) Trần nhân theo số bản

`app/server.py` là `ThreadingHTTPServer` **một tiến trình**, nên lỗ hổng này chưa lộ ở vận hành hiện
tại — nhưng nó là lỗ hổng THẬT ngày chuyển sang nhiều bản (hoặc chạy sau bộ cân bằng tải). AG-00 đã
đo ở G18 (`app/thu/thu_g18_multiprocess.py`, mục P1); lượt này **đo lại y hệt bằng bộ đo mới**
(`app/thu/thu_g19_gioihan.py`, mục P1) trên cây nền `6e61fc1`:

```
✗ [P1.2] N=2 ... từng bản cho qua [20, 20] ⇒ TỔNG 40 (khai báo 20)   · 2 pid khác nhau phục vụ
✗ [P1.4] N=4 ... ⇒ TỔNG 80
✗ [P1.8] N=8 ... từng bản cho qua [20,20,20,20,20,20,20,20] ⇒ TỔNG 160 · 8 pid khác nhau phục vụ
```

Nguyên nhân nằm ở hai dòng trạng thái trong bộ nhớ: `_lan: OrderedDict[str, deque]` và
`_chan_den: dict` — mỗi tiến trình một bản.

### 2.2 (b) Cửa lách khởi động lại

Cửa lách này **độc lập với số tiến trình**; chính chú thích đầu tệp (CLAUDE.md §12.1 luật 3) đã ghi
nó từ trước. Đo ở mục P4 của bộ đo mới, trên cây nền:

```
✗ [P4.1] tiến trình A (lớp kho NoneType): cho qua 20/20 lượt ⇒ trần đã tiêu hết
         tiến trình B MỚI: cho qua 1, BỊ CHẶN 0          ← khởi động lại là trần về 0
✗ [P4.3] máy chủ #1 (pid 72805) cho qua 20 lượt rồi trả 429
         máy chủ #2 (pid 72807) nhận lượt ĐẦU TIÊN = 401  ← ở LỚP HTTP
✗ [P5.2] sau 11 lượt còn lại 12 (đúng ra là 1)            ← bộ đếm không dùng chung
```

---

## 3. Khuôn vá — và những gì được giữ nguyên

### 3.1 Kho mới: đếm trong CSDL

Hai bảng do chính module tạo (`CREATE TABLE IF NOT EXISTS`, thao tác THÊM — **không `ALTER` bảng
nào đang có**), cùng khuôn với `han_muc_nhap_thang` của PHẦN B:

```sql
gioi_han_luot(khoa TEXT, moc REAL)                    -- mỗi LƯỢT ĐƯỢC CHO QUA là một dòng
ix_gh_luot(khoa, moc)                                 -- chỉ mục cho phép đếm theo cửa sổ
gioi_han_chan(khoa TEXT PRIMARY KEY, chan_den REAL)   -- thời gian phạt (chan_giay)
```

Câu ghi giữ **trần trong chính nó** (khuôn PHẦN B; khác một điểm vì đây là bảng ĐẾM DÒNG):

```sql
INSERT INTO gioi_han_luot (khoa, moc)
SELECT ?, ? WHERE (SELECT COUNT(*) FROM gioi_han_luot WHERE khoa=? AND moc>?) < ?
```

`rowcount == 0` nghĩa là vượt trần. Cả lượt kiểm (mọi chiều) nằm trong **MỘT giao dịch
`BEGIN IMMEDIATE`** (`KhoCSDL.giao_dich`) — nhờ vậy luật 4 ở đầu tệp ("kiểm hết rồi mới ghi") vẫn
đúng khi có nhiều TIẾN TRÌNH, không chỉ nhiều luồng.

Cửa sổ **trượt** được giữ nguyên (mỗi lượt một dòng + đếm `moc > bay - cua_so`), KHÔNG đổi sang cửa
sổ cố định: cửa sổ cố định cho vượt gần 2× trần quanh mốc chuyển cửa sổ, tức là NỚI trần ở một chỗ
khác.

Mốc thời gian lưu là `time.time()` (epoch giây), không phải `time.monotonic()`: monotonic là thang
của một lần chạy hệ điều hành — không so được giữa các tiến trình khác lần khởi động, không sống
qua reboot.

Ngưỡng dọn kho tính từ `CHINH_SACH` + `LUAT_MAC_DINH` (`_cua_so_lon_nhat()`), KHÔNG viết cứng 3600
như bản cũ: viết cứng thì ngày ai thêm một luật có cửa sổ dài hơn, chỗ dọn sẽ âm thầm cắt ngắn trần
của luật đó.

### 3.2 Bất biến giữ nguyên (mỗi cái có ca canh)

| Bất biến | Ca canh |
|---|---|
| Trần theo chiều (`ip`/`dinh_danh`/`tenant`), theo endpoint, cách ly tenant | `thu_gioi_han` b2·b3·b5 |
| Vượt trần thì chặn + `Retry-After` + phạt `chan_giay` | `thu_gioi_han` b1 |
| **Kiểm hết rồi mới ghi**: lượt bị chặn KHÔNG cộng lượt ở chiều nào | `thu_gioi_han` b6 (luồng) · `thu_g19_gioihan` P5.1 (tiến trình) |
| `dat_lai` sau đăng nhập thành công | `thu_gioi_han` b8 · `thu_g19_gioihan` P5.2 (tiến trình) |
| Danh sách ĐEN: endpoint lạ vẫn có trần | `thu_gioi_han` b7 |
| Vô danh chưa biết tên không gộp một bucket chung | `thu_gioi_han` b9 |
| Trần số bucket (`TOI_DA_KHOA`) | `thu_gioi_han` b11 |
| Đồng thời không vượt trần | `thu_gioi_han` b10 (40 luồng) · `thu_g19_gioihan` P3 (8 tiến trình) |
| Không tin `X-Forwarded-For` vô điều kiện | `thu_gioi_han` a1–a5 |
| PHẦN B (hạn mức nhập) nguyên vẹn | `thu_gioi_han` c1–c15 · `thu_han_muc_nguyen_tu` (5 ca) |

### 3.3 Giá phải trả (nói thẳng)

1. **Mỗi lượt kiểm là một giao dịch ghi.** Đo ở §5: 0,238 ms/lượt so với 0,0041 ms/lượt của kho bộ
   nhớ (≈58×), tức khoảng **+0,23 ms cho mỗi yêu cầu HTTP** đi qua giới hạn tần suất.
2. **CSDL là phụ thuộc CỨNG** của đường kiểm. CSDL hỏng thì `kiem` **ném lỗi**, CỐ Ý không im lặng
   cho qua: một giới hạn tần suất tự tắt khi kho hỏng là hỏng im lặng.
3. **Kho dùng chung chỉ trong phạm vi MỘT CSDL.** Nhiều MÁY vẫn nhân theo số máy — xem §6.

---

## 4. Bằng chứng — lệnh thật · mã thoát thật · SHA · số ca · số bỏ qua

Mọi mã thoát dưới đây ghi **trước mọi đường ống** (dạng `lệnh > log 2>&1; echo "exit=$?"`).

### 4.1 Phép đo chính: CÙNG một bộ đo, trước và sau

| Lệnh | Cây | Mã thoát | Ca | Bỏ qua |
|---|---|---|---|---|
| `python3 app/thu/thu_g19_gioihan.py` | nền `6e61fc1` (chưa vá) | **1** | 24 = 14 ĐẠT / 10 HỎNG | 0 |
| `python3 app/thu/thu_g19_gioihan.py` | đã vá | **0** | 22 = 22 ĐẠT / 0 HỎNG | 0 |

Cùng một bộ đo (sha256 `53bb154d…`), cùng một cây mã nguồn **trừ lớp kho**. 10 ca HỎNG ở cây nền rơi
đúng vào hai lỗ hổng: P1.2·P1.4·P1.8 (trần nhân), P3.0–P3.2 (không có kho chung), P4.1·P4.3 (mất
khi restart), P5.1·P5.2 (bất biến không dùng chung qua tiến trình).

Số ca hai lượt khác nhau (24 so với 22) là **cố ý**: khi P3 hỏng thì bộ đo báo từng vòng một
(P3.0·P3.1·P3.2); khi mọi vòng đạt thì gộp thành MỘT ca P3. Số phép đo không đổi.
Lượt chạy sau: 27,0 giây · 45 lệnh thật + mã thoát thật (không lệnh nào thoát khác 0 ngoài những
lệnh mà ca âm CỐ Ý đòi hỏng).

### 4.2 Từng khẳng định sau khi vá (kèm đối chứng độc lập)

```
✓ [P1.0] header `X-RateLimit-Limit`=20 và số lượt cho qua trước 429 = 20 · chiều bị chặn = 'ip'
✓ [P1.1] N=1 ⇒ TỔNG 20
✓ [P1.2] N=2 ⇒ TỔNG 20   ✓ [P1.4] N=4 ⇒ TỔNG 20   ✓ [P1.8] N=8 ⇒ TỔNG 20
         (N=8: từng bản [3,3,3,3,2,2,2,2] = 20 · 8 pid khác nhau THẬT SỰ phục vụ · log hỏng 0)
✓ [P3]   3 vòng × 8 tiến trình đua cùng lúc (hàng rào thời gian) ⇒ mỗi vòng cho qua ĐÚNG 20
         và ĐẾM THẲNG bảng `gioi_han_luot` bằng sqlite3 cũng ĐÚNG 20 dòng
✓ [P4.1] tiến trình A tiêu 20/20 rồi TẮT; tiến trình B MỚI: cho qua 0, BỊ CHẶN 1
✓ [P4.3] máy chủ #1 cho qua 20 rồi 429; máy chủ #2 (MỚI) nhận lượt đầu = 429, Retry-After=300
✓ [P5.1] 4 tiến trình × 6 lượt cho cùng một định danh ⇒ TỔNG 12 (trần 12), chiều `ip` còn 8/20
✓ [P5.2] 11 lượt ⇒ còn 1; tiến trình KHÁC gọi `dat_lai` ⇒ tiến trình THỨ BA thấy còn 12
✓ [P6]   4 tiến trình × 40 lượt xin suất, trần CSDL 150 ⇒ đặt được ĐÚNG 150, chặn 10
```

**Đối chứng ĐỘC LẬP cho P3** (bộ đếm không được tự làm chứng cho chính nó — CLAUDE.md §12.1): số
dòng trong `gioi_han_luot` đọc bằng `sqlite3`, **không qua một hàm nào của `gioi_han`**, đúng bằng
trần. Với P1, đối chứng độc lập là **log JSON của chính các tiến trình máy chủ** (8 pid khác nhau
cùng phục vụ) và **header trần đọc từ máy chủ**, không chép từ tài liệu.

### 4.3 Đối chứng ÂM và DƯƠNG (bộ đo tự kiểm)

Bộ đo dựng một **bản đột biến** của `gioi_han`: giữ nguyên phần quyết định, chỉ thay lớp kho về đúng
khuôn cũ (bộ nhớ một tiến trình), rồi chạy ĐÚNG phép đo P1/P4 trên đó.

| Đối chứng | Nội dung | Kết quả sau khi vá |
|---|---|---|
| Âm (a) | bản đột biến qua N tiến trình **phải** ra 20·N | P2.1 = 20 · P2.2 = 40 · P2.4 = 80 · **P2.8 = 160** |
| Âm (b) | bản đột biến khởi động lại **phải** vượt được trần | P4.2: tiến trình B mới cho qua 1, bị chặn 0 |
| Dương | PHẦN B (đếm trong CSDL từ trước) **không** được nhân | P6: trần 150 ⇒ đặt được đúng 150 |
| Tự kiểm đầu | máy chủ tự nói trần và tự chặn đúng ở đó | P1.0: khai 20, cho qua 20, chặn ở lượt 21 |

Không có P2 và P4.2 thì P1 và P4.1 xanh **không nói lên điều gì**: một bộ đo luôn trả lời "đúng
trần" sẽ xanh ở mọi cây mã, kể cả cây còn lỗ hổng.

### 4.4 Hồi quy: các bộ thử cũ (chạy bằng lệnh thật, sau khi vá)

| Lệnh | Mã thoát | Ca | Ghi chú |
|---|---|---|---|
| `python3 app/thu/thu_gioi_han.py` | **0** | 34 (`Ran 34 tests`, `OK`) | trước khi vá: 0 · 34 ca · 0,072 giây |
| `python3 app/thu/thu_han_muc_nguyen_tu.py` | **0** | 5 | PHẦN B + bốn chốt nguyên tử |
| `python3 app/thu/thu_g18_maysrv.py` | 1 | 17 | **xem §4.5** — ca B_Tran::test_b6 |

### 4.5 SÁU BỘ THỬ ĐÃ ĐẠT NAY ĐỔI KẾT LUẬN (hệ quả tất yếu của việc vá)

Đây là phần quan trọng nhất của tài liệu này. Việc vá làm **sáu** bộ thử của G17/G18 chuyển từ ĐẠT
sang HỎNG. Mỗi bộ được đo **trước và sau** bằng lệnh thật:

| Bộ thử | Cây nền `6e61fc1` | Đã vá | Ca hỏng | Vì sao |
|---|---|---|---|---|
| `thu_g18_multiprocess.py` | exit 0 · 26 ca ĐẠT | exit 1 · 22 ĐẠT/4 HỎNG | P1.1·P1.2·P1.4·P1.8 | khẳng định `sum(cho qua) == N × khai báo` — tức khẳng định CHÍNH lỗ hổng |
| `thu_g18_maysrv.py` | exit 0 · `Ran 17` OK | exit 1 | `B_Tran::test_b6` (mệnh đề b) | đòi "KHÔNG có bảng nào trong CSDL giữ bộ đếm" |
| `thu_qa_g18_tich_hop.py` | exit 0 · `Ran 26` OK | exit 1 | `C_TranTanSuat::c3·c4·c5`, `D::d2` | C3–C5 khẳng định trần nhân theo số bản; D2 là đối chứng dương của một phép quét tĩnh, ghim vào tên `_lan`/`_chan_den` |
| `thu_postgres.py` | exit 0 | exit 1 | `I_DDLNguyenTuTruocSau::test_i3` | tripwire "bảng NGOÀI bộ DDL": danh sách 2 tên → 4 tên (thêm `gioi_han_luot`, `gioi_han_chan`) |
| `thu_g17_baomat.py` | exit 0 | exit 1 | `V_QuetCua::test_v4`, `Z_TongKet::test_z1` | ảnh chụp CSDL trước/sau lượt của tenant B thấy bảng `gioi_han_luot` có hàng mới, mà bảng đó không có cột chủ sở hữu ⇒ xếp loại `'KHONG_RO'` ⇒ báo "hàng của A bị đổi" |
| `thu_qa_g17.py` · `thu_qa_g18.py` | exit 0 (cây SẠCH) | exit 1 (cây BẨN) | `A_Nen::test_a1_cay_sach…` | chỉ vì ba tệp của lượt này chưa được commit — **không liên quan mã** |

Chi tiết ba nhóm:

1. **Ba bộ khẳng định lỗ hổng là đúng** (`thu_g18_multiprocess` P1, `thu_qa_g18_tich_hop` C3–C5):
   chúng viết `assertEqual(2 * http1, tong)` và "Bộ đếm nằm trong BỘ NHỚ tiến trình". Vá lỗ hổng thì
   chúng **phải** đỏ; giữ chúng xanh nghĩa là giữ lỗ hổng.
   `P1.1` còn đỏ vì bộ đo đó đọc trần bằng một máy chủ dùng-một-lần **trên chính cái nền sắp đo**
   rồi mở các bản mới — trước đây mỗi tiến trình mới có ngân sách mới, nay ngân sách nằm trong CSDL
   nên đã tiêu hết. Đó chính là bằng chứng lỗ hổng (b) đã đóng.
2. **Hai tripwire canh cái MỚI** (`thu_postgres` i3, `thu_g17_baomat` V4/Z1): chúng làm đúng việc
   được giao — kêu lên khi có bảng mới ngoài bộ DDL, và khi có bảng có hàng mà ảnh chụp không phân
   loại được chủ. Cả hai cần người sở hữu **khai báo** bảng mới (hoặc ra quyết định chính sách).
3. **Hai bộ canh CÂY SẠCH** (`thu_qa_g17`, `thu_qa_g18`): ba tệp của lượt này nằm trong worktree chưa
   commit. Đã đo nguyên nhân: `git status --porcelain -uall` chỉ có đúng ba tệp đó; ở cây nền SẠCH
   cả hai bộ thoát 0. Ghi chú: phiên này **không commit được** — sandbox từ chối ghi
   `.git/worktrees/…/index.lock` (`Operation not permitted`), nên việc commit thuộc về người gỡ.

`P1.4-rieng` của `thu_g18_multiprocess` (mỗi bản một CSDL riêng) vẫn ĐẠT sau khi vá — đúng như thiết
kế: **trần vẫn nhân khi các bản KHÔNG dùng chung CSDL** (xem §6).

### 4.6 Quét toàn dự án (`sh app/thu/chay_tat_ca.sh`, sau khi vá)

```
python:   1609 ca · 45 bộ chạy thật
frontend: 56 + 36 ca (hai tầng tự động)
E2E:      41/41 phép đo đạt
bộ hỏng:  thu_g17_baomat.py  thu_g18_maysrv.py  thu_g18_multiprocess.py  thu_postgres.py
          thu_qa_g17.py  thu_qa_g18_tich_hop.py  thu_qa_g18.py
EXIT=1
```

Đúng 7 bộ hỏng = 5 bộ ở nhóm 1–2 của §4.5 + 2 bộ canh cây sạch. Bộ mới `thu_g19_gioihan.py` được
bộ chạy chung đếm là **22 ca** và ĐẠT.

Ghi chú về "1631 ca/44 bộ" của lượt G18 đã nghiệm thu: lượt này **45 bộ** (thêm bộ mới) và số ca
lệch một phần vì `thu_g18_multiprocess.py` không còn in dòng `N ca — ĐẠT` mà in `26 ca — HỎNG` (bộ
chạy chung đếm ca bằng dòng `… ca — ĐẠT`). Đây là cách ĐẾM của bộ chạy, không phải mất ca.

---

## 5. Chi phí phải trả (đo, không suy đoán)

2.000 lượt `kiem("auth.dang_nhap", ip=<mỗi lượt một IP khác>, dinh_danh=None)` trên MỘT tiến trình,
CSDL tạm trong thư mục tạm; so kho CSDL (đã vá) với kho bộ nhớ (bản đột biến = đúng mã cũ):

| Lớp kho | 2.000 lượt | Mỗi lượt |
|---|---|---|
| `KhoCSDL` (đã vá) | 0,476 giây | **0,238 ms** |
| `_KhoBoNho` (khuôn cũ) | 0,008 giây | **0,0041 ms** |

≈58× chậm hơn, tức khoảng **+0,23 ms cho mỗi yêu cầu** đi qua giới hạn tần suất. Đọc kèm:
`thu_gioi_han.py` (34 ca, khoảng 700 lượt kiểm) mất 0,072 giây trước khi vá và 0,317 giây sau khi
vá. Đây là giá của việc trần đúng qua tiến trình VÀ sống qua khởi động lại; nếu cần nhanh hơn thì
chỗ đúng để đổi là Redis (xem §6), không phải quay lại bộ nhớ.

---

## 6. NGOÀI PHẠM VI — nói rõ cái CHƯA đo

1. **Nhiều MÁY / sau bộ cân bằng tải.** Kho dùng chung chỉ trong phạm vi MỘT CSDL. Nhiều máy, hoặc
   mỗi máy một CSDL, thì trần vẫn nhân theo số máy — `thu_g18_multiprocess` P1.4-rieng (mỗi bản một
   CSDL riêng) vẫn cho thấy đúng như vậy sau khi vá. Chỗ đó phải là Redis hoặc một CSDL chung;
   **CHƯA làm, CHƯA đo** ở lượt này.
2. **PostgreSQL / Redis.** D-8: CSDL nghiệp vụ vẫn SQLite; cụm PostgreSQL `:5432` là của dự án khác
   (`vip_customs*`) — CẤM đụng. Bộ đo của lượt này chỉ mở SQLite trong thư mục tạm (P0b đọc 16 byte
   đầu của `hub.db` = `SQLite format 3`) và gỡ `VIP_THU_POSTGRES` khỏi môi trường MỌI tiến trình con.
   (`thu_postgres.py` của dự án vẫn chạy trong bộ chạy chung theo mặc định của chính nó; nó dùng
   cụm tạm riêng và tự từ chối cổng 5432 — không phải do lượt này bật.)
3. **Tấn công phân tán nhiều IP** vẫn không chặn được; giới hạn này không thay WAF/gateway.
4. **Tải lớn.** Chưa đo số lượt/giây khi tranh chấp ghi nặng. Mỗi lượt kiểm nay là một giao dịch ghi
   (`BEGIN IMMEDIATE`) trên CSDL nghiệp vụ, nên trước khi chạy nhiều bản cần đo riêng: đây là câu
   hỏi THẬT, không phải chi tiết vụn.
5. **Hãng thật, mã trạng thái 110 (D-4), `CHO_PHEP_LIVE`.** Bộ đo KHÔNG mở `CHO_PHEP_LIVE` (P0c đọc
   thuộc tính lớp của cả ba adapter: vẫn `False`), không gọi ra mạng (chỉ `127.0.0.1` với cổng động
   do `bind(("127.0.0.1", 0))` chọn), không đoán mã 110.
6. **DDL chưa vào `csdl.SCHEMA`.** Hai bảng mới do `gioi_han` tự tạo, y như `han_muc_nhap_thang` của
   PHẦN B đang làm. Đây chính là thứ `thu_postgres::test_i3` kêu lên (§4.5) — xem §7.

---

## 7. Bàn giao — việc còn lại của người khác

1. **AG-00 (chủ `csdl.py` / `migrate.py`)**: đưa `DDL_GIOI_HAN` (2 bảng + 1 chỉ mục) vào
   `csdl.SCHEMA` hoặc một bước migration, như đã ghi cho `han_muc_nhap_thang`. Sau đó cập nhật danh
   sách trong `thu_postgres::test_i3` (2 tên → 4 tên) — ca đó đang kêu đúng chỗ.
2. **Chủ `app/thu/thu_g18_multiprocess.py`**: viết lại mục P1 — (a) đọc trần khai báo trên một nền
   RIÊNG (không tiêu ngân sách của nền sắp đo), (b) khẳng định trần DÙNG CHUNG thay vì khẳng định
   nhân. Giữ nguyên `P1.4-rieng` (nó vẫn đúng và vẫn có giá trị: phạm vi một CSDL).
3. **Chủ `app/thu/thu_g18_maysrv.py`**: mệnh đề (b) của `B_Tran::test_b6` ("không có bảng đếm dùng
   chung") nay SAI THEO THIẾT KẾ — cập nhật thành "kho đếm dùng chung nằm trong CSDL"; giữ mệnh đề
   (a) (trần đầy lại sau `xoa_het`) vì nó vẫn đúng.
4. **Chủ `app/thu/thu_qa_g18_tich_hop.py`**: `C_TranTanSuat::c3–c5` phải đổi kỳ vọng từ "trần × N"
   sang "trần dùng chung"; `D::d2` (đối chứng dương của phép quét tĩnh) phải trỏ vào một chỗ còn
   trạng thái mức mô-đun bị ghi (ví dụ `_da_tao_bang_gh` của `gioi_han`, hoặc `csdl._local`).
5. **Chủ `app/thu/thu_g17_baomat.py`**: khai báo `gioi_han_luot`/`gioi_han_chan` trong bản đồ chủ sở
   hữu của ảnh chụp CSDL (chúng là sổ hạ tầng của bộ giới hạn, không có cột tenant, không chứa dữ
   liệu nghiệp vụ). Đây cũng là một QUYẾT ĐỊNH CHÍNH SÁCH: chấp nhận sổ hạ tầng dùng chung trong
   CSDL nghiệp vụ hay không — người quyết định không phải lượt này.
6. **Commit**: ba tệp của lượt này nằm trong worktree, CHƯA commit (sandbox chặn ghi `.git`). Vân tay
   ở đầu tài liệu để đối chiếu khi merge.
7. **Việc lớn hơn (cần quyết định)**: nhiều máy ⇒ Redis/CSDL chung. Chưa nằm trong lượt này.
8. **Quan sát ngoài phạm vi (chưa sửa)**: `app/server.py:461` gọi
   `dat_lai(..., ip=self.client_address[0])` — địa chỉ TCP thô, trong khi `_gioi_han` dùng
   `dia_chi_that(...)` (đã đi qua luật trusted proxy). Khi `PROXY_TIN_CAY` khác rỗng thì khoá của
   `dat_lai` LỆCH khoá của `kiem` ⇒ lượt đăng nhập thành công không xoá được bộ đếm. Tệp của
   AG-00/AG-01, chưa sửa ở lượt này.
9. **Quan sát về vệ sinh bộ thử (không liên quan mã của lượt này)**: `app/du-lieu/khoa-noi-bo.key`
   (đã bị `.gitignore`, là khoá nội bộ sinh tự động) XUẤT HIỆN trong lượt chạy bộ thử chung của lượt
   này. Đã đo để loại trừ: (a) bộ đo mới **không** tạo nó — chuyển tệp đi rồi chạy lại trọn bộ đo,
   `app/du-lieu/` vẫn rỗng; (b) `thu_postgres.py` cũng không tạo lại nó. Tức là có ít nhất một bộ
   thử trong dự án chạy tiến trình con **không** đặt `VIP_HUB_DATA` và ghi vào thư mục dữ liệu mặc
   định. Không phải việc của lượt này, nhưng nên có người rà: một bộ thử ghi khoá vào thư mục dữ
   liệu thật là chuyện đáng sửa trước khi có dữ liệu thật trong đó.

---

## 8. Phụ lục — bộ đo mới có gì

`app/thu/thu_g19_gioihan.py` (mới, 22 ca khi mọi thứ ĐẠT). Chạy: `python3 app/thu/thu_g19_gioihan.py`.
Mã thoát: `0` mọi ca ĐẠT · `1` có ca HỎNG · `9` chốt an toàn từ chối (dữ liệu thật).

| Mục | Nội dung | Số ca |
|---|---|---|
| P0 | Chốt an toàn: nền tạm · `hub.db` là SQLite · `CHO_PHEP_LIVE` vẫn False · bind `127.0.0.1` | 4 |
| P1 | Trần qua N = 1·2·4·8 tiến trình máy chủ THẬT, cùng một CSDL (lỗ hổng a) | 5 |
| P2 | **Đối chứng âm**: chạy đúng P1 trên bản đột biến (kho bộ nhớ) ⇒ phải ra 20·N | 4 |
| P3 | Nguyên tử không qua HTTP: 8 tiến trình đua một khoá, 3 vòng, có hàng rào thời gian | 1 |
| P4 | Khởi động lại: tiêu hết trần → tắt tiến trình → tiến trình mới (và máy chủ HTTP mới) phải bị chặn (lỗ hổng b) + đối chứng âm | 3 |
| P5 | Bất biến cũ qua tiến trình: "kiểm hết rồi mới ghi" + `dat_lai` dùng chung | 2 |
| P6 | Đối chứng dương: PHẦN B (đếm trong CSDL) không nhân theo số bản | 1 |
| P7 | Hồi quy: chạy lại hai bộ thử cũ bằng lệnh thật, đòi mã thoát 0 | 2 |
| P8 | Tổng kết + danh sách lệnh thật kèm mã thoát thật | (không tính ca) |

Quy ước an toàn của bộ đo (đã cài trong MÃ, không chỉ trong tài liệu): mọi tiến trình con **tự chối
chạy** nếu `cau_hinh.DUONG_DAN_CSDL` nằm ngoài thư mục tạm (mã thoát 9); máy chủ luôn được đặt
`VIP_HUB_BIND=127.0.0.1`; cổng lấy từ `bind(("127.0.0.1", 0))`; `VIP_THU_POSTGRES` bị gỡ khỏi môi
trường mọi tiến trình con; tắt tiến trình theo ĐÚNG PID (không `pkill`/`killall`).
