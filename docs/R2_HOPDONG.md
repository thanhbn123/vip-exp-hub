# R2 — HỢP ĐỒNG VÀ KỲ VỌNG CŨ (BEST integration @ c909ebb)

Ngày đo: **19/10/2026 (UTC+7)**. Worktree: `/Users/viporder/orca/workspaces/vip-express-hub/r2-hopdong`.
Nhánh `best/integration`, HEAD `c909ebb93ee9b1cf8f6daf157cbd4640448a0fd1`; `main = de740dc` — **không dùng main**.
Cây theo dõi sạch trước khi sửa. Không sửa mã sản phẩm, không đụng DB nghiệp vụ, không gọi hãng,
không credentials, không push/deploy. **BEST-09 giữ BLOCKED.**

Báo cáo QA gốc đã đọc: `docs/QA_NGUYENNHAN.md` (worktree QA `Projects-vip-express-hub`, còn ở trạng
thái staged — chưa có trong cây này tại `c909ebb`). Bộ tự kiểm `app/thu/thu_qa_nguyennhan.py` được
chạy với `QANN_REPO` trỏ về worktree này, xem §5.

## 1. Phạm vi

| Tệp | Việc |
|---|---|
| `app/thu/thu_qa_g16.py` | phân biệt **THÔNG BÁO LỖI** với **SECRET THẬT** trong AST hard-code |
| `app/thu/thu_qa_jt.py` | phân biệt `urllib.parse` (xử lý chuỗi) với **I/O THẬT** |
| `app/thu/thu_qa_soat.py` | đo **TỪ CHỐI 400** theo hợp đồng G22 + đường truy vấn hợp lệ + cách ly tenant |
| `app/thu/thu_tich_hop.py` | chỉ sửa `test_05` (chú thích vs mã thật); **`test_09` GIỮ R7** |
| `app/thu/thu_r2_hopdong.py` | **mới** — đối chứng âm/đường + bảng bằng chứng |
| `docs/R2_HOPDONG.md` | **mới** — báo cáo này |

Không sửa: `chay_tat_ca.sh` (R6), `thu_g21_bimat`/`thu_g22_chotcay` (R27), `thu_g20_*` (R3), mã sản phẩm.

## 2. Lỗi TRƯỚC khi sửa — lệnh THẬT, exit THẬT

Môi trường mỗi lượt: `VIP_HUB_DATA=<thư mục tạm riêng>`, `VIP_HUB_BIND=127.0.0.1`,
`VIP_JT_MOI_TRUONG=mock`, `PYTHONDONTWRITEBYTECODE=1`, bỏ `VIP_KHO_DANG_CHAY`.
Các biến `GIT_CONFIG_*` hỏng của máy được gỡ (§6). Mã thoát lấy trực tiếp từ tiến trình.

| Bộ | Exit | `Ran` | FAIL/ERROR | Bỏ qua | Lỗi đầu |
|---|---:|---:|---:|---:|---|
| `thu_qa_g16.py` | **1** | 61 | 1 | 0 | `test_c5`: 3 dòng `app/xac_thuc_best.py:91,102,103` trong `MA_LOI` bị coi là credential |
| `thu_qa_jt.py` | **1** | 22 | 1 | 0 | `test_a4`: `'urllib' unexpectedly found ... adapter_best.py: from urllib.parse` |
| `thu_qa_soat.py` | **1** | 30 | 1 | 0 | `test_q09f`: `AssertionError: 400 != 200` (dòng cuối đòi 200 cho `GET /don?tenant_id=…`) |
| `thu_tich_hop.py` (git env sạch) | **1** | 12 | 2 | 0 | `test_05` grep trúng `http.client` trong **chú thích**; `test_09` luật phân tầng (R7) |

