#!/bin/sh
# KHÔI PHỤC DB từ một thư mục backup — CHỈ chạy khi Owner đã duyệt và có cửa sổ bảo trì.
# Không tự chạy. Không khôi phục gói khoá ở đây; gói khoá dùng sao_luu_khoa.py khoi-phuc.
#
# Bản AG-06 vá bốn lỗi thật của bản cũ:
#   1. `cp` DB cũ trong khi `hub.db-wal`/`-shm` còn đó: bản "trước phục hồi" có thể THIẾU giao
#      dịch đã commit trong WAL. Bây giờ snapshot cũ bằng API backup của SQLite (có WAL).
#   2. không xoá WAL/SHM của DB cũ trước khi đặt DB mới: SQLite có thể áp WAL cũ lên DB vừa
#      phục hồi. Bây giờ xoá cả hai sau khi đã snapshot.
#   3. chạy `migrate --kiem` SAU khi service đã lên: schema lệch thì service đã nhận lưu lượng.
#      Bây giờ kiểm bằng container một-lần TRƯỚC khi `up`.
#   4. DB hiện tại thiếu (ca phục hồi sự cố) làm `set -e` dừng giữa đường, không rollback. Bây
#      giờ có snapshot best-effort + rollback nếu bất kỳ bước nào hỏng.
set -eu

GOC="${VIP_HUB_VPS_ROOT:-/home/deploy/vip-express-hub}"
# Thư mục compose là THƯ MỤC CHỨA CHÍNH TỆP NÀY, không phải một đường cố định. Bản cũ ghim
# `$GOC/src/trien_khai/vps`; khi checkout trên VPS đổi từ `src/` sang `app/` (clone từ GitHub,
# 2026-10-20) thì đường đó không còn tồn tại và script chết ngay dòng kiểm compose. Đó là cách
# cron sao lưu đứng im nhiều ngày mà không ai thấy. Tự định vị thì không còn chỗ để lệch.
COMPOSE_DIR="${VIP_HUB_COMPOSE_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
COMPOSE="$COMPOSE_DIR/docker-compose.yml"
BACKUP="${1:-}"
TS="$(date +%Y%m%d-%H%M%S)-$$"
OLD="$GOC/data/hub.db.truoc-phuc-hoi-$TS"
DA_STOP=0
DA_THAY=0

[ -n "$BACKUP" ] || { echo "dùng: $0 <thư-mục-backup>" >&2; exit 2; }
[ -f "$BACKUP/hub.db" ] || { echo "thiếu $BACKUP/hub.db" >&2; exit 2; }
[ -f "$BACKUP/hub.db.sha256" ] || { echo "thiếu $BACKUP/hub.db.sha256 — không phục hồi mù" >&2; exit 2; }
[ "${TOI_DONG_Y_PHUC_HOI:-}" = "TOI_DONG_Y_PHUC_HOI" ] || {
  echo "TỪ CHỐI: đặt TOI_DONG_Y_PHUC_HOI=TOI_DONG_Y_PHUC_HOI sau khi Owner duyệt" >&2; exit 3; }
command -v python3 >/dev/null || { echo "thiếu python3 trên host" >&2; exit 2; }
command -v curl >/dev/null || { echo "thiếu curl" >&2; exit 2; }
command -v docker >/dev/null || { echo "thiếu docker" >&2; exit 2; }
[ -d "$GOC/backups" ] || { echo "thiếu $GOC/backups — chạy chuan_bi.sh" >&2; exit 2; }

if command -v flock >/dev/null 2>&1; then
  exec 8>"$GOC/backups/.lock"
  flock -n 8 || { echo "[restore] backup/restore khác đang chạy — bỏ lượt này" >&2; exit 5; }
fi

