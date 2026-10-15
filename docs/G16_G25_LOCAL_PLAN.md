# G16 → G25 — KẾ HOẠCH LOCAL (ĐỀ XUẤT), chưa phải yêu cầu đã chốt

> **ĐỌC DÒNG NÀY TRƯỚC.** `G17`–`G25` **KHÔNG được định nghĩa ở đâu trong repo này.** Đo được:
> `grep -rn "G17\|G18\|…\|G25" docs/` → **0**; mốc G lớn nhất trong `docs/` là **G16**.
> Tài liệu này là **ĐỀ XUẤT LOCAL của AG-00** dựng từ **backlog đã có thật** trong repo
> (`docs/BAN_GIAO.md` §6, `docs/QA_G13_G15.md` §L2.8, `docs/G16_ACCEPTANCE.md` §8,
> `docs/SHARED_CONTRACTS.md` §25), **không phải yêu cầu cũ được khôi phục**.
> Mục nào không có nguồn trong repo thì ghi rõ **"(đề xuất mới)"**.
> **Anh Thành / Codex chốt lại thì tài liệu này mới thành yêu cầu.**

**Ngày:** 15/10/2026 · **Controller:** AG-00 (DeepSeek, `dsh`, trong Orca)
**Nền:** `integration/g16` @ `98baeb3` · **`main` giữ nguyên `de740dc`** · **Orca Run:** `run_695b048104a9`

---

## 0. NGUỒN CỦA TỪNG MỤC — để không ai đọc nhầm là yêu cầu cũ

| Mục | Nguồn thật trong repo |
|---|---|
| G16 đã đóng | `docs/G16_ACCEPTANCE.md` — 3 cổng ĐẠT, 1 BLOCKED (sandbox), 1 NOT AUTHORIZED (production) |
| Việc còn nợ G01–G15 | `docs/BAN_GIAO.md` §6.1 (`V-13912`★ · `V-13914` · route `truy_van.py` + `DDL_G12Q` vào migration v9 · 21 mã VTP · `P-3`/`P-4`) |
| Ba cổng **CHƯA đo** | `docs/QA_G13_G15.md` §L2.8 + `docs/G16_ACCEPTANCE.md` §8: cách ly tenant **toàn cục** · **RBAC** · **AES-256-GCM đầy đủ** |
| Bảy mục CHƯA đo của G16 | `docs/G16_ACCEPTANCE.md` §8 (AG-01 lập, AG-00 giữ nguyên) |
| Chưa được cấp quyền | `docs/SHARED_CONTRACTS.md` §25 + §37 |

---

## 1. WAVE G17 — "ĐÓNG NỢ ĐO LƯỜNG" (đang chạy)

**Chủ đề chung:** G16 đã dựng **lớp HTTP thật đầu tiên** và ba cổng đã ĐẠT. Wave này **không thêm
tính năng mới** — nó **trả lời những câu G16 cố ý để mở**, và biến "chưa đo" thành "đã đo".

| Làn | Việc | Worktree / nhánh | Nguồn |
|---|---|---|---|
| **AG-01** | **QA**: kế hoạch + bộ thử độc lập G17 **trên nền đóng băng**, rồi nghiệm thu sau khi gộp | `g17-ag01-qa` | `QA_G13_G15.md` §6.3 |
| **AG-02** | **Transport**: chịu tải **đồng thời**, **hết giờ** nhiều tầng, **che bí mật** (redaction) | `g17-ag02-transport` | `G16_ACCEPTANCE.md` §8 mục 4 |
| **AG-03** | **Hợp đồng nghiệp vụ**: ca **phủ định** ở mock; **giữ KHOÁ** mọi endpoint chưa xác minh | `g17-ag03-business-api` | `G16_ACCEPTANCE.md` §8 mục 2 |
| **AG-04** | **Webhook**: replay · idempotency · harness cục bộ | `g17-ag04-webhook` | `G16_ACCEPTANCE.md` §8 mục 5 |
| **AG-05** | **PostgreSQL**: giao dịch · migration · diễn tập trên cụm RIÊNG | `g17-ag05-postgres` | `G12_POSTGRES.md` · `SHARED_CONTRACTS.md` §29 |
| **AG-06** | **Frontend quản lý kết nối J&T + E2E local** (Owner/Codex chốt). Trước đó làn này làm **bảo mật & cách ly**; **không huỷ**, hoàn thành rồi nhận Dispatch mới | `g17-ag06-security` | Owner/Codex chốt 15/10 |

