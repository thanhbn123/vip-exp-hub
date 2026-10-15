# NGHIỆM THU G19 — AG-01 (QA/VERIFIER) · LƯỢT 1: KẾ HOẠCH + BASELINE ĐỘC LẬP

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_20ac493ef369` · **Dispatch:** `ctx_9eb39225a1e9`
**Nền đo:** `integration/g18 @ 6e61fc1e1f1f9a6d64931464e4f40ed887192ab5` (`6e61fc1`) — **NỀN ĐÓNG BĂNG**,
worktree riêng `g19-ag01-qa`. **KHÔNG** dùng `main` (`de740dc`, không chứa G13–G19).
**Hai tệp AG-01 G19 được phép tạo (và là hai tệp DUY NHẤT đã tạo):**
`app/thu/thu_qa_g19.py` (**26 ca**) · `docs/QA_G19.md` (tài liệu này).

**Lệnh chạy bộ kiểm của tôi:**

```sh
python3 app/thu/thu_qa_g19.py                     # làn MẶC ĐỊNH — 26 ca · 0 hỏng · 4 bỏ qua · exit 0
VIP_G19_DAY_DU=1 python3 app/thu/thu_qa_g19.py    # + hồi quy toàn phần + tầng 3 Chromium thật
```

**Tôi là NGƯỜI KIỂM, không phải người viết.** Lượt này tôi **không sửa một dòng mã sản phẩm nào**:
tìm thấy lỗi thì ghi lại và báo cáo (§4). Việc của lượt này là **kế hoạch nghiệm thu có CỔNG FAIL rõ
ràng** + **baseline độc lập** + **bộ kiểm đã dựng sẵn cho lượt gộp**.

**Luật bằng chứng tự áp:** mọi khẳng định dưới đây đi kèm **lệnh thật + mã thoát thật + số ca thật +
số bỏ qua**. Mã thoát lấy **ngay sau lệnh**, không qua ống. **Hai chốt chặn bắt buộc** (§3): (a) ca
TỰ KIỂM BỘ ĐO chạy trong **tiến trình con**; (b) **ĐỐI CHỨNG DƯƠNG** cho **mọi** ca phủ định, có sổ
`DOI_CHUNG` và `Z1` tự phán HỎNG nếu thiếu. Cái gì không đo được thì nằm ở **§5 CHƯA ĐO** — đó là
**lỗ hổng phạm vi, KHÔNG phải ĐẠT**.

**Một quyết định thiết kế phải nói ngay, không giấu:** mỗi cổng trong bộ kiểm phục vụ **HAI chiều
kỳ vọng** trên **CÙNG MỘT phép đo** — *nợ MỞ* (cây nền đóng băng, phải ra **đúng con số nợ** đã đo
ở §2) và *nợ ĐÓNG* (cây đã gộp G19, phải ra con số của trạng thái đã vá). Nhờ vậy **"cổng có răng"
không phải một lời hứa**: cùng một phép đo cho **ĐỎ** ở lượt nền và **phải** cho **XANH** ở lượt gộp.
Chế độ được in ra ở dòng đầu và **tự suy từ một dấu hiệu đo được** (`csdl.PHIEN_BAN_SCHEMA >= 9`),
ép được bằng `VIP_G19_CHO_GOP=0|1`; `J6` chứng minh bộ chọn chế độ **có răng**.

---

## 0. BẢNG PHÁN QUYẾT — BẢY ACCEPTANCE CỦA G19, KÈM **CỔNG FAIL**

Cột **CỔNG FAIL** là điều kiện làm mục đó **ĐỎ** — đọc cột đó trước cột phán quyết. Cột **NỀN
`6e61fc1`** là con số **tôi đo được hôm nay**, không chép của ai.

| # | Acceptance G19 (`G16_G25_LOCAL_PLAN.md` §9) | CỔNG FAIL (điều kiện ĐỎ) | Cách đo (bộ kiểm của tôi) | NỀN `6e61fc1` |
|---|---|---|---|---|
| 1 | **AG-02** trần tần suất giữ nguyên qua N=1·2·4·8 tiến trình **thật** | tổng lượt được phép **≠ trần khai** ở **bất kỳ** N nào · **hoặc** trần khai đọc không ra | `B1` (đo 4 mức N) + `J3` (đột biến sửa trần) | **NỢ MỞ** — `{1:20, 2:40, 4:80, 8:160}` = **20·N** |
| 2 | **AG-03** bộ đếm **sống qua khởi động lại**; vượt trần sau restart ⇒ bị chặn | tổng qua 2 lượt khởi động lại **≠ trần khai** | `C1` | **NỢ MỞ** — **40** lượt qua 2 lượt khởi động lại |
| 3 | **AG-04** 21 mã VTP có **bảng ánh xạ + ca**; mã chưa xác minh vẫn `NEEDS_REVIEW` | **< 21** mã hãng được nhận ra · **hoặc** nguồn vẫn khai *"mô phỏng của chính dự án"* · **hoặc** mã cố ý-`None`/nhập nhằng rơi vào trạng thái **HOÀN TẤT** · **hoặc** mã lạ bị gán trạng thái | `D1` + `D2` + `D3` + `J4` | **NỢ MỞ** — **0/21** mã thật; nguồn = *"bộ mô phỏng của chính dự án"* |
| 4 | **AG-05** mỗi màn **có đường vào thật** (bấm được, có ca E2E) **hoặc bị bỏ kèm lý do** | còn module đợt 3 **0 lần được `admin.js` tham chiếu** · **hoặc** tầng 3 còn màn *chưa cắm* | `E1` (tĩnh) + `I1` (Chromium thật) | **NỢ MỞ** — **4/5** module **CHẾT**; tầng 3: **15/17** màn chưa cắm |
| 5 | **AG-06** ca bàn phím **đi hết được** các màn quản trị | mục điều hướng **không Tab tới được** còn **> 0** · **hoặc** Tab không rời `body` · **hoặc** nút Đăng xuất không Tab tới được | `F1` (tĩnh) + `I2` (Chromium thật, 40 lượt Tab) | **NỢ MỞ** — **12** mục không Tab tới được; Chromium: **0/11** mục menu, Tab **không bao giờ** rời `body` (40/40) |
| 6 | **AG-00** `truy_van.py` có **route thật** + E2E qua HTTP; `P-3`/`P-4` sửa | `PHIEN_BAN_SCHEMA < 9` · **hoặc** không có `nang_len_v9` · **hoặc** `server.py` **0** tham chiếu module `truy_van` | `G1` + `J6` | **NỢ MỞ** — schema **v8** · `nang_len_v9`=**False** · **0** tham chiếu |
| 7 | **AG-01** đối chiếu chéo + regression riêng + mục CHƯA ĐO nói thẳng | nền **sai HEAD** · **hoặc** cây đổi ngoài 2 tệp AG-01 · **hoặc** thiếu chốt (a)/(b) ở §3 | `A1`/`A2`/`Z2` + `J1`–`J6` + `Z1` | **ĐẠT** cho lượt 1 (xem §1, §3) |

**Phán quyết một dòng của lượt 1:** nền `6e61fc1` **sạch và tự chạy xanh** (exit 0 · 1631 ca · 44 bộ ·
0 hỏng · 0 bỏ qua), **cả sáu khoản nợ G19 đều còn nguyên và tôi đo được con số của từng khoản** —
nghĩa là sáu cổng ở trên **đang ĐỎ**, đúng như phải thế trước khi wave G19 gộp. Bộ kiểm đã sẵn sàng
cho lượt gộp: **hai chốt chặn bắt buộc đã chạy thật** (§3), **bốn phép đột biến** chứng minh bốn
cổng **có răng**, và làn đầy đủ chạy **xanh trọn** (`Ran 26 tests · OK · exit 0`, §3.3).
**Bốn phát hiện mới**: `N-G19-01` (**TRUNG BÌNH**, mã hãng dạng số trượt khoá chuỗi — chìa khoá cửa
cho AG-04), `N-G19-02` (**THẤP**, tài liệu ghi 16/17 màn, đo ra 15/17), `N-G19-03` (**TRUNG BÌNH**,
cổng "cây sạch" của hai wave trước làm cổng hồi quy chung ĐỎ) và `N-G18-01` **tái diễn** (ca tầng 3
của bộ G18 chập chờn: **2/3** lượt). Cộng thêm **hai lỗi của chính bàn đo tôi** ở §4.3 — trong đó
một lỗi suýt biến thành *"phép đo không có răng"*.

---

## 1. BASELINE ĐỘC LẬP TRÊN NỀN ĐÓNG BĂNG

### 1.0 Vân tay cây + HEAD + số tệp

```sh
export GIT_CONFIG_COUNT=0        # bắt buộc trên máy này — xem N-G18-00
git rev-parse HEAD
git ls-files | wc -l
git status --porcelain=v1 -uall
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

