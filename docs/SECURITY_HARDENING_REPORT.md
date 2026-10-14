# BÁO CÁO SECURITY HARDENING ĐỢT 2 — AG-01

15/10/2026 · nhánh `agent/security-hardening` · worktree `~/code/veh2-security-hardening`
Nền vào: `fd7c545`, schema v6, 184 test đạt (số do AG-00 chốt trong `docs/SHARED_CONTRACTS.md`).

---

## 1. Việc đã làm

| Mã | Việc | Tình trạng |
|---|---|---|
| **S03** | Sao lưu/khôi phục khóa — `app/sao_luu_khoa.py` + `docs/KEY_BACKUP_RESTORE.md` | xong ở phạm vi local; **production recovery `BLOCKED`** |
| **S04** | Giới hạn tần suất — `app/gioi_han.py` PHẦN A | mã + bộ thử xong; **chưa cắm vào `server.py`** (của AG-00) |
| **S05** | Hạn mức nhập file — `app/gioi_han.py` PHẦN B | mã + bộ thử xong; **chưa cắm vào `server.py`** (của AG-00) |
| **S01** | Token reset: 6 tính chất | xác nhận lại + **vá thêm 1 lỗ hổng thật** (xem §4) |
| **S02** | Static không phục vụ bí mật | xác nhận lại, 29 đường + 9 đường lách + đối chứng |
| **S06** | AES-GCM / xoay khóa / cách ly / thu hồi phiên | xác nhận lại |

## 2. File đã đổi

| File | Việc |
|---|---|
| `app/gioi_han.py` | **mới** — rate limiting (PHẦN A) + hạn mức nhập (PHẦN B) |
| `app/sao_luu_khoa.py` | **mới** — sao lưu/khôi phục khóa |
| `app/thu/thu_gioi_han.py` | **mới** — 34 ca cho S04 + S05 |
| `app/thu/thu_bao_mat.py` | **thêm** 5 lớp (`H`..`K` + nền HTTP), 25→57 ca |
| `app/bao_mat.py` | **vá** `dat_lai_mat_khau`: token sinh trước lần đổi mật khẩu gần nhất → hết hiệu lực |
| `docs/KEY_BACKUP_RESTORE.md` | **mới** |
| `docs/SECURITY_HARDENING_REPORT.md` | **mới** (file này) |
| `docs/MA_HOA.md` | **thêm** mục sao lưu khóa + sửa mục "Giới hạn còn lại" |

**Không chạm:** `server.py`, `csdl.py`, `migrate.py`, `cau_hinh.py`, `don_hang.py`, `webhook.py`,
`nhap_file.py`, `admin/`, `gateway/`. Bốn chữ ký contract §3/§14 của `SHARED_CONTRACTS.md` giữ
nguyên (ca `G_GiuNguyenContract` canh).

## 3. Kết quả nghiệm thu — SỐ THẬT

Chạy ngày 15/10/2026, MacBook Pro, `python3` hệ thống, `cryptography` đã có sẵn:

```
python3 app/thu/thu_bao_mat.py      → Ran 57 tests in 4.170s   OK
python3 app/thu/thu_gioi_han.py     → Ran 34 tests in 0.044s   OK
python3 app/thu/thu_qa_soat.py      → Ran 30 tests in 1.524s   OK
python3 app/thu/thu_tich_hop.py     → Ran  6 tests in 0.040s   OK
python3 app/thu/thu_g01_g02.py      → Ran 21 tests in 2.868s   OK
python3 app/thu/thu_saas.py         → Ran 19 tests in 1.891s   OK
python3 gateway/thu/thu_gateway.py  → Ran  9 tests in 0.702s   OK
```

Hai bộ ngoài danh sách nghiệm thu, chạy thêm để chắc không vỡ chỗ khác:

```
python3 app/thu/thu_g03.py          → Ran 53 tests in 0.062s   OK
python3 app/thu/thu_nhap_file.py    → Ran 21 tests in 0.746s   OK
```

`python3 -m py_compile app/*.py app/thu/*.py` → sạch.

**Tổng 250 ca đạt** trên chín bộ ở trên. Nền vào là 25 ca `thu_bao_mat` + 0 ca `thu_gioi_han`;
đợt này thêm **66 ca** (32 ca mới trong `thu_bao_mat`, 34 ca `thu_gioi_han`).
*Phạm vi của con số: chín bộ thử liệt kê ở trên, chạy tuần tự trên MacBook, không chạy bộ nào
khác.*

