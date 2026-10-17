# G22 — BỘ ĐO NGHIỆM THU TRÊN **BẢN SAO SẠCH** (AG-05 · CLEAN ACCEPTANCE)

> **Vai:** AG-05 — CLEAN ACCEPTANCE · **Task:** `task_62962cac2292` · **Dispatch:** `ctx_8e6240960131`
> **Nền đo:** `integration/g20 @ a76ec51` (`a76ec51c9931b62451721302446d7c3b74b9c81f`, tree
> `4676e5c53288e21e7c1a87e6bdde9a12c295a147`). **KHÔNG** dùng `main` (`de740dc`) — `main` không chứa G13–G22.
> **Phạm vi ghi của làn này:** `trien_khai/g22-acceptance/*` (mới) · `docs/G22_ACCEPTANCE_HARNESS.md`
> (tệp này). **KHÔNG** sửa `app/thu/thu_qa_g22.py`, **KHÔNG** sửa mã sản phẩm, **KHÔNG** sửa
> `docs/QA_G22.md` (Controller cập nhật sau khi tích hợp).
>
> **ĐÂY LÀ DỤNG CỤ ĐO, KHÔNG PHẢI LỜI TUYÊN BỐ ĐẠT.** Bộ đo **không** có quyền kết luận sản phẩm
> PASS/FAIL; nó chạy bộ kiểm G22 trên một **bản sao sạch** và trên **worktree**, rồi in bảng đối
> chiếu kèm mọi số đo, log, mã thoát. Phán quyết sản phẩm nằm ở log của bộ kiểm và ở người đọc.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

| Câu hỏi | Trả lời ĐO ĐƯỢC |
|---|---|
| Bản sao sạch dựng bằng gì? | `git clone --shared --no-checkout` + `checkout --detach <commit>` (mặc định) — **không ghi `.git` của worktree chính**; chế độ `archive` (`git archive`) chỉ dùng khi cần NỘI DUNG |
| Bộ kiểm G22 chạy ở đâu? | **HAI nơi:** worktree và bản sao sạch; cùng một bộ kiểm, cùng một commit, cùng cây phụ thuộc |
| Thu được gì? | lệnh thật · mã thoát thật (đọc ngay sau lệnh) · `Ran N` · PASS · FAIL · ERROR · SKIP · từng ca · từng dòng đo · **đường dẫn log + sha256** |
| Có dùng cache không? | **KHÔNG.** Mỗi lượt: thư mục `ket_qua/<run-id-UUID>`, `VIP_G22_LOG` mới, `TMPDIR` mới, `PYTHONDONTWRITEBYTECODE=1`, **không** bật `VIP_G22_DAY_DU`; script **từ chối** chạy nếu thư mục log/tmp đã tồn tại (§6) |
| Hai bên có khớp? | **Lượt `full-05`: KHÔNG khớp ở 2 ca + 2 dòng đo**, và **chưa đủ điều kiện so sánh** vì worktree còn tệp chưa commit. Chi tiết ở §7 — **không** có kết luận PASS |
| Mã thoát của bộ đo? | **1** = "có lệch hoặc chưa đủ điều kiện"; **0** chỉ khi hai bên khớp **và** đủ điều kiện; **2** = bộ đo không chạy được. Mã 0 **không** phải "sản phẩm ĐẠT" |
| Cái gì KHÔNG đo được? | §8 — nói thẳng, **không** cộng vào cột xanh |

---

## 1. VÌ SAO PHẢI CÓ "BẢN SAO SẠCH" — ĐO, KHÔNG KỂ

### 1.1 Worktree KHÔNG đo được cổng "cây chỉ mục"

Trên máy này, sandbox chặn ghi `.git` của worktree. Đo trong chính lượt này:

```sh
$ git write-tree
fatal: Unable to create '…/.git/worktrees/g22-a5-acceptance/index.lock': Operation not permitted
# === EXIT CODE THAT = 128
```

Hệ quả: trong worktree, `[A1]` (cây chỉ mục == cây nền) **không thể đọc**; nó in
`write-tree=LỖI(rc=128)`. Không được lấy một cổng "cây sạch" đo trong worktree bị chặn làm bằng
chứng — đó là **ĐỎ GIẢ của môi trường**, đúng loại lỗi `L-G22-B` mà `docs/QA_G22.md` §1.2 đã ghi.

### 1.2 Cách đúng: một kho BÌNH THƯỜNG

`git clone --shared` dựng một kho **thật**, có `.git` ghi được, `HEAD` đặt đúng commit. Trong đó
`git write-tree`/`git status` chạy đúng. Đo được ở lượt `full-05`:

```sh
$ git clone --shared --no-checkout --quiet <worktree> /tmp/veh_g22_nghiem_thu/<lượt>/ban_sao
# === EXIT CODE THAT = 0
$ git -C <bản sao> checkout --detach --quiet a76ec51c9931b62451721302446d7c3b74b9c81f
# === EXIT CODE THAT = 0
$ git -C <bản sao> rev-parse HEAD   → a76ec51c9931b62451721302446d7c3b74b9c81f  (== commit yêu cầu)
$ git -C <bản sao> write-tree       → 4676e5c53288e21e7c1a87e6bdde9a12c295a147  (== tree của commit)
$ git -C <bản sao> status --porcelain -uall → RỖNG  ⇒ bản sao SẠCH
```

