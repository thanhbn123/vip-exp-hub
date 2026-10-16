# G22 — SAO LƯU / KHÔI PHỤC: ĐÓNG `do2b` VÀ BỎ ĐỒNG HỒ NGẦM KHỎI CA ĐO

> **Phạm vi được ghi của lượt này:** `app/migrate.py` · `app/cau_hinh.py` · `app/thu/thu_g21_saoluu.py`
> · `trien_khai/g20-saoluu/*` · `app/thu/thu_g22_saoluu.py` (mới) · `docs/G22_SAOLUU.md` (mới).
> **KHÔNG** sửa `app/csdl.py`; **KHÔNG** sửa tệp nào của bộ thử ngoài danh sách trên.
> Không push · không deploy · không tunnel · không mở `CHO_PHEP_LIVE` · không gọi API hãng ·
> không credentials thật · không PostgreSQL nghiệp vụ (D-8) — cụm PostgreSQL duy nhất dùng ở đây là
> cụm RIÊNG của bộ đo, TỪ CHỐI cổng `:5432`.

---

## 0. Tóm tắt một màn hình

Hai việc, cả hai đều là **sửa lỗi sản phẩm**, không phải sửa ca cho xanh:

| | Trước (G21) | Sau (G22) | Bằng chứng |
|---|---|---|---|
| **S8 / `do2b`** — `hub.db` CŨ còn sót + deployment CHƯA KHAI | `sao_luu()` thoát **0**, trả một bản sao TRÔNG HỢP LỆ (51 bảng, 34.336.000 đ) mà **không chứa một dòng nào** của 9.324.000 đ đang phục vụ ở PostgreSQL ⇒ `S8` = FAIL_OPEN, **1/10 ca FAIL_CLOSED** | **TỪ CHỐI**, `rc = 1`, thông báo nêu rõ thiếu gì · khai ở đâu · trên đĩa đang có gì ⇒ `S8` = **FAIL_CLOSED**, **10/10 ca FAIL_CLOSED** | §3 (bảng `do1/do1b/do2a/do2b/do3`), §6 (`B2`/`B3`) |
| **Ca E3** — "ba lượt khôi phục cùng một giây không được xoá nhau" | Ba lượt **đọc `datetime.now()` ngầm**, có thể rơi vào 2–3 mốc khác nhau ⇒ phép đếm XANH mà **đường ĐÈ chưa hề được chạm tới**; kết quả phụ thuộc tốc độ máy | Mốc thời gian là **ĐẦU VÀO** (`sao_luu(luc=)` / `khoi_phuc(luc=)`); bộ đo truyền **một mốc CỐ ĐỊNH**, và bộ đo **TỪ CHỐI kết luận** nếu ba bản cất không cùng mang mốc đó | §5, bảng riêng/chung |

Không `retry` ở đâu cả. Không ca nào bị xoá, không điều kiện nào bị nới — hai ca PIN hành vi cũ
được **viết lại theo bất biến ĐÚNG và CHẶT HƠN** (`test_a9`, `test_c4` của G21), và một ca đo
"cái giá của quyết định" (`test_c9`) được đổi thành **phép tiêm có răng** (`D5`).

---

## 1. Lệnh chạy lại TOÀN BỘ bằng chứng của lượt này

```sh
python3 trien_khai/g20-saoluu/chay_do.py                 # B0…B9, in bảng, ghi JSON vào ket_qua/
python3 trien_khai/g20-saoluu/do_8_bo_ngoai.py --json trien_khai/g20-saoluu/ket_qua/g22_8_bo_ngoai.json
sh    trien_khai/dien_tap_khoi_phuc.sh                   # (AG-05) hai chế độ khai / chưa khai
python3 app/thu/thu_g21_saoluu.py                        # 23 ca
python3 app/thu/thu_g22_saoluu.py                        # 14 ca (mới)
python3 app/thu/thu_g20_saoluu.py                        # 41 ca — bộ thử AG-04, KHÔNG sửa tệp
```

Kết quả thô: `trien_khai/g20-saoluu/ket_qua/` (`chay_do_g22.log`, `chay_do.json`, `truoc.json`,
`sau.json`, `tiem_d*.json`, `g22_8_bo_ngoai.json`, `g22_dien_tap_*.log`).

> Hai tệp trong thư mục đó là **DI VẬT của lượt TRƯỚC**, không phải kết quả của lượt này:
> `chinh_sach_tu_choi.json` (biến thể `chinh_sach_tu_choi` **đã bị bỏ** — nay là mặc định của
> tệp thật, xem `B4.D5`) và `chay_do.log` (log của lượt trước). Lượt này ghi vào
> `chay_do_g22.log`. Chúng được GIỮ LẠI, không xoá: chúng là số đo của lượt trước, và xoá số đo
> cũ là cách chắc chắn nhất để lượt sau không dựng lại được bảng TRƯỚC/SAU.

