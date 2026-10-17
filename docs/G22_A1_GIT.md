# G22 · A1 — GIT SANDBOX: ĐO `write-tree` BẰNG MỘT MÔI TRƯỜNG HỢP LỆ

> **Vai:** AG-03 (CODE AGENT) · **Nhiệm vụ:** `task_26893671ed79` · **Dispatch:** `ctx_25573d797cba`
> **Nền đo:** `integration/g20 @ a76ec51c9931b62451721302446d7c3b74b9c81f` — cây
> `4676e5c53288e21e7c1a87e6bdde9a12c295a147`.
> **KHÔNG** dùng `main` (`de740dc`): `main` không chứa G13–G22. **KHÔNG** mở G23.
> **Phạm vi ghi của tôi:** `app/thu/thu_g22_a1.py` (mới) · `trien_khai/g22-a1/*` (mới) ·
> `docs/G22_A1_GIT.md` (mới). **KHÔNG** sửa `app/thu/thu_qa_g22.py` — ca `test_a1_*` thuộc AG-02.

---

## 0. TÓM TẮT MỘT MÀN HÌNH

| # | Việc | Kết quả ĐO ĐƯỢC | Bằng chứng |
|---|---|---|---|
| A1-1 | `git write-tree` **trần** trong worktree này | **CHẶN** — `rc=128` · `Unable to create '…/worktrees/g22-a3-gitsandbox/index.lock': Operation not permitted` | §1.2 · `bang_chung_a1.log` |
| A1-2 | `git write-tree` **tương đương** bằng index tạm + ODB tạm + alternates chỉ-đọc | **CHẠY** — `rc=0` · tree `4676e5c5…` = `HEAD^{tree}` · **index thật không đổi** | §3 · `bang_chung_a1.log` |
| A1-3 | Môi trường **cô lập** `git clone --shared` + `checkout --detach` trong `TMP` | **CHẠY** — `rc=0` · tree `4676e5c5…` = `HEAD^{tree}` | §4 · `bang_chung_a1.log` |
| A1-4 | **Đối chứng dương**: tiêm 1 mục vào **bản sao** index | tree **ĐỔI** `4676e5c5… → 5bf63bb3…` · index thật vẫn nguyên | §3.4 · `bang_chung_a1.log` |
| A1-5 | Ca `test_a1_*` trong **bản sao ghi được `.git`**, ghim ĐÚNG lượt | **XANH** — `Ran 1 test · OK · rc=0` | §4.3 · `bang_chung_ghim_clone.log` |
| A1-6 | Cùng ca đó nhưng **ghim cũ** `3b7e93b/37079aa8` | **ĐỎ** — `write-tree=4676e5c5` ≠ `TREE_NEN=37079aa8` | §5 · `bang_chung_ghim_clone.log` |

**Trả lời câu hỏi của đề bài:** **A1 ĐO ĐƯỢC** trong môi trường hợp lệ, bằng **hai** đường —
(A) đo tại chỗ bằng index tạm (khuyến nghị cho `test_a1_*`, xem §3.3) và (B) chạy trong bản sao
cô lập (đã là cách chạy toàn bộ bộ kiểm, xem §4). Ngoài lỗi sandbox còn **một nguyên nhân ĐỎ
THỨ HAI, độc lập**: **ghim `TREE_NEN` của bộ kiểm chính thức đang là cây của lượt TRƯỚC**
(§5). Sửa môi trường mà không sửa ghim thì A1 **vẫn ĐỎ** — và đó là ĐỎ DO GHIM, không phải do
môi trường.

---

## 1. LỖI THẬT — TÁI HIỆN, KHÔNG SUY ĐOÁN

### 1.1 Hai lỗi môi trường ĐỘC LẬP, và thứ tự của chúng quan trọng

**(a) `GIT_CONFIG_COUNT=2` thiếu `GIT_CONFIG_KEY_*`** — đã ghi ở `docs/OWNER_ACTIONS.md` §F:

