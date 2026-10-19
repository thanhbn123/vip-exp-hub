# G16-A — AG-01 (QA/VERIFIER): bộ thử ĐỘC LẬP cho ba cổng nghiệm thu G16-A.
#
# VÌ SAO CÓ TỆP NÀY
# -----------------
# AG-01 không tin báo cáo PASS của làn nào (kể cả báo cáo của chính mình ở lượt trước).
# Mỗi cổng dưới đây là một phép đo AG-01 TỰ chạy, trên lớp HTTP THẬT (`app/http_jt.py`),
# với stub cục bộ bind `127.0.0.1` CỔNG 0 — không cổng cố định, nên bốn làn chung một cây
# không tranh cổng và không sinh HỎNG GIẢ (R-13, `QA2_TEST_PLAN.md` §6).
#
# BA NHÓM:
#   · `T_Transport`   — G16-A/1 HTTP TRANSPORT (danh sách trắng · hết giờ · 5xx/4xx · KHÔNG tự
#                       thử lại · không rò bí mật · stub chỉ vòng lặp nội bộ)
#   · `C_Credentials` — G16-A/2 CREDENTIAL CONFIGURATION
#   · `H_HopDong`     — G16-A/3 CONTRACT TESTS (chữ ký · UTC+7 · codMoney · ba kết cục · D-9)
#
# HAI CHỐT CHẶN TỰ CAM KẾT (docs/QA_G13_G15.md §6.3 — giữ nguyên ở G16):
#   1. `E_TuKiemBoDo` chạy một ca CỐ Ý HỎNG trong TIẾN TRÌNH CON và khẳng định bộ dò THẤY nó
#      hỏng. Không có nhóm này thì mọi dòng "✓ … ca" của tệp này KHÔNG chứng minh gì.
#   2. Đối chứng DƯƠNG cho mọi ca PHỦ ĐỊNH. `Z_TongKet` đọc sổ `DOI_CHUNG`: nhóm nào có ca âm
#      mà KHÔNG có ca dương nào ⇒ bộ thử TỰ BÁO HỎNG. (Tầng chết hẳn cũng làm ca âm xanh.)
#
# KỸ THUẬT CHỦ ĐẠO — "ĐỒNG HỒ KẾT NỐI": mọi ca danh sách trắng chạy mà KHÔNG cần mạng. Ta thay
# `http.client.HTTPConnection.connect` / `HTTPSConnection.connect` bằng bộ đếm. Khi đó:
#   · host bị TỪ CHỐI  ⇒ ngoại lệ đúng loại VÀ bộ đếm = 0 (chưa hề mở socket);
#   · host được PHÉP   ⇒ bộ đếm > 0 (đã đi qua cổng danh sách trắng).
# Nhờ vậy đo được cả hai host J&T THẬT mà KHÔNG gửi một byte nào ra ngoài.
#
# Chạy: VIP_HUB_DATA=/tmp/veh_g16_ag01_qa python3 app/thu/thu_qa_g16.py
import ast
import base64
import contextlib
import datetime as dt
import hashlib
import http.client
import http.server
import io
import json
import logging
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest
from urllib.parse import parse_qsl

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g16-qa-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import transport                     # noqa: E402
import cau_hinh                      # noqa: E402
import bao_mat                       # noqa: E402
import adapter                       # noqa: E402
import adapter_jt as aj              # noqa: E402
import loi_hang                      # noqa: E402

try:
    import http_jt
except ImportError:                  # AG-02 chưa bàn giao ⇒ nhóm T tự khai BỎ QUA
    http_jt = None

CO_HTTP_JT = http_jt is not None and callable(getattr(http_jt, "gui_form", None))

# ── Sổ đối chứng dương: mỗi ca PHỦ ĐỊNH phải có ít nhất một ca DƯƠNG cùng nhóm ───────────────────
DOI_CHUNG = {}

# ── Sổ PHÁT HIỆN: điều ĐO ĐƯỢC mà chưa đủ mức chặn gộp. In ra ở `Z_TongKet`, không làm đỏ lượt. ──
PHAT_HIEN = []


def _dc(nhom, loai):
    o = DOI_CHUNG.setdefault(nhom, {"duong": 0, "am": 0})
    o[loai] += 1


def _dc_duong(nhom):
    _dc(nhom, "duong")


def _dc_am(nhom):
    _dc(nhom, "am")


CANARY_DUOI = "CANARY-G16-AG01"          # chuỗi dài — PHẢI bị che
CANARY_NGAN = "Ab1!x"                    # chuỗi NGẮN (5 ký tự) — dùng để đo ngưỡng che
TZ7 = dt.timezone(dt.timedelta(hours=7))

# Vector đáp án biết trước — AG-01 tính TAY ngoài bộ thử rồi ghim lại đây. Ca kiểm KHÔNG phụ
# thuộc vào chính hàm của adapter: ai đổi công thức ký thì vector lệch ngay.
VECTOR_G16 = [
    ('{"customerCode": "CC", "txlogisticId": "T1"}', "K1", "or6valR+VpzGkhLAL7VdtQ=="),
    ('{"a": 1}', "K1", "8p+hFUxoVI7krhcHEsxXuQ=="),
    ('{"a": 1}', "K2", "5ssVUPK9SnwVyBquiQaG3A=="),
    ('bizContent-JSON', "KHOA-THU-KY", "9JF//h1VnUXFVQ3jeWrTMQ=="),
]

DON_MAU = {
    "ma_don": "G16-QA-1", "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Thử",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
    "hang_hoa": "Áo thử", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
    "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa",
}

CRED_THU = {"apiAccount": "669", "privateKey": CANARY_DUOI + "-PK",
            "customerCode": "CC-THU", "password": CANARY_DUOI + "-PW"}


def ad_mock(cred=None):
    return adapter.tao_adapter("jt", dict(cred or CRED_THU), "mock")


@contextlib.contextmanager
def _cho_phep_live_tam():
    """Mở TẠM `CHO_PHEP_LIVE` của lớp adapter để chạm được các ổ khoá SÂU HƠN.

    Không có nó thì ổ khoá đầu (`__init__`) chặn trước mọi thứ, và không đo được rằng các ổ
    khoá sau vẫn độc lập. `finally` để không rò trạng thái sang ca khác.
    """
    cu = aj.AdapterJT.CHO_PHEP_LIVE
    aj.AdapterJT.CHO_PHEP_LIVE = True
    try:
        yield
    finally:
        aj.AdapterJT.CHO_PHEP_LIVE = cu


# ══════════════════════════════════════════════════════════════════════════════════════════════
# STUB CỤC BỘ — chỉ `127.0.0.1`, cổng do hệ điều hành cấp (0). Không bind ra ngoài.
# ══════════════════════════════════════════════════════════════════════════════════════════════
class _ChanKetNoi(Exception):
    """Sentinel: 'có ai đó ĐỊNH mở socket'. Không bao giờ để nó ra ngoài bộ thử."""


@contextlib.contextmanager
def dem_ket_noi(chan_that=True):
    """Đếm số lần `http.client` ĐỊNH nối. `chan_that=True` ⇒ chặn luôn, không chạm mạng thật."""
    dem = {"n": 0}
    goc_h = http.client.HTTPConnection.connect
    goc_s = http.client.HTTPSConnection.connect

    def _boc(goc):
        def _connect(self):
            dem["n"] += 1
            if chan_that:
                raise _ChanKetNoi(f"CHẶN TRONG BỘ THỬ: định nối {self.host}:{self.port}")
            return goc(self)
        return _connect

    http.client.HTTPConnection.connect = _boc(goc_h)
    http.client.HTTPSConnection.connect = _boc(goc_s)
    try:
        yield dem
    finally:
        http.client.HTTPConnection.connect = goc_h
        http.client.HTTPSConnection.connect = goc_s


