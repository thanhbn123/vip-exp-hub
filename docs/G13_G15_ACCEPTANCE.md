# NGHIỆM THU G13–G15 — VIP EXPRESS HUB · do AG-00 (DeepSeek) lập trong Orca

> **AI-ASSISTED, KHÔNG PHẢI NGƯỜI SOÁT.** Mọi số trong tài liệu này do tác tử AI chạy trên
> máy này. Làn kiểm thử AG-01 là một tác tử AI **độc lập**, không phải người.
> `docs/BAN_GIAO.md` §2: **"AI review không phải human review. Bộ thử xanh không phải lời cho phép."**
> **Hệ này CHƯA production-ready.** Tài liệu này không tuyên bố điều ngược lại.

**Nền đo:** `de740dc` · **Nhánh:** `integration/g13-g15` (+ `agent/g13-jt-api`,
`agent/g14-jt-webhook`, `agent/g15-infra`) · **Máy:** macOS arm64 · python 3.9.6 · SQLite 3.51.0
· node v26.7.0.

> **MỐC CÂY — tự đo, đừng tin tài liệu.** Theo đúng bài học `BAN_GIAO.md` §7.3, tệp này **không**
> ghi SHA của chính commit chứa nó (ghi vào là tự làm mình sai ở lượt sau). Người đọc tự chạy:
> ```bash
> cd ~/Projects/vip-express-hub && git log --oneline -1 integration/g13-g15
> ```

---

## 1. CƠ CẤU — 5 AGENT, ĐÚNG CHỈ THỊ

| Mã | Vai | Trạng thái |
|---|---|---|
| **AG-00** | DeepSeek Project Controller | xong |
| **AG-01** | DeepSeek QA / Verifier (P0) | xong — phán quyết ở §7 |
| **AG-02** | DeepSeek J&T API Engineer (G13) | xong — làn đã đóng |
| **AG-03** | DeepSeek Webhook Engineer (G14) | xong — làn đã đóng |
| **AG-04** | DeepSeek Infrastructure Engineer (G12/G15) | xong |

**1 Controller · 1 QA · 3 Code Agent.** Không tạo agent thứ sáu. **Claude không được gọi** một
lượt nào.

---

## 2. KẾT QUẢ ĐO ĐƯỢC

| Phép đo | Kết quả THẬT | Lệnh |
|---|---|---|
| Bộ thử python | **1133 ca · 34 bộ · 0 hỏng · 0 bỏ qua** | `sh app/thu/chay_tat_ca.sh` |
| Frontend tầng 1 (node) | **56 ca** | (trong bộ trên) |
| Frontend tầng 2 (HTTP + tệp tĩnh) | **36 ca** | (trong bộ trên) |
| Frontend tầng 3 (Chromium thật) | **26 đạt · 1 bỏ qua** | `sh thu_giao_dien/chay.sh` |
| E2E qua HTTP thật | **41/41** | (trong bộ trên) |
| Đồng thời **8 tiến trình thật × 400 phép × 3 ca** | **3200/3200 chốt · 0 mất cập nhật · 0 khoá hết giờ · 0 giao dịch hỏng** | `python3 app/thu/dong_thoi/chay.py` |
| Harness E2E G15 | **29 đạt · 0 hỏng · 2 BLOCKED** | `sh trien_khai/g15/chay_harness.sh` |
| Diễn tập chuyển PostgreSQL (cụm RIÊNG) | **26 đạt · 0 hỏng · 0 bỏ qua** — dựng cụm riêng cổng 55432, tự dừng, tự xoá. Vân tay `:5432` **trước = sau** (`postgres`, `vip_customs`, `vip_customs_g16`, `vip_customs_test`), **0 cụm thử còn sót** | `python3 trien_khai/postgres/dien_tap_chuyen.py` |
| Harness hãng G09 | **97 đạt · 0 hỏng · 3 bỏ qua** · LOCAL READY=PASS · SANDBOX=BLOCKED · LIVE=BLOCKED | `python3 app/harness_hang.py` |

**TESTS PASSED: 1133 (python) + 92 (frontend) + 41 (E2E) + 27 (Chromium)**
**TESTS FAILED: 0**
**TESTS SKIPPED: 1 (Chromium) + 3 (harness hãng) + 2 BLOCKED (G15 sandbox)**

