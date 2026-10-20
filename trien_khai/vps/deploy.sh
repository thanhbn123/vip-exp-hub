#!/bin/sh
# Cập nhật VIP Express Hub trên VPS từ GitHub, build lại image và restart container.
# Chạy: ./trien_khai/vps/deploy.sh
# Yêu cầu: checkout này là git clone sạch, .env đã có (không commit), data ở
# /home/deploy/vip-express-hub/data.
set -eu
cd "$(dirname "$0")"
echo "[deploy] git pull --ff-only"
git pull --ff-only
TAG="vps-$(git rev-parse --short HEAD)"
export VIP_HUB_IMAGE_TAG="$TAG"
echo "[deploy] image tag $TAG"
docker compose build
docker compose up -d
docker compose ps
echo "[deploy] health"
i=0
while [ "$i" -lt 30 ]; do
  if curl -fsS --max-time 3 http://127.0.0.1:18897/api/v2/suc-khoe >/dev/null 2>&1; then
    echo "[deploy] OK — https://best-uat.viporder.vn/"
    exit 0
  fi
  i=$((i+1)); sleep 2
done
echo "[deploy] health KHÔNG đạt sau 60s — xem docker logs vip-express-hub" >&2
exit 1
