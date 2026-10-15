#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-01 QA/VERIFIER — nghiệm thu độc lập G13 (J&T adapter contract) + các ổ khoá LIVE.

VÌ SAO BỘ NÀY KHÔNG DÙNG MẠNG, KHÔNG DỰNG MÁY CHỦ, KHÔNG MỞ CỔNG:
ba làn khác đang ghi vào CÙNG cây làm việc này. Mọi bộ thử bind cổng cố định đều có thể
báo HỎNG GIẢ vì tranh cổng (`QA2_TEST_PLAN.md` §6, R-13). Bộ này chạy thuần trong tiến
trình nên không có cổng nào để tranh, và chạy xong trong < 1 giây.

HAI CHỐT CHẶN TỰ CAM KẾT (§6.3 `docs/QA_G13_G15.md`):
  * nhóm D — ca thử TỰ KIỂM chính bộ dò: một ca CỐ Ý HỎNG chạy trong tiến trình con,
    khẳng định phép phán ĐẠT/HỎNG thật sự nhìn thấy nó hỏng;
  * nhóm C — ĐỐI CHỨNG DƯƠNG: mọi khẳng định phủ định ("mã lạ KHÔNG đổi trạng thái") đi
    kèm một khẳng định khẳng định ("mã rõ nghĩa CÓ đổi trạng thái"), để ca phủ định không
    xanh một cách vô nghĩa khi cả cỗ máy đã chết.

