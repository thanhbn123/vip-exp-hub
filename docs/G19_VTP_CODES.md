# G19 (AG-03) — MÃ TRẠNG THÁI VIETTEL POST: ĐÃ ÁP 13 CON SỐ CÓ NGUỒN, KHÔNG ĐOÁN CON NÀO

**Nền:** `integration/g18 @ 6e61fc1` · **Nhánh:** `g19-ag03-vtp` (worktree riêng)
**Lỗ hổng đóng:** `docs/BAN_GIAO.md` §6.1, dòng *«21 mã trạng thái Viettel Post (AG-03 khảo sát,
chưa áp)»* — và `docs/G16_G25_LOCAL_PLAN.md:187` (AG-04), `:71`.
**Tệp được phép ghi:** `app/trang_thai_hang.py` · `app/thu/thu_g19_vtp.py` (mới) · tệp này (mới).

> **KHÔNG gọi hãng, kể cả sandbox.** `V-G09-01` + `V-13906-05` CHƯA CẤP. Tệp này và bộ thử của nó
> không mở socket, không HTTP, không credentials — ép bằng mã ở lớp `F` của bộ thử.
> **KHÔNG** push · **KHÔNG** deploy · **KHÔNG** mở cổng · **KHÔNG** chạm `CHO_PHEP_LIVE`.

---

## 1. ĐỌC LẠI NGUỒN TRONG REPO: 21 LÀ CON SỐ, KHÔNG PHẢI DANH SÁCH

Đây là phát hiện định hình toàn bộ việc của G19, nên nói trước mọi con số khác.

| Nguồn (trong chính repo này) | Nói gì |
|---|---|
| `docs/VTP_YEU_CAU_BO_SUNG.md:36` | Bộ mã chính thức của VTP có **21 mã**: **15 mã có ánh xạ** + **6 mã cố ý KHÔNG ánh xạ** — và **nêu đích danh cả sáu**: `102, 202, 503, 505, 508, 550`. Nguồn dẫn: `partner2.viettelpost.vn/document/webhook`, mục *«Bảng danh sách trạng thái»* |
| `docs/G12_VTP_KHAO_SAT.md:86`, `:120`, `:377` | Cùng dữ kiện, ghi lại lần thứ hai (khảo sát độc lập trên `develop 68e9642`). `:120` chốt: **«Không một mã THẬT nào của VTP có trong hệ»** |
| `app/adapter_vtp.py:13` | Cùng dữ kiện, lần thứ ba |
| `docs/VTP_YEU_CAU_BO_SUNG.md:80` (câu **B1**) | `104` = «Lấy hàng điều phối bưu tá»; nhóm **trạng thái CUỐI** theo đoạn «Lưu ý» = `101/107/201/501/503/504`; `200` = «lấy hàng thành công» |
| `docs/VTP_YEU_CAU_BO_SUNG.md:83` (câu **B4**) | `505` = «Yêu cầu chuyển hoàn»; `503` = «Tiêu huỷ theo yêu cầu khách hàng» |
| `docs/G09_FINAL_REPORT.md:200-206`, `:392` | Mâu thuẫn của `104` + bản vá **P4b**: *«đưa 104 vào sổ `NHAP_NHANG` ngay»* |
| `docs/G12_VTP_KHAO_SAT.md:150` | Cùng mâu thuẫn `104`, kèm chỉ thị *«Phải vào sổ `NHAP_NHANG` khi mang sang»* |

**ĐẾM ĐƯỢC — 13 CON SỐ ĐƯỢC NÊU TÊN:**
`101 · 102 · 104 · 107 · 200 · 201 · 202 · 501 · 503 · 504 · 505 · 508 · 550`

**VÀ ĐÂY LÀ CHỖ PHẢI NÓI THẲNG: repo này KHÔNG chép bảng 21 mã.** Nó chép **con số 21** và **13
cái tên**. **8 con số còn lại KHÔNG hề xuất hiện ở đâu trong repo** — không thể liệt kê, không thể
ánh xạ, và **tuyệt đối không được bịa**. Phép đếm, kèm giả định nói rõ:

```
21 = 15 mã có ánh xạ + 6 mã cố ý None          (nguồn: VTP_YEU_CAU_BO_SUNG.md:36)
6 mã None        đều CÓ TÊN  → 102, 202, 503, 505, 508, 550
15 mã có ánh xạ  chỉ có 7 tên → 101, 104, 107, 200, 201, 501, 504   ← GIẢ ĐỊNH: cả 7 thuộc bộ 21
⇒ 21 − 13 = 8 con số KHÔNG có trong repo, và CẢ 8 đều nằm trong nhóm «có ánh xạ»
  — đúng nhóm mà bảng ánh xạ của ta cần nhất, và cũng đúng nhóm repo không chép lại.
```
**Nếu `200` không thuộc bộ 21** thì con số là **9**; repo không đủ dữ kiện để phân xử (câu hỏi
**B3** gửi hãng). **Dù 8 hay 9, kết luận không đổi**: phần lớn bảng mà ta cần thì repo không có,
và G19 không được phép lấp chỗ đó bằng suy đoán.

**Điểm thứ hai phải nói rõ:** **nguyên văn của hãng KHÔNG có trong repo.** Mọi mô tả dưới đây là
**diễn giải của bản khảo sát**, không phải câu chữ của Viettel Post. Cờ `VTP_CO_NGUYEN_VAN_HANG =
False` trong mã ghi đúng điều đó, và nó **hạ trần độ tin cậy** của cả bảng VTP xuống `trung_binh`
(xem §3 và ca `b3`) — chốt bằng mã, không bằng lời dặn.

---

## 2. BẢNG ĐỐI CHIẾU: MÃ → TRẠNG THÁI → CƠ SỞ

`None` = **chỉ ghi nhận, KHÔNG đổi trạng thái đơn**. Bảng này là bản viết tay của `DOI_CHIEU`
trong `app/thu/thu_g19_vtp.py`; sửa một bên mà không sửa bên kia thì ca `a5` đỏ.

| Mã | Mô tả (diễn giải của khảo sát) | Trạng thái áp được | Nhãn soát | Cơ sở |
|---|---|---|---|---|
| **101** | Trạng thái CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **102** | Có thật; repo nguồn CỐ Ý không ánh xạ — nghĩa không có trong repo | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:36` |
| **104** | Lấy hàng điều phối bưu tá — **TÀI LIỆU TỰ MÂU THUẪN** về việc có phải trạng thái cuối | `None` | `NEEDS_REVIEW` | `:80` + `G12:150` + `G09:200` |
| **107** | Trạng thái CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **200** | **Lấy hàng thành công** | **`lay_hang`** | `OK` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **201** | Trạng thái CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **202** | Có thật; repo nguồn CỐ Ý không ánh xạ | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:36` |
| **501** | Trạng thái CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **503** | Tiêu huỷ theo yêu cầu khách hàng (mã CUỐI) — không trùng nghĩa huỷ/hoàn | `None` | `NEEDS_REVIEW` | `:36` + `:83` (B4) |
| **504** | Trạng thái CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:80` |
| **505** | Yêu cầu chuyển hoàn — dùng cho CẢ «khách từ chối» lẫn «người gửi yêu cầu hoàn» | `None` | `NEEDS_REVIEW` | `:36` + `:83` (B4) |
| **508** | Có thật; repo nguồn CỐ Ý không ánh xạ | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:36` |
| **550** | Có thật; repo nguồn CỐ Ý không ánh xạ | `None` | `NEEDS_REVIEW` | `VTP_YEU_CAU_BO_SUNG.md:36` |

**Tổng: 13 mã — 1 mã áp được (`200`), 12 mã `NEEDS_REVIEW`.** Không mã nào trong 13 được ánh xạ
sang trạng thái HOÀN TẤT (`giao_thanh_cong` / `hoan_hang`): hướng hoàn tất của VTP **chưa ai xác
minh**, nên đóng đơn bằng một mã VTP là đoán — và đó là loại sai đắt nhất.

### Vì sao `104` KHÔNG nằm trong sổ `NHAP_NHANG` như P4b chỉ định

Xem §5 — có phép đo thật. Tóm tắt: một bộ thử **đang xanh** khoá sổ đó vào J&T, và G19 không
được phép sửa tệp đó. Hiệu quả an toàn thì giữ nguyên: không đổi trạng thái đơn + bắt người soát.