**Mã thoát của mọi lượt trên: 0.**

---

## 3. TRẠNG THÁI TỪNG CỔNG

| Cổng | Trạng thái | Căn cứ |
|---|---|---|
| **G12** | **XONG** | Tầng 3 Playwright 26 đạt · đồng thời 8 tiến trình 0 mất cập nhật · migration lock · khoá dự phòng. **Docker = BLOCKED** (không cài — xem §8) |
| **G13 J&T API** | **MOCK_VERIFIED · LIVE = BLOCKED** | Adapter 313→~900 dòng, ba ổ khoá LIVE độc lập, COD đi `codMoney`, chốt D-9 nguyên vẹn. **KHÔNG gọi hãng lượt nào** |
| **G14 J&T WEBHOOK** | **MOCK_VERIFIED · CALLBACK THẬT = BLOCKED** | Hai lỗi THẬT đã vá (xem §4). Tenant CHỈ từ `carrier_account`. Mã `110` ⇒ `NEEDS_REVIEW` |
| **G15 LOCAL E2E** | **MOCK_VERIFIED · chặng SANDBOX = BLOCKED** | Harness 10 bước chạy thật trên CSDL tạm, 29 đạt · 2 BLOCKED ghi rõ cái thiếu |
| **G13 LIVE VERIFIED** | **KHÔNG — và không thể** | `V-G09-01` + `V-13906-05` chưa cấp; lớp transport HTTP thật chưa viết |

---

## 4. BỐN LỖI THẬT ĐÃ VÁ (đều đo được TRƯỚC/SAU, không suy đoán)

### 4.1 Bộ chạy hồi quy tự nói dối — và nó GIẤU một phát hiện khỏi chính AG-00
`app/thu/chay_tat_ca.sh` có `set -e` + `OUT=$(python3 "$t" 2>&1); MA=$?`. Dưới `set -e`, **một bộ
thử hỏng giết CẢ script**: đo được **169 byte · 3 dòng · 2/29 bộ · 0 dòng ✗ · KHÔNG bảng tổng kết
· KHÔNG khối phạm vi**. **27/29 bộ chưa từng chạy.**
Hệ quả nặng hơn: nó **giấu luôn bộ thử thứ hai** bị lỗi git (`thu_tich_hop.py`) khỏi chính người
đang đi tìm lỗi — bộ đó xếp sau `thu_bao_mat.py` nên không bao giờ tới lượt.
**Bản vá ĐẦU của AG-00 SAI** (`if ! OUT=...; then MA=$?; fi`) — `!` đảo mã thoát nên `MA` luôn 0,
xoá luôn tiêu chí mã thoát. **AG-01 bác đúng.** Dạng đúng: `MA=0; OUT=$(...) || MA=$?`.
Đã kiểm chứng trên cây cách ly: bộ hỏng được báo `HỎNG (mã thoát 1)`, in đủ bảng tổng kết + khối
phạm vi, thoát 1.

### 4.2 Watermark J&T bị mã KHÔNG ĐƯỢC ÁP đầu độc (AG-03)
`luu_dau_vet()` ghi `wh_su_kien.hang_moc_thoi_gian` cho **mọi** sự kiện, kể cả mã nhập nhằng `110`
và mã chỉ ghi nhận `121`; `watermark()` lại ưu tiên đọc cột đó. Nguồn audit (chỉ ghi khi ĐÃ ÁP) thì
đúng — **hai nguồn nói khác nhau, nguồn được ưu tiên là nguồn SAI.**
Hậu quả đo được: `113 Delivered` lúc 09:00 đến sau `110` lúc 10:00 **bị chặn "đến muộn"** ⇒
**đơn đã giao mà hệ thống không bao giờ biết.**
**Vì sao bộ thử cũ xanh suốt:** lỗi chỉ hiện trên CSDL **đã migrate** (schema v7+). `thu_webhook.py`
chạy trên CSDL **chưa** migrate nên rơi xuống nguồn audit (nguồn đúng). **CSDL thật thì đã migrate.**
Vá hai tầng: `_ghi_watermark()` là nơi **duy nhất** ghi cột và **chỉ khi `ap_dung=1`**; tầng đọc
**vẫn giữ** bộ lọc `trang_thai_chuan IS NOT NULL` để cứu **dữ liệu cũ** do mã cũ ghi.

