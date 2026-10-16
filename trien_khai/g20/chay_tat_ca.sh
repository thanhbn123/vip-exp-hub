#!/bin/sh
# Chạy TRỌN harness HỢP ĐỒNG LỚP HTTP G20/AG-03 trên một nền CÔ LẬP, bind loopback, CỔNG 0.
#
# BA TẦNG, chạy độc lập được:
#   1. TỰ KIỂM BỘ DÒ CHỐT AN TOÀN (13 cấu hình tổng hợp) — một bộ dò không phân biệt được cấu
#      hình an toàn với cấu hình nguy hiểm thì mọi lời khai "đã từ chối chạy" vô nghĩa.
#   2. TIÊM LỖI (14 ca) — chứng minh bộ phán ĐỎ ĐƯỢC, có ĐỐI CHỨNG DƯƠNG. Một harness luôn in
#      "ĐẠT" thì dòng "ĐẠT" ấy không có nghĩa.
#   3. HỢP ĐỒNG (13 chặng) — gọi TỪNG harness con theo đúng cách của nó, gom về MỘT bảng.
#
# KHÔNG gọi API hãng, kể cả sandbox: `V-G09-01` + `V-13906-05` CHƯA CẤP. Mọi máy chủ do các
# harness con dựng đều bind 127.0.0.1 CỔNG 0 (hệ điều hành cấp). Không tunnel, không deploy,
# không push, không mở cổng. `CHO_PHEP_LIVE=False`; chốt D-9 (city/area) giữ CHẶN CỨNG.
#
# DỌN THEO ĐÚNG PID. Không `pkill`, không `killall`: trên máy có nhiều làn chạy song song,
# `pkill -f server.py` giết cả máy chủ của làn khác — một lệnh dọn tay làm hỏng lượt của người
# khác (CLAUDE.md §16.7). Harness tự tắt mọi tiến trình nó spawn; `trap` dưới đây chỉ là lưới
# hứng khi chính nó chết giữa đường, và nó đọc PID từ tệp `pid.txt` do harness ghi.
#
# IN MÃ THOÁT TRƯỚC MỌI ỐNG LỆNH. `| tee` nuốt mã thoát của `python3` (mã thoát của ống là của
# `tee`), và một bộ đo HỎNG sẽ được phán ĐẠT. Đó là khuôn lỗi §7.1 của BAN_GIAO.
set -u
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 2

# ── Chuẩn hoá gia đình `GIT_CONFIG_*` dị dạng ────────────────────────────────
# `GIT_CONFIG_COUNT=N` đòi hỏi đủ `GIT_CONFIG_KEY_0..N-1`. Phiên nào đặt COUNT mà THIẾU khoá
# thì MỌI lệnh git thoát 128 — kể cả `git status` — và hai nhiệt kế đo hai môi trường khác
# nhau (N-G18-00). Gỡ ở ĐÂY chứ không dặn lòng vòng: lời dặn thì người sau quên, dòng mã thì không.
if [ -n "${GIT_CONFIG_COUNT:-}" ] && [ "${GIT_CONFIG_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    _i=0; _thieu=0
    while [ "$_i" -lt "$GIT_CONFIG_COUNT" ]; do
        eval "_k=\${GIT_CONFIG_KEY_$_i:-}"
        if [ -z "$_k" ]; then _thieu=1; fi
        _i=$((_i + 1))
    done
    if [ "$_thieu" -eq 1 ]; then
        echo "[cảnh báo] GIT_CONFIG_COUNT=$GIT_CONFIG_COUNT nhưng thiếu GIT_CONFIG_KEY_* —"
        echo "           gỡ gia đình GIT_CONFIG_* dị dạng (nếu không, MỌI lệnh git thoát 128)."
        unset GIT_CONFIG_COUNT
        for _v in $(env | sed -n 's/^\(GIT_CONFIG_[A-Z_0-9]*\)=.*/\1/p'); do unset "$_v"; done
        unset _v
    fi
    unset _i _thieu _k
fi

NEN_BASE=${VIP_HUB_DATA:-/tmp/veh_g20_ag03}
NEN="$NEN_BASE/lan-$$-$(date +%s 2>/dev/null || echo 0)"
PID_FILE="$NEN/pid.txt"
mkdir -p "$NEN"

don_theo_pid() {
    if [ -f "$PID_FILE" ]; then
        while read -r P; do
            case "$P" in
                ''|*[!0-9]*) continue;;
            esac
            if kill -0 "$P" 2>/dev/null; then
                kill -TERM "$P" 2>/dev/null || true
                echo "[g20] trap: đã tắt pid $P (theo ĐÚNG PID, không dọn theo tên tiến trình)"
            fi
        done < "$PID_FILE"
    fi
}
trap don_theo_pid EXIT INT TERM

