# SAO LƯU / KHÔI PHỤC KHÓA MÃ HÓA (S03)

AG-01 · 15/10/2026 · mã: `app/sao_luu_khoa.py` · bộ thử: `app/thu/thu_bao_mat.py` lớp `H_SaoLuuKhoa`

---

## 1. Vì sao cần, và cái hỏng nó chặn

Mất `app/du-lieu/khoa/` là **mất sạch credentials hãng của mọi tenant**. Nhưng cái hỏng này
**không báo lỗi**:

- Bản mã vẫn nằm nguyên trong `carrier_accounts.credentials_ma_hoa`.
- Sao lưu CSDL vẫn chạy, vẫn đủ dòng, vẫn khớp số.
- Hệ vẫn khởi động, vẫn đăng nhập được, giao diện vẫn hiện tên tài khoản hãng.
- Tới lượt gọi hãng đầu tiên mới hỏng — có thể là ngày hôm sau, có thể là tuần sau.

Đúng dạng hỏng im lặng (`CLAUDE.md` §12.2). `secret_provider.lay_khoa` **cố ý không sinh khóa
thay thế** khi thiếu khóa (nó ném `LoiKhoa`), vì sinh khóa mới chỉ biến "giải mã hỏng, thấy
ngay" thành "dữ liệu mất, không ai thấy". Hệ quả: **không có bản sao lưu khóa thì không có đường
về.** Trước đợt này, hệ **chưa có** quy trình nào cho việc đó.

---

## 2. Luật cốt lõi: bản backup được bảo vệ ĐỘC LẬP

> **Không dùng chính khóa đang được sao lưu làm phương tiện bảo vệ bản sao lưu.**

Nếu gói backup được mã hóa bằng khóa nằm trong gói, nó chỉ là một file nén có mật khẩu dán sẵn ở
bên trong: mất thư mục khóa là vừa mất khóa **vừa mất đường mở backup**. Nên:

| Mục | Giá trị |
|---|---|
| Khóa mã hóa gói (KEK) | dẫn xuất từ **passphrase do người vận hành cấp** |
| KDF | PBKDF2-HMAC-SHA256, `dklen=32` |
| Số vòng | 600.000 (env `VIP_HUB_BACKUP_PBKDF2`; dưới 100.000 thì **từ chối**) |
| Salt | 16 byte ngẫu nhiên **mỗi gói** |
| Mã hóa | AES-256-GCM, nonce 12 byte, **AAD = toàn bộ header** |
| Nguồn passphrase | env `VIP_HUB_BACKUP_PASSPHRASE`, hoặc nhập lúc chạy (`getpass`, chỉ khi có terminal) |
| Độ dài tối thiểu | 16 ký tự, và không nằm trong danh sách chuỗi giữ chỗ (`changeme`, `password`…) |

**Ba điều hệ TỪ CHỐI, cưỡng chế bằng mã:**

1. **Không tự sinh passphrase.** Thiếu thì ném `LoiSaoLuu` kèm hướng dẫn. Bí mật tự sinh thì
   phải lưu ở đâu đó, và chỗ đó lại là một bí mật nữa không ai giữ.
   *(ca thử `h4`)*
2. **Passphrase không được là chính khóa đang sao lưu** — kiểm cả dạng byte thô, hex và base64.
   *(ca thử `h3`)*
3. **Hạ số vòng PBKDF2 trong header là giải mã HỎNG**, vì header là AAD của GCM. Không ai lấy
   được gói rồi sửa `vong: 600000` thành `vong: 1` để dò passphrase nhanh.
   *(ca thử `h8`)*

---

## 3. Khuôn gói `.vipkb`

```
b"VIPHUBKEYBAK1\n"            magic 14 byte
4 byte big-endian             độ dài header
header JSON (utf-8)           KHÔNG chứa bí mật nào → đọc được mà không cần passphrase
ciphertext                    AESGCM(KEK).encrypt(nonce, gzip(payload JSON), aad=header_bytes)
```

