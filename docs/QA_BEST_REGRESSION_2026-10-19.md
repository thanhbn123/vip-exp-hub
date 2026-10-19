# Hồi quy BEST trên base `c04c619` — QA/QV (19/10/2026)

## 0. Kết luận trong phạm vi đã đo

**Chạy đủ bộ tổng hợp trên base `c04c619`: exit 1. KHÔNG full green.**

- Python: **kế hoạch 2843 ca · 2807 ca có kết quả · 32 bỏ qua · 4 chưa chạy (did-not-run) ·
  0 không kết luận**; dò **87/87 bộ**, cả 87 bộ có ca chạy, **13 bộ Python đỏ**.
- Frontend tầng 1: **56/56 đạt**. Tầng 2 (`thu_frontend/thu_http.py`): **39/40 đạt, 1 hỏng**
  ⇒ tầng 2 đỏ.
- E2E qua HTTP thật (`app/thu/chay_e2e.sh`): **41/41 phép đo đạt**.
- Giao diện Chromium (`sh thu_giao_dien/chay.sh`): **75 đạt · 1 hỏng · 4 chưa chạy**, exit 1.
- Tổng số mục đỏ của lượt này: **13 bộ Python + 1 bộ frontend tầng 2** (bộ tổng hợp báo
  `hỏng 13`, cộng `thu_http.py` thành 14 dòng đỏ), **+ 1 ca Playwright hỏng và 4 ca chưa chạy**
  ở tầng giao diện.

**Lỗi sản phẩm thật tái hiện được:** `thu_g21_saoluu.py` — khôi phục bản sao lưu có schema
**thấp hơn** (v6 đè lên v9) **không fail-closed**: hệ vẫn chạy `rc=0` trên schema cũ, không một
lời cảnh báo (`test_a5`, `test_c4`). Đây là đỏ **có sẵn**, không phải do BEST, nhưng vẫn là lỗi
cần sửa, không được hạ kỳ vọng của test.

**Đỏ mới do thay đổi BEST (theo danh sách đỏ baseline `cced0f5` + diff mã):** `thu_g17_baomat`,
`thu_qa2_soat`, `thu_r2_hopdong`, `thu_qv_kiemchung`, `thu_r3_ghim`,
`thu_frontend/thu_http.py`; ngoài bộ tổng hợp còn **ca `10_trang_tinh_du_lieu.spec.js:144`**
(Playwright) đỏ vì `pages/best.html` chưa được khai. Phần lớn là **kỳ vọng cũ/bộ thử chưa cập
nhật theo trang & route mới của BEST**, không phải lỗi runtime đã chứng minh — trừ lỗi S5 của
G21 nêu trên.

**Không sửa một dòng mã sản phẩm hay test nào.** Báo cáo này là tệp duy nhất được tạo/commit.

## 1. Mốc đo, môi trường, lệnh chạy

| Mục | Giá trị |
|---|---|
| Worktree | `/Users/viporder/orca/workspaces/vip-express-hub/ag07` |
| HEAD khi đo | `c04c6191f077a6225d54733cabde7e813b0bb886` |
| Vân tay trước/sau | Git là chính: `diff HEAD=0`, `status --porcelain -uall=0`; vân tay **KHÔNG ĐỔI** |
| Hệ điều hành | Darwin arm64 |
| Python / SQLite | 3.9.6 / 3.51.0 |
| Node / Playwright | v26.7.0 / 1.56.1 |
| Chromium | headless_shell 141.0.7390.37, SHA-256 `a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040` (KHỚP ghim) |

Lệnh đã chạy:

```sh
VIP_KHO_DANG_CHAY=sqlite sh app/thu/chay_tat_ca.sh        # log: /tmp/ag07_qa/full_run.log
sh thu_giao_dien/chay.sh                                  # log: /tmp/ag07_qa/ui_run.log
```

Từng bộ đỏ được chạy lại riêng để lấy log đầy đủ:
`VIP_KHO_DANG_CHAY=sqlite python3 app/thu/<bộ>.py` → `/tmp/ag07_qa/red_<bộ>.log`.
Không gọi hãng, không dùng credential thật, không push/deploy, không mở adapter LIVE
(`2 hãng đăng ký: jt, vtp; KHÔNG hãng nào mở live`).

