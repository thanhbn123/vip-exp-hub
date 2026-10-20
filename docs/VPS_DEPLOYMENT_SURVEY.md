> **CẬP NHẬT 2026-10-20:** Owner đã duyệt; dịch vụ đã chạy trên VPS qua Cloudflare Tunnel.
> URL tạm và quy trình nhập BEST: `docs/BEST_EXPRESS_LIVE_UAT.md`. Tên miền chính
> `best-uat.viporder.vn` vẫn NXDOMAIN; Caddy chưa có cert cho tên này. Báo cáo dưới là hiện
> trạng trước triển khai.

# VIP EXPRESS HUB — KHẢO SÁT & PHƯƠNG ÁN TRIỂN KHAI VPS 160.22.170.20

**Ngày:** 2026-10-19 · **Trạng thái:** ĐÃ KHẢO SÁT + ĐÃ BUILD/SELF-TEST CÔ LẬP.
**AG-06 (cùng ngày):** đã review bộ deploy, vá các lỗi thật, build lại và self-test trên staging
`/home/deploy/vip-express-hub/ag06-review`; **KHÔNG** đụng dịch vụ/Caddy/DNS/firewall đang chạy.
**CHƯA** đổi DNS, **CHƯA** thêm site Caddy, **CHƯA** mở dịch vụ ra Internet, **CHƯA** gọi BEST
bằng credential thật. Các mục **[CẦN DUYỆT]** chờ Owner. Chi tiết AG-06 ở mục 10.

---

## 1. TÌNH TRẠNG VPS (đo read-only)

| Mục | Kết quả |
|---|---|
| OS/kernel | Ubuntu 26.04 LTS · kernel 7.0.0-34-generic · VMware · x86_64 |
| CPU | 4 vCPU Intel Xeon Platinum 8272CL @ 2.60GHz |
| RAM | 7,2 GiB total · 2,0 GiB used · **5,3 GiB available** · swap 2 GiB (đã dùng 393 MiB) |
| Disk | 89 GB ext4 · 26 GB used · **59 GB free** · inode 10% |
| Docker | Engine 29.1.3 · Compose **v5.6.0** · containerd 2.2.2 |
| User | `deploy` UID 1000 · group `docker` · **KHÔNG có sudo** (`sudo -n` từ chối) |
| Time/NTP | Asia/Ho_Chi_Minh · clock synchronized · chrony active |
| Public IP | 160.22.170.20/23 · IPv6 tailscale riêng |
| Docker hiện có | 23 container đang chạy / 35 tổng; 129 image; build cache 2,87 GB |
| Cổng 80/443 | `vip-staging-caddy` (caddy:2, **network_mode=host**) giữ 80/443 |
| Cổng app dự kiến | `127.0.0.1:18897` — **đang trống** |
| DNS hiện có | `viporder.com.vn`, `cpn.viporder.vn`, `qua.viporder.vn`, `hq.vipgroup.com.vn`, `hub.staging...`, `vtp.staging...`, `ai.vipgroup.com.vn`, `cowork.vipgroup.com.vn` |
| DNS ứng viên | **`best-uat.viporder.vn` CHƯA có bản ghi**; `best-uat.viporder.com.vn` trỏ **103.159.50.70** (sai VPS) |

### Dịch vụ đang chạy — KHÔNG được đụng

- `viporder` (staging) + `viporder-prod` (production `viporder.com.vn`)
- `hub-vip-viettelpost`, `staging-hub`, `member`, `vip-customs-ai-staging`
- `vip-ai-brain-acceptance`, `vipphone-staging`, `vip-staging` + shared Caddy
- Caddy dùng chung đang phục vụ nhiều tên miền; **không restart**, chỉ reload sau backup/validate.

---

## 2. PHƯƠNG ÁN KIẾN TRÚC ĐỀ XUẤT

```
Internet
  │  HTTPS 443 (Let's Encrypt)
  ▼
vip-staging-caddy (host network, shared)  ──► 127.0.0.1:18897
                                                    │
                                        docker-proxy (loopback only)
                                                    ▼
                                   vip-express-hub (container)
                                   - bind 0.0.0.0:8897 trong container
                                   - UID 1000, read_only, cap_drop ALL
                                   - /du-lieu = bind mount persistent
                                   - SQLite hub.db + khoá AES-256-GCM
```