**Header** mang: `phien_ban`, `tao_luc`, `kdf`, `vong`, `salt_hex`, `nonce_hex`, `so_khoa`,
`khoa_hien_hanh`, `so_ban_ma`, `sha256_ro`. Đọc bằng `doc_header()` hoặc
`python3 app/sao_luu_khoa.py header <goi>`. Nhờ đó trả lời được "gói này của ngày nào, mấy khóa"
mà **không phải mở bí mật ra**. Ca thử `h11` quét header tìm nội dung khóa và passphrase ở ba
dạng — phải không thấy gì.

**Payload** (đã mã hóa) gồm bốn phần:

| Phần | Nội dung | Vì sao phải có |
|---|---|---|
| `khoa[]` | từng `<key_id>.key`: nội dung base64 + `sha256` + quyền | đây là vật liệu master key |
| `khoa_hien_hanh` | con trỏ `hien-hanh` | thiếu nó thì sau khôi phục hệ mã hóa MỚI bằng một khóa khác, và bản mã mới nằm dưới khóa **không ai sao lưu** |
| `khoa_cu` | file một-bản cũ `khoa-noi-bo.key` | bản mã **v1/v2 không mang `key_id`**, chỉ đọc được từ đúng file này ở đúng chỗ này |
| `ban_ma[]` | bản mã credentials + webhook secret, kèm **`tenant_id` · `hang` · `webhook_ma`** | ba trường đó là đầu vào dựng **AAD** (`cred:<tenant_id>:<hang>`, `wh:<webhook_ma>`). Khôi phục khóa xong mà AAD dựng sai thì vẫn giải không ra |
| `sieu_du_lieu` | `schema_version`, danh sách tenant (id/code/ten/trạng thái), số lượng | để nghiệm thu khôi phục **ngay trong môi trường cô lập**, không phải chờ CSDL thật |

`ban_ma[]` chỉ chứa **bản đã mã hóa** — hàm sao lưu không giải mã gì cả. Ca thử `h2` khẳng định
không có dấu hiệu plaintext (`{"`, `"api_key"`, chuỗi bí mật đã biết) trong đó.

---

## 4. Chỗ được ghi gói — và ba chỗ bị TỪ CHỐI

`_kiem_duong_ra()` chạy **trước** khi mã hóa (không phải sau), nên không bao giờ có một file bí
mật nằm sai chỗ, kể cả trong một phần giây.

| Từ chối | Vì sao |
|---|---|
| `admin/ pages/ assets/ mock/` | đó là **danh sách trắng static đang được phục vụ**. Gói ở đó **tải về được bằng một yêu cầu GET vô danh**. File này **KHÔNG đổi** danh sách trắng ấy — chỉ từ chối ghi vào đó |
| `app/du-lieu/khoa/` và `.git/` | lẫn backup với khóa thật là đường tới chỗ xóa nhầm |
| trong repo git mà `.gitignore` **không** chặn | đo bằng `git check-ignore`, không bằng niềm tin vào `.gitignore`. Lọt vào git là lộ vĩnh viễn trong lịch sử |
| tên file không có đuôi `.vipkb` | để gói bí mật không mang tên trông như file thường |

**Phòng hai lớp:** đuôi `.vipkb` cũng **không** nằm trong `DUOI_CHO_PHEP` của static, nên dù ai
đặt tay một file `.vipkb` vào `assets/` thì vẫn 404 *(ca thử `j5`)*.

**Một cái bẫy đã bắt được ngày 15/10/2026:** bản đầu dùng `os.path.isdir(goc_repo/.git)`. Trong
một **git worktree** thì `.git` là một **FILE** trỏ sang repo chính, không phải thư mục — nên
chốt chặn gitignore **chết im lặng đúng ở nơi mọi agent đang làm việc**. Ca thử `h6` bắt được;
đã đổi sang `os.path.exists`.

**Hai điều khác cưỡng chế bằng mã:** ghi file tạm rồi `os.replace` (nguyên tử), và `chmod 0600`
**trước** khi đổi tên — không có khe hở 0644 (`CLAUDE.md` §16.3).

---

## 5. Lệnh

