# G09 — CHECKLIST CREDENTIALS

**Soạn:** AG-03 CARRIER, 15/10/2026.

> **File này KHÔNG chứa credentials nào và không bao giờ được chứa.** Nó chỉ liệt kê *cần những
> trường nào*, *xin ai*, *để ở đâu*. Luật §15.2 của `CLAUDE.md` cấm tuyệt đối ghi mật khẩu,
> OTP, số thẻ, khoá API vào kho tri thức; mục 14 của `docs/SHARED_CONTRACTS.md` quy định chỉ
> bốn hàm `bao_mat.ma_hoa_cred / giai_ma_cred / ma_hoa_wh / giai_ma_wh` được chạm bí mật.

---

## 0. Cách harness nhận credentials — và vì sao không qua biến môi trường trần

`app/harness_hang.py` đọc credentials từ **một file JSON** mà biến `VIP_HUB_HARNESS_CRED_FILE`
trỏ tới, chứ không nhận giá trị trực tiếp từ biến môi trường.

Lý do đo được: biến môi trường trần hiện trong `ps -E`, trong log của bộ lập lịch, và trong ảnh
chụp màn hình khi ai đó dán `env` vào hội thoại. File thì chỉ lộ **đường dẫn**.

Khuôn file (các giá trị dưới đây là **chỗ trống**, không phải giá trị thật):

```json
{
  "jt":  {"apiAccount": "", "privateKey": "", "customerCode": "", "password": ""},
  "vtp": {"vtp_token": "", "vtp_username": "", "vtp_password": "",
          "vtp_base_url": "https://partnerdev.viettelpost.vn"}
}
```

Đặt file **ngoài repo** (ví dụ `~/.config/vip-hub/g09-cred.json`), quyền `600`. `.gitignore`
của repo **không** phải lớp bảo vệ duy nhất — đừng đặt trong cây làm việc.

---

## 1. J&T EXPRESS — bốn trường, HAI nguồn cấp khác nhau

Đây là chỗ nhiều người nhầm: J&T có **hai lớp tài khoản**, và có một lớp thì vẫn chưa gọi được.

| # | Trường | Lớp | Xin ai | Tài liệu gọi nó là gì | Trạng thái 15/10/2026 |
|---|---|---|---|---|---|
| 1 | `apiAccount` | nền tảng | tự xem trong *控制台* sau khi hoàn tất 开发者认证 | *"接入方在平台的api账户标识"* | **CHƯA CÓ** cho VIP EXPRESS HUB |
| 2 | `privateKey` | nền tảng | như trên | *"apiAccount和privateKey可在控制台内查看"* | **CHƯA CÓ** |
| 3 | `customerCode` | hợp đồng khách | **bưu cục hợp tác của J&T** cấp | *"客户编码（客户合作网点提供）"* | **CHƯA CÓ** |
| 4 | `password` | hợp đồng khách | như trên | *"客户资料提供的开平账号密码"* | **CHƯA CÓ** |

### Hai điều đã đo được, nói rõ để không ai hiểu nhầm

1. **Trang tài liệu công khai IN SẴN một `apiAccount` và một `privateKey` của môi trường thử**
   (mục *接口信息* của mọi trang API). Chúng tôi **cố ý không chép giá trị đó vào bất kỳ file
   nào của dự án**: dù là giá trị công khai, chép khoá vào vault là tạo tiền lệ sai, và đến khi
   có khoá thật thì không ai phân biệt được nữa. Ai cần thì mở đúng trang tài liệu mà xem.
2. **Có hai trường đó vẫn KHÔNG tạo được đơn thử.** `customerCode` và `password` không có trên
   trang, phải do bưu cục cấp. Đây là nút thắt thật — câu hỏi 20 của
   `docs/JT_CAU_HOI_CHINH_THUC.md`.

### Thủ tục đối tiếp (chép từ trang `极兔API简介`, đọc 15/10/2026)

1. Đăng ký tài khoản trên `open.jtexpress.vn`.
2. Xin làm nhà phát triển (*申请成为开发者*).
3. **开发者认证** — chứng thực nhà phát triển, bước này mới mở đủ quyền các API đơn hàng và
   nhãn điện tử.
4. **联调测试** — chạy thử trên môi trường test, *"与具体的接口服务人员沟通"* (phải có người
   phụ trách của J&T đi kèm).
5. 发布上线 — lên thật sau khi bước 4 đạt.

⇒ **Không có đường tự phục vụ.** Bước 3 và 4 đều cần người của J&T.

---

## 2. VIETTEL POST — một trong hai cách