Script **kiểm ba vế trên trước khi đo**; sai một vế là **DỪNG** (mã thoát 2), không đo tiếp trên
một bản sao bẩn/sai commit.

### 1.3 Nhãn không phải thẩm quyền — SHA mới là

Mọi khẳng định trong tài liệu này gắn với **SHA thật** mà script phân giải (`<commit>^{commit}`,
`<commit>^{tree}`), không với tên nhánh. Script in cả ba: `commit yêu cầu`, `commit THẬT`,
`tree của commit`; nếu bản sao không khớp, nó dừng.

---

## 2. TỆP CỦA LÀN NÀY

**sha256 của bộ đo (bản dùng để đo §7):** `d85261ef5e50da2ace93ab8fadfa8fc853953bd6cbba1b4974cfe06acc5df5db`
**sha256 của bộ kiểm G22 (không bị sửa):** `1c5d955fa490d37ef6681d8176a5236d8dffc0414dc17bf450c24fc165c60cf7`

| Tệp | Vai |
|---|---|
| `trien_khai/g22-acceptance/nghiem_thu_ban_sao.py` | **Bộ đo.** Dựng bản sao sạch · chạy bộ kiểm hai bên · thu số · so sánh · in bảng · ghi JSON/log |
| `trien_khai/g22-acceptance/.gitignore` | Không commit `ket_qua/` (bằng chứng đo là **sản phẩm của lượt**, không phải mã nguồn) và `__pycache__/` |
| `docs/G22_ACCEPTANCE_HARNESS.md` | Tài liệu này: cách dùng · tiêu chí · **cái gì không đo được** · bằng chứng lượt chạy thật |
| `trien_khai/g22-acceptance/ket_qua/<run-id>/` | **Sinh ra khi chạy, KHÔNG commit:** log hai bên, `KET_QUA.json`, `BANG_SO_SANH.txt` |

Script **không** chép bộ kiểm vào bản sao; nó chạy chính `app/thu/thu_qa_g22.py` **đã có trong
commit**. Nếu bản sao thiếu tệp đó, phép đo dừng với lỗi rõ ràng.

---

## 3. CÁCH DÙNG

### 3.1 Lượt nghiệm thu đầy đủ (mặc định: chạy CẢ HAI bên, so sánh)

```sh
python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
    --commit a76ec51 \
    --mode clone \
    --nhan <nhãn-của-lượt>
```

Mặc định:
- `--dest` = `/tmp/veh_g22_nghiem_thu/<run-id>/ban_sao` (ngoài cây; không làm bẩn worktree);
- `--kho` = repo chứa script;
- `--che-do gop` = truyền `VIP_G22_CHE_DO=gop` cho bộ kiểm (chế độ nghiệm thu bản đã gộp);
- `--node-modules` = `node_modules` của worktree nguồn, **symlink** vào bản sao để **hai bên dùng
  CÙNG một cây phụ thuộc**;
- `--timeout-giay 2700` cho **mỗi bên**.

### 3.2 Chỉ định thư mục đích (bắt buộc khi cần giữ bản sao ở chỗ khác)

```sh
python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
    --commit a76ec51 \
    --dest /tmp/veh_g22_nt/ban_sao_a76ec51 \
    --mode clone
```

`--dest` **đã tồn tại ⇒ từ chối**, không ghi đè, không xoá. Muốn đo lại thì dùng thư mục mới.

### 3.3 Chế độ `archive` (chỉ nội dung, KHÔNG có `.git`)

```sh
python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py --commit a76ec51 --mode archive
```

`git archive --format=tar -o <tar> <sha>` rồi giải nén. Bản sao **không có `.git`** ⇒ mọi cổng
git (`A1`, `A2`, `E1`, `E2`, `D1` phần git) **không đo được**. Chế độ này chỉ dùng để kiểm **nội
dung** (tệp có mặt, sha, chạy được Python…). **Không dùng cho nghiệm thu G22.**

### 3.4 Hai cờ CHẨN ĐOÁN (không dùng cho nghiệm thu)

| Cờ | Việc | Cảnh báo |
|---|---|---|
| `--chi-mot-ben` | Chỉ chạy bên bản sao, không chạy worktree/không so sánh | Mã thoát 0 chỉ nói "phép đo chạy xong"; **không** phải nghiệm thu |
| `--doi-so-them …` | Truyền đối số lọc ca cho bộ kiểm (vd `A_Nen`) | Chỉ đo một phần; **không** dùng cho nghiệm thu cuối |

### 3.5 Bảng tham số

