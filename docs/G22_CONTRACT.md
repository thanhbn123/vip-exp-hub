# G22 · AGENT 02 — HỢP ĐỒNG TEST (VÒNG 2 · TÍCH HỢP SAU 5 AGENT)

> **Vai:** AGENT 02 · G22 TEST CONTRACT · `task_790aa6314621` · dispatch `ctx_ca352ff451e7`.
> **Nền đo:** `HEAD = dd788fc01c5c7e7b4da93e2a216aa5d4fe251d0b` · tree
> `96285874039248115549c647caa168ec615ce7f2` (worktree `g22-a2-contract`).
> **KHÔNG** dùng `main` (`de740dc` — không chứa G13–G22). **KHÔNG** mở G23.
> **Phạm vi ghi:** `app/thu/thu_qa_g22.py` (sửa) · `docs/G22_CONTRACT.md` (tài liệu này).
> **CAM KẾT:** không push · không deploy · không tunnel · không credentials thật · không API
> production · không sửa CSDL thật · không tự bấm duyệt sandbox · không ghi `.git` của worktree.
> **D-8 / `OWNER_ACTIONS C4` (PostgreSQL) = BLOCKED OWNER** — vòng này không đo, không sửa,
> không ép xanh phần đó.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

| | TRƯỚC — vòng 1 (tôi đo lại trên chính cây này) | SAU — vòng 2 |
|---|---|---|
| Lệnh | `python3 app/thu/thu_qa_g22.py` | `python3 app/thu/thu_qa_g22.py` |
| `Ran` | **24** | **24** |
| PASS (tính = Ran − FAIL − SKIP) | **19** | **22** = 24 − 1 − 1 |
| FAIL | **3** (`A1`, `B2`, `B3`) | **1** (`B2`) |
| ERROR | 0 | 0 |
| SKIP | **2** (`E1` môi trường · `Z9` mồi) | **1** (`Z9` mồi) |
| **EXIT CODE** | **1** | **1** |
| Bằng chứng | `/tmp/g22-a2-logs/truoc_khi_sua.log` | `/tmp/g22-a2-logs/sau_khi_sua_lan3.log` |

Ba chuyển biến ĐO ĐƯỢC của vòng 2:

1. **`A1` ĐỎ → XANH.** Hai nguyên nhân độc lập đã xử lý: (a) `tree_hien_tai()` đo
   `write-tree` TƯƠNG ĐƯƠNG bằng index tạm + ODB tạm + alternates chỉ-đọc (AGENT 03,
   `docs/G22_A1_GIT.md` §3.3); (b) ghim `NEN_SHA`/`TREE_NEN` cập nhật theo nền HIỆN TẠI, và
   `A1` thêm vế tự kiểm `NEN_SHA^{tree} == TREE_NEN`.
2. **`B3` ĐỎ → XANH.** `SO_DO` của bàn phím không còn ghim `(7,0,0)` của lượt cũ; số ca được
   đếm bằng chính Playwright (`--list`) = **8**, chạy thật **8/8**, `exit 0`.
3. **`E1` SKIP → XANH.** Vì `HEAD` nay ĐÚNG là nền, ba cổng "cây sạch" phán quyết được:
   **3/3 XANH**, kèm đối chứng clone + tiêm **3/3 ĐỎ-THẬT**.

**`EXIT 1` còn lại KHÔNG phải lỗi của vòng 2 và KHÔNG được giả xanh:** `B2` đo được
`(57, 1, 7)` — một ca hỏng CÓ SẴN (`01_luong_chinh.spec.js:36`, ca 03) và 7 ca kế tiếp không
chạy vì tệp đó đặt `serial`. Cổng giữ nguyên `(65,0,0)`; tôi **không** hạ cổng, **không** đổi
`SO_DO` thành `(57,1,7)`, **không** thêm `skipTest`. Xem §3 — chủ sở hữu: **AGENT 01 /
AG-06 FRONTEND**.

---

## 1. LỆNH THẬT + MÃ THOÁT THẬT (đọc NGAY sau lệnh, không qua ống)

