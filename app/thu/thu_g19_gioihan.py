#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G19/AG-02 — GIỚI HẠN TẦN SUẤT: TRẦN DÙNG CHUNG QUA TIẾN TRÌNH + SỐNG QUA KHỞI ĐỘNG LẠI.

====== HAI LỖ HỔNG PHẢI ĐÓNG, VÀ CÁCH ĐO CHÚNG ======
(a) TRẦN NHÂN THEO SỐ BẢN. PHẦN A của `app/gioi_han.py` giữ bộ đếm trong BỘ NHỚ MỘT TIẾN TRÌNH.
    G18/AG-02 đo được (`thu_g18_multiprocess.py` P1): khai 20 ⇒ cho qua đúng 20·40·80·160 lượt
    với N = 1·2·4·8 tiến trình máy chủ. Chữa bằng khuôn ĐÃ CÓ TRONG NHÀ: chính PHẦN B của cùng
    tệp — trần nằm TRONG câu ghi, CSDL tự so, kết quả xét qua `rowcount`.
(b) CỬA LÁCH KHỞI ĐỘNG LẠI. Bộ đếm trong bộ nhớ mất sạch khi tiến trình chết ⇒ khởi động lại
    là vượt được trần, kể cả khi chỉ có MỘT tiến trình. Sửa bằng chính kho ở (a): kho nằm trong
    CSDL nên sống qua khởi động lại.

====== LUẬT CỦA BỘ ĐO NÀY ======
1. **ĐO BẰNG TIẾN TRÌNH THẬT** (`subprocess`), KHÔNG bằng luồng: phía bị đo luôn là N tiến trình
   độc lập. Luồng chỉ dùng ở phía BẮN, để tạo áp lực đồng thời LÊN các tiến trình đó.
2. **MỌI KHẲNG ĐỊNH CÓ ĐỐI CHỨNG.** Bộ đo tự dựng một BẢN ĐỘT BIẾN của `gioi_han`: phần QUYẾT
   ĐỊNH giữ nguyên từng dòng, chỉ đổi chỗ giữ trạng thái về đúng khuôn CŨ (bộ nhớ một tiến
   trình). Rồi nó chạy ĐÚNG phép đo đó trên bản đột biến. Bản đột biến PHẢI ra 20·N — nếu nó
   cũng ra 20 thì phép đo MÙ, và mọi kết luận "đã chia sẻ trần" ở trên vô nghĩa.
3. **CHỈ LOOPBACK + CSDL TẠM.** Máy chủ bind `127.0.0.1`; không một byte ra mạng; KHÔNG gọi hãng,
   kể cả sandbox (V-G09-01 + V-13906-05 CHƯA CẤP). KHÔNG đụng cụm PostgreSQL :5432 (D-8: CSDL
   nghiệp vụ vẫn SQLite) và KHÔNG đụng `app/du-lieu`. Tiến trình con TỰ CHỐI CHẠY nếu CSDL của
   nó nằm ngoài thư mục tạm (mã thoát 9).
4. **KHÔNG đoán mã trạng thái 110** (D-4) và **KHÔNG mở `CHO_PHEP_LIVE`** — P0 ĐO LẠI điều thứ
   hai (đọc thuộc tính của ba lớp adapter trong một tiến trình con), không chỉ nói suông.

====== CÁC PHẦN ======
  P0  Chốt an toàn: nền tạm · chỉ loopback · CSDL là SQLite · `CHO_PHEP_LIVE` vẫn False
  P1  TRẦN QUA N TIẾN TRÌNH MÁY CHỦ THẬT (N = 1·2·4·8) — lớp HTTP                    [lỗ hổng a]
  P2  TỰ KIỂM BỘ ĐO: chạy ĐÚNG P1 trên BẢN ĐỘT BIẾN (bộ nhớ) ⇒ PHẢI ra 20·N
  P3  NGUYÊN TỬ KHÔNG QUA HTTP: N tiến trình cùng đua MỘT khoá, có hàng rào thời gian
  P4  KHỞI ĐỘNG LẠI: tiêu hết trần rồi tắt tiến trình; tiến trình MỚI phải bị chặn [lỗ hổng b]
  P5  BẤT BIẾN CŨ QUA TIẾN TRÌNH: "kiểm hết rồi mới ghi" + `dat_lai` dùng chung
  P6  ĐỐI CHỨNG DƯƠNG: PHẦN B (đếm trong CSDL từ trước) KHÔNG nhân theo số bản
  P7  HỒI QUY: hai bộ thử cũ của giới hạn tần suất phải còn xanh (chạy bằng lệnh thật)
  P8  Tổng kết + bằng chứng (lệnh thật · mã thoát thật)

CHẠY
----
    python3 app/thu/thu_g19_gioihan.py     # 0 = mọi ca ĐẠT · 1 = có ca HỎNG · 9 = chốt an toàn

PHẠM VI — NÓI RÕ CÁI NẰM NGOÀI
------------------------------
Đo: N tiến trình trên MỘT máy · loopback · SQLite WAL trong thư mục tạm · hai lỗ hổng (a) và (b)
của PHẦN A, cùng các bất biến cũ của nó. Ba lỗ hổng CÒN LẠI của PHẦN A, đo ở đây KHÔNG có:
nhiều MÁY hoặc sau bộ cân bằng tải (mỗi máy một CSDL ⇒ trần vẫn nhân — cần Redis hoặc một CSDL
chung, xem docs/G19_GIOI_HAN.md §6) · tấn công phân tán nhiều IP · PostgreSQL/Redis (D-8: cụm
:5432 là của dự án khác, CẤM đụng). Không đo tải lớn, không gọi hãng, không đoán mã 110.
"""
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # …/app
DU_AN = os.path.dirname(GOC_APP)
THU_MUC_TAM = os.path.realpath(tempfile.gettempdir())
DU_LIEU_MAC_DINH = os.path.realpath(os.path.join(GOC_APP, "du-lieu"))
DUONG_DANG_NHAP = "/api/v2/auth/dang-nhap"

DAT, HONG, BO_QUA, KHUYET = "DAT", "HONG", "BO_QUA", "KHUYET"
KY = {DAT: "✓", HONG: "✗", BO_QUA: "–", KHUYET: "!"}
KQ = []
NENS = []
CON = []
LENH = []          # (lệnh, mã thoát) — BẰNG CHỨNG dạng "lệnh thật + mã thoát thật"
GIOI_HAN_LUOT_CSDL = 0      # số dòng bảng `gioi_han_luot` đã đọc TRỰC TIẾP bằng sqlite3


# ===============================================================================================
# HẠ TẦNG: IN · GHI NHẬN · CHẠY LỆNH THẬT · DỌN DẸP
# ===============================================================================================
def ket(ma, ten, trang_thai, bang_chung=""):
    KQ.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    print("  %s [%s] %s%s" % (KY[trang_thai], ma, ten,
                              ("\n        " + bang_chung) if bang_chung else ""))
    return trang_thai


def muc(t):
    print("\n" + "─" * 78 + "\n─ %s\n" % t + "─" * 78)


def chay(lenh, *, env=None, gio=300, cwd=None):
    """Chạy một tiến trình THẬT, ghi (lệnh, mã thoát) làm bằng chứng, trả `CompletedProcess`."""
    p = subprocess.run(lenh, capture_output=True, text=True, env=env, cwd=cwd or DU_AN, timeout=gio)
    LENH.append((" ".join(lenh), p.returncode))
    return p


def nen_tam(tien_to):
    """Một nền dữ liệu TẠM. Chốt cứng: phải nằm trong thư mục tạm của hệ, không phải dữ liệu thật."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="vh-g19-%s-" % tien_to))
    if not d.startswith(THU_MUC_TAM + os.sep) or d == DU_LIEU_MAC_DINH:
        raise SystemExit("TỪ CHỐI: nền %r không nằm trong thư mục tạm" % d)
    NENS.append(d)
    return d