- **Reverse proxy dùng chung**, thêm một site block; không mở Nginx/Caddy mới trên 80/443.
- **App chỉ bind loopback** `127.0.0.1:18897`; không mở cổng 8897/18897 ra Internet.
- **HTTPS do Caddy** kết thúc; app đặt `VIP_HUB_HTTPS=1` để cookie `Secure` + HSTS.
- **Database**: SQLite (`hub.db`) trên bind mount `/home/deploy/vip-express-hub/data`;
  app hiện chỉ hỗ trợ SQLite (Postgres mới là đường backup/ghi chú, chưa có adapter runtime).
- **Persistent**: bind mount ngoài container; không dùng `/tmp`; root filesystem container read-only.
- **Multi-tenant**: giữ nguyên; mỗi tenant có account BEST riêng, webhook `webhook_ma` riêng.

---

## 3. TÊN MIỀN / HTTPS ĐỀ XUẤT

**Đề xuất:** `best-uat.viporder.vn` → `A 160.22.170.20` (DNS-only).

Vì sao:
- `viporder.vn` đã có `cpn.viporder.vn` và `qua.viporder.vn` trỏ đúng VPS này → Owner kiểm soát
  vùng DNS và mẫu bản ghi đã tồn tại.
- Không dùng `best-uat.viporder.com.vn` vì đang trỏ 103.159.50.70.
- Không dùng `viporder.com.vn`/`www` vì đó là production hiện hữu.

Sau khi có DNS, Caddy tự xin Let's Encrypt qua HTTP-01 (cổng 80 đã mở). Không cần đổi firewall.
Nếu DNS bật proxy Cloudflare, phải chuyển DNS-only hoặc dùng DNS-01 (chưa cấu hình).

**Cần Owner/DNS admin thực hiện:** thêm bản ghi A; xác nhận `dig +short` trả 160.22.170.20.

---

## 4. NHỮNG GÌ ĐÃ CHUẨN BỊ (không ảnh hưởng dịch vụ khác)

| Việc | Bằng chứng (đo 2026-10-19, staging `ag06-review`) |
|---|---|
| Source copy | `/home/deploy/vip-express-hub/src` (bản cũ) + staging `/home/deploy/vip-express-hub/ag06-review/src` (bản AG-06); production source **chưa** bị ghi đè |
| Compose validate | `docker compose config --quiet` exit 0; resolved `user: 1000:1000`, `HUB_UID/GID=1000`, `create_host_path: false`, `mem_limit 512m`, `pids_limit 512`, port `127.0.0.1:18897` |
| Caddy block validate | `kiem_caddy.sh` → **Valid configuration** cho live + candidate; live sha256 `c0ae5314…e1c74ad` không đổi; Caddy started `13:26:02Z`, restarts 0 |
| Build image | `vip-express-hub:ag06-review` · 232 MB · id `90af23af65be` · build exit 0; base `python:3.11-slim-bookworm@sha256:0a310…f5f89` |
| Quyền image | user `hub` **UID/GID 1000**; `/du-lieu` 1000:1000 mode 700; volume ẩn danh ghi được; root FS read-only chặn ghi `/app` |
| Không rò `.env` | `find /app -name '.env*'` → rỗng; Dockerfile COPY tường minh (bản cũ `COPY trien_khai/` từng mang `.env` vào image) |
| Self-test cô lập | `--network none`, health **healthy sau 6 s**; `/suc-khoe` 200; `/san-sang` 200; UAT 200 |
| Restart test | restart → **healthy sau 7 s**; wall 17 s; `/suc-khoe` + `/san-sang` 200 |
| Port-mapped test | `127.0.0.1:18898→8897`; health/ready/UAT 200; auth-required 401; webhook mã lạ **404 fail-closed**; HSTS trên GET; cookie `Secure; HttpOnly` (login có CSRF header) |
| Backup | `backup.sh` end-to-end trên container cô lập: `hub.db` + `.sha256`, integrity `ok`, 52 bảng; gói khoá `.vipkb` 818 B, header `VIPHUBKEYBAK`, 1 khoá |
| Restore | diễn tập logic bằng shim `docker`/`curl`: success đổi đúng DB; rollback khi `migrate --kiem` hỏng giữ dữ liệu logic; **chưa** chạy `compose up` thật |
| Dọn test | container/data/log staging đã xoá; không còn container `vip-express-hub*`; cổng 18897/18898 trống; **không** đụng compose/container hiện có |

**Chưa làm:** chưa thêm khối Caddy, chưa `docker compose up -d`, chưa tạo DB/admin thật, chưa
đổi DNS/firewall, chưa cài cron backup, chưa gọi BEST.

