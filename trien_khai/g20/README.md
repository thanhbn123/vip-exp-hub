# G20/AG-03 — HARNESS HỢP ĐỒNG LỚP HTTP

Một chỗ chạy **HẾT** năm harness con của lớp HTTP, gom kết quả về **MỘT bảng**, và nói rõ:

* chặng nào **CHẠY ĐƯỢC**
* chặng nào **KHÔNG CHẠY ĐƯỢC** (kèm ĐÚNG chốt an toàn còn thiếu)
* chặng nào **BLOCKED** (kèm ĐÚNG mã giấy phép còn thiếu — **không bao giờ tính là đạt**)
* chặng nào **HỎNG** (đã chạy nhưng vi phạm khai báo của hợp đồng)

## Chạy

```sh
sh trien_khai/g20/chay_tat_ca.sh                 # cả ba tầng, ~60–90 giây
sh trien_khai/g20/chay_tat_ca.sh --khong-chay    # chỉ phán hợp đồng, không thực thi
python3 trien_khai/g20/chay_hop_dong.py --danh-sach
python3 trien_khai/g20/chay_hop_dong.py --chi-chang G19
python3 trien_khai/g20/chot_an_toan.py --tu-kiem
python3 trien_khai/g20/tiem_loi.py
python3 app/thu/thu_g20_hop_dong.py
```

## Ba tầng, và vì sao tầng nào cũng cần

| Tầng | Tệp | Trả lời câu |
|---|---|---|
| 1 | `chot_an_toan.py --tu-kiem` | Bộ dò chốt an toàn có **phân biệt được** cấu hình an toàn với cấu hình nguy hiểm không? |
| 2 | `tiem_loi.py` | Bộ phán có **ĐỎ ĐƯỢC** không, khi tiêm lỗi vào một bản sao hợp đồng? |
| 3 | `chay_hop_dong.py` | Hợp đồng lớp HTTP **đang giữ được gì, đang hở gì**? |

Tầng 1 và 2 là điều kiện của tầng 3. Một harness luôn in "ĐẠT" thì dòng "ĐẠT" ấy không có
nghĩa; một harness đỏ vì lời cảnh báo của chính nó thì cũng không.

## Tệp

| Tệp | Việc |
|---|---|
| `hop_dong.json` | **Hợp đồng** — dữ liệu máy đọc được: 13 chặng, điều kiện chạy, kết quả mong đợi |
| `chot_an_toan.py` | Bảy chốt an toàn + bộ tự kiểm 17 cấu hình tổng hợp |
| `chay_hop_dong.py` | Bộ điều phối: phán từng chặng, in một bảng, ghi báo cáo gom |
| `tiem_loi.py` | 14 phép tiêm lỗi vào bản sao hợp đồng (có đối chứng dương P0) |
| `gia_lap_chang.py` | Chặng giả lập dùng cho các phép tiêm |
| `chay_tat_ca.sh` | Chạy cả ba tầng; tự chuẩn hoá `GIT_CONFIG_*`; dọn theo ĐÚNG PID |
| `app/thu/thu_g20_hop_dong.py` | 36 ca thử cho chính harness này |

## An toàn

* **Không gọi API hãng, kể cả sandbox** — `V-G09-01` + `V-13906-05` CHƯA CẤP. Mọi phép đo lớp
  HTTP đi qua loopback, cổng do hệ điều hành cấp (`bind` cổng 0).
* **Không push, không deploy, không tunnel, không mở cổng ra ngoài.**
* `CHO_PHEP_LIVE=False`; chốt `D-9` (`city`/`area`) giữ CHẶN CỨNG; **không đoán** mã trạng thái
  hãng (`D-4`) — mã chưa xác minh ⇒ `NEEDS_REVIEW`.
* CSDL nghiệp vụ **vẫn là SQLite** (`D-8`). PostgreSQL chỉ dùng cho **CỤM RIÊNG** của phép đo
  G18/AG-06, **CẤM cổng 5432** (cụm hệ thống đang giữ `vip_customs*`).
* **Mọi lượt dọn theo ĐÚNG PID.** Chốt `N6` soi chính mã của làn này (bằng AST với Python,
  bằng bộ lọc chú thích/chuỗi với shell) và **TỪ CHỐI CHẠY** nếu tìm thấy lệnh giết theo tên.
* Mỗi lượt dựng một **nền TẠM riêng** (`os.makedirs` không `exist_ok` ⇒ giành nền là nguyên tử),
  nên hai làn chạy song song không giẫm lên dữ liệu của nhau.

## Kết quả lượt này

13 chặng: **4 CHẠY ĐƯỢC · 0 KHÔNG CHẠY ĐƯỢC · 8 BLOCKED · 1 HỎNG** (G18).

Chặng `G18` hỏng vì một **lỗi thật, đã đo được và đã truy nguyên**: G19/AG-02 (`f04de21`)
chuyển kho đếm tần suất từ bộ nhớ tiến trình sang bảng CSDL dùng chung, còn
`trien_khai/g18/harness_tai.py` (`8d58117`) viết trước đó vẫn tưởng `gioi_han.xoa_het()` chỉ
xoá bộ nhớ của chính nó. Chi tiết + đối chứng đường: `docs/G20_CONTRACT_HARNESS.md`.