---

## 2. Đã sửa gì, ở đâu (kèm SHA-256 của tệp cuối)

| Tệp | Sửa gì |
|---|---|
| `app/cau_hinh.py` | Thêm chốt cấu hình **`KHO_DANG_CHAY`** (+ `KHO_SQLITE`, `KHO_POSTGRESQL`, `BIEN_KHAI_KHO`). **Mặc định `None` = CHƯA KHAI = TỪ CHỐI.** Không suy ra từ mtime/kích thước/tên tệp. |
| `app/migrate.py` | Bỏ hẳn công tắc `CHINH_SACH_CHUA_KHAI`; thêm `_tu_choi_chua_khai()` (chốt 4b) và cho `khoi_phuc(..., luc=)` / `sao_luu(luc=)` / `_duong_chua_dung(..., luc=)` nhận **mốc thời gian qua THAM SỐ**. |
| `trien_khai/g20-saoluu/kich_ban.py` | `moi_truong(khai_kho=…)` · `sao_luu(khai_kho=…)` · `khoi_phuc(luc=…)`: mọi kịch bản **KHAI RÕ `sqlite`** (đúng thứ chúng là), trừ những vế **CỐ Ý** đo nhánh "chưa khai" (`do1b`, `do2b`). Ca E3 nhận `LUC_BA_LUOT = "20261016-120000"` và ghi lại `cung_mot_moc`. |
| `trien_khai/g20-saoluu/fail_closed.py` | `S8`: phán quyết `do2b` **đảo dấu** (nay `rc == 0` ⇒ ĐỎ) + vế (b) "phải NÓI RA"; thêm vế `do1b`. `S4`: thêm chốt **PHÉP ĐO KHÔNG DỰNG ĐƯỢC** nếu ba bản cất không cùng một mốc. |
| `trien_khai/g20-saoluu/ban_va.py` | Bản vá khai thành **19 mảnh** (mỗi mảnh phải có mặt ĐÚNG MỘT lần) + **4 mảnh đường cũ phải VẮNG**; **5 phép tiêm** `D1…D5` (`D5` = nới lại chính sách cũ); bỏ biến thể `chinh_sach_tu_choi` (nay là mặc định của tệp thật). |
| `trien_khai/g20-saoluu/do_postgres.py` | `do2b` **khai rõ "chưa khai"** + đo `bao_ro`; thêm `do1b`; đối chứng đường `D4` **khai `sqlite`** (nếu không nó TỪ CHỐI vì lý do không liên quan tới thứ nó đo). |
| `trien_khai/g20-saoluu/chay_do.py` | `B4` thêm `D5`; `B5` cũ (biến thể chính sách) **đổi thành CA E3 CHẠY RIÊNG ×3**, `B7` là **CHẠY CHUNG**; thêm `B9` (bộ thử G22); chốt chống **nhãn tiêm không phân tích được** (xem §6). |
| `trien_khai/g20-saoluu/do_8_bo_ngoai.py` *(mới)* | Đo **cái giá** của mặc định mới trên các bộ thử ngoài vùng được ghi + diễn tập khôi phục: hai chế độ `chua_khai` / `khai_sqlite`. |
| `app/thu/thu_g21_saoluu.py` | `test_a9`, `test_c4` viết lại theo bất biến mới (10/10, không còn ngoại lệ `S8`); `test_c9` đổi thành đối chứng âm `D5`; `BC_DAT` và các phép tiêm `S4`/`S8` bổ sung vế mới. |
| `app/thu/thu_g22_saoluu.py` *(mới)* | 14 ca cho hai bất biến của lượt này (kho đang chạy · mốc thời gian là đầu vào), mỗi ca phủ định đều có ĐỐI CHỨNG ĐƯỜNG. |

**SHA-256 của tệp lúc đo** — mọi con số trong tài liệu này gắn với đúng bộ băm dưới đây:

