#!/bin/sh
# Chuẩn bị thư mục persistent TRƯỚC `docker compose up` — không khởi động gì.
#
# Vì sao cần: compose dùng bind mount với `create_host_path: false` (fail-closed). Nếu thư mục
# chưa có, `up` phải báo lỗi rõ thay vì để Docker tự tạo bằng root rồi app UID 1000 chết vì
# không ghi được. Script này tạo data/ + backups/ bằng chính user deploy, mode 700.
set -eu

GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
COMPOSE_DIR="$GOC/src/trien_khai/vps"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
ENV_FILE="$COMPOSE_DIR/.env"

[ -f "$COMPOSE" ] || { echo "[chuan_bi] thiếu compose: $COMPOSE" >&2; exit 2; }
[ -f "$ENV_FILE" ] || {
  echo "[chuan_bi] thiếu $ENV_FILE — copy .env.production.example rồi chmod 600" >&2
  exit 2
}

uid="$(id -u)"
gid="$(id -g)"

# Nếu .env khai UID/GID khác user đang chạy thì compose sẽ chạy container bằng UID khác chủ
# sở hữu data — kiểm trước, đừng để lỗi quyền lộ ra lúc app khởi động.
uid_cfg="$(sed -n 's/^VIP_HUB_UID=//p' "$ENV_FILE" | tail -1)"
gid_cfg="$(sed -n 's/^VIP_HUB_GID=//p' "$ENV_FILE" | tail -1)"
[ -z "$uid_cfg" ] || [ "$uid_cfg" = "$uid" ] || {
  echo "[chuan_bi] VIP_HUB_UID=$uid_cfg nhưng user hiện tại UID=$uid — sửa .env hoặc chown data" >&2
  exit 3
}
[ -z "$gid_cfg" ] || [ "$gid_cfg" = "$gid" ] || {
  echo "[chuan_bi] VIP_HUB_GID=$gid_cfg nhưng user hiện tại GID=$gid — sửa .env" >&2
  exit 3
}

for d in data backups; do
  duong="$GOC/$d"
  [ ! -L "$duong" ] || { echo "[chuan_bi] $duong là symlink — từ chối" >&2; exit 3; }
  if [ ! -d "$duong" ]; then
    mkdir -p "$duong"
  fi
  chmod 700 "$duong"
  chu="$(stat -c '%u:%g' "$duong")"
  if [ "$chu" != "$uid:$gid" ]; then
    echo "[chuan_bi] $duong thuộc $chu, cần $uid:$gid. Không có sudo: nhờ Owner chown," >&2
    echo "           hoặc xoá thư mục rỗng rồi chạy lại script (CHỈ khi chắc chắn rỗng)." >&2
    exit 3
  fi
done

mode_env="$(stat -c '%a' "$ENV_FILE")"
[ "$mode_env" = "600" ] || echo "[chuan_bi] CẢNH BÁO: $ENV_FILE mode $mode_env, nên là 600" >&2
[ -s "$GOC/data/hub.db" ] && echo "[chuan_bi] LƯU Ý: đã có data/hub.db — không xoá gì."

echo "[chuan_bi] OK: $GOC/data và $GOC/backups mode 700, chủ $uid:$gid"
echo "[chuan_bi] Bước tiếp: docker compose config && docker compose build (chưa up)."
