#!/bin/sh
# ĐƯA GÓI KHOÁ RA NGOÀI THIẾT BỊ (G12 / D-3) — AG-05 SECURITY & KEY OPS.
# Dùng: sh trien_khai/sao_luu_ngoai/dua-goi-khoa-ra-ngoai.sh <goi.vipkb> <dich>
#
# ============================================================================================
#  RỦI RO MÀ D-3 SINH RA ĐỂ VÁ — NÓI THẲNG
# ============================================================================================
#  Hôm nay gói khoá nằm CÙNG MÁY với CSDL mà nó bảo vệ. Mất ổ là mất CẢ HAI cùng lúc, và
#  `secret_provider.lay_khoa` CỐ Ý không sinh khoá thay thế, nên khi đó KHÔNG CÒN ĐƯỜNG NÀO VỀ:
#  bản mã credentials của mọi tenant thành rác vĩnh viễn. Đây không phải rủi ro lý thuyết —
#  nó là lý do duy nhất D-3 tồn tại.
#
#  Một bản sao "ngoài" mà vẫn nằm trên cùng ổ, cùng máy, cùng tài khoản đám mây thì KHÔNG vá
#  được rủi ro này. Nó chỉ làm người ta yên tâm, và yên tâm sai là tệ hơn lo đúng.
#
# ============================================================================================
#  D-3 — ANH THÀNH DUYỆT **CÓ ĐIỀU KIỆN**, BA ĐIỀU
# ============================================================================================
#  1. **Mã hoá độc lập**  → ĐÃ CÓ, do `app/sao_luu_khoa.py` làm: KEK dẫn xuất từ passphrase
#     riêng (PBKDF2-HMAC-SHA256, 600.000 vòng, salt mỗi gói), AES-256-GCM, header làm AAD.
#     Script này **không mã hoá lại gì** — nó chỉ chuyển một gói ĐÃ mã hoá. Mã hoá hai lần
#     bằng hai sơ đồ là thêm một chỗ hỏng, không thêm an toàn.
#  2. **Kiểm tra quyền**  → mục QUYỀN bên dưới, và script tự đo quyền file trước khi gửi.
#  3. **Diễn tập khôi phục** → `sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh`, đã chạy, có số.
#
#  **Và một điều nữa, do chỉ thị đặt, không do anh:** lượt GHI THẬT đầu tiên ra VIP Vault
#  **phải hỏi anh Thành**. Script này KHÔNG tự ghi — xem CHỐT HỎI NGƯỜI bên dưới.
#
# ============================================================================================
#  QUYỀN — AI ĐƯỢC CHẠY, CHẠY Ở ĐÂU, GÓI NẰM ĐÂU VỚI QUYỀN GÌ
# ============================================================================================
#  | Hạng mục            | Quy định                                                          |
#  |---------------------|-------------------------------------------------------------------|
#  | Ai chạy             | anh Thành, hoặc người anh chỉ định bằng lời. KHÔNG phải tác tử.   |
#  | Chạy ở đâu          | TAY, trên máy giữ gói. KHÔNG lịch chạy nền, KHÔNG launchd/cron.   |
#  | Passphrase          | chỉ trong đầu/kho mật khẩu của anh. KHÔNG vào vault, git, hội thoại|
#  | Quyền file gói      | `0600`, chủ sở hữu là người chạy. Script TỪ CHỐI nếu khác.        |
#  | Quyền thư mục chứa  | `0700`. Script TỪ CHỐI nếu nhóm/người khác đọc được.              |
#  | Đích                | ổ rời đã mã hoá toàn ổ, HOẶC `/opt/vip-vault` trên VPS (chưa duyệt)|
#  | KHÔNG được làm đích | thư mục static đang phục vụ · trong repo git · ổ dùng chung không mã hoá |
#
#  **CẤM TUYỆT ĐỐI:** đưa passphrase vào dòng lệnh (`ps` nhìn thấy), vào script, vào nhật ký,
#  vào `wiki/`, vào `nhat-ky/` (CLAUDE.md §15.2 cấm thẳng).
#
# ============================================================================================
#  VIP VAULT — NÓI RÕ CÁI CHƯA BIẾT
# ============================================================================================
#  `CLAUDE.md` §19.4: từ 27/09/2026 hệ sao lưu DUY NHẤT là VIP Vault (`/opt/vip-vault`,
#  5 timer systemd, kho chính là NAS). Nó **tự dò CSDL SQLite** và **dump PostgreSQL**.
#
#  **Gói khoá `.vipkb` KHÔNG nằm trong phạm vi đó — CHƯA ĐO, đừng giả định nó tự được sao lưu.**
#  Nó không phải SQLite, không phải PostgreSQL, và `/etc/vip-vault/config.yml` chưa ai thêm nó.
#  Nên cần ÍT NHẤT một quyết định nữa từ anh Thành, nêu ở `docs/G12_KEY_OPS.md`:
#     (a) thêm một mục vào `config.yml` để VIP Vault nuốt luôn thư mục gói khoá, hay
#     (b) giữ gói khoá NGOÀI VIP Vault, trên ổ rời do anh giữ tay.
#  Có lý lẽ cho (b): VIP Vault chép sang NAS, mà NAS cũng đồng bộ với vault trên hai máy Mac.
#  Gói khoá đi theo đường đó là nó có mặt ở nhiều chỗ hơn ta đếm được.
#
#  Chỉ thị dự án CẤM deploy VPS, nên script này **không có đường nào tự nối tới VPS**: nó chỉ
#  chép vào một thư mục đích trên máy đang chạy, và IN RA lệnh `rsync`/`scp` cho anh tự chạy.
#
# ============================================================================================
#  CHỐT HỎI NGƯỜI — lượt GHI THẬT đầu tiên phải có người bật
# ============================================================================================
#  Script DỪNG (mã thoát 7) trừ khi có MỘT trong hai:
#     - file công tắc  `trien_khai/sao_luu_ngoai/TOI-DA-DOC-VA-DONG-Y`  (do NGƯỜI tạo), hoặc
#     - tham số        `--toi-da-doc-va-dong-y`
#  File công tắc KHÔNG nằm trong repo và KHÔNG script nào được tự tạo nó. Chạy khô
#  (`--chay-kho`) thì không cần công tắc — nó không ghi gì.
set -eu

