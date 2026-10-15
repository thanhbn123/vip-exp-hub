# G18 — HAI ĐƯỜNG RÒ BÍ MẬT MÀ LƯỢT NGHIỆM THU G17 GHI Ở MỤC "CHƯA ĐỎ".
#
# Tệp này là BẰNG CHỨNG cho hai lỗ hổng của AG-01 (G17) và cho phép mở rộng bộ dò:
#   (a) "bí mật hãng ECHO LẠI mà ta chưa từng gửi"  → `CaG18BiMatHangEcho`
#   (b) "bí mật nằm trong ĐƯỜNG DẪN URL"            → `CaG18BiMatDuongDan`
#   (3) sáu DẠNG bí mật × ba VỊ TRÍ                 → `CaG18SauDang`
#   (4) ĐỐI CHỨNG ĐƯỜNG: chuỗi KHÔNG phải bí mật đi qua nguyên văn → `CaG18DoiChungDuong`
#   tự kiểm bộ dò bằng ĐỘT BIẾN mã sản phẩm          → `CaG18TuKiem`
#
# PHẠM VI — nói thẳng cái gì NẰM NGOÀI:
#   · MỌI lượt gửi trong tệp này đi tới STUB CỤC BỘ trên `127.0.0.1` với cổng do hệ điều hành cấp
#     (bind cổng 0). KHÔNG một lượt nào ra Internet, và điều đó ÉP BẰNG MÃ: `setUpModule` thay
#     `socket.socket.connect` bằng chốt chặn chỉ cho loopback đi qua, cộng máy đếm. Gõ sai URL
#     trong bất kỳ ca nào thì ca đó HỎNG TO, chứ không thành một lượt gọi ra ngoài.
#   · KHÔNG đo được hành vi thật của J&T: V-G09-01 + V-13906-05 CHƯA CẤP (SHARED_CONTRACTS §37)
#     nên CHƯA TỪNG có lượt gọi hãng nào. Bộ thử xanh ở đây KHÔNG phải lời cho phép gọi sandbox,
#     và KHÔNG được đọc thành "LIVE VERIFIED".
#   · KHÔNG đo được: hãng thật có echo bí mật của chính nó hay không. Cái đo được là: NẾU hãng làm
#     vậy thì lớp HTTP của ta có chặn hay không. Stub đóng vai một máy chủ "nói nhiều" — đúng vai
#     mà `stub_jt.DOI_DAU` đã đóng ở G16.
#   · KHÔNG chạm CSDL, không chạm mạng ngoài, không bật môi trường nào, không gọi API hãng.
#
# BA LUẬT CỦA BỘ THỬ NÀY (docs/QA_G13_G15.md §6.3):
#   1. Mỗi khẳng định PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG: trước khi nói "bí mật không có trong
#      ngoại lệ", phải chứng minh bí mật THẬT SỰ đã đi trên dây và THẬT SỰ bị echo lại (đọc thân
#      THÔ của stub). Không có bước đó thì "không thấy bí mật" đúng một cách vô nghĩa.
#   2. Mỗi bộ dò phải TỰ KIỂM bằng ĐỘT BIẾN: phá mã sản phẩm rồi chạy lại ĐÚNG ca đó trong TIẾN
#      TRÌNH CON — ca phải ĐỎ. Kèm ĐỐI CHỨNG ĐƯỜNG (không đột biến ⇒ XANH).
#   3. Bộ dò rò rỉ của CHÍNH TỆP NÀY là bản cài thứ HAI, không gọi hàm của sản phẩm: nếu nó lấy
#      `http_jt._bien_the` để quyết định "phải tìm những dạng nào" thì nó chỉ đang tự kiểm chính nó.
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, quote_plus, unquote, urlsplit

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
for _d in (GOC, THU):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402

# ---- Bí mật GIẢ ĐỊNH. Không có credential thật nào tồn tại (SHARED_CONTRACTS §38) — và đó chính
# ---- là lý do các ca rò rỉ ĐO ĐƯỢC: ta biết CHÍNH XÁC chuỗi cần tìm.
HANG_RIENG = "HANG-GIUKHOA-9f3ac21b7d4e-KHONG-PHAI-CUA-TA"    # bí mật CỦA HÃNG, ta chưa từng gửi
HANG_RIENG_VB = "HANG-TRONG-VAN-BAN-7c1d90aa"                # cùng vai, nhưng ở thân KHÔNG phải JSON
HANG_HEADER_VB = "HANG-HEADER-5XX-2f81ce40"                  # cùng vai, nhưng ở header của lượt 5xx
HANG_RIENG_2XX = "HANG-HEADER-2XX-4be27d10"                  # cùng vai, nhưng ở một lượt HTTP 200
HANG_PHIEN = "PHIEN-1234abcd-SET-COOKIE"                     # `Set-Cookie`: bí mật phiên của hãng
BI_MAT_DUONG = "DUONG-DAN-CHUA-BI-MAT-c41f9a2b7e"            # bí mật đặt trong ĐƯỜNG DẪN URL
BI_MAT_QUERY = "TOKEN-QUERY-8a3f21d0"                        # bí mật đặt trong QUERY của URL
ACC_GIA_DINH = "acct-gia-dinh-g18"
TS_GIA_DINH = "1700000000000"
DUONG_THAT = "/webopenplatformapi/api/order/addOrder"        # endpoint THẬT: đối chứng đường
MA_VAN_DON = "VH000000001VN"                                 # dữ liệu HÃNG trả về, KHÔNG phải bí mật
THONG_DIEP_SACH = "hãng không cấp được mã vận đơn"           # câu chữ của hãng, không phải bí mật


