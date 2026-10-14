#!/bin/sh
# DIỄN TẬP KHÔI PHỤC — chạy THẬT trên dữ liệu thử. AG-05 DEVOPS sở hữu file này.
# Dùng: sh trien_khai/dien_tap_khoi_phuc.sh
#
# ====== VÌ SAO PHẢI DIỄN TẬP CHỨ KHÔNG CHỈ VIẾT QUY TRÌNH ======
# Một bản sao lưu chưa từng được khôi phục là một bản sao lưu CHƯA BIẾT có dùng được không.
# Mục PRODUCTION READINESS của dự án ghi đúng lý do 3: "chưa có lượt khôi phục khóa thật".
# Script này không vá được điều đó (nó chạy trên MÁY DỰNG, không phải máy chủ sạch), nhưng nó
# biến "quy trình có vẻ đúng" thành "quy trình đã chạy một lượt, đây là số đo".
#
# ====== CHỐT AN TOÀN ======
# TUYỆT ĐỐI KHÔNG ghi đè CSDL đang dùng. Chốt dưới đây là CẤU TRÚC, không phải lời dặn: script
# tự dựng thư mục tạm và TỪ CHỐI chạy nếu `VIP_HUB_DATA` trỏ vào vùng dữ liệu thật.
set -eu

GOC=$(cd "$(dirname "$0")/.." && pwd)
VUNG_CAM="$HOME/Projects/vip-express-hub"

NEN=$(mktemp -d "${TMPDIR:-/tmp}/veh-dientap.XXXXXX")
don_dep() { rm -rf "$NEN"; }
trap don_dep EXIT INT TERM

# Chốt 1: nền tạm không được nằm trong vùng dữ liệu thật.
case "$NEN" in
    "$VUNG_CAM"*) echo "DUNG: nen tam nam trong vung du lieu that: $NEN" >&2; exit 9 ;;
esac
# Chốt 2: nếu người chạy đã đặt sẵn VIP_HUB_DATA trỏ vào vùng thật thì DỪNG, không ghi đè nó
# im lặng — biến môi trường bị ghi đè âm thầm là đúng kiểu hỏng im lặng.
if [ -n "${VIP_HUB_DATA:-}" ]; then
    case "$VIP_HUB_DATA" in
        "$VUNG_CAM"*) echo "DUNG: VIP_HUB_DATA dang tro vao $VIP_HUB_DATA (du lieu THAT)." >&2
                      echo "Bo bien do roi chay lai — script tu dung nen tam." >&2; exit 9 ;;
    esac
fi

export VIP_HUB_DATA="$NEN/du-lieu"
export VIP_HUB_BACKUP_PASSPHRASE="dien-tap-$(date +%s)-khong-phai-passphrase-that"
export PYTHONPATH="$GOC/app"
mkdir -p "$VIP_HUB_DATA"
cd "$GOC"

echo "=============================================================="
echo " DIEN TAP KHOI PHUC — VIP Express Hub G11"
echo " Nen tam : $VIP_HUB_DATA"
echo " Luc     : $(date '+%Y-%m-%d %H:%M:%S%z')"
echo " Luu y   : passphrase o day la passphrase DIEN TAP, sinh tai cho, khong phai cua anh Thanh."
echo "=============================================================="

echo ""
echo "--- B1. Dung CSDL + schema + du lieu mau ---"
python3 app/migrate.py   > "$NEN/migrate.log" 2>&1 || { echo "migrate HONG"; cat "$NEN/migrate.log"; exit 1; }
python3 app/khoi_tao.py  > "$NEN/seed.log"    2>&1 || { echo "seed HONG";    cat "$NEN/seed.log";    exit 1; }
tail -3 "$NEN/migrate.log" | sed 's/^/    /'