```sh
# TRƯỚC khi sửa — tái hiện đúng mốc vòng 1:
$ python3 app/thu/thu_qa_g22.py
# → Ran 24 tests in 23.533s
# → FAILED (failures=3, skipped=2)
# → EXIT 1   (A1, B2, B3 hỏng; E1, Z9 bỏ qua)

# SAU khi sửa — toàn bộ bộ kiểm:
$ python3 app/thu/thu_qa_g22.py
# → Ran 24 tests in 178.746s
# → FAILED (failures=1, skipped=1)
# → EXIT 1   (chỉ còn B2 — lỗi CÓ SẴN, ngoài phạm vi vá của vòng này)

# Các nhóm chạy riêng trong vòng 2 (log thô cùng thư mục):
$ python3 app/thu/thu_qa_g22.py A_Nen          # Ran 4 · OK   · EXIT 0
$ python3 app/thu/thu_qa_g22.py C_BanPhim      # Ran 3 · FAILED (failures=1) · EXIT 1
$ python3 app/thu/thu_qa_g22.py E_CaySach      # Ran 2 · OK (skipped=0) · EXIT 0
```

Log thô (máy đo): `/tmp/g22-a2-logs/truoc_khi_sua.log`, `sau_khi_sua.log`,
`c_banphim.log`, `e_caysach.log`. Log E2E đầy đủ:
`/var/folders/v1/443y_fys65vflj24_rjw9x_w0000gn/T/veh_g22_ag01_qa/e2e_lan_nay.txt`.

**sha256 tệp bộ kiểm sau khi sửa:**
`4cf9a7325c38fe3368c860208a88570f35530c96c09c285795e7a0dcb66ffbf0`.
`git status`: đúng hai tệp — `M app/thu/thu_qa_g22.py` + `M docs/G22_CONTRACT.md`.

---

## 2. HAI PHÁT HIỆN ĐƯỢC ÁP VÀO TỆP NÀY

### 2.1 `A1` — HAI nguyên nhân, không phải một (AGENT 03 · `docs/G22_A1_GIT.md`)

**(a) MÔI TRƯỜNG — `git write-tree` trần bị chặn GHI.** Gitdir của worktree là
`/Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a2-contract`, NGOÀI vùng sandbox
cho ghi; `git write-tree` trần trả `rc=128` (`index.lock: Operation not permitted`). Vòng 2 thay
`tree_hien_tai()` bằng đoạn §3.3 của AGENT 03:

```
<gitdir>/index          --copy-->  <tmp>/index            (GIT_INDEX_FILE)
<tmp>/objects           <--ghi--   write-tree            (GIT_OBJECT_DIRECTORY)
<common>/objects        --đọc-->   object cũ             (GIT_ALTERNATE_OBJECT_DIRECTORIES)
```

ĐO ĐƯỢC trong lượt chạy cuối:

```
[A1] HEAD=dd788fc01c5c · write-tree (index tạm)=962858740392 · 380 tệp theo dõi
index THẬT: sha256 trước=de647d533b039fe5 · sau=de647d533b039fe5 · index.lock trước=False sau=False
```

`de647d53…` là sha256 index của **worktree này**; `283acae…` trong tài liệu AGENT 03 là index
của **worktree `g22-a3-gitsandbox`** — hai worktree, hai index, cùng một kết quả đo `9628587`.

**(b) GHIM CŨ — sửa môi trường mà giữ ghim cũ thì `A1` VẪN ĐỎ.** Ghim vòng 1 là
`3b7e93b/37079aa8` (cây của LƯỢT TRƯỚC); nền vòng 2 là HEAD `dd788fc`, cây `9628587`.
Vòng 2 cập nhật:

```python
NEN_SHA  = "dd788fc01c5c7e7b4da93e2a216aa5d4fe251d0b"
TREE_NEN = "96285874039248115549c647caa168ec615ce7f2"
```

và `A1` thêm vế **GHIM**: `git rev-parse NEN_SHA^{tree}` phải bằng `TREE_NEN`. Ghim lệch ⇒
`A1` báo **lỗi GHIM**, không bị báo nhầm thành lỗi môi trường (đúng đề nghị §5 của AGENT 03).

