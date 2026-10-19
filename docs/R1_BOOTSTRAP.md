# R1 — BOOTSTRAP KHAI KHO + CÁCH LY: BÁO CÁO ĐỐI CHỨNG

**Làn:** R1 · **Ngày đo:** 19/10/2026 (giờ VN) · **Nhánh:** `r1-bootstrap`
**HEAD đo:** `c909ebb` (`best/integration`); `main = de740dc` — **KHÔNG dùng**.
**Đọc trước:** `docs/QA_NGUYENNHAN.md` (báo cáo QA gốc). Tệp ấy nằm ở worktree
`qa-nguyennhan` dưới dạng **chưa theo dõi**; lượt này đọc bản đó, không sửa nội dung.

---

## 0. TÓM TẮT CHO NGƯỜI VỘI

**Ba bộ R1 đã xanh hoàn toàn bằng cách sửa BOOTSTRAP CỦA PHÉP THỬ, không sửa sản phẩm:**

| Bộ | Trước (không khai kho) | Sau (bộ thử tự khai) | Bỏ qua / chưa chạy |
|---|---|---|---:|
| `thu_g01_g02.py` | exit **1** · Ran **21** · 1 ERROR + 1 FAIL | exit **0** · Ran **21** · **OK** | 0 / 0 |
| `thu_g19_route.py` | exit **1** · Ran **14** · **13 ERROR** | exit **0** · Ran **50** · **OK** | 0 / 0 |
| `chay_e2e.sh` | exit **1** · **0 phép đo** (output 0 byte) | exit **0** · **KẾT QUẢ 41/41** | 0 / 0 |

Nguyên nhân gốc **không phải ba lỗi khác nhau**: cả ba bộ đều để `migrate.py` chạy trong
**tiến trình con** mà không truyền lời khai "kho đang chạy"; chốt fail-closed của G22
(`TỪ CHỐI: CHƯA KHAI kho đang chạy`) làm tiến trình con thoát 1. Vì vậy bản vá đặt ở **bootstrap
của từng phép thử**: sau khi `VIP_HUB_DATA` đã trỏ thư mục TẠM, gọi
`cau_hinh.khai_kho_kiem_thu()` — hàm này đặt `VIP_KHO_DANG_CHAY=sqlite` vào `os.environ` nên con
kế thừa qua `env=dict(os.environ)`. **Không** thêm mặc định SQLite vào `app/migrate.py` hay cấu
hình production; `git diff` không chạm `app/migrate.py`, `app/cau_hinh.py` hay bất kỳ tệp sản phẩm nào.

Phần R2/R3 còn lại trong hai bộ cũng được sửa **theo hợp đồng hiện hành**, không theo đầu ra:
`test_010` đo đúng hợp đồng truy vấn (body bị bỏ qua / query lạ **400**) kèm đối chứng dương và
cách ly tenant; `test_014` giữ **chốt chống tụt schema** và đo **đường khôi phục được phép**;
G19 bỏ ghim `31/32`, `103/104`, thay bằng **bất biến tập hợp**, và bổ sung phép đo cách ly cho
route mà G12 thêm sau lượt G18 (`/api/v2/don/loc-mo-ta`).

---

## 1. PHƯƠNG PHÁP VÀ MÔI TRƯỜNG

- Mỗi bộ chạy bằng `python3 app/thu/<tên>.py` từ gốc repo; E2E bằng `sh app/thu/chay_e2e.sh`.
  **Mã thoát lấy trực tiếp từ `$?` của tiến trình**, không đọc qua grep/pipeline.
- Môi trường: Python hệ thống 3.9.6, Darwin arm64. `VIP_HUB_DATA` là thư mục tạm; với lượt
  "trước" và "đối chứng âm" thì **không đặt** `VIP_KHO_DANG_CHAY`; `VIP_HUB_BIND=127.0.0.1`,
  `VIP_JT_MOI_TRUONG=mock`, `PYTHONDONTWRITEBYTECODE=1`. Không đặt biến cho tiến trình production.
