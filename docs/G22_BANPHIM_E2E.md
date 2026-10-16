# G22 · AG-06 — CỔNG E2E TẦNG 3: **65/65**, VÀ PHÂN BIỆT *"SẢN PHẨM HỎNG"* VỚI *"NỀN CHẾT"*

**Nền đo:** `integration/g20` @ `7344c020abad562dafb593c4234d5e1f9ecfd18c` — đúng cái cây mà điều
phối gọi là *"integration/g21 @ 7344c02"*. Nội dung đã vào cây làm việc và **xác minh bằng sha256
từng tệp** (§1).
**Người làm:** AG-06 · wave G22. **Vùng được ghi:** `admin/ban_phim.js` · `admin/admin.js` ·
`thu_giao_dien/*.spec.js` · `app/thu/thu_g22_e2e.py` (mới) · `docs/G22_BANPHIM_E2E.md` (mới).
**Lượt này KHÔNG sửa một dòng mã sản phẩm nào** — chỉ thêm cổng đo và tài liệu.

**Lệnh dựng lại toàn bộ số trong tài liệu này:**

```sh
python3 app/thu/thu_g22_e2e.py --tu-kiem        # 26 ca tự kiểm của Phần A — Phần B thêm e1–e5 ⇒ 31 ca, exit 0
python3 app/thu/thu_g22_e2e.py --ghim-chromium  # đường dẫn + phiên bản + sha256 binary
python3 app/thu/thu_g22_e2e.py                  # CỔNG ĐẦY ĐỦ: 65 ca, exit 0
sh thu_giao_dien/chay.sh                        # bộ chạy cũ — ĐỌC §3 TRƯỚC KHI TIN
```

---

> **CẬP NHẬT — DISPATCH 2 (17/10/2026): tài liệu này có thêm **PHẦN B** ở CUỐI.**
> Phần B gồm: **vá hai lỗi báo cáo của `chay.sh`** (dòng PHẠM VI + mã thoát nay in trong
> `trap … EXIT`; bộ dọn không còn nói dối về tiến trình đã chết), **bộ đo giới hạn tiến trình**
> (fd · ổ cắm · cổng · con · thời gian sống · tín hiệu làm nó chết) kèm **đối chứng âm + dương
> bắt buộc**, và **7 lượt chạy lại trọn bộ ghi rõ từng lượt**. Đọc Phần B trước khi dùng lại
> những con số ở Phần A: ba lượt đỏ của Phần A nay có **bản sao dấu vết tái lập được** và một
> **phán quyết bằng máy** (`HA_TANG_CHET`, không phải "sản phẩm hỏng").

## 0. BA CÂU — ĐỌC LÀ ĐỦ

1. **Cây này ĐẠT 65/65.** Sáu lượt chạy độc lập cho **65 đạt · 0 hỏng · 0 bỏ qua · 0 không chạy**,
   `exit 0`. Hai ca *"did not run"* của lượt trước (ca 02 và 03 của `08_bang_duong_billing`) nay
   **đã chạy và đã đạt** — vì `admin/billing.js` trên cây đã là bản sửa của AG-00 (`sha256[:8] =
   00e8d4cd`), không còn là bản G19 (`abf62f42`).
2. **`sh thu_giao_dien/chay.sh` KHÔNG tái lập được con số ấy một cách đáng tin.** Ba trong chín
   lượt chạy **máy chủ bị giết giữa lượt** (không traceback, log đứt giữa dòng), và bộ chạy báo
   ra **5–10 ca "sản phẩm hỏng"** cộng **14–43 ca "không chạy"** — những con số ấy đo *cái nền*,
   không đo sản phẩm. Nguyên nhân bị giết **CHƯA XÁC ĐỊNH ĐƯỢC** (§3 nói rõ đã loại trừ những gì).
3. Vì thế lượt này thêm **một cổng biết phân biệt bốn phán quyết** (`DAT` · `HONG` ·
   `HA_TANG_CHET` · `KHONG_DO_DUOC`) và **"did not run" bị tính là HỎNG**, không phải là đạt.

---

## 1. NỀN: `7344c02` VÀO CÂY BẰNG CÁCH NÀO — VÀ VÌ SAO KHÔNG PHẢI `git merge`

**Sandbox CHẶN GHI `.git`.** Đo bằng lệnh thật, không suy đoán:

```sh
touch /Users/viporder/Projects/vip-express-hub/.git/worktrees/g21-ag06-e2e/.ag06-probe
# touch: ... Operation not permitted          ← exit 1
git merge --ff-only 7344c02
# fatal: update_ref failed for ref 'ORIG_HEAD': cannot lock ref 'ORIG_HEAD': Unable to create
#   '.../worktrees/g21-ag06-e2e/ORIG_HEAD.lock': Operation not permitted     ← exit 128
```

Nhánh `g21-ag06-e2e` đứng ở `0d55255`, là **tổ tiên** của `7344c02` (`git merge-base --is-ancestor`
→ YES), nên nhánh chỉ cần fast-forward — nhưng fast-forward cần ghi `.git`, mà `.git` nằm **ngoài**
thư mục làm việc nên bị chặn. Đã **KHÔNG tự vượt**: nội dung được materialize bằng
`git archive 7344c02 -- <27 tệp> | tar -x -C .` (chỉ ghi vào cây làm việc), rồi **xác minh từng
tệp**:

```sh
# với MỖI tệp trong 27: so sha256 trên đĩa với blob của 7344c02
#   KHỚP=27  LỆCH=0
```

**Ba tệp đang sửa dở (không nằm trong tập 27) được giữ nguyên** — sha256 trước và sau khi đồng bộ
**khớp nhau**:

| tệp | sha256[:8] trước | sau |
|---|---|---|
| `docs/G21_BANPHIM_E2E.md` | `c8c42c3d` | `c8c42c3d` |
| `thu_giao_dien/06_ban_phim.spec.js` | `193ee9a8` | `193ee9a8` |
| `thu_giao_dien/chay.sh` | `7d946928` | `7d946928` |

**Sản phẩm trên cây SAU khi đồng bộ** (đây là mốc mà mọi con số dưới đây gắn vào):

| tệp | sha256[:8] | ghi chú |
|---|---|---|
| `admin/billing.js` | **`00e8d4cd`** | **bản AG-00 gộp** (commit `7d8dfe4`) — đúng cái đã mở khoá ca 08 |
| `admin/admin.js` | `80bdc9fd` | bản AG-00 gộp |
| `admin/ban_phim.js` | `b5c7d741` | không đổi |
| `app/server.py` | `23515e6d` | theo `7344c02` |

**Đối chứng âm của phép đồng bộ:** nếu cây vẫn giữ bản G19 thì `08_bang_duong_billing` ca 01 phải
ĐỎ. Lượt chạy 16:26 (trước khi đồng bộ) đỏ đúng ở `08:114`; mọi lượt sau khi đồng bộ đều **xanh ở
`08:114`, `08:144` và `08:201`** (§2). Phép đồng bộ đã làm đúng cái nó phải làm.

---

## 2. KẾT QUẢ CHẠY — **SỐ THẬT**, ĐỦ CẢ LƯỢT ĐỎ LẪN LƯỢT XANH

Chín lượt chạy, **cùng một cây, cùng một bộ ca**, khác nhau ở cách gọi:

| # | lệnh | mốc (log) | mã thoát THẬT | đạt / hỏng / bỏ qua / **không chạy** | máy chủ |
|---|---|---|---|---|---|
| 1 | `sh thu_giao_dien/chay.sh` | 16:26:35 | **1** | 46 / **5** / 0 / **14** | **CHẾT** giữa lượt |
| 2 | `sh thu_giao_dien/chay.sh` | 16:32:12 | **1** | 12 / **10** / 0 / **43** | **CHẾT** giữa lượt |
| 3 | runner tự dựng nền | 16:29 | **0** | **65 / 0 / 0 / 0** | sống |
| 4 | E1 — bản sao **y** `chay.sh`, chỉ đổi chỗ ghi log máy chủ | 16:34:41 | **0** | **65 / 0 / 0 / 0** | sống |
| 5 | E2 — y E1, thêm `--reporter=list` | 16:36:59 | **1** | 27 / **7** / 0 / **31** | **CHẾT** giữa lượt |
| 6 | **CỔNG G22** `python3 app/thu/thu_g22_e2e.py` (lượt #1) | 16:43 | **0** | **65 / 0 / 0 / 0** | sống |
| 7 | **CỔNG G22** (lượt #2) | 16:45 | **0** | **65 / 0 / 0 / 0** | sống |
| 8 | **CỔNG G22** (lượt #3, sau khi vá bộ dọn) | 22:57 | **0** | **65 / 0 / 0 / 0** | sống |
| 9 | **CỔNG G22** (lượt #4, sau khi vá nhãn dọn) | 23:00 | **0** | **65 / 0 / 0 / 0** | sống |

**6 xanh · 3 đỏ**, và **cả ba lượt đỏ đều là nền chết**, không lượt nào là lỗi sản phẩm.

Lượt #1 và #2 ở trên là **hai lượt của chính lệnh được giao**, đọc nguyên văn:

```sh
sh thu_giao_dien/chay.sh
# lượt 1 → === EXIT CODE THẬT = 1
#   5 failed · 14 did not run · 46 passed (1.6m)
# lượt 2 → === EXIT CODE THẬT = 1
#   10 failed · 43 did not run · 12 passed (55.3s)
```

### 2.1 Vì sao "62 đạt / 1 hỏng / 2 không chạy" của lượt trước nay là 65/0/0/0

Ca hỏng duy nhất của lượt trước là `08_bang_duong_billing:114` — nó đối chiếu bảng khai trong
`admin/billing.js` với `app/server.py`, và bản G19 khai *CHỜ BACKEND* cho một đường **đã cắm**.
AG-00 đã gộp bản sửa (`00e8d4cd`). Trên cây này, **cả ba ca của tệp 08 đều chạy và đều đạt** —
hai ca *"did not run"* cũ chính là ca 02 và 03 của tệp ấy, bị chặn bởi `serial` khi ca 01 đỏ:

```
  ✓  53 08_bang_duong_billing.spec.js:114  › 01 — bảng khai của billing.js KHỚP server.py ở CẢ HAI chiều
  ✓  54 08_bang_duong_billing.spec.js:144  › 02 — TỰ KIỂM: đưa bảng SAI của bản trước G20 vào thì bộ đo PHẢI ĐỎ
  ✓  55 08_bang_duong_billing.spec.js:201  › 03 — đo THẬT: mỗi đường ĐANG DÙNG trả khác 404, mỗi đường CHỜ trả ĐÚNG 404
```

⇒ **Số thật của lượt này là `65 đạt · 0 hỏng · 0 bỏ qua · 0 không chạy`, mã thoát `0`.** Không làm
tròn, không bỏ qua ca nào.

**Quy mô bộ ca (đếm được, không kê tay):** 59 khối `test(` cộng 6 ca sinh bởi vòng lặp tham số
(3 ở `02_bo_cuc`, 3 ở `03_quyen`) = **65**. Con số này được **ghim bằng máy**: ca tự kiểm `d5` chạy
`npx playwright test --list` rồi đòi số ca liệt kê **bằng đúng** hằng ghim `SO_CA_GHIM = 65`.

---

## 3. BA LƯỢT ĐỎ — **MÁY CHỦ BỊ GIẾT TỪ NGOÀI**, KHÔNG PHẢI SẢN PHẨM HỎNG

### 3.1 Bằng chứng thứ nhất — mọi ca hỏng đều là *mất kết nối*, không phải *sai hành vi*

| lượt | số dòng `Error:` | `net::ERR_CONNECTION_REFUSED` | còn lại |
|---|---|---|---|
| #1 | 5 | **5** | 0 |
| #2 | 10 | **9** | 1 × `page.evaluate: TypeError: Failed to fetch` |
| #5 (E2) | 7 | **6** | 1 × *"không thu được nhãn CHỜ BACKEND nào có đường"* (ca tự canh của `04`, bắn giữa lúc máy chủ đã chết) |

22 dòng lỗi: **20 là `ERR_CONNECTION_REFUSED`**, 2 dòng còn lại là **hệ quả cùng một cái chết**
(cùng một cổng, cùng một lượt). Bốn ca ấy **đạt trong CẢ BỐN lượt xanh** trên **cùng cây** — nên
chúng không phải khuyết tật sản phẩm.

### 3.2 Bằng chứng thứ hai — log máy chủ **đứt giữa dòng, KHÔNG một traceback**

Lượt E2 giữ được log máy chủ (`/tmp/ag06-E2-server.log`, 251 098 byte). Nó **dừng đột ngột lúc
16:38:01 giữa dòng traffic bình thường**:

```
[hub] "GET /api/v2/audit HTTP/1.1" 200 -
{"luc": "2026-10-16 16:38:01+0700", ..., "duong": "/api/v2/audit", "ma_http": 200, "ms": 0}
                                    ← hết. Không dòng nào tiếp theo.
grep -c Traceback /tmp/ag06-E2-server.log   →  0
grep -c Exception /tmp/ag06-E2-server.log   →  0
```

Một tiến trình Python **tự chết vì lỗi** để lại traceback; một tiến trình **bị giết bằng tín hiệu**
thì không. Đây là dấu vết của **tín hiệu từ bên ngoài**, không phải lỗi mã nguồn.

### 3.3 Đã LOẠI TRỪ được những gì (mỗi dòng là một phép đo)

| nghi phạm | phép đo | kết quả |
|---|---|---|
| Hết đĩa | `df -h /` | 188 Gi trống — **loại** |
| Hết bộ nhớ / jetsam | `memory_pressure` (31% trống) · `ls /Library/Logs/DiagnosticReports/` quanh 16:27–16:38 | không có báo cáo crash/jetsam nào — **không có bằng chứng** |
| Máy chủ tự chết sau một khoảng thời gian | dựng máy chủ **đứng yên 100 giây**, có traffic nhẹ mỗi giây | **sống suốt 100 giây** — **loại** |
| Trong repo có lệnh giết theo mẫu tên | `grep -rn 'pkill\|killall'` toàn repo | 124 dòng, **tất cả** là chú thích/tài liệu hoặc bộ dò *cấm* nó; không có lời gọi nào — **loại** |
| Bộ báo cáo HTML của Playwright | E1 (bật HTML) **xanh**, E2 (tắt HTML) **đỏ** | **không tương quan** — **loại** |
| `set -e` của `chay.sh` | xem §4 | giải thích được **dòng bị thiếu ở cuối**, **không** giải thích được cái chết giữa lượt |

### 3.4 KẾT LUẬN — và điều **KHÔNG** được nói

**Nguyên nhân cái chết CHƯA XÁC ĐỊNH ĐƯỢC.** Không có `dtrace`/`strace` trong phiên này, và
`ps -o comm=` bị sandbox chặn (trả chuỗi rỗng), nên **không đo được ai gửi tín hiệu**. Tài liệu này
**không đoán**. Cái ĐO ĐƯỢC là: *tín hiệu từ ngoài tiến trình, không traceback, không tái lập ổn
định (6 xanh / 3 đỏ), và bản thân sản phẩm thì đạt 65/65 ở mọi lượt nền sống.*

**Hệ quả bắt buộc cho người đọc:** một lượt đỏ của `chay.sh` **KHÔNG được đọc thành "sản phẩm
hỏng"** khi chưa kiểm dấu hiệu nền chết. Cách kiểm, đúng ba dòng:

```sh
grep -c 'ERR_CONNECTION_REFUSED' <log>     # > 0  ⇒ nghi nền chết
grep -c 'Traceback' <log máy chủ>          # = 0  và log đứt giữa dòng ⇒ bị giết, không phải lỗi mã
kill -0 <pid máy chủ>                      # PID đã chết trong khi lượt còn chạy ⇒ nền chết
```

Cổng G22 làm đúng ba phép kiểm ấy **bằng máy** rồi mới phán (§5).

---

## 4. MỘT KHUYẾT TẬT CỦA `chay.sh` ĐO ĐƯỢC: `set -e` NUỐT DÒNG PHẠM VI

Trong **cả hai** lượt đỏ của `chay.sh`, dòng `[giao-dien] mã thoát N` **KHÔNG HỀ XUẤT HIỆN**
(`grep -n 'giao-dien' <log>` chỉ ra đúng một dòng: dòng `nền=… cổng=… pid=…`). Nguyên nhân đo được:

```sh
sh -c 'set -e; sh -c "exit 1"; MA=$?; echo "[giao-dien] mã thoát $MA"; exit $MA'
# → KHÔNG in gì · mã thoát = 1        ← dòng echo và `exit $MA` là MÃ CHẾT
sh -c      'sh -c "exit 1"; MA=$?; echo "[giao-dien] mã thoát $MA"; exit $MA'
# → "[giao-dien] mã thoát 1" · mã thoát = 1   ← ĐỐI CHỨNG DƯƠNG: bỏ `set -e` thì dòng ấy in ra
```

`chay.sh` có `set -e`, nên ngay khi `npx playwright test` thoát khác 0 thì shell **thoát tại chỗ**:
`MA=$?`, dòng `mã thoát`, dòng `PHẠM VI` và `exit $MA` **không bao giờ chạy**. Mã thoát vẫn ra `1`
một cách **tình cờ** (đúng mã của lệnh vừa hỏng), nên suốt nhiều wave không ai thấy.

**Vì sao ghi ra:** dòng `PHẠM VI` là dòng nói *"chỉ Chromium · chỉ 375/768/1280 · không cảm ứng
thật…"* — nó biến mất **đúng ở những lượt có ca hỏng**, tức đúng lúc người đọc cần nó nhất.
`thu_giao_dien/chay.sh` **KHÔNG nằm trong vùng được ghi của lượt này**, nên AG-06 **không tự sửa**;
bản vá đề nghị (một dòng): `npx playwright test "$@" || MA=$?` thay cho `set -e` bắt lấy nó — hoặc
`set +e` quanh đúng lời gọi ấy. **Cần AG-00 quyết.**

---

## 5. CỔNG G22 — `app/thu/thu_g22_e2e.py`

### 5.1 BỐN phán quyết, không phải hai

| mã | nhãn | khi nào | vì sao TÁCH RIÊNG |
|---|---|---|---|
| 0 | `DAT` | 65 đạt, 0 hỏng, 0 bỏ qua, 0 không chạy, máy chủ sống, mã thoát 0 | — |
| 1 | `HONG` | có ca hỏng / **không chạy** / bỏ qua / chập chờn, hoặc số đạt **khác ghim** | đây mới là *sản phẩm* |
| 2 | `KHONG_DUNG_DUOC_NEN` | thiếu Playwright/Chromium, không có cổng rỗng, migrate/seed/chuan_bi hỏng, máy chủ không mở cổng | không phải lỗi sản phẩm, cũng không phải "đạt" |
| 3 | `HA_TANG_CHET` | **máy chủ chết khi lượt kết thúc**, hoặc log có dấu hiệu mất kết nối | **đây là lượt 16:26 và 16:32** — nếu gộp vào `HONG` thì báo cáo sẽ nói "5 ca sản phẩm hỏng" |
| 4 | `KHONG_DO_DUOC` | không đọc được dòng tổng kết nào | bộ đọc hỏng ≠ đạt |

**Thứ tự xét là cố ý:** nền chết được xét **TRƯỚC** mọi kết luận về sản phẩm. Khi máy chủ chết thì
`failed`/`did not run` **không còn đo sản phẩm nữa** — chúng đo cái nền; xét sau sẽ là **gán tội
cho sản phẩm bằng một phép đo đã hỏng**.

### 5.2 Ba điều khoản của nhiệm vụ được cưỡng chế BẰNG MÁY

* **"`did not run` KHÔNG phải là đạt"** — `did_not_run > 0` ⇒ `HONG`. Ghim bằng `test_b5`.
* **Ghim số ca** — `passed != 65` ⇒ `HONG`. Ghim bằng `test_b7` (12 ca ⇒ HỎNG) và `test_b8`
  (66 ca ⇒ HỎNG), cộng `test_d5` (số ca `--list` phải bằng hằng ghim).
* **Ghim binary Chromium** — thiếu binary ⇒ `KHONG_DUNG_DUOC_NEN`; ca `d2` đòi đường dẫn Playwright
  **thật sự spawn** phải trùng đường dẫn tài liệu ghim.

### 5.3 Bộ tự kiểm — **26 ca, exit 0**, và nó ĐỎ ĐƯỢC ở cả hai chiều

```sh
python3 app/thu/thu_g22_e2e.py --tu-kiem
# → Ran 26 tests in 2.257s · OK
#   TỰ KIỂM: 26 ca · hỏng 0 · lỗi 0 · bỏ qua 0
```

| nhóm | ca | đối chứng |
|---|---|---|
| A · bộ đọc | `a1`–`a5` | `a1` đọc **nguyên văn khối tổng kết THẬT của lượt đỏ 16:26** (46/5/14); `a3` rác ⇒ `None`; `a4` dòng `✓ 1 [chromium] …` **không** bị đếm thành "1 passed" |
| B · phán quyết | `b1`–`b10` | **`b3` là ca quyết định:** *cùng khối số 46/5/14*, máy chủ sống ⇒ `HONG`; máy chủ chết ⇒ `HA_TANG_CHET`. `b5`/`b6`/`b7`/`b8` ghim điều khoản 3 |
| C · cổng & PID | `c1`–`c6` | `c2` **đối chứng âm**: tự chiếm một cổng rồi đòi bộ dò phải nói CÓ. `c5`/`c6` là hai lỗi **của chính cổng** do chạy nó mà lộ ra (§5.4) |
| D · bất biến | `d1`–`d5` | `d3` đọc thẳng `adapter.CarrierAdapter.CHO_PHEP_LIVE` **và** sổ đăng ký hãng — đòi sổ **không rỗng** rồi mới đòi không hãng nào mở live; `d4` gỡ `GIT_CONFIG_*` **chỉ khi dị dạng**, hợp lệ thì không đụng |

### 5.4 HAI LỖI CỦA CHÍNH CỔNG — do chạy nó mà lộ ra, đã vá, đã ghim bằng ca

Ghi ra vì luật của dự án: một bộ đo chưa từng đỏ thì chưa chứng minh được gì.

1. **`os.kill(pid, 0)` nói dối với ZOMBIE.** Lượt cổng #1 in
   `dọn tiến trình: CẢNH BÁO: pid 46403 còn sống nhưng tên là '' — KHÔNG SIGKILL` — trong khi
   `còn mồ côi: False`, tức tiến trình **đã chết**. Nguyên nhân: con đã chết nhưng chưa `wait()`
   vẫn giữ PID và `kill(pid, 0)` vẫn thành công. **Vá:** giữ đối tượng `Popen` và hỏi `tt.poll()`
   (vừa trả lời vừa thu lại tiến trình). **Ghim:** `test_c5`.
2. **Đường dọn SẠCH trả ghi chú RỖNG.** Lượt cổng #3 in `dọn tiến trình: không có pid nào` — dù
   máy chủ **có** PID và **đã được tắt sạch**. Nơi in dịch chuỗi rỗng thành "không có pid nào",
   nên một lượt dọn THÀNH CÔNG hiện ra y như một lượt KHÔNG CÓ PID — đúng chỗ người đọc dùng để
   tin là không còn mồ côi. **Vá:** đường sạch phải nói ra nó sạch, kèm PID. **Ghim:** `test_c6`.

### 5.5 KHỐI BẰNG CHỨNG NGUYÊN VĂN — lượt cổng #4 (bản đã vá, `sha256[:8] = d42eed9e`)

```sh
python3 app/thu/thu_g22_e2e.py --log /tmp/ag06-cong-g22-4.log --json /tmp/ag06-cong-g22-4.json
```

```
[g22] nền=/var/folders/.../T/veh-g22-e2e.avmmslwp cổng=18008 pid=14927
[g22] npx playwright test
[g22] mã thoát playwright (THẬT, ghi trước mọi pipe) = 0

════════════════ BẰNG CHỨNG CỔNG E2E TẦNG 3 (G22 · AG-06) ════════════════
  lệnh thật           : npx playwright test
  mã thoát playwright : 0
  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 65/0/0/0/0  (ghim ĐẠT = 65)
  máy chủ còn sống    : True   (pid 14927)
  dấu hiệu nền chết   : không
  cổng / nền          : 18008 / /var/folders/.../T/veh-g22-e2e.avmmslwp
  Chromium (GHIM)     : .../playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
  Chromium phiên bản  : Chromium 141.0.7390.37
  Chromium sha256     : a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040  (146794928 byte)
  playwright          : 1.56.1
  HEAD                : 0d55255582cb797de75bdf9a40e1b63fd248a6be
  sha[:8] sản phẩm    : {"admin/ban_phim.js": "b5c7d741", "admin/billing.js": "00e8d4cd",
                         "admin/admin.js": "80bdc9fd", "app/server.py": "23515e6d"}
  log playwright      : /tmp/ag06-cong-g22-4.log
  log máy chủ         : /var/folders/.../T/veh-g22-may-chu-18008.log
  dọn tiến trình      : máy chủ đã tắt SẠCH theo ĐÚNG PID 14927 (SIGTERM, đã xác minh chết)
  còn mồ côi          : False
  ── PHÁN QUYẾT: DAT (mã thoát 0)
     65 ca đạt · 0 hỏng · 0 bỏ qua · 0 không chạy · 0 chập chờn
══════════════════════════════════════════════════════════════════════════════
[g22] MÃ THOÁT CỦA CỔNG = 0
```

Bốn lượt cổng (#1, #2, #3, #4) cho **cùng một kết quả**: `65/0/0/0`, mã thoát `0`, máy chủ sống,
`còn mồ côi: False`. Ba lượt đầu in dòng dọn tiến trình **sai** như mô tả ở §5.4 — nên khối trên
lấy từ lượt **#4**, lượt duy nhất chạy bằng bản **đã vá cả hai lỗi**.

---

## 6. GHIM CHROMIUM — ĐƯỜNG DẪN · PHIÊN BẢN · SHA256 (yêu cầu trực tiếp của Owner)

```
đường dẫn : /Users/viporder/orca/workspaces/vip-express-hub/g21-ag06-e2e/node_modules/
            playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
phiên bản : Chromium 141.0.7390.37
sha256    : a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040
kích thước: 146 794 928 byte
Playwright: @playwright/test 1.56.1 · playwright-core 1.56.1   (PLAYWRIGHT_BROWSERS_PATH=0)
```

### 6.1 CÁI BẪY — `chromium.executablePath()` trả **một binary KHÁC** với binary được spawn

```sh
node -e 'const {chromium}=require("playwright-core"); console.log(chromium.executablePath())'
# → .../chromium-1194/chrome-mac/Chromium.app/Contents/MacOS/Chromium      ← binary ĐẦY ĐỦ
PLAYWRIGHT_BROWSERS_PATH=0 DEBUG=pw:browser node -e '…chromium.launch({headless:true})…'
# → pw:browser <launching> .../chromium_headless_shell-1194/chrome-mac/headless_shell …  ← CÁI THẬT
```

Chế độ `headless: true` (đúng cấu hình `playwright.config.js`) spawn **headless shell**, không phải
Chromium đầy đủ. Hai đường dẫn ấy **khác nhau** và cả hai đều báo `Chromium 141.0.7390.37`. Ghi vào
tài liệu đường dẫn của `executablePath()` là **ghim nhầm thứ cho QA lượt sau** — nên đường dẫn ghim
ở trên được lấy bằng cách **hỏi thẳng Playwright cái nó spawn**, và ca `d2` canh đúng điều đó.

### 6.2 YÊU CẦU CHO QA LƯỢT SAU (nguyên văn tinh thần của Owner)

* Dùng **đúng binary trên** — cùng đường dẫn, cùng sha256 `a9752d88…`.
* **KHÔNG được skip tầng này.** Cổng G22 coi "thiếu binary" là `KHONG_DUNG_DUOC_NEN` (mã 2), và
  ca `d1`/`d2` chỉ `skipTest` **kèm lý do** khi máy chưa cài — còn trên cây này binary **có mặt**
  và đã được kiểm.
* Muốn biết máy đang có gì: `python3 app/thu/thu_g22_e2e.py --ghim-chromium`.

---

## 7. DỌN TIẾN TRÌNH — THEO **ĐÚNG PID**, KHÔNG `pkill`

* Máy chủ do cổng dựng được tắt bằng **`SIGTERM` gửi tới đúng PID của `Popen`**, chờ tới khi nó
  **chết thật** (`tt.poll()`), chỉ `SIGKILL` khi là **con của chính tiến trình này** (PID chưa thể
  được cấp lại) — **không bao giờ** khớp theo mẫu tên (§16.7; tiền lệ `pkill -f cat` giết cả
  Ollama và Synology Drive).
* Sau khi dọn, cổng **xác minh lại**: `còn mồ côi: False` trong cả bốn lượt cổng xanh.
* **GHI RÕ PHẠM VI:** `ps -o comm=` **bị sandbox chặn** ở phiên này (trả chuỗi rỗng), nên đường
  "xác minh danh tính rồi mới `SIGKILL`" **không chạy được ở đây**. Khi không xác minh được, cổng
  **TỪ CHỐI giết rồi báo ra**, chứ không giết bừa. Đường ấy vẫn giữ trong mã cho môi trường khác.
* Kiểm tay sau lượt này:
  `ps -eo pid,args | grep -E 'app/server\.py' | grep -v grep` → **không dòng nào**.

---

## 8. TỆP ĐÃ SỬA / TẠO, VÀ **AG-00 PHẢI COMMIT HỘ**

### 8.1 Tệp của lượt này

| tệp | trạng thái | sha256[:8] |
|---|---|---|
| `app/thu/thu_g22_e2e.py` | **MỚI** | `d42eed9e` |
| `docs/G22_BANPHIM_E2E.md` | **MỚI** (tài liệu này) | tự tham chiếu — lấy bằng `shasum -a 256 docs/G22_BANPHIM_E2E.md` (mỗi lần sửa tài liệu là sha đổi, nên không ghim vào chính nó) |

**KHÔNG có tệp mã sản phẩm nào bị sửa trong lượt này.** Ba tệp đang sửa dở từ lượt G21
(`thu_giao_dien/06_ban_phim.spec.js`, `thu_giao_dien/chay.sh`, `docs/G21_BANPHIM_E2E.md`) và ba
tệp spec AG-02 chưa được theo dõi **được giữ nguyên sha** (§1).

### 8.2 AG-00 PHẢI COMMIT HỘ — sandbox CHẶN ghi `.git`

`touch .git/worktrees/g21-ag06-e2e/…` → `Operation not permitted`; `git merge --ff-only` → không
khoá được `ORIG_HEAD`. AG-06 **không tự vượt**. **Danh sách `git add` chính xác** (chỉ những tệp
thuộc làn này — 27 tệp đã đồng bộ **không** nằm trong danh sách, chúng đã có sẵn trong
`integration/g20`):

```sh
git add app/thu/thu_g22_e2e.py docs/G22_BANPHIM_E2E.md \
        thu_giao_dien/06_ban_phim.spec.js thu_giao_dien/chay.sh docs/G21_BANPHIM_E2E.md \
        thu_giao_dien/08_bang_duong_billing.spec.js \
        thu_giao_dien/09_man_ag05.spec.js \
        thu_giao_dien/10_trang_tinh_du_lieu.spec.js
```

**Lưu ý cho AG-00:** cây làm việc đang có **34 mục** trong `git status --porcelain` (15 `M` +
19 `??`) vì 27 tệp của `7344c02` đã được materialize **mà không ghi được vào index**. Những tệp ấy
**trùng byte** với `integration/g20` (đã xác minh 27/27 bằng sha256), nên `git add` chúng là vô hại
— nhưng danh sách trên **cố ý không có chúng** để commit của làn này sạch.

---

## 9. CHƯA ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

* **Nguyên nhân máy chủ bị giết (§3.4).** Đây là lỗ hổng lớn nhất lượt này để lại: một cái cổng
  chặn hồi quy chạy được **6/9 lượt** thì chưa đủ tin để làm chốt. Cổng G22 **phân loại đúng**
  nhưng **không ngăn được**.
* **`chay.sh` chưa được vá** (§4) — ngoài vùng được ghi.
* Chỉ **Chromium**, chỉ ba bề rộng 375/768/1280; **không** thiết bị cảm ứng thật, **không** trình
  đọc màn hình, **không** in/PDF thật, **không** Safari/Firefox.
* **Không** gọi ra hãng ở bất kỳ môi trường nào; **không** mở `CHO_PHEP_LIVE`; bind `127.0.0.1`;
  **không** đụng PostgreSQL; **không** deploy/tunnel/push.
* `git` của phiên này ở trạng thái **dị dạng** (`GIT_CONFIG_COUNT=2` thiếu `GIT_CONFIG_KEY_0,1`):
  mọi lệnh git thoát 128 nếu không gỡ biến. Cổng G22 tự gỡ **kèm cảnh báo** (ca `d4`).

---

## 10. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM

| # | Luật | Cách đo | Kết quả |
|---|---|---|---|
| 1 | Không gọi API hãng (kể cả sandbox) | nền cô lập + `adapter.CarrierAdapter.CHO_PHEP_LIVE is False` **đọc từ mã** (ca `d3`) + sổ đăng ký hãng không hãng nào `live_mo` | ✓ |
| 2 | Không push/deploy/tunnel; bind `127.0.0.1`; không mở `CHO_PHEP_LIVE` | cổng **TỪ CHỐI CHẠY** nếu `VIP_HUB_BIND` không phải loopback; URL nền luôn `http://127.0.0.1:<cổng>` | ✓ |
| 3 | Không credentials thật, không `.env`, không in bí mật | không tạo/đọc `.env`; log chỉ chứa tên tài khoản demo | ✓ |
| 4 | Không đoán mã trạng thái hãng (D-4) | lượt này không chạm mã trạng thái hãng nào | ✓ |
| 5 | Giữ chốt D-9 city/area | không sửa dòng mã sản phẩm nào | ✓ |
| 6 | Không chuyển CSDL nghiệp vụ sang PostgreSQL (D-8) | không chạm `:5432`, không chạy cụm PG nào | ✓ |
| 7 | Không dùng mô hình khác; không tự bấm duyệt sandbox | không gọi mô hình nào; `git` bị chặn thì **báo AG-00**, không tự vượt | ✓ |
| 8 | Không xoá hàng loạt, không sửa ngoài vùng được ghi | xem §8.1; dọn tiến trình theo **đúng PID**; thư mục tạm `veh-*` được xoá sau mỗi lượt | ✓ |

---

## 11. ĐỀ NGHỊ CHO AG-00 / ĐIỀU PHỐI

1. **Commit hộ** danh sách ở §8.2 (sandbox chặn `.git`).
2. **Vá `chay.sh`** theo §4 (một dòng) — nếu không, mọi lượt có ca hỏng sẽ **im lặng bỏ dòng PHẠM VI**.
3. **Điều tra cái chết của máy chủ** (§3.4) trước khi dùng tầng 3 làm cổng chặn hồi quy: hiện
   6/9 lượt xanh. Đây là việc **ngoài** vùng được ghi của AG-06.
4. **QA lượt sau:** dùng cổng G22 (`python3 app/thu/thu_g22_e2e.py`) thay vì đọc `chay.sh` trần —
   nó nói thẳng lượt đỏ là *sản phẩm* hay *nền*, và ghim đúng binary Chromium ở §6.

---
---

# PHẦN B — LƯỢT AG-06 #2 (DISPATCH MỚI): VÁ RUNNER · ĐO GIỚI HẠN TIẾN TRÌNH · CHẠY LẠI TRỌN BỘ

**Người làm:** AG-06 · dispatch 2 (`task_506aad6bf953` / `ctx_9282e8c40431`) · 17/10/2026 ·
nối tiếp Phần A (`integration/g20` @ `7344c02`, đã được AG-00 gộp ở commit `05eecf1`).
**Vùng được ghi của lượt này:** `thu_giao_dien/chay.sh` · `thu_giao_dien/*.spec.js` ·
`admin/ban_phim.js` · `app/thu/thu_g22_e2e.py` · `docs/G22_BANPHIM_E2E.md`.
**KHÔNG sửa một dòng mã sản phẩm nào** — sha256 sản phẩm ở §B.5 khớp đúng bản đã ghim ở §1.

Ba việc của lượt này thay cho ba đề nghị ở §11 Phần A: **đề nghị 2 (vá `chay.sh`) đã làm**,
**đề nghị 3 (điều tra cái chết) đã đo tới đáy những gì đo được**, **đề nghị 1 (commit hộ) vẫn cần
AG-00** vì `.git` vẫn bị chặn ghi (§B.5).

## B.0 — BA CÂU, ĐỌC LÀ ĐỦ

1. **Đã vá HAI lỗi báo cáo thật của `chay.sh`** (`set -e` nuốt dòng PHẠM VI + mã thoát;
   `kill -0` nói dối về tiến trình đã chết), và chứng minh bằng **sáu đường thoát**: trên **cùng
   một ca hỏng thật**, bản cũ in **0** dòng PHẠM VI, bản vá in **2**; thoát sớm giữ đúng mã `2`;
   ca hỏng giữ đúng mã `1`; `SIGTERM` giữa lượt giữ đúng mã `143` và **không để lại tiến trình mồ
   côi nào** (`0` người nghe trên cổng, `0` tiến trình `app/server.py` còn lại).
2. **Đã đo giới hạn tiến trình của chính lượt chạy, và phép đo BẮT ĐƯỢC cái chết**:
   đỉnh `fd` = **50–53** trên trần `ulimit -n` = **1048575** (≈ 0,005 %), tiến trình con = **0**,
   cổng đang mở = **đúng 1** (cổng được chọn), thời gian sống **112,4–113,5 s**; **đối chứng
   dương**: giết máy chủ từ ngoài ở giây **30,0** ⇒ bộ đo bắt ở giây **30,01** với
   `SIGKILL(9)` (tín hiệu KHÔNG do bộ dọn gửi), `0` traceback, `9 × ERR_CONNECTION_REFUSED` —
   **đúng dấu vết của 3/9 lượt đỏ ở Phần A**.
3. **Đã chạy lại trọn bộ 7 lượt trong lượt này: 6 lượt ghi được đều `65/0/0/0 · exit 0`, và
   KHÔNG lượt nào bị một cơ chế LẠ giết** — lượt thứ bảy là **đối chứng dương của chính tôi**
   (giết ở giây 30 để chứng minh phép đo bắt được cái chết), cộng ma trận 4 tiến trình nền sống
   đủ **240 s** (kể cả bản sao *giống tên* `app/server.py`, bản sao *nghe cổng* 18xxx, và chính
   `app/server.py` thật không tải).
   Cái chết **KHÔNG tái lập** ở lượt này; cái **ĐO ĐƯỢC** là nó không phải lỗi sản phẩm (§B.4).

**Lệnh dựng lại toàn bộ số ở Phần B** (chép nguyên, chạy từ gốc repo):

```sh
python3 app/thu/thu_g22_e2e.py --tu-kiem                        # 31 ca tự kiểm · exit 0
python3 app/thu/thu_g22_e2e.py --do-chay-sh 4 \
        --thu-muc-log /tmp/ag06-do-viec3 --json-tong /tmp/ag06-viec3.json   # 4 lượt trọn bộ + đo
python3 app/thu/thu_g22_e2e.py --do-chay-sh 1 --giet-luc 30 \
        --thu-muc-log /tmp/ag06-do-doi-chung --json-tong /tmp/ag06-doi-chung.json  # ĐỐI CHỨNG DƯƠNG
python3 app/thu/thu_g22_e2e.py --tro-ngo 240 --json-tong /tmp/ag06-tro-ngo.json # ma trận 4 tiến trình
python3 app/thu/thu_g22_e2e.py --json /tmp/ag06-cong.json       # CỔNG ĐẦY ĐỦ: 65 ca · exit 0
```

---

## B.1 — VIỆC 1: `chay.sh` NUỐT DÒNG PHẠM VI — ĐÃ VÁ, VÀ CHỨNG MINH BẰNG SÁU ĐƯỜNG THOÁT

### B.1.1 Hai lỗi, nguyên văn nguyên nhân

| # | lỗi | cơ chế ĐO ĐƯỢC | bản vá |
|---|---|---|---|
| 1 | **dòng `PHẠM VI` biến mất đúng ở lượt có ca hỏng** | `set -e` + lời gọi `npx playwright test` không được bắt ⇒ shell thoát NGAY tại lời gọi hỏng; `MA=$?`, dòng `mã thoát`, dòng `PHẠM VI`, `exit $MA` là **mã chết**. Mã thoát vẫn ra `1` một cách **tình cờ** (đúng mã lệnh vừa hỏng) nên nhiều wave không ai thấy (§4 Phần A) | lời gọi được bắt `\|\| MA=$?`; **mã thoát THẬT + PHẠM VI in trong `trap … EXIT`** ⇒ không đường thoát nào bỏ qua |
| 2 | **bộ dọn nói dối về tiến trình ĐÃ CHẾT** | `kill -0 PID` **vẫn thành công với ZOMBIE** ⇒ vòng dọn quay 5 s vô ích, in *"pid VẪN SỐNG — còn tiến trình mồ côi"* cho một máy chủ đã chết, và **bỏ mất mã thoát thật** của nó (128+tín hiệu ⇒ biết bị giết bằng tín hiệu nào). Cùng họ với lỗi đã đo ở §5.4 Phần A | `may_chu_con_song()` = `kill -0` **+ đòi còn ít nhất một mô tả tệp** (zombie không còn tệp nào), rồi `wait` để **thu lại** và đọc mã thoát thật |

### B.1.2 SÁU đường thoát — mỗi dòng là một lượt chạy THẬT, không phải suy luận

| # | đường thoát | lệnh (nguyên văn) | mã thoát THẬT | dòng `[giao-dien] PHẠM VI` | dòng `mã thoát THẬT` |
|---|---|---|---|---|---|
| 1 | cây tạm **thiếu Playwright** | `sh <tạm>/thu_giao_dien/chay.sh` | **2** | **2** | 1 (`2`) |
| 2 | cây tạm **nền hỏng** (thiếu `app/`) | `sh <tạm2>/thu_giao_dien/chay.sh` | **2** | **2** | 1 (`2`) |
| 3 | **CA HỎNG THẬT**, bản **CŨ** `7d946928` (trích từ `HEAD`, cùng cây) | `sh thu_giao_dien/_chay_cu_tam.sh --reporter=list _tu_kiem_chay_sh_tam.spec.js` | **1** | **0** | **0** |
| 4 | **cùng ca hỏng ấy**, bản **VÁ** `15e865d8` | `sh thu_giao_dien/chay.sh --reporter=list _tu_kiem_chay_sh_tam.spec.js` | **1** | **2** | 1 (`1`) |
| 5 | **`SIGTERM` giữa lượt** | `sh chay.sh & P=$!; sleep 20; kill -TERM $P` | **143** | **2** | 1 (`143`) |
| 6 | **máy chủ bị giết từ NGOÀI** (đối chứng dương §B.2.3) | `--do-chay-sh 1 --giet-luc 30` | **1** | **2** | 1 (`1`) |

**Nguyên văn hai log của đường 3 và 4 — CÙNG một ca hỏng, khác đúng một dòng bản vá:**

```sh
# BẢN CŨ 7d946928 — các dòng bắt đầu bằng `[giao-dien]`:
$ grep -n '^\[giao-dien\]' /tmp/ag06-t4-cu.log
3:[giao-dien] nền=…/veh-giao-dien.hbFKDa cổng=19946 pid=39285
$ # → KHÔNG có dòng PHẠM VI, KHÔNG có dòng "mã thoát".  (chỉ 1 dòng [giao-dien])

# BẢN VÁ — cùng ca hỏng ấy:
$ grep -n '^\[giao-dien\]' /tmp/ag06-t4.log | tail -4
43:[giao-dien] PHẠM VI (in lại khi kết thúc): chỉ Chromium (bản Playwright trong node_modules) · …
44:[giao-dien] máy chủ pid 38879 còn sống khi lượt kết thúc
45:[giao-dien] bộ dọn đã tắt máy chủ pid 38879 theo ĐÚNG PID
46:[giao-dien] bộ dọn đã tắt máy chủ pid 38879: mã 143 = SIGTERM(15) — tín hiệu do CHÍNH bộ dọn gửi
```

**Đếm bằng máy (neo `^[giao-dien]` — KHÔNG đếm trần, vì chuỗi "PHẠM VI" còn nằm trong chính
ngữ cảnh lỗi mà Playwright in ra, lượt đầu đã đếm nhầm đúng vì thế):**

| log | tổng dòng `[giao-dien]` | dòng `PHẠM VI` | dòng `mã thoát` |
|---|---|---|---|
| bản CŨ `7d946928`, ca hỏng | 1 | **0** | **0** |
| bản VÁ `15e865d8`, ca hỏng | 7 | **2** | 1 |

**Đường 5 nói thêm điều đáng nói:** `SIGTERM` gửi vào runner giữa lượt **không** ngắt được
`npx playwright` đang chạy (POSIX hoãn trap tới khi lệnh nền trước kết thúc) — runner chạy hết
lượt rồi mới thoát `143`. Điều **quan trọng** là: mã thoát thật **được giữ**, dòng PHẠM VI **có
mặt**, và bộ dọn vẫn tắt đúng PID:

```sh
$ kill -TERM $P; wait $P; echo $?          # → 143
$ lsof -nP -iTCP:19547 -sTCP:LISTEN | wc -l # → 0   (không còn người nghe trên cổng của lượt)
$ pgrep -f 'app/server.py' | wc -l          # → 0   (không còn tiến trình mồ côi)
```

### B.1.3 Ba bản vá THÔNG BÁO nữa, do chính các lượt đo ở trên làm lộ ra

Ghi ra theo luật của dự án: *một bộ đo chưa từng đỏ thì chưa chứng minh được gì*.

| # | hiện tượng ĐO ĐƯỢC | bản vá |
|---|---|---|
| a | lượt đối chứng #1 in `log máy chủ: 0` rồi **một dòng `? traceback`** — vì `grep -c` in ra `0` **rồi** thoát `1`, nên `\|\| echo "?"` ghép thêm một dòng vào biến | tách hai bước: lấy `grep -c`, chỉ thay `?` khi biến RỖNG |
| b | bộ dọn in *"máy chủ pid … bị GIẾT BẰNG TÍN HIỆU: mã 143"* cho **chính `SIGTERM` của nó** ⇒ đọc nhầm thành bị giết từ ngoài | `thu_hoi_may_chu tu-don` ⇒ câu rõ: *"tín hiệu do CHÍNH bộ dọn gửi"* / *"tín hiệu KHÔNG do bộ dọn gửi"* |
| c | `SIGTERM` không đủ sau 5 s thì vòng dọn cũ **không thử lại** sau `kill -9` | thêm vòng chờ thứ hai sau `SIGKILL`, vẫn xác minh danh tính trước khi dùng tín hiệu mạnh |

**Chuỗi sha256 của `chay.sh` trong lượt này** (mọi khác biệt giữa ba bản đều nằm ở **câu chữ của
nhánh BÁO CHẾT**, không đụng đường in PHẠM VI / đọc mã thoát — đã kiểm bằng `diff`):

| bản | sha256[:8] | dùng ở đâu |
|---|---|---|
| H1 | `2f724e4d` | lượt trọn bộ 23:27 (lượt #1 ở §B.3) |
| H2 | `15e865d8` | đường 4 + 5 ở trên, và **lượt đối chứng dương** 00:21 |
| **H3 (cuối)** | **`d9278db6`** | **bốn lượt trọn bộ 00:25–00:30** (§B.2.2, §B.3) |

---

## B.2 — VIỆC 2: MÁY CHỦ BỊ GIẾT TỪ NGOÀI — ĐO GIỚI HẠN TIẾN TRÌNH, VÀ ĐỐI CHỨNG BẮT BUỘC

### B.2.1 Bộ đo: đo cái gì, và vì sao đo như thế

`app/thu/thu_g22_e2e.py` (§G) thêm `BoDoGioiHan`: lấy mẫu **mỗi 0,4 s** tiến trình máy chủ bằng
`lsof` + `pgrep` + một phép nối TCP thật — không dùng `ps` (bị sandbox chặn: `/bin/ps: Operation
not permitted`) và không dùng `dtrace` (SIP chặn: `dtrace: failed to initialize dtrace: Operation
not permitted`):

| đại lượng | cách đo | trả gì khi KHÔNG đo được |
|---|---|---|
| **mô tả tệp đang mở** | `lsof -p PID -F f`, đếm dòng `^f` | `None` (KHÔNG trả `0` — "0 fd" và "không đo được" là hai chuyện khác nhau) |
| **ổ cắm TCP + cổng đang nghe** | `lsof -nP -p PID -a -iTCP -F fTn`, gom theo fd rồi xét `TST=LISTEN` | `(None, None)` |
| **tiến trình con trực tiếp** | `pgrep -P PID` | `None` |
| **máy chủ còn TRẢ LỜI không** | nối TCP + `GET /` (mã HTTP, ms) | `ok=False`, `ms` vẫn đo |
| **cái CHẾT** | `phat_hien_chet()`: hai dấu hiệu ĐỘC LẬP — (a) `kill(pid,0)` sai **hoặc** hết mô tả tệp (bắt được ZOMBIE), (b) cổng ngừng trả lời trong khi mẫu trước còn trả lời | `(None, None, "còn sống tới hết lượt")` |
| **trần của phiên** | `ulimit -n`, `ulimit -Hn`, `launchctl limit maxfiles` | `None` |

### B.2.2 BẢNG GIỚI HẠN — số của TỪNG lượt (đây là phần "ghi rõ bằng số" của việc 2)

Bốn lượt trọn bộ (00:25:00 → 00:30:42), chạy **đúng như người dùng gõ** `sh thu_giao_dien/chay.sh`
(không thêm cờ nào), bộ đo gắn vào tiến trình máy chủ ngay khi runner công bố pid:

| lượt | giờ | mã thoát | đạt/hỏng/bỏ qua/**không chạy** | PHẠM VI | máy chủ sống | **fd** min…max | **tcp** ≤ | **cổng nghe** | **con** ≤ | ms tb / cao nhất | HTTP cuối | phán quyết |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 00:25:00 | **0** | **65**/0/0/0 | 2 | **112,6 s** | 45…**50** | 2 | `18733` | 0 | 0,6 / 4,6 | **200** | **DAT** |
| 2 | 00:26:53 | **0** | **65**/0/0/0 | 2 | **112,4 s** | 45…**53** | 2 | `18441` | 0 | 1,1 / 136,2 | **200** | **DAT** |
| 3 | 00:28:48 | **0** | **65**/0/0/0 | 2 | **113,5 s** | 45…**50** | 2 | `18434` | 0 | 0,9 / 30,1 | **200** | **DAT** |
| 4 | 00:30:42 | **0** | **65**/0/0/0 | 2 | **112,5 s** | 45…**50** | 2 | `19863` | 0 | 0,6 / 6,9 | **200** | **DAT** |
| **đối chứng dương** | 00:21:02 | **1** | 15/**9**/0/**41** | 2 | **CHẾT ở 30,01 s** | 0…48 | 1 | `19848` | 0 | 0,5 / 3,2 | — (chết) | **HA_TANG_CHET** |

**Trần của chính phiên đo** (máy chủ THỪA HƯỞNG vì cùng cây tiến trình):

```
ulimit -n  (mềm) = 1048575        ulimit -Hn (cứng) = unlimited
launchctl limit maxfiles = maxfiles 256 unlimited     ← chỉ áp cho tiến trình do launchd sinh ra;
                                                        máy chủ của `chay.sh` thừa hưởng 1048575
```

### B.2.3 ĐỐI CHỨNG — ÂM và DƯƠNG, cả hai đều BẮT BUỘC

**ĐỐI CHỨNG ÂM (mốc so sánh): những lượt KHÔNG bị giết.** Sáu lượt ghi được trong lượt này —
năm lượt `chay.sh` + một lượt cổng đầy đủ — đều `65/0/0/0`, `exit 0`, PHẠM VI 2 dòng, máy chủ sống
tới hết lượt (112–119 s), `fd` đỉnh 50–53, `tcp` đỉnh ≤ 2, `con` = 0, **một** cổng nghe duy nhất,
HTTP cuối `200`, và log máy chủ **0 traceback**. Thêm nữa, lượt cổng đầy đủ giữ được log máy chủ:

```
$ L=/var/folders/…/T/veh-g22-may-chu-18708.log
$ wc -l < $L ; wc -c < $L ; grep -c Traceback $L
4190            623701           0
$ grep -o 'Thread-[0-9]*' $L | sed 's/Thread-//' | sort -n | tail -1
2097            ← ≈ 2097 luồng phục vụ đã tạo trong ~110 giây, KHÔNG traceback, dòng cuối là
                  một yêu cầu 200 lúc 00:34:30 — tức 2 giây trước khi lượt kết thúc (00:34:32)
```

**ĐỐI CHỨNG DƯƠNG (chứng minh phép đo BẮT ĐƯỢC cái chết — không phải quan sát tình cờ):**
`--do-chay-sh 1 --giet-luc 30` cho **bộ đo tự giết máy chủ từ một tiến trình KHÁC** (không phải
từ runner) sau 30 giây, rồi đòi chính phép đo phải thấy nó:

```
[đo]    máy chủ pid 49972 · cổng 19848 → bắt đầu lấy mẫu mỗi 0.40s
[đo]    exit=1 · 40.7s · HA_TANG_CHET ⇒ tiến trình máy chủ KHÔNG còn sống khi lượt chạy kết thúc
        ⇒ 9 ca hỏng / 41 ca không chạy là HỆ QUẢ CỦA NỀN, không phải của sản phẩm
  │      ↳ ĐỐI CHỨNG DƯƠNG: bộ đo giết máy chủ ở giây 30.0 ⇒ bộ đo bắt được ở giây 30.01
  │        (tiến trình không còn sống (kill(pid,0) hoặc hết mô tả tệp))
```

Sai số nói ĐÚNG những gì đo được: **mẫu ĐẦU TIÊN thấy chết ở giây 30,01**, mốc giết là **30,0**,
lần trả lời HTTP cuối cùng thành công ở **29,56 s**, nhịp lấy mẫu **0,4 s** ⇒ cái chết được định vị
trong một cửa sổ **0,4 s** quanh mốc giết. Đây **không** phải "quan sát tình cờ": bộ đo còn **nói ra
lý do** (`tiến trình không còn sống (kill(pid,0) hoặc hết mô tả tệp)`), và **tín hiệu** lấy từ mã
thoát THẬT của con (`137 = SIGKILL(9)`), không phải từ phỏng đoán. Và runner — **bản vá việc 1** —
nói đúng cái đã xảy ra, trong khi bản cũ sẽ **im lặng** đúng ở dòng này:

```
[giao-dien] mã thoát THẬT 1
[giao-dien] PHẠM VI (in lại khi kết thúc): …
[giao-dien] CẢNH BÁO: máy chủ pid 49972 ĐÃ CHẾT GIỮA LƯỢT (trước khi bộ dọn tắt nó)
[giao-dien] máy chủ pid 49972 bị GIẾT BẰNG TÍN HIỆU: mã 137 = SIGKILL(9) — tín hiệu KHÔNG do bộ dọn gửi
[giao-dien] log máy chủ: 0 traceback · 1000 dòng · 8 dòng cuối (log đứt giữa dòng + 0 traceback
            ⇒ bị giết bằng tín hiệu, không phải lỗi mã):
```

**Đây là bản sao CHÍNH XÁC dấu vết của 3/9 lượt đỏ ở Phần A** — cùng loại: log đứt giữa dòng,
**0 traceback**, ca hỏng là `ERR_CONNECTION_REFUSED` (lượt này: **9** dòng), phần lớn ca còn lại
"did not run" vì `serial`. Khác duy nhất một điều: lần này **người giết là bộ đo của chính tôi**,
nên biết chắc nó là **tín hiệu từ ngoài tiến trình**.

### B.2.4 Ma trận BỐN tiến trình nền — 240 giây, để tách "sản phẩm" khỏi "cả phiên"

Nếu một cơ chế nào đó của môi trường giết tiến trình nền dài hơi, nó phải giết **cả những tiến
trình không liên quan gì tới sản phẩm**. Bốn tiến trình sống cùng một cửa sổ 240 s:

| tiến trình | có gì giống máy chủ thật | số phận trong 240 s |
|---|---|---|
| **P1** `sleep 600` | không tên giống, không cổng | **còn sống suốt 240 s** (pid 46322) |
| **P2** ngủ, đường dẫn `…/app/server.py` | **GIỐNG TÊN** (khớp `pkill -f app/server.py`), không cổng | **còn sống suốt 240 s** (pid 46323) |
| **P3** ngủ, **nghe cổng 19030** | không giống tên, **CÓ CỔNG trong dải 18xxx của runner** | **còn sống suốt 240 s** (pid 46324) |
| **P4** chính `app/server.py` **thật**, nền cô lập, **không tải** | giống tên + có cổng + **là sản phẩm** | **còn sống suốt 240 s** (pid 46370) |

Cả bốn bị **chính bộ đo** tắt lúc hết cửa sổ (`mã -15` = do bộ đo gửi) — tức **trong 240 s ấy
không có cơ chế nào giết tiến trình nền**, kể cả tiến trình *giống tên* hay *đang nghe cổng*.

### B.2.5 Kết luận việc 2 — cái gì ĐÃ BỊ LOẠI BẰNG SỐ, cái gì CHƯA BIẾT

| nghi phạm | phép đo của lượt này | kết luận |
|---|---|---|
| Cạn mô tả tệp (`ulimit -n`) | đỉnh **53** / trần **1048575** = **0,005 %** — cả 5 lượt đo đều 50–53, không leo thang | **LOẠI** |
| Bùng nổ tiến trình con / fork | `pgrep -P` = **0** ở mọi mẫu của mọi lượt | **LOẠI** |
| Cổng lạ / tranh cổng | mỗi lượt có **đúng một** cổng nghe, đúng cổng runner chọn (`18733`, `18441`, `18434`, `19863`, `19848`) | **LOẠI** |
| Watchdog "sống quá T giây thì giết" | sống **112,4–113,5 s** ở 4 lượt tải; sống **240 s** khi không tải (P4); không có ngưỡng nào bị chạm | **LOẠI** (với T ≤ 240 s) |
| Quét theo MẪU TÊN (`pkill -f 'app/server.py'`) trong phiên này | P2 **giống tên y hệt** vẫn sống đủ 240 s | **không xảy ra** trong cửa sổ đo |
| Sản phẩm tự chết (lỗi mã) | **0 traceback** ở mọi log; log lượt bị giết **đứt GIỮA DÒNG** ngay sau một `200`; log lượt xanh kết thúc bằng `200` lúc 00:34:30 (lượt kết thúc 00:34:32) | **LOẠI** |
| **Ai gửi tín hiệu** | **VẪN CHƯA BIẾT.** `dtrace` bị SIP chặn (*"dtrace: failed to initialize dtrace: Operation not permitted"*), `ps` bị sandbox chặn (*"/bin/ps: Operation not permitted"*) ⇒ **không nhìn được kẻ gửi**, và tài liệu này **không đoán** | **CHƯA ĐO ĐƯỢC** |

**Tỉ lệ, nói bằng số:** Phần A đo **3/9 lượt bị giết** (1/3). Lượt này: **0/7 lượt trọn bộ bị giết**
(6 lượt ghi được + 1 lượt chạy bị mất log, xem §B.4.1). Nếu tỉ lệ cũ còn hiệu lực thì xác suất
quan sát được 0 lượt chết trong 7 lượt là `(2/3)^7 ≈ 5,9 %` — **thấp**, nhưng **không đủ** để nói
"đã hết". Điều **đủ** để nói, và là điều Owner yêu cầu: **cái chết không phải do sản phẩm** —
sáu lượt `65/65` trên cùng cây, log máy chủ 0 traceback và trả lời `200` tới 2 giây trước khi lượt
kết thúc, còn dấu vết của lượt bị giết thì **tái lập được BẰNG MỘT TÍN HIỆU TỪ NGOÀI** (§B.2.3).

---

## B.3 — VIỆC 3: CHẠY LẠI TRỌN BỘ — TỪNG LƯỢT, ĐỦ CẢ ĐẠT LẪN HỎNG

Bảy lượt trọn bộ trong lượt làm việc này (cùng cây, cùng 65 ca, **đúng binary Chromium đã ghim**
`chromium_headless_shell-1194/…/headless_shell` · `Chromium 141.0.7390.37` ·
`sha256 a9752d88…fa3040`):

| # | giờ | lệnh | `chay.sh` | mã thoát | đạt / **hỏng** / bỏ qua / **không chạy** | máy chủ | phán quyết |
|---|---|---|---|---|---|---|---|
| 1 | 23:27:19→23:29:14 | `sh thu_giao_dien/chay.sh --reporter=list` | H1 `2f724e4d` | **0** | **65**/0/0/0 | sống tới hết lượt | **DAT** |
| 2 | ≈00:18:50→00:20:44 | `--do-chay-sh 1` (log bị **mất** — lỗi của bộ đo, §B.4.1) | H2 | (không ghi) | (không ghi — **KHÔNG tính là đạt**) | sống | *(không phán)* |
| 3 | 00:21:02→00:21:42 | `--do-chay-sh 1 --giet-luc 30` (**đối chứng dương**) | H2 | **1** | 15/**9**/0/**41** | **CHẾT ở 30,01 s** (`SIGKILL(9)`) | **HA_TANG_CHET** (cổng trả 3) |
| 4 | 00:25:00 | `--do-chay-sh 4` (không cờ thêm) | **H3 `d9278db6`** | **0** | **65**/0/0/0 | sống **112,6 s** | **DAT** |
| 5 | 00:26:53 | ″ | ″ | **0** | **65**/0/0/0 | sống **112,4 s** | **DAT** |
| 6 | 00:28:48 | ″ | ″ | **0** | **65**/0/0/0 | sống **113,5 s** | **DAT** |
| 7 | 00:30:42 | ″ | ″ | **0** | **65**/0/0/0 | sống **112,5 s** | **DAT** |
| 8 | 00:32:36→00:34:32 | `python3 app/thu/thu_g22_e2e.py` (CỔNG ĐẦY ĐỦ, tự dựng nền) | H3 | **0** | **65**/0/0/0 | sống, dọn SẠCH, `còn mồ côi: False` | **DAT** |

**Lượt #2 KHÔNG được tính là đạt** dù nó gần như chắc chắn xanh: log của nó bị mất vì lỗi thư mục
log của chính bộ đo (§B.4.1) — "không đo được" **không phải** "đạt", đúng luật của tài liệu này.

**Lượt #8 (cổng đầy đủ) là đối chứng hồi quy cho chính những gì tôi sửa** — cổng cũ vẫn phải nói
`DAT`, và nó nói:

```
  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 65/0/0/0/0  (ghim ĐẠT = 65)
  Chromium (GHIM)     : …/chromium_headless_shell-1194/chrome-mac/headless_shell
  Chromium phiên bản  : Chromium 141.0.7390.37
  Chromium sha256     : a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040  (146794928 byte)
  sha[:8] sản phẩm    : {"admin/ban_phim.js": "b5c7d741", "admin/billing.js": "00e8d4cd",
                         "admin/admin.js": "80bdc9fd", "app/server.py": "23515e6d"}
  ── PHÁN QUYẾT: DAT (mã thoát 0)
```

**Bộ tự kiểm của cổng: 26 ca (Phần A) → 31 ca, `exit 0`.** Năm ca mới ghim đúng những gì lượt này
thêm vào:

| ca | ghim điều gì | đối chứng |
|---|---|---|
| `e1` | `phat_hien_chet()`: dãy "sống → chết" cho ĐÚNG giây chết; dãy sống suốt cho `None`; **cổng ngừng trả lời trong khi tiến trình vẫn "sống"** cũng bị bắt | đối chứng âm + dương của phép đo cái chết |
| `e2` | `doc_dong_runner()`: log **thiếu** dòng PHẠM VI ⇒ `pham_vi = 0` (để bất biến ĐỎ ĐƯỢC); log đủ ⇒ `2`; đọc đúng cổng/pid/mã thoát/tín hiệu, và **không** gán cái chết từ ngoài cho bộ dọn | hai log THẬT chép nguyên văn |
| `e3` | dựng **cây tạm thiếu Playwright**, chạy `chay.sh` thật ⇒ thoát `2` **và** vẫn in dòng PHẠM VI | đối chứng dương của bản vá việc 1 |
| `e4` | dựng cây tạm **nền hỏng** ⇒ thoát `2`, có `NỀN KHÔNG DỰNG ĐƯỢC`, vẫn in PHẠM VI | đường thoát sớm thứ hai |
| `e5` | **đối chứng dương của BỘ ĐO**: dựng một tiến trình thật, đo được `fd` + **cổng đang nghe**, rồi **giết nó** và đòi bộ đo **bắt được cái chết** | ca này **ĐỎ ở lần chạy đầu** vì một lỗi thật của bộ đo — §B.4.2 |

```sh
$ python3 app/thu/thu_g22_e2e.py --tu-kiem
Ran 31 tests in 2.507s
OK
TỰ KIỂM: 31 ca · hỏng 0 · lỗi 0 · bỏ qua 0
```

---

## B.4 — HAI LỖI CỦA CHÍNH BỘ ĐO LƯỢT NÀY (do chạy nó mà lộ ra, đã vá)

### B.4.1 `--thu-muc-log` chưa tạo thư mục ⇒ mất trắng log của một lượt trọn bộ

Lượt đối chứng dương **đầu tiên** chết ngay sau khi runner khởi động:

```
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/ag06-do-doi-chung/luot-01.log'
```

Hệ quả **thật**: tiến trình `chay.sh` đã được sinh ra, chạy hết lượt trọn bộ, nhưng **log của nó
bị bỏ** (ẩu ra đường ống rồi mất) ⇒ một lượt chạy đã tiêu tốn ~2 phút mà **không để lại bằng
chứng**, và nó **không được tính là đạt** ở §B.3 (lượt #2). **Vá:** `os.makedirs(thu_muc_log,
exist_ok=True)` trước vòng lặp (kèm chú thích ngay tại dòng ấy).

### B.4.2 Bộ đọc ổ cắm đọc sai THỨ TỰ trường của `lsof` ⇒ ca `e5` ĐỎ

`lsof -F fTn` in **ba dòng liền nhau cho mỗi fd**: `f<fd>` → `n<địa chỉ>` → `TST=<trạng thái>`.
Bản đầu của `o_cam_tcp()` đòi thấy `TST=LISTEN` **trước** dòng `n`, nên **không bao giờ** thấy cổng
nào đang nghe — và ca `e5` đỏ đúng ở dòng `assertIn(str(cong), m1["nghe"])`. Nếu ca `e5` không tồn
tại, "cổng đang mở = 1" ở §B.2.2 sẽ là một **cột rỗng** mà không ai biết. **Vá:** gom theo fd rồi
mới xét trạng thái; `e5` ghim lại vĩnh viễn.

**Ba lỗi nữa của `chay.sh`** (đã liệt kê ở §B.1.3) cũng thuộc nhóm này: chúng chỉ lộ ra vì có
người **chạy** bản vá, không phải vì có người **đọc** nó.

---

## B.5 — TỆP ĐÃ SỬA/TẠO, VÀ **AG-00 PHẢI COMMIT HỘ**

### B.5.1 Tệp của lượt này

| tệp | trạng thái | sha256[:8] |
|---|---|---|
| `thu_giao_dien/chay.sh` | **SỬA** (2 lỗi báo cáo + 3 bản vá thông báo) | `d9278db6` |
| `app/thu/thu_g22_e2e.py` | **SỬA** (mục §G bộ đo giới hạn · 5 ca tự kiểm `e1`–`e5` · 2 chế độ CLI `--do-chay-sh`, `--tro-ngo`) | `9c631883` |
| `docs/G22_BANPHIM_E2E.md` | **SỬA** (Phần B này) | tự tham chiếu |

**KHÔNG sửa gì khác.** Bằng chứng bằng sha256, đo trên cây làm việc:

```
admin/ban_phim.js b5c7d741 · admin/billing.js 00e8d4cd · admin/admin.js 80bdc9fd · app/server.py 23515e6d
  → KHỚP đúng bản đã ghim ở §1 Phần A (bản AG-00 gộp)
10 tệp thu_giao_dien/*.spec.js: giữ nguyên sha (06_ban_phim.spec.js = 193ee9a8)
  → hai tệp .spec.js tạm dùng cho phép đo đã được XOÁ (đã kiểm: không còn tệp `_tam` nào)
```

### B.5.2 AG-00 PHẢI COMMIT HỘ — sandbox VẪN chặn ghi `.git`

Đo lại ở lượt này, không suy đoán:

```sh
touch /Users/viporder/Projects/vip-express-hub/.git/worktrees/g21-ag06-e2e/.ag06-probe
# touch: … Operation not permitted          ← exit 1 (đường dẫn .git nằm NGOÀI thư mục làm việc)
```

**Danh sách `git add` chính xác** (đúng ba tệp đang `M` trong `git status --porcelain`; `HEAD` hiện
là `05eecf1` — bản Phần A đã được gộp, nên Phần B cần một commit MỚI):

```sh
git add thu_giao_dien/chay.sh app/thu/thu_g22_e2e.py docs/G22_BANPHIM_E2E.md
```

---

## B.6 — CHƯA ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

* **Ai giết máy chủ ở 3/9 lượt Phần A — VẪN CHƯA BIẾT** (§B.2.5). Đã loại bằng số: cạn fd, tiến
  trình con, cổng lạ, watchdog theo thời gian sống, quét theo mẫu tên *trong phiên này*, và lỗi mã
  sản phẩm. `dtrace` bị SIP chặn, `ps` bị sandbox chặn ⇒ **không có cách nào nhìn thấy kẻ gửi tín
  hiệu từ trong phiên này**. Cái **đã** đạt được: dấu vết ấy **tái lập được** bằng một tín hiệu từ
  ngoài (§B.2.3), runner **nói ra** nó (§B.1), và cổng **phân loại** nó thành `HA_TANG_CHET` chứ
  không gán tội cho sản phẩm (§B.3 lượt #3).
* **Tỉ lệ 0/7 lượt bị giết ở lượt này KHÔNG chứng minh "đã hết"** — chỉ nói rằng với 7 lượt, nếu
  tỉ lệ cũ (1/3) còn hiệu lực thì xác suất quan sát như thế là ≈ 5,9 %. Muốn chắc phải có **nhiều
  lượt hơn** hoặc **nhìn được kẻ gửi tín hiệu** (ngoài phiên này).
* **Không đo được RSS/bộ nhớ theo tiến trình**: `ps` và `top` đều bị sandbox chặn
  (`/usr/bin/top: Operation not permitted`). Đĩa/bộ nhớ đã bị loại ở Phần A bằng phép đo khác.
* **Không đo được số LUỒNG** của máy chủ (cùng lý do). Đo được một **cận dưới** từ log của chính
  máy chủ: `Thread-2097` ở lượt cổng đầy đủ ⇒ ≈ 2097 luồng đã tạo trong ~110 s, 0 traceback.
* Chỉ **Chromium** (binary đã ghim), chỉ ba bề rộng 375/768/1280; **không** thiết bị cảm ứng thật,
  **không** trình đọc màn hình, **không** in/PDF thật, **không** Safari/Firefox.
* **Không** gọi ra hãng ở bất kỳ môi trường nào; **không** mở `CHO_PHEP_LIVE`; bind `127.0.0.1`;
  **không** đụng PostgreSQL; **không** deploy/tunnel/push; **không** credentials thật; **không** tự
  bấm duyệt sandbox.

## B.7 — TUÂN THỦ, TỰ KIỂM

| # | Luật | Cách đo của lượt này | Kết quả |
|---|---|---|---|
| 1 | Không gọi API hãng | mọi lượt đều trên nền cô lập + `VIP_HUB_BIND` chỉ loopback; ca `d3` đọc thẳng `CHO_PHEP_LIVE is False` và đòi sổ hãng KHÔNG rỗng | ✓ |
| 2 | Không push/deploy/tunnel | không lệnh nào ra ngoài; `git` chỉ ĐỌC (`rev-parse`, `show`, `status`), ghi `.git` bị chặn thì **báo AG-00** | ✓ |
| 3 | Không credentials thật | không tạo/đọc `.env`; tài khoản trong log đều là demo của nền cô lập | ✓ |
| 4 | Không giết theo MẪU TÊN | tắt theo **đúng PID**; đối chứng dương cũng `os.kill(pid, SIGKILL)` theo PID đã giữ; ma trận trò-ngo chỉ *quan sát* P2/P3 | ✓ |
| 5 | Không sửa ngoài vùng được ghi | §B.5.1: đúng 3 tệp, sản phẩm và 10 spec giữ nguyên sha; hai tệp `.spec.js` tạm đã xoá | ✓ |
| 6 | Không PG, không push, không tự duyệt sandbox | không chạm `:5432`; không tự vượt chặn nào | ✓ |

