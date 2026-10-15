#!/bin/sh
# Dựng một cụm PostgreSQL THỬ, tách hẳn cụm hệ thống. Dừng và xoá bằng `--xoa`.
#
# ====== VÌ SAO KHÔNG DÙNG CỤM :5432 CÓ SẴN ======
# Máy MacBook này (đo 15/10/2026) đang chạy một cụm PostgreSQL hệ thống ở cổng 5432, và cụm
# đó GIỮ CSDL CỦA DỰ ÁN KHÁC: `vip_customs`, `vip_customs_g16`, `vip_customs_test`.
# Tạo CSDL thử ở đó là đặt rác vào nhà người khác, và một lệnh `DROP` gõ nhầm ở đó là mất
# dữ liệu thật. Cụm này dựng riêng, cổng riêng, thư mục riêng, xoá sạch khi xong.
#
# ====== BA CHỖ ĐÃ VẤP, CHÉP LẠI ĐỂ KHÔNG VẤP LẠI ======
# 1. `initdb` hỏng vì locale của máy → phải `LANG=C LC_ALL=C initdb --locale=C --encoding=UTF8`.
# 2. Đường socket Unix dài quá 103 byte thì `pg_ctl` không mở nổi. Thư mục scratchpad của
#    phiên vượt ngưỡng đó, nên socket PHẢI đặt ở đường ngắn: `mktemp -d /tmp/vhpg.XXXX`.
# 3. `listen_addresses=''` — cụm thử KHÔNG mở cổng TCP nào. Chỉ nói chuyện qua socket Unix.
#    Mở TCP trên máy của anh Thành cho một cụm dùng một lần là mở cửa không cần thiết.
#
# ====== DỪNG CỤM: `pg_ctl stop`, KHÔNG `kill`, KHÔNG `pkill` ======
# `CLAUDE.md` §16.7 cấm tắt tiến trình theo mẫu tên trên mọi máy của vault. Một lệnh
# `pkill -f postgres` ở đây sẽ giết luôn cụm :5432 đang giữ dữ liệu dự án khác.
#
# CHẠY:
#   sh trien_khai/postgres/dung_cum_thu.sh          # dựng, in biến môi trường cần export
#   sh trien_khai/postgres/dung_cum_thu.sh --xoa    # dừng và xoá sạch
set -e

THU_MUC=${VHPG_THU_MUC:-/tmp/vhpg_cluster}
CONG=${VHPG_CONG:-55432}
NGUOI=${VHPG_NGUOI:-vhtest}

if [ "$1" = "--xoa" ]; then
    if [ -d "$THU_MUC/data" ]; then
        pg_ctl -D "$THU_MUC/data" stop -m fast >/dev/null 2>&1 || true
    fi
    if [ -f "$THU_MUC/sockpath" ]; then
        rm -rf "$(cat "$THU_MUC/sockpath")" || true
    fi
    rm -rf "$THU_MUC"
    echo "Đã dừng và xoá cụm thử tại $THU_MUC"
    exit 0
fi

for L in initdb pg_ctl psql; do
    command -v "$L" >/dev/null 2>&1 || {
        echo "THIẾU: không có lệnh \`$L\` trên PATH. Không dựng được cụm thử." >&2
        echo "Cài bằng: brew install postgresql@16" >&2
        exit 3
    }
done

# Chốt chặn: không bao giờ dùng cổng 5432.
if [ "$CONG" = "5432" ]; then
    echo "TỪ CHỐI: cổng 5432 là cụm hệ thống đang giữ CSDL dự án khác. Chọn cổng khác." >&2
    exit 4
fi

rm -rf "$THU_MUC"
mkdir -p "$THU_MUC"
LANG=C LC_ALL=C initdb -D "$THU_MUC/data" --locale=C --encoding=UTF8 -U "$NGUOI" \
    >"$THU_MUC/initdb.log" 2>&1 || { tail -20 "$THU_MUC/initdb.log" >&2; exit 5; }

SOCK=$(mktemp -d /tmp/vhpg.XXXX)
printf '%s' "$SOCK" >"$THU_MUC/sockpath"
# `LC_ALL=C` phải đặt cho CẢ `pg_ctl`, không chỉ `initdb` (chỗ vấp thứ 4). Thiếu nó thì
# postmaster chết ngay với `FATAL: postmaster became multithreaded during startup`.
LANG=C LC_ALL=C pg_ctl -D "$THU_MUC/data" -l "$THU_MUC/pg.log" \
       -o "-p $CONG -k $SOCK -c listen_addresses=''" -w start >/dev/null

# Nghiệm thu bằng một lượt TRUY VẤN THẬT, không bằng việc `pg_ctl` báo "server started"
# (§12.1: thứ dùng để kiểm chứng phải được kiểm trước khi tin).
psql -h "$SOCK" -p "$CONG" -U "$NGUOI" -d postgres -qtAX -c "SELECT 1" >/dev/null

echo "Cụm thử SẴN SÀNG · PID $(head -1 "$THU_MUC/data/postmaster.pid")"
echo "export VHPG_SOCKET=$SOCK"
echo "export VHPG_CONG=$CONG"
echo "export VHPG_NGUOI=$NGUOI"
echo "Xoá khi xong: sh trien_khai/postgres/dung_cum_thu.sh --xoa"
