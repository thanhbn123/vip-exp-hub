#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21/AG-04 — CỔNG ĐỐI CHIẾU **ĐỘC LẬP**: GIỚI HẠN TẦN SUẤT DÙNG CHUNG QUA TIẾN TRÌNH.

====== VÌ SAO CÓ TỆP NÀY (đọc trước khi tin bất kỳ con số nào) ======
Nghiệm thu G20 của AG-01 (`docs/QA_G20.md`, cổng **C5**) kết luận thẳng: con số *"1733 ca · 47 bộ"*
mà mọi báo cáo trích dẫn **KHÔNG chứa một cổng đối chiếu độc lập nào** cho sáu cổng G19. Ba bộ
của **từng làn** (`thu_g19_gioihan.py` 22 ca · `thu_g19_route.py` 49 ca · `thu_g19_vtp.py` 31 ca)
**có** chạy — nhưng chúng do **chính người viết mã** viết, nên chúng là **bản tự khai**, không
phải một phép đo thứ hai.

Tệp này là **phép đo thứ hai** cho đúng một cổng: **GIỚI HẠN TẦN SUẤT** (PHẦN A của
`app/gioi_han.py`). Nó **không** sao chép `thu_g19_gioihan.py`: khác **cách bắn** (đồng thời có
hàng rào, không bắn lần lượt), khác **cách đếm** (đọc thẳng CSDL ở một kênh độc lập), khác **cách
tự kiểm** (hai chiều đối chứng thật, không chỉ một), và khác **phạm vi** (thêm cửa sổ TRƯỢT, đo
`Retry-After` tới từng giây theo dữ liệu trong CSDL, và `408 → timeout=True` của §42).

====== NĂM ĐIỀU BẮT BUỘC PHẢI ĐO, VÀ ĐO CẢ HAI CHIỀU ======
1. **TRẦN KHÔNG NHÂN THEO SỐ BẢN.** N = 1·2·4·8 tiến trình máy chủ THẬT, CÙNG một CSDL, CÙNG một
   IP ⇒ TỔNG số lượt được cho qua phải **BẰNG ĐÚNG** trần khai báo (không phải "≤"). Đo bằng N
   tiến trình `subprocess` thật; phía bắn dùng hàng rào để các lượt trong một vòng **ĐỒNG THỜI**.
2. **CHIỀU NGƯỢC LẠI — TRẦN **CÓ** NHÂN.** N bản, **MỖI BẢN MỘT CSDL RIÊNG** ⇒ TỔNG = N × trần.
   Đây là đối chứng **DƯƠNG** của điều 1: không có nó thì một bộ đo **MÙ** (luôn ra "không nhân")
   vẫn xanh, và ta không phân biệt được "đã chia sẻ trần" với "bộ đo không nhìn thấy gì".
3. **HAI CHIỀU ĐẾM KHÁC NHAU** (trần theo **IP** = 20 và theo **định danh** = 12, cùng cửa sổ
   300 giây) · **CỬA SỔ TRƯỢT** (chứng minh bằng cách đẩy mốc thời gian của TỪNG DÒNG, không phải
   bằng lời) · **KHỞI ĐỘNG LẠI** tiến trình ⇒ trạng thái **CÒN**.
4. **PHẢN HỒI KHI CHẠM TRẦN** phải có `Retry-After`, và **`408` phải ra `timeout=True`** — ý định
   đã chốt ở `docs/SHARED_CONTRACTS.md` §42, đo qua **stub loopback thật**.
5. **TỰ KIỂM BỘ ĐO: quay lại kho bộ nhớ MỘT tiến trình ⇒ bộ đo **PHẢI** ĐỎ.** Bản đột biến giữ
   nguyên phần quyết định của `gioi_han`, chỉ đổi **lớp kho**. Nếu bộ đo vẫn xanh trên bản đó thì
   nó là một cổng **hỏng sẵn** và mọi dòng xanh phía trên **không chứng minh gì**.

====== RÀNG BUỘC TUYỆT ĐỐI CỦA BỘ ĐO NÀY ======
* **KHÔNG gọi API hãng, kể cả sandbox** (`V-G09-01` + `V-13906-05` CHƯA CẤP). Mọi phép đo HTTP chỉ
  chạm `127.0.0.1` với cổng do hệ điều hành cấp. Stub J&T của dự án tự chặn mọi `host` khác.
* **KHÔNG push / deploy / tunnel.** Máy chủ đo bind `127.0.0.1` **tường minh** (không trông cậy giá
  trị mặc định) và cổng lấy từ `bind(('127.0.0.1', 0))` nên không tranh cổng của ai.
* **KHÔNG mở `CHO_PHEP_LIVE`** — A0c ĐO LẠI bằng tiến trình con, không nói suông.
* **KHÔNG credentials thật, KHÔNG `.env`.** Bí mật trong tệp này là chuỗi GIẢ tự đặt, có hậu tố
  `GIA`, và chỉ sống trong tiến trình bộ thử.
* **KHÔNG đoán mã trạng thái hãng (D-4)** — bộ đo chỉ chạm mã HTTP của **máy chủ nhà** và của
  **stub**, không gán một mã nào cho hãng.
* **KHÔNG chuyển CSDL sang PostgreSQL (D-8).** CSDL của mọi nền đo là SQLite trong thư mục **TẠM**;
  tiến trình con **TỰ CHỐI CHẠY** (mã thoát 9) nếu CSDL của nó nằm ngoài thư mục tạm. Không mở một
  kết nối nào tới `:5432`. `VIP_THU_POSTGRES` bị **gỡ** khỏi môi trường của mọi tiến trình con.
* **KHÔNG giữ chốt `D-9`** (`city`/`area` chặn cứng ngoài mock): bộ đo **không** chạm ánh xạ `area`.
* **Tắt tiến trình theo ĐÚNG PID** (không `pkill`/`killall`), và dọn thư mục tạm khi xong.

====== CÁC PHẦN ======
  A0   Chốt an toàn + đối chứng dương cho chính LUẬT PHÁN của bộ đo
  A1   Trần KHAI BÁO đọc từ chính máy chủ (IP 20 · định danh 12 · cùng cửa sổ 300 giây)
  A2   CHIỀU 1 — N = 1·2·4·8 bản CHUNG một CSDL ⇒ TỔNG = ĐÚNG trần           [bất biến chính]
  A3   KÊNH ĐỘC LẬP — đếm thẳng bảng `gioi_han_luot` bằng `sqlite3`, đối chiếu với số qua HTTP
  A4   CHIỀU 2 — N bản MỖI BẢN MỘT CSDL ⇒ TỔNG = N × trần                     [đối chứng DƯƠNG]
  A5   TỰ KIỂM — bản ĐỘT BIẾN (kho bộ nhớ một tiến trình) ⇒ bộ đo PHẢI ĐỎ
  A6   CỬA SỔ TRƯỢT — đẩy mốc TỪNG DÒNG: nhả đúng phần đã trôi, và `Retry-After` theo dòng cũ nhất
  A7   KHỞI ĐỘNG LẠI — tiến trình MỚI trên CSDL cũ vẫn bị chặn (+ đối chứng dương: CSDL mới thì qua)
  A8   HÌNH DẠNG 429 — `Retry-After` · `X-RateLimit-*` · `chieu`
  A9   `408 → timeout=True` (§42) qua stub loopback, kèm hai đối chứng dương
  A10  HỒI QUY — ba bộ thử giới hạn của dự án, chạy bằng LỆNH THẬT + MÃ THOÁT THẬT
  A11  SỔ ĐỐI CHỨNG — mọi nhóm ca ÂM phải có ca DƯƠNG; sổ tự kiểm chính nó
  A12  Tổng kết + bằng chứng (bảng N · tổng lượt qua · trần khai báo · lệnh · mã thoát)

CHẠY
----
    python3 app/thu/thu_g21_gioihan.py        # 0 = mọi ca ĐẠT · 1 = có ca HỎNG · 9 = chốt an toàn
    sh trien_khai/g21-gioihan/chay.sh         # bản có ghi log ra thư mục tạm + in bảng tổng kết

PHẠM VI — NÓI RÕ CÁI **NẰM NGOÀI**
---------------------------------
Đo: N tiến trình trên **MỘT máy**, loopback, SQLite WAL trong thư mục tạm. **KHÔNG** đo: nhiều MÁY
hoặc sau bộ cân bằng tải (mỗi máy một CSDL ⇒ trần vẫn nhân — đúng cái `gioi_han.py` dòng 42-43 tự
khai; chỗ đó cần Redis hoặc một CSDL chung) · tấn công phân tán nhiều IP · tải lớn · PostgreSQL.
Tệp này **không sửa một dòng mã sản phẩm nào**; nó chỉ ĐO. Bản đột biến ở A5 sống trong thư mục
tạm và bị xoá khi kết thúc.
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
import threading
import time
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # …/app
DU_AN = os.path.dirname(GOC_APP)
THU_MUC_TAM = os.path.realpath(tempfile.gettempdir())
DU_LIEU_MAC_DINH = os.path.realpath(os.path.join(GOC_APP, "du-lieu"))
DUONG_DANG_NHAP = "/api/v2/auth/dang-nhap"

DAT, HONG, BO_QUA, KHUYET = "DAT", "HONG", "BO_QUA", "KHUYET"
KY = {DAT: "✓", HONG: "✗", BO_QUA: "–", KHUYET: "!"}
KQ = []
NENS = []
CON = []
LENH = []              # (lệnh, mã thoát) — BẰNG CHỨNG "lệnh thật + mã thoát thật"
BANG_N = []            # (chiều, N, tổng lượt qua, trần khai báo, phán quyết)
DOI_CHUNG = {}         # nhóm → {"am": n, "duong": n} — chốt (b): mọi ca ÂM phải có ca DƯƠNG