| Mốc | Giá trị |
|---|---|
| `git rev-parse HEAD` | `6e61fc1e1f1f9a6d64931464e4f40ed887192ab5` — **không đổi suốt lượt đo** |
| Số tệp được theo dõi | **265** |
| `git status --porcelain=v1` **TRƯỚC** lượt chạy nào | **RỖNG** (đo lúc bắt đầu, xem ghi chú) |
| **Vân tay lúc cây SẠCH** (`ls-files -s` + porcelain **rỗng**) | `0874a9aee8bfdd456391e35e97d65900435c9c0cd697de748d9c5107db45f9a8` |
| Vân tay **SAU** tất cả (`porcelain` có 2 dòng) | `1cc3f68828a221f018c1dbf929d00e02dd29d60c49f28e948fca8eb1662edfc1` |
| **Vân tay BỘ KIỂM** (miễn trừ đúng 2 tệp AG-01) | `c6f38c18c9e9eb1b2b9e8183f944021612ef2cd86e514068e8d00635156f3d31` — **TRƯỚC = SAU** (`Z2`) |
| `git ls-files -s` **riêng nó** (chỉ phụ thuộc HEAD + index) | `0874a9ae…` — **KHÔNG ĐỔI** |
| `git diff --stat` · `git diff --cached --stat` | **RỖNG** cả hai — **không một tệp ĐÃ THEO DÕI nào bị sửa** |
| `git status --porcelain=v1 -uall` **SAU** tất cả | **ĐÚNG 2 dòng**: `?? app/thu/thu_qa_g19.py` · `?? docs/QA_G19.md` — **đúng hai tệp đề bài cho phép** |

**Vì sao hai vân tay thô khác nhau (`0874a9ae…` vs `1cc3f688…`) mà vẫn là "cây không đổi":** phép
băm gộp **cả** chuỗi `git status --porcelain`; lúc cây sạch chuỗi đó **rỗng**, sau khi tôi tạo hai
tệp được phép thì nó có **đúng hai dòng**. Phép băm **miễn trừ hai tệp AG-01** (`c6f38c18…`) là
phép băm dùng để phán "cây có đổi không", và nó **TRƯỚC = SAU**. Bằng chứng mạnh hơn cả ba con số:
`git diff --stat` và `git diff --cached --stat` đều **RỖNG** — tức **0 byte** mã sản phẩm bị đụng,
kể cả khi tôi đã chạy **ba lượt làn-đầy-đủ** (mỗi lượt gồm một lượt `chay_tat_ca.sh` 45 bộ + một
lượt Chromium), **bốn phép đột biến trên cây sao chép**, và nhiều lượt dựng cụm PostgreSQL riêng.

> **GHI CHÚ PHƯƠNG PHÁP — một thiếu sót của chính lượt đo, ghi ra thay vì che.** TRƯỚC lượt chạy
> baseline tôi **có** đo `HEAD` và `git status --porcelain` (ra RỖNG), nhưng **không** chạy lệnh
> băm để chụp **chuỗi vân tay lúc cây sạch** tại thời điểm đó — giá trị `0874a9ae…` ở bảng trên là
> **tính lại sau**, từ `git ls-files -s` (chỉ phụ thuộc `HEAD`, bất biến) cộng **chuỗi porcelain
> rỗng** đã đo được lúc đầu. Suy ra được, nhưng **không phải một phép đo trực tiếp tại chỗ**. Lượt
> sau tôi sẽ chụp vân tay **trước khi** chạy bất cứ thứ gì. Cái **đo trực tiếp** thì không thiếu:
> `git diff --stat` / `--cached --stat` rỗng, và phép băm **miễn trừ 2 tệp AG-01** của bộ kiểm
> **TRƯỚC = SAU** trong cùng một lượt (`Z2`).

