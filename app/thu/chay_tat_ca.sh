#!/bin/sh
# Chạy TOÀN BỘ bộ thử của dự án và in bảng tổng kết có PHẠM VI.
#
# Vì sao TỰ DÒ file thay vì liệt kê cứng: danh sách viết cứng là chỗ một bộ thử mới bị quên
# IM LẶNG — thêm `thu_abc.py` mà quên thêm vào danh sách thì nó không bao giờ chạy, và không
# có gì báo. Tự dò thì file mới tự vào. Đổi lại, phải canh ngược: nếu số bộ dò được ÍT HƠN
# ngưỡng tối thiểu thì script HỎNG, chứ không lặng lẽ chạy 0 bộ rồi báo đạt (§12.1 luật 5).
set -e
GOC=$(cd "$(dirname "$0")/../.." && pwd)
cd "$GOC"

TOI_THIEU=${VIP_TOI_THIEU_BO:-12}

echo "══════════ BỘ THỬ PYTHON (unittest) ══════════"
TONG=0; SO_BO=0; HONG=""; BO_QUA=""; SO_BO_QUA=0
# `thu_e2e.py` CỐ Ý loại khỏi phép dò: nó cần một máy chủ đang chạy + CSDL cô lập do
# `chay_e2e.sh` dựng, nên chạy một mình là vô nghĩa. Nó vẫn ĐƯỢC CHẠY — ở mục E2E bên dưới,
# qua đúng bộ chạy của nó. Loại ở đây là để không đếm nó hai lần và không báo hỏng giả;
# KHÔNG phải để bỏ qua nó.
for t in $(find app/thu gateway/thu -name 'thu_*.py' -type f ! -name 'thu_e2e.py' | sort); do
    SO_BO=$((SO_BO + 1))
    # VÁ 15/10/2026 (N-01, AG-01 phát hiện — AG-00 chốt): bản cũ là
    #     OUT=$(python3 "$t" 2>&1); MA=$?
    # Dưới `set -e`, phép gán trên MANG mã thoát của `python3`, nên bộ thử hỏng đầu tiên
    # làm CHẾT CẢ SCRIPT ngay tại đây — trước bảng tổng kết, không một dòng báo hỏng.
    # Bản vá ĐẦU của AG-00 (`if ! OUT=...; then MA=$?; fi`) cũng SAI: `!` đảo mã thoát nên
    # `$?` trong `then` luôn là 0 — nó xoá luôn tiêu chí mã thoát và quay về đúng khuôn
    # "phán bằng chữ trong output" đã gây hai lần báo hỏng giả (§7.1 BAN_GIAO).
    # Dạng dưới đây là dạng ĐÚNG: `||` chỉ chạy khi lệnh hỏng, và lúc đó `$?` VẪN là mã thoát
    # của chính lệnh vừa hỏng. Đã đo: mọi bộ đều được chạy, bộ hỏng được báo kèm lý do ĐÚNG.
    MA=0
    OUT=$(python3 "$t" 2>&1) || MA=$?
    # Đếm ca: `Ran N` của unittest, hoặc `N ca — ĐẠT` của bộ thử viết tay.
    N=$(printf '%s' "$OUT" | grep -oE 'Ran [0-9]+' | tail -1 | grep -oE '[0-9]+' || true)
    if [ -z "$N" ]; then
        N=$(printf '%s' "$OUT" | grep -oE '[0-9]+ ca — ĐẠT' | tail -1 | grep -oE '^[0-9]+' || true)
    fi
    N=${N:-0}
    TONG=$((TONG + N))
    # PHÁN BẰNG MÃ THOÁT, không bằng chữ trong output.
    #
    # Trước đây phán bằng `grep '^OK'` — nếp của unittest. Cách đó đã báo HỎNG GIẢ HAI LẦN,
    # cùng một kiểu: lần đầu với thu_http.py (in dòng chẩn đoán sau `OK` nên `tail -3` bỏ sót),
    # lần hai ngày 15/10/2026 với thu_bien_driver.py (không dùng unittest nên không in `OK`
    # bao giờ, dù thoát 0 và 4 ca đều đạt). CLAUDE.md §12.2: một cấu trúc hỏng LẦN THỨ HAI
    # theo cùng một kiểu thì ĐỔI CẤU TRÚC, đừng sửa cho đúng thêm một lần nữa.
    #
    # Và hướng sai NGUY HIỂM hơn nằm ở mặt còn lại: một bộ thử in `OK` ở đâu đó rồi thoát
    # khác 0 sẽ được phán ĐẠT. Hiện chưa bộ nào như vậy (đo 15/10/2026: 27/27 bộ thoát 0,
    # 26 bộ có `OK`, 1 bộ không) — nhưng "hiện chưa" không phải là chốt chặn.
    #
    # Mã thoát một mình vẫn lừa được: một bộ thử bắt hết lỗi rồi thoát 0 mà KHÔNG chạy ca nào
    # cũng đạt. Nên đòi thêm DẤU VẾT ĐÃ CHẠY: đếm được số ca, hoặc có dòng OK/ĐẠT.
    if printf '%s' "$OUT" | grep -qE '^OK( |$)|ca — ĐẠT'; then CO_DAU_VET=1; else CO_DAU_VET=0; fi
    if [ "$MA" -eq 0 ] && [ "$CO_DAU_VET" = 1 ] && [ "$N" -gt 0 ]; then
        printf '  ✓ %-24s %4s ca\n' "$(basename "$t")" "$N"
    elif [ "$MA" -eq 0 ] && [ "$N" -eq 0 ] && printf '%s' "$OUT" | grep -q 'skipped'; then
        # BỎ QUA là phán quyết THỨ BA, không gộp vào ĐẠT.
        # Trước 15/10/2026 chỉ có hai phán quyết, nên thu_postgres.py — bộ tự bỏ qua trừ khi
        # bật VIP_THU_POSTGRES=1 — hiện dấu ✓ trong MỌI báo cáo dù chạy KHÔNG MỘT CA NÀO.
        # Người đọc "27 bộ ĐẠT" tin là PostgreSQL đã được phủ; thật ra chưa đo gì.
        # §12.1 luật 3: kết luận chỉ được nói trong đúng phạm vi đã đo.
        LY=$(printf '%s' "$OUT" | grep -oE 'Bật bằng: [A-Z_]+=[0-9]+' | head -1 || true)
        printf '  ⊘ %-24s    BỎ QUA  %s\n' "$(basename "$t")" "${LY:-không nêu cách bật}"
        SO_BO_QUA=$((SO_BO_QUA + 1)); BO_QUA="$BO_QUA $(basename "$t")"
    else
        LY_DO="mã thoát $MA"
        if [ "$MA" -eq 0 ] && [ "$CO_DAU_VET" = 0 ]; then
            LY_DO="thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào"
        elif [ "$MA" -eq 0 ] && [ "$N" -eq 0 ]; then
            LY_DO="thoát 0 nhưng đếm được 0 ca"
        fi
        printf '  ✗ %-24s %4s ca  HỎNG (%s)\n' "$(basename "$t")" "$N" "$LY_DO"
        HONG="$HONG $(basename "$t")"
        printf '%s' "$OUT" | grep -E '^(FAIL|ERROR):' | head -8 | sed 's/^/        /'
    fi
