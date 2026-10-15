# BÁO CÁO NGHIỆM THU — WAVE 3 (G07 → G11)

> Định dạng theo mục 15 chỉ thị của chủ dự án. Mọi con số là **số đo**, lấy từ lệnh đã chạy
> trên MacBook ngày **15/10/2026**. Chỗ nào chưa đo thì ghi thẳng là chưa đo (`CLAUDE.md`
> §12.1 luật 4 và luật số "0").

## PROJECT
VIP EXPRESS HUB · `~/Projects/vip-express-hub`

## STARTING SHA
`31a321f` — chủ dự án báo. AG-00 tự kiểm: khớp HEAD thật, cây sạch, 0 commit lạ, 0 worktree cũ.

## FINAL LOCAL SHA
**Commit MÃ cuối cùng: `be25413`.** Sau nó chỉ còn commit **tài liệu** (gồm chính dòng này) —
một commit không thể chứa SHA của chính nó, nên con số viết cứng sẽ luôn lạc một commit. Lấy
số thật:

```sh
cd ~/Projects/vip-express-hub && git rev-parse HEAD
git log --oneline be25413..HEAD --name-only | grep -E '^(app|gateway|admin|thu_frontend|trien_khai)/'
```

Lệnh thứ hai in ra rỗng nghĩa là báo cáo còn hiệu lực. In ra file mã nào thì phải chạy lại bộ
thử trước khi tin các con số dưới đây.

## BRANCH
`main` (local). **0 git remote** — không có đường push, kể cả vô ý.

## AG-00 CONTROLLER
Đóng băng hợp đồng · gộp 5 nhánh · migration v8 · cắm 44 route · 10 bản vá · 3 bộ thử mới.

| Agent | Nhánh | SHA | Bàn giao | AG-00 tự kiểm |
|---|---|---|---|---|
| **AG-01 FINANCE** | `agent/g07-finance` | `d3a7d03` | xong | 6 file mới, 0 file cũ bị sửa |
| **AG-02 BILLING** | `agent/g08-billing` | `7db6b59` | xong | 6 file mới, 0 file cũ bị sửa |
| **AG-03 CARRIER** | `agent/g09-carrier` | `9953fa5` | xong | 8 file mới, 0 file cũ bị sửa |
| **AG-04 AI** | `agent/g10-ai` | `fb73262` | xong | 5 file mới, 0 file cũ bị sửa |
| **AG-05 DEVOPS** | `agent/g11-devops` | `be82b0d` | xong | 15 file mới, 0 file cũ bị sửa |

**Chạy song song — nói đúng sự thật:** 5 agent được phóng cùng một lượt và thực sự chạy đồng
thời như 5 tiến trình nền, mỗi agent một git worktree riêng. Thời gian hoàn thành lệch nhau
(AG-02 xong trước ~6 phút, AG-05/AG-04 xong sau), nên AG-00 gộp theo thứ tự phụ thuộc.

**Soát của AG-00 trên công việc của agent là AI-ASSISTED CONTROLLER VERIFICATION** — AI kiểm
AI. **KHÔNG phải independent human review.** Không ai trong chuỗi này là người.

---

## EXISTING GATES — có bị hồi quy không

| Gate | Trạng thái | Căn cứ |
|---|---|---|
| G01 MULTI-TENANT | **PASS** | 21/21 `thu_g01_g02` (TEST-001…015) |
| G02 AUTH + RBAC | **PASS** | 57/57 `thu_bao_mat` |
| G03 CARRIER ENGINE | **PASS (mock)** | 53/53 `thu_g03` |
| G04 ORDER SERVICE | **PASS** | 63/63 `thu_don_hang` |
| G05 IMPORT ENGINE | **PASS** | 21/21 `thu_nhap_file` |
| G06 WEBHOOK | **PASS** | 68/68 `thu_webhook` |

