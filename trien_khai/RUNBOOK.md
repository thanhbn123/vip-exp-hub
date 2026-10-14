# RUNBOOK TRIỂN KHAI — VIP Express Hub (G11)

> **Tài liệu cho NGƯỜI LÀM, không phải script tự chạy.** Mỗi mục là việc có người bấm, có
> người đọc kết quả. Không có bước nào ở đây tự nối lên máy chủ thật.

| | |
|---|---|
| Sở hữu | AG-05 DEVOPS |
| Viết ngày | 15/10/2026 |
| Nền | nhánh `agent/g11-devops`, nền `143084b`, schema **v7** |
| Máy đã đo | MacBook — `python3 3.9.6`, `node v26.7.0`, **không có Docker** |

## 0. HAI ĐIỀU PHẢI ĐỌC TRƯỚC

**0.1 — Triển khai staging lên VPS là `V-G11-01`, CHƯA ĐƯỢC CẤP QUYỀN** (SHARED_CONTRACTS §25).
Giao G11 **không có nghĩa** là được deploy. Không mục nào trong file này được chạy lên một máy
chủ thật cho tới khi anh Thành cấp quyền đó. Mục 5 trở đi viết để **sẵn sàng**, không để chạy.

**0.2 — Chưa có lượt Docker build nào.** Máy dựng không có Docker (`docker --version` →
`command not found`, đo 15/10/2026). `Dockerfile` và `docker-compose.yml` đã soát cú pháp và
soát tính nhất quán với mã thật, nhưng **chưa build lượt nào**. Ai build lượt đầu thì ghi kết
quả vào `docs/G11_FINAL_REPORT.md` — dòng đó hiện là **BLOCKED**, không phải PASS.

---

## 1. CHECKLIST TRƯỚC KHI TRIỂN KHAI

Chạy **theo thứ tự**. Bước nào không đạt thì **dừng**, không đi tiếp.

| # | Việc | Lệnh | Đạt khi |
|---|---|---|---|
| 1.1 | Cây làm việc sạch | `git -C ~/code/veh3-g11-devops status --short` | không có dòng nào lạ |
| 1.2 | Cú pháp | `sh trien_khai/kiem_cu_phap.sh` | mã thoát 0 |
| 1.3 | Cấu hình | `python3 trien_khai/kiem_cau_hinh.py --env .env` | mã thoát 0 |
| 1.4 | Bộ thử Python | `for f in app/thu/thu_*.py; do python3 "$f"; done` | mọi bộ `OK` |
| 1.5 | Bộ thử E2E qua HTTP thật | `sh app/thu/chay_e2e.sh` | `41/41 phép đo đạt`, mã thoát 0 |
| 1.6 | Diễn tập khôi phục | `sh trien_khai/dien_tap_khoi_phuc.sh` | mã thoát 0 |
| 1.7 | `.env` KHÔNG trong Git | `git check-ignore -v .env` | in ra một dòng |

> **1.7 hiện KHÔNG ĐẠT.** `.gitignore` chưa chặn `.env` (đo 15/10/2026). AG-00 giữ file đó —
> xem **bản vá P-3**. Tới khi cắm, giữ `.env` ngoài cây repo và trỏ `--env-file` vào đường
> tuyệt đối.

**Bước 1.5 là bước không được bỏ.** Nó là phép đo **độc lập**: gọi HTTP thật vào một máy chủ
thật trên nền cô lập. Mọi bộ thử khác gọi hàm Python trong cùng tiến trình — chúng không chứng
minh được là **máy chủ** chạy.

---

## 2. BUILD IMAGE (lượt đầu — CHƯA AI CHẠY)

```sh
cd ~/code/veh3-g11-devops
docker build -t vip-express-hub:0.3-saas-local .
docker image inspect vip-express-hub:0.3-saas-local --format '{{.Size}} byte'
```

**Nghiệm thu build — ba điều phải kiểm, không chỉ kiểm "build xong":**

