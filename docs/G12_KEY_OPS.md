# G12 — XOAY KHOÁ CÓ KIỂM SOÁT & SAO LƯU KHOÁ RA NGOÀI

| | |
|---|---|
| Tác tử | AG-05 SECURITY & KEY OPS ENGINEER |
| Nhánh | `agent/g12-keyops` · worktree `~/code/veh4-g12-keyops` |
| Nền thật khi làm | `9af8115` (chỉ thị ghi `714fd76`; nhánh đã nhận thêm 3 commit của AG-00 — ghi ra để không ai đối chiếu nhầm) |
| Ngày | 15/10/2026 |
| Máy đã đo | MacBook Pro — `python3 3.9.6` · `cryptography` có · **Docker: KHÔNG CÓ** |
| File mới | `app/xoay_khoa.py` · `app/thu/thu_xoay_khoa.py` · `trien_khai/sao_luu_ngoai/` · hai tài liệu G12 |

---

## 0. KẾT LUẬN MỘT DÒNG

**Cơ cấu xoay khoá và đường đưa gói khoá ra ngoài đã dựng xong và đã chạy thật trên nền cô lập
(30/30 ca thử đạt, diễn tập một lệnh mã thoát 0). Nhưng KHÔNG có lượt nào chạm khoá thật, và
KHÔNG có lượt ghi thật nào ra VIP Vault — cả hai đều đang chờ anh Thành.**

`app/du-lieu/khoa/` của bản triển khai thật **không bị đụng**; bằng chứng ở mục 8.

---

## 1. HAI QUYẾT ĐỊNH, VÀ RANH GIỚI CỦA CHÚNG

### D-2 — *"Đồng ý, nhưng khoá bằng quyền quản trị đặc biệt và kiểm thử trên bản sao trước."*

| Anh yêu cầu | Đã làm | Chưa làm |
|---|---|---|
| quyền quản trị **đặc biệt** | quyền MỚI `platform.khoa.xoay`, **chỉ** `PLATFORM_OWNER`, hai lớp kiểm (mục 3) | AG-00 chưa seed quyền vào `role_permissions` |
| kiểm thử trên **bản sao** trước | `xoay_khoa.dien_tap()` — chép CSDL + khoá sang thư mục tạm, xoay ở đó, giải mã lại **cả hai** đường (mục 5.2) | — |
| **không** xoay khoá thật | **KHÔNG xoay lượt nào.** `V-13906-02` vẫn CHƯA CẤP | — |

### D-3 — *"Đồng ý có điều kiện: mã hoá độc lập, kiểm tra quyền và diễn tập khôi phục."*

Ba điều kiện và trạng thái từng điều: `trien_khai/sao_luu_ngoai/README.md` mục 2.
Tóm: (1) **ĐẠT** — đã có sẵn từ `app/sao_luu_khoa.py`, G12 **không viết lại**; (2) **ĐẠT trong
phạm vi script** — cưỡng chế ở bước K1/K4; (3) **ĐẠT trên máy dựng** — số đo mục 5.3.

**Lượt ghi THẬT đầu tiên ra VIP Vault: CHƯA, và script cố ý dừng lại hỏi** (mục 6).

### Thứ tự bắt buộc do chỉ thị đặt

> *"Không xoay khoá thật khi chưa kiểm tra phương án khôi phục."*

Nên: **khôi phục chứng minh được TRƯỚC, xoay khoá SAU.** Đây không phải lời khuyên trong tài
liệu — nó là **sáu điều kiện cưỡng chế bằng mã** ở mục 4, và `xoay_that()` không có đường nào
đi vòng qua chúng.

---

## 2. VÌ SAO CÓ `app/xoay_khoa.py`, KHI `bao_mat.xoay_khoa()` ĐÃ CHẠY ĐƯỢC

`bao_mat.xoay_khoa()` (AG-01, đã có) là **cơ cấu**: nó sinh khoá mới, đặt hiện hành, mã hoá lại.
Nó **không hỏi ai đang gọi** và **không hỏi có đường về hay chưa**.

Gọi thẳng nó trên máy chủ thật mà chưa có bản sao lưu kiểm được là đặt credentials của **mọi
tenant** lên một lượt ghi không có đường lùi. Mã hoá lại hỏng giữa đường thì còn cứu được —
khoá cũ giữ lại, bản mã chưa chuyển vẫn mang `key_id` cũ. Nhưng **mất thư mục khoá ngay sau
đó** thì không: `secret_provider.lay_khoa()` cố ý không sinh khoá thay thế.

