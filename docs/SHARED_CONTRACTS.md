# SHARED CONTRACTS — khóa bởi AG-00, agent KHÔNG tự đổi

Agent nào thấy cần đổi contract thì **báo AG-00**, không tự sửa. File dùng chung (`app/server.py`,
`app/csdl.py`, `app/cau_hinh.py`, `app/don_hang.py`, `app/webhook.py`, `app/polling.py`) do AG-00 hợp nhất.

## 1. TenantContext / AuthenticatedPrincipal  (AG-01 sở hữu `app/bao_mat.py`)
```python
bao_mat.ngu_canh(token) -> NguCanh | None
NguCanh: .user_id .tenant_id .role .platform_role .tenant_ten .token .co_quyen(hanh_dong)
```
`tenant_id` CHỈ đến từ phiên đã xác thực — không bao giờ từ body/query. Giữ nguyên chữ ký này.

## 2. AuthorizationPolicy  (AG-01 sở hữu `app/quyen.py`)
```python
quyen.co_quyen(role_ma, hanh_dong) -> bool      # tra CSDL role_permissions
quyen.CAP_DUOC[role] -> tuple                    # vai trò được phép cấp
```

## 3. CredentialEncryption + SecretProvider  (AG-01)
```python
bao_mat.ma_hoa_cred(cred: dict, tenant_id, hang) -> (ban_ma: str, duoi: str)
bao_mat.giai_ma_cred(ban_ma, tenant_id, hang)    -> dict
bao_mat.ma_hoa_wh(secret, webhook_ma)            -> str
bao_mat.giai_ma_wh(ban_ma, webhook_ma)           -> str
```
**Bốn hàm này là contract.** AG-02/AG-04 chỉ được gọi, KHÔNG tự viết mã hóa.
AG-01 được thêm key_id/version và rotation NHƯNG phải giữ nguyên bốn chữ ký trên.

## 4. CarrierAdapter + CarrierCapabilities  (AG-02 sở hữu `app/adapter*.py`)
```python
CarrierAdapter: createOrder cancelOrder getOrder trackOrder getShippingFee getShippingLabel
                getCapabilities() -> dict          # AG-02 bổ sung
                normalizeTrackingStatus(ma) -> KetQuaAnhXa
lớp: ma_hang, ten_hang, CAPABILITIES, CHO_PHEP_LIVE, KHOA_CHONG_TRUNG
KetQuaHang(ok, ma_van_don, phi, loi, timeout, tho)
```
Ba kết cục KHÔNG gộp: ok / từ chối (ok=False,timeout=False) / không biết (timeout=True).
`CHO_PHEP_LIVE=False` là **khóa an toàn** — không agent nào được mở.

## 5. NormalizedCarrierError  (AG-02 thêm mới)
Chuẩn hóa lỗi hãng về một kiểu chung, tối thiểu: `ma_chuan`, `ma_goc_hang`, `thong_diep`,
`co_the_thu_lai: bool`. Order Service dựa vào `co_the_thu_lai` để quyết định.

## 6. ImportBatch / ImportRow  (AG-04 sở hữu `app/nhap_file.py`)
Trạng thái batch bắt buộc: `UPLOADED PARSING VALIDATING READY APPROVED PROCESSING COMPLETED
PARTIAL_FAILED FAILED`. Trạng thái dòng: `VALID INVALID READY SUBMITTED SUCCESS FAILED
UNSUPPORTED NEEDS_REVIEW`. Mọi batch gắn `tenant_id`; tenant A không đọc được batch tenant B.

## 7. OrderDraft  (AG-04 định nghĩa; AG-03 Orders KHÔNG chạy đợt này)
Import chỉ sinh **bản nháp**, không tạo đơn vận chuyển thật. Dùng lại `don_hang.tao_don(...)`
với `idem_key` để duyệt lại không nhân đôi.

## 8. AuditEvent  (AG-00 giữ)
```python
csdl.audit(hanh_dong, doi_tuong="<resource_type>:<id>", chi_tiet, tenant_id, user_id, dia_chi, ket_qua)
ket_qua ∈ {thanh_cong, tu_choi, that_bai}
```
Cấm ghi mật khẩu/token/secret vào audit và log.

## 9. Quy tắc chung
- Không agent nào sửa `gateway/` (đã nghiệm thu) trừ khi có lỗi thật, và phải báo AG-00.
- Không push remote, không deploy, không gọi API hãng thật, không mở `CHO_PHEP_LIVE`.
- Mọi test mới đặt trong file test RIÊNG của agent để không giẫm chân nhau.

---

# ĐÓNG BĂNG ĐỢT 2 — 15/10/2026 (AG-00 chốt, agent KHÔNG tự đổi)

Nền: `fd7c545`, schema v6, 184 test đạt. Hợp đồng dưới đây **đang được mã chạy dùng** — đổi phải
có đề xuất + đánh giá tương thích ngược + AG-00 duyệt + regression test.

## 10. OrderStatus — hợp đồng HIỆN TẠI (không phá)
Trạng thái nghiệp vụ trong `don_hang.trang_thai`: `nhap · da_duyet · dang_gui · da_gui · huy`.
Trạng thái GIAO VẬN tách riêng ở `don_hang.trang_thai_giao` (+ `hang_trang_thai_giao` để chặn
sự kiện đến muộn): `cho_lay(1) · lay_hang(2) · dang_giao(3) · giao_that_bai(4) ·
giao_thanh_cong(5) · hoan_hang(6)`.

