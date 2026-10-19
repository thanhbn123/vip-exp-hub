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

# ══════════════════════════════════════════════════════════════════════════════════════════════
# BỘ ĐẾM DÙNG CHUNG — MỘT chỗ duy nhất: `app/thu/thu_r6_demca.py`
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# R6 (19/10/2026): bộ đếm cũ nằm NGAY TRONG TỆP NÀY dưới dạng ba `grep`, còn
# `thu_g22_gioihan.py` giữ một bản sao thứ hai. Hai bản sao đã trôi khỏi nhau — và mỗi lần trôi
# thì bảng ghi một con số khác con số bộ thử vừa công bố. Nay:
#   · `thu_r6_demca.py` hiểu khuôn của CẢ BA loại runner (unittest · Playwright · viết tay)
#     và cả `node --test` của tầng 1;
#   · TỆP NÀY KHÔNG còn regex đếm nào — chỉ gọi bộ đếm chung rồi dùng kết quả;
#   · `--tinh-ca` (đường `thu_g22_demca2.py` / `thu_qa_nguyennhan.py` đo) cũng gọi ĐÚNG tệp đó.
#
# BỐN CON SỐ TÁCH RỜI — không gộp "chưa chạy" vào "ca chạy thật":
#   KE_HOACH    số ca runner công bố (gồm cả bỏ qua + chưa chạy)
#   CO_KET_QUA  số ca THỰC SỰ có phán quyết đạt/hỏng (trừ skip, did-not-run, KHUYẾT)
#   BO_QUA      ca bỏ qua có chủ đích
#   CHUA_CHAY   ca `did not run` (Playwright) — KHÔNG cộng vào ca có kết quả
#
# `TC_N` GIỮ nghĩa cũ = KE_HOACH, để bộ tự kiểm QA (`thu_qa_nguyennhan.py`) đọc y nguyên.
BO_DEM="$GOC/app/thu/thu_r6_demca.py"
if [ ! -f "$BO_DEM" ]; then
    echo "HỎNG: KHÔNG có bộ đếm dùng chung $BO_DEM ⇒ không đo được bộ nào." >&2
    exit 2
fi

tinh_ca() {
    TC_MA=$1
    TC_OUT=$2
    # Mặc định HỎNG: nếu bộ đếm chung không chạy được thì KHÔNG được lặng lẽ cho qua.
    TC_N=0; TC_KHUON="bộ đếm"; TC_PHAN=HONG; TC_LY_DO="bộ đếm dùng chung lỗi"
    TC_KE_HOACH=0; TC_CO_KET_QUA=0; TC_DAT=-1; TC_HONG=-1
    TC_BO_QUA=0; TC_CHUA_CHAY=0; TC_KHONG_KET_LUAN=0; TC_DAU_VET=0; TC_HONG_TU_BAO=0
    _tc=$(printf '%s' "$TC_OUT" | python3 "$BO_DEM" --shell "$TC_MA" 2>/dev/null) || _tc=""
    if [ -z "$_tc" ]; then
        TC_LY_DO="bộ đếm dùng chung KHÔNG chạy được (thử: python3 $BO_DEM)"
        return 0
    fi
    eval "$_tc"
    TC_N=$TC_KE_HOACH
    case "${TC_LY_DO_MA:-}" in
        ma_thoat)      TC_LY_DO="mã thoát $TC_MA" ;;
        tu_bao_hong)   TC_LY_DO='thoát 0 nhưng báo cáo tự in `ca — HỎNG`' ;;
        khong_dau_vet) TC_LY_DO="thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào" ;;
        khong_ca)      TC_LY_DO="thoát 0 nhưng đếm được 0 ca" ;;
        chua_chay)     TC_LY_DO="thoát 0 nhưng còn $TC_CHUA_CHAY ca did-not-run" ;;
        *)             TC_LY_DO="" ;;
    esac
}

# CHẾ ĐỘ ĐO BỘ ĐẾM (dùng bởi `app/thu/thu_g22_demca2.py` và `app/thu/thu_qa_nguyennhan.py`):
#     sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>
# Gọi ĐÚNG bộ đếm chung, in `KEY=giá-trị` (N/KHUON/PHAN/LY_DO + bốn con số tách rời).
if [ "${1:-}" = "--tinh-ca" ]; then
    case "${2:-}" in
        ''|*[!0-9]*) echo "mã thoát phải là số: '${2:-}'" >&2; exit 2 ;;
    esac
    if [ "$#" -ne 3 ] || [ ! -f "$3" ]; then
        echo "dùng: sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>" >&2
        exit 2
    fi
    exec python3 "$BO_DEM" --tinh-ca "$2" "$3"