GOC=$(cd "$(dirname "$0")/../.." && pwd)
THU_MUC_TOI=$(cd "$(dirname "$0")" && pwd)
CONG_TAC="$THU_MUC_TOI/TOI-DA-DOC-VA-DONG-Y"

GOI=""; DICH=""; DONG_Y=0; CHAY_KHO=0
for a in "$@"; do
    case "$a" in
        --toi-da-doc-va-dong-y) DONG_Y=1 ;;
        --chay-kho)             CHAY_KHO=1 ;;
        -*) echo "Tham so la: $a" >&2; exit 2 ;;
        *)  if [ -z "$GOI" ]; then GOI="$a"; elif [ -z "$DICH" ]; then DICH="$a"; fi ;;
    esac
done

if [ -z "$GOI" ] || [ -z "$DICH" ]; then
    cat <<EOF
Cach dung:
  sh trien_khai/sao_luu_ngoai/dua-goi-khoa-ra-ngoai.sh <goi.vipkb> <thu-muc-dich> [--chay-kho] [--toi-da-doc-va-dong-y]

  --chay-kho               kiem moi dieu kien, KHONG ghi gi. Khong can cong tac.
  --toi-da-doc-va-dong-y   bat luot ghi THAT (hoac tao file $CONG_TAC).

Tao goi truoc bang:  python3 app/sao_luu_khoa.py tao <goi.vipkb>
Dien tap truoc bang: sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh
EOF
    exit 2
fi

echo "=============================================================="
echo " DUA GOI KHOA RA NGOAI (D-3) — $(date '+%Y-%m-%d %H:%M:%S%z')"
echo " Goi  : $GOI"
echo " Dich : $DICH"
[ "$CHAY_KHO" -eq 1 ] && echo " Che do: CHAY KHO — khong ghi gi"
echo "=============================================================="

loi=0
canh=0

echo ""
echo "--- K1. Goi ton tai, dung duoi, quyen 0600 ---"
if [ ! -f "$GOI" ]; then
    echo "  TU CHOI: khong thay $GOI"; exit 1
fi
case "$GOI" in
    *.vipkb) : ;;
    *) echo "  TU CHOI: goi phai co duoi .vipkb"; exit 1 ;;
