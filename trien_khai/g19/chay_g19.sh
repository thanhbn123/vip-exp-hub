#!/bin/sh
# Chạy trọn bộ G19 / AG-04 (phủ 31 route còn thiếu) trên nền CÔ LẬP, loopback, CỔNG 0.
#
# BA TẦNG, chạy độc lập được:
#   1. Bộ trích route thứ ba (nguyên lý: THI HÀNH) — in ra hằng số / ứng viên / route / cặp.
#   2. Bộ hồi quy `app/thu/thu_g19_route.py` — 49 ca: tự kiểm bộ trích (A), đột biến (B),
#      đo cách ly tenant 31 mục (C), con số cuối (D).
#   3. (tuỳ chọn) `--chi-liet-ke` chỉ chạy tầng 1.
#
# KHÔNG gọi hãng kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP): máy chủ đo bind `127.0.0.1`
# CỔNG 0 do hệ điều hành cấp, và `may_chu_do.py` ghi lại MỌI lượt `socket.connect()` rồi khẳng
# định 0 lượt ra ngoài loopback. Không tunnel, không deploy, không mở cổng, không `.env`.
#
# MỖI phép đo tự tạo `VIP_HUB_DATA` TẠM RIÊNG (do `bot_route_thi_hanh.chay_may_chu` cấp), nên
# script này KHÔNG đụng vào `app/du-lieu/` của dự án — và cũng không cần dọn gì.
#
# IN EXIT CODE TRƯỚC MỌI PIPE: mất mã thoát là mất bằng chứng.
set -u
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 2

echo "=== [1/2] BỘ TRÍCH ROUTE THỨ BA (nguyên lý: THI HÀNH) ==="
python3 trien_khai/g19/bot_route_thi_hanh.py --ra /tmp/g19_liet_ke.json
echo "EXIT_LIET_KE=$?"
if [ "${1:-}" = "--chi-liet-ke" ]; then
    exit 0
fi

echo
echo "=== [2/2] BỘ HỒI QUY G19 (49 ca) ==="
python3 app/thu/thu_g19_route.py > /tmp/g19_thu.log 2>&1
MA=$?
echo "EXIT_THU=$MA"
tail -n 40 /tmp/g19_thu.log
echo "(nhật ký đầy đủ: /tmp/g19_thu.log · kết quả thô: /tmp/g19_liet_ke.json)"
exit "$MA"
