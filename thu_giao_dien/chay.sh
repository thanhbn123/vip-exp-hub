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
#
# ══════════════════════════════════════════════════════════════════════════════════════════════
# BẢN VÁ AG-06 (dispatch 2) — HAI LỖI BÁO CÁO ĐÃ ĐO ĐƯỢC, KHÔNG PHẢI LỖI SẢN PHẨM:
#
#   LỖI 1 (nuốt dòng PHẠM VI): dòng `PHẠM VI` nằm ở CUỐI thân script, sau lời gọi
#   `npx playwright test`. `set -e` làm shell thoát NGAY tại lời gọi hỏng, nên đúng ở những
#   lượt CÓ CA HỎNG thì `MA=$?`, dòng "mã thoát", dòng "PHẠM VI" và `exit $MA` KHÔNG BAO GIỜ
#   chạy — tức dòng phạm vi biến mất đúng lúc người đọc cần nó nhất. Đo được ở cả hai lượt đỏ
#   (docs/G22_BANPHIM_E2E.md §4). MÃ THOÁT khi ấy vẫn ra 1 một cách TÌNH CỜ (đúng mã của lệnh
#   vừa hỏng), nên suốt nhiều wave không ai thấy.
#   → VÁ: (a) lời gọi playwright được bắt bằng `|| MA=$?` (không để `set -e` nuốt), (b) dòng
#     PHẠM VI + mã thoát THẬT in trong `trap ... EXIT`, tức KHÔNG có đường thoát nào bỏ qua nó.
#
#   LỖI 2 (nói dối về tiến trình đã chết): `kill -0 PID` VẪN THÀNH CÔNG với một tiến trình
#   ZOMBIE (con đã chết nhưng chưa `wait`). Bộ dọn vì thế quay 5 giây vô ích rồi in
#   "pid VẪN SỐNG — còn tiến trình mồ côi" cho một máy chủ ĐÃ CHẾT, và bỏ luôn cơ hội đọc mã
#   thoát THẬT của nó (128+tín hiệu ⇒ biết nó bị giết bằng tín hiệu nào).
#   → VÁ: `may_chu_con_song()` — `kill -0` + đòi tiến trình còn ít nhất một mô tả tệp (zombie
#     thì không còn tệp nào), rồi `wait` để THU LẠI tiến trình và lấy mã thoát thật.
# ══════════════════════════════════════════════════════════════════════════════════════════════
set -e
GOC=$(cd "$(dirname "$0")/.." && pwd)
NEN=$(mktemp -d "${TMPDIR:-/tmp}/veh-giao-dien.XXXXXX")
PID=""
CONG=""
MA_SV=""

# PHẠM VI in ở ĐẦU và in LẠI ở CUỐI (trong trap). Một chuỗi, hai chỗ in — không chép tay hai bản.
PHAM_VI="chỉ Chromium (bản Playwright trong node_modules) · chỉ ba bề rộng 375/768/1280 · không thiết bị cảm ứng thật · không trình đọc màn hình · không in ra giấy/PDF thật · không Safari, không Firefox"
in_pham_vi() {
    echo "[giao-dien] PHẠM VI: $PHAM_VI"
}
in_pham_vi

# Máy chủ còn sống THẬT không. `kill -0` một mình NÓI DỐI với zombie (xem LỖI 2 ở đầu tệp).
may_chu_con_song() {
    [ -n "$PID" ] || return 1
    kill -0 "$PID" 2>/dev/null || return 1
    if command -v lsof >/dev/null 2>&1; then
        # Còn sống thì còn mô tả tệp (stdout/stderr của máy chủ). Zombie: `lsof` không thấy tệp nào.
        [ -n "$(lsof -p "$PID" -F f 2>/dev/null | grep '^f' | head -1)" ] || return 1
    fi
    return 0
}

# Mã thoát 128+tín hiệu ⇒ tên tín hiệu. Một tiến trình TỰ CHẾT vì lỗi để lại traceback trong log;
# một tiến trình BỊ GIẾT bằng tín hiệu thì không — nên tên tín hiệu ở đây là BẰNG CHỨNG, không
# phải suy đoán.
ten_tin_hieu() {
    case "$1" in
        129) echo "SIGHUP(1)" ;;
        130) echo "SIGINT(2)" ;;
        134) echo "SIGABRT(6)" ;;
        137) echo "SIGKILL(9)" ;;
        139) echo "SIGSEGV(11)" ;;
        143) echo "SIGTERM(15)" ;;
        *) echo "" ;;
    esac
}

