# Một TIẾN TRÌNH trong phép đo đồng thời (chỉ thị G12 mục 11–13).
#
# Mỗi phép ghi được xếp vào ĐÚNG MỘT trong bốn kết cục mà chỉ thị đòi phân biệt:
#   CHOT_THANH_CONG  — đã commit, dữ liệu vào thật
#   TU_CHOI_NGHIEP_VU — CSDL/mã từ chối đúng luật (vượt trần, trùng khoá). KHÔNG phải lỗi.
#   KHOA_HET_GIO     — chờ khoá quá hạn (SQLITE_BUSY). Mất việc, phải người xử.
#   GIAO_DICH_HONG   — lỗi khác, giao dịch lùi.
# Và một kết cục KHÔNG nằm trong bốn cái trên vì nó không tự báo:
#   MAT_CAP_NHAT     — ghi đè mất nhau. Chỉ phát hiện được bằng ĐỐI CHIẾU cuối lượt.
import json
import os
import sys
import time

GOC = os.environ["VIP_GOC"]
sys.path.insert(0, GOC)
import cau_hinh                                                          # noqa: E402
cau_hinh.THU_MUC_DU_LIEU = os.environ["VIP_DATA"]
cau_hinh.DUONG_DAN_CSDL = os.path.join(os.environ["VIP_DATA"], "hub.db")
import csdl                                                             # noqa: E402
import tai_chinh                                                        # noqa: E402

NHAN = sys.argv[1]
SO_PHEP = int(os.environ.get("VIP_SO_PHEP", "400"))
TENANT = int(os.environ.get("VIP_TENANT", "1"))
KIEU = os.environ.get("VIP_KIEU", "but_toan")

dem = {"CHOT_THANH_CONG": 0, "TU_CHOI_NGHIEP_VU": 0, "KHOA_HET_GIO": 0,
       "GIAO_DICH_HONG": 0}
chi_tiet = {}
tong_ghi = 0        # tổng số tiền tiến trình này TIN là đã ghi vào sổ


def ghi_nhan(ma, vi_du=""):
    dem[ma] += 1
    if vi_du and len(chi_tiet.setdefault(ma, [])) < 3:
        chi_tiet[ma].append(vi_du[:90])


def mot_phep(i):
    """Một phép GHI. Trả số tiền đã vào sổ (0 nếu không vào)."""
    global tong_ghi
    try:
        if KIEU == "but_toan":
            # Sổ cái bất biến: bút toán + cập nhật công nợ, phải cùng vào hoặc cùng không.
            tai_chinh.ghi_but_toan(TENANT, "cod_hang_bao_thu", 1000, "nguoi",
                                   f"{NHAN}#{i}")
            ghi_nhan("CHOT_THANH_CONG")
            return 1000
        if KIEU == "doc_sua_ghi":
            # ĐỌC rồi SỬA rồi GHI trên cùng một hàng — chỗ sinh ra MẤT CẬP NHẬT.
            # CỐ Ý viết theo kiểu dễ sai nhất (đọc ngoài, ghi theo giá trị đã đọc) để phép
            # đo chạm được vào ca đó; mã thật dùng UPDATE ... SET x = x + ? nên không sai.
            with csdl.giao_dich():
                r = csdl.mot("SELECT dem FROM _dt_bo_dem WHERE id=1")
                csdl.ghi("UPDATE _dt_bo_dem SET dem=? WHERE id=1", (r["dem"] + 1,))
            ghi_nhan("CHOT_THANH_CONG")
            return 1
        if KIEU == "han_muc":
            # `kiem_va_tang_don` KHÔNG trả bool — nó NÉM `billing.VuotHanMuc` khi vượt trần
            # và trả None khi cho qua. Bản đầu của bàn đo này viết `if billing.kiem_va_...()`
            # nên đếm MỌI lượt thành công thành "từ chối" (None là giả) và mọi lượt vượt trần
            # thành "giao dịch hỏng". Kết quả: báo 0 lượt chốt trong khi bộ đếm CSDL là 15 —
            # con số tự tố cáo nhau nên mới lộ. §12.1: bàn đo cũng là thứ phải kiểm trước.
            import billing
            try:
                billing.kiem_va_tang_don(TENANT)
            except billing.VuotHanMuc as e:
                ghi_nhan("TU_CHOI_NGHIEP_VU", str(e))
                return 0
            ghi_nhan("CHOT_THANH_CONG")
            return 1
        raise SystemExit("VIP_KIEU lạ: " + KIEU)
    except csdl.LoiVanHanh as e:
        s = str(e).lower()
        if "locked" in s or "busy" in s or "timeout" in s:
            ghi_nhan("KHOA_HET_GIO", str(e))
        else:
            ghi_nhan("GIAO_DICH_HONG", "%s: %s" % (type(e).__name__, e))
        return 0
    except (csdl.LoiToanVen, tai_chinh.LoiTaiChinh) as e:
        ghi_nhan("TU_CHOI_NGHIEP_VU", "%s: %s" % (type(e).__name__, e))
        return 0
    except Exception as e:                      # noqa: BLE001 — xếp loại rồi đi tiếp
        ghi_nhan("GIAO_DICH_HONG", "%s: %s" % (type(e).__name__, e))
        return 0


khi = float(os.environ["VIP_BAT_DAU"])
while time.time() < khi:
    time.sleep(0.001)
t0 = time.time()
for i in range(SO_PHEP):
    tong_ghi += mot_phep(i)
print(json.dumps({"nhan": NHAN, "giay": round(time.time() - t0, 3),
                  "tong_ghi": tong_ghi, "dem": dem, "vi_du": chi_tiet}), flush=True)
