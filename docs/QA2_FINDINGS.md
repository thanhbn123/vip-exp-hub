# QA2_FINDINGS — AG-05 QA / SECURITY VERIFIER, WAVE 1

> **AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW.**
> **KHÔNG** phải independent human review. Mọi phát hiện dưới đây do một tác tử AI đọc mã và
> chạy ca thử tự sinh ra, trong một làn công việc tách biệt với các tác tử đang sửa mã. **Chưa
> có người nào ngoài hệ thống soát lại.** Mục "đã kiểm, không phải lỗ hổng" chỉ đúng trong
> **đúng phạm vi ca thử đã ghi**. Xem mục 5 trước khi mở ra Internet.

**Ngày đo:** 15/10/2026 · **Worktree:** `~/code/veh2-qa-verification`, nhánh `agent/qa-verification`
**Nền chạy:** macOS Darwin 25.6.0 (MacBook Pro), `Python 3.9.6`
**Commit soát:** `4016eef8d558d13049ba56a64e219c13c7f1c3f5`
*(nhiệm vụ ghi nền `fd7c545`; `fd7c545..HEAD` chỉ thêm 52 dòng tài liệu vào
`docs/SHARED_CONTRACTS.md`, **không đổi dòng mã nào** — ghi mốc THẬT đã chạy, không ghi mốc được
giao)*
**Bằng chứng:** `app/thu/thu_qa2_soat.py` — **49 ca**, mỗi phát hiện có tên ca đi kèm.
**Kế hoạch và phạm vi:** `docs/QA2_TEST_PLAN.md` · **End-to-end:** `docs/QA2_E2E_EVIDENCE.md`

---

## 1. Baseline — số ĐO ĐƯỢC, không phải số chép lại

Báo cáo cũ nói **184 test**. Đo lại từng bộ, lấy mã thoát của **chính tiến trình `python3`**
(không qua `tail`/`grep`):

| Bộ thử | Số ca | PASS | FAIL | Mã thoát |
|---|---:|---:|---:|---:|
| `app/thu/thu_bao_mat.py` | 25 | 25 | 0 | 0 |
| `app/thu/thu_g01_g02.py` | 21 | 21 | 0 | 0 |
| `app/thu/thu_g03.py` | 53 | 53 | 0 | 0 |
| `app/thu/thu_nhap_file.py` | 21 | 21 | 0 | 0 |
| `app/thu/thu_qa_soat.py` | 30 | 30 | 0 | 0 |
| `app/thu/thu_saas.py` | 19 | 19 | 0 | 0 |
| `app/thu/thu_tich_hop.py` | 6 | 6 | 0 | 0 |
| `gateway/thu/thu_gateway.py` | 9 | 9 | 0 | 0 |
| **Tổng** | **184** | **184** | **0** | — |

**Con số 184 đúng.** Nó là 175 ca ở `app/thu/` + 9 ca ở `gateway/thu/`.

Thêm bộ mới của AG-05: `app/thu/thu_qa2_soat.py` — **49 ca · 40 PASS · 9 FAIL**, ổn định y
nguyên qua **3 lượt** chạy liên tiếp. Cả 9 ca FAIL đều mang tiền tố `LOHONG`, tức **FAIL là
đúng**: mỗi ca là bằng chứng một phát hiện chưa vá. **0 ca `KIN`/`ANTOAN`/`PHAMVI` hỏng.**

Tổng kho ca thử sau lượt này: **233 ca** (184 + 49).

### 1.1 Gateway — 24 lượt, tách bạch segfault với cổng bận

Gateway có tiền sử segfault ngắt quãng (~1/5 lượt, do dùng chung một kết nối SQLite giữa các
thread; đã vá bằng kết nối theo-thread).

| Phân loại | Số lượt | Cách nhận mặt |
|---|---:|---|
| **OK** (`Ran 9 tests` · `OK`) | **24 / 24** | mã thoát 0 |
| **SEGFAULT** | **0 / 24** | mã thoát 139 |
| **Cổng bận** (`Address already in use`) | **0 / 24** | chuỗi đó trong log; **không phải lỗi sản phẩm** |
| Hỏng khác | 0 / 24 | — |

**Bản vá kết nối theo-thread trụ được qua 24 lượt.** Phạm vi của câu này (§12.1 luật 5): *0
segfault trong 24 lượt tuần tự của `gateway/thu/thu_gateway.py`, một tiến trình mỗi lượt,
CPython 3.9.6, macOS Darwin 25.6.0, MacBook Pro, 15/10/2026.* Nó **không** nói gì về gateway
dưới tải thật, nhiều tiến trình, hay nền chạy khác. Lỗi 1/5 lượt mà 24 lượt sạch thì xác suất
còn sót là nhỏ, **không phải không**.

### 1.2 Cổng bận ĐÃ xảy ra thật — ở lượt baseline đầu tiên