```bash
export VIP_HUB_BACKUP_PASSPHRASE='...'          # hoặc để trống rồi nhập lúc chạy
python3 app/sao_luu_khoa.py tao       ~/sao-luu-khoa/khoa-2026-10-15.vipkb
python3 app/sao_luu_khoa.py header    ~/sao-luu-khoa/khoa-2026-10-15.vipkb   # không cần passphrase
python3 app/sao_luu_khoa.py kiem      ~/sao-luu-khoa/khoa-2026-10-15.vipkb   # mã thoát 1 nếu không đạt
python3 app/sao_luu_khoa.py khoi-phuc ~/sao-luu-khoa/khoa-2026-10-15.vipkb /duong/den/thu-muc-dich
```

**`thu_muc_dich` BẮT BUỘC, không có mặc định.** Mặc định về thư mục khóa đang chạy nghĩa là gõ
thiếu một tham số là ghi đè khóa thật.

**Mặc định KHÔNG ghi đè** file khóa đã tồn tại ở đích: nó vào danh sách `bo_qua` và lượt khôi
phục đi tiếp. Ghi đè một khóa **đang dùng** bằng khóa trong gói **cũ** là mất dữ liệu đã mã hóa
bằng khóa mới — mà không có gì báo lỗi cho tới lượt giải mã sau. Muốn ghi đè thì phải nói ra:
`--ghi-de` *(ca thử `h9`)*.

**Khóa gốc không bị di chuyển hay xóa ở bất kỳ nhánh nào** của `khoi_phuc()`.

Audit ghi `sao_luu_khoa` / `khoi_phuc_khoa` với **số lượng và `key_id`** — không ghi khóa, không
ghi passphrase. Audit hỏng thì **in lý do ra stderr**, không nuốt im lặng (§12.2).

---

## 6. DIỄN TẬP KHÔI PHỤC — đã chạy thật, có số

Ca `H_SaoLuuKhoa.test_h1_DIEN_TAP_backup_roi_khoi_phuc_roi_giai_ma_duoc`, chạy trong
`app/thu/thu_bao_mat.py`. Kết quả đo ngày 15/10/2026: **56/56 ca đạt**.

Chuỗi đo, đúng theo thứ tự:

| # | Bước | Phép đo | Kết quả |
|---|---|---|---|
| 1 | Dựng môi trường **cô lập** (`tempfile.mkdtemp`), bộ khóa riêng | thư mục khóa riêng + `LocalSecretProvider` riêng | khóa `goc` + 1 khóa mới |
| 2 | Mã hóa credentials + webhook secret bằng khóa hiện hành | `bao_mat.key_id_cua(ban_ma) == key_id_moi` | đạt |
| 3 | **Backup** | `so_khoa ≥ 2`, có `key_id` mới, có con trỏ hiện hành, quyền file | `0o600`, đạt |
| 4 | **Kiểm toàn vẹn TRƯỚC khi tin gói** (§12.1) | `sha256` từng khóa so với giá trị trong gói | `dat=True`, `loi=[]` |
| 5 | **Khôi phục** vào môi trường cô lập **thứ hai** | `da_ghi` khớp `key_id` của gói, con trỏ khôi phục đúng | đạt |
| 6 | **Giải mã bằng credentials thử** qua nhà cung cấp MỚI | `giai_ma_cred(...)["api_key"] == bí mật`, `giai_ma_wh(...) == bí mật` | đạt |
| 7 | **Không lộ secret** | quét **byte thô** của gói tìm khóa và plaintext ở **ba dạng** (thô / hex / base64) | `dang_bi_lo = []` |
| 8 | **Không chạm khóa gốc** | mọi file khóa gốc + `khoa-noi-bo.key` còn tồn tại | đạt |

Bước 7 là phép đo **độc lập với việc mã hóa**: nó không hỏi "đã mã hóa chưa", nó hỏi "chuỗi bí
mật có xuất hiện trong file không".

