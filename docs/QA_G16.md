# QA_G16 — AG-01 (QA / VERIFIER): baseline độc lập · phán quyết lời khai AG-00 · nghiệm thu G16-A

**Vai:** AG-01 QA/VERIFIER, cổng **G16-A**. **Không viết mã sản phẩm.**
**Tệp được ghi theo §39:** `docs/QA_G16.md` (tệp này) · `app/thu/thu_qa_g16.py` (mới) ·
`app/thu/thu_qa_jt.py` (tệp thử **của AG-01** từ G13–G15 — cập nhật theo yêu cầu của AG-00, xem `G16-06`).

**Nền:** `integration/g13-g15`. Mốc đóng băng G16 do AG-00 chốt trong lượt: **`6d05c74`**.
Mọi hợp đồng §1–§41 còn hiệu lực.

**LUẬT VÂN TAY (§41 — AG-00 chốt sau phát hiện `G16-01` của tôi):** mọi con số dưới đây đi kèm
**vân tay cây + mốc giờ + hash tệp được đo**. Không có ba thứ đó thì con số **không dùng được**
để đối chiếu — bốn làn ghi chung một cây, và tôi đã **đo được** vân tay đổi **giữa** lượt chạy.

---

## 0. TÓM TẮT MỘT KHỐI

| Việc | Kết quả đo được |
|---|---|
| Baseline lượt 1 (`449bb2d`, 15:41–15:43) | **exit 0** · **1133 ca** · 34 bộ · tự cộng lại **khớp** |
| Baseline lượt 2 (`449bb2d`, 15:43–15:45) | **exit 0** · **1138 ca** · 34 bộ · tự cộng lại **khớp** |
| Baseline lượt 3 (`6d05c74`, 15:49–15:51) | **exit 1** · 1268 ca · 36 bộ · **2 bộ hỏng**: `thu_qa_g16.py` + `thu_qa_jt.py` |
| Baseline lượt 5 (`6d05c74`, 15:58) | **exit 0** · 1270 ca · 36 bộ · 0 bộ hỏng · tự cộng lại **khớp** |
| **Baseline lượt 7 — LƯỢT CHỐT (`6d05c74`, 16:04:41–16:05:50)** | **exit 0** · **1284 ca** · 36 bộ · **0 bộ hỏng** · tự cộng lại **1284 ✔** · **CÂY ĐỨNG YÊN** |
| **Baseline lượt 8 — TRÊN BẢN ĐÃ COMMIT (`c9fcaef`, 16:14:56–16:16:28)** | **exit 0** · **1284 ca** · 36 bộ · **0 bộ hỏng** · tự cộng lại **1284 ✔** · **CÂY ĐỨNG YÊN** · `git diff HEAD` **RỖNG** |
| Vân tay cây giữa các lượt | **ĐỔI ở 6/8 lượt**; **lượt 7 và 8 ĐỨNG YÊN** (§1.3) |
| Lời khai AG-00 #1 (`main` không chứa G13–G15) | **XÁC NHẬN** — cả ba mệnh đề, đo lại được |
| Lời khai AG-00 #2 (CSDL thật `aaf713…`) | **XÁC NHẬN TUYỆT ĐỐI** — trùng từng ký tự |
| Lời khai AG-00 #2 ("cây sạch") | **ĐÚNG LÚC GHI · SAI VỀ SAU** (§2.2) |
| **G16-A / 1 HTTP TRANSPORT** | **ĐẠT** — **25 ca**, có **hai** phép đột biến chứng minh |
| **G16-A / 2 CREDENTIAL CONFIGURATION** | **ĐẠT** — 13 ca |
| **G16-A / 3 CONTRACT TESTS** | **ĐẠT** — 8 ca |
| Bộ G16-A của AG-01 | `thu_qa_g16.py` · **61 ca · exit 0** · 19,2 giây · thuần trong tiến trình |
| Hồi quy các làn khác trong lượt chốt | `thu_http_jt.py` **37 ca ✓** (AG-02) · `thu_adapter_jt.py` **71 ca ✓** (AG-03) · `thu_qa_jt.py` **22 ca ✓** |
| Phát hiện | **9** (§4): 1 HIGH · 7 MEDIUM · 1 LOW · **8 đã đóng** · **1 CÒN MỞ** (`G16-09`) |

**G16-A ĐẠT ở mức "ba cổng đã đo được", KHÔNG phải "gọi được hãng".** §40 cấm mọi câu đọc như
`LIVE VERIFIED`: chưa có lượt gọi API thật nào, `V-G09-01` + `V-13906-05` **CHƯA CẤP**, và tài liệu
này **không** tuyên bố mức đó.

---

## 1. BASELINE ĐỘC LẬP — số thật, mã thoát thật

### 1.1 Lệnh chạy

```bash
cd /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1      # môi trường git hỏng (AG-00)
rm -rf /tmp/veh_g16_ag01x
VIP_HUB_DATA=/tmp/veh_g16_ag01x sh app/thu/chay_tat_ca.sh; echo "MÃ THOÁT THẬT=$?"
```

**KHÔNG** chạm `:5432` (dữ liệu dự án khác) · **KHÔNG** gọi mạng · **KHÔNG** mở `CHO_PHEP_LIVE`.

### 1.2 Số thật

| Lượt | Mốc | `VIP_HUB_DATA` | Mã thoát | Bộ | Ca in ra | **Ca AG-01 tự cộng** | Khớp | Bộ hỏng |
|---|---|---|---|---|---|---|---|---|
| 1 | `449bb2d` + cây bẩn | `/tmp/veh_g16_ag01` | **0** | 34 | 1133 | **1133** | ✅ | 0 |
| 2 | `449bb2d` + cây bẩn | `/tmp/veh_g16_ag01b` | **0** | 34 | 1138 | **1138** | ✅ | 0 |
| 3 | `6d05c74` | `/tmp/veh_g16_ag01c` | **1** | 36 | 1268 | **1268** | ✅ | 2 |
| 5 | `6d05c74` | `/tmp/veh_g16_ag01e` | **0** | 36 | 1270 | **1270** | ✅ | 0 |
| 6 | `6d05c74` (giữa lượt AG-02/AG-03 sửa) | `/tmp/veh_g16_ag01f` | **1** | 36 | 1271 | **1271** | ✅ | **2** (`thu_http_jt` · `thu_adapter_jt`) |
| 7 | `6d05c74` · `http_jt = 3d9d8f0a` · **cây ĐỨNG YÊN** | `/tmp/veh_g16_ag01g` | **0** | 36 | 1284 | **1284** | ✅ | 0 |
| **8 · CHỐT TRÊN BẢN ĐÃ COMMIT** | **`c9fcaef`** `[integration/g16]` · `git diff HEAD` **RỖNG** · **cây ĐỨNG YÊN** | `/tmp/veh_g16_c9f` | **0** | 36 | **1284** | **1284** | ✅ | **0** |

Cách tự cộng: bóc **từng dòng** `✓ <bộ> <N> ca` rồi cộng bằng `awk` — **không** đọc con số tổng
mà script in. Khớp ở **cả năm** lượt tự cộng được. (Lượt 3: 1190 ca của 34 bộ đạt + 56 `thu_qa_g16` + 22
`thu_qa_jt` = 1268 ✔ — hai bộ hỏng không nằm trong dòng `✓`.)

Ngoài phần Python: frontend tầng 1 **56 ca** · tầng 2 **36 ca** · tầng 3 **KHÔNG chạy** ·
E2E **41/41**, exit 0. **Vân tay + mốc giờ của lượt 5 ở §1.5.**

### 1.3 ⚠️ CÂY KHÔNG ĐỨNG YÊN — vân tay đổi **GIỮA** lượt chạy

