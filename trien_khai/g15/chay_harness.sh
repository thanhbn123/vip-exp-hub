#!/bin/sh
# Chạy harness E2E G15 trên một nền CÔ LẬP, cổng loopback, adapter MOCK.
#
# Vì sao phải cô lập: kịch bản này TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT
# trong CSDL. Chạy nó lên `app/du-lieu/` là làm bẩn dữ liệu đang dùng. Nền ở đây là thư mục
# tạm riêng dưới `VIP_HUB_DATA`, xoá sạch khi xong.
#
# KHÔNG mở cổng ra ngoài: máy chủ bind `127.0.0.1` (mặc định của `server.py`), cổng lấy ngẫu
# nhiên trong 18000–19999. Không tunnel, không VPS, không deploy.
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
NEN_BASE=${VIP_HUB_DATA:-/tmp/veh_data_ag04}
NEN="$NEN_BASE/g15_harness"

# Xoá nền CŨ của chính harness này thôi — không đụng thư mục nào khác.
if [ -d "$NEN" ]; then rm -rf "$NEN"; fi
mkdir -p "$NEN"

echo "[g15] dự án   = $GOC"
echo "[g15] nền     = $NEN"
echo "[g15] cổng    = loopback, ngẫu nhiên 18000–19999"
echo "[g15] adapter = MOCK · CHO_PHEP_LIVE=False · KHÔNG gọi hãng thật"

VIP_HUB_DATA="$NEN" exec python3 "$GOC/trien_khai/g15/harness_e2e.py" \
    --json "$NEN/bao-cao-g15.json" "$@"
