# NGHIỆM THU G21 — AG-01 (QA/VERIFIER) · LƯỢT 1: BASELINE ĐỘC LẬP TRÊN `a3400a8` + KẾ HOẠCH CÓ CỔNG FAIL

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_92a7a30f44a4` · **Dispatch:** `ctx_8d4ae46d707c`
**Nền đo:** `integration/g20 @ a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1`, worktree riêng `g21-ag01-qa`.
**KHÔNG** dùng `main` (`de740dc`) — `main` không chứa G13–G21.
**Hai tệp AG-01 G21 được phép tạo:** `docs/QA_G21.md` (tài liệu này) · `app/thu/thu_qa_g21.py` (bộ kiểm,
**24 ca**, `sha256 4ebf21e8804246bda315fbe9bc1721625fad0ec2130c5036f235d4e04ca40700`).
Tôi **không sửa một dòng mã sản phẩm nào**: `git diff --stat` và `git diff --cached --stat` **RỖNG** (§7).

> **Vì sao ghim SHA của bộ kiểm mà không phải của tài liệu này:** một tệp **không tự ghi được SHA của
> chính nó** (`BAN_GIAO.md` §7.3). Nên tôi ghim SHA của **bộ kiểm** — thứ sinh ra mọi con số dưới
> đây. Mọi số ở §0–§5 đều đo bằng **đúng bản `4ebf21e8…`** đó (làn `gop` `6aeefd0f…` là bản trước khi
> mở rộng `G1` 2→3; bản `4ebf21e8…` cho `0/3` thay vì `0/2` — §5.3).

**Lệnh chạy bộ kiểm của tôi:**

```sh
python3 app/thu/thu_qa_g21.py                       # làn MẶC ĐỊNH — 24 ca · 0 hỏng · 4 bỏ qua · exit 0
VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py    # NGHIỆM THU BẢN ĐÃ GỘP — 8/8 cổng ĐỎ · exit 1
VIP_G21_DAY_DU=1 python3 app/thu/thu_qa_g21.py      # + hồi quy toàn phần (chay_tat_ca.sh)
```

> **MỘT CÂU PHẢI NÓI NGAY.** Năm làn G21 **KHÔNG** phủ hết năm cổng G20 mà lượt trước đã kết luận
> ĐỎ. **C4 (route `truy_van` cho migration v9) KHÔNG CÓ CHỦ SỞ HỮU** — AG-00 xác nhận bằng văn bản
> ngày 16/10/2026. Nghĩa là: **dù cả năm làn G21 đều XANH, nghiệm thu G21 VẪN là FAILED** nếu C4
> chưa đóng. Tôi ghi thẳng điều đó ở §0, §2.8 và §8 để không ai đọc nhầm "năm làn xanh = G21 đạt".

**Luật bằng chứng tự áp:** mọi khẳng định đi kèm **lệnh thật + mã thoát thật + số ca + số bỏ qua**;
mã thoát lấy **ngay sau lệnh**, không qua ống. **Hai chốt chặn bắt buộc** ở §2.9: (a) ca TỰ KIỂM BỘ ĐO
chạy trong **tiến trình con**; (b) **ĐỐI CHỨNG DƯƠNG** cho **mọi** ca phủ định, có sổ `DOI_CHUNG` và
`Z1` tự phán HỎNG nếu thiếu. Cái gì không đo được nằm ở **§6 CHƯA ĐO** — đó là **lỗ hổng phạm vi,
KHÔNG phải ĐẠT**.

---

## 0. BẢNG PHÁN QUYẾT — TÁM CỔNG, ĐO TRÊN `a3400a8`

Cột **CỔNG FAIL** là điều kiện làm mục đó **ĐỎ** — đọc cột đó trước cột phán quyết. Cột
**`a3400a8`** là con số **tôi đo được hôm nay**, không chép của ai. Mọi con số dưới đây lấy từ
`VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py` (`Ran 24 tests in 66.357s · FAILED (failures=8,
skipped=4) · EXIT=1`, log `g21_gop_nguyen_moi_truong.txt`, `sha256 6aeefd0f…`).

| # | Làn | Khoản nợ (nguồn đo được) | **CỔNG FAIL** | Cách đo | `a3400a8` |
|---|---|---|---|---|---|
| **G1** | **AG-05** `chotcay` | `N-G19-03`/`N-G21-05`: cổng cây sạch miễn trừ theo **tên cứng** — **BA bản sao** | **< 3/3** cổng cũ XANH khi cây chỉ có tệp AG-01 G21 hợp lệ · **hoặc** giá trị `1`/`2` (nửa vời) | chạy **3** cổng cây sạch trong **tiến trình con**, phân loại ĐỎ-THẬT ≠ PHÉP-ĐO-CHẾT | **ĐỎ — 0/3** |
| **G2** | **AG-05** `chotcay` | `N-G18-00`: `GIT_CONFIG_*` dị dạng ⇒ **mọi** lệnh git thoát 128 | `git rev-parse HEAD` môi trường **nguyên bản** thoát **≠ 0** | `_git(..., tho=True)` + đối chứng đã gỡ biến | **ĐỎ — 128** |
| **G3** | **AG-06** `e2e` | `V-13911`: bàn phím **TRONG màn**; ca 04 chỉ vào **1** điều khiển (đặc tả đòi `>10`) | bộ ba `06_ban_phim.spec.js` **≠ (7, 0, 0)** | Chromium thật, nhị phân **ghim** | **ĐỎ — (3, 1, 3)** |
| **G4** | **AG-02** `backup` | `G20_BACKUP_RESTORE.md` §5 **K-1/K-2/K-5**: `khoi_phuc()` chỉ `shutil.copy2`, không kiểm tệp | **> 0** đầu vào ĐỘC HẠI được **NHẬN** (rc 0) | `python3 app/migrate.py --rollback <tệp>` × 4, có đối chứng LÀNH | **ĐỎ — 4/4 nhận** |
| **G5** | **AG-03** `bimat` | `G20_DA_HANG.md` §5 + §8 **R-2**: tầng che theo **TÊN** chỉ đúng 4 tên của J&T | **> 0** tổ hợp (tên, giá trị) **RÒ** credential NGẮN | stub ECHO 401 trên `127.0.0.1`, 5 tổ hợp | **ĐỎ — 2/5 rò** |
| **G6** | **AG-04** `gioihan` | `G20_CONTRACT_HARNESS.md` §6 `N-G20-01`: `gioi_han.xoa_het()` xoá kho đếm **DÙNG CHUNG** ⇒ chặng `G18-05` ĐỎ | `sh trien_khai/g18/chay_harness.sh` thoát **≠ 0** | chạy nguyên văn | **ĐỎ — thoát 1** |
| **G7** | **AG-04** `gioihan` | `QA_G20.md` §2.5 `C5`/`N-G20-01`: **0** bộ `thu_qa_g19*.py` chạy được ≥1 ca | **< 1** bộ G19-tổng-hợp chạy thật | đếm `Ran N tests` của từng bộ `thu_qa_g19*.py` | **ĐỎ — 0/1** |
| **G8** | **⛔ KHÔNG AI** | `QA_G20.md` §2.4 `C4` (C6 của G19 **nửa vời**) | cặp `(schema_ok, route_ok)` **≠ (True, True)** | `PHIEN_BAN_SCHEMA` + đếm tệp SẢN XUẤT import `truy_van` | **ĐỎ — (True, False)** |
| **A** | — | Cửa an toàn tuyệt đối (LIVE · D-8 · `:5432` · `127.0.0.1`) | bất kỳ mục nào ở §7 đỏ | `A1`–`A4`, `Z2`, `Z3` | **ĐẠT — 4/4** |

**Phán quyết một dòng của lượt 1:** nền `a3400a8` **không tự chạy xanh** — `sh app/thu/chay_tat_ca.sh`
cho **exit 1 · 1870 ca · 51 bộ · 2 bộ hỏng** (§1.1); **cả tám cổng G21 đều ĐỎ với con số của từng
cổng**; và **nền E2E theo `chay.sh` HỎNG SẴN 7/7 đặc tả vì MÔI TRƯỜNG** (§4.1) nên nó **không cho
tín hiệu sản phẩm nào** — năm làn sửa **không được** kết luận E2E trên lượt chạy đó.

---

## 1. BASELINE ĐỘC LẬP TRÊN NỀN `a3400a8`

### 1.0 Vân tay cây + HEAD — chụp **TRƯỚC mọi lượt chạy**

```sh
git rev-parse HEAD && git status --porcelain=v1 -uall && git ls-files -s | shasum -a 256
find . -path ./.git -prune -o -path ./node_modules -prune -o -type f -print | sort | shasum -a 256
```

| Mốc | **TRƯỚC** (07:05:36Z) | **SAU** (sau lượt hồi quy) |
|---|---|---|
| `git rev-parse HEAD` | `a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1` | **không đổi** |
| `git status --porcelain=v1 -uall` | **RỖNG** | **RỖNG** |
| Số tệp được theo dõi | **317** | **317** |
| `git ls-files -s \| shasum -a 256` | `de394bac183005da36c8e1bc409d452355f6e7a8f04a4cf5aeadb232373de627` | **KHÔNG ĐỔI** |
| Băm **cả cây làm việc** | `d76198f30ccdcff5c6a01e1ca05c82f771b83c7cfd2853ef19688e09bee40d14` | `b98ecd76e45c7fef9965176ee6c63f476397c653540bdcf4a15ce172d1995b3a` |

> **VÌ SAO HAI VÂN TAY THÔ KHÁC NHAU MÀ CÂY VẪN "KHÔNG ĐỔI" — bài học đo lường, lặp lại y hệt G20.**
> Nguyên nhân **đo được**: lượt chạy sinh ra `app/du-lieu/khoa-noi-bo.key`, `thu_giao_dien/_bao-cao/**`
> và `thu_giao_dien/_ket-qua/**`. Cả ba nằm trong `.gitignore` nên `porcelain` không thấy. **Hệ quả
> phương pháp:** bộ kiểm của tôi băm **cây ĐƯỢC THEO DÕI**; `Z2` khẳng định **TRƯỚC = SAU** và in ra
> cả hai (`de394bac183005da` = `de394bac183005da`, `không đổi=True`).

### 1.1 Lượt chạy độc lập của bộ chạy chung — con số **của riêng tôi**

```sh
sh app/thu/chay_tat_ca.sh        # log thô: $TMPDIR/veh_g21_ag01_qa_log/baseline_raw.txt
# 07:05:48Z → 07:15:40Z  (9 phút 52 giây)   sha256 f500f4e1baf037fd75df019aa5e579fbe34e097d29b0ca0ff4a297cb2ff06882
# === EXIT CODE THAT = 1
```

| Chỉ tiêu | **Số TÔI đo** |
|---|---|
| **Mã thoát** | **1** |
| Số **ca** python | **1870** |
| Số **bộ** chạy thật | **51** |
| Số bộ **BỎ QUA** (0 ca) | **1** — `thu_qa_g19.py` |
| Số bộ **HỎNG** | **2** — `thu_g20_saoluu.py` (41 ca) · `thu_qa_g18.py` (46 ca) |
| Frontend tầng 1 + 2 | **56 + 36** ca |
| E2E qua HTTP thật | **41/41** phép đo |
| Môi trường | `Darwin arm64` · python **3.9.6** · SQLite **3.51.0** |

**Hai bộ đỏ, và chúng KHÁC HẲN hai bộ đỏ của G20.** Trên `148ecd3` bàn đo G20 đo được
**1733 ca · 47 bộ · 1 bộ hỏng** (`thu_qa_g18.py`). Trên `a3400a8` tôi đo được **1870 ca · 51 bộ ·
2 bộ hỏng**: nhánh gộp G20 thêm **4 bộ và 137 ca**, và **thêm một bộ đỏ mới** là bộ thử của chính
làn SAO LƯU. Bộ đỏ thứ hai là ca bàn phím tầng 3, y như G20 — xem §1.2 và §4.2.

### 1.2 Bộ đỏ thứ nhất **KHÔNG TẤT ĐỊNH** — đo tới đáy, không dừng ở dòng tóm tắt

`chay_tat_ca.sh` chỉ in được một dòng cho bộ đỏ:

```
  ✗ thu_g20_saoluu.py          41 ca  HỎNG (mã thoát 1)
        FAIL: test_e3_DOC_HAI_DA_BIET_ba_luot_cung_giay_ghi_de_mat_ban_cat_duy_nhat
```

Tôi chạy **cùng tệp đó một mình**:

```sh
python3 app/thu/thu_g20_saoluu.py     # log: g20_saoluu_doc_lap.txt
# === EXIT CODE THAT = 0
#   1 lượt khôi phục → 1 bản cất · 3 lượt cùng giây → 1 bản cất
#   bản cất còn giữ được dữ liệu vừa mất: False
```

⇒ **Cùng một tệp, cùng một commit, cùng một máy: ĐỎ trong lượt chung và XANH khi chạy riêng.** Đây
là một phát hiện thật, không phải nhiễu báo cáo — **`N-G21-01`** ở §5.1.

### 1.3 `C3` đo trực tiếp, **không qua** bộ chạy nào

```sh
git rev-parse HEAD                 # KHÔNG gỡ biến môi trường
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
| Cùng lệnh, **đã gỡ** gia đình biến | **exit 0** · `a3400a8…` |

⇒ `N-G18-00` **tái diễn lần thứ tư** trên nền G20. Vá trong **bộ chạy** vẫn có tác dụng; **GỐC CHƯA
VÁ**: ai gọi `git` trực tiếp vẫn nhận **128**.

### 1.4 Lượt hồi quy **THỨ HAI** — khi cây đã có hai tệp AG-01 G21

Sau khi tạo hai tệp được phép, tôi chạy lại hồi quy chung **bên trong** làn đầy đủ của bộ kiểm tôi
(`VIP_G21_DAY_DU=1`, mục `H1`; log `$TMPDIR/veh_g21_ag01_qa_log/hoi_quy.log`):

```
  python:   1894 ca · 52 bộ chạy thật
  bộ hỏng:  thu_g20_baomat.py thu_qa_g17.py thu_qa_g18.py
```

**Phép cộng là một đối chứng độc lập:** lượt nền cho **1870 ca · 51 bộ** (§1.1); thêm đúng tệp của
tôi (**24 ca**, **1 bộ**) thì lượt chung cho **1894 ca · 52 bộ** ⇒ **1870 + 24 = 1894** ✓ và
**51 + 1 = 52** ✓. Không ca nào biến mất, không bộ nào bị nuốt.

**Và đây là con số định lượng cho khoản nợ "cây sạch":** chỉ cần **hai tệp mà đề bài CHO PHÉP tôi
tạo** xuất hiện, số bộ đỏ đi từ **2** lên **3** — trong đó **hai bộ đỏ hoàn toàn không liên quan tới
sản phẩm** (`thu_qa_g17.py`, `thu_g20_baomat.py` đỏ **chỉ vì** hai tệp hợp lệ của tôi). Xem §5.3.

> **Chính cổng `H1` của tôi đã tìm ra bản sao thứ ba.** Lượt `DAY_DU` đầu tiên **HỎNG** với:
> `AssertionError: BỘ ĐỎ KHÔNG RƠI VÀO NHÓM NÀO = HỎNG SẢN PHẨM: thu_g20_baomat.py`. Lúc đó tôi mới
> biết khoản nợ có **ba** bản sao chứ không phải hai — và tôi **mở rộng cổng `G1` từ 2 lên 3** thay
> vì thêm `thu_g20_baomat.py` vào danh sách "đã biết" rồi đi tiếp. Thêm nó vào danh sách mà **không**
> mở rộng cổng thì một bản vá **2/3** sẽ lọt qua — đúng ô `NUA_VOI` mà §2.0 cấm.

**Lượt làn đầy đủ THỨ HAI (sau khi mở rộng `G1` 2→3) — ĐẠT, và đây là số CHỐT:**

```sh
VIP_G21_DAY_DU=1 python3 app/thu/thu_qa_g21.py
# 07:47:08Z → 08:02:13Z   Ran 24 tests in 905.358s · OK (skipped=3) · EXIT=0
# log g21_day_du_lan2.txt · sha256 554e3a59e13d6288b1238da6ca9181d8e59edf8214d955ae904debfbc0eafdfe
#   [H1] `sh app/thu/chay_tat_ca.sh` mã thoát=1 · 1894 ca · 52 bộ · 657 giây
```

| Ca | Phép đo | **Số thật** |
|---|---|---|
| `H1` | `sh app/thu/chay_tat_ca.sh` NGUYÊN VĂN (cờ làn đầy đủ **đã gỡ**, có `T5` canh) | **thoát 1** · **1894 ca** · **52 bộ** · **657 giây** |
| `H1` | bộ hỏng | **3**: `thu_g20_baomat.py` · `thu_qa_g17.py` · `thu_qa_g18.py` — **cả ba rơi vào nhóm CÓ TÊN** |
| `H1` | phân loại | cả ba → `N-G19-03/N-G21-05` (cây sạch); `thu_qa_g18.py` thêm `N-G18-01` (bàn phím) |
| `H1` | **bộ đỏ VÔ DANH** | **0** ⇒ **không** HỎNG SẢN PHẨM |
| `H1` | chạy lại từng bộ một mình | cả ba **vẫn thoát 1** ⇒ ĐỎ **TẤT ĐỊNH**, không phải nhiễu bộ chạy |
| `H1` | `thu_g20_saoluu.py` (bộ đỏ **chập chờn** ở §1.2) | lượt chung này **XANH** ⇒ **xác nhận lần thứ ba** nó không tất định: **ĐỎ 1 / XANH 2** trên ba lượt chung |

> **Vì sao `H1` KHÔNG đòi `bộ hỏng == []`.** Trên nền này ba khoản nợ **CÓ THẬT** làm hồi quy đỏ, và
> **đó là kết quả ĐÚNG**. Việc của `H1` không phải "không có bộ đỏ" — mà là **"không có bộ đỏ nào VÔ
> DANH"**. Bộ nào không rơi được vào nhóm có tên ⇒ **HỎNG SẢN PHẨM** và `H1` **ĐỎ**. Ba khoản nợ kia
> có **cổng riêng** (`G1`, `G3`) và chúng **ĐỎ** ở chế độ `gop`; ở `H1` chúng chỉ được **PHÂN LOẠI**,
> không được tha.

---

## 2. KẾ HOẠCH NGHIỆM THU G21 — MỖI LÀN MỘT CỔNG FAIL

### 2.0 Cơ chế cốt lõi — SỔ HAI Ô, và ô thứ ba là ĐỎ

```
"nen"  = giá trị TÔI ĐO ĐƯỢC trên a3400a8   (khoản nợ CÒN NGUYÊN)
"dong" = giá trị phải có khi khoản nợ đã đóng (điều kiện nghiệm thu)

giá trị == "nen"     -> NEN
giá trị == "dong"    -> DONG
giá trị KHÁC CẢ HAI  -> NUA_VOI  ==> LUÔN ĐỎ, ở mọi chế độ
```

Ở chế độ `VIP_G21_CHE_DO=gop` thì ô **`NEN` cũng ĐỎ** ⇒ nợ chưa đóng **không thể lọt qua** bằng câu
"nền còn đóng băng". Cơ chế này **đã được đo, không phải hứa**: cùng một cây, cùng một tệp,

```sh
python3 app/thu/thu_qa_g21.py
# → Ran 24 tests in 71.347s · OK (skipped=4) · EXIT 0        (log g21_mac_dinh_lan3.txt, sha256 a0d709e0…)

VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
# → Ran 24 tests in 78.936s · FAILED (failures=8, skipped=4) · EXIT 1
#                                                            (log g21_gop_lan2.txt, sha256 84bd3bb3…)
```

⇒ **8/8 cổng ĐỎ ở chế độ `gop`** và **làn mặc định XANH** — nên bộ kiểm **không** phải một cổng hỏng
sẵn, và **không** phải một cổng luôn xanh. Đó là bằng chứng "cổng có răng" (§2.9 `T4` làm chặt thêm:
giá trị **nửa vời** bị phán `NUA_VOI` ở **cả hai** chế độ).

### 2.1 `G4` — AG-02: **sao lưu phải FAIL-CLOSED** — **ĐỎ**

**Cách đo:** 4 đầu vào độc hại đi qua **đúng đường người trực dùng**, trên nền cô lập:

```sh
VIP_HUB_DATA=<nền tạm> python3 app/migrate.py --rollback <tệp độc hại>
```

| Đầu vào ĐỘC HẠI | rc | CSDL sau khi "khôi phục" |
|---|---|---|
| `rong-0-byte` | **0** | **0 bảng** · `integrity_check = "ok"` ← **nguy hiểm nhất** |
| `cat-cut-40-phan-tram` | **0** | `DatabaseError: database disk image is malformed` |
| `byte-0-magic-hong` | **0** | `DatabaseError: file is not a database` |
| `khong-phai-sqlite-PGDMP` | **0** | `DatabaseError: file is not a database` |
| **ĐỐI CHỨNG DƯƠNG** — `LANH` (sao lưu thật) | **0** | **52 bảng · 140 dòng · integrity `ok`** = đúng nền sạch |

⇒ **4/4 nhận** (nền). **Đóng = 0/4, VÀ tệp LÀNH vẫn phải được nhận với dữ liệu nguyên vẹn.**
**CỔNG FAIL: `> 0` đầu vào độc hại được nhận (rc 0), hoặc tệp LÀNH bị từ chối / khôi phục sai.**

> **Vì sao đối chứng dương là bắt buộc ở đây:** không có nó thì "0/4 nhận" có thể chỉ là một
> `khoi_phuc()` hỏng sẵn. Và lưu ý **tệp 0 byte qua được `PRAGMA integrity_check`** với kết quả
> `"ok"` — nên một bản vá chỉ thêm `integrity_check` **sẽ không** đóng được K-1; phải kiểm **số byte**
> hoặc **số bảng**. Đó là điều kiện tôi sẽ đo lại ở lượt 2, không tin lời khai.

### 2.2 `G5` — AG-03: **credential NGẮN của hãng KHÁC J&T không được rò** — **ĐỎ**

**Cách đo:** stub **ECHO LẠI** nguyên header + thân, kèm **HTTP 401**, chỉ `127.0.0.1` cổng OS cấp.
Stub **phải echo** — nếu không thì không có gì để rò và phép đo sẽ xanh **vì stub**.

Ngưỡng đo được: `http_jt.DAI_TOI_THIEU_DE_CHE = 8`. Canary NGẮN 5 ký tự `A1b2C`; canary DÀI
`K7x` + `Qw9z`×8 (35 ký tự).

| Tổ hợp (tên trường, giá trị) | Kết quả | Nghĩa |
|---|---|---|
| `privateKey` + NGẮN (tên **J&T**) | **KHÔNG rò** | tầng che theo **TÊN** còn sống |
| `x-mau-khoa-bi-mat` + NGẮN (tên **hãng giả**) | **RÒ qua `than_da_che` + `str(e)`** | **khoản nợ** |
| `maTaiKhoanGia` + NGẮN | **RÒ qua `than_da_che` + `str(e)`** | **khoản nợ** |
| `privateKey` + DÀI | KHÔNG rò | **đối chứng dương** |
| `x-mau-khoa-bi-mat` + DÀI | KHÔNG rò | **đối chứng dương** |

⇒ **2/5 tổ hợp rò** (nền). **Đóng = 0/5.** **CỔNG FAIL: `> 0` tổ hợp rò, HOẶC hai tổ hợp DÀI cũng rò
(tầng theo độ dài chết), HOẶC `privateKey`+NGẮN rò (tầng theo tên chết) — hai vế sau là điều kiện
"phép đo mù", không được tính là ĐẠT.**

> **Lệch có ghi lại, không hoà giải:** `G20_DA_HANG.md` §5 ghi vết rò gồm **ba** kênh
> (`than_da_che` + `headers_da_che` + `str(e)`). Với stub của tôi, kênh `headers_da_che` **không**
> chứa canary ⇒ tôi ghi **hai** kênh. Hai bàn đo khác stub thì khác số kênh; **số tổ hợp rò = 2** là
> con số của tôi, đo trên `a3400a8`.

### 2.3 `G6` — AG-04: **harness giới hạn tần suất phải chạy HẾT và XANH** — **ĐỎ**

```sh
sh trien_khai/g18/chay_harness.sh
# 07:23:05Z → 07:23:36Z (31 giây)   sha256 1d31f310dd5f50a0d3bf7a6b43c162c9428c73bee9f38657d126a760868aef2e
# === EXIT CODE THAT = 1
```

```
✗ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
```

⇒ **ĐỎ — thoát 1**, đúng chặng đã được `G20_CONTRACT_HARNESS.md` §6 truy nguyên (`gioi_han.xoa_het()`
xoá kho đếm **DÙNG CHUNG**, nên bucket vừa bị xoá sạch trước chặng G18-05). **Đóng = thoát 0.**
**CỔNG FAIL: thoát ≠ 0, HOẶC output không có dòng tổng kết (harness không khởi động được — khi đó là
CHƯA ĐO, không phải ĐẠT).**

### 2.4 `G7` — AG-04: **phải có ≥1 bộ G19-tổng-hợp CHẠY THẬT** — **ĐỎ**

```sh
python3 app/thu/thu_qa_g19.py
# → mã thoát 0 · 0 ca   (tự BỎ QUA: bộ này ghim nền cũ 6e61fc1)
```

| Phép đo | Số thật |
|---|---|
| Bộ khớp `thu_qa_g19*.py` | **1** — `thu_qa_g19.py` |
| Bộ đó chạy được ≥1 ca trên cây này | **KHÔNG** (0 ca, tự bỏ qua) |
| Bộ G19-tổng-hợp chạy thật | **0 / 1** |

**Đóng = 1.** **CỔNG FAIL: `< 1` bộ chạy thật, HOẶC không còn tệp `thu_qa_g19*.py` nào (phép đo vô
nghĩa, KHÔNG phải ĐẠT).**

### 2.5 `G1` — AG-05: **tệp HỢP LỆ của làn khác không được làm cổng cũ ĐỎ** — **ĐỎ**

**Ba cổng, không phải hai** — vì khoản nợ này có **ba bản sao** trong dự án (đo được: §5.3 `N-G21-05`):

```sh
python3 app/thu/thu_qa_g17.py     A_Nen.test_a1_cay_sach_va_head
python3 app/thu/thu_qa_g18.py     A_Nen.test_a1_cay_sach_theo_pham_vi_wave
python3 app/thu/thu_g20_baomat.py A_Nen.test_a1_cay_sach_theo_pham_vi_wave
```

| Phép đo | Số thật trên nền |
|---|---|
| `thu_qa_g17.py` | **exit 1** · `DO_THAT` |
| `thu_qa_g18.py` | **exit 1** · `DO_THAT` |
| `thu_g20_baomat.py` | **exit 1** · `DO_THAT` |
| Cổng XANH | **0 / 3** |
| Miễn trừ của g18 nhận ra **tệp của chính nó** | **True** (cơ chế còn sống, không phải cổng hỏng sẵn) |
| Giá trị "đóng" (3/3) tới được? | **CÓ** — `q17._cay_ban(ngoai=<tệp AG-01 G21>)` → **`[]`**; và `qb._loc_cay_ban(<tệp AG-01 G21>, qb.TEP_CUA_WAVE_G20 + <tệp AG-01 G21>)` → **`[]`** |

⇒ **Đóng = 3/3.** **CỔNG FAIL: `< 3/3` cổng XANH, HOẶC giá trị `1` hay `2` (nửa vời — sửa được một
hay hai bản sao).** Bộ kiểm **phân biệt ba lớp** cho mỗi cổng — `XANH` · `DO_THAT` (cây bẩn thật) ·
`PHEP_DO_CHET` (tên ca không tồn tại / `Ran 0 tests`) — và **một phép đo chết làm cổng HỎNG NGAY**,
không được đếm thành "cây bẩn" (`L-G20-C`, §5.2).

### 2.6 `G2` — AG-05: **`git` với môi trường NGUYÊN BẢN** — **ĐỎ**

Xem §1.3. Giá trị: **128** (nền) → **0** (đóng). Đối chứng dương: **cùng lệnh**, chỉ khác là đã gỡ
gia đình biến ⇒ **exit 0** và `git status` cũng **exit 0**.

**CỔNG FAIL: mã thoát ≠ 0.** Chẩn đoán phải nêu **đúng** `GIT_CONFIG_KEY_0`; nếu git thoát ≠ 0 vì
nguyên nhân khác thì bộ kiểm **phán HỎNG** chứ không ghi "nợ còn nguyên".

> **NÓI THẲNG MỘT ĐIỀU VỀ CỔNG NÀY.** `N-G18-00` là **dị dạng MÔI TRƯỜNG của phiên chạy**, không nằm
> trong mã nguồn repo. Nếu làn `g21-ag05-chotcay` **không** nêu ra **cơ chế** làm cho `git` trực tiếp
> thoát 0 trong môi trường nguyên bản (sửa môi trường? một chốt trong bộ chạy? một tài liệu bắt
> buộc?), thì cổng này **không thể** chuyển XANH bằng một bản vá trong repo — và tôi sẽ **giữ nguyên
> nó ĐỎ**, không hạ cổng xuống cho vừa.

### 2.7 `G3` — AG-06: **bàn phím TRONG màn, tầng 3 Chromium thật** — **ĐỎ**

**Cách đo:** dựng máy chủ trên nền **CÔ LẬP** (ÉP `VIP_HUB_BIND=127.0.0.1`, cổng OS cấp), chạy
**đúng khuôn `thu_giao_dien/chay.sh`**, chỉ khác **đường nhị phân Chromium** (§4.1 giải thích vì sao
buộc phải khác):

```sh
npx playwright test 06_ban_phim.spec.js
```

| Phép đo | Số thật trên nền |
|---|---|
| Bộ ba (ĐẠT, HỎNG, **KHÔNG CHẠY**) | **(3, 1, 3)** |
| Mã thoát Playwright | **1** |
| Ca hỏng | `06_ban_phim.spec.js:153 › 04 — Tab vào được các điều khiển TRONG màn` |
| **Điểm dừng Tab vào được điều khiển TRONG màn** | **1** (đặc tả đòi **`> 10`**) |
| **3 ca KHÔNG HỀ CHẠY** | ca **05** · ca **06** (TỰ KIỂM gỡ `ban_phim.js`) · ca **07** |

```
[đo] 30 lượt Tab: 1 điểm dừng là điều khiển trong màn · 0 lượt ở body · 30 đích khác nhau
Error: 30 lượt Tab chỉ vào được 1 điều khiển trong màn
Expected: > 10   Received: 1
```

⇒ **Đóng = (7, 0, 0)** — cả 7 ca **chạy**, không ca nào hỏng.
**CỔNG FAIL: bộ ba ≠ (7, 0, 0).** Đặc biệt: một giá trị như `(7, 0, 1)` hay `(2, 5, 0)` là **NỬA VỜI
⇒ ĐỎ**, vì `did not run` **không bao giờ** được gộp vào "bỏ qua" hay "đạt" (`N-G20-03`).

### 2.8 `G8` — **KHÔNG LÀN NÀO SỞ HỮU**: C4 (C6 của G19 nửa vời) — **ĐỎ**

```sh
# PHIEN_BAN_SCHEMA=9 · nang_len_v9=True · tệp SẢN XUẤT import truy_van = 0
```

| Phép đo | Số thật |
|---|---|
| `csdl.PHIEN_BAN_SCHEMA` + `migrate.nang_len_v9` | **True** (v9 đã gộp) |
| Tệp **SẢN XUẤT** (ngoài `app/thu/**`) import `truy_van` | **0** |
| Cặp giá trị | **(True, False)** |

⇒ **Đóng = (True, True).** **CỔNG FAIL: cặp ≠ (True, True)** — và vì **không làn nào sở hữu**, cổng
này **sẽ vẫn ĐỎ** ở lượt nghiệm thu bản đã gộp, trừ khi AG-00 mở một làn mới.

### 2.9 HAI CHỐT CHẶN BẮT BUỘC — chạy **thật**, không phải khai

**CHỐT (a) — ca TỰ KIỂM BỘ ĐO chạy trong TIẾN TRÌNH CON.** Không có nó thì mọi dòng `✓ … ca` của tệp
tôi **không chứng minh gì**: một ca tự kiểm gọi thẳng hàm trong **cùng** tiến trình vẫn có thể "xanh"
nhờ trạng thái đã bị chính bộ thử làm bẩn.

| Ca | Phép đo | Kết quả thật |
|---|---|---|
| `T2` | tiến trình con chạy ca **CỐ Ý HỎNG** | **thoát 1** + có `FAILED` ⇒ luật phán trả **HỎNG** |
| `T2` | **ĐỐI CHỨNG DƯƠNG**: cùng tệp, ca **CỐ Ý ĐẠT** | **thoát 0** + có `OK` + `Ran 1 test` |
| `T1` | luật phán phải **TỪ CHỐI** giá trị lửng lơ | `1/2` → `NUA_VOI` · `3` → `NUA_VOI` · `(6,0,0)` → `NUA_VOI` |
| `T4` | giá trị **NỬA VỜI** phải ĐỎ ở **CẢ HAI** chế độ | 3 cổng × 2 chế độ đều **ĐỎ**; giá trị **ĐÓNG** đều **qua** |
| `T5` | **chốt chống ĐỆ QUY**: `bo_bien` phải gỡ **thật** biến khỏi tiến trình con | có gỡ → `CO=False` · không gỡ → `CO=True` |
| `G3b` | bộ đếm Playwright **không gộp** `did not run` vào đạt | `4 passed · 1 did not run` → `(4, …, 1)` |

**CHỐT (b) — ĐỐI CHỨNG DƯƠNG cho MỌI ca phủ định.** Sổ `DOI_CHUNG` in ra ở `Z1`, và `Z1` **tự phán
HỎNG** nếu một nhóm có ca ÂM mà thiếu ca DƯƠNG; `Z1` cũng **tự kiểm chính nó** (một nhóm âm cố ý
không có dương **phải** bị nó bắt). Kết quả lượt `gop`:

```
  [Z1] 14 nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả
  [Z1] bo-g19-tong-hop      âm=1 dương=1      [Z1] harness-gioi-han    âm=1 dương=1
  [Z1] cong-cay-sach        âm=1 dương=1      [Z1] live-khoa           âm=1 dương=1
  [Z1] cum-5432             âm=1 dương=1      [Z1] ro-credential-ngan  âm=1 dương=1
  [Z1] dem-playwright       âm=1 dương=1      [Z1] sao-luu-fail-closed âm=1 dương=1
  [Z1] git-tho              âm=1 dương=1      [Z1] sqlite-D8           âm=1 dương=1
  [Z1] go-bien              âm=1 dương=1      [Z1] tang3-ban-phim      âm=1 dương=1
  [Z1] truy-van-C6          âm=1 dương=1      [Z1] tu-kiem-con         âm=1 dương=1
```

Mỗi cặp nằm trên **cùng một hàm đo**, nên không thể có chuyện hàm đo hỏng mà cả hai cùng xanh. Ví dụ:
`git-tho` có ca **âm** (môi trường nguyên bản, phải khác 0) và ca **dương** (đã gỡ biến, phải bằng 0)
— **cùng một lệnh `git rev-parse HEAD`**; `sao-luu-fail-closed` có ca âm (4 tệp độc hại) và ca dương
(tệp LÀNH, dữ liệu nguyên vẹn) — **cùng một hàm `_thu()`**.

---

## 3. ĐO LẠI NĂM CỔNG G20 (`C1`..`C5`) TRÊN `a3400a8`

Bộ kiểm G20 là **bàn đo độc lập thứ hai** cho cùng năm khoản nợ. AG-00 cho phép **(a)** chép **tạm**
`app/thu/thu_qa_g20.py` vào worktree này để đo rồi **xoá trước khi kết thúc**; tôi đã làm đúng vậy
(`sha256` bản chép **5a4b3c83c45f2f2c465d2eed380f1f6f69583878ca9e3a5f910bd01c1a0ddcd0` = đúng bản
`QA_G20.md` §dòng 7 ghim; đã **xoá**, xem §7).

```sh
VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
# 07:16:25Z → 07:17:02Z   sha256 3d17633e8f85b5c72437cc50e24cb56847f076813887347e2c75e3e920a177c5
# Ran 21 tests in 48.476s · FAILED (failures=6, skipped=2) · EXIT=1
```

| Cổng G20 | Khoản nợ | **`a3400a8` (tôi đo lại)** | So với `148ecd3` (G20 đo) |
|---|---|---|---|
| **C1** | `N-G19-03` cổng cây sạch miễn trừ tên cứng | **ĐỎ — 0/2** *(xem cảnh báo dưới bảng)* | **Y NGUYÊN** |
| **C2** | `V-13911` bàn phím trong màn | **ĐỎ — (3, 1, 3)**, ca 04 = **1** điều khiển (đòi `>10`) | **Y NGUYÊN** |
| **C3** | `N-G18-00` git môi trường nguyên bản | **ĐỎ — 128** | **Y NGUYÊN** |
| **C4** | C6 của G19 nửa vời (route `truy_van`) | **ĐỎ — (True, False)**, 0 tệp sản xuất import | **Y NGUYÊN** |
| **C5** | `N-G20-01` không bộ G19-tổng-hợp nào chạy | **ĐỎ — 0/1** | **Y NGUYÊN** |

⇒ **CẢ NĂM CỔNG G20 VẪN ĐỎ TRÊN NỀN G21.** Năm làn sửa chưa gộp vào `a3400a8` — đúng như dự kiến
(nền đóng băng trước khi sửa). Đây là **thuốc đo "TRƯỚC"** cho lượt nghiệm thu bản đã gộp.

> ⚠ **CẢNH BÁO VỀ CON SỐ `C1 = 0/2` — MỘT NỬA CỦA NÓ LÀ PHÉP ĐO CHẾT.** `CONG_CAY_SACH` của bộ kiểm
> G20 gọi `thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01`. **Tên ca đó KHÔNG CÒN
> TỒN TẠI** trên `a3400a8` — nó đã được đổi thành `test_a1_cay_sach_theo_pham_vi_wave` khi gộp G20.
> Đo trực tiếp:
>
> ```sh
> python3 app/thu/thu_qa_g18.py A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01
> # → Ran 1 test in 0.000s · FAILED (errors=1)   ← ERROR, không phải FAILURE
> # === EXIT CODE THAT = 1
> ```
>
> ⇒ `0/2` = **1 cổng ĐỎ THẬT** (`g17`, cây bẩn vì tệp AG-01 G20) **+ 1 phép đo CHẾT** (tên ca sai).
> Bộ kiểm của tôi vì thế **không dùng** tên cũ, đo **ba** cổng còn sống, và **phân loại**
> `DO_THAT` ≠ `PHEP_DO_CHET` (§5.2 `L-G20-C`). Đây là lý do thứ hai — sau `L-G20-A` — khiến bộ kiểm
> G20 **không dùng lại được nguyên trạng**.

### 3.1 `failures=6`, không phải 5 — và lỗi thứ sáu là **của chính bàn đo G20**

Năm cổng ĐỎ + **một** đỏ nữa. Tôi truy tới đáy:

```
FAIL: test_c1_git_voi_moi_truong_NGUYEN_BAN (__main__.C_MoiTruong)
  File "…/thu_qa_g20.py", line 520, in test_c1_git_voi_moi_truong_NGUYEN_BAN
    self.assertEqual(r2.stdout.strip(), HEAD_NEN)
AssertionError: 'a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1' != '148ecd380a9009c7b01dc0c268a3f1a97327a164'

FAIL: test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong (__main__.Z_ChotChan)
AssertionError: Lists differ: ['git-tho'] != [] : THIẾU ĐỐI CHỨNG DƯƠNG cho: ['git-tho']
```

**Đó là `L-G20-A` và `L-G20-B` — xem §5.2.** Và vì lượt chạy này còn một hệ quả nữa, tôi chạy luôn
**làn MẶC ĐỊNH** của bộ kiểm G20 trên cây đã gộp:

```sh
python3 app/thu/thu_qa_g20.py
# → Ran 21 tests in 38.146s · FAILED (failures=2, skipped=3) · EXIT=1
```

`QA_G20.md` §7 mục 4 ghi: *"làn mặc định — **phải XANH**; nếu không, chính bộ kiểm hỏng."* Trên
`a3400a8` nó **KHÔNG XANH**. ⇒ **Bộ kiểm G20 KHÔNG dùng lại được nguyên trạng** cho lượt nghiệm thu
G21; đối chứng dương của nó phải được **bỏ ghim nền** trước (xem §5.2 và §8).

---

## 4. NỀN E2E TRÊN `a3400a8`

### 4.1 `sh thu_giao_dien/chay.sh` — **HỎNG SẴN 7/7 VÌ MÔI TRƯỜNG, KHÔNG CHO TÍN HIỆU SẢN PHẨM**

```sh
sh thu_giao_dien/chay.sh
# 07:19:10Z → 07:19:24Z (14 giây)   sha256 84e962a00ba1ff5d313a4360ad8cda350ddda289f2d3b836dc1689e22b4ef834
# === EXIT CODE THAT = 1
#   7 failed  ·  44 did not run
```

**Đọc log TRƯỚC khi kết luận** (đúng luật của đề bài). Nguyên nhân **nằm ở MỘT dòng, giống nhau cho
cả 7 đặc tả**:

```
Error: browserType.launch: Executable doesn't exist at
  /Users/viporder/orca/workspaces/vip-express-hub/g21-ag01-qa/node_modules/playwright-core/
  .local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
```

| Phép đo | Số thật |
|---|---|
| Ca hỏng | **7** — tức **cả 7 đặc tả**, mỗi tệp hỏng ngay ở ca đầu |
| Ca `did not run` | **44** |
| Đặc tả nào chạm được logic sản phẩm? | **KHÔNG một đặc tả nào** — tất cả chết ở `browserType.launch` |
| `node_modules/playwright-core/.local-browsers` | **KHÔNG TỒN TẠI** trong worktree này |
| Nhị phân CÓ trên máy | `~/code/veh4-g12-playwright/…/.local-browsers/chromium-1194` + `chromium_headless_shell-1194` |

**Vì sao:** `thu_giao_dien/chay.sh` ghim cứng `PLAYWRIGHT_BROWSERS_PATH=0` (tức
`node_modules/playwright-core/.local-browsers`), mà thư mục đó **không có** trong worktree.

⇒ **Đây KHÔNG phải lỗi sản phẩm và cũng KHÔNG phải lỗi sandbox chặn ghi.** Đây là **thiếu nhị phân
trình duyệt**. **Hệ quả cho năm làn sửa, nói thẳng:** ai chạy `sh thu_giao_dien/chay.sh` trên worktree
này rồi đọc "7 failed" là đọc **số của môi trường**, không phải số của sản phẩm. Làn **AG-06
(`e2e`)** **không được** kết luận E2E trên lượt chạy đó — xem `N-G21-04` §5.5.

### 4.2 Tầng 3 **THẬT** — chạy được bằng nhị phân ghim: **ca nào hỏng SẴN trên nền**

Để có **tín hiệu sản phẩm thật**, tôi chạy **trọn bộ 7 đặc tả (51 ca)** qua driver nền cô lập, chỉ
khác **đường nhị phân**:

```sh
# driver dùng `do_tang_3()` của bộ kiểm G20 (bind 127.0.0.1 · cổng OS cấp · tắt theo ĐÚNG PID)
# sha256 log: 63ffe43f80ccf60e23db4a3932f52807a600a17c8b42a89aea06f9c91bc31273
# MA_THOAT_TANG3=1 · DEM=(47, 1, 0, 3) · DIEM_DUNG_TRONG_MAN=1
#   1 failed · 3 did not run · 47 passed (2.2m)
```

| Chỉ tiêu | **Số thật** |
|---|---|
| Nhị phân | `chỉ định BAN_GIAO §1` — `chromium-1194` |
| Tổng ca | **51** |
| **ĐẠT** | **47** |
| **HỎNG** | **1** — `06_ban_phim.spec.js:153 › 04 — Tab vào được các điều khiển TRONG màn` (`Expected: > 10`, `Received: 1`) |
| **KHÔNG CHẠY** | **3** — ca 05, 06, 07 của `06_ban_phim.spec.js` |
| Bỏ qua | **0** |

⇒ **Ca hỏng SẴN trên nền: ĐÚNG MỘT** — ca 04 bàn phím trong màn, tất định (đo **2/2** lượt: lượt
trong `chay_tat_ca.sh` qua `thu_qa_g18.py`, và lượt riêng này, **cùng một ca, cùng con số `1`**).
Và **ba ca còn lại của cùng tệp KHÔNG HỀ CHẠY** — chúng **không được** tính là đạt.

> **Con số này trùng khớp với bàn đo G20 (`(47, 1, 0, 3)`)** — nhưng tôi đo ra nó trên `a3400a8`,
> không chép. Đây là **đối chứng chéo độc lập** cho thấy tầng 3 **không hồi quy** khi gộp G20, và
> khoản nợ bàn phím **vẫn nguyên**.

---

## 5. PHÁT HIỆN

### 5.1 `N-G21-01` — **CAO**: ca thử của làn SAO LƯU **KHÔNG TẤT ĐỊNH**, và tín hiệu ĐỎ của nó **nhập nhằng**

`app/thu/thu_g20_saoluu.py::E_KhoiPhucDeLenCsdlDangChay::test_e3_DOC_HAI_DA_BIET_ba_luot_cung_giay_ghi_de_mat_ban_cat_duy_nhat`
**ghim một hành vi ĐỘC HẠI** (K-3: ba lượt `khoi_phuc()` trong **cùng một GIÂY** ghi đè bản cất duy
nhất). Ba khẳng định của nó — `so_ban_cat_sau_3_lan == 1`, `ban_cat_con_giu_duoc_du_lieu_goc is False`,
hai băm khác nhau — **chỉ đúng nếu ba lượt khôi phục rơi vào CÙNG MỘT GIÂY ĐỒNG HỒ TƯỜNG**.

| Lượt | Cách chạy | Kết quả |
|---|---|---|
| 1 | trong `sh app/thu/chay_tat_ca.sh` | **ĐỎ** (exit 1) |
| 2 | `python3 app/thu/thu_g20_saoluu.py` một mình | **XANH** (exit 0) |

**Hai hệ quả, và hệ quả thứ hai mới là hệ quả đắt:**

1. **Số bộ đỏ của hồi quy chung phụ thuộc TẢI MÁY, không tất định.** Máy bận ⇒ ba lượt khôi phục
   vượt qua ranh giới giây ⇒ hành vi độc hại không tái hiện ⇒ ca đỏ. Đây là **nhiệt kế phụ thuộc
   đồng hồ**, không phải cổng sản phẩm.
2. **Khi làn AG-02 vá `khoi_phuc()` cho fail-closed (điều ĐÚNG phải làm), ca này SẼ ĐỎ — và ĐỎ vì lý
   do THẬT.** Nhưng nó **không phân biệt được** với lý do **GIẢ** ở mục 1: cùng một dòng `FAIL`, cùng
   một ca, cùng một tệp. Chính docstring của ca viết: *"Nếu ca này đỏ: ai đó đã vá `khoi_phuc()`"* —
   **sai**, vì hôm nay nó đỏ vì máy bận.

**Việc phải làm (không phải việc của tôi — tôi là người kiểm, không sửa):** làn AG-02 phải **viết lại
khẳng định theo BẤT BIẾN ĐÚNG** — *bản cất của lượt ĐẦU phải còn nguyên vẹn sau N lượt khôi phục* —
và **nói rõ ca cũ ghim gì** (nó ghim **tên bản cất đặt theo GIÂY ⇒ ghi đè im lặng**). **KHÔNG được**
nới điều kiện cho qua (ví dụ thêm `time.sleep` để "ổn định" ca thử, hay hạ `assertEqual(..., 1)`
xuống `assertLessEqual(..., 3)`) — cả hai đều là **làm hỏng nhiệt kế để nhiệt kế khỏi kêu**.

### 5.2 `L-G20-A` / `L-G20-B` / `L-G20-C` — **BA LỖI CỦA CHÍNH BÀN ĐO G20**, lộ ra khi chạy trên cây đã gộp

| Mã | Chỗ | Triệu chứng | Nguyên nhân thật |
|---|---|---|---|
| **`L-G20-A`** | `thu_qa_g20.py` **dòng 520** | cổng **C3** ĐỎ vì `'a3400a8…' != '148ecd3…'` | **ĐỐI CHỨNG DƯƠNG bị GHIM NỀN**: `assertEqual(r2.stdout.strip(), HEAD_NEN)` với `HEAD_NEN = 148ecd3…`. Trên cây đã gộp, `git rev-parse HEAD` trả **đúng** HEAD mới — nên đối chứng **luôn** đỏ. Phép đo C3 (`128`) thì vẫn đúng, nhưng **lý do ĐỎ thì SAI**. |
| **`L-G20-B`** | `thu_qa_g20.py` **dòng 871** (`Z1`) | `THIẾU ĐỐI CHỨNG DƯƠNG cho: ['git-tho']` | **Hệ quả dây chuyền của `L-G20-A`**: `_dc_duong("git-tho")` nằm **sau** dòng 520, nên khi 520 ném thì nhóm `git-tho` chỉ còn ca ÂM. |
| **`L-G20-C`** | `thu_qa_g20.py` — `CONG_CAY_SACH` | cổng `C1` đo `g18` bằng **tên ca đã chết**; `FAILED (errors=1)`, `Ran 1 test in 0.000s` | **TÊN CA ĐÃ ĐỔI sau khi gộp G20**: `test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` → `test_a1_cay_sach_theo_pham_vi_wave`. Bộ đếm chỉ nhìn "mã thoát ≠ 0" nên đếm **một phép đo CHẾT** thành **một cổng ĐỎ vì cây bẩn** ⇒ `C1 = 0/2` gồm **1 ĐỎ thật + 1 phép đo chết**. |

**Điều đáng ghi nhất:** chốt (b) của G20 **đã làm ĐÚNG việc của nó** — nó phát hiện rằng một khẳng
định phủ định **thiếu đối chứng dương**, và nó phát hiện **chính bàn đo của mình**. Nhưng vì `L-G20-A`
làm `failures` từ 5 lên **6**, người đọc dễ tưởng có **sáu khoản nợ sản phẩm** trong khi thực tế là
**năm nợ + một lỗi bàn đo**. Và `L-G20-C` là loại lỗi **im lặng hơn**: nó không làm ai nghi ngờ, vì
`0/2` **trông đúng như đã khai trên nền G20**.

**Hệ quả vận hành, nói thẳng:** `QA_G20.md` §7 mục 4 đòi làn **MẶC ĐỊNH** của bộ kiểm G20 phải XANH;
trên `a3400a8` nó cho `FAILED (failures=2, skipped=3) · EXIT=1`. ⇒ **Bộ kiểm G20 không dùng lại được
nguyên trạng.** Bộ kiểm của tôi **đã sửa đúng cả ba chỗ đó**: `A1` kiểm nền bằng **TỔ TIÊN**
(`git merge-base --is-ancestor`) chứ không bằng `==`; `G2` kiểm đối chứng dương bằng **cùng lệnh đã gỡ
biến** rồi mới đòi `^[0-9a-f]{40}$` — **không ghim giá trị HEAD nào**; và `G1` **phân loại**
`DO_THAT` ≠ `PHEP_DO_CHET` rồi **phán HỎNG ngay** nếu có phép đo chết.

### 5.3 `N-G21-05` — **CAO**: khoản nợ "cây sạch" có **BA bản sao**, không phải hai

`G20_BAOMAT.md` §3.1 đã ghi bản sao **thứ ba** ở `thu_qa_g19.py` (dormant). Đo trên `a3400a8` với
**đúng hai tệp AG-01 G21** trong cây, tôi tìm được **ba bản sao ĐANG SỐNG**:

| Bản sao | Danh sách miễn trừ | Ca đo được | Trên cây có tệp AG-01 G21 |
|---|---|---|---|
| `thu_qa_g17.py` | `TEP_CUA_AG01_G17` (tên cứng) | `A_Nen.test_a1_cay_sach_va_head` | **exit 1** |
| `thu_qa_g18.py` | `PHAM_VI_WAVE` = `PHAM_VI_LAN_NHA` + `PHAM_VI_LAN_KHAC` (theo **wave**, vẫn đích danh) | `A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **exit 1** |
| `thu_g20_baomat.py` | `TEP_CUA_WAVE_G20` = **4 tệp viết tay** (g17, g18, chính nó, `docs/G20_BAOMAT.md`) | `A_Nen.test_a1_cay_sach_theo_pham_vi_wave` | **exit 1** |
| *(dormant)* `thu_qa_g19.py` | `TEP_CUA_AG01_G19` (tên cứng) | tự BỎ QUA khi HEAD ≠ `6e61fc1` | không đo được |

**Vì sao điều này quyết định phạm vi của AG-05:** một bản vá chỉ sửa `g17` + `g18` sẽ cho `G1 = 2/3`
⇒ **`NUA_VOI` ⇒ ĐỎ**. Bản vá phải **định nghĩa lại "cây sạch" trên CẢ BA** (và lý tưởng là cả bản
dormant thứ tư). Bộ kiểm của tôi giữ **`dong = 3`** cho tới khi cả ba XANH.

> **Đối chứng dương cho cả ba** (giá trị ĐÓNG phải TỚI ĐƯỢC, nếu không thì `0/3` chỉ là cổng hỏng sẵn):
> `q17._cay_ban(ngoai=<2 tệp AG-01 G21>)` → **`[]`** ·
> `qb._loc_cay_ban(<2 tệp AG-01 G21>, qb.TEP_CUA_WAVE_G20 + <2 tệp AG-01 G21>)` → **`[]`** ·
> và cả ba cổng đều **nhận ra tệp của chính chúng** khi cây sạch.

### 5.4 `N-G21-02` — **CAO (phạm vi)**: **C4 KHÔNG CÓ CHỦ SỞ HỮU** ⇒ nghiệm thu G21 vẫn FAILED

AG-00 xác nhận bằng văn bản ngày 16/10/2026 (trả lời `orca orchestration ask`):

> C3 ⇒ **có** làn: `g21-ag05-chotcay`. C5 ⇒ **có** làn: `g21-ag04-gioihan`.
> **C4 (route `truy_van` cho migration v9) ⇒ KHÔNG CÓ LÀN NÀO.**
> *"Nghiệm thu G21 VẪN là FAILED nếu C4 chưa đóng, dù năm làn kia xanh."*

**Số đo của tôi khớp:** `G8` = `(True, False)` — migration v9 **đã gộp**, `app/truy_van.py`
(**30.770 byte**, có `DDL_G12Q`) **tồn tại** nhưng **không một tệp SẢN XUẤT nào import nó**; nơi duy
nhất import là **chính bộ thử của nó** (`app/thu/thu_truy_van.py`). Một mô-đun chỉ được **bộ thử của
chính nó** gọi là mô-đun **KHÔNG CÓ ĐƯỜNG VÀO**.

**Đây là ô `NUA_VOI` thật, không phải ví dụ tổng hợp** — và nó **không** nằm trong năm làn G21. Tôi
giữ cổng `G8` **ĐỎ** và ghi thẳng vào §0, §2.8, §8; **tôi không hạ cổng xuống cho vừa.**

### 5.5 `N-G21-03` — **CAO**: một ca thử đang **GHIM chính hành vi RÒ** mà AG-03 phải diệt

`app/thu/thu_g20_dahang.py::CaGanChat::test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia`
**khẳng định hành vi rò là ĐÚNG**:

```python
self.assertTrue(ket_qua["gia_ngan"],
                "ĐỔI HÀNH VI: credential ngắn của hãng giả nay ĐƯỢC che — nếu ai đó vừa mở "
                "rộng `TRUONG_CREDENTIAL`, hãy cập nhật tài liệu và ca này")
```

Nghĩa là: **ngay khi AG-03 vá xong `G5` (0/5 rò), ca thử này SẼ ĐỎ** — và nó nằm trong
`app/thu/thu_g20_dahang.py`, **tệp của làn G20 AG-06**, có thể **ngoài phạm vi ghi** của AG-03.

**Luật áp cho chỗ này (đề bài, nguyên văn):** *"Nếu một ca thử đang ghim HÀNH VI CŨ thì viết lại khẳng
định theo bất biến ĐÚNG và nói rõ ca đó ghim gì; KHÔNG được nới điều kiện cho qua."*

⇒ Làn AG-03 phải **viết lại** `assertTrue(ket_qua["gia_ngan"])` thành **bất biến đúng**
(*"credential NGẮN **của BẤT KỲ hãng nào** đều không được rò"*), và **ghi rõ**: ca cũ ghim
*"tầng che theo TÊN chỉ đúng cho bốn tên của J&T"* (`G20_DA_HANG.md` §5 + §8 R-2). **Xoá ca, `skipTest`,
hay hạ `assertTrue` xuống một khẳng định yếu hơn đều là nới điều kiện cho qua** — và lượt nghiệm thu
của tôi sẽ bắt được vì `G5` đo **độc lập**, không qua ca đó.

### 5.6 `N-G21-04` — **TRUNG BÌNH**: `chay.sh` **không chạy được** trong worktree thiếu nhị phân

Xem §4.1. Nguyên nhân là `PLAYWRIGHT_BROWSERS_PATH=0` ghim vào
`node_modules/playwright-core/.local-browsers`, **thư mục không tồn tại** trong worktree này.

**Vì sao đáng ghi thành phát hiện chứ không chỉ là "lỗi môi trường":** đây là **bộ chạy E2E chính
thức của dự án** (`chay.sh` là thứ `chay_tat_ca.sh` chỉ sang). Trên nền này nó cho **7 failed · 44 did
not run** và **0 tín hiệu sản phẩm**. Làn **AG-06** vì thế **không thể** chứng minh "E2E đạt" bằng
`chay.sh`. Phải chọn và **nói rõ một** trong hai đường: (a) cài nhị phân vào
`node_modules/playwright-core/.local-browsers` đúng như `chay.sh` ghim; hoặc (b) cho `chay.sh` **dự
phòng** sang đường nhị phân đã ghim ở `BAN_GIAO.md` §1 khi thư mục trong repo vắng. Đường nào cũng
phải để lại **mã thoát thật + số ca thật** của `sh thu_giao_dien/chay.sh`, **không** phải của một
driver tự viết.

### 5.7 **MỘT LỖI CỦA CHÍNH TÔI** — ghi lại vì nó dạy đúng một điều

| Lỗi | Triệu chứng | Nguyên nhân thật | Đã sửa |
|---|---|---|---|
| **Tôi tự làm bẩn phép đo C3** | Lượt `gop` đầu cho `skipped=3`, và `test_c2` của bộ G20 in *"phiên này KHÔNG đặt `GIT_CONFIG_COUNT`"* — trong khi §1.3 vừa đo được `GIT_CONFIG_COUNT=2` | Tôi gõ `unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1` **trong cùng một phiên shell** rồi mới chạy bộ kiểm, để `git status` chạy được. Con sinh ra **không còn** thấy dị dạng ⇒ cổng C3 được đo trên **một môi trường khác** môi trường thật | Chạy lại **nguyên môi trường** (`KEY=0 VALUE=2`), ghi lại vào §3 (`failures=6, skipped=2`). **Lượt `gop` bị bẩn vẫn được giữ trong log** (`g20_gop_tren_a3400a8.txt`) để đối chiếu |

> **Bài học, cùng loại với `QA_G20.md` §4.4:** một phép đo có thể **đúng chương trình** mà **sai môi
> trường**, và khi đó nó **im lặng** cho ra một con số khác. Thứ duy nhất bắt được là **in ra môi
> trường ngay trong lượt đo** — bộ kiểm của tôi in `GIT_CONFIG_COUNT/KEY_*/VALUE_*` ở `G2` và đòi
> `GIT_CONFIG_KEY_0` trong thông điệp lỗi.

---

## 6. CHƯA ĐO — **LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT**

| # | Mục | Vì sao chưa đo | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Gọi API hãng thật, kể cả sandbox** | `V-G09-01` + `V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM**. Mọi phép đo HTTP của tôi chỉ chạm `127.0.0.1` (cổng OS cấp); `Z3` tự soi chính bộ kiểm | anh Thành cấp quyền |
| 2 | **C1..C5 sau khi năm làn sửa gộp** | Nền `a3400a8` **chưa có** bản sửa. Đây là **số "TRƯỚC"**; số "SAU" thuộc **lượt 2** | Dispatch nghiệm thu G21 (đã báo trước) |
| 3 | **`C4` ở trạng thái ĐÓNG** | **Không làn nào sở hữu** (`N-G21-02`). Không ai làm thì không có gì để đo | AG-00 mở làn mới |
| 4 | **3 ca tầng 3 KHÔNG HỀ CHẠY** (05 Đăng xuất · 06 TỰ KIỂM gỡ `ban_phim.js` · 07 bố cục hẹp) | Bị ca 04 chặn (`N-G20-03`). **Chúng KHÔNG được tính là đạt** | đóng `G3` ⇒ chúng tự chạy |
| 5 | **Toàn bộ 7 đặc tả qua `sh thu_giao_dien/chay.sh`** | Chạy được **bằng driver của tôi** (51 ca — §4.2), nhưng **KHÔNG** qua `chay.sh` được, vì thiếu nhị phân (`N-G21-04`) | AG-06 (a) hoặc (b) ở §5.5 |
| 6 | **Menu NỀN TẢNG (`MAN_PLATFORM`), bẫy tiêu điểm trong hộp thoại, bảng bên trong màn** | Ca 04 chỉ đo màn **Đơn hàng** với **30** lượt Tab; các màn khác **CHƯA ĐO** | lượt 2 (mở rộng ca) |
| 7 | **Hai đầu vào độc hại của K-3/K-4** (`khoi_phuc()` **3 lượt cùng giây**; **schema v6 đè v9**) | `G4` đo **4** đầu vào (0 byte · cắt 40% · hỏng magic · PGDMP). K-3/K-4 **không** nằm trong 4 đầu vào đó | lượt 2, hoặc bộ của làn AG-02 |
| 8 | **Credential NGẮN của hãng THỨ HAI THẬT** | Hãng thứ hai **chưa có** credential/endpoint (`R-6`, CHƯA CẤP). `G5` đo bằng **tên trường giả** trên stub | anh Thành cấp |
| 9 | **21 mã trạng thái VTP** | Lượt này **không** đo. Dấu hiệu lạ giữ nguyên từ G20: `BANG["vtp"]` khoá **hỗn hợp `int` + `str`** | làn VTP + lượt 2 |
| 10 | **Hành vi ĐA TIẾN TRÌNH dưới tải lớn** (ngoài trần tần suất) | Bộ riêng `app/thu/dong_thoi/chay.py`; lượt này **không** chạy lại | giữ nguyên phạm vi G18 |
| 11 | **PostgreSQL production (D-8)** | **BỊ CẤM chuyển** — CSDL nghiệp vụ vẫn SQLite (`A3`: **0/33** tệp `app/*.py` import driver PostgreSQL). Cụm `:5432` **CHẶN CỨNG** (`A4` **chỉ đọc** `lsof`) | quyết định của anh Thành |
| 12 | **Deploy / push / tunnel / VPS / TLS thật** | **BỊ CẤM** | — |
| 13 | **Safari · Firefox · trình đọc màn hình · cảm ứng thật · in PDF thật · dữ liệu lớn · credentials thật** | Ngoài phạm vi theo thiết kế (`chay.sh` tự khai) | — |
| 14 | **Chốt `D-9` (`city`/`area`)** | Lượt này **không** đo ánh xạ `area` ngoài mock — **giữ nguyên chốt cứng** | làn có quyền sửa ánh xạ |
| 15 | **Bản sao thứ TƯ (dormant) của khoản nợ "cây sạch": `thu_qa_g19.py`** | Nó tự BỎ QUA khi HEAD ≠ `6e61fc1` ⇒ **0 ca chạy**, không đo được trên cây đã gộp. Nó chỉ đỏ khi ai đó chạy `VIP_G19_HEAD=<HEAD>` (`G20_BAOMAT.md` §3.1) | làn AG-05 (sửa luôn) hoặc lượt 2 với `VIP_G19_HEAD` |
| 16 | **Hồi quy toàn phần SAU khi năm làn sửa gộp** | Số `H1` hôm nay (`1894 ca · 52 bộ · 3 bộ hỏng`, §1.4) là số **TRƯỚC**. Số **SAU** phải cho **bộ hỏng ít hơn** và vẫn **0 bộ đỏ vô danh** | lượt 2 |

