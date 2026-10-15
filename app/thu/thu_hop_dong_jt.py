# G13 (J02/J04) — HỢP ĐỒNG YÊU CẦU CỦA J&T: chữ ký · thân yêu cầu · tiền · ánh xạ `area`.
#
# VÌ SAO CÓ FILE NÀY
# ------------------
# `app/thu/thu_g03.py` (G03) đã kiểm công thức chữ ký ở mức "hàm ký chạy đúng". File này kiểm
# ở mức HỢP ĐỒNG GỬI ĐI: từng thao tác của J&T dựng ra gói yêu cầu gì, tiền đi ở trường nào,
# đường dẫn nào đã xác minh và đường dẫn nào thì CHƯA, và chỗ nào adapter phải DỪNG thay vì đoán.
#
# Ba nhóm ca đáng chú ý:
#   · nhóm C (TIỀN): COD phải đi ở `codMoney`, KHÔNG bao giờ ở `itemsValue`; số thập phân bị
#     TỪ CHỐI chứ không làm tròn — nhầm cột COD là "hàng đi, tiền không về, không lỗi nào báo".
#   · nhóm D (D-9): ánh xạ `area` là GIẢ ĐỊNH chưa được hãng xác nhận; ca kiểm GHIM giả định đó
#     lại và khẳng định đường LIVE bị chặn — để lần đổi nào cũng phải nhìn thấy.
#   · nhóm E (ĐƯỜNG DẪN): thao tác chưa xác minh đường dẫn thì bị chặn ở mọi môi trường khác
#     `mock`. Không có nhóm này thì "chưa đọc được tài liệu" âm thầm biến thành "đã đoán một URL".
#
# Chạy: python3 app/thu/thu_hop_dong_jt.py
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g13-hd-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import adapter_jt as aj      # noqa: E402
import adapter               # noqa: E402
import loi_hang as lh        # noqa: E402

DON_MAU = {
    "ma_don": "G13-HD-1", "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Thử",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
    "hang_hoa": "Áo thử", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
    "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa",
}

CRED_THU = {"apiAccount": "669", "privateKey": "KHOA-THU-KY", "customerCode": "CC-THU",
            "password": "MK-THU"}

# Vector ĐÁP ÁN BIẾT TRƯỚC: tính bằng tay (base64(md5(bytes))) ngoài bộ thử rồi ghim lại đây.
# Ca kiểm dùng vector này KHÔNG phụ thuộc vào chính hàm của adapter — nếu ai đổi công thức ký
# (ví dụ lấy md5 hexdigest rồi base64), vector sẽ lệch ngay.
VECTOR = [
    ('{"customerCode": "CC", "txlogisticId": "T1"}', "K1", "or6valR+VpzGkhLAL7VdtQ=="),
    ('{"a": 1}', "K1", "8p+hFUxoVI7krhcHEsxXuQ=="),
    ('{"a": 1}', "K2", "5ssVUPK9SnwVyBquiQaG3A=="),
]

# Từ khoá nhập thư viện gọi mạng. Adapter J&T phải KHÔNG có cái nào: mọi môi trường khác mock
# đang bị chặn, nên một dòng gọi mạng lọt vào đây là dòng không ai kiểm mà vẫn có thể chạy.
CAM_GOI_MANG = ("import requests", "import httpx", "import aiohttp", "urllib.request",
                "http.client", "socket.socket", "urlopen(")


def quet_goi_mang(nguon: str):
    """Trả danh sách từ khoá gọi mạng có trong `nguon`. Rỗng = sạch."""
    return [cam for cam in CAM_GOI_MANG if cam in nguon]


# Tên thao tác CHƯA xác minh đường dẫn, dùng cho phép quét URL tuyệt đối trong mã nguồn adapter.
# Đây là bản SAO có chủ ý của `aj.THAO_TAC_CHUA_XAC_MINH`: bộ dò phải là một phép ĐỘC LẬP, đọc
# từ chính nó chứ không hỏi bảng đang bị soi (hỏi bảng thì bảng nói dối lúc nào cũng lọt).
TOKEN_CHUA_XAC_MINH = ("cancelOrder", "calculatingFees", "printOrder", "getOrder")


def quet_url_bua(nguon: str):
    """Trả danh sách URL TUYỆT ĐỐI (`http(s)://…`) trỏ tới bốn thao tác chưa xác minh.

    Vì sao quét cả TỆP chứ không chỉ quét bảng `DUONG_API`: bảng là một chỗ, nhưng một URL dán
    thẳng vào một hàm (`url = "https://…/cancelOrder"`) thì không đi qua bảng nào cả. Bộ dò đọc
    NGUỒN nên bắt được cả hai đường. Đường dẫn trong CHÚ THÍCH (`open.jtexpress.vn/apiDoc/…`,
    không có scheme) KHÔNG bị tính — đó là dẫn nguồn tài liệu, không phải một lượt gọi.
    """
    ra = []
    for mau in re.findall(r"https?://[^\s\"'`,;)\]}]+", nguon):
        if any(tok in mau for tok in TOKEN_CHUA_XAC_MINH):
            ra.append(mau)
    return ra


class ChoPhepLiveTam:
    """Mở tạm `CHO_PHEP_LIVE` để chạm được vào các chốt chặn SÂU HƠN.

    Cần thiết vì chốt đầu tiên (`__init__`) chặn trước mọi thứ khác, nên không mở nó thì không
    đo được rằng các chốt sau vẫn độc lập. Dùng `finally` để không rò trạng thái sang ca khác.
    """

    def __enter__(self):
        self.cu = aj.AdapterJT.CHO_PHEP_LIVE
        aj.AdapterJT.CHO_PHEP_LIVE = True
        return self

    def __exit__(self, *a):
        aj.AdapterJT.CHO_PHEP_LIVE = self.cu
        return False


def ad_mock(cred=None):
    return adapter.tao_adapter("jt", dict(cred or CRED_THU), "mock")


