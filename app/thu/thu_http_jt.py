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
import io
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from email.utils import format_datetime
from urllib.parse import parse_qs, urlsplit

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
for _d in (GOC, THU):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402
from stub_jt import StubJT                                              # noqa: E402

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
