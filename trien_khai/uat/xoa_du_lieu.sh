#!/bin/bash
# ============================================================================
# VIP Express Hub — XOÁ SẠCH DỮ LIỆU UAT LOCAL
# ----------------------------------------------------------------------------
# Chạy:  ./trien_khai/uat/xoa_du_lieu.sh          (hỏi xác nhận)
#        ./trien_khai/uat/xoa_du_lieu.sh --yes    (không hỏi; dùng trong script)
#
# Chỉ xoá thư mục do bộ script này tạo — nhận diện bằng dấu
# `.veh-uat-fixture.json` có `loai=VEH-UAT-FIXTURE` và đúng đường dẫn repo.
# TỪ CHỐI nếu:
#   · thư mục không có dấu UAT (có thể là dữ liệu thật),
#   · thư mục nằm trong repo / là app/du-lieu / /du-lieu / thư mục nhà,
#   · phiên UAT còn đang chạy (phải chạy dung.sh trước).
#
# Đây là lệnh XOÁ DUY NHẤT trong bộ script. `dung.sh` không xoá dữ liệu.
# ============================================================================
set -euo pipefail
umask 077

THU_MUC_SCRIPT="$(cd "$(dirname "$0")" && pwd -P)"
. "$THU_MUC_SCRIPT/lib.sh"

kiem_tra_vi_tri_du_lieu "${VIP_UAT_DATA:-$DATA_MAC_DINH}"

if [ ! -d "$DATA" ]; then
    noi "Không có thư mục dữ liệu UAT để xoá: $DATA"
    exit 0
fi
if [ ! -f "$MARKER" ]; then
    dung_loi "TỪ CHỐI xoá '$DATA': không có dấu UAT ($TEN_DAU_UAT).
          Không xoá thư mục không rõ nguồn gốc — có thể là dữ liệu thật."
fi
la_dau_uat_hop_le || dung_loi "TỪ CHỐI xoá '$DATA': dấu UAT không hợp lệ hoặc thuộc dự án khác."

# Không xoá khi phiên còn chạy.
STATE="$DATA/uat.dang-chay"
if [ -f "$STATE" ]; then
    pid_dang_chay="$(lay_state pid "$STATE")"
    if tien_trinh_con_song "$pid_dang_chay"; then
        dung_loi "TỪ CHỐI xoá: UAT vẫn đang chạy (PID $pid_dang_chay).
          Chạy $THU_MUC_SCRIPT/dung.sh trước, rồi xoá dữ liệu."
    fi
    canh_bao "File trạng thái cũ ghi PID $pid_dang_chay nhưng tiến trình đã chết — sẽ dọn cùng thư mục."
fi

# Tóm tắt để người chạy biết mình sắp xoá cái gì.
SO_TEP="$(find "$DATA" -type f 2>/dev/null | wc -l | tr -d ' ')"
DUNG_LUONG="$(du -sh "$DATA" 2>/dev/null | awk '{print $1}' || true)"
noi "Thư mục sắp xoá : $DATA"
noi "Dấu UAT         : $MARKER (hợp lệ)"
noi "Số tệp / dung lượng: ${SO_TEP:-?} tệp · ${DUNG_LUONG:-?}"
noi "CSDL UAT        : $DATA/hub.db (KHÔNG phải app/du-lieu)"
if [ "${1:-}" != "--yes" ] && [ "${1:-}" != "-y" ]; then
    printf '[uat] Gõ đúng chữ "xoa" để xác nhận: '
    if ! read -r xac_nhan; then
        xac_nhan=""
    fi
    if [ "$xac_nhan" != "xoa" ]; then
        noi "Đã huỷ — không xoá gì."
        exit 1
    fi
fi

# Chốt cuối: đường dẫn đã được chuẩn hoá + kiểm vị trí + có dấu UAT. Không dùng
# biến chưa kiểm, không xoá theo khuôn.
[ "$(chuan_hoa_duong "$DATA")" = "$DATA" ] || dung_loi "TỪ CHỐI: đường dẫn thay đổi sau khi kiểm."
la_dau_uat_hop_le || dung_loi "TỪ CHỐI: dấu UAT biến mất ngay trước khi xoá."

rm -rf "$DATA"
if [ -e "$DATA" ]; then
    dung_loi "XOÁ KHÔNG HẾT: $DATA vẫn tồn tại — kiểm tra quyền/ổ đĩa."
fi
noi "ĐÃ XOÁ SẠCH dữ liệu UAT: $DATA"
noi "Lần khởi động sau sẽ tạo thư mục mới + bộ tài khoản FIXTURE mới."