### Sổ `CHUA_XAC_MINH` — cơ chế mới, và vì sao phải là sổ RIÊNG

| Sổ | Nghĩa | Nhãn | Chốt được bằng `chot_nghia()`? |
|---|---|---|---|
| `NHAP_NHANG` | Tài liệu nói **hai nghĩa ngược chiều**, cả hai **đã đọc được** | `AMBIGUOUS` | Có (và bị cấm chốt về hoàn tất) |
| `CHUA_XAC_MINH` (mới) | Biết **chắc mã có thật**, nhưng **nghĩa thì repo không có** | `NEEDS_REVIEW` | **Không** — `KeyError`, vì không có nghĩa nào để chốt |

Gộp hai sổ là tự nói dối rằng ta đã đọc được hai nghĩa. Ba loại chưa-xác-minh, không gộp:
`chua_co_nghia` (6 mã) · `huong_cuoi_khong_ro` (5 mã) · `mau_thuan_tai_lieu` (1 mã = `104`).

**Hệ quả cài BẰNG MÃ, không bằng lời dặn** (ca `d2`/`d3` chứng minh bằng đột biến): mã trong sổ
này luôn có `trang_thai_ap = None`, `can_soat = True`, `do_tin_cay = chua_xac_minh`, và bị **CHẶN
CỨNG** khỏi mọi trạng thái hoàn tất — **kể cả khi ai đó sửa thẳng bảng** để gán một giá trị.

---

## 3. ĐỐI CHIẾU VỚI BẢNG ÁNH XẠ TRƯỚC G19

| | Trước G19 | Sau G19 |
|---|---|---|
| Mã **THẬT** của hãng trong `BANG["vtp"]` | **0** (đo bằng `grep`, `G12_VTP_KHAO_SAT.md:120`) | **13** |
| Khoá của bộ mô phỏng | 6 | 6 (**giữ nguyên**, không thay thế) |
| `NGUON_BANG["vtp"]` | «bộ mô phỏng của chính dự án (KHÔNG có tài liệu hãng)» | dẫn 3 tài liệu khảo sát trong repo + ghi rõ **CHƯA đối chiếu trang hãng** |
| `PHIEN_BAN_TAI_LIEU["vtp"]` | `chua-co-tai-lieu` | `khao-sat-gian-tiep-2026-10-15` |
| Trần độ tin cậy của bảng | — | `trung_binh` (nguồn gián tiếp ⇒ không được khai `cao`) |
| `ORDER_STATUS` dạng **chuỗi** (`"200"`) | rơi im lặng vào nhánh «mã lạ» | chuẩn hoá về khoá số (ca `b2`) |

**Gộp chứ không thay** `VTP_MA_MOCK`: bỏ nó là làm chết đường MOCK của adapter VTP. Hai bộ khoá
không đụng nhau (số của hãng vs tên chuẩn của bộ mô phỏng) — ca `a2` canh điều đó.

**J&T KHÔNG bị đụng**: `JT_MA` vẫn 13 khoá, `NHAP_NHANG` vẫn đúng một mục `("jt", 110)`,
`NGHIA_DA_CHOT` vẫn rỗng. Ca `b4`, `e1`–`e3` khoá lại.

---

## 4. BẰNG CHỨNG — LỆNH THẬT, MÃ THOÁT THẬT, SỐ CA THẬT

Mọi lệnh dưới đây chạy trong worktree G19, `python3` hệ thống, **không gọi mạng**.

### 4.1 Bộ thử của G19

```sh
$ python3 app/thu/thu_g19_vtp.py ; echo "EXIT=$?"
Ran 31 tests in 0.005s
OK
EXIT=0
```

**31 ca · 0 hỏng · 0 bỏ qua.** Sáu lớp:

| Lớp | Số ca | Đo cái gì |
|---|---|---|
| `A_BangDoiChieu` | 7 | 13 mã vào bảng **đúng bằng** tập có nguồn; 6 khoá mô phỏng còn nguyên; nguồn/phiên bản nói đúng sự thật; từng mã một khớp bảng §2 |
| `B_CaDuong` | 6 | **ĐỐI CHỨNG DƯƠNG** — đường ánh xạ đang chạy: `200` → `lay_hang`; `"200"` (chuỗi) → `lay_hang`; trần tin cậy hạ đúng chỗ (J&T vẫn `cao`); J&T không bị đụng; **không mã VTP nào đóng được đơn** |
| `C_CaAm` | 7 | **12 mã chưa xác minh → `NEEDS_REVIEW`, `trang_thai_ap = None`**; 6 mã nguồn để trống vẫn trống; 5 mã «cuối không rõ hướng» vẫn không đoán; `104` ghi mâu thuẫn chứ không chọn bên; mã ngoài bảng vẫn là **mã lạ** (khác `NEEDS_REVIEW` của sổ mới); **không `chot_nghia()` được** mã chưa xác minh |
| `D_TuKiemBangDotBien` | 4 | **Bộ dò phải ĐỎ được**: tiêm `giao_thanh_cong` cho `550` → bộ dò thấy **và** chốt cứng của sản phẩm vẫn giữ; tiêm thẳng `hoan_hang` → vẫn bị `CHẶN`; xoá hồ sơ → bộ dò thấy; **đối chứng đường**: không tiêm thì xanh |
| `E_GiuNguyenD4` | 3 | D-4 (`J&T 110`) nguyên vẹn: `AMBIGUOUS`, không đổi đơn, `NGHIA_DA_CHOT` rỗng, sổ nhập nhằng vẫn đúng một mục |
| `F_KhongGoiHang` | 4 | Quét mã nguồn **neo đầu dòng**: **0** dấu vết `import socket/urllib/requests/httpx/http.client` và **0** lệnh gán `CHO_PHEP_LIVE` trong cả tệp sản phẩm lẫn tệp thử; **đối chứng dương** cho chính bộ quét (đưa dòng cấm vào thì nó phải thấy); 0 biến kiểu credentials |

> **Ghi lại một lần bộ dò tự bắt chính nó:** bản đầu của lớp `F` quét `assertNotIn("import socket",
> n)` — và chuỗi đó nằm ngay trong danh sách cấm của chính tệp thử, nên ca `f2` **đỏ một cách vô
> nghĩa**. Sửa bằng cách **neo đầu dòng** (`^\s*(import|from)\s+…`), và thêm ca `f3` làm **đối
> chứng dương** để bộ quét không bị "sửa cho xanh" rồi thành bộ quét rỗng. Đây đúng dạng §12.1:
> *phép đo không đụng tới thứ cần đo thì kết quả đạt của nó vô nghĩa.*

### 4.2 Các bộ thử cũ (chạy lại, KHÔNG sửa tệp nào của G16/G17/G18)

```sh
$ for t in thu_g03 thu_webhook thu_webhook_jt thu_harness_hang thu_qa2_soat thu_adapter_jt thu_qa_soat thu_doi_soat; do
>   python3 app/thu/$t.py >/dev/null 2>&1; echo "$t EXIT=$?"; done
```

| Bộ thử | Mã thoát | Số ca | Số ca hỏng |
|---|---|---|---|
| `thu_g03.py` | **0** | 53 | 0 |
| `thu_webhook.py` | **0** | 68 | 0 |
| `thu_webhook_jt.py` | **0** | 99 | 0 |
| `thu_harness_hang.py` | **0** | 57 | 0 |
| `thu_qa2_soat.py` | **0** | 49 | 0 |
| `thu_adapter_jt.py` | **0** | 84 | 0 |
| `thu_qa_soat.py` | **0** | 30 | 0 |
| `thu_doi_soat.py` | **0** | 27 | 0 |

`thu_g03.py` là bộ **đáng lo nhất**: ca `a8` duyệt **mọi** mã đã biết của **mọi** hãng rồi khẳng
định mã nào có trạng thái thì trạng thái đó phải nằm trong `cau_hinh.HANG_TRANG_THAI_GIAO` — tức
13 mã mới đi thẳng qua lưới đó.

### 4.3 Bộ chạy toàn dự án — và hai bộ ĐỎ vì CÂY BẨN, không vì logic

