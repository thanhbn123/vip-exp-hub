# `trien_khai/g19/` — BỘ TRÍCH ROUTE **THỨ BA** + PHÉP ĐO CÁCH LY TENANT (G19, làn AG-04)

Đóng khoảng trống mà lượt nghiệm thu G18 đo được (`docs/QA_G18_INTEGRATED.md` dòng 223-259):
hai dụng cụ đo V5 (cách ly tenant) **ĐỒNG Ý ở 73 route** và **lệch PHẠM VI ở 31 route** —
AG-06 phủ **104** route, AG-01 phủ **73**. Nghĩa là **31 route chưa từng được đo cách ly tenant**.

Báo cáo đầy đủ: **`docs/G19_ROUTE_COVERAGE.md`**. Bộ ca: **`app/thu/thu_g19_route.py`** (49 ca).

| Tệp | Việc |
|---|---|
| `bot_route_thi_hanh.py` | **Bộ trích route thứ ba.** Nguyên lý **THI HÀNH**: không gian ứng viên moi từ **hằng số đã biên dịch** (`co_consts` của `server.py`), rồi quyết định "có route hay không" bằng **phản hồi THẬT** của máy chủ đang chạy. Khác AG-06 (`ast.parse` + bảng cửa khai tay) và khác AG-01 (`re` trên từng dòng nguồn). Kèm 4 hàm ĐỘT BIẾN chạy trên **bản sao** trong thư mục tạm |
| `may_chu_do.py` | **Máy chủ đo** trong tiến trình riêng, CSDL tạm riêng, bind `127.0.0.1` **cổng 0**. Hai chế độ: `liet-ke` (phân loại từng lượt `đường × phương thức`) và `cach-ly` (dựng dữ liệu A/B có ĐÁNH DẤU rồi đo). Ghi lại **mọi** `socket.connect()` để khẳng định 0 lượt ra ngoài loopback |
| `chay_g19.sh` | Bộ chạy: bộ trích → bộ hồi quy 49 ca, **in exit code trước mọi pipe** |

```bash
sh trien_khai/g19/chay_g19.sh                 # chạy đầy đủ
sh trien_khai/g19/chay_g19.sh --chi-liet-ke   # chỉ chạy bộ trích
python3 trien_khai/g19/bot_route_thi_hanh.py  # bộ trích, in số liệu + ghi JSON
python3 app/thu/thu_g19_route.py              # 49 ca (unittest)
python3 app/thu/thu_g19_route.py --do         # chỉ ĐO, in JSON thô để soi
```

## Vì sao cần bộ trích THỨ BA

Hai bộ đã có dùng chung một giả định: *"route là thứ đọc được từ mã nguồn"*. Bộ này bỏ giả định
đó và đổi câu hỏi thành: **route nào máy chủ ĐANG CHẠY thật sự phục vụ?**

```
BỘ THỨ BA = (không gian ứng viên từ HẰNG SỐ ĐÃ BIÊN DỊCH)  ∩  (PHÂN LOẠI BẰNG THI HÀNH)
```

Phân loại bám vào **ĐÚNG CÂU CHỮ** của nhánh rơi cuối router (`{"loi": "không có đường này"}`),
không bám vào mã HTTP — vì một route CÓ vẫn trả 404 (`{"loi": "không có đơn này"}` khi id không
tồn tại), và hai câu đó khác nhau.

## Bốn đột biến chứng minh bộ trích CÓ RĂNG

| Đột biến | Kỳ vọng | Vì sao quan trọng |
|---|---|---|
| Tiêm **route giả** vào bản sao | bộ trích **PHẢI thấy**, và lượt HTTP của nó phải trả **200 đúng thân đã tiêm** | "thấy" phải là thấy một route chạy được, không phải thấy một cái tên |
| Tiêm chuỗi vào **chú thích** `#` | **KHÔNG** được vào không gian ứng viên | chứng minh tầng tĩnh đọc **bảng hằng số**, không `grep` văn bản |
| Tiêm **hằng số chuỗi THẬT** | tầng tĩnh **NHẬN**, tầng thi hành **LOẠI** (404 nhánh rơi) | chứng minh tầng thi hành có răng, không phải vật trang trí |
| **Xoá** một route thật | phải **MẤT ĐÚNG** route đó | chứng minh không đọc danh sách ghim cứng |

