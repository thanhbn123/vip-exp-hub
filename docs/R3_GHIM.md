# R3 — GHIM SỰ THẬT MÔI TRƯỜNG: BỎ SỐ CŨ, GIỮ BẤT BIẾN

Ngày đo: **19/10/2026** · Nhánh `r3-ghim` trên `best/integration` @ `c909ebb` · `main = de740dc` **KHÔNG dùng**.
Phạm vi: `app/thu/thu_g20_dahang.py`, `app/thu/thu_g20_saoluu.py`, `app/thu/thu_qa_g18.py` (chỉ đọc/không phải sửa),
`app/thu/thu_g22_gioihan.py`, `app/thu/thu_r3_ghim.py` (mới), `docs/R3_GHIM.md` (mới).
**Không sửa mã sản phẩm.** `git diff --name-only` chỉ có tệp thử/tài liệu (xem §7).

---

## 0. KẾT LUẬN NGẮN

| Bộ | Trước sửa | Sau sửa | Ghi chú |
|---|---|---|---|
| `thu_g20_dahang.py` | exit 1 · Ran 27 · **3 HỎNG** | **exit 0 · Ran 27 · 27 ĐẠT** | bỏ ghim `CHUNG=30`, 4 số dòng, 4 tọa độ nhánh |
| `thu_g20_saoluu.py` | exit 1 · Ran 41 · **1 HỎNG** | **exit 0 · Ran 41 · 41 ĐẠT** | bỏ ghim schema `9`; đọc schema nguồn tại chỗ |
| `thu_qa_g18.py` | exit 1 · Ran 47 · **3 HỎNG** · 1 bỏ qua | **exit 1 · Ran 47 · 1 HỎNG** · 1 bỏ qua | G2 đã xanh (40 ca, exit 0); B1 còn ĐỎ vì lý do NGOÀI R3 (xem §6) |
| `thu_g22_gioihan.py` | exit 1 · 32 mục = 27 ĐẠT + **3 HỎNG + 2 KHUYẾT** | **exit 0 · 32 mục = 32 ĐẠT** | cô lập fixture C5, chốt hợp đồng OR/AND |
| `thu_r3_ghim.py` (mới) | — | **exit 0 · Ran 9 · 9 ĐẠT** | tự kiểm bản vá + đối chứng âm/dương |

Không xoá ca, không bỏ assertion, không thêm `skip`, không nuốt exception, không đổi mã thoát cho xanh.
Số ca được đếm từ output thật của từng bộ; `Ran N` của unittest **gồm** ca bỏ qua, nên cột bỏ qua ghi riêng.

---

## 1. LỖI TRƯỚC KHI SỬA — LỆNH THẬT, MÃ THOÁT THẬT

Mọi lượt chạy từ gốc kho, `VIP_HUB_DATA` là thư mục tạm **bên trong** `$TMPDIR` (không dùng `/tmp` trực tiếp —
`thu_g21_gioihan` từ chối dữ liệu ngoài thư mục tạm), `VIP_HUB_BIND=127.0.0.1`,
`VIP_JT_MOI_TRUONG=mock`, `PYTHONDONTWRITEBYTECODE=1`, `GIT_CONFIG_*` đã gỡ (N-G18-00).

| Bộ | Exit | `Ran` | ĐẠT | HỎNG | Bỏ qua | Lỗi đầu |
|---|---:|---:|---:|---:|---:|---|
| `thu_g20_dahang.py` | 1 | 27 | 24 | **3** | 0 | `{'CHUNG': 38, 'DAC_THU_JT': 7} != {'CHUNG': 30, 'DAC_THU_JT': 7}` |
| `thu_g20_saoluu.py` | 1 | 41 | 40 | **1** | 0 | `10 != 9 : phiên bản schema sau khôi phục khác 9` |
| `thu_qa_g18.py` | 1 | 47 | 43 | **3** | 1 | B1 Chromium/Playwright; G2 `11 != 10` |
| `thu_g22_gioihan.py` | 1 | 32 mục | 27 | **3** | 0 | B3.a/b/c: C5 vẫn `1/2 · DONG` khi tiêm 1 ứng viên |

Ba lỗi G20 đa hãng cụ thể (đo được):