```sh
$ sh app/thu/chay_tat_ca.sh ; echo "EXIT=$?"
  python:   1662 ca · 45 bộ chạy thật
  frontend: 56 + 36 ca (hai tầng tự động)
  E2E:      41/41 phép đo đạt
  bộ hỏng:  thu_qa_g17.py thu_qa_g18.py
EXIT=1
```

**PHÉP ĐO ĐỐI CHIẾU VỚI NỀN G18 (`1631 ca / 44 bộ`):** nay là **`1662 ca / 45 bộ`**.
`1662 − 1631 = 31` và `45 − 44 = 1` — **đúng bằng bộ thử mới của G19, không sai một ca**. Tức
**không một bộ thử nào khác đổi số ca**: G19 không chạm vào chỗ nào khác của hệ.

**HAI BỘ ĐỎ — nguyên nhân đo được, không phải suy đoán.** Cả hai đều là **chốt "cây sạch"**, và
đỏ vì ba tệp của G19 đang **chưa được commit**:

| Bộ | Số ca | Ca đỏ | Nguyên văn thông điệp |
|---|---|---|---|
| `thu_qa_g17.py` | 53 | **1** — `test_a1_cay_sach_va_head` | `Lists differ: [' M app/trang_thai_hang.py', '?? app/thu/…', '?? docs/…'] != []` |
| `thu_qa_g18.py` | 43 | **1** khi chạy một mình — `test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` | cùng dạng (`assertEqual(git status --porcelain, [])`) |

Hai ca đó **không đọc một dòng logic sản phẩm nào**: chúng chỉ so `git status --porcelain` với
`[]`. Danh sách đỏ trong thông điệp **đúng bằng ba tệp G19 được cấp phép ghi** — không thừa, không
thiếu. Đây là hệ quả của mô hình công việc (worker ghi ra rồi để coordinator gộp), **không phải
hồi quy**.

> **ĐỐI CHỨNG TRÊN CÂY SẠCH: BỊ CHẶN — ghi lại đúng như đã đo, không suy diễn thành "đã kiểm".**
> Lượt chạy đối chứng cần `git checkout --`/`git stash` để trả cây về `6e61fc1` sạch, nhưng
> sandbox `workspace-write` chặn ghi chỉ mục git nằm **ngoài** workspace:
> `fatal: Unable to create '…/.git/worktrees/g19-ag03-vtp/index.lock': Operation not permitted`
> (`exit 128`). Vì vậy khẳng định "hai ca đỏ là do cây bẩn" dựa trên **nguyên văn thông điệp +
> danh sách ca đỏ**, **không** dựa trên một lượt chạy lại trên cây sạch. Ai gỡ được chốt đó
> (commit ba tệp rồi chạy lại) sẽ có kết luận mạnh hơn — và đó là việc của bước gộp.

**`thu_qa_g18.py` ca `b1` (tầng 3, DOM/CSS trong Chromium thật):** đỏ trong **lượt chạy chung**
45 bộ, nhưng **XANH khi chạy một mình** — đo lại:

```sh
$ python3 app/thu/thu_qa_g18.py ; echo "EXIT=$?"
FAIL: test_a1_cay_sach_mien_tru_dung_hai_tep_ag01 (__main__.A_Nen)
Ran 43 tests in 109.602s
FAILED (failures=1, skipped=1)
  [B1] nhị phân: chromium-1194 · mã thoát=0 · 36 đạt · 0 hỏng · 1 bỏ qua
EXIT=1
```

Tầng 3 **đạt 36/36, 0 hỏng**, `b1` xanh; ca đỏ duy nhất còn lại vẫn là `a1` (cây bẩn). Khác biệt
duy nhất giữa hai lượt là **45 bộ chạy chen nhau** — tranh chấp tài nguyên, **không phải ca thử
hỏng**, và cũng không liên quan tới G19 (G19 không đụng một dòng DOM/CSS nào). Lượt chạy chung
**không** in `EPERM`/`Permission denied` nào.

### 4.4 Phạm vi ghi — đúng ba tệp, không hơn

