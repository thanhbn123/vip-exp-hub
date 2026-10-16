#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 — AG-03: CHE BÍ MẬT (CREDENTIAL REDACTION) TRÊN **MỌI** ĐƯỜNG.

VÌ SAO CÓ TỆP NÀY
-----------------
G16-05 đã sửa một lỗi THẬT: ngưỡng che theo ĐỘ DÀI (`>= 8`) bỏ sót bí mật NGẮN, và hai đường
(form-body / header) cho hai đáp án khác nhau. Bản vá G16 chuyển sang **che THEO TÊN TRƯỜNG**.
Nghiệm thu G20 của AG-01 kết luận **FAILED**, và che bí mật là một trong năm vùng phải sửa.

Tệp này ĐO LẠI TOÀN BỘ ĐƯỜNG, không tin bản vá cũ:
  · **Đường yêu cầu**: header · thân form · QUERY · ĐƯỜNG DẪN · vị trí TÊN
  · **Đường phản hồi**: thân (JSON / văn bản / trang lỗi) · header · thông điệp ngoại lệ
  · **Đường đi tiếp**: `than_da_che` · `headers_da_che` · `mo_ta_yeu_cau` · `str(e)` · `repr(e)` ·
    `e.args` · `traceback` · `__context__` · stdout/stderr trong lúc gọi
  · **Đường RA KHỎI TIẾN TRÌNH**: log máy chủ THẬT trên đĩa · CSDL tạm · thông báo lỗi của adapter

Với MỖI đường, thử: bí mật DÀI · bí mật NGẮN (1–7 ký tự) · bí mật RỖNG · bí mật TRÙNG TÊN trường
khác · bí mật trong JSON LỒNG NHAU · bí mật bị mã hoá URL HAI LẦN · bí mật là **bí mật của chính
HÃNG** (thứ ta chưa từng gửi).

HAI LUẬT TỰ ÁP (không có thì mọi dòng "✓" ở đây vô nghĩa)
--------------------------------------------------------
1. **ĐỐI CHỨNG ĐƯỜNG** cho MỌI ca phủ định: chuỗi KHÔNG phải bí mật phải đi qua NGUYÊN VẸN, và bí
   mật phải THẬT SỰ có trong thân stub gửi đi (không thì bộ dò đang tìm một chuỗi chưa từng tồn
   tại). Sổ `DOI_CHUNG` ghi từng lượt; `Z_TongKet` tự phán HỎNG nếu một nhóm âm thiếu đối chứng.
2. **TỰ KIỂM BỘ ĐO** trong TIẾN TRÌNH CON: đột biến chính phép che (và chính bản vá mới) rồi khẳng
   định bộ dò PHẢI ĐỎ; kèm đối chứng dương (không đột biến ⇒ XANH).

KHÔNG CÓ CHẾ ĐỘ "NỬA VỜI"
------------------------
    python3 app/thu/thu_g21_bimat.py        # 0 bỏ qua · còn rò là ĐỎ

Ba đường rò đo được ở G21 (`loi_hang.tu_ma_hang` chép nguyên `msg hãng` · `server.log_message`
ghi nguyên query xuống tệp log · trường `duong` của dòng JSONL) đã được VÁ trong chính lượt này
theo quyết định của AG-00, nên tệp này không còn ô "NEEDS_REVIEW" nào: mọi khẳng định đều CỨNG.
Nhóm **G** chứng minh từng ca ĐỎ ĐƯỢC bằng cách TIÊM LẠI đúng hành vi trước bản vá rồi chạy lại —
một ca không đỏ được là một ca không có răng.

GIỚI HẠN ĐÃ BIẾT (không phải ĐẠT): xem `docs/G21_BIMAT.md` §5 — bí mật 1–7 ký tự chỉ xuất hiện
trong ĐƯỜNG DẪN hoặc dưới một TÊN không thuộc danh sách credential thì KHÔNG có gì để nhận diện;
ca `A10b`/`B3` ghim đúng biên giới đó thay vì giả vờ nó không tồn tại.

CHỐT AN TOÀN
------------
Mọi phép đo lớp HTTP chỉ chạm **stub `127.0.0.1` cổng OS cấp**; chốt chặn mạng của chính tệp này
(`ChanMang`) đếm và CHẶN mọi lượt nối ra ngoài vòng lặp. KHÔNG gọi API hãng (kể cả sandbox) —
`V-G09-01`/`V-13906-05` CHƯA CẤP. Bí mật trong tệp này là chuỗi GIẢ tự đặt. CSDL là thư mục tạm;
không mở `CHO_PHEP_LIVE`; không đụng `:5432`.
"""
import contextlib
import gc
import io
import json
import os
import re
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
from urllib.parse import quote, quote_plus, unquote, urlsplit

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
DU_AN = os.path.dirname(GOC)

# =================================================================================================
# CSDL PHẢI NẰM TRONG THƯ MỤC TẠM — ĐẶT BIẾN NGAY Ở CẤP MÔ-ĐUN, TRƯỚC MỌI IMPORT CỦA `app/`
# =================================================================================================
# `cau_hinh.THU_MUC_DU_LIEU` được tính MỘT LẦN lúc `cau_hinh` được nạp, và `cau_hinh` được nạp
# theo `adapter_jt`. Đặt biến SAU khi import là quá muộn: `csdl.mo()` sẽ mở `app/du-lieu/hub.db` —
# CSDL THẬT của dự án. ĐO ĐƯỢC ở lượt chạy trước của chính tệp này: `app/du-lieu/` mọc thêm
# `hub.db` + `-wal` + `-shm` (các cây khác chỉ có `khoa-noi-bo.key`). Một bộ thử ghi vào thư mục
# dữ liệu thật là lỗi chặn phát hành, không phải chuyện nhỏ.
# Tiến trình CON (nhóm F/G chạy ca trong tiến trình con) nhận thư mục qua `VIP_G21_TAM_GOC` để
# KHÔNG đẻ thư mục riêng — thư mục của con do CHA dọn, và `tearDownModule` của con không đụng vào.
_TAM_GOC_DO_TOI = "VIP_G21_TAM_GOC" not in os.environ
_TAM_GOC = (os.environ["VIP_G21_TAM_GOC"] if not _TAM_GOC_DO_TOI
            else tempfile.mkdtemp(prefix="vh-g21bimat-goc-"))
os.environ["VIP_HUB_DATA"] = _TAM_GOC
# Vân tay CSDL THẬT của dự án, chụp TRƯỚC mọi phép đo — `Z5` canh nó không đổi.
_DU_LIEU_THAT = os.path.join(GOC, "du-lieu")
_CSDL_THAT_TRUOC = {t: (os.path.exists(os.path.join(_DU_LIEU_THAT, t)),
                        os.path.getmtime(os.path.join(_DU_LIEU_THAT, t))
                        if os.path.exists(os.path.join(_DU_LIEU_THAT, t)) else None)
                    for t in ("hub.db", "hub.db-wal", "hub.db-shm")}
for _d in (GOC, THU):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import adapter_jt as aj                                                 # noqa: E402
import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402

# =================================================================================================
# 0. BÍ MẬT GIẢ — mọi giá trị dưới đây do tệp này tự đặt, KHÔNG phải credential của ai
# =================================================================================================
BM_DAI = "BI-MAT-DAI-9f3ac21b7d4e"          # dài (>= ngưỡng 8)
BM_NGAN = "aB3"                             # NGẮN (1–7 ký tự) — chỗ ngưỡng độ dài từng bỏ sót
BM_RONG = ""                                # RỖNG — không được làm phép che che bừa
BM_TRUNG_TEN = "customerCode"               # bí mật TRÙNG TÊN một trường khác
BM_HAI_LOP_GC = "a b&c=d"                   # để dựng bí mật bị mã hoá URL HAI LẦN
BM_JSON_LONG = json.dumps({"password": BM_NGAN})        # JSON lồng nhau, giá trị NGẮN
HANG_DAI = "HANG-GIUKHOA-5c1d90aa-KHONG-PHAI-CUA-TA"    # bí mật CỦA HÃNG (ta chưa từng gửi)
HANG_NGAN = "hk3"
HANG_PHIEN = "PHIEN-2f81ce40-SET-COOKIE"
KHONG_BI_MAT = "VH000000001VN"              # mã vận đơn — KHÔNG phải bí mật (đối chứng đường)
CAU_CUA_HANG = "hãng không cấp được mã vận đơn"          # câu chữ của hãng, không phải bí mật
DUONG_THAT = "/webopenplatformapi/api/order/addOrder"    # endpoint thật: đối chứng đường

ACC_GIA_DINH = "acct-gia-dinh-g21"
TS_GIA_DINH = "1700000000000"
CRED_GIA_DINH = {"apiAccount": ACC_GIA_DINH, "privateKey": BM_DAI,
                 "customerCode": "cc-gia-dinh", "password": BM_NGAN}
DON_MAU = {
    "ma_don": "G21-AD-1", "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Thử",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
    "hang_hoa": "Áo thử", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
    "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa",
}

# Sổ ĐỐI CHỨNG ĐƯỜNG: nhóm âm -> số lượt đối chứng dương đã chạy. `Z_TongKet` tự phán HỎNG nếu
# một nhóm âm không có lượt nào. Rỗng nghĩa là "chưa đo được gì", KHÔNG phải "sạch".
DOI_CHUNG = {}
SO_PHEP_DO = [0]
# BẢNG "đường nào che cái gì" — in ở `Z_TongKet`.
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
    """MỌI dạng mà `s` có thể mang trên dây / trong JSON.

    Viết từ mô tả giao thức — percent-encoding của form (`urlencode`), percent-encoding của đường
    dẫn (`quote`), escape ASCII của JSON — KHÔNG gọi `http_jt._bien_the`. Một bộ dò gọi chính hàm
    đang đo thì đột biến hàm đó sẽ tắt luôn bộ dò, và ca tự kiểm ở nhóm F mất răng.
    """
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
    """→ `{tên nơi: chuỗi}` cho MỌI cửa mà một bí mật có thể đi qua để tới log."""
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
    """→ danh sách `(nơi, dạng)` đã rò. RỖNG nghĩa là sạch TRONG PHẠM VI các cửa đã liệt kê.

    Trả DANH SÁCH chứ không `assert` ngay, để một lượt chạy in ra ĐỦ mọi đường rò — một ca chỉ
    báo đường rò đầu tiên thì lần sửa sau vẫn còn đường khác.
    """
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
    """Không có nó thì một URL gõ sai biến bộ thử thành một lượt gọi ra Internet — IM LẶNG."""

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
                    f"CHẶN MẠNG G21: bộ thử định nối ra {dia_chi!r} — chỉ được loopback. "
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
# 3. STUB CỤC BỘ — 127.0.0.1, cổng do OS cấp; thân/header do CHÍNH CA THỬ dựng
# =================================================================================================
class _BoXuLy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StubG21/1.0"
    sys_version = ""

    def log_message(self, *a):
        pass                                # không in ra stdout/stderr: bộ thử đo cả hai luồng đó

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

    def url_voi(self, duong):
        return self.goc + duong

    @property
    def than_tho_cuoi(self):
        return self.da_tra_loi[-1]["than"] if self.da_tra_loi else b""

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

    Đây là stub "nói nhiều" nhất có thể: nếu một bí mật rò qua BẤT KỲ vị trí nào ta gửi đi, nó
    xuất hiện trong thân phản hồi và mọi cửa che đều bị thử cùng lúc.

    ĐỌC TỪ BẢN GHI `yeu_cau`, KHÔNG đọc lại `rfile`: `_BoXuLy` đã đọc thân TRƯỚC khi gọi hàm này,
    nên lượt đọc thứ hai sẽ CHẶN tới hết hạn của khách — biến phép đo thành một lượt HẾT GIỜ.
    Đó là HỎNG GIẢ đã xảy ra thật ở lượt chạy đầu của tệp này (ca A3 xanh vì ngoại lệ hết giờ
    không mang thân nào để rò, tức "sạch" một cách vô nghĩa).
    """
    ban_ghi = bo_xu_ly.server.stub.yeu_cau[-1]
    phan = ["%s: %s" % (ten, gt) for ten, gt in ban_ghi["headers"]]
    phan.append("PATH=" + ban_ghi["duong_dan"])
    phan.append("BODY=" + ban_ghi["than"].decode("utf-8", "replace"))
    return ma, "\n".join(phan).encode("utf-8"), (them_header or {})


