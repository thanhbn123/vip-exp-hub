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

---

# ĐÓNG BĂNG G16 — 15/10/2026 (AG-00 DeepSeek chốt, agent KHÔNG tự đổi)

**Nền: `integration/g13-g15` @ `449bb2d`.** Mọi hợp đồng **§1–§35 vẫn hiệu lực nguyên vẹn**.

> **XÁC MINH BẮT BUỘC ĐÃ LÀM — `main` KHÔNG chứa G13–G15.** Đo được: `main` = `de740dc`,
> `integration/g13-g15` = `449bb2d`, và `git merge-base --is-ancestor integration/g13-g15 main`
> **THẤT BẠI** ⇒ **CHƯA merge**. Mọi việc G16 làm **trên nền `integration/g13-g15`**, KHÔNG trên
> `main`. Ai đọc lịch sử `main` sẽ **không thấy** G13–G15 ở đó.

## 36. HỢP ĐỒNG LỚP HTTP — chốt TRƯỚC khi giao việc

`app/transport.py` **đã có** chính sách (số lần thử, backoff, hết giờ, `duoc_thu_lai`) và bộ chạy
`goi()`. **Thiếu đúng một thứ: hàm HTTP thật để `goi()` gọi.** G16 lấp chỗ đó.

```python
# app/http_jt.py  — AG-02 sở hữu
MOCK = "mock"; SANDBOX = "sandbox"; PRODUCTION = "production"

class TraLoiHTTP:            # kết quả MỘT lượt gửi
    ma_http: int             # mã HTTP; 0 nếu không có phản hồi
    than: bytes              # thân thô, nguyên văn
    headers: dict

def gui_form(url, headers, body: dict, *, timeout: float) -> TraLoiHTTP
    """Gửi MỘT lượt POST `application/x-www-form-urlencoded`.
    Ném `transport.LoiTamThoi`  khi ĐÁNG thử lại (mạng, hết giờ, 5xx).
    Ném `transport.LoiVinhVien` khi thử lại VÔ ÍCH (4xx, URL sai, chữ ký sai).
    KHÔNG tự thử lại — việc thử lại thuộc `transport.goi()`."""
```

**Ba luật cứng của lớp này:**

1. **Thao tác GHI không được tự thử lại.** `createOrder`/`cancelOrder` chỉ thử lại qua
   `transport.chinh_sach_cho(..., co_khoa_chong_trung=True)`, và chỉ vì J&T có `txlogisticId`
   chống trùng. `http_jt` **không** được tự retry — nó chỉ ném đúng loại lỗi.
2. **Danh sách TRẮNG máy chủ.** Chỉ nhận host trong `DUONG_API` (sandbox/production của J&T)
   **hoặc** `127.0.0.1`/`localhost` (để bộ thử dựng stub cục bộ). Host khác ⇒ **TỪ CHỐI**.
   Đây là chốt chặn để một URL gõ sai không biến thành một lượt gọi ra ngoài.
3. **Ba kết cục không gộp** (§4): `ok` / `hãng TỪ CHỐI` / `KHÔNG BIẾT` (hết giờ, mạng chập) —
   kết cục thứ ba **không bao giờ** được coi là thành công.

## 37. MOCK / SANDBOX / PRODUCTION — tách rõ, và mặc định là MOCK

| Môi trường | Điều kiện chạy | Trạng thái đợt này |
|---|---|---|
| `mock` | **MẶC ĐỊNH.** Không chạm mạng, không cần credentials | **MỞ** |
| `sandbox` | Cần `V-G09-01` **VÀ** `V-13906-05` ⇒ **hiện CHƯA CẤP** | **BLOCKED** |
| `production` | Cần duyệt riêng của anh Thành | **KHÔNG ĐƯỢC PHÉP** |

Cấm mọi agent **tự mở** hai mức dưới. Code phải **đủ khả năng** chạy sandbox, nhưng phải **TỪ CHỐI**
cho tới khi Owner cấp. Từ chối kèm **lý do đọc được**, không im lặng.

## 38. CREDENTIALS — bề mặt cấu hình còn CHƯA TỒN TẠI

Đo được: **không có tệp `.env` nào**, và `.env.example` **không khai một khoá J&T nào**. Cần 4 tên
trường, **hai lớp, hai nguồn cấp** (đúng `docs/G09_CREDENTIALS_CHECKLIST.md`):

| Nhóm | Trường | Nguồn cấp |
|---|---|---|
| Nền tảng (Console J&T) | `apiAccount` · `privateKey` | J&T Open Platform |
| Bưu cục hợp tác | `customerCode` · `password` | bưu cục J&T |

