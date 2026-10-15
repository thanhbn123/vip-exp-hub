# BÀN GIAO — VIP EXPRESS HUB, đóng băng sau G12

Người bàn giao: **AG-00 (Claude Opus 5)** · ngày **15/10/2026** · theo lệnh anh Thành:
*"a muốn chuyển sang orca cho deepseek làm tiếp e tạm dừng và đóng băng bàn giao"*.

Người nhận: **DeepSeek, làm trong Orca.**

> Tài liệu này **tự đứng được**. Người nhận không có ngữ cảnh hội thoại của phiên trước, nên
> mọi thứ cần biết nằm ở đây hoặc ở tệp mà đây trỏ tới. Đọc **mục 1, 2, 7** trước khi gõ lệnh nào.

---

## 1. MỐC ĐÓNG BĂNG — và chỗ làm việc

| | Giá trị |
|---|---|
| **Mốc đóng băng** | `f36b53075d65ddff8df7042608c7168722903a0a` |
| **Mốc MÃ đã nghiệm thu** | `936467b5e9d782dd3100e46fd38a58b1736c9e53` — toàn bộ 927 ca + 9.600 lượt đo đồng thời chạy trên đúng commit này. Mọi commit sau nó **chỉ là `docs/*.md`, 0 dòng mã** |
| **Nhánh** | `main` (ở `~/Projects/vip-express-hub`) · `Projects-vip-express-hub` (ở worktree Orca) — **cả hai đang cùng ở `f36b530`** |
| **Cây làm việc** | sạch, 0 tệp dở, 0 stash, ở **cả hai** nơi |
| **Remote** | **0** — chưa bao giờ push. Chỉ thị cấm (mục 17) |

### Chỗ làm việc của DeepSeek

```
~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
```

AG-00 đã **tiến thẳng** worktree đó từ `695ce6b` lên `f36b530` lúc bàn giao (nó đang lùi 3
commit, thiếu hẳn mục 5C + 11–13 + cả 4 tài liệu). Tiến thẳng thuần, 0 commit riêng, 0 xung đột.
**Đã chạy lại bộ thử NGAY TRONG worktree Orca: 927 ca, 0 hỏng, mã thoát 0** — không suy từ
lượt chạy ở `~/Projects/`, vì đường dẫn khác thì phải đo.

### HAI điều về worktree Orca phải biết ngay

1. **Không có `node_modules`** → **tầng 3 Playwright chưa chạy được ở đó.** Nguồn còn tại
   `~/code/veh4-g12-playwright/node_modules` (489MB). Nối vào, đừng tải lại:
   ```bash
   ln -s ~/code/veh4-g12-playwright/node_modules ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub/node_modules
   ```
   `.gitignore` đã chặn **cả hai** dạng `node_modules/` và `node_modules` — dạng có gạch chéo
   khớp **thư mục** chứ không khớp **symlink**, nên phải có cả hai.
   Trình duyệt nằm trong `node_modules/playwright-core/.local-browsers/chromium-1194`;
   `thu_giao_dien/chay.sh` đã đặt `PLAYWRIGHT_BROWSERS_PATH=0` để dùng bản đó.
   **KHÔNG dùng cache hệ thống** `~/Library/Caches/ms-playwright/` — nó có chromium 1148 và
   1243 **của dự án khác**. Đừng chạm vào nó.

2. **CSDL THẬT không nằm trong worktree Orca.** Nó chỉ có ở:
   ```
   ~/Projects/vip-express-hub/app/du-lieu/hub.db   (200.704 byte, đo 15/10)
   ```
   Worktree Orca **chưa có** `hub.db` — bộ thử ở đó tự dựng CSDL mới. **Đó là điều tốt**:
   làm ở Orca thì không có đường nào chạm vào dữ liệu thật. Giữ nguyên như vậy.
   Hợp đồng §24: **chỉ AG-00 chạy migration lên CSDL thật, và chỉ sau khi đã thử trên bản sao.**

---

## 2. CẤM — chỉ thị của anh Thành, còn hiệu lực nguyên vẹn

Không mục nào dưới đây đã được nới. Đừng tự suy diễn rằng việc được giao đồng nghĩa với quyền.

