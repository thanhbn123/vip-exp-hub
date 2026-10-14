#!/bin/sh
# Chạy bộ thử E2E qua HTTP THẬT trên một nền CÔ LẬP HOÀN TOÀN.
#
# Vì sao phải cô lập: bộ thử này tạo tenant, tài khoản hãng, đơn và sự kiện webhook THẬT.
# Chạy nó lên `app/du-lieu/` là làm bẩn dữ liệu đang dùng. Nền ở đây là một thư mục tạm
# riêng, xoá sạch khi xong.
#
# Cổng: lấy ngẫu nhiên trong 18000–19999 và THỬ TRƯỚC xem có rỗi không. Cổng cố định làm bộ
# thử báo HỎNG GIẢ khi hai worktree chạy cùng lúc — và báo hỏng giả là kiểu sai tệ nhất với
# một cổng chặn hồi quy (AG-04 báo, 15/10).
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
NEN=$(mktemp -d "${TMPDIR:-/tmp}/veh-e2e.XXXXXX")
don_dep() {
    if [ -n "$PID" ]; then
        # Tắt theo ĐÚNG PID đã giữ lúc khởi động, không bao giờ theo mẫu tên (§16.7).
        kill "$PID" 2>/dev/null || true
        sleep 1
    fi
    rm -rf "$NEN"
}
trap don_dep EXIT INT TERM

CONG=""
i=0
while [ $i -lt 40 ]; do
    thu=$(awk 'BEGIN{srand();print 18000+int(rand()*2000)}')
    if ! nc -z 127.0.0.1 "$thu" 2>/dev/null; then CONG=$thu; break; fi
    i=$((i+1))
done
[ -z "$CONG" ] && { echo "KHÔNG tìm được cổng rỗi sau 40 lượt thử"; exit 2; }

export VIP_HUB_DATA="$NEN" VIP_E2E_CONG="$CONG"
cd "$GOC"
python3 app/migrate.py  > "$NEN/migrate.log" 2>&1
python3 app/khoi_tao.py > "$NEN/seed.log"    2>&1
python3 app/server.py "$CONG" > "$NEN/server.log" 2>&1 &
PID=$!
# Chờ máy chủ MỞ THẬT, không ngủ một con số cố định rồi tin là đã mở.
j=0
while [ $j -lt 50 ]; do
    nc -z 127.0.0.1 "$CONG" 2>/dev/null && break
    kill -0 "$PID" 2>/dev/null || { echo "MÁY CHỦ CHẾT khi khởi động:"; cat "$NEN/server.log"; exit 2; }
    sleep 0.2; j=$((j+1))
done
[ $j -ge 50 ] && { echo "máy chủ không mở cổng $CONG sau 10 giây"; cat "$NEN/server.log"; exit 2; }

echo "[e2e] nền=$NEN cổng=$CONG pid=$PID"
python3 app/thu/thu_e2e.py
MA=$?
echo "[e2e] mã thoát $MA"
exit $MA
