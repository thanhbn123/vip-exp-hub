# OWNER_ACTIONS — VIỆC CHỈ ANH THÀNH QUYẾT ĐƯỢC

> **Tài liệu này gom MỌI việc đang chặn tiến độ LOCAL, để anh xử một lượt.**
> **Mục nào bị chặn vì anh CHƯA CẤP QUYỀN thì KHÔNG phải lỗi của phần local** — nó là
> `BLOCKED`, không phải `FAILED`. Phần local đã và đang chạy độc lập được thì vẫn chạy.
>
> **AI-ASSISTED, KHÔNG PHẢI NGƯỜI SOÁT.** Mọi số trong tài liệu này do tác tử AI chạy trên máy này.
> `docs/BAN_GIAO.md` §2: *"AI review không phải human review. Bộ thử xanh không phải lời cho phép."*
> **Hệ này CHƯA production-ready.**

**Ngày lập:** 15/10/2026 · **Controller:** AG-00 (DeepSeek `dsh`, Orca Run `run_695b048104a9`)
**Mốc tự đo:** người đọc tự chạy `git log --oneline -1 integration/g17` — tài liệu này **không** ghi
SHA của chính commit chứa nó (`BAN_GIAO.md` §7.3).

---

## A. CẦN QUYỀN — không có thì không tiến được

| # | Việc | Cần chính xác cái gì | Chặn cái gì |
|---|---|---|---|
| **A1** | Gọi API J&T (kể cả **sandbox**) | **`V-G09-01`** — CHƯA CẤP | G21: gọi hãng thật, đối chiếu chữ ký/mã lỗi thật, TLS thật tới `*.jtexpress.vn` |
| **A2** | Credentials J&T | **`V-13906-05`** — CHƯA CẤP. Cần **4 TÊN trường**: `apiAccount` · `privateKey` · `customerCode` · `password` | Mọi lượt gọi hãng; hiện **chưa có tệp `.env` nào** |
| **A3** | Callback thật | **`V-G11-01`** — URL công khai — CHƯA CẤP | G22: callback thật, tunnel, HTTPS |
| **A4** | Docker | **`V-13913`** — cài Docker = **đổi máy** ⇒ cần duyệt riêng | G23: vận hành bằng container |
| **A5** | Bấm duyệt sandbox | Một số thao tác cần **anh bấm** hộp thoại cấp quyền (ghi `.git`, chạy Playwright). **AG-00 KHÔNG tự bấm, KHÔNG vượt chốt** | Các bước commit/tích hợp local |

## B. CẦN HÃNG J&T TRẢ LỜI — không đoán, không bịa

| # | Câu hỏi | Vì sao KHÔNG được đoán |
|---|---|---|
| **B1** | **Nghĩa mã trạng thái `110`** | Quyết định **D-4**: hệ **không thêm mã nào** vào bảng. `quyet_dinh("jt","110")` trả `None [AMBIGUOUS]`, `tin_cay='nhap_nhang'`, **không áp trạng thái**, `can_soat=1`. Đoán sai ⇒ đơn đi sai nhánh |
| **B2** | **Ánh xạ `area`/`city`** | Quyết định **D-9**: ví dụ của hãng đặt **quận vào `city`, phường vào `area`** — **ngược** với cách hệ đang dùng, và hệ **không gửi `city`**. Nay **CHẶN CỨNG** ngoài `mock`, có ca **ĐẾM** chứng minh khi chốt nổ thì số byte rời đi = **0** |
| **B3** | **`cancelOrder`**: tiền tố cổng + **TÊN trường lý do huỷ** | Đường dẫn CHƯA ĐỌC ĐƯỢC. Adapter giữ `duong=None` và **TỪ CHỐI** ngoài mock |
| **B4** | **`calculatingFees`**: đường dẫn + bảng tham số | như trên |
| **B5** | **`printOrder`**: đường dẫn + tham số | như trên |
| **B6** | **`getOrder`** (câu hỏi 26) | như trên |
| **B7** | **`timestamp` (a)/(b) · dạng `password`** (câu hỏi 12 và 22) | Chưa xác minh ⇒ không tự chọn |
| **B8** | **Hợp đồng callback** — 10 chỗ hở | `CHAN_HOP_DONG_CALLBACK` là **dữ liệu máy đọc được**, mỗi chỗ gắn **câu hỏi gửi hãng**. Năm mục anh chỉ định đều có: **khoá ký chiều callback** · **chuỗi đem đi ký** · **phương thức HTTP** · **hình dạng phản hồi** · **chính sách thử lại**. Mức vẫn `DOCUMENTED`; có ca canh **chống tự nâng mức** |