**Hai trục này CỐ Ý tách nhau** — nghiệp vụ do người điều khiển, giao vận do hãng báo về.
Mở rộng state machine (VALIDATED/PENDING_APPROVAL/SUBMITTING/IN_TRANSIT…) phải **ánh xạ** vào hai
trục này, hoặc di cư có migration + giữ đọc được giá trị cũ. KHÔNG gộp hai trục làm một.

Bất biến phải giữ: chỉ vào `da_gui` khi hãng XÁC NHẬN; hãng timeout ⇒ giữ `dang_gui` +
`can_doi_soat_ket_qua=1`, tuyệt đối không coi là thành công.

## 11. OrderEvent / TrackingEvent
`don_lich_su(don_id, luc, nguon, noi_dung)` — `nguon` dạng `user:<id>` | `webhook:<sk_id>` |
`polling` | `he_thong`. Mọi thay đổi trạng thái PHẢI ghi một dòng ở đây.

## 12. WebhookEvent
`wh_su_kien(carrier_account_id, event_id, payload_tho, headers_json, nhan_luc, trang_thai,
so_lan_thu, loi_cuoi)` với `UNIQUE(carrier_account_id, event_id)` — chống trùng do **CSDL cưỡng
chế**, không bằng `if`. Trạng thái: `moi · dang_xu_ly · xong · cho_thu_lai · dlq · khong_khop`.
Tenant resolve từ `carrier_account`, **không bao giờ** từ payload.

## 13. IdempotencyRecord
Hiện cưỡng chế bằng `UNIQUE(tenant_id, idem_key)` trên `don_hang`. Thêm bảng riêng thì phải giữ
ràng buộc này hoặc thay bằng ràng buộc tương đương ở tầng CSDL — không chuyển sang kiểm bằng mã.

## 14. CredentialReference
Chỉ bốn hàm được phép chạm secret: `bao_mat.ma_hoa_cred / giai_ma_cred / ma_hoa_wh / giai_ma_wh`.
Bản mã mang `key_id` (`v3$<key_id>$<nonce>$<ct>`) để xoay khóa được. Cấm gọi `ma_hoa`/`giai_ma`
trần ngoài `migrate.py` — có ca canh `thu_tich_hop.test_02`.

## 15. Quyền sở hữu file đợt này
| Agent | SỞ HỮU | CẤM chạm |
|---|---|---|
| AG-01 SECURITY | `bao_mat.py`, `quyen.py`, `secret_provider.py`, `gioi_han.py`(mới), `thu_bao_mat.py`, `thu_gioi_han.py`(mới) | `don_hang.py`, `webhook.py`, `admin/` |
| AG-02 ORDERS | `don_hang.py`, `thu_don_hang.py`(mới) | `bao_mat.py`, `webhook.py`, `admin/` |
| AG-03 WEBHOOK | `webhook.py`, `trang_thai_hang.py`, `polling.py`, `thu_webhook.py`(mới) | `don_hang.py`, `bao_mat.py`, `admin/` |
| AG-04 FRONTEND | `admin/*`, `assets/*` | toàn bộ `app/*.py` |
| AG-05 QA | `thu_qa_*.py`, `docs/QA_*.md` | mọi mã sản phẩm |
| **AG-00** | `server.py`, `csdl.py`, `migrate.py`, `cau_hinh.py`, `khoi_tao.py`, `thu_tich_hop.py`, `thu_saas.py` | — |

**LUẬT KHÓA WORKTREE:** AG-00 **chỉ ĐỌC** worktree của agent khi họ đang chạy. Muốn sửa thì đợi
bàn giao rồi sửa trên nhánh tích hợp. (Lỗi đã xảy ra 14/10: AG-00 ghi vào worktree của AG-07.)

---

# ĐÓNG BĂNG ĐỢT 3 — 15/10/2026 (AG-00 chốt, agent KHÔNG tự đổi)

Nền: `31a321f`, schema **v7**, **563 phép kiểm đạt** (430 python + 56 node + 36 HTTP frontend
+ 41 E2E). Mọi hợp đồng ở trên **vẫn hiệu lực** — đợt này THÊM, không sửa.

## 16. TIỀN TỆ — luật cứng, không ngoại lệ

**Mọi số tiền là `INTEGER`, đơn vị ĐỒNG (VND), không có phần thập phân.**

- **CẤM `REAL`/`FLOAT`/`DOUBLE` cho tiền** ở mọi bảng, mọi biến, mọi JSON. `0.1 + 0.2 != 0.3`
  — một đồng lệch trong đối soát là một lần phải ngồi tìm cả buổi.
- VND không có đơn vị nhỏ hơn đồng đang lưu hành, nên **không cần nhân 100**. `cod INTEGER` là
  số đồng, đọc thẳng. Mã hiện tại đã làm đúng vậy (`don_hang.cod`, `phi_van_chuyen`,
  `don_mat_hang.don_gia`) — **giữ nguyên cách đó**, đừng đổi sang đơn vị khác giữa đường.
- Tỷ lệ / phần trăm: lưu **điểm cơ bản** (`INTEGER`, 1 = 0,01 %), không lưu `0.0825`.
- Chia tiền: dùng `//` và ghi rõ phần dư đi đâu. **Không bao giờ để phần dư biến mất** — tổng
  các phần phải bằng đúng số ban đầu, và phải có ca thử canh điều đó.
- Nếu một agent thấy **cần** số thập phân, đó là dấu hiệu đơn vị chọn sai: **bàn giao AG-00**,
  không tự đổi kiểu cột.