Đây là phép đo quan trọng nhất của §1, và nó **hạ thấp** giá trị của mọi con số ở §1.2.

Vân tay = sha256 của danh sách sha256 **mọi** tệp `.py/.mjs/.sh/.json` trong
`app/ gateway/ thu_frontend/ thu_giao_dien/`, sắp `LC_ALL=C sort`.

| Lượt | Mốc giờ | `FP_BEFORE` | `FP_AFTER` | Kết |
|---|---|---|---|---|
| 2 | 15:43–15:45 | `9ce6accf…` | `bd09d610…` | **ĐỔI** |
| 3 | 15:49–15:51 | `e77f34d4…` | `1699e948…` | **ĐỔI** |
| 4 | 15:55–15:56 | `214682bb…` | `ff0180c5…` | **ĐỔI** |
| 5 | 15:58:48–15:59:51 | `e0396466…` | `61fa338e…` | **ĐỔI** |
| 6 | 16:02:22–16:03:25 | `e76366c6…` | `bb11ee74…` | **ĐỔI** |
| 7 | 16:04:41–16:05:50 | `9a72ec87…` | `9a72ec87…` | **ĐỨNG YÊN** ✅ |
| **8 · TRÊN BẢN ĐÃ COMMIT** | **16:14:56–16:16:28** | **`9a72ec87…`** | **`9a72ec87…`** | **ĐỨNG YÊN** ✅ |

**LƯỢT 7 — LƯỢT CHỐT, và là lượt DUY NHẤT ghim được vào một mốc mã:** vân tay **giống nhau trước
và sau** (`9a72ec87…`), `app/http_jt.py` **không đổi** trong lượt (`3d9d8f0a…`), `HEAD = 6d05c74`.
Kết quả: **exit 0 · 1284 ca · 36 bộ · 0 bộ hỏng · tự cộng lại = 1284 ✔**.

**Lượt 8 khớp `HEAD`:** vân tay lượt 8 = `9a72ec87…` = **đúng** vân tay lượt 7, mà lượt 8 chạy trên
cây **đã commit** `c9fcaef` với `git diff HEAD` **RỖNG**. ⇒ **Bản đã commit CHÍNH LÀ cây tôi đã
nghiệm thu ở lượt 7** — không phải suy đoán, mà là hai vân tay bằng nhau cộng với một cây sạch.

⇒ **Sáu lượt đầu KHÔNG ghim được; lượt 7 và 8 ghim được.** Đây là điều đáng nói nhất của §1: cây **có**
những khoảng đứng yên, nên **luật §41 không phải án tử hình** — nó chỉ bắt người báo cáo **chứng minh**
mình đo trong khoảng đứng yên. Lượt 5 (1270) và lượt 7 (1284) **khác nhau 14 ca** mà **cùng một
`HEAD`** — đó chính là lý do không con số nào được dùng mà thiếu vân tay.

**Quy được về ĐÚNG một tệp (lượt 2):** `diff` từng dòng số-ca giữa hai lượt cho **đúng một** khác
biệt — `thu_tich_hop.py` **6 → 11 ca**; 33 bộ còn lại y hệt.

**Mốc thời gian ghim đúng lúc:** `app/cau_hinh.py` ghi `15:43:17` **trong** lượt 1 (log đóng
`15:43:27`) · `app/thu/thu_tich_hop.py` ghi `15:44:15` **trong** lượt 2 · `app/webhook.py` ghi
`15:45:06` · `app/http_jt.py` ghi `15:48:10` **rồi** `15:55:35` — **giữa** các lượt đo của tôi.

**`git status` đi từ 1 → 6 tệp bẩn trong 2 phút**, cùng một phiên.

### 1.4 Hệ quả — điều **KHÔNG** được viết

- **1133 · 1138 · 1268 · 1270 đều là số THẬT**, nhưng **không** con số nào là *"hồi quy của mốc
  `6d05c74`"*. Chúng là ảnh chụp của một cây **đang được ba làn khác ghi**.
- Cổng **F0-a** của tôi (`QA_G13_G15.md` §6.1 — *"cây bẩn ⇒ mọi số đo vô hiệu"*) **không thoả được**
  trong cấu hình bốn làn một cây. Tôi **không** tự miễn cổng đó; tôi **đổi cách khai**: mọi số
  phải kèm **vân tay + mốc giờ + hash tệp**. AG-00 đã nhận và **biến thành luật §41**.
- Đây là **N-05 tái phát lần thứ ba** — cùng một cấu trúc hỏng lại một lần nữa (`CLAUDE.md` §12.2:
  *"hỏng lần thứ hai cùng kiểu thì ĐỔI CẤU TRÚC"*). Lần này cấu trúc **đã đổi**: §41.

### 1.5 PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI

**ĐÃ ĐO:** bộ chạy hồi quy đầy đủ (macOS arm64 · Python 3.9.6 · SQLite 3.51.0) **bốn lượt**, mã
thoát thật, số ca tự cộng lại · mốc git (`main`, `integration/g13-g15`, `HEAD`, `--is-ancestor`,
`branch --contains`, `worktree list`) · sha256 **chỉ đọc** của CSDL thật · trạng thái Git tại nhiều
thời điểm · **ba cổng G16-A** (§3) · **đột biến** chứng minh bộ dò transport dò được (§3.4).

**Hash tệp tại thời điểm đo (chốt, `16:01:34`):**

| Tệp | sha256 |
|---|---|
| `app/http_jt.py` | `97e38a49cdb6f01b69f33bb19d728f27fac64872531edad4336ee88b646d3391` |
| `app/adapter_jt.py` | `7addee61a2c2230eff67156d1ac25300f65ea4732993b85d622759bbe6a5b707` |
| `app/thu/thu_qa_g16.py` | `f341deeafc9bbc18a945d16fb0f12e3d293bc5a941ba63e344cb68e6be15d480` |
| `app/thu/thu_qa_jt.py` | `b93fc2467672c7d0d72ddc68c13644a57f411aecdc5a2be7e2ebac1a3458ffc0` |
| `docs/QA_G16.md` | **KHÔNG ghim ở đây** — xem ghi chú ngay dưới |

