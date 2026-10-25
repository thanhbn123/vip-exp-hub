#!/bin/sh
# Kiểm tra SAU triển khai — không gửi credential, không tạo đơn.
#
# Bản AG-06 vá hai lỗi của bản cũ:
#   · "cổng app chỉ loopback" chỉ IN ra `ss` rồi luôn thoát 0: app bind 0.0.0.0:18897 vẫn
#     "qua" cổng kiểm. Bây giờ kiểm ĐỊA CHỈ và fail nếu có gì ngoài loopback / không thấy cổng.
#   · không kiểm health của container, nên `restarting`/`unhealthy` vẫn có thể đi tiếp.
set -eu
DOMAIN="${VIP_HUB_DOMAIN:-best-uat.viporder.vn}"
LOCAL="http://127.0.0.1:18897"
GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
# Thư mục compose là THƯ MỤC CHỨA CHÍNH TỆP NÀY, không phải một đường cố định. Bản cũ ghim
# `$GOC/src/trien_khai/vps`; khi checkout trên VPS đổi từ `src/` sang `app/` (clone từ GitHub,
# 2026-10-20) thì đường đó không còn tồn tại và script chết ngay dòng kiểm compose. Đó là cách
# cron sao lưu đứng im nhiều ngày mà không ai thấy. Tự định vị thì không còn chỗ để lệch.
COMPOSE_DIR="${VIP_HUB_COMPOSE_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
TEN="${VIP_HUB_CONTAINER:-vip-express-hub}"
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

if ! docker inspect "$TEN" >/dev/null 2>&1; then
  echo "  ✗ không thấy container $TEN"; loi=1
else
  i=0; tt=""
  while [ "$i" -lt 30 ]; do
    tt="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$TEN" 2>/dev/null || echo missing)"
    [ "$tt" = "healthy" ] && break
    i=$((i+1)); sleep 2
  done
  if [ "$tt" = "healthy" ]; then
    echo "  ✓ health container — healthy"
  else
    echo "  ✗ health container — $tt (chờ tối đa 60s)"; loi=1
  fi

  nguon="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/du-lieu"}}{{.Source}}{{end}}{{end}}' "$TEN" 2>/dev/null || true)"
  if [ "$nguon" = "$GOC/data" ]; then
    echo "  ✓ bind mount /du-lieu — $nguon"
  else
    echo "  ✗ bind mount /du-lieu — '$nguon' (mong '$GOC/data')"; loi=1
  fi
fi

echo "== quyền thư mục dữ liệu =="
if [ -d "$GOC/data" ]; then
  chu="$(stat -c '%u:%g' "$GOC/data")"
  mode="$(stat -c '%a' "$GOC/data")"
  echo "  data: chủ $chu mode $mode"
  [ "$mode" = "700" ] || { echo "  ✗ data phải mode 700"; loi=1; }
else
  echo "  ✗ thiếu $GOC/data"; loi=1
fi

echo "== local =="
check "health" 200 "$LOCAL/api/v2/suc-khoe"
check "ready" 200 "$LOCAL/api/v2/san-sang"
check "trang UAT" 200 "$LOCAL/pages/best-uat.html"
check "hợp đồng BEST cần đăng nhập" 401 "$LOCAL/api/v2/best/hop-dong"
# Thứ tự tham số của `check` là `tên kỳ_vọng URL [curl opts]`. Bản cũ viết `-X POST` TRƯỚC URL,
# nên `url` bị gán thành `-X` và `curl` nhận `POST` như một URL: cổng kiểm này luôn đỏ dù dịch
# vụ đúng. Giữ URL ở vị trí thứ ba.
check "webhook mã lạ bị chặn (404 fail-closed)" 404 "$LOCAL/api/v2/webhook/nhan/khong-co" \
  -X POST -H 'Content-Type: application/json' -d '{}'
# GET trên cửa webhook phải là 405 + Allow: POST, KHÔNG phải 401 "chưa đăng nhập": hãng thử URL
# bằng GET trước khi bật cấu hình, và 401 nói sai rằng endpoint cần phiên.
check "webhook GET trả 405 (không phải 401)" 405 "$LOCAL/api/v2/webhook/nhan/khong-co"

echo "== cổng app chỉ loopback =="
if ! command -v ss >/dev/null 2>&1; then
  echo "  ✗ thiếu ss — không kiểm được cổng"; loi=1
else
  dong="$(ss -lntH 2>/dev/null | awk '{print $4}' | grep ':18897$' || true)"
  if [ -z "$dong" ]; then
    echo "  ✗ không thấy cổng 18897 đang LISTEN"; loi=1
  elif printf '%s\n' "$dong" | grep -qvE '^(127\.0\.0\.1|\[::1\]):18897$'; then
    echo "  ✗ cổng 18897 KHÔNG chỉ loopback:"; printf '%s\n' "$dong" | sed 's/^/    /'; loi=1
  else
    echo "  ✓ 18897 chỉ loopback: $(printf '%s' "$dong" | paste -sd, -)"
  fi
fi

echo "== HTTPS công khai (resolve local) =="
check "health HTTPS" 200 "https://$DOMAIN/api/v2/suc-khoe" --resolve "$DOMAIN:443:127.0.0.1"
check "trang UAT HTTPS" 200 "https://$DOMAIN/pages/best-uat.html" --resolve "$DOMAIN:443:127.0.0.1"

echo "== HSTS =="
# Dùng GET, KHÔNG `curl -I`: app stdlib không hỗ trợ HEAD và trả 501 (đo 2026-10-19). Bản cũ
# dùng HEAD nên cổng kiểm HSTS luôn đỏ dù header có mặt trên GET.
curl -sS -o /dev/null -D - --max-time 12 --resolve "$DOMAIN:443:127.0.0.1" \
  "https://$DOMAIN/" 2>/dev/null \
  | grep -i '^strict-transport-security:' || { echo "  ✗ thiếu HSTS"; loi=1; }

echo "== TLS =="
if command -v openssl >/dev/null 2>&1; then
  echo | openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates 2>/dev/null || { echo "  ✗ không đọc được cert"; loi=1; }
else
  echo "  ✗ thiếu openssl"; loi=1
fi

exit "$loi"
