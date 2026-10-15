# SAO LƯU KHOÁ RA NGOÀI THIẾT BỊ (G12 / D-3)

AG-05 SECURITY & KEY OPS · 15/10/2026 · nhánh `agent/g12-keyops`

| File | Việc |
|---|---|
| `dien-tap-khoa.sh` | **Một lệnh**, chạy thật, trên dữ liệu thử: sao lưu → kiểm → chứng nhận khôi phục → chốt → xoay trên bản sao → xoay thật trên nền thử. Không chạm `app/du-lieu/`. |
| `dua-goi-khoa-ra-ngoai.sh` | Đưa một gói `.vipkb` **đã mã hoá** ra khỏi máy. **Dừng lại hỏi người** trước lượt ghi thật đầu tiên. |
| `TOI-DA-DOC-VA-DONG-Y` | File công tắc, **do người tạo**. Không có trong repo, không script nào được tự tạo. |

Mã hoá gói là việc của `app/sao_luu_khoa.py` (AG-01) — thư mục này **không mã hoá lại gì**.
Mã hoá hai lần bằng hai sơ đồ là thêm một chỗ hỏng, không thêm an toàn.

---

## 1. Rủi ro mà D-3 sinh ra để vá — nói thẳng trước khi nói gì khác

> **Hôm nay gói khoá nằm CÙNG MÁY với CSDL mà nó bảo vệ.**

Mất ổ là mất cả hai cùng lúc. Và `secret_provider.lay_khoa()` **cố ý không sinh khoá thay thế**
(nó ném `LoiKhoa`), nên khi đó **không còn đường nào về**: bản mã credentials của mọi tenant
thành rác vĩnh viễn. Cái hỏng này không báo lỗi — CSDL vẫn đủ dòng, `integrity_check` vẫn `ok`,
hệ vẫn đăng nhập được, giao diện vẫn hiện tên tài khoản hãng. Tới **lượt gọi hãng đầu tiên**
mới biết, có thể là hôm sau, có thể là tuần sau.

Và một bản sao "ngoài" mà vẫn nằm **cùng ổ, cùng máy, cùng tài khoản đám mây** thì **không vá
được** rủi ro này. Nó chỉ làm người ta yên tâm, mà yên tâm sai tệ hơn lo đúng. Vì thế
`dua-goi-khoa-ra-ngoai.sh` có bước **K5**: nó `df` hai đầu và **cảnh báo nặng** khi nguồn và
đích nằm chung một ổ.

---

## 2. Ba điều kiện của D-3 — trạng thái từng điều

Anh Thành duyệt D-3 **có điều kiện**: *"mã hoá độc lập, kiểm tra quyền và diễn tập khôi phục."*

| # | Điều kiện | Trạng thái | Đo bằng gì |
|---|---|---|---|
| 1 | **Mã hoá độc lập** | **ĐẠT** (đã có từ G11/AG-01) | KEK dẫn xuất từ passphrase riêng — PBKDF2-HMAC-SHA256, 600.000 vòng, salt 16 byte **mỗi gói**; AES-256-GCM; **header làm AAD** nên sửa header là giải mã hỏng. `app/sao_luu_khoa.py` **từ chối** passphrase trùng nội dung khoá trong gói. Đo: `app/thu/thu_bao_mat.py` lớp `H_SaoLuuKhoa` |
| 2 | **Kiểm tra quyền** | **ĐẠT trong phạm vi script** | bảng mục 3 dưới đây, cưỡng chế ở bước **K1** (gói `0600`, chủ là người chạy) và **K4** (đích `0700`, không trong repo, không trong thư mục static) |
| 3 | **Diễn tập khôi phục** | **ĐẠT trên máy dựng** | `sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh` → mã thoát **0**. Số đo ở `docs/G12_KEY_OPS.md` mục 5 |
| + | **Lượt ghi THẬT ra VIP Vault** | **CHƯA — chờ anh Thành** | script dừng ở mã thoát **7**, xem mục 5 |

---

## 3. Quyền — ai được chạy, chạy ở đâu, gói nằm đâu với quyền gì

