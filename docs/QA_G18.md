# NGHIỆM THU G18 — AG-01 (QA/VERIFIER)

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_26caf9b4f14c` · **Dispatch:** `ctx_34f637d0a32f`
**Nền đo:** `integration/g17 @ 7b741c88b3b280d65f80b5e11301f17ebd767b26` (`7b741c8`), worktree riêng
`g18-ag01-qa`. **KHÔNG** dùng `main` (`de740dc`, không chứa G13–G18).
**Hai tệp AG-01 G18 được phép tạo (và là hai tệp DUY NHẤT đã tạo):**
`app/thu/thu_qa_g18.py` (bộ thử, **43 ca**) · `docs/QA_G18.md` (tài liệu này).
**Lệnh chạy bộ thử của tôi:**
`VIP_G18_HEAD=7b741c88b3b280d65f80b5e11301f17ebd767b26 python3 app/thu/thu_qa_g18.py`

**Luật bằng chứng tự áp:** mọi khẳng định dưới đây đi kèm **lệnh thật + mã thoát thật + số ca thật
+ số bỏ qua**. Mã thoát lấy **ngay sau lệnh**, không qua ống. Ca phủ định nào cũng có **đối chứng
dương** trong cùng nhóm (`DOI_CHUNG`, `Z_TongKet` tự phán HỎNG nếu thiếu). Bộ dò được **tự kiểm**
bằng một ca cố ý hỏng chạy trong **tiến trình con** (`J1`) **và** bằng **sáu phép đột biến trên cây
sao chép** (`J3`–`J7` cho bốn cổng HTTP/quyền + `D2` cho bàn đo đồng thời). Cái gì không đo được thì nằm ở §6 **CHƯA ĐO** — đó là **lỗ hổng phạm vi,
KHÔNG phải ĐẠT**.

**Nhiệm vụ của lượt này là DỌN LỖ HỔNG ĐÃ GHI, không làm lại mục đã đạt.** Ba cổng G16-A và cả
wave G17 (1460 ca / 38 bộ / exit 0) đã ĐẠT; tôi **không** đo lại V5/V6/V7 toàn cục, **không** dựng
lại phép đo G16-A, **không** sửa một dòng mã sản phẩm nào.

**Tuân thủ tuyệt đối (tự kiểm bằng máy, không bằng lời):** không gọi API hãng kể cả sandbox
(`V-G09-01` + `V-13906-05` CHƯA CẤP; `A3`: 0/2 lớp adapter `CHO_PHEP_LIVE=True`; `A6`: 0 lượt
`connect` ra ngoài loopback) · không push/deploy/tunnel (máy chủ đo bind `127.0.0.1` **cổng 0**) ·
không mở `CHO_PHEP_LIVE` · không credentials thật, không `.env` (CSDL và khoá nằm trong thư mục
tạm) · không đoán mã `110` (`D-4`) · giữ chốt D-9 (không đo `area` ngoài mock) · vẫn SQLite
(`A5`; `D-8`) · cụm PostgreSQL `:5432` (đang giữ `vip_customs`, `vip_customs_g16`,
`vip_customs_test`) **CHẶN CỨNG**, chỉ dùng cụm RIÊNG `55432` (`H1`–`H3`) · không đổi mô hình ·
không tự bấm duyệt sandbox.

---

## 0. BẢNG PHÁN QUYẾT

**Bảy** trong **11** mục **"CHƯA ĐO"** của `docs/QA_G17.md` §5 nay có phép đo độc lập; **bốn mục
còn lại vẫn CHƯA ĐO** và nằm ở §6. Cột **CỔNG FAIL** là điều kiện làm mục đó ĐỎ — đọc cột đó
trước cột phán quyết.

| # | Mục §5 `QA_G17` | CỔNG FAIL (điều kiện ĐỎ) | Cách đo (bộ thử của tôi) | Phán quyết |
|---|---|---|---|---|
| 1 | **§5.3** Harness SANDBOX AG-04 (`trien_khai/g16/**`) | harness thoát ≠ 0 · **hoặc** chặng chạm hãng KHÔNG ghi `BLOCKED` · **hoặc** thiếu `V-G09-01`/`V-13906-05` · **hoặc** nền ngoài thư mục tạm mà vẫn chạy | `C1`–`C3` | **ĐẠT** (mã thoát 0 · tự kiểm 10 cấu hình · từ chối thật khi nền sai: thoát **4**) |
| 2 | **§5.4** Tầng 3 — DOM/CSS Chromium | `failed > 0` · **hoặc** `passed == 0` (xanh giả) · **hoặc** mã thoát ≠ 0 | `B1`/`B2` | **ĐẠT có điều kiện** — **CHẬP CHỜN**, xem `N-G18-01` |
| 3 | **§5.5** Đa tiến trình thật *(phạm vi: TIẾN TRÌNH; đa luồng dưới tải lớn vẫn CHƯA ĐO)* | bàn đo thoát ≠ 0 · **hoặc** thiếu một trong ba ca (SỔ CÁI / ĐỌC–SỬA–GHI / HẠN MỨC) · **hoặc** đột biến "mất ghi" mà bàn đo VẪN xanh | `D1`/`D2` | **ĐẠT** (8 tiến trình × 400 phép · 10,2 giây · đột biến "mất ghi" làm nó ĐỎ) |
| 4 | **§5.6** Ma trận `(cửa × POST/PUT/DELETE)` | bất kỳ cửa ghi nào trả **≠ 401** khi không phiên · **hoặc** thiếu `X-Requested-With` mà không 403 · **hoặc** B ghi được hàng của A (mã 2xx **hoặc** dữ liệu A đổi) | `E1`–`E9` | **ĐẠT** (22 cửa ghi tĩnh × 3 = **66 lượt** đều 401 · 25 cửa ghi có tham số · B lọt 0) |
| 5 | **§5.7** Mặt phẳng `/api/v2/platform/*` | phiên tenant nhận **≠ 403** · **hoặc** không có đối chứng dương cho platform admin | `F1`–`F3` | **ĐẠT** (8 cửa × 2 = **16 lượt** đều 403 · PLATFORM_ADMIN 200 · tạo tenant 403, PLATFORM_OWNER 201) |
| 6 | **§5.8** Hai tầng frontend (56 + 36 ca) | thoát ≠ 0 · **hoặc** `fail > 0` · **hoặc** **TEO CA** dưới 56 / 36 | `G1`/`G2` | **ĐẠT** (56 đạt / 0 hỏng · 36 ca) |
| 7 | **§5.9** V11 — PostgreSQL (cụm RIÊNG) | chạm cổng `5432` mà không bị từ chối · **hoặc** cụm thử còn sót ở `55432` · **hoặc** vân tay `:5432` trước ≠ sau · **hoặc** bộ thử chạy 0 ca | `H1`–`H3` + `A7`/`Z3` | **ĐẠT** (**42 ca · 0 bỏ qua** trên cụm riêng · `:5432` trước = sau · trỏ vào `5432` ⇒ thoát **1**) |
| 8 | Nền đóng băng | cây đổi ngoài 2 tệp AG-01 · **hoặc** HEAD ≠ ghim | `A1`/`A2`/`Z2` | **ĐẠT** (vân tay `d7a5bd43…` trước = sau; xem §1.0) |
| 9 | Hồi quy toàn phần trên nền | bộ chạy chung thoát ≠ 0 **khi môi trường git ĐÚNG** | §1.1 | **ĐẠT** (lượt B: thoát 0 · 1460 ca · 38 bộ · 0 hỏng) · **HỎNG ở lượt A** vì biến môi trường (`N-G18-00`) · **HỎNG ở lượt C** vì cổng "cây sạch" của wave trước, KHÔNG phải lỗi sản phẩm (`N-G18-03`) |
| 10 | Gọi hãng thật · TLS thật · bốn thao tác đầu-cuối · deploy/push | — | không đo (bị cấm) | **CHƯA ĐO** — §6 |

**Phán quyết một dòng:** **bảy mục "CHƯA ĐO" của G17 nay đã được đo độc lập — sáu ĐẠT, một (tầng 3)
ĐẠT nhưng CHẬP CHỜN**; điều chập chờn đó được ghi thành `N-G18-01` chứ **không** được gộp vào ĐẠT.
**Bốn mục còn nguyên là CHƯA ĐO** (§6): gọi hãng thật/TLS thật · bốn thao tác đầu-cuối · ngoài
phạm vi theo thiết kế · chưa có người đọc lại. **Bốn phát hiện mới**: `N-G18-00` (**HIGH vận hành** — biến `GIT_CONFIG_*` hỏng vẫn còn, tái diễn
`N-G17-00`), `N-G18-01` (**MEDIUM** — một ca tầng 3 không ổn định), `N-G18-03` (**MEDIUM** — cổng
"cây sạch" của wave trước đỏ vì tệp chưa commit của làn khác) và `N-G18-02` (**LOW** — đường nhị
phân Chromium ghim trong repo). Ngoài ra tôi ghi lại
**năm lỗi của chính bàn đo** ở §4 — trong đó một lỗi suýt biến thành *"5 ca hỏng của sản phẩm"*.

**SỐ BỎ QUA (SKIP) — nói thẳng, không gộp vào ĐẠT:**

| Lượt chạy | Số ca | Bỏ qua | Nguồn của ca bỏ qua |
|---|---|---|---|
| bộ thử AG-01 G18, **làn ĐẦY ĐỦ** (`VIP_G18_DAY_DU=1`) | 43 | **0** | — (đây là lượt tôi dùng để ký phán quyết ở §2) |
| bộ thử AG-01 G18, **làn MẶC ĐỊNH** | 43 | **1** | `H3` — làn PostgreSQL trọn: `skipped 'CHƯA ĐO trong làn mặc định: bật VIP_G18_DAY_DU=1 để chạy trọn'` ⇒ `OK (skipped=1)` |
| tầng 3 Chromium (bên trong bộ thử) | 37 | **1** | một ca của chính bộ spec (`- 10 …`), không phải ca của tôi |
| `sh app/thu/chay_tat_ca.sh` (lượt B và C) | 1460 / 1503 | **0** | không bộ nào bỏ qua |

---

## 1. BASELINE ĐỘC LẬP TRÊN NỀN ĐÓNG BĂNG

### 1.0 Vân tay cây + HEAD + số tệp (đo TRƯỚC lượt nào)

```sh
export GIT_CONFIG_COUNT=0        # bắt buộc trên máy này: xem N-G18-00
git rev-parse HEAD
git ls-files | wc -l
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

| Mốc | Giá trị |
|---|---|
| `git rev-parse HEAD` | `7b741c88b3b280d65f80b5e11301f17ebd767b26` |
| Số tệp được theo dõi | **237** |
| **Vân tay TRƯỚC mọi lượt đo** (11:44:10Z, cây CHƯA có tệp AG-01) | `d7a5bd4339de0db551ab91979f6df5b57361de6bc20ddab019bb0d3f3d8ddeb1` |
| **Vân tay SAU tất cả các lượt** (miễn trừ đúng 2 tệp AG-01 G18) | `d7a5bd43…` — **KHÔNG đổi** |
| `git status --porcelain=v1 -uall` sau tất cả | **1 dòng**: `?? app/thu/thu_qa_g18.py` (+ `?? docs/QA_G18.md` sau khi tài liệu này được tạo) |

**Vân tay TRƯỚC của tôi khớp từng ký tự với con số AG-00 công bố (`d7a5bd4339de0db5`) — và nó
KHÔNG đổi suốt lượt đo.** Nghĩa là: ngoài hai tệp mà đề bài cho phép tôi tạo, **không một byte nào**
của cây đổi — kể cả khi tôi chạy ba lượt hồi quy toàn phần, một lượt tầng 3 Chromium, một lượt
harness AG-04, một lượt PostgreSQL dựng cụm riêng và một bàn đo 8 tiến trình.

> Bộ thử dùng cách băm tương đương nhưng nối chuỗi khác một ký tự xuống dòng, nên nó in
> `cdc5dace7cfd38425dabf1dd63edb185bdd5443baadb63cef5b316faf9c27b90` (`A1`, `Z2`). Hai giá trị
> **không so trực tiếp được với nhau**; điều có nghĩa là **trước = sau trong cùng một cách băm**
> (đã đo cả hai cách, cả hai đều không đổi).

### 1.1 Ba lượt chạy thật của bộ chạy chung

```sh
# LƯỢT A — ĐÚNG NHƯ MÔI TRƯỜNG ĐƯA (giữ nguyên GIT_CONFIG_*)
rm -rf /tmp/veh_g18_ag01_qa_A && mkdir -p /tmp/veh_g18_ag01_qa_A
VIP_HUB_DATA=/tmp/veh_g18_ag01_qa_A sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
# LƯỢT B — GỠ biến git hỏng
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g18_ag01_qa_B sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
```

| | **Lượt A** (nguyên văn) | **Lượt B** (gỡ `GIT_CONFIG_*`) | **Lượt C** (+ tệp AG-01 G18) |
|---|---|---|---|
| Bắt đầu → kết thúc (UTC) | 11:44:21 → 11:47:21 | 11:47:33 → 11:50:30 | 12:05:33 → 12:09:55 |
| **Mã thoát** | **1** | **0** | **1** — xem `N-G18-03` |
| Số bộ thử python | 38 bộ (**2 ✗**) | 38 bộ (38 ✓) | **39 bộ** (**1 ✗**) |
| Số ca python | **1460** | **1460** | **1503** (= 1460 + **43** ca AG-01 G18) |
| Số bộ hỏng | **2** (`thu_bao_mat.py` · `thu_tich_hop.py`) | **0** | **1** (`thu_qa_g17.py` — `test_a1_cay_sach_va_head`; **KHÔNG phải** lỗi sản phẩm, xem `N-G18-03`) |
| Số ca BỎ QUA | 0 | 0 | **0** (không có dòng `BỎ QUA` nào; 39/39 bộ chạy thật) |
| Frontend (tầng 1 + 2) | 56 + 36 ca | 56 + 36 ca | 56 + 36 ca |
| E2E qua HTTP thật | 41/41 | 41/41 | 41/41 |
| Cây / HEAD | `d7a5bd43…` / `7b741c8` | y hệt | y hệt |

**Hai con số 1460 ca và 38 bộ của tôi TRÙNG với con số AG-00 vừa đo (1460 ca · 38 bộ · 0 hỏng ·
exit 0) — nhưng tôi đo ra chúng, không chép.** Khác biệt duy nhất: **lượt A của tôi ĐỎ**, còn
AG-00 báo xanh. Nguyên nhân được tách ở §1.2 — và nó **không phải lỗi sản phẩm**.

### 1.2 Thí nghiệm A/B tách **lỗi môi trường** khỏi **lỗi sản phẩm**

CÙNG cây, CÙNG hai bộ thử, CÙNG số ca; **chỉ** biến môi trường khác:

```sh
VIP_HUB_DATA=/tmp/veh_g18_cmp  python3 app/thu/thu_bao_mat.py    # → FAILED (failures=1) · exit 1
VIP_HUB_DATA=/tmp/veh_g18_cmp  python3 app/thu/thu_tich_hop.py   # → FAILED (failures=2) · exit 1
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g18_cmp2 python3 app/thu/thu_bao_mat.py   # → OK · exit 0
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g18_cmp2 python3 app/thu/thu_tich_hop.py  # → OK · exit 0
```

Ba ca hỏng ở lượt A **đều là ca kiểm có gọi `git`**, và lệnh `git` trên máy này thoát **128**:

```sh
git status --porcelain=v1
# error: missing config key GIT_CONFIG_KEY_0
# fatal: unable to parse command-line config        → EXIT=128
```

Số đo môi trường: `GIT_CONFIG_COUNT=2` nhưng `GIT_CONFIG_KEY_0` **rỗng**, `GIT_CONFIG_VALUE_0`
và `GIT_CONFIG_VALUE_1` đều dài **5** ký tự. Đây **đúng là `N-G17-00`** mà AG-01 G17 đã ghi —
**chưa được vá**, và nó vẫn làm cổng hồi quy mặc định ĐỎ. Xem `N-G18-00`.

⇒ **Kết luận của phép tách:** lượt A đỏ vì **môi trường**, không vì sản phẩm. Một báo cáo chỉ ghi
"1460 ca, 2 bộ hỏng" mà không nói điều này là báo cáo SAI theo hướng nói xấu sản phẩm; một báo cáo
ghi "exit 0" mà không nói rằng phải gỡ biến môi trường trước là báo cáo SAI theo hướng nói tốt.

---

## 2. SÁU LỖ HỔNG "CHƯA ĐO" ĐÃ ĐÓNG — lệnh thật, mã thoát thật, số ca thật

**LƯỢT CHỐT — chạy trên ĐÚNG bytes đã băm ở §8** (sau khi bàn đo đã được vá ở §4):

```sh
env GIT_CONFIG_COUNT=0 VIP_G18_HEAD=7b741c88b3b280d65f80b5e11301f17ebd767b26 VIP_G18_DAY_DU=1 \
    python3 app/thu/thu_qa_g18.py
# → Ran 43 tests in 92.850s · OK · EXIT=0        (43 ca · 0 bỏ qua · 0 hỏng)
#   log thô của từng làn: /var/folders/…/T/veh_g18_ag01_qa_log/
```

Một lượt **TRƯỚC** đó, **cùng bộ thử, cùng cây, cùng HEAD**, ra
`Ran 43 tests in 140.408s · FAILED (failures=1)`: ca hỏng là ca **CHẬP CHỜN** của tầng 3 —
`N-G18-01`. **Cả hai lượt đều được ghi lại**; lượt đỏ không bị bỏ đi và cũng không bị gọi là
"lỗi sản phẩm".

### 2.1 §5.3 — Harness SANDBOX AG-04 (`trien_khai/g16/**`) — **ĐẠT**

`docs/G16_ACCEPTANCE.md` §8.5 để mục này là *"AG-01 chưa nghiệm thu"*; `QA_G17.md` §5.3 giữ nguyên.

```sh
python3 trien_khai/g16/chot_an_toan.py --tu-kiem     # → EXIT=0 · 10 cấu hình tổng hợp
sh trien_khai/g16/chay_harness.sh                    # → EXIT=0 (nền tạm riêng)
```

| Phép đo | Số thật |
|---|---|
| `C1` tự kiểm bộ dò chốt an toàn | **mã thoát 0** · **10 cấu hình** (1 ca đủ chốt phải ĐI QUA + 9 ca hỏng phải bị BẮT) |
| `C2` harness đầy đủ | **mã thoát 0** · xác nhận *"sáu chốt an toàn: ĐỦ"* |
| `C2` hai chặng chạm hãng | ghi **BLOCKED** kèm **đúng** `V-G09-01` + `V-13906-05` (không tính là ĐẠT) |
| `C3` **đối chứng âm** — nền NGOÀI thư mục tạm | **mã thoát 4**, in *"TỪ CHỐI CHẠY"*, **không tạo gì** ở `~/.veh-g18-phai-tu-choi/g16_harness` |

⇒ Harness có **phán quyết thứ ba** (`BLOCKED`) và **từ chối chạy thật** khi mất chốt an toàn —
không phải chỉ khai trong tài liệu.

### 2.2 §5.4 — Tầng 3: DOM/CSS trong Chromium THẬT — **ĐẠT, nhưng CHẬP CHỜN**

G17 không đo được vì thiếu nhị phân. Lượt này nhị phân **có**, ở đúng nguồn mà `BAN_GIAO.md` §1
chỉ định: `~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers`
(`chromium-1194` + `chromium_headless_shell-1194`, khớp `playwright-core 1.56.1` của worktree).
**KHÔNG** dùng cache hệ thống `~/Library/Caches/ms-playwright` (bị `BAN_GIAO.md` §1 cấm).

Bộ thử chạy **đúng khuôn** `thu_giao_dien/chay.sh` (migrate → khoi_tao → chuan_bi mk → máy chủ cổng
động → chuan_bi don → `playwright test`), khác **đúng một biến**: đường nhị phân.

| Lượt | Lệnh | Mã thoát | đạt | hỏng | bỏ qua | Ghi chú |
|---|---|---|---|---|---|---|
| 1 (trong bộ thử, lần đầu) | `python3 app/thu/thu_qa_g18.py` | 1 | 8 | **5** | 24 | **LỖI CỦA BÀN ĐO** — ống stdout máy chủ đầy ⇒ máy chủ chặn ở lệnh ghi ⇒ 4 ca `page.goto` timeout. Xem §4.1 |
| 2 (chạy riêng) | `python3 app/thu/thu_qa_g18.py B_Tang3` | **0** | **36** | **0** | **1** | 58,5 giây · xanh trọn |
| 3 (trong bộ thử, sau khi vá) | `python3 app/thu/thu_qa_g18.py` | 1 | 33 | **1** | 2 | ca `05_ket_noi_jt.spec.js:359` — xem `N-G18-01` |
| 4 (chạy riêng) | `python3 app/thu/thu_qa_g18.py B_Tang3` | **0** | **36** | **0** | **1** | 54,7 giây · xanh trọn |
| 5 (chạy riêng) | `python3 app/thu/thu_qa_g18.py B_Tang3` | **0** | **36** | **0** | **1** | 52,4 giây · xanh trọn |
| 6 (**lượt CHỐT**, trong bộ thử) | `VIP_G18_DAY_DU=1 python3 app/thu/thu_qa_g18.py` | **0** | **36** | **0** | **1** | 92,9 giây cho **cả** bộ thử · xanh trọn |
| — | `sh thu_giao_dien/chay.sh` **nguyên bản** | **1** | 0 | 4 | 23 | **ĐỎ do MÔI TRƯỜNG**: `Executable doesn't exist at …/.local-browsers/chromium_headless_shell-1194/…` — worktree này **không có** `node_modules/playwright-core/.local-browsers` |

**Đối chứng âm `B2`** (chứng minh cổng này CÓ RĂNG): trỏ `VIP_G18_PW_BROWSERS` vào một thư mục
RỖNG ⇒ bộ dò nhị phân trả `None` (nó **không** lặng lẽ quay về đường mặc định) và chính
`sh thu_giao_dien/chay.sh` nguyên bản **thoát 1** với lý do nêu đúng tên tệp nhị phân còn thiếu.

⇒ **Tầng 3 nay ĐÃ ĐO ĐƯỢC** (36 ca chạy thật trong Chromium, 1 ca bỏ qua), nhưng **không ổn định**:
1/5 lượt đỏ, ở cùng một ca. Đó là **CHẬP CHỜN CỦA SẢN PHẨM**, không phải lỗi bàn đo — `N-G18-01`.

### 2.3 §5.5 — Đa tiến trình THẬT — **ĐẠT**

G17 không chạy `app/thu/dong_thoi/chay.py` lượt nào.

```sh
python3 app/thu/dong_thoi/chay.py            # VIP_SO_TT=8 · VIP_SO_PHEP=400
```

| Phép đo | Số thật |
|---|---|
| `D1` mã thoát | **0** · **10,2 giây** · 8 tiến trình hệ điều hành × 400 phép × 3 ca |
| `D1` ba ca | **SỔ CÁI TÀI CHÍNH** · **ĐỌC–SỬA–GHI** · **HẠN MỨC** — cả ba đều chạy, không ca nào bị bỏ |
| `D2` **đối chứng âm** | cây sao chép bị tiêm *"mất ghi"* (bỏ lệnh `ghi_but_toan` nhưng vẫn báo thành công) ⇒ bàn đo thoát **1** — nó **bắt được** mất ghi |
| `thu_http_jt.py` (chạy riêng) | **mã thoát 0** · **57 ca** · `OK` · **91,8 giây** (bộ này có **tự kiểm bộ dò** riêng: `CaTuKiem` + `CaTuKiemG17`) |

⇒ Trần rate-limit theo tenant sống trong bộ nhớ **một** tiến trình; lượt này đo được rằng **phần
CSDL** (sổ cái, đọc–sửa–ghi, hạn mức) đúng dưới **8 tiến trình thật**, và bàn đo **có răng**.

### 2.4 §5.6 — Ma trận ghi `(cửa × POST/PUT/DELETE)` — **ĐẠT**

G17 quét **mọi cửa GET** và **4** phép ghi có chủ đích; phần còn lại của ma trận ghi chưa quét.

| Phép đo | Số thật |
|---|---|
| `E1` rút cửa từ chính `app/server.py` (không chép tay) | **22 cửa ghi TĨNH** · **25 cửa ghi CÓ THAM SỐ** |
| `E2` **không phiên**, mọi cửa ghi tĩnh × 3 phương thức | **66 lượt** · mã trả về **`{401: 66}`** · khác 401: **0** |
| `E3` **đối chứng dương** | `POST /api/v2/khach-hang` bằng chủ hợp lệ → **201** (cửa thật sự chạy) |
| `E4` thiếu `X-Requested-With` | **403** · có header → **201** |
| `E5` B đổi membership của A | B → **404**, dữ liệu A **còn nguyên** · chủ A → **200** |
| `E6` B khoá tài khoản hãng của A | B → **404**, `kich_hoat` + bản mã **không đổi** · chủ A → **200** |
| `E7` B huỷ đơn của A | B → **404**, trạng thái đơn **không đổi** · chủ A → **200** (trên đơn đối chứng riêng) |
| `E8` B khai `tenant_id=A` khi tạo đơn | đơn vẫn thuộc **B**; số đơn của A **2 → 2** |
| `E9` lưới rộng: 25 cửa ghi có tham số × 3 phương thức | B lọt **0** · rò canary **0** · (đối chứng dương trong lưới: chủ A không bị 401/403) |

⇒ Ba lớp được đo **độc lập nhau**: (a) **không phiên ⇒ 401** trên *mọi* cửa ghi; (b) **có phiên
nhưng thiếu CSRF ⇒ 403**; (c) **có phiên của tenant khác ⇒ không 2xx VÀ dữ liệu của A không đổi**
(đo bằng **CSDL**, không chỉ bằng mã HTTP — mã 404 vẫn có thể đi kèm một lượt ghi đã xảy ra).

### 2.5 §5.7 — Mặt phẳng `/api/v2/platform/*` — **ĐẠT**

G17 cố ý để mặt phẳng nền tảng **ngoài** phép quét chéo tenant.

| Phép đo | Số thật |
|---|---|
| `F1` phiên tenant (không `platform_role`) trên **8 cửa** × 2 phương thức | **16 lượt** · mã **`{403: 16}`** · không-403: **0** |
| `F2` **đối chứng dương** | `PLATFORM_ADMIN` `GET /api/v2/platform/tenants` → **200** (2 tenant) |
| `F3` ma trận quyền nền tảng | `co_quyen("PLATFORM_ADMIN","platform.tenant.tao")` = **False** · `POST /platform/tenants` bằng PLATFORM_ADMIN → **403** · bằng PLATFORM_OWNER → **201** và CSDL **+1 tenant** |

### 2.6 §5.8 — Hai tầng frontend (56 + 36 ca) — **ĐẠT (đo độc lập)**

```sh
node --test thu_frontend/thu_logic.mjs      # → EXIT=0 · ℹ pass 56 · ℹ fail 0 (0,1 giây)
python3 thu_frontend/thu_http.py            # → EXIT=0 · Ran 36 · OK (1,8 giây)
```

Cổng của tôi **không chỉ đòi xanh**: nó đòi **`pass ≥ 56`** và **`Ran ≥ 36`**, nên một bộ thử bị
**teo ca** (hoặc bị vô hiệu hoá âm thầm) sẽ làm cổng ĐỎ chứ không xanh.

### 2.7 §5.9 — V11 PostgreSQL trên CỤM RIÊNG — **ĐẠT**

G17 chỉ xác nhận *"CSDL nghiệp vụ vẫn SQLite"*, **không** chạy lại cụm `55432`, **không** đối chiếu
DDL.

```sh
lsof -iTCP:55432 -sTCP:LISTEN                                  # → rỗng
python3 app/thu/thu_postgres.py                                # cụm RIÊNG, tự dựng tự xoá
VHPG_CONG=5432 python3 app/thu/thu_postgres.py                 # → phải TỪ CHỐI
python3 trien_khai/postgres/van_tay_cum.py --chup --cong 5432  # TRƯỚC = SAU
```

| Phép đo | Số thật |
|---|---|
| `H3` chạy trọn trên cụm riêng | **mã thoát 0** · **42 ca** · **0 bỏ qua** · **5,8 giây** (đo lại **riêng**: `Ran 42 tests in 5.824s` · `OK` · thoát **0**) |
| `H1` cụm thử còn sót | `lsof -iTCP:55432 -sTCP:LISTEN` → **rỗng** |
| `H2` **đối chứng âm** — trỏ CẢ bộ thử vào `:5432` | **mã thoát 1**, in *"TỪ CHỐI chạy trên cổng 5432…"* |
| `A7`/`Z3` vân tay cụm hệ thống `:5432` | pid `58873`, **6 CSDL** (`postgres`, `template0`, `template1`, **`vip_customs`**, **`vip_customs_g16`**, **`vip_customs_test`**) — **TRƯỚC = SAU**, cả trước và sau **mọi** lượt đo của tôi |

⇒ `D-8` **không bị vi phạm**: CSDL nghiệp vụ vẫn SQLite (`A5`: `app/*.py` không import driver nào
khác); PostgreSQL chỉ được đo trên **cụm riêng `55432`** (`listen_addresses=''`, chỉ socket Unix).
Cụm `:5432` giữ dữ liệu dự án khác — **không bị đụng tới**, và điều đó được chứng minh bằng vân tay
chứ không bằng lời hứa.

---

## 3. HAI CHỐT CHẶN BẮT BUỘC

### 3.1 Chốt 1 — ca TỰ KIỂM BỘ DÒ chạy trong TIẾN TRÌNH CON

| Ca | Việc làm | Kết quả thật |
|---|---|---|
| `J1` | chạy một tệp unittest **cố ý hỏng** (`assertEqual(1, 2)`) trong **tiến trình con** | thoát **1** · output có `FAILED` · **không** có dòng `^OK` · luật phán trả **HỎNG** |
| `J1` | chạy ca **đạt** trong tiến trình con (đối chứng dương) | thoát **0** · `Ran 1 test` · luật phán trả **ĐẠT** |
| `J2` | ba kịch bản **lừa** luật phán | thoát 0 mà 0 ca ⇒ **HỎNG** · thoát 0 không dấu vết ⇒ **HỎNG** · in `OK` rồi thoát 1 ⇒ **HỎNG** |

Không có nhóm này thì mọi dòng "✓ … ca" của tệp thử **không chứng minh gì**.

### 3.2 Chốt 2 — ĐỐI CHỨNG DƯƠNG cho mọi ca PHỦ ĐỊNH

`Z_TongKet::z1` tự phán **HỎNG** nếu có nhóm nào có ca ÂM mà không có ca DƯƠNG. Sổ đối chứng in ra
ở cuối lượt chạy; các nhóm chính:

| Nhóm | Ca ÂM | ĐỐI CHỨNG DƯƠNG |
|---|---|---|
| `ghi-cheo` | B không đổi được membership / không khoá được tài khoản hãng / không huỷ được đơn của A | **chủ A làm được cả ba** (200) |
| `ghi-khong-phien` | 66 lượt ghi không phiên đều 401 | cùng cửa, có phiên hợp lệ → **201** |
| `csrf` | thiếu `X-Requested-With` → 403 | có header → **201** |
| `plane-nen-tang` | 16 lượt phiên tenant trên `/platform/*` đều 403 | `PLATFORM_ADMIN` → **200** |
| `quyen-nen-tang` | `PLATFORM_ADMIN` tạo tenant → 403 | `PLATFORM_OWNER` → **201**, CSDL +1 |
| `tang3` | `chay.sh` nguyên bản → **1** (thiếu nhị phân) | tầng 3 với nhị phân đúng → **0** (36 đạt) |
| `harness-g16` | nền ngoài thư mục tạm ⇒ **từ chối** (thoát 4) | nền tạm ⇒ chạy trọn (thoát 0) |
| `postgres-5432` | `VHPG_CONG=5432` ⇒ thoát 1 (từ chối) | cụm riêng ⇒ **42 ca**, thoát 0 |
| `dong-thoi` | cây tiêm *"mất ghi"* ⇒ thoát 1 | cây thật ⇒ thoát 0 |
| `dot-bien-M1…M5` | mỗi đột biến làm cổng tương ứng ĐỎ | cây thật làm cổng đó XANH |
| `tu-choi-khi-thieu-chot` | nền ngoài thư mục tạm ⇒ bộ thử tự thoát **3** | môi trường thật ⇒ chốt an toàn trả `None` |

### 3.3 Năm phép đột biến trên CÂY SAO CHÉP — chứng minh từng cổng CÓ RĂNG

Mỗi phép: chạy **cùng một hàm đo** trên cây THẬT (phải xanh) rồi trên **cây sao chép đã tiêm**
(phải đỏ). Cây thật **không** bị đụng (chỉ `app/**/*.py` được sao sang thư mục tạm).

| Mã | Đột biến | Cây THẬT | Cây ĐỘT BIẾN | Cổng được chứng minh |
|---|---|---|---|---|
| **M1** | bỏ nhánh `if nc is None: 401` của middleware | 0 cửa hở | **66 cửa hở** | `E2` |
| **M2** | bỏ `raise …403` trong `_can_csrf` | 403 | **201** | `E4` |
| **M3** | `if not nc.platform_role:` → `if False:` | 0 cửa hở | **4 cửa hở** | `F1` |
| **M4** | bỏ `AND tenant_id=?` khi tra membership | B bị chặn (404), dữ liệu A **nguyên** | B **SỬA ĐƯỢC** (200), dữ liệu A **đổi** | `E5` |
| **M5** | `quyen.co_quyen` luôn `True` | `PLATFORM_ADMIN` → 403 | **201** | `F3` |
| **M6** | bỏ lệnh ghi trong `nguoi_chay.py` (vẫn báo thành công) | bàn đo thoát 0 | **thoát 1** | `D1` |

---

## 4. DỤNG CỤ ĐO CŨNG PHẢI ĐƯỢC ĐO — năm lỗi của CHÍNH BÀN ĐO (lượt chạy đầu)

Lượt chạy đầu của tôi: **43 ca · 6 hỏng · 2 lỗi**. **Không một lỗi nào là lỗi sản phẩm** — cả tám
đều nằm trong **bàn đo**. Ghi lại đủ, vì một bàn đo không tự kiểm thì con số của nó vô nghĩa:

| # | Lỗi của bàn đo | Triệu chứng | Sự thật |
|---|---|---|---|
| 1 | **Ống stdout của máy chủ đầy** (`stdout=subprocess.PIPE` mà không đọc) | tầng 3: 5 ca hỏng, 4 ca `page.goto: Timeout 15000ms` | Máy chủ ghi 1 dòng JSON mỗi lượt HTTP; ống đầy 64KB thì nó **chặn ở lệnh ghi** ⇒ mọi lượt sau treo. Suýt được báo thành *"5 ca hỏng của sản phẩm"*. `chay.sh` ghi log ra **tệp** vì đúng lý do này. Đã sửa: ghi ra tệp ⇒ tầng 3 xanh **36/0/1** |
| 2 | Sai **tên bảng** (`don` thay vì `don_hang`) | 2 lỗi `sqlite3.OperationalError: no such table: don` | Bảng đơn là `don_hang` (`app/csdl.py:141`) |
| 3 | Bộ đọc kết quả `node --test` chỉ nhận `# pass` | tầng 1 bị báo **"TEO CA: 0 < 56"** | Node v26 in `ℹ pass 56`; tầng 1 thật ra **đạt 56/0**. Đã nhận cả hai dạng |
| 4 | `VIP_G18_PW_BROWSERS` **rỗng thì lặng lẽ quay về đường mặc định** | đối chứng âm `B2` báo sai | Đã sửa: biến được ĐẶT thì là ý chí của người chạy, không được fallback |
| 5 | **Đối chứng dương chọn sai hàng** (`/api/v2/memberships/1` = membership của chính TENANT_OWNER) | `E9` báo "chủ hợp lệ bị chặn: 403" | 403 đó là **ĐÚNG** theo thiết kế (`server.py:762`). Đã đổi sang membership của nhân viên |