**Luật — không ngoại lệ:**
- **CẤM** hard-code secret trong mã. **CẤM** đưa credentials vào Git (`.gitignore` đã chặn `.env*`,
  giữ `.env.example`). **CẤM** in ra log/terminal/stdout/prompt.
- Đường lưu **duy nhất** là `carrier_accounts.credentials_ma_hoa` qua **`bao_mat.ma_hoa_cred`**
  (AES-256-GCM, bản mã mang `key_id` dạng `v3$…`). Bốn hàm ở §3 là **hợp đồng**, không tự viết mã hoá.
- `.env.example` chỉ được khai **TÊN** khoá + mô tả, **giá trị luôn để rỗng**.

## 39. Quyền sở hữu file — G16

Bốn làn chạy **đồng thời trong CÙNG một cây** (hạ tầng chặn ghi `.git` nên không tách worktree được).

| Làn | SỞ HỮU (được ghi) | CẤM chạm |
|---|---|---|
| **AG-01 QA** | `docs/QA_G16.md` (mới) · `app/thu/thu_qa_g16.py` (mới) | **mọi mã sản phẩm** |
| **AG-02 HTTP TRANSPORT** | `app/http_jt.py` (mới) · `app/thu/thu_http_jt.py` (mới) · `app/thu/stub_jt.py` (mới) · `docs/G16_TRANSPORT.md` (mới) | `adapter_jt.py`, `webhook.py`, `csdl.py`, `migrate.py`, `server.py` |
| **AG-03 J&T BUSINESS API** | `app/adapter_jt.py` · `app/thu/thu_adapter_jt.py` · `app/thu/thu_hop_dong_jt.py` · `docs/G16_JT_API.md` (mới) | `http_jt.py` (chỉ GỌI), `webhook.py`, `csdl.py`, `migrate.py`, `server.py` |
| **AG-04 WEBHOOK** | `app/webhook.py` · `app/thu/thu_webhook_jt.py` · `trien_khai/g16/` (mới) · `docs/G16_WEBHOOK.md` (mới) · `docs/G16_SANDBOX_HARNESS.md` (mới) | `adapter_jt.py`, `http_jt.py`, `csdl.py`, `migrate.py`, `server.py` |
| **AG-00** | `app/cau_hinh.py` · `.env.example` · `app/transport.py` · `app/server.py` · `app/csdl.py` · `app/migrate.py` · `app/thu/chay_tat_ca.sh` · `SHARED_CONTRACTS.md` · `.gitignore` · mọi file của agent SAU KHI bàn giao | — |

**Không agent nào được mở `CHO_PHEP_LIVE`.** Không agent nào được gọi mạng ra ngoài `127.0.0.1`.

## 40. Luật riêng của G16

- **KHÔNG gọi API hãng thật, kể cả sandbox** — `V-G09-01` + `V-13906-05` **CHƯA CẤP**. Mọi phép đo
  của lớp HTTP dùng **stub cục bộ trên `127.0.0.1`**. Đó là cách đo lớp HTTP thật mà không gọi hãng.
- **KHÔNG mở cổng ra Internet**, không tunnel, không deploy — `V-G11-01` chưa cấp.
- **KHÔNG đoán mã trạng thái `110`** (D-4). Mã chưa xác minh ⇒ `NEEDS_REVIEW`, cấm `DELIVERED`,
  cấm kích hoạt đối soát COD (§18).
- **GIỮ chốt chặn `city`/`area`** (D-9) — chưa có J&T xác nhận thì vẫn CHẶN CỨNG ngoài `mock`.
- **KHÔNG báo `LIVE VERIFIED`** nếu chưa có bằng chứng gọi API thật thành công. G16-A **không thể**
  đạt mức đó, và **không được** viết bất cứ câu nào đọc như đã đạt.
- Mỗi làn dùng `VIP_HUB_DATA` riêng (`/tmp/veh_g16_ag0x`) vì bốn làn chung một cây.

## 41. MỐC MÃ của G16 — và LUẬT VÂN TAY (AG-01 `G16-01`/`G16-02`, AG-00 chốt)

**Bảng "MỐC BẢO VỆ" ở §35 là bản ghi LỊCH SỬ của lượt G13–G15** (lúc đó cây thật sự sạch). Nó
**không** còn mô tả lượt G16 — đọc nó như hiện trạng là sai. Mốc của G16:

| Đối tượng | Giá trị G16 |
|---|---|
| Nền mã | `integration/g13-g15` @ **`449bb2d`** |
| `main` | **`de740dc`** — và **KHÔNG chứa G13–G15** (`merge-base --is-ancestor` thất bại) |
| CSDL THẬT | sha256 `aaf71362f86f7391f9394f77a5c8a3b24c81e7e1b6ca49da116143eb556d0c54` |

**LUẬT VÂN TAY — bắt buộc, không phải thiện chí.** Bốn làn ghi đồng thời vào **một** cây, nên một
lượt hồi quy **không** ghim được vào một mốc mã. Đo được (`docs/QA_G16.md` §1.3): vân tay cây đổi
**giữa** lượt chạy, và `git status` đi từ 1 → 6 tệp bẩn trong **2 phút**.

Từ nay, **mọi báo cáo có số đo** (của AG-00, AG-01, AG-02, AG-03, AG-04) phải kèm **hai** thứ:

1. **Vân tay cây** — lấy bằng lệnh, không điền tay:
   ```bash
   { git ls-files -s; git status --porcelain=v1; } | shasum -a 256
   ```

   > **BẢN ĐẦU CỦA LỆNH NÀY MÙ — AG-01 phát hiện (`G16-09`, MEDIUM).** Lệnh cũ là
   > `find app gateway thu_frontend thu_giao_dien -type f \( -name '*.py' -o -name '*.mjs' -o -name '*.sh' -o -name '*.json' \) | …`,
   > tức **`docs/` không nằm trong phạm vi** và **`.md` không nằm trong danh sách đuôi**. Đo được:
   > thêm một dòng vào **chính tệp hợp đồng này** (`docs/SHARED_CONTRACTS.md`) mà vân tay
   > **không nhúc nhích một ký tự** (`9a72ec87…` trước = sau). Luật §41 sinh ra để bảo đảm *"con số
   > nào cũng đối chiếu được với một cây"*, mà nó **mù đúng ở tệp quan trọng nhất** — §36–§42, thứ
   > định nghĩa ba cổng đang được nghiệm thu. Một lượt sửa hợp đồng giữa lượt đo sẽ **lọt qua** cả
   > vân tay **và** mắt người đọc.
   >
   > **AG-01 tự nhận đây là lỗi của chính nó** — nó viết lệnh đó trước, AG-00 chép nguyên văn vào
   > luật; rồi nó **tự kiểm cái mình viết** và thấy nó **hổng**. Ghi lại đúng như vậy.
   >
   > **Vì sao lệnh mới kín hơn:** `git ls-files -s` liệt kê **mọi tệp được theo dõi** kèm hash blob
   > ⇒ phủ **mọi thư mục, mọi đuôi tệp**, không phụ thuộc danh sách mà ai đó nhớ để viết ra; còn
   > `git status --porcelain` phủ **thay đổi chưa commit**. Hai vế cộng lại thì không còn đường nào
   > sửa nội dung mà vân tay đứng yên. Đã kiểm chứng: sửa tệp hợp đồng ⇒ vân tay đổi
   > (`f673c48c…` → `eb028e61…`); hoàn tác ⇒ về đúng `f673c48c…`.
   >
   > **Bài học giữ nguyên hiệu lực:** *thứ dùng để kiểm chứng cũng phải được kiểm.* Lệnh vân tay là
   > một **bộ dò**, và bộ dò này đã **hổng một lượt** trước khi có người thử phá nó.

   **THỨ TỰ ƯU TIÊN (AG-01 đề nghị, AG-00 chốt).** Khi cây **đã commit và sạch**, khoá **bằng Git**
   là **CHÍNH** — nó phủ **mọi tệp được theo dõi**, kể cả `docs/**`, `.env.example`, `.gitignore`,
   nên **mạnh hơn** vân tay:

   | | Khi cây SẠCH (đã commit) | Khi cây BẨN (nhiều làn cùng ghi) |
   |---|---|---|
   | **CHÍNH** | `git rev-parse HEAD` + **`git diff HEAD` phải RỖNG** + **`git status --porcelain -uall` phải RỖNG** | vân tay (lệnh ở trên) |
   | **DỰ PHÒNG** | vân tay | `git status -uall` ghi kèm |

   **Vì sao thứ tự này, có ví dụ sống:** `HEAD` đi `c9fcaef → eb6cb3a` mà **vân tay KHÔNG đổi**
   (`9a72ec87…`). Vân tay **một mình** không phân biệt được *"chỉ thêm một tài liệu"* với *"không ai
   đụng gì"* — cả hai cho **cùng một con số**. Thứ **chứng minh được** là Git:
   `git diff --name-only c9fcaef eb6cb3a` → **đúng một** đường dẫn `docs/G16_ACCEPTANCE.md`,
   **0 tệp mã**. Nhờ đó mới dám nói câu **có căn cứ**: *"lượt đo trên `c9fcaef` vẫn đúng cho
   `eb6cb3a` vì mã không đổi một byte"*.