esac
Q=$(stat -f '%Lp' "$GOI" 2>/dev/null || stat -c '%a' "$GOI")
CHU=$(stat -f '%Su' "$GOI" 2>/dev/null || stat -c '%U' "$GOI")
echo "  quyen=$Q chu=$CHU kich_thuoc=$(wc -c < "$GOI" | tr -d ' ') byte"
[ "$Q" = "600" ] || { echo "  TU CHOI: quyen goi phai la 600, dang la $Q"; loi=1; }
[ "$CHU" = "$(id -un)" ] || { echo "  TU CHOI: goi khong thuoc nguoi dang chay ($CHU != $(id -un))"; loi=1; }

echo ""
echo "--- K2. Goi MO DUOC va TOAN VEN (khong tin mot file chua kiem) ---"
# Doc header truoc (khong can passphrase), roi kiem toan ven (can passphrase).
# Thu dung de kiem chung phai duoc kiem TRUOC khi tin — CLAUDE.md 12.1.
PYTHONPATH="$GOC/app" python3 "$GOC/app/sao_luu_khoa.py" header "$GOI" | sed 's/^/    /' || loi=1
if [ -n "${VIP_HUB_BACKUP_PASSPHRASE:-}" ] || [ -t 0 ]; then
    PYTHONPATH="$GOC/app" python3 "$GOC/app/sao_luu_khoa.py" kiem "$GOI" | sed 's/^/    /' || loi=1
else
    echo "  BO QUA kiem toan ven: khong co passphrase va khong co terminal."
    echo "  DAY KHONG PHAI 'dat' — chi la CHUA DO. Dat VIP_HUB_BACKUP_PASSPHRASE roi chay lai."
    canh=$((canh+1))
fi

echo ""
echo "--- K3. Co chung nhan khoi phuc ben canh goi khong ---"
CN="$(dirname "$GOI")/chung-nhan-khoi-phuc.json"
if [ -f "$CN" ]; then
    echo "  co: $CN"
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('    ket_qua =', d.get('ket_qua'), '| ghi luc', d.get('luc'))" "$CN"
else
    echo "  KHONG CO chung nhan khoi phuc ben canh goi."
    echo "  Mot goi chua tung duoc khoi phuc la mot goi CHUA BIET co dung duoc khong."
    echo "  Chay: python3 app/xoay_khoa.py chung-nhan \"$GOI\""
    canh=$((canh+1))
fi