`app/xoay_khoa.py` là **cái van** đặt trước cơ cấu đó. Nó **không viết lại** mã hoá, **không
viết lại** sao lưu — nó gọi `bao_mat` và `sao_luu_khoa`, và thêm đúng bốn thứ: **quyền**,
**chốt**, **bản sao**, **nghiệm thu sau xoay**.

---

## 3. QUYỀN — `platform.khoa.xoay`

**Tên đề xuất cho AG-00 seed:** `platform.khoa.xoay` — *"Xoay khoá mã hoá nền tảng"*.
Cấp cho **`PLATFORM_OWNER` và chỉ nó**. Không cấp cho `PLATFORM_ADMIN`.

Quyền này **mới**, không dùng lại quyền sẵn có. Có ca thử canh (`test_a1`): nếu về sau ai đó
đưa `platform.khoa.xoay` vào `quyen.QUYEN` dưới một cái tên trùng quyền khác thì bộ thử hỏng.

### Hai lớp kiểm, và vì sao phải hai

```python
if vai_tro not in VAI_TRO_DUOC_XOAY:            # lớp 1 — hằng số trong MÃ
    raise LoiXoayKhoa(...)
if not quyen.co_quyen(vai_tro, QUYEN_XOAY):     # lớp 2 — nguồn chân lý RBAC trong CSDL
    raise LoiXoayKhoa(...)
```

Lớp 1 nghĩa là: **một dòng `INSERT INTO role_permissions` không biến ADMIN thành người xoay
được khoá của cả nền tảng.** Ca `test_a4` đo đúng điều đó — nó **seed nhầm** quyền cho
`PLATFORM_ADMIN`, khẳng định `quyen.co_quyen()` trả `True`, rồi khẳng định `kiem_quyen()` vẫn
**từ chối**.

Đây **không phải** "lọc hai chỗ" mà `CLAUDE.md` §12.2 cấm: hai lớp đo **hai thứ khác nhau**
(danh tính vai trò / cấu hình quyền), nên chúng không che nhau. Cùng lý lẽ với hai lớp che log
của `quan_sat.che()` trong G11.

`VAI_TRO_DUOC_XOAY` là **danh sách trắng**, và ở đây trắng là đúng theo ngoại lệ §12.2 đã nêu
sẵn. Câu hỏi phân biệt: *quên một dòng thì an toàn hay hỏng?* Quên một vai trò ⇒ vai trò đó
không xoay được ⇒ **hỏng ồn ào**, có người báo. Dùng danh sách đen mà quên ⇒ vai trò lạ xoay
được khoá của cả nền tảng ⇒ **hỏng im lặng**.

### `xoay_khoa` KHÔNG tự seed quyền cho mình

Ca `test_a2`: chưa seed thì **ngay cả OWNER** cũng bị từ chối, kèm thông điệp nói rõ AG-00 phải
seed. Một mô-đun tự cấp quyền cho mình là một mô-đun không có quyền nào cả.

---

## 4. CHỐT — SÁU ĐIỀU KIỆN, THIẾU MỘT LÀ KHÔNG XOAY

`xoay_khoa.kiem_chot(goi, chung_nhan)` — **chỉ đọc**, không ghi gì, không tạo gì (ca `test_b8`
đo bằng cách so danh sách file và `mtime` của gói trước/sau).

| Mã | Điều kiện | Cái hỏng nó chặn |
|---|---|---|
| **C1** | Gói tồn tại, đúng khuôn `.vipkb`, đọc được header | xoay khi không có gói nào |
| **C2** | Gói **mở được**, **toàn vẹn**, và **phủ đủ mọi `key_id` mà CSDL SỐNG đang dùng** | gói **cũ** + khoá sinh sau đó ⇒ khôi phục xong vẫn mất phần dữ liệu mã hoá bằng khoá thiếu, **không gì báo** |
| **C3** | Có **chứng nhận khôi phục ĐẠT**, buộc vào gói này bằng **sha256** | chứng nhận của một gói khác bị đổi tên thành tên gói hôm nay |
| **C4** | Chứng nhận còn hạn (≤ 30 ngày) | chứng nhận năm ngoái không nói gì về gói hôm nay |
| **C5** | Chứng nhận do **lượt chạy KHÁC** ghi (`pid` khác) | **tiến trình tự làm chứng cho chính nó** |
| **C6** | CSDL có dấu vết `khoi_phuc_khoa` **của chính gói này**, do `sao_luu_khoa` ghi | bằng chứng hoàn toàn do mô-đun này tự dựng |

