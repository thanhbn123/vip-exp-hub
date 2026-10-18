#!/bin/sh
# DEPLOY VIP EXPRESS HUB LÊN VPS KHÔNG CÓ DOCKER
#
# Chạy TỪ MÁY ANH (không phải trên VPS), hoặc copy sang VPS rồi chạy ở đó.
# Không cần docker. Không cần pip. Ứng dụng là **100% Python stdlib**:
#   `grep` toàn bộ app/ + gateway/ chỉ ra 0 phụ thuộc ngoài — chỉ `http.server`, `sqlite3`,
#   `ssl`, `hashlib`, `urllib`, `xml`… đều là thư viện chuẩn.
#
# CÁCH DÙNG:
#   ./trien_khai/live/deploy_khong_docker.sh <alias-ssh> <ten-mien>
# ví dụ:
#   ./trien_khai/live/deploy_khong_docker.sh veh-uat exp.vipgroup.com.vn
#
# Script này KHÔNG tự chạy nếu thiếu tham số, và KHÔNG đụng vào cấu hình nginx hiện có của
# dự án khác — nó chỉ IN ra các bước cần làm và kiểm tra, để người vận hành tự quyết.

set -eu

ALIAS="${1:-}"
TEN_MIEN="${2:-}"

if [ -z "${ALIAS}" ] || [ -z "${TEN_MIEN}" ]; then
  echo "THIẾU THAM SỐ."
  echo "  Cách dùng: $0 <alias-ssh> <ten-mien>"
  echo "  Alias phải có sẵn trong ~/.ssh/config, hoặc key phải đã ssh-add."
  echo "  Ví dụ: $0 veh-uat exp.vipgroup.com.vn"
  exit 2
fi

THU_MUC_DICH="/opt/veh"
CONG_NOI_BO="${VIP_CONG:-8080}"

echo "=============================================================="
echo " DEPLOY VIP EXPRESS HUB — KHONG DOCKER"
echo "   alias ssh  : ${ALIAS}"
echo "   ten mien   : ${TEN_MIEN}"
echo "   thu muc    : ${THU_MUC_DICH}"
echo "   cong noi bo: ${CONG_NOI_BO}  (app bind 127.0.0.1)"
echo "=============================================================="

# ---- 0. KIỂM TRƯỚC KHI LÀM ----
echo "[0] Kiểm kết nối tới ${ALIAS}…"
if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "${ALIAS}" 'echo OK' 2>/dev/null | grep -q OK; then
  echo "  DỪNG: không SSH được tới '${ALIAS}' ở chế độ không hỏi mật khẩu."
  echo "  Kiểm lại: ~/.ssh/config có Host ${ALIAS}? key đã ssh-add? đã thêm public key vào authorized_keys trên VPS?"
  exit 3
fi
echo "  OK: SSH được."

echo "[0b] Kiểm VPS có python3…"
ssh -o BatchMode=yes "${ALIAS}" 'command -v python3 >/dev/null && python3 -V' || {
  echo "  DỪNG: VPS không có python3."; exit 4; }
echo "  OK: có python3."

echo "[0c] Kiểm VPS có web server làm TLS (nginx | caddy)…"
CO_PROXY=$(ssh -o BatchMode=yes "${ALIAS}" 'command -v nginx || command -v caddy || echo KHONG')
if [ "${CO_PROXY}" = "KHONG" ]; then
  echo "  CẢNH BÁO: VPS KHÔNG có nginx lẫn caddy."
  echo "  => KHÔNG thể phục vụ HTTPS cho ${TEN_MIEN}."
  echo "     J&T gọi webhook bằng HTTPS. Phải cài nginx hoặc caddy TRƯỚC."
  echo "     Script DỪNG ở đây thay vì dựng một webhook không ai gọi tới được."
  exit 5
fi
echo "  OK: ${CO_PROXY}"

# ---- 1. ĐƯA MÃ NGUỒN LÊN ----
echo "[1] Đồng bộ mã nguồn lên ${THU_MUC_DICH} (KHÔNG xoá dữ liệu)…"
ssh -o BatchMode=yes "${ALIAS}" "mkdir -p '${THU_MUC_DICH}/app' '${THU_MUC_DICH}/gateway' '${THU_MUC_DICH}/admin' '${THU_MUC_DICH}/pages' '${THU_MUC_DICH}/mock'"
rsync -az --delete \
  --exclude '.git' --exclude '__pycache__' --exclude 'node_modules' \
  --exclude 'app/du-lieu' --exclude '_bao-cao' --exclude '_ket-qua' \
  app/        "${ALIAS}:${THU_MUC_DICH}/app/"