| Tham số | Mặc định | Nghĩa |
|---|---|---|
| `--commit` | `HEAD` | commit/nhãn cần đo; script luôn in **SHA thật** đã phân giải |
| `--dest` | `/tmp/veh_g22_nghiem_thu/<run-id>/ban_sao` | thư mục đích của bản sao sạch (phải chưa tồn tại) |
| `--mode` | `clone` | `clone` = `git clone --shared` + `checkout --detach`; `archive` = `git archive` |
| `--kho` | repo chứa script | kho nguồn |
| `--che-do` | `gop` | `VIP_G22_CHE_DO` truyền cho bộ kiểm (`nen`/`gop`) |
| `--node-modules` | `<worktree>/node_modules` | cây phụ thuộc cấp cho bản sao (symlink); hai bên dùng chung |
| `--khong-lien-ket-node-modules` | tắt | không symlink (e2e sẽ không chạy được — có ghi) |
| `--timeout-giay` | `2700` | hết giờ cho **mỗi bên**; hết giờ ⇒ mã 2, không giả rc=0 |
| `--nhan` | rỗng | nhãn ngắn ghi vào tên thư mục lượt |
| `--json` | `<lượt>/KET_QUA.json` | đường dẫn JSON kết quả |

### 3.6 Mã thoát của BỘ ĐO (khác mã thoát của BỘ KIỂM)

| Mã | Nghĩa |
|---|---|
| **0** | Đo xong; **hai bên khớp nhau ở mọi chỉ tiêu** và **đủ điều kiện so sánh**. **KHÔNG** có nghĩa sản phẩm ĐẠT — bộ kiểm vẫn có thể ĐỎ |
| **1** | Đo xong; **có lệch** HOẶC **chưa đủ điều kiện so sánh** (worktree bẩn, khác bộ kiểm, khác deps) |
| **2** | Bộ đo **không chạy được**: dựng bản sao hỏng, bộ kiểm không in `Ran N`, hết giờ… |

Trong bảng in ra, **mã thoát của bộ kiểm G22** được ghi riêng. Bộ đo **không** sửa, không nuốt,
không diễn giải lại mã đó.

---

## 4. ĐO CÁI GÌ — VÀ TIÊU CHÍ

### 4.1 Mỗi bên, bộ đo thu:

| # | Số đo | Cách lấy | Ghi chú |
|---|---|---|---|
| 1 | **Lệnh thật** | `argv` + biến môi trường đã đặt, in trong log | không dùng `shell=True`; không qua ống |
| 2 | **Mã thoát thật** | `CompletedProcess.returncode`, đọc **ngay sau lệnh** | hết giờ ⇒ `None` + cờ `het_gio`, không giả 0 |
| 3 | **`Ran N`** | dòng `^Ran N tests? in Xs` **cuối cùng** của bộ **CHÍNH** | output của bộ con bị lọc (§4.3) |
| 4 | **PASS** | `Ran − failures − errors − skipped` | `unittest` **không** in dòng PASS; nếu đếm từng ca lệch tổng kết ⇒ **cảnh báo**, không che |
| 5 | **FAIL / ERROR / SKIP** | dòng tổng kết + đếm từng ca | hai nguồn phải khớp; lệch ⇒ cảnh báo |
| 6 | **Từng ca** | `unittest -v`: `test_x (__main__.Lớp) ... ok/FAIL/ERROR/skipped` | hỗ trợ cả dạng trạng thái in **thành dòng riêng** sau output của ca |
| 7 | **Từng dòng đo** | các dòng `[A1]`, `[B2]`, `[D1]`… của bộ kiểm | dùng để so sánh **giá trị** đo, không chỉ trạng thái ca |
| 8 | **Bộ kiểm tự báo** | dòng `ca: N · hỏng/loi: … · bỏ qua: … · MÃ THOÁT = …` | đối chiếu với `Ran`/mã thoát ta đọc; lệch ⇒ cảnh báo |
| 9 | **Log** | `chay_<bên>.log` + `sha256` + bytes + mtime | log thô nằm trong thư mục lượt |
| 10 | **Vân tay cây** | sha256 nội dung **mọi tệp theo dõi** trước/sau lượt | chứng minh bộ kiểm không để lại thay đổi |
| 11 | **Bộ kiểm có bị đổi?** | sha256 6 tệp quyết định trước/sau | chứng minh **không sửa test** |
| 12 | **`.git` nguồn có bị ghi?** | mtime/size/sha256 của `.git/index`, `.git/HEAD` trước/sau | chứng minh **không ghi `.git`** |

### 4.2 Tiêu chí "hai bên khớp"

Hai bên khớp **chỉ khi TẤT CẢ** các mục sau bằng nhau:

1. mã thoát bộ kiểm;
2. `Ran N`, PASS, FAIL, ERROR, SKIP;
3. **tập ca** và **trạng thái từng ca**;
4. **từng dòng đo** (sau khi bỏ khác biệt *không mang nghĩa sản phẩm*: đường dẫn cây, thư mục
   log, cổng `127.0.0.1:<port>`, PID, số giây, mốc thời gian);
5. dòng **bộ kiểm tự báo** (`ca`/`hỏng-lỗi`/`bỏ qua`/`MÃ THOÁT`).

Khác một mục ⇒ **in rõ lệch ở đâu** (bảng ca + bảng dòng đo), **không** làm tròn, **không** bỏ qua.

### 4.3 Bộ đọc phải lọc output của BỘ CON — bài học ĐO ĐƯỢC

