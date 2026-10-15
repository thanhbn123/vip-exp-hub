# G16 — BỘ THỬ LỚP HTTP THẬT (`app/http_jt.py`) + STUB J&T CỤC BỘ (`app/thu/stub_jt.py`).
#
# PHẠM VI — nói thẳng cái gì NẰM NGOÀI:
#   · Mọi lượt gửi trong tệp này đi tới STUB trên `127.0.0.1` (cổng do hệ điều hành cấp). KHÔNG
#     một lượt nào ra Internet, và điều đó được ÉP BẰNG MÃ: `setUpModule` thay `socket.socket.connect`
#     bằng một chốt chặn chỉ cho loopback đi qua, cộng thêm một máy đếm. Ai đó gõ sai URL trong bất
#     kỳ ca nào thì ca đó HỎNG TO, chứ không thành một lượt gọi ra ngoài.
#   · KHÔNG đo được: hành vi thật của J&T (chữ ký có được chấp nhận không, mã lỗi thật là gì, TLS
#     của hãng, giới hạn hạn mức). V-G09-01/V-13906-05 CHƯA CẤP nên chưa từng có lượt gọi hãng nào.
#     Bộ thử xanh ở đây KHÔNG phải lời cho phép gọi sandbox, và KHÔNG được đọc thành "LIVE VERIFIED".
#   · KHÔNG đo được: thời gian hết giờ thật của hãng. Các ca hết giờ dùng stub ngủ có chủ ý.
#
# HAI CHỐT CHẶN BẮT BUỘC CỦA DỰ ÁN (docs/QA_G13_G15.md §6.3), có ở đây:
#   1. TỰ KIỂM BỘ DÒ (`CaTuKiem`): mỗi bộ dò được ĐỘT BIẾN trong một TIẾN TRÌNH CON — nếu bộ dò
#      hỏng thì ca phải ĐỎ; kèm ĐỐI CHỨNG DƯƠNG (không đột biến ⇒ XANH) để chứng minh đường chạy
#      con không phải "luôn báo hỏng".
#   2. ĐỐI CHỨNG DƯƠNG CHO MỌI CA PHỦ ĐỊNH: mỗi ca "phải bị từ chối / phải ném lỗi" đều đi kèm một
#      khẳng định rằng cửa đó MỞ khi hợp lệ (host thật được nhận, chậm-trong-hạn thì thành công,
#      có kết nối khi host hợp lệ, thân đủ thì trả về nguyên văn…).
import ast
import base64
import contextlib
import datetime as _dt
import hashlib
import http.client
import io
import json
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import unittest
from email.utils import format_datetime
from urllib.parse import parse_qs, quote, quote_plus, urlsplit

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
for _d in (GOC, THU):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402
from stub_jt import HoDenKetNoi, StubJT                                 # noqa: E402

# Bốn "bí mật" GIẢ ĐỊNH, chỉ sống trong tiến trình này. Không có credential thật nào tồn tại
# (SHARED_CONTRACTS §38) — và đây là lý do các ca rò rỉ đo được: ta biết CHÍNH XÁC chuỗi cần tìm.
KHOA_GIA_DINH = "KHOA-RIENG-GIA-DINH-G16-KHONG-PHAI-KHOA-THAT"
ACC_GIA_DINH = "acct-gia-dinh-g16"
TS_GIA_DINH = "1700000000000"
TEN_NGUOI_NHAN = "Nguyễn Văn Ước & Cộng + Hoà"


def chuoi_biz(ten=TEN_NGUOI_NHAN):
    """`bizContent`: CHUỖI JSON (không phải object lồng), dấu cách chỉ nằm trong GIÁ TRỊ.

    `separators=(",", ":")` là cố ý: nhờ nó, mọi dấu `+` trong thân form gửi đi đều đến từ dấu
    cách trong dữ liệu, nên đếm được chính xác (xem ca a2).
    """
    return json.dumps({"txlogisticId": "VEH-G16-0001", "nguoi_nhan": ten},
                      ensure_ascii=False, separators=(",", ":"))


def digest_chuan(biz, khoa=KHOA_GIA_DINH):
    """Công thức ĐỘC LẬP: base64(md5-bytes(bizContent + privateKey)).

    Cố ý KHÔNG import `adapter_jt.ky_digest`: `adapter_jt.py` là tệp của làn AG-03 đang được viết
    đồng thời, import nó là buộc bộ thử của tôi vào một tệp đang sửa. Có ca riêng (d3) canh hai
    chỗ không trôi khỏi nhau, bằng AST.
    """
    return base64.b64encode(hashlib.md5((biz + khoa).encode("utf-8")).digest()).decode()


def headers_chuan(biz, **them):
    h = {"apiAccount": ACC_GIA_DINH, "digest": digest_chuan(biz), "timestamp": TS_GIA_DINH,
         "Content-Type": "application/x-www-form-urlencoded"}
    h.update(them)
    return h


def _dem_ngu(nguon):
    """→ danh sách mô tả các lời gọi NGỦ trong mã nguồn (rỗng = không có lời gọi nào).

    Dò bằng **AST**: `sleep(...)` trần, `time.sleep(...)`, và `…ngu(...)` (tên tham số ngủ của
    `transport.goi`). Chú thích và chuỗi KHÔNG bị tính — đó chính là lý do phải dùng AST: tệp
    `http_jt.py` có câu "KHÔNG BAO GIỜ NGỦ" trong chú thích, grep sẽ báo nhầm.
    """
    try:
        cay = ast.parse(nguon)
    except SyntaxError as e:
        return [f"không phân tích được: {e}"]
    ra = []
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in ("sleep", "ngu"):
            ra.append(f"dòng {n.lineno}: {f.id}()")
        elif isinstance(f, ast.Attribute) and f.attr in ("sleep", "ngu"):
            ra.append(f"dòng {n.lineno}: …{f.attr}()")
    return ra


def _la_loopback(host):
    if not isinstance(host, str):
        return False
    return host == "localhost" or host == "::1" or host.startswith("127.")


class ChanMangNgoai:
    """CHỐT CHẶN MẠNG của cả bộ thử: chỉ loopback được nối ra, và mọi lần nối đều được ĐẾM.

    Không có nó thì một URL gõ sai biến bộ thử thành một lượt gọi ra Internet — và tệ hơn, thành
    một lượt gọi IM LẶNG (không ai đọc log của bộ thử). Nó cũng là máy đếm để chứng minh "TỪ CHỐI
    trước khi mở socket" (ca d1) và "KHÔNG đi theo chuyển hướng" (ca b5).
    """

    def __init__(self):
        self._goc = None
        self.da_noi = []

    def bat(self):
        if self._goc is not None:
            # ĐÃ BẬT ⇒ KHÔNG bọc lần hai. Bọc lần hai thì mỗi lượt nối bị ĐẾM HAI LẦN, và mọi ca đo
            # "số lượt nối" sẽ báo sai gấp đôi. Lỗi này có thật: `chay_con` gọi `setUpModule()` thủ
            # công, rồi `unittest` gọi nó LẦN NỮA khi chạy suite (AG-02 đo được 16 lượt nối cho 8
            # lượt gọi). Bộ đếm là BẰNG CHỨNG, nên nó phải bật được nhiều lần mà vẫn đúng.
            return
        self._goc = socket.socket.connect
        goc = self._goc
        da_noi = self.da_noi

        def connect(sock, dia_chi, *a, **kw):
            host = dia_chi[0] if isinstance(dia_chi, (tuple, list)) and dia_chi else dia_chi
            cong = dia_chi[1] if isinstance(dia_chi, (tuple, list)) and len(dia_chi) > 1 else None
            da_noi.append((host, cong))
            if not _la_loopback(host):
                raise AssertionError(
                    f"CHẶN MẠNG: bộ thử định nối ra {dia_chi!r} — chỉ được loopback. "
                    "Ban G16: không có lượt gọi hãng nào được phép.")
            return goc(sock, dia_chi, *a, **kw)

        socket.socket.connect = connect

    def tat(self):
        if self._goc is not None:
            socket.socket.connect = self._goc
            self._goc = None


CHAN = ChanMangNgoai()


def setUpModule():
    CHAN.bat()


def tearDownModule():
    CHAN.tat()


class CaGoc(unittest.TestCase):
    """Bộ khung chung: mở stub (tự dọn), dựng yêu cầu, chạy tiến trình con."""

    def mo(self, che_do=StubJT.THANH_CONG, **kw):
        stub = StubJT(che_do, **kw)
        self.addCleanup(stub.dung)          # dọn cả khi ca HỎNG (không để lại cổng/tiến trình)
        return stub

    def gui(self, stub, biz=None, timeout=5.0, headers=None, body=None, url=None):
        biz = chuoi_biz() if biz is None else biz
        return http_jt.gui_form(url or stub.url, headers or headers_chuan(biz),
                                body if body is not None else {"bizContent": biz},
                                timeout=timeout)

    def cho_tra_loi(self, stub, so=1, het_gio=3.0):
        """Chờ stub GHI XONG phản hồi rồi mới so `than`.

        Vì sao cần: stub ghi vào `da_tra_loi` SAU khi đã gửi byte đi (đó mới là bản ghi trung thực).
        Nên client có thể nhận đủ thân rồi quay về TRƯỚC khi luồng máy chủ kịp ghi lại. Đã xảy ra
        THẬT ngày 15/10/2026 khi hai bản bộ thử chạy song song: `than_tra_loi_cuoi` là `None` và ca
        đỏ dù mã đúng — đúng khuôn HỎNG GIẢ của N-05. Chờ có hạn, rồi mới khẳng định.
        """
        han = time.time() + het_gio
        while len(stub.da_tra_loi) < so and time.time() < han:
            time.sleep(0.005)
        self.assertGreaterEqual(len(stub.da_tra_loi), so,
                                f"stub chưa ghi nhận phản hồi nào sau {het_gio}s")
        return stub.da_tra_loi[-1]["than"]

    def chay_con(self, ten_ca, dot_bien=""):
        """Chạy MỘT ca trong TIẾN TRÌNH CON, tuỳ chọn tiêm một dòng đột biến trước khi chạy."""
        ma = (
            "import sys, unittest\n"
            f"sys.path.insert(0, {GOC!r})\n"
            f"sys.path.insert(0, {THU!r})\n"
            "import http_jt\n"
            f"{dot_bien}\n"
            "import thu_http_jt\n"
            "thu_http_jt.setUpModule()\n"
            f"ca = unittest.TestLoader().loadTestsFromName({ten_ca!r}, thu_http_jt)\n"
            "kq = unittest.TextTestRunner(verbosity=2).run(ca)\n"
            "thu_http_jt.tearDownModule()\n"
            "raise SystemExit(0 if kq.wasSuccessful() else 1)\n")
        return subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                              timeout=180, cwd=GOC)


# =================================================================================================
# A. GÓI YÊU CẦU: ĐÚNG BYTE, ĐÚNG HEADER, CHỮ KÝ TRÊN CHÍNH CHUỖI ĐÃ GỬI
# =================================================================================================
class CaGoiYeuCau(CaGoc):

    def test_a1_bon_header_bat_buoc_co_mat_dung_ten(self):
        """Ba header tài liệu bắt buộc + Content-Type phải tới nơi, ĐÚNG CHỮ HOA/THƯỜNG và thứ tự."""
        stub = self.mo()
        biz = chuoi_biz()
        h = headers_chuan(biz)
        kq = self.gui(stub, biz, headers=h)

        self.assertEqual(kq.ma_http, 200)
        yc = stub.yeu_cau[-1]
        self.assertEqual(yc.phuong_thuc, "POST")                     # không phải GET
        for ten in ("apiAccount", "digest", "timestamp", "Content-Type"):
            self.assertIn(ten, yc.ten_header, f"thiếu header {ten} trên dây")
        self.assertEqual(yc.header("Content-Type"), "application/x-www-form-urlencoded")
        self.assertEqual(yc.header("apiAccount"), ACC_GIA_DINH)
        self.assertEqual(yc.header("timestamp"), TS_GIA_DINH)
        self.assertEqual([t for t in yc.ten_header if t in h], list(h))   # giữ nguyên thứ tự gọi
        self.assertEqual(yc.duong_dan, "/webopenplatformapi/api/order/addOrder")
        self.assertEqual(stub.so_yeu_cau, 1)                         # ĐÚNG MỘT lượt

    def test_a2_than_form_dung_byte_utf8_va_escaping(self):
        """Thân form: một trường `bizContent`, UTF-8, `&`/`+`/dấu tiếng Việt phải được escape."""
        stub = self.mo()
        biz = chuoi_biz()
        self.gui(stub, biz)
        raw = stub.yeu_cau[-1].than_tho

        self.assertTrue(raw.startswith(b"bizContent="), raw[:40])
        payload = raw[len(b"bizContent="):]
        self.assertEqual(payload.count(b"&"), 0, "có '&' CHƯA escape trong thân")
        self.assertEqual(raw.count(b"+"), 6, "6 dấu cách trong dữ liệu phải thành đúng 6 dấu '+'")
        self.assertNotIn(b" ", raw, "khoảng trắng thô không được có trong thân form")
        self.assertIn(b"%2B", raw, "dấu '+' trong DỮ LIỆU phải thành %2B")
        self.assertIn(b"%26", raw, "dấu '&' trong DỮ LIỆU phải thành %26")
        self.assertIn(b"%C6%AF", raw, "Ư phải là UTF-8 percent-encoded (C6 AF)")
        self.assertIn(b"%E1%BB%9B", raw, "ớ phải là UTF-8 percent-encoded (E1 BB 9B)")
        # Vòng tròn: giải mã thân form mà stub NHẬN ĐƯỢC phải ra ĐÚNG chuỗi đã ký, nguyên dấu.
        self.assertEqual(json.loads(parse_qs(raw.decode("utf-8"))["bizContent"][0]),
                         json.loads(biz))
        self.assertEqual(json.loads(parse_qs(raw.decode("utf-8"))["bizContent"][0])["nguoi_nhan"],
                         TEN_NGUOI_NHAN)
        self.assertEqual(len(parse_qs(raw.decode("utf-8"))), 1, "thân chỉ được có MỘT trường")

        # ĐỐI CHỨNG DƯƠNG của phép đếm: đổi dữ liệu ⇒ số dấu '+' phải ĐỔI (nếu không, phép đếm
        # đang đo một hằng số chứ không đo dữ liệu).
        stub2 = self.mo()
        biz2 = chuoi_biz("Hoà Bình")                                  # đúng MỘT dấu cách
        self.gui(stub2, biz2, headers=headers_chuan(biz2), body={"bizContent": biz2})
        self.assertEqual(stub2.yeu_cau[-1].than_tho.count(b"+"), 1)

    def test_a3_chu_ky_tinh_tren_dung_chuoi_da_gui(self):
        """`digest` phải khớp công thức tính lại từ CHÍNH chuỗi mà stub đã nhận."""
        stub = self.mo()
        biz = chuoi_biz()
        self.gui(stub, biz)
        yc = stub.yeu_cau[-1]
        biz_da_nhan = yc.form_value("bizContent")

        self.assertEqual(biz_da_nhan, biz, "chuỗi đi trên dây phải ĐÚNG BẰNG chuỗi đã ký")
        self.assertEqual(yc.header("digest"), digest_chuan(biz_da_nhan),
                         "chữ ký không khớp chuỗi đã gửi")
        self.assertEqual(len(biz_da_nhan), len(biz))
        self.assertIn(TEN_NGUOI_NHAN, biz_da_nhan)                    # dấu tiếng Việt còn nguyên
        # ĐỐI CHỨNG DƯƠNG: lệch một ký tự là chữ ký KHÁC ⇒ phép so ở trên nhìn thấy được.
        self.assertNotEqual(yc.header("digest"), digest_chuan(biz_da_nhan + " "))
        self.assertNotEqual(yc.header("digest"), digest_chuan(biz_da_nhan, khoa="khoa-khac"))

    def test_a4_than_tra_loi_nguyen_van_va_repr_khong_in_than(self):
        """`TraLoiHTTP.than` là thân THÔ; `repr` KHÔNG được in thân (repr là thứ hay bị đem đi log)."""
        stub = self.mo()
        kq = self.gui(stub)
        self.assertEqual(kq.than, self.cho_tra_loi(stub))
        self.assertEqual(json.loads(kq.than.decode("utf-8"))["code"], "1")
        self.assertIn("Content-Type", kq.headers)
        self.assertNotIn("billCode", repr(kq))
        self.assertNotIn("VH000000001VN", repr(kq))
        self.assertEqual(sorted(kq.__slots__), ["headers", "ma_http", "than"])   # hình dạng §36

    def test_a5_khong_co_content_type_thi_tu_them_dung_chuan_tai_lieu(self):
        """Gọi trực tiếp không kèm Content-Type ⇒ lớp HTTP tự thêm đúng giá trị tài liệu."""
        stub = self.mo()
        biz = chuoi_biz()
        h = headers_chuan(biz)
        h.pop("Content-Type")
        self.gui(stub, biz, headers=h)
        yc = stub.yeu_cau[-1]
        self.assertEqual(yc.header("Content-Type"), "application/x-www-form-urlencoded")
        self.assertEqual(yc.ten_header.count("Content-Type"), 1, "không được gửi Content-Type hai lần")
        # ĐỐI CHỨNG DƯƠNG: khi người gọi ĐÃ đưa Content-Type thì giữ NGUYÊN VĂN, không viết lại.
        stub2 = self.mo()
        h2 = headers_chuan(biz, **{"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"})
        self.gui(stub2, biz, headers=h2)
        self.assertEqual(stub2.yeu_cau[-1].header("Content-Type"),
                         "application/x-www-form-urlencoded; charset=utf-8")

    def test_a6_content_length_do_lop_http_dat_dung_so_byte_that(self):
        stub = self.mo()
        h = headers_chuan(chuoi_biz())
        h["Content-Length"] = "99999"          # người gọi khai SAI: phải bị bỏ, không được tin
        self.gui(stub, headers=h)
        yc = stub.yeu_cau[-1]
        self.assertEqual(int(yc.header("Content-Length")), len(yc.than_tho))
        self.assertNotEqual(int(yc.header("Content-Length")), 99999)


