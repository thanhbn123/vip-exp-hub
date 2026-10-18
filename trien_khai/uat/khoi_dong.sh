#!/bin/bash
# ============================================================================
# VIP Express Hub — KHỞI ĐỘNG UAT LOCAL (dữ liệu RIÊNG, KHÔNG dùng dữ liệu thật)
# ----------------------------------------------------------------------------
# Chạy:  ./trien_khai/uat/khoi_dong.sh
#
# Script này làm đúng bốn việc:
#   1. TỪ CHỐI nếu thư mục dữ liệu trỏ vào dữ liệu thật (repo, app/du-lieu,
#      /du-lieu, thư mục không rỗng mà không có dấu UAT, ...).
#   2. Dựng schema + seed TÀI KHOẢN FIXTURE vào thư mục RIÊNG (mặc định ~/veh-uat).
#   3. Nghe 127.0.0.1 với CỔNG DO OS CẤP; ghi PID + cổng + giờ bắt đầu vào
#      $DATA/uat.dang-chay để `dung.sh` dừng đúng tiến trình.
#   4. Tự gọi /api/v2/suc-khoe qua loopback để chứng minh máy chủ thật sự phục vụ.
#
# KHÔNG gọi API hãng (kể cả sandbox) · KHÔNG tạo đơn thật · KHÔNG dùng
# credentials thật. Mọi adapter hãng ở chế độ mock với live_mo=False.
# ============================================================================
set -euo pipefail
umask 077

# `cd` về thư mục chứa script trước khi source: lib.sh tự xác định GOC từ BASH_SOURCE.
THU_MUC_SCRIPT="$(cd "$(dirname "$0")" && pwd -P)"
. "$THU_MUC_SCRIPT/lib.sh"

# ---------------------------------------------------------------------------
# 0. Điều kiện tối thiểu
# ---------------------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || dung_loi "không có python3 trong PATH"
[ -f "$GOC/app/server.py" ] || dung_loi "không thấy $GOC/app/server.py — chạy script từ đúng repo"
[ -f "$GOC/app/migrate.py" ] || dung_loi "không thấy $GOC/app/migrate.py"
[ -f "$GOC/app/khoi_tao.py" ] || dung_loi "không thấy $GOC/app/khoi_tao.py"
[ -f "$GOC/trien_khai/uat/tao_du_lieu_uat.py" ] || \
    dung_loi "không thấy $GOC/trien_khai/uat/tao_du_lieu_uat.py"

# ---------------------------------------------------------------------------
# 1. Chốt an toàn: dữ liệu RIÊNG, không phải dữ liệu thật
# ---------------------------------------------------------------------------
kiem_tra_vi_tri_du_lieu "${VIP_UAT_DATA:-$DATA_MAC_DINH}"
kiem_tra_moi_truong_an_toan

STATE="$DATA/uat.dang-chay"

# Nếu đã có phiên chạy: chỉ chấp nhận khi PID còn sống và đúng là máy chủ UAT.
# Không bao giờ "dọn" một tiến trình lạ; chỉ dọn file trạng thái đã chết.
if [ -f "$STATE" ]; then
    pid_cu="$(lay_state pid "$STATE")"
    if tien_trinh_con_song "$pid_cu"; then
        la_cua_minh=0
        cmd_cu="$(lenh_tien_trinh "$pid_cu")"
        if [ -n "$cmd_cu" ] && la_lenh_may_chu_uat "$cmd_cu"; then
            la_cua_minh=1
        fi
        # `ps` có thể bị sandbox chặn: hỏi health của cổng đã ghi. Health trả
        # đúng pid_cu thì đó chính là máy chủ UAT của mình.
        if [ "$la_cua_minh" -ne 1 ]; then
            port_cu="$(lay_state port "$STATE")"
            if la_pid_so "$port_cu"; then
                hp_cu="$(pid_tu_health "$port_cu" || true)"
                if [ "$hp_cu" = "$pid_cu" ]; then
                    la_cua_minh=1
                fi
            fi
        fi
        if [ "$la_cua_minh" -eq 1 ]; then
            dung_loi "UAT đang chạy sẵn (PID $pid_cu). Dừng trước bằng:
          $THU_MUC_SCRIPT/dung.sh"
        fi
        dung_loi "TỪ CHỐI: $STATE ghi PID $pid_cu, tiến trình này còn sống nhưng KHÔNG xác thực
          được là máy chủ UAT. Không ghi đè, không kill.
          Kiểm tra: ps -p $pid_cu -o pid,command  (hoặc xem $STATE)"
    fi
    canh_bao "File trạng thái cũ $STATE ghi PID $pid_cu nhưng tiến trình không còn sống — dọn file cũ."
    rm -f "$STATE"
