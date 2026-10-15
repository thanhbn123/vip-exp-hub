# NGHIỆM THU G17 — AG-01 (QA/VERIFIER)

**Vai:** AG-01 QA/VERIFIER · **Nhiệm vụ:** `task_3662f53f86f9` · **Dispatch:** `ctx_a78707b421db`
**Nền đo:** `integration/g16 @ 98baeb357214d41a9380467fde2fee2b94fd31cc` (`98baeb3`), worktree riêng
`g17-ag01-qa`.
**Tệp AG-01 G17 được phép tạo (và là hai tệp DUY NHẤT đã tạo):**
`app/thu/thu_qa_g17.py` (bộ thử, **53 ca**) · `docs/QA_G17.md` (tài liệu này).
**Lệnh chạy bộ thử của tôi:**
`VIP_G17_HEAD=98baeb357214d41a9380467fde2fee2b94fd31cc python3 app/thu/thu_qa_g17.py`

**Luật bằng chứng tự áp:** mọi khẳng định dưới đây đi kèm **lệnh thật + mã thoát thật + số ca thật**.
Ca phủ định nào cũng có **đối chứng dương** trong cùng nhóm (`DOI_CHUNG`, `Z_TongKet` tự phán HỎNG
nếu thiếu). Bộ dò được **tự kiểm** bằng một ca cố ý hỏng chạy trong tiến trình con **và** bằng
**bốn phép đột biến trên cây sao chép**. Cái gì không đo được thì nằm ở §5 **CHƯA ĐO** — đó là
**lỗ hổng phạm vi, KHÔNG phải ĐẠT**.

**Tuân thủ tuyệt đối (đã tự kiểm bằng máy, không bằng lời):** không gọi API hãng thật kể cả
sandbox (`A6` đếm socket: 0 lượt `connect` ra ngoài loopback) · không push/deploy/mở cổng ra
Internet (máy chủ đo bind `127.0.0.1` **cổng 0**) · không mở `CHO_PHEP_LIVE` (`A4`: mọi lớp trong
`adapter._DANG_KY` đều `False`) · không credential thật, không `.env` (CSDL và khóa nằm trong thư
mục tạm) · không đoán mã `110` (`E3`) · giữ chốt D-9 (`E1`/`E2`) · vẫn SQLite (`A7`) · không đổi
mô hình.

---

## 0. BẢNG PHÁN QUYẾT

| # | Cổng | Cách đo (bộ thử của tôi) | Phán quyết |
|---|---|---|---|
| **F0-a** | Cây SẠCH tại mốc đo | `A1` — `git status -uall` rỗng (miễn trừ đúng 2 tệp AG-01) | **ĐẠT** |
| **F0-b** | `CHO_PHEP_LIVE=False` mọi lớp | `A4` — vòng lặp ĐỘNG trên `adapter._DANG_KY` | **ĐẠT** |
| **F0-c** | Adapter không có đường mạng thật | `A5` — AST `app/adapter*.py`: không `requests/httpx/urllib.request/http.client/socket` | **ĐẠT** |
| **F0-d** | Không kết nối ra ngoài | `A6` — bộ đếm `socket.connect` | **ĐẠT** (0 lượt) |
| **V5** | Cách ly tenant **toàn cục** (§L2.8, mục MỞ) | `B0`–`B9` — 2 tenant thật + **41 cửa** rút từ `server.py` | **ĐẠT** (phạm vi §5) |
| **V6** | RBAC (§L2.8, mục MỞ) | `C1`–`C8` — ma trận ĐỘNG trên `role_permissions` + HTTP | **ĐẠT** · 1 phát hiện `N-G17-01` (LOW) |
| **V7** | AES-256-GCM đầy đủ (§L2.8, mục MỞ) | `D1`–`D8` — ca RIÊNG, không mượn `thu_bao_mat.py`; 4 hàm hợp đồng chỉ được GỌI | **ĐẠT** |
| **V2b** | D-9 `area` chặn cứng ngoài mock | `E1`/`E2` | **ĐẠT** |
| **V2c** | D-4 mã `110` không được đoán | `E3` | **ĐẠT** |
| **V1b** | 4 thao tác `duong=None` dừng đúng · **BLOCKED kèm đúng giấy phép còn thiếu** | `E4`/`E5`/`E6`/`E7` | **ĐẠT** |
| **CHỐT AN TOÀN** | Bộ thử **TỰ CHỐI CHẠY** khi thiếu nền tạm / live / loopback | `H1`/`H2` — chạy thật trong tiến trình con | **ĐẠT** (thoát **3**, không tạo gì) |
| **V11b** | D-8 vẫn SQLite | `A7` | **ĐẠT** |
| **V13** | Bộ chạy hồi quy: luật phán | `G1`/`G2` + quét tĩnh | **ĐẠT** · 1 phát hiện `N-G17-02` + ghi chú lệnh `python3` trên script `sh` |
| **BASELINE** | `chay_tat_ca.sh` trên nền đóng băng | §1 — **3 lượt chạy thật** | **ĐẠT** khi gỡ biến git; **HỎNG (exit 1)** đúng như harness đưa — xem `N-G17-00` |
| **AG-04 harness** | `trien_khai/g16/**` | không dựng phép đo độc lập | **CHƯA ĐO** |
| **TẦNG 3** | DOM/CSS Chromium | `sh thu_giao_dien/chay.sh` → **exit 1**, thiếu nhị phân Chromium | **CHƯA ĐO** |

