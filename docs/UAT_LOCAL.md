# UAT LOCAL — VIP EXPRESS HUB

**Tự nghiệm thu trên máy của bạn, với dữ liệu RIÊNG, không dùng dữ liệu thật.**

Bộ script trong `trien_khai/uat/` dựng một bản UAT local hoàn toàn tách biệt:

- dữ liệu nằm trong thư mục riêng `~/veh-uat` (không phải `app/du-lieu`, không phải `/du-lieu`);
- máy chủ chỉ nghe `127.0.0.1`, cổng do hệ điều hành cấp;
- tài khoản là **FIXTURE** (mật khẩu sinh ngẫu nhiên, ghi vào file riêng, không phải mật khẩu thật);
- mọi adapter hãng ở `mock` với `live_mo=False` — **không gọi API hãng, kể cả sandbox**;
- dừng bằng **đúng PID đã ghi**, không dùng `pkill`/`killall` theo khuôn.

> **Đây không phải bản production.** Không mở cổng ra ngoài, không dùng credentials thật, không tạo
> đơn thật, không trỏ vào dữ liệu thật. Mọi tên/SĐT/địa chỉ/mã vận đơn trong tài liệu này là hư cấu.

---

## 1. Cam kết an toàn của bộ script

| Hạng mục | Cách làm | Chốt chặn |
|---|---|---|
| Thư mục dữ liệu | mặc định `~/veh-uat` (mode `0700`) | TỪ CHỐI nếu nằm trong repo, trong bất kỳ cây git, là `app/du-lieu`, `/du-lieu`, thư mục nhà, hoặc thư mục không rỗng mà không có dấu UAT |
| Dấu UAT | `~/veh-uat/.veh-uat-fixture.json` (`loai=VEH-UAT-FIXTURE`, ghi đường dẫn repo) | Không có dấu ⇒ không ghi tiếp, không xoá |
| Mạng | `VIP_HUB_BIND=127.0.0.1`, cổng `0` (OS cấp) | Script đọc cổng thật từ log, kiểm `lsof` thấy `127.0.0.1:<cổng>`; từ chối nếu thấy `0.0.0.0`/`*` |
| Hãng vận chuyển | `VIP_JT_MOI_TRUONG=mock`; adapter `CHO_PHEP_LIVE=False` | Script từ chối nếu biến môi trường là `sandbox`/`production`; kiểm CSDL `live_mo=0`, `moi_truong='mock'` |
| Credentials | không có credentials thật; carrier account seed là dữ liệu demo mã hoá | Không đọc/ghi file `.env`, không dùng biến credentials hãng, không in mật khẩu ra terminal |
| Tài khoản | 9 tài khoản fixture, mật khẩu sinh ngẫu nhiên bởi `app/khoi_tao.py` | File `~/veh-uat/TAI-KHOAN-UAT.md` mode `0600`; nội dung ghi rõ **FIXTURE — KHÔNG PHẢI MẬT KHẨU THẬT** |
| Dừng | đọc PID + cổng + lstart trong `~/veh-uat/uat.dang-chay` | Chỉ gửi tín hiệu tới đúng PID; kiểm health pid, `ps` (user/lstart/command), `lsof`; không khớp ⇒ TỪ CHỐI kill |
| Dữ liệu thật | không bao giờ đặt `VIP_HUB_DATA` mặc định | TỪ CHỐI nếu `VIP_HUB_DATA` đang trỏ khác thư mục UAT; `app/du-lieu` không bị đọc/ghi |
| Cờ nguy hiểm | `VIP_HUB_RESET_TOKEN=0` | TỪ CHỐI nếu ai đó đặt `=1` (lỗ hổng chiếm tài khoản) |

---

## 2. Yêu cầu

- macOS hoặc Linux, shell `bash`.
- Python 3.8+ (sản phẩm đã yêu cầu Python; bộ script dùng thêm `sqlite3` của Python).
- Repo đã được checkout đầy đủ (có `app/`, `admin/`, `trien_khai/uat/`).
- Không cần cài thêm gói. `sqlite3` CLI và `lsof` là tuỳ chọn — thiếu vẫn chạy, chỉ mất một phép kiểm.
- **Không** đặt sẵn `VIP_HUB_DATA`, `VIP_HUB_BIND`, `VIP_JT_MOI_TRUONG` trong shell. Nếu có, xem mục 11.