### 1.1 Lượt chạy độc lập của bộ chạy chung — **trên cây SẠCH (chưa có tệp AG-01)**

```sh
sh app/thu/chay_tat_ca.sh          # log thô: /tmp/g19-ag01-qa/baseline_chay_tat_ca.log
```

| Chỉ tiêu | **Số TÔI đo** | AG-00 công bố | Khớp? |
|---|---|---|---|
| **Mã thoát** | **0** | 0 | ✓ |
| Số **ca** python | **1631** | 1631 | ✓ |
| Số **bộ** chạy thật | **44** | 44 | ✓ |
| Số **bộ hỏng** | **0** | 0 | ✓ |
| Số bộ **BỎ QUA** (0 ca) | **0** | — | — |
| Frontend tầng 1 + 2 | **56 + 36** ca | — | — |
| E2E qua HTTP thật | **41/41** phép đo | — | — |
| Môi trường | `Darwin arm64` · python 3.9.6 · SQLite 3.51.0 | — | — |

**Con số của tôi TRÙNG con số AG-00 — nhưng tôi đo ra chúng, không chép.** Đây là **lượt chạy trên
cây sạch**, tức **trước khi** `app/thu/thu_qa_g19.py` tồn tại; đó là con số **đối chiếu được với
AG-00**. Sau khi tệp AG-01 G19 ra đời, **cùng lệnh đó** sẽ tự dò thêm nó (bộ chạy TỰ DÒ `thu_*.py`),
nên lượt sau phải là **1631 + 26 = 1657 ca · 45 bộ** — đo được ở `H1`, §3.3.

**Chi tiết không được bỏ qua:** dòng đầu log là

```
[cảnh báo] GIT_CONFIG_COUNT=2 nhưng thiếu GIT_CONFIG_KEY_* — gỡ gia đình GIT_CONFIG_* dị dạng
```

Tức **`N-G17-00`/`N-G18-00` VẪN CÒN** trên máy này: `GIT_CONFIG_COUNT=2` với `GIT_CONFIG_KEY_0`
rỗng làm **mọi** lệnh git thoát **128** (`error: missing config key GIT_CONFIG_KEY_0` / `fatal:
unable to parse command-line config`). Lượt này **không** còn làm cổng hồi quy ĐỎ, vì
`chay_tat_ca.sh` nay **TỰ CHUẨN HOÁ** (gỡ gia đình biến dị dạng trước khi chạy). Đây là **vá đúng
chỗ** — nhưng nó là **vá trong bộ chạy**, không phải vá môi trường: bất kỳ ai gọi `git` trực tiếp
mà quên gỡ biến vẫn nhận 128.

### 1.2 Lượt chạy bộ kiểm AG-01 G19 — làn MẶC ĐỊNH

```sh
python3 app/thu/thu_qa_g19.py
# → Ran 26 tests in 1.394s · OK (skipped=4) · EXIT=0
```

| Lượt | Số ca | Đạt | Hỏng | **Bỏ qua** | Nguồn của ca bỏ qua |
|---|---|---|---|---|---|
| làn **MẶC ĐỊNH** (dùng để ký §2) | 26 | 22 | **0** | **4** | `H1`, `H2`, `I1`, `I2` — làn nặng, bật bằng `VIP_G19_DAY_DU=1` |
| làn **ĐẦY ĐỦ** (`VIP_G19_DAY_DU=1`) | 26 | xem §3.3 | xem §3.3 | xem §3.3 | — |

**HAI lượt đỏ của chính bàn đo tôi được ghi lại, không giấu** (chúng là lý do tôi tìm ra
`N-G19-01`): lượt 1 `Ran 23 tests … FAILED (failures=2)` — `J4` và `J5` đỏ vì **hai phép đột biến
của tôi chưa đúng**, không phải vì sản phẩm. Xem §4.3. Bộ kiểm nay có **26 ca** (thêm `H2` đối
chứng phân loại và `I2` bàn phím Chromium sau khi lượt 1 lộ ra hai lỗ hổng đo).

---

## 2. SÁU CỔNG — ĐO THẬT TRÊN NỀN `6e61fc1` (CẢ SÁU ĐANG **ĐỎ**)

Sáu cổng dưới đây là **điều kiện nghiệm thu lượt gộp**. Hôm nay chúng **ĐỎ** — và **đó là kết quả
đúng**: wave G19 chưa gộp. Giá trị của lượt này là **con số nợ của từng cổng**, để lượt gộp có cái
đối chiếu.

### 2.1 CỔNG C1 (AG-02) — trần tần suất **nhân theo số bản** — **ĐỎ**

```sh
# driver THẬT: N tiến trình ĐỒNG THỜI, cùng một IP, cùng một nền CSDL tạm
python3 app/thu/thu_qa_g19.py B_AG02_TranTheoBan
```

| Số tiến trình **N** | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| **Tổng lượt được phép (đo)** | **20** | **40** | **80** | **160** |
| Trần khai (`auth.dang_nhap`, chiều `ip`) | 20 | 20 | 20 | 20 |
| Trần **ĐÚNG** phải là | 20 | 20 | 20 | 20 |

⇒ Trần thực tế = **20 · N**. Con số này **khớp từng ký tự** với phép đo AG-02 ghi trong
`G16_G25_LOCAL_PLAN.md` §9** (*"trần khai 20 ⇒ qua 20·40·80·160 lượt với N=1·2·4·8"*) — **tôi đo
lại độc lập và ra đúng dãy đó**. Cổng C1 đạt khi và chỉ khi **mọi N cho đúng 20**.

### 2.2 CỔNG C2 (AG-03) — bộ đếm **mất sạch khi khởi động lại** — **ĐỎ**

| Phép đo | Số thật |
|---|---|
| Trần khai | **20** |
| Tổng lượt được phép qua **2 lượt khởi động lại** (2 tiến trình mới, tuần tự) | **40** |
| Phải là | **20** |

⇒ Đây là **cửa lách thứ hai, độc lập với số tiến trình** — đúng như `gioi_han.py` tự khai trong
phần *"GIỚI HẠN CỦA PHẦN A"*. Cổng C2 đạt khi tổng qua 2 lượt khởi động lại **= 20**.