**Quyền sở hữu — KHÔNG TRÙNG** (mỗi làn một worktree riêng, nên tranh chấp tệp là **bất khả** về mặt
vật lý; bảng này để chốt *ý định*, không phải để chống ghi đè):

| Làn | CHỈ được ghi |
|---|---|
| AG-01 | `docs/QA_G17.md` · `app/thu/thu_qa_g17.py` |
| AG-02 | `app/http_jt.py` · `app/thu/thu_http_jt.py` · `app/thu/stub_jt.py` · `docs/G17_TRANSPORT.md` |
| AG-03 | `app/adapter_jt.py` · `app/thu/thu_adapter_jt.py` · `app/thu/thu_hop_dong_jt.py` · `docs/G17_BUSINESS_API.md` |
| AG-04 | `app/webhook.py` · `app/thu/thu_webhook_jt.py` · `trien_khai/g17/` · `docs/G17_WEBHOOK.md` |
| AG-05 | `trien_khai/postgres/` · `app/thu/thu_postgres.py` · `docs/G17_POSTGRES.md` |
| AG-06 (việc 1) | `app/thu/thu_g17_baomat.py` (mới) · `docs/G17_SECURITY_ISOLATION.md` (mới) |
| AG-06 (việc 2, sau settlement) | `admin/admin.js` · `admin/carrier_health.js` · `admin/logic.js` · `pages/carriers.html` · `thu_giao_dien/*.spec.js` · `docs/G17_FRONTEND_E2E.md` (mới) |
| **AG-00** | `app/csdl.py` · `app/migrate.py` · `app/server.py` · `app/cau_hinh.py` · `app/transport.py` · `app/quan_sat.py` · `docs/SHARED_CONTRACTS.md` · `.gitignore` · tệp của làn **SAU KHI** làn đó bàn giao |

---

## 2. G18 — "ĐO ĐỒNG THỜI THẬT" (đề xuất)

- `V-13914(a)`: tiến trình bị **tắt GIỮA giao dịch** — chưa ai đo (`BAN_GIAO.md` §6.1).
- `V-13914(b)`: **máy chủ HTTP thật dưới tải** — bàn đo hiện gọi thẳng hàm, **không** qua
  `ThreadingHTTPServer`.
- `V-13914(c)`: **trần chống lạm dụng nhiều tiến trình** — `B- G11-10` đã đo: hai tiến trình ⇒
  trần thực **gấp đôi** khai báo. Đây là **điều kiện kích hoạt số 2** của kế hoạch PostgreSQL.
- **Tiêu chí đóng:** ba phép đo trên có **số thật + tên lệnh**, và mỗi phép có **đối chứng âm**.

## 3. G19 — "ĐƯỜNG VÀO CỦA LỚP TRUY VẤN" (đề xuất)

- Cắm route cho `app/truy_van.py` + đưa `DDL_G12Q` vào **migration v9** (AG-01 đã viết, **chưa gộp
  vào đường chạy** — `BAN_GIAO.md` §6.1).
- 21 mã trạng thái **Viettel Post** (AG-03 khảo sát, **chưa áp**).
- `P-3`/`P-4`: `admin/finance.js` dòng 19–20 nói *"chưa có đường API nào"* trong khi 17 dòng route đã
  cắm; `API_DANG_DUNG_TC` có **2 dòng trùng** ⇒ "17 route" thật ra là **15**.
- **Tiêu chí đóng:** route có ca E2E qua HTTP thật; tài liệu **không còn câu nào sai về hệ thống**.