## 17. FinancialEntry — bút toán BẤT BIẾN (AG-01 sở hữu)

```
FinancialEntry: id · tenant_id · loai · don_id? · carrier_account_id? · so_tien_dong (INTEGER)
                · chieu (ghi_no|ghi_co) · nguon (hang|nguoi|he_thong) · can_cu
                · tao_boi · tao_luc · batch_id?
```

- **Bút toán KHÔNG được sửa, KHÔNG được xoá.** Sai thì ghi bút toán ĐẢO, không `UPDATE`.
  Đây là chỗ §19 (luật thùng rác) và "không silent overwrite" gặp nhau: lịch sử tiền phải dựng
  lại được từ đầu, nên một dòng đã ghi là một dòng ở đó mãi.
- Mọi bút toán phải trả lời được **ai · lúc nào · căn cứ gì**. `nguon` phân biệt rõ số do
  **hãng** báo, số do **người** chốt, số do **hệ thống** suy ra — ba thứ có độ tin cậy khác nhau
  và **cấm trộn vào một cột**.

## 18. CodState — sáu trạng thái COD, KHÔNG gộp

```
COD_EXPECTED · COD_COLLECTED · COD_RECONCILED · COD_SETTLED · COD_DISPUTED · COD_ADJUSTED
```

**Luật quan trọng nhất của G07: `trang_thai_giao = 'giao_thanh_cong'` KHÔNG có nghĩa là tiền
COD đã về.** Giao hàng và thu tiền là hai sự kiện khác nhau, cách nhau nhiều ngày, do hai bên
khác nhau xác nhận. Đơn giao xong mà hãng chưa đối soát thì COD vẫn là `COD_COLLECTED` (hãng
đang giữ tiền), chưa phải `COD_SETTLED`. Gộp hai thứ này là cách nhanh nhất để báo doanh thu
không có thật.

Chuyển trạng thái phải qua MỘT hàm duy nhất, có bảng chuyển hợp lệ, và ghi `FinancialEntry`.

## 19. SubscriptionPlan — KHÔNG đổi tên ba gói đang chạy (AG-02 sở hữu)

CSDL đang có **đúng ba gói**: `free` (Miễn phí) · `basic` (Cơ bản) · `pro` (Chuyên nghiệp),
và `tenants.goi_id` đang trỏ vào đó. Chỉ thị đợt này đề xuất tên `FREE/STARTER/BUSINESS/
ENTERPRISE` — đó là **tên kỹ thuật đề xuất, không phải lệnh đổi tên**.

- **CẤM đổi hay xoá ba mã `free`/`basic`/`pro`.** Đổi là phá mọi tenant đang chạy và phá
  `thu_saas.py`. Muốn thêm gói thì **THÊM dòng mới**, giữ ba dòng cũ.
- `goi_dich_vu` hiện có 5 cột hạn mức (`han_muc_don_thang`, `han_muc_ai_thang`, `so_nhan_vien`,
  `so_tai_khoan_hang`, `gia_thang`). Thêm hạn mức thì **thêm cột `DEFAULT`**, không đổi cột cũ.
- **Giá bán thực tế do anh Thành quyết.** Agent được điền giá cho gói MỚI chỉ khi gói đó chưa
  bán cho ai; gói đang chạy thì giữ nguyên giá.

## 20. UsageEvent — mỗi lượt tính phí phải có khoá chống trùng (AG-02 sở hữu)

```
UsageEvent: id · tenant_id · loai · so_luong (INTEGER) · idem_key (UNIQUE cùng tenant_id)
            · nguon · tao_luc · tham_chieu?
```

- **`UNIQUE(tenant_id, idem_key)` là ràng buộc CSDL, không phải phép kiểm trong mã.** Worker
  thử lại là chuyện bình thường; thu phí hai lần thì không. Chặn ở tầng CSDL thì không có khe
  hở nào giữa đọc và ghi.
- Bộ đếm cộng bằng **một `UPDATE` có trần trong `WHERE`**, xét `rowcount` — đúng khuôn
  `gioi_han._cong_co_tran` và `billing.kiem_va_tang_don` (đã vá đợt 2 vì đọc-rồi-ghi để lọt
  5/8 luồng). **Cấm đọc rồi mới ghi.**
- `billing.kiem_va_tang_don` và `billing.hoan_don` **đang được `don_hang.gui_don` dùng** — đổi
  chữ ký phải bàn giao AG-00.

## 21. AIJob — hợp đồng công việc AI (AG-04 sở hữu)

```
AIJob: id · tenant_id · user_id · loai · trang_thai (moi|dang_chay|xong|loi|cho_duyet|tu_choi)
       · vao_json · ra_json? · nha_cung_cap · phien_ban_hop_dong · do_tin_cay?
       · can_nguoi_duyet (0|1) · duyet_boi? · duyet_luc? · idem_key · tao_luc · xong_luc?
```

- **`tenant_id` lấy từ PHIÊN đã xác thực, KHÔNG từ body.** Đây là luật đã có từ G01, áp nguyên
  vào đây. Một AIJob không có `tenant_id` là một AIJob không được chạy.
- **Kết quả AI là DỮ LIỆU, không phải LỆNH.** Không có đường nào cho `ra_json` quyết định quyền,
  gọi hãng, hay đổi trạng thái đơn. Nó chỉ được đề xuất; người duyệt mới là người quyết.
- `ra_json` phải qua **phép kiểm schema** trước khi lưu. Kết quả không khớp schema là `loi`,
  không phải `xong` với dữ liệu méo.