## C. CẦN ANH QUYẾT — không phải thiếu quyền, mà là chọn hướng

| # | Việc | Trạng thái |
|---|---|---|
| **C1** | Gộp `integration/g16` → `main` | `main` = `de740dc`. **`integration/g13-g15` CHƯA gộp vào `main`** (đã xác minh `--is-ancestor` thất bại). Mọi việc G16–G18 dựng trên nhánh tích hợp, **không** trên `main` |
| **C2** | Gộp `integration/g17` → `main` | Sau khi G18 xong và QA nghiệm thu |
| **C3** | `P-G15-02` | `migrate.sao_luu()` nên **ném `NotImplementedError`** khi chạy trên PostgreSQL không? — chờ anh quyết |
| **C4** | Chuyển CSDL nghiệp vụ sang PostgreSQL | Quyết định **D-8**: **CHƯA** chuyển. Vẫn SQLite. Có **điều kiện kích hoạt** đã đo, không phải cảm tính |
| **C5** | 5 worktree G12 cũ (`~/code/veh4-g12-*`) | **GIỮ NGUYÊN** theo chỉ đạo. Ghi chú: `veh4-g12-playwright` là nguồn `node_modules` **duy nhất** |

## D. LỖ HỔNG PHẠM VI — đã ghi thẳng, **KHÔNG** phải ĐẠT

Đây là những thứ **chưa ai đo**, không phải "đã đo và đạt":

1. **Gọi hãng thật / TLS thật** — chưa từng có một byte nào ra `*.jtexpress.vn`.
2. **PostgreSQL đường GHI** (`csdl.ghi`, `rowcount`) — G17 mới chỉ **dựng schema**. *(G18 đang đóng.)*
3. **Nhiều TIẾN TRÌNH** — bộ thử G17 chỉ chồng **luồng trong MỘT tiến trình**; khoá ghi của Python
   **không phủ qua tiến trình**. *(G18 đang đóng.)*
4. **Bí mật hãng ECHO LẠI** mà ta chưa từng gửi. *(G18 đang đóng.)*
5. **Bí mật trong ĐƯỜNG DẪN URL**. *(G18 đang đóng.)*
6. **Tắt tiến trình GIỮA giao dịch** — `V-13914(a)`. *(G18 đang đóng.)*
7. **Máy chủ HTTP thật dưới tải** — `V-13914(b)`; bàn đo cũ gọi **thẳng hàm**, không qua `ThreadingHTTPServer`. *(G18 đang đóng.)*
8. **V5/V6/V7 toàn cục** — G17 đã đo **lần đầu** (AG-01 và AG-06 đo **độc lập**, hai bộ đồ khác nhau).
   **Còn hở:** V5 của AG-01 phủ **41 cửa ⊂ 104 route** của AG-06 ⇒ **không phải bằng chứng cho 63 route còn lại**.
9. **Tầng 3 Chromium** — có chạy (`26 passed · 1 skipped` ở G16) nhưng **không đo DOM/CSS sâu**.
10. **Rate limit nhiều tiến trình** — `B-G11-10`: hai tiến trình ⇒ trần thực **gấp đôi** khai báo. Đã đo, **chưa sửa**.

## E. LỖI ĐÃ TÌM RA VÀ ĐÃ VÁ — ghi lại vì đó là bài học