Bộ kiểm G22 chạy các bộ khác trong tiến trình con (`E2` chạy `thu_qa_g19.py`, `D1` chạy
`thu_qa_g20.py`, `G1` chạy `thu_g20_dahang.py`, `I1` chạy các cổng trên cây gương, `Z5` chạy lại
chính bộ kiểm). Lượt chạy đầu của script này đã **đọc nhầm** `Ran 29` của bộ con (nằm trong thông
điệp lỗi của `E2`) làm `Ran` của bộ chính ⇒ bảng so sánh **sai** (`29` vs `24`). Đã sửa bằng hai
việc **đo được**, không bằng nới điều kiện:

1. Lấy dòng `Ran` **cuối cùng** trong log (dòng của bộ chính);
2. Lọc ca/nhãn theo **chính tệp `app/thu/thu_qa_g22.py`** của bên đang đo (`class …(unittest.TestCase)`
   + `def test_…`), nên ca của bộ con không lọt vào.

Sau khi sửa, cả hai bên đọc ra **`Ran 24`**, và đếm từng ca **khớp** tổng kết; không còn cảnh báo.

---

## 5. HAI BÊN CÓ THỰC SỰ SO SÁNH ĐƯỢC KHÔNG?

Bộ đo in mục **"ĐIỀU KIỆN SO SÁNH"** với hai danh sách **tách rời** (gộp chúng là tự lừa mình):

| Danh sách | Nghĩa | Ví dụ đo được |
|---|---|---|
| **KHÔNG SO SÁNH ĐƯỢC** | Hai bên khác điều kiện đo ⇒ bảng chỉ là **đối chiếu thô** | worktree còn tệp chưa commit; hai bên khác bộ kiểm; khác `node_modules` |
| **GIỚI HẠN PHÉP ĐO** | Phép đo **không phủ tới** một vùng ⇒ vùng đó **không được cộng vào cột "khớp"** | thiếu Chromium trong `node_modules`; worktree `git write-tree` rc=128 |

Danh sách **KHÔNG SO SÁNH ĐƯỢC** phải **RỖNG** thì mới có "đủ điều kiện". Điều kiện tối thiểu:

- worktree **sạch** (`git status --porcelain -uall` rỗng) **và** bản sao sạch;
- hai bên **cùng commit** (HEAD = commit yêu cầu);
- sáu tệp quyết định của bộ kiểm **cùng sha256**;
- hai bên dùng **cùng** một cây `node_modules` (symlink về một chỗ).

Nếu thiếu, script in thẳng: *"HAI BÊN KHÔNG CÙNG ĐIỀU KIỆN ĐO: bảng trên là ĐỐI CHIẾU THÔ,
KHÔNG phải nghiệm thu"*, kèm việc cần làm (commit trước rồi chạy lại).

> **Hệ quả trung thực:** trên máy này, worktree bị sandbox chặn `git write-tree`, nên **dòng đo
> `[A1]` của worktree luôn khác bản sao** (một bên `LỖI(rc=128)`, một bên là tree thật). Vì vậy
> **mã thoát 0 khó đạt** ngay cả sau khi commit. Đó **không** phải lỗi của script và **không** nên
> "chữa" bằng cách nới điều kiện; nó là giới hạn môi trường đã đo, được ghi thành mục riêng. Mọi
> kết luận về `A1` phải lấy từ **bản sao sạch**, nơi `write-tree` chạy được.

---

## 6. KHÔNG DÙNG KẾT QUẢ CACHE — CÁCH XÁC NHẬN (ĐO, KHÔNG KHAI)

### 6.1 Cơ chế

1. **Thư mục lượt mới**: `ket_qua/<YYYYmmdd-HHMMSS>-<uuid6>[-nhãn]`, tạo bằng
   `os.makedirs(..., exist_ok=False)` — trùng tên là **lỗi**, không dùng lại.
2. **`VIP_G22_LOG` mới cho từng bên** (`log_worktree`, `log_ban_sao`); trước khi chạy phải **RỖNG**;
   script **từ chối** nếu đã tồn tại.
3. **`TMPDIR` mới cho từng bên**, nằm ở `/tmp/veh-g22-nt-<lượt>-<bên>` (đường dẫn ngắn, tránh giới
   hạn `AF_UNIX`); trước khi chạy phải **RỖNG**.
4. **`PYTHONDONTWRITEBYTECODE=1`** — không sinh/đọc `.pyc`; script đếm `.pyc` **mới sinh** (phải 0).
5. **`VIP_G22_DAY_DU` KHÔNG bật** — không đọc lại log `chay_tat_ca.sh` của lượt trước.
6. **Không chép tệp kết quả nào vào**; mỗi bên chạy lại bộ kiểm từ đầu.
7. Script ghi lại **mtime + sha256** của từng tệp log mới và kiểm chúng **≥ thời điểm bắt đầu lượt**.

### 6.2 Bằng chứng của lượt `full-05`

