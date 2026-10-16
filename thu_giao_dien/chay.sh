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
        # Chờ tới khi nó CHẾT THẬT rồi mới thôi. `sleep 1` rồi tin là đã chết chính là cách
        # một máy chủ mồ côi sống sót qua lượt chạy: tiền lệ pid 41082 nghe cổng 19449 — đúng
        # dải cổng mà vòng chọn cổng dưới đây dùng — được AG-04 phát hiện ở một lượt sau.
        k=0
        while [ $k -lt 25 ]; do
            kill -0 "$PID" 2>/dev/null || break
            sleep 0.2; k=$((k+1))
        done
        # Vẫn sống sau 5 giây: XÁC MINH DANH TÍNH TRƯỚC KHI dùng tín hiệu mạnh, vì PID có thể
        # đã được cấp lại cho một tiến trình KHÁC. Chỉ `kill -9` khi tên vẫn là Python; không
        # xác minh được thì KHÔNG đóng — báo ra để người đọc kiểm tay.
        if kill -0 "$PID" 2>/dev/null; then
            TEN=$(ps -o comm= -p "$PID" 2>/dev/null || true)
            case "$TEN" in
                *[Pp]ython*) kill -9 "$PID" 2>/dev/null || true ;;
                *) echo "[giao-dien] CẢNH BÁO: pid $PID còn sống nhưng tên tiến trình là '$TEN' — KHÔNG kill -9 (đề phòng PID được cấp lại). Kiểm tay: kill -0 $PID" >&2 ;;
            esac
        fi
        # Im lặng ở đây là che một tiến trình mồ côi — nói thẳng nếu vẫn còn.
        if kill -0 "$PID" 2>/dev/null; then
            echo "[giao-dien] CẢNH BÁO: pid $PID VẪN SỐNG sau khi dọn — còn tiến trình mồ côi." >&2
        fi
    fi
    rm -rf "$NEN"
    return 0
}
# Bắt cả SIGHUP (đóng terminal) — thiếu nó thì trap không chạy và máy chủ ở lại một mình.
# Mọi tín hiệu đều đi qua `exit` để trap EXIT dọn dẹp, thay vì để script chạy tiếp sau trap.
trap don_dep EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

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