```
aad036c4a98e653cc6785b30d9813166703375a6d3a5d9c6c2b22be747dfdf67  app/migrate.py
3c9a0f29a2707976557d202766609d2a574ddc160ff7dbc2a2230f85bfad346d  app/cau_hinh.py
2d715a54730c5e743461429f6bbaae3f9b0f0637cbf33ce64cf22b6a14fe2006  app/thu/thu_g21_saoluu.py
4d3229baf4abc39040a87b2df0cf6a7ee60b4aecc9724414c1c151e10896eee8  app/thu/thu_g22_saoluu.py
4f05268cd7314c8497f5a22c13ff3224d6b12c4015fda52874fc6fc32c351b16  trien_khai/g20-saoluu/kich_ban.py
ebbe705220512f38d81e741e919c5328eb8ed41d17c33866bcbc4b76a8fa699d  trien_khai/g20-saoluu/fail_closed.py
4e02b93c6ea270d9fd596bb58897640156d0da80358b36dd9a680fee241fd808  trien_khai/g20-saoluu/ban_va.py
1595db12971c2af33e2c77f18fc5ec086448451b37a7411d93803c04c196d576  trien_khai/g20-saoluu/do_postgres.py
2bbdd9f15474296da1d6111896621f5ab07b45410378a28fdf90613ad1256a3c  trien_khai/g20-saoluu/chay_do.py
c0a69143ea7b4c626a7c9e0930aee623220ba0b36b4bc9dec6a88bb6a4850730  trien_khai/g20-saoluu/do_8_bo_ngoai.py
```

Phạm vi ảnh hưởng của từng phép đo (để lượt sau không đo thừa): bảng §4 (các bộ ngoài) và hai lượt
`dien_tap_khoi_phuc.sh` **chỉ phụ thuộc `app/migrate.py` + `app/cau_hinh.py`** — hai tệp đó không
đổi sau lượt đo ấy; bảng §6 phụ thuộc cả bộ đo, nên nó được chạy lại **sau cùng**.

---

## 3. VIỆC 1 — ĐÓNG `S8`/`do2b`

### 3.1 Chốt được chốt ở đâu, và vì sao ở đó

`app/cau_hinh.py` — chỗ chính thức của cấu hình:

```python
KHO_SQLITE = "sqlite"
KHO_POSTGRESQL = "postgresql"
BIEN_KHAI_KHO = "VIP_KHO_DANG_CHAY"
KHO_DANG_CHAY = (os.environ.get(BIEN_KHAI_KHO) or "").strip().lower() or None   # None = CHƯA KHAI
```

`None` ⇒ `migrate.sao_luu()` **TỪ CHỐI**. Không có công tắc nào khác: công tắc cũ
(`CHINH_SACH_CHUA_KHAI = "sqlite"`) **đã bị BỎ**, vì chính nó là khoảng hở — nó biến "không biết"
thành "coi như SQLite" rồi vẫn trả mã thoát 0.

Lý do phải là KHAI BÁO chứ không phải phép đo: `app/csdl.py` thuần SQLite, hệ **không có** cách
nào tự biết dữ liệu nghiệp vụ đang ở đâu. Một `hub.db` CŨ còn sót và một `hub.db` đang phục vụ
**không phân biệt được** bằng mtime, kích thước hay tên tệp — nên hàm không đoán, và câu trả lời
duy nhất có thẩm quyền là của người triển khai.

### 3.2 Thông báo (nguyên văn, `rc = 1`)

```
$ VIP_HUB_DATA=/tmp/g22msg/A python3 -c "import sys;sys.path.insert(0,'app');import migrate;print(migrate.sao_luu())"
rc=1
[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này
          có chứa dữ liệu đang phục vụ hay không (chưa có nguồn nào khai).
          TRÊN ĐĨA ĐANG CÓ `hub.db` tại /tmp/g22msg/A/hub.db.
          Tệp đó CÓ THỂ là kho đang phục vụ, CŨNG CÓ THỂ là tệp CŨ còn sót lại sau
          khi dữ liệu đã chuyển sang PostgreSQL. Hai thứ đó KHÔNG phân biệt được
          bằng mtime / kích thước / tên tệp — nên hàm này KHÔNG đoán.
          Khai MỘT trong hai:
            · `KHO_DANG_CHAY = 'sqlite'` (hoặc 'postgresql') trong app/cau_hinh.py, hoặc
            · biến môi trường VIP_KHO_DANG_CHAY=sqlite|postgresql cho tiến trình chạy `migrate`.
          Nếu kho đang chạy là PostgreSQL: `sao_luu()` KHÔNG dùng được — sao lưu bằng
          `pg_dump -Fc`; xem docs/G22_SAOLUU.md.
          Nếu kho đang chạy là SQLite: khai `sqlite` rồi chạy lại. Chốt này cố ý KHÔNG có
          mặc định: một mặc định ở đây là một phép đoán, và phép đoán đó trả mã thoát 0.
```