```
[worktree]
  thư mục VIP_G22_LOG trước lượt : 0 đường (BẮT BUỘC rỗng)
  thư mục TMPDIR trước lượt      : 0 đường (BẮT BUỘC rỗng)
  tệp LOG sinh trong lượt         : 4 · tệp TMPDIR: 718
  MỌI tệp LOG mới (mtime ≥ bắt đầu): True
  tệp TMP giữ mtime cũ (copy2)    : 119 (KHÔNG phải cache — xem tài liệu §6)
  .pyc mới sinh                  : KHÔNG
  PYTHONDONTWRITEBYTECODE         : 1
  VIP_G22_DAY_DU                  : KHÔNG bật (không đọc lại log `chay_tat_ca.sh`)
  sha256 log của lượt             : 311f86c6c65cee2ea8b566b51bd97db934356e291a26abbacc30ae3f6b452af3

[bản sao]
  thư mục VIP_G22_LOG trước lượt : 0 đường (BẮT BUỘC rỗng)
  thư mục TMPDIR trước lượt      : 0 đường (BẮT BUỘC rỗng)
  tệp LOG sinh trong lượt         : 4 · tệp TMPDIR: 718
  MỌI tệp LOG mới (mtime ≥ bắt đầu): True
  tệp TMP giữ mtime cũ (copy2)    : 119 (KHÔNG phải cache — xem tài liệu §6)
  .pyc mới sinh                  : KHÔNG
  PYTHONDONTWRITEBYTECODE         : 1
  VIP_G22_DAY_DU                  : KHÔNG bật (không đọc lại log `chay_tat_ca.sh`)
  sha256 log của lượt             : c42760782e3a57521600abcde5d00597e65f77d913be9e1cd37a0816c027ac9e
```

**119 tệp TMP mang mtime CŨ — vì sao đây KHÔNG phải cache:** vài bộ thử **chép** mã nguồn vào nền
tạm bằng `shutil.copy2`, nên mtime **được giữ nguyên**. Bằng chứng không-cache không nằm ở mtime
của tệp được chép, mà ở chỗ: **thư mục TMPDIR là MỚI và RỖNG trước lượt**, và **mọi tệp LOG do bộ
kiểm sinh ra đều mới**. Script ghi **cả hai** con số để người đọc tự kiểm, không giấu.

**Cách tự kiểm lại một lượt:**

```sh
# 1) thư mục lượt phải là duy nhất, không có tệp của lượt trước
ls trien_khai/g22-acceptance/ket_qua/<run-id>/
# 2) log ghi mốc bắt đầu/kết thúc + mã thoát THẬT
head -12 trien_khai/g22-acceptance/ket_qua/<run-id>/chay_worktree.log
tail -6  trien_khai/g22-acceptance/ket_qua/<run-id>/chay_worktree.log
# 3) mtime tệp log >= mốc bắt đầu trong header (script tự kiểm; xem KET_QUA.json → khong_cache)
# 4) không có .pyc mới
find app -name '*.pyc' -newer trien_khai/g22-acceptance/ket_qua/<run-id>/chay_worktree.log | wc -l
```

---

## 7. BẰNG CHỨNG LƯỢT CHẠY THẬT

### 7.1 Lệnh và mã thoát

```sh
$ cd /Users/viporder/orca/workspaces/vip-express-hub/g22-a5-acceptance
$ python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
      --commit a76ec51 --mode clone --nhan full-05
# === EXIT CODE THAT = 1   (bộ đo: có lệch / chưa đủ điều kiện; KHÔNG phải phán quyết sản phẩm)
```

Lượt này chạy **43.12 giây** (`2026-10-17T16:05:24Z → 16:06:07Z`); `run-id = 20261017-230524-1f10a3-full-05`.

### 7.2 Bảng số đo hai bên

| Chỉ tiêu | worktree | bản sao sạch | khớp |
|---|---|---|---|
| cwd | `…/g22-a5-acceptance` | `/tmp/veh_g22_nghiem_thu/<lượt>/ban_sao` | khác (đúng thiết kế) |
| lệnh | `VIP_G22_CHE_DO=gop … python3 app/thu/thu_qa_g22.py` | như trên | **CÓ** |
| **mã thoát bộ kiểm** | **1** | **1** | **CÓ** |
| **`Ran N`** | **24** | **24** | **CÓ** |
| **PASS** | **12** | **14** | **KHÔNG** |
| **FAIL** | **9** | **7** | **KHÔNG** |
| **ERROR** | **1** | **1** | **CÓ** |
| **SKIP** | **2** | **2** | **CÓ** |
| bộ kiểm tự báo | `ca 24 · hỏng/loi 10 · bỏ qua 2 · mã thoát 1` | `ca 24 · hỏng/loi 8 · bỏ qua 2 · mã thoát 1` | **KHÔNG** |
| log | `ket_qua/<lượt>/chay_worktree.log` (29 139 B) | `ket_qua/<lượt>/chay_ban_sao.log` (26 882 B) | — |
| sha256 log | `311f86c6c65cee2e…52af3` | `c42760782e3a5752…27ac9` | — |

**PASS không phải dòng của `unittest`** — nó được tính `Ran − failures − errors − skipped`; đếm
từng ca khớp đúng tổng kết ở **cả hai bên** (không có cảnh báo).

### 7.3 Lệch ở đâu — in nguyên văn từ bảng của script

**Hai ca lệch:**

