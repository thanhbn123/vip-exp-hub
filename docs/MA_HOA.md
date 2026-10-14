# MÃ HÓA SECRET — AES-256-GCM

Owner duyệt 14/10/2026: *"Triển khai AES-256-GCM ngay"*. Đã thay bản tự dựng (XOR keystream + HMAC)
bằng AES-256-GCM của thư viện `cryptography` (đã được kiểm định — **không tự cài đặt AES**).

## Thiết kế

| Mục | Giá trị |
|---|---|
| Thuật toán | AES-256-GCM (AEAD: vừa mã hóa vừa xác thực toàn vẹn) |
| Khóa | 32 byte trong `app/du-lieu/khoa-noi-bo.key`, quyền 0600, ngoài git |
| Nonce | 12 byte (96 bit) ngẫu nhiên **mỗi lần mã hóa** |
| Định dạng | `v2$<nonce_hex>$<ciphertext_hex>` (tag nằm trong ciphertext) |
| Định dạng cũ | `<nonce>$<ct>$<mac>` — **chỉ còn đọc** để migrate, không mã hóa mới nữa |

## AAD — chống chép bản mã sang chỗ khác

GCM cho phép gắn dữ liệu xác thực kèm (AAD). Hệ dùng AAD để **buộc bản mã vào đúng chỗ của nó**:

| Loại secret | AAD | Chặn được gì |
|---|---|---|
| Credentials hãng | `cred:<tenant_id>:<hang>` | Chép bản mã của tenant A sang hàng tenant B → giải mã HỎNG |
| Webhook secret | `wh:<webhook_ma>` | Chép secret sang webhook khác → giải mã HỎNG |

Kẻ có quyền ghi CSDL cũng không thể hoán đổi credentials giữa các tenant.

## Cặp hàm bắt buộc dùng (đừng gọi `ma_hoa`/`giai_ma` trần)

```python
bao_mat.ma_hoa_cred(cred_dict, tenant_id, hang) -> (ban_ma, duoi_hien_thi)
bao_mat.giai_ma_cred(ban_ma, tenant_id, hang)   -> dict
bao_mat.ma_hoa_wh(secret, webhook_ma)           -> ban_ma
bao_mat.giai_ma_wh(ban_ma, webhook_ma)          -> secret
```

**Vì sao bắt buộc:** lúc đầu mỗi call site tự gọi `ma_hoa(...)` rồi tự truyền AAD. Chỉ cần **một chỗ
quên** là bên ghi và bên đọc lệch nhau → bản mã không đọc được. Đã dính thật ngày 14/10/2026: chỗ
tạo tài khoản hãng quên AAD cho webhook secret, làm **mọi webhook trả HTTP 500** (bộ thử bắt được).
Sửa bằng cách **đổi cấu trúc**: gộp AAD vào trong cặp hàm, call site không còn cơ hội dựng sai.
Chỉ `migrate.py` được dùng hàm trần, vì nó phải đọc định dạng cũ (vốn không có AAD).

## Không âm thầm tụt về sơ đồ yếu

Thiếu `cryptography` thì `bao_mat` **ném ImportError và hệ không chạy**, thay vì lặng lẽ dùng lại
sơ đồ cũ. Mã hóa yếu mà không ai biết còn nguy hơn là dừng hẳn.

```
python3 -m pip install cryptography     # nếu máy chưa có (máy này: 50.0.1, đã có sẵn)
```

## Migration (schema v3)

`app/migrate.py::nang_len_v3` giải mã bằng đường cũ rồi mã lại bằng AES-GCM + AAD. Chạy thật trên
CSDL đang dùng ngày 14/10/2026: **4 credentials + 4 webhook secret** chuyển xong, số dòng mọi bảng
giữ nguyên, và sau đó mọi secret đều đọc lại được đúng.

Hàng nào **không giải mã nổi** thì migration **không nổ cả lượt**: ghi rõ hàng nào hỏng vào ghi chú
của `schema_version` và in ra màn hình, giữ nguyên định dạng cũ để người xử — không im lặng bỏ qua.

## Giới hạn còn lại

- Khóa nằm trong **file trên đĩa**, chưa phải KMS/HSM. Ai đọc được file là giải mã được. Lên máy chủ
  thật nên chuyển sang KMS hoặc ít nhất biến môi trường + quyền chặt.
- **Chưa có cơ chế xoay khóa** (key rotation): đổi khóa hiện tại sẽ làm mọi bản mã cũ không đọc được.
  Muốn xoay thì cần thêm định danh khóa vào bản mã (`v3$<key_id>$...`) và một lượt mã hóa lại.
- Bản mã có `nonce` ngẫu nhiên 96 bit: an toàn ở quy mô này, nhưng nếu sau này mã hóa cực nhiều bản
  ghi bằng **cùng một khóa** thì nên cân nhắc nonce dạng đếm để triệt tiêu rủi ro trùng nonce.