# =================================================================================================
# 4. NỀN CA THỬ
# =================================================================================================
DOI_CHUNG_NHOM = {}          # lớp -> tên nhóm đối chứng (mọi lớp ÂM phải khai)


class CaGoc(unittest.TestCase):
    NHOM = ""                # nhóm đối chứng của lớp này (rỗng = lớp không có ca phủ định)

    def mo(self, tra_loi, **kw):
        stub = Stub(tra_loi, **kw)
        self.addCleanup(stub.dung)
        return stub

    def gui(self, url, headers=None, body=None, timeout=5.0):
        """Gửi qua `http_jt.gui_form`, gom cả stdout/stderr trong lúc gọi."""
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

    # ---- hai khẳng định nền: âm (không rò) và DƯƠNG (bí mật thật sự đi qua đường) ----
    def khang_dinh_401(self, e, nhan):
        """Ca ÂM chỉ có nghĩa khi lượt gọi THẬT SỰ hỏng vì hãng TỪ CHỐI (HTTP 401).

        Thiếu khẳng định này, một stub bị treo biến ngoại lệ thành HẾT GIỜ — ngoại lệ đó KHÔNG
        mang thân phản hồi nào, nên mọi phép dò rò rỉ đều "sạch" một cách vô nghĩa. Đây là HỎNG GIẢ
        đã xảy ra thật ở lượt chạy đầu của tệp này.
        """
        self.assertIsNotNone(e, "%s: phải NÉM (stub trả 401)" % nhan)
        self.assertFalse(getattr(e, "timeout", False),
                         "%s: ngoại lệ là HẾT GIỜ, không phải 401 — ca âm vô nghĩa: %s" % (nhan, e))
        self.assertEqual(getattr(e, "ma_http", 0), 401,
                         "%s: ngoại lệ không mang mã 401 (nhận %r)" % (nhan, getattr(e, "ma_http", 0)))

    def khang_dinh_di_tren_day(self, stub, bi_mat, ghi_chu=""):
        """ĐỐI CHỨNG DƯƠNG BẮT BUỘC: bí mật phải THẬT SỰ có trong thân stub đã gửi.

        Không có bước này thì mọi khẳng định "không rò" ở trên đúng một cách vô nghĩa — bộ dò có
        thể đang tìm một chuỗi chưa bao giờ tồn tại trên dây.
        """
        than = self.cho_tra_loi(stub).decode("utf-8", "replace")
        self.assertIn(bi_mat, than,
                      "bí mật %r KHÔNG có trong thân echo ⇒ ca vô nghĩa %s" % (bi_mat, ghi_chu))
        doi_chung(self.NHOM)

    @staticmethod
    def _dang_mo_ta(bi_mat):
        if bi_mat == "":
            return "rỗng"
        if len(bi_mat) < http_jt.DAI_TOI_THIEU_DE_CHE:
            return "ngắn(%d)" % len(bi_mat)
        return "dài(%d)" % len(bi_mat)