**Bài học áp cho chính tài liệu này:** mọi con số "sản phẩm hỏng" phải đi qua câu hỏi *"bàn đo của
mình có đang nói dối không?"* trước khi được viết ra. Lượt 1 là bằng chứng rằng câu hỏi đó **không
phải hình thức**.

---

## 5. PHÁT HIỆN

| Mã | Mức | Nội dung | Bằng chứng đo được |
|---|---|---|---|
| **`N-G18-00`** | **HIGH (vận hành)** — *tái diễn `N-G17-00`, chưa vá* | **Biến `GIT_CONFIG_*` hỏng vẫn làm nền đóng băng ĐỎ cổng hồi quy mặc định.** `GIT_CONFIG_COUNT=2` nhưng `GIT_CONFIG_KEY_0` **RỖNG** ⇒ **mọi** lệnh `git` thoát **128**. Ba ca kiểm có gọi `git` trong `thu_bao_mat.py` + `thu_tich_hop.py` vì thế hỏng. | Lượt A **exit 1** (2 bộ ✗, 1460 ca) vs lượt B **exit 0** (38/38 ✓, 1460 ca) — **cùng cây, cùng HEAD, cùng số ca**; `git status --porcelain=v1` → `error: missing config key GIT_CONFIG_KEY_0` · **EXIT=128**. AG-00 báo "exit 0" ⇒ nhiệt kế của AG-00 và của tôi đang đo **hai môi trường khác nhau**, và không tài liệu nào nói ra. |
| **`N-G18-01`** | **MEDIUM (ca thử không ổn định)** | **Tầng 3 có một ca CHẬP CHỜN.** `05_ket_noi_jt.spec.js:359` (`08 — lối vào sâu #ket-noi-jt…`) chờ `#kn-cong` hiện trong **5 giây** (`expect` mặc định); dưới tải, màn Kết nối J&T chưa kịp hiện ⇒ đỏ. **5 lượt hợp lệ**: **4 lượt XANH 36/0/1** (3 lượt chạy riêng: 58,5s · 54,7s · 52,4s, và **lượt chốt trong bộ thử**); **1 lượt ĐỎ 33/1/2** (chạy trong bộ thử, lúc máy có tải) — cùng cây, cùng HEAD, cùng bộ spec. Khi máy có tải (bộ thử còn giữ máy chủ trong tiến trình, và các làn G18 khác đang chạy trên cùng máy — quan sát được `/tmp/veh_g18_ag03_data`, `/tmp/veh_g18_ag04`), màn Kết nối J&T chưa kịp hiện ⇒ đỏ. **Không phải lỗi môi trường** (nhị phân đúng, máy chủ sống, 33 ca khác vẫn xanh) và **không phải lỗi sản phẩm** (3/3 lượt riêng đều xanh) — đây là ca thử **không tất định dưới tải**. |
| **`N-G18-02`** | **LOW (cấu hình bộ chạy)** | `thu_giao_dien/chay.sh` **ghim cứng** `PLAYWRIGHT_BROWSERS_PATH=0` (tức `node_modules/playwright-core/.local-browsers`), mà worktree này **không có** thư mục đó — nhị phân `chromium*‑1194` chỉ nằm ở nguồn **NGOÀI repo**
mà `BAN_GIAO.md` §1 chỉ định (`~/code/veh4-g12-playwright/…`). Hệ quả: ở mọi worktree mới, tầng 3 **mặc định CHƯA ĐO** — và `chay_tat_ca.sh` lại chỉ hỏi `[ -d node_modules/@playwright ]` rồi in *"tầng 3: CÓ, nhưng KHÔNG chạy ở đây"* ⇒ người đọc tưởng tầng 3 dùng được. | `sh thu_giao_dien/chay.sh` → **exit 1** · `browserType.launch: Executable doesn't exist at …/chromium_headless_shell-1194/chrome-mac/headless_shell`; `ls node_modules/playwright-core/` → **không có** `.local-browsers`. (Đây là `N-G17-02` tái diễn ở dạng mới: G17 thiếu **cả** nhị phân; nay nhị phân có ở ngoài repo nhưng đường ghim vẫn sai.) |
| **`N-G18-03`** | **MEDIUM (tích hợp giữa các làn)** | **Cổng "cây sạch" của bộ thử wave TRƯỚC đỏ khi cây có tệp CHƯA COMMIT của làn KHÁC.** `thu_qa_g17.py::test_a1_cay_sach_va_head` chỉ miễn trừ **đúng hai tệp của G17**, nên hai tệp của tôi làm nó ĐỎ. Hệ quả trong suốt wave: `sh app/thu/chay_tat_ca.sh` **exit 1** vì lý do **TÍCH HỢP**, không phải lỗi sản phẩm — người nghiệm thu rất dễ đọc nhầm thành "G18 làm hỏng hồi quy". | Lượt C: **1503 ca · 39 bộ · exit 1**, bộ hỏng **duy nhất** là `thu_qa_g17.py` (`FAIL: test_a1_cay_sach_va_head`), còn `thu_qa_g18.py` **43 ca ✓**. Vân tay cây vẫn `d7a5bd43…`. Cổng này tự xanh lại khi các tệp được **commit** (`git status` sạch). **Bộ thử của TÔI cũng có đúng cơ chế đó** (`TEP_CUA_AG01_G18`) — nói thẳng, không giấu. |

