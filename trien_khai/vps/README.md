# VIP Express Hub — VPS 160.22.170.20 (runbook)

**Trạng thái:** đã khảo sát, đã build image và self-test cô lập; **CHƯA** thêm Caddy site,
**CHƯA** mở dịch vụ ra Internet, **CHƯA** đổi DNS/firewall, **CHƯA** gọi BEST bằng credential thật.
Mọi bước đánh dấu **[CẦN DUYỆT]** phải có xác nhận của Owner trước khi chạy.

## 0. Thông tin đã đo (2026-10-19)

| Mục | Giá trị |
|---|---|
| Host | Ubuntu 26.04 LTS, kernel 7.0.0-34, VMware, 4 vCPU Xeon 8272CL |
| RAM/swap | 7,2 GiB (5,3 GiB available) · swap 2 GiB |
| Disk | 89 GB, dùng 26 GB, còn **59 GB** · inode 10% |
| Docker | 29.1.3 · Compose v5.6.0 · user `deploy` thuộc group `docker` |
| sudo | **KHÔNG** có (sudo -n từ chối) — thao tác root phải qua `docker exec` hoặc Owner cấp |
| Cổng 80/443 | Caddy dùng chung `vip-staging-caddy`, `network_mode=host`; Caddyfile `/srv/vip-staging-proxy/Caddyfile` |
| App port đề xuất | `127.0.0.1:18897` (đang trống) |
| Domain đề xuất | `best-uat.viporder.vn` — **chưa có A record**; cần Owner tạo A → 160.22.170.20 |
| Domain KHÔNG dùng | `best-uat.viporder.com.vn` đang trỏ 103.159.50.70 (sai VPS) |
| Docker image | `vip-express-hub:2026-10-19` (232 MB) — build từ source đã copy |
| Self-test | health 200, ready 200, restart healthy, login admin 200, cookie `Secure`, trang UAT 200 |

## 1. Cấu trúc trên VPS

```
/home/deploy/vip-express-hub/
├── src/                         # source đã copy (không chứa .env, DB, docs)
│   └── trien_khai/vps/          # compose + runbook + script
├── data/                        # bind mount /du-lieu — DB + khoá, mode 700
├── backups/                     # bản sao lưu DB/key, mode 700
└── selftest-*                   # chỉ tạo/xoá trong lúc đo
```

Container `vip-express-hub` chạy `user 1000:1000`, root filesystem `read_only`, `cap_drop: ALL`,
`no-new-privileges`, chỉ bind `127.0.0.1:18897`. Caddy (host network) proxy vào.

## 2. Chuẩn bị (đã làm, không ảnh hưởng dịch vụ khác)

```sh
# trên VPS
cd /home/deploy/vip-express-hub/src/trien_khai/vps
cp -n .env.production.example .env && chmod 600 .env
docker compose config          # OK
docker compose build           # OK — image 232 MB
```

Image đã sửa quyền đọc: `chmod -R a+rX /app` trước `chmod -R a-w /app`. Nếu không, container
`hub` (UID 999) không đọc được file source mode 600 và chết ngay khi import.

## 3. [CẦN DUYỆT] DNS

Owner/DNS admin tạo:

```
best-uat.viporder.vn.  A  160.22.170.20
```

- DNS-only (không bật proxy Cloudflare) để Caddy xin Let's Encrypt HTTP-01.
- Kiểm: `dig +short best-uat.viporder.vn` → `160.22.170.20`.
- Không sửa bản ghi `viporder.vn` apex (đang ở 160.22.171.228) hay `cpn/qua`.

## 4. [CẦN DUYỆT] Thêm Caddy site (zero-downtime)

Caddyfile là file root-owned; `deploy` không có sudo. Cách đã chuẩn bị là ghi qua container
Caddy (chạy root), **sau khi** backup và validate:

```sh
# 1) backup ra home deploy (không ghi đè file root)
docker exec vip-staging-caddy cat /etc/caddy/Caddyfile \
  > ~/Caddyfile.bak-$(date +%F-%H%M)

# 2) dán khối đã duyệt
docker exec -i vip-staging-caddy sh -c 'cat >> /etc/caddy/Caddyfile' \
  < /home/deploy/vip-express-hub/src/trien_khai/vps/Caddyfile.best-uat

# 3) validate TRƯỚC khi reload
docker exec vip-staging-caddy caddy validate \
  --config /etc/caddy/Caddyfile --adapter caddyfile

# 4) reload (không restart)
docker exec vip-staging-caddy caddy reload \
  --config /etc/caddy/Caddyfile --adapter caddyfile
```