# Trần của `auth.dang_nhap` theo CHÍNH SÁCH SẢN PHẨM (`gioi_han.CHINH_SACH`). Bộ đo KHÔNG tin hai
# con số này: A1 đọc lại từ header của chính máy chủ và khẳng định chúng khớp.
TRAN_IP_MONG = 20
TRAN_DINH_DANH_MONG = 12
CUA_SO_MONG = 300


# ===============================================================================================
# HẠ TẦNG: IN · GHI NHẬN · LỆNH THẬT · NỀN TẠM · BẢO ĐẢM DỌN DẸP
# ===============================================================================================
def ket(ma, ten, trang_thai, bang_chung="", nhom=None, chieu=None):
    """Ghi một ca. `nhom` + `chieu` ('am'|'duong') nuôi SỔ ĐỐI CHỨNG ở A11."""
    KQ.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    if nhom is not None:
        o = DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})
        if chieu in ("am", "duong"):
            o[chieu] += 1
    print("  %s [%s] %s%s" % (KY[trang_thai], ma, ten,
                              ("\n        " + bang_chung) if bang_chung else ""))
    return trang_thai


def muc(t):
    print("\n" + "─" * 78 + "\n─ %s\n" % t + "─" * 78)


def chay(lenh, *, env=None, gio=1800, cwd=None):
    """Chạy một tiến trình THẬT, ghi (lệnh, mã thoát) làm bằng chứng."""
    p = subprocess.run(lenh, capture_output=True, text=True, env=env, cwd=cwd or DU_AN,
                       timeout=gio)
    LENH.append((" ".join(lenh), p.returncode))
    return p


def nen_tam(tien_to):
    """Một thư mục dữ liệu TẠM (một CSDL riêng). Chốt cứng: phải nằm trong thư mục tạm."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="vh-g21-ag04-%s-" % tien_to))
    if not d.startswith(THU_MUC_TAM + os.sep) or d == DU_LIEU_MAC_DINH:
        raise SystemExit("TỪ CHỐI: nền %r không nằm trong thư mục tạm" % d)
    NENS.append(d)
    return d


def dung_nen(nen):
    """Dựng schema trên nền tạm bằng ĐÚNG hai bộ cài của dự án (`migrate.py` + `khoi_tao.py`)."""
    for ten in ("migrate.py", "khoi_tao.py"):
        p = chay([sys.executable, os.path.join(GOC_APP, ten)], gio=300, env=moi_truong_nen(nen))
        if p.returncode:
            raise RuntimeError("%s hỏng (mã %d): %s"
                               % (ten, p.returncode, (p.stderr or p.stdout)[-400:]))
    return nen


def moi_truong_sach(**them):
    """Môi trường cho tiến trình con, KHÔNG tự đặt `VIP_HUB_DATA` (tiến trình tự chọn nền)."""
    env = dict(os.environ, **them)
    env.pop("VIP_THU_POSTGRES", None)          # D-8: bộ đo này KHÔNG chạm PostgreSQL
    env.pop("VIP_HUB_CHO_PHEP_LIVE", None)     # KHÔNG mở cờ live, kể cả qua môi trường thừa hưởng
    return env


def moi_truong_nen(nen, **them):
    """Môi trường cho tiến trình con: CSDL trỏ vào nền tạm, bind loopback, KHÔNG PostgreSQL."""
    return moi_truong_sach(VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1", **them)


def cong_roi():
    """Cổng do HỆ ĐIỀU HÀNH cấp trên `127.0.0.1` — không tranh cổng của ai, không mở ra ngoài."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def cho_cong(cong, p, giay=90):
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


def tat_tien_trinh(p, giay=20):
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
# TIẾN TRÌNH CON — ghi ra TỆP TẠM, không phải tệp của dự án
# ===============================================================================================
CHAY_MAY_CHU = r'''# -*- coding: utf-8 -*-
"""BỘ KHỞI ĐỘNG máy chủ cho phép đo G21/AG-04 — để chèn được BẢN ĐỘT BIẾN lên đầu `sys.path`.

Chạy thẳng `python3 app/server.py` thì `sys.path[0]` LUÔN là `app/`, nên bản `gioi_han.py` đột
biến ở thư mục khác không bao giờ được nạp. `runpy.run_path` giữ nguyên `sys.argv` (cổng vẫn là
`sys.argv[1]`) và đặt `__name__ == "__main__"`, nên `server.py` chạy y như được gọi trực tiếp.
"""
import os, runpy, sys

goc = os.environ["VIP_G21_GOC_APP"]
mut = os.environ.get("VIP_G21_MUT") or ""
sys.path.insert(0, goc)
if mut:
    sys.path.insert(0, mut)
runpy.run_path(os.path.join(goc, "server.py"), run_name="__main__")
'''

CON_CHOT = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G21/AG-04): đọc `CHO_PHEP_LIVE` của BA lớp adapter và đường dẫn CSDL.

