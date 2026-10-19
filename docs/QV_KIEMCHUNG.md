# QV-01 — KIỂM CHỨNG ĐỘC LẬP BA NHÓM R1 / R2 / R27 TRƯỚC KHI GỘP

**Người đo:** AG-01 (QA kiểm chứng độc lập) · **Ngày:** 19/10/2026 (giờ VN)
**Cây đo:** `qv1-kiemchung` · **Máy:** Darwin arm64 · **Python:** 3.9.6
**Nền của ba nhánh:** `best/integration @ c909ebb`
**Fork-point với cây chính:** `c909ebb → 5429c6d` (cây chính đi trước 2 commit: chỉ thêm
`app/thu/thu_qa_nguyennhan.py`, `docs/QA_NGUYENNHAN.md`, `docs/DINHCHINH_R6.md` — **không**
đụng tệp nào của ba nhóm).

---

## 0. PHÁN QUYẾT

| Nhóm | Nhánh | Phán quyết | Căn cứ bằng số | Điều kiện / việc còn lại |
|---|---|---|---|---|
| R1 | `r1-bootstrap` | **ĐẠT** | 3/3 bộ xanh (21/21 · 50/50 · 41/41) + bộ tự kiểm 11/11; gỡ lời khai ⇒ cả 3 đỏ lại đúng chữ ký | không |
| R2 | `r2-hopdong` | **ĐẠT CÓ ĐIỀU KIỆN** | 3/4 bộ xanh (61 · 22 · 30) + harness 12/12; `thu_tich_hop` còn **đúng 1 đỏ** `test_09` (R7) | (a) R7 cần AG-00 chốt; (b) bộ dò G16 có **1 lỗ hổng mới** `SECRET_KEY = "<câu 4 từ>"` |
| R27 | `r27-isolation` | **ĐẠT CÓ ĐIỀU KIỆN** | 2/2 bộ xanh (33 · 11) + harness 4/4; 2 lượt G21 song song cùng TMPDIR đều 33/33 | (a) Z4 **không còn** canh rác của lượt trước; (b) D4 chọn "bản bị bắt gần nhất", không phải "bản ngay trước" |

**Không nhóm nào sửa mã sản phẩm.** Cả ba chỉ sửa tệp thử + thêm báo cáo. Số ca **không giảm**
ở bất kỳ bộ nào; **không** thêm `skip`, **không** có `assertTrue(True)`, **không** nuốt
exception. Có **ba** kỳ vọng bị đổi: hai ca `200 → 400` (R1 `test_010`, R2 `test_q09f`) và
một ca rollback-vô-điều-kiện → rollback-theo-chốt (R1 `test_014`) — cả ba **có tài liệu hợp
đồng + đối chứng dương**, xem §4.1; **không** phải đổi số cho khớp output.

---

## 1. TRẠNG THÁI GIT — HEAD TRƯỚC/SAU VÀ TỆP SỬA

Cả ba nhánh **không có commit mới**: HEAD trước = HEAD sau = `c909ebb`, `git diff --cached`
rỗng. Toàn bộ thay đổi nằm ở **working tree chưa commit** (agent bị chặn ghi `.git`; tôi chỉ
đọc trạng thái, không thử ghi `.git`). Vì vậy mọi lượt "trước" bên dưới chạy trên **bản clone
sạch của `c909ebb`**, không phải trên cây đang sửa.

| Nhóm | HEAD trước | HEAD sau | Tệp sửa (`M`) | Tệp mới (`??`) | Tệp sản phẩm bị sửa |
|---|---|---|---|---|---|
| R1 | `c909ebb` | `c909ebb` | `app/thu/thu_g01_g02.py` · `app/thu/thu_g19_route.py` · `app/thu/chay_e2e.sh` | `app/thu/thu_r1_bootstrap.py` · `docs/R1_BOOTSTRAP.md` | **0** |
| R2 | `c909ebb` | `c909ebb` | `thu_qa_g16.py` · `thu_qa_jt.py` · `thu_qa_soat.py` · `thu_tich_hop.py` | `thu_r2_hopdong.py` · `docs/R2_HOPDONG.md` | **0** |
| R27 | `c909ebb` | `c909ebb` | `thu_g21_bimat.py` · `thu_g22_chotcay.py` | `thu_r27_fixture.py` · `docs/R27_FIXTURE.md` | **0** |

`git diff --stat` khớp đúng danh sách trên (R1 190+ / R2 187+ / R27 206+ dòng). Không có tệp
nào ngoài phạm vi bị chạm.

**PHƯƠNG PHÁP ĐO (chống sửa cây của nhóm):** mỗi nhóm được dựng lại trong `/tmp` bằng
`git clone` tại `c909ebb` + `git apply` đúng `git diff` của nhánh + chép nguyên các tệp
`??`. Cây thật của ba nhóm **không bị ghi** trong suốt lượt kiểm chứng (đã đối chiếu lại
`git status` sau khi chạy: vẫn đúng 3+2 / 4+2 / 2+2 tệp như bảng trên).

---

## 2. MÔI TRƯỜNG VÀ LỆNH ĐO