def dung_nen(nen, *, them_env=None):
    """Dựng schema trên nền tạm bằng ĐÚNG hai bộ cài của dự án (`migrate.py` + `khoi_tao.py`)."""
    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1")
    env.pop("VIP_THU_POSTGRES", None)          # D-8: bộ đo này KHÔNG chạm PostgreSQL
    env.update(them_env or {})
    for ten in ("migrate.py", "khoi_tao.py"):
        p = chay([sys.executable, os.path.join(GOC_APP, ten)], env=env, gio=180)
        if p.returncode:
            raise RuntimeError("%s hỏng (mã %d): %s" % (ten, p.returncode, (p.stderr or p.stdout)[-400:]))
    return env


def cong_roi():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def cho_cong(cong, p, giay=60):
    het = time.time() + giay
    while time.time() < het:
        try:
            socket.create_connection(("127.0.0.1", cong), 0.3).close()
            return True
        except OSError:
            if p.poll() is not None:
                return False
            time.sleep(0.1)
    return False


def tat_tien_trinh(p, giay=15):
    """Tắt ĐÚNG PID (CLAUDE.md §16.7: KHÔNG `pkill`, KHÔNG `killall`)."""
    if p.poll() is not None:
        return p.returncode
    p.terminate()
    try:
        return p.wait(timeout=giay)
    except subprocess.TimeoutExpired:
        p.kill()
        return p.wait(timeout=giay)


def don_dep():
    for p in list(CON):
        try:
            tat_tien_trinh(p)
        except Exception:                                                   # noqa: BLE001
            pass
    CON[:] = []
    for d in list(NENS):
        shutil.rmtree(d, ignore_errors=True)
    NENS[:] = []


# ===============================================================================================
# TIẾN TRÌNH CON — nguồn ghi ra TỆP TẠM (không phải tệp của dự án)
# ===============================================================================================
CON_KIEM = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G19/AG-02): kiểm trần tần suất ở TẦNG MÔ-ĐUN và ghi kết quả ra JSON.

Vì sao có `--mut`: bộ đo cần chạy CÙNG một phép đo trên BẢN ĐỘT BIẾN (kho trong bộ nhớ) để tự
kiểm mình. Thư mục `--mut` được chèn LÊN ĐẦU `sys.path` nên `import gioi_han` lấy bản đột biến;
trường `kho` trong kết quả ghi lại TÊN LỚP KHO đã nạp — bằng chứng bản đột biến thật sự được dùng.
"""
import argparse, json, os, sys, tempfile, time

ap = argparse.ArgumentParser()
ap.add_argument("--goc", required=True)
ap.add_argument("--mut", default="")
ap.add_argument("--che-do", choices=("kiem", "dat_lai", "xem"), default="kiem")
ap.add_argument("--endpoint", default="auth.dang_nhap")
ap.add_argument("--ip", default="9.9.9.9")
ap.add_argument("--dinh-danh", default="")
ap.add_argument("--so-lan", type=int, default=1)
ap.add_argument("--bat-dau-luc", type=float, default=0.0)
ap.add_argument("--out", required=True)
a = ap.parse_args()
sys.path.insert(0, a.goc)
if a.mut:
    sys.path.insert(0, a.mut)

import cau_hinh                                                             # noqa: E402
duong = os.path.realpath(cau_hinh.DUONG_DAN_CSDL)
if not duong.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
    sys.stderr.write("TỪ CHỐI: CSDL %r không nằm trong thư mục tạm\n" % duong)
    raise SystemExit(9)

import gioi_han                                                             # noqa: E402

dd = a.dinh_danh or None
ten_kho = type(getattr(gioi_han, "KHO", None)).__name__
if a.che_do == "xem":
    kq = gioi_han.kiem(a.endpoint, ip=a.ip, dinh_danh=dd, ghi_nhan=False)
    ra = {"che_do": "xem", "cho_phep": kq.cho_phep, "con_lai": kq.con_lai, "chieu": kq.chieu,
          "khoa": kq.khoa, "kho": ten_kho}
elif a.che_do == "dat_lai":
    gioi_han.dat_lai(a.endpoint, ip=a.ip, dinh_danh=dd)
    ra = {"che_do": "dat_lai", "xong": True, "kho": ten_kho}
else:
    while a.bat_dau_luc and time.time() < a.bat_dau_luc:      # HÀNG RÀO: cùng vào một lúc
        time.sleep(0.001)
    cho_phep, bi_chan, loi = 0, 0, []
    for _ in range(a.so_lan):
        try:
            if gioi_han.kiem(a.endpoint, ip=a.ip, dinh_danh=dd).cho_phep:
                cho_phep += 1
            else:
                bi_chan += 1
        except Exception as e:                                              # noqa: BLE001
            loi.append("%s: %s" % (type(e).__name__, e))
    ra = {"che_do": "kiem", "cho_phep": cho_phep, "bi_chan": bi_chan, "loi": loi, "kho": ten_kho}
ra["pid"] = os.getpid()
with open(a.out, "w") as f:
    json.dump(ra, f, ensure_ascii=False)
'''

CON_HAN_MUC = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G19/AG-02): ĐỐI CHỨNG DƯƠNG — xin suất đơn nháp, trần ĐẾM TRONG CSDL.

Đây là trần CÓ DÙNG CHUNG đã có từ trước (PHẦN B của `gioi_han`). Nó KHÔNG được nhân theo số
bản. Nếu ở đây cũng ra "nhân", thì lỗi nằm ở BỘ ĐO chứ không ở mã sản phẩm.
"""
import argparse, json, os, sys, tempfile, time