**Ghi chú thêm (không phải phát hiện, nhưng phải nói):** `trien_khai/g16/chot_an_toan.py --tu-kiem`
in **10** cấu hình tổng hợp, không phải 9 như một số tài liệu G16 mô tả. Đo thẳng: dòng
`TỰ KIỂM BỘ DÒ CHỐT AN TOÀN G16 — 10 cấu hình tổng hợp` (log `g16_harness.log`).

---

## 6. CHƯA ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

Đối chiếu **từng mục** của `docs/QA_G17.md` §5 (**11 mục**): **bảy mục đã có phép đo độc lập**
(trong đó **hai mục có phạm vi hẹp hơn tên gọi** — nói rõ ngay tại dòng), **bốn mục còn nguyên**.
Mục nào còn thì nói thẳng là còn:

| §5 `QA_G17` | Trạng thái sau G18 | Ghi chú |
|---|---|---|
| 1. Gọi hãng thật (kể cả sandbox) · TLS thật tới `*.jtexpress.vn` | **CÒN CHƯA ĐO** | `V-G09-01` + `V-13906-05` **CHƯA CẤP**. Không thử lấy một byte nào; `A6` đo **0** lượt `connect` ra ngoài loopback |
| 2. `cancelOrder`/`getShippingFee`/`getShippingLabel`/`getOrder` đầu-cuối | **CÒN CHƯA ĐO** | Đường dẫn **CHƯA ĐỌC ĐƯỢC** (`duong=None`); tôi chỉ đo được rằng hệ **DỪNG ĐÚNG**, không đo được hành vi thật của hãng |
| 3. Harness SANDBOX AG-04 (`trien_khai/g16/**`) | **ĐÃ ĐÓNG** | §2.1 — `C1`–`C3`, thoát 0, có đối chứng âm thoát 4 |
| 4. Tầng 3 (DOM/CSS Chromium) | **ĐÃ ĐÓNG, CÓ ĐIỀU KIỆN** | §2.2 — 36 ca chạy thật; **còn chập chờn** (`N-G18-01`) và **phụ thuộc nhị phân ngoài repo** (`N-G18-02`) |
| 5. Đa tiến trình / đa luồng thật | **ĐÃ ĐÓNG một nửa** | §2.3 — `dong_thoi/chay.py` (8 tiến trình thật) **đã đo**. `thu_http_jt.py` chạy riêng: **57 ca · `OK` · thoát 0** (91,8 giây). **Đa luồng trong MỘT tiến trình dưới tải lớn, nhiều máy, nhiều tiến trình `http_jt` — vẫn CHƯA ĐO** |
| 6. Mọi cặp `(cửa × POST/PUT/DELETE)` | **ĐÃ ĐÓNG (có phạm vi)** | §2.4 — 66 lượt không phiên + 25 cửa có tham số. **CÒN CHƯA ĐO:** *body hợp lệ đầy đủ* cho các cửa tài chính/import/AI (tôi đo được **không 2xx + không rò canary + dữ liệu A không đổi**, **không** đo được nhánh nghiệp vụ sâu bên trong khi chủ hợp lệ gọi đúng) |
| 7. `/api/v2/platform/*` | **ĐÃ ĐÓNG** | §2.5 — 16 lượt 403 + đối chứng dương 200 |
| 8. Hai tầng frontend (56 + 36 ca) | **ĐÃ ĐÓNG** | §2.6 — chạy độc lập, có cổng chống **teo ca** |
| 9. V11 PostgreSQL | **ĐÃ ĐÓNG** | §2.7 — cụm **RIÊNG** `55432`, 42 ca · 0 bỏ qua; `:5432` **CHẶN CỨNG**, vân tay trước = sau |
| 10. Ngoài phạm vi theo thiết kế | **CÒN** | deploy · push · HTTPS thật · tunnel · VPS · chuyển CSDL nghiệp vụ sang PostgreSQL (`D-8`) · credentials hãng thật · AI/LLM thật · dữ liệu lớn · Safari/Firefox · mã `110` (`D-4`) |
| 11. Chưa có người đọc lại | **CÒN** | Toàn bộ là tác tử AI; tài liệu này **không** thay thế người nghiệm thu |

