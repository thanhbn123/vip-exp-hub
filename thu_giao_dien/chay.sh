#!/bin/sh
# TẦNG 3 — kiểm giao diện trong TRÌNH DUYỆT THẬT (Chromium qua Playwright).
#
# Theo đúng khuôn `app/thu/chay_e2e.sh`: nền cô lập, cổng rỗi lấy ngẫu nhiên và THỬ TRƯỚC,
# chờ máy chủ mở THẬT, tắt theo ĐÚNG PID đã giữ, dọn bằng trap kể cả khi hỏng giữa đường.
#
# PHẠM VI — đọc trước khi tin kết quả (§12.1 luật 3 và luật 5):
#   - CHỈ Chromium (bản đi kèm Playwright, cài trong `node_modules/` của repo).
#   - CHỈ ba bề rộng 375 / 768 / 1280, không thiết bị cảm ứng thật, không trình đọc màn hình,
#     không in ra giấy/PDF thật, không Safari, không Firefox.
#   - Tràn ngang đo bằng `scrollWidth` vs `clientWidth`, KHÔNG đo bằng cảm nhận và KHÔNG đo
#     bằng ảnh chụp. Ảnh chụp chỉ để người xem, không bao giờ là điều kiện đạt.
set -e
GOC=$(cd "$(dirname "$0")/.." && pwd)
NEN=$(mktemp -d "${TMPDIR:-/tmp}/veh-giao-dien.XXXXXX")
PID=""
don_dep() {
    if [ -n "$PID" ]; then
        # Tắt theo ĐÚNG PID giữ lúc khởi động. KHÔNG BAO GIỜ theo mẫu tên (§16.7):
        # một lượt `pkill -f cat` đã từng giết cả Ollama và Synology Drive vì chữ "cat"
        # nằm trong "Application".
        kill "$PID" 2>/dev/null || true
        sleep 1
    fi
    rm -rf "$NEN"
}
trap don_dep EXIT INT TERM

if [ ! -d "$GOC/node_modules/@playwright/test" ]; then
    echo "CHƯA CÀI Playwright. Chạy trong thư mục repo:  npm install"
    echo "rồi:  PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium"
    exit 2
fi

CONG=""
i=0
while [ $i -lt 40 ]; do
    thu=$(awk 'BEGIN{srand();print 18000+int(rand()*2000)}')
    if ! nc -z 127.0.0.1 "$thu" 2>/dev/null; then CONG=$thu; break; fi
    i=$((i+1))
done
[ -z "$CONG" ] && { echo "KHÔNG tìm được cổng rỗi sau 40 lượt thử"; exit 2; }

export VIP_HUB_DATA="$NEN"
cd "$GOC"
python3 app/migrate.py   > "$NEN/migrate.log" 2>&1
python3 app/khoi_tao.py  > "$NEN/seed.log"    2>&1
python3 thu_giao_dien/chuan_bi.py mk

python3 app/server.py "$CONG" > "$NEN/server.log" 2>&1 &
PID=$!
# Chờ máy chủ MỞ THẬT. Không `sleep` một con số rồi tin là đã mở.
j=0
while [ $j -lt 50 ]; do
    nc -z 127.0.0.1 "$CONG" 2>/dev/null && break
    kill -0 "$PID" 2>/dev/null || { echo "MÁY CHỦ CHẾT khi khởi động:"; cat "$NEN/server.log"; exit 2; }
    sleep 0.2; j=$((j+1))
done
[ $j -ge 50 ] && { echo "máy chủ không mở cổng $CONG sau 10 giây"; cat "$NEN/server.log"; exit 2; }

GOC_URL="http://127.0.0.1:$CONG"
python3 thu_giao_dien/chuan_bi.py don "$GOC_URL"

echo "[giao-dien] nền=$NEN cổng=$CONG pid=$PID"
VIP_GD_GOC="$GOC_URL" VIP_GD_NEN="$NEN" PLAYWRIGHT_BROWSERS_PATH=0 \
    npx playwright test "$@"
MA=$?
echo "[giao-dien] mã thoát $MA"
echo "[giao-dien] PHẠM VI: chỉ Chromium · chỉ 375/768/1280 · không cảm ứng thật · không trình đọc màn hình · không in thật."
exit $MA
