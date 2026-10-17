# G21 / AG-04 — CỔNG ĐỐI CHIẾU ĐỘC LẬP: GIỚI HẠN TẦN SUẤT QUA TIẾN TRÌNH

Thư mục này là **làn triển khai** của một phép đo, không phải của một tính năng. Nó không chứa
mã chạy production; nó chứa **cách chạy lại** phép đo.

## Vì sao có làn này

Nghiệm thu G20 của AG-01 (`docs/QA_G20.md`, cổng **C5**) kết luận: con số **"1733 ca · 47 bộ"**
mà mọi báo cáo trích dẫn **không chứa một cổng đối chiếu độc lập nào**. Ba bộ của từng làn
(`thu_g19_gioihan.py` 22 ca · `thu_g19_route.py` 49 ca · `thu_g19_vtp.py` 31 ca) **có** chạy —
nhưng chúng do **chính người viết mã** viết, nên chúng là **bản tự khai**, không phải một phép đo
thứ hai.

Làn này đóng phần **giới hạn tần suất** của khoảng trống đó bằng **một bộ đo thứ hai**, viết bởi
một làn khác, đo bằng **cách khác**, và **tự chứng minh nó có răng**.

## Chạy

```sh
sh trien_khai/g21-gioihan/chay.sh
```

Script in `EXIT_BO_DO=<mã>` **trước mọi pipe**, rồi in **bảng N / tổng lượt qua / trần khai báo**
lấy nguyên văn từ log. Log đầy đủ nằm ở `${TMPDIR}/veh_g21_ag04/gioihan.log` — **cố ý KHÔNG nằm
trong cây mã nguồn**: một tệp log trong repo làm cây BẨN và sẽ đánh đỏ các cổng "cây sạch" của
`thu_qa_g17.py` / `thu_qa_g18.py` vì một lý do không liên quan tới sản phẩm.

Chạy thẳng bộ đo cũng được (cùng mã thoát):

```sh
python3 app/thu/thu_g21_gioihan.py     # 0 = mọi ca ĐẠT · 1 = có ca HỎNG/KHUYẾT · 9 = chốt an toàn
```

## Bộ tổng hợp — nối phép đo vào bộ chạy chung, và TỰ CHỨNG MINH nó đo được

Một phép đo **không tự vào bảng tổng kết**: `app/thu/chay_tat_ca.sh` chỉ ghi nhận một bộ thử khi
bộ đó thoát 0, **có dấu vết đã chạy ca** (`^OK` hoặc `ca — ĐẠT`) và **đếm được số ca > 0**.
`app/thu/thu_g19_tich_hop.py` là bộ tổng hợp làm việc đó: nó gọi runner này và **trả về ĐÚNG mã
thoát của runner** (chỉ siết thêm ở đúng một chỗ: runner thoát 0 mà **0 ca đo thật** thì cổng ĐỎ,
vì đó là xanh giả).

```sh
python3 app/thu/thu_g19_tich_hop.py
# PHẦN 1/2: tự kiểm cổng — TIÊM LỖI THẬT vào bản sao của runner (a/b/c/d + hai đối chứng dương)
# PHẦN 2/2: chạy runner thật, in bảng bằng chứng hai kênh, thoát bằng mã thoát của runner
```

Bốn ca tiêm lỗi (mã thoát in ra là mã thoát **thật** của tiến trình):

| Ca | Lỗi được tiêm vào **bản sao** của `chay.sh` | Cổng phải ra |
|---|---|---|
| (a) | bộ đo bị gọi sai đường dẫn ⇒ runner thoát **2** | ĐỎ |
| (b) | runner **không tồn tại** / là thư mục | ĐỎ + nói rõ "KHÔNG CHẠY ĐƯỢC" |
| (c) | suite `unittest` **RỖNG** ⇒ `Ran 0 tests` + `OK`, thoát **0** | ĐỎ (0 ca không phải là đạt) |
| (d) | thoát 0 nhưng **mọi ca BỎ QUA** (`TỔNG=5`) | ĐỎ (0 ca ĐO THẬT) |

Bản sao nằm **cùng thư mục** với runner (khác thư mục thì `dirname $0/../..` trỏ sai gốc cây ⇒ nó
hỏng vì đường dẫn chứ không phải vì lỗi được tiêm), bị xoá ngay sau mỗi ca, và mỗi ca còn khẳng
định bản sao **khác bản gốc ĐÚNG MỘT DÒNG**. Chi tiết + bằng chứng: `docs/G21_GIOIHAN.md` §12.