fi

kiem_tra_thu_muc_uat
tao_thu_muc_uat

if [ -e "$GOC/app/du-lieu" ]; then
    noi "GHI CHÚ: $GOC/app/du-lieu có tồn tại — bộ script này KHÔNG đọc/ghi vào đó."
else
    noi "GHI CHÚ: $GOC/app/du-lieu không tồn tại — không có dữ liệu sản phẩm trên máy này."
fi

NHAT_KY="$DATA/nhat-ky"
mkdir -p "$NHAT_KY" || dung_loi "không tạo được $NHAT_KY"
chmod 700 "$NHAT_KY" 2>/dev/null || true

MIGRATE_LOG="$NHAT_KY/migrate.log"
SEED_LOG="$NHAT_KY/seed.log"
KIEM_TRA_LOG="$NHAT_KY/kiem-tra-an-toan.log"
MAY_CHU_LOG="$NHAT_KY/may-chu.log"
for f in "$MIGRATE_LOG" "$SEED_LOG" "$KIEM_TRA_LOG" "$MAY_CHU_LOG"; do
    : > "$f"
    chmod 600 "$f" 2>/dev/null || true
done

# Mọi lượt chạy con đều nhận CÙNG một môi trường tối thiểu này. `env` chỉ đặt
# cho tiến trình con, không làm bẩn shell của người chạy.
MT_UAT=(env
    "VIP_HUB_DATA=$DATA"
    "VIP_KHO_DANG_CHAY=sqlite"
    "VIP_HUB_BIND=127.0.0.1"
    "VIP_HUB_PORT=0"
    "VIP_JT_MOI_TRUONG=mock"
    "VIP_HUB_RESET_TOKEN=0"
    "VIP_HUB_HTTPS=0"
    "VIP_HUB_PROXY_TIN_CAY="
    "PYTHONPATH=$GOC/app"
    "PYTHONDONTWRITEBYTECODE=1"
    "PYTHONUNBUFFERED=1"
    "PYTHONIOENCODING=utf-8"
)

# ---------------------------------------------------------------------------
# 2. Schema + seed TÀI KHOẢN FIXTURE + dữ liệu mẫu
# ---------------------------------------------------------------------------
noi "1/4  Nâng schema trên thư mục RIÊNG: $DATA"
if ! "${MT_UAT[@]}" python3 "$GOC/app/migrate.py" >> "$MIGRATE_LOG" 2>&1; then
    tail -n 25 "$MIGRATE_LOG" >&2 || true
    dung_loi "migrate HỎNG — xem $MIGRATE_LOG"
fi

noi "2/4  Seed tài khoản FIXTURE + dữ liệu mẫu (KHÔNG phải dữ liệu thật)"
if ! "${MT_UAT[@]}" python3 "$GOC/app/khoi_tao.py" >> "$SEED_LOG" 2>&1; then
    tail -n 25 "$SEED_LOG" >&2 || true
    dung_loi "seed HỎNG — xem $SEED_LOG"
fi
if ! "${MT_UAT[@]}" python3 "$THU_MUC_SCRIPT/tao_du_lieu_uat.py" >> "$SEED_LOG" 2>&1; then
    tail -n 25 "$SEED_LOG" >&2 || true
    dung_loi "seed dữ liệu mẫu HỎNG — xem $SEED_LOG"
fi

