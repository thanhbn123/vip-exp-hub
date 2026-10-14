# QA_TEST_PLAN — VIP EXPRESS HUB

**Tác giả:** AG-07 QA · **Đợt:** WAVE 1 · **Ngày đo:** 14/10/2026
**Worktree:** `~/code/veh-qa`, nhánh `agent/qa` · **Gốc soát:** commit `a1dea69`
**Nền chạy:** macOS Darwin 25.6.0 (MacBook Pro) · `Python 3.9.6`

> **Đây là QA bằng AI, KHÔNG phải independent human review.**
>
> **Luật trung thực của bản kế hoạch này (§12.1):** mục nào **chưa chạy** thì ghi
> `NOT TESTED`, không ghi `PASS`. Mỗi `PASS` phải trỏ về một ca thử có tên thật, và chỉ có
> hiệu lực **trong phạm vi ca thử đó**. Mọi con số dưới đây lấy từ lệnh, không từ tài liệu.
>
> **Phạm vi WAVE 1:** chỉ mã **có sẵn tại commit `a1dea69`**. Bốn agent SECURITY · CARRIER ·
> IMPORT · FRONTEND đang sửa trong worktree riêng; WAVE 1 **không thấy và không chạy** mã của
> họ. Vì vậy phần lớn hạng mục của bốn nhóm đó là `NOT TESTED` một cách **cố ý**, không phải
> bỏ sót.

---

## 0. Baseline regression — số liệu THẬT

Cách đo: chạy từng bộ, lấy mã thoát của **chính tiến trình python** (không lấy của `tail`),
và đếm từ dòng `Ran N tests` do `unittest` in ra.

| Bộ thử | Số ca | PASS | FAIL | Mã thoát | Trạng thái |
|---|---|---|---|---|---|
| `app/thu/thu_g03.py` | 30 | 30 | 0 | 0 | **PASS** |
| `app/thu/thu_g01_g02.py` | 21 | 21 | 0 | 0 | **PASS** |
| `app/thu/thu_saas.py` | 19 | 18 | **1** | 1 | **FAIL** — `test_16_khong_dung_du_lieu_cu` |
| `gateway/thu/thu_gateway.py` | 9 | 9 | 0 | 0 | **PASS** |
| `app/thu/thu_qa_soat.py` *(mới, của AG-07)* | 30 | 16 | **14** | 1 | **FAIL CÓ Ý** — 14 ca chứng minh lỗ hổng |
| **Tổng** | **109** | **94** | **15** | — | |

### Ca baseline hỏng: `thu_saas.py::test_16_khong_dung_du_lieu_cu`

```
AssertionError: False is not true
  self.assertTrue(os.path.exists(os.path.join(goc, "gateway", "du-lieu", "gateway.db")))
```

**Đây là lỗi BỘ THỬ, không phải lỗi sản phẩm** (Q-11). `.gitignore` loại `gateway/du-lieu/`
khỏi git, nên trong worktree mới file đó chưa tồn tại; ca thử đòi nó có sẵn. Khẳng định thật
mà ca thử muốn chốt — "CSDL SaaS nằm riêng, không đụng `gateway.db` của G01" — nằm ở dòng
`assertNotEqual` ngay dưới và dòng đó **đạt**.

### Gateway — tiền sử segfault ngắt quãng

Lệnh đo (lặp 20 lượt, đếm lượt mã thoát khác 0):

```sh
h=0; for i in $(seq 1 20); do python3 gateway/thu/thu_gateway.py >/dev/null 2>&1 || h=$((h+1)); done; echo "$h/20 hỏng"
```

| Loạt | Kết quả |
|---|---|
| Loạt 1 (20 lượt) | **0/20 hỏng** |
| Loạt 2 (20 lượt, đo lại độc lập) | **0/20 hỏng** |
| **Tổng 40 lượt** | **0 segfault, 0 hỏng** |

**Kết luận: bản vá "mỗi thread một kết nối SQLite" giữ được.** `csdl.py` (phía app) ghi rõ lý do
và dùng `threading.local()`; không lượt nào trả mã thoát âm (segfault cho `-11`/`139`) trong
40 lượt.

