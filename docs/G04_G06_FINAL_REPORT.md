# BÁO CÁO NGHIỆM THU — SECURITY HARDENING + G04 + G06

> Định dạng theo mục 18 chỉ thị của chủ dự án. Mọi con số trong file này là **số đo**, lấy từ
> lệnh đã chạy trên MacBook ngày **15/10/2026**, không điền từ trí nhớ. Chỗ nào chưa đo thì ghi
> thẳng là chưa đo — theo luật `CLAUDE.md` §12.1 luật 4 và luật số "0".

---

## PROJECT
VIP EXPRESS HUB

## PROJECT PATH
`~/Projects/vip-express-hub`

## BASELINE SHA
`fd7c545` — chủ dự án báo; AG-00 đã tự đối chiếu, khớp.

## STARTING SHA
`4016eef` — AG-00 WAVE 0: đóng băng hợp đồng đợt 2 + bảng quyền sở hữu file + luật khóa worktree.
Năm worktree agent đều nhận nền này.

## FINAL LOCAL SHA
`599dd08` (`599dd088232572128cc6eb9dd4855b3f766a7d0a`)

## BRANCH
`main` (local). **Không có git remote nào được cấu hình** — nên không có đường để push, kể cả vô ý.

## CONTROLLER
AG-00

## WORKERS
AG-01 SECURITY · AG-02 ORDERS · AG-03 WEBHOOK · AG-04 FRONTEND · AG-05 QA

---

## AGENT STATUS

| Agent | Nhánh | SHA | Bàn giao | AG-00 tự kiểm | Gộp |
|---|---|---|---|---|---|
| **AG-01** | `agent/security-hardening` | `c52f8f1` | xong | 8 file, +2763 dòng, không chạm file người khác sở hữu | `7f7c6dc` |
| **AG-02** | `agent/g04-orders` | `c43bed2` | xong | `don_hang.py` 213→1059 dòng, `DDL_G04` chỉ THÊM | `71fc2cd` |
| **AG-03** | `agent/g06-webhook` | `48d04f9` | xong | +600 `webhook.py`, +265 `trang_thai_hang.py`, +108 `polling.py` | `6e7b194` |
| **AG-04** | `agent/frontend-automation` | `fb39fe3` | xong | 9 file, +2596/−129, không chạm `app/` lẫn `gateway/` | `88b491e` |
| **AG-05** | `agent/qa-verification` | `0efd291` | xong | 4 file mới, +2037 dòng; **AG-05 không tự commit** — AG-00 chốt hộ sau khi làn đã nhả, không sửa một dòng nội dung | `4461fb0` |

**Chạy song song — nói đúng sự thật:** năm agent chạy như năm tiến trình nền thật, mỗi agent một
git worktree riêng. Năm agent của **WAVE 1** được phóng cùng một lượt và thực sự chạy đồng thời.
Riêng thời gian hoàn thành lệch nhau nhiều (AG-02/AG-03 xong trước, AG-01/AG-04 xong sau ~31 phút),
nên AG-00 gộp theo thứ tự phụ thuộc chứ không gộp một lượt.

**Về soát của AG-05:** đây là **AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW** — một luồng công việc
độc lập do AI thực hiện. **KHÔNG phải independent human review.** Không ai trong chuỗi này là người.

---

## QUALITY GATES

| Gate | Trạng thái | Căn cứ đo |
|---|---|---|
| **G01 MULTI-TENANT** | **PASS** | 21/21 `thu_g01_g02.py` (TEST-001…015); ngữ cảnh tenant chỉ giải từ phiên, không từ body/query — đo lại ở E2E |
| **G02 AUTH + RBAC** | **PASS** | 57/57 `thu_bao_mat.py`; 6 vai trò, 24 quyền trong CSDL, chốt leo thang `quyen.CAP_DUOC` |
| **G03 CARRIER ENGINE** | **PASS (mock)** | 53/53 `thu_g03.py`; cả 5 hãng `CHO_PHEP_LIVE=False` — **chưa gọi API thật lượt nào** |
| **G04 ORDER SERVICE** | **PASS** | 63/63 `thu_don_hang.py` + 12/12 route đo qua HTTP thật trong E2E |
| **G05 IMPORT ENGINE** | **PASS** | 21/21 `thu_nhap_file.py`; E2E nạp CSV 3 dòng → 2 đơn, chặn tiêm công thức đo được |
| **G06 WEBHOOK** | **PASS** | 68/68 `thu_webhook.py` + 2 điểm cắm đo qua HTTP; mã J&T `110` giữ AMBIGUOUS, không đoán |