```sh
$ env | grep '^GIT_CONFIG'
GIT_CONFIG_COUNT=2
GIT_CONFIG_VALUE_0=false
GIT_CONFIG_VALUE_1=false
# KHÔNG có GIT_CONFIG_KEY_0 / GIT_CONFIG_KEY_1

$ git rev-parse HEAD
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
rc=128
```

Lỗi này nổ **trước** khi git kịp mở `.git`, nên nếu không gỡ nó thì phép đo nhìn thấy **sai
nguyên nhân**. Bộ kiểm chính thức đã có `_git_env()` gỡ gia đình biến này để **đo được** (không
phải để "cho xanh" — ca `C3` của bàn đo G20 mới là ca đo môi trường nguyên bản). Script của tôi
cũng gỡ đúng như vậy:

```sh
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git …
```

**(b) Sandbox chặn GHI vào gitdir của worktree** — đây mới là lỗi A1:

```sh
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git write-tree
fatal: Unable to create '/Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a3-gitsandbox/index.lock':
       Operation not permitted
rc=128
```

### 1.2 Đúng lệnh nào, đúng đường nào

| Thành phần | Giá trị ĐO ĐƯỢC | Cách đo |
|---|---|---|
| Lệnh bị chặn | `git write-tree` | §1.1(b) |
| Nơi bị chặn | `/Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a3-gitsandbox/index.lock` | `git rev-parse --git-dir` |
| Thông báo | `Unable to create '…/index.lock': Operation not permitted` | stderr, `rc=128` |
| Worktree (gốc được ghi) | `/Users/viporder/orca/workspaces/vip-express-hub/g22-a3-gitsandbox` | `git rev-parse --show-toplevel` |
| gitdir | **NGOÀI** gốc được ghi: `/Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a3-gitsandbox` | `.git` là **tệp** con trỏ: `gitdir: /Users/viporder/Projects/…` |
| Nhánh đọc (không ghi) | `rev-parse`, `ls-files`, `status`, `show` chạy `rc=0` | log §0 |
| `index` thật | sha256 `283acae98addd21020b2bedb5e7505263233632a9a23b61e80c0075fe99f0aa3` | TRƯỚC và SAU mọi phép đo **giống hệt** |
| `index.lock` | **KHÔNG** có trước, **KHÔNG** có sau | không xoá gì; không có gì để xoá |

**Vì sao đây là lỗi môi trường, không phải lỗi sản phẩm:** `index` đọc được, object đọc được,
`HEAD` đúng nền; chỉ **đường GHI** bị chặn. Cùng lệnh trong một bản sao nằm ở `TMP` trả `rc=0`
(§4). Không có thay đổi nào của sản phẩm làm `write-tree` hỏng.

### 1.3 `git write-tree` CẦN gì — kiểm tra quyền, không đoán

`write-tree` ghi **hai** thứ, cả hai đều nằm trong gitdir:

1. **`<gitdir>/index.lock`** rồi cập nhật `<gitdir>/index` (cache-tree extension) — đây là chỗ
   nổ trước tiên;
2. **object mới** vào `<gitdir>/objects` khi cây cần dựng object chưa có.

Cả hai đường đều **ra ngoài** gốc được sandbox cho ghi ⇒ `EPERM`. Bằng chứng quyền theo chiều
DƯƠNG (để chứng minh phép đo không phải "đoán rằng mọi thứ đều bị chặn"):

```sh
$ mktemp -d /tmp/… && echo hello > /tmp/…/x       # ghi TMP: rc=0
$ cp <gitdir>/index /tmp/…/index                   # ĐỌC gitdir: rc=0
$ git clone --shared --no-checkout <worktree> /tmp/…/cp   # GHI .git trong TMP: rc=0
$ git -C /tmp/…/cp checkout --detach a76ec51        # rc=0
$ git -C /tmp/…/cp write-tree                       # rc=0 · 4676e5c5…
```

⇒ Quyền POSIX của người dùng **không** phải nguyên nhân (không `chmod`, không `sudo`, không xoá
lock). Đây là **lớp sandbox** chỉ cho ghi dưới workspace + vùng tạm.

---

## 2. TRẢ LỜI: A1 CÓ ĐO ĐƯỢC KHÔNG?

