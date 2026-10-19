# Bộ thử LỚP HỢP ĐỒNG BEST CHÍNH THỨC — không gọi mạng, không credential.
#
# Mục tiêu: canh đúng tên trường tài liệu chính thức, parser Result/Message/data/traceLogs,
# bảng 23 mã, và cổng phê duyệt Owner (không sửa cờ adapter).
import json
import os
import sys
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

import best_hop_dong as bhd  # noqa: E402


def don_mau(**thua):
    d = {
        "ma_don": "MD-UAT-1",
        "hang_hoa": "Hàng kiểm thử",
        "nguoi_gui_ten": "Nguyễn Gửi",
        "nguoi_gui_sdt": "0901000001",
        "nguoi_gui_tinh": "Hồ Chí Minh",
        "nguoi_gui_quan": "Bình Thạnh",
        "nguoi_gui_xa": "Phường 12",
        "nguoi_gui_dia_chi": "12 Đường ABCD",
        "nguoi_nhan_ten": "Trần Nhận",
        "nguoi_nhan_sdt": "0902000002",
        "nguoi_nhan_tinh": "Hồ Chí Minh",
        "nguoi_nhan_quan": "Tân Bình",
        "nguoi_nhan_xa": "Phường 10",
        "nguoi_nhan_dia_chi": "34 Đường XYZ",
        "khoi_luong_gram": 500,
        "chieu_dai_mm": 100,
        "chieu_rong_mm": 100,
        "chieu_cao_mm": 100,
        "cod": 150000,
        "gia_tri_khai": 300000,
        "journey_type": 1,
    }
    d.update(thua)
    return d


class TestBuilder(unittest.TestCase):
    def test_01_login_dung_hai_truong(self):
        p = bhd.dung_login("user", "pass")
        self.assertEqual(set(p), {"Username", "Password"})

    def test_02_order_add_31_truong_chinh_thuc(self):
        p = bhd.dung_order_add(don_mau(), {"merchant_order_code": "MD-UAT-1"})
        self.assertEqual(len(p), 31)
        for ten in ("Code", "ProductName", "SourceCity", "SourceDistrict", "SourceWard",
                    "SourceAddress", "SourceName", "SourcePhoneNumber", "DestCity",
                    "DestDistrict", "DestWard", "DestAddress", "DestName", "DestPhoneNumber",
                    "ReturnCity", "ReturnDistrict", "ReturnWard", "ReturnAddress",
                    "ReturnName", "ReturnPhoneNumber", "ServiceId", "Weight", "Length",
                    "Width", "Height", "CollectAmount", "ProductPrice", "JourneyType",
                    "PickupType", "Note", "ShipmentPayer"):
            self.assertIn(ten, p, ten)
        self.assertNotIn("TenantId", p)
        self.assertNotIn("IdempotencyKey", p)
        self.assertEqual(p["ServiceId"], 12491)
        self.assertEqual(p["Weight"], 500)
        self.assertEqual(p["Length"], 100)
        self.assertEqual(p["CollectAmount"], 150000)
        self.assertEqual(p["ProductPrice"], 300000)

    def test_03_dia_chi_hai_cap_district_mot_khoang_trang(self):
        p = bhd.dung_order_add(don_mau(nguoi_gui_quan="", nguoi_nhan_quan=""),
                               {"merchant_order_code": "MD-UAT-1"})
        self.assertEqual(p["SourceDistrict"], " ")
        self.assertEqual(p["DestDistrict"], " ")
        self.assertEqual(p["ReturnDistrict"], " ")

    def test_04_service_id_12490_bi_tu_choi(self):
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_order_add(don_mau(service_id=12490), {"merchant_order_code": "MD-UAT-1"})

    def test_05_journey_type_sai_bi_tu_choi(self):
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_order_add(don_mau(journey_type=4), {"merchant_order_code": "MD-UAT-1"})

    def test_06_thieu_product_name_bi_tu_choi(self):
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_order_add(don_mau(hang_hoa=""), {"merchant_order_code": "MD-UAT-1"})

    def test_07_update_dung_truong(self):
        p = bhd.dung_update(don_mau(), "8485")
        self.assertEqual(set(p), {"Code", "ProductName", "ProductPrice", "CollectAmount",
                                  "ServiceId", "Length", "Height", "Width", "Weight"})

    def test_08_update_address_dung_truong(self):
        p = bhd.dung_update_address(don_mau(), "8485", address_type=2)
        self.assertEqual(set(p), {"Code", "AddressTypeId", "Address", "CityName",
                                  "DistrictName", "WardName", "ContactName",
                                  "PhoneNumber1", "PhoneNumber2"})
        self.assertEqual(p["AddressTypeId"], 2)

    def test_09_cancel_chi_code(self):
        self.assertEqual(bhd.dung_cancel("8485"), {"Code": "8485"})

    def test_10_query_dung_codes_va_gioi_han_10(self):
        p = bhd.dung_query(["A", "B"])
        self.assertEqual(p["LangType"], "en-US")
        self.assertEqual(p["Codes"], ["A", "B"])
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_query([str(i) for i in range(11)])

    def test_11_estimate_dung_truong(self):
        p = bhd.dung_estimate(don_mau())
        for ten in ("UserName", "ServiceId", "DestCity", "DestDistrict", "DestWard",
                    "SourceCity", "SourceDistrict", "SourceWard", "COD", "ProductPrice",
                    "DiscountCode", "Weight", "Length", "Height", "Width"):
            self.assertIn(ten, p, ten)
        self.assertEqual(p["ServiceId"], 12491)
        self.assertEqual(p["COD"], 150000)

    def test_12_print_dung_codes_va_gioi_han_50(self):
        self.assertEqual(bhd.dung_print(["A"]), {"codes": ["A"]})
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_print([str(i) for i in range(51)])