- **Cấm đưa bí mật vào prompt** (credentials hãng, khoá, token, mật khẩu). Có ca thử canh.
- `MOCK` trong `app/ai_gateway.py` hiện là `True`. **Không ai được đặt `False`** trong đợt này —
  nối thật là **V-G10-01, CHƯA được cấp quyền**.

## 22. Quyền sở hữu file — ĐỢT 3

| Agent | SỞ HỮU (được ghi) | CHỈ ĐỌC |
|---|---|---|
| **AG-01 FINANCE** | `app/tai_chinh.py` · `app/doi_soat.py` · `app/thu/thu_tai_chinh.py` · `app/thu/thu_doi_soat.py` · `admin/finance.js` · `docs/G07_*.md` | mọi thứ khác |
| **AG-02 BILLING** | `app/goi_dich_vu.py` · `app/usage.py` · `app/thu/thu_goi_dich_vu.py` · `app/thu/thu_usage.py` · `admin/billing.js` · `docs/G08_*.md` | mọi thứ khác |
| **AG-03 CARRIER** | `app/harness_hang.py` · `app/thu/thu_harness_hang.py` · `docs/G09_*.md` · `docs/JT_*.md` · `docs/VTP_*.md` | mọi thứ khác (gồm `adapter*.py` — ĐỌC để khảo sát, **không sửa**) |
| **AG-04 AI** | `app/ai_job.py` · `app/ai_validator.py` · `app/thu/thu_ai_job.py` · `admin/ai.js` · `docs/G10_*.md` | mọi thứ khác (gồm `ai_gateway.py` — bàn giao AG-00 nếu cần sửa) |
| **AG-05 DEVOPS** | `Dockerfile` · `docker-compose.yml` · `.env.example` · `trien_khai/` (thư mục MỚI) · `app/quan_sat.py` · `app/thu/thu_quan_sat.py` · `docs/G11_*.md` | mọi thứ khác |
| **AG-00** | `app/csdl.py` · `app/migrate.py` · `app/server.py` · `app/cau_hinh.py` · `app/billing.py` · `app/ai_gateway.py` · `docs/SHARED_CONTRACTS.md` · `.gitignore` · mọi file của agent SAU KHI agent đó bàn giao | — |

**Không agent nào được ghi vào `app/csdl.py`, `app/migrate.py`, `app/server.py`.** Cần schema
mới thì khai **hằng `DDL_G0x`** trong module của chính mình; AG-00 viết migration v8. Cần route
mới thì khai bảng route trong tài liệu của mình; AG-00 cắm.

## 23. WORKTREE OWNERSHIP LOCK — giữ nguyên từ đợt 2

AG-00 **KHÔNG ghi file vào worktree mà agent đang dùng**, kể cả để sửa một lỗi nhỏ, kể cả khi
nghĩ rằng mình đang giúp. Lỗi này đã xảy ra thật ở đợt 1 (AG-00 chép `thu_saas.py` vào worktree
AG-07 đang chạy, AG-07 phát hiện và báo). Cần sửa thì **nói với agent**; agent đã kết thúc thì
làn coi như đã nhả và AG-00 mới được vào.

## 24. CSDL thử của từng agent — KHÔNG ai chạy migration lên CSDL thật

Mỗi worktree đặt `VIP_HUB_DATA` trỏ vào thư mục riêng của nó. **Cấm chạy `migrate.py` lên
`~/Projects/vip-express-hub/app/du-lieu/`** — đó là CSDL đang giữ dữ liệu thật của các đợt
trước. AG-00 là người duy nhất chạy migration lên đó, sau khi đã thử trên bản sao.

## 25. Những điều CHƯA được cấp quyền — cấm tự suy diễn

| Mã | Việc | Trạng thái |
|---|---|---|
| V-13906-01 | Thư viện ngoài để tự động hoá kiểm giao diện tầng 3 | **ĐÃ CẤP 14/10/2026** — quyết định D-1, anh Thành: "Đồng ý Playwright, cài riêng trong dự án". Cài tại `node_modules/` của repo, trình duyệt ở `playwright-core/.local-browsers/` (KHÔNG dùng cache hệ thống — cache đó có bản của dự án khác). |
| V-13906-02 | Xoay khoá mã hoá thật | **CHƯA CẤP** |
| V-13906-03 | Sao lưu bí mật ra ngoài máy (VIP Vault) | **CHƯA CẤP** |
| V-13906-04 | Nghĩa của mã J&T `110` | **CHƯA CẤP** |
| V-13906-05 | Credentials sandbox J&T | **CHƯA CẤP** |
| V-G09-01 | Gọi API hãng thật (sandbox hoặc live) | **CHƯA CẤP** |
| V-G10-01 | Nối VIP AI Brain thật | **CHƯA CẤP** |
| V-G11-01 | Triển khai staging lên VPS | **CHƯA CẤP** |

**Giao G09 không có nghĩa là được gọi hãng. Giao G10 không có nghĩa là được nối AI thật. Giao
G11 không có nghĩa là được deploy.** Việc nào chạm vào tám dòng trên thì dừng, ghi **BLOCKED**
kèm chính xác cái còn thiếu, rồi làm tiếp phần mock/local.

---

# ĐÓNG BĂNG G12 — 15/10/2026 (AG-00 chốt theo 9 quyết định của anh Thành)

Nền: `9af8115`, schema **v8**, **927 phép kiểm đạt**. Mọi hợp đồng ở trên **vẫn hiệu lực**.

## 26. CHÍN QUYẾT ĐỊNH — trạng thái sau khi anh Thành chốt 15/10