---

## SECURITY HARDENING

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **PASSWORD RESET** | **PASS** | Ba lỗ đã bịt: token mặc định TẮT (`HIEN_TOKEN_RESET=0`); token sinh TRƯỚC lần đổi mật khẩu bị từ chối (AG-01 `test_i5`, đã chứng minh ca thử load-bearing bằng cách gỡ bản vá ra → ca HỎNG); **r29** cấp token mới giết mọi token cũ (trước đó 5 token sống đồng thời 30 phút) |
| **STATIC SERVER** | **PASS** | Danh sách TRẮNG `admin/ pages/ assets/ mock/` + `index.html`; `.py` → 404 đo lại trong `thu_qa2_soat` |
| **AES-GCM BACKUP** | **PASS** | `app/sao_luu_khoa.py` 526 dòng; gói mã hoá ĐỘC LẬP bằng passphrase của người vận hành, **không** dùng chính khoá đang backup; quét byte thô gói tìm bí mật ở 3 dạng (thô/hex/base64) → `dang_bi_lo=[]` |
| **KEY RESTORE** | **PASS (local, cô lập)** · **BLOCKED (production)** | Diễn tập 8 bước có số trong `thu_bao_mat::test_h1`: backup → kiểm toàn vẹn TRƯỚC khi tin gói → khôi phục ở môi trường cô lập THỨ HAI → giải mã lại được credentials + webhook secret. **BLOCKED** vì thiếu passphrase thật do chủ dự án giữ, chỗ cất gói ngoài máy chủ, và một lượt khôi phục thật trên máy chủ sạch |
| **RATE LIMITING** | **PASS** | `app/gioi_han.py` 584 dòng + 34/34 `thu_gioi_han.py`; AG-00 cắm **11 điểm** vào `server.py`. Đo qua HTTP: 40 lượt đăng nhập sai → 429; 14 lượt webhook sai chữ ký → 429 |
| **TENANT ISOLATION** | **PASS** | TEST-011 (đổi resource id không lộ dữ liệu tenant khác) + `thu_qa2_soat::r40` soát tĩnh mọi SQL chạm bảng có `tenant_id`; G04-L2 đưa `tenant_id` thành tham số BẮT BUỘC của `ap_trang_thai_giao` |
| **CARRIER ACCOUNT ISOLATION** | **PASS** | Credentials mã hoá AES-256-GCM với AAD gắn `cred:{tenant_id}:{hang}`; webhook secret AAD gắn `wh:{webhook_ma}` — đổi tenant là giải mã thất bại, không phải đọc được dữ liệu người khác |

---

## ORDER SERVICE

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **ORDER LIFECYCLE** | **PASS** | 5 giá trị `trang_thai` giữ nguyên hợp đồng đóng băng. "Bị từ chối" **không** là giá trị thứ 6 — mô hình hoá là `trang_thai='nhap'` + `ly_do_tu_choi` khác NULL (cố ý, để không phá mọi chỗ đang đọc) |
| **APPROVAL** | **PASS** | Duyệt → `approved_by` + `approved_luc`; từ chối bắt buộc có lý do (thiếu lý do → 400, đo qua HTTP); duyệt lại đơn đã duyệt → 409 |
| **CARRIER INTEGRATION** | **PASS (mock)** | Ba kết quả TÁCH HẲN: ok / hãng-từ-chối / timeout-không-rõ. `createOrder` KHÔNG thử lại trừ khi hãng có khoá chống trùng riêng |
| **IDEMPOTENCY** | **PASS** | Ràng buộc CSDL `UNIQUE(tenant_id, idem_key)` và `UNIQUE(carrier_account_id, event_id)` — chặn ở tầng CSDL, không ở tầng mã. Đo: 15 lượt × 4 luồng gửi đồng thời → hãng bị gọi **đúng 15 lần**, 0 lượt gọi 2 lần, mỗi đơn đúng 1 mã vận đơn |
| **IMPORT-TO-ORDER** | **PASS** | E2E: CSV 3 dòng → `VALID`/`VALID`/`NEEDS_REVIEW` → duyệt 2 dòng → `SUCCESS: 2` → 2 đơn trong CSDL |