**CÓ.** Hai đường, cả hai đều cho **cùng một giá trị nội dung** `4676e5c5…`:

| | Đường A — index tạm (tại chỗ) | Đường B — bản sao cô lập |
|---|---|---|
| Lệnh | `GIT_INDEX_FILE=<tmp>/index GIT_OBJECT_DIRECTORY=<tmp>/objects GIT_ALTERNATE_OBJECT_DIRECTORIES=<common>/objects git write-tree` | `git clone --shared --no-checkout <worktree> <tmp>/cp && git -C <tmp>/cp checkout --detach <NEN>` rồi `git write-tree` |
| `rc` | **0** | **0** |
| tree | `4676e5c53288e21e7c1a87e6bdde9a12c295a147` | `4676e5c53288e21e7c1a87e6bdde9a12c295a147` |
| `HEAD` | `a76ec51c9931b62451721302446d7c3b74b9c81f` | `a76ec51c9931b62451721302446d7c3b74b9c81f` |
| Ghi vào `.git` thật | **KHÔNG** (index thật sha không đổi, không lock) | **KHÔNG** (chỉ đọc nguồn) |
| Đo cái gì | **ĐÚNG index đang có** của worktree chính | nội dung của commit `NEN_SHA` sau checkout |
| Dùng cho | **`test_a1_*`** (AG-02) | **toàn bộ bộ kiểm** (đã là cách chạy ở `docs/QA_G22.md` §1.2) |

Đường A **tương đương tuyệt đối** với `write-tree` trần: cùng index, cùng cách phân giải object
(alternates **chỉ đọc** trỏ vào ODB thật), chỉ khác **nơi ghi**. Vì vậy nó đo **đúng câu hỏi của
A1** — "cây của index đang có là gì" — chứ không phải cây của một commit được checkout sẵn.

---

## 3. ĐƯỜNG A — ĐO TẠI CHỖ, KHÔNG GHI `.git` THẬT (khuyến nghị cho `test_a1_*`)

### 3.1 Cơ chế

```
<gitdir>/index          --copy-->  <tmp>/index            (GIT_INDEX_FILE)
<tmp>/objects           <--ghi--   write-tree            (GIT_OBJECT_DIRECTORY)
<common>/objects        --đọc-->   object cũ             (GIT_ALTERNATE_OBJECT_DIRECTORIES)
```

Mọi thứ cần **GHI** rơi vào `<tmp>`; mọi thứ cần **ĐỌC** lấy từ kho thật. Không có `index.lock`
nào được tạo trong gitdir thật.

### 3.2 Lệnh shell tối thiểu — chạy thật, kết quả thật

```sh
# Shell của lượt này: gỡ biến GIT_CONFIG dị dạng TRƯỚC (xem §1.1a), nếu không mọi lệnh git rc=128.
$ GIT="env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git"
$ GD=$($GIT rev-parse --git-dir)
$ CD=$($GIT rev-parse --git-common-dir)
$ TMP=$(mktemp -d /tmp/g22-a1-XXXXXX); mkdir -p "$TMP/objects"
$ cp "$GD/index" "$TMP/index"

$ GIT_INDEX_FILE="$TMP/index" \
  GIT_OBJECT_DIRECTORY="$TMP/objects" \
  GIT_ALTERNATE_OBJECT_DIRECTORIES="$CD/objects" \
  $GIT write-tree
4676e5c53288e21e7c1a87e6bdde9a12c295a147
# rc=0

$ shasum -a 256 "$GD/index"
283acae98addd21020b2bedb5e7505263233632a9a23b61e80c0075fe99f0aa3   # KHÔNG ĐỔI
$ ls "$GD" | grep -c index.lock
0
```

### 3.3 Đoạn Python CHÍNH XÁC để AGENT 02 thay `tree_hien_tai()`

Đây là thay đổi **nhỏ nhất** và đúng chỗ: `tree_hien_tai()` đang được **cả** `van_tay()` (A1/A2,
vân tay) **và** `main()` (tự đo môi trường) dùng. Thay hàm này là mọi chỗ gọi nó tự động đo được.