**0 hồi quy.** Hai ca thử của G07 từng hỏng trong lượt tích hợp — cả hai là **ca thử khoá
chiều tiến bộ**, không phải lỗi sản phẩm (xem mục "ca thử tự nó sai" dưới).

## NEW GATES

| Gate | Trạng thái | Căn cứ đo |
|---|---|---|
| **G07 COD & ĐỐI SOÁT** | **PASS (local)** | 51/51 `thu_tai_chinh` + 27/27 `thu_doi_soat`; 13 bảng, 4 trigger bất biến; 18 route đo qua HTTP thật 20/20 |
| **G08 SaaS BILLING** | **PASS (local)** | 37/37 `thu_goi_dich_vu` + 41/41 `thu_usage`; 9 bảng; 11 route đo qua HTTP |
| **G09 CARRIER LOCAL** | **PASS** | 57/57 `thu_harness_hang` + 95 ca harness MOCK (0 hỏng, 3 bỏ qua); 2 route |
| **G09 SANDBOX** | **BLOCKED** | thiếu `customerCode`+`password` sandbox J&T (chỉ bưu cục hợp tác cấp được) · `V-13906-05` chưa cấp |
| **G09 LIVE** | **BLOCKED** | `V-G09-01` chưa cấp · `CHO_PHEP_LIVE=False` chốt cứng cả 5 hãng · thiếu danh mục địa danh |
| **G10 AI GATEWAY LOCAL** | **PASS** | 87/87 `thu_ai_job`; 9 route đo qua HTTP; 3 phép đo chứng minh không có lượt gọi mạng nào |
| **G10 REAL CONNECTION** | **BLOCKED** | `V-G10-01` chưa cấp · **chưa có hợp đồng kết nối nào** (không endpoint, không dạng xác thực, không schema) |
| **G11 LOCAL READINESS** | **PASS một phần** | 45/45 `thu_quan_sat`; diễn tập khôi phục mã thoát 0; 2 route sức khoẻ. **Docker build/compose = BLOCKED** |
| **G11 STAGING** | **BLOCKED** | `V-G11-01` chưa cấp |
| **G11 PRODUCTION** | **NOT ASSESSED** | chưa đánh giá, và chưa nên đánh giá |

---

## TESTS

| Loại | Số ca |
|---|---|
| **BASELINE** (đầu đợt 3) | **563** (430 python + 56 node + 36 HTTP + 41 E2E) |
| **MỚI của đợt 3** | **364** |
| → G07 | 51 + 27 = **78** |
| → G08 | 37 + 41 = **78** |
| → G09 | **57** (+ 95 ca harness, không tính vào tổng vì `thu_harness_hang` đã bao) |
| → G10 | **87** |
| → G11 | **45** |
| → AG-00 | 5 hạn mức nguyên tử + 6 mã lạ + 8 header bảo mật = **19** |
| **TOTAL PASSED** | **927** (794 python / 22 bộ + 56 node + 36 HTTP frontend + 41 E2E) |
| **TOTAL FAILED** | **0** |
| **TOTAL SKIPPED** | **1** (`thu_qa2_soat` — một ca hết việc vì lỗ hổng đã vá) |

**PHẠM VI của con số 927 — cái gì NẰM NGOÀI** (§12.1 luật số "0"):
đo trên **MacBook**, Darwin arm64, Python 3.9.6, SQLite 3.51.0, **một tiến trình**, máy chủ
bind `127.0.0.1`, **adapter MOCK toàn bộ** (`CHO_PHEP_LIVE=False` cả 5 hãng), **AI mock toàn
bộ** (`MOCK=True` + khoá thứ hai `DA_DUYET_NOI_THAT=False`).

**KHÔNG phủ:** VPS · PostgreSQL · **Docker** (chưa cài trên máy này) · nhiều tiến trình (trần
rate limit sống trong bộ nhớ MỘT tiến trình) · tầng DOM/CSS trong trình duyệt thật · nhãn vận
đơn thật · credentials hãng thật · mô hình AI thật · dữ liệu lớn · Safari/Firefox · giao dịch
ngân hàng · HTTPS thật · proxy thật.