---

## 3. Khởi động

Từ thư mục gốc repo:

```bash
cd /duong/dan/toi/vip-express-hub
./trien_khai/uat/khoi_dong.sh
```

Lần đầu script sẽ:

1. tạo `~/veh-uat/` (mode `0700`) + dấu UAT;
2. chạy `app/migrate.py` để dựng schema **trên thư mục UAT**;
3. chạy `app/khoi_tao.py` để seed 9 tài khoản fixture + 2 tenant + tài khoản hãng mock;
4. seed thêm dữ liệu mẫu (khách hàng, 10 đơn, audit, usage);
5. khởi động máy chủ ở `127.0.0.1`, cổng do OS cấp;
6. gọi thật `GET /api/v2/suc-khoe` qua loopback và đối chiếu `pid` health với PID đã spawn;
7. ghi `~/veh-uat/uat.dang-chay` để `dung.sh` dừng đúng tiến trình.

Kết quả cuối trông như sau (PID/cổng thay đổi mỗi lần):

```text
[uat] ======================================================================
[uat] ĐÃ SẴN SÀNG — UAT LOCAL
[uat]   URL        : http://127.0.0.1:54321/admin/
[uat]   PID        : 12345  (đã ghi vào /Users/ban/veh-uat/uat.dang-chay)
[uat]   Dữ liệu    : /Users/ban/veh-uat  (thư mục RIÊNG, marker .veh-uat-fixture.json)
[uat]   Tài khoản  : /Users/ban/veh-uat/TAI-KHOAN-UAT.md  (mật khẩu FIXTURE, KHÔNG phải thật)
[uat]   Hãng       : mock — mọi adapter live_mo=False, KHÔNG gọi API hãng
[uat]   Nhật ký    : /Users/ban/veh-uat/nhat-ky/may-chu.log
[uat]   Dừng       : /duong/dan/toi/repo/trien_khai/uat/dung.sh
[uat] ======================================================================
```

Mở URL ở dòng `URL` (thường là `http://127.0.0.1:<cổng>/admin/`).

Nếu muốn dùng thư mục khác (ví dụ ổ ngoài), đặt `VIP_UAT_DATA` **khi khởi động** và dùng đúng biến đó
cho `dung.sh`/`xoa_du_lieu.sh`:

```bash
VIP_UAT_DATA="$HOME/veh-uat-2" ./trien_khai/uat/khoi_dong.sh
```

Thư mục mới vẫn phải ở ngoài repo và không được là `app/du-lieu`/`/du-lieu`.

Cổng **không cố định**. Muốn biết cổng đang dùng:

```bash
sed -n 's/^port=//p' ~/veh-uat/uat.dang-chay
```

---

## 4. Đăng nhập — tài khoản FIXTURE

Mật khẩu được sinh ngẫu nhiên ở lần tạo dữ liệu đầu tiên và chỉ nằm trong:

```bash
~/veh-uat/TAI-KHOAN-UAT.md
```

File này mode `0600`, có dòng đầu ghi rõ:

> **MẬT KHẨU DƯỚI ĐÂY LÀ FIXTURE — KHÔNG PHẢI MẬT KHẨU THẬT.**

Các tài khoản (tên đăng nhập cố định):

