# G22 — CẤU HÌNH "KHO ĐANG CHẠY": KHAI RÕ TRONG NỀN KIỂM THỬ CÔ LẬP, GIỮ NGUYÊN FAIL-CLOSED

**Vai:** AG-01 (CODE AGENT) · **Task:** `task_d84156884830` · **Dispatch:** `ctx_9c1c48abfc1e`
**Nền:** `integration/g20` @ `a76ec51c9931b62451721302446d7c3b74b9c81f`
(cây `4676e5c53288e21e7c1a87e6bdde9a12c295a147`)
**KHÔNG** dùng `main` (`de740dc`) · **KHÔNG** mở G23.

**Phạm vi được ghi (và chỉ sáu tệp này):**

| Tệp | Loại | sha256 SAU khi sửa |
|---|---|---|
| `app/cau_hinh.py` | sửa | `5fa242ded0788426c278c4a7b9e19a1a25387266e75ad347d259addfd931da0f` |
| `app/migrate.py` | sửa | `4b66ef7ca290dc30a45e8c812eb0f3c87e5995c68bbf969099171a4c354f5cde` |
| `.env.example` | sửa | `449ffe184cd1bd4ebe898df958fe97828b6d8d80ef02fb2932187dc7625ff3d0` |
| `trien_khai/dien_tap_khoi_phuc.sh` | sửa | `b6bdf692043a892ed0520903739824d76b0eacbaf1a0acf827e1b089a983c1b7` |
| `app/thu/thu_g22_cauhinh.py` | **mới** | `a1580f270cbc832e1baeb8b4ef3cf38e05c6765ee626db4779a95f4a0c0df8c8` |
| `docs/G22_CAUHINH.md` | **mới** | (tệp này — không tự ghi được sha256 của chính nó, `BAN_GIAO.md` §7.3) |

Hai tệp nguồn **TRƯỚC** khi sửa khớp đúng bộ băm AG-02 đã ghim trong `docs/G22_SAOLUU.md` §2:
`3c9a0f29…` (`app/cau_hinh.py`) và `aad036c4…` (`app/migrate.py`) — nên mọi so sánh TRƯỚC/SAU
dưới đây gắn đúng vào tệp mà lượt trước đã đo.

`git status --porcelain -uall` trong cây này có **đúng sáu đường** = năm tệp trên + `docs/G22_CAUHINH.md`.
Không tệp nào khác bị sửa. **Chưa commit** — sandbox chặn ghi `.git` (bằng chứng ở §8).

---

## 0. TÓM TẮT MỘT MÀN HÌNH

| | TRƯỚC (nền `a76ec51`) | SAU (lượt này) | Bằng chứng |
|---|---|---|---|
| **Mặc định bảo mật**: CHƯA KHAI kho | `migrate.py` TỪ CHỐI, rc 1 | **KHÔNG ĐỔI** — vẫn TỪ CHỐI, rc 1 | §4 hàng 1; `app/thu/thu_g22_cauhinh.py` ca `a1` |
| **Tác dụng phụ của lượt bị từ chối** | vẫn để lại `hub.db` **200.704 byte** rồi mới TỪ CHỐI — đúng "hub.db CŨ còn sót" của P-G15-02 `do2b` | TỪ CHỐI **trước khi** `csdl.mo()` chạm đĩa: **không** `hub.db`, **không** `sao-luu/` | §4 hàng 1; ca `a2` |
| **Khai trong nền kiểm thử cô lập** | phải tự viết `os.environ[...]` ở từng bộ; không có chốt cô lập | 1 dòng `VIP_KHO_DANG_CHAY=sqlite`, hoặc 1 lời gọi `cau_hinh.khai_kho_kiem_thu()` **có hai chốt cô lập** | §4 bảng khai/không khai; ca `c1`–`c5` |
| **Bảng biến thể giá trị** | nằm trong `migrate.py` | nằm ở `cau_hinh.KHO_DANG_CHAY_BIEN_THE`, `migrate` dùng chung | ca `e1` |
| **Tài liệu cho người trực** | thông báo lỗi có hướng dẫn, nhưng chưa phân biệt production vs kiểm thử | thông báo + `.env.example` nói rõ: **chỉ** khai trong nền kiểm thử cô lập; **KHÔNG** đặt ở production | §2, §5 |

Câu trả lời ngắn cho hai câu hỏi của đề bài:

1. **Sau khi làm, B2/B3 có chạy được không?** — **Về phía cấu hình kho: CÓ.** Nền của cả hai
   dựng được (`migrate.py` rc 0), B3 chạy **8 đạt / 0 hỏng / 0 bỏ qua / 0 KHÔNG CHẠY**, rc **0**;
   B2 chạy **65 ca**: **57 đạt / 1 hỏng / 7 KHÔNG CHẠY**, rc **1** — ca hỏng là lỗi **có sẵn**
   của bộ đặc tả, không liên quan cấu hình (đối chứng ở §6.2). Cổng `C_BanPhim` của
   `app/thu/thu_qa_g22.py` vẫn **ĐỎ** vì **sổ kỳ vọng của nó đã cũ** (`(51,0,0)` và `(7,0,0)`
   trong khi cây này có 65 và 8 ca) — tệp đó **ngoài phạm vi ghi của tôi** (§6.3).
2. **Không khai biến thì hệ có còn TỪ CHỐI đúng thiết kế không?** — **CÓ.** rc **1**, thông báo
   `TỪ CHỐI: CHƯA KHAI kho đang chạy`, **không** tạo `hub.db`, **không** tạo bản sao lưu; và bản
   chép bị tiêm chính sách cũ ("chưa khai ⇒ coi là SQLite") cho rc **0** — tức phép đo **bắt
   được** lỗi nếu ai đó nới chốt (§4.2).

---

## 1. CƠ CHẾ KHAI — ĐỌC TỪ MÃ, KHÔNG PHẢI TỪ TRÍ NHỚ

`app/cau_hinh.py` (dòng 19–37) và `app/migrate.py::kho_dang_chay()` đọc **HAI nguồn**, theo
đúng thứ tự này:

```
1. cau_hinh.KHO_DANG_CHAY   — đọc MỘT LẦN lúc nạp mô-đun, từ os.environ[VIP_KHO_DANG_CHAY]
2. os.environ[VIP_KHO_DANG_CHAY] ở MỖI lượt gọi `migrate.kho_dang_chay()` (dòng 311–315)
```

* Chưa khai (`None`) ⇒ `_kiem_kho_truoc_khi_sao_luu()` gọi `_tu_choi_chua_khai()` ⇒ **rc 1**.
* `sqlite` / `sqlite3` ⇒ đi tiếp, `sao_luu()` tạo bản sao + `.sha256`.
* `postgres` / `postgresql` / `pg` / `psql` ⇒ TỪ CHỐI, chỉ đường `pg_dump -Fc`.
* Giá trị lạ (`my-sql`) ⇒ TỪ CHỐI kèm **nguyên văn** giá trị sai — **không** bị coi là "chưa khai".
* Chuỗi rỗng sau khi cắt khoảng trắng ⇒ **chưa khai** ⇒ TỪ CHỐI.

**Vì sao vẫn phải là KHAI BÁO, không được đoán:** `app/csdl.py` thuần SQLite, hệ **không có**
cách tự biết dữ liệu nghiệp vụ đang ở đâu; `hub.db` CŨ còn sót và `hub.db` ĐANG PHỤC VỤ không
phân biệt được bằng mtime/kích thước/tên tệp. Lượt này **không đổi** quyết định đó — chỉ làm cho
việc KHAI RÕ trong nền kiểm thử cô lập trở nên đúng và khó sai.

---

## 2. ĐÃ SỬA GÌ, Ở ĐÂU

| Tệp | Thay đổi |
|---|---|
| `app/cau_hinh.py` (dòng 39–123) | Thêm `KHO_DANG_CHAY_BIEN_THE` (6 biến thể, một chỗ duy nhất), `chuan_hoa_kho()` (phép chuẩn hoá thuần), và **`khai_kho_kiem_thu()`** — đường khai MỘT DÒNG cho bộ thử, kèm **hai chốt cô lập**: từ chối khi chưa đặt `VIP_HUB_DATA`, từ chối khi thư mục dữ liệu nằm trong cây repo hoặc là volume `/du-lieu`. Từ chối **trước khi** đặt biến môi trường (không tác dụng phụ). **Dòng 37 `KHO_DANG_CHAY = …` giữ nguyên từng ký tự** — mặc định vẫn là `None`. |
| `app/migrate.py` | (1) `_chuan_hoa_kho()` dùng chung bảng biến thể với cấu hình, **giữ nguyên thông báo lỗi của `migrate`** (dòng 293–313). (2) Thông báo `_tu_choi_chua_khai()` thêm 5 dòng: **chỉ** khai trong nền kiểm thử cô lập, **KHÔNG** đặt cho tiến trình production, và chỉ tới `docs/G22_CAUHINH.md`. (3) `chay()` **kiểm kho TRƯỚC `csdl.mo()`** khi `hub.db` chưa tồn tại (dòng 827–838) — xem §3. |
| `.env.example` (dòng 35–50) | Khối G22: giải thích đường lùi giả, hai giá trị, mặc định KHÔNG có; dòng khai **để dạng COMMENT** `# VIP_KHO_DANG_CHAY=sqlite` và nói rõ: bỏ comment là KHAI, không phải mẫu; chỉ bật ở nền kiểm thử cô lập. |
| `trien_khai/dien_tap_khoi_phuc.sh` (dòng 37–43) | `export VIP_KHO_DANG_CHAY=sqlite` ngay sau `export VIP_HUB_DATA="$NEN/du-lieu"` + chú thích vì sao đây là khai ĐÚNG (nền SQLite tạm do chính script dựng; script đã TỪ CHỐI nếu `VIP_HUB_DATA` trỏ vùng dữ liệu thật). |
| `app/thu/thu_g22_cauhinh.py` **(mới, 17 ca)** | Chứng minh **cả hai chiều** + **đối chứng đường**: khai ⇒ rc 0 có bản sao; không khai ⇒ rc 1 và **không** `hub.db`; tiêm chính sách cũ ⇒ rc 0 (phép đo có răng); bốn chốt cô lập của hàm trợ giúp; hợp đồng bảng biến thể; mặc định vẫn `None`; `chay.sh` của B2/B3 còn khai; `.env.example` không tự bật khai. |
| `docs/G22_CAUHINH.md` | Tài liệu này. |