- Không gọi hãng, không credential thật, không sửa DB nghiệp vụ, không push/deploy, không mở LIVE.
- Ba lượt đo chính (trước / sau khi khai / sau khi sửa) đều dùng **lệnh thật**, exit thật. Log
  đầy đủ nằm trong thư mục bằng chứng tạm của lượt chạy (tên tệp ghi dưới đây); các đoạn trích
  quan trọng được chép nguyên văn vào báo cáo này.

### 1.1. Cách đếm

- `Ran N` của `unittest` **gồm ca skipped**; bảng dưới tách `bỏ qua` và `chưa chạy` riêng.
- G19 sinh test động: 1 test cho mỗi ca cách ly. `Ran 50` = 8 (A) + 5 (B) + 36 (C: 3 tổng hợp +
  33 ca sinh động) + 1 (D). Số ca con **không** cộng vào tổng của bộ khác.
- E2E là bộ viết tay: con số phạm vi là **41 phép đo** do chính script công bố. Dòng
  "cửa hạn mức nhập: HTTP 404 — chưa mở, không tính là ca" là ghi chú, không phải ca.

---

## 2. NGUYÊN NHÂN GỐC (đo trước khi sửa)

### 2.1. G01/G02 — `test_014` gọi `subprocess.run(migrate.py)`

```text
$ env -u VIP_KHO_DANG_CHAY VIP_HUB_DATA=<tạm> ... python3 app/thu/thu_g01_g02.py
ERROR: test_010_doi_tenant_id_trong_request_khong_vuot_quyen
FAIL:  test_014_migration_bao_toan_du_lieu
[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này
Ran 21 tests
FAILED (failures=1, errors=1)
exit 1
```

Hai lỗi **khác nguyên nhân**, không được gộp:

1. `test_014` đỏ vì **thiếu khai kho ở tiến trình con** (R1).
2. Khi khai kho (đối chứng chẩn đoán, chưa sửa tệp), `test_014` chuyển sang:

```text
[migrate] TỪ CHỐI: TỤT SCHEMA. Bản sao lưu ở phiên bản **v0**, CSDL đang chạy ở **v10**.
```

Đây là **chốt chống tụt schema đang làm đúng việc của nó**: bộ cũ đòi rollback vô điều kiện về
v1, tức là đòi sản phẩm bỏ chốt để phép thử xanh (R3).

`test_010` (đo được ở cả hai lượt) đỏ vì bộ cũ đọc `kq["don"]` sau một lượt `GET
/api/v2/don?tenant_id=...`. Hợp đồng G12/G22 hiện tại **từ chối 400** tên lọc lạ
(`truy_van._kiem_ten_la`) thay vì bỏ qua im lặng; `kq` là `{"loi": ...}` nên lỗi bề mặt là
`KeyError: 'don'`. Không phải rò tenant — đây là **kỳ vọng cũ** (R2).

### 2.2. G19 route — `BOT.chay_may_chu → may_chu_do (con) → migrate`

```text
$ env -u VIP_KHO_DANG_CHAY ... python3 app/thu/thu_g19_route.py
RuntimeError: may_chu_do thất bại (exit 1)
STDERR: [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy ...
13 ERROR (A1, A2, A4, A5, A6, A7, A8, B1, B3, B4, B5, C setUpClass, D1)
Ran 14 tests
FAILED (errors=13)
exit 1
```

Khai kho bằng biến môi trường (chẩn đoán):

```text
exit 1 · Ran 49 · FAILED (failures=2)
FAIL: test_a6...  AssertionError: 31 != 32
FAIL: test_d1...  AssertionError: 103 != 104
[A6] AG-06=105 · AG-01=73 · khoảng trống=32 = 31 route thật + 1 artefact tiền tố
```

Mục thứ 32 là **`/api/v2/don/loc-mo-ta`** — route G12 thêm **sau** lượt G18. Ghim `31/103` là
**ảnh cũ**, không phải số mới cần thay bằng `32/104`. Phép đo cách ly cũ **chưa hề có** ca cho
route này: nếu chỉ đổi số thì bộ sẽ xanh nhưng một route thật vẫn chưa được đo cách ly.