ap = argparse.ArgumentParser()
ap.add_argument("--goc", required=True)
ap.add_argument("--tenant", type=int, required=True)
ap.add_argument("--so-lan", type=int, default=40)
ap.add_argument("--bat-dau-luc", type=float, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
sys.path.insert(0, a.goc)

import cau_hinh                                                             # noqa: E402
duong = os.path.realpath(cau_hinh.DUONG_DAN_CSDL)
if not duong.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
    sys.stderr.write("TỪ CHỐI: CSDL %r không nằm trong thư mục tạm\n" % duong)
    raise SystemExit(9)

import gioi_han                                                             # noqa: E402

tran = gioi_han.tran_cua(a.tenant)["tran_don_nhap_thang"]
gioi_han.da_dung(a.tenant)          # tạo bảng TRƯỚC hàng rào, tránh đua CREATE TABLE
while time.time() < a.bat_dau_luc:
    time.sleep(0.001)
dat_duoc, bi_chan, loi = 0, 0, []
for _ in range(a.so_lan):
    try:
        gioi_han.dat_truoc_don_nhap(a.tenant, 1)
        dat_duoc += 1
    except gioi_han.VuotHanMucNhap:
        bi_chan += 1
    except Exception as e:                                                  # noqa: BLE001
        loi.append("%s: %s" % (type(e).__name__, e))
with open(a.out, "w") as f:
    json.dump({"pid": os.getpid(), "tran": tran, "dat_duoc": dat_duoc, "bi_chan": bi_chan,
               "loi": loi}, f, ensure_ascii=False)
'''

CHAY_MAY_CHU = r'''# -*- coding: utf-8 -*-
"""BỘ KHỞI ĐỘNG máy chủ cho phép đo G19/AG-02 — để chèn được BẢN ĐỘT BIẾN lên đầu `sys.path`.

Chạy thẳng `python3 app/server.py` thì `sys.path[0]` LUÔN là `app/`, nên một bản `gioi_han.py`
đột biến ở thư mục khác không bao giờ được nạp. `runpy.run_path` giữ `sys.argv` (cổng vẫn là
`sys.argv[1]`) và `__name__ == "__main__"`, nên `server.py` chạy y như được gọi trực tiếp.
"""
import os, runpy, sys

goc = os.environ["VIP_G19_GOC_APP"]
mut = os.environ.get("VIP_G19_MUT") or ""
sys.path.insert(0, goc)
if mut:
    sys.path.insert(0, mut)
runpy.run_path(os.path.join(goc, "server.py"), run_name="__main__")
'''

CON_CHOT = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G19/AG-02): ĐỌC `CHO_PHEP_LIVE` của ba lớp adapter — phải vẫn là False."""
import json, os, sys

sys.path.insert(0, sys.argv[1])
import adapter, adapter_jt, adapter_vtp                                  # noqa: E402

# Đọc thuộc tính LỚP, không phải thuộc tính mô-đun: cờ nằm trong ba lớp này.
with open(sys.argv[2], "w") as f:
    json.dump({"adapter.CarrierAdapter": bool(adapter.CarrierAdapter.CHO_PHEP_LIVE),
               "adapter_jt.AdapterJT": bool(adapter_jt.AdapterJT.CHO_PHEP_LIVE),
               "adapter_vtp.AdapterVTP": bool(adapter_vtp.AdapterVTP.CHO_PHEP_LIVE),
               "cho_phep_live_env": os.environ.get("VIP_HUB_CHO_PHEP_LIVE", "(không đặt)")}, f)
'''


def ghi_con(nen, ten, nguon):
    duong = os.path.join(nen, ten)
    with open(duong, "w") as f:
        f.write(nguon)
    return duong


def dung_ban_dot_bien(nen):
    """BẢN ĐỘT BIẾN CỐ Ý của `gioi_han`: quay LẠI đúng khuôn cũ — kho trong BỘ NHỚ một tiến trình.

    Phần QUYẾT ĐỊNH (chính sách, thứ tự kiểm, luật 4 "kiểm hết rồi mới ghi", cửa sổ trượt, thời
    gian phạt) giữ NGUYÊN từng dòng của mã thật — bản đột biến chỉ THAY LỚP KHO. Nhờ vậy phép đo
    ở P1/P2/P4 tách được đúng MỘT biến: trạng thái nằm ở đâu.

    Trên cây CHƯA vá (kho còn nằm trong bộ nhớ), tệp này vẫn dựng được: `gioi_han` không có tên
    `KHO`, nên phần gán ở cuối vô hại và bản "đột biến" hành xử y như mã thật — đúng ý đồ: phép
    đo phải nói "nhân theo số bản" ở CẢ HAI.
    """
    goc = open(os.path.join(GOC_APP, "gioi_han.py"), encoding="utf-8").read()
    thu_muc = os.path.join(nen, "mut")
    os.makedirs(thu_muc, exist_ok=True)
    duong = os.path.join(thu_muc, "gioi_han.py")
    with open(duong, "w", encoding="utf-8") as f:
        f.write(goc + BAN_DOT_BIEN)
    return thu_muc


BAN_DOT_BIEN = '''

# ===============================================================================================
# BẢN ĐỘT BIẾN CỐ Ý — CHỈ dùng cho ĐỐI CHỨNG ÂM của bộ đo G19/AG-02, KHÔNG bao giờ là mã sản phẩm.
# Đúng khuôn TRƯỚC KHI VÁ: trạng thái nằm trong BỘ NHỚ MỘT TIẾN TRÌNH (không dùng chung, mất khi
# khởi động lại). Giao diện y hệt `KhoCSDL` để phần quyết định phía trên không đổi một dòng nào.
# ===============================================================================================
import contextlib as _ct
import threading as _th


class _KhoBoNho:
    def __init__(self):
        self._k = _th.Lock()
        self._luot = {}
        self._chan = {}

    def _dam_bao_bang(self):
        return None

    @_ct.contextmanager
    def giao_dich(self):
        with self._k:
            yield self

    def dem(self, khoa, tu_moc):
        return sum(1 for m in self._luot.get(khoa, ()) if m > tu_moc)

    def moc_cu_nhat(self, khoa, tu_moc):
        ds = [m for m in self._luot.get(khoa, ()) if m > tu_moc]
        return min(ds) if ds else None

    def ghi_luot(self, khoa, moc, tu_moc, tran):
        if self.dem(khoa, tu_moc) >= tran:
            return False
        self._luot.setdefault(khoa, []).append(moc)
        return True

    def doc_chan(self, khoa):
        return self._chan.get(khoa)

    def ghi_chan(self, khoa, den):
        self._chan[khoa] = den

    def xoa(self, khoa):
        self._luot.pop(khoa, None)
        self._chan.pop(khoa, None)

    def xoa_het(self):
        self._luot.clear()
        self._chan.clear()

    def so_khoa(self):
        return len(self._luot) + len(self._chan)

    def don(self, bay):
        # DỌN LƯỜI, đúng như bản cũ: chỉ quét khi số khoá VƯỢT trần. Quét mọi lượt thì bản đột
        # biến bị chính bộ đôi của bộ thử làm chậm, và phép đo CHI PHÍ ở docs sẽ so sai.
        if self.so_khoa() <= TOI_DA_KHOA:
            return
        for k in list(self._luot):
            self._luot[k] = [m for m in self._luot[k] if m > bay - 3600]
            if not self._luot[k]:
                self._luot.pop(k, None)
        for k in list(self._chan):
            if self._chan[k] <= bay:
                self._chan.pop(k, None)

    def thong_ke(self):
        return {"so_bucket": self.so_khoa(), "so_dang_chan": len(self._chan),
                "tran_bucket": TOI_DA_KHOA}


KHO = _KhoBoNho()
'''


# ===============================================================================================
# MÁY CHỦ THẬT + LƯỢT GỌI HTTP (chỉ loopback)
# ===============================================================================================
def mo_may_chu(nen, *, mut_dir=None, tien_to="sv"):
    c = cong_roi()
    log = os.path.join(nen, "%s-%d.log" % (tien_to, c))
    f = open(log, "w")
    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1",
               VIP_G19_GOC_APP=GOC_APP, VIP_G19_MUT=mut_dir or "")
    env.pop("VIP_THU_POSTGRES", None)
    if mut_dir:
        lenh = [sys.executable, os.path.join(nen, "chay_may_chu.py"), str(c)]
    else:
        lenh = [sys.executable, os.path.join(GOC_APP, "server.py"), str(c)]
    p = subprocess.Popen(lenh, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
    CON.append(p)
    if not cho_cong(c, p):
        raise RuntimeError("máy chủ không mở cổng %d (pid %d):\n%s"
                           % (c, p.pid, open(log).read()[-500:]))
    return {"p": p, "cong": c, "log": log, "nen": nen, "mut": bool(mut_dir)}


def goi_dang_nhap(cong, ten):
    """MỘT lượt đăng nhập SAI. Tên đăng nhập KHÁC NHAU mỗi lượt để chỉ chiều `ip` cộng.

    (Dùng lại một tên thì chiều `dinh_danh` — trần 12, có phạt 900 giây — chặn TRƯỚC chiều `ip`
    trần 20, và phép đo sẽ đọc nhầm chiều. Đây là bài học G18/AG-02 đã ghi lại.)
    """
    d = json.dumps({"ten_dang_nhap": ten, "mat_khau": "sai"}).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (cong, DUONG_DANG_NHAP), data=d,
                               method="POST")
    r.add_header("X-Requested-With", "VIPHub")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as f:
            return f.status, f.read(), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def bom_tuan_tu(sv, *, toi_da_moi_ban, nhan=""):
    """Bắn LẦN LƯỢT, VÒNG TRÒN qua các bản: mỗi bản đúng một lượt mỗi vòng.

    Vòng tròn để N tiến trình cùng SỐNG và cùng phục vụ. Một bản tự dừng khi nhận 429 đầu tiên
    (hết ngân sách), nên tổng số lượt được cho qua là TẤT ĐỊNH.
    """
    dem = [0] * len(sv)
    con = [True] * len(sv)
    ct = [[] for _ in sv]
    for vong in range(toi_da_moi_ban):
        for k in range(len(sv)):
            if not con[k]:
                continue
            ma, than, hdr = goi_dang_nhap(sv[k]["cong"], "g19-%s%s-%d-%d" % (nhan, k, vong, os.getpid()))
            o = {"ma": ma, "retry_after": hdr.get("Retry-After"),
                 "gioi_han": hdr.get("X-RateLimit-Limit"), "chieu": None}
            if ma == 401:                       # 401 = sai thông tin đăng nhập = ĐÃ QUA trần
                dem[k] += 1
            elif ma == 429:
                try:
                    o["chieu"] = json.loads(than.decode("utf-8")).get("chieu")
                except (ValueError, UnicodeDecodeError):
                    pass
                con[k] = False
            else:
                o["la"] = "mã lạ"
            ct[k].append(o)
    return dem, ct