Khi trên đĩa **không** có `hub.db`, cùng chốt đó in dòng `Trên đĩa cũng KHÔNG có 'hub.db' tại …`
— thông báo không được phép nói "hub.db cũ còn sót" khi nó không tồn tại.

### 3.3 Bảng `do1 / do1b / do2a / do2b / do3` — TRƯỚC và SAU

Đo trên **cụm PostgreSQL RIÊNG** (`do_postgres.py`, TỪ CHỐI `:5432`, có vân tay cụm hệ thống
trước/sau), dữ liệu PostgreSQL thật: 6 đơn · 6 bút toán · **9.324.000 đồng**; `hub.db` cũ có
**51 bảng · 34.336.000 đồng**.

| Vế | Đo cái gì | TRƯỚC (G21, `truoc.json`/`sau.json`) | SAU (G22) |
|---|---|---|---|
| `do1` | KHAI `sqlite` + `hub.db` **không tồn tại** | `rc=0` · tệp **4.096 byte / 0 BẢNG** / `integrity=ok` ⇒ ĐƯỜNG LÙI GIẢ, im lặng | **`rc=1`** |
| `do1b` *(mới)* | **CHƯA KHAI** + `hub.db` không tồn tại | `rc=0` · tệp 4.096 byte / `0` bảng (bản gốc **không có chốt nào** để chặn nhánh chưa khai) | **`rc=1`** · `bao_ro=True` |
| `do2a` | `hub.db` CŨ + ĐÃ KHAI `postgresql` | `rc=0` · trả tệp 561.152 byte | **`rc=1`** |
| `do2b` | `hub.db` CŨ + **CHƯA KHAI** ← khoảng hở P-G15-02 | **`rc=0`** · bản sao **51 bảng / 34.336.000 đ**, băm khớp đúng tệp SQLite cũ ⇒ **không chứa dòng nào của 9.324.000 đ đang chạy** | **`rc=1`** · `bao_ro=True` · **không** có tệp bản sao nào |
| `do3` | `khoi_phuc()` nhận một `pg_dump -Fc` THẬT (124.700 byte, `pg_dump` rc=0) | **`khoi_phuc_NHAN = True`** — bản gốc NHẬN và làm chết CSDL SQLite | `khoi_phuc_NHAN = False` (đã đóng từ G21) |

`S8` là **FAIL_CLOSED** khi và chỉ khi **cả năm** vế trên đều đúng — `phan_quyet` không gộp vế
nào, và vế `do2b` còn tách làm hai: `rc != 0` **(a)** và thông báo **NÓI RA** `(b)`. Một `rc != 0`
im lặng vẫn bắt người trực đi đoán, nên nó không được tính là đạt.

### 3.4 Bộ đo PHẢI phân biệt được — phép tiêm `D5`

Kết luận "S8 đã đóng" chỉ có nghĩa nếu **nới chốt ra thì bộ đo ĐỎ**. `ban_va.TIEM_LOI` có thêm:

```
D5 — nới lại CHÍNH SÁCH CŨ: chưa khai ⇒ coi kho là SQLite rồi đi tiếp   ⇒  PHẢI bị S8 bắt
     '    if kho is None:\n        _tu_choi_chua_khai(nguon)\n'
  →  '    if kho is None:\n        kho = KHO_SQLITE  # D5: chưa khai ⇒ COI LÀ SQLITE (chính sách cũ, đã bị bỏ)\n'
```

Phép thay áp lên **TỆP THẬT** (`ban_va.doc_that()` đọc `app/migrate.py` từ đĩa), chạy **ĐÚNG bộ
đo** trên bản bị tiêm, và đòi `S8` chuyển FAIL_OPEN. Kết quả ở bước `B4.D5` (§6).

---

## 4. CÁI GIÁ của mặc định mới — ĐO, KHÔNG ĐOÁN

`migrate.chay()` trên một thư mục dữ liệu MỚI **có** gọi `sao_luu()` (`csdl.mo()` tạo
`schema_version` rỗng ⇒ `MAX(phien_ban)=0` ⇒ chạy nâng cấp). Nên khi "chưa khai ⇒ TỪ CHỐI" trở
thành mặc định, **mọi bộ thử gọi `chay()` mà không khai kho đều TỪ CHỐI**. Đó là cái giá, và nó
phải là con số đo được:

```sh
python3 trien_khai/g20-saoluu/do_8_bo_ngoai.py --json trien_khai/g20-saoluu/ket_qua/g22_8_bo_ngoai.json
```