```sh
# 2.1 KHÔNG có bí mật trong layer. `docker history` đọc được mọi layer, vĩnh viễn.
docker history --no-trunc vip-express-hub:0.3-saas-local | grep -Ei 'passphrase|secret|api_key|\.env' && echo "CO BI MAT — DUNG LAI"

# 2.2 KHÔNG chạy bằng root.
docker image inspect vip-express-hub:0.3-saas-local --format '{{.Config.User}}'   # phải là `hub`

# 2.3 KHÔNG có file khóa / CSDL nào lọt vào image.
docker run --rm --entrypoint sh vip-express-hub:0.3-saas-local -c \
  'find / -xdev \( -name "*.key" -o -name "*.db" -o -name "*.vipkb" -o -name ".env" \) 2>/dev/null'
# phải KHÔNG in gì
```

> 2.3 là phép đo **độc lập** với `.dockerignore`: `.dockerignore` nói *ý định*, lệnh này nói
> *kết quả*. Tin `.dockerignore` rồi kết luận là tin một danh sách đen mình tự viết.

---

## 3. CHẠY LOCAL BẰNG COMPOSE

```sh
cp .env.example .env        # rồi MỞ RA SỬA. Đừng chạy với giá trị mẫu.
python3 trien_khai/kiem_cau_hinh.py --env .env   # phải 0 lỗi
docker compose up -d
docker compose ps           # cột STATUS phải có (healthy) sau ~20 giây
```

**Lượt đầu sẽ DỪNG ở mã thoát 3** vì volume mới chưa có schema. Đó là hành vi **đúng**:
`khoi_dong.sh` cố ý **không tự chạy migration** (lý do viết trong chính script đó). Làm mục 4.

```sh
docker compose logs --tail 30 hub     # phải thấy: "CSDL o schema v0, ma can v7"
```

---

## 4. MIGRATION — BƯỚC RIÊNG, CÓ NGƯỜI NHÌN

**Luật: nâng schema không bao giờ chạy tự động trong ENTRYPOINT.** Lý do ghi trong
`trien_khai/khoi_dong.sh` — gọn lại: N bản chạy song song là N lượt migration đua nhau, và
`restart: unless-stopped` biến một lượt nâng hỏng thành vòng lặp nâng-hỏng-nâng-hỏng, mỗi vòng
một file backup mới, tới lúc không ai còn biết bản nào là bản **trước** khi hỏng.

```sh
# 4.1 XEM phiên bản. Không sửa gì.
docker compose run --rm --entrypoint python3 hub app/migrate.py --kiem

# 4.2 NÂNG. `migrate.py` tự backup trước, tự kiểm bảo toàn số dòng.
docker compose run --rm --entrypoint python3 hub app/migrate.py
# GHI LẠI đường dẫn file backup mà nó in ra. Mục 8 cần đúng đường đó.

# 4.3 Đo lại
docker compose run --rm --entrypoint python3 hub trien_khai/do_csdl.py
```

> **CẢNH BÁO — bản sao lưu có thể BỊ GHI ĐÈ IM LẶNG.** `migrate.sao_luu()` đặt tên theo
> **giây** (`hub-truoc-migrate-YYYYMMDD-HHMMSS.db`). Đo thật 15/10/2026: hai lượt gọi trong
> **cùng một giây** trả về **cùng một đường dẫn** và lượt sau ghi đè lượt trước, không báo gì.
> Nghĩa là: **chạy lại migration ngay sau một lượt hỏng có thể xoá mất bản "trước khi hỏng".**
> Cách tránh cho tới khi có bản vá **P-4**: trước mỗi lượt `migrate.py`, tự chép tay một bản
> ra tên riêng.
> ```sh
> docker compose run --rm --entrypoint sh hub -c \
>   'cp /du-lieu/hub.db "/du-lieu/sao-luu/tay-$(date +%Y%m%d-%H%M%S-%N).db"'
> ```

---

## 5. KHỞI ĐỘNG + SMOKE TEST

```sh
docker compose up -d
sh trien_khai/kiem_san_sang.sh http://127.0.0.1:8897 15
```

`kiem_san_sang.sh` gọi **từ ngoài tiến trình, qua HTTP** — cố ý. Chạy
`python3 app/quan_sat.py san-sang` trên máy chủ **không** kiểm chứng được rằng *máy chủ web
đang chạy đã sẵn sàng*; nó chỉ kiểm chứng rằng *một tiến trình Python mới dựng lên thì sẵn
sàng*. Hai thứ khác nhau: tiến trình web có thể đang giữ một kết nối SQLite hỏng, đang treo
thread, hoặc đang chạy mã của bản deploy **trước**.

### Smoke test — 6 phép đo