Rollback: ghi lại file backup bằng `cat > /etc/caddy/Caddyfile`, validate, reload. Không
`restart` container Caddy; reload là graceful.

Khối Caddy có HSTS, `X-Robots-Tag: noindex`, `request_body max_size 1MB`, proxy
`127.0.0.1:18897`, log `/data/access-vip-express-hub.log`.

## 5. [CẦN DUYỆT] Khởi tạo DB + admin + chạy service

```sh
cd /home/deploy/vip-express-hub/src/trien_khai/vps

# 5.1 migration fresh DB (bắt buộc; entrypoint KHÔNG tự migrate)
docker compose run --rm -e VIP_KHO_DANG_CHAY=sqlite \
  --entrypoint python3 hub /app/app/migrate.py

# 5.2 tạo tenant + owner; mật khẩu đi qua stdin, KHÔNG vào argv/log
printf '%s\n' "$MAT_KHAU_OWNER" | docker compose run --rm -T \
  --entrypoint python3 hub /app/trien_khai/vps/bootstrap_admin.py

# 5.3 bật cổng Owner cho sandbox UAT (chỉ trong cửa sổ nghiệm thu)
#     sửa .env: VIP_BEST_OWNER_APPROVED=1, VIP_BEST_OWNER_APPROVAL_ID=OWNER-UAT-...
#     KHÔNG đặt production; production ghi vẫn bị khoá trong mã.

# 5.4 khởi động
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:18897/api/v2/suc-khoe
```

Sau khi Caddy + DNS xong:

```sh
sh /home/deploy/vip-express-hub/src/trien_khai/vps/kiem_tra.sh
```

## 6. Backup / restore

- DB: `sao_luu()` của app (SQLite backup API) + copy ra `backups/<ts>/hub.db` + `.sha256`,
  giữ 14 ngày. Cron **chưa cài**; cần Owner duyệt.
- Khoá mã hoá: `sao_luu_khoa.py tao ...vipkb` với passphrase Owner giữ; DB backup một mình
  **không đủ** khôi phục credential nếu mất `data/khoa`.
- Restore: `restore.sh <backup>` yêu cầu `TOI_DONG_Y_PHUC_HOI=TOI_DONG_Y_PHUC_HOI`; tự giữ
  bản `hub.db.truoc-phuc-hoi-<ts>`, chạy health + `migrate --kiem`. **Chưa chạy thử on VPS**;
  phải diễn tập trên bản copy trước khi tin.
- Không dùng `/tmp` cho DB/backup nghiệp vụ.

## 7. Việc chưa làm / rủi ro

| # | Việc | Trạng thái |
|---|---|---|
| 1 | DNS `best-uat.viporder.vn` | **BLOCKED — chờ Owner/DNS** |
| 2 | Thêm khối Caddy + reload | **CHỜ DUYỆT** (thay đổi reverse proxy dùng chung) |
| 3 | `docker compose up -d` | **CHỜ DUYỆT** |
| 4 | Tạo admin/tenant trên DB thật | **CHỜ DUYỆT** + mật khẩu Owner |
| 5 | Credential BEST sandbox | **BLOCKED — BEST/Owner cấp** |
| 6 | Webhook BEST gọi thật | **BLOCKED — cần DNS/Caddy + BEST cấu hình** |
| 7 | Cron backup | **CHỜ DUYỆT** |
| 8 | Diễn tập restore | **CHƯA CHẠY** |
| 9 | Firewall | Không cần đổi: 80/443 đã mở cho Caddy; app chỉ loopback |
| 10 | Production BEST | **KHOÁ TRONG MÃ** — không mở ở lượt này |

## 8. Lệnh không được chạy khi chưa duyệt

```sh
docker compose down -v          # xoá volume/data — CẤM
docker system prune -a          # ảnh hưởng dịch vụ khác — CẤM
docker restart vip-staging-caddy # dùng reload, không restart
# sửa /srv/vip-staging-proxy/Caddyfile trực tiếp khi chưa backup/validate — CẤM
```