# =================================================================================================
# B. PHÂN LOẠI THEO HTTP + KHÔNG TỰ THỬ LẠI
# =================================================================================================
class CaPhanLoai(CaGoc):

    def test_b1_http_500_la_tam_thoi_va_khong_biet(self):
        stub = self.mo(StubJT.HTTP_500)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub)
        e = ctx.exception
        self.assertEqual(e.loai, "http-5xx")
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_BIET)
        self.assertTrue(e.timeout, "5xx = KHÔNG BIẾT yêu cầu đã được xử lý chưa")
        self.assertEqual(e.ma_http, 500)
        self.assertIn("KHÔNG BIẾT", str(e))
        # Thân 5xx CÓ đi vào thông điệp (đã CHE bí mật và cắt 200 byte) — có chủ ý, để chẩn đoán
        # được lỗi phía hãng. Ca e1 chứng minh bí mật bị che TRƯỚC khi vào đây.
        self.assertIn("Bad Gateway", str(e))
        self.assertEqual(e.so_byte_than, len(b"<html><body>502 Bad Gateway</body></html>"))
        self.assertEqual(stub.so_yeu_cau, 1, "KHÔNG được tự thử lại")

    def test_b2_http_4xx_la_vinh_vien(self):
        stub = self.mo(StubJT.HTTP_400)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub)
        e = ctx.exception
        self.assertEqual(e.loai, "http-4xx")
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_HANG_TU_CHOI)
        self.assertFalse(e.timeout)
        self.assertEqual(e.ma_http, 400)
        self.assertEqual(stub.so_yeu_cau, 1)

    def test_b3_4xx_khac_van_la_vinh_vien(self):
        """ĐỐI CHỨNG ÂM của quyết định 408/429 (AG-00, 15/10/2026): **KHÔNG nới 4xx nào khác**.

        `408`/`429` đã được tách ra (xem `CaGioiHanTanSuat`). Ở đây chốt rằng 400/401/403/404 VẪN
        là `LoiVinhVien`: nếu ai "nới cho chắc" cả nhóm 4xx, ca này ĐỎ.
        """
        for che_do, ma in ((StubJT.HTTP_400, 400), (StubJT.HTTP_401, 401),
                           (StubJT.HTTP_403, 403), (StubJT.HTTP_404, 404)):
            with self.subTest(ma=ma):
                stub = self.mo(che_do)
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    self.gui(stub)
                self.assertEqual(ctx.exception.ma_http, ma)
                self.assertEqual(ctx.exception.loai, "http-4xx")
                self.assertEqual(ctx.exception.ket_cuc, http_jt.KET_CUC_HANG_TU_CHOI)
                self.assertFalse(ctx.exception.timeout)
                self.assertEqual(stub.so_yeu_cau, 1)

    def test_b4_chuyen_huong_khong_duoc_di_theo(self):
        """302 sang host khác: TỪ CHỐI, và máy đếm chứng minh KHÔNG có lượt nối nào tới host đó."""
        stub = self.mo(StubJT.HTTP_302)
        truoc = len(CHAN.da_noi)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            self.gui(stub)
        self.assertEqual(ctx.exception.loai, "http-3xx")
        self.assertEqual(stub.so_yeu_cau, 1)
        for host, _cong in CHAN.da_noi[truoc:]:
            self.assertTrue(_la_loopback(host), f"đã nối ra {host!r} — không được đi theo 302")
        self.assertIn("KHÔNG đi theo chuyển hướng", str(ctx.exception))

    def test_b5_goi_thu_lai_doc_duoc_nhung_khong_thu_lai_ghi(self):
        """LUẬT CỨNG §36.1 đo trên `transport.goi()` THẬT, không phải trên bản mô tả."""
        stub = self.mo(StubJT.HTTP_500)
        stub.xep_hang_doi(StubJT.HTTP_500, StubJT.HTTP_500, StubJT.THANH_CONG)
        biz = chuoi_biz()
        h = headers_chuan(biz)
        nghi = []
        kq, lan, nhat_ky = transport.goi(
            lambda: http_jt.gui_form(stub.url, h, {"bizContent": biz}, timeout=5),
            "trackOrder", ngu=nghi.append)
        self.assertEqual((kq.ma_http, lan), (200, 3))
        self.assertEqual(stub.so_yeu_cau, 3)
        self.assertEqual(nghi, [0.2, 0.4], "backoff phải do `transport.goi()` quyết định")
        self.assertTrue(any("ok" in d for d in nhat_ky))

        # ---- Thao tác GHI: `createOrder` mặc định KHÔNG được thử lại ----
        stub2 = self.mo(StubJT.HTTP_500)
        nghi2 = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(lambda: http_jt.gui_form(stub2.url, h, {"bizContent": biz}, timeout=5),
                          "createOrder", ngu=nghi2.append)
        self.assertEqual(stub2.so_yeu_cau, 1, "createOrder bị thử lại MÙ QUÁNG — nguy cơ tạo đơn trùng")
        self.assertEqual(nghi2, [], "không được chờ backoff cho một thao tác ghi bị chặn")
        self.assertFalse(transport.chinh_sach_cho("createOrder").duoc_thu_lai)
        self.assertEqual(transport.chinh_sach_cho("createOrder").so_lan, 1)
        self.assertTrue(transport.chinh_sach_cho("trackOrder").duoc_thu_lai)

        # `so_lan=3` mà `duoc_thu_lai=False` thì VẪN chỉ 1 lượt: hai tham số tách rời nhau, nên
        # "được thử lại" không thể bị lách bằng cách tăng số lần.
        stub4 = self.mo(StubJT.HTTP_500)
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(lambda: http_jt.gui_form(stub4.url, h, {"bizContent": biz}, timeout=5),
                          "createOrder",
                          chinh_sach=transport.ChinhSach(so_lan=3, duoc_thu_lai=False),
                          ngu=lambda s: None)
        self.assertEqual(stub4.so_yeu_cau, 1)

        # ---- ĐỐI CHỨNG DƯƠNG: có khóa chống trùng `txlogisticId` thì thử lại ĐƯỢC mở ----
        stub3 = self.mo(StubJT.HTTP_500)
        nghi3 = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(lambda: http_jt.gui_form(stub3.url, h, {"bizContent": biz}, timeout=5),
                          "createOrder", co_khoa_chong_trung=True, ngu=nghi3.append)
        self.assertEqual(stub3.so_yeu_cau, 3, "có khóa chống trùng thì chính sách phải mở 3 lượt")
        self.assertEqual(nghi3, [0.2, 0.4])

    def test_b6_goi_khong_thu_lai_khi_4xx(self):
        stub = self.mo(StubJT.HTTP_400)
        biz = chuoi_biz()
        with self.assertRaises(transport.LoiVinhVien):
            transport.goi(lambda: http_jt.gui_form(stub.url, headers_chuan(biz),
                                                   {"bizContent": biz}, timeout=5),
                          "trackOrder", ngu=lambda s: None)
        self.assertEqual(stub.so_yeu_cau, 1, "4xx là vĩnh viễn — không được thử lại")


