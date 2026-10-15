# G12 — BÁO CÁO CUỐI: NỀN TẢNG TRƯỚC SẢN XUẤT + GIA CỐ CSDL

AG-00 PROJECT CONTROLLER · ngày **15/10/2026** · chỉ thị G12 (20 mục).

> **KHÔNG tuyên bố production-ready.** Tài liệu này báo cáo những gì **đo được**, phạm vi của
> từng phép đo, và cái gì **nằm ngoài** phạm vi đó. Phần cần anh Thành duyệt nằm ở §7.

## 1. FINAL LOCAL SHA (mục 20)

| Cái gì | SHA |
|---|---|
| **commit MÃ cuối** (hết mục 5, 11–13) | `936467b5e9d782dd3100e46fd38a58b1736c9e53` |
| **commit TÀI LIỆU** (mục 19 — gồm chính tệp này) | `0a35de1e1fd81d5574c2e053529240e9534c6ff2` |
| **FINAL LOCAL SHA** | `0a35de1e1fd81d5574c2e053529240e9534c6ff2` |

Ghi **hai** dòng vì một tài liệu không tự ghi được SHA của chính commit chứa nó: lúc viết thì
SHA chưa tồn tại, lúc commit xong thì SHA đã đổi. Bản đầu của tệp này ghi `936467b` làm FINAL
SHA — **sai**, vì commit tài liệu ngay sau đó dời `main` sang `0a35de1`. Ai chạy
`git rev-parse HEAD` sẽ thấy lệch và không biết tin bên nào (§12.1 luật 4: trường nào là dữ
kiện đo được thì phải lấy từ lệnh). Nên: `936467b` là mốc **mã** nghiệm thu được bằng bộ thử;
`0a35de1` là mốc cây làm việc.

Nhánh `main`, **local**. Chưa push GitHub, chưa triển khai VPS (chỉ thị mục 16, 17).
So với nền G12 (`9af8115`): **63 tệp, +10.628 dòng, −125 dòng**, 21 commit.

## 2. NGHIỆM THU CUỐI

| Tầng | Số phép kiểm | Kết quả |
|---|---|---|
| python (29 bộ) | **927 ca** | 0 hỏng · 0 bỏ qua |
| frontend tầng 1 (node) | 56 ca | 0 hỏng |
| frontend tầng 2 (HTTP + tệp tĩnh) | 36 ca | 0 hỏng |
| E2E qua HTTP thật | 41 phép đo | 41/41 đạt |
| **tầng 3 Chromium thật (Playwright)** | **27 ca** | **26 đạt · 1 bỏ qua · mã thoát 0** |
| **đồng thời 8 tiến trình × 400 phép × 3 ca** | **9.600 lượt** | **0 khoá hết giờ · 0 giao dịch hỏng · 0 mất cập nhật** |

Thời gian bộ hồi quy: **40,7 giây**. Mã thoát: **0**.

**Câu "0" của lượt này — kèm phạm vi (§12.1 luật 5):**
0 hỏng **theo 29 bộ thử python + 2 tầng frontend + E2E + tầng 3 Chromium**, đo trên
**macOS arm64 · python 3.9.6 · SQLite 3.51.0 · PostgreSQL cụm tạm riêng**, máy chủ bind
`127.0.0.1`, **cả 5 adapter hãng ở chế độ MOCK** (`CHO_PHEP_LIVE=False`).

**NẰM NGOÀI:** VPS · hãng thật · credentials hãng thật · AI thật · Safari/Firefox · cảm ứng
thật · trình đọc màn hình thật · ổ mạng · nhiều máy · dữ liệu lớn · tiến trình bị tắt giữa
giao dịch · trần chống lạm dụng nhiều tiến trình (vẫn sống trong bộ nhớ MỘT tiến trình).

## 3. ĐÃ LÀM — theo từng mục chỉ thị