```python
def tree_hien_tai():
    """write-tree TƯƠNG ĐƯƠNG, KHÔNG ghi `.git` của worktree chính (A1 · AG-03).

    Sandbox chỉ cho ghi dưới workspace + TMP; gitdir của worktree nằm ngoài ⇒ `git write-tree`
    trần trả rc=128 (`index.lock: Operation not permitted`). Đo bằng BẢN SAO index + ODB tạm;
    object cũ đọc qua alternates CHỈ ĐỌC. Cây trả về là cây của ĐÚNG index đang có.
    """
    def _out(*tham_so):
        rc, out = chay(["git"] + list(tham_so))
        dong = [d.strip() for d in out.splitlines() if d.strip()]
        return dong[-1] if rc == 0 and dong else ""

    git_dir = _out("rev-parse", "--git-dir")
    common = _out("rev-parse", "--git-common-dir")
    if not git_dir or not common:
        return "LỖI(rc=128)"
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(GOC_CAY, git_dir)
    if not os.path.isabs(common):
        common = os.path.join(GOC_CAY, common)
    tmp = tempfile.mkdtemp(prefix="g22-a1-")
    try:
        os.makedirs(os.path.join(tmp, "objects"), exist_ok=True)
        index_tam = os.path.join(tmp, "index")
        shutil.copy2(os.path.join(git_dir, "index"), index_tam)
        rc, out = chay(["git", "write-tree"], env_them={
            "GIT_INDEX_FILE": index_tam,
            "GIT_OBJECT_DIRECTORY": os.path.join(tmp, "objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.path.join(common, "objects"),
        })
        dong = [d.strip() for d in out.splitlines() if d.strip()]
        return dong[-1] if rc == 0 and dong else "LỖI(rc=%d)" % rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

`os`, `shutil`, `tempfile`, `GOC_CAY`, `chay` **đã có sẵn** trong `thu_qa_g22.py`. Không cần
thêm import nào.

### 3.4 ĐỐI CHỨNG DƯƠNG — chứng minh phép đo KHÔNG MÙ

Ca `test_03` của `app/thu/thu_g22_a1.py` tiêm **một mục mới** vào **bản sao** index (blob mới ghi
vào ODB tạm, mục mới ghi vào index tạm) rồi đo lại:

```
[A1-03] blob mới       = a7c10aa40c0d53655f0b3667764e9e643d05e6b5
        tree TRƯỚC    = 4676e5c53288e21e7c1a87e6bdde9a12c295a147
        tree SAU      = 5bf63bb330be65b0c68e2f7682e3947b9af1ad6d
        ĐỔI           = True
        sha256(index thật) TRƯỚC = SAU = 283acae98addd21020b2bedb5e7505263233632a9a23b61e80c0075fe99f0aa3
```

⇒ Phép đo **nhìn thấy** thay đổi, và **không** làm bẩn index thật. Nếu AGENT 02 muốn nhúng đối
chứng này vào `test_a1_*` (đúng luật "mọi ca phủ định phải có đối chứng dương"), chỉ cần:

```python
import sys
sys.path.insert(0, GOC_THU)          # GOC_THU đã có sẵn trong thu_qa_g22.py
import thu_g22_a1                    # bộ đo AG-03, chỉ ĐỌC + ghi trong TMP