def doc_log_may_chu(duong_dan):
    """Đọc log JSON của MỘT máy chủ → [(pid, mốc, đường, mã HTTP)] + số dòng không parse được."""
    ra, hong = [], 0
    if not os.path.exists(duong_dan):
        return ra, hong
    with open(duong_dan, "r", encoding="utf-8", errors="replace") as f:
        for dong in f:
            dong = dong.strip()
            if not dong.startswith("{"):
                continue
            try:
                o = json.loads(dong)
            except ValueError:
                hong += 1
                continue
            if o.get("loai") == "yeu_cau" and o.get("pid"):
                ra.append((int(o["pid"]), str(o.get("luc", "")), str(o.get("duong", "")),
                           o.get("ma_http")))
    return ra, hong


# ===============================================================================================
# P0 — CHỐT AN TOÀN
# ===============================================================================================
def p0_chot_an_toan(nen):
    muc("P0. CHỐT AN TOÀN — nền tạm · chỉ loopback · SQLite · `CHO_PHEP_LIVE` vẫn False")
    print("  thư mục tạm của hệ : %s" % THU_MUC_TAM)
    print("  dữ liệu THẬT (cấm): %s" % DU_LIEU_MAC_DINH)
    print("  Python             : %s · SQLite %s" % (sys.version.split()[0],
                                                      sqlite3.sqlite_version))
    truoc = os.environ.get("VIP_HUB_DATA")
    if truoc and not os.path.realpath(truoc).startswith(THU_MUC_TAM + os.sep):
        print("  TỪ CHỐI: VIP_HUB_DATA=%r nằm NGOÀI thư mục tạm — không chạy trên dữ liệu thật."
              % truoc)
        raise SystemExit(9)
    ket("P0a", "Mọi nền đo nằm trong thư mục TẠM, không phải dữ liệu thật",
        DAT if (THU_MUC_TAM != DU_LIEU_MAC_DINH and nen.startswith(THU_MUC_TAM + os.sep)) else HONG,
        "nền tạm: %s · dữ liệu thật: %s" % (nen, DU_LIEU_MAC_DINH))
    # (b) ĐO THẬT: tệp CSDL của nền là SQLite (đọc 16 byte đầu), không phải PostgreSQL.
    with open(os.path.join(nen, "hub.db"), "rb") as f:
        dau = f.read(16)
    ket("P0b", "CSDL nghiệp vụ của nền là SQLite thật (D-8: KHÔNG chuyển sang PostgreSQL)",
        DAT if dau == b"SQLite format 3\x00" else HONG,
        "16 byte đầu của %s: %r · bộ đo chỉ mở kết nối tới `127.0.0.1` và tệp trong thư mục tạm; "
        "không có cổng :5432 nào được mở" % (os.path.join(nen, "hub.db"), dau))
    con = ghi_con(nen, "con_chot.py", CON_CHOT)
    ra = os.path.join(nen, "chot.json")
    p = chay([sys.executable, con, GOC_APP, ra], gio=120,
             env=dict(os.environ, VIP_HUB_DATA=nen))
    o = {}
    if os.path.exists(ra):
        with open(ra) as f:
            o = json.load(f)
    ket("P0c", "`CHO_PHEP_LIVE` của CẢ BA lớp adapter vẫn là False (bộ đo KHÔNG mở nó)",
        DAT if (p.returncode == 0 and o
                and not any(o[k] for k in ("adapter.CarrierAdapter", "adapter_jt.AdapterJT",
                                           "adapter_vtp.AdapterVTP"))) else HONG,
        "tiến trình con ĐỌC THẲNG thuộc tính lớp: %s (mã thoát %d) · biến môi trường "
        "`VIP_HUB_CHO_PHEP_LIVE` = %r%s"
        % (o or "?", p.returncode, os.environ.get("VIP_HUB_CHO_PHEP_LIVE", "(không đặt)"),
           "" if p.returncode == 0 else " · đầu ra: %r"
           % (((p.stdout or "") + (p.stderr or ""))[-300:])))
    ket("P0d", "Máy chủ đo bind `127.0.0.1`, không mở cổng ra ngoài",
        DAT, "`VIP_HUB_BIND=127.0.0.1` được đặt tường minh cho MỌI tiến trình con; cổng lấy từ "
             "`bind(('127.0.0.1', 0))` nên không tranh cổng của ai. Phạm vi KHÔNG gồm: nhiều máy, "
             "sau cân bằng tải, TLS, cụm PostgreSQL :5432.")
    return True