| Bộ (ngoài vùng được ghi của AG-02) | `chua_khai` | `khai_sqlite` (một dòng khai) |
|---|---|---|
| `thu_giao_dich.py` | rc=1 | rc=0 · 17 ca · OK |
| `thu_han_muc_nguyen_tu.py` | rc=1 | rc=0 · 5 ca · OK |
| `dong_thoi/do_dong_thoi.py` *(không có `__main__`)* | rc=0 · OK | rc=0 · OK |
| `thu_qa_g18.py` | rc=1 · 46 ca · skip 1 · **23 đỏ** | rc=1 · 46 ca · skip 1 · **3 đỏ** (đỏ sẵn có — §7) |
| `thu_header_bao_mat.py` | rc=1 | rc=0 · 8 ca · OK |
| `thu_qa_g19.py` | rc=0 · 0 ca · skip 1 · OK | rc=0 · 0 ca · skip 1 · OK |
| `thu_g17.py` | rc=2 | rc=2 (thiếu tệp — không liên quan) |
| `thu_g17_baomat.py` | rc=1 | rc=0 · 31 ca · OK |
| `thu_migrate_dong_thoi.py` *(đo thêm)* | rc=1 · 8 ca · **2 đỏ** | rc=0 · 8 ca · OK |
| `trien_khai/dien_tap_khoi_phuc.sh` *(AG-05, đo thêm)* | rc=1 (dừng ở B1) | rc=0 · diễn tập chạy hết |

Kết luận rút ra từ đúng bảng trên, không phải từ suy luận:

* **Mọi bộ bị ảnh hưởng đều trở lại mức nền của chính nó bằng MỘT dòng khai**
  (`VIP_KHO_DANG_CHAY=sqlite`, hoặc `KHO_DANG_CHAY = "sqlite"` trong `app/cau_hinh.py`). Không
  phải bằng cách nới chốt, không phải bằng cách sửa ca.
* Một số dòng `rc=0` ở cột `chua_khai` **không** nghĩa là "bộ đó không bị ảnh hưởng": chúng
  không có khối `__main__` (chạy trực tiếp không đo gì), hoặc thiếu tệp, hoặc mọi ca đều bị
  `skip`. Cột `co__main__` trong JSON ghi rõ chuyện đó.
* Các ca đỏ **sẵn có** (đỏ ở CẢ HAI chế độ) được ghi riêng ở §7 — chúng không phải do chốt mới.

> **Việc còn lại của VIỆC 1.3 (ngoài vùng được ghi của AG-02):** 8 bộ thử + 1 diễn tập không
> thuộc danh sách tệp AG-02 được phép sửa, nên AG-02 **không** sửa chúng. Đường sửa đã được đo
> là đúng và rẻ: khai `VIP_KHO_DANG_CHAY=sqlite` cho tiến trình chạy bộ thử (hoặc export trong
> `app/thu/chay_tat_ca.sh`). Đã báo qua `worker_done`.

---

## 5. VIỆC 2 — CA E3 KHÔNG ĐƯỢC PHỤ THUỘC ĐỒNG HỒ

### 5.1 Khiếm khuyết, đo được chứ không suy luận

`ca_khoi_phuc_de_len_csdl_dang_chay()` gọi ba lượt `khoi_phuc()`. Tên bản cất do
`migrate._duong_chua_dung()` đặt bằng `datetime.now()` **ở dưới sâu trong sản phẩm**, nên:

* ba lượt có thể rơi vào **hai–ba mốc khác nhau**; khi đó **tên khác nhau ⇒ phép đếm "≥ 3" XANH**
  mà **đường ĐÈ chưa hề được chạm tới** ⇒ ca XANH trên một sản phẩm còn lỗi;
* kết quả phụ thuộc **tốc độ máy** ⇒ chạy riêng một kiểu, chạy chung một kiểu.

Bản ĐÓNG BĂNG (`trien_khai/g20-saoluu/migrate_nguyenban.py`, md5 `611182a621fd279c3816d5fc5d2785e3`)
chứng minh khiếm khuyết ở tầng API: nó **không có** tham số `luc`, tức mốc thời gian **không thể**
là đầu vào của `khoi_phuc()` — chỉ có thể đọc ngầm bên trong:

```
python3 … import migrate; migrate.khoi_phuc('/khong/co/that.db', luc='20261016-120000')
→ rc != 0 · TypeError: khoi_phuc() got an unexpected keyword argument 'luc'      (ca c1)
cùng lời gọi trên TỆP THẬT                                                     → rc != 0 vì KHÔNG THẤY TỆP (ca c2)
```

### 5.2 Cách sửa: mốc thời gian là THAM SỐ, và bộ đo TỪ CHỐI kết luận nếu nó không được truyền