### C2 là điều kiện dễ bị bỏ sót nhất — nên nói riêng

`sao_luu_khoa.kiem_toan_ven()` đã kiểm *"bản mã TRONG GÓI có đủ khoá chưa"*. Nhưng gói là **bản
chụp của một thời điểm**. Giữa lúc tạo gói và lúc xoay, hệ có thể đã ghi thêm secret dưới một
khoá khác. Nên C2 hỏi lại **CSDL SỐNG**, không hỏi lại cái gói. Ca `test_b5` dựng đúng tình
huống đó: tạo gói → sinh khoá mới → thêm một tài khoản hãng → C2 **không đạt**, và nó nêu đúng
`key_id` còn thiếu.

Và đây cũng là lý do bước **B9** của diễn tập **cố ý** cho chốt từ chối: sau khi xoay, gói cũ
không còn phủ đủ khoá nữa. Đó là hành vi **đúng** — xoay xong thì **phải tạo gói mới**.

### C5 và C6 — thứ dùng để kiểm chứng phải ĐỘC LẬP (§12.1)

Ca thật trong vault: *bước nghiệm thu của bộ cài tự chạy hộ bằng shell có sẵn quyền, nên nó
LUÔN báo đạt, che mất việc bộ lập lịch không chạy nổi.* Chốt ở đây tránh đúng kiểu đó bằng ba
điều **đo được**, không bằng lời hứa:

1. **`xoay_khoa` không bao giờ tự tạo gói backup.** Ca `test_d5` đo bằng **cây cú pháp**
   (`ast`), tìm mọi lượt **gọi** `tao_goi` trong `app/xoay_khoa.py` — phải rỗng.
   *(Lượt đầu ca này dùng `grep` và **báo hỏng oan**: nó bắt phải chữ `tao_goi()` nằm trong một
   dòng chú thích nói rằng không được gọi hàm đó. Đúng dạng §12.1 luật 3 — công cụ mình tự tay
   giới hạn cũng là công cụ cần nghi. Đổi sang `ast` thì nó chỉ thấy lượt gọi thật.)*
2. **C5** từ chối chứng nhận mang `pid` trùng tiến trình đang xoay (ca `test_b3`).
3. **C6** đòi một dòng audit do **`sao_luu_khoa`** — mô-đun khác, AG-01 sở hữu — ghi vào CSDL.

> **GIỚI HẠN, nói thẳng:** chốt này chặn được việc **quên**, **không** chặn được người có quyền
> ghi đĩa + ghi CSDL cố tình dựng bằng chứng giả. Bằng chứng thật sự độc lập là một lượt khôi
> phục trên **máy chủ sạch** bằng **passphrase thật** — blocker **B-2**, vẫn còn nguyên.

### Không bỏ qua được bằng một cờ môi trường

Yêu cầu trực tiếp của chỉ thị. Bốn phép đo:

| Ca | Đo gì |
|---|---|
| `test_d2` | đặt **10 biến môi trường** trông như cờ bỏ qua (`VIP_HUB_FORCE`, `SKIP_CHECKS`, `VIP_HUB_KHAN_CAP`…) rồi gọi `xoay_that()` — nó **vẫn từ chối** |
| `test_d3` | **chữ ký hàm** `xoay_that` không có tham số nào tên chứa `bo_qua/force/skip/khan_cap/no_/ep_` |
| `test_d4` | trong `app/xoay_khoa.py` chỉ có **đúng một** biến môi trường được đọc: `VIP_HUB_DATA` (chốt cách ly của tiến trình con). **Ca này cố ý đọc mã, và ghi rõ phạm vi của chính nó** |
| `test_d7` | **quyền kiểm trước chốt** — người không có quyền không dò được trạng thái chốt |

Vì sao viết thành luật: bản đầu của hầu hết chốt chặn đều có một *"lối thoát cho trường hợp
khẩn cấp"*. Trường hợp khẩn cấp là **đúng lúc** người ta dễ bỏ qua chốt nhất, và cũng là lúc
hậu quả nặng nhất. Muốn xoay khi chưa đủ điều kiện thì đi làm cho đủ: tạo gói, chạy chứng nhận.
Mất thêm vài phút, không mất dữ liệu.

