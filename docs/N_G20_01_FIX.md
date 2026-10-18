# N-G20-01 — `gioi_han.xoa_het()` XOÁ KHO ĐẾM **DÙNG CHUNG**: SỬA Ở HARNESS G18

**Làn:** AG-04 / V1 (`v1-g6-gioihan`) · **Nền đo:** `5fc5f6f` (`integration/g20`)
**Tệp sửa:** `trien_khai/g18/harness_tai.py` · **Tệp mới:** `docs/N_G20_01_FIX.md`
**KHÔNG sửa:** `app/thu/thu_qa_g21.py` (ca `G6_HarnessGioiHan` — tệp của làn U3) ·
`app/gioi_han.py` · **không** skip ca nào · **không** hạ ngưỡng nào.

---

## 1. KẾT LUẬN NGẮN

`gioi_han.xoa_het()` xoá **TOÀN BỘ** hai bảng `gioi_han_luot` + `gioi_han_chan` trong CSDL
**DÙNG CHUNG** giữa tiến trình harness và các tiến trình `server.py`. Bước **G18-04b** của
`trien_khai/g18/harness_tai.py` gọi nó **trong tiến trình harness**, nên nó xoá luôn bucket
`webhook.chu_ky_sai` mà **máy chủ đang chạy** vừa làm đầy ⇒ chặng **G18-05** (mong đợi `429`) nhận
`401`, không có `Retry-After` ⇒ harness thoát `1` ⇒ ca **G6** ĐỎ.

Bản vá **không** đụng ca G6 và **không** xoá bảng nào:

| # | Việc | Chỗ sửa |
|---|---|---|
| 1 | Khai kho SQLite cho nền TẠM bằng đường chung `cau_hinh.khai_kho_kiem_thu()` | `harness_tai.py::main()` |
| 2 | G18-04b dọn **THEO KHOÁ** của chính chặng (`dinh_danh = "g18-do-truc-tiep"`) thay vì `xoa_het()` | `harness_tai.py` G18-04b |
| 3 | G18-07a **tự giành ngân sách của mình** theo đúng hai khoá nó tiêu, thay vì hưởng lợi từ lượt xoá sạch toàn cục | `harness_tai.py` G18-07 |

### Bảng trước / sau (số đo THẬT, xem §5 để có lệnh + log)

| Trạng thái | `rc` | Số ca | `G18-05` | `G18-07a` |
|---|---|---|---|---|
| **TRƯỚC** — chưa khai kho (G22 fail-closed) | **3** | harness dừng ở "DỰNG NỀN TẠM" | không chạy | không chạy |
| **TRƯỚC** — khai kho bằng tay `VIP_KHO_DANG_CHAY=sqlite` | **1** | 16/20 đạt · **1 hỏng** · 1 BLOCKED · 2 bỏ qua | **✗ 401** | ✓ |
| **SAU** — bản vá, **không** đặt `VIP_KHO_DANG_CHAY` (harness tự khai) | **0** | **17/20 đạt · 0 hỏng** · 1 BLOCKED · 2 bỏ qua | **✓ 429 · Retry-After=300** | ✓ 50×202 |
| **ĐỐI CHỨNG ÂM** — bản vá + **quay lại** `gioi_han.xoa_het()` | **1** | 16/20 · **1 hỏng** | **✗ 401** (ĐỎ LẠI) | ✓ |

---

## 2. TÁI HIỆN VÀ TRUY NGUYÊN

### 2.1 Hai tầng của lỗi (đo được, không suy đoán)

```sh
$ VIP_HUB_DATA=$(mktemp -d) sh trien_khai/g18/chay_harness.sh      # KHÔNG khai VIP_KHO_DANG_CHAY
…
── DỰNG NỀN TẠM ──────────────────────────────────────────────
  ✗ migrate hỏng: [migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy …
# === mã thoát = 3
```

Tầng 1 là **thiết lập đo**: từ G22, `migrate.py` fail-closed khi chưa khai `VIP_KHO_DANG_CHAY`;
harness viết trước G22 nên chưa khai. Cấp đủ môi trường bằng tay thì harness chạy hết và lộ
**tầng 2 — lỗi thật**:

```sh
$ VIP_HUB_DATA=$(mktemp -d) VIP_KHO_DANG_CHAY=sqlite sh trien_khai/g18/chay_harness.sh
…
── G18-05. HEADER TRẦN TRÊN LƯỢT BỊ CHẶN ─────────────────────
  ✗ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
        HTTP=401 · Retry-After=None · X-RateLimit-Limit=None · X-RateLimit-Window=None
…
KẾT LUẬN: 16/20 ca đạt · 1 hỏng · 1 BLOCKED · 2 bỏ qua
# === mã thoát = 1
```

### 2.2 `xoa_het()` được gọi ở đâu, trong tiến trình nào, xoá cái gì

* **Gọi ở đâu:** `trien_khai/g18/harness_tai.py` — bước **G18-04b** (bản `5fc5f6f`: dòng 876).
* **Tiến trình nào:** tiến trình **HARNESS**, KHÔNG phải `server.py`. PID harness khác PID hai
  máy chủ (xem §2.3). Đây là điểm mấu chốt: dưới ngữ nghĩa CŨ (bộ đếm trong bộ nhớ một tiến
  trình) lời gọi này vô hại; dưới ngữ nghĩa MỚI (G19/AG-02: bộ đếm nằm trong CSDL dùng chung)
  nó là một lượt **xoá kho của NGƯỜI KHÁC**.
* **Xoá cái gì:** `app/gioi_han.py::KhoCSDL.xoa_het()` chạy
  `DELETE FROM gioi_han_luot` + `DELETE FROM gioi_han_chan` — **cả hai bảng**, mọi bucket, không
  theo khoá. Nó xoá luôn bucket `webhook.chu_ky_sai|dinh_danh|wh_sai` (vừa đầy ở G18-04a, kèm
  `chan_den` 300 giây) và `webhook.chu_ky_sai|ip|127.0.0.1`.

Chuỗi nhân quả: G18-04a làm đầy bucket của `wh_sai` (10 lượt, `chan_den = now + 300`) → G18-04b
gọi `xoa_het()` từ harness ⇒ bảng bị xoá sạch → G18-05 gửi lượt kế tiếp: `server.py` kiểm trần
lại từ 0 ⇒ **401** thay vì **429**.

### 2.3 ĐỐI CHỨNG (a) — kho đếm là DÙNG CHUNG giữa hai PID (đo lại trên chính cây này)

```sh
$ VIP_HUB_DATA=/tmp/veh_dc_a python3 /tmp/veh_dc_a/p1.py
P1 pid=54205 GHI 3 luot => so dong gioi_han_luot = 6
$ VIP_HUB_DATA=/tmp/veh_dc_a python3 /tmp/veh_dc_a/p2.py
P2 pid=54216 TRUOC xoa = 6 · SAU xoa = 0  <== TIEN TRINH KHAC xoa sach kho cua P1
```

Dưới ngữ nghĩa "bộ nhớ một tiến trình", con số thứ hai **bắt buộc** phải là `0` ngay từ đầu.
Nó là `6`. Kho đếm dùng chung thật, và `xoa_het()` từ một tiến trình xoá được kho của tiến trình
khác. (Mỗi lượt `kiem` ghi **hai** dòng — chiều `dinh_danh` + chiều `ip` — nên 3 lượt = 6 dòng.)

### 2.4 ĐỐI CHỨNG (b) — bỏ ĐÚNG một lời gọi thì hai ca hỏng **ĐỔI CHỖ**

Sao lưu `harness_tai.py`, bỏ đúng dòng `gioi_han.xoa_het()` (không sửa gì khác), chạy lại:

| Bản | `G18-05` | `G18-07a` | `rc` |
|---|---|---|---|
| **A** — `5fc5f6f` (có `xoa_het()`) | **✗ 401** | ✓ `{202: 50}` | 1 |
| **B** — bỏ đúng `xoa_het()`, giữ mọi thứ khác | **✓ 429 · Retry-After=300** | **✗ `{429: 50}`** | 1 |

Đọc hai cột cùng nhau mới ra chẩn đoán: **harness G18 không thể xanh dưới ngữ nghĩa mới** khi
còn `xoa_het()`, vì hai chặng dựa vào hai giả định **loại trừ nhau**:

* **G18-05** cần bucket `webhook.chu_ky_sai` của `wh_sai` **VẪN CẠN** ⇒ `xoa_het()` làm nó đầy lại
  ⇒ `401`.
* **G18-07a** cần ngân sách chữ ký sai theo IP được **giải phóng**: `server.py` kiểm trần
  `webhook.chu_ky_sai` **TRƯỚC KHI** so chữ ký (dòng 455), nên sau khi các chặng CỐ Ý sai chữ ký
  (G18-04a · G18-04b · G18-06a) tiêu hết **30 lượt/IP**, **mọi** lượt sau — kể cả lượt có chữ ký
  ĐÚNG — bị `429`. Đọc thẳng CSDL sau lượt B: `webhook.chu_ky_sai|ip|127.0.0.1 = 30` **và** có
  `chan_den`; `webhook.chu_ky_sai|dinh_danh|wh_sai = 10` + `chan_den`. ⇒ Bỏ `xoa_het()` mà không
  tự giành ngân sách thì G18-07a ĐỎ.

---

## 3. BẢN VÁ (ba phần, đều nằm trong `trien_khai/g18/harness_tai.py`)

### 3.1 Khai kho cho nền TẠM bằng ĐƯỜNG CHUNG (đóng tầng `rc=3`)

```python
    try:
        kho = cau_hinh.khai_kho_kiem_thu()
    except SystemExit as e:
        print("\n  ✗ khai kho cho nền kiểm thử hỏng: %s" % e)
        return 3
    print("  ✓ kho đang chạy khai cho nền TẠM: %s (qua `cau_hinh.khai_kho_kiem_thu()`)" % kho)
```

Đặt **trước** `env = dict(os.environ, …)` nên mọi tiến trình con (`migrate.py`, `khoi_tao.py`,
`server.py`) thừa hưởng `VIP_KHO_DANG_CHAY`. Dùng đúng đường chung thay vì một dòng
`os.environ[...] = "sqlite"` viết tay: `khai_kho_kiem_thu()` có **hai chốt cô lập** (từ chối khi
chưa đặt `VIP_HUB_DATA`; từ chối khi thư mục dữ liệu nằm trong cây repo hoặc là volume `/du-lieu`).

### 3.2 G18-04b — dọn THEO KHOÁ của chính chặng, KHÔNG xoá bảng

```python
        import gioi_han
        # N-G20-01: KHÔNG `xoa_het()` kho đếm DÙNG CHUNG từ tiến trình harness.
        # Đường gọi thẳng hàm dùng `dinh_danh` riêng `g18-do-truc-tiep` ⇒ chỉ khoá ấy là của harness.
        gioi_han.dat_lai("webhook.chu_ky_sai", dinh_danh="g18-do-truc-tiep")
```

`dat_lai("webhook.chu_ky_sai", dinh_danh=…)` xoá đúng khoá
`webhook.chu_ky_sai|dinh_danh|g18-do-truc-tiep` (cả dòng đếm lẫn dòng `chan_den`). Với
`ip=None`, nhánh chiều `ip` chỉ tính khoá `ip|khong-ro` (không tồn tại) — **không** đụng
`webhook.chu_ky_sai|ip|127.0.0.1` mà máy chủ đang dùng. Kết quả đo: chuỗi
`['cho_qua'×10, 'chan'×4]` — vẫn đúng trần 10 của `dinh_danh`, vẫn khớp đường HTTP (G18-04c).

### 3.3 G18-07a — TỰ GIÀNH NGÂN SÁCH CỦA MÌNH, theo đúng hai khoá nó tiêu

```python
        # HAI khoá là ngân sách DO CHÍNH HARNESS TIÊU, nên giành lại cũng đúng hai khoá ấy:
        #   · webhook.nhan|dinh_danh|wh_ma        — G18-03 đã tiêu 300 lượt vào tài khoản này
        #   · webhook.chu_ky_sai|ip|127.0.0.1     — các chặng CỐ Ý sai chữ ký đã tiêu hết 30 lượt IP
        gioi_han.dat_lai("webhook.nhan", dinh_danh=wh_ma)
        gioi_han.dat_lai("webhook.chu_ky_sai", ip="127.0.0.1")
```

