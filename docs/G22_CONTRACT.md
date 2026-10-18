# G22 · AGENT 02 — HỢP ĐỒNG TEST (VÒNG 4 · `C4`/`G19-C6` ĐÃ ĐÓNG · TÍCH HỢP `146500b`)

> **Vai:** AGENT 02 · G22 TEST CONTRACT · task `task_2d2ea3e07ccc` · dispatch `ctx_e398c90995a7`
> (vòng 4; nối tiếp vòng 3 `task_6ec3f270dffb`/`ctx_d56f10e956ad`).
> **Nền đo:** `HEAD` **ĐỌC TẠI CHỖ** — KHÔNG còn hằng số. Vòng 4 đo trên **bản sao TMP của tích
> hợp `146500b`** (`HEAD^{tree}` = `368664e148aa…`, cây SẠCH, có bản vá B2 của AG-06 và route
> `truy_van`). Worktree `g22-a2-contract` đứng ở `a6b5b73` (cây `8f390317e9b7…` — thiếu B2) và
> **sandbox chặn ghi `.git`** nên KHÔNG fast-forward được — xem §0ter.4.
> **KHÔNG** dùng `main` (`de740dc` — không chứa G13–G22). **KHÔNG** mở G23.
> **Phạm vi ghi:** `app/thu/thu_qa_g22.py` (sửa) · `docs/G22_CONTRACT.md` (tài liệu này).
> **CAM KẾT:** không push · không deploy · không tunnel · không credentials thật · không API
> production · không sửa CSDL thật · không tự bấm duyệt sandbox · không ghi `.git` của worktree.
> **HAI THỨ TRÙNG NHÃN "C4" — KHÔNG ĐÁNH ĐỒNG:** `C4`/`G19-C6` (route `truy_van` + `DDL_G12Q`
> vào migration) **ĐÃ ĐÓNG phần tuyến** — chủ **Agent 06** + **Agent 02**; còn
> **`OWNER_ACTIONS C4` = "Chuyển CSDL nghiệp vụ sang PostgreSQL" = D-8, BLOCKED OWNER** — vòng
> này KHÔNG đo, KHÔNG sửa, KHÔNG ép xanh phần đó.

---

## 0bis. VÒNG 3 — `A1` BỎ GHIM, NỀN ĐỌC TẠI CHỖ (thay §2.1(b) của vòng 2)

**Vấn đề của vòng 2:** phép đo đã đúng, nhưng kết quả vẫn bị **GHIM** vào hai hằng số
`NEN_SHA`/`TREE_NEN`. `HEAD` nhích ở **mọi** commit, nên đúng một commit sau khi gộp, cặp số đó
thành STALE và `A1` đỏ **vĩnh viễn** cho tới khi có người sửa số. Đó là họ **H5/N-G19-04**
("ghim SỰ THẬT MÔI TRƯỜNG") — cùng loại đã bị diệt ở C5/G7, `SO_DO`, tiêu đề F; vòng 3 diệt nốt
ở `A1`. Đây là **lần thứ ba** cùng một kiểu lỗi, nên vòng 3 **sửa CHO BỀN**, không cập nhật số.

### 0bis.1 Cách sửa (không còn số nào để cập nhật)

| Thứ | Vòng 2 (ghim) | Vòng 3 (đọc tại chỗ) |
|---|---|---|
| nền | hằng `NEN_SHA = "dd788fc…"` | `git rev-parse HEAD` — **đọc ngay trong phép đo** |
| cây nền | hằng `TREE_NEN = "9628587…"` | `git rev-parse HEAD^{tree}` — **đọc ngay trong phép đo** |
| cây đang đo | `write-tree` trên bản sao index | **giữ nguyên** (bản sao index + ODB tạm + alternates chỉ-đọc, AGENT 03 §3.3) |
| phán quyết | `vt["tree"] == TREE_NEN` + tự kiểm ghim | `write-tree(index) == HEAD^{tree}` **và** `status` không có đường ngoài `TEP_DUOC_PHEP` |
| `NEN_SHA` dùng ở `A2`/`E1`/`main` | so với hằng | đọc `HEAD` tại chỗ; **bỏ hẳn** khái niệm "delta hai commit được miễn trừ" |

Điểm vào duy nhất của phán quyết là **`do_a1(goc=None)`**: ca thật và **mọi** đối chứng âm đều
gọi đúng hàm này, nên không thể có chuyện "đối chứng đo một đằng, ca thật đo một nẻo".

```python
# app/thu/thu_qa_g22.py — không còn dòng nào kiểu này:
NEN_SHA  = "..."
TREE_NEN = "..."
# thay bằng: HEAD và HEAD^{tree} đọc tại chỗ trong do_a1(), đối chiếu với write-tree(index tạm).
```

### 0bis.2 `A1` TRƯỚC / SAU (đo thật, không khẳng định)

| | TRƯỚC khi sửa | SAU khi sửa |
|---|---|---|
| Lệnh | `python3 app/thu/thu_qa_g22.py A_Nen` | `python3 app/thu/thu_qa_g22.py` (toàn bộ) |
| `HEAD` | `38f806e869ae…` | `a6b5b73bf349…` (**đã nhích**, xem §0bis.4) |
| `HEAD^{tree}` | `bf5bd4df0400…` | `8f390317e9b7…` |
| `write-tree` (index tạm) | `bf5bd4df0400…` | `8f390317e9b7…` |
| Ghim trong tệp | `dd788fc / 9628587` — **STALE** | **không còn ghim** |
| `A1` | **ĐỎ** (đo đúng, ghim sai) | **XANH** |
| Nhóm `A_Nen` | `Ran 4 · FAILED (failures=1) · EXIT 1` | `Ran 4 · OK · EXIT 0` |
| Log | `/tmp/g22-a2-v3/a1_truoc.log` | `/tmp/g22-a2-v3/full_lan4_ban_giao.log` |

Dòng đo trước khi sửa (nguyên văn): `[A1] HEAD=38f806e869ae · write-tree (index tạm)=bf5bd4df0400
· 380 tệp theo dõi` và `GHIM: git rev-parse dd788fc01c5c^{tree} → 9628587 = TREE_NEN ✓` — tức
**phép đo đúng, cái sai là GHIM**. Sau khi sửa, cùng phép đo so với `HEAD^{tree}` **đọc tại chỗ**.

### 0bis.3 BA ĐỐI CHỨNG ÂM + BA DƯƠNG — TẤT CẢ LÀM THẬT trên clone tạm

Không có phần này thì "bỏ ghim" có thể chỉ là "bỏ luôn răng". Mỗi dòng dưới đây là kết quả đo
trong `/tmp/g22-a2-v3/full_lan4_ban_giao.log` (clone `--shared` trong TMP; `.git` của worktree thật
không bị ghi).

| Vế | Việc LÀM THẬT trên clone | Kết quả ĐO ĐƯỢC |
|---|---|---|
| **D** dương | clone sạch tại `HEAD` | `XANH` — `write-tree = HEAD^{tree} = 8f390317` |
| **A1** âm | sửa `admin/admin.js` (không stage) | **ĐỎ** — `CÂY BẨN NGOÀI PHẠM VI: admin/admin.js` |
| **A2** âm | thêm `admin/__tiem_a1_g22.js` | **ĐỎ** — `CÂY BẨN NGOÀI PHẠM VI: admin/admin.js, admin/__tiem_a1_g22.js` |
| **B** âm | sửa rồi `git add admin/admin.js` | **ĐỎ** — `INDEX VÀ HEAD LỆCH NHAU: write-tree=46017e14a12e ≠ HEAD^{tree}=8f390317e9b7` |
| **C1** âm | xoá `.git/index` của clone | **ĐỎ** — `KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX (… LỖI(không có index tại …/​.git/index))` |
| **C2** âm | ghi HEAD hỏng trong clone | **ĐỎ** — `KHÔNG ĐỌC ĐƯỢC HEAD (git rev-parse HEAD rc=128)` + `KHÔNG ĐỌC ĐƯỢC CÂY CỦA HEAD` |
| **D2** dương | trả index/HEAD lại | `XANH` — clone khôi phục sạch |
| **D3** dương | **commit thật** trong clone | `HEAD a6b5b73 → 7887793df1b7`, cây `8f390317 → 9ebad2f29042`, **vẫn XANH** (SHA commit CỐ ĐỊNH nhờ ghim `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`, nên lượt sau đối chiếu lại được) |

**D3 là vế trả lời trực tiếp yêu cầu "không còn phải cập nhật số nào khi HEAD nhích":** HEAD đổi,
cây đổi, `A1` vẫn xanh vì nền được đọc lại tại chỗ. Đối chứng dương `D`/`D2` chặn khả năng "cổng
luôn đỏ"; ba vế âm chặn khả năng "cổng luôn xanh".

### 0bis.4 BẰNG CHỨNG CÔNG KHAI: `HEAD` NHÍCH THẬT GIỮA LƯỢT

Trong lúc lượt này đang chạy, AG-00/Controller commit hộ bản đang làm: `38f806e → **a6b5b73**`
("AGENT 02 VONG 3 (G22) A1 BEN VUNG: bo HANG SO, doc HEAD^{tree} TAI CHO"). Đây đúng là tình
huống đã giết `A1` ba lần. Kết quả: lần chạy sau đó đo `HEAD=a6b5b73bf349 · tree=8f390317e9b7`
và **XANH**, **không một hằng số nào được sửa**. Nếu còn ghim, `A1` sẽ đỏ ngay tại đây.

### 0bis.5 KẾT QUẢ TOÀN BỘ (so với mốc 24/22/1/1)

| | Mốc vòng 2 | Vòng 3 (lượt cuối) |
|---|---|---|
| `Ran` | 24 | **24** |
| PASS (= Ran − FAIL − SKIP) | 22 | **22** |
| FAIL | 1 (`B2`) | **1 (`B2`)** |
| SKIP | 1 (`Z9` mồi) | **1 (`Z9` mồi)** |
| **EXIT CODE** | **1** | **1** |

`A1` xanh, `E1` xanh (không còn skip vì không còn trạng thái `HEAD ≠ nền`), `B2` vẫn đỏ **đúng
lỗi có sẵn** — không sửa ca, không hạ cổng. Log: `/tmp/g22-a2-v3/full_lan4_ban_giao.log`.
`sha256 app/thu/thu_qa_g22.py` (bản cuối): `3a971f2b6479e205e43a2307889b4395f6552f5d0b4648d342cd560c40f07821`.