---

## 5. SỐ ĐO — ĐÃ CHẠY THẬT

### 5.1 Bộ thử

`python3 app/thu/thu_xoay_khoa.py` → **`Ran 30 tests … OK`**, 15/10/2026.

> **Phạm vi câu "30/30 đạt"** (§12.1 luật 5): con số do `unittest` đếm, trên **một** file
> `app/thu/thu_xoay_khoa.py`, chạy trên **MacBook Pro**, `python3 3.9.6`, nền `VIP_HUB_DATA`
> là thư mục tạm. **NGOÀI phạm vi:** mọi bộ thử khác, mọi máy khác, mọi lượt chạy trên dữ liệu
> thật. Năm lớp: `A_Quyen` (6) · `B_Chot` (9) · `C_DienTapBanSao` (7) · `D_ChotKhongBoQuaDuoc`
> (7) · `E_XoayThatTrenNenCoLap` (1).

**Hồi quy toàn bộ Python**, cùng máy cùng ngày, `for f in app/thu/thu_*.py; do python3 "$f"; done`:

| Bộ | Kết quả |
|---|---|
| 22 bộ cũ + bộ mới | mọi bộ **OK**, **trừ một** |
| `thu_qa2_soat.py` | **FAILED (failures=1)** — `test_r40`, **do file mới của G12 gây ra**, xem mục 7 bản vá **P-G12-1** |
| `thu_e2e.py` | **KHÔNG CHẠY** lượt nào ở đợt này (chạy qua `chay_e2e.sh`, cần dựng máy chủ) — **chưa đo**, không phải đã đạt |

### 5.2 Diễn tập XOAY TRÊN BẢN SAO (D-2)

`python3 app/xoay_khoa.py dien-tap`, nền thử cô lập, 15/10/2026 10:19 +0700:

| Phép đo | Giá trị |
|---|---|
| `key_id` trước → sau | `goc` → `k-20261015-101912-6aff34` |
| Số tài khoản hãng | **6** |
| Bản mã được mã hoá lại | **6 credentials + 6 webhook secret** |
| Hỏng khi mã hoá lại | **0** |
| **Bản mã đo lại nội dung** | **12** (cả hai cột của cả 6 hàng) |
| **Giải lại KHỚP nguyên văn** | **12 / 12** |
| `ban_ma_LECH_noi_dung` | **rỗng** |
| `ban_ma_KHONG_giai_duoc_sau_xoay` | **rỗng** |
| Đường giải mã đã đo | **`giai_ma_cred` VÀ `giai_ma_wh`** — hai AAD khác nhau |
| **Khoá cũ bị xoá** | **rỗng** — số khoá 1 → 2, khoá `goc` còn nguyên |
| `key_id` còn sót sau xoay | **rỗng** |
| **Nguồn còn nguyên** | `true` — cùng tên file, cùng kích thước, cùng quyền |
| Bản sao sau khi xong | **đã xoá** (ca `test_c4`) |

**Phép đo quan trọng nhất là dòng "giải lại KHỚP", không phải dòng "số bản mã".** Số dòng khớp
**không** chứng minh xoay thành công: CSDL về đủ mà khoá lệch thì credentials thành rác,
`integrity_check` vẫn `ok`, và **không gì báo tới lượt gọi hãng đầu tiên**. Nên tiến trình con
tính **digest sha256 của plaintext trước và sau** rồi so — và **chỉ số đếm đi ra ngoài tiến
trình con**, không plaintext, không digest.

**Cách ly là do hệ điều hành cưỡng chế, không do nhớ:** lượt xoay chạy trong **tiến trình con**
với `VIP_HUB_DATA` riêng. Lý do đo được: `secret_provider` giữ một nhà cung cấp dùng chung cho
cả tiến trình, `csdl` giữ kết nối theo thread trỏ vào `cau_hinh.DUONG_DAN_CSDL` tính lúc
import, và `bao_mat._khoa_noi_bo()` đọc `cau_hinh.DUONG_DAN_KHOA`. Lắp lại ba thứ đó trong
tiến trình đang chạy là vá tạm, và **một chỗ sót là lượt "diễn tập" ghi vào dữ liệu thật**.
Tiến trình con còn có **chốt riêng**: thiếu `VIP_HUB_DATA` hoặc nó trỏ vào thư mục dữ liệu mặc
định thì thoát **mã 9** (ca `test_c6`, `test_c7`).