that_bai() {
  echo "[restore] LỖI: $1" >&2
  if [ "$DA_THAY" = 1 ]; then
    rm -f "$GOC/data/hub.db" "$GOC/data/hub.db-wal" "$GOC/data/hub.db-shm"
    if [ -f "$OLD" ]; then
      cp -p "$OLD" "$GOC/data/hub.db"
      chmod 600 "$GOC/data/hub.db"
      echo "[restore] đã đặt lại bản trước: $OLD" >&2
    else
      echo "[restore] KHÔNG có bản trước để đặt lại (DB cũ vốn không tồn tại)" >&2
    fi
  fi
  if [ "$DA_STOP" = 1 ]; then
    docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" up -d hub >/dev/null 2>&1 \
      || echo "[restore] CẢNH BÁO: không tự bật lại được hub — cần người xem" >&2
  fi
  exit 1
}
trap 'that_bai "bị ngắt" ' INT TERM

# 1. Dấu kiểm + cấu trúc TRƯỚC khi dừng dịch vụ.
( cd "$BACKUP" && sha256sum -c hub.db.sha256 ) || {
  echo "[restore] dấu kiểm hub.db KHÔNG khớp — không dừng dịch vụ" >&2; exit 4; }
if ! python3 - "$BACKUP/hub.db" <<'PY'
import sqlite3
import sys

kn = sqlite3.connect("file:%s?mode=ro&immutable=1" % sys.argv[1], uri=True)
try:
    nguyen = kn.execute("PRAGMA integrity_check").fetchone()[0]
    so_bang = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    print("[restore] integrity_check=%r so_bang=%d" % (nguyen, so_bang))
finally:
    kn.close()
raise SystemExit(0 if nguyen == "ok" and so_bang > 0 else 1)
PY
then
  echo "[restore] bản backup KHÔNG đạt integrity_check / không có bảng" >&2
  exit 4
fi

echo "[restore] dừng hub"
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" stop hub || that_bai "không stop được hub"
DA_STOP=1

# 2. Snapshot DB cũ bằng API backup SQLite — WAL được gộp, không mất giao dịch đã commit.
if [ -f "$GOC/data/hub.db" ]; then
  if ! python3 - "$GOC/data/hub.db" "$OLD" <<'PY'
import sqlite3
import sys

nguon, dich = sys.argv[1], sys.argv[2]
src = sqlite3.connect(nguon, timeout=30)
dst = sqlite3.connect(dich)
try:
    with dst:
        src.backup(dst)
finally:
    dst.close()
    src.close()
PY
  then
    that_bai "không snapshot được DB cũ"
  fi
  chmod 600 "$OLD"
  echo "[restore] bản trước: $OLD"
else
  echo "[restore] CẢNH BÁO: không có hub.db cũ — phục hồi từ backup, không có bản lùi" >&2
fi

# 3. Đặt DB mới và dọn WAL/SHM của DB cũ. Backup của app là ảnh độc lập (SQLite backup API).
DA_THAY=1
rm -f "$GOC/data/hub.db-wal" "$GOC/data/hub.db-shm"
cp -p "$BACKUP/hub.db" "$GOC/data/hub.db" || that_bai "không chép được backup vào data/hub.db"
chmod 600 "$GOC/data/hub.db"

# 4. Kiểm schema bằng container MỘT-LẦN trước khi mở cổng. Lỗi ở đây chưa ảnh hưởng lưu lượng.
if ! docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" run --rm --no-deps -T \
  -e VIP_KHO_DANG_CHAY=sqlite --entrypoint python3 hub /app/app/migrate.py --kiem
then
  that_bai "migrate --kiem KHÔNG đạt trên DB vừa phục hồi"
fi

echo "[restore] khởi động hub"
docker compose -f "$COMPOSE" --project-directory "$COMPOSE_DIR" up -d hub || that_bai "không up được hub"

# 5. Health + readiness. Health chỉ là tiến trình sống; readiness mới bắt thiếu khóa/schema.
i=0
while [ "$i" -lt 60 ]; do
  if curl -fsS --max-time 3 http://127.0.0.1:18897/api/v2/suc-khoe >/dev/null 2>&1; then break; fi
  i=$((i+1)); sleep 2
done
[ "$i" -lt 60 ] || that_bai "health KHÔNG lên sau 120s"
if ! curl -fsS --max-time 5 http://127.0.0.1:18897/api/v2/san-sang >/dev/null 2>&1; then
  that_bai "readiness /san-sang KHÔNG đạt sau khi phục hồi (thiếu khóa? schema? worker?)"
fi

echo "[restore] xong. Bản trước: $OLD"