| Cấm | Ghi chú |
|---|---|
| **Push GitHub** | repo chưa có remote nào. Đừng thêm |
| **Triển khai VPS / staging** | `V-G11-01` chưa cấp |
| **Chuyển CSDL nghiệp vụ sang PostgreSQL** | chỉ thị mục 8. Kho nghiệp vụ **vẫn là SQLite** |
| **Sửa `vip_customs*` hoặc CSDL của dự án khác** | chỉ thị mục 9 |
| **Gọi API hãng thật** (J&T, Viettel Post, GHN, GHTK, Ninja) | cả 5 adapter khoá cứng `CHO_PHEP_LIVE = False`. Đừng mở |
| **Tạo đơn vận chuyển thật · thanh toán thật · chuyển tiền thật** | — |
| **Xoay khoá mã hoá thật** | chỉ thị mục 14, `V-13906-02` |
| **Ghi khoá ra VIP Vault** | chỉ thị mục 15, `V-13906-03` |
| **Sửa VIP AI Brain** | dự án khác, có phiên khác đang làm |
| **Đưa credentials vào Git** | `.gitignore` đã chặn `.env`, `.env.*`, giữ `.env.example` |
| **Xoá dữ liệu hiện tại** | `CLAUDE.md` §19: xoá gì cũng vào thùng rác, cấm xoá cứng |
| **Coi thử lại vô hạn là phương án** | chỉ thị mục 13 |
| **Tự tuyên bố production-ready** | chỉ thị mục 20. **Hệ này CHƯA production-ready** |

Và: **AI review không phải human review.** Bộ thử xanh không phải lời cho phép.

---

## 3. TRẠNG THÁI — làm xong tới đâu

**Cổng G00 → G12 đã qua.** 927 ca python (29 bộ) · 56 node · 36 HTTP · 41 E2E ·
27 Playwright Chromium thật · 9.600 lượt đo đồng thời 8 tiến trình. **0 hỏng, 0 bỏ qua.**

Báo cáo cuối G12: **[G12_FINAL_REPORT.md](G12_FINAL_REPORT.md)** — đọc §4 (bảy lỗi đã vá),
§7 (việc cần anh duyệt), §8 (việc còn lại đã đo mà chưa vá).

Bốn tài liệu của G12:
[G12_FINAL_REPORT.md](G12_FINAL_REPORT.md) ·
[POSTGRESQL_MIGRATION_PLAN.md](POSTGRESQL_MIGRATION_PLAN.md) ·
[DATABASE_CONCURRENCY_REPORT.md](DATABASE_CONCURRENCY_REPORT.md) ·
[PLAYWRIGHT_ACCEPTANCE.md](PLAYWRIGHT_ACCEPTANCE.md)

Hợp đồng giữa các làn: **[SHARED_CONTRACTS.md](SHARED_CONTRACTS.md)** — **§30 là luật mới,
đọc trước khi chạm vào bất cứ lượt ghi CSDL nào.**

---

## 4. CHẠY LẠI — bốn lệnh

```bash
cd ~/orca/workspaces/vip-express-hub/Projects-vip-express-hub
```

```bash
sh app/thu/chay_tat_ca.sh
```
Hồi quy đầy đủ: 927 ca python + 2 tầng frontend + E2E. ~41 giây. In **phạm vi đã đo** và
**cái gì nằm ngoài** ở cuối — đọc khối đó, đừng chỉ đọc con số.

```bash
sh thu_giao_dien/chay.sh
```
Tầng 3 Chromium thật, 27 ca, ~34 giây. Cần `node_modules` (xem mục 1).

```bash
python3 app/thu/dong_thoi/chay.py
```
Đo đồng thời **8 tiến trình hệ điều hành thật × 400 phép × 3 ca**. Đổi quy mô bằng
`VIP_SO_TT` và `VIP_SO_PHEP`.

---

## 5. BẢY ĐIỀU VỀ SQLite ĐÃ ĐO — đừng suy lại, mỗi điều từng làm hỏng một thứ

| Điều | Đo được trên py 3.9.6 + SQLite 3.51.0 |
|---|---|
| `RAISE(ABORT)` của trigger | huỷ **CÂU**, **KHÔNG** huỷ giao dịch — câu sau vẫn commit. PostgreSQL thì `RAISE EXCEPTION` huỷ cả giao dịch |
| `executescript()` | **tự COMMIT** giao dịch đang mở, lặng lẽ. Dùng `migrate.chay_ddl_trong_giao_dich()` |
| `with kn:` của python | mở giao dịch cho DML, **KHÔNG** cho `CREATE`/`ALTER` |
| `BEGIN IMMEDIATE` | **nổ** nếu python đã tự mở giao dịch; chỉ dùng được khi `isolation_level=None` |
| `SAVEPOINT` trần | mở giao dịch **HOÃN** — đọc-rồi-ghi qua nhiều tiến trình nhận `SQLITE_BUSY_SNAPSHOT` **NGAY**, `busy_timeout` **không** chờ ca này |
| `PRAGMA foreign_keys` | **bị bỏ qua** nếu đặt trong giao dịch, **không báo lỗi** |
| `PRAGMA journal_mode=WAL` | cần khoá độc quyền; `busy_timeout` **không** phủ nó |

