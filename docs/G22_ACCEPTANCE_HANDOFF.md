# G22 — BÀN GIAO NGHIỆM THU LOCAL

**Controller:** DeepSeek (AG-00) · **Ngày:** 18/10/2026 · **Gate:** G22
**Nhánh tích hợp:** `integration/g22` (worktree `Projects-vip-express-hub`, nhánh git `integration/g20`)
**`main`:** `de740dc` — **CHƯA ĐỤNG SUỐT wave**

---

## 1. SHA VÀ HASH

| Hạng mục | Giá trị |
|---|---|
| **SHA nghiệm thu** | `e4d3f5ca49fd0bef4dd63f8497f22d086d968966` |
| `PHIEN_BAN_SCHEMA` | **10** |
| Cây git | **SẠCH** (0 dòng `git status`) |
| `main` | `de740dc` (không đổi) |
| Remote | **0** (không có remote ⇒ không thể push) |

## 2. KẾT QUẢ TỪNG BỘ — chế độ riêng của từng bộ (exit TỪNG BỘ)

| Bộ | Lệnh | Exit | Ran | Kết quả |
|---|---|---|---|---|
| **G20** | `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` | **0** | 21 | `OK (skipped=3)` |
| **G21** | `VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py` | **0** | 24 | `OK (skipped=3)` |
| **G22** | `VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py` | **0** | 29 | `OK (skipped=1)` |

> **CẢNH BÁO VỀ CÁCH CHẠY — tôi đã mắc lỗi này một lần:** đặt **cả ba** biến `..._CHE_DO=gop` cùng
> lúc làm `D1` (chạy G20 như bộ con) và `G7` (chạy G21) chạy **sai chế độ** ⇒ thấy `G22 failures=2`
> **GIẢ**. **Phải chạy mỗi bộ đúng biến của nó.**

## 3. CLEAN-COPY — `EXIT_BO_DO = 0`, hai bên KHỚP

```
cùng commit  : worktree = e4d3f5ca49fd… · bản sao = e4d3f5ca49fd… · yêu cầu = e4d3f5c  ✓
cùng bộ kiểm : sha256 CÓ
Ran N        : 24 / 24   CÓ
PASS         : 23 / 23   CÓ
FAIL         : 0  / 0    CÓ
SKIP         : 1  / 1    CÓ
tổng kết     : OK (skipped=1) / OK (skipped=1)
ĐỦ ĐIỀU KIỆN : CÓ
Mã thoát BỘ KIỂM G22 : worktree = 0 · bản sao = 0
```

**Ghi chú phải nêu:** bộ đo chạy **không đặt `VIP_HUB_DATA`** ⇒ `Ran 24`; tôi chạy trực tiếp **có**
đặt ⇒ `Ran 29`. Tệp có **32 `def test_`**. Số ca chạy thật **phụ thuộc môi trường** — hai bên vẫn
khớp nhau vì cùng môi trường, nhưng **đây là giới hạn phép đo, không phải hằng số**.

## 4. DANH SÁCH SKIP — từng ca, kèm lý do

**G20 — 3 skip**
| Ca | Lý do |
|---|---|
| ca dị dạng `GIT_CONFIG` | `CHƯA ĐO: phiên này KHÔNG đặt GIT_CONFIG_COUNT` |
| `test_h1_hoi_quy_toan_phan` | `CHƯA ĐO: làn đầy đủ (VIP_G20_DAY_DU=1)` |
| CA CỐ Ý HỎNG | `mồi cho T2 — chỉ chạy trong tiến trình con của T2` |

**G21 — 3 skip**: `test_h1_hoi_quy_toan_phan` (`CHƯA ĐO: VIP_G21_DAY_DU=1`) · *Mồi ĐẠT cho T2* · *Mồi HỎNG cho T2*

**G22 — 1 skip**: CA CỐ Ý HỎNG — `mồi cho Z5 — chỉ chạy trong tiến trình con của Z5`

⇒ **Hợp lệ**: hoặc là **mồi cho đối chứng âm** (bỏ đi thì `T2`/`Z5` mất răng), hoặc **làn đầy đủ
chưa bật** và **được ghi thẳng là `CHƯA ĐO`** — tức **giới hạn phạm vi, KHÔNG phải ĐẠT**.