# … trong test_a1_*:
kq = thu_g22_a1.tiem_index_ban_sao()
self.assertEqual(kq["rc"], 0)
self.assertNotEqual(kq["tree_sau"], vt["tree"], "phép đo MÙ — tiêm thay đổi mà cây không đổi")
self.assertEqual(kq["index_sha256_sau"], kq["index_sha256_truoc"], "index thật bị đổi")
```

### 3.5 Giới hạn — nói thẳng

* Đường A đo **index**, đúng như `write-tree` trần. Thay đổi **chưa stage** trong working tree
  **không** làm đổi cây — đó là ngữ nghĩa Git, không phải lỗi phép đo.
* Nếu index đang bị tiến trình khác khoá/ghi đồng thời, bản sao có thể lệch một nhịp. Bộ kiểm
  chạy đơn tuyến; rủi ro thấp, nhưng phải biết.
* Nếu ODB thật **thiếu** blob mà index tham chiếu (partial clone), alternates không cứu được;
  `write-tree` sẽ báo lỗi. Repo này đủ object (đo được).

---

## 4. ĐƯỜNG B — BẢN SAO CÔ LẬP (cách chạy TOÀN BỘ bộ kiểm)

### 4.1 Lệnh — chạy thật

> Trong shell của lượt này, mọi lệnh `git` dưới đây được chạy qua
> `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1` (§1.1a); ở đây viết gọn
> là `git` cho dễ đọc. Script `trien_khai/g22-a1/do_moi_truong.sh` tự gỡ.

```sh
$ TMP=$(mktemp -d /tmp/g22-a1-XXXXXX)
$ git clone --shared --no-checkout /Users/viporder/orca/workspaces/vip-express-hub/g22-a3-gitsandbox "$TMP/cp"
Cloning into '…/cp'...
done.
# rc=0

$ git -C "$TMP/cp" checkout --detach a76ec51
HEAD is now at a76ec51 AG-00: GOP BAN VA C5/G7 CUA AG-01 VAO CAY TICH HOP (sua loi gop -X ours)
# rc=0

$ git -C "$TMP/cp" rev-parse HEAD
a76ec51c9931b62451721302446d7c3b74b9c81f
$ git -C "$TMP/cp" write-tree
4676e5c53288e21e7c1a87e6bdde9a12c295a147
# rc=0
```

### 4.2 Vì sao đường B hợp lệ — và cái bẫy của nó

Đường B tạo một kho **BÌNH THƯỜNG** trong `TMP`: `HEAD` = nền, cây SẠCH, và `git init` của bộ
thử khác **không chạm tới** nó (khác với đường `GIT_DIR` bóng đã hỏng — `docs/QA_G22.md` §1.2).
Vì vậy chạy **cả bộ kiểm** trong đó là cách đúng.

**Cái bẫy:** nếu chỉ `checkout NEN` rồi đo `write-tree`, giá trị **bằng đúng** `NEN^{tree}` theo
định nghĩa — phép đo thành **hiển nhiên đúng** (tautology), không chứng minh cây của worktree
chính. Vì thế:

* Dùng đường B cho **toàn bộ bộ kiểm** (nơi mọi cổng cùng đo trên một cây đã checkout).
* Dùng **đường A** cho **riêng A1** nếu muốn A1 đo **đúng worktree chính**.
* Hoặc **đối chiếu chéo**: `thu_g22_a1.write_tree_an_toan()["tree"]` (worktree chính) **phải
  bằng** `write-tree` trong bản sao. Hai phép đo độc lập cùng giá trị ⇒ không tautology.

### 4.3 Bằng chứng tách nguyên nhân — A1 trong bản sao ghi được `.git`

`trien_khai/g22-a1/bang_chung_ghim_clone.log` (chạy thật, `rc` đọc ngay sau lệnh):

```sh
# (1) A1 NGUYÊN BẢN — ghim cũ 3b7e93b/37079aa8
$ cd <tmp>/cp && python3 app/thu/thu_qa_g22.py A_Nen.test_a1_cay_dung_bang_cay_cua_nen
  [A1] HEAD=a76ec51c9931 · write-tree=4676e5c53288 · 379 tệp theo dõi · băm danh sách=9d4e1abd658b4927
  Ran 1 test in 0.037s
  FAILED (failures=1)
rc=1

# (2) BẢN SAO CHỈ ĐỔI GHIM: NEN_SHA 3b7e93b→a76ec51 · TREE_NEN 37079aa8→4676e5c5
$ python3 app/thu/thu_qa_g22_ghim_moi.py A_Nen.test_a1_cay_dung_bang_cay_cua_nen
  [A1] HEAD=a76ec51c9931 · write-tree=4676e5c53288 · 379 tệp theo dõi · băm danh sách=9d4e1abd658b4927
  Ran 1 test in 0.033s
  OK
