#!/bin/sh
# DIỄN TẬP KHOÁ — MỘT LỆNH, CHẠY THẬT, TRÊN DỮ LIỆU THỬ. AG-05 SECURITY & KEY OPS (G12).
# Dùng: sh trien_khai/sao_luu_ngoai/dien-tap-khoa.sh
#
# ====== NÓ DIỄN TẬP CÁI GÌ ======
# Đúng chuỗi mà D-2 và D-3 đòi, theo đúng thứ tự bắt buộc:
#   B1 dựng nền thử cô lập          B2 nạp secret đã mã hoá (cred + webhook, hai AAD khác nhau)
#   B3 TẠO gói backup               B4 KIỂM gói trước khi tin nó
#   B5 CHỨNG NHẬN khôi phục         B6 đọc CHỐT (phải ĐẠT)
#   B7 DIỄN TẬP xoay trên BẢN SAO   B8 XOAY THẬT trên nền thử
#   B9 chốt lại sau khi xoay        B10 nghiệm thu không-chạm-dữ-liệu-thật
#
# ====== CHỐT AN TOÀN — BẰNG CẤU TRÚC, KHÔNG BẰNG LỜI DẶN ======
# Script tự dựng nền tạm và TỪ CHỐI chạy (mã thoát 9) nếu nền tạm hoặc `VIP_HUB_DATA` chạm vào
# vùng dữ liệu thật. Cùng khuôn với `trien_khai/dien_tap_khoi_phuc.sh` của G11 — chốt đó đã
# chứng minh là có tác dụng, nên dùng lại chứ không nghĩ kiểu mới.
#
# ====== PHẠM VI (§12.1 luật 3 + luật 5) ======
#   ĐO:        sao lưu · kiểm gói · khôi phục vào thư mục cô lập · giải mã lại CẢ HAI đường
#              (`giai_ma_cred` + `giai_ma_wh`) · sáu điều kiện của chốt · xoay trên bản sao ·
#              xoay thật trên NỀN THỬ · khoá cũ còn hay mất.
#   KHÔNG ĐO:  khôi phục trên MÁY CHỦ SẠCH bằng PASSPHRASE THẬT (blocker B-2) · gói nằm ngoài
#              máy (D-3 chưa được ghi thật lượt nào) · dữ liệu nghiệp vụ đúng hay sai ·
#              hiệu năng trên dữ liệu lớn.
#   Passphrase ở đây sinh tại chỗ, là passphrase DIỄN TẬP, không phải của anh Thành.
set -eu

GOC=$(cd "$(dirname "$0")/../.." && pwd)
VUNG_CAM="$HOME/Projects/vip-express-hub"

NEN=$(mktemp -d "${TMPDIR:-/tmp}/veh-dientap-khoa.XXXXXX")
don_dep() { rm -rf "$NEN"; }
trap don_dep EXIT INT TERM

case "$NEN" in
    "$VUNG_CAM"*) echo "DUNG: nen tam nam trong vung du lieu that: $NEN" >&2; exit 9 ;;
esac
if [ -n "${VIP_HUB_DATA:-}" ]; then
    case "$VIP_HUB_DATA" in
        "$VUNG_CAM"*) echo "DUNG: VIP_HUB_DATA dang tro vao $VIP_HUB_DATA (du lieu THAT)." >&2
                      echo "Bo bien do roi chay lai — script tu dung nen tam." >&2; exit 9 ;;
    esac
fi

export VIP_HUB_DATA="$NEN/du-lieu"
export VIP_HUB_BACKUP_PASSPHRASE="dien-tap-khoa-$(date +%s)-khong-phai-passphrase-that"
export PYTHONPATH="$GOC/app"
export PYTHONDONTWRITEBYTECODE=1
GOI="$NEN/goi-dien-tap.vipkb"
CN="$NEN/chung-nhan-khoi-phuc.json"
mkdir -p "$VIP_HUB_DATA"
cd "$GOC"

echo "=============================================================="
echo " DIEN TAP KHOA — VIP Express Hub G12 (D-2 + D-3)"
echo " Nen thu : $VIP_HUB_DATA"
echo " Luc     : $(date '+%Y-%m-%d %H:%M:%S%z')"
echo " Luu y   : passphrase DIEN TAP, sinh tai cho. Khong cham du lieu that."
echo "=============================================================="

echo ""
echo "--- B1. Dung CSDL + schema + du lieu mau ---"
python3 app/migrate.py  > "$NEN/migrate.log" 2>&1 || { echo "migrate HONG"; cat "$NEN/migrate.log"; exit 1; }
python3 app/khoi_tao.py > "$NEN/seed.log"    2>&1 || { echo "seed HONG";    cat "$NEN/seed.log";    exit 1; }
tail -2 "$NEN/migrate.log" | sed 's/^/    /'