### 4.3 `DON_TRUNG` bị xử như "hãng từ chối" (AG-02 phát hiện, AG-00 định tuyến)
J&T `145003204` = lượt trước **ĐÃ VÀO**. Nhánh `else` trả đơn về `da_duyet` + **hoàn suất** ⇒ gửi
lại cùng `txlogisticId` ⇒ lại `DON_TRUNG` ⇒ **mắc vòng**, trong khi vận đơn **đang sống ở hãng**.
Nay `DON_TRUNG` giữ `dang_gui` + `can_doi_soat_ket_qua=1`, **KHÔNG hoàn suất**, có vết lịch sử.
Đối xứng nhánh `timeout` (AG-00 **tự đọc mã kiểm**, không tin lời khai): cả hai đều không ném; chỉ
nhánh từ chối THẬT mới `hoan_don` + 502.

### 4.4 Năm khối ghi tiền không nằm trong giao dịch (V-13912 — AG-00 tự làm)
`khoa_ghi` trần **không phải** giao dịch: mỗi `csdl.ghi()` vẫn tự chốt ngay. Nặng nhất: một lượt
chuyển COD ghi **5 chỗ** mà **3 chỗ nằm ngoài giao dịch** ⇒ COD nhảy `COD_SETTLED` trong khi sổ cái
**không có bút toán nào** — đúng khuôn §18. Bút toán là bất biến (§17) nên chênh đó chỉ chữa được
bằng bút toán đảo.
Đã bọc `csdl.giao_dich()` cho **5 khối** (`don_hang` ×2 · `tai_chinh` ×2 · `usage` ×1).
**Bằng chứng bản vá là thật:** 3 ca canh mới **HỎNG trên mã TRƯỚC bản vá** (đã đo bằng cách lùi mã
nguyên văn từ `git show HEAD:`), xanh sau khi vá.