class TestBuilderMoi(unittest.TestCase):
    def test_37_31_truong_nen_va_34_truong_tai_lieu(self):
        self.assertEqual(len(bhd.TRUONG_ORDER_ADD_NEN), 31)
        self.assertEqual(len(bhd.TRUONG_ORDER_ADD), 34)
        p = bhd.dung_order_add(don_mau(), {})
        self.assertEqual(len(p), 31)
        p2 = bhd.dung_order_add(don_mau(number_of_products=3,
                                        bonus_product_name1="Quà 1",
                                        bonus_product_name2="Quà 2"), {})
        self.assertEqual(p2["NumberOfProducts"], 3)
        self.assertEqual(p2["BonusProductName1"], "Quà 1")
        self.assertEqual(p2["BonusProductName2"], "Quà 2")

    def test_38_thieu_can_nang_bi_tu_choi(self):
        d = don_mau()
        d.pop("khoi_luong_gram")
        with self.assertRaises(bhd.LoiHopDong):
            bhd.dung_order_add(d, {})

    def test_39_update_address_chon_dung_nguoi_theo_loai(self):
        d = don_mau(nguoi_tra_ten="Người Trả", nguoi_tra_sdt="0903",
                    nguoi_tra_tinh="Đà Nẵng", nguoi_tra_quan="Hải Châu",
                    nguoi_tra_xa="Phường 1", nguoi_tra_dia_chi="9 Đường Trả")
        p1 = bhd.dung_update_address(d, "W1", 1)
        self.assertEqual(p1["ContactName"], d["nguoi_gui_ten"])
        p2 = bhd.dung_update_address(d, "W1", 2)
        self.assertEqual(p2["ContactName"], d["nguoi_nhan_ten"])
        p3 = bhd.dung_update_address(d, "W1", 3)
        self.assertEqual(p3["ContactName"], "Người Trả")
        self.assertEqual(p3["CityName"], "Đà Nẵng")
        self.assertEqual(p3["PhoneNumber1"], "0903")

    def test_40_estimate_khong_bat_buoc_ward(self):
        d = don_mau()
        d.pop("nguoi_gui_xa", None)
        d.pop("nguoi_nhan_xa", None)
        p = bhd.dung_estimate(d)
        self.assertEqual(p["SourceWard"], " ")
        self.assertEqual(p["DestWard"], " ")