| Tên đăng nhập | Vai trò | Phạm vi | Dùng cho |
|---|---|---|---|
| `platform-owner` | `PLATFORM_OWNER` | nền tảng | màn Tenants, Quản trị gói, Vai trò & quyền, Audit nền tảng |
| `platform-admin` | `PLATFORM_ADMIN` | nền tảng | kiểm quyền quản trị không có quyền đổi gói/tạo tenant |
| `shopa-owner` | `TENANT_OWNER` | Shop Demo A | toàn bộ màn tenant của Shop A |
| `shopa-staff` | `TENANT_STAFF` | Shop Demo A | kiểm màn bị ẩn/chặn do thiếu quyền |
| `shopa-viewer` | `TENANT_VIEWER` | Shop Demo A | kiểm chế độ chỉ xem |
| `da-tenant` | `TENANT_ADMIN` (Shop A) + `TENANT_VIEWER` (Shop B) | cả hai tenant | kiểm **đổi tenant** trên header |
| `shopb-owner` | `TENANT_OWNER` | Shop Demo B | kiểm tenant thứ hai |
| `shopb-staff` | `TENANT_STAFF` | Shop Demo B | kiểm quyền nhân viên |
| `shopb-viewer` | `TENANT_VIEWER` | Shop Demo B | kiểm chỉ xem |

Gợi ý: bắt đầu bằng `shopa-owner`, sau đó đăng xuất và đăng nhập `platform-owner` để xem màn nền tảng.

> **Lưu ý:** màn đăng nhập của giao diện có dòng gợi ý `app/du-lieu/TAI-KHOAN-DEMO.md`. Đó là đường dẫn
> của bản chạy mặc định, **không phải UAT**. Với UAT, dùng `~/veh-uat/TAI-KHOAN-UAT.md` như trên.

Nếu làm mất file mật khẩu: không khôi phục được (mật khẩu băm một chiều). Hãy dừng, xoá dữ liệu UAT
(mục 8) rồi khởi động lại để nhận bộ tài khoản mới.

---

## 5. Dữ liệu mẫu gồm những gì

Tất cả đều là dữ liệu hư cấu, chỉ nằm trong `~/veh-uat/hub.db`:

| Nhóm | Số lượng | Ghi chú |
|---|---|---|
| Tenant | 2 | `shop-a` = Shop Demo A, `shop-b` = Shop Demo B, gói `basic` |
| Người dùng | 9 | bảng tài khoản ở mục 4 |
| Khách hàng | 6 | 1 khách seed gốc mỗi tenant + 2 khách fixture mỗi tenant |
| Tài khoản hãng | 4 | `vtp` + `jt` cho mỗi tenant; `moi_truong='mock'`; `live_mo=0` |
| Nhà vận chuyển | 2 | `vtp`, `jt` — capability lấy từ adapter, không gọi mạng |
| Đơn hàng | 10 | 7 đơn Shop A + 3 đơn Shop B, đủ trạng thái để xem luồng |
| Lịch sử đơn | 19 dòng | nguồn `uat-seed`, ghi rõ “fixture, không gửi hãng” |
| Audit | 3 | 1 seed gốc + 2 `uat_seed` theo tenant |
| Usage tháng | 2 | mỗi tenant 3 đơn đã gửi (để màn Gói & usage có số) |

### Danh sách đơn mẫu

| Mã đơn | Tenant | Trạng thái nghiệp vụ | Trạng thái giao | Hãng | COD | Mã vận đơn |
|---|---|---|---|---|---|---|
| `UAT-A-001` | Shop A | `nhap` | — | — | 0 | — |
| `UAT-A-002` | Shop A | `da_duyet` | — | vtp | 199.000 | — |
| `UAT-A-003` | Shop A | `dang_gui` | — | vtp | 320.000 | — |
| `UAT-A-004` | Shop A | `da_gui` | `cho_lay` | vtp | 250.000 | `MOCK-UAT-A-004` |
| `UAT-A-005` | Shop A | `da_gui` | `dang_giao` | jt | 0 | `MOCK-UAT-A-005` |
| `UAT-A-006` | Shop A | `da_gui` | `giao_thanh_cong` | jt | 450.000 | `MOCK-UAT-A-006` |
| `UAT-A-007` | Shop A | `huy` | — | — | 0 | — |
| `UAT-B-001` | Shop B | `da_gui` | `lay_hang` | vtp | 120.000 | `MOCK-UAT-B-001` |
| `UAT-B-002` | Shop B | `da_gui` | `giao_that_bai` | jt | 0 | `MOCK-UAT-B-002` |
| `UAT-B-003` | Shop B | `da_gui` | `hoan_hang` | vtp | 0 | `MOCK-UAT-B-003` |