**Giới hạn phạm vi:** SQLite tại thư mục tạm · máy chủ bind `127.0.0.1` · adapter MOCK ·
PostgreSQL chỉ là cụm tạm/schema thử, không phải CSDL nghiệp vụ · VPS/triển khai, hãng thật,
credential thật, AI thật, dữ liệu lớn, Safari/Firefox **ngoài phạm vi** · giao diện chỉ Chromium
ở 375/768/1280.

## 2. Số đo tổng hợp

| Hạng mục | Kế hoạch | Có kết quả | Bỏ qua | Chưa chạy | Đỏ |
|---|---:|---:|---:|---:|---:|
| Python (unittest/viết tay) | 2843 | 2807 | 32 | 4 | **13 bộ** |
| Frontend tầng 1 (node) | 56 | 56 | 0 | 0 | 0 |
| Frontend tầng 2 (`thu_http.py`) | 40 | 39 | 0 | 0 | **1 ca** |
| E2E shell (`chay_e2e.sh`) | 41 | 41 | 0 | 0 | 0 |
| Giao diện Chromium (Playwright) | 80 | 75 | 0 | 4 | **1 ca** |

Bộ tổng hợp in: `python: KẾ HOẠCH 2843 ca · CÓ KẾT QUẢ 2807 ca (bỏ qua 32 · chưa chạy 4 ·
không kết luận 0)`; `bộ: dò 87/87 · có ca chạy 87 · hỏng 13`; `E2E: 41/41`;
`bộ hỏng: thu_g17_baomat.py thu_g19_route.py thu_g21_saoluu.py thu_g22_e2e.py
thu_g22_phanloai.py thu_g22_zeroca.py thu_qa_g18.py thu_qa_g20.py thu_qa_g22.py
thu_qa2_soat.py thu_qv_kiemchung.py thu_r2_hopdong.py thu_r3_ghim.py thu_http.py`.

## 3. Danh sách đỏ và phân loại

