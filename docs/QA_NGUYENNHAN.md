# QA nguyên nhân gốc — BEST integration c909ebb

Ngày đo: **19/10/2026, giờ Việt Nam (UTC+7)**. Kho: `/Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub`. Nhánh `best/integration`; HEAD `c909ebb93ee9b1cf8f6daf157cbd4640448a0fd1`; `main=de740dc` theo Git tại lúc kiểm tra. Cây theo dõi sạch trước đo.

## 1. Kết luận trong phạm vi đã đo

**Đã chạy trực tiếp đủ 25 mục gốc: 9 đạt, 16 không đạt.** Đây là kết quả của **25 mục được yêu cầu**, không phải số bộ đỏ của toàn bộ 75 bộ hiện nay; không chạy lại toàn bộ hồi quy để suy ra tổng mới. Không tái sử dụng con số 2216 hay 25 đỏ làm sự thật hiện tại.

Đối chứng không đổi mã sản phẩm làm xanh thêm **hai bộ riêng biệt**: `chay_e2e.sh` với khai kho SQLite trên nền tạm (**41/41, exit 0**), và `thu_g21_bimat.py` với thư mục tạm sạch (**33 ca, exit 0**). Không có một sửa chữa duy nhất nào đã được chứng minh làm cả 16 bộ còn lại xanh.

**R1 chung chỉ xuất hiện còn lại ở 3 bộ:** G01/G02, G19 route, E2E shell. Khai kho chỉ làm **1/3 bộ xanh hoàn toàn**; hai bộ kia lộ lỗi kỳ vọng cũ sau đó. Các bộ trước đây báo 0 ca như G17 bảo mật, G18 máy chủ, G18 đa tiến trình, G19 giới hạn, G21 giới hạn, giao dịch, hạn mức, header và truy vấn **đều chạy được** ở mốc này.

**Chưa xác nhận lỗi chức năng sản phẩm R5 trong lượt đo này.** Điều này không chứng minh sản phẩm không có lỗi: Chromium không khởi động được trong sandbox, một phần PostgreSQL không chạy được, và luật phân tầng HTTP giữa G16/BEST còn mâu thuẫn. Những phần ấy giữ R7, không được đổi thành PASS hay tự nới gate.

## 2. Phương pháp, môi trường và độ tin cậy

- Mỗi lệnh Python gốc là `python3 app/thu/<tên>.py`, E2E là `sh app/thu/chay_e2e.sh`, chạy từ gốc kho. Mã thoát lấy trực tiếp từ tiến trình, không lấy từ grep hay pipeline.
- `VIP_HUB_DATA` luôn trỏ thư mục tạm riêng; `VIP_HUB_BIND=127.0.0.1`, `VIP_JT_MOI_TRUONG=mock`, `PYTHONDONTWRITEBYTECODE=1`. Lượt cơ sở bỏ `VIP_KHO_DANG_CHAY`; lượt R1 chỉ thêm `VIP_KHO_DANG_CHAY=sqlite` trong môi trường thử. Không đặt biến cho tiến trình đang phục vụ.
- Python hệ thống 3.9.6, Darwin arm64. Đã được cấp quyền ghi kho và mạng để mở loopback. Lượt ban đầu bị chặn bind được cách ly trong `work/qa-sandbox-blocked`, **không dùng để kết luận**.
- Quyền mạng chưa gỡ hạn chế Mach bootstrap của Chromium hoặc shared memory PostgreSQL. Không tự duyệt sandbox, không lấy credentials, không gọi hãng, không push/deploy, không sửa DB đang dùng.
- Trong lúc đo có hai lượt trùng nhau ở nhóm G21/G22. Nhóm có khả năng dùng chung tệp được **đo lại tuần tự trên clone tạm cùng commit**, có local branch `main` cùng SHA; `node_modules` dùng chung ở chế độ đọc. Bằng chứng có tiền tố `isolated-` là lượt đối chiếu sạch; không dùng lượt chồng nhau để kết luận nguyên nhân. Clone `codex-qann-copy-*` không phải worktree sản phẩm.
- “Ca” trong bảng là số ca mà runner thực sự công bố ở lượt đó, không phải số trong báo cáo cũ. Với unittest, `Ran N` **gồm ca skipped**; cột bỏ qua/chưa chạy ghi riêng. Số ca con nằm trong output cha không được cộng thêm. Với Playwright, 80 là số ca kế hoạch có trạng thái, **53 chưa chạy**, 27 có trạng thái pass/fail; không khẳng định 27 thân test đã chạy hết vì lỗi xảy ra ở browser fixture. Với bộ viết tay, tổng có thể chứa KHUYẾT; xem chi tiết dưới.
- Raw log + metadata cho từng tiến trình, log con và `counter.json` được đóng gói trong `QA_NGUYENNHAN_BANG_CHUNG.zip` bàn giao cùng báo cáo. Các tên log dưới đây là đường tương đối trong gói đó.

## 3. Bảng phân nhóm đủ 25 mục