# =================================================================================================
# A. ĐƯỜNG YÊU CẦU VÀ ĐƯỜNG PHẢN HỒI — MA TRẬN ĐẦY ĐỦ
# =================================================================================================
class A_DuongChe(CaGoc):
    """Mọi vị trí ta GỬI ĐI × mọi dạng bí mật, với stub echo lại TẤT CẢ."""

    NHOM = "A"

    def _mot_ca(self, nhan, headers, body, bi_mat, url=None, ghi_chu=""):
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(url or stub.url, headers, body)
        self.khang_dinh_401(e, nhan)
        self.khang_dinh_di_tren_day(stub, bi_mat, ghi_chu)
        do()
        ro = tim_ro_ri(e, bi_mat, out, err)
        bang_ghi(nhan, "ngoại lệ + stdout/stderr", self._dang_mo_ta(bi_mat),
                 "sạch" if not ro else str(ro))
        self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)" % (bi_mat, [n for n, _ in ro], nhan))
        return e

    # -- A1: header mang TÊN credential ------------------------------------------------
    def test_a1_header_ten_credential_dai_va_ngan(self):
        for bi_mat in (BM_DAI, BM_NGAN):
            with self.subTest(bi_mat=self._dang_mo_ta(bi_mat)):
                self._mot_ca("A1 header privateKey", {"privateKey": bi_mat}, {"bizContent": "{}"},
                             bi_mat)

    # -- A2: thân form, tên credential, kể cả JSON lồng ---------------------------------
    def test_a2_than_form_credential_dai_ngan_va_long_JSON(self):
        for nhan, body, bi_mat in (
                ("A2 form password", {"password": BM_NGAN}, BM_NGAN),
                ("A2 form password dài", {"password": BM_DAI}, BM_DAI),
                ("A2 form JSON lồng password ngắn",
                 {"bizContent": json.dumps({"password": BM_NGAN})}, BM_NGAN),
                ("A2 form JSON lồng sâu hai tầng",
                 {"bizContent": json.dumps({"a": {"b": {"privateKey": BM_NGAN}}})}, BM_NGAN)):
            with self.subTest(nhan=nhan):
                self._mot_ca(nhan, None, body, bi_mat)

    # -- A3: QUERY của URL --------------------------------------------------------------
    def test_a3_query_dai_ngan_va_long_JSON(self):
        for nhan, gia_tri, bi_mat in (
                ("A3 query token dài", BM_DAI, BM_DAI),
                ("A3 query token ngắn", BM_NGAN, BM_NGAN),
                ("A3 query JSON lồng ngắn", BM_JSON_LONG, BM_NGAN)):
            stub = self.mo(echo_tat)
            url = stub.url_voi(DUONG_THAT + "?token=" + quote_plus(gia_tri))
            kq, e, out, err = self.gui(url)
            self.khang_dinh_401(e, nhan)
            self.khang_dinh_di_tren_day(stub, bi_mat, nhan)
            do()
            ro = tim_ro_ri(e, bi_mat, out, err)
            bang_ghi(nhan, "query URL", self._dang_mo_ta(bi_mat),
                     "sạch" if not ro else str(ro))
            self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)" % (bi_mat, [n for n, _ in ro], nhan))

    # -- A4: header KHÔNG phải tên credential, GIÁ TRỊ là JSON LỒNG ---------------------
    def test_a4_header_gia_tri_JSON_long_bi_mat_NGAN(self):
        """LỖ HỔNG ĐO ĐƯỢC (AG-03, G21) — đường này trước bản vá cho ĐÁP ÁN KHÁC đường form.

        `X-Du-Lieu: {"password": "aB3"}`: cả chuỗi dài >= 8 nên chuỗi JSON ĐƯỢC vào tập che, nhưng
        giá trị BÊN TRONG thì không — trong khi thân form đi qua `_gia_tri_trong_json` và có. Hãng
        echo lại đúng giá trị bên trong ⇒ RÒ. Khẳng định ở đây là bất biến ĐÚNG: mọi giá trị ta
        gửi đi, ở BẤT KỲ vị trí nào, đều phải được soi JSON lồng.
        """
        for nhan, ten in (("A4 header JSON password ngắn", "password"),
                          ("A4 header JSON privateKey ngắn", "privateKey")):
            with self.subTest(nhan=nhan):
                stub = self.mo(lambda bx, gt=BM_NGAN: (401, ("chi tiet: " + gt).encode(), {}))
                headers = {"X-Du-Lieu": json.dumps({ten: BM_NGAN})}
                kq, e, out, err = self.gui(stub.url, headers, {"bizContent": "{}"})
                self.khang_dinh_401(e, nhan)
                # ĐỐI CHỨNG DƯƠNG: header THẬT SỰ đi trên dây, ĐÚNG giá trị JSON đã dựng.
                self.assertIn(("X-Du-Lieu", json.dumps({ten: BM_NGAN})),
                              [(t, v) for t, v in stub.yeu_cau[-1]["headers"]],
                              "%s: header JSON không đi trên dây ⇒ ca vô nghĩa" % nhan)
                self.khang_dinh_di_tren_day(stub, BM_NGAN, nhan)
                do()
                ro = tim_ro_ri(e, BM_NGAN, out, err)
                bang_ghi(nhan, "header JSON lồng", self._dang_mo_ta(BM_NGAN),
                         "sạch" if not ro else str(ro))
                self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)" % (BM_NGAN, [n for n, _ in ro], nhan))

    # -- A5: bí mật CỦA HÃNG nằm trong header phản hồi, dạng JSON lồng -------------------
    def test_a5_bi_mat_CUA_HANG_trong_header_phan_hoi_dang_JSON_long(self):
        """LỖ HỔNG ĐO ĐƯỢC (AG-03, G21): header phản hồi chỉ được soi theo TÊN, nên bí mật của
        hãng nằm trong JSON của một header KHÁC TÊN đi thẳng vào `headers_da_che`."""
        for nhan, bi_mat in (("A5 header phản hồi JSON privateKey ngắn", HANG_NGAN),
                             ("A5 header phản hồi JSON privateKey dài", HANG_DAI)):
            with self.subTest(nhan=nhan):
                stub = self.mo(lambda bx, gt=bi_mat: (
                    401, b'{"code":"145005005"}',
                    {"X-Debug": json.dumps({"privateKey": gt})}))
                kq, e, out, err = self.gui(stub.url, None, {"bizContent": "{}"})
                self.khang_dinh_401(e, nhan)
                # ĐỐI CHỨNG DƯƠNG: bí mật THẬT SỰ có trong HEADER PHẢN HỒI stub đã gửi đi.
                # (Không dùng `khang_dinh_di_tren_day`: ca này bí mật nằm ở header phản hồi, không
                #  nằm trong thân echo — khẳng định vào thân là khẳng định nhầm chỗ.)
                # `cho_tra_loi` CHỜ stub ghi xong: stub ghi bản ghi SAU khi gửi byte, nên đọc ngay
                # là đọc nhầm lúc — HỎNG GIẢ đã xảy ra thật ở lượt chạy của chính tệp này.
                self.cho_tra_loi(stub)
                self.assertIn(bi_mat, json.dumps(stub.da_tra_loi[-1]["headers"], ensure_ascii=False),
                              "%s: hãng không gửi bí mật trong header ⇒ ca vô nghĩa" % nhan)
                doi_chung(self.NHOM)
                do()
                ro = tim_ro_ri(e, bi_mat, out, err)
                bang_ghi(nhan, "header phản hồi JSON lồng", self._dang_mo_ta(bi_mat),
                         "sạch" if not ro else str(ro))
                self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)" % (bi_mat, [n for n, _ in ro], nhan))

    # -- A6: bí mật CỦA HÃNG trong header 2xx (TraLoiHTTP rất hay bị đem đi log) --------
    def test_a6_bi_mat_CUA_HANG_trong_header_luot_2xx(self):
        stub = self.mo(lambda bx: (200, b'{"code":"1","data":{"billCode":"' +
                                   KHONG_BI_MAT.encode() + b'"}}',
                                   {"X-Api-Key": HANG_DAI,
                                    "X-Debug": json.dumps({"token": HANG_NGAN})}))
        kq, e, out, err = self.gui(stub.url, None, {"bizContent": "{}"})
        self.assertIsNone(e, "lượt 2xx không được ném: %r" % (e,))
        self.cho_tra_loi(stub)
        for bi_mat in (HANG_DAI, HANG_NGAN):
            do()
            ro = []
            for dang in sorted(cac_dang(bi_mat)):
                if not dang:
                    continue
                for ten_noi, chuoi in (("TraLoiHTTP.headers", json.dumps(kq.headers, ensure_ascii=False)),
                                       ("TraLoiHTTP.repr", repr(kq)),
                                       ("stdout", out), ("stderr", err)):
                    if dang in chuoi:
                        ro.append((ten_noi, dang))
            bang_ghi("A6 header 2xx", "TraLoiHTTP", self._dang_mo_ta(bi_mat),
                     "sạch" if not ro else str(ro))
            self.assertEqual(ro, [], "RÒ RỈ %r ở lượt 2xx qua %s" % (bi_mat, [n for n, _ in ro]))
        # ĐỐI CHỨNG DƯƠNG: mã vận đơn KHÔNG phải bí mật và phải đi qua NGUYÊN VẸN trong thân 2xx.
        doi_chung(self.NHOM)
        self.assertIn(KHONG_BI_MAT, kq.than.decode("utf-8"), "mã vận đơn bị mất ⇒ ca vô nghĩa")

    # -- A7: bí mật RỖNG không được làm phép che che bừa ---------------------------------
    def test_a7_bi_mat_RONG_khong_lam_che_bua(self):
        """Một giá trị RỖNG không phải bí mật — và nếu nó lọt vào tập che thì `che_bi_mat` sẽ chèn
        nhãn vào GIỮA MỌI KÝ TỰ của thân phản hồi (thay chuỗi rỗng ở mọi vị trí), tức là phá sạch
        thông điệp chẩn đoán.

        BẤT BIẾN ĐÚNG: giá trị rỗng KHÔNG vào tập che; các giá trị THẬT SỰ đã gửi thì vẫn bị che
        (đối chứng dương — chứng minh phép che đang chạy, không phải "không che gì").
        """
        do()
        headers = {"privateKey": BM_RONG, "apiAccount": BM_RONG, "X-Rong": BM_RONG}
        than = {"password": BM_RONG, "bizContent": json.dumps({"password": BM_RONG})}
        tap = http_jt._gia_tri_ta_gui(headers, http_jt._ma_hoa_form(than))
        self.assertNotIn("", tap, "giá trị RỖNG lọt vào tập che ⇒ phép che sẽ phá cả thân")
        self.assertEqual(http_jt.che_bi_mat(b"than nguyen ven", {""}), b"than nguyen ven",
                         "phép che thay thế cả thân vì một mục RỖNG trong tập che")
        # ĐỐI CHỨNG DƯƠNG: cùng đường ấy, một giá trị THẬT thì PHẢI vào tập che.
        self.assertIn(BM_DAI, http_jt._gia_tri_ta_gui({"privateKey": BM_DAI},
                                                      http_jt._ma_hoa_form(than)))
        # Và trên đường THẬT: lượt gọi với bí mật rỗng vẫn hỏng vì 401 (không phải vì treo/che bừa).
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(stub.url, headers, than)
        self.khang_dinh_401(e, "A7")
        doi_chung(self.NHOM)
        bang_ghi("A7 bí mật rỗng", "tập che", "rỗng", "không vào tập che (không che bừa)")

    # -- A8: bí mật TRÙNG TÊN một trường khác -------------------------------------------
    def test_a8_bi_mat_trung_ten_truong_khac(self):
        """Bí mật có GIÁ TRỊ đúng bằng TÊN một trường khác (`customerCode`): phép che phải thay
        HẾT chỗ xuất hiện của nó trong thân echo, và TÊN trường hợp lệ vẫn đọc được."""
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(stub.url, {"privateKey": BM_TRUNG_TEN}, {"bizContent": "{}"})
        self.khang_dinh_401(e, "A8")
        self.khang_dinh_di_tren_day(stub, BM_TRUNG_TEN, "A8")
        do()
        ro = tim_ro_ri(e, BM_TRUNG_TEN, out, err)
        bang_ghi("A8 bí mật trùng tên trường", "ngoại lệ", "trùng tên",
                 "sạch" if not ro else str(ro))
        self.assertEqual(ro, [], "RÒ RỈ %r qua %s" % (BM_TRUNG_TEN, [n for n, _ in ro]))

    # -- A9: mã hoá URL HAI LẦN ----------------------------------------------------------
    def test_a9_bi_mat_ma_hoa_URL_HAI_LAN(self):
        for nhan, gia_tri in (("một lớp", quote_plus(BM_HAI_LOP_GC)),
                              ("hai lớp", quote_plus(quote_plus(BM_HAI_LOP_GC)))):
            with self.subTest(lop=nhan):
                stub = self.mo(echo_tat)
                url = stub.url_voi(DUONG_THAT + "?password=" + gia_tri)
                kq, e, out, err = self.gui(url)
                self.khang_dinh_401(e, nhan)
                self.assertIn(gia_tri, self.cho_tra_loi(stub).decode("utf-8", "replace"),
                              "dạng %s không có trong thân echo ⇒ ca vô nghĩa" % nhan)
                doi_chung(self.NHOM)
                do()
                ro = []
                for dang in sorted(cac_dang(gia_tri)):
                    if not dang:
                        continue
                    for noi, chuoi in _cac_noi_ro(e, out, err).items():
                        if dang in chuoi:
                            ro.append((noi, dang))
                bang_ghi("A9 query mã hoá %s" % nhan, "query URL", "mã hoá %s" % nhan,
                         "sạch" if not ro else str(ro))
                self.assertEqual(ro, [], "RÒ RỈ %r (%s) qua %s" % (gia_tri, nhan, [n for n, _ in ro]))

    # -- A10: bí mật nằm trong ĐƯỜNG DẪN -------------------------------------------------
    def test_a10_bi_mat_DAI_nam_trong_DUONG_DAN_khong_ro(self):
        """Đoạn đường dẫn CHỨA bí mật dài: nhận diện được (blob ngẫu nhiên), phải che."""
        nhan = "A10 đoạn đường dẫn chứa bí mật dài"
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(stub.url_voi("/api/%s/order/addOrder" % BM_DAI))
        self.khang_dinh_401(e, nhan)
        self.khang_dinh_di_tren_day(stub, BM_DAI, nhan)
        do()
        ro = tim_ro_ri(e, BM_DAI, out, err)
        bang_ghi(nhan, "đường dẫn URL", self._dang_mo_ta(BM_DAI), "sạch" if not ro else str(ro))
        self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)" % (BM_DAI, [n for n, _ in ro], nhan))

    def test_a10b_BIEN_GIOI_bi_mat_NGAN_chi_nam_trong_DUONG_DAN(self):
        """BIÊN GIỚI ĐÃ BIẾT — ghi ra để nó KHÔNG bị đọc thành "đạt" (khuôn `thu_g18_bi_mat.k2d`).

        Một đoạn đường dẫn 1–7 ký tự (`/api/aB3/…`) mà bí mật ấy KHÔNG xuất hiện ở bất kỳ vị trí
        nào khác thì không có gì để nhận diện: đoạn đường dẫn không có TÊN, và độ dài dưới ngưỡng
        nên không phân biệt được với một endpoint thật (`order`, `api`, `v1`). Che mọi đoạn ngắn là
        che luôn tên endpoint — thứ duy nhất cho biết lượt gọi đi tới đâu.

        Khẳng định ở đây là BẤT BIẾN ĐÚNG, không phải "miễn trừ":
          · cùng bí mật NGẮN ấy, khi so BẰNG NHAU với một giá trị ta ĐÃ GỬI ở trường credential,
            thì PHẢI được nhận diện (kể cả khi nó nằm trong đường dẫn);
          · bí mật DÀI trong đường dẫn vẫn phải nhận diện được (ca A10 ngay trên) — biên giới
            KHÔNG được mở rộng.
        """
        do()
        self.assertTrue(http_jt._doan_chua_bi_mat(BM_NGAN, {BM_NGAN}),
                        "bí mật ngắn trùng nguyên một đoạn đường dẫn KHÔNG được nhận diện")
        self.assertFalse(http_jt._doan_chua_bi_mat(BM_NGAN, set()),
                         "đoạn đường dẫn bị coi là bí mật khi KHÔNG có căn cứ nào")
        self.assertTrue(http_jt._la_doan_bi_mat(BM_DAI),
                        "bí mật dài trong đường dẫn không được nhận diện")
        doi_chung(self.NHOM)
        bang_ghi("A10b BIÊN GIỚI bí mật ngắn chỉ trong đường dẫn", "đường dẫn URL", "ngắn(3)",
                 "CHƯA ĐO ĐƯỢC (biên giới đã biết — docs/G21_BIMAT.md §5)")