Lượt baseline **đầu tiên** cho `thu_gateway.py` **mã thoát 1**, `Ran 0 tests`,
`OSError: [Errno 48] Address already in use` tại `setUpClass`. Ngay sau đó `lsof -nP -iTCP:18898`
trả **rỗng** — cổng đã trống. Tức một agent song song giữ cổng `18898` đúng lúc đó rồi nhả ra.

**Đây KHÔNG phải lỗi sản phẩm**, nhưng là lỗi **bộ thử** (R-13 dưới đây): bind cổng cố định làm
nhiễu song sinh với segfault. Ghi ra vì không ghi thì lượt sau có người lại kết luận sai —
đúng dạng §12.1 ca 8 (phép đo thiếu một ca).

---

## 2. Bảng phát hiện

Ký hiệu cột **Vá?**: `KÍN` = bản vá đợt trước còn kín, đã xác minh độc lập · `CHƯA` = chưa vá.

### 2.1 Xác minh lại 14 bản vá của đợt trước (Q02)

| Mã cũ | Mức | Nội dung | Ca thử QA2 | Vá? |
|---|---|---|---|---|
| Q-01 | CRITICAL | Token reset lộ cho người vô danh | `r01`, `r02`, `r03`, `r04`, `r05` | **KÍN** |
| Q-02 | HIGH | Static trả mã nguồn / secret hãng | `r08`, `r09`, `r10`, `r11`, `r12` | **KÍN** |
| Q-03 | MEDIUM | `/platform/vai-tro`, `/platform/goi` không chặn | `r17` | **KÍN** *(một phần — xem R-02)* |
| Q-04 | LOW | 404-vs-403 đếm được số doanh nghiệp | `r18` | **KÍN** |
| Q-05 | MEDIUM | `gioi_han=-1` → `LIMIT -1` = không giới hạn | `r30`–`r32` (gián tiếp), đọc mã `_so_nguyen` | **KÍN** |
| Q-05b/c | LOW | tham số sai kiểu → HTTP 500 | `r48` | **KÍN cho 2 tham số đã vá; CÒN HỞ ở chỗ khác — R-07** |
| Q-06 | MEDIUM | Khóa vĩnh viễn tài khoản từ xa | `r06` | **KÍN** |
| Q-07 | MEDIUM | `/import` không chặn số dòng | `r30` | **KÍN** |
| Q-07b | MEDIUM | `duyet_batch` không chặn độ dài `dong_ids` | `r31` | **KÍN** |
| Q-07c | MEDIUM | Body 20 MB cho đường vô danh | `r32` | **KÍN** |
| Q-08 | LOW | CSV formula injection khi xuất | đọc mã: `/don/xuat-csv` và `/import/*/xuat-csv` dùng **chung** `nhap_file.lam_sach_o_xuat` | **KÍN** |
| Q-10 | LOW | `ap_trang_thai_giao` nhận `don_id` trần | `r40` (miễn có lý do + đối chứng động) | **KÍN về hành vi; rủi ro cấu trúc còn** |
| Q-11 | LOW | `thu_saas::test_16` đòi file ngoài git | lượt baseline: `thu_saas` **19/19 OK, exit 0** | **KÍN** |
| Q-12 | LOW | Bộ thử bind cổng cố định | tái hiện ở mục 1.2 | **CHƯA** (R-13) |

**14/14 bản vá còn kín về hành vi.** Ba mục kèm phần dư: Q-03 còn hai cửa không tra quyền
(R-02), Q-05b/c vá theo từng tham số nên kiểu khác vẫn hở (R-07), Q-12 chưa vá.

### 2.2 Phát hiện MỚI (Q03/Q04)

| Mã | Mức | Vấn đề | Bằng chứng | Vá? |
|---|---|---|---|---|
| **R-01** | **HIGH** | **Gửi đơn song song gọi hãng HAI LẦN** — `gui_don` kiểm trạng thái rồi mới ghi, không khóa | `test_r34_LOHONG_gui_don_dong_thoi_goi_hang_HAI_LAN` | **CHƯA** |
| **R-02** | **HIGH** | **Không có rate limiting ở bất kỳ đâu** — đăng nhập, quên mật khẩu, webhook | `test_r27_…`, `test_r28_…`, `test_r33_…` | **CHƯA** |
| **R-03** | **MEDIUM** | **Webhook không chuẩn hoá mã trạng thái của hãng** — mã J&T thật vào rồi bị bỏ im lặng | `test_r36_LOHONG_webhook_khong_chuan_hoa_ma_trang_thai_cua_hang` | **CHƯA** |
| **R-04** | **MEDIUM** | Token reset cũ **không bị vô hiệu** khi cấp token mới → nhiều token sống đồng thời | `test_r29_LOHONG_token_reset_cu_khong_bi_vo_hieu_khi_cap_token_moi` | **CHƯA** |
| **R-05** | **LOW** | Hai cửa `/platform/goi` và `/platform/vai-tro` **không gọi `_can()`** | `test_r19_LOHONG_hai_cua_platform_khong_tra_ma_tran_quyen` | **CHƯA** |
| **R-06** | **LOW** | Thông báo đăng nhập **lộ sự tồn tại** của tài khoản bị quản trị khóa | `test_r07_LOHONG_thong_bao_dang_nhap_lo_tai_khoan_bi_khoa_co_that` | **CHƯA** |
| **R-07** | **LOW** | Kiểu dữ liệu lạ trong body → **HTTP 500** trên 5/6 cửa đã thử | `test_r48_LOHONG_kieu_du_lieu_la_trong_body_thanh_HTTP_500` | **CHƯA** |
| **R-13** | **LOW** | *Lỗi bộ thử, không phải lỗi sản phẩm:* bind cổng cố định → nhiễu song sinh với segfault | mục 1.2 | **CHƯA** |