| # | Đo gì | Lệnh | Đạt khi |
|---|---|---|---|
| S1 | Health | `curl -s localhost:8897/api/v2/suc-khoe` | `"ok": true` |
| S2 | Readiness | `sh trien_khai/kiem_san_sang.sh` | mã thoát 0 |
| S3 | Static có phục vụ | `curl -so /dev/null -w '%{http_code}' localhost:8897/admin/index.html` | `200` |
| S4 | Static allowlist còn chặn | `curl -so /dev/null -w '%{http_code}' localhost:8897/app/bao_mat.py` | `404` |
| S5 | CSRF còn chặn | `curl -so /dev/null -w '%{http_code}' -X POST localhost:8897/api/v2/auth/dang-nhap` | `403` |
| S6 | Đăng nhập thật | xem `app/du-lieu/TAI-KHOAN-DEMO.md` | `200` + cookie `phien` |

> **S4 không phải phép đo trang trí.** Ngày 14/10/2026 AG-07 QA chứng minh được thật:
> `/app/bao_mat.py` và `/gateway/cau_hinh.py` trả **200** cho người vô danh, lộ cả secret HMAC
> của 5 hãng. Danh sách trắng static vá chỗ đó. Mỗi lượt deploy phải đo lại — một bản vá đã có
> rồi vẫn mất được ở lượt gộp nhánh sau.

---

## 6. LÙI (ROLLBACK)

**Hai thứ lùi RIÊNG, không gộp:** lùi **mã** và lùi **CSDL**. Lùi mã mà không lùi CSDL thường
là đúng (mã cũ đọc được schema mới, phần lớn trường hợp). Lùi CSDL thì **mất dữ liệu phát sinh
từ lúc backup tới giờ** — nên đó là việc cuối, không phải việc đầu.

```sh
# 6.1 LÙI MÃ (thử trước, vì không mất dữ liệu)
docker compose down                     # TUYỆT ĐỐI KHÔNG `-v` — xem mục 9
docker tag vip-express-hub:<the-cu> vip-express-hub:0.3-saas-local
docker compose up -d
sh trien_khai/kiem_san_sang.sh

# 6.2 LÙI CSDL — chỉ khi 6.1 không cứu được
docker compose down
docker compose run --rm --entrypoint python3 hub trien_khai/do_csdl.py > /tmp/truoc-lui.json
docker compose run --rm --entrypoint python3 hub app/migrate.py --rollback /du-lieu/sao-luu/<file>
docker compose run --rm --entrypoint python3 hub trien_khai/do_csdl.py > /tmp/sau-lui.json
python3 trien_khai/do_csdl.py --so-sanh /tmp/truoc-lui.json /tmp/sau-lui.json
docker compose up -d && sh trien_khai/kiem_san_sang.sh
```

`migrate.py --rollback` **cất bản hiện tại trước khi đè** (`hub-truoc-rollback-*.db`) — nên lùi
vẫn lùi lại được. Đã đo trong diễn tập, bước B12.

---

## 7. BACKUP — BỐN THỨ, BỐN CHỖ

| Thứ | Lệnh | Chu kỳ | Khôi phục ở |
|---|---|---|---|
| CSDL | `migrate.sao_luu()` (tự chạy trong `migrate.py`) | mỗi lượt migration + theo lịch | mục 8.1 |
| Khóa mã hóa | `python3 app/sao_luu_khoa.py tao <đường>.vipkb` | mỗi lần xoay khóa, và sau mỗi lần thêm tài khoản hãng | mục 8.2 |
| Cấu hình | mã băm `app/cau_hinh.py` + `.env.example` + Dockerfile + compose | mỗi lượt deploy | mục 8.3 |
| Bí mật thật | **KHÔNG sao lưu tự động** | — | người giữ |

**Bí mật thật không nằm trong bất kỳ lượt sao lưu tự động nào, và đó là CÓ CHỦ Ý.** Passphrase
của gói khóa do **anh Thành giữ**; nó không ở trong vault, không ở trong `.env` của dịch vụ web,
không ở trong Git. Sao lưu bí mật ra ngoài máy là `V-13906-03`, **chưa cấp quyền**.