**Ba điều TÔI CỐ Ý KHÔNG LÀM:**

1. **Không sửa một dòng mã sản phẩm nào** — kể cả `N-G18-00` (một biến môi trường), `N-G18-01`
   (một timeout trong spec) hay `N-G18-02` (một đường ghim trong `chay.sh`). AG-01 **không** viết
   mã sản phẩm: một bản vá do người kiểm viết ra thì chính người kiểm không còn đo được nó độc lập.
2. **Không diễn giải kết quả tầng 3 thành "giao diện ĐẠT"** — 36/37 ca xanh ở **một** lượt, và
   **2/4 lượt đỏ ở cùng một ca**. Phán quyết đúng là *"đo được, có một ca chập chờn"*.
3. **Không gộp `BỎ QUA` vào `ĐẠT`.** Bộ thử của tôi có **1 ca bỏ qua** trong làn mặc định
   (`H3` — chạy trọn PostgreSQL chỉ khi `VIP_G18_DAY_DU=1`) và **0 ca bỏ qua** khi bật làn đầy đủ.
   Lượt tôi dùng để ký phán quyết ở §2 là lượt **`VIP_G18_DAY_DU=1`** ⇒ **0 bỏ qua** ở các làn
   mang phán quyết.

---

## 7. CHẠY LẠI — bốn lệnh