rsync -az gateway/ "${ALIAS}:${THU_MUC_DICH}/gateway/"  2>/dev/null || true
rsync -az admin/   "${ALIAS}:${THU_MUC_DICH}/admin/"    2>/dev/null || true
rsync -az pages/   "${ALIAS}:${THU_MUC_DICH}/pages/"    2>/dev/null || true
rsync -az mock/    "${ALIAS}:${THU_MUC_DICH}/mock/"     2>/dev/null || true
echo "  OK."

# ---- 2. DỮ LIỆU RIÊNG, KHÔNG BAO GIỜ LÀ DỮ LIỆU THẬT ----
echo "[2] Tạo thư mục dữ liệu RIÊNG trên VPS…"
ssh -o BatchMode=yes "${ALIAS}" "mkdir -p '${THU_MUC_DICH}/du-lieu' && chmod 700 '${THU_MUC_DICH}/du-lieu'"
echo "  OK: ${THU_MUC_DICH}/du-lieu (chỉ chủ sở hữu đọc được)."

# ---- 3. SYSTEMD UNIT ----
echo "[3] Cài systemd unit (chạy app, bind 127.0.0.1:${CONG_NOI_BO})…"
ssh -o BatchMode=yes "${ALIAS}" "cat > /tmp/veh.service <<'UNIT'
[Unit]
Description=VIP Express Hub (local/UAT)
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=${THU_MUC_DICH}
Environment=VIP_HUB_DATA=${THU_MUC_DICH}/du-lieu
Environment=VIP_HUB_BIND=127.0.0.1
Environment=VIP_CONG=${CONG_NOI_BO}
ExecStart=/usr/bin/python3 ${THU_MUC_DICH}/app/server.py
Restart=on-failure
RestartSec=3
# Không cho ghi ra ngoài thư mục dự án
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
UNIT
sudo mv /tmp/veh.service /etc/systemd/system/veh.service
sudo systemctl daemon-reload
sudo systemctl enable --now veh
sleep 2
systemctl is-active veh"
echo "  (nếu bước này cần sudo mà user không có quyền, script sẽ báo lỗi — đó là thông tin, không phải lỗi script)"

# ---- 4. KIỂM APP ĐÃ NGHE ----
echo "[4] Kiểm app nghe trên 127.0.0.1:${CONG_NOI_BO}…"
ssh -o BatchMode=yes "${ALIAS}" "curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:${CONG_NOI_BO}/ " || true
echo

# ---- 5. TLS + REVERSE PROXY (KHÔNG ĐỤNG CẤU HÌNH CŨ) ----
echo "[5] TLS + reverse proxy cho ${TEN_MIEN}"
cat <<'HD'
  Script CỐ Ý KHÔNG tự sửa cấu hình nginx/caddy hiện có.
  Nếu VPS đang chạy dự án KHÁC, sửa nhầm một dòng là sập dự án đó.

  Làm TAY, đúng một trong hai:

  --- CADDY (dễ nhất, tự xin cert) ---
  Thêm vào /etc/caddy/Caddyfile:
      TEN_MIEN {
          reverse_proxy 127.0.0.1:CONG_NOI_BO
      }
  rồi:  sudo systemctl reload caddy

  --- NGINX + certbot ---
  /etc/nginx/sites-available/veh:
      server {
          listen 80;
          server_name TEN_MIEN;
          location / { proxy_pass http://127.0.0.1:CONG_NOI_BO; proxy_set_header Host ${host};
                       proxy_set_header X-Forwarded-For ${proxy_add_x_forwarded_for}; }
      }
  rồi:  sudo ln -s /etc/nginx/sites-available/veh /etc/nginx/sites-enabled/
        sudo nginx -t && sudo systemctl reload nginx
        sudo certbot --nginx -d TEN_MIEN

HD

echo "=============================================================="
echo " XONG PHẦN TỰ ĐỘNG. CÒN LẠI LÀM TAY:"
echo "   1. Dựng TLS + reverse proxy (mục 5 ở trên)"
echo "   2. Kiểm: curl -sI https://${TEN_MIEN}/  => phải là 200/3xx, KHÔNG phải 000"
echo "   3. Nạp credentials J&T qua API của app (KHÔNG để trong file .env)"
echo "   4. Gọi SANDBOX trước, chứng minh digest đúng, RỒI MỚI production"
echo "=============================================================="
