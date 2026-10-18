# G20 · U2 — BỘ ĐO STALE: PHÂN LOẠI TRƯỚC, SỬA SAU

> **Vai:** U2 (worker được AG-00 dispatch) · task `task_619686f23c26` · dispatch `ctx_7573b4c771ca`.
> **Nền đo:** worktree `u2-g20-stale`, `HEAD = 2f4c3d1402c1222633207cfc483796c09f3df0f9`
> (bản clone độc lập của Codex đứng ở `b1c5205`; Phạm vi đo là **cây đã gộp** này).
> **Phạm vi ghi:** `app/thu/thu_qa_g20.py` (sửa) · `docs/G20_MEASURE_FIX.md` (tệp này, mới).
> **KHÔNG sửa tệp của agent khác.** Không push · không deploy · không gọi API production ·
> không sửa CSDL thật · không ghi `.git` · không tự bấm duyệt sandbox · mọi HTTP chỉ `127.0.0.1`.
> **Lệnh nghiệm thu:** `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py`.
> **Nguyên tắc:** ca STALE thì viết lại theo **bất biến đúng**, **đọc tại chỗ**, **giữ đối chứng
> âm** (làm hành vi cũ trở lại thì ca PHẢI đỏ); ca lỗi thật thì KHÔNG sửa. Không xoá ca, không
> hạ ngưỡng, không ép PASS, không `skipTest` để né.

---

## 0. KẾT LUẬN MỘT MÀN HÌNH

**6/6 ca hỏng đều là STALE — không có lỗi thật nào của sản phẩm trong 6 ca này.**
Sau khi sửa: `0 failure`, `EXIT 0`.

| Lượt | `Ran` | PASS (= Ran − FAIL − SKIP) | FAIL | SKIP | EXIT |
|---|---|---|---|---|---|
| TRƯỚC — máy này (`2f4c3d1`) | 21 | **13** | **6** | 2 | **1** |
| TRƯỚC — Codex độc lập (clone `b1c5205`) | 21 | 12 | 6 | 3 | 1 |
| **SAU — máy này, `VIP_G20_CHE_DO=gop`** | **21** | **19** | **0** | **2** | **0** |

SKIP = 2 trên máy này: `H_HoiQuy.test_h1` (làn đầy đủ `VIP_G20_DAY_DU=1` đang TẮT) và
`T_TuKiem.test_z9` (mồi CÓ CHỦ ĐÍCH cho `T2`). Codex báo SKIP = 3; chênh 1 ca là ca phụ thuộc
môi trường — trên máy này `A4` CHẠY THẬT (`lsof` thấy cụm `:5432`), còn máy không có `lsof`/cụm
không nghe thì `A4` bỏ qua; một khả năng khác là `C2` bỏ qua khi phiên KHÔNG đặt
`GIT_CONFIG_COUNT`. `Z9`/`H1` là skip có chủ đích, không phải nợ; không ca nào bị `skipTest`
để né lỗi.

Số liệu dòng **SAU** lấy từ lượt `g20_final3`: `Ran 21 tests in 18.889s · OK (skipped=2) · EXIT 0`.
Tầng 3 đã chạy **8 lượt** trong cả quá trình: **7 xanh, 1 lượt ca `06 — TỰ KIỂM` đỏ** do chập
chờn của chính đặc tả (tệp của AG-06/G22, ngoài phạm vi U2) — B1 phán ĐỎ là ĐÚNG; xem §5.7.
Không thêm retry để ép xanh, không sửa đặc tả.

---

## 1. BẢNG PHÂN LOẠI — PHẦN QUAN TRỌNG NHẤT