### 3.1 Một lượt hỏng do CỔNG BẬN — ghi lại nguyên văn, không nói giảm

Trong hai lượt chạy **liên tiếp cả chuỗi** lúc đầu phiên, `thu_g01_g02` ra
`Ran 0 tests ... FAILED (errors=1)` với lỗi ở `setUpClass`. Sau đó:

- **10 lượt chạy riêng** `thu_g01_g02` → OK cả 10.
- **4 lượt chạy lại cả chuỗi** → OK cả 4.
- Traceback đầy đủ **không bắt lại được**, nên **không đo được** nguyên nhân chính xác.

Giả thuyết hợp lý nhất: `thu_g01_g02` bind **cổng cố định 18896**, và cổng đó giống nhau ở **mọi
worktree** — một agent khác chạy song song là đụng. Đây đúng điều kiện đã biết trong brief
("`Address already in use` là cổng bận, không phải test hỏng"). **Ghi là giả thuyết, không ghi là
kết luận** — chưa có phép đo nào chứng minh (§12.1).

Bộ thử mới của AG-01 dùng cổng riêng **18921** và khi cổng bận thì `SkipTest` kèm thông điệp nói
rõ "CỔNG BẬN, không phải test hỏng" — để lần sau không ai phải đoán như lần này.

---

## 4. Lỗ hổng MỚI tìm được và đã vá: token reset sống sót qua lần đổi mật khẩu

**Chuỗi chạy được thật** (trước khi vá):

1. Kẻ xấu gọi `/api/v2/auth/quen-mat-khau` cho tài khoản nạn nhân → `reset_tokens` có một token
   hiệu lực 30 phút. (Ở cấu hình mặc định kẻ xấu **không nhận được** token qua API — cửa đó đã
   bị bịt từ đợt trước — nhưng token vẫn tồn tại, và đường rò là email/log/bất cứ chỗ nào.)
2. Nạn nhân phát hiện, **tự đổi mật khẩu** qua `/api/v2/auth/doi-mat-khau`. Hệ thu hồi mọi phiên
   khác. Nạn nhân tin là đã an toàn.
3. Kẻ xấu dùng token cũ → `bao_mat.dat_lai_mat_khau` chỉ kiểm `da_dung` và `het_han`, **không
   kiểm mốc đổi mật khẩu** → đặt lại mật khẩu thành công, **chiếm tài khoản**.

Nạn nhân làm đúng mọi thứ mà vẫn mất tài khoản, và **không có gì báo lỗi**.

**Vá:** so theo **MỐC** — `reset_tokens.tao_luc < users.doi_mat_khau_luc` thì từ chối, kèm audit
`ket_qua='tu_choi'`. So mốc (không đánh dấu từng token) để mọi token cũ — kể cả token sinh ở
phiên khác, kể cả token chưa ai biết là có — **cùng chết một lúc**. Quên một token thì mất tài
khoản, nên đây phải là phép so bao trùm, không phải danh sách phải nhớ.

**Bằng chứng ca thử là load-bearing:** gỡ đúng khối vá ra rồi chạy
`I_TokenReset.test_i5_...` → `FAILED (failures=1)`:
`AssertionError: True is not false : token sinh TRƯỚC lần đổi mật khẩu vẫn dùng được → chiếm tài khoản`.
Phục hồi mã → OK. (Đo 15/10/2026.)

---

## 4b. Một chốt chặn CHẾT IM LẶNG trong chính mã mới — bắt được bằng `git status`

Bản đầu của `sao_luu_khoa._kiem_duong_ra` kiểm "có đang ở trong repo git không" bằng
`os.path.isdir(goc_repo/".git")`. Trong một **git worktree** thì `.git` là một **FILE** trỏ sang
repo chính, **không phải thư mục** — nên chốt chặn gitignore **chết im lặng đúng ở nơi mọi agent
đang làm việc**.

