# Z1 — CHÍN BỘ THỬ "0 CA": TỰ KHAI KHO ĐANG CHẠY (G22)

**Kết luận:** 9/9 bộ chạy được thật · **204 ca** · **0 skip** · **exit 0** cho cả chín.
Nguyên nhân "0 ca" không phải lỗi sản phẩm: mỗi bộ gọi `migrate.chay()` (trực tiếp hoặc qua
tiến trình con) mà chưa khai `VIP_KHO_DANG_CHAY`, nên `migrate` TỪ CHỐI trước khi ca nào chạy.

- Mốc đo: `HEAD = cb23312` (`integration/g20` + `y1-kho-suites` + `y2-race-migrate`).
- Phạm vi ghi: **9 tệp thử dưới đây + tệp tài liệu này**. KHÔNG sửa mã sản phẩm, KHÔNG sửa tệp
  khác. `git status` chỉ có 9 tệp `M` + tệp này `??`.
- Mọi nền dữ liệu là `tempfile.mkdtemp`; không chạm `app/du-lieu`, không chạm DB thật.

## 0. Vì sao trước đây "0 ca"

`app/migrate.py::_kiem_kho_truoc_khi_sao_luu()` là cổng **fail-closed** của G22: chưa khai kho
thì nó ném `SystemExit` với nguyên văn:

```
[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này
          ...
          Bộ thử dùng SQLite: `cau_hinh.khai_kho_kiem_thu()` (từ chối nếu thư mục dữ liệu
          không cô lập) — xem docs/G22_CAUHINH.md.
```

Vì vậy đây là **bộ thử chưa khai ngữ cảnh kho của chính mình**, không phải lỗi sản phẩm. Cách
sửa đúng là gọi `app/cau_hinh.py::khai_kho_kiem_thu()` — hàm này (1) chỉ nhận `sqlite`, (2) đòi
`VIP_HUB_DATA` đặt tường minh, (3) từ chối nếu đường dữ liệu nằm trong cây repo hoặc volume
`/du-lieu`, rồi mới đặt `VIP_KHO_DANG_CHAY` vào môi trường. Chép đúng mẫu Y1 đã có trong
`thu_qa_g17.py` / `thu_qa_g18.py` / `thu_g20_baomat.py`.

## 1. Từng bộ: gọi trực tiếp hay qua tiến trình con?

| # | Bộ thử | `migrate` được gọi ở đâu | Dạng | Khai ở (dòng) | Env cho con (dòng) |
|---|--------|--------------------------|------|----------------|---------------------|
| 1 | `thu_g17_baomat.py` | `migrate.chay()` trong `dung_nen()` (tiến trình này); ca `e4` chạy lại **chính bộ thử** trong tiến trình con trên bản sao `app/` | **trực tiếp + con** | 109 | 1751 |
| 2 | `thu_g18_maysrv.py` | `migrate.py` + `khoi_tao.py` spawn trong `setUpModule` | **tiến trình con** | 79 | 129 |
| 3 | `thu_g18_multiprocess.py` | `migrate.py` spawn trong `dung_nen()` | **tiến trình con** | 89 | 123 |
| 4 | `thu_g19_gioihan.py` | `migrate.py` spawn trong `dung_nen()`; P7 còn chạy 2 bộ thử khác bằng `subprocess` | **tiến trình con** | 81 | 125 · 924 |
| 5 | `thu_g21_gioihan.py` | `migrate.py` spawn trong `dung_nen()`; mọi con đi qua `moi_truong_sach()` (A10 chạy 3 bộ hồi quy) | **tiến trình con** | 109 | 175 |
| 6 | `thu_giao_dich.py` | `migrate.chay()` trong `setUpModule` | **trực tiếp** | 32 | — |
| 7 | `thu_han_muc_nguyen_tu.py` | `migrate.chay()` trong `setUpClass` | **trực tiếp** | 39 | — |
| 8 | `thu_header_bao_mat.py` | `migrate.chay()` trong `setUpClass` | **trực tiếp** | 41 | — |
| 9 | `thu_truy_van.py` | `migrate.py` spawn trong `_migrate()` và `do_hieu_nang()` | **tiến trình con** | 45 | 57 · 617 |

