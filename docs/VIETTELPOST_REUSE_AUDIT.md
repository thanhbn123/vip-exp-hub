# Audit: repo `vip-viettelpost` có gì tái dùng được cho VIP EXPRESS HUB?

**Người khảo sát:** AG-02 CARRIER · **Ngày đo:** 14/10/2026
**Quyền:** Owner cho phép **CHỈ ĐỌC**. Không sửa, không commit, không push vào repo đó — và lượt
khảo sát này đã giữ đúng như vậy.

## 0. Phạm vi của phép đo (§12.1 luật 3 và luật "0")

Mọi con số dưới đây đo bằng `wc -l`, `find`, `git log` và đọc tay toàn bộ file nguồn, trên:

| Thứ | Giá trị đo được |
|---|---|
| Đường dẫn | `~/code/vip-viettelpost` (bản trên MacBook) |
| Commit mới nhất | `4df8ce7` *"feat: add shipping persistence schema and migrations"*, 2026-09-29 12:12:59 +0700 |
| Tổng số commit | 2 |
| Mã nguồn `app/` | 1.286 dòng Python |
| Bộ thử | 618 dòng (4 file) |

**Nằm NGOÀI phạm vi đã đo:** các nhánh khác của repo đó (chỉ đọc nhánh đang checkout), lịch sử
commit bị ghi đè, và mọi bản khác của repo trên máy khác. Kết luận dưới đây **chỉ nói về bản
`4df8ce7` trên MacBook, ngày 14/10/2026.**

## 1. Kết luận một câu — nói thẳng

> **Lớp TÍCH HỢP HÃNG: không tái dùng được gì — nó là khung rỗng.**
> **Lớp LƯU TRỮ: không rỗng, có 1.325 dòng mã thật và có vài quyết định thiết kế đáng mượn Ý TƯỞNG,
> nhưng không mượn được MÃ, vì hai dự án khác hẳn nền kỹ thuật.**

Lượt khảo sát trước kết luận *"scaffold rỗng, không có gì tái dùng được"*. Kiểm lại thì **vế đầu
đúng, vế sau nói quá**: đúng với lớp provider (thứ AG-02 cần), nhưng repo đó **không rỗng toàn
bộ** — phần persistence là mã thật, có ràng buộc CSDL, có migration và có 471 dòng test cho riêng
repository. Bản đính chính này ghi lại cho đúng (§12.1: báo cáo nghiệm thu cũng phải nêu đúng
phạm vi của nó).

## 2. Bảng từng hạng mục — CÓ THẬT hay KHUNG RỖNG