# =================================================================================================
# B. NHẤT QUÁN GIỮA CÁC ĐƯỜNG — cùng một bí mật ⇒ cùng một kết quả
# =================================================================================================
class B_NhatQuan(CaGoc):
    """Tiêu chí ĐẠT của G21: giá trị bị che phải NHẤT QUÁN giữa các đường.

    G16 từng đo được HAI đường cho HAI đáp án khác nhau (form-body và header). Tệp này đo lại
    đúng khuôn đó: cùng bí mật `BM_NGAN`, đặt ở 5 vị trí, với cùng một thân phản hồi — kết quả che
    phải GIỐNG NHAU.
    """
    NHOM = "B"

    def test_b1_cung_bi_mat_ngan_cho_cung_ket_qua_o_moi_duong(self):
        """NĂM vị trí, CÙNG một bí mật, và ở mọi vị trí nó đều nằm dưới một TÊN credential.

        Cố ý dùng tên credential ở CẢ NĂM vị trí: ca này đo **tính nhất quán giữa các đường**, không
        đo ngưỡng độ dài. Trộn một tên không-credential vào đây là đo hai thứ trong một ca, rồi
        không biết kết quả đỏ là do đường nào — ngưỡng độ dài có ca riêng (B2, A11).
        """
        truong_hop = {
            "header tên credential": ({"privateKey": BM_NGAN}, {"bizContent": "{}"}, None),
            "header JSON lồng": ({"X-Du-Lieu": json.dumps({"password": BM_NGAN})},
                                 {"bizContent": "{}"}, None),
            "thân form": (None, {"password": BM_NGAN}, None),
            "thân form JSON lồng": (None, {"bizContent": json.dumps({"password": BM_NGAN})}, None),
            "query tên credential": (None, {"bizContent": "{}"}, "?password=" + BM_NGAN),
        }
        ket_qua = {}
        for nhan, (h, b, q) in truong_hop.items():
            with self.subTest(duong=nhan):
                stub = self.mo(lambda bx: (401, b"chi tiet: " + BM_NGAN.encode(), {}))
                url = stub.url_voi(DUONG_THAT + q) if q else stub.url
                kq, e, out, err = self.gui(url, h, b)
                self.khang_dinh_401(e, nhan)
                self.khang_dinh_di_tren_day(stub, BM_NGAN, nhan)
                ket_qua[nhan] = getattr(e, "than_da_che", b"").decode("utf-8", "replace")
        do()
        gia_tri = sorted(set(ket_qua.values()))
        bang_ghi("B1 nhất quán", "5 đường", "ngắn(%d)" % len(BM_NGAN),
                 "1 kết quả" if len(gia_tri) == 1 else "%d kết quả khác nhau" % len(gia_tri))
        self.assertEqual(len(gia_tri), 1,
                         "CÙNG một bí mật cho %d kết quả KHÁC NHAU ở các đường: %r"
                         % (len(gia_tri), ket_qua))
        self.assertEqual(gia_tri[0], "chi tiet: [DA-CHE]",
                         "kết quả che không đúng dạng nhãn: %r" % gia_tri[0])
        # ĐỐI CHỨNG DƯƠNG: KHÔNG đường nào để lọt bí mật.
        doi_chung(self.NHOM)

    def test_b3_BIEN_GIOI_bi_mat_NGAN_duoi_TEN_khong_credential(self):
        """BIÊN GIỚI ĐÃ BIẾT của ngưỡng độ dài — khai ra thay vì để nó lặng lẽ thành "đạt".

        Một giá trị 1–7 ký tự nằm dưới một TÊN KHÔNG thuộc danh sách credential (`?tk=`, `X-Ma-Don`)
        KHÔNG được tự động che: đó là đánh đổi có ý thức từ G16/G17 (`test_j2`, `test_j5` ghim đúng
        ngưỡng này), vì che mọi giá trị ngắn là che cả `trang=2`, `ma=1`, `id=7` — thông điệp chẩn
        đoán mất hết thông tin.

        BẤT BIẾN ĐÚNG được khẳng định ở đây, không phải "miễn trừ":
          · ngưỡng vẫn còn tác dụng (giá trị ngắn dưới tên lạ ⇒ KHÔNG che);
          · NHƯNG nếu CÙNG bí mật ấy xuất hiện ở một vị trí CÓ TÊN credential thì nó bị che ở MỌI
            chỗ trong thân phản hồi — kể cả chỗ nằm dưới tên lạ (che theo GIÁ TRỊ, đã gom một lần).
        """
        do()
        self.assertNotIn(BM_NGAN, http_jt._gia_tri_can_che({"X-Ma-Don": BM_NGAN}, b"x=1"),
                         "giá trị ngắn dưới tên KHÔNG phải credential bị che ⇒ ngưỡng mất tác dụng")
        # CÙNG bí mật, nay có thêm một vị trí TÊN credential ⇒ phải có trong tập che.
        self.assertIn(BM_NGAN, http_jt._gia_tri_can_che(
            {"X-Ma-Don": BM_NGAN, "privateKey": BM_NGAN}, b"x=1"),
            "bí mật ở vị trí tên credential KHÔNG vào tập che")
        # Và phép che theo GIÁ TRỊ áp cho MỌI chỗ xuất hiện, không phân biệt tên.
        than = http_jt.che_bi_mat(("tk=" + BM_NGAN + " & privateKey=" + BM_NGAN).encode(),
                                  {BM_NGAN})
        self.assertNotIn(BM_NGAN.encode(), than, "che theo giá trị bỏ sót một chỗ xuất hiện")
        doi_chung(self.NHOM)
        bang_ghi("B3 BIÊN GIỚI ngắn dưới tên không-credential", "tập che", "ngắn(3)",
                 "CHƯA CHE ĐƯỢC (ngưỡng có ý thức — docs/G21_BIMAT.md §5)")

    def test_b2_nguong_do_dai_van_con_tac_dung_cho_ten_khong_credential(self):
        """Nhất quán KHÔNG có nghĩa là che hết: giá trị NGẮN dưới một TÊN không phải credential
        vẫn phải đi qua nguyên vẹn, nếu không thông điệp chẩn đoán bị che vô tội vạ."""
        do()
        self.assertNotIn("VH12", http_jt._gia_tri_can_che({"X-Ma-Don": "VH12"}, b"x=1"))
        self.assertIn("VH123456", http_jt._gia_tri_can_che({"X-Ma-Don": "VH123456"}, b"x=1"))
        # ĐỐI CHỨNG DƯƠNG: cùng bí mật NGẮN nhưng TÊN là credential thì PHẢI có trong tập che.
        self.assertIn(BM_NGAN, http_jt._gia_tri_can_che({"privateKey": BM_NGAN}, b"x=1"))
        doi_chung(self.NHOM)
        bang_ghi("B2 ngưỡng độ dài", "tập che", "ngắn(3)", "còn tác dụng")