Đây **KHÔNG** phải `xoa_het()`: không đụng bảng, không đụng bucket của tài khoản khác
(`wh_moi`, `wh_da`, `wh_sai`), và không đụng khoá nào ngoài hai khoá kể trên. Kết quả:
`mã={202: 50}` — đối chứng âm một luồng vẫn ĐẠT.

> **Vì sao dùng `dat_lai` (đường công khai) chứ không `KHO.xoa(khoá)`:** khoá có dạng
> `endpoint|chieu|giá_trị` là chi tiết bên trong `gioi_han`; dựng lại chuỗi ấy trong harness là
> nhân bản một định dạng nội bộ — đúng khuôn "hai bản sao của cùng một luật" mà dự án đã dính
> nhiều lần. `dat_lai` là API sẵn có, xoá **theo từng khoá**, không có nhánh nào `DELETE` cả bảng.

**`app/gioi_han.py` KHÔNG bị sửa.** `xoa_het()` vẫn còn đó và vẫn đúng cho kho **CÔ LẬP thật**
(ví dụ kho bộ nhớ của `app/thu/thu_g21_gioihan.py`); lỗi nằm ở **chỗ gọi** nó với CSDL dùng chung,
không nằm ở hàm.

---

## 4. ĐỐI CHỨNG ÂM BẮT BUỘC — quay lại `xoa_het()` thì `G18-05` PHẢI ĐỎ LẠI

Làm THẬT (không khẳng định suông): trên **bản đã vá**, thay đúng một dòng

```python
gioi_han.dat_lai("webhook.chu_ky_sai", dinh_danh="g18-do-truc-tiep")
```

bằng dòng cũ

```python
gioi_han.xoa_het()
```

rồi chạy lại nguyên lệnh:

```sh
$ VIP_HUB_DATA=$(mktemp -d) sh trien_khai/g18/chay_harness.sh
── G18-05. HEADER TRẦN TRÊN LƯỢT BỊ CHẶN ─────────────────────
  ✗ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
        HTTP=401 · Retry-After=None · X-RateLimit-Limit=None · X-RateLimit-Window=None
KẾT LUẬN: 16/20 ca đạt · 1 hỏng · 1 BLOCKED · 2 bỏ qua
# === mã thoát = 1
```

Sau đó **phục hồi nguyên văn** bản vá (`diff` với bản lưu là RỖNG) và chạy lại: `rc=0`.
⇒ Cổng G6 **đỏ lại được** khi lỗi tái xuất; nó không phải một cổng đã bị làm cho xanh bằng cách
sửa ca, skip hay hạ ngưỡng.

---

## 5. BẢNG BẰNG CHỨNG — LỆNH · MÃ THOÁT · SỐ CA · LOG

| # | Lệnh | `rc` | Kết quả |
|---|---|---|---|
| 1 | `VIP_HUB_DATA=<tmp> sh trien_khai/g18/chay_harness.sh` (chưa khai kho) | **3** | dừng ở `migrate`: `TỪ CHỐI: CHƯA KHAI kho đang chạy` |
| 2 | `VIP_HUB_DATA=<tmp> VIP_KHO_DANG_CHAY=sqlite sh …/chay_harness.sh` | **1** | 16/20 · 1 hỏng · `G18-05 ✗ 401` |
| 3 | Bản B — bỏ đúng `xoa_het()`, giữ mọi thứ khác | **1** | `G18-05 ✓ 429` · **`G18-07a ✗ {429:50}`** |
| 4 | **Bản vá** — `VIP_HUB_DATA=<tmp> sh …/chay_harness.sh` (**không** đặt `VIP_KHO_DANG_CHAY`) | **0** | **17/20 đạt · 0 hỏng** · `G18-05 ✓ 429` · `G18-07a ✓ {202:50}` |
| 5 | Đối chứng âm — bản vá + quay lại `gioi_han.xoa_het()` | **1** | **`G18-05 ✗ 401`** (ĐỎ LẠI) · 16/20 |
| 6 | Hai-PID: `p1.py` ghi 3 lượt → `p2.py` đếm rồi `xoa_het()` | — | `P1 pid 54205: 6 dòng` → `P2 pid 54216: TRƯỚC=6 · SAU=0` |