Điểm cốt lõi của cột "Env cho con": với 6 bộ dạng **tiến trình con**, khai trong tiến trình hiện
tại là **chưa đủ** nếu môi trường con bị dựng lại. Vì vậy mỗi chỗ spawn `migrate` (và mỗi chỗ
spawn bộ thử khác có thể gọi `migrate`) đều truyền **tường minh**:

```python
env = dict(os.environ, VIP_HUB_DATA=<nền tạm>, VIP_KHO_DANG_CHAY="sqlite")
```

Với 3 harness không có `VIP_HUB_DATA` toàn cục (`g18_multiprocess`, `g19_gioihan`,
`g21_gioihan`), bộ thử tạo thêm một thư mục tạm `_NEN_KHAI` **chỉ để thoả chốt cô lập của hàm
khai**; mọi nền ĐO vẫn do `nen_tam()` tạo riêng. Thư mục khai được đưa vào `NENS` để dọn ở cuối.

## 2. Thay đổi cụ thể (chỉ 9 tệp thử)

Mỗi tệp nhận đúng một khối mẫu Y1, đặt ngay sau import và **sau khi** `VIP_HUB_DATA` đã trỏ nền
tạm:

```python
# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# ... (ghi rõ bộ này gọi migrate TRỰC TIẾP hay qua TIẾN TRÌNH CON) ...
cau_hinh.khai_kho_kiem_thu()
```

- `thu_g17_baomat.py`: khối dòng 102–109; `moi_truong` của ca `e4` (dòng 1751) thêm
  `VIP_KHO_DANG_CHAY="sqlite"`.
- `thu_g18_maysrv.py`: khối dòng 72–79; `setUpModule` (dòng 129) thêm biến cho `migrate.py` /
  `khoi_tao.py`.
- `thu_g18_multiprocess.py`: khối dòng 77–89; `dung_nen()` (dòng 123) thêm biến.
- `thu_g19_gioihan.py`: khối dòng 70–81; `dung_nen()` (dòng 125) và P7 (dòng 924) thêm biến.
- `thu_g21_gioihan.py`: khối dòng 98–109; `moi_truong_sach()` (dòng 175) thêm biến cho **mọi**
  tiến trình con.
- `thu_giao_dich.py`: dòng 17 đặt `os.environ["VIP_HUB_DATA"] = _TM` trước khi nạp `cau_hinh`
  (để chốt cô lập của hàm khai thấy đúng nền tạm), khối khai dòng 26–32.
- `thu_han_muc_nguyen_tu.py`: khối dòng 33–39.
- `thu_header_bao_mat.py`: khối dòng 35–41.
- `thu_truy_van.py`: khối dòng 39–45; hai chỗ spawn `migrate.py` (dòng 57 và 617) thêm biến.

Không xoá ca, không hạ ngưỡng, không `skipTest`, không sửa mã sản phẩm.

### 2.1. Một thay đổi phụ trong `thu_g17_baomat.py` — route mới chưa khai

Sau khi khai kho, bộ G17 chạy 31 ca và lộ **một đỏ có sẵn** (không liên quan khai kho):

```
FAIL: test_v1_bang_cua_phu_moi_route_trong_server
AssertionError: ... ['GET /api/v2/don/loc-mo-ta (server.py:945)']
```

Đây là cửa `truy_van.mo_ta_bo_loc()` do G22/AG-02 thêm sau khi bảng cửa của bộ G17 được viết
(commit `146500b`). Cách sửa **không phải** nới ngưỡng: khai cửa đó vào `bang_cua()` (dòng 642)
để nó được quét cách ly như mọi cửa đọc khác — V1/V2/R5 sẽ đo nó, không bỏ qua. Sau thay đổi:
31/31 ca ĐẠT, exit 0. Đây là sửa **tệp thử** (trong 9 tệp được phép), không phải mã sản phẩm.

## 3. Bằng chứng dương — chạy lại TỪNG bộ (số đo cuối)