```sh
cd <worktree g18-ag01-qa>
export GIT_CONFIG_COUNT=0        # N-G18-00; thiếu dòng này thì 2 bộ thử sẽ đỏ GIẢ

# 1) bộ thử độc lập của AG-01 G18 (43 ca · 0 bỏ qua · ~1,5 phút ở làn đầy đủ · ~3,4 phút nếu tầng 3 chậm)
VIP_G18_HEAD=7b741c88b3b280d65f80b5e11301f17ebd767b26 VIP_G18_DAY_DU=1 \
    python3 app/thu/thu_qa_g18.py

# 2) hồi quy toàn phần trên nền đóng băng
rm -rf /tmp/veh_g18_ag01_qa_base && mkdir -p /tmp/veh_g18_ag01_qa_base
VIP_HUB_DATA=/tmp/veh_g18_ag01_qa_base sh app/thu/chay_tat_ca.sh

# 3) vân tay cây — phải khớp §1.0 khi miễn trừ đúng hai tệp AG-01
{ git ls-files -s; git status --porcelain=v1 | grep -vE '(docs/QA_G18\.md|app/thu/thu_qa_g18\.py)'; } \
    | shasum -a 256          # → d7a5bd4339de0db551ab91979f6df5b57361de6bc20ddab019bb0d3f3d8ddeb1

# 4) vân tay cụm PostgreSQL hệ thống — phải TRƯỚC = SAU
python3 trien_khai/postgres/van_tay_cum.py --chup --cong 5432
```