```sh
$ git rev-parse HEAD
6e61fc1e1f1f9a6d64931464e4f40ed887192ab5
$ git status --porcelain
 M app/trang_thai_hang.py
?? app/thu/thu_g19_vtp.py
?? docs/G19_VTP_CODES.md
$ shasum -a 256 app/trang_thai_hang.py app/thu/thu_g19_vtp.py
fb5adbd36ce8f8a8d1f93d39c794611512aee8494b5797c2d92261e0c69dc8c5  app/trang_thai_hang.py
893c2dfcee79d543e5c2a65ac62eceb96785fc9a7f36e0246b50648e12a59aec  app/thu/thu_g19_vtp.py
```

**Không push · không commit · không deploy · không tunnel · không cổng nào được mở.** HEAD vẫn là
`6e61fc1` (`integration/g18`) và chỉ **một** tệp cũ bị sửa — đúng danh sách được cấp.
*(SHA của chính tệp tài liệu này không ghi ở đây được: ghi vào là nó tự đổi — con số đó nằm trong
báo cáo `worker_done`.)*

---

## 5. PHÁT HIỆN: `NHAP_NHANG` ĐANG BỊ KHOÁ VÀO J&T — P4b KHÔNG LÀM ĐƯỢC TRONG PHẠM VI G19

`docs/G09_FINAL_REPORT.md:392` (bản vá **P4b**) và `docs/G12_VTP_KHAO_SAT.md:150` chỉ định rõ:
khi mang mã VTP sang thì **đưa `104` vào sổ `NHAP_NHANG` ngay**. G19 **không làm được**, và đây
là phép đo — không phải ý kiến:

```sh
$ cat >> app/trang_thai_hang.py <<'PY'      # tiêm tạm một mục ("vtp", 104) vào NHAP_NHANG
NHAP_NHANG[("vtp", 104)] = { ... }
PY
$ python3 app/thu/thu_webhook_jt.py ; echo "EXIT=$?"
FAIL: test_j03_hop_dong_callback_khong_duoc_tu_dong_nang_muc (__main__.J_ChotChan)
  File "app/thu/thu_webhook_jt.py", line 1133, in test_j03_hop_dong_callback_khong_duoc_tu_dong_nang_muc
    self.assertIn(ma, tth.JT_MA if ma_hang == "jt" else {}, f"mã nhập nhằng {ma} lạ")
AssertionError: 104 not found in {} : mã nhập nhằng 104 lạ
Ran 99 tests in 1.021s
FAILED (failures=1)
EXIT=1
```

**Nguyên nhân, đọc thẳng mã:** `app/thu/thu_webhook_jt.py:1132-1133` duyệt `tth.NHAP_NHANG` rồi
khẳng định mỗi mã nhập nhằng phải có trong **bảng của chính hãng đó** — nhưng biểu thức viết là
`tth.JT_MA if ma_hang == "jt" else {}`, tức **mọi hãng khác J&T nhận `{}`** và luôn đỏ. Đây là
một chốt thời G14 ("sổ nhập nhằng chỉ có J&T"), đúng lúc đó và **sai từ hôm nay**.

**Sau khi gỡ tiêm:** `sha256` của `app/trang_thai_hang.py` **khớp lại từng ký tự** với bản trước
khi tiêm, và `python3 app/thu/thu_webhook_jt.py` → **EXIT=0**.

**G19 chọn cách không phá chốt của người khác:** `104` vào **sổ `CHUA_XAC_MINH`** với
`loai = "mau_thuan_tai_lieu"` và hồ sơ ghi **cả hai vế** của mâu thuẫn. Hiệu quả an toàn **như
nhau và đo được**: `trang_thai_ap = None`, `can_soat = True`, nhãn `NEEDS_REVIEW`, bị chặn cứng
khỏi trạng thái hoàn tất.

**Việc còn lại cho AG-00 (ngoài phạm vi ghi của G19):** nới đúng một dòng ở
`app/thu/thu_webhook_jt.py:1133` cho đa hãng (ví dụ `tth.BANG.get(ma_hang, {})`), rồi mới
chuyển `104` từ `CHUA_XAC_MINH` sang `NHAP_NHANG` — kèm hai nghĩa và ca thử riêng. Sổ nhập nhằng
là **chỗ đúng** cho `104` về mặt thiết kế; cái chặn chỉ là một dòng khẳng định của bộ thử.