echo ""
echo "--- B2. Them credentials DA MA HOA (de kiem thuc su giai ma duoc sau khoi phuc) ---"
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ["PYTHONPATH"]))
import csdl, bao_mat
csdl.mo()
# Tên cột lấy từ `PRAGMA table_info(carrier_accounts)` ĐO THẬT ngày 15/10/2026, không từ trí nhớ:
# credentials_ma_hoa · credentials_duoi · webhook_ma · webhook_secret_ma_hoa · hang · moi_truong.
# Bản đầu của script này đoán `cred_ban_ma`/`provider_ma` và nổ ngay ở bước B2.
tn = csdl.mot("SELECT id FROM tenants LIMIT 1")
assert tn is not None, "khong co tenant nao sau seed — kiem lai khoi_tao.py"
tid = tn["id"]
cred = {"api_key": "KEY-DIEN-TAP-0001", "secret": "SECRET-DIEN-TAP-0001"}
ban_ma, duoi = bao_mat.ma_hoa_cred(cred, tid, "jt")
wh_ma = "wh-dien-tap-0001"
wh_bm = bao_mat.ma_hoa_wh("HMAC-DIEN-TAP-0001", wh_ma)
csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
         " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, kich_hoat, tao_luc)"
         " VALUES (?,?,?,?,?,?,?,?,?,?)",
         (tid, "jt", "TK dien tap", "sandbox", ban_ma, duoi, wh_ma, wh_bm, 1, csdl.bay_gio()))
print("    da ghi 1 ban ghi: credentials + webhook secret, ca hai DA MA HOA (tenant %d)" % tid)
PY

echo ""
echo "--- B3. SO DO TRUOC: so dong tung bang + integrity_check ---"
python3 trien_khai/do_csdl.py > "$NEN/truoc.json"
python3 trien_khai/do_csdl.py --in-gon "$NEN/truoc.json"

echo ""
echo "--- B4. Sao luu CSDL (API backup cua SQLite, nhat quan ca khi co WAL) ---"
BAN_CSDL=$(python3 -c "
import sys; sys.path.insert(0,'$GOC/app')
import migrate; print(migrate.sao_luu())")
echo "    ban sao CSDL : $BAN_CSDL"
ls -l "$BAN_CSDL" | awk '{print "    kich thuoc   : "$5" byte"}'

echo ""
echo "--- B5. Sao luu KHOA (goi .vipkb ma hoa doc lap bang passphrase) ---"
GOI="$NEN/khoa-dien-tap.vipkb"
python3 app/sao_luu_khoa.py tao "$GOI" > "$NEN/goi.json" 2>&1 \
    || { echo "tao goi khoa HONG"; cat "$NEN/goi.json"; exit 1; }
sed 's/^/    /' "$NEN/goi.json" | head -20
echo "--- B5b. KIEM goi TRUOC khi tin no (§12.1: kiem cong cu truoc khi dung) ---"
python3 app/sao_luu_khoa.py kiem "$GOI" | sed 's/^/    /'

echo ""
echo "--- B6. Sao luu CAU HINH ---"
# Cấu hình của hệ này nằm trong MÃ (`app/cau_hinh.py`) + biến môi trường, không có file riêng.
# Nên "sao lưu cấu hình" = ghi lại MÃ BĂM của file cấu hình + danh sách TÊN biến (KHÔNG giá trị).
mkdir -p "$NEN/cau-hinh"
shasum -a 256 app/cau_hinh.py .env.example Dockerfile docker-compose.yml .dockerignore \
    > "$NEN/cau-hinh/bam.txt" 2>/dev/null || true
env | sed -n 's/^\(VIP_HUB_[A-Z_]*\)=.*/\1/p' | sort > "$NEN/cau-hinh/ten-bien.txt"
echo "    ma bam cau hinh : $NEN/cau-hinh/bam.txt ($(wc -l < "$NEN/cau-hinh/bam.txt" | tr -d ' ') dong)"
echo "    ten bien (KHONG gia tri): $(tr '\n' ' ' < "$NEN/cau-hinh/ten-bien.txt")"

echo ""
echo "--- B7. GIA LAP THAM HOA: xoa CSDL va toan bo khoa ---"
rm -f "$VIP_HUB_DATA/hub.db" "$VIP_HUB_DATA/hub.db-wal" "$VIP_HUB_DATA/hub.db-shm"
rm -rf "$VIP_HUB_DATA/khoa" "$VIP_HUB_DATA/khoa-noi-bo.key"
echo "    con lai trong thu muc du lieu: $(ls -A "$VIP_HUB_DATA" | tr '\n' ' ')"
echo "    (phai KHONG con hub.db va khong con thu muc khoa)"

echo ""
echo "--- B8. KHOI PHUC CSDL ---"
cp "$BAN_CSDL" "$VIP_HUB_DATA/hub.db"
echo "    da chep $BAN_CSDL -> hub.db"

echo ""
echo "--- B9. KHOI PHUC KHOA tu goi ---"
python3 app/sao_luu_khoa.py khoi-phuc "$GOI" "$VIP_HUB_DATA/khoa" | sed 's/^/    /'

echo ""
echo "--- B10. SO DO SAU + so sanh ---"
python3 trien_khai/do_csdl.py > "$NEN/sau.json"
python3 trien_khai/do_csdl.py --in-gon "$NEN/sau.json"
echo ""
# Lệch ĐÃ KHAI TRƯỚC, kèm lý do đo được: `sao_luu_khoa.khoi_phuc()` tự ghi MỘT dòng audit
# (app/sao_luu_khoa.py dòng 454, `ghi_audit=True`). Đó là hành vi ĐÚNG — lượt khôi phục khóa
# phải để lại dấu vết. Khai đúng con số +1 chứ không khai cả bảng: khai cả bảng là tắt phép đo,
# và từ đó một lượt mất 500 dòng audit cũng đi qua im lặng.
python3 trien_khai/do_csdl.py --so-sanh "$NEN/truoc.json" "$NEN/sau.json" \
    --cho-phep-lech 'audit=+1:sao_luu_khoa.khoi_phuc() tu ghi 1 dong audit — hanh vi dung' \
    || KQ_SS=1

echo ""
echo "--- B11. GIAI MA LAI credentials (phep do THAT su quan trong) ---"
# Số dòng khớp KHÔNG đủ để kết luận "khôi phục thành công": CSDL về đủ mà khóa sai thì mọi
# credentials thành rác, và không có gì báo cho tới lượt gọi hãng đầu tiên. Đây là chỗ hai thứ
# phải khớp NHAU, nên phải đo riêng.
python3 - <<'PY' || { echo "    GIAI MA THAT BAI — khoi phuc KHONG dat"; exit 1; }
import os, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
import csdl, bao_mat
csdl.dong(); csdl.mo()
r = csdl.mot("SELECT id, tenant_id, hang, credentials_ma_hoa, webhook_ma,"
             " webhook_secret_ma_hoa FROM carrier_accounts"
             " WHERE ten='TK dien tap' ORDER BY id DESC LIMIT 1")
assert r is not None, "khong con ban ghi credentials nao"
cred = bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
assert cred["api_key"] == "KEY-DIEN-TAP-0001", "giai ma credentials ra noi dung SAI"
# Đo CẢ secret webhook: `ma_hoa_wh`/`giai_ma_wh` là hàm KHÁC với AAD KHÁC. Đo một đường rồi
# kết luận cho cả hai là đúng kiểu vượt phạm vi §12.1 luật 3 — rủi ro R-h của dự án ghi rõ
# `ban_ma[]` của gói backup CHỈ phủ `carrier_accounts`, nên phải đo từng đường một.
wh = bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], r["webhook_ma"])
assert wh == "HMAC-DIEN-TAP-0001", "giai ma webhook secret ra noi dung SAI"
print("    giai ma DAT — credentials VA webhook secret khop nguyen van (gia tri KHONG in ra)")
PY