Hậu quả đo được, không phải lý thuyết: ca thử `h6` (vốn khẳng định "phải TỪ CHỐI ghi vào
`docs/`") đã **ghi thật** một gói khóa hoàn chỉnh, mở được, vào `docs/khoa.vipkb` — 776 byte,
quyền `0600`, `so_khoa=1`, `vong=600000`. Nó nằm trong cây mã nguồn cho tới khi `git status`
trước lúc commit nhìn thấy. (Khóa trong gói là khóa của thư mục tạm của bộ thử, không phải khóa
production — nhưng đó là **may**, không phải thiết kế.)

Đã làm ba việc:

1. Đổi sang `os.path.exists` — chốt chặn sống lại trong worktree.
2. `h6` nay **đo luôn kết quả trên đĩa**: `assertFalse(os.path.exists(duong_docs))`. Chốt chặn
   chết thì thấy ngay, không phải chờ ai nhìn `git status`.
3. Thêm `h6b` — **quét toàn repo** tìm file `.vipkb` lạc. Một phép đo nhìn vào **kết quả**, độc
   lập với mọi chốt chặn trong `_kiem_duong_ra` (§12.1: thứ dùng để kiểm chứng phải độc lập với
   thứ được kiểm chứng).
4. Gói lạc đã xoá; `git status` sau đó sạch, không file `.key`/`.vipkb` nào ngoài `.gitignore`.

Đây là ca đúng khuôn §12.2: **thứ dùng để chặn tự nó hỏng mà không báo gì.**

---

## 5. ĐIỂM CẮM CẦN AG-00 LÀM

AG-01 không sửa `server.py`. Dưới đây là **đủ để làm mà không phải đoán**. Số dòng theo
`app/server.py` ở nền `fd7c545`.

### 5.1 Rate limiting (S04) — 10 điểm cắm

Thêm `import gioi_han` vào đầu `server.py`. Thêm **một** hàm phụ trong `BoXuLy`:

```python
    def _gioi_han(self, endpoint, dinh_danh=None, tenant_id=None):
        """Chặn theo tần suất. 429 + Retry-After. Gọi TRƯỚC khi làm việc thật."""
        kq = gioi_han.kiem_yeu_cau(endpoint, self.client_address[0], self._headers_thuong(),
                                   dinh_danh=dinh_danh, tenant_id=tenant_id)
        if not kq.cho_phep:
            csdl.audit("gioi_han_tan_suat", f"endpoint:{endpoint}",
                       f"chiều {kq.chieu}, chờ {kq.cho_bao_lau}s",
                       tenant_id=tenant_id, user_id=None,
                       dia_chi=self.client_address[0], ket_qua="tu_choi")
            self._tra_voi_header(429, {"loi": f"quá nhiều yêu cầu, thử lại sau "
                                              f"{kq.cho_bao_lau} giây"}, gioi_han.tieu_de(kq))
            return False
        return True
```

`_tra` hiện không nhận header tùy ý, nên cần một biến thể `_tra_voi_header(ma, obj, headers)` —
hoặc đơn giản hơn: trả 429 bằng `_tra` và **bỏ** `Retry-After` (kém hơn, nhưng vẫn chặn).
`gioi_han.tieu_de(kq)` trả sẵn `Retry-After`, `X-RateLimit-Limit/Window/Remaining`.

| # | Dòng | Endpoint HTTP | Nhãn truyền vào | `dinh_danh` | `tenant_id` |
|---|---|---|---|---|---|
| 1 | 204 | `POST /api/v2/auth/dang-nhap` | `auth.dang_nhap` | `d.get("ten_dang_nhap","")` | — |
| 2 | 213 | `POST /api/v2/auth/quen-mat-khau` | `auth.quen_mat_khau` | `ten_dang_nhap` trong body | — |
| 3 | 223 | `POST /api/v2/auth/dat-lai-mat-khau` | `auth.dat_lai_mat_khau` | — (token không phải định danh) | — |
| 4 | 258 | `POST /api/v2/auth/doi-mat-khau` | `auth.doi_mat_khau` | `nc.user_id` | `nc.tenant_id` |
| 5 | 275 | mọi `/api/v2/platform/*` | `platform.quan_tri` | `nc.user_id` | — |
| 6 | 403 | `POST /api/v2/memberships` | `membership.tao` | `nc.user_id` | `nc.tenant_id` |
| 7 | 434 | `PUT/DELETE /api/v2/memberships/{id}` | `membership.sua` | `nc.user_id` | `nc.tenant_id` |
| 8 | 508 | `POST /api/v2/tai-khoan-hang` (+ rotate/khóa) | `tai_khoan_hang.quan_ly` | `nc.user_id` | `nc.tenant_id` |
| 9 | 630 | `POST /api/v2/import` | `import.upload` | `nc.user_id` | `nc.tenant_id` |
| 10 | 682 | `POST /api/v2/import/{id}/duyet` | `import.duyet` | `nc.user_id` | `nc.tenant_id` |

Thêm được thì tốt: `/api/v2/ai/*` (dòng 740) với nhãn `ai.goi`.

**Ba điều bắt buộc giữ đúng:**

1. **Cắm cho đường vô danh (1–3) phải nằm TRƯỚC `self._doc_json()`** nếu muốn chặn cả chi phí
   đọc body; nhưng `dinh_danh` lại nằm *trong* body. Cách đúng: gọi `_gioi_han(endpoint)`
   (chỉ chiều IP) **trước** khi đọc body, rồi gọi lại với `dinh_danh` **sau** khi đọc. Hai lượt
   `kiem` cộng hai lượt vào bucket IP — nếu không muốn vậy thì lượt đầu truyền
   `gioi_han.kiem(endpoint, ip=..., ghi_nhan=False)`. AG-01 không chọn hộ, vì đây là đổi hành
   vi bộ đếm.
2. **Sau khi `bao_mat.dang_nhap` trả token THÀNH CÔNG**, gọi
   `gioi_han.dat_lai("auth.dang_nhap", ip=gioi_han.dia_chi_that(self.client_address[0], self._headers_thuong()), dinh_danh=ten_dang_nhap)`.
   Không có bước này thì người dùng thật gõ sai 4 lần rồi gõ đúng vẫn bị trần đè ở lần sau.
   **Chỉ gọi khi THÀNH CÔNG.**
3. **`tenant_id` và `dinh_danh` phải lấy từ `nc` (phiên đã xác thực)**, không bao giờ từ
   body/query — trừ hai đường vô danh 1–2, nơi `dinh_danh` là tên người gửi tự khai (và vì vậy
   luật IP luôn đi kèm).

**Trusted proxy:** mặc định `VIP_HUB_PROXY_TIN_CAY` **rỗng = không tin header nào**. Ngày nào đặt
hệ sau Caddy/nginx thì đặt env đó bằng IP/CIDR của proxy. AG-00 **không cần** sửa mã cho việc này.

### 5.2 Hạn mức nhập (S05) — 2 điểm cắm + 1 bảng mới

**Điểm cắm A — `POST /api/v2/import` (dòng 630),** ngay **trước** `nhap_file.tao_batch`:

```python
            gioi_han.kiem_file_nhap(tenant_id, len(du_lieu))   # ném VuotHanMucNhap
            batch_id = nhap_file.tao_batch(tenant_id, nc.user_id, d["ten_file"], du_lieu)
```

**Điểm cắm B — `POST /api/v2/import/{id}/duyet` (dòng 682),** ngay **trước** `duyet_batch`:

```python
            da_dat = gioi_han.dat_truoc_don_nhap(tenant_id, len(dong_ids))
            try:
                kq = nhap_file.duyet_batch(tenant_id, nc.user_id, int(m.group(1)), dong_ids, ng)
            except Exception:
                gioi_han.nha_don_nhap(tenant_id, da_dat)       # hỏng cả lượt → hoàn hết suất
                raise
            # hoàn lại suất cho dòng KHÔNG tạo được đơn
            gioi_han.nha_don_nhap(tenant_id, da_dat - kq.get("SUCCESS", 0))
```

**Bắt lỗi mới trong `_chay()`** (cạnh nhánh `billing.VuotHanMuc` ở dòng 167):

```python
        except gioi_han.VuotHanMucNhap as e:
            self._tra(e.ma, {"loi": f"vượt hạn mức nhập: {e}"})
```

`VuotHanMucNhap` **cố ý KHÔNG** kế thừa `billing.VuotHanMuc`: `server.py` map
`billing.VuotHanMuc` → **402** ("cần trả tiền"). Hạn mức nhập là **chống lạm dụng**, không phải
mời nâng gói — kế thừa là vô tình bật một thông điệp thu phí mà không ai quyết định. `e.ma` là
**429** (quá nhiều) hoặc **413** (quá cỡ). Ca `c2b` canh điều này.

**Bảng mới — migration.** `gioi_han` tự tạo bảng bằng `CREATE TABLE IF NOT EXISTS` khi dùng lần
đầu (thao tác **THÊM**, không `ALTER` bảng nào đang chạy), nên hệ chạy được ngay. Nhưng nên đưa
vào `csdl.SCHEMA` + một bước migration cho đúng nếp. **SQL y nguyên:**

```sql
CREATE TABLE IF NOT EXISTS han_muc_nhap_thang (
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
  thang       TEXT    NOT NULL,
  so_don_nhap INTEGER NOT NULL DEFAULT 0,
  so_dong     INTEGER NOT NULL DEFAULT 0,
  so_file     INTEGER NOT NULL DEFAULT 0,
  so_byte     INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT,
  PRIMARY KEY (tenant_id, thang)
);
```

Không `ALTER` bảng nào. Không `DROP` gì. Không đụng `usage_thang`. Lượt migration đi xuống (nếu
cần) chỉ là `DROP TABLE han_muc_nhap_thang` — nhưng theo §19 thì nên cất bản sao trước.

**Cấu hình** đang ở đầu PHẦN B của `gioi_han.py` (mỗi hằng có env tương ứng:
`VIP_HUB_BOI_SO_DON_NHAP`, `VIP_HUB_NHAP_BYTE_FILE`, `VIP_HUB_NHAP_DONG_FILE`,
`VIP_HUB_NHAP_FILE_GIO`, `VIP_HUB_NHAP_BYTE_THANG`…). Đặt ở đó vì `cau_hinh.py` do AG-00 giữ;
AG-00 muốn dọn về `cau_hinh.py` thì chuyển cả khối, **nhớ chuyển cả env** kẻo đổi env mà không
có tác dụng.

**Nên có, chưa làm:** một endpoint `GET /api/v2/billing/han-muc-nhap` trả
`gioi_han.trang_thai(tenant_id)` (gộp trần + đã dùng + còn lại) để giao diện hiện được, quyền
`tenant.billing.xem`. Và một đường cho PLATFORM gọi `gioi_han.doi_soat(tenant_id)` — phép đo
**độc lập** so bộ đếm với số đơn thật trong `don_hang`.

### 5.3 Xoay khóa và sao lưu khóa qua HTTP — chưa có cửa

`docs/MA_HOA.md` đã ghi là chưa có endpoint xoay khóa. Nay thêm: cũng chưa có endpoint sao
lưu/khôi phục khóa. Nếu AG-00 mở, đề nghị:

- `POST /api/v2/platform/khoa/xoay` → `bao_mat.xoay_khoa(user_id, dia_chi)`, chỉ
  `PLATFORM_OWNER`, nhãn rate limit `khoa.xoay` (3 lượt/giờ/người).
- `POST /api/v2/platform/khoa/sao-luu` → **đề nghị KHÔNG mở.** Gói backup phải cần passphrase
  nhập tay; làm qua HTTP nghĩa là passphrase đi qua body, vào log, vào bộ nhớ tiến trình web.
  Việc này nên giữ ở dòng lệnh. Nếu bắt buộc phải mở thì gói **không bao giờ** được trả về qua
  HTTP response — chỉ trả đường dẫn và `sha256`.

---

## 6. Diễn tập khôi phục khóa — kết quả và BLOCKED

Chi tiết đầy đủ ở `docs/KEY_BACKUP_RESTORE.md` §6–§7. Tóm lại:

**Đã làm, có bằng chứng** (ca `test_h1_DIEN_TAP_...`, chạy trong `thu_bao_mat.py`, 56/56 đạt):
môi trường tạm cô lập → mã hóa credentials thử → backup → kiểm toàn vẹn (sha256 từng khóa) →
khôi phục vào môi trường cô lập **thứ hai** → **giải mã lại được** credentials và webhook secret
bằng khóa vừa khôi phục → quét byte thô gói, **không lộ** bí mật ở cả ba dạng (thô/hex/base64) →
khóa gốc còn nguyên, không di chuyển, không xóa.

**`BLOCKED` — khôi phục production.** Thiếu bốn thứ: (1) passphrase thật do Owner giữ,
(2) chỗ cất gói ngoài máy chủ (lưu ý §18: chuỗi sao lưu đêm trên Mac mini **đã tắt** từ
27/09/2026, hệ duy nhất là VIP Vault, và gói khóa **chưa** nằm trong phạm vi VIP Vault — chưa
đo), (3) một lượt khôi phục thật trên máy chủ sạch, (4) chính sách xoay vòng gói theo §19.4.

**Không tự tạo bí mật giả rồi báo PASS.** Passphrase dùng trong bộ thử (`PASS_THU`) là một chuỗi
công khai nằm trong mã test, không phải bí mật.

---

## 7. Giới hạn còn lại — đọc trước khi tin

1. **Rate limit (PHẦN A) giữ trạng thái trong BỘ NHỚ TIẾN TRÌNH.** Khởi động lại máy chủ là
   **mất sạch** bộ đếm: ngay sau restart mọi trần về 0. Nhiều tiến trình **không dùng chung** bộ
   đếm — 4 worker là trần thực tế gấp 4. Hiện `server.py` là `ThreadingHTTPServer` **một** tiến
   trình nên đúng; ngày nào chuyển sang nhiều tiến trình/nhiều máy thì **phải** đổi sang kho
   dùng chung (Redis, hoặc một bảng CSDL có `UPDATE` điều kiện như PHẦN B đang làm).
   Vì vậy PHẦN A chặn **lạm dụng tự động** (dò mật khẩu, spam quên-mật-khẩu), **không** chặn
   tấn công phân tán nhiều IP, và **không thay cho** WAF/gateway.
2. **PHẦN B thì khác** — đếm trong CSDL nên sống qua restart và dùng chung giữa tiến trình. Hai
   phần cố ý khác nhau vì hậu quả khác nhau.
3. **`billing.kiem_va_tang_don` vẫn còn hở điều kiện tranh chấp** — nó `usage_hien_tai()` rồi
   mới `_tang()`, hai yêu cầu song song lọt cả hai. AG-01 **không sửa** (`billing.py` không
   thuộc quyền AG-01 và không nằm trong brief). Cách vá đúng là cùng khuôn với
   `gioi_han._cong_co_tran`: đưa điều kiện trần vào `WHERE` của một câu `UPDATE` duy nhất rồi
   xét `rowcount`. **Ghi ra vì rủi ro không ghi là rủi ro bị bỏ quên** (§12.1).
4. **`don_hang.tao_don` vẫn không gọi hạn mức nào.** S05 chặn ở **tầng endpoint import**, không
   ở trong `tao_don`. Nên đường tạo đơn lẻ `POST /api/v2/don` vẫn không bị hạn mức nháp — đó là
   **cố ý** (một đơn một lượt, đã có rate limit mặc định), nhưng nếu sau này có đường nào khác
   gọi `tao_don` hàng loạt thì nó **sẽ lọt**. Vá gốc thật sự là gọi hạn mức trong `tao_don`, và
   việc đó thuộc AG-02.
5. **`ban_ma[]` của gói backup chỉ phủ `carrier_accounts`** — cùng phạm vi với
   `bao_mat.ma_hoa_lai_carrier_accounts`. Bảng mới có secret mã hóa thì phải thêm vào **cả hai**
   chỗ **và** vào bộ thử.
6. **Khóa vẫn nằm trong file trên đĩa**, chưa KMS/HSM. `KMSSecretProvider` vẫn là giao diện rỗng
   (cố ý).
7. **Danh sách tin cậy proxy chưa được đo với proxy thật.** `dia_chi_that` đã có 5 ca thử, nhưng
   tất cả là gọi hàm trực tiếp — **chưa** có lượt nào đi qua Caddy/nginx thật. Kết luận chỉ nói
   trong phạm vi đó.
8. **`.gitignore` chưa chặn `*.vipkb`.** AG-01 **không sửa** `.gitignore` (không thuộc quyền sở
   hữu đợt này). Hiện `sao_luu_khoa._kiem_duong_ra` **từ chối ghi** vào mọi chỗ trong repo mà
   gitignore không chặn — đó là lớp mạnh hơn. Nhưng nếu AG-00 thêm `*.vipkb` vào `.gitignore`
   thì ca `h6` (đang khẳng định `docs/khoa.vipkb` bị từ chối) **sẽ hỏng** và phải đổi đường thử.
   Nói trước để không ai bất ngờ.
9. **Một lượt `thu_g01_g02` hỏng không dựng lại được** — xem §3.1. Nguyên nhân là **giả thuyết**
   (cổng 18896 dùng chung giữa các worktree), chưa có phép đo chứng minh.