# ════════════════════════════════════════════════════════════════════════════════════════════════
class A_ChuKyVaHeaders(unittest.TestCase):
    """Chữ ký: công thức, vector biết trước, ba header, thân form."""

    def test_a1_vector_dap_an_biet_truoc(self):
        for biz, khoa, mong in VECTOR:
            self.assertEqual(aj.ky_digest(biz, khoa), mong,
                             f"digest lệch vector cho biz={biz!r} key={khoa!r}")

    def test_a2_digest_la_md5_bytes_roi_base64(self):
        """Bản SAI (md5 hexdigest → base64) phải KHÁC bản đúng. Nếu ai đổi công thức, ca này đỏ."""
        import base64
        import hashlib
        biz, khoa = VECTOR[1][0], VECTOR[1][1]
        dung = base64.b64encode(hashlib.md5((biz + khoa).encode()).digest()).decode()
        sai = base64.b64encode(hashlib.md5((biz + khoa).encode()).hexdigest().encode()).decode()
        self.assertNotEqual(dung, sai)
        self.assertEqual(aj.ky_digest(biz, khoa), dung)
        self.assertNotEqual(aj.ky_digest(biz, khoa), sai)
        self.assertEqual(len(aj.ky_digest(biz, khoa)), 24, "md5 16 byte → base64 phải 24 ký tự")

    def test_a3_doi_bizcontent_hoac_khoa_thi_chu_ky_doi(self):
        a = aj.ky_digest('{"a":1}', "K1")
        self.assertNotEqual(a, aj.ky_digest('{"a":2}', "K1"))
        self.assertNotEqual(a, aj.ky_digest('{"a":1}', "K2"))

    def test_a4_du_ba_header_va_content_type(self):
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        h = yc["headers"]
        for ten in ("apiAccount", "digest", "timestamp", "Content-Type"):
            self.assertIn(ten, h, f"thiếu header {ten} theo bảng Headers của tài liệu")
        self.assertEqual(h["Content-Type"], aj.CONTENT_TYPE)
        self.assertEqual(h["apiAccount"], CRED_THU["apiAccount"])
        self.assertEqual(h["digest"], aj.ky_digest(yc["bizContent"], CRED_THU["privateKey"]))

    def test_a5_timestamp_la_mili_giay_UTC7_tuong_minh(self):
        import datetime as dt
        tz7 = dt.timezone(dt.timedelta(hours=7))
        moc = dt.datetime(2026, 10, 15, 12, 0, 0, tzinfo=tz7)
        self.assertEqual(aj.dau_thoi_gian_ms(moc), int(moc.timestamp() * 1000))
        self.assertEqual(len(str(aj.dau_thoi_gian_ms())), 13, "phải là mili giây, không phải giây")
        ts = ad_mock().yeu_cau_tao_don(dict(DON_MAU), bay_gio=moc)["headers"]["timestamp"]
        self.assertEqual(ts, str(int(moc.timestamp() * 1000)))

    def test_a6_body_la_form_dung_mot_truong_bizcontent(self):
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        self.assertEqual(list(yc["body"].keys()), ["bizContent"])
        # Mã hoá form thật rồi giải lại: chứng minh thân yêu cầu đi được bằng
        # application/x-www-form-urlencoded mà KHÔNG cần mạng.
        ma_hoa = urllib.parse.urlencode(yc["body"])
        self.assertTrue(ma_hoa.startswith("bizContent="))
        self.assertEqual(urllib.parse.parse_qs(ma_hoa)["bizContent"][0], yc["bizContent"])

    def test_a7_bizcontent_la_chuoi_json_da_dem_di_ky(self):
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        self.assertIsInstance(yc["bizContent"], str)
        biz = json.loads(yc["bizContent"])
        self.assertEqual(biz["txlogisticId"], DON_MAU["ma_don"])
        self.assertEqual(biz["customerCode"], CRED_THU["customerCode"])
        self.assertEqual(biz["password"], CRED_THU["password"])

    def test_a8_mock_khong_mang_url_that(self):
        """Ở mock, URL phải là None — để một lượt gọi ra ngoài không thể xảy ra do sơ ý."""
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        self.assertIsNone(yc["url"])
        self.assertIsNone(aj.url_cua("createOrder", "mock"))
        self.assertIsNone(aj.url_cua("trackOrder", "mock"))

    def test_a9_kiem_chu_ky_doc_lap_tinh_tu_chuoi_NAM_TRONG_GOI(self):
        """G16-D: phép kiểm chữ ký phải ĐỘC LẬP — tính lại bằng tay, không mượn hàm của adapter."""
        import base64
        import hashlib
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        r = aj.kiem_chu_ky(yc, CRED_THU)
        self.assertTrue(r["khop"])
        self.assertTrue(r["co_bizcontent"])
        tay = base64.b64encode(hashlib.md5(
            (yc["bizContent"] + CRED_THU["privateKey"]).encode("utf-8")).digest()).decode()
        self.assertEqual(r["digest_tinh_lai"], tay)
        self.assertEqual(yc["headers"]["digest"], tay)

    def test_a10_ky_mot_chuoi_gui_chuoi_khac_thi_kiem_chu_ky_PHAT_HIEN(self):
        """Ca mà hàm ký tự-kiểm-chính-mình KHÔNG BAO GIỜ thấy: sửa thân gửi sau khi đã ký."""
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        self.assertTrue(aj.kiem_chu_ky(yc, CRED_THU)["khop"])
        cu = yc["bizContent"]
        yc["bizContent"] = cu.replace('"codMoney": "15000"', '"codMoney": "15001"')
        self.assertNotEqual(yc["bizContent"], cu, "phép sửa chuỗi không tác dụng ⇒ ca thử vô nghĩa")
        self.assertNotEqual(yc["headers"]["digest"],
                            aj.ky_digest(yc["bizContent"], CRED_THU["privateKey"]))
        self.assertFalse(aj.kiem_chu_ky(yc, CRED_THU)["khop"],
                         "đổi chuỗi đem gửi mà chữ ký vẫn 'khớp' ⇒ phép kiểm vô nghĩa")

    def test_a11_TU_KIEM_kiem_chu_ky_khong_luon_dung(self):
        """Bộ dò phải chứng minh nó BẮT ĐƯỢC chữ ký sai — nếu không, ca A9 xanh vô nghĩa."""
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU))
        yc_digest_sai = json.loads(json.dumps(yc))
        yc_digest_sai["headers"]["digest"] = "AAAA"
        self.assertFalse(aj.kiem_chu_ky(yc_digest_sai, CRED_THU)["khop"])
        self.assertFalse(aj.kiem_chu_ky(yc, dict(CRED_THU, privateKey="KHOA-KHAC"))["khop"])
        self.assertFalse(aj.kiem_chu_ky({"headers": {}}, CRED_THU)["khop"],
                         "gói không có bizContent mà vẫn 'khớp' là sai")

    def test_a12_kiem_chu_ky_kiem_ca_moc_thoi_gian(self):
        import datetime as dt
        tz7 = dt.timezone(dt.timedelta(hours=7))
        moc = dt.datetime(2026, 10, 15, 12, 0, 0, tzinfo=tz7)
        ms = int(moc.timestamp() * 1000)
        yc = ad_mock().yeu_cau_tao_don(dict(DON_MAU), bay_gio=moc)
        r = aj.kiem_chu_ky(yc, CRED_THU, luc_goi_ms=ms, sai_so_ms=1000)
        self.assertTrue(r["thoi_gian_hop_le"])
        self.assertEqual(r["thoi_gian_ms"], ms)
        # ĐỐI CHỨNG ÂM cho chính phép kiểm này: lệch quá sai số ⇒ KHÔNG hợp lệ.
        self.assertFalse(aj.kiem_chu_ky(yc, CRED_THU, luc_goi_ms=ms + 10_000,
                                        sai_so_ms=1000)["thoi_gian_hop_le"])
        yc_giay = json.loads(json.dumps(yc))
        yc_giay["headers"]["timestamp"] = str(ms // 1000)
        self.assertFalse(aj.kiem_chu_ky(yc_giay, CRED_THU)["thoi_gian_hop_le"],
                         "mốc GIÂY bị nhận là mili giây ⇒ hãng từ chối ở lớp chống phát-lại")

    def test_a13_L2N2_moc_NAIVE_di_theo_UTC7_khong_theo_mui_gio_MAY(self):
        """VÁ `L2-N2` (docs/QA_G13_G15.md §L2.2) — đo bằng TIẾN TRÌNH CON, đúng cách đã phát hiện.

        Trước bản vá: `TZ=UTC` cho ra con số lệch ĐÚNG 7 tiếng so với `TZ=Asia/Ho_Chi_Minh`,
        trong khi docstring hứa "không mượn múi giờ của máy".
        """
        ma = ("import sys; sys.path.insert(0, %r); import datetime as d; import adapter_jt as a;"
              " print(a.dau_thoi_gian_ms(d.datetime(2026, 10, 15, 10, 0, 0)))" % GOC_APP)
        ra = []
        for tz in ("Asia/Ho_Chi_Minh", "UTC", "America/New_York"):
            r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                               env=dict(os.environ, TZ=tz))
            self.assertEqual(r.returncode, 0, f"TZ={tz}: {r.stderr[-300:]}")
            ra.append(int(r.stdout.strip()))
        self.assertEqual(len(set(ra)), 1,
                         f"mốc NAIVE vẫn đổi theo múi giờ MÁY: {ra} — L2-N2 tái phát")
        self.assertEqual(ra[0], 1792033200000,
                         "10:00 ngày 15/10/2026 theo UTC+7 phải là 1792033200000")
        # Mốc CÓ múi giờ vẫn phải giữ nguyên hành vi cũ (không được vá quá tay).
        import datetime as dt
        tz7 = dt.timezone(dt.timedelta(hours=7))
        moc = dt.datetime(2026, 10, 15, 10, 0, 0, tzinfo=tz7)
        self.assertEqual(aj.dau_thoi_gian_ms(moc), 1792033200000)
        self.assertEqual(aj.dau_thoi_gian_ms(moc.replace(tzinfo=None)), 1792033200000,
                         "mốc naive phải cho CÙNG kết quả với mốc UTC+7 tường minh")


class B_DuongDanDaXacMinh(unittest.TestCase):
    """Đường dẫn: cái gì đã đọc được, cái gì chưa — ghim lại bằng hằng số, không bằng trí nhớ."""

    def test_b1_hai_duong_dan_da_doc_dung_nguyen_van(self):
        self.assertEqual(aj.URL_TAO_DON["sandbox"],
                         "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder")
        self.assertEqual(aj.URL_TAO_DON["production"],
                         "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder")
        self.assertEqual(aj.URL_TRA_HANH_TRINH["sandbox"],
                         "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/logistics/trace")
        self.assertEqual(aj.URL_TRA_HANH_TRINH["production"],
                         "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/logistics/trace")

    def test_b2_muc_xac_nhan_tung_thao_tac(self):
        self.assertEqual(aj.DUONG_API["createOrder"]["muc"], aj.MUC_DA_DOC)
        self.assertEqual(aj.DUONG_API["trackOrder"]["muc"], aj.MUC_DA_DOC)
        for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            self.assertEqual(aj.DUONG_API[op]["muc"], aj.MUC_CHUA_XAC_NHAN,
                             f"{op} chưa xác minh đường dẫn ⇒ phải khai đúng là CHƯA")
            self.assertIsNone(aj.DUONG_API[op]["duong"], f"{op} không được có URL đoán ra")

    def test_b3_duong_dan_huy_don_chi_doc_duoc_o_dang_tuong_doi(self):
        self.assertEqual(aj.DUONG_API["cancelOrder"]["duong_tuong_doi_da_doc"],
                         "/api/order/cancelOrder")
        self.assertIn("tương đối", aj.DUONG_API["cancelOrder"]["nguon"])

    def test_b4_moi_thao_tac_deu_khai_nguon_tai_lieu(self):
        for op, d in aj.DUONG_API.items():
            self.assertTrue(str(d.get("nguon") or "").strip(), f"{op} thiếu nguồn tài liệu")

    def test_b5_getOrder_chua_co_tai_lieu_nen_capability_false(self):
        self.assertFalse(aj.AdapterJT.CAPABILITIES["getOrder"])
        self.assertFalse(ad_mock().capability("getOrder"))
        kq = ad_mock().getOrder("MVD1")
        self.assertFalse(kq.ok)
        self.assertIn("không hỗ trợ", kq.loi or "")


