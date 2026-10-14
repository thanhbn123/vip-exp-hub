# MÃ HÓA SECRET — AES-256-GCM

Owner duyệt 14/10/2026: *"Triển khai AES-256-GCM ngay"*. Đã thay bản tự dựng (XOR keystream + HMAC)
bằng AES-256-GCM của thư viện `cryptography` (đã được kiểm định — **không tự cài đặt AES**).

## Thiết kế

| Mục | Giá trị |
|---|---|
| Thuật toán | AES-256-GCM (AEAD: vừa mã hóa vừa xác thực toàn vẹn) |
| Khóa | 32 byte mỗi file, `app/du-lieu/khoa/<key_id>.key`, quyền 0600, thư mục 0700, ngoài git |
| Nonce | 12 byte (96 bit) ngẫu nhiên **mỗi lần mã hóa** |
| Định dạng GHI hiện nay | `v3$<key_id>$<nonce_hex>$<ciphertext_hex>` — có định danh khóa |
| Định dạng chỉ ĐỌC | `v2$<nonce_hex>$<ciphertext_hex>` (khóa `goc`) và `<nonce>$<ct>$<mac>` (v1 XOR+HMAC) |
| Nguồn khóa | `app/secret_provider.py` — `LocalSecretProvider` đọc `app/du-lieu/khoa/<key_id>.key` |

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

## key_id và SecretProvider (thêm 14/10/2026)

Bản mã v2 **không nói nó dùng khóa nào**, nên đổi khóa là mọi bản mã cũ thành rác — thực tế
không xoay khóa được. Định dạng `v3` mang `key_id`, nên khóa cũ và khóa mới **sống song song**:
bản nào chưa kịp chuyển vẫn giải được bằng đúng khóa của nó.

### Ba lớp nguồn khóa — `app/secret_provider.py`

| Lớp | Việc |
|---|---|
| `SecretProvider` | lớp nền: `lay_khoa(key_id)` · `khoa_hien_hanh() -> (key_id, bytes)` · `danh_sach_key_id()` (+ `tao_khoa_moi`, `dat_khoa_hien_hanh` cho đường xoay khóa) |
| `LocalSecretProvider` | khóa trong file: `app/du-lieu/khoa/<key_id>.key` (32 byte, 0600), con trỏ khóa hiện hành ở `app/du-lieu/khoa/hien-hanh` |
| `KMSSecretProvider` | **CHỈ giao diện**, mọi hàm ném `NotImplementedError`. Cố ý chưa triển khai: một bản KMS "trông như thật" mà chưa đo với dịch vụ thật đúng là hỏng im lặng (§12.2) |

**Di cư khóa cũ:** khóa một-file cũ `app/du-lieu/khoa-noi-bo.key` được **chép** (không di chuyển)
thành `khoa/goc.key` và là khóa hiện hành đầu tiên. Phải **chép**, vì bản mã v1/v2 không mang
`key_id` nên `bao_mat` vẫn phải đọc đúng file cũ ở đúng chỗ cũ — xóa file cũ là mất dữ liệu.

**Thiếu khóa thì ném `LoiKhoa`, KHÔNG sinh khóa mới.** Sinh khóa thay thế chỉ biến
"giải mã hỏng, thấy ngay" thành "dữ liệu mất, không ai thấy".

**`key_id` bị kiểm bằng biểu thức** `^[a-z0-9][a-z0-9._-]{0,62}$`: `key_id` lọt `$` thì phá định
dạng bản mã, lọt `/` hay `..` thì thoát khỏi thư mục khóa.

### Xoay khóa — `bao_mat.xoay_khoa()`

Thứ tự **cố ý**: sinh khóa mới → đặt làm hiện hành → mới mã hóa lại dữ liệu. Hỏng giữa đường thì
hàng chưa chuyển vẫn mang `key_id` cũ, khóa cũ vẫn còn, nên vẫn giải được. Đổi thứ tự (xóa khóa cũ
trước) là mất dữ liệu.

- Phủ **cả hai** cột secret của `carrier_accounts`: `credentials_ma_hoa` và `webhook_secret_ma_hoa`.
- Nhận được cả bản mã v1 và v2 (coi là "cần xoay"), không chỉ v3 khóa cũ.
- Một hàng không giải được thì **ghi ra** rồi đi tiếp; audit ghi `ket_qua='that_bai'` — không báo
  đạt khi chưa đạt.
- **Khóa cũ không bao giờ bị xóa ở đây.** Bỏ một khóa cũ là việc người làm, sau khi tự kiểm không
  còn bản mã nào mang `key_id` đó (§19).
- Audit chỉ ghi `key_id` và **số lượng** — không ghi secret, không ghi nội dung khóa.
- **Không đụng** `credentials_doi_luc`: cột đó ghi lần đổi *credentials của hãng*, còn đây là đổi
  *khóa mã hóa*. Gộp hai việc vào một cột làm mất nghĩa cả hai.

### Migration schema v4

`app/migrate.py::nang_len_v4` đưa mọi secret sang `v3$<key_id>$…` bằng khóa **hiện hành**
(không sinh khóa mới — việc đó là của `xoay_khoa`). Dùng cùng khuôn với v3: backup, transaction,
kiểm bảo toàn số dòng, báo rõ hàng hỏng thay vì nổ cả lượt.

## Sao lưu / khôi phục khóa (thêm 15/10/2026 — S03)