fi


# VÁ 15/10/2026 (N-G18-00, AG-01 phát hiện — AG-00 chốt): MÔI TRƯỜNG GIT HỎNG LÀM HAI NHIỆT KẾ
# ĐO HAI THỨ KHÁC NHAU.
#
# `GIT_CONFIG_COUNT=N` đòi hỏi đủ `GIT_CONFIG_KEY_0..N-1` VÀ `GIT_CONFIG_VALUE_0..N-1`. Phiên nào
# đặt `GIT_CONFIG_COUNT` mà THIẾU khoá — gặp thật: có `COUNT=2` + `VALUE_0`/`VALUE_1` nhưng KHÔNG
# có `KEY_0`/`KEY_1` — thì MỌI lệnh git thoát 128, kể cả `git status`.
#
# Hệ quả ĐO ĐƯỢC: CÙNG một cây, CÙNG `HEAD`, CÙNG số ca, mà lượt chạy "nguyên văn" cho
# exit 1 + 2 bộ hỏng, còn lượt đã gỡ biến cho exit 0. AG-00 luôn gỡ biến trước khi đo nên báo 0;
# AG-01 chạy nguyên văn nên báo 1. HAI CON SỐ ĐỀU ĐÚNG — nhưng chúng đo HAI MÔI TRƯỜNG khác nhau,
# và như thế thì không con số nào đối chiếu được với con số kia. Một bộ chạy mà kết quả phụ thuộc
# vào việc người gọi có nhớ gỡ một biến hay không là một bộ chạy không đáng tin.
#
# Nay bộ chạy TỰ CHUẨN HOÁ: thấy gia đình `GIT_CONFIG_*` dị dạng thì gỡ nó đi rồi mới chạy.
# Gỡ ở ĐÂY chứ không dặn lòng vòng, vì lời dặn thì người sau quên, còn dòng mã thì không.
if [ -n "${GIT_CONFIG_COUNT:-}" ] && [ "${GIT_CONFIG_COUNT:-0}" -gt 0 ] 2>/dev/null; then
    _i=0; _thieu=0
    while [ "$_i" -lt "$GIT_CONFIG_COUNT" ]; do
        eval "_k=\${GIT_CONFIG_KEY_$_i:-}"
        if [ -z "$_k" ]; then _thieu=1; fi
        _i=$((_i + 1))
    done
    if [ "$_thieu" -eq 1 ]; then
        echo "[cảnh báo] GIT_CONFIG_COUNT=$GIT_CONFIG_COUNT nhưng thiếu GIT_CONFIG_KEY_* —"
        echo "           gỡ gia đình GIT_CONFIG_* dị dạng (nếu không, MỌI lệnh git thoát 128)."
        echo "           Xem N-G18-00 trong docs/QA_G18.md."
        unset GIT_CONFIG_COUNT
        for _v in $(env | sed -n 's/^\(GIT_CONFIG_[A-Z_0-9]*\)=.*/\1/p'); do unset "$_v"; done
        unset _v
    fi
    unset _i _thieu
fi

TOI_THIEU=${VIP_TOI_THIEU_BO:-12}

# ══════════════════════════════════════════════════════════════════════════════════════════════
# VÂN TAY CÂY — **GIT LÀ CHÍNH** (luật §41 `docs/SHARED_CONTRACTS.md`), vá `G16-09`
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÌ SAO PHẢI CÓ: `docs/QA_G16.md` §`G16-09` đo được rằng lệnh vân tay CŨ
#     find app gateway thu_frontend thu_giao_dien -type f \( -name '*.py' -o -name '*.mjs' \
#          -o -name '*.sh' -o -name '*.json' \) | sort | shasum -a 256
# **MÙ** với `docs/` (không nằm trong phạm vi `find`) và với `*.md` (không nằm trong danh sách
# đuôi): thêm một dòng vào CHÍNH bản hợp đồng mà vân tay **không nhúc nhích**. Con số không kèm
# vân tay là con số không đối chiếu được — nhưng một vân tay MÙ còn tệ hơn: nó làm người đọc TIN
# là đã ghim, trong khi lượt sửa hợp đồng giữa lượt đo đã lọt qua cả vân tay lẫn mắt người.
#
# NAY: **Git là CHÍNH** — `git rev-parse HEAD` + `git diff HEAD` rỗng + `git status --porcelain
# -uall` rỗng. Nó phủ MỌI tệp được theo dõi (kể cả `docs/**`, `*.md`, `.gitignore`) và mọi thay
# đổi CHƯA COMMIT (kể cả tệp mới). Khi cây đã bẩn (nhiều làn cùng ghi) thì dùng vân tay DỰ PHÒNG
# `{ git ls-files -s; git status --porcelain -uall; }` — và chế độ đang dùng được IN RA.
#
# Một chỗ duy nhất hiện thực: `app/thu/thu_g21_chotcay.py` (ba bản sao là ba bản sẽ trôi khỏi nhau).
# Mã thoát của `--van-tay-so` NÓI RÕ cái gì đã đổi: 1 = HEAD · 2 = tệp đã theo dõi (⇒ HỎNG, số đo
# thuộc hai mốc mã khác nhau) · 3 = chỉ tập tệp CHƯA theo dõi (⇒ CẢNH BÁO) · 4 = không đo được.
VT_TEP="$GOC/app/thu/thu_g21_chotcay.py"
VT_TAM="${TMPDIR:-/tmp}/veh_g21_van_tay_$$.json"
VT_CO=0
if [ -f "$VT_TEP" ]; then
    python3 "$VT_TEP" --van-tay-ghi "$VT_TAM" || VT_CO=$?