| ca | worktree | bản sao |
|---|---|---|
| `A_Nen.test_a2_khong_sua_ma_san_pham` | **FAIL** | **PASS** |
| `E_CaySach.test_e2_ban_sao_thu_tu_dormant_nam_o_dau` | **FAIL** | **PASS** |

**Hai dòng đo lệch:**

```
[A1] worktree : write-tree=LỖI(rc=128)  · băm danh sách=9d4e1abd658b4927
     bản sao  : write-tree=4676e5c53288 · băm danh sách=9d4e1abd658b4927
[A2] worktree : status 3 đường  = 0 tệp được phép + 0 delta + 3 NGOÀI phép
     bản sao  : status 0 đường  = 0 tệp được phép + 0 delta + 0 NGOÀI phép
```

**Nguyên nhân ĐO ĐƯỢC của từng lệch (không suy diễn):**

1. **`A2` + `E2` ở worktree:** worktree còn **3 tệp chưa commit** của làn này
   (`.gitignore`, `nghiem_thu_ban_sao.py`, `docs/G22_ACCEPTANCE_HARNESS.md`); `A2` gọi đúng 3 đường đó là "NGOÀI phép". `E2` chạy
   `thu_qa_g19.py`; trên worktree bẩn bộ đó trả **rc=1** (cổng cây sạch của nó thấy 3 đường), nên
   `E2` FAIL; trên bản sao sạch bộ đó trả **rc=0**, `E2` PASS. **Không phải hồi quy sản phẩm** —
   commit các tệp của làn là hết.
2. **`A1`:** worktree bị sandbox chặn `git write-tree` (rc=128); bản sao đọc được nhưng tree
   `4676e5c…` **≠** `TREE_NEN` mà bộ kiểm ghim (`37079aa8…`) ⇒ `A1` **FAIL ở cả hai bên**. Đây là
   **ghim nền cũ** trong bộ kiểm (`NEN_SHA=3b7e93b`, trong khi cây tích hợp là `a76ec51`), không
   phải lỗi của bản sao.

### 7.4 Vì sao BỘ KIỂM đỏ trên **bản sao sạch** (7 lỗi + 1 error) — nói thẳng

`Ran 24 · FAILED (failures=7, errors=1, skipped=2)`, mã thoát **1**. Tám ca:

| Ca | Nguyên nhân ĐO ĐƯỢC từ log | Thuộc về |
|---|---|---|
| `A_Nen.test_a1` | `'4676e5c…' != '37079aa8…'` — ghim `NEN_SHA/TREE_NEN` là cây `3b7e93b`, không phải `a76ec51` | **bộ kiểm (AG-01): ghim nền cũ** |
| `C_BanPhim.test_b2` | `(3, 10, 0, 52)` = NỬA VỜI; 52 ca "did not run" vì Chromium không khởi động được | **môi trường: thiếu `.local-browsers`** |
| `C_BanPhim.test_b3` | `(0, 1, 0, 7)`, 0 ca đạt — cùng lý do thiếu nhị phân | **môi trường** |
| `F_DongHo.test_f1/f3` | `KHÔNG ĐO ĐƯỢC E3` / không tìm thấy cách đặt tên bản cất | **bộ kiểm: F group STALE** sau khi `khoi_phuc()` được vá (`docs/QA_G22.md` §10.5 đã cảnh báo) |
| `F_DongHo.test_f2` | **ERROR** `RuntimeError: không vá được khoi_phuc: đoạn gốc không khớp nguyên văn` | **bộ kiểm: F group STALE** |
| `G_NG2103.test_g1` | đối chứng độc lập `G5` báo **0/5 tổ hợp RÒ** ⇒ "bộ đo độc lập mù"; hành vi RÒ đã hết, ca vẫn ghim hành vi cũ | **bộ kiểm: G group STALE** |
| `Z_ChotChan.test_z6` | thiếu đối chứng cho nhóm `cay-sach-3-ban-sao` — vì `E1` **SKIP** (HEAD ≠ ghim nền) | **hệ quả của ghim nền cũ** |

Hai ca bỏ qua: `E1` (bộ kiểm tự từ chối phán quyết vì `HEAD=a76ec51` ≠ `NEN_SHA=3b7e93b` — đúng
thiết kế của nó) và `Z9` (ca mồi cố ý hỏng, chỉ chạy trong tiến trình con của `Z5`).

> **Không kết luận sản phẩm hỏng từ tám ca này.** Chúng là **nợ bộ kiểm + môi trường** đã đo, và
> `docs/QA_G22.md` §10.5 đã ghi trước hai nhóm `F`/`G` là STALE. Việc của AG-01/Controller: cập
> nhật ghim nền và nhóm `F`/`G`, cấp Chromium — **không** phải của bộ đo này. Bộ đo chỉ chịu trách
> nhiệm **chạy đúng lệnh, đọc đúng số, in đúng chỗ lệch**.

### 7.5 Bằng chứng tuân thủ trong chính lượt này

