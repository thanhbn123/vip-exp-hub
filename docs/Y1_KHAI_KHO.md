# Y1 — 9 BỘ THỬ TỰ KHAI KHO ĐANG CHẠY

**Làn:** Y1 · **Ngày đo:** 19/10/2026 · **Nhánh:** `y1-kho-suites` · **HEAD:** `7b8bb84`
**Phạm vi ghi:** 9 bộ thử dưới đây + tệp này. **KHÔNG sửa** `app/cau_hinh.py`, `app/migrate.py`
(tệp của làn Y2), `app/thu/chay_tat_ca.sh`, bộ thử nào ngoài danh sách, `.git`, DB thật.
**Không** push/deploy/gọi hãng.

---

## 0. TÓM TẮT CHO NGƯỜI VỘI

X2 đo được: **một dòng** `VIP_KHO_DANG_CHAY=sqlite` trong môi trường chạy làm **9 bộ xanh hoàn
toàn** (286 ca). Nghĩa là 9 bộ ấy đỏ vì **cổng fail-closed của G22** chặn `migrate.py` khi kho
chưa được khai — **không phải lỗi sản phẩm**.

Lượt này không thêm dòng `export` ấy vào `app/thu/chay_tat_ca.sh` (tệp ngoài phạm vi, và như thế
vẫn là "người chạy nhớ khai"). Thay vào đó **từng bộ tự khai** bằng giao diện có sẵn
`cau_hinh.khai_kho_kiem_thu()`:

| # | Bộ | Trước | Sau | Đối chứng âm |
|---:|---|---|---|---|
| 1 | `thu_bao_mat.py` | exit **1** · **57** ca · 1 FAIL | exit **0** · 57 ca · 0 FAIL | bỏ khai → exit **1** · 57 ca · 1 FAIL |
| 2 | `thu_g19_tich_hop.py` | exit **1** · **8** ca (cổng ĐỎ) | exit **0** · 8 ca | bỏ khai **và** kho hỏng → exit **1** |
| 3 | `thu_g20_baomat.py` | exit **1** · **28** ca · 1 FAIL | exit **0** · 28 ca · 0 FAIL | kho hỏng → exit **1** |
| 4 | `thu_g21_bimat.py` | exit **1** · **33** ca · 6 FAIL | exit **0** · 33 ca · 0 FAIL | bỏ khai → exit **1** · 6 FAIL; kho hỏng → exit **1** |
| 5 | `thu_g22_bimat.py` | exit **1** · **23** ca · 5 FAIL | exit **0** · 23 ca · 0 FAIL | bỏ khai → exit **1** · 4 FAIL; kho hỏng → exit **1** |
| 6 | `thu_qa_g17.py` | exit **1** · **56** ca · 25 FAIL/ERROR | exit **0** · 56 ca · 0 FAIL | bỏ khai → exit **1** · 24 ERROR; kho hỏng → exit **1** |
| 7 | `thu_qa_g18_tich_hop.py` | exit **1** · **26** ca · 3 FAIL | exit **0** · 26 ca · 0 FAIL | bỏ khai → exit **1** · 3 FAIL |
| 8 | `thu_qa_g18.py` | exit **1** · **47** ca · **1 skip** · 20 FAIL/ERROR | exit **0** · 47 ca · 1 skip | bỏ khai → exit **1** · 15 FAIL/ERROR; kho hỏng → exit **1** |
| 9 | `thu_qa_g19_tich_hop.py` | exit **1** · **8** ca (cổng ĐỎ) | exit **0** · 8 ca | kho hỏng → exit **1** |

**Tổng: 9/9 bộ xanh khi chạy riêng · 286 ca được đo lại** (đúng con số X2 đã đo bằng biến môi
trường), **0 ca bị xoá, 0 ngưỡng bị hạ, 0 `skipTest` được thêm**. Mỗi bộ có **ít nhất một đối
chứng âm** làm nó đỏ lại (bảng §4); 5/9 bộ đỏ lại bằng **cả hai** kiểu đối chứng.

**Chạy toàn cây:** `sh app/thu/chay_tat_ca.sh` → exit **1** · **1967** ca · **47** bộ ✓ ·
**23** bộ ✗ · **1** bộ ⊘ (+ dòng E2E riêng ✗). Trong 9 bộ của lượt này, **8 bộ ✓**; riêng
`thu_g19_tich_hop.py` **ĐỎ một lượt trong toàn cây do runner bên trong flake**, không phải do
khai kho — chạy riêng **4/4 lượt xanh** và cổng ĐẠT `38/38` ca (xem §6). Số đỏ còn lại là các bộ
**ngoài phạm vi**: 2 lỗi thật của X2, các ghim cũ, 9 bộ Phụ lục A + `thu_qa_g21.py` (cùng bệnh
"chưa tự khai" nhưng không được cấp phép ghi), và E2E thiếu Chromium. **Không có bộ nào trong 9
bộ bị đỏ vì lời khai kho.**