| # | Trường | Bắt buộc | Xin ai | Ghi chú |
|---|---|---|---|---|
| 1 | `vtp_base_url` | có | — | **Phải là `https://partnerdev.viettelpost.vn`** cho sandbox. `partner.viettelpost.vn` 301 sang `partner2.viettelpost.vn` (production) |
| 2a | `vtp_token` | **hoặc** nhóm 2b | tạo trên `viettelpost.vn` rồi đổi qua `POST /v2/user/LoginVTP`, hoặc token dài hạn sẵn có | token tĩnh ⇒ bước `authenticate` **không gọi mạng**, xem cảnh báo dưới |
| 2b | `vtp_username` + `vtp_password` | **hoặc** 2a | tài khoản Partner dev do Viettel Post cấp | đường đầy đủ: `Login` → `ownerconnect` |

### Cảnh báo bắt buộc đọc trước khi dùng token tĩnh

Repo `thanhbn123/vip-viettelpost` đã dính và đã **rút lại** một kết luận PASS vì điều này
(`CR-STG-007`, 01–02/10/2026): với token tĩnh, bước `authenticate` không gọi mạng, và hai API
`getPriceAll` / `getPrice` của `partnerdev` **không kiểm token** — nên **một token bịa cũng cho
kết quả PASS**.

⇒ Lượt sandbox của chúng ta **phải** dùng đường `Login` + `ownerconnect` (2b) cho ít nhất một
lượt, để biết credentials thật sự đúng. Dùng 2a thì ghi rõ là *chưa chứng minh được token đúng*.

---

## 3. Những thứ KHÔNG phải credentials nhưng vẫn phải có trước khi chạy sandbox

| # | Thứ cần | Ai cấp | Vì sao |
|---|---|---|---|
| 1 | Mã việc **`V-G09-01`** (gọi API hãng) | anh Thành | `docs/SHARED_CONTRACTS.md` mục 25 ghi **CHƯA CẤP**. Harness từ chối chạy nếu `VIP_HUB_HARNESS_DUYET` không khớp |
| 2 | Mã việc **`V-13906-05`** (credentials sandbox J&T) | anh Thành | như trên |
| 3 | `VIP_HUB_HARNESS_NGUOI_DUYET` | — | ghi tên người chịu trách nhiệm lượt chạy; harness từ chối nếu rỗng |
| 4 | Mở `CHO_PHEP_LIVE` trong `app/adapter*.py` | **chỉ Owner**, qua AG-00 | hằng chốt cứng. G09 CHỈ ĐỌC file đó và **không đề nghị** mở ở đợt này |
| 5 | URL công khai cho callback (nếu thử webhook thật) | AG-05 DEVOPS (V-G11-01, **CHƯA CẤP**) | hãng phải gọi được vào mình |
| 6 | Địa chỉ gửi/nhận thật nằm trong vùng phục vụ | vận hành | J&T trả `145005004`/`1450033315` nếu địa danh sai |

---

## 4. Nơi cất credentials sau khi có — ba lớp, không trộn

| Nơi | Dùng cho | Luật |
|---|---|---|
| File JSON ngoài repo, quyền `600` | chạy harness bằng tay trên máy người | **không** commit, **không** đưa vào vault, **không** dán vào hội thoại |
| Bảng `carrier_accounts.credentials_ma_hoa` | tài khoản hãng của tenant trong sản phẩm | mã hoá bằng `bao_mat.ma_hoa_cred`, bản mã mang `key_id` (`v3$…`) để xoay khoá được |
| Kho bí mật của nơi triển khai | chạy tự động | thuộc G11, **V-G11-01 CHƯA CẤP** |

**Cấm** chép credentials giữa ba nơi bằng tay. **Cấm** lấy token production từ repo khác
(`vip-viettelpost` có credentials trong GitHub Environment `staging` — đó là của repo đó, không
phải của dự án này; chỉ thị G09 cấm rõ điều này).

---

## 5. Cách TỰ KIỂM đã đủ chưa, không cần đoán

```sh
export VIP_HUB_DATA=$(mktemp -d)
export VIP_HUB_HARNESS_DUYET=V-G09-01
export VIP_HUB_HARNESS_NGUOI_DUYET="<tên người duyệt>"
export VIP_HUB_HARNESS_CRED_FILE="$HOME/.config/vip-hub/g09-cred.json"
python3 - <<'PY'
import sys; sys.path.insert(0, "app")
import harness_hang as hh
for hang in ("jt", "vtp"):
    thieu = hh.thieu_gi_de_chay(hh.SANDBOX, hang)
    print(hang, "— ĐỦ" if not thieu else "— còn thiếu:")
    for t in thieu:
        print("   -", t)
PY
```

Lệnh trên **chỉ đọc cấu hình, không gọi hãng**. Nó in ra đúng danh sách còn thiếu, cùng một
danh sách mà harness dùng để từ chối chạy — nên không có chuyện báo cáo nói một đằng, lúc chạy
lại một nẻo.

Hôm nay (15/10/2026) chạy ra: mỗi hãng còn **4 điều kiện thiếu** (mã việc · người duyệt · file
credentials · `CHO_PHEP_LIVE=False`).