| Mục | Việc | Trạng thái |
|---|---|---|
| 1, 3 | Tiếp nhận + gộp AG-02 Playwright sau nghiệm thu | **xong** — [PLAYWRIGHT_ACCEPTANCE.md](PLAYWRIGHT_ACCEPTANCE.md) |
| 2 | Không ghi vào worktree AG-02 khi agent còn chạy | **giữ** |
| 4 | Chạy lại toàn bộ hồi quy | **xong** — §2 |
| 5A | Gom quản lý kết nối SQLite về một chỗ | **xong** — §4.1 |
| 5B | Ranh giới giao dịch + kiểm thử trigger và rollback | **xong** — §4.2 |
| 5C | Khoá chống migration đồng thời | **xong** — §4.3 |
| 6 | Kiến trúc migration PostgreSQL | **xong** — [POSTGRESQL_MIGRATION_PLAN.md](POSTGRESQL_MIGRATION_PLAN.md) |
| 7 | CSDL PostgreSQL thử hoàn toàn độc lập | **xong** — cụm tạm tự dựng, 2 chốt chặn từ chối cổng 5432 và cụm hệ thống |
| 8, 9 | Không chuyển CSDL nghiệp vụ · không sửa `vip_customs*` | **giữ** — kho nghiệp vụ vẫn SQLite |
| 10 | Đối chiếu schema · cô lập tenant · ràng buộc tài chính · idempotency · tương thích migration | **xong** — §5 |
| 11, 12 | Thử lại đồng thời 8 tiến trình × 400 phép, phân biệt bốn kết cục | **xong** — [DATABASE_CONCURRENCY_REPORT.md](DATABASE_CONCURRENCY_REPORT.md) |
| 13 | Không coi thử lại vô hạn là phương án | **giữ** — mọi đường chờ đều có hạn và **ném** khi hết |
| 14–18 | Không xoay khoá thật · không ghi VIP Vault · không deploy · không push · không gọi hãng thật | **giữ** |
| 19 | Bốn tài liệu | **xong** |
| 20 | FINAL LOCAL SHA + nghiệm thu | **xong** — §1, §2 |

## 4. BẢY LỖI ĐÃ VÁ — ba lỗi TIỀN, không phải nợ dành cho PostgreSQL

Chỉ thị gọi mục 5 là *"ba cải tiến database"*. Đi làm thì phát hiện **ba lỗi làm lệch tiền
hoặc mất tiền ngay hôm nay trên SQLite một máy**.

### 4.1 Mục 5A — gom driver (nợ kiến trúc)

7 tệp nạp `import sqlite3`, **5 trong số đó không mở kết nối nào** — nạp cả driver chỉ để gọi
tên ba kiểu của nó. Nay chỉ `csdl.py` nạp; mã nghiệp vụ dùng `csdl.Row` · `csdl.LoiCSDL` ·
`csdl.LoiToanVen` · `csdl.LoiVanHanh` · `csdl.ket_noi()`.
Chốt chặn `thu_bien_driver.py` (5 ca, dò bằng **AST** không grep, có ca **tự kiểm bộ dò**).

### 4.2 Mục 5B — ranh giới giao dịch: HAI lỗi tiền

| # | Lỗi | Đo được |
|---|---|---|
| **L1** | `ghi_but_toan` có docstring ghi *"cùng một transaction"* mà mã thì không (`csdl.ghi` commit từng câu) | ép bước công nợ hỏng → bút toán **777.000đ vào sổ**, công nợ đứng yên. Bút toán **không xoá được** (trigger bất biến) → sai nằm lại vĩnh viễn |
| **L2** | `ghi_nhan_thanh_toan` ghi 4 câu, mỗi câu tự chốt | đơn COD 100.000 đã trả 50.000, đợt mới trả 90.000 → câu 2 từ chối **đúng** nhưng câu 1 đã commit → dòng **90.000đ mồ côi**, và `UNIQUE` chặn làm lại → **đợt kẹt vĩnh viễn** |

`csdl.giao_dich()`: tầng ngoài `BEGIN IMMEDIATE`, tầng lồng `SAVEPOINT`. Bắt
`BaseException` chứ không `Exception` — Ctrl-C giữa chừng cũng phải lùi.

### 4.3 Mục 5C — khoá migration: BA lỗi nữa

| # | Lỗi | Đo được |
|---|---|---|
| **L3** | `executescript()` **tự COMMIT** giao dịch đang mở, lặng lẽ | migration nạp 5 khối DDL qua nó → **chưa bao giờ nguyên tử**, trong khi thông báo lỗi vẫn hứa *"rollback"* |
| **L4** | Mô-đun `sqlite3` tự quản giao dịch, sổ sách lệch với `BEGIN` tường minh | 3 tiến trình cùng `BEGIN IMMEDIATE` thì **cả ba lấy được khoá** (0,000 · 0,038 · 0,051s) dù COMMIT đầu tiên mãi 0,074s |
| **L5** | **Một thread tự khoá chính mình qua HAI kết nối** | `test_d5` lượng tử hoá theo `busy_timeout`: 0,005 · 30,35 · 30,35 · 60,70 · 60,70 · 91,04 · 91,05 · 121,42 · 121,43 · 121,43 giây, 4/10 thread `database is locked`. Sau vá: **tổng 0,01 giây** |

Nghiệm thu: 8 tiến trình hệ điều hành thật → **đúng 1 nâng cấp, 7 nhường, 0 lỗi**.

