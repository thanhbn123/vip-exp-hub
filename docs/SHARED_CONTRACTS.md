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