Đọc thuộc tính LỚP (không phải thuộc tính mô-đun): cờ nằm trong ba lớp đó. Tự CHỐI (mã 9) nếu
CSDL không nằm trong thư mục tạm — chốt cứng để không bao giờ đo trên dữ liệu thật.
"""
import json, os, sys, tempfile

sys.path.insert(0, sys.argv[1])
import cau_hinh                                                          # noqa: E402
duong = os.path.realpath(cau_hinh.DUONG_DAN_CSDL)
if not duong.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
    sys.stderr.write("TỪ CHỐI: CSDL %r ngoài thư mục tạm\n" % duong)
    raise SystemExit(9)

import adapter, adapter_jt, adapter_vtp                                  # noqa: E402

with open(sys.argv[2], "w") as f:
    json.dump({"csdl": duong,
               "cho_phep_live": {"adapter.CarrierAdapter": bool(adapter.CarrierAdapter.CHO_PHEP_LIVE),
                                 "adapter_jt.AdapterJT": bool(adapter_jt.AdapterJT.CHO_PHEP_LIVE),
                                 "adapter_vtp.AdapterVTP": bool(adapter_vtp.AdapterVTP.CHO_PHEP_LIVE)},
               "jt_sandbox": bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", False)),
               "cong_pg_5432": os.environ.get("VIP_HUB_PG", "(không đặt)")}, f)
'''

# ===============================================================================================
# BẢN ĐỘT BIẾN — CHỈ để TỰ KIỂM bộ đo, KHÔNG BAO GIỜ là mã sản phẩm
# ===============================================================================================
BAN_DOT_BIEN = '''

# ===============================================================================================
# BẢN ĐỘT BIẾN CỐ Ý (G21/AG-04) — CHỈ dùng cho ca TỰ KIỂM A5, KHÔNG BAO GIỜ là mã sản phẩm.
#
# Nó QUAY LẠI đúng khuôn TRƯỚC KHI VÁ: trạng thái nằm trong BỘ NHỚ MỘT TIẾN TRÌNH (không dùng
# chung qua tiến trình, mất sạch khi khởi động lại). Giao diện y hệt `KhoCSDL` nên phần QUYẾT
# ĐỊNH phía trên (chính sách · thứ tự kiểm · luật 4 "kiểm hết rồi mới ghi" · cửa sổ trượt · thời
# gian phạt) KHÔNG đổi một dòng nào. Nhờ vậy A5 tách được ĐÚNG MỘT biến: trạng thái nằm ở đâu.
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
        # DỌN LƯỜI, đúng như bản cũ: chỉ quét khi số khoá VƯỢT trần (quét mọi lượt thì chính bộ
        # đôi của bộ thử làm chậm phép đo).
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


def dung_ban_dot_bien(nen):
    """Sinh `mut/gioi_han.py` = mã thật + phần ghi đè lớp kho. Trả THƯ MỤC để chèn vào `sys.path`."""
    with open(os.path.join(GOC_APP, "gioi_han.py"), encoding="utf-8") as f:
        goc = f.read()
    thu_muc = os.path.join(nen, "mut")
    os.makedirs(thu_muc, exist_ok=True)
    with open(os.path.join(thu_muc, "gioi_han.py"), "w", encoding="utf-8") as f:
        f.write(goc + BAN_DOT_BIEN)
    return thu_muc


# ===============================================================================================
# MÁY CHỦ THẬT (chỉ loopback) + LƯỢT GỌI HTTP
# ===============================================================================================
def mo_may_chu(nen, *, mut=None, tien_to="sv"):
    """Một tiến trình máy chủ THẬT trên `nen`. `mut` = thư mục chứa bản đột biến (A5)."""
    c = cong_roi()
    log = os.path.join(nen, "%s-%d.log" % (tien_to, c))
    f = open(log, "w")
    env = moi_truong_nen(nen, VIP_G21_GOC_APP=GOC_APP, VIP_G21_MUT=mut or "")
    if mut:
        lenh = [sys.executable, os.path.join(nen, "chay_may_chu.py"), str(c)]
    else:
        lenh = [sys.executable, os.path.join(GOC_APP, "server.py"), str(c)]
    p = subprocess.Popen(lenh, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
    CON.append(p)
    if not cho_cong(c, p):
        raise RuntimeError("máy chủ không mở cổng %d (pid %d):\n%s"
                           % (c, p.pid, open(log).read()[-600:]))
    return {"p": p, "cong": c, "log": log, "nen": nen, "pid": p.pid}


def goi_dang_nhap(cong, ten, *, mat_khau="sai-be-bet", gio=30):
    """MỘT lượt đăng nhập SAI. Trả `(mã HTTP, thân, header)`. CHỈ `127.0.0.1`."""
    d = json.dumps({"ten_dang_nhap": ten, "mat_khau": mat_khau}).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (cong, DUONG_DANG_NHAP), data=d,
                               method="POST")
    r.add_header("X-Requested-With", "VIPHub")      # `_can_csrf` đòi header này
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=gio) as f:
            return f.status, f.read(), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def phan_loai(ma, than):
    """401 = ĐÃ QUA trần (sai thông tin đăng nhập) · 429 = BỊ CHẶN · khác = 'mã lạ'."""
    if ma == 401:
        return "qua"
    if ma == 429:
        try:
            return "chan:" + str(json.loads(than.decode("utf-8")).get("chieu"))
        except (ValueError, UnicodeDecodeError):
            return "chan:?"
    return "ma_la:%s" % ma


def ban_dong_thoi(sv, *, tran, nhan=""):
    """Bắn ĐỒNG THỜI: mỗi vòng, MỌI bản còn sống nhận ĐÚNG một lượt, cùng một HÀNG RÀO.

    Khác `thu_g19_gioihan.bom_tuan_tu` (bắn LẦN LƯỢT): ở đây các lượt trong một vòng được phát
    ĐỒNG THỜI, nên áp lực lên bộ đếm DÙNG CHUNG là thật. Bất biến được khẳng định KHÔNG đổi:
    TỔNG số lượt được cho qua phải bằng ĐÚNG trần khai báo.

    Một bản tự dừng khi nhận 429 đầu tiên (hết ngân sách), nên tổng số lượt được cho qua là TẤT
    ĐỊNH chứ không phụ thuộc thứ tự đến.
    """
    dem = [0] * len(sv)
    con = [True] * len(sv)
    ct = [[] for _ in sv]
    for vong in range(tran + 3):
        song = [k for k in range(len(sv)) if con[k]]
        if not song:
            break
        rao = threading.Barrier(len(song))
        khoa = threading.Lock()

        def _mot(k):
            rao.wait()
            try:
                ma, than, hdr = goi_dang_nhap(
                    sv[k]["cong"], "g21-%s-%d-%d-%d" % (nhan, k, vong, os.getpid()))
                pl, hdr = phan_loai(ma, than), hdr
            except Exception as e:                                          # noqa: BLE001
                # Lỗi mạng/tiến trình chết KHÔNG được nuốt: nó thành một lượt "mã lạ" để ca HỎNG
                # nhìn thấy, chứ không âm thầm làm tổng nhỏ đi rồi được đọc là "không nhân".
                ma, pl, hdr = None, "ma_la:%s" % type(e).__name__, {}
            with khoa:
                ct[k].append({"ma": ma, "phan_loai": pl, "retry_after": hdr.get("Retry-After"),
                              "gioi_han": hdr.get("X-RateLimit-Limit"),
                              "con_lai": hdr.get("X-RateLimit-Remaining")})
                if pl == "qua":
                    dem[k] += 1
                else:
                    con[k] = False

        luong = [threading.Thread(target=_mot, args=(k,)) for k in song]
        for t in luong:
            t.start()
        for t in luong:
            t.join()
    return {"dem": dem, "ct": ct, "pids": [s["pid"] for s in sv],
            "so_luot": sum(len(x) for x in ct),
            "ma_la": [[o for o in x if o["phan_loai"].startswith("ma_la")] for x in ct]}


# ===============================================================================================
# KÊNH ĐỘC LẬP — ĐỌC THẲNG CSDL (không qua API của sản phẩm)
# ===============================================================================================
def _mo_csdl(nen):
    return sqlite3.connect(os.path.join(nen, "hub.db"), timeout=30)


def doc_luot(nen, khoa):
    """Danh sách `moc` của một khoá, đọc TRỰC TIẾP bằng `sqlite3`.

    Đây là KÊNH ĐỘC LẬP của A3: con số đi qua API và con số đọc từ đĩa phải khớp. Một bộ đo chỉ
    tin lời máy chủ thì không phân biệt được "trần đúng" với "máy chủ nói dối".
    """
    kn = _mo_csdl(nen)
    try:
        return [float(r[0]) for r in
                kn.execute("SELECT moc FROM gioi_han_luot WHERE khoa=? ORDER BY moc", (khoa,))]
    finally:
        kn.close()


def lui_moc(nen, khoa, *, so_dong, giay):
    """Đẩy `so_dong` dòng **CŨ NHẤT** của `khoa` lùi `giay` giây — MÔ PHỎNG thời gian trôi qua.

    Đây là phép ĐO, không phải bản vá: nó không đổi `gioi_han.py` một dòng nào, chỉ đổi DỮ LIỆU mà
    cửa sổ trượt đọc. Nếu cửa sổ là **CỐ ĐỊNH** (một bộ đếm + một mốc đầu cửa sổ) thì thao tác
    này KHÔNG THỂ làm đúng điều nó vừa làm được — đó chính là điều A6 đo.
    """
    kn = _mo_csdl(nen)
    try:
        rows = [r[0] for r in kn.execute(
            "SELECT rowid FROM gioi_han_luot WHERE khoa=? ORDER BY moc LIMIT ?", (khoa, so_dong))]
        kn.executemany("UPDATE gioi_han_luot SET moc = moc - ? WHERE rowid=?", [(giay, r) for r in rows])
        kn.commit()
        return len(rows)
    finally:
        kn.close()


def luot_trong_cua_so(nen, khoa, cua_so, bay=None):
    """Số dòng CÒN trong cửa sổ, tính bằng đồng hồ của CHÍNH bộ đo (không hỏi máy chủ)."""
    bay = time.time() if bay is None else bay
    return [m for m in doc_luot(nen, khoa) if m > bay - cua_so]


def khoa_ip():
    return "auth.dang_nhap|ip|127.0.0.1"


def khoa_dinh_danh(ten):
    return "auth.dang_nhap|dinh_danh|%s" % ten


# ===============================================================================================
# LUẬT PHÁN CỦA BỘ ĐO + SỔ ĐỐI CHỨNG (chốt (b): mọi ca ÂM phải có ca DƯƠNG)
# ===============================================================================================
def phan_quyet_tran_chung(tong_qua, tran):
    """LUẬT PHÁN của bất biến chính: N bản CHUNG một CSDL ⇒ TỔNG qua phải BẰNG ĐÚNG `tran`.

    Trả `(đạt?, lý do)`. Ba nhánh, và nhánh thứ ba quan trọng ngang hai nhánh kia: một tổng **nhỏ
    hơn** trần KHÔNG phải "đạt" — nó nghĩa là phép đo chưa bắn đủ lượt, và kết luận "không nhân"
    lúc đó là kết luận rỗng.
    """
    if tong_qua == tran:
        return True, "ĐÚNG trần khai báo (%d)" % tran
    if tong_qua > tran:
        return False, ("TRẦN NHÂN THEO SỐ BẢN: %d lượt qua > trần %d (thừa %d)"
                       % (tong_qua, tran, tong_qua - tran))
    return False, ("CHƯA CHẠM TRẦN: chỉ %d/%d lượt qua — phép đo thiếu lượt, KHÔNG kết luận"
                   % (tong_qua, tran))


def nhom_thieu_duong(so):
    """Nhóm có ca ÂM mà KHÔNG có ca DƯƠNG. Rỗng = sổ cân."""
    return sorted(k for k, v in so.items() if v["am"] > 0 and v["duong"] == 0)


# ===============================================================================================
# A0 — CHỐT AN TOÀN + ĐỐI CHỨNG DƯƠNG CHO CHÍNH LUẬT PHÁN
# ===============================================================================================
def a0_chot_an_toan(nen):
    muc("A0. CHỐT AN TOÀN — nền tạm · SQLite · loopback · `CHO_PHEP_LIVE` vẫn False")
    print("  thư mục tạm của hệ : %s" % THU_MUC_TAM)
    print("  dữ liệu THẬT (cấm): %s" % DU_LIEU_MAC_DINH)
    print("  Python %s · SQLite %s" % (sys.version.split()[0], sqlite3.sqlite_version))
    truoc = os.environ.get("VIP_HUB_DATA")
    if truoc and not os.path.realpath(truoc).startswith(THU_MUC_TAM + os.sep):
        print("  TỪ CHỐI: VIP_HUB_DATA=%r nằm NGOÀI thư mục tạm — không chạy trên dữ liệu thật."
              % truoc)
        raise SystemExit(9)
    ket("A0a", "Mọi nền đo nằm trong thư mục TẠM, không phải dữ liệu thật",
        DAT if (THU_MUC_TAM != DU_LIEU_MAC_DINH and nen.startswith(THU_MUC_TAM + os.sep)) else HONG,
        "nền: %s · dữ liệu thật: %s" % (nen, DU_LIEU_MAC_DINH))
    with open(os.path.join(nen, "hub.db"), "rb") as f:
        dau = f.read(16)
    ket("A0b", "CSDL nghiệp vụ của nền là SQLite THẬT (D-8: KHÔNG chuyển sang PostgreSQL)",
        DAT if dau == b"SQLite format 3\x00" else HONG,
        "16 byte đầu của hub.db: %r · bộ đo chỉ mở `127.0.0.1` + tệp trong thư mục tạm; "
        "`VIP_THU_POSTGRES` bị GỠ khỏi môi trường mọi tiến trình con; KHÔNG kết nối `:5432`" % dau)
    con = os.path.join(nen, "con_chot.py")
    with open(con, "w") as f:
        f.write(CON_CHOT)
    ra = os.path.join(nen, "chot.json")
    p = chay([sys.executable, con, GOC_APP, ra], gio=120, env=moi_truong_nen(nen))
    o = {}
    if os.path.exists(ra):
        with open(ra) as f:
            o = json.load(f)
    live = o.get("cho_phep_live", {})
    ket("A0c", "`CHO_PHEP_LIVE` của CẢ BA lớp adapter vẫn False (bộ đo KHÔNG mở nó)",
        DAT if (p.returncode == 0 and live and not any(live.values())) else HONG,
        "tiến trình con ĐỌC THẲNG thuộc tính lớp: %s (mã thoát %d) · `JT_CHO_PHEP_SANDBOX`=%s · "
        "CSDL con thấy: %s" % (live or "?", p.returncode, o.get("jt_sandbox"), o.get("csdl")))
    # ĐỐI CHỨNG DƯƠNG cho chính luật phán: nó phải có RĂNG ở CẢ HAI phía.
    d1, l1 = phan_quyet_tran_chung(TRAN_IP_MONG, TRAN_IP_MONG)
    d2, l2 = phan_quyet_tran_chung(TRAN_IP_MONG * 4, TRAN_IP_MONG)
    d3, l3 = phan_quyet_tran_chung(TRAN_IP_MONG - 1, TRAN_IP_MONG)
    ket("A0d", "Luật phán của bộ đo có RĂNG: đúng trần ⇒ ĐẠT · nhân theo bản ⇒ HỎNG · thiếu lượt ⇒ HỎNG",
        DAT if (d1 and not d2 and not d3) else HONG,
        "qua=%d ⇒ (%s, %s) · qua=%d ⇒ (%s, %s) · qua=%d ⇒ (%s, %s)"
        % (TRAN_IP_MONG, d1, l1, TRAN_IP_MONG * 4, d2, l2, TRAN_IP_MONG - 1, d3, l3))
    return True


# ===============================================================================================
# A1 — TRẦN KHAI BÁO, ĐỌC TỪ CHÍNH MÁY CHỦ
# ===============================================================================================
def a1_tran_khai_bao():
    muc("A1. TRẦN KHAI BÁO — đọc từ chính máy chủ, hai chiều, cùng một cửa sổ")
    # --- chiều `ip`: tên đăng nhập KHÁC NHAU mỗi lượt ⇒ chỉ chiều `ip` cộng ---
    nen = dung_nen(nen_tam("tran-ip"))
    sv = mo_may_chu(nen, tien_to="a1ip")
    try:
        so_qua, chan = 0, None
        for i in range(TRAN_IP_MONG + 6):
            ma, than, hdr = goi_dang_nhap(sv["cong"], "g21-a1ip-%d-%d" % (i, os.getpid()))
            if ma == 401:
                so_qua += 1
            else:
                chan = {"ma": ma, "than": than, "hdr": hdr}
                break
    finally:
        tat_tien_trinh(sv["p"])
    # GHI LẠI ĐỂ KHÔNG AI PHẢI ĐOÁN: máy chủ CHỈ gắn nhóm `X-RateLimit-*` lên lượt **429**;
    # lượt ĐƯỢC QUA (401) KHÔNG mang header nào của bộ đếm (đo ở A8c). Nên trần và cửa sổ phải
    # đọc từ CHÍNH lượt bị chặn — đọc từ lượt qua thì luôn ra `None`.
    cua_so = chan["hdr"].get("X-RateLimit-Window") if chan else None
    chieu = json.loads(chan["than"].decode("utf-8")) if chan and chan["ma"] == 429 else {}
    ok_ip = (so_qua == TRAN_IP_MONG and chan and chan["ma"] == 429 and chieu.get("chieu") == "ip"
             and int(chan["hdr"].get("X-RateLimit-Limit") or 0) == TRAN_IP_MONG
             and int(cua_so or 0) == CUA_SO_MONG)
    ket("A1a", "Chiều `ip`: đúng %d lượt qua rồi 429 · `X-RateLimit-Limit`=%d · cửa sổ=%s giây"
        % (TRAN_IP_MONG, TRAN_IP_MONG, cua_so),
        DAT if ok_ip else HONG,
        "số lượt qua thực đo = %d (mong %d) · lượt chặn: mã %s · `chieu`=%r · header "
        "`X-RateLimit-Limit`=%s · `X-RateLimit-Window`=%s"
        % (so_qua, TRAN_IP_MONG, chan and chan["ma"], chieu.get("chieu"),
           chan and chan["hdr"].get("X-RateLimit-Limit"), cua_so),
        nhom="tran-ip", chieu="duong")
    # --- chiều `dinh_danh`: CÙNG một tên ⇒ chiều định danh (12) chạm trước chiều ip (20) ---
    nen2 = dung_nen(nen_tam("tran-dd"))
    sv2 = mo_may_chu(nen2, tien_to="a1dd")
    ten = "g21-a1dd-co-dinh-%d" % os.getpid()
    try:
        so_qua2, chan2 = 0, None
        for i in range(TRAN_DINH_DANH_MONG + 30):
            ma, than, hdr = goi_dang_nhap(sv2["cong"], ten)
            if ma == 401:
                so_qua2 += 1
            else:
                chan2 = {"ma": ma, "than": than, "hdr": hdr}
                break
    finally:
        tat_tien_trinh(sv2["p"])
    cua_so2 = chan2["hdr"].get("X-RateLimit-Window") if chan2 else None
    chieu2 = json.loads(chan2["than"].decode("utf-8")) if chan2 and chan2["ma"] == 429 else {}
    ok_dd = (so_qua2 == TRAN_DINH_DANH_MONG and chan2 and chan2["ma"] == 429
             and chieu2.get("chieu") == "dinh_danh"
             and int(chan2["hdr"].get("X-RateLimit-Limit") or 0) == TRAN_DINH_DANH_MONG
             and int(cua_so2 or 0) == CUA_SO_MONG)
    ket("A1b", "Chiều `dinh_danh` (cùng một tên): đúng %d lượt qua rồi 429 · cửa sổ=%s giây"
        % (TRAN_DINH_DANH_MONG, cua_so2),
        DAT if ok_dd else HONG,
        "số lượt qua thực đo = %d (mong %d) · lượt chặn: mã %s · `chieu`=%r · header "
        "`X-RateLimit-Limit`=%s · `X-RateLimit-Window`=%s · HAI CHIỀU KHÁC NHAU (%d vs %d), "
        "CÙNG một cửa sổ %s giây"
        % (so_qua2, TRAN_DINH_DANH_MONG, chan2 and chan2["ma"], chieu2.get("chieu"),
           chan2 and chan2["hdr"].get("X-RateLimit-Limit"), cua_so2, TRAN_IP_MONG,
           TRAN_DINH_DANH_MONG, cua_so2),
        nhom="tran-ip", chieu="duong")
    return {"ip": TRAN_IP_MONG, "dinh_danh": TRAN_DINH_DANH_MONG, "cua_so": CUA_SO_MONG}, chan2


# ===============================================================================================
# A2 / A4 / A5 — BA CHIỀU ĐO CÙNG MỘT PHÉP BẮN
# ===============================================================================================
def _do_mot_lan(nhan, N, *, kieu):
    """Dựng N máy chủ rồi bắn đồng thời. `kieu` ∈ 'chung' | 'rieng' | 'dot_bien'."""
    if kieu == "rieng":
        # MỖI BẢN MỘT CSDL RIÊNG — đúng khuôn "nhiều máy, mỗi máy một CSDL" mà `gioi_han.py`
        # dòng 42-43 tự khai là CHƯA đóng.
        sv = [mo_may_chu(dung_nen(nen_tam("%s-n%d" % (nhan, N))), tien_to="%s%d" % (nhan, N))
              for _ in range(N)]
        nen_chung = None
        mut = None
    else:
        nen_chung = dung_nen(nen_tam("%s-n%d" % (nhan, N)))
        mut = dung_ban_dot_bien(nen_chung) if kieu == "dot_bien" else None
        if mut:
            with open(os.path.join(nen_chung, "chay_may_chu.py"), "w") as f:
                f.write(CHAY_MAY_CHU)
        sv = [mo_may_chu(nen_chung, mut=mut, tien_to="%s%d" % (nhan, N)) for _ in range(N)]
    try:
        k = ban_dong_thoi(sv, tran=TRAN_IP_MONG, nhan=nhan)
        k.update({"N": N, "kieu": kieu, "nen_chung": nen_chung, "mut": mut})
        return k
    finally:
        for s in sv:
            tat_tien_trinh(s["p"])


def _in_bang(k, tran, ket_luan):
    BANG_N.append((k["kieu"], k["N"], sum(k["dem"]), tran, ket_luan))


def a2_chieu_chung():
    muc("A2. CHIỀU 1 — N bản CHUNG một CSDL ⇒ TỔNG lượt qua phải BẰNG ĐÚNG trần khai báo")
    print("  Bắn ĐỒNG THỜI (hàng rào mỗi vòng), N tiến trình `subprocess` thật, cùng IP 127.0.0.1,")
    print("  cùng một CSDL. Trần khai báo = %d (A1 đọc từ chính máy chủ)." % TRAN_IP_MONG)
    ra = {}
    for N in (1, 2, 4, 8):
        k = _do_mot_lan("chung%d" % N, N, kieu="chung")
        ra[N] = k
        tong = sum(k["dem"])
        dat, vi = phan_quyet_tran_chung(tong, TRAN_IP_MONG)
        _in_bang(k, TRAN_IP_MONG, "ĐẠT" if dat else "HỎNG")
        ket("A2.%d" % N, "N=%d bản CHUNG CSDL: TỔNG qua = %d (trần %d) — KHÔNG nhân theo số bản"
            % (N, tong, TRAN_IP_MONG),
            DAT if (dat and not any(k["ma_la"])) else HONG,
            "%s · từng bản qua %s ⇒ TỔNG %d · tổng lượt đã bắn %d · mã lạ: %s · pid con %s"
            % (vi, k["dem"], tong, k["so_luot"], k["ma_la"], k["pids"]),
            nhom="tran-dung-chung", chieu="duong")
        if N == 8:
            # A3 — KÊNH ĐỘC LẬP: đếm thẳng CSDL, không hỏi máy chủ.
            rows = luot_trong_cua_so(k["nen_chung"], khoa_ip(), CUA_SO_MONG)
            ket("A3", "KÊNH ĐỘC LẬP: đếm thẳng `gioi_han_luot` bằng `sqlite3` khớp số qua HTTP",
                DAT if len(rows) == tong == TRAN_IP_MONG else HONG,
                "đọc đĩa: %d dòng `%s` trong cửa sổ %d giây · qua HTTP: %d · trần: %d. Hai kênh "
                "độc lập (API của sản phẩm vs. tệp CSDL) phải khớp; một bộ đo chỉ tin lời máy chủ "
                "thì không phân biệt được 'trần đúng' với 'máy chủ nói dối'."
                % (len(rows), khoa_ip(), CUA_SO_MONG, tong, TRAN_IP_MONG))
    return ra


def a4_chieu_rieng():
    muc("A4. CHIỀU 2 (ĐỐI CHỨNG DƯƠNG) — N bản MỖI BẢN MỘT CSDL ⇒ TỔNG = N × trần")
    print("  CÙNG bộ bắn, CÙNG trần khai báo, CÙNG số bản — CHỈ khác: mỗi bản một CSDL riêng.")
    print("  Nếu ở đây CŨNG ra %d thì bộ đo MÙ và mọi dòng xanh ở A2 vô nghĩa." % TRAN_IP_MONG)
    ra = {}
    for N in (1, 2, 4, 8):
        k = _do_mot_lan("rieng%d" % N, N, kieu="rieng")
        ra[N] = k
        tong = sum(k["dem"])
        dat = tong == N * TRAN_IP_MONG and not any(k["ma_la"])
        _in_bang(k, TRAN_IP_MONG, "ĐẠT" if dat else "HỎNG")
        ket("A4.%d" % N, "N=%d bản RIÊNG CSDL: TỔNG qua = %d = %d × %d — trần CÓ nhân"
            % (N, tong, N, TRAN_IP_MONG),
            DAT if dat else HONG,
            "từng bản qua %s ⇒ TỔNG %d (mong %d) · mã lạ: %s. Đây là ĐỐI CHỨNG DƯƠNG của A2: nó "
            "chứng minh phép đo NHÌN THẤY được việc nhân, nên 'không nhân' ở A2 là một kết quả "
            "ĐO ĐƯỢC chứ không phải một bộ đo hỏng."
            % (k["dem"], tong, N * TRAN_IP_MONG, k["ma_la"]),
            nhom="tran-nhan-theo-ban", chieu="duong")
    return ra


def a5_tu_kiem(ket_qua_chung):
    muc("A5. TỰ KIỂM BỘ ĐO — quay lại kho BỘ NHỚ MỘT TIẾN TRÌNH ⇒ bộ đo **PHẢI ĐỎ**")
    print("  Bản đột biến giữ NGUYÊN phần quyết định của `gioi_han`, chỉ đổi LỚP KHO về đúng khuôn")
    print("  trước khi vá, rồi chạy ĐÚNG phép đo của A2. Với N ≥ 2 nó PHẢI ra N × %d — và luật phán"
          % TRAN_IP_MONG)
    print("  của bộ đo PHẢI trả HỎNG trên con số đó. Xanh ở đây nghĩa là cổng này HỎNG SẴN.")
    print("  N = 1 là ĐỐI CHỨNG DƯƠNG riêng: một tiến trình thì 'kho bộ nhớ' và 'kho CSDL' là MỘT,")
    print("  nên bản đột biến PHẢI cho đúng %d — nó chứng minh bản đột biến chỉ đổi ĐÚNG một biến."
          % TRAN_IP_MONG)
    ra = {}
    for N in (1, 2, 4, 8):
        k = _do_mot_lan("dotbien%d" % N, N, kieu="dot_bien")
        ra[N] = k
        tong = sum(k["dem"])
        dat, vi = phan_quyet_tran_chung(tong, TRAN_IP_MONG)
        doi_chieu = sum(ket_qua_chung[N]["dem"])
        if N == 1:
            _in_bang(k, TRAN_IP_MONG, "ĐẠT")
            ket("A5.%d" % N, "ĐỐI CHỨNG DƯƠNG N=1: bản đột biến cho ĐÚNG %d — nó chỉ đổi LỚP KHO, "
                "không đổi phần quyết định" % tong,
                DAT if (tong == TRAN_IP_MONG and dat and not any(k["ma_la"])) else HONG,
                "từng bản qua %s ⇒ TỔNG %d · luật phán: %s · đối chiếu A2.1 (bản THẬT, N=1) = %d. "
                "Hai số BẰNG NHAU ở N=1 là điều PHẢI đúng: một tiến trình thì hai lớp kho là một."
                % (k["dem"], tong, vi, doi_chieu),
                nhom="tu-kiem-dot-bien", chieu="duong")
            continue
        _in_bang(k, TRAN_IP_MONG, "HỎNG")
        ket("A5.%d" % N, "N=%d bản ĐỘT BIẾN (kho bộ nhớ): TỔNG = %d = %d × %d, luật phán trả HỎNG"
            % (N, tong, N, TRAN_IP_MONG),
            DAT if (tong == N * TRAN_IP_MONG and not dat and not any(k["ma_la"])) else HONG,
            "từng bản qua %s ⇒ TỔNG %d (mong %d) · luật phán: %s · đối chiếu A2.%d (CÙNG bộ bắn, "
            "CÙNG trần, CÙNG số bản, chỉ khác LỚP KHO) = %d. HAI SỐ KHÁC NHAU nghĩa là bộ đo PHÂN "
            "BIỆT ĐƯỢC 'đếm chung' với 'đếm riêng'; và luật phán PHẢI trả HỎNG trên con số nhân — "
            "nếu nó trả ĐẠT thì cổng này là cổng HỎNG SẴN."
            % (k["dem"], tong, N * TRAN_IP_MONG, vi, N, doi_chieu),
            nhom="tu-kiem-dot-bien", chieu="am")
    # A5.TK — HỆ QUẢ LÊN MÃ THOÁT, kiểm bằng máy chứ không bằng lời. `main()` trả 1 khi có BẤT KỲ
    # ca HỎNG nào; ở đây ta cho chính những con số ĐO ĐƯỢC TRÊN BẢN ĐỘT BIẾN đi qua ĐÚNG luật phán
    # mà A2 dùng, rồi đếm xem có bao nhiêu ca sẽ HỎNG. Nếu con số này là 0 thì câu "bộ đo PHẢI đỏ"
    # chỉ là một lời hứa, không phải một phép đo.
    se_hong = [N for N in (1, 2, 4, 8)
               if not phan_quyet_tran_chung(sum(ra[N]["dem"]), TRAN_IP_MONG)[0]]
    ket("A5.TK", "HỆ QUẢ MÃ THOÁT: nếu sản phẩm quay lại kho bộ nhớ, bộ đo trả mã thoát 1",
        DAT if se_hong == [2, 4, 8] else HONG,
        "đưa các tổng ĐO ĐƯỢC TRÊN BẢN ĐỘT BIẾN (%s) qua ĐÚNG luật phán của A2 ⇒ ca sẽ HỎNG: %s "
        "⇒ `main()` trả 1. N = 1 KHÔNG nằm trong danh sách này, và đó là điều PHẢI đúng: một tiến "
        "trình thì hai lớp kho là một, nên nó không phân biệt được — đúng lý do phải đo N ≥ 2."
        % ([sum(ra[N]["dem"]) for N in (1, 2, 4, 8)], se_hong),
        nhom="tu-kiem-dot-bien", chieu="am")
    return ra


# ===============================================================================================
# A6 — CỬA SỔ TRƯỢT
# ===============================================================================================
def a6_cua_so_truot():
    muc("A6. CỬA SỔ TRƯỢT — chứng minh bằng cách đẩy MỐC CỦA TỪNG DÒNG, không bằng lời")
    nen = dung_nen(nen_tam("truot"))
    kq = {}
    # (0) Tiêu hết trần — ca này canh chính cái nền của A6: nếu chưa tiêu hết thì mọi ca dưới
    #     đều đo trên một kho chưa đầy và "nhả suất" sẽ không chứng minh gì.
    sv = mo_may_chu(nen, tien_to="a6-0")
    try:
        qua = 0
        for i in range(TRAN_IP_MONG + 2):
            ma, _, _ = goi_dang_nhap(sv["cong"], "g21-a6-%d-%d" % (i, os.getpid()))
            if ma == 401:
                qua += 1
            else:
                break
    finally:
        tat_tien_trinh(sv["p"])
    trong_csdl = len(luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG))
    ket("A6.0", "Nền của A6: tiêu hết ĐÚNG %d suất, kho có ĐÚNG %d dòng trong cửa sổ"
        % (TRAN_IP_MONG, TRAN_IP_MONG),
        DAT if qua == TRAN_IP_MONG and trong_csdl == TRAN_IP_MONG else HONG,
        "máy chủ cho qua %d lượt (mong %d) · bộ đo đếm thẳng CSDL: %d dòng `%s` (mong %d)"
        % (qua, TRAN_IP_MONG, trong_csdl, khoa_ip(), TRAN_IP_MONG),
        nhom="cua-so-truot", chieu="duong")
    kq["tieu_het"] = qua == TRAN_IP_MONG and trong_csdl == TRAN_IP_MONG
    # (1) Đẩy MỌI dòng lùi 250 giây — VẪN trong cửa sổ 300 giây. Cửa sổ CỐ ĐỊNH (bộ đếm + mốc đầu
    #     cửa sổ) không thể biểu diễn việc này; cửa sổ TRƯỢT thì `Retry-After` phải co lại ~50.
    n_lui = lui_moc(nen, khoa_ip(), so_dong=TRAN_IP_MONG, giay=250)
    rows = luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG)
    cu = min(rows) if rows else None
    sv = mo_may_chu(nen, tien_to="a6-1")
    try:
        du_doan = int(cu + CUA_SO_MONG - time.time()) + 1 if cu is not None else None
        ma, than, hdr = goi_dang_nhap(sv["cong"], "g21-a6-sau-%d" % os.getpid())
        chan_sau = {"ma": ma, "hdr": hdr,
                    "chieu": (json.loads(than.decode("utf-8")).get("chieu") if ma == 429 else None)}
    finally:
        tat_tien_trinh(sv["p"])
    retry = chan_sau["hdr"].get("Retry-After")
    ok_retry = (chan_sau["ma"] == 429 and retry is not None and du_doan is not None
                and abs(int(retry) - du_doan) <= 3 and int(retry) < 150)
    kq["retry_truot"] = ok_retry
    ket("A6b", "Cửa sổ TRƯỢT: sau khi đẩy MỌI dòng lùi 250 giây, `Retry-After` co còn ~%s giây "
        "(KHÔNG phải ~%d)" % (retry, CUA_SO_MONG),
        DAT if ok_retry else HONG,
        "đã lùi %d dòng · vẫn 429: %s · `Retry-After` máy chủ trả = %s · bộ đo ĐỘC LẬP tính từ "
        "CSDL (dòng cũ nhất còn trong cửa sổ + %d − bây giờ + 1) = %s · lệch ≤ 3 giây. Cửa sổ CỐ "
        "ĐỊNH neo ở lượt ĐẦU sẽ trả ~%d ở đây; một bộ đếm không có mốc từng dòng thì KHÔNG THỂ "
        "trả %s." % (n_lui, chan_sau["ma"] == 429, retry, CUA_SO_MONG, du_doan, CUA_SO_MONG, retry),
        nhom="cua-so-truot", chieu="duong")
    # (3) Đẩy 7 dòng CŨ NHẤT ra HẲN khỏi cửa sổ ⇒ phải nhả ĐÚNG 7 suất, rồi chặn lại.
    n2 = lui_moc(nen, khoa_ip(), so_dong=7, giay=400)
    con_trong = len(luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG))
    sv = mo_may_chu(nen, tien_to="a6-2")
    try:
        qua3, chan3 = 0, None
        for i in range(30):
            ma, than, hdr = goi_dang_nhap(sv["cong"], "g21-a6b-%d-%d" % (i, os.getpid()))
            if ma == 401:
                qua3 += 1
            else:
                chan3 = {"ma": ma, "hdr": hdr}
                break
    finally:
        tat_tien_trinh(sv["p"])
    ok_nha = (n2 == 7 and con_trong == TRAN_IP_MONG - 7 and qua3 == 7 and chan3
              and chan3["ma"] == 429)
    kq["nha_dung_7"] = ok_nha
    ket("A6a", "Cửa sổ TRƯỢT: đẩy ĐÚNG 7 dòng cũ nhất ra khỏi cửa sổ ⇒ nhả ĐÚNG 7 suất rồi chặn lại",
        DAT if ok_nha else HONG,
        "đã lùi %d dòng · bộ đo tự đếm trong cửa sổ: %d dòng (trần %d) · máy chủ cho qua ĐÚNG %d "
        "lượt rồi 429 (mã %s). Một bộ đếm NGUYÊN KHỐI theo cửa sổ sẽ nhả 0 hoặc cả %d — không "
        "bao giờ đúng 7." % (n2, con_trong, TRAN_IP_MONG, qua3, chan3 and chan3["ma"],
                            TRAN_IP_MONG),
        nhom="cua-so-truot", chieu="duong")
    # (4) Đẩy nốt phần còn lại ra khỏi cửa sổ ⇒ nhả HẾT (đúng trần), rồi chặn lại.
    lui_moc(nen, khoa_ip(), so_dong=10 ** 6, giay=400)
    con_lai = len(luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG))
    sv = mo_may_chu(nen, tien_to="a6-3")
    try:
        qua4, chan4 = 0, None
        for i in range(TRAN_IP_MONG + 4):
            ma, _, _ = goi_dang_nhap(sv["cong"], "g21-a6c-%d-%d" % (i, os.getpid()))
            if ma == 401:
                qua4 += 1
            else:
                chan4 = ma
                break
    finally:
        tat_tien_trinh(sv["p"])
    ok_het = con_lai == 0 and qua4 == TRAN_IP_MONG and chan4 == 429
    kq["nha_het"] = ok_het
    ket("A6c", "Cửa sổ TRƯỢT: đẩy HẾT ra khỏi cửa sổ ⇒ nhả ĐÚNG trần (%d) rồi chặn lại"
        % TRAN_IP_MONG,
        DAT if ok_het else HONG,
        "bộ đo tự đếm trong cửa sổ: %d dòng · máy chủ cho qua %d lượt rồi mã %s"
        % (con_lai, qua4, chan4),
        nhom="cua-so-truot", chieu="duong")
    # (5) ĐỐI CHỨNG ÂM: KHÔNG đẩy mốc thì phải là 0 suất. Không có ca này thì A6a/A6c có thể xanh
    #     vì một lý do khác hẳn (ví dụ bộ đo tự xoá sạch kho trước mỗi lượt).
    con_nay = len(luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG))
    sv = mo_may_chu(nen, tien_to="a6-4")
    try:
        ma_am, _, _ = goi_dang_nhap(sv["cong"], "g21-a6-am-%d" % os.getpid())
    finally:
        tat_tien_trinh(sv["p"])
    ok_am = ma_am == 429 and con_nay == TRAN_IP_MONG
    kq["am_khong_lui"] = ok_am
    ket("A6d", "ĐỐI CHỨNG ÂM: KHÔNG đẩy mốc ⇒ 0 suất (kho vẫn đầy %d dòng)" % TRAN_IP_MONG,
        DAT if ok_am else HONG,
        "trong cửa sổ: %d dòng · lượt gọi trả mã %s (mong 429). Ca này chặn kịch bản 'A6a/A6c "
        "xanh vì bộ đo vô tình xoá kho trước mỗi lượt'." % (con_nay, ma_am),
        nhom="cua-so-truot", chieu="am")
    return kq


# ===============================================================================================
# A7 — KHỞI ĐỘNG LẠI
# ===============================================================================================
def a7_khoi_dong_lai():
    muc("A7. KHỞI ĐỘNG LẠI tiến trình ⇒ trạng thái CÒN (+ đối chứng dương: CSDL mới thì qua)")
    nen = dung_nen(nen_tam("restart"))
    sv = mo_may_chu(nen, tien_to="a7-1")
    pid1 = sv["pid"]
    try:
        qua = 0
        for i in range(TRAN_IP_MONG + 2):
            ma, _, _ = goi_dang_nhap(sv["cong"], "g21-a7-%d-%d" % (i, os.getpid()))
            if ma == 401:
                qua += 1
            else:
                break
    finally:
        tat_tien_trinh(sv["p"])
    trong_cua_so = len(luot_trong_cua_so(nen, khoa_ip(), CUA_SO_MONG))
    sv2 = mo_may_chu(nen, tien_to="a7-2")      # TIẾN TRÌNH MỚI, CÙNG CSDL
    try:
        ma2, than2, hdr2 = goi_dang_nhap(sv2["cong"], "g21-a7-moi-%d" % os.getpid())
    finally:
        tat_tien_trinh(sv2["p"])
    ok_con = (qua == TRAN_IP_MONG and ma2 == 429 and trong_cua_so == TRAN_IP_MONG
              and pid1 != sv2["pid"])
    ket("A7a", "Tiến trình MỚI (pid %d ≠ %d) trên CSDL CŨ: lượt ĐẦU TIÊN đã bị chặn 429"
        % (sv2["pid"], pid1),
        DAT if ok_con else HONG,
        "bản cũ tiêu hết %d/%d suất rồi bị tắt · bộ đo tự đếm lại từ đĩa: %d dòng còn trong cửa "
        "sổ · bản MỚI trả mã %s, `Retry-After`=%s. Kho trong BỘ NHỚ sẽ cho qua ở đây (bản đột "
        "biến A5 chứng minh điều đó)."
        % (qua, TRAN_IP_MONG, trong_cua_so, ma2, hdr2.get("Retry-After")),
        nhom="khoi-dong-lai", chieu="am")
    # ĐỐI CHỨNG DƯƠNG: CSDL MỚI TINH ⇒ lượt đầu phải QUA.
    nen2 = dung_nen(nen_tam("restart-moi"))
    truoc_khi_ban = len(luot_trong_cua_so(nen2, khoa_ip(), CUA_SO_MONG))
    sv3 = mo_may_chu(nen2, tien_to="a7-3")
    try:
        ma3, _, hdr3 = goi_dang_nhap(sv3["cong"], "g21-a7-tinh-%d" % os.getpid())
    finally:
        tat_tien_trinh(sv3["p"])
    sau_khi_ban = len(luot_trong_cua_so(nen2, khoa_ip(), CUA_SO_MONG))
    ket("A7b", "ĐỐI CHỨNG DƯƠNG: tiến trình mới trên CSDL MỚI TINH ⇒ lượt đầu QUA (401)",
        DAT if (ma3 == 401 and hdr3.get("Retry-After") is None
                and truoc_khi_ban == 0 and sau_khi_ban == 1) else HONG,
        "mã %s · kho đếm ĐỘC LẬP bằng `sqlite3`: TRƯỚC khi bắn %d dòng, SAU khi bắn %d dòng "
        "(mong 0 rồi 1) · `Retry-After`=%r (mong None). Thiếu ca này thì A7a có thể xanh chỉ vì "
        "'máy chủ này luôn trả 429'."
        % (ma3, truoc_khi_ban, sau_khi_ban, hdr3.get("Retry-After")),
        nhom="khoi-dong-lai", chieu="duong")
    return {"con": ok_con, "moi_thi_qua": ma3 == 401}


# ===============================================================================================
# A8 — HÌNH DẠNG PHẢN HỒI KHI CHẠM TRẦN
# ===============================================================================================
def a8_hinh_dang_429():
    muc("A8. PHẢN HỒI KHI CHẠM TRẦN — `Retry-After` · `X-RateLimit-*` · `chieu`")
    nen = dung_nen(nen_tam("hinh-dang"))
    sv = mo_may_chu(nen, tien_to="a8")
    try:
        qua, chan = 0, None
        for i in range(TRAN_IP_MONG + 2):
            ma, than, hdr = goi_dang_nhap(sv["cong"], "g21-a8-%d-%d" % (i, os.getpid()))
            if ma == 401:
                qua += 1
            else:
                chan = {"ma": ma, "than": than, "hdr": hdr}
                break
    finally:
        tat_tien_trinh(sv["p"])
    than_j = json.loads(chan["than"].decode("utf-8")) if chan and chan["ma"] == 429 else {}
    ra = chan["hdr"].get("Retry-After") if chan else None
    ok = (chan and chan["ma"] == 429 and ra is not None and str(ra).isdigit() and int(ra) >= 1
          and chan["hdr"].get("X-RateLimit-Remaining") == "0"
          and chan["hdr"].get("X-RateLimit-Limit") == str(TRAN_IP_MONG)
          and chan["hdr"].get("X-RateLimit-Window") == str(CUA_SO_MONG)
          and than_j.get("chieu") == "ip" and isinstance(than_j.get("cho_bao_lau_giay"), int))
    ket("A8", "Lượt bị chặn mang ĐỦ `Retry-After` + `X-RateLimit-*` + `chieu` trong thân",
        DAT if ok else HONG,
        "mã %s · `Retry-After`=%r · `X-RateLimit-Limit`=%r · `X-RateLimit-Remaining`=%r · "
        "`X-RateLimit-Window`=%r · thân: chieu=%r cho_bao_lau_giay=%r. `Retry-After` là header "
        "CHUẨN cho 429 — thiếu nó thì bên gọi không biết chờ bao lâu và sẽ đập lại ngay."
        % (chan and chan["ma"], ra, chan and chan["hdr"].get("X-RateLimit-Limit"),
           chan and chan["hdr"].get("X-RateLimit-Remaining"),
           chan and chan["hdr"].get("X-RateLimit-Window"), than_j.get("chieu"),
           than_j.get("cho_bao_lau_giay")),
        nhom="hinh-dang-429", chieu="am")
    # ĐỐI CHỨNG DƯƠNG: lượt ĐƯỢC QUA không được mang `Retry-After` (nếu không, header vô nghĩa).
    nen2 = dung_nen(nen_tam("hinh-dang-duong"))
    sv2 = mo_may_chu(nen2, tien_to="a8b")
    try:
        ma2, _, hdr2 = goi_dang_nhap(sv2["cong"], "g21-a8b-%d" % os.getpid())
    finally:
        tat_tien_trinh(sv2["p"])
    ket("A8b", "ĐỐI CHỨNG DƯƠNG: lượt ĐƯỢC QUA (401) KHÔNG mang `Retry-After`",
        DAT if ma2 == 401 and hdr2.get("Retry-After") is None else HONG,
        "mã %s · `Retry-After`=%r (mong None). Nếu lượt ĐƯỢC QUA cũng mang `Retry-After` thì "
        "header đó thành vô nghĩa: bên gọi không phân biệt được 'chờ đi' với 'cứ gọi tiếp'."
        % (ma2, hdr2.get("Retry-After")),
        nhom="hinh-dang-429", chieu="duong")
    # A8c — GHI LẠI MỘT SỰ THẬT CỦA HỢP ĐỒNG ĐANG CÓ, không phải một lời khen.
    khong_co_429 = all(hdr2.get(t) is None for t in
                       ("X-RateLimit-Limit", "X-RateLimit-Window", "X-RateLimit-Remaining"))
    ket("A8c", "SỰ THẬT ĐO ĐƯỢC: lượt ĐƯỢC QUA **KHÔNG** mang nhóm `X-RateLimit-*` — chỉ lượt 429 mới mang",
        DAT if khong_co_429 else HONG,
        "trên lượt 401: `X-RateLimit-Limit`=%r · `X-RateLimit-Window`=%r · `X-RateLimit-Remaining`=%r"
        " (cả ba None). GHI CHÚ CHO AG-00 (KHÔNG phải lỗi tôi tự sửa): với hợp đồng này, bên gọi "
        "**không biết được ngân sách còn lại TRƯỚC khi bị chặn** — muốn biết phải chạm trần. Đây "
        "là mô tả trung thực của hành vi đang có, và là lý do A1/A7 phải đọc trần từ CHÍNH lượt 429."
        % (hdr2.get("X-RateLimit-Limit"), hdr2.get("X-RateLimit-Window"),
           hdr2.get("X-RateLimit-Remaining")))
    return ok


# ===============================================================================================
# A9 — `408` → `timeout=True` (§42), ĐO QUA STUB LOOPBACK THẬT
# ===============================================================================================
CRED_GIA = {"apiAccount": "ACC-G21-AG04-GIA", "privateKey": "KHOA-G21-AG04-GIA",
            "customerCode": "CC-G21-AG04", "password": "MK-G21-AG04-GIA"}
DON_GIA = {"ma_don": "G21-AG04-1", "nguoi_gui_ten": "Shop Đo", "nguoi_gui_sdt": "0901111111",
           "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Đo",
           "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
           "hang_hoa": "Áo đo", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
           "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
           "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa"}


def a9_408_timeout():
    muc("A9. `408` → `timeout=True` (§42 SHARED_CONTRACTS) — qua STUB loopback thật")
    for p in (GOC_APP, os.path.join(GOC_APP, "thu")):
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import stub_jt
        import adapter_jt as aj
        import http_jt as http_that
        import loi_hang as lh
        import transport as tp
    except Exception as e:                                                  # noqa: BLE001
        return ket("A9", "`408` → `timeout=True`", BO_QUA,
                   "không nhập được stub/adapter: %r — ca này KHÔNG được tính là đạt" % (e,))
    print("  Stub J&T của dự án tự chặn mọi `host` khác `127.0.0.1`/`localhost`; cổng do hệ cấp.")
    print("  Đây là ĐƯỜNG DUY NHẤT được phép chạm tới một 'hãng' — và nó là stub cục bộ.")

    def _goi_qua_stub(che_do, them_header=None):
        with stub_jt.StubJT(che_do, them_header=them_header) as stub:
            ad = aj.AdapterJT(dict(CRED_GIA), "mock")
            yc = ad.yeu_cau_tao_don(dict(DON_GIA))
            with aj.DungDiemCuoiTam(stub.goc):
                yc["url"] = aj.url_cua("createOrder", "sandbox")
            t0 = time.time()
            kq = ad._goi_that(http_that, "createOrder", yc)
            return kq, time.time() - t0, stub

    def _lop_http(che_do):
        with stub_jt.StubJT(che_do) as stub:
            try:
                http_that.gui_form(stub.url, {"apiAccount": "A", "digest": "d" * 24,
                                              "timestamp": "1792054650790"},
                                   {"bizContent": "{}"}, timeout=5)
                return "khong-nem", None
            except tp.LoiTamThoi as e:
                return "tam-thoi", getattr(e, "ma_http", None)
            except tp.LoiVinhVien:
                return "vinh-vien", None

    kq408, giay408, _ = _goi_qua_stub(stub_jt.StubJT.HTTP_408)
    c408 = kq408.tho.get("loi_chuan", {})
    loai408, ma408 = _lop_http(stub_jt.StubJT.HTTP_408)
    chuan = lh.tu_http(408)
    ok408 = (kq408.ok is False and kq408.timeout is True and ma408 == 408 and loai408 == "tam-thoi"
             and chuan.ma_chuan == lh.HET_GIO and chuan.co_the_thu_lai is True
             and c408.get("ma_chuan") == lh.HET_GIO and c408.get("co_the_thu_lai") is True
             and c408.get("http_status") == 408 and giay408 < 5.0)
    ket("A9a", "`408` ⇒ adapter phát `timeout=True` (KHÔNG BIẾT kết quả) — đúng ý định §42",
        DAT if ok408 else HONG,
        "adapter: `ok`=%s · `timeout`=%s · `ma_chuan`=%r · `co_the_thu_lai`=%r · `http_status`=%r "
        "· mất %.2f giây (lớp HTTP KHÔNG được tự ngủ) · lớp `http_jt`: %s mã %s (mong 'tam-thoi' "
        "408) · `loi_hang.tu_http(408)`: ma_chuan=%r co_the_thu_lai=%r"
        % (kq408.ok, kq408.timeout, c408.get("ma_chuan"), c408.get("co_the_thu_lai"),
           c408.get("http_status"), giay408, loai408, ma408, chuan.ma_chuan, chuan.co_the_thu_lai),
        nhom="408-timeout", chieu="am")
    # ĐỐI CHỨNG DƯƠNG 1: 429 KHÁC 408 — hãng TỪ CHỐI rõ ràng ⇒ `timeout=False`.
    kq429, _, _ = _goi_qua_stub(stub_jt.StubJT.HTTP_429)
    c429 = kq429.tho.get("loi_chuan", {})
    ket("A9b", "ĐỐI CHỨNG DƯƠNG: `429` ⇒ `timeout=False` (hãng TỪ CHỐI rõ ràng, KHÁC `408`)",
        DAT if (kq429.ok is False and kq429.timeout is False
                and c429.get("co_the_thu_lai") is True) else HONG,
        "adapter: `ok`=%s · `timeout`=%s (mong False) · `co_the_thu_lai`=%r (mong True — 429 là "
        "TẠM THỜI). Hai mã cùng 'tạm thời' nhưng KHÁC nhau ở `timeout`: gộp chúng làm một là "
        "khuôn lệch mà §42 đã bác." % (kq429.ok, kq429.timeout, c429.get("co_the_thu_lai")),
        nhom="408-timeout", chieu="duong")
    # ĐỐI CHỨNG DƯƠNG 2: 400 VẪN là vĩnh viễn — quyết định §42 KHÔNG nới các 4xx khác.
    kq400, _, _ = _goi_qua_stub(stub_jt.StubJT.HTTP_400)
    loai400, _ = _lop_http(stub_jt.StubJT.HTTP_400)
    chuan400 = lh.tu_http(400)
    ket("A9c", "ĐỐI CHỨNG DƯƠNG: `400` VẪN là VĨNH VIỄN — §42 chỉ tách `408`/`429`, không nới 4xx",
        DAT if (loai400 == "vinh-vien" and chuan400.co_the_thu_lai is False
                and kq400.timeout is False) else HONG,
        "lớp `http_jt`: %s (mong 'vinh-vien') · `loi_hang.tu_http(400)`: ma_chuan=%r "
        "co_the_thu_lai=%r · adapter `timeout`=%s. Ca này chặn kịch bản 'A9a xanh vì MỌI 4xx đều "
        "bị coi là tạm thời'." % (loai400, chuan400.ma_chuan, chuan400.co_the_thu_lai, kq400.timeout),
        nhom="408-timeout", chieu="duong")
    return ok408


# ===============================================================================================
# A10 — HỒI QUY: BA BỘ THỬ GIỚI HẠN CỦA DỰ ÁN, LỆNH THẬT + MÃ THOÁT THẬT
# ===============================================================================================
BO_HOI_QUY = ("thu_gioi_han.py", "thu_han_muc_nguyen_tu.py", "thu_g19_gioihan.py")


def a10_hoi_quy():
    muc("A10. HỒI QUY — ba bộ thử giới hạn của dự án, chạy bằng LỆNH THẬT")
    print("  Đây KHÔNG phải cổng đối chiếu độc lập (chúng do người viết mã viết) — chúng ở đây để")
    print("  chứng minh bộ đo của tôi KHÔNG hồi quy thứ đang có. Con số ca được đếm từ output THẬT.")
    ra = {}
    for ten in BO_HOI_QUY:
        duong = os.path.join(GOC_APP, "thu", ten)
        if not os.path.exists(duong):
            ket("A10." + ten, "%s — KHÔNG TỒN TẠI" % ten, BO_QUA,
                "tệp %s không có trên cây này ⇒ ca này KHÔNG được tính là đạt" % duong)
            continue
        t0 = time.time()
        p = chay([sys.executable, duong], gio=3600,
                 env=moi_truong_sach(VIP_HUB_DATA=nen_tam("hq-" + ten.replace(".py", ""))))
        giay = time.time() - t0
        ra[ten] = p.returncode
        than = (p.stdout or "") + (p.stderr or "")
        # Đếm ca bằng HAI khuôn, vì ba bộ thử có hai kiểu dòng tổng kết khác nhau: `unittest`
        # in `Ran N tests`, còn bộ của làn G19 in `N ca — ĐẠT`. Chỉ nhận một khuôn thì bộ thứ ba
        # hiện ra `None ca` — một con số TRÔNG NHƯ ĐO ĐƯỢC mà thực ra là bộ đếm mù.
        m = re.search(r"Ran (\d+) tests?", than)
        so_ca = int(m.group(1)) if m else None
        if so_ca is None:
            m = re.search(r"^\s*(\d+) ca\b", than, re.M)
            so_ca = int(m.group(1)) if m else 0
        m = re.search(r"skipped=(\d+)", than)
        so_skip = int(m.group(1)) if m else 0
        ket("A10." + ten, "%s — mã thoát %d" % (ten, p.returncode),
            DAT if p.returncode == 0 and so_ca > 0 else HONG,
            "$ python3 app/thu/%s  →  mã thoát %d · %d ca · %d skip · %.1f giây · dòng cuối: %r"
            % (ten, p.returncode, so_ca, so_skip, giay,
               [d for d in than.splitlines() if d.strip()][-1:] or ""),
            nhom="hoi-quy", chieu="duong")
    return ra


# ===============================================================================================
# A11 — SỔ ĐỐI CHỨNG
# ===============================================================================================
def a11_doi_chung():
    muc("A11. SỔ ĐỐI CHỨNG — mọi nhóm ca ÂM phải có ca DƯƠNG (chốt (b))")
    for k in sorted(DOI_CHUNG):
        v = DOI_CHUNG[k]
        print("  [sổ] %-22s âm=%d dương=%d" % (k, v["am"], v["duong"]))
    # ĐỐI CHỨNG DƯƠNG CỦA CHÍNH PHÉP KIỂM: một nhóm ÂM cố ý thiếu DƯƠNG PHẢI bị bắt...
    gia = dict(DOI_CHUNG)
    gia["nhom-gia-thieu-duong"] = {"am": 1, "duong": 0}
    bat = nhom_thieu_duong(gia)
    # ...và một nhóm đã đủ hai chiều KHÔNG được báo động giả.
    thanh = {"du": {"am": 1, "duong": 1}, "chi-duong": {"am": 0, "duong": 3},
             "rong": {"am": 0, "duong": 0}}
    khong_bao_dong = nhom_thieu_duong(thanh)
    thieu = nhom_thieu_duong(DOI_CHUNG)
    ket("A11a", "Phép kiểm 'thiếu đối chứng dương' có RĂNG và KHÔNG báo động giả",
        DAT if bat == ["nhom-gia-thieu-duong"] and khong_bao_dong == [] else HONG,
        "nhóm ÂM cố ý thiếu DƯƠNG ⇒ bắt được %r (mong ['nhom-gia-thieu-duong']) · nhóm đủ hai "
        "chiều / chỉ có DƯƠNG / rỗng ⇒ %r (mong [])" % (bat, khong_bao_dong))
    ket("A11b", "MỌI nhóm có ca ÂM trên cây này đều có ca DƯƠNG đi kèm",
        DAT if not thieu else HONG,
        "nhóm thiếu DƯƠNG: %s · sổ đầy đủ: %s" % (thieu or "KHÔNG CÓ", dict(sorted(DOI_CHUNG.items()))))
    return thieu


# ===============================================================================================
# A12 — TỔNG KẾT + BẰNG CHỨNG
# ===============================================================================================
def a12_tong_ket(giay):
    muc("A12. TỔNG KẾT + BẰNG CHỨNG")
    print("  BẢNG N / TỔNG LƯỢT QUA / TRẦN KHAI BÁO")
    print("  %-10s %-4s %-14s %-14s %-8s" % ("chiều", "N", "tổng lượt qua", "trần khai báo", "phán"))
    for chieu, N, tong, tran, kl in BANG_N:
        print("  %-10s %-4d %-14d %-14d %-8s" % (chieu, N, tong, tran, kl))
    print("\n  BẰNG CHỨNG DẠNG 'LỆNH THẬT + MÃ THOÁT THẬT' (%d lượt chạy, gộp lệnh trùng):"
          % len(LENH))
    gop = {}
    for lenh, ma in LENH:
        gop[(lenh, ma)] = gop.get((lenh, ma), 0) + 1
    for (lenh, ma), n in gop.items():
        print("    mã thoát %-3d ×%-3d ← %s" % (ma, n, lenh))
    khac0 = sorted({ma for _, ma in LENH if ma != 0})
    print("    (mã thoát KHÁC 0 đã gặp: %s)" % (khac0 or "KHÔNG CÓ"))
    so = {DAT: 0, HONG: 0, BO_QUA: 0, KHUYET: 0}
    for k in KQ:
        so[k["trang_thai"]] += 1
    hong = [k["ma"] for k in KQ if k["trang_thai"] == HONG]
    print("\n  ca ĐẠT=%d · HỎNG=%d · BỎ QUA=%d · KHUYẾT=%d · TỔNG=%d"
          % (so[DAT], so[HONG], so[BO_QUA], so[KHUYET], len(KQ)))
    if hong:
        print("  CA HỎNG: %s" % ", ".join(hong))
    print("  thời gian: %.1f giây · HEAD: %s"
          % (giay, os.environ.get("VIP_G21_HEAD", "(không đặt)")))
    return so


# ===============================================================================================
# ĐIỀU KHIỂN
# ===============================================================================================
def _chay_phan(ma, ten, fn, *a):
    """Chạy một phần; phần nào NỔ thì ghi KHUYẾT và đi tiếp.

    Không có lớp này thì một lỗi ở A3 làm cả báo cáo trắng, và người đọc không phân biệt được
    'sản phẩm hỏng' với 'bộ đo hỏng'. KHUYẾT là kết luận DUY NHẤT đúng cho một phép đo không chạy.
    """
    try:
        return fn(*a)
    except SystemExit:
        raise
    except Exception as e:                                                  # noqa: BLE001
        import traceback
        return ket(ma, ten, KHUYET,
                   "phần này NỔ: %s: %s\n%s" % (type(e).__name__, e,
                                                traceback.format_exc()[-700:]))


def main():
    t0 = time.time()
    print("=" * 78)
    print("G21/AG-04 — CỔNG ĐỐI CHIẾU ĐỘC LẬP: GIỚI HẠN TẦN SUẤT QUA TIẾN TRÌNH")
    print("Trần khai báo (theo CHÍNH SÁCH SẢN PHẨM): ip=%d · dinh_danh=%d · cửa sổ=%d giây"
          % (TRAN_IP_MONG, TRAN_DINH_DANH_MONG, CUA_SO_MONG))
    print("=" * 78)
    nen = dung_nen(nen_tam("chot"))
    _chay_phan("A0", "Chốt an toàn", a0_chot_an_toan, nen)
    _chay_phan("A1", "Trần khai báo", a1_tran_khai_bao)
    a2 = _chay_phan("A2", "Chiều dùng chung", a2_chieu_chung) or {}
    _chay_phan("A4", "Chiều nhân theo bản", a4_chieu_rieng)
    _chay_phan("A5", "Tự kiểm bộ đo", a5_tu_kiem, a2)
    _chay_phan("A6", "Cửa sổ trượt", a6_cua_so_truot)
    _chay_phan("A7", "Khởi động lại", a7_khoi_dong_lai)
    _chay_phan("A8", "Hình dạng 429", a8_hinh_dang_429)
    _chay_phan("A9", "408 → timeout=True", a9_408_timeout)
    _chay_phan("A10", "Hồi quy", a10_hoi_quy)
    _chay_phan("A11", "Sổ đối chứng", a11_doi_chung)
    so = a12_tong_ket(time.time() - t0)
    return 1 if (so[HONG] or so[KHUYET]) else 0


if __name__ == "__main__":
    try:
        MA = main()
    finally:
        don_dep()
    sys.exit(MA)