---

## WEBHOOK

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **EVENT VERIFICATION** | **PASS** | Sơ đồ chữ ký theo TỪNG hãng (`hub_hmac`, `jt_digest`); chữ ký sai → 401 đo qua HTTP |
| **TENANT RESOLUTION** | **PASS** | Giải từ `webhook_ma` trong URL — chính nó XÁC ĐỊNH tenant, không nhận tenant từ body |
| **DEDUPLICATION** | **PASS** | E2E: gửi lại cùng `event_id` → HTTP 200 `da_nhan_truoc_do`, **1** sự kiện trong CSDL (không phải 2) |
| **DLQ** | **PASS** | 68/68 `thu_webhook.py`; replay có trần `REPLAY_TOI_DA = 5`, có kiểm tenant, có ghi audit |
| **OUT-OF-ORDER** | **PASS** | E2E: sự kiện `cho_lay` (hạng 1) đến SAU `dang_giao` (hạng 3) → trạng thái **vẫn** `dang_giao`, không lùi. Mốc thời gian hãng: **chỉ J&T có** — hãng khác chỉ có rank guard, đã nói đúng phạm vi |
| **J&T STATUS 110** | **PASS (giữ nhập nhằng — cố ý)** | `110` trả `trang_thai_ap=None`, `nhan='AMBIGUOUS'`, `can_soat=True`. Đơn mang mã này **không tiến trạng thái** cho tới khi có người chốt nghĩa kèm căn cứ. Đây là cái giá cố ý chịu: thà đứng còn hơn đi sai hướng |

---

## FRONTEND

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **ORDER UI** | **PASS** | Bộ lọc 9 điều kiện, chi tiết đơn 4 tab, màn từ chối 6 mã lý do, phiếu in tự khai "KHÔNG PHẢI NHÃN VẬN ĐƠN" |
| **IMPORT UI** | **PASS** | Màn ánh xạ cột đã viết, tự bật khi backend có API (hiện chưa có — khai rõ ở `API_CHO_BACKEND`) |
| **TRACKING UI** | **PASS** | Dòng thời gian hai trục; `NEEDS_REVIEW`/`AMBIGUOUS` hiện **nguyên văn** kèm ⚠, không dịch thành trạng thái bình thường |
| **AUTOMATED TESTS** | **PASS (2/3 tầng)** | Tầng 1 logic thuần: **56/56** (`node --test`). Tầng 2 HTTP + tệp tĩnh: **36/36** (máy chủ THẬT). **Tầng 3 (DOM/CSS/bố cục trong trình duyệt thật) CHƯA tự động hoá** — repo cấm thư viện ngoài nên không có Playwright/Puppeteer. `chay.sh` **tự in ra** rằng tầng 3 chưa chạy, để con số gộp không nói rộng hơn phạm vi |

---

## TEST RESULTS