done

if [ "$SO_BO" -lt "$TOI_THIEU" ]; then
    echo
    echo "HỎNG: chỉ dò được $SO_BO bộ thử, ngưỡng tối thiểu là $TOI_THIEU."
    echo "Phép dò đang nhìn sai chỗ — KHÔNG được coi là đã chạy hết."
    exit 2
fi

echo
echo "══════════ FRONTEND ══════════"
FE_L=0; FE_H=0
if command -v node >/dev/null 2>&1; then
    if [ -f thu_frontend/thu_logic.mjs ]; then
        # node in dạng `ℹ pass 56` (có ký tự ℹ ở đầu), KHÔNG phải `# pass 56`.
        FE_L=$(node --test thu_frontend/thu_logic.mjs 2>&1 | grep -oE 'pass [0-9]+' | head -1 | grep -oE '[0-9]+' || echo 0)
        FE_L=${FE_L:-0}
        printf '  tầng 1 (logic thuần, node):  %4s ca\n' "$FE_L"
    fi
else
    echo "  tầng 1: BỎ QUA — không có node trên máy này"
fi
if [ -f thu_frontend/thu_http.py ]; then
    # L2-N1 (AG-01 phát hiện, AG-00 vá): chỗ này từng là `... || true` rồi phán bằng
    # `grep -qE '^OK'` — tức VỨT mã thoát rồi đoán bằng CHỮ TRONG OUTPUT, đúng cái khuôn mà
    # dòng 40 của chính tệp này tuyên bố đã từ bỏ. Nay phán bằng MÃ THOÁT + DẤU VẾT ĐÃ CHẠY
    # (số ca > 0), cùng luật với vòng lặp python ở trên.
    MA_FE=0
    O=$(python3 thu_frontend/thu_http.py 2>&1) || MA_FE=$?
    FE_H=$(printf '%s' "$O" | grep -oE 'Ran [0-9]+' | tail -1 | grep -oE '[0-9]+' || echo 0)
    FE_H=${FE_H:-0}
    if [ "$MA_FE" -eq 0 ] && [ "$FE_H" -gt 0 ]; then
        printf '  tầng 2 (HTTP + tệp tĩnh):    %4s ca\n' "$FE_H"
    else
        printf '  tầng 2: HỎNG (mã thoát %s · %s ca)\n' "$MA_FE" "$FE_H"
        HONG="$HONG thu_http.py"
        printf '%s' "$O" | grep -E '^(FAIL|ERROR):' | head -5 | sed 's/^/        /'
    fi
