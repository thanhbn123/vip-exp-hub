# G22 · AG-06 — CỔNG E2E TẦNG 3: **65/65**, VÀ PHÂN BIỆT *"SẢN PHẨM HỎNG"* VỚI *"NỀN CHẾT"*

**Nền đo:** `integration/g20` @ `7344c020abad562dafb593c4234d5e1f9ecfd18c` — đúng cái cây mà điều
phối gọi là *"integration/g21 @ 7344c02"*. Nội dung đã vào cây làm việc và **xác minh bằng sha256
từng tệp** (§1).
**Người làm:** AG-06 · wave G22. **Vùng được ghi:** `admin/ban_phim.js` · `admin/admin.js` ·
`thu_giao_dien/*.spec.js` · `app/thu/thu_g22_e2e.py` (mới) · `docs/G22_BANPHIM_E2E.md` (mới).
**Lượt này KHÔNG sửa một dòng mã sản phẩm nào** — chỉ thêm cổng đo và tài liệu.

**Lệnh dựng lại toàn bộ số trong tài liệu này:**

```sh
python3 app/thu/thu_g22_e2e.py --tu-kiem        # 26 ca tự kiểm của cổng, exit 0
python3 app/thu/thu_g22_e2e.py --ghim-chromium  # đường dẫn + phiên bản + sha256 binary
python3 app/thu/thu_g22_e2e.py                  # CỔNG ĐẦY ĐỦ: 65 ca, exit 0
sh thu_giao_dien/chay.sh                        # bộ chạy cũ — ĐỌC §3 TRƯỚC KHI TIN
```

---

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