class C_TienVaCOD(unittest.TestCase):
    """Tiền: INTEGER đồng (§16); COD ở `codMoney`, KHÔNG BAO GIỜ ở `itemsValue`."""

    def _biz(self, **them):
        don = dict(DON_MAU)
        don.update(them)
        return json.loads(ad_mock().yeu_cau_tao_don(don)["bizContent"])

    def test_c1_cod_di_dung_truong_codmoney_va_la_chuoi_so_nguyen(self):
        biz = self._biz(cod=15000)
        self.assertEqual(biz["codMoney"], "15000")
        self.assertIsInstance(biz["codMoney"], str)
        self.assertNotIn(".", biz["codMoney"], "tiền không có phần thập phân (§16)")

    def test_c2_KHONG_bao_gio_dung_itemsValue_cho_COD(self):
        """Ca quan trọng nhất của nhóm này: nhầm cột COD là mất tiền mà không có lỗi nào báo."""
        biz = self._biz(cod=15000)
        self.assertNotIn("itemsValue", biz,
                         "itemsValue KHÔNG có trong bảng tham số — COD phải đi ở codMoney")

    def test_c3_cod_bang_khong_van_gui_truong(self):
        self.assertEqual(self._biz(cod=0)["codMoney"], "0")

    def test_c4_cod_nhan_chuoi_so_nguyen(self):
        self.assertEqual(self._biz(cod="25000")["codMoney"], "25000")

    def test_c5_cod_thap_phan_bi_TU_CHOI_chu_khong_lam_tron(self):
        for xau in (15000.5, "15000.5", 0.1):
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                self._biz(cod=xau)
            self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)
            self.assertIn("thập phân", e.exception.thong_diep)

    def test_c6_cod_am_hoac_sai_kieu_bi_tu_choi(self):
        for xau in (-1, "-5", True, "mười nghìn", "nan", "inf", float("nan")):
            with self.assertRaises(lh.NormalizedCarrierError, msg=f"nhận nhầm cod={xau!r}"):
                self._biz(cod=xau)

    def test_c7_cod_nguyen_kieu_float_van_di_qua(self):
        """15000.0 là số nguyên viết kiểu float — nhận, nhưng ra chuỗi nguyên."""
        self.assertEqual(self._biz(cod=15000.0)["codMoney"], "15000")

    def test_c8_goodsValue_va_isInsured_bat_buoc(self):
        biz = self._biz(gia_tri_khai=200000)
        self.assertEqual(biz["goodsValue"], "200000")
        self.assertIn("isInsured", biz)
        self.assertEqual(biz["isInsured"], 0)

    def test_c9_khong_co_gia_tri_khai_thi_lay_COD(self):
        biz = self._biz(gia_tri_khai=0, cod=15000)
        self.assertEqual(biz["goodsValue"], "15000")

    def test_c10_can_nang_ra_chuoi_kg_hai_chu_so(self):
        self.assertEqual(self._biz(khoi_luong_gram=1500)["packageInfo"]["weight"], "1.50")
        self.assertEqual(self._biz(khoi_luong_gram=500)["packageInfo"]["weight"], "0.50")

    def test_c11_can_nang_khong_hop_le_thi_dung(self):
        for xau in (0, -5, 1500.5, "1,5kg"):
            with self.assertRaises(lh.NormalizedCarrierError):
                self._biz(khoi_luong_gram=xau)

    def test_c12_phi_mock_la_so_nguyen_va_tu_khai_khong_phai_gia_hang(self):
        kq = ad_mock().getShippingFee(dict(DON_MAU))
        self.assertTrue(kq.ok)
        self.assertIsInstance(kq.phi, int, "phí phải là INTEGER đồng (§16)")
        self.assertFalse(kq.tho.get("la_gia_hang"),
                         "phí mock KHÔNG được tự nhận là giá của hãng")
        self.assertIn("KHÔNG phải bảng giá J&T", kq.tho.get("nguon_gia", ""))


class D_AnhXaArea_D9(unittest.TestCase):
    """D-9: `area` ← quận/huyện là GIẢ ĐỊNH. Ca kiểm ghim giả định và khẳng định LIVE bị chặn."""

    def test_d1_anh_xa_dang_dung_la_quan_huyen_va_la_gia_dinh(self):
        cap = {(nhom, truong): cot for nhom, truong, cot in aj.AdapterJT.TRUONG_HANH_CHINH}
        self.assertEqual(cap[("sender", "area")], "nguoi_gui_quan")
        self.assertEqual(cap[("receiver", "area")], "nguoi_nhan_quan")
        self.assertIn("giả định", aj.AdapterJT._dung_bizcontent_tao_don.__doc__)

    def test_d2_co_chot_chan_va_mac_dinh_la_chan(self):
        self.assertFalse(aj.ANH_XA_AREA_DA_XAC_NHAN)
        self.assertEqual(str(aj.NGUON_XAC_NHAN_AREA or "").strip(), "")
        self.assertEqual(aj.CAP_HANH_CHINH_CHO_AREA, "quan-huyen")
        self.assertTrue(callable(aj.chot_chan_anh_xa_area))

    def test_d3_mock_di_qua_con_duong_live_thi_dung(self):
        self.assertIsNone(aj.chot_chan_anh_xa_area("mock"))     # không ném
        with self.assertRaises(lh.NormalizedCarrierError) as e:
            aj.chot_chan_anh_xa_area("sandbox")
        self.assertIn("D-9", e.exception.thong_diep)
        self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)

    def test_d4_mo_CO_PHEP_LIVE_KHONG_go_duoc_chot_D9(self):
        """Hai ổ khoá ĐỘC LẬP: mở ổ này không mở ổ kia. Đây là điều D-9 muốn."""
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                ad.yeu_cau_tao_don(dict(DON_MAU))
            self.assertIn("D-9", e.exception.thong_diep)

    def test_d5_city_khong_duoc_gui_va_ghi_ro_la_khong_gui(self):
        biz = json.loads(ad_mock().yeu_cau_tao_don(dict(DON_MAU))["bizContent"])
        self.assertNotIn("city", biz["sender"])
        self.assertNotIn("city", biz["receiver"])
        self.assertFalse(aj.CITY_CO_GUI, "hằng phải nói thật: hệ KHÔNG gửi `city`")

    def test_d6_mock_thieu_dia_chi_hanh_chinh_thi_ghi_vao_GOI_YEU_CAU_khong_vao_biz(self):
        don = dict(DON_MAU)
        for cot in ("nguoi_gui_tinh", "nguoi_gui_quan", "nguoi_nhan_tinh", "nguoi_nhan_quan"):
            don.pop(cot)
        yc = ad_mock().yeu_cau_tao_don(don)
        self.assertEqual(len(yc["thieu_truong"]), 4)
        biz = json.loads(yc["bizContent"])
        self.assertNotIn("thieu_truong", biz, "không được gửi trường nội bộ lên hãng")
        self.assertNotIn("thieu_truong", json.dumps(biz, ensure_ascii=False))

    def test_d7_ngoai_mock_thieu_dia_chi_thi_dung_truoc_khi_goi(self):
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            don = dict(DON_MAU)
            don.pop("nguoi_gui_tinh")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                ad.yeu_cau_tao_don(don)
            self.assertIn("nguoi_gui_tinh", e.exception.thong_diep)
            self.assertIn("1450033315", e.exception.thong_diep)


