#!/bin/bash
# ============================================================================
# VIP Express Hub — DỪNG UAT LOCAL BẰNG ĐÚNG PID ĐÃ GHI
# ----------------------------------------------------------------------------
# Chạy:  ./trien_khai/uat/dung.sh
#
# VÌ SAO KHÔNG DIỆT THEO MẪU TÊN TIẾN TRÌNH:
#   Mẫu lệnh đó giết MỌI tiến trình khớp chuỗi, kể cả máy chủ thật của người
#   khác đang chạy trên cùng máy. Đã có tiền lệ. Script này chỉ gửi tín hiệu
#   tới ĐÚNG PID trong $DATA/uat.dang-chay, sau khi kiểm:
#     · PID thuộc user hiện tại,
#     · giờ bắt đầu (lstart) khớp lúc ghi trạng thái,
#     · dòng lệnh chứa đúng "$GOC/app/server.py".
#   Không khớp ⇒ TỪ CHỐI kill, giữ nguyên file trạng thái để người vận hành xem.
#
# Sau khi dừng, script kiểm bằng PID (không đoán):
#     ps -p <PID>  → không còn
#     kết nối TCP tới 127.0.0.1:<cổng> → không còn ai nghe
# ============================================================================
set -euo pipefail
umask 077

THU_MUC_SCRIPT="$(cd "$(dirname "$0")" && pwd -P)"
. "$THU_MUC_SCRIPT/lib.sh"

kiem_tra_vi_tri_du_lieu "${VIP_UAT_DATA:-$DATA_MAC_DINH}"

STATE="$DATA/uat.dang-chay"
if [ ! -f "$STATE" ]; then
    noi "Không có phiên UAT nào đang chạy ($STATE không tồn tại)."
    exit 0
fi

PID="$(lay_state pid "$STATE")"
PORT="$(lay_state port "$STATE")"
LSTART="$(lay_state lstart "$STATE")"
SDATA="$(lay_state data "$STATE")"
SREPO="$(lay_state repo "$STATE")"
SLOG="$(lay_state log "$STATE")"

la_pid_so "$PID" || dung_loi "file trạng thái hỏng: pid='$PID' — KHÔNG kill gì cả."
la_pid_so "$PORT" || dung_loi "file trạng thái hỏng: port='$PORT' — KHÔNG kill gì cả."
[ -n "$LSTART" ] || dung_loi "file trạng thái hỏng: thiếu lstart — KHÔNG kill gì cả."
[ "$SDATA" = "$DATA" ] || dung_loi "file trạng thái thuộc dữ liệu '$SDATA', không phải '$DATA'.
          Đặt VIP_UAT_DATA đúng thư mục đã dùng khi khởi động."
[ "$SREPO" = "$GOC" ] || dung_loi "file trạng thái thuộc repo '$SREPO', không phải '$GOC'."

# PID đã chết từ trước: không có gì để kill, chỉ dọn file trạng thái.
if ! kill -0 "$PID" 2>/dev/null; then
    noi "PID $PID không còn sống — phiên UAT đã dừng trước đó. Dọn file trạng thái cũ."
    rm -f "$STATE"
    noi "Không còn tiến trình UAT nào của lượt này."
    exit 0
fi

# ---- Kiểm thân phận tiến trình TRƯỚC KHI gửi bất kỳ tín hiệu nào ----
# Ba nguồn xác thực độc lập: (1) health của chính máy chủ báo pid, (2) `ps`
# (user + lstart + dòng lệnh), (3) `lsof` (PID đang nghe đúng cổng loopback).
# Cần ít nhất MỘT nguồn khớp. Nếu một nguồn không dùng được (sandbox chặn
# `ps`, ...) thì nói rõ và dựa vào nguồn còn lại — không đoán, không kill mù.
DA_XAC_THUC=0
PS_DUNG="$(lay_state ps "$STATE")"
[ -n "$PS_DUNG" ] || PS_DUNG=1

HEALTH_PID="$(pid_tu_health "$PORT" || true)"
if [ -n "$HEALTH_PID" ]; then
    if [ "$HEALTH_PID" != "$PID" ]; then
        dung_loi "TỪ CHỐI kill: health trên cổng $PORT báo pid=$HEALTH_PID, khác PID đã ghi ($PID).
          Cổng có thể đã bị tiến trình khác chiếm. Giữ nguyên file trạng thái $STATE."
    fi
    noi "Xác thực health: pid=$HEALTH_PID khớp PID đã ghi."
    DA_XAC_THUC=1
else
    canh_bao "health không trả lời — sẽ dựa vào ps/lsof để xác thực."
fi

if ps_dung_duoc; then
    CMD="$(lenh_tien_trinh "$PID")"
    USER_NOW="$(chu_tien_trinh "$PID")"
    LSTART_NOW="$(luc_bat_dau_tien_trinh "$PID")"

    if [ -n "$USER_NOW" ] && [ "$USER_NOW" != "$(id -un)" ]; then
        dung_loi "TỪ CHỐI kill PID $PID: tiến trình thuộc user '$USER_NOW', không phải '$(id -un)'."
    fi
    if [ "$PS_DUNG" != "0" ] && [ "$LSTART" != "KHONG_RO" ] && [ -n "$LSTART_NOW" ]; then
        if [ "$LSTART_NOW" != "$LSTART" ]; then
            canh_bao "  lstart hiện tại : $LSTART_NOW"
            canh_bao "  lstart đã ghi   : $LSTART"
            dung_loi "TỪ CHỐI kill PID $PID: giờ bắt đầu KHÔNG khớp — PID có thể đã bị cấp lại cho
          tiến trình khác. Giữ nguyên file trạng thái $STATE."
        fi
    fi
    if [ -n "$CMD" ]; then
        if ! la_lenh_may_chu_uat "$CMD"; then
            canh_bao "  dòng lệnh: $CMD"
            dung_loi "TỪ CHỐI kill PID $PID: dòng lệnh không chứa '$GOC/app/server.py'.
          Giữ nguyên file trạng thái $STATE."
        fi
        DA_XAC_THUC=1
    else
        canh_bao "ps không đọc được dòng lệnh — bỏ phép kiểm command."
    fi
