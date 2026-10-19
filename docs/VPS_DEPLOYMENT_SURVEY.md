# VIP EXPRESS HUB — KHẢO SÁT & PHƯƠNG ÁN TRIỂN KHAI VPS 160.22.170.20

**Ngày:** 2026-10-19 · **Trạng thái:** ĐÃ KHẢO SÁT + ĐÃ BUILD/SELF-TEST CÔ LẬP.
**CHƯA** đổi DNS, **CHƯA** thêm site Caddy, **CHƯA** mở dịch vụ ra Internet, **CHƯA** gọi BEST
bằng credential thật. Các mục **[CẦN DUYỆT]** chờ Owner.

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

| Việc | Bằng chứng |
|---|---|
| Source copy lên `/home/deploy/vip-express-hub/src` | `rsync` exit 0; không có `.env`, DB, docs |
| Compose validate | `docker compose config` exit 0 trên VPS |
| Caddy block validate | `caddy validate` → **Valid configuration** (container tạm, không reload) |
| Build image | `vip-express-hub:2026-10-19` · 232 MB · build exit 0 |
| Sửa quyền image | `chmod -R a+rX /app` trước `a-w`; nếu thiếu, container chết `PermissionError` |
| Self-test cô lập | `--network none`, health **healthy** sau ~6s; `/suc-khoe` 200; `/san-sang` 200 |
| Restart test | restart → **healthy** sau ~6s |
| Port-mapped test | `127.0.0.1:18898` → admin 200, UAT 200, login 200, cookie `Secure`, API 200 |
| Dọn test | container + data test đã xoá; **không** đụng compose/container hiện có |

**Chưa làm:** chưa thêm khối Caddy, chưa `docker compose up -d`, chưa tạo DB/admin thật, chưa
đổi DNS/firewall, chưa cài cron backup, chưa gọi BEST.

---

## 5. CẤU HÌNH DATABASE / BACKUP

- `VIP_HUB_DATA=/du-lieu` → bind `/home/deploy/vip-express-hub/data` (mode 700, UID 1000).
- Migration fresh: `docker compose run --rm -e VIP_KHO_DANG_CHAY=sqlite --entrypoint python3 hub /app/app/migrate.py` → schema 10, bảo toàn 0 dòng.
- Bootstrap admin: `bootstrap_admin.py` tạo tenant + `PLATFORM_OWNER` + `TENANT_OWNER`; **từ chối**
  nếu DB đã có user; mật khẩu qua stdin, không in.
- Backup DB: `sao_luu()` (SQLite backup API) → `backups/<ts>/hub.db` + `.sha256`; giữ 14 ngày.
- Backup khoá: `sao_luu_khoa.py tao ...vipkb` với passphrase Owner giữ; **DB một mình không đủ**
  khôi phục credential nếu mất `data/khoa`.
- Restore: `restore.sh` yêu cầu câu xác nhận, giữ bản trước, health + `migrate --kiem`.
- **Chưa cài cron**; cần Owner duyệt. Không dùng `/tmp` cho DB/backup nghiệp vụ.
- Diễn tập restore trên bản copy **chưa chạy**; phải làm trước khi tin.

---

## 6. RỦI RO / VẤN ĐỀ CÒN TỒN TẠI

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| 1 | Caddyfile root-owned, `deploy` không sudo | Cao | Ghi qua `docker exec` (root) sau backup; validate; reload; rollback đã soạn |
| 2 | Shared Caddy lỗi làm sập nhiều site | Cao | Chỉ append site mới; `caddy validate` trước; reload graceful; giữ backup; không restart |
| 3 | DNS chưa có, chưa xin được cert | Cao | Chờ Owner tạo A record; kiểm `dig` trước |
| 4 | DB SQLite + khoá nằm cùng ổ | Trung bình | Bind mount persistent; backup DB + key package; chưa có NAS/offsite |
| 5 | Chưa diễn tập restore | Trung bình | Chạy trên bản copy trước khi mở dịch vụ |
| 6 | Backup cron chưa cài | Trung bình | Cài sau duyệt; theo dõi dung lượng 59 GB |
| 7 | App chỉ hỗ trợ SQLite | Trung bình | Chấp nhận cho UAT; muốn Postgres phải làm adapter riêng |
| 8 | `deploy` không sudo | Trung bình | Docker group đủ cho container/Caddy exec; firewall/DNS cần Owner |
| 9 | Rate limit sau proxy có thể gộp IP | Thấp | Đo log, điền `VIP_HUB_PROXY_TIN_CAY` sau; app chỉ loopback |
| 10 | Credential BEST thật | Cao | Chỉ nhập qua HTTPS; mã hoá; không log/chat; Owner phê duyệt |

---

## 7. CẦN OWNER PHÊ DUYỆT (từng mục)

1. **DNS**: đồng ý dùng `best-uat.viporder.vn`, tạo `A 160.22.170.20` (DNS-only) và báo khi có.
2. **Caddy**: đồng ý thêm khối `best-uat.viporder.vn` vào Caddy dùng chung, backup + validate +
   reload (không restart); chấp nhận rủi ro reverse proxy dùng chung.
3. **Dịch vụ**: đồng ý tạo `/home/deploy/vip-express-hub/data`, chạy migration, bootstrap admin,
   `docker compose up -d` trên cổng loopback `18897`.
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

`kiem_tra.sh` kiểm: container, health/ready, trang UAT, 401 khi chưa đăng nhập, webhook thiếu
Bearer 401, HSTS, TLS cert, cổng app chỉ loopback.

---

## 9. KẾT LUẬN

- VPS **đủ tài nguyên** cho VIP Express Hub (4 vCPU, 5,3 GiB RAM trống, 59 GB disk).
- **Không cần firewall/NAT mới**: Caddy đã giữ 80/443; app chỉ loopback.
- **Cần DNS + một khối Caddy**; đây là thay đổi reverse proxy dùng chung, phải được duyệt.
- Image đã build và self-test **healthy/restart healthy**; chưa phải triển khai thật.
- **Chưa có URL công khai** cho đến khi DNS + Caddy được duyệt.
- **Chưa có REAL PASS/OWNER APPROVED**; mọi tuyên bố như vậy là sai.