**(c) ĐỐI CHỨNG DƯƠNG — phép đo KHÔNG mù.** Nhúng ngay trong `A1` phép tiêm của AGENT 03 §3.4:

```
ĐỐI CHỨNG DƯƠNG: tiêm `__tiem_g22.txt` vào BẢN SAO index
                 → tree 9628587 → 44025342f53b · rc=0
index THẬT: sha256 trước = sau = de647d533b039fe5 · index.lock trước=sau=False
```

Tức là: cùng phép đo, tiêm một mục thì cây **ĐỔI**, còn index thật **KHÔNG đổi** và **KHÔNG**
sinh lock. Nếu `tree_hien_tai()` trả hằng số hoặc đọc nhầm cây, vế này sẽ bắt được.

> **Lưu ý cho lượt sau:** khi AG-00 commit hai tệp của vòng 2, `HEAD` sẽ nhích sang commit mới
> và `A1` sẽ (ĐÚNG) báo **GHIM STALE** cho tới khi ghim được cập nhật theo nền mới. Đó là hành
> vi mong muốn — ghim là mốc của lượt, không phải hằng số vĩnh viễn.

### 2.2 `SO_DO` của `C_BanPhim` — ghim `(51,0,0)`/`(7,0,0)` đã STALE

Cây hiện tại có **65 ca / 8 ca bàn phím**, không phải 51/7. Đây là **sự thật môi trường của một
lượt chạy cũ** (họ H5/N-G19-04), không phải bất biến. Vòng 2:

* **Đếm bằng chính Playwright:** `npx playwright test --list` → `Total: 65 tests in 10 files`,
  trong đó `06_ban_phim.spec.js` = **8**. Đây là nguồn sự thật vì nó tính cả ca SINH TRONG VÒNG
  LẶP mà đếm chuỗi `test(` sẽ đếm sai: `02_bo_cuc.spec.js` khai 1 ca × 3 bề rộng,
  `03_quyen.spec.js` khai 1 ca × 3 vai trò — quét `^\s*test(` ra 62 (còn đếm nhầm một lời gọi
  `test.skip` bên trong ca), còn Playwright ra **65**.
* **`SO_DO` suy từ số đó**, không dán một con số mới:

```python
"e2e-ban-phim": {"nen": (0, 8, 0),  "dong": (8, 0, 0)}
"e2e-toan-bo":  {"nen": (0, 8, 57), "dong": (65, 0, 0)}
```

  (`nen` = hình dạng khi thiếu nhị phân, suy từ số đo G21 `(0,7,44)` quy theo 65/8 hiện tại;
  `dong` = cả bộ sạch, suy trực tiếp từ `--list`.)
* **Đổi tên cho khỏi nói dối:** khóa `e2e-ban-phim-7` → `e2e-ban-phim`; ca
  `test_b3_e2e_bay_ca_ban_phim_chay_that` → `test_b3_e2e_tam_ca_ban_phim_chay_that`. **Không xoá
  ca nào**, `Ran` vẫn 24.
* **HAI đối chứng âm** (đề bài đòi "hạ một ca xuống ⇒ cổng PHẢI ĐỎ"):
  * bỏ đúng 1 dòng khai ca trong **bản sao TẠM** của `06_ban_phim.spec.js` ⇒ bộ đếm tĩnh
    `8 → 7` (và bộ đếm tĩnh phải khớp `--list` trước khi được tin);
  * hạ 1 ca trong **báo cáo** ⇒ `(7,0,0)` với bàn phím / `(64,0,0)` với toàn bộ ⇒ phân quyết
    `NUA_VOI` ⇒ cổng ĐỎ.

ĐO ĐƯỢC (lượt cuối):