echo ""
echo "--- B12. DIEN TAP LUI (rollback) ---"
# Ghi thêm một dòng SAU khi backup, rồi lùi về backup, rồi kiểm dòng đó đã mất.
python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
import csdl
csdl.dong(); csdl.mo()
csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
         ("SAU-BACKUP", "Tenant tao SAU luot backup", "free", csdl.bay_gio()))
print("    da them tenant 'SAU-BACKUP' (ton tai SAU moc backup)")
PY
python3 app/migrate.py --rollback "$BAN_CSDL" 2>&1 | sed 's/^/    /'
python3 - <<'PY' || { echo "    LUI KHONG DAT"; exit 1; }
import os, sys
sys.path.insert(0, os.environ["PYTHONPATH"])
import csdl
csdl.dong(); csdl.mo()
r = csdl.mot("SELECT 1 FROM tenants WHERE code='SAU-BACKUP'")
assert r is None, "lui xong ma dong tao SAU backup VAN CON — rollback khong co tac dung"
print("    lui DAT — dong tao sau moc backup da mat dung nhu mong doi")
PY

echo ""
echo "=============================================================="
echo " DIEN TAP XONG. So do: $NEN/truoc.json va $NEN/sau.json"
echo " LUU Y PHAM VI: luot nay chay tren MAY DUNG, tren du lieu THU, bang passphrase DIEN TAP."
echo " No KHONG thay cho mot luot khoi phuc that tren may chu SACH bang passphrase THAT"
echo " (blocker B-2 cua du an van con nguyen)."
echo "=============================================================="
exit "${KQ_SS:-0}"