## Ba chốt an toàn (đo lại bằng máy, không nói suông)

| Chốt | Cách bộ đo tự kiểm |
|---|---|
| **KHÔNG gọi hãng, kể cả sandbox** (`V-G09-01` + `V-13906-05` CHƯA CẤP) | Mọi HTTP chỉ chạm `127.0.0.1` cổng do hệ điều hành cấp. Phần `408` dùng **stub J&T cục bộ của dự án** (`app/thu/stub_jt.py`), thứ tự chặn mọi `host` khác `127.0.0.1`/`localhost` |
| **KHÔNG push / deploy / tunnel / mở cổng** | `VIP_HUB_BIND=127.0.0.1` đặt **tường minh** cho MỌI tiến trình con (không trông cậy giá trị mặc định — một biến thừa hưởng có thể mở cổng ra ngoài); cổng lấy từ `bind(('127.0.0.1', 0))` |
| **KHÔNG PostgreSQL (D-8)** | CSDL của mọi nền đo là SQLite trong thư mục **TẠM** (A0b đọc 16 byte đầu); `VIP_THU_POSTGRES` bị **gỡ** khỏi môi trường mọi tiến trình con; **không** mở kết nối nào tới `:5432` |

Thêm: **KHÔNG mở `CHO_PHEP_LIVE`** (A0c đọc thẳng thuộc tính lớp của ba adapter trong một tiến
trình con), **KHÔNG credentials thật / `.env`** (bí mật trong bộ đo là chuỗi GIẢ có hậu tố `GIA`),
**KHÔNG đoán mã trạng thái hãng (D-4)**, **KHÔNG chạm ánh xạ `area`** (giữ chốt `D-9`).
Tắt tiến trình theo **ĐÚNG PID** (không `pkill`/`killall`) và dọn thư mục tạm khi kết thúc.

## Bộ đo gồm những gì

Xem docstring đầu `app/thu/thu_g21_gioihan.py` để có bảng đầy đủ. Tóm tắt:

| Phần | Đo cái gì |
|---|---|
| `A0` | Chốt an toàn + **đối chứng dương cho chính luật phán** của bộ đo |
| `A1` | Trần **khai báo**, đọc từ chính máy chủ: `ip` = 20 · `dinh_danh` = 12 · cùng cửa sổ 300 giây |
| `A2` | **CHIỀU 1**: N = 1·2·4·8 bản **chung một CSDL** ⇒ TỔNG = **đúng** trần (không nhân) |
| `A3` | **KÊNH ĐỘC LẬP**: đếm thẳng `gioi_han_luot` bằng `sqlite3`, đối chiếu với số qua HTTP |
| `A4` | **CHIỀU 2**: N bản **mỗi bản một CSDL** ⇒ TỔNG = N × trần (đối chứng DƯƠNG của A2) |
| `A5` | **TỰ KIỂM**: bản đột biến quay lại *kho bộ nhớ một tiến trình* ⇒ bộ đo **PHẢI ĐỎ** |
| `A6` | **CỬA SỔ TRƯỢT**: đẩy mốc **từng dòng** ⇒ nhả đúng phần đã trôi; `Retry-After` theo dòng cũ nhất |
| `A7` | **KHỞI ĐỘNG LẠI**: tiến trình mới trên CSDL cũ vẫn bị chặn (+ đối chứng dương: CSDL mới thì qua) |
| `A8` | Hình dạng **429**: `Retry-After` · `X-RateLimit-*` · `chieu` |
| `A9` | **`408` → `timeout=True`** (`docs/SHARED_CONTRACTS.md` §42) qua stub loopback |
| `A10` | Hồi quy: ba bộ thử giới hạn của dự án, chạy bằng **lệnh thật + mã thoát thật** |
| `A11` | **SỔ ĐỐI CHỨNG**: mọi nhóm ca ÂM phải có ca DƯƠNG; sổ tự kiểm chính nó |

## Phạm vi — nói rõ cái NẰM NGOÀI