```
[B2] số ca DO PLAYWRIGHT LIỆT KÊ (`--list`): 65 ca / 10 tệp spec · bàn phím=8 ca
     (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (57, 1, 0, 7) · tổng báo cáo = 65
     đối chứng âm: hạ 1 ca → (64, 0, 0) → ĐỎ (đòi ĐỎ)          → phân quyết: NUA_VOI
[B3] `--list`=8 · đối chiếu đếm dòng khai ca=8
     đối chứng âm bộ đếm: bỏ 1 dòng khai ca trong BẢN SAO TẠM → 8 → 7 ca
     mã thoát THẬT = 0 · (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (8, 0, 0, 0)
     đối chứng âm: hạ 1 ca → (7, 0, 0) → ĐỎ                 → phân quyết: DONG
```

### 2.3 Chromium — nhị phân, sha256, và một việc hạ tầng phải KHAI

Đường đề bài ghim và đường thực tế đã kiểm:

| Thành phần | ĐO ĐƯỢC |
|---|---|
| `chromium_headless_shell-1194/chrome-mac/headless_shell` (nhị phân `chay.sh` dùng) | CÓ · `Chromium 141.0.7390.37` · sha256 **`a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040`** = đúng ghim đề bài |
| `chromium-1194/chrome-mac/Chromium.app/.../Chromium` (đường thứ hai) | CÓ · `Chromium 141.0.7390.37` · sha256 `a01de8bb11d24acc6f91848415c9df9744965bea7fd58763f2930d4f280d5b84` |
| `node_modules/playwright-core/.local-browsers` **lúc bắt đầu vòng 2** | **KHÔNG TỒN TẠI** ⇒ nếu chạy ngay, `chay.sh` báo `Executable doesn't exist` và B2/B3 là "KHÔNG CHẠY ĐƯỢC" (một KẾT QUẢ, không phải skip) |

**Việc hạ tầng đã làm, khai rõ:** tôi tạo lại **symlink**
`node_modules/playwright-core/.local-browsers` →
`/Users/viporder/orca/workspaces/vip-express-hub/Projects-vip-express-hub/node_modules/playwright-core/.local-browsers`,
đúng hướng dẫn `docs/G21_BANPHIM_E2E.md` §10. `node_modules/` **không được git theo dõi**;
`git status` không đổi; **không** tệp sản phẩm nào bị sửa. Không có symlink này thì B1/B2/B3
phải báo "KHÔNG CHẠY ĐƯỢC" chứ **không** được skip. B1 nay kiểm cả `headless_shell` +
sha256 + phiên bản, không chỉ "thấy tệp là tin".

---

## 3. BẢNG "CA NÀO ĐỎ / VÌ SAO / AI SỞ HỮU"

| Ca | Vòng 2 | Nhóm | Bằng chứng | Ai sở hữu việc sửa |
|---|---|---|---|---|
| `A1` `test_a1_cay_dung_bang_cay_cua_nen` | **PASS** | Đã sửa trong vòng 2: **môi trường** (sandbox chặn `write-tree`) + **ghim cũ** (3b7e93b/37079aa8) | tree index tạm = `9628587` = `TREE_NEN`; GHIM `dd788fc^{tree}` = `9628587`; tiêm index ⇒ `44025342f53b`, index thật không đổi | **AGENT 02** (tệp kiểm) · **AGENT 03** (phương pháp đo, `docs/G22_A1_GIT.md`) — ĐÃ XONG |
| `B2` `test_b2_chay_e2e_toan_bo_that` | **FAIL** | **LỖI CÓ SẴN** (không do vòng 2): ca `01_luong_chinh.spec.js:36` **03 — bộ lọc nâng cao** timeout 10 s ở `waitForFunction`; 7 ca kế tiếp `did not run` vì tệp đặt `serial` | `(57, 1, 7)` · tổng 65 = `--list`; cổng `(65,0,0)` ⇒ `NUA_VOI`; log E2E dẫn ở §1. Tệp spec + `admin/` của ca này **giống hệt HEAD** (`git status` chỉ có 2 tệp của AGENT 02) ⇒ vòng 2 không thể là nguyên nhân | **AGENT 01 / AG-06 FRONTEND** — sửa ca 03 (hoặc hành vi lọc) rồi chạy lại `01_luong_chinh.spec.js`; sau đó 7 ca `did not run` mới có số đo |
| `B3` `test_b3_e2e_tam_ca_ban_phim_chay_that` | **PASS** | Đã sửa: **ghim cũ** `(7,0,0)` → `(8,0,0)`; số ca đếm từ `--list` | chạy thật `8/8`, `exit 0`; hai đối chứng âm ĐỎ đúng | **AGENT 02** — ĐÃ XONG |
| `E1` `test_e1_ba_cong_cay_sach_chay_that` | **PASS** | Trước là **SKIP vì môi trường/ghim** (`HEAD ≠ nền`); nay `HEAD == nền` nên phán quyết được | cây này 3/3 XANH; clone tại nền: sạch 3/3 XANH, tiêm `admin/__tiem_g22.js` 3/3 `DO_THAT` | **AGENT 02** — ĐÃ XONG |
| `Z9` `test_z9_ca_CO_Y_HONG_de_tu_kiem` | **SKIP (có chủ đích)** | Không phải lỗi: đây là MỒI cho `Z5`, chỉ chạy trong tiến trình con | `Z5` đọc mã thoát con = 1 với mồi hỏng; `Z1` 10/10 nhóm đã chạy đối chứng | **AGENT 02** — thiết kế giữ nguyên |