```
cùng commit            : worktree=a76ec51c9931… · bản sao=a76ec51c9931… · yêu cầu=a76ec51c9931…
worktree sạch          : KHÔNG (3 đường chưa commit của làn này)
bản sao sạch           : CÓ (status RỖNG)
cùng bộ kiểm (sha256)  : CÓ  (app/thu/thu_qa_g22.py = 1c5d955fa490d37e…; không đổi trong lượt)
cùng node_modules      : CÓ  (một symlink, cùng cây phụ thuộc)
có .local-browsers     : False  ← giới hạn phép đo (e2e Chromium)
write-tree worktree    : rc=128
bộ kiểm bị đổi giữa lượt: worktree=KHÔNG · bản sao=KHÔNG
cây bị đổi giữa lượt   : worktree=[] · bản sao=[]
nguồn `.git` bị ghi     : KHÔNG (vân tay `.git/index` + `.git/HEAD` trước == sau)
```

Bản sao: `HEAD == commit`, `write-tree == 4676e5c…` (= tree của commit), `status` **RỖNG**, có
`.git` bình thường; bản sao nằm **ngoài cây** (`/tmp/veh_g22_nghiem_thu/<lượt>/ban_sao`), nên nó
không làm bẩn `git status` của worktree.

---

## 8. CÁI GÌ **KHÔNG** ĐO ĐƯỢC — KHÔNG CỘNG VÀO CỘT XANH

| # | Không đo được | Vì sao (đo được) | Ai cần xử |
|---|---|---|---|
| 1 | **Kết luận sản phẩm PASS/FAIL** | Bộ đo chỉ so hai lần chạy; "khớp" không có nghĩa "đúng". Bộ kiểm có thể ĐỎ ở cả hai bên | Người/Controller đọc log |
| 2 | **E2E Chromium (B2/B3)** | `node_modules/playwright-core/.local-browsers` **KHÔNG có**; `chay.sh` ghim `PLAYWRIGHT_BROWSERS_PATH=0`. Đo trên bản sao: `B3 = (0,1,0,7)` (0 đạt), `B2 = (3,10,0,52)` (52 ca *did not run*). Hai bên **cùng thiếu** ⇒ không phân biệt được sản phẩm với môi trường | Controller cấp Chromium (symlink như `docs/QA_G22.md` §4.1) rồi chạy lại |
| 3 | **`[A1]` ở worktree** | `git write-tree` rc=128 (sandbox chặn `index.lock`). Chỉ bản sao đo được | Không cần: dùng bản sao |
| 4 | **`A2`/`E2` khi worktree còn tệp chưa commit** | Chính tệp của làn này làm `status` bẩn ⇒ `A2`/`E2` FAIL ở worktree. **Commit trước** thì hết | Controller commit |
| 5 | **Chế độ `archive`: mọi cổng git** | Bản sao không có `.git` ⇒ `A1/A2/E1/E2` không đo được; chỉ kiểm nội dung | Chỉ dùng `clone` cho nghiệm thu |
| 6 | **CSDL nghiệp vụ trên PostgreSQL (`OWNER_ACTIONS C4` = D-8)** | **BLOCKED OWNER** — bộ đo này **không chạm**: mọi test dùng SQLite/nền tạm; không mở kết nối `:5432` | Owner quyết D-8; **không** ép cổng xanh |
| 7 | **`G19-C6` (route `truy_van` + DDL_G12Q vào migration)** | Là khoản nợ **local** *khác* C4; bộ kiểm chỉ đo `import truy_van` (H1 = 0 tệp sản xuất). Bộ đo G22 không tự sửa test, không tự đóng nợ | AG-02 (làn sở hữu) |
| 8 | **API hãng thật, credentials thật, TLS thật** | `V-G09-01`/`V-13906-05` **CHƯA CẤP** ⇒ **BỊ CẤM**; không có lời gọi ra ngoài | Owner |
| 9 | **Safari/Firefox, trình đọc màn hình, cảm ứng thật, in PDF thật** | ngoài phạm vi `thu_giao_dien/chay.sh` (tự khai) | Owner |
| 10 | **Tính tất định / chập chờn (N-G22-01)** | Bộ đo chạy **mỗi bên MỘT lượt**, **không retry**. Ca chập chờn có thể PASS bên này/FAIL bên kia; bộ đo **in lệch**, không làm mượt. Muốn đo tất định phải chạy lặp **nhiều lượt** và có đối chứng — ngoài phạm vi script này | AG-01/AG-00 |
| 11 | **Nhiều tiến trình / tải / rate limit thật** | mỗi lượt chạy tuần tự, một tiến trình bộ kiểm; không đo song song | ngoài phạm vi G22 local |
| 12 | **Thời gian chạy như một chỉ tiêu** | thời gian được in nhưng **không** so khớp (máy dùng chung, load 9–17) | — |
| 13 | **Kết luận từ một lượt duy nhất** | một lượt chỉ là **một** phép đo; kết luận cần lặp + đối chứng | Controller |

---

## 9. TUÂN THỦ TUYỆT ĐỐI