> **Gói khóa chưa có bản ngoài nhà.** Lý do 3 của mục PRODUCTION READINESS. Gói `.vipkb` nằm
> cùng máy với CSDL nó bảo vệ, nên một lượt mất ổ là mất **cả hai**. Cách vá đúng: cất gói ở
> **chỗ khác máy chủ** (NAS, hoặc chỗ anh Thành chọn) và **diễn tập khôi phục trên máy sạch**.
> Chưa làm được vì đụng `V-13906-03`.

---

## 8. KHÔI PHỤC THẢM HOẠ

**Luật trước mọi bước: dựng lại ở chỗ MỚI, không ghi đè chỗ cũ.** Chỗ cũ là bằng chứng để chẩn
đoán vì sao hỏng; ghi đè nó là xoá bằng chứng.

### 8.1 Mất CSDL, còn khóa
```sh
mkdir -p /du-lieu-moi && cp /du-lieu/sao-luu/<ban-moi-nhat>.db /du-lieu-moi/hub.db
cp -a /du-lieu/khoa /du-lieu-moi/khoa
VIP_HUB_DATA=/du-lieu-moi python3 trien_khai/do_csdl.py     # integrity_check phải `ok`
```

### 8.2 Mất khóa, còn CSDL — **ca nguy hiểm nhất**
CSDL còn nguyên mà khóa mất thì **mọi credentials hãng và webhook secret là rác không cứu
được**. AES-256-GCM không có cửa sau, và đó là đúng.
```sh
python3 app/sao_luu_khoa.py kiem <goi>.vipkb              # KIỂM gói TRƯỚC khi tin nó
python3 app/sao_luu_khoa.py header <goi>.vipkb            # xem key_id có trong gói
python3 app/sao_luu_khoa.py khoi-phuc <goi>.vipkb /du-lieu-moi/khoa
```
Rồi **đo thật** là giải mã lại được — số dòng khớp **không** chứng minh điều đó:
```sh
VIP_HUB_DATA=/du-lieu-moi python3 - <<'PY'
import sys; sys.path.insert(0, "app")
import csdl, bao_mat
r = csdl.mot("SELECT tenant_id, hang, credentials_ma_hoa FROM carrier_accounts LIMIT 1")
bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
print("giai ma DAT")
PY
```
> `kiem` **trước** `khoi-phuc` là §12.1 luật 1: thứ dùng để kiểm chứng phải được kiểm trước khi
> tin. Một gói hỏng mà cứ khôi phục là ghi khóa rác lên chỗ khóa, và lúc đó mất thật.

### 8.3 Mất cả hai
Dữ liệu đã mã hóa **không cứu được**. Dựng lại hệ rỗng (`migrate.py` + `khoi_tao.py`), rồi nhập
lại credentials hãng **bằng tay** từ chỗ anh Thành giữ. Ghi vào nhật ký đúng những gì đã mất.

> **RỦI RO CỐ Ý CHƯA VÁ, ghi ra để không bị bỏ quên:** `ban_ma[]` của gói khóa **chỉ phủ bảng
> `carrier_accounts`** (rủi ro R-h của dự án). Bảng mới nào có secret thì phải thêm vào **CẢ BA
> chỗ**: `sao_luu_khoa`, `ma_hoa_lai_carrier_accounts`, và bộ thử. Quên một chỗ là mất im lặng.

---

## 9. BA ĐIỀU TUYỆT ĐỐI KHÔNG LÀM

1. **Không `docker compose down -v`.** `-v` xoá volume `vip_hub_du_lieu`, tức là xoá CSDL **và**
   khóa mã hóa. Khóa mất thì mọi credentials đã mã hóa là rác (mục 8.2). Dừng dịch vụ bằng
   `docker compose down` hoặc `docker compose stop`.
2. **Không `pkill` / `killall` theo mẫu tên** — luật cứng của chủ dự án (CLAUDE.md §16.7). Ca đã
   xảy ra thật: `pkill -f cat` giết cả Ollama, Synology Drive và Terminal, vì chữ "cat" nằm
   trong "Appli**cat**ion". Dừng container bằng `docker compose stop`; dừng tiến trình thì
   `pgrep -fl`, rồi `ps -p <pid> -o pid,lstart,command`, **nhìn tận mắt**, rồi `kill <pid>`.
3. **Không chạy `migrate.py` lên CSDL thật** `~/Projects/vip-express-hub/app/du-lieu/`
   (SHARED_CONTRACTS §24). Đó là CSDL giữ dữ liệu thật của các đợt trước. AG-00 là người duy
   nhất chạy migration lên đó, sau khi đã thử trên bản sao.