`thu_tich_hop.py` chạy trong **env nguyên trạng** còn thêm 2 FAIL `test_04`/`test_11` với
`AssertionError: 128 != 0` — đó là lỗi **môi trường git** của máy, không phải lỗi sản phẩm/bộ thử;
xem §6. Không sửa hai ca ấy vì phạm vi được chốt là `test_05`.

## 3. Nguyên nhân gốc và cách sửa

### 3.1 `thu_qa_g16` — thông báo lỗi ≠ secret

**Nguyên nhân gốc.** `quet_hardcode()` chỉ soi *tên* định danh + *độ mạnh* của literal. Ba khoá
`CREDENTIAL_KHONG_HOP_LE`, `TOKEN_KHONG_HOP_LE`, `CREDENTIAL_DA_DOI_KHONG_LUU` khớp
`TEN_NHAY_CAM` ở tiền tố, còn giá trị là **câu chẩn đoán tiếng Việt** đủ dài/đủ loại ký tự nên
`_du_manh()` cũng đúng. Không có bước nào nhìn **ngữ cảnh định danh** hay **hình dạng giá trị**.

**Sửa.** Thêm luật 4 trong `quet_hardcode`, chỉ miễn khi **đồng thời**:
1. tên là **MÃ LỖI UPPER_SNAKE** (`MA_LOI_UPPER_SNAKE.fullmatch`);
2. tên **không phải** trường bí mật chuẩn (không trùng/kết thúc bằng `password`, `secret`,
   `apikey`, `privatekey`, `accesskey`, `pwd`, `matkhau`);
3. giá trị là **câu văn ≥ 3 từ** với ≥ 2 từ có chữ cái.

Đây là ngữ cảnh AST có ý nghĩa, **không phải whitelist tệp/dòng**, và không tắt bộ dò: secret
vẫn bị bắt nếu rơi vào phép gán, dict cấu hình, hay **chính khoá mã lỗi** ấy.

**Bảng "thông báo lỗi vs secret" — đo trên `app/xac_thuc_best.py` THẬT:**

| Mã lỗi | Giá trị (rút gọn) | Là câu? | Trước | Sau | Tiêm `Xk9#mQ2$vL7@nR4` vào cùng mã |
|---|---|---:|---|---|---|
| `CREDENTIAL_KHONG_HOP_LE` | `Username rỗng/sai kiểu/ký tự điều khiển; Password rỗng/…` | có | **bị kêu (sai)** | không kêu | **bị bắt** |
| `TOKEN_KHONG_HOP_LE` | `token nhận được rỗng/sai kiểu/chứa ký tự không hợp lệ` | có | **bị kêu (sai)** | không kêu | **bị bắt** |
| `CREDENTIAL_DA_DOI_KHONG_LUU` | `credential đổi giữa lượt đăng nhập — từ chối token …` | có | **bị kêu (sai)** | không kêu | **bị bắt** |

Đối chứng âm bổ sung (trong `test_c5`): secret tiêm vào bản sao `transport.py` và bản sao
`xac_thuc_best.py` (cả phép gán `TOKEN_TIEM` lẫn dict `MA_LOI_TIEM`) **đều bị bắt**;
`PASSWORD = "correct horse battery staple"` vẫn bị bắt. Đối chứng dương: 5 dương tính giả cũ
(khoá dict câu văn, fixture giữ chỗ, đọc env, rỗng, ngắn) vẫn **không** bị kêu.

### 3.2 `thu_qa_jt` — `urllib.parse` không phải I/O

**Nguyên nhân gốc.** `test_a4` cấm **tên gốc** `urllib` và `http`. `adapter_best.py` chỉ có
`from urllib.parse import urlsplit` để tách URL — không mở socket — nhưng vẫn bị bắt. Đây là
nhầm "xử lý chuỗi" với "thực hiện I/O".

