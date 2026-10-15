# Bàn đo đồng thời: N TIẾN TRÌNH hệ điều hành thật × M phép ghi (chỉ thị G12 mục 11–13).
#
# Vì sao TIẾN TRÌNH chứ không THREAD: `csdl.khoa_ghi` là RLock của Python — nó chỉ phủ MỘT
# tiến trình. Đo bằng thread là đo chính cái khoá đó, và sẽ kết luận "an toàn" cho một ca
# mà khoá ấy không hề phủ. Mọi kết luận về nhiều tiến trình phải đo bằng nhiều tiến trình.
import json
import os
import subprocess
import sys
import tempfile
import time

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
sys.path.insert(0, GOC)

SO_TIEN_TRINH = int(os.environ.get("VIP_SO_TT", "8"))
SO_PHEP = int(os.environ.get("VIP_SO_PHEP", "400"))


def _nen(thu_muc, tran_don=None):
    """Dựng CSDL + tenant. Chạy trong TIẾN TRÌNH CON để không nhiễm bộ nhớ của bàn đo."""
    ma = '''
import os, sys
sys.path.insert(0, %r)
import cau_hinh
cau_hinh.THU_MUC_DU_LIEU = %r
cau_hinh.DUONG_DAN_CSDL = %r
import csdl, migrate, tai_chinh
migrate.chay(im_lang=True)
tai_chinh.quen_cache_bang(); tai_chinh._dam_bao_bang()
tran = %r
csdl.ghi("INSERT OR IGNORE INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,"
         "han_muc_ai_thang,so_nhan_vien,so_tai_khoan_hang) VALUES ('do',"
         "'goi do',0,?,999999,999,999)", (tran if tran is not None else 999999,))
csdl.ghi("INSERT OR IGNORE INTO tenants (id,ten,goi_id,tao_luc) VALUES (1,'DO','do',?)",
         (csdl.bay_gio(),))
csdl.ghi("CREATE TABLE IF NOT EXISTS _dt_bo_dem (id INTEGER PRIMARY KEY, dem INTEGER NOT NULL)")
csdl.ghi("INSERT OR REPLACE INTO _dt_bo_dem (id,dem) VALUES (1,0)")
print("nen-ok")
''' % (GOC, thu_muc, os.path.join(thu_muc, "hub.db"), tran_don)
    p = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True)
    if "nen-ok" not in p.stdout:
        raise RuntimeError("dựng nền hỏng: " + (p.stderr or p.stdout)[-500:])


def chay(kieu, tran_don=None, so_tt=None, so_phep=None):
    so_tt = so_tt or SO_TIEN_TRINH
    so_phep = so_phep or SO_PHEP
    tm = tempfile.mkdtemp(prefix="vh-dt-%s-" % kieu)
    _nen(tm, tran_don)
    mt = dict(os.environ, VIP_GOC=GOC, VIP_DATA=tm, VIP_KIEU=kieu,
              VIP_SO_PHEP=str(so_phep), VIP_BAT_DAU=str(time.time() + 3.0))
    ps = [subprocess.Popen([sys.executable, os.path.join(DAY, "nguoi_chay.py"), "tt%d" % i],
                           env=mt, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
          for i in range(so_tt)]
    bao, vo = [], []
    for p in ps:
        o, e = p.communicate(timeout=900)
        try:
            bao.append(json.loads(o.strip().splitlines()[-1]))
        except Exception:
            vo.append((o[-200:], e[-400:]))
    return tm, bao, vo


def tong_hop(bao):
    t = {"CHOT_THANH_CONG": 0, "TU_CHOI_NGHIEP_VU": 0, "KHOA_HET_GIO": 0, "GIAO_DICH_HONG": 0}
    for b in bao:
        for k, v in b["dem"].items():
            t[k] += v
    return t


def in_bang(ten, bao, vo, so_phep, doi_chieu=None):
    t = tong_hop(bao)
    tong = sum(t.values())
    print("\n┌─ %s ─ %d tiến trình × %d phép = %d" % (ten, len(bao), so_phep, len(bao) * so_phep))
    for k in ("CHOT_THANH_CONG", "TU_CHOI_NGHIEP_VU", "KHOA_HET_GIO", "GIAO_DICH_HONG"):
        print("│  %-20s %6d" % (k, t[k]))
    print("│  %-20s %6d  (phải khớp số phép)" % ("tổng xếp loại", tong))
    if vo:
        print("│  TIẾN TRÌNH VỠ      %6d  %s" % (len(vo), vo[0][1][-120:]))
    lau = [b["giay"] for b in bao]
    print("│  thời gian: nhanh %.1fs · chậm %.1fs" % (min(lau), max(lau)))
    if doi_chieu:
        for dong in doi_chieu:
            print("│  %s" % dong)
    print("└" + "─" * 60)
    return t, tong