* `migrate._duong_chua_dung(goc_ten, duoi, luc=None)` · `sao_luu(luc=None)` ·
  `khoi_phuc(duong_backup, toi_da_biet_chua_kiem_duoc=False, luc=None)`.
  `luc=None` (đường chạy thật) ⇒ `datetime.now()`; `luc` là `datetime` **hoặc chuỗi dùng nguyên
  văn** ⇒ tên mang ĐÚNG mốc đó.
* `kich_ban.LUC_BA_LUOT = "20261016-120000"` — mốc **CỐ ĐỊNH** của ca đo, truyền xuống **cả ba**
  lượt.
* Kịch bản ghi lại `cung_mot_moc`: ba bản cất có thật sự cùng mang mốc đã truyền không.
* `fail_closed.phan_quyet` (S4) **tố cáo "PHÉP ĐO KHÔNG DỰNG ĐƯỢC"** nếu `cung_mot_moc` sai —
  ca không thể XANH vì một lý do không liên quan.
* **KHÔNG retry.** Chạy lại cho tới khi XANH là che mất đúng thứ ca này sinh ra để đo.

### 5.2b Một ĐỎ-GIẢ-theo-hướng-XANH-GIẢ đã bị bắt trong chính lượt này

Khi bộ đo chạy trên **bản ĐÓNG BĂNG** (bản chưa có tham số `luc`), lời gọi
`khoi_phuc(path, luc=…)` nổ `TypeError`, và một vụ nổ như thế **cũng cho `rc != 0`** — tức nó
được tính là "TỪ CHỐI ĐẠT" ở mọi kịch bản vốn mong đợi sự từ chối. Đo được: lượt chạy đầu của G22
cho cột **TRƯỚC = 4/10 FAIL_CLOSED**, trong khi bảng của lượt trước là **1/10** — bốn ca XANH lên
vì một lý do **không liên quan** tới thứ chúng đo.

Cách chữa nằm ở bộ đo, không ở ca: `kich_ban._MA_KHOI_PHUC` **dò chữ ký** hàm, chỉ truyền `luc`
khi hàm nhận, và **in ra** `LUC-DUOC-NHAN True/False`; `kich_ban.khoi_phuc()` đọc thành `nhan_luc`;
`phan_quyet` (S4) **ĐÒI** `nhan_luc is True` trên bản đang đo, nếu không thì kết luận là
**"PHÉP ĐO KHÔNG DỰNG ĐƯỢC"** chứ không phải ĐẠT. Sau khi vá: cột TRƯỚC trở lại **1/10** (khớp
bảng lượt trước), cột SAU vẫn **10/10**.

### 5.3 Bảng E3 — chạy RIÊNG và chạy CHUNG

| Lượt chạy | Lệnh | `rc` | Số ca | Skip | `1 lượt → bản cất` | `3 lượt cùng mốc → bản cất` |
|---|---|---|---|---|---|---|
| Chạy **RIÊNG** — lượt 1 | `python3 app/thu/thu_g20_saoluu.py E_KhoiPhucDeLenCsdlDangChay` | 0 | 3 | 0 | 1 | **3** |
| Chạy **RIÊNG** — lượt 2 | (y hệt) | 0 | 3 | 0 | 1 | **3** |
| Chạy **RIÊNG** — lượt 3 | (y hệt) | 0 | 3 | 0 | 1 | **3** |
| Chạy **CHUNG** (cả bộ 41 ca) | `python3 app/thu/thu_g20_saoluu.py` | 0 | 41 | 0 | 1 | **3** |

Ba lượt "RIÊNG" là ba lượt **ĐỘC LẬP CÓ CHỦ Ý** (đo tính tất định), không phải ba lần thử lại:
cả ba cho **cùng** kết quả, cùng tên bản cất (`test_b4` của bộ thử G22 so cả DANH SÁCH TÊN, không
chỉ con số đếm).

Tầng API cũng được đo trực tiếp (`app/thu/thu_g22_saoluu.py`, lớp `B_DongHoLaDauVao`):

* `b1` — tên bản sao lưu là `hub-truoc-migrate-20261016-120000.db`: mang **ĐÚNG mốc đã truyền** và
  **KHÔNG** chứa giờ hệ thống (nếu sản phẩm đọc đồng hồ ngầm, ca này ĐỎ);
* `b2` — ba lượt `khoi_phuc(luc=…)` cùng mốc ⇒ **3** bản cất, không xoá nhau;
* `b3` — **ĐỐI CHỨNG ĐƯỜNG**: mốc khác ⇒ tên khác (chứng minh `luc` không bị bỏ qua);
* `b4` — ca của bộ đo chạy **hai lần** ⇒ cùng số bản cất **và** cùng tên.