else
    canh_bao "ps không dùng được — bỏ kiểm user/lstart/command; dùng health + lsof."
fi

# Kiểm cổng đang nghe thuộc đúng PID (nếu có lsof). Chỉ để xác nhận, không kill
# theo cổng.
if command -v lsof >/dev/null 2>&1; then
    if BIND="$(lsof -nP -a -p "$PID" -iTCP -sTCP:LISTEN 2>/dev/null)"; then
        if [ -n "$BIND" ]; then
            case "$BIND" in
                *"127.0.0.1:$PORT"*)
                    DA_XAC_THUC=1 ;;
                *)
                    canh_bao "PID $PID không nghe 127.0.0.1:$PORT theo lsof:"
                    printf '%s\n' "$BIND" >&2
                    dung_loi "TỪ CHỐI kill: trạng thái không khớp. Kiểm tra tay trước." ;;
            esac
        else
            canh_bao "lsof không thấy PID $PID nghe cổng $PORT."
        fi
    else
        canh_bao "lsof không chạy được — bỏ phép kiểm bind."
    fi
fi

if [ "$DA_XAC_THUC" -ne 1 ]; then
    dung_loi "TỪ CHỐI kill PID $PID: KHÔNG có nguồn nào xác thực được tiến trình
          (health, ps, lsof đều không dùng được). Giữ nguyên file trạng thái $STATE."
fi

noi "Gửi SIGTERM tới ĐÚNG PID $PID (cổng $PORT)..."
kill -TERM "$PID" 2>/dev/null || dung_loi "không gửi được SIGTERM tới PID $PID"

# Chờ tối đa 20 giây. Hết hạn mới SIGKILL — vẫn CHỈ PID đó, không theo khuôn.
i=0
while kill -0 "$PID" 2>/dev/null; do
    if [ "$i" -ge 40 ]; then
        canh_bao "PID $PID không thoát sau 20 giây — gửi SIGKILL tới ĐÚNG PID này."
        kill -KILL "$PID" 2>/dev/null || true
        break
    fi
    sleep 0.5
    i=$((i + 1))
done

# Chờ thêm tối đa 5 giây sau SIGKILL.
i=0
while kill -0 "$PID" 2>/dev/null && [ "$i" -lt 10 ]; do
    sleep 0.5
    i=$((i + 1))
done

if kill -0 "$PID" 2>/dev/null; then
    dung_loi "PID $PID VẪN CÒN SỐNG — KHÔNG xoá file trạng thái.
          Kiểm tra tay: ps -ww -p $PID -o pid,ppid,stat,command"
fi

# ---- Chứng minh không còn tiến trình mồ côi ----
if cong_loopback_da_dong "$PORT"; then
    noi "Cổng 127.0.0.1:$PORT đã đóng — không còn ai nghe."
else
    canh_bao "Cổng 127.0.0.1:$PORT VẪN mở sau khi PID $PID đã chết."
    if command -v lsof >/dev/null 2>&1; then
        canh_bao "Tiến trình đang nghe cổng $PORT (KHÔNG tự kill):"
        lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
    fi
    rm -f "$STATE"
    dung_loi "Còn tiến trình nghe cổng $PORT — cần người vận hành xem tay."
fi

# Kiểm thêm: còn tiến trình nào chạy đúng file server của repo này không. Đây là
# phép KIỂM, không phải phép kill; nếu có thì báo để người vận hành biết.
if ps_dung_duoc; then
    CON_LAI="$(ps -ww -axo pid=,command= 2>/dev/null \
        | grep -F "$GOC/app/server.py" \
        | grep -v -F "grep -F" || true)"
    if [ -n "$CON_LAI" ]; then
        canh_bao "Còn tiến trình khác chạy $GOC/app/server.py (KHÔNG tự kill):"
        printf '%s\n' "$CON_LAI" >&2
    else
        noi "Không còn tiến trình nào chạy $GOC/app/server.py."
    fi
else
    noi "ps không dùng được — bỏ phép quét danh sách; đã kiểm bằng PID + cổng loopback ở trên."
fi

rm -f "$STATE"
noi "======================================================================"
noi "ĐÃ DỪNG UAT LOCAL"
noi "  PID $PID : không còn tồn tại (kiểm bằng kill -0)"
noi "  Cổng $PORT : không còn LISTEN (kiểm bằng kết nối TCP loopback)"
noi "  Dữ liệu vẫn ở: $DATA (không bị xoá)"
noi "  Nhật ký máy chủ: ${SLOG:-$DATA/nhat-ky/may-chu.log}"
noi "  Xoá sạch dữ liệu UAT: $THU_MUC_SCRIPT/xoa_du_lieu.sh"
noi "======================================================================"
