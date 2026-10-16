#!/bin/sh
# G20 / AG-04 — VỎ CHẠY TAY: đo vòng tròn SAO LƯU → KHÔI PHỤC và in mã thoát THẬT.
#
# Dùng:
#   sh trien_khai/g20-saoluu/chay_do.sh
#   sh trien_khai/g20-saoluu/chay_do.sh --nhanh     # bỏ qua kịch bản PostgreSQL
#
# ====== VÌ SAO PHẢI GHI MÃ THOÁT TRƯỚC MỖI ỐNG DẪN ======
# `lệnh | tee f` trả về mã thoát của `tee`, KHÔNG phải của `lệnh`. Bản vá này giữ mã thoát
# thật trong biến ngay sau lệnh, rồi mới in — xem `docs/QA_G18.md` mục N-01 và N-G18-00.
#
# ====== CHỐT AN TOÀN ======
# Mọi lượt đo chạy trong thư mục TẠM do bộ đo tự dựng. `kich_ban.chot_an_toan()` TỪ CHỐI mọi
# đường nằm trong vùng dữ liệu thật. KHÔNG gọi mạng: lớp HTTP chỉ đi qua stub 127.0.0.1:0.
# Cụm PostgreSQL là cụm RIÊNG, socket Unix, `listen_addresses=''`, và TỪ CHỐI cổng 5432.
set -u

GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 9

NEN=$(mktemp -d "${TMPDIR:-/tmp}/g20-ag04-do.XXXXXX")
don_dep() { rm -rf "$NEN"; }
trap don_dep EXIT INT TERM

NHANH=0
for a in "$@"; do
    [ "$a" = "--nhanh" ] && NHANH=1
done

echo "══════════════════════════════════════════════════════════════════════════"
echo " G20 / AG-04 — VÒNG TRÒN SAO LƯU → KHÔI PHỤC"
echo " Nền tạm : $NEN"
echo " Lúc     : $(date '+%Y-%m-%d %H:%M:%S%z')"
echo "══════════════════════════════════════════════════════════════════════════"

echo ""
echo "── B1. Kiểm cú pháp 3 tệp của AG-04 ──────────────────────────────────────"
python3 -c "
import ast, sys
for t in ('trien_khai/g20-saoluu/khung_do.py', 'trien_khai/g20-saoluu/gieo.py',
          'trien_khai/g20-saoluu/kich_ban.py', 'trien_khai/g20-saoluu/do_vong_tron.py',
          'trien_khai/g20-saoluu/do_postgres.py', 'app/thu/thu_g20_saoluu.py'):
    ast.parse(open(t, encoding='utf-8').read())
    print('  cú pháp OK:', t)
"
MA_B1=$?
echo "  [mã thoát B1] $MA_B1"
[ "$MA_B1" -eq 0 ] || { echo "DỪNG: cú pháp hỏng."; exit "$MA_B1"; }

echo ""
echo "── B2. Chạy 9 kịch bản đo ────────────────────────────────────────────────"
if [ "$NHANH" -eq 1 ]; then
    python3 trien_khai/g20-saoluu/do_vong_tron.py --chi 1 2 3 4 5 6 7 8 \
        --json "$NEN/so-do.json" > "$NEN/do.txt" 2>&1
else
    python3 trien_khai/g20-saoluu/do_vong_tron.py --json "$NEN/so-do.json" \
        > "$NEN/do.txt" 2>&1
fi
MA_B2=$?
echo "  [mã thoát B2] $MA_B2        (mã thoát được lấy TRƯỚC mọi ống dẫn)"
sed -n 's/^/  /p' "$NEN/do.txt"

echo ""
echo "── B3. Bộ thử tự động (lượt hồi quy chung cũng chạy tệp này) ──────────────"
python3 app/thu/thu_g20_saoluu.py > "$NEN/thu.txt" 2>&1
MA_B3=$?
echo "  [mã thoát B3] $MA_B3"
tail -25 "$NEN/thu.txt" | sed -n 's/^/  /p'

echo ""
echo "══════════════════════════════════════════════════════════════════════════"
echo " TỔNG KẾT G20 / AG-04"
echo "   B1 cú pháp            : mã thoát $MA_B1"
echo "   B2 9 kịch bản đo      : mã thoát $MA_B2"
echo "   B3 bộ thử tự động     : mã thoát $MA_B3"
echo ""
echo "   B2 = 0 nghĩa là MỌI KỊCH BẢN ĐO CHẠY ĐƯỢC (kể cả các vế đối chứng đường),"
echo "   KHÔNG có nghĩa sản phẩm không có khuyết điểm. Phán nằm ở"
echo "   docs/G20_BACKUP_RESTORE.md."
echo "══════════════════════════════════════════════════════════════════════════"

# Mã thoát tổng: hỏng nếu BẤT KỲ bước nào hỏng. Giữ đơn giản và ồn ào.
[ "$MA_B1" -eq 0 ] || exit "$MA_B1"
[ "$MA_B2" -eq 0 ] || exit "$MA_B2"
exit "$MA_B3"