---

## 0ter. VÒNG 4 — `C4`/`G19-C6`: SẢN PHẨM ĐÃ ĐÓNG, CỔNG ĐỎ VÌ GHIM TRẠNG THÁI NỀN

> Dispatch `ctx_e398c90995a7` · task `task_2d2ea3e07ccc` · nền đo: **bản sao TMP của tích hợp
> `146500b`** (cây SẠCH). AG-00 đã đo ở đó `Ran 24 · FAIL 1 · SKIP 1 · EXIT 1`, ca hỏng duy nhất
> là `H_C4`. `C4` ở đây = **`G19-C6`**, KHÔNG phải `OWNER_ACTIONS C4` (D-8).

### 0ter.1 Sự thật đo được — vì sao ca cũ ĐỎ dù sản phẩm xanh

`SO_DO_G20` ghi C4 bằng CẶP `(schema v9 đạt?, có tệp SẢN XUẤT import truy_van?)`:
nền `(True, False)` → đóng `(True, True)`.

| Cây | `app/server.py` | cặp đo được | ca `H_C4` cũ |
|---|---|---|---|
| nền `a6b5b73` (worktree này) | KHÔNG có `import truy_van` | `(True, False)` = ô NỀN | XANH (vì nó ghim đúng `(True, False)`) |
| tích hợp `146500b` | `import truy_van` + route `/api/v2/don` gọi `truy_van.tim_don(...)`, bắt `truy_van.LoiTruyVan`; route `/api/v2/don/loc-mo-ta` gọi `truy_van.mo_ta_bo_loc()` | **`(True, True)`** = ô ĐÓNG | **ĐỎ** — nó khẳng định trạng thái CŨ |

Đo lại bằng **chính ca cũ** trên bản sao `146500b` (log `/tmp/g22-a2-v4/nen.log`):
`[H1] … tệp SẢN XUẤT import truy_van: 1` · `cặp đo được = (True, True)` → `AssertionError`.
⇒ **Không phải lỗi sản phẩm; là ca thử GHIM hành vi cũ** — đúng họ H5/N-G19-04 mà vòng 3 đã diệt
ở `A1`, nay diệt nốt ở `H_C4`. **KHÔNG xoá ca, KHÔNG `skipTest`, KHÔNG nới assert.**

### 0ter.2 Hai thứ trùng nhãn "C4" — tuyệt đối không đánh đồng

| Nhãn | Nội dung | Trạng thái vòng 4 | Chủ |
|---|---|---|---|
| **`C4` = `G19-C6`** | route `truy_van.py` + `DDL_G12Q` vào migration v9 | **ĐÓNG phần TUYẾN**; phần `DDL_G12Q`→migration **CÒN TREO** (§0ter.5) | **Agent 06** (port khối route ~20 dòng vào `app/server.py`, `146500b`) + **Agent 02** (ca đo này) |
| **`OWNER_ACTIONS C4`** | "Chuyển CSDL nghiệp vụ sang PostgreSQL" = **D-8** | **BLOCKED OWNER** — KHÔNG thực hiện, KHÔNG ép xanh, KHÔNG đụng `:5432` | Owner/AG-05 — ngoài phạm vi vòng này |

Dòng `D-8 / OWNER_ACTIONS C4` ở đầu tài liệu là về **hàng thứ hai**; nó **không** nói gì về
`G19-C6`. Đánh đồng hai thứ này là coi một việc đã đóng như một việc bị chặn — hoặc ngược lại.

### 0ter.3 Ca viết lại — ĐO TẠI CHỖ + ĐỐI CHỨNG ÂM LÀM THẬT (không khẳng định suông)

`H_C4` mới gọi **một** điểm vào `_do_c4(goc)` (giống `do_a1()`), nên ca thật và mọi đối chứng đo
**cùng một hàm**:

1. **Đọc tại chỗ, KHÔNG ghim số:** quét `app/**/*.py` (trừ `app/thu/**`, `docs/**`, chính
   `app/truy_van.py`), `ast.parse` từng tệp, đếm **THẬT**:
   * tệp có `import truy_van` / `from truy_van import …`;
   * số lần **DÙNG** — `Name` trùng tên do CHÍNH tệp đó import (biến cục bộ trùng tên, đo được ở
     `gateway/server.py`, KHÔNG bị tính — một dương tính giả đã bị bắt tại chỗ);
   * `csdl.PHIEN_BAN_SCHEMA` của CHÍNH cây đang đo; **v9 là SÀN** (`>= 9`), không ghim đúng `9`
     — `v10` sau này không làm cổng đỏ vĩnh viễn.
     → **THAY Ở VÒNG 6 (§9.4):** không còn `>= 9` viết tay. `MỐC` = số N của `nang_len_vN` áp
     `truy_van.DDL_G12Q` trong `app/migrate.py`, ĐỌC TẠI CHỖ; so `schema >= MỐC`. Đây là "SCHEMA
     TỐI THIỂU", và nó đã đóng vì `nang_len_v10` + `PHIEN_BAN_SCHEMA = 10` đã được áp.
2. **ĐỐI CHỨNG DƯƠNG:** bản sao `app/` Y NGUYÊN phải cho đúng cặp như cây thật.
   → **THAY Ở VÒNG 6 (§9.5):** bộ ba `(schema_ok, chi_muc_ok, tuyen_ok)`, không còn cặp.
3. **ĐỐI CHỨNG ÂM BẮT BUỘC — LÀM THẬT:** trên CHÍNH bản sao đó, gỡ bằng AST (không ghim dòng)
   mọi `import truy_van` + mọi khối `if` DÙNG `truy_van`; tệp phải còn hợp lệ cú pháp; đo lại
   **phải** ra `(True, False)` và cổng **PHẢI ĐỎ**. Gỡ tuyến mà vẫn xanh ⇒ bộ đo MÙ.
   → **THAY Ở VÒNG 6 (§9.5):** đòi `(True, True, False)` — tầng CHỈ MỤC không bị chạm — và thêm
   một đối chứng âm RIÊNG cho tầng đó: hạ `PHIEN_BAN_SCHEMA` xuống `MỐC − 1` ⇒ cổng PHẢI ĐỎ.

Nhóm đối chứng `c4-go-route` được ghi vào `CA_PHU_DINH`/`DOI_CHUNG` và vào danh sách **bắt buộc
tiêm lỗi** của `Z6`: xoá đối chứng âm này thì `Z6` ĐỎ, không im lặng.

**Kết quả ĐO ĐƯỢC** (`/tmp/g22-a2-v4/sau2.log`):

```
[H1] C4 = G19-C6 — ĐO TẠI CHỖ trên cây thật (/private/tmp/g22-a2-v4/clone)
     `PHIEN_BAN_SCHEMA`=9 (đích: ≥9, KHÔNG ghim đúng 9) · tệp SẢN XUẤT tham chiếu `truy_van`=1
     tham chiếu ĐẾM ĐƯỢC: app/server.py (import 1 · dùng 3)
     cặp đo được = (True, True) · sổ G20: nền=(True, False) · đóng=(True, True) · phân quyết = DONG
     ĐỐI CHỨNG DƯƠNG: bản sao `app/` y nguyên → (True, True) (đòi (True, True)) ✓
     ĐỐI CHỨNG ÂM (LÀM THẬT): gỡ 3 khối / 21 dòng khỏi `app/server.py` — import truy_van (1 dòng),
       khối if DÙNG truy_van (tuyến) (15 dòng), khối if DÙNG truy_van (tuyến) (5 dòng)
     sau khi gỡ: tệp sản xuất tham chiếu `truy_van`=0 · cặp đo được = (True, False)
     ⇒ gỡ tuyến thì cổng ĐỎ (đòi ĐỎ) ✓ — cổng KHÔNG phải bộ đo mù.
```

### 0ter.4 Bằng chứng chạy — số ca + mã thoát THẬT

| Lượt | Lệnh (cây) | Kết quả ĐO ĐƯỢC |
|---|---|---|
| NỀN (ca cũ) | `python3 app/thu/thu_qa_g22.py` trên bản sao `146500b` | `Ran 24 tests in 150.571s` · `FAILED (failures=1, skipped=1)` · **EXIT 1** — ca hỏng duy nhất `H_C4` |
| `H_C4` đơn | `python3 app/thu/thu_qa_g22.py H_C4` trên bản sao `146500b`, ca MỚI | `Ran 1 test` · `OK` · **EXIT 0** |
| TOÀN BỘ (ca mới) | `python3 app/thu/thu_qa_g22.py` trên bản sao `146500b` | `Ran 24 tests in 147.835s` · **`OK (skipped=1)`** · **EXIT 0** · `ca: 24 · hỏng/loi: 0 · bỏ qua: 1` |

`PASS = 24 − 0 − 1 = 23`. **SKIP 1 là `Z9` — MỒI CÓ CHỦ ĐÍCH của `Z5`**, không phải nợ: nó
`skipTest` khi chạy trong làn thường và `Z5` cố ý chạy nó ở tiến trình con với
`VIP_G22_CHAY_MOI=1` để chứng minh bộ chạy có răng. Vì thế **SKIP 0 là bất khả thi nếu không xoá
mồi/nuốt skip — cả hai đều bị cấm.** Con số đúng phải đọc là **24 ca · 0 hỏng · 1 bỏ qua CÓ CHỦ
ĐÍCH · EXIT 0**.

`sha256 app/thu/thu_qa_g22.py` (bản vòng 4):
`1d6f99a879a79b67e84a1905b87f0daa117fa13306e5a6fe46bccbfbf5f13880` — đúng tệp đã dùng trong
lượt chạy toàn bộ ở trên (bản sao TMP có cùng sha256).

**Vì sao chạy trên bản sao TMP chứ không phải worktree này:** worktree `g22-a2-contract` đứng ở
`a6b5b73`, THIẾU bản vá B2 (`146500b`), và sandbox CHẶN ghi `.git`:

```
$ git update-index --really-refresh
fatal: Unable to create '…/Projects/vip-express-hub/.git/worktrees/g22-a2-contract/index.lock':
       Operation not permitted            (rc = 128)
```