Ba tệp **không** bị chạm: `app/csdl.py`, `docs/G22_SAOLUU.md`, `app/thu/thu_qa_g22.py` (chủ sở
hữu khác). Mọi tệp nguồn của AG-02 đều đi qua lại được: `ban_va.xac_nhan()` **OK** (19 mảnh bản
vá, mỗi mảnh đúng một lần) — xem §5 hàng 12.

---

## 3. TÁC DỤNG PHỤ ĐÃ ĐÓNG: LƯỢT TỪ CHỐI KHÔNG CÒN ĐỂ LẠI `hub.db` GIẢ

`migrate.chay()` cũ gọi `csdl.mo()` trước, rồi mới tới `sao_luu()` — nên một lượt **CHƯA KHAI**
vẫn TẠO `hub.db` rồi mới TỪ CHỐI. Đo trên bản **HEAD trước khi sửa** (bộ băm khớp `aad036c4…`):

```sh
$ NEN=$(mktemp -d /tmp/probe-migrate.XXXXXX)
$ VIP_HUB_DATA="$NEN" env -u VIP_KHO_DANG_CHAY python3 app/migrate.py
# EXIT_NO_DECL=1
# [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …
$ ls -la "$NEN"
# -rw-r--r--  200704  hub.db        ← TỆP GIẢ CÒN LẠI sau lượt bị từ chối
```

Sau khi sửa, **cùng lệnh, một thư mục tạm MỚI** (`mktemp -d`, không dùng lại chỗ đã có `hub.db`):

```sh
$ NEN=$(mktemp -d /tmp/probe3.XXXXXX)
$ VIP_HUB_DATA="$NEN" env -u VIP_KHO_DANG_CHAY python3 app/migrate.py
# EXIT_NO_DECL=1
# hub.db exists? NO          ← không còn tệp giả
```

Đây không phải "làm gọn": `hub.db` do chính lượt bị từ chối tạo ra **chính là** thứ P-G15-02
`do2b` gọi là "hub.db CŨ còn sót" — lượt sau nhìn vào nó **không phân biệt được** với dữ liệu
đang phục vụ. Chốt mới chỉ áp dụng khi `hub.db` **chưa tồn tại**; CSDL đã ở phiên bản mới nhất
vẫn chạy được **không cần** khai (đo được: lượt hai trên CSDL v9, không khai ⇒ rc **0**,
`"CSDL đã ở phiên bản 9 — không cần nâng cấp."`) — nên không có chuyện từ chối oan trên
triển khai đang chạy bình thường.

---

## 4. BẢNG "KHAI / KHÔNG KHAI" — CẢ HAI CHIỀU, CÓ ĐỐI CHỨNG

### 4.1 Hai chiều, đo bằng mã thoát thật

Mỗi hàng là một lượt `python3 app/migrate.py` trong **tiến trình con** với `VIP_HUB_DATA` là
`tempfile.mkdtemp()` (không đụng `app/du-lieu`). Số liệu sinh bởi `app/thu/thu_g22_cauhinh.py`
(17 ca, log `/tmp/cauhinh_suite.log`); cột "hub.db" kiểm **sau** lượt chạy.