## 4. G20 — "GIAO DIỆN DÙNG ĐƯỢC" (đề xuất — hai phát hiện CAO chưa xử)

- `V-13910` (cao): **16/17 màn khai ở đợt 3 KHÔNG tồn tại trong giao diện** — năm mô-đun
  `admin/{finance,billing,carrier_health,ai,health}.js` là **mã chưa ai gọi**.
- `V-13911` (cao): giao diện quản trị **không dùng được bằng bàn phím** — 15 lượt Tab không rời `body`.
- **Tiêu chí đóng:** mỗi màn có **đường vào thật**; ca canh bàn phím thêm **cùng lượt** với bản vá.
- **Lưu ý:** `BAN_GIAO.md` §10 chốt đây là **chỗ yếu nhất của hệ**, không phải CSDL.

## 5. G21–G25 — KHUNG ĐỀ XUẤT, chưa có nguồn trong repo

| Mốc | Đề xuất | Trạng thái nguồn |
|---|---|---|
| **G21** | **J&T thật**: mở `sandbox` theo phiếu duyệt, chạy harness ra hãng, đối chiếu chữ ký/mã lỗi thật. **Cần `V-G09-01` + `V-13906-05`.** | chờ Owner |
| **G22** | **Callback thật**: trả lời 10 chỗ hở ở `CHAN_HOP_DONG_CALLBACK`, nâng mức khỏi `DOCUMENTED`. **Cần `V-G11-01` (URL công khai).** | chờ Owner + hãng |
| **G23** | **Vận hành**: Docker (`V-13913`, cài = đổi máy ⇒ cần duyệt) · log có cấu trúc · health/readiness · sao lưu/khôi phục. | một phần có nguồn (`G12_DOCKER.md`) |
| **G24** | **Đa hãng**: VTP 21 mã · GHN/GHTK/BEST — dùng lại lớp HTTP đã có, không viết lại adapter. | một phần có nguồn |
| **G25** | **Nghiệm thu người**: chuẩn bị gói để **anh Thành tự chạy và tự kết luận**; **AI không tự tuyên bố production-ready**. | `BAN_GIAO.md` §2 |

> `G21`–`G25` **phần lớn KHÔNG có nguồn trong repo** — đây là khung, không phải cam kết. Đừng đọc
> chúng như việc đã được giao.

## 6. HAI ĐIỀU PHẢI NÓI THẲNG

**6.1 Phân công nay ĐÃ ĐẦY ĐỦ — bản trước bị TUI tách theo dòng, không phải Owner thiếu yêu cầu.**
Codex đã xác nhận (`msg_56f72b42a31c`). Bản đầy đủ:
- **AG-05**: PostgreSQL **transaction / migration / concurrency CHỈ trên DB test riêng**;
  **CẤM migration DB nghiệp vụ** (D-8). Cấm đụng cụm `:5432`.
- **AG-06**: **frontend quản lý kết nối J&T + E2E local** — và làn này **đang chạy bảo mật**;
  **không huỷ, không tạo worker trùng**; sau settlement giao việc frontend cho **cùng agent** bằng
  **Dispatch mới**, cập nhật ownership.
- **AG-01 QA**: baseline · **V5/V6/V7 tenant/RBAC/AES** · **harness** · **Chromium**.
- **G17–G25** là **đề xuất mới dựa trên backlog**; Owner **đã uy quyền** đề xuất và tiếp tục local.
- Giữ `main` và **giữ nguyên worktree G12 cũ**.

**6.1b `dsh` — ID do RUNTIME chứng minh, ghi ở ĐÂY, không sửa cấu hình Orca toàn máy.**
```
worker-start --agent dsh       -> ok:true · provider.id = "dsh" · terminal chạy `dsh-tui .`
worker-start --agent deepseek  -> ok:false · error.code = "agent_unconfigured"
```
Tài liệu Orca liệt kê `claude, codex, cursor, antigravity, muse, zcode, opencode, opencode2` —
**KHÔNG có `dsh`**. Đây là chỗ tài liệu Orca **thiếu**, không phải chỗ dự án sai.
Ghi vào tài liệu **dự án** để phiên sau không phải đo lại. **Không sửa cấu hình Orca toàn máy.**
Giới hạn quản trị đã đo: `worker-stop` trên worker `dsh` trả `stop_unknown` / `processAction: none` /
*"The worker terminal is user_owned"* ⇒ dừng phải theo đúng hợp đồng vòng đời, **không dùng đường tắt**.