# =================================================================================================
# C. ĐỐI CHỨNG ĐƯỜNG — chuỗi KHÔNG phải bí mật đi qua NGUYÊN VẸN
# =================================================================================================
class C_DoiChungDuong(CaGoc):
    NHOM = "C"

    def test_c1_chuoi_khong_phai_bi_mat_di_qua_NGUYEN_VAN(self):
        """Không có ca này thì "không rò" ở trên có thể đạt được bằng cách che SẠCH mọi thứ — và
        một thông điệp chẩn đoán bị che sạch thì người trực ca không đọc được gì.

        Đối chứng đường ở đây cố ý chọn hai thứ KHÔNG phải bí mật mà phép che hay ăn nhầm nhất:
        một giá trị NGẮN dưới tên KHÔNG credential (`don-42`), và TÊN endpoint trong đường dẫn
        (`addOrder`) — thứ duy nhất cho biết lượt gọi đi tới đâu.
        """
        ngan = "don-42"                     # 6 ký tự, KHÔNG phải credential, KHÔNG phải bí mật
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(stub.url, {"X-Ma-Don": ngan},
                                   {"bizContent": json.dumps({"txlogisticId": BM_DAI})})
        self.khang_dinh_401(e, "C1")
        than = self.cho_tra_loi(stub).decode("utf-8", "replace")
        self.assertIn(ngan, than, "chuỗi đối chứng không đi trên dây ⇒ ca vô nghĩa")
        doi_chung(self.NHOM)
        do()
        self.assertIn(ngan, str(e), "giá trị ngắn KHÔNG phải bí mật bị che mất khỏi thông điệp")
        self.assertIn("addOrder", str(e), "TÊN endpoint bị che mất — chẩn đoán mất thông tin")
        self.assertIn("apiAccount", str(e), "TÊN trường hợp lệ bị che mất")
        # ĐỐI CHỨNG DƯƠNG của chính ca này: phép che ĐANG chạy (bí mật dài trong bizContent bị che).
        self.assertNotIn(BM_DAI, str(e), "phép che không chạy ⇒ 'nguyên vẹn' ở trên vô nghĩa")
        bang_ghi("C1 đối chứng đường", "thông điệp + thân", "ngắn(6) + tên endpoint", "nguyên vẹn")

    def test_c2_than_2xx_van_NGUYEN_VAN_theo_hop_dong(self):
        """Hợp đồng §36: thân 2xx là BẰNG CHỨNG, không được sửa. Che nó là phá dữ liệu nghiệp vụ
        (mã vận đơn nằm trong đó)."""
        than_that = json.dumps({"code": "1", "data": {"billCode": KHONG_BI_MAT}}).encode()
        stub = self.mo(lambda bx: (200, than_that, {}))
        kq, e, out, err = self.gui(stub.url, None, {"bizContent": "{}"})
        self.assertIsNone(e, "2xx không được ném: %r" % (e,))
        self.cho_tra_loi(stub)
        doi_chung(self.NHOM)
        do()
        self.assertEqual(kq.than, than_that, "thân 2xx bị SỬA — hợp đồng §36 bị phá")
        bang_ghi("C2 thân 2xx", "TraLoiHTTP.than", "không phải bí mật", "nguyên vẹn")

    def test_c3_gia_tri_o_vi_tri_TEN_khong_bi_in_ra(self):
        """Bí mật đặt NHẦM vào vị trí TÊN header: nó không được vào thông điệp lỗi, nhưng TÊN hợp
        lệ vẫn phải đọc được."""
        mat = "MAT KHAU BI MAT 0123456789"      # có dấu cách ⇒ tên header không hợp lệ
        stub = self.mo(echo_tat)
        kq, e, out, err = self.gui(stub.url, {mat: "x"}, {"bizContent": "{}"})
        # Tên header không hợp lệ bị chặn TRƯỚC khi mở socket ⇒ ngoại lệ VĨNH VIỄN, `ma_http=0`
        # (không phải 401: chưa có lượt nào ra tới hãng). Khẳng định đúng loại ngoại lệ, không
        # khẳng định mã HTTP — khẳng định mã 401 ở đây là khẳng định sai chỗ.
        self.assertIsNotNone(e, "C3: tên header không hợp lệ phải bị CHẶN")
        self.assertFalse(getattr(e, "timeout", False), "C3: ngoại lệ là HẾT GIỜ — ca vô nghĩa")
        self.assertEqual(getattr(e, "loai", ""), "tham-so-sai",
                         "C3: loại ngoại lệ không phải tham-so-sai (nhận %r)" % getattr(e, "loai", ""))
        doi_chung(self.NHOM)
        do()
        for noi, chuoi in _cac_noi_ro(e, out, err).items():
            self.assertNotIn(mat, chuoi, "RÒ RỈ giá trị ở vị trí TÊN qua %s" % noi)
        self.assertEqual(stub.yeu_cau, [], "tên sai mà vẫn có lượt gửi đi")
        self.assertEqual(http_jt._mo_ta_ten("apiAccount"), "apiAccount",
                         "TÊN hợp lệ bị che mất — chẩn đoán mất thông tin")
        bang_ghi("C3 bí mật ở vị trí TÊN", "thông điệp lỗi", "dài(24)", "sạch + tên hợp lệ giữ")