**Sửa.** Tách hai danh sách như luật đã dùng ở `test_09`:
`MANG_GOC = {requests, httpx, aiohttp, urllib3, socket, socketserver, ftplib, telnetlib, smtplib,
asyncio, ssl, xmlrpc, pycurl, websocket}`; `MANG_DAY_DU = {urllib.request, urllib.error,
http.client, http.server}`. Dò bằng AST (chú thích bị bỏ qua), xử lý cả ba dạng:
`import urllib.request`, `from urllib import request`, `http.client`; vẫn bắt lời gọi
`urlopen()`/`connect()`/`Session()`.

**Đối chứng âm:** tiêm từng dạng I/O thật (`import urllib.request`, `from urllib import request`,
`import http.client`, `import socket`, `urllib.request.urlopen(u)`) — bộ dò **phải** thấy.
**Đối chứng dương:** `from urllib.parse import urlsplit` và chú thích `# import urllib.request`
**không** bị kêu.

### 3.3 `thu_qa_soat` — 400 theo hợp đồng hiện hành, không phải 200

**Nguyên nhân gốc.** `test_q09f` khẳng định `GET /api/v2/don?tenant_id=…` trả **200** (giả định
máy chủ bỏ qua tham số tenant). Từ G22, `GET /don` đi qua `truy_van.tim_don`, lớp này **từ chối
400 tên lọc lạ** (`tenant_id` không nằm trong danh sách trường lọc). Giữ kỳ vọng 200 là ghìm
hợp đồng cũ; đổi sang 200 mà không đo gì thêm sẽ bỏ mất vế "không im lặng bỏ qua tham số lạ".

**Sửa.** Đo đúng ba vế, không nới cổng:
1. **Từ chối 400** + body có `loi` đọc được cho `GET /don?tenant_id=<tenant B>`.
2. **Đường hợp lệ** `GET /don` vẫn **200** và trả đơn vừa tạo của **tenant A**.
3. **Cách ly tenant**: phiên **B** gọi `GET /don` thấy danh sách của B và **không** chứa đơn của A.
Giữ nguyên hai phép đo body `tenant_id` ở `POST /don` và `POST /khach-hang`: vẫn 201 và dữ liệu
ghi vào **tenant A** — chứng minh tham số body **không ghi đè** ngữ cảnh phiên.

**Đối chứng âm:** nếu máy chủ quay lại hành vi cũ (bỏ qua `tenant_id`, trả 200), phép thử đỏ
ngay tại `assertEqual(st, 400)`. Đột biến này được chạy thật ở `thu_r2_hopdong.py` test 12.

### 3.4 `thu_tich_hop.test_05` — chú thích không phải mã

**Nguyên nhân gốc.** `test_05` `assertNotIn` trên **toàn văn tệp**. `adapter_best.py` có chữ
`http.client` trong **chú thích** giải thích vì sao tách lớp HTTP — grep trúng, dương tính giả.

**Sửa.** Thay grep bằng AST (`_vi_pham_nhap_mang`): chỉ thấy `Import`/`ImportFrom` trong **mã
chạy**; `urllib.parse` được phép; `urllib.request`/`http.client`/`socket` bị bắt. Đối chứng âm:
tiêm `import http.client`, `from urllib import request`, `import socket` → **phải** thấy.
Đối chứng dương: chú thích `# import http.client …` và `from urllib.parse import urlsplit`
→ **không** kêu.

### 3.5 `test_09` — GIỮ R7, không tự nới

Không sửa một dòng nào trong `test_09`. Nó **vẫn đỏ** (exit 1, 1 FAIL), **không thêm skip**,
**không bỏ assertion**, **không đổi danh sách mô-đun được phép**. Xem §4.

## 4. R7 — `test_09` còn thiếu căn cứ gì (báo AG-00)

Đo được ở `c909ebb` (AST, không grep):

```
http_best.py: import http.client
http_best.py: import socket
xac_thuc_best.py: import urllib.error
xac_thuc_best.py: import urllib.request
```