fi
# Tầng 3 KHÔNG chạy trong bộ này: nó cần Chromium + máy chủ sống, mất ~34 giây, và phải
# chạy bằng đúng bộ chạy của nó (thu_giao_dien/chay.sh đặt PLAYWRIGHT_BROWSERS_PATH=0 để
# dùng trình duyệt trong node_modules, KHÔNG dùng cache hệ thống của dự án khác).
if [ -d thu_giao_dien ] && [ -d node_modules/@playwright ]; then
    echo "  tầng 3 (DOM/CSS trong Chromium thật): CÓ, nhưng KHÔNG chạy ở đây"
    echo "     → chạy riêng: sh thu_giao_dien/chay.sh   (đo 15/10/2026: 26 đạt · 1 bỏ qua)"
else
    echo "  tầng 3 (DOM/CSS trong trình duyệt thật): KHÔNG CHẠY ĐƯỢC — thiếu node_modules/@playwright"
    echo "     → cài: npm ci   (anh Thành đã duyệt Playwright ngày 14/10/2026, quyết định D-1)"
fi

echo
echo "══════════ E2E QUA HTTP THẬT ══════════"
E2E=0
if [ -f app/thu/chay_e2e.sh ]; then
    # L2-N1 (AG-01 phát hiện, AG-00 vá): như tầng 2 — bỏ `|| true` + phán bằng chuỗi
    # "mã thoát 0" in ra, nay bắt MÃ THOÁT THẬT của chính tiến trình.
    MA_E2E=0
    O=$(sh app/thu/chay_e2e.sh 2>&1) || MA_E2E=$?
    E2E=$(printf '%s' "$O" | grep -oE 'KẾT QUẢ: [0-9]+/[0-9]+' | head -1 || echo "")
    if [ "$MA_E2E" -eq 0 ]; then
        echo "  ✓ $E2E phép đo đạt"
    else
        echo "  ✗ E2E HỎNG (mã thoát $MA_E2E): $E2E"; HONG="$HONG chay_e2e.sh"
        printf '%s' "$O" | grep -E '^\s+✗' | head -8 | sed 's/^/     /'
    fi
fi

echo
echo "══════════════════════════════════════════════════════════"
echo "  python:   $TONG ca · $((SO_BO - SO_BO_QUA)) bộ chạy thật"
if [ "$SO_BO_QUA" -gt 0 ]; then
    echo "            + $SO_BO_QUA bộ BỎ QUA (0 ca):$BO_QUA"
fi
echo "  frontend: $FE_L + $FE_H ca (hai tầng tự động)"
echo "  E2E:      $E2E"
echo "  bộ hỏng: ${HONG:- KHÔNG}"
echo
echo "  PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI:"
echo "    đo trên: $(uname -s) $(uname -m) · python $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:3])))') · SQLite $(python3 -c 'import sqlite3;print(sqlite3.sqlite_version)')"
# N-02 (AG-01 phát hiện, AG-00 vá): dòng cũ VIẾT CỨNG "cả 5 hãng" trong khi sổ đăng ký chỉ có
    # 2 adapter (jt, vtp). Sai theo hướng NÓI RỘNG HƠN sự thật — hướng nguy hiểm (§12.1 luật 3), lại nằm
    # ngay trong khối mà người đọc dùng để tin báo cáo. Nay lấy thẳng từ sổ đăng ký: dữ kiện đo được
    # thì phải lấy từ LỆNH, không điền vào tệp (§7.3 BAN_GIAO).
    PHAM_VI_HANG=$(python3 -c "
import sys; sys.path.insert(0,'app')
import adapter, adapter_jt, adapter_vtp
ds = adapter.danh_sach_hang()
mo = sorted(m for m, t in ds.items() if t['live_mo'])
print('%d hang dang ky (%s) - dang MO live: %s'
      % (len(ds), ', '.join(sorted(ds)), ', '.join(mo) if mo else 'khong hang nao'))
" 2>/dev/null || echo "KHONG DO DUOC so adapter dang ky")
    echo "    máy chủ bind 127.0.0.1 · adapter hãng ở chế độ MOCK ($PHAM_VI_HANG)"
    # N-03 (AG-01): câu cũ khai "NGOÀI phạm vi: PostgreSQL" trong khi CÙNG lượt chạy in
    # "✓ thu_postgres.py 21 ca" — người đọc không thể biết ý là CHƯA THỬ hay CHƯA CHUYỂN.
    echo "    NGOÀI phạm vi: VPS · CSDL NGHIỆP VỤ chưa chuyển sang PostgreSQL (mới chỉ thử schema"
    echo "      trên cụm tạm cổng riêng) · nhiều tiến trình (bộ riêng app/thu/dong_thoi/chay.py;"
    echo "      trần rate limit sống trong bộ nhớ MỘT tiến trình) · DOM/CSS trong trình duyệt thật ·"
    echo "      nhãn hãng thật · credentials hãng thật · AI thật · dữ liệu lớn · Safari/Firefox"
echo "══════════════════════════════════════════════════════════"
[ -z "$HONG" ] || exit 1