| Ca | Đo được TRƯỚC (nguyên văn rút gọn) | Vì sao hỏng | Phân loại | Đã làm |
|---|---|---|---|---|
| **A5** (`test_g1_cong_cay_sach…`) | `AssertionError: g17 KHÔNG thấy tệp AG-01 G20 đang có trong cây bẩn: []` | Cổng "cây sạch" của G17/G18 đã chuyển sang **luật vùng** (`docs/` + `thu*`) từ G21, nên tệp hợp lệ KHÔNG còn làm cổng đỏ. Bản G20 vẫn ghim "0/2 cổng đỏ" + cơ chế miễn trừ theo **tên cứng** — tức ghim một khoản nợ đã đóng. | **STALE** (ghim hành vi cũ) | Viết lại thành "không thay đổi NGOÀI vùng wave": 2/2 cổng cũ XANH, 2 ca tự kiểm phạm vi XANH, luật vùng phải bắt được tệp sản phẩm. |
| **B1** (`test_b1_tang_3_ban_phim…`) | `0 not greater than 0` · log: `[migrate hỏng] … CHƯA KHAI kho đang chạy` | Hai lớp STALE: (a) `app/migrate.py` (G22) nay **từ chối** khi chưa khai kho, nên nền tầng 3 dựng bằng công thức cũ ra **0 ca**; (b) sổ ghim `(7,0,0)` trong khi đặc tả đã có thêm ca TỰ KIỂM `04b` ⇒ **8 ca**. | **STALE** (công thức dựng nền + ghim số ca) | Khai `VIP_KHO_DANG_CHAY=sqlite` cho thư mục TẠM cô lập; bỏ ghim số ca, canh bất biến "chạy TRỌN VẸN + xanh". Nền không dựng được là `self.fail`, KHÔNG skip. |
| **B2** (`test_b2_ca_04…`) | `log tầng 3 KHÔNG nhắc ca 04 ⇒ đặc tả đã đổi` | Chỉ là **hệ quả của B1**: B1 không chạy được nền nên log không có ca 04. | **STALE** (dây chuyền) | Giữ phép đọc lại log; không ghim nguyên văn tiêu đề ca, chỉ đòi log nhắc `04` + DÒNG ĐO số điểm dừng. |
| **C4** (`test_c4_route_truy_van…`) | `['app/server.py'] != []` tại `assertEqual(nhap, [])` | Dòng 702 ghim **trạng thái nền** "chưa tệp SẢN XUẤT nào import `truy_van`". Route đã đóng thật (`app/server.py` import + dùng `truy_van`) nên sản phẩm đúng lại bị bắt đỏ. `docs/G22_CONTRACT.md` §0ter đã ghi đây là họ H5/`L-G20-A` và yêu cầu chủ `thu_qa_g20.py` sửa. | **STALE** (ghim trạng thái nền) | Bỏ `assertEqual(nhap, [])`; cổng dùng cặp `(schema_ok, route_ok)`; thêm đối chứng âm/dương LÀM THẬT trên cây tạm; `(True, False)` phải ĐỎ ở `gop`. |
| **C1** (`test_c1_git_voi_moi_truong…`) | `'2f4c3d1…' != '148ecd3…'` tại `assertEqual(r2.stdout.strip(), HEAD_NEN)` | (a) Đối chứng dương **ghim HEAD = nền đóng băng 148ecd3**; HEAD đã nhích từ lâu ⇒ đỏ vì lý do giả. (b) `git` thô trả `128` vì **dị dạng `GIT_CONFIG_*` của PHIÊN** (`N-G18-00`: `GIT_CONFIG_COUNT=2` thiếu `KEY_0/1`) — nợ MÔI TRƯỜNG ngoài repo, không phải nợ sản phẩm; bản cũ biến nó thành ô "nền" nên `gop` đỏ vĩnh viễn. | **STALE** (ghim HEAD + ghim sự thật môi trường) | Đọc HEAD tại chỗ (40 hex + là hậu duệ `HEAD_NEN` bằng `merge-base --is-ancestor`); phân loại git thô theo chữ ký: `OK` / `N-G18-00` (in cảnh báo, chủ AG-00) / `LOI_KHAC` (ĐỎ). |
| **Z1** (`test_z1_moi_ca_phu_dinh…`) | `THIẾU ĐỐI CHỨNG DƯƠNG cho: ['cong-cay-sach', 'git-tho', 'truy-van-C6']` | Ba ca trên ném lỗi TRƯỚC khi kịp gọi `_dc_duong(...)` ⇒ sổ đối chứng chỉ còn vế âm. **Không phải lỗi của Z1.** | **STALE** (dây chuyền) | Sửa ba ca trên; mỗi ca vẫn có `_dc_am` + `_dc_duong`; Z1 tự bắt nhóm thiếu dương bằng dữ liệu tổng hợp. |