Mọi mã vận đơn bắt đầu bằng `MOCK-UAT-` để không ai nhầm với vận đơn thật. Không có lệnh gọi hãng nào
được thực hiện để tạo các dòng này — chúng được ghi thẳng vào CSDL UAT.

---

## 6. Checklist UAT

Đánh dấu từng mục khi xem. Cột “Tài khoản” là tài khoản nên dùng để thấy đúng màn.

### 6.1. Đăng nhập / phiên

| # | Việc làm | Tài khoản | Kỳ vọng |
|---|---|---|---|
| 1 | Mở `http://127.0.0.1:<cổng>/admin/`, đăng nhập | `shopa-owner` | Vào Tổng quan, header hiện **Shop Demo A**, vai trò `TENANT_OWNER` |
| 2 | Đăng xuất rồi đăng nhập lại | `shopa-owner` | Về màn đăng nhập; đăng nhập lại được; không lộ mật khẩu trong URL/log |
| 3 | Đăng nhập sai mật khẩu 1 lần | `shopa-owner` | Báo sai tên/mật khẩu; không lộ tài khoản có tồn tại hay không |
| 4 | Đăng nhập `da-tenant`, đổi tenant trên header | `da-tenant` | Đổi được giữa Shop A (`TENANT_ADMIN`) và Shop B (`TENANT_VIEWER`); menu đổi theo quyền |

### 6.2. Các màn tenant (dùng `shopa-owner`)

| # | Màn | Việc làm | Kỳ vọng |
|---|---|---|---|
| 5 | Tổng quan | Xem thẻ số liệu, biểu đồ, hoạt động gần đây | Có 7 đơn Shop A; biểu đồ không lỗi; audit có mục `uat_seed` |
| 6 | Đơn hàng | Xem danh sách, lọc `trang_thai`, mở chi tiết `UAT-A-006` | 7 đơn; `UAT-A-006` hiện `da_gui` / `giao_thanh_cong`, COD 450.000, mã `MOCK-UAT-A-006` |
| 7 | Đơn hàng | Thử lọc theo hãng `vtp`/`jt`, khoảng COD, ngày | Bộ lọc chạy; không có đơn nào bị tạo mới ngoài ý muốn |
| 8 | Đơn hàng | Xuất CSV | Tải file CSV; mở được; không có công thức độc hại trong ô |
| 9 | Tạo đơn | Tạo một đơn nháp với thông tin hư cấu | Đơn mới xuất hiện trong danh sách, trạng thái `nhap`; **không** gọi hãng, không sinh vận đơn thật |
| 10 | Khách hàng | Xem danh sách, thêm một khách hư cấu | Có 3 khách Shop A; thêm được; dữ liệu chỉ nằm trong CSDL UAT |
| 11 | Import file | Tải `mock/import-sample.csv`, xem bước parse/validate | Batch hiện ra; dòng lỗi/không lỗi được đánh dấu; không gửi hãng |
| 12 | Hãng vận chuyển | Xem VTP/J&T và tài khoản hãng | 2 tài khoản (`vtp`, `jt`), môi trường `mock`; không có nút/đường nào gọi sandbox/production |
| 13 | Kết nối J&T | Xem trạng thái kết nối | Hiện mock/chưa cấu hình credentials thật; không có kết nối mạng ra ngoài |
| 14 | Webhook | Xem danh sách sự kiện | Trạng thái rỗng là bình thường (chưa có callback); không có endpoint công khai |
| 15 | Thành viên | Xem danh sách thành viên Shop A | 4 thành viên: owner, staff, viewer, `da-tenant` |
| 16 | Gói & usage | Xem gói, usage, cảnh báo hạn mức | Gói `basic`; usage tháng hiện 3 đơn đã gửi; không có hoá đơn thật |
| 17 | Bảng COD | Xem COD từng đơn và tổng | Có `UAT-A-004` 250.000 và `UAT-A-006` 450.000; số tổng khớp |
| 18 | Đợt đối soát / Bảng kê / Chênh lệch | Mở các màn tài chính | Trạng thái rỗng/không có đợt là bình thường; không lỗi 500; không gọi hãng |
| 19 | Trợ lý AI | Mở các màn AI | Các màn dựng được; thao tác AI là local/mock; không gọi nhà cung cấp AI bên ngoài |
| 20 | Sức khoẻ hệ thống | Xem health/readiness | Health 200; readiness báo rõ từng phép kiểm; worker webhook sống |
| 21 | Nhật ký | Xem audit của tenant | Có mục `uat_seed`; thao tác đăng nhập/tạo đơn của bạn cũng được ghi |
| 22 | Cài đặt | Xem thông tin phiên/cài đặt | Hiển thị đúng user/tenant; **không** đổi mật khẩu fixture nếu muốn giữ nguyên bộ tài khoản |