- `test_a2`: bảng hàm thật là `{'CHUNG': 38, 'DAC_THU_JT': 7}` (45 hàm), không phải `30/7`.
- `test_a6`: bốn dòng nhãn hãng thật là `[108, 115, 116, 1035]`, không phải `(108, 115, 116, 831)`.
- `test_a7`: bốn nhánh ràng buộc hãng thật ở dòng `[285, 311, 344, 946]` trong các hàm
  `_gia_tri_trong_json`, `_gia_tri_bi_mat_trong_json`, `_gia_tri_bi_mat_tu_phan_hoi`, `tach_url`,
  không phải `[285, 311, 343, 742]`.

Đây là **số dòng dịch chuyển**, không phải hành vi sản phẩm đổi. Ghim tọa độ dòng biến mọi lần sửa mã
thành ĐỎ giả.

---

## 2. BẢNG “GHIM CŨ → BẤT BIẾN MỚI”

| # | Tệp / ca | Ghim cũ | Số đo cũ | Bất biến mới | Đo bằng |
|---|---|---|---|---|---|
| 1 | `thu_g20_dahang.py::test_a2` | `{"CHUNG": 30, "DAC_THU_JT": 7}` | `38/7` (45 hàm) | **Phân hoạch theo bằng chứng**: `DAC_THU_JT ⇔ hang_dac_thu != []`; `CHUNG ⇔ hang_dac_thu == []`; hai tập phủ đúng `len(ham)`; hai chốt chặn và 8 hàm lõi neo bằng **tên** | `PT.phan_tich()` + đối chiếu từng hàm |
| 2 | `thu_g20_dahang.py::test_a6` | `(108, 115, 116, 831)` | `[108, 115, 116, 1035]` | **Hai nguồn độc lập phải khớp**: bộ dò sản phẩm `PT.phan_tich` và phép quét AST viết trong ca thử (`_nhan_hieu_doc_lap`) phải ra **cùng tập dòng**; mỗi dòng phải có literal chuỗi thật chứa `trich`; docstring bị loại | AST hai lần, độc lập |
| 3 | `thu_g20_dahang.py::test_a7` | `[285, 311, 343, 742]` | `[285, 311, 344, 946]` | **Dòng phải nằm TRONG hàm nó khai** (`lineno..end_lineno`); hằng đặc thù phải được dùng trong thân hàm; nhánh phải có ≥ 1 lệnh; tập hàm neo bằng tên, không bằng dòng | AST + `_vung_ham` |
| 4 | `thu_g20_saoluu.py::test_a5` | `phien_ban_sau == 9` | `10` | **Schema khôi phục phải BẰNG schema NGUỒN**, đọc tại chỗ từ `_truoc["phien_ban"]`; không ghim 9 hay 10 | `kich_ban.ca_vong_tron()` |
| 5 | `thu_frontend/thu_http.py::test_04` | `len(ten_trang) == 10` | `11` | **Đọc danh sách từ đĩa**, khác rỗng, và **mọi trang** tải được + dùng `assets/css/style.css` + `assets/js/app.js`; số trang là kết quả đo, không phải kỳ vọng | `os.listdir(pages)` + HTTP thật |
| 6 | `thu_g22_gioihan.py::b3_chieu_do` (fixture C5) | tiêm 1 trong 2 ứng viên ⇒ đòi C5 ĐỎ | C5 vẫn `1/2 · DONG` | **C5 là OR**: `chay = min(Σ(ứng viên chạy thật & thoát 0), 1)`. Đo chiều ĐỎ bằng cách **cô lập danh sách còn đúng bản uỷ quyền** rồi mới tiêm; trả lại trong `finally` + đối chiếu tồn tại | Chính `thu_qa_g20.py` (chỉ đọc) |

### Vì sao bất biến #4 đúng hơn “9”
`ca_vong_tron()` gieo dữ liệu bằng chính `migrate` hiện tại rồi `sao_luu()` → `khoi_phuc()`. Câu hỏi là
“bản khôi phục có giữ đúng phiên bản của **nguồn** không”, không phải “phiên bản có bằng số 9 của lượt G20 không”.
Khi migration lên v10, vế trái vẫn đúng; ghim 9 thì sai. Trong lượt này nguồn là **10**, khôi phục là **10**.

### Vì sao bất biến #5 đúng hơn “10”
`pages/` hiện có **11** tệp `.html`; `best.html` là trang thứ 11. Bản cũ ĐỎ dù **không trang nào gãy**.
Bất biến mới không cấm thêm trang; nó chỉ cấm **phép đo rỗng** và cấm **một trang không tải được / không dùng CSS-JS chung**.