---

## SECURITY

| Hạng mục | Trạng thái | Đo bằng gì |
|---|---|---|
| **TENANT ISOLATION** | **PASS** | TEST-011 · `thu_qa2_soat::r40` soát tĩnh mọi SQL chạm bảng có `tenant_id` · G10 có 8 ca cách ly tenant cho AIJob · `ap_trang_thai_giao` nhận `tenant_id` bắt buộc |
| **RBAC** | **PASS** | 6 vai trò, 24 quyền trong CSDL · `thu_qa2_soat::r41` đòi mọi nhánh API tenant đều tra quyền |
| **CREDENTIAL SECURITY** | **PASS (local)** | AES-256-GCM + AAD · gói backup khoá mã hoá độc lập bằng passphrase người vận hành · diễn tập khôi phục mã thoát 0 · quét byte thô gói tìm bí mật 3 dạng → rỗng |
| **FINANCIAL INTEGRITY** | **PASS** | Tiền là `INTEGER` đồng, **0 cột REAL/FLOAT** trong 27 bảng mới · 4 trigger bất biến **đo được là chặn thật** (chèn bút toán hợp lệ rồi thử UPDATE/DELETE → cả hai bị chặn, số dòng không đổi) · import đối soát idempotent bằng `UNIQUE(...van_tay_dong)` |
| **BILLING INTEGRITY** | **PASS** | 4 chốt hạn mức đều nguyên tử (đo: 8 luồng tranh 1 suất → đúng 1 qua) · `UNIQUE(tenant_id, idem_key)` ở tầng CSDL · phiên bản gói đã ghim được tôn trọng |
| **AI DATA ISOLATION** | **PASS (mock)** | `tenant_id` từ phiên không từ body · kết quả AI là dữ liệu không phải lệnh (`loc_khoa_lenh` quét 40 khoá nghi lệnh) · 14 mẫu tiêm prompt × 2 đường · 12 mẫu bí mật × 3 dạng → prompt sạch |

### Lỗ hổng tìm được và đã vá trong đợt này

| # | Lỗ hổng | Đo được | Ai tìm |
|---|---|---|---|
| 1 | `kiem_va_tang_ai` đọc-rồi-ghi | **28/40 lượt vượt trần**, `so_ai` cao nhất 30/20 | AG-02 |
| 2 | `kiem_han_muc_tai_khoan_hang` đọc-rồi-ghi | **12/12 luồng qua, 12 tài khoản trên trần 1** | AG-00 |
| 3 | `kiem_han_muc_nhan_vien` cùng khuôn | không tái hiện (khoá ghi tình cờ che) — **không tái hiện KHÔNG PHẢI an toàn** | AG-00 |
| 4 | Phiên bản gói bị bỏ qua ở chốt chặn thật | ghim v1 mà áp trần v2 (50 → 9999) | AG-02 |
| 5 | `.env` không bị gitignore chặn | `git status` cho `?? .env` | AG-05 |
| 6 | `sao_luu()` ghi đè im lặng | 2 lượt cùng giây → **1 file** trên đĩa | AG-05 |
| 7 | **0 header bảo mật** | `curl -D -` chỉ thấy `Server/Date/Content-*/Cache-Control` | AG-05 |
| 8 | bind ghim cứng `127.0.0.1` | trong container không ai gọi được từ ngoài | AG-05 |
| 9 | **COD của J&T gán vào `itemsValue`** thay vì `codMoney` | đọc mã; `itemsValue` không có trong bảng tham số ⇒ hãng **không biết phải thu COD** | AG-03 |
| 10 | `prov`/`area` của J&T gửi chuỗi rỗng dù bắt buộc | đọc mã; 4 cột dữ liệu đã có từ v7, chưa ai nối | AG-03 |