### 2.3. E2E shell — `chay_e2e.sh` gọi `python3 app/migrate.py`

Chạy **chính bản `HEAD`** của script (không sửa tệp theo dõi; chép ra tên tạm rồi xoá):

```text
$ env -u VIP_KHO_DANG_CHAY ... sh app/thu/.r1-e2e-goc.sh
exit 1
--- output: 0 byte ---
```

`migrate.log` nằm trong nền `$NEN` bị `trap` xoá, nên shell chết **không có phép đo nào**. Chạy
riêng **đúng bước** `python3 app/migrate.py` trên nền `mktemp -d` mới:

```text
không khai: exit 1 · [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy ...   (am-e2e-migrate-khongkhai.log)
khai sqlite: exit 0 · [migrate] ... bảo toàn ĐẠT · Xong, phiên bản 10 (am-e2e-migrate-khaisqlite.log)
```

---

## 3. THAY ĐỔI ĐÃ LÀM

### 3.1. Bootstrap — một quy tắc, ba entrypoint

| Tệp | Thay đổi | Vì sao đúng chỗ |
|---|---|---|
| `app/thu/thu_g01_g02.py` | sau khi đặt `VIP_HUB_DATA=_tam` (**mkdtemp**) và import `cau_hinh`: gọi `cau_hinh.khai_kho_kiem_thu()` | `test_014` truyền `env=dict(os.environ, VIP_HUB_DATA=<tạm>)` cho con ⇒ con kế thừa lời khai |
| `app/thu/thu_g19_route.py` | tạo `_NEN_CHA` bằng **mkdtemp**, đặt `VIP_HUB_DATA`, gọi `cau_hinh.khai_kho_kiem_thu()` trước `CAC_CA`; `atexit` dọn nền cha | `BOT.chay_may_chu` truyền `env=dict(os.environ)` cho `may_chu_do`; con tự ghi đè `VIP_HUB_DATA` bằng nền tạm riêng của nó |
| `app/thu/chay_e2e.sh` | `export ... VIP_KHO_DANG_CHAY=sqlite` **sau** dòng `NEN=$(mktemp -d)`, cùng dòng với `VIP_HUB_DATA="$NEN"` | lời khai đi cùng đúng nền tạm mà nó khai; `python3 app/migrate.py` là tiến trình con của shell |

`cau_hinh.khai_kho_kiem_thu()` giữ nguyên **hai chốt cô lập**: từ chối khi `VIP_HUB_DATA` chưa
đặt, nằm trong cây repo, hoặc là volume `/du-lieu`. Không có nhánh nào nới chốt.

### 3.2. `test_010` — theo hợp đồng hiện hành, không theo output

Đo **năm vế**, mỗi vế có vai trò riêng:

1. Body mang `tenant_id` của B khi tạo đơn ⇒ **201**, đơn vẫn thuộc **A** (body bị bỏ qua).
2. `GET /api/v2/don?tenant_id=<B>` ⇒ **400** và body nêu đúng tên `tenant_id` (từ chối, không
   bỏ qua im lặng).
3. Đối chứng đường: `GET /api/v2/don?gioi_han=200` ⇒ **200**, thấy đơn của **A**, **không** thấy
   đơn của **B**.
4. Body `tenant_id` khi tạo khách hàng ⇒ **201**, vẫn thuộc **A**.
5. `POST /auth/doi-tenant` sang tenant không thuộc ⇒ **403**.

Không xoá assertion nào; thay một kỳ vọng cũ (200 + đọc `.don`) bằng **đúng hợp đồng** + hai đối
chứng (dương/đường).

### 3.3. `test_014` — giữ chốt, đo đường khôi phục được phép

Dựng CSDL v1 (không có bảng `schema_version` ⇒ phiên bản 0) có dữ liệu, chạy migrate thật lên
v10, rồi:

1. **Đối chứng âm:** `migrate.py --rollback <bản-sao-lưu>` ⇒ exit **≠ 0**,
   thông điệp **`TỤT SCHEMA`** (v0 đè v10).
2. **Bất biến fail-closed:** sau lượt bị từ chối, CSDL đang chạy vẫn **v10**, còn đủ dòng
   `don_hang`, và **chưa** mọc cột `vai_tro` — chốt từ chối **trước khi** đụng CSDL.
3. **Đối chứng dương:** cùng tệp, thêm đúng cờ `--toi-da-biet-chua-kiem-duoc` (đường thoát đã
   ghi trong thông điệp) ⇒ exit **0**, schema về v1 (có `vai_tro`), dữ liệu còn nguyên.
4. **Vòng tròn:** chạy migrate lần nữa trên **bản sao tạm** ⇒ exit **0**, lên lại v10, dữ liệu
   còn nguyên.

Vế (3) chứng minh lượt đỏ ở (1) là do **chốt**, không phải bản sao lưu hỏng; vế (2) chứng minh
chốt thật sự fail-closed. Không xoá `test_014`, không bỏ assertion, không đổi exit để cho xanh.

### 3.4. G19 — bỏ ghim số, thay bằng bất biến tập hợp, bổ sung phép đo còn thiếu

- `HAI_MUOI_MOT` → `MUC_CON_THIEU`; thêm `/api/v2/don/loc-mo-ta` (đúng khoảng trống thật).
- `A6`: bỏ `assertEqual(31, len(thieu))`. Giữ **bất biến**: `sorted(MUC_CON_THIEU) ==
  sorted(AG-06 − AG-01)`; mọi mục không phải artefact đều được bộ ba thấy; artefact trong
  khoảng trống đúng bằng danh sách đã chứng minh ở A7.
- `C2`: bỏ `31`/`30`; thay bằng **tập MỤC đã đo == tập MỤC cần đo** (trừ artefact A7), và
  artefact không được lọt vào ca C.
- `D1`: bỏ `103`/`104`; thay bằng hai **bất biến tập hợp**:
  `that == cua_toi & that` (bộ ba phủ đủ route thật của AG-06) và
  `that == phu_ag01 | dat_that` (hai đường đo độc lập phủ đúng cùng một tập — mạnh hơn so số đếm).
  Khi sản phẩm thêm route, phép so tự đỏ nếu đường đo chưa phủ tới.
- **Bổ sung ca cách ly** cho `/api/v2/don/loc-mo-ta`: route trả mô tả bộ lọc, là đường toàn cục
  (hai tenant nhận giống nhau, không chứa dấu tenant). Ca A6 bắt buộc phải có ca này; không phải
  "thêm ca cho đủ số".

---

## 4. BẰNG CHỨNG SAU KHI SỬA (exit thật, số ca thật)

### 4.1. Bảng trước / sau

| Bộ | Lượt | Exit | Ran | Kết quả | Skip | Chưa chạy |
|---|---|---:|---:|---|---:|---:|
| `thu_g01_g02.py` | trước (không khai) | 1 | 21 | 1 ERROR + 1 FAIL | 0 | 0 |
| | khai bằng env (chẩn đoán) | 1 | 21 | 1 ERROR + 1 FAIL (`KeyError`, `TỤT SCHEMA`) | 0 | 0 |
| | **sau bản vá** | **0** | **21** | **OK** | **0** | **0** |
| `thu_g19_route.py` | trước (không khai) | 1 | 14 | 13 ERROR | 0 | 0 |
| | khai bằng env (chẩn đoán) | 1 | 49 | 2 FAIL (`31!=32`, `103!=104`) | 0 | 0 |
| | **sau bản vá** | **0** | **50** | **OK** | **0** | **0** |
| `chay_e2e.sh` | trước (bản `HEAD`) | 1 | 0 | không có phép đo, output 0 byte | 0 | 41 |
| | **sau bản vá** | **0** | **41** | **41/41 phép đo đạt** | **0** | **0** |

### 4.2. Đoạn in quan trọng của G19 sau bản vá