---

## 3. ĐỐI CHỨNG ÂM — TIÊM LẠI GHIM CŨ, PHÉP THỬ PHẢI ĐỎ

Mỗi phép dưới đây **chỉ thêm một assertion cũ** vào bản đang xanh, chạy lại, rồi phục hồi tệp bằng `cp`
và `cmp` (đã xác nhận `RESTORED_OK`).

| Đối chứng âm | Lệnh (rút gọn) | Exit | Bằng chứng |
|---|---|---:|---|
| Ghim số hàm `30/7` | thêm `assertEqual(dem, {"CHUNG": 30, "DAC_THU_JT": 7})` vào `test_a2`; `python3 app/thu/thu_g20_dahang.py CaRanhGioi` | **1** | `AssertionError: {'CHUNG': 38, 'DAC_THU_JT': 7} != {'CHUNG': 30, 'DAC_THU_JT': 7}` · Ran 7 · failures=1 |
| Ghim schema `9` | thêm `assertEqual(phien_ban_sau, 9)` vào `test_a5`; `python3 app/thu/thu_g20_saoluu.py A_VongTronTrenDuLieuThat` | **1** | `AssertionError: 10 != 9 : R3 NEGATIVE CONTROL` · Ran 5 · failures=1 |
| Ghim `10` trang | thêm `assertEqual(len(ten_trang), 10)` vào `test_04`; `python3 thu_frontend/thu_http.py ThuFrontendHTTP.test_04_moi_trang_demo_g00_khong_bi_pha` | **1** | `AssertionError: 11 != 10 : R3 NEGATIVE CONTROL` · Ran 1 · failures=1 |
| Ghim dòng nhãn `831` / nhánh `[285,311,343,742]` | `thu_r3_ghim.py::test_08` đưa từng ghim cũ trở lại dưới `assertRaises(AssertionError)` | **0** (9/9 ĐẠT) | Cả hai assertion cũ đều ném `AssertionError` trên số đo hiện tại — nếu một ghim bỗng khớp lại, ca này ĐỎ |
| Fixture C5 cũ (không cô lập) | lượt **trước sửa** trên cùng cây: tiêm 1 ứng viên, C5 vẫn `1/2` | **1** | 32 mục = 27 ĐẠT + **3 HỎNG** (B3.a/b/c) + **2 KHUYẾT** (B3.d/d2) |

Đối chứng âm của C5 sau sửa nằm ngay trong B3: sau khi cô lập còn `['thu_qa_g19_tich_hop.py']`,
mỗi phép tiêm cho **`0/1`** và C5 **ĐỎ** (exit 1). Đây là cùng một phép tiêm, khác điều kiện fixture.

---

## 4. ĐỐI CHỨNG DƯƠNG — ĐƯỜNG HỢP LỆ PHẢI ĐẠT

| Đối chứng dương | Kết quả |
|---|---|
| G20 đa hãng chạy đủ bộ | **exit 0 · Ran 27 · OK** (99,2 giây) |
| G20 sao lưu chạy đủ bộ | **exit 0 · Ran 41 · OK** (12,0 giây) |
| QA G18 — G2 chạy `thu_frontend/thu_http.py` | **exit 0 · 40 ca** (1,9 giây), dòng `[G2] ... mã thoát 0 · 40 ca` |
| C5 với bản uỷ quyền lành | **`1/2 · DONG`**, exit 0 (B2) — đúng hợp đồng OR |
| `thu_r3_ghim.py::test_09` chạy riêng ca trang demo | **Ran 1 · OK**, exit 0 |
| `thu_r3_ghim.py` toàn bộ | **exit 0 · Ran 9 · OK** (2,0 giây) |

---

## 5. C5 — HỢP ĐỒNG OR/AND, VÀ KẾT LUẬN “CÓ BỎ LỌT LỖI KHÔNG?”

### Hợp đồng đo được (đọc từ `app/thu/thu_qa_g20.py`, KHÔNG sửa tệp đó)

```python
ung_vien = sorted(t for t in os.listdir(GOC_THU) if re.match(r"thu_qa_g19.*\.py$", t))
...
chay = min(sum(1 for _, ma, n, bq, nc in chi_tiet
               if ma == 0 and n > 0 and nc > 0), 1)
dat, vi = dat_cong("bo-g19-tong-hop", chay)
```