# =================================================================================================
# B2. 408 / 429 — QUYẾT ĐỊNH CỦA AG-00 (15/10/2026): HAI MÃ NÀY LÀ LỖI TẠM THỜI
# =================================================================================================
class CaGioiHanTanSuat(CaGoc):
    """`429` = bị giới hạn tần suất; `408` = hãng không nhận kịp yêu cầu. Cả hai: hãng NÓI THẲNG
    "thử lại sau" ⇒ `LoiTamThoi`, tách khỏi luật "4xx = vĩnh viễn", và **không nới mã 4xx nào khác**.

    Ba điều kiện đi kèm, mỗi điều có ca riêng:
      · `cho_giay` lấy từ `Retry-After` (giây HOẶC HTTP-date), **kẹp trần `transport.CHO_TOI_DA`**;
      · `gui_form` **KHÔNG BAO GIỜ NGỦ** (soát bằng AST — `test_b11`) — nếu ngủ, `createOrder`
        (`so_lan=3`) sẽ treo 3 × trần trong một yêu cầu HTTP của hệ này;
      · `http_jt` và `loi_hang` phải **ĐỒNG Ý** về hai mã này (`test_b10` — ca canh chống lệch).
    """

    def test_b7_429_la_tam_thoi_va_KHAC_5xx_trong_log(self):
        stub = self.mo(StubJT.HTTP_429)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub)
        e = ctx.exception
        self.assertEqual(e.loai, "http-429")
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_QUA_HAN_MUC)
        self.assertNotEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_BIET, "429 KHÔNG được lẫn với 5xx")
        self.assertNotEqual(e.ket_cuc, http_jt.KET_CUC_HANG_TU_CHOI, "429 không phải hãng từ chối")
        self.assertTrue(getattr(e, "gioi_han_tan_suat", False))
        self.assertEqual(e.ma_http, 429)
        self.assertTrue(e.timeout)
        self.assertIn("GIỚI HẠN TẦN SUẤT", str(e))
        self.assertEqual(stub.so_yeu_cau, 1, "KHÔNG tự thử lại")
        # Không có `Retry-After` ⇒ KHÔNG bịa gợi ý: để `None`, `transport.goi()` dùng backoff chính sách.
        self.assertIsNone(e.cho_giay)
        self.assertFalse(e.retry_after_bi_cat)

    def test_b8_408_la_tam_thoi_nhung_KHAC_429(self):
        stub = self.mo(StubJT.HTTP_408)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub)
        e = ctx.exception
        self.assertEqual(e.loai, "http-408")
        self.assertNotEqual(e.loai, "http-429", "hai mã phải phân biệt được trong log")
        self.assertNotEqual(e.loai, "http-4xx")
        # 408 = hãng KHÔNG NHẬN KỊP ⇒ chắc chắn CHƯA xử lý gì ⇒ thử lại AN TOÀN.
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_GUI_DI)
        self.assertTrue(e.timeout)
        self.assertEqual(e.ma_http, 408)
        self.assertFalse(getattr(e, "gioi_han_tan_suat", False))
        self.assertIsNone(e.cho_giay)
        self.assertEqual(stub.so_yeu_cau, 1)
        # ĐỐI CHỨNG DƯƠNG: cùng stub đó với 400 ⇒ VĨNH VIỄN (nên ca này không phải "mọi thứ đều tạm thời").
        stub2 = self.mo(StubJT.HTTP_400)
        with self.assertRaises(transport.LoiVinhVien):
            self.gui(stub2)

    def test_b9_retry_after_doc_duoc_KEP_TRAN_va_KHONG_ngu(self):
        """Bốn dạng `Retry-After` + một khẳng định về THỜI GIAN: không có lượt nào bị ngủ."""
        # (1) số giây bình thường
        stub = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "5"})
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub)
        self.assertLess(time.time() - t0, 1.0, "gui_form đã NGỦ theo Retry-After")
        self.assertEqual(ctx.exception.cho_giay, 5.0)
        self.assertFalse(ctx.exception.retry_after_bi_cat)

        # (2) số giây khổng lồ ⇒ KẸP TRẦN, và tuyệt đối không ngủ theo hãng
        stub2 = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "86400"})
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx2:
            self.gui(stub2)
        self.assertLess(time.time() - t0, 1.0, "Retry-After: 86400 đã treo tiến trình")
        self.assertEqual(ctx2.exception.cho_giay, transport.CHO_TOI_DA)
        self.assertTrue(ctx2.exception.retry_after_bi_cat)
        self.assertIn("KẸP TRẦN", str(ctx2.exception))

        # (3) HTTP-date (dạng thứ hai của RFC) — đo trong khoảng, không so tuyệt đối
        moc = _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=30)
        stub3 = self.mo(StubJT.HTTP_429,
                        them_header={"Retry-After": format_datetime(moc, usegmt=True)})
        with self.assertRaises(transport.LoiTamThoi) as ctx3:
            self.gui(stub3)
        self.assertIsNotNone(ctx3.exception.cho_giay)
        self.assertGreater(ctx3.exception.cho_giay, 25.0)
        self.assertLess(ctx3.exception.cho_giay, 35.0)
        self.assertFalse(ctx3.exception.retry_after_bi_cat)

        # (4) rác ⇒ không đoán, để `None` (KHÔNG được biến rác thành một con số)
        stub4 = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "khong-phai-so"})
        with self.assertRaises(transport.LoiTamThoi) as ctx4:
            self.gui(stub4)
        self.assertIsNone(ctx4.exception.cho_giay)
        self.assertIn("KHÔNG gửi `Retry-After` đọc được", str(ctx4.exception))

        # (5) mốc đã qua ⇒ 0 giây (không được ra số âm)
        moc_xa = _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(seconds=600)
        stub5 = self.mo(StubJT.HTTP_429,
                        them_header={"Retry-After": format_datetime(moc_xa, usegmt=True)})
        with self.assertRaises(transport.LoiTamThoi) as ctx5:
            self.gui(stub5)
        self.assertEqual(ctx5.exception.cho_giay, 0.0)

        # (6) và 408 cũng đọc `Retry-After` (cùng một đường mã)
        stub6 = self.mo(StubJT.HTTP_408, them_header={"Retry-After": "7"})
        with self.assertRaises(transport.LoiTamThoi) as ctx6:
            self.gui(stub6)
        self.assertEqual(ctx6.exception.cho_giay, 7.0)

    def test_b10_http_jt_va_loi_hang_DONG_Y_ve_408_va_429(self):
        """CA CANH CHỐNG LỆCH — quan trọng nhất trong nhóm này.

        `loi_hang.tu_http()` là bảng phân loại của dự án; `co_the_thu_lai` của nó là thứ Order
        Service đọc. Nếu `http_jt` ném `LoiVinhVien` cho một mã mà `loi_hang` nói "thử lại được",
        hai lớp nói ngược nhau về CÙNG một lượt gửi — đúng khuôn "lệch im lặng".
        """
        import loi_hang                                      # nạp trong ca: `loi_hang` không thuộc làn này

        bang = ((StubJT.HTTP_400, 400), (StubJT.HTTP_401, 401), (StubJT.HTTP_403, 403),
                (StubJT.HTTP_404, 404), (StubJT.HTTP_408, 408), (StubJT.HTTP_429, 429),
                (StubJT.HTTP_500, 500))
        for che_do, ma in bang:
            with self.subTest(ma=ma):
                noi_thu_lai = loi_hang.tu_http(ma).co_the_thu_lai
                stub = self.mo(che_do)
                try:
                    self.gui(stub)
                    self.fail(f"HTTP {ma} mà KHÔNG ném lỗi")
                except transport.LoiTamThoi:
                    toi_noi_thu_lai = True
                except transport.LoiVinhVien:
                    toi_noi_thu_lai = False
                self.assertEqual(
                    toi_noi_thu_lai, noi_thu_lai,
                    f"LỆCH: HTTP {ma} — `loi_hang` nói thử lại={noi_thu_lai}, "
                    f"`http_jt` nói thử lại={toi_noi_thu_lai}")
        # ĐỐI CHỨNG DƯƠNG của chính phép so: bảng phân loại thật sự có CẢ HAI giá trị, nên phép so
        # ở trên không thể đúng một cách vô nghĩa (nếu mọi mã đều "thử lại được" thì ca vô giá trị).
        self.assertTrue(loi_hang.tu_http(429).co_the_thu_lai)
        self.assertTrue(loi_hang.tu_http(408).co_the_thu_lai)
        self.assertFalse(loi_hang.tu_http(400).co_the_thu_lai)
        self.assertFalse(loi_hang.tu_http(404).co_the_thu_lai)
        self.assertTrue(loi_hang.tu_http(500).co_the_thu_lai)

    def test_b11_gui_form_KHONG_BAO_GIO_NGU_soat_bang_AST(self):
        """Soát bằng **AST**, không bằng grep: `gui_form` không được có lời gọi ngủ nào.

        Vì sao phải là AST: grep đọc cả chú thích, và chính tệp này có câu "**KHÔNG BAO GIỜ NGỦ**"
        trong chú thích — grep sẽ báo nhầm (đúng bài học `thu_bien_driver.py` ca a4).
        Vì sao phải chặn: `createOrder` có khoá chống trùng dùng `so_lan=3`; nếu `gui_form` ngủ để
        tôn trọng `Retry-After` thì một yêu cầu HTTP của hệ này treo `3 × trần` giây, và §36 luật 1
        bị phá.
        """
        duong = os.path.join(GOC, "http_jt.py")
        with open(duong, encoding="utf-8") as f:
            nguon = f.read()
        self.assertEqual(_dem_ngu(nguon), [], "`gui_form`/mô-đun có lời gọi NGỦ")
        # Chốt chặn thứ hai, cấu trúc hơn: mô-đun không nạp `time` thì không thể ngủ.
        self.assertNotIn("import time", nguon)
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải BẮT được một `sleep` được tiêm vào — nếu không, ca này xanh
        # vì bộ dò hỏng chứ không vì mã sạch.
        self.assertTrue(_dem_ngu("import time\ndef gui_form():\n    time.sleep(1)\n"))
        self.assertTrue(_dem_ngu("from time import sleep\ndef gui_form():\n    sleep(1)\n"))
        self.assertTrue(_dem_ngu("import transport\ndef gui_form():\n    transport.ngu(1)\n"))
        # ...và KHÔNG báo nhầm khi `sleep` chỉ nằm trong chú thích hoặc trong chuỗi.
        self.assertEqual(_dem_ngu("# KHÔNG BAO GIỜ NGỦ: time.sleep(1)\nx = 1\n"), [])
        self.assertEqual(_dem_ngu('x = "time.sleep(1)"\n'), [])

    def test_b12_cho_giay_toi_duoc_cho_CHO_cua_transport_goi(self):
        """ĐẦU-CUỐI: `cho_giay` của lớp này phải tới được chỗ CHỜ của `transport.goi()`.

        Không có ca này thì hai lớp có thể "đồng ý trên giấy" mà `goi()` vẫn chờ theo backoff 0,2s —
        và `Retry-After` của hãng thành vô nghĩa. `ngu=nghi.append` GHI LẠI thay vì ngủ thật, nên ca
        này đo đúng con số mà `goi()` truyền cho hàm ngủ.
        """
        def mot_luot(stub, biz):
            return lambda: http_jt.gui_form(stub.url, headers_chuan(biz), {"bizContent": biz},
                                            timeout=5)

        biz = chuoi_biz()
        # (1) 429 + Retry-After: 5 ⇒ goi() chờ 5s mỗi lượt (KHÔNG phải 0,2/0,4 của chính sách)
        stub = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "5"})
        nghi = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(mot_luot(stub, biz), "trackOrder", ngu=nghi.append)
        self.assertEqual(stub.so_yeu_cau, 3)
        self.assertEqual(nghi, [5.0, 5.0], "`cho_giay` không tới được chỗ chờ của `goi()`")

        # (2) ĐỐI CHỨNG DƯƠNG: không có gợi ý ⇒ chờ đúng backoff của chính sách (0,2 · 0,4)
        stub2 = self.mo(StubJT.HTTP_500)
        nghi2 = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(mot_luot(stub2, biz), "trackOrder", ngu=nghi2.append)
        self.assertEqual(nghi2, [0.2, 0.4])

        # (3) `Retry-After: 86400` ⇒ KẸP TRẦN, không treo tiến trình
        stub3 = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "86400"})
        nghi3 = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(mot_luot(stub3, biz), "trackOrder", ngu=nghi3.append)
        self.assertEqual(nghi3, [transport.CHO_TOI_DA, transport.CHO_TOI_DA])

        # (4) THAO TÁC GHI: `createOrder` vẫn ĐÚNG MỘT lượt, dù hãng gợi ý chờ — luật §36.1 không đổi
        stub4 = self.mo(StubJT.HTTP_429, them_header={"Retry-After": "5"})
        nghi4 = []
        with self.assertRaises(transport.LoiTamThoi):
            transport.goi(mot_luot(stub4, biz), "createOrder", ngu=nghi4.append)
        self.assertEqual(stub4.so_yeu_cau, 1)
        self.assertEqual(nghi4, [])


# =================================================================================================
# C. HẾT GIỜ / ĐỨT / TỪ CHỐI KẾT NỐI — KẾT CỤC "KHÔNG BIẾT" KHÔNG BAO GIỜ LÀ THÀNH CÔNG
# =================================================================================================
class CaKhongBiet(CaGoc):

    def test_c1_het_gio_doc_bi_chan_dung_han_va_la_khong_biet(self):
        stub = self.mo(StubJT.CHAM, do_tre=1.5)
        biz = chuoi_biz()
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            http_jt.gui_form(stub.url, headers_chuan(biz), {"bizContent": biz}, timeout=0.4)
        qua = time.time() - t0
        e = ctx.exception
        self.assertEqual(e.loai, "het-gio")
        self.assertTrue(e.timeout)
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_BIET)
        self.assertEqual(e.ma_http, 0)
        self.assertIn("KHÔNG BIẾT", str(e))
        self.assertGreaterEqual(qua, 0.35, "chưa chờ đủ hạn — hết giờ giả?")
        self.assertLess(qua, 1.2, "hạn ĐỌC không được ép: đã chờ quá lâu")
        self.assertEqual(stub.so_yeu_cau, 1, "hết giờ KHÔNG được tự gửi lại")

        # ---- ĐỐI CHỨNG DƯƠNG: CÙNG stub chậm đó, hạn đủ rộng thì phải THÀNH CÔNG ----
        stub.dat_che_do(StubJT.CHAM, do_tre=0.4)
        kq = http_jt.gui_form(stub.url, headers_chuan(biz), {"bizContent": biz}, timeout=5)
        self.assertEqual(kq.ma_http, 200)

    def test_c2_than_doc_do_khong_bao_gio_thanh_thanh_cong(self):
        """Ca then chốt: HTTP 200 + `Content-Length` lớn hơn số byte thật ⇒ thân ĐỨT GIỮA CHỪNG.

        Không có ca này thì một bản vá "đọc được bao nhiêu trả bấy nhiêu" sẽ biến một lượt KHÔNG BIẾT
        thành một `TraLoiHTTP` 200 trông y hệt thành công.
        """
        stub = self.mo(StubJT.THAN_THIEU, do_tre=1.5)
        biz = chuoi_biz()
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            http_jt.gui_form(stub.url, headers_chuan(biz), {"bizContent": biz}, timeout=0.4)
        qua = time.time() - t0
        e = ctx.exception
        self.assertEqual(e.loai, "than-doc-do")
        self.assertTrue(e.timeout)
        self.assertTrue(getattr(e, "than_dut", False))
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_BIET)
        self.assertEqual(e.ma_http, 200, "biết mã HTTP, KHÔNG biết nội dung — hai thứ khác nhau")
        self.assertLess(qua, 1.0, "phải hết giờ khi đọc thân, không chờ hết `do_tre`")
        self.assertFalse(hasattr(e, "than"), "không được gắn thân đọc dở vào ngoại lệ")

        # ---- ĐỐI CHỨNG DƯƠNG: thân ĐỦ thì cùng đường đó trả về NGUYÊN VĂN ----
        stub2 = self.mo()
        kq = self.gui(stub2, biz)
        self.assertEqual(kq.than, self.cho_tra_loi(stub2))
        self.assertEqual(json.loads(kq.than.decode("utf-8"))["code"], "1")

    def test_c3_hang_dong_ket_noi_giua_luot_la_khong_biet(self):
        stub = self.mo(StubJT.CAT_KET_NOI)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub)
        e = ctx.exception
        self.assertEqual(e.loai, "ket-noi-dut")
        self.assertTrue(e.timeout)
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_BIET)
        # ĐỐI CHỨNG DƯƠNG: yêu cầu ĐÃ tới nơi (nếu không, đây là ca "chưa gửi được gì", khác hẳn).
        self.assertEqual(stub.so_yeu_cau, 1)

    def test_c4_tu_choi_ket_noi_KHAC_het_gio_va_khac_hang_tu_choi(self):
        """Cổng đóng: biết chắc CHƯA gửi được gì — khác "hết giờ", và KHÁC "hãng từ chối"."""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cong = s.getsockname()[1]
        s.close()
        biz = chuoi_biz()
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            http_jt.gui_form(f"http://127.0.0.1:{cong}/x", headers_chuan(biz),
                             {"bizContent": biz}, timeout=3)
        e = ctx.exception
        self.assertEqual(e.loai, "tu-choi-ket-noi")
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_GUI_DI)
        self.assertLess(time.time() - t0, 2.0, "từ chối kết nối phải trả về NGAY")
        self.assertIn("CHƯA ra khỏi máy", str(e))
        self.assertIn("KHÔNG phải", str(e))          # nói thẳng: đây không phải hãng từ chối
        # ĐỐI CHỨNG DƯƠNG: cùng URL đó, có stub đứng sau thì đi qua được (cổng không phải vấn đề).
        stub = self.mo()
        self.assertEqual(self.gui(stub).ma_http, 200)

    def test_c5_goi_het_gio_thi_thu_lai_duoc_va_bao_khong_biet(self):
        """`transport.goi()` thử lại ca hết giờ, và mỗi lượt vẫn bị hạn của lớp HTTP chặn."""
        stub = self.mo(StubJT.CHAM, do_tre=1.5)
        biz = chuoi_biz()
        cs = transport.ChinhSach(so_lan=2, backoff_goc=0, he_so=1, duoc_thu_lai=True)
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            transport.goi(lambda: http_jt.gui_form(stub.url, headers_chuan(biz),
                                                   {"bizContent": biz}, timeout=0.3),
                          "trackOrder", chinh_sach=cs, ngu=lambda s: None)
        qua = time.time() - t0
        self.assertEqual(stub.so_yeu_cau, 2)
        self.assertTrue(ctx.exception.timeout, "kết cục KHÔNG BIẾT phải đi ra ngoài dưới cờ timeout")
        self.assertLess(qua, 1.3, "hạn của lớp HTTP không được ép cho từng lượt")


