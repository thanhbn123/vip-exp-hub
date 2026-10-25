#!/bin/sh
# Sao lưu DB + (tuỳ chọn) gói khoá mã hoá của VIP Express Hub trên VPS.
# KHÔNG đặt passphrase vào cron. Chạy tay khi cần gói khoá; cron chỉ sao lưu DB.
#
# Bản AG-06 vá bốn lỗi thật của bản cũ:
#   1. bản cũ chọn "tệp .db mới nhất" bằng `ls -t` — nếu `sao_luu()` không tạo tệp mới mà vẫn
#      trả 0, nó có thể chép một bản CŨ và báo thành công. Bây giờ lấy ĐÚNG đường dẫn do
#      `migrate.sao_luu()` trả về và đòi tệp mới hơn mốc bắt đầu.
#   2. bản cũ không kiểm dấu kiểm do app ghi cho bản nguồn, và không kiểm cấu trúc SQLite của
#      bản đã chép. Bây giờ kiểm cả hai TRƯỚC khi coi là xong.
#   3. passphrase gói khoá từng đi qua `-e VAR=...` (lộ trong `ps`/môi trường tiến trình).
#      Bây giờ đi qua stdin, không vào argv hay env của container.
#   4. không có khoá chống hai lượt backup chạy chồng; thêm `flock` và tên thư mục duy nhất.
set -eu

GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
# Thư mục compose là THƯ MỤC CHỨA CHÍNH TỆP NÀY, không phải một đường cố định. Bản cũ ghim
# `$GOC/src/trien_khai/vps`; khi checkout trên VPS đổi từ `src/` sang `app/` (clone từ GitHub,
# 2026-10-20) thì đường đó không còn tồn tại và script chết ngay dòng kiểm compose. Đó là cách
# cron sao lưu đứng im nhiều ngày mà không ai thấy. Tự định vị thì không còn chỗ để lệch.
COMPOSE_DIR="${VIP_HUB_COMPOSE_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
TEN="${VIP_HUB_CONTAINER:-vip-express-hub}"
TS="$(date +%Y%m%d-%H%M%S)"
MARK=""

[ -f "$COMPOSE" ] || { echo "[backup] thiếu compose: $COMPOSE" >&2; exit 2; }
[ -d "$GOC/data" ] || { echo "[backup] thiếu data dir: $GOC/data" >&2; exit 2; }
[ -d "$GOC/backups" ] || { echo "[backup] thiếu backups dir: $GOC/backups (chạy chuan_bi.sh)" >&2; exit 2; }
command -v python3 >/dev/null || { echo "[backup] thiếu python3 trên host để kiểm CSDL" >&2; exit 2; }
command -v sha256sum >/dev/null || { echo "[backup] thiếu sha256sum" >&2; exit 2; }

# Chống chạy chồng (cron + tay). `flock` có sẵn trên Ubuntu; thiếu thì chỉ cảnh báo.
if command -v flock >/dev/null 2>&1; then
  exec 9>"$GOC/backups/.lock"
  flock -n 9 || { echo "[backup] đang có lượt backup khác giữ khoá — bỏ lượt này" >&2; exit 5; }
fi

# Dùng `docker exec` theo container_name cố định thay vì `docker compose exec`: backup chỉ cần
# tiến trình đang chạy, không cần metadata project Compose. Đo được lượt AG-06: một container
# chạy đúng image nhưng thiếu label Compose khiến `docker compose ps/exec` không thấy, trong khi
# `docker inspect` + `docker exec` vẫn đúng. Tên đổi được qua VIP_HUB_CONTAINER nếu cần.
[ "$(docker inspect -f '{{.State.Running}}' "$TEN" 2>/dev/null || echo false)" = "true" ] \
  || { echo "[backup] container $TEN KHÔNG chạy — không sao lưu online" >&2; exit 2; }

DICH="$(mktemp -d "$GOC/backups/${TS}-XXXXXX")"
chmod 700 "$GOC/backups" "$DICH"
LOG="$DICH/sao-luu.log"
: > "$LOG"
chmod 600 "$LOG"
MARK="$DICH/.bat-dau"
: > "$MARK"

echo "[backup] $TS — sao lưu SQLite qua API backup của app"
DUONG_CONTAINER="$(docker exec -i -e VIP_KHO_DANG_CHAY=sqlite "$TEN" \
  python3 -c 'import sys; sys.path.insert(0,"/app/app"); import migrate; print(migrate.sao_luu())' \
  2>>"$LOG")" || { echo "[backup] migrate.sao_luu() THẤT BẠI — xem $LOG" >&2; exit 3; }