`min(..., 1)` là **OR** trên danh sách ứng viên: chỉ cần **một** ứng viên chạy thật + thoát 0 là cổng xanh.
Vì vậy:

- Với **2 ứng viên**, tiêm hỏng **một** ứng viên ⇒ C5 in `1/2 · DONG` và exit 0. **Đó là đúng hợp đồng OR**,
  không phải bằng chứng C5 bắt được lỗi.
- Muốn C5 **ĐỎ** trên một cây có 2 ứng viên, phải làm **cả hai** hỏng (AND của các thất bại), hoặc **cô lập**
  danh sách còn một ứng viên rồi tiêm. Fixture chọn cách cô lập: chuyển `thu_qa_g19.py` ra khỏi khuôn tên
  `thu_qa_g19.*.py` trong lúc chạy B3, sau đó trả lại + `assert` tồn tại.

### Số đo

| Lượt | Ứng viên C5 | B2 (lành) | B3 (tiêm) | Kết luận |
|---|---|---|---|---|
| Trước sửa | `thu_qa_g19.py`, `thu_qa_g19_tich_hop.py` | `1/2` DONG | `1/2` DONG cả 5 phép tiêm | C5 **không** đổi màu; 3 HỎNG + 2 KHUYẾT |
| Sau sửa — B2 | 2 ứng viên | `1/2` DONG | — | OR: một ứng viên còn xanh là đủ |
| Sau sửa — B3 | **1 ứng viên** (`thu_qa_g19_tich_hop.py`) | — | **`0/1`**, exit 1, cả 5 phép tiêm | C5 **bắt được** lỗi khi chỉ còn ứng viên đó |

**Kết luận thẳng:** C5 **có bắt lỗi** của bản uỷ quyền khi nó là ứng viên duy nhất (hoặc khi mọi ứng viên đều hỏng).
C5 **không bắt lỗi** của một ứng viên nếu một ứng viên khác vẫn xanh — đó là **giới hạn phạm vi của cổng OR**,
không phải lỗi của bản uỷ quyền. Muốn C5 canh **từng** ứng viên thì phải sửa `thu_qa_g20.py` (AND / lọc danh sách);
tệp đó **ngoài phạm vi R3** — báo AG-00 quyết định. Fixture R3 chỉ **cô lập để đo**, không sửa C5.

---

## 6. CÒN LẠI — KHÔNG TỰ SỬA, BÁO AG-00

### 6.1 QA G18 — B1 còn ĐỎ vì danh sách trang Playwright, không phải vì R3
`thu_giao_dien/chay.sh` chạy **80 ca Playwright**: **75 đạt, 1 hỏng, 4 không chạy**, exit 1.
Ca hỏng: `10_trang_tinh_du_lieu.spec.js::01` — trên đĩa **11 trang**, bảng khai `TRANG` chỉ **10**;
`best.html` (trang thứ 11) chưa được khai. Đây là **danh sách viết tay** trong
`thu_giao_dien/10_trang_tinh_du_lieu.spec.js`, không phải bản ghim 10 trang của `thu_frontend/thu_http.py` (đã sửa).
Sửa nó cần thêm `best` vào `TRANG` **và** thêm lớp `.khung` cho `pages/best.html` (mã giao diện) — ngoài phạm vi R3.
**Không sửa**; giữ ĐỎ làm R7/AG-00. (Trong lượt QA gốc, B1 ĐỎ vì Chromium bị sandbox chặn; trong lượt này Chromium
chạy được nên lộ thêm lỗi danh sách trang.)

### 6.2 `thu_qa_g18.py` skip 1 ca
`H_Postgres.test_h3_chay_tron_tren_cum_rieng` tự bỏ qua ở làn mặc định (`VIP_G18_DAY_DU=1` mới chạy trọn).
Đây là skip **có sẵn**, không phải skip R3 thêm.

### 6.3 Số ca `thu_g20_saoluu.py` phụ thuộc môi trường
Lượt này `Ran 41`, 0 bỏ qua: 6 ca `K_PostgreSQL` chạy được trên cụm tạm của máy này.
Báo cáo QA gốc đo `Ran 35`, 1 bỏ qua vì sandbox chặn `shmget` (R7). **Không cộng hai số**; đây là hai môi trường
khác nhau. Sửa `test_a5` không liên quan tới việc PostgreSQL có chạy được hay không.