### Ba luật ghi CSDL — có chốt chặn, gỡ ra là bộ thử đỏ

1. **Chỉ `csdl.py` được `import sqlite3`.** Mã nghiệp vụ dùng `csdl.Row` · `csdl.LoiCSDL` ·
   `csdl.LoiToanVen` · `csdl.LoiVanHanh` · `csdl.ket_noi()`.
   Chốt: `thu_bien_driver.py` a1 (dò bằng **AST**, không grep).
2. **Nhiều câu ghi phải thành một đơn vị thì bọc `csdl.giao_dich()`.**
   `with csdl.khoa_ghi:` **KHÔNG** phải giao dịch — nó chỉ chặn hai thread giẫm nhau.
   Chốt: `thu_giao_dich.py` c1, c2.
3. **CẤM `kn.commit()` / `kn.rollback()` trên kết nối của `csdl.mo()`** — kết nối đó ở chế độ
   tường minh nên hai lệnh ấy là **LỆNH RỖNG**, rỗng mà không báo lỗi. Muốn gộp thì
   `giao_dich()`; muốn bỏ một câu đã ghi thì **XOÁ theo id**.
   Chốt: `thu_bien_driver.py` a5. Miễn trừ: `csdl.py`, `migrate.py`.

---

## 6. VIỆC TIẾP THEO — xếp theo thứ tự nên làm

### 6.1 Làm được ngay, không cần anh duyệt

| Mã | Việc | Vì sao nên làm trước |
|---|---|---|
| **V-13912** | Bọc `csdl.giao_dich()` cho **5 khối ghi còn lại**: `don_hang.py:944` (3 câu) · `tai_chinh.py:673` (2 câu) · `usage.py:220` · `don_hang.py:854` (gọi `_ghi_lich_su`) · `tai_chinh.py:385` `ghi_nhat_ky` (đọc-rồi-ghi móc băm) | Cùng **đúng khuôn** đã làm hỏng 3 lần và lần nào cũng lệch tiền. §12.2 bước 4 đã quét 30 khối, vá 2 nặng nhất, đây là phần còn lại. `billing.py:68/119` **KHÔNG** phải lỗi — `INSERT OR IGNORE` + `UPDATE`-có-trần, bước đầu idempotent |
| **V-13914** | Đo 3 ca đồng thời chưa phủ: (a) tiến trình bị tắt **GIỮA** giao dịch · (b) máy chủ HTTP thật **dưới tải** (bàn đo hiện gọi thẳng hàm, không qua `ThreadingHTTPServer`) · (c) trần chống lạm dụng nhiều tiến trình | (c) là **điều kiện kích hoạt số 2** của kế hoạch PostgreSQL |
| — | Cắm route cho `truy_van.py` + đưa `DDL_G12Q` vào migration **v9** (AG-01 đã viết, chưa gộp vào đường chạy) | lớp lọc + phân trang ở máy chủ đã có mã, chưa có đường vào |
| — | 21 mã trạng thái Viettel Post (AG-03 khảo sát, chưa áp) | — |
| — | **P-3** `admin/finance.js` dòng 19–20 ghi *"chưa có đường API nào"* trong khi 17 dòng route đã cắm — chú thích lạc hậu · **P-4** `API_DANG_DUNG_TC` có **2 dòng trùng** nên "17 route" đếm từ đó **cao hơn thực tế 2**, thật ra **15** đường rời nhau | nhỏ, nhưng là tài liệu nói sai về hệ thống |

### 6.2 Chờ anh Thành — đừng tự làm