**Lối tắt có nói ra (không bao giờ là ĐẠT):** `VIP_G18_BO_TANG3=1` ⇒ làn Chromium chuyển thành
**BỎ QUA** kèm lý do (dùng khi chạy bộ chạy chung ở nơi không có nhị phân, để nó không phụ thuộc
Chromium một cách im lặng).

---

## 8. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY

- Mọi số đo thuộc **`7b741c8`** và **chỉ** `7b741c8`; cây khác thì phải đo lại.
- Bộ thử của tôi **tự dựng CSDL riêng** bằng `csdl.mo()` + `migrate.chay()`, trong thư mục tạm.
  Nó **không** đo trên `app/du-lieu/` và **không** đo trên dữ liệu thật.
- Mọi phép đo lớp HTTP là **trong tiến trình** + máy chủ bind `127.0.0.1` **cổng 0**.
  **Không** đo sau proxy thật, **không** đo TLS thật, **không** đo đa máy.
- `M1`–`M6` chứng minh **cổng có răng**, **không** chứng minh mã sản phẩm đúng ở mọi ngả khác.
- Làn tầng 3 dùng nhị phân Chromium ở **ngoài repo** (nguồn `BAN_GIAO.md` §1 chỉ định). Ai chạy lại
  mà không có đường đó thì làn này **BỎ QUA** (CHƯA ĐO) — **không** phải ĐẠT.
- Hai tệp AG-01 G18 là tệp **MỚI, chưa `git add`**; cổng "cây sạch" của bộ thử **miễn trừ đúng hai
  đường dẫn đó** và không miễn trừ gì khác (`TEP_CUA_AG01_G18`).
- Lượt tầng 3 sinh tệp **ngoài git** trong `thu_giao_dien/_ket-qua/` và `thu_giao_dien/_bao-cao/`
  (đã có trong `.gitignore`); `git status -uall` sau đó **không** thấy gì ngoài hai tệp AG-01.
- **SHA256 `app/thu/thu_qa_g18.py`** (bản đã đo, 1.419 dòng, 80.738 byte):
  `9cca7a99d80707af12c6aa323d1b52f9ecb0ae9fee34552ab71592f03f21f04a`.
- **SHA256 của chính tài liệu này** không thể nằm trong nó — nó được ghi ở báo cáo
  `worker_done` gửi AG-00 (cùng SHA của tệp bộ thử, ở dạng ĐÓNG BĂNG sau lượt chốt).