---

## 1. DANH SÁCH 9 BỘ — LẤY TỪ `docs/G22_PHAN_LOAI_DO.md` CỦA X2

X2 phân nhóm A (§3.1) đúng **9 bộ** đỏ **hoàn toàn** vì `migrate` fail-closed:

| # trong bảng 20 của X2 | Bộ | Vì sao đỏ (bằng chứng X2) |
|---:|---|---|
| 1 | `thu_bao_mat.py` | `test_e1_migrate_v4…` — `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| 4 | `thu_g19_tich_hop.py` | runner `thu_g21_gioihan.py` chết ở `migrate.py hỏng (mã 1)` |
| 5 | `thu_g20_baomat.py` | chạy `thu_qa_g17.py`/`thu_qa_g18.py` trong tiến trình con; hai bộ này chết ở `migrate` |
| 8 | `thu_g21_bimat.py` | `máy chủ thật không mở cổng … CSDL ở schema v0` |
| 10 | `thu_g22_bimat.py` | cùng gốc `CSDL ở schema v0` |
| 13 | `thu_qa_g17.py` | `moi_truong() → migrate.chay() → sao_luu() → _kiem_kho_truoc_khi_sao_luu()` |
| 14 | `thu_qa_g18_tich_hop.py` | `migrate.py` chạy ngay ở cấp mô-đun; cổng không lên |
| 15 | `thu_qa_g18.py` | `moi_truong() → migrate.chay()`; 19 lỗi cùng gốc |
| 16 | `thu_qa_g19_tich_hop.py` | chạy bộ gốc `thu_g19_tich_hop.py`, chết ở runner |

Hai bộ **#3 `thu_g19_route.py`** và **#20 `thu_g22_gioihan.py`** cũng có lỗi dựng nền này nhưng
**còn ghim số/route** nên không nằm trong 9 bộ "xanh hoàn toàn"; chúng không thuộc phạm vi lượt
này. **Không bộ nào trong 9 bộ trên là lỗi sản phẩm** — X2 đã đo bằng cách khai biến môi trường.

Nguồn: `docs/G22_PHAN_LOAI_DO.md` §3.1 (nhóm A) và §4 (bảng tổng hợp: 9 bộ = 286 ca).

---

## 2. CÁCH SỬA — MỘT LỜI GỌI CHO MỖI BỘ, KHÔNG DỰA VÀO NGƯỜI CHẠY

### 2.1 Mẫu chung

Mỗi bộ đã có `VIP_HUB_DATA` trỏ thư mục TẠM từ trước. Thêm **một lời gọi** sau khi `cau_hinh`
được nạp và trước phép đo đầu tiên:

```python
cau_hinh.khai_kho_kiem_thu()
```

Hàm này (Agent 01, `app/cau_hinh.py:75`):
1. đặt `VIP_KHO_DANG_CHAY=sqlite` vào `os.environ` (nên **tiến trình con kế thừa**);
2. đặt `cau_hinh.KHO_DANG_CHAY='sqlite'` (nên `migrate.chay()` **trong chính tiến trình** thấy);
3. **từ chối** nếu `VIP_HUB_DATA` chưa đặt, nằm trong cây repo, hoặc là volume `/du-lieu` —
   nên không thể vô tình khai kho cho dữ liệu thật.

Không bộ nào đọc `VIP_KHO_DANG_CHAY` từ shell; lượt đo dưới đây chạy với biến ấy **không đặt**.

### 2.2 Vị trí đã sửa (9 tệp, +109 dòng)

| Bộ | Vị trí | Ghi chú |
|---|---|---|
| `thu_bao_mat.py` | sau khối import `app/` | khai trước `E_MigrateV4` (chạy `migrate.py` trong con) |
| `thu_g19_tich_hop.py` | sau hằng số, trước khi chạy runner | **cổng**: tự khai rồi truyền env sang `chay.sh`; nếu `VIP_HUB_DATA` chưa có thì tạo thư mục tạm |
| `thu_g20_baomat.py` | sau `sys.path`, trước `HEAD_GHIM` | chạy các bộ con nên env được kế thừa |
| `thu_g21_bimat.py` | sau import `app/`, trước phần BÍ MẬT GIẢ | tiến trình này + con đều thấy |
| `thu_g22_bimat.py` | sau import `app/`, trước phần BÍ MẬT GIẢ | như trên |
| `thu_qa_g17.py` | sau import `app/` | gọi qua helper `_khai_kho_cua_bo_thu()` (xem §2.3) |
| `thu_qa_g18_tich_hop.py` | **trước** `_MIGRATE` cấp mô-đun | `migrate.py` được gọi ngay sau đó |
| `thu_qa_g18.py` | sau import `app/` | gọi qua cùng helper (xem §2.3) |
| `thu_qa_g19_tich_hop.py` | sau hằng số, trước `_lenh()` | **bản uỷ quyền**: tự khai rồi truyền env sang bộ gốc |

### 2.3 Hai bộ QA cần thêm một chi tiết — và vì sao KHÔNG nới chốt

`thu_qa_g17.py` và `thu_qa_g18.py` có **driver đột biến**: chúng sao `app/*.py` vào thư mục tạm
rồi đặt bản sao ấy **lên trước `sys.path`** (`_cay_dot_bien` → `_chay_con(cay_app=…)`). Trong
tiến trình con ấy:

* `import cau_hinh` nạp **bản sao** trong thư mục tạm;
* `cau_hinh.THU_MUC_GOC` vì thế là **chính thư mục tạm** (`…/T`), không phải gốc repo;
* mọi nền đo `…/T/veh-g17-drv-…` đều bị hàm khai coi là "nằm trong cây repo" ⇒ **TỪ CHỐI OAN**.

Đo được: lần chạy đầu sau khi thêm khai, `thu_qa_g17.py` còn **1 FAIL** (`f7`/M4) và
`thu_qa_g18.py` còn **5 FAIL** (`j3`–`j7`) — tất cả là `SystemExit` từ chốt cô lập, không phải
sản phẩm. Cách sửa **không nới chốt**: gốc repo THẬT luôn suy được từ `__file__` của bộ thử
(`GOC_CAY`), nên helper chỉ cho hàm khai nhìn gốc THẬT **trong lúc gọi** rồi trả lại giá trị cũ:

```python
def _khai_kho_cua_bo_thu():
    cu = getattr(cau_hinh, "THU_MUC_GOC", None)
    try:
        cau_hinh.THU_MUC_GOC = GOC_CAY          # gốc repo THẬT, không phải bản sao
        return cau_hinh.khai_kho_kiem_thu()
    finally:
        cau_hinh.THU_MUC_GOC = cu
```

Chốt cô lập **giữ nguyên độ răng**: dữ liệu nằm trong repo thật vẫn bị từ chối —
đo ở §4.2 (`VIP_G17_DATA=<repo>/app/du-lieu` ⇒ exit 1 kèm `TỪ CHỐI`). Đây là sửa **đầu vào bị
bản sao làm sai**, không phải bỏ kiểm tra.

---

## 3. BẰNG CHỨNG "TRƯỚC / SAU" — TỪNG BỘ, MÃ THOÁT THẬT

Lệnh (mỗi bộ chạy riêng, `cwd` = gốc repo, `VIP_KHO_DANG_CHAY` **không** đặt,
`GIT_CONFIG_*` dị dạng đã gỡ như N-G18-00):

```sh
env -u VIP_KHO_DANG_CHAY python3 app/thu/<bộ>.py
```

| # | Bộ | Trước: exit · Ran · skip · kết quả unittest | Sau: exit · Ran · skip · kết quả unittest |
|---:|---|---|---|
| 1 | `thu_bao_mat.py` | **1** · **57** · 0 · `FAILED (failures=1)` | **0** · **57** · 0 · `OK` |
| 2 | `thu_g19_tich_hop.py` | **1** · **8** · 0 · tự kiểm `OK`, **cổng ĐỎ** (`EXIT_BO_DO=1`) | **0** · **8** · 0 · `OK`, cổng ĐẠT |
| 3 | `thu_g20_baomat.py` | **1** · **28** · 0 · `FAILED (failures=1)` | **0** · **28** · 0 · `OK` |
| 4 | `thu_g21_bimat.py` | **1** · **33** · 0 · `FAILED (failures=6)` | **0** · **33** · 0 · `OK` (xem ghi chú flake §6) |
| 5 | `thu_g22_bimat.py` | **1** · **23** · 0 · `FAILED (failures=5)` | **0** · **23** · 0 · `OK` |
| 6 | `thu_qa_g17.py` | **1** · **56** · 0 · `FAILED (failures=1, errors=24)` | **0** · **56** · 0 · `OK` |
| 7 | `thu_qa_g18_tich_hop.py` | **1** · **26** · 0 · `FAILED (failures=3)` | **0** · **26** · 0 · `OK` |
| 8 | `thu_qa_g18.py` | **1** · **47** · **1** · `FAILED (failures=8, errors=12, skipped=1)` | **0** · **47** · **1** · `OK (skipped=1)` |
| 9 | `thu_qa_g19_tich_hop.py` | **1** · **8** · 0 · tự kiểm `OK`, **cổng ĐỎ** (mã bộ gốc = 1) | **0** · **8** · 0 · `OK`, cổng ĐẠT |

**Đọc số cho đúng:**

* `Ran N` là số ca **THẬT SỰ chạy** của `unittest`; ca `skip` nằm trong `N` và được ghi riêng.
  Chỉ `thu_qa_g18.py` có **1 skip** (ca sẵn có, không do lượt này); 8 bộ còn lại **0 skip**.
* Hai bộ **cổng** (#2, #9) có `unittest` tự kiểm XANH ngay cả trước khi sửa (`Ran 8 · OK`) —
  mã thoát của chúng là **mã của runner**, và runner đỏ vì `migrate`. Vì thế đọc "OK" mà bỏ mã
  thoát là đọc sai; bảng ghi cả hai.
* Tổng số ca của 9 bộ: `57+8+28+33+23+56+26+47+8 = **286**` — khớp đúng con số X2 đo được khi
  khai biến môi trường. Không ca nào bị xoá hay thêm.

Log thô: `/tmp/y1_kho/logs/truoc__*.log` (trước) và `/tmp/y1_kho/logs/sau__*.log` (sau),
`/tmp/y1_kho/logs/lap__thu_g21_bimat_*.log` (3 lượt lặp của #4).

---

## 4. ĐỐI CHỨNG ÂM — BỎ KHAI / KHO HỎNG THÌ BỘ THỬ PHẢI ĐỎ LẠI

Một bộ chỉ xanh vì có một lời khai **không được** là bộ xanh giả. Nên mỗi bộ bị bắt đỏ lại bằng
**hai kiểu độc lập**, không sửa tệp nào:

### 4.1 Kiểu A — "BỎ KHAI" (import hook, tệp bộ thử KHÔNG bị sửa)

Harness `/tmp/y1_kho/khong_khai.py` chèn một `MetaPathFinder`: ngay sau khi `cau_hinh` được nạp,
nó thay `khai_kho_kiem_thu` bằng hàm **rỗng** — không đặt `VIP_KHO_DANG_CHAY`, không đổi
`KHO_DANG_CHAY`. Chạy với `env -u VIP_KHO_DANG_CHAY`, cwd = gốc repo, **đúng tệp đang giao**
(không phải bản sao).

| Bộ | Exit | Ran | Kết quả | Bằng chứng đỏ |
|---|---:|---:|---|---|
| `thu_bao_mat.py` | **1** | 57 | `FAILED (failures=1)` | `TỪ CHỐI: CHƯA KHAI kho đang chạy` ở `test_e1_migrate_v4…` |
| `thu_g19_tich_hop.py` | **1** | 8 | tự kiểm `OK`, cổng ĐỎ | `EXIT_BO_DO=1` · `migrate.py hỏng (mã 1)` |
| `thu_g20_baomat.py` | 0 | 28 | `OK` | **không đỏ** — bộ này chỉ chạy hai bộ con, mà hai bộ con đã tự khai độc lập; xem kiểu B |
| `thu_g21_bimat.py` | **1** | 33 | `FAILED (failures=6)` | máy chủ con không lên (`CSDL ở schema v0`) |
| `thu_g22_bimat.py` | **1** | 23 | `FAILED (failures=4)` | cùng gốc |
| `thu_qa_g17.py` | **1** | 56 | `FAILED (errors=24)` | `moi_truong() → migrate.chay() → TỪ CHỐI` |
| `thu_qa_g18_tich_hop.py` | **1** | 26 | `FAILED (failures=3)` | `_MIGRATE` cấp mô-đun hỏng ⇒ cổng không lên |
| `thu_qa_g18.py` | **1** | 47 (1 skip) | `FAILED (failures=3, errors=12)` | `moi_truong() → migrate.chay() → TỪ CHỐI` |
| `thu_qa_g19_tich_hop.py` | 0 | 8 | `OK` | **không đỏ** — bản uỷ quyền chạy bộ gốc, mà bộ gốc đã tự khai độc lập; xem kiểu B |

**Đọc đúng chỗ "không đỏ":** hai bộ này **không** phải bộ xanh giả. Chúng là bộ **uỷ quyền**:
khi bỏ khai ở chúng, bộ con/bộ gốc vẫn tự khai (đó chính là điều lượt này làm), nên chúng vẫn
xanh — và điều đó chứng minh **bộ con không phụ thuộc vào bộ cha**. Để chứng minh **chính chúng**
có răng, dùng kiểu B dưới đây: chúng từ chối nền không cô lập ngay ở lời khai của mình.

### 4.2 Kiểu B — "KHO HỎNG" (trỏ nền dữ liệu vào cây repo)

Đặt biến nền của chính bộ thử trỏ vào `$GOC/app/du-lieu` (thư mục dữ liệu thật của ứng dụng).
`khai_kho_kiem_thu()` phải **TỪ CHỐI trước khi mở bất kỳ CSDL nào**, nên đây cũng là phép đo
chốt cô lập. (`app/du-lieu` **không tồn tại** trong worktree này; phép đo chỉ so tiền tố đường
dẫn, không tạo gì.)

| Bộ | Biến tiêm | Exit | Bằng chứng |
|---|---|---:|---|
| `thu_g19_tich_hop.py` | `VIP_HUB_DATA` | **1** | `[cau_hinh] TỪ CHỐI: VIP_HUB_DATA trỏ vào CÂY REPO (…/app/du-lieu)` |
| `thu_g20_baomat.py` | `VIP_G20_DATA` | **1** | cùng thông điệp |
| `thu_g21_bimat.py` | `VIP_G21_TAM_GOC` | **1** | cùng thông điệp |
| `thu_g22_bimat.py` | `VIP_G22_TAM_GOC` | **1** | cùng thông điệp |
| `thu_qa_g17.py` | `VIP_G17_DATA` | **1** | cùng thông điệp |
| `thu_qa_g18.py` | `VIP_G18_DATA` | **1** | cùng thông điệp |
| `thu_qa_g19_tich_hop.py` | `VIP_HUB_DATA` | **1** | cùng thông điệp |
| `thu_bao_mat.py` | — (bộ tự `mkdtemp`, không có biến nền) | — | đã đỏ bằng kiểu A |
| `thu_qa_g18_tich_hop.py` | — (bộ tự `mkdtemp`, không có biến nền) | — | đã đỏ bằng kiểu A |

**Kết luận:** **9/9 bộ có ít nhất một đối chứng âm làm chúng đỏ lại**; **5/9** bộ đỏ lại bằng **cả
hai** kiểu. Không tệp bộ thử nào bị sửa để làm phép đo này (harness nằm ngoài repo; kiểu B chỉ
đặt biến môi trường).

### 4.3 Đối chứng âm KHÔNG làm yếu bộ thử

* **Không xoá ca, không hạ ngưỡng, không `skipTest`.** Số ca trước và sau giống nhau từng bộ
  (bảng §3); skip duy nhất là skip sẵn có của `thu_qa_g18.py`.
* **Các phép tự kiểm bên trong bộ thử vẫn chạy và vẫn xanh** — gồm các nhóm đột biến
  (`thu_qa_g17.py::F_TuKiemBoDo`, `thu_qa_g18.py::J_TuKiemBoDo`, `thu_g21_bimat.py` nhóm G,
  `thu_g22_bimat.py` nhóm B, `thu_g20_baomat.py` nhóm T/B4/B5/C6…) và các đối chứng âm có sẵn
  của chúng.
* **Hai lỗi thật của X2 vẫn đỏ** trong lượt chạy toàn cây (§5): `thu_migrate_dong_thoi.py`
  (race `sao_luu`) và `thu_bien_driver.py` (biên driver). Lượt này **không** đụng vào chúng,
  nên chúng vẫn là bằng chứng các bộ thử còn bắt được lỗi sản phẩm thật.
* `app/cau_hinh.py` **không bị sửa**; git chỉ thấy 9 tệp bộ thử (và tệp tài liệu này).

---

## 5. CHẠY TOÀN CÂY — `sh app/thu/chay_tat_ca.sh`

Lệnh (đúng như X2 dùng; `python3` trên tệp `.sh` là sai cú pháp):

```sh
env -u VIP_KHO_DANG_CHAY sh app/thu/chay_tat_ca.sh
```

| Chỉ số | Trước (X2, cây sạch) | Sau (lượt này) |
|---|---:|---:|
| Mã thoát | 1 | **1** |
| Tệp `thu_*.py` dò được (trừ `thu_e2e.py`) | 70 (X2 đếm) | **71** |
| Bộ chạy thật | — | **70** |
| Bộ ✓ | 40 | **47** |
| Bộ ✗ | 30 | **23** (+ dòng **E2E ✗** riêng) |
| Bộ ⊘ (bỏ qua) | — | **1** (`thu_nhat_ky_yeu_cau.py`) |
| Tổng ca python | 485 ca nằm trong các bộ đỏ | **1967 ca** (toàn cây) |

Chi tiết thô: `python: 1967 ca · 70 bộ chạy thật`; `bộ hỏng (cuối)` gồm 23 tệp + `chay_e2e.sh`.
**Trong 9 bộ của lượt này: 8 bộ ✓** (`thu_bao_mat`, `thu_g20_baomat`, `thu_g21_bimat`,
`thu_g22_bimat`, `thu_qa_g17`, `thu_qa_g18_tich_hop`, `thu_qa_g18`, `thu_qa_g19_tich_hop`);
`thu_g19_tich_hop` đỏ **một lượt** do runner bên trong flake — chạy riêng 4/4 xanh, xem §6.1.

**22 bộ ✗ ngoài phạm vi** (cộng thêm `thu_g19_tich_hop` — bộ trong phạm vi bị flake §6.1 — và
dòng E2E riêng) chia đúng theo `docs/G22_PHAN_LOAI_DO.md` cộng thêm nhóm "cùng bệnh chưa tự khai"
mà lượt này **không được cấp phép ghi**:

| Nhóm | Bộ | Vì sao vẫn đỏ |
|---|---|---|
| **2 lỗi thật** (L) | `thu_migrate_dong_thoi.py`, `thu_bien_driver.py` | race `sao_luu()` · biên driver `sqlite3` — X2 đã xác định |
| **8 ghim cũ** (S) | `thu_g01_g02.py`, `thu_g19_route.py`, `thu_g20_dahang.py`, `thu_g20_saoluu.py`, `thu_g21_saoluu.py`, `thu_qa_soat.py`, `thu_g22_gioihan.py`, `thu_g22_chotcay.py` | ghim số/route/schema/API cũ; `thu_g22_chotcay.py` thêm tương tác d4 ở §6.3 |
| **E2E** (C) | `thu_qa_g22.py`, `thu_g22_e2e.py` + `chay_e2e.sh` | thiếu `chromium-1194` / cần máy chủ E2E |
| **Cùng bệnh chưa tự khai** (ngoài 9 bộ) | `thu_g17_baomat.py`, `thu_g18_maysrv.py`, `thu_g18_multiprocess.py`, `thu_g19_gioihan.py`, `thu_g21_gioihan.py`, `thu_giao_dich.py`, `thu_han_muc_nguyen_tu.py`, `thu_header_bao_mat.py`, `thu_truy_van.py`, `thu_qa_g21.py` | chính là 9 bộ Phụ lục A + `thu_qa_g21.py`: vẫn chưa tự khai nên vẫn đỏ khi **không** có dòng `export` toàn cục |

**Đây là phát hiện quan trọng cho lượt sau:** nếu chỉ khai kho bằng một dòng `export` trong
`chay_tat_ca.sh` thì 10 bộ cuối bảng cũng sẽ xanh — nhưng đó vẫn là "bộ thử phụ thuộc người chạy
nhớ khai". Muốn bỏ hẳn chế độ đó phải tự khai **từng bộ** (đúng việc lượt này làm cho 9 bộ đầu).
Lượt này **không** sửa 10 bộ ấy vì ngoài phạm vi.

---

## 6. GHI CHÚ ĐO — HAI FLAKE VÀ MỘT TƯƠNG TÁC NGOÀI PHẠM VI

### 6.1 `thu_g19_tich_hop.py` — runner bên trong flake một lượt trong toàn cây

Toàn cây ghi `✗ thu_g19_tich_hop.py 8 ca HỎNG (mã thoát 1)` nhưng **không có dòng `FAIL:` nào**:
8 ca tự kiểm XANH, chỉ `chay.sh` trả mã 1. Đo lại **4 lượt liên tiếp** sau toàn cây: **4/4 exit 0 ·
`Ran 8` · cổng ĐẠT `38/38` ca** (`/tmp/y1_kho/logs/lap__thu_g19_tich_hop_1..4.log`). Bộ đo bên
trong (`thu_g21_gioihan.py`) có các phép đo thời gian/tần suất nên có thể flake dưới tải; **không
phải do lời khai kho** (cùng lời khai, cùng cây, chạy riêng xanh 4/4). Bảng §3 ghi exit 0 theo
4 lượt chạy riêng; không sửa `thu_g21_gioihan.py`/`chay.sh` vì ngoài phạm vi.

### 6.2 `thu_g21_bimat.py` — flake dọn thư mục tạm có sẵn

Lượt chạy #4 ở bảng §3 có **1 FAIL** `Z_TongKet::test_z4_khong_con_thu_muc_tam_cua_bo_thu`:
`['vh-g21bimat-con-…','vh-g21bimat-goc-…'] != []`. Đây là **flake dọn thư mục tạm có sẵn của
chính bộ thử** (nó tự cảnh báo WAL có thể làm thư mục "mọc lại"; `don_sach_thu_muc()` có vòng
chờ), không phải do lời khai kho:

* lần chạy đầu sau sửa: exit 0 · 33 ca · 0 FAIL;
* lần chạy #4: exit 1 · 33 ca · 1 FAIL (z4);
* **3 lượt lặp liên tiếp sau đó: 3/3 exit 0 · 33 ca · 0 FAIL** (`/tmp/y1_kho/logs/lap__*`);
* toàn cây: **✓ 33 ca**;
* các thư mục `vh-g21bimat-*` đã được dọn sạch sau lượt chạy.

Vì vậy bảng §3 ghi **exit 0 · 33 ca** cho #4, kèm ghi chú này để không giấu lượt đỏ. Không sửa
`thu_g21_bimat.py` để "chéo" flake — nó ngoài nguyên nhân của lượt này và sửa nó là việc của
làn sở hữu bộ thử.

### 6.3 `thu_g22_chotcay.py::test_d4` — tương tác với MỌI sửa đổi chưa commit của 3 tệp cổng

Toàn cây ghi `✗ thu_g22_chotcay.py 11 ca · 1 FAIL (d4)`. **Đây là hậu quả trực tiếp của việc
lượt này sửa `thu_g20_baomat.py`, `thu_qa_g17.py`, `thu_qa_g18.py`** — ba trong bốn tệp mà d4
dùng làm "bản sao chốt cây sạch". Cơ chế (đọc mã, không đoán):

* `nguon_truoc_khi_va()` lấy **commit gần nhất có nội dung KHÁC tệp đang làm việc**;
* trên cây sạch, nó bỏ qua HEAD (trùng nội dung) và lấy bản **trước bản vá** — bản này FAIL
  `kiem_quy_tac`, nên d4 ĐẠT;
* khi tệp bị sửa **chưa commit**, bản "trước" chính là HEAD — mà HEAD đã là bản ĐẠT
  `kiem_quy_tac` ⇒ d4 FAIL, dù bản sửa của ta không đụng logic miễn trừ.

Đo đối chứng: **hoàn nguyên 9 tệp về HEAD (băm từng tệp khớp lại sau khi phục hồi) ⇒
`thu_g22_chotcay.py` exit 0 · 11 ca · OK**; chỉ cần một trong ba tệp trên bị sửa là d4 đỏ
(hoàn nguyên riêng `thu_g20_baomat.py` thì nó chuyển sang báo `thu_qa_g17.py`). Vì vậy:
**không phải lỗi sản phẩm, không phải lời khai kho, và không thể tránh nếu vẫn phải sửa ba tệp
ấy mà không commit** (lượt này không ghi `.git`). Đề xuất cho làn sở hữu `thu_g22_chotcay.py`:
d4 nên lùi tới bản commit **cuối cùng mà `kiem_quy_tac` FAIL** (hoặc bỏ qua tệp đang có thay đổi
chưa commit) thay vì chỉ lấy "một bản trước".

---

## 7. RÀNG BUỘC ĐÃ GIỮ

| Ràng buộc | Bằng chứng |
|---|---|
| Không sửa `app/cau_hinh.py` · `app/migrate.py` | `git status --porcelain -uall` chỉ có 9 tệp `app/thu/thu_*` (M) + `docs/Y1_KHAI_KHO.md` (??) |
| Không sửa `app/thu/chay_tat_ca.sh` | không có trong `git status` |
| Không xoá ca / hạ ngưỡng / `skipTest` | số ca từng bộ không đổi (§3); chỉ 1 skip sẵn có |
| Không dùng DB thật | mọi bộ dùng `tempfile.mkdtemp`; `app/du-lieu` không tồn tại |
| Local-first, không push/deploy/gọi hãng | mọi HTTP chỉ loopback; không lệnh mạng ra ngoài |
| Không tự bấm duyệt sandbox | không có thao tác xin quyền |
| Không ghi `.git` | không commit/tag; `git status` chỉ đọc |

---

## 8. VIỆC CÒN LẠI (NGOÀI PHẠM VI Y1)

1. **Sửa 2 lỗi thật** X2 đã xác định: race `sao_luu()` (`thu_migrate_dong_thoi.py`) và biên
   driver `sqlite3` trong `migrate.py` (`thu_bien_driver.py`). Hai bộ này vẫn đỏ có chủ đích.
2. **Cập nhật các ghim cũ**: schema 9 → 10 (`thu_g20_saoluu.py`, `trien_khai/g20-saoluu/…`),
   route 103 → 104 / khoảng trống 31 → 32 (`thu_g19_route.py`), số hàm/số dòng
   (`thu_g20_dahang.py`), nhận 400 (`thu_g01_g02.py`, `thu_qa_soat.py`), kỳ vọng C5 hai ứng viên
   (`thu_g22_gioihan.py`), tiền điều kiện "cây bẩn" (`thu_g22_chotcay.py`).
3. **`thu_qa_g22.py`** cần `chromium-1194` để đo vế E2E — hiện là (C), chưa kết luận.
4. **Flake z4 của `thu_g21_bimat.py`** (§6.2) và **flake runner của `thu_g19_tich_hop.py`**
   (§6.1) — làn sở hữu bộ thử nên làm ổn định; lượt này không sửa vì ngoài phạm vi.
5. **`thu_g22_chotcay.py::d4`** (§6.3) — cần sửa heuristic "bản trước" để chấp nhận tệp đang
   sửa chưa commit, hoặc chuyển phép đo sang một commit/bản sao. Đây là chỗ **duy nhất** trong
   toàn cây bị đỏ **thêm** vì chính 3 tệp của lượt này bị sửa — không phải lỗi sản phẩm.
6. **10 bộ "cùng bệnh chưa tự khai"** (9 bộ Phụ lục A + `thu_qa_g21.py`) — nếu muốn bỏ hẳn dòng
   `export` trong `chay_tat_ca.sh` thì phải tự khai từng bộ như lượt này. Cần một dispatch riêng
   vì ngoài phạm vi Y1.

**Không được làm:** nới cổng `KHO_DANG_CHAY` để bộ thử xanh; đặt `export VIP_KHO_DANG_CHAY` trong
`chay_tat_ca.sh` thay cho việc từng bộ tự khai (cách đó vẫn làm bộ thử phụ thuộc người chạy).

---

## 9. LỆNH TÁI LẬP

```sh
# 1. Từng bộ (KHÔNG đặt VIP_KHO_DANG_CHAY)
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_bao_mat.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_g19_tich_hop.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_g20_baomat.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_g21_bimat.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_g22_bimat.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_qa_g17.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_qa_g18_tich_hop.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_qa_g18.py
env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_qa_g19_tich_hop.py

# 2. Toàn cây
env -u VIP_KHO_DANG_CHAY sh app/thu/chay_tat_ca.sh; echo "exit=$?"

# 3. Đối chứng âm kiểu A — bỏ khai bằng import hook (không sửa tệp)
env -u VIP_KHO_DANG_CHAY python3 /tmp/y1_kho/khong_khai.py app/thu/thu_bao_mat.py

# 4. Đối chứng âm kiểu B — kho hỏng (ví dụ bộ QA G17)
env VIP_G17_DATA="$PWD/app/du-lieu" python3 app/thu/thu_qa_g17.py; echo "exit=$?"
```

> `GIT_CONFIG_*` dị dạng của máy này (N-G18-00) phải được gỡ trước khi đo — `chay_tat_ca.sh` tự
> gỡ; các lệnh trên nên chạy trong shell đã `unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0
> GIT_CONFIG_KEY_1 GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1`.

---

## 10. PHỤ LỤC — MÃ HARNESS ĐỐI CHỨNG ÂM KIỂU A

Harness `/tmp/y1_kho/khong_khai.py` (chạy ngoài repo; **không** sửa tệp bộ thử). Nó thay
`cau_hinh.khai_kho_kiem_thu` bằng hàm rỗng ngay sau khi mô-đun `cau_hinh` được nạp:

```python
import importlib.abc, importlib.machinery, os, runpy, sys
os.environ.pop("VIP_KHO_DANG_CHAY", None)

class _ThayKhai(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != "cau_hinh":
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return None
        goc_exec = spec.loader.exec_module

        def exec_module(module):
            goc_exec(module)

            def khong_khai(*_a, **_k):
                os.environ.pop(module.BIEN_KHAI_KHO, None)
                module.KHO_DANG_CHAY = None
                return None

            module.khai_kho_kiem_thu = khong_khai

        spec.loader.exec_module = exec_module
        return spec

sys.meta_path.insert(0, _ThayKhai())
bo_thu = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(bo_thu, run_name="__main__")
```

Chạy:

```sh
env -u VIP_KHO_DANG_CHAY python3 /tmp/y1_kho/khong_khai.py app/thu/thu_bao_mat.py
# exit 1 · Ran 57 · TỪ CHỐI: CHƯA KHAI kho đang chạy
```