Mười một ca còn lại của lớp `H` phủ: ràng buộc tenant/hãng trong gói (`h2`), ba luật passphrase
(`h3`, `h4`), bốn chỗ bị từ chối ghi (`h5`, `h5b`, `h6`), sai passphrase / sửa một byte / sửa
header (`h7`, `h8`), không ghi đè (`h9`), thư mục khóa rỗng thì từ chối thay vì báo đạt (`h10`),
header không chứa bí mật (`h11`), và gói thiếu đúng khóa mà bản mã đang dùng thì **báo ra ở bước
kiểm** thay vì để phát hiện lúc cần tới (`h12`).

`h5b` so **trực tiếp** danh sách static của `server.py` với danh sách trong `sao_luu_khoa.py` —
hai danh sách ở hai file, lệch nhau là lỗ hổng im lặng, nên để bộ thử canh.

---

## 7. BLOCKED — phần chưa làm được, nói rõ ra

> **Khôi phục cho môi trường PRODUCTION: `BLOCKED`.**

Đợt này **chỉ nghiệm thu được đường khôi phục trong môi trường local cô lập**, bằng passphrase
do bộ thử tự đặt (`PASS_THU`, một chuỗi công khai nằm trong mã test, **không phải bí mật**).

Để khôi phục production được coi là nghiệm thu, còn thiếu:

1. **Passphrase sao lưu thật do Owner giữ** — chưa có. Phải do anh Thành (hoặc người anh chỉ
   định) sinh và giữ ngoài vault, ngoài git, ngoài hội thoại. **Không tự tạo một bí mật giả rồi
   báo PASS** — đó đúng là cái §12.1 cấm.
2. **Chỗ cất gói backup ngoài máy chủ** — chưa chọn. Lưu ý: `CLAUDE.md` §18 nói từ 27/09/2026
   chuỗi sao lưu đêm trên Mac mini **đã tắt**, và hệ sao lưu duy nhất là VIP Vault
   (`/opt/vip-vault`) với kho chính là NAS. Gói khóa **chưa** nằm trong phạm vi VIP Vault —
   chưa đo, đừng giả định nó tự được sao lưu.
3. **Lượt khôi phục thật trên một máy chủ sạch**, đo bằng chính gói production. Diễn tập local
   đạt **không** chứng minh được điều đó (§12.1 luật 3: kết luận chỉ nói trong phạm vi đã đo).
4. **Chính sách xoay vòng gói backup** — giữ bao nhiêu bản, bao lâu. Phải theo §19.4 (bản sao
   lưu tự sinh được xoay vòng, nhưng có ba chốt), hiện **chưa nối** vào
   `sao-luu-vps/xoay-vong-sao-luu.py`.

---

## 8. Giới hạn còn lại

- Khóa vẫn nằm trong **file trên đĩa**, chưa phải KMS/HSM. `KMSSecretProvider` vẫn là **giao
  diện rỗng** (cố ý — xem `docs/MA_HOA.md`).
- Gói backup chứa **mọi khóa còn giữ**, nên ai mở được gói là giải được mọi bản mã. Sức mạnh của
  cả sơ đồ nằm ở **một** passphrase. Chưa có chia mảnh (Shamir) hay nhiều người cùng giữ.
- **Chưa có lệnh/endpoint HTTP** để người bấm sao lưu. Hiện chỉ gọi từ dòng lệnh hoặc từ mã.
  Mở cửa HTTP thuộc `app/server.py`, do AG-00 làm — xem `docs/SECURITY_HARDENING_REPORT.md`.
- `ban_ma[]` hiện **chỉ phủ `carrier_accounts`**. Đó là hai cột secret duy nhất đo được trong
  schema v6 (cùng phạm vi với `bao_mat.ma_hoa_lai_carrier_accounts`). Thêm bảng nào có secret mã
  hóa thì **phải** thêm vào `_thu_gom_ban_ma()` **và** vào bộ thử, nếu không nó bị bỏ sót im
  lặng ở lượt sao lưu sau.
- Chưa có **cơ chế nhắc**: không ai bị báo khi gói backup gần nhất đã quá cũ. Đây là chỗ hỏng im
  lặng còn lại của chính quy trình này.
