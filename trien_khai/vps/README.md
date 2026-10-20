# VIP Express Hub — VPS 160.22.170.20 (runbook)

**Trạng thái (AG-06, 2026-10-19):** đã review bộ deploy, build image và self-test cô lập;
**CHƯA** thêm site Caddy, **CHƯA** `docker compose up -d`, **CHƯA** tạo DB/admin thật, **CHƯA**
đổi DNS/firewall, **CHƯA** gọi BEST. Mọi bước đánh dấu **[CẦN DUYỆT]** phải có xác nhận của
Owner trước khi chạy. Bằng chứng chi tiết ở `docs/VPS_DEPLOYMENT_SURVEY.md` mục 10.

## 0. Thông tin đã đo (2026-10-19)

| Mục | Giá trị |
|---|---|
| Host | Ubuntu 26.04 LTS, kernel 7.0.0-34, VMware, 4 vCPU Xeon 8272CL |
| RAM/swap | 7,2 GiB (5,3 GiB available) · swap 2 GiB |
| Disk | 89 GB, dùng 26 GB, còn **59 GB** · inode 10% |
| Docker | 29.1.3 · Compose v5.6.0 · user `deploy` UID/GID **1000:1000**, group `docker` |
| sudo | **KHÔNG** có (sudo -n từ chối) — thao tác root cần Owner/root |
| Cổng 80/443 | Caddy dùng chung `vip-staging-caddy`, `network_mode=host`; Caddyfile host `/srv/vip-staging-proxy/Caddyfile` |
| App port | `127.0.0.1:18897` (đang trống) |
| Domain | `best-uat.viporder.vn` — **CHƯA có A record**; cần Owner tạo A → 160.22.170.20 |
| Domain KHÔNG dùng | `best-uat.viporder.com.vn` đang trỏ 103.159.50.70 (sai VPS) |
| Image review | `vip-express-hub:ag06-review` · 232 MB · id `90af23af65be` · user `hub` UID/GID 1000 |
| Self-test cuối | migration schema 10 · health **200**, ready **200**, UAT **200** · health 6 s, restart 7 s · không có `.env*` trong image |
| Caddy | live + candidate `Valid configuration`; live **không đổi** sha256 `c0ae…c74ad`; container started 13:26:02Z, restarts 0 |

## 1. Cấu trúc trên VPS

```
/home/deploy/vip-express-hub/
├── src/                         # source copy + .env runtime (mode 600), không DB/docs
│   └── trien_khai/vps/          # compose + runbook + script
├── data/                        # bind mount /du-lieu — DB + khoá, mode 700, UID 1000
├── backups/                     # bản sao lưu DB/key, mode 700
└── ag06-review/                 # staging của lượt review: src/ + data/ rỗng, KHÔNG phải dịch vụ
```

Container `vip-express-hub` (khi được duyệt) chạy `user 1000:1000`, root filesystem
`read_only`, `cap_drop: ALL`, `no-new-privileges`, chỉ bind `127.0.0.1:18897`; Caddy host
network proxy vào. Image tạo user `hub` **UID/GID 1000** (trước AG-06 là 999, lệch compose).

## 2. Chuẩn bị (không khởi động dịch vụ)

```sh
# trên VPS, trong source đã copy
cd /home/deploy/vip-express-hub/src/trien_khai/vps
cp -n .env.production.example .env      # mẫu đã track; KHÔNG chứa bí mật thật
chmod 600 .env
# sửa VIP_HUB_UID/GID nếu `id -u`/`id -g` khác 1000
sh chuan_bi.sh                         # tạo data/ + backups/ mode 700, đúng chủ sở hữu
docker compose config                   # chỉ kiểm cú pháp
docker compose build                    # build image; KHÔNG chạy container
```

- `chuan_bi.sh` là bắt buộc vì compose dùng bind mount `create_host_path: false`: thiếu
  `data/` thì `up` báo lỗi rõ, thay vì để Docker tạo thư mục bằng root rồi app UID 1000 chết.