---

## 5. CẤU HÌNH DATABASE / BACKUP

- `VIP_HUB_DATA=/du-lieu` → bind `/home/deploy/vip-express-hub/data` (mode 700, UID 1000).
- Migration fresh: `docker compose run --rm -e VIP_KHO_DANG_CHAY=sqlite --entrypoint python3 hub /app/app/migrate.py` → schema 10, bảo toàn 0 dòng. Đo AG-06: migration **tự tạo khóa đầu tiên** `data/khoa/goc.key` (600) + `hien-hanh`; readiness sau migration đạt. Không cần bước tạo khóa riêng.
- Bootstrap admin: `bootstrap_admin.py` tạo tenant + `PLATFORM_OWNER` + `TENANT_OWNER`; **từ chối** nếu DB đã có user. Bản AG-06 gói kiểm tra + seed quyền + insert trong **một transaction** `BEGIN IMMEDIATE`; lần hai đo được exit 1, user/tenant/membership/role không đổi. Mật khẩu qua stdin, không in.
- Backup DB: `sao_luu()` (SQLite backup API) → `backups/<ts>/hub.db` + `.sha256`; giữ 14 ngày. `backup.sh` lấy đúng path app trả về (map `/du-lieu` → host), kiểm `.sha256` nguồn + integrity bản chép, khoá `flock`, dùng `docker exec` theo `container_name`.
- Backup khoá: `sao_luu_khoa.py tao ...vipkb`; passphrase đi qua **stdin**, không `-e`/argv; **DB một mình không đủ** khôi phục credential nếu mất `data/khoa`. Đo: gói 818 B, header `VIPHUBKEYBAK`, 1 khoá.
- Restore: `restore.sh` yêu cầu câu xác nhận; kiểm checksum + integrity **trước** khi dừng; snapshot DB cũ bằng SQLite backup API (gộp WAL); xoá WAL/SHM cũ; `migrate --kiem` bằng container một-lần **trước** `up`; health + readiness; rollback DB cũ nếu lỗi. Đã test logic bằng shim; **chưa** chạy thật.
- **Chưa cài cron**; cần Owner duyệt. Không dùng `/tmp` cho DB/backup nghiệp vụ.
- Diễn tập restore trên bản copy **chưa chạy**; phải làm trước khi tin.

---

## 6. RỦI RO / VẤN ĐỀ CÒN TỒN TẠI

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| 1 | Caddyfile root-owned, `deploy` không sudo; `/etc/caddy/Caddyfile` là **mount READ-ONLY** | Cao | Chỉ Owner/root ghi file host **in-place**; `kiem_caddy.sh` validate live+candidate trước; reload graceful; giữ backup. Cách cũ `docker exec ... cat >>` **hỏng** (`Read-only file system`) |
| 2 | Shared Caddy lỗi làm sập nhiều site | Cao | Validate candidate trước; ghi in-place; validate file live; reload graceful; giữ backup; **không restart** |
| 3 | DNS chưa có, chưa xin được cert | Cao | Chờ Owner tạo A record; kiểm `dig` trước; đo hiện tại NO_DNS |
| 4 | DB SQLite + khoá nằm cùng ổ | Trung bình | Bind mount persistent; backup DB + key package; chưa có NAS/offsite |
| 5 | Chưa diễn tập restore thật | Trung bình | Mới test logic bằng shim; phải chạy trên bản copy + cửa sổ bảo trì trước khi tin |
| 6 | Backup cron chưa cài | Trung bình | Cài sau duyệt; theo dõi dung lượng 59 GB |
| 7 | App chỉ hỗ trợ SQLite | Trung bình | Chấp nhận cho UAT; muốn Postgres phải làm adapter riêng |
| 8 | `deploy` không sudo; quyền Docker gần tương đương root | Trung bình | Chỉ dùng lệnh đã duyệt; không chạy container mount `/srv` tùy tiện; firewall/DNS cần Owner |
| 9 | Rate limit sau proxy có thể gộp IP | Trung bình | `VIP_HUB_PROXY_TIN_CAY` đang trống; app thấy peer là gateway Docker, không phải client. Đo log/gateway rồi mới điền, không tin dải rộng |
| 10 | Credential BEST thật | Cao | Chỉ nhập qua HTTPS; mã hoá; không log/chat; Owner phê duyệt |
| 11 | `.env` trong build context | Cao (đã vá image) | Root `.dockerignore` khớp `.env` **không** đệ quy; bản cũ `COPY trien_khai/` từng đưa `.env` vào image. Dockerfile nay COPY tường minh + `test`; **cần** sửa `.dockerignore` thành `**/.env` (ngoài phạm vi AG-06) |
| 12 | HEAD không được app hỗ trợ | Thấp | App trả 501 cho HEAD; monitor/health bên ngoài dùng GET; `kiem_tra.sh` đã đổi HSTS sang GET |
| 13 | Image base trôi | Thấp | Đã ghim digest `python:3.11-slim-bookworm@sha256:0a310…f5f89`; nâng digest phải review |
| 14 | UID image/compose lệch | Đã vá | Image tạo `hub` 1000:1000, compose `user: ${VIP_HUB_UID}:${VIP_HUB_GID}`, build args cùng nguồn; `chuan_bi.sh` kiểm chủ data |