**Phán quyết một dòng:** ba mục **MỞ** của §L2.8 (V5 · V6 · V7) nay **đã có phép đo độc lập và
đều ĐẠT** trong phạm vi ghi ở §5; nền `98baeb3` **ĐẠT** hồi quy **chỉ khi** gỡ biến môi trường
`GIT_CONFIG_*` hỏng; hai phát hiện mới (`N-G17-00` mức **HIGH vận hành**, `N-G17-02` mức **MEDIUM**)
và hai ghi chú tài liệu (`N-G17-03`, `N-G17-04`).

---

## 1. BASELINE ĐỘC LẬP TRÊN NỀN ĐÓNG BĂNG — lệnh thật, mã thoát thật

### 1.0 Vân tay cây + mốc giờ + HEAD (luật §41)

```sh
export GIT_CONFIG_COUNT=0                      # xem N-G17-00: biến này hỏng thì MỌI lệnh git hỏng
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

| Mốc | Giá trị |
|---|---|
| **Trước lượt đo** (2026-10-15 **16:34:35 +07** = 09:34:35Z) | `4e6d7edb111bbb236340b369d7adc242ca2e70c19e4c5f7d5e4c025af5ae46d5` |
| **Sau lượt A** (16:36:02 +07) | `4e6d7edb…` — **KHÔNG đổi** |
| **Sau lượt B** (16:38:07 +07) | `4e6d7edb…` — **KHÔNG đổi** |
| **Sau lượt C** (16:44:04 +07) | `4e6d7edb…` (miễn trừ 2 tệp AG-01) — **KHÔNG đổi** |
| **Sau lượt E** (16:48:36 +07) và đo lại lúc 16:48:45 +07 | `4e6d7edb…` (miễn trừ 2 tệp AG-01) — **KHÔNG đổi** |
| **Cuối cùng** — vân tay **THÔ** khi đã có đủ 2 tệp AG-01 | `f8c833ba521de210864b957d239a5bee18a9dee40870ae11735147c338c16c55` |
| `git rev-parse HEAD` trước / sau | `98baeb357214d41a9380467fde2fee2b94fd31cc` / **y hệt** |
| Số tệp được theo dõi | **220** |

**Hai vân tay khớp nhau từng byte:** lệnh Python trong bộ thử (`van_tay_cay(bo_qua=TEP_CUA_AG01_G17)`)
và lệnh shell `{ git ls-files -s; git status --porcelain=v1 | grep -v <2 tệp>; } | shasum -a 256`
cho **cùng** `4e6d7edb…`. Nghĩa là: ngoài hai tệp mà đề bài cho phép tôi tạo, **không một byte nào**
của cây đổi trong suốt lượt đo — kể cả khi bốn worktree G17 (`ag01-qa`, `ag02-transport`,
`ag03-business-api`, `ag04-webhook`) cùng trỏ `98baeb3`.

> **Rủi ro `N-05` ("bốn làn chung MỘT cây") KHÔNG áp cho lượt này.** `git worktree list` cho thấy
> bốn làn G17 nằm ở **bốn thư mục khác nhau**, cùng một commit. Vân tay trước = sau là **bằng chứng
> đo được** rằng không làn nào ghi vào cây của tôi — chứ không phải suy đoán.

### 1.1 Ba lượt chạy thật

```sh
rm -rf /tmp/veh_g17_ag01_qa_base && mkdir -p /tmp/veh_g17_ag01_qa_base
# LƯỢT A — ĐÚNG NHƯ HARNESS ĐƯA (giữ nguyên GIT_CONFIG_*)
VIP_HUB_DATA=/tmp/veh_g17_ag01_qa_base sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
# LƯỢT B — GỠ biến git hỏng
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g17_ag01_qa_base_fix sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
```

| | **Lượt A** (nguyên văn) | **Lượt B** (gỡ `GIT_CONFIG_*`) | **Lượt C** (B + `thu_qa_g17.py`) |
|---|---|---|---|
| Bắt đầu → kết thúc (UTC) | 09:34:42 → 09:36:02 | 09:36:45 → 09:38:07 | 09:42:40 → 09:44:04 |
| **Mã thoát** | **1** | **0** | **0** |
| Số bộ thử python | 36 bộ (34 ✓ · **2 ✗**) | 36 bộ (36 ✓ · 0 ✗) | **37 bộ** (37 ✓ · 0 ✗) |
| Số ca python | **1284** | **1284** | **1333** (= 1284 + **49** ca của AG-01) |
| Frontend tầng 1 + 2 | 56 + 36 ca | 56 + 36 ca | 56 + 36 ca |
| E2E qua HTTP thật | 41/41 | 41/41 | 41/41 |
| Cây / HEAD | `4e6d7edb…` / `98baeb3` | y hệt | y hệt |

**Hai bộ hỏng ở lượt A:** `thu_bao_mat.py` (57 ca · `FAILED (failures=1)`) và `thu_tich_hop.py`
(12 ca · `FAILED (failures=2)`). Ba ca hỏng, **cả ba đều là ca kiểm liên quan tới GIT**:
`F_KhongTutVeSoDoYeu::test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git` ·
`CanhCauTruc::test_04_khoa_ma_hoa_khong_duoc_vao_git` ·
`G16_CauHinhVaPhanTang::test_11_khong_co_secret_that_trong_cay_lam_viec`.

### 1.2 Thí nghiệm A/B tách **lỗi môi trường** khỏi **lỗi sản phẩm**

CÙNG cây, CÙNG hai bộ thử, CÙNG 57 + 12 ca; **chỉ** biến môi trường khác:

```sh
VIP_HUB_DATA=/tmp/veh_g17_cmp  python3 app/thu/thu_bao_mat.py   # → Ran 57 · FAILED (failures=1) · exit 1
VIP_HUB_DATA=/tmp/veh_g17_cmp  python3 app/thu/thu_tich_hop.py  # → Ran 12 · FAILED (failures=2) · exit 1
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g17_cmp2 python3 app/thu/thu_bao_mat.py   # → Ran 57 · OK · exit 0
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g17_cmp2 python3 app/thu/thu_tich_hop.py  # → Ran 12 · OK · exit 0
```

⇒ **Kết luận đo được:** đây là **lỗi MÔI TRƯỜNG, không phải lỗi mã sản phẩm** — nhưng nó làm
**cổng hồi quy mặc định của nền ĐỎ**, nên nó là một phát hiện vận hành thật (`N-G17-00`, §4).

---

## 2. BỘ THỬ ĐỘC LẬP `app/thu/thu_qa_g17.py`

### 2.1 Kết quả

```sh
VIP_G17_HEAD=98baeb357214d41a9380467fde2fee2b94fd31cc python3 app/thu/thu_qa_g17.py
```

| | |
|---|---|
| **Số ca** | **53** (`Ran 53 tests`) |
| **Mã thoát** | **0** (`OK`) |
| **Thời gian** | **5,766 s** |
| **Cổng** | bind `127.0.0.1` **cổng 0** — đo được `http://127.0.0.1:53557`; **không** trùng `8888/8899/9000/9999/8947` |
| **CSDL** | thư mục tạm `…/veh-g17-qa-*` (KHÔNG BAO GIỜ `app/du-lieu/`) |
| **Chạy được cả khi biến git hỏng?** | **CÓ** — exit 0 khi chạy đúng như harness đưa (bộ thử tự gỡ biến cho các lệnh git của nó) |