### 5.3 Diễn tập KHÔI PHỤC (D-3) — một lệnh

`sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh` → **mã thoát 0**, 15/10/2026 10:19 +0700.
Nền thử: `/var/folders/…/veh-dientap-khoa.UNhk6R/du-lieu`.

| Bước | Phép đo | Kết quả |
|---|---|---|
| B3 tạo gói | kích thước · số khoá · quyền | **2 095 byte** · 1 khoá (`goc`) + khoá cũ · **`0o600`** |
| B4 **kiểm gói TRƯỚC khi tin** | `sao_luu_khoa.py kiem` | `dat: true`, `loi: []`, `key_id_thieu: []`, 6 bản mã, 2 tenant |
| B5 chứng nhận khôi phục | khôi phục vào thư mục **cô lập**, giải mã lại | `ket_qua: dat` · `khoi_phuc.dat: true`, 1 khoá ghi, con trỏ `goc` |
| B5 — **giải mã lại** | **cả hai** đường | **cred 6/0 · webhook 6/0** (đạt/hỏng) |
| B6 chốt | 6 điều kiện | **C1…C6 đều ĐẠT** |
| B7 diễn tập bản sao | mục 5.2 | đạt |
| B8 **xoay thật trên NỀN THỬ** | nghiệm thu sau xoay | 6 cred + 6 wh mã hoá lại, giải lại **6/0 và 6/0**, `khoa_cu_bi_mat: []` |
| B9 gói cũ sau khi xoay | chốt phải **TỪ CHỐI** | từ chối, `chua_dat: ['C2']` — **đúng như mong đợi** |
| B10 | thư mục dữ liệu mặc định của repo | **KHÔNG TỒN TẠI** |

**Chứng nhận không chứa bí mật** — ca `test_b9` quét **byte thô** file chứng nhận tìm nội dung
mọi khoá, credentials và passphrase ở **ba dạng** (thô · hex · base64): **rỗng**. Đây là phép đo
**độc lập với việc mã hoá**: nó không hỏi *"đã mã hoá chưa"*, nó hỏi *"chuỗi bí mật có xuất hiện
trong file không"*.

### 5.4 Đường đưa gói ra ngoài — đã chạy, chưa ghi thật ra đâu cả

| Ca | Lệnh | Kết quả |
|---|---|---|
| chạy khô | `… --chay-kho` | K1…K5 chạy, **0 lỗi 1 cảnh báo** (K5: đích cùng ổ với gói), **không ghi gì** |
| **chưa có công tắc** | không tham số | **mã thoát 7**, in màn hình dừng 4 câu hỏi, **không ghi gì** |
| đích trong `assets/` | `--toi-da-doc-va-dong-y` | **TỪ CHỐI** (static đang phục vụ ⇒ tải về bằng GET vô danh), không tạo thư mục nào |
| ghi thật vào thư mục tạm | `--toi-da-doc-va-dong-y` | ghi `0600` trong thư mục `0700`, **sha256 khớp hai đầu**, mã thoát 0 |

Lượt "ghi thật" trên chỉ ghi vào **thư mục tạm của phiên này**, đã dọn. **Chưa có gói khoá nào
rời khỏi máy này.**

---

## 6. VIP VAULT — QUY TRÌNH VÀ CHỖ SCRIPT DỪNG LẠI HỎI

Quy trình đầy đủ: `trien_khai/sao_luu_ngoai/README.md` mục 4–6.

**Chỗ dừng:** `dua-goi-khoa-ra-ngoai.sh` thoát **mã 7** và **không ghi gì**, trừ khi có **một**
trong hai: file công tắc `trien_khai/sao_luu_ngoai/TOI-DA-DOC-VA-DONG-Y` (**do người tạo** — nó
không có trong repo và không script nào được tự tạo), hoặc tham số `--toi-da-doc-va-dong-y`.

**Script không có đường nào nối tới VPS.** Chỉ thị cấm deploy VPS, nên nó chỉ chép vào một thư
mục trên máy đang chạy rồi **in ra** lệnh `rsync` kèm sha256 mong đợi, để anh tự chạy và tự
nghiệm thu ở đầu bên kia.

