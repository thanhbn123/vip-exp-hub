#!/bin/sh
# Kiểm tra SAU triển khai — không gửi credential, không tạo đơn.
set -eu
DOMAIN="${VIP_HUB_DOMAIN:-best-uat.viporder.vn}"
LOCAL="http://127.0.0.1:18897"
GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
COMPOSE_DIR="$GOC/src/trien_khai/vps"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
loi=0

check() { # tên, kỳ vọng, URL, curl opts
  ten="$1"; mong="$2"; url="$3"; shift 3
  ma="$(curl -sS -o /tmp/vip-express-check.$$ -w '%{http_code}' --max-time 12 "$@" "$url" 2>/dev/null || true)"
  if [ "$ma" = "$mong" ]; then echo "  ✓ $ten — HTTP $ma"; else
    echo "  ✗ $ten — HTTP $ma (mong $mong)"; loi=1; fi
  rm -f /tmp/vip-express-check.$$
}

echo "== container =="
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" ps
echo "== local =="
check "health" 200 "$LOCAL/api/v2/suc-khoe"
check "ready" 200 "$LOCAL/api/v2/san-sang"
check "trang UAT" 200 "$LOCAL/pages/best-uat.html"
check "hợp đồng BEST cần đăng nhập" 401 "$LOCAL/api/v2/best/hop-dong"
check "webhook thiếu Bearer bị chặn" 401 -X POST "$LOCAL/api/v2/webhook/nhan/khong-co" \
  -H 'Content-Type: application/json' -d '{}'
echo "== cổng app chỉ loopback =="
ss -lnt 2>/dev/null | grep ':18897' || true
echo "== HTTPS công khai (resolve local) =="
check "health HTTPS" 200 "https://$DOMAIN/api/v2/suc-khoe" --resolve "$DOMAIN:443:127.0.0.1"
check "trang UAT HTTPS" 200 "https://$DOMAIN/pages/best-uat.html" --resolve "$DOMAIN:443:127.0.0.1"
echo "== HSTS =="
curl -sSI --max-time 12 --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN/" 2>/dev/null \
  | grep -i '^strict-transport-security:' || { echo "  ✗ thiếu HSTS"; loi=1; }
echo "== TLS =="
echo | openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates 2>/dev/null || { echo "  ✗ không đọc được cert"; loi=1; }
exit "$loi"
