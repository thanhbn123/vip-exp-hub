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