### 2.2 Hai chốt chặn đã có thật

**(a) Ca TỰ KIỂM BỘ DÒ — ca cố ý hỏng chạy trong TIẾN TRÌNH CON** (`F1`/`F2`/`F3`):

- `F1`: một tệp unittest **cố ý hỏng** (`assertEqual(1, 2)`) chạy bằng tiến trình con ⇒
  **mã thoát ≠ 0**, output có `FAILED`, và **không** có dòng `^OK`.
- `F2` (đối chứng dương): ca ĐẠT ⇒ **exit 0**, `Ran 1 test`, có `^OK`.
- `F3`: bản sao **luật phán của `chay_tat_ca.sh`** bị ba kịch bản lừa: *thoát 0 mà 0 ca* · *thoát 0
  không dấu vết* · *in `OK` rồi thoát 1* — cả ba đều bị phán **HỎNG**; và nó phán ĐẠT/BỎ QUA đúng
  ở hai kịch bản thật.

**(b) BỐN PHÉP ĐỘT BIẾN trên cây sao chép — chứng minh từng cổng CÓ RĂNG** (`F4`–`F7`).
Mỗi phép đo **cùng một đường đo** trên cây thật và trên cây đột biến:

| Mã | Đột biến tiêm vào bản sao `app/` | Cây THẬT | Cây ĐỘT BIẾN | Kết luận |
|---|---|---|---|---|
| `M1` | `bao_mat.py`: bỏ AAD (`aad.encode() if aad else None` → `None`) | `KETQUA=CHAN` | `KETQUA=RO` | cổng V7 **đỏ được** |
| `M2` | `trang_thai_hang.py`: xoá `("jt", 110)` khỏi sổ nhập nhằng | `KETQUA=DAT` | `KETQUA=HONG` | cổng D-4 **đỏ được** |
| `M3` | `adapter_jt.py`: mở chốt `chot_chan_anh_xa_area` (`if True: return`) | `KETQUA=CHAN` | `KETQUA=RO` | cổng D-9 **đỏ được** |
| `M4` | `server.py`: `tenant_id = int(ts.get("tenant_id") or nc.tenant_id)` | `"ro": false` | `"ro": true` | cổng cách ly tenant V5 **đỏ được** |

`M4` là phép đột biến đáng giá nhất: nó tiêm **đúng lỗi mà V5 sinh ra để bắt** (tenant lấy từ
query thay vì từ phiên) và cổng V5 **thấy** canary của tenant A lọt sang tenant B.

