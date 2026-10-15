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

    def test_e1_bon_thao_tac_chua_xac_minh_bi_dung_ngoai_mock(self):
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            for ten, goi in (("cancelOrder", lambda: ad.cancelOrder("MVD1", "khách huỷ")),
                             ("getShippingFee", lambda: ad.getShippingFee(dict(DON_MAU))),
                             ("getShippingLabel", lambda: ad.getShippingLabel("MVD1"))):
                with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                    goi()
                self.assertEqual(e.exception.thao_tac, ten)
                self.assertTrue(any("chưa xác minh" in t for t in e.exception.thieu),
                                f"{ten}: phải nói rõ đường dẫn chưa xác minh")
                self.assertEqual(e.exception.moi_truong, "sandbox")

    def test_e2_trackOrder_qua_duoc_cua_duong_dan_nhung_dung_o_cua_transport(self):
        """Đường dẫn tra hành trình ĐÃ xác minh ⇒ chốt còn lại là lớp transport chưa viết."""
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                ad.trackOrder("MVD1")
            self.assertTrue(any("transport" in t for t in e.exception.thieu),
                            f"thiếu lý do transport: {e.exception.thieu}")

    def test_e3_khong_co_lop_transport_that(self):
        self.assertIs(aj.TRANSPORT_THAT_DA_VIET, False)
        self.assertIs(aj.AdapterJT.TRANSPORT_THAT_DA_VIET, False)

    def test_e4_huy_don_mock_van_dung_duoc_va_ghi_ro_truong_con_thieu(self):
        yc = ad_mock().yeu_cau_huy_don("MVD1", "khách huỷ")
        self.assertEqual(json.loads(yc["bizContent"])["txlogisticId"], "MVD1")
        self.assertIsNone(yc["url"])
        self.assertTrue(yc["thieu_truong"], "phải ghi rõ còn thiếu gì ngay ở mock")
        self.assertIsNone(aj.url_cua("cancelOrder", "sandbox"))

    def test_e5_ten_truong_ly_do_huy_dang_rong_va_khong_doan(self):
        self.assertEqual(aj.TRUONG_LY_DO_HUY, "",
                         "chưa đọc được tên trường lý do huỷ ⇒ để RỖNG, không đoán")
        biz = json.loads(ad_mock().yeu_cau_huy_don("MVD1", "khách huỷ")["bizContent"])
        for ten_doan in ("reason", "cancelReason", "remark", "cancelRemark"):
            self.assertNotIn(ten_doan, biz, f"KHÔNG được đoán tên trường {ten_doan!r}")

    def test_e6_tra_hanh_trinh_ton_trong_tran_30_ma(self):
        yc = ad_mock().yeu_cau_tra_hanh_trinh([f"MVD{i}" for i in range(30)])
        self.assertEqual(json.loads(yc["bizContent"])["billcodes"].count(","), 29)
        with self.assertRaises(lh.NormalizedCarrierError) as e:
            ad_mock().yeu_cau_tra_hanh_trinh([f"MVD{i}" for i in range(31)])
        self.assertEqual(e.exception.ma_goc_hang, "145003502")
        self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)

    def test_e7_tra_hanh_trinh_danh_sach_rong_thi_dung(self):
        for xau in ([], "", None):
            with self.assertRaises(lh.NormalizedCarrierError):
                ad_mock().yeu_cau_tra_hanh_trinh(xau)

    def test_e8_yeu_cau_tra_hanh_trinh_co_chu_ky_cua_chinh_no(self):
        yc = ad_mock().yeu_cau_tra_hanh_trinh(["A1", "B2"])
        self.assertEqual(yc["headers"]["digest"],
                         aj.ky_digest(yc["bizContent"], CRED_THU["privateKey"]))
        self.assertEqual(yc["body"]["bizContent"], yc["bizContent"])

    def test_e9_url_chi_co_o_hai_moi_truong_da_xac_minh(self):
        for mt in ("sandbox", "production"):
            self.assertTrue(aj.url_cua("createOrder", mt).startswith("https://"))
            self.assertTrue(aj.url_cua("trackOrder", mt).startswith("https://"))
            for op in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
                self.assertIsNone(aj.url_cua(op, mt), f"{op}/{mt} không được có URL")


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