# Gói tài khoản seed vào một file DUY NHẤT có nhãn FIXTURE rõ ràng. Không bao
# giờ in mật khẩu ra stdout/terminal: file 0600 nằm trong thư mục dữ liệu 0700.
TAI_KHOAN="$DATA/TAI-KHOAN-UAT.md"
if [ -f "$DATA/TAI-KHOAN-DEMO.md" ]; then
    {
        printf '# TÀI KHOẢN FIXTURE — UAT LOCAL\n\n'
        printf '> **MẬT KHẨU DƯỚI ĐÂY LÀ FIXTURE — KHÔNG PHẢI MẬT KHẨU THẬT.**\n'
        printf '> Chỉ dùng trên máy này. Máy chủ chỉ nghe 127.0.0.1. Không dùng cho production.\n'
        printf '> Dấu UAT: `%s`\n\n' "$MARKER"
        printf 'Mật khẩu do `app/khoi_tao.py` sinh ngẫu nhiên khi tạo thư mục UAT lần đầu.\n'
        printf 'Nếu làm mất file này, mật khẩu không khôi phục được: hãy xoá dữ liệu UAT\n'
        printf 'bằng `xoa_du_lieu.sh` rồi khởi động lại để nhận bộ tài khoản mới.\n\n'
        printf -- '---\n\n'
        cat "$DATA/TAI-KHOAN-DEMO.md"
    } > "$TAI_KHOAN.tam"
    chmod 600 "$TAI_KHOAN.tam"
    mv "$TAI_KHOAN.tam" "$TAI_KHOAN"
else
    canh_bao "không thấy $DATA/TAI-KHOAN-DEMO.md (dữ liệu đã tồn tại từ trước?)."
    canh_bao "Mật khẩu fixture không khôi phục được — xem hướng dẫn trong docs/UAT_LOCAL.md."
fi

# Chốt cuối trước khi mở cổng: KHÔNG có adapter hãng nào được phép gọi mạng,
# và KHÔNG có tài khoản hãng nào khác `mock` trong CSDL UAT.
noi "3/4  Kiểm tra an toàn: adapter mock + CSDL không có tài khoản hãng thật"
if ! "${MT_UAT[@]}" python3 - "$DATA" >> "$KIEM_TRA_LOG" 2>&1 <<'PY'
import os
import sqlite3
import sys

# Nạp registry adapter để kiểm tra CẢ MÃ, không chỉ dữ liệu trong CSDL.
import adapter          # noqa: F401
import adapter_jt       # noqa: F401
import adapter_vtp      # noqa: F401

data = os.path.realpath(sys.argv[1])
db = os.path.join(data, "hub.db")

live = [ma for ma, h in adapter.danh_sach_hang().items() if h.get("live_mo")]
if live:
    sys.exit("[kiem-tra] TỪ CHỐI: adapter có live_mo=True: %r" % (live,))

con = sqlite3.connect(db)
try:
    live_db = con.execute("SELECT ma FROM carrier_providers WHERE live_mo<>0").fetchall()
    if live_db:
        sys.exit("[kiem-tra] TỪ CHỐI: carrier_providers live_mo<>0: %r" % (live_db,))
    khac_mock = con.execute(
        "SELECT id, hang, moi_truong FROM carrier_accounts WHERE moi_truong<>'mock'").fetchall()
    if khac_mock:
        sys.exit("[kiem-tra] TỪ CHỐI: carrier_accounts khác mock: %r" % (khac_mock,))
    so_hang = con.execute("SELECT COUNT(*) FROM carrier_providers").fetchone()[0]
    so_tk = con.execute("SELECT COUNT(*) FROM carrier_accounts").fetchone()[0]
    so_don = con.execute("SELECT COUNT(*) FROM don_hang").fetchone()[0]
    so_user = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
finally:
    con.close()

print("[kiem-tra] Adapter đăng ký: %s — tất cả live_mo=False"
      % ", ".join(sorted(adapter.danh_sach_hang())))
print("[kiem-tra] carrier_providers=%d (live_mo=0) · carrier_accounts=%d (mock) · users=%d · don_hang=%d"
      % (so_hang, so_tk, so_user, so_don))
print("[kiem-tra] VIP_JT_MOI_TRUONG=%r · VIP_HUB_DATA=%s"
      % (os.environ.get("VIP_JT_MOI_TRUONG"), data))
