#!/bin/sh
# G22/AG-04 — CHẠY CỔNG "ĐIỂM VƯỚNG TÊN TỆP CỦA C5/G7" (`app/thu/thu_g22_gioihan.py`).
#
# Vì sao có script này thay vì gọi thẳng tệp: log phải ra một chỗ **KHÔNG nằm trong cây mã
# nguồn**. Ghi log vào trong repo làm cây BẨN, và trên cây này có những cổng "cây sạch"
# (`thu_qa_g17.py::A_Nen`, `thu_qa_g18.py::A_Nen`) sẽ ĐỎ vì một tệp rác — đỏ vì lý do không
# liên quan tới sản phẩm. Nên log đi vào `${TMPDIR}/veh_g22_ag04/`.
#
# BỐN CHỐT CỦA CỔNG NÀY (đọc kỹ ở đầu `app/thu/thu_g22_gioihan.py`):
#   · KHÔNG gọi hãng kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Cổng này KHÔNG mở
#     socket nào; nó chỉ đọc tệp và chạy tiến trình con cục bộ.
#   · KHÔNG push / deploy / tunnel; KHÔNG mở `CHO_PHEP_LIVE`.
#   · KHÔNG PostgreSQL (D-8): `VIP_THU_POSTGRES` bị GỠ khỏi môi trường mọi tiến trình con.
#   · Tệp tạm duy nhất được tạo là BẢN SAO của bộ kiểm AG-01 (`app/thu/thu_qa_g20.py`) và BẢN SAO
#     đã tiêm lỗi của bản uỷ quyền — cả hai bị XOÁ / TRẢ LẠI trong `finally` + `atexit`, và cổng
#     tự khẳng định điều đó trước khi kết thúc.
#
# IN EXIT CODE TRƯỚC MỌI PIPE: mất mã thoát là mất bằng chứng.
set -u
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 2

LOG_DIR="${TMPDIR:-/tmp}/veh_g22_ag04"
mkdir -p "$LOG_DIR" || exit 2
LOG="$LOG_DIR/gioihan_g22.log"

# HEAD là một phần của bằng chứng: cổng chạy trên cây nào phải nói được.
# `GIT_CONFIG_*` bị gỡ vì môi trường này có `GIT_CONFIG_COUNT` nhưng THIẾU `GIT_CONFIG_KEY_*`
# (N-G18-00) — giữ nguyên thì `git` thoát 128 và dòng HEAD thành vô nghĩa.
HEAD=$(env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
       git rev-parse HEAD 2>/dev/null)
echo "HEAD = ${HEAD:-<không đọc được>}"
echo "log  = $LOG"
echo

# `-u`: không đệm. Cổng chạy vài phút; đệm thì log đứng im và người vận hành không phân biệt
# được "đang chạy" với "đã treo".
VIP_G22_HEAD="$HEAD" python3 -u app/thu/thu_g22_gioihan.py > "$LOG" 2>&1
MA=$?
echo "EXIT_BO_DO=$MA"

echo
echo "──────────────── BẢNG C5/G7: TỶ LỆ · PHÁN QUYẾT · TIÊM LỖI ────────────────"
sed -n '/B1\./,$p' "$LOG" | grep -E "CHẠY THẬT|B3\.|B2 |CHIỀU|TỔNG:|ca ĐẠT=" || true
echo "──────────────────────────────────────────────────────────────────────────"
echo "(nhật ký đầy đủ: $LOG)"

# Cây phải SẠCH hơn lúc bắt đầu, không được kém hơn: cổng tự kiểm hai tệp nó mượn.
echo
echo "── KIỂM RÁC SAU KHI CHẠY ──"
for f in app/thu/thu_qa_g20.py app/thu/thu_qa_g19_tich_hop.py; do
    if [ -f "$f" ]; then echo "  có   $f"; else echo "  KHÔNG $f"; fi
done
echo "(không tệp tam/GIA nao duoc de lai — cong tu khang dinh trong finally)"
exit "$MA"