### 4.4 Mục 11 — lỗi tiền thứ ba, do chính phép đo phơi ra

| # | Lỗi | Đo được |
|---|---|---|
| **L6** | `SAVEPOINT` trần mở giao dịch **hoãn** → đọc-rồi-ghi nhiều tiến trình nhận `SQLITE_BUSY_SNAPSHOT` **ngay** | 14/30 lượt `database is locked` ở **0,0 giây** (không phải chờ lâu) |
| **L7** | Sau khi đổi sang chế độ tường minh, `kn.rollback()` thành **LỆNH RỖNG** | `usage.ghi_su_kien` dùng nó để bỏ sự kiện khi vượt trần → **sự kiện mồ côi** → lần thử lại cùng `idem_key` bị coi là TRÙNG rồi lặng lẽ không thu gì → **mất tiền một chiều** |

L7 lộ ra nhờ `thu_usage.test_d2`. §12.2 bước 4: quét được **21 chỗ** gọi
`kn.commit()`/`kn.rollback()`, 20 vô hại, **1 là lỗi tiền**. Đã dọn 19 dòng rỗng còn lại —
mã trông như có đường hoàn tác mà thật ra rỗng thì tệ hơn không có mã. Chốt chặn `a5`.

## 5. MỤC 10 — năm phép đối chiếu

| Hạng mục | Phép đo | Kết quả |
|---|---|---|
| **Schema** | `thu_postgres.py` sinh DDL PostgreSQL rồi nạp thật trên cụm tạm | 21/21 ca đạt, schema khớp sau 4 phép sửa |
| **Cô lập tenant** | `thu_usage.d6_cheo_tenant`: 10 luồng, 2 tenant | 10 qua, 0 lỗi, 5/5 — không rò chéo |
| **Ràng buộc tài chính** | 8 tiến trình × 400 bút toán + đối chiếu `cong_no()` với `tinh_lai_cong_no()` dựng lại từ sổ | 3.200 dòng = 3.200.000đ = công nợ tổng hợp |
| **Idempotency** | `thu_usage.d4_cung_idem_key`: 8 luồng cùng khoá | 1 được tính, 7 báo trùng, 0 lỗi, bộ đếm 1 |
| **Tương thích migration** | 8 tiến trình cùng migrate CSDL trống; đối chiếu `schema_version`, số bảng, số trigger, seed gói, `permissions` | đúng 1 bản ghi phiên bản 8 · 50 bảng · 4 trigger · 3 gói · 28 quyền không trùng |

## 6. SỬA Ở CHÍNH CÔNG CỤ KIỂM CHỨNG — §12.1

Bốn thứ dùng để kiểm chứng tự nó nói sai, phát hiện trong lượt này:

1. **Bộ chạy hồi quy phán bằng chữ `OK`** (nếp unittest) nên báo **HỎNG GIẢ** cho bộ thử
   không dùng unittest. Đã hỏng **lần thứ hai** cùng kiểu (lần đầu với `thu_http.py`) → §12.2
   đổi cấu trúc: phán bằng **mã thoát** + **dấu vết đã chạy** + **số ca > 0**.
   Hướng sai nguy hiểm hơn ở mặt còn lại: bộ thử in `OK` rồi thoát khác 0 sẽ được phán ĐẠT.
2. **`thu_postgres.py` hiện dấu ✓ trong MỌI báo cáo trước mà chạy ĐÚNG 0 CA** — nó tự bỏ qua
   trừ khi bật biến môi trường, lý do ghi là *"~1,5–3 giây"*; đo thật **1,405 giây** cho cả 21
   ca. Ai đọc "27 bộ đạt" đều tưởng PostgreSQL đã được phủ. Nay bật mặc định, và bộ chạy có
   **phán quyết thứ ba BỎ QUA**, không gộp vào ĐẠT.
3. **Hai bộ thử che mã thoát của chính nó** (`thu_usage.py`, `thu_quan_sat.py`) —
   `unittest.main(exit=False)` nên **luôn thoát 0 kể cả khi có ca hỏng**. Đã giữ kết quả rồi
   thoát theo nó; kiểm mặt sau bằng cách ép một ca hỏng → mã thoát 1.
4. **Bộ thử đồng thời của chính em sai hai lần:** lượt đầu không có **vạch xuất phát chung**
   nên 6/6 tiến trình báo *"nâng=True, 0,20 giây"* — nhìn như không ai phải chờ khoá, thật ra
   chúng chạy nối đuôi và phép đo **không chạm tới khoá lần nào**; rồi ca `a1` chỉ tính **một**
   trong **hai** đường nhường chính đáng nên báo hỏng 3/5 lượt. **Nếu tin nó thì em đã đi
   "sửa" mã đang chạy đúng.** Nay `a1` tự đòi ít nhất 1 tiến trình phải đi qua đúng đường khoá.