# ===============================================================================================
# P1 + P2 — TRẦN QUA N TIẾN TRÌNH MÁY CHỦ THẬT · và ĐỐI CHỨNG ÂM trên bản đột biến
# ===============================================================================================
def doc_tran_khai_bao(nen):
    """Trần KHAI BÁO đọc từ CHÍNH máy chủ (header `X-RateLimit-Limit` trên lượt 429).

    Máy chủ dùng MỘT LẦN rồi tắt: đọc trần bằng một lượt gọi vào chính bản sắp đo là tự trừ suất
    của nó (bài học HỎNG GIẢ N-05 của G18/AG-02). Trả `(trần, số lượt đã cho qua, mã, chiều)`.
    """
    sv = mo_may_chu(nen, tien_to="do-tran")
    try:
        for i in range(200):
            ma, than, hdr = goi_dang_nhap(sv["cong"], "g19-do-tran-%d-%d" % (i, os.getpid()))
            if ma == 429:
                chieu = None
                try:
                    chieu = json.loads(than.decode("utf-8")).get("chieu")
                except (ValueError, UnicodeDecodeError):
                    pass
                return int(hdr.get("X-RateLimit-Limit") or 0), i, ma, chieu
        return 0, 200, "khong-thay-429", None
    finally:
        tat_tien_trinh(sv["p"])


def do_tran_http(nen, N, *, khai_bao, mut_dir=None, nhan=""):
    """N tiến trình máy chủ THẬT cùng một CSDL, cùng IP; bắn vòng tròn; trả kết quả đo."""
    sv = [mo_may_chu(nen, mut_dir=mut_dir, tien_to=nhan or "sv") for _ in range(N)]
    try:
        dem, ct = bom_tuan_tu(sv, toi_da_moi_ban=khai_bao + 3, nhan=nhan)
        pids, hong_log = set(), 0
        for s in sv:
            dong, hong = doc_log_may_chu(s["log"])
            hong_log += hong
            for pid, _luc, duong, _ma in dong:
                if duong == DUONG_DANG_NHAP:
                    pids.add(pid)
        return {"N": N, "dem": dem, "ct": ct, "pids": sorted(pids), "hong_log": hong_log,
                "pid_con": [s["p"].pid for s in sv],
                "da_chan": [bool(x) and x[-1]["ma"] == 429 for x in ct],
                "ma_la": [[o for o in x if o["ma"] not in (401, 429)] for x in ct]}
    finally:
        for s in sv:
            tat_tien_trinh(s["p"])


def p1_p2_tran_http(nen_goc, khai_bao):
    muc("P1. TRẦN QUA N TIẾN TRÌNH MÁY CHỦ THẬT (N = 1·2·4·8) — LỖ HỔNG (a)")
    ket("P1.0", "Máy chủ tự nói trần và tự chặn ở đúng đó (máy chủ dùng một lần)",
        DAT if (khai_bao[0] > 0 and khai_bao[1] == khai_bao[0] and khai_bao[3] == "ip") else HONG,
        "header `X-RateLimit-Limit` = %d và số lượt thực sự cho qua trước khi trả 429 = %d "
        "· chiều bị chặn = %r · mã lượt chặn = %s. Tên đăng nhập KHÁC NHAU mỗi lượt để chắc chắn "
        "chiều chặn là `ip` (trần 20), không phải `dinh_danh` (trần 12). Nếu ca này lệch thì bộ "
        "đếm lượt của bộ đo sai và mọi ca dưới vô nghĩa."
        % (khai_bao[0], khai_bao[1], khai_bao[3], khai_bao[2]))
    ket_qua, ket_qua_mut = {}, {}
    for N in (1, 2, 4, 8):
        nen = nen_tam("tran%d" % N)
        dung_nen(nen)
        ket_qua[N] = do_tran_http(nen, N, khai_bao=khai_bao[0], nhan="t%d" % N)
    for N in (1, 2, 4, 8):
        nen = nen_tam("mut%d" % N)
        dung_nen(nen)
        mut = dung_ban_dot_bien(nen)
        ghi_con(nen, "chay_may_chu.py", CHAY_MAY_CHU)
        ket_qua_mut[N] = do_tran_http(nen, N, khai_bao=khai_bao[0], mut_dir=mut, nhan="m%d" % N)

    for N in (1, 2, 4, 8):
        k = ket_qua[N]
        tong = sum(k["dem"])
        dung = (tong == khai_bao[0] and all(k["da_chan"]) and not any(k["ma_la"])
                and len(k["pids"]) == N)
        ket("P1.%d" % N, "N=%d tiến trình CÙNG một CSDL: TỔNG cho qua = trần khai báo (%d), "
            "KHÔNG nhân theo số bản" % (N, khai_bao[0]),
            DAT if dung else HONG,
            "từng bản cho qua %s ⇒ TỔNG %d (khai báo %d) · mỗi bản kết thúc bằng 429: %s · "
            "%d pid khác nhau đã phục vụ (pid con %s) · lượt mã lạ: %s · log hỏng: %d"
            % (k["dem"], tong, khai_bao[0], k["da_chan"], len(k["pids"]), k["pid_con"],
               k["ma_la"], k["hong_log"]))

    muc("P2. TỰ KIỂM BỘ ĐO — chạy ĐÚNG P1 trên BẢN ĐỘT BIẾN (kho trong bộ nhớ)")
    print("  Bản đột biến giữ nguyên phần quyết định của `gioi_han`, chỉ đổi LỚP KHO về đúng khuôn")
    print("  trước khi vá. Nếu phép đo ở P1 là MÙ thì ở đây nó cũng sẽ ra %d — và bộ đo tự báo HỎNG."
          % khai_bao[0])
    for N in (1, 2, 4, 8):
        k = ket_qua_mut[N]
        tong = sum(k["dem"])
        dat = (tong == N * khai_bao[0] and not any(k["ma_la"]))
        ket("P2.%d" % N, "ĐỐI CHỨNG ÂM N=%d: bản đột biến PHẢI ra %d×%d = %d (bộ đo THẤY được "
            "việc nhân)" % (N, N, khai_bao[0], N * khai_bao[0]),
            DAT if dat else HONG,
            "từng bản cho qua %s ⇒ TỔNG %d · lượt mã lạ: %s. CÙNG bộ bắn, CÙNG trần khai báo, "
            "CÙNG số bản — chỉ khác LỚP KHO. Tổng ở P1.%d là %d: hai số KHÁC NHAU nghĩa là phép "
            "đo phân biệt được 'đếm chung' với 'đếm riêng'."
            % (k["dem"], tong, k["ma_la"], N, sum(ket_qua[N]["dem"])))
    return ket_qua, ket_qua_mut