---

## 7. CẦN OWNER PHÊ DUYỆT (từng mục)

1. **DNS**: đồng ý dùng `best-uat.viporder.vn`, tạo `A 160.22.170.20` (DNS-only) và báo khi có.
2. **Caddy**: đồng ý thêm khối `best-uat.viporder.vn` vào Caddy dùng chung. Owner/root phải
   backup và ghi **in-place** file host `/srv/vip-staging-proxy/Caddyfile` (mount ro, không
   `docker exec >>` được); deploy validate + reload (không restart). Chấp nhận rủi ro reverse
   proxy dùng chung.
3. **Dịch vụ**: đồng ý tạo `/home/deploy/vip-express-hub/data`, chạy migration (tự tạo khóa
   đầu tiên), bootstrap admin, `docker compose up -d` trên cổng loopback `18897`.
4. **Tài khoản admin**: chọn username (mặc định `owner`) và cách giao mật khẩu ban đầu
   (khuyến nghị: Owner tự đặt qua stdin trên SSH, không gửi chat; đổi sau đăng nhập đầu).
5. **BEST sandbox**: đồng ý bật `VIP_BEST_OWNER_APPROVED=1` + mã audit trong cửa sổ UAT;
   credential do BEST cấp; **không** production.
6. **Backup**: đồng ý cài cron backup DB hằng ngày (giữ 14 ngày) và lịch diễn tập restore.
7. **Webhook**: sau khi có DNS/Caddy, đồng ý gửi URL `https://best-uat.viporder.vn/api/v2/webhook/nhan/<ma>`
   + Bearer token cho BEST cấu hình trên V9.

**Không tự ý thay đổi** các dịch vụ/container/cổng 80/443/DNS hiện có. Sau khi được duyệt từng
mục, mới thực hiện và báo lại URL + bằng chứng.

---

## 8. LỆNH KIỂM TRA SAU KHI DUYỆT

```sh
cd /home/deploy/vip-express-hub/src/trien_khai/vps
docker compose ps
curl -fsS http://127.0.0.1:18897/api/v2/suc-khoe
sh kiem_tra.sh
```

`kiem_tra.sh` kiểm: container health (chờ tối đa 60 s), bind mount `/du-lieu`, quyền data 700,
health/ready, trang UAT, 401 khi chưa đăng nhập, webhook mã lạ **404 fail-closed**, HSTS bằng
**GET** (app trả 501 cho HEAD), TLS cert, và cổng app **chỉ loopback** (fail nếu bind ngoài /
không thấy cổng).

---

## 9. KẾT LUẬN

- VPS **đủ tài nguyên** cho VIP Express Hub (4 vCPU, 5,3 GiB RAM trống, 59 GB disk).
- **Không cần firewall/NAT mới**: Caddy đã giữ 80/443; app chỉ loopback.
- **Cần DNS + một khối Caddy**; đây là thay đổi reverse proxy dùng chung, phải được duyệt.
- Image đã build và self-test **healthy/restart healthy**; chưa phải triển khai thật.
- AG-06: image review `vip-express-hub:ag06-review` sạch `.env*`, UID 1000; Caddy live không đổi;
  backup/restore đã test logic nhưng **chưa** chạy restore thật.
- **Chưa có URL công khai** cho đến khi DNS + Caddy được duyệt.
- **Chưa có REAL PASS/OWNER APPROVED**; mọi tuyên bố như vậy là sai.

---

## 10. AG-06 — REVIEW BỘ DEPLOY (2026-10-19)