Mọi lượt chạy dùng đúng một khuôn (mã thoát lấy trực tiếp từ tiến trình):

```sh
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 -u VIP_KHO_DANG_CHAY \
    VIP_HUB_DATA="$(mktemp -d)" VIP_HUB_BIND=127.0.0.1 VIP_JT_MOI_TRUONG=mock \
    PYTHONDONTWRITEBYTECODE=1 python3 app/thu/<bộ>.py
```

- `VIP_KHO_DANG_CHAY` **không đặt** (đúng điều kiện "người chạy quên khai") — trừ lượt chẩn
  đoán có ghi rõ.
- Biến `GIT_CONFIG_*` hỏng của máy (`GIT_CONFIG_COUNT=2` thiếu `KEY_0/1`) được gỡ, nếu không
  mọi `git` con chết với `Exit 128`. Đây là lỗi **môi trường**, đã tái hiện được (§3.2).
- Không mạng, không hãng, không credential, không PostgreSQL, không API trả phí.

---

## 3. KIỂM CHỨNG TỪNG NHÓM (6 mục bắt buộc)

### 3.0. BẢNG 3 NHÓM × 6 MỤC

| Mục | R1 `r1-bootstrap` | R2 `r2-hopdong` | R27 `r27-isolation` |
|---|---|---|---|
| **(1) HEAD trước/sau + tệp sửa** | `c909ebb → c909ebb`; 3 M + 2 ??; **0** tệp sản phẩm | `c909ebb → c909ebb`; 4 M + 2 ??; **0** | `c909ebb → c909ebb`; 2 M + 2 ??; **0** |
| **(2) Lệnh · môi trường · exit · ca TRƯỚC/SAU** | g01 `1/21`→`0/21`; g19 `1/14`→`0/50`; e2e `1/0`→`0/41`; tự kiểm mới `0/11` | g16 `1/61`→`0/61`; jt `1/22`→`0/22`; soát `1/30`→`0/30`; tích hợp `1/12`→`1/12` (chỉ R7); harness `0/12` | g21 `1/33`→`0/33`; g22 `1/11`→`0/11`; harness `0/4` |
| **(3) ĐỐI CHỨNG ÂM (tiêm lỗi phải ĐỎ)** | gỡ lời khai ⇒ g01 `exit 1 · 1 FAIL`; g19 `exit 1 · 13 ERROR`; e2e `exit 1 · 0 byte` | tiêm `http.client` ⇒ jt+tích hợp ĐỎ; tiêm secret ⇒ g16 ĐỎ; máy chủ trả 200 ⇒ q09f ĐỎ | gốc tạm dùng chung ⇒ Z4 ĐỎ; bản sao sạch ⇒ D2 báo `SẠCH TRƠN` + 4 lỗi; bản "gần nhất" 3/4 ĐẠT ⇒ D4 cũ sai |
| **(4) ĐỐI CHỨNG ĐƯỜNG (đường hợp lệ phải ĐẠT)** | e2e `41/41`; rollback có cờ `exit 0` về v1 rồi lên lại v10; 3 chốt cô lập helper đúng | `urllib.parse` được tha; query hợp lệ `200`; tenant B không thấy đơn A | 2 lượt G21 **song song** cùng TMPDIR đều `33/33`; thư mục lượt khác **còn nguyên**; cây thật không đổi |
| **(5) Lỗi hết / còn / BLOCKED** | **3/3 hết**; không BLOCKED | **3/4 hết**; còn `test_09` **R7 đỏ có chủ đích** → **BLOCKED chờ AG-00** | **2/2 hết**; không BLOCKED |
| **(6) Vi phạm luật** | **không** (test 21/17 giữ nguyên; assert 110→123 · 42→41 do gộp D1) | **không xoá test/skip**; **CÓ nới bộ dò** `SECRET_KEY` (xem §5.1) | **không xoá test/skip**; **Z4 thu hẹp phạm vi** canh (xem §5.2) |


### 3.1. R1 — `r1-bootstrap`

**(1) HEAD + tệp sửa:** xem §1. **(2) Lệnh · môi trường · exit · số ca TRƯỚC/SAU:**

| Bộ | Trước (clone `c909ebb`) | Sau (bản vá R1) | Diễn biến |
|---|---|---|---|
| `thu_g01_g02.py` | **exit 1 · Ran 21** · 1 ERROR (`test_010`: `KeyError: 'don'`) + 1 FAIL (`test_014`: migrate con thoát 1) | **exit 0 · Ran 21 · OK** | 21 → 21 ca |
| `thu_g19_route.py` | **exit 1 · Ran 14** · **13 ERROR** (`may_chu_do thất bại` + `TỪ CHỐI: CHƯA KHAI kho đang chạy`) | **exit 0 · Ran 50 · OK** | 14 → 50 ca (36 ca sinh động chỉ tồn tại khi bootstrap chạy được) |
| `chay_e2e.sh` | **exit 1 · 0 phép đo** · output **0 byte** | **exit 0 · 41/41 phép đo đạt** | 0 → 41 phép đo |
| `thu_r1_bootstrap.py` (mới) | — | **exit 0 · Ran 11 · OK** | — |