class StubJt:
    """Máy chủ thử CỤC BỘ. Bind `127.0.0.1` cổng 0. Ghi lại MỌI yêu cầu nhận được."""

    def __init__(self):
        self.yeu_cau = []
        self.dem_theo_duong = {}
        self.srv = None
        self.cong = None
        self.host_bind = None

    def _tra_loi(self, h, ma, than=b"", headers=()):
        try:
            h.send_response(ma)
            for k, v in headers:
                h.send_header(k, v)
            h.send_header("Content-Length", str(len(than)))
            h.end_headers()
            if than:
                h.wfile.write(than)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _chay(self):
        stub = self

        class H(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def handle(self):
                try:
                    super().handle()
                except (ConnectionResetError, BrokenPipeError):
                    pass

            def _tra_loi(self, *a, **kw):
                self.close_connection = True     # không giữ kết nối ⇒ không đọc lại trên socket đã đóng
                return stub._tra_loi(self, *a, **kw)

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                than = self.rfile.read(n) if n else b""
                duong = self.path.split("?")[0]
                stub.dem_theo_duong[duong] = stub.dem_theo_duong.get(duong, 0) + 1
                stub.yeu_cau.append({
                    "duong": duong, "than": than,
                    "content_type": self.headers.get("Content-Type"),
                    "headers": dict(self.headers.items()),
                })
                if duong == "/ok":
                    return stub._tra_loi(self, 200, b'{"code":"1","data":{"billCode":"OK1"}}')
                if duong == "/500":
                    return stub._tra_loi(self, 500, b"loi phia hang")
                if duong == "/503":
                    return stub._tra_loi(self, 503, b"loi phia hang")
                if duong == "/400":
                    return stub._tra_loi(self, 400, b"tham so sai")
                if duong == "/401":
                    return stub._tra_loi(self, 401, b"xac thuc hong")
                if duong == "/404":
                    return stub._tra_loi(self, 404, b"khong thay")
                if duong == "/302":
                    return stub._tra_loi(self, 302, b"", [("Location", "http://evil.example/")])
                if duong == "/403":
                    return stub._tra_loi(self, 403, b"khong co quyen")
                if duong in ("/408", "/429", "/429-ra", "/429-ra-to"):
                    # `Retry-After` lấy từ QUERY để một route phục vụ nhiều mức.
                    ra = None
                    if "?" in self.path:
                        for k, v in parse_qsl(self.path.split("?", 1)[1], keep_blank_values=True):
                            if k == "ra":
                                ra = v
                    hdr = [("Retry-After", ra)] if ra else []
                    return stub._tra_loi(self, int(duong[1:4]), b"hang bao cho", hdr)
                if duong == "/bytes":
                    # Byte KHÔNG phải UTF-8 + CRLF: thân phải về NGUYÊN VĂN.
                    return stub._tra_loi(self, 200, b"\xff\xfe\r\n\x00binary\x80")
                if duong == "/slow":
                    time.sleep(3.0)
                    return stub._tra_loi(self, 200, b'{"code":"1"}')
                if duong == "/fail-once":
                    if stub.dem_theo_duong[duong] == 1:
                        return stub._tra_loi(self, 500, b"lan dau hong")
                    return stub._tra_loi(self, 200, b'{"code":"1"}')
                if duong == "/echo":
                    return stub._tra_loi(self, 400, b"ECHO: " + than)
                if duong == "/echo-header":
                    # Hãng ECHO LẠI một header ta đã gửi — nguyên văn, KHÔNG percent-encode.
                    gt = (self.headers.get("apiAccount") or "").encode("utf-8", "replace")
                    return stub._tra_loi(self, 400, b"ECHO-HEADER: apiAccount=" + gt)
                return stub._tra_loi(self, 404, b"khong thay")

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.srv.daemon_threads = True
        self.host_bind = self.srv.server_address[0]
        self.cong = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return self

    def url(self, duong):
        return f"http://127.0.0.1:{self.cong}{duong}"

    def dung(self):
        if self.srv:
            self.srv.shutdown()
            self.srv.server_close()


@contextlib.contextmanager
def stub():
    s = StubJt()._chay()
    try:
        yield s
    finally:
        s.dung()


# ══════════════════════════════════════════════════════════════════════════════════════════════
class A_Nen(unittest.TestCase):
    """Cổng nền F0 — áp cho MỌI mục. Vi phạm ở đây thì mọi số đo sau đều vô hiệu."""

    def test_a1_khong_hang_nao_mo_live(self):
        """Vòng lặp ĐỘNG trên sổ đăng ký lớp — không đọc hằng viết cứng, không bỏ sót lớp mới."""
        dang_ky = adapter._DANG_KY
        self.assertTrue(dang_ky, "sổ đăng ký lớp RỖNG — phép kiểm này không đo gì")
        for ma, lop in dang_ky.items():
            with self.subTest(hang=ma):
                self.assertIs(getattr(lop, "CHO_PHEP_LIVE", None), False,
                              f"hãng {ma}: CHO_PHEP_LIVE không phải False ⇒ CRITICAL, CHẶN NGAY")
        ds = adapter.danh_sach_hang()
        self.assertEqual(set(ds), set(dang_ky))
        for ma, tt in ds.items():
            with self.subTest(hang=ma, nguon="danh_sach_hang"):
                self.assertIs(tt["live_mo"], False,
                              f"hãng {ma}: đang MỞ live ⇒ CRITICAL, CHẶN NGAY")

    def test_a2_cong_moi_truong_jt_dong(self):
        self.assertIs(cau_hinh.JT_CHO_PHEP_SANDBOX, False)
        self.assertIs(cau_hinh.JT_CHO_PHEP_PRODUCTION, False)
        # `moi_truong=None` KHÔNG phải "môi trường lạ" — nó nghĩa là "dùng mặc định đã cấu hình".
        # Nên ca này kiểm mặc định đó TRƯỚC, rồi mới kiểm các giá trị lạ.
        self.assertEqual(cau_hinh.JT_MOI_TRUONG, "mock", "MẶC ĐỊNH phải là mock (§37)")
        self.assertTrue(cau_hinh.jt_kiem_moi_truong(None)[0])
        for mt in ("sandbox", "production", "", "bịa"):
            with self.subTest(moi_truong=mt):
                cho_qua, ly_do = cau_hinh.jt_kiem_moi_truong(mt)
                self.assertFalse(cho_qua, f"môi trường {mt!r} phải bị CHẶN")
                self.assertTrue(str(ly_do).strip(), "từ chối phải kèm lý do ĐỌC ĐƯỢC")
        cho_qua, _ = cau_hinh.jt_kiem_moi_truong("mock")
        self.assertTrue(cho_qua, "mock phải MỞ — đây là đối chứng dương của cổng này")

    def test_a3_adapter_chan_sandbox_truoc_khi_cham_mang(self):
        """HAI ổ khoá độc lập, cả hai phải 0 socket — và phải nổ KÈM LÝ DO ĐỌC ĐƯỢC."""
        _dc_am("a3")
        with dem_ket_noi(chan_that=True) as dem:
            with self.assertRaises(PermissionError):
                adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
        self.assertEqual(dem["n"], 0, "dựng adapter sandbox đã ĐỊNH mở socket ⇒ CRITICAL")

        # Ổ KHOÁ SÂU HƠN: mở tạm `CHO_PHEP_LIVE` (đúng cách `thu_hop_dong_jt` làm) để chạm tới
        # cửa môi trường. Trên đường `createOrder`, chốt D-9 nổ TRƯỚC cửa môi trường (D-9 nằm ở
        # chỗ DỰNG bizContent), nên cả hai loại ngoại lệ đều là "đã chặn". Điều bắt buộc là
        # KHÔNG một socket nào được mở.
        with _cho_phep_live_tam(), dem_ket_noi(chan_that=True) as dem2:
            ad = adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
            with self.assertRaises((PermissionError, loi_hang.NormalizedCarrierError)):
                ad.createOrder(dict(DON_MAU))
        self.assertEqual(dem2["n"], 0,
                         "mở CHO_PHEP_LIVE mà sandbox đã ĐỊNH gọi mạng ⇒ CRITICAL")

        # CỬA MÔI TRƯỜNG ĐO RIÊNG, đúng chỗ nó nằm — cửa này PHẢI là `PermissionError` kèm lý do.
        with _cho_phep_live_tam():
            ad2 = adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
            with self.assertRaises(PermissionError) as e:
                ad2._chuan_bi_goi_that("trackOrder")
        self.assertIn("TỪ CHỐI", str(e.exception))
        self.assertGreater(len(str(e.exception)), 60, "lý do từ chối phải ĐỌC ĐƯỢC")

        # ĐỐI CHỨNG DƯƠNG: cùng hàm, môi trường `mock` ⇒ đi qua bình thường, vẫn 0 socket.
        with dem_ket_noi(chan_that=True) as dem3:
            kq = ad_mock().createOrder(dict(DON_MAU))
        self.assertTrue(kq.ok, f"mock phải tạo được đơn, nhận {kq.loi and kq.loi.ma_chuan}")
        self.assertEqual(dem3["n"], 0, "mock KHÔNG được chạm mạng")
        _dc_duong("a3")


# ══════════════════════════════════════════════════════════════════════════════════════════════
class E_TuKiemBoDo(unittest.TestCase):
    """CHỐT CHẶN 1 (§6.3): bộ dò phải TỰ CHỨNG MINH nó thấy được cái nó cần thấy."""

    MA_HONG = (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_hong(self):\n"
        "        self.assertEqual(1, 2, 'co y hong')\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n"
    )
    MA_DAT = (
        "import unittest\n"
        "class T(unittest.TestCase):\n"
        "    def test_dat(self):\n"
        "        self.assertEqual(1, 1)\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n"
    )

    def _chay(self, nguon):
        d = tempfile.mkdtemp(prefix="vip-hub-g16-tk-")
        p = os.path.join(d, "thu_tu_kiem.py")
        with io.open(p, "w", encoding="utf-8") as f:
            f.write(nguon)
        r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=60)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    @staticmethod
    def phan_quyet(ma_thoát, out):
        """Bản sao LUẬT PHÁN QUYẾT của `app/thu/chay_tat_ca.sh`: mã thoát + dấu vết + số ca > 0.

        Chép ra đây để ca tự kiểm đo được CHÍNH LUẬT đang dùng, không đo cảm giác.
        """
        n = 0
        m = re.findall(r"Ran (\d+)", out or "")
        if m:
            n = int(m[-1])
        co_dau_vet = bool(re.search(r"(?m)^OK( |$)|ca — ĐẠT", out or ""))
        if ma_thoát == 0 and co_dau_vet and n > 0:
            return "ĐẠT", n
        if ma_thoát == 0 and n == 0 and "skipped" in (out or ""):
            return "BỎ QUA", n
        return "HỎNG", n

    def test_e1_ca_co_y_hong_thi_bo_do_THAY(self):
        ma, out = self._chay(self.MA_HONG)
        self.assertNotEqual(ma, 0, "ca cố ý hỏng mà tiến trình con thoát 0 ⇒ bộ dò MÙ")
        phan, n = self.phan_quyet(ma, out)
        self.assertEqual(phan, "HỎNG", f"luật phán quyết không thấy ca hỏng (mã {ma}, {n} ca)")

    def test_e2_doi_chung_duong_ca_dat_thi_thay_DAT(self):
        ma, out = self._chay(self.MA_DAT)
        self.assertEqual(ma, 0)
        phan, n = self.phan_quyet(ma, out)
        self.assertEqual(phan, "ĐẠT", f"ca đạt bị phán {phan} (mã {ma}, {n} ca)")
        self.assertEqual(n, 1)

    def test_e3_doi_chung_duong_phan_biet_duoc_hai_chieu(self):
        ma_h, out_h = self._chay(self.MA_HONG)
        ma_d, out_d = self._chay(self.MA_DAT)
        self.assertNotEqual(self.phan_quyet(ma_h, out_h)[0], self.phan_quyet(ma_d, out_d)[0],
                            "bộ dò phán HAI trường hợp khác nhau GIỐNG nhau ⇒ vô giá trị")

    def test_e4_dong_pham_vi_noi_THANG_khi_thieu_lop_http(self):
        """Không được để nhóm transport biến mất IM LẶNG (bài học `thu_postgres.py`)."""
        co = _dong_pham_vi(True)
        khong = _dong_pham_vi(False)
        self.assertIn("BỎ QUA", khong.upper())
        self.assertNotIn("BỎ QUA", co.upper())
        self.assertIn("TRANSPORT", khong.upper())

    @unittest.skipUnless(CO_HTTP_JT, "cần app/http_jt.py để đột biến chính nó")
    def test_e5_DOT_BIEN_pha_danh_sach_trang_thi_bo_do_PHAI_do(self):
        """ĐỘT BIẾN: phá danh sách trắng trong một BẢN SAO rồi chạy lại đúng ca canh nó.

        Nếu ca canh vẫn xanh trên bản đã bị phá thì nó KHÔNG chứng minh gì — đó là toàn bộ lý do
        ca này tồn tại (§12.1 luật 1). Bản sao nằm ở `/tmp`, KHÔNG đụng tệp thật của AG-02.
        """
        goc = io.open(os.path.join(GOC_APP, "http_jt.py"), encoding="utf-8").read()
        kim = "    return h in HOST_HANG or h in HOST_CUC_BO"
        self.assertIn(kim, goc, "không tìm thấy dòng danh sách trắng để đột biến — đo lại kim")
        d = tempfile.mkdtemp(prefix="vip-hub-g16-db-")
        p_mut = os.path.join(d, "http_jt.py")
        io.open(p_mut, "w", encoding="utf-8").write(goc.replace(kim, "    return True"))

        ma = (
            "import importlib.util, os, sys, unittest\n"
            "WORK = %r\n"
            "sys.path.insert(0, os.path.join(WORK, 'app'))\n"
            "spec = importlib.util.spec_from_file_location('http_jt', %r)\n"
            "m = importlib.util.module_from_spec(spec)\n"
            "sys.modules['http_jt'] = m\n"
            "spec.loader.exec_module(m)\n"
            "assert m.host_duoc_phep('evil.example') is True, 'dot bien khong co tac dung'\n"
            "sys.path.insert(0, os.path.join(WORK, 'app', 'thu'))\n"
            "import thu_qa_g16 as q\n"
            "ten = ['T_Transport.test_t4_host_ngoai_bi_tu_choi_khong_mo_socket',\n"
            "       'T_Transport.test_t5_host_hau_to_bi_tu_choi',\n"
            "       'T_Transport.test_t7_host_hang_gia_tien_to_bi_tu_choi']\n"
            "r = unittest.TextTestRunner(verbosity=0).run(\n"
            "    unittest.TestSuite([unittest.TestLoader().loadTestsFromName(t, q) for t in ten]))\n"
            "sys.exit(0 if r.wasSuccessful() else 1)\n" % (GOC_CAY, p_mut))
        p_drv = os.path.join(d, "chay_dot_bien.py")
        io.open(p_drv, "w", encoding="utf-8").write(ma)
        r = subprocess.run([sys.executable, p_drv], capture_output=True, text=True, timeout=180,
                           env=dict(os.environ, VIP_HUB_DATA=os.path.join(d, "data")))
        self.assertNotEqual(r.returncode, 0,
                            "ĐỘT BIẾN phá danh sách trắng mà bộ dò VẪN XANH ⇒ bộ dò vô giá trị\n"
                            + (r.stdout or "")[-1200:] + (r.stderr or "")[-1200:])
        self.assertIn("Ran 3 tests", (r.stderr or "") + (r.stdout or ""),
                      "tiến trình đột biến không chạy đủ 3 ca ⇒ phép đo không chạm gì")