| Mã | Loại | Nội dung | Trạng thái |
|---|---|---|---|
| **G16-05** | Bảo mật | Cổng che bí mật đặt ngưỡng theo **ĐỘ DÀI ≥ 8** ⇒ credential **ngắn** lộ nguyên văn; và **hai đường cho hai câu trả lời khác nhau** (thân form thì không, header thì rò). *"Kết luận 'không rò' chỉ từ một đường là SAI."* | **ĐÃ VÁ** — che theo **TÊN TRƯỜNG, bất kể độ dài** |
| **G16-09** | Bộ dò | **Luật vân tay §41 MÙ với `docs/`** — thêm một dòng vào chính bản hợp đồng mà vân tay **không nhúc nhích**. **AG-01 tự nhận là lỗi của chính nó** (nó viết lệnh đó, AG-00 chép nguyên văn vào luật) | **ĐÃ VÁ** — khoá bằng **Git là CHÍNH** (`HEAD` + `git diff HEAD` rỗng + `git status -uall` rỗng); vân tay chỉ còn là **dự phòng** |
| **H1** | **Sản phẩm** | **Trần replay bị vượt khi hai lượt chồng nhau** — tuần tự 202/409 ĐÚNG, chồng nhau 202/202 ⇒ `so_lan_replay=6 > trần 5`. Đúng khuôn đọc-rồi-ghi mà G17 đã vá cho chốt `đang xử lý` nhưng **bỏ sót chốt TRẦN** | **ĐÃ VÁ** — cả hai điều kiện nằm **trong** câu ghi, **và** lượt ghi audit nằm **trong cùng khoá** |
| **H5** | Thử nghiệm | Cổng "cây sạch" miễn trừ **cứng** 2 tệp của lượt 1 ⇒ làn giao thêm tệp ở lượt sau thì cổng **tự ĐỎ**. Ca thử **ghim SỰ THẬT MÔI TRƯỜNG** thay vì ghim **TÍNH CHẤT** | **ĐÃ VÁ** — khai quyền sở hữu bằng **MẪU**; kiểm chứng **hai chiều** (nền xanh + đối chứng âm làm bẩn tệp sản phẩm thì cổng đỏ) |

**Bài học chung của cả bốn:** *thứ dùng để kiểm chứng cũng phải được kiểm.* Cả `G16-05`, `G16-09`, `H5`
đều là **cổng do chính chúng tôi tạo ra**, và cả ba **hổng cho tới khi có người thử phá**.

## F. PHÁT HIỆN VẬN HÀNH — ảnh hưởng cách chạy, không phải lỗi mã

- **Worker DeepSeek KHÔNG commit được.** Cả 6 worktree G17 còn nguyên công chưa commit khi
  settlement — worker cũng bị chặn ghi `.git` như AG-00 (đúng lỗ hổng lớp `G16-08`).
  ⇒ **AG-00 phải commit hộ từng làn khi settlement.** Đây là việc **bắt buộc với mọi wave**.
- **`worker-stop` KHÔNG dừng được worker `dsh`.** Đo được: `state: "stop_unknown"`,
  `processAction: "none"`, *"The worker terminal is user_owned; no terminal was closed."*
  ⇒ Phải theo **đúng hợp đồng vòng đời**; không dùng đường tắt.
- **Alias `dsh` KHÔNG có trong tài liệu Orca.** `worker-start --agent dsh` ⇒ `ok:true`,
  `provider.id="dsh"`; `--agent deepseek` ⇒ `agent_unconfigured`. Tài liệu Orca liệt kê
  `claude, codex, cursor, antigravity, muse, zcode, opencode, opencode2` — **thiếu `dsh`**.
  Đã ghi vào tài liệu **dự án**; **KHÔNG** sửa cấu hình Orca toàn máy.
- **Terminal giám sát của Codex `term_d22bda1c-…` không nhận được thư trực tiếp**
  (`terminal_not_found` — *"no live pane or durable Run/Dispatch mailbox"*). AG-00 đang thay bằng
  cách đăng vào **mailbox của Run**.