# Thu lại tiến trình ĐÃ CHẾT (nếu chưa ai thu) và in mã thoát THẬT của máy chủ.
# KHÔNG gọi hàm này khi máy chủ còn sống: `wait` sẽ chặn tới lúc nó chết.
# $1 = "tu-don" khi CHÍNH bộ dọn vừa gửi tín hiệu — phải nói rõ, vì "mã 143" do bộ dọn gửi và
# "mã 143" từ một kẻ giết bên ngoài là HAI chuyện khác hẳn nhau khi đọc bằng chứng.
thu_hoi_may_chu() {
    TU_DON="${1:-}"
    MA_SV=""
    wait "$PID" 2>/dev/null || MA_SV=$?
    if [ -z "$MA_SV" ] || [ "$MA_SV" = "127" ]; then
        echo "[giao-dien] máy chủ pid $PID đã tắt SẠCH theo đúng PID (đã thu lại tiến trình)"
        return 0
    fi
    if [ "$MA_SV" -ge 128 ] 2>/dev/null; then
        if [ -n "$TU_DON" ]; then
            echo "[giao-dien] bộ dọn đã tắt máy chủ pid $PID: mã $MA_SV = $(ten_tin_hieu "$MA_SV") — tín hiệu do CHÍNH bộ dọn gửi"
        else
            echo "[giao-dien] máy chủ pid $PID bị GIẾT BẰNG TÍN HIỆU: mã $MA_SV = $(ten_tin_hieu "$MA_SV") — tín hiệu KHÔNG do bộ dọn gửi"
        fi
    else
        echo "[giao-dien] máy chủ pid $PID tự thoát với mã $MA_SV (không do bộ dọn gửi tín hiệu)"
    fi
}

don_dep() {
    # MÃ THOÁT THẬT phải lấy TRƯỚC mọi lệnh khác: chỉ cần một lệnh chen vào là `$?` đổi và lượt
    # chạy báo sai mã thoát — đúng kiểu "nuốt mã thoát" mà bản trước mắc.
    MA_VAO=$?
    trap - EXIT INT TERM HUP
    set +e
    # (1) MÃ THOÁT — in NGAY, trước khi dọn, để một lỗi lúc dọn không thể nuốt nó.
    echo "[giao-dien] mã thoát THẬT $MA_VAO"
    # (2) PHẠM VI — LUÔN in, kể cả khi có ca hỏng hoặc khi runner thoát sớm (bản vá LỖI 1).
    echo "[giao-dien] PHẠM VI (in lại khi kết thúc): $PHAM_VI"
    # (3) Máy chủ còn sống không — TRƯỚC khi ta tắt nó. Chết ở đây = chết GIỮA LƯỢT: mọi ca hỏng
    #     sau đó là hệ quả của nền, không phải của sản phẩm (§3 tài liệu G22).
    if [ -n "$PID" ]; then
        if may_chu_con_song; then
            echo "[giao-dien] máy chủ pid $PID còn sống khi lượt kết thúc"
            # Tắt theo ĐÚNG PID giữ lúc khởi động. KHÔNG BAO GIỜ theo mẫu tên (§16.7):
            # một lượt `pkill -f cat` đã từng giết cả Ollama và Synology Drive vì chữ "cat"
            # nằm trong "Application".
            kill "$PID" 2>/dev/null || true
            # Chờ tới khi nó CHẾT THẬT rồi mới thôi. `sleep 1` rồi tin là đã chết chính là cách
            # một máy chủ mồ côi sống sót qua lượt chạy: tiền lệ pid 41082 nghe cổng 19449 — đúng
            # dải cổng mà vòng chọn cổng dưới đây dùng — được AG-04 phát hiện ở một lượt sau.
            k=0
            while [ $k -lt 25 ]; do
                may_chu_con_song || break
                sleep 0.2; k=$((k+1))
            done
            # Vẫn sống sau 5 giây: XÁC MINH DANH TÍNH TRƯỚC KHI dùng tín hiệu mạnh, vì PID có thể
            # đã được cấp lại cho một tiến trình KHÁC. Chỉ `kill -9` khi tên vẫn là Python; không
            # xác minh được thì KHÔNG đóng — báo ra để người đọc kiểm tay.
            if may_chu_con_song; then
                TEN=$(ps -o comm= -p "$PID" 2>/dev/null || true)
                case "$TEN" in
                    *[Pp]ython*) kill -9 "$PID" 2>/dev/null || true
                                 echo "[giao-dien] SIGTERM không đủ sau 5 giây — đã dùng SIGKILL cho pid $PID" ;;
                    *) echo "[giao-dien] CẢNH BÁO: pid $PID còn sống nhưng tên tiến trình là '$TEN' — KHÔNG kill -9 (đề phòng PID được cấp lại). Kiểm tay: kill -0 $PID" >&2 ;;
                esac
                k=0
                while [ $k -lt 25 ]; do
                    may_chu_con_song || break
                    sleep 0.2; k=$((k+1))
                done
            fi
            # Im lặng ở đây là che một tiến trình mồ côi — nói thẳng nếu vẫn còn.
            if may_chu_con_song; then
                echo "[giao-dien] CẢNH BÁO: pid $PID VẪN SỐNG sau khi dọn — còn tiến trình mồ côi." >&2
            else
                echo "[giao-dien] bộ dọn đã tắt máy chủ pid $PID theo ĐÚNG PID"
                thu_hoi_may_chu tu-don
            fi
        else
            echo "[giao-dien] CẢNH BÁO: máy chủ pid $PID ĐÃ CHẾT GIỮA LƯỢT (trước khi bộ dọn tắt nó)"
            thu_hoi_may_chu
            if [ -f "$NEN/server.log" ]; then
                # `grep -c` in ra "0" RỒI thoát 1 khi không khớp: viết `|| echo "?"` sẽ ghép thêm
                # một dòng "?" vào biến (đã đo được ở lượt đối chứng đầu tiên) — tách hai bước.
                SO_TB=$(grep -c Traceback "$NEN/server.log" 2>/dev/null)
                [ -z "$SO_TB" ] && SO_TB="?"
                SO_DONG=$(wc -l < "$NEN/server.log" 2>/dev/null | tr -d ' ')
                echo "[giao-dien] log máy chủ: $SO_TB traceback · $SO_DONG dòng · 8 dòng cuối (log đứt giữa dòng + 0 traceback ⇒ bị giết bằng tín hiệu, không phải lỗi mã):"
                tail -8 "$NEN/server.log" 2>/dev/null | sed 's/^/[giao-dien]   /'
            fi
        fi
    fi
    rm -rf "$NEN"
    # Giữ NGUYÊN mã thoát thật của lượt chạy — kể cả khi nó là mã của một lần thoát sớm (2, 130…).
    exit "$MA_VAO"
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

