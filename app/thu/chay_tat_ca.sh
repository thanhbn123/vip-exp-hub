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
# BỘ ĐẾM + LUẬT PHÁN — MỘT chỗ duy nhất, dùng cho CẢ vòng lặp lẫn chế độ `--tinh-ca`
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÁ 19/10/2026 (X1 đo được, Z2 vá): `app/thu/thu_g22_gioihan.py` **CHẠY THẬT 32 ca** nhưng bảng
# tổng kết của bộ chạy này in `0 ca` — bộ thử KHÔNG chết, chỉ có bộ ĐẾM sai.
#
# Vì sao: khi có ca HỎNG/KHUYẾT, bộ thử viết tay in dòng cuối
#     `TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)`
# còn bộ đếm cũ chỉ nhận `Ran N` và `N ca — ĐẠT` ⇒ không khớp khuôn nào ⇒ đọc thành 0.
# Như thế "0 ca" gộp CHẾT THẬT với "CHẠY 32 CA RỒI HỎNG" vào cùng một nhãn — đúng thứ §12.1 luật 3
# cấm: kết luận chỉ được nói trong đúng phạm vi ĐÃ ĐO.
#
# NAY nhận thêm BA khuôn, giữ nguyên THỨ TỰ ƯU TIÊN cũ (một bộ in nhiều khuôn thì `Ran N` vẫn
# thắng — B5 của `thu_g22_gioihan.py` canh đúng thứ tự này):
#     1. `Ran N`          (unittest)                    — lần CUỐI
#     2. `N ca — ĐẠT`     (bộ viết tay, lượt đạt)      — lần CUỐI
#     3. `N ca — HỎNG`    (bộ viết tay, lượt hỏng)     — lần CUỐI   ← MỚI
#     4. `TỔNG: N ca`     (tổng kết tự công bố)        — lần CUỐI   ← MỚI
#     5. `số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : a/b/c/d/e`
#                         (cổng E2E `thu_g22_e2e.py`) — tổng a+b+c+d+e ← MỚI
#        Vì sao có khuôn 5: cùng một lớp lỗi. Sau khi vá Chromium (việc 2), cổng E2E **chạy thật**
#        nhưng output của nó không có `Ran`/`N ca — ĐẠT`/`TỔNG:` ⇒ bộ đếm vẫn đọc 0 và còn phán
#        HỎNG oan một lượt đã thoát 0. Đọc đúng khuôn của nó là đếm đúng, KHÔNG phải nới luật.
#
# KHÔNG nới điều kiện ĐẠT. Ngược lại, siết thêm MỘT vế đã đo được: một bộ thoát 0 nhưng TỰ IN
# `ca — HỎNG` phải là ĐỎ — nếu không, nó vừa tự báo hỏng vừa được bảng ghi ✓.
#
# Vì sao gom vào HÀM: bộ tự kiểm `app/thu/thu_g22_demca2.py` phải đo CHÍNH bộ đếm này, không đo
# bản chép lại (hai bản sẽ trôi khỏi nhau — §41). Chế độ `--tinh-ca` chỉ gọi đúng hàm dưới đây.
tinh_ca() {
    TC_MA=$1
    TC_OUT=$2
    TC_N=$(printf '%s' "$TC_OUT" | grep -oE 'Ran [0-9]+' | tail -1 | grep -oE '[0-9]+' || true)
    TC_KHUON="Ran [0-9]+"
    if [ -z "$TC_N" ]; then
        TC_N=$(printf '%s' "$TC_OUT" | grep -oE '[0-9]+ ca — ĐẠT' | tail -1 | grep -oE '^[0-9]+' || true)
        TC_KHUON="N ca — ĐẠT"
    fi
    if [ -z "$TC_N" ]; then
        TC_N=$(printf '%s' "$TC_OUT" | grep -oE '[0-9]+ ca — HỎNG' | tail -1 | grep -oE '^[0-9]+' || true)
        TC_KHUON="N ca — HỎNG"
    fi
    if [ -z "$TC_N" ]; then
        TC_N=$(printf '%s' "$TC_OUT" | grep -oE 'TỔNG: [0-9]+ ca' | tail -1 | grep -oE '[0-9]+' || true)
        TC_KHUON="TỔNG: N ca"
    fi
    # Khuôn 5 — cổng E2E: `số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : a/b/c/d/e`.
    # Số ca ĐÃ CHẠY là TỔNG a+b+c+d+e (bỏ sót `did not run` là đếm thiếu đúng chỗ nó cần nói).
    if [ -z "$TC_N" ]; then
        TC_DAY=$(printf '%s' "$TC_OUT" | grep -oE 'số ca +ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : [0-9]+/[0-9]+/[0-9]+/[0-9]+/[0-9]+' | tail -1 || true)
        if [ -n "$TC_DAY" ]; then
            TC_N=0
            _tc_ifs=$IFS
            IFS=/
            for _tc_p in $(printf '%s' "$TC_DAY" | sed 's/.*: //'); do
                TC_N=$((TC_N + _tc_p))
            done
            IFS=$_tc_ifs
            TC_KHUON="số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN"
        fi
    fi
    if [ -z "$TC_N" ]; then
        TC_N=0
        TC_KHUON="không khớp khuôn nào"
    fi
    if printf '%s' "$TC_OUT" | grep -qE '^OK( |$)|ca — ĐẠT|số ca +ĐẠT/HỎNG'; then TC_DAU_VET=1; else TC_DAU_VET=0; fi
    # Dòng PHÁN QUYẾT là dòng CUỐI CÙNG (sau khi bỏ dòng trống) — KHÔNG phải "có chữ HỎNG ở đâu
    # đó". Vì sao phải chặt như thế, đo được trên cây thật: `thu_g22_zeroca.py` thoát 0, 17/17 ca
    # đạt, nhưng docstring của ca 04 trích nguyên văn `TỔNG: 32 ca — HỎNG`; unittest -v in
    # docstring ra, nên bản vá đầu tiên gắn HỎNG oan cho nó. Dòng cuối của một bộ thử mới là
    # phán quyết của chính nó; chữ HỎNG nằm giữa bài là TRÍCH DẪN.
    TC_CUOI=$(printf '%s' "$TC_OUT" | grep -v '^[[:space:]]*$' | tail -1 || true)
    if printf '%s' "$TC_CUOI" | grep -qE '[0-9]+ ca — HỎNG'; then TC_HONG=1; else TC_HONG=0; fi
    TC_PHAN=HONG
    TC_LY_DO=""
    if [ "$TC_MA" -eq 0 ] && [ "$TC_DAU_VET" = 1 ] && [ "$TC_N" -gt 0 ] && [ "$TC_HONG" -eq 0 ]; then
        TC_PHAN=DAT
    elif [ "$TC_MA" -eq 0 ] && [ "$TC_N" -eq 0 ] && [ "$TC_HONG" -eq 0 ] \
         && printf '%s' "$TC_OUT" | grep -q 'skipped'; then
        TC_PHAN=BO_QUA
    elif [ "$TC_MA" -ne 0 ]; then
        TC_LY_DO="mã thoát $TC_MA"
    elif [ "$TC_HONG" -eq 1 ]; then
        TC_LY_DO='thoát 0 nhưng báo cáo tự in `ca — HỎNG`'
    elif [ "$TC_DAU_VET" = 0 ]; then
        TC_LY_DO="thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào"
    else
        TC_LY_DO="thoát 0 nhưng đếm được 0 ca"
    fi
}