| # | Bộ | Exit | Kế hoạch/có KQ | Phân loại | Bằng chứng chính | Mới / có sẵn |
|---:|---|---:|---:|---|---|---|
| 1 | `thu_g17_baomat.py` | 1 | 31/31 | **Kỳ vọng cũ — thiếu khai route** | `FAIL test_v1_bang_cua_phu_moi_route_trong_server`: **20 route BEST** có trong `server.py` nhưng không có trong bảng cửa; gồm 7 nhánh thao tác, `hop-dong`, `trang-thai`, `kiem-ket-noi`, `webhook-bearer`, `lich-su`, và nhánh `duong in (...)` | **MỚI (BEST)** |
| 2 | `thu_g19_route.py` | 1 | 50/50 | **Lỗi bộ thử + kỳ vọng cũ** | `a6`, `d1`: `SystemExit: 3` khi `thu_qa_g18.py` import, vì `g19_route` import `cau_hinh` **trước** khi đặt `VIP_HUB_DATA` ⇒ chốt an toàn thấy `app/du-lieu`; `a8`: `8 != 30` cặp lệch cấp phương thức do route BEST mới. Output: `[C2] đã đo đủ 32 MỤC` | **CÓ SẴN** + lỗi `a8` mới do BEST |
| 3 | `thu_g21_saoluu.py` | 1 | 23/23 | **LỖI CODE/NGHIỆP VỤ THẬT** | `FAIL test_a5...`: `S5 KHÔNG fail-closed: (c) sau khi tụt schema, hệ VẪN CHẠY được (rc=0) trên schema cũ — không một lời cảnh báo`; `test_c4` lặp cùng lỗi | **CÓ SẴN** |
| 4 | `thu_g22_e2e.py` | 1 | 80/76 (4 chưa chạy) | **Kỳ vọng cũ + cascade UI** | Cổng in `75/1/0/4`; `ghim ĐẠT = 65` trong khi lượt này 75 (BEST thêm 10 ca spec). 1 ca hỏng là `10_trang_tinh_du_lieu.spec.js:144` (`best` chưa khai); 4 ca sau đó did-not-run | **CÓ SẴN** (nguyên nhân hiện tại do BEST) |
| 5 | `thu_g22_phanloai.py` | 1 | 6/6 | **Kỳ vọng cũ** | `test_03`: `0 == 0 : bản sạch KHÔNG đỏ — phép đo mất răng` (mô hình phân loại của chính nó đã cũ) | **CÓ SẴN** |
| 6 | `thu_g22_zeroca.py` | 1 | 17/17 | **Kỳ vọng cũ** | `test_14`: `17 != 0 : chưa khai kho mà vẫn chạy được ca nào?` — các bộ đã được vá tự khai kho, kỳ vọng "0 ca" không còn đúng | **CÓ SẴN** |
| 7 | `thu_qa_g18.py` | 1 | 47/46 (1 skip) | **Cascade + flaky tầng UI** | `b1`: tầng 3 exit 1; log lồng `74 đạt · 2 hỏng · 4 bỏ qua` — 1 hỏng do `best` chưa khai, 1 hỏng `best_express:03` chờ `#auth` quá 5 giây; `g2`: tầng 2 exit 1 do `best-uat.html` thiếu `assets/js/app.js` | **CÓ SẴN** (nguyên nhân hiện tại do BEST) |
| 8 | `thu_qa_g20.py` | 1 | 21/18 (3 skip) | **Tự kiểm/kỳ vọng cũ** | `FAIL: test_t1_luat_phan_tu_choi_bon_kieu_xanh_gia`, `test_t2_tu_kiem_bang_TIEN_TRINH_CON`, `test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong` (log riêng chưa lấy xong khi dừng theo chỉ đạo) | **CÓ SẴN** |
| 9 | `thu_qa_g22.py` | 1 | 24/23 (1 skip) | **Cascade/tự kiểm** | `FAIL: test_b2_chay_e2e_toan_bo_that`, `test_d1_nam_cong_g20`, `test_t1...`, `test_t2...`, `test_z1...`; b2 chạy đúng `thu_giao_dien/chay.sh` nên dính ca UI ở mục 4/13 | **CÓ SẴN** (b2 do BEST) |
| 10 | `thu_qa2_soat.py` | 1 | 49/48 (1 skip) | **Kỳ vọng cũ — bộ quét tĩnh** | `test_r41`: chỉ kêu đúng nhánh `duong in ("/api/v2/best/bao-gia", "/api/v2/best/tao-don", ...)`. Nhánh này gọi `_best_thao_tac`, và `app/server.py:488` có `self._can(nc, "tenant.hang.quan_ly")` — **không chứng minh được bypass quyền**; đây là giới hạn quét văn bản đã ghi trong docstring | **MỚI (BEST)** |
| 11 | `thu_qv_kiemchung.py` | 1 | 17/17 | **Kỳ vọng cũ/cascade** | 3 FAIL của chính nó: `test_02` đòi `thu_g19_route` exit 0 (thực tế 1); `test_08` đòi `thu_tich_hop` exit 1 (thực tế 0); `test_09` đòi `thu_r2_hopdong` exit 0 (thực tế 1) | **MỚI (BEST)** |
| 12 | `thu_r2_hopdong.py` | 1 | 12/12 | **Kỳ vọng cũ/hợp đồng** | `test_04`: `0 != 1 : R7 phải còn ĐỎ; không được nới cổng để xanh`; bảng in `thu_tich_hop | 0 | 12 | 0 | 0`. BEST đã sửa `duoc_phep` trong `thu_tich_hop.py` để cho 4 lớp HTTP BEST | **MỚI (BEST)** |
| 13 | `thu_r3_ghim.py` | 1 | 9/9 | **Kỳ vọng cũ — trang mới** | `FAIL test_06... (trang='best-uat.html')`: `'assets/js/app.js' not found`; `test_09` là đối chứng dương chạy lại ca trang demo nên đỏ theo | **MỚI (BEST)** |
| 14 | `thu_frontend/thu_http.py` | 1 | 40/39 | **Kỳ vọng cũ — trang mới** | `FAIL test_04_moi_trang_demo_g00_khong_bi_pha`: `'assets/js/app.js' not found ... : best-uat.html`. Trang chỉ nạp `../admin/best_uat.js` | **MỚI (BEST)** |

Ngoài bộ tổng hợp:

| # | Ca Playwright | Phân loại | Bằng chứng | Mới / có sẵn |
|---:|---|---|---|---|
| 15 | `10_trang_tinh_du_lieu.spec.js:144` (01) | **Kỳ vọng cũ — thiếu khai trang** | `la = ["best"]`: `pages/best.html` có trên đĩa nhưng không có trong bảng `TRANG` của spec; ca này hỏng kéo 4 ca sau thành **did-not-run** (75 đạt/1 hỏng/4 chưa chạy) | **MỚI (BEST)** |

## 4. Đỏ mới do BEST — giải thích nguyên nhân gốc

### 4.1. Route BEST chưa được khai ở G17 (mục 1)