### 2.3 Rủi ro cấu trúc — ghi ra, CHƯA tái hiện được thành lỗi

| Mã | Mức | Nội dung | Ca thử |
|---|---|---|---|
| **R-08** | **MEDIUM** *(rủi ro)* | `billing.kiem_va_tang_don` kiểm rồi mới tăng, phần KIỂM không nằm trong khóa — cùng họ với R-01. 8 luồng trong **một** tiến trình **không** làm nó vượt hạn mức (GIL + lượt ghi rất ngắn). **Không** bảo đảm cho nhiều tiến trình / nhiều máy. | `test_r35_PHAMVI_han_muc_goi_kiem_roi_moi_tang_CHUA_tai_hien_duoc_vuot` |
| **R-09** | **MEDIUM** *(rủi ro đã ghi sẵn trong mã)* | **Mã J&T `110` nhập nhằng**: bảng tham số của hãng ghi *Arrival* (→ `dang_giao`), ví dụ của cùng tài liệu ghi *Quét kiện vấn đề* (→ `giao_that_bai`). Mã hiện theo bảng tham số. | `test_r45_PHAMVI_ma_jt_110_nhap_nhang_da_duoc_ghi_ra` |

---

## 3. Chi tiết các phát hiện nặng nhất

### R-01 — HIGH · gửi đơn song song gọi hãng HAI LẦN

`app/don_hang.py::gui_don`:

```python
don = lay_don(tenant_id, don_id)              # ĐỌC
if don["trang_thai"] == "da_gui":
    return dict(don)
if don["trang_thai"] not in ("da_duyet", "dang_gui"):   # KIỂM
    raise LoiNghiepVu(...)
...
csdl.ghi("UPDATE don_hang SET trang_thai='dang_gui', ... WHERE id=? AND tenant_id=?", ...)  # GHI
kq = ad.createOrder(dict(don))
```

Ba việc **ĐỌC → KIỂM → GHI** không nằm trong `csdl.khoa_ghi`. Hai yêu cầu
`POST /api/v2/don/{id}/gui` đến gần nhau thì **cả hai** đọc được `da_duyet`, **cả hai** qua
chốt, **cả hai** gọi `createOrder`.

**Đo được:** `createOrder` được gọi **2 lần** cho **1 đơn**; cả hai yêu cầu trả **HTTP 200**.
Cách đo: bọc `adapter.tao_adapter` **trong bộ thử** (không sửa mã sản phẩm) bằng một adapter
đếm lượt gọi và giữ cả hai luồng ở trong `createOrder` cùng lúc qua `threading.Barrier`.

**Vì sao nặng:**
- Hãng nhận **hai đơn** cho một lô hàng → hai vận đơn, có thể hai lần thu phí thật.
- `billing.kiem_va_tang_don` bị gọi hai lần → usage sai.
- Mọi adapter hiện có đều `KHOA_CHONG_TRUNG = False` (mặc định của `CarrierAdapter`), nghĩa là
  **phía hãng không có gì gỡ lại được**. `app/transport.py` đã dùng đúng cờ này để chặn thử lại
  tự động — nhưng cờ đó không giúp gì cho hai yêu cầu **song song** từ người dùng.

**Vì sao lọt qua 184 ca:** `thu_saas.py::test_09` và `thu_qa_soat.py` đều thử idempotency của
**TẠO** đơn (`tao_don` **có** dùng `csdl.khoa_ghi` + `UNIQUE(tenant_id, idem_key)`), không ai thử
đồng thời ở bước **GỬI**. Hai bước này được bảo vệ khác nhau, mà bộ thử chỉ phủ bước được bảo vệ.

Đây đúng dạng **§12.2**: cùng một cấu trúc check-then-act, một chỗ đã làm đúng (`tao_don`,
`ap_trang_thai_giao` — cả hai dùng `csdl.khoa_ghi`), ba chỗ còn lại thì không (`gui_don`,
`duyet_don`, `huy_don`). Hỏng lần thứ hai theo cùng một kiểu thì **đổi cấu trúc**, đừng vá một
hàm: nên có **một** chỗ duy nhất chuyển trạng thái đơn, và chỗ đó tự giữ khóa.