i=0
while [ $i -lt 40 ]; do
    thu=$(awk 'BEGIN{srand();print 18000+int(rand()*2000)}')
    if ! nc -z 127.0.0.1 "$thu" 2>/dev/null; then CONG=$thu; break; fi
    i=$((i+1))
done
[ -z "$CONG" ] && { echo "KHÔNG tìm được cổng rỗi sau 40 lượt thử"; exit 2; }

export VIP_HUB_DATA="$NEN"
# CHỐT 4b của `app/migrate.py` (làn sao lưu, G22): tiến trình gọi `migrate` phải KHAI kho đang
# chạy, thiếu khai thì nó TỪ CHỐI — cố ý, vì `hub.db` CŨ còn sót và `hub.db` ĐANG PHỤC VỤ không
# phân biệt được bằng mtime/kích thước/tên tệp, và bản sao lưu của kho đoán nhầm vẫn trả mã 0.
# Nền của lượt này là SQLite trong thư mục TẠM `$NEN` do chính script này dựng — khai `sqlite` là
# khai ĐÚNG, không phải một mặc định cho tiện. Ghi ra đây để lượt sau không "sửa" nó thành nới chốt.
export VIP_KHO_DANG_CHAY=sqlite
cd "$GOC"
python3 app/migrate.py   > "$NEN/migrate.log" 2>&1 || { echo "[giao-dien] NỀN KHÔNG DỰNG ĐƯỢC: migrate.py thoát $?"; tail -20 "$NEN/migrate.log"; exit 2; }
python3 app/khoi_tao.py  > "$NEN/seed.log"    2>&1 || { echo "[giao-dien] NỀN KHÔNG DỰNG ĐƯỢC: khoi_tao.py thoát $?"; tail -20 "$NEN/seed.log"; exit 2; }
python3 thu_giao_dien/chuan_bi.py mk           || { echo "[giao-dien] NỀN KHÔNG DỰNG ĐƯỢC: chuan_bi.py mk thoát $?"; exit 2; }

python3 app/server.py "$CONG" > "$NEN/server.log" 2>&1 &
PID=$!
# Chờ máy chủ MỞ THẬT. Không `sleep` một con số rồi tin là đã mở.
j=0
while [ $j -lt 50 ]; do
    nc -z 127.0.0.1 "$CONG" 2>/dev/null && break
    may_chu_con_song || { echo "MÁY CHỦ CHẾT khi khởi động (pid $PID):"; cat "$NEN/server.log"; exit 2; }
    sleep 0.2; j=$((j+1))
done
[ $j -ge 50 ] && { echo "máy chủ không mở cổng $CONG sau 10 giây"; cat "$NEN/server.log"; exit 2; }

GOC_URL="http://127.0.0.1:$CONG"
python3 thu_giao_dien/chuan_bi.py don "$GOC_URL" || { echo "[giao-dien] NỀN KHÔNG DỰNG ĐƯỢC: chuan_bi.py don thoát $?"; exit 2; }

echo "[giao-dien] nền=$NEN cổng=$CONG pid=$PID"
# `|| MA=$?` là bản vá LỖI 1: KHÔNG để `set -e` thoát tại đây, nếu không thì mã thoát thật không
# bao giờ được đọc và phần "mã thoát" của dòng PHẠM VI mất luôn.
MA=0
VIP_GD_GOC="$GOC_URL" VIP_GD_NEN="$NEN" PLAYWRIGHT_BROWSERS_PATH=0 \
    npx playwright test "$@" || MA=$?
exit "$MA"