**6.2 `G17`–`G25` là ĐỀ XUẤT, không phải yêu cầu cũ.** Không có tệp nào trong repo định nghĩa chúng.
Nếu sau này có người đọc tài liệu này rồi tưởng đó là chỉ thị cũ, thì **hiểu sai** — đó là lý do
§0 và §6 tồn tại.

---

## 7. BẤT BIẾN AN TOÀN — KHÔNG ĐỔI SUỐT G17

- **Không gọi hãng thật**, kể cả sandbox (`V-G09-01`, `V-13906-05` CHƯA CẤP). Mọi phép đo của lớp
  HTTP dùng **stub `127.0.0.1` cổng 0**.
- **Không push · không deploy · không mở cổng ra Internet** (`V-G11-01` chưa cấp).
- **`CHO_PHEP_LIVE = False`**; cổng `sandbox`/`production` là **hằng số trong mã**, KHÔNG đọc từ biến
  môi trường.
- **Không credentials thật**, không `.env`, không in bí mật ra log.
- **Chốt `D-9` (`city`/`area`) giữ CHẶN CỨNG**; **không đoán mã `110`** (D-4).
- **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8) — vẫn SQLite; PostgreSQL chỉ **diễn tập trên
  cụm RIÊNG**, không đụng cụm `:5432`.
- **`main` giữ nguyên `de740dc`** cho tới khi có phê duyệt riêng.

---

## 8. WAVE G18 — "ĐO ĐA TIẾN TRÌNH & NHỮNG CHỖ CHƯA TỪNG CHẠM" (đang chạy)

**Nền:** `integration/g17` @ `7b741c8` · Run `run_695b048104a9` · 6 worktree `g18-*`, mỗi làn một nhánh.
**Nguyên tắc:** wave này **chỉ đóng lỗ hổng đã ghi ra**, không làm lại mục đã đạt (G16-A và G17 đã ĐẠT).

| Làn | Worktree | Việc | Nguồn |
|---|---|---|---|
| AG-01 | `g18-ag01-qa` | QA độc lập: kế hoạch + baseline + 2 chốt chặn | `QA_G13_G15.md` §6.3 |
| AG-02 | `g18-ag02-multiprocess` | **ĐA TIẾN TRÌNH** thật (không thread) + đo lại `B-G11-10` | AG-01 ghi "chỉ chồng luồng trong MỘT tiến trình" |
| AG-03 | `g18-ag03-secretpaths` | **Bí mật bị hãng ECHO LẠI** + bí mật trong **ĐƯỜNG DẪN URL** | AG-01 ghi 2 lỗ hổng phạm vi của AG-02 |
| AG-04 | `g18-ag04-httpserver` | **Máy chủ HTTP THẬT dưới tải** (`ThreadingHTTPServer`) | `BAN_GIAO.md` §6.1 `V-13914(b)` |
| AG-05 | `g18-ag05-pgwrite` | **PostgreSQL ĐƯỜNG GHI** (`csdl.ghi`, `rowcount`) | AG-01 ghi "AG-05 chỉ dựng SCHEMA" |
| AG-06 | `g18-ag06-crash` | **Tắt tiến trình GIỮA giao dịch** (SIGKILL) | `BAN_GIAO.md` §6.1 `V-13914(a)` |

### Danh sách ACCEPTANCE của G18 — phải nộp đủ, nếu không thì ghi CHƯA ĐO