**Hướng vá đề nghị (AG-05 không vá):** bọc đọc-kiểm-ghi của `gui_don` trong `csdl.khoa_ghi`, và
để lượt `UPDATE` tự mang điều kiện trạng thái —
`UPDATE … SET trang_thai='dang_gui' WHERE id=? AND tenant_id=? AND trang_thai IN ('da_duyet','dang_gui')`
— rồi chỉ gọi `createOrder` khi `rowcount == 1`. Như vậy CSDL cưỡng chế, không phải `if` cưỡng chế.

### R-02 — HIGH · không có rate limiting ở bất kỳ đâu

AG-00 đo là **CHƯA CÓ**. AG-05 kiểm chứng lại bằng hai đường độc lập:

**(a) Soát tĩnh.** `grep -rniE "rate.?limit|throttle|so_lan_trong|per_ip|gioi_han_yeu_cau|toc_do"`
trên `app/` và `gateway/` (trừ `*/thu/`): **không khớp dòng nào.**

**(b) Đo động**, ba cửa, không cửa nào trả `429`:

| Cửa | Số yêu cầu | Mã nhận được | Hệ quả |
|---|---:|---|---|
| `POST /api/v2/auth/dang-nhap` (vô danh) | 60 | `[200 … ]` toàn bộ nhận, **0 lượt bị chặn theo tốc độ** | Dò mật khẩu rải mỏng (password spraying) tự do |
| `POST /api/v2/auth/quen-mat-khau` (vô danh) | 40 | `[200]` × 40, `reset_tokens` **+40 hàng** | Bơm hàng nghìn token sống + phình CSDL + phình `audit` |
| `POST /api/v2/webhook/nhan/{ma}` sai chữ ký | 40 | `[401]` × 40 | Mỗi lượt buộc máy chủ **giải mã AES-GCM + băm HMAC** trước khi từ chối |

**Khóa tạm 15 phút KHÔNG phải rate limit.** Nó đếm theo **tài khoản**
(`users.so_lan_sai`), không theo **nguồn gọi**. Kẻ xấu đổi `ten_dang_nhap` mỗi lượt thì không
tài khoản nào đạt 5 lần sai, nên không có khóa nào bật — trong khi vẫn thử được vô hạn mật khẩu
trên cả danh sách người dùng. Đây là chỗ hai thứ bị tưởng là một.

**Cửa webhook nặng hơn phần còn lại** vì nó **vô danh** và `webhook_ma` **không phải bí mật**
(nó nằm trong URL, và `POST /tai-khoan-hang` trả thẳng nó về cho client). `app/server.py::_api`
gọi `tim_account_theo_webhook_ma` → `webhook.kiem_chu_ky` → `bao_mat.giai_ma_wh` (giải mã
AES-GCM) **trước** mọi mức chặn — vì không có mức nào.

**Ghi NOT TESTED/FAIL, không ghi PASS.** Trạng thái: **FAIL — tính năng chưa tồn tại.**

**Hướng vá đề nghị:** mức chặn theo **nguồn gọi** (IP, hoặc token nếu đã đăng nhập) đặt ở **một
chỗ** trong `_api` trước khi định tuyến, không rải ra từng cửa. Mức riêng, chặt hơn, cho ba cửa
vô danh (`dang-nhap`, `quen-mat-khau`, `webhook/nhan`). Và `kiem_chu_ky` nên đặt **sau** mức
chặn, không trước.

### R-03 — MEDIUM · webhook không chuẩn hoá mã trạng thái của hãng

Chú thích đầu `app/webhook.py` mô tả pipeline:
`VERIFY → PERSIST RAW → QUEUE → NORMALIZE → RESOLVE TENANT+ORDER → UPDATE → AUDIT`.

**Bước NORMALIZE không có trong mã.** `webhook._xu_ly` làm:

```python
loai = d.get("event")
...
ap_dung, ly_do = don_hang.ap_trang_thai_giao(don["id"], loai, f"webhook:{sk['id']}")
```

và `ap_trang_thai_giao` tra thẳng `cau_hinh.HANG_TRANG_THAI_GIAO` — bảng chứa **tên nội bộ** của
dự án (`cho_lay`, `lay_hang`, `dang_giao`…). Hàm `trang_thai_hang.anh_xa()` tồn tại và đúng, và
`app/polling.py` **có** gọi nó qua `ad.normalizeTrackingStatus(ma_tt)` — nhưng `webhook.py`
**không gọi ở đâu cả**. Hai đường cập nhật cùng một thứ mà hiểu đầu vào khác nhau.

**Đo được:** đẩy webhook ký ĐÚNG với `{"event": "106"}` (J&T *Picked Up*, có trong
`trang_thai_hang.JT_MA`, ánh xạ sang `lay_hang`) vào một đơn đã gửi thật:

- HTTP **202** — nhận.
- `wh_su_kien.trang_thai` = **`xong`** — hệ coi là xử lý thành công.
- `don_hang.trang_thai_giao` vẫn là **`cho_lay`** — **không đổi gì**.

Sự kiện **không** vào DLQ, **không** báo lỗi, chỉ còn một dòng
`don_lich_su` ghi *"loại sự kiện lạ: 106"*. Đây là **hỏng im lặng** đúng nghĩa §12.2: màn hình
nói "xong", thực tế mất cập nhật.

Hiện chưa ai gọi hãng thật nên chưa gây hại. Nhưng **ngày nối hãng thật là ngày nó hỏng**, và nó
sẽ hỏng theo kiểu khó thấy nhất: đơn ở trạng thái cũ mà hàng đợi webhook sạch bong.

**Đây cũng là chỗ R-09 (mã `110`) nằm.** Hai tầng hiểu `110` khác nhau, mà tầng webhook thì chưa
hiểu `110` chút nào.

**Hướng vá đề nghị:** `webhook._xu_ly` gọi `adapter` của account để chuẩn hoá trước khi áp, và
mã **không ánh xạ được** phải vào DLQ hoặc một trạng thái "cần người xem", **không** được ghi
`xong`. Đồng thời sửa chú thích đầu file nếu quyết định không làm bước đó — tài liệu nói có mà
mã không có thì chính tài liệu là thứ nói dối (§12.2).

### R-04 — MEDIUM · token reset cũ không bị vô hiệu khi cấp token mới

`bao_mat.tao_token_reset` chỉ `INSERT` một hàng mới vào `reset_tokens`. Token cũ **vẫn còn hiệu
lực** tới khi hết 30 phút hoặc bị dùng.

**Đo được:** xin 5 token liên tiếp cho một tài khoản, rồi dùng **token thứ nhất** → `ok=True`,
đổi mật khẩu thành công.

Gộp với **R-02** (không có rate limit trên `/auth/quen-mat-khau`) thì cửa sổ tấn công mở rộng
tuỳ ý: hàng nghìn token sống cùng lúc cho một tài khoản, token nào rò ra (log, lịch sử trình
duyệt, email bị đọc) cũng dùng được trong 30 phút. Cấp một token mới **nên** vô hiệu các token
cũ của cùng người — đó là hành vi người dùng mong đợi khi họ bấm "gửi lại".

### R-05 — LOW · hai cửa platform không gọi `_can()`

Bản vá Q-03 đúng hướng: `_api_platform` nay có **một cổng chung** chặn mọi ai không có
`platform_role`, nên `TENANT_VIEWER` không còn đọc được ma trận RBAC (`r17` xác nhận). Nhưng
hai cửa vẫn không tra quyền **bên trong** cổng đó:

```python
if duong == "/api/v2/platform/goi":          # không có self._can(...)
if duong == "/api/v2/platform/vai-tro":      # không có self._can(...)
```

**Đo được:** xoá sạch `role_permissions` của `PLATFORM_ADMIN`, rồi đăng nhập bằng
`PLATFORM_ADMIN`:

- `/api/v2/platform/audit` → **403** (đối chứng: cửa **có** `_can` chặn đúng).
- `/api/v2/platform/goi` → **200**, trả trọn bảng giá.
- `/api/v2/platform/vai-tro` → **200**, trả trọn `roles` + `permissions` + `role_permissions`.

Mức LOW vì chỉ người đã có `platform_role` tới được, và dữ liệu không phải bí mật khách hàng.
Nhưng nó là **ngoại lệ còn lại** của luật "mọi endpoint đều tra quyền trong CSDL", và ngoại lệ
không được ghi ra là ngoại lệ sẽ bị nhân bản khi có người thêm cửa thứ ba.

### R-06 — LOW · thông báo đăng nhập lộ sự tồn tại của tài khoản bị khóa

`bao_mat.dang_nhap` trả `CHUNG = "sai tên đăng nhập hoặc mật khẩu"` cho hầu hết nhánh — **đúng**
— kể cả nhánh "đang khóa tạm" (bản vá cố ý làm vậy, có chú thích rõ). Nhưng nhánh
`u["trang_thai"] == "khoa"` trả riêng `"tài khoản đã bị khóa — liên hệ quản trị"`.

**Đo được:** người vô danh gõ mật khẩu rác:

| Tên đăng nhập | Thân phản hồi |
|---|---|
| tài khoản **có thật**, bị quản trị khóa | `{"loi": "tài khoản đã bị khóa — liên hệ quản trị"}` |
| tên **không tồn tại** | `{"loi": "sai tên đăng nhập hoặc mật khẩu"}` |

Phân biệt được ⇒ dò được danh sách tài khoản (ít nhất là các tài khoản bị khóa). Gộp với **R-02**
(không rate limit) thì dò được cả danh sách ở quy mô lớn.

