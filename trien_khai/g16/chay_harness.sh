#!/bin/sh
# Chạy harness nghiệm thu G16-A trên một nền CÔ LẬP, cổng loopback, adapter MOCK.
#
# Vì sao phải cô lập: kịch bản này TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT
# trong CSDL. Chạy nó lên `app/du-lieu/` là làm bẩn dữ liệu đang dùng — và harness TỪ CHỐI
# CHẠY nếu `VIP_HUB_DATA` trỏ vào đó.
#
# KHÔNG mở cổng ra ngoài: máy chủ bind `127.0.0.1`, cổng do hệ điều hành cấp (bind cổng 0).
# Không tunnel, không VPS, không deploy, KHÔNG gọi hãng thật kể cả sandbox.
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
NEN_BASE=${VIP_HUB_DATA:-/tmp/veh_g16_ag04}
NEN="$NEN_BASE/g16_harness"

# Xoá nền CŨ của chính harness này thôi — không đụng thư mục nào khác.
if [ -d "$NEN" ]; then rm -rf "$NEN"; fi
mkdir -p "$NEN"

echo "[g16] dự án   = $GOC"
echo "[g16] nền     = $NEN"
echo "[g16] cổng    = loopback, do hệ điều hành cấp (bind cổng 0)"
echo "[g16] adapter = MOCK · CHO_PHEP_LIVE=False · KHÔNG gọi hãng kể cả sandbox"
echo "[g16] chặng   = G05 (gửi sandbox) và G06-SANDBOX (callback jt_digest) là BLOCKED"
echo

# TỰ KIỂM BỘ DÒ CHỐT trước khi tin lời khai "harness đã từ chối chạy": một bộ dò không phân
# biệt được cấu hình an toàn với cấu hình nguy hiểm thì mọi lời khai ấy vô nghĩa.
python3 "$GOC/trien_khai/g16/chot_an_toan.py" --tu-kiem || exit $?
echo

VIP_HUB_DATA="$NEN" python3 "$GOC/trien_khai/g16/harness_nghiem_thu.py" \
    --json "$NEN/bao-cao-g16.json" "$@"
