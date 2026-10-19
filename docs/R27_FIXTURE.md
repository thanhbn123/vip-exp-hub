# R27 — CÔ LẬP FIXTURE: G21 BÍ MẬT · G22 CHỐT CÂY

**Nền đo:** `best/integration` @ `c909ebb` (nhánh `r27-isolation`). `main = de740dc` **không dùng**.
**Phạm vi sửa:** `app/thu/thu_g21_bimat.py` · `app/thu/thu_g22_chotcay.py` ·
`app/thu/thu_r27_fixture.py` (mới) · `docs/R27_FIXTURE.md` (mới).
**Không sửa:** mã sản phẩm, `chay_tat_ca.sh`, các bộ R2/R3/R6, DB nghiệp vụ, credentials, LIVE.

Báo cáo QA dùng để đối chiếu: `docs/QA_NGUYENNHAN.md` §5 (trong worktree này tệp chưa được R1
commit; đọc từ `r1-bootstrap`, chạy bộ tự kiểm của R1 với `QANN_REPO` trỏ về worktree này).

---

## 1. Nguyên nhân gốc (đo TRƯỚC khi sửa)

| Bộ | Lỗi trước sửa | Nguyên nhân gốc |
|---|---|---|
| `thu_g21_bimat.py` | **exit 1 · Ran 33 · failures=1** — `Z4` báo `['vh-g21bimat-goc-qhez_tsf'] != []` | `Z4` quét **toàn bộ** `tempfile.gettempdir()` theo tiền tố `vh-g21bimat-*`/`vip-hub-g21-*` và phán "bộ thử để lại rác". Thư mục ấy do **lượt khác** tạo; fixture không cô lập, và nếu "vá" bằng cách xoá mọi thư mục khớp tiền tố thì sẽ **xoá tài nguyên của lượt khác**. Chỉ đổi `TMPDIR` sang thư mục sạch: exit 0, 33 ca (QA đo được). |
| `thu_g22_chotcay.py` | **exit 1 · Ran 11 · failures=2** (D2, D4) | **D2** chạy cổng trên **CÂY THẬT** rồi đòi cây ấy có sẵn tệp mới của "làn khác" (`len(_dong_porcelain()) >= 1`); trên cây sạch D2 ĐỎ vì phép canh chống rỗng, không phải vì sản phẩm. **D4** lấy "bản khác bản đang có GẦN NHẤT" rồi đòi nó hỏng; trên nền này bản ấy (`6ac4d0a8`) đã **ĐẠT** quy tắc nên tiền đề sai. |

Không có bằng chứng nào cho thấy sản phẩm rò bí mật hay chốt cây hỏng: đây là **lỗi fixture**.

---

## 2. Đã sửa gì

### 2.1. `thu_g21_bimat.py` — mỗi lượt có gốc tạm riêng, chỉ dọn của mình

- Mỗi lượt tạo **một gốc tạm riêng** `vh-g21bimat-luot-<ngẫu nhiên>` (trước đây là
  `...-goc-`); **mọi** thư mục tạm của lượt (`dung_nen_tam`, tiến trình con, máy chủ phụ) được
  tạo **bên trong gốc ấy** và ghi vào sổ `_TAM_DA_TAO`.
- `Z4` **không còn quét TMPDIR**. Nó canh hai thứ của chính lượt: (a) mọi đường đã đăng ký trong
  `_TAM_DA_TAO` phải đã biến mất; (b) trong gốc tạm của lượt không được còn **thư mục con lạ**.
  Vì vậy nó vẫn bắt được rác do chính mình để lại (kể cả thư mục SQLite "mọc lại" sau `rmtree`),
  nhưng **không thấy và không đụng** thư mục của lượt khác.
- `tearDownModule` chỉ xoá gốc **khi chính lượt này tạo nó** (`_TAM_GOC_DO_TOI`). Không có lệnh
  nào xoá theo tiền tố/scan.

### 2.2. `thu_g22_chotcay.py` — D2 trên bản sao, D4 chọn đúng bản

- **D2:** dựng **bản sao (clone HEAD) trong thư mục tạm**, tự thêm đúng **một** tệp của làn khác
  (`docs/_r27_lan_khac.md`), chạy 4 cổng trên bản sao rồi xoá. Cây thật được chụp `git status`
  trước/sau và **phải không đổi**. Phép canh chống rỗng giữ nguyên: bản sao phải có thay đổi
  ngoài làn của từng bản sao. TMPDIR của các cổng con được cô lập trong thư mục tạm của bản sao.
- **D4:** thêm `nguon_cu_hong()` — lấy bản lịch sử **GẦN NHẤT mà `kiem_quy_tac` BẮT ĐƯỢC** (bỏ
  qua các bản đã ĐẠT; bỏ qua bản chưa có ca cổng). In rõ bản "khác gần nhất" bị bỏ qua. Không
  nới quy tắc, không bỏ assertion; D6 vẫn là đối chứng **mẫu sai tiêm có chủ đích**.

---

## 3. Bằng chứng chạy THẬT

### 3.1. Hai bộ sau khi sửa

| Bộ | Lệnh | Exit | Kế hoạch | Có kết quả | Bỏ qua | Chưa chạy | Ghi chú |
|---|---|---:|---:|---:|---:|---:|---|
| G21 bí mật | `python3 app/thu/thu_g21_bimat.py` | **0** | 33 | **33** | 0 | 0 | `Ran 33 tests` · `OK`; thư mục lạ của lượt khác vẫn nằm trong TMPDIR mà bộ thử vẫn xanh |
| G22 chốt cây | `python3 app/thu/thu_g22_chotcay.py` | **0** | 11 | **11** | 0 | 0 | `Ran 11 tests` · `OK`; D2 4/4 bản sao XANH trên bản sao; D4 4/4 bản lịch sử bị bắt |
| R27 fixture | `python3 app/thu/thu_r27_fixture.py` | **0** | 4 | **4** | 0 | 0 | `Ran 4 tests` · `OK` |