| Hạng mục | Trạng thái đo được | Bằng chứng |
|---|---|---|
| **Authentication** | ❌ KHUNG RỖNG | `app/providers/viettel_post/auth.py` (11 dòng): trả `settings.vtp_token` nếu có, còn lại `raise NotImplementedError("Viettel Post auth chưa được bật...")`. Không có endpoint đăng nhập, không có luồng lấy token |
| **Vòng đời token** | ❌ KHÔNG CÓ | Không có hạn dùng, không làm mới, không lưu đệm, không xử lý 401-rồi-lấy-token-mới. Token chỉ là một biến cấu hình tĩnh |
| **Services (tra dịch vụ)** | ❌ KHUNG RỖNG | `provider.py::get_services` → `NotImplementedError("Chưa map endpoint dịch vụ Viettel Post.")` |
| **Tính cước** | ❌ KHUNG RỖNG | `provider.py::calculate_fee` → `NotImplementedError` |
| **Tạo đơn** | ❌ KHUNG RỖNG | `provider.py::create_shipment` → `NotImplementedError` |
| **Hủy đơn** | ❌ KHUNG RỖNG | `provider.py::cancel_shipment` → `NotImplementedError` |
| **Tracking / tra đơn** | ❌ KHUNG RỖNG | `provider.py::get_shipment` → `NotImplementedError` |
| **Ánh xạ trạng thái** | ❌ RỖNG HOÀN TOÀN | `status_mapper.py` (8 dòng): `STATUS_MAP: dict[str, ShipmentStatus] = {}` kèm `# TODO: Fill only after verifying official VTP status codes.` **Không có một mã trạng thái VTP nào** |
| **Webhook** | ⚠️ CÓ CỬA, KHÔNG CÓ RUỘT | `app/webhooks/routes.py` (18 dòng) có route `POST /shipping/webhooks/viettel-post`, nhưng thân hàm là 6 dòng TODO (xác thực chữ ký · lưu bản thô · chống trùng · ánh xạ · ghi sự kiện · cập nhật) rồi trả `{"accepted": True, ...}` — **nhận gì cũng báo đã nhận** |
| **Xử lý lỗi** | ❌ KHÔNG CÓ | Không có lớp lỗi chuẩn hóa, không có bảng mã lỗi, không retry, không timeout nghiệp vụ. `client.py` chỉ gọi `response.raise_for_status()` → ném thẳng `httpx.HTTPStatusError` |
| **Client HTTP** | ⚠️ KHUNG TỐI THIỂU | `client.py` (23 dòng): `httpx.AsyncClient(timeout=20.0)`, header `Bearer`, `Content-Type: application/json`. Không retry, không phân biệt đọc/ghi, không chống trùng |
| **Endpoint thật** | ❌ KHÔNG CÓ | `docs/VIETTEL_POST_INTEGRATION.md` tự ghi: *"Scaffold cố ý không điền endpoint/path cụ thể cho các API nghiệp vụ cho tới khi baseline và tài liệu Partner được xác minh"* |
| **Tests** | ⚠️ CHIA HAI NỬA | `test_health_contract.py` = `assert True` (2 dòng), `test_status_model.py` = 1 assert (4 dòng). **Nhưng** `test_shipping_repository.py` 471 dòng và `test_shipping_database_migrations.py` 141 dòng là test THẬT của lớp lưu trữ |
| **Lưu trữ / CSDL** | ✅ CÓ THẬT | `app/db/models.py` 424 dòng, `app/repositories/shipping.py` 400 dòng, migration Alembic `shp_0001` 501 dòng. 8 bảng, có `UniqueConstraint`/`CheckConstraint`/`Index` đầy đủ |
| **Chống lộ bí mật** | ✅ CÓ THẬT | `app/repositories/redaction.py`: danh sách TRẮNG cho header, danh sách marker cho JSON tự do |

**Tổng: 9 hạng mục tích hợp hãng — 7 rỗng hẳn, 2 là vỏ.** Đúng như cảnh báo trước lượt khảo sát.

## 3. Thứ duy nhất cụ thể về hãng — và vì sao KHÔNG được dùng làm căn cứ

`app/core/config.py` và `.env.example` có:

```
vtp_base_url = "https://partner.viettelpost.vn"
vtp_username / vtp_password / vtp_token      # kiểu xác thực dự kiến: Bearer
```

Đây là **phỏng đoán của repo đó**, không phải trích từ tài liệu Partner của hãng — chính repo đó
viết là chưa xác minh. Vì vậy **không chép vào `app/adapter_vtp.py` như dữ kiện**; nó đang nằm ở
đó dưới tên `VTP_HOST_CHUA_XAC_MINH` kèm ghi chú, đúng §12 (không biến giả định thành sự thật).

## 4. Có mượn được gì không? — tách MÃ và Ý TƯỞNG

**Mã: không.** VIP EXPRESS HUB chạy `sqlite3` + thư viện chuẩn, đồng bộ; repo kia là FastAPI +
SQLAlchemy + Alembic + `httpx`, bất đồng bộ. Chép sang sẽ kéo theo cả một nền phụ thuộc mới cho
một lớp mà bên này **đã có** (`app/csdl.py`, `app/don_hang.py`, `app/webhook.py`).