**Phạm vi của con số "0" này (§12.1 luật 5):**
(a) **Công cụ đo:** mã thoát tiến trình của `python3 gateway/thu/thu_gateway.py`, 40 lượt.
(b) **Phạm vi thật:** 9 ca của bộ gateway, chạy **tuần tự**, một tiến trình mỗi lượt, trên
MacBook Pro / Python 3.9.6.
(c) **NGOÀI phạm vi:** tải đồng thời thật (nhiều client song song trong **cùng** một tiến
trình lâu dài), máy khác (Mac mini M4, VPS), và Python khác. Segfault do đua thread là lỗi
**xác suất theo thời điểm**: 0/40 lượt ngắn **không** chứng minh "đã hết", chỉ chứng minh
"không còn tái hiện ở tần suất ~1/5 như trước".

### Ghi thêm: cả 4 bộ thử bind cổng cố định (Q-12)

Quan sát **1 lượt trong 41** hỏng với `OSError: [Errno 48] Address already in use` (cổng
`18898`), xảy ra khi một bộ khác đang chạy chồng. **Không phải segfault** — đã đo nguyên nhân
bằng `netstat` (hàng loạt `TIME_WAIT` trên `127.0.0.1.18898`) và bằng chuỗi lỗi trong log, chứ
không suy đoán. Đây là nguồn "hỏng ngắt quãng" **giả** rất dễ bị ghi nhầm thành lỗi sản phẩm.
Hướng xử: bind cổng `0` để hệ cấp cổng trống.

---

## 1. Bảo mật

| # | Hạng mục | Trạng thái | Ca thử / lý do |
|---|---|---|---|
| S-01 | Cách ly tenant — đọc/sửa/xóa đơn chéo | **PASS** | `thu_saas` 01–03, `thu_g01_g02` 002–003 |
| S-02 | Cách ly tenant — **dòng import** chéo | **PASS** | `thu_qa_soat::test_q09_…` (mới — trước đây chưa phủ) |
| S-03 | Cách ly tenant — `duyet_batch` nhận dòng của batch/tenant khác | **PASS** | `thu_qa_soat::test_q09b_…` (mới) |
| S-04 | Cách ly tenant — **rotate/revoke/khóa** tài khoản hãng chéo | **PASS** | `thu_qa_soat::test_q09m_…` (mới) |
| S-05 | Webhook cập nhật đơn tenant khác khi **mã vận đơn trùng ở hai tenant** | **PASS** | `thu_qa_soat::test_q09c_…` (mới — ca cũ chỉ kiểm mã không tồn tại) |
| S-06 | `tenant_id` từ body/query không ghi đè ngữ cảnh | **PASS** | `thu_qa_soat::test_q09f_…`, `thu_g01_g02` 010 |
| S-07 | Soát tĩnh: câu SQL thiếu điều kiện tenant | **PASS** (có 6 câu được miễn, từng câu có lý do) | `thu_qa_soat::test_q09g_…` + `SQL_DUOC_MIEN` |
| S-08 | RBAC — mọi endpoint gọi `self._can()` | **FAIL** | `test_q03_…`, `test_q03b_…` → **Q-03**: `/platform/vai-tro`, `/platform/goi` thiếu |
| S-09 | RBAC — các đường `/platform/*` còn lại chặn `TENANT_VIEWER` | **PASS** | `thu_qa_soat::test_q03c_…` |
| S-10 | RBAC — `VIEWER` không ghi, `STAFF` không đổi vai trò | **PASS** | `thu_g01_g02` 007–008 |
| S-11 | Leo thang đặc quyền qua `POST /memberships` (ADMIN → OWNER/PLATFORM) | **PASS** | `thu_qa_soat::test_q09j_…` (mới) |
| S-12 | Thu hồi quyền có hiệu lực **ngay**, không cache ngữ cảnh | **PASS** | `thu_qa_soat::test_q09e_…` (mới), `thu_g01_g02` 006/012/021 |
| S-13 | Không đổi sang tenant không có membership | **PASS** | `thu_qa_soat::test_q09k_…`, `thu_g01_g02` 016 |
| S-14 | **Luồng đặt lại mật khẩu không lộ token ở cấu hình mặc định** | **FAIL** | `test_q01_…`/`q01b`/`q01c` → **Q-01 CRITICAL** |
| S-15 | Bộ phục vụ static không trả mã nguồn | **FAIL** | `test_q02_…` → **Q-02 HIGH** |
| S-16 | Static không thoát ra ngoài gốc repo (`..`, `%2e%2e`) | **PASS** | `thu_qa_soat::test_q09l_…` (mới) |
| S-17 | Khóa mã hóa và `.git` không tải được | **PASS** (nhờ danh sách đen — xem cảnh báo Q-02) | `thu_qa_soat::test_q02b_…` |
| S-18 | Webhook bắt buộc chữ ký, không có đường vòng | **PASS** (4 biến thể) | `thu_qa_soat::test_q09d_…` (mới) |
| S-19 | Secret/mật khẩu không lọt vào log, audit, phản hồi API | **PASS** *(trong phạm vi 5 secret của bộ thử)* | `thu_qa_soat::test_q09h_…`, `thu_saas` 12 |
| S-20 | `wh_su_kien.headers_json` không lộ ra API | **PASS** | `thu_qa_soat::test_q09i_…` (mới) |
| S-21 | Mã hóa credentials AES-256-GCM, AAD chặn chép chéo tenant | **PASS** | `thu_g03` E1–E7 (7 ca) |
| S-22 | Không âm thầm tụt về sơ đồ mã hóa yếu | **PASS** | `thu_g03::test_e6_…` |
| S-23 | Khóa tài khoản sau 5 lần sai **có đường khôi phục** | **FAIL** | `test_q06_…` → **Q-06**: khóa vĩnh viễn từ xa |
| S-24 | 404-vs-403 không làm máy dò sự tồn tại | **FAIL** | `test_q04_…` → **Q-04** |
| S-25 | CSRF — header `X-Requested-With` bắt buộc cho ghi | **PASS** | `thu_saas` 13 |
| S-26 | Phiên hết hạn / thu hồi mất hiệu lực | **PASS** | `thu_g01_g02` 012, `thu_saas` 14 |
| S-27 | Thông báo đăng nhập không tiết lộ tài khoản tồn tại | **PASS** | `thu_g01_g02` 005/017 |
| S-28 | Chặn theo IP / tốc độ cho đường vô danh | **NOT TESTED** — **mã không có tính năng này**; không có gì để thử. Đã ghi là thiếu sót ở Q-06/Q-07c | — |
| S-29 | HTTPS / nhãn cookie `Secure` | **NOT TESTED** — hệ bind `127.0.0.1`, chạy HTTP thuần ở local; thuộc tầng triển khai, chưa có | — |
| S-30 | Chữ ký webhook của **hãng thật** (mỗi hãng một sơ đồ) | **BLOCKED** — `moi_truong` khác `mock` bị chặn cứng 403 chờ Owner duyệt | `thu_saas` 17 chốt việc chặn |
| S-31 | Pentest / soát bởi người | **NOT TESTED** — nằm ngoài khả năng của tác tử QA | — |