echo "══════════════════════════════════════════════════════════════════════════"
echo " G20/AG-03 — HARNESS HỢP ĐỒNG LỚP HTTP"
echo "══════════════════════════════════════════════════════════════════════════"
echo " dự án    = $GOC"
echo " nền      = $NEN"
echo " cổng     = loopback · CỔNG 0 (hệ điều hành cấp) · KHÔNG mở cổng ra ngoài"
echo " adapter  = MOCK · CHO_PHEP_LIVE=False · KHÔNG gọi hãng kể cả sandbox"
echo " giấy phép còn thiếu = V-G09-01 (gọi API hãng) · V-13906-05 (credentials sandbox J&T)"
echo " dọn dẹp  = theo ĐÚNG PID · không pkill/killall"
echo

echo "── TẦNG 1/3. TỰ KIỂM BỘ DÒ CHỐT AN TOÀN ─────────────────────────────────"
python3 trien_khai/g20/chot_an_toan.py --tu-kiem
MA_CHOT=$?
echo ">>> MÃ THOÁT TẦNG 1 = $MA_CHOT"
echo

echo "── TẦNG 2/3. TIÊM LỖI: BỘ PHÁN CÓ ĐỎ ĐƯỢC KHÔNG? ────────────────────────"
python3 trien_khai/g20/tiem_loi.py
MA_TIEM=$?
echo ">>> MÃ THOÁT TẦNG 2 = $MA_TIEM"
echo

echo "── TẦNG 3/3. CHẠY HỢP ĐỒNG (13 chặng) ──────────────────────────────────"
VIP_HUB_DATA="$NEN" python3 trien_khai/g20/chay_hop_dong.py \
    --nen "$NEN/hop-dong" --json "$NEN/bao-cao-g20-hop-dong.json" "$@"
MA_HD=$?
echo ">>> MÃ THOÁT TẦNG 3 = $MA_HD"
echo

echo "══════════════════════════════════════════════════════════════════════════"
echo " TỔNG KẾT — phán bằng MÃ THOÁT, không bằng chữ trong output"
echo "   tự kiểm chốt (1) : mã thoát $MA_CHOT  $([ "$MA_CHOT" -eq 0 ] && echo ĐẠT || echo HỎNG)"
echo "   tiêm lỗi      (2) : mã thoát $MA_TIEM  $([ "$MA_TIEM" -eq 0 ] && echo ĐẠT || echo HỎNG)"
echo "   hợp đồng      (3) : mã thoát $MA_HD  $([ "$MA_HD" -eq 0 ] && echo ĐẠT || echo 'CHƯA ĐẠT')"
echo "══════════════════════════════════════════════════════════════════════════"
echo " bằng chứng: nền $NEN (nhật ký từng chặng ở $NEN/hop-dong/nhat-ky/)"
echo " báo cáo gom: $NEN/bao-cao-g20-hop-dong.json"
echo

if [ "$MA_CHOT" -ne 0 ] || [ "$MA_TIEM" -ne 0 ] || [ "$MA_HD" -ne 0 ]; then
    exit 1
fi
exit 0