class E_ChotChanDuongDanChuaXacMinh(unittest.TestCase):
    """Thao tác chưa xác minh đường dẫn: chặn ở MỌI môi trường khác mock, và nói rõ còn thiếu gì."""

    def test_e1_chan_chua_chay_duoc_neu_DU_ly_do_khong_chi_ly_do_dau(self):
        """`_chan_chua_chay_duoc` phải gom ĐỦ ba lý do — nêu một lý do rồi dừng là cách người
        đọc sửa xong chỗ thứ nhất, chạy lại, rồi mới thấy chỗ thứ hai."""
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                ad._chan_chua_chay_duoc("cancelOrder")
        self.assertEqual(e.exception.thao_tac, "cancelOrder")
        self.assertEqual(e.exception.moi_truong, "sandbox")
        gop = " | ".join(e.exception.thieu).lower()
        self.assertIn("cấp quyền", gop, "thiếu lý do MÔI TRƯỜNG")
        self.assertIn("chưa xác minh", gop, "thiếu lý do ĐƯỜNG DẪN")
        if aj.http_jt_dang_dung() is None:
            self.assertIn("http", gop, "thiếu lý do LỚP HTTP")
        else:
            # Lớp HTTP ĐÃ có trên đĩa (AG-02 giao `app/http_jt.py`) ⇒ lý do đó KHÔNG còn đúng,
            # và hàm phải thôi nêu nó. Nêu một lý do đã hết hiệu lực cũng là nói sai.
            self.assertNotIn("chưa có trên đĩa", gop)

    def test_e2_moi_truong_duoc_kiem_TRUOC_khi_gui(self):
        """Cửa môi trường là cửa ĐẦU TIÊN của đường gửi — kể cả thao tác ĐÃ có đường dẫn."""
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(PermissionError) as e:
                ad.trackOrder("MVD1")      # trackOrder CÓ đường dẫn đã xác minh
            self.assertIn("V-G09-01", str(e.exception))

    def test_e3_bon_thao_tac_chua_xac_minh_bi_cua_DUONG_DAN_dung(self):
        """Cửa đường dẫn, đo TRỰC TIẾP: mỗi thao tác phải nêu đúng tên nó và nguồn đã đọc."""
        for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            for mt in ("sandbox", "production"):
                with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                    aj.chan_duong_chua_xac_nhan(op, mt)
                self.assertEqual(e.exception.thao_tac, op)
                self.assertEqual(e.exception.moi_truong, mt)
                gop = " | ".join(e.exception.thieu).lower()
                self.assertIn("chưa", gop, f"{op}: lý do phải nói rõ là CHƯA")
                self.assertIn("xác minh", gop, f"{op}: lý do phải nói rõ ĐƯỜNG DẪN chưa xác minh")
        # ĐỐI CHỨNG DƯƠNG: hai thao tác ĐÃ xác minh thì cửa này KHÔNG ném.
        for op in ("createOrder", "trackOrder"):
            for mt in ("sandbox", "production"):
                self.assertIsNone(aj.chan_duong_chua_xac_nhan(op, mt))

    def test_e4_duong_dan_da_xac_minh_nhung_thieu_lop_HTTP_thi_dung(self):
        """Đường dẫn ĐÃ xác minh mà chưa có lớp HTTP ⇒ `ChuaXacNhanTaiLieu`, KHÔNG gửi rỗng."""
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            if aj.http_jt_dang_dung() is None:
                with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                    ad._chan_chua_chay_duoc("trackOrder")
                self.assertTrue(any("HTTP" in t for t in e.exception.thieu),
                                f"thiếu lý do lớp HTTP: {e.exception.thieu}")
        # ĐỐI CHỨNG DƯƠNG: ở mock thì CÙNG thao tác chạy được — nếu không, một bản "chặn tất
        # cả" cũng làm ca trên xanh một cách vô nghĩa.
        self.assertTrue(ad_mock().trackOrder("JTVN1").ok)

    def test_e5_huy_don_mock_van_dung_duoc_va_ghi_ro_truong_con_thieu(self):
        yc = ad_mock().yeu_cau_huy_don("MVD1", "khách huỷ")
        self.assertEqual(json.loads(yc["bizContent"])["txlogisticId"], "MVD1")
        self.assertIsNone(yc["url"])
        self.assertTrue(yc["thieu_truong"], "phải ghi rõ còn thiếu gì ngay ở mock")
        self.assertIsNone(aj.url_cua("cancelOrder", "sandbox"))

    def test_e6_ten_truong_ly_do_huy_dang_rong_va_khong_doan(self):
        self.assertEqual(aj.TRUONG_LY_DO_HUY, "",
                         "chưa đọc được tên trường lý do huỷ ⇒ để RỖNG, không đoán")
        biz = json.loads(ad_mock().yeu_cau_huy_don("MVD1", "khách huỷ")["bizContent"])
        for ten_doan in ("reason", "cancelReason", "remark", "cancelRemark"):
            self.assertNotIn(ten_doan, biz, f"KHÔNG được đoán tên trường {ten_doan!r}")

    def test_e7_tra_hanh_trinh_ton_trong_tran_30_ma(self):
        yc = ad_mock().yeu_cau_tra_hanh_trinh([f"MVD{i}" for i in range(30)])
        self.assertEqual(json.loads(yc["bizContent"])["billcodes"].count(","), 29)
        with self.assertRaises(lh.NormalizedCarrierError) as e:
            ad_mock().yeu_cau_tra_hanh_trinh([f"MVD{i}" for i in range(31)])
        self.assertEqual(e.exception.ma_goc_hang, "145003502")
        self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)

    def test_e8_tra_hanh_trinh_danh_sach_rong_thi_dung(self):
        for xau in ([], "", None):
            with self.assertRaises(lh.NormalizedCarrierError):
                ad_mock().yeu_cau_tra_hanh_trinh(xau)

    def test_e9_yeu_cau_tra_hanh_trinh_co_chu_ky_cua_chinh_no(self):
        yc = ad_mock().yeu_cau_tra_hanh_trinh(["A1", "B2"])
        self.assertEqual(yc["headers"]["digest"],
                         aj.ky_digest(yc["bizContent"], CRED_THU["privateKey"]))
        self.assertEqual(yc["body"]["bizContent"], yc["bizContent"])

    def test_e10_url_chi_co_o_hai_moi_truong_da_xac_minh(self):
        for mt in ("sandbox", "production"):
            self.assertTrue(aj.url_cua("createOrder", mt).startswith("https://"))
            self.assertTrue(aj.url_cua("trackOrder", mt).startswith("https://"))
            for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
                self.assertIsNone(aj.url_cua(op, mt), f"{op}/{mt} không được có URL")

    def test_e11_khong_them_duong_dan_nao_moi(self):
        """G16-A KHÔNG được nới bảng đường dẫn: bốn thao tác vẫn phải `duong=None`.

        Ca này là chốt chặn cho cám dỗ "đoán một URL cho đủ sáu thao tác" — đoán sai thì hãng
        từ chối và mình chẩn đoán nhầm hướng.
        """
        self.assertEqual(sorted(aj.DUONG_API), sorted(
            ["createOrder", "trackOrder", "cancelOrder", "getShippingFee", "getShippingLabel",
             "getOrder"]))
        for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            self.assertIsNone(aj.DUONG_API[op]["duong"], f"{op} bị gán URL chưa xác minh")
            self.assertEqual(aj.DUONG_API[op]["muc"], aj.MUC_CHUA_XAC_NHAN)


class F_KhongCoMaGoiMang(unittest.TestCase):
    """Adapter phải sạch mã gọi mạng — và bộ dò phải TỰ CHỨNG MINH nó dò được."""

    def test_f1_adapter_jt_khong_co_ma_goi_mang(self):
        with open(os.path.join(GOC_APP, "adapter_jt.py"), encoding="utf-8") as f:
            nguon = f.read()
        self.assertEqual(quet_goi_mang(nguon), [],
                         "adapter_jt.py có mã gọi mạng — mọi môi trường thật đang bị chặn,"
                         " nên dòng đó không ai kiểm mà vẫn chạy được")

    def test_f2_TU_KIEM_bo_do_thuc_su_do_duoc(self):
        """Nếu bộ dò hỏng (luôn trả rỗng) thì ca F1 xanh vô nghĩa. Ca này chứng minh nó dò được."""
        self.assertTrue(quet_goi_mang("import requests\n"))
        self.assertTrue(quet_goi_mang("x = urllib.request.urlopen(u)\n"))
        self.assertEqual(quet_goi_mang("import json\nimport hashlib\n"), [])

    def test_f3_http_jt_duoc_nap_LUOI_khong_o_dau_tep(self):
        """`http_jt` phải được nạp TRONG hàm. Nạp ở cấp module thì lúc AG-02 chưa viết xong,
        cả adapter chết vì một tệp của làn khác — và đó là hỏng THẬT, không phải hỏng giả."""
        import ast
        with open(os.path.join(GOC_APP, "adapter_jt.py"), encoding="utf-8") as f:
            cay = ast.parse(f.read())
        for n in cay.body:      # chỉ soi CẤP MODULE: import lồng trong hàm là đúng ý đồ
            if isinstance(n, ast.Import):
                for a in n.names:
                    self.assertNotEqual(a.name.split(".")[0], "http_jt",
                                        "http_jt bị nạp ở CẤP MODULE")
            elif isinstance(n, ast.ImportFrom):
                self.assertNotEqual((n.module or "").split(".")[0], "http_jt",
                                    "http_jt bị nạp ở CẤP MODULE")
        # TỰ KIỂM bộ dò: nó phải bắt được đúng khuôn sai đó.
        gia = ast.parse("import http_jt\n")
        self.assertTrue(any(isinstance(n, ast.Import)
                            and n.names[0].name.split(".")[0] == "http_jt" for n in gia.body),
                        "bộ dò không bắt được `import http_jt` ở cấp module ⇒ ca F3 vô nghĩa")


