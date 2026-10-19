#!/usr/bin/env bash
# Bàn nghiệm thu BEST Express — HTTPS cục bộ, chỉ sandbox, production ghi bị khoá trong mã.
#
# Vì sao phải có script này:
#   · credential thật KHÔNG được đi qua HTTP bản rõ;
#   · cổng Owner phải được bật TƯỜNG MINH, không có mặc định;
#   · BEST phải gọi được webhook từ Internet — script in URL công khai nếu bạn khai
#     VIP_HUB_PUBLIC_BASE_URL (ví dụ một tunnel HTTPS), và nói thẳng nếu chưa khai.
#
# CÁCH DÙNG:
#   VIP_BEST_OWNER_APPROVAL_ID='OWNER-UAT-2026-10-19' ./trien_khai/best_nghiem_thu.sh
# hoặc:
#   ./trien_khai/best_nghiem_thu.sh 'OWNER-UAT-2026-10-19'
#
# KHÔNG đặt VIP_HUB_DATA vào trong cây repo nếu chứa credential thật. Mặc định dùng /tmp.
set -euo pipefail

GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MA_PHE_DUYET="${1:-${VIP_BEST_OWNER_APPROVAL_ID:-}}"
if [ -z "$MA_PHE_DUYET" ]; then
  echo "[best-uat] TỪ CHỐI: cần mã phê duyệt của Owner (tham số 1 hoặc VIP_BEST_OWNER_APPROVAL_ID)." >&2
  echo "[best-uat] Đây là mã AUDIT, không phải mật khẩu. Ví dụ: OWNER-UAT-2026-10-19" >&2
  exit 2
fi

export VIP_HUB_DATA="${VIP_HUB_DATA:-/tmp/vip-best-uat-data}"
export VIP_HUB_PORT="${VIP_HUB_PORT:-8897}"
export VIP_HUB_BIND="${VIP_HUB_BIND:-127.0.0.1}"
export VIP_BEST_OWNER_APPROVED=1
export VIP_BEST_OWNER_APPROVAL_ID="$MA_PHE_DUYET"
export VIP_HUB_HTTPS=1

THU_MUC_TLS="${VIP_HUB_TLS_DIR:-/tmp/vip-best-uat-tls}"
mkdir -p "$VIP_HUB_DATA" "$THU_MUC_TLS"
chmod 700 "$VIP_HUB_DATA" "$THU_MUC_TLS" 2>/dev/null || true

CERT="$THU_MUC_TLS/best-uat.crt"
KEY="$THU_MUC_TLS/best-uat.key"
if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
  echo "[best-uat] Tạo chứng chỉ tự ký cho localhost/127.0.0.1 (chỉ dùng cho máy này)…"
  openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 2 \
    -keyout "$KEY" -out "$CERT" \
    -subj "/CN=localhost/O=VIP Express Hub local UAT" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
  chmod 600 "$KEY" "$CERT"
fi
export VIP_HUB_TLS_CERT="$CERT"
export VIP_HUB_TLS_KEY="$KEY"

# Dữ liệu demo + tài khoản đăng nhập hub. KHÔNG in mật khẩu ra terminal.
if [ ! -s "$VIP_HUB_DATA/hub.db" ]; then
  echo "[best-uat] Khởi tạo CSDL demo tại $VIP_HUB_DATA …"
  (cd "$GOC" && python3 app/khoi_tao.py >/dev/null)
fi
# CSDL mới tạo ở schema v0; server TỪ CHỐI nếu chưa migrate. Chạy migration ngay trong script
# để người nghiệm thu không phải tự đoán bước tiếp theo. Khai kho SQLite là bắt buộc.
echo "[best-uat] Kiểm tra/migrate schema CSDL…"
(cd "$GOC" && VIP_KHO_DANG_CHAY=sqlite python3 app/migrate.py >/dev/null)

echo "[best-uat] Mã phê duyệt phiên: $MA_PHE_DUYET"
echo "[best-uat] Chỉ môi trường SANDBOX được dùng; tạo/sửa/hủy đơn production bị khoá trong mã."
echo "[best-uat] Mở https://localhost:${VIP_HUB_PORT}/admin/ (chứng chỉ tự ký — chọn 'tiếp tục')."
echo "[best-uat] Tài khoản hub demo: xem $VIP_HUB_DATA/TAI-KHOAN-DEMO.md"
if [ -n "${VIP_HUB_PUBLIC_BASE_URL:-}" ]; then
  echo "[best-uat] Webhook công khai: ${VIP_HUB_PUBLIC_BASE_URL%/}/api/v2/webhook/nhan/<webhook_ma>"
else
  echo "[best-uat] CHƯA khai VIP_HUB_PUBLIC_BASE_URL — URL webhook chỉ là đường dẫn nội bộ;"
  echo "           BEST KHÔNG gọi được 127.0.0.1. Cần tunnel/reverse proxy HTTPS công khai để nghiệm thu webhook thật."
fi
echo "[best-uat] Bàn nghiệm thu: https://localhost:${VIP_HUB_PORT}/pages/best-uat.html"

cd "$GOC"
exec python3 app/server.py