Lỗ hổng 9 là nặng nhất về hậu quả nghiệp vụ: nếu đơn lọt qua thì **hàng đi, tiền không về, và
không có lỗi nào báo**.

### Việc CỐ Ý KHÔNG vá, kèm lý do

**Bộ mã J&T thứ hai** (`10`/`50`/`92`/`94`/`100`). AG-03 đọc tài liệu bằng trình duyệt thật và
thấy ví dụ trả lời dùng bộ mã khác bảng tham số. Mã `100` = "Ký nhận" (đã giao) **không có**
trong bảng, nên đơn đã giao **không về `giao_thanh_cong`**.

AG-00 **không thêm** năm mã đó: làm vậy là đoán nghĩa khi chưa có văn bản của hãng — chính là
**V-13906-04**, quyết định của chủ dự án, chưa cấp. Thà đơn đứng chờ người xử còn hơn hệ tự
tuyên bố "đã giao" rồi để đối soát COD áp tiền theo một dữ kiện chưa chắc.

AG-00 cũng **sửa mô tả của AG-03**: AG-03 viết mã `100` *"không báo lỗi gì"* — **nói quá**. Đo
được: mã lạ ra `can_soat=True` + `do_tin_cay='ma_la'`, và cột `can_soat` đã phơi ra cửa
`?can_soat=1` từ đợt 2. Nên nó **được nêu ra**, chỉ là không tự tiến trạng thái. "Mất im lặng"
và "đứng chờ người xử, có chỗ tra" là hai câu khác nhau. Hành vi hiện tại đã được khoá bằng 6
ca thử (`thu_ma_la_hang.py`).

---

## DATABASE

| Hạng mục | Giá trị |
|---|---|
| **CURRENT MIGRATION** | **v8** (từ v7) |
| **Nội dung v8** | **27 bảng · 21 index · 4 trigger**. Đo sau khi **bỏ lời bình trước khi quét**: 0 DROP · 0 ALTER · 0 DELETE ngoài trigger · 0 cột REAL/FLOAT · 0 trùng tên (cả giữa các agent và với 23 bảng đang có) |
| **Không viết lại DDL** | migration CHẠY ĐÚNG CHUỖI trong module của từng agent. Chép sang `migrate.py` là tạo bản thứ hai, và hai bản nội dung là hai bản sẽ lệch nhau — lúc đó bộ thử của agent chạy một chuỗi còn CSDL thật mang một chuỗi khác |
| **BACKUP VERIFIED** | **PASS** — thử trên **bản sao trước**, rồi chạy thật: 23→50 bảng, **204 dòng, 0 dòng mất**, `integrity_check: ok`, `foreign_key_check` 0 vi phạm, 3 gói `free/basic/pro` nguyên vẹn, đơn cũ `T1-000001`/`T1-000002` đọc được |
| **RESTORE VERIFIED** | **PASS (local)** — `migrate.py --rollback` đo ở đợt 2 trên bản sao: schema lùi đúng, số cột lùi đúng, số dòng giữ nguyên. AG-05 diễn tập khôi phục 12 bước, mã thoát 0, và đo riêng **cả hai** đường giải mã (`giai_ma_cred` + `giai_ma_wh`) vì số dòng khớp KHÔNG chứng minh khôi phục thành công — CSDL về đủ mà khoá lệch thì credentials thành rác và không gì báo tới lượt gọi hãng đầu tiên |
| **ROLLBACK VERIFIED** | **PASS (local)** — AG-05 thêm tenant sau mốc backup rồi `--rollback`: dòng đó **mất đúng như mong đợi** |
| **Sao lưu trên đĩa** | 9 bản |

---

## GIT