### 6.3. Màn nền tảng (dùng `platform-owner`)

| # | Màn | Việc làm | Kỳ vọng |
|---|---|---|---|
| 23 | Tenants | Xem danh sách tenant | 2 tenant `shop-a`, `shop-b`; gói `basic` |
| 24 | Quản trị gói | Xem các gói | 3 gói: `free`, `basic`, `pro`; không sửa dữ liệu thật |
| 25 | Vai trò & quyền | Xem ma trận 6 vai trò | 6 vai trò; quyền đọc từ CSDL, không hard-code ở UI |
| 26 | Audit nền tảng | Xem nhật ký nền tảng | Có mục seed; không lộ mật khẩu/token |
| 27 | Phân quyền | Đăng nhập `shopa-staff`/`shopa-viewer` | Màn không đủ quyền bị ẩn; gọi thẳng API vẫn bị backend chặn 403 |

### 6.4. Kiểm tra an toàn cuối buổi

| # | Việc làm | Kỳ vọng |
|---|---|---|
| 28 | `lsof -nP -iTCP:<cổng> -sTCP:LISTEN` | Chỉ thấy `127.0.0.1:<cổng>`, **không** thấy `0.0.0.0`/`*` |
| 29 | Mở `http://<IP-máy-bạn>:<cổng>/admin/` từ máy khác | **Không kết nối được** (chỉ loopback) |
| 30 | `sqlite3 ~/veh-uat/hub.db "select ma,live_mo from carrier_providers;"` | `jt|0`, `vtp|0` |
| 31 | `sqlite3 ~/veh-uat/hub.db "select id,hang,moi_truong from carrier_accounts;"` | Tất cả `mock`; không có credentials thật |
| 32 | Kiểm tra `app/du-lieu` trên repo | Không bị tạo/sửa bởi bộ script UAT |

---

## 7. Dừng

```bash
./trien_khai/uat/dung.sh
```

Nếu đã dùng `VIP_UAT_DATA` khác khi khởi động, truyền đúng biến đó:

```bash
VIP_UAT_DATA="$HOME/veh-uat-2" ./trien_khai/uat/dung.sh
```

Script đọc `~/veh-uat/uat.dang-chay` và:

1. kiểm PID còn sống;
2. xác thực **ba nguồn độc lập**: health của máy chủ báo đúng `pid`; `ps` khớp user + `lstart` + dòng
   lệnh nếu `ps` dùng được; `lsof` thấy đúng PID nghe `127.0.0.1:<cổng>`;
3. gửi `SIGTERM` tới **đúng PID**; chờ tối đa 20 giây; chỉ khi vẫn sống mới `SIGKILL` **cùng PID đó**;
4. kiểm lại bằng `kill -0` (không còn tiến trình) và kết nối TCP loopback (cổng đã đóng);
5. xoá file trạng thái, **không xoá dữ liệu**.

Kết quả mẫu:

```text
[uat] Xác thực health: pid=12345 khớp PID đã ghi.
[uat] Gửi SIGTERM tới ĐÚNG PID 12345 (cổng 54321)...
[uat] Cổng 127.0.0.1:54321 đã đóng — không còn ai nghe.
[uat] Không còn tiến trình nào chạy .../app/server.py.
[uat] ĐÃ DỪNG UAT LOCAL
[uat]   PID 12345 : không còn tồn tại (kiểm bằng kill -0)
```