1. **AG-02:** số **tiến trình thật** (1/2/4/8) × trần thực tế so với khai báo; **đối chứng âm** với 1
   tiến trình phải ĐÚNG bằng khai báo; kết luận lớp nào an toàn qua tiến trình, lớp nào không.
2. **AG-03:** hai bẫy (echo + path) có **ca âm/dương**; bộ dò phủ **6 dạng** bí mật; **quyết định**
   về việc in path nguyên văn (giữ thì phải có lý do + ca canh).
3. **AG-04:** máy chủ thật bind `127.0.0.1` cổng 0; số **yêu cầu/giây**, tỉ lệ lỗi, `5xx`, và hạn chế
   tốc độ qua **HTTP thật** (khác khi gọi hàm trực tiếp); tắt máy chủ theo **đúng PID**.
4. **AG-05:** `rowcount` **SQLite vs PostgreSQL** trên cùng câu ghi; 5 dạng ghi; **vân tay cụm `:5432`
   TRƯỚC = SAU**; không để cụm sót lại.
5. **AG-06:** giết ở **5 điểm** trong/ quanh giao dịch; sau mỗi lần mở lại CSDL đo **tính toàn vẹn**
   (số dòng, tổng COD, dòng mồ côi); **đối chứng dương** khi không giết; đo trên **cả SQLite và PostgreSQL**.
6. **AG-01:** kế hoạch + baseline riêng + **ca tự kiểm bộ dò** + **đối chứng dương**; mục CHƯA ĐO nói thẳng.
7. **AG-00:** commit hộ từng làn (worker không ghi được `.git`), tích hợp `integration/g18`, regression
   trên **commit sạch** có **SHA · lệnh · exit code · số ca · số bộ · số hỏng · số skip · vân tay trước/sau**.

### Ràng buộc riêng của G18
**Concurrency CHỈ trên DB test riêng** — mỗi tiến trình `VIP_HUB_DATA` riêng hoặc CSDL tạm riêng; **cấm
dùng CSDL thật**. PostgreSQL **chỉ cụm riêng**, **cấm đụng `:5432`**. Không mở cổng ra ngoài.

---

## 9. WAVE G19 — "ĐÓNG NỢ VẬN HÀNH ĐÃ ĐO ĐƯỢC" (chuẩn bị)

**Nền dự kiến:** `integration/g18` @ `626d422` · sau khi AG-01 nghiệm thu xong.
**Nguyên tắc giữ nguyên:** chỉ đóng lỗ hổng **đã đo được**, không thêm tính năng mới.

| Làn | Việc | Nguồn — lỗ hổng CÓ THẬT |
|---|---|---|
| **AG-02** | `gioi_han` **PHẦN A**: trần tần suất **nhân theo số bản** | AG-02 đo G18: trần khai 20 ⇒ qua **20·40·80·160** lượt với N=1·2·4·8. **Khuôn chữa ĐÃ CÓ SẴN TRONG NHÀ** (`gioi_han` PHẦN B: `UPDATE … WHERE … + ? <= trần`) đã đo giữ đúng trần qua **4 tiến trình** |
| **AG-03** | **Cửa lách thứ hai**: bộ đếm tần suất **mất sạch khi khởi động lại** | AG-02 ghi G18: *"đó là cửa lách thứ hai, độc lập với số tiến trình"* — đã ghi trong `gioi_han.py`, **chưa sửa** |
| **AG-04** | **21 mã trạng thái Viettel Post** chưa ánh xạ | `BAN_GIAO.md` §6.1 |
| **AG-05** | **`V-13910`** (CAO): 16/17 màn khai ở đợt 3 **không tồn tại trong giao diện** | `BAN_GIAO.md` §6.1 · AG-06 đo G17: `carrier_health`/`finance`/`health` = **0 lần được `admin.js` tham chiếu = MÃ CHẾT** |
| **AG-06** | **`V-13911`** (CAO): giao diện quản trị **không dùng được bằng bàn phím** — 15 lượt Tab không rời `body` | `BAN_GIAO.md` §6.1 · `BAN_GIAO.md` §10 gọi đây là **chỗ yếu nhất của hệ** |
| **AG-01** | QA độc lập + **nghiệm thu trên bản đã gộp** | như G18 |
| **AG-00** | Route `truy_van.py` + `DDL_G12Q` vào **migration v9**; `P-3`/`P-4` | `BAN_GIAO.md` §6.1 — tệp `migrate.py` thuộc AG-00 |