**Dây chuyền ngoài danh sách 6 ca (phải sửa để không tự tạo STALE mới):**

| Ca | Vì sao phải chạm | Phân loại |
|---|---|---|
| `Z2` (`test_z2_cay_khong_doi_ngoai_hai_tep_duoc_phep`) | Miễn trừ theo **đúng hai tên tệp** sẽ tự đỏ khi lượt này tạo `docs/G20_MEASURE_FIX.md` — đúng `N-G19-03`/`docs/G22_GIOIHAN.md` §6.2. | **STALE** — đổi sang luật vùng; thêm đối chứng âm tệp sản phẩm + đổi tên `app/server.py → docs/server.py`. |
| `T4` (`test_t4_gia_tri_NUA_VOI…`) | Dùng `SO_DO["tang3-ban-phim"]`/`["git-tho"]` — hai cổng đã bỏ ghim số. | **STALE** — kiểm bất biến tầng 3 (7/8/9 ca đều ĐÓNG; có ca hỏng/bỏ qua/không chạy/0 ca đều ĐỎ). |

---

## 2. TỪNG CA: TRƯỚC → SAU (BẢNG TRƯỚC/SAU)

### 2.1 A5 — cổng "cây sạch" của wave trước

**TRƯỚC (STALE):** đòi `0/2` cổng cũ XANH (vì tệp AG-01 G20 làm chúng đỏ), rồi đối chứng dương
lại đòi chính tệp đó phải nằm trong `q17._cay_ban()`. Trên cây gộp, luật vùng đã làm cả hai
cổng **XANH 2/2**, cây không còn dòng bẩn nào ngoài vùng ⇒ `dang_co` không thấy trong `ban` ⇒
`AssertionError` tại dòng 650. Đây là **ghim khoản nợ đã đóng**, không phải cổng hỏng.

**SAU (bất biến đúng, đọc tại chỗ):**

```python
xanh = <số cổng cũ thoát 0>                     # 2/2 trên cây này
dat_cong("cong-cay-sach", xanh)                 # sổ: nền 0, đóng 2
# "cây sạch" = KHÔNG thay đổi NGOÀI vùng thử/tài liệu (docs/ + mọi thư mục tên bắt đầu "thu")
ngoai_vung = [d for d in git_status if not _la_dong_cua_wave(d, vung)]
assertEqual(ngoai_vung, [])
# ĐỐI CHỨNG ÂM: luật vùng phải BẮT được " M admin/admin.js", "?? app/server.py"
# ĐỐI CHỨNG DƯƠNG: "?? docs/G20_MEASURE_FIX.md", "?? app/thu/thu_moi.py" phải được THA
# ĐỐI CHỨNG ÂM ĐỘC LẬP: test_a1b của CHÍNH g17/g18 (canh phạm vi miễn trừ) phải XANH
```

Đây là luật của `thu_g21_chotcay`: luật nằm MỘT chỗ, g17/g18/g20 dùng chung; miễn trừ theo
**quy tắc vùng**, không theo tên. Không nới thành "bỏ qua hết": tệp sản phẩm vẫn bị bắt.

**BẰNG CHỨNG (lượt sau):**

```
thu_qa_g17.py → mã thoát 0
thu_qa_g18.py → mã thoát 0
thu_qa_g17.py tự kiểm phạm vi → mã thoát 0
thu_qa_g18.py tự kiểm phạm vi → mã thoát 0
[G1] cổng cây sạch wave trước XANH: 2/2 · vùng wave TỰ DÒ=('app/thu/', 'docs/', 'gateway/thu/',
     'thu_frontend/', 'thu_giao_dien/') · thay đổi ngoài vùng=0 · luật bắt được tệp sản phẩm
```

