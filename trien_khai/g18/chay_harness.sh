#!/bin/sh
# Chạy harness TẢI HTTP THẬT của G18 (làn AG-04) trên một nền CÔ LẬP, loopback, CỔNG 0.
#
# Vì sao phải cô lập: kịch bản này TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT trong
# CSDL, rồi bắn vài trăm yêu cầu vào đó. Chạy nó lên `app/du-lieu/` là làm bẩn dữ liệu đang dùng —
# và harness TỪ CHỐI CHẠY nếu `VIP_HUB_DATA` trỏ vào đó (chốt G17-1).
#
# KHÔNG gọi hãng thật, kể cả sandbox: `V-G09-01` + `V-13906-05` CHƯA CẤP. Adapter là MOCK. Máy
# chủ bind `127.0.0.1` CỔNG 0 (hệ điều hành cấp). Không tunnel, không deploy, không mở cổng.
#
# TẮT MÁY CHỦ THEO ĐÚNG PID. Không `pkill`, không `killall`: trên máy có nhiều làn chạy song
# song, `pkill -f server.py` giết cả máy chủ của làn khác — một lệnh dọn tay làm hỏng lượt của
# người khác. Lượt này spawn HAI tiến trình, nên tệp pid có THỂ NHIỀU DÒNG; `trap` đọc hết.
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
NEN_BASE=${VIP_HUB_DATA:-/tmp/veh_g18_ag04}
NEN="$NEN_BASE/g18_tai"
PID_FILE="$NEN/hub.pid"

don_theo_pid() {
    if [ -f "$PID_FILE" ]; then
        while read -r P; do
            case "$P" in
                ''|*[!0-9]*) continue;;
            esac
            if kill -0 "$P" 2>/dev/null; then
                kill -TERM "$P" 2>/dev/null || true
                echo "[g18] trap: đã tắt pid $P (theo ĐÚNG PID, không dọn theo tên tiến trình)"
            fi
        done < "$PID_FILE"
    fi
}
trap don_theo_pid EXIT INT TERM

# Xoá nền CŨ của chính harness này thôi — không đụng thư mục nào khác.
if [ -d "$NEN" ]; then rm -rf "$NEN"; fi
mkdir -p "$NEN"

echo "[g18] dự án   = $GOC"
echo "[g18] nền     = $NEN"
echo "[g18] cổng    = loopback, CỔNG 0 (hệ điều hành cấp) — KHÔNG mở cổng ra ngoài"
echo "[g18] adapter = MOCK · CHO_PHEP_LIVE=False · KHÔNG gọi hãng kể cả sandbox"
echo "[g18] tiến trình máy chủ = 2 (để đo B-G11-10: trần có nhân theo số bản không)"
echo

# TỰ KIỂM trước khi tin bất kỳ lời khai nào. BỐN tầng, và tầng nào cũng cần:
#   1. bộ dò CHỐT AN TOÀN (14 cấu hình tổng hợp) — bảy chốt mượn của G17 + năm chốt của G18;
#   2. BỘ ĐO TẢI bắn vào máy chủ giả cố tình hỏng — bộ đo phải BÁO RA được 5xx và lỗi kết nối,
#      và phải báo 0 lỗi trên máy chủ lành;
#   3. BỘ PHÁN QUYẾT TRẦN trên bốn chuỗi mã trạng thái tổng hợp;
#   4. CHỨNG MINH NGƯỢC: tiêm lỗi vào chính bộ đo rồi đòi tầng 2 và tầng 3 phải ĐỎ.
# Một bộ đo không phân biệt được máy chủ lành với máy chủ hỏng thì mọi con số nó in ra là số đo
# của chính nó, không phải của hệ. Và một bộ tự kiểm luôn in "đạt" thì dòng "đạt" ấy không có
# nghĩa — nên tầng 4 tồn tại: nó là thứ duy nhất chứng minh ba tầng trên ĐỎ ĐƯỢC.
python3 "$GOC/trien_khai/g18/chot_an_toan.py" --tu-kiem || exit $?
echo
python3 "$GOC/trien_khai/g18/harness_tai.py" --tu-kiem || exit $?
echo
python3 "$GOC/trien_khai/g18/tiem_loi.py" || exit $?
echo

VIP_HUB_DATA="$NEN" python3 "$GOC/trien_khai/g18/harness_tai.py" \
    --json "$NEN/bao-cao-g18.json" --so-tien-trinh 2 "$@"
