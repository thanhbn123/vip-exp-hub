#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — AG-03: CHE BÍ MẬT · BA ĐƯỜNG RA KHỎI TIẾN TRÌNH **ĐO ĐƯỢC** + CỔNG `G5` + RÀ ASSERTION.

VÌ SAO CÓ TỆP NÀY (và nó KHÁC tệp G21 ở đâu)
--------------------------------------------
`thu_g21_bimat.py` đã ĐO và VÁ năm đường rò, và nó có nhóm `G` chứng minh ca ĐỎ ĐƯỢC. Lượt G22
không viết lại chuyện đó. Ba việc của lượt này:

1. **Ba đường RA KHỎI TIẾN TRÌNH phải ĐO ĐƯỢC bằng chứng cứ trên ĐĨA, không bằng suy luận:**
   (i) thân HTTP 502 không chứa bí mật · (ii) tệp log trên đĩa không chứa bí mật · (iii) trường
   `duong` của dòng JSONL không chứa bí mật. Nhóm `A` đo cả ba; nhóm `B` chứng minh chúng ĐỎ ĐƯỢC
   bằng cách TIÊM LẠI đúng hành vi trước bản vá rồi chạy lại trên bản chưa vá.
2. **Cổng `G5` của AG-01** (`docs/QA_G21.md` §2.2, dòng 49): *"credential NGẮN của hãng KHÁC J&T
   không được rò"* — đo trên nền là **ĐỎ 2/5**. Nhóm `C` đo lại năm tổ hợp, đo **đối chứng không
   mù** (tầng theo TÊN và tầng theo ĐỘ DÀI phải còn sống), và ghim **biên giới còn lại**.
3. **RÀ LẠI TOÀN BỘ ASSERTION VỀ CHE BÍ MẬT** trong các bộ thử hiện có (Owner giao riêng): có
   assertion nào đang **ghim HÀNH VI CŨ** hoặc **quá lỏng** không? Nhóm `D` làm việc đó bằng MÁY
   (quét AST trên `app/thu/thu_*.py`), in ra sổ, và khẳng định từng chỗ đã biết.

BẤT BIẾN MỚI CỦA G22 — **ECHO THEO TÊN** (vá cổng `G5`)
-------------------------------------------------------
    Một trường trong PHẢN HỒI mang ĐÚNG cái TÊN mà TA ĐÃ GỬI ĐI, với ĐÚNG giá trị ta đã gửi dưới
    tên đó, là một bản ECHO của yêu cầu TA — không phải dữ liệu độc lập của hãng. Yêu cầu của ta
    có thể mang credential ở BẤT KỲ tên nào (hợp đồng hãng thứ hai CHƯA CÓ — `R-6`), nên giá trị
    echo ấy bị che BẤT KỂ ĐỘ DÀI. Luật này KHÔNG dùng danh sách từ khoá nào.

Vì sao KHÔNG vá bằng cách mở rộng `TRUONG_CREDENTIAL`: tầng theo TÊN chỉ đúng với những tên ĐÃ
BIẾT, nên một danh sách dài hơn vẫn là danh sách của J&T đội lốt. Vì sao KHÔNG vá bằng luật HÌNH
DẠNG giá trị: `VH12` cũng "trông giống khoá" và nó là mã vận đơn — hình dạng không phân biệt được.

HAI LUẬT TỰ ÁP (không có thì mọi dòng "✓" ở đây vô nghĩa)
---------------------------------------------------------
1. **ĐỐI CHỨNG DƯƠNG** cho MỌI ca phủ định: chuỗi không phải bí mật phải đi qua nguyên vẹn, dữ
   liệu của hãng phải nguyên văn, và bí mật phải THẬT SỰ có trên dây trước khi bị che. Sổ
   `DOI_CHUNG` ghi từng lượt; `Z_TongKet` tự phán HỎNG nếu một nhóm âm thiếu đối chứng.
2. **TỰ KIỂM BỘ ĐO** trong TIẾN TRÌNH CON: tiêm lại hành vi trước bản vá (nhóm `B`) rồi khẳng định
   ca phải ĐỎ; kèm đối chứng dương (không tiêm ⇒ XANH).

