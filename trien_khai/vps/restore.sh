#!/bin/sh
# KHÔI PHỤC DB từ một thư mục backup — CHỈ chạy khi Owner đã duyệt và có cửa sổ bảo trì.
# Không tự chạy. Không khôi phục gói khoá ở đây; gói khoá dùng sao_luu_khoa.py khoi-phuc.
set -eu

GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
COMPOSE_DIR="$GOC/src/trien_khai/vps"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
BACKUP="${1:-}"
[ -n "$BACKUP" ] || { echo "dùng: $0 <thư-mục-backup>" >&2; exit 2; }
[ -f "$BACKUP/hub.db" ] || { echo "thiếu $BACKUP/hub.db" >&2; exit 2; }
[ "${TOI_DONG_Y_PHUC_HOI:-}" = "TOI_DONG_Y_PHUC_HOI" ] || {
  echo "TỪ CHỐI: đặt TOI_DONG_Y_PHUC_HOI=TOI_DONG_Y_PHUC_HOI sau khi Owner duyệt" >&2; exit 3; }

( cd "$BACKUP" && sha256sum -c hub.db.sha256 )
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" stop hub
TS="$(date +%Y%m%d-%H%M%S)"
cp -p "$GOC/data/hub.db" "$GOC/data/hub.db.truoc-phuc-hoi-$TS"
cp -p "$BACKUP/hub.db" "$GOC/data/hub.db"
chmod 600 "$GOC/data/hub.db"
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" up -d hub
i=0
while [ "$i" -lt 60 ]; do
  if curl -fsS --max-time 3 http://127.0.0.1:18897/api/v2/suc-khoe >/dev/null 2>&1; then break; fi
  i=$((i+1)); sleep 2
done
[ "$i" -lt 60 ] || { echo "[restore] health KHÔNG lên sau 120s — KHÔNG tự xoá bản trước" >&2; exit 4; }
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" exec -T \
  -e VIP_KHO_DANG_CHAY=sqlite hub python3 /app/app/migrate.py --kiem
echo "[restore] xong. Bản trước: $GOC/data/hub.db.truoc-phuc-hoi-$TS"