| Mã | Việc |
|---|---|
| **V-13910** (cao) | **16/17 màn khai ở đợt 3 KHÔNG tồn tại trong giao diện.** Năm module `admin/{finance,billing,carrier_health,ai,health}.js` là **mã chưa ai gọi**: `grep innerHTML|document.` ra **0 ở cả năm**, và `admin.js` **không** tham chiếu màn nào. Tầng 1 kiểm chúng như hàm thuần nên chúng xanh, nhưng **không người dùng nào với tới được** |
| **V-13911** (cao) | Giao diện quản trị **không dùng được bằng bàn phím**: 10 mục menu + Đăng xuất là `<a>` không `href`/`tabindex`/`role`; **15 lượt Tab không rời `body`**. Thêm ca canh **cùng lượt** với bản vá, không trước |
| **V-13913** | Cài Docker (`brew install --cask colima docker docker-compose`). `Dockerfile` + `docker-compose.yml` đã viết nhưng **chưa chạy lượt nào** |
| **V-13906-04/05** | Gửi **11 câu hỏi ưu tiên** cho J&T. Chốt chặn ánh xạ `area` đang **khoá cứng** ở mọi chế độ khác `mock` (quyết định D-9: *"chưa chốt cách ánh xạ cho đến khi hãng xác nhận"*) |
| — | Chạy chặng 1–2 của kế hoạch PostgreSQL. **Khuyến nghị của AG-00: CHƯA.** Số đo đồng thời cho thấy SQLite còn dư sức; chặng 0 vừa xong đã mang gần hết lợi ích kiến trúc mà không mang rủi ro dữ liệu nào |

---

## 7. BA CÁI BẪY AG-00 ĐÃ SA VÀO — đọc để không lặp lại

Ghi ra vì cả ba đều **không báo lỗi gì**, và cả ba làm mất thời gian thật.

### 7.1 Thứ dùng để kiểm chứng tự nó nói sai (4 ca trong một lượt)

- Bộ chạy hồi quy phán ĐẠT/HỎNG bằng **chữ `OK` trong output** (nếp unittest) → báo **hỏng giả**
  cho bộ thử không dùng unittest. Đã hỏng **lần thứ hai cùng kiểu** → đổi sang phán bằng
  **mã thoát + dấu vết đã chạy + số ca > 0**. Hướng sai nguy hiểm hơn ở mặt còn lại: bộ thử
  in `OK` rồi thoát khác 0 sẽ được phán ĐẠT.
- `thu_postgres.py` hiện dấu ✓ trong **mọi** báo cáo trước mà chạy **đúng 0 ca** (nó tự bỏ qua
  trừ khi bật biến môi trường). Ai đọc *"27 bộ đạt"* đều tưởng PostgreSQL đã được phủ.
  Nay bật mặc định, và bộ chạy có **phán quyết thứ ba BỎ QUA**, không gộp vào ĐẠT.
- Hai bộ thử **che mã thoát của chính nó** (`unittest.main(exit=False)` rồi in thêm) → luôn
  thoát 0 kể cả khi có ca hỏng.
- Bộ thử đồng thời của **chính AG-00** sai **hai lần**: thiếu **vạch xuất phát chung** nên
  6/6 tiến trình báo *"nâng=True, 0,20 giây"* — nhìn như không ai phải chờ khoá, thật ra chúng
  chạy nối đuôi và phép đo **không chạm tới khoá lần nào**; rồi ca `a1` chỉ tính **một** trong
  **hai** đường nhường chính đáng nên báo hỏng 3/5 lượt. **Tin nó thì đã đi "sửa" mã đang chạy đúng.**

**Luật rút ra:** trước khi tin một con số, hỏi *công cụ nào tạo ra nó, nó thật sự kiểm cái gì,
và cái gì nằm NGOÀI cái nó kiểm.* Bộ thử nào cũng cần một ca **tự kiểm chính bộ dò**
(xem `thu_bien_driver.py` ca a4).

### 7.2 Vá mò trước khi đo đúng chỗ

Lỗi *"một thread tự khoá chính mình qua hai kết nối"* mất **ba lượt vá sai**:
tưởng `journal_mode=WAL` là thủ phạm (sai) · tưởng thiếu `khoa_ghi` (đúng một phần, 91s còn
61s) · **nâng `busy_timeout` từ 5 lên 30 giây → LÀM TỆ HƠN**, vì nó biến một lỗi **nhanh**
thành một lượt **ngồi chờ**.

Chỉ khi đo **thời gian TỪNG PHA trong từng thread** mới thấy con số lượng tử hoá theo đúng
`busy_timeout` (0,005 · 30,35 · 30,35 · 60,70 · … · 121,43 giây) — lúc đó nguyên nhân tự hiện ra.

**Luật rút ra:** đo **từng pha**, không đo tổng. Tổng thời gian không nói được nguyên nhân.

### 7.3 Tệp không tự ghi được SHA của chính commit chứa nó