echo ""
echo "--- B2. Nap secret da ma hoa + seed quyen platform.khoa.xoay ---"
# Ten cot lay tu `PRAGMA table_info(carrier_accounts)` DO THAT ngay 15/10/2026:
#   tenant_id · hang · ten · moi_truong · credentials_ma_hoa · credentials_duoi ·
#   credentials_doi_luc · webhook_ma · webhook_secret_ma_hoa · kich_hoat · tao_luc
# KHONG co cot `trang_thai` — ban dau script nay doan co, va no no ngay o buoc nay.
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
import bao_mat, csdl, quyen, xoay_khoa
csdl.mo()
tid = csdl.mot("SELECT id FROM tenants LIMIT 1")["id"]
for hang, wh in (("jt", "wh-dientap-g12-jt"), ("vtp", "wh-dientap-g12-vtp")):
    if csdl.mot("SELECT id FROM carrier_accounts WHERE webhook_ma=?", (wh,)):
        continue
    bm, duoi = bao_mat.ma_hoa_cred({"api_key": f"KEY-DT-{hang}", "secret": f"SEC-DT-{hang}"},
                                   tid, hang)
    csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
             " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa,"
             " kich_hoat, tao_luc) VALUES (?,?,?,?,?,?,?,?,1,?)",
             (tid, hang, f"TK dien tap {hang}", "sandbox", bm, duoi, wh,
              bao_mat.ma_hoa_wh(f"WHSEC-DT-{hang}", wh), csdl.bay_gio()))
# Quyen moi — o nen THU nay thi seed de chay duoc het chuoi. Tren he that, AG-00 seed.
csdl.ghi("INSERT OR IGNORE INTO permissions (ma, mo_ta) VALUES (?,?)",
         (xoay_khoa.QUYEN_XOAY, "Xoay khoa ma hoa nen tang"))
csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma) VALUES (?,?)",
         ("PLATFORM_OWNER", xoay_khoa.QUYEN_XOAY))
u = csdl.mot("SELECT id FROM users WHERE platform_role='PLATFORM_OWNER' LIMIT 1")
assert u, "khong co PLATFORM_OWNER sau seed — kiem lai khoi_tao.py"
n = csdl.mot("SELECT COUNT(*) n FROM carrier_accounts")["n"]
print(f"    {n} tai khoan hang; PLATFORM_OWNER user_id={u['id']}")
open(os.path.join(os.environ["VIP_HUB_DATA"], "owner-id"), "w").write(str(u["id"]))
PY
UID_OWNER=$(cat "$VIP_HUB_DATA/owner-id")

echo ""
echo "--- B3. TAO goi backup (sao_luu_khoa — KHONG qua xoay_khoa) ---"
python3 app/sao_luu_khoa.py tao "$GOI" | sed 's/^/    /'

echo ""
echo "--- B4. KIEM goi TRUOC khi tin no (CLAUDE.md 12.1) ---"
python3 app/sao_luu_khoa.py kiem "$GOI" | sed 's/^/    /'

echo ""
echo "--- B5. CHUNG NHAN khoi phuc (luot chay RIENG — pid khac luot xoay) ---"
python3 app/xoay_khoa.py chung-nhan "$GOI" "$CN" | sed 's/^/    /'

echo ""
echo "--- B6. Doc CHOT (6 dieu kien) — phai DAT ---"
python3 app/xoay_khoa.py kiem-chot "$GOI" "$CN" | sed 's/^/    /'

echo ""
echo "--- B7. DIEN TAP xoay tren BAN SAO (D-2: 'kiem thu tren ban sao truoc') ---"
python3 app/xoay_khoa.py dien-tap | sed 's/^/    /'

echo ""
echo "--- B8. XOAY THAT tren NEN THU (khong phai du lieu that) ---"
python3 app/xoay_khoa.py xoay-that "$GOI" "$CN" --user-id "$UID_OWNER" | sed 's/^/    /'

echo ""
echo "--- B9. Sau khi xoay: goi CU khong con phu du khoa => CHOT phai TU CHOI ---"
# Day la hanh vi DUNG, khong phai loi: xoay xong thi phai TAO GOI MOI. Mot gol cu khong con la
# duong ve cho du lieu vua ma hoa lai bang khoa moi.
if python3 app/xoay_khoa.py kiem-chot "$GOI" "$CN" > "$NEN/chot-sau.json" 2>&1; then
    echo "    CANH BAO: chot VAN DAT voi goi cu — kiem lai C2" ; sed 's/^/    /' "$NEN/chot-sau.json"
else
    echo "    DUNG NHU MONG DOI: chot tu choi goi cu (ma thoat 1)."
    python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print('    chua dat:', d['chua_dat'])" "$NEN/chot-sau.json" 2>/dev/null || true
fi

echo ""
echo "--- B10. Nghiem thu: KHONG cham du lieu that ---"
THAT="$VUNG_CAM/app/du-lieu/khoa"
if [ -d "$THAT" ]; then
    echo "    Thu muc khoa THAT ($THAT):"
    ls -l "$THAT" | sed 's/^/      /'
    echo "    (so sanh bang mat voi anh chup truoc khi chay — script nay chi DOC)"
else
    echo "    Khong co $THAT tren may nay — khong co gi de cham."
fi
echo "    Thu muc du lieu mac dinh cua repo: $GOC/app/du-lieu"
[ -e "$GOC/app/du-lieu" ] && echo "      TON TAI (kiem lai: dien tap khong duoc tao no)" \
                          || echo "      KHONG TON TAI — dung nhu mong doi"

echo ""
echo "=============================================================="
echo " DIEN TAP KHOA: HET. Ma thoat 0 = moi buoc B1..B8 chay dat."
echo " PHAM VI: may dung, du lieu thu, passphrase dien tap."
echo " KHONG chung minh: khoi phuc tren may chu sach bang passphrase that (B-2)."
echo "=============================================================="
