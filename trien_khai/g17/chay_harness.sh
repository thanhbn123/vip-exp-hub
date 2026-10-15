#!/bin/sh
# Chạy harness G17 (webhook: replay + chống trùng) trên một nền CÔ LẬP, cổng loopback cổng 0.
#
# Vì sao phải cô lập: kịch bản này TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT trong
# CSDL. Chạy nó lên `app/du-lieu/` là làm bẩn dữ liệu đang dùng — và harness TỪ CHỐI CHẠY nếu
# `VIP_HUB_DATA` trỏ vào đó.
#
# KHÔNG gọi hãng thật, kể cả sandbox: `V-G09-01` + `V-13906-05` CHƯA CẤP. Máy chủ bind CỔNG 0
# trên 127.0.0.1; mọi callback đi qua stub bind 127.0.0.1 cổng 0. Không tunnel, không deploy.
#
# TẮT MÁY CHỦ THEO ĐÚNG PID. Không `pkill`, không `killall`: trên máy có nhiều làn chạy song
# song, `pkill -f server.py` giết cả máy chủ của làn khác — một lệnh dọn tay làm hỏng lượt của
# người khác. Harness tự tắt máy chủ nó spawn; `trap` dưới đây chỉ là lưới hứng khi harness chết
# giữa đường, và nó đọc PID từ tệp `hub.pid` do chính harness ghi.
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
NEN_BASE=${VIP_HUB_DATA:-/tmp/veh_g17_ag04}
NEN="$NEN_BASE/g17_harness"
PID_FILE="$NEN/hub.pid"

don_theo_pid() {
    if [ -f "$PID_FILE" ]; then
        P=$(cat "$PID_FILE" 2>/dev/null || true)
        case "$P" in
            ''|*[!0-9]*) echo "[g17] tệp pid không có số hợp lệ — không tắt gì";;
            *)
                if kill -0 "$P" 2>/dev/null; then
                    kill -TERM "$P" 2>/dev/null || true
                    echo "[g17] trap: đã tắt pid $P (theo ĐÚNG PID, không dọn theo tên tiến trình)"
                fi
                ;;
        esac
    fi
}
trap don_theo_pid EXIT INT TERM

# Xoá nền CŨ của chính harness này thôi — không đụng thư mục nào khác.
if [ -d "$NEN" ]; then rm -rf "$NEN"; fi
mkdir -p "$NEN"

echo "[g17] dự án   = $GOC"
echo "[g17] nền     = $NEN"
echo "[g17] cổng    = loopback, CỔNG 0 (hệ điều hành cấp); stub bên gửi cũng cổng 0"
echo "[g17] adapter = MOCK · CHO_PHEP_LIVE=False · KHÔNG gọi hãng kể cả sandbox"
echo "[g17] chặng   = SANDBOX (gửi sang hãng + callback theo sơ đồ hãng) là BLOCKED"
echo

# TỰ KIỂM trước khi tin bất kỳ lời khai nào: bộ dò chốt an toàn (12 cấu hình tổng hợp) và bộ đếm
# phán quyết (`BLOCKED` KHÔNG được tính là đạt). Một bộ dò không phân biệt được cấu hình an toàn
# với cấu hình nguy hiểm thì lời khai "harness đã từ chối chạy" vô nghĩa.
python3 "$GOC/trien_khai/g17/chot_an_toan.py" --tu-kiem || exit $?
echo
python3 "$GOC/trien_khai/g17/harness_webhook.py" --tu-kiem || exit $?
echo

VIP_HUB_DATA="$NEN" python3 "$GOC/trien_khai/g17/harness_webhook.py" \
    --json "$NEN/bao-cao-g17.json" "$@"