**Ngoài phạm vi đã đo — nói thẳng:** tôi **không** sửa `app/migrate.py`, `app/quan_sat.py`,
`app/gioi_han.py`, `app/truy_van.py`, `thu_qa_g17.py`, `thu_qa_g18.py` hay bất kỳ tệp nào của làn
khác. `G1`–`G8` là **phép đo**, không phải yêu cầu sửa. Bộ kiểm của tôi **không thay thế** nghiệm thu
của từng làn trên làn của họ; nó là **cổng đối chiếu độc lập** trên **bản đã gộp**.

---

## 7. TUÂN THỦ TUYỆT ĐỐI — tự kiểm **bằng máy**, không bằng lời

| # | Điều bị cấm | Cách tôi tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng **kể cả sandbox** | `Z3`: quét chính tệp bộ kiểm, **0** URL ngoài `127.0.0.1`. Mọi HTTP là **stub/máy chủ của tôi** trên `127.0.0.1` cổng OS cấp | ✓ |
| 2 | Push / deploy / tunnel / **mở cổng ra ngoài** | **Không một lệnh** `git push`/`ssh`/tunnel nào. `do_tang_3()` **ÉP `VIP_HUB_BIND=127.0.0.1`** (không trông cậy giá trị mặc định); **`Z3` khẳng định chính dòng mã đó có mặt** | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; sửa `app/cau_hinh.py` | `A2`: **0** adapter `CHO_PHEP_LIVE=True`, và bộ dò **BẮT** được adapter giả MỞ LIVE ⇒ có răng | ✓ |
| 4 | Credentials thật · `.env` · in bí mật | **Không đọc `.env`**; canary của `G5` là **chuỗi tự đặt** (`A1b2C`, `K7x…`), không phải bí mật thật; CSDL/log nằm trong thư mục tạm | ✓ |
| 5 | **Không đoán mã trạng thái chưa hãng xác minh** (D-4) | Lượt này **không** chạm bảng ánh xạ trạng thái; `G8` chỉ **đếm** tệp import | ✓ |
| 6 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area`; xem §6 mục 14 | ✓ |
| 7 | **Không chuyển CSDL nghiệp vụ sang PostgreSQL** (D-8) | `A3`: **0/33** tệp `app/*.py` import `psycopg`/`psycopg2`/`asyncpg`/`pg8000`; `A4` **chỉ đọc** `lsof` trên `:5432`, **không** kết nối, cụm `:5432` **không đổi** | ✓ |
| 8 | Không dùng mô hình khác · không tự bấm duyệt sandbox | Không một lời gọi mô hình nào; không thao tác duyệt nào | ✓ |
| 9 | Không xoá hàng loạt · không sửa ngoài phạm vi | `git diff --stat` + `git diff --cached --stat` **RỖNG**; `git status --porcelain -uall` **đúng hai** tệp AG-01 G21; `Z2` vân tay cây **TRƯỚC = SAU = `de394bac183005da…`**, `git status` ngoài hai tệp **RỖNG** | ✓ |
| 10 | Tệp chép **tạm** của bàn đo G20 | Chép **đúng** `sha256 5a4b3c83…` để đo (§3), rồi **XOÁ**; đã xác nhận `ls` → *No such file or directory* và `git status` sạch trước khi kết thúc | ✓ |

---

## 8. KẾ HOẠCH LƯỢT 2 — NGHIỆM THU BẢN ĐÃ GỘP G21

1. `git merge-base --is-ancestor a3400a8 HEAD` + vân tay cây **TRƯỚC mọi lượt chạy** (`A1`, `Z2`).
2. `VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py` — **tám cổng phải chuyển ĐỎ → XANH**:
   - **G1** `3/3` cổng cây sạch XANH — **cả BA bản sao** (`thu_qa_g17.py`, `thu_qa_g18.py`,
     `thu_g20_baomat.py`), miễn trừ **theo QUY TẮC**, không theo tên cứng;
   - **G2** `git` môi trường nguyên bản thoát **0** *(và làn phải nêu **cơ chế** — §2.6)*;
   - **G3** tầng 3 `(7, 0, 0)` — ca 04 vào được **> 10** điều khiển, và **ca 05/06/07 phải CHẠY**;
   - **G4** **0/4** đầu vào độc hại được nhận, **và** tệp LÀNH vẫn nhận + dữ liệu nguyên vẹn;
   - **G5** **0/5** tổ hợp rò, **và** hai tổ hợp DÀI + `privateKey`+NGẮN vẫn không rò (phép đo không mù);
   - **G6** `chay_harness.sh` thoát **0**;
   - **G7** **≥ 1** bộ `thu_qa_g19*.py` chạy thật;
   - **G8** `(True, True)` — **cổng này chỉ xanh nếu có làn mới**; nếu không, **G21 = FAILED** (§5.3).
3. `VIP_G21_DAY_DU=1 python3 app/thu/thu_qa_g21.py` — `H1` phải **phân loại được MỌI bộ đỏ**, số ca
   **≥ 1870**, số bộ **≥ 51**. **Bộ đỏ VÔ DANH ⇒ HỎNG SẢN PHẨM ⇒ `H1` ĐỎ.**
4. `python3 app/thu/thu_qa_g21.py` (làn mặc định) — **phải XANH**; nếu không, chính bộ kiểm tôi hỏng.
5. **Đối chiếu chéo** với báo cáo của năm làn: mỗi con số của họ phải có một con số của tôi khớp
   **hoặc** một lý do lệch được nêu.
6. **Kiểm ba chỗ đã cảnh báo:** `N-G21-01` (ca E3 phải được viết lại theo bất biến đúng, **không** nới
   điều kiện), `N-G21-03` (`test_c2a` phải được viết lại theo bất biến đúng), `N-G21-04` (đường nhị
   phân của `chay.sh`).
7. **Nếu `thu_qa_g20.py` được AG-00 commit vĩnh viễn vào cây:** `X1` sẽ tự chạy lại nó. **`L-G20-A`
   phải được sửa trước** (bỏ ghim `HEAD_NEN` ở dòng 520), nếu không nó sẽ ĐỎ **vì lý do giả** và làm
   nhiễu phán quyết.
8. Cập nhật **§6 CHƯA ĐO** — mục nào đóng được thì đóng, mục nào còn thì **vẫn nói thẳng**.
9. **Nếu một khoản nợ chưa gộp: cổng tương ứng ĐỎ, và tôi KHÔNG hạ cổng xuống cho vừa.**
