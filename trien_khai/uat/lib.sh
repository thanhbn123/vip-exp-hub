#!/bin/bash
# ============================================================================
# VIP Express Hub — THƯ VIỆN DÙNG CHUNG CHO UAT LOCAL
# ----------------------------------------------------------------------------
# File này CHỈ định nghĩa hàm và hằng. Source nó KHÔNG chạy gì cả.
#
# Ba bất biến của cả bộ script UAT:
#   1. Dữ liệu UAT là thư mục RIÊNG (mặc định ~/veh-uat), TUYỆT ĐỐI không phải
#      thư mục dữ liệu mặc định của sản phẩm (app/du-lieu) hay volume /du-lieu.
#   2. Mọi thứ nghe trên 127.0.0.1, cổng do OS cấp. Không mở ra ngoài.
#   3. Dừng bằng ĐÚNG PID đã ghi + kiểm thân phận tiến trình. KHÔNG dùng
#      lệnh diệt theo mẫu tên tiến trình — kiểu đó đã từng giết tiến trình của người khác.
#
# Vì sao phần kiểm tra nằm ở đây chứ không rải trong từng script: ba script
# (khởi động / dừng / xoá) phải cùng một luật. Hai bản sao của một luật an toàn
# là hai bản sẽ lệch nhau, và bản lệch thường là bản không ai đọc lại.
# ============================================================================

GOC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
DATA_MAC_DINH="${HOME}/veh-uat"
TEN_DAU_UAT=".veh-uat-fixture.json"
LOAI_DAU_UAT="VEH-UAT-FIXTURE"

noi() { printf '[uat] %s\n' "$*"; }
canh_bao() { printf '[uat] CẢNH BÁO: %s\n' "$*" >&2; }
loi() { printf '[uat] LỖI: %s\n' "$*" >&2; }
dung_loi() { loi "$*"; exit 1; }


# ---------------------------------------------------------------------------
# Đường dẫn
# ---------------------------------------------------------------------------
# macOS không có `realpath` mặc định và `readlink -f` cũng không có. Dùng Python
# (thứ sản phẩm đã bắt buộc phải có) để chuẩn hoá: expanduser + realpath.
chuan_hoa_duong() {
    python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$1"
}