`app/server.py` thêm 20 route BEST (7 thao tác thật dùng chung `_best_thao_tac`, cùng
`hop-dong`, `trang-thai`, `kiem-ket-noi`, `webhook-bearer`, `lich-su`). Bảng cửa của
`thu_g17_baomat.py` chưa khai, nên ca canh KHAI BÁO đỏ. **Đây là lỗ hổng phủ sóng của bộ thử**:
các route này chưa đi qua lưới HTTP đối chứng A/B của G17. Không chứng minh được bypass runtime;
muốn kết luận an toàn phải khai bảng cửa và chạy lại G17.

### 4.2. Quét tĩnh G19 route lệch vì nhánh gộp nhiều route (mục 2, 11)

BEST thêm nhánh `if duong in (7 route thao tác) ...: return self._best_thao_tac(...)`. Bộ trích
của G19 đếm thêm cặp phương thức, nên `test_a8` đòi 8 cặp lệch nhưng đo **30**. Hai lỗi `a6/d1`
lại do **thứ tự import**: `thu_g19_route.py` import `cau_hinh` trước khi đặt `VIP_HUB_DATA`;
`_ag01_route()` import `thu_qa_g18.py`, chốt an toàn của QA G18 thấy `app/du-lieu` và
`raise SystemExit(3)`. Đây là lỗi bộ thử độc lập với BEST, nhưng làm G19 không đo được phần phủ.

### 4.3. Hợp đồng phân tầng HTTP bị nới trong test (mục 11, 12)

BEST sửa `app/thu/thu_tich_hop.py`: `duoc_phep = {"http_jt.py", "http_best.py",
"xac_thuc_best.py", "best_hop_dong.py"}`. Nhờ đó `thu_tich_hop` từ exit 1 (một FAIL `test_09`)
chuyển **exit 0, 12/12**. R2 và QV là hai cổng canh đúng trạng thái cũ "R7 còn ĐỎ", nên đỏ.
**Đây là thay đổi hợp đồng có chủ ý, không phải lỗi runtime** — nhưng phải được Owner/chủ hợp
đồng chốt lại (R2/QV phải được cập nhật theo quyết định, không được chỉ "làm xanh" im lặng).
Báo cáo giữ nguyên sự thật: **một cổng an toàn đã được nới trong chính tệp test BEST**.

### 4.4. Trang `best-uat.html` không nạp `assets/js/app.js` (mục 7, 13, 14)

Trang mới `pages/best-uat.html` chỉ nạp `../assets/css/style.css` và
`../admin/best_uat.js`, không nạp `assets/js/app.js`. Ba nơi đang canh bất biến "mọi trang demo
nạp chung CSS/JS" cùng đỏ: `thu_frontend/thu_http.py`, `thu_r3_ghim.py`, và con `g2` của
`thu_qa_g18.py`. **Không phải lỗi bảo mật đã chứng minh**; là xung đột giữa quy ước trang demo
và trang nghiệm thu độc lập. Cần hoặc thêm `app.js` (nếu an toàn) hoặc khai miễn trừ tường minh
cho trang này — không được lặng lẽ bỏ ca.

### 4.5. `pages/best.html` chưa khai trong `TRANG` (mục 4, 15)

`10_trang_tinh_du_lieu.spec.js` khai `best-uat` nhưng thiếu `best`, trong khi `pages/best.html`
có trên đĩa. Ca 01 đỏ, 4 ca sau did-not-run. Đây cũng là ca hỏng duy nhất trong lượt
`sh thu_giao_dien/chay.sh` độc lập và là ca hỏng của `thu_g22_e2e`. Cần khai `best` và chạy lại
các ca dữ liệu tĩnh cho trang này.

### 4.6. Ghim số ca UI không còn đúng (mục 4)

`thu_g22_e2e.py` ghim `ĐẠT = 65`; BEST thêm spec `best_express` (10 ca) làm lượt đo 75 đạt.
Kể cả khi ca `best` được khai và tất cả xanh, ghim 65 vẫn làm cổng đỏ. Phải cập nhật ghim theo
số ca **do `--list` công bố**, không hạ mẫu số.

## 5. Đỏ có sẵn, không do BEST

- **`thu_g21_saoluu.py` (mục 3) — lỗi sản phẩm thật:** S5 khôi phục bản schema thấp hơn lên bản
  cao hơn không bị từ chối; exit 0 và không cảnh báo. `test_c4` chạy cùng kịch bản trên bản vá
  cũng lặp lại. **Không sửa test; cần vá `migrate`/khôi phục fail-closed và giữ ca đỏ tới khi vá.**