| # | Điều bị cấm | Cách tự kiểm trong lượt này | Kết quả |
|---|---|---|---|
| 1 | Push GitHub / deploy VPS / API production | Không có lệnh `git push`/`ssh`/deploy/tunnel; bộ kiểm chỉ chạm `127.0.0.1` | ✓ |
| 2 | Tạo đơn vận chuyển thật / sửa dữ liệu thật / xoá database | Không chạm `.env`, không chạm CSDL thật; mọi nền là `mktemp`/`TMPDIR` mới | ✓ |
| 3 | Tự ý merge `main` / lệnh phá dữ liệu | Không merge, không `reset --hard`, không `clean -fd`; script chỉ `clone` + `checkout --detach` vào thư mục **mới**; `--dest` tồn tại thì **từ chối** | ✓ |
| 4 | Sửa mã sản phẩm / sửa test / sửa `docs/QA_G22.md` | Chỉ tạo `trien_khai/g22-acceptance/*` + tệp này; sha256 bộ kiểm trước == sau trong lượt; `git status` chỉ có tệp của làn | ✓ |
| 5 | Ghi `.git` của worktree chính | Chỉ đọc; vân tay `.git/index` + `.git/HEAD` trước == sau; bản sao có `.git` riêng ngoài cây | ✓ |
| 6 | Tự bấm duyệt sandbox / tự vượt chốt | Không thao tác duyệt; chỗ bị chặn (`write-tree` rc=128) được **báo**, không lách | ✓ |
| 7 | Kết luận PASS khi không có log | Không có kết luận PASS; mọi số trong tài liệu gắn với log trong `ket_qua/<lượt>/` | ✓ |

---

## 10. VIỆC CÒN LẠI — CHO CONTROLLER / AG-01 (KHÔNG TỰ VƯỢT PHẠM VI)

1. **Commit ba tệp của làn này** (`nghiem_thu_ban_sao.py`, `.gitignore`, tài liệu này). Khi chưa
   commit: worktree bẩn ⇒ `A2`/`E2` đỏ ở worktree và **chưa đủ điều kiện so sánh**. Thư mục
   `ket_qua/` **đã được `.gitignore`**, nên log bằng chứng không làm bẩn `status`.
2. **Cấp Chromium** cho `node_modules/playwright-core/.local-browsers` (symlink tới
   `chromium-1194`, như `docs/QA_G22.md` §4.1). Không có nó thì `B2`/`B3` **không đo được** — cả
   hai bên cùng đỏ, và bộ đo ghi đúng như vậy.
3. **AG-01 cập nhật bộ kiểm** (ngoài phạm vi ghi của làn này):
   - ghim `NEN_SHA/TREE_NEN` theo cây tích hợp đang đo (`a76ec51` / `4676e5c…`), nếu không `A1`
     đỏ và `E1` bỏ qua ở mọi lượt;
   - nhóm `F` (E3) và `G` (N-G21-03) đã **STALE** từ `bf8696d` — phải cập nhật ca đo, **không**
     nới điều kiện và **không** xoá ca;
   - `Z6` sẽ hết đỏ khi `E1` chạy được (tức khi ghim nền đúng).
4. **Chạy lại sau khi commit** (và sau khi cấp Chromium) — dùng **đúng lệnh §3.1**, đổi `--nhan`.
   Đọc **bảng §1 + §2 + §3**; đừng đọc mã thoát 0/1 như phán quyết sản phẩm.
5. **Quyết định của Owner không bị chạm:** `OWNER_ACTIONS C4` = **D-8, BLOCKED OWNER** —
   **không** thực hiện, **không** ép cổng xanh. `G19-C6` là khoản nợ local **khác**, thuộc AG-02.

---

## 11. CÁCH ĐỌC `KET_QUA.json`

| Khoá | Nội dung |
|---|---|
| `nguon` | kho, HEAD, commit yêu cầu/THẬT, tree, status worktree, vân tay `.git` trước/sau, cờ "không đổi" |
| `ban_sao.tao` / `ban_sao.kiem` | từng lệnh dựng + mã thoát; HEAD/tree/status/số tệp/`node_modules` của bản sao |
| `worktree` / `ban_sao_do` | lệnh, cwd, môi trường, exit, `Ran`, PASS/FAIL/ERROR/SKIP, **từng ca**, **từng dòng đo**, log + sha256, vân tay cây, bộ kiểm trước/sau, `khong_cache` |
| `so_sanh` | `khac` (số), `ca_lech`, `dong_do_lech`, `cung_dieu_kien`, `ly_do` (không so sánh được), `gioi_han_do` (giới hạn phép đo) |
| `ket_luan` | `ma_thoat` của bộ đo + nghĩa; **không** phải phán quyết sản phẩm |

---

## 12. TÁI LẬP NHANH (SMOKE — KHÔNG PHẢI NGHIỆM THU)

```sh
# chỉ bản sao, chỉ 4 ca A_Nen; ~10 giây; chứng minh pipeline chạy thật
python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
    --commit a76ec51 --mode clone --chi-mot-ben --doi-so-them A_Nen
# mã thoát 0 = phép ĐO chạy xong (không phải sản phẩm ĐẠT)

# kiểm chế độ archive (không .git)
python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
    --commit a76ec51 --mode archive --chi-mot-ben --doi-so-them A_Nen
```

Kết quả smoke đã chạy thật được ghi trong log tương ứng ở `ket_qua/<lượt>/`; cả hai pipeline
(`clone`, `archive`) đều chạy và in số, không cần mạng ngoài.