| Chế độ khai | rc | `hub.db` sau lượt | Bản sao lưu + `.sha256` | Kết luận |
|---|---|---|---|---|
| **KHÔNG khai** (không đặt biến) | **1** | **KHÔNG** | KHÔNG | **TỪ CHỐI — đúng thiết kế fail-closed** |
| `VIP_KHO_DANG_CHAY=sqlite` | **0** | CÓ | **1 + 1** | chạy được |
| `=sqlite3` · `="  SQLite  "` · `=SQLITE` | **0** | CÓ | 1 + 1 mỗi lượt | biến thể hợp lệ |
| `=postgresql` | **1** | **KHÔNG** | KHÔNG | TỪ CHỐI, thông báo chỉ `pg_dump -Fc` |
| `=my-sql` (sai chính tả) | **1** | **KHÔNG** | KHÔNG | TỪ CHỐI kèm **nguyên văn** `my-sql` |
| `=` (rỗng) | **1** | **KHÔNG** | KHÔNG | khai rỗng **không phải** khai báo |
| CSDL **đã v9**, không khai | **0** | (đã có) | — | không nâng cấp ⇒ không từ chối oan |

**ĐỐI CHỨNG DƯƠNG** bắt buộc đi kèm: cùng nền trống, cùng lệnh, khác **đúng một biến** ⇒ rc
`1 → 0`, `hub.db` `KHÔNG → CÓ`, bản sao lưu `KHÔNG → 1`. Thiếu vế này thì "từ chối" có thể chỉ là
một `migrate.py` hỏng với MỌI đầu vào.

### 4.2 Phép đo CÓ RĂNG — tiêm lại chính sách cũ (`D5`)

Muốn nói "hệ đang từ chối đúng" thì phải chứng minh **nếu nới chốt, phép đo sẽ bắt được**. Ca
`d1` chép `app/` sang thư mục tạm, chạy **đúng lệnh của ca `a1`** trên bản chép:

| Bản chép | Thay đổi | rc | `hub.db` | Kết luận |
|---|---|---|---|---|
| **KHÔNG tiêm** | (nguyên bản) | **1** | KHÔNG | từ chối đúng |
| **CÓ tiêm** | thay `if kho is None: _tu_choi_chua_khai(nguon)` bằng `kho = KHO_SQLITE` (đúng `D5` của `trien_khai/g20-saoluu/ban_va.py`) | **0** | **CÓ** | phép đo **BẮT ĐƯỢC** lỗi |

### 4.3 Bốn chốt cô lập của `cau_hinh.khai_kho_kiem_thu()`

| Chốt | Đầu vào | Kết quả | Ca |
|---|---|---|---|
| (0) giá trị hợp lệ | `sqlite` | đặt biến + `KHO_DANG_CHAY`, `migrate` con rc **0** | `c1` |
| (1) `VIP_HUB_DATA` phải đặt tường minh | không đặt | `SystemExit`, biến **KHÔNG** bị đặt | `c2` |
| (2a) không được nằm trong cây repo | `app/du-lieu` | `SystemExit`, biến **KHÔNG** bị đặt | `c3` |
| (2b) không được là volume `/du-lieu` | `/du-lieu` | `SystemExit`, biến **KHÔNG** bị đặt | `c4` |
| (3) chỉ mở nhánh SQLite | `postgresql` | `SystemExit` | `c5` |

---

## 5. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA, SKIP

Mọi lệnh chạy trong `a76ec51`, `cwd` = gốc repo, `VIP_KHO_DANG_CHAY` **không** đặt sẵn ở shell.
"PASS/FAIL/SKIP" là số của chính bộ chạy (unittest: `Ran N` / `OK` / `FAILED`; Playwright:
`passed` / `failed` / `did not run` / `skipped`).