rc=0
```

⇒ Trong **cùng một môi trường ghi được `.git`**, `write-tree` trả đúng `4676e5c5…`; A1 chỉ đổi
từ ĐỎ sang XANH khi **ghim** đổi. Vậy nguyên nhân ĐỎ của A1 hiện tại gồm **đúng hai** thứ:
**(1) sandbox chặn ghi `.git`** và **(2) ghim nền là cây của lượt trước**. Không có nguyên nhân
thứ ba.

---

## 5. PHÁT HIỆN THỨ HAI — GHIM `TREE_NEN` ĐANG LÀ CÂY CỦA LƯỢT TRƯỚC

Đo trực tiếp (chỉ đọc):

```sh
$ grep -n '^NEN_SHA =\|^TREE_NEN =' app/thu/thu_qa_g22.py
107:NEN_SHA = "3b7e93b59b70449b8306eb4fa374dd1e97a8e7af"
108:TREE_NEN = "37079aa83f2ad62c2862f2eb7ce1c809c24570fb"

$ git rev-parse a76ec51^{tree}
4676e5c53288e21e7c1a87e6bdde9a12c295a147
$ git merge-base --is-ancestor 3b7e93b a76ec51 ; echo $?
0
```

| | `NEN_SHA` | `TREE_NEN` |
|---|---|---|
| Ghim trong bộ kiểm chính thức (`sha256 1c5d955f…`) | `3b7e93b59b70449b8306eb4fa374dd1e97a8e7af` | `37079aa83f2ad62c2862f2eb7ce1c809c24570fb` |
| Nền của lượt này: `integration/g20 @ a76ec51` | `a76ec51c9931b62451721302446d7c3b74b9c81f` | **`4676e5c53288e21e7c1a87e6bdde9a12c295a147`** |
| Khớp? | **KHÔNG** | **KHÔNG** |

Đây là **cùng loại việc** đã được ghi ở `docs/QA_G22.md` §10.5b (cập nhật ghim cho đúng cây
đang đo), nhưng lượt này **chưa** được cập nhật. **Tôi KHÔNG sửa** — `thu_qa_g22.py` thuộc phạm
vi AG-02. Đề nghị:

1. AG-02 (hoặc AG-00) cập nhật `NEN_SHA = "a76ec51…"`, `TREE_NEN = "4676e5c5…"` **theo hợp
   đồng của lượt**, không phải để "cho xanh"; hoặc
2. thêm một **ca tự kiểm ghim** để ghim lệch nổ ra như **lỗi GHIM**, không bị báo nhầm thành
   **lỗi MÔI TRƯỜNG**:
   ```python
   rc, out = chay(["git", "rev-parse", NEN_SHA + "^{tree}"])
   self.assertEqual(out.strip(), TREE_NEN, "TREE_NEN không phải cây của NEN_SHA — GHIM STALE")
   ```

`thu_g22_a1.py --kiem-ghim` **đã** làm đúng phép đối chiếu này và hiện **ĐỎ có chủ đích**
(`rc=1`) — xem §8.

---

## 6. BẢNG "BỊ CHẶN Ở ĐÂU / GỠ BẰNG GÌ"

| Việc | Bị chặn ở đâu | Thông báo thật | Gỡ bằng gì | Bằng chứng |
|---|---|---|---|---|
| Mọi lệnh git | **trước** khi mở repo | `missing config key GIT_CONFIG_KEY_0` / `unable to parse command-line config` | `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1` (bộ kiểm đã có `_git_env()`) | §1.1(a) |
| `git write-tree` (trần) | `<gitdir>/index.lock` | `Unable to create '…/index.lock': Operation not permitted` · `rc=128` | **Đường A**: index tạm + ODB tạm + alternates | §3.2 |
| `git write-tree` (trong bản sao) | không bị chặn | — · `rc=0` | **Đường B**: `clone --shared` + `checkout --detach` trong `TMP` | §4.1 |
| `git checkout`/`reset` trên worktree chính | `<gitdir>/index.lock` | cùng `EPERM` (đã ghi ở `docs/QA_G22.md` §1.2/§8.1) | **KHÔNG** tự vượt — báo AG-00 commit/checkout hộ | `docs/QA_G22.md` |
| A1 với ghim cũ | không phải môi trường | `write-tree=4676e5c5 ≠ TREE_NEN=37079aa8` | cập nhật ghim theo §5 | §4.3 |
| Chạy toàn bộ bộ kiểm trong worktree chính | nhiều lệnh cần ghi `.git` | — | chạy trong bản sao **Đường B** | §4 |

---

## 7. TUÂN THỦ VÀ KIỂM TRA CUỐI

**BLOCKED trong phạm vi A1: KHÔNG.** Không có việc nào của A1 phải chờ quyền mới đo được; hai
nguyên nhân ĐỎ đã định vị và đã có đường xử lý (§3, §4, §5). Phần còn lại là **bàn giao** cho
AG-02 (chủ tệp kiểm) và AG-00 (commit hộ), không phải BLOCKED của tôi.

**Đã KHÔNG làm:** không `sudo` · không `chmod` · không xoá `index.lock` (không có lock nào để
xoá) · không ghi `.git` của worktree chính · không sửa `index` · không sửa `thu_qa_g22.py` ·
không push · không deploy · không gọi API production · không tạo đơn · không sửa/xoá CSDL · không
mở G23 · không đụng `OWNER_ACTIONS C4`/D-8.

**Số đo cuối (cùng lượt chạy `do_moi_truong.sh`, `rc=0`):**

```
sha256(index) TRƯỚC = 283acae98addd21020b2bedb5e7505263233632a9a23b61e80c0075fe99f0aa3
sha256(index) CUỐI  = 283acae98addd21020b2bedb5e7505263233632a9a23b61e80c0075fe99f0aa3
index.lock CUỐI     = KHONG
write-tree TRẦN     = rc=128 (index.lock · Operation not permitted)
write-tree ĐƯỜNG A  = rc=0 · 4676e5c53288e21e7c1a87e6bdde9a12c295a147
write-tree ĐƯỜNG B  = rc=0 · 4676e5c53288e21e7c1a87e6bdde9a12c295a147
EXIT CODE THAT      = 0
```

**Năm tệp tôi đã tạo (chưa commit — worker bị chặn ghi `.git`, AG-00 phải commit hộ):**

```
?? app/thu/thu_g22_a1.py
?? trien_khai/g22-a1/do_moi_truong.sh
?? trien_khai/g22-a1/bang_chung_a1.log
?? trien_khai/g22-a1/bang_chung_ghim_clone.log
?? docs/G22_A1_GIT.md
```

Đề nghị AG-00:

```sh
git -C /Users/viporder/orca/workspaces/vip-express-hub/g22-a3-gitsandbox add \
    app/thu/thu_g22_a1.py trien_khai/g22-a1/ docs/G22_A1_GIT.md