CHỐT AN TOÀN
------------
Mọi phép đo lớp HTTP chỉ chạm **stub `127.0.0.1` cổng OS cấp**; `ChanMang` đếm và CHẶN mọi lượt
nối ra ngoài vòng lặp. KHÔNG gọi API hãng (kể cả sandbox) — `V-G09-01`/`V-13906-05` CHƯA CẤP.
Mọi bí mật trong tệp này là chuỗi GIẢ tự đặt. CSDL là thư mục TẠM; không mở `CHO_PHEP_LIVE`;
không đụng `:5432`; không đọc `.env`.
"""
import ast
import contextlib
import gc
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import parse_qsl, quote, quote_plus, urlsplit

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
DU_AN = os.path.dirname(GOC)
G20_DAHANG = os.path.join(DU_AN, "trien_khai", "g20-dahang")            # làn AG-06 (stub hãng giả)

# =================================================================================================
# CSDL PHẢI NẰM TRONG THƯ MỤC TẠM — ĐẶT BIẾN Ở CẤP MÔ-ĐUN, TRƯỚC MỌI IMPORT CỦA `app/`
# =================================================================================================
# `cau_hinh.THU_MUC_DU_LIEU` được tính MỘT LẦN lúc `cau_hinh` được nạp (theo `adapter_jt`); đặt
# `VIP_HUB_DATA` SAU khi import là quá muộn và `csdl.mo()` sẽ mở `app/du-lieu/hub.db` — CSDL THẬT
# của dự án. Đó là lỗi đã xảy ra thật ở lượt G21 (`thu_g21_bimat` §4.2) và `Z5` ở đây canh lại.
_TAM_GOC_DO_TOI = "VIP_G22_TAM_GOC" not in os.environ
_TAM_GOC = (os.environ["VIP_G22_TAM_GOC"] if not _TAM_GOC_DO_TOI
            else tempfile.mkdtemp(prefix="vh-g22bimat-goc-"))
os.environ["VIP_HUB_DATA"] = _TAM_GOC
_DU_LIEU_THAT = os.path.join(GOC, "du-lieu")
_CSDL_THAT_TRUOC = {t: (os.path.exists(os.path.join(_DU_LIEU_THAT, t)),
                        os.path.getmtime(os.path.join(_DU_LIEU_THAT, t))
                        if os.path.exists(os.path.join(_DU_LIEU_THAT, t)) else None)
                    for t in ("hub.db", "hub.db-wal", "hub.db-shm")}
for _d in (GOC, THU, G20_DAHANG):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import adapter_jt as aj                                                 # noqa: E402
import cau_hinh                                                         # noqa: E402
import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402
from stub_hang_gia import KHOA_GIA_DAI, KHOA_GIA_NGAN, StubHangGia      # noqa: E402

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# `migrate` chạy trong tiến trình này và trong các con (env kế thừa). Bộ thử tự khai bằng
# `cau_hinh.khai_kho_kiem_thu()` — KHÔNG dựa vào việc người chạy nhớ `export VIP_KHO_DANG_CHAY`.
# `VIP_HUB_DATA` đã trỏ thư mục TẠM ở trên, nên hai chốt cô lập của hàm khai đều thoả.
cau_hinh.khai_kho_kiem_thu()

# =================================================================================================
# 0. BÍ MẬT GIẢ — mọi giá trị dưới đây do tệp này tự đặt, KHÔNG phải credential của ai
# =================================================================================================
BM_DAI = "BM-G22-DAI-7c4f10ab93d2"              # dài (>= ngưỡng 8)
BM_NGAN = "b7K2"                                # NGẮN (4) — chỗ ngưỡng độ dài bỏ sót
BM_MSG_HANG = "G22-KHOA-CUA-BAN-4e91ab"         # bí mật hãng echo lại trong `msg` của lượt 200
BM_QUERY = "BM-G22-QUERY-3a91f7c2d0e4"          # bí mật nằm trong QUERY
BM_DUONG = "BM-G22-DUONG-b5e83c1a9d47"          # bí mật nằm trong ĐƯỜNG DẪN
BM_HANG = "G22-HANG-GIUKHOA-8f2c1d"             # bí mật CỦA HÃNG (ta chưa từng gửi)
KHONG_BI_MAT = "VH000000002VN"                  # mã vận đơn — KHÔNG phải bí mật (đối chứng đường)
DUONG_THAT = "/webopenplatformapi/api/order/addOrder"
DUONG_HUB = "/api/v2/don"
ACC_GIA_DINH = "acct-gia-dinh-g22"
TS_GIA_DINH = "1700000000000"
CRED_GIA_DINH = {"apiAccount": ACC_GIA_DINH, "privateKey": BM_DAI,
                 "customerCode": "cc-gia-dinh", "password": BM_NGAN}
DON_MAU = {
    "ma_don": "G22-AD-1", "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Thử",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
    "hang_hoa": "Áo thử", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
    "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa",
}
# Năm tổ hợp của cổng `G5` — chép ĐÚNG năm tổ hợp mà AG-01 đo (`docs/QA_G21.md` §2.2), để hai bàn
# đo nói cùng một ngôn ngữ. Canary NGẮN/DÀI lấy từ `stub_hang_gia` của làn AG-06.
TO_HOP_G5 = (
    ("privateKey", KHOA_GIA_NGAN, "tên J&T + NGẮN"),
    ("x-mau-khoa-bi-mat", KHOA_GIA_NGAN, "tên HÃNG GIẢ + NGẮN"),
    ("maTaiKhoanGia", KHOA_GIA_NGAN, "tên HÃNG GIẢ 2 + NGẮN"),
    ("privateKey", KHOA_GIA_DAI, "tên J&T + DÀI (đối chứng dương)"),
    ("x-mau-khoa-bi-mat", KHOA_GIA_DAI, "tên HÃNG GIẢ + DÀI (đối chứng dương)"),
)

DOI_CHUNG = {}
SO_PHEP_DO = [0]
BANG = []


def doi_chung(nhom):
    DOI_CHUNG[nhom] = DOI_CHUNG.get(nhom, 0) + 1


def do():
    SO_PHEP_DO[0] += 1


def bang_ghi(duong, vi_tri, dang, ket_qua):
    BANG.append((duong, vi_tri, dang, ket_qua))


# =================================================================================================
# 1. BỘ DÒ RÒ RỈ — bản cài ĐỘC LẬP với mã sản phẩm (chỉ dùng mô tả GIAO THỨC)
# =================================================================================================
def cac_dang(s):
    """MỌI dạng mà `s` có thể mang trên dây / trong JSON — viết từ mô tả giao thức, KHÔNG gọi
    `http_jt._bien_the` (một bộ dò gọi chính hàm đang đo thì đột biến hàm đó sẽ tắt luôn bộ dò)."""
    ra = {s}
    lop = [s]
    for _ in range(2):
        moi = []
        for v in lop:
            for w in (quote_plus(v, safe=""), quote(v, safe=""),
                      json.dumps(v, ensure_ascii=True)[1:-1]):
                if w and w not in ra:
                    ra.add(w)
                    moi.append(w)
        lop = moi
    return ra


NOI_CO_THE_RO = ("str(e)", "repr(e)", "e.args", "than_da_che", "headers_da_che",
                 "mo_ta_yeu_cau", "__context__", "traceback")


def _cac_noi_ro(e, stdout="", stderr="", them=None):
    ra = {
        "str(e)": str(e),
        "repr(e)": repr(e),
        "e.args": str(getattr(e, "args", ())),
        "than_da_che": getattr(e, "than_da_che", b"").decode("utf-8", "replace"),
        "headers_da_che": str(getattr(e, "headers_da_che", {})),
        "mo_ta_yeu_cau": str(getattr(e, "mo_ta_yeu_cau", "")),
        "__context__": str(getattr(e, "__context__", None)),
        "traceback": "".join(traceback.format_exception(
            type(e), e, getattr(e, "__traceback__", None))),
        "stdout": stdout,
        "stderr": stderr,
    }
    for k, v in (them or {}).items():
        ra[k] = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    return ra


def tim_ro_ri(e, bi_mat, stdout="", stderr="", them=None):
    """→ danh sách `(nơi, dạng)` đã rò. RỖNG = sạch TRONG PHẠM VI các cửa đã liệt kê."""
    noi = _cac_noi_ro(e, stdout, stderr, them)
    ra = []
    for dang in sorted(cac_dang(bi_mat)):
        if not dang:
            continue
        for ten_noi in list(NOI_CO_THE_RO) + sorted((them or {})):
            if dang in noi[ten_noi]:
                ra.append((ten_noi, dang))
    return ra


# =================================================================================================
# 2. CHỐT CHẶN MẠNG — chỉ loopback, mọi lượt nối đều được ĐẾM
# =================================================================================================
def _la_loopback(host):
    return isinstance(host, str) and (host in ("localhost", "::1") or host.startswith("127."))


class ChanMang:
    def __init__(self):
        self._goc = None
        self.da_noi = []

    def bat(self):
        if self._goc is not None:
            return
        self._goc = socket.socket.connect
        goc, da_noi = self._goc, self.da_noi

        def connect(sock, dia_chi, *a, **kw):
            host = dia_chi[0] if isinstance(dia_chi, (tuple, list)) and dia_chi else dia_chi
            da_noi.append(host)
            if not _la_loopback(host):
                raise AssertionError(
                    f"CHẶN MẠNG G22: bộ thử định nối ra {dia_chi!r} — chỉ được loopback. "
                    "V-G09-01/V-13906-05 CHƯA CẤP: không có lượt gọi hãng nào được phép.")
            return goc(sock, dia_chi, *a, **kw)

        socket.socket.connect = connect

    def tat(self):
        if self._goc is not None:
            socket.socket.connect = self._goc
            self._goc = None

    def so_lan_ngoai_loopback(self):
        return sum(1 for h in self.da_noi if not _la_loopback(h))


CHAN = ChanMang()


# =================================================================================================
# 3. STUB CỤC BỘ — 127.0.0.1, cổng do OS cấp
# =================================================================================================
class _BoXuLy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StubG22/1.0"
    sys_version = ""

    def log_message(self, *a):
        pass

    def _nhan(self):
        try:
            dai = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            dai = 0
        than = self.rfile.read(dai) if dai > 0 else b""
        self.server.stub.yeu_cau.append({"duong_dan": self.path,
                                         "headers": list(self.headers.items()),
                                         "than": than})
        ma, than_ra, headers_them = self.server.stub.tra_loi(self)
        self.send_response(ma)
        for ten, gt in (headers_them or {}).items():
            self.send_header(ten, gt)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(than_ra)))
        self.end_headers()
        self.wfile.write(than_ra)
        self.wfile.flush()
        self.server.stub.da_tra_loi.append({"ma": ma, "than": than_ra,
                                            "headers": dict(headers_them or {})})

    do_POST = _nhan
    do_GET = _nhan
    do_PUT = _nhan


class Stub:
    """Máy chủ "nói nhiều" cục bộ. `tra_loi(bo_xu_ly)` → `(mã, thân, headers_them)`."""

    def __init__(self, tra_loi, host="127.0.0.1"):
        self.tra_loi = tra_loi
        self.yeu_cau = []
        self.da_tra_loi = []
        self._mc = ThreadingHTTPServer((host, 0), _BoXuLy)
        self._mc.stub = self
        self._mc.daemon_threads = True
        self.host = host
        self.cong = self._mc.server_address[1]
        threading.Thread(target=self._mc.serve_forever, kwargs={"poll_interval": 0.02},
                         daemon=True).start()

    @property
    def goc(self):
        return "http://%s:%d" % (self.host, self.cong)

    @property
    def url(self):
        return self.goc + DUONG_THAT

    def dung(self):
        try:
            self._mc.shutdown()
        except Exception:                                            # noqa: BLE001
            pass
        try:
            self._mc.server_close()
        except Exception:                                            # noqa: BLE001
            pass


def echo_tat(bo_xu_ly, ma=401, them_header=None):
    """Trả TOÀN BỘ yêu cầu (dòng yêu cầu + header + thân) trong thân phản hồi.

    Đọc từ bản ghi `yeu_cau`, KHÔNG đọc lại `rfile`: `_BoXuLy` đã đọc thân TRƯỚC khi gọi hàm này,
    nên lượt đọc thứ hai sẽ CHẶN tới hết hạn của khách và biến phép đo thành một lượt HẾT GIỜ —
    ngoại lệ hết giờ KHÔNG mang thân phản hồi nào, nên mọi phép dò rò rỉ đều "sạch" vô nghĩa.
    """
    ban_ghi = bo_xu_ly.server.stub.yeu_cau[-1]
    phan = ["%s: %s" % (ten, gt) for ten, gt in ban_ghi["headers"]]
    phan.append("PATH=" + ban_ghi["duong_dan"])
    phan.append("BODY=" + ban_ghi["than"].decode("utf-8", "replace"))
    return ma, "\n".join(phan).encode("utf-8"), (them_header or {})


# =================================================================================================
# 4. NỀN CA THỬ
# =================================================================================================
class CaGoc(unittest.TestCase):
    NHOM = ""

    def mo(self, tra_loi, **kw):
        stub = Stub(tra_loi, **kw)
        self.addCleanup(stub.dung)
        return stub

    def gui(self, url, headers=None, body=None, timeout=5.0):
        h = {"apiAccount": ACC_GIA_DINH, "timestamp": TS_GIA_DINH}
        if headers:
            h.update(headers)
        ra, rong = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(ra), contextlib.redirect_stderr(rong):
            try:
                kq = http_jt.gui_form(url, h, body if body is not None else {"bizContent": "{}"},
                                      timeout=timeout)
                return kq, None, ra.getvalue(), rong.getvalue()
            except Exception as e:                                   # noqa: BLE001
                return None, e, ra.getvalue(), rong.getvalue()

    def cho_tra_loi(self, stub, so=1, het_gio=3.0):
        han = time.time() + het_gio
        while len(stub.da_tra_loi) < so and time.time() < han:
            time.sleep(0.005)
        self.assertGreaterEqual(len(stub.da_tra_loi), so,
                                "stub chưa ghi nhận phản hồi nào sau %ss" % het_gio)
        return stub.da_tra_loi[-1]["than"]

    def khang_dinh_401(self, e, nhan):
        """Ca ÂM chỉ có nghĩa khi lượt gọi THẬT SỰ hỏng vì hãng TỪ CHỐI (HTTP 401), không vì treo."""
        self.assertIsNotNone(e, "%s: phải NÉM (stub trả 401)" % nhan)
        self.assertFalse(getattr(e, "timeout", False),
                         "%s: ngoại lệ là HẾT GIỜ, không phải 401 — ca âm vô nghĩa: %s" % (nhan, e))
        self.assertEqual(getattr(e, "ma_http", 0), 401,
                         "%s: ngoại lệ không mang mã 401 (nhận %r)" % (nhan, getattr(e, "ma_http", 0)))

    @staticmethod
    def _dang_mo_ta(bi_mat):
        if bi_mat == "":
            return "rỗng"
        if len(bi_mat) < http_jt.DAI_TOI_THIEU_DE_CHE:
            return "ngắn(%d)" % len(bi_mat)
        return "dài(%d)" % len(bi_mat)


# =================================================================================================
# 5. MÁY CHỦ HUB THẬT TRONG TIẾN TRÌNH CON — bằng chứng là TỆP LOG ĐỌC LẠI TỪ ĐĨA
# =================================================================================================
BOOT_SERVER = (
    "import sys\n"
    "sys.path.insert(0, %r)\n"
    "import server\n"
    "%s\n"
    "server.chay(%d)\n")


def dung_nen_tam(ten="vh-g22bimat-"):
    """Nền CSDL tạm + một cổng do OS cấp. KHÔNG BAO GIỜ `app/du-lieu/`."""
    tam = tempfile.mkdtemp(prefix=ten)
    env = dict(os.environ, VIP_HUB_DATA=tam)
    for lenh in ("migrate.py", "khoi_tao.py"):
        subprocess.run([sys.executable, os.path.join(GOC, lenh)], capture_output=True, text=True,
                       env=env, cwd=DU_AN)
    return tam


def dung_may_chu(tam, cong, dot_bien="", log=None):
    """Máy chủ THẬT trong tiến trình con, bind `127.0.0.1` cổng OS cấp.

    `dot_bien` là mã Python chèn TRƯỚC `server.chay(...)` — dùng để TIÊM LẠI hành vi trước bản vá
    và chứng minh phép đo ĐỎ ĐƯỢC (nhóm `B`).
    """
    log = log or os.path.join(tam, "server.log")
    f = open(log, "w")
    sv = subprocess.Popen([sys.executable, "-c", BOOT_SERVER % (GOC, dot_bien, cong)],
                          stdout=f, stderr=subprocess.STDOUT,
                          env=dict(os.environ, VIP_HUB_DATA=tam), cwd=DU_AN)
    het = time.time() + 25
    while time.time() < het:
        try:
            socket.create_connection(("127.0.0.1", cong), 0.3).close()
            return sv, log
        except OSError:
            if sv.poll() is not None:
                break
            time.sleep(0.2)
    try:
        sv.kill()
    except Exception:                                                # noqa: BLE001
        pass
    return None, log


def don_sach_thu_muc(thu_muc, lan=6, cho=0.25):
    """Xoá thư mục tạm và CHỜ cho nó ỔN ĐỊNH: SQLite WAL tạo lại `hub.db` khi một kết nối còn mở
    được đóng, nên "vừa xoá xong" chưa phải là "đã sạch" (đo được ở G21)."""
    for _ in range(lan):
        shutil.rmtree(thu_muc, True)
        gc.collect()
        time.sleep(cho)
        if not os.path.exists(thu_muc):
            time.sleep(cho)
            if not os.path.exists(thu_muc):
                return True
    return not os.path.exists(thu_muc)


def cong_roi():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def goi_hub(cong, duong, pt="GET", body=None):
    import urllib.error
    import urllib.request
    d = json.dumps(body).encode() if body is not None else None
    yc = urllib.request.Request("http://127.0.0.1:%d%s" % (cong, duong), data=d, method=pt)
    yc.add_header("X-Requested-With", "VIPHub")
    if d is not None:
        yc.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(yc, timeout=15) as ph:
            return ph.status, ph.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                           # noqa: BLE001
        return 0, str(e).encode()


def quet_thay_bi_mat(nen, bi_mat):
    """MỌI tệp trong nền tạm (log + CSDL + khoá) có chứa `bi_mat` không."""
    thay = []
    for goc, _, tep in os.walk(nen):
        for t in tep:
            p = os.path.join(goc, t)
            try:
                with open(p, "rb") as fh:
                    d = fh.read()
            except OSError:
                continue
            if bi_mat.encode("utf-8") in d:
                thay.append(p)
    return thay


def doc_jsonl(log):
    """→ danh sách các dòng JSONL `loai == "yeu_cau"` trong tệp log của máy chủ.

    ĐÂY LÀ CÁCH ĐO RIÊNG CHO YÊU CẦU (iii): trường `duong` của dòng JSONL là một ĐƯỜNG GHI KHÁC
    với dòng access log thô, nên nó phải được đọc và khẳng định riêng — quét cả tệp là không đủ.
    """
    ra = []
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            for dong in f:
                dong = dong.strip()
                if not dong.startswith("{"):
                    continue
                try:
                    ban = json.loads(dong)
                except ValueError:
                    continue
                if ban.get("loai") == "yeu_cau":
                    ra.append(ban)
    except OSError:
        pass
    return ra


# =================================================================================================
# 6. CHẠY MỘT CA TRONG TIẾN TRÌNH CON, TUỲ CHỌN TIÊM MỘT DÒNG ĐỘT BIẾN
# =================================================================================================
def chay_ca_trong_con(ten_ca, dot_bien=""):
    ma = (
        "import sys, unittest\n"
        "sys.path.insert(0, %r)\n"
        "sys.path.insert(0, %r)\n"
        "import thu_g22_bimat as T\n"
        "T.CHAN.bat()\n"
        "%s\n"
        "ca = unittest.TestLoader().loadTestsFromName(%r, T)\n"
        "kq = unittest.TextTestRunner(verbosity=2).run(ca)\n"
        "T.CHAN.tat()\n"
        "raise SystemExit(0 if kq.wasSuccessful() else 1)\n"
        % (GOC, THU, dot_bien, ten_ca))
    tam_con = tempfile.mkdtemp(prefix="vh-g22bimat-con-")
    try:
        return subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                              timeout=300, cwd=DU_AN,
                              env=dict(os.environ, VIP_HUB_DATA=tam_con,
                                       VIP_G22_TAM_GOC=tam_con))
    finally:
        don_sach_thu_muc(tam_con)


# =================================================================================================
# A. BA ĐƯỜNG RA KHỎI TIẾN TRÌNH — ĐO ĐƯỢC BẰNG CHỨNG CỨ TRÊN ĐĨA
# =================================================================================================
class A_BaDuongRaKhoiTienTrinh(CaGoc):
    """(i) thân 502 · (ii) tệp log trên đĩa · (iii) trường `duong` của JSONL.

    Ba đường này KHÁC NHAU về bản chất bằng chứng: (i) là byte đi trên DÂY tới người dùng, (ii) và
    (iii) là byte nằm lại trên ĐĨA. Một phép đo chỉ nhìn ngoại lệ trong bộ nhớ sẽ bỏ sót cả (ii)
    lẫn (iii) — đúng chỗ G16–G20 chưa từng đo.
    """
    NHOM = "A"

    # ---- (i) THÂN HTTP 502 ---------------------------------------------------------------------
    _nen = None

    def _dung_nen_http(self):
        """Máy chủ THẬT trong tiến trình + CSDL tạm. Ba hàm tuyến webhook được TIÊM để tới được chỗ
        dựng thân 502 mà không cần đăng nhập; phần ĐANG ĐO (ánh xạ ngoại lệ → thân phản hồi) là mã
        SẢN XUẤT, không bị tiêm."""
        cls = type(self)
        if cls._nen is not None:
            return cls._nen
        import csdl
        import quyen
        import server
        csdl.mo()
        quyen.seed()
        sv = HTTPServer(("127.0.0.1", 0), server.BoXuLy)      # một luồng, luồng phục vụ JOIN được
        luong = threading.Thread(target=sv.serve_forever, kwargs={"poll_interval": 0.02},
                                 daemon=True)
        self.addCleanup(sv.server_close)
        self.addCleanup(luong.join, 10)
        self.addCleanup(sv.shutdown)
        self.addCleanup(csdl.dong)
        luong.start()
        cls._nen = {"cong": sv.server_address[1], "sv": sv}
        return cls._nen

    def _kq_tu_msg_hang(self, bi_mat):
        """Kết quả THẬT của adapter khi hãng echo bí mật trong `msg` của một lượt HTTP **200**."""
        stub = self.mo(lambda bx, gt=bi_mat: (
            200, json.dumps({"code": "145005005", "msg": "khoa cua ban: " + gt,
                             "data": None}).encode("utf-8"), {}))
        ad = aj.AdapterJT(dict(CRED_GIA_DINH), "mock")
        with aj.DungDiemCuoiTam(stub.goc):
            yc = ad.yeu_cau_tao_don(dict(DON_MAU))
            yc["url"] = aj.url_cua("createOrder", "sandbox")
            kq = ad._goi_that(http_jt, "createOrder", yc)
        than_stub = self.cho_tra_loi(stub).decode("utf-8", "replace")
        # ĐỐI CHỨNG DƯƠNG BẮT BUỘC: bí mật THẬT SỰ có trong thân phản hồi của hãng.
        self.assertIn(bi_mat, than_stub, "hãng chưa echo bí mật ⇒ ca vô nghĩa")
        doi_chung(self.NHOM)
        return kq

    def test_a1_than_502_tren_day_KHONG_chua_bi_mat(self):
        """ĐO TRỌN ĐƯỜNG: máy chủ THẬT (socket thật) → `LoiNghiepVu` → thân 502 người dùng nhận."""
        import urllib.error
        import urllib.request
        import don_hang
        import webhook
        nen = self._dung_nen_http()
        cu = (webhook.tim_account_theo_webhook_ma, webhook.kiem_chu_ky, webhook.nhan_su_kien)
        self.addCleanup(lambda: setattr(webhook, "tim_account_theo_webhook_ma", cu[0]))
        self.addCleanup(lambda: setattr(webhook, "kiem_chu_ky", cu[1]))
        self.addCleanup(lambda: setattr(webhook, "nhan_su_kien", cu[2]))
        webhook.tim_account_theo_webhook_ma = lambda ma: {"id": 1, "hang": "jt", "tenant_id": 1}
        webhook.kiem_chu_ky = lambda *a, **k: True
        for nhan, bi_mat in (("A1 thân 502 — NGẮN", BM_NGAN), ("A1 thân 502 — DÀI", BM_DAI)):
            with self.subTest(nhan=nhan):
                kq = self._kq_tu_msg_hang(bi_mat)

                def _no(*a, **k):
                    raise don_hang.LoiNghiepVu("hãng từ chối: " + str(kq.loi), 502)
                webhook.nhan_su_kien = _no
                yc = urllib.request.Request(
                    "http://127.0.0.1:%d/api/v2/webhook/nhan/ma-gia" % nen["cong"],
                    data=b"{}", method="POST")
                yc.add_header("Content-Type", "application/json")
                yc.add_header("X-Requested-With", "VIPHub")
                try:
                    with urllib.request.urlopen(yc, timeout=15) as ph:
                        ma, than = ph.status, ph.read().decode("utf-8", "replace")
                except urllib.error.HTTPError as e:
                    ma, than = e.code, e.read().decode("utf-8", "replace")
                do()
                # ĐỐI CHỨNG DƯƠNG: đúng lượt 502 ấy PHẢI mang thông điệp của hãng (đã dịch) và mã
                # lỗi gốc — không có nó thì "thân không chứa bí mật" đúng vô nghĩa (có thể là 404).
                self.assertEqual(ma, 502, "không phải lượt 502 — ca đo nhầm chỗ: %r" % than[:200])
                self.assertIn("hãng từ chối", than, "thân 502 không mang thông điệp của hãng")
                self.assertIn("145005005", than, "thân 502 mất mã lỗi gốc của hãng")
                ro = [d for d in sorted(cac_dang(bi_mat)) if d and d in than]
                bang_ghi(nhan, "thân HTTP 502 (socket thật)", self._dang_mo_ta(bi_mat),
                         "sạch" if not ro else "RÒ: %s" % ro)
                self.assertEqual(ro, [], "RÒ RỈ %r trong THÂN 502 trên dây: %r" % (bi_mat, than[:300]))

    # ---- (ii) + (iii) TỆP LOG TRÊN ĐĨA: access log VÀ trường `duong` của JSONL -------------------
    def _mot_luot_log(self, duong, pt="GET", body=None, dot_bien=""):
        """Dựng máy chủ THẬT trên nền tạm, gọi MỘT lượt, rồi ĐỌC LẠI tệp log từ đĩa."""
        tam = dung_nen_tam()
        self.addCleanup(shutil.rmtree, tam, True)
        cong = cong_roi()
        sv, log = dung_may_chu(tam, cong, dot_bien)
        self.assertIsNotNone(sv, "máy chủ thật không mở cổng %d (log: %s)"
                             % (cong, open(log).read()[-300:] if os.path.exists(log) else ""))
        try:
            ma, _ = goi_hub(cong, duong, pt, body)
            time.sleep(0.4)
            with open(log, encoding="utf-8", errors="replace") as f:
                tho = f.read()
        finally:
            sv.terminate()
            try:
                sv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                sv.kill()
        # ĐỐI CHỨNG DƯƠNG: máy chủ THẬT SỰ đã ghi log — "sạch" vì log RỖNG là "sạch" vô nghĩa.
        self.assertIn("[hub]", tho, "log máy chủ rỗng ⇒ ca vô nghĩa")
        doi_chung(self.NHOM)
        return tam, log, tho, ma

    def test_a2_D4_bi_mat_trong_QUERY_khong_lot_vao_tep_nao(self):
        """(ii) QUERY của URL không được xuống tệp log — đo bằng cách ĐỌC LẠI TỆP TRÊN ĐĨA."""
        duong = DUONG_HUB + "?token=" + BM_QUERY
        tam, log, tho, ma = self._mot_luot_log(duong)
        do()
        thay = quet_thay_bi_mat(tam, BM_QUERY)
        bang_ghi("A2 D4 query URL", "MỌI tệp trên đĩa (nền tạm)", self._dang_mo_ta(BM_QUERY),
                 "sạch" if not thay else "RÒ: %s" % thay)
        self.assertEqual(thay, [], "bí mật trong QUERY xuống tệp trên đĩa: %s" % thay)
        # ĐỐI CHỨNG ĐƯỜNG: dòng access log VẪN Ở ĐÓ, chỉ mất phần query.
        self.assertIn("da-cat-query", tho, "dòng access log mất hẳn ⇒ ca vô nghĩa")
        self.assertIn(DUONG_HUB, tho, "đường dẫn thật bị che khỏi log ⇒ chẩn đoán mất thông tin")
        # (iii) trường `duong` của JSONL — đường ghi KHÁC, phải đọc riêng.
        ban = [b for b in doc_jsonl(log) if b.get("duong", "").startswith("/api/")]
        self.assertTrue(ban, "không có dòng JSONL `yeu_cau` nào ⇒ phép đo (iii) rỗng, không phải ĐẠT")
        for b in ban:
            with self.subTest(duong=b.get("duong")):
                self.assertNotIn(BM_QUERY, b.get("duong", ""), "trường `duong` của JSONL mang QUERY")
        self.assertIn(DUONG_HUB, [b.get("duong") for b in ban],
                      "trường `duong` của JSONL mất đường dẫn thật")

    def test_a3_D5_bi_mat_trong_DUONG_DAN_khong_lot_vao_tep_nao(self):
        """(ii)+(iii) bí mật trong ĐƯỜNG DẪN không xuống đĩa, và trường `duong` của JSONL đã che."""
        duong = "/api/" + BM_DUONG + "/x"
        tam, log, tho, ma = self._mot_luot_log(duong)
        do()
        thay = quet_thay_bi_mat(tam, BM_DUONG)
        bang_ghi("A3 D5 đường dẫn URL", "MỌI tệp trên đĩa (nền tạm)", self._dang_mo_ta(BM_DUONG),
                 "sạch" if not thay else "RÒ: %s" % thay)
        self.assertEqual(thay, [], "bí mật trong ĐƯỜNG DẪN xuống tệp trên đĩa: %s" % thay)
        # ĐỐI CHỨNG ĐƯỜNG: dòng log VẪN nói được đường dẫn đã gọi, chỉ đoạn bí mật bị che.
        self.assertIn("/api/[DA-CHE]/x", tho, "dòng log không còn hình dạng đường dẫn đã gọi")
        # (iii) RIÊNG trường `duong` của JSONL — đây là yêu cầu của đề bài, không gộp với access log.
        ban = [b for b in doc_jsonl(log) if "/api/" in b.get("duong", "")]
        self.assertTrue(ban, "không có dòng JSONL `yeu_cau` nào ⇒ phép đo (iii) rỗng, không phải ĐẠT")
        for b in ban:
            with self.subTest(duong=b.get("duong")):
                self.assertNotIn(BM_DUONG, b.get("duong", ""),
                                 "trường `duong` của JSONL mang bí mật trong đường dẫn")
                self.assertIn("[DA-CHE]", b.get("duong", ""),
                              "trường `duong` của JSONL không che đoạn nguy hiểm")
                self.assertIn("/api/", b.get("duong", ""), "mất hình dạng đường dẫn đã gọi")
        self.assertIn("/api/[DA-CHE]/x", [b.get("duong") for b in ban],
                      "trường `duong` của JSONL không phải dạng đã che")

    def test_a4_ba_duong_la_BA_phep_do_khac_nhau(self):
        """Ba đường phải là BA phép đo, không phải một phép đo đếm ba lần.

        Khẳng định bằng MÃ: ba lớp ca đo ba thứ khác nhau — thân trên dây (A1) · tệp trên đĩa (A2,
        A3) · trường `duong` của JSONL (A2, A3). Nếu ai đó gộp chúng lại thành một, ca này đỏ.
        """
        do()
        self.assertTrue(hasattr(self, "test_a1_than_502_tren_day_KHONG_chua_bi_mat"))
        self.assertTrue(hasattr(self, "test_a2_D4_bi_mat_trong_QUERY_khong_lot_vao_tep_nao"))
        self.assertTrue(hasattr(self, "test_a3_D5_bi_mat_trong_DUONG_DAN_khong_lot_vao_tep_nao"))
        doi_chung(self.NHOM)
        bang_ghi("A4 ba đường = ba phép đo", "thân dây · tệp đĩa · JSONL", "—", "3 phép đo riêng")


# =================================================================================================
# B. CHỨNG MINH CA KIỂM **ĐỎ ĐƯỢC** — tiêm lại đúng hành vi TRƯỚC bản vá
# =================================================================================================
class B_TiemLaiLoi(CaGoc):
    """Không có nhóm này thì mọi dòng "sạch" ở nhóm `A` có thể đang đo một thứ không bao giờ ĐỎ."""
    NHOM = "B"

    # Hành vi TRƯỚC bản vá, chép nguyên dạng:
    #   · `loi_hang.tu_ma_hang` chép thẳng `msg hãng` vào `thong_diep` ⇒ bí mật vào thân 502.
    DOT_BIEN_D3 = ("import loi_hang\n"
                   "loi_hang._mo_ta_msg_hang = (lambda msg: "
                   "(' | msg hãng: %s' % msg) if msg else '')\n")
    #   · `server.log_message` ghi nguyên `fmt % args` (kèm QUERY) và KHÔNG che đường dẫn.
    DOT_BIEN_D4_D5 = (
        "import sys as _sys\n"
        "server.BoXuLy.log_message = (lambda self, fmt, *a: "
        "_sys.stderr.write('[hub] %s\\n' % (fmt % a)))\n"
        "server._doan_duong_dan_trong_log = (lambda d: d)\n")
    #   · G22: gỡ luật ECHO THEO TÊN ⇒ credential NGẮN của hãng khác J&T quay lại rò.
    DOT_BIEN_G5 = ("http_jt._gia_tri_echo_theo_ten = "
                   "(lambda than, headers_tra_loi, ten_ta_gui: set())\n")

    def _kiem(self, ten_ca, dot_bien):
        p = chay_ca_trong_con(ten_ca, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_b1_tiem_lai_loi_D3_thi_ca_A1_PHAI_DO(self):
        for ten_ca in ("A_BaDuongRaKhoiTienTrinh.test_a1_than_502_tren_day_KHONG_chua_bi_mat",):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, self.DOT_BIEN_D3)
                self.assertNotEqual(p.returncode, 0,
                                    "tiêm lại lỗi D3 mà %s vẫn XANH — ca không có RĂNG:\n%s"
                                    % (ten_ca, out[-1500:]))
        doi_chung(self.NHOM)

    def test_b2_tiem_lai_loi_D4_D5_thi_ca_A2_A3_PHAI_DO(self):
        """Chạy TRÊN BẢN CHƯA VÁ (máy chủ dựng lại với `log_message` cũ) — phép đo phải thấy rò."""
        for nhan, duong, bi_mat in (
                ("A2", DUONG_HUB + "?token=" + BM_QUERY, BM_QUERY),
                ("A3", "/api/" + BM_DUONG + "/x", BM_DUONG)):
            with self.subTest(ca=nhan):
                tam = dung_nen_tam()
                self.addCleanup(shutil.rmtree, tam, True)
                cong = cong_roi()
                sv, log = dung_may_chu(tam, cong, self.DOT_BIEN_D4_D5)
                self.assertIsNotNone(sv, "máy chủ (bản chưa vá) không mở cổng %d" % cong)
                try:
                    goi_hub(cong, duong)
                    time.sleep(0.4)
                finally:
                    sv.terminate()
                    try:
                        sv.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        sv.kill()
                thay = quet_thay_bi_mat(tam, bi_mat)
                bang_ghi("B2 tiêm lại lỗi cũ — %s" % nhan, "tệp trên đĩa",
                         self._dang_mo_ta(bi_mat), "BỘ DÒ THẤY RÒ" if thay else "KHÔNG THẤY")
                self.assertTrue(thay, "tiêm lại lỗi log cũ mà bộ dò KHÔNG thấy %r rò xuống đĩa — "
                                      "ca %s không có RĂNG" % (bi_mat, nhan))
        doi_chung(self.NHOM)

    def test_b3_tiem_lai_loi_G5_thi_ca_C_PHAI_DO(self):
        """Gỡ luật ECHO THEO TÊN ⇒ hai tổ hợp (tên hãng giả + NGẮN) phải rò LẠI. Đó là ĐỐI CHỨNG
        cho toàn bộ nhóm `C`: nếu gỡ bản vá mà `C` vẫn xanh thì `C` không đo bản vá."""
        for ten_ca in ("C_CongG5.test_c1_nam_to_hop_tren_stub_ECHO",
                       "C_CongG5.test_c2_doi_chung_khong_mu"):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, self.DOT_BIEN_G5)
                self.assertNotEqual(p.returncode, 0,
                                    "gỡ luật ECHO THEO TÊN mà %s vẫn XANH — ca không có RĂNG:\n%s"
                                    % (ten_ca, out[-1500:]))
        doi_chung(self.NHOM)

    def test_b4_doi_chung_DUONG_khong_tiem_thi_PHAI_XANH(self):
        """Thiếu ca này thì một bộ chạy con "luôn báo hỏng" cũng làm các ca trên xanh vô nghĩa."""
        for ten_ca in ("A_BaDuongRaKhoiTienTrinh.test_a1_than_502_tren_day_KHONG_chua_bi_mat",
                       "A_BaDuongRaKhoiTienTrinh.test_a2_D4_bi_mat_trong_QUERY_khong_lot_vao_tep_nao",
                       "C_CongG5.test_c1_nam_to_hop_tren_stub_ECHO"):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, "")
                self.assertEqual(p.returncode, 0, "ca hỏng cả khi KHÔNG tiêm:\n%s" % out[-1500:])
                self.assertIn("OK", out)
        doi_chung(self.NHOM)


# =================================================================================================
# C. CỔNG `G5` — CREDENTIAL NGẮN CỦA **BẤT KỲ HÃNG NÀO**
# =================================================================================================
class C_CongG5(CaGoc):
    """Cổng nghiệm thu `G5` của AG-01: **0/5 tổ hợp rò**, VÀ phép đo KHÔNG ĐƯỢC MÙ.

    "Không mù" là hai vế bắt buộc: (a) `privateKey` + NGẮN vẫn phải bị che (tầng theo TÊN còn sống);
    (b) cả hai tổ hợp DÀI vẫn phải bị che (tầng theo ĐỘ DÀI còn sống). Một bản vá che SẠCH mọi thứ
    sẽ cho 0/5 mà vẫn là một bản vá HỎNG — nó phá thông điệp chẩn đoán.
    """
    NHOM = "C"

    def _co_ro(self, ten, gia_tri):
        """→ `(kết quả, kênh_rò)`. Stub `DOI_DAU` ECHO LẠI header + thân rồi trả HTTP 401.

        Đọc CẢ BA kênh mà AG-01 đo (`than_da_che`, `headers_da_che`, `str(e)`), không chỉ một —
        một bàn đo chỉ nhìn `str(e)` sẽ bỏ sót hai kênh kia và báo "0 rò" sai.
        """
        stub = StubHangGia(StubHangGia.DOI_DAU)
        self.addCleanup(stub.dung)
        try:
            http_jt.gui_form(stub.url, {"Content-Type": http_jt.CONTENT_TYPE_FORM, ten: gia_tri},
                             {"truong": gia_tri}, timeout=5.0)
            return "KHONG-NEM", ()
        except transport.LoiVinhVien as e:
            kenh = []
            if gia_tri in e.than_da_che.decode("utf-8", "replace"):
                kenh.append("than_da_che")
            if gia_tri in str(e.headers_da_che):
                kenh.append("headers_da_che")
            if gia_tri in str(e):
                kenh.append("str(e)")
            return ("RO" if kenh else "sach"), tuple(kenh)

    def test_c1_nam_to_hop_tren_stub_ECHO(self):
        """NĂM tổ hợp của `G5` — chép đúng năm tổ hợp AG-01 đo, trên stub ECHO cổng OS cấp."""
        ro = 0
        for ten, gt, nhan in TO_HOP_G5:
            with self.subTest(to_hop=nhan):
                kq, kenh = self._co_ro(ten, gt)
                do()
                bang_ghi("C1 %s" % nhan, "than_da_che · headers_da_che · str(e)",
                         self._dang_mo_ta(gt), "%s %s" % (kq, list(kenh) if kenh else ""))
                self.assertNotEqual(kq, "KHONG-NEM",
                                    "%s: lớp HTTP phải NÉM với HTTP 401, không được trả về" % nhan)
                if kq == "RO":
                    ro += 1
                self.assertNotEqual(kq, "RO",
                                    "RÒ credential %r dưới tên %r qua %s — cổng G5 còn ĐỎ"
                                    % (gt, ten, list(kenh)))
        doi_chung(self.NHOM)
        self.assertEqual(ro, 0, "còn %d/5 tổ hợp rò" % ro)

    def test_c2_doi_chung_khong_mu(self):
        """HAI VẾ BẮT BUỘC: tầng theo TÊN và tầng theo ĐỘ DÀI đều phải còn sống.

        Không có ca này thì `c1` xanh được bằng cách che sạch mọi thứ — và một bản vá che sạch là
        bản vá HỎNG theo chiều ngược lại (người trực không đọc được gì).
        """
        do()
        # (a) tầng theo TÊN: credential NGẮN của J&T vẫn phải bị che.
        self.assertIn(KHOA_GIA_NGAN,
                      http_jt._gia_tri_can_che({"privateKey": KHOA_GIA_NGAN}, b"x=1"),
                      "tầng che theo TÊN đã chết ⇒ phép đo G5 mù")
        # (b) tầng theo ĐỘ DÀI: giá trị dài dưới tên lạ vẫn phải bị che.
        self.assertIn(KHOA_GIA_DAI,
                      http_jt._gia_tri_can_che({"x-mau-khoa-bi-mat": KHOA_GIA_DAI}, b"x=1"),
                      "tầng che theo ĐỘ DÀI đã chết ⇒ phép đo G5 mù")
        doi_chung(self.NHOM)
        bang_ghi("C2 đối chứng không mù", "tập che ta gửi đi", "ngắn+dài",
                 "TÊN (privateKey) + ĐỘ DÀI (37) đều còn sống")

    def test_c3_khong_che_bua_du_lieu_cua_hang(self):
        """ĐỐI CHỨNG ĐƯỜNG của luật mới: nó chỉ che thứ TA ĐÃ GỬI, không che dữ liệu của hãng.

        Đây là chỗ luật ECHO THEO TÊN rất dễ bị viết quá tay ("thấy tên lạ là che"): bản cài đúng
        đòi khớp CẢ TÊN LẪN GIÁ TRỊ. Ca này đo vế thứ hai.
        """
        do()
        than = json.dumps({"code": "145003030", "msg": "hãng báo lỗi",
                           "data": {"billCode": KHONG_BI_MAT, "ma_van_don": "JT123"}},
                          ensure_ascii=False).encode()
        ten_ta_gui = http_jt._ten_ta_gui({"X-Ma-Don": "VH12"}, b"x=1")
        ra = http_jt._gia_tri_echo_theo_ten(than, [("X-Trace", "abc")], ten_ta_gui)
        self.assertEqual(ra, set(), "luật echo che dữ liệu của hãng: %r" % ra)
        # Và phép che với tập RỖNG phải là hàm ĐỒNG NHẤT — che bừa là phá dữ liệu nghiệp vụ.
        self.assertEqual(http_jt.che_bi_mat(b"than nguyen ven", set()), b"than nguyen ven")
        doi_chung(self.NHOM)
        bang_ghi("C3 đối chứng đường (dữ liệu hãng)", "tập che từ phản hồi", "mã vận đơn",
                 "nguyên vẹn — không che bừa")

    def test_c4_luat_echo_bat_duoc_o_CA_BA_vi_tri(self):
        """Luật mới phải bắt ở CẢ BA vị trí echo: header phản hồi · JSON · văn bản `ten=giá_trị`.

        Một bản cài chỉ xử lý header sẽ đóng được stub này nhưng để hở hai vị trí kia — và lần đo
        sau sẽ thấy đúng khe ấy. Nên ca này đo từng vị trí một, bằng chính hàm nhận diện.
        """
        do()
        mat = "Zx9Qm"                                    # 5 ký tự, tên lạ, không thuộc danh sách nào
        ten_ta_gui = http_jt._ten_ta_gui({"x-mau-khoa-bi-mat": mat}, ("truong=" + mat).encode())
        self.assertIn(mat, http_jt._gia_tri_echo_theo_ten(b"", [("X-Mau-Khoa-Bi-Mat", mat)],
                                                          ten_ta_gui),
                      "vị trí HEADER phản hồi: không bắt được")
        self.assertIn(mat, http_jt._gia_tri_echo_theo_ten(
            json.dumps({"x-mau-khoa-bi-mat": mat}).encode(), [], ten_ta_gui),
            "vị trí JSON trong thân: không bắt được")
        self.assertIn(mat, http_jt._gia_tri_echo_theo_ten(
            ("x-mau-khoa-bi-mat: " + mat).encode(), [], ten_ta_gui),
            "vị trí văn bản `ten=giá_trị`: không bắt được")
        # Và tên ta gửi ở THÂN form cũng vào sổ (không chỉ header).
        self.assertIn("truong", ten_ta_gui, "sổ tên ta gửi bỏ sót tên trường trong THÂN form")
        doi_chung(self.NHOM)
        bang_ghi("C4 luật echo — ba vị trí", "header · JSON · văn bản", "ngắn(5)", "che cả ba")

    def test_c5_bien_gioi_CON_LAI_echo_TRAN_khong_kem_ten(self):
        """BIÊN GIỚI ĐÃ BIẾT — ghim ra thay vì để nó lặng lẽ thành "đạt".

        Một giá trị NGẮN bị hãng echo lại **KHÔNG kèm tên** (nằm trần trong câu chữ của hãng) thì
        KHÔNG có gì để nhận diện: che mọi chuỗi ngắn là che luôn `2`, `200`, `-` và phá sạch thông
        điệp chẩn đoán. Giá trị DÀI ở dạng trần thì **tầng theo ĐỘ DÀI** (`_gia_tri_can_che`) đã
        bắt từ trước — ca này khẳng định ĐÚNG CẢ HAI VẾ, vì một bản cài chỉ dựa vào luật echo sẽ
        bỏ hở mọi giá trị dài echo trần.
        """
        do()
        mat = "Zx9Qm"                                    # cùng giá trị NGẮN như ca c4
        ten_ta_gui = http_jt._ten_ta_gui({"x-mau-khoa-bi-mat": mat}, ("truong=" + mat).encode())
        ra_tran = http_jt._gia_tri_echo_theo_ten(
            ("loi: khoa " + mat + " khong hop le").encode(), [], ten_ta_gui)
        self.assertEqual(ra_tran, set(),
                         "biên giới đã đổi: echo TRẦN nay bắt được — cập nhật tài liệu G22 §5")
        # ĐỐI CHỨNG DƯƠNG: CÙNG giá trị ấy, chỉ cần thêm TÊN là bắt được ngay.
        self.assertIn(mat, http_jt._gia_tri_echo_theo_ten(
            ("x-mau-khoa-bi-mat=" + mat).encode(), [], ten_ta_gui),
            "cùng giá trị mà có tên cũng không bắt được ⇒ luật echo hỏng, không phải biên giới")
        # ĐỐI CHỨNG DƯƠNG thứ hai: giá trị DÀI echo trần VẪN bị che — nhưng bởi **tầng theo ĐỘ DÀI**
        # (`_gia_tri_can_che`), KHÔNG phải bởi luật echo. Đây là chỗ dễ viết sai: luật echo KHÔNG
        # phải đường nhận diện duy nhất, và một bản cài chỉ dựa vào nó sẽ bỏ hở mọi giá trị dài.
        dai = "Tran-Dai-9f3ac21b7d4e"
        can_che_dai = http_jt._gia_tri_can_che({"X-Ma-Don": dai}, b"x=1")
        self.assertIn(dai, can_che_dai, "tầng theo ĐỘ DÀI không nhận ra giá trị dài")
        self.assertNotIn(dai.encode(),
                         http_jt.che_bi_mat(("loi: " + dai).encode(), can_che_dai),
                         "giá trị DÀI echo trần không bị che ⇒ tầng theo ĐỘ DÀI đã chết")
        doi_chung(self.NHOM)
        bang_ghi("C5 BIÊN GIỚI echo trần (ngắn)", "thân phản hồi, không kèm tên", "ngắn(5)",
                 "CHƯA ĐO ĐƯỢC (biên giới đã biết — docs/G22_BIMAT.md §5)")

    def test_c6_danh_sach_ten_credential_KHONG_doi(self):
        """Bản vá G22 KHÔNG được đổi `TRUONG_CREDENTIAL` — hai bộ khác đang ghim bảng ấy.

        `thu_g20_dahang.c2b` khẳng định bảng có ĐÚNG 4 tên của J&T và tên của hãng giả KHÔNG nằm
        trong đó; `thu_http_jt` khẳng định nó khớp `adapter_jt.TRUONG_CREDENTIAL`. Nếu bản vá "mở
        rộng bảng cho chắc" thì hai bộ kia đỏ — và chúng đỏ ĐÚNG, vì mở rộng bảng là cách vá sai
        (nó chỉ đúng với những tên đã biết).
        """
        do()
        self.assertEqual(len(http_jt.TRUONG_CREDENTIAL), 4)
        self.assertEqual(tuple(http_jt.TRUONG_CREDENTIAL),
                         ("apiaccount", "privatekey", "customercode", "password"))
        for ten in ("x-mau-khoa-bi-mat", "maTaiKhoanGia"):
            with self.subTest(ten=ten):
                self.assertNotIn(ten.lower(), http_jt.TRUONG_CREDENTIAL)
        self.assertEqual(http_jt.DAI_TOI_THIEU_DE_CHE, 8)
        doi_chung(self.NHOM)
        bang_ghi("C6 bảng tên credential", "http_jt.TRUONG_CREDENTIAL", "—", "KHÔNG đổi (4 tên J&T)")


# =================================================================================================
# D. RÀ LẠI TOÀN BỘ ASSERTION VỀ CHE BÍ MẬT — BẰNG MÁY, TRÊN `app/thu/thu_*.py`
# =================================================================================================
KY_HIEU_CHE = (
    "than_da_che", "headers_da_che", "mo_ta_yeu_cau", "che_bi_mat", "_gia_tri_can_che",
    "_gia_tri_ta_gui", "_gia_tri_bi_mat_tu_phan_hoi", "_gia_tri_bi_mat_trong_json",
    "_gia_tri_bi_mat_trong_vb", "TRUONG_CREDENTIAL", "DAI_TOI_THIEU_DE_CHE", "[DA-CHE]",
    "doan_duong_dan_da_che", "_duong_dan_da_che", "_che_chuoi", "_gia_tri_tu_url",
    "_gia_tri_tu_duong_dan", "_dang_che", "DA-CHE", "_gia_tri_echo_theo_ten", "_ten_ta_gui",
)


def quet_assertion_che():
    """Quét AST mọi `app/thu/thu_*.py`, trả `(theo_tep, chi_tiet)`.

    TIÊU CHÍ ĐẾM, nói rõ để người sau đo lại được: một assertion được tính là "về che bí mật" khi
    **mã nguồn của chính câu lệnh ấy** chạm một trong các KÝ HIỆU của cơ chế che (`KY_HIEU_CHE`).
    Đếm theo TÊN HÀM không dùng được: nó nuốt cả những bộ không liên quan (`thu_bao_mat` đo khoá,
    `thu_ai_job` đo quét bí mật trong prompt) và cho ra con số vô nghĩa (828 ở lượt thử đầu).
    """
    theo_tep, chi_tiet = {}, []
    for ten_tep in sorted(os.listdir(THU)):
        if not (ten_tep.startswith("thu_") and ten_tep.endswith(".py")):
            continue
        duong = os.path.join(THU, ten_tep)
        try:
            with open(duong, encoding="utf-8") as f:
                nguon = f.read()
            cay = ast.parse(nguon)
        except (OSError, SyntaxError):
            continue
        for nut in ast.walk(cay):
            if not isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for con in ast.walk(nut):
                if not (isinstance(con, ast.Call) and isinstance(con.func, ast.Attribute)
                        and con.func.attr.startswith("assert")):
                    continue
                doan = ast.get_source_segment(nguon, con) or ""
                if any(k in doan for k in KY_HIEU_CHE):
                    theo_tep[ten_tep] = theo_tep.get(ten_tep, 0) + 1
                    chi_tiet.append((ten_tep, nut.name, con.func.attr,
                                     " ".join(doan.split())[:120]))
    return theo_tep, chi_tiet


class D_RaSoatAssertion(CaGoc):
    """Owner giao riêng mục này: *có assertion nào đang GHIM HÀNH VI CŨ hoặc QUÁ LỎNG không?*

    SỔ RÀ SOÁT — trạng thái CUỐI lượt G22 (số đo ở `test_d1`, chi tiết ở `docs/G22_BIMAT.md` §4):

    | # | Chỗ | Vấn đề | Xử lý |
    |---|---|---|---|
    | 1 | `thu_g20_dahang.test_c2a` — `assertTrue(ket_qua["gia_ngan"])` | **GHIM CHÍNH HÀNH VI RÒ** (N-G21-03) | **ĐÃ VIẾT LẠI** thành `assertFalse` + ghi rõ ca cũ ghim gì (vùng ghi mở rộng — xem `docs/G22_BIMAT.md` §6.3) |
    | 2 | `thu_g21_bimat.test_c1` — `assertIn("don-42", str(e))` | ghim *"giá trị ta gửi, hãng echo lại, đi qua NGUYÊN VẸN"* — hành vi cũ | **ĐÃ VIẾT LẠI** theo bất biến đúng, MẠNH HƠN: TÊN trường/endpoint/HTTP/số byte vẫn nguyên |
    | 3 | `thu_g21_bimat.test_b3` — `bang_ghi(... "CHƯA CHE ĐƯỢC")` | kết luận đã LỖI THỜI: đường echo nay bắt được | **ĐÃ SIẾT**: thêm khẳng định vế mới, sửa kết luận bảng |
    | 4 | `thu_g18_bi_mat` — đột biến `l1` cho ca `k2e` | **PHÉP ĐO ĐÃ CHẾT**: nó gỡ một luật, nhưng luật thứ hai (echo) nay bắt hộ ⇒ "đột biến không bị bắt" | **ĐÃ SỬA**: gỡ CẢ HAI luật (đo được: gỡ 1 luật ⇒ exit 0 · gỡ 2 luật ⇒ exit 1) |
    | 5 | `thu_http_jt.j2/j5` · `thu_g18_bi_mat.k4` · `thu_g20_dahang.c2b` · `thu_qa_g18_tich_hop.a5` | **KHÔNG lỏng**: chúng đo TẬP GIÁ TRỊ TA GỬI ĐI và bảng tên — bản vá G22 không đụng hai thứ ấy | **GIỮ NGUYÊN** (đo lại: cả bốn bộ xanh) |
    | 6 | 67 câu còn lại chạm ký hiệu che trong 9 tệp | đo tập giá trị / nhãn `[DA-CHE]` / thân 2xx / đối chứng đường | **GIỮ NGUYÊN** — không câu nào khẳng định một giá trị ĐÃ RÒ là đúng |
    """
    NHOM = "D"

    def test_d1_so_do_ra_soat_assertion(self):
        theo_tep, chi_tiet = quet_assertion_che()
        tong = sum(theo_tep.values())
        print("\n  RÀ SOÁT ASSERTION CHE BÍ MẬT — %d câu · %d tệp" % (tong, len(theo_tep)))
        for t, n in sorted(theo_tep.items(), key=lambda x: (-x[1], x[0])):
            print("    %-32s %3d" % (t, n))
        print("    (tiêu chí: mã nguồn câu lệnh chạm một ký hiệu của cơ chế che)")
        do()
        bang_ghi("D1 rà soát assertion", "app/thu/thu_*.py (AST)", "%d câu" % tong,
                 "đã phân loại — xem docs/G22_BIMAT.md §4")
        # SÀN, không ghim cứng: làn khác thêm ca thì con số TĂNG, và tăng là chuyện tốt. Ghim cứng
        # một con số ở đây sẽ biến mọi bộ thử của làn khác thành một ca đỏ giả.
        self.assertGreaterEqual(tong, 60, "số câu rà được TỤT xuống %d — bộ quét hỏng?" % tong)
        for tep in ("thu_http_jt.py", "thu_g18_bi_mat.py", "thu_g21_bimat.py", "thu_g20_dahang.py"):
            with self.subTest(tep=tep):
                self.assertIn(tep, theo_tep)
        doi_chung(self.NHOM)

    @staticmethod
    def _ca(ten_tep, ten_ca):
        """→ `(docstring, [(tên_assert, mã_nguồn câu lệnh)])` của MỘT ca thử.

        Đọc bằng AST chứ KHÔNG bằng `in` trên cả chuỗi: docstring của ca ĐƯỢC PHÉP (và phải) nhắc
        lại câu lệnh cũ — nó phải nói rõ ca từng ghim gì. Một phép kiểm bằng `in` sẽ bắt nhầm chính
        lời giải thích ấy và biến việc ghi rõ lịch sử thành một ca đỏ.
        """
        with open(os.path.join(THU, ten_tep), encoding="utf-8") as f:
            nguon = f.read()
        for nut in ast.walk(ast.parse(nguon)):
            if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)) and nut.name == ten_ca:
                ra = []
                for con in ast.walk(nut):
                    if (isinstance(con, ast.Call) and isinstance(con.func, ast.Attribute)
                            and con.func.attr.startswith("assert")):
                        ra.append((con.func.attr, ast.get_source_segment(nguon, con) or ""))
                return ast.get_docstring(nut) or "", ra
        return "", []

    def test_d2_bon_cho_pin_hanh_vi_cu_DA_DUOC_XU_LY(self):
        """BỐN chỗ đã biết phải ở trạng thái ĐÃ XỬ LÝ — ca này canh chúng không quay lại."""
        do()
        # (1) `test_c2a` — KHÔNG còn câu `assertTrue(...gia_ngan...)`; phải là `assertFalse` + nói rõ.
        mo_ta, assert_c2a = self._ca(
            "thu_g20_dahang.py", "test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia")
        self.assertTrue(assert_c2a, "không đọc được `test_c2a` ⇒ ca này vô nghĩa")
        self.assertEqual([d for ten, d in assert_c2a if ten == "assertTrue" and "gia_ngan" in d], [],
                         "`test_c2a` quay lại GHIM hành vi rò (N-G21-03 mở lại)")
        self.assertTrue([d for ten, d in assert_c2a
                         if ten == "assertFalse" and 'ket_qua["gia_ngan"]' in d],
                        "`test_c2a` không còn khẳng định bất biến đúng (credential NGẮN của BẤT KỲ "
                        "hãng nào cũng không được rò)")
        self.assertIn("N-G21-03", mo_ta, "ca viết lại phải NÓI RÕ nó từng ghim gì")
        bang_ghi("D2.1 test_c2a (g20_dahang)", "assertTrue → assertFalse", "ngắn(5)",
                 "ĐÃ VIẾT LẠI theo bất biến đúng")
        # (2) `thu_g21_bimat.C1` — KHÔNG còn khẳng định giá trị echo đi qua nguyên vẹn.
        _, assert_c1 = self._ca(
            "thu_g21_bimat.py", "test_c1_chuoi_khong_phai_bi_mat_di_qua_NGUYEN_VAN")
        # `assertIn(ngan, than, …)` (chuỗi đối chứng ĐI TRÊN DÂY) là ĐỐI CHỨNG DƯƠNG bắt buộc và
        # phải giữ; cái bị cấm là khẳng định **chính giá trị ấy** đi qua **THÔNG ĐIỆP** (`str(e)`)
        # — hành vi cũ. (`assertNotIn(ngan, str(e)` KHÔNG khớp mẫu này: `assertNotIn(` không chứa
        # chuỗi con `assertIn(`.)
        self.assertEqual([d for ten, d in assert_c1
                          if ten == "assertIn" and "assertIn(ngan" in d and "str(e)" in d], [],
                         "ca C1 quay lại khẳng định giá trị echo đi qua NGUYÊN VẸN trong thông điệp")
        self.assertTrue([d for ten, d in assert_c1 if ten == "assertNotIn" and "ngan, str(e)" in d],
                        "ca C1 mất vế khẳng định bất biến G22 (giá trị echo bị che)")
        bang_ghi("D2.2 test_c1 (g21_bimat)", "assertIn → assertNotIn", "ngắn(6)",
                 "ĐÃ VIẾT LẠI — TÊN trường/endpoint/HTTP vẫn nguyên")
        # (3) Đột biến `l1` của `thu_g18_bi_mat` phải gỡ CẢ HAI tầng (nếu không, phép đo đã chết).
        with open(os.path.join(THU, "thu_g18_bi_mat.py"), encoding="utf-8") as f:
            nguon18 = f.read()
        self.assertIn("http_jt._gia_tri_tu_url = lambda u: set()", nguon18)
        self.assertIn("http_jt._gia_tri_echo_theo_ten = lambda than, h, t: set()", nguon18,
                      "đột biến `l1` cho ca `k2e` lại chỉ gỡ MỘT tầng ⇒ phép đo đã chết trở lại")
        bang_ghi("D2.3 đột biến l1 (g18_bi_mat)", "gỡ CẢ HAI tầng", "query",
                 "ĐÃ SỬA — đo được: 1 tầng ⇒ exit 0 · 2 tầng ⇒ exit 1")
        # (4) Bảng tên credential KHÔNG được mở rộng để "vá cho xanh" (`test_c2b` canh việc đó).
        self.assertEqual(len(http_jt.TRUONG_CREDENTIAL), 4)
        bang_ghi("D2.4 bảng TRUONG_CREDENTIAL", "http_jt", "4 tên J&T",
                 "GIỮ NGUYÊN — không nới bảng để vá")
        doi_chung(self.NHOM)

    def test_d3_bo_quet_khong_dem_theo_TEN_HAM(self):
        """ĐỐI CHỨNG ÂM của chính bộ quét: đếm theo TÊN HÀM cho ra một con số VÔ NGHĨA.

        Lượt thử đầu của tệp này đếm theo tên hàm và ra **828** câu — nó nuốt cả `thu_bao_mat.py`
        (đo khoá/SecretProvider) và `thu_ai_job.py` (quét bí mật trong prompt), tức những bộ KHÔNG
        đo cơ chế che của lớp HTTP. Ca này ghim bài học ấy bằng số: tiêu chí theo KÝ HIỆU cho ra ít
        hơn HẲN tiêu chí theo TÊN.
        """
        do()
        theo_ky_hieu, _ = quet_assertion_che()
        tong_ky_hieu = sum(theo_ky_hieu.values())
        # Đếm theo tên hàm (cách SAI) — chỉ để so:
        tong_theo_ten = 0
        for ten_tep in sorted(os.listdir(THU)):
            if not (ten_tep.startswith("thu_") and ten_tep.endswith(".py")):
                continue
            try:
                with open(os.path.join(THU, ten_tep), encoding="utf-8") as f:
                    cay = ast.parse(f.read())
            except (OSError, SyntaxError):
                continue
            for nut in ast.walk(cay):
                if isinstance(nut, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(k in nut.name for k in ("che", "bi_mat", "bimat", "ro", "lot", "secret")):
                        for con in ast.walk(nut):
                            if (isinstance(con, ast.Call) and isinstance(con.func, ast.Attribute)
                                    and con.func.attr.startswith("assert")):
                                tong_theo_ten += 1
        self.assertGreater(tong_theo_ten, tong_ky_hieu * 3,
                           "hai tiêu chí không còn khác nhau rõ (%d vs %d) — bộ quét đã trôi"
                           % (tong_theo_ten, tong_ky_hieu))
        bang_ghi("D3 đối chứng âm của bộ quét", "AST hai tiêu chí", "—",
                 "ký hiệu=%d · tên hàm=%d" % (tong_ky_hieu, tong_theo_ten))
        doi_chung(self.NHOM)


# =================================================================================================
# Z. TỔNG KẾT — sổ đối chứng + bảng "đường nào che cái gì"
# =================================================================================================
class Z_TongKet(unittest.TestCase):

    def test_z1_moi_nhom_AM_deu_co_doi_chung_duong(self):
        self.assertNotIn("", DOI_CHUNG,
                         "có lượt đối chứng ghi vào khoá RỖNG — lớp quên khai `NHOM`")
        for nhom in ("A", "B", "C", "D"):
            with self.subTest(nhom=nhom):
                self.assertGreater(DOI_CHUNG.get(nhom, 0), 0,
                                   "nhóm %s có ca phủ định nhưng KHÔNG có đối chứng dương nào" % nhom)

    def test_z2_so_phep_do_va_bang_duong_che(self):
        print("\n  SỔ ĐỐI CHỨNG DƯƠNG (nhóm → số lượt): %s"
              % json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))
        print("  BẢNG “ĐƯỜNG NÀO CHE CÁI GÌ” (%d dòng)" % len(BANG))
        for duong, vi_tri, dang, ket_qua in BANG:
            print("    %-44s %-34s %-12s %s" % (duong, vi_tri, dang, ket_qua))
        print("  TỔNG phép đo đã ghi bảng: %d" % SO_PHEP_DO[0])
        self.assertGreater(SO_PHEP_DO[0], 12, "quá ít phép đo — bảng không đủ phủ các đường")

    def test_z3_khong_co_luot_noi_nao_ra_ngoai_loopback(self):
        self.assertEqual(CHAN.so_lan_ngoai_loopback(), 0,
                         "bộ thử đã nối ra ngoài vòng lặp: %r" % (CHAN.da_noi,))

    def test_z4_chot_chan_mang_cua_CHINH_bo_thu_hoat_dong(self):
        s = socket.socket()
        try:
            CHAN.bat()
            with self.assertRaises(AssertionError) as ctx:
                s.connect(("vi-du.example.com", 80))
            self.assertIn("CHẶN MẠNG", str(ctx.exception))
            self.assertIn("vi-du.example.com", CHAN.da_noi)
        finally:
            s.close()
            CHAN.da_noi[:] = [h for h in CHAN.da_noi if h != "vi-du.example.com"]
            CHAN.tat()

    def test_z5_khong_ghi_vao_CSDL_THAT_cua_du_an(self):
        hien_tai = {t: (os.path.exists(os.path.join(_DU_LIEU_THAT, t)),
                        os.path.getmtime(os.path.join(_DU_LIEU_THAT, t))
                        if os.path.exists(os.path.join(_DU_LIEU_THAT, t)) else None)
                    for t in ("hub.db", "hub.db-wal", "hub.db-shm")}
        self.assertEqual(hien_tai, _CSDL_THAT_TRUOC,
                         "bộ thử đã ĐỤNG vào CSDL THẬT của dự án (%s): %r → %r"
                         % (_DU_LIEU_THAT, _CSDL_THAT_TRUOC, hien_tai))

    def test_z6_khong_con_thu_muc_tam_cua_bo_thu(self):
        goc = os.path.basename(_TAM_GOC)
        con = [d for d in os.listdir(tempfile.gettempdir())
               if (d.startswith("vh-g22bimat-") or d.startswith("vh-g22bimat-con-")) and d != goc]
        self.assertEqual(con, [], "bộ thử để lại thư mục tạm: %r" % con)


def setUpModule():
    CHAN.bat()


def tearDownModule():
    CHAN.tat()
    if _TAM_GOC_DO_TOI:
        don_sach_thu_muc(_TAM_GOC)


if __name__ == "__main__":
    print("=== G22/AG-03 · BA ĐƯỜNG RA KHỎI TIẾN TRÌNH + CỔNG G5 + RÀ ASSERTION ===")
    unittest.main(verbosity=2)