### 4.5 `ma` vs `ma_chuan` — hai tên cho một thứ (AG-02 phát hiện, AG-00 quyết)
`NormalizedCarrierError.nhu_dict()` phát `ma_chuan` (đúng hợp đồng §5) nhưng `don_hang` đọc `ma` —
một cái tên **không có trong hợp đồng nào**. Nhánh `chua_vao` của `doi_soat_don` **chết im lặng**,
và ca thử cũ **xanh vì nó dựng fixture bằng đúng cái tên sai** ("thứ dùng để kiểm chứng tự nó nói
sai", §12.1). **AG-00 quyết: `ma_chuan` là tên chuẩn.** Hai đầu đã đổi; lớp lùi đã **gỡ hẳn**; ca
canh **H5** mới khẳng định tên cũ **không** còn được nhận (ai thêm lại dòng dự phòng là ca đỏ).

---

## 5. AN TOÀN — ĐO ĐƯỢC, KHÔNG PHẢI LỜI HỨA

| Điều phải giữ | Cách đo | Kết quả |
|---|---|---|
| Không gọi được hãng | quét **AST** 4 mô-đun transport | `adapter_jt.py` · `adapter_vtp.py` · `adapter.py` · `transport.py` — **KHÔNG import thư viện mạng nào** |
| Khoá LIVE còn nguyên | hỏi thẳng sổ đăng ký | `jt: False` · `vtp: False` · `TRANSPORT_THAT_DA_VIET = False` |
| Ánh xạ `area` chưa chốt | chạy bộ canh D-9 | **16 ca · 0 hỏng** — vẫn CHẶN CỨNG ngoài `mock` |
| COD đúng trường | ca hợp đồng | đi `codMoney`; có ca **cấm** `itemsValue` |
| Không rò bí mật | quét tệp thay đổi | **0** chuỗi dạng secret · **0** tệp khoá/`.env` bị đụng |
| CSDL THẬT không bị chạm | sha256 trước/sau | **`aaf71362f86f7391f9394f77a5c8a3b24c81e7e1b6ca49da116143eb556d0c54`** — **y nguyên** |
| Cụm PostgreSQL dự án KHÁC | vân tay trước/sau | `:5432` PID postmaster 58873 · danh sách CSDL y nguyên · **0 kết nối tới `vip_customs*`** · **0 cụm thử còn sót** |
| Cây làm việc Orca | tìm `.db`/`.db-wal` | **0 tệp** — mọi bộ thử dùng CSDL tạm dưới `/tmp` |
| Không mở cổng ra Internet | `lsof -nP -iTCP -sTCP:LISTEN` | **mọi listener của dự án chỉ `127.0.0.1`**. Các bind `*:` là dịch vụ hệ thống macOS (`rapportd`, `ControlCenter`) và chính Orca — **không phải dự án này** |
| Không có tunnel | dò `ngrok` · `cloudflared` · `localtunnel` | **không có cái nào** trên máy |

**GIT PUSH: KHÔNG** (repo vẫn 0 remote) · **VPS DEPLOY: KHÔNG** · **ĐƠN VẬN CHUYỂN THẬT: KHÔNG** ·
**CỔNG RA INTERNET: KHÔNG mở** · **XOAY KHOÁ THẬT: KHÔNG** · **GHI RA VIP VAULT: KHÔNG**.

---

## 6. PHÁT HIỆN LỚN NHẤT — ĐẢO NGƯỢC GIẢ ĐỊNH CỦA KẾ HOẠCH POSTGRESQL (AG-04)

Cùng một khuôn **đọc-rồi-ghi ngây thơ**, 4 tiến trình thật:

| | SQLite 3.51.0 | PostgreSQL 16.15 |
|---|---|---|
| Báo lỗi | 18/160 lượt `database is locked` — **ỒN ÀO** | **0 lượt báo lỗi** |
| **MẤT CẬP NHẬT** | **0** | **84/120 lượt chốt (70%) — IM LẶNG** |

**Kết luận cứng:** SQLite **không mất dữ liệu** — nó **từ chối ồn ào**. PostgreSQL, với **cùng khuôn
mã đó**, mất **70%** số lượt ghi **mà không báo gì**. Chuyển CSDL mà giữ nguyên khuôn đọc-rồi-ghi là
**đổi một lỗi ồn ào lấy một lỗi im lặng** — tệ hơn cho một hệ thống tiền.
Bốn kết cục được tách riêng đúng yêu cầu I02: `lock timeout` · `failed transaction` · `lost update` ·
`commit OK`. PostgreSQL **không tự sửa** kết cục thứ tư — chỉ `UPDATE ... SET x = x + 1` hoặc
`SELECT ... FOR UPDATE` mới sửa.
**Hệ quả cho quyết định:** chặng "lớp phương ngữ" **phải đi cùng** chặng "soát từng chỗ đọc-rồi-ghi",
không tách rời. Đã ghi thành **điều kiện tiên quyết** trong `docs/G12_POSTGRES.md`.

---

## 7. PHÁN QUYẾT CỦA AG-01 (làn kiểm thử độc lập)

Xem `docs/QA_G13_G15.md` (767 dòng) — baseline độc lập · Finding A/B · `N-01`…`N-06` · kế hoạch
`V1–V13` · **LƯỢT 2** · bộ thử độc lập `app/thu/thu_qa_jt.py` (**22 ca · 0 hỏng**).

### Bảng phán quyết lượt 2

| Cổng | Phán quyết |
|---|---|
| **V13** bộ chạy hồi quy | **ĐẠT** |
| **V1** adapter J&T (chữ ký · mốc thời gian · AST · COD · ba ổ khoá) | **ĐẠT** |
| **V2** ánh xạ · D-9 | **ĐẠT** |
| **V3** ranh giới giao dịch (V-13912) | **ĐẠT** — lời khai của AG-00 **được xác nhận độc lập** |
| **V4** webhook | **ĐẠT** — **cả hai lỗi ĐỀU THẬT, cả hai bản vá ĐỀU KÍN** |
| **V8** COD | **ĐẠT** |
| **V5** server B11 | **ĐẠT** — *"không bắt được lỗi nói quá"* |
| **V11** PostgreSQL | **ĐẠT một phần** |
| **V5/V6/V7 toàn cục** (cách ly tenant ngoài đường webhook · RBAC · AES đầy đủ) | **CHƯA ĐO ĐỘC LẬP — vẫn MỞ** |

> **KHÔNG có mục CRITICAL/HIGH ⇒ không có gì chặn gộp. AG-01 không miễn trừ mục nào.**

**AG-01 kiểm bằng cách mạnh hơn, không tin bản sao.** AG-03 đo lỗi watermark bằng hàm chép nguyên
văn; AG-01 dựng nhánh BEFORE bằng **`webhook.py` lấy nguyên văn `git show HEAD:`** trên **CSDL mới
tinh đã migrate** cho từng kịch bản. Kết quả: lỗi có thật, bản vá kín cả hai kịch bản, và **toàn kho
mã chỉ còn ĐÚNG MỘT câu `UPDATE` cột mốc** ⇒ **không còn đường rò khác**.
**AG-01 còn tự đột biến bộ dò của chính nó:** tiêm lại bẫy `hexdigest` ⇒ bộ thử của nó **ĐỎ**. Tức
bộ dò **thật sự dò được**, không phải "đọc thấy đúng".

**AG-01 đã bắt lỗi CHÍNH AG-00 — hai lần.** `N-01` (HIGH): bản vá `set -e` mà AG-00 đóng băng vào
hợp đồng **sai**, áp nguyên văn thì **xoá tiêu chí mã thoát**. `L2-N1` (MEDIUM): hai mục cuối của
bộ chạy **vẫn phán bằng chữ trong output**. Cả hai **đã vá** (xem §9). Đây là lý do tồn tại của một
làn kiểm thử độc lập: **người viết không tự soát được mình, và hợp đồng đóng băng không miễn nhiễm
với lỗi.**

---

## 8. BLOCKED — CHÍNH XÁC CÁI CÒN THIẾU

| # | Việc | Thiếu chính xác cái gì | Ai gỡ |
|---|---|---|---|
| 1 | **Mọi lượt gọi hãng (kể cả sandbox)** | `V-G09-01` chưa cấp | **anh Thành** |
| 2 | **Credentials J&T** | **Không có tệp `.env` nào**, và `.env.example` **không khai một khoá J&T nào** ⇒ bề mặt cấu hình **chưa tồn tại**. Cần 4 **tên** trường: `apiAccount` · `privateKey` · `customerCode` · `password` | J&T + bưu cục + anh Thành |
| 3 | **Lớp transport HTTP thật** | **Chưa ai viết.** Mở `CHO_PHEP_LIVE` một mình **không đủ** | làn kế tiếp |
| 4 | **Nghĩa mã `110` + nghi HAI bộ mã** | `V-13906-04` chưa cấp. Hệ **không áp** trạng thái nào cho `110`; đánh dấu cần soát (D-4) | J&T |
| 5 | **Ánh xạ `area` (D-9)** | Câu hỏi 28. Ví dụ của chính hãng đặt **quận vào `city`**, **phường vào `area`** — ngược ánh xạ đang dùng, và hệ **không gửi `city`** | J&T + anh Thành |
| 6 | **Chữ ký callback** | Có công thức `base64(md5-bytes(bizContent+privateKey))` nhưng **KHÔNG nói khoá ký chiều callback là khoá nào**, và **chuỗi đem đi ký là gì** | J&T |
| 7 | **Hình dạng phản hồi callback** | Trích lục chỉ có một mảnh "`code` khác 1". Đã trả thêm `code=1`; **mã HTTP đúng vẫn chưa biết** — cố ý KHÔNG đoán | J&T |
| 8 | **`cancelOrder` · `calculatingFees` · `printOrder` · `getOrder`** | Đường dẫn chưa xác minh; **tên trường lý do huỷ** để RỖNG chứ không đoán | J&T |
| 9 | **Docker** | **Không cài** — cài là đổi máy anh. **CẤM báo "Docker build PASS"** | anh Thành |
| 10 | **URL công khai cho webhook** | `V-G11-01` chưa cấp | anh Thành |

---

## 9. VIỆC CÒN LẠI ĐÃ ĐO MÀ CHƯA VÁ (nói thẳng, không giấu)

| # | Việc | Bằng chứng |
|---|---|---|
| **P-G15-01** | Log có cấu trúc **đã nối** vào đường yêu cầu trong lượt này (trước: **0 dòng JSON**, không lượt nào có `request_id`). Ca canh: `app/thu/thu_nhat_ky_yeu_cau.py` | đã vá + có ca |
| **B-G11-10** | **Trần tần suất nhân theo số bản**: hai tiến trình máy chủ cùng CSDL cùng IP ⇒ trần thực **40** thay vì khai báo **20** | AG-04 **đo được** (bản A cho qua 20 rồi 429, bản B vẫn cho qua 20 nữa). AG-00 **kiểm lại cấu trúc**: `app/gioi_han.py` giữ bộ đếm bằng `threading.Lock()` **trong bộ nhớ**, không có CSDL chống lưng ⇒ N tiến trình là N lần trần. **Chưa vá** — đây là **điều kiện kích hoạt số 2** của kế hoạch PostgreSQL |
| **N-02/N-03/N-04** | AG-01 phát hiện trong bộ chạy và `thu_postgres.py` | **đã vá cả ba** |
| **L2-N1** (MEDIUM) | Hai mục cuối bộ chạy (`tầng 2`, E2E) **vứt mã thoát** (`|| true`) rồi **phán bằng chữ trong output** — đúng khuôn mà dòng 40 của chính tệp đó tuyên bố đã từ bỏ | **ĐÃ VÁ + ĐÃ CHỨNG MINH NGƯỢC:** AG-00 tiêm vào bản sao một bộ **in `OK` rồi thoát 1** (đúng "hướng sai chết người" AG-01 nêu). Trước: sẽ phán **ĐẠT**. Sau: `tầng 2: HỎNG (mã thoát 1 · 0 ca)`, mã thoát 1 |
| **Bộ thử đồng thời `migrate` hay hỏng GIẢ** | `thu_migrate_dong_thoi.py` ca `a1` dùng **vạch xuất phát HẸN GIỜ** (`BAT_DAU = time.time() + 2.0`): dưới tải, con nạp mô-đun lâu hơn hạn thì tới muộn ⇒ không kịp chờ khoá ⇒ `assertGreaterEqual(nhuong_trong, 1)` đỏ. AG-04 đo: **1/3 lượt hồi quy đầy đủ · 0/6 lượt riêng** | **ĐÃ VÁ:** thay bằng **bắt tay TỆP BÁO SẴN SÀNG** (cha đợi đủ 8 tệp rồi mới thả). *"Hẹn giờ là đoán; tệp báo sẵn sàng là đo."* **Đo lại: 6/6 lượt riêng + 4/4 lượt DƯỚI TẢI hồi quy đầy đủ** |
| **L2-N2** (LOW) | `dau_thoi_gian_ms(datetime không tzinfo)` đi theo múi giờ MÁY (`TZ=UTC` lệch đúng 7 tiếng) — docstring hứa ngược lại. **Không tới được**: mọi lời gọi trong mã đều truyền mốc có `tzinfo` | **còn mở** (LOW, không chặn) |
| **N-05** | Bốn làn chung MỘT cây ⇒ **hỏng GIẢ ngẫu nhiên**. AG-01 **không** báo chúng là lỗi sản phẩm và **không** khẳng định nguyên nhân | **đã tìm ra MỘT nguyên nhân thật** (bộ thử `migrate` ở trên, đã vá). Phần tranh cổng cố định giữa các làn **còn nguyên** — là hạ tầng, không phải mã |
| **P-G15-02** (đề xuất của AG-04, **chưa làm**) | Khi kho đổi sang PostgreSQL, `migrate.sao_luu()` hiện là `Connection.backup()` — trên PostgreSQL **vô dụng mà vẫn chạy trót lọt**, tạo "bản sao" rỗng và **báo thành công** ⇒ **đường lùi GIẢ**, nguy hiểm hơn không có đường lùi | **cần anh Thành duyệt** (chỉ kích hoạt nếu chuyển CSDL — việc **chưa** được duyệt) |
| — | `abortOrder`/`getOrder` lái bằng `trackOrder` | xem §8 |

---

## 10. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY — cái gì NẰM NGOÀI

- **Chưa lượt gọi hãng nào.** Chưa chứng minh được: hãng chấp nhận chữ ký, mã lỗi thật khớp bảng,
  sandbox sống, callback ký bằng khoá nào, mã HTTP nào đúng.
- **Chưa deploy, chưa push, chưa HTTPS thật, chưa tunnel, chưa VPS.**
- **Chưa chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8). Kho nghiệp vụ **vẫn là SQLite**.
- **Chưa có người đọc lại.** Toàn bộ là tác tử AI. `BAN_GIAO.md` §2 vẫn nguyên hiệu lực.
- Chưa đo: Safari/Firefox · dữ liệu lớn · nhiều MÁY · ổ mạng · tải nhiều tiến trình máy chủ thật.