| # | Lệnh | Exit | Số ca | PASS / FAIL / SKIP | Ghi chú |
|---|---|---|---|---|---|
| 1 | `python3 app/thu/thu_g22_cauhinh.py` | **0** | **17** | **17 / 0 / 0** | bộ mới; `Ran 17 tests in 1.010s · OK` (lần chạy cuối; log `/tmp/cauhinh_final.log`) |
| 2 | `env -u VIP_KHO_DANG_CHAY sh trien_khai/dien_tap_khoi_phuc.sh` | **0** | 12 bước B1–B12 | — | B11 `giải mã ĐẠT`; B12 `lùi ĐẠT`; 148 dòng log |
| 3 | *(đối chứng âm của #2)* bỏ đúng dòng `export VIP_KHO_DANG_CHAY=sqlite` rồi chạy lại, hoàn nguyên ngay | **1** | dừng ở B1 | — | `migrate HONG` · `TỪ CHỐI: CHƯA KHAI kho đang chạy`; hash hoàn nguyên **khớp** `b6bdf692…` |
| 4 | `sh thu_giao_dien/chay.sh 06_ban_phim.spec.js` | **0** | **8** | **8 / 0 / 0** | `8 passed (11.1s)`; lượt trong cổng QA: `(8,0,0,0)`, 11.6s |
| 5 | `sh thu_giao_dien/chay.sh` (toàn bộ) | **1** | **65** | **57 / 1 / 7** | `57 passed · 1 failed · 7 did not run (2.5m)`; **lặp lại y hệt 3 lượt** |
| 6 | `sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js -g "03 —"` | **1** | 1 | 0 / **1** / 0 | ca `03 — bộ lọc nâng cao…`; `TimeoutError: page.waitForFunction` |
| 7 | *(đối chứng của #6)* đặt lại **nguyên bản HEAD** `app/cau_hinh.py` + `app/migrate.py` (băm `3c9a0f29…` + `aad036c4…`), chạy lại, phục hồi | **1** | 1 | 0 / **1** / 0 | **lỗi có sẵn** — không do thay đổi của lượt này |
| 8 | `python3 app/thu/thu_qa_g22.py C_BanPhim` | **1** | 3 | **1 / 2 / 0** | B1 đạt; B2 `(57,1,0,7)` → `NUA_VOI`; B3 `(8,0,0,0)` → `NUA_VOI` (§6.3) |
| 9 | `python3 app/thu/thu_g22_saoluu.py` | **0** | **14** | **14 / 0 / 0** | `Ran 14 tests · OK` — hồi quy AG-02 |
| 10 | `python3 app/thu/thu_g21_saoluu.py` | **0** | **23** | **23 / 0 / 0** | `Ran 23 tests · OK`; `10/10 FAIL_CLOSED` trên tệp thật đã vá |
| 11 | `python3 app/thu/thu_g20_saoluu.py` | **0** | **41** | **41 / 0 / 0** | `Ran 41 tests · OK` (bộ này tự dựng cụm PostgreSQL RIÊNG cổng 55432 — xem §8) |
| 12 | `ban_va.xac_nhan()` (gọi qua `python3 -c`) | **0** | 19 mảnh | — | `XAC_NHAN_OK: mọi mảnh bản vá có mặt đúng một lần` |
| 13 | `env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_giao_dich.py` | **1** | — | — | `TỪ CHỐI: CHƯA KHAI kho đang chạy` — **bộ ngoài phạm vi**, xem §6.1 |
| 14 | `VIP_KHO_DANG_CHAY=sqlite python3 app/thu/thu_giao_dich.py` | **0** | **17** | **17 / 0 / 0** | chứng minh "một dòng khai" là đủ |
| 15 | `env -u VIP_KHO_DANG_CHAY python3 app/thu/thu_header_bao_mat.py` | **1** | — | — | `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| 16 | `VIP_KHO_DANG_CHAY=sqlite python3 app/thu/thu_header_bao_mat.py` | **0** | **8** | **8 / 0 / 0** | một dòng khai là đủ |
| 17 | `python3 app/thu/thu_qa_g22.py F_DongHo` (cả hai chế độ khai) | **1** | 3 | 0 / 3 / 0 | **STALE** của bộ QA: `RuntimeError: không vá được khoi_phuc` + kỳ vọng cũ — **không** phải do kho (§6.3) |
| 18 | `VIP_HUB_DATA=<v9> python3 app/migrate.py` **không** khai, CSDL đã v9 | **0** | — | — | không từ chối oan — xem §3 |

**Không có SKIP nào ở các bộ do tôi chạy.** Ngoại lệ duy nhất là `thu_qa_g22.py` (cột #8, #17):
3 ca chạy, 0 bỏ qua, 2 hỏng + 3 hỏng — cả hai đều **không** do cấu hình kho (§6.2, §6.3).

---

## 6. B2/B3 — TRẢ LỜI BẰNG SỐ, VÀ BA CHƯỚNG NGẠI CÒN LẠI

### 6.1 Chẩn đoán "migrate TỪ CHỐI" **không còn đúng trên nền này** — và vì sao

`thu_giao_dien/chay.sh` — bộ chạy CHÍNH THỨC của B2/B3 — **đã khai sẵn**:

```
dòng 191: export VIP_KHO_DANG_CHAY=sqlite
```

Dòng đó vào cây bằng commit **`f72a52e`** ("AG-06 (G22 dot 3) …"), và `f72a52e` **là tổ tiên**
của `a76ec51` (kiểm bằng `git merge-base --is-ancestor f72a52e a76ec51` → **YES**). Đo được:
nền của B3 dựng xong (`[chuan-bi] đã tạo 8 đơn; API đếm lại được 8 đơn`) và 8 ca chạy thật.
Nói cách khác: cảnh `[giao-dien] NỀN KHÔNG DỰNG ĐƯỢC: migrate.py thoát 1` mà `docs/QA_G22.md`
§10.5 ghi là **của cây TRƯỚC `f72a52e`**; nó **không tái hiện** trên `a76ec51`. Tôi không sửa
`chay.sh` (ngoài phạm vi) và không cần sửa.

### 6.2 B2 chạy được nhưng có **1 ca hỏng sẵn** — không liên quan cấu hình

| Lượt | Exit | Đạt / Hỏng / KHÔNG CHẠY / Bỏ qua | Thời gian |
|---|---|---|---|
| B2 lượt 1 | **1** | 57 / **1** / 7 / 0 | 2.5 phút |
| B2 lượt 2 (chạy một mình, không tải nền) | **1** | 57 / **1** / 7 / 0 | 2.5 phút |
| B2 trong cổng QA | **1** | 57 / **1** / 7 / 0 | 151.2 giây |

Ca hỏng: `01_luong_chinh.spec.js:36` — **"03 — bộ lọc nâng cao LỌC Ở MÁY CHỦ…"**,
`TimeoutError: page.waitForFunction: Timeout 10000ms exceeded` (chờ số dòng `#d-bang tr` đổi sau
khi đặt `#l-cod-tu`). **Đối chứng (hàng 7, §5):** chạy lại ca này sau khi đặt lại **nguyên bản
HEAD** của `app/cau_hinh.py` + `app/migrate.py` (băm khớp `3c9a0f29…` + `aad036c4…`) ⇒ **vẫn
hỏng y hệt**. Vậy nó **có sẵn trên nền**, không phải hồi quy của lượt này, và không phải chuyện
của cấu hình kho. Sửa nó là việc của chủ sở hữu bộ đặc tả/`admin/` — **ngoài phạm vi** của tôi.

### 6.3 Cổng QA vẫn ĐỎ vì **sổ kỳ vọng đã cũ** — ngoài phạm vi ghi

`app/thu/thu_qa_g22.py` giữ số đóng băng trong `SO_DO`:

```python
"e2e-ban-phim-7": {"nen": (0, 7, 0), "dong": (7, 0, 0)}      # ← cây này có 8 ca
"e2e-toan-bo":    {"nen": (0, 7, 44), "dong": (51, 0, 0)}    # ← cây này có 65 ca
```

Đo thật: B3 `(8,0,0,0)`, B2 `(57,1,7)` ⇒ `dat_cong()` trả `NUA_VOI` cho **cả hai** (giá trị
không rơi vào ô `nền` lẫn ô `đóng`). Đây là **đúng thiết kế của bộ QA** ("giá trị lửng lơ KHÔNG
rơi vào ô nào ⇒ NUA_VOI"), nhưng con số kỳ vọng đã trôi so với cây: **65 ca** chứ không phải 51,
**8 ca** chứ không phải 7. `app/thu/thu_qa_g22.py` **không** thuộc vùng được ghi của tôi —
phải do AG-01/AG-00 cập nhật ghim (hoặc chạy trên đúng cây nền mà bộ QA ghim `37079aa8…`).

Ngoài ra nhóm `F_DongHo` (E3) **STALE** theo đúng `docs/QA_G22.md` §10.5: `_app_tam()` không còn
khớp nguyên văn đoạn `khoi_phuc()` đã vá ⇒ `RuntimeError: không vá được khoi_phuc`, và kỳ vọng
cũ vẫn đòi 1 bản cất. Lượt này **không** sửa tệp đó (§5 hàng 17).

### 6.4 Một chướng ngại MÔI TRƯỜNG đã gỡ — khai rõ

Worktree mới **không có** `node_modules/playwright-core/.local-browsers`, nên lượt B3 đầu tiên
chết ngay ở `browserType.launch` (`Executable doesn't exist … chromium_headless_shell-1194`).
`docs/BAN_GIAO.md` §1 và `docs/G21_BANPHIM_E2E.md` §10 đã ghi sẵn bước hạ tầng: nối symlink tới
`chromium-1194`. Tôi đã làm **đúng bước đó** (một symlink **không được track**, `node_modules/`
đã bị `.gitignore` chặn):

```sh
ln -s ~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers \
      node_modules/playwright-core/.local-browsers
# → chromium-1194 dùng được; B3: 8 passed, rc 0
```

Đây là **thay đổi môi trường, không phải thay đổi mã**; `git status` không thấy nó. Mọi worktree
mới cần cùng một bước trước khi chạy tầng 3.

---

## 7. VIỆC CÒN LẠI — NGOÀI PHẠM VI GHI CỦA LƯỢT NÀY

| # | Việc | Chủ sở hữu | Đường sửa đã đo được |
|---|---|---|---|
| 1 | **8 bộ thử + 1 diễn tập** cần khai kho. Diễn tập **đã xong** (trong phạm vi); 8 bộ còn lại: `thu_giao_dich.py`, `thu_han_muc_nguyen_tu.py`, `thu_qa_g18.py`, `thu_header_bao_mat.py`, `thu_qa_g19.py`, `thu_g17.py`, `thu_g17_baomat.py`, `thu_migrate_dong_thoi.py` | AG-00/AG-05 | Một dòng `export VIP_KHO_DANG_CHAY=sqlite` trong `app/thu/chay_tat_ca.sh` (nền cô lập của nó) **hoặc** `cau_hinh.khai_kho_kiem_thu()` ở đầu mỗi bộ. Đo mới: `thu_giao_dich.py` `1 → 0` (17 ca), `thu_header_bao_mat.py` `1 → 0` (8 ca). **Lưu ý đo được:** `thu_giao_dich.py` chỉ đổi `cau_hinh.THU_MUC_DU_LIEU` mà **không** đổi `cau_hinh.DUONG_DAN_KHOA`, nên khi được khai nó tạo `app/du-lieu/khoa-noi-bo.key` (32 byte) trong **cây repo** — xem §8; sửa đúng phải đặt cả `DUONG_DAN_KHOA` vào thư mục tạm (hoặc đặt `VIP_HUB_DATA` **trước** khi `import cau_hinh`). |
| 2 | `app/thu/chay_e2e.sh` (dòng 35) chạy `python3 app/migrate.py` **không** khai ⇒ mục E2E của `chay_tat_ca.sh` không dựng được nền | AG-00/AG-05 | Thêm `export VIP_KHO_DANG_CHAY=sqlite` cạnh `export VIP_HUB_DATA="$NEN"` (dòng 34) — cùng khuôn `chay.sh` đã làm. |
| 3 | `app/thu/thu_qa_g22.py`: (a) `SO_DO` e2e cũ `(51,0,0)` / `(7,0,0)`; (b) nhóm `F` stale; (c) script `MA_E3` gọi `migrate.sao_luu()` mà không khai kho | AG-01 (chủ sở hữu tệp) | Cập nhật ghim theo cây; sửa `_app_tam()` theo đoạn `khoi_phuc()` hiện tại; trong `MA_E3` thêm `os.environ["VIP_KHO_DANG_CHAY"]="sqlite"` (hoặc gọi `cau_hinh.khai_kho_kiem_thu()` sau khi đặt `VIP_HUB_DATA`). |
| 4 | Cây HEAD `4676e5c…` ≠ `TREE_NEN` `37079aa…` của bộ QA ⇒ ca `A1` ĐỎ nếu chạy cả bộ | AG-01 | Chạy bộ QA trên đúng cây nền của nó, hoặc cập nhật ghim — **không phải** nới điều kiện. |
| 5 | Nhị phân Chromium cho worktree mới | hạ tầng | Bước symlink ở §6.4 (có văn bản: `BAN_GIAO.md` §1). |
| 6 | Ca `01_luong_chinh.spec.js` "03 — bộ lọc nâng cao…" hỏng sẵn | chủ `admin/` + bộ đặc tả | Đo được ở §6.2; cần người sở hữu xem `#l-cod-tu` / `#d-bang` — **không** thuộc cấu hình kho. |

---

## 8. RANH GIỚI C4 / D-8 VÀ TUÂN THỦ

**`OWNER_ACTIONS C4` = "Chuyển CSDL nghiệp vụ sang PostgreSQL" = D-8 = BLOCKED OWNER.**
Lượt này **KHÔNG** thực hiện C4, **KHÔNG** mở kết nối PostgreSQL nào cho dữ liệu nghiệp vụ,
**KHÔNG** sửa `app/csdl.py`, **KHÔNG** đổi CSDL thật. Việc local `G19-C6` (route `truy_van` +
`DDL_G12Q` vào migration) cũng **không** bị đụng tới.

Khai `sqlite` trong một nền kiểm thử cô lập **không phải** C4 và **không cần** Owner duyệt:
D-8 nói CSDL nghiệp vụ **vẫn là SQLite**; khai `sqlite` cho một thư mục `mktemp` là khai **đúng
thứ nó là**. Ngược lại, tài liệu và thông báo của lượt này **cấm** đặt biến đó cho tiến trình
production (nếu dữ liệu thật đã sang PostgreSQL thì khai `sqlite` ở đó = đường lùi giả, rc 0).
`.env.example` giữ dòng khai ở dạng **COMMENT**; ca `e4` canh việc này.

Đã tuân thủ: **không push GitHub · không deploy VPS · không gọi API production · không tạo đơn
vận chuyển thật · không sửa dữ liệu thật · không xoá database · không merge `main` · không mở
G23 · không tự đổi quyết định OWNER.** Mọi lượt đo **của tôi** dùng `tempfile.mkdtemp()`; không
có `hub.db` nào trong cây repo.

**Một hiện vật phụ ĐÃ ĐO và ĐÃ DỌN — khai ra chứ không giấu:** bộ thử **ngoài phạm vi**
`app/thu/thu_giao_dich.py` tự đổi `cau_hinh.THU_MUC_DU_LIEU` nhưng **không** đổi
`cau_hinh.DUONG_DAN_KHOA`. Khi nó được khai `VIP_KHO_DANG_CHAY=sqlite` (đo lúc 23:07), migration
chạy được và tạo `app/du-lieu/khoa-noi-bo.key` (**32 byte**) trong **cây repo**. Đo hai chiều:
chưa khai ⇒ rc 1, **không** tạo gì; có khai ⇒ rc 0, tạo đúng một tệp khóa. Tôi đã
`rm -rf app/du-lieu` sau khi ghi nhận — cây trở lại **không** có thư mục đó; không có `hub.db`,
không dữ liệu nghiệp vụ nào bị chạm. Đây chính là lý do §7 hàng 1 yêu cầu sửa **cả**
`DUONG_DAN_KHOA` khi khai cho bộ đó.

**Chưa commit — sandbox chặn ghi `.git`** (đúng điều đã báo trước trong đề bài):

```sh
$ git write-tree
fatal: Unable to create '/Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a1-cauhinh/index.lock':
Operation not permitted
```

⇒ **Controller commit hộ** năm tệp sửa + hai tệp mới. Không tự vượt sandbox.

**Hai thứ nằm ngoài repo cần khai:** (1) symlink `node_modules/playwright-core/.local-browsers`
(§6.4 — untracked, `.gitignore` đã chặn `node_modules`); (2) log `/tmp/*.log` của các lượt đo.
Ngoài ra bộ hồi quy **AG-04** (`thu_g20_saoluu.py`, 41 ca) tự dựng **cụm PostgreSQL RIÊNG** trên
cổng **55432** — đó là hành vi của bộ thử đó, **không** phải kết nối của tôi tới `:5432` hay dữ
liệu nghiệp vụ.

---

## 9. DỰNG LẠI MỌI SỐ TRONG TÀI LIỆU NÀY

```sh
cd "$REPO"                              # nền a76ec51, cây 4676e5c…

# (1) Bộ mới — hai chiều + đối chứng đường + bốn chốt cô lập
python3 app/thu/thu_g22_cauhinh.py                            # kỳ vọng: Ran 17 · OK · rc 0

# (2) Diễn tập khôi phục — SAU khi khai trong script: chạy hết, rc 0
env -u VIP_KHO_DANG_CHAY sh trien_khai/dien_tap_khoi_phuc.sh  # kỳ vọng: DIEN TAP XONG · rc 0

# (3) Hồi quy ba bộ của AG-02/AG-04
python3 app/thu/thu_g22_saoluu.py                              # 14 ca · OK · rc 0
python3 app/thu/thu_g21_saoluu.py                              # 23 ca · OK · rc 0
python3 app/thu/thu_g20_saoluu.py                              # 41 ca · OK · rc 0 (PG riêng :55432)

# (4) B2/B3
sh thu_giao_dien/chay.sh 06_ban_phim.spec.js                   # 8 đạt · rc 0
sh thu_giao_dien/chay.sh                                       # 57/1/7 · rc 1 (ca hỏng sẵn — §6.2)

# (5) Cổng QA (ĐỎ vì sổ cũ — §6.3, KHÔNG phải vì kho)
python3 app/thu/thu_qa_g22.py C_BanPhim

# (6) Bốn băm của tệp sau khi sửa
shasum -a 256 app/cau_hinh.py app/migrate.py .env.example \
              trien_khai/dien_tap_khoi_phuc.sh app/thu/thu_g22_cauhinh.py
```

**Phạm vi của mọi kết luận trong tài liệu:** đo trên macOS (Darwin), Python 3.9, SQLite của
Python, Chromium 1194 của `node_modules/playwright-core/.local-browsers`, **một máy**, **một
thư mục tạm mỗi lượt**. Không kết luận gì về máy chủ sạch, về sao lưu thật trên VPS, hay về
PostgreSQL nghiệp vụ (D-8 vẫn BLOCKED OWNER).
