# Chạy TOÀN BỘ phép đo đồng thời của chỉ thị G12 mục 11.
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import do_dong_thoi as D                                                # noqa: E402
sys.path.insert(0, D.GOC)

SO_TT = int(os.environ.get("VIP_SO_TT", "8"))
SO_PHEP = int(os.environ.get("VIP_SO_PHEP", "400"))
xau = []


def _csdl(tm):
    import cau_hinh
    cau_hinh.THU_MUC_DU_LIEU = tm
    cau_hinh.DUONG_DAN_CSDL = os.path.join(tm, "hub.db")
    import csdl
    csdl.dong()
    return csdl


# ──────────────────────────────── 1. SỔ CÁI TÀI CHÍNH
tm, bao, vo = D.chay("but_toan", so_tt=SO_TT, so_phep=SO_PHEP)
csdl = _csdl(tm)
kn = csdl.ket_noi(os.path.join(tm, "hub.db"), theo_ten_cot=True)
so_bt = kn.execute("SELECT COUNT(*) c, COALESCE(SUM(so_tien_dong),0) s FROM tc_but_toan").fetchone()
cong_no = kn.execute("SELECT COALESCE(SUM(so_du_dong),0) s FROM tc_cong_no").fetchone()["s"]
kn.close()
t, tong = D.in_bang("1. SỔ CÁI TÀI CHÍNH (bút toán + công nợ)", bao, vo, SO_PHEP, [
    "bút toán trong sổ : %d dòng, tổng %d đồng" % (so_bt["c"], so_bt["s"]),
    "tiến trình TIN đã ghi: %d đồng" % sum(b["tong_ghi"] for b in bao),
    "công nợ tổng hợp  : %d đồng" % cong_no,
])
if so_bt["s"] != sum(b["tong_ghi"] for b in bao):
    xau.append("SỔ CÁI: tiến trình tin %d mà sổ có %d — MẤT GHI hoặc GHI THỪA"
               % (sum(b["tong_ghi"] for b in bao), so_bt["s"]))
if so_bt["s"] != cong_no:
    xau.append("SỔ CÁI: sổ %d ≠ công nợ %d — bút toán mồ côi" % (so_bt["s"], cong_no))
if t["CHOT_THANH_CONG"] != so_bt["c"]:
    xau.append("SỔ CÁI: báo chốt %d lượt mà sổ %d dòng" % (t["CHOT_THANH_CONG"], so_bt["c"]))

# ──────────────────────────────── 2. ĐỌC–SỬA–GHI (bắt MẤT CẬP NHẬT)
tm, bao, vo = D.chay("doc_sua_ghi", so_tt=SO_TT, so_phep=SO_PHEP)
kn = _csdl(tm).ket_noi(os.path.join(tm, "hub.db"), theo_ten_cot=True)
dem_that = kn.execute("SELECT dem FROM _dt_bo_dem WHERE id=1").fetchone()["dem"]
kn.close()
tin = sum(b["tong_ghi"] for b in bao)
t2, _ = D.in_bang("2. ĐỌC–SỬA–GHI trên cùng một hàng", bao, vo, SO_PHEP, [
    "bộ đếm tin đã tăng: %d" % tin,
    "bộ đếm THỰC TẾ   : %d" % dem_that,
    "MẤT CẬP NHẬT     : %d  (%.1f%% số lượt chốt)" % (
        tin - dem_that, 100.0 * (tin - dem_that) / tin if tin else 0),
])
MAT = tin - dem_that

# ──────────────────────────────── 3. TRẦN HẠN MỨC
TRAN = SO_PHEP      # trần = 400, tổng nhu cầu = 8×400 = 3200
tm, bao, vo = D.chay("han_muc", tran_don=TRAN, so_tt=SO_TT, so_phep=SO_PHEP)
kn = _csdl(tm).ket_noi(os.path.join(tm, "hub.db"), theo_ten_cot=True)
r = kn.execute("SELECT so_don FROM usage_thang WHERE tenant_id=1").fetchone()
kn.close()
so_don = r["so_don"] if r else 0
t3, _ = D.in_bang("3. TRẦN HẠN MỨC (trần %d, nhu cầu %d)" % (TRAN, SO_TT * SO_PHEP),
                  bao, vo, SO_PHEP, [
    "bộ đếm trong CSDL : %d  (trần %d)" % (so_don, TRAN),
"số lượt được cho  : %d" % sum(
        b["dem"]["CHOT_THANH_CONG"] for b in bao),
])
cho = sum(b["dem"]["CHOT_THANH_CONG"] for b in bao)
if so_don > TRAN:
    xau.append("HẠN MỨC: bộ đếm %d VƯỢT trần %d" % (so_don, TRAN))
if cho != so_don:
    xau.append("HẠN MỨC: cho qua %d lượt mà bộ đếm %d" % (cho, so_don))

# ──────────────────────────────── KẾT
print("\n" + "=" * 62)
print("PHẠM VI ĐÃ ĐO: %d TIẾN TRÌNH hệ điều hành thật × %d phép ghi mỗi tiến trình." % (SO_TT, SO_PHEP))
print("  macOS arm64 · python 3.9.6 · SQLite 3.51.0 · WAL · ổ NỘI BỘ.")
print("NGOÀI phạm vi: PostgreSQL · ổ MẠNG (khoá SQLite không đáng tin ở đó) · nhiều MÁY ·")
print("  tiến trình bị tắt giữa giao dịch · máy chủ HTTP thật · hãng thật.")
print()
if MAT > 0:
    print("MẤT CẬP NHẬT đo được: %d lượt ở ca ĐỌC–SỬA–GHI." % MAT)
    print("  Đây là ca viết CỐ Ý theo kiểu dễ sai (đọc ngoài, ghi theo giá trị đã đọc) để")
    print("  phép đo chạm tới được. Mã nghiệp vụ thật KHÔNG viết kiểu đó — nó dùng")
    print("  `UPDATE ... SET x = x + ?` hoặc đặt điều kiện trần trong `WHERE`.")
    print("  Nghĩa của con số này: khoá trong MỘT tiến trình không cứu được nhiều tiến trình.")
else:
    print("MẤT CẬP NHẬT: 0 — nhưng chỉ trong %d×%d lượt này, trên ổ nội bộ." % (SO_TT, SO_PHEP))
if xau:
    print("\nSAI LỆCH CẦN XỬ:")
    for x in xau:
        print("  ✗ " + x)
    sys.exit(1)
print("\n0 sai lệch ở BA phép đối chiếu: tổng sổ cái khớp số tiến trình tin đã ghi · sổ cái")
print("khớp công nợ · bộ đếm hạn mức không vượt trần và khớp số lượt được cho.")