# ===============================================================================================
# P3 — NGUYÊN TỬ KHÔNG QUA HTTP: N tiến trình đua MỘT khoá, có hàng rào
# ===============================================================================================
def p3_nguyen_tu(nen, *, khai_bao, so_lan_moi_tien_trinh=30, N=8, vong=3):
    global GIOI_HAN_LUOT_CSDL
    muc("P3. NGUYÊN TỬ KHÔNG QUA HTTP — %d tiến trình đua MỘT khoá, hàng rào thời gian, %d vòng"
        % (N, vong))
    con = ghi_con(nen, "con_kiem.py", CON_KIEM)
    env = dung_nen(nen) if not os.path.exists(os.path.join(nen, "hub.db")) else None
    env = env or dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1")
    dung = True
    for v in range(vong):
        # MỖI VÒNG MỘT KHOÁ RIÊNG (một IP khác): trần là ngân sách, tiêu hết ở vòng trước thì
        # vòng sau cho qua 0 lượt — đo tiếp trên cùng khoá là đo NHẦM "hết ngân sách" thành
        # "nguyên tử hỏng". (Đã dính đúng lỗi này ở lượt chạy đầu của bộ đo.)
        ip = "203.0.113.%d" % (10 + v)
        # TẠO BẢNG TRƯỚC hàng rào: 8 tiến trình cùng `CREATE TABLE IF NOT EXISTS` là một lượt
        # đua DDL không liên quan tới thứ đang đo — thua nó sẽ bị đọc nhầm thành "trần hỏng".
        p = chay([sys.executable, con, "--goc", GOC_APP, "--ip", ip, "--so-lan", "0",
                  "--che-do", "xem", "--out", os.path.join(nen, "p3-nap-%d.json" % v)],
                 env=env, gio=120)
        if p.returncode:
            ket("P3.%d" % v, "vòng %d: nạp trước bảng" % v, HONG,
                "mã thoát %d: %s" % (p.returncode, (p.stderr or p.stdout)[-300:]))
            dung = False
            continue
        bat_dau = time.time() + 1.5
        outs = [os.path.join(nen, "p3-%d-%d.json" % (v, k)) for k in range(N)]
        ps = []
        for k in range(N):
            ps.append(subprocess.Popen(
                [sys.executable, con, "--goc", GOC_APP, "--ip", ip,
                 "--so-lan", str(so_lan_moi_tien_trinh), "--bat-dau-luc", "%.3f" % bat_dau,
                 "--out", outs[k]], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, cwd=DU_AN))
            CON.append(ps[-1])
        for x in ps:
            x.wait(timeout=300)
        kqs, thieu = [], 0
        for o in outs:
            if os.path.exists(o):
                with open(o) as f:
                    kqs.append(json.load(f))
            else:
                thieu += 1
        tong = sum(x["cho_phep"] for x in kqs)
        loi = [l for x in kqs for l in x["loi"]]
        kho = sorted({x.get("kho") for x in kqs})
        # ĐỐI CHỨNG ĐỘC LẬP: đếm THẲNG số dòng trong bảng kho bằng sqlite3, không qua hàm của
        # `gioi_han` — bộ đếm không được tự làm chứng cho chính nó (§12.1).
        kn = sqlite3.connect(os.path.join(nen, "hub.db"))
        so_dong = kn.execute("SELECT COUNT(*) FROM gioi_han_luot WHERE khoa=?",
                            ("auth.dang_nhap|ip|" + ip,)).fetchone()[0] \
            if kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='gioi_han_luot'"
                          ).fetchone()[0] else -1
        kn.close()
        GIOI_HAN_LUOT_CSDL = max(GIOI_HAN_LUOT_CSDL, so_dong)
        ok = (thieu == 0 and tong == khai_bao and not loi and so_dong == khai_bao
              and kho == ["KhoCSDL"])
        dung = dung and ok
        print("      vòng %d: %d tiến trình × %d lượt (đua cùng lúc) ⇒ cho qua TỔNG %d, "
              "bảng CSDL có %d dòng, lớp kho %s, lỗi %s"
              % (v, N, so_lan_moi_tien_trinh, tong, so_dong, kho, loi[:2]))
        if not ok:
            ket("P3.%d" % v, "vòng %d" % v, HONG,
                "cho qua %d (phải đúng %d) · %d tiến trình không trả kết quả · lỗi %s · "
                "số dòng CSDL %d" % (tong, khai_bao, thieu, loi[:3], so_dong))
            dung = False
    if dung:
        ket("P3", "%d vòng × %d tiến trình THẬT đua cùng lúc: TỔNG cho qua = trần và số dòng "
            "trong CSDL = trần (đếm độc lập bằng sqlite3)" % (vong, N), DAT,
            "%d vòng, mỗi vòng %d tiến trình × %d lượt, hàng rào thời gian chung · mọi vòng cho "
            "qua ĐÚNG %d · đếm thẳng bảng `gioi_han_luot` cũng đúng %d dòng ⇒ không có khe hở "
            "giữa đọc và ghi." % (vong, N, so_lan_moi_tien_trinh, khai_bao, khai_bao))
    return dung


# ===============================================================================================
# P4 — KHỞI ĐỘNG LẠI: tiêu hết trần rồi tắt tiến trình, tiến trình MỚI phải bị chặn
# ===============================================================================================
def p4_khoi_dong_lai(nen, nen_mut, *, khai_bao):
    muc("P4. KHỞI ĐỘNG LẠI — LỖ HỔNG (b): tiêu hết trần, TẮT tiến trình, tiến trình MỚI phải bị chặn")
    con = ghi_con(nen, "con_kiem.py", CON_KIEM)
    ip = "198.51.100.7"

    def mot_tien_trinh(env, mut, so_lan, nhan, bat_dau=0.0, che_do="kiem"):
        ra = os.path.join(env["VIP_HUB_DATA"], "p4-%s.json" % nhan)
        lenh = [sys.executable, con, "--goc", GOC_APP, "--ip", ip, "--so-lan", str(so_lan),
                "--che-do", che_do, "--bat-dau-luc", "%.3f" % bat_dau, "--out", ra]
        if mut:
            lenh += ["--mut", mut]
        p = chay(lenh, env=env, gio=180)
        with open(ra) as f:
            o = json.load(f)
        o["ma_thoat"] = p.returncode
        return o

    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1")
    env_mut = dict(os.environ, VIP_HUB_DATA=nen_mut, VIP_HUB_BIND="127.0.0.1")
    a = mot_tien_trinh(env, None, khai_bao, "a")                      # tiêu hết trần
    b = mot_tien_trinh(env, None, 1, "b")                             # TIẾN TRÌNH MỚI
    xem = mot_tien_trinh(env, None, 0, "xem", che_do="xem")
    ket("P4.1", "TIẾN TRÌNH MỚI (đã khởi động lại) gửi 1 lượt sau khi trần đã tiêu hết ⇒ BỊ CHẶN",
        DAT if (a["cho_phep"] == khai_bao and a["bi_chan"] == 0 and b["cho_phep"] == 0
                and b["bi_chan"] == 1 and not b["loi"] and xem["cho_phep"] is False) else HONG,
        "tiến trình A (pid %d, lớp kho %s): cho qua %d/%d lượt ⇒ trần đã tiêu hết · tiến trình B "
        "MỚI (pid %d, mã thoát %d): cho qua %d, BỊ CHẶN %d · lượt chỉ-xem trên tiến trình thứ ba: "
        "cho phép=%s, chiều=%s, còn lại=%s. Bộ đếm nằm trong CSDL nên sống qua cái chết của tiến "
        "trình." % (a["pid"], a["kho"], a["cho_phep"], khai_bao, b["pid"], b["ma_thoat"],
                    b["cho_phep"], b["bi_chan"], xem["cho_phep"], xem["chieu"], xem["con_lai"]))

    # ĐỐI CHỨNG ÂM cho (b): bản đột biến (kho trong bộ nhớ) — khởi động lại là trần về 0.
    mut = dung_ban_dot_bien(nen_mut)
    am_a = mot_tien_trinh(env_mut, mut, khai_bao, "ma")
    am_b = mot_tien_trinh(env_mut, mut, 1, "mb")
    ket("P4.2", "ĐỐI CHỨNG ÂM: bản đột biến (bộ nhớ) khởi động lại thì VƯỢT ĐƯỢC trần",
        DAT if (am_a["cho_phep"] == khai_bao and am_b["cho_phep"] == 1 and am_b["bi_chan"] == 0
                and am_a["kho"] == "_KhoBoNho" and am_b["kho"] == "_KhoBoNho") else HONG,
        "bản đột biến, tiến trình A (pid %d, lớp kho %s) tiêu %d suất rồi TẮT; tiến trình B MỚI "
        "(pid %d) cho qua %d lượt, bị chặn %d ⇒ cửa lách (b) CÓ THẬT và bộ đo THẤY nó. Không có "
        "ca này thì ca P4.1 xanh không nói lên điều gì."
        % (am_a["pid"], am_a["kho"], am_a["cho_phep"], am_b["pid"], am_b["cho_phep"],
           am_b["bi_chan"]))

    # Và một lượt ở LỚP HTTP thật: hai máy chủ NỐI TIẾP nhau trên cùng một nền.
    nen_do_tran_http = nen_tam("do-tran-http")
    dung_nen(nen_do_tran_http)
    tb, dem_do, ma_do, chieu = doc_tran_khai_bao(nen_do_tran_http)
    nen_http = nen_tam("restart-http")
    dung_nen(nen_http)
    sv1 = mo_may_chu(nen_http, tien_to="r1")
    try:
        dem1, ct1 = bom_tuan_tu([sv1], toi_da_moi_ban=tb + 2, nhan="r1")
    finally:
        tat_tien_trinh(sv1["p"])
    sv2 = mo_may_chu(nen_http, tien_to="r2")
    try:
        ma, than, hdr = goi_dang_nhap(sv2["cong"], "g19-restart-sau-%d" % os.getpid())
    finally:
        tat_tien_trinh(sv2["p"])
    ket("P4.3", "LỚP HTTP: tắt máy chủ rồi mở máy chủ MỚI trên cùng CSDL ⇒ lượt đầu đã bị 429",
        DAT if (dem1[0] == tb and ma == 429) else HONG,
        "máy chủ #1 (pid %d) cho qua %d lượt rồi trả 429 · máy chủ #2 (pid %d) nhận lượt ĐẦU "
        "TIÊN = %d, `Retry-After`=%s, chiều=%s. Trần đọc từ chính máy chủ: %d."
        % (sv1["p"].pid, dem1[0], sv2["p"].pid, ma, hdr.get("Retry-After"),
           (json.loads(than.decode("utf-8")).get("chieu")
            if ma == 429 and than else None), tb))
    return True