else
    echo "[cảnh báo] KHÔNG có $VT_TEP ⇒ lượt chạy này KHÔNG có vân tay (số đo không ghim được)"
    VT_CO=4
fi
if [ "$VT_CO" -ne 0 ]; then
    echo "[cảnh báo] không ghi được vân tay TRƯỚC (mã thoát $VT_CO) — vẫn chạy tiếp, sẽ báo ở cuối"
fi

echo "══════════ BỘ THỬ PYTHON (unittest) ══════════"
# Bốn tổng TÁCH RỜI. `TONG` = kế hoạch (gồm skip/did-not-run), `TONG_CO_KET_QUA` mới là số ca
# thực sự có phán quyết. KHÔNG cộng `TONG_CHUA_CHAY` vào bất kỳ dòng "ca chạy thật" nào.
TONG=0; TONG_CO_KET_QUA=0; TONG_BO_QUA_CA=0; TONG_CHUA_CHAY=0; TONG_KHONG_KET_LUAN=0
SO_BO=0; SO_BO_CO_KQ=0; SO_BO_HONG=0; HONG=""; BO_QUA=""; SO_BO_QUA=0
# `thu_e2e.py` CỐ Ý loại khỏi phép dò: nó cần một máy chủ đang chạy + CSDL cô lập do
# `chay_e2e.sh` dựng, nên chạy một mình là vô nghĩa. Nó vẫn ĐƯỢC CHẠY — ở mục E2E bên dưới,
# qua đúng bộ chạy của nó. Loại ở đây là để không đếm nó hai lần và không báo hỏng giả;
# KHÔNG phải để bỏ qua nó.
#
# DÒ MỘT LẦN rồi dùng lại danh sách: cuối vòng lặp so `SO_BO` với `SO_BO_DO`. Nếu một bộ bị CHE
# (không được chạy) thì phép so lệch và cả lượt chạy HỎNG — thay vì lặng lẽ báo "đã chạy hết".
DS_BO=$(find app/thu gateway/thu -name 'thu_*.py' -type f ! -name 'thu_e2e.py' | sort)
SO_BO_DO=$(printf '%s\n' "$DS_BO" | grep -c . || true)
for t in $DS_BO; do
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
    # Đếm ca + phán quyết: MỘT hàm, dùng CHUNG với chế độ `--tinh-ca` ở đầu tệp. Hàm gọi
    # `thu_r6_demca.py`; tệp này KHÔNG giữ regex đếm nào.
    tinh_ca "$MA" "$OUT"
    N=$TC_N
    TONG=$((TONG + N))
    TONG_CO_KET_QUA=$((TONG_CO_KET_QUA + TC_CO_KET_QUA))
    TONG_BO_QUA_CA=$((TONG_BO_QUA_CA + TC_BO_QUA))
    TONG_CHUA_CHAY=$((TONG_CHUA_CHAY + TC_CHUA_CHAY))
    TONG_KHONG_KET_LUAN=$((TONG_KHONG_KET_LUAN + TC_KHONG_KET_LUAN))
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
    if [ "$TC_PHAN" = DAT ]; then
        SO_BO_CO_KQ=$((SO_BO_CO_KQ + 1))
        printf '  ✓ %-24s %4s ca · %4s có kết quả\n' "$(basename "$t")" "$N" "$TC_CO_KET_QUA"
    elif [ "$TC_PHAN" = BO_QUA ]; then
        # BỎ QUA là phán quyết THỨ BA, không gộp vào ĐẠT.
        # Trước 15/10/2026 chỉ có hai phán quyết, nên thu_postgres.py — bộ tự bỏ qua trừ khi
        # bật VIP_THU_POSTGRES=1 — hiện dấu ✓ trong MỌI báo cáo dù chạy KHÔNG MỘT CA NÀO.
        # Người đọc "27 bộ ĐẠT" tin là PostgreSQL đã được phủ; thật ra chưa đo gì.
        # §12.1 luật 3: kết luận chỉ được nói trong đúng phạm vi đã đo.
        LY=$(printf '%s' "$OUT" | grep -oE 'Bật bằng: [A-Z_]+=[0-9]+' | head -1 || true)
        printf '  ⊘ %-24s    BỎ QUA  %s\n' "$(basename "$t")" "${LY:-không nêu cách bật}"
        SO_BO_QUA=$((SO_BO_QUA + 1)); BO_QUA="$BO_QUA $(basename "$t")"
    else
        # Lý do đã được `tinh_ca` tính: mã thoát · tự in HỎNG · không dấu vết · 0 ca · chưa chạy.
        SO_BO_HONG=$((SO_BO_HONG + 1))
        if [ "$TC_CO_KET_QUA" -gt 0 ]; then SO_BO_CO_KQ=$((SO_BO_CO_KQ + 1)); fi
        printf '  ✗ %-24s %4s ca · %4s có kết quả  HỎNG (%s)\n' \
            "$(basename "$t")" "$N" "$TC_CO_KET_QUA" "$TC_LY_DO"
        HONG="$HONG $(basename "$t")"
        printf '%s' "$OUT" | grep -E '^(FAIL|ERROR):' | head -8 | sed 's/^/        /'
    fi