- **`GIT_CONFIG_COUNT=2` với khoá RỖNG** làm **mọi** lệnh git hỏng (mã thoát 128). Phải
  `unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1` trước khi chạy git.

## G. VIỆC ANH NÊN LÀM TRƯỚC (thứ tự đề nghị)

1. **A1 + A2** — mở `V-G09-01` và `V-13906-05`, gửi **4 tên trường**. Không có thì **G21 không chạy được**.
2. **B1** — trả lời **mã `110`**. Đây là chỗ **rẻ nhất mà rủi ro cao nhất**: một mã, một câu trả lời.
3. **B3–B6** — bốn đường dẫn còn thiếu.
4. **A5** — biết trước là sẽ có hộp thoại cần anh bấm; AG-00 **không tự bấm**.
5. **C1/C2** — quyết gộp nhánh (hoặc quyết **không** gộp, cũng là một quyết định).

---

## H. PHÂN QUYỀN / PHÊ DUYỆT — ĐIỀU TRA VÀ QUYẾT ĐỊNH (15/10/2026)

### H.1 Cơ chế thật của từng hệ — đo, không suy đoán

**DeepSeek Harness (`dsh`)** — đọc trực tiếp `@deepseek-ai/dsh-base` `cordis.patch.yml`:
```yaml
- id: approval   → @deepseek-ai/dsh-user-approval
  config: { policy: "(DSH_PERMISSION_MODE ?? 'workspace-write') === 'danger-full-access' ? 'never' : 'ask'" }
- id: permission → @deepseek-ai/dsh-permission-presets
  config:
    presets:
      read-only:          { sandbox: read-only,          approval: ask }
      workspace-write:    { sandbox: workspace-write,    approval: ask }
      danger-full-access: { sandbox: danger-full-access, approval: never }
```

**HAI ĐIỀU LÀM ĐẢO NGƯỢC GIẢ ĐỊNH THÔNG THƯỜNG:**

1. **`never` KHÔNG phải "tự cho phép" — nó là "tự TỪ CHỐI".** README `dsh-user-approval` nói nguyên
   văn: *"`never` **rejects** every request deterministically … the strict headless stance for CI and
   unattended runs."* Preset `danger-full-access` đi kèm `never` **không phải** để cho qua — mà vì
   sandbox đã cho qua hết nên **không còn yêu cầu nào để hỏi**.
2. **Ranh giới ghi KHÔNG nới được bằng cấu hình.** README `dsh-sandbox-policy`: `workspaceRoot` chỉ
   là **dự phòng**; *"Normal agent calls use the session's **immutable cwd**"* — *"A switched session
   **keeps its immutable workspace cwd** as the writable boundary."* Ranh giới **ghim lúc tạo phiên**.

**`dsh` KHÔNG có allowlist theo từng lệnh.** README `dsh-permission-presets`: *"Each preset name
bundles **one sandbox mode with one approval policy**"* — đúng **hai** trường. Tên `custom`/`auto` là
**dành riêng**, không được xuất hiện trong bảng. Và *"Callers cannot publish another preset through a
generic contribution API."* ⇒ **Mục 5 của chỉ thị ("nếu agent hỗ trợ allowlist") KHÔNG áp dụng được
cho dsh** — không có allowlist nào để thiết lập.

**Claude Code** — `~/.claude/settings.json` **có `autoMode`**, và nó đang làm đúng mục 4:
```json
"soft_deny": ["$defaults", "Bash(cp:.env *)", "Bash(git push:*develop)", "Bash(git push:*main)"]
```
Không có khoá `permissions`. **Đây là mẫu để copy** nếu sau này muốn ép mục 4 bằng kỹ thuật — chặn
theo **mẫu lệnh**, không phải theo "hỏi hay không hỏi".