⇒ không `merge --ff-only` được. Bằng chứng vì thế chạy trên **bản sao TMP** của `146500b`
(`git clone --shared` + `checkout --detach 146500b` + symlink `node_modules` — đúng cách `A1`/`E1`
đã dùng; `.git` của worktree thật KHÔNG bị ghi). Đo `H_C4` trên **chính worktree** `a6b5b73` cho
kết quả **ĐỎ** với thông điệp `C4 CHƯA ĐÓNG: KHÔNG có tệp SẢN XUẤT nào import truy_van — đây là
trạng thái NỀN (True, False)` (log `/tmp/g22-a2-v4/hc4_worktree_final.log`) — **đúng trạng thái
nền, không phải ca viết sai**; đó là lý do bằng chứng phải đo trên cây đã có B2. **Việc còn lại
của AG-00:** fast-forward `g22-a2-contract` lên `146500b` (hoặc merge bản vá này vào tích hợp)
rồi chạy lại toàn bộ tại đó — kỳ vọng `24 ca · 0 hỏng · 1 bỏ qua (Z9) · EXIT 0`.

### 0ter.5 CÒN TREO — nói thẳng, không nhận là đã xong

1. **`nang_len_v10` CHƯA được áp** — `PHIEN_BAN_SCHEMA` vẫn là **9**; `truy_van.DDL_G12Q`
   (9 chỉ mục) **chưa** được đưa vào migration cho CSDL ĐÃ Ở v9. Đây là **phần còn lại của
   `G19-C6`**, chủ **AG-02 backend**. Ca `H_C4` chỉ gác phần TUYẾN + sàn schema, **không** gác
   phần chỉ mục.
   → **ĐÃ ĐÓNG Ở VÒNG 6 (§9.4/§9.5):** U4 đã áp `migrate.nang_len_v10` và
   `csdl.PHIEN_BAN_SCHEMA = 10`; ca `H_C4` nay gác CẢ tầng chỉ mục (đo `truy_van.DDL_G12Q` có
   thật + mốc `nang_len_v10` được `chay()` gọi), không chỉ "sàn schema".
2. **Bàn đo G20 còn GHIM trạng thái nền ở chính cổng C4** — `app/thu/thu_qa_g20.py` dòng 702:
   `self.assertEqual(nhap, [], "nền đã đổi: có tệp SẢN XUẤT import truy_van")`. Đo TRỰC TIẾP trên
   cây tích hợp `146500b`: `AssertionError: ['app/server.py'] != []` ⇒ cổng C4 của G20 **ĐỎ** dù
   `dat_cong` nói ĐÓNG. **Và `D1` che nó:** `D1` chạy cả bàn đo G20 nhưng **không đọc mã thoát**
   (chỉ regex dòng `Ran …`), nên các ca hỏng bên trong G20 (đo trên bản sao: 7 ca — C4, C1 ghim
   môi trường `148ecd3`, hai ca tầng 3 `B1`/`B2`, và `A5` + `Z1`/`Z2`) **không** làm `D1` đỏ. Đây
   là tệp **ngoài phạm vi ghi của AG-02** (`thu_qa_g22.py` + tài liệu này) — **báo AG-00** để cấp
   việc cho chủ `thu_qa_g20.py`; không sửa lén.
   → **ĐÃ SỬA Ở VÒNG 5 (§0quater):** `D1` nay đọc **mã thoát THẬT** và **ĐỎ đúng** vì G20 còn
   hỏng; phần sửa các ca hỏng bên trong `thu_qa_g20.py` vẫn thuộc chủ tệp đó (Agent U2).
3. **Worktree `g22-a2-contract` chưa lên `146500b`** (sandbox chặn ghi `.git`, xem §0ter.4) —
   AG-00 cần fast-forward/merge; commit hộ vẫn là AG-00/Controller như các vòng trước.

---

## 0quater. VÒNG 5 — `D1` CHE LỖI CỦA G20: MỘT CỔNG BÁO ĐẠT TRONG KHI BÀN ĐO ĐỎ

> Dispatch `ctx_9a5bd3e3389c` · task `task_eaf399b954e3` · nền đo: `HEAD` **ĐỌC TẠI CHỖ**
> `2f4c3d1402c1` (cây `ece2b65d4623`), cây **SẠCH**. Phạm vi ghi: `app/thu/thu_qa_g22.py` +
> tài liệu này. Không push · không deploy · không API production · không sửa CSDL thật.

### 0quater.1 Sự thật đo được — vì sao đây là ƯU TIÊN SỐ 1

`D1` (`test_d1_nam_cong_g20`) chạy **CẢ** bàn đo G20 nhưng **KHÔNG ĐỌC MÃ THOÁT**: nó lấy `rc`
rồi chỉ `re.search(r"Ran (\d+) tests? …")` trên output, và chỉ HỎNG khi **không tìm thấy dòng
`Ran …`**. Một bàn đo G20 có 6 ca hỏng vẫn in `Ran 21 tests`, nên `m` khác `None` ⇒ cổng PASS.

| | TRƯỚC khi sửa (đo được) | SAU khi sửa (đo được) |
|---|---|---|
| Lệnh đo G20 | `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` | y nguyên |
| `Ran` / `FAIL` / `SKIP` của G20 | **21 · 6 · 3** (cây SẠCH) | **21 · 7 · 3** (xem ghi chú dưới) |
| Dòng tổng kết G20 | `FAILED (failures=6, skipped=3)` | `FAILED (failures=7, skipped=3)` |
| **MÃ THOÁT THẬT của G20** | **1** | **1** (G20 còn hỏng — chưa ai sửa) |
| `D1` phán | **PASS** ← SAI | **FAIL** ← ĐÚNG |
| Nhóm `D_BanDoG20` | `Ran 1 · OK · ca: 1 · hỏng/loi: 0 · MÃ THOÁT = 0` | `Ran 1 · FAILED (failures=1) · hỏng/loi: 1 · MÃ THOÁT = 1` |
| Log | `/tmp/u1-d1-truoc-d1.log` | `/tmp/u1-d1-sau-d1.log` |

Nguyên văn dòng đo TRƯỚC khi sửa (bộ kiểm in ra `rc` rồi **bỏ qua**):

```
       mã thoát THẬT = 1 · 7.6 giây · Ran 21 tests in 7.599s  FAILED (failures=6, skipped=3)
...
  ca: 1 · hỏng/loi: 0 · bỏ qua: 0 · MÃ THOÁT = 0
EXIT=0
```

Tức bàn đo nó canh đã **ĐỎ** (`EXIT 1`, 6 ca hỏng) mà cổng vẫn **XANH**. Một cổng báo ĐẠT khi
thứ nó đo THẤT BẠI là **lỗi tệ nhất của cả wave**: nó biến mọi báo cáo thành vô nghĩa. Log
`full-08` của AG-00 cũng in `G20 exit 1` mà `D1` vẫn PASS — đúng lỗi này.

### 0quater.2 Cách sửa — MỘT điểm vào, BỐN vế, và mã thoát là vế CHÍNH

`D1` (và cả bốn đối chứng âm) đi qua **đúng một** hàm `_phan_quyet_ban_do_g20(rc, out)` — cùng
nguyên tắc "một điểm vào" đã dùng cho `do_a1()`/`_do_c4()`, nên không thể có chuyện "đối chứng
đo một đằng, ca thật đo một nẻo".

| Vế | Điều kiện ĐẠT | Nguồn của sự thật |
|---|---|---|
| **(1) MÃ THOÁT** — vế CHÍNH | `rc == 0` | `p.returncode` của `chay()`, đọc NGAY sau lệnh, **không qua ống** |
| (2) không có ca hỏng | 0 dòng `FAIL:` + 0 dòng `ERROR:` | nguyên văn output của bàn đo |
| (3) có ca thật | `Ran N` đọc được và `N > 0` | nguyên văn output |
| (4) có kết luận | có dòng tổng kết `OK…` / `FAILED…`, và **không** là `FAILED` | nguyên văn output |

`Ran N` · `PASS` · `FAIL` · `ERROR` · `SKIP` **vẫn được in ra để BÁO CÁO** (`PASS` suy ra =
`Ran − FAIL − ERROR − SKIP`), nhưng phán quyết không còn chỉ dựa vào regex. Vế (2)(3)(4) chặn
đúng chiều sai ngược lại: **"tin mã thoát đơn lẻ"**. Bàn đo không tồn tại / không chạy được /
quá thời gian (`rc = None`) ⇒ **ĐỎ** và in rõ `KHÔNG CHẠY ĐƯỢC`, không bao giờ là "đạt".

### 0quater.3 BỐN ĐỐI CHỨNG ÂM BẮT BUỘC + ĐỐI CHỨNG DƯƠNG — ĐO ĐƯỢC (không phải khẳng định)

Mỗi đối chứng là một **TIẾN TRÌNH CON THẬT** (`subprocess` chạy một bàn đo giả trong TMP) đi qua
**chính** hàm `_phan_quyet_ban_do_g20()`. Nguyên văn log `/tmp/u1-d1-sau-d1.log`:

| Vế | Kịch bản TIÊM (thật) | Kết quả ĐO ĐƯỢC |
|---|---|---|
| **(a)** | bàn đo giả in `Ran 3 tests` + `OK` (chữ nói ĐẠT) nhưng `sys.exit(3)` | `rc=3 → ĐỎ ✓` · lý do: `MÃ THOÁT THẬT = 3 (đòi 0)` ⇒ **chỉ vế (1) bắt được** |
| **(b)** | thoát **0** nhưng in `FAIL: …` + `FAILED (failures=1)` | `rc=0 → ĐỎ ✓` · lý do: `output có 1 dòng FAIL: … dù mã thoát=0 — KHÔNG tin mã thoát đơn lẻ` |
| **(c)** | in `Ran 0 tests` + `OK` rồi thoát 0 | `rc=0 → ĐỎ ✓` · lý do: ``Ran 0 tests`: bàn đo KHÔNG chạy ca nào ⇒ 0 ca, không phải ĐẠT` |
| **(d)** | trỏ vào tệp **không tồn tại** | `rc=2 → ĐỎ ✓` · lý do: `KHÔNG CHẠY ĐƯỢC: output KHÔNG có dòng Ran N tests … KHÔNG được coi là đạt` |
| **(+)** dương | bàn đo giả in `Ran 3 tests` + `OK`, thoát 0 | `rc=0 → ĐẠT ✓` · `Ran 3 · tổng kết 'OK'` ⇒ chặn kiểu hỏng "cổng luôn Đỏ" |