Ngoài ra A5 bắt **PHÉP ĐO CHẾT**: nếu tên ca bị đổi / `Ran 0 tests` / `AttributeError` thì
`self.fail` với thông điệp riêng, không đếm thành "cây bẩn" (`L-G20-C`).

### 2.2 B1 — tầng 3 `06_ban_phim.spec.js`

**TRƯỚC (STALE), hai lớp:**

1. `do_tang_3()` dựng nền bằng `migrate.py` nhưng **không khai kho**. G22 đổi `migrate.py` sang
   fail-closed: chưa khai `KHO_DANG_CHAY` thì từ chối, vì một `hub.db` cũ trông y hệt `hub.db`
   đang phục vụ và bản sao lưu rỗng là đường lùi giả. Vì thế log là
   `[migrate hỏng] … CHƯA KHAI kho đang chạy` ⇒ **0 ca**, B1 đỏ.
2. Sổ ghim `(7,0,0)`; đặc tả hiện có **8** ca (thêm `04b — TỰ KIỂM`). Lượt đo thủ công trên nền
   đúng cho `8 passed (18.2s)`, ca 04 đo **13** điểm dừng TRONG màn (ngưỡng `> 10`). Con số 7
   là **ghim STALE**, không phải nợ sản phẩm.

**SAU:** `do_tang_3()` khai `VIP_KHO_DANG_CHAY=sqlite` cho thư mục TẠM cô lập (không phải
chuyển production sang SQLite — D-8), rồi B1 canh bất biến, **không ghim số ca**:

```python
# DONG  = thoát 0, hỏng=0, bỏ qua=0, "did not run"=0, đạt>0
# NEN   = còn hỏng/bỏ qua/không chạy, hoặc thoát != 0
# KHONG_DO = 0 ca  ⇒ ĐỎ (phép đo chết), không phải BỎ QUA
```

`nền không dựng được` / `máy chủ không mở` ⇒ `self.fail` kèm log, **không** `skipTest`.
Đối chứng dương của bộ đếm: output tổng hợp `8 passed · 1 failed · 2 skipped · 3 did not run`
phải đọc ra `(8,1,2,3)`.

**BẰNG CHỨNG (lượt sau):**

```
[B1] nhị phân: chỉ định BAN_GIAO §1 (chromium-1194) · mã thoát=0 · 8 đạt · 0 hỏng ·
     0 bỏ qua · 0 KHÔNG CHẠY
     ca 04 đo được: 13 điểm dừng là điều khiển TRONG màn
     phán quyết cổng C2 = ĐÓNG (ĐẠT)
```

**MỘT LƯU Ý TRUNG THỰC:** trong **8 lượt** chạy đặc tả của lượt này, **1 lượt** ca
`06 — TỰ KIỂM` đỏ (`gỡ module mà Enter VẪN đổi màn`) kéo theo `1 did not run`; B1 phán ĐỎ là
ĐÚNG (spec chưa trọn vẹn/xanh). Đó là **lỗi thật của bộ đo tầng 3** nằm trong
`thu_giao_dien/06_ban_phim.spec.js` — tệp của AG-06/G22, **ngoài phạm vi ghi của U2**; không sửa,
không retry để ép xanh. Xem §5.7.

### 2.3 B2 — đọc lại log ca 04

**TRƯỚC (STALE):** log không tồn tại/không có ca 04 vì B1 dựng nền hỏng. Bản cũ còn ghim
nguyên văn tiêu đề `04 — Tab vào được các điều khiển TRONG màn`; đặc tả có thể thêm chữ mà phép
đo vẫn đúng.

**SAU:** chỉ đòi (a) log nhắc số hiệu ca `04`, (b) có DÒNG ĐO
`… lượt Tab: N điểm dừng là điều khiển trong màn`, (c) `N` đọc được. Đối chứng dương: đọc một
dòng tổng hợp `11` phải ra `11`. Không chạy tầng 3 lần hai.

**BẰNG CHỨNG:** `[B2] ca 04 trên nền: 13 điểm dừng là điều khiển TRONG màn`.