def _dong_pham_vi(co_http):
    """Dòng phạm vi in cuối lượt. Hàm THUẦN để ca e4 đo được mà không cần chạy tiến trình con."""
    if co_http:
        return "PHẠM VI G16-A: 3/3 nhóm ĐÃ ĐO (transport · credentials · hợp đồng)"
    return ("PHẠM VI G16-A: 2/3 nhóm đã đo — nhóm TRANSPORT **BỎ QUA** "
            "(không nạp được `app/http_jt.py`) ⇒ CỔNG G16-A/1 CHƯA ĐO, KHÔNG được coi là ĐẠT")


# ══════════════════════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(CO_HTTP_JT, "chưa có app/http_jt.py — nhóm TRANSPORT BỎ QUA (xem Z_TongKet)")
class T_Transport(unittest.TestCase):
    """G16-A/1 — HTTP TRANSPORT. Đo trên lớp HTTP THẬT, stub cục bộ `127.0.0.1:0`."""

    # ── T1/T2: transport THẬT + stub chỉ vòng lặp nội bộ ───────────────────────────────────────
    def test_t1_gui_POST_that_tren_vong_lap_noi_bo(self):
        with stub() as s, dem_ket_noi(chan_that=False) as dem:
            r = http_jt.gui_form(s.url("/ok"), {"apiAccount": "669"}, {"bizContent": "{}"},
                                 timeout=5)
        self.assertIsInstance(r, http_jt.TraLoiHTTP)
        self.assertEqual(r.ma_http, 200)
        self.assertEqual(dem["n"], 1, "phải có ĐÚNG một lượt nối")
        self.assertEqual(len(s.yeu_cau), 1, "stub phải nhận ĐÚNG một yêu cầu")
        yc = s.yeu_cau[0]
        self.assertEqual(yc["content_type"], "application/x-www-form-urlencoded")
        self.assertEqual(yc["than"], b"bizContent=%7B%7D", "thân form phải đúng nguyên văn")
        self.assertEqual(json.loads(r.than.decode()), {"code": "1", "data": {"billCode": "OK1"}})

    def test_t2_stub_chi_bind_vong_lap_noi_bo(self):
        with stub() as s:
            self.assertEqual(s.host_bind, "127.0.0.1",
                             "stub bind ra ngoài vòng lặp nội bộ ⇒ CRITICAL")
            # ĐỐI CHỨNG DƯƠNG: từ 127.0.0.1 thì nối được.
            k = socket.create_connection(("127.0.0.1", s.cong), timeout=2)
            k.close()
        # ĐỐI CHỨNG ÂM: từ một địa chỉ KHÔNG-loopback của máy thì KHÔNG nối được.
        ip_ngoai = _ip_khong_vong_lap()
        if ip_ngoai is None:
            self.skipTest("máy không có địa chỉ IPv4 không-loopback để thử chiều âm")
        with stub() as s2:
            with self.assertRaises(OSError):
                socket.create_connection((ip_ngoai, s2.cong), timeout=2)

    # ── T3..T12: DANH SÁCH TRẮNG ───────────────────────────────────────────────────────────────
    def test_t3_doi_chung_duong_loopback_duoc_phep_va_CO_qua_cong_chan(self):
        """Không có ca này thì mọi ca T4–T12 xanh một cách vô nghĩa (tầng chết hẳn cũng xanh)."""
        with stub() as s, dem_ket_noi(chan_that=False) as dem:
            r = http_jt.gui_form(s.url("/ok"), {}, {"bizContent": "{}"}, timeout=5)
        self.assertEqual(r.ma_http, 200)
        self.assertGreaterEqual(dem["n"], 1, "loopback phải ĐI QUA cổng danh sách trắng")
        _dc_duong("danh-sach-trang")

    def test_t4_host_ngoai_bi_tu_choi_khong_mo_socket(self):
        self._khang_dinh_tu_choi("http://evil.example/api")

    def test_t5_host_hau_to_bi_tu_choi(self):
        self._khang_dinh_tu_choi("http://127.0.0.1.evil.example/api")

    def test_t6_userinfo_trong_url_bi_tu_choi(self):
        self._khang_dinh_tu_choi("http://127.0.0.1@evil.example/api")

    def test_t7_host_hang_gia_tien_to_bi_tu_choi(self):
        self._khang_dinh_tu_choi("https://demoopenapi.jtexpress.vn.evil.example/api")

    def test_t8_host_trong_query_khong_cuu_duoc(self):
        self._khang_dinh_tu_choi("http://evil.example/api?u=http://127.0.0.1/")

    def test_t9_ip_viet_kieu_khac_bi_tu_choi(self):
        for url in ("http://2130706433/api", "http://0.0.0.0/api", "http://127.1/api"):
            with self.subTest(url=url):
                self._khang_dinh_tu_choi(url)

    def test_t10_giao_thuc_la_bi_tu_choi(self):
        for url in ("file:///etc/passwd", "ftp://127.0.0.1/api", "gopher://127.0.0.1/"):
            with self.subTest(url=url):
                self._khang_dinh_tu_choi(url)

    def test_t11_chuyen_huong_KHONG_duoc_di_theo(self):
        with stub() as s, dem_ket_noi(chan_that=False):
            with self.assertRaises(transport.LoiVinhVien) as e:
                http_jt.gui_form(s.url("/302"), {}, {"bizContent": "{}"}, timeout=5)
        self.assertEqual(getattr(e.exception, "ma_http", None), 302)
        self.assertEqual(getattr(e.exception, "ket_cuc", None), http_jt.KET_CUC_HANG_TU_CHOI)
        _dc_am("danh-sach-trang")

    def test_t12_chu_hoa_trong_url_bi_tu_choi(self):
        self._khang_dinh_tu_choi("HTTP://EVIL.EXAMPLE/api")

    def test_t12b_host_hang_that_DI_QUA_cong_danh_sach_trang(self):
        """ĐỐI CHỨNG DƯƠNG cho hai host J&T — đo MÀ KHÔNG gửi một byte nào ra ngoài.

        Ngoại lệ của bộ đếm là loại LẠ với `http_jt`, nên nó bị ánh xạ thành `LoiVinhVien`
        (an toàn cho thao tác ghi). Điều ta khẳng định ở đây là **số lần ĐỊNH nối = 1** —
        tức host ĐÃ qua được cổng danh sách trắng rồi mới bị bộ đếm chặn.
        """
        for host in (http_jt.HOST_HANG_SANDBOX, http_jt.HOST_HANG_PRODUCTION):
            with self.subTest(host=host):
                with dem_ket_noi(chan_that=True) as dem:
                    try:
                        http_jt.gui_form(f"https://{host}/api/order/createOrder", {},
                                         {"bizContent": "{}"}, timeout=1)
                    except (transport.LoiVinhVien, transport.LoiTamThoi, _ChanKetNoi) as e:
                        self.assertIn("CHẶN TRONG BỘ THỬ", str(e))
                    else:
                        self.fail("bộ đếm không chặn được ⇒ phép đo này vô hiệu")
                self.assertEqual(dem["n"], 1,
                                 f"{host} phải QUA cổng danh sách trắng rồi mới bị bộ đếm chặn")
        _dc_duong("danh-sach-trang")

    def test_t12c_host_hang_buoc_phai_https_cong_443(self):
        for url in ("http://demoopenapi.jtexpress.vn/api", "https://demoopenapi.jtexpress.vn:8443/api"):
            with self.subTest(url=url):
                with dem_ket_noi(chan_that=True) as dem:
                    with self.assertRaises(transport.LoiVinhVien):
                        http_jt.gui_form(url, {}, {"bizContent": "{}"}, timeout=1)
                self.assertEqual(dem["n"], 0)

    def _khang_dinh_tu_choi(self, url):
        """Ca ÂM: host phải bị từ chối VÀ bộ đếm nối phải bằng 0 (chưa hề mở socket)."""
        _dc_am("danh-sach-trang")
        with dem_ket_noi(chan_that=True) as dem:
            with self.assertRaises(transport.LoiVinhVien) as e:
                http_jt.gui_form(url, {}, {"bizContent": "{}"}, timeout=5)
        self.assertEqual(dem["n"], 0,
                         f"{url} ĐÃ ĐỊNH mở socket ⇒ danh sách trắng bị vòng qua ⇒ CRITICAL")
        self.assertEqual(getattr(e.exception, "ket_cuc", None), http_jt.KET_CUC_KHONG_GUI_DI)

    # ── T13: HẾT GIỜ ──────────────────────────────────────────────────────────────────────────
    def test_t13_het_gio_that_su_huy_luot_goi(self):
        with stub() as s, dem_ket_noi(chan_that=False):
            t0 = time.monotonic()
            with self.assertRaises(transport.LoiTamThoi) as e:
                http_jt.gui_form(s.url("/slow"), {}, {"bizContent": "{}"}, timeout=0.5)
            mat = time.monotonic() - t0
        self.assertLess(mat, 2.0, f"hết giờ 0,5 s nhưng ngồi chờ {mat:.2f} s ⇒ KHÔNG huy được")
        self.assertEqual(getattr(e.exception, "timeout", None), True)
        self.assertEqual(getattr(e.exception, "loai", None), "het-gio")
        self.assertEqual(getattr(e.exception, "ket_cuc", None), http_jt.KET_CUC_KHONG_BIET)
        _dc_am("het-gio")
        # ĐỐI CHỨNG DƯƠNG: cùng stub, hạn đủ rộng ⇒ 200.
        with stub() as s2, dem_ket_noi(chan_that=False):
            r = http_jt.gui_form(s2.url("/slow"), {}, {"bizContent": "{}"}, timeout=8)
        self.assertEqual(r.ma_http, 200)
        _dc_duong("het-gio")

    def test_t13b_het_gio_khong_ro_ri_thanh_cong(self):
        """Kết cục thứ ba KHÔNG BAO GIỜ được trả về dưới dạng `TraLoiHTTP`."""
        with stub() as s, dem_ket_noi(chan_that=False):
            try:
                r = http_jt.gui_form(s.url("/slow"), {}, {"bizContent": "{}"}, timeout=0.5)
            except transport.LoiTamThoi:
                r = None
        self.assertIsNone(r, "hết giờ mà vẫn trả về một đối tượng phản hồi")

    # ── T14/T15: 5xx → tạm thời · 4xx → vĩnh viễn ─────────────────────────────────────────────
    def test_t14_5xx_la_tam_thoi(self):
        for duong in ("/500", "/503"):
            with self.subTest(duong=duong), stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiTamThoi) as e:
                    http_jt.gui_form(s.url(duong), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(getattr(e.exception, "timeout", None), True)
            self.assertEqual(getattr(e.exception, "ket_cuc", None), http_jt.KET_CUC_KHONG_BIET)
        _dc_am("ma-http")
        with stub() as s, dem_ket_noi(chan_that=False):
            r = http_jt.gui_form(s.url("/ok"), {}, {"bizContent": "{}"}, timeout=5)
        self.assertEqual(r.ma_http, 200)
        _dc_duong("ma-http")

    def test_t15_4xx_la_vinh_vien(self):
        for duong, ma in (("/400", 400), ("/401", 401), ("/404", 404)):
            with self.subTest(duong=duong), stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiVinhVien) as e:
                    http_jt.gui_form(s.url(duong), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(getattr(e.exception, "ma_http", None), ma)
            self.assertEqual(getattr(e.exception, "timeout", None), False)
        _dc_am("ma-http")

    # ── T16/T17: KHÔNG TỰ THỬ LẠI ─────────────────────────────────────────────────────────────
    def test_t16_mot_luot_goi_gui_DUNG_mot_yeu_cau(self):
        """Kể cả khi hãng trả 5xx (đáng thử lại), `gui_form` KHÔNG được gửi lần thứ hai."""
        with stub() as s, dem_ket_noi(chan_that=False):
            for _ in range(1):
                with self.assertRaises(transport.LoiTamThoi):
                    http_jt.gui_form(s.url("/fail-once"), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(s.dem_theo_duong.get("/fail-once"), 1,
                             "gui_form ĐÃ tự thử lại ⇒ vi phạm §36 luật 1")
            _dc_am("khong-tu-thu-lai")
            # ĐỐI CHỨNG DƯƠNG: gọi lần hai (do NGƯỜI GỌI quyết định) thì có yêu cầu thứ hai.
            r = http_jt.gui_form(s.url("/fail-once"), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(r.ma_http, 200)
            self.assertEqual(s.dem_theo_duong.get("/fail-once"), 2)
            _dc_duong("khong-tu-thu-lai")

    def test_t17a_chinh_sach_thao_tac_GHI_khong_thu_lai_mac_dinh(self):
        for tt in ("createOrder", "cancelOrder"):
            with self.subTest(thao_tac=tt):
                cs = transport.chinh_sach_cho(tt)
                self.assertIs(cs.duoc_thu_lai, False, f"{tt} mặc định KHÔNG được thử lại")
                self.assertEqual(cs.so_lan, 1)
        _dc_am("khong-tu-thu-lai")
        cs = transport.chinh_sach_cho("getOrder")
        self.assertIs(cs.duoc_thu_lai, True)
        self.assertEqual(cs.so_lan, 3)
        _dc_duong("khong-tu-thu-lai")

    def test_t17b_mo_thu_lai_thao_tac_GHI_chi_khi_co_khoa_chong_trung(self):
        cs = transport.chinh_sach_cho("createOrder", co_khoa_chong_trung=True)
        self.assertIs(cs.duoc_thu_lai, True)
        self.assertEqual(cs.so_lan, 3)
        cs2 = transport.chinh_sach_cho("cancelOrder", co_khoa_chong_trung=True)
        self.assertIs(cs2.duoc_thu_lai, True)

    def test_t17c_khoa_chong_trung_co_THAT_trong_than_gui_di(self):
        """`KHOA_CHONG_TRUNG=True` chỉ AN TOÀN nếu khoá đó thật sự có trong thân sẽ gửi lại.

        Nếu cờ bật mà `txlogisticId` không nằm trong `bizContent`, thì lượt thử lại thứ hai
        gửi một yêu cầu KHÔNG có khoá chống trùng ⇒ hãng tạo ĐƠN THỨ HAI. Đây là phép kiểm
        chạm đúng chỗ nguy hiểm, không chỉ đọc cờ.
        """
        self.assertIs(aj.AdapterJT.KHOA_CHONG_TRUNG, True,
                      "cờ chống trùng phải khớp thực tế tài liệu J&T")
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        biz = json.loads(yc["bizContent"])
        self.assertIn("txlogisticId", biz, "thiếu khoá chống trùng ⇒ thử lại createOrder là NGUY HIỂM")
        self.assertTrue(str(biz["txlogisticId"]).strip())
        _dc_duong("khong-tu-thu-lai")

    def test_t17d_goi_that_khong_tu_thu_lai_qua_transport(self):
        """Đo ở TẦNG adapter, trên ĐƯỜNG GỬI THẬT: `_goi_that` phải tôn trọng chính sách.

        Gọi thẳng `_goi_that` với một yêu cầu ĐÃ DỰNG: đi vòng qua chốt D-9 (chốt đó canh chỗ
        DỰNG `bizContent`, và nó PHẢI còn nổ — ca h7 canh việc đó). Ở đây ta đo đúng một điều:
        một lượt `createOrder` gửi bao nhiêu yêu cầu, và có đi qua `transport.goi` không.
        """
        _dc_am("khong-tu-thu-lai")
        with stub() as s, dem_ket_noi(chan_that=False), _cho_phep_live_tam():
            ad = adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
            yc = {"url": s.url("/ok"), "headers": {"apiAccount": "669"},
                  "body": {"bizContent": "{}"}}
            kq = ad._goi_that(http_jt, "createOrder", yc)
            so_ok = sum(s.dem_theo_duong.values())
        self.assertTrue(kq.ok, f"lượt gửi thật phải thành công: {kq.loi and kq.loi.ma_chuan}")
        self.assertEqual(so_ok, 1, f"một lượt createOrder gửi {so_ok} yêu cầu cho một phản hồi 200")
        self.assertIn("so_lan_goi", kq.tho, "kết quả phải tự khai số lần gọi")

        # ĐỐI CHỨNG DƯƠNG + ÂM: hãng trả 500 ⇒ KHÔNG BIẾT kết quả, và số lượt phải ĐÚNG bằng
        # `so_lan` của chính sách đang áp cho createOrder (có khoá chống trùng ⇒ tối đa 3).
        with stub() as s2, dem_ket_noi(chan_that=False), _cho_phep_live_tam():
            ad2 = adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
            cs = transport.chinh_sach_cho("createOrder", co_khoa_chong_trung=bool(ad2.KHOA_CHONG_TRUNG))
            yc2 = {"url": s2.url("/500"), "headers": {}, "body": {"bizContent": "{}"}}
            kq2 = ad2._goi_that(http_jt, "createOrder", yc2)
            so_hong = sum(s2.dem_theo_duong.values())
        self.assertFalse(kq2.ok)
        self.assertIs(kq2.timeout, True, "5xx ⇒ KHÔNG BIẾT kết quả, không bao giờ là ok")
        self.assertLessEqual(so_hong, cs.so_lan, "gửi nhiều hơn trần chính sách")
        self.assertGreaterEqual(so_hong, 1, "không có yêu cầu nào tới stub ⇒ phép đo không chạm gì")
        _dc_duong("khong-tu-thu-lai")

    # ── T18: RÒ BÍ MẬT ────────────────────────────────────────────────────────────────────────
    def test_t18a_khong_ro_canary_DUOI_vao_ngoai_le(self):
        """Ép BỐN đường lỗi; canary DÀI không được xuất hiện ở BẤT KỲ đâu đọc được."""
        _dc_am("ro-bi-mat")
        canary = CANARY_DUOI
        than = json.dumps({"customerCode": canary + "-CC", "password": canary + "-PW"}).encode()
        headers = {"apiAccount": canary + "-ACC", "digest": canary + "-DIG"}

        ghi_log = io.StringIO()
        handler = logging.StreamHandler(ghi_log)
        logging.getLogger().addHandler(handler)
        try:
            with stub() as s:
                duong_loi = [(s.url("/echo"), "echo-4xx"), (s.url("/500"), "5xx")]
                for url, nhan in duong_loi:
                    with self.subTest(duong=nhan):
                        try:
                            http_jt.gui_form(url, dict(headers),
                                             {"bizContent": than.decode()}, timeout=5)
                            self.fail("phải ném")
                        except (transport.LoiTamThoi, transport.LoiVinhVien) as e:
                            self._khang_dinh_sach(e, canary, nhan)
                with stub() as s2:
                    try:
                        http_jt.gui_form(s2.url("/slow"), dict(headers),
                                         {"bizContent": than.decode()}, timeout=0.5)
                        self.fail("phải ném")
                    except transport.LoiTamThoi as e:
                        self._khang_dinh_sach(e, canary, "het-gio")
            with dem_ket_noi(chan_that=True):
                try:
                    http_jt.gui_form("http://evil.example/x", dict(headers),
                                     {"bizContent": than.decode()}, timeout=5)
                    self.fail("phải ném")
                except transport.LoiVinhVien as e:
                    self._khang_dinh_sach(e, canary, "host-bi-tu-choi")
        finally:
            logging.getLogger().removeHandler(handler)
        self.assertNotIn(canary, ghi_log.getvalue(), "canary lọt vào logging")
        _dc_duong("ro-bi-mat")   # đối chứng dương: chính bộ dò phải TÌM THẤY canary khi có thật
        self.assertIn(canary, "tiền tố " + canary + " hậu tố",
                      "bộ dò chuỗi của chính ca này hỏng ⇒ ca âm ở trên vô nghĩa")

    def _khang_dinh_sach(self, e, canary, nhan):
        for nhan_nguon, chuoi in (("str", str(e)), ("repr", repr(e)),
                                  ("args", repr(getattr(e, "args", ()))),
                                  ("traceback", traceback.format_exc())):
            self.assertNotIn(canary, chuoi,
                             f"[{nhan}] canary rò qua {nhan_nguon} ⇒ CRITICAL")
        for ten in ("than_da_che", "headers_da_che", "mo_ta_yeu_cau"):
            if hasattr(e, ten):
                self.assertNotIn(canary, repr(getattr(e, ten)),
                                 f"[{nhan}] canary rò qua thuộc tính {ten} ⇒ CRITICAL")

    def test_t18b_truong_CREDENTIAL_bi_che_BAT_KE_do_dai(self):
        """CỔNG CHẶN: giá trị của trường CREDENTIAL phải bị che BẤT KỂ ĐỘ DÀI.

        Lịch sử của ca này (giữ lại vì nó là bằng chứng cổng đang làm việc): bản `http_jt.py` lúc
        `15:48` chỉ che theo NGƯỠNG ĐỘ DÀI (8 ký tự). AG-01 đo được: một `apiAccount`/`password`
        **5 ký tự** bị hãng echo lại trong thân 4xx thì **LỘ NGUYÊN VĂN** vào thông điệp ngoại lệ
        (`rò qua HEADER = True`). Bản `1c862635` vá đúng cách: che theo **TÊN TRƯỜNG**
        (`TRUONG_CREDENTIAL`) không ngưỡng, ngưỡng chỉ còn dùng cho giá trị KHÔNG tên.
        Ca này khẳng định bất biến ĐÓ, nên nếu ai quay lại cách cũ thì nó ĐỎ.
        """
        ngan = CANARY_NGAN
        nguong = getattr(http_jt, "DAI_TOI_THIEU_DE_CHE", None)
        truong = tuple(getattr(http_jt, "TRUONG_CREDENTIAL", ()) or ())
        self.assertLess(len(ngan), nguong, "canary đo phải NGẮN hơn ngưỡng che")
        self.assertIn("password", truong, "danh sách trường credential phải có `password`")
        self.assertIn("apiaccount", truong, "danh sách trường credential phải có `apiAccount`")

        _dc_am("ro-bi-mat")
        with stub() as s, dem_ket_noi(chan_that=False):
            # (a) header tên CREDENTIAL, giá trị NGẮN
            try:
                http_jt.gui_form(s.url("/echo-header"), {"apiAccount": ngan},
                                 {"bizContent": "{}"}, timeout=5)
                self.fail("phải ném")
            except transport.LoiVinhVien as e:
                self.assertNotIn(ngan, str(e),
                                 "giá trị header `apiAccount` NGẮN bị rò NGUYÊN VĂN ⇒ CRITICAL")
            # (b) giá trị NGẮN nằm dưới khoá `password` trong `bizContent` (JSON lồng)
            try:
                http_jt.gui_form(s.url("/echo"), {"apiAccount": "669"},
                                 {"bizContent": json.dumps({"password": ngan})}, timeout=5)
                self.fail("phải ném")
            except transport.LoiVinhVien as e:
                self.assertNotIn(ngan, str(e),
                                 "`password` NGẮN trong bizContent bị rò ⇒ CRITICAL")
        _dc_duong("ro-bi-mat")

        # ĐO, KHÔNG CHẶN: giá trị KHÔNG mang tên credential và NGẮN hơn ngưỡng thì KHÔNG bị che —
        # đó là chủ ý (che số ngắn vô hại làm hỏng thông điệp chẩn đoán). Ghi ra để lượt sau biết.
        PHAT_HIEN.append(
            f"ngưỡng che KHÔNG-tên = {nguong} ký tự · trường credential che bất kể độ dài = {truong}")

    def test_t22_429_va_408_la_TAM_THOI_con_4xx_khac_van_VINH_VIEN(self):
        """Hợp đồng AG-00 chốt 15/10/2026: 429/408 = *"thử lại sau"* ⇒ TẠM THỜI.

        Đây là ca **hai chiều**, và chiều ÂM quan trọng ngang chiều dương: một bản vá nới rộng
        "4xx là tạm thời" sẽ biến lỗi CHẮC CHẮN hỏng (sai chữ ký, sai quyền) thành một vòng
        thử lại vô ích. Nên 400/401/403/404 **phải vẫn** là `LoiVinhVien`.
        """
        _dc_am("ma-http")
        for duong, ket in (("/429", http_jt.KET_CUC_QUA_HAN_MUC), ("/408", http_jt.KET_CUC_KHONG_GUI_DI)):
            with self.subTest(duong=duong), stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiTamThoi) as e:
                    http_jt.gui_form(s.url(duong), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(getattr(e.exception, "timeout", None), True)
            self.assertEqual(getattr(e.exception, "ket_cuc", None), ket)
            self.assertEqual(getattr(e.exception, "ma_http", None), int(duong[1:]))
        for duong, ma in (("/400", 400), ("/401", 401), ("/403", 403), ("/404", 404)):
            with self.subTest(duong=duong), stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiVinhVien) as e:
                    http_jt.gui_form(s.url(duong), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(getattr(e.exception, "ma_http", None), ma,
                             f"HTTP {ma} phải VẪN là vĩnh viễn — bản vá đã nới cả 4xx")
        _dc_duong("ma-http")

    def test_t23_Retry_After_duoc_DOC_va_KEP_TRAN(self):
        """`Retry-After` là dữ liệu NGOÀI: đọc được thì tốt, nhưng KHÔNG được phép treo tiến trình."""
        _dc_am("retry-after")
        tran = transport.CHO_TOI_DA
        self.assertGreater(tran, 0)
        for ra, mong in (("5", 5.0), (str(int(tran) + 3600), float(tran))):
            with self.subTest(Retry_After=ra), stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiTamThoi) as e:
                    http_jt.gui_form(s.url("/429?ra=" + ra), {}, {"bizContent": "{}"}, timeout=5)
            self.assertEqual(getattr(e.exception, "cho_giay", None), mong,
                             f"Retry-After: {ra} ⇒ cho_giay phải là {mong}")
        # ĐỐI CHỨNG DƯƠNG: KHÔNG có header thì vẫn phải là lỗi tạm thời, chỉ là không có gợi ý.
        with stub() as s, dem_ket_noi(chan_that=False):
            with self.assertRaises(transport.LoiTamThoi):
                http_jt.gui_form(s.url("/429"), {}, {"bizContent": "{}"}, timeout=5)
        _dc_duong("retry-after")

    def test_t24_gui_form_KHONG_BAO_GIO_ngu(self):
        """`gui_form` gửi MỘT lượt rồi trả về. Ngủ trong đó thì `so_lan=3` nhân thời gian chờ lên 3.

        Soát HAI cách: AST trên nguồn (bắt cả nhánh chưa chạy tới) và ĐỘNG (thay `time.sleep`
        bằng hàm ném, rồi gọi thật).
        """
        _dc_am("khong-ngu")
        nguon = io.open(os.path.join(GOC_APP, "http_jt.py"), encoding="utf-8").read()
        cay = ast.parse(nguon)
        for nut in ast.walk(cay):
            if isinstance(nut, ast.FunctionDef) and nut.name == "gui_form":
                for con in ast.walk(nut):
                    if isinstance(con, ast.Call):
                        f = con.func
                        ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
                        self.assertNotIn(ten, ("sleep", "wait", "run", "run_until_complete"),
                                         f"`gui_form` gọi {ten}() ở dòng {con.lineno} — "
                                         "việc CHỜ thuộc `transport.goi()`, không thuộc lớp này")
                break
        else:
            self.fail("không tìm thấy `gui_form` trong nguồn ⇒ phép soát AST không đo gì")

        goc_ngu = time.sleep
        time.sleep = lambda g: self.fail(f"`gui_form` ĐÃ NGỦ {g} giây — việc chờ thuộc transport.goi()")
        try:
            with stub() as s, dem_ket_noi(chan_that=False):
                with self.assertRaises(transport.LoiTamThoi):
                    http_jt.gui_form(s.url("/429?ra=5"), {}, {"bizContent": "{}"}, timeout=5)
        finally:
            time.sleep = goc_ngu
        _dc_duong("khong-ngu")

    def test_t25_transport_goi_lay_MAX_va_kep_tran(self):
        """`cho_giay` phải vào ĐÚNG chỗ: `transport.goi()` lấy MAX với backoff rồi kẹp `CHO_TOI_DA`."""
        _dc_am("retry-after")
        da_ngu = []

        def _ngu(giay):
            da_ngu.append(giay)

        def _ham():
            raise transport.LoiTamThoi("429", cho_giay=transport.CHO_TOI_DA + 3600)

        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(_ham, "getOrder", ngu=_ngu)
        self.assertTrue(da_ngu, "không có lượt chờ nào ⇒ phép đo không chạm gì")
        self.assertLessEqual(max(da_ngu), transport.CHO_TOI_DA,
                             f"chờ {max(da_ngu)}s — VƯỢT trần {transport.CHO_TOI_DA}s")
        self.assertGreaterEqual(max(da_ngu), transport.CHO_TOI_DA * 0.99,
                                "gợi ý lớn hơn trần thì phải chờ ĐÚNG bằng trần")
        _dc_duong("retry-after")

    # ── T19/T20: thân nguyên văn · không rò trạng thái toàn cục ───────────────────────────────
    def test_t19_than_tra_loi_nguyen_van_tung_byte(self):
        with stub() as s, dem_ket_noi(chan_that=False):
            r = http_jt.gui_form(s.url("/bytes"), {}, {"bizContent": "{}"}, timeout=5)
        self.assertEqual(r.than, b"\xff\xfe\r\n\x00binary\x80",
                         "thân bị giải mã/mã hoá lại ⇒ mất bằng chứng")

    def test_t20_khong_doi_timeout_toan_cuc(self):
        truoc = socket.getdefaulttimeout()
        with stub() as s, dem_ket_noi(chan_that=False):
            http_jt.gui_form(s.url("/ok"), {}, {"bizContent": "{}"}, timeout=5)
            try:
                http_jt.gui_form(s.url("/slow"), {}, {"bizContent": "{}"}, timeout=0.4)
            except transport.LoiTamThoi:
                pass
        self.assertEqual(socket.getdefaulttimeout(), truoc,
                         "đổi `socket.setdefaulttimeout` toàn cục ⇒ mọi socket khác bị ảnh hưởng")

    def test_t21_tra_loi_repr_khong_in_than(self):
        r = http_jt.TraLoiHTTP(200, b"bi-mat-trong-than", {"a": "b"})
        self.assertNotIn("bi-mat-trong-than", repr(r), "repr in thân ⇒ thân hay bị đem đi log")


def _ip_khong_vong_lap():
    """Địa chỉ IPv4 của máy KHÔNG phải loopback — để thử chiều âm của T2."""
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
class C_Credentials(unittest.TestCase):
    """G16-A/2 — CREDENTIAL CONFIGURATION."""

    def test_c1_bon_ten_truong_hai_lop(self):
        self.assertEqual(set(cau_hinh.JT_TRUONG_CREDENTIALS),
                         {"apiAccount", "privateKey", "customerCode", "password"})
        self.assertEqual(set(cau_hinh.JT_TRUONG_NEN_TANG), {"apiAccount", "privateKey"})
        self.assertEqual(set(cau_hinh.JT_TRUONG_BUU_CUC), {"customerCode", "password"})
        self.assertEqual(len(set(cau_hinh.JT_TRUONG_NEN_TANG) & set(cau_hinh.JT_TRUONG_BUU_CUC)), 0)
        _dc_duong("credentials")

    def test_c2_env_example_khong_gan_gia_tri_cho_bon_truong(self):
        duong = os.path.join(GOC_CAY, ".env.example")
        self.assertTrue(os.path.isfile(duong), ".env.example phải tồn tại (là TÀI LIỆU)")
        for i, dong in enumerate(io.open(duong, encoding="utf-8"), 1):
            than = dong.split("#", 1)[0].strip()
            if not than or "=" not in than:
                continue
            ten, _, gt = than.partition("=")
            if ten.strip() in cau_hinh.JT_TRUONG_CREDENTIALS:
                self.assertEqual(gt.strip(), "",
                                 f".env.example dòng {i}: '{ten.strip()}' bị GÁN GIÁ TRỊ ⇒ CRITICAL")
        _dc_am("credentials")
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải BẮT được một dòng có giá trị.
        self.assertTrue(_env_co_gia_tri("password=abc123\n"),
                        "bộ dò .env của chính ca này hỏng ⇒ ca âm vô nghĩa")
        self.assertFalse(_env_co_gia_tri("# password để trống\npassword=\n"))

    def test_c3_env_bi_gitignore_chan_va_khong_co_env_that(self):
        self.assertFalse(os.path.exists(os.path.join(GOC_CAY, ".env")),
                         "có tệp .env thật trong cây ⇒ nguy cơ credentials vào Git")
        gi = io.open(os.path.join(GOC_CAY, ".gitignore"), encoding="utf-8").read().splitlines()
        gi = [d.strip() for d in gi]
        self.assertIn(".env", gi)
        self.assertIn(".env.*", gi)
        self.assertIn("!.env.example", gi)

    def test_c4_git_khong_theo_doi_credentials(self):
        ds = _git(["ls-files"]).splitlines()
        self.assertTrue(ds, "git ls-files rỗng — phép kiểm không đo gì")
        env = [d for d in ds if os.path.basename(d).startswith(".env")]
        self.assertEqual(env, [".env.example"], f"Git đang theo dõi tệp env lạ: {env}")

    def test_c5_khong_hard_code_secret_trong_ma_san_pham(self):
        """Quét mô-đun SẢN PHẨM. Bộ thử/harness được MIỄN: fixture PHẢI được có giá trị giả."""
        vi_pham, da_quet = [], []
        for goc, _, tens in os.walk(GOC_APP):
            if os.path.basename(goc) in THU_MUC_MIEN:
                continue
            for t in sorted(tens):
                if not t.endswith(".py") or t in TEP_MIEN:
                    continue
                p = os.path.join(goc, t)
                da_quet.append(os.path.relpath(p, GOC_CAY))
                nguon = io.open(p, encoding="utf-8", errors="replace").read()
                for v in quet_hardcode(nguon):
                    vi_pham.append(f"{os.path.relpath(p, GOC_CAY)}:{v}")
        self.assertGreaterEqual(len(da_quet), 20,
                                f"chỉ quét được {len(da_quet)} tệp ⇒ phép quét nhìn sai chỗ")
        self.assertNotIn("harness_hang.py", " ".join(da_quet), "harness phải được miễn")
        self.assertEqual(vi_pham, [], "secret hard-code ⇒ CRITICAL:\n" + "\n".join(vi_pham))
        _dc_am("credentials")

        # ĐỐI CHỨNG DƯƠNG 1 — mẫu bịa: bộ dò PHẢI bắt.
        self.assertTrue(quet_hardcode('password = "Xk9#mQ2$vL7@nR4"\n'),
                        "bộ dò hard-code của chính ca này hỏng ⇒ ca âm vô nghĩa")
        self.assertTrue(quet_hardcode('CFG = {"privateKey": "Xk9#mQ2$vL7@nR4"}\n'))
        # ĐỐI CHỨNG DƯƠNG 2 — TIÊM secret THẬT vào BẢN SAO một mô-đun sản phẩm rồi quét lại.
        # Đây là phép ĐỘT BIẾN: nếu bộ dò không bắt được bí mật thật trong chính tệp thật thì
        # "0 phát hiện" ở trên KHÔNG chứng minh gì.
        goc_that = os.path.join(GOC_APP, "transport.py")
        ban_sao = io.open(goc_that, encoding="utf-8").read() + (
            '\nMAT_KHAU_MAC_DINH = "Xk9#mQ2$vL7@nR4"\n')
        self.assertTrue(quet_hardcode(ban_sao),
                        "tiêm secret THẬT vào bản sao transport.py mà bộ dò KHÔNG thấy ⇒ vô giá trị")
        # ĐỐI CHỨNG ÂM 3 — TIÊM vào CHÍNH tệp đã bị bắt nhầm (`xac_thuc_best.py`) cả hai dạng:
        # phép gán và giá trị dict. Nếu bản sửa chỉ "tắt tiếng" tệp này thì hai phép tiêm dưới
        # đây sẽ im ⇒ ca này đỏ ngay.
        ban_sao = io.open(os.path.join(GOC_APP, "xac_thuc_best.py"),
                          encoding="utf-8").read() + (
            '\nTOKEN_TIEM_VAO_TEP_THAT = "Xk9#mQ2$vL7@nR4"\n'
            'MA_LOI_TIEM = {"TOKEN_KHONG_HOP_LE": "Xk9#mQ2$vL7@nR4"}\n')
        self.assertTrue(
            quet_hardcode(ban_sao),
            "tiêm secret THẬT vào bản sao xac_thuc_best.py (phép gán + dict) mà bộ dò KHÔNG "
            "thấy ⇒ bản sửa đã tắt bộ dò chứ không phân biệt ngữ cảnh")
        # PHÂN BIỆT THÔNG BÁO LỖI với SECRET THẬT — cùng một mã lỗi, hai giá trị khác nhau:
        # câu chẩn đoán KHÔNG kêu; token tiêm vào CHÍNH mã ấy PHẢI kêu.
        self.assertEqual(
            quet_hardcode(
                'MA_LOI = {"CREDENTIAL_KHONG_HOP_LE": "Username rỗng/sai kiểu/ký tự điều khiển; '
                'Password rỗng/sai kiểu/quá dài/NUL"}\n'),
            [], "câu thông báo lỗi bị nhận nhầm là credential hard-code")
        self.assertTrue(
            quet_hardcode('MA_LOI = {"CREDENTIAL_KHONG_HOP_LE": "Xk9#mQ2$vL7@nR4"}\n'),
            "tiêm secret vào CÙNG mã lỗi mà bộ dò im ⇒ đã miễn cả mã lỗi, không phải phân biệt")
        self.assertTrue(quet_hardcode('PASSWORD = "correct horse battery staple"\n'),
                        "tên trường bí mật chuẩn + câu nhiều từ vẫn phải bắt")
        # ĐỐI CHỨNG ÂM — những thứ KHÔNG được kêu (đúng 5 dương tính giả của lượt đầu):
        for mau, vi_sao in (
            ('D = {"credentials hãng / khoá / token / mật khẩu / hash": "cấm tuyệt đối vì lý do"}\n',
             "KHOÁ dict là CÂU VĂN tài liệu"),
            ('cred = {"apiAccount": "111", "privateKey": "KHOA-BI-MAT-XYZ"}\n',
             "fixture có dấu hiệu giữ chỗ"),
            ('password = os.environ.get("X")\n', "đọc từ môi trường"),
            ('password = ""\n', "rỗng"),
            ('password = "MK-THU"\n', "fixture ngắn"),
        ):
            with self.subTest(mau=vi_sao):
                self.assertEqual(quet_hardcode(mau), [], f"dương tính giả: {vi_sao}")
        _dc_duong("credentials")

    def test_c6_c7_c10_duong_luu_duy_nhat_la_ma_hoa_cred(self):
        cred = {"apiAccount": "669", "privateKey": CANARY_DUOI + "-PK",
                "customerCode": "CC-THU", "password": CANARY_DUOI + "-PW"}
        ban_ma, duoi = bao_mat.ma_hoa_cred(dict(cred), 1, "jt")
        self.assertTrue(ban_ma.startswith("v3$"), f"bản mã không mang key_id v3: {ban_ma[:4]!r}")
        phan = ban_ma.split("$")
        self.assertEqual(len(phan), 4, "bản mã v3 phải có 4 phần v3$key_id$nonce$ct")
        self.assertTrue(phan[1].strip(), "key_id RỖNG")
        for gt in cred.values():
            if len(gt) >= 8:
                self.assertNotIn(gt, ban_ma, "BẢN RÕ lọt vào bản mã ⇒ CRITICAL")
        self.assertEqual(bao_mat.giai_ma_cred(ban_ma, 1, "jt"), cred, "khứ hồi lệch")
        ban_ma2, _ = bao_mat.ma_hoa_cred(dict(cred), 1, "jt")
        self.assertNotEqual(ban_ma, ban_ma2, "hai lượt mã hoá ra CÙNG bản mã ⇒ nonce không ngẫu nhiên")
        _dc_duong("credentials")

    def test_c8_c9_aad_sai_thi_PHAI_nem(self):
        cred = {"apiAccount": "669", "privateKey": CANARY_DUOI + "-PK",
                "customerCode": "CC-THU", "password": CANARY_DUOI + "-PW"}
        ban_ma, _ = bao_mat.ma_hoa_cred(dict(cred), 1, "jt")
        for ten, args in (("tenant khác", (ban_ma, 2, "jt")), ("hãng khác", (ban_ma, 1, "vtp"))):
            with self.subTest(aad=ten):
                try:
                    ra = bao_mat.giai_ma_cred(*args)
                except Exception:
                    ra = None
                self.assertIsNone(ra, f"AAD {ten} vẫn giải ra bản rõ ⇒ CRITICAL")
        _dc_am("aad")
        self.assertEqual(bao_mat.giai_ma_cred(ban_ma, 1, "jt"), cred)
        _dc_duong("aad")

    def test_c11_khong_in_gia_tri_ra_stdout(self):
        ma = ("import sys; sys.path.insert(0, %r)\n"
              "import cau_hinh as c\n"
              "print('TEN=', c.JT_TRUONG_CREDENTIALS)\n"
              "print('THIEU=', c.jt_thieu_truong({}))\n" % GOC_APP)
        r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                           timeout=60, env=dict(os.environ, VIP_HUB_DATA=_tam))
        self.assertEqual(r.returncode, 0, r.stderr)
        for ten in cau_hinh.JT_TRUONG_CREDENTIALS:
            self.assertIn(ten, r.stdout)
        self.assertNotIn(CANARY_DUOI, r.stdout)

    def test_c12_cong_moi_truong_tu_choi_kem_ly_do(self):
        for mt in ("sandbox", "production"):
            cho_qua, ly_do = cau_hinh.jt_kiem_moi_truong(mt)
            self.assertFalse(cho_qua)
            self.assertGreater(len(str(ly_do)), 20, "lý do từ chối phải ĐỌC ĐƯỢC, không im lặng")
        self.assertTrue(cau_hinh.jt_kiem_moi_truong("mock")[0])

    def test_c13_luoc_do_khong_co_cot_credentials_ban_ro(self):
        nguon = io.open(os.path.join(GOC_APP, "csdl.py"), encoding="utf-8").read()
        m = re.search(r"CREATE TABLE IF NOT EXISTS carrier_accounts \((.*?)\n\);", nguon, re.S)
        self.assertIsNotNone(m, "không tìm thấy DDL carrier_accounts ⇒ phép kiểm không đo gì")
        than = m.group(1)
        cot = re.findall(r"^\s*([a-z_][a-z0-9_]*)", than, re.M)
        self.assertIn("credentials_ma_hoa", cot)
        self.assertNotIn("credentials", cot, "có cột credentials BẢN RÕ ⇒ CRITICAL")
        self.assertNotIn("password", cot)
        self.assertNotIn("private_key", cot)


def _env_co_gia_tri(van_ban):
    """Bộ dò dùng chung cho ca c2 — tách ra để ca dương đo được chính nó."""
    for dong in van_ban.splitlines():
        than = dong.split("#", 1)[0].strip()
        if "=" in than:
            ten, _, gt = than.partition("=")
            if ten.strip() in ("apiAccount", "privateKey", "customerCode", "password") and gt.strip():
                return True
    return False


# So CHUỖI CON trên TÊN (để bắt cả `MAT_KHAU_MAC_DINH`) — an toàn vì KHOÁ dict dạng câu văn đã
# bị chặn riêng bằng `re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ...)` trước khi tới đây.
TEN_NHAY_CAM = re.compile(
    r"(private_?key|password|passwd|mat_?khau|pwd|customer_?code|api_?account|secret|token|"
    r"api_?key|credential|khoa_bi_mat|access_?key|client_?secret)", re.I)

# Dấu hiệu GIỮ CHỖ. Danh sách ĐEN là hướng AN TOÀN: quên một từ chỉ bỏ sót một fixture vô hại,
# còn nhận nhầm một fixture là chặn oan — và một cổng kêu nhầm thì bị HỌC CÁCH BỎ QUA
# (`BAN_GIAO.md` §7.1). Đây là bài học AG-00 đo được: 5/5 dòng bị cờ ở lượt đầu đều là dương
# tính giả (2 dòng là KHOÁ dict tài liệu trong `ai_job.py`, 3 dòng là fixture `harness_hang.py`).
DAU_HIEU_GIA = ("mock", "thu", "xyz", "demo", "test", "example", "change", "bi-mat", "bimat",
                "fake", "dummy", "sample", "placeholder", "your-", "abc", "123", "nhap",
                "diensan", "填", "ví dụ", "vi du")

# Mô-đun KHÔNG quét: bộ thử và harness PHẢI được phép có giá trị giả — nếu không thì không
# viết được bộ thử nào. Đây là "quét mô-đun SẢN PHẨM", không phải quét cả cây.
THU_MUC_MIEN = ("thu", "__pycache__", "du-lieu", "thu_giao_dien")
TEP_MIEN = ("harness_hang.py", "seed.py")


def _la_giu_cho(v):
    """Từ NGẮN (`thu`, `abc`, `123`) phải khớp theo RANH GIỚI — khớp giữa chữ sẽ bỏ sót bí mật thật.

    `thu` là dấu hiệu của fixture (`KHOA-THU-MOCK`), nhưng khớp thô thì `thuong`/`thuc` cũng dính;
    hướng sai đó là BỎ SÓT một bí mật thật, tệ hơn nhiều so với bỏ sót một fixture.
    """
    thap = v.lower()
    for d in DAU_HIEU_GIA:
        if len(d) <= 4:
            if re.search(r"(^|[^a-z])" + re.escape(d) + r"([^a-z]|$)", thap):
                return True
        elif d in thap:
            return True
    return False


def _du_manh(v):
    """Bí mật THẬT thường dài và trộn loại ký tự. Fixture thì không."""
    if len(v) < 12:
        return False
    loai = sum(bool(re.search(p, v)) for p in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]"))
    return loai >= 2


# Mã lỗi ổn định trong sản phẩm là UPPER_SNAKE (`CREDENTIAL_KHONG_HOP_LE`). Tên ấy khớp
# `TEN_NHAY_CAM` ở tiền tố "credential"/"token", nhưng GIÁ TRỊ của nó là CÂU VĂN chẩn đoán —
# không phải bí mật. Đây là ngữ cảnh AST cần phân biệt (Finding G16: 3 dòng trong `MA_LOI`).
MA_LOI_UPPER_SNAKE = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")

# Tên trường bí mật CHUẨN — dù giá trị là câu nhiều từ vẫn phải bắt. `ADMIN_PASSWORD` /
# `API_KEY` là tên người ta hard-code thật; còn `CREDENTIAL_KHONG_HOP_LE` là MÃ LỖI.
TEN_BI_MAT_CHUAN = {"password", "passwd", "pwd", "matkhau", "secret", "token",
                    "apikey", "privatekey", "accesskey", "credential", "clientsecret"}
DUOI_TEN_BI_MAT = ("password", "passwd", "matkhau", "secret", "apikey", "privatekey",
                   "accesskey")


def _ten_truong_bi_mat(ten):
    chuan = re.sub(r"[^a-z0-9]", "", str(ten).lower())
    return chuan in TEN_BI_MAT_CHUAN or any(chuan.endswith(d) for d in DUOI_TEN_BI_MAT)


def _la_cau_thong_bao(ten, v):
    """THÔNG BÁO LỖI ≠ SECRET THẬT: mã lỗi UPPER_SNAKE đi với CÂU VĂN nhiều từ.

    Secret thật là một TOKEN LIỀN MẠCH (`Xk9#mQ2$vL7@nR4`); thông báo lỗi là câu chẩn đoán
    ("Username rỗng/sai kiểu/ký tự điều khiển; ..."). Miễn trừ này CHỈ áp cho định danh dạng mã
    lỗi và KHÔNG áp cho tên trường bí mật chuẩn — nên `PASSWORD = "correct horse ..."` vẫn bị
    bắt, và tiêm một token vào chính `CREDENTIAL_KHONG_HOP_LE` cũng vẫn bị bắt (đối chứng âm
    trong `test_c5`). Không có danh sách trắng tệp/dòng nào ở đây.
    """
    if not MA_LOI_UPPER_SNAKE.fullmatch(str(ten)) or _ten_truong_bi_mat(ten):
        return False
    tu = v.split()
    if len(tu) < 3:
        return False
    return sum(bool(re.search(r"[^\W\d_]{2,}", t)) for t in tu) >= 2


def quet_hardcode(nguon):
    """Quét AST (KHÔNG grep — grep bắt cả chú thích, bài học §L2.9). Trả danh sách vi phạm.

    Bốn luật để KHÔNG kêu nhầm:
      1. chỉ literal ở **vế phải phép gán** hoặc **giá trị của dict** — không xét KHOÁ dict,
         không xét literal nằm trong câu văn;
      2. tên trường phải là **định danh** (`privateKey`), không phải câu mô tả có dấu cách;
      3. giá trị phải **đủ mạnh** và **không mang dấu hiệu giữ chỗ**;
      4. giá trị là **CÂU VĂN của một MÃ LỖI** thì là thông báo, không phải secret (xem
         `_la_cau_thong_bao`) — nhưng token tiêm vào cùng mã lỗi vẫn bị bắt.
    """
    try:
        cay = ast.parse(nguon)
    except SyntaxError:
        return []
    ra = []
    for nut in ast.walk(cay):
        cap = []
        if isinstance(nut, ast.Assign):
            for t in nut.targets:
                if isinstance(t, ast.Name):
                    cap.append((t.id, nut.value))
                elif isinstance(t, ast.Attribute):
                    cap.append((t.attr, nut.value))
                elif isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant):
                    cap.append((str(t.slice.value), nut.value))
        elif isinstance(nut, ast.AnnAssign) and isinstance(nut.target, ast.Name):
            cap.append((nut.target.id, nut.value))
        elif isinstance(nut, ast.Dict):
            # CHỈ giá trị của dict, và CHỈ khi khoá có dạng ĐỊNH DANH (không dấu cách, không '/').
            # Khoá kiểu "credentials hãng / khoá / token" là câu văn tài liệu, không phải trường.
            for k, v in zip(nut.keys, nut.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str) \
                        and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k.value):
                    cap.append((k.value, v))
        for ten, gt in cap:
            if not TEN_NHAY_CAM.match(str(ten)):
                continue
            if not (isinstance(gt, ast.Constant) and isinstance(gt.value, (str, bytes))):
                continue
            v = gt.value.decode("utf-8", "replace") if isinstance(gt.value, bytes) else gt.value
            if not _du_manh(v) or _la_giu_cho(v):
                continue
            if _la_cau_thong_bao(ten, v):
                continue
            ra.append(f"dòng {getattr(gt, 'lineno', '?')}: {ten} = <literal {len(v)} ký tự>")
    return ra


