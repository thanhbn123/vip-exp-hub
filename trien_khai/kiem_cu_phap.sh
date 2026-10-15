#!/bin/sh
# Cổng CÚ PHÁP — chốt chặn 1 trong bốn chốt bắt buộc của CLAUDE.md §18.2.
# AG-05 DEVOPS sở hữu file này. Dùng: sh trien_khai/kiem_cu_phap.sh
#
# PHẠM VI (§12.1 luật 3 — kết luận chỉ được nói trong đúng phạm vi đã đo):
#   ĐO:    cú pháp mọi `.py` trong `app/` bằng `py_compile`; cú pháp mọi `.sh` trong
#          `trien_khai/` bằng `sh -n`; `.js` trong `admin/` bằng `node --check` NẾU có node;
#          YAML của compose bằng bộ đọc tối giản (dự án không có PyYAML).
#   KHÔNG ĐO: hành vi lúc chạy, cú pháp Dockerfile (cần Docker — KHÔNG CÓ trên máy dựng),
#          ngữ nghĩa YAML của Docker Compose (cần `docker compose config`), và tính đúng của
#          chính mã. Cú pháp đạt KHÔNG nghĩa là mã đúng.
set -eu
GOC=$(cd "$(dirname "$0")/.." && pwd)
cd "$GOC"
loi=0

echo "== 1. Python (py_compile) =="
n=0
for f in $(find app -name '*.py' | sort); do
    if python3 -m py_compile "$f" 2>/tmp/pyc.$$; then n=$((n+1)); else
        echo "  HONG: $f"; cat /tmp/pyc.$$; loi=1
    fi
done
rm -f /tmp/pyc.$$
echo "  $n file .py cu phap dat"

echo "== 2. Shell (sh -n) =="
n=0
for f in $(find trien_khai -name '*.sh' | sort) app/thu/chay_e2e.sh; do
    [ -f "$f" ] || continue
    if sh -n "$f" 2>/tmp/shn.$$; then n=$((n+1)); else
        echo "  HONG: $f"; cat /tmp/shn.$$; loi=1
    fi
done
rm -f /tmp/shn.$$
echo "  $n file .sh cu phap dat"

echo "== 3. JavaScript (node --check) =="
if command -v node >/dev/null 2>&1; then
    n=0
    for f in admin/*.js assets/js/*.js; do
        [ -f "$f" ] || continue
        if node --check "$f" 2>/tmp/nc.$$; then n=$((n+1)); else
            echo "  HONG: $f"; cat /tmp/nc.$$; loi=1
        fi
    done
    rm -f /tmp/nc.$$
    echo "  $n file .js cu phap dat (node $(node --version))"
else
    echo "  BO QUA: khong co node — KHONG PHAI da dat"
fi

echo "== 4. Cau hinh trien khai (kiem_cau_hinh.py) =="
python3 trien_khai/kiem_cau_hinh.py || loi=1

echo "== 5. Dockerfile / compose =="
if command -v docker >/dev/null 2>&1; then
    docker build --check . 2>/dev/null || echo "  (docker build --check khong dung duoc o ban nay)"
    docker compose config -q && echo "  compose config dat" || loi=1
else
    echo "  BLOCKED: khong co docker tren may nay — cu phap Dockerfile/compose CHUA DO."
    echo "  Day KHONG PHAI 'dat'. Xem docs/G11_FINAL_REPORT.md, dong 'Docker build'."
fi

[ "$loi" -eq 0 ] && echo "== KET LUAN: cu phap DAT trong pham vi da neu o dau file ==" \
                 || echo "== KET LUAN: CO LOI CU PHAP =="
exit "$loi"