2. **Mốc giờ** của lượt đo.

Con số **không** kèm vân tay là con số **không đối chiếu được** — nó đúng với *một cây nào đó*,
không ai biết cây nào. Đây là **N-05 tái phát lần thứ ba**; theo `CLAUDE.md` §12.2, hỏng cùng kiểu
lần thứ hai thì **đổi CẤU TRÚC**, và luật này là cấu trúc thay cho lời dặn.

**Hệ quả đã ghi nhận:** hai con số `1133` và `1138` đều **đúng**, nhưng **không** con số nào là
*"hồi quy của mốc `449bb2d`"* — chúng là hồi quy của **hai cây khác nhau** trong cùng một buổi.

**Bổ sung quyền sở hữu (AG-01 `G16-04`):** `app/thu/thu_tich_hop.py` **thuộc AG-00** (bộ thử hợp
đồng/tích hợp). §39 ghi thiếu tên tệp này; nay xác nhận rõ.

## 42. `408` VÀ `429` — QUYẾT ĐỊNH ĐÃ CHỐT (AG-00, 15/10/2026)

**Cả `408` và `429` là lỗi TẠM THỜI**, không phải "4xx = vĩnh viễn". Lý do: cả hai là tín hiệu
*"thử lại sau"* của máy chủ, không phải *"yêu cầu của bạn sai"*. Trước quyết định này **hai lớp
nói ngược nhau** cho cùng một lượt gửi — `loi_hang.tu_http` nói thử lại được, `http_jt` nói vĩnh
viễn — đúng khuôn lệch im lặng. Ca canh chống lệch: `thu_http_jt.b10`,
`thu_adapter_jt.test_h5b`.

**`Retry-After` được tôn trọng, và LUÔN bị chặn trần** `transport.CHO_TOI_DA = 60.0`. Hãng không
được quyết định treo tiến trình: một `Retry-After: 86400` bị kẹp về 60 giây. Trần chỉ khai **một
chỗ** — khai hai chỗ là hai chỗ trôi khỏi nhau.

**`gui_form` CẤM ngủ.** Nếu lớp HTTP tự ngủ để tôn trọng `Retry-After`, `transport.goi()` sẽ gọi
lại nó tới `so_lan` lượt ⇒ tổng chờ = `so_lan × trần` (trần 30s ⇒ 90 giây treo trong một yêu cầu).
Việc chờ thuộc **`transport.goi()`** — nơi duy nhất sở hữu việc thử lại (§36 luật 1). Canh bằng
**AST** (`thu_http_jt.test_b11`, `thu_qa_g16.t24`) **và** bằng hành vi (`thu_adapter_jt.h5b` đo
thời gian < 5 giây).

### 42.1 `408` phát ra `timeout=True` — CỐ Ý, và đây là lý do

Mã `408` nghĩa là máy chủ không nhận kịp yêu cầu ⇒ *trên lý thuyết* biết là **chưa xử lý gì**. Vậy
mà `loi_hang.tu_http` xếp nó `HET_GIO`, nên adapter phát **`timeout=True`** = "KHÔNG BIẾT kết quả".

**AG-00 chốt: GIỮ NGUYÊN.** Hai lý do:
1. **Trong thực tế `408` KHÔNG rõ nghĩa.** Nhiều proxy phát `408` khi **thượng nguồn** quá hạn —
   lúc đó yêu cầu **có thể đã được xử lý**. Tin chắc "chưa xử lý gì" là tin vào một điều mình
   không kiểm được.
2. **Chi phí hai chiều LỆCH NHAU.** Đoán sai theo chiều thận trọng chỉ tốn **một lượt đối soát**;
   đoán sai theo chiều kia tốn **một vận đơn thật** (gửi lại và hãng tạo đơn trùng). Hợp đồng §10
   đã chốt nguyên tắc này: *"hãng timeout ⇒ giữ `dang_gui` + `can_doi_soat_ket_qua=1`, tuyệt đối
   không coi là thành công"*.

Muốn đổi thì đổi ở **`loi_hang.tu_http`** (tệp của AG-00), **không** đổi ở adapter. Ca thử ghim
bảng mong đợi để không ai phải đoán lại.
