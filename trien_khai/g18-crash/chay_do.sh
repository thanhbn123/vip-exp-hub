#!/bin/sh
# Chạy lượt ĐO G18/AG-06 — "tiến trình bị tắt GIỮA giao dịch" (`V-13914(a)`).
#
# ====== CÁI GÌ ĐƯỢC GIẾT, VÀ CÁI GÌ KHÔNG ======
# GIẾT: tiến trình con do chính bộ thử này spawn (`os.kill(pid, SIGKILL)`), và tiến trình
#        backend của CỤM PostgreSQL THỬ do chính nó dựng.
# KHÔNG GIẾT: bất cứ tiến trình nào khác trên máy. Không `pkill`, không `killall` — trên máy
#        nhiều làn, dọn theo TÊN là giết cả làn khác (CLAUDE.md §16.7). Chốt C4 của
#        `chot_an_toan.py` dò đúng điều này, bằng AST, trên mọi tệp mã của làn.
#
# ====== BA CHỐT MÔI TRƯỜNG ======
# 1. CSDL nghiệp vụ vẫn là SQLite, trong một thư mục TẠM mới cho mỗi lượt chạy. Không đụng
#    `app/du-lieu/hub.db`.
# 2. PostgreSQL chạy trên CỤM RIÊNG, cổng riêng, socket Unix riêng, `listen_addresses=''`.
#    CẤM cổng 5432 (cụm hệ thống đang giữ `vip_customs*`). Bộ thử TỪ CHỐI nếu ai đó đặt 5432.
# 3. KHÔNG gọi API hãng — kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Lượt này không
#    mở một kết nối mạng nào: mọi phép đo là tiến trình cục bộ + ổ đĩa cục bộ.
#
# CHẠY:
#   sh trien_khai/g18-crash/chay_do.sh
#   sh trien_khai/g18-crash/chay_do.sh --giu-bang-chung /tmp/g18.txt
#   VIP_THU_POSTGRES=0 sh trien_khai/g18-crash/chay_do.sh     # chỉ phần SQLite
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC"

BANG_CHUNG=""
if [ "$1" = "--giu-bang-chung" ] && [ -n "$2" ]; then
    BANG_CHUNG=$2
fi

CONG_PG=${VHG18_CONG_PG:-55718}
if [ "$CONG_PG" = "5432" ]; then
    echo "TỪ CHỐI: VHG18_CONG_PG=5432 là cụm hệ thống đang giữ CSDL dự án khác." >&2
    exit 4
fi

echo "══════════════════════════════════════════════════════════════════════════"
echo " G18/AG-06 — ĐO TIẾN TRÌNH BỊ TẮT GIỮA GIAO DỊCH  (V-13914(a))"
echo "══════════════════════════════════════════════════════════════════════════"
echo " dự án        = $GOC"
echo " CSDL nguồn   = SQLite, thư mục TẠM mới cho mỗi lượt (KHÔNG đụng app/du-lieu/)"
echo " PostgreSQL   = CỤM RIÊNG, cổng $CONG_PG, socket Unix, listen_addresses='' (KHÔNG mở TCP)"
echo " gọi hãng     = KHÔNG (CHO_PHEP_LIVE=False, kể cả sandbox — V-G09-01 chưa cấp)"
echo " mạng         = không mở kết nối nào"
echo

echo "── 0. TỰ KIỂM CHỐT AN TOÀN (14 cấu hình tổng hợp) ─────────────────────────"
set +e
python3 trien_khai/g18-crash/chot_an_toan.py --tu-kiem
MA_CHOT=$?
set -e
echo "   >>> mã thoát = $MA_CHOT"

echo
echo "── 0b. TỰ KIỂM CÁI MÓC GIẾT (`set_trace_callback` bắn TRƯỚC khi câu chạy?) ─"
set +e
python3 trien_khai/g18-crash/do_giet.py --tu-kiem-moc
MA_MOC=$?
set -e
echo "   >>> mã thoát = $MA_MOC"

echo
echo "── 1. BỘ ĐO ĐẦY ĐỦ (SQLite 7 điểm giết + PostgreSQL 9 lượt) ──────────────"
set +e
if [ -n "$BANG_CHUNG" ]; then
    # Ghi ra tệp TRƯỚC rồi mới in: `| tee` nuốt mã thoát của `python3` (mã thoát của ống là
    # của `tee`), và một bộ đo HỎNG sẽ được phán ĐẠT. Đây đúng là khuôn lỗi §7.1 BAN_GIAO.
    python3 app/thu/thu_g18_crash.py >"$BANG_CHUNG" 2>&1
    MA_THU=$?
    cat "$BANG_CHUNG"
else
    python3 app/thu/thu_g18_crash.py
    MA_THU=$?
fi
set -e
echo "   >>> mã thoát bộ đo = $MA_THU"

echo
echo "── 2. DỌN DẸP ────────────────────────────────────────────────────────────"
echo "   Nền tạm do bộ đo tự xoá (ca e2/e3 canh việc đó). Cụm PostgreSQL thử tắt bằng"
echo "   \`pg_ctl stop -m fast\` theo ĐÚNG PID postmaster, không dùng kill theo tên."
echo "   Còn tiến trình nào của làn này không: ca e1 hỏi TỪNG PID đã spawn."

echo
echo "══════════════════════════════════════════════════════════════════════════"
echo " TỔNG KẾT — phán bằng MÃ THOÁT, không bằng chữ trong output"
echo "   chốt an toàn (0)      : mã thoát $MA_CHOT  $([ "$MA_CHOT" -eq 0 ] && echo ĐẠT || echo HỎNG)"
echo "   móc giết     (0b)     : mã thoát $MA_MOC  $([ "$MA_MOC" -eq 0 ] && echo ĐẠT || echo HỎNG)"
echo "   bộ đo        (1)      : mã thoát $MA_THU  $([ "$MA_THU" -eq 0 ] && echo ĐẠT || echo HỎNG)"
echo "══════════════════════════════════════════════════════════════════════════"
if [ -n "$BANG_CHUNG" ]; then
    echo " bằng chứng đầy đủ: $BANG_CHUNG"
fi

if [ "$MA_CHOT" -ne 0 ] || [ "$MA_MOC" -ne 0 ] || [ "$MA_THU" -ne 0 ]; then
    exit 1
fi
exit 0