### 2.3 CỔNG C3 (AG-04) — 21 mã trạng thái VTP — **ĐỎ**

| Phép đo | Số thật trên nền |
|---|---|
| Mã VTP **thật** được hệ thống nhận ra (dạng **chuỗi**) | **0 / 21** |
| Mã VTP thật được nhận ra (dạng **SỐ** — thứ hãng gửi) | **0 / 21** |
| Số khoá của `BANG["vtp"]` | **6** — toàn khoá chữ do chính dự án bịa (`cho_lay`, `lay_hang`, …) |
| `NGUON_BANG["vtp"]` | *"bộ mô phỏng của chính dự án (KHÔNG có tài liệu hãng)"* |
| `PHIEN_BAN_TAI_LIEU["vtp"]` | `"chua-co-tai-lieu"` |
| Mã cố ý-`None` (102/202/503/505/508/550) rơi vào trạng thái HOÀN TẤT | **0 / 6** ✓ (chưa có gì để sai) |
| Mã nhập nhằng **104** rơi vào HOÀN TẤT | **0 / 1** ✓ |
| Mã lạ hoàn toàn (`99999`) bị từ chối ở **cả** hai dạng | **CÓ** ✓ |

**Dữ kiện đối chiếu của tôi là dữ kiện CỦA HÃNG, không phải phán đoán:** 21 mã lấy từ trang
`partner2.viettelpost.vn/document/webhook`, bản chép lại đã đối chiếu nằm **cục bộ** ở
`~/code/vip-viettelpost-g12/app/providers/viettel_post/status_mapper.py`
(**sha256 `d1d84496f51afe5685596bee06dd3dc2d9d8ef2c8d80abfcf4c1877b0a81416a`**, 148 dòng).
Bộ kiểm chỉ hỏi *"hệ thống có BIẾT mã này không"*, **KHÔNG** hỏi *"mã này phải ánh xạ sang trạng
thái nào"* — việc ánh xạ là quyết định của làn AG-04. **Không một byte nào ra khỏi máy này.**

### 2.4 CỔNG C4 (AG-05) — màn khai ở đợt 3 **không có đường vào** — **ĐỎ**

| Phép đo | Cách đo | Số thật |
|---|---|---|
| Module đợt 3 **0 lần** được `admin.js` tham chiếu = **MÃ CHẾT** | `E1` — **tĩnh**, đọc nguồn | **4 / 5**: `VIPFINANCE`, `VIPBILLING`, `VIPAI`, `VIPHEALTH`. Chỉ `VIPCARRIERHEALTH` = **1** lần |
| Màn đợt 3 **chưa cắm** vào giao diện | `I1` — **Chromium THẬT**, spec `04_nhan_va_man_dot3.spec.js` | **15 / 17** (*"đợt 3 khai 17 màn; 2 đã có trên menu; 15 CHƯA cắm"*) |

Lượt tầng 3 chạy riêng (log `/tmp/g19-ag01-qa/tang3_dot3.log`): **`3 passed (4.1s)` · mã thoát 0**.
Danh sách 15 màn chưa cắm: 7 màn `finance.js` (`cod`, `dot`, `bang_ke`, `phai_thu`, `phai_tra`,
`chenh_lech`, `dieu_chinh`) · 6 màn `billing.js` (`dang-ky`, `muc-dung`, `canh-bao`, `lich-su`,
`du-thao`, `quan-tri-goi`) · `ai.js` → `ai` · `health.js` → `health`.

> **Chênh lệch với tài liệu — ghi lại, không hoà giải:** `BAN_GIAO.md` §6.1 (`V-13910`) và
> `G16_G25_LOCAL_PLAN.md` §9 ghi **16/17** màn. Đo trên nền `6e61fc1` bằng **chính bộ đo của dự án**
> ra **15/17**. Xem `N-G19-02` ở §4.2.

### 2.5 CỔNG C5 (AG-06) — giao diện quản trị **không dùng được bằng bàn phím** — **ĐỎ**

**Phép đo TĨNH (`F1`, đọc nguồn):**

| Phép đo | Số thật |
|---|---|
| Khuôn menu `<a data-man="${id}">` thiếu **cả** `href`, `tabindex`, `role` | **1 khuôn** |
| Nút Đăng xuất `<a id="nut-thoat" …>` thiếu **cả** ba thuộc tính | **1** |
| Mục menu tenant mà khuôn đó vẽ ra | **11** |
| **Tổng số mục KHÔNG Tab tới được** (tenant) | **12** (= 11 + Đăng xuất) |

**Phép đo THẬT (`I2`, Chromium + Playwright, 40 lượt Tab, ghi vết tiêu điểm từng lượt):**

```sh
VIP_G19_DAY_DU=1 python3 app/thu/thu_qa_g19.py I_Tang3.test_i2_tang3_ban_phim_tab_toi_duoc
```

| Phép đo | Số thật |
|---|---|
| Số mục menu sau khi đăng nhập `shopa-owner` | **11** |
| **Tab rời `body` ở lượt thứ** | **KHÔNG BAO GIỜ** (40/40 lượt tiêu điểm vẫn là `BODY`) |
| Mục menu **Tab tới được** | **0 / 11** |
| Nút **Đăng xuất** Tab tới được | **False** |
| Lỗi trang khi đi bằng bàn phím | **0** |

⇒ **`V-13911` được tái hiện ĐỘC LẬP, đúng nguyên văn** (*"15 lượt Tab không rời `body`"* — tôi đi
**40** lượt và vết tiêu điểm 40/40 đều là `BODY`). Đây là **cổng ĐỦ**, không phải điều kiện cần:
phép đo tĩnh `F1` nói *"phần tử không nằm trong thứ tự tiêu điểm"*, còn `I2` nói *"bàn phím đi 40
lượt vẫn không tới được cái nào"*. Cổng C5 đạt khi `I2` cho **11/11 mục menu** và **có** nút Đăng
xuất. Nút `#nut-menu` (☰) **cũng** không tới được — nhưng nó là `<button>` nên nằm ngoài phép đo
tĩnh `F1` (phép đo tĩnh chỉ soi `<a>`); `I2` phủ nó.