Đo: N tiến trình trên **MỘT máy**, loopback, SQLite WAL trong thư mục tạm. **KHÔNG** đo: nhiều MÁY
hoặc sau bộ cân bằng tải (mỗi máy một CSDL ⇒ trần **vẫn** nhân — chính `app/gioi_han.py` dòng 42-43
tự khai điều này; chỗ đó cần Redis hoặc một CSDL chung) · tấn công phân tán nhiều IP · tải lớn ·
PostgreSQL/Redis. Bộ đo **không sửa một dòng mã sản phẩm nào**; bản đột biến ở `A5` sống trong thư
mục tạm và bị xoá khi kết thúc.

---

# G22 / AG-04 — ĐIỂM VƯỚNG **TÊN TỆP** CỦA CỔNG C5/G7

Cùng một làn, lượt tiếp theo. Lượt G21 để lại một điểm vướng **ownership** chưa gỡ: cổng `C5`
(`app/thu/thu_qa_g20.py`, AG-01) và `G7` (`app/thu/thu_qa_g21.py`) **đếm theo KHUÔN TÊN**
`re.match(r"thu_qa_g19.*\.py$", os.listdir(app/thu))`. Bộ tổng hợp thật của làn này tên
`app/thu/thu_g19_tich_hop.py` nên **không bao giờ** lọt vào danh sách đó ⇒ C5 đo `0/1` dù bộ tổng
hợp chạy thật và xanh. Đây là **lỗi đặt tên**, không phải lỗi sản phẩm.

Lượt này AG-00 cấp tường minh `app/thu/thu_qa_g19_tich_hop.py` cho AG-04 — một **bản uỷ quyền
MỎNG**: nó chạy bộ gốc và trả về **ĐÚNG mã thoát** của bộ gốc, **không** chứa bản logic thứ hai.

## Chạy

```sh
sh trien_khai/g21-gioihan/chay_g22.sh      # log ra ${TMPDIR}/veh_g22_ag04/, in mã thoát trước mọi pipe
python3 app/thu/thu_g22_gioihan.py         # 0 = ĐẠT · 1 = có HỎNG/KHUYẾT · 9 = chốt an toàn
```

## Cổng này đo gì

| Mã | Việc |
|---|---|
| `B0` | **CHỐT AN TOÀN**: không push / không tunnel / không mở `CHO_PHEP_LIVE` / không chạm `:5432`; `VIP_THU_POSTGRES` bị GỠ khỏi tiến trình con (D-8) |
| `B1` | **BỘ ĐẾM THẬT CỦA C5/G7** — đọc từ mã nguồn AG-01 rồi chạy trên `app/thu` thật |
| `B2` | **CHIỀU XANH** — gọi **CHÍNH** phương thức C5 ⇒ phải ra `1/2 · DONG` |
| `B3` | **CHIỀU ĐỎ** — tiêm lỗi **một dòng** vào BẢN SAO của bản uỷ quyền, đo **qua chính C5** |
| `B4` | **LỖ HỔNG ĐO ĐƯỢC** của C5: bỏ qua ở mức PHƯƠNG THỨC ⇒ C5 vẫn XANH dù 0 ca chạy (`N-G22-01`) |
| `B5` | **KHUÔN BÁO CÁO** — bộ đếm lấy dòng `Ran N` CUỐI; đo bằng một cái bẫy + đối chứng dương |
| `B6` | **SỔ ĐỐI CHỨNG** + tổng kết (mọi nhóm ÂM phải có DƯƠNG) |

## Kết quả lượt này

`ca ĐẠT=15 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=1 · TỔNG=16` · **exit 1** — chỗ KHUYẾT là **lỗ hổng của
C5** (`N-G22-01`), không phải của bản uỷ quyền. Chi tiết + bản vá đề xuất: `docs/G22_GIOIHAN.md`.

## Phạm vi — nói rõ cái NẰM NGOÀI

Cổng này **không mở socket nào**: nó chỉ ĐỌC tệp và chạy tiến trình con cục bộ. Hai tệp được mượn
tạm (`app/thu/thu_qa_g20.py` chép từ worktree AG-01, và bản sao tiêm lỗi của bản uỷ quyền) đều
được **trả lại / xoá** trong `finally` + `atexit`, kèm đối chiếu **sha256**.

---

## Lượt AG-04 mới (G22) — khối `B7`: HỢP ĐỒNG TENANT · PHỦ TUYẾN · PHÂN TRANG