`PASS 22` gồm 19 ca vốn đã xanh ở vòng 1 + `A1` + `B3` + `E1` (E1 trước là SKIP, nay chạy và
xanh). Không ca nào bị xoá, không ca nào bị đổi sang SKIP, không assert nào bị hạ.

---

## 4. BẰNG CHỨNG ĐỐI CHỨNG ÂM / DƯƠNG CỦA CHÍNH VÒNG 2

| Phép đo | Đối chứng DƯƠNG | Đối chứng ÂM |
|---|---|---|
| `tree_hien_tai()` | tiêm 1 mục vào bản sao index ⇒ tree `9628587 → 44025342f53b`; index thật sha256 không đổi; không lock | nếu cây khác `TREE_NEN` ⇒ `A1` FAIL; nếu `NEN_SHA^{tree}` khác `TREE_NEN` ⇒ FAIL với thông điệp **GHIM STALE** |
| số ca E2E | `--list` = 65/8 khớp báo cáo chạy thật (`65 = 57+1+7`, `8 = 8+0+0`) | bỏ 1 dòng khai ca trong bản sao TẠM: `8 → 7`; hạ 1 ca trong báo cáo: `(64,0,0)`/`(7,0,0)` ⇒ cổng ĐỎ |
| `E1` 3 cổng cây sạch | clone tại nền: 3/3 XANH | tiêm tệp bẩn: 3/3 `DO_THAT` (không phải "phép đo chết") |
| `B2`/`B3` chạy thật | `B3` 8/8 đạt; `B2` 57 đạt | `B2` 1 hỏng + 7 không chạy ⇒ cổng ĐỎ, **không** bị tính là đạt |

---

## 5. NHỮNG GÌ **KHÔNG** BỊ THAY ĐỔI / CHỐNG NỚI CỔNG

* **Không xoá ca, không đổi ca sang SKIP, không hạ assert.** `Ran` vẫn **24**.
* `dat_cong` / `phan_quyet`: **không sửa**. Giá trị "nửa vời" vẫn ĐỎ ở cả hai chế độ.
* `E1` vẫn **TỪ CHỐI phán quyết** khi `HEAD ≠ NEN_SHA` — điều kiện đó không bị gỡ.
* `B2` vẫn giữ đích `(65,0,0)`; **không** đổi thành `(57,1,7)` để lấy `EXIT 0`.
* Không sửa mã sản phẩm: `git status` chỉ có `app/thu/thu_qa_g22.py` + `docs/G22_CONTRACT.md`.
* Không sửa `thu_qa_g20.py`, `thu_qa_g21.py`, `thu_g20_dahang.py`; chỉ đọc/chạy.
* Không đụng `D-8` / `C4` / `:5432`; `A3`/`A4`/`H` giữ nguyên.
* Ngoài phạm vi hai tệp: chỉ tạo lại **symlink** trong `node_modules` (không được git theo dõi)
  — khai ở §2.3.