### 2.6 CỔNG C6 (AG-00) — route `truy_van.py` + `DDL_G12Q` vào migration **v9** — **ĐỎ**

| Phép đo (`G1`) | Số thật |
|---|---|
| `csdl.PHIEN_BAN_SCHEMA` | **8** |
| `migrate.py` có hàm `nang_len_v9` | **False** (mới tới `nang_len_v8`) |
| Tham chiếu **module** `truy_van.` trong `server.py` | **0** (`_truy_van` = 2 lần, nhưng đó là **phương thức nội bộ** phân tích chuỗi truy vấn, **không phải** `app/truy_van.py`) |
| Tuyến `/api/v2/*truy*` khai trong `server.py` | **[]** — rỗng |

`app/truy_van.py` **có tồn tại** (30.770 byte) nhưng **chưa ai gọi**: `grep -rn "import truy_van"` ra
**0**. Đây đúng là mô tả *"route `truy_van.py` + `DDL_G12Q` vào migration v9"* trong §9 — khoản nợ
**còn nguyên**.

---

## 3. HAI CHỐT CHẶN BẮT BUỘC

### 3.1 CHỐT (a) — ca TỰ KIỂM BỘ ĐO chạy trong **TIẾN TRÌNH CON**

Không có mục này thì mọi dòng `✓ … ca` của tệp tôi **không chứng minh gì**.

| Ca | Phép đo | Kết quả thật |
|---|---|---|
| `J1` | một ca **cố ý hỏng** (`assertEqual(1, 2)`) chạy bằng `subprocess` + một ca đạt | hỏng → thoát **1**, có `FAILED`, **không** có dòng `OK` → luật phán trả **HỎNG**; đạt → thoát **0** → **ĐẠT** |
| `J2` | luật phán phải **TỪ CHỐI** bốn kiểu "xanh giả" | `ok,0-ca` → HỎNG · `ok,không-dấu-vết` → HỎNG · `OK` rồi thoát 1 → HỎNG · `Ran 0 tests` + `OK` → HỎNG · `Ran 5 tests` + `OK` + thoát 0 → **ĐẠT** |
| `J3` | **đột biến M1** trên **cây sao chép**: trần `20 → 5`; driver chạy trong **tiến trình con** | cây thật → `{1:20, 2:40}` · cây đột biến → `{1:5, 2:10}` ⇒ **C1 đọc trần TỪ MÃ, CÓ RĂNG** |
| `J4` | **đột biến M2**: thêm mã `"101"` vào `VTP_MA_MOCK` | cây thật → **0** mã thật · cây đột biến → **1** ⇒ **C3 đọc BẢNG TỪ MÃ, CÓ RĂNG** |
| `J5` | **đột biến M3**: thêm `href`/`tabindex`/`role` — **vá nửa vời** rồi **vá cả hai chỗ** | cây thật → **12** · vá chỉ khuôn menu → **1** · vá cả menu + Đăng xuất → **0** ⇒ **C5 CÓ RĂNG**, và nó **tách được hai chỗ** |
| `J6` | **đột biến M4**: `PHIEN_BAN_SCHEMA 8 → 9` | cây thật → **v8** · cây đột biến → **v9** **và bộ chọn chế độ tự đổi sang "nợ ĐÓNG"** ⇒ **C6 + bộ chọn chế độ CÓ RĂNG** |

**Bốn phép đột biến đều chạy trên CÂY SAO CHÉP trong thư mục tạm** (`app/**/*.py` + `admin/admin.js`),
**không đụng cây thật** — `Z2` xác nhận vân tay cây không đổi.

### 3.2 CHỐT (b) — ĐỐI CHỨNG DƯƠNG cho **mọi** ca phủ định

Sổ `DOI_CHUNG` in ra ở `Z1`. **22 nhóm**, trong đó **19 nhóm có ca ÂM** và **cả 19 đều có ca DƯƠNG**
(`Z1` tự phán HỎNG nếu thiếu). Ví dụ cụ thể của một cặp: cổng C1 có ca **âm** *"với N tiến trình,
tổng phải bằng trần khai"* và ca **dương** *"với N=1, đúng 20 lượt được phép rồi lượt 21 bị chặn"* —
đo trên **cùng một hàm**, nên không thể có chuyện hàm đo hỏng mà cả hai cùng xanh.

Chốt (b) còn được **đo bằng máy** ở một chỗ nữa: `gioi_han` bị **đột biến trần** (`J3`) — nếu phép
đo chỉ đọc một hằng số viết cứng thì `J3` sẽ **xanh giả**, và nó đã **đỏ** ở lượt 1 (xem §4.3).

### 3.3 Làn ĐẦY ĐỦ (`VIP_G19_DAY_DU=1`) — hồi quy toàn phần + tầng 3 Chromium

```sh
VIP_G19_DAY_DU=1 python3 app/thu/thu_qa_g19.py
# → Ran 26 tests in 319.217s · OK · EXIT=0        (26 ca · 0 hỏng · 0 bỏ qua)
#   log thô: /tmp/g19-ag01-qa/qa_g19_daydu3.log
```

| Ca | Phép đo | **Số thật** |
|---|---|---|
| `H1` | `sh app/thu/chay_tat_ca.sh` NGUYÊN VĂN (nền tạm riêng) | **thoát 1** · **1657 ca** · **45 bộ** · **0 bộ bỏ qua** · frontend **56 + 36** · E2E **41/41** · **310,3 giây** |
| `H1` | bộ hỏng | **2**: `thu_qa_g17.py`, `thu_qa_g18.py` — **cả hai** rơi vào nhóm **CỔNG CÂY SẠCH CỦA WAVE TRƯỚC** (`N-G19-03`) |
| `H1` | **HỎNG SẢN PHẨM** | **KHÔNG** |
| `H2` | đối chứng dương cho cách phân loại | cả hai bộ **ĐỎ** và lời phàn nàn **nêu đích danh** `['app/thu/thu_qa_g19.py', 'docs/QA_G19.md']` |
| `I1` | tầng 3 — màn đợt 3, Chromium thật | thoát **0** · **3 đạt · 0 hỏng** · khai **17** · có-menu **2** · **chưa-cắm 15** |
| `I2` | tầng 3 — bàn phím, Chromium thật | **11** mục menu · Tab rời `body` ở lượt **`None`** (không bao giờ) · Tab tới được **0/11** · Đăng xuất **False** · lỗi trang **[]** |

