# G12 — MA TRẬN ĐIỀU KIỆN NGHIỆM THU STAGING

| | |
|---|---|
| Tác tử | AG-05 SECURITY & KEY OPS ENGINEER |
| Ngày | 15/10/2026 · nền `9af8115` · schema **v8** |
| Máy đã đo | MacBook Pro — `python3 3.9.6` · `node v26.7.0` · **Docker: KHÔNG CÓ** |
| Đây là | **cổng** cho lần triển khai staging đầu tiên. `V-G11-01` **CHƯA CẤP** |

---

## 0. BA LUẬT ĐỌC BẢNG NÀY

1. **Không dòng nào được ghi ĐẠT nếu không có lệnh đo.** Cột *"Đo bằng lệnh nào"* là bắt buộc.
   Dòng nào chưa có lệnh thì trạng thái là **CHƯA**, không phải ĐẠT.
2. **"Không có lỗi" ≠ "ĐẠT".** Công cụ không chạy được thì kết quả là **CHƯA ĐO**, và CHƯA ĐO
   không phải là đạt (`CLAUDE.md` §12.1 luật 5). Ví dụ thật ở đây: không có Docker ⇒ ba dòng
   S-01, S-02, S-03 là **BLOCKED**, không phải "chưa thấy vấn đề".
3. **Mỗi câu "0 lỗi" phải nêu công cụ · phạm vi · cái gì NẰM NGOÀI.** Áp cho từng dòng, xem cột
   *"Điều kiện đạt"* và phần **NGOÀI PHẠM VI** ở mục 3.

**Trạng thái dùng trong bảng:**

| | Nghĩa |
|---|---|
| **ĐẠT** | có lệnh đo, đã chạy, kết quả thoả điều kiện — **trong đúng phạm vi ghi ở dòng đó** |
| **CHƯA** | chưa chạy, hoặc chạy mà chưa thoả. Mở được bằng công việc kỹ thuật |
| **BLOCKED** | không mở được bằng công việc kỹ thuật ở đây — thiếu quyền anh Thành, thiếu máy, hoặc thiếu bí mật thật |

---

## 1. MA TRẬN — 22 DÒNG

### A. Lược đồ, migration, đường lùi

| # | Điều kiện | Đo bằng lệnh nào | Điều kiện đạt | Trạng thái | Ai mở được |
|---|---|---|---|---|---|
| S-01 | Image build được | `docker build -t viphub:staging .` | mã thoát 0 | **BLOCKED** | **máy có Docker** — `docker --version` → `command not found` trên MacBook 15/10. Thay tạm bằng `sh trien_khai/kiem_cu_phap.sh` (chỉ **nội dung tĩnh**, KHÔNG phải build) |
| S-02 | Compose chạy một lượt | `docker compose config -q && docker compose up -d` | config 0 lỗi; container `healthy` | **BLOCKED** | như S-01 |
| S-03 | Image không nhúng bí mật | `docker history --no-trunc viphub:staging \| grep -i "key\|secret\|passw"` | rỗng | **BLOCKED** | như S-01. Lớp tĩnh đã đo: `python3 trien_khai/kiem_cau_hinh.py` kiểm `Dockerfile` không `COPY .env`, không `ENV` dài như secret |
| S-04 | Migration chạy được, có bản lùi | `python3 app/migrate.py --kiem` rồi `python3 app/migrate.py` | phiên bản lên đúng; `migrate.sao_luu()` để lại `hub-truoc-migrate-*.db` kích thước > 0 | **ĐẠT trên máy dựng** | — |
| S-05 | Đường lùi CSDL đã diễn tập | `sh trien_khai/dien_tap_khoi_phuc.sh` | mã thoát **0**; bước B12 lùi làm **mất đúng** dòng thêm sau mốc backup | **ĐẠT** (G11, 15/10 06:42 +0700) | — |
| S-06 | Tên bản sao lưu không trùng theo giây | hai lượt `migrate.sao_luu()` liên tiếp rồi so đường dẫn | hai đường **khác nhau** | **CHƯA** | AG-00 — bản vá **P-4** của G11. Đã đo trùng thật: cùng ra `hub-truoc-migrate-20261015-064137.db`, và `sqlite3.backup` ghi đè **không báo gì** |

### B. Sao lưu / khôi phục CSDL