done

# CHỐT CHỐNG "BỘ BỊ CHE": mọi tệp dò được PHẢI được xử lý. Lệch ⇒ dừng, không được coi là
# "đã chạy hết" (đây là chỗ 6 bộ từng biến mất khỏi bảng mà không ai thấy).
if [ "$SO_BO" -ne "$SO_BO_DO" ]; then
    echo
    echo "HỎNG: dò được $SO_BO_DO bộ nhưng chỉ xử lý $SO_BO bộ — có bộ bị CHE khỏi bảng."
    echo "      Bảng dưới đây KHÔNG phải 'đã chạy hết'; không được dùng làm bằng chứng."
    exit 2
fi

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
        # Dùng CHUNG bộ đếm: node --test in `ℹ pass 56` / `ℹ fail 0` (hoặc `# pass 56`).
        # Bản cũ chỉ đọc `pass` và VỨT mã thoát ⇒ một lượt `fail 3` vẫn in "56 ca" mà không đỏ.
        MA_NODE=0
        O=$(node --test thu_frontend/thu_logic.mjs 2>&1) || MA_NODE=$?
        tinh_ca "$MA_NODE" "$O"
        FE_L=$TC_N
        if [ "$TC_PHAN" = DAT ]; then
            printf '  tầng 1 (logic thuần, node):  %4s ca · %4s có kết quả\n' \
                "$TC_N" "$TC_CO_KET_QUA"
        else
            printf '  tầng 1: HỎNG (%s · %s ca)\n' "$TC_LY_DO" "$TC_N"
            HONG="$HONG thu_logic.mjs"
            printf '%s' "$O" | grep -E '^[[:space:]]*(#|ℹ) (fail|not ok)' | head -5 | sed 's/^/        /'
        fi
    fi
else
    echo "  tầng 1: BỎ QUA — không có node trên máy này"