**Vì sao lượt chung thoát 1 mà cổng `H1` vẫn ĐẠT — và vì sao điều đó KHÔNG phải nới cổng:** hai bộ
đỏ đều đỏ vì **tệp mà đề bài cho phép tôi tạo** (`H2` chứng minh bằng máy), và `H1` **từ chối** mọi
bộ hỏng không rơi được vào một trong ba nhóm **có tên + có bằng chứng** (`N-G19-03` cây sạch,
`N-G18-01` chập chờn-**có-chạy-lại**, còn lại = HỎNG SẢN PHẨM). Cổng "teo ca" vẫn canh: `1657 ca`
và `45 bộ` được khẳng định, và số ca kỳ vọng được **đếm từ chính tệp này** chứ không viết cứng.

Ba lượt làn-đầy-đủ đã chạy; **lượt 2 đỏ** (`thu_qa_g18.py::test_b1_tang_3…` — `N-G18-01`, §4.5),
**lượt 3 xanh trọn**. Cả ba lượt đều được ghi lại, lượt đỏ **không** bị bỏ đi.

Làn này bật `H1` (chạy `sh app/thu/chay_tat_ca.sh` — bộ chạy **tự dò** thêm chính tệp này) và
`I1`/`I2` (Chromium thật). `do_hoi_quy()` **GỠ** `VIP_G19_DAY_DU` và `VIP_G19_CHO_GOP` khỏi môi
trường con — để bộ chạy chung không **đệ quy vô hạn** khi nó tự dò ra tệp này.

---

## 4. PHÁT HIỆN

### 4.1 `N-G19-01` — **TRUNG BÌNH**: mã hãng gửi dạng **SỐ** không khớp khoá bảng dạng **CHUỖI**

`app/trang_thai_hang.py::_khoa_ma` chuẩn hoá `int()` cho **`jt`** nhưng **trả nguyên giá trị** cho
mọi hãng khác:

```python
def _khoa_ma(ma_hang, ma_trang_thai):
    if ma_hang == "jt":
        try:
            return int(ma_trang_thai), None
        ...
    return ma_trang_thai, None          # ← hãng khác: KHÔNG chuẩn hoá
```

**Đo được** (cây sao chép, bảng VTP có khoá **chuỗi** `"101"`):

```sh
python3 app/thu/thu_qa_g19.py D_AG04_MaVTP     # ca D3 đo cả hai dạng
# → biết mã ở dạng CHUỖI=0 · ở dạng SỐ (hãng gửi)=0 · kiểu khoá bảng=['str']
```

và trên cây đột biến có `"101"`: `anh_xa("vtp", "101")` → `biet_ma=True`;
`anh_xa("vtp", 101)` → **`biet_ma=False`**.

**Vì sao đáng ghi ngay bây giờ:** tài liệu hãng khai `ORDER_STATUS` là **Integer**, và bản chép lại
đã đối chiếu có hẳn hàm `normalize_provider_status` chỉ để đổi `int → str` vì lý do này. **Hôm nay
nó chưa gây hậu quả** — `BANG["vtp"]` chưa có khoá số nào, nên cả hai dạng đều ra *"không biết"* như
nhau. **Nó thành lỗi thật đúng vào lúc AG-04 mang 21 mã sang**: nếu khoá là **chuỗi** thì webhook
thật (payload **số**) sẽ **trượt sạch ánh xạ mà không có gì báo** — đúng khuôn `V-13910`
(*"không người dùng nào với tới được"*). Ca `D3` canh đúng chỗ đó; nó **không** đoán mã nào.

> **Đây là NHẬN XÉT, không phải yêu cầu sửa.** Tôi là người kiểm; quyết định có nằm trong phạm vi
> AG-04 hay không thuộc AG-00.

### 4.2 `N-G19-02` — **THẤP**: tài liệu ghi **16/17** màn chưa cắm, đo lại ra **15/17**

`BAN_GIAO.md` §6.1 (`V-13910`) và `G16_G25_LOCAL_PLAN.md` §9 ghi **16/17**. Chạy **chính bộ đo của
dự án** (`thu_giao_dien/04_nhan_va_man_dot3.spec.js`, 3 ca, `3 passed (4.1s)`, thoát **0**) trên nền
`6e61fc1` ra **15/17**:

```
[đo] đợt 3 khai 17 màn; 2 đã có trên menu; 15 CHƯA cắm vào giao diện:
```

Lệch **một màn**. Sai theo hướng **nói rộng hơn sự thật** — hướng nguy hiểm theo `§12.1 luật 3`,
nhưng ở đây lệch về phía *bi quan*, tức không che bớt nợ. Tôi **không** hoà giải hai con số: tôi ghi
con số **đo được** và để `E1`/`I1` làm cổng cho lượt gộp.

### 4.3 Hai lỗi của **chính bàn đo tôi** — ghi lại vì chúng dạy đúng một điều

| Lỗi | Triệu chứng | Nguyên nhân thật | Đã sửa |
|---|---|---|---|
| `J4` đỏ ở lượt 1 | *"đột biến thêm mã 101 mà phép đo không thấy: 0"* | driver nhận danh sách mã qua biến môi trường bằng `"[" + ",".join(...) + "]"` — **thiếu dấu nháy** ⇒ JSON ra **số**, không ra **chuỗi**; truy vấn bằng số thì trượt khoá chuỗi | dùng `json.dumps()`; **và** lỗi này **lộ ra `N-G19-01`** — xem §4.1 |
| `J5` đỏ ở lượt 1 | *"thêm href/tabindex/role mà phép đo VẪN báo 1"* | đột biến chỉ vá **khuôn menu**, quên **nút Đăng xuất** — phép đo **đúng**, kỳ vọng của tôi **sai** | đột biến nay vá **cả hai**, và có thêm bước **"vá nửa vời ⇒ phải còn đúng 1"** |

⇒ Cả hai lượt đỏ **không phải** lỗi sản phẩm, và **không** bị gọi là lỗi sản phẩm. Chúng cũng là
bằng chứng ngược: **nếu phép đo là một hằng số viết cứng thì `J4`/`J5` đã không thể đỏ.**