- `.env` **không được** nằm trong image. Dockerfile COPY từng tệp runtime (entrypoint +
  `bootstrap_admin.py`) và có phép `test` chặn `.env*`; root `.dockerignore` chỉ khớp `.env`
  ở gốc context, **không** khớp `trien_khai/vps/.env` (đã đo — xem mục 10).
- Image ghim digest base `python:3.11-slim-bookworm@sha256:0a310…f5f89`; đổi digest thì sửa
  `ARG PYTHON_IMAGE` trong Dockerfile.

## 3. [CẦN DUYỆT] DNS

Owner/DNS admin tạo:

```
best-uat.viporder.vn.  A  160.22.170.20
```

- DNS-only (không bật proxy Cloudflare) để Caddy xin Let's Encrypt HTTP-01.
- Kiểm: `dig +short best-uat.viporder.vn` → `160.22.170.20`.
- Không sửa bản ghi `viporder.vn` apex (đang ở 160.22.171.228) hay `cpn/qua`.
- Đo 2026-10-19: **chưa có bản ghi** (`getent hosts` → NO_DNS).

## 4. [CẦN DUYỆT] Thêm Caddy site (không restart)

**Sự thật đã đo:** `/etc/caddy/Caddyfile` trong container là bind mount **READ-ONLY** từ
`/srv/vip-staging-proxy/Caddyfile` (root:root 644). Vì vậy cách cũ
`docker exec ... cat >> /etc/caddy/Caddyfile` **KHÔNG chạy được** (`Read-only file system`),
và `deploy` không có sudo. Chỉ Owner/root ghi được file host.

Quy trình đúng:

```sh
# 1) Validate live + candidate, KHÔNG ghi gì, KHÔNG reload
cd /home/deploy/vip-express-hub/src/trien_khai/vps
sh kiem_caddy.sh

# 2) Owner/root backup file host
sudo cp -p /srv/vip-staging-proxy/Caddyfile \
            /srv/vip-staging-proxy/Caddyfile.bak-$(date +%F-%H%M)

# 3) Owner/root ghi IN-PLACE (không dùng mv/install đè inode — container đang giữ inode cũ)
{ docker exec vip-staging-caddy cat /etc/caddy/Caddyfile; printf '\n\n';
  cat Caddyfile.best-uat; } > ~/Caddyfile.best-uat.candidate
sudo sh -c 'cat /home/deploy/Caddyfile.best-uat.candidate \
            > /srv/vip-staging-proxy/Caddyfile'

# 4) Validate file live RỒI MỚI reload (graceful, KHÔNG restart)
docker exec vip-staging-caddy caddy validate \
  --config /etc/caddy/Caddyfile --adapter caddyfile
docker exec vip-staging-caddy caddy reload \
  --config /etc/caddy/Caddyfile --adapter caddyfile
```

Rollback: Owner/root ghi backup **in-place** (`sudo sh -c 'cat backup > file'`), validate,
reload. Không `docker restart vip-staging-caddy`; không sửa file host khi chưa backup/validate.

Khối Caddy có HSTS, `X-Robots-Tag: noindex`, `request_body max_size 1MB`, proxy
`127.0.0.1:18897`, log `/data/access-vip-express-hub.log`. Đo 2026-10-19:
`kiem_caddy.sh` → **Valid configuration** cho cả live và candidate; live hash không đổi.

## 5. [CẦN DUYỆT] Khởi tạo DB + admin + chạy service