# =================================================================================================
# D. DANH SÁCH TRẮNG MÁY CHỦ
# =================================================================================================
class CaDanhSachTrang(CaGoc):

    def test_d1_host_la_bi_tu_choi_TRUOC_khi_mo_socket(self):
        """Host ngoài danh sách trắng: TỪ CHỐI, và máy đếm chứng minh CHƯA hề mở kết nối.

        Dùng `127.0.0.2` (loopback, KHÔNG có gì lắng nghe) làm "host lạ": nó không phân giải ra
        Internet, nên ca này không thể biến thành một lượt gọi ra ngoài dù mã có hỏng thế nào.
        """
        stub = self.mo()
        biz = chuoi_biz()
        url_la = f"http://127.0.0.2:{stub.cong}/webopenplatformapi/api/order/addOrder"
        truoc = len(CHAN.da_noi)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(url_la, headers_chuan(biz), {"bizContent": biz}, timeout=2)
        e = ctx.exception
        self.assertEqual(e.loai, "host-bi-tu-choi")
        self.assertEqual(e.ket_cuc, http_jt.KET_CUC_KHONG_GUI_DI)
        self.assertFalse(e.timeout)
        self.assertIn("không nằm trong danh sách trắng", str(e))
        self.assertEqual(len(CHAN.da_noi), truoc, "đã MỞ SOCKET trước khi kiểm danh sách trắng")
        self.assertEqual(stub.so_yeu_cau, 0)
        # ĐỐI CHỨNG DƯƠNG: cùng stub, host HỢP LỆ ⇒ CÓ mở kết nối (chốt chặn không chặn nhầm tất cả).
        self.assertEqual(self.gui(stub, biz).ma_http, 200)
        self.assertGreater(len(CHAN.da_noi), truoc)
        self.assertTrue(all(_la_loopback(h) for h, _ in CHAN.da_noi[truoc:]))

    def test_d2_host_na_duoi_hang_that_bi_tu_choi(self):
        """So KHỚP CHÍNH XÁC, không so chuỗi con — và host hãng chỉ nhận https:443."""
        xau = ["demoopenapi.jtexpress.vn.ke-tan-cong.example",
               "ke-tan-cong.example",
               "ylopenapi.jtexpress.vn.evil",
               "jtexpress.vn",
               "127.0.0.1.ke-tan-cong.example"]
        for h in xau:
            with self.subTest(host=h):
                self.assertFalse(http_jt.host_duoc_phep(h))
                with self.assertRaises(transport.LoiVinhVien):
                    http_jt.tach_url(f"https://{h}/webopenplatformapi/api/order/addOrder")
        # ĐỐI CHỨNG DƯƠNG: đúng hai host hãng thì ĐƯỢC NHẬN (nếu không, hàm đang từ chối tất cả).
        for h in http_jt.HOST_HANG:
            self.assertTrue(http_jt.host_duoc_phep(h))
            self.assertEqual(http_jt.tach_url(f"https://{h}/x")[1], h)
        # host hãng: cấm http (credentials ra ngoài bằng kênh không mã hoá) và cấm cổng lạ.
        for url in ("http://demoopenapi.jtexpress.vn/x", "https://demoopenapi.jtexpress.vn:8443/x"):
            with self.subTest(url=url):
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    http_jt.tach_url(url)
                self.assertEqual(ctx.exception.loai, "url-sai")

    def test_d3_hai_host_hang_khong_troi_khoi_adapter_jt_va_loi_duong_dan_sai(self):
        """Canh lệch bằng AST (không import `adapter_jt` — tệp của làn AG-03, đang được viết)."""
        duong = os.path.join(GOC, "adapter_jt.py")
        try:
            with open(duong, encoding="utf-8") as f:
                cay = ast.parse(f.read())
        except (OSError, SyntaxError) as ex:
            self.skipTest(f"adapter_jt.py chưa đọc được bằng AST (làn AG-03 đang ghi): {ex}")
        host_api = None
        for n in ast.walk(cay):
            if isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "HOST_API" for t in n.targets):
                host_api = ast.literal_eval(n.value)
        self.assertIsNotNone(host_api, "không thấy HOST_API trong adapter_jt.py")
        # `HOST_API` của adapter giữ URL ĐẦY ĐỦ; `http_jt.HOST_HANG` giữ TÊN MÁY CHỦ. So phần tên.
        ten_trong_adapter = {urlsplit(u).hostname for u in host_api.values()}
        self.assertEqual(ten_trong_adapter, set(http_jt.HOST_HANG),
                         "hai host J&T trong `http_jt` đã trôi khỏi `adapter_jt.HOST_API`")
        for h in ten_trong_adapter:
            self.assertTrue(http_jt.host_duoc_phep(h))           # ĐỐI CHỨNG DƯƠNG
        # Bốn TÊN trường credentials (§38) cũng phải khớp — chép tên mà không canh là chỗ trôi im lặng.
        truong = None
        for n in ast.walk(cay):
            if isinstance(n, ast.Assign) and any(
                    getattr(t, "id", None) == "TRUONG_CREDENTIAL" for t in n.targets):
                truong = ast.literal_eval(n.value)
        self.assertIsNotNone(truong, "không thấy TRUONG_CREDENTIAL trong adapter_jt.py")
        self.assertEqual({t.lower() for t in truong}, set(http_jt.TRUONG_CREDENTIAL),
                         "tên trường credential trong `http_jt` đã trôi khỏi `adapter_jt`")
        # URL hỏng đủ kiểu: từ chối HẾT, và không cái nào chạm tới mạng.
        truoc = len(CHAN.da_noi)
        for url in ("", "   ", "khong-phai-url", "ftp://127.0.0.1/x", "http:///x",
                    "https://user:matkhau@127.0.0.1/x", "http://127.0.0.1/x#neo",
                    "http://127.0.0.1:khong-phai-so/x", "http://127.0.0.1/x y"):
            with self.subTest(url=url):
                with self.assertRaises(transport.LoiVinhVien):
                    http_jt.tach_url(url)
        self.assertEqual(len(CHAN.da_noi), truoc)
        # ĐỐI CHỨNG DƯƠNG: một URL hợp lệ đi qua được.
        self.assertEqual(http_jt.tach_url("http://127.0.0.1:8080/x")[3], "/x")

    def test_d4_tham_so_sai_bi_chan_truoc_khi_gui(self):
        stub = self.mo()
        biz = chuoi_biz()
        h = headers_chuan(biz)
        for timeout in (0, -1, None, float("nan"), float("inf"), "5", True):
            with self.subTest(timeout=timeout):
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    http_jt.gui_form(stub.url, h, {"bizContent": biz}, timeout=timeout)
                self.assertEqual(ctx.exception.loai, "tham-so-sai")
        for body in (None, {}, {"bizContent": None}, {"bizContent": b"x"}, {"bizContent": {"a": 1}}):
            with self.subTest(body=body):
                with self.assertRaises(transport.LoiVinhVien):
                    http_jt.gui_form(stub.url, h, body, timeout=2)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, {"digest": "abc\r\nX-Chen: 1"}, {"bizContent": biz}, timeout=2)
        self.assertIn("chèn header", str(ctx.exception))
        self.assertNotIn("abc", str(ctx.exception), "giá trị header KHÔNG được vào thông điệp")
        self.assertEqual(stub.so_yeu_cau, 0, "tham số sai mà vẫn có lượt gửi đi")
        # ĐỐI CHỨNG DƯƠNG: cùng stub, tham số ĐÚNG ⇒ gửi được.
        self.assertEqual(self.gui(stub, biz).ma_http, 200)
        self.assertEqual(stub.so_yeu_cau, 1)


# =================================================================================================
# E. BÍ MẬT KHÔNG ĐƯỢC RÒ RA NGOẠI LỆ / LOG / repr
# =================================================================================================
class CaBiMat(CaGoc):

    def test_e1_khong_ro_bi_mat_ra_ngoai_le_log_repr(self):
        """Máy chủ ECHO LẠI header + thân + digest vào cả thân và header phản hồi.

        ĐỐI CHỨNG DƯƠNG đặt TRƯỚC mọi khẳng định phủ định: phải chứng minh rằng bí mật THẬT SỰ đã
        đi trên dây và THẬT SỰ bị echo lại — nếu không, các khẳng định "không thấy bí mật" đúng một
        cách vô nghĩa (chẳng có gì để rò).
        """
        stub = self.mo(StubJT.DOI_DAU)
        biz = chuoi_biz()
        h = headers_chuan(biz)
        ra, rong = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(ra), contextlib.redirect_stderr(rong):
            with self.assertRaises(transport.LoiVinhVien) as ctx:
                http_jt.gui_form(stub.url, h, {"bizContent": biz}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub)

        # (1) ĐỐI CHỨNG DƯƠNG: digest ĐÃ đi trên dây, và hãng ĐÃ echo nó lại.
        yc = stub.yeu_cau[-1]
        self.assertEqual(yc.header("digest"), h["digest"])
        self.assertIn(h["digest"].encode("utf-8"), than_that, "stub không echo digest — ca vô nghĩa")
        self.assertIn(ACC_GIA_DINH.encode("utf-8"), than_that)

        # (2) Bí mật KHÔNG được có trong thông điệp, args, hay bất kỳ luồng ra nào.
        for bi_mat in (h["digest"], ACC_GIA_DINH, KHOA_GIA_DINH, "VEH-G16-0001", TEN_NGUOI_NHAN):
            for noi, chuoi in (("str(e)", str(e)), ("repr(e)", repr(e)), ("e.args", str(e.args)),
                               ("stdout", ra.getvalue()), ("stderr", rong.getvalue())):
                self.assertNotIn(bi_mat, chuoi, f"RÒ RỈ {bi_mat!r} trong {noi}")

        # (3) Thân/header gắn vào NGOẠI LỆ đã được CHE, và có dấu vết rằng đã che.
        self.assertNotIn(h["digest"], e.than_da_che.decode("utf-8", "replace"))
        self.assertNotIn(ACC_GIA_DINH, e.than_da_che.decode("utf-8", "replace"))
        self.assertNotIn("VEH-G16-0001", e.than_da_che.decode("utf-8", "replace"))
        self.assertIn("[DA-CHE]", e.than_da_che.decode("utf-8", "replace"))
        self.assertEqual(e.headers_da_che.get("X-Digest-Echo"), "[DA-CHE]")
        self.assertGreater(e.so_byte_than, 0)

        # (4) Phép che là của TÔI, không phải của stub: thân thô vẫn còn nguyên bí mật.
        self.assertIn(h["digest"].encode("utf-8"), than_that)

    def test_e3_credential_NGAN_hon_nguong_van_bi_che(self):
        """ĐO ĐÚNG CÁI BIÊN mà bộ QA độc lập AG-01 đã đo (`thu_qa_g16.t18b`): credential NGẮN.

        Canary 5 ký tự đặt ở header `apiAccount` VÀ ở `bizContent.password`. Ngưỡng 8 ký tự bỏ sót cả
        hai đường; nên giá trị của bốn trường credential nay bị che BẤT KỂ ĐỘ DÀI (`TRUONG_CREDENTIAL`).
        """
        ngan = "aB3$9"
        self.assertLess(len(ngan), http_jt.DAI_TOI_THIEU_DE_CHE)
        stub = self.mo(StubJT.DOI_DAU)
        biz = json.dumps({"txlogisticId": "VEH-G16-0009", "password": ngan},
                         ensure_ascii=False, separators=(",", ":"))
        h = {"apiAccount": ngan, "digest": digest_chuan(biz), "timestamp": TS_GIA_DINH}
        ra, rong = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(ra), contextlib.redirect_stderr(rong):
            with self.assertRaises(transport.LoiVinhVien) as ctx:
                http_jt.gui_form(stub.url, h, {"bizContent": biz}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub)

        # ĐỐI CHỨNG DƯƠNG: canary THẬT SỰ đi trên dây và THẬT SỰ bị echo lại.
        self.assertEqual(stub.yeu_cau[-1].header("apiAccount"), ngan)
        self.assertIn(ngan.encode("utf-8"), than_that, "stub không echo canary — ca vô nghĩa")
        for noi, chuoi in (("str(e)", str(e)), ("repr(e)", repr(e)), ("e.args", str(e.args)),
                           ("than_da_che", e.than_da_che.decode("utf-8", "replace")),
                           ("headers_da_che", str(e.headers_da_che)),
                           ("stdout", ra.getvalue()), ("stderr", rong.getvalue())):
            self.assertNotIn(ngan, chuoi, f"RÒ RỈ credential NGẮN trong {noi}")

        # ĐỐI CHỨNG DƯƠNG thứ hai: phép CHỌN giá trị đáng che vẫn phân biệt hai mức — giá trị 5 ký tự
        # KHÔNG thuộc trường credential thì KHÔNG bị che (ngưỡng còn tác dụng; nếu không, thông điệp
        # chẩn đoán sẽ bị che vô tội vạ).
        self.assertIn(ngan, http_jt._gia_tri_can_che({"apiAccount": ngan}, b"x=1"))
        self.assertNotIn("VH12", http_jt._gia_tri_can_che({"X-Ma-Don": "VH12"}, b"x=1"))
        self.assertIn("VH123456", http_jt._gia_tri_can_che({"X-Ma-Don": "VH123456"}, b"x=1"))
        self.assertIn(ngan, http_jt._gia_tri_can_che({}, http_jt._ma_hoa_form({"bizContent": biz})))

    def test_e2_repr_va_thong_diep_chi_neu_TEN_khong_neu_gia_tri(self):
        stub = self.mo()
        biz = chuoi_biz()
        kq = self.gui(stub, biz)
        for bi_mat in (KHOA_GIA_DINH, ACC_GIA_DINH, "VEH-G16-0001"):
            self.assertNotIn(bi_mat, repr(kq))
        # Thông điệp lỗi chỉ nêu TÊN header (đối chứng dương: tên thì CÓ, giá trị thì KHÔNG).
        stub2 = self.mo(StubJT.HTTP_500)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub2, biz)
        self.assertIn("digest", str(ctx.exception))
        self.assertIn("apiAccount", str(ctx.exception))
        self.assertNotIn(headers_chuan(biz)["digest"], str(ctx.exception))
        self.assertNotIn(ACC_GIA_DINH, str(ctx.exception))
        self.assertNotIn("billCode", str(ctx.exception))


# =================================================================================================
# F. BA KẾT CỤC KHÔNG GỘP (§4) — đo trên lớp HTTP, không đo trên bản mô tả
# =================================================================================================
class CaBaKetCuc(CaGoc):

    def test_f1_ok_va_hang_tu_choi_duoc_phan_biet_bang_code_trong_than_nguyen_van(self):
        """Lớp HTTP KHÔNG phán ok/từ chối — nó trả thân nguyên văn, `code` là việc của adapter."""
        stub_ok = self.mo()
        kq_ok = self.gui(stub_ok)
        goi_ok = json.loads(kq_ok.than.decode("utf-8"))
        self.assertEqual((kq_ok.ma_http, goi_ok["code"]), (200, "1"))

        stub_tc = self.mo(StubJT.HANG_TU_CHOI)
        kq_tc = self.gui(stub_tc)
        goi_tc = json.loads(kq_tc.than.decode("utf-8"))
        self.assertEqual(kq_tc.ma_http, 200, "hãng từ chối vẫn là HTTP 200 — thân mới nói lên điều đó")
        self.assertNotEqual(goi_tc["code"], "1")
        self.assertTrue(goi_tc["msg"])
        # Hai kết cục KHÁC NHAU, phân biệt được bằng máy, và cả hai đều là thân NGUYÊN VĂN.
        self.assertNotEqual(kq_ok.than, kq_tc.than)
        self.assertEqual(kq_tc.than, self.cho_tra_loi(stub_tc))

    def test_f2_ket_cuc_thu_ba_khong_bao_gio_tra_ve_TraLoiHTTP(self):
        """Hết giờ / đứt / thân đọc dở ⇒ NÉM. Không có `TraLoiHTTP` nào để người gọi tưởng là xong."""
        for che_do, kw in ((StubJT.CHAM, {"do_tre": 1.5}), (StubJT.CAT_KET_NOI, {}),
                           (StubJT.THAN_THIEU, {"do_tre": 1.5})):
            with self.subTest(che_do=che_do):
                stub = self.mo(che_do, **kw)
                with self.assertRaises(transport.LoiTamThoi) as ctx:
                    self.gui(stub, timeout=0.4)
                self.assertTrue(ctx.exception.timeout)
                self.assertFalse(isinstance(ctx.exception, http_jt.TraLoiHTTP))
                self.assertIn(ctx.exception.ket_cuc, (http_jt.KET_CUC_KHONG_BIET,
                                                       http_jt.KET_CUC_KHONG_GUI_DI))
        # ĐỐI CHỨNG DƯƠNG: cùng ba chế độ đó, chế độ THÀNH CÔNG trả về đúng một `TraLoiHTTP` 2xx.
        stub = self.mo()
        kq = self.gui(stub)
        self.assertIsInstance(kq, http_jt.TraLoiHTTP)
        self.assertTrue(200 <= kq.ma_http <= 299)