| # | Điều kiện | Đo bằng lệnh nào | Điều kiện đạt | Trạng thái | Ai mở được |
|---|---|---|---|---|---|
| S-07 | Khôi phục CSDL có số đo, so **từng bảng** | `sh trien_khai/dien_tap_khoi_phuc.sh` | `integrity_check=ok` · `foreign_key_check=0` · số dòng **từng bảng** khớp, lệch nào cũng phải **khai con số chính xác** | **ĐẠT** (G11: 12 bảng khớp, `audit` lệch **+1** đã khai, lý do đo được) | — |
| S-08 | Khôi phục CSDL trên **máy chủ sạch** | lượt khôi phục thật trên staging, rồi `sh trien_khai/kiem_san_sang.sh <url>` từ **ngoài** máy chủ | mã thoát 0 | **BLOCKED** | `V-G11-01` + một máy chủ |
| S-09 | Sao lưu CSDL chạy theo lịch trên staging | `systemctl list-timers \| grep viphub` (hoặc cron) trên máy chủ | có timer, lượt gần nhất < 24h | **BLOCKED** | `V-G11-01`. Lưu ý `CLAUDE.md` §18: chuỗi đêm Mac mini **đã tắt** từ 27/09 — không được giả định nó chạy |

### C. Sao lưu / khôi phục **khoá**

| # | Điều kiện | Đo bằng lệnh nào | Điều kiện đạt | Trạng thái | Ai mở được |
|---|---|---|---|---|---|
| S-10 | Gói khoá tạo được, quyền đúng | `python3 app/sao_luu_khoa.py tao <goi>.vipkb` | `quyen: "0o600"`, `so_khoa ≥ 1` | **ĐẠT** (15/10: 2 095 byte, `0o600`) | — |
| S-11 | Gói **kiểm được TRƯỚC khi tin** | `python3 app/sao_luu_khoa.py kiem <goi>.vipkb` | `dat: true`, `loi: []`, `key_id_thieu: []`; mã thoát 0 | **ĐẠT** | — |
| S-12 | Khôi phục khoá + **giải mã lại CẢ HAI đường** | `python3 app/xoay_khoa.py chung-nhan <goi>.vipkb` | `ket_qua: "dat"`, `cred_hong: 0` **và** `wh_hong: 0`, cả hai `*_dat > 0` | **ĐẠT** (15/10: cred **6/0**, webhook **6/0**) | — |
| S-13 | Gói phủ **đủ khoá CSDL SỐNG đang dùng** | `python3 app/xoay_khoa.py kiem-chot <goi>.vipkb` | điều kiện **C2** đạt, `key_id_thieu_so_voi_csdl` rỗng | **ĐẠT trên nền thử** | — |
| S-14 | Gói khoá có **bản ngoài máy** | `sh trien_khai/sao_luu_ngoai/dua-goi-khoa-ra-ngoai.sh <goi> <dich>` rồi `shasum -a 256` **ở đầu bên kia** | hai mã băm khớp, và `df` hai đầu ra **hai ổ khác nhau** | **BLOCKED** | `V-13906-03` + anh Thành bật công tắc + chọn (a)/(b) ở `trien_khai/sao_luu_ngoai/README.md` mục 6 |
| S-15 | Khôi phục khoá trên **máy chủ sạch** bằng **passphrase thật** | `python3 app/xoay_khoa.py chung-nhan <goi>` chạy **trên máy chủ**, gói là gói production | `ket_qua: "dat"` | **BLOCKED (B-2)** | passphrase thật do Owner giữ + một máy chủ sạch |
| S-16 | Xoay khoá có quyền + có chốt | `python3 app/thu/thu_xoay_khoa.py` | `Ran 30 tests … OK` | **ĐẠT** (15/10) | — |
| S-17 | Xoay khoá **thật** trên staging | `python3 app/xoay_khoa.py xoay-that <goi> --user-id <OWNER>` | `dat: true`, `khoa_cu_bi_mat: []`, `cred_hong: 0`, `wh_hong: 0` | **BLOCKED** | `V-13906-02`; và S-14, S-15 phải ĐẠT trước |

### D. Bí mật, HTTPS, quyền