```sh
cd /home/deploy/vip-express-hub/src/trien_khai/vps

# 5.1 migration fresh DB (bắt buộc; entrypoint KHÔNG tự migrate)
#     Đo 2026-10-19: migration tạo schema 10 VÀ tạo khóa mã hóa đầu tiên `data/khoa/goc.key`
#     (mode 600) + con trỏ `hien-hanh`; readiness sau đó ĐẠT. KHÔNG tự tạo khóa thay thế nếu
#     thư mục khóa bị mất — lúc đó readiness đỏ và phải điều tra, không che bằng khóa mới.
docker compose run --rm -e VIP_KHO_DANG_CHAY=sqlite \
  --entrypoint python3 hub /app/app/migrate.py

# 5.2 kiểm readiness trên CSDL vừa migrate (worker được bỏ qua có ghi chú)
docker compose run --rm -e VIP_KHO_DANG_CHAY=sqlite \
  --entrypoint python3 hub -c \
  'import sys,json; sys.path.insert(0,"/app/app"); import quan_sat; kq=quan_sat.san_sang(bo_qua=("worker",)); print(json.dumps(kq,ensure_ascii=False)); sys.exit(0 if kq["ok"] else 1)'

# 5.3 tạo tenant + owner; mật khẩu đi qua stdin, KHÔNG vào argv/log
printf '%s\n' "$MAT_KHAU_OWNER" | docker compose run --rm -T \
  --entrypoint python3 hub /app/trien_khai/vps/bootstrap_admin.py

# 5.4 bật cổng Owner cho sandbox UAT (chỉ trong cửa sổ nghiệm thu)
#     sửa .env: VIP_BEST_OWNER_APPROVED=1, VIP_BEST_OWNER_APPROVAL_ID=OWNER-UAT-...
#     KHÔNG đặt production; production ghi vẫn bị khoá trong mã.

# 5.5 khởi động (CHỜ OWNER DUYỆT)
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:18897/api/v2/suc-khoe
curl -fsS http://127.0.0.1:18897/api/v2/san-sang
```

`bootstrap_admin.py` từ chối nếu CSDL đã có user; lần chạy thứ hai đo được exit 1 và số
user/tenant/role không đổi. Việc seed role/permission nằm **trong cùng transaction** với phần
kiểm tra, nên lượt từ chối không ghi gì.

Sau khi Caddy + DNS xong:

```sh
sh /home/deploy/vip-express-hub/src/trien_khai/vps/kiem_tra.sh
```

`kiem_tra.sh` kiểm container health (chờ tối đa 60 s), bind mount `/du-lieu`, quyền data 700,
health/ready/UAT, 401 khi chưa đăng nhập, webhook mã lạ **404 fail-closed**, cổng 18897 **chỉ
loopback** (fail nếu bind ngoài), HSTS bằng **GET** (app không hỗ trợ HEAD — trả 501), và TLS.
Bản cũ dùng HEAD nên cổng HSTS luôn đỏ; bản cũ cũng chỉ in `ss` mà không fail khi cổng hở.

## 6. Backup / restore

- DB: `migrate.sao_luu()` (SQLite backup API) + copy ra `backups/<ts>/hub.db` + `.sha256`,
  giữ 14 ngày. `backup.sh` lấy **đúng đường dẫn** app trả về (đổi `/du-lieu/...` → host
  `$GOC/data/...`), đòi tệp mới hơn mốc bắt đầu, kiểm `.sha256` nguồn, kiểm integrity bản
  chép, khoá `flock`, và dùng `docker exec` theo `container_name` (không phụ thuộc label
  Compose). Cron **chưa cài**; cần Owner duyệt.
- Khoá mã hoá: `sao_luu_khoa.py tao ...vipkb` với passphrase Owner giữ. Bản AG-06 truyền
  passphrase qua **stdin** (`docker exec -i`), không qua `-e`/argv. DB backup một mình
  **không đủ** khôi phục credential nếu mất `data/khoa`.