def _git(args):
    """Git với môi trường ĐÃ GỠ `GIT_CONFIG_*` (môi trường git của máy này hỏng — Finding A)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    r = subprocess.run(["git", "-C", GOC_CAY] + args, capture_output=True, text=True,
                       timeout=120, env=env)
    return r.stdout


# ══════════════════════════════════════════════════════════════════════════════════════════════
class H_HopDong(unittest.TestCase):
    """G16-A/3 — CONTRACT TESTS."""

    def test_h1_chu_ky_dung_tung_byte(self):
        for biz, khoa, mong in VECTOR_G16:
            with self.subTest(biz=biz):
                # Tính lại ĐỘC LẬP, không mượn hàm của adapter.
                doc_lap = base64.b64encode(
                    hashlib.md5((biz + khoa).encode("utf-8")).digest()).decode()
                self.assertEqual(doc_lap, mong, "vector ghim đã sai — tính lại tay")
                self.assertEqual(aj.ky_digest(biz, khoa), mong)
        # ĐỘT BIẾN: bản SAI (hexdigest → base64) phải KHÁC bản đúng.
        biz, khoa = VECTOR_G16[1][0], VECTOR_G16[1][1]
        sai = base64.b64encode(hashlib.md5((biz + khoa).encode()).hexdigest().encode()).decode()
        self.assertNotEqual(aj.ky_digest(biz, khoa), sai,
                            "bộ dò không phân biệt được md5-bytes và md5-hexdigest ⇒ vô nghĩa")
        self.assertEqual(len(aj.ky_digest(biz, khoa)), 24)
        _dc_duong("hop-dong")

    def test_h2_moc_thoi_gian_utc7_mili_giay(self):
        t0 = time.time()
        ms = aj.dau_thoi_gian_ms()
        t1 = time.time()
        self.assertIsInstance(ms, int)
        self.assertEqual(len(str(ms)), 13, f"mốc phải là MILI giây 13 chữ số, nhận {ms}")
        self.assertLess(abs(ms / 1000.0 - (t0 + t1) / 2), 5.0)
        _dc_duong("hop-dong")

    def test_h2b_moc_naive_khong_phu_thuoc_mui_gio_MAY(self):
        """Đóng `L2-N2` của AG-01: mốc naive phải được hiểu là UTC+7, KHÔNG theo múi giờ máy.

        Đo bằng TIẾN TRÌNH CON với `TZ` khác nhau — không đoán, không đọc mã.
        """
        ma = (
            "import sys, datetime as dt\n"
            "sys.path.insert(0, %r)\n"
            "import adapter_jt as aj\n"
            "n = dt.datetime(2026, 10, 15, 10, 0, 0)\n"
            "print(aj.dau_thoi_gian_ms(n), aj.dau_thoi_gian_ms(n.replace(tzinfo=dt.timezone(dt.timedelta(hours=7)))))\n"
            % GOC_APP)
        for tz in ("UTC", "Etc/UTC", "Asia/Ho_Chi_Minh", "America/New_York"):
            with self.subTest(TZ=tz):
                r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                                   timeout=60, env=dict(os.environ, TZ=tz, VIP_HUB_DATA=_tam))
                self.assertEqual(r.returncode, 0, r.stderr)
                a, b = (int(x) for x in r.stdout.split())
                self.assertEqual(a, b, f"TZ={tz}: mốc naive bị hiểu theo múi giờ MÁY, không phải UTC+7")

    def test_h3_cod_di_codMoney_khong_bao_gio_itemsValue(self):
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        biz = json.loads(yc["bizContent"])
        self.assertIn("codMoney", biz, "COD phải đi ở trường codMoney")
        self.assertEqual(biz["codMoney"], str(DON_MAU["cod"]), "codMoney phải là CHUỖI số nguyên")
        self.assertNotIn("itemsValue", biz,
                         "itemsValue KHÔNG có trong bảng tham số J&T — dùng nó là mất tiền COD")
        _dc_am("cod")
        # ĐỐI CHỨNG DƯƠNG: COD = 0 vẫn phải GỬI trường (không bỏ trống).
        d0 = dict(DON_MAU, cod=0)
        biz0 = json.loads(ad_mock().yeu_cau_tao_don(d0)["bizContent"])
        self.assertIn("codMoney", biz0)
        _dc_duong("cod")

    def test_h4_ba_ket_cuc_khong_gop(self):
        ok = aj.KetQuaHang(True, ma_van_don="X")
        self.assertTrue(ok.ok)
        _, kq_tu_choi = _phan_loai(transport.LoiVinhVien("4xx"))
        _, kq_khong_biet = _phan_loai(transport.LoiTamThoi("5xx"))
        self.assertFalse(kq_tu_choi.ok)
        self.assertFalse(kq_khong_biet.ok)
        self.assertIs(kq_tu_choi.timeout, False, "hãng TỪ CHỐI ⇒ biết chắc, timeout=False")
        self.assertIs(kq_khong_biet.timeout, True, "KHÔNG BIẾT ⇒ timeout=True, không bao giờ là ok")
        self.assertNotEqual((kq_tu_choi.ok, kq_tu_choi.timeout), (kq_khong_biet.ok, kq_khong_biet.timeout),
                            "hai kết cục bị GỘP làm một ⇒ CRITICAL")

    def test_h5_chong_don_trung_o_TANG_CSDL(self):
        nguon = io.open(os.path.join(GOC_APP, "csdl.py"), encoding="utf-8").read()
        m = re.search(r"CREATE TABLE IF NOT EXISTS don_hang \((.*?)\n\);", nguon, re.S)
        self.assertIsNotNone(m, "không tìm thấy DDL don_hang")
        self.assertIn("idem_key", m.group(1))
        self.assertRegex(m.group(1), r"UNIQUE\s*\(\s*tenant_id\s*,\s*idem_key\s*\)",
                         "chống trùng phải bằng UNIQUE ở CSDL, KHÔNG bằng `if` trong mã ⇒ CRITICAL")

    def test_h6_co_lap_tenant_tren_credentials(self):
        """Nối C8 ở mức HỢP ĐỒNG: khoá của tenant này không mở được bằng AAD tenant khác."""
        cred = {"apiAccount": "669", "privateKey": CANARY_DUOI + "-PK",
                "customerCode": "CC-THU", "password": CANARY_DUOI + "-PW"}
        ban_ma, _ = bao_mat.ma_hoa_cred(dict(cred), 11, "jt")
        self.assertEqual(bao_mat.giai_ma_cred(ban_ma, 11, "jt"), cred)
        try:
            ra = bao_mat.giai_ma_cred(ban_ma, 22, "jt")
        except Exception:
            ra = None
        self.assertIsNone(ra, "tenant khác giải được credentials ⇒ CRITICAL")

    def test_h7_chot_D9_city_area_con_no(self):
        for mt in ("sandbox", "production"):
            with self.subTest(moi_truong=mt):
                with self.assertRaises(loi_hang.NormalizedCarrierError) as e:
                    aj.chot_chan_anh_xa_area(mt)
                self.assertIn("D-9", str(e.exception), "chốt D-9 nổ nhưng không nói rõ là chốt nào")
        _dc_am("d9")
        # Ổ KHOÁ SÂU HƠN: mở `CHO_PHEP_LIVE` rồi dựng bizContent thật cho sandbox ⇒ vẫn phải DỪNG.
        with _cho_phep_live_tam():
            ad = adapter.tao_adapter("jt", dict(CRED_THU), "sandbox")
            with self.assertRaises((loi_hang.NormalizedCarrierError, aj.ChuaXacNhanTaiLieu)):
                ad.yeu_cau_tao_don(dict(DON_MAU))
        self.assertEqual(aj.CAP_HANH_CHINH_CHO_AREA, "quan-huyen",
                         "giả định ánh xạ `area` đã đổi mà không ai cập nhật chốt D-9")
        self.assertIs(aj.CITY_CO_GUI, False)
        self.assertIs(aj.ANH_XA_AREA_DA_XAC_NHAN, False,
                      "cờ xác nhận ánh xạ `area` bị mở mà chưa có J&T trả lời ⇒ CRITICAL")
        _dc_duong("d9")
        # ĐỐI CHỨNG DƯƠNG: `mock` phải ĐI QUA được (chốt chỉ chặn đường LIVE).
        self.assertIsNone(aj.chot_chan_anh_xa_area("mock"))
        self.assertTrue(ad_mock().yeu_cau_tao_don(dict(DON_MAU))["bizContent"])

    def test_h8_ma_chua_xac_minh_khong_ra_DELIVERED(self):
        """D-4: mã CHƯA xác minh không được thành `giao_thanh_cong`, không kích hoạt đối soát COD."""
        import trang_thai_hang as tth
        _dc_am("ma-chua-xac-minh")
        for ma in ("110", "9999", "0", "-1", ""):
            with self.subTest(ma=ma):
                try:
                    qd = tth.quyet_dinh("jt", ma)
                except Exception:
                    continue
                self.assertNotEqual(qd.trang_thai_ap, "giao_thanh_cong",
                                    f"mã chưa xác minh {ma!r} bị coi là GIAO THÀNH CÔNG ⇒ CRITICAL")
                self.assertNotEqual(qd.nhan, "OK",
                                    f"mã chưa xác minh {ma!r} được coi là ĐÃ XÁC MINH")
        # ĐỐI CHỨNG DƯƠNG: mã ĐÃ có trong bảng hiệu lực phải đi qua được — nếu không thì ca âm
        # ở trên xanh một cách vô nghĩa (hàm hỏng, luôn trả None, cũng làm mọi ca âm xanh).
        for ma, mong in (("113", "giao_thanh_cong"), ("103", "cho_lay"), ("106", "lay_hang")):
            with self.subTest(ma_hop_le=ma):
                qd = tth.quyet_dinh("jt", ma)
                self.assertEqual(qd.nhan, "OK", f"mã hợp lệ {ma!r} bị đánh dấu cần soát")
                self.assertEqual(qd.trang_thai_ap, mong)
        _dc_duong("ma-chua-xac-minh")


def _phan_loai(loi):
    """Đối chứng cho h4: dùng CHÍNH hàm ánh xạ của adapter, không viết lại."""
    ad = ad_mock()
    kq = ad._ket_qua_tu_ngoai_le_transport(loi, "createOrder")
    return ad, kq


# ══════════════════════════════════════════════════════════════════════════════════════════════
class Z_TongKet(unittest.TestCase):
    """CHỐT CHẶN 2 (§6.3): nhóm nào có ca ÂM mà không có ca DƯƠNG ⇒ bộ thử TỰ BÁO HỎNG."""

    def test_z1_moi_nhom_phu_dinh_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertEqual(thieu, [], f"nhóm có ca âm mà KHÔNG có đối chứng dương: {thieu}")
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")

    def test_z2_in_dong_pham_vi(self):
        print("\n" + _dong_pham_vi(CO_HTTP_JT))
        print("SỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))
        if PHAT_HIEN:
            print("PHÁT HIỆN ĐO ĐƯỢC (chưa đủ mức chặn gộp — xem docs/QA_G16.md §4):")
            for p in PHAT_HIEN:
                print("  · " + p)


if __name__ == "__main__":
    print("NGƯỠNG CHE BÍ MẬT (http_jt):", getattr(http_jt, "DAI_TOI_THIEU_DE_CHE", "n/a"))
    unittest.main(verbosity=2)