- **`thu_g22_phanloai.py` (mục 5):** bộ tự phân loại 20 bộ đỏ theo mô hình cũ; bản sạch của nó
  nay exit 0 nên `test_03` mất răng. Là kỳ vọng của công cụ QA, không phải sản phẩm.
- **`thu_g22_zeroca.py` (mục 6):** kỳ vọng "thiếu khai kho ⇒ 0 ca" đã bị các bản vá tự khai kho
  (R1/R3) làm hết đúng; `thu_giao_dich` chạy 17 ca ngay cả khi không đặt biến.
- **`thu_qa_g20.py` / `thu_qa_g22.py` (mục 8, 9):** các ca tự kiểm (`t1`, `t2`, `z1`) và bản đồ
  G20 (`d1`) là tầng kiểm tra của chính QA, không đo sản phẩm; `b2` của QA G22 chạy lại toàn bộ
  Playwright nên đỏ theo ca UI. Log riêng từng ca của hai bộ này chưa lấy xong khi dừng theo
  chỉ đạo — **không kết luận chúng là lỗi sản phẩm**.
- **`thu_g19_route.py` (mục 2):** đã đỏ trong baseline; hai lỗi `a6/d1` là lỗi thứ tự import
  của chính bộ thử; `a8` là vế mới do BEST.
- **`thu_qa_g18.py` (mục 7):** đã đỏ trong baseline, nhưng nguyên nhân hiện tại **không còn là
  Chromium bị chặn** (Chromium chạy được, SHA khớp ghim). Nguyên nhân hiện tại là ca UI `best`
  + trang `best-uat` + một ca auth không ổn định (xem §6).

## 6. Mục không ổn định (flaky) đã quan sát

Cùng một bộ `best_express.spec.js:219` (ca 03 — credential/password, không lộ secret):

- Lượt `sh thu_giao_dien/chay.sh` độc lập lúc 21:15: **ĐẠT** (75 đạt/1 hỏng/4 chưa chạy; ca hỏng
  là `10_trang_tinh_du_lieu`).
- Lượt lồng trong `thu_qa_g18.py` lúc 21:27: **HỎNG** — `#auth` vẫn là
  `"Đang kiểm tra phiên đăng nhập…"` sau 5 giây, timeout 30 giây; log
  `/var/folders/.../veh_g18_ag01_qa_log/tang3.log`.

Vì vậy lượt lồng cho `74 đạt · 2 hỏng · 4 bỏ qua`, còn lượt độc lập cho `75 · 1 · 4`. Đây là
**không ổn định của phép đo tầng UI**, cần chạy lặp và/hoặc tăng chờ có kiểm soát trước khi coi
là lỗi sản phẩm. Báo cáo không giấu khác biệt này.

## 7. Đối chiếu "mới do BEST" và "có sẵn"

Baseline tham chiếu: `docs/BEST_EXPRESS_HTTP_E2E.md` §7 (lượt `cced0f5`, `VIP_KHO_DANG_CHAY=sqlite`):
**exit 1 · 2711 kế hoạch · 2675 có kết quả · 36 skip · 12 bộ đỏ**, danh sách:

```text
thu_g19_route.py thu_g20_hop_dong.py thu_g21_saoluu.py thu_g22_e2e.py
thu_g22_phanloai.py thu_g22_zeroca.py thu_qa_g18.py thu_qa_g20.py
thu_qa_g21.py thu_qa_g22.py thu_tich_hop.py thu_webhook_jt.py
```

| Nhóm | Bộ | Ghi chú |
|---|---|---|
| **12 bộ đỏ baseline nay còn đỏ (8)** | `thu_g19_route`, `thu_g21_saoluu`, `thu_g22_e2e`, `thu_g22_phanloai`, `thu_g22_zeroca`, `thu_qa_g18`, `thu_qa_g20`, `thu_qa_g22` | G19/G22 E2E/QA G18 có thêm nguyên nhân mới do BEST; G21 vẫn là lỗi thật; G22 phân loại/zero-ca/QA G20/G22 là kỳ vọng cũ |
| **12 bộ đỏ baseline nay XANH (4)** | `thu_g20_hop_dong` (36/36), `thu_qa_g21` (24 ca/21 KQ), `thu_tich_hop` (12/12), `thu_webhook_jt` (99/99) | `thu_webhook_jt` baseline đỏ do artefact checkout `/tmp`; trên workspace thật xanh |
| **Đỏ MỚI không có trong baseline (6)** | `thu_g17_baomat`, `thu_qa2_soat`, `thu_qv_kiemchung`, `thu_r2_hopdong`, `thu_r3_ghim`, `thu_frontend/thu_http.py` | Tất cả đều truy được về route/trang/allowlist do BEST thêm; chi tiết §4 |
| **Playwright mới đỏ ngoài bộ tổng hợp (1 ca)** | `10_trang_tinh_du_lieu.spec.js:144` | Do `pages/best.html` chưa khai; kéo 4 ca did-not-run |