- Restore: `restore.sh <backup>` yêu cầu `TOI_DONG_Y_PHUC_HOI=TOI_DONG_Y_PHUC_HOI`; kiểm
  checksum + integrity trước khi dừng dịch vụ; snapshot DB cũ bằng SQLite backup API (gộp
  WAL); xoá `hub.db-wal/-shm` cũ trước khi đặt DB mới; chạy `migrate --kiem` bằng container
  một-lần **trước** `up`; health + readiness; rollback DB cũ nếu bất kỳ bước nào hỏng.
- **Chưa chạy restore thật trên VPS** (không được `docker compose up -d` trong lượt này).
  Đã diễn tập logic bằng `docker`/`curl` giả: success + rollback giữ nguyên dữ liệu logic;
  **vẫn phải diễn tập trên bản copy trước khi tin**.
- Không dùng `/tmp` cho DB/backup nghiệp vụ.

## 7. Việc chưa làm / rủi ro còn lại

| # | Việc | Trạng thái |
|---|---|---|
| 1 | DNS `best-uat.viporder.vn` | **BLOCKED — chờ Owner/DNS** (đo: NO_DNS) |
| 2 | Thêm khối Caddy + reload | **CHỜ DUYỆT** — file host root-owned + mount ro; Owner/root ghi in-place |
| 3 | `docker compose up -d` | **CHỜ DUYỆT** — lượt AG-06 KHÔNG chạy |
| 4 | Tạo admin/tenant trên DB thật | **CHỜ DUYỆT** + mật khẩu Owner |
| 5 | Credential BEST sandbox | **BLOCKED — BEST/Owner cấp** |
| 6 | Webhook BEST gọi thật | **BLOCKED — cần DNS/Caddy + BEST cấu hình** |
| 7 | Cron backup | **CHỜ DUYỆT** |
| 8 | Diễn tập restore thật | **CHƯA CHẠY** — mới test logic bằng shim |
| 9 | Firewall | Không cần đổi: 80/443 đã mở cho Caddy; app chỉ loopback |
| 10 | Production BEST | **KHOÁ TRONG MÃ** — không mở ở lượt này |
| 11 | `VIP_HUB_PROXY_TIN_CAY` | **CHƯA ĐO** — để trống; rate limit/audit IP sau Docker port mapping có thể gộp. Đo log gateway rồi mới điền, không tin dải rộng |
| 12 | HEAD request | App trả **501** cho HEAD; monitor bên ngoài phải dùng GET. Caddy không chặn HEAD |
| 13 | Base image digest | Đã ghim digest đo trên VPS; cần quy trình nâng digest có review |
| 14 | Root `.dockerignore` | `.env`/`.env.*` **không** khớp file lồng; image mới đã chặn bằng COPY tường minh, nhưng **hai image cũ `2026-10-19` và `vps-c04c619` đang chứa `/app/trien_khai/vps/.env`** — không dùng để deploy; rebuild/remove sau duyệt. Nên sửa `.dockerignore` thành `**/.env` |

## 8. Lệnh không được chạy khi chưa duyệt

```sh
docker compose down -v          # xoá volume/data — CẤM
docker system prune -a          # ảnh hưởng dịch vụ khác — CẤM
docker restart vip-staging-caddy # dùng reload, không restart
# sửa /srv/vip-staging-proxy/Caddyfile trực tiếp khi chưa backup/validate — CẤM
# docker compose up -d khi chưa có duyệt — CẤM
```

## 10. CẬP NHẬT TỪ GITHUB (canonical)

Checkout chuẩn trên VPS: `/home/deploy/vip-express-hub/app` (clone từ
`https://github.com/thanhbn123/vip-exp-hub`, nhánh `main`). Thư mục `src` cũ chỉ là bản
trước khi chuyển Git; không sửa ở đó.

```sh
cd /home/deploy/vip-express-hub/app
./trien_khai/vps/deploy.sh
```

Script pull fast-forward, build image tag theo commit, `docker compose up -d`, kiểm health.
`.env` nằm trong `trien_khai/vps/.env` (không commit). Không chạy `git reset --hard`/`down -v`.