# ===============================================================================================
# P5 — BẤT BIẾN CŨ QUA TIẾN TRÌNH
# ===============================================================================================
def p5_bat_bien(nen):
    muc("P5. BẤT BIẾN CŨ QUA TIẾN TRÌNH — 'kiểm hết rồi mới ghi' + `dat_lai` dùng chung")
    con = ghi_con(nen, "con_kiem.py", CON_KIEM)
    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1")
    ip, dd = "192.0.2.44", "nan-nhan-g19"

    def chay_con(so_lan, nhan, *, che_do="kiem", ip_=ip, dd_=dd, bat_dau=0.0):
        ra = os.path.join(nen, "p5-%s.json" % nhan)
        lenh = [sys.executable, con, "--goc", GOC_APP, "--ip", ip_, "--dinh-danh", dd_,
                "--so-lan", str(so_lan), "--che-do", che_do, "--out", ra]
        if bat_dau:
            lenh += ["--bat-dau-luc", "%.3f" % bat_dau]
        p = chay(lenh, env=env, gio=180)
        with open(ra) as f:
            o = json.load(f)
        o["ma_thoat"] = p.returncode
        return o

    chay_con(0, "nap", che_do="xem")     # nạp trước bảng (có CHẠM kho), tránh đua DDL
    # (a) 4 tiến trình cùng đua MỘT định danh (trần 12) trên CÙNG một IP: 12 lượt qua, phần còn
    #     lại bị chặn. Luật 4 nói lượt bị chặn KHÔNG được cộng vào chiều `ip` của người khác.
    bat_dau = time.time() + 1.5
    ps = []
    for k in range(4):
        ra = os.path.join(nen, "p5-a-%d.json" % k)
        ps.append(subprocess.Popen(
            [sys.executable, con, "--goc", GOC_APP, "--ip", ip, "--dinh-danh", dd,
             "--so-lan", "6", "--bat-dau-luc", "%.3f" % bat_dau, "--out", ra],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=DU_AN))
        CON.append(ps[-1])
    for x in ps:
        x.wait(timeout=300)
    kqs = []
    for k in range(4):
        with open(os.path.join(nen, "p5-a-%d.json" % k)) as f:
            kqs.append(json.load(f))
    tong_qua = sum(x["cho_phep"] for x in kqs)
    xem = chay_con(0, "xem-ip", che_do="xem", dd_="")
    ket("P5.1", "4 tiến trình đua một định danh: đúng 12 lượt qua, và 12 lượt bị chặn KHÔNG cộng "
        "vào chiều `ip`", DAT if (tong_qua == 12 and xem["con_lai"] == 8) else HONG,
        "4 tiến trình × 6 lượt = 24 lượt cho cùng định danh %r ⇒ cho qua TỔNG %d (trần định danh "
        "= 12) · chiều `ip` sau đó còn lại %s/20 (nếu lượt bị chặn bị cộng nhầm thì con số này là "
        "0 chứ không phải 8 — bất biến 'kiểm hết rồi mới ghi' phải đúng qua CẢ tiến trình)."
        % (dd, tong_qua, xem["con_lai"]))

    # (b) `dat_lai` ở tiến trình KHÁC phải xoá được bộ đếm của tiến trình đã tiêu lượt.
    ip2, dd2 = "192.0.2.45", "dat-lai-g19"
    chay_con(11, "b-tieu", ip_=ip2, dd_=dd2)
    truoc = chay_con(0, "b-truoc", che_do="xem", ip_=ip2, dd_=dd2)
    chay_con(0, "b-dat-lai", che_do="dat_lai", ip_=ip2, dd_=dd2)
    sau = chay_con(0, "b-sau", che_do="xem", ip_=ip2, dd_=dd2)
    ket("P5.2", "`dat_lai` ở MỘT tiến trình xoá được bộ đếm cho MỌI tiến trình (dùng chung kho)",
        DAT if (truoc["con_lai"] == 1 and sau["con_lai"] == 12 and sau["cho_phep"]) else HONG,
        "sau 11 lượt (trần định danh 12): còn lại %s · tiến trình THỨ HAI gọi `dat_lai` · "
        "lượt chỉ-xem ở tiến trình THỨ BA: còn lại %s, cho phép=%s. Đây là đường 'đăng nhập thành "
        "công thì xoá bộ đếm' của `server.py` — nó phải xoá được cả khi lượt đăng nhập rơi vào "
        "một bản máy chủ KHÁC." % (truoc["con_lai"], sau["con_lai"], sau["cho_phep"]))
    return True


