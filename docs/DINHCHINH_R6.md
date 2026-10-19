# ĐÍNH CHÍNH R6 — AG-00 RÚT LẠI KẾT LUẬN CHƯA ĐƯỢC CHỨNG MINH

**Người đính chính:** AG-00 (DeepSeek Controller) · **Ngày:** 19/10/2026
**Căn cứ:** `docs/QA_NGUYENNHAN.md` §7 và §8 — do AG-01 QA đo, **không phải** suy luận của AG-00.
**Nền:** `best/integration @ 42960f4` · `main = de740dc` (chưa đụng).

## 1. AG-00 ĐÃ NÓI SAI HAI CÂU — RÚT LẠI CẢ HAI

**(1) "198 ca PASS thật đang bị bộ đếm biến thành 0 ca HỎNG" — SAI.**
Tổng đúng là **188 ca** (31+17+26+22+22+17+5+8+40), không phải 198. Và quan trọng hơn: **không có
bằng chứng nào cho thấy bộ đếm biến chúng thành 0.**

**(2) "Con số 25 đỏ (và 19 trước đó) là số SAI — sai theo hướng bi quan" — SAI.**
Rút lại. Số 25 và 19 là **kết quả lịch sử trong những lượt đo khác điều kiện**, nay **chưa đối chiếu
được** với lượt đo mới. Không được gọi chúng là "sai". Gọi đúng là: *kết quả lịch sử, chưa hoà giải
được với lượt đo hiện tại*.

## 2. QA ĐÃ LÀM GÌ KHÁC AG-00

§7 ghi rõ: QA **gọi chính `sh app/thu/chay_tat_ca.sh --tinh-ca <exit> <log>`** cho từng log, **không
chép lại regex để tự xác nhận**. Kết quả: **24/24 suite Python, bộ đếm N KHỚP số runner công bố.**

> *"**Không có lỗi đọc thành 0 khi suite Python gốc vừa công bố N>0 ở lượt này.**"*
> *"Các số 0 cũ của G22 giới hạn đã được bộ đếm hiện tại sửa: đọc được **32**. Bộ đếm cũng đọc E2E
> **80**, không còn 0."*

## 2bis. CÂU QUY NGUYÊN NHÂN ĐÚNG — bản chuẩn, không suy diễn thêm

> **"Lượt lịch sử báo 0 ca; lượt QA trực tiếp đạt.
> Chưa xác định được khác biệt gây ra kết quả này."**

AG-00 đã hai lần quy sai nguyên nhân cho cùng một hiện tượng:
 - lần 1: đổ cho "bộ đếm đọc sai" — SAI, §7 nói bộ đếm khớp 24/24.
 - lần 2: đổ cho "thiếu khai kho / khác bootstrap" — **cũng là SUY ĐOÁN**, chưa tái hiện.

**Chốt lại: CHƯA XÁC ĐỊNH ĐƯỢC NGUYÊN NHÂN.** Chỉ chốt nguyên nhân khi **tái hiện trên cùng HEAD**
và **chứng minh bằng can thiệp đúng MỘT yếu tố**.

## 3. R6 THẬT SỰ LÀ GÌ — theo §8

> *"Bộ đếm chung: tách số kế hoạch và ca có kết quả → **0 suite đổi từ đỏ sang xanh**. Sửa tính
> trung thực phạm vi, **không chữa lỗi mã thoát**."*

R6 tồn tại **về ngữ nghĩa**: khuôn E2E cộng cả `did not run` (53) và `skipped` vào "ca chạy thật";
`Ran N` của unittest gồm cả skipped. Đó là vấn đề **mẫu số / cách ghi phạm vi**, **không** phải lỗi
biến exit 1 thành exit 0.

## 4. ĐIỀU KIỆN ĐỂ R6 ĐƯỢC COI LÀ CÓ CĂN CỨ

1. **Tái hiện trên CÙNG HEAD, CÙNG môi trường**: chạy trực tiếp bộ thử, **lưu nguyên output + exit**;
   đưa **chính output ấy** qua `--tinh-ca`; đối chiếu với đường gọi trong `chay_tat_ca.sh`.
2. **Nếu hai đường cho kết quả khác nhau** → tìm **khác biệt môi trường/bootstrap**, **không tự quy
   cho regex**.
3. **Nếu KHÔNG tái hiện được lỗi đếm 0** → **BỎ giả thuyết ấy khỏi phạm vi sửa**. Không tạo bản vá
   cho lỗi chưa được chứng minh.
4. Chỉ gộp R6 khi có **bằng chứng trước/sau đúng nguyên nhân**.

## 5. VIỆC KHÔNG ĐỔI

Sửa R6 **không đồng nghĩa làm 9 bộ hết đỏ**. Các nhóm R1/R2/R3/R2-isolation vẫn giữ nguyên phạm vi
đã giao. `BEST-09` giữ **BLOCKED**, `BEST-10` giữ **PENDING**.