| Mã | Quyết định của anh | Hệ quả cho G12 |
|---|---|---|
| **D-1** | **Đồng ý Playwright**, cài riêng trong dự án | **MỞ** — AG-02 làm. Cài vào `node_modules` của chính dự án, KHÔNG cài toàn cục |
| **D-2** | Đồng ý xoay khoá, **nhưng khoá bằng quyền quản trị đặc biệt và kiểm thử trên bản sao trước** | **MỞ CÓ ĐIỀU KIỆN** — AG-05. Chưa xoay khoá thật lượt nào |
| **D-3** | Đồng ý sao lưu khoá ra VIP Vault **có điều kiện**: mã hoá độc lập · kiểm quyền · diễn tập khôi phục | **MỞ CÓ ĐIỀU KIỆN** — AG-05 dựng cơ chế + diễn tập. **Lượt ghi THẬT đầu tiên ra VIP Vault phải hỏi anh** |
| **D-4** | Chờ J&T xác nhận; tiếp tục đánh dấu cần rà soát | **GIỮ NGUYÊN** — không thêm mã nào vào bảng ánh xạ |
| **D-5** | Chưa cấp credentials; **chuẩn bị tài liệu đăng ký và kiểm thử** | **MỞ phần tài liệu** — AG-03 |
| **D-6** | **Giữ cấu hình giá chưa phát hành, không tự đặt giá** | **KHOÁ** — không agent nào điền giá |
| **D-7** | **Đồng ý, làm ngay** | **XONG 15/10** — 3 quyền `tenant.taichinh.*`, đo qua HTTP |
| **D-8** | Tiếp tục SQLite local; **thử PostgreSQL trước khi quyết định** | **MỞ phần THỬ** — AG-04. **KHÔNG chuyển CSDL thật** |
| **D-9** | **Chưa chốt cách ánh xạ `area`** cho tới khi hãng xác nhận | **KHOÁ** — AG-03 phải biến giả định hiện tại thành **chốt chặn cứng**, không để nó im lặng thành dữ kiện |

## 27. Môi trường ĐÃ ĐO trên máy này (15/10, MacBook)

| Công cụ | Có? | Ghi chú |
|---|---|---|
| **PostgreSQL 16.15** | **CÓ** (Homebrew) | Cụm hệ thống đang chạy `:5432` và **đang giữ CSDL của dự án khác** (`vip_customs`, `vip_customs_g16`, `vip_customs_test`) — **CẤM đụng**. Cụm thử phải là **cụm riêng**: `initdb --locale=C`, cổng riêng, **socket ở đường NGẮN** (`mktemp -d /tmp/vhpg.XXXX`) vì đường scratchpad dài quá 103 byte |
| **node v26.7.0 · npm 11.19.0** | **CÓ** | Playwright cài được |
| **Docker / podman / colima** | **KHÔNG CÓ** | `brew` có sẵn nên cài được, **nhưng cài là đổi máy của anh ⇒ phải hỏi**. Chưa hỏi thì Docker build = **BLOCKED**, và **CẤM báo "Docker build PASS"** |

## 28. Quyền sở hữu file — G12

| Agent | SỞ HỮU | CHỈ ĐỌC |
|---|---|---|
| **AG-01 BACKEND QUERY** | `app/truy_van.py` · `app/thu/thu_truy_van.py` · `docs/G12_QUERY.md` | mọi thứ khác |
| **AG-02 UI TESTING** | `thu_giao_dien/` (thư mục MỚI) · `package.json` · `package-lock.json` · `playwright.config.js` · `docs/G12_PLAYWRIGHT.md` | mọi thứ khác |
| **AG-03 CARRIER** | `docs/G12_VTP_KHAO_SAT.md` · `docs/G12_JT_DANG_KY.md` · `app/thu/thu_anh_xa_area.py` | mọi thứ khác |
| **AG-04 DATA PLATFORM** | `trien_khai/postgres/` (MỚI) · `app/thu/thu_postgres.py` · `docs/G12_POSTGRES.md` · `docs/G12_DOCKER.md` | mọi thứ khác (gồm `Dockerfile`, `docker-compose.yml` — **đọc**, bản vá đề xuất) |
| **AG-05 SECURITY** | `app/xoay_khoa.py` · `app/thu/thu_xoay_khoa.py` · `trien_khai/sao_luu_ngoai/` (MỚI) · `docs/G12_KEY_OPS.md` · `docs/G12_STAGING_MATRIX.md` | mọi thứ khác |
| **AG-00** | `app/csdl.py` · `migrate.py` · `server.py` · `cau_hinh.py` · `billing.py` · `quyen.py` · `ai_gateway.py` · `adapter*.py` · `SHARED_CONTRACTS.md` · `.gitignore` | — |

Luật §22–§24 giữ nguyên: không agent nào ghi `csdl.py`/`migrate.py`/`server.py`; khai hằng
`DDL_G12x` và bảng route; mỗi worktree một CSDL thử riêng qua `VIP_HUB_DATA`.

## 29. Luật riêng của G12

- **CẤM cài gì ở mức TOÀN CỤC.** Playwright vào `node_modules` của dự án. PostgreSQL dùng bản
  đã có. Docker thì **hỏi trước**, không `brew install` tự ý.
- **CẤM đụng cụm PostgreSQL `:5432`** — nó giữ dữ liệu dự án khác. Cụm thử phải tự dựng, tự
  dừng, tự xoá.