`G12_FINAL_REPORT.md` §1 ghi SHA làm FINAL SHA → commit tệp đó đổi SHA → đính chính → lượt
đính chính lại đổi SHA lần nữa. **Hai lượt sửa, cả hai tự làm mình sai.**
Nay §1 ghi **mốc MÃ** (ổn định, kiểm được: 0 dòng mã sau nó) và để người đọc tự đo mốc cây
bằng `git rev-parse HEAD`.

**Luật rút ra** (`CLAUDE.md` §12.1 luật 4): trường nào là **dữ kiện đo được** — giờ, số tệp,
mã thoát, SHA — thì phải **lấy từ lệnh**, không điền vào tệp.

---

## 8. Dọn dẹp lúc đóng băng — đã làm

| Việc | Trạng thái |
|---|---|
| Tắt máy chủ thử `python3 -m http.server 8899` của phiên trước | **xong** — tắt theo **PID 23435 đã nhìn tận mắt** (`ps -p` in cả dòng lệnh), không theo mẫu tên. `CLAUDE.md` §16.7 **cấm** `pkill -f` / `killall` trên mọi máy của vault |
| Tiến thẳng worktree Orca `695ce6b` → `f36b530` | **xong**, đã chạy lại 927 ca tại đó |
| Cây làm việc sạch ở cả hai nơi | **xong** — 0 tệp dở, 0 stash |
| Nhật ký vault | **xong** — `nhat-ky/ngay/2026-10-15.md` mục 26, `V-13910`→`V-13914`, `wiki/log.md`, dòng khai phiên |

### 5 worktree agent của G12 — CHƯA gỡ, cố ý

```
~/code/veh4-g12-carrier      agent/g12-carrier      eec95d7
~/code/veh4-g12-data         agent/g12-data         6f71414
~/code/veh4-g12-keyops       agent/g12-keyops       8d81ae9
~/code/veh4-g12-playwright   agent/g12-playwright   cccd275   ← node_modules 489MB ở đây
~/code/veh4-g12-query        agent/g12-query        4a68017
```

Cả 5 **đã gộp vào `main`**. Giữ lại vì `veh4-g12-playwright` đang là **nguồn `node_modules`
duy nhất** — gỡ nó là mất 489MB phải tải lại. Gỡ thì chép `node_modules` ra chỗ khác trước.

23 nhánh `agent/*` giữ làm dấu vết, đừng xoá.

---

## 9. Luật vault còn hiệu lực

Mã nằm **NGOÀI vault** (`~/Projects/vip-express-hub`), vault chỉ ghi sổ. Nhưng `CLAUDE.md`
vẫn áp cho cách làm việc:

- **§12** chống bịa · **§12.1** thứ dùng để kiểm chứng phải tự nó đáng tin, và mọi câu *"0 lỗi"*
  phải nêu **công cụ nào · phạm vi nào · cái gì nằm ngoài** · **§12.2** một cấu trúc hỏng
  **lần thứ hai cùng kiểu** thì **đổi cấu trúc**, đừng vá đúng thêm một lần nữa.
- **§15** mọi việc phải vào sổ; việc dở **bắt buộc** sinh mã `V-xxx`.
- **§16** nhiều phiên song song: dải mã việc của phiên này là **V-13900 → V-13949**, đã cấp tới
  **V-13914**, còn trống **V-13915 → V-13949**. Chiếm dải mới thì khai ở
  `nhat-ky/phien-song-song.md` rồi **đọc lại** xem có ai vừa chiếm cùng dải.
- **§16.7** chỉ tắt tiến trình theo **PID đã nhìn tận mắt**. `pkill -f` và `killall` bị **móc
  chặn** chặn ở mọi phiên mở tại gốc vault.
- **§19** xoá gì cũng vào thùng rác, **cấm xoá cứng**.

---

## 10. Một câu cho người nhận

Hệ này **chạy được và đo được**, nhưng **chưa production-ready**, và chỗ yếu nhất **không**
nằm ở CSDL — nó nằm ở giao diện: **16/17 màn của đợt 3 là mã chưa ai gọi** (V-13910), và màn
quản trị **không dùng được bằng bàn phím** (V-13911). Bộ thử tầng 1 kiểm chúng như hàm thuần
nên chúng **xanh**, và đó đúng là lý do phải có tầng 3.

Nếu chỉ làm được một việc, làm **V-13912** — bọc giao dịch cho 5 khối ghi còn lại. Đó là cùng
đúng một khuôn đã làm lệch tiền **ba lần** trong lượt vừa rồi.