**(c) Đối chứng dương cho mọi ca phủ định** — `Z1` đọc sổ `DOI_CHUNG` và **tự phán HỎNG** nếu nhóm
nào có ca âm mà không có ca dương. Đo được: **29 nhóm có ca âm, 29/29 đều có đối chứng dương**
(tổng **29 ca âm · 73 ca dương**); sổ in ra đầy đủ ở cuối lượt chạy.

**(d) CHỐT AN TOÀN tự chối chạy — và chứng minh nó THẬT SỰ chối** (`H1`/`H2`).
Trước mọi phép đo, bộ thử kiểm ba chốt: nền CSDL **trong thư mục tạm và ngoài cây repo** · **không**
adapter nào `CHO_PHEP_LIVE=True` · máy chủ bind **loopback**. Thiếu một chốt ⇒ `SystemExit(3)`,
**không** chạy tiếp rồi báo ĐẠT. Đo được (tiến trình con, `VIP_G17_DATA=~/.veh-g17-phai-tu-choi`):
**thoát 3**, in `TỪ CHỐI CHẠY — thiếu chốt an toàn: nền CSDL KHÔNG nằm trong thư mục tạm…`,
**không** in dấu `LOT-QUA-DUOC`, và **không tạo gì** ở đường đó. `H2` còn tiêm động một lớp adapter
giả `CHO_PHEP_LIVE=True` và bind `0.0.0.0`/`192.168.1.9` để chứng minh bộ kiểm **thấy** — rồi trả
sổ đăng ký về nguyên trạng.

#### 2.3 Các lượt C/D/E — bộ thử của tôi nằm TRONG bộ chạy chung

```sh
env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g17_ag01_qa_final3 sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
```

| | **Lượt C** (bộ thử 49 ca) | **Lượt D** (49 ca) | **Lượt E — CUỐI** (bộ thử **53 ca**, nội dung đóng băng) |
|---|---|---|---|
| Bắt đầu → kết thúc (UTC) | 09:42:40 → 09:44:04 | 09:45:02 → 09:46:23 | 09:47:13 → 09:48:36 |
| **Mã thoát** | **0** | **0** | **0** |
| Dòng của bộ thử tôi | `✓ thu_qa_g17.py 49 ca` | `✓ thu_qa_g17.py 49 ca` | `✓ thu_qa_g17.py 53 ca` |
| Tổng python | 1333 ca · 37 bộ | 1333 ca · 37 bộ | **1337 ca · 37 bộ** |
| Bộ hỏng | KHÔNG | KHÔNG | **KHÔNG** |
| Frontend / E2E | 56 + 36 · 41/41 | 56 + 36 · 41/41 | 56 + 36 · **41/41** |
| Vân tay cây (miễn trừ 2 tệp AG-01) | `4e6d7edb…` | `4e6d7edb…` | `4e6d7edb…` |

Nghĩa là: tệp thử mới **vào được** bộ chạy tự dò, **đếm được số ca thật**, **không** làm đỏ làn nào
(`docs/QA_G13_G15.md` §7.3 lo đúng điều này khi bộ chạy tự dò `app/thu/thu_*.py`).

#### 2.3.1 LƯỢT E — số cuối cùng (bộ thử **53 ca**, nội dung đóng băng)

| | |
|---|---|
| Lệnh | `env GIT_CONFIG_COUNT=0 VIP_HUB_DATA=/tmp/veh_g17_ag01_qa_final3 sh app/thu/chay_tat_ca.sh` (mã thoát lấy **ngay sau** lệnh, không qua ống) |
| Bắt đầu → kết thúc | 2026-10-15 09:47:13Z → **09:48:36Z** (83 giây) |
| **Mã thoát** | **0** |
| Dòng của bộ thử tôi | **`✓ thu_qa_g17.py  53 ca`** |
| Tổng python | **1337 ca · 37 bộ chạy thật** (= 1284 + 53; = 36 + 1) · **bộ hỏng: KHÔNG** (0 dòng ✗) |
| Frontend / E2E | 56 + 36 ca · E2E **41/41** |
| **SHA256 `app/thu/thu_qa_g17.py` TRƯỚC = SAU** | `7a920e8ab84173e78087d0a34dff170ce7611d845dc2d0f4d90fff2166fd1bb5` — **không đổi trong suốt lượt đo** |
| Vân tay cây (miễn trừ 2 tệp AG-01) | `4e6d7edb…` — **KHÔNG đổi** (đo lại lúc 16:48:45 +07, sau lượt E) |
| `git rev-parse HEAD` | **`98baeb357214d41a9380467fde2fee2b94fd31cc`** — y hệt trước lượt A (và y hệt sau mọi lượt) |

*(Một chi tiết đáng ghi, vì nó là `N-G17-00` tái diễn ngay trong lượt cuối: hai dòng `HEAD=` và vân
tay in ở **đầu/cuối log của lượt E** ra **RỖNG** — vì chính script ghi log đó gọi `git` mà **quên**
gỡ `GIT_CONFIG_*`. Tôi đã đo lại hai giá trị này bằng lệnh có gỡ biến và ghi đúng ở bảng trên. Đây
là lần thứ ba trong một buổi mà cùng một biến môi trường làm một phép đo ra rỗng/sai.)*

---

## 3. BA MỤC **MỞ** CỦA §L2.8 — đo thế nào, và đo được gì