### 6.4 Phạm vi tệp: G2 nằm ngoài danh sách R3
Bản ghim `10` trang **không nằm** trong `app/thu/thu_qa_g18.py`; nó nằm trong `thu_frontend/thu_http.py`.
`app/thu/thu_qa_g18.py` chỉ gọi tiến trình con và đòi exit 0 — không thể sửa gốc tại đó. Đã hỏi coordinator
(`msg_429569c8dd1a`), chờ 600 giây không trả lời; đã sửa đúng một tệp `thu_frontend/thu_http.py` vì đề bài
yêu cầu “đếm tại chỗ, không ghim 10 hay 11”. **Đây là tệp ngoài danh sách PHẠM VI — coordinator cần xác nhận.**
Không sửa `thu_giao_dien/10_trang_tinh_du_lieu.spec.js`.

---

## 7. TỆP ĐÃ SỬA / KHÔNG SỬA

```
$ git status --short
 M app/thu/thu_g20_dahang.py
 M app/thu/thu_g20_saoluu.py
 M app/thu/thu_g22_gioihan.py
 M thu_frontend/thu_http.py
?? app/thu/thu_r3_ghim.py
?? docs/R3_GHIM.md
```

- **Không** sửa `app/http_jt.py`, `app/migrate.py`, `app/csdl.py`, `app/server.py` hay bất kỳ mã sản phẩm nào.
- **Không** sửa `chay_tat_ca.sh` (R6), `thu_qa_g16/jt/soat/tich_hop` (R2), `thu_g21_bimat`/`thu_g22_chotcay` (R27).
- Không push/deploy, không gọi API hãng, không credentials, không mở LIVE, không sửa CSDL nghiệp vụ.

### 7.1 Commit bị chặn — BÁO AG-00

Lượt này **chưa commit** vì file sandbox chặn ghi `.git/index.lock`:

```text
$ git add ... && git commit -m "AGENT R3 ..."
fatal: Unable to create
'/Users/viporder/Projects/vip-express-hub/.git/worktrees/r3-ghim/index.lock':
Operation not permitted
exit 128
```

Không có `index.lock` tồn tại trước lệnh; đây là chặn quyền ghi của sandbox, không phải lock mồ côi.
**Đề nghị AG-00 commit trên worktree `r3-ghim`** với đúng sáu tệp ở trên. Mọi thay đổi đang nằm trong
working tree (chưa staged) và đã được đo bằng các lệnh ở §8.

---

## 8. LỆNH CHẠY LẠI

```sh
# G20 đa hãng
D=$(mktemp -d)
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA="$D" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_g20_dahang.py

# G20 sao lưu
D=$(mktemp -d)
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA="$D" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_g20_saoluu.py

# QA G18 (G2 là tầng 2; B1 là tầng 3 Playwright)
D=$(mktemp -d)
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA="$D" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_qa_g18.py

# G22 giới hạn / C5
D=$(mktemp -d)    # phải nằm trong $TMPDIR, không dùng /tmp trực tiếp
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA="$D" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_g22_gioihan.py

# Bộ tự kiểm R3
D=$(mktemp -d)
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    VIP_HUB_DATA="$D" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/thu_r3_ghim.py
```

Bộ tự kiểm phân loại (`app/thu/thu_qa_nguyennhan.py`, worktree `qa-nguyennhan`) chạy **exit 0 · Ran 34 · OK**
trong lượt đối chiếu; R3 không sửa logic phân loại nên đây chỉ là kiểm tra hồi quy, không phải bằng chứng cho bản vá.

---

## 9. GIỚI HẠN CỦA LƯỢT ĐO NÀY

- Không chứng minh sản phẩm không còn lỗi R5; R3 chỉ sửa **kỳ vọng cũ**.
- B1 Playwright, PostgreSQL `shmget`, Chromium/Mach bootstrap vẫn là R7 — không tự duyệt sandbox.
- C5: kết luận OR/AND ở §5 là **đọc từ mã nguồn + đo qua chính C5**; không sửa C5.
- Mọi con số ở trên là của **một lượt chạy** trên cây `r3-ghim` @ `c909ebb`; không dùng làm số tổng của toàn bộ hồi quy.