Bốn vế âm + một vế dương nghĩa là: phép đo **BẮT ĐƯỢC** cả bốn kiểu hỏng (kể cả kiểu "chữ nói
OK, mã thoát nói hỏng" — đúng kiểu đã xảy ra), **và** không phải một cổng luôn Đỏ.

### 0quater.4 KẾT QUẢ TOÀN BỘ SAU KHI SỬA (đo thật)

| | Vòng 4 | **Vòng 5 (lượt này)** |
|---|---|---|
| `Ran` | 24 | **24** |
| PASS (= Ran − FAIL − SKIP) | 23 | **22** |
| FAIL | 0 | **1 (`D1`)** |
| SKIP | 1 (`Z9` mồi) | **1 (`Z9` mồi)** |
| **EXIT** | 0 | **1** |

Nguyên văn `Ran 24 tests in 210.386s` · `FAILED (failures=1, skipped=1)` · `ca: 24 · hỏng/loi: 1 ·
bỏ qua: 1 · MÃ THOÁT = 1` (log `/tmp/u1-d1-full-sau2.log`; lượt trước đó
`/tmp/u1-d1-full-sau.log` cho **cùng** số). `B2`/`B3` vẫn **XANH** trong lượt này (`chay.sh` toàn
bộ 65 ca: `mã thoát THẬT = 0`, 157.2 s; bàn phím 8 ca: `mã thoát = 0`, 13.3 s).

`FAIL 1` là **`D1` ĐỎ ĐÚNG**: bàn đo G20 bên trong còn **ít nhất 6 ca hỏng** (§0quater.6). Không ca nào
bị xoá, không ngưỡng nào bị hạ, không ca nào bị ép PASS. Khi `thu_qa_g20.py` hết hỏng, `D1` tự
xanh trở lại — **không phải sửa cổng**.

### 0quater.5 RÀ SOÁT **CẢ LỚP LỖI** — mọi cổng "chạy nhưng không đọc mã thoát"

Đây là **lớp lỗi**, không phải một ca. Đã rà **từng** chỗ gọi `chay()`/`chay_con()`/`_git()` trong
tệp: **47 chỗ** của bản trước + **2 chỗ** mới của chính đối chứng `D1` (bàn đo giả và bàn đo không
tồn tại) = **49 chỗ**; quét lại bằng AST: **không còn biến `rc` nào bị bỏ không dùng** (trừ `_` cố
ý của PID).

| Cổng / chỗ chạy | Trước | Sửa |
|---|---|---|
| **`D1`** | `rc` lấy ra, **in ra, không dùng**; phán quyết bằng regex `Ran …` | **vế CHÍNH** của `_phan_quyet_ban_do_g20()`; thêm 4 đối chứng âm + 1 dương (§0quater.2/3) |
| **`B2`** (`chay.sh` toàn bộ) | `kq["rc"]` **chỉ in**, phán quyết bằng số ca parse từ output | thêm `assertEqual(kq["rc"], 0, …)` — bộ chạy thoát khác 0 vẫn là ĐỎ dù báo cáo trông đầy đủ |
| **`B3`** (`chay.sh 06_ban_phim`) | y như `B2` | y như `B2` |
| **Mẫu số `--list`** (`B2`/`B3`) | `so_ca_playwright()` trả `rc` nhưng **không ai đọc** | hàm dùng chung `so_ca_playwright_dat_duoc()`; `--list` thoát khác 0 ⇒ mẫu số không đáng tin ⇒ ĐỎ |
| **Khôi phục clone trong đối chứng âm `A1`** | 3 lệnh `git checkout/reset/add` **bỏ qua `rc`** | kiểm `rc != 0` ⇒ `RuntimeError` (vế sau không được đo trên một clone BẨN) |
| `A1`/`A2`/`A3` · `E1`/`E2` · `F1`(`do_e3`) · `G1` · `H1`(`_do_c4`) · `I1`(`C5`/`G7`) · `Z2` · `Z5` · `Z9` | **đã đọc `rc`** trước đó | không sửa — đã đúng |

### 0quater.6 CÒN LẠI — NÓI THẲNG, KHÔNG GIẢ XANH

1. **`D1` đang ĐỎ vì `thu_qa_g20.py` còn hỏng** — và đó là **ĐỎ ĐÚNG**. Bàn đo G20 đo được
   `Ran 21 · FAILED (failures=6, skipped=3) · EXIT 1` khi cây SẠCH: các ca hỏng gồm `C4` còn
   **ghim trạng thái nền** (`assertEqual(nhap, [])`, đã báo ở §0ter.5.2), `C1`/`git-tho` ghim
   `148ecd3`, `Z1` thiếu đối chứng dương cho `cong-cay-sach`/`git-tho`/`truy-van-C6`, `A5`, và
   hai ca tầng 3 `B1`/`B2`. **Sửa các ca đó là việc của chủ `app/thu/thu_qa_g20.py` (Agent U2)**
   — tệp này NGOÀI phạm vi ghi của lượt này; **không sửa lén, không nới cổng `D1`**.
2. **Vì sao TRƯỚC đo được `failures=6`, SAU đo được `failures=7` — KHAI RÕ, không phải "chập
   chờn":** sáu ca hỏng ĐỘC LẬP với lượt này là `A5`
   (`test_g1_cong_cay_sach_wave_truoc…`), `B1`, `B2` (tầng 3), `C4` (`route/migration`), `C1`
   (`git` môi trường NGUYÊN BẢN) và `Z1` (thiếu đối chứng dương). Ca thứ BẢY là `Z2` của chính
   G20 — `test_z2_cay_khong_doi_ngoai_hai_tep_duoc_phep` — nó ĐỎ vì cây đang có **đúng hai tệp
   của lượt này đã sửa nhưng CHƯA commit** (`M app/thu/thu_qa_g22.py`, `M docs/G22_CONTRACT.md`);
   G20 chỉ cho phép hai tệp CỦA NÓ. Trước khi sửa, cây SẠCH nên `Z2` xanh ⇒ 6 ca. Sau khi
   AG-00 commit hai tệp, `Z2` sẽ xanh lại ⇒ G20 về **6 ca hỏng**, mã thoát vẫn **1**, `D1` vẫn
   **ĐỎ**. Báo cáo `D1` ghi **số đo của lượt đang chạy**, không ghim một con số.
3. **Symlink nhị phân Chromium** `node_modules/playwright-core/.local-browsers` được **tạo lại**
   (không được git theo dõi, đúng §2.3 / `docs/G21_BANPHIM_E2E.md` §10) để `B1`/`B2`/`B3` chạy
   được thật trong lượt đo này. **Không phải tệp sản phẩm**, `git status` không đổi.
4. Không sửa `thu_qa_g20.py`, `thu_qa_g21.py`, `thu_g20_dahang.py`; không đụng `:5432`; không
   sửa `SO_DO`/`dat_cong`/`phan_quyet`.

---

## 0. TÓM TẮT MỘT MÀN HÌNH (VÒNG 2 — GIỮ LÀM LỊCH SỬ)

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

> Số trong mục này là **vòng 2** (giữ làm lịch sử). Số của **vòng 3** — bản đang bàn giao — ở
> §0bis.5; log: `/tmp/g22-a2-v3/full_lan4_ban_giao.log`.

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

> **⚠ VÒNG 3 ĐÃ BỎ HẲN CÁCH NÀY — xem §0bis.** Cập nhật số là chữa TRIỆU CHỨNG: commit kế tiếp
> lại làm ghim STALE. Vòng 3 đọc `HEAD`/`HEAD^{tree}` tại chỗ, nên đoạn `NEN_SHA`/`TREE_NEN` ở
> trên chỉ còn là **lịch sử** (không còn trong mã).

**(c) ĐỐI CHỨNG DƯƠNG — phép đo KHÔNG mù.** Nhúng ngay trong `A1` phép tiêm của AGENT 03 §3.4:

```
ĐỐI CHỨNG DƯƠNG: tiêm `__tiem_g22.txt` vào BẢN SAO index
                 → tree 9628587 → 44025342f53b · rc=0
index THẬT: sha256 trước = sau = de647d533b039fe5 · index.lock trước=sau=False
```

Tức là: cùng phép đo, tiêm một mục thì cây **ĐỔI**, còn index thật **KHÔNG đổi** và **KHÔNG**
sinh lock. Nếu `tree_hien_tai()` trả hằng số hoặc đọc nhầm cây, vế này sẽ bắt được.

> **Lưu ý cho lượt sau (ĐÃ ĐƯỢC VÒNG 3 XỬ LÝ):** nhận định dưới đây của vòng 2 đã đúng — `HEAD`
> nhích và ghim STALE — nhưng cách chữa "cập nhật số" là vô tận. Vòng 3 bỏ ghim; xem §0bis.
>
> ~~khi AG-00 commit hai tệp của vòng 2, `HEAD` sẽ nhích sang commit mới và `A1` sẽ (ĐÚNG) báo
> GHIM STALE cho tới khi ghim được cập nhật theo nền mới.~~ (lịch sử)

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

| Ca | Vòng 3 | Nhóm | Bằng chứng | Ai sở hữu việc sửa |
|---|---|---|---|---|
| `A1` `test_a1_cay_dung_bang_cay_cua_nen` | **PASS** | Đã sửa **cho bền** ở vòng 3: bỏ hẳn hằng số, đọc `HEAD`/`HEAD^{tree}` tại chỗ (§0bis) | `write-tree(index tạm) = HEAD^{tree} = 8f390317e9b7` (HEAD `a6b5b73`); ba đối chứng âm (cây bẩn / index≠HEAD / không đọc được cây) đều **ĐỎ**, D3 commit thật làm HEAD nhích vẫn **XANH** | **AGENT 02** (tệp kiểm) · **AGENT 03** (phương pháp đo index tạm, `docs/G22_A1_GIT.md`) — ĐÃ XONG |
| `B2` `test_b2_chay_e2e_toan_bo_that` | **FAIL** | **LỖI CÓ SẴN so với vòng 2/vòng 3**, nhưng **KHÔNG có trước wave G22** — xem bisect §3.1: ca `01_luong_chinh.spec.js` **03 — bộ lọc nâng cao** timeout 10 s ở `waitForFunction`; 7 ca kế tiếp `did not run` vì tệp đặt `serial` | `(57, 1, 7)` · tổng 65 = `--list`; cổng `(65,0,0)` ⇒ `NUA_VOI`; log E2E `/var/folders/…/veh_g22_ag01_qa/e2e_lan_nay.txt`; bisect ở §3.1 | **AGENT 01 / AG-06 FRONTEND** — sửa ca 03 (hoặc hành vi lọc) rồi chạy lại `01_luong_chinh.spec.js`; sau đó 7 ca `did not run` mới có số đo |
| `B3` `test_b3_e2e_tam_ca_ban_phim_chay_that` | **PASS** | Đã sửa ở vòng 2: **ghim cũ** `(7,0,0)` → `(8,0,0)`; số ca đếm từ `--list` | chạy thật `8/8`, `exit 0`; hai đối chứng âm ĐỎ đúng | **AGENT 02** — ĐÃ XONG |
| `E1` `test_e1_ba_cong_cay_sach_chay_that` | **PASS** | Vòng 3 **bỏ `skipTest`**: "nền" nay là HEAD đọc tại chỗ nên trạng thái `HEAD ≠ nền` không còn tồn tại | cây này 3/3 XANH; clone tại HEAD: sạch 3/3 XANH, tiêm `admin/__tiem_g22.js` 3/3 `DO_THAT` | **AGENT 02** — ĐÃ XONG |
| `Z9` `test_z9_ca_CO_Y_HONG_de_tu_kiem` | **SKIP (có chủ đích)** | Không phải lỗi: đây là MỒI cho `Z5`, chỉ chạy trong tiến trình con | `Z5` đọc mã thoát con = 1 với mồi hỏng; `Z1` 10/10 nhóm đã chạy đối chứng | **AGENT 02** — thiết kế giữ nguyên |
| `H1` `test_h1_c4_do_hay_da_dong` | **PASS (vòng 4)** | Trước vòng 4: **FAIL** — ca ghim trạng thái nền `(True, False)` trong khi sản phẩm đã đóng `(True, True)` (§0ter.1). Đã viết lại: đo tại chỗ + đối chứng âm gỡ tuyến **LÀM THẬT** | cặp `(True, True)`; bản sao `app/` y nguyên `(True, True)`; gỡ 3 khối/21 dòng ⇒ `(True, False)` ⇒ cổng ĐỎ; `Z1` 11/11 nhóm | **Agent 02** (ca) + **Agent 06** (route, `146500b`) — ĐÃ XONG **phần tuyến**; phần `DDL_G12Q`→migration còn treo (§0ter.5) |

`PASS 22` của vòng 3 = `24 − 1 (B2) − 1 (Z9)`. Không ca nào bị xoá, không ca nào bị đổi sang
SKIP, không assert nào bị hạ. `E1` không còn SKIP vì lý do môi trường đã bị loại bỏ tận gốc
(không còn hằng số nền để lệch).

**Cập nhật vòng 4:** `B2` đã **XANH** trên `146500b` (AG-06 vá backend — `57 → 65 đạt`);
`H1`/C4 là ca đỏ duy nhất còn lại **ở thời điểm AG-00 giao việc** và đã sửa xong (§0ter). Kết quả
toàn bộ vòng 4: `Ran 24 · PASS 23 · FAIL 0 · SKIP 1 (Z9 mồi) · EXIT 0` (§0ter.4).

### 3.1 `B2` — "có sẵn" từ đâu? Bisect THẬT trên 7 mốc

Câu hỏi của AG-00: *"nó có thật trước cả wave này không?"*. Trả lời bằng cách chạy
`sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js` trong **clone sạch** tại từng commit (cùng
`node_modules` qua symlink, cùng Chromium; log `/tmp/g22-a2-v3/bisect_*.log`):

| Commit | Vai | Spec tại commit đó | Kết quả |
|---|---|---|---|
| `0d55255` | **trước wave G22** (cha của `05eecf1`) | bản cũ (`cccd275`) | **10 passed · 0 failed · exit 0 (11.2 s)** |
| `f72a52e` | AG-06 dot 3 — **spec được viết lại tại đây** | bản mới | **1 failed · 7 did not run · 2 passed (45.1 s)** |
| `209a2e4` | merge nhánh AG-06 vào integration | bản mới | 1 failed · 7 did not run (44.7 s) |
| `a76ec51` | merge gộp `-X ours` của AG-00 | bản mới | 1 failed · 7 did not run (44.8 s) |
| `dd788fc` | nền vòng 2 | bản mới | 1 failed · 7 did not run (44.9 s) |
| `38f806e` | HEAD trước mọi sửa đổi của vòng 3 | bản mới | 1 failed · 7 did not run (44.9 s) |
| `a6b5b73` | HEAD hiện tại (đo trong làn đầy đủ) | bản mới | `(57, 1, 7)` toàn bộ 65 ca |

⇒ **Kết luận phải nói thẳng:** `B2` **KHÔNG** có trước wave G22 — trên `0d55255` (trước wave) ca
này **xanh 10/10**. Nó **sinh ra trong wave**, tại `f72a52e` (AG-06 dot 3 viết lại
`01_luong_chinh.spec.js` + `admin/logic.js`), và **có mặt ở mọi commit từ đó tới nay**, gồm cả
`dd788fc`/`38f806e`. Vì vậy nó là **có sẵn so với vòng 2 và vòng 3** (không do hai vòng QA này),
nhưng **không phải "lỗi có sẵn trước wave"**. Chủ sở hữu vẫn là **AGENT 01 / AG-06 FRONTEND**.

Một chi tiết đo được, để không ai dùng nó làm bằng chứng sai: chạy **spec MỚI trên cây TRƯỚC
wave** thì nó đỏ ở một assert khác (`khung lọc không nói máy chủ TỪ CHỐI tham số lạ`, vì UI cũ
chưa có câu đó) — tức spec mới gắn với UI của wave, nên phép so "spec mới × cây cũ" **không**
dùng để kết luận pass/fail sản phẩm được. Bảng bisect ở trên dùng **spec cùng thời** với từng
commit.

---

## 4. BẰNG CHỨNG ĐỐI CHỨNG ÂM / DƯƠNG (VÒNG 3)

| Phép đo | Đối chứng DƯƠNG | Đối chứng ÂM |
|---|---|---|
| `A1` nền đọc tại chỗ | clone sạch: `write-tree = HEAD^{tree}` ⇒ XANH; commit thật trong clone (HEAD `a6b5b73 → 7887793df1b7`, cây `8f390317 → 9ebad2f2`) ⇒ vẫn XANH | sửa/thêm tệp ngoài phạm vi ⇒ ĐỎ `CÂY BẨN NGOÀI PHẠM VI`; `git add` ⇒ ĐỎ `INDEX VÀ HEAD LỆCH NHAU` (`46017e14 ≠ 8f390317`); xoá index ⇒ ĐỎ `KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX`; HEAD hỏng ⇒ ĐỎ `KHÔNG ĐỌC ĐƯỢC HEAD` |
| `tree_hien_tai()` | tiêm 1 mục vào bản sao index ⇒ tree ĐỔI (`8f390317 → 867891278559`); index thật sha256 không đổi (`57d02bcbe47e2cf8` trước = sau); không lock | nếu trả hằng số/đọc nhầm cây, vế D3 ở trên sẽ lộ ra (HEAD đổi mà kết quả không đổi) |
| số ca E2E | `--list` = 65/8 khớp báo cáo chạy thật (`65 = 57+1+7`, `8 = 8+0+0`) | bỏ 1 dòng khai ca trong bản sao TẠM: `8 → 7`; hạ 1 ca trong báo cáo: `(64,0,0)`/`(7,0,0)` ⇒ cổng ĐỎ |
| `E1` 3 cổng cây sạch | clone tại HEAD: 3/3 XANH; cây thật: 3/3 XANH | tiêm tệp bẩn: 3/3 `DO_THAT` (không phải "phép đo chết") |
| `B2`/`B3` chạy thật | `B3` 8/8 đạt; `B2` 57 đạt | `B2` 1 hỏng + 7 không chạy ⇒ cổng ĐỎ, **không** bị tính là đạt |

**Bổ sung VÒNG 4 — `H_C4` / `C4` = `G19-C6` (chi tiết §0ter):**

| Phép đo | Đối chứng DƯƠNG | Đối chứng ÂM |
|---|---|---|
| `H_C4` đo tại chỗ | bản sao `app/` Y NGUYÊN ⇒ `(True, True)` đúng như cây thật; cây thật `146500b`: `app/server.py` (import 1 · dùng 3) | **GỠ TUYẾN LÀM THẬT** bằng AST trên chính bản sao: bỏ `import truy_van` + 2 khối `if` DÙNG nó (3 khối/21 dòng) ⇒ tệp sản xuất tham chiếu = **0**, cặp `(True, False)` ⇒ cổng **ĐỎ** (đòi ĐỎ) |

---

## 5. NHỮNG GÌ **KHÔNG** BỊ THAY ĐỔI / CHỐNG NỚI CỔNG

* **Không xoá ca, không đổi ca sang SKIP, không hạ assert.** `Ran` vẫn **24**.
* `dat_cong` / `phan_quyet`: **không sửa**. Giá trị "nửa vời" vẫn ĐỎ ở cả hai chế độ.
* `E1` **không còn `skipTest`** — nhưng không phải để "cho xanh": điều kiện skip cũ
  (`HEAD ≠ NEN_SHA`) không còn tồn tại vì `NEN_SHA` đã bị bỏ; nếu HEAD không đọc được thì `E1`
  **ĐỎ**, không skip.
* `B2` vẫn giữ đích `(65,0,0)`; **không** đổi thành `(57,1,7)` để lấy `EXIT 0`.
* Không sửa mã sản phẩm: `git status` chỉ có `app/thu/thu_qa_g22.py` + `docs/G22_CONTRACT.md`.
* Không sửa `thu_qa_g20.py`, `thu_qa_g21.py`, `thu_g20_dahang.py`; chỉ đọc/chạy.
* Không đụng `OWNER_ACTIONS C4` / **D-8** / `:5432`; `A3`/`A4` giữ nguyên. `C4`/`G19-C6` là việc
  KHÁC — vòng 4 chỉ ĐO phần TUYẾN đã đóng và **gỡ tuyến trên bản sao TMP** để chứng minh cổng có
  răng (§0ter.2/§0ter.3).
* Ngoài phạm vi hai tệp: chỉ tạo lại **symlink** trong `node_modules` (không được git theo dõi)
  — khai ở §2.3.
* `.git` của worktree **không bị ghi** bởi bộ kiểm: phép đo index dùng bản sao + ODB tạm;
  mọi thao tác phá `.git` của các đối chứng âm chỉ xảy ra trên **clone tạm trong TMP**.
* **VÒNG 5 — KHÔNG nới cổng `D1`, KHÔNG ép xanh:** `D1` không bị xoá, `Ran` vẫn **24**, `SO_DO`/
  `dat_cong`/`phan_quyet` **không sửa**. `D1` **ĐỎ** vì bàn đo G20 bên trong còn hỏng — đó là
  điều ĐÚNG phải xảy ra. Bốn đối chứng âm (a)–(d) + một dương của `D1` đều **chạy thật** trên
  tiến trình con (§0quater.3), không phải lời khai. `B2`/`B3` chỉ **THÊM** vế mã thoát, không
  hạ ngưỡng nào; không sửa `thu_qa_g20.py`/`thu_qa_g21.py`.

---

## 6. CÒN LẠI — NÓI THẲNG, KHÔNG GIẢ XANH

1. **`B2` (AGENT 01 / AG-06 FRONTEND):** ca 03 của `01_luong_chinh.spec.js` timeout ở bộ lọc
   nâng cao; 7 ca sau `did not run` do `serial`. Nó **có sẵn so với vòng 2/vòng 3**, nhưng
   **không có trước wave G22** — bisect đầy đủ ở §3.1 (mốc xanh gần nhất: `0d55255`). **Vòng 4:
   `B2` ĐÃ XANH trên `146500b`** (AG-06 vá backend thật: route `/api/v2/don` đi qua
   `app/truy_van.py`) — mục này giữ làm LỊCH SỬ BISECT, không còn là nợ. (`D1` vẫn che lỗi G20
   bên trong — xem mục 7.)
2. **Commit:** AG-00/Controller commit hộ. Giữa lượt vòng 3, `HEAD` đã nhích `38f806e → a6b5b73`
   (chính là phép thử sống của §0bis.4). Bản bàn giao **vòng 4** gồm **đúng hai tệp**:
   * `app/thu/thu_qa_g22.py` — sha256 `1d6f99a879a79b67e84a1905b87f0daa117fa13306e5a6fe46bccbfbf5f13880`
     (bản vòng 3, giữ làm lịch sử: `3a971f2b6479…`);
   * `docs/G22_CONTRACT.md` — tài liệu này.
   `git status` tại thời điểm bàn giao: `M app/thu/thu_qa_g22.py` + `M docs/G22_CONTRACT.md`.
   **Không push.**
3. **Nhị phân Chromium:** symlink `.local-browsers` **không được commit** (gitignore). Trên cây
   mới, phải dựng lại theo `docs/G21_BANPHIM_E2E.md` §10, nếu không `B1`/`B2`/`B3` sẽ báo
   "KHÔNG CHẠY ĐƯỢC" — không được skip.
4. **Ghim của lượt sau: KHÔNG CÒN.** `HEAD` nhích bao nhiêu lần cũng không có `NEN_SHA`/
   `TREE_NEN` nào phải cập nhật — đó là toàn bộ mục đích của vòng 3. Nếu ai đó thêm lại một cặp
   số viết cứng vào `A1`, họ đang tái sinh H5/N-G19-04.
5. **`OWNER_ACTIONS C4` / D-8:** giữ nguyên **BLOCKED OWNER**; không đo, không sửa, không ép
   xanh. (KHÁC `C4`=`G19-C6` — xem §0ter.2. Phần TUYẾN của `G19-C6` đã đóng; phần
   `DDL_G12Q`→`nang_len_v10` **còn treo**, chủ AG-02 backend — §0ter.5.)
6. **`nang_len_v10` (vòng 4):** `PHIEN_BAN_SCHEMA` vẫn **9**; **chưa** áp `truy_van.DDL_G12Q`
   cho CSDL đã ở v9. **Không** nhận `G19-C6` là đã xong hoàn toàn — xem §0ter.5.1.
7. **Bàn đo G20 (vòng 4 → ĐÃ SỬA Ở VÒNG 5):** cổng C4 của `thu_qa_g20.py` còn ghim trạng thái
   nền (`assertEqual(nhap, [])`, dòng 702) ⇒ ĐỎ trên `146500b`. **`D1` che nó** — nay `D1` đọc
   **mã thoát THẬT** và ĐỎ đúng (§0quater). Việc còn lại: chủ `thu_qa_g20.py` (Agent U2) sửa các
   ca hỏng bên trong; **không** sửa lén tệp đó ở đây.
8. **Worktree (vòng 4):** `g22-a2-contract` còn ở `a6b5b73`; sandbox chặn ghi `.git` nên không
   fast-forward được lên `146500b` — bằng chứng chạy trên bản sao TMP (§0ter.4); AG-00 cần
   fast-forward/merge.
9. **`D1` (vòng 5):** đọc mã thoát thật + 4 đối chứng âm + 1 dương (§0quater.2/3). **Đang ĐỎ**
   vì G20 còn ít nhất 6 ca hỏng — **ĐỎ ĐÚNG**, không phải nợ của bộ kiểm. Không xoá ca, không hạ
   ngưỡng, không ép PASS.

---

## 7. CÁCH TỰ KIỂM LẠI

```sh
# 1) Toàn bộ — kỳ vọng VÒNG 6: Ran 24 · PASS 23 · FAIL 0 · SKIP 1 (Z9 mồi) · EXIT 0
#    (D1 nay XANH vì bàn đo G20 đã XANH: exit 0 · Ran 21 · OK (skipped=2/3 tuỳ môi trường git).)
python3 app/thu/thu_qa_g22.py

# 2) Các nhóm quyết định:
python3 app/thu/thu_qa_g22.py A_Nen        # Ran 4 · OK · EXIT 0 (A1 + 5 đối chứng)
python3 app/thu/thu_qa_g22.py C_BanPhim    # B1, B2, B3 OK khi CÓ nhị phân Chromium 1194 · EXIT 0
python3 app/thu/thu_qa_g22.py E_CaySach    # Ran 2 · OK · skipped=0 · EXIT 0
python3 app/thu/thu_qa_g22.py H_C4         # Ran 1 · OK · EXIT 0 (bộ ba C4 + gỡ tuyến/hạ schema ⇒ ĐỎ)
python3 app/thu/thu_qa_g22.py D_BanDoG20   # Ran 1 · OK · EXIT 0 (G20 exit 0) — VÒNG 6

# 3) Xem đối chứng âm trong log: A1 (cây bẩn · index≠HEAD · cây không đọc được · HEAD nhích),
#    B2/B3 (hạ 1 ca), E1 (tiêm tệp bẩn), H_C4 (GỠ `import truy_van` + khối route bằng AST
#    trên bản sao `app/` ⇒ bộ ba (T,T,T) → (T,T,F) ⇒ cổng ĐỎ; HẠ schema 10→9 ⇒ (F,T,T) ⇒ ĐỎ;
#    NÂNG 10→13 ⇒ (T,T,T) ⇒ XANH, chứng minh `>=` chứ không ghim đúng số),
#    D1 (bốn bàn đo GIẢ: (a) thoát 3 dù chữ nói OK · (b) thoát 0 mà có dòng FAIL ·
#        (c) `Ran 0 tests` · (d) tệp không tồn tại — cả bốn PHẢI ĐỎ; một bàn đo giả XANH PHẢI ĐẠT;
#        ba phép TIÊM vào GHIM (e)(f)(g) + một bản sao Y NGUYÊN — §9.3).
# 4) Kiểm sha256 nhị phân headless:
shasum -a 256 node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
# → a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040
```

> Số của vòng 3 (lịch sử): `Ran 24 · PASS 22 · failures=1 (B2) · skipped=1 (Z9) · EXIT 1`. Số của
> vòng 4: `Ran 24 · PASS 23 · FAIL 0 · SKIP 1 (Z9 mồi) · EXIT 0` — §0ter.4. Số của **vòng 5**:
> `Ran 24 · PASS 22 · FAIL 1 (D1 — ĐỎ ĐÚNG vì G20 còn hỏng) · SKIP 1 (Z9 mồi) · EXIT 1` —
> §0quater.4. Số của **vòng 6**: `Ran 24 · PASS 23 · FAIL 0 · SKIP 1 (Z9 mồi) · EXIT 0` — §9.7.

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

---

## 9. VÒNG 6 — GHIM CỦA BỘ ĐO SAU KHI GỘP U1..U5 (`task_889a1ddeccdb` · cây `5fc5f6f`)

**Phạm vi ghi:** `app/thu/thu_qa_g22.py` + tài liệu này. **KHÔNG** sửa `thu_qa_g20.py`,
`thu_qa_g21.py`, không sửa backend, không đụng cụm `:5432`. `OWNER_ACTIONS C4` = **D-8 vẫn
BLOCKED OWNER** — không thực hiện, không ép xanh.

### 9.1 Trạng thái ĐO ĐƯỢC trước khi sửa (cùng SHA `5fc5f6f`, cây SẠCH lúc bắt đầu)

| Bộ | Lệnh | Kết quả THẬT |
|---|---|---|
| G20 | `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` | `Ran 21 tests in 26.1s` · `OK (skipped=2)` · **EXIT 0** |
| G21 (cây sạch) | `VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py` | `Ran 24 tests in 51.2s` · `FAILED (failures=1, skipped=3)` · **EXIT 1** — CHỈ `test_g6_harness_gioi_han_tan_suat` = lỗi thật `N-G20-01`, chủ **V1/backend** |
| G22 | `VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py` | `Ran 24 tests in 27.666s` · `FAILED (failures=8, skipped=1)` · **EXIT 1** |

Tám ca ĐỎ của G22, phân loại THEO NGUYÊN NHÂN (không phải theo tên):

1. **GHIM CŨ** (đối tượng của vòng này): `D1` (`BAN_DO_G20_GOC_SHA`), `I1`+`I2`(a)(b) (ghim **và**
   cây gương thiếu mô-đun — §9.6), `H1` (đối chứng đòi `sau["tep"] == []`, SAI từ khi `migrate.py`
   cũng chạm `truy_van`, + `== 9`/sàn v9 cũ).
2. **HỆ QUẢ**: `Z6` — hai nhóm `c4-go-route`/`c5-tru-bo-qua` chưa kịp bật cờ vì `H1`/`I1` hỏng.
3. **MÔI TRƯỜNG**: `B2`, `B3` — worktree này THIẾU `node_modules/playwright-core/.local-browsers/`.
   `B1` vẫn xanh vì có đường dự phòng, nhưng `chay.sh` CHỈ tìm trong `node_modules` cục bộ ⇒
   `Executable doesn't exist`. Đây là **hạ tầng**, không phải sản phẩm — xử lý ở §9.8.

> **Số ca:** bộ tệp này có **24 ca** ở `5fc5f6f` (không phải 29). Không ca nào bị xoá trong lượt
> này: **24 trước = 24 sau**. Mọi đối chứng mới được nhúng vào `D1`/`H1`, không thêm ca giả.

### 9.2 GHIM "cũ → mới" — HAI ô cho MỖI tệp, và NGUỒN là PHÉP TÍNH TẠI CHỖ

Trước vòng này mỗi tệp chỉ có MỘT ô: sha256 của bản **hoàn vá** (`..._GOC_SHA`). Nó bắt được
"tệp khác bản gốc", nhưng KHÔNG bắt được "nội dung bị đổi rồi hoàn vá vẫn khớp" — và nó không
nói thẳng "tệp trong cây đã bị đổi". Nay mỗi tệp có **hai** ô:

* `..._SHA_TRONG_CAY` — sha256 của ĐÚNG tệp đang nằm trong cây; đổi **một byte** ⇒ ĐỎ ngay;
* `..._GOC_SHA` — sha256 sau khi HOÀN VÁ hai/ba khối bộ đếm; chứng minh tệp đúng là
  "bản gốc đã chốt + đúng các khối vá".

| Tệp | Ô | Ghim CŨ | Ghim MỚI | Nguồn (tính tại chỗ, KHÔNG chép log) |
|---|---|---|---|---|
| `app/thu/thu_qa_g20.py` | `BAN_DO_G20_SHA_TRONG_CAY` | — (chưa có ô này) | `b56062bc928f16f0db13eb4b806b20ad342c992f224ad4df70f6c446710b48dc` | `sha256(open(tệp,'rb').read())` |
| `app/thu/thu_qa_g20.py` | `BAN_DO_G20_GOC_SHA` | `5a4b3c83c45f2f2c465d2eed380f1f6f69583878ca9e3a5f910bd01c1a0ddcd0` | `6a96e294066abdd0be1c824a8f292df913d7344cb74b3b62463c9dcc13fe818f` | `sha256(_hoan_va(tệp, G20_C5_VA))` |
| `app/thu/thu_qa_g21.py` | `BAN_DO_G21_SHA_TRONG_CAY` | — (chưa có ô này) | `4e730aac79cbb4f7bc541d151e9d423a616635a4707cfce4c2e602fa9520d0a2` | `sha256(open(tệp,'rb').read())` |
| `app/thu/thu_qa_g21.py` | `BAN_DO_G21_GOC_SHA` | `4ebf21e8804246bda315fbe9bc1721625fad0ec2130c5036f235d4e04ca40700` | `6a97ef519b3433bfbf105048721bbd743354fc014e6d541efc4bc2364a9982be` | `sha256(_hoan_va(tệp, G21_G7_VA))` |

**Vì sao CẢ HAI giá trị đều đổi:** U2 đã sửa THẬT `thu_qa_g20.py` (bỏ ghim stale C1/C4, thêm
`import thu_g21_chotcay`) và U3 đã sửa THẬT `thu_qa_g21.py` (bỏ ghim stale). Tệp đo đổi ⇒ ghim
phải đổi THEO, có ý thức. Lệnh + output đã chạy được ghi NGUYÊN VĂN ngay cạnh bốn hằng số trong
`thu_qa_g22.py`; không có giá trị nào được suy ra từ "cổng đang đỏ nên đổi số cho khớp".

**GHIM NÀY KHÔNG PHẢI ĐỂ BÁO XANH** — nó để phát hiện "bộ đo bị đổi giữa lượt". Vì thế nó phải
có ĐỐI CHỨNG ÂM, và đối chứng ấy được LÀM THẬT:

### 9.3 ĐỐI CHỨNG ÂM CỦA CHÍNH CÁI GHIM (LÀM THẬT trên bản sao trong `TMP`)

`D1` tiêm vào **bản sao** của tệp (cây thật không bị chạm) rồi gọi ĐÚNG `nguon_da_va()` mà ca
thật dùng. Output đo được:

```
(e) G20 — đổi 1 chữ NGOÀI khối vá   → ĐỎ ✓ · sha256 TỆP TRONG CÂY = dae351d4bf515a69 ≠ ghim
                                     b56062bc928f16f0 ⇒ `thu_qa_g20.py` ĐÃ BỊ ĐỔI
(f) G20 — đổi 1 chữ TRONG khối vá   → ĐỎ ✓ · KHÔNG hoàn vá được `thu_qa_g20.py`: khối vá không
                                     còn khớp nguyên văn ⇒ tệp KHÔNG PHẢI 'bản gốc + đúng khối vá'
(g) G21 — đổi 1 chữ NGOÀI khối vá   → ĐỎ ✓ · sha256 TỆP TRONG CÂY = c3b497d20c865782 ≠ ghim
                                     4e730aac79cbb4f7 ⇒ `thu_qa_g21.py` ĐÃ BỊ ĐỔI
(+) G20 — bản sao Y NGUYÊN          → ĐẠT ✓ · tệp trong cây b56062bc928f ✓ · gốc ghim
                                     6a96e294066a ✓ + đúng 2 khối vá
```

Ba phép tiêm nhắm **hai ô ghim khác nhau**: (e)/(g) bắt bởi ô "tệp trong cây"; (f) CỐ Ý gọi với
`sha_trong_cay=None` để chỉ kiểm ô "gốc" — nếu không, (e) và (f) sẽ cùng một đường và ô "gốc"
không bao giờ được chứng minh là có răng. Phép (+) chặn kiểu hỏng "ghim luôn Đỏ".

### 9.4 `PHIEN_BAN_SCHEMA == 9` → "SCHEMA TỐI THIỂU" (KHÔNG phải đổi 9 thành 10)

Đọc `app/csdl.py` + `app/migrate.py`: `csdl.PHIEN_BAN_SCHEMA = 10`; `nang_len_v10` là bước
DUY NHẤT áp `truy_van.DDL_G12Q` (9 câu `CREATE INDEX`), và `migrate.chay()` GỌI nó. Vậy **schema
tối thiểu mà `thu_qa_g22.py` cần** = mốc của chính bước áp `DDL_G12Q`.

Cách làm (trong tiến trình con của `_do_c4`, `MA_QUET_C4`):

```python
# moc_ddl_migration(goc): ast.parse(app/migrate.py)
#   → mọi FunctionDef tên `nang_len_v(\d+)` có Attribute `truy_van.DDL_G12Q`
#   → MỐC = min(N); đòi có lời gọi `nang_len_vN(...)` trong chính migrate.py
schema_ok  = moc is not None and csdl.PHIEN_BAN_SCHEMA >= moc   # >=, KHÔNG ==
chi_muc_ok = moc is not None and duoc_goi and hang_ddl            # hằng DDL_G12Q khác rỗng
```

Đo trên cây này: `moc_ddl=10` · `nang_len_v10` · `được gọi=True` · `DDL_G12Q` có **9 câu**.
Nếu ai bỏ mốc v10 (hoặc bỏ hằng DDL) ⇒ `moc=None` ⇒ vế schema/chỉ mục ĐỎ — nó **không** âm thầm
tụt về 9.

**ĐỐI CHỨNG ÂM "hạ schema" + ĐỐI CHỨNG DƯƠNG "nâng schema"** (LÀM THẬT, trên bản sao `app/`
trong TMP; sửa đúng một dòng `PHIEN_BAN_SCHEMA`):

```
hạ  10 → 9   → bộ ba (False, True, True) · schema_ok=False · dat_cong: ĐỎ ✓
nâng 10 → 13 → bộ ba (True, True, True)  · schema_ok=True  ⇒ KHÔNG ghim đúng một số
```

Vế "nâng" là vế quan trọng: nếu ai viết `== 10` (đổi 9 thành 10 đơn thuần) thì nó ĐỎ — đúng thứ
`msg_0b757445cfb8` cảnh báo.

### 9.5 `SO_DO` C4: CẶP → **BỘ BA**, và hai đối chứng âm riêng cho hai tầng

`G19-C6` có HAI tầng đóng ở hai mốc khác nhau; một cặp boolean không phân biệt được "thiếu
tuyến" với "thiếu chỉ mục". Sổ G22 thêm dòng:

```python
"c4-route-va-moc-ddl": {"nen": (False, False, False), "dong": (True, True, True)},
# (schema_ok, chi_muc_ok, tuyen_ok) — nền a6b5b73: schema 9, chưa có mốc DDL, chưa nối tuyến.
```

`SO_DO_G20` (sổ của bàn đo G20, ghi nguyên văn) **KHÔNG bị sửa** — nó là sổ của tệp khác.
`H_C4` đo `cap = (schema_ok, chi_muc_ok, tuyen_ok)` và dùng chính `dat_cong()` để phán, nên
"ĐỎ" ở đây là phán quyết của cổng, không phải của câu `assert`.

Đo trên cây thật: `(True, True, True)`; tham chiếu đếm được:
`app/migrate.py (import 1 · dùng 1 · DDL 1)`; `app/server.py (import 1 · dùng 3 · DDL 0)`.

**ĐỐI CHỨNG ÂM "GỠ TUYẾN"** (LÀM THẬT bằng AST, trên MỌI tệp sản xuất có tham chiếu TUYẾN):

```
gỡ 3 khối / 21 dòng khỏi app/server.py
  — import truy_van (1 dòng) · khối if DÙNG truy_van (tuyến) (15 dòng) · (5 dòng)
sau khi gỡ: bộ ba = (True, True, False) · tham chiếu còn lại: app/migrate.py (import 1 · dùng 1 · DDL 1)
dat_cong → ĐỎ (NỬA VỜI)
```

Vòng trước phép gỡ chỉ sửa `server.py` và đòi `sau["tep"] == []`; U4 thêm `import truy_van` vào
`migrate.py` ⇒ đòi hỏi đó thành SAI. Nay phép gỡ quét mọi tệp có tham chiếu **tuyến**, GIỮ NGUYÊN
tệp chỉ chạm `DDL_G12Q` (tầng chỉ mục có đối chứng "hạ schema" riêng), và có chốt "gỡ xong VẪN
còn DÙNG ⇒ ném" để không bao giờ kết luận trên một phép gỡ dở.

### 9.6 Hệ quả bắt buộc: cây gương của `I_TiemLoiC5` thiếu mô-đun hỗ trợ

`I1`/`I2` dựng cây gương trong TMP chỉ với HAI bàn đo + hai tệp tiêm. U2 đã cho
`thu_qa_g20.py` `import thu_g21_chotcay` ⇒ cột "SAU" chết với
`ModuleNotFoundError: No module named 'thu_g21_chotcay'` (một ĐỎ GIẢ của **môi trường cây
gương**, không phải của bản vá). Nay `_dung_cay_guong()` chép mọi mô-đun trong `app/thu/` **TRỪ**
`thu_qa_g19*` (hai tệp ấy do phép TIÊM viết — mẫu số phải giữ là **2**) và trừ chính hai bàn đo
(ghi đè ngay sau). Đo lại: mẫu số vẫn 2, và cột TRƯỚC/SAU tách đúng:

```
C5 & G7 · dị dạng v (mọi ca bỏ qua ở mức PHƯƠNG THỨC):
  TRƯỚC khi vá: thoát 0 · 1/2 · DONG ⇒ XANH     (lỗ hổng TÁI HIỆN được)
  SAU  khi vá: thoát 1 · 0/2 · NỬA VỜI ⇒ ĐỎ     (đã đóng)
I2 (đối chứng dương): thoát 0 · 1/2 · DONG ⇒ XANH ở CẢ HAI cổng
```

### 9.7 Kết quả SAU khi sửa — MÃ THOÁT THẬT

```
$ VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py
Ran 24 tests in 175.358s
OK (skipped=1)
ca: 24 · hỏng/loi: 0 · bỏ qua: 1 · MÃ THOÁT = 0
```

**Ran 24 · PASS 23 · FAIL 0 · SKIP 1 · EXIT 0.** SKIP 1 là `Z9` — **mồi CÓ CHỦ ĐÍCH** của `Z5`
(chạy trong tiến trình con để chứng minh bộ chạy có răng), không phải nợ và không được xoá.

Sáu ca từng ĐỎ, nay XANH (đo trong cùng lượt):

| Ca | Trước | Sau |
|---|---|---|
| `D_BanDoG20.test_d1` | FAIL (ghim G20 stale) | **ok** — G20 `exit 0 · Ran 21 · OK (skipped=3)` dưới D1 |
| `H_C4.test_h1` | FAIL (đối chứng đòi `tep == []`) | **ok** — bộ ba `(T,T,T)`, 3 đối chứng âm + 2 dương |
| `I_TiemLoiC5.test_i1` | FAIL (ghim stale) | **ok** — 5 dị dạng × 2 cổng × 2 cột |
| `I_TiemLoiC5.test_i2` (a)(b) | FAIL (cây gương thiếu mô-đun) | **ok** — `1/2 · DONG ⇒ XANH` cả hai cổng |
| `Z_ChotChan.test_z6` | FAIL (hệ quả) | **ok** — mọi nhóm phủ định có đối chứng chạy thật |
| `C_BanPhim.test_b2/b3` | FAIL (thiếu nhị phân) | **ok** — `(65,0,0,0)` / 8 ca, exit 0 (sau §9.8) |

G20 và G21 đo lại sau khi sửa (cây có `thu_qa_g22.py` đã sửa):

```
G20: Ran 21 · OK (skipped=2) · EXIT 0
G21 (CÂY SẠCH, bản sửa G22 đã commit trong CLONE TMP):
     Ran 24 · FAILED (failures=1, skipped=3) · EXIT 1 — CHỈ G6 (N-G20-01, V1)
```

> Vì sao G21 phải đo trên CLONE: `Z2` của `thu_qa_g21.py` đòi `git status` chỉ có các tệp của
> CHÍNH nó; worktree đang làm việc có `M app/thu/thu_qa_g22.py` (tệp của dispatch này, chưa
> commit) nên `Z2` ĐỎ **vì trạng thái làm việc**, không phải sản phẩm. Trên clone sạch
> (`git clone --shared` + commit bản sửa, `.git` nằm trong TMP — KHÔNG ghi `.git` thật) `Z2` XANH
> và chỉ còn G6. Đây cũng là bằng chứng "commit bản sửa rồi thì G21 trở lại đúng 1 đỏ".

### 9.8 MÔI TRƯỜNG: nhị phân Chromium của worktree này (không phải thay đổi mã)

`B2`/`B3` đỏ vì `node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/…`
KHÔNG có trong worktree (các worktree khác có). `B1` vẫn xanh nhờ đường dự phòng
`g17-ag06-security`, nhưng `chay.sh` ghim `PLAYWRIGHT_BROWSERS_PATH=0` nên chỉ tìm cục bộ.

Xử lý: chép THẲNG thư mục nhị phân revision 1194 từ worktree bên cạnh (`g22-a2-contract`) vào
`node_modules/…/.local-browsers/` — KHÔNG mạng, KHÔNG đổi mã. Kiểm lại:

```
$ shasum -a 256 node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell
a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040   ← ĐÚNG `PW_HEADLESS_SHA256`
```

`node_modules/` nằm trong `.gitignore` ⇒ `A1` (write-tree == HEAD^{tree}) và `A2` (phạm vi ghi)
KHÔNG đổi. Nói cách khác: đây là **sửa hạ tầng đo**, không phải sửa sản phẩm, và không ca nào
được "cho qua" bằng cách này — B2 vẫn phải ĐẠT **65/65 ca** thật.

### 9.9 G1/G5 — ĐO LẠI THEO HÀNH VI HIỆN TẠI, **KHÔNG SỬA**

`msg_0b757445cfb8` yêu cầu đo lại G1/G5 và chỉ sửa nếu chúng ghim HÀNH VI CŨ. Đo lại:

```
[G1] `test_c2a` chạy được · `assertFalse` (bất biến ĐÚNG) · `assertTrue` (ghim RÒ) = KHÔNG
     ĐỐI CHỨNG (a) `thu_qa_g21.py::G5_CredentialNgan` trên cây thật: rc=0 · tổ hợp RÒ=0/5
     ĐỐI CHỨNG (b) TIÊM tắt luật ECHO THEO TÊN: G5 đọc RÒ=2/5 · `test_c2a` rc=1 (ĐỎ ✓)
```

⇒ Chúng đang đo **bất biến ĐÚNG** (credential NGẮN không được rò), có đối chứng âm thật, và
XANH trên cây này. **Không sửa một dòng nào** — sửa sẽ là "sửa ca đang đúng". (AG-03 đã đóng
phần này; ghi nhận, không mở lại.)

`test_g5_ro_credential_ngan` trong `msg_0b757445cfb8` là ca của **bàn đo G21**, không phải của
`thu_qa_g22.py`; G21 đo lại ở §9.7 chỉ còn G6 đỏ.

### 9.10 Vì sao bản sửa này KHÔNG phải "ép PASS" / "nới cổng"

* **KHÔNG xoá ca** (24 → 24), **KHÔNG `skipTest`** mới, **KHÔNG hạ ngưỡng**, **KHÔNG sửa G20/G21**.
* `H_C4`: số vế TĂNG (2 → 3), số đối chứng âm TĂNG (1 → 3: gỡ tuyến, hạ schema; + nâng schema),
  và mỗi đối chứng đều hỏi `dat_cong()` — tức chính cổng phải ĐỎ, không chỉ `assert`.
* `D1`: thêm BA đối chứng âm cho GHIM (và một dương) — trước đây "ghim khớp" không phân biệt
  được với "ghim không kiểm gì".
* Schema: `== 9` → `>= MỐC` đọc tại chỗ; nếu ai bỏ mốc/cắt tầng chỉ mục, cổng ĐỎ — không có
  đường "đổi số cho khớp".
* `I1/I2`: mẫu số vẫn **2** (không nhét thêm bộ thật vào cây gương để làm loãng), chỉ chép
  mô-đun HỖ TRỢ mà chính hai bàn đo import.

### 9.11 CÒN ĐỎ / CÒN TREO — nói thẳng

1. **G21 `G6`** (`test_g6_harness_gioi_han_tan_suat`) = lỗi THẬT `N-G20-01`, chủ **V1/backend**.
   **KHÔNG sửa ở đây** (đúng đề bài). Trên cây sạch, đó là ca ĐỎ DUY NHẤT của G21.
2. **`OWNER_ACTIONS C4` = D-8** (chuyển CSDL nghiệp vụ sang PostgreSQL) vẫn **BLOCKED OWNER** —
   không thực hiện, không đụng `:5432`. `C4` trong tài liệu này là `G19-C6`, việc KHÁC.
3. **Worktree này chưa commit** bản sửa (`M app/thu/thu_qa_g22.py`, `M docs/G22_CONTRACT.md`).
   Commit/push thuộc AG-00/Controller — theo ràng buộc "không push" của dispatch.
4. **`node_modules` của worktree này** vừa được bổ sung nhị phân Chromium (không tracked). Nếu
   chạy ở worktree khác thiếu nhị phân, `B2/B3` sẽ đỏ vì MÔI TRƯỜNG — không phải vì bản sửa này.