### 3.1 V5 — Cách ly tenant **toàn cục**

**Cách đo (không chép tay danh sách cửa):** bộ thử **rút mọi đường `/api/v2/…` tĩnh từ chính
`app/server.py`** bằng regex, bỏ các nhánh `auth/`, `platform/`, `webhook/nhan`, rồi gọi từng cửa
bằng phiên của tenant B và tìm **canary** — một chuỗi ngẫu nhiên chỉ tồn tại trong dữ liệu tenant A
(tên tenant + tên khách hàng).

| Phép đo | Kết quả |
|---|---|
| Số cửa rút được | **41** |
| Cửa trả 200 cho chính chủ A (đối chứng dương) | **32** |
| Cửa trả 200 cho B | 32 |
| **Cửa để canary của A lọt sang B** | **0** |
| Đọc chéo một bản ghi (`GET /khach-hang/<idA>` bằng B) | **404** (A: 200 + canary) |
| `tenant_id` trong **body** (`POST /khach-hang`) | **bị bỏ qua** — hàng mới thuộc B, kiểm bằng `SELECT tenant_id` |
| `tenant_id` trong **query** (`GET /khach-hang?tenant_id=<A>`) | **bị bỏ qua** — canary vắng |
| Đổi tenant không membership (`POST /auth/doi-tenant`) | **403** (người có membership hai tenant: **200**) |
| Xoá chéo membership (`DELETE /memberships/<idA>` bằng B) | **404** và hàng còn nguyên (chủ A: **200**) |
| Danh sách tài khoản hãng của B chứa `webhook_ma` của A | **KHÔNG** (A thấy của chính A) |
| Webhook vô danh, chữ ký SAI | **401** và **0** dòng `wh_su_kien` mới |

**Phạm vi:** quét đủ **mọi đường tĩnh rút được** (gọi bằng GET) + **4 phép ghi/xoá có chủ đích** (body/query/doi-tenant/xoá).
**Chưa** quét hết mọi cặp `(cửa × POST/PUT/DELETE)` — ghi ở §5.

### 3.2 V6 — RBAC

**Ma trận ĐỘNG:** đọc `role_permissions` từ CSDL rồi so với `quyen.MA_TRAN` trong mã nguồn.

| Phép đo | Kết quả |
|---|---|
| CSDL ↔ mã nguồn (**6 vai trò**, **28 quyền** khai trong `quyen.QUYEN`) | **khớp hoàn toàn** (bộ so tự bắt được lệch khi tiêm vào bản sao) |
| VIEWER **đọc** khách hàng | **200** (đối chứng dương) |
| VIEWER **ghi** khách hàng | **403** — và STAFF (có `tenant.khach.ghi`) ghi được: **201** |
| VIEWER đọc danh sách thành viên | **403** — OWNER: **200** |
| `TENANT_ADMIN` cấp vai trò `TENANT_OWNER` | **403** (leo thang) — cấp `TENANT_VIEWER`: **201** |
| `TENANT_STAFF` mời thành viên | **403** — OWNER: **201** |
| Mọi `self._can(nc, "…")` trong `server.py` dùng quyền CÓ THẬT (**26 tên quyền** khác nhau được gọi) | **ĐẠT**, trừ **1 chỗ** → `N-G17-01` |

### 3.3 V7 — AES-256-GCM đầy đủ (bộ ca RIÊNG, không mượn `thu_bao_mat.py`)

| Phép đo | Kết quả |
|---|---|
| Đi–về nguyên vẹn (đối chứng dương) | **ĐẠT** |
| **Lật 1 bit** trong bản mã | **ném lỗi** (không trả bản rõ) — bản chưa sửa vẫn đọc được |
| **Sai AAD** (tenant khác) | **ném lỗi** — đúng AAD: đọc được |
| **Đổi chỗ hai bản mã giữa hai tenant TRONG CSDL** | đọc bằng AAD của chủ ⇒ **ném lỗi** |
| Bản mã `v3` mang `key_id` | **CÓ**; bản mã mới: `can_xoay()` = `False` |
| Gọi TRẦN `ma_hoa()`/`giai_ma()` ngoài `bao_mat.py`/`migrate.py` | **0 chỗ** (quét AST, không grep chú thích) |
| **Xoay khoá** (`bao_mat.xoay_khoa()`) | `hong=[]`; `key_id` **đổi**; bí mật **vẫn đọc được** ⇒ **không mất secret** |

---

## 3b. YÊU CẦU MỞ RỘNG (Owner/Codex chốt — `msg_bb195b03f767`, 09:38:19Z) — đối chiếu TỪNG MỤC

Không huỷ việc đang làm; đây là phần mở rộng, và mọi mục dưới đây đã được **ĐO THẬT** (không chỉ
nằm trong kế hoạch):

| # | Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|---|
| **1** | **V5** — hai tenant THẬT (A và B), quét **mọi cửa** `/api/v2/*`, khẳng định B không đọc/ghi/xoá được dữ liệu của A; **đối chứng dương**: chính cửa đó với chủ hợp lệ phải trả 200 | **ĐÃ ĐO** | §3.1: **41 cửa**; A được **200 ở 32 cửa**; **0 cửa** để canary của A lọt sang B; 4 phép ghi/xoá có chủ đích (body · query · doi-tenant · xoá membership) đều **bị chặn**, mỗi phép có đối chứng dương |
| **2** | **V6** — ma trận ĐỘNG `role × hành_động` từ bảng `role_permissions`; **KHÔNG** hằng số viết cứng; ma trận **rỗng ⇒ CHƯA ĐO**, không báo ĐẠT | **ĐÃ ĐO** | `C6` đọc **68 ô** từ CSDL rồi so với mã nguồn (khớp hoàn toàn). Nếu bảng rỗng, ca này `skipTest("CHƯA ĐO: … ma trận rỗng KHÔNG phải ĐẠT")` — **không** có đường nào để nó thành ĐẠT |
| **3** | **V7** — (a) tự sửa một byte bản mã ⇒ HỎNG · (b) đổi chỗ hai bản mã giữa hai tenant trong CSDL ⇒ HỎNG · (c) sai AAD ⇒ HỎNG · (d) bản mã mang `key_id` dạng `v3$…`; **bốn hàm hợp đồng `ma_hoa_cred`/`giai_ma_cred`/`ma_hoa_wh`/`giai_ma_wh` CHỈ được GỌI, KHÔNG được viết lại** | **ĐÃ ĐO** | §3.3 — bốn dòng (a)(b)(c)(d). Thêm `D8`: **0 tệp** ngoài `bao_mat.py` định nghĩa lại bốn hàm (bộ quét tự bắt được mẫu tiêm vào); hợp đồng **đang được gọi từ 7 tệp**; AES-GCM trực tiếp chỉ được ở `bao_mat.py` + `sao_luu_khoa.py` (KEK của bản sao lưu — **lớp secret KHÁC**, có chủ đích) |
| **4a** | Harness phải chạy **MOCK trên nền TẠM**, **chỉ loopback**, và **TỰ CHỐI CHẠY** nếu thiếu chốt an toàn | **ĐÃ ĐO** | §2.2(d) + `H1`/`H2`: nền không phải thư mục tạm ⇒ **thoát 3**, in lời từ chối, **không tạo gì**; bộ kiểm thấy được adapter giả `CHO_PHEP_LIVE=True` và bind `0.0.0.0`/`192.168.1.9` |
| **4b** | Chặng nào **chạm hãng** phải ghi **BLOCKED kèm ĐÚNG giấy phép còn thiếu**, **KHÔNG** tính là ĐẠT | **ĐÃ ĐO** | `E7`: `sandbox` bị chặn kèm **`V-G09-01` + `V-13906-05`** ngay trong thông điệp; `production` kèm *"cần anh Thành duyệt riêng"*; bốn thao tác chưa xác minh nêu **đúng tên thao tác** + *"đường dẫn API đầy đủ CHƯA được xác minh"*. Đối chứng dương: `createOrder` (đã đọc đường) **đi qua được** |
| **4c** | Tầng 3 Chromium: **tự chạy** `thu_giao_dien/chay.sh`, báo **số thật** (passed / skipped / exit code) | **ĐÃ CHẠY — KHÔNG ĐO ĐƯỢC** | §3b.1 |

### 3b.1 Tầng 3 Chromium — SỐ THẬT

```sh
sh thu_giao_dien/chay.sh ; echo "EXIT=$?"
```

| Chỉ số | Số thật |
|---|---|
| **Mã thoát** | **1** |
| **passed** | **0** |
| **failed** | **4** |
| **did not run / skipped** | **23** |
| Tổng phép đo trong bộ | 27 (khớp con số *"26 đạt · 1 bỏ qua"* của 15/10) |
| Nguyên nhân | `browserType.launch: Executable doesn't exist at /…/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell` — **thiếu nhị phân Chromium** |
| Tái lập | chạy **2 lần** độc lập, **cả hai exit 1**, cùng thông điệp |

⇒ Đây là **CHƯA ĐO** (lỗ hổng phạm vi), **KHÔNG** phải "4 ca hỏng của sản phẩm": bốn ca "failed" là
bốn lượt `browserType.launch` không mở nổi trình duyệt. Báo thô `4 failed` mà không nói lý do là kết
luận SAI theo hướng nói xấu sản phẩm; báo "tầng 3: CÓ" như dòng của bộ chạy là SAI theo hướng nói
tốt. Cả hai hướng đều bị chặn ở đây — xem `N-G17-02`.

### 3b.2 Định dạng bằng chứng (theo yêu cầu)

Mọi kết quả trong tài liệu này kèm: **LỆNH** (khối `sh` ngay trên bảng) · **MÃ THOÁT** (lấy **ngay
sau** lệnh, không qua ống — các lượt A/B/C/D/E dùng `>> log 2>&1` rồi `echo "EXIT=$?"`, không `| head`)
· **SHA** (`git rev-parse HEAD` + vân tay cây §1.0) · **SỐ CA** · **SỐ BỎ QUA**. Bộ thử AG-01 G17:
**53 ca · 0 bỏ qua** (`OK`, không có dòng `skipped`).

---

## 4. PHÁT HIỆN