- **CẤM ghi đè bản clone `~/code/vip-viettelpost`** (đang ở `4df8ce7`, nhánh
  `feature/shp-database`, sạch). Khảo sát bằng **bản clone MỚI riêng** hoặc `gh api`.
- **CẤM xoay khoá thật.** D-2 cho phép *xây* chức năng + *thử trên bản sao*; lượt xoay thật
  trên khoá đang dùng vẫn cần anh duyệt riêng.
- **CẤM ghi thật ra VIP Vault.** D-3 cho phép dựng cơ chế + diễn tập cục bộ; lượt ghi thật
  đầu tiên phải hỏi anh.
- **CẤM điền giá** cho bất kỳ gói nào (D-6).
- **CẤM tự tuyên bố production-ready.**

## 30. Ranh giới giao dịch — luật sau đợt G12 mục 5 (15/10/2026)

Đổi cấu trúc, không phải thêm lời dặn. Ba điều dưới đây là **bắt buộc**, mỗi điều sinh ra
từ một lỗi đo được thật, và mỗi điều có chốt chặn trong bộ thử.

**30.1 — Chỉ `csdl.py` được `import sqlite3`.** Mã nghiệp vụ dùng `csdl.Row`,
`csdl.LoiCSDL`, `csdl.LoiToanVen`, `csdl.LoiVanHanh`, `csdl.ket_noi()`.
Chốt chặn: `app/thu/thu_bien_driver.py` ca a1 (dò bằng AST, không grep).

**30.2 — Nhiều câu ghi phải thành MỘT đơn vị thì bọc `csdl.giao_dich()`.**
`with csdl.khoa_ghi:` KHÔNG phải giao dịch — nó chỉ chặn hai thread giẫm nhau. Lỗi đã dính:
`ghi_but_toan` có docstring ghi "cùng một transaction" mà ép bước hai hỏng thì bút toán
777.000đ vào sổ còn công nợ đứng yên; `ghi_nhan_thanh_toan` để lại dòng thanh toán 90.000đ
mồ côi và KẸT VĨNH VIỄN vì UNIQUE chặn làm lại.
Chốt chặn: `app/thu/thu_giao_dich.py` ca c1, c2.

**30.3 — CẤM `kn.commit()` / `kn.rollback()` trên kết nối của `csdl.mo()`.**
Kết nối ấy ở chế độ tường minh (`isolation_level=None`) nên hai lệnh đó là **LỆNH RỖNG** —
rỗng mà không báo lỗi, nên mã trông như có đường hoàn tác. Lỗi đã dính:
`usage.ghi_su_kien` gọi `kn.rollback()` để bỏ sự kiện khi vượt trần → sự kiện mồ côi → lần
thử lại cùng `idem_key` bị coi là trùng rồi lặng lẽ không thu gì (mất tiền một chiều).
Muốn gộp thì `giao_dich()`; muốn bỏ một câu đã ghi thì XOÁ theo id.
Chốt chặn: `app/thu/thu_bien_driver.py` ca a5. Miễn trừ: `csdl.py`, `migrate.py`.

**30.4 — Điều phải biết về SQLite, đã đo, đừng suy lại:**

| Điều | Đo được |
|---|---|
| `RAISE(ABORT)` của trigger | huỷ **CÂU**, KHÔNG huỷ giao dịch — câu sau vẫn commit. PostgreSQL thì `RAISE EXCEPTION` huỷ cả giao dịch |
| `executescript()` | **tự COMMIT** giao dịch đang mở, lặng lẽ. Dùng `migrate.chay_ddl_trong_giao_dich()` |
| `with kn:` của python | mở giao dịch cho DML, **KHÔNG** cho `CREATE`/`ALTER` |
| `BEGIN IMMEDIATE` | nổ nếu python đã tự mở giao dịch; dùng được khi `isolation_level=None` |
| `SAVEPOINT` trần | mở giao dịch **HOÃN** — đọc-rồi-ghi qua nhiều tiến trình nhận `SQLITE_BUSY_SNAPSHOT` NGAY, `busy_timeout` không chờ |
| `PRAGMA foreign_keys` | **bị bỏ qua** nếu đặt trong giao dịch, không báo lỗi |
| `PRAGMA journal_mode=WAL` | cần khoá độc quyền; `busy_timeout` **không** phủ nó |

**30.5 — Phép đo đồng thời (chỉ thị G12 mục 11):**
`app/thu/dong_thoi/chay.py`, mặc định **8 tiến trình hệ điều hành thật × 400 phép**.
Phân biệt bốn kết cục: `CHOT_THANH_CONG` · `TU_CHOI_NGHIEP_VU` · `KHOA_HET_GIO` ·
`GIAO_DICH_HONG`, cộng `MAT_CAP_NHAT` chỉ phát hiện được bằng đối chiếu cuối lượt.
Đo bằng **tiến trình**, không bằng thread: `khoa_ghi` là RLock của Python, chỉ phủ MỘT tiến
trình — đo bằng thread là đo chính cái khoá đó rồi kết luận "an toàn" cho ca nó không phủ.

---

# ĐÓNG BĂNG G13–G15 — 15/10/2026 (AG-00 DeepSeek chốt, agent KHÔNG tự đổi)

Nền: `de740dc` (cây sạch, 0 stash, ở cả `main` lẫn worktree Orca). Mọi hợp đồng **§1–§30 vẫn
hiệu lực nguyên vẹn** — đợt này chỉ THÊM. Baseline AG-00 tự đo lại trước khi giao việc:
**927 ca python · 29 bộ · 0 hỏng · 0 bỏ qua** + **56 + 36 ca frontend** + **E2E 41/41** +
**tầng 3 Chromium 26 đạt · 1 bỏ qua** (mã thoát 0 cả bốn lượt).