| Loại | Số ca | Kết quả |
|---|---|---|
| **UNIT** | 57 + 34 + 53 + 21 + 63 = **228** | `thu_bao_mat` · `thu_gioi_han` · `thu_g03` · `thu_nhap_file` · `thu_don_hang` — ĐẠT |
| **INTEGRATION** | 21 + 19 + 6 + 68 = **114** | `thu_g01_g02` · `thu_saas` · `thu_tich_hop` · `thu_webhook` — ĐẠT |
| **SECURITY** | 30 + 49 = **79** | `thu_qa_soat` (30) · `thu_qa2_soat` (49, 1 ca `skipped` vì lỗ hổng đã vá nên hết việc) — ĐẠT |
| **FRONTEND** | 56 + 36 = **92** | node tầng 1 · HTTP tầng 2 — ĐẠT. Tầng 3 KHÔNG tính vào đây |
| **REGRESSION** | **430** ca × 2 lượt mỗi bộ | 12 bộ unittest (gồm `thu_gateway` 9) — 0 hỏng |
| **E2E MOCK** | **41** phép đo | `app/thu/chay_e2e.sh` qua HTTP thật trên nền cô lập — 41/41 đạt, mã thoát 0 |

**Tổng: 430 + 56 + 36 + 41 = 563 phép kiểm, 0 hỏng.**

**Phạm vi của con số 563 — nói rõ cái gì NẰM NGOÀI** (`CLAUDE.md` §12.1 luật số "0"):
đo trên **MacBook**, Python 3.9, SQLite, máy chủ bind `127.0.0.1`, **adapter MOCK toàn bộ**.
**Không** phủ: VPS, PostgreSQL, nhiều tiến trình (trần rate limit sống trong bộ nhớ MỘT tiến
trình — 4 worker là trần gấp 4), tầng DOM/CSS trong trình duyệt thật, nhãn vận đơn thật,
credentials hãng thật, Safari/Firefox, thiết bị cảm ứng, trình đọc màn hình, dữ liệu lớn
(đo trên 9 đơn, batch 3 dòng — bảng vài nghìn dòng chưa biết chạy thế nào).

---

## BẢN VÁ CÓ LOAD-BEARING KHÔNG — tự đo, không tin báo cáo

Chỉ thị nói "không tin duy nhất vào báo cáo của Agent". Một ca thử ĐẠT chưa chứng minh gì: nó có
thể đạt vì nó không thật sự kiểm cái nó nói. Phép đo duy nhất đáng tin là **gỡ bản vá ra và xem ca
thử có HỎNG hay không**. AG-00 làm việc đó cho ba bản vá quan trọng nhất, rồi phục hồi nguyên trạng:

| Bản vá | Gỡ ra | Phục hồi |
|---|---|---|
| Chốt "token reset sinh TRƯỚC lần đổi mật khẩu bị từ chối" (AG-01) | `thu_bao_mat::test_i5` **HỎNG** | OK |
| **r29** cấp token mới giết token cũ (AG-00) | `thu_qa2_soat::r29` **HỎNG** | OK |
| **r35** đưa trần vào `WHERE` của một `UPDATE` (AG-00) | `thu_qa2_soat::r35` **HỎNG** | OK |

Ba bản vá đều load-bearing: gỡ ra là ca thử kêu ngay. AG-01 tự báo đã làm phép này cho `test_i5` —
AG-00 **đo lại độc lập** và kết quả khớp.

**Chưa đo load-bearing cho:** r07, r19, r27, r28, r33, r48, G04-L2, G04-L3. Nói đúng phạm vi —
tám bản vá đó chỉ có bằng chứng "ca thử chuyển từ HỎNG sang ĐẠT sau khi vá", chứ chưa có bằng
chứng chiều ngược lại.

---

## MIGRATION