class TestParser(unittest.TestCase):
    def test_20_result_1_thanh_cong(self):
        ok, data, loi, result = bhd.boc_ket_qua({"Result": 1, "Message": None,
                                                 "Code": "8485", "RouteCode": "SG"})
        self.assertTrue(ok)
        self.assertEqual(result, 1)
        self.assertEqual(bhd.ma_van_don(data), "8485")

    def test_21_result_2_that_bai_co_ly_do(self):
        ok, data, loi, result = bhd.boc_ket_qua({"Result": 2, "Message": "[ex0034] cancelled"})
        self.assertFalse(ok)
        self.assertEqual(result, 2)
        self.assertIn("cancelled", loi)

    def test_22_result_la_khong_doan(self):
        ok, data, loi, result = bhd.boc_ket_qua({"Result": 9, "Message": ""})
        self.assertFalse(ok)
        self.assertIn("Result lạ", loi)

    def test_23_token_30_ngay_duoc_boc(self):
        ok, data, loi, _ = bhd.boc_ket_qua({"token": "a.b.c"})
        self.assertTrue(ok)
        self.assertEqual(bhd.boc_token(data), ("a.b.c", ""))

    def test_24_query_lay_trace_log_moi_nhat(self):
        goi = {"Result": 1, "Message": None, "data": [{
            "code_best": "8485", "merchant_order_code": "MD1",
            "traceLogs": [
                {"status": "202", "modified_at": 1000},
                {"status": "666", "modified_at": 3000},
                {"status": "301", "modified_at": 2000},
            ]}]}
        ok, ds, loi = bhd.boc_query(goi)
        self.assertTrue(ok, loi)
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0]["status"], "666")
        self.assertEqual(ds[0]["trang_thai_chung"], "giao_thanh_cong")

    def test_25_estimate_doc_data_total_fee(self):
        ok, d, loi = bhd.boc_estimate({"Result": 1, "Message": "", "data": {
            "TotalFee": 19800, "FreightFee": 19800, "CODFee": 0}})
        self.assertTrue(ok, loi)
        self.assertEqual(d["TotalFee"], 19800)

    def test_26_print_doc_url(self):
        ok, url, loi = bhd.boc_print({"Result": 1, "Message": "", "Url": "https://x/y.pdf",
                                      "Guid": "g"})
        self.assertTrue(ok, loi)
        self.assertEqual(url, "https://x/y.pdf")

    def test_27_bang_23_ma_chinh_thuc(self):
        self.assertEqual(len(bhd.BANG_MA), 23)
        self.assertEqual(bhd.trang_thai_chung(666)[0], "giao_thanh_cong")
        self.assertEqual(bhd.trang_thai_chung(605)[0], "hoan_hang")
        self.assertEqual(bhd.trang_thai_chung(606)[0], "dang_giao")
        self.assertEqual(bhd.trang_thai_chung(777)[0], "giao_that_bai")
        self.assertTrue(bhd.trang_thai_chung(777)[1])
        self.assertEqual(bhd.trang_thai_chung(1000)[0], "giao_that_bai")
        self.assertEqual(bhd.trang_thai_chung(2)[0], "da_huy")
        self.assertIsNone(bhd.trang_thai_chung(99999)[0])