Đây là **đánh đổi có thật**, không hẳn là lỗi rõ ràng: nói "liên hệ quản trị" giúp người dùng
thật biết phải làm gì. Nhưng nếu đã chọn nói chung cho nhánh khóa tạm thì nhánh khóa vĩnh viễn
nên nhất quán — hoặc ghi rõ đây là đánh đổi đã cân nhắc. Hiện mã **không** ghi.

### R-07 — LOW · kiểu dữ liệu lạ trong body → HTTP 500

Đợt trước vá hai ca cùng kiểu (`gioi_han=abc`, `cod` không phải số) — nhưng vá **theo từng tham
số**. Thử các tham số khác:

| Cửa | Body | Mã | Ngoại lệ |
|---|---|---:|---|
| `POST /auth/doi-tenant` | `{"tenant_id": [1]}` | **500** | `InterfaceError` |
| `POST /auth/doi-tenant` | `{"tenant_id": {"a": 1}}` | **500** | `InterfaceError` |
| `POST /khach-hang` | `{"ten": {"x": 1}}` | **500** | `AttributeError` |
| `PUT /tenant` | `{"ten": [1, 2]}` | **500** | `AttributeError` |
| `POST /import` | `{"ten_file": ["a.csv"], …}` | **500** | `AttributeError` |
| `POST /don` | `khoi_luong_gram=[500]` | 400 ✓ | — (`_kiem_du_lieu` bắt đúng) |

500 nghĩa "máy chủ hỏng", 400 nghĩa "anh gửi sai". Nhầm hai thứ làm hỏng **hai** việc: người
dùng không biết sửa gì, và người vận hành thấy biểu đồ 5xx đầy rác nên **không nhận ra lúc máy
chủ hỏng thật**.

**Đã kiểm, KHÔNG phải lỗ hổng lộ thông tin:** thân 500 chỉ nêu **tên** ngoại lệ, không nêu
traceback, SQL, hay đường dẫn tuyệt đối (`test_r49`). Mức LOW vì vậy.

Đây là **§12.2 áp vào kiểm tham số**: vá lần thứ ba theo cùng một kiểu thì **đổi cấu trúc** —
dùng một hàm đọc-và-kiểm-kiểu cho mọi trường (như `_so_nguyen` đã làm cho số), thay vì thêm một
`try/except` nữa cho tham số vừa bị phát hiện.

---

## 4. Đã kiểm, KHÔNG phải lỗ hổng — kèm phạm vi đã kiểm

Mỗi dòng dưới đây là một mối lo đã dựng ca thử và **kết luận không phải lỗ hổng**, nhưng chỉ
**trong đúng phạm vi ghi ở cột phải**. Không dòng nào là lời bảo đảm chung.