# ===============================================================================================
# P6 — ĐỐI CHỨNG DƯƠNG: PHẦN B (đếm trong CSDL từ trước) không nhân theo số bản
# ===============================================================================================
def p6_doi_chung_duong(nen, *, N=4, so_lan=40):
    muc("P6. ĐỐI CHỨNG DƯƠNG — PHẦN B (trần đếm trong CSDL từ trước) KHÔNG nhân theo số bản")
    env = dung_nen(nen)
    kn = sqlite3.connect(os.path.join(nen, "hub.db"))
    kn.execute("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
               ("g19-pb", "Tenant PB", "free", "2026-10-15 00:00:00+0700"))
    kn.commit()
    tenant = kn.execute("SELECT id FROM tenants WHERE code='g19-pb'").fetchone()[0]
    kn.close()
    con = ghi_con(nen, "con_han_muc.py", CON_HAN_MUC)
    bat_dau = time.time() + 2.0
    outs = [os.path.join(nen, "pb-%d.json" % k) for k in range(N)]
    ps = []
    for k in range(N):
        ps.append(subprocess.Popen(
            [sys.executable, con, "--goc", GOC_APP, "--tenant", str(tenant),
             "--so-lan", str(so_lan), "--bat-dau-luc", "%.3f" % bat_dau, "--out", outs[k]],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=DU_AN))
        CON.append(ps[-1])
    for x in ps:
        x.wait(timeout=300)
    kqs = []
    for o in outs:
        if os.path.exists(o):
            with open(o) as f:
                kqs.append(json.load(f))
    tong_dat = sum(x["dat_duoc"] for x in kqs)
    tong_chan = sum(x["bi_chan"] for x in kqs)
    tran = kqs[0]["tran"] if kqs else 0
    loi = [l for x in kqs for l in x["loi"]]
    ket("P6", "%d tiến trình × %d lượt xin suất, trần trong CSDL = %d ⇒ đặt được ĐÚNG %d"
        % (N, so_lan, tran, tran),
        DAT if (len(kqs) == N and tran > 0 and tong_dat == tran
                and tong_chan == N * so_lan - tran and not loi) else HONG,
        "%d tiến trình × %d lượt = %d lượt xin · trần %d ⇒ ĐẶT ĐƯỢC %d, BỊ CHẶN %d · lỗi: %s. "
        "Trần CÓ dùng chung thì không nhân — nên kết luận 'nhân theo số bản' ở P1/P2 là do LỚP "
        "KHO, không phải do bộ đo." % (N, so_lan, N * so_lan, tran, tong_dat, tong_chan, loi[:3]))
    return True


# ===============================================================================================
# P7 — HỒI QUY: hai bộ thử cũ phải còn xanh
# ===============================================================================================
def p7_hoi_quy():
    muc("P7. HỒI QUY — hai bộ thử cũ của giới hạn tần suất/hạn mức phải còn xanh")
    for ten in ("thu_gioi_han.py", "thu_han_muc_nguyen_tu.py"):
        duong = os.path.join(GOC_APP, "thu", ten)
        nen = nen_tam("hq-" + ten.replace(".py", ""))
        p = chay([sys.executable, duong], env=dict(os.environ, VIP_HUB_DATA=nen), gio=600)
        ra = (p.stdout or "") + (p.stderr or "")
        m = re.search(r"Ran (\d+) tests?", ra)
        so_ca = int(m.group(1)) if m else 0
        ket("P7.%s" % ten.replace(".py", ""), "%s: mã thoát 0 và đếm được số ca" % ten,
            DAT if (p.returncode == 0 and so_ca > 0) else HONG,
            "lệnh: python3 app/thu/%s · mã thoát %d · %d ca · dòng cuối: %r"
            % (ten, p.returncode, so_ca, ra.strip().splitlines()[-1] if ra.strip() else ""))
    return True


# ===============================================================================================
# P8 — TỔNG KẾT
# ===============================================================================================
def p8_tong_ket(giay):
    muc("P8. TỔNG KẾT")
    so = {DAT: 0, HONG: 0, BO_QUA: 0, KHUYET: 0}
    for k in KQ:
        so[k["trang_thai"]] += 1
    print("  ca ĐẠT: %d · HỎNG: %d · BỎ QUA: %d · KHÔNG KẾT LUẬN: %d · TỔNG: %d · %.1f giây"
          % (so[DAT], so[HONG], so[BO_QUA], so[KHUYET], len(KQ), giay))
    print("  lệnh thật + mã thoát thật đã chạy: %d" % len(LENH))
    khac0 = [(l, m) for l, m in LENH if m != 0]
    for l, m in LENH[:8]:
        print("    exit %d   %s" % (m, l[:150]))
    if len(LENH) > 8:
        print("    … và %d lệnh nữa (mã thoát khác 0: %d)" % (len(LENH) - 8, len(khac0)))
    for l, m in khac0[:5]:
        print("    ⚠ exit %d   %s" % (m, l[:150]))
    print("  số dòng lớn nhất đếm được TRỰC TIẾP trong bảng `gioi_han_luot` bằng sqlite3: %d"
          % GIOI_HAN_LUOT_CSDL)
    if so[HONG] or so[KHUYET]:
        print("  KẾT LUẬN: có ca HỎNG — xem bằng chứng ở trên.")
        print("  %d ca — ĐẠT, %d ca HỎNG" % (so[DAT], so[HONG] + so[KHUYET]))
        return 1
    print("  KẾT LUẬN: mọi ca ĐẠT. Phạm vi đã đo: N tiến trình trên MỘT máy, loopback, SQLite tạm.")
    print("  NGOÀI phạm vi: nhiều máy / sau cân bằng tải · PostgreSQL · Redis · tải lớn · hãng thật.")
    print("  %d ca — ĐẠT" % so[DAT])
    return 0


def main():
    t0 = time.time()
    print("=" * 78)
    print("G19/AG-02 — GIỚI HẠN TẦN SUẤT: TRẦN DÙNG CHUNG QUA TIẾN TRÌNH + SỐNG QUA KHỞI ĐỘNG LẠI")
    print("=" * 78)
    nen_goc = nen_tam("goc")
    dung_nen(nen_goc)
    try:
        p0_chot_an_toan(nen_goc)
        nen_do_tran = nen_tam("do-tran")
        dung_nen(nen_do_tran)
        khai_bao = doc_tran_khai_bao(nen_do_tran)
        if not khai_bao[0]:
            ket("P1.0", "Đọc được trần khai báo từ máy chủ", HONG,
                "máy chủ không trả `X-RateLimit-Limit` sau 200 lượt (mã cuối %s)" % khai_bao[2])
            return p8_tong_ket(time.time() - t0)
        p1_p2_tran_http(nen_goc, khai_bao)
        p3_nguyen_tu(nen_tam("ngtu"), khai_bao=khai_bao[0])
        p4_khoi_dong_lai(nen_tam("restart"), nen_tam("restart-mut"), khai_bao=khai_bao[0])
        p5_bat_bien(nen_tam("batbien"))
        p6_doi_chung_duong(nen_tam("pb"))
        p7_hoi_quy()
    except SystemExit:
        raise
    except Exception as e:                                                  # noqa: BLE001
        import traceback
        ket("X", "Bộ đo nổ giữa chừng", HONG, "%s: %s\n%s"
            % (type(e).__name__, e, traceback.format_exc()[-800:]))
    finally:
        don_dep()
    return p8_tong_ket(time.time() - t0)


if __name__ == "__main__":
    sys.exit(main())
