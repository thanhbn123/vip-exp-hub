#!/bin/sh
# G21/AG-04 — CHẠY CỔNG ĐỐI CHIẾU ĐỘC LẬP CHO GIỚI HẠN TẦN SUẤT (bộ đo `thu_g21_gioihan.py`).
#
# Vì sao có script này thay vì gọi thẳng tệp: log phải ra một chỗ **KHÔNG nằm trong cây mã
# nguồn**. Ghi log vào trong repo làm cây BẨN, và trên cây này có những cổng "cây sạch"
# (`thu_qa_g17.py::A_Nen`, `thu_qa_g18.py::A_Nen`) sẽ ĐỎ vì một tệp rác — đỏ vì lý do không
# liên quan tới sản phẩm. Nên log đi vào `${TMPDIR}/veh_g21_ag04/`.
#
# BA CHỐT CỦA BỘ ĐO (đọc kỹ ở đầu `app/thu/thu_g21_gioihan.py`):
#   · KHÔNG gọi hãng kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Mọi HTTP chỉ chạm
#     `127.0.0.1` với cổng do hệ điều hành cấp; phần `408` dùng stub J&T CỤC BỘ của dự án.
#   · KHÔNG push / deploy / tunnel; máy chủ đo bind `127.0.0.1` TƯỜNG MINH; `CHO_PHEP_LIVE` vẫn
#     False (A0c ĐO LẠI bằng tiến trình con, không nói suông).
#   · KHÔNG PostgreSQL (D-8): mọi CSDL là SQLite trong thư mục TẠM, `VIP_THU_POSTGRES` bị gỡ,
#     tiến trình con TỰ CHỐI CHẠY (mã 9) nếu CSDL của nó nằm ngoài thư mục tạm.
#
# IN EXIT CODE TRƯỚC MỌI PIPE: mất mã thoát là mất bằng chứng.
set -u
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 2

LOG_DIR="${TMPDIR:-/tmp}/veh_g21_ag04"
mkdir -p "$LOG_DIR" || exit 2
LOG="$LOG_DIR/gioihan.log"

# HEAD là một phần của bằng chứng: bộ đo chạy trên cây nào phải nói được.
# `GIT_CONFIG_*` bị gỡ vì môi trường này có `GIT_CONFIG_COUNT` nhưng THIẾU `GIT_CONFIG_KEY_*`
# (N-G18-00) — giữ nguyên thì `git` thoát 128 và dòng HEAD thành vô nghĩa.
HEAD=$(env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
       git rev-parse HEAD 2>/dev/null)
echo "HEAD = ${HEAD:-<không đọc được>}"
echo "log  = $LOG"
echo

# `-u`: không đệm. Bộ đo chạy ~1,5 phút; đệm thì log đứng im và người vận hành không phân biệt
# được "đang chạy" với "đã treo".
VIP_G21_HEAD="$HEAD" python3 -u app/thu/thu_g21_gioihan.py > "$LOG" 2>&1
MA=$?
echo "EXIT_BO_DO=$MA"

# Bảng bằng chứng in NGUYÊN VĂN từ log: N · tổng lượt qua · trần khai báo · phán quyết.
echo
echo "──────────────── BẢNG N / TỔNG LƯỢT QUA / TRẦN KHAI BÁO ────────────────"
sed -n '/BẢNG N \/ TỔNG LƯỢT QUA/,$p' "$LOG"
echo "──────────────────────────────────────────────────────────────────────"
echo "(nhật ký đầy đủ: $LOG)"
exit "$MA"