### 2.4 C4 — route `truy_van` + migration v9

**TRƯỚC (STALE):** dòng 702 `assertEqual(nhap, [])` khẳng định **trạng thái nền**.
`docs/G22_CONTRACT.md` §0ter ghi nguyên văn:

> `app/thu/thu_qa_g20.py` dòng 702: `self.assertEqual(nhap, [], "nền đã đổi…")`. Đo trực tiếp
> trên cây tích hợp `146500b`: `AssertionError: ['app/server.py'] != []` ⇒ cổng C4 của G20 ĐỎ
> dù `dat_cong` nói ĐÓNG.

Sản phẩm đã đóng route: `app/server.py` có `import truy_van`, gọi `truy_van.tim_don(...)`, bắt
`truy_van.LoiTruyVan`, và `truy_van.mo_ta_bo_loc()`. Đây đúng là **ghim trạng thái nền**, không
phải lỗi.

**SAU:** bỏ dòng ghim; giữ cặp `(schema_ok, route_ok)` với `schema_ok = PHIEN_BAN_SCHEMA >= 9`
(sàn, không ghim đúng 9) và `route_ok = có ≥1 tệp SẢN XUẤT import truy_van`. Bổ sung:

- đối chứng **dương** trên cây tạm: tệp `server_gia.py` có `import truy_van` phải được đếm;
- đối chứng **âm**: gỡ/comment import trên chính cây tạm ⇒ bộ dò trả `[]`;
- đối chứng **âm của cổng**: `(True, False)` phải bị `dat_cong(..., che_do="gop")` phán ĐỎ.

**BẰNG CHỨNG:** `[C4] PHIEN_BAN_SCHEMA=9 · nang_len_v9=True · tệp SẢN XUẤT import truy_van=1
['app/server.py'] · phán quyết = DONG (ĐẠT) · nền (True, False) bị phán ĐỎ khi gộp`.

### 2.5 C1 — `git` với môi trường nguyên bản

**TRƯỚC (STALE):**

- Đối chứng dương `assertEqual(r2.stdout.strip(), HEAD_NEN)` ghim `HEAD = 148ecd3`; HEAD thật là
  `2f4c3d1…` ⇒ đỏ vì HEAD nhích, không phải vì git hỏng (`L-G20-A`).
- `git` thô trả **128** vì môi trường phiên có `GIT_CONFIG_COUNT=2` nhưng thiếu
  `GIT_CONFIG_KEY_0/1` và có `VALUE_0/1` ⇒ `fatal: unable to parse command-line config`
  (`N-G18-00`). Đây là **lỗi MÔI TRƯỜNG của máy**, không phải cây mã, và từ trong repo KHÔNG
  sửa được gốc (`docs/G21_CHOTCAY.md` §5.1; `docs/QA_G22.md` §6.3). Bản cũ biến nó thành ô
  "nền" của một cổng nên `gop` **luôn** đỏ.

**SAU (bất biến đúng, đọc tại chỗ):**

```python
loai = phan_loai_git_tho(rc, stderr)
# OK          : git thô chạy được (môi trường lành)
# N-G18-00    : đúng chữ ký thiếu GIT_CONFIG_KEY_*  → IN CẢNH BÁO, chủ AG-00, KHÔNG phải nợ sản phẩm
# LOI_KHAC    : git hỏng vì lý do THẬT              → ca PHẢI ĐỎ, kèm stderr
# đối chứng dương: git ĐÃ CHUẨN HOÁ phải thoát 0, HEAD là 40 hex, và merge-base --is-ancestor
#                  HEAD_NEN HEAD == 0 (HEAD_NEN chỉ là TỔ TIÊN, KHÔNG so bằng)
```

Bộ phân loại có đối chứng âm: `128 + thiếu KEY_0` ⇒ `N-G18-00`; `1 + "not a git repository"`
⇒ `LOI_KHAC` (không được nuốt lỗi thật).