## 2. Carrier (hãng vận chuyển)

| # | Hạng mục | Trạng thái | Ca thử / lý do |
|---|---|---|---|
| C-01 | Capability matrix từng hãng, hãng không hỗ trợ thì từ chối rõ | **PASS** | `thu_g03` nhóm A/B |
| C-02 | Thu lại + backoff tăng dần, lỗi vĩnh viễn không thu lại | **PASS** | `thu_g03` C1–C6 |
| C-03 | Chống trùng theo khóa của adapter | **PASS** | `thu_g03::test_c5_…` |
| C-04 | Polling chỉ hỏi đơn đang chạy, qua rank guard, ghi audit | **PASS** | `thu_g03` D1–D5 |
| C-05 | Polling **không tự chạy** khi import | **PASS** | `thu_g03::test_d6_…` |
| C-06 | Tôn trọng giới hạn lô theo tài liệu hãng (J&T 30/lượt) | **PASS** | `thu_g03::test_d5_…` |
| C-07 | Timeout khi gửi hãng **không** đánh dấu `da_gui`, bật cờ đối soát | **PASS** | `thu_saas` 10 |
| C-08 | Công thức ký J&T đúng tài liệu (đối chiếu độc lập bằng `hashlib`) | **PASS** | `thu_saas` 18 |
| C-09 | Môi trường `sandbox`/`production` bị khóa | **PASS** | `thu_saas` 17, `thu_g03` |
| C-10 | Gọi API hãng **thật** (VTP, J&T, GHN, GHTK, BEST) | **BLOCKED** — ràng buộc nhiệm vụ cấm gọi API hãng thật; chỉ có mock | — |
| C-11 | Mã trạng thái **lạ** từ hãng thật → `polling_ma_la`, không đoán | **PASS** *(ở mức mock)*; với mã thật là **BLOCKED** | `thu_g03` D |
| C-12 | Mã nguồn carrier do AG-CARRIER sửa ở WAVE 1 | **NOT TESTED** — worktree khác, WAVE 1 không thấy | — |