| Hạng mục | Giá trị |
|---|---|
| **PREVIOUS VERSION** | 6 |
| **FINAL VERSION** | 7 |
| **Nội dung v7** | `don_hang` +14 cột · bảng MỚI `don_mat_hang` · `wh_su_kien` +9 cột · bảng MỚI `han_muc_nhap_thang` · 5 chỉ mục. **TOÀN BỘ là thao tác THÊM** — không `DROP`, không `DELETE`, không `UPDATE` dữ liệu sẵn có, không đổi kiểu hay ràng buộc cột cũ |
| **BACKUP VERIFIED** | **PASS** — thử trên **BẢN SAO trước**: 202 dòng giữ nguyên, `integrity_check: ok`. Rồi chạy thật: 6→7, **0 dòng mất**, `integrity_check: ok`, bản sao ở `app/du-lieu/sao-luu/hub-truoc-migrate-20261015-003910.db` (200 704 byte) |
| **RESTORE VERIFIED** | **PASS** — chạy `--rollback` trên bản sao: schema 7→**6**, `don_hang` 40→**26** cột, `don_mat_hang` **mất đúng như mong**, 202 dòng, `integrity_check: ok`, đơn cũ `T1-000001`/`T1-000002` đọc được. Chính lượt lùi **cất lại** bản trước khi lùi (§19 — không xoá cứng). CSDL thật **không bị đụng** (đo lại: vẫn v7) |

---

## GIT

| Hạng mục | Giá trị |
|---|---|
| **AGENT COMMITS** | `c52f8f1` AG-01 · `c43bed2` AG-02 · `48d04f9` AG-03 · `fb39fe3` AG-04 · `0efd291` AG-05 |
| **INTEGRATION COMMITS** | `8270f03` (sửa ca chập chờn) · `71fc2cd` · `6e7b194` · `7f7c6dc` · `88b491e` · `4461fb0` (5 lượt gộp) · `f449f33` (WAVE 2) · `5caa68f` (WAVE 3) · `ae2be33` (tài liệu) · `599dd08` (sửa dải mã việc) |
| **FINAL MAIN SHA** | `599dd08` |
| **REMOTE PUSH** | **NO** — không có remote nào được cấu hình, nên không có đường push kể cả vô ý |
| **FILES CHANGED** | 40 file, +12 747 / −304 dòng (so với `fd7c545`) |
| **Xung đột khi gộp** | 0 — nhờ bảng quyền sở hữu file đóng băng ở WAVE 0 |

---

## LOCAL ACCEPTANCE
**PASS** — 563/563 phép kiểm đạt trên MacBook, trong phạm vi đã nêu ở mục TEST RESULTS.

## LIVE CARRIER ACCEPTANCE
**BLOCKED — CREDENTIALS NOT APPROVED.**
Cả 5 hãng đang `CHO_PHEP_LIVE=False` (chốt cứng trong mã, không phải cờ cấu hình). Chưa gọi API
thật lượt nào. Chưa tạo đơn vận chuyển thật nào. Chủ dự án đã chốt: credentials J&T cấp **khi bắt
đầu kiểm thử LIVE**, chưa phải lúc này.

## PRODUCTION READINESS
**NOT READY.** Lý do cụ thể, không nói chung:
1. Trần rate limit sống trong bộ nhớ MỘT tiến trình — nhiều worker là trần nhân lên theo số worker.
2. Khoá mã hoá vẫn là tệp trên đĩa; `KMSSecretProvider` còn là giao diện rỗng (cố ý).
3. Chưa có lượt khôi phục khoá thật trên máy chủ sạch, và gói khoá **chưa nằm trong phạm vi VIP Vault** — tức là **chưa có bản ngoài nhà**.
4. Chưa đo trên PostgreSQL, chưa đo sau proxy thật (Caddy/nginx).
5. Tầng DOM/CSS chưa có chặn hồi quy chạy-lại-được.
6. Chưa đo với dữ liệu lớn.

---

## BLOCKERS

| # | Blocker | Cần gì để mở |
|---|---|---|
| B-1 | Kiểm thử LIVE với J&T / Viettel Post | Credentials sandbox thật + chủ dự án duyệt từng lượt |
| B-2 | Khôi phục khoá ở production | Passphrase thật do chủ dự án giữ; chỗ cất gói ngoài máy chủ; một lượt khôi phục thật trên máy chủ sạch |
| B-3 | Nghĩa của mã J&T `110` | Căn cứ từ hãng (tài liệu hoặc xác nhận của hãng). Hệ **không đoán** — đơn mang mã này đứng tại chỗ |
| B-4 | Chữ ký `jt_digest` | Mức DOCUMENTED, chưa ai ký thật thử vì chưa có sandbox |
| B-5 | Chữ ký webhook Viettel Post | **BLOCKED** ở môi trường thật — tài liệu công khai không nói rõ. Không bịa cách ký |