| Bộ thử | exit | số ca | skip | thời gian |
|--------|------|-------|------|-----------|
| `thu_g17_baomat.py` | **0** | 31 (`Ran 31 tests`, OK) | 0 | 10 s |
| `thu_g18_maysrv.py` | **0** | 17 (`Ran 17 tests`, OK) | 0 | 6 s |
| `thu_g18_multiprocess.py` | **0** | 26 (`TỔNG: 26`, BỎ QUA 0) | 0 | 36 s |
| `thu_g19_gioihan.py` | **0** | 22 (`TỔNG: 22`, BỎ QUA 0) | 0 | 26 s |
| `thu_g21_gioihan.py` | **0** | 38 (`TỔNG=38`, BỎ QUA 0) | 0 | 70 s |
| `thu_giao_dich.py` | **0** | 17 (`Ran 17 tests`, OK) | 0 | <1 s |
| `thu_han_muc_nguyen_tu.py` | **0** | 5 (`Ran 5 tests`, OK) | 0 | <1 s |
| `thu_header_bao_mat.py` | **0** | 8 (`Ran 8 tests`, OK) | 0 | 1 s |
| `thu_truy_van.py` | **0** | 40 (`Ran 40 tests`, OK) | 0 | <1 s |
| **TỔNG** | **0 cả 9** | **204** | **0** | ~150 s |

Ghi chú `g21`: dòng `22 ca — ĐẠT` xuất hiện trong output là **bản ghi A10 của
`thu_g19_gioihan.py`** (bộ hồi quy được gọi từ A10), không phải số ca của chính G21. Tổng kết
thật của G21 là `ca ĐẠT=38 · TỔNG=38`; commit `9ded4a5` của chính bộ cũng ghi "38 ca ĐẠT, exit
0". Sổ ghim X1 ghi 22 là đếm theo dòng A10 — cần cập nhật sổ, không phải hồi quy.

## 4. Đối chứng âm — bỏ khai thì bộ thử PHẢI đỏ lại (làm thật)

### 4.1. Trước khi sửa (mốc gốc)

Chạy 9 tệp trên `HEAD` nguyên bản, chưa thêm một dòng nào:

| Bộ thử | exit | số ca | dấu vết |
|--------|------|-------|---------|
| `thu_g17_baomat.py` | 1 | 0 (bộ chạy chung đếm 0: không có dòng `Ran N`; E1–E3 chạy trước, rồi `SystemExit` từ `migrate.chay()` làm unittest không in tổng kết) | `[migrate] TỪ CHỐI` |
| `thu_g18_maysrv.py` | 1 | 0 | `Ran 0 tests`; `RuntimeError: migrate.py hỏng` |
| `thu_g18_multiprocess.py` | 1 | 0 | `RuntimeError: migrate.py hỏng (mã 1)` |
| `thu_g19_gioihan.py` | 1 | 0 | `RuntimeError: migrate.py hỏng (mã 1)` |
| `thu_g21_gioihan.py` | 1 | 0 | `RuntimeError: migrate.py hỏng (mã 1)` |
| `thu_giao_dich.py` | 1 | 0 | `[migrate] TỪ CHỐI` |
| `thu_han_muc_nguyen_tu.py` | 1 | 0 | `[migrate] TỪ CHỐI` |
| `thu_header_bao_mat.py` | 1 | 0 | `[migrate] TỪ CHỐI` |
| `thu_truy_van.py` | 1 | 0 | `Ran 0 tests`; `RuntimeError: migrate hỏng` |

### 4.2. Sau khi sửa — lấy lại nguyên văn `HEAD` rồi chạy (rồi phục hồi)

Với TỪNG bộ: sao lưu bản đã sửa → `git show HEAD:<tệp>` ghi đè → chạy → phục hồi bản đã sửa →
`cmp` xác nhận phục hồi đúng từng byte. Kết quả:

| Bộ thử | exit NC | số ca NC | phục hồi |
|--------|---------|----------|----------|
| `thu_g17_baomat.py` | 1 | 0 | `cmp` OK |
| `thu_g18_maysrv.py` | 1 | 0 (`Ran 0 tests`) | `cmp` OK |
| `thu_g18_multiprocess.py` | 1 | 0 | `cmp` OK |
| `thu_g19_gioihan.py` | 1 | 0 | `cmp` OK |
| `thu_g21_gioihan.py` | 1 | 0 | `cmp` OK |
| `thu_giao_dich.py` | 1 | 0 | `cmp` OK |
| `thu_han_muc_nguyen_tu.py` | 1 | 0 (không có dòng `Ran N`) | `cmp` OK |
| `thu_header_bao_mat.py` | 1 | 0 | `cmp` OK |
| `thu_truy_van.py` | 1 | 0 (`Ran 0 tests`) | `cmp` OK |

⇒ Lời khai là **nguyên nhân thật**: bỏ nó thì cả chín bộ chết lại đúng như cũ; giữ nó thì cả
chín bộ chạy thật. Không có ca nào bị xoá/hạ ngưỡng để đạt exit 0.