```text
[A1] hằng số biên dịch=84 · ứng viên(tĩnh)=106 · CÓ ROUTE(thi hành)=104
[A5] 0 route lạ: cả 104 route của bộ ba đều nằm trong tập AG-06
[A6] AG-06=105 · AG-01=73 · khoảng trống=32 = 31 route thật + 1 artefact tiền tố
     bộ ba thấy đủ 31/31 route thật (mục còn lại do ca A7 đo riêng)
[C1] ĐẠT 33/33 · CHƯA ĐO 0 · RÒ RỈ 0 · khẳng định rỗng 0
[C2] đã đo đủ 32 MỤC = 31 route thật (ca C) + 1 artefact (ca A7); dùng 33 ca
[D1] AG-06 đếm: 105 mục · trong đó route THẬT: 104
     Khoảng trống AG-06 − AG-01: 32 mục = 31 route thật + 1 artefact
     CHƯA ĐO: 0
     ⇒ ĐÃ CÓ BẰNG CHỨNG CÁCH LY TENANT: 104/104 route THẬT
     ⇒ Còn thiếu: 0 route
Ran 50 tests
OK
exit 0
```

### 4.3. E2E sau bản vá

```text
$ env -u VIP_KHO_DANG_CHAY ... sh app/thu/chay_e2e.sh
...
==========================================================
KẾT QUẢ: 41/41 phép đo đạt
[e2e] mã thoát 0
exit 0
```

---

## 5. ĐỐI CHỨNG ÂM — TIÊM LẠI ĐÚNG LỖI, PHÉP ĐO PHẢI ĐỎ

Không có lớp này thì các dòng xanh ở §4 không chứng minh lời khai là nguyên nhân: một bộ luôn
xanh, hoặc một bộ đọc nhầm tệp, cũng cho cùng bảng.

### 5.1. G01/G19 — vô hiệu hoá lời khai bằng **import hook**, KHÔNG sửa tệp

Harness nằm **ngoài repo** (`sitecustomize.py` trên `PYTHONPATH`): ngay sau khi `cau_hinh` được
nạp, nó thay `khai_kho_kiem_thu` bằng hàm rỗng (không đặt `VIP_KHO_DANG_CHAY`, không đổi
`KHO_DANG_CHAY`), và bỏ biến thừa hưởng từ shell. Chạy **đúng tệp đang giao**, `env -u
VIP_KHO_DANG_CHAY`:

| Bộ | Exit | Ran | Kết quả | Bằng chứng đỏ |
|---|---:|---:|---|---|
| `thu_g01_g02.py` | **1** | 21 | `FAILED (failures=1)` | `FAIL: test_014` + `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| `thu_g19_route.py` | **1** | 14 | `FAILED (errors=13)` | `RuntimeError: may_chu_do thất bại` + `TỪ CHỐI: CHƯA KHAI kho đang chạy` |

Đúng chữ ký của lượt trước khi sửa (§2.1, §2.2): lời khai là **nguyên nhân**, không phải trùng hợp.

### 5.2. E2E — chạy đúng bước migrate của shell trên nền tạm mới

| Lượt | Exit | Bằng chứng |
|---|---:|---|
| Không khai (`env -u VIP_KHO_DANG_CHAY`) | **1** | `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| Khai `VIP_KHO_DANG_CHAY=sqlite` | **0** | `bảo toàn ĐẠT · Xong, phiên bản 10` |

Đây là **đúng lệnh** mà `chay_e2e.sh` chạy; không thêm công tắc chỉ để thử vào script.

### 5.3. Chốt cô lập của helper — ba đối chứng âm trong bộ tự kiểm

`app/thu/thu_r1_bootstrap.py` chạy helper trong tiến trình con với ba nền xấu:

- chưa đặt `VIP_HUB_DATA` ⇒ exit ≠ 0, `chưa đặt VIP_HUB_DATA`;
- `VIP_HUB_DATA` trong cây repo ⇒ exit ≠ 0, `CÂY REPO`;
- `VIP_HUB_DATA=/du-lieu/...` ⇒ exit ≠ 0, `volume triển khai`.