### Gói khoá CHƯA nằm trong phạm vi VIP Vault — cần quyết định của anh

`CLAUDE.md` §19.4: từ 27/09/2026 hệ sao lưu **duy nhất** là VIP Vault (`/opt/vip-vault`, 5 timer
systemd, kho chính là NAS). Nó **tự dò CSDL SQLite** và **dump PostgreSQL**.

> Gói khoá `.vipkb` **không phải** SQLite, **không phải** PostgreSQL, và chưa ai thêm nó vào
> `/etc/vip-vault/config.yml`. **CHƯA ĐO — đừng giả định nó tự được sao lưu.**

Hai hướng, cái giá của từng hướng ở `README.md` mục 6. AG-05 **không tự chọn**: chọn hướng (a)
là chạm vào hệ sao lưu đang chạy trên VPS. Nếu anh chọn (a) thì **phải quyết thêm hai điều cùng
lúc**, không để sau:

1. **Mức giữ khi xoay vòng.** Gói khoá khác bản dump CSDL ở một điểm sống còn: một gói khoá
   **cũ** vẫn mở được bản mã cũ, nên xoá nó không giống xoá một bản dump thừa.
2. **Chỗ giữ passphrase.** VIP Vault chép **file**; nó không biết gì về passphrase. Gói trên NAS
   mà passphrase mất là NAS đang giữ một file vô dụng.

### Rủi ro gốc, nói thẳng

**Hôm nay gói khoá nằm cùng máy với CSDL nó bảo vệ. Mất ổ là mất cả hai, và không còn đường về.
Đó chính là lý do D-3 tồn tại, và nó CHƯA được vá** — mọi thứ G12 dựng mới chỉ là cái đường để
vá, chưa phải lượt vá.

---

## 7. BẢN VÁ ĐỀ XUẤT — MÔ TẢ, KHÔNG SỬA

### P-G12-1 — `app/thu/thu_qa2_soat.py`: thêm MỘT dòng miễn cho `xoay_khoa.py` (ĐANG LÀM BỘ THỬ ĐỎ)

**Đã đo bằng lệnh, không suy từ đọc mã.** `python3 app/thu/thu_qa2_soat.py` →
`FAILED (failures=1)`, ca `test_r40_ANTOAN_sql_cham_bang_co_tenant_id_deu_co_dieu_kien_tenant`,
**3 phát hiện**, cả 3 đều là `('xoay_khoa.py', 'carrier_accounts', …)`.

Ba câu SQL đó **cố ý** không lọc tenant — xoay khoá và nghiệm thu sau xoay phải phủ **mọi**
tenant; lọc theo tenant là bỏ sót bản mã của tenant khác dưới khoá cũ, đúng kiểu mất im lặng.
Cùng một lý do đã được miễn sẵn cho `bao_mat.py`, `sao_luu_khoa.py` và `migrate.py`.

AG-05 **không sở hữu** `app/thu/thu_qa2_soat.py`, nên **không sửa**. Thêm đúng một mục vào
`MIEN`:

```python
("xoay_khoa.py", "carrier_accounts"):
    "xoay khoá có kiểm soát: CỐ Ý chạy trên MỌI tenant — mã hoá lại mà lọc theo tenant thì "
    "bản mã của tenant khác ở lại dưới khoá cũ và không gì báo. KIỂM ĐƯỢC: `grep xoay_khoa "
    "app/server.py` ra rỗng ⇒ module KHÔNG có cửa HTTP nào, chỉ gọi được từ dòng lệnh của "
    "PLATFORM_OWNER. Cùng loại miễn với bao_mat.py và sao_luu_khoa.py ngay trên.",