| Hạng mục | Quy định | Cưỡng chế ở đâu |
|---|---|---|
| Ai chạy | anh Thành, hoặc người anh chỉ định **bằng lời**. **Không phải tác tử.** | không cưỡng chế được bằng mã — ghi ra để không ai hiểu nhầm |
| Chạy ở đâu | **tay**, trên máy giữ gói. **Không** lịch chạy nền, **không** `launchd`/`cron` | công tắc `TOI-DA-DOC-VA-DONG-Y` phải do người tạo |
| Passphrase | chỉ trong đầu/kho mật khẩu của anh. **Không** vào vault, git, hội thoại, nhật ký (CLAUDE.md §15.2 cấm thẳng) | `sao_luu_khoa.lay_passphrase()` chỉ nhận env hoặc `getpass`; **không tự sinh** |
| Truyền passphrase | **CẤM** đặt trên dòng lệnh — `ps` nhìn thấy. Dùng biến môi trường hoặc nhập lúc chạy | — |
| Quyền file gói | `0600`, chủ sở hữu là người chạy | **K1**, từ chối nếu khác |
| Quyền thư mục đích | `0700` | **K4**, từ chối nếu khác |
| Đích hợp lệ | ổ rời **đã mã hoá toàn ổ**, hoặc một máy khác | — |
| Đích **cấm** | `admin/ pages/ assets/ mock/` (static đang phục vụ ⇒ tải về bằng GET vô danh) · bất kỳ đâu **trong repo** · ổ dùng chung không mã hoá | **K4**, từ chối |

Lệnh đưa anh Thành chạy **viết cho `zsh`** (CLAUDE.md §12.2). Cần nhập passphrase thì:

```zsh
stty -echo; printf 'Passphrase sao luu khoa: '; read VIP_HUB_BACKUP_PASSPHRASE; stty echo; echo
export VIP_HUB_BACKUP_PASSPHRASE
```

Không dùng `read -s -p` — đó là cú pháp bash, trong zsh nó nhận 0 ký tự rồi báo sai.

---

## 4. Quy trình — bốn bước, theo đúng thứ tự

```zsh
cd ~/code/veh4-g12-keyops          # hoặc thư mục triển khai thật
export VIP_HUB_BACKUP_PASSPHRASE='...'      # xem đoạn zsh ở mục 3

# B1. TẠO gói (sao_luu_khoa, không phải xoay_khoa)
python3 app/sao_luu_khoa.py tao ~/sao-luu-khoa/khoa-$(date +%Y-%m-%d).vipkb

# B2. KIỂM gói TRƯỚC khi tin nó — §12.1
python3 app/sao_luu_khoa.py kiem ~/sao-luu-khoa/khoa-$(date +%Y-%m-%d).vipkb

# B3. CHỨNG NHẬN khôi phục — khôi phục thật vào thư mục cô lập, giải mã lại cả hai đường
python3 app/xoay_khoa.py chung-nhan ~/sao-luu-khoa/khoa-$(date +%Y-%m-%d).vipkb

# B4. ĐƯA RA NGOÀI — chạy khô trước, rồi mới ghi thật
sh trien_khai/sao_luu_ngoai/dua-goi-khoa-ra-ngoai.sh \
      ~/sao-luu-khoa/khoa-$(date +%Y-%m-%d).vipkb /Volumes/<o-roi>/vip-khoa --chay-kho
```

**Thứ tự này không đảo được.** B2 trước B3 vì không khôi phục một gói chưa kiểm. B3 trước B4 vì
*một gói chưa từng được khôi phục là một gói **chưa biết** có dùng được không* — và lúc cần tới
nó thì không còn chỗ để thử.

---

## 5. Chỗ script DỪNG LẠI HỎI

`dua-goi-khoa-ra-ngoai.sh` thoát **mã 7** và không ghi gì, trừ khi có **một** trong hai:

- file công tắc `trien_khai/sao_luu_ngoai/TOI-DA-DOC-VA-DONG-Y` — **do người tạo**, và
- hoặc tham số `--toi-da-doc-va-dong-y`.

`--chay-kho` không cần công tắc: nó kiểm hết K1…K5 rồi dừng, **không ghi gì**.