## 5. LÀN ĐẦY ĐỦ — **khoảng hở CHƯA ĐÓNG**

`VIP_G20_DAY_DU=1` chạy `test_h1_hoi_quy_toan_phan`, mà ca đó chạy **`sh app/thu/chay_tat_ca.sh`**
(hồi quy toàn dự án). Đo được:

```
G20 làn đầy đủ: exit=1 · Ran 21 · FAILED (failures=2, skipped=2)
   FAIL test_h1_hoi_quy_toan_phan      ← chạy chay_tat_ca.sh, chưa xanh
   FAIL test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong
```

**⇒ Hồi quy TOÀN DỰ ÁN (`chay_tat_ca.sh`) CHƯA XANH.** Đây là **giới hạn thật**, không phải chi
tiết nhỏ: ba bộ G20/G21/G22 xanh **không đồng nghĩa** toàn bộ ~1900 ca của dự án xanh.

## 6. UAT LOCAL — chạy thật, đạt

```
khoi_dong.sh EXIT=0
  URL      : http://127.0.0.1:57586/admin/
  PID      : 35783   (health báo pid=35783 — KHỚP PID đã ghi)
  Dữ liệu  : /Users/viporder/veh-uat   ← thư mục RIÊNG, ngoài repo, marker .veh-uat-fixture.json
  Tài khoản: platform-owner · shopa-owner · shopa-staff · shopa-viewer · da-tenant · shopb-owner
             mật khẩu FIXTURE sinh ngẫu nhiên ở veh-uat/TAI-KHOAN-UAT.md
  Hãng     : mock — mọi adapter live_mo=False, KHÔNG gọi API hãng

gọi API loopback : HTTP / = 200
dung.sh EXIT=0
  PID 35783 : không còn tồn tại (kiểm bằng kill -0)
  Cổng 57586: không còn LISTEN (kiểm bằng TCP loopback)
  Dữ liệu vẫn ở ~/veh-uat (không bị xoá)
tiến trình mồ côi : 0
```

Hướng dẫn đầy đủ: **`docs/UAT_LOCAL.md`** (447 dòng). Script: `trien_khai/uat/`.

**Dừng bằng đúng PID đã ghi — không `pkill`/`killall`** (đã có tiền lệ pkill làm chết tiến trình
của người khác).

## 7. NHỮNG LỖI ĐÃ ĐÓNG TRONG WAVE NÀY

| Mã | Lỗi | Cách đóng | Commit |
|---|---|---|---|
| `N-G22-01` | C5/G7 không trừ ca bỏ qua ⇒ **mọi ca skip ở mức phương thức vẫn XANH** | Bản vá vào **TỆP NGUỒN**; đường tạm xoá hẳn; 5 hình dạng tiêm lỗi trên **cùng SHA** | `06a79c2` · `a76ec51` |
| `N-G22-03` | Bộ đếm `chay_tat_ca.sh` không có khuôn `N ca — HỎNG` ⇒ cổng đỏ bị đếm **0 ca** | Sửa bộ đếm + **fixture chống sai đếm** 4 trường hợp | `6ac4d0a` |
| **XANH GIẢ `D1`** | `D1` chạy G20 nhưng **không đọc mã thoát** ⇒ G20 exit 1 mà D1 PASS | D1 **phán quyết theo MÃ THOÁT** + 4 đối chứng âm | `30bf7b3` |
| `N-G20-01` | `gioi_han.xoa_het()` xoá kho đếm **DÙNG CHUNG** ⇒ `G18-05` đỏ | Dọn **theo KHOÁ**; harness khai SQLite | `cd4f22a` |
| **`G19-C6`** | Route `truy_van` **không tệp sản xuất nào import**; `DDL_G12Q` chưa áp | Nối route vào `server.py`; **`nang_len_v10`** áp `DDL_G12Q` (**9/9 chỉ mục trên fixture `v9→v10`**, idempotent, 2 đối chứng âm) | `146500b` · `f1e4f90` |
| **Ghim trôi** (họ `H5`/`N-G19-04`) | `TREE_NEN` · `SO_DO` · `H_C4` · `NEN_SHA` là **hằng số** ⇒ đỏ lại sau mỗi lần gộp | **Đọc TẠI CHỖ** (`HEAD^{tree}`, `csdl.PHIEN_BAN_SCHEMA`, đếm tham chiếu) + giữ đối chứng âm | `a6b5b73` · `031d95a` |
| **Bộ đo sai** | `os.path.abspath()` không giải symlink ⇒ `/private` sinh "lệch" giả | `os.path.realpath()` | `b1c5205` |