**BẰNG CHỨNG:** `[C1] git thô=128 (N-G18-00) · git đã chuẩn hoá=0 · HEAD=2f4c3d1402c1 (hậu duệ
của nền)` + cảnh báo `N-G18-00 VẪN MỞ — chủ AG-00`. Không có skip, không có PASS giả: dị dạng
vẫn được in và vẫn nằm trong báo cáo; chỉ **không** bị tính thành nợ sản phẩm.

### 2.6 Z1 — sổ đối chứng dương

Ba nhóm thiếu dương là hệ quả của A5/C1/C4 ném lỗi trước `_dc_duong`. Sau khi sửa, sổ có **15
nhóm, 0 nhóm thiếu dương**, gồm cả ba nhóm từng thiếu:

```
[Z1] cong-cay-sach          âm=1 dương=1
[Z1] git-tho                âm=1 dương=1
[Z1] truy-van-C6           âm=1 dương=1
[Z1] 15 nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả
```

Z1 vẫn tự kiểm bằng dữ liệu tổng hợp: nhóm âm cố ý thiếu dương phải bị bắt, nhóm đủ hai chiều
không được báo động giả.

---

## 3. ĐỐI CHỨNG ÂM — "LÀM HÀNH VI CŨ TRỞ LẠI THÌ CA PHẢI ĐỎ"

| Hành vi cũ nếu quay lại | Đối chứng bắt nó | Kết quả đo |
|---|---|---|
| Miễn trừ "cây sạch" theo **danh sách tên cứng** | `A_Nen.test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu` của g17/g18 (chạy trong A5) | XANH hiện tại; đỏ nếu phạm vi trôi về tên cứng |
| Luật vùng nuốt mã sản phẩm | `chotcay.phan_loai([" M admin/admin.js", "?? app/server.py"], mau)["do"]` | phải trả đúng hai dòng |
| Cây bẩn ngoài vùng wave | `git status` + `_la_dong_cua_wave` (A5 + Z2) | `[]` trên cây này |
| B1 ghim lại số ca `(7,0,0)` | `T4`: `dat_cong_tang_3(0, 7/8/9, 0, 0, 0)` | cả ba đều ĐẠT (không ghim số) |
| B1 cho qua khi còn ca chưa chạy | `T4`: `(0,5,0,0,2)` (did not run), `(0,5,1,0,0)` (failed), `(0,5,0,1,0)` (skipped), `(1,5,0,0,0)` (exit≠0) | tất cả ĐỎ |
| B1 coi nền không dựng được là "0 ca rồi bỏ qua" | B1: `self.fail` khi `ghi_chu == "nền không dựng được"` | ĐỎ kèm log, không skip |
| C4 lại ghim `nhap == []` | bỏ hẳn assertion; `(True, False)` phải ĐỎ ở `gop` | ĐỎ |
| Bộ dò `truy_van` mù | cây tạm: có import ⇒ thấy; gỡ import ⇒ `[]` | đúng hai chiều |
| C1 ghim HEAD = `148ecd3` | HEAD đọc tại chỗ (40 hex) + `merge-base --is-ancestor` | XANH dù HEAD đã nhích |
| Bộ phân loại git nuốt lỗi thật | `phan_loai_git_tho(1, "fatal: not a git repository") == "LOI_KHAC"` | ĐỎ nếu trả `N-G18-00`/`OK` |
| Z1 bỏ sót nhóm thiếu dương | `nhom_thieu_duong({"nhom-gia": {"am":1,"duong":0}})` | `["nhom-gia"]` |

---

## 4. BẰNG CHỨNG CHẠY (CMD + EXIT + SỐ CA)

### 4.1 TRƯỚC

```
$ VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
Ran 21 tests in 7.742s
FAILED (failures=6, skipped=2)
EXIT=1
```

Sáu ca: `A5_CongCaySach.test_g1…` · `B_GiaoDien.test_b1…` · `B_GiaoDien.test_b2…` ·
`C4_C5_NoKhac.test_c4…` · `C_MoiTruong.test_c1…` · `Z_ChotChan.test_z1…`.

### 4.2 SAU

```
$ VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py
Ran 21 tests in 18.889s
OK (skipped=2)
EXIT=0
```

Chi tiết các dòng phán quyết:

```
[A1] HEAD=2f4c3d1402c1 · nền 148ecd3 là TỔ TIÊN · main=de740dc (khác HEAD) · chế độ=gop
[B1] nhị phân: … (chromium-1194) · mã thoát=0 · 8 đạt · 0 hỏng · 0 bỏ qua · 0 KHÔNG CHẠY
     ca 04 đo được: 13 điểm dừng là điều khiển TRONG màn · phán quyết cổng C2 = ĐÓNG (ĐẠT)
[B2] ca 04 trên nền: 13 điểm dừng là điều khiển TRONG màn (ngưỡng đặc tả: >10)
[C4] PHIEN_BAN_SCHEMA=9 · nang_len_v9=True · tệp SẢN XUẤT import truy_van=1 ['app/server.py']
     phán quyết cổng C4 = DONG (ĐẠT) · nền (True, False) bị phán ĐỎ khi gộp
[C1] git thô=128 (N-G18-00) · git đã chuẩn hoá=0 · HEAD=2f4c3d1402c1 (hậu duệ của nền)
[G1] cổng cây sạch wave trước XANH: 2/2 · vùng wave TỰ DÒ=('app/thu/', 'docs/', 'gateway/thu/',
     'thu_frontend/', 'thu_giao_dien/') · thay đổi ngoài vùng=0 · luật bắt được tệp sản phẩm
[Z1] 15 nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả
[Z2] git status ngoài vùng thử/tài liệu: RỖNG
```

### 4.3 Đo thủ công nền tầng 3 (trước khi sửa B1 — bằng chứng "nền không đúng" là STALE)

Cùng công thức của `do_tang_3`, chỉ thêm khai kho cho thư mục TẠM:

```
PREP migrate rc=0 · khoi_tao rc=0 · chuan_bi mk rc=0 · chuan_bi don rc=0
8 passed (18.2s)
[đo] 30 lượt Tab: 13 điểm dừng là điều khiển trong màn · 1 lượt ở body · 23 đích khác nhau
```

⇒ Sản phẩm bàn phím **không** hỏng; cái hỏng là **công thức dựng nền của bộ đo**.

### 4.4 Tệp đã sửa + sha256

```
app/thu/thu_qa_g20.py   (sửa)   sha256 = b56062bc928f16f0db13eb4b806b20ad342c992f224ad4df70f6c446710b48dc
docs/G20_MEASURE_FIX.md (mới)   tệp này
```

Không tệp nào khác bị ghi. `git status` ngoài hai tệp: RỖNG (Z2 xác nhận).

---

## 5. CÒN MỞ — BÁO AG-00, KHÔNG TỰ SỬA

1. **`N-G18-00` — lỗi MÔI TRƯỜNG của máy, vẫn mở.** `GIT_CONFIG_COUNT=2` nhưng thiếu
   `GIT_CONFIG_KEY_0/1` ⇒ `git` gọi trần vẫn `128`. Chủ: **AG-00** (gỡ biến khỏi môi trường
   spawn, hoặc đặt đủ cặp). Đây **không phải** lỗi sản phẩm và đã được C1 in cảnh báo rõ; bộ
   kiểm không còn biến nó thành ĐỎ của bản gộp.
2. **`G22 · app/thu/thu_qa_g22.py` ghim sha256 của chính tệp này.** Hằng
   `BAN_DO_G20_GOC_SHA = "5a4b3c83c45f…"` + tuple `G20_C5_VA` dựng lại "bản gốc + 2 khối vá"
   rồi băm. Lượt này sửa hợp lệ `thu_qa_g20.py` ⇒ `D_BanDoG20.test_d1_nam_cong_g20` của G22
   **sẽ đỏ** cho tới khi chủ G22/AG-00 cập nhật hằng + mô tả. Tệp ngoài phạm vi ghi của U2 ⇒
   báo, không sửa lén. sha256 MỚI của tệp đã sửa:
   `b56062bc928f16f0db13eb4b806b20ad342c992f224ad4df70f6c446710b48dc`.
