#!/bin/sh
# ENTRYPOINT của container VIP Express Hub (G11). AG-05 DEVOPS sở hữu file này.
#
# ====== VÌ SAO SCRIPT NÀY KHÔNG TỰ CHẠY MIGRATION ======
# Đây là quyết định thiết kế quan trọng nhất của file, nên viết ra chứ không để ai đoán.
# `app/migrate.py` tự backup trước khi nâng, tự kiểm bảo toàn số dòng, và có `--rollback`. Rất
# tốt. Nhưng cho ENTRYPOINT tự gọi nó thì:
#   - Chạy N bản (replica) là N lượt migration ĐUA NHAU trên cùng một CSDL.
#   - Lượt nâng hỏng + `restart: unless-stopped` = vòng lặp nâng-hỏng-nâng-hỏng, mỗi vòng một
#     file backup mới, và không ai còn biết bản backup nào là bản TRƯỚC khi hỏng.
#   - Nâng schema là việc KHÔNG LÙI ĐƯỢC TỰ ĐỘNG. Thứ không lùi được tự động thì phải có người
#     nhìn, đúng tinh thần §18.1 của CLAUDE.md: mã hỏng lên dịch vụ thật lúc 2 giờ sáng thì
#     không ai nhìn.
# Nên: migration là MỘT BƯỚC RIÊNG do người chạy (RUNBOOK mục 4), và script này chỉ KIỂM rồi
# DỪNG SẠCH nếu schema chưa đúng.
#
# `server.chay()` cũng tự `SystemExit(3)` khi CSDL cũ hơn mã. Không nuốt lỗi đó: mã thoát của
# script này là mã thoát của máy chủ.
set -eu

GOC=/app
: "${VIP_HUB_DATA:=/du-lieu}"
: "${VIP_HUB_PORT:=8897}"
export VIP_HUB_DATA VIP_HUB_PORT PYTHONPATH="$GOC/app"

noi() { printf '{"luc":"%s","loai":"khoi_dong","muc":"%s","thong_diep":"%s"}\n' \
        "$(date +%Y-%m-%dT%H:%M:%S%z)" "$1" "$2" >&2; }

# ---- 1. Thư mục dữ liệu phải GHI ĐƯỢC ----
# Không `mkdir -p` rồi coi như xong: trong container, thư mục này là VOLUME do Docker tạo, và
# nếu nó thuộc root trong khi ta chạy bằng `hub` thì `mkdir` thành công mà `ghi` vẫn hỏng.
# Phép đo là GHI THẬT một file rồi xoá.
if [ ! -d "$VIP_HUB_DATA" ]; then
    noi loi "thu muc du lieu $VIP_HUB_DATA khong ton tai"
    exit 4
fi
thu="$VIP_HUB_DATA/.thu-ghi-$$"
if ! (: > "$thu") 2>/dev/null; then
    noi loi "KHONG ghi duoc vao $VIP_HUB_DATA — kiem chown volume (xem RUNBOOK muc 10.2)"
    exit 4
fi
rm -f "$thu"

# ---- 2. Cờ nguy hiểm ----
# Bật `VIP_HUB_RESET_TOKEN=1` là lỗ hổng chiếm tài khoản (AG-07 ca q01b). Nó CHỈ dành cho bộ
# thử. Dừng ngay chứ không chỉ cảnh báo: cảnh báo trong log khởi động là thứ không ai đọc.
if [ "${VIP_HUB_RESET_TOKEN:-0}" = "1" ]; then
    noi loi "VIP_HUB_RESET_TOKEN=1 — lo hong chiem tai khoan. Container TU CHOI chay."
    exit 5
fi

# ---- 3. Schema phải ĐÚNG phiên bản. KHÔNG tự nâng ----
pb=$(python3 - <<'PY'
import sys
sys.path.insert(0, "/app/app")
try:
    import csdl
    print("%d %d" % (csdl.phien_ban_hien_tai(), csdl.PHIEN_BAN_SCHEMA))
except Exception as e:
    print("loi %r" % (e,))
PY
) || { noi loi "khong doc duoc phien ban schema"; exit 6; }

co=$(echo "$pb" | awk '{print $1}')
can=$(echo "$pb" | awk '{print $2}')
if [ "$co" = "loi" ]; then
    noi loi "khong mo duoc CSDL: $pb"
    exit 6
fi
if [ "$co" -lt "$can" ]; then
    noi loi "CSDL o schema v$co, ma can v$can. CHAY MIGRATION TRUOC (RUNBOOK muc 4). Khong tu nang."
    exit 3
fi
noi tin "schema v$co (ma can v$can) — dat"

# ---- 4. Readiness MỘT LƯỢT trước khi mở cổng ----
# Chạy ở đây để lỗi hiện trong log KHỞI ĐỘNG, chứ không hiện ở lượt gọi đầu của người dùng.
# Lưu ý PHẠM VI: lượt này chạy TRƯỚC khi worker webhook khởi động (worker do `server.chay()`
# bật), nên `worker` chắc chắn chưa sống. Bỏ qua nó CÓ CHỦ Ý và `san_sang()` sẽ GHI RA là đã bỏ
# (`ok: None`, không phải `ok: True`) — bỏ qua mà không ghi là đúng kiểu hỏng §12.1.
python3 - <<'PY' >&2 || { noi loi "readiness truoc khoi dong KHONG dat — xem dong JSON ngay tren"; exit 7; }
import json, sys
sys.path.insert(0, "/app/app")
import quan_sat
kq = quan_sat.san_sang(bo_qua=("worker",))
print(json.dumps(kq, ensure_ascii=False))
sys.exit(0 if kq["ok"] else 1)
PY

noi tin "mo cong $VIP_HUB_PORT"
# `exec` để máy chủ thành PID 1: nhận được SIGTERM của `docker stop` và chạy nhánh `finally`
# (dừng worker webhook, `server_close`). Không `exec` thì shell ăn tín hiệu và Docker phải
# SIGKILL sau 10 giây — tức là worker bị cắt giữa một sự kiện webhook đang xử lý.
cd "$GOC"
exec python3 app/server.py "$VIP_HUB_PORT"