# =================================================================================================
# D. THÔNG BÁO LỖI CỦA HÃNG — đường MỚI chưa được đo ở G16–G20
# =================================================================================================
class D_Adapter_ThongBaoLoi(CaGoc):
    """Đường MỚI: phản hồi từ hãng → thông báo lỗi của adapter → ngoại lệ → **thân HTTP 502**.

    Vì sao đường này là chỗ dễ rò nhất: thân của lượt **HTTP 200** là BẰNG CHỨNG NGUYÊN VĂN theo
    hợp đồng §36 (nó không bị che ở tầng HTTP — và đó là chủ ý, mã vận đơn nằm trong đó). Nhưng
    adapter lại đọc `msg` từ chính thân ấy rồi chép vào thông điệp lỗi, và `don_hang` biến thông
    điệp ấy thành thân phản hồi 502 — tức bí mật đi ra ngoài đúng đường người dùng NHÌN THẤY.
    """
    NHOM = "D"

    def _kq_tu_msg_hang(self, bi_mat):
        """Kết quả THẬT của adapter khi hãng echo bí mật trong `msg` của một lượt HTTP 200."""
        stub = self.mo(lambda bx, gt=bi_mat: (
            200, json.dumps({"code": "145005005", "msg": "khoa cua ban: " + gt,
                             "data": None}).encode("utf-8"), {}))
        ad = aj.AdapterJT(dict(CRED_GIA_DINH), "mock")
        with aj.DungDiemCuoiTam(stub.goc):
            yc = ad.yeu_cau_tao_don(dict(DON_MAU))
            yc["url"] = aj.url_cua("createOrder", "sandbox")
            kq = ad._goi_that(http_jt, "createOrder", yc)
        self.cho_tra_loi(stub)
        # ĐỐI CHỨNG DƯƠNG: bí mật THẬT SỰ có trong thân phản hồi của hãng.
        self.assertIn(bi_mat, self.cho_tra_loi(stub).decode("utf-8", "replace"),
                      "hãng chưa echo bí mật ⇒ ca vô nghĩa")
        doi_chung(self.NHOM)
        return kq

    def test_d1_thong_diep_adapter_khong_chua_van_ban_cua_hang(self):
        """`kq.loi` · `kq.tho` · chuỗi mà `don_hang` đưa vào thân 502 — KHÔNG được chứa bí mật."""
        for nhan, bi_mat in (("D1 msg hãng — bí mật NGẮN", BM_NGAN),
                             ("D1 msg hãng — bí mật DÀI", BM_DAI)):
            with self.subTest(nhan=nhan):
                kq = self._kq_tu_msg_hang(bi_mat)
                do()
                # ĐÚNG chuỗi `don_hang.gui_don` dựng: `f"hãng từ chối: {kq.loi}"` (dòng 672), rồi
                # `server._chay_that` trả `{"loi": str(e)}` với mã 502. Nên khẳng định trên `kq.loi`
                # là khẳng định trên thân 502; ca D2 đo trọn đường HTTP để chốt điều đó.
                than_502 = "hãng từ chối: " + str(kq.loi)
                ro = []
                for dang in sorted(cac_dang(bi_mat)):
                    if not dang:
                        continue
                    for noi, chuoi in (("KetQuaHang.loi", str(kq.loi)),
                                       ("KetQuaHang.tho", json.dumps(kq.tho, ensure_ascii=False,
                                                                     default=str)),
                                       ("chuỗi thân 502 (don_hang.py:672)", than_502)):
                        if dang in chuoi:
                            ro.append((noi, dang))
                bang_ghi(nhan, "KetQuaHang.loi/tho + thân 502", self._dang_mo_ta(bi_mat),
                         "sạch" if not ro else str(sorted({n for n, _ in ro})))
                self.assertEqual(ro, [], "RÒ RỈ %r qua %s (%s)"
                                 % (bi_mat, [n for n, _ in ro], nhan))
                # ĐỐI CHỨNG ĐƯỜNG: phần ĐÃ DỊCH của bảng mã lỗi vẫn còn — bỏ chẩn đoán là hỏng
                # sản phẩm theo chiều ngược lại.
                self.assertIn("获取运单号失败", str(kq.loi),
                              "thông điệp mất phần mô tả ĐÃ DỊCH của mã lỗi hãng")
                self.assertEqual(kq.tho["loi_chuan"]["ma_goc_hang"], "145005005")

    # ---- nền HTTP dùng chung cho D2: dựng MỘT lần, không dựng lại mỗi vòng lặp ----
    _nen = None

    def _dung_nen_http(self):
        """Máy chủ THẬT trong tiến trình + CSDL tạm. Ba hàm tuyến webhook được TIÊM để tới được
        chỗ dựng thân 502 mà không cần đăng nhập (tuyến webhook là tuyến vãng lai duy nhất chạm
        `LoiNghiepVu`). Phần ĐANG ĐO — ánh xạ ngoại lệ → thân phản hồi (`server._chay_that`) và
        nội dung `kq.loi` — là mã SẢN XUẤT, không bị tiêm.
        """
        cls = type(self)
        if cls._nen is not None:
            return cls._nen
        # Dùng CHÍNH `_TAM_GOC` (đã đặt ở cấp mô-đun, TRƯỚC mọi import của `app/`) — không đẻ thêm
        # thư mục, nên không có thư mục nào để `Z4` bắt làm rác.
        import csdl
        import quyen
        import server
        csdl.mo()
        quyen.seed()
        # `HTTPServer` (một luồng) + luồng phục vụ JOIN ĐƯỢC — cố ý, không dùng
        # `ThreadingHTTPServer`: kết nối CSDL của luồng phục vụ phải được ĐÓNG trước khi xoá thư
        # mục tạm. SQLite ở chế độ WAL TẠO LẠI `hub.db`/`-wal`/`-shm` khi một kết nối còn mở được
        # đóng, nên thư mục "đã xoá" mọc lại và `Z4` bắt được — đúng chuyện đã xảy ra ở bốn lượt
        # chạy liên tiếp trước bản này, kể cả khi đã thử lại `rmtree` nhiều vòng.
        sv = HTTPServer(("127.0.0.1", 0), server.BoXuLy)
        luong = threading.Thread(target=sv.serve_forever, kwargs={"poll_interval": 0.02},
                                 daemon=True)
        self.addCleanup(sv.server_close)
        self.addCleanup(luong.join, 10)
        self.addCleanup(sv.shutdown)
        self.addCleanup(csdl.dong)
        luong.start()
        cls._nen = {"cong": sv.server_address[1], "sv": sv}
        return cls._nen

    def test_d2_than_502_THAT_tren_HTTP_khong_chua_bi_mat(self):
        """ĐO TRỌN ĐƯỜNG: máy chủ THẬT (socket thật) → `LoiNghiepVu` → thân 502 trên dây."""
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
        for nhan, bi_mat in (("D2 thân 502 — bí mật NGẮN", BM_NGAN),
                             ("D2 thân 502 — bí mật DÀI", BM_DAI)):
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
                # ĐỐI CHỨNG DƯƠNG: đúng lượt 502 ấy PHẢI mang thông điệp của hãng (đã dịch) —
                # không có nó thì "thân không chứa bí mật" đúng một cách vô nghĩa (có thể chỉ là 404).
                self.assertEqual(ma, 502, "không phải lượt 502 — ca đo nhầm chỗ: %r" % than[:200])
                self.assertIn("hãng từ chối", than, "thân 502 không mang thông điệp của hãng")
                self.assertIn("145005005", than, "thân 502 mất mã lỗi gốc của hãng")
                do()
                ro = [d for d in sorted(cac_dang(bi_mat)) if d and d in than]
                bang_ghi(nhan, "thân HTTP 502 (socket thật)", self._dang_mo_ta(bi_mat),
                         "sạch" if not ro else "RÒ: %s" % ro)
                self.assertEqual(ro, [], "RÒ RỈ %r trong THÂN 502 trên dây: %r" % (bi_mat, than[:300]))


# =================================================================================================
# E. TỆP BẰNG CHỨNG TRÊN ĐĨA — log máy chủ THẬT, đọc lại từ đĩa
# =================================================================================================
# Hai hàm dưới đây dựng máy chủ thật trong TIẾN TRÌNH CON. `dot_bien` (tuỳ chọn) là mã Python được
# chèn TRƯỚC `server.chay(...)` — dùng để TIÊM LẠI lỗi cũ và chứng minh ca kiểm ĐỎ ĐƯỢC (nhóm G).
BOOT_SERVER = (
    "import sys\n"
    "sys.path.insert(0, %r)\n"
    "import server\n"
    "%s\n"
    "server.chay(%d)\n")


def dung_nen_tam(ten="vh-g21bimat-"):
    """Nền CSDL tạm + một cổng do OS cấp. KHÔNG BAO GIỜ `app/du-lieu/`."""
    tam = tempfile.mkdtemp(prefix=ten)
    env = dict(os.environ, VIP_HUB_DATA=tam)
    for lenh in ("migrate.py", "khoi_tao.py"):
        subprocess.run([sys.executable, os.path.join(GOC, lenh)], capture_output=True, text=True,
                       env=env, cwd=DU_AN)
    return tam


def dung_may_chu(tam, cong, dot_bien="", log=None):
    """Máy chủ THẬT trong tiến trình con, bind `127.0.0.1` cổng OS cấp."""
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
    """Xoá một thư mục tạm, và CHỜ cho nó ỔN ĐỊNH — không chỉ "vừa xoá xong".

    Vì sao không xoá một lượt rồi kết luận: SQLite ở chế độ WAL **tạo lại** `hub.db`/`-wal`/`-shm`
    khi một kết nối CÒN MỞ được đóng — kể cả kết nối của một luồng máy chủ đã xong việc nhưng chưa
    kết thúc. ĐO ĐƯỢC ở ba lượt chạy liên tiếp của chính tệp này: `rmtree` trả về "đã xoá", rồi
    `Z4` thấy thư mục **mọc lại** y nguyên tên. Nên: xoá → ép thu gom → chờ → kiểm lại một nhịp
    nữa; chỉ trả `True` khi thư mục VẮNG MẶT ỔN ĐỊNH.
    """
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


def goi_http(cong, duong, pt="GET", body=None):
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