# =================================================================================================
# BỘ DÒ RÒ RỈ CỦA CHÍNH TỆP NÀY — bản cài thứ HAI, độc lập với `http_jt`
# =================================================================================================
def cac_dang(s):
    """MỌI dạng mà `s` có thể mang trên dây / trong JSON — TÍNH ĐỘC LẬP với mã sản phẩm.

    Viết từ mô tả GIAO THỨC, không gọi `http_jt._bien_the`: percent-encoding của form
    (`urlencode`), percent-encoding của đường dẫn (`quote`), và escape ASCII của JSON.
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


def _cac_noi_ro(e):
    """→ `{tên nơi: chuỗi}` cho MỌI cửa mà một bí mật có thể đi qua để tới log."""
    return {
        "str(e)": str(e),
        "repr(e)": repr(e),
        "e.args": str(getattr(e, "args", ())),
        "than_da_che": getattr(e, "than_da_che", b"").decode("utf-8", "replace"),
        "headers_da_che": str(getattr(e, "headers_da_che", {})),
        "mo_ta_yeu_cau": str(getattr(e, "mo_ta_yeu_cau", "")),
        "__context__": str(getattr(e, "__context__", None)),
        "traceback": "".join(traceback.format_exception(
            type(e), e, getattr(e, "__traceback__", None))),
    }


def tim_ro_ri(e, bi_mat):
    """→ danh sách `(nơi, dạng)` đã rò. RỖNG nghĩa là sạch.

    Trả về DANH SÁCH chứ không `assert` ngay, để ca thử in ra được ĐỦ mọi đường rò trong một lần
    chạy — một ca chỉ báo đường rò đầu tiên thì lần sửa sau vẫn còn đường khác.
    """
    noi = _cac_noi_ro(e)
    ra = []
    for dang in sorted(cac_dang(bi_mat)):
        for ten_noi in NOI_CO_THE_RO:
            if dang in noi[ten_noi]:
                ra.append((ten_noi, dang))
    return ra


# =================================================================================================
# CHỐT CHẶN MẠNG — chỉ loopback, và ĐẾM mọi lần nối
# =================================================================================================
def _la_loopback(host):
    if not isinstance(host, str):
        return False
    return host in ("localhost", "::1") or host.startswith("127.")


class ChanMangNgoaiG18:
    """Chốt chặn mạng của tệp này: chỉ loopback được nối ra, mọi lần nối đều được ĐẾM.

    Không có nó thì một URL gõ sai biến bộ thử thành một lượt gọi ra Internet — và tệ hơn, thành
    một lượt gọi IM LẶNG. Máy đếm còn là BẰNG CHỨNG cho khẳng định "không có lượt gọi hãng nào".
    """

    def __init__(self):
        self._goc = None
        self.da_noi = []

    def bat(self):
        if self._goc is not None:
            return          # bật hai lần thì mỗi lượt nối bị ĐẾM HAI LẦN và mọi số đo thành sai
        self._goc = socket.socket.connect
        goc = self._goc
        da_noi = self.da_noi

        def connect(sock, dia_chi, *a, **kw):
            host = dia_chi[0] if isinstance(dia_chi, (tuple, list)) and dia_chi else dia_chi
            cong = dia_chi[1] if isinstance(dia_chi, (tuple, list)) and len(dia_chi) > 1 else None
            da_noi.append((host, cong))
            if not _la_loopback(host):
                raise AssertionError(
                    f"CHẶN MẠNG G18: bộ thử định nối ra {dia_chi!r} — chỉ được loopback. "
                    "V-G09-01/V-13906-05 CHƯA CẤP: không có lượt gọi hãng nào được phép.")
            return goc(sock, dia_chi, *a, **kw)

        socket.socket.connect = connect

    def tat(self):
        if self._goc is not None:
            socket.socket.connect = self._goc
            self._goc = None

    def so_lan_ngoai_loopback(self):
        return sum(1 for h, _ in self.da_noi if not _la_loopback(h))


CHAN = ChanMangNgoaiG18()


def setUpModule():
    CHAN.bat()


def tearDownModule():
    CHAN.tat()


# =================================================================================================
# STUB CỤC BỘ — bind `127.0.0.1` cổng 0, thân/header do CA THỬ quyết định
# =================================================================================================
class _BoXuLyG18(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StubG18/1.0"
    sys_version = ""

    def log_message(self, *a):          # không in ra stdout/stderr: bộ thử đo cả hai luồng đó
        pass

    def do_POST(self):
        stub = self.server.stub
        try:
            dai = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            dai = 0
        than_vao = self.rfile.read(dai) if dai > 0 else b""
        headers_goc = list(self.headers.items())
        stub.yeu_cau.append({"duong_dan": self.path, "headers": headers_goc, "than": than_vao})
        than_ra = stub.dung_than(self.path, headers_goc, than_vao)
        headers_them = stub.dung_header(self.path, headers_goc, than_vao) or {}
        self.send_response(stub.ma)
        for ten, gt in headers_them.items():
            self.send_header(ten, gt)
        self.send_header("Content-Type", stub.content_type)
        self.send_header("Content-Length", str(len(than_ra)))
        self.end_headers()
        if than_ra:
            self.wfile.write(than_ra)
        self.wfile.flush()
        stub.da_tra_loi.append({"ma": stub.ma, "than": than_ra, "headers": dict(headers_them)})

    def do_GET(self):
        self.do_POST()


class StubG18:
    """Máy chủ "nói nhiều" cục bộ: thân và header phản hồi do CHÍNH CA THỬ dựng.

    Vì sao không dùng lại `stub_jt.StubJT`: hai lỗ hổng của G18 cần những thân phản hồi mà `StubJT`
    không có chế độ nào tạo ra (bí mật CỦA HÃNG trong JSON lỗi, trong trang lỗi KHÔNG phải JSON, và
    trong header của một lượt 2xx). Thêm ba chế độ vào `stub_jt.py` là sửa tệp của làn khác; dựng
    stub riêng ở đây giữ thay đổi trong đúng tệp được cấp.
    """

    def __init__(self, ma=401, dung_than=None, dung_header=None,
                 content_type="application/json; charset=utf-8", host="127.0.0.1"):
        self.ma = int(ma)
        self.dung_than = dung_than or (lambda duong_dan, h, t: b"{}")
        self.dung_header = dung_header or (lambda duong_dan, h, t: {})
        self.content_type = content_type
        self.yeu_cau = []
        self.da_tra_loi = []
        self.loi_may_chu = []
        self._may_chu = ThreadingHTTPServer((host, 0), _BoXuLyG18)
        self._may_chu.stub = self
        self._may_chu.daemon_threads = True
        self.host = host
        self.cong = self._may_chu.server_address[1]
        self._luong = threading.Thread(target=self._may_chu.serve_forever,
                                       kwargs={"poll_interval": 0.02}, daemon=True)
        self._luong.start()

    @property
    def url(self):
        return f"http://{self.host}:{self.cong}{DUONG_THAT}"

    def url_voi(self, duong_dan):
        return f"http://{self.host}:{self.cong}{duong_dan}"

    def dung(self):
        try:
            self._may_chu.shutdown()
        except Exception:
            pass
        try:
            self._may_chu.server_close()
        except Exception:
            pass

    @property
    def than_tho_cuoi(self):
        """Thân THÔ stub đã gửi đi — ĐỐI CHỨNG DƯƠNG cho mọi khẳng định phủ định."""
        return self.da_tra_loi[-1]["than"] if self.da_tra_loi else b""


# =================================================================================================
# A. LỖ HỔNG (a) — BÍ MẬT CỦA HÃNG, TA CHƯA TỪNG GỬI
# =================================================================================================
class CaGocG18(unittest.TestCase):

    def mo(self, **kw):
        stub = StubG18(**kw)
        self.addCleanup(stub.dung)
        return stub

    def gui(self, url, headers=None, body=None, timeout=5.0):
        h = {"apiAccount": ACC_GIA_DINH, "timestamp": TS_GIA_DINH}
        if headers:
            h.update(headers)
        return http_jt.gui_form(url, h, body if body is not None else {"bizContent": '{"a":1}'},
                                timeout=timeout)

    def cho_tra_loi(self, stub, so=1, het_gio=3.0):
        """Chờ stub GHI XONG phản hồi rồi mới đọc `than_tho_cuoi`.

        Vì sao cần: stub ghi vào `da_tra_loi` SAU khi đã gửi byte đi (đó mới là bản ghi trung thực).
        Nên client có thể nhận đủ thân rồi quay về TRƯỚC khi luồng máy chủ kịp ghi lại — và ca thử
        đỏ dù mã đúng. Đây là HỎNG GIẢ đã xảy ra THẬT ở G17 (ghi trong `thu_http_jt.cho_tra_loi`),
        và nó tái hiện ngay ở lượt chạy đầu của tệp này. Chờ có hạn, rồi mới khẳng định.
        """
        han = time.time() + het_gio
        while len(stub.da_tra_loi) < so and time.time() < han:
            time.sleep(0.005)
        self.assertGreaterEqual(len(stub.da_tra_loi), so,
                                f"stub chưa ghi nhận phản hồi nào sau {het_gio}s")
        return stub.da_tra_loi[-1]["than"]

    def khang_dinh_sach(self, e, bi_mat, ghi_chu=""):
        ro = tim_ro_ri(e, bi_mat)
        self.assertEqual(
            ro, [],
            "RÒ RỈ %r qua %s %s" % (bi_mat, [n for n, _ in ro], ghi_chu))

    def khang_dinh_co_trong_than_tho(self, stub, bi_mat, ghi_chu=""):
        """ĐỐI CHỨNG DƯƠNG: bí mật PHẢI thật sự có trong thân stub đã gửi.

        Không có bước này thì mọi khẳng định "không rò" ở trên đúng một cách vô nghĩa — bộ dò có
        thể đang tìm một chuỗi chưa bao giờ tồn tại.
        """
        than = self.cho_tra_loi(stub).decode("utf-8", "replace")
        self.assertIn(bi_mat, than,
                      f"bí mật {bi_mat!r} KHÔNG có trong thân echo ⇒ ca vô nghĩa {ghi_chu}")


class CaG18BiMatHangEcho(CaGocG18):
    """LỖ HỔNG (a): hãng echo lại bí mật CỦA CHÍNH NÓ — thứ ta CHƯA TỪNG GỬI.

    Phép che của G16/G17 chỉ biết những giá trị TA gửi đi, nên bí mật của hãng đi thẳng vào
    `than_da_che` / `headers_da_che` / thông điệp ngoại lệ. ĐO ĐƯỢC TRƯỚC KHI VÁ (AG-03, 15/10/2026):
    cả ba cửa đều `True` — xem `docs/G18_SECRET_PATHS.md` §1 bảng "trước khi vá".
    """

    def _stub_echo_hang(self):
        """401 + bí mật của hãng ở CẢ HAI chỗ: khoá JSON `privateKey` và header `X-PrivateKey-Echo`.

        Thân CÒN echo lại đường dẫn YÊU CẦU (`self.path`) — đó là cửa sau của lỗ hổng (b): che lúc
        IN mà không đưa giá trị đường dẫn vào TẬP CHE thì bí mật vẫn vào log qua thân echo.
        """
        def than(duong_dan, h, t):
            return json.dumps({
                "code": "145003030", "msg": THONG_DIEP_SACH,
                "data": {"privateKey": HANG_RIENG, "duong_dan_da_nhan": duong_dan},
            }, ensure_ascii=False).encode("utf-8")

        return self.mo(ma=401, dung_than=than,
                       dung_header=lambda dd, h, t: {"X-PrivateKey-Echo": HANG_RIENG})

    def test_k1_bi_mat_CUA_HANG_trong_JSON_loi_va_trong_HEADER_khong_ro(self):
        stub = self._stub_echo_hang()
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url, {"digest": "D" * 24})
        e = ctx.exception
        # ĐỐI CHỨNG DƯƠNG: hãng THẬT SỰ đã nói ra bí mật của nó, ở cả thân lẫn header.
        self.khang_dinh_co_trong_than_tho(stub, HANG_RIENG)
        self.assertEqual(stub.da_tra_loi[-1]["headers"].get("X-PrivateKey-Echo"), HANG_RIENG,
                         "stub không gửi header X-PrivateKey-Echo ⇒ ca vô nghĩa")
        # KHẲNG ĐỊNH PHỦ ĐỊNH: không một cửa nào mang bí mật của hãng ra ngoài.
        self.khang_dinh_sach(e, HANG_RIENG, "(bí mật của hãng, thân JSON + header)")
        # và thân gắn vào ngoại lệ phải ĐÃ CHE, không phải rỗng — che thật, không phải bỏ đi
        self.assertIn("[DA-CHE]", getattr(e, "than_da_che", b"").decode("utf-8", "replace"))

    def test_k1b_bi_mat_CUA_HANG_trong_than_KHONG_phai_JSON_van_bi_che(self):
        """Trang lỗi HTML của tầng proxy — `json.loads` không đọc được, nên phải có đường THỨ HAI.

        Đây là ca canh đúng một hồi quy có thật: ai đó "đơn giản hoá" phép nhận diện về chỉ-đọc-JSON.
        Bí mật trong THÂN cố ý KHÁC bí mật trong header, để hai đường (đọc JSON và đọc văn bản)
        không che lẫn nhau — nếu không thì ca này xanh kể cả khi đường văn bản đã hỏng.
        """
        def than(duong_dan, h, t):
            return ("<html><body>upstream auth failed: "
                    f"privateKey={HANG_RIENG_VB} ; please retry</body></html>").encode("utf-8")

        stub = self.mo(ma=500, dung_than=than,
                       content_type="text/html; charset=utf-8",
                       dung_header=lambda dd, h, t: {"X-Api-Key": HANG_HEADER_VB})
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub.url, {"digest": "D" * 24})
        e = ctx.exception
        self.assertNotEqual(HANG_RIENG_VB, HANG_HEADER_VB, "hai bí mật phải KHÁC nhau")
        self.khang_dinh_co_trong_than_tho(stub, HANG_RIENG_VB)
        self.khang_dinh_sach(e, HANG_RIENG_VB, "(bí mật của hãng, thân KHÔNG phải JSON)")
        self.khang_dinh_sach(e, HANG_HEADER_VB, "(bí mật của hãng, header của lượt 5xx)")

    def test_k1c_luot_2xx_che_HEADER_cua_hang_nhung_than_2xx_VAN_NGUYEN_VAN(self):
        """Ranh giới hợp đồng §36: thân 2xx trả NGUYÊN VĂN cho người gọi; HEADER thì che.

        Ca này là ĐỐI CHỨNG ĐƯỜNG cho chính phép vá: nếu ai đó che luôn thân 2xx cho "chắc", ca này
        ĐỎ — và nó phải ĐỎ, vì che thân 2xx là phá hợp đồng với adapter.
        """
        def than(duong_dan, h, t):
            return json.dumps({"code": "1", "msg": "成功", "data": {"billCode": MA_VAN_DON}},
                              ensure_ascii=False).encode("utf-8")

        stub = self.mo(ma=200, dung_than=than,
                       dung_header=lambda dd, h, t: {"X-Api-Key": HANG_RIENG_2XX,
                                                     "Set-Cookie": "phien=" + HANG_PHIEN})
        kq = self.gui(stub.url, {"digest": "D" * 24})
        self.assertEqual(kq.ma_http, 200)
        # THÂN nguyên văn — hợp đồng §36
        self.assertEqual(kq.than, self.cho_tra_loi(stub), "thân 2xx bị sửa ⇒ phá hợp đồng §36")
        self.assertIn(MA_VAN_DON, kq.than.decode("utf-8"))
        # HEADER của hãng: bí mật của chính hãng bị che, vì `TraLoiHTTP.headers` rất dễ bị đem đi log
        for ten in ("X-Api-Key", "Set-Cookie"):
            gt = kq.headers.get(ten, "")
            self.assertIn("[DA-CHE]", gt, f"header {ten} của hãng không bị che: {gt!r}")
            self.assertNotIn(HANG_RIENG_2XX, gt)
            self.assertNotIn(HANG_PHIEN, gt)
        # ĐỐI CHỨNG ĐƯỜNG: header KHÔNG mang bí mật thì đi qua nguyên văn
        self.assertEqual(kq.headers.get("Content-Type", ""),
                         "application/json; charset=utf-8",
                         "header giao thức bị che ⇒ thông điệp chẩn đoán mất thông tin")


# =================================================================================================
# B. LỖ HỔNG (b) — BÍ MẬT NẰM TRONG ĐƯỜNG DẪN URL
# =================================================================================================
class CaG18BiMatDuongDan(CaGocG18):
    """LỖ HỔNG (b): `mo_ta_yeu_cau` in `phan.path` NGUYÊN VĂN, và mô tả đó KHÔNG đi qua phép che.

    QUYẾT ĐỊNH CỦA AG-03 (15/10/2026): KHÔNG che cả đường dẫn (mất thông tin endpoint), KHÔNG giữ
    nguyên văn (đúng lỗ hổng). Che TỪNG ĐOẠN nguy hiểm, giữ nguyên các đoạn còn lại — lý do đầy đủ
    ở `http_jt._duong_dan_da_che` và `docs/G18_SECRET_PATHS.md` §2.
    """

    DUONG_CO_BI_MAT = "/webopenplatformapi/api/" + BI_MAT_DUONG + "/addOrder"

    def _stub_echo_duong(self, ma=401):
        def than(duong_dan, h, t):
            return json.dumps({"code": "145003030", "msg": THONG_DIEP_SACH,
                               "data": {"duong_dan_da_nhan": duong_dan}},
                              ensure_ascii=False).encode("utf-8")

        return self.mo(ma=ma, dung_than=than)

    def test_k2_bi_mat_trong_DUONG_DAN_khong_ro_ke_ca_khi_hang_echo_lai_duong_dan(self):
        stub = self._stub_echo_duong()
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url_voi(self.DUONG_CO_BI_MAT), {"digest": "D" * 24})
        e = ctx.exception
        # ĐỐI CHỨNG DƯƠNG: đường dẫn THẬT SỰ đi trên dây, và hãng THẬT SỰ echo nó lại.
        self.assertIn(BI_MAT_DUONG, self.cho_tra_loi(stub).decode("utf-8", "replace"),
                      "stub không echo đường dẫn ⇒ ca vô nghĩa")
        self.assertIn(BI_MAT_DUONG, stub.yeu_cau[-1]["duong_dan"],
                      "đường dẫn có bí mật không thật sự đi trên dây ⇒ ca vô nghĩa")
        self.khang_dinh_sach(e, BI_MAT_DUONG, "(bí mật trong đường dẫn)")
        # ĐỐI CHỨNG ĐƯỜNG: phần còn lại của đường dẫn đi qua NGUYÊN VĂN — che đoạn, không che cả path
        mo_ta = getattr(e, "mo_ta_yeu_cau", "")
        self.assertIn("/webopenplatformapi/api/[DA-CHE]/addOrder", mo_ta,
                      f"mô tả phải che ĐÚNG một đoạn và giữ phần còn lại: {mo_ta!r}")
        self.assertNotIn(BI_MAT_DUONG, mo_ta)

    def test_k2b_bi_mat_trong_DUONG_DAN_khi_hang_KHONG_echo_than(self):
        """Cùng lỗ hổng, nhưng cửa duy nhất là `mo_ta` — không có thân echo để lần theo.

        Ca này tách hai cơ chế: `k2` đo được cả `mo_ta` LẪN cửa sau thân-echo; ca này chỉ `mo_ta`.
        """
        stub = self.mo(ma=401, dung_than=lambda dd, h, t: json.dumps(
            {"code": "145003030", "msg": THONG_DIEP_SACH}).encode("utf-8"))
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url_voi(self.DUONG_CO_BI_MAT), {"digest": "D" * 24})
        e = ctx.exception
        self.assertNotIn(BI_MAT_DUONG, self.cho_tra_loi(stub).decode("utf-8", "replace"),
                         "ca này cố ý KHÔNG echo ⇒ tiền đề sai")
        self.khang_dinh_sach(e, BI_MAT_DUONG, "(bí mật trong đường dẫn, không echo)")

    def test_k2c_bi_mat_NGAN_1_den_3_ky_tu_la_CA_MOT_DOAN_duong_dan_van_bi_che(self):
        """Bí mật 1–3 ký tự đứng nguyên một đoạn (`/api/j/order`).

        Che được vì giá trị ĐÃ BIẾT (nó nằm ở một trường credential ta gửi đi), nên luật "cả đoạn
        BẰNG NHAU" bắt được mà không cần ngưỡng độ dài — và không có tác dụng phụ nào.
        """
        for ngan in ("j", "zq", "a%b"):
            with self.subTest(bi_mat=ngan):
                stub = self._stub_echo_duong()
                duong = "/api/" + quote(ngan, safe="") + "/order/addOrder"
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    self.gui(stub.url_voi(duong), {"apiAccount": ngan, "digest": "D" * 24})
                e = ctx.exception
                self.assertIn(quote(ngan, safe=""), stub.yeu_cau[-1]["duong_dan"],
                              "bí mật ngắn không thật sự nằm trong đường dẫn ⇒ ca vô nghĩa")
                self.khang_dinh_sach(e, ngan, f"(bí mật ngắn {ngan!r} là cả một đoạn đường dẫn)")
                self.assertIn("[DA-CHE]", getattr(e, "mo_ta_yeu_cau", ""))

    def test_k2d_BIEN_GIOI_bí_mật_ngan_CHI_co_trong_duong_dan_thi_KHONG_the_nhan_dien(self):
        """BIÊN GIỚI ĐÃ BIẾT — ghi thẳng, không giấu: một token ≤3 ký tự CHỈ có mặt trong đường dẫn.

        Không có tín hiệu nào để nhận ra nó. `zq` trong `/api/zq/order/addOrder` không phân biệt được
        với `v1` trong `/api/v1/order` — và BẤT KỲ luật nào che được `zq` cũng che luôn `v1`, tức là
        che mất chính endpoint. Đây là giới hạn THÔNG TIN, không phải chỗ có thể vá thêm.

        Ca này ĐO ĐÚNG HIỆN TRẠNG và đo luôn ĐỐI CHỨNG ĐƯỜNG, để không ai đọc sự im lặng thành
        "đã phủ". Nó KHÔNG phải một lời khẳng định rằng hiện trạng là an toàn.
        """
        stub = self._stub_echo_duong()
        duong = "/api/zq/order/addOrder"
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url_voi(duong), {"digest": "D" * 24})
        e = ctx.exception
        mo_ta = getattr(e, "mo_ta_yeu_cau", "")
        # Hiện trạng: KHÔNG che (vì không có tín hiệu), và các đoạn endpoint đi qua nguyên văn.
        self.assertIn("/api/zq/order/addOrder", mo_ta,
                      f"hiện trạng đã đổi — cập nhật tài liệu biên giới: {mo_ta!r}")
        # ĐỐI CHỨNG ĐƯỜNG ngay trong ca biên giới: token DÀI trong đường dẫn thì CHE.
        stub2 = self._stub_echo_duong()
        with self.assertRaises(transport.LoiVinhVien) as ctx2:
            self.gui(stub2.url_voi(self.DUONG_CO_BI_MAT), {"digest": "D" * 24})
        self.assertNotIn(BI_MAT_DUONG, getattr(ctx2.exception, "mo_ta_yeu_cau", ""),
                         "token dài trong đường dẫn phải bị che ⇒ biên giới mới đúng là biên giới")
        # và biên giới của "trông như bí mật": endpoint thật KHÔNG bị che (không có chữ-số-trộn)
        for doan in ("webopenplatformapi", "api", "order", "addOrder", "v1"):
            self.assertFalse(http_jt._la_doan_bi_mat(doan),
                             f"đoạn endpoint {doan!r} bị coi là bí mật ⇒ che nhầm, hỏng chẩn đoán")

    def test_k2e_bi_mat_o_QUERY_string_va_o_CA_HAI_cung_luc_khong_ro(self):
        """Đề bài nêu *"query string / path"* — ca này giữ CẢ HAI trong cùng một bộ thân.

        QUERY đã được G17 (AG-02) che bằng `_gia_tri_tu_url`; ở đây nó được đo LẠI trong cùng bộ
        thân với đường dẫn, để một chỗ chạy được trọn câu chuyện "bí mật trong URL". Ca nặng nhất
        là lượt **vừa có bí mật ở query, vừa có bí mật ở đường dẫn** — hai cơ chế che khác nhau
        cùng phải làm việc, và một trong hai hỏng thì `than_da_che` vẫn sạch nếu cái kia che được
        ⇒ nên ca này khẳng định TỪNG bí mật một, không gộp.
        """
        for nhan, duong in (
                ("chỉ query", DUONG_THAT + "?tk=" + BI_MAT_QUERY),
                ("query + đường dẫn", "/api/" + BI_MAT_DUONG + "/order/addOrder?tk=" + BI_MAT_QUERY)):
            with self.subTest(vi_tri=nhan):
                stub = self._stub_echo_duong()
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    self.gui(stub.url_voi(duong), {"digest": "D" * 24})
                e = ctx.exception
                than_tho = self.cho_tra_loi(stub).decode("utf-8", "replace")
                # ĐỐI CHỨNG DƯƠNG: bí mật THẬT SỰ đi trên dây VÀ THẬT SỰ bị echo lại.
                self.assertIn(BI_MAT_QUERY, stub.yeu_cau[-1]["duong_dan"],
                              "bí mật query không thật sự đi trên dây ⇒ ca vô nghĩa")
                self.assertIn(BI_MAT_QUERY, than_tho, "stub không echo query ⇒ ca vô nghĩa")
                self.khang_dinh_sach(e, BI_MAT_QUERY, f"(query, {nhan})")
                if "đường dẫn" in nhan:
                    self.assertIn(BI_MAT_DUONG, than_tho, "stub không echo đường dẫn ⇒ ca vô nghĩa")
                    self.khang_dinh_sach(e, BI_MAT_DUONG, f"(đường dẫn, {nhan})")


# =================================================================================================
# C. SÁU DẠNG BÍ MẬT × BA VỊ TRÍ
# =================================================================================================
class CaG18SauDang(CaGocG18):
    """Mở rộng bộ dò: ba HÌNH DẠNG (ngắn 1–3 · dấu tiếng Việt · ký tự đặc biệt) × ba VỊ TRÍ
    (header · thân form · đường dẫn). G16/G17 chỉ phủ bốn TÊN trường credential với chuỗi ASCII.

    Ghi chú về hai chỗ KHÔNG có ca, kèm lý do — để không ai đọc thiếu sót thành đã phủ:
      · Dấu tiếng Việt ở HEADER: `http.client` mã hoá header bằng latin-1, nên `ậ` (U+1EAD) KHÔNG
        lên được dây — đó là giới hạn của HTTP, không phải của phép che. Dấu tiếng Việt vì vậy được
        đo ở THÂN và ở ĐƯỜNG DẪN (nơi nó đi qua percent-encoding).
      · Token ≤3 ký tự CHỈ có trong đường dẫn: xem `CaG18BiMatDuongDan.test_k2d` — biên giới thông tin.
    """

    # (nhãn, giá trị, các vị trí hợp lệ)
    DANG = (
        ("ngắn-1", "j", ("header", "than", "duong")),
        ("ngắn-2", "zq", ("header", "than", "duong")),
        ("ngắn-3-ky-tu-dac-biet", "a%b", ("header", "than", "duong")),
        ("tiếng-Việt", "mật-khẩu-Ộ-Ước", ("than", "duong")),
        ("ký-tự-đặc-biệt", "aB?cd&e=f", ("header", "than", "duong")),
        ("ký-tự-đặc-biệt-2", "p@ss+w%rd#1", ("header", "than", "duong")),
    )

    def _stub_echo_tat_ca(self):
        """401 echo LẠI CẢ header lẫn thân yêu cầu, và echo đường dẫn — mọi cửa rò mở cùng lúc."""
        def than(duong_dan, h, t):
            return json.dumps({
                "code": "145003030", "msg": THONG_DIEP_SACH,
                "data": {"headers": {k: v for k, v in h},
                         "than": t.decode("utf-8", "replace"),
                         "duong_dan_da_nhan": duong_dan},
            }, ensure_ascii=False).encode("utf-8")

        return self.mo(ma=401, dung_than=than)

    def _khung_chan_doan_sach(self):
        """Thông điệp lỗi của một lượt KHÔNG có bí mật — mốc để loại HỎNG GIẢ cho bí mật 1 ký tự."""
        stub = self._stub_echo_tat_ca()
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url, {"apiAccount": "acc-0001", "digest": "D" * 24},
                     {"bizContent": '{"txlogisticId":"VEH-G18-0001"}', "password": "mat-khau-thuong"})
        return str(ctx.exception)

    def test_k3_sau_dang_bi_mat_o_ca_ba_vi_tri_deu_khong_ro(self):
        khung = self._khung_chan_doan_sach()
        for nhan, gt, vi_tri in self.DANG:
            for vt in vi_tri:
                with self.subTest(dang=nhan, vi_tri=vt):
                    # TIỀN ĐỀ CỦA CHÍNH BỘ DÒ: bí mật 1 ký tự chỉ đo được nếu ký tự đó KHÔNG có
                    # sẵn trong khung chẩn đoán. Không kiểm tiền đề thì ca báo HỎNG GIẢ, và một
                    # HỎNG GIẢ ở cổng an toàn còn tệ hơn không có cổng.
                    if len(gt) <= 2:
                        for dang in cac_dang(gt):
                            self.assertNotIn(dang, khung,
                                             f"khung chẩn đoán đã chứa {dang!r} ⇒ ca HỎNG GIẢ; "
                                             "đổi ký tự")
                    stub = self._stub_echo_tat_ca()
                    h = {"digest": "D" * 24}
                    body = {"bizContent": '{"txlogisticId":"VEH-G18-0002"}'}
                    duong = DUONG_THAT
                    if vt == "header":
                        h["apiAccount"] = gt                     # TÊN thuộc credential
                    else:
                        # Bí mật ĐÃ BIẾT, đặt ở TÊN credential trong THÂN (form mã hoá UTF-8, nên
                        # chở được cả dấu tiếng Việt — header thì không, xem ghi chú đầu lớp).
                        body["password"] = gt
                        # `mật` (1 ký tự) sẽ thành `%E1%BA%AD`; `_duong_dan_da_che` giải mã đoạn
                        # trước khi so, nên vẫn khớp.
                        if vt == "duong":
                            duong = "/api/" + quote(gt, safe="") + "/order/addOrder"
                    with self.assertRaises(transport.LoiVinhVien) as ctx:
                        self.gui(stub.url_voi(duong), h, body)
                    e = ctx.exception
                    # ĐỐI CHỨNG DƯƠNG theo TỪNG vị trí: bí mật THẬT SỰ đi trên dây ở đúng vị trí đó.
                    than_tho = self.cho_tra_loi(stub).decode("utf-8", "replace")
                    if vt == "header":
                        self.assertIn(gt, than_tho, f"{gt!r} không được echo từ header")
                    elif vt == "than":
                        self.assertIn(quote_plus(gt, safe=""), than_tho,
                                      f"dạng trên dây của {gt!r} không có trong thân echo")
                    else:
                        self.assertIn(quote(gt, safe=""), stub.yeu_cau[-1]["duong_dan"],
                                      f"{gt!r} không thật sự nằm trong đường dẫn")
                    self.khang_dinh_sach(e, gt, f"({nhan} ở {vt})")

    def test_k3b_moi_dang_deu_THAT_SU_di_qua_duoc_stub(self):
        """ĐỐI CHỨNG DƯƠNG cho chính BẢNG DẠNG: nếu một dạng không lên được dây thì ca ở trên xanh
        một cách vô nghĩa. Ca này khẳng định stub ĐÃ NHẬN đủ sáu dạng."""
        stub = self._stub_echo_tat_ca()
        body = {"bizContent": '{"txlogisticId":"VEH-G18-0003"}'}
        h = {"digest": "D" * 24}
        for i, (nhan, gt, vi_tri) in enumerate(self.DANG):
            if "than" in vi_tri:
                body["password" + str(i)] = gt
            if "header" in vi_tri:
                h["X-Dang-" + str(i)] = gt
        with self.assertRaises(transport.LoiVinhVien):
            self.gui(stub.url, h, body)
        than_tho = self.cho_tra_loi(stub).decode("utf-8", "replace")
        for nhan, gt, vi_tri in self.DANG:
            if "than" in vi_tri:
                self.assertIn(quote_plus(gt, safe=""), than_tho,
                              f"dạng {nhan!r} không lên được dây ở thân ⇒ ca k3 vô nghĩa")


# =================================================================================================
# D. ĐỐI CHỨNG ĐƯỜNG — CHUỖI KHÔNG PHẢI BÍ MẬT PHẢI ĐI QUA NGUYÊN VĂN
# =================================================================================================
class CaG18DoiChungDuong(CaGocG18):
    """Phép che phải HẸP. Một cổng che mọi thứ là một cổng vô dụng: nó làm thông điệp chẩn đoán
    không còn đọc được, và người trực sẽ tắt nó đi — đó là cách một cổng an toàn chết.
    """

    def test_k4_chuoi_KHONG_phai_bi_mat_di_qua_NGUYEN_VAN(self):
        def than(duong_dan, h, t):
            return json.dumps({
                "code": "145003030",
                "msg": THONG_DIEP_SACH,
                "data": {"billCode": MA_VAN_DON, "duong_dan_da_nhan": duong_dan,
                         "ghiChu": "don hang giao buoi sang"},
            }, ensure_ascii=False).encode("utf-8")

        stub = self.mo(ma=401, dung_than=than)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub.url, {"digest": "D" * 24, "X-Ma-Don": "VH12"})
        e = ctx.exception
        than_da_che = getattr(e, "than_da_che", b"").decode("utf-8", "replace")
        # (1) Dữ liệu của HÃNG mà ta CHƯA TỪNG GỬI, dưới tên KHÔNG phải credential: nguyên văn.
        self.assertIn(MA_VAN_DON, than_da_che,
                      "mã vận đơn của hãng bị che ⇒ che nhầm, thông điệp chẩn đoán mất dữ liệu")
        # (2) Câu chữ của hãng: nguyên văn.
        self.assertIn(THONG_DIEP_SACH, than_da_che)
        # (3) Mã lỗi của hãng: nguyên văn.
        self.assertIn("145003030", than_da_che)
        # (4) Đường dẫn endpoint: nguyên văn, TỪNG ĐOẠN.
        self.assertIn(DUONG_THAT, than_da_che,
                      "endpoint thật bị che ⇒ không còn biết lượt gọi đi đâu")
        # (5) Giá trị NGẮN (< ngưỡng) ở tên KHÔNG phải credential: KHÔNG vào tập che.
        can_che = http_jt._gia_tri_can_che({"X-Ma-Don": "VH12"}, b"x=1")
        self.assertNotIn("VH12", can_che,
                         "giá trị ngắn vô hại bị đưa vào tập che ⇒ ngưỡng đã mất tác dụng")
        # (6) ĐỐI CHỨNG DƯƠNG ngược lại: giá trị DÀI ở tên không phải credential VẪN được che
        #     (nếu không thì (5) chỉ đang chứng minh "tập che rỗng").
        self.assertIn("VH123456", http_jt._gia_tri_can_che({"X-Ma-Don": "VH123456"}, b"x=1"))
        # (7) TÊN trường/header vẫn nguyên văn — tên là thứ duy nhất chỉ đúng chỗ sai.
        self.assertIn("apiAccount", getattr(e, "mo_ta_yeu_cau", ""))

    def test_k4b_than_2xx_van_NGUYEN_VAN_va_khong_bi_che_bua(self):
        """Hợp đồng §36: thân 2xx là BẰNG CHỨNG, không được sửa. Ca này canh phép vá G18 không
        lấn sang thân 2xx (một cách 'sửa cho chắc' rất dễ mắc)."""
        than_that = json.dumps({"code": "1", "msg": "成功", "data": {"billCode": MA_VAN_DON}},
                               ensure_ascii=False).encode("utf-8")
        stub = self.mo(ma=200, dung_than=lambda dd, h, t: than_that)
        kq = self.gui(stub.url, {"digest": "D" * 24})
        self.assertEqual(kq.than, than_that, "thân 2xx bị sửa ⇒ phá hợp đồng §36")
        self.assertNotIn(b"[DA-CHE]", kq.than, "thân 2xx bị che ⇒ phá hợp đồng §36")


# =================================================================================================
# E. TỰ KIỂM BỘ DÒ — ĐỘT BIẾN MÃ SẢN PHẨM TRONG TIẾN TRÌNH CON
# =================================================================================================
class CaG18TuKiem(CaGocG18):
    """Luật 1 của `docs/QA_G13_G15.md` §6.3: MỖI bộ dò mới phải chứng minh nó BẮT ĐƯỢC, bằng cách
    phá chính nó rồi chạy lại ĐÚNG ca đó trong TIẾN TRÌNH CON. Ca phải ĐỎ.

    Mỗi dòng dưới đây là một HỒI QUY CÓ THẬT — một cách sửa sai người sau rất dễ mắc — không phải
    một phép đột biến cho vui. Kèm ĐỐI CHỨNG ĐƯỜNG (`l2`): chạy nguyên lớp ca, KHÔNG đột biến,
    phải XANH; nếu không thì "đột biến làm ca đỏ" không chứng minh được gì, vì một bộ chạy con
    luôn-đỏ cũng làm mọi dòng dưới đây "đạt".
    """

    CA_HANG = "CaG18BiMatHangEcho"
    CA_DUONG = "CaG18BiMatDuongDan"

    CA = (
        (CA_HANG + ".test_k1_bi_mat_CUA_HANG_trong_JSON_loi_va_trong_HEADER_khong_ro",
         "http_jt._gia_tri_bi_mat_tu_phan_hoi = lambda than, h: set()",
         "tắt phép nhận diện bí mật CỦA HÃNG ⇒ lỗ hổng (a) quay lại nguyên vẹn"),
        (CA_HANG + ".test_k1_bi_mat_CUA_HANG_trong_JSON_loi_va_trong_HEADER_khong_ro",
         "http_jt.TRUONG_CREDENTIAL_PHAN_HOI = ()\n"
         "http_jt._MAU_CAP_TEN_BI_MAT = __import__('re').compile(r'(?!)')",
         "gỡ DANH SÁCH TÊN ở CẢ BA đường (header · JSON · văn bản) — tức là gỡ tính năng. Phải gỡ "
         "cả mẫu đã biên dịch, vì nó là BẢN SAO của danh sách tại lúc nạp mô-đun: chỉ đặt danh "
         "sách về rỗng là một phép đột biến KHÔNG có tác dụng, và một phép đột biến không tác "
         "dụng thì không chứng minh được gì"),
        (CA_HANG + ".test_k1_bi_mat_CUA_HANG_trong_JSON_loi_va_trong_HEADER_khong_ro",
         "http_jt._gia_tri_bi_mat_trong_json = lambda vb, ra: None\n"
         "http_jt._gia_tri_bi_mat_trong_vb = lambda vb, ra: None",
         "chỉ còn nhận diện theo TÊN HEADER, bỏ đọc THÂN ⇒ bí mật của hãng trong JSON lỗi lộ "
         "nguyên văn; ca này phải bắt được vì nó kiểm CẢ HAI đường"),
        (CA_HANG + ".test_k1b_bi_mat_CUA_HANG_trong_than_KHONG_phai_JSON_van_bi_che",
         "http_jt._gia_tri_bi_mat_trong_vb = lambda vb, ra: None",
         "chỉ còn đọc JSON ⇒ bí mật của hãng trong trang lỗi HTML lộ nguyên văn"),
        (CA_HANG + ".test_k1c_luot_2xx_che_HEADER_cua_hang_nhung_than_2xx_VAN_NGUYEN_VAN",
         "http_jt._gia_tri_bi_mat_tu_phan_hoi = lambda than, h: set()",
         "bỏ che header phản hồi ⇒ bí mật phiên của hãng nằm trong `TraLoiHTTP.headers`"),
        (CA_DUONG + ".test_k2_bi_mat_trong_DUONG_DAN_khong_ro_ke_ca_khi_hang_echo_lai_duong_dan",
         "http_jt._duong_dan_da_che = lambda url, h, t: (urlsplit(url).path or '/', 0)",
         "quay lại in NGUYÊN VĂN đường dẫn ⇒ đúng lỗ hổng (b) mà G17 để lại"),
        (CA_DUONG + ".test_k2b_bi_mat_trong_DUONG_DAN_khi_hang_KHONG_echo_than",
         "http_jt._duong_dan_da_che = lambda url, h, t: (urlsplit(url).path or '/', 0)",
         "cửa `mo_ta` một mình cũng đủ rò — ca này phải bắt được khi chỉ `mo_ta` bị phá"),
        (CA_DUONG + ".test_k2_bi_mat_trong_DUONG_DAN_khong_ro_ke_ca_khi_hang_echo_lai_duong_dan",
         "http_jt._gia_tri_tu_duong_dan = lambda url, moc: set()",
         "che lúc IN mà không đưa giá trị đường dẫn vào TẬP CHE ⇒ hãng echo lại là lộ (cửa sau)"),
        (CA_DUONG + ".test_k2_bi_mat_trong_DUONG_DAN_khong_ro_ke_ca_khi_hang_echo_lai_duong_dan",
         "http_jt._la_doan_bi_mat = lambda d: False",
         "bỏ luật HÌNH DẠNG ⇒ token dài trong đường dẫn không còn được nhận ra"),
        (CA_DUONG + ".test_k2c_bi_mat_NGAN_1_den_3_ky_tu_la_CA_MOT_DOAN_duong_dan_van_bi_che",
         "http_jt._doan_chua_bi_mat = lambda d, c: False",
         "bỏ luật 'cả đoạn BẰNG NHAU' ⇒ bí mật NGẮN trong đường dẫn lộ nguyên văn"),
        (CA_DUONG + ".test_k2e_bi_mat_o_QUERY_string_va_o_CA_HAI_cung_luc_khong_ro",
         "http_jt._gia_tri_tu_url = lambda u: set()",
         "bỏ giá trị QUERY khỏi tập che ⇒ bí mật trong query lộ khi hãng echo lại"),
    )

    LOP_CA = (CA_HANG, CA_DUONG, "CaG18SauDang", "CaG18DoiChungDuong")

    def chay_con(self, ten_ca, dot_bien=""):
        ma = (
            "import sys, unittest\n"
            f"sys.path.insert(0, {GOC!r})\n"
            f"sys.path.insert(0, {THU!r})\n"
            "import http_jt\n"
            "from urllib.parse import urlsplit\n"
            f"{dot_bien}\n"
            "import thu_g18_bi_mat\n"
            "thu_g18_bi_mat.setUpModule()\n"
            f"ca = unittest.TestLoader().loadTestsFromName({ten_ca!r}, thu_g18_bi_mat)\n"
            "kq = unittest.TextTestRunner(verbosity=2).run(ca)\n"
            "raise SystemExit(0 if kq.wasSuccessful() else 1)\n")
        return subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                              timeout=180, cwd=GOC)

    def _chay(self, ten, dot_bien=""):
        p = self.chay_con(ten, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_l1_moi_bo_do_moi_DEU_bat_duoc_khi_bi_pha(self):
        # CHỐT NGƯỢC: một danh sách RỖNG cũng làm vòng lặp dưới đây "đạt" một cách vô nghĩa —
        # đúng khuôn hỏng mà `chay_tat_ca.sh` đã gặp với `VIP_TOI_THIEU_BO` (dòng 79–84).
        self.assertGreaterEqual(len(self.CA), 11,
                                "danh sách đột biến bị thu hẹp ⇒ cổng tự kiểm mất răng")
        for ten_ca, dot_bien, vi_sao in self.CA:
            self.assertTrue(ten_ca and dot_bien and vi_sao, "mục đột biến thiếu vế")
            with self.subTest(ca=ten_ca.split(".")[-1][:46], pha=dot_bien.split("=")[0][-38:]):
                p, out = self._chay(ten_ca, dot_bien)
                self.assertNotEqual(p.returncode, 0,
                                    f"ĐỘT BIẾN KHÔNG BỊ BẮT — hồi quy: {vi_sao}\n{out[-1500:]}")
                self.assertTrue("FAIL" in out or "ERROR" in out, out[-1500:])

    def test_l2_doi_chung_duong_moi_LOP_CA_XANH_khi_KHONG_dot_bien(self):
        self.assertGreaterEqual(len(self.LOP_CA), 4, "thiếu lớp ca ⇒ đối chứng đường mất răng")
        for ten_lop in self.LOP_CA:
            with self.subTest(lop=ten_lop):
                p, out = self._chay(ten_lop, "")
                self.assertEqual(p.returncode, 0,
                                 f"lớp {ten_lop} hỏng cả khi KHÔNG đột biến:\n{out[-1500:]}")
                self.assertIn("OK", out)

    def test_l3_chot_chan_mang_cua_CHINH_bo_thu_nay_hoat_dong(self):
        """Tự kiểm chốt chặn mạng, và BẰNG CHỨNG "không gọi hãng": mọi lượt nối của tệp này đều
        loopback, TRỪ đúng một lượt cố ý của ca này — và lượt đó đã bị chặn trước khi mở socket."""
        truoc = len(CHAN.da_noi)
        s = socket.socket()
        try:
            with self.assertRaises(AssertionError) as ctx:
                s.connect(("vi-du-g18.example.com", 80))
            self.assertIn("CHẶN MẠNG G18", str(ctx.exception))
        finally:
            s.close()
        # ĐỐI CHỨNG DƯƠNG: chốt chặn KHÔNG chặn bừa — loopback phải đi qua được.
        tam = socket.socket()
        try:
            tam.bind(("127.0.0.1", 0))
            cong_mo = tam.getsockname()[1]
        finally:
            tam.close()
        s2 = socket.socket()
        try:
            with self.assertRaises(OSError):
                s2.connect(("127.0.0.1", cong_mo))   # qua được chốt chặn, rồi hỏng vì cổng đã đóng
        finally:
            s2.close()
        # Mọi lượt nối TỪ TRƯỚC ca này phải là loopback; lượt ngoài duy nhất được phép là lượt
        # cố ý ở trên, và nó nằm ngay tại chỉ số `truoc`.
        for i, (host, _cong) in enumerate(CHAN.da_noi):
            if i == truoc:
                self.assertEqual(host, "vi-du-g18.example.com", "lượt nối cố ý không đúng chỗ")
                continue
            self.assertTrue(_la_loopback(host),
                            f"có lượt nối ra {host!r} tại vị trí {i} — ngoài loopback phải là 0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