Phạm vi: `trien_khai/vps/**`, `Dockerfile`, tài liệu này. **Không** sửa `app/**`, `admin/**`,
`pages/**`; **không** đụng dịch vụ/Caddy/DNS/firewall; **không** `docker compose up -d`; không
push. Mọi thao tác dưới đây chạy trên staging `/home/deploy/vip-express-hub/ag06-review` hoặc
container cô lập; production source `/home/deploy/vip-express-hub/src` **không bị ghi đè**.

### 10.1 Lỗi thật đã tìm và vá

| ID | Lỗi | Bằng chứng / cách vá |
|---|---|---|
| B-1 | **UID lệch**: image tạo `hub` UID 999, compose chạy `1000:1000`; bind mount data thuộc 1000 | Dockerfile tạo user thường UID/GID 1000 (`ARG HUB_UID/HUB_GID`), compose `user: ${...}` + build args. Đo: `id` → `uid=1000`, `/du-lieu 1000:1000 700`, volume ẩn danh ghi được |
| B-2 | **`.env` lọt vào image**: `.dockerignore` khớp `.env` không đệ quy; `COPY trien_khai/` mang `trien_khai/vps/.env` + `.env.production.example` vào `/app` | Dockerfile COPY **tường minh** entrypoint + bootstrap; `test -z "$(find /app ... '.env*')"`. Đo image cũ có 2 tệp; **cả hai image đang có trên VPS `vip-express-hub:2026-10-19` và `:vps-c04c619` cũng chứa `/app/trien_khai/vps/.env` + `.env.production.example`** — không dùng chúng để deploy; rebuild từ Dockerfile mới rồi Owner quyết định xoá image cũ. Image cuối `FIND_DONE` rỗng. Lượt test chỉ có `.env` mẫu (không bí mật thật), nhưng production `.env` có thể có giá trị thật — **cần** sửa root `.dockerignore` thành `**/.env` (ngoài phạm vi) |
| B-3 | **Quy trình Caddy bất khả thi**: `/etc/caddy/Caddyfile` là bind mount **ro**; README cũ bảo `docker exec ... cat >>` → `Read-only file system` | `kiem_caddy.sh` validate live + candidate trong `/tmp` container, không ghi live; README/Caddyfile hướng dẫn Owner/root ghi **in-place** file host. Đo: live + candidate `Valid configuration`; live sha256 không đổi; Caddy restarts 0 |
| B-4 | **Backup chọn sai bản**: `ls -t hub-*.db` có thể chép bản cũ; không kiểm checksum nguồn/integrity; passphrase qua `-e`; path container/host lẫn | `backup.sh` lấy đúng path `sao_luu()` trả, map `/du-lieu` → host, đòi mtime > mốc, verify `.sha256` nguồn + `PRAGMA integrity_check`, `flock`, `docker exec` theo `container_name`, passphrase qua stdin. Đo: DB + `.vipkb` 818 B, header `VIPHUBKEYBAK` |
| B-5 | **Restore mất WAL / dính WAL cũ / kiểm schema sau khi mở cổng / DB cũ thiếu thì không rollback** | Snapshot cũ bằng SQLite backup API (gộp WAL), xoá `-wal/-shm` trước khi đặt DB mới, `migrate --kiem` bằng container một-lần **trước** `up`, rollback nếu lỗi. Test shim: success + rollback giữ nguyên dữ liệu logic |
| B-6 | **Bootstrap seed quyền trước khi kiểm user** (ghi vào DB đang chạy rồi mới từ chối); khe race hai lượt | Kiểm user/tenant/plan + seed + insert trong **một transaction** `BEGIN IMMEDIATE`; hash mật khẩu tính trước transaction. Đo: lần 2 exit 1, counts không đổi |
| B-7 | **Bind mount short syntax** để Docker tự tạo `data/` bằng root; thiếu trần tài nguyên; thiếu `.env.production.example` trong repo (bị `.gitignore` chặn) | Compose long syntax `create_host_path: false`; `chuan_bi.sh` tạo/kiểm data + backups; `mem_limit 512m`, `pids_limit 512`; template + `.gitignore` cục bộ mở ngoại lệ; `docker compose config` OK |
| B-8 | **`kiem_tra.sh` vừa báo đỏ giả vừa bỏ qua lỗi thật**: webhook mã lạ thực tế 404 nhưng kỳ vọng 401; HSTS dùng HEAD nhưng app trả 501; `ss` chỉ in, không fail khi bind ngoài; không kiểm container health | Kỳ vọng webhook **404**; HSTS dùng **GET**; kiểm `ss` chỉ loopback và fail nếu hở; chờ/kiểm health container; kiểm bind mount + mode data |
| B-9 | **Base image không ghim** | `ARG PYTHON_IMAGE=python:3.11-slim-bookworm@sha256:0a310…f5f89` (digest đo trên VPS) |
| B-10 | `khao_sat.sh` gọi host BEST (TLS ẩn danh) dù lượt này cấm gọi BEST | Gate sau `KHAO_SAT_BEST=1`; mặc định in "BỎ QUA" |