**Một họ lỗi lặp 5 lần:** *ghim SỰ THẬT MÔI TRƯỜNG thay vì ghim BẤT BIẾN.* Nguyên tắc áp dụng
**không đổi lần nào**: viết lại khẳng định theo **bất biến đúng** · **GIỮ đối chứng âm** ·
**không xoá ca** · **không nới assert**.

## 8. BẢO MẬT — 7/7 mặt ĐẠT (`thu_g22_regression.py`, 35 ca, 0 skip, exit 0)

| Mặt | Đo được |
|---|---|
| tenant isolation | **A→A 200** vs **A→B 404** |
| RBAC | 403 vs 201 |
| fail-closed | rc=1 vs rc=0 (5 kịch bản, vân tay `hub.db` không đổi) |
| idempotency | (201,200) cùng id, +1 vs +2 |
| webhook | 401 (0 sự kiện) vs 202 (+1) |
| **rò rỉ chéo tenant** | **0/11 phản hồi + 0/2 log trên đĩa + 0/15 tệp bằng chứng** |
| **gửi ra ngoài** | **74 kết nối TOÀN loopback · 0 tới `:5432`** · mọi adapter `live_mo=False` |

**7 phép tiêm lỗi ngoài** trên bản sao cây trong TMP ⇒ **ĐỎ ĐÚNG CA (7/7, rc=1)**.

## 9. GIỚI HẠN PHẠM VI — KHÔNG ĐO ĐƯỢC

- **Hồi quy TOÀN DỰ ÁN chưa xanh** (`chay_tat_ca.sh`) — xem §5
- **Làn đầy đủ** (`VIP_*_DAY_DU=1`) chưa đóng: 2 ca đỏ ở G20
- **Số ca phụ thuộc `VIP_HUB_DATA`** (24 ≠ 29)
- Webhook `jt_digest` **ngoài mock** · **idempotency đa tiến trình** · danh tính tiến trình giết máy chủ
- **KHÔNG có lệnh gọi hãng nào, kể cả sandbox** (`V-G09-01`)

## 10. BLOCKED OWNER — không phải lỗi local

| Mã | Nội dung |
|---|---|
| **`OWNER_ACTIONS` C4 / D-8** | *"Chuyển CSDL nghiệp vụ sang PostgreSQL"* — **CHƯA chuyển**, vẫn SQLite. **KHÁC `G19-C6`.** |
| `V-G09-01` · `V-13906-05` | API hãng (kể cả sandbox) + credentials thật — **CHƯA CẤP** |
| `V-G11-01` | URL webhook công khai |
| `V-13913` | Docker |

## 11. KẾT LUẬN TRUNG THỰC

**ĐẠT:** ba bộ G20/G21/G22 xanh trên **cùng một SHA** · clean-copy **khớp hoàn toàn**, `EXIT_BO_DO=0` ·
UAT khởi động–gọi API–dừng sạch, **0 tiến trình mồ côi** · bảo mật **7/7 mặt** · không có lệnh gọi
hãng nào.

**CHƯA ĐẠT:** **hồi quy toàn dự án chưa xanh** (§5). Đây là **khoảng hở thật** và tôi **không** gộp
nó vào chữ "PASS".

**Vì vậy tôi KHÔNG tuyên bố G22 PASS.** Tôi bàn giao để **chủ dự án nghiệm thu** với đầy đủ số đo,
và với một giới hạn được nêu thẳng thay vì bị giấu.

**Không push · không deploy · không API hãng · không dữ liệu thật · không mở G23.** `main` giữ
`de740dc`. `OWNER_ACTIONS C4`/D-8 giữ **BLOCKED**.