---

## 6. Bảng bằng chứng đầy đủ của lượt này

`python3 trien_khai/g20-saoluu/chay_do.py` — mỗi bước ghi **LỆNH THẬT · MÃ THOÁT THẬT · SỐ CA ·
SỐ SKIP**:

| Bước | `rc` | Số ca | Skip | Đo cái gì |
|---|---|---|---|---|
| `B0` | 0 | 9 | 0 | cú pháp 9 tệp (đọc bằng `ast.parse`) |
| `B1` | 0 | — | — | `ban_va.xac_nhan()`: **19 mảnh bản vá có mặt đúng 1 lần · 4 mảnh đường cũ VẮNG · 5 mốc tiêm còn nguyên** |
| `B2` | **1** | 10 | 0 | **TRƯỚC** — bản ĐÓNG BĂNG (`migrate_nguyenban.py`, md5 ghim): **1/10 FAIL_CLOSED**, còn đỏ `S1 S2 S3 S4 S5 S6a S6b S7 S8` |
| `B3` | **0** | 10 | 0 | **SAU** — **CHÍNH `app/migrate.py`**: **10/10 FAIL_CLOSED**, còn đỏ `(không)` |
| `B4.D1` | 0 | 1 | 0 | tiêm "chép thẳng lên CSDL đang chạy" ⇒ `S6b` **bắt được** (`dat=True`) |
| `B4.D2` | 0 | 1 | 0 | tiêm "tên bản cất theo giây, cho phép đè" ⇒ `S4` **bắt được** |
| `B4.D3` | 0 | 1 | 0 | tiêm "bỏ chốt TỤT SCHEMA" ⇒ `S5` **bắt được** |
| `B4.D4` | 0 | 2 | 0 | tiêm "bỏ mọi phép kiểm chứng" ⇒ `S3` **và** `S7` **bắt được** |
| `B4.D5` | 0 | 1 | 0 | **tiêm "nới lại chính sách cũ" ⇒ `S8` BẮT ĐƯỢC** (`dat=True`, `da_bat=['S8']`) |
| `B5.E3-rieng-1…3` | 0 | 3 | 0 | CA E3 chạy **RIÊNG**, ba lượt độc lập |
| `B6` | 0 | 23 | 0 | bộ thử G21 (`thu_g21_saoluu.py`) |
| `B7` | 0 | 41 | 0 | bộ thử **AG-04** (`thu_g20_saoluu.py`) — CA E3 chạy **CHUNG**; trước G22: `rc=1`, **1 ca đỏ `test_k4`** |
| `B9` | 0 | 14 | 0 | bộ thử G22 (`thu_g22_saoluu.py`, mới) |
| `B8.TRƯỚC` / `B8.SAU` | 0 | — | — | bảng từng bảng sinh từ JSON số đo, không chép tay |

`KẾT LUẬN: mọi bước đạt; E3 riêng/chung đều [3] bản cất` — `chay_do.py` trả `rc = 0`.

Đọc bảng này cho đúng:

* `B2` / `B3` / `B4` **không** phải "rc phải bằng 0": chúng chạy những kịch bản HỎNG, nên mã thoát
  ĐẠT của chúng là "bộ đo KẾT LUẬN ĐỎ" ⇒ `rc=1` là KẾT QUẢ ĐÚNG. `B3` = `rc 0` vì **10/10
  FAIL_CLOSED** (trước G22: `rc 1`, 9/10, còn đỏ `S8`).
* `B4.D5` là vế **đối chứng âm** quan trọng nhất: nới lại chính sách cũ ⇒ `S8` **PHẢI** đỏ.
* `B5` cũ (đo biến thể `chinh_sach_tu_choi`) **đã bị bỏ** cùng biến thể đó: quyết định ấy nay là
  mặc định của tệp thật, nên vế cần chứng minh là vế ngược lại (`B4.D5`). Chỗ `B5` nay là CA E3
  CHẠY RIÊNG.
* Một phép tiêm mà **nhãn không phân tích được** sẽ tách ra thành mã kịch bản không tồn tại, lọc
  còn **0 ca**, và bước đó báo "KHÔNG bắt được phép tiêm" — một ĐỎ vì **phép đo rỗng**, không
  phải vì sản phẩm. Lượt chạy đầu của G22 đã trúng đúng bẫy này; `chay_do.py` nay **NÉM** ngay
  tại chỗ thay vì để người đọc đi tìm một phép tiêm trượt.

Ba bộ thử, chạy trực tiếp (lệnh thật + mã thoát thật):