# CHẾ ĐỘ ĐO BỘ ĐẾM (dùng bởi `app/thu/thu_g22_demca2.py`):
#     sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>
# In bốn dòng `KHOÁ=giá-trị`. Mã thoát 0 = ĐỌC ĐƯỢC; phán quyết nằm ở `PHAN`, KHÔNG phải mã thoát
# của chế độ này. Cố ý không in gì khác để bộ tự kiểm phân tích được.
if [ "${1:-}" = "--tinh-ca" ]; then
    case "${2:-}" in
        ''|*[!0-9]*) echo "mã thoát phải là số: '${2:-}'" >&2; exit 2 ;;
    esac
    if [ "$#" -ne 3 ] || [ ! -f "$3" ]; then
        echo "dùng: sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>" >&2
        exit 2
    fi
    _out=$(cat "$3")
    tinh_ca "$2" "$_out"
    printf 'N=%s\nKHUON=%s\nPHAN=%s\nLY_DO=%s\n' "$TC_N" "$TC_KHUON" "$TC_PHAN" "$TC_LY_DO"
    exit 0
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
    # Đếm ca + phán quyết: MỘT hàm, dùng CHUNG với chế độ `--tinh-ca` ở đầu tệp (bộ tự kiểm
    # `thu_g22_demca2.py` gọi đúng hàm đó, không chép lại). Hàm nhận thêm `N ca — HỎNG` và
    # `TỔNG: N ca`; xem khối "BỘ ĐẾM + LUẬT PHÁN" ở đầu tệp để biết vì sao (X1: 32 ca ⇒ đọc 0).
    tinh_ca "$MA" "$OUT"
    N=$TC_N
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
    if [ "$TC_PHAN" = DAT ]; then
        printf '  ✓ %-24s %4s ca\n' "$(basename "$t")" "$N"
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
        # Lý do đã được `tinh_ca` tính: mã thoát · tự in HỎNG · không dấu vết · 0 ca.
        printf '  ✗ %-24s %4s ca  HỎNG (%s)\n' "$(basename "$t")" "$N" "$TC_LY_DO"
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