Tự kiểm lại (không đoán):

```bash
PID=$(sed -n 's/^pid=//p' ~/veh-uat/uat.dang-chay)   # nếu state còn
kill -0 "$PID" 2>/dev/null && echo "CÒN SỐNG" || echo "ĐÃ DỪNG"
```

> **Không dùng `pkill -f server.py`.** Lệnh đó giết mọi tiến trình khớp chuỗi, kể cả máy chủ thật của
> người khác. Nếu `dung.sh` từ chối kill vì PID không khớp thân phận, hãy xem `ps -p <PID> -o pid,command`
> và xử lý tay — đừng kill theo khuôn.

---

## 8. Xoá sạch dữ liệu UAT

Dừng trước, rồi:

```bash
./trien_khai/uat/dung.sh
./trien_khai/uat/xoa_du_lieu.sh
```

Script hỏi gõ đúng chữ `xoa`. Trong script tự động có thể dùng `--yes`:

```bash
./trien_khai/uat/xoa_du_lieu.sh --yes
```

`xoa_du_lieu.sh` chỉ xoá khi:

- thư mục có dấu `.veh-uat-fixture.json` hợp lệ và đúng repo;
- đường dẫn không nằm trong repo, không phải `app/du-lieu`, `/du-lieu`, thư mục nhà;
- không còn phiên UAT đang chạy.

Nó **không** đụng `app/du-lieu`, `gateway/du-lieu`, hay bất kỳ thư mục nào khác. Sau khi xoá, lần khởi
động sau tạo thư mục mới + bộ tài khoản fixture mới (mật khẩu mới).

---

## 9. Cách xác nhận KHÔNG chạm dữ liệu thật

### 9.1. Chốt ở tầng script

Script từ chối (exit 1, không ghi gì) khi thư mục dữ liệu:

- nằm trong repo hiện tại hoặc bất kỳ cây git nào (kiểm `.git` đi ngược lên);
- là `app/du-lieu` / `gateway/du-lieu` / bất kỳ thư mục tên `du-lieu`;
- là `/du-lieu` hoặc thư mục con;
- là thư mục nhà `/Users/<bạn>` hoặc gốc `/`;
- đã có dữ liệu nhưng **không** có dấu UAT (có thể là dữ liệu thật của ai đó).

Ngoài ra, nếu shell đang có `VIP_HUB_DATA` trỏ tới chỗ khác, script **từ chối** thay vì tự đổi biến của
bạn — vì tự đổi sẽ che mất việc bạn đang trỏ nhầm vào dữ liệu thật.

### 9.2. Kiểm bằng mắt

```bash
# 1. Thư mục dữ liệu đúng là thư mục UAT riêng
ls -ld ~/veh-uat
cat ~/veh-uat/.veh-uat-fixture.json

# 2. CSDL đang dùng là CSDL UAT, không phải app/du-lieu
ls -l ~/veh-uat/hub.db
test -e app/du-lieu && echo "CẢNH BÁO: app/du-lieu có tồn tại" || echo "app/du-lieu KHÔNG tồn tại (bình thường)"

# 3. Không có hub.db nào bị tạo trong repo do UAT
find . -maxdepth 3 -name hub.db -not -path './.git/*' 2>/dev/null
```

`find` ở trên chỉ để kiểm tra; nếu repo của bạn vốn có `app/du-lieu/hub.db` thì đó là dữ liệu sản phẩm —
bộ script UAT không đọc/ghi vào đó.

### 9.3. Kiểm bằng biến môi trường của tiến trình

Máy chủ UAT được spawn với `VIP_HUB_DATA=~/veh-uat` (hoặc `VIP_UAT_DATA` bạn chọn). Script không bao giờ
gọi `migrate.py`/`khoi_tao.py` mà thiếu biến này. Nếu bạn muốn kiểm:

```bash
grep -n "VIP_HUB_DATA" trien_khai/uat/khoi_dong.sh
```

---

## 10. Cách xác nhận KHÔNG gọi API hãng

### 10.1. Cấu hình

Script export cố định:

```text
VIP_JT_MOI_TRUONG=mock
VIP_HUB_BIND=127.0.0.1
VIP_HUB_RESET_TOKEN=0
```

Nó **từ chối chạy** nếu bạn đặt `VIP_JT_MOI_TRUONG=sandbox`/`production`, vì UAT local không được gọi
API hãng kể cả sandbox.

### 10.2. Kiểm CSDL

```bash
sqlite3 ~/veh-uat/hub.db \
  "SELECT ma, live_mo FROM carrier_providers ORDER BY ma;
   SELECT id, tenant_id, hang, moi_truong FROM carrier_accounts ORDER BY id;"
```

Kỳ vọng:

```text
jt|0
vtp|0
1|1|vtp|mock
2|1|jt|mock
3|2|vtp|mock
4|2|jt|mock
```

### 10.3. Kiểm mã adapter

```bash
grep -n "CHO_PHEP_LIVE" app/adapter.py app/adapter_jt.py app/adapter_vtp.py
```

Adapter nền đặt `CHO_PHEP_LIVE = False`; mọi lớp con kế thừa, nên `live_mo=False`. Script còn kiểm lại
bằng Python (`adapter.danh_sach_hang()`) trước khi mở cổng — nếu có adapter nào `live_mo=True`, nó dừng.

### 10.4. Không có credentials thật

- Không có biến môi trường credentials hãng nào được đọc/ghi.
- Tài khoản hãng seed chỉ chứa `{"ghi_chu": "credentials demo mock", "ma_demo": ...}` đã mã hoá.
- Webhook secret là chuỗi ngẫu nhiên sinh local, dùng cho demo, không phải secret thật.
- Không tạo đơn thật: đơn mẫu ghi thẳng CSDL; đơn bạn tạo trong UAT cũng chỉ ghi CSDL local, không gửi hãng.
- Không mở webhook ra ngoài: máy chủ chỉ nghe `127.0.0.1`.

---

## 11. Xử lý sự cố

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `TỪ CHỐI: VIP_HUB_DATA đang trỏ tới ...` | Shell đang export biến cho môi trường khác | `unset VIP_HUB_DATA` rồi chạy lại |
| `TỪ CHỐI: ... nằm trong CÂY REPO` | `VIP_UAT_DATA` trỏ vào repo | Dùng `~/veh-uat` hoặc thư mục ngoài repo |
| `TỪ CHỐI: thư mục đã có dữ liệu nhưng KHÔNG có dấu UAT` | Trỏ nhầm vào dữ liệu thật/thư mục lạ | Chọn thư mục mới; **không** xoá thư mục đó khi chưa chắc |
| `mkdir: Operation not permitted` | Sandbox/IDE chặn ghi ra ngoài workspace | Chạy trong terminal thường, hoặc đặt `VIP_UAT_DATA` vào chỗ ghi được (vẫn phải ngoài repo) |
| `ps không dùng được` | Một số sandbox chặn `ps` | Không phải lỗi; script xác thực bằng health pid + `lsof`. Trên máy thật `ps` chạy bình thường |
| Không thấy dòng URL | Máy chủ thoát trước khi bind | Xem `~/veh-uat/nhat-ky/may-chu.log` |
| Đăng nhập báo sai mật khẩu | Dùng nhầm mật khẩu file khác, hoặc file cũ | Mở đúng `~/veh-uat/TAI-KHOAN-UAT.md`; nếu nghi mất, xoá dữ liệu và khởi động lại |
| Bị khoá tạm sau 5 lần sai | Cơ chế chống đoán mật khẩu | Chờ 15 phút, hoặc xoá dữ liệu UAT và khởi động lại |
| `dung.sh` báo `TỪ CHỐI kill PID ...` | PID đã bị cấp lại cho tiến trình khác, hoặc state cũ | **Không** kill. Kiểm `ps -p <PID> -o pid,command`; nếu chắc chắn là máy chủ UAT cũ, xử lý tay |
| State cũ nhưng PID đã chết | Lần trước dừng không sạch | `dung.sh` tự dọn state cũ và báo “không còn” |
| Cổng đã đóng nhưng state còn | Hiếm: process chết trước khi kịp dọn | Chạy `dung.sh`; nó thấy PID chết sẽ dọn state |

