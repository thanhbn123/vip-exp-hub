#!/bin/sh
# Chạy toàn bộ bộ thử frontend tự động (hai tầng chạy được bằng máy).
# Dùng: sh thu_frontend/chay.sh
#
# Tầng 3 (trình duyệt thật) KHÔNG nằm trong script này và KHÔNG tự chạy được — xem
# docs/FRONTEND_AUTOMATION.md mục "Tầng 3". Script báo ĐẠT chỉ có nghĩa hai tầng đầu đạt.
set -e
GOC=$(cd "$(dirname "$0")/.." && pwd)
cd "$GOC"

echo "=== TẦNG 1 — logic thuần (Node, không trình duyệt) ==="
node --test thu_frontend/thu_logic.mjs

echo
echo "=== TẦNG 2 — HTTP + tệp tĩnh (Python, server thật, không trình duyệt) ==="
python3 thu_frontend/thu_http.py

echo
echo "HAI TẦNG TỰ ĐỘNG ĐẠT."
echo "CHƯA chạy: tầng 3 (trình duyệt thật) — DOM, CSS, bố cục, tràn ngang."
echo "Xem docs/FRONTEND_AUTOMATION.md để biết tầng 3 phủ gì và chạy bằng tay thế nào."