## 31. Quyền sở hữu file — G13–G15

Bốn làn chạy **đồng thời trong CÙNG một cây làm việc** (không tách worktree được — xem §33).
Vì vậy quyền sở hữu dưới đây là **ranh giới cứng**, không phải gợi ý.

| Làn | SỞ HỮU (được ghi) | CẤM chạm |
|---|---|---|
| **AG-01 QA/VERIFIER** | `docs/QA_G13_G15.md` (mới) · `app/thu/thu_qa_jt.py` (mới) | **mọi mã sản phẩm** (chỉ đọc) |
| **AG-02 J&T API** | `app/adapter_jt.py` · `app/thu/thu_adapter_jt.py` (mới) · `app/thu/thu_hop_dong_jt.py` (mới) · `docs/G13_*.md` (mới) | `webhook.py`, `csdl.py`, `migrate.py`, `server.py`, `adapter.py` (lớp nền — đề xuất, không sửa) |
| **AG-03 WEBHOOK** | `app/webhook.py` · `app/trang_thai_hang.py` · `app/thu/thu_webhook_jt.py` (mới) · `docs/G14_*.md` (mới) · `docs/JT_*.md` | `adapter_jt.py`, `csdl.py`, `migrate.py`, `server.py`, **`gateway/`** (đã nghiệm thu — báo AG-00 nếu thấy lỗi thật) |
| **AG-04 INFRA** | `trien_khai/` · `app/thu/thu_postgres.py` · `docs/G15_*.md` (mới) · `docs/G12_*.md` | `csdl.py`, `migrate.py`, `server.py`, `adapter_jt.py`, `webhook.py` |
| **AG-00** | `csdl.py` · `migrate.py` · `server.py` · `cau_hinh.py` · `billing.py` · `quyen.py` · `ai_gateway.py` · `adapter.py` · `SHARED_CONTRACTS.md` · `.gitignore` · **mọi file của agent SAU KHI bàn giao** | — |

Không agent nào được mở `CHO_PHEP_LIVE`. Không agent nào được ghi `csdl.py`/`migrate.py`/`server.py`.

## 32. Trạng thái J&T — điều ĐÃ XÁC MINH được, và điều CÒN THIẾU

**Đã có trong mã (đọc lại trên `de740dc`, không phải nghe báo cáo):**
`adapter_jt.py` đã dựng theo tài liệu công khai: chữ ký `base64(md5-bytes(bizContent + privateKey))`,
header `apiAccount` · `digest` · `timestamp` (ms, UTC+7), body `application/x-www-form-urlencoded`
một trường `bizContent`. **COD đã nằm đúng `codMoney`** (số nguyên đồng, §16) — lỗi dùng
`itemsValue` đã được vá trước đợt này. Chốt chặn **D-9** cho `area` là **chặn cứng** (16 ca canh).
`CAPABILITIES` có `webhook: True` theo trang `logistics/statusFeedback`.

**Điều CÒN THIẾU — đã đo, không suy đoán:**

| Thiếu gì | Bằng chứng đo được |
|---|---|
| **Credentials J&T** | **Không có tệp `.env` nào** trong cây làm việc. `.env.example` **không khai một khoá J&T nào** — bề mặt cấu hình cho credentials J&T **chưa tồn tại**, không chỉ thiếu giá trị |
| **Nghĩa mã trạng thái `110`** | `V-13906-04` CHƯA CẤP ⇒ mọi mã chưa xác minh phải ra `NEEDS_REVIEW`, cấm `DELIVERED`, cấm kích hoạt đối soát COD |
| **Cách ánh xạ `area`** | Quyết định **D-9 KHOÁ**. Ví dụ của chính hãng đặt QUẬN vào `city` và PHƯỜNG vào `area` — ngược ánh xạ đang dùng. Giữ nguyên chốt chặn |
| **Phạm vi sandbox** | `V-G09-01` CHƯA CẤP ⇒ **không gọi API hãng thật**, kể cả sandbox. G13 **không được** báo "LIVE VERIFIED" đợt này |

## 33. HAI lỗi hạ tầng AG-00 đo được trước khi giao việc

**33.1 — Biến môi trường `GIT_CONFIG_*` làm MỌI lệnh git hỏng (exit 128).**
Harness đặt `GIT_CONFIG_COUNT=2` cùng `GIT_CONFIG_VALUE_0/_1` nhưng **thiếu** `GIT_CONFIG_KEY_0/_1`,
nên git chết với `fatal: unable to parse command-line config` / `missing config key GIT_CONFIG_KEY_0`.
Hệ quả đo được: `thu_bao_mat.py::test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git` **HỎNG**
(57 ca, 1 hỏng) vì nó gọi `git check-ignore`. **Đây là lỗi MÔI TRƯỜNG, không phải lỗi mã.**
Bỏ ba biến đó đi thì bộ thử **57/57 ĐẠT, mã thoát 0**.

