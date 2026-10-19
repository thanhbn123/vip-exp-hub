#!/bin/sh
# KHẢO SÁT READ-ONLY VPS 160.22.170.20 — không đổi gì. Chạy từ máy có SSH:
#   ssh viporder-staging 'bash -s' < trien_khai/vps/khao_sat.sh
set +e
echo "===== HOST ====="
hostname -f; uptime; date -Is
echo "===== CPU/RAM/DISK ====="
nproc; free -h; df -hT /; df -i /
echo "===== USER/SUDO ====="
id; sudo -n true 2>&1; echo "sudo_rc=$?"
echo "===== DOCKER ====="
docker version 2>&1 | sed -n '1,16p'; docker compose version 2>&1
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1
docker compose ls 2>&1
echo "===== PORTS ====="
ss -lnt 2>&1 | sed -n '1,80p'
echo "===== CADDY ====="
docker inspect -f 'net={{.HostConfig.NetworkMode}} ports={{json .HostConfig.PortBindings}}' vip-staging-caddy 2>&1
docker exec vip-staging-caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -3
echo "===== DNS ỨNG VIÊN ====="
for d in viporder.vn viporder.com.vn cpn.viporder.vn qua.viporder.vn best-uat.viporder.vn; do
  printf '%-28s ' "$d"; getent hosts "$d" 2>&1 | awk '{print $1}' | paste -sd, -
done
echo "===== BEST TLS (không credential) ====="
if [ "${KHAO_SAT_BEST:-0}" = "1" ]; then
  for h in sgp-seaedi-test.800best.com sgp-seaedi.800best.com sea-edi-hxtest.800best.com; do
    printf '%-32s ' "$h"; curl -sS -o /dev/null -w 'HTTP %{http_code} TLS %{ssl_verify_result}\n' --max-time 10 "https://$h/" 2>&1
  done
else
  echo "BỎ QUA: KHAO_SAT_BEST!=1 — không gọi host BEST (kể cả TLS ẩn danh) theo ràng buộc lượt này."
fi
echo "===== KẾT THÚC ====="