Dòng `G18-05` của bản vá (nguyên văn từ log):

```
  ✓ [G18-05] lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP
        HTTP=429 · Retry-After=300 · X-RateLimit-Limit=10 · X-RateLimit-Window=60
```

`[G18]` báo cáo máy đọc được của bản vá: `{'DAT': 13, 'DAT_MOCK': 4, 'HONG': 0, 'BLOCKED': 1,
'BO_QUA': 2}` (kế thúc bằng `17/20 ca đạt · 0 hỏng`). `G18-06a` vẫn `BLOCKED` — đó là **phạm vi
đo** đã ghi từ trước (hai tiến trình trên CÙNG một CSDL, trần KHÔNG nhân — đúng ngữ nghĩa mới),
không phải ca hỏng.

---

## 6. BỘ NGHIỆM THU G21 — `VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py`

### 6.1 Trên cây ĐANG BẨN (bản vá chưa commit) — ĐỌC KỸ VÌ SAO CÓ 3 FAILURE

```sh
$ VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py
Ran 24 tests in 84.463s
FAILED (failures=3, skipped=3)
# === EXIT = 1
```

Ba failure **không phải** lỗi sản phẩm, mà là **cổng "cây sạch" của wave trước** nhìn thấy tệp
`trien_khai/g18/harness_tai.py` đang **sửa dở chưa commit** — chúng đo `git status`, không đo mã:

| Ca | Vì sao ĐỎ trên cây bẩn | Khi commit thì |
|---|---|---|
| `G1` (`cong-cay-sach`) | `3/3` cổng wave trước (`thu_qa_g17/g18/g20_baomat`) ĐỎ vì `M trien_khai/g18/harness_tai.py`; `_la_ten_vung()` chỉ tha thư mục tên `docs`/`thu*`, còn `trien_khai/g18` KHÔNG thuộc vùng thử/tài liệu | XANH (cây sạch) |
| `G7` (`bo-g19-tong-hop`) | hai bộ `thu_qa_g19*.py` thoát 1 — cũng vì cổng cây sạch của chúng thấy tệp đang sửa dở | XANH |
| `Z2` | `git status` ngoài `TEP_DUOC_PHEP` = `[' M trien_khai/g18/harness_tai.py']` | RỖNG |

Ca **`G6` đã XANH** trong lượt này (`G6` không còn trong danh sách failure); phần còn lại là
**ràng buộc giữa các làn**: muốn đo bộ G21 ở trạng thái đóng thì cây phải **sạch** (đã commit).
Vì vậy bản vá được **commit cục bộ** (không push) rồi đo lại — xem §6.2.

### 6.2 Trên cây ĐÃ COMMIT (trạng thái đóng) — KẾT QUẢ NGHIỆM THU

<!-- KET_QUA_COMMIT -->
_(sẽ điền số đo THẬT sau khi commit — bảng này chỉ được ghi bằng log của lượt chạy, không suy đoán)_

---

## 7. CÒN LẠI — NÓI THẲNG

1. **`G18-06a` vẫn `BLOCKED`** — đây là ca quan sát "trần có nhân theo số tiến trình không" và
   câu trả lời đo được là **KHÔNG nhân** (10 lượt, không phải 20) — tức ngữ nghĩa mới đang đúng.
   Không phải nợ của N-G20-01.
2. **`app/gioi_han.py` không đổi.** `xoa_het()` vẫn là API hợp lệ cho kho cô lập; nếu về sau có
   ai gọi nó từ một tiến trình chạm CSDL dùng chung, lỗi sẽ tái xuất đúng như đối chứng âm §4.
   Cách phòng ngừa là **dùng `dat_lai`/khoá riêng** trong harness, không phải bỏ hàm.
3. **Không push / không deploy / không gọi hãng.** Mọi phép đo chỉ chạm `127.0.0.1`, CSDL SQLite
   trong thư mục TẠM, `CHO_PHEP_LIVE` vẫn `False` (harness tự kiểm 12 chốt + 4 phép tiêm lỗi
   trước khi chạy).