| Mã | Mức | Nội dung | Bằng chứng đo được |
|---|---|---|---|
| **`N-G17-00`** | **HIGH (vận hành)** | **Biến môi trường `GIT_CONFIG_*` hỏng làm nền đóng băng ĐỎ cổng hồi quy mặc định.** `GIT_CONFIG_COUNT=2` nhưng `GIT_CONFIG_KEY_0`/`GIT_CONFIG_KEY_1` **RỖNG** ⇒ mọi lệnh `git` thoát **128** (`error: missing config key GIT_CONFIG_KEY_0` / `fatal: unable to parse command-line config`). Ba ca kiểm có gọi git trong `thu_bao_mat.py` + `thu_tich_hop.py` vì thế hỏng. | Lượt A **exit 1** (2 bộ ✗, 1284 ca) vs Lượt B **exit 0** (36/36 ✓, 1284 ca) — **cùng cây, cùng HEAD, cùng số ca**; và cặp lệnh A/B ở §1.2. Không phải lỗi mã sản phẩm. |
| **`N-G17-01`** | **LOW** | **Quyền MA**: `app/server.py:1187` gọi `self._can(nc, "tenant.billing.quan_ly" …)` nhưng `tenant.billing.quan_ly` **không có** trong `quyen.QUYEN`. | `quyen.co_quyen(role, "tenant.billing.quan_ly")` = **False cho MỌI vai trò** (6/6) ⇒ nhánh đầu là mã chết. Cửa `/api/v2/dang-ky/doi-goi` **vẫn mở** bằng quyền nền: VIEWER **403**, OWNER **200** ⇒ không phải cửa chết, không phải lỗ hổng — nhưng là **độ lệch danh mục quyền**. Có mục trong `PHAT_HIEN_DA_BIET` + ca `C8` tự ĐỎ nếu mục này hết đúng. |
| **`N-G17-02`** | **MEDIUM (bộ đo tự nói sai)** | **Phép kiểm sẵn sàng của tầng 3 là phép kiểm THAY THẾ.** `chay_tat_ca.sh` chỉ hỏi `[ -d node_modules/@playwright ]` rồi in *"tầng 3 (DOM/CSS trong Chromium thật): **CÓ**, nhưng KHÔNG chạy ở đây"*. Thực đo: gói JS **có**, **nhị phân Chromium KHÔNG có**. | `sh thu_giao_dien/chay.sh` → **exit 1**, **passed 0 · failed 4 · did not run 23** (tổng 27), lỗi: `browserType.launch: Executable doesn't exist at …/node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell`. Chạy **hai lần**, cả hai exit 1. Con số *"26 đạt · 1 bỏ qua (15/10/2026)"* **không tái lập được** trong worktree này. |
| **`N-G17-03`** | **LOW (tài liệu)** | `docs/G16_ACCEPTANCE.md` §8.7 khai *"`integration/g16` chưa gộp `main`"*. Đo được: **`main` đã nằm TRỌN trong nền** (`HEAD..main = 0` commit). | `git rev-list --count HEAD..main` = **0**; `main..HEAD` = **17**; `merge-base --is-ancestor main HEAD` → **exit 0**. (Có thể ý tác giả là "chưa gộp thêm lần nào kể từ điểm rẽ" — nhưng câu chữ đang nói điều ngược lại.) |
| **`N-G17-04`** | **INFO (phạm vi)** | **Nền được ghim `98baeb3` KHÔNG phải đầu nhánh `integration/g16`.** | `git rev-parse integration/g16` = `c16afef`; `HEAD..integration/g16` = **1** commit (`AG-00: ke hoach local G16 -> G25 (DE XUAT…)`, chỉ thêm `docs/G16_G25_LOCAL_PLAN.md`, `+122` dòng, không đụng mã). Mọi số đo ở đây có hiệu lực cho **`98baeb3`**, không phải cho `c16afef`. |

**Ghi chú thêm (không phải phát hiện, nhưng phải nói):** đề bài ghi lệnh được phép chạy là
`python3 app/thu/chay_tat_ca.sh`. Đo thẳng: đó là **script POSIX `sh`** (`#!/bin/sh`), nên
`python3` trên nó thoát **1** với `SyntaxError: invalid syntax` (ca `G2`). Mọi lượt chạy trong tài
liệu này dùng **`sh app/thu/chay_tat_ca.sh`** — và ca `G2` còn kiểm `sh -n` để chứng minh tệp **hợp
lệ** với đúng trình thông dịch của nó.

---

## 5. CHƯA ĐO — LỖ HỔNG PHẠM VI, KHÔNG PHẢI ĐẠT

1. **Gọi hãng thật, kể cả sandbox · TLS thật tới `*.jtexpress.vn`** — `V-G09-01` + `V-13906-05`
   **CHƯA CẤP**. Không thử lấy một byte nào (đo được: **0** lượt `connect` ra ngoài loopback).
2. **`cancelOrder` / `getShippingFee` / `getShippingLabel` / `getOrder` đầu-cuối** — đường dẫn
   **CHƯA ĐỌC ĐƯỢC** (`duong=None`); tôi chỉ đo được rằng hệ **DỪNG ĐÚNG** (`E4`/`E5`/`E6`),
   **không** đo được hành vi thật của hãng.