AG-01 KHÔNG sửa mã sản phẩm. Bộ này chỉ ĐỌC và ĐO.
"""
import ast
import base64
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adapter                                                          # noqa: E402
import adapter_jt as aj                                                 # noqa: E402
import loi_hang                                                         # noqa: E402
import trang_thai_hang as tth                                           # noqa: E402

TZ7 = dt.timezone(dt.timedelta(hours=aj.MUI_GIO_GIO))
DON_MAU = {
    "ma_don": "QA01-D1", "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0900000001",
    "nguoi_gui_dia_chi": "1 Lê Lợi", "nguoi_gui_tinh": "HN", "nguoi_gui_quan": "Q1",
    "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0900000002", "nguoi_nhan_dia_chi": "2 Nguyễn Huệ",
    "nguoi_nhan_tinh": "HCM", "nguoi_nhan_quan": "Q2",
    "khoi_luong_gram": 1000, "cod": 150000, "gia_tri_khai": 0,
}
CRED = {"apiAccount": "qa01", "privateKey": "pk-qa01"}


def _adapter():
    return adapter.tao_adapter("jt", dict(CRED), "mock")


def _doc(ten):
    with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
        return f.read()


# =======================================================================================
# A — CHỮ KÝ · KHÔNG CHẠM MẠNG · MỨC XÁC NHẬN ĐƯỜNG DẪN
# =======================================================================================
class A_ChuKyVaTransport(unittest.TestCase):

    def test_a1_chu_ky_khop_cach_tinh_doc_lap(self):
        """Đối chiếu với một cách tính VIẾT LẠI ĐỘC LẬP + openssl nếu có."""
        biz, khoa = '{"txlogisticId":"D1","codMoney":"150000"}', "pk-qa01"
        # cách tính lại từ đầu, không mượn hàm của sản phẩm
        mong = base64.b64encode(hashlib.md5((biz + khoa).encode("utf-8")).digest()).decode()
        self.assertEqual(aj.ky_digest(biz, khoa), mong, "công thức chữ ký đã lệch")
        self.assertEqual(len(mong), 24, "md5 16 byte → base64 phải đúng 24 ký tự")
        r = subprocess.run(["sh", "-c",
                            "printf '%%s' %s | openssl dgst -md5 -binary | openssl base64 -A"
                            % json.dumps(biz + khoa)], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            self.assertEqual(aj.ky_digest(biz, khoa), r.stdout.strip(),
                             "lệch với openssl — công cụ thứ ba nói khác")

    def test_a2_phuong_phap_SAI_khac_phuong_phap_dung(self):
        """`hexdigest` rồi base64 là SAI. Ca này chứng minh hai cách RA HAI KẾT QUẢ KHÁC NHAU,
        nên nếu ai đó đổi sang cách sai thì a1 sẽ đỏ — chứ không phải 'trùng nhau nên khó thấy'."""
        biz, khoa = "abc", "k"
        dung = aj.ky_digest(biz, khoa)
        sai = base64.b64encode(hashlib.md5((biz + khoa).encode()).hexdigest().encode()).decode()
        self.assertNotEqual(dung, sai, "hai phương pháp trùng nhau — ca canh mất tác dụng")
        self.assertEqual(len(sai), 44, "hexdigest 32 ký tự → base64 44 ký tự (dài hơn bản đúng)")

    def test_a3_khong_co_hexdigest_trong_MA_CHAY(self):
        """Phương pháp sai không được nằm ở BẤT KỲ nhánh nào — kể cả nhánh chưa ai gọi.
        Soát bằng TOKENIZE (bỏ chú thích + chuỗi), không grep: chữ `hexdigest` XUẤT HIỆN
        trong chú thích để giải thích cái bẫy, và grep sẽ báo hỏng giả đúng vì lời giải thích."""
        import io
        import tokenize
        for ten in ("adapter_jt.py",):
            ma_that = []
            with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
                for tok in tokenize.generate_tokens(f.readline):
                    if tok.type == tokenize.NAME:
                        ma_that.append(tok.string)
            self.assertNotIn("hexdigest", ma_that,
                             f"{ten}: `hexdigest` nằm trong MÃ CHẠY, không phải chú thích")
        self.assertIn("digest", _doc("adapter_jt.py"), "đối chứng: file phải có `digest` thật")
        _ = io  # giữ import rõ ràng

    def test_a4_khong_co_duong_cham_mang_bang_AST(self):
        """Dò bằng AST chứ không grep: bắt được cả `from urllib import request` và lời gọi."""
        cam = {"requests", "httpx", "aiohttp", "urllib", "http", "socket", "socketserver",
               "ftplib", "telnetlib", "smtplib", "asyncio", "ssl", "xmlrpc", "pycurl"}
        for ten in sorted(f for f in os.listdir(GOC_APP)
                          if f.startswith("adapter") or f in ("transport.py", "loi_hang.py")):
            cay = ast.parse(_doc(ten))
            for n in ast.walk(cay):
                if isinstance(n, ast.Import):
                    for a in n.names:
                        self.assertNotIn(a.name.split(".")[0], cam, f"{ten}: import {a.name}")
                elif isinstance(n, ast.ImportFrom):
                    self.assertNotIn((n.module or "").split(".")[0], cam, f"{ten}: from {n.module}")
                elif isinstance(n, ast.Call):
                    nm = getattr(n.func, "attr", None) or getattr(n.func, "id", None)
                    self.assertNotIn(nm, ("urlopen", "connect", "Session"),
                                     f"{ten}: gọi {nm}()")

    def test_a5_moi_duong_api_deu_khai_muc_xac_nhan(self):
        """Đường dẫn CHƯA xác nhận phải để `None`, không được đoán một URL rồi dùng."""
        self.assertEqual(aj.DUONG_API["createOrder"]["duong"],
                         "/webopenplatformapi/api/order/addOrder")
        for ten, v in aj.DUONG_API.items():
            self.assertIn(v["muc"], ("da-doc-trong-tai-lieu", "chua-xac-nhan"),
                          f"{ten}: mức xác nhận lạ {v['muc']!r}")
            self.assertTrue(v.get("nguon"), f"{ten}: không khai nguồn tài liệu")
            if v["muc"] == "chua-xac-nhan":
                self.assertIsNone(v["duong"], f"{ten}: chưa xác nhận mà vẫn có URL — đó là đoán")
        self.assertIsInstance(aj.TRANSPORT_THAT_DA_VIET, bool)
        # G16-A (AG-00 chốt 15/10/2026): `TRANSPORT_THAT_DA_VIET` là TRẠNG THÁI TIẾN ĐỘ, KHÔNG
        # phải một bất biến an toàn. AG-02 đã giao `app/http_jt.py`, nên cờ nay ĐÚNG là `True`.
        # Ca cũ ghim `is False` ⇒ đỏ dù mã đúng. Canh "một tệp đã tồn tại chưa" là canh nhầm chỗ:
        # thứ phải canh là BA Ổ KHOÁ THẬT, và chúng được đo bằng SỐ LẦN ĐỊNH NỐI SOCKET ở `a6`.

    def test_a6_khong_mot_luot_goi_nao_ra_ngoai_o_moi_moi_truong(self):
        """BA Ổ KHOÁ THẬT — canh bằng SỐ LẦN ĐỊNH NỐI SOCKET, không bằng sự tồn tại của tệp.

        G16-A thay ca cũ (`TRANSPORT_THAT_DA_VIET is False`): cờ đó lật khi AG-02 giao tệp, và
        một ca canh tiến độ thì đỏ dù mã vẫn an toàn. Ở đây ta chặn tầng `http.client` bằng bộ
        đếm: mọi môi trường (kể cả `sandbox`) phải nổ TRƯỚC khi có ai ĐỊNH mở socket, và bộ đếm
        phải là 0. Đối chứng dương: `mock` đi qua được.
        """
        import http.client as hc
        dem = {"n": 0}
        goc_h, goc_s = hc.HTTPConnection.connect, hc.HTTPSConnection.connect

        def _boc(goc):
            def _connect(self):
                dem["n"] += 1
                raise AssertionError(f"ĐỊNH nối {self.host}:{self.port} — không được phép")
            return _connect

        hc.HTTPConnection.connect = _boc(goc_h)
        hc.HTTPSConnection.connect = _boc(goc_s)
        try:
            import cau_hinh
            self.assertIs(cau_hinh.JT_CHO_PHEP_SANDBOX, False, "cổng sandbox phải ĐÓNG")
            self.assertIs(cau_hinh.JT_CHO_PHEP_PRODUCTION, False, "cổng production phải ĐÓNG")
            self.assertEqual(cau_hinh.JT_MOI_TRUONG, "mock", "mặc định phải là mock (§37)")
            self.assertTrue(adapter._DANG_KY, "sổ đăng ký lớp RỖNG — ca này không đo gì")
            for ma, lop in adapter._DANG_KY.items():
                self.assertIs(getattr(lop, "CHO_PHEP_LIVE", None), False,
                              f"hãng {ma}: CHO_PHEP_LIVE phải là False")

            with self.assertRaises(Exception) as ctx:
                ad = adapter.tao_adapter("jt", dict(CRED), "sandbox")
                ad.createOrder(dict(DON_MAU))
            self.assertNotIsInstance(ctx.exception, AttributeError,
                                     "gọi sai tên hàm — ca thử không đo được điều nó định đo")
            self.assertGreater(len(str(ctx.exception)), 20, "chặn phải kèm lý do ĐỌC ĐƯỢC")

            # ĐỐI CHỨNG DƯƠNG: `mock` phải đi qua được — nếu không thì ca âm ở trên xanh vô nghĩa.
            kq = adapter.tao_adapter("jt", dict(CRED), "mock").createOrder(dict(DON_MAU))
            self.assertTrue(kq.ok, f"mock phải tạo được đơn: {kq.loi and kq.loi.ma_chuan}")
        finally:
            hc.HTTPConnection.connect = goc_h
            hc.HTTPSConnection.connect = goc_s
        self.assertEqual(dem["n"], 0, "có lượt ĐỊNH nối socket ⇒ CRITICAL")


# =======================================================================================
# B — MỐC THỜI GIAN
# =======================================================================================
class B_MocThoiGian(unittest.TestCase):

    def test_b1_mili_giay_13_chu_so(self):
        ts = aj.dau_thoi_gian_ms()
        self.assertEqual(len(str(ts)), 13, "timestamp phải là mili giây, không phải giây")
        self.assertLess(abs(ts / 1000 - dt.datetime.now(TZ7).timestamp()), 5,
                        "mốc mặc định lệch quá 5 giây so với giờ thật")

    def test_b2_moc_CO_DINH_theo_UTC7_khop_gia_tri_tuyet_doi(self):
        """Mốc nhận biết múi giờ phải ra ĐÚNG một con số, không phụ thuộc máy đang ở đâu."""
        moc = dt.datetime(2026, 10, 15, 10, 0, 0, tzinfo=TZ7)
        self.assertEqual(aj.dau_thoi_gian_ms(moc), int(moc.timestamp() * 1000))
        self.assertEqual(aj.dau_thoi_gian_ms(moc), 1792033200000,
                         "10:00 UTC+7 ngày 15/10/2026 phải là 1792033200000")

    def test_b3_moc_mac_dinh_khong_phu_thuoc_mui_gio_may(self):
        """Chạy lại trong tiến trình con với TZ khác hẳn; mốc mặc định phải trùng khớp."""
        ma = ("import sys; sys.path.insert(0, %r); import adapter_jt as a;"
              " print(a.dau_thoi_gian_ms())" % GOC_APP)
        ra = []
        for tz in ("Asia/Ho_Chi_Minh", "UTC", "America/New_York"):
            env = dict(os.environ, TZ=tz)
            r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, f"TZ={tz}: {r.stderr[-200:]}")
            ra.append(int(r.stdout.strip()))
        self.assertLess(max(ra) - min(ra), 5000,
                        f"mốc mặc định đổi theo múi giờ MÁY: {ra}")

    def test_b4_moc_naive_duoc_gan_UTC7_tuong_minh(self):
        """G16-A: mốc KHÔNG mang múi giờ nay được gắn UTC+7 TƯỜNG MINH — canh bất biến MỚI.

        Ca cũ (`..._la_diem_MO_can_va`) ghim hành vi CŨ: mốc naive bị Python hiểu theo múi giờ
        MÁY. AG-03 đã vá (xem `dau_thoi_gian_ms` docstring), nên ca cũ trở thành **HỎNG GIẢ** trên
        máy đặt `TZ=UTC` — nó sẽ chỉ người sau đi "sửa" đúng chỗ mã đang đúng (§7.1/§7.2 BAN_GIAO).
        Bất biến ĐÚNG, đo được ở MỌI máy: naive ⇒ hiểu là UTC+7, không mượn múi giờ máy.
        """
        moc = dt.datetime(2026, 10, 15, 10, 0, 0)
        self.assertEqual(aj.dau_thoi_gian_ms(moc),
                         aj.dau_thoi_gian_ms(moc.replace(tzinfo=TZ7)),
                         "mốc naive phải được hiểu là UTC+7, KHÔNG theo múi giờ máy")
        # Đo lại trong tiến trình con với TZ khác hẳn — bất biến phải giữ ở MỌI máy.
        ma = ("import sys, datetime as dt; sys.path.insert(0, %r); import adapter_jt as a;"
              " n = dt.datetime(2026, 10, 15, 10, 0, 0);"
              " print(a.dau_thoi_gian_ms(n), a.dau_thoi_gian_ms(n.replace("
              "tzinfo=dt.timezone(dt.timedelta(hours=7)))))" % GOC_APP)
        for tz in ("UTC", "Etc/UTC", "America/New_York", "Asia/Ho_Chi_Minh"):
            r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                               env=dict(os.environ, TZ=tz), timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            a, b = (int(x) for x in r.stdout.split())
            self.assertEqual(a, b, f"TZ={tz}: mốc naive bị hiểu theo múi giờ MÁY")


# =======================================================================================
# C — COD (INTEGER ĐỒNG, `codMoney`, KHÔNG BAO GIỜ `itemsValue`) + ĐỐI CHỨNG DƯƠNG
# =======================================================================================
class C_CODVaAnhXa(unittest.TestCase):

    def test_c1_cod_di_dung_codmoney_kieu_chuoi_so_nguyen(self):
        biz = _adapter()._dung_bizcontent_tao_don(dict(DON_MAU))
        self.assertIn("codMoney", biz, "thiếu codMoney — đơn đi mà không ai thu tiền")
        self.assertEqual(biz["codMoney"], "150000")
        self.assertIsInstance(biz["codMoney"], str, "J&T nhận chuỗi số, không nhận số thô")
        self.assertTrue(biz["codMoney"].isdigit(), "codMoney phải là chuỗi CHỮ SỐ")

    def test_c2_KHONG_bao_gio_dung_itemsValue_cho_COD(self):
        biz = _adapter()._dung_bizcontent_tao_don(dict(DON_MAU))
        self.assertNotIn("itemsValue", biz, "itemsValue không phải trường COD của J&T")
        # Không có KHOÁ nào tên itemsValue trong mã chạy — chữ này chỉ được xuất hiện trong
        # chú thích/docstring giải thích cái bẫy, nên phải soát theo khoá dict, không theo chữ.
        self.assertNotIn('"itemsValue":', _doc("adapter_jt.py"),
                         "có nhánh THẬT SỰ gán itemsValue")
        self.assertNotIn("'itemsValue':", _doc("adapter_jt.py"),
                         "có nhánh THẬT SỰ gán itemsValue")

    def test_c3_cod_bang_khong_van_gui_truong(self):
        b = dict(DON_MAU)
        b.pop("cod")
        biz = _adapter()._dung_bizcontent_tao_don(b)
        self.assertEqual(biz["codMoney"], "0", "không có COD thì vẫn phải gửi '0', không bỏ trường")
        self.assertEqual(biz["isInsured"], 0)
        self.assertIn("goodsValue", biz, "goodsValue là trường bắt buộc theo tài liệu")

    def test_c4_tien_phai_la_so_nguyen_dong(self):
        for v, mo in ((150000, "int"), ("150000", "chuỗi số"), (0, "0")):
            self.assertEqual(aj.tien_nguyen_vnd(v, "cod"), int(v), f"phải NHẬN {mo}")
        for v, mo in ((-1, "âm"), (1.5, "thập phân"), (float("nan"), "NaN"),
                      (float("inf"), "vô cực"), ("12abc", "chuỗi lẫn chữ"), (True, "bool"),
                      ({}, "dict")):
            with self.assertRaises(Exception, msg=f"phải TỪ CHỐI {mo}"):
                aj.tien_nguyen_vnd(v, "cod")

    def test_c5_ma_LA_khong_doi_trang_thai__va_DOI_CHUNG_DUONG(self):
        """Cặp đối chứng: mã lạ ⇒ không áp, cần soát. Mã rõ nghĩa ⇒ ÁP THẬT.
        Thiếu vế thứ hai thì vế thứ nhất xanh một cách vô nghĩa (cỗ máy chết cũng xanh)."""
        for ma in (110, 9999, 121):
            q = tth.quyet_dinh("jt", ma, su_kien_goc={"ma_van_don": "X"}, nhan_luc=None)
            self.assertIsNone(q.trang_thai_ap, f"mã {ma} KHÔNG được đổi trạng thái")
        q110 = tth.quyet_dinh("jt", 110, su_kien_goc={"ma_van_don": "X"}, nhan_luc=None)
        self.assertTrue(q110.can_soat, "mã 110 phải vào diện CẦN SOÁT, không im lặng bỏ qua")
        qx = tth.quyet_dinh("jt", 9999, su_kien_goc={"ma_van_don": "X"}, nhan_luc=None)
        self.assertTrue(qx.can_soat, "mã lạ phải vào diện CẦN SOÁT")
        # ĐỐI CHỨNG DƯƠNG — cỗ máy ánh xạ thật sự chạy được
        q113 = tth.quyet_dinh("jt", 113, su_kien_goc={"ma_van_don": "X"}, nhan_luc=None)
        self.assertEqual(q113.trang_thai_ap, "giao_thanh_cong",
                         "ĐỐI CHỨNG DƯƠNG HỎNG: mã 113 phải áp được — nếu không, các ca "
                         "'không đổi trạng thái' ở trên xanh vô nghĩa")


# =======================================================================================
# D — Ổ KHOÁ LIVE (ba ổ độc lập) + TỰ KIỂM BỘ DÒ
# =======================================================================================
class D_OKhoaLive(unittest.TestCase):

    def test_d1_moi_adapter_dang_ky_deu_khoa_live(self):
        """Lặp ĐỘNG trên sổ đăng ký, không đọc một hằng viết cứng nào."""
        ds = adapter.danh_sach_hang()
        self.assertGreater(len(ds), 0, "sổ đăng ký rỗng — phép kiểm này vô nghĩa")
        for ma, tt in ds.items():
            self.assertIs(tt["live_mo"], False, f"{ma} đã MỞ đường LIVE")

    def test_d2_chot_chan_D9_chan_moi_moi_truong_khac_mock(self):
        aj.chot_chan_anh_xa_area("mock")                      # mock đi qua, không ném
        with self.assertRaises(loi_hang.NormalizedCarrierError):
            aj.chot_chan_anh_xa_area("sandbox")
        with self.assertRaises(loi_hang.NormalizedCarrierError):
            aj.chot_chan_anh_xa_area("live")

    def test_d3_mo_CHO_PHEP_LIVE_KHONG_go_duoc_chot_D9(self):
        """ĐỐI CHỨNG: mở ổ khoá thứ nhất KHÔNG được mở ổ khoá thứ hai."""
        cu = aj.AdapterJT.CHO_PHEP_LIVE
        try:
            aj.AdapterJT.CHO_PHEP_LIVE = True
            with self.assertRaises(loi_hang.NormalizedCarrierError,
                                   msg="mở CHO_PHEP_LIVE đã gỡ luôn chốt chặn D-9"):
                aj.chot_chan_anh_xa_area("sandbox", da_xac_nhan=False)
        finally:
            aj.AdapterJT.CHO_PHEP_LIVE = cu
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False, "ca thử phải trả cờ về False")

    def test_d4_chot_D9_khong_cho_qua_bang_chuoi_giu_cho(self):
        """Bật cờ xác nhận nhưng nguồn là chuỗi giữ chỗ / rỗng ⇒ vẫn phải CHẶN."""
        with self.assertRaises(loi_hang.NormalizedCarrierError):
            aj.chot_chan_anh_xa_area("sandbox", da_xac_nhan=True, nguon="", cap="quan")
        with self.assertRaises(loi_hang.NormalizedCarrierError):
            aj.chot_chan_anh_xa_area("sandbox", da_xac_nhan=True, nguon="TODO", cap="quan-huyen")
        # cấp hành chính ngoài danh sách TRẮNG cũng phải chặn
        with self.assertRaises(loi_hang.NormalizedCarrierError):
            aj.chot_chan_anh_xa_area("sandbox", da_xac_nhan=True, nguon="a" * 40, cap="quan")
        # ĐỐI CHỨNG DƯƠNG: đủ ba cửa thì phải ĐI QUA được, nếu không thì ba ca trên
        # xanh một cách vô nghĩa (hàm chặn tất cả thì "chặn đúng" cũng luôn đúng).
        aj.chot_chan_anh_xa_area("sandbox", da_xac_nhan=True,
                                 nguon="J&T trả lời email 15/10/2026, mã 2.3", cap="quan-huyen")


class E_TuKiemBoDo(unittest.TestCase):
    """TỰ KIỂM BỘ DÒ (§6.3 cam kết 1). Nếu nhóm này không có, 'bộ thử xanh' không chứng minh gì:
    một bộ thử luôn báo ĐẠT thì xanh với mọi thứ, kể cả mã đã hỏng."""

    MA_HONG = ("import unittest\n"
               "class T(unittest.TestCase):\n"
               "    def test_x(self): self.assertEqual(1, 2)\n"
               "unittest.main(verbosity=2)\n")
    MA_DAT = ("import unittest\n"
              "class T(unittest.TestCase):\n"
              "    def test_x(self): self.assertEqual(1, 1)\n"
              "unittest.main(verbosity=2)\n")

    def _chay(self, ma):
        r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_e1_bo_do_THAY_duoc_ca_hong(self):
        rc, out = self._chay(self.MA_HONG)
        self.assertNotEqual(rc, 0, "bộ dò KHÔNG thấy ca hỏng qua mã thoát — chốt chặn đã chết")
        self.assertNotRegex(out, r"(?m)^OK( |$)", "ca hỏng mà vẫn in 'OK'")
        self.assertIn("FAILED", out)

    def test_e2_bo_do_KHONG_bao_hong_gia(self):
        """ĐỐI CHỨNG DƯƠNG: ca đạt phải thoát 0 và có dấu vết đã chạy — nếu không thì mọi
        phán quyết 'HỎNG' ở e1 cũng vô nghĩa vì bộ dò hỏng theo hướng ngược lại."""
        rc, out = self._chay(self.MA_DAT)
        self.assertEqual(rc, 0, f"ca ĐẠT mà thoát {rc}")
        self.assertRegex(out, r"(?m)^OK( |$)", "ca ĐẠT nhưng không có dòng OK")
        self.assertRegex(out, r"Ran 1 test", "không đếm được số ca đã chạy")

    def test_e3_tieu_chi_cua_bo_chay_phan_biet_duoc_hai_chieu(self):
        """Mô phỏng ĐÚNG tiêu chí của `chay_tat_ca.sh`: mã thoát + dấu vết + số ca > 0."""
        def phan(rc, out):
            n = 0
            for dong in out.split("\n"):
                if dong.startswith("Ran "):
                    n = int(dong.split()[1])
            co_dau_vet = any(d.startswith("OK") for d in out.split("\n"))
            return "ĐẠT" if (rc == 0 and co_dau_vet and n > 0) else "HỎNG"
        self.assertEqual(phan(*self._chay(self.MA_DAT)), "ĐẠT")
        self.assertEqual(phan(*self._chay(self.MA_HONG)), "HỎNG")


if __name__ == "__main__":
    print("=" * 78)
    print("AG-01 QA — nghiệm thu J&T contract · PHẠM VI: chữ ký · mốc thời gian · AST không")
    print("chạm mạng · COD codMoney · ba ổ khoá LIVE (đo bằng bộ đếm socket) · tự kiểm bộ dò.")
    print("KHÔNG phủ: API hãng thật (V-G09-01 chưa cấp) · HTTP end-to-end ra hãng.")
    print("Lớp HTTP thật (`app/http_jt.py`, AG-02) do `app/thu/thu_qa_g16.py` nghiệm thu.")
    print("=" * 78)
    kq = unittest.main(verbosity=2, exit=False).result
    print()
    print("Tổng: %d ca · hỏng %d · lỗi %d · bỏ qua %d"
          % (kq.testsRun, len(kq.failures), len(kq.errors), len(kq.skipped)))
    sys.exit(0 if kq.wasSuccessful() else 1)