---

## 10. CỔNG PHÊ DUYỆT PRODUCTION

**Trạng thái hôm nay: CHƯA ĐẠT.** Không phải vì thiếu tài liệu, mà vì 10 cổng dưới đây chưa đủ.

### 10.1 Cổng chặn — phải mở TRƯỚC khi production

| # | Cổng | Trạng thái 15/10/2026 | Thiếu chính xác cái gì |
|---|---|---|---|
| G-1 | Anh Thành cấp quyền triển khai | **CHƯA** | `V-G11-01` |
| G-2 | Docker build + compose chạy một lượt | **CHƯA** | máy có Docker |
| G-3 | HTTPS thật | **CHƯA** | proxy (Caddy/nginx) + cookie `Secure` (bản vá P-2) |
| G-4 | `server.py` bind được ra ngoài `127.0.0.1` | **CHƯA** | bản vá P-1 (AG-00 cắm) |
| G-5 | Header bảo mật | **CHƯA** | bản vá P-2 |
| G-6 | Khôi phục khóa thật trên máy chủ sạch | **CHƯA** | blocker B-2: passphrase thật + chỗ cất ngoài máy |
| G-7 | Gói khóa có bản ngoài nhà | **CHƯA** | `V-13906-03` |
| G-8 | Rate limit dùng được với nhiều worker | **CHƯA** | trần sống trong bộ nhớ một tiến trình (R-a) |
| G-9 | Đo trên dữ liệu lớn | **CHƯA** | lý do 6 của PRODUCTION READINESS |
| G-10 | `.env` nằm ngoài Git | **CHƯA** | bản vá P-3 |

### 10.2 Hay hỏng ở đâu — bảng tra nhanh

| Triệu chứng | Nghi trước tiên | Đo bằng |
|---|---|---|
| Container `(unhealthy)` ngay từ đầu | schema cũ hơn mã | `docker compose logs hub` — tìm `schema v` |
| Cổng mở mà `curl` không nối được | `server.py` ghim cứng bind `127.0.0.1` **trong** container | `docker exec … curl localhost:8897/api/v2/suc-khoe` được, từ host thì không ⇒ đúng là bind (bản vá P-1) |
| `KHONG ghi duoc vao /du-lieu` | volume thuộc root, tiến trình chạy `hub` | `docker exec … ls -ld /du-lieu` → `chown -R 999:999` |
| Readiness hỏng ở `khoa` | thiếu thư mục khóa hoặc thiếu con trỏ `hien-hanh` | `docker exec … ls -la /du-lieu/khoa` |
| Giải mã credentials nổ sau khôi phục | CSDL và khóa **lệch nhau** (hai bản sao lưu khác mốc) | mục 8.2, bước đo cuối |
| Rate limit lỏng hơn mong đợi | nhiều worker ⇒ trần nhân lên theo số worker | R-a; đo bằng số bản đang chạy |
| Readiness xanh mà hệ vẫn hỏng | đọc kỹ `bo_qua` — phép kiểm bị bỏ qua là `ok: null`, **chưa đo**, không phải đã đạt | `curl … /api/v2/san-sang \| grep bo_qua` |

### 10.3 Quy trình phê duyệt — năm bước

1. Chạy trọn mục 1. Dán **kết quả thật** (kèm mã thoát) vào `docs/G11_FINAL_REPORT.md`.
2. Mở từng cổng ở 10.1. Cổng nào bỏ qua thì **ghi ra kèm lý do và cách vá đúng** — rủi ro không
   ghi là rủi ro bị bỏ quên.
3. Đưa anh Thành bảng 10.1 ở trạng thái **thật**, không làm nhẹ đi.
4. Anh duyệt từng dòng. Chưa duyệt thì **không** triển khai.
5. Sau triển khai: `kiem_san_sang.sh` + 6 phép đo smoke ở mục 5, **từ ngoài máy chủ**.

> **Lệnh đưa anh Thành chạy phải viết cho `zsh`** (CLAUDE.md §12.2) — máy anh dùng zsh.
> `read -s -p` là cú pháp bash; trong zsh nó nhận 0 ký tự rồi báo sai. Cần nhập mật khẩu/
> passphrase thì dùng `stty -echo` + `read` trần.