# =================================================================================================
# G. TỰ KIỂM BỘ DÒ — ĐỘT BIẾN TRONG TIẾN TRÌNH CON (docs/QA_G13_G15.md §6.3 luật 1)
# =================================================================================================
class CaTuKiem(CaGoc):
    """Mỗi bộ dò phải chứng minh nó BẮT ĐƯỢC, bằng cách phá chính nó rồi chạy lại trong tiến trình
    con. Kèm ĐỐI CHỨNG DƯƠNG: không phá thì phải XANH — nếu không, một bộ chạy con "luôn báo hỏng"
    cũng làm các ca dưới đây xanh một cách vô nghĩa."""

    CA_DANH_SACH_TRANG = "CaDanhSachTrang.test_d1_host_la_bi_tu_choi_TRUOC_khi_mo_socket"
    CA_BI_MAT = "CaBiMat.test_e1_khong_ro_bi_mat_ra_ngoai_le_log_repr"

    def _kiem(self, ten_ca, dot_bien):
        p = self.chay_con(ten_ca, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_g1_bo_do_danh_sach_trang_bat_duoc_khi_bi_pha(self):
        p, out = self._kiem(self.CA_DANH_SACH_TRANG, "http_jt.host_duoc_phep = lambda host: True")
        self.assertNotEqual(p.returncode, 0, f"phá danh sách trắng mà bộ thử vẫn XANH!\n{out[-2000:]}")
        self.assertTrue("FAIL" in out or "ERROR" in out, out[-2000:])
        # ĐỐI CHỨNG DƯƠNG: không phá ⇒ XANH.
        p2, out2 = self._kiem(self.CA_DANH_SACH_TRANG, "")
        self.assertEqual(p2.returncode, 0, f"ca d1 hỏng cả khi KHÔNG đột biến:\n{out2[-2000:]}")
        self.assertIn("OK", out2)

    def test_g2_bo_do_che_bi_mat_bat_duoc_khi_bi_pha(self):
        p, out = self._kiem(self.CA_BI_MAT, "http_jt.che_bi_mat = lambda du_lieu, can_che: du_lieu")
        self.assertNotEqual(p.returncode, 0, f"tắt phép che mà bộ thử vẫn XANH!\n{out[-2000:]}")
        self.assertTrue("FAIL" in out or "ERROR" in out, out[-2000:])
        p2, out2 = self._kiem(self.CA_BI_MAT, "")
        self.assertEqual(p2.returncode, 0, f"ca e1 hỏng cả khi KHÔNG đột biến:\n{out2[-2000:]}")
        self.assertIn("OK", out2)

    def test_g3_bo_do_thong_diep_bat_duoc_khi_bi_pha(self):
        """Bộ dò thứ ba: chính hàm DỰNG THÔNG ĐIỆP. Nếu nó in giá trị header ra, ca e1 phải ĐỎ."""
        p, out = self._kiem(
            self.CA_BI_MAT,
            "http_jt.mo_ta_yeu_cau = lambda url, headers, than: repr(dict(headers))")
        self.assertNotEqual(p.returncode, 0,
                            f"thông điệp lỗi in cả giá trị header mà bộ thử vẫn XANH!\n{out[-2000:]}")
        self.assertTrue("FAIL" in out or "ERROR" in out, out[-2000:])

    def test_g4_chot_chan_mang_cua_CHINH_bo_thu_hoat_dong(self):
        """Tự kiểm chốt chặn mạng: nối ra host ngoài phải BỊ CHẶN, nối loopback phải đi qua."""
        s = socket.socket()
        try:
            with self.assertRaises(AssertionError) as ctx:
                s.connect(("vi-du.example.com", 80))
            self.assertIn("CHẶN MẠNG", str(ctx.exception))
        finally:
            s.close()
        s2 = socket.socket()
        tam = socket.socket()
        tam.bind(("127.0.0.1", 0))
        cong_dong = tam.getsockname()[1]        # cổng vừa đóng: chắc chắn không có ai nghe
        tam.close()
        try:
            with self.assertRaises(OSError):
                s2.connect(("127.0.0.1", cong_dong))   # loopback: ĐI QUA chốt chặn, rồi hỏng vì cổng đóng
        finally:
            s2.close()
        self.assertTrue(any(h == "vi-du.example.com" for h, _ in CHAN.da_noi))


# =================================================================================================
# H. §37 — MÔI TRƯỜNG: MOCK MỞ, SANDBOX/PRODUCTION TỪ CHỐI KÈM LÝ DO
# =================================================================================================
class CaMoiTruong(CaGoc):

    def test_h1_mock_mo_con_sandbox_va_production_tu_choi(self):
        http_jt.chan_moi_truong(http_jt.MOCK)                      # ĐỐI CHỨNG DƯƠNG: không chặn tất cả
        for mt, ma in ((http_jt.SANDBOX, "V-G09-01"), (http_jt.PRODUCTION, None)):
            with self.subTest(moi_truong=mt):
                with self.assertRaises(PermissionError) as ctx:
                    http_jt.chan_moi_truong(mt)
                self.assertIn("TỪ CHỐI", str(ctx.exception))
                if ma:
                    self.assertIn(ma, str(ctx.exception))
                    self.assertIn("V-13906-05", str(ctx.exception))
        self.assertFalse(http_jt.CHO_PHEP_MOI_TRUONG[http_jt.SANDBOX])
        self.assertFalse(http_jt.CHO_PHEP_MOI_TRUONG[http_jt.PRODUCTION])
        self.assertEqual((http_jt.MOCK, http_jt.SANDBOX, http_jt.PRODUCTION),
                         ("mock", "sandbox", "production"))


# =================================================================================================
# I. ĐA LUỒNG / NHIỀU KẾT NỐI CÙNG LÚC — lỗ hổng #4 của `docs/G16_ACCEPTANCE.md` §8
#
# "Đa luồng trên `http_jt` — bộ thử chạy tuần tự." Mục này ĐO nó. Mọi lượt gửi vẫn chỉ đi tới stub
# trên `127.0.0.1` (cổng do hệ điều hành cấp), dưới đúng chốt chặn mạng của tệp này.
# =================================================================================================
def _fd_dang_mo():
    """→ số file descriptor đang mở của tiến trình này, hoặc `None` nếu hệ điều hành không cho đọc."""
    for d in ("/dev/fd", "/proc/self/fd"):
        try:
            return len(os.listdir(d))
        except OSError:
            continue
    return None


def _cho_fd_on_dinh(han=3.0):
    """Chờ số fd ĐỨNG YÊN rồi mới đo — luồng máy chủ của stub cần vài chục ms để dọn socket."""
    truoc = _fd_dang_mo()
    if truoc is None:
        return None
    het_han = time.time() + han
    while time.time() < het_han:
        time.sleep(0.05)
        sau = _fd_dang_mo()
        if sau == truoc:
            return sau
        truoc = sau
    return truoc


def chay_song_song(so_luong, ham):
    """Chạy `ham(i)` trong `so_luong` luồng THẬT → (kết quả, lỗi, số giây).

    Lỗi được GIỮ LẠI theo từng luồng chứ không nuốt: một ca đa luồng phải phân biệt được "luồng này
    hỏng" với "không có gì chạy". Bắt cả `BaseException` vì một khẳng định sai trong luồng cũng phải
    nổi lên thành ca ĐỎ, không được biến mất.
    """
    kq = [None] * so_luong
    loi = [None] * so_luong

    def _boc(i):
        try:
            kq[i] = ham(i)
        except BaseException as e:          # noqa: BLE001 — cố ý: giữ mọi thứ để ca thử phán
            loi[i] = e

    ths = [threading.Thread(target=_boc, args=(i,), name=f"thu-g17-{i}") for i in range(so_luong)]
    t0 = time.perf_counter()
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    return kq, loi, time.perf_counter() - t0


class CaDongThoi(CaGoc):
    """ĐA LUỒNG / NHIỀU KẾT NỐI CÙNG LÚC.

    ĐO ĐƯỢC (AG-02, 15/10/2026, macOS · Python 3.9.6):
      · Lớp HTTP KHÔNG giữ trạng thái dùng chung nào giữa các lượt gọi (không pool, không khoá, không
        biến toàn cục bị ghi) ⇒ 24 luồng chạy SONG SONG THẬT, không lẫn dữ liệu.
      · RÀNG BUỘC ĐO ĐƯỢC: MỘT kết nối TCP cho MỘT lượt gọi, mở rồi đóng, KHÔNG dùng lại. Trần đồng
        thời của lớp này vì vậy là trần file descriptor của tiến trình, không phải một con số của
        chính nó — không có giới hạn N lượt gọi đồng thời nào ở đây (việc hãm nằm ở lớp khác).
      · KHÔNG phụ thuộc `socket.setdefaulttimeout()` toàn cục: hạn luôn được truyền tường minh, và
        lớp này cũng KHÔNG đổi mặc định toàn cục của tiến trình.
    """

    SO_LUONG = 24

    def test_i1_N_luong_dong_thoi_khong_lan_du_lieu_va_chay_SONG_SONG_that(self):
        stub = self.mo(StubJT.VONG_LAP, do_tre=0.25)

        def mot(i):
            dau = f"VEH-G17-{i:04d}"
            biz = json.dumps({"txlogisticId": dau, "ghiChu": "luong-%02d" % i},
                             separators=(",", ":"))
            kq = http_jt.gui_form(stub.url,
                                  {"apiAccount": "acc-%04d" % i, "timestamp": TS_GIA_DINH},
                                  {"bizContent": biz}, timeout=10)
            return i, dau, kq

        kq, loi, giay = chay_song_song(self.SO_LUONG, mot)
        self.assertEqual([e for e in loi if e], [], "có luồng hỏng")
        self.assertEqual(stub.so_yeu_cau, self.SO_LUONG)
        for i, dau, r in kq:
            self.assertEqual(r.ma_http, 200)
            than = r.than.decode("utf-8")
            self.assertIn(dau, than, f"luồng {i} KHÔNG nhận được dấu vết của chính nó")
            self.assertIn("acc-%04d" % i, than)
            for j in range(self.SO_LUONG):
                if j != i:
                    self.assertNotIn(f"VEH-G17-{j:04d}", than,
                                     f"LẪN DỮ LIỆU: luồng {i} nhận thân của luồng {j}")
        # SONG SONG THẬT — hai đường đo độc lập: số yêu cầu chồng nhau ở stub, và tổng thời gian.
        self.assertGreaterEqual(
            stub.cao_nhat_dang_xu_ly, 4,
            "mọi lượt bị TUẦN TỰ HOÁ: cao nhất chỉ %d yêu cầu cùng lúc" % stub.cao_nhat_dang_xu_ly)
        self.assertLess(giay, self.SO_LUONG * 0.25 / 2,
                        "tổng thời gian gần bằng chạy tuần tự ⇒ không song song")
        # ĐỐI CHỨNG DƯƠNG: cùng stub đó, chạy TUẦN TỰ 6 lượt ⇒ phải THẤY khác biệt (cao nhất = 1 và
        # thời gian ≈ 6 × độ trễ). Không có đối chứng này thì "cao nhất ≥ 4" có thể chỉ là hằng số.
        stub2 = self.mo(StubJT.VONG_LAP, do_tre=0.25)
        t0 = time.perf_counter()
        for _ in range(6):
            http_jt.gui_form(stub2.url, {"apiAccount": "acc-tuan-tu"}, {"bizContent": "{}"},
                             timeout=10)
        self.assertEqual(stub2.cao_nhat_dang_xu_ly, 1)
        self.assertGreater(time.perf_counter() - t0, 6 * 0.25 * 0.8)

    def test_i2_MOT_ket_noi_TCP_cho_MOT_luot_goi_KHONG_co_pool(self):
        n = 12
        stub = self.mo(StubJT.VONG_LAP, do_tre=0)
        kq, loi, _ = chay_song_song(n, lambda i: http_jt.gui_form(
            stub.url, {"apiAccount": "acc-%02d" % i}, {"bizContent": "{}"}, timeout=10))
        self.assertEqual([e for e in loi if e], [])
        self.assertEqual([r for r in kq if r is None], [])
        self.assertEqual(stub.so_ket_noi, n,
                         "%d lượt gọi nhưng %d kết nối TCP ⇒ có dùng lại kết nối"
                         % (n, stub.so_ket_noi))
        # ĐỐI CHỨNG DƯƠNG cho CHÍNH máy đếm: dùng lại MỘT kết nối cho 3 yêu cầu ⇒ máy đếm chỉ thấy
        # THÊM 1. Không có đối chứng này thì "12 lượt = 12 kết nối" có thể chỉ là "máy đếm đếm yêu cầu".
        kn = http.client.HTTPConnection(stub.host, stub.cong, timeout=5)
        try:
            for _ in range(3):
                kn.request("POST", "/webopenplatformapi/api/order/addOrder",
                           body=b"bizContent=%7B%7D",
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
                kn.getresponse().read()
        finally:
            kn.close()
        self.assertEqual(stub.so_ket_noi, n + 1, "máy đếm không đếm KẾT NỐI mà đếm yêu cầu")
        self.assertEqual(stub.so_yeu_cau, n + 3)
        # CHI PHÍ ĐO ĐƯỢC: mỗi lượt đang bay giữ MỘT fd; gọi xong phải TRẢ LẠI HẾT.
        truoc = _cho_fd_on_dinh()
        for _ in range(20):
            http_jt.gui_form(stub.url, {"apiAccount": "acc-tuan-tu"}, {"bizContent": "{}"},
                             timeout=10)
        sau = _cho_fd_on_dinh()
        if truoc is not None and sau is not None:
            self.assertLessEqual(sau, truoc + 1, f"fd rò dần: {truoc} → {sau} sau 20 lượt gọi")

    def test_i3_timeout_toan_cuc_KHONG_anh_huong_va_KHONG_bi_doi(self):
        truoc = socket.getdefaulttimeout()
        self.addCleanup(socket.setdefaulttimeout, truoc)
        socket.setdefaulttimeout(30.0)          # "ai đó" đặt mặc định toàn cục RẤT lớn
        stub = self.mo(StubJT.CHAM, do_tre=1.5)

        def mot(i):
            return http_jt.gui_form(stub.url, {"apiAccount": "acc-%02d" % i},
                                    {"bizContent": "{}"}, timeout=0.3)

        kq, loi, giay = chay_song_song(6, mot)
        self.assertEqual([r for r in kq if r is not None], [],
                         "có lượt THÀNH CÔNG dù hạn của nó là 0,3s")
        for e in loi:
            self.assertIsInstance(e, transport.LoiTamThoi)
            self.assertTrue(e.timeout)
        self.assertLess(giay, 2.0,
                        "hạn 0,3s mà mất %.2fs ⇒ đã nghe theo mặc định toàn cục 30s" % giay)
        # (a) `http_jt` KHÔNG được ĐỔI mặc định toàn cục của tiến trình (nó không sở hữu biến đó).
        self.assertEqual(socket.getdefaulttimeout(), 30.0)
        # ĐỐI CHỨNG DƯƠNG: cùng mặc định toàn cục đó, máy chủ trả lời NHANH ⇒ gọi được bình thường.
        nhanh = self.mo()
        self.assertEqual(http_jt.gui_form(nhanh.url, {"apiAccount": "acc-ok"},
                                          {"bizContent": "{}"}, timeout=5).ma_http, 200)
        self.assertEqual(socket.getdefaulttimeout(), 30.0)
        # (b) ĐỔI mặc định toàn cục NGAY TRONG LÚC các lượt gọi đang bay ⇒ vẫn không ảnh hưởng.
        stub2 = self.mo(StubJT.CHAM, do_tre=1.2)
        dung = threading.Event()

        def doi_lien_tuc():
            i = 0
            while not dung.is_set():
                socket.setdefaulttimeout(0.001 if i % 2 else 45.0)
                i += 1
                time.sleep(0.002)

        t = threading.Thread(target=doi_lien_tuc, daemon=True)
        t.start()
        try:
            kq2, loi2, giay2 = chay_song_song(4, lambda i: http_jt.gui_form(
                stub2.url, {"apiAccount": "acc-%02d" % i}, {"bizContent": "{}"}, timeout=0.35))
        finally:
            dung.set()
            t.join(timeout=2)
            socket.setdefaulttimeout(truoc)
        self.assertEqual([r for r in kq2 if r is not None], [])
        self.assertLess(giay2, 1.5)

    def test_i4_chot_chan_mang_bat_duoc_TRONG_luong_va_so_lan_noi_bang_so_luot(self):
        truoc = len(CHAN.da_noi)
        stub = self.mo()
        kq, loi, _ = chay_song_song(8, lambda i: http_jt.gui_form(
            stub.url, {"apiAccount": "acc-%02d" % i}, {"bizContent": "{}"}, timeout=5))
        self.assertEqual([e for e in loi if e], [])
        self.assertEqual([r for r in kq if r is None], [])
        self.assertEqual(len(CHAN.da_noi) - truoc, 8, "số lượt nối THẬT khác số lượt gọi")
        for host, _cong in CHAN.da_noi[truoc:]:
            self.assertTrue(_la_loopback(host), f"có lượt nối ra {host!r} — ngoài loopback")
        # ĐỐI CHỨNG ÂM, TRONG LUỒNG: host ngoài danh sách trắng ⇒ LoiVinhVien, và KHÔNG lượt nối nào.
        truoc2 = len(CHAN.da_noi)
        stub2 = self.mo()
        kq2, loi2, _ = chay_song_song(3, lambda i: http_jt.gui_form(
            f"http://ke-tan-cong-{i}.example/webopenplatformapi/api/order/addOrder",
            {"apiAccount": "acc-x"}, {"bizContent": "{}"}, timeout=5))
        self.assertEqual([r for r in kq2 if r is not None], [])
        for e in loi2:
            self.assertIsInstance(e, transport.LoiVinhVien)
            # So với CHUỖI LITERAL, không so với hằng số của sản phẩm: so với hằng số thì một đột
            # biến `KET_CUC_KHONG_GUI_DI = KET_CUC_KHONG_BIET` sẽ làm khẳng định đúng một cách vô
            # nghĩa (`CaTuKiemG17` đo chính điều đó).
            self.assertEqual(e.ket_cuc, "khong-gui-di")
        self.assertEqual(len(CHAN.da_noi), truoc2, "host bị chặn mà vẫn có lượt nối")
        # ĐỐI CHỨNG DƯƠNG: cùng lúc đó, host loopback ĐI QUA chốt chặn và gọi được.
        self.assertEqual(self.gui(stub2).ma_http, 200)


# =================================================================================================
# K. HAI TẦNG HẠN THỜI GIAN: NỐI và ĐỌC
# =================================================================================================
class CaHetGioNhieuTang(CaGoc):
    """TÁCH RÕ hết giờ KẾT NỐI và hết giờ ĐỌC — đo cả hai bằng stub chậm + hố đen TCP loopback.

    ĐO ĐƯỢC (AG-02, 15/10/2026):
      · Hạn NỐI = `min(timeout, HET_GIO_KET_NOI_TOI_DA = 5.0)`. Hố đen + `timeout=0.3` ⇒ ném sau
        0,30s; CÙNG hố đen + `timeout=7` ⇒ ném sau 5,00s (đúng trần 5,0 — không phải 7).
      · Hạn ĐỌC = `timeout`, KHÔNG bị trần 5,0 kẹp: stub ngủ 5,4s + `timeout=7` ⇒ THÀNH CÔNG.
      · Ba kết cục KHÁC NHAU, không gộp: hết giờ NỐI ⇒ `khong-gui-di` (chưa byte nào ra khỏi máy,
        thử lại AN TOÀN); hết giờ ĐỌC ⇒ `khong-biet` (yêu cầu ĐÃ đi, hãng có thể đã xử lý).
      · Treo KHÔNG BAO GIỜ được đọc thành công — kể cả khi đã nhận được dòng trạng thái 200.
    """

    def _ho_den(self):
        h = HoDenKetNoi()
        self.addCleanup(h.dung)
        return h

    def test_k1_het_gio_KET_NOI_do_duoc_va_PHAN_LOAI_la_khong_gui_di(self):
        h = self._ho_den()
        t0 = time.perf_counter()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(h, timeout=0.3, url=h.url)
        giay = time.perf_counter() - t0
        e = ctx.exception
        self.assertEqual(e.loai, "het-gio")
        self.assertTrue(e.timeout, "hết giờ mà `timeout=False` ⇒ người gọi tưởng BIẾT kết quả")
        # CHUỖI LITERAL (không so với hằng số của sản phẩm — xem ghi chú ở ca i4).
        self.assertEqual(e.ket_cuc, "khong-gui-di",
                         "hết giờ NỐI nghĩa là CHƯA có byte nào ra khỏi máy — phải là khong-gui-di")
        self.assertGreaterEqual(giay, 0.2, "trả về quá nhanh: hạn nối CHƯA được ÁP")
        self.assertLess(giay, 1.5, "hạn nối 0,3s mà mất %.2fs" % giay)
        # ĐỐI CHỨNG DƯƠNG: cùng hạn 0,3s, một máy chủ SỐNG trả lời kịp ⇒ 0,3s là đủ, không phải "mọi
        # thứ đều hết giờ".
        stub = self.mo()
        t0 = time.perf_counter()
        self.assertEqual(self.gui(stub, timeout=0.3).ma_http, 200)
        self.assertLess(time.perf_counter() - t0, 0.3)

    def test_k2_het_gio_DOC_do_duoc_va_PHAN_LOAI_la_khong_biet(self):
        stub = self.mo(StubJT.CHAM, do_tre=1.5)
        t0 = time.perf_counter()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub, timeout=0.35)
        giay = time.perf_counter() - t0
        e = ctx.exception
        self.assertEqual(e.loai, "het-gio")
        self.assertTrue(e.timeout)
        self.assertEqual(e.ket_cuc, "khong-biet",
                         "hết giờ ĐỌC: yêu cầu ĐÃ đi ⇒ KHÔNG BIẾT, không được gộp với khong-gui-di")
        self.assertGreaterEqual(giay, 0.3)
        self.assertLess(giay, 1.2, "hạn đọc 0,35s mà mất %.2fs" % giay)
        self.assertEqual(stub.so_yeu_cau, 1, "yêu cầu chưa ra khỏi máy ⇒ ca này đo sai chỗ")
        # ĐỐI CHỨNG DƯƠNG: cùng stub đó, hạn đủ rộng ⇒ THÀNH CÔNG với thân đúng.
        stub2 = self.mo(StubJT.CHAM, do_tre=1.5)
        t0 = time.perf_counter()
        kq = self.gui(stub2, timeout=4)
        self.assertEqual(kq.ma_http, 200)
        self.assertIn("billCode", kq.than.decode("utf-8"))
        self.assertGreaterEqual(time.perf_counter() - t0, 1.4)

    def test_k3_han_NOI_bi_KEP_TRAN_5s_du_nguoi_goi_xin_7s(self):
        """Trần `HET_GIO_KET_NOI_TOI_DA` — đo bằng hố đen thật, KHÔNG monkeypatch hằng số."""
        self.assertEqual(http_jt.HET_GIO_KET_NOI_TOI_DA, 5.0)
        h = self._ho_den()
        t0 = time.perf_counter()
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(h, timeout=7.0, url=h.url)
        giay = time.perf_counter() - t0
        self.assertEqual(ctx.exception.loai, "het-gio")
        self.assertGreaterEqual(giay, 4.5, "hạn nối phải là trần 5,0s; đo được %.2fs" % giay)
        self.assertLess(giay, 6.5, "vượt cả hạn người gọi (7s): %.2fs" % giay)

    def test_k4_han_DOC_KHONG_bi_tran_NOI_5s_kep(self):
        """Chậm hơn trần NỐI (5s) mà vẫn trong hạn ĐỌC ⇒ PHẢI thành công. Hai tầng TÁCH RỜI."""
        stub = self.mo(StubJT.CHAM, do_tre=5.4)
        t0 = time.perf_counter()
        kq = self.gui(stub, timeout=7.0)
        giay = time.perf_counter() - t0
        self.assertEqual(kq.ma_http, 200)
        self.assertIn("billCode", kq.than.decode("utf-8"))
        self.assertGreaterEqual(giay, 5.0, "chưa chậm hơn trần nối thì ca này không đo được gì")
        self.assertLess(giay, 7.0)

    def test_k5_treo_KHONG_BAO_GIO_duoc_doc_thanh_cong(self):
        """Bốn hình dạng TREO, kể cả "đã nhận HTTP 200 rồi mới treo giữa thân"."""
        for che_do, kw, loai_mong_doi in (
                (StubJT.CHAM, {"do_tre": 1.2}, "het-gio"),
                (StubJT.THAN_THIEU, {"do_tre": 1.2}, "than-doc-do"),
                (StubJT.CAT_KET_NOI, {}, "ket-noi-dut"),
                (StubJT.NHO_GIO, {"do_tre": 0.9, "so_byte_nho": 6}, "than-doc-do")):
            with self.subTest(che_do=che_do):
                stub = self.mo(che_do, **kw)
                with self.assertRaises(transport.LoiTamThoi) as ctx:
                    self.gui(stub, timeout=0.5)
                e = ctx.exception
                self.assertFalse(isinstance(e, http_jt.TraLoiHTTP))
                self.assertTrue(e.timeout)
                self.assertEqual(e.loai, loai_mong_doi)
                if loai_mong_doi == "than-doc-do":
                    self.assertTrue(getattr(e, "than_dut", False),
                                    "thân đọc dở mà không có dấu `than_dut`")
                    self.assertEqual(e.ket_cuc, "khong-biet")
                # Thân ĐỌC DỞ không được xuất hiện ở bất kỳ luồng ra nào: `billCode` chỉ có trong
                # thân của lượt 200 (đã nhận một phần) — nó KHÔNG được đi tiếp.
                for noi, chuoi in (("str(e)", str(e)), ("repr(e)", repr(e)),
                                   ("than_da_che",
                                    getattr(e, "than_da_che", b"").decode("utf-8", "replace"))):
                    self.assertNotIn("billCode", chuoi, f"thân đọc dở đi vào {noi}")
        # ĐỐI CHỨNG DƯƠNG: cùng bốn chế độ đó, chế độ THÀNH CÔNG trả về đúng một `TraLoiHTTP`.
        stub = self.mo()
        kq = self.gui(stub, timeout=3)
        self.assertIsInstance(kq, http_jt.TraLoiHTTP)
        self.assertIn("billCode", kq.than.decode("utf-8"))

    def test_k6_nho_gio_GHI_LAI_GIOI_HAN_timeout_la_han_TUNG_LAN_DOC(self):
        """GIỚI HẠN ĐÃ BIẾT (không phải "đạt"): `timeout` KHÔNG phải hạn TỔNG của lượt gọi.

        `http.client` đặt hạn lên TỪNG lần đọc socket. Máy chủ gửi một byte mỗi 0,2s (nhỏ hơn
        `timeout=0.6`) giữ được lượt gọi 1,2s — lâu hơn `timeout` gấp đôi — mà vẫn trả về thân TRỌN
        VẸN. Ca này GHÉP CẶP hai chiều để phép đo có nghĩa, và khẳng định điều quan trọng nhất: thân
        trả về vẫn TRỌN VẸN, không có thân đọc dở nào được coi là thành công.
        """
        stub = self.mo(StubJT.NHO_GIO, do_tre=0.2, so_byte_nho=6)
        t0 = time.perf_counter()
        kq = self.gui(stub, timeout=0.6)
        giay = time.perf_counter() - t0
        self.assertEqual(kq.ma_http, 200)
        self.assertGreater(giay, 0.6, "chưa vượt hạn đọc thì ca này không đo được giới hạn")
        self.assertIn("billCode", kq.than.decode("utf-8"))
        self.assertEqual(kq.than, self.cho_tra_loi(stub), "thân trả về phải TRỌN VẸN và nguyên văn")
        # CHIỀU NGƯỢC LẠI: khe giữa hai byte LỚN HƠN hạn đọc ⇒ hết giờ NGAY GIỮA thân của HTTP 200,
        # và KHÔNG có `TraLoiHTTP` nào đi ra.
        stub2 = self.mo(StubJT.NHO_GIO, do_tre=0.9, so_byte_nho=6)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub2, timeout=0.5)
        self.assertEqual(ctx.exception.loai, "than-doc-do")
        self.assertEqual(ctx.exception.ket_cuc, "khong-biet")