## UNRESOLVED RISKS

| # | Rủi ro | Mức | Ghi chú |
|---|---|---|---|
| R-a | Trần rate limit trong bộ nhớ một tiến trình: restart là mất bộ đếm; nhiều worker là trần nhân lên | TRUNG BÌNH | Chặn được lạm dụng tự động, **không** chặn tấn công phân tán, **không thay WAF** |
| R-b | `_doc_json` chỉ đóng lớp list/dict ở chỗ chờ vô hướng. **CHƯA đóng**: số ở chỗ chờ chuỗi (`ten=5` vẫn làm `.strip()` nổ) và kiểu sai ở tầng sâu trong một khoá đã khai | THẤP | Việc **V-13904** |
| R-c | Mã lý do từ chối lưu trong chuỗi `ly_do_tu_choi`, **không truy vấn được như dữ liệu có cấu trúc** | THẤP | Muốn thống kê "bao nhiêu đơn bị từ chối vì sai địa chỉ" thì phải thêm cột. Việc **V-13905** |
| R-d | Tầng 3 frontend không có chặn hồi quy | TRUNG BÌNH | Muốn có thì phải nới ràng buộc "không thư viện ngoài" — **quyết định của chủ dự án** |
| R-e | Bộ lọc nâng cao lọc TẠI GIAO DIỆN trên tập đã tải — CSDL lớn thì lọc thiếu | TRUNG BÌNH | Giao diện nói rõ phạm vi và cảnh báo khi chạm trần, nhưng đó là **vá bằng lời, không phải vá bằng cấu trúc**. Vá gốc = thêm tham số lọc cho `GET /api/v2/don` |
| R-f | `NGHIA_DA_CHOT` sống trong tiến trình, chưa có bảng CSDL | THẤP | Nhiều tiến trình phải chốt riêng. Khi cần chốt thật thì thêm bảng và nạp lúc khởi động |
| R-g | `don_hang.tao_don` không gọi hạn mức nào — hạn mức nhập chặn ở tầng endpoint import, nên đường nào khác gọi `tao_don` hàng loạt sẽ lọt | THẤP | AG-01 ghi ra, chưa vá |
| R-h | `ban_ma[]` của gói backup khoá **chỉ phủ `carrier_accounts`** | THẤP | Bảng mới có secret phải thêm vào CẢ `sao_luu_khoa` VÀ `ma_hoa_lai_carrier_accounts` VÀ bộ thử |
| R-i | `.gitignore` chưa chặn `*.vipkb` | THẤP | **Cố ý không thêm**: mã hiện TỪ CHỐI ghi gói khoá vào mọi chỗ trong repo mà gitignore không chặn — đó là lớp MẠNH HƠN. Thêm vào gitignore sẽ làm yếu đi và làm ca `h6` của AG-01 hỏng |

## OWNER DECISIONS — cần chủ dự án quyết

| # | Việc cần quyết | Vì sao AG-00 không tự quyết |
|---|---|---|
| D-1 | Có nới ràng buộc "không thư viện ngoài" để tự động hoá tầng 3 frontend? | Đổi nguyên tắc kiến trúc của dự án |
| D-2 | Có mở `POST /api/v2/platform/khoa/xoay` (chỉ PLATFORM_OWNER)? | AG-01 khuyến nghị MỞ cái này, nhưng **KHÔNG mở** cửa HTTP cho sao lưu khoá — passphrase sẽ đi qua body, vào log, vào bộ nhớ tiến trình web |
| D-3 | Gói khoá có đưa vào phạm vi VIP Vault không? | Chạm hệ sao lưu đang chạy; `CLAUDE.md` §18 nói chuỗi đêm Mac mini đã tắt từ 27/09 |
| D-4 | Mở cửa HTTP chốt nghĩa mã nhập nhằng (J&T `110`)? Ai được chốt? | Một tenant **không** được định nghĩa lại nghĩa mã của hãng cho cả hệ thống. AG-03 đề xuất cửa PLATFORM_OWNER |
| D-5 | Khi nào cấp credentials sandbox J&T để bắt đầu kiểm thử LIVE? | Chủ dự án đã chốt "khi bắt đầu kiểm thử LIVE" — cần mốc cụ thể |