| Hạng mục | Giá trị |
|---|---|
| **AGENT COMMITS** | `d3a7d03` · `7db6b59` · `9953fa5` · `fb73262` · `be82b0d` |
| **INTEGRATION COMMITS** | `143084b` (đóng băng) · `6887304` (bộ chạy thử) · `0348c51` (hạn mức) · `9e8dbae` (mã lạ) · `d0f4986` (gộp + v8) · `ec83a3d` (P-1…P-4) · `397ba4c` (47 route) · `be25413` (5 bản vá) |
| **FINAL MAIN SHA** | `be25413` (mã) |
| **PUSHED REMOTE** | **NO** — 0 remote |
| **FILES CHANGED** | 55 file · +18 090 / −59 dòng (so với `31a321f`) |
| **Xung đột khi gộp** | **0** — nhờ bảng quyền sở hữu file đóng băng ở WAVE 0 |

---

## BLOCKERS

| # | Việc | Thiếu CHÍNH XÁC cái gì |
|---|---|---|
| B-1 | Gọi API hãng (sandbox/live) | `V-G09-01` chưa cấp |
| B-2 | Credentials sandbox J&T | `customerCode`+`password` — **chỉ bưu cục hợp tác cấp được**, không có trên trang tài liệu (`V-13906-05`) |
| B-3 | `apiAccount`+`privateKey` riêng cho dự án | lấy trong 控制台 **sau 开发者认证** — bước này cần người của J&T |
| B-4 | Nghĩa mã J&T `110` | văn bản trả lời của hãng (`V-13906-04`) |
| B-5 | Bộ mã J&T thứ hai | xác nhận có hai bộ `scanTypeCode` và bộ nào áp cho VN |
| B-6 | Khoá ký callback J&T | tài liệu không nói callback ký bằng khoá nào |
| B-7 | Trần tần suất J&T | tài liệu công khai **không công bố** |
| B-8 | Nhãn vận đơn VTP | **chưa tìm được trang tài liệu nào** |
| B-9 | Bảng mã lỗi VTP | `"vtp" in loi_hang.BANG_MA_LOI` → `False` |
| B-10 | API tra vận đơn VTP | ⇒ đơn VTP "không rõ kết quả" **chỉ người mới đối soát được** |
| B-11 | Danh mục địa danh hai hãng | **không có thì không tạo nổi một đơn nào** |
| B-12 | Nối VIP AI Brain | **chưa có hợp đồng kết nối nào** — 6 nhóm điều kiện ở `docs/G10_FINAL_REPORT.md` (`V-G10-01`) |
| B-13 | Docker build + compose | **một máy có Docker** — `docker --version` → `command not found` |
| B-14 | Triển khai staging | `V-G11-01` chưa cấp |
| B-15 | Xoay khoá thật | `V-13906-02` chưa cấp |
| B-16 | Gói khoá có bản ngoài máy | `V-13906-03` chưa cấp ⇒ gói nằm **cùng máy** với CSDL nó bảo vệ, mất ổ là mất cả hai |
| B-17 | Tự động hoá tầng 3 frontend | `V-13906-01` chưa cấp (cần nới ràng buộc "không thư viện ngoài") |

---

## OWNER DECISIONS — cần chủ dự án quyết