### 5.4. Đối chứng âm của chính bộ tự kiểm

Fixture tí hon đúng khuôn R1 (nền tạm → tự khai → chạy `migrate.py` trong con):

- chạy sạch ⇒ exit **0**, `FIXTURE_OK`;
- chạy qua import hook (bỏ khai) ⇒ exit **≠ 0**, `CHƯA KHAI kho đang chạy`.

Lượt chạy đầu của bộ tự kiểm **đã bắt được một lỗi của chính nó**: dùng lại một nền cho cả hai
vế, lượt thứ hai thấy CSDL đã ở schema hiện tại nên `migrate` không gọi `sao_luu()` và cổng khai
kho không bị chạm ⇒ đối chứng âm xanh giả. Bản đang giao dùng **hai nền tách biệt**; lỗi được
ghi lại vì nó là bài học về chính phép đo.

---

## 6. BỘ TỰ KIỂM MỚI

`app/thu/thu_r1_bootstrap.py` — 11 test, không có skip:

| Nhóm | Nội dung |
|---|---|
| A (4) | ba chốt cô lập của `khai_kho_kiem_thu()` + nhận nền tạm và đặt env |
| B (3) | `migrate.py` trong con: thiếu khai ⇒ đỏ đúng thông điệp; cha khai ⇒ con kế thừa `env=dict(os.environ)` ⇒ xanh; **import hook bỏ khai ⇒ fixture đỏ** |
| C (4) | kiểm tĩnh trên **ba tệp đang giao**: lời khai ở cấp mô-đun, đứng trước phép đo; E2E khai **sau** `NEN=$(mktemp -d)` và cùng dòng `VIP_HUB_DATA="$NEN"`; `app/cau_hinh.py` vẫn đọc từ khai báo, `app/migrate.py` vẫn còn thông điệp fail-closed |

```text
$ env -u VIP_KHO_DANG_CHAY -u VIP_HUB_DATA python3 app/thu/thu_r1_bootstrap.py
...
Ran 11 tests in 0.548s
OK
exit 0
```

### 6.1. Chạy lại bộ tự kiểm phân loại của QA

`app/thu/thu_qa_nguyennhan.py` và `docs/QA_NGUYENNHAN.md` nằm ở worktree `qa-nguyennhan`
(untracked), **không** có trong cây này. Chạy chính tệp ấy với `QANN_REPO` trỏ về cây R1 để nó
đo **mã và bộ đếm của cây này**:

```text
$ QANN_REPO=<r1-bootstrap> python3 <qa-nguyennhan>/app/thu/thu_qa_nguyennhan.py
Ran 11 tests in 0.940s
OK
exit 0
```

Lượt cuối chạy **đúng lệnh** `python3 app/thu/thu_qa_nguyennhan.py` sau khi chép tạm tệp vào
`app/thu/` (chạy xong gỡ ngay, không đưa vào phạm vi giao): exit **0** · Ran **11** · **OK**.

### 6.2. Hồi quy liên quan cấu hình

Thay đổi dựa trên giao diện `cau_hinh.khai_kho_kiem_thu()`; chạy lại bộ tự kiểm của chính giao
diện ấy (không sửa tệp):

```text
$ env -u VIP_KHO_DANG_CHAY VIP_HUB_DATA=<tạm> python3 app/thu/thu_g22_cauhinh.py
Ran 17 tests in 1.237s
OK
exit 0
```

---

## 7. RÀNG BUỘC ĐÃ GIỮ

- **Sản phẩm không bị sửa**: `git diff` chỉ có 3 tệp bộ thử/bootstrap + 2 tệp mới.
  `app/migrate.py`, `app/cau_hinh.py`, `app/server.py`, DB nghiệp vụ: **0 thay đổi**.
- **Không nới cổng**: mọi lượt chưa khai vẫn `TỪ CHỐI: CHƯA KHAI kho đang chạy`; không thêm
  `KHO_DANG_CHAY = "sqlite"` vào cấu hình; không đặt biến toàn cục trong `chay_tat_ca.sh`.