class E_TepBangChungTrenDia(CaGoc):
    """Bí mật không cần đi qua ngoại lệ nào: chỉ cần đi qua ĐƯỜNG YÊU CẦU là nó đã vào TỆP LOG.

    Đây là chỗ dễ rò nhất mà G16–G20 chưa đo, và là chỗ `docs/QA_G20.md` §5 mục 4 khai là "chưa
    đo". Ba phép đo: THÂN (đã có từ G15) · QUERY · ĐƯỜNG DẪN.
    """
    NHOM = "E"

    def _mot_luot(self, duong, bi_mat, pt="GET", body=None, dot_bien=""):
        tam = dung_nen_tam()
        self.addCleanup(shutil.rmtree, tam, True)
        cong = cong_roi()
        sv, log = dung_may_chu(tam, cong, dot_bien)
        self.assertIsNotNone(sv, "máy chủ thật không mở cổng %d (log: %s)"
                             % (cong, open(log).read()[-300:] if os.path.exists(log) else ""))
        try:
            goi_http(cong, duong, pt, body)
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
        return quet_thay_bi_mat(tam, bi_mat), tho

    def test_e1_bi_mat_trong_THAN_khong_lot_vao_tep_nao(self):
        thay, _ = self._mot_luot("/api/v2/auth/dang-nhap", BM_DAI, "POST",
                                 {"ten_dang_nhap": "platform-owner", "mat_khau": BM_DAI})
        do()
        bang_ghi("E1 thân request", "log + CSDL tạm", self._dang_mo_ta(BM_DAI),
                 "sạch" if not thay else str(thay))
        self.assertEqual(thay, [], "bí mật trong THÂN đã xuống đĩa: %s" % thay)

    def test_e2_bi_mat_trong_QUERY_khong_lot_vao_tep_nao(self):
        thay, tho = self._mot_luot("/api/v2/don?token=" + BM_DAI, BM_DAI)
        do()
        bang_ghi("E2 query URL", "log + CSDL tạm", self._dang_mo_ta(BM_DAI),
                 "sạch" if not thay else "RÒ xuống đĩa")
        self.assertEqual(thay, [], "bí mật trong QUERY xuống tệp trên đĩa: %s" % thay)
        # ĐỐI CHỨNG ĐƯỜNG: dòng access log VẪN Ở ĐÓ (chỉ mất query) — không phải bị bỏ hẳn.
        self.assertIn("da-cat-query", tho, "dòng access log mất hẳn ⇒ ca vô nghĩa")
        self.assertIn("/api/v2/don", tho, "đường dẫn thật bị che khỏi log ⇒ chẩn đoán mất thông tin")

    def test_e3_bi_mat_trong_DUONG_DAN_khong_lot_vao_tep_nao(self):
        thay, tho = self._mot_luot("/api/" + HANG_DAI + "/x", HANG_DAI)
        do()
        bang_ghi("E3 đường dẫn URL", "log + CSDL tạm", self._dang_mo_ta(HANG_DAI),
                 "sạch" if not thay else "RÒ xuống đĩa")
        self.assertEqual(thay, [], "bí mật trong ĐƯỜNG DẪN xuống tệp trên đĩa: %s" % thay)
        # ĐỐI CHỨNG ĐƯỜNG: dòng log VẪN nói được đường dẫn đã gọi, chỉ đoạn bí mật bị che.
        self.assertIn("/api/[DA-CHE]/x", tho, "dòng log không còn hình dạng đường dẫn đã gọi")

# =================================================================================================
# F. TỰ KIỂM BỘ ĐO — đột biến trong TIẾN TRÌNH CON
# =================================================================================================
class F_TuKiemBoDo(CaGoc):
    """Không có nhóm này thì mọi ca phủ định ở trên có thể đang đo một thứ không bao giờ ĐỎ."""

    NHOM = "F"
    CA_HEADER_JSON = "A_DuongChe.test_a4_header_gia_tri_JSON_long_bi_mat_NGAN"
    CA_PHAN_HOI = "A_DuongChe.test_a5_bi_mat_CUA_HANG_trong_header_phan_hoi_dang_JSON_long"
    CA_CO_BAN = "A_DuongChe.test_a1_header_ten_credential_dai_va_ngan"

    def chay_con(self, ten_ca, dot_bien=""):
        """Dùng CHUNG `chay_ca_trong_con` với nhóm G — một bản cài, không hai bản trôi khỏi nhau."""
        return chay_ca_trong_con(ten_ca, dot_bien)

    def _kiem(self, ten_ca, dot_bien):
        p = self.chay_con(ten_ca, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_f1_tat_phep_che_thi_bo_do_PHAI_DO(self):
        """ĐỘT BIẾN: `che_bi_mat` thành hàm đồng nhất. Mọi ca rò rỉ phải ĐỎ."""
        for ten_ca in (self.CA_CO_BAN, self.CA_HEADER_JSON, self.CA_PHAN_HOI):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, "http_jt.che_bi_mat = lambda du_lieu, can_che: du_lieu")
                self.assertNotEqual(p.returncode, 0,
                                    "tắt phép che mà %s vẫn XANH!\n%s" % (ten_ca, out[-1500:]))
        doi_chung(self.NHOM)

    def test_f2_go_ban_va_JSON_long_trong_HEADER_thi_ca_moi_PHAI_DO(self):
        """ĐỘT BIẾN ĐÚNG BẢN VÁ G21: bỏ phép soi JSON lồng trong giá trị header (yêu cầu) và
        trong giá trị header phản hồi. Ca mới phải ĐỎ — nếu không, bản vá không có RĂNG."""
        for ten_ca, dot_bien in (
                (self.CA_HEADER_JSON, "http_jt._gia_tri_trong_json = lambda chuoi, ra: None"),
                (self.CA_PHAN_HOI,
                 "http_jt._gia_tri_bi_mat_trong_json = lambda chuoi, ra: None; "
                 "http_jt._gia_tri_bi_mat_trong_vb = lambda van_ban, ra: None")):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, dot_bien)
                self.assertNotEqual(p.returncode, 0,
                                    "gỡ bản vá G21 mà %s vẫn XANH — ca không có răng!\n%s"
                                    % (ten_ca, out[-1500:]))
        doi_chung(self.NHOM)

    def test_f3_doi_chung_DUONG_khong_dot_bien_thi_PHAI_XANH(self):
        """ĐỐI CHỨNG DƯƠNG của chính nhóm tự kiểm: không đột biến ⇒ XANH. Thiếu ca này thì một bộ
        chạy con "luôn báo hỏng" cũng làm hai ca trên xanh một cách vô nghĩa."""
        for ten_ca in (self.CA_CO_BAN, self.CA_HEADER_JSON, self.CA_PHAN_HOI):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, "")
                self.assertEqual(p.returncode, 0, "ca hỏng cả khi KHÔNG đột biến:\n%s" % out[-1500:])
                self.assertIn("OK", out)
        doi_chung(self.NHOM)

    def test_f4_chot_chan_mang_cua_CHINH_bo_thu_hoat_dong(self):
        """Nối ra host ngoài phải BỊ CHẶN; nối loopback phải ĐI QUA chốt chặn.

        Lượt nối CỐ Ý ra `vi-du.example.com` được GỠ khỏi sổ đếm ngay sau khi đo: nó là phép thử
        của CHÍNH chốt chặn, không phải một lượt nối của bộ thử. `Z3` đọc sổ đó để khẳng định
        "0 lượt ra ngoài loopback" — để nguyên thì Z3 đỏ vì chính ca này.
        """
        s = socket.socket()
        try:
            CHAN.bat()
            with self.assertRaises(AssertionError) as ctx:
                s.connect(("vi-du.example.com", 80))
            self.assertIn("CHẶN MẠNG", str(ctx.exception))
            self.assertIn("vi-du.example.com", CHAN.da_noi,
                          "lượt nối cố ý không được ghi lại ⇒ số đo '0 lượt ra ngoài' vô nghĩa")
        finally:
            s.close()
            CHAN.da_noi[:] = [h for h in CHAN.da_noi if h != "vi-du.example.com"]
            CHAN.tat()
        doi_chung(self.NHOM)
        do()
        bang_ghi("F4 chốt chặn mạng", "socket.connect", "host ngoài", "BỊ CHẶN")




# =================================================================================================
# G. CHỨNG MINH CA KIỂM **ĐỎ ĐƯỢC** — tiêm lại đúng lỗi vừa vá (yêu cầu (c) của AG-00)
# =================================================================================================
def chay_ca_trong_con(ten_ca, dot_bien=""):
    """Chạy MỘT ca trong TIẾN TRÌNH CON, tuỳ chọn tiêm một dòng đột biến trước khi chạy."""
    ma = (
        "import sys, unittest\n"
        "sys.path.insert(0, %r)\n"
        "sys.path.insert(0, %r)\n"
        "import thu_g21_bimat as T\n"
        "T.CHAN.bat()\n"
        "%s\n"
        "ca = unittest.TestLoader().loadTestsFromName(%r, T)\n"
        "kq = unittest.TextTestRunner(verbosity=2).run(ca)\n"
        "T.CHAN.tat()\n"
        "raise SystemExit(0 if kq.wasSuccessful() else 1)\n"
        % (GOC, THU, dot_bien, ten_ca))
    # Con phải có CSDL RIÊNG: để con thừa hưởng `VIP_HUB_DATA` của cha thì con mở lại đúng tệp
    # CSDL cha vừa xoá, và SQLite TẠO LẠI tệp ấy trong thư mục của cha (đo được: thư mục tạm của
    # cha mọc lại sau khi con thoát). Dọn thư mục của con ngay tại đây, sau khi con kết thúc.
    tam_con = tempfile.mkdtemp(prefix="vh-g21bimat-con-")
    try:
        return subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                              timeout=300, cwd=DU_AN,
                              env=dict(os.environ, VIP_HUB_DATA=tam_con,
                                       VIP_G21_TAM_GOC=tam_con))
    finally:
        don_sach_thu_muc(tam_con)