| Ca thử | Kết luận | Phạm vi đã kiểm |
|---|---|---|
| `r10` | Path traversal không lọt | **18 biến thể**, gửi bằng **socket thô** (không qua `urllib`, vì `urllib` tự chuẩn hoá đường dẫn ⇒ đo nó chứ không đo máy chủ): `..`, `%2e%2e`, `%252e%252e`, `//`, `///`, `..;/`, `....//`, `%00`, byte null thật, đường tuyệt đối, `./` lồng nhau. Ngoài mã HTTP, còn kiểm phản hồi không chứa `import cau_hinh`/`root:x:0:0`/`PBKDF2_VONG` |
| `r11` | Khóa + CSDL nằm ngoài tầm static **theo cấu trúc** | 4 thư mục trắng `admin/ pages/ assets/ mock/` + `index.html` ở gốc. Chốt bằng đường dẫn, không bằng tên file ⇒ nới danh sách đuôi file cũng không với tới |
| `r12` | Thư mục phục vụ công khai không chứa bí mật | 20 file trong 4 thư mục trắng, 3 mẫu: `privateKey`, `BEGIN … PRIVATE KEY`, `secret: "…"` ≥12 ký tự. **Không** quét entropy, **không** quét bí mật đặt tên lạ |
| `r13`, `r44` | Chéo tenant bị chặn | **13 cửa**: 5 cửa đơn hàng, 3 cửa tài khoản hãng, 5 cửa import. Kiểm cả mã HTTP **và** dữ liệu của tenant A không đổi một chữ trong CSDL |
| `r14` | Không dùng được tài khoản hãng của tenant khác | Đường `POST /don/{id}/gui` với `carrier_account_id` của tenant khác; kiểm cả `carrier_account_id` trong CSDL vẫn `NULL` |
| `r25` | Đổi chỗ bản mã giữa hai tenant → giải mã hỏng | Chép thẳng cột `credentials_ma_hoa` của A sang hàng của B **trong CSDL**, rồi gọi cửa gửi đơn thật. AAD `cred:{tenant_id}:{hang}` cưỡng chế |
| `r26` | Xoay khóa không mất secret | Mọi hàng `carrier_accounts`, **cả hai** cột secret, kiểm `key_id` mới + webhook còn ký/xác thực được sau khi xoay |
| `r37` | Webhook: chữ ký, chống trùng, chống replay, không chéo tenant | 1 account, HMAC-SHA256; chữ ký rác → 401; secret của **account khác** → 401; replay y nguyên **3 lượt** → 200 `da_nhan_truoc_do` cùng `su_kien_id`; chống trùng do `UNIQUE(account_id, event_id)` **trong CSDL** (đếm 1 hàng), không phải bởi `if`; sự kiện của A trỏ vận đơn của B → `khong_khop`, không đụng đơn ai |
| `r38` | Sai thứ tự không kéo lùi trạng thái | Rank guard trên **6** trạng thái trong `cau_hinh.HANG_TRANG_THAI_GIAO` |
| `r39` | Idempotency tạo đơn do CSDL cưỡng chế | **6 luồng song song** cùng `Idempotency-Key`, nhả khỏi Barrier cùng lúc → đúng **1** đơn |
| `r40` | SQL chạm bảng có `tenant_id` đều có điều kiện tenant | **Chuỗi SQL hằng** trong `app/*.py` (trừ `thu/`), 6 bảng. **Không** thấy SQL ghép ở thời gian chạy. 11 dòng miễn, mỗi dòng có lý do; dòng miễn nặng nhất (`server.py` + `tenant_memberships`) có **đối chứng động** |
| `r41` | Mọi nhánh API tenant đều qua cổng kiểm quyền | `_api_tenant` trong `app/server.py`, đếm **theo văn bản** ⇒ nhánh gọi `_can` trong hàm con sẽ bị báo thiếu. Kèm đối chứng động |
| `r42` | Vòng đời đơn không bỏ bước | `nhap → da_duyet → da_gui`; chưa duyệt không gửi được, duyệt lại báo lỗi, đã gửi không sửa được |
| `r43` | Kết quả hãng **không rõ** không bị nhận là thành công | Nhánh `timeout=True`: đơn giữ `dang_gui`, `can_doi_soat_ket_qua=1`, `ma_van_don` vẫn `NULL` |
| `r46` | Không đổi được tenant không có membership | `/auth/doi-tenant` với 7 giá trị xấu: `0, -1, 999999, "1 OR 1=1", null, [1], {}`. *(Mã HTTP cho kiểu lạ là R-07, không phải lỗ hổng quyền)* |
| `r47` | Bí mật không lọt ra ngoài | **6** cửa API + **3** bảng (`audit.chi_tiet`, `don_lich_su.noi_dung`, `wh_su_kien.loi_cuoi`) + `stderr` máy chủ trong lượt chạy này + cột bản mã. Dùng chuỗi bí mật sinh ngẫu nhiên để không trùng dữ liệu cũ |

---

## 5. Cần NGƯỜI rà trước khi lên production

Theo đúng yêu cầu Q07. Đây là những chỗ ca thử xanh **không đủ** để kết luận:

1. **R-01 (HIGH) — bản vá đồng thời của `gui_don`.** Khóa đặt sai chỗ thì chuyển từ "gọi hãng
   hai lần" sang "treo cả máy chủ". Người rà phải xem **ba** hàm cùng họ (`gui_don`,
   `duyet_don`, `huy_don`), không chỉ hàm bị báo.
2. **R-02 (HIGH) — thiết kế rate limiting.** Mức chặn đặt theo IP sẽ chặn oan khi nhiều người
   dùng sau một NAT; đặt quá lỏng thì vô dụng. Đây là quyết định sản phẩm, không phải quyết
   định kỹ thuật, và **cấm** để một tác tử tự chọn ngưỡng.
3. **R-03 (MEDIUM) + R-09 — nối mã trạng thái hãng thật.** Phải có người **đối tiếp với J&T**
   hỏi nghĩa của `110` và của `121 FINISH`. Không ai trong hệ thống này trả lời được bằng cách
   đọc tài liệu — tài liệu tự mâu thuẫn với ví dụ của chính nó.
4. **Bản vá Q-01 (CRITICAL) của đợt trước.** `HIEN_TOKEN_RESET` nay mặc định TẮT — đúng. Nhưng
   **chưa có cổng chặn khởi động**: bật cờ đó mà không bind `127.0.0.1` thì hệ vẫn chạy. §12.2:
   *lời dặn không chặn được máy.* Hướng vá đợt trước đã nêu phần này, nó **chưa được làm**.
5. **Bản vá Q-02 (HIGH) — danh sách trắng static.** Danh sách trắng là lựa chọn đúng. Nhưng
   `mock/` nằm trong 4 thư mục trắng và cho cả `.json`/`.csv`; hôm nay 4 file ở đó vô hại
   (`r12` xác nhận), nên nó phụ thuộc vào việc **không ai** bỏ dữ liệu thật vào `mock/` sau này.
   Người rà nên quyết: `mock/` có nên ra khỏi danh sách trắng ở bản production hay không.
