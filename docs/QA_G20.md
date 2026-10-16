# NGHIỆM THU G20 — AG-01 (QA/VERIFIER) · LƯỢT 1: BASELINE ĐỘC LẬP + KẾ HOẠCH CÓ CỔNG FAIL

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_a59477417511` · **Dispatch:** `ctx_54d46c95b4f3`
**Nền đo:** `integration/g19 @ 148ecd380a9009c7b01dc0c268a3f1a97327a164` — **NỀN ĐÓNG BĂNG**,
worktree riêng `g20-ag01-qa`. **KHÔNG** dùng `main` (`de740dc`, không chứa G13–G20).
**Hai tệp AG-01 G20 được phép tạo (và là hai tệp DUY NHẤT đã tạo):**
`app/thu/thu_qa_g20.py` (**21 ca**, 985 dòng, `sha256 5a4b3c83c45f2f2c465d2eed380f1f6f69583878ca9e3a5f910bd01c1a0ddcd0`)
· `docs/QA_G20.md` (tài liệu này).

> **Vì sao ghi SHA của tệp kia mà không phải của chính tài liệu này:** một tệp **không tự ghi được
> SHA của chính nó** (`BAN_GIAO.md` §7.3 — dòng SHA sẽ đổi chính tệp đang chứa nó). Nên tôi ghim
> SHA của **bộ kiểm** — thứ sinh ra mọi con số dưới đây. Mọi số ở §1–§3 đều đo bằng **đúng bản
> `5a4b3c83…`** này.

**Lệnh chạy bộ kiểm của tôi:**

```sh
python3 app/thu/thu_qa_g20.py                      # làn MẶC ĐỊNH — 21 ca · 0 hỏng · 2 bỏ qua · exit 0
VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py   # NGHIỆM THU BẢN ĐÃ GỘP — 5 cổng ĐỎ trên nền
VIP_G20_DAY_DU=1 python3 app/thu/thu_qa_g20.py     # + hồi quy toàn phần qua chay_tat_ca.sh
```

**Tôi là NGƯỜI KIỂM, không phải người viết.** Lượt này tôi **không sửa một dòng mã sản phẩm nào**:
`git diff --stat` và `git diff --cached --stat` đều **RỖNG** (§1.3). Tìm thấy lỗi thì ghi lại và
báo cáo — việc của lượt này là **baseline độc lập** + **kế hoạch nghiệm thu có cổng FAIL rõ ràng**
+ **bộ kiểm đã dựng sẵn cho lượt gộp**.

> **MỘT CÂU PHẢI NÓI NGAY, KHÔNG GIẤU Ở CUỐI TÀI LIỆU.** Tôi đã hỏi AG-00 danh sách mục của wave
> G20 (để §2 khớp từng mục với từng làn) bằng `orca orchestration ask` — **hai lượt, tổng 20 phút,
> KHÔNG có trả lời** (`messageId: msg_7b93a1080577`, vẫn đang chờ). Nên **danh sách cổng ở §2 do
> TÔI SUY RA TỪ BẰNG CHỨNG ĐO ĐƯỢC trong repo** (`QA_G19.md` §4–§5, `BAN_GIAO.md` §6.1,
> `G16_G25_LOCAL_PLAN.md` §4), không phải từ một bảng phân công. Cấu trúc thì vẫn đúng cho mọi
> danh sách: **mỗi mục một cổng, mỗi cổng một điều kiện ĐỎ, và một giá trị "nửa vời" luôn ĐỎ.**

**Luật bằng chứng tự áp:** mọi khẳng định dưới đây đi kèm **lệnh thật + mã thoát thật + số ca thật
+ số bỏ qua**. Mã thoát lấy **ngay sau lệnh**, không qua ống. **Hai chốt chặn bắt buộc** (§3):
(a) ca TỰ KIỂM BỘ ĐO chạy trong **tiến trình con**; (b) **ĐỐI CHỨNG DƯƠNG** cho **mọi** ca phủ
định, có sổ `DOI_CHUNG` và `Z1` tự phán HỎNG nếu thiếu. Cái gì không đo được thì nằm ở **§5 CHƯA
ĐO** — đó là **lỗ hổng phạm vi, KHÔNG phải ĐẠT**.

---

## ⛔ KHÔNG KẾT LUẬN NGHIỆM THU — ĐỌC DÒNG NÀY TRƯỚC MỌI CON SỐ

**Lượt này KHÔNG phải một nghiệm thu, và TÔI KHÔNG TUYÊN BỐ G20 ĐẠT.** Ba con số dưới đây hay bị
đọc nhầm thành "xanh", nên chúng được nói thẳng ở đây:

| Lệnh | Kết quả thật | **Nghĩa của nó — và KHÔNG phải nghĩa gì** |
|---|---|---|
| `python3 app/thu/thu_qa_g20.py` | `Ran 21 tests · OK (skipped=2) · EXIT=0` | **Đây là CHẾ ĐỘ NỀN.** Nó xanh vì **năm khoản nợ đang ĐÚNG NHƯ ĐÃ KHAI** trên nền `148ecd3` — **KHÔNG** có nghĩa G20 đạt |
| `VIP_G20_DAY_DU=1 python3 app/thu/thu_qa_g20.py` | `Ran 21 tests · OK (skipped=1) · EXIT=0` | `H1` xanh vì nó **PHÂN LOẠI ĐƯỢC** mọi bộ đỏ, **KHÔNG** phải vì hết bộ đỏ. **Hồi quy chung vẫn `exit 1` với 2 bộ hỏng**, và **tầng 3 vẫn KHÔNG đạt** |
| `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` | `FAILED (failures=5, skipped=2) · EXIT=1` | **Đây mới là phán quyết nghiệm thu.** **CẢ NĂM cổng G20 ĐỎ** |

**Trạng thái thật của G20 hôm nay: NĂM KHOẢN NỢ CÒN NGUYÊN · TẦNG 3 KHÔNG ĐẠT · HỒI QUY CHUNG `exit 1`.**
Việc còn lại là **Dispatch lượt 2** để nghiệm thu bản **đã gộp** — xem §7.

---

## 0. BẢNG PHÁN QUYẾT — NĂM CỔNG G20, KÈM **CỔNG FAIL**

Cột **CỔNG FAIL** là điều kiện làm mục đó **ĐỎ** — đọc cột đó trước cột phán quyết. Cột
**NỀN `148ecd3`** là con số **tôi đo được hôm nay**, không chép của ai.

| # | Khoản nợ (nguồn) | **CỔNG FAIL (điều kiện ĐỎ)** | Cách đo (`thu_qa_g20.py`) | NỀN `148ecd3` |
|---|---|---|---|---|
| **C1** | **N-G19-03**: cổng "cây sạch" của wave trước miễn trừ theo **tên cứng** | **< 2/2** cổng cũ XANH khi cây chỉ có hai tệp AG-01 G20 hợp lệ · **hoặc** giá trị **= 1** (nửa vời) | `G1` (chạy 2 cổng trong tiến trình con) | **ĐỎ** — **0/2** |
| **C2** | **V-13911 phần còn lại**: bàn phím **TRONG màn** (menu đã xong ở G19) | tầng 3 đặc tả `06_ban_phim.spec.js` **≠ (7 ĐẠT, 0 HỎNG, 0 KHÔNG CHẠY)** | `B1` (Chromium thật) + `B2` | **ĐỎ** — **(3, 1, 3)**; ca 04 chỉ vào được **1** điều khiển trong màn (ngưỡng đặc tả `>10`) |
| **C3** | **N-G18-00**: `GIT_CONFIG_*` dị dạng ⇒ **mọi** lệnh git thoát **128** | `git rev-parse HEAD` với môi trường **nguyên bản** thoát **≠ 0** | `C1` + `C2` | **ĐỎ** — thoát **128** |
| **C4** | **C6 của G19** (nửa vời): migration v9 **đã gộp**, `truy_van.py` **chưa có đường vào** | cặp `(schema_ok, route_ok)` **≠ (True, True)** | `C4` | **ĐỎ** — **(True, False)**: `PHIEN_BAN_SCHEMA=9`, `nang_len_v9=True`, **0** tệp SẢN XUẤT import `truy_van` |
| **C5** | **N-G20-01** (tôi phát hiện): **không** bộ thử G19-tổng-hợp nào chạy trên cây đã gộp | **0** bộ `thu_qa_g19*.py` chạy được ≥1 ca | `C5` | **ĐỎ** — **0/1**: `thu_qa_g19.py` tự BỎ QUA; `thu_qa_g19_tich_hop.py` **không tồn tại** |
| **A** | Cửa an toàn tuyệt đối (LIVE · D-8 · `:5432` · `127.0.0.1`) | bất kỳ mục nào ở §6 đỏ | `A1`–`A4`, `Z2`, `Z3` | **ĐẠT** — 4/4 |

**Phán quyết một dòng của lượt 1:** nền `148ecd3` **không tự chạy xanh** — `sh app/thu/chay_tat_ca.sh`
cho **exit 1 · 1733 ca · 47 bộ · 1 bộ hỏng**; tôi **đo độc lập và xác định được nguyên nhân thật**
của bộ đỏ đó (**không phải** lý do được nêu trong đề bài — §4.1), và **năm khoản nợ G20 đều còn
nguyên với con số của từng khoản**. Bộ kiểm đã sẵn sàng cho lượt gộp: **hai chốt chặn bắt buộc đã
chạy thật** (§3), và ở chế độ `VIP_G20_CHE_DO=gop` **cả năm cổng ĐỎ** (`FAILED (failures=5)`) —
tức "cổng có răng" đã được đo, không phải hứa.

**Bốn phát hiện mới:** `N-G20-01` (TRUNG BÌNH — không bộ thử G19-tổng-hợp nào chạy; tệp mà bộ thử
G19 chỉ sang **không tồn tại**), `N-G20-02` (CAO — cổng duy nhất làm hồi quy ĐỎ **không phải** cổng
cây sạch như mô tả, mà là **một lỗ hổng sản phẩm có thật và TẤT ĐỊNH**), `N-G20-03` (TRUNG BÌNH —
một ca Playwright hỏng làm **3 ca khác KHÔNG HỀ CHẠY**, và không dòng báo cáo nào nói ra), và
**hai lỗi của chính bàn đo tôi** (§4.4) — trong đó một lỗi gây **đệ quy vô hạn** thật.

---

## 1. BASELINE ĐỘC LẬP TRÊN NỀN ĐÓNG BĂNG

### 1.0 Vân tay cây + HEAD — **chụp TRƯỚC mọi lượt chạy**

```sh
git rev-parse HEAD
git status --porcelain=v1 -uall
git ls-files -s | shasum -a 256
find . -path ./.git -prune -o -path ./node_modules -prune -o -type f -print | sort | shasum -a 256
```

| Mốc | **TRƯỚC** (00:45:04Z) | **SAU** (00:54:54Z) |
|---|---|---|
| `git rev-parse HEAD` | `148ecd380a9009c7b01dc0c268a3f1a97327a164` | **không đổi** |
| `git status --porcelain=v1 -uall` | **RỖNG** | **RỖNG** |
| `git ls-files -s \| shasum -a 256` | `ad19a3320eb428ce80fd392313292c25064da0f62c81b171c69b9ff3c2cc16a1` | **KHÔNG ĐỔI** |
| Số tệp được theo dõi | **291** | **291** |
| Băm **cả cây làm việc** | `032f41142122785bfa66cfa1a8e2d77f25a0bf7e8baa11d90ddf6e2c737edb12` | `90e6f226fcb7d956d0c11cdbee9851900fddefcde1761505d8db561e3ee12845` |

> **VÌ SAO HAI VÂN TAY THÔ KHÁC NHAU MÀ CÂY VẪN LÀ "KHÔNG ĐỔI" — và đây là một bài học đo lường.**
> `git status --porcelain` **RỖNG cả hai lượt**, `git ls-files -s` **không đổi**, nhưng băm **cả cây
> làm việc** lại đổi. Nguyên nhân **đo được**, không phải phỏng đoán — đúng những tệp này sinh ra
> trong lượt chạy:
>
> ```
> app/du-lieu/khoa-noi-bo.key                      (sinh lại khoá nội bộ)
> thu_giao_dien/_bao-cao/**                        (báo cáo HTML của Playwright)
> thu_giao_dien/_ket-qua/**                        (trace.zip của ca hỏng)
> ```
>
> Cả ba đều nằm trong `.gitignore` (`.gitignore` dòng 33–34), nên `porcelain` không thấy chúng.
> **Hệ quả phương pháp:** một bộ kiểm băm **cả cây làm việc** sẽ báo "cây đã đổi" sau **mỗi** lượt
> chạy — một nhiệt kế đo nhầm thứ, và là nhiệt kế sẽ bị học cách bỏ qua. Bộ kiểm của tôi vì thế
> băm **cây ĐƯỢC THEO DÕI** (`Z2`), và `Z2` **TRƯỚC = SAU** trong cùng một lượt.

### 1.1 N-G18-00 **tái diễn lần thứ ba** — đo trực tiếp, không qua bộ chạy

```sh
git rev-parse HEAD          # KHÔNG gỡ biến môi trường
# → error: missing config key GIT_CONFIG_KEY_0
#   fatal: unable to parse command-line config
#   exit=128
```

| Phép đo | Số thật |
|---|---|
| `GIT_CONFIG_COUNT` thừa hưởng | **2** |
| Số biến `GIT_CONFIG_KEY_*` | **0** |
| Số biến `GIT_CONFIG_VALUE_*` | **2** |
| `git rev-parse HEAD` môi trường **nguyên bản** | **exit 128** |
| Cùng lệnh, **đã gỡ** gia đình biến | **exit 0** · `148ecd3…` |

Bộ chạy chung in dòng đầu tiên của log:
`[cảnh báo] GIT_CONFIG_COUNT=2 nhưng thiếu GIT_CONFIG_KEY_* — gỡ gia đình GIT_CONFIG_* dị dạng`.
⇒ **Vá trong BỘ CHẠY đã có tác dụng** (hồi quy không còn ĐỎ vì nó), **nhưng GỐC CHƯA VÁ**: bất kỳ
ai gọi `git` trực tiếp vẫn nhận **128**. Bộ kiểm của tôi cũng phải tự gỡ (`_git()`), và cổng **C3**
canh đúng chỗ đó.

### 1.2 Lượt chạy độc lập của bộ chạy chung — **trên cây SẠCH**

```sh
sh app/thu/chay_tat_ca.sh        # log thô: /tmp/ag01-g20/baseline_raw.txt
# 00:45:09Z → 00:54:51Z  (5 phút 42 giây)
# === EXIT CODE THAT = 1
```

| Chỉ tiêu | **Số TÔI đo** |
|---|---|
| **Mã thoát** | **1** |
| Số **ca** python | **1733** |
| Số **bộ** chạy thật | **47** |
| Số **bộ hỏng** | **1** — `thu_qa_g18.py` (43 ca, exit 1) |
| Số bộ **BỎ QUA** (0 ca) | **1** — `thu_qa_g19.py` (`BỎ QUA  không nêu cách bật`) |
| Frontend tầng 1 + 2 | **56 + 36** ca |
| E2E qua HTTP thật | **41/41** phép đo |
| Tầng 3 trong lượt chung | **KHÔNG chạy ở mục riêng** — nhưng **CÓ chạy** bên trong `thu_qa_g18.py` (§1.4) |
| Môi trường | `Darwin arm64` · python **3.9.6** · SQLite **3.51.0** |

**Con số của tôi TRÙNG con số AG-00 công bố (1733 ca · 47 bộ) — nhưng tôi đo ra chúng, không chép.**
Và **AG-00 đúng ở số bộ hỏng: đúng MỘT bộ, đúng `thu_qa_g18.py`**. Chỗ tôi **không** khớp là **LÝ DO**
— xem §4.1.

### 1.3 Cây có bị đụng không — bằng chứng mạnh hơn cả vân tay

Sau khi tạo **cả hai** tệp được phép:

```sh
git status --porcelain=v1 -uall
# ?? app/thu/thu_qa_g20.py
# ?? docs/QA_G20.md
git diff --stat          # RỖNG
git diff --cached --stat # RỖNG
git ls-files -s | shasum -a 256
# ad19a3320eb428ce80fd392313292c25064da0f62c81b171c69b9ff3c2cc16a1   ← KHÔNG ĐỔI
```

**`git diff --stat` RỖNG nghĩa là 0 byte mã sản phẩm bị sửa** — kể cả sau khi tôi đã chạy **nhiều
lượt tầng 3 Chromium**, dựng máy chủ trên nền tạm, và chạy hồi quy toàn phần.

### 1.4 **Bộ đỏ duy nhất** — đo tới đáy, không dừng ở dòng tóm tắt

`chay_tat_ca.sh` chỉ in được **một** dòng cho bộ đỏ:

```
  ✗ thu_qa_g18.py              43 ca  HỎNG (mã thoát 1)
        FAIL: test_b1_tang_3_chay_duoc_va_khong_co_ca_hong (__main__.B_Tang3)
```

Tôi chạy **hai phép đo tách rời** để biết **ca nào** hỏng và **vì sao**:

```sh
# (a) cổng "cây sạch" của g18, chạy RIÊNG, trên cây SẠCH
python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01
# → Ran 1 test in 0.043s · OK · EXIT=0
#   [A1] cây sạch (miễn trừ ('docs/QA_G18.md', 'app/thu/thu_qa_g18.py')) · vân tay=07b12b09…

# (b) ca tầng 3, chạy RIÊNG
python3 app/thu/thu_qa_g18.py B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong
# → Ran 1 test in 119.460s · FAILED (failures=1) · EXIT=1
#   [B1] nhị phân: chỉ định BAN_GIAO §1 (chromium-1194) · mã thoát=1 · 47 đạt · 1 hỏng · 3 bỏ qua
```

⇒ **Cổng "cây sạch" của g18 XANH trên cây sạch.** Bộ đỏ **không** phải cổng cây sạch.

---

## 2. KẾ HOẠCH NGHIỆM THU G20 — CỔNG, CÁCH ĐO, VÀ ĐIỀU KIỆN ĐỎ

Bộ kiểm `app/thu/thu_qa_g20.py` hiện thực hóa kế hoạch này. **Cơ chế cốt lõi** — mỗi cổng có một
**SỔ HAI Ô** ghi hai giá trị **đã đo được**:

```
"nen"  = giá trị trên nền đóng băng 148ecd3   (nợ CÒN NGUYÊN)
"dong" = giá trị khi khoản nợ đã đóng          (điều kiện nghiệm thu)

giá trị == "nen"     -> NEN
giá trị == "dong"    -> DONG
giá trị KHÁC CẢ HAI  -> NUA_VOI  ==> LUÔN ĐỎ, ở mọi chế độ
```

**Ô thứ ba là chỗ tôi cố ý làm CHẶT HƠN khuôn G19** (chỉ có hai ô MỞ/ĐÓNG). Ở G19, một bản vá
lửng lơ vẫn có thể được đọc là "chưa gộp"; ở đây nó là một **phán quyết riêng và là ĐỎ**. Ví dụ
đúng thứ wave này có thể gặp: sửa được **2/5** màn, hay tầng 3 còn **`2 did not run`** — cả hai
đều **không** rơi vào ô nào và bị chặn. `T4` chứng minh bằng máy: **3 giá trị nửa vời bị phán
`NUA_VOI` ở CẢ HAI chế độ**, còn **giá trị ĐÓNG của cả 3 cổng đều qua được**.

Thêm chế độ **`VIP_G20_CHE_DO=gop`** cho **lượt nghiệm thu bản ĐÃ GỘP**: khi đó ô `NEN` **cũng ĐỎ**
⇒ nợ chưa đóng **không thể lọt qua** bằng cách viện cớ "nền còn đóng băng".

### 2.1 CỔNG C1 (N-G19-03) — tệp ĐƯỢC PHÉP TẠO không được làm cổng cũ ĐỎ — **ĐỎ**

**Cách đo (`G1`)**: chạy 2 cổng cây sạch của wave trước **trong tiến trình con**:

```sh
python3 app/thu/thu_qa_g17.py A_Nen.test_a1_cay_sach_va_head
python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01
```

| Phép đo | Số thật trên nền |
|---|---|
| `thu_qa_g17.py` (cây có tệp AG-01 G20) | **exit 1** |
| `thu_qa_g18.py` (cây có tệp AG-01 G20) | **exit 1** |
| Cổng XANH | **0 / 2** |
| Miễn trừ của g18 nhận ra **tệp của chính nó** | **True** (cơ chế còn sống, không phải cổng hỏng sẵn) |
| Miễn trừ của g18 có nhận tệp AG-01 G20? | **False** (đây chính là lỗi) |

**Giá trị "đóng" (2/2) CHỨNG MINH ĐƯỢC LÀ TỚI ĐƯỢC** — đối chứng dương của `G1`:
`thu_qa_g17._cay_ban(ngoai=('docs/QA_G20.md','app/thu/thu_qa_g20.py'))` → **`[]`**, tức nếu cổng
miễn trừ **theo quy tắc** thì nó **XANH**. Không có phép kiểm này thì "0/2" có thể chỉ là một cổng
hỏng vĩnh viễn, chứ không phải một khoản nợ.

### 2.2 CỔNG C2 (V-13911 phần còn lại) — bàn phím **TRONG màn** — **ĐỎ**

**Cách đo (`B1`)**: dựng máy chủ trên nền cô lập (bind `127.0.0.1`, cổng OS cấp) rồi chạy **đúng
khuôn `thu_giao_dien/chay.sh`**, chỉ khác **đường nhị phân Chromium**:

```sh
npx playwright test 06_ban_phim.spec.js      # qua driver của thu_qa_g20.py
```

| Phép đo | Số thật trên nền |
|---|---|
| Bộ ba (ĐẠT, HỎNG, **KHÔNG CHẠY**) | **(3, 1, 3)** |
| Mã thoát Playwright | **1** |
| Ca hỏng | `06_ban_phim.spec.js:153 › 04 — Tab vào được các điều khiển TRONG màn, không chỉ quanh menu` |
| **Điểm dừng Tab vào được điều khiển TRONG màn** | **1** (đặc tả đòi **`> 10`**) |
| Số đích khác nhau / số lượt ở `body` | **30 / 0** |
| **3 ca KHÔNG HỀ CHẠY** | ca **05** (Đăng xuất bằng bàn phím) · ca **06** (TỰ KIỂM gỡ `ban_phim.js`) · ca **07** (bố cục hẹp) |

Dòng đo thô trong log (`tang3_ban_phim.log`):

```
[đo] 30 lượt Tab: 1 điểm dừng là điều khiển trong màn · 0 lượt ở body · 30 đích khác nhau
Error: 30 lượt Tab chỉ vào được 1 điều khiển trong màn
Expected: > 10   Received: 1
1 failed · 3 did not run · 47 passed (2.0m)
```

**Tính TẤT ĐỊNH — đo 2/2 lượt, không phải chập chờn:** lượt trong `chay_tat_ca.sh` và lượt chạy
riêng đều cho **đúng cùng một ca hỏng, cùng một con số** (§1.4). Tôi **không** gọi nó là chập chờn.

### 2.3 CỔNG C3 (N-G18-00) — `git` môi trường nguyên bản — **ĐỎ**

Xem §1.1. Giá trị: **128** (nền) → **0** (đóng). Đối chứng dương: **cùng lệnh**, chỉ khác là đã gỡ
gia đình biến ⇒ **exit 0** và ra đúng `148ecd3…`.

### 2.4 CỔNG C4 — C6 của G19 **NỬA VỜI** — **ĐỎ**

```sh
python3 app/thu/thu_qa_g20.py C4_C5_NoKhac.test_c4_route_truy_van_va_migration_v9
```

| Phép đo | Số thật |
|---|---|
| `csdl.PHIEN_BAN_SCHEMA` | **9** |
| `migrate.nang_len_v9` tồn tại | **True** |
| Tệp **SẢN XUẤT** (ngoài `app/thu/**`) import `truy_van` | **0** |
| Nơi DUY NHẤT import `truy_van` | `app/thu/thu_truy_van.py` — **chính bộ thử của nó** |
| `app/truy_van.py` | **có tồn tại** (30.770 byte, có `DDL_G12Q`) nhưng **chưa ai gọi** |
| Cặp giá trị | **(True, False)** |

⇒ **Migration đã gộp, đường vào CHƯA có.** Đây là ví dụ **THẬT** của ô `NUA_VOI`: cổng C6 của G19
được tuyên bố đóng, nhưng chỉ đóng **một nửa**. Một mô-đun chỉ được **bộ thử của chính nó** gọi là
mô-đun **không có đường vào** — đúng khuôn `V-13910`.

### 2.5 CỔNG C5 (N-G20-01) — **không** bộ thử G19-tổng-hợp nào chạy — **ĐỎ**

```sh
python3 app/thu/thu_qa_g19.py
# → Ran 0 tests in 0.011s · OK (skipped=1) · EXIT=0
#   skipped 'BỘ ĐO NỀN — HEAD 148ecd3 != nền đóng băng 6e61fc1. … Nghiệm thu cây ĐÃ GỘP thuộc
#            bộ riêng `thu_qa_g19_tich_hop.py`.'
ls app/thu/thu_qa_g19_tich_hop.py
# → No such file or directory
```

| Phép đo | Số thật |
|---|---|
| Bộ khớp `thu_qa_g19*.py` | **1** — `thu_qa_g19.py` |
| Bộ đó chạy được ≥1 ca trên cây này | **KHÔNG** (0 ca, tự bỏ qua) |
| Tệp mà chính nó chỉ sang | **KHÔNG TỒN TẠI** |
| Bộ G19-tổng-hợp chạy thật | **0 / 1** |

**Hệ quả vận hành, nói thẳng:** con số **"1733 ca · 47 bộ"** mà mọi báo cáo trích dẫn **KHÔNG chứa
một cổng G19-tổng-hợp nào**. Sáu cổng C1–C6 của G19 (trần theo số bản · bộ đếm qua khởi động lại ·
21 mã VTP · màn chết · bàn phím · route `truy_van`) **không được canh bởi bộ chạy chung**. Các bộ
**của từng làn** (`thu_g19_gioihan.py` 22 ca · `thu_g19_route.py` 49 ca · `thu_g19_vtp.py` 31 ca)
**có** chạy — nhưng đó là bộ **do người viết viết**, không phải cổng **đối chiếu độc lập**.

---

## 3. HAI CHỐT CHẶN BẮT BUỘC

### 3.1 CHỐT (a) — ca TỰ KIỂM BỘ ĐO chạy trong **TIẾN TRÌNH CON**

Không có mục này thì mọi dòng `✓ … ca` của tệp tôi **không chứng minh gì**. Vì sao **tiến trình
con** chứ không phải gọi hàm tại chỗ: một ca tự kiểm gọi thẳng hàm trong **cùng** tiến trình vẫn
có thể "xanh" nhờ trạng thái đã bị chính bộ thử làm bẩn. Chạy bằng `subprocess` thì tiến trình mới
**hoàn toàn**, và cái được kiểm là **đúng thứ người chấm sẽ chạy**: `python3 <tệp> <ca>`.

| Ca | Phép đo | Kết quả thật |
|---|---|---|
| `T2` | tiến trình con chạy ca **CỐ Ý HỎNG** (`T_TuKiem.test_z9_…`) | **thoát 1** + có `FAILED` ⇒ luật phán trả **HỎNG** |
| `T2` | **ĐỐI CHỨNG DƯƠNG**: cùng tệp, tiến trình con chạy ca **ĐẠT** (`T1`) | **thoát 0** + có `OK` |
| `T1` | luật phán phải **TỪ CHỐI** bốn kiểu "xanh giả" | `ok,0-ca` → HỎNG · `ok,không-dấu-vết` → HỎNG · `OK` rồi thoát 1 → HỎNG · `Ran 0 tests`+`OK` → HỎNG · `Ran 5 tests`+`OK`+thoát 0 → **ĐẠT** |
| `T3` | bộ đếm Playwright phải đọc ra **cả bốn** con số | `1 failed / 3 did not run / 47 passed` → **(47, 1, 0, 3)** ✓ |
| `T5` | **chốt chống ĐỆ QUY**: `bo_bien` phải gỡ **thật** biến khỏi tiến trình con | có gỡ → `CO=False` · không gỡ → `CO=True` |

`T5` tồn tại vì **lượt đo đầu của tôi đã ĐỆ QUY VÔ HẠN thật** — xem §4.4.

### 3.2 CHỐT (b) — ĐỐI CHỨNG DƯƠNG cho **mọi** ca phủ định

Sổ `DOI_CHUNG` in ra ở `Z1`. `Z1` **tự phán HỎNG** nếu một nhóm có ca ÂM mà thiếu ca DƯƠNG, và
**tự kiểm chính nó**: một nhóm âm **cố ý** không có dương **phải** bị nó bắt (`Z1` khẳng định
`nhom_thieu_duong({"nhom-gia-thieu-duong": …}) == ["nhom-gia-thieu-duong"]`), và một nhóm đã đủ hai
chiều **không** được báo động giả.

```
  [Z1] bo-g19-tong-hop        âm=1 dương=1
  [Z1] cong-cay-sach          âm=1 dương=1
  [Z1] cum-5432               âm=1 dương=1
  [Z1] dem-playwright         âm=1 dương=1
  [Z1] git-tho                âm=1 dương=1
  [Z1] go-bien                âm=1 dương=1
  [Z1] goc-do                 âm=1 dương=1
  [Z1] live-khoa              âm=1 dương=1
  [Z1] luat-phan              âm=1 dương=1
  [Z1] nua-voi                âm=1 dương=1
  [Z1] sqlite-D8              âm=1 dương=1
  [Z1] tang3-ban-phim         âm=1 dương=1
  [Z1] tang3-so-do            âm=1 dương=1
  [Z1] truy-van-C6            âm=1 dương=1
  [Z1] tu-kiem-con            âm=1 dương=1
  [Z1] 15 nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả
```

Mỗi cặp nằm trên **cùng một hàm đo**, nên không thể có chuyện hàm đo hỏng mà cả hai cùng xanh.
Ví dụ cụ thể: `git-tho` có ca **âm** (môi trường nguyên bản, phải khác 0) và ca **dương** (đã gỡ
biến, phải bằng 0) — **cùng một lệnh `git rev-parse HEAD`**; `dem-playwright` có ca âm (output tổng
hợp có `did not run`) và ca dương (output sạch).

### 3.3 Làn ĐẦY ĐỦ (`VIP_G20_DAY_DU=1`) — hồi quy toàn phần

```sh
VIP_G20_DAY_DU=1 python3 app/thu/thu_qa_g20.py
# → Ran 21 tests in 649.945s · OK (skipped=1) · EXIT=0
#   log thô hồi quy: $TMPDIR/veh_g20_ag01_qa_log/hoi_quy.log
```

**Chạy HAI lượt làn đầy đủ, con số TRÙNG KHỚP** (`Ran 21 tests in 650.529s · OK (skipped=1)`, `H1`
lượt 2: **1754 ca · 48 bộ · 1 bỏ qua · 2 hỏng · 448,1s**) — chỉ thời gian chênh, không con số nào
chênh. Đây là lượt chạy lại **sau khi** mọi sửa đổi của tôi đã đóng băng (`sha256 5a4b3c83…`).

**Log thô giữ lại để đối chiếu (không nằm trong repo — chỉ hai tệp AG-01 được phép tạo):**

| Log | Đường | `sha256` |
|---|---|---|
| Làn đầy đủ lượt 2 (`daydu3`) | `/tmp/ag01-g20/g20_daydu3.txt` | `4e32887889df6229af3de307381fff9b0a42ad5abc962e480e8ec3b018f5de1b` |
| Baseline nền (§1.2) | `/tmp/ag01-g20/baseline_raw.txt` | `dc43994a656fabd63a7bbbe69475f5396e570514a5e1c4676c5f7caf15d6f014` |
| Hồi quy chung NGUYÊN VĂN bên trong `H1` | `$TMPDIR/veh_g20_ag01_qa_log/hoi_quy.log` | — |
| Tầng 3 đặc tả bàn phím | `$TMPDIR/veh_g20_ag01_qa_log/tang3_ban_phim.log` | — |

Hai dòng quyết định, trích NGUYÊN VĂN từ `hoi_quy.log`:

```
  python:   1754 ca · 48 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_qa_g19.py
  bộ hỏng:  thu_qa_g17.py thu_qa_g18.py
  ✓ thu_qa_g20.py              21 ca
  E2E:      KẾT QUẢ: 41/41
```

| Ca | Phép đo | **Số thật** |
|---|---|---|
| `H1` | `sh app/thu/chay_tat_ca.sh` NGUYÊN VĂN (cờ làn đầy đủ **đã gỡ**, có ca `T5` canh) | **thoát 1** · **1754 ca** · **48 bộ chạy thật** · **1 bộ BỎ QUA** (`thu_qa_g19.py`) · **450,7 giây** |
| `H1` | bộ hỏng | **2**: `thu_qa_g17.py` · `thu_qa_g18.py` — **cả hai rơi vào nhóm CÓ TÊN** |
| `H1` | ca hỏng | **4**: `thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` · `thu_qa_g18.py::A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` · `thu_qa_g18.py::Z_TongKet.test_z2_cay_khong_doi_trong_luot_do` · `thu_qa_g18.py::B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong` |
| `H1` | phân loại | `thu_qa_g17.py → N-G19-03` · `thu_qa_g18.py → N-G19-03 + N-G18-01` · **0 bộ đỏ VÔ DANH** |
| `H1` | **HỎNG SẢN PHẨM (ngoài hai khoản nợ đã ghi)** | **KHÔNG** |
| `H1` | **cổng "teo ca"** | **1754 = 1733 + 21** ✓ · **48 = 47 + 1** ✓ |
| `H1` | bộ của tôi trong lượt chung | **`✓ thu_qa_g20.py 21 ca`** |
| `H1` | frontend · E2E | **56 + 36** ca · **KẾT QUẢ: 41/41** |

**Phép cộng này là một đối chứng độc lập:** lượt chạy nền cho **1733 ca · 47 bộ** (§1.2); thêm đúng
tệp của tôi (**21 ca**) thì lượt chung cho **1754 ca · 48 bộ**. Không ca nào biến mất, không bộ nào
bị nuốt.

**Và đây là con số định lượng cho `N-G19-03`:** chỉ cần **hai tệp mà đề bài CHO PHÉP tôi tạo** xuất
hiện, hồi quy chung đi từ **1 bộ đỏ / 1 ca đỏ** (§1.2) lên **2 bộ đỏ / 4 ca đỏ** — trong đó **3 ca
đỏ hoàn toàn không liên quan tới sản phẩm**:

| Ca đỏ (khi cây có hai tệp AG-01 G20) | Vì sao | Có phải lỗi sản phẩm? |
|---|---|---|
| `thu_qa_g17.py::A_Nen.test_a1_cay_sach_va_head` | Cổng cây sạch miễn trừ **tên cứng** | **KHÔNG** — `N-G19-03` |
| `thu_qa_g18.py::A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` | y như trên | **KHÔNG** — `N-G19-03` |
| `thu_qa_g18.py::Z_TongKet.test_z2_cay_khong_doi_trong_luot_do` | Cổng vân tay cây của g18, cùng gốc | **KHÔNG** — `N-G19-03` |
| `thu_qa_g18.py::B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong` | Tầng 3, ca 04 bàn phím trong màn | **CÓ** — khoản nợ G20 (`N-G20-02`) |

**Bộ kiểm của tôi KHÔNG che chuyện này:** `H1` in ra **từng** bộ đỏ kèm **nhóm có tên**, và một bộ
đỏ không rơi được vào nhóm nào sẽ làm `H1` **ĐỎ** với nhãn *"HỎNG SẢN PHẨM"*.

> **Vì sao `H1` KHÔNG đòi `bộ hỏng == []`.** Trên nền này hai khoản nợ **CÓ THẬT** (N-G19-03 và
> N-G18-01) làm hồi quy đỏ, và **đó là kết quả ĐÚNG**. Việc của `H1` không phải là "không có bộ
> đỏ" — mà là **"không có bộ đỏ nào VÔ DANH"**. Bộ nào không rơi được vào nhóm có tên ⇒ **HỎNG SẢN
> PHẨM** và `H1` **ĐỎ**. Hai khoản nợ kia có **cổng riêng** (`G1`, `B1`) và chúng **ĐỎ** ở chế độ
> `gop`; ở `H1` chúng chỉ được **PHÂN LOẠI**, không được tha.

### 3.4 Đo "cổng có răng" bằng máy — chế độ `gop`

```sh
VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
# → Ran 21 tests in 36.447s · FAILED (failures=5, skipped=2) · EXIT=1
```

**Đúng năm cổng ĐỎ**, mỗi cổng kèm lý do nêu tên:

```
FAIL: test_g1_…  CỔNG C1 ĐỎ: chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN
FAIL: test_b1_…  CỔNG C2 ĐỎ: tầng 3 bàn phím (3, 1, 3) — chế độ GỘP: khoản nợ (3, 1, 3) VẪN CÒN NGUYÊN
FAIL: test_c1_…  CỔNG C3 ĐỎ: chế độ GỘP: khoản nợ 128 VẪN CÒN NGUYÊN
FAIL: test_c4_…  CỔNG C4 ĐỎ: chế độ GỘP: khoản nợ (True, False) VẪN CÒN NGUYÊN
FAIL: test_c5_…  CỔNG C5 ĐỎ: chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN
```

Và làn **MẶC ĐỊNH** trên cùng cây đó **XANH** (`Ran 21 tests · OK (skipped=2) · EXIT=0`) — nên bộ
kiểm **không** phải một cổng hỏng sẵn, và **không** phải một cổng luôn xanh.

---

## 4. PHÁT HIỆN

### 4.1 `N-G20-02` — **CAO**: bộ đỏ duy nhất **KHÔNG PHẢI** cổng cây sạch, mà là **lỗ hổng sản phẩm TẤT ĐỊNH**

**Đề bài nêu:** *"AG-00 đo trên cùng commit này có MỘT bộ đỏ: `thu_qa_g18.py` (chốt 'cây sạch' của nó)."*

**Đo độc lập của tôi nói khác — và tôi giữ nguyên con số của mình, không hoà giải:**

| Câu hỏi | Cách đo | Kết quả |
|---|---|---|
| Cổng "cây sạch" của g18 có đỏ trên **cây SẠCH** không? | `python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` | **KHÔNG** — `Ran 1 test in 0.043s · OK · EXIT=0` |
| Vậy ca nào đỏ? | `python3 app/thu/thu_qa_g18.py B_Tang3.test_b1_tang_3_chay_duoc_va_khong_co_ca_hong` | `FAILED (failures=1) · EXIT=1` |
| Đỏ vì cái gì? | đọc `tang3_ban_phim.log` | `06_ban_phim.spec.js:153 › 04 — Tab vào được các điều khiển TRONG màn`: **30 lượt Tab chỉ vào được 1 điều khiển trong màn** (đặc tả đòi `> 10`) |
| Có chập chờn không? | chạy lại **2/2** lượt | **KHÔNG** — cùng một ca, cùng con số |

**Cách hiểu đúng — và nó KHÔNG bênh ai:** lý do AG-00 nêu **tái hiện được**, nhưng chỉ khi **cây
BẨN** (chính tệp của AG-00 chưa commit). Trên **cây sạch của nền đóng băng** — thứ mà đề bài yêu
cầu tôi đo — cổng đó **XANH**, và bộ đỏ duy nhất là một **khoản nợ sản phẩm khác hẳn**.

**Đây có phải lỗi sản phẩm không? — CÓ, và là loại tệ nhất: không ai báo.** Ba dấu hiệu:

1. **Đặc tả do chính dự án viết và nó tự nói mình sai.** `thu_giao_dien/06_ban_phim.spec.js` là tệp
   **MỚI của G19** — thêm bởi commit `13dd5d1 "AG-06 (G19) V-13911 ban phim…"`. Ở nền trước
   (`6e61fc1`, `integration/g18`) tệp **không tồn tại** (`0` test). Nên đây **không** phải nợ cũ.
2. **Nó là tiêu chí nghiệm thu số 5 của G19** (*"ca bàn phím **đi hết được** các màn quản trị"*),
   và `QA_G19.md` §5 mục 2 đã tự khai phần này **CHƯA ĐO**. Hoá ra **có** một ca cho nó — và ca đó
   **đang ĐỎ** trên chính commit đã gộp.
3. **Nó không lộ ra ở đâu cả.** Tầng 3 **không** chạy ở mục riêng của `chay_tat_ca.sh`; nó chỉ chạy
   **bên trong** `thu_qa_g18.py`, và ở đó nó hiện ra dưới dạng **một bộ đỏ tên `thu_qa_g18.py`** —
   người đọc tưởng đó là chuyện của bộ G18, không phải của giao diện.

### 4.2 `N-G20-03` — **TRUNG BÌNH**: một ca hỏng làm **3 ca khác KHÔNG HỀ CHẠY**, và không dòng nào nói ra

Kết quả thật của tầng 3 là **`1 failed · 3 did not run · 47 passed`**. Ba ca **không hề chạy**:

| Ca bị bỏ | Nội dung | Vì sao đáng lo |
|---|---|---|
| **05** | Đăng xuất bấm được bằng bàn phím | Không đo được |
| **06** | **TỰ KIỂM**: gỡ `ban_phim.js` ⇒ menu mất thứ tự Tab | **Chính là ca chứng minh bản vá có răng** — không chạy nghĩa là **không có gì chứng minh bàn phím đang được canh** |
| **07** | Bố cục hẹp: Tab không vào chỗ khuất | Không đo được |

Nguyên nhân **đo được**: khi một ca Playwright **quá hạn**, Playwright đóng tiến trình con và **các
ca còn lại trong cùng tệp không chạy**. Vì `playwright.config.js` đặt `workers: 1`, toàn bộ phần
đuôi của tệp bị mất.

**Và bộ đếm hiện có KHÔNG thấy điều đó.** `thu_qa_g18.py::_dem_playwright()` **có** trả về số
`did not run` — nhưng `test_b1` chỉ khẳng định `ma == 0`, `hong == 0`, `dat > 0`; **`bo`/`không
chạy` không vào điều kiện nào**. Hôm nay điều đó chưa gây hậu quả (vì có ca hỏng nên mã thoát đã
khác 0), nhưng **nó là một nhiệt kế thiếu vạch**. Bộ kiểm của tôi đặt `did not run` **ngay trong
giá trị của cổng C2** — `(3, 1, 3)` — nên không thể che được.

### 4.3 `N-G20-01` — **TRUNG BÌNH**: không bộ thử G19-tổng-hợp nào chạy; tệp được chỉ sang **không tồn tại**

Xem §2.5. Bổ sung một chi tiết đáng ghi: **bộ chạy chung in `⊘ thu_qa_g19.py BỎ QUA không nêu cách
bật`** — nó cố đọc dòng `Bật bằng: <BIẾN>=<giá trị>` trong output, nhưng `thu_qa_g19.py` chỉ in
`skipped '<lý do dài>'`, **không** nêu tên biến. Nên người đọc báo cáo thấy *"1 bộ BỎ QUA"* mà
**không có cách nào biết bật bằng gì**. Tên biến thật (`VIP_G19_HEAD=6e61fc1…`) nằm **trong** chuỗi
lý do, chỉ đúng khi nền là `6e61fc1` — tức **vô dụng trên cây đã gộp**.

### 4.4 **HAI LỖI CỦA CHÍNH BÀN ĐO TÔI** — ghi lại vì chúng dạy đúng một điều

| Lỗi | Triệu chứng | Nguyên nhân thật | Đã sửa |
|---|---|---|---|
| **Đệ quy VÔ HẠN** | `VIP_G20_DAY_DU=1` chạy mãi; `hoi_quy.log` không bao giờ ra; log tầng 3 của tôi bị ghi lại **mỗi ~7 phút** (08:18 · 08:25 · 08:32) | `H1` **có** lọc `VIP_G20_DAY_DU` ra khỏi một dict rồi truyền `env=` — nhưng `_chay()` **`update()` đè lên `os.environ`**, nên biến **sống sót** sang con; con chạy `chay_tat_ca.sh`, bộ chạy chung chạy lại chính tệp tôi ở làn đầy đủ ⇒ **vòng lặp** | `_chay(..., bo_bien=…)` **gỡ hẳn** khoá; **`T5`** canh đúng chỗ đó; tiến trình mồ côi đã được dọn (xem dưới) |
| **Đối chứng dương quá chặt** | `G1` đỏ với `AssertionError: g17 KHÔNG thấy hai tệp AG-01 G20…: ['?? app/thu/thu_qa_g20.py']`, rồi `Z1` báo thiếu dương cho `cong-cay-sach` | `G1` đòi thấy **CẢ HAI** tệp AG-01 G20, nhưng lúc đó `docs/QA_G20.md` **chưa được viết** | chỉ đòi thấy những tệp **đang tồn tại** |

**Dọn dẹp sau sự cố đệ quy — theo ĐÚNG PID, không theo mẫu tên (§16.7):** sau khi huỷ job,
`pgrep -fl "app/server.py"` còn **đúng một** tiến trình mồ côi
(`53056 … Python app/server.py 8897`); tôi `kill -TERM 53056` và xác nhận lại danh sách **RỖNG**.
Máy chủ đó bind `127.0.0.1` nên **không mở cổng ra ngoài** — nhưng để mồ côi là sai, và nó được ghi
lại đây chứ không giấu.

> **Bài học, và nó là bài học của chính dự án (`BAN_GIAO.md` §7.2 "Vá mò trước khi đo đúng chỗ"):**
> tôi **đã viết** đúng ý định ("gỡ cờ để không đệ quy") nhưng **cơ chế gỡ không có tác dụng**, và
> **không có ca nào canh cơ chế đó**. Một dòng `self.assertIn("CO=False", …)` chạy trong tiến trình
> con — tức `T5` — là thứ duy nhất phát hiện được. Đây đúng là lý do chốt (a) bắt buộc.

---

## 5. CHƯA ĐO — **LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT**

| # | Mục | Vì sao chưa đo | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Gọi API hãng thật, kể cả sandbox** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM**. Mọi phép đo HTTP của tôi chỉ chạm `127.0.0.1` (cổng do OS cấp); `Z3` tự soi chính bộ kiểm | anh Thành cấp quyền |
| 2 | **Điều khiển TỪNG MÀN bằng bàn phím trên BẢN ĐÃ GỘP** | Nền **đang ĐỎ** (C2); "đóng" chỉ đo được ở **lượt 2** | làn sửa giao diện + lượt 2 của tôi |
| 3 | **Menu NỀN TẢNG (`MAN_PLATFORM`), bẫy tiêu điểm trong hộp thoại, bảng bên trong màn** | Ca 04 chỉ đo màn **Đơn hàng** (`don`) với **30** lượt Tab; các màn khác **CHƯA ĐO** | lượt 2 (mở rộng ca) |
| 4 | **3 ca tầng 3 không hề chạy** (05 Đăng xuất · 06 TỰ KIỂM gỡ `ban_phim.js` · 07 bố cục hẹp) | Bị ca 04 chặn (`N-G20-03`). **Chúng KHÔNG được tính là đạt** | đóng C2 ⇒ chúng tự chạy |
| 5 | **Toàn bộ 7 đặc tả tầng 3 trong MỘT lượt** | Làn mặc định của tôi chỉ chạy `06_ban_phim.spec.js` — **cả làn mặc định hết 36 giây**; chạy trọn bộ là ~2 phút. `thu_qa_g18.py` **có** chạy trọn (51 ca), nhưng đó là **bộ của wave trước** và nó không phân loại "did not run" | lượt 2, hoặc `thu_giao_dien/chay.sh` khi có nhị phân trong repo |
| 6 | **`P-3`/`P-4`** (hai câu tài liệu sai về hệ thống) | Là mục **tài liệu**, không phải mã; bộ kiểm của tôi **không có phép đo cho văn xuôi** | AG-00 |
| 7 | **21 mã trạng thái VTP** | Lượt này tôi **không** đo. Ghi nhận **dấu hiệu lạ**: `BANG["vtp"]` có **19** khoá, kiểu khoá **hỗn hợp `int` + `str`** — `N-G19-01` (mã hãng gửi dạng **số** trượt khoá **chuỗi**) **chưa được xác nhận là đã đóng** | làn AG-04/G19 + lượt 2 |
| 8 | **Hành vi ĐA TIẾN TRÌNH dưới tải lớn** (ngoài trần tần suất) | Bộ riêng `app/thu/dong_thoi/chay.py`; lượt này tôi không chạy lại (G18 đã đo 8 tiến trình × 400 phép) | giữ nguyên phạm vi G18 |
| 9 | **PostgreSQL production (D-8)** | **BỊ CẤM chuyển** — CSDL nghiệp vụ vẫn SQLite (`A3`: **0/33** tệp `app/*.py` import driver PostgreSQL). Cụm `:5432` **CHẶN CỨNG** (`A4` chỉ **đọc** `lsof`) | quyết định của anh Thành |
| 10 | **Deploy / push / tunnel / VPS / TLS thật** | **BỊ CẤM** | — |
| 11 | **Safari · Firefox · trình đọc màn hình · cảm ứng thật · in PDF thật · dữ liệu lớn · credentials thật** | Ngoài phạm vi theo thiết kế (`thu_giao_dien/chay.sh` tự khai) | — |
| 12 | **Chốt `D-9` (`city`/`area`)** | Lượt này **không** đo ánh xạ `area` ngoài mock — **giữ nguyên chốt cứng** | làn có quyền sửa ánh xạ |
| 13 | **Nghiệm thu bản ĐÃ GỘP của G20** | **Đây là lượt 1**: nền còn đóng băng, **năm khoản nợ còn nguyên**. Bộ kiểm đã sẵn sàng | **Dispatch mới** (đã báo trước) |

**Ngoài phạm vi đã đo — nói thẳng:** tôi **không** sửa `app/truy_van.py`, `app/server.py`,
`admin/*.js`, `thu_giao_dien/*.spec.js`, `thu_qa_g17.py` hay `thu_qa_g18.py`. `C4`/`C5`/`G1` là
**phép đo**, không phải yêu cầu sửa — quyết định có nằm trong phạm vi làn nào thuộc **AG-00**. Bộ
kiểm của tôi **không** thay thế nghiệm thu của các làn G20 trên làn của họ; nó là **cổng đối chiếu
độc lập** trên **bản đã gộp**.

---

## 6. TUÂN THỦ TUYỆT ĐỐI — tự kiểm **bằng máy**, không bằng lời

| # | Điều bị cấm | Cách tôi tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng **kể cả sandbox** | `Z3`: quét chính tệp bộ kiểm, **0** URL ngoài `127.0.0.1`. Mọi HTTP là máy chủ **của tôi** trên nền tạm | ✓ |
| 2 | Push / deploy / tunnel / **mở cổng ra ngoài** | Không một lệnh `git push`/`ssh`/tunnel nào. Máy chủ tầng 3: `do_tang_3()` **ÉP `VIP_HUB_BIND=127.0.0.1`** (không chỉ trông cậy giá trị mặc định — một biến thừa hưởng có thể mở cổng ra ngoài), cổng do OS cấp (`bind 127.0.0.1:0`); **`Z3` khẳng định chính dòng mã đó có mặt** | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; sửa `app/cau_hinh.py` | `A2`: **0** adapter `CHO_PHEP_LIVE=True`, và chốt an toàn **BẮT** được adapter giả MỞ LIVE ⇒ có răng; `Z2` vân tay cây **không đổi** | ✓ |
| 4 | Credentials thật · `.env` · in bí mật | Không đọc `.env`; CSDL và log nằm trong thư mục tạm; log tầng 3 chỉ chứa kết quả ca | ✓ |
| 5 | **Không đoán mã trạng thái chưa hãng xác minh** (D-4) | Lượt này tôi **không** chạm bảng ánh xạ trạng thái; `C4` chỉ **đếm** tệp import, **không** gán trạng thái nào | ✓ |
| 6 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area`; xem §5 mục 12 | ✓ |
| 7 | **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8) | `A3`: **0/33** tệp `app/*.py` import `psycopg`/`psycopg2`/`asyncpg`/`pg8000`; `A4` chỉ **đọc** `lsof` trên `:5432`, **không** kết nối; bộ thử PostgreSQL của dự án dùng cụm riêng `55432` | ✓ |
| 8 | Không dùng Claude/mô hình khác · không tự bấm duyệt sandbox | Không một lời gọi mô hình nào; không thao tác duyệt nào | ✓ |
| 9 | Không xoá hàng loạt · không sửa ngoài phạm vi | `git diff --stat` và `git diff --cached --stat` **RỖNG**; `git status --porcelain` **đúng hai** tệp AG-01 G20; `Z2` vân tay cây **TRƯỚC = SAU** | ✓ |

---

## 7. KẾ HOẠCH LƯỢT 2 — NGHIỆM THU BẢN ĐÃ GỘP G20

1. `git merge-base --is-ancestor 148ecd3 HEAD` + chụp **vân tay TRƯỚC mọi lượt chạy** (đã làm đúng
   ở lượt này — §1.0).
2. `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` — **năm cổng phải chuyển từ ĐỎ sang XANH**:
   - **C1** `2/2` cổng cây sạch XANH (miễn trừ **theo quy tắc**, không theo tên cứng);
   - **C2** tầng 3 `(7, 0, 0)` — ca 04 vào được **> 10** điều khiển trong màn, và **5/6/7 phải CHẠY**;
   - **C3** `git` môi trường nguyên bản thoát **0**;
   - **C4** `(True, True)` — `truy_van.py` có **đường vào sản xuất**;
   - **C5** có **≥ 1** bộ G19-tổng-hợp chạy thật.
3. `VIP_G20_DAY_DU=1 python3 app/thu/thu_qa_g20.py` — hồi quy toàn phần: **`H1` phải phân loại được
   MỌI bộ đỏ**, số ca **> 1733**, số bộ **≥ 47**.
4. `python3 app/thu/thu_qa_g20.py` (làn mặc định) — **phải XANH**; nếu không, chính bộ kiểm hỏng.
5. **Đối chiếu chéo** với báo cáo của các làn G20: mỗi con số của họ phải có một con số của tôi khớp
   hoặc một lý do lệch được nêu.
6. Cập nhật **§5 CHƯA ĐO** — mục nào đóng được thì đóng, mục nào còn thì **vẫn nói thẳng**.
7. **Nếu một khoản nợ chưa gộp: cổng tương ứng ĐỎ, và tôi KHÔNG hạ cổng xuống cho vừa.** Ở chế độ
   `gop`, giá trị `NEN` **cũng** ĐỎ — nên không có đường lùi nào bằng câu "nền còn đóng băng".