## 3. Import

| # | Hạng mục | Trạng thái | Ca thử / lý do |
|---|---|---|---|
| I-01 | Nạp CSV và XLSX, chuẩn hóa tên cột | **PASS** | `thu_saas` 11 |
| I-02 | Dòng lỗi không làm hỏng cả batch, đánh dấu `INVALID` | **PASS** | `thu_saas` 11 |
| I-03 | Idempotency khi duyệt lại batch (không nhân đôi đơn) | **PASS** | `thu_saas` 09, khóa `import-{batch}-{dong}` |
| I-04 | Sửa dòng chéo tenant bị chặn | **PASS** | `thu_qa_soat::test_q09_…` (mới) |
| I-05 | Duyệt dòng của batch/tenant khác bị chặn | **PASS** | `thu_qa_soat::test_q09b_…` (mới) |
| I-06 | **Chặn số dòng / kích thước file** | **FAIL** | `test_q07_…` → **Q-07** (20.000 dòng/1 yêu cầu được nhận) |
| I-07 | **Chặn độ dài `dong_ids` do client cấp** | **FAIL** | `test_q07b_…` → **Q-07b** (50.000 id được xử) |
| I-08 | PDF có lớp văn bản — best-effort, PDF scan báo lỗi rõ | **NOT TESTED** — chưa dựng mẫu PDF; mã có nhánh lỗi rõ ràng nhưng chưa chạy qua | — |
| I-09 | XLSX hỏng / zip bomb / XML bomb | **NOT TESTED** — `doc_xlsx` dùng `zipfile` + `ElementTree` không giới hạn; mối lo thật, chưa dựng ca | — |
| I-10 | Mã nguồn import do AG-IMPORT sửa ở WAVE 1 | **NOT TESTED** — worktree khác | — |

## 4. Frontend

| # | Hạng mục | Trạng thái | Ca thử / lý do |
|---|---|---|---|
| F-01 | Frontend không cầm secret, có header chống CSRF | **PASS** | `thu_saas` 13 |
| F-02 | API danh sách tài khoản hãng không trả credentials | **PASS** | `thu_saas` 12 |
| F-03 | **Tiêm công thức vào CSV xuất ra** | **FAIL** | `test_q08_…` → **Q-08** |
| F-04 | XSS trong `admin/admin.js` (656 dòng) | **NOT TESTED** — không soát JS ở WAVE 1; chưa đọc `admin.js`, `pages/` | — |
| F-05 | Giao diện chạy thật trên trình duyệt (render, lỗi console) | **NOT TESTED** — chưa mở trình duyệt lượt nào | — |
| F-06 | Dùng được trên điện thoại / màn nhỏ | **NOT TESTED** | — |
| F-07 | Mã nguồn frontend do AG-FRONTEND sửa ở WAVE 1 | **NOT TESTED** — worktree khác | — |

## 5. Regression & độ bền

| # | Hạng mục | Trạng thái | Ca thử / lý do |
|---|---|---|---|
| R-01 | Bốn bộ thử gốc chạy lại trên worktree sạch | **FAIL** (1 ca, `thu_saas::test_16`) | xem mục 0 — là lỗi bộ thử (Q-11) |
| R-02 | Gateway không segfault — 40 lượt | **PASS** *(0/40, phạm vi ở mục 0)* | lệnh đo ở mục 0 |
| R-03 | Bộ soát QA ổn định (14 FAIL đúng những ca đó, không đổi) | **PASS** — 20 lượt, 20 lượt đều mã thoát `1` | lặp 20 lượt `thu_qa_soat.py` |
| R-04 | Migration bảo toàn dữ liệu, có đường lùi | **PASS** | `thu_g01_g02` 014 |
| R-05 | Nâng cấp v3 đổi hết credentials sang AES-GCM, đọc lại được | **PASS** | `thu_g03::test_e7_…` |
| R-06 | Còn đọc được bản mã định dạng v1 (không mất credentials khi migrate) | **PASS** | `thu_g03::test_e5_…` |
| R-07 | Gateway G01 cũ vẫn đạt sau khi lên v2 | **PASS** | `thu_g01_g02` 015 |
| R-08 | Hạn mức gói chặn từ backend (nhân viên, kết nối hãng, đơn, AI) | **PASS** | `thu_saas` 15 |
| R-09 | Audit đủ trường, ghi cả lượt **từ chối** | **PASS** | `thu_g01_g02` 018 |
| R-10 | RBAC lấy từ CSDL, không hard-code | **PASS** | `thu_g01_g02` 019 |
| R-11 | Webhook retry → DLQ → replay | **PASS** | `thu_saas` 08b, `thu_gateway` 05–06 |
| R-12 | Dữ liệu người dùng sai → 400, **không** thành 500 | **FAIL** | `test_q05b_…`, `test_q05c_…` → **Q-05b/c** |
| R-13 | Tham số `gioi_han` có chặn **cả hai đầu** | **FAIL** | `test_q05_…` → **Q-05** (`LIMIT -1` = không giới hạn) |
| R-14 | Mức chặn body riêng cho đường vô danh | **FAIL** | `test_q07c_…` → **Q-07c** |
| R-15 | Tải đồng thời thật (nhiều client song song, phiên dài) | **NOT TESTED** — chưa dựng bộ đo tải; đúng chỗ tiền sử segfault từng xuất hiện | — |
| R-16 | Chạy lâu / rò bộ nhớ / rò kết nối SQLite theo thread | **NOT TESTED** | — |
| R-17 | Khôi phục sau khi CSDL bị khóa / đĩa đầy | **NOT TESTED** | — |
| R-18 | Bộ thử bind cổng động, chạy chồng được | **FAIL** | Q-12 — cả 4 bộ dùng cổng cố định |

