#!/bin/sh
# Validate Caddyfile LIVE + CANDIDATE (live + khối best-uat) — KHÔNG ÁP DỤNG, KHÔNG reload.
#
# Vì sao cần script này: `/etc/caddy/Caddyfile` trong container là bind mount READ-ONLY từ
# /srv/vip-staging-proxy/Caddyfile. Cách cũ trong README (`docker exec ... cat >> /etc/caddy/...`)
# sẽ hỏng với "Read-only file system"; tệ hơn, nếu validate SAU khi ghi thì một khối sai đã nằm
# trong file live. Script này dựng candidate trong /tmp của container, validate TRƯỚC, rồi mới
# in hướng dẫn cho Owner ghi file host (in-place) — không đụng file live.
set -eu

CADDY="${VIP_HUB_CADDY_CONTAINER:-vip-staging-caddy}"
HERE="$(cd "$(dirname "$0")" && pwd)"
SNIPPET="${1:-$HERE/Caddyfile.best-uat}"
TMP_C="/tmp/vip-express-hub-candidate-$$.Caddyfile"
WORK=""

[ -f "$SNIPPET" ] || { echo "[kiem_caddy] thiếu snippet: $SNIPPET" >&2; exit 2; }
command -v docker >/dev/null || { echo "[kiem_caddy] thiếu docker" >&2; exit 2; }
docker inspect "$CADDY" >/dev/null 2>&1 || { echo "[kiem_caddy] không thấy container $CADDY" >&2; exit 2; }
[ "$(docker inspect -f '{{.State.Running}}' "$CADDY")" = "true" ] || {
  echo "[kiem_caddy] $CADDY không chạy — không validate trên container sống" >&2; exit 2; }

cleanup() {
  if [ -n "$WORK" ]; then rm -rf "$WORK"; fi
  docker exec "$CADDY" rm -f "$TMP_C" >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

WORK="$(mktemp -d "${TMPDIR:-/tmp}/vip-caddy-kiem.XXXXXX")"
hash_truoc="$(docker exec "$CADDY" cat /etc/caddy/Caddyfile | sha256sum | awk '{print $1}')"

echo "[kiem_caddy] validate LIVE (chỉ đọc)…"
docker exec "$CADDY" caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

docker exec "$CADDY" cat /etc/caddy/Caddyfile > "$WORK/live.Caddyfile"
{
  cat "$WORK/live.Caddyfile"
  printf '\n\n'
  cat "$SNIPPET"
} > "$WORK/candidate.Caddyfile"

echo "[kiem_caddy] validate CANDIDATE (live + $(basename "$SNIPPET"))…"
docker cp "$WORK/candidate.Caddyfile" "$CADDY:$TMP_C" >/dev/null
docker exec "$CADDY" caddy validate --config "$TMP_C" --adapter caddyfile

hash_sau="$(docker exec "$CADDY" cat /etc/caddy/Caddyfile | sha256sum | awk '{print $1}')"
[ "$hash_truoc" = "$hash_sau" ] || {
  echo "[kiem_caddy] TỪ CHỐI: Caddyfile live ĐỔI trong lúc validate — có người khác đang sửa" >&2
  exit 4; }

echo "[kiem_caddy] OK: live + candidate hợp lệ; live KHÔNG đổi (sha256 $hash_sau)."
echo "[kiem_caddy] KHÔNG áp dụng. Ghi file host là việc của Owner/root: xem Caddyfile.best-uat."