**Orca Desktop** — **không có chính sách phê duyệt riêng.** `orca --help` không có lệnh nào về
permission/approval (chỉ `computer permissions`, cho điều khiển GUI — không liên quan).
`~/.orca/agent-hooks/dsh-hook.sh` là hook **spool sự kiện** `PreToolUse`/`PostToolUse` — nó **QUAN
SÁT, KHÔNG quyết định**. Cài đặt Orca nằm trong storage Electron (`Local Storage`/`IndexedDB`), không
phải JSON đọc được an toàn. ⇒ Hộp thoại duyệt Bash trong Orca Desktop là **giao diện hiển thị yêu cầu
`ask` do tầng dsh phát ra**.

### H.2 Kiểm chứng thực tế (mục 7 của chỉ thị) — bốn thao tác được phép

| Thao tác | Kết quả |
|---|---|
| Đọc file trong dự án | **Không xin duyệt** |
| Tạo + sửa file thử nghiệm trong dự án | **Không xin duyệt** |
| Chạy test (`thu_tich_hop.py`) | **Không xin duyệt** — `exit 0 · Ran 12 · OK` |
| Git **chỉ đọc** (`status`, `log -1`) | **Không xin duyệt** |
| Git **ghi** (`git add` — ngoài phạm vi) | **BỊ CHẶN** — đúng như thiết kế |

⇒ **Năm mục đầu của chỉ thị VỐN ĐÃ miễn phí.** Friction không đến từ chúng, mà từ **thao tác ra
ngoài `cwd` của phiên** (ghi `.git` dùng chung, ghi sang worktree khác, chạy Playwright ở worktree
khác). **Nới approval không sửa được cái đó.**

### H.3 QUYẾT ĐỊNH CỦA OWNER: **KHÔNG ĐỔI GÌ**

Owner đã chọn **giữ nguyên toàn bộ cấu hình phân quyền**. Lý do hợp lý và đã kiểm chứng: không có
thay đổi nào cần thiết cho các thao tác được phép (H.2), và thay đổi duy nhất còn lại
(`~/.dsh/profiles/dsh-tui/cordis.patch.yml` = preset `workspace-write` + `approval: never`) là
**cấu hình TOÀN CỤC**, đồng thời **bỏ mất lưới kiểm của người** cho `git push` và lệnh phá hoại
**trong** dự án. Theo **mục 6** của chỉ thị, việc đó thuộc phạm vi phải Owner duyệt — và Owner đã
**không** duyệt.

**Đã thực hiện đúng chỉ thị:** *không* dùng wildcard Bash toàn quyền (mục 5) · *không* tự sửa cấu
hình bảo mật toàn cục (mục 6) · *có* chạy kiểm chứng bốn thao tác (mục 7) · **Git history, CSDL và
mã nguồn giữ nguyên** (tệp thử nghiệm tạo ra đã được xoá; `git add` bị chặn nên không commit nào phát
sinh từ lượt kiểm chứng).

### H.4 ĐÍNH CHÍNH một kết luận cũ của AG-00 (mục F ở trên)

Mục F ghi *"Worker DeepSeek KHÔNG commit được"*. **Điều đó KHÔNG đúng một cách phổ quát.** Đo lại
trên 6 làn G18 (`git log 7b741c8..HEAD`):

| Làn | Commit tự tạo | Ai commit |
|---|---|---|
| AG-02 | **3** | tự commit |
| AG-03 | **3** | tự commit |
| AG-04 | **2** | tự commit |
| AG-01 | 1 | **AG-00 commit hộ** |
| AG-05 | 1 | **AG-00 commit hộ** |
| AG-06 | 1 | **AG-00 commit hộ** |

⇒ Đúng hơn phải nói: **một số worker commit được, một số không** — nên **AG-00 phải KIỂM TỪNG LÀN**
khi settlement, chứ **không được mặc định** là làn nào cũng cần commit hộ. Mặc định sai theo chiều nào
cũng có giá: mặc định "không commit được" thì AG-00 commit hộ một cây đã sạch (vô hại); mặc định
"commit được" thì công của làn **nằm trần ở cây làm việc** và `git clean -fd` xoá sạch im lặng.