Lượt trước đóng điểm vướng **tên tệp** của C5/G7. Lượt này đo **hợp đồng đóng băng §1 của AG-02**
(`docs/G22_TRUYVAN.md`) trên **fixture SQLite TẠM** với **hai tenant A/B** — và **bác bỏ**
`assertIn(200, 400)`: một điều kiện nhận cả hai mã thì không phân biệt được *từ chối tường minh*
với *bỏ qua im lặng*, mà vế thứ hai đúng là dạng hỏng cả nhiệm vụ G12 sinh ra để diệt.

```sh
sh trien_khai/g21-gioihan/chay_hopdong.sh    # HAI CÂY: cây nhà (ÂM) + cây AG-02 (DƯƠNG)
python3 app/thu/thu_g22_gioihan.py           # đầy đủ B0…B7 trên cây này
```

`chay_hopdong.sh` là **đối chứng ÂM/DƯƠNG của chính phép đo**: cây nhà **chưa** gộp tuyến
`/api/v2/don` của AG-02 nên các **ghim hợp đồng PHẢI ĐỎ** (`exit 1`); cây AG-02 (tuyến đã cắm)
**PHẢI XANH** (`exit 0`). Runner chỉ thoát `0` khi cặp kết quả đúng như vậy — một cây đối chứng đỏ
nghĩa là phép đo sai **hoặc** hợp đồng bị vi phạm, cả hai đều phải đỏ.

| Mã | Việc |
|---|---|
| `B7a` | **CHỐT AN TOÀN**: CSDL đo nằm trong thư mục `tempfile`; **TỪ CHỐI ĐO (mã thoát 9)** nếu không |
| `B7b` | Nền: hai tenant A/B, 60 đơn ở A + 1 đơn ở B, dựng bằng **chính `don_hang.tao_don`** |
| `B7c` | **ĐỐI CHỨNG DƯƠNG**: A đọc dữ liệu A ⇒ **đúng `200`** + đúng bảng khoá §1.5 + trang mặc định **50** |
| `B7d`·`B7e` | Phân trang: mặc định **50** · trần **500 bị KẸP** (không 400) · **trang 2 RỜI trang 1** |
| `B7f` | Tham số sai ⇒ **đúng `400`** (4 vế âm) + tham số hợp lệ ⇒ `200` (vế dương) |
| `B7g`·`B7h` | **CROSS-TENANT**: B gửi `tenant_id=<A>` ⇒ **đúng `400`**; B lọc `ma_don`/`q` của A ⇒ `200` nhưng thân **RỖNG** (kiểm **cả thân**, không chỉ mã) |
| `B7i`·`B7j`·`B7k` | **ĐỐI CHỨNG DƯƠNG của từng vế âm**: chính A lọc cùng tham số ⇒ thấy đúng đơn của mình |
| `B7l` | Vô danh ⇒ **đúng `401`** (§1.4) |
| `B7m`·`B7p` | Hình dạng `truy_van.chay()` khớp §1.5 (10 khoá) · `loc-mo-ta` **bằng đẳng thức** với `mo_ta_bo_loc()` |
| `B7n` | **PHỦ TUYẾN**: mọi tuyến `/api/v2/don*` dò bằng HTTP thật với **bộ đếm trong tiến trình máy chủ** |
| `B7o` | **D-8**: CSDL nghiệp vụ không đổi (`sha256` · `mtime` · cỡ y nguyên) |

Kết quả lượt này (HEAD `4431430` + 2 tệp chưa commit): cây nhà **`exit 1` · 32 ca · ĐẠT=22 ·
HỎNG=8 · BỎ QUA=0 · KHUYẾT=2**; cây đối chứng AG-02 **`exit 0` · 20 ca · ĐẠT=19 · HỎNG=0 ·
BỎ QUA=1 · KHUYẾT=0**. Phát hiện + bảng đầy đủ: `docs/G22_GIOIHAN.md` §8.

**Phạm vi:** CSDL đo là SQLite TẠM (không migration CSDL nghiệp vụ — **D-8**); máy chủ đo bind
`127.0.0.1` cổng 0; KHÔNG hãng kể cả sandbox, KHÔNG push/deploy/tunnel, KHÔNG credentials thật.
Cây đối chứng được đo **CHỈ ĐỌC** (`PYTHONDONTWRITEBYTECODE=1`) — không rơi `__pycache__` sang cây
khác, và thư mục tạm bị xoá trong `finally`.