# Kiểm tra một đường dẫn có được phép làm thư mục dữ liệu UAT hay không.
# Kết quả: đặt DATA, MARKER. TỪ CHỐI (exit 1) nếu trỏ vào dữ liệu thật.
kiem_tra_vi_tri_du_lieu() {
    local raw="${1:-}" repo_real home_real p
    [ -n "$raw" ] || dung_loi "chưa có đường dẫn thư mục dữ liệu UAT"

    DATA="$(chuan_hoa_duong "$raw")" || dung_loi "không chuẩn hoá được đường dẫn: $raw"
    MARKER="$DATA/$TEN_DAU_UAT"
    repo_real="$(chuan_hoa_duong "$GOC")"
    home_real="$(chuan_hoa_duong "$HOME")"

    [ "$DATA" != "/" ] || dung_loi "TỪ CHỐI: không được dùng gốc hệ thống '/' làm dữ liệu UAT"
    [ "$DATA" != "$home_real" ] || dung_loi "TỪ CHỐI: không được dùng thẳng thư mục nhà '$HOME'"
    [ "$DATA" != "$repo_real" ] || dung_loi "TỪ CHỐI: không được dùng gốc repo làm dữ liệu UAT"

    case "$DATA" in
        "$repo_real"/*)
            dung_loi "TỪ CHỐI: '$DATA' nằm trong CÂY REPO — đó có thể là dữ liệu thật.
          Chọn thư mục ngoài repo, ví dụ: $DATA_MAC_DINH" ;;
    esac
    case "$DATA" in
        /du-lieu|/du-lieu/*)
            dung_loi "TỪ CHỐI: '$DATA' là volume triển khai /du-lieu — đó là DỮ LIỆU THẬT." ;;
    esac
    # Bắt mọi thư mục tên `du-lieu` (app/du-lieu, gateway/du-lieu, ...), kể cả
    # khi repo đã được chép sang chỗ khác và không còn dấu .git.
    if [ "$(basename "$DATA")" = "du-lieu" ]; then
        dung_loi "TỪ CHỐI: '$DATA' có tên 'du-lieu' — đây là quy ước thư mục dữ liệu
          của sản phẩm, không phải nền UAT. Dùng một thư mục riêng, ví dụ $DATA_MAC_DINH."
    fi
    if [ -f "$DATA/app/server.py" ]; then
        dung_loi "TỪ CHỐI: '$DATA' trông như một bản mã nguồn sản phẩm (có app/server.py)."
    fi

    # KHÔNG nằm trong BẤT KỲ cây git nào. Luật này bắt cả repo chính lẫn worktree
    # và mọi thư mục con của chúng — kể cả khi worktree hiện tại chỉ là một phần
    # của repo lớn hơn.
    p="$DATA"
    while [ -n "$p" ] && [ "$p" != "/" ]; do
        if [ -e "$p/.git" ]; then
            dung_loi "TỪ CHỐI: '$DATA' nằm trong cây git ($p/.git).
          Dữ liệu UAT phải nằm NGOÀI mọi repo, ví dụ: $DATA_MAC_DINH"
        fi
        p="$(dirname "$p")"
    done
    return 0
}

# Đọc dấu UAT đã tạo. Trả 0 nếu đúng dấu + đúng dự án, 1 nếu không.
la_dau_uat_hop_le() {
    [ -f "$MARKER" ] || return 1
    python3 - "$MARKER" "$GOC" <<'PY'
import json, os, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    sys.exit(1)
if d.get("loai") != "VEH-UAT-FIXTURE":
    sys.exit(1)
try:
    du_an = os.path.realpath(str(d.get("du_an") or ""))
    goc = os.path.realpath(sys.argv[2])
except Exception:
    sys.exit(1)
sys.exit(0 if du_an == goc else 1)
PY
}

# Kiểm tra thư mục đã tồn tại (nếu có) có phải do bộ script này tạo hay không.
# Đây là chốt "TỪ CHỐI nếu trỏ vào dữ liệu thật" ở tầng thư mục: một thư mục
# KHÔNG rỗng mà không có dấu UAT thì có thể là dữ liệu thật của ai đó.
kiem_tra_thu_muc_uat() {
    if [ -L "$DATA" ]; then
        dung_loi "TỪ CHỐI: '$DATA' là symlink. Dùng đường dẫn thật, không dùng symlink."
    fi
    if [ -e "$DATA" ] && [ ! -d "$DATA" ]; then
        dung_loi "TỪ CHỐI: '$DATA' tồn tại nhưng không phải thư mục."
    fi
    if [ -d "$DATA" ]; then
        if [ -f "$MARKER" ]; then
            la_dau_uat_hop_le || dung_loi "TỪ CHỐI: '$DATA' có file dấu UAT nhưng nội dung không hợp lệ
          hoặc thuộc dự án khác. KHÔNG ghi tiếp vào thư mục này."
        else
            if [ -n "$(ls -A "$DATA" 2>/dev/null || true)" ]; then
                dung_loi "TỪ CHỐI: '$DATA' đã có dữ liệu nhưng KHÔNG có dấu UAT ($TEN_DAU_UAT).
          Đây có thể là dữ liệu thật. KHÔNG ghi đè.
          Chọn thư mục mới (ví dụ $DATA_MAC_DINH) hoặc xoá thư mục đó bằng tay sau khi
          đã chắc chắn nó không phải dữ liệu thật."
            fi
        fi
    fi
}

# Tạo thư mục + dấu UAT (chỉ sau khi kiem_tra_thu_muc_uat đã qua).
tao_thu_muc_uat() {
    mkdir -p "$DATA" || dung_loi "không tạo được thư mục $DATA"
    chmod 700 "$DATA" 2>/dev/null || true
    if [ ! -f "$MARKER" ]; then
        python3 - "$MARKER" "$GOC" <<'PY'
import json, os, sys
from datetime import datetime
marker, goc = sys.argv[1], os.path.realpath(sys.argv[2])
d = {
    "loai": "VEH-UAT-FIXTURE",
    "ghi_chu": ("Dữ liệu UAT local. Mọi tài khoản, khách hàng và đơn hàng là FIXTURE — "
                "KHÔNG phải dữ liệu thật. Không dùng cho production."),
    "du_an": goc,
    "tao_luc": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
    "khong_dung_cho_production": True,
}
tam = marker + ".tam-%d" % os.getpid()
with open(tam, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
    f.write("\n")
os.chmod(tam, 0o600)
os.replace(tam, marker)
PY
        [ -f "$MARKER" ] || dung_loi "không ghi được dấu UAT $MARKER"
    fi
    [ -d "$DATA" ] || dung_loi "không có thư mục dữ liệu $DATA"
    chmod 700 "$DATA" 2>/dev/null || true
}

# Các biến môi trường nguy hiểm: từ chối thay vì âm thầm đổi ý người vận hành.
kiem_tra_moi_truong_an_toan() {
    if [ -n "${VIP_HUB_DATA:-}" ]; then
        local hd
        hd="$(chuan_hoa_duong "$VIP_HUB_DATA")" || \
            dung_loi "không chuẩn hoá được VIP_HUB_DATA=$VIP_HUB_DATA"
        if [ "$hd" != "$DATA" ]; then
            dung_loi "TỪ CHỐI: VIP_HUB_DATA đang trỏ tới '$hd', khác thư mục UAT '$DATA'.
          Script không tự đổi biến môi trường của bạn — làm vậy sẽ che mất việc bạn
          đang trỏ vào dữ liệu thật. Hãy chạy: unset VIP_HUB_DATA
          rồi chạy lại (hoặc đặt VIP_HUB_DATA đúng bằng thư mục UAT)."
        fi
    fi
    if [ -n "${VIP_HUB_BIND:-}" ]; then
        case "${VIP_HUB_BIND}" in
            127.0.0.1|localhost|::1) ;;
            *) dung_loi "TỪ CHỐI: VIP_HUB_BIND=${VIP_HUB_BIND} — UAT local CHỈ nghe 127.0.0.1.
          Hãy unset VIP_HUB_BIND rồi chạy lại." ;;
        esac
    fi
    if [ -n "${VIP_JT_MOI_TRUONG:-}" ]; then
        case "$(printf '%s' "$VIP_JT_MOI_TRUONG" | tr '[:upper:]' '[:lower:]')" in
            mock) ;;
            *) dung_loi "TỪ CHỐI: VIP_JT_MOI_TRUONG=${VIP_JT_MOI_TRUONG} — UAT local chỉ cho phép mock.
          KHÔNG gọi API hãng, kể cả sandbox. Hãy unset VIP_JT_MOI_TRUONG rồi chạy lại." ;;
        esac
    fi
    if [ "${VIP_HUB_RESET_TOKEN:-0}" = "1" ]; then
        dung_loi "TỪ CHỐI: VIP_HUB_RESET_TOKEN=1 là lỗ hổng chiếm tài khoản, chỉ dành cho bộ thử.
          UAT local không cần cờ này. Hãy unset VIP_HUB_RESET_TOKEN rồi chạy lại."
    fi
}


# ---------------------------------------------------------------------------
# Trạng thái chạy + tiến trình
# ---------------------------------------------------------------------------
# File trạng thái dạng dòng `khoá=giá_trị`. Không `source` nó: nội dung file
# không được phép trở thành mã chạy.
lay_state() {
    local dong
    dong="$(grep -m1 "^$1=" "$2" 2>/dev/null || true)"
    printf '%s' "${dong#*=}"
}

la_pid_so() {
    case "${1:-}" in
        ''|*[!0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

tien_trinh_con_song() {
    la_pid_so "${1:-}" && kill -0 "$1" 2>/dev/null
}

lenh_tien_trinh() {
    ps -ww -p "${1:-0}" -o command= 2>/dev/null || true
}

chu_tien_trinh() {
    ps -p "${1:-0}" -o user= 2>/dev/null | tr -d '[:space:]' || true
}

luc_bat_dau_tien_trinh() {
    ps -p "${1:-0}" -o lstart= 2>/dev/null \
        | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true
}

ps_dung_duoc() {
    ps -p "$$" -o pid= >/dev/null 2>&1
}

# PID mà máy chủ UAT tự báo qua /api/v2/suc-khoe. Đây là phép xác thực KHÔNG
# phụ thuộc `ps`: nếu health trả pid đúng bằng PID đã ghi thì tiến trình đang
# nghe cổng đúng là tiến trình mình đã khởi động. In PID ra stdout; exit 1 nếu
# không gọi được health hoặc JSON không có pid.
pid_tu_health() {
    python3 - "${1:-0}" <<'PY'
import json
import sys
import urllib.request

try:
    port = int(sys.argv[1])
    with urllib.request.urlopen("http://127.0.0.1:%d/api/v2/suc-khoe" % port,
                                timeout=2) as r:
        d = json.loads(r.read().decode("utf-8"))
    pid = d.get("pid")
except Exception:
    sys.exit(1)
if not isinstance(pid, int):
    sys.exit(1)
print(pid)
sys.exit(0)
PY
}

la_lenh_may_chu_uat() {
    case "${1:-}" in
        *"$GOC/app/server.py"*) return 0 ;;
        *) return 1 ;;
    esac
}

# Kiểm tra cổng TCP loopback có còn ai nghe. Trả 0 nếu KHÔNG kết nối được.
cong_loopback_da_dong() {
    python3 - "${1:-0}" <<'PY'
import socket, sys
try:
    port = int(sys.argv[1])
except ValueError:
    sys.exit(2)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(0.6)
try:
    s.connect(("127.0.0.1", port))
except OSError:
    sys.exit(0)          # không kết nối được = cổng đã đóng
finally:
    s.close()
sys.exit(1)              # vẫn kết nối được = còn tiến trình nghe
PY
}