git -C /Users/viporder/orca/workspaces/vip-express-hub/g22-a3-gitsandbox commit -m \
  "AG-03 (G22) A1 GIT SANDBOX: do write-tree bang index tam + ODB tam; clone co lap; A1 do duoc (4676e5c5)"
```

> **Vì sao phải commit hộ:** sandbox chặn ghi `.git` (chính là `L-G22-B`); tôi **không tự vượt**.
> Ngoài ra `test_a2_khong_sua_ma_san_pham` của bộ kiểm chỉ nhận 4 tệp trong `TEP_DUOC_PHEP`, nên
> khi 5 tệp này còn **chưa commit**, A2 sẽ thấy chúng là "ngoài phép" — một **ĐỎ GIẢ của phạm
> vi**, không phải của sản phẩm. Commit xong thì hết.

---

## 8. CHẠY LẠI TOÀN BỘ BẰNG CHỨNG

```sh
$ sh trien_khai/g22-a1/do_moi_truong.sh
# … in từng lệnh + rc …
# EXIT CODE THAT = 0

$ python3 app/thu/thu_g22_a1.py
# 5 ca · 0 hỏng · 0 bỏ qua · Ran 5 tests in ~0.5s · OK · MÃ THOÁT = 0

$ python3 app/thu/thu_g22_a1.py --kiem-ghim
# Ran 6 tests · FAILED (failures=1) · MÃ THOÁT = 1
#   ↑ ĐỎ CÓ CHỦ ĐÍCH: ghim TREE_NEN=37079aa8 ≠ cây đo được 4676e5c5 (xem §5)