class H_MoiTruong_HaiCuaDocLap(unittest.TestCase):
    """§37 — `mock` là MẶC ĐỊNH; `sandbox`/`production` TỪ CHỐI kèm lý do; hai cửa ĐỘC LẬP.

    Vì sao tách nhóm riêng: trước G16 chỉ có MỘT cửa (`CHO_PHEP_LIVE`). Nay có BA, và bất biến
    quan trọng nhất là **mở một cửa KHÔNG mở hai cửa kia**. Không có nhóm này thì lần sau ai gộp
    ba cửa làm một cũng không ai biết.
    """

    def test_h1_mock_la_mac_dinh_va_khong_can_credential(self):
        ad = aj.AdapterJT({}, "mock")
        self.assertEqual(ad.moi_truong, "mock")
        self.assertTrue(aj.moi_truong_duoc_chay("mock"))
        self.assertTrue(ad.createOrder(dict(DON_MAU, ma_don="G16-H1")).ok)

    def test_h2_sandbox_va_production_mac_dinh_la_CHAN_kem_ly_do_doc_duoc(self):
        for mt in ("sandbox", "production"):
            self.assertFalse(aj.moi_truong_duoc_chay(mt), f"{mt} phải đang CHẶN")
            with self.assertRaises(PermissionError) as e:
                aj.chan_moi_truong_chua_duoc_cap(mt)
            self.assertIn(mt, str(e.exception))
            self.assertIn("§37", aj.ly_do_moi_truong(mt))
        self.assertIn("V-G09-01", aj.ly_do_moi_truong("sandbox"))
        self.assertIn("duyệt riêng", aj.ly_do_moi_truong("production"))

    def test_h3_moi_truong_LA_thi_TU_CHOI_khong_doan(self):
        for mt in ("staging", "", None, "prod", "sanbox"):
            self.assertFalse(aj.moi_truong_duoc_chay(mt), f"{mt!r} bị coi là được phép")
            with self.assertRaises(PermissionError):
                aj.chan_moi_truong_chua_duoc_cap(mt)

    def test_h4_duong_chay_that_tu_choi_ngay_luc_dung_adapter(self):
        """Cửa 1: `CHO_PHEP_LIVE=False` ⇒ dựng adapter ngoài mock đã nổ, chưa cần cửa nào khác."""
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False)
        for mt in ("sandbox", "production"):
            with self.assertRaises(PermissionError):
                adapter.tao_adapter("jt", dict(CRED_THU), mt)

    def test_h5_mo_CHO_PHEP_LIVE_KHONG_mo_duoc_moi_truong(self):
        """Cửa 1 (lớp nền) và cửa 2 (môi trường) ĐỘC LẬP — mở cửa này KHÔNG mở cửa kia.

        AG-00 chốt 15/10/2026 và yêu cầu ca này khẳng định đúng bất biến hai-cửa, theo hướng
        CHẶT HƠN: mở `CHO_PHEP_LIVE` rồi thì thao tác vẫn phải bị TỪ CHỐI, và lý do phải nêu
        đúng §37.
        """
        with ChoPhepLiveTam():
            self.assertTrue(aj.AdapterJT.CHO_PHEP_LIVE, "cửa 1 phải đang mở trong khối này")
            ad = aj.AdapterJT(dict(CRED_THU), "production")
            with self.assertRaises(PermissionError) as e:
                ad.trackOrder("MVD1")     # đường dẫn ĐÃ xác minh ⇒ cửa chặn chắc chắn là môi trường
            self.assertIn("duyệt riêng", str(e.exception))
            for ten, goi in (("getShippingFee", lambda: ad.getShippingFee(dict(DON_MAU))),
                             ("getShippingLabel", lambda: ad.getShippingLabel("MVD1"))):
                with self.assertRaises(PermissionError, msg=f"{ten} lọt qua cửa môi trường"):
                    goi()
            # `cancelOrder` dựng gói yêu cầu TRƯỚC khi hỏi cửa môi trường, và gói đó cần đường
            # dẫn chưa xác minh ⇒ nó dừng ở cửa ĐƯỜNG DẪN. Vẫn là DỪNG, khác chỗ dừng.
            with self.assertRaises(aj.ChuaXacNhanTaiLieu):
                ad.cancelOrder("MVD1")
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False, "cửa 1 phải được trả lại sau khối")

    def test_h6_mo_CHO_PHEP_LIVE_van_de_D9_chan_createOrder(self):
        """Cửa 2 và cửa 4 (D-9) cũng ĐỘC LẬP: mở cửa 1 không gỡ được chốt D-9."""
        with ChoPhepLiveTam():
            for mt in ("sandbox", "production"):
                ad = aj.AdapterJT(dict(CRED_THU), mt)
                with self.assertRaises(lh.NormalizedCarrierError) as e:
                    ad.createOrder(dict(DON_MAU))
                self.assertIn("D-9", e.exception.thong_diep)

    def test_h7_ba_cua_nguon_deu_DONG_va_moi_cua_mot_cho(self):
        """Ghim BA nguồn quyền, mỗi nguồn một chỗ — gộp chúng lại là mất chốt chặn."""
        import cau_hinh
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False, "cửa 1 (adapter.py)")
        self.assertIs(cau_hinh.JT_CHO_PHEP_SANDBOX, False, "cửa 2 sandbox (cau_hinh.py)")
        self.assertIs(cau_hinh.JT_CHO_PHEP_PRODUCTION, False, "cửa 2 production (cau_hinh.py)")
        self.assertEqual(cau_hinh.JT_MOI_TRUONG, "mock", "mặc định của hệ phải là mock")
        self.assertIs(aj.TRANSPORT_THAT_DA_VIET, aj._co_http_jt(),
                      "cờ transport phải là ẢNH CHỤP của phép dò, không phải hằng viết tay")
        self.assertIsNone(aj.DIEM_CUOI_GHI_DE, "điểm cuối thay thế phải TRỐNG ở cây bàn giao")
        # Bảng quyền KHÔNG được nhân bản trong tệp adapter: chỉ `cau_hinh` được phán.
        self.assertFalse(hasattr(aj, "UY_QUYEN_MOI_TRUONG"),
                         "adapter_jt tự dựng bảng quyền song song với cau_hinh ⇒ hai bảng sẽ lệch")

    def test_h8_seam_diem_cuoi_TU_CHOI_dia_chi_ngoai_vong_lap(self):
        """TỰ KIỂM: seam của bộ thử không được là một đường gọi ra Internet."""
        for xau in ("https://demoopenapi.jtexpress.vn", "http://10.0.0.1:80",
                    "https://ylopenapi.jtexpress.vn", "ftp://127.0.0.1"):
            with self.assertRaises(ValueError, msg=f"nhận nhầm {xau}"):
                aj.DungDiemCuoiTam(xau)
        for tot in ("http://127.0.0.1:8123", "http://localhost:9", "http://[::1]:9"):
            with aj.DungDiemCuoiTam(tot):
                self.assertTrue(aj.url_cua("createOrder", "sandbox").startswith(tot))
            self.assertIsNone(aj.DIEM_CUOI_GHI_DE, "hết khối `with` phải trả lại giá trị cũ")

    def test_h9_ghi_de_diem_cuoi_KHONG_bia_duong_dan_chua_xac_minh(self):
        """Ghi đè điểm cuối chỉ đổi HOST: thao tác chưa biết đường dẫn vẫn phải `None`."""
        with aj.DungDiemCuoiTam("http://127.0.0.1:8123"):
            for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
                self.assertIsNone(aj.url_cua(op, "sandbox"),
                                  f"{op}: ghi đè điểm cuối biến đường dẫn CHƯA BIẾT thành có thật")