```

**Đã đo lượt vá:** chèn đúng mục này rồi chạy lại → `Ran 49 tests … OK (skipped=1)`; sau đó
**khôi phục nguyên trạng** file (`git status` chỉ còn ba đường mới của G12). Tức là **một mục
là đủ**, không cần sửa gì khác.

### P-G12-2 — `app/quyen.py`: seed quyền mới (AG-00)

```python
# trong QUYEN:
"platform.khoa.xoay": "Xoay khoá mã hoá nền tảng (chỉ PLATFORM_OWNER)",
# trong MA_TRAN["PLATFORM_OWNER"]: thêm "platform.khoa.xoay"
# MA_TRAN["PLATFORM_ADMIN"]: KHÔNG thêm.
```

Chưa seed thì `xoay_that()` từ chối **ngay cả với OWNER** (ca `test_a2`) — đó là hành vi đúng,
không phải lỗi.

### P-G12-3 — `app/server.py`: **KHÔNG mở cửa HTTP** (bản vá dạng "đừng làm")

Khuyến nghị của AG-01 ở `docs/G07_G11_FINAL_REPORT.md` D-2 là mở
`POST /api/v2/platform/khoa/xoay` cho `PLATFORM_OWNER`. **AG-05 khuyến nghị CHƯA mở, lý do đo
được:**

| | |
|---|---|
| **Bảng route nếu sau này mở** | `POST /api/v2/platform/khoa/xoay` · quyền `platform.khoa.xoay` · chỉ `PLATFORM_OWNER` · `200`/`403`/`409` · gọi `xoay_khoa.xoay_that(nc=nc, …)` · **bắt buộc** `X-Requested-With: VIPHub` như mọi đường ghi · body chỉ mang `duong_goi`, **tuyệt đối không mang passphrase** |
| **Vì sao chưa nên mở** | chốt C2/C3 cần **mở gói**, mà mở gói cần **passphrase**. Passphrase đi qua body HTTP là đi vào bộ nhớ tiến trình web, vào mọi tầng proxy, và có ngày vào log. Đó đúng là điều AG-01 đã cảnh báo cho đường **sao lưu**, và nó áp y nguyên cho đường **xoay** |
| **Mở thế nào cho đúng, nếu anh muốn có nút bấm** | tách đôi: HTTP chỉ **đọc trạng thái chốt** (`GET …/khoa/chot`, không cần passphrase vì C1/C5/C6 đọc được mà không mở gói); còn lượt **xoay** vẫn chạy từ dòng lệnh trên máy chủ. Người bấm nhìn thấy "còn thiếu C2" mà không ai phải gửi bí mật qua mạng |
| **Trạng thái hôm nay** | `grep -n "xoay_khoa" app/server.py` → **rỗng**. Mô-đun **không có cửa HTTP nào** |

---

## 8. KHOÁ THẬT KHÔNG BỊ ĐỤNG — BẰNG CHỨNG

`app/du-lieu/` **không tồn tại trong worktree này** (nó bị `.gitignore` chặn và chưa lượt nào
tạo ra). Thư mục khoá thật của bản triển khai nằm ở `~/Projects/vip-express-hub/app/du-lieu/khoa/`.

**Trước** khi bắt đầu (`stat`, 15/10/2026 ~10:04 +0700) và **sau** khi xong mọi lượt đo:

| File | Quyền | Byte | `mtime` |
|---|---|---|---|
| `goc.key` | `-rw-------` | 32 | 14/10/2026 23:35:08 |
| `hien-hanh` | `-rw-------` | 24 | 14/10/2026 23:35:28 |
| `k-20261014-233528-b08d5c.key` | `-rw-------` | 32 | 14/10/2026 23:35:28 |

**Giống hệt nhau cả ba cột.** `mtime` vẫn là của **14/10**, tức là không lượt nào trong phiên
15/10 ghi vào đó. **Không đọc nội dung khoá, không ghi sha256 của khoá vào tài liệu này** — kích
thước + quyền + `mtime` đủ để chứng minh không-chạm, và sha256 của một khoá là thứ không cần
nằm trong tài liệu.

> **Phạm vi câu "không bị đụng"** (§12.1 luật 5): đo bằng `ls -l` + `stat` trên **một** thư mục
> `~/Projects/vip-express-hub/app/du-lieu/khoa/`, trên **MacBook Pro**, so hai mốc trong cùng
> phiên. **NGOÀI phạm vi:** thư mục khoá trên Mac mini, trên VPS, và mọi bản sao khác — AG-05
> không với tới và **không nói gì** về chúng.

---

## 9. GIỚI HẠN VÀ **BLOCKED** — mỗi mục nêu chính xác cái còn thiếu

| # | Mục | Trạng thái | Thiếu chính xác cái gì |
|---|---|---|---|
| 1 | **Xoay khoá THẬT** | **BLOCKED** | `V-13906-02` chưa cấp. Và kể cả khi cấp, chốt C1…C6 vẫn phải đạt trước |
| 2 | **Gói khoá có bản ngoài máy** | **BLOCKED** | `V-13906-03` chưa cấp; chưa chọn (a) hay (b) ở mục 6; chưa có passphrase thật do Owner giữ |
| 3 | **Khôi phục trên máy chủ sạch** | **BLOCKED (B-2)** | một máy chủ sạch + passphrase thật. Diễn tập local đạt **không** chứng minh điều này |
| 4 | **Quyền `platform.khoa.xoay`** | **CHỜ AG-00** | bản vá P-G12-2 |
| 5 | **Bộ thử `thu_qa2_soat` đang ĐỎ** | **CHỜ chủ file** | bản vá P-G12-1, một mục `MIEN`. Đã đo là đủ |
| 6 | **Cửa HTTP để xoay khoá** | **CỐ Ý KHÔNG MỞ** | xem P-G12-3. Hôm nay chỉ chạy được từ dòng lệnh |
| 7 | **Chốt chống người cố tình** | **KHÔNG CÓ, và nói ra** | chốt chặn *quên*, không chặn người có quyền ghi đĩa + ghi CSDL dựng bằng chứng giả. Vá đúng: chứng nhận ký bằng khoá của một bên thứ ba, hoặc khôi phục có người thứ hai chứng kiến |
| 8 | **Cơ chế nhắc gói quá cũ** | **KHÔNG CÓ** | không ai bị báo khi gói gần nhất đã cũ. Vá đúng là nối vào `canh-bao.py` trên VPS — **chạm VPS**, ngoài phạm vi G12 |
| 9 | **Một passphrase, một người giữ** | **rủi ro cố ý chấp nhận** | ai mở được gói là giải được **mọi** bản mã của **mọi** tenant. Chưa có chia mảnh (Shamir), chưa có nhiều người cùng giữ |
| 10 | **`ban_ma[]` chỉ phủ `carrier_accounts`** | **giới hạn kế thừa** | thêm bảng nào có secret mã hoá thì phải thêm vào `sao_luu_khoa._thu_gom_ban_ma()` **và** `xoay_khoa.key_id_dang_dung()` **và** `bao_mat.ma_hoa_lai_carrier_accounts()` — **ba chỗ**, quên một là bỏ sót im lặng. Đây là chỗ hỏng im lặng rõ nhất còn lại |
| 11 | **`KMSSecretProvider` vẫn rỗng** | **cố ý** | khoá còn nằm trong file trên đĩa. G12 **giữ nguyên** chủ ý đó, không dựng KMS giả |
| 12 | **Chưa đo trên dữ liệu lớn** | **chưa đo** | diễn tập chạy trên **6** tài khoản hãng. Lượt xoay thật mã hoá lại từng hàng trong một vòng lặp không có giao dịch bao ngoài — với hàng nghìn tài khoản thì thời gian và hành vi khi đứt giữa chừng **chưa ai đo** |

### Rủi ro cố ý bỏ qua — ghi ra kèm cách vá đúng

- **Mục 10 (ba chỗ phải sửa cùng lúc)** là một cấu trúc sẽ hỏng lần thứ hai theo cùng một kiểu.
  Theo `CLAUDE.md` §12.2 (*hỏng lần thứ hai thì ĐỔI CẤU TRÚC*), cách vá đúng là một **nơi duy
  nhất khai báo "cột nào chứa secret mã hoá"**, rồi ba hàm kia đọc từ đó. G12 **không làm**, vì
  nó phải sửa `bao_mat.py` và `sao_luu_khoa.py` — hai file AG-05 không sở hữu. **Đề xuất cho
  AG-01.**
- **Chứng nhận khôi phục là file thường trên đĩa.** Ai ghi được đĩa thì sửa được nó. C6 (audit
  trong CSDL) bù một phần, nhưng ai ghi được CSDL cũng sửa được. Đã ghi ở mục 4 và mục 9 dòng 7.
- **`dien_tap()` chép cả `hub.db-wal`.** Nếu có tiến trình khác đang ghi CSDL đúng lúc chép thì
  bản sao có thể bắt được một trạng thái giữa chừng. Với diễn tập thì **chấp nhận được** (nó chỉ
  làm sai số đếm, không làm hỏng nguồn), nhưng **không** dùng cách chép này cho sao lưu thật —
  sao lưu thật phải đi qua `sqlite3.Connection.backup()` như `migrate.sao_luu()` đang làm.