PY
then
    tail -n 25 "$KIEM_TRA_LOG" >&2 || true
    dung_loi "chốt an toàn KHÔNG đạt — xem $KIEM_TRA_LOG"
fi

# ---------------------------------------------------------------------------
# 3. Khởi động máy chủ: 127.0.0.1 + cổng 0 (OS cấp)
# ---------------------------------------------------------------------------
noi "4/4  Khởi động máy chủ tại 127.0.0.1, cổng do OS cấp..."
PID=""
DA_SAN_SANG=0
don_dep_khi_loi() {
    if [ "$DA_SAN_SANG" -ne 1 ] && [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
        canh_bao "Khởi động chưa hoàn tất — dừng ĐÚNG PID $PID để không để lại tiến trình mồ côi."
        kill -TERM "$PID" 2>/dev/null || true
        i=0
        while kill -0 "$PID" 2>/dev/null && [ "$i" -lt 25 ]; do
            sleep 0.2
            i=$((i + 1))
        done
        kill -KILL "$PID" 2>/dev/null || true
    fi
}
trap don_dep_khi_loi EXIT

cd "$GOC"
"${MT_UAT[@]}" python3 "$GOC/app/server.py" 0 >> "$MAY_CHU_LOG" 2>&1 &
PID=$!

PORT=""
i=0
while [ "$i" -lt 100 ]; do
    if ! kill -0 "$PID" 2>/dev/null; then
        tail -n 30 "$MAY_CHU_LOG" >&2 || true
        dung_loi "máy chủ thoát ngay sau khi khởi động — xem $MAY_CHU_LOG"
    fi
    PORT="$(sed -n 's#.*http://127\.0\.0\.1:\([0-9][0-9]*\).*#\1#p' "$MAY_CHU_LOG" | head -1)"
    if [ -n "$PORT" ]; then
        break
    fi
    sleep 0.2
    i=$((i + 1))
done
if [ -z "$PORT" ]; then
    tail -n 30 "$MAY_CHU_LOG" >&2 || true
    dung_loi "không đọc được cổng từ log máy chủ — xem $MAY_CHU_LOG"
fi
la_pid_so "$PORT" || dung_loi "cổng đọc được không phải số: $PORT"
[ "$PORT" -gt 0 ] || dung_loi "cổng OS cấp không hợp lệ: $PORT"

# Chứng minh socket chỉ nghe loopback và thuộc ĐÚNG PID vừa khởi động.
# `lsof` có thể bị chặn trong một số sandbox: khi đó BỎ QUA phép kiểm này và
# nói rõ, KHÔNG coi là đã kiểm. Trên máy thật (không sandbox) nó chạy bình
# thường và là bằng chứng bind loopback.
if command -v lsof >/dev/null 2>&1; then
    if BIND="$(lsof -nP -a -p "$PID" -iTCP -sTCP:LISTEN 2>/dev/null)"; then
        case "$BIND" in
            *"127.0.0.1:$PORT"*) ;;
            *)
                printf '%s\n' "$BIND" >&2
                dung_loi "không thấy PID $PID nghe 127.0.0.1:$PORT — TỪ CHỐI coi là đã sẵn sàng" ;;
        esac
        if printf '%s\n' "$BIND" | grep -Eq '(^|[^0-9])(\*|0\.0\.0\.0):'"$PORT"'([^0-9]|$)'; then
            printf '%s\n' "$BIND" >&2
            dung_loi "TỪ CHỐI: máy chủ đang nghe RA NGOÀI (0.0.0.0/*:$PORT)."
        fi
    else
        canh_bao "lsof không chạy được — bỏ phép kiểm bind; vẫn kiểm bằng health PID + log."
    fi
fi

# Gọi thật một API loopback. Đây là bằng chứng máy chủ phục vụ, không phải chỉ
# "tiến trình còn sống".
if ! python3 - "$PORT" <<'PY'
import json
import sys
import time
import urllib.request