> **AG-01 đính chính bán kính ảnh hưởng: **HAI** bộ thử, không phải một.** AG-00 chỉ kể
> `thu_bao_mat.py`. Bộ thứ hai là `thu_tich_hop.py::test_04_khoa_ma_hoa_khong_duoc_vao_git`
> (git hỏng: thoát 1, 1 ca hỏng · git lành: thoát 0, OK). AG-01 tìm ra bằng cách chạy **cả 29 bộ**
> với git hỏng: đúng hai bộ đó gọi git, không bộ nào khác.
>
> **Vì sao AG-00 bỏ sót — và đây là chỗ đáng nhớ nhất:** `thu_tich_hop.py` xếp **SAU**
> `thu_bao_mat.py` theo thứ tự chữ cái, nên **Finding B (§33.2) giết bộ chạy trước khi nó tới
> lượt**. Một bộ chạy chết lặng không chỉ giấu lỗi — **nó giấu luôn phát hiện của chính người
> đang đi tìm lỗi.** Đây là lý do §33.2 phải vá trước mọi việc khác.
>
> **Hai bộ này KHÔNG được "sửa".** Chúng canh một bất biến thật (khoá mã hoá không lọt vào git);
> git hỏng thì git thật sự không trả lời được câu hỏi đó. Sửa ở đây là làm hỏng chốt chặn. Cách chạy đúng từ nay:
```bash
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
```
Hệ quả thứ hai: **mọi lượt ghi git đều bị sandbox chặn** (`git branch` → *cannot lock ref:
Operation not permitted*), nên không tách được worktree cho từng làn.

**33.2 — `app/thu/chay_tat_ca.sh` chết LẶNG khi có bộ thử hỏng.**
Script có `set -e` (dòng 8) rồi tới `OUT=$(python3 "$t" 2>&1); MA=$?` (dòng 22). Dưới `set -e`,
**một bộ thử thoát khác 0 làm CHẾT CẢ SCRIPT ngay lập tức** — trước khi in bảng tổng kết. Đo được:
lượt chạy đầu chỉ in **3 dòng** (2 bộ đầu) rồi thoát 1, **không một dòng báo hỏng nào**. Đây đúng
**cùng một khuôn** với ba cái bẫy ở `docs/BAN_GIAO.md` §7.1: thứ dùng để kiểm chứng tự nó nói sai.
Nguy hiểm thật: một hồi quy thật có thể bị đọc thành *"chạy có 2 bộ, chắc ổn"*. **Phải vá** để mọi
bộ đều được chạy và đều được báo.

**BẢN VÁ ĐÚNG** (AG-01 đo và kiểm chứng; AG-00 chốt sau khi bản đầu của chính AG-00 bị AG-01 bác):
```sh
    MA=0
    OUT=$(python3 "$t" 2>&1) || MA=$?
```

> **§33.2 bản đầu đã SAI — ghi lại để không ai lặp.** AG-00 viết
> `if ! OUT=$(python3 "$t" 2>&1); then MA=$?; fi`. Toán tử `!` **đảo mã thoát**, nên `$?` trong
> nhánh `then` **luôn bằng 0**. Hệ quả: lý do hỏng bị nói SAI (`thoát 0` cho một bộ thoát 1), và
> tiêu chí **mã thoát bị xoá sạch** — phán quyết quay về đúng cái khuôn *phán bằng chữ trong
> output* đã gây **hai lần báo hỏng giả** mà `BAN_GIAO.md` §7.1 dựng ra để từ bỏ. Một bản vá
> *trông như* đang vá đúng chỗ nguy hiểm nhất.
>
> **AG-01 phát hiện (`N-01`, mức HIGH).** Đây là lý do tồn tại của một làn kiểm thử độc lập:
> AG-00 vừa đóng băng một bản vá sai vào chính tài liệu hợp đồng. Bài học giữ nguyên: **hợp đồng
> đóng băng không miễn nhiễm với lỗi, và người viết không tự soát được mình.**

## 34. Luật riêng của đợt G13–G15

- **Không gọi API hãng thật**, kể cả sandbox — `V-G09-01` chưa cấp. Mọi làn chạy ở **MOCK**.
- **Không mở cổng ra Internet**, không tunnel, không deploy VPS/staging — `V-G11-01` chưa cấp.
- **Không cài gì ở mức toàn cục.** Docker/colima **KHÔNG CÓ** trên máy này; cài là đổi máy của
  anh ⇒ **Docker = BLOCKED**, và **CẤM báo "Docker build PASS"**.
- **CẤM đụng cụm PostgreSQL `:5432`** — nó đang giữ `vip_customs`, `vip_customs_g16`,
  `vip_customs_test` của **dự án khác**. Thử PostgreSQL phải là **cụm riêng**, cổng riêng,
  socket ở đường ngắn (`mktemp -d /tmp/vhpg.XXXX`, giới hạn 103 byte).
- **KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL.** Kho nghiệp vụ vẫn là **SQLite** (D-8).
- **Không tự tuyên bố production-ready.**
- Mỗi làn dùng `VIP_HUB_DATA` **riêng** (`/tmp/veh_data_ag0x`) khi chạy thử, vì bốn làn dùng
  chung một cây làm việc.

## 35. Mốc bảo vệ — ghi lại trước khi sửa, để cuối lượt đối chiếu

| Đối tượng | Dấu vân tay lúc bắt đầu |
|---|---|
| CSDL THẬT `~/Projects/vip-express-hub/app/du-lieu/hub.db` | `200.704` byte · sha256 `aaf71362f86f7391f9394f77a5c8a3b24c81e7e1b6ca49da116143eb556d0c54` |
| Cây làm việc Orca | sạch, 0 tệp dở, 0 stash |
| HEAD | `de740dc` — `41ed553` là **tổ tiên** (12 commit), KHÔNG reset về nó |
| Bản sao lưu mã nguồn | `/tmp/veh_backup_de740dc/workspace_src.tgz` (1,0 MB) |