## NEXT ACTIONS — theo thứ tự phụ thuộc

1. **Thêm tham số lọc cho `GET /api/v2/don`** (R-e) — đây là rủi ro TRUNG BÌNH duy nhất vá được hoàn toàn bằng mã, không cần chủ dự án quyết.
2. **Mở `GET /api/v2/billing/han-muc-nhap`** (AG-01 đề xuất) để người vận hành thấy hạn mức nhập còn bao nhiêu.
3. **Mở 4 đường còn khai CHỜ BACKEND**: `GET /webhook/su-kien/<id>` · `GET/PUT /import/<id>/anh-xa-cot` · `GET /import/tong-hop` · `POST /tai-khoan-hang/<id>/kiem-ket-noi`.
4. **Vá R-b và R-c** (hai việc nhỏ đã có mã việc).
5. Chờ **D-1** để làm tầng 3 frontend; chờ **D-5** để bắt đầu LIVE.

---

## TEST COMMANDS — chạy lại được nguyên văn

```sh
cd ~/Projects/vip-express-hub

# 12 bộ unittest (430 ca)
for t in app/thu/thu_bao_mat.py app/thu/thu_gioi_han.py app/thu/thu_g01_g02.py \
         app/thu/thu_g03.py app/thu/thu_saas.py app/thu/thu_nhap_file.py \
         app/thu/thu_qa_soat.py app/thu/thu_tich_hop.py app/thu/thu_don_hang.py \
         app/thu/thu_webhook.py app/thu/thu_qa2_soat.py gateway/thu/thu_gateway.py; do
  echo "== $t"; python3 "$t" 2>&1 | tail -3
done

# frontend tầng 1 + 2 (56 + 36 ca) — tự in ra rằng tầng 3 chưa chạy
sh thu_frontend/chay.sh

# E2E qua HTTP thật trên nền cô lập (41 phép đo)
sh app/thu/chay_e2e.sh

# migration: kiểm phiên bản, không ghi gì
python3 app/migrate.py --kiem
```

## ROLLBACK PLAN

| Muốn lùi gì | Lệnh | Đã đo chưa |
|---|---|---|
| **CSDL về v6** | `python3 app/migrate.py --rollback app/du-lieu/sao-luu/hub-truoc-migrate-20261015-003910.db` | **ĐÃ ĐO trên bản sao**: 7→6, 40→26 cột, 202 dòng, `integrity_check: ok`. Lượt lùi tự cất bản trước khi lùi |
| **Mã về trước đợt này** | `git reset --hard fd7c545` | Chưa cần dùng. 5 nhánh agent và mọi commit tích hợp đều còn, không nhánh nào bị xoá |
| **Mã về sau WAVE 2** | `git reset --hard f449f33` | — |
| **Mã về sau WAVE 3** | `git reset --hard 5caa68f` | — |
| **Khoá mã hoá** | `python3 app/sao_luu_khoa.py khoi-phuc <gói.vipkb> <thư-mục-đích> [--ghi-de]` — passphrase lấy từ `VIP_HUB_BACKUP_PASSPHRASE` hoặc nhập lúc chạy. Kiểm gói TRƯỚC bằng `kiem <gói.vipkb>` | ĐÃ ĐO trong môi trường cô lập; **CHƯA ĐO** trên máy chủ thật (B-2) |

**Không dùng `force reset` để loại mã lỗi** — chỉ thị cấm, và không có lượt nào cần dùng.