class G_ChungMinhCaDoDuoc(CaGoc):
    """Ba ca mới (D1 · D2 · E2+E3) phải ĐỎ ĐƯỢC. Khẳng định suông là không đủ.

    Cách chứng minh: TIÊM LẠI đúng hành vi trước bản vá rồi chạy lại chính ca đó — bộ dò phải
    thấy. Kèm ĐỐI CHỨNG DƯƠNG: không tiêm thì ca XANH (nếu không, một bộ chạy con "luôn báo hỏng"
    cũng làm các ca dưới đây xanh vô nghĩa).
    """
    NHOM = "G"

    # Hành vi TRƯỚC bản vá, chép lại nguyên dạng để tiêm:
    #   · `loi_hang.tu_ma_hang` chép thẳng `msg hãng` vào `thong_diep`;
    DOT_BIEN_D3 = ("import loi_hang\n"
                   "loi_hang._mo_ta_msg_hang = (lambda msg: "
                   "(' | msg hãng: %s' % msg) if msg else '')\n")
    #   · `server.log_message` ghi nguyên `fmt % args` (kèm query) và KHÔNG che đường dẫn.
    DOT_BIEN_D4_D5 = (
        "import sys as _sys\n"
        "server.BoXuLy.log_message = (lambda self, fmt, *a: "
        "_sys.stderr.write('[hub] %s\\n' % (fmt % a)))\n"
        "server._doan_duong_dan_trong_log = (lambda d: d)\n")

    def _kiem(self, ten_ca, dot_bien):
        p = chay_ca_trong_con(ten_ca, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_g1_tiem_lai_loi_D3_thi_ca_D1_va_D2_PHAI_DO(self):
        for ten_ca in ("D_Adapter_ThongBaoLoi.test_d1_thong_diep_adapter_khong_chua_van_ban_cua_hang",
                       "D_Adapter_ThongBaoLoi.test_d2_than_502_THAT_tren_HTTP_khong_chua_bi_mat"):
            with self.subTest(ca=ten_ca):
                p, out = self._kiem(ten_ca, self.DOT_BIEN_D3)
                self.assertNotEqual(p.returncode, 0,
                                    "tiêm lại lỗi D3 mà %s vẫn XANH — ca không có RĂNG:\n%s"
                                    % (ten_ca, out[-1500:]))
        # ĐỐI CHỨNG DƯƠNG: không tiêm ⇒ XANH.
        p, out = self._kiem("D_Adapter_ThongBaoLoi."
                            "test_d1_thong_diep_adapter_khong_chua_van_ban_cua_hang", "")
        self.assertEqual(p.returncode, 0, "ca D1 hỏng cả khi KHÔNG tiêm:\n%s" % out[-1500:])
        doi_chung(self.NHOM)

    def test_g2_tiem_lai_loi_D4_D5_thi_ca_E2_va_E3_PHAI_DO(self):
        """Chạy TRÊN BẢN CHƯA VÁ (máy chủ dựng lại với `log_message` cũ) — phép đo phải thấy rò."""
        for nhan, duong, bi_mat in (
                ("E2", "/api/v2/don?token=" + BM_DAI, BM_DAI),
                ("E3", "/api/" + HANG_DAI + "/x", HANG_DAI)):
            with self.subTest(ca=nhan):
                tam = dung_nen_tam()
                self.addCleanup(shutil.rmtree, tam, True)
                cong = cong_roi()
                sv, log = dung_may_chu(tam, cong, self.DOT_BIEN_D4_D5)
                self.assertIsNotNone(sv, "máy chủ (bản chưa vá) không mở cổng %d" % cong)
                try:
                    goi_http(cong, duong)
                    time.sleep(0.4)
                finally:
                    sv.terminate()
                    try:
                        sv.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        sv.kill()
                thay = quet_thay_bi_mat(tam, bi_mat)
                bang_ghi("G2 tiêm lại lỗi cũ — %s" % nhan, "tệp trên đĩa", self._dang_mo_ta(bi_mat),
                         "BỘ DÒ THẤY RÒ" if thay else "KHÔNG THẤY")
                self.assertTrue(thay, "tiêm lại lỗi log cũ mà bộ dò KHÔNG thấy %r rò xuống đĩa — "
                                      "ca E %s không có RĂNG" % (bi_mat, nhan))
        doi_chung(self.NHOM)


# =================================================================================================
# Z. TỔNG KẾT — sổ đối chứng + bảng "đường nào che cái gì"
# =================================================================================================
class Z_TongKet(unittest.TestCase):

    def test_z1_moi_nhom_AM_deu_co_doi_chung_duong(self):
        """Sổ `DOI_CHUNG`: nhóm nào có ca PHỦ ĐỊNH mà không có ĐỐI CHỨNG DƯƠNG thì HỎNG.

        Không có phép kiểm này thì "không rò" có thể đạt được bằng một bộ dò chết.
        """
        self.assertNotIn("", DOI_CHUNG,
                         "có lượt đối chứng ghi vào khoá RỖNG — lớp quên khai `NHOM`")
        for nhom in ("A", "B", "C", "D", "E", "F", "G"):
            with self.subTest(nhom=nhom):
                self.assertGreater(DOI_CHUNG.get(nhom, 0), 0,
                                   "nhóm %s có ca phủ định nhưng KHÔNG có đối chứng dương nào" % nhom)

    def test_z2_so_phep_do_va_bang_duong_che(self):
        print("\n  SỔ ĐỐI CHỨNG DƯƠNG (nhóm → số lượt): %s"
              % json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))
        print("  BẢNG “ĐƯỜNG NÀO CHE CÁI GÌ” (%d dòng)" % len(BANG))
        for duong, vi_tri, dang, ket_qua in BANG:
            print("    %-44s %-22s %-12s %s" % (duong, vi_tri, dang, ket_qua))
        print("  TỔNG phép đo đã ghi bảng: %d" % SO_PHEP_DO[0])
        self.assertGreater(SO_PHEP_DO[0], 15, "quá ít phép đo — bảng không đủ phủ các đường")

    def test_z3_khong_co_luot_noi_nao_ra_ngoai_loopback(self):
        self.assertEqual(CHAN.so_lan_ngoai_loopback(), 0,
                         "bộ thử đã nối ra ngoài vòng lặp: %r" % (CHAN.da_noi,))

    def test_z5_khong_ghi_vao_CSDL_THAT_cua_du_an(self):
        """Bộ thử này KHÔNG được tạo/sửa `app/du-lieu/hub.db` — CSDL THẬT của dự án.

        VÌ SAO CÓ CA NÀY: nó đã xảy ra THẬT. `cau_hinh.THU_MUC_DU_LIEU` được tính MỘT LẦN lúc nạp
        mô-đun (theo `adapter_jt`), nên đặt `VIP_HUB_DATA` SAU khi import là quá muộn — `csdl.mo()`
        mở `app/du-lieu/hub.db`, và thư mục dữ liệu thật mọc thêm `hub.db` + `-wal` + `-shm`. Bản
        vá: đặt biến Ở CẤP MÔ-ĐUN, trước mọi import của `app/`. Ca này canh bản vá đó.
        """
        hien_tai = {t: (os.path.exists(os.path.join(_DU_LIEU_THAT, t)),
                        os.path.getmtime(os.path.join(_DU_LIEU_THAT, t))
                        if os.path.exists(os.path.join(_DU_LIEU_THAT, t)) else None)
                    for t in ("hub.db", "hub.db-wal", "hub.db-shm")}
        self.assertEqual(hien_tai, _CSDL_THAT_TRUOC,
                         "bộ thử đã ĐỤNG vào CSDL THẬT của dự án (%s): %r → %r"
                         % (_DU_LIEU_THAT, _CSDL_THAT_TRUOC, hien_tai))
        do()
        bang_ghi("Z5 CSDL thật của dự án", "app/du-lieu", "—", "KHÔNG bị đụng")

    def test_z4_khong_con_thu_muc_tam_cua_bo_thu(self):
        # `_TAM_GOC` là thư mục CSDL của CHÍNH mô-đun này; nó bị xoá ở `tearDownModule` (sau ca
        # cuối), nên ở đây chỉ canh mọi thư mục KHÁC — thứ sẽ nằm lại vĩnh viễn nếu rò.
        goc = os.path.basename(_TAM_GOC)
        con = [d for d in os.listdir(tempfile.gettempdir())
               if (d.startswith("vh-g21bimat-") or d.startswith("vip-hub-g21-")) and d != goc]
        self.assertEqual(con, [], "bộ thử để lại thư mục tạm: %r" % con)


def setUpModule():
    CHAN.bat()


def tearDownModule():
    CHAN.tat()
    if _TAM_GOC_DO_TOI:
        don_sach_thu_muc(_TAM_GOC)


if __name__ == "__main__":
    print("=== G21/AG-03 · CHE BÍ MẬT — MỌI KHẲNG ĐỊNH ĐỀU CỨNG (còn rò là ĐỎ) ===")
    unittest.main(verbosity=2)