class G_DuongNoiCredentials(unittest.TestCase):
    """J03 — credentials đi từ bản mã `v3$…` (AES-256-GCM) tới adapter, KHÔNG qua đường khác.

    Ca kiểm ở đây chỉ dùng giá trị GIẢ do bộ thử tự dựng. Danh sách credentials THẬT còn thiếu
    là bốn TÊN trường (`apiAccount`, `privateKey`, `customerCode`, `password`) — xem
    `docs/G13_JT_API.md` mục BLOCKED và `docs/G09_CREDENTIALS_CHECKLIST.md`.
    """

    CRED = {"apiAccount": "ACC-GIA", "privateKey": "KHOA-GIA", "customerCode": "CC-GIA",
            "password": "MK-GIA"}
    TENANT = 4242

    def test_g1_ban_ma_mang_key_id_v3_va_khong_lo_gia_tri(self):
        import bao_mat
        ban_ma, _duoi = bao_mat.ma_hoa_cred(dict(self.CRED), self.TENANT, "jt")
        self.assertTrue(ban_ma.startswith("v3$"), f"thiếu key_id để xoay khoá: {ban_ma[:6]}")
        self.assertGreaterEqual(ban_ma.count("$"), 3)
        for gia_tri in self.CRED.values():
            self.assertNotIn(gia_tri, ban_ma, "bản mã chứa giá trị đọc được")

    def test_g2_chi_dung_tenant_va_hang_moi_giai_ma_duoc(self):
        import bao_mat
        ban_ma, _ = bao_mat.ma_hoa_cred(dict(self.CRED), self.TENANT, "jt")
        self.assertEqual(bao_mat.giai_ma_cred(ban_ma, self.TENANT, "jt"), self.CRED)
        for tenant, hang in ((self.TENANT + 1, "jt"), (self.TENANT, "vtp")):
            try:
                ra = bao_mat.giai_ma_cred(ban_ma, tenant, hang)
            except Exception:                       # noqa: BLE001 — chặn được là tốt
                continue
            self.assertNotEqual(ra, self.CRED,
                                f"giải mã được bằng (tenant={tenant}, hang={hang}) — AAD hở")

    def test_g3_adapter_dung_dung_credentials_da_giai_ma(self):
        import bao_mat
        ban_ma, _ = bao_mat.ma_hoa_cred(dict(self.CRED), self.TENANT, "jt")
        ad = adapter.tao_adapter("jt", bao_mat.giai_ma_cred(ban_ma, self.TENANT, "jt"), "mock")
        yc = ad.yeu_cau_tao_don(dict(DON_MAU))
        biz = json.loads(yc["bizContent"])
        self.assertEqual(biz["customerCode"], self.CRED["customerCode"])
        self.assertEqual(biz["password"], self.CRED["password"])
        self.assertEqual(yc["headers"]["apiAccount"], self.CRED["apiAccount"])
        self.assertEqual(yc["headers"]["digest"],
                         aj.ky_digest(yc["bizContent"], self.CRED["privateKey"]))
        self.assertNotIn(self.CRED["privateKey"], json.dumps(ad.createOrder(dict(DON_MAU)).tho))

    def test_g4_adapter_jt_khong_tu_ma_hoa_credentials(self):
        """Bốn hàm contract (mục 14) là đường DUY NHẤT chạm secret — adapter không được tự gọi."""
        import re
        with open(os.path.join(GOC_APP, "adapter_jt.py"), encoding="utf-8") as f:
            nguon = f.read()
        mau = re.compile(r"bao_mat\s*\.\s*(ma_hoa|giai_ma)(?!_(cred|wh))")
        self.assertIsNone(mau.search(nguon), "adapter_jt.py tự gọi hàm mã hoá trần")
        # TỰ KIỂM bộ dò: nếu mẫu hỏng thì ca trên xanh vô nghĩa.
        self.assertIsNotNone(mau.search("x = bao_mat.ma_hoa(ro, aad)"))
        self.assertIsNone(mau.search("x = bao_mat.ma_hoa_cred(c, t, h)"))


class I_ThieuTruongHanhChinh(unittest.TestCase):
    """AG-03 — NHÁNH BIÊN của trường hành chính: thiếu cột nào thì phải NÓI ĐÚNG cột đó.

    Vì sao nhóm này tồn tại dù nhóm D đã có D6/D7: D6/D7 đo "thiếu CẢ BỐN thì có bị chặn không".
    Đó là một ca, không phải một phép đo — nó xanh kể cả khi hàm trả về một danh sách cứng bốn
    phần tử, hoặc khi nó chỉ đếm mà không nói TÊN cột. Ở đây mỗi cột được đo RIÊNG, và mỗi ca
    phủ định đều có ĐỐI CHỨNG DƯƠNG ngay cạnh: điền đúng cột đó vào thì nó phải BIẾN MẤT khỏi
    danh sách thiếu. Thiếu vế đối chứng thì một hàm `return ["a","b","c","d"]` cũng làm mọi ca
    dưới đây xanh.
    """

    BON_COT = ("nguoi_gui_tinh", "nguoi_gui_quan", "nguoi_nhan_tinh", "nguoi_nhan_quan")

    def test_i1_moi_cot_do_rieng_va_doi_chung_duong_bien_mat(self):
        for cot in self.BON_COT:
            thieu_don = dict(DON_MAU)
            thieu_don.pop(cot)
            self.assertEqual(ad_mock().truong_hanh_chinh_thieu(thieu_don), [cot],
                             f"thiếu {cot} mà không nói đúng tên cột đó")
            # ĐỐI CHỨNG DƯƠNG: điền lại ĐÚNG cột ấy ⇒ hết thiếu. Cùng một đơn, khác một trường.
            self.assertEqual(ad_mock().truong_hanh_chinh_thieu(dict(DON_MAU)), [],
                             f"đơn đầy đủ mà vẫn báo thiếu (đang đo {cot})")

    def test_i2_bien_rong_khoang_trang_None_va_doi_chung_duong(self):
        """Rỗng · toàn khoảng trắng · None đều là THIẾU. Chuỗi thật là ĐỦ (đối chứng)."""
        for gia_tri in ("", "   ", "\t\n", None):
            don = dict(DON_MAU, nguoi_gui_tinh=gia_tri)
            self.assertIn("nguoi_gui_tinh", ad_mock().truong_hanh_chinh_thieu(don),
                          f"giá trị {gia_tri!r} bị coi là ĐÃ ĐIỀN")
        # ĐỐI CHỨNG DƯƠNG: cùng cột đó, một chuỗi thật ⇒ đủ.
        self.assertNotIn("nguoi_gui_tinh",
                         ad_mock().truong_hanh_chinh_thieu(dict(DON_MAU, nguoi_gui_tinh="Huế")))

    def test_i3_mock_thieu_thi_ghi_danh_sach_chu_khong_chan(self):
        """Ở mock đơn THIẾU vẫn dựng được (dữ liệu demo chưa có địa chỉ) — nhưng phải GHI LẠI."""
        don = dict(DON_MAU)
        for cot in self.BON_COT:
            don.pop(cot)
        yc = ad_mock().yeu_cau_tao_don(don)
        self.assertEqual(sorted(yc["thieu_truong"]), sorted(self.BON_COT))
        # ĐỐI CHỨNG DƯƠNG: đơn đủ thì KHÔNG có khoá đó — nếu khoá luôn xuất hiện thì ca trên
        # chỉ chứng minh "có một khoá tên thieu_truong", không chứng minh nó phản ánh dữ liệu.
        self.assertNotIn("thieu_truong", ad_mock().yeu_cau_tao_don(dict(DON_MAU)))

    def test_i4_ngoai_mock_thieu_thi_DUNG_va_neu_dung_TEN_COT(self):
        with ChoPhepLiveTam():
            for cot in self.BON_COT:
                don = dict(DON_MAU)
                don.pop(cot)
                ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
                with self.assertRaises(lh.NormalizedCarrierError) as e:
                    ad.yeu_cau_tao_don(don)
                self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)
                self.assertIn(cot, e.exception.thong_diep,
                              f"lỗi không nêu TÊN cột {cot} — người sửa phải đoán")
                self.assertIn("1450033315", e.exception.thong_diep,
                              "phải nêu mã lỗi hãng sẽ trả, để tra được tài liệu")

    def test_i5_DOI_CHUNG_DUONG_du_dia_chi_thi_di_QUA_cua_hanh_chinh(self):
        """Đối chứng PHÂN BIỆT cho I4: cùng môi trường, đơn ĐỦ địa chỉ ⇒ lỗi KHÁC HẲN.

        Nếu cửa hành chính chặn nhầm cả đơn đủ dữ liệu thì I4 vẫn xanh (nó chỉ đòi "có ném"),
        và trên đời sẽ không đơn nào gửi được. Ở đây đơn đủ đi qua cửa đó và dừng ở chốt D-9 —
        tức nó đã đi XA HƠN I4 đúng một cửa. Đó mới là bằng chứng cửa hành chính phân biệt được.
        """
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                ad.yeu_cau_tao_don(dict(DON_MAU))
            self.assertIn("D-9", e.exception.thong_diep,
                          "đơn đủ địa chỉ phải đi qua cửa hành chính rồi mới dừng ở D-9")
            self.assertNotIn("thiếu trường hành chính", e.exception.thong_diep)

    def test_i6_danh_sach_thieu_khong_bao_gio_duoc_gui_len_hang(self):
        don = dict(DON_MAU, nguoi_nhan_quan="")
        yc = ad_mock().yeu_cau_tao_don(don)
        self.assertEqual(yc["thieu_truong"], ["nguoi_nhan_quan"])
        self.assertNotIn("thieu_truong", yc["bizContent"])
        self.assertNotIn("thieu_truong", json.dumps(json.loads(yc["bizContent"])))