echo ""
echo "--- K4. Dich: khong phai cho cam, quyen 0700 ---"
case "$(cd "$(dirname "$DICH")" 2>/dev/null && pwd || echo "$DICH")/$(basename "$DICH")" in
    "$GOC"/admin/*|"$GOC"/pages/*|"$GOC"/assets/*|"$GOC"/mock/*)
        echo "  TU CHOI: dich nam trong thu muc static dang duoc phuc vu — tai ve duoc bang GET vo danh"
        loi=1 ;;
    "$GOC"/*)
        echo "  TU CHOI: dich nam TRONG repo. Goi khoa ra ngoai thi phai RA NGOAI."
        loi=1 ;;
esac
if [ -d "$DICH" ]; then
    QD=$(stat -f '%Lp' "$DICH" 2>/dev/null || stat -c '%a' "$DICH")
    echo "  thu muc dich ton tai, quyen=$QD"
    [ "$QD" = "700" ] || { echo "  TU CHOI: thu muc dich phai 0700, dang $QD. Sua: chmod 700 '$DICH'"; loi=1; }
else
    echo "  thu muc dich CHUA CO — se tao voi quyen 0700 (neu duoc phep ghi)"
fi

echo ""
echo "--- K5. Dich co phai cung o voi goi khong ---"
# Day la cau hoi QUAN TRONG NHAT cua ca D-3, va la cau de bi bo qua nhat.
O_GOI=$(df -P "$(dirname "$GOI")" 2>/dev/null | awk 'NR==2{print $1}')
O_DICH=$(df -P "$(dirname "$DICH")" 2>/dev/null | awk 'NR==2{print $1}')
echo "  o cua goi : $O_GOI"
echo "  o cua dich: $O_DICH"
if [ "$O_GOI" = "$O_DICH" ]; then
    echo "  CANH BAO NANG: dich NAM CUNG O voi goi. Mat o la mat ca hai."
    echo "  Day KHONG va duoc rui ro ma D-3 sinh ra de va. Chi coi la ban sao tien tay."
    canh=$((canh+1))
fi

echo ""
echo "=============================================================="
echo " Ket qua kiem: $loi loi, $canh canh bao"
echo "=============================================================="
[ "$loi" -eq 0 ] || { echo "DUNG: con loi o tren, khong ghi gi." >&2; exit 1; }

if [ "$CHAY_KHO" -eq 1 ]; then
    echo ""
    echo "CHAY KHO: moi dieu kien da kiem, KHONG ghi gi. Bo --chay-kho de ghi that."
    exit 0
fi

# ---------------------------------------------------------------------------------------
# CHOT HOI NGUOI — day la cho script DUNG LAI
# ---------------------------------------------------------------------------------------
if [ "$DONG_Y" -ne 1 ] && [ ! -f "$CONG_TAC" ]; then
    cat >&2 <<EOF

==============================================================
 DUNG LAI — LUOT GHI THAT CAN NGUOI BAT
==============================================================
 Day la luot dua mot GOI CHUA MOI KHOA MA HOA cua he ra khoi may. Chi thi du an doi
 luot ghi THAT dau tien phai duoc anh Thanh dong y, nen script khong tu ghi.

 Truoc khi bat, doc lai bon dieu:
   1. Dich "$DICH" co thuc su NGOAI thiet bi nay khong?
      (K5 o tren da do o dia — doc lai dong do.)
   2. Ai doc duoc dich do? Ai co chia khoa cua o do?
   3. Passphrase mo goi dang o dau? Mat no la goi nay vo dung.
      (Va no KHONG duoc nam cung cho voi goi.)
   4. Da chay dien tap khoi phuc chua?  sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh

 Bat bang MOT trong hai cach:
   touch "$CONG_TAC"
   hoac them tham so:  --toi-da-doc-va-dong-y

 Ve VIP Vault (/opt/vip-vault tren VPS): goi khoa CHUA nam trong pham vi cua no
 (CLAUDE.md 19.4 — no tu do SQLite + dump PostgreSQL, chua ai them goi khoa vao
 /etc/vip-vault/config.yml). Can quyet dinh rieng cua anh Thanh. Script nay KHONG
 noi toi VPS — chi thi cam deploy VPS.
==============================================================
EOF
    exit 7
fi

echo ""
echo "--- G1. GHI THAT ---"
mkdir -p "$DICH"
chmod 700 "$DICH"
TEN="$(basename "$GOI")"
# Ghi file tam cung thu muc roi doi ten — doi ten la nguyen tu, hong giua duong thi file dich
# cu con nguyen (CLAUDE.md 16.3). Dat quyen TRUOC khi doi ten, khong de khe ho 0644.
TAM="$DICH/.$TEN.dang-chep.$$"
cp "$GOI" "$TAM"
chmod 600 "$TAM"
mv "$TAM" "$DICH/$TEN"
[ -f "$CN" ] && { cp "$CN" "$DICH/.cn.$$"; chmod 600 "$DICH/.cn.$$"; mv "$DICH/.cn.$$" "$DICH/$(basename "$CN")"; }

echo ""
echo "--- G2. NGHIEM THU: so ma bam HAI DAU ---"
# Chep xong khong phai la chep dung. Do bang sha256 hai dau, khong tin lenh cp.
A=$(shasum -a 256 "$GOI"      | awk '{print $1}')
B=$(shasum -a 256 "$DICH/$TEN"| awk '{print $1}')
echo "  nguon: $A"
echo "  dich : $B"
if [ "$A" = "$B" ]; then
    echo "  KHOP."
else
    echo "  KHONG KHOP — xoa ban dich hong, khong de lai mot ban sao sai." >&2
    rm -f "$DICH/$TEN"
    exit 1
fi
ls -l "$DICH" | sed 's/^/  /'

cat <<EOF

==============================================================
 XONG — nhung CHUA phai la "co ban ngoai nha"
==============================================================
 Da ghi: $DICH/$TEN  (quyen 600, thu muc 700, sha256 khop hai dau)

 Dua len VIP Vault / may khac thi ANH TU CHAY (script nay khong noi toi VPS):

   rsync -avz --chmod=F600 "$DICH/$TEN" <nguoi>@<may>:/duong/den/kho/

 Sau do nghiem thu o DAU BEN KIA, dung mot lenh chay O BEN DO:
   shasum -a 256 /duong/den/kho/$TEN     # phai ra: $A

 Va dieu quan trong nhat: mot goi chua tung duoc khoi phuc o BEN KIA thi van la
 mot goi chua biet co dung duoc khong. Chay chung-nhan o may do.
==============================================================
EOF