| # | Việc | Vì sao AG-00 không tự quyết |
|---|---|---|
| D-1 | Nới ràng buộc "không thư viện ngoài" để tự động hoá kiểm giao diện? | Đổi nguyên tắc kiến trúc dự án |
| D-2 | Mở `POST /platform/khoa/xoay`? | AG-01 khuyến nghị MỞ cái này, nhưng **KHÔNG** mở cửa HTTP cho sao lưu khoá — passphrase sẽ đi qua body, vào log |
| D-3 | Gói khoá vào VIP Vault? | Chạm hệ sao lưu đang chạy |
| D-4 | Nghĩa mã J&T `110` + bộ mã thứ hai: ai được chốt? | Một tenant **không** được định nghĩa lại nghĩa mã của hãng cho cả hệ thống |
| D-5 | Khi nào cấp credentials sandbox J&T? | — |
| D-6 | **Giá bán thực tế của 4 gói** | AG-02 **chưa điền giá cho gói nào** — giá là quyết định kinh doanh |
| D-7 | Quyền tài chính riêng (`tenant.taichinh.xem/ghi/duyet`)? | Hiện ai duyệt đơn thì duyệt được cả đối soát tiền — hai việc nên tách (V-13908) |
| D-8 | Có chuyển SQLite → PostgreSQL? | AG-05 **không đề xuất chuyển** và nêu ba dấu hiệu sẽ cần; chuyển CSDL khi chưa chạy nổi một container là đổi thứ chưa đo để chữa bệnh chưa chẩn đoán |
| D-9 | `area` của J&T lấy từ **quận/huyện** hay **xã/phường**? | Hệ có 3 cấp, J&T có 2. AG-00 **giả định quận/huyện** và ghi rõ là giả định; hãng xác nhận khác thì đổi một dòng |

---

## NEXT ACTIONS — theo thứ tự, không cần chờ anh quyết

1. **Mở `POST /billing/du-thao`** sau khi thêm quyền `tenant.billing.lap_du_thao` (V-13909) — hiện cố ý chưa cắm vì dùng quyền XEM cho một lệnh GHI là nới quyền im lặng.
2. **Thêm quyền tài chính riêng** (V-13908) — `QUYEN_TC` của AG-01 đã ưu tiên quyền riêng nên **không cần sửa dòng mã nào**.
3. **Thêm tham số lọc cho `GET /api/v2/don`** — rủi ro còn lại từ đợt 2, bộ lọc nâng cao hiện lọc tại giao diện.
4. **4 đường còn khai CHỜ BACKEND** của `admin/logic.js`.
5. **Cập nhật bản clone `~/code/vip-viettelpost`** lên `origin/main` (đi sau **174 commit**) và đính chính `docs/VIETTELPOST_REUSE_AUDIT.md` — toàn bộ kết luận cũ đo trên bản clone sai.
6. **Gửi `docs/JT_CAU_HOI_CHINH_THUC.md`** (29 câu) cho J&T — câu 1–5 chặn nhiều việc nhất.

---

## TEST COMMANDS

```sh
cd ~/Projects/vip-express-hub

# TẤT CẢ: 22 bộ python (tự dò) + 2 tầng frontend + E2E, kèm in PHẠM VI
sh app/thu/chay_tat_ca.sh

# riêng E2E qua HTTP thật trên nền cô lập
sh app/thu/chay_e2e.sh

# harness hãng, chế độ MOCK (mặc định; SANDBOX/LIVE đòi phiếu duyệt riêng)
python3 app/harness_hang.py

# diễn tập khôi phục trên thư mục tạm (TỪ CHỐI chạy nếu trỏ vào repo thật)
sh trien_khai/dien_tap_khoi_phuc.sh

# migration: kiểm phiên bản, không ghi gì
python3 app/migrate.py --kiem
```

## ROLLBACK

| Lùi gì | Lệnh | Đã đo chưa |
|---|---|---|
| CSDL về v7 | `python3 app/migrate.py --rollback app/du-lieu/sao-luu/hub-truoc-migrate-20261015-070440.db` | ĐÃ ĐO đường lùi ở đợt 2 trên bản sao |
| Mã về trước đợt 3 | `git reset --hard 31a321f` | chưa cần dùng; 5 nhánh agent và mọi commit tích hợp đều còn |
| Mã về sau khi gộp | `git reset --hard d0f4986` | — |
| Khoá mã hoá | `python3 app/sao_luu_khoa.py khoi-phuc <gói.vipkb> <thư-mục-đích> [--ghi-de]` | ĐÃ ĐO trong môi trường cô lập; **CHƯA ĐO** trên máy chủ sạch (B-16) |

**Không dùng `force reset` để loại mã lỗi** — chỉ thị cấm, và không lượt nào cần.
