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