$ python3 app/thu/thu_g22_a1.py --json
# thêm dòng __JSON__={…} để máy đọc (head, tree, sha index, ghim, số ca, mã thoát)
```

**SHA-256 của các tệp bằng chứng tại lượt đo này** (tài liệu này **không** tự băm chính nó —
`docs/BAN_GIAO.md` §7.3):

```
06e8583908e340df778413999b39746b514c51293c0f0bb680ec42525be7bec9  app/thu/thu_g22_a1.py
f0f249859050bfbd29a44ad6fa26518c07077f32f6980cfdcac2e888136da4e3  trien_khai/g22-a1/do_moi_truong.sh
48b014aef354e5a020fe5b93c839127481e6d3aa229e24704888aec71531bfcf  trien_khai/g22-a1/bang_chung_a1.log
8a4f46c6163a4d7d3f60f59ced59c16a87bfc143cf78eb5f6d9b14c0db3441b9  trien_khai/g22-a1/bang_chung_ghim_clone.log
1c5d955fa490d37ef6681d8176a5236d8dffc0414dc17bf450c24fc165c60cf7  app/thu/thu_qa_g22.py (ĐỌC, không sửa)
```

Nội dung `bang_chung_a1.log` gồm: khảo sát môi trường · lệnh trần `rc=128` + stderr · phương án
A `rc=0` · phương án B `rc=0` · 5 ca của `thu_g22_a1.py` · kiểm tra index/lock cuối · mã thoát.
`bang_chung_ghim_clone.log` gồm: clone/checkout/write-tree `rc=0` · A1 nguyên bản `rc=1` (ghim
cũ) · A1 bản chỉ đổi ghim `rc=0` (XANH).

---

## 9. VIỆC CÒN LẠI — CHỦ SỞ HỮU RÕ RÀNG

| # | Việc | Ai làm | Vì sao |
|---|---|---|---|
| 1 | Thay `tree_hien_tai()` bằng đoạn §3.3 vào `app/thu/thu_qa_g22.py`; thêm đối chứng dương §3.4 vào `test_a1_*` | **AG-02** (chủ tệp) | A1 đo được **ngay trong worktree chính**, không cần chạy cả bộ kiểm ở nơi khác |
| 2 | Cập nhật ghim `NEN_SHA`/`TREE_NEN` → `a76ec51`/`4676e5c5` **theo hợp đồng lượt**, hoặc thêm ca tự kiểm ghim | **AG-02 + AG-00 quyết** | Nếu giữ ghim cũ, A1 vẫn ĐỎ dù môi trường đã đúng — ĐỎ do GHIM, không do sản phẩm |
| 3 | Commit 5 tệp ở §7 | **AG-00 / Controller** | worker bị sandbox chặn ghi `.git`; không tự vượt |
| 4 | Khi chạy **toàn bộ** bộ kiểm: dùng bản sao **Đường B** tại đúng `NEN_SHA` | AG-02/AG-00 | tránh mọi lỗi ghi `.git` khác (checkout, reset, index.lock) |
| 5 | Không đụng `OWNER_ACTIONS C4` (PostgreSQL, **D-8, BLOCKED OWNER**) và không mở G23 | tất cả | quyết định đã chốt, không bàn lại |

**Kết luận để bàn giao:** A1 **không phải** "không đo được". Nó **đo được** bằng index tạm
(Đường A) hoặc bản sao cô lập (Đường B), với **cùng một giá trị** `4676e5c5…`; phép đo đã được
chứng minh **bắt được thay đổi** (`→ 5bf63bb3…`). Hai nguyên nhân ĐỎ hiện tại — **sandbox** và
**ghim cũ** — đều **đã định vị, đã có cách xử lý, và không cần nới bất kỳ điều kiện nào**.