**Vì sao KHÔNG ghim hash của chính tài liệu này:** sửa tệp là đổi hash của nó — ghim vào đây thì
lượt sửa kế tiếp **tự làm mình sai**, đúng bẫy `BAN_GIAO.md` §7.3 (*"tệp không tự ghi được SHA của
chính commit chứa nó"*). Ai cần thì đo bằng `shasum -a 256 docs/QA_G16.md`; ghim hash của **tệp
được ĐO** mới có nghĩa, vì đó là thứ phán quyết nói tới.

**`app/http_jt.py` đổi **SÁU LẦN** trong lúc tôi nghiệm thu** — `c0d21201…` (`15:48`) → `1c862635…`
(`15:55:35`) → `58fa6523…` (`16:01:18`) → `97e38a49…` (`16:01:34`) → `50d8301c…` (`16:02:22`) →
**`3d9d8f0a…`** (`16:04:41`, **đứng yên suốt lượt chốt**). Bộ G16-A xanh trên **mọi** bản đã đo,
nhưng điều đó **chỉ** nói được: *"xanh trên sáu bản tôi đã đo"*. Đây là `G16-01` ở dạng **nặng
nhất**: đối tượng được nghiệm thu **tự nó** đổi giữa lượt đo. **Chỉ lượt 7 ghim được** — và vì thế
**chỉ lượt 7** là căn cứ cho phán quyết.

**NGOÀI PHẠM VI — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT:**

| Chưa đo | Vì sao |
|---|---|
| **Gọi API hãng thật (kể cả sandbox)** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** — §37/§40 |
| TLS thật tới `*.jtexpress.vn` | chưa được phép gọi; tôi chỉ đo **danh sách trắng**, không mở TLS |
| `cancelOrder`/`getShippingFee`/`getShippingLabel`/`getOrder` **đầu-cuối** | đường dẫn **CHƯA ĐỌC ĐƯỢC** ⇒ adapter cố ý DỪNG |
| Frontend tầng 3 (DOM/CSS Chromium) | không chạy trong `chay_tat_ca.sh`; cần `sh thu_giao_dien/chay.sh` |
| **V5/V6/V7 toàn cục** (tenant · RBAC · AES đầy đủ) | **vẫn mở** từ `QA_G13_G15.md` §L2.8 — lượt này **không** đóng |
| Đa luồng trên `http_jt` | bộ G16-A chạy **tuần tự** |
| PostgreSQL · VPS · đa tiến trình · Safari/Firefox · dữ liệu lớn | ngoài phạm vi bộ chạy (script tự khai) |

---

## 2. PHÁN QUYẾT HAI LỜI KHAI CỦA AG-00

Nguyên tắc: **đo lại, không tin.**

### 2.1 Lời khai 1 — "`main` KHÔNG chứa G13–G15, `integration/g13-g15` = `449bb2d`"

**PHÁN QUYẾT: ✅ XÁC NHẬN — cả ba mệnh đề.**

```
$ unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
$ git rev-parse main                        → de740dcd16617328f49f5ab97fac3ceb741e39fa
$ git rev-parse integration/g13-g15         → 449bb2de7e0586265321e77bc832652c1408e9f7
$ git merge-base --is-ancestor integration/g13-g15 main ; echo $?   → 1   (THẤT BẠI)
$ git branch -a --contains 449bb2d          → 5 nhánh, KHÔNG có `main`
$ git worktree list                         → 2 cây: `…/Projects/vip-express-hub` [main de740dc]
                                                    `…/Projects-vip-express-hub`  [integration 449bb2d]
```

⇒ Hệ quả vận hành **đúng như AG-00 cảnh báo**: CSDL thật nằm trong cây `main` (**không** có
G13–G15); việc G16 làm ở cây `integration/g13-g15`. **Lời khai 1 đứng vững.**

### 2.2 Lời khai 2 — "cây sạch" + "CSDL thật ở `~/Projects/…/hub.db`, sha256 `aaf713…`"

**PHÁN QUYẾT: ✅ NỬA SAU XÁC NHẬN TUYỆT ĐỐI · ⚠️ NỬA ĐẦU ĐÚNG LÚC GHI RỒI SAI VỀ SAU.**

**(a) CSDL thật — trùng TỪNG KÝ TỰ, chỉ đọc:**

```
$ ls -la ~/Projects/vip-express-hub/app/du-lieu/hub.db
-rw-r--r--@ 1 viporder  staff  200704 Oct 14 23:47 …/hub.db
$ shasum -a 256 …
aaf71362f86f7391f9394f77a5c8a3b24c81e7e1b6ca49da116143eb556d0c54
```

Khớp đường dẫn · kích thước `200.704` byte (đúng §35) · sha256. mtime `Oct 14 23:47` — **không** bị
đụng. Tôi chỉ **đọc** (không mở bằng SQLite, không ghi, không `chmod`). Cây Orca **không** chứa
`hub.db` ⇒ bộ thử **không thể** vô tình chạm CSDL thật.

**(b) "Cây làm việc sạch":** lúc tôi bắt đầu, `git status --porcelain -uall` trả **đúng 1 dòng**
(` M docs/SHARED_CONTRACTS.md`); hai phút sau **6 dòng**. Vậy:

- **Đúng** theo nghĩa *"0 mã sản phẩm dở, 0 stash"* (`git stash list` **rỗng** — đo được).
- **Sai** theo nghĩa chữ *"sạch"*: dòng **duy nhất** bẩn lúc tôi bắt đầu **chính là khối đóng băng
  G16 §36–§40** mà AG-00 đang viết. *"Sạch"* **chưa bao giờ** có nghĩa *"sạch khỏi thay đổi G16"*.
- Và nó **không bền** — nên chỉ đọc được như **ảnh chụp**, không phải **bảo đảm**.

---

## 3. KẾT QUẢ BA CỔNG G16-A — chạy gì, cổng FAIL là gì, đo được gì

**Nguyên tắc:** AG-01 **không tin báo cáo PASS của làn nào**. Mỗi cổng do AG-01 **tự chạy**.
Mọi phép đo lớp HTTP dùng **stub cục bộ `127.0.0.1` CỔNG 0** (§40) — không cổng cố định, nên bốn
làn chung một cây **không tranh cổng** và **không sinh HỎNG GIẢ** (R-13, `QA2_TEST_PLAN.md` §6).

**Bộ thử:** `app/thu/thu_qa_g16.py` — **57 ca · exit 0 · 15,1 giây**, chạy **thuần trong tiến trình**.

**Cổng nền F0 (áp cho mọi mục):** `CHO_PHEP_LIVE` **False** ở **mọi** lớp trong `adapter._DANG_KY`
(vòng lặp động) · `JT_CHO_PHEP_SANDBOX`/`JT_CHO_PHEP_PRODUCTION` **False** · `JT_MOI_TRUONG == "mock"` ·
`sandbox` gọi thử ⇒ nổ **TRƯỚC** khi mở socket (bộ đếm = 0).

**Kỹ thuật chủ đạo — "ĐỒNG HỒ KẾT NỐI":** thay `http.client.HTTPConnection.connect` /
`HTTPSConnection.connect` bằng bộ đếm. Host **bị từ chối** ⇒ ngoại lệ đúng loại **và bộ đếm = 0**;
host **được phép** ⇒ bộ đếm > 0. Nhờ vậy đo được **cả hai host J&T thật** mà **không gửi một byte
nào ra ngoài**.

**Cổng chặn:** mọi phát hiện **CRITICAL**/**HIGH** ⇒ **CHẶN GỘP**; AG-01 **không được miễn trừ**.

### 3.1 G16-A / 1 — HTTP TRANSPORT · **ĐẠT**

Đo trên `app/http_jt.py` @ **`97e38a49cdb6f01b69f33bb19d728f27fac64872531edad4336ee88b646d3391`**
(mtime `16:01`). **25 ca.**
*(Bản đầu tôi đo là `c0d21201…`; tệp đổi **ba lần** trong lúc nghiệm thu — xem §1.5 và `G16-05`.)*

| Nhóm | Ca | Kết quả đo |
|---|---|---|
| HTTP **thật** trên loopback | `t1` | stub nhận **POST**, `Content-Type: application/x-www-form-urlencoded`, thân `bizContent=%7B%7D` **nguyên văn**; `TraLoiHTTP.ma_http == 200`; **đúng 1** lượt nối |
| Stub **chỉ** loopback | `t2` | `getsockname()[0] == "127.0.0.1"`; kết nối từ IP không-loopback **thất bại** |
| **Danh sách trắng** — đối chứng dương | `t3`, `t12b`, `t12c` | loopback **đi qua** (bộ đếm ≥ 1); **cả hai host J&T đi qua cổng danh sách trắng rồi mới bị bộ đếm chặn** (bộ đếm = 1); host hãng **buộc https:443** |
| **Danh sách trắng** — 13 ca phủ định | `t4`–`t12` | `evil.example` · `127.0.0.1.evil.example` · `127.0.0.1@evil.example` · `demoopenapi.jtexpress.vn.evil.example` · host-trong-query · `2130706433` · `0.0.0.0` · `127.1` · `file://` · `ftp://` · `gopher://` · `HTTP://EVIL.EXAMPLE` — **tất cả TỪ CHỐI, bộ đếm nối = 0** |
| **Chuyển hướng** | `t11` | stub trả `302 Location: http://evil.example/` ⇒ **KHÔNG đi theo**, ném `LoiVinhVien`, `ket_cuc = hang-tu-choi` |
| **Hết giờ** | `t13`, `t13b` | stub ngủ 3 s · `timeout=0.5` ⇒ **huỷ sau 0,5 s** (đồng hồ tường < 2,0 s), `LoiTamThoi`, `timeout=True`, `ket_cuc = khong-biet`; **kết cục thứ ba KHÔNG BAO GIỜ trả về `TraLoiHTTP`**. Đối chứng dương: cùng stub, `timeout=8` ⇒ 200 |
| `5xx` → tạm thời | `t14` | `/500`, `/503` ⇒ `LoiTamThoi`, `timeout=True`, `ket_cuc = khong-biet` |
| `4xx` → vĩnh viễn **(TRỪ 408/429)** | `t15` | `/400`, `/401`, `/403`, `/404` ⇒ `LoiVinhVien`, `timeout=False`, `ma_http` đúng |
| **`429`/`408` → TẠM THỜI** (hợp đồng AG-00 chốt) | `t22` | `429` ⇒ `LoiTamThoi`, `ket_cuc = qua-han-muc` · `408` ⇒ `LoiTamThoi`, `ket_cuc = khong-gui-di`. **Đối chứng âm:** 400/401/403/404 **vẫn** `LoiVinhVien` — bản vá **không** được nới cả 4xx |
| `Retry-After` đọc được và **kẹp trần** | `t23` | `Retry-After: 5` ⇒ `cho_giay == 5.0` · `Retry-After: 86400` ⇒ `cho_giay == 60.0` (`transport.CHO_TOI_DA`) · không có header ⇒ vẫn tạm thời |
| `gui_form` **KHÔNG BAO GIỜ NGỦ** | `t24` | soát **AST** trên `gui_form` (không `sleep`/`wait`) **và** thay `time.sleep` bằng hàm ném rồi gọi thật — nếu lớp này ngủ thì `so_lan=3` nhân thời gian chờ lên 3 |
| `cho_giay` vào đúng chỗ | `t25` | `transport.goi()` lấy **max** với backoff rồi **kẹp trần**: gợi ý 3660 s ⇒ chờ **đúng** 60 s |
| **KHÔNG tự thử lại** | `t16`, `t17a`–`t17d` | một `gui_form` ⇒ stub nhận **ĐÚNG 1** yêu cầu kể cả khi hãng `500`; `chinh_sach_cho("createOrder").duoc_thu_lai is False` · `so_lan == 1`; mở thử lại **chỉ** khi có khoá chống trùng; **`txlogisticId` có THẬT trong `bizContent`** (nếu thiếu thì cờ `KHOA_CHONG_TRUNG=True` là NGUY HIỂM); tầng adapter: một lượt ⇒ tối đa `cs.so_lan`, `5xx` ⇒ `timeout=True` |
| **Không rò bí mật** | `t18a`, `t18b` | canary 16 ký tự **không** xuất hiện trong `str(e)`/`repr(e)`/`args`/`traceback`/`thân đã che`/`header đã che`/`mô tả yêu cầu`/`logging` ở **bốn** đường lỗi; **giá trị 5 ký tự dưới tên trường credential cũng KHÔNG rò** (xem `G16-05`) |
| Thân **nguyên văn** | `t19` | byte không-UTF-8 + CRLF về **đúng từng byte** |
| Không rò trạng thái toàn cục | `t20` | `socket.getdefaulttimeout()` **không đổi** sau một lượt hết giờ |
| `repr` không in thân | `t21` | `repr(TraLoiHTTP)` không chứa thân |

### 3.2 G16-A / 2 — CREDENTIAL CONFIGURATION · **ĐẠT**

13 ca. Bề mặt **đã có** (`cau_hinh.JT_TRUONG_CREDENTIALS` · `.env.example` khối G16 · `jt_kiem_moi_truong`).

| Ca | Đo được |
|---|---|
| `c1` | 4 TÊN đúng, tách **2 lớp** (nền tảng / bưu cục), giao nhau **rỗng** |
| `c2` | `.env.example` khai **TÊN**, **không** gán giá trị; bộ dò `.env` có **đối chứng dương** |
| `c3` | **không** có `.env` thật; `.gitignore` chặn `.env`, `.env.*`, mở `!.env.example` |
| `c4` | `git ls-files` chỉ có **`.env.example`** trong họ env |
| `c5` | quét **AST** 30+ mô-đun sản phẩm: **0** secret hard-code; **đối chứng dương**: mẫu bịa **bị bắt**, **tiêm secret thật vào bản sao `transport.py` cũng BỊ BẮT**; 5 mẫu dương-tính-giả của lượt đầu **không** bị kêu (xem `G16-07`) |
| `c6`·`c7`·`c10` | đường lưu **duy nhất**: bản mã `v3$<key_id>$<nonce>$<ct>` (4 phần, `key_id` khác rỗng); **bản rõ không lọt vào bản mã**; khứ hồi **bằng nhau**; hai lượt mã hoá ⇒ **hai bản mã khác nhau** (nonce ngẫu nhiên) |
| `c8`·`c9` | AAD **sai tenant** / **sai hãng** ⇒ **KHÔNG** giải ra bản rõ |
| `c11` | tiến trình con in `JT_TRUONG_CREDENTIALS` ⇒ **chỉ TÊN**, không giá trị |
| `c12` | `sandbox`/`production` **TỪ CHỐI kèm lý do đọc được**; `mock` mở |
| `c13` | DDL `carrier_accounts`: **không** có cột credentials bản rõ (chỉ `credentials_ma_hoa`, `credentials_duoi`, `credentials_doi_luc`, `webhook_secret_ma_hoa`) |

### 3.3 G16-A / 3 — CONTRACT TESTS · **ĐẠT**

8 ca.

| Ca | Đo được |
|---|---|
| `h1` | chữ ký **byte-đúng-từng-byte**: 4 vector **tính tay ngoài bộ thử** (3 vector khớp bản ghim của AG-03 + 1 vector **mới** `('bizContent-JSON','KHOA-THU-KY') → 9JF//h1VnUXFVQ3jeWrTMQ==`); **đột biến**: `hexdigest→base64` **KHÁC** bản đúng (bộ dò phân biệt được), độ dài 24 |
| `h2`·`h2b` | mốc **13 chữ số mili giây**, lệch < 5 s; **mốc naive KHÔNG phụ thuộc múi giờ máy** — đo trong **4 tiến trình con** (`UTC`, `Etc/UTC`, `America/New_York`, `Asia/Ho_Chi_Minh`) đều **bằng nhau** ⇒ đóng `L2-N2` của tôi |
| `h3` | COD đi **`codMoney`** (chuỗi số nguyên), **KHÔNG** `itemsValue`; COD = 0 **vẫn gửi trường** |
| `h4` | **ba kết cục không gộp**: `ok` · hãng từ chối (`timeout=False`) · **KHÔNG BIẾT** (`timeout=True`) — cặp `(ok, timeout)` **khác nhau** |
| `h5` | chống đơn trùng bằng **`UNIQUE(tenant_id, idem_key)` ở CSDL**, không phải `if` trong mã |
| `h6` | cô lập tenant trên credentials (nối `c8`) |
| `h7` | **chốt D-9 CÒN NỔ**: `sandbox`/`production` ⇒ ném kèm chữ `D-9`; mở `CHO_PHEP_LIVE` rồi dựng `bizContent` thật ⇒ **vẫn DỪNG**; `CAP_HANH_CHINH_CHO_AREA == "quan-huyen"`; `CITY_CO_GUI is False`; `ANH_XA_AREA_DA_XAC_NHAN is False`; **đối chứng dương**: `mock` đi qua |
| `h8` | mã **chưa xác minh** (`110`, `9999`, `0`, `-1`, `""`) **không** ra `giao_thanh_cong`, **không** nhãn `OK`; **đối chứng dương**: `113/103/106` ra đúng `giao_thanh_cong`/`cho_lay`/`lay_hang` với nhãn `OK` |

### 3.4 HAI CHỐT CHẶN TỰ CAM KẾT (§6.3) — **đã có thật, và đang làm việc**

1. **Tự kiểm bộ dò** — `E_TuKiemBoDo` (5 ca): `e1` chạy ca **CỐ Ý HỎNG** trong tiến trình con ⇒ bộ
   dò **thấy** hỏng (mã thoát ≠ 0, phán `HỎNG`) · `e2` **đối chứng dương** (ca đạt ⇒ exit 0,
   `Ran 1 test`, `OK`) · `e3` hai chiều phán **KHÁC NHAU** · `e4` dòng phạm vi **phải** nói `BỎ QUA`
   khi thiếu lớp HTTP. `e1`/`e2`/`e3` chép **đúng luật phán quyết** của `chay_tat_ca.sh` (mã thoát +
   dấu vết + số ca > 0) ra để **đo chính luật đang dùng**, không đo cảm giác.
2. **Đối chứng dương cho MỌI ca phủ định** — sổ `DOI_CHUNG`; `Z_TongKet.z1` **tự báo HỎNG** nếu
   nhóm nào có ca âm mà **0** ca dương. **Chốt này đã thật sự chặn trong lượt** (nó đỏ khi tôi còn
   thiếu đối chứng cho `a3`/`d9`/`ma-chua-xac-minh`) — AG-00 đã kiểm và ghi nhận.
   Sổ cuối lượt: `a3 1/1` · `aad 1/1` · `cod 1/1` · `credentials 2/3` · `d9 1/1` ·
   `danh-sach-trang 13/2` · `het-gio 1/1` · `khong-tu-thu-lai 3/4` · `ma-chua-xac-minh 1/1` ·
   `ma-http 2/1` · `ro-bi-mat 2/2`.

**ĐỘT BIẾN chứng minh bộ dò dò được** — `e5`: sao `app/http_jt.py` sang `/tmp`, phá
`host_duoc_phep` thành `return True`, nạp bản đã phá qua `sys.modules` (không đụng tệp của AG-02),
chạy lại **đúng ba ca canh** danh sách trắng ⇒ **PHẢI đỏ**, và tôi khẳng định nó **đỏ thật**
(exit ≠ 0, `Ran 3 tests`). Không có ca này thì "13 ca danh sách trắng xanh" **không chứng minh gì**.

**Đột biến thứ hai — hợp đồng `429`/`408`:** sao `http_jt.py`, đổi `if ma_http in (408, 429):`
thành `if False:` (tức 408/429 quay về "4xx vĩnh viễn") ⇒ chạy lại `t22`/`t23` ⇒ **ĐỎ thật**
(`Ran 2 tests · FAILED (errors=4)`). Cổng mới **có răng**, không phải ca trang trí.

---

## 4. PHÁT HIỆN

Định dạng: **mức · tái hiện · nguyên nhân gốc · mong đợi · thực tế · cách sửa bắt buộc.**
**Cả 7 phát hiện đã đóng trong lượt** — 5 do làn sở hữu sửa, 2 do chính AG-01 sửa.

### `G16-01` · **HIGH (vận hành)** · Baseline **không ghim được vào một mốc mã** — ba làn ghi đè giữa lượt chạy · **ĐÃ ĐÓNG (luật §41)**

- **Tái hiện:** `FP(); VIP_HUB_DATA=/tmp/x sh app/thu/chay_tat_ca.sh; FP` — `FP` là vân tay ở §1.3.
- **Nguyên nhân gốc:** bốn làn ghi **đồng thời** vào **cùng một cây**; hạ tầng chặn ghi `.git` nên
  không tách worktree được (§39). `chay_tat_ca.sh` **tự dò** `thu_*.py` nên tệp mới/bị sửa **tự vào**
  lượt chạy của **mọi** làn.
- **Mong đợi:** một baseline dùng được để đối chiếu phải ghim được vào **một** vân tay cây.
- **Thực tế:** vân tay **đổi ở cả ba lượt đo được**, kể cả **giữa** một lượt; toàn bộ chênh lệch
  lượt 2 quy về **một** tệp (`thu_tich_hop.py` 6→11); `cau_hinh.py` ghi **trong** lượt 1;
  `http_jt.py` ghi `15:48:10` **rồi** `15:55:35` **giữa** các lượt của tôi.
- **Cách sửa:** AG-00 chọn phương án **(c)** và **biến thành luật §41**: mọi báo cáo có số đo phải
  kèm **vân tay cây + mốc giờ**; §35 là bản ghi **lịch sử**, không phải hiện trạng. **Đã đóng.**

### `G16-02` · **MEDIUM** · Khối đóng băng G16 **KHÔNG nằm trong Git** · **ĐÃ ĐÓNG (`6d05c74`)**

- **Tái hiện (lúc đo):**
  ```bash
  git show HEAD:docs/SHARED_CONTRACTS.md | grep -c 'HỢP ĐỒNG LỚP HTTP'   # → 0
  git show HEAD:.env.example | grep -ci jt                              # → 0
  git show HEAD:app/cau_hinh.py | grep -c JT_MOI_TRUONG                 # → 0
  git diff HEAD --stat        # SHARED_CONTRACTS +97 · .env.example +31 · cau_hinh.py +66
  ```
- **Nguyên nhân gốc:** AG-00 soạn §36–§40 + bề mặt cấu hình G16 **sau** commit `449bb2d` và **chưa
  commit** ⇒ `HEAD` không chứa chúng; `git checkout -- .` / `git stash` xoá **cả ba**, không cảnh báo.
- **Mong đợi:** hợp đồng **đã đóng băng** phải nằm trong Git.
- **Thực tế:** cả ba tệp **chưa** commit. Bảng **§35** còn ghi *"Cây làm việc Orca | sạch"* — nay **sai**.
- **Cách sửa:** AG-00 **commit** `6d05c74` gồm §36–§41 + `.env.example` + `app/cau_hinh.py` +
  `thu_tich_hop.py`, và sửa §35 thành bản ghi **lịch sử**. **Đã đóng** — tôi đo lại: `HEAD = 6d05c74`.

### `G16-03` · **MEDIUM** · Ca thử ghim **trạng thái tiến độ** thay vì **bất biến an toàn** · **ĐÃ ĐÓNG**

- **Tái hiện:** `grep -n 'TRANSPORT_THAT_DA_VIET' app/adapter_jt.py app/thu/thu_hop_dong_jt.py`
- **Nguyên nhân gốc:** ca `thu_hop_dong_jt.e3` khẳng định `TRANSPORT_THAT_DA_VIET is False` — một
  hằng viết tay nói *"lớp HTTP chưa được viết"*. G16 **đảo** sự thật đó ⇒ ca **đỏ dù mã đúng**.
  Hai nửa của cùng bất biến nằm ở **hai làn** (`http_jt.py` của AG-02; `adapter_jt.py` +
  `thu_hop_dong_jt.py` của AG-03).
- **Mong đợi:** canh **cổng thật** (`CHO_PHEP_LIVE`, cổng môi trường, 0 socket), không canh
  **sự tồn tại của một tệp** — thứ sẽ còn đổi nữa.
- **Thực tế:** AG-03 đã đổi thành phép **DÒ ĐỘNG** (`TRANSPORT_THAT_DA_VIET = _co_http_jt()`) và
  **viết lại** `e2`/`e3` để đo **cửa môi trường** và **cửa đường dẫn** trực tiếp. Tôi kiểm lại:
  `e2` khẳng định `sandbox` ném `PermissionError` chứa `V-G09-01`; `e3` đo `chan_duong_chua_xac_nhan`.
  **Đã đóng.** Bản sao của cùng lỗi trong **tệp của tôi** xem `G16-06`.

### `G16-04` · **LOW** · `app/thu/thu_tich_hop.py` **không thuộc làn nào** trong §39 · **ĐÃ ĐÓNG**

- **Tái hiện:** `grep -n 'thu_tich_hop' docs/SHARED_CONTRACTS.md` → **không** dòng nào (lúc đo).
- **Nguyên nhân gốc:** §39 khai 5 làn và tệp của từng làn; tệp này **không** có tên ⇒ ai cũng sửa
  được, không ai chịu trách nhiệm.
- **Thực tế:** tệp **được sửa thật** (`6 → 11 ca`) trong lúc tôi chạy baseline — chính là nguồn của
  `G16-01`.
- **Cách sửa:** AG-00 đã đưa tệp vào mốc `6d05c74`. **Đã đóng.**

### `G16-05` · **MEDIUM (đã đóng trong lượt)** · Giá trị credentials **ngắn hơn ngưỡng che** rò **NGUYÊN VĂN**

- **Tái hiện (trên `app/http_jt.py` @ `c0d21201…`, mtime `15:48`):**
  ```python
  http_jt.gui_form("http://127.0.0.1:<cổng>/echo-header",
                   {"apiAccount": "Ab1!x"},              # 5 ký tự — NGẮN hơn ngưỡng 8
                   {"bizContent": '{"password": "Ab1!x"}'}, timeout=5)
  ```
  → `LoiVinhVien` với `str(e)` **chứa** `Ab1!x` ⇒ `rò qua HEADER = True`.
- **Nguyên nhân gốc:** `_gia_tri_can_che` chỉ gom giá trị có `len >= DAI_TOI_THIEU_DE_CHE` (**8**).
  Giá trị credentials ngắn hơn 8 (`apiAccount` dạng số · `customerCode`/`password` ngắn của bưu cục)
  **không** vào tập che. Thông điệp `http-4xx` lại **kèm 200 byte đầu của thân trả lời** ⇒ hãng chỉ
  cần echo lại header/thân là giá trị lọt vào **thông điệp ngoại lệ**, và từ đó vào **log**.
- **Mong đợi:** **không** giá trị credentials nào ra khỏi tiến trình, **bất kể độ dài**.
- **Thực tế:** đo được **hai đường khác nhau** — qua **thân form** thì **không** rò (giá trị bị
  percent-encode), qua **header** thì **rò** (`rò qua HEADER = True`). Ghi lại vì **hai đường cho
  hai câu trả lời khác nhau**: kết luận "không rò" chỉ từ đường thân form là **kết luận sai**.
- **Cách sửa (AG-02 đã làm, đúng cách):** che theo **TÊN TRƯỜNG** — `TRUONG_CREDENTIAL`
  (`apiaccount`, `privatekey`, `customercode`, `password`) che **bất kể độ dài**; ngưỡng 8 chỉ còn
  áp cho giá trị **không** mang tên credential. **Đã đóng tại `1c862635…`**; tôi **đo lại**:
  `rò qua HEADER = False`, và cổng `t18b` (mới) **ghim bất biến đó** để không quay lại cách cũ.
  *(AG-02 không thấy tin này của tôi trước khi vá — bản vá của họ trùng đúng hướng tôi đề nghị.)*

### `G16-06` · **MEDIUM** · **Tệp thử của AG-01** ghim sự thật đã đổi, làm **ĐỎ lượt hồi quy chung** · **ĐÃ ĐÓNG (AG-01 tự sửa)**

- **Tái hiện:**
  ```bash
  VIP_HUB_DATA=/tmp/x python3 app/thu/thu_qa_jt.py    # → exit 1
  TZ=UTC VIP_HUB_DATA=/tmp/x python3 -m unittest \
      app.thu.thu_qa_jt.B_MocThoiGian.test_b4_ky_tu_thoi_gian_naive_la_diem_MO_can_va   # → FAIL
  ```
- **Nguyên nhân gốc — hai ca, hai kiểu hỏng khác nhau:**
  - `test_a5` khẳng định `TRANSPORT_THAT_DA_VIET is False`. AG-02 giao `http_jt.py` ⇒ cờ **đúng** là
    `True` ⇒ ca **đỏ dù mã đúng**.
  - `test_b4` ghim hành vi **CŨ**: mốc naive bị hiểu theo **múi giờ máy**. AG-03 đã vá (naive ⇒ gắn
    UTC+7 tường minh). Trên máy đặt **UTC+7** (máy này) hai cách hiểu **trùng nhau** nên ca **xanh
    giả**; trên máy `TZ=UTC` ca **đỏ** và sẽ chỉ người sau đi **"sửa" đúng chỗ mã đang đúng**
    — đúng cái bẫy `BAN_GIAO.md` §7.1/§7.2.
- **Mong đợi:** ca thử canh **bất biến an toàn**, không canh **trạng thái tiến độ**; và **xanh ở mọi
  `TZ`**.
- **Thực tế:** lượt 3: `1268 ca · bộ hỏng: thu_qa_g16.py thu_qa_jt.py` — **AG-01 là làn duy nhất
  đang làm đỏ hồi quy chung** (AG-00 phát hiện và báo).
- **Cách sửa (đã làm):** `test_a5` bỏ mệnh đề cờ, thay bằng `assertIsInstance(..., bool)` +
  ghi rõ cờ là **trạng thái tiến độ**; `test_a6` viết lại thành **cổng thật** — chặn
  `http.client.*Connection.connect` bằng bộ đếm, khẳng định **0 lần ĐỊNH nối** ở **mọi** môi trường,
  kèm **đối chứng dương** (`mock` đi qua); `test_b4` viết lại thành bất biến **MỚI**, đo trong **bốn**
  tiến trình con `TZ`. Đo lại: **22 ca · exit 0** ở **cả** `TZ` mặc định **và** `TZ=UTC`.

### `G16-07` · **MEDIUM (tự phát giác)** · Bộ dò "secret hard-code" của **AG-01** kêu **5/5 DƯƠNG TÍNH GIẢ** · **ĐÃ ĐÓNG**

- **Tái hiện (bản đầu):** `thu_qa_g16.test_c5` → FAIL với 5 mục; **cả 5** đều không phải bí mật:
  `ai_job.py:158,161` là **KHOÁ dict TÀI LIỆU** (câu văn giải thích thứ gì bị CẤM gửi cho AI);
  `harness_hang.py:695,696,944` là **fixture** tự khai (`KHOA-BI-MAT-XYZ`, `MK-THU`).
- **Nguyên nhân gốc:** bộ dò `search` tên nhạy cảm trên **cả dòng**, rồi coi **mọi** literal cùng
  dòng là bí mật — kể cả **khoá dict** và literal trong **câu văn**.
- **Vì sao nặng hơn một lỗi nhỏ:** cổng CRITICAL kêu nhầm **5/5** thì **không còn chặn được gì** —
  nó bị **học cách bỏ qua**, đúng khuôn §7.1. AG-00 đã đọc từng dòng và báo lại.
- **Cách sửa (đã làm, 4 luật):** (1) chỉ quét **mô-đun sản phẩm**, **miễn** `app/thu/*` + harness;
  (2) chỉ xét literal ở **vế phải phép gán** hoặc **giá trị của dict** — khoá dict phải là **định
  danh** (`privateKey`), câu văn bị loại; (3) đòi **độ mạnh** (≥ 12 ký tự, ≥ 2 loại ký tự) và
  **không** mang dấu hiệu giữ chỗ (`MOCK`, `THU`, `XYZ`, `DEMO`, `TEST`, `BI-MAT` …), từ ngắn khớp
  theo **ranh giới** để không bỏ sót bí mật thật; (4) giữ **đối chứng dương**, thêm **đột biến**:
  tiêm secret thật vào **bản sao `transport.py`** ⇒ bộ dò **PHẢI** bắt. Đo lại: `0` phát hiện trên
  30+ mô-đun sản phẩm, và **6 mẫu đối chứng** (1 bắt buộc bắt + 5 bắt buộc không kêu) đều đúng.

### `G16-08` · **MEDIUM** · **Toàn bộ sản phẩm G16-A KHÔNG nằm trong Git** · **ĐÃ ĐÓNG (`6bae1bc`…`c9fcaef`)**

**Bằng chứng đóng (AG-01 đo lại, `16:14`, cây `c9fcaef`):** `git ls-files` theo dõi **13 tệp** G16
(`app/http_jt.py` · `app/thu/stub_jt.py` · `app/thu/thu_http_jt.py` · `app/thu/thu_qa_g16.py` ·
`app/thu/thu_qa_jt.py` · 4× `docs/G16_*.md` · `docs/QA_G16.md` · 4× `trien_khai/g16/**`) —
trước mốc là **0**. `6bae1bc` chứa **2090 dòng** gồm cả bộ thử và tài liệu của tôi. **Đã đóng.**
*(Ghi chú nhỏ: lệnh AG-00 trích trong báo cáo — `grep -E 'http_jt|G16_'` — cho **6**, không phải 13;
con số **13** đúng khi tính **đủ bộ §39**. Kết luận đúng, chỉ lệnh trích là thiếu.)*

- **Tái hiện (`16:01:15`):**
  ```bash
  unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
  git rev-parse HEAD                # 6d05c74
  git status --porcelain -uall | grep -E 'http_jt|G16|QA_G16'
  ```
  → **17 dòng**, trong đó **`??` (CHƯA TỪNG được Git biết)**:
  ```
  ?? app/http_jt.py            ?? docs/G16_TRANSPORT.md
  ?? app/thu/stub_jt.py        ?? docs/G16_JT_API.md
  ?? app/thu/thu_http_jt.py    ?? docs/G16_WEBHOOK.md
  ?? app/thu/thu_qa_g16.py     ?? docs/G16_SANDBOX_HARNESS.md
  ?? docs/QA_G16.md            ?? trien_khai/g16/**
  ```
  và **` M` (đã theo dõi, chưa commit)**: `app/adapter_jt.py` · `app/webhook.py` ·
  `app/thu/thu_adapter_jt.py` · `app/thu/thu_webhook_jt.py`.
  
  Kiểm chéo: `git ls-files | grep -E 'http_jt|QA_G16|stub_jt'` → **RỖNG**.
- **Nguyên nhân gốc:** `G16-02` đã đóng cho **hợp đồng** (§36–§41 — nay ở `6d05c74`), nhưng **sản
  phẩm của G16-A** ra đời **sau** mốc đó và chưa ai commit. Mốc `6d05c74` chỉ chứa **4 tệp**
  (`.env.example`, `app/cau_hinh.py`, `app/thu/thu_tich_hop.py`, `docs/SHARED_CONTRACTS.md`) —
  **không** chứa lớp HTTP.
- **Mong đợi:** thứ được nghiệm thu phải **nằm trong Git** trước khi có kết luận nghiệm thu.
- **Thực tế:** **lớp HTTP — đối tượng chính của cổng G16-A/1 — là tệp CHƯA ĐƯỢC GIT BIẾT.** Cùng với
  nó: bộ thử của AG-02, stub, cả bốn tài liệu làn, bộ thử của tôi, tài liệu này, và `trien_khai/g16/`.
  Một `git clean -fd` hoặc `git stash -u` xoá **toàn bộ** G16-A — **không một cảnh báo**, và
  `git status` sau đó vẫn "sạch".
- **Vì sao MEDIUM chứ không thấp hơn:** rủi ro không nằm ở *khả năng xảy ra* mà ở **bán kính**:
  mất một lượt là mất **cả** lớp vận chuyển, ba bộ thử và bốn tài liệu — và **không** có mốc nào
  để dựng lại, vì chưa từng có commit.
- **Cách sửa bắt buộc (AG-00):** commit **một mốc G16-A** gồm `app/http_jt.py` · `app/thu/stub_jt.py` ·
  `app/thu/thu_http_jt.py` · `app/thu/thu_qa_g16.py` · `app/thu/thu_qa_jt.py` · `app/adapter_jt.py` ·
  `app/webhook.py` · `app/thu/thu_adapter_jt.py` · `app/thu/thu_webhook_jt.py` · bốn `docs/G16_*.md` ·
  `docs/QA_G16.md` · `trien_khai/g16/**` — rồi **ghi hash tệp vào §41** như mốc G16-A.
  **Không** tự commit được: hạ tầng chặn ghi `.git` (§39), nên đây **phải** là việc của AG-00.

### `G16-09` · **MEDIUM · CÒN MỞ** · **LUẬT VÂN TAY §41 MÙ với `docs/`** — kể cả với chính bản hợp đồng đã đóng băng

- **Tái hiện (`16:17`, cây `c9fcaef`, `git diff HEAD` RỖNG):**
  ```bash
  FP() { find app gateway thu_frontend thu_giao_dien -type f \
           \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
           | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256; }
  FP                                                    # 9a72ec87…
  printf '\n<!-- THU NGHIEM -->\n' >> docs/SHARED_CONTRACTS.md
  FP                                                    # 9a72ec87…   ← KHÔNG ĐỔI
  git status --porcelain docs/SHARED_CONTRACTS.md       #  M docs/SHARED_CONTRACTS.md
  ```
  ⇒ Sửa **chính bản hợp đồng đã đóng băng** mà vân tay **không nhúc nhích một ký tự**.
  *(Đã hoàn tác nguyên trạng; `git status` sau hoàn tác = rỗng.)*
- **Nguyên nhân gốc:** lệnh vân tay mà §41 chép lại **chỉ quét 4 thư mục `app/ gateway/ thu_frontend/
  thu_giao_dien` và 4 đuôi `.py/.mjs/.sh/.json`**. `docs/` **không** nằm trong phạm vi, `.md` cũng
  không. Và đây là **lỗi của chính tôi**: lệnh đó do tôi viết ra (§1.3), rồi AG-00 chép **nguyên văn**
  vào luật. Tôi đã tự kiểm cái mình viết — và nó **hổng**.
- **Vì sao MEDIUM chứ không thấp hơn:** §41 tồn tại để bảo đảm *"con số nào cũng đối chiếu được với
  một cây"*. Nó **mù đúng ở tệp quan trọng nhất** — §36–§41, thứ định nghĩa ba cổng tôi đang nghiệm
  thu. Một lượt sửa hợp đồng giữa lượt đo sẽ **lọt qua** cả vân tay **và** mắt người đọc §41.
- **Bằng chứng cụ thể trong chính lượt này:** `docs/G16_ACCEPTANCE.md` **được tạo lúc `16:15:11`** —
  **giữa** lượt đo của tôi (`16:14:56`–`16:16:28`) — mà **vân tay trước = sau**. `git status` đi từ
  **0 → 1 dòng**. Nếu tôi chỉ ghi vân tay mà không ghi `git status`, tôi đã **không thấy** nó.
  *(Đây cũng là dữ kiện cho câu "bốn làn đã DỪNG": có một tệp mới ra đời trong lượt — không phải mã,
  nên **không** làm hỏng phép đo, nhưng nói đúng rằng cây **chưa** hoàn toàn đứng yên.)*

- **Ví dụ sống, ngay sau lượt chốt:** `HEAD` đi `c9fcaef` → **`eb6cb3a`**, và **vân tay KHÔNG đổi**
  (`9a72ec87…`). Vân tay **một mình** không nói được đó là *"chỉ thêm một tài liệu"* hay *"không ai
  đụng gì"* — cả hai đều cho cùng một con số. Thứ **chứng minh được** là Git:
  `git diff --name-only c9fcaef eb6cb3a` → **đúng một** đường dẫn, `docs/G16_ACCEPTANCE.md`, **không**
  tệp `.py/.sh/.mjs/.json` nào. Nhờ vậy tôi nói được câu có căn cứ: **lượt đo trên `c9fcaef` vẫn
  đúng cho `eb6cb3a`**, vì **mã không đổi một byte**.
  ⇒ Đây là lý do **cụ thể** để đảo thứ tự ưu tiên ở mục *cách sửa* dưới đây.
- **Cách sửa bắt buộc — và nay đã làm được, rẻ hơn trước:** cây đã **commit và sạch**, nên **thứ tự
  ưu tiên đảo lại**:
  1. **Khóa bằng Git là chính:** `git rev-parse HEAD` + **`git diff HEAD` phải RỖNG** +
     `git status --porcelain -uall` phải **RỖNG**. Cách này phủ **mọi tệp được theo dõi**, kể cả
     `docs/**`, `.env.example`, `.gitignore` — **mạnh hơn** vân tay.
  2. **Vân tay chỉ còn là phương án DỰ PHÒNG** cho lúc cây **bẩn** (bốn làn cùng ghi) — và khi đó
     phải mở rộng phạm vi: thêm `docs` và `-name '*.md'` + các tệp cấu hình ở gốc, **hoặc** ghi kèm
     `git status --porcelain -uall` để phần ngoài phạm vi vân tay **vẫn nhìn thấy được**.
- **Ai sửa:** AG-00 (chủ `SHARED_CONTRACTS.md` §41). Đây là **sửa luật**, không phải sửa mã.

### Ghi chú (KHÔNG phải phát hiện) — `carrier_accounts.credentials_duoi`

`app/csdl.py` khai `credentials_duoi TEXT NOT NULL DEFAULT ''` — *"4 ký tự cuối để hiển thị"*. Đây là
**thiết kế đã chốt** cho màn hình phân biệt tài khoản, **không** phải đường rò mới. Ghi ra vì cổng
`c13` quét lược đồ này; nếu sau ai thêm cột credentials bản rõ thì `c13` **phải** đỏ. **Không** đề
nghị đổi.

### Ghi chú — thứ tự hai cổng chặn trên đường `createOrder`

Trên `sandbox`, `createOrder` ném **chốt D-9** (`NormalizedCarrierError`) **trước** cửa môi trường
(`PermissionError`), vì D-9 nằm ở chỗ **dựng `bizContent`** còn cửa môi trường nằm ở chỗ **chuẩn bị
gửi**. **Cả hai đều chặn cứng và đều mở 0 socket**, nên **không phải lỗ hổng**; chỉ là thông điệp
người vận hành nhận được **chưa phải** cái §37 muốn hỏi trước tiên. Ghi lại, **không** đề nghị sửa
trong lượt này.

---

## 5. ĐIỀU TÔI **CHƯA** ĐO ĐỘC LẬP (nói thẳng — LỖ HỔNG PHẠM VI, không phải ĐẠT)

| Cổng | Vì sao chưa | Cần gì để đóng |
|---|---|---|
| **Gọi hãng thật (kể cả sandbox)** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** | phiếu duyệt của Owner — **G16-A không thể** tự đạt mức này (§40) |
| **TLS thật tới `*.jtexpress.vn`** | chưa được phép gọi | chỉ đo được **danh sách trắng**; TLS thật **chưa** đo |
| **`cancelOrder`/`getShippingFee`/`getShippingLabel`/`getOrder` đầu-cuối** | đường dẫn **CHƯA ĐỌC ĐƯỢC** ⇒ adapter cố ý DỪNG | J&T trả lời `docs/JT_CAU_HOI_CHINH_THUC.md` |
| **V5/V6/V7 toàn cục** (tenant · RBAC · AES đầy đủ) | **vẫn mở** từ `QA_G13_G15.md` §L2.8 | bộ ca riêng — lượt này **không** đóng |
| Frontend tầng 3 (DOM/CSS Chromium) | không chạy trong `chay_tat_ca.sh` | `sh thu_giao_dien/chay.sh` |
| **Đa luồng trên `http_jt`** | bộ G16-A chạy **tuần tự** | chưa đo tranh chấp khi nhiều luồng cùng `gui_form` |
| **Nhánh `integration/g16` chưa gộp vào `main`** | `--is-ancestor` vẫn **thất bại** (đúng như thiết kế) | việc gộp là quyết định của AG-00/anh Thành — **không** thuộc G16-A |
| **Harness SANDBOX của AG-04** (`trien_khai/g16/**`) | AG-00 chạy riêng (*"đạt 32 · ĐẠT (MOCK) 12 · BLOCKED 2"*); tôi **chưa** dựng phép đo độc lập cho nó | bộ ca riêng — **không** tính là AG-01 đã nghiệm thu |
| PostgreSQL · VPS · đa tiến trình · Safari/Firefox · dữ liệu lớn | ngoài phạm vi bộ chạy | theo `G12_POSTGRES.md` / `G11_FINAL_REPORT.md` |

---

## 6. LỆNH CHẠY LẠI (cho người nghiệm thu kế tiếp)

```bash
cd /Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1

# 0) VÂN TAY CÂY — BẮT BUỘC, trước và sau (luật §41)
find app gateway thu_frontend thu_giao_dien -type f \
  \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) \
  | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256

date '+%H:%M:%S'; git rev-parse HEAD main integration/g13-g15
shasum -a 256 app/http_jt.py app/adapter_jt.py app/cau_hinh.py   # ghim tệp ĐƯỢC ĐO

# 1) baseline đầy đủ
rm -rf /tmp/veh_g16_ag01 && VIP_HUB_DATA=/tmp/veh_g16_ag01 sh app/thu/chay_tat_ca.sh
echo "MÃ THOÁT THẬT=$?"          # phải tự cộng lại từng dòng '✓ <bộ> <N> ca'

# 2) bộ G16-A của AG-01
rm -rf /tmp/veh_g16_ag01_qa && VIP_HUB_DATA=/tmp/veh_g16_ag01_qa python3 app/thu/thu_qa_g16.py
echo "MÃ THOÁT THẬT=$?"

# 3) CSDL THẬT — CHỈ ĐỌC, không mở bằng SQLite
shasum -a 256 ~/Projects/vip-express-hub/app/du-lieu/hub.db
# phải là aaf71362f86f7391f9394f77a5c8a3b24c81e7e1b6ca49da116143eb556d0c54
```

**Cấm:** gọi hãng thật (kể cả sandbox) · mở `CHO_PHEP_LIVE` · chạm `:5432` · push/deploy ·
đưa secret vào log/prompt.