class J_TienSaiDinhDang(unittest.TestCase):
    """AG-03 — BIÊN của tiền: mọi cách viết hỏng đều ra `THAM_SO_SAI`, và KHÔNG làm tròn im lặng.

    Mỗi dòng của `BANG` là một CẶP: (cách viết HỎNG, cách viết HỢP LỆ gần nhất, giá trị đúng).
    Cặp là điểm mấu chốt — một ca phủ định đứng một mình chỉ chứng minh "có ném", còn cặp chứng
    minh hàm PHÂN BIỆT được: cùng một chỗ gọi, đổi đúng một ký tự thì đi qua.
    """

    # (hỏng, hợp lệ, giá trị nguyên đúng)
    BANG = (
        (15000.5,       15000,        15000),
        ("15000.5",     "15000",      15000),
        (0.1,           0,            0),
        (-1,            0,            0),
        ("-5",          "5",          5),
        (True,          1,            1),
        ("mười nghìn",  "10000",      10000),
        ("nan",         "0",          0),
        ("inf",         "0",          0),
        (float("nan"),  0.0,          0),
        ("²",           "2",          2),
        ("١٢٣",         "123",        123),
        ("１５００",     "1500",       1500),
        ("1,5",         "15",         15),
    )

    def _biz(self, **them):
        return json.loads(ad_mock().yeu_cau_tao_don(dict(DON_MAU, **them))["bizContent"])

    def test_j1_moi_dong_la_mot_CAP_phu_dinh_va_doi_chung_duong(self):
        for xau, tot, mong in self.BANG:
            with self.subTest(xau=xau):
                # (1) CÁCH VIẾT HỎNG ⇒ ném, mã chuẩn THAM_SO_SAI (không phải ValueError trần).
                with self.assertRaises(lh.NormalizedCarrierError) as e:
                    self._biz(cod=xau)
                self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)
                # (2) ĐỐI CHỨNG DƯƠNG: cách viết hợp lệ GẦN NHẤT, cùng chỗ gọi, đi qua và ra
                #     ĐÚNG giá trị. Không có vế này thì (1) xanh kể cả khi hàm chặn tất cả.
                self.assertEqual(self._biz(cod=tot)["codMoney"], str(mong))

    def test_j2_TU_KIEM_cac_dang_hong_thuc_su_tung_lam_hong_duong_cu(self):
        """Chứng minh ba dạng dưới đây KHÔNG phải ca tưởng tượng — chúng đánh lừa được `isdigit`.

        Không có ca này thì J1 vẫn xanh, nhưng người đọc không biết dòng `"²"` là một lỗi THẬT
        đã đo được hay chỉ là phòng xa. Đây là phép đo trên chính Python đang chạy.
        """
        self.assertTrue("²".isdigit(), "tiền đề của ca '²' không còn đúng trên Python này")
        with self.assertRaises(ValueError):
            int("²")        # ⇒ đường cũ ném ValueError TRẦN, phá hợp đồng mã lỗi §5
        for chuoi in ("١٢٣", "１５００"):
            self.assertTrue(chuoi.isdigit())
            self.assertFalse(chuoi.isascii())
            self.assertIsInstance(int(chuoi), int)   # đọc ĐƯỢC ⇒ đường cũ ĐỔI IM LẶNG
        self.assertTrue("15000".isascii() and "15000".isdigit())

    def test_j3_khong_lam_tron_im_lang_bang_chung_so_hoc(self):
        """`int(15000.7)` là 15000 — nếu hàm làm tròn, KẾT QUẢ TRÔNG VẪN HỢP LỆ và sai 0,7 đồng."""
        self.assertEqual(int(15000.7), 15000, "tiền đề của ca này đã đổi")
        with self.assertRaises(lh.NormalizedCarrierError):
            self._biz(cod=15000.7)
        # và điều KHÔNG được xảy ra: một gói yêu cầu ra đời với con số đã bị bỏ phần lẻ.
        self.assertEqual(self._biz(cod=15000)["codMoney"], "15000")

    def test_j4_bien_0_va_so_nguyen_lon_di_DUNG_duong_int(self):
        """BIÊN: 0 đi qua (COD 0 là đơn không thu tiền, KHÁC với 'thiếu dữ liệu').

        Số nguyên lớn là ca biên thật: `float(2**53+1)` mất đúng 1 đồng. Đi qua `float()` là một
        đường làm lệch tiền mà không có lỗi nào báo, nên ca này ghim cả giá trị LẪN đường đi.
        """
        self.assertEqual(self._biz(cod=0)["codMoney"], "0")
        lon = 2 ** 53 + 1
        self.assertEqual(self._biz(cod=lon)["codMoney"], str(lon))
        self.assertEqual(self._biz(cod=str(lon))["codMoney"], str(lon))
        self.assertNotEqual(int(float(lon)), lon, "tiền đề: float() thật sự làm lệch số nguyên lớn")

    def test_j5_GIOI_HAN_DO_DUOC_float_mat_tien_TRUOC_khi_vao_adapter(self):
        """GIỚI HẠN ĐÃ ĐO, ghi lại bằng ca kiểm thay vì bằng lời hứa.

        `tien_nguyen_vnd(9007199254740993.0)` KHÔNG ném: giá trị đã thành `...992.0` từ TRƯỚC,
        ở chỗ gọi, và thông tin đã mất — không hàm nào đọc lại được. Đây không phải lỗi của hàm
        kiểm (nó vẫn đúng: nhận được một số nguyên), mà là một ĐƯỜNG ỐNG còn hở: tiền đi vào
        bằng `float` thì có thể lệch 1 đồng mà không ai báo.

        Ca này GHIM sự thật đó lại, để:
          · không ai đọc docstring rồi tin rằng float luôn bị chặn (nó chỉ bị chặn khi CÓ phần lẻ);
          · đường ĐÚNG (`int` hoặc chuỗi) được đo ngay cạnh và giữ nguyên giá trị;
          · việc còn phải làm hiện ra: chặn `float` ở tầng nhập liệu là việc của Order Service,
            NẰM NGOÀI phạm vi tệp adapter này.
        """
        lon = 2 ** 53 + 1
        mat = int(float(lon))
        self.assertNotEqual(mat, lon)
        self.assertEqual(self._biz(cod=float(lon))["codMoney"], str(mat),
                         "float vào thẳng hàm kiểm mà không bị chặn — đúng như đã đo")
        self.assertEqual(self._biz(cod=lon)["codMoney"], str(lon), "đường int giữ nguyên")
        self.assertEqual(self._biz(cod=str(lon))["codMoney"], str(lon), "đường chuỗi giữ nguyên")
        # Và cái CHẮC CHẮN phải chặn thì vẫn chặn: float có phần lẻ.
        self.assertEqual(float(lon) + 0.5, float(lon),
                         "tiền đề: ở cỡ này float không còn biểu diễn được nửa đồng")
        with self.assertRaises(lh.NormalizedCarrierError):
            self._biz(cod=15000.5)

    def test_j6_cung_bien_do_cho_gia_tri_khai_va_khoi_luong(self):
        """Ba trường tiền dùng CHUNG một hàm — đo cả ba, không chỉ `cod` (chỗ dễ nhìn nhất)."""
        for truong in ("gia_tri_khai", "khoi_luong_gram", "cod"):
            for xau in (15000.5, "15000.5", "²", "١٢٣"):
                with self.assertRaises(lh.NormalizedCarrierError, msg=f"{truong}={xau!r}"):
                    self._biz(**{truong: xau})
            self.assertTrue(self._biz(**{truong: 15000}))

    def test_j7_mock_KHONG_duoc_du_dai_hon_duong_that(self):
        """Ở mock tiền hỏng vẫn phải NỔ: mock không được là chỗ duy nhất bỏ qua phép kiểm."""
        with self.assertRaises(lh.NormalizedCarrierError) as e:
            ad_mock().yeu_cau_tao_don(dict(DON_MAU, cod="15000.5"))
        self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)
        # ĐỐI CHỨNG DƯƠNG: cùng adapter, cùng đơn, tiền hợp lệ ⇒ dựng được gói.
        self.assertTrue(ad_mock().yeu_cau_tao_don(dict(DON_MAU))["bizContent"])