### 4.4 `N-G19-03` — **TRUNG BÌNH**: cổng "cây sạch" của HAI wave trước làm cổng hồi quy chung ĐỎ

`thu_qa_g17.py::test_a1_cay_sach_va_head` và
`thu_qa_g18.py::test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` **chỉ miễn trừ tệp của chính chúng**.
Nên **chính hai tệp mà đề bài cho phép AG-01 G19 tạo** làm chúng ĐỎ:

```sh
python3 app/thu/thu_qa_g17.py A_Nen.test_a1_cay_sach_va_head
# → EXIT=1 · Ran 1 test in 0.027s
#   AssertionError: Lists differ: ['?? app/thu/thu_qa_g19.py', '?? docs/QA_G19.md'] != []
python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01
# → EXIT=1 · Ran 1 test in 0.028s   (cùng một thông điệp, cùng hai tệp)
```

**Đây là `N-G18-03` tái diễn NGUYÊN XI** (`docs/QA_G18.md` §1.1 lượt C: *"cổng 'cây sạch' của wave
trước đỏ vì tệp chưa commit của làn khác"*). Hệ quả vận hành: **bất kỳ làn AG-01 nào tạo tệp mới
cũng làm `sh app/thu/chay_tat_ca.sh` ĐỎ**, và người đọc thấy *"2 bộ hỏng"* mà không có gì nói đó là
tệp **được phép tạo**. Đúng khuôn `§12.2`: cấu trúc hỏng **lần thứ hai** theo cùng một kiểu thì
**đổi cấu trúc**, đừng vá thêm một lần nữa. Đề xuất (không thuộc quyền tôi sửa): hai cổng đó nên
miễn trừ theo **quy tắc** (`?? app/thu/thu_qa_g*.py`, `?? docs/QA_G*.md`) chứ không theo **danh sách
tên tệp viết cứng**.

Bộ kiểm của tôi **không che** chuyện này: `H1` phân loại và **in ra ba nhóm riêng biệt**, và `H2`
là **đối chứng dương** bắt lời phàn nàn phải **nêu đích danh** hai tệp AG-01 G19 — nếu mai kia có
người nhét một bộ khác vào danh sách miễn trừ, `H2` sẽ **ĐỎ**.

### 4.5 `N-G18-01` **tái diễn** — ca tầng 3 của bộ G18 chập chờn trong lượt chạy chung

Trong `sh app/thu/chay_tat_ca.sh`, `thu_qa_g18.py` đỏ **HAI** ca:

```
  ✗ thu_qa_g18.py              43 ca  HỎNG (mã thoát 1)
        FAIL: test_a1_cay_sach_mien_tru_dung_hai_tep_ag01 (__main__.A_Nen)
        FAIL: test_b1_tang_3_chay_duoc_va_khong_co_ca_hong (__main__.B_Tang3)
```

Ca thứ hai **không** do tệp của tôi. Bằng chứng bằng **chạy lại**:

| Lượt | Lệnh | Kết quả |
|---|---|---|
| trong lượt chung | `sh app/thu/chay_tat_ca.sh` | **HỎNG** |
| chạy lại TRỌN BỘ, một mình | `python3 app/thu/thu_qa_g18.py` | `Ran 43 tests in 88.009s` · **`FAILED (failures=1)`** — ca hỏng **duy nhất** là cổng cây sạch; `test_b1_tang_3…` **ĐẠT** |
| chạy lại ĐÚNG CA đó | `python3 app/thu/thu_qa_g18.py B_Tang3.test_b1_tang_3…` | `Ran 1 test in 46.489s` · **`OK`** · **EXIT=0** |

⇒ Đây **đúng là `N-G18-01`** mà `docs/QA_G18.md` §2.2 đã ghi (*"tầng 3 CHẬP CHỜN — 1/5 lượt đỏ"*),
**không phải** hồi quy của G19. **Tần suất đo được của tôi: 2/3 lượt làn-đầy-đủ** (đỏ ở lượt 1 và
lượt 2, xanh ở lượt 3 — §3.3).

Bộ kiểm của tôi xử lý ca này bằng một luật **có răng**: nó chỉ tha
khi ca đó (1) có tên trong danh sách **đã ghi tên** của wave trước, **và** (2) **chạy lại một mình
thì ĐẠT**. Chạy lại mà vẫn hỏng thì nó rơi vào **HỎNG SẢN PHẨM** và cổng `H1` **ĐỎ**. Kết quả
chạy lại được in ra từng lượt (`↻ thu_qa_g18.py: {... thoát 0}`), không giấu.

### 4.6 `N-G18-00` **vẫn còn** — biến `GIT_CONFIG_*` dị dạng

Ghi lại vì nó tái diễn lần thứ ba (`N-G17-00` → `N-G18-00` → nay). **Mức độ đã giảm**: bộ chạy chung
tự gỡ biến nên cổng hồi quy không còn ĐỎ vì nó. **Nhưng gốc chưa được vá**: bất kỳ lệnh `git` nào
gọi trực tiếp vẫn thoát **128**. Bộ kiểm của tôi cũng phải tự gỡ (`_git()`).

---

## 5. CHƯA ĐO — **LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT**

| # | Mục | Vì sao chưa đo | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Gọi API hãng thật, kể cả sandbox** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM**. Mọi phép đo lớp HTTP của tôi chỉ dùng stub `127.0.0.1` **cổng 0** | anh Thành cấp quyền |
| 2 | **Điều khiển được TỪNG MÀN bằng bàn phím** (biểu mẫu, nút, bảng bên trong màn) | `I2` mới đo **khung điều hướng** (11 mục menu + Đăng xuất) và **đã đo được** — nhưng *"đi hết được các màn quản trị"* còn nghĩa **thao tác được trong từng màn**, phần đó **CHƯA ĐO**. Cũng chưa đo **menu nền tảng** (`MAN_PLATFORM`) và **bẫy tiêu điểm trong hộp thoại** | AG-06 + lượt 2 của tôi |
| 3 | **`P-3`/`P-4`** (hai câu tài liệu sai về hệ thống) | Là mục **tài liệu**, không phải mã; bộ kiểm của tôi không có phép đo cho văn xuôi | AG-00 |
| 4 | **`truy_van.py` chạy đầu-cuối qua HTTP** | Route **chưa tồn tại** trên nền (C6 ĐỎ) ⇒ chưa có gì để gọi. `G1` mới đo **dấu hiệu** (v9 + tham chiếu module + tuyến khai báo) | lượt 2, sau khi AG-00 gộp |
| 5 | **Hành vi ĐA TIẾN TRÌNH dưới tải lớn** (ngoài trần tần suất) | Bộ riêng `app/thu/dong_thoi/chay.py`; lượt này tôi không chạy lại (G18 đã đo **8 tiến trình × 400 phép**) | giữ nguyên phạm vi G18 |
| 6 | **PostgreSQL production (D-8)** | **BỊ CẤM chuyển** — CSDL nghiệp vụ vẫn SQLite (`A4`: **0/33** tệp `app/*.py` import driver PostgreSQL). Cụm `:5432` **CHẶN CỨNG**: `Z3` xác nhận nó đang nghe (**2** tiến trình, pid `58873` lúc đo) và bộ thử PostgreSQL chỉ dùng cụm riêng `55432` | quyết định của anh Thành |
| 7 | **Deploy / push / tunnel / VPS / TLS thật** | **BỊ CẤM** | — |
| 8 | **Safari · Firefox · trình đọc màn hình · dữ liệu lớn · credentials thật** | Ngoài phạm vi theo thiết kế (`thu_giao_dien/chay.sh` tự khai) | — |
| 9 | **Chốt `D-9` (`city`/`area`)** | Lượt này **không đo** ánh xạ `area` ngoài mock — giữ nguyên chốt cứng | làn có quyền sửa ánh xạ |
| 10 | **Nghiệm thu bản ĐÃ GỘP của G19** | **Đây là lượt 1**: nền còn đóng băng, sáu khoản nợ còn nguyên. Bộ kiểm đã sẵn sàng cho lượt 2 | **Dispatch mới** (đã báo trước) |

---

## 6. TUÂN THỦ TUYỆT ĐỐI — tự kiểm bằng máy, không bằng lời

| # | Điều bị cấm | Cách tôi tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | Không có lời gọi mạng nào trong bộ kiểm; mọi phép đo HTTP dùng stub `127.0.0.1` **cổng 0** hoặc **không** dùng HTTP | ✓ |
| 2 | Push / deploy / tunnel / mở cổng ra ngoài | `Z3`: chỉ đọc trạng thái cụm `:5432`; máy chủ tầng 3 bind `127.0.0.1` cổng OS cấp | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; sửa `app/cau_hinh.py` | `A2`/`A3`: **0** adapter `CHO_PHEP_LIVE=True`; chốt an toàn **BẮT** được adapter giả MỞ LIVE ⇒ bộ kiểm có răng; `cau_hinh.py` **không** bị sửa (`Z2` vân tay) | ✓ |
| 4 | Credentials thật · `.env` · in bí mật | CSDL và log nằm trong thư mục tạm; không đọc `.env`; không in credential nào | ✓ |
| 5 | **Không đoán mã trạng thái chưa hãng xác minh** | `D2`: mã cố ý-`None` và mã nhập nhằng **không** rơi vào trạng thái HOÀN TẤT; mã lạ (`99999`) bị **từ chối ở cả hai dạng**, không gán trạng thái | ✓ |
| 6 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Lượt này không chạm ánh xạ `area`; xem §5 mục 9 | ✓ |
| 7 | **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (`D-8`) | `A4`: **0/33** tệp `app/*.py` import `psycopg`/`psycopg2`/`asyncpg`/`pg8000`; kết nối nghiệp vụ = `sqlite3.Connection`; cụm `:5432` **không** bị đụng (`Z3`) | ✓ |
| 8 | Không dùng Claude / không đổi mô hình / không tự bấm duyệt sandbox | Không có lời gọi mô hình nào; không có thao tác duyệt nào | ✓ |
| 9 | Không xoá hàng loạt, không sửa ngoài phạm vi | `Z2` vân tay TRƯỚC = SAU; `git status` chỉ có **2** tệp AG-01; **0** dòng mã sản phẩm bị sửa | ✓ |

**Ngoài phạm vi đã đo — nói thẳng:** `N-G19-01` (§4.1) là **nhận xét**, không phải bản vá; tôi
**không** sửa `app/trang_thai_hang.py`. `N-G19-02` (§4.2) là **chênh lệch tài liệu**, tôi không sửa
tài liệu của làn khác. Bộ kiểm của tôi **không** thay thế nghiệm thu của AG-02…AG-06 trên làn của
họ — nó là **cổng đối chiếu độc lập** trên **bản đã gộp**.

---

## 7. KẾ HOẠCH LƯỢT 2 — NGHIỆM THU BẢN ĐÃ GỘP G19

1. `git rev-parse HEAD` + **chụp vân tay TRƯỚC** (chụp **trước** mọi lượt chạy — khắc phục §1.0).
2. `python3 app/thu/thu_qa_g19.py` — **sáu cổng phải chuyển từ `nợ MỞ` sang `nợ ĐÓNG`**:
   C1 `{N: 20}` với mọi N · C2 `20` · C3 `21/21` **cả hai dạng** (chuỗi **và** số) · C4 `0/5` module
   chết · C5 tĩnh `0` mục không Tab tới được · C6 `v9` + `nang_len_v9` + tuyến thật.
3. `VIP_G19_DAY_DU=1 python3 app/thu/thu_qa_g19.py` — hồi quy toàn phần (**1657 ca · 45 bộ** kỳ
   vọng) + tầng 3 Chromium (`I1` màn đợt 3 **`chua_cam = 0`**; `I2` **11/11** mục menu + nút Đăng
   xuất Tab tới được).
4. **Đối chiếu chéo** với báo cáo của AG-02…AG-06: mỗi con số của họ phải có một con số của tôi
   khớp hoặc một lý do lệch được nêu.
5. Cập nhật `§5 CHƯA ĐO` — mục nào đóng được thì đóng, mục nào còn thì **vẫn nói thẳng**.
6. **Nếu một khoản nợ chưa gộp:** cổng tương ứng **ĐỎ**, và tôi **không** hạ cổng xuống cho vừa.