| # | Điều kiện | Đo bằng lệnh nào | Điều kiện đạt | Trạng thái | Ai mở được |
|---|---|---|---|---|---|
| S-18 | Bí mật **không** nằm trong Git | `git check-ignore -v .env` · `git log --all --full-history -- '*.key' '*.vipkb' '.env'` | `.env` bị chặn; lịch sử **rỗng** | **ĐẠT (lớp tĩnh)** — `.gitignore` đã có `.env`, `.env.*`, `!.env.example`, `app/du-lieu/` (bản vá P-3 đã cắm). **CỐ Ý không chặn `*.vipkb`**: `sao_luu_khoa._kiem_duong_ra()` **từ chối** ghi gói vào chỗ trong repo mà gitignore không chặn — thêm vào gitignore sẽ **làm yếu đi** | — |
| S-19 | HTTPS + 4 header + cookie `Secure` | `curl -sI https://<staging>/api/v2/suc-khoe` | có `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`; cookie phiên có `Secure` | **CHƯA** — mã **đã sẵn sàng**: `_header_bao_mat()` có đủ 4 header (`grep -c` → 4), cookie gắn `Secure` theo `VIP_HUB_HTTPS=1`, bind lấy từ `VIP_HUB_BIND` (P-1/P-2 đã cắm). **Chưa đo sau proxy thật** | cần proxy (Caddy/nginx) + `V-G11-01` |
| S-20 | RBAC + cách ly tenant | `python3 app/thu/thu_g01_g02.py` · `python3 app/thu/thu_qa2_soat.py` | cả hai `OK` | **CHƯA — đang ĐỎ** | `thu_qa2_soat` `FAILED (failures=1)`: ca `test_r40` bắt 3 câu SQL của `app/xoay_khoa.py`. Mở bằng bản vá **P-G12-1** (một mục `MIEN`), chủ file sửa — xem `docs/G12_KEY_OPS.md` mục 7 |
| S-21 | Log **không rò bí mật** | `python3 app/thu/thu_quan_sat.py` (lớp `B_QuetBiMatBaDang`) | `dang_bi_lo` **rỗng**, quét ở **ba dạng** thô/hex/base64 | **ĐẠT trong phạm vi nêu** — `Ran 45 tests … OK`. **NGOÀI phạm vi:** chỉ bắt bí mật **nằm trong danh sách** bộ thử đưa vào; không bắt bí mật rò qua stderr thư viện khác, core dump, hay tên file tạm | — |

### E. Vận hành

| # | Điều kiện | Đo bằng lệnh nào | Điều kiện đạt | Trạng thái | Ai mở được |
|---|---|---|---|---|---|
| S-22 | Sức khoẻ / sẵn sàng gọi **từ ngoài** | `sh trien_khai/kiem_san_sang.sh https://<staging>` | mã thoát **0**; `/api/v2/suc-khoe` → 200, `/api/v2/san-sang` → 200 (hoặc **503** khi chưa sẵn sàng) | **CHƯA** — route đã cắm (`app/server.py` dòng 421/427); chưa gọi được lượt nào qua HTTPS thật | `V-G11-01` |
| S-23 | Rate limit đúng với **nhiều bản** | chạy ≥ 2 bản sau proxy rồi bắn quá ngưỡng; đếm số lượt bị `429` | trần **không nhân lên** theo số bản | **CHƯA (rủi ro R-a)** | trần sống trong **bộ nhớ một tiến trình** ⇒ restart là mất bộ đếm, nhiều worker là trần nhân lên. Vá đúng: kho đếm ngoài (Postgres/Redis). Nếu staging chạy **một bản** thì ghi rõ "một bản" rồi đi tiếp |
| S-24 | Adapter hãng **còn khoá LIVE** | `grep -n "CHO_PHEP_LIVE" app/adapter_jt.py app/adapter_vtp.py` | cả hai `= False` | **ĐẠT** (15/10: `adapter_jt.py:97` và `adapter_vtp.py:40` đều `False`) | giữ nguyên tới khi `V-G09-01` được cấp |
| S-25 | AI **còn khoá** | `python3 -c "import ai_gateway"` + soát `harness_hang.thieu_gi_de_chay(LIVE, …)` | đường live liệt kê thiếu `VIP_HUB_DUYET_*` ⇒ **không chạy** | **ĐẠT** (`V-G10-01` chưa cấp; chốt duyệt đòi mã việc + người duyệt + file credentials) | `V-G10-01` |
| S-26 | Hạn mức / billing chặn từ backend | `python3 app/thu/thu_goi_dich_vu.py` · `python3 app/thu/thu_han_muc_nguyen_tu.py` · `python3 app/thu/thu_usage.py` | cả ba `OK` | **ĐẠT** (37 + 5 + 41 ca, 15/10) | — |
| S-27 | Đường lùi **mã** | `git log --oneline -1` ghi lại SHA trước deploy; lùi bằng `git checkout <sha>` + dựng lại | SHA trước deploy được **ghi vào `docs/`** trước khi deploy | **CHƯA** | người deploy; RUNBOOK mục 6 đã tách **lùi mã** / **lùi CSDL** |
| S-28 | Runbook **có người đọc thử** | một người **không viết nó** chạy `trien_khai/RUNBOOK.md` mục 1 từng dòng rồi ghi chỗ vấp | mọi bước chạy được bằng đúng lệnh in trong tài liệu | **CHƯA** | một người thứ hai. Runbook tự nó chưa phải bằng chứng là runbook dùng được |

---

## 2. TÓM TẮT