Chẩn đoán "khai kho bằng env" ở HEAD (để chứng minh lỗi là *thiếu lời khai*, không phải bộ
trích route hỏng) — tôi chạy lại đúng:

```text
VIP_KHO_DANG_CHAY=sqlite … python3 app/thu/thu_g01_g02.py
  exit 1 · Ran 21 · ERROR test_010 (KeyError 'don') + FAIL test_014 (TỤT SCHEMA v0→v10)
VIP_KHO_DANG_CHAY=sqlite … python3 app/thu/thu_g19_route.py
  exit 1 · Ran 49 · FAIL test_a6 (31 != 32) + FAIL test_d1 (103 != 104)
```

Khớp **từng con số** với báo cáo R1: 21/49, 14/50, 0/41. Nguyên nhân gốc (con `migrate.py`
không kế thừa lời khai `VIP_KHO_DANG_CHAY`) là đúng: sau khi khai, 13 ERROR biến mất và chỉ
còn 2 đỏ là **số ghim cũ** (31/103) — tức lớp lỗi thứ hai, không phải lỗi bootstrap.

**(3) Đối chứng âm — tôi tiêm lại lỗi bằng cách gỡ đúng bản vá (trên bản sao `/tmp`):**

| Bộ | Cách tiêm | Kết quả ĐO |
|---|---|---|
| `thu_g01_g02.py` | bỏ dòng `cau_hinh.khai_kho_kiem_thu()` | **exit 1 · Ran 21 · FAILED (failures=1)** · `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| `thu_g19_route.py` | bỏ dòng khai | **exit 1 · Ran 14 · 13 ERROR** · cùng thông điệp |
| `chay_e2e.sh` | bỏ `VIP_KHO_DANG_CHAY=sqlite` khỏi dòng `export` | **exit 1 · 0 byte output** |

Đúng chữ ký lượt "trước" ⇒ lời khai **là nguyên nhân** xanh, không phải trùng hợp. Ngoài ra
tôi đo trực tiếp 3 chốt cô lập của helper: không có `VIP_HUB_DATA` → từ chối; trỏ vào
**cây repo** → từ chối (`CÂY REPO`); trỏ `/du-lieu` → từ chối (`volume triển khai`); thư mục
tạm hợp lệ → exit 0, đặt `VIP_KHO_DANG_CHAY=sqlite`.

**(4) Đối chứng đường:** `test_014` đo **cả hai vế**: rollback tụt schema **bị từ chối**
(exit ≠ 0, `TỤT SCHEMA`, CSDL vẫn v10, chưa mọc cột `vai_tro`) và **đường khôi phục được phép**
`--toi-da-biet-chua-kiem-duoc` → **exit 0**, về v1, dữ liệu còn nguyên; sau đó nâng cấp lại →
exit 0, về v10. Cờ này là đường thoát **có thật trong sản phẩm** (`app/migrate.py` dòng 5-6,
1236-1239), không phải cờ mới thêm cho test. E2E sau vá: **41/41**.

**(5) Lỗi đã hết / còn lại:** cả 3 lỗi R1 đã hết; 0 lỗi còn lại trong phạm vi R1. **BLOCKED:**
không.

**(6) Vi phạm luật:** **không**. `thu_g01_g02` 21 test (110 → 123 assertion); `thu_g19_route`
17 test (42 → 41 assertion — **giảm 1 do GỘP** 3 phép đếm rời của D1 thành 2 **bất biến tập
hợp**, không phải bỏ vế đo; xem §4.3). Không thêm skip, không xoá test. Hai kỳ vọng bị đổi
`200 → 400` và rollback-vô-điều-kiện → rollback-có-chốt: **có căn cứ hợp đồng + đối chứng**
(§4.1), không phải "đổi số cho khớp output".

> **Ghi chú phạm vi:** `chay_e2e.sh` là tệp thứ ba bị sửa. Task ghi phạm vi R1 có "bootstrap
> E2E" nên tôi coi là **trong phạm vi**; báo cáo R1 cũng đã khai báo minh bạch việc này.

---

### 3.2. R2 — `r2-hopdong`

**(1) HEAD + tệp sửa:** xem §1. **(2) Lệnh · môi trường · exit · số ca TRƯỚC/SAU:**

| Bộ | Trước (clone `c909ebb`) | Sau (bản vá R2) | Ca |
|---|---|---|---|
| `thu_qa_g16.py` | **exit 1 · Ran 61** · FAIL `test_c5` (3 dòng `MA_LOI` bị coi là credential) | **exit 0 · Ran 61 · OK** | 61 → 61 |
| `thu_qa_jt.py` | **exit 1 · Ran 22** · FAIL `test_a4` (`from urllib.parse import urlsplit` bị coi là I/O) | **exit 0 · Ran 22 · OK** | 22 → 22 |
| `thu_qa_soat.py` | **exit 1 · Ran 30** · FAIL `test_q09f` (`400 != 200`) | **exit 0 · Ran 30 · OK** | 30 → 30 |
| `thu_tich_hop.py` | **exit 1 · Ran 12** · FAIL `test_05` (grep trúng chú thích) + FAIL `test_09` (R7) | **exit 1 · Ran 12** · **chỉ còn 1 FAIL `test_09`** | 12 → 12 |
| `thu_r2_hopdong.py` (mới) | — | **exit 0 · Ran 12 · OK** | — |

Tôi tái hiện thêm lỗi **môi trường git** mà báo cáo R2 nêu: chạy `thu_tich_hop.py` trong env
nguyên trạng (`GIT_CONFIG_COUNT=2` thiếu key) ⇒ `test_04` và `test_11` đỏ thêm với
`AssertionError: 128 != 0`. Đây là lỗi env, không phải sản phẩm; nhóm **không sửa** hai ca ấy
(đúng phạm vi đã chốt là `test_05`).

**(3) Đối chứng âm — tôi tiêm lỗi thật vào bản sao, không dùng harness của nhóm:**

| Tiêm | Bộ phải đỏ | Kết quả ĐO |
|---|---|---|
| Thêm `import http.client` vào `app/adapter_best.py` | `thu_qa_jt` `test_a4` + `thu_tich_hop` `test_05` | **jt exit 1 · FAIL test_a4**; **tich_hop exit 1 · FAIL test_05** |
| Thêm `TOKEN_TIEM = "Xk9#mQ2$vL7@nR4"` vào `app/xac_thuc_best.py` | `thu_qa_g16` `test_c5` | **exit 1 · FAIL test_c5** |
| Máy chủ giả **bỏ qua `tenant_id`, trả 200** (hành vi cũ) | `thu_qa_soat` `test_q09f` | **AssertionError, thông điệp có `400`** (tôi tự dựng lại phép đột biến, không chạy harness của nhóm) |

Nghĩa là các bộ không "xanh bằng cách xoá assertion": chúng **vẫn bắt** đúng lỗi cũ.

**(4) Đối chứng đường:** bộ dò mới **tha** `from urllib.parse import urlsplit` và chú thích
`# import http.client` (dương tính giả cũ) nhưng **bắt** `import http.client`,
`from urllib import request`, `import socket`, `urllib.request.urlopen(...)`. Đo trực tiếp trên
**sản phẩm**: `truy_van.tim_don(1, {"gioi_han": "5"})` chạy được; `truy_van.tim_don(1,
{"tenant_id": "2"})` ném `LoiTruyVan` **mã 400** với thông điệp nêu đúng tên lạ. Như vậy vế
"400" là **hợp đồng sản phẩm có thật** (`app/truy_van.py` dòng 36, 217-226; `docs/G12_QUERY.md`
§3.1 + bảng dòng 330 **không** có `tenant_id` trong danh sách trường lọc), không phải phép thử
tự bịa.

