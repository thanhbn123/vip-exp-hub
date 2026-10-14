#!/bin/sh
# Chạy TOÀN BỘ bộ thử của dự án và in bảng tổng kết có PHẠM VI.
#
# Vì sao TỰ DÒ file thay vì liệt kê cứng: danh sách viết cứng là chỗ một bộ thử mới bị quên
# IM LẶNG — thêm `thu_abc.py` mà quên thêm vào danh sách thì nó không bao giờ chạy, và không
# có gì báo. Tự dò thì file mới tự vào. Đổi lại, phải canh ngược: nếu số bộ dò được ÍT HƠN
# ngưỡng tối thiểu thì script HỎNG, chứ không lặng lẽ chạy 0 bộ rồi báo đạt (§12.1 luật 5).
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC"

TOI_THIEU=${VIP_TOI_THIEU_BO:-12}

echo "══════════ BỘ THỬ PYTHON (unittest) ══════════"
TONG=0; SO_BO=0; HONG=""
# `thu_e2e.py` CỐ Ý loại khỏi phép dò: nó cần một máy chủ đang chạy + CSDL cô lập do
# `chay_e2e.sh` dựng, nên chạy một mình là vô nghĩa. Nó vẫn ĐƯỢC CHẠY — ở mục E2E bên dưới,
# qua đúng bộ chạy của nó. Loại ở đây là để không đếm nó hai lần và không báo hỏng giả;
# KHÔNG phải để bỏ qua nó.
for t in $(find app/thu gateway/thu -name 'thu_*.py' -type f ! -name 'thu_e2e.py' | sort); do
    SO_BO=$((SO_BO + 1))
    OUT=$(python3 "$t" 2>&1) || true
    N=$(printf '%s' "$OUT" | grep -oE 'Ran [0-9]+' | tail -1 | grep -oE '[0-9]+' || echo 0)
    N=${N:-0}
    TONG=$((TONG + N))
    # Tìm dòng OK trên TOÀN BỘ output, không phải trên `tail -3`: một số bộ thử in thêm
    # dòng chẩn đoán SAU dòng OK (thu_http.py in hai dòng [ca09]), nên tail -3 bỏ sót OK và
    # báo HỎNG GIẢ. Bộ thử báo hỏng giả là kiểu sai tệ nhất với một cổng chặn hồi quy.
    if printf '%s' "$OUT" | grep -qE '^OK( |$)'; then
        printf '  ✓ %-24s %4s ca\n' "$(basename "$t")" "$N"
    else
        printf '  ✗ %-24s %4s ca  HỎNG\n' "$(basename "$t")" "$N"
        HONG="$HONG $(basename "$t")"
        printf '%s' "$OUT" | grep -E '^(FAIL|ERROR):' | head -8 | sed 's/^/        /'
    fi
done

if [ "$SO_BO" -lt "$TOI_THIEU" ]; then
    echo
    echo "HỎNG: chỉ dò được $SO_BO bộ thử, ngưỡng tối thiểu là $TOI_THIEU."
    echo "Phép dò đang nhìn sai chỗ — KHÔNG được coi là đã chạy hết."
    exit 2
fi

echo
echo "══════════ FRONTEND ══════════"
FE_L=0; FE_H=0
if command -v node >/dev/null 2>&1; then
    if [ -f thu_frontend/thu_logic.mjs ]; then
        # node in dạng `ℹ pass 56` (có ký tự ℹ ở đầu), KHÔNG phải `# pass 56`.
        FE_L=$(node --test thu_frontend/thu_logic.mjs 2>&1 | grep -oE 'pass [0-9]+' | head -1 | grep -oE '[0-9]+' || echo 0)
        FE_L=${FE_L:-0}
        printf '  tầng 1 (logic thuần, node):  %4s ca\n' "$FE_L"
    fi
else
    echo "  tầng 1: BỎ QUA — không có node trên máy này"
fi
if [ -f thu_frontend/thu_http.py ]; then
    O=$(python3 thu_frontend/thu_http.py 2>&1) || true
    FE_H=$(printf '%s' "$O" | grep -oE 'Ran [0-9]+' | tail -1 | grep -oE '[0-9]+' || echo 0)
    FE_H=${FE_H:-0}
    if printf '%s' "$O" | grep -qE '^OK( |$)'; then
        printf '  tầng 2 (HTTP + tệp tĩnh):    %4s ca\n' "$FE_H"
    else
        printf '  tầng 2: HỎNG\n'; HONG="$HONG thu_http.py"
    fi
fi
echo "  tầng 3 (DOM/CSS trong trình duyệt thật): CHƯA TỰ ĐỘNG HOÁ"
echo "     → repo cấm thư viện ngoài nên không có Playwright/Puppeteer (V-13906-01, chờ anh Thành)"

echo
echo "══════════ E2E QUA HTTP THẬT ══════════"
E2E=0
if [ -f app/thu/chay_e2e.sh ]; then
    O=$(sh app/thu/chay_e2e.sh 2>&1) || true
    E2E=$(printf '%s' "$O" | grep -oE 'KẾT QUẢ: [0-9]+/[0-9]+' | head -1 || echo "")
    if printf '%s' "$O" | grep -q 'mã thoát 0'; then
        echo "  ✓ $E2E phép đo đạt"
    else
        echo "  ✗ E2E HỎNG: $E2E"; HONG="$HONG chay_e2e.sh"
        printf '%s' "$O" | grep -E '^\s+✗' | head -8 | sed 's/^/     /'
    fi
fi

echo
echo "══════════════════════════════════════════════════════════"
echo "  python:   $TONG ca · $SO_BO bộ"
echo "  frontend: $FE_L + $FE_H ca (hai tầng tự động)"
echo "  E2E:      $E2E"
echo "  bộ hỏng: ${HONG:- KHÔNG}"
echo
echo "  PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI:"
echo "    đo trên: $(uname -s) $(uname -m) · python $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))') · SQLite $(python3 -c 'import sqlite3;print(sqlite3.sqlite_version)')"
echo "    máy chủ bind 127.0.0.1 · adapter hãng ở chế độ MOCK (CHO_PHEP_LIVE=False cả 5 hãng)"
echo "    NGOÀI phạm vi: VPS · PostgreSQL · nhiều tiến trình (trần rate limit sống trong bộ"
echo "      nhớ MỘT tiến trình) · DOM/CSS trong trình duyệt thật · nhãn hãng thật ·"
echo "      credentials hãng thật · AI thật · dữ liệu lớn · Safari/Firefox"
echo "══════════════════════════════════════════════════════════"
[ -z "$HONG" ] || exit 1