# =================================================================================================
# J. CỔNG CHE BÍ MẬT, MỞ RỘNG — bốn đường mà G16 chưa phủ
# =================================================================================================
def cac_dang(s):
    """MỌI dạng mà `s` có thể mang trên dây / trong JSON — TÍNH ĐỘC LẬP với mã sản phẩm.

    Cố ý KHÔNG gọi `http_jt._bien_the`: nếu bộ thử lấy chính hàm của sản phẩm để quyết định "phải
    tìm những dạng nào" thì nó chỉ đang tự kiểm chính nó. Đây là bản cài thứ HAI, viết từ mô tả giao
    thức: percent-encoding của form (`urlencode`) và escape ASCII của JSON.
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


class CaBiMatMoRong(CaGoc):
    """BỐN ĐƯỜNG RÒ mà cổng che bí mật của G16 chưa phủ (AG-02 mở rộng, 15/10/2026).

    Mỗi ca đều có ĐỐI CHỨNG DƯƠNG trước mọi khẳng định phủ định: bí mật phải THẬT SỰ đi trên dây và
    THẬT SỰ bị máy chủ echo lại — nếu không thì "không thấy bí mật" đúng một cách vô nghĩa.
    """

    def _khung_chan_doan(self, stub, h=None, body=None):
        """Thông điệp lỗi của một lượt KHÔNG có bí mật — mốc để kiểm khung chẩn đoán."""
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, h or {"apiAccount": ACC_GIA_DINH},
                             body or {"bizContent": chuoi_biz()}, timeout=5)
        return str(ctx.exception)

    def _khong_lot(self, e, bi_mat, ghi_chu=""):
        """Khẳng định `bi_mat` — ở MỌI dạng nó có thể mang — không có trong luồng ra nào."""
        for dang in cac_dang(bi_mat):
            for noi, chuoi in (
                    ("str(e)", str(e)), ("repr(e)", repr(e)), ("e.args", str(e.args)),
                    ("than_da_che", getattr(e, "than_da_che", b"").decode("utf-8", "replace")),
                    ("headers_da_che", str(getattr(e, "headers_da_che", {}))),
                    ("__context__", str(getattr(e, "__context__", None))),
                    ("traceback", "".join(traceback.format_exception(
                        type(e), e, getattr(e, "__traceback__", None))))):
                self.assertNotIn(dang, chuoi, f"RÒ RỈ {dang!r} trong {noi} {ghi_chu}")

    def test_j1_bi_mat_NGAN_1_den_5_ky_tu_o_HEADER_va_o_THAN_deu_bi_che(self):
        """(a) Bí mật NGẮN 1–5 ký tự, ở CẢ HAI đường: header và thân form.

        Ngưỡng độ dài 8 của G16 bỏ sót cả bốn giá trị dưới đây; mức theo TÊN trường credential mới
        che được chúng. `a%b` còn kiểm luôn dạng percent-encode (`a%25b`) — xem `j3`.
        """
        ngan1 = "j"          # 1 ký tự
        ngan3 = "a%b"        # 3 ký tự, có ký tự bị percent-encode trên dây
        ngan5 = "aB?cd"      # 5 ký tự
        ngan_u = "ộ"         # 1 ký tự, KHÔNG phải ASCII (chỉ đi được trong THÂN, UTF-8)
        for s in (ngan1, ngan3, ngan5, ngan_u):
            self.assertLessEqual(len(s), 5)
            self.assertLess(len(s), http_jt.DAI_TOI_THIEU_DE_CHE)
        biz = json.dumps({"txlogisticId": "VEH-G17-0001", "password": ngan_u},
                         ensure_ascii=False, separators=(",", ":"))
        h = {"apiAccount": ngan1, "customerCode": ngan5, "digest": digest_chuan(biz),
             "timestamp": TS_GIA_DINH}
        stub = self.mo(StubJT.DOI_DAU_LAP, so_lan_echo=2)
        # TIỀN ĐỀ CỦA CHÍNH BỘ DÒ: bí mật 1 ký tự chỉ đo được nếu ký tự đó KHÔNG có sẵn trong khung
        # chẩn đoán ("quyền", "byte", số byte, tên header…). Không kiểm tiền đề thì ca này báo HỎNG
        # GIẢ, và một HỎNG GIẢ ở cổng an toàn còn tệ hơn không có cổng.
        khung = self._khung_chan_doan(
            stub,
            {"apiAccount": "acc-0001", "customerCode": "cust-0001", "digest": "D" * 24,
             "timestamp": TS_GIA_DINH},
            {"bizContent": json.dumps({"txlogisticId": "VEH-G17-0001", "password": "mat-khau-thuong"},
                                      separators=(",", ":")), "password": "mat-khau-thuong"})
        for s in (ngan1, ngan_u):
            self.assertNotIn(s, khung,
                             f"khung chẩn đoán đã chứa {s!r} ⇒ ca này sẽ HỎNG GIẢ; đổi ký tự")
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, h, {"bizContent": biz, "password": ngan3}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub, so=2).decode("utf-8", "replace")
        # ĐỐI CHỨNG DƯƠNG: cả bốn bí mật THẬT SỰ đi trên dây và THẬT SỰ bị echo lại (hai dạng).
        for s in (ngan1, ngan3, ngan5, ngan_u):
            self.assertIn(s, than_that, f"{s!r} không có trong thân echo ⇒ ca vô nghĩa")
        self.assertIn(quote_plus(ngan3, safe=""), than_that, "dạng trên dây của `a%b` không có mặt")
        self.assertIn(quote_plus(ngan_u, safe=""), than_that, "dạng trên dây của `ộ` không có mặt")
        for s in (ngan1, ngan3, ngan5, ngan_u):
            self._khong_lot(e, s, "(bí mật ngắn)")
        self.assertIn("[DA-CHE]", e.than_da_che.decode("utf-8", "replace"))

    def test_j2_bi_mat_o_HEADER_va_o_THAN_voi_TEN_khong_phai_credential(self):
        """(b) Bí mật đủ dài nhưng nằm ở TÊN trường KHÔNG thuộc danh sách credential.

        Đây là mặt còn lại của ngưỡng: mức theo TÊN không được thay thế mức theo ĐỘ DÀI.
        """
        stub = self.mo(StubJT.DOI_DAU_LAP, so_lan_echo=2)
        biz = json.dumps({"txlogisticId": "VEH-G17-0002", "ghiChu": "GHI-CHU-BI-MAT-0123456789"},
                         separators=(",", ":"))
        h = {"apiAccount": ACC_GIA_DINH, "digest": digest_chuan(biz), "timestamp": TS_GIA_DINH,
             "X-Ma-Noi-Bo": "TOKEN-NOI-BO-0123456789"}
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, h,
                             {"bizContent": biz, "maNoiBo": "TRUONG-NOI-BO-0123456789"}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub).decode("utf-8", "replace")
        for bi_mat in ("TOKEN-NOI-BO-0123456789", "GHI-CHU-BI-MAT-0123456789",
                       "TRUONG-NOI-BO-0123456789", ACC_GIA_DINH, h["digest"], "VEH-G17-0002"):
            self.assertIn(bi_mat, than_that, f"{bi_mat!r} không được echo ⇒ ca vô nghĩa")
            self._khong_lot(e, bi_mat, "(tên không phải credential)")
        # ĐỐI CHỨNG DƯƠNG cho NGƯỠNG: giá trị NGẮN không thuộc trường credential thì KHÔNG bị che —
        # nếu không, thông điệp chẩn đoán bị che vô tội vạ và người trực không đọc được gì.
        self.assertIn("VH123456", http_jt._gia_tri_can_che({"X-Ma-Don": "VH123456"}, b"x=1"))
        self.assertNotIn("VH12", http_jt._gia_tri_can_che({"X-Ma-Don": "VH12"}, b"x=1"))

    def test_j3_bien_the_TREN_DAY_percent_encoding_va_JSON_escape_khong_lot(self):
        """ĐO ĐƯỢC TRƯỚC KHI VÁ — lỗ hổng NẶNG NHẤT của cổng che G16.

        Phép che so khớp chuỗi GỐC trong Python; hãng echo lại BYTE TRÊN DÂY, đã percent-encode (và
        với JSON `ensure_ascii=True` thì escape thêm một lớp). Đo được trước khi vá: `aB?cd&e=f` ở
        `bizContent.password` RÒ nguyên văn dạng `aB%3Fcd%26e%3Df` trong `than_da_che`.
        """
        stub = self.mo(StubJT.DOI_DAU_LAP, so_lan_echo=2, json_ascii=True)
        mat = "aB?cd&e=f"
        mat_u = "mật-khẩu-Ư-2026"
        biz = json.dumps({"txlogisticId": "VEH-G17-0003", "password": mat_u},
                         ensure_ascii=True, separators=(",", ":"))
        h = {"apiAccount": ACC_GIA_DINH, "digest": digest_chuan(biz), "timestamp": TS_GIA_DINH}
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, h, {"bizContent": biz, "password": mat}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub).decode("utf-8", "replace")
        # ĐỐI CHỨNG DƯƠNG: ĐÚNG những dạng đã từng rò nay phải CÓ trong thân echo.
        for nhan, dang in (("percent-encode (trường form phẳng)", quote_plus(mat, safe="")),
                           ("JSON escape rồi percent-encode (JSON lồng)",
                            quote_plus(json.dumps(mat_u, ensure_ascii=True)[1:-1], safe=""))):
            self.assertIn(dang, than_that, f"{nhan}: {dang!r} không có trong thân echo ⇒ ca vô nghĩa")
        self._khong_lot(e, mat, "(dạng trên dây)")
        self._khong_lot(e, mat_u, "(JSON escape ASCII)")

    def test_j4_hang_DOP_LAI_nhieu_lan_trong_than_van_bi_che_HET(self):
        """(c) Bí mật bị DỚP LẶP nhiều lần trong thân phản hồi: phép che phải thay HẾT, không chỉ lần đầu."""
        stub = self.mo(StubJT.DOI_DAU_LAP, so_lan_echo=3)
        mat = "DOP-LAI-BI-MAT-0123456789"
        biz = chuoi_biz()
        h = {"apiAccount": ACC_GIA_DINH, "digest": digest_chuan(biz), "timestamp": TS_GIA_DINH,
             "X-Lap": mat}
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.url, h, {"bizContent": biz}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub).decode("utf-8", "replace")
        so_lan = than_that.count(mat)
        self.assertGreaterEqual(so_lan, 3,
                                "bí mật chỉ xuất hiện %d lần ⇒ ca không đo được DỚP LẶP" % so_lan)
        che = e.than_da_che.decode("utf-8", "replace")
        self.assertEqual(che.count(mat), 0, f"còn {che.count(mat)} bản sao CHƯA bị che")
        self.assertGreaterEqual(che.count("[DA-CHE]"), so_lan)

    def test_j5_bi_mat_o_QUERY_cua_URL_khong_lot(self):
        """Bí mật đi trong QUERY của URL: nó RA NGOÀI thật, nên nó cũng phải được che."""
        token = "BI-MAT-QUERY-0123456789"
        stub = self.mo(StubJT.DOI_DAU_LAP, so_lan_echo=2)
        url = stub.url_cho(f"/webopenplatformapi/api/order/addOrder?tk={token}")
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(url, {"apiAccount": ACC_GIA_DINH, "timestamp": TS_GIA_DINH},
                             {"bizContent": chuoi_biz()}, timeout=5)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub).decode("utf-8", "replace")
        self.assertIn(token, than_that, "stub không echo dòng yêu cầu ⇒ ca vô nghĩa")
        self._khong_lot(e, token, "(query của URL)")
        # ĐỐI CHỨNG DƯƠNG: tham số query NGẮN (< ngưỡng, tên không phải credential) KHÔNG bị che ⇒
        # thông điệp chẩn đoán còn đọc được; ngưỡng không bị phá.
        self.assertNotIn("trang", http_jt._gia_tri_can_che({}, b"x=1", stub.url_cho("/a?trang=2")))
        self.assertIn(token, http_jt._gia_tri_can_che({}, b"x=1", url))

    def test_j6_bi_mat_o_VI_TRI_TEN_khong_bi_in_ra_trong_thong_diep(self):
        """(d) Bí mật nằm NHẦM ở vị trí TÊN header/trường form — nó không được vào thông điệp lỗi."""
        mat = "MAT KHAU BI MAT 0123456789"        # có dấu cách ⇒ tên header không hợp lệ
        stub = self.mo()
        for nhan, headers, body in (
                ("header", {mat: "x"}, {"bizContent": chuoi_biz()}),
                # Tên trường form chỉ "không hợp lệ" khi KHÔNG phải chuỗi (hoặc rỗng) — nên ca này
                # dùng đúng dạng đó: một GIÁ TRỊ bị đặt nhầm vào vị trí tên.
                ("trường form", {"apiAccount": ACC_GIA_DINH}, {(mat,): "x"})):
            with self.subTest(vi_tri=nhan):
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    http_jt.gui_form(stub.url, headers, body, timeout=5)
                e = ctx.exception
                self.assertEqual(e.loai, "tham-so-sai")
                self.assertNotIn(mat, str(e), f"RÒ RỈ giá trị ở vị trí TÊN ({nhan})")
                self.assertNotIn(mat, repr(e))
                self.assertNotIn(mat, str(getattr(e, "header", "")))
                self.assertNotIn(mat, str(getattr(e, "truong", "")))
        self.assertEqual(stub.so_yeu_cau, 0, "tên sai mà vẫn có lượt gửi đi")
        # ĐỐI CHỨNG DƯƠNG: TÊN HỢP LỆ vẫn được nêu NGUYÊN VĂN — chẩn đoán không mất thông tin.
        self.assertEqual(http_jt._mo_ta_ten("apiAccount"), "apiAccount")
        with self.assertRaises(transport.LoiVinhVien) as ctx2:
            http_jt.gui_form(stub.url, {"digest": "abc\r\nX-Chen: 1"}, {"bizContent": chuoi_biz()},
                             timeout=5)
        self.assertIn("digest", str(ctx2.exception))
        self.assertNotIn("abc", str(ctx2.exception))

    def test_j7_ngoai_le_THO_khong_con_voi_toi_duoc_tu_ngoai_le_da_che(self):
        """(d) Ngoại lệ THÔ của thư viện (`IncompleteRead`) mang theo thân đọc dở CHỨA BÍ MẬT.

        `from None` chỉ che phần in ra; ngoại lệ thô vẫn nối được qua `__context__` — và một bộ ghi
        log đi theo chuỗi ngoại lệ sẽ đọc tới nó. Lớp này ném ngoại lệ ĐÃ CHE ở NGOÀI khối `except`,
        nên `__context__` là `None`.
        """
        mat = "BI-MAT-THAN-DOC-DO-0123456789"
        stub = self.mo(StubJT.THAN_THIEU, do_tre=0.05, ma_van_don=mat)
        with self.assertRaises(transport.LoiTamThoi) as ctx:
            self.gui(stub, timeout=2)
        e = ctx.exception
        than_that = self.cho_tra_loi(stub)
        self.assertIn(mat.encode("utf-8"), than_that,
                      "thân đọc dở không chứa bí mật ⇒ ca vô nghĩa")
        self.assertEqual(e.loai, "than-doc-do")
        self.assertNotIn(mat, str(e))
        self.assertIsNone(e.__context__,
                          "ngoại lệ THÔ còn nối được ⇒ bộ ghi log đi theo `__context__` sẽ đọc tới nó")
        self._khong_lot(e, mat, "(ngoại lệ thô)")

    def test_j8_URL_hong_nem_LoiVinhVien_chu_khong_phai_ValueError_tran(self):
        """ĐO ĐƯỢC TRƯỚC KHI VÁ: `urlsplit` ném `ValueError` TRẦN ra ngoài `tach_url`.

        `transport.goi()` chỉ bắt `LoiTamThoi`/`LoiVinhVien` ⇒ một `ValueError` trần nổi lên tận Order
        Service như lỗi 500. Và URL chứa ký tự điều khiển làm `http.client` ném `InvalidURL` MANG THEO
        CẢ URL — tức mang theo bí mật nằm trong query. Nay lớp này chặn TRƯỚC khi mở socket.
        """
        stub = self.mo()
        for url in ("http://[abc/webopenplatformapi", "http://[::1:80/x"):
            with self.subTest(url=url):
                with self.assertRaises(transport.LoiVinhVien) as ctx:
                    http_jt.gui_form(url, {"apiAccount": ACC_GIA_DINH}, {"bizContent": "{}"},
                                     timeout=2)
                self.assertEqual(ctx.exception.loai, "url-sai")
                self.assertEqual(ctx.exception.ket_cuc, "khong-gui-di")
        mat = "BI-MAT-TRONG-QUERY-0123456789"
        truoc = len(CHAN.da_noi)
        with self.assertRaises(transport.LoiVinhVien) as ctx:
            http_jt.gui_form(stub.goc + "/x?tk=" + mat + "\x01", {"apiAccount": ACC_GIA_DINH},
                             {"bizContent": "{}"}, timeout=2)
        self.assertNotIn(mat, str(ctx.exception))
        self.assertEqual(len(CHAN.da_noi), truoc, "URL bị từ chối mà vẫn mở socket")
        # ĐỐI CHỨNG DƯƠNG: URL HỢP LỆ vẫn đi qua và gọi được — cổng chặn không chặn nhầm.
        self.assertEqual(self.gui(stub).ma_http, 200)


# =================================================================================================
# L. TỰ KIỂM BỘ DÒ CỦA G17 — ĐỘT BIẾN MÃ SẢN PHẨM TRONG TIẾN TRÌNH CON
# =================================================================================================
class CaTuKiemG17(CaGoc):
    """TỰ KIỂM BỘ DÒ (`docs/QA_G13_G15.md` §6.3 luật 1) cho MỌI ca mới của G17.

    Cách làm: ĐỘT BIẾN MÃ SẢN PHẨM rồi chạy lại ĐÚNG ca đó trong một TIẾN TRÌNH CON; ca phải ĐỎ.
    Mỗi dòng dưới đây là một HỒI QUY CÓ THẬT (một cách sửa sai người sau rất dễ mắc), không phải
    một phép đột biến cho vui.

    ĐỐI CHỨNG DƯƠNG: mỗi LỚP ca được chạy NGUYÊN VẸN, KHÔNG đột biến, trong tiến trình con và phải
    XANH — nếu không thì "đột biến làm ca đỏ" không chứng minh được gì, vì một bộ chạy con luôn-đỏ
    cũng làm mọi dòng dưới đây "đạt".

    CHI PHÍ: mỗi dòng là một tiến trình Python mới (~0,7s) cộng thời gian ca; hai ca đo hạn thời
    gian thật (k3, k4) tốn ~5s mỗi lượt. Đây là giá của việc có BẰNG CHỨNG thay vì có lời khai.
    """

    # (tên ca, mã đột biến, vì sao đột biến đó là một hồi quy có thật)
    CA = (
        ("CaDongThoi.test_i1_N_luong_dong_thoi_khong_lan_du_lieu_va_chay_SONG_SONG_that",
         "import threading as _th\n"
         "_goc_gui = http_jt.gui_form\n"
         "_khoa = _th.Lock()\n"
         "def _tuan_tu(*a, **k):\n"
         "    with _khoa:\n"
         "        return _goc_gui(*a, **k)\n"
         "http_jt.gui_form = _tuan_tu",
         "ai đó thêm một khoá toàn cục quanh mọi lượt gọi ⇒ 24 luồng bị TUẦN TỰ HOÁ"),
        ("CaDongThoi.test_i2_MOT_ket_noi_TCP_cho_MOT_luot_goi_KHONG_co_pool",
         "_dung_chung = {}\n"
         "_goc_mkn = http_jt._mo_ket_noi\n"
         "def _mot_ket_noi(s, h, c, t):\n"
         "    k = (s, h, c)\n"
         "    if k not in _dung_chung:\n"
         "        kn = _goc_mkn(s, h, c, t)\n"
         "        kn.connect()\n"
         "        _dung_chung[k] = kn\n"
         "    return _dung_chung[k]\n"
         "http_jt._mo_ket_noi = _mot_ket_noi\n"
         "http_jt._dong = lambda k: None\n"
         "import http.client as _hc\n"
         "_hc.HTTPConnection.connect = lambda self: None",
         "ai đó thêm một 'pool' MỘT kết nối dùng chung, không khoá ⇒ 12 luồng chung 1 socket"),
        ("CaDongThoi.test_i3_timeout_toan_cuc_KHONG_anh_huong_va_KHONG_bi_doi",
         "_goc_mkn = http_jt._mo_ket_noi\n"
         "def _mkn_doi_mac_dinh(s, h, c, t):\n"
         "    __import__('socket').setdefaulttimeout(7.0)\n"
         "    return _goc_mkn(s, h, c, t)\n"
         "http_jt._mo_ket_noi = _mkn_doi_mac_dinh",
         "lớp HTTP ĐỔI mặc định timeout TOÀN CỤC của tiến trình ⇒ mọi socket khác bị ảnh hưởng"),
        ("CaDongThoi.test_i3_timeout_toan_cuc_KHONG_anh_huong_va_KHONG_bi_doi",
         "_socket = __import__('socket')\n"
         "_goc_st = _socket.socket.settimeout\n"
         "_socket.socket.settimeout = lambda self, t: _goc_st(self, None)",
         "hạn ĐỌC bị bỏ, socket nghe theo mặc định toàn cục ⇒ hạn của người gọi vô hiệu"),
        ("CaDongThoi.test_i4_chot_chan_mang_bat_duoc_TRONG_luong_va_so_lan_noi_bang_so_luot",
         "http_jt.host_duoc_phep = lambda host: True",
         "danh sách trắng máy chủ bị vô hiệu ⇒ một URL gõ sai thành lượt gọi ra Internet"),
        ("CaHetGioNhieuTang.test_k1_het_gio_KET_NOI_do_duoc_va_PHAN_LOAI_la_khong_gui_di",
         "http_jt.KET_CUC_KHONG_GUI_DI = http_jt.KET_CUC_KHONG_BIET",
         "GỘP 'hết giờ NỐI' (chắc chắn chưa gửi đi) vào 'không biết' ⇒ mất đường thử lại an toàn"),
        ("CaHetGioNhieuTang.test_k1_het_gio_KET_NOI_do_duoc_va_PHAN_LOAI_la_khong_gui_di",
         "http_jt.HET_GIO_KET_NOI_TOI_DA = 0.0",
         "trần hạn NỐI bị đặt về 0 ⇒ lượt nối không còn được chờ theo hạn đã cấu hình"),
        ("CaHetGioNhieuTang.test_k2_het_gio_DOC_do_duoc_va_PHAN_LOAI_la_khong_biet",
         "http_jt.KET_CUC_KHONG_BIET = http_jt.KET_CUC_KHONG_GUI_DI",
         "GỘP 'hết giờ ĐỌC' (yêu cầu ĐÃ đi) vào 'chưa gửi đi' ⇒ báo an toàn cho một lượt CÓ THỂ đã tạo đơn"),
        ("CaHetGioNhieuTang.test_k3_han_NOI_bi_KEP_TRAN_5s_du_nguoi_goi_xin_7s",
         "http_jt.HET_GIO_KET_NOI_TOI_DA = 0.0",
         "mất trần hạn NỐI theo hướng ngược lại: hết giờ nối ngay lập tức"),
        ("CaHetGioNhieuTang.test_k4_han_DOC_KHONG_bi_tran_NOI_5s_kep",
         "_goc_kt = http_jt._kiem_tra_het_gio\n"
         "http_jt._kiem_tra_het_gio = lambda t: min(_goc_kt(t), http_jt.HET_GIO_KET_NOI_TOI_DA)",
         "ai đó 'đơn giản hoá' bằng cách lấy trần NỐI kẹp luôn hạn ĐỌC ⇒ mọi lượt chậm >5s bị cắt oan"),
        ("CaHetGioNhieuTang.test_k5_treo_KHONG_BAO_GIO_duoc_doc_thanh_cong",
         "_goc_gui = http_jt.gui_form\n"
         "def _gia_thanh_cong(url, headers, body, *, timeout):\n"
         "    try:\n"
         "        return _goc_gui(url, headers, body, timeout=timeout)\n"
         "    except http_jt.transport.LoiTamThoi:\n"
         "        return http_jt.TraLoiHTTP(200, b'{\"code\":\"1\"}', {})\n"
         "http_jt.gui_form = _gia_thanh_cong",
         "TREO bị đọc thành THÀNH CÔNG — lỗi nặng nhất mà lớp này tồn tại để chặn"),
        ("CaHetGioNhieuTang.test_k6_nho_gio_GHI_LAI_GIOI_HAN_timeout_la_han_TUNG_LAN_DOC",
         "_goc_gui = http_jt.gui_form\n"
         "def _gia_thanh_cong(url, headers, body, *, timeout):\n"
         "    try:\n"
         "        return _goc_gui(url, headers, body, timeout=timeout)\n"
         "    except http_jt.transport.LoiTamThoi:\n"
         "        return http_jt.TraLoiHTTP(200, b'{\"code\":\"1\"}', {})\n"
         "http_jt.gui_form = _gia_thanh_cong",
         "thân đọc dở giữa một HTTP 200 được trả về như một lượt thành công"),
        ("CaBiMatMoRong.test_j1_bi_mat_NGAN_1_den_5_ky_tu_o_HEADER_va_o_THAN_deu_bi_che",
         "http_jt.TRUONG_CREDENTIAL = ()",
         "bỏ mức che THEO TÊN ⇒ credential 1–5 ký tự lộ nguyên văn (đúng lỗi G16-05)"),
        ("CaBiMatMoRong.test_j2_bi_mat_o_HEADER_va_o_THAN_voi_TEN_khong_phai_credential",
         "http_jt.DAI_TOI_THIEU_DE_CHE = 10 ** 6",
         "bỏ mức che THEO ĐỘ DÀI ⇒ mọi bí mật ≥8 ký tự lộ nguyên văn"),
        ("CaBiMatMoRong.test_j3_bien_the_TREN_DAY_percent_encoding_va_JSON_escape_khong_lot",
         "http_jt._bien_the = lambda s: {s}",
         "quay lại che theo CHUỖI GỐC ⇒ dạng percent-encode/JSON-escape trên dây lộ nguyên văn"),
        ("CaBiMatMoRong.test_j4_hang_DOP_LAI_nhieu_lan_trong_than_van_bi_che_HET",
         "_goc_che = http_jt.che_bi_mat\n"
         "def _chi_lan_dau(du_lieu, can_che):\n"
         "    ra = bytes(du_lieu)\n"
         "    for gt in sorted(can_che, key=len, reverse=True):\n"
         "        if not gt:\n"
         "            continue\n"
         "        try:\n"
         "            ra = ra.replace(gt.encode('utf-8'), b'[DA-CHE]', 1)\n"
         "        except UnicodeEncodeError:\n"
         "            continue\n"
         "    return ra\n"
         "http_jt.che_bi_mat = _chi_lan_dau",
         "chỉ che lần xuất hiện ĐẦU TIÊN ⇒ các bản DỚP LẠI lộ nguyên văn"),
        ("CaBiMatMoRong.test_j5_bi_mat_o_QUERY_cua_URL_khong_lot",
         "http_jt._gia_tri_tu_url = lambda u: set()",
         "bỏ giá trị trong QUERY của URL khỏi tập che ⇒ token trong query lộ khi hãng echo lại"),
        ("CaBiMatMoRong.test_j6_bi_mat_o_VI_TRI_TEN_khong_bi_in_ra_trong_thong_diep",
         "http_jt._mo_ta_ten = lambda t: str(t)",
         "in thẳng TÊN không hợp lệ ⇒ giá trị nằm nhầm ở vị trí tên lộ vào thông điệp lỗi"),
        ("CaBiMatMoRong.test_j7_ngoai_le_THO_khong_con_voi_toi_duoc_tu_ngoai_le_da_che",
         "_goc_loi = http_jt._loi_tu_ngoai_le\n"
         "def _loi_kem_than(e, *a, **k):\n"
         "    loi = _goc_loi(e, *a, **k)\n"
         "    try:\n"
         "        loi.__context__ = e\n"
         "        loi.than_da_che = getattr(e, 'partial', b'')\n"
         "    except Exception:\n"
         "        pass\n"
         "    return loi\n"
         "http_jt._loi_tu_ngoai_le = _loi_kem_than",
         "nối lại ngoại lệ THÔ ⇒ thân đọc dở (chứa bí mật) đi theo `__context__` vào log"),
        ("CaBiMatMoRong.test_j8_URL_hong_nem_LoiVinhVien_chu_khong_phai_ValueError_tran",
         "_goc_tach = http_jt.tach_url\n"
         "def _tach_khong_boc(url):\n"
         "    if isinstance(url, str):\n"
         "        __import__('urllib.parse').urlsplit(url)\n"
         "    return _goc_tach(url)\n"
         "http_jt.tach_url = _tach_khong_boc",
         "bỏ lớp bọc `urlsplit` ⇒ `ValueError` trần nổi lên tận Order Service như lỗi 500"),
    )

    LOP_CA = ("CaDongThoi", "CaHetGioNhieuTang", "CaBiMatMoRong")

    def _chay(self, ten, dot_bien=""):
        p = self.chay_con(ten, dot_bien)
        return p, (p.stdout or "") + (p.stderr or "")

    def test_l1_moi_bo_do_moi_DEU_bat_duoc_khi_bi_pha(self):
        for ten_ca, dot_bien, vi_sao in self.CA:
            with self.subTest(ca=ten_ca.split(".")[-1][:48], dot_bien=dot_bien.splitlines()[0][:48]):
                p, out = self._chay(ten_ca, dot_bien)
                self.assertNotEqual(
                    p.returncode, 0,
                    f"ĐỘT BIẾN KHÔNG BỊ BẮT — hồi quy: {vi_sao}\n{out[-1500:]}")
                self.assertTrue("FAIL" in out or "ERROR" in out, out[-1500:])

    def test_l2_doi_chung_duong_moi_LOP_CA_XANH_khi_KHONG_dot_bien(self):
        for ten_lop in self.LOP_CA:
            with self.subTest(lop=ten_lop):
                p, out = self._chay(ten_lop, "")
                self.assertEqual(p.returncode, 0,
                                 f"lớp {ten_lop} hỏng cả khi KHÔNG đột biến:\n{out[-1500:]}")
                self.assertIn("OK", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)