fi
if [ -f thu_frontend/thu_http.py ]; then
    # L2-N1 (AG-01 phát hiện, AG-00 vá): chỗ này từng là `... || true` rồi phán bằng
    # `grep -qE '^OK'` — tức VỨT mã thoát rồi đoán bằng CHỮ TRONG OUTPUT. Nay dùng CHUNG bộ đếm.
    MA_FE=0
    O=$(python3 thu_frontend/thu_http.py 2>&1) || MA_FE=$?
    tinh_ca "$MA_FE" "$O"
    FE_H=$TC_N
    if [ "$TC_PHAN" = DAT ]; then
        printf '  tầng 2 (HTTP + tệp tĩnh):    %4s ca · %4s có kết quả\n' \
            "$TC_N" "$TC_CO_KET_QUA"
    else
        printf '  tầng 2: HỎNG (%s · %s ca)\n' "$TC_LY_DO" "$TC_N"
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
E2E="(chưa đo)"
if [ -f app/thu/chay_e2e.sh ]; then
    # L2-N1: bắt MÃ THOÁT THẬT; R6: dùng CHUNG bộ đếm cho khuôn `KẾT QUẢ: x/y`.
    # Bản cũ cho ✓ chỉ vì mã thoát 0 — một lượt thoát 0 mà không in phép đo nào vẫn "đạt".
    MA_E2E=0
    O=$(sh app/thu/chay_e2e.sh 2>&1) || MA_E2E=$?
    tinh_ca "$MA_E2E" "$O"
    if [ "$TC_PHAN" = DAT ]; then
        E2E="$TC_DAT/$TC_N"
        echo "  ✓ KẾT QUẢ: $E2E phép đo đạt"
    else
        E2E="${TC_DAT:-?}/$TC_N"
        echo "  ✗ E2E HỎNG ($TC_LY_DO · $E2E)"; HONG="$HONG chay_e2e.sh"
        printf '%s' "$O" | grep -E '^[[:space:]]+✗' | head -8 | sed 's/^/     /'
    fi
fi

echo
echo "══════════════════════════════════════════════════════════"
echo "  python:   KẾ HOẠCH $TONG ca · CÓ KẾT QUẢ $TONG_CO_KET_QUA ca"
echo "            (bỏ qua $TONG_BO_QUA_CA ca · chưa chạy $TONG_CHUA_CHAY ca · không kết luận $TONG_KHONG_KET_LUAN ca)"
if [ "$SO_BO_QUA" -gt 0 ]; then
    echo "            + $SO_BO_QUA bộ BỎ QUA (0 ca):$BO_QUA"
fi
echo "  bộ:       dò $SO_BO/$SO_BO_DO · có ca chạy $SO_BO_CO_KQ · hỏng $SO_BO_HONG"
echo "  frontend: $FE_L + $FE_H ca KẾ HOẠCH (hai tầng tự động)"
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
echo
echo "══════════ VÂN TAY CÂY — GIT LÀ CHÍNH (luật §41, vá G16-09) ══════════"
VT_MA=0
if [ -f "$VT_TEP" ] && [ "$VT_CO" -eq 0 ]; then
    python3 "$VT_TEP" --van-tay-so "$VT_TAM" || VT_MA=$?
elif [ "$VT_CO" -eq 4 ]; then
    echo "  ✗ KHÔNG có vân tay TRƯỚC ⇒ lượt chạy này KHÔNG ghim được vào cây nào"
    VT_MA=4
else
    echo "  ✗ ghi vân tay TRƯỚC hỏng (mã thoát $VT_CO) ⇒ không so được"
    VT_MA=4
fi
rm -f "$VT_TAM"
case "$VT_MA" in
    0) : ;;
    1|2) echo "  ✗ VÂN TAY ĐỔI ⇒ các con số trên KHÔNG đối chiếu được với một mốc mã (§41)"
         HONG="$HONG van-tay-cay" ;;
    3) # CẢNH BÁO, KHÔNG phải HỎNG — và đây là quyết định có căn cứ, không phải nới lỏng:
       # `docs/QA_G20.md` §1.0 đã ĐO được rằng băm/bắt cả cây làm việc sẽ báo "cây đã đổi" sau MỖI
       # lượt chạy (báo cáo của Playwright, khoá nội bộ, `__pycache__`) — "một nhiệt kế đo nhầm thứ,
       # và là nhiệt kế sẽ bị học cách bỏ qua". Một làn KHÁC giao tệp giữa lượt chạy không làm sai
       # những gì ĐÃ chạy; nó chỉ làm con số "N bộ · M ca" khó tái lập. Nên nó được IN RA KÈM ĐƯỜNG,
       # ngay trước dòng mã thoát — chứ không im lặng và cũng không làm đỏ oan cả bộ chạy.
       echo "  ⚠ CẢNH BÁO (không phải HỎNG): có làn giao tệp CHƯA THEO DÕI giữa lượt chạy"
       echo "     ⇒ con số '$TONG ca · $((SO_BO - SO_BO_QUA)) bộ' KHÔNG tái lập nguyên vẹn;"
       echo "     chạy lại khi cây đứng yên nếu cần con số ghim." ;;
    *) echo "  ✗ KHÔNG ĐO ĐƯỢC vân tay ⇒ con số trên là con số KHÔNG GHIM"
       HONG="$HONG van-tay-cay-khong-do-duoc" ;;
esac
echo "  bộ hỏng (cuối): ${HONG:- KHÔNG}"
echo "══════════════════════════════════════════════════════════"
[ -z "$HONG" ] || exit 1