3. **Harness SANDBOX của AG-04 (`trien_khai/g16/**`)** — **không** dựng phép đo độc lập; đây vẫn là
   mục *"AG-01 chưa nghiệm thu"* y như `G16_ACCEPTANCE.md` §8.5.
4. **Tầng 3 (DOM/CSS trong Chromium)** — **KHÔNG ĐO ĐƯỢC** trong worktree này: thiếu nhị phân
   Chromium (`N-G17-02`). Con số 26/1 của ngày 15/10 **chưa được tái lập**.
5. **Đa tiến trình / đa luồng thật** — `app/thu/dong_thoi/chay.py` (8 tiến trình × 400 phép) và
   `thu_http_jt.py` **không** do tôi chạy trong lượt này; mọi phép đo HTTP của tôi là **trong tiến
   trình** + máy chủ cổng động.
6. **Mọi cặp `(cửa × POST/PUT/DELETE)`** — tôi quét **mọi cửa GET** và 4 phép ghi/xoá có chủ đích;
   phần còn lại của ma trận ghi **chưa** quét hết.
7. **`/api/v2/platform/*`** — cố ý **nằm ngoài** phép quét chéo tenant (đó là mặt phẳng nền tảng,
   không phải mặt phẳng tenant). V5 ở đây **không** nói gì về cách ly giữa các platform admin.
8. **Hai tầng frontend (56 + 36 ca)** — do **bộ chạy chung** chạy và xanh, nhưng tôi **không** dựng
   phép đo độc lập cho chúng trong lượt này.
9. **V11 PostgreSQL** — tôi chỉ xác nhận **CSDL nghiệp vụ vẫn SQLite** (`A7`) và **không** import
   driver CSDL khác trong `app/*.py`; **không** chạy lại cụm PostgreSQL 55432, **không** đối chiếu DDL.
10. **Ngoài phạm vi theo thiết kế:** deploy · push · HTTPS thật · tunnel · VPS · chuyển CSDL nghiệp
    vụ sang PostgreSQL (D-8) · credentials hãng thật · AI/LLM thật · dữ liệu lớn · Safari/Firefox.
11. **Chưa có người đọc lại.** Toàn bộ là tác tử AI; tài liệu này **không** thay thế người nghiệm thu.

**Và một điều tôi CỐ Ý không làm:** tôi **không** sửa một dòng nào trong mã sản phẩm, kể cả
`N-G17-01` (một dòng trong `quyen.py` là đủ) — AG-01 **không** viết mã sản phẩm, và một bản vá do
người kiểm viết ra thì chính người kiểm không còn đo được nó một cách độc lập nữa.

---

## 6. CHẠY LẠI — ba lệnh

```sh
cd <worktree g17-ag01-qa>
export GIT_CONFIG_COUNT=0                        # N-G17-00; thiếu dòng này thì 2 bộ thử sẽ đỏ GIẢ

# 1) bộ thử độc lập của AG-01 (49 ca, ~7 giây)
VIP_G17_HEAD=98baeb357214d41a9380467fde2fee2b94fd31cc python3 app/thu/thu_qa_g17.py

# 2) hồi quy toàn phần trên nền đóng băng
rm -rf /tmp/veh_g17_ag01_qa_base && mkdir -p /tmp/veh_g17_ag01_qa_base
VIP_HUB_DATA=/tmp/veh_g17_ag01_qa_base sh app/thu/chay_tat_ca.sh

# 3) vân tay cây — phải khớp §1.0 khi miễn trừ đúng hai tệp AG-01
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

---

## 7. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY

- Mọi số đo thuộc **`98baeb3`** và **chỉ** `98baeb3`; `integration/g16` đã đi thêm 1 commit
  (`N-G17-04`). Cây nào khác thì phải đo lại.
- Bộ thử của tôi **tự dựng CSDL riêng** bằng `csdl.mo()` + `migrate.chay()` (đúng đường của
  `chay_e2e.sh`), trong thư mục tạm. Nó **không** đo trên `app/du-lieu/` và **không** đo trên dữ
  liệu thật.
- `M1`–`M4` chứng minh **cổng có răng**, không chứng minh mã sản phẩm đúng ở mọi ngả khác.
- Hai tệp AG-01 G17 là tệp **MỚI, chưa `git add`**; cổng "cây sạch" của bộ thử **miễn trừ đúng hai
  đường dẫn đó** và không miễn trừ gì khác (`TEP_CUA_AG01_G17`).
- **SHA256 `app/thu/thu_qa_g17.py` (cuối cùng): `7a920e8ab84173e78087d0a34dff170ce7611d845dc2d0f4d90fff2166fd1bb5`.
  *(Băm của **chính tài liệu này** không thể nằm trong chính nó — nó được ghi ở báo cáo `worker_done` gửi AG-00.)*
- Lượt tầng 3 có sinh tệp **ngoài git** trong `thu_giao_dien/_ket-qua/` và `thu_giao_dien/_bao-cao/`
  (hai thư mục đã có trong `.gitignore`, sinh lại được bằng `sh thu_giao_dien/chay.sh`); `git status`
  sau đó **không** thấy gì ngoài hai tệp AG-01.