---

## 6. CÒN LẠI — NÓI THẲNG, KHÔNG GIẢ XANH

1. **`B2` (AGENT 01 / AG-06 FRONTEND):** ca 03 của `01_luong_chinh.spec.js` timeout ở bộ lọc
   nâng cao; 7 ca sau `did not run` do `serial`. Đây là **lỗi có sẵn**, không phải do vòng 2.
   Cần sửa ca/hành vi rồi chạy lại; khi đó `B2` mới có thể đạt `(65,0,0)`.
2. **Commit:** bị chặn ghi `.git`; AG-00/Controller commit hộ **đúng hai tệp**:
   * `app/thu/thu_qa_g22.py` — sha256 `4cf9a7325c38fe3368c860208a88570f35530c96c09c285795e7a0dcb66ffbf0`
   * `docs/G22_CONTRACT.md` — tài liệu này
   `git status` tại thời điểm bàn giao: `M app/thu/thu_qa_g22.py` + `M docs/G22_CONTRACT.md`.
   **Không push.**
3. **Nhị phân Chromium:** symlink `.local-browsers` **không được commit** (gitignore). Trên cây
   mới, phải dựng lại theo `docs/G21_BANPHIM_E2E.md` §10, nếu không `B1`/`B2`/`B3` sẽ báo
   "KHÔNG CHẠY ĐƯỢC" — không được skip.
4. **Ghim của lượt sau:** commit của AG-00 sẽ làm `HEAD` nhích; lượt sau phải cập nhật
   `NEN_SHA`/`TREE_NEN` theo nền mới, và `A1` sẽ tự báo **GHIM STALE** cho tới lúc đó.
5. **`C4` / D-8:** giữ nguyên **BLOCKED OWNER**; vòng này không đo, không sửa, không ép xanh.

---

## 7. CÁCH TỰ KIỂM LẠI

```sh
# 1) Toàn bộ — kỳ vọng vòng 2: Ran 24 · failures=1 (B2) · skipped=1 (Z9) · EXIT 1
python3 app/thu/thu_qa_g22.py

# 2) Ba nhóm quyết định của vòng 2:
python3 app/thu/thu_qa_g22.py A_Nen        # Ran 4 · OK · EXIT 0
python3 app/thu/thu_qa_g22.py C_BanPhim    # B1, B3 OK; B2 FAIL vì lỗi có sẵn · EXIT 1
python3 app/thu/thu_qa_g22.py E_CaySach    # Ran 2 · OK · skipped=0 · EXIT 0

# 3) Xem đối chứng âm trong log: A1 (tiêm index), B2/B3 (hạ 1 ca), E1 (tiêm tệp bẩn).
# 4) Kiểm sha256 nhị phân headless:
shasum -a 256 node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
# → a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040
```

**Ba luật bằng chứng đã giữ:** mọi khẳng định đi kèm lệnh thật + mã thoát thật + số ca + số
skip; không đoán mã trạng thái hãng (không có lời gọi hãng nào); mọi ca phủ định trong phạm vi
đều có đối chứng dương **chạy thật**.

---

## 8. LỊCH SỬ VÒNG 1 (giữ để đối chiếu, không thay số hiện tại)

Vòng 1 (`task_82754aae6280`, nền `a76ec51`) đã đưa 5 ca thuộc phạm vi F1/F2/F3/G1/Z6 từ
HỎNG/ERROR sang XANH bằng cách sửa **cách đo** theo hợp đồng đã duyệt: `luc=` là tham số
(F1/F3 + bản đóng băng md5 `611182a6…` ở F2), `G5` thật **0/5** + tiêm **2/5** (G1),
`Z6` có đối chứng clone thật. Các số và bằng chứng của vòng 1 nằm trong
`docs/G22_SAOLUU.md` và log vòng 1 trên máy đo cũ (`/tmp/g22_a2/`).
Vòng 2 không sửa lại các ca đó; chúng vẫn XANH trong lượt chạy cuối (`F1`, `F2`, `F3`, `G1`,
`Z6` đều `ok`).