Đây **không phải lỗi vô hại**: `http_best.py` là lớp HTTP của BEST, `xac_thuc_best.py` có transport
đăng nhập trực tiếp bằng `urllib.request`. Nhưng luật của `test_09` phát biểu toàn cục
"chỉ `http_jt.py` được nói chuyện với mạng", trong khi `docs/BEST_EXPRESS_API_CONTRACT.md` lại
chủ động đưa `http_best.py` vào thiết kế. **Hai hợp đồng đang mâu thuẫn.** QA không được tự chọn.

Cần AG-00 chốt trước khi sửa scanner hay chuyển mã:

1. **Luật phân tầng là theo HÃNG hay toàn cục?** Nếu theo hãng: cho phép đúng một lớp transport
   mỗi hãng (`http_jt.py` cho JT, `http_best.py` cho BEST) và ghi danh sách trắng có tên trong
   hợp đồng G16; nếu toàn cục: phải gộp BEST vào một lớp duy nhất và chuyển `xac_thuc_best.py`
   sang dùng lớp ấy.
2. **Transport đăng nhập BEST** (`xac_thuc_best.py`) có được là mô-đun mạng thứ hai không? Nếu
   có, phải có hợp đồng an toàn tương đương `http_jt` (danh sách trắng host, hết giờ, không tự
   thử lại, che bí mật) và được review riêng trước khi mở.
3. **Tài liệu nào có thẩm quyền**: `BEST_EXPRESS_API_CONTRACT.md` (đưa `http_best.py` vào) hay
   luật G16 trong `test_09`. Cần sửa **cùng lúc** tài liệu + test + (nếu cần) mã, kèm đối chứng
   âm cho scanner phân tầng; không được chỉ đổi danh sách `duoc_phep` để xanh.

Cho tới khi chốt: `test_09` **R7/ĐỎ**, không phải PASS, không được tính vào nghiệm thu.

## 5. Bằng chứng SAU khi sửa

### 5.1 Bốn bộ chạy thật

| Bộ | Exit | `Ran` | FAIL/ERROR | Bỏ qua | Ghi chú |
|---|---:|---:|---:|---:|---|
| `thu_qa_g16.py` | **0** | 61 | 0 | 0 | `OK`; `Ran 61` gồm cả ca skipped (ở đây 0) |
| `thu_qa_jt.py` | **0** | 22 | 0 | 0 | `OK` |
| `thu_qa_soat.py` | **0** | 30 | 0 | 0 | `OK`; q09f đo 400 + 200 hợp lệ + cách ly |
| `thu_tich_hop.py` | **1** | 12 | **1** | 0 | chỉ `test_09` (R7) — `test_05` đã xanh |

Tách số ca: **kế hoạch = đã chạy** với cả bốn bộ (unittest không có ca chưa chạy); bỏ qua = 0;
`subTest` bên trong một ca **không** được cộng thêm vào `Ran`. Không cộng test con hai lần.

Lệnh (ví dụ G16; ba bộ còn lại thay tên tệp):

```sh
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 -u VIP_KHO_DANG_CHAY \
  VIP_HUB_DATA="$(mktemp -d)" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
  PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_qa_g16.py
```

### 5.2 Đối chứng âm ở mức PHÉP THỬ (`app/thu/thu_r2_hopdong.py`)

`python3 app/thu/thu_r2_hopdong.py -v` → **exit 0, Ran 12, OK**. Nó chạy lại 4 bộ và làm 4 phép
đột biến: tiêm **hành vi cũ** rồi đòi **phép thử đỏ**; nếu bản sửa chỉ xoá assertion, các ca này
sẽ không đỏ và harness fail.

| Đột biến (hành vi cũ) | Phép thử phải đỏ | Kết quả đo |
|---|---|---|
| Bộ dò G16 báo lại 3 dòng `MA_LOI` là credential | `test_c5` | **1 failure** |
| Bộ dò JT báo `from urllib.parse import urlsplit` là I/O | `test_a4` | **1 failure** |
| Bộ dò tích hợp báo `http.client` trong chú thích | `test_05` | **1 failure** |
| Máy chủ giả bỏ qua `tenant_id`, trả 200 | `test_q09f` | **1 failure** |