6. **Toàn bộ các lớp mang nhãn BLOCKED:** `moi_truong != "mock"` bị chặn cứng ở
   `CarrierAdapter.__init__` và ở `POST /tai-khoan-hang`. Mọi kết luận trong tài liệu này được
   đo **ở chế độ mock**. Mở sandbox/production là đổi nền chạy ⇒ phải đo lại, **không** suy ra.
7. **`secret_provider` chỉ là giao diện**, chưa nối KMS/HSM thật. Khóa AES nằm ở file `0600`
   trên đĩa. Chấp nhận được ở local, **phải** xem lại trước khi ra Internet.

---

## 6. Mục NOT TESTED / BLOCKED còn lại

| Mục | Trạng thái | Vì sao |
|---|---|---|
| Rate limiting | **FAIL** (tính năng chưa tồn tại) | R-02 — đo bằng 2 đường, không ghi PASS |
| Đồng thời ở mức **nhiều tiến trình / nhiều máy** | **NOT TESTED** | Mọi phép đo đồng thời ở đây là nhiều **luồng** trong **một** tiến trình CPython. R-08 ghi rõ giới hạn này |
| Gateway dưới tải thật | **NOT TESTED** | 24 lượt tuần tự, không đo đồng thời/tải |
| API hãng THẬT (J&T, Viettel Post) | **BLOCKED** | Ràng buộc nhiệm vụ: cấm gọi. `CHO_PHEP_LIVE=False` ở mọi adapter |
| Nghĩa thật của J&T `110`, `121` | **BLOCKED** | Cần người đối tiếp với hãng (R-09) |
| Viettel Post: mã trạng thái thật | **BLOCKED** | Chưa có tài liệu Partner API + credentials (`docs/VIETTELPOST_REUSE_AUDIT.md`) |
| Logic nội bộ `gateway/*.py` | **NOT TESTED** | Làn của agent khác trong WAVE 1 |
| Tầng giao diện `pages/`, `admin/admin.js` | **NOT TESTED** | Chỉ soát ở mức "có lộ bí mật không" (`r12`) |
| Bảo vệ khóa bằng phần cứng (KMS/HSM) | **NOT TESTED** | `secret_provider` hiện chỉ là giao diện |
| Bản vá của 4 agent WAVE 1 khác | **NOT TESTED** | AG-05 không thấy worktree của họ. Cần lượt soát thứ hai sau khi AG-00 tích hợp |
| Quét bí mật bằng entropy | **NOT TESTED** | `r12` chỉ khớp 3 mẫu tên đã biết |

---

## 7. Khuyến nghị nghiệm thu

**FAIL — chưa đạt để lên production.** (Với WAVE 1 ở mức "nền tảng vẫn vững": **PASS**.)

Cơ sở:

- **14/14 bản vá CRITICAL/HIGH của đợt trước còn kín**, xác minh bằng bộ thử **độc lập**, viết
  lại từ đầu. Đây là tin tốt và nó được đo, không phải được giả định.
- **184/184 ca thử sẵn có PASS, mã thoát 0 cả 8 bộ.** Không hồi quy nào.
- **0/24 lượt gateway segfault.** Bản vá kết nối theo-thread trụ được trong phạm vi đã đo.
- **14/14 bước end-to-end PASS**, dữ liệu thật trong CSDL thật của worktree này.
- **Nhưng còn 2 phát hiện HIGH chưa vá** (R-01 gọi hãng hai lần, R-02 không có rate limit) và
  2 MEDIUM chưa vá (R-03 webhook không chuẩn hoá — hỏng im lặng; R-04 token reset cũ còn sống).
  R-01 và R-03 **đụng tiền và đụng hàng thật** của khách.
- Và **7 mục ở mục 5 cần người đọc**, không chỉ cần ca thử xanh.

**Trước khi mở ra Internet, tối thiểu:** vá R-01, R-02, R-03, R-04; làm cổng chặn khởi động cho
`HIEN_TOKEN_RESET` (mục 5.4); và có **một người** đọc lại bảy mục ở mục 5.

---

## 8. Công bố tính độc lập

**AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW.**

Tài liệu này là kết quả của một **làn công việc độc lập** — worktree riêng, cổng riêng, dữ liệu
nền riêng, bộ thử viết lại không `import` gì từ bộ thử của phiên bị soát. Đó là nghĩa duy nhất
của chữ "independent" ở đây.

Nó **KHÔNG** phải **independent human review**. **Chưa có người nào ngoài hệ thống đọc lại** bất
kỳ bản vá hay ca thử nào ở đây. Mọi câu "đã kiểm, không phải lỗ hổng" chỉ đúng trong **đúng
phạm vi ca thử đã ghi ở mục 4**, và mọi câu dạng "0 …" trong tài liệu này đều kèm công cụ đo,
phạm vi đo, và loại đối tượng nằm ngoài phạm vi, theo `CLAUDE.md` §12.1 luật 5.

**Các bản vá bảo mật quan trọng cần người rà trước khi lên production: xem mục 5.**