Và **một phép đo của em sai**: đọc `$?` sau một đường ống nên đo mã thoát của `tail`, ra 0 trong
khi thật là 1. Đo lại không đường ống mới đúng.

## 7. CẦN ANH THÀNH DUYỆT — chưa làm vì chưa được phép

| Việc | Mã | Vì sao cần anh |
|---|---|---|
| Sửa `admin/**`: cắm 17 màn đợt 3 vào giao diện | P-1 | **16/17 màn khai ở đợt 3 không tồn tại** — 5 module là mã chưa ai gọi. Việc lớn, đổi hẳn giao diện quản trị |
| Sửa `admin/**`: cho dùng được bằng bàn phím | P-2 | 10 mục menu là `<a>` không `href`/`tabindex`; 15 lượt Tab không rời `body`. Nên thêm ca canh **cùng lượt** với bản vá |
| Cài Docker | — | AG-04 đề xuất `brew install --cask colima docker docker-compose`. `Dockerfile` + `docker-compose.yml` đã viết, **chưa chạy lượt nào** |
| Chạy chặng 1–2 PostgreSQL | — | Vài ngày việc, không đụng dữ liệu. **Khuyến nghị: chưa** — §1 của kế hoạch migration |
| Xoay khoá mã hoá thật | V-13906-02 | Chỉ thị mục 14 cấm tự làm |
| Ghi khoá ra VIP Vault lần đầu | V-13906-03 | Chỉ thị mục 15 cấm tự làm |
| Gửi 11 câu hỏi ưu tiên cho J&T | V-13906-04/05 | D-4, D-9 chờ hãng xác nhận; chốt chặn ánh xạ `area` đang **khoá cứng** ở chế độ không phải mock |
| Triển khai staging VPS | V-G11-01 | Chỉ thị mục 16 cấm |
| Push GitHub | — | Chỉ thị mục 17 cấm |

## 8. VIỆC CÒN LẠI — đã đo, chưa vá, ghi ra để không quên

**Khối ghi nhiều câu chưa bọc `giao_dich()`** (§12.2 bước 4 đã quét 30 khối, vá 2 nặng nhất):
`don_hang.py:944` (3 câu) · `tai_chinh.py:673` (2 câu) · `usage.py:220` · `don_hang.py:854`
(gọi `_ghi_lich_su`) · `tai_chinh.py:385` `ghi_nhat_ky` (đọc-rồi-ghi móc băm).
`billing.py:68/119` **không** phải lỗi — `INSERT OR IGNORE` + `UPDATE`-có-trần, bước đầu
idempotent nên hỏng nửa chừng vô hại.

**Chưa gộp / chưa áp:** route cho `truy_van.py` + `DDL_G12Q` vào migration v9 (AG-01) ·
21 mã trạng thái VTP (AG-03) · P-3, P-4.

**Trần chống lạm dụng** vẫn sống trong bộ nhớ MỘT tiến trình (B-G11-10) — nhiều tiến trình đi
xuyên qua. Đã biết từ đợt 3, chưa vá, và nó là **điều kiện kích hoạt số 2** của kế hoạch
PostgreSQL.

**Chưa đo:** tiến trình bị tắt **giữa** giao dịch · máy chủ HTTP dưới tải thật · dữ liệu lớn ·
CSDL trên ổ mạng (khoá SQLite không đáng tin ở đó — CSDL phải nằm trên ổ nội bộ).

## 9. Bốn tài liệu của mục 19

| Tài liệu | Nội dung |
|---|---|
| [G12_FINAL_REPORT.md](G12_FINAL_REPORT.md) | tài liệu này |
| [POSTGRESQL_MIGRATION_PLAN.md](POSTGRESQL_MIGRATION_PLAN.md) | 7 chặng kèm trạng thái; chặng 0 đã xong |
| [DATABASE_CONCURRENCY_REPORT.md](DATABASE_CONCURRENCY_REPORT.md) | 9.600 lượt đo, 7 lỗi, phạm vi và cái nằm ngoài |
| [PLAYWRIGHT_ACCEPTANCE.md](PLAYWRIGHT_ACCEPTANCE.md) | nghiệm thu tầng 3 chạy lại từ `main` |

Luật mới vào hợp đồng: `SHARED_CONTRACTS.md` **§30** (ba luật ranh giới giao dịch + bảng
**bảy** điều về SQLite đã đo) và **§25** sửa `V-13906-01` thành **ĐÃ CẤP** theo D-1.