Harness cũng tiêm **secret thật** (`Xk9#mQ2$vL7@nR4`) vào phép gán, dict cấu hình, và đúng khoá
`CREDENTIAL_KHONG_HOP_LE` — cả ba **đều bị bắt**; tiêm I/O thật (`urllib.request`, `http.client`,
`socket`) vào AST — cả ba **đều bị bắt**. In bảng "BỘ THỬ | exit | ca | FAIL/ERROR | bỏ qua" và
bảng "MÃ LỖI | là CÂU? | câu bị kêu? | cùng mã + secret bị bắt?" khi chạy `-v`.

### 5.3 Bộ tự kiểm phân loại của QA

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub
QANN_REPO=/Users/viporder/orca/workspaces/vip-express-hub/r2-hopdong \
  python3 app/thu/thu_qa_nguyennhan.py -v
```

Kết quả: **exit 0, Ran 11, OK**. Không đổi hàm `phan_loai` của QA; chỉ chạy lại theo yêu cầu vì
thay đổi có liên quan phân loại (thông báo lỗi vs secret).

## 6. Môi trường đo — lỗi git của máy (báo AG-00)

Môi trường phiên này đặt `GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0/1`, nên mọi tiến
trình `git` con chết:

```
fatal: unable to parse command-line config   (exit 128)
```

Đây là lỗi môi trường, không phải lỗi sản phẩm. `thu_qa_g16._git()` đã tự gỡ `GIT_CONFIG*`
(docstring gọi là Finding A); các lượt đo ở đây cũng gỡ. `thu_tich_hop.test_04/test_11` chưa gỡ
nên trong env nguyên trạng chúng đỏ **giả** (`128 != 0`). **Không sửa hai ca đó** vì phạm vi được
chốt là `test_05`; đề nghị AG-00 chuẩn hoá env trước khi chạy hồi quy toàn bộ, hoặc gỡ
`GIT_CONFIG*` ở mọi chỗ gọi git.

## 7. Ràng buộc đã giữ

- Local-first; **không** push/deploy/commit; **không** gọi API hãng; **không** credentials;
  **không** sửa DB nghiệp vụ; **không** tự mở LIVE; **BEST-09 giữ BLOCKED**.
- Không xoá test, không bỏ assertion, không thêm skip, không nuốt exception, không đổi exit để
  xanh, không chỉ đổi số kỳ vọng cho khớp output.
- Không sửa `chay_tat_ca.sh`, `thu_g20_*`, `thu_g21_bimat`, `thu_g22_chotcay`, mã sản phẩm.
- Không chạy lại toàn bộ 75 bộ và **không** tuyên bố toàn bộ hồi quy xanh.

## 8. Tệp thay đổi & chạy lại

```text
M app/thu/thu_qa_g16.py      # luật 4 + đối chứng âm/dương
M app/thu/thu_qa_jt.py       # AST tách urllib.parse khỏi I/O thật
M app/thu/thu_qa_soat.py     # q09f: 400 theo hợp đồng + 200 hợp lệ + cách ly tenant
M app/thu/thu_tich_hop.py    # test_05 AST; test_09 giữ nguyên (R7)
?? app/thu/thu_r2_hopdong.py # harness bằng chứng + đột biến
?? docs/R2_HOPDONG.md        # báo cáo này
```

Chạy lại tối thiểu:

```sh
python3 app/thu/thu_qa_g16.py
python3 app/thu/thu_qa_jt.py
python3 app/thu/thu_qa_soat.py
python3 app/thu/thu_tich_hop.py          # còn 1 FAIL test_09 = R7 có chủ đích
python3 app/thu/thu_r2_hopdong.py -v     # exit 0 khi R7 vẫn đúng là R7
```