### §9b ĐÍNH CHÍNH QUYỀN SỞ HỮU — HAI LỖI THIẾT KẾ CỦA CHÍNH AG-00 (phát hiện lúc phóng wave)

Bảng §9 ban đầu **trùng quyền sở hữu ở hai chỗ**. Đã sửa **trước khi phóng**:

1. **`gioi_han.py` bị hai làn cùng nhận.** §9 định giao AG-02 việc "PHẦN A nhân trần" và AG-03 việc
   "bộ đếm mất khi khởi động lại" — nhưng **cả hai đều nằm trong `app/gioi_han.py`**. Hai làn cùng
   ghi một tệp là đúng thứ luật quyền sở hữu sinh ra để chặn.
   ⇒ **Gộp cả hai việc vào MỘT làn (AG-02)** — chúng là **cùng một hệ thống**, một người sửa thì
   nhất quán; và **giao AG-03 việc khác** (21 mã VTP).

2. **`admin/` + `pages/` bị hai làn cùng nhận.** §9 định giao AG-05 `V-13910` và AG-06 `V-13911` —
   cả hai đều phải sửa `admin/*.js` và `pages/*.html`.
   ⇒ **Tách theo TỆP, rời nhau hẳn:**
   - **AG-05** chỉ ghi `admin/admin.js` · `admin/finance.js` · `admin/health.js` ·
     `admin/carrier_health.js` · `admin/billing.js`
   - **AG-06** chỉ ghi `pages/*.html` · `admin/logic.js` · `thu_giao_dien/*.spec.js`
   Mỗi spec ghi **CANH BAO TRUNG QUYEN** nói rõ tệp nào của làn kia.

**Bài học ghi lại:** lỗi này **không lộ ra khi đọc bảng** — nó chỉ lộ khi **đối chiếu bảng quyền với
DANH SÁCH TỆP THẬT**. Luật "quyền sở hữu không trùng" phải được kiểm bằng **tệp**, không bằng **mô tả
công việc**: hai mô tả khác nhau vẫn có thể trỏ vào cùng một tệp.

### Acceptance của G19
1. **AG-02:** trần tần suất **giữ nguyên** qua N=1·2·4·8 tiến trình **thật**; **đối chứng âm** —
   cố tình quay lại bộ đếm trong bộ nhớ thì phép đo **phải ĐỎ**.
2. **AG-03:** bộ đếm **sống qua khởi động lại**; có ca chứng minh (khởi động lại rồi vượt trần ⇒ bị chặn).
3. **AG-04:** 21 mã có **bảng ánh xạ + ca**, và mã **chưa xác minh** vẫn `NEEDS_REVIEW` (không đoán).
4. **AG-05:** mỗi màn hoặc **có đường vào thật** (bấm được, có ca E2E), hoặc **bị bỏ kèm lý do**.
5. **AG-06:** ca bàn phím **đi hết được** các màn quản trị; thêm ca **cùng lượt** với bản vá.
6. **AG-00:** `truy_van.py` có route thật + E2E qua HTTP; `P-3`/`P-4` sửa xong và **không còn câu nào sai về hệ thống** trong tài liệu.
7. **AG-01:** đối chiếu chéo + regression riêng + mục CHƯA ĐO nói thẳng.

> **Ghi chú thi hành (bài học G18):** trong wave G18, AG-02 và AG-04 **kẹt ~45 phút** nhưng vẫn
> đang làm việc thật; AG-00 **không dừng chúng** và cả hai **tự settlement**. ⇒ Với G19: khi một làn
> có vẻ đứng yên, **thu bằng chứng trước**, và **không** dừng/abandon khi chỉ có vắng mặt.