**(5) Lỗi đã hết / còn lại:** 3 lỗi gốc đã hết. **Còn 1 đỏ có chủ đích:**
`thu_tich_hop.py::test_09` (R7) — luật "chỉ `http_jt.py` nói chuyện với mạng" mâu thuẫn với
`http_best.py`/`xac_thuc_best.py` mà `docs/BEST_EXPRESS_API_CONTRACT.md` chủ động đưa vào.
Nhóm **giữ nguyên** `test_09`, không skip, không nới danh sách trắng. **BLOCKED — cần AG-00
chốt** luật phân tầng theo hãng hay toàn cục; trước khi chốt **không được tính R2 là "toàn
xanh"**.

**(6) Vi phạm luật:** không xoá test, không thêm skip, không đổi exit (`thu_tich_hop` vẫn 1).
Assertion tăng ở cả 4 bộ (196→200 · 69→70 · 65→70 · 37→40). **Nhưng có MỘT điểm phải nêu:**
luật 4 mới của `quet_hardcode` **nới bộ dò** — xem điều kiện (b) ở §5.1.

---

### 3.3. R27 — `r27-isolation`

**(1) HEAD + tệp sửa:** xem §1. **(2) Lệnh · môi trường · exit · số ca TRƯỚC/SAU:**

| Bộ | Trước (clone `c909ebb`) | Sau (bản vá R27) | Ca |
|---|---|---|---|
| `thu_g21_bimat.py` | **exit 1 · Ran 33** · FAIL `test_z4` (`['vh-g21bimat-goc-qhez_tsf'] != []` — thư mục của lượt khác) | **exit 0 · Ran 33 · OK** | 33 → 33 |
| `thu_g22_chotcay.py` | **exit 1 · Ran 11** · FAIL `test_d2` (đòi cây thật phải bẩn) + FAIL `test_d4` (bản "khác gần nhất" đã ĐẠT) | **exit 0 · Ran 11 · OK** | 11 → 11 |
| `thu_r27_fixture.py` (mới) | — | **exit 0 · Ran 4 · OK** | — |

Nguyên nhân gốc **đã xác nhận bằng hiện vật**: trong `TMPDIR` của máy có sẵn
`vh-g21bimat-goc-qhez_tsf/` (mốc thời gian **09:09**, do lượt khác để lại, **trước** phiên
này). Đó đúng là thứ làm Z4 cũ đỏ. Nó vẫn còn nguyên sau lượt đo — không lượt nào xoá nó.

**(3) Đối chứng âm — tôi dựng lại đúng hai lỗi:**