class TestParserMoi(unittest.TestCase):
    def test_41_query_customer_cancel(self):
        goi = {"Result": 1, "Message": None, "data": [{
            "code_best": "8485", "merchant_order_code": "MD1",
            "traceLogs": [{"status": "customer Cancel", "modified_at": 2000,
                           "status_content": "khách hủy"}]}]}
        ok, ds, loi = bhd.boc_query(goi)
        self.assertTrue(ok, loi)
        self.assertEqual(ds[0]["status_so"], 2)
        self.assertTrue(ds[0]["customer_cancel"])
        self.assertEqual(ds[0]["trang_thai_chung"], "da_huy")
        self.assertTrue(ds[0]["biet_ma"])

    def test_42_estimate_alias_cod_va_phi_cuoi(self):
        ok, d, loi = bhd.boc_estimate({"Result": 1, "Message": "", "data": {
            "Cod": 100000, "TotalFee": 19800, "TotalFeeVAT": 21780}})
        self.assertTrue(ok, loi)
        self.assertEqual(d["COD"], 100000)
        self.assertEqual(d["Cod"], 100000)
        self.assertEqual(bhd.phi_cuoi(d), 21780)

    def test_43_print_full_guid_va_url(self):
        ok, d, loi = bhd.boc_print_full({"Result": 1, "Message": "",
                                         "Guid": "3034", "Url": "http://x/y.pdf"})
        self.assertTrue(ok, loi)
        self.assertEqual(d["Guid"], "3034")
        self.assertEqual(d["Url"], "http://x/y.pdf")

    def test_44_http_best_nang_http_len_https_chi_host_hang(self):
        import http_best
        self.assertEqual(
            http_best.nang_cap_https_cho_url_hang(
                "http://sgp-seaedi-test.800best.com/VietNamV3/x.pdf?y=1"),
            "https://sgp-seaedi-test.800best.com/VietNamV3/x.pdf?y=1")
        self.assertEqual(http_best.nang_cap_https_cho_url_hang("http://evil.example/x.pdf"),
                         "http://evil.example/x.pdf")


class TestApproval(unittest.TestCase):
    def setUp(self):
        self._cu = {k: os.environ.get(k) for k in
                    ("VIP_BEST_OWNER_APPROVED", "VIP_BEST_OWNER_APPROVAL_ID")}
        for k in self._cu:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_30_thieu_phe_duyet_bi_chan(self):
        ok, ly_do = bhd.cua_phe_duyet("sandbox", True)
        self.assertFalse(ok)
        self.assertIn("VIP_BEST_OWNER_APPROVED", ly_do)

    def test_31_co_phe_duyet_nhung_thieu_ma_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        ok, ly_do = bhd.cua_phe_duyet("sandbox", True)
        self.assertFalse(ok)
        self.assertIn("APPROVAL_ID", ly_do)

    def test_32_du_phe_duyet_sandbox_cho_phep(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        ok, ly_do = bhd.cua_phe_duyet("sandbox", True)
        self.assertTrue(ok, ly_do)
        ok2, ly_do2 = bhd.cua_phe_duyet("sandbox", True, ghi=True,
                                        xac_nhan=bhd.CAU_XAC_NHAN_GHI)
        self.assertTrue(ok2, ly_do2)

    def test_33_production_ghi_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        ok, ly_do = bhd.cua_phe_duyet("production", True, ghi=True,
                                      xac_nhan=bhd.CAU_XAC_NHAN_GHI)
        self.assertFalse(ok)
        self.assertIn("PRODUCTION", ly_do)

    def test_34_thieu_cau_xac_nhan_ghi_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        ok, ly_do = bhd.cua_phe_duyet("sandbox", True, ghi=True, xac_nhan="sai")
        self.assertFalse(ok)
        self.assertIn("xác nhận", ly_do)

    def test_35_tls_host_la_bi_tu_choi_khong_mo_mang(self):
        kq = bhd.kiem_tra_tls("example.com")
        self.assertFalse(kq["ok"])

    def test_36_thong_tin_hop_dong_khong_secret(self):
        tt = bhd.thong_tin_hop_dong()
        raw = json.dumps(tt, ensure_ascii=False)
        self.assertNotIn("password", raw.lower())
        self.assertNotIn("bearer", raw.lower())
        self.assertNotIn("secret", raw.lower())
        self.assertEqual(tt["service_id"], 12491)
        self.assertEqual(tt["so_ma"], 23)


if __name__ == "__main__":
    import unittest as _ut
    kq = _ut.TextTestRunner(verbosity=2).run(
        _ut.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f"\nCa chạy: {kq.testsRun} · lỗi: {len(kq.errors)} · hỏng: {len(kq.failures)} "
          f"· skip: {len(kq.skipped)}")
    print("KẾT QUẢ:", "ĐẠT" if kq.wasSuccessful() else "HỎNG")
    sys.exit(0 if kq.wasSuccessful() else 1)