**Giả thuyết đã bị phủ định (không vá):** tưởng migration không tạo khóa nên thiếu bước
init. Đo thực tế migration tạo `data/khoa/goc.key` + `hien-hanh`, readiness đạt; không thêm
script tự sinh khóa (tự sinh khi mất khóa cũ sẽ che mất sự cố).

### 10.2 Bằng chứng chính (staging)

```sh
cd /home/deploy/vip-express-hub/ag06-review/src/trien_khai/vps
docker compose config --quiet            # COMPOSE_CONFIG_OK
sh chuan_bi.sh                           # OK: data/backups 700, chủ 1000:1000
docker compose build                     # vip-express-hub:ag06-review, id 90af23af65be, 232 MB
docker run --rm --entrypoint id vip-express-hub:ag06-review   # uid=1000(hub)
docker run --rm --entrypoint sh ... find /app -name '.env*'   # rỗng
sh kiem_caddy.sh                         # live + candidate Valid; live hash không đổi
```

Self-test cuối (data riêng, `--network none`): migration schema 10; `/suc-khoe` 200; `/san-sang`
200; UAT 200; health **6 s**; restart **7 s** (wall 17 s); auth-required 401; webhook mã lạ 404.
Port-mapped `127.0.0.1:18898→8897`: 200/200/200, HSTS trên GET, cookie `Secure; HttpOnly` khi
login có `X-Requested-With: VIPHub`. Sau test: container/data/log đã xoá; `NO_APP_CONTAINER`;
cổng 18897/18898 trống.

Backup: `backup.sh` chạy với container cô lập — `hub.db` 568K, `.sha256` OK, integrity `ok`,
52 bảng; gói khoá 818 B. Restore: shim `docker`/`curl` — success đổi đúng DB; rollback khi
`migrate --kiem` hỏng giữ nguyên users/tenants/membership/schema; **chưa** chạy `compose up`
thật.

### 10.3 Điều KHÔNG làm trong lượt này

- Không thêm khối Caddy, không `caddy reload`/`restart`; live Caddyfile hash
  `c0ae5314b634782d914ddb35f4fe06eca911faa14b2b0da5b89173253e1c74ad` trước/sau giống nhau,
  Caddy started `2026-10-19T13:26:02Z`, restarts 0.
- Không đổi DNS (`best-uat.viporder.vn` vẫn NO_DNS), firewall, cổng 80/443.
- Không `docker compose up -d`, không tạo DB/admin thật, không cài cron, không gọi BEST.
- Không ghi vào `/home/deploy/vip-express-hub/src` (production source); chỉ staging
  `ag06-review`. Không push.

### 10.4 Cần Owner duyệt trước khi làm thật

1. DNS `A best-uat.viporder.vn → 160.22.170.20` (DNS-only).
2. Caddy: Owner/root backup + ghi **in-place** file host; deploy validate + reload.
3. Copy source AG-06 vào `/home/deploy/vip-express-hub/src` (thay bản cũ) và chạy
   `chuan_bi.sh` / `compose config` / `build`.
4. Migration + bootstrap admin trên DB thật; mật khẩu Owner tự nhập qua stdin.
5. `docker compose up -d` + `kiem_tra.sh`.
6. Cron backup + diễn tập restore thật.
7. BEST sandbox credential + cửa sổ `VIP_BEST_OWNER_APPROVED=1`; không production.

### 10.5 Kết luận AG-06

Bộ deploy đã **build được**, **self-test healthy/restart healthy**, compose/Caddy validate OK,
image sạch `.env*` và đúng UID 1000. Các lỗi quyền/backup/restore/Caddy/kiểm tra ở trên đã được
vá trong phạm vi. **Chưa** có bằng chứng nào cho phép nói dịch vụ đã chạy thật: DNS, Caddy,
`up -d`, admin thật, restore thật đều còn chờ Owner.