| Đối chứng | Cách dựng | Kết quả ĐO |
|---|---|---|
| **Z4 mù thật không?** | `VIP_G21_TAM_GOC` trỏ vào gốc **dùng chung** có sẵn `vh-g21bimat-cua-luot-khac/` | **exit 1 · Ran 33 · FAIL `test_z4`**; thư mục lạ **CÒN NGUYÊN** (không bị xoá) |
| **D2 chống rỗng còn răng?** | Gọi thẳng `do_d2_tren_cay()` trên **bản sao HEAD KHÔNG có** tệp của làn khác | **5 lỗi**, gồm `cây SẠCH TRƠN ⇒ phép đo rỗng` + 4 lỗi "không có thay đổi ngoài làn" — đúng báo cáo |
| **D2 có đụng cây thật?** | Chạy `thu_g22_chotcay.py` rồi so `git status` + tìm `veh-g22-d2-*` | **status không đổi**, không có `docs/_r27_lan_khac.md` trong cây thật, **0** thư mục clone sót |
| **D4 chọn bản sai thật không?** | Đọc bảng in ra | 3/4 bản "khác gần nhất" (`6ac4d0a8`, `7a60385a`) **ĐẠT** quy tắc ⇒ tiền đề cũ sai, đúng như nhóm khai |

**(4) Đối chứng đường:** tôi chạy **2 lượt G21 SONG SONG** trên **cùng một `TMPDIR`** có sẵn
thư mục + mốc nội dung của "lượt khác": **cả hai exit 0 · 33/33 · OK**, thư mục lạ và mốc
**còn nguyên**, **0** gốc tạm sót lại sau khi cả hai xong. Đây là tính chất cốt lõi của R27 và
nó **đo được**, không chỉ khai.

**(5) Lỗi đã hết / còn lại:** 2 lỗi fixture đã hết; 0 lỗi còn lại trong phạm vi. **BLOCKED:**
không (R7 thuộc R2, không liên quan).

**(6) Vi phạm luật:** không xoá test (33 · 11 giữ nguyên), không thêm skip, assertion tăng
(83→84 · 27→29). **Nhưng Z4 bị THU HẸP phạm vi canh** (thay vì "quét TMPDIR", nay chỉ canh sổ
`_TAM_DA_TAO` + thư mục con của gốc lượt). Đây là cách chữa đúng cho dương tính giả, nhưng để
lại **lỗ hổng thật** — xem §5.2.

---

## 4. LUẬT §6 — SOI TỪNG DẤU HIỆU NỚI CỔNG

### 4.1. Ba kỳ vọng bị đổi — có phải "đổi số cho khớp output"?

**Không.** Với **hai ca `200 → 400`**, ba căn cứ độc lập:

1. **Sản phẩm không bị sửa** — hành vi 400 đã có sẵn ở `c909ebb`; ba nhóm chỉ sửa tệp thử.
2. **Hợp đồng có tài liệu, viết trước lượt này:** `docs/G12_QUERY.md` §3.1 ("Điều kiện lạ →
   400, không bỏ qua im lặng") và bảng đường dẫn dòng 330 liệt kê trường lọc hợp lệ **không có
   `tenant_id`**; `app/truy_van.py` dòng 217-226 giải thích quyết định.
3. **Đo trực tiếp sản phẩm** (không qua bộ thử): `tim_don(1, {"gioi_han":"5"})` → chạy được;
   `tim_don(1, {"tenant_id":"2"})` → `LoiTruyVan(ma=400)`.

Đổi kỳ vọng **đi kèm** đối chứng dương (query hợp lệ vẫn 200, thấy dữ liệu của chính tenant)
và đối chứng cách ly (tenant B không thấy đơn A) — tức bản vá **tăng** phép đo, không thay số
để im lặng.

**Kỳ vọng thứ ba — `test_014` rollback (R1).** Bản cũ đòi `migrate.py --rollback <bản-sao-lưu>`
vô điều kiện **exit 0** rồi hạ schema v10 → v0. Sản phẩm từ `c909ebb` đã có **chốt chống tụt
schema** (fail-closed) nên lượt ấy **exit ≠ 0** với `TỤT SCHEMA` — đo được (§3.1). Bản vá giữ
chốt và đo **đường khôi phục được phép** bằng cờ có thật `--toi-da-biet-chua-kiem-duoc`
(`app/migrate.py` dòng 5-6, 1236-1239, chính thông điệp từ chối chỉ ra cờ này). Đây là **đổi
kỳ vọng theo hợp đồng đã có trong sản phẩm**, không phải nới chốt: bất biến fail-closed (CSDL
không bị đụng khi bị từ chối) được **thêm** vào cùng ca.

### 4.2. Bảng đếm trước/sau (9 tệp bị sửa)

| Tệp | Test trước→sau | Assertion trước→sau | Skip mới | Xoá test? |
|---|---|---:|---:|---|
| `thu_g01_g02.py` | 21 → 21 | 110 → **123** | 0 | không |
| `thu_g19_route.py` | 17 → 17 | 42 → 41 | 0 | không |
| `thu_qa_g16.py` | 61 → 61 | 196 → **200** | 0 | không |
| `thu_qa_jt.py` | 22 → 22 | 69 → **70** | 0 | không |
| `thu_qa_soat.py` | 30 → 30 | 65 → **70** | 0 | không |
| `thu_tich_hop.py` | 12 → 12 | 37 → **40** | 0 | không |
| `thu_g21_bimat.py` | 33 → 33 | 83 → **84** | 0 | không |
| `thu_g22_chotcay.py` | 11 → 11 | 27 → **29** | 0 | không |
| `chay_e2e.sh` | 0 → 0 | (shell) | 0 | không |

- **Không** có dòng `skipTest` / `@unittest.skip` / `assertTrue(True)` / `pass  #` / `except:`
  **mới** trong cả 9 tệp (các `skipUnless`/`skipTest` đếm được ở `thu_qa_g16`/`thu_qa_soat`
  là **có từ trước**, đếm trước = đếm sau: 3 và 1).
- **Số ca chạy không giảm** ở bất kỳ bộ nào. `thu_g19_route` **tăng** 49 → 50 (thêm ca
  `/api/v2/don/loc-mo-ta` — route G12 thêm sau lượt G18, trước đó **chưa từng** có ca cách ly).
- **Đúng 1 ca bị ĐỔI TÊN, không mất ca:** `thu_g19_route.test_a6_bo_trich_ba_phu_31_muc_con_
  thieu_cua_AG01` → `…_phu_het_khoang_trong_cua_AG01` (tên cũ ghim số `31`, tên mới nói đúng
  bất biến tập hợp). Tôi so **tập tên** 8 tệp python: 7 tệp giống hệt, chỉ tệp này đổi 1 tên.
- **Exit code không bị đổi để xanh:** `thu_tich_hop` vẫn exit 1; R7 vẫn đỏ.

### 4.3. Vì sao assertion `thu_g19_route` 42 → 41 mà không phải "bỏ vế đo"

Ba phép đếm rời của D1 (`103`, `103`, `len(that) == len(phu_ag01)+len(dat_that)`) được **gộp**
thành **hai bất biến tập hợp mạnh hơn**: `that == cua_toi & that` và
`that == phu_ag01 | dat_that`. Phép so tập hợp bắt được cả trường hợp "số đếm trùng nhau nhưng
tập khác nhau" — thứ mà phép đếm cũ bỏ lọt. Tương tự A6: bỏ ghim `31` nhưng giữ
`sorted(MUC_CON_THIEU) == khoảng trống thật` **và** thêm bất biến artefact. **Không có vế đo nào
bị bỏ mà không được thay bằng vế mạnh hơn.**

---

## 5. CÁI CHƯA ĐẠT / CHƯA KIỂM ĐƯỢC (và vì sao)

### 5.1. R2 — bộ dò G16 có lỗ hổng MỚI (đo được, không suy đoán)

Luật 4 miễn trừ **mọi** hằng `UPPER_SNAKE` có giá trị là "câu ≥ 3 từ". Tôi quét 22 tên thật
với giá trị `"correct horse battery staple"`:

| Tên | `c909ebb` | Sau bản vá R2 | Kết luận |
|---|---|---|---|
| `SECRET_KEY` | **BẮT** | **THẢ** | **hồi quy thật** — tên trường bí mật cổ điển, giá trị là cụm mật khẩu |
| `CREDENTIAL_X` | **BẮT** | **THẢ** | hồi quy (tên mã lỗi giả, nhưng vẫn là tên chứa "credential") |
| `CREDENTIAL_KHONG_HOP_LE` / `TOKEN_KHONG_HOP_LE` | BẮT (sai) | THẢ | **đúng mục tiêu** |
| `PASSWORD` / `SECRET` / `CLIENT_SECRET` / `PRIVATE_KEY` | BẮT | BẮT | giữ nguyên |

Nguyên nhân: `_ten_truong_bi_mat()` so **đúng bằng** hoặc **đuôi** với danh sách
(`password`, `secret`, `apikey`, `privatekey`, `accesskey`…) nhưng **thiếu** `key`, `token`,
`credential`; `SECRET_KEY` chuẩn hoá thành `secretkey` nên không khớp đuôi nào.

**Điều kiện để R2 thành ĐẠT:** thêm `key`/`token`/`credential` vào phép so đuôi (hoặc chỉ miễn
khi tên kết thúc bằng `_LOI`/`_MA_LOI`), và thêm một ca hồi quy
`SECRET_KEY = "correct horse battery staple"` **phải bị bắt**. Đây là **nới cổng bảo mật**,
không phải "thêm đối chứng" — dù các đối chứng nhóm thêm đều đúng.

### 5.2. R27 — Z4 không còn canh rác của lượt TRƯỚC

Tôi dựng `TMPDIR` có sẵn `vh-g21bimat-luot-rac-cu/` (đúng tiền tố, đại diện lượt chạy trước bị
crash) rồi chạy G21: **exit 0 · OK**, thư mục rác **vẫn còn nguyên**. Trước bản vá, đúng tình
huống này làm Z4 đỏ. Đây là **cái giá có ý thức** của việc bỏ quét TMPDIR — nhưng nghĩa là
**không còn phép đo nào** canh "lượt trước để lại rác", và rác sẽ tích tụ vô hạn (hiện vật
`vh-g21bimat-goc-qhez_tsf` từ 09:09 vẫn nằm đó). Điều kiện: thêm một invariant/cleanup riêng
cho gốc tạm cũ (ví dụ quét theo tuổi hoặc dọn đầu lượt), tách khỏi phép canh cô lập.

**D4 cũng bị thu hẹp độ nhạy:** bản cũ đòi "bản khác GẦN NHẤT phải hỏng"; bản mới **tìm ngược
tối đa 40 bản** để lấy một bản bị bắt. Trên nền này tiền đề cũ đúng là sai (3/4 bản gần nhất
ĐẠT — tôi đo lại được), nên cách chữa hợp lý; nhưng nó **không còn chứng minh** "bản ngay
trước khi vá hỏng". Bù lại bằng D6 (mẫu sai tiêm có chủ đích) — tôi đã thấy D6 chạy.

### 5.3. Những thứ tôi CHƯA kiểm được

1. **Không chạy lại toàn bộ 79 bộ trên từng nhánh** — chỉ chạy đúng các bộ thuộc phạm vi +
   bộ tự kiểm mới. Rủi ro hồi quy chéo thấp (chỉ sửa tệp thử) nhưng **chưa phủ hết**.
2. **Không xác minh được việc agent bị chặn ghi `.git`** — tôi chỉ xác minh **hệ quả**:
   HEAD không đổi, không có gì staged, thay đổi nằm ở working tree. Tôi không thử ghi `.git`.
3. **Không kiểm các bộ cần PostgreSQL/Chromium/LIVE** — ngoài phạm vi 3 nhóm.
4. **Bộ dò G16**: tôi đo 22 tên mẫu, không chứng minh được "không còn lỗ hổng nào khác";
   kết luận chỉ trong phạm vi đã đo.
5. **R7**: tôi xác nhận nó **còn đỏ** và **không** bị nới, nhưng **không** đủ thẩm quyền chốt
   luật phân tầng — việc của AG-00.

---

## 6. NỀN HIỆN TẠI — `sh app/thu/chay_tat_ca.sh` TRÊN CÂY CHÍNH (`5429c6d`)

Chạy trên `qv1-kiemchung` **trước khi gộp**, mục đích **chỉ để biết nền**, không phải kết quả
ba nhóm. (Cây chính chưa có bản vá nào của R1/R2/R27.)

```text
$ env -u VIP_KHO_DANG_CHAY -u VIP_HUB_DATA sh app/thu/chay_tat_ca.sh
…
══════════════════════════════════════════════════════════
  python:   2459 ca · 77 bộ chạy thật
            + 1 bộ BỎ QUA (0 ca): thu_nhat_ky_yeu_cau.py
  frontend: 56 + 40 ca (hai tầng tự động)     ← tầng 2 HỎNG: thu_http.py test_04
  E2E:      (rỗng)                            ← HỎNG, mã thoát 1, 0 phép đo
  bộ hỏng:  thu_g01_g02.py thu_g19_route.py thu_g20_dahang.py thu_g20_saoluu.py
            thu_g21_bimat.py thu_g21_saoluu.py thu_g22_chotcay.py thu_g22_e2e.py
            thu_g22_gioihan.py thu_g22_phanloai.py thu_g22_zeroca.py thu_qa_g16.py
            thu_qa_g18.py thu_qa_g21.py thu_qa_g22.py thu_qa_jt.py thu_qa_soat.py
            thu_tich_hop.py thu_http.py chay_e2e.sh
EXIT=1
```

- **Mã thoát 1 · 2459 ca · 77/78 bộ chạy thật · 59 bộ ✓ · 18 bộ ✗ (python) · 1 bộ ⊘.**
- **9 bộ thuộc 3 nhóm đều đỏ trên cây chưa gộp** — đúng dự kiến: `thu_g01_g02` 21 ca,
  `thu_g19_route` 14 ca, `thu_qa_g16` 61, `thu_qa_jt` 22, `thu_qa_soat` 30, `thu_tich_hop` 12,
  `thu_g21_bimat` 33, `thu_g22_chotcay` 11, `chay_e2e` (0 phép đo).
- **11 mục đỏ còn lại nằm NGOÀI phạm vi 3 nhóm** (10 bộ python + `thu_http.py`) (`thu_g20_dahang`, `thu_g20_saoluu`,
  `thu_g21_saoluu`, `thu_g22_e2e`, `thu_g22_gioihan`, `thu_g22_phanloai`, `thu_g22_zeroca`,
  `thu_qa_g18`, `thu_qa_g21`, `thu_qa_g22`) — là R3/R6/R7 đã biết, **không** do 3 nhóm này.
- **Hai cảnh báo của chính bộ chạy, ghi nguyên văn:**
  1. `⚠ tập TỆP CHƯA THEO DÕI ĐỔI giữa lượt chạy` — vì tôi tạo `app/thu/thu_qv_kiemchung.py`
     + `docs/QV_KIEMCHUNG.md` **trong lúc** nó chạy; bộ chạy tự báo "số 2459 ca · 77 bộ KHÔNG
     tái lập nguyên vẹn". Con số vẫn là **đo được**, nhưng muốn ghim thì phải chạy lại trên cây
     đứng yên.
  2. Lượt chạy diễn ra khi máy có **~6 bộ chạy toàn phần song song** của các agent khác ⇒ thời
     gian bị kéo dài; không thấy dấu hiệu hỏng giả do tranh chấp cổng (các bộ đỏ đều đỏ đúng
     lý do đã biết).


---

## 7. GỘP KHÔ — BA NHÓM ÁP LÊN CÂY CHÍNH HIỆN TẠI

Tôi dựng bản sao `5429c6d` (HEAD cây chính) rồi áp **cả ba** patch + chép 3 tệp mới:

```text
git clone … ; git checkout 5429c6d
git apply r1-bootstrap.patch && git apply r2-hopdong.patch && git apply r27-isolation.patch
⇒ 0 xung đột; 9 tệp M + 6 tệp ?? đúng danh sách §1
```

Kết quả chạy bộ kiểm chứng hợp nhất (`app/thu/thu_qv_kiemchung.py`, xem §8):

```text
$ python3 app/thu/thu_qv_kiemchung.py
Ran 17 tests in 166.005s
OK
EXIT=0

BỘ THỬ                     | exit |  ca | FAIL/ERROR | bỏ qua
thu_g01_g02.py             |    0 |  21 |          0 |      0
thu_g19_route.py           |    0 |  50 |          0 |      0
thu_r1_bootstrap.py        |    0 |  11 |          0 |      0
thu_qa_g16.py              |    0 |  61 |          0 |      0
thu_qa_jt.py               |    0 |  22 |          0 |      0
thu_qa_soat.py             |    0 |  30 |          0 |      0
thu_tich_hop.py            |    1 |  12 |          1 |      0   ← R7, đúng ca test_09
thu_r2_hopdong.py          |    0 |  12 |          0 |      0
thu_g21_bimat.py           |    0 |  33 |          0 |      0
thu_g22_chotcay.py         |    0 |  11 |          0 |      0
thu_r27_fixture.py         |    0 |   4 |          0 |      0
chay_e2e.sh                |    0 |  41 |          — |      —   (E2E: 41/41)
```

**Kết luận gộp khô: 0 xung đột, 17/17 phép kiểm ĐẠT, không nhóm nào phá nhóm khác** (lượt này
chạy trong lúc máy có ~6 bộ chạy toàn phần song song của agent khác — càng có giá trị về tính
ổn định). Lưu ý: đây là **gộp thử trong `/tmp`**, không phải gộp thật; cây chính vẫn ở
`5429c6d` và chỉ có thêm 2 tệp báo cáo/bộ kiểm của QV-01.

---

## 8. BỘ KIỂM CHỨNG MỚI — `app/thu/thu_qv_kiemchung.py`

17 ca, mỗi ca là một phép **độc lập** với báo cáo của nhóm:

- **12 ca số ca/exit** cho 11 bộ + E2E (bao gồm `thu_tich_hop` được phép đỏ **đúng** `test_09`).
- **1 ca đối chứng âm R1**: import hook vô hiệu hoá `khai_kho_kiem_thu` ⇒ `thu_g01_g02` **phải
  đỏ** với `CHƯA KHAI kho đang chạy`. Không sửa tệp nào.
- **1 ca hợp đồng sản phẩm**: `tim_don` hợp lệ chạy được + `tenant_id` bị 400 (đo trên
  `app/truy_van.py`, không qua bộ thử).
- **1 ca hai chiều cho bộ dò R2**: bắt I/O/secret thật, tha `urllib.parse`/thông báo lỗi.
- **1 ca luật §6**: so `c909ebb` ↔ cây đang đứng — test không giảm, không skip mới, không dấu
  hiệu rỗng mới.
- **1 ca R27**: Z4 không quét TMPDIR, mọi thư mục tạm nằm trong gốc lượt, D2 dùng bản sao, D4
  dùng `nguon_cu_hong`.

Chạy: `python3 app/thu/thu_qv_kiemchung.py` (exit 0 = ĐẠT). Bộ tự dò của `chay_tat_ca.sh` sẽ
nhặt tệp này ở lượt sau — **nghĩa là trên cây CHƯA gộp nó sẽ ĐỎ**, đúng thiết kế: nó là
cổng SAU gộp, không phải bộ thử độc lập của cây hiện tại.

---

## 9. RÀNG BUỘC ĐÃ GIỮ

- Local-first; **không** push/deploy/tunnel; **không** gọi API hãng; **không** credential thật;
  **không** sửa DB nghiệp vụ; **không** đụng PostgreSQL; **không** mở LIVE; BEST-09 giữ BLOCKED.
- **Không sửa tệp nào của ba nhóm** — mọi phép tiêm/đột biến chạy trên bản sao `/tmp`.
- **Không ghi `.git`**, không stage, không commit, không tạo nhánh.
- Mọi thư mục dữ liệu là `mkdtemp` ngoài cây repo; dọn sau mỗi lượt.