---

## 6. Tổng kết trạng thái

Số dưới đây **đếm bằng lệnh** từ chính các bảng mục 1–5 của file này (§12.1 luật 4), không
đếm tay:

| Trạng thái | Số hạng mục | Mã |
|---|---|---|
| **PASS** | 48 | — |
| **FAIL** | 13 | `S-08` `S-14` `S-15` `S-23` `S-24` `I-06` `I-07` `F-03` `R-01` `R-12` `R-13` `R-14` `R-18` |
| **BLOCKED** | 3 | `S-30` `C-10` `C-11` (chờ Owner duyệt môi trường thật / nhiệm vụ cấm gọi API hãng) |
| **NOT TESTED** | 14 | `S-28` `S-29` `S-31` `C-12` `I-08` `I-09` `I-10` `F-04` `F-05` `F-06` `F-07` `R-15` `R-16` `R-17` |
| **Tổng** | **78** | |

**13 hạng mục `FAIL` ≠ 14 ca thử `FAIL`** — số không khớp là có lý do, không phải sai sót: hai
hạng mục gộp nhiều phát hiện cùng gốc. `S-08` phủ cả Q-03 và Q-03b (hai đường thiếu `_can`);
`R-12` phủ cả Q-05b và Q-05c (cùng một họ "dữ liệu sai → 500").

Ánh xạ sang `docs/QA_FINDINGS.md`: `S-14`→Q-01 · `S-15`→Q-02 · `S-08`→Q-03/Q-03b ·
`S-24`→Q-04 · `R-13`→Q-05 · `R-12`→Q-05b/Q-05c · `S-23`→Q-06 · `I-06`→Q-07 · `I-07`→Q-07b ·
`R-14`→Q-07c · `F-03`→Q-08 · `R-01`→Q-11 · `R-18`→Q-12. Q-10 không có hạng mục `FAIL` riêng:
nó là **rủi ro cấu trúc chưa gây lỗi hôm nay**, nằm trong `S-07` (PASS, kèm danh sách miễn có
lý do).

**Không phát hiện nào được vá trong worktree này** — ràng buộc nhiệm vụ: QA phát hiện, không vá.

## 7. Việc WAVE 2 phải làm

1. Chạy lại cả 5 bộ thử sau khi AG-00 hợp nhất; **đếm xem bao nhiêu trong 14 ca `LOHONG` đã
   chuyển xanh**, và ca nào xanh *vì bị sửa assert* thay vì vì mã được vá.
2. Soát mã mới của 4 agent kia — WAVE 1 **chưa đọc một dòng nào** trong đó.
3. Lấp các mục `NOT TESTED` có đòn bẩy cao nhất, theo thứ tự: `R-15` (tải đồng thời — chỗ
   segfault từng ở), `F-04` (XSS trong `admin.js`), `I-09` (XLSX/zip bomb), `I-08` (PDF).
4. Gộp Q-11 + Q-12 thành một việc dọn bộ thử (bỏ phụ thuộc file ngoài git, bind cổng `0`).