Màn hình dừng bắt đọc lại bốn câu, và câu thứ ba là câu hay bị bỏ qua nhất: **passphrase mở gói
đang ở đâu, và nó có nằm cùng chỗ với gói không?** Gói và passphrase cùng một chỗ thì cả sơ đồ
mã hoá độc lập ở mục 2 trở thành trang trí.

---

## 6. VIP Vault — nói rõ cái CHƯA BIẾT

`CLAUDE.md` §19.4: từ 27/09/2026 hệ sao lưu **duy nhất** là VIP Vault (`/opt/vip-vault` trên
VPS, 5 timer systemd, kho chính là NAS). Nó **tự dò mọi CSDL SQLite** và **dump PostgreSQL**.

> **Gói khoá `.vipkb` KHÔNG nằm trong phạm vi đó. CHƯA ĐO — đừng giả định nó tự được sao lưu.**

Nó không phải SQLite, không phải PostgreSQL, và chưa ai thêm nó vào `/etc/vip-vault/config.yml`.
Cần **một quyết định nữa của anh Thành**, hai hướng:

| | Hướng | Được gì | Mất gì |
|---|---|---|---|
| **(a)** | thêm thư mục gói khoá vào `/etc/vip-vault/config.yml` | đi theo 5 timer sẵn có, tự chép sang NAS, tự kiểm khớp, tự xoay vòng, `canh-bao.py` canh sẵn | gói khoá **nhân bản** theo đường VPS → NAS → (NAS đồng bộ vault hai máy Mac). Nó có mặt ở nhiều chỗ hơn ta đếm được, và mỗi chỗ là một chỗ lộ |
| **(b)** | giữ gói khoá **ngoài** VIP Vault, trên ổ rời do anh giữ tay | số bản sao đếm được trên đầu ngón tay; ai cầm được ổ là chuyện vật lý | không tự động ⇒ **sẽ quên**. Và quên ở đây không báo lỗi |

AG-05 **không tự chọn**: chọn (a) là chạm vào hệ sao lưu đang chạy trên VPS, mà chỉ thị **cấm
deploy VPS**. Script này **không có đường nào nối tới VPS** — nó chỉ chép vào một thư mục trên
máy đang chạy rồi **in ra** lệnh `rsync` cho anh tự chạy.

**Nếu chọn (a), phải quyết thêm hai điều** (ghi ra để không ai tưởng chỉ thêm một dòng config):

1. **Xoay vòng.** §19.4 cho phép xoá bản sao lưu tự sinh quá hạn. Gói khoá **khác** bản sao lưu
   CSDL ở một điểm sống còn: một gói khoá **cũ** vẫn mở được bản mã cũ, nên xoá nó không giống
   xoá một bản dump thừa. Mức giữ phải do anh đặt, không để mặc định ăn theo.
2. **Passphrase.** VIP Vault chép **file**; nó không biết gì về passphrase. Gói trên NAS mà
   passphrase mất là NAS đang giữ một file vô dụng. Chỗ giữ passphrase phải quyết **cùng lúc**,
   không để sau.

---

## 7. Giới hạn — cái thư mục này KHÔNG làm được

- **Chưa có lượt ghi thật nào ra ngoài thiết bị.** Mọi lượt đo ở đây chạy trên thư mục tạm của
  máy dựng. Blocker **B-2** của dự án (khôi phục trên **máy chủ sạch** bằng **passphrase thật**)
  **vẫn còn nguyên**, và `V-13906-03` vẫn **CHƯA CẤP**.
- **Không có cơ chế nhắc.** Không ai bị báo khi gói gần nhất đã quá cũ. Đây là chỗ hỏng im lặng
  còn lại của chính quy trình này — cùng điều `docs/KEY_BACKUP_RESTORE.md` mục 8 đã ghi, và
  G12 **không vá được** vì vá đúng là nối vào `canh-bao.py` trên VPS.
- **Một passphrase, một người giữ.** Ai mở được gói là giải được **mọi** bản mã của **mọi**
  tenant. Chưa có chia mảnh (Shamir), chưa có nhiều người cùng giữ.
- **Không chặn được người có quyền.** Script kiểm quyền file và đường đích; nó không chặn được
  người đã có quyền chạy nó cố tình chép gói đi chỗ khác. Đó là ranh giới của công cụ.