---

## 12. Bằng chứng chạy thật (môi trường soạn tài liệu)

Ngày chạy: **2026-10-18**, repo này. Lệnh dùng thư mục UAT tạm `/tmp/veh-uat-run` vì sandbox của IDE
chặn ghi vào `$HOME` và chặn `ps`; trên máy của chủ dự án, chạy trong terminal thường, mặc định `~/veh-uat` và
`ps` hoạt động đầy đủ. Cùng một bộ script, cùng các chốt an toàn.

| Phép kiểm | Kết quả |
|---|---|
| `khoi_dong.sh` (lần đầu, thư mục trống) | **exit 0**; tạo marker, schema v9, 9 user, 2 tenant, 10 đơn, 6 khách, 4 tài khoản hãng mock |
| Bind | `lsof`: `Python <PID> ... TCP 127.0.0.1:<cổng> (LISTEN)` — không có `0.0.0.0`/`*` |
| API loopback | `GET /api/v2/suc-khoe` → **200**, `{"ok": true, "pid": <PID>, ...}`; health pid khớp PID đã ghi |
| Đăng nhập fixture | 9 tài khoản đọc được từ `TAI-KHOAN-UAT.md`; `shopa-owner` → `TENANT_OWNER` Shop Demo A; `platform-owner` → `PLATFORM_OWNER` |
| API nghiệp vụ | `GET /api/v2/don?gioi_han=50` → 7 đơn Shop A; `GET /api/v2/tai-khoan-hang` → 2 tài khoản `mock`; `GET /api/v2/billing` → gói `basic`, usage 3 đơn |
| Đổi tenant | `da-tenant`: Shop A (`TENANT_ADMIN`) → `POST /auth/doi-tenant` → Shop B (`TENANT_VIEWER`) |
| API nền tảng | `GET /api/v2/platform/tenants` → 2 tenant `shop-a`, `shop-b` |
| `dung.sh` | **exit 0**; gửi SIGTERM đúng PID; health pid khớp trước khi kill; sau đó `kill -0 <PID>` thất bại; kết nối `127.0.0.1:<cổng>` bị `Connection refused`; state bị xoá |
| Không còn tiến trình mồ côi | `kill -0 <PID>` thất bại; kết nối `127.0.0.1:<cổng>` bị từ chối; không còn listener |
| Xoá dữ liệu | `xoa_du_lieu.sh --yes` **exit 0**; thư mục biến mất; khởi động lại tạo bộ tài khoản mới |
| Chốt từ chối | repo root, `app/du-lieu`, `/du-lieu`, `VIP_HUB_DATA` khác, thư mục không dấu, `VIP_JT_MOI_TRUONG=sandbox`, `VIP_HUB_RESET_TOKEN=1`, khởi động trùng, xoá khi đang chạy, xoá thư mục không dấu — tất cả **exit 1**, không ghi gì |

Bản ghi chi tiết hơn (không chứa mật khẩu) ở `trien_khai/uat/bang_chung/lan_chay_2026-10-18.md`.

---

## 13. Tệp trong bộ UAT

| Tệp | Vai trò |
|---|---|
| `trien_khai/uat/khoi_dong.sh` | Khởi động: kiểm an toàn, migrate, seed, chạy server loopback, ghi PID |
| `trien_khai/uat/dung.sh` | Dừng đúng PID đã ghi; kiểm không còn tiến trình/cổng |
| `trien_khai/uat/xoa_du_lieu.sh` | Xoá sạch dữ liệu UAT khi có dấu hợp lệ |
| `trien_khai/uat/lib.sh` | Thư viện dùng chung: kiểm đường dẫn, dấu UAT, PID, health |
| `trien_khai/uat/tao_du_lieu_uat.py` | Seed dữ liệu mẫu (khách, đơn, audit, usage) — idempotent |
| `trien_khai/uat/bang_chung/` | Bản ghi lần chạy thật (không chứa mật khẩu) |
| `docs/UAT_LOCAL.md` | Tài liệu này |