## 5. Ảnh hưởng ra NGOÀI phạm vi (không sửa — báo lại)

1. **`app/thu/thu_g22_zeroca.py::TuKiem.test_14_that_thu_giao_dich_tu_choi_roi_chay_duoc`**
   đang ghim hành vi cũ: chạy `thu_giao_dich.py` **không** đặt `VIP_KHO_DANG_CHAY` thì phải
   `0 ca` / `TU_CHOI`. Nay bộ đó tự khai nên chạy **17 ca** ⇒ test_14 FAIL:
   `Ran 17 tests` · `FAILED (failures=1)`. Đây là **hệ quả đúng** của việc sửa; cần cập nhật
   test_14 (hoặc chuyển đối chứng lịch sử sang một bộ chưa khai) — **ngoài phạm vi 9 tệp**, tôi
   không sửa.
2. **Sổ ghim `SO_CA_GHIM`** của `thu_g22_zeroca.py` cần cập nhật theo số đo mới:
   `thu_g17_baomat.py` từ `("HONG", 31)` → `("DAT", 31)`; `thu_g21_gioihan.py` từ
   `("DAT", 22)` → `("DAT", 38)`. **Bảy** bộ còn lại khớp ghim (17 · 26 · 22 · 17 · 5 · 8 · 40).
   `so_sanh()` xếp mục lệch là `CANH_BAO` (không phải `FAIL`).
3. **Đo lại 12 bộ bằng chính bộ tự kiểm** (`python3 app/thu/thu_g22_zeroca.py --do-lai`, chế độ
   NGUYÊN VĂN — không đặt `VIP_KHO_DANG_CHAY`): `exit 2` · `HOI_SINH=10 · KHOP=2`.
   - 9 bộ của Z1 + `thu_bien_driver.py` = 10 "hồi sinh" (mốc ghim 0 ca, nay > 0). Riêng
     `thu_bien_driver.py` **không phải do Z1**: tệp đó không gọi `migrate` và Z1 không sửa nó;
     trên cây này nó đã xanh 5 ca ở `HEAD` (mốc ghim X1 cũ). Cần cập nhật sổ.
   - 2 `KHOP` là `thu_g22_gioihan.py` (HỎNG 32 ca — cổng C5 có sẵn, ngoài phạm vi) và
     `thu_g22_e2e.py` (THIẾU PHỤ THUỘC Chromium).
   - `exit 2` ở đây là **"mốc cũ, cần cập nhật sổ"** theo thiết kế của zeroca, không phải hồi quy.
   - Zeroca đếm G21 = 22 ca vì nó bắt dòng `22 ca — ĐẠT` của A10 nhúng trong output; số ca THẬT
     của G21 là 38 (xem §3) — giới hạn bộ đếm của zeroca, không phải bộ G21 chạy thiếu.
4. `thu_g22_zeroca.py` (bộ tự kiểm) hiện `Ran 17 tests` · 1 FAIL đúng như mục 1; các ca còn
   lại vẫn ĐẠT. Không sửa vì ngoài phạm vi.

## 6. Ràng buộc đã giữ

- local-first: mọi bộ chạy trên máy, chỉ `127.0.0.1`; không gọi API hãng, không ra mạng.
- Không push/deploy; không sửa DB thật; mọi nền là thư mục tạm (`tempfile.mkdtemp`).
- Không tự bấm duyệt sandbox; không đụng `.git`.
- Không sửa mã sản phẩm; không sửa tệp ngoài 9 tệp thử + tài liệu này.
- Không xoá ca, không hạ ngưỡng, không `skipTest`.

## 7. Tái lập

```sh
cd <repo>
# Môi trường git của máy có GIT_CONFIG_COUNT=2 thiếu KEY_0/KEY_1 (N-G18-00) — bỏ trước khi chạy:
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1

for f in thu_g17_baomat.py thu_g18_maysrv.py thu_g18_multiprocess.py thu_g19_gioihan.py \
         thu_g21_gioihan.py thu_giao_dich.py thu_han_muc_nguyen_tu.py \
         thu_header_bao_mat.py thu_truy_van.py; do
  python3 app/thu/$f; echo "exit=$? — $f"
done
# Kỳ vọng: exit 0 cho cả 9 · tổng 204 ca · 0 skip.
```