| Bộ | Exit thật | Ca báo cáo | Bỏ qua/chưa chạy | Nhóm | Nguyên nhân / kết quả |
|---|---:|---:|---:|---|---|
| `thu_g01_g02.py` | 1 | 21 | 0 | R1 + R2 | Tiến trình con migrate thiếu khai kho; query tenant_id bị từ chối 400, bộ cũ đọc kq[don]; sau khai còn chốt chống tụt v10→v0. |
| `thu_g17_baomat.py` | 0 | 31 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_g18_maysrv.py` | 0 | 17 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_g18_multiprocess.py` | 0 | 26 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_g19_gioihan.py` | 0 | 22 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_g19_route.py` | 1 | 14 | 0 | R1 + R3 | BOT → may_chu_do (con) thiếu khai kho; sau khai còn ghim khoảng trống 31 thay vì 32, route 103 thay vì 104. |
| `thu_g20_dahang.py` | 1 | 27 | 0 | R3 | Ghim số nhãn CHUNG 30 nhưng đo 38; ghim dòng 831 và [285,311,343,742] đã dịch chuyển. |
| `thu_g20_saoluu.py` | 1 | 35 | 1 | R3 + R7 | Schema khôi phục 10, phép đo đòi 9; có 1 ca PostgreSQL bỏ qua vì sandbox chặn shmget. |
| `thu_g21_bimat.py` | 1 | 33 | 0 | R2 | Z4 quét cả thư mục tạm của lượt khác; chỉ đổi TMPDIR sang thư mục sạch: exit 0, 33 ca. |
| `thu_g21_gioihan.py` | 0 | 22 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_g21_saoluu.py` | 1 | 13 | 1 | R7 | initdb/shmget bị sandbox chặn; ca con ném SkipTest rồi bị cha coi là lỗi. Chưa đo đủ fail-closed PostgreSQL. |
| `thu_g22_chotcay.py` | 1 | 11 | 0 | R2 + R3 | D2 đòi cây thật có tệp mới; D4 chọn bản lịch sử gần nhất vốn đã đạt quy tắc. Tạo tệp trên clone chỉ chữa D2. |
| `thu_g22_e2e.py` | 1 | 80 | 53 | R3 + R6 + R7 | Chromium bị chặn Mach bootstrap; kế hoạch hiện tại 80 nhưng ghim 65; bộ đếm cộng 53 did-not-run vào tổng. |
| `thu_g22_gioihan.py` | 1 | 32 | 0 | R3; R6 chưa đủ bằng chứng | C5 có 2 ứng viên, tiêm 1 thì ứng viên kia còn xanh: 1/2 vẫn DONG. Không thể suy riêng lỗi đếm skipped từ lượt này. |
| `thu_giao_dich.py` | 0 | 17 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_han_muc_nguyen_tu.py` | 0 | 5 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_header_bao_mat.py` | 0 | 8 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `thu_qa_g16.py` | 1 | 61 | 0 | R2 | Quét AST nhận nhầm 3 giá trị trong dict MA_LOI (câu thông báo lỗi BEST) là credential hard-code. |
| `thu_qa_g18.py` | 1 | 47 | 1 | R3 + R7 | B1: Chromium bị sandbox chặn; G2: thu_frontend/thu_http.py ghim 10 trang demo, hiện có 11. |
| `thu_qa_g22.py` | 1 | 24 | 1 | R7 | 3 FAIL cấp ngoài: E2E toàn bộ, bàn phím, bàn đo G20; cùng chuỗi Chromium bị chặn, có 1 skip. |
| `thu_qa_jt.py` | 1 | 22 | 0 | R2 | Cấm gốc urllib nên bắt urllib.parse trong adapter_best dù chỉ tách URL, không thực hiện I/O. |
| `thu_qa_soat.py` | 1 | 30 | 0 | R2 | Hợp đồng query hiện từ chối tenant_id (400); bộ cũ đòi 200. |
| `thu_tich_hop.py` | 1 | 12 | 0 | R2 + R7 | test_05 grep trúng http.client trong chú thích; test_09 mâu thuẫn luật chỉ http_jt với các mô-đun BEST mới. Chưa tự ý đổi hợp đồng. |
| `thu_truy_van.py` | 0 | 40 | 0 | XANH — không tái hiện | Không có FAIL/ERROR ở lượt đo trực tiếp. |
| `chay_e2e.sh` | 1 | 0 | 0 | R1 | migrate chạy trong tiến trình con, log bị trap xóa; cùng bước migrate tái hiện thiếu khai; khai sqlite thì E2E đạt 41/41. |

`thu_g20_saoluu`: Ran 35 (1 skip), không phải số 41 trong lịch sử. `thu_g21_saoluu`: Ran 13 (1 skip), không phải 23. `thu_qa_g22`: Ran 24 (1 skip) ở **suite ngoài**; output còn chứa Ran 21 của G20 con, không cộng thành 45. Các số này phụ thuộc môi trường và nhánh fixture thực sự chạy.

`thu_g22_gioihan`: 32 mục = **27 ĐẠT + 3 HỎNG + 2 KHUYẾT**. 32 không đồng nghĩa 32 assertion sản phẩm thành công. Lượt isolated cũng cho đúng phân bố này, exit 1.

## 4. R1 — đối chứng trước/sau và vị trí gọi migrate

| Bộ | Kiểu gọi | Không khai | Chỉ thêm khai SQLite trên nền tạm | Còn lỗi gì? |
|---|---|---|---|---|
| G01/G02 | `test_014` → `subprocess.run(migrate.py)` | exit 1, Ran 21; thiếu khai kho | exit 1, Ran 21 | test_010 `KeyError: don`; test_014 chuyển sang từ chối tụt schema v10→v0 |
| G19 route | `BOT.chay_may_chu` → `may_chu_do` con → migrate | exit 1, Ran 14, 13 ERROR | exit 1, Ran 49, 2 FAIL | ghim 31/32 và 103/104; lớp C trước không dựng nổi nền, nay đã chạy |
| E2E shell | shell → `python3 app/migrate.py` | exit 1, 0 phép đo | **exit 0, KẾT QUẢ 41/41** | không còn lỗi ở lượt này |

Log: `base-*`, `sqlite-*`. E2E gốc chuyển stdout/stderr migrate vào nền rồi trap xóa toàn bộ nền nên output gốc rỗng. Đã chạy riêng **đúng bước `python3 app/migrate.py` trên nền tạm mới**: không khai exit 1 và thông điệp `TỪ CHỐI: CHƯA KHAI kho đang chạy`; khai SQLite exit 0 (`e2e-step-undeclared.log`, `e2e-step-sqlite.log`). Không trình bày thông điệp tái hiện này như thể nó xuất hiện trong log shell gốc.

Ba lỗi thiếu khai hiện còn thấy đều đi qua **tiến trình con**, không phải ba cách hỏng khác nhau trong sản phẩm. Điểm sửa bền: bootstrap của phép thử tự khai sau khi xác minh dữ liệu cô lập, và truyền môi trường sang con. Không đưa mặc định SQLite vào migrate/cấu hình production. Việc dùng biến môi trường ở lượt này là đối chứng chẩn đoán, chưa phải bản vá.

## 5. R2/R3 — kỳ vọng cũ, fixture không độc lập, ghim số liệu

- **Query tenant_id:** G01 `test_010` và QA soát `test_q09f` cùng giả định máy chủ bỏ qua tham số tenant do client gửi. Hợp đồng G22 hiện từ chối 400. G01 không kiểm status trước khi đọc khóa `don`, nên dấu vết bề mặt thành KeyError; không phải bằng chứng rò tenant. Cần giữ đối chứng dương truy vấn hợp lệ và đo từ chối 400/body đúng.
- **Rollback G01:** sau khai kho, migrate từ chối bản v0 đè v10 đúng chốt chống tụt schema. Bộ cũ đòi rollback được nhận vô điều kiện. Cập nhật phép đo theo hợp đồng và đo đường khôi phục được phép trên bản sao; không bỏ chốt sản phẩm để làm test xanh.
- **G19 route:** sau khai kho, chính bộ đo in 104 route, 32 mục thiếu. Assertion vẫn là 103 và 31. Hai lỗi ở cùng một bộ thử; sửa ghim mà chưa khai kho không làm xanh bộ này.
- **G20 đa hãng:** chỉ 3 FAIL là ghim số nhãn CHUNG và tọa độ dòng. Nhãn đo được `CHUNG=38` trong khi kỳ vọng 30; dòng thông điệp là `[108,115,116,1035]` thay vì đòi có 831; nhánh có dòng thực tế `[285,311,344,946]` trong khi kỳ vọng `[285,311,343,742]`. Nên đo cấu trúc/hành vi bằng AST, không cập nhật số dòng để tiếp tục trôi.
- **G20 sao lưu:** dữ liệu được bảo toàn và schema khôi phục là 10; `test_a5` đòi đúng 9. Còn 1 ca PostgreSQL bỏ qua trong sandbox, vì vậy sửa assertion không đồng nghĩa toàn phạm vi PostgreSQL đã được nghiệm thu.
- **G21 bí mật:** Z4 liệt kê toàn bộ thư mục hệ thống có tiền tố `vh-g21bimat-*`/`vip-hub-g21-*`; nó thấy thư mục của lượt trước, không chứng minh lượt này rò. Clone cùng commit + TMPDIR riêng mới: **33 ca, exit 0**. Chỉ dọn tài nguyên do chính lượt tạo, không xóa thư mục của lượt khác. Log `fresh-temp-thu_g21_bimat.py.log`.
- **G22 chốt cây:** trên clone sạch có 2 FAIL (D2, D4); thêm riêng `docs/qann_probe.md` trong clone cho D2 đạt nhưng vẫn **exit 1, Ran 11, D4 FAIL**. D4 lấy bản lịch sử gần nhất `6ac4d0a8` làm bản phải hỏng, nhưng bản đó đã đạt quy tắc. Đây là fixture lịch sử sai tiền đề; tự tiêm một mẫu sai có chủ đích sẽ có ý nghĩa hơn. Không làm bẩn cây thật để chiều D2. Log `isolated-*` và `dirty-copy-*`.
- **G16 secret:** 3 ứng viên tại `xac_thuc_best.py:91,102,103` đều là giá trị trong `MA_LOI`: thông điệp chẩn đoán, không phải credential. Tên khóa chứa CREDENTIAL/TOKEN cộng câu văn dài làm heuristic trúng nhầm. Cần đo ngữ cảnh AST, kèm tiêm secret thật vào cả assignment và dict để tránh chữa bằng cách tắt bộ dò.
- **QA JT:** `adapter_best.py` chỉ `from urllib.parse import urlsplit`. Phép thử cấm cả gốc `urllib`, nhầm xử lý chuỗi thành I/O.
- **Tích hợp:** `test_05` dùng grep, trúng chữ `http.client` trong chú thích adapter BEST. Nhưng **test_09 là vấn đề khác:** AST thấy I/O thật ở `http_best.py` và `xac_thuc_best.py`, trong khi luật G16 chỉ cho `http_jt.py`. Tài liệu `BEST_EXPRESS_API_CONTRACT.md` lại chủ động đưa vào `http_best.py`. Phải chốt hợp đồng hiện hành trước khi sửa scanner hay chuyển code. Phần test_09 giữ **R7**, không tuyên bố mọi vi phạm phân tầng đều vô hại.
- **QA G18/frontend:** log con `fe_tang2.log` có Ran 40, đúng 1 FAIL `test_04_muoi_trang_demo_g00_khong_bi_pha`: **11 != 10**. Đây là lỗi ghim số trang độc lập với Chromium.
- **G22 giới hạn/C5:** ứng viên `thu_qa_g19*.py` hiện là 2. Khi tiêm hỏng một wrapper, C5 vẫn in **1/2, DONG, exit 0** vì ứng viên kia đạt. G22 đòi C5 đỏ nên có 3 HỎNG; 2 phép all-skipped thành KHUYẾT. Chưa đủ bằng chứng để kết luận nhánh all-skipped được chính C5 chấp nhận: ứng viên còn lại có thể đã làm cổng xanh. Phải cô lập danh sách ứng viên hoặc kiểm từng ứng viên, rồi mới quyết định OR/AND theo hợp đồng. Cả lượt đo lại tuần tự cho cùng kết quả. Hàm `_dem_nhu_chay_tat_ca` trong bộ này còn là bản sao regex cũ, không còn trung thành với bộ đếm đã thêm 5 khuôn.

Các suite trong bảng **không có cờ nghiệm thu nào đã được chứng minh làm xanh toàn bộ lỗi hiện tại**. `VIP_G22_CHE_DO=gop` là chế độ nghiệm thu được định nghĩa ở QA G22, nhưng không gỡ chặn Chromium và không được coi là “đổi cờ là xanh”. Không dùng chế độ nền làm bằng chứng đã nghiệm thu.

## 6. R4/R5/R7 — phần môi trường và sản phẩm chưa đo được

**Không tái hiện R4 thiếu Chromium/node_modules.** Chromium tồn tại, chạy được bước lấy phiên bản: 141.0.7390.37, Playwright 1.56.1, SHA-256 `a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040`.

Browser fixture chết với `FATAL … mach_port_rendezvous_mac.cc … bootstrap_check_in … Permission denied (1100)`. Cổng G22 trả **exit 1/HONG**, máy chủ vẫn sống; báo cáo Playwright là **2 passed / 25 failed / 0 skipped / 53 did not run**. Lượt clone riêng lặp lại cùng phân bố. Các thất bại browser fixture không phải 25 lỗi nghiệp vụ được chứng minh. Cần phân biệt rõ thất bại khởi động browser với lỗi ứng dụng ở gate (đây là một thiếu sót phân loại hạ tầng cần xem xét).

Ba suite bị cùng hạn chế Chromium: **G22 E2E, QA G18, QA G22** (QA G22 còn gọi G20 con). Sửa môi trường đo một lần ảnh hưởng cả 3; chưa thể hứa cả 3 xanh: G22 E2E còn ghim 65 dù danh sách đã là 80, QA G18 còn ghim 10 trang.

PostgreSQL thử nghiệm dùng cụm tạm, nhưng `initdb` không tạo được shared-memory segment: `shmget … Operation not permitted`. G21 sao lưu có **2 FAIL + 1 skip**; G20 sao lưu có 1 skip. Đây không phải bằng chứng thiếu gói PostgreSQL. Cần môi trường chạy được cụm tạm rồi đo lại; không dùng cụm nghiệp vụ để thay thế.

R5 chưa được chứng minh bằng ca chức năng hiện tại. Bộ mới vẫn có đối chứng R5 thật: bản sao `adapter_jt.ky_digest` bị đổi trả chữ ký sai, cùng harness bản sạch đạt và bản tiêm thất bại. Nhãn R5 không bị gộp chung vào “bộ đo cũ”.

## 7. R6 — đối chiếu bộ in gì và bộ đếm đọc gì

Đã gọi **chính** `sh app/thu/chay_tat_ca.sh --tinh-ca <exit> <log>` cho từng log, không chép lại regex để tự xác nhận. Bảng sau dành cho 24 suite Python; shell E2E có đường đọc riêng `KẾT QUẢ`, nên việc `--tinh-ca` không nhận khuôn shell không phải lỗi của đường tổng hợp hiện tại.

| Bộ | Ca runner công bố | Bộ đếm N | Ghi chú |
|---|---:|---:|---|
| `thu_g01_g02.py` | 21 | 21 | khớp số công bố |
| `thu_g17_baomat.py` | 31 | 31 | khớp số công bố |
| `thu_g18_maysrv.py` | 17 | 17 | khớp số công bố |
| `thu_g18_multiprocess.py` | 26 | 26 | khớp số công bố |
| `thu_g19_gioihan.py` | 22 | 22 | khớp số công bố |
| `thu_g19_route.py` | 14 | 14 | khớp số công bố |
| `thu_g20_dahang.py` | 27 | 27 | khớp số công bố |
| `thu_g20_saoluu.py` | 35 | 35 | khớp số công bố; 1 skip |
| `thu_g21_bimat.py` | 33 | 33 | khớp số công bố |
| `thu_g21_gioihan.py` | 22 | 22 | khớp số công bố |
| `thu_g21_saoluu.py` | 13 | 13 | khớp số công bố; 1 skip |
| `thu_g22_chotcay.py` | 11 | 11 | khớp số công bố |
| `thu_g22_e2e.py` | 80 | 80 | 80 là kế hoạch; 53 chưa chạy, chỉ 27 có trạng thái pass/fail |
| `thu_g22_gioihan.py` | 32 | 32 | 32 = 27 ĐẠT + 3 HỎNG + 2 KHUYẾT |
| `thu_giao_dich.py` | 17 | 17 | khớp số công bố |
| `thu_han_muc_nguyen_tu.py` | 5 | 5 | khớp số công bố |
| `thu_header_bao_mat.py` | 8 | 8 | khớp số công bố |
| `thu_qa_g16.py` | 61 | 61 | khớp số công bố |
| `thu_qa_g18.py` | 47 | 47 | khớp số công bố; 1 skip |
| `thu_qa_g22.py` | 24 | 24 | khớp số công bố; 1 skip |
| `thu_qa_jt.py` | 22 | 22 | khớp số công bố |
| `thu_qa_soat.py` | 30 | 30 | khớp số công bố |
| `thu_tich_hop.py` | 12 | 12 | khớp số công bố |
| `thu_truy_van.py` | 40 | 40 | khớp số công bố |

**Không có lỗi đọc thành 0 khi suite Python gốc vừa công bố N>0 ở lượt này.** Các số 0 cũ của G22 giới hạn đã được bộ đếm hiện tại sửa: đọc được **32**. Bộ đếm cũng đọc E2E **80**, không còn 0.

**R6 về ngữ nghĩa vẫn tồn tại nếu tổng được gọi là “ca chạy thật”:** khuôn E2E cộng cả `did not run` và `skipped`. Từng hạng mục của lượt thật: pass=2, fail=25, skip=0, did-not-run=53, flaky=0 → tổng kế hoạch 80, kết quả pass/fail 27. Chênh **53** không được coi là 53 ca đã chạy. Đây là vấn đề ở mẫu số/cách ghi phạm vi, không biến exit 1 thành exit 0. Tương tự, `Ran N` unittest gồm skipped; cần tách kế hoạch/chạy/bỏ qua trong báo cáo, không tự đổi nghĩa của unittest.

E2E shell sau khai kho: **KẾT QUẢ: 41/41**, đường shell trong bộ tổng hợp hiện có regex `KẾT QUẢ`, không có bằng chứng đếm nhầm ở đường này. Không cộng 41 vào tổng Python.

## 8. Bảng “sửa một chỗ thì N bộ xanh” — phân biệt chứng minh và dự kiến

| Điểm chung / nơi cần xử lý | Số bộ bị ảnh hưởng trong 25 | Số bộ xanh hoàn toàn đã chứng minh chỉ bằng can thiệp ấy | Điều còn ngăn kết luận |
|---|---:|---:|---|
| Bootstrap khai kho cho môi trường thử → con; 3 entrypoint cùng một quy tắc | 3 | **1** (E2E shell) | G01 còn query/rollback; G19 route còn 2 ghim. Chưa có một helper được cả 3 dùng, không nói sai là sửa 1 dòng hiện hữu |
| TMPDIR riêng / phạm vi sở hữu tài nguyên G21 bí mật | 1 | **1** (33 ca) | Cần sửa test chỉ theo dõi tài nguyên do lượt tạo, không dọn toàn máy |
| Môi trường cho Chromium khởi động | 3 | **0 đã chứng minh** | Sandbox chưa cho chạy; E2E ghim 65/80; QA G18 ghim 10/11 |
| Môi trường shared memory cho PostgreSQL tạm | 2 | **0 đã chứng minh** | G20 còn schema9; G21 phải đo lại các kịch bản bị chặn |
| Hợp đồng query từ chối tenant_id | 2 | **0 đã sửa/đo sau sửa** | Cần đổi assertion ở hai tệp; G01 còn lỗi khác, không phải 1 file chung |
| G19 route: thay số ghim bằng quan hệ tập hợp | 1 | **0; dự kiến 1 nếu đã khai kho** | Chưa sửa bộ cũ theo phạm vi yêu cầu |
| G20 đa hãng: bỏ tọa độ dòng/số nhãn cứng | 1 | **0; dự kiến 1** | Cần giữ kiểm ngữ nghĩa và đối chứng âm, không chỉ cập nhật con số |
| G20 sao lưu: kỳ vọng schema theo fixture/hợp đồng | 1 | **0; dự kiến hết FAIL hiện thấy** | Vẫn còn một skip PostgreSQL, chưa đủ nghiệm thu đầy đủ |
| Scanner secret hiểu ngữ cảnh thông báo lỗi | 1 | **0; dự kiến 1** | Không thêm whitelist rộng làm lọt secret thật |
| Scanner adapter xử lý AST đúng cho urllib.parse/chú thích | 2 | **0; dự kiến QA JT hết FAIL** | Tích hợp còn xung đột luật transport phải chốt riêng |
| Fixture C5: tách ứng viên / kiểm từng ứng viên | 1 | **0 đã chứng minh** | Cổng OR hiện vẫn có ứng viên sạch; 3 HỎNG + 2 KHUYẾT cùng một gốc fixture |
| Fixture chốt cây: tự tạo tệp trên clone, tiêm bản sai cụ thể | 1 | **0 toàn bộ** | Tạo tệp mới chỉ làm D2 xanh; D4 vẫn FAIL |
| Bộ đếm chung: tách số kế hoạch và ca có kết quả | Mọi dòng báo cáo dùng khuôn tương ứng | **0 suite đổi từ đỏ sang xanh** | Sửa tính trung thực phạm vi, không chữa lỗi mã thoát |

Không cộng các dòng thành số bộ vì có giao nhau. Không chia 5 agent theo quota. Có thể giao theo cụm sở hữu: (a) bootstrap/test isolation, (b) hợp đồng và bộ quét QA, (c) fixture C5/chốt cây/bộ đếm, (d) hạ tầng Chromium/PostgreSQL. Cụm hạ tầng không sửa sản phẩm; các cụm còn lại phải tránh giao trùng file QA G22 và G20. Đây là đề xuất phân công, chưa dispatch và chưa sửa.

## 9. Bộ tự kiểm phân loại mới

Tệp `app/thu/thu_qa_nguyennhan.py`: **11 test, exit 0, OK**. API `phan_loai` nhận bằng chứng đối chứng, có thể trả nhiều nhãn; không tự biến mọi exit khác 0 thành R5, không dùng bảng kết luận viết cứng để tự xác nhận.

- R1: gọi migrate thật, không khai thất bại, khai SQLite trên nền tạm đạt; trích dẫn thông điệp mà thiếu đối chứng không đủ gán R1.
- R2: fixture cùng mã nguồn, chế độ nền thất bại và nghiệm thu đạt; nghiệm thu vẫn thất bại phải giữ R7.
- R3: assertion schema ghim cũ thất bại, đo schema thực tế độc lập; ghim bằng sự thật không bị gán R3.
- R4: thiếu tệp phụ thuộc thật làm tiến trình hỏng, cung cấp tệp làm đạt; không có bằng chứng thiếu thì không gán R4.
- R5: copy app sang nền tạm, chạy chữ ký thật đạt; chỉ đổi `ky_digest` ở bản sao làm cùng harness hỏng; băm mã sản phẩm gốc trước/sau không đổi.
- R6: chạy 2 ca unittest thật, lấy `result.testsRun`, gọi bộ đếm thật; đổi khuôn summary làm bộ đếm đọc 0 và bị phát hiện; khuôn đúng đọc 2. Có thêm đối chứng khuôn G22 giới hạn/E2E hiện tại và lỗi lẫn “chưa chạy” vào “đã chạy”.
- R7: lỗi không đủ bằng chứng hoặc exit0/0ca không được phong XANH.
- Đa nguyên nhân: thiếu khai được gỡ nhưng schema vẫn lệch phải giữ cả R1 + R3.

Fixture R2/R4 là kiểm chứng khả năng của bộ phân loại, **không phải** tuyên bố hai nhóm ấy được tái hiện trên mọi suite thật. Bằng chứng suite thật nằm ở các bảng phía trên. Bộ phân loại chỉ suy đúng khi người gọi cung cấp can thiệp cùng mã nguồn/đúng một yếu tố như giao diện đã quy định; không phải một bộ chẩn đoán tự động hiểu mọi traceback.

## 10. Dòng lỗi đầu và FAIL/ERROR cụ thể cho từng bộ

Đọc log nguyên bản để có toàn bộ traceback. Dưới đây lưu dòng lỗi đầu và mọi tiêu đề FAIL/ERROR bắt được; output của suite cha có thể chứa cả lỗi của suite con, được giữ nguyên làm bằng chứng và không cộng vào số ca cha.

### `thu_g01_g02.py` — exit 1, 21 ca

Log: `base-thu_g01_g02.py.log`.

Lỗi đầu: KeyError: 'don'

```text
ERROR: test_010_doi_tenant_id_trong_request_khong_vuot_quyen (__main__.ThuG01G02)
FAIL: test_014_migration_bao_toan_du_lieu (__main__.ThuG01G02)
```

### `thu_g17_baomat.py` — exit 0, 31 ca

Log: `base-thu_g17_baomat.py.log`.

Không có FAIL/ERROR.

### `thu_g18_maysrv.py` — exit 0, 17 ca

Log: `base-thu_g18_maysrv.py.log`.

Không có FAIL/ERROR.

### `thu_g18_multiprocess.py` — exit 0, 26 ca

Log: `base-thu_g18_multiprocess.py.log`.

Không có FAIL/ERROR.

### `thu_g19_gioihan.py` — exit 0, 22 ca

Log: `base-thu_g19_gioihan.py.log`.

Không có FAIL/ERROR.

### `thu_g19_route.py` — exit 1, 14 ca

Log: `base-thu_g19_route.py.log`.

Lỗi đầu: RuntimeError: may_chu_do thất bại (exit 1):

```text
ERROR: test_a1_tang_tinh_va_tang_thi_hanh_deu_lam_viec (__main__.A_BoTrichThuBa)
ERROR: test_a2_tang_thi_hanh_THUC_SU_loai_bot (__main__.A_BoTrichThuBa)
ERROR: test_a4_giam_sat_mang_zero_luot_ra_ngoai_loopback (__main__.A_BoTrichThuBa)
ERROR: test_a5_bo_trich_ba_khong_co_route_la (__main__.A_BoTrichThuBa)
ERROR: test_a6_bo_trich_ba_phu_31_muc_con_thieu_cua_AG01 (__main__.A_BoTrichThuBa)
ERROR: test_a7_RAM_platform_khong_phai_route (__main__.A_BoTrichThuBa)
ERROR: test_a8_noi_ro_gioi_han_cap_phuong_thuc (__main__.A_BoTrichThuBa)
ERROR: test_b1_tiem_route_gia_thi_PHAI_thay (__main__.B_DotBien)
ERROR: test_b3_bia_dang_CHUOI_THAT_thi_tang_thi_hanh_phai_loai (__main__.B_DotBien)
ERROR: test_b4_xoa_route_that_thi_PHAI_mat (__main__.B_DotBien)
ERROR: test_b5_dot_bien_RO_RI_thi_phep_do_cach_ly_PHAI_do (__main__.B_DotBien)
ERROR: setUpClass (__main__.C_DoCachLy)
ERROR: test_d1_con_so_phu (__main__.D_ConSoCuoi)
```

### `thu_g20_dahang.py` — exit 1, 27 ca

Log: `base-thu_g20_dahang.py.log`.

Lỗi đầu: AssertionError: {'CHUNG': 38, 'DAC_THU_JT': 7} != {'CHUNG': 30, 'DAC_THU_JT': 7}

```text
FAIL: test_a2_hai_ham_giu_chot_chan_hang_bi_gan_nhan_dung (__main__.CaRanhGioi)
FAIL: test_a6_nhan_hieu_hang_trong_thong_diep_chi_tinh_chuoi_CHAY_DUOC (__main__.CaRanhGioi) (dong=831)
FAIL: test_a7_bon_nhanh_ma_bi_rang_buoc_hang (__main__.CaRanhGioi)
```

### `thu_g20_saoluu.py` — exit 1, 35 ca

Log: `base-thu_g20_saoluu.py.log`.

Lỗi đầu: AssertionError: 10 != 9 : phiên bản schema sau khôi phục khác 9

```text
FAIL: test_a5_ban_sao_luu_co_byte_va_mo_duoc (__main__.A_VongTronTrenDuLieuThat)
```

### `thu_g21_bimat.py` — exit 1, 33 ca

Log: `base-thu_g21_bimat.py.log`.

Lỗi đầu: AssertionError: Lists differ: ['vh-g21bimat-goc-qhez_tsf'] != []

```text
FAIL: test_z4_khong_con_thu_muc_tam_cua_bo_thu (__main__.Z_TongKet)
```

### `thu_g21_gioihan.py` — exit 0, 22 ca

Log: `base-thu_g21_gioihan.py.log`.

Không có FAIL/ERROR.

### `thu_g21_saoluu.py` — exit 1, 13 ca

Log: `base-thu_g21_saoluu.py.log`.

Lỗi đầu: AssertionError: 1 != 0 : lượt đo trên biến thể ban_va hỏng (rc=1): 20-saoluu/do_postgres.py", line 122, in chay

```text
FAIL: test_c4_ban_va_lam_moi_kich_ban_chuyen_sang_FAIL_CLOSED (__main__.C_TuKiemBoDo)
FAIL: test_c9_noi_lai_chinh_sach_cu_thi_S8_PHAI_do (__main__.C_TuKiemBoDo)
```

### `thu_g22_chotcay.py` — exit 1, 11 ca

Log: `base-thu_g22_chotcay.py.log`.

Lỗi đầu: AssertionError: 0 not greater than or equal to 1 : cây SẠCH TRƠN ⇒ phép đo rỗng

```text
FAIL: test_d2_moi_ban_sao_xanh_tren_cay_co_tep_moi_cua_lan_khac (__main__.D_BanSao)
FAIL: test_d4_moi_ban_sao_theo_QUY_TAC_va_ban_CU_bi_bat (__main__.D_BanSao)
```

### `thu_g22_e2e.py` — exit 1, 80 ca

Log: `base-thu_g22_e2e.py.log`.

Lỗi đầu: Log browser con: FATAL mach_port_rendezvous_mac.cc — bootstrap_check_in … Permission denied (1100).

Không có dòng `FAIL:`/`ERROR:` theo unittest; runner viết tay/shell.

### `thu_g22_gioihan.py` — exit 1, 32 ca

Log: `base-thu_g22_gioihan.py.log`.

Lỗi đầu:   ✗ B3.a_bo_goc_tra_ma_khac_0                                  C5 ĐỎ LẠI khi bản uỷ quyền bị tiêm lỗi (a_bo_goc_tra_ma_khac_0)

Không có dòng `FAIL:`/`ERROR:` theo unittest; runner viết tay/shell.

Mục hỏng: B3.a_bo_goc_tra_ma_khac_0; B3.b_bo_goc_khong_ton_tai; B3.c_suite_rong_0_ca. KHUYẾT: B3.d_moi_ca_bo_qua_phuong_thuc; B3.d2_moi_ca_bo_qua_module.

### `thu_giao_dich.py` — exit 0, 17 ca

Log: `base-thu_giao_dich.py.log`.

Không có FAIL/ERROR.

### `thu_han_muc_nguyen_tu.py` — exit 0, 5 ca

Log: `base-thu_han_muc_nguyen_tu.py.log`.

Không có FAIL/ERROR.

### `thu_header_bao_mat.py` — exit 0, 8 ca

Log: `base-thu_header_bao_mat.py.log`.

Không có FAIL/ERROR.

### `thu_qa_g16.py` — exit 1, 61 ca

Log: `base-thu_qa_g16.py.log`.

Lỗi đầu: AssertionError: Lists differ: ['app/xac_thuc_best.py:dòng 91: CREDENTIAL[188 chars]tự>'] != []

```text
FAIL: test_c5_khong_hard_code_secret_trong_ma_san_pham (__main__.C_Credentials)
```

### `thu_qa_g18.py` — exit 1, 47 ca

Log: `base-thu_qa_g18.py.log`.

Lỗi đầu: AssertionError: 1 != 0 : tầng 3 KHÔNG đạt (mã thoát 1) — log: /var/folders/v1/443y_fys65vflj24_rjw9x_w0000gn/T/veh_g18_ag01_qa_log/tang3.log

```text
FAIL: test_b1_tang_3_chay_duoc_va_khong_co_ca_hong (__main__.B_Tang3)
FAIL: test_g2_tang_2_http_dat_va_khong_teo_ca (__main__.G_HaiTangFE)
```

### `thu_qa_g22.py` — exit 1, 24 ca

Log: `base-thu_qa_g22.py.log`.

Lỗi đầu: AssertionError: 1 != 0 : BỘ CHẠY `chay.sh` THOÁT KHÁC 0 (rc=1) dù báo cáo đọc được (2 đạt, 25 hỏng, 0 bỏ qua, 53 không chạy) ⇒ mã thoát là phán quyết, không tin báo cáo đơn lẻ:

```text
FAIL: test_b2_chay_e2e_toan_bo_that (__main__.C_BanPhim)
FAIL: test_b3_e2e_tam_ca_ban_phim_chay_that (__main__.C_BanPhim)
FAIL: test_d1_nam_cong_g20 (__main__.D_BanDoG20)
FAIL: test_b1_tang_3_ban_phim_trong_man (__main__.B_GiaoDien)
FAIL: test_b2_ca_04_phai_do_hien_duoc_so_diem_dung (__main__.B_GiaoDien)
FAIL: test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong (__main__.Z_ChotChan)
```

### `thu_qa_jt.py` — exit 1, 22 ca

Log: `base-thu_qa_jt.py.log`.

Lỗi đầu: AssertionError: 'urllib' unexpectedly found in {'urllib', 'asyncio', 'telnetlib', 'socket', 'smtplib', 'requests', 'ftplib', 'xmlrpc', 'pycurl', 'aiohttp', 'ssl', 'httpx', 'socketserver', 'http'} : adapter_best.py: from urllib.parse

```text
FAIL: test_a4_khong_co_duong_cham_mang_bang_AST (__main__.A_ChuKyVaTransport)
```

### `thu_qa_soat.py` — exit 1, 30 ca

Log: `base-thu_qa_soat.py.log`.

Lỗi đầu: AssertionError: 400 != 200

```text
FAIL: test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh (__main__.ThuQaSoat)
```

### `thu_tich_hop.py` — exit 1, 12 ca

Log: `base-thu_tich_hop.py.log`.

Lỗi đầu: AssertionError: 'http.client' unexpectedly found in '# B1 — ADAPTER BEST EXPRESS (VietnamV3) — MOCK_VERIFIED, chưa có REAL PASS.\n#\n# TRẠNG THÁI, NÓI NGAY TỪ DÒNG ĐẦU:\n#   · Tài liệu API BEST trong đề bài là một Google Docs. Task KHÔNG kèm URL, workspace KHÔNG có\n#     bản sao, và agent bị CẤM đoán endpoint/request schema. Vì vậy tệp này chỉ dùng những gì…

```text
FAIL: test_05_adapter_khong_co_duong_goi_mang_nao (__main__.CanhCauTruc)
FAIL: test_09_chi_MOT_mo_dun_san_pham_duoc_noi_chuyen_voi_mang (__main__.G16_CauHinhVaPhanTang)
```

### `thu_truy_van.py` — exit 0, 40 ca

Log: `base-thu_truy_van.py.log`.

Không có FAIL/ERROR.

### `chay_e2e.sh` — exit 1, 0 ca

Log: `base-chay_e2e.sh.log`.

Lỗi đầu: Output gốc rỗng: migrate.log nằm trong nền bị trap xóa. Bước migrate tái hiện độc lập: TỪ CHỐI: CHƯA KHAI kho đang chạy (exit 1).

Không có dòng `FAIL:`/`ERROR:` theo unittest; runner viết tay/shell.

## 11. Trạng thái bàn giao

Chỉ thêm hai tệp theo yêu cầu: báo cáo này và bộ tự kiểm phân loại mới. Không sửa có lưu lại bất kỳ bộ thử cũ hay mã sản phẩm nào; không commit/gộp/push/deploy. Các bộ thử có thao tác tạm đã khôi phục cây; đối chiếu `git diff HEAD` cho tệp theo dõi rỗng sau đo. Hai tệp mới sẽ làm trạng thái untracked khác lúc baseline; không dùng kết quả sau tạo tệp để giả làm kết quả trên cây sạch ban đầu.

Chưa thể báo toàn bộ hồi quy xanh. Bước tiếp theo phải là sửa theo nhóm được chốt phạm vi riêng, chạy QA chứng minh từng nhóm, rồi mới chạy lại toàn bộ `chay_tat_ca.sh`. BEST-09/BEST-10 không được mở hoặc tự xác nhận trong lượt phân tích này.