**Ý tưởng: có bốn thứ đáng cân nhắc** — đây là *đề xuất cho AG-00*, AG-02 **không tự làm** vì
chúng nằm ở file của người khác:

1. **`secret_reference` là CON TRỎ, không phải bí mật.** Bảng `shipping_accounts` chỉ lưu chuỗi
   dạng `env://VTP_TOKEN`, `vault://...`, và **CSDL tự ép khuôn `scheme://`** bằng `CheckConstraint`.
   Bên mình đang mã hóa bí mật rồi lưu thẳng vào bảng (AG-01, AES-256-GCM) — khác đường, nhưng ý
   "cấu trúc canh giữ chứ không canh bằng lời dặn" thì cùng một họ với §19.1 luật 5.
2. **Bảng sự kiện webhook có `fingerprint` SHA-256 + `UniqueConstraint(provider_id, fingerprint)`
   và `UniqueConstraint(provider_id, event_id)`.** Chống trùng webhook bằng **ràng buộc CSDL**, không
   bằng câu `if` trong mã. Đáng xem lại xem `app/webhook.py` bên mình có chốt tương đương chưa.
3. **`redaction.py` dùng danh sách TRẮNG cho header, danh sách marker cho JSON tự do** — và nó ghi
   rõ lý do chọn mỗi bên. Trùng khớp câu hỏi phân biệt của §12.2 (*quên một dòng thì an toàn hay
   hỏng?*): quên một tên header chỉ mất gợi ý gỡ lỗi; quên một tên trong danh sách đen là **lộ
   credentials**. Cách nghĩ này nên áp vào chỗ ghi audit của hệ mình.
4. **Repository `flush` nhưng không `commit`; chèn chống trùng bọc trong SAVEPOINT** để một bản ghi
   trùng không kéo đổ cả giao dịch của người gọi.

## 5. Nút thắt thật của Viettel Post

Trước lượt khảo sát, hồ sơ dự án ghi nút thắt là *"chưa được phép đọc repo `vip-viettelpost`"*.
**Đo xong thì nút thắt đó không phải là nút thắt.** Đọc rồi, và trong đó không có mã trạng thái,
không có endpoint, không có mã lỗi nào của hãng.

> **Nút thắt thật: TÀI LIỆU PARTNER API chính thức của Viettel Post + credentials test.**
> Không có hai thứ đó thì adapter VTP ở bên mình **phải** ở nguyên mức mock, vì điền tiếp là bịa.

Đối chiếu để thấy chênh lệch: J&T có tài liệu công khai đọc được, nên bên mình đã có **13 mã trạng
thái** (`app/trang_thai_hang.py`) và **26 mã lỗi** (`app/loi_hang.py`) có nguồn. VTP: **0 và 0** —
và con số 0 đó là *"chưa đọc được tài liệu"*, không phải *"hãng không có"*.

## 6. Việc đề nghị AG-00 quyết

| # | Việc | Vì sao |
|---|---|---|
| 1 | Xin Owner **tài liệu Partner API của Viettel Post** (hoặc tài khoản để đọc cổng đối tác) | Đây là thứ duy nhất gỡ được BLOCKED của VTP. Xin thêm quyền đọc repo sẽ không giúp gì |
| 2 | Rà `app/webhook.py`: chống trùng đã bằng ràng buộc CSDL chưa, hay chỉ bằng mã? | Ý tưởng 2 mục 4. File của AG-00/AG-04, AG-02 không đụng |
| 3 | Rà chỗ ghi audit: payload hãng có đi qua bộ lọc bí mật không? | Ý tưởng 3 mục 4. SHARED_CONTRACTS mục 8 cấm ghi token vào audit, nhưng cấm bằng lời dặn thì không chặn được máy |
| 4 | Chốt: repo `vip-viettelpost` có còn là nguồn tham chiếu nữa không | Nó dừng ở commit 29/09/2026 và lớp provider chưa từng được điền. Để mở dễ làm người sau tưởng ở đó có sẵn tích hợp |