| Bộ thử | Lệnh | `rc` | Số ca | Skip |
|---|---|---|---|---|
| G21 — fail-closed | `python3 app/thu/thu_g21_saoluu.py` | **0** | 23 | 0 |
| G22 — kho đang chạy + đồng hồ (mới) | `python3 app/thu/thu_g22_saoluu.py` | **0** | 14 | 0 |
| AG-04 (G20) — vòng tròn sao lưu/khôi phục | `python3 app/thu/thu_g20_saoluu.py` | **0** | 41 | 0 |

Trước G22, dòng cuối là `rc = 1 · 41 ca · 1 đỏ` — ca đỏ là `test_k4_BAT_BIEN_hub_db_CU_khong_duoc_coi_la_du_lieu_dang_chay`,
tức **chính ca PIN khoảng hở `do2b`**. Nó XANH ở lượt này vì **sản phẩm đã sửa**, không phải vì
ca bị nới: `test_k4` và `test_k3`/`test_k5`/`test_k6` của tệp đó **không bị sửa một ký tự nào**
(AG-02 không được sửa tệp AG-04).

---

## 7. CÒN LẠI / CHƯA ĐÓNG — nói thẳng

| # | Việc | Vì sao chưa xong | Đề xuất |
|---|---|---|---|
| 1 | 8 bộ thử + 1 diễn tập ngoài vùng được ghi cần **một dòng khai** | AG-02 **không được sửa** tệp ngoài danh sách (§0). Đã ĐO cả hai chế độ ở §4 | AG-00/AG-05 thêm `VIP_KHO_DANG_CHAY=sqlite` vào môi trường chạy bộ thử (`app/thu/chay_tat_ca.sh`) hoặc vào từng bộ |
| 2 | Cây đang **BẨN** (`git status`: `app/migrate.py`, `app/cau_hinh.py`, … chưa commit) | AG-02 **không** tự vượt `.git`; việc commit là của AG-00 | AG-00 commit để `test_a1_cay_sach_theo_pham_vi_wave` của `thu_qa_g18` hết đỏ |
| 3 | `docs/G21_BACKUP_RESTORE.md` §CÒN HỞ nay **đã cũ** (`do2b` đã đóng) | Tệp này **không** nằm trong vùng được ghi của lượt này | Chủ tệp (AG-02 lượt trước) trỏ sang `docs/G22_SAOLUU.md` §3 |
| 4 | `thu_migrate_dong_thoi.py` từng đỏ **KHÔNG ỔN ĐỊNH** ở `test_a1` (`[Errno 2] No such file or directory` / `disk I/O error` ở 6/8 tiến trình con) | Đo HAI lượt: lượt đầu đỏ ở **cả hai** chế độ (⇒ không phải chốt mới), lượt sau với `khai_sqlite` **8/8 OK** ⇒ ĐỎ KHÔNG ỔN ĐỊNH của môi trường/temp-dir. Delta do chốt mới chỉ là `test_a2`, và nó biến mất khi khai | Nếu tái diễn: AG-00/AG-05 xem temp-dir của 8 tiến trình con |
| 5 | `thu_qa_g18::test_b1_tang_3…` đỏ **sẵn có** | Tầng-3/E2E: sandbox chặn ghi `thu_giao_dien/_bao-cao/`, `_ket-qua/` — đúng cảnh báo đã có từ trước | Đọc LOG trước khi kết luận; không phải lỗi sản phẩm của lượt này |
| 6 | Bản sao lưu **PostgreSQL** thật (`pg_dump -Fc`) + khôi phục thử | Ngoài phạm vi AG-02 (chặng 3 của `trien_khai/postgres/`) | Giữ nguyên là việc của chủ chặng đó |

---

## 8. Bất biến của lượt này, phát biểu để lượt sau không nới

1. `sao_luu()` **không bao giờ** trả mã thoát 0 khi chưa biết chắc kho đang chạy là kho nào. Không
   có mặc định, không có công tắc, không đoán từ mtime/kích thước/tên tệp.
2. Từ chối thì **phải NÓI RA**: thiếu gì · khai ở đâu · trên đĩa đang có gì.
3. Mọi ca đo về **THỜI GIAN** phải nhận mốc qua **THAM SỐ**. Đọc `datetime.now()` ngầm trong một
   ca đo là biến kết quả thành hàm của tốc độ máy.
4. Ca nào không dựng được phép đo của nó thì phải báo **"PHÉP ĐO KHÔNG DỰNG ĐƯỢC"**, không được
   tính là ĐẠT.
5. Không `retry` để xanh. Không nới điều kiện. Không xoá ca.
