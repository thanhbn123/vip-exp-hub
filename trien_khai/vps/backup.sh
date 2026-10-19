#!/bin/sh
# Sao lưu DB + (tuỳ chọn) gói khoá mã hoá của VIP Express Hub trên VPS.
# KHÔNG đặt passphrase vào cron. Chạy tay khi cần gói khoá; cron chỉ sao lưu DB.
set -eu

GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
COMPOSE_DIR="$GOC/src/trien_khai/vps"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
TS="$(date +%Y%m%d-%H%M%S)"
DICH="$GOC/backups/$TS"

[ -f "$COMPOSE" ] || { echo "[backup] thiếu compose: $COMPOSE" >&2; exit 2; }
[ -d "$GOC/data" ] || { echo "[backup] thiếu data dir: $GOC/data" >&2; exit 2; }
mkdir -p "$DICH"
chmod 700 "$GOC/backups" "$DICH"

echo "[backup] $TS — sao lưu SQLite qua API backup của app"
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" exec -T \
  -e VIP_KHO_DANG_CHAY=sqlite hub \
  python3 -c 'import sys; sys.path.insert(0,"/app/app"); import migrate; migrate.sao_luu()' \
  > "$DICH/sao-luu.log"

MOI_NHAT="$(ls -1t "$GOC/data/sao-luu"/hub-*.db 2>/dev/null | head -1 || true)"
[ -n "$MOI_NHAT" ] || { echo "[backup] KHÔNG thấy tệp .db mới" >&2; exit 3; }
cp -p "$MOI_NHAT" "$DICH/hub.db"
chmod 600 "$DICH"/*
# Tạo dấu kiểm THEO TÊN ĐÍCH hub.db (không chép .sha256 của tên gốc — nó ghi tên khác).
( cd "$DICH" && sha256sum hub.db > hub.db.sha256 && sha256sum -c hub.db.sha256 ) \
  >> "$DICH/sao-luu.log" 2>&1 || {
  echo "[backup] dấu kiểm hub.db KHÔNG khớp" >&2; exit 4; }

# Gói khoá: CHỈ khi operator chủ động đặt passphrase trong shell của lượt chạy.
if [ -n "${VIP_HUB_BACKUP_PASSPHRASE:-}" ]; then
  echo "[backup] tạo gói khoá .vipkb (passphrase lấy từ môi trường, không in ra)"
  docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" exec -T \
    -e "VIP_HUB_BACKUP_PASSPHRASE=$VIP_HUB_BACKUP_PASSPHRASE" hub \
    python3 /app/app/sao_luu_khoa.py tao "/du-lieu/sao-luu/khoa-$TS.vipkb" \
    > "$DICH/khoa.log" 2>&1
  cp -p "$GOC/data/sao-luu/khoa-$TS.vipkb" "$DICH/khoa.vipkb"
  chmod 600 "$DICH/khoa.vipkb"
else
  echo "[backup] BỎ QUA gói khoá: chưa đặt VIP_HUB_BACKUP_PASSPHRASE." \
       "DB này KHÔNG tự khôi phục được credential nếu mất thư mục data/khoa." >&2
fi

# Giữ 14 ngày; không đụng ra ngoài $GOC/backups.
find "$GOC/backups" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} + 2>/dev/null || true
echo "[backup] xong: $DICH"
ls -lh "$DICH"