- **Cách ly**: mọi `VIP_HUB_DATA` dùng trong lượt đo là `mktemp -d`/`tempfile.mkdtemp` ngoài
  cây repo; helper từ chối nền trong repo và volume `/du-lieu`; không dùng dữ liệu thật.
- **Không xoá test / bỏ assertion / thêm skip / nuốt exception / đổi exit cho xanh.** Số ca
  không giảm: G01 giữ 21, G19 tăng 49 → 50 do **thêm** phép đo cách ly cho route mới, E2E giữ 41.
- **Không push/deploy**, không gọi hãng, không credential, không mở LIVE, BEST-09 giữ BLOCKED.

---

## 8. CÒN LẠI / BÀN GIAO

- **R1 đã hết trong ba bộ thuộc phạm vi**: G01/G02, G19 route, E2E shell xanh hoàn toàn bởi
  bootstrap của chính chúng, không phụ thuộc người chạy nhớ `export`.
- **`app/thu/chay_e2e.sh`** không nằm trong danh sách PHẠM VI ban đầu nhưng là **entrypoint thứ
  ba** của cùng R1 (QA §4 xếp nó vào R1). Đã sửa **một dòng export ở bootstrap** và ghi rõ ở
  đây để coordinator đối chiếu; nếu làn khác sở hữu tệp này thì thay đổi là một dòng, dễ hoàn.
- **Việc chẩn đoán của QA vẫn đúng**: các bộ R2/R3 khác (`thu_qa_soat.py::test_q09f`, G20,
  Chromium, PostgreSQL shm…) **không** được sửa trong lượt này; không tuyên bố toàn hồi quy xanh.
- `thu_qa_nguyennhan.py` trong lượt `QANN_REPO` vẫn xanh 11/11, nên bảng phân loại R1→R2/R3 vẫn
  dùng được; không cần sửa bộ phân loại.

---

## 9. TỆP ĐÃ THAY ĐỔI

| Tệp | Loại |
|---|---|
| `app/thu/thu_g01_g02.py` | bootstrap khai kho; `test_010` theo hợp đồng; `test_014` theo hợp đồng khôi phục |
| `app/thu/thu_g19_route.py` | bootstrap khai kho; bất biến tập hợp thay ghim `31/32`, `103/104`; thêm ca `/api/v2/don/loc-mo-ta` |
| `app/thu/chay_e2e.sh` | export `VIP_KHO_DANG_CHAY=sqlite` trên nền `mktemp -d` đã xác minh |
| `app/thu/thu_r1_bootstrap.py` | **mới** — bộ tự kiểm cơ chế bootstrap + đối chứng âm |
| `docs/R1_BOOTSTRAP.md` | **mới** — báo cáo này |

---

## 10. TRẠNG THÁI GIT — CHƯA COMMIT ĐƯỢC (BÁO AG-00)

Sandbox của lượt này **chặn ghi `.git`**. Cả `git add` và `git commit` đều thoát **128** với
cùng một lỗi, nên thay đổi **chưa được commit** và **chưa được stage**:

```text
$ git add app/thu/thu_g01_g02.py app/thu/thu_g19_route.py app/thu/chay_e2e.sh \
        app/thu/thu_r1_bootstrap.py docs/R1_BOOTSTRAP.md
fatal: Unable to create
'/Users/viporder/Projects/vip-express-hub/.git/worktrees/r1-bootstrap/index.lock':
Operation not permitted
exit 128
```

Năm tệp nằm nguyên trên đĩa trong worktree `r1-bootstrap` (`git status --short`):
`M app/thu/chay_e2e.sh`, `M app/thu/thu_g01_g02.py`, `M app/thu/thu_g19_route.py`,
`?? app/thu/thu_r1_bootstrap.py`, `?? docs/R1_BOOTSTRAP.md`.
**Đề nghị AG-00 commit hộ** đúng năm tệp này; không push, không gộp nhánh.