---

## 6. ĐỐI CHIẾU VỚI D-4 (J&T `110`) — NGUYÊN TẮC «KHÔNG ĐOÁN MÃ» GIỮ NGUYÊN

| | J&T `110` (D-4) | VTP `104` | 12 mã VTP chưa xác minh |
|---|---|---|---|
| Đã đọc được nghĩa chưa | **Có, hai nghĩa** (bảng tham số vs ví dụ trả lời) | Có một phần; **mâu thuẫn ở vế «có phải cuối»** | **Không** |
| Sổ | `NHAP_NHANG` | `CHUA_XAC_MINH` (`mau_thuan_tai_lieu`) | `CHUA_XAC_MINH` |
| Nhãn | `AMBIGUOUS` | `NEEDS_REVIEW` | `NEEDS_REVIEW` |
| Đổi trạng thái đơn | Không | Không | Không |
| Chốt được về HOÀN TẤT | **Cấm cứng** | **Cấm cứng** | **Cấm cứng** |
| Nghĩa theo bảng (cho ĐỌC) | giữ `dang_giao` | — | — |

Nguyên tắc D-4 **không bị nới một ly nào cho VTP**: không có mã nào được đoán, không có nghĩa
nào được chốt sẵn (`NGHIA_DA_CHOT` vẫn rỗng), và **không mã VTP nào được phép đóng đơn**. Ca
`e1`–`e3` và `b5` khoá lại từng vế. G19 cũng **không** đụng quyết định D-9 (`city`/`area`).

---

## 7. NẰM NGOÀI PHẠM VI ĐÃ ĐO — nói rõ để không ai đọc quá lời

* **8 (hoặc 9) con số còn thiếu của bộ 21** — không có trong repo ⇒ không liệt kê được, không
  ánh xạ được. Đây vẫn là **lỗ hổng MỞ**, chỉ thu hẹp chứ chưa đóng.
* **Nghĩa THẬT của 13 mã** — chưa ai đối chiếu trang hãng. Cả bảng VTP đang ở mức nguồn **gián
  tiếp**; đó là lý do trần tin cậy là `trung_binh`, không phải `cao`.
* **`200` có thuộc bộ 21 hay không** — repo không nói (câu **B3**).
* **Hướng hoàn tất của VTP** — chưa xác minh, nên **không mã VTP nào đóng được đơn**. Ca `b5`
  canh điều này: nó đỏ nếu có mã VTP nào **không nằm trong sổ chưa xác minh** mà được gán vào
  `giao_thanh_cong` / `hoan_hang`.
* **`ORDER_STATUSDATE` theo múi giờ nào** (câu **B2**) — chưa trả lời; ảnh hưởng thứ tự sự kiện,
  không thuộc phạm vi G19.
* **Webhook VTP** — cửa vẫn `SO_DO_THEO_HANG["vtp"] = None` (chưa cài). G19 **không mở** nó.
* **Credentials · gọi hãng (kể cả sandbox) · `CHO_PHEP_LIVE` · PostgreSQL · deploy** — ngoài phạm
  vi, và theo chỉ thị thì **cấm**.

## 8. VIỆC NÊN LÀM TIẾP, theo thứ tự

1. **AG-00 nới một dòng** ở `app/thu/thu_webhook_jt.py:1133` rồi chuyển `104` sang `NHAP_NHANG`
   với hai nghĩa — P4b hoàn tất đúng thiết kế.
2. **Xin 8 con số còn thiếu** + nghĩa của chúng: câu **B3** và **B4** trong
   `docs/VTP_YEU_CAU_BO_SUNG.md`. Không có hai câu trả lời đó thì 8 mã kia mãi là «mã lạ».
3. **Đối chiếu trang hãng một lượt** (khi `V-G09-01` được cấp): đọc bảng 21 mã, lật
   `VTP_CO_NGUYEN_VAN_HANG = True`, và **hạ hoặc nâng trần tin cậy theo đúng thứ đọc được**.
4. Khi hướng hoàn tất được xác minh: thêm mã cuối của VTP vào bảng và **bỏ ca `b5`** — nhưng chỉ
   lúc đó, và phải kèm dẫn chứng từ hãng.