class K_ChotCungBonDuongChuaXacMinh(unittest.TestCase):
    """AG-03 — CA CANH cho chốt cứng: bốn thao tác chưa xác minh phải giữ `duong=None`.

    Vì sao cần một ca RIÊNG ngoài B2/E3/E10/E11: những ca kia khẳng định TRẠNG THÁI ("đang là
    None"). Chúng xanh miễn là chưa ai sửa gì, và chúng không phân biệt được hai tình huống:
    (a) bảng sạch, (b) bộ dò hỏng nên không thấy gì. Nhóm này khẳng định thêm hai điều:
      · bộ dò `vi_pham_chot_duong_dan()` THẬT SỰ bắt được một URL bừa (TỰ KIỂM, có bơm dữ liệu);
      · khi bảng bị bơm URL bừa vào CHÍNH module đang chạy thì ĐƯỜNG CHẠY vẫn không có URL —
        tức chốt không chỉ nằm trong bộ thử.
    """

    # URL bừa điển hình của cám dỗ "ghép tiền tố cổng cho đủ sáu thao tác".
    URL_BUA = {
        "cancelOrder": "/webopenplatformapi/api/order/cancelOrder",
        "getShippingFee": "/webopenplatformapi/api/fees/calculatingFees",
        "getShippingLabel": "/webopenplatformapi/api/vip/printOrder",
        "getOrder": "/webopenplatformapi/api/order/getOrder",
    }

    def _bang_gia(self, op=None, duong=None, muc=None, xoa=False):
        """Bản SAO của bảng đường dẫn, có bơm lỗi. Không bao giờ chạm bảng thật."""
        bang = {k: dict(v) for k, v in aj.DUONG_API.items()}
        if xoa:
            bang.pop(op, None)
        else:
            bang[op]["duong"] = duong
            if muc is not None:
                bang[op]["muc"] = muc
        return bang

    def test_k1_bang_that_hien_tai_sach(self):
        self.assertEqual(aj.vi_pham_chot_duong_dan(), [],
                         f"bảng đường dẫn tự mâu thuẫn: {aj.vi_pham_chot_duong_dan()}")

    def test_k2_TU_KIEM_bo_do_THAT_SU_bat_duoc_URL_bua(self):
        """Bơm URL bừa vào bảng GIẢ ⇒ bộ dò PHẢI kêu. Không có ca này thì K1 vô nghĩa."""
        for op, duong in self.URL_BUA.items():
            vi_pham = aj.vi_pham_chot_duong_dan(self._bang_gia(op, duong))
            self.assertTrue(any(v.startswith(op + ":") for v in vi_pham),
                            f"bộ dò bỏ sót URL bừa của {op}: {vi_pham}")
        # Bơm kiểu thứ hai: đổi `muc` thành "đã xác minh" mà không có đường dẫn.
        vi_pham = aj.vi_pham_chot_duong_dan(
            self._bang_gia("cancelOrder", None, muc=aj.MUC_DA_DOC))
        self.assertTrue(any("muc=" in v for v in vi_pham), vi_pham)
        # Bơm kiểu thứ ba: xoá hẳn thao tác khỏi bảng (chốt biến mất cùng dòng).
        vi_pham = aj.vi_pham_chot_duong_dan(self._bang_gia("getOrder", xoa=True))
        self.assertTrue(any("BIẾN MẤT" in v for v in vi_pham), vi_pham)
        # ĐỐI CHỨNG ÂM: bảng giả KHÔNG bơm gì thì bộ dò phải im — nếu không, nó kêu vì lý do khác.
        self.assertEqual(aj.vi_pham_chot_duong_dan(
            {k: dict(v) for k, v in aj.DUONG_API.items()}), [])

    def test_k3_bom_URL_bua_vao_MODULE_DANG_CHAY_thi_duong_chay_VAN_tu_choi(self):
        """Ca mạnh nhất của nhóm: sửa THẬT bảng của module rồi đo đường chạy.

        Chốt phải nằm ở MÃ, không chỉ ở bộ thử. Nếu ai đó gán bừa `duong` cho `cancelOrder`:
          · `vi_pham_chot_duong_dan()` kêu ⇒ K1/K2 ĐỎ (bộ thử bắt được);
          · `url_cua()` vẫn None, kể cả dưới điểm cuối thay thế ⇒ chưa kịp có bộ thử thì cũng
            không có lượt gọi nào đi ra.
        """
        goc = aj.DUONG_API["cancelOrder"]["duong"]
        try:
            aj.DUONG_API["cancelOrder"]["duong"] = self.URL_BUA["cancelOrder"]
            self.assertNotEqual(aj.vi_pham_chot_duong_dan(), [],
                                "bộ dò không thấy URL bừa vừa gán vào bảng THẬT")
            self.assertIsNone(aj.url_cua("cancelOrder", "sandbox"),
                              "gán `duong` là mở được đường ra — chốt nằm ở sai chỗ")
            self.assertIsNone(aj.url_cua("cancelOrder", "production"))
            with aj.DungDiemCuoiTam("http://127.0.0.1:8123"):
                self.assertIsNone(aj.url_cua("cancelOrder", "sandbox"),
                                  "điểm cuối thay thế biến URL bừa thành URL thật")
            with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                aj.chan_duong_chua_xac_nhan("cancelOrder", "sandbox")
            self.assertTrue(any("MÂU THUẪN" in t for t in e.exception.thieu),
                            f"lý do chặn không nói ra mâu thuẫn: {e.exception.thieu}")
        finally:
            aj.DUONG_API["cancelOrder"]["duong"] = goc
        self.assertIsNone(aj.DUONG_API["cancelOrder"]["duong"], "ca kiểm không trả lại bảng gốc")
        self.assertEqual(aj.vi_pham_chot_duong_dan(), [])

    def test_k4_bon_thao_tac_giu_None_va_muc_chua_xac_nhan(self):
        self.assertEqual(tuple(aj.THAO_TAC_CHUA_XAC_MINH),
                         ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"))
        for op in aj.THAO_TAC_CHUA_XAC_MINH:
            self.assertIsNone(aj.DUONG_API[op]["duong"], f"{op} bị gán URL chưa xác minh")
            self.assertEqual(aj.DUONG_API[op]["muc"], aj.MUC_CHUA_XAC_NHAN)
            self.assertIsNone(aj.duong_da_xac_minh(op), f"{op} có đường dẫn 'đã xác minh'")
        # ĐỐI CHỨNG DƯƠNG: hai thao tác ĐÃ xác minh vẫn có đường dẫn (chốt không chặn nhầm).
        for op in ("createOrder", "trackOrder"):
            self.assertTrue(str(aj.duong_da_xac_minh(op) or "").startswith("/"))

    def test_k5_khong_moi_truong_nao_co_URL_cho_bon_thao_tac_nay(self):
        for op in aj.THAO_TAC_CHUA_XAC_MINH:
            for mt in ("mock", "sandbox", "production"):
                self.assertIsNone(aj.url_cua(op, mt), f"{op}/{mt} có URL")
            with self.assertRaises(aj.ChuaXacNhanTaiLieu):
                aj.chan_duong_chua_xac_nhan(op, "sandbox")
        self.assertIsNone(aj.DUONG_API["cancelOrder"]["duong"])
        self.assertEqual(aj.DUONG_API["cancelOrder"]["duong_tuong_doi_da_doc"],
                         "/api/order/cancelOrder",
                         "đường dẫn tương đối đã đọc vẫn phải được GHI LẠI, chỉ không được dùng")

    def test_k6_ten_tai_lieu_khop_voi_cau_hoi_dang_cho_hang(self):
        """Bảng tên để người đọc nối 'việc còn thiếu' với câu hỏi đã gửi J&T."""
        self.assertEqual(aj.TEN_TAI_LIEU_CUA_THAO_TAC["getShippingFee"], "calculatingFees")
        self.assertEqual(aj.TEN_TAI_LIEU_CUA_THAO_TAC["getShippingLabel"], "printOrder")
        self.assertEqual(aj.TEN_TAI_LIEU_CUA_THAO_TAC["cancelOrder"], "cancelOrder")
        for op in aj.THAO_TAC_CHUA_XAC_MINH:
            self.assertTrue(str(aj.TEN_TAI_LIEU_CUA_THAO_TAC.get(op) or "").strip(),
                            f"{op} chưa có tên trang tài liệu")

    def test_k7_khong_co_URL_tuyet_doi_nao_khac_trong_tep_adapter(self):
        """Quét NGUỒN: đổi bảng là một đường, dán thẳng một URL vào chỗ khác là đường thứ hai."""
        with open(os.path.join(GOC_APP, "adapter_jt.py"), encoding="utf-8") as f:
            nguon = f.read()
        self.assertEqual(quet_url_bua(nguon), [],
                         "adapter_jt.py có URL tuyệt đối cho thao tác CHƯA xác minh")
        # TỰ KIỂM bộ dò: nếu mẫu hỏng thì ca trên xanh vô nghĩa.
        self.assertTrue(quet_url_bua(
            'u = "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/cancelOrder"\n'))
        self.assertTrue(quet_url_bua(
            'u = "https://demoopenapi.jtexpress.vn/api/vip/printOrder"\n'))
        self.assertEqual(quet_url_bua(
            'u = "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder"\n'), [])


if __name__ == "__main__":
    kq = unittest.main(verbosity=2, exit=False).result
    print()
    print("=" * 78)
    print("PHẠM VI ĐÃ ĐO: gói yêu cầu do app/adapter_jt.py DỰNG RA ở môi trường mock (chữ ký,")
    print("  thân form, tiền/COD, ánh xạ `area`, bảng đường dẫn). KHÔNG gửi lượt nào ra mạng.")
    print("NẰM NGOÀI: J&T có chấp nhận chữ ký/tham số này không; sandbox hãng có sống không;")
    print("  đường dẫn của cancelOrder / calculatingFees / printOrder có đúng không —")
    print("  cả ba đang BLOCKED (chưa đọc được tài liệu, chưa có credentials).")
    print(f"Tổng: {kq.testsRun} ca · hỏng {len(kq.failures)} · lỗi {len(kq.errors)} "
          f"· bỏ qua {len(kq.skipped)}")
    print("=" * 78)
    sys.exit(bool(kq.failures or kq.errors))