[ -n "$DUONG_CONTAINER" ] || { echo "[backup] sao_luu() không trả đường dẫn" >&2; exit 3; }
# `sao_luu()` chạy TRONG container nên trả /du-lieu/...; script chạy trên HOST. Chỉ nhận đúng
# tiền tố đó rồi ghép basename vào bind mount host — không dùng nguyên đường dẫn container.
case "$DUONG_CONTAINER" in
  /du-lieu/sao-luu/*) : ;;
  *) echo "[backup] đường dẫn lạ từ sao_luu(): $DUONG_CONTAINER" >&2; exit 3 ;;
esac
DUONG="$GOC/data/sao-luu/$(basename "$DUONG_CONTAINER")"
[ -f "$DUONG" ] || { echo "[backup] không thấy bản vừa tạo trên host: $DUONG" >&2; exit 3; }
[ "$DUONG" -nt "$MARK" ] || {
  echo "[backup] bản 'mới' KHÔNG mới hơn mốc bắt đầu ($DUONG) — từ chối chép bản cũ" >&2
  exit 3
}

# Dấu kiểm của app cho bản NGUỒN: bắt được tệp bị sửa sau khi app ghi xong.
( cd "$(dirname "$DUONG")" && sha256sum -c "$(basename "$DUONG").sha256" ) >> "$LOG" 2>&1 || {
  echo "[backup] dấu kiểm NGUỒN của app KHÔNG khớp — không dùng bản này" >&2; exit 4; }

cp -p "$DUONG" "$DICH/hub.db"
chmod 600 "$DICH/hub.db"

# Kiểm cấu trúc bản ĐÃ CHÉP bằng python3 trên host, không tin riêng `cp` exit 0.
if ! python3 - "$DICH/hub.db" >> "$LOG" 2>&1 <<'PY'
import sqlite3
import sys

duong = sys.argv[1]
kn = sqlite3.connect("file:%s?mode=ro&immutable=1" % duong, uri=True)
try:
    nguyen = kn.execute("PRAGMA integrity_check").fetchone()[0]
    so_bang = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    print("[backup] integrity_check=%r so_bang=%d" % (nguyen, so_bang))
finally:
    kn.close()
raise SystemExit(0 if nguyen == "ok" and so_bang > 0 else 1)
PY
then
  echo "[backup] bản chép KHÔNG đạt integrity_check / không có bảng" >&2; exit 4
fi

# Dấu kiểm THEO TÊN ĐÍCH hub.db (không chép .sha256 của tên gốc — nó ghi tên khác).
( cd "$DICH" && sha256sum hub.db > hub.db.sha256 && sha256sum -c hub.db.sha256 ) \
  >> "$LOG" 2>&1 || {
  echo "[backup] dấu kiểm hub.db KHÔNG khớp" >&2; exit 4; }

# Gói khoá: CHỈ khi operator chủ động đặt passphrase trong shell của lượt chạy.
if [ -n "${VIP_HUB_BACKUP_PASSPHRASE:-}" ]; then
  echo "[backup] tạo gói khoá .vipkb (passphrase qua stdin, không in, không vào env container)"
  KHOA_TS="$TS-$$"
  printf '%s\n' "$VIP_HUB_BACKUP_PASSPHRASE" | \
    docker exec -i -e "VIP_HUB_BACKUP_TS=$KHOA_TS" "$TEN" \
      python3 -c '
import os
import sys
sys.path.insert(0, "/app/app")
import sao_luu_khoa
passphrase = sys.stdin.readline().rstrip("\r\n")
duong = "/du-lieu/sao-luu/khoa-%s.vipkb" % os.environ["VIP_HUB_BACKUP_TS"]
print(sao_luu_khoa.tao_goi(duong, passphrase=passphrase)["duong"])
' > "$DICH/khoa-duong.log" 2>>"$LOG" || {
        echo "[backup] tạo gói khoá THẤT BẠI — xem $LOG" >&2; exit 5; }
  DUONG_KHOA_CONTAINER="$(cat "$DICH/khoa-duong.log")"
  case "$DUONG_KHOA_CONTAINER" in
    /du-lieu/sao-luu/*.vipkb) : ;;
    *) echo "[backup] đường dẫn gói khoá bất thường: $DUONG_KHOA_CONTAINER" >&2; exit 5 ;;
  esac
  DUONG_KHOA="$GOC/data/sao-luu/$(basename "$DUONG_KHOA_CONTAINER")"
  [ -f "$DUONG_KHOA" ] || { echo "[backup] không thấy gói khoá trên host: $DUONG_KHOA" >&2; exit 5; }
  cp -p "$DUONG_KHOA" "$DICH/khoa.vipkb"
  chmod 600 "$DICH/khoa.vipkb"
else
  echo "[backup] BỎ QUA gói khoá: chưa đặt VIP_HUB_BACKUP_PASSPHRASE." \
       "DB này KHÔNG tự khôi phục được credential nếu mất thư mục data/khoa." >&2
fi

rm -f "$MARK"
chmod 600 "$DICH"/*
# Giữ 14 ngày; không đụng ra ngoài $GOC/backups.
# KHÔNG xoá `data/sao-luu/`: đó là bản lùi của migrate do app quản lý, cần Owner quyết định
# retention riêng — xoá tự động ở đây sẽ làm mất đường lùi của một lượt migrate hỏng.
find "$GOC/backups" -mindepth 1 -maxdepth 1 -type d -mtime +14 -exec rm -rf {} + 2>/dev/null || true
echo "[backup] xong: $DICH"
ls -lh "$DICH"