3. **`G22 · SO_DO_G20` còn ghim số cũ:** `C2 = (7,0,0)` (nay 8 ca, có `04b`) và `C3 = 128→0`
   (nay là nợ môi trường `N-G18-00`, không phải nợ sản phẩm). D1 chỉ in ra chứ không assert hai
   giá trị này, nhưng người đọc dễ đọc nhầm; chủ G22/AG-00 cập nhật.
4. **Cùng họ STALE ở `thu_qa_g21.py`:** `SO_DO["tang3-ban-phim"] = (3,1,3)→(7,0,0)` và
   `SO_DO["git-tho"] = 128→0` vẫn ghim y như bản G20 cũ. Chạy `VIP_G21_CHE_DO=gop` trên cây
   này sẽ đỏ ở hai cổng đó vì đặc tả nay có 8 ca và git thô vẫn 128. Ngoài phạm vi ghi của U2
   ⇒ báo AG-00/giao chủ G21 nếu cần.
5. **`VIP_G20_DAY_DU=1` (hồi quy toàn phần) CHƯA chạy trong lượt này** — H1 đang skip có chủ
   đích. Kết quả nghiệm thu ở đây là làn `gop` mặc định; nếu AG-00 cần bằng chứng làn đầy đủ,
   chạy lại với biến đó.
6. **Tài liệu lịch sử** `docs/QA_G20.md`, `docs/G21_BANPHIM_E2E.md`, `docs/G22_GIOIHAN.md`…
   còn trích số cũ (dòng 520/702, `(7,0,0)`). Đây là bản ghi lịch sử, ngoài phạm vi ghi; tệp
   này là bản cập nhật của lượt U2.
7. **Ca `06 — TỰ KIỂM` của `thu_giao_dien/06_ban_phim.spec.js` CHẬP CHỜN — lỗi thật, ngoài
   phạm vi U2.** Đo được **1 đỏ / 8 lượt chạy tầng 3** trong lượt này: `Error: gỡ module mà
   Enter VẪN đổi màn ⇒ ca 02 không đo bản vá`; log
   `tang3_ban_phim.log` + Playwright báo `1 failed · 1 did not run`. Cùng thời điểm máy có
   `load average ≈ 10–12` và một làn khác (`u1-d1-xanhgia`) cũng chạy đặc tả này; giả thuyết
   khả dĩ là `#tieu-de` đổi do nạp dữ liệu bất đồng bộ sau đăng nhập, không phải do Enter — ca
   06 không chờ mạng lặng trước khi chốt `tieu_de_truoc`. **Không sửa spec** (tệp agent khác,
   ngoài vùng ghi). Đề nghị AG-00 giao AG-06 làm bền ca 06, hoặc dùng cổng
   `python3 app/thu/thu_g22_e2e.py` thay vì chạy spec trần (chính `docs/G22_BANPHIM_E2E.md`
   §11 đã ghi tầng 3 chỉ xanh 6/9 lượt vì nền chập chờn). Vì đây là lỗi thật **của bộ đo**, B1
   không được nới: nó phải ĐỎ khi spec không trọn vẹn/xanh.

---

## 6. PHẠM VI / TUÂN THỦ

- Chỉ ghi `app/thu/thu_qa_g20.py` và `docs/G20_MEASURE_FIX.md`; không sửa tệp agent khác.
- Không push, không deploy, không tunnel, không credentials thật, không API production.
- Không sửa DB thật; mọi tầng 3 dùng `VIP_HUB_DATA` trong `tempfile.mkdtemp`, ÉP
  `VIP_HUB_BIND=127.0.0.1`, cổng do OS cấp, tắt theo đúng PID; cụm PostgreSQL `:5432` chỉ ĐỌC
  bằng `lsof`, không kết nối. D-8 giữ nguyên SQLite.
- Không ghi `.git` (sandbox workspace-write). Không tự bấm duyệt sandbox.
- Không xoá ca, không hạ ngưỡng, không `skipTest` để né; mọi ca phủ định đều có đối chứng dương
  trong `DOI_CHUNG`, `Z1` tự phán hỏng nếu thiếu.
