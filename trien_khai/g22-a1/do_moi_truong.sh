#!/bin/sh
# AG-03 (G22) — A1 GIT SANDBOX: tái lập lỗi + chạy môi trường đo CÔ LẬP.
#
# Chạy:  sh trien_khai/g22-a1/do_moi_truong.sh
# Ghi log:  sh trien_khai/g22-a1/do_moi_truong.sh > /tmp/a1.log 2>&1; rc=$?; ...
#
# KHÔNG ghi `.git` của worktree chính, KHÔNG sudo, KHÔNG chmod, KHÔNG xoá lock,
# KHÔNG sửa index. Mọi thứ ghi được đều nằm trong `mktemp -d`.
set -u

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd) || exit 1
cd "$ROOT" || exit 1
TMP=$(mktemp -d "${TMPDIR:-/tmp}/g22-a1-script.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT INT TERM

git_sach() { env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 git "$@"; }
bam() {
    if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | awk '{print $1}';
    else sha256sum "$1" | awk '{print $1}'; fi
}

rc_cuoi=0
echo "=============================================================================="
echo " AG-03 (G22) · A1 GIT SANDBOX · môi trường đo write-tree"
echo " Thời điểm: $(date '+%Y-%m-%dT%H:%M:%S%z')"
echo " Worktree : $ROOT"
echo " TMP      : $TMP"
echo "=============================================================================="

echo
echo "== 0. KHẢO SÁT — lệnh THẬT, rc NGAY sau lệnh =="
echo '$ git --version';           git_sach --version;           echo "rc=$?"
echo '$ git rev-parse --git-dir --git-common-dir --show-toplevel'
git_sach rev-parse --git-dir --git-common-dir --show-toplevel; echo "rc=$?"

GD=$(git_sach rev-parse --git-dir)
CD=$(git_sach rev-parse --git-common-dir)
HEAD=$(git_sach rev-parse HEAD)
TREE_HEAD=$(git_sach rev-parse 'HEAD^{tree}')
SO_TEP=$(git_sach ls-files | grep -c . )
IDX="$GD/index"
SHA_TRUOC=$(bam "$IDX")
echo "HEAD=$HEAD"
echo "tree(HEAD)=$TREE_HEAD"
echo "so tep theo doi=$SO_TEP"
echo "index=$IDX"
echo "sha256(index) TRUOC=$SHA_TRUOC"
echo "index.lock TRUOC=$( [ -e "$GD/index.lock" ] && echo CO || echo KHONG )"

echo
echo "== 1. LỆNH BỊ CHẶN — git write-tree TRẦN =="
echo '$ git write-tree'
git_sach write-tree > "$TMP/truc.out" 2> "$TMP/truc.err"
rc_truc=$?
TREE_TRUC=$(cat "$TMP/truc.out")
echo "rc=$rc_truc"
echo "stdout=$(cat "$TMP/truc.out")"
echo "stderr=$(cat "$TMP/truc.err")"
if [ "$rc_truc" -eq 0 ]; then
    echo "→ MÔI TRƯỜNG NÀY GHI ĐƯỢC .git: đo trực tiếp được (tree=$TREE_TRUC)"
    [ "$TREE_TRUC" = "$TREE_HEAD" ] || { echo "VI PHẠM: tree trực tiếp != tree(HEAD)"; rc_cuoi=1; }
elif [ "$rc_truc" -eq 128 ] \
     && grep -q 'index.lock' "$TMP/truc.err" \
     && grep -q 'Operation not permitted' "$TMP/truc.err"; then
    echo "→ BỊ CHẶN đúng như báo cáo: index.lock / Operation not permitted (LỖI MÔI TRƯỜNG ĐO)"
else
    echo "→ MÃ THOÁT LẠ — không kết luận, dừng phần này"
    rc_cuoi=1
fi

SHA_SAU=$(bam "$IDX")
echo "sha256(index) SAU  =$SHA_SAU"
echo "index.lock SAU    =$( [ -e "$GD/index.lock" ] && echo CO || echo KHONG )"
[ "$SHA_SAU" = "$SHA_TRUOC" ] || { echo "VI PHẠM: index THẬT bị đổi"; rc_cuoi=1; }
[ ! -e "$GD/index.lock" ] || { echo "VI PHẠM: còn index.lock — KHÔNG xoá, báo Controller"; rc_cuoi=1; }

echo
echo "== 2. PHƯƠNG ÁN A — index TẠM + ODB TẠM + alternates CHỈ ĐỌC =="
mkdir -p "$TMP/objects"
cp "$IDX" "$TMP/index"
echo '$ GIT_INDEX_FILE=<tmp>/index GIT_OBJECT_DIRECTORY=<tmp>/objects \'
echo '  GIT_ALTERNATE_OBJECT_DIRECTORIES=<common>/objects git write-tree'
GIT_INDEX_FILE="$TMP/index" \
GIT_OBJECT_DIRECTORY="$TMP/objects" \
GIT_ALTERNATE_OBJECT_DIRECTORIES="$CD/objects" \
    git_sach write-tree > "$TMP/safe.out" 2> "$TMP/safe.err"
rc_safe=$?
TREE_SAFE=$(cat "$TMP/safe.out")
echo "rc=$rc_safe"
echo "stdout=$TREE_SAFE"
echo "stderr=$(cat "$TMP/safe.err")"
echo "tree(HEAD)=$TREE_HEAD · KHOP=$( [ "$TREE_SAFE" = "$TREE_HEAD" ] && echo YES || echo NO )"
[ "$rc_safe" -eq 0 ] || { echo "VI PHẠM: phương án A hỏng"; rc_cuoi=1; }
[ "$TREE_SAFE" = "$TREE_HEAD" ] || { echo "VI PHẠM: cây A != cây HEAD"; rc_cuoi=1; }

SHA_SAU2=$(bam "$IDX")
[ "$SHA_SAU2" = "$SHA_TRUOC" ] || { echo "VI PHẠM: index THẬT bị đổi bởi phương án A"; rc_cuoi=1; }
[ ! -e "$GD/index.lock" ] || { echo "VI PHẠM: phương án A để lại index.lock"; rc_cuoi=1; }
echo "sha256(index) sau A=$SHA_SAU2"

echo
echo "== 3. PHƯƠNG ÁN B — BẢN SAO CÔ LẬP trong TMP =="
echo '$ git clone --shared --no-checkout <worktree> <tmp>/cp'
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    git clone --shared --no-checkout "$ROOT" "$TMP/cp" > "$TMP/clone.out" 2>&1
rc_clone=$?
echo "rc=$rc_clone"
echo '$ git -C <tmp>/cp checkout --detach <HEAD>'
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    git -C "$TMP/cp" checkout --detach "$HEAD" > "$TMP/co.out" 2>&1
rc_co=$?
echo "rc=$rc_co"
echo '$ git -C <tmp>/cp write-tree'
env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    git -C "$TMP/cp" write-tree > "$TMP/clone_wt.out" 2> "$TMP/clone_wt.err"
rc_cwt=$?
TREE_CLONE=$(cat "$TMP/clone_wt.out")
HEAD_CLONE=$(env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
    git -C "$TMP/cp" rev-parse HEAD)
echo "rc=$rc_cwt"
echo "HEAD(clone)=$HEAD_CLONE"
echo "write-tree(clone)=$TREE_CLONE"
echo "tree(HEAD)=$TREE_HEAD · KHOP=$( [ "$TREE_CLONE" = "$TREE_HEAD" ] && echo YES || echo NO )"
[ "$rc_clone" -eq 0 ] || { echo "VI PHẠM: clone hỏng"; rc_cuoi=1; }
[ "$rc_co" -eq 0 ] || { echo "VI PHẠM: checkout hỏng"; rc_cuoi=1; }
[ "$rc_cwt" -eq 0 ] || { echo "VI PHẠM: write-tree trong bản sao hỏng"; rc_cuoi=1; }
[ "$HEAD_CLONE" = "$HEAD" ] || { echo "VI PHẠM: HEAD bản sao != HEAD gốc"; rc_cuoi=1; }
[ "$TREE_CLONE" = "$TREE_HEAD" ] || { echo "VI PHẠM: cây bản sao != cây gốc"; rc_cuoi=1; }

echo
echo "== 4. BỘ ĐO CỦA AG-03 — app/thu/thu_g22_a1.py =="
echo '$ python3 app/thu/thu_g22_a1.py'
python3 app/thu/thu_g22_a1.py
rc_py=$?
echo "rc=$rc_py"
[ "$rc_py" -eq 0 ] || { echo "VI PHẠM: bộ đo AG-03 hỏng"; rc_cuoi=1; }

echo
echo "== 5. KIỂM TRA CUỐI — không dấu vết trên cây chính =="
SHA_CUOI=$(bam "$IDX")
echo "sha256(index) TRUOC=$SHA_TRUOC"
echo "sha256(index) CUOI =$SHA_CUOI"
echo "index.lock CUOI   =$( [ -e "$GD/index.lock" ] && echo CO || echo KHONG )"
echo '$ git status --porcelain -uall'
git_sach status --porcelain -uall
echo "rc=$?"
[ "$SHA_CUOI" = "$SHA_TRUOC" ] || { echo "VI PHẠM: index đổi"; rc_cuoi=1; }
[ ! -e "$GD/index.lock" ] || { echo "VI PHẠM: còn index.lock"; rc_cuoi=1; }

echo "=============================================================================="
echo " KẾT LUẬN ĐO ĐƯỢC"
echo " - write-tree TRẦN: rc=$rc_truc (bị chặn ở index.lock / Operation not permitted)"
echo " - PHƯƠNG ÁN A (index tạm): rc=$rc_safe · tree=$TREE_SAFE"
echo " - PHƯƠNG ÁN B (bản sao)  : rc=$rc_cwt · tree=$TREE_CLONE"
echo " - tree(HEAD)             : $TREE_HEAD"
echo " - Bộ đo AG-03            : rc=$rc_py"
echo " - index THẬT bất biến    : $( [ "$SHA_CUOI" = "$SHA_TRUOC" ] && echo YES || echo NO )"
echo " - index.lock còn lại     : $( [ -e "$GD/index.lock" ] && echo CO || echo KHONG )"
echo " - EXIT CODE THAT = $rc_cuoi"
echo "=============================================================================="
exit "$rc_cuoi"