port = int(sys.argv[1])
url = "http://127.0.0.1:%d/api/v2/suc-khoe" % port
loi_cuoi = None
for _ in range(25):
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            body = r.read().decode("utf-8")
            if r.status == 200:
                d = json.loads(body)
                print("[kiem-tra] GET %s -> 200 %s"
                      % (url, json.dumps(d, ensure_ascii=False)[:240]))
                sys.exit(0)
            loi_cuoi = "HTTP %s" % r.status
    except Exception as e:                       # noqa: BLE001
        loi_cuoi = repr(e)
    time.sleep(0.2)
print("[kiem-tra] health KHÔNG đạt sau 5 giây: %s" % loi_cuoi, file=sys.stderr)
sys.exit(1)
PY
then
    tail -n 30 "$MAY_CHU_LOG" >&2 || true
    dung_loi "API loopback /api/v2/suc-khoe KHÔNG trả 200"
fi

# Xác thực ngược: health tự báo pid. Nếu pid đó khớp PID ta vừa spawn thì
# tiến trình đang nghe cổng ĐÚNG là tiến trình của mình — bằng chứng không phụ
# thuộc `ps` (thứ có thể bị sandbox chặn, nhưng trên máy thật vẫn dùng thêm).
HEALTH_PID="$(pid_tu_health "$PORT" || true)"
[ -n "$HEALTH_PID" ] || dung_loi "health 200 nhưng không đọc được pid — TỪ CHỐI coi là đã sẵn sàng"
[ "$HEALTH_PID" = "$PID" ] || dung_loi "health báo pid=$HEALTH_PID nhưng PID đã spawn là $PID — TỪ CHỐI."
noi "      Xác thực: health báo pid=$HEALTH_PID, khớp PID đã ghi"

# ---------------------------------------------------------------------------
# 4. Ghi trạng thái để dung.sh dừng ĐÚNG tiến trình
# ---------------------------------------------------------------------------
LSTART="$(luc_bat_dau_tien_trinh "$PID")"
PS_DUNG=1
if [ -z "$LSTART" ]; then
    # `ps` bị chặn (sandbox) hoặc không có. Vẫn an toàn: PID + health pid + lsof
    # là ba mảnh xác thực; `dung.sh` sẽ bỏ phép so lstart và nói rõ.
    PS_DUNG=0
    LSTART="KHONG_RO"
    canh_bao "ps không dùng được — bỏ phép so lstart; vẫn xác thực bằng health pid + lsof."
fi
{
    printf 'pid=%s\n' "$PID"
    printf 'port=%s\n' "$PORT"
    printf 'lstart=%s\n' "$LSTART"
    printf 'ps=%s\n' "$PS_DUNG"
    printf 'data=%s\n' "$DATA"
    printf 'repo=%s\n' "$GOC"
    printf 'log=%s\n' "$MAY_CHU_LOG"
    printf 'url=http://127.0.0.1:%s/admin/\n' "$PORT"
} > "$STATE.tam"
chmod 600 "$STATE.tam" 2>/dev/null || true
mv "$STATE.tam" "$STATE"

# Từ đây script kết thúc BÌNH THƯỜNG: trap không được dừng máy chủ nữa.
DA_SAN_SANG=1

noi "======================================================================"
noi "ĐÃ SẴN SÀNG — UAT LOCAL"
noi "  URL        : http://127.0.0.1:$PORT/admin/"
noi "  PID        : $PID  (đã ghi vào $STATE)"
noi "  Dữ liệu    : $DATA  (thư mục RIÊNG, marker $TEN_DAU_UAT)"
noi "  Tài khoản  : $TAI_KHOAN  (mật khẩu FIXTURE, KHÔNG phải thật)"
noi "  Hãng       : mock — mọi adapter live_mo=False, KHÔNG gọi API hãng"
noi "  Nhật ký    : $MAY_CHU_LOG"
noi "  Dừng       : $THU_MUC_SCRIPT/dung.sh"
noi "======================================================================"
noi "Tài khoản gợi ý: platform-owner · shopa-owner · shopa-staff · shopa-viewer"
noi "                 da-tenant (đổi tenant) · shopb-owner"
noi "Mật khẩu nằm trong: $TAI_KHOAN"