Thêm một đột biến cho **bộ đo cách ly**: bỏ `WHERE tenant_id=?` khỏi truy vấn `/api/v2/audit`
⇒ phép đo cách ly **PHẢI ĐỎ**. Không có ca này thì mọi ca xanh đều vô nghĩa — một bộ đo không
thể đỏ là bộ đo không đo.

## Nguyên tắc của phép đo cách ly

Mỗi mục phải có **HAI** vế, thiếu vế thứ hai thì "B không thấy dữ liệu A" chỉ có thể là vì
B chẳng nhận được gì:

1. **ĐỐI CHỨNG DƯƠNG** — chính route đó với **chủ sở hữu hợp lệ** phải trả 200 kèm dữ liệu
   **CỦA CHÍNH MÌNH** (dấu `canary_a`). Không đạt ⇒ ghi thẳng **CHƯA ĐO**, không tính là đạt.
2. **ĐỐI CHỨNG ĐƯỜNG** — lượt của tenant B phải mang dữ liệu **CỦA B** (`canary_b`).
3. **PHỦ ĐỊNH** — thân phản hồi của B **KHÔNG** được chứa `canary_a`.

Hai kiểu đường được đo khác nhau, và nói rõ ra:

* **tenant** — đường theo phiên: A thấy dấu A, B thấy dấu B.
* **toan_cuc** — danh mục toàn cục / dữ liệu tiến trình (`/hang`, `/goi`, `/g09/*`, `/suc-khoe`,
  `/san-sang`): hai tenant phải nhận **GIỐNG NHAU** và **KHÔNG** lượt nào được chứa dấu tenant.

## Ràng buộc đã giữ

* **Không gọi hãng kể cả sandbox** — máy chủ đo bind `127.0.0.1` cổng `0`; lưới `_gac_mang()`
  ghi mọi lượt `socket.connect()` và ca **A4/C0** khẳng định **0 lượt ra ngoài loopback**.
* **Không push / deploy / tunnel / mở cổng**; không `.env`; không credential thật (mật khẩu
  trong CSDL TẠM là chuỗi thử).
* **Không sửa `app/`** — mọi đột biến chạy trên **bản sao** trong thư mục tạm; `git status` chỉ
  thấy các tệp mới của làn này.
* **Không chuyển sang PostgreSQL**, không đụng cụm `:5432`; nghiệp vụ vẫn SQLite.
* **Không đoán mã trạng thái 110 (D-4)**: `/api/v2/g09/can-soat` chỉ được khẳng định là *dữ liệu
  có mặt và giống nhau ở hai tenant*, không phán quyết nghĩa của mã.

## Giới hạn đã đo (nói thẳng)

Không gian ứng viên chỉ đầy đủ nếu mọi route được so bằng một hằng số **có mặt trong mã đã biên
dịch**. Route dựng bằng f-string rồi so sẽ bị bỏ sót — hiện `app/server.py` không có chỗ nào như
vậy (f-string `/api/v2` duy nhất, dòng 849, là để **dựng URL** trả cho khách, không phải để so).
Đây là giả định **được khai**, không phải điều được chứng minh.

Ở cấp **(đường, phương thức)** bộ này lệch AG-06 đúng 8 cặp, và **hai bên đều có phần sai**:
bộ này thừa 1 cặp (`DELETE /api/v2/platform/tenants/{id}` — `_can` chạy TRƯỚC khi kiểm phương
thức nên trả 403), AG-06 thừa 7 cặp (4 thuộc đường không phải route `/api/v2/platform/`, 3 thuộc
`/api/v2/webhook/nhan/{ma}` vốn chỉ nhận POST). Vì thế **mọi khẳng định độ phủ ở cấp ĐƯỜNG**,
không ở cấp phương thức. Chi tiết: `docs/G19_ROUTE_COVERAGE.md` §4.