**Độ tin cậy của nhãn mới/có sẵn:** đối chiếu danh sách đỏ baseline đã công bố, cộng diff mã
`cced0f5..c04c619` và log từng bộ. Không chạy lại toàn bộ baseline `cced0f5` trong lượt này
(dừng điều tra theo chỉ đạo), nên nhãn "mới" là **suy ra từ baseline + thay đổi mã**, không phải
phép đo song song hai mốc. Các kết luận lỗi sản phẩm chỉ nêu khi log chỉ đích danh hành vi sản
phẩm (S5).

## 8. Việc còn lại (không thực hiện trong lượt này)

1. Khai 20 route BEST vào bảng cửa G17 rồi chạy lại lưới A/B; không tắt ca canh.
2. Chốt hợp đồng phân tầng HTTP BEST: cập nhật R2/QV theo quyết định có chủ đích, hoặc giữ
   `thu_tich_hop` đỏ; không lặng lẽ nới cổng.
3. Khai `best` vào `TRANG` của `10_trang_tinh_du_lieu.spec.js`; quyết định `best-uat.html` nạp
   `assets/js/app.js` hay được miễn trừ tường minh trong F05/R3/QA G18.
4. Cập nhật ghim số ca UI của `thu_g22_e2e` theo `playwright --list`, không hạ mẫu số.
5. Sửa thứ tự import `VIP_HUB_DATA` trong `thu_g19_route.py`; cập nhật `MUC_CON_THIEU`/`a8`
   theo 20 route BEST bằng bằng chứng, không ghim số mới.
6. **Vá lỗi thật S5:** khôi phục schema thấp hơn phải fail-closed và cảnh báo; giữ
   `thu_g21_saoluu` đỏ tới khi vá xong. Không sửa `test_a5`/`test_c4` để xanh.
7. Chạy lặp ca UI auth `best_express:03` để xác định flaky hay lỗi thật.

## 9. Phụ lục — log và số đo thô

| Tệp log | Nội dung |
|---|---|
| `/tmp/ag07_qa/full_run.log` | Toàn bộ bộ tổng hợp, bảng tổng kết, vân tay trước/sau |
| `/tmp/ag07_qa/ui_run.log` | Playwright độc lập: 75 đạt/1 hỏng/4 chưa chạy |
| `/tmp/ag07_qa/red_thu_g17_baomat.log` | 20 route BEST thiếu khai |
| `/tmp/ag07_qa/red_thu_g19_route.log` | `SystemExit: 3`, `8 != 30` |
| `/tmp/ag07_qa/red_thu_g21_saoluu.log` | S5 fail-closed, `test_c4` |
| `/tmp/ag07_qa/red_thu_g22_e2e.log` | `75/1/0/4`, ghim 65 |
| `/tmp/ag07_qa/red_thu_g22_phanloai.log` | `bản sạch KHÔNG đỏ` |
| `/tmp/ag07_qa/red_thu_g22_zeroca.log` | `17 != 0` |
| `/tmp/ag07_qa/red_thu_qa_g18.log` | `b1`/`g2` đỏ, log lồng 74/2/4 |
| `/tmp/ag07_qa/red_thu_qa2_soat.log` | nhánh `duong in (...)` bị kêu |
| `/tmp/ag07_qa/red_thu_qv_kiemchung.log` | 3 FAIL `test_02/08/09` |
| `/tmp/ag07_qa/red_thu_r2_hopdong.log` | `R7 phải còn ĐỎ` |
| `/tmp/ag07_qa/red_thu_r3_ghim.log` | `best-uat.html` thiếu `app.js` |
| `/tmp/ag07_qa/red_thu_http.log` | cùng lỗi `best-uat.html` |
| `/var/folders/.../veh_g18_ag01_qa_log/tang3.log` | 2 ca Playwright hỏng khi chạy lồng |

**Không có mã sản phẩm, mã kiểm thử, hay tệp cấu hình nào bị sửa trong lượt này.**
Tệp báo cáo là thay đổi duy nhất được commit.