Không cộng các dòng `Ran 1` của tiến trình con (G21 F/G, G22 D2/D3) vào số ca của bộ cha — đó là
output con, đã nằm trong `Ran 33`/`Ran 11`.

### 3.2. Bảng "chạy SONG SONG 2 lượt" (R27.1)

Cùng **một `TMPDIR`**, hai lượt G21 khởi chạy đồng thời; trong TMPDIR có sẵn một thư mục
`vh-g21bimat-cua-luot-khac/` + mốc nội dung (đại diện tài nguyên của lượt khác).

| Lượt | Bắt đầu (s) | Kết thúc (s) | Exit | Ran | Bỏ qua | Hỏng | Lỗi |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.000 | 16.758 | 0 | 33 | 0 | 0 | 0 |
| B | 0.001 | 16.758 | 0 | 33 | 0 | 0 | 0 |

- **Gốc tạm RIÊNG quan sát ĐỒNG THỜI: 2** — `vh-g21bimat-luot-1ua21d12`,
  `vh-g21bimat-luot-vnc1arhw`.
- Sau khi cả hai xong: **0** gốc tạm còn lại (mỗi lượt dọn gốc của chính nó).
- Thư mục + mốc của "lượt khác": **CÒN NGUYÊN** (không bị lượt nào xoá/sửa).

### 3.3. Đối chứng âm (fixture dùng chung / phép canh rỗng phải ĐỎ lại)

| Đối chứng | Cách dựng | Kết quả đo |
|---|---|---|
| **G21 — gốc tạm DÙNG CHUNG** | Chạy G21 với `VIP_G21_TAM_GOC` trỏ vào gốc đã có thư mục `vh-g21bimat-cua-luot-khac/` bên trong | **exit 1 · Ran 33 · failures=1 · `FAIL: test_z4_khong_con_thu_muc_tam_cua_bo_thu`**; thư mục lạ **CÒN NGUYÊN**. Chứng minh `Z4` không bị bịt mắt và không xoá tài nguyên lạ. |
| **G22 — D2 trên bản sao SẠCH** | Cùng hàm `do_d2_tren_cay()` trên bản sao HEAD **không** có tệp làn khác | **5 lỗi**, gồm `cây SẠCH TRƠN ⇒ phép đo rỗng` + 4 lỗi riêng cho 4 bản sao; 4 cổng vẫn xanh (đúng kiểu "xanh vô nghĩa" mà phép canh phải bắt). |
| **G22 — D4 theo cách chọn CŨ** | So "bản khác gần nhất" với "bản gần nhất bị bắt" trên 4 bản sao | **3/4** bản "khác gần nhất" **ĐẠT** quy tắc (g20 `6ac4d0a8`, g17/g18 `7a60385a`), nên cách chọn cũ sai tiền đề; cả 4 bản bị bắt mới đều `ĐẠT=False`. |

---

## 4. Tái lập

```sh
cd /Users/viporder/orca/workspaces/vip-express-hub/r27-isolation

# Hai bộ mục tiêu
python3 app/thu/thu_g21_bimat.py          # exit 0 · Ran 33 · OK
python3 app/thu/thu_g22_chotcay.py        # exit 0 · Ran 11 · OK

# Bằng chứng song song + đối chứng âm + g22 lồng
python3 app/thu/thu_r27_fixture.py -v     # exit 0 · Ran 4 · OK
```

Bộ tự kiểm phân loại của QA (không sửa phần phân loại; tệp không có trong worktree nền):

```sh
QANN_REPO=$PWD python3 ../r1-bootstrap/app/thu/thu_qa_nguyennhan.py
# exit 0 · Ran 11 · OK
```

---

## 5. Ràng buộc đã giữ

- Local-first; **không** push/deploy/tunnel; **không** gọi API hãng (kể cả sandbox); **không**
  credentials; **không** mở `CHO_PHEP_LIVE`; **không** đụng PostgreSQL/`:5432`; **không** sửa DB
  nghiệp vụ. G22 D2 chỉ tạo bản sao trong thư mục tạm và **không đổi cây thật** (có canh
  `git status` trước/sau). BEST-09 vẫn BLOCKED (không chạm).
- Không xoá test, không bỏ assertion, không thêm skip, không nuốt exception, không đổi exit để
  xanh, không chỉ sửa số kỳ vọng. Các con số trong báo cáo là số runner công bố, tách
  kế hoạch/có kết quả/bỏ qua/chưa chạy.
- Không ghi `.git` (không tự bấm duyệt sandbox). Lệnh stage thật đã chạy:
  `git add app/thu/thu_g21_bimat.py app/thu/thu_g22_chotcay.py app/thu/thu_r27_fixture.py docs/R27_FIXTURE.md`
  → **exit 128**, `fatal: Unable to create
  '/Users/viporder/Projects/vip-express-hub/.git/worktrees/r27-isolation/index.lock': Operation
  not permitted` (`[sandbox: file access denied under workspace-write mode]`). Không có
  `index.lock` tồn tại trước lệnh. Theo luật AG-00: **báo AG-00 commit hộ**; working tree vẫn đủ
  4 tệp, không có thay đổi nào bị mất.