Mất `app/du-lieu/khoa/` là **mất sạch credentials hãng**, và cái hỏng đó **không báo lỗi**: bản mã
vẫn còn trong CSDL, sao lưu CSDL vẫn khớp số dòng, hệ vẫn chạy — tới lượt gọi hãng đầu tiên mới
biết. Và `lay_khoa` cố ý **không sinh khóa thay thế**, nên không có bản sao lưu là không có đường
về. Trước 15/10/2026 hệ **chưa có** quy trình nào cho việc này.

Nay có `app/sao_luu_khoa.py`. Điều quan trọng nhất của thiết kế:

> **Gói backup được bảo vệ bằng passphrase RIÊNG do người vận hành cấp — KHÔNG bằng chính khóa
> đang được sao lưu.** Mã hóa gói bằng khóa nằm trong gói thì nó chỉ là một file nén có mật khẩu
> dán sẵn bên trong: mất thư mục khóa là mất luôn đường mở backup.

| Mục | Giá trị |
|---|---|
| KEK | PBKDF2-HMAC-SHA256 từ passphrase, salt 16 byte mỗi gói, 600.000 vòng (dưới 100.000 thì từ chối) |
| Mã hóa gói | AES-256-GCM, nonce 12 byte, **AAD = toàn bộ header** (hạ `vong` trong header là giải mã hỏng) |
| Nguồn passphrase | env `VIP_HUB_BACKUP_PASSPHRASE`, hoặc nhập lúc chạy. **Không hard-code, không tự sinh** |
| Nội dung gói | mọi `<key_id>.key` + con trỏ `hien-hanh` + `khoa-noi-bo.key` + bản mã **kèm `tenant_id`/`hang`/`webhook_ma`** (đầu vào dựng AAD) + siêu dữ liệu |
| Chỗ bị từ chối ghi | `admin/ pages/ assets/ mock/` (static đang phục vụ), thư mục khóa, `.git/`, mọi chỗ trong repo mà `git check-ignore` không chặn, tên không đuôi `.vipkb` |

Chi tiết, lệnh, diễn tập khôi phục đã chạy thật và phần **`BLOCKED`** (passphrase production do
Owner giữ, chỗ cất gói ngoài máy chủ, lượt khôi phục trên máy chủ sạch, xoay vòng gói theo §19.4):
**`docs/KEY_BACKUP_RESTORE.md`**.

Một cái bẫy đáng ghi: bản đầu kiểm repo git bằng `os.path.isdir(.git)`. Trong một **git worktree**
thì `.git` là một **FILE**, nên chốt chặn gitignore **chết im lặng đúng ở nơi mọi agent đang làm
việc**. Bộ thử `h6` bắt được; đã đổi sang `os.path.exists`.

## Giới hạn còn lại

- Khóa vẫn nằm trong **file trên đĩa**, chưa phải KMS/HSM. Ai đọc được file là giải mã được.
  `KMSSecretProvider` mới là **giao diện rỗng** — chưa nối với dịch vụ nào, chưa đo lượt nào.
- `xoay_khoa()` hiện **chỉ phủ `carrier_accounts`**. Đó là hai cột secret duy nhất đo được trong
  schema v4 (đo bằng `grep` cột `*_ma_hoa` trong `app/csdl.py`, ngày 14/10/2026). Thêm bảng nào có
  secret mã hóa thì **phải** thêm vào `ma_hoa_lai_carrier_accounts` và vào bộ thử, nếu không nó sẽ
  bị bỏ sót im lặng ở lượt xoay sau.
- Chưa có lệnh/endpoint để người bấm xoay khóa — hiện chỉ gọi được từ mã (`bao_mat.xoay_khoa()`)
  hoặc qua `migrate.py`. Mở cửa HTTP cho việc này thuộc `app/server.py`, do AG-00 làm.
- Chưa có cơ chế **thu hồi** khóa cũ (đếm còn bao nhiêu bản mã mang `key_id` cũ rồi mới cho xóa).
  Bù lại một phần: `sao_luu_khoa.kiem_toan_ven()` **báo ra** `key_id` mà bản mã đang dùng nhưng
  gói backup không có — phát hiện ở bước kiểm, không để phát hiện lúc cần tới.
- Chưa có **lệnh/endpoint HTTP** để người bấm sao lưu khóa; hiện chỉ gọi từ dòng lệnh
  (`python3 app/sao_luu_khoa.py tao|kiem|header|khoi-phuc`) hoặc từ mã. Đề nghị **không** mở cửa
  HTTP cho việc sao lưu: passphrase sẽ đi qua body, vào log, vào bộ nhớ tiến trình web.
- Chưa có **cơ chế nhắc** khi gói backup gần nhất đã quá cũ — đây là chỗ hỏng im lặng còn lại của
  chính quy trình sao lưu.
- Gói backup chứa **mọi khóa còn giữ**, nên sức mạnh cả sơ đồ nằm ở **một** passphrase. Chưa có
  chia mảnh (Shamir) hay nhiều người cùng giữ.
- Bản mã có `nonce` ngẫu nhiên 96 bit: an toàn ở quy mô này, nhưng nếu sau này mã hóa cực nhiều bản
  ghi bằng **cùng một khóa** thì nên cân nhắc nonce dạng đếm để triệt tiêu rủi ro trùng nonce.