| Trạng thái | Số dòng | Dòng |
|---|---|---|
| **ĐẠT** (trong phạm vi nêu) | **13** | S-04, S-05, S-07, S-10, S-11, S-12, S-13, S-16, S-18, S-21, S-24, S-25, S-26 |
| **CHƯA** | **7** | S-06, S-19, S-20, S-22, S-23, S-27, S-28 |
| **BLOCKED** | **8** | S-01, S-02, S-03, S-08, S-09, S-14, S-15, S-17 |

> **Ba con số trên do ĐẾM TAY bảng mục 1, không do công cụ nào.** Lượt đếm đầu ra 12 ĐẠT, đếm
> lại ra 13 — ghi ra chỗ lệch thay vì sửa lặng, đúng nếp `CLAUDE.md` §16.3 dặn cho
> `tong_viec_mo`. Tổng kiểm: 13 + 7 + 8 = **28**, khớp đúng số dòng S-01…S-28.

**Chốt một dòng: staging CHƯA mở được.** Tám dòng BLOCKED đều cần hoặc một máy có Docker, hoặc
một quyết định của anh Thành (`V-G11-01`, `V-13906-02`, `V-13906-03`), hoặc một bí mật thật mà
tác tử **không được** tự tạo.

---

## 3. NGOÀI PHẠM VI CỦA CẢ BẢNG NÀY — nói rõ để không ai suy rộng

- **Không đo hiệu năng.** Mọi lượt chạy trên nền thử với **6 tài khoản hãng** và vài chục dòng.
  Hành vi trên dữ liệu lớn: **chưa ai đo** (G11 lý do 6; và `docs/G12_KEY_OPS.md` mục 9 dòng 12).
- **Không đo frontend.** 56 ca Node và 36 ca HTTP frontend của các đợt trước: AG-05 **không
  chạy lượt nào** ở đợt này, nên bảng này **không nói gì** về chúng.
- **Không đo `thu_e2e.py`.** Nó chạy qua `app/thu/chay_e2e.sh` và cần dựng máy chủ — **chưa
  chạy lượt nào** trong phiên G12.
- **Chỉ đo trên MacBook Pro.** Mac mini M4 và VPS: **không với tới**, không nói gì. Đây là
  `CLAUDE.md` §14.6 — *nói về "máy" thì phải nêu rõ máy nào và ngày đo*.
- **Không đo tính ĐÚNG của dữ liệu nghiệp vụ.** Một bảng bị ghi trắng vẫn cho
  `integrity_check = ok`. Vì thế S-07 đòi so số dòng **từng bảng**, không so tổng.

---

## 4. QUAN HỆ VỚI 10 CỔNG CỦA `trien_khai/RUNBOOK.md` MỤC 10.1

Bảng này **không thay** 10 cổng của G11 — nó **chi tiết hoá** và cập nhật trạng thái ba cổng đã
đổi kể từ 15/10 sáng:

| Cổng G11 | Trạng thái G11 | Trạng thái hôm nay | Dòng tương ứng |
|---|---|---|---|
| G-1 anh Thành cấp quyền | CHƯA | **CHƯA** (`V-G11-01`) | S-08, S-09, S-22 |
| G-2 Docker build + compose | CHƯA | **BLOCKED** | S-01, S-02 |
| G-3 HTTPS thật | CHƯA | **CHƯA** — cookie `Secure` theo cờ **đã cắm** | S-19 |
| G-4 bind ra ngoài `127.0.0.1` | CHƯA | **ĐÃ CẮM** — `app/server.py:1417` đọc `VIP_HUB_BIND` | S-19 |
| G-5 header bảo mật | CHƯA | **ĐÃ CẮM** — đủ 4 header trong `_header_bao_mat()` | S-19 |
| G-6 khôi phục khoá trên máy chủ sạch | CHƯA | **BLOCKED (B-2)** | S-15 |
| G-7 gói khoá có bản ngoài nhà | CHƯA | **BLOCKED** (`V-13906-03`) | S-14 |
| G-8 rate limit nhiều worker | CHƯA | **CHƯA** (R-a) | S-23 |
| G-9 đo trên dữ liệu lớn | CHƯA | **CHƯA** | mục 3 |
| G-10 `.env` ngoài Git | CHƯA | **ĐÃ CẮM** — P-3 có trong `.gitignore` | S-18 |

**Ba cổng G-4, G-5, G-10 đã được AG-00 cắm sau báo cáo G11.** Đo lại bằng lệnh ở cột trạng thái,
không lấy từ báo cáo cũ — vì một tài liệu nói về chính hệ thống cũng là thứ phải nghi
(`CLAUDE.md` §14.6, ca "đã gỡ cùng ngày" sai suốt tám ngày).

**Hai cổng mới mà G11 chưa có, G12 thêm vào:** S-13 (gói phủ đủ khoá CSDL **sống** — không phải
khoá trong gói) và S-17 (xoay khoá thật, có quyền và có chốt).
