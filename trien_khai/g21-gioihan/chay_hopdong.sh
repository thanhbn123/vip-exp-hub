#!/bin/sh
# G22/AG-04 — CHẠY KHỐI B7 (HỢP ĐỒNG TENANT + PHỦ TUYẾN + PHÂN TRANG) TRÊN **HAI CÂY**.
#
# Vì sao HAI cây: một phép đo chỉ có giá trị khi biết nó ĐỔI MÀU được. Cây nhà (làn AG-04) chưa
# gộp tuyến `/api/v2/don` của AG-02, nên các GHIM HỢP ĐỒNG ở đây PHẢI ĐỎ; cây đối chứng (làn
# AG-02, nơi tuyến đã cắm) PHẢI XANH. Hai cột ấy là đối chứng ÂM/DƯƠNG của chính phép đo — thiếu
# cột nào thì không phân biệt được "hợp đồng bị vi phạm" với "phép đo hỏng".
#
# Bốn chốt của khối B7 (đọc kỹ ở đầu `app/thu/thu_g22_gioihan.py`):
#   · CSDL đo là SQLite trong thư mục TẠM do chính bộ đo dựng; TỪ CHỐI ĐO (mã thoát 9) nếu CSDL
#     mở ra không nằm trong thư mục tạm ⇒ KHÔNG migration CSDL nghiệp vụ (D-8).
#   · CSDL nghiệp vụ chỉ được ĐỌC dấu vân tay (sha256 · mtime · cỡ) trước/sau.
#   · Máy chủ đo bind `127.0.0.1` cổng 0; KHÔNG hãng (kể cả sandbox), KHÔNG push/deploy/tunnel.
#   · Cây đối chứng được đo CHỈ ĐỌC (`PYTHONDONTWRITEBYTECODE=1`) — không rơi `__pycache__`.
#
# IN EXIT CODE TRƯỚC MỌI PIPE: mất mã thoát là mất bằng chứng.
set -u
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC" || exit 2

LOG_DIR="${TMPDIR:-/tmp}/veh_g22_ag04"
mkdir -p "$LOG_DIR" || exit 2
LOG_NHA="$LOG_DIR/hopdong_cay_nha.log"
LOG_DC="$LOG_DIR/hopdong_cay_doi_chung.log"

CAY_NHA="$GOC/app"
# Cây đối chứng: làn AG-02 (nơi `. ` hợp đồng §1 được cắm vào). Đổi bằng biến môi trường khi
# cây gộp thật đã có — KHÔNG sửa tệp này.
CAY_DC="${VIP_G22_CAY_DOI_CHUNG:-$(cd "$GOC/.." && pwd)/g21-ag02-backup/app}"

# HEAD là một phần của bằng chứng: đo trên cây nào phải nói được.
# `GIT_CONFIG_*` bị gỡ vì môi trường này có `GIT_CONFIG_COUNT` nhưng THIẾU `GIT_CONFIG_KEY_*`
# (N-G18-00) — giữ nguyên thì `git` thoát 128 và dòng HEAD thành vô nghĩa.
HEAD=$(env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
       git rev-parse HEAD 2>/dev/null)
echo "HEAD           = ${HEAD:-<không đọc được>}"
echo "cây nhà        = $CAY_NHA"
echo "cây đối chứng  = $CAY_DC"
echo

bang() {   # $1 = tệp log · $2 = mốc mở bảng → in TRỌN khối bảng (từ `┌` tới `└`)
    awk -v moc="$2" 'index($0, moc) { p = 1 } p { print } p && /^  └/ { p = 0 }' "$1"
}

chay_cay() {   # $1 = thư mục app · $2 = tệp log · $3 = nhãn. Đặt mã thoát vào `MA_CUOI`.
    echo "──────── CHẠY $3 ────────"
    echo "  \$ VIP_G22_CAY_APP=$1 python3 -u app/thu/thu_g22_gioihan.py"
    VIP_G22_CAY_APP="$1" python3 -u app/thu/thu_g22_gioihan.py > "$2" 2>&1
    MA_CUOI=$?
    echo "  EXIT_BO_DO_$3=$MA_CUOI"
}

chay_cay "$CAY_NHA" "$LOG_NHA" "CAY_NHA"; MA_NHA=$MA_CUOI
echo
if [ -d "$CAY_DC" ]; then
    chay_cay "$CAY_DC" "$LOG_DC" "CAY_DOI_CHUNG"; MA_DC=$MA_CUOI
else
    echo "──────── CHẠY CAY_DOI_CHUNG ────────"
    echo "  KHÔNG CHẠY ĐƯỢC: $CAY_DC không phải thư mục"
    MA_DC=127
    : > "$LOG_DC"
fi

echo
echo "════════════════ BẢNG BẰNG CHỨNG KHỐI B7 — CÂY NHÀ (AG-04, chưa gộp tuyến) ════════════════"
bang "$LOG_NHA" "BẢNG TENANT A/B"
bang "$LOG_NHA" "BẢNG PHÂN TRANG"
bang "$LOG_NHA" "BẢNG CROSS-TENANT"
bang "$LOG_NHA" "BẢNG PHỦ TUYẾN"
echo "── phán quyết từng ca B7 (cây nhà) ──"
grep -E "^  (✓|✗|!) B7" "$LOG_NHA" || true
grep -E "ca ĐẠT=|TỔNG:" "$LOG_NHA" | tail -2

echo
echo "════════ BẢNG BẰNG CHỨNG KHỐI B7 — CÂY ĐỐI CHỨNG (AG-02, tuyến đã cắm) ════════"
bang "$LOG_DC" "BẢNG TENANT A/B"
bang "$LOG_DC" "BẢNG PHÂN TRANG"
bang "$LOG_DC" "BẢNG CROSS-TENANT"
bang "$LOG_DC" "BẢNG PHỦ TUYẾN"
echo "── phán quyết từng ca B7 (cây đối chứng) ──"
grep -E "^  (✓|✗|!) B7" "$LOG_DC" || true
grep -E "ca ĐẠT=|TỔNG:" "$LOG_DC" | tail -2

echo
echo "════════════════════════════ TỔNG KẾT HAI CÂY ════════════════════════════"
echo "  cây nhà        (AG-04) : EXIT=$MA_NHA   (kỳ vọng: 1 — hợp đồng §1 CHƯA gộp ⇒ ghim ĐỎ + KHUYẾT)"
echo "  cây đối chứng  (AG-02) : EXIT=$MA_DC   (kỳ vọng: 0 — mọi ghim hợp đồng XANH)"
echo "  log: $LOG_NHA"
echo "       $LOG_DC"
echo "══════════════════════════════════════════════════════════════════════════"

# Mã thoát của runner: 0 CHỈ KHI cả hai cây cho ĐÚNG kỳ vọng (nhà đỏ-vì-thiếu-tuyến, đối chứng
# xanh). Một cây đối chứng ĐỎ nghĩa là phép đo sai hoặc hợp đồng bị vi phạm — cả hai đều phải đỏ.
if [ "$MA_NHA" = "1" ] && [ "$MA_DC" = "0" ]; then
    echo "PHÁN QUYẾT RUNNER: ĐẠT — đối chứng ÂM/DƯƠNG phân biệt được hai cây."
    exit 0
fi
echo "PHÁN QUYẾT RUNNER: HỎNG — hai cây KHÔNG cho cặp kết quả mong đợi (nhà=1 · đối chứng=0)."
exit 1
