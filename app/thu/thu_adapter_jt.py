# G13 (J04/J06) — HÀNH VI CỦA ADAPTER J&T Ở MOCK: ba kết cục · đọc gói trả lời · chống trùng ·
# cách ly tenant · các ổ khoá chặn LIVE.
#
# VÌ SAO CÓ FILE NÀY
# ------------------
# `thu_hop_dong_jt.py` kiểm gói yêu cầu DỰNG RA. File này kiểm cái QUAY VỀ: sáu thao tác trả
# `KetQuaHang` gì, lỗi của hãng có đi qua bảng mã lỗi thật không, và ba kết cục
# (ok / hãng-từ-chối / KHÔNG-BIẾT) có bị gộp làm một không.
#
# Hai chỗ đáng chú ý:
#   · nhóm C dùng chính `doc_goi_tra_loi` của adapter với các gói `{code,msg,data}` theo quy ước
#     tài liệu, rồi đối chiếu với `don_hang._la_khong_tim_thay` — hàm THẬT của Order Service.
#     Nhờ vậy ca kiểm bắt được cả chỗ lệch tên khoá giữa hai lớp (`ma_chuan` vs `ma`), thứ mà
#     trước G13 không ca nào chạm tới: adapter phát `ma_chuan`, Order Service đọc `ma`.
#   · nhóm E kiểm khoá chống trùng bằng SỔ MÔ PHỎNG bật tường minh, và có CA ĐỐI CHỨNG: khi sổ
#     TẮT thì cùng một `ma_don` tạo được hai lượt — nếu thiếu ca đối chứng này thì "phát hiện
#     trùng" có thể chỉ là một phép kiểm luôn-đúng mà không ai biết.
#
# Chạy: python3 app/thu/thu_adapter_jt.py
import json
import os
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g13-ad-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import adapter          # noqa: E402
import adapter_jt as aj  # noqa: E402
import don_hang         # noqa: E402
import loi_hang as lh   # noqa: E402
import trang_thai_hang as tth   # noqa: E402
import transport as tp  # noqa: E402

DON_MAU = {
    "ma_don": "G13-AD-1", "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_nhan_ten": "Khách Thử",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Đường Nhận",
    "hang_hoa": "Áo thử", "khoi_luong_gram": 1500, "cod": 15000, "gia_tri_khai": 200000,
    "nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Quận 1",
    "nguoi_nhan_tinh": "Hà Nội", "nguoi_nhan_quan": "Quận Đống Đa",
}

BI_MAT = ("KHOA-BI-MAT-G13", "MAT-KHAU-G13", "ACC-BI-MAT-G13")
CRED_THU = {"apiAccount": "ACC-BI-MAT-G13", "privateKey": "KHOA-BI-MAT-G13",
            "customerCode": "CC-G13", "password": "MAT-KHAU-G13"}

KHOÁ_HOP_DONG = ("ma_chuan", "ma_goc_hang", "thong_diep", "co_the_thu_lai")


def quet_bi_mat(doi_tuong, danh_sach=BI_MAT):
    """Trả danh sách chuỗi bí mật XUẤT HIỆN trong `doi_tuong` (đã đổ thành JSON). Rỗng = sạch."""
    chuoi = json.dumps(doi_tuong, ensure_ascii=False, default=str)
    return [b for b in danh_sach if b and b in chuoi]


def quet_bien_the_module(mod, danh_sach=BI_MAT):
    """Quét mọi giá trị cấp module (không chỉ dict trả về) — nơi giấu credentials kín nhất."""
    return quet_bi_mat({k: repr(v) for k, v in vars(mod).items()
                        if not k.startswith("__")}, danh_sach)


def ad_mock(cred=None, **kw):
    # `cred or CRED_THU` sẽ biến `{}` (credentials RỖNG — chính là ca cần đo ở F5) thành bộ
    # credentials đầy đủ. Phân biệt bằng `is None`, không bằng tính đúng/sai của dict.
    return aj.AdapterJT(dict(CRED_THU if cred is None else cred), "mock", **kw)


class ChoPhepLiveTam:
    def __enter__(self):
        self.cu = aj.AdapterJT.CHO_PHEP_LIVE
        aj.AdapterJT.CHO_PHEP_LIVE = True
        return self

    def __exit__(self, *a):
        aj.AdapterJT.CHO_PHEP_LIVE = self.cu
        return False


# ════════════════════════════════════════════════════════════════════════════════════════════════
class A_SauThaoTacOMock(unittest.TestCase):
    """Mỗi thao tác chạy được ở mock, và ba kết cục phân biệt được."""

    def test_a1_createOrder_ok(self):
        kq = ad_mock().createOrder(dict(DON_MAU))
        self.assertTrue(kq.ok and not kq.timeout)
        self.assertTrue(str(kq.ma_van_don).startswith("JTVN"), kq.ma_van_don)
        self.assertIs(kq.tho.get("mock"), True, "kết quả mock phải TỰ NHẬN là mock")

    def test_a2_createOrder_hang_tu_choi(self):
        kq = ad_mock().createOrder(dict(DON_MAU, ghi_chu="demo_force_fail"))
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout, "hãng TỪ CHỐI không phải 'không biết kết quả'")
        chuan = kq.tho["loi_chuan"]
        self.assertEqual(chuan["ma_chuan"], lh.THAM_SO_SAI)
        self.assertEqual(chuan["ma_goc_hang"], "145003050", "phải là mã lỗi THẬT của hãng")

    def test_a3_createOrder_khong_biet_ket_qua(self):
        kq = ad_mock().createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout"))
        self.assertFalse(kq.ok)
        self.assertTrue(kq.timeout)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.HET_GIO)
        self.assertIsNone(kq.ma_van_don, "không biết kết quả thì KHÔNG được có mã vận đơn")

    def test_a4_ba_ket_cuc_khong_bi_gop(self):
        ad = ad_mock()
        ok = ad.createOrder(dict(DON_MAU))
        tu_choi = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail"))
        khong_biet = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout"))
        self.assertEqual((ok.ok, ok.timeout), (True, False))
        self.assertEqual((tu_choi.ok, tu_choi.timeout), (False, False))
        self.assertEqual((khong_biet.ok, khong_biet.timeout), (False, True))

    def test_a5_cancelOrder_ba_ket_cuc(self):
        ad = ad_mock()
        ok = ad.cancelOrder("JTVN1", "khách huỷ")
        self.assertTrue(ok.ok and ok.ma_van_don == "JTVN1")
        tu_choi = ad.cancelOrder("MOCK-HONG-1", "khách huỷ")
        self.assertFalse(tu_choi.ok)
        self.assertFalse(tu_choi.timeout)
        self.assertEqual(tu_choi.tho["loi_chuan"]["ma_chuan"], lh.HANG_TU_CHOI)
        self.assertEqual(tu_choi.tho["loi_chuan"]["ma_goc_hang"], "999010010")
        treo = ad.cancelOrder("MOCK-HETGIO-1", "khách huỷ")
        self.assertTrue(treo.timeout and not treo.ok)

    def test_a6_trackOrder_ok_tra_ma_cua_hang(self):
        kq = ad_mock().trackOrder("JTVN9")
        self.assertTrue(kq.ok and kq.ma_van_don == "JTVN9")
        self.assertEqual(kq.tho["trang_thai"], 112)
        self.assertEqual(kq.tho["so_van_don"], 1)

    def test_a7_trackOrder_ba_nhanh_xau(self):
        ad = ad_mock()
        hong = ad.trackOrder("MOCK-HONG-1")
        self.assertFalse(hong.ok and hong.timeout)
        self.assertEqual(hong.tho["loi_chuan"]["ma_goc_hang"], "145003100")
        treo = ad.trackOrder("MOCK-HETGIO-1")
        self.assertTrue(treo.timeout)
        khong_thay = ad.trackOrder("MOCK-KHONGCO-1")
        self.assertFalse(khong_thay.ok)
        self.assertEqual(khong_thay.tho["loi_chuan"]["ma_chuan"], lh.KHONG_TIM_THAY)

    def test_a8_trackOrder_nhan_nhieu_ma(self):
        kq = ad_mock().trackOrder(["A1", "A2", "A3"])
        self.assertTrue(kq.ok)
        self.assertEqual(kq.tho["ma_da_tra"], ["A1", "A2", "A3"])
        self.assertEqual(kq.ma_van_don, "A1")

    def test_a9_getShippingFee_ba_ket_cuc(self):
        ad = ad_mock()
        ok = ad.getShippingFee(dict(DON_MAU))
        self.assertTrue(ok.ok and isinstance(ok.phi, int) and ok.phi > 0)
        tu_choi = ad.getShippingFee(dict(DON_MAU, ghi_chu="demo_force_fail"))
        self.assertFalse(tu_choi.ok and tu_choi.timeout)
        self.assertEqual(tu_choi.tho["loi_chuan"]["ma_goc_hang"], "145005004")
        treo = ad.getShippingFee(dict(DON_MAU, ghi_chu="demo_force_timeout"))
        self.assertTrue(treo.timeout and treo.phi is None)

    def test_a10_getShippingLabel_ok_va_tu_khai_khong_phai_nhan_hang(self):
        kq = ad_mock().getShippingLabel("JTVN1")
        self.assertTrue(kq.ok)
        self.assertEqual(kq.tho["label"], "MOCK-PDF")
        self.assertFalse(kq.tho["la_nhan_hang"])

    def test_a11_getShippingLabel_ba_nhanh_xau(self):
        ad = ad_mock()
        self.assertFalse(ad.getShippingLabel("MOCK-HONG-1").ok)
        self.assertTrue(ad.getShippingLabel("MOCK-HETGIO-1").timeout)
        self.assertEqual(ad.getShippingLabel("MOCK-KHONGCO-1").tho["loi_chuan"]["ma_chuan"],
                         lh.KHONG_TIM_THAY)

    def test_a12_getOrder_khong_ho_tro_nhung_khong_no_ngoai_le(self):
        ad = ad_mock()
        self.assertFalse(ad.capability("getOrder"))
        kq = ad.getOrder("MVD1")
        self.assertFalse(kq.ok)
        self.assertIn("không hỗ trợ", kq.loi or "")

    def test_a13_moi_ket_qua_mock_deu_tu_nhan_la_mock(self):
        ad = ad_mock()
        ra = [ad.createOrder(dict(DON_MAU)), ad.cancelOrder("JTVN1"), ad.trackOrder("JTVN1"),
              ad.getShippingFee(dict(DON_MAU)), ad.getShippingLabel("JTVN1")]
        for kq in ra:
            self.assertIs(kq.tho.get("mock"), True,
                          f"{kq.tho.get('thao_tac')} không tự nhận là mock")


class B_MaTrangThaiMockDiQuaBangAnhXaThat(unittest.TestCase):
    """Mock trả mã CỦA HÃNG, không trả tên trạng thái chuẩn — nếu không, polling thành 'mã lạ'."""

    def test_b1_ma_mock_tra_ve_nam_trong_bang_that(self):
        kq = ad_mock().trackOrder("JTVN1")
        qd = tth.quyet_dinh("jt", kq.tho["trang_thai"])
        self.assertTrue(qd.biet_ma, "polling sẽ đếm 'mã lạ' nếu mock trả mã không có trong bảng")
        self.assertEqual(qd.trang_thai_ap, "dang_giao")

    def test_b2_TU_KIEM_gia_tri_cu_thuc_su_la_ma_la(self):
        """Chứng minh ca B1 không rỗng: giá trị mock CŨ ('dang_giao') đúng là mã lạ với J&T."""
        self.assertFalse(tth.quyet_dinh("jt", "dang_giao").biet_ma)
        self.assertEqual(tth.quyet_dinh("jt", 112).trang_thai_ap, "dang_giao",
                         "ĐỐI CHỨNG: mã 112 là mã THẬT và ánh xạ ra dang_giao")


class C_DocGoiTraLoi(unittest.TestCase):
    """`doc_goi_tra_loi`: quy ước code == "1" là thành công; mã lạ KHÔNG được đoán."""

    def test_c1_thanh_cong_co_ma_van_don(self):
        kq = aj.doc_goi_tra_loi({"code": "1", "msg": "成功", "data": {"billCode": "JT999"}},
                                "createOrder")
        self.assertTrue(kq.ok and kq.ma_van_don == "JT999")
        self.assertIs(kq.tho.get("mock"), False, "kết quả đọc từ gói hãng KHÔNG phải mock")

    def test_c2_thanh_cong_ma_khong_doc_duoc_ma_van_don_thi_noi_ra_khong_bia(self):
        kq = aj.doc_goi_tra_loi({"code": "1", "msg": "成功", "data": {"waybillNo": "X"}},
                                "createOrder")
        self.assertTrue(kq.ok, "hãng đã xác nhận thì KHÔNG được coi là thất bại")
        self.assertIsNone(kq.ma_van_don)
        self.assertIs(kq.tho.get("thieu_ma_van_don"), True)
        self.assertIn("KHÔNG bịa", kq.tho.get("canh_bao", ""))

    def test_c3_ma_van_don_nam_trong_danh_sach_details(self):
        kq = aj.doc_goi_tra_loi({"code": "1", "data": [{"scanTypeCode": 112, "billCode": "JT7"}]},
                                "trackOrder")
        self.assertTrue(kq.ok and kq.ma_van_don == "JT7")

    def test_c4_code_0_la_that_bai_khong_phai_thanh_cong(self):
        kq = aj.doc_goi_tra_loi({"code": "0", "msg": "fail"}, "createOrder")
        self.assertFalse(kq.ok)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.KHONG_RO)
        self.assertFalse(kq.tho["loi_chuan"]["co_the_thu_lai"])

    def test_c5_ma_chu_ky_sai_ve_XAC_THUC_HONG(self):
        kq = aj.doc_goi_tra_loi({"code": "145003030", "msg": "请求头中的签名验证失败"},
                                "createOrder")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.XAC_THUC_HONG)
        self.assertFalse(kq.tho["loi_chuan"]["co_the_thu_lai"])

    def test_c6_ma_khong_tim_thay_duoc_Order_Service_hieu(self):
        kq = aj.doc_goi_tra_loi({"code": "999002000", "msg": "未找到数据"}, "trackOrder")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.KHONG_TIM_THAY)
        self.assertIs(don_hang._la_khong_tim_thay(kq), True,
                      "lệch tên khoá giữa adapter và Order Service làm nhánh `chua_vao` chết im lặng")

    def test_c7_don_trung_KHONG_duoc_coi_la_chua_vao(self):
        kq = aj.doc_goi_tra_loi({"code": "145003204", "msg": "订单重复"}, "createOrder")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.DON_TRUNG)
        self.assertIs(don_hang._la_khong_tim_thay(kq), False,
                      "đơn trùng nghĩa là lượt TRƯỚC ĐÃ VÀO — coi là 'chưa vào' là mở đường tạo lại")

    def test_c8_goi_khong_phai_json_object(self):
        for xau in ("<html>502</html>", [1, 2], None):
            kq = aj.doc_goi_tra_loi(xau, "createOrder")
            self.assertFalse(kq.ok)
            self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.KHONG_RO)

    def test_c9_thieu_truong_code(self):
        kq = aj.doc_goi_tra_loi({"msg": "không có code"}, "createOrder")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.KHONG_RO)

    def test_c10_http_503_la_KHONG_BIET_ket_qua(self):
        kq = aj.doc_goi_tra_loi({"x": 1}, "createOrder", http_status=503)
        self.assertTrue(kq.timeout, "5xx: chưa biết đơn đã vào chưa ⇒ timeout=True")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.HET_GIO)
        self.assertTrue(kq.tho["loi_chuan"]["co_the_thu_lai"])

    def test_c11_http_429_qua_han_muc_thi_cho_roi_thu_lai(self):
        kq = aj.doc_goi_tra_loi({"x": 1}, "trackOrder", http_status=429)
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout, "429 là hãng TỪ CHỐI rõ ràng, không phải 'không biết'")
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.QUA_HAN_MUC)
        self.assertTrue(kq.tho["loi_chuan"]["co_the_thu_lai"])

    def test_c12_http_400_tham_so_sai_khong_thu_lai(self):
        kq = aj.doc_goi_tra_loi({"x": 1}, "createOrder", http_status=400)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.THAM_SO_SAI)
        self.assertFalse(kq.tho["loi_chuan"]["co_the_thu_lai"])

    def test_c13_http_2xx_van_doc_than_tra_loi_binh_thuong(self):
        kq = aj.doc_goi_tra_loi({"code": "1", "data": {"billCode": "JT1"}}, "createOrder",
                                http_status=200)
        self.assertTrue(kq.ok and kq.ma_van_don == "JT1")

    def test_c14_TU_KIEM_loi_khac_KHONG_duoc_coi_la_khong_tim_thay(self):
        kq = aj.doc_goi_tra_loi({"code": "145003030"}, "trackOrder")
        self.assertIs(don_hang._la_khong_tim_thay(kq), False,
                      "sai chữ ký mà kết luận 'hãng chưa nhận đơn' là đường tới vận đơn trùng")


class D_ChuanHoaLoi(unittest.TestCase):
    def _moi_loi(self):
        ad = ad_mock()
        return [ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail")),
                ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout")),
                ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_trung")),
                ad.trackOrder("MOCK-HONG-1"), ad.trackOrder("MOCK-KHONGCO-1"),
                aj.doc_goi_tra_loi({"code": "145003030"}, "createOrder"),
                aj.doc_goi_tra_loi({"khong": "co code"}, "createOrder"),
                aj.doc_goi_tra_loi("x", "createOrder", http_status=503)]

    def test_d1_moi_loi_du_bon_truong_hop_dong(self):
        for kq in self._moi_loi():
            chuan = kq.tho.get("loi_chuan")
            self.assertIsInstance(chuan, dict, f"thiếu tho['loi_chuan']: {kq.loi}")
            for ten in KHOÁ_HOP_DONG:
                self.assertIn(ten, chuan, f"lỗi chuẩn thiếu trường {ten}")
            self.assertIsInstance(chuan["co_the_thu_lai"], bool)
            self.assertEqual(chuan["hang"], "jt")

    def test_d2_loi_chuan_dung_hinh_dang_hop_dong_va_Order_Service_doc_duoc(self):
        """AG-00 chốt 15/10/2026: `ma_chuan` là tên CHUẨN (hợp đồng §5). Adapter phát đúng hình
        dạng `nhu_dict()`, KHÔNG phát bí danh `ma`; `don_hang` là bên đã được vá để đọc `ma_chuan`.

        Ca này giữ cả hai đầu: hình dạng đầu ra, và việc Order Service THẬT nhận ra mã lỗi của
        adapter THẬT (không qua adapter giả, không qua dict tự chế).
        """
        for kq in self._moi_loi():
            chuan = kq.tho["loi_chuan"]
            self.assertEqual(set(chuan), set(lh.NormalizedCarrierError(
                lh.KHONG_RO).nhu_dict()), "hình dạng lỗi lệch `NormalizedCarrierError.nhu_dict()`")
            self.assertIn("ma_chuan", chuan)
            self.assertNotIn("ma", chuan, "bí danh `ma` đã được gỡ — tên chuẩn là `ma_chuan`")

        that = ad_mock().trackOrder("MOCK-KHONGCO-1")     # đi qua adapter THẬT
        self.assertEqual(that.tho["loi_chuan"]["ma_chuan"], lh.KHONG_TIM_THAY)
        self.assertIs(don_hang._la_khong_tim_thay(that), True,
                      "Order Service không nhận ra mã lỗi của adapter thật — nhánh `chua_vao` chết")
        self.assertIs(don_hang._la_don_trung(that), False)
        trung = ad_mock().createOrder(dict(DON_MAU, ghi_chu="demo_force_trung"))
        self.assertIs(don_hang._la_don_trung(trung), True,
                      "Order Service không nhận ra DON_TRUNG của adapter thật")
        self.assertIs(don_hang._la_khong_tim_thay(trung), False,
                      "DON_TRUNG KHÔNG được coi là 'không tìm thấy'")

    def test_d3_chi_HET_GIO_va_QUA_HAN_MUC_moi_thu_lai_duoc(self):
        for kq in self._moi_loi():
            chuan = kq.tho["loi_chuan"]
            mong = chuan["ma_chuan"] in (lh.HET_GIO, lh.QUA_HAN_MUC)
            self.assertIs(chuan["co_the_thu_lai"], mong,
                          f"{chuan['ma_chuan']}: co_the_thu_lai sai")

    def test_d4_khong_co_bi_mat_trong_loi_chuan(self):
        for kq in self._moi_loi():
            self.assertEqual(quet_bi_mat(kq.tho), [], f"lộ bí mật trong tho: {kq.tho}")


class E_ChongTrungDon(unittest.TestCase):
    def setUp(self):
        aj.xoa_so_mock()

    def tearDown(self):
        aj.xoa_so_mock()

    def test_e1_co_khoa_chong_trung_va_transport_tuan_theo(self):
        self.assertIs(aj.AdapterJT.KHOA_CHONG_TRUNG, True)
        self.assertTrue(tp.chinh_sach_cho("createOrder", True).duoc_thu_lai)
        self.assertFalse(tp.chinh_sach_cho("createOrder", False).duoc_thu_lai,
                         "ĐỐI CHỨNG: cờ tắt thì thao tác ghi không được thử lại")

    def test_e2_ep_don_trung_thi_ve_DON_TRUNG_khong_thu_lai(self):
        kq = ad_mock().createOrder(dict(DON_MAU, ghi_chu="demo_force_trung"))
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.DON_TRUNG)
        self.assertEqual(kq.tho["loi_chuan"]["ma_goc_hang"], "145003204")
        self.assertFalse(kq.tho["loi_chuan"]["co_the_thu_lai"])
        self.assertIs(kq.tho.get("don_da_ton_tai_tai_hang"), True)

    def test_e3_so_mo_phong_bat_thi_luot_hai_la_don_trung(self):
        ad = ad_mock(mo_phong_chong_trung=True)
        dau = ad.createOrder(dict(DON_MAU))
        self.assertTrue(dau.ok)
        sau = ad.createOrder(dict(DON_MAU))
        self.assertFalse(sau.ok)
        self.assertEqual(sau.tho["loi_chuan"]["ma_chuan"], lh.DON_TRUNG)
        self.assertEqual(sau.tho.get("ma_van_don_luot_truoc"), dau.ma_van_don,
                         "phải chỉ ra được vận đơn của lượt trước — đó là bằng chứng ĐÃ VÀO")

    def test_e4_DOI_CHUNG_so_tat_thi_cung_ma_don_van_tao_duoc_hai_luot(self):
        """Không có ca này thì 'phát hiện trùng' có thể chỉ là phép kiểm luôn-đúng."""
        ad = ad_mock()          # mặc định: mô phỏng chống trùng TẮT
        self.assertFalse(ad.mo_phong_chong_trung)
        lan1 = ad.createOrder(dict(DON_MAU))
        lan2 = ad.createOrder(dict(DON_MAU))
        self.assertTrue(lan1.ok and lan2.ok)
        self.assertIsNone(lan2.tho.get("ma_van_don_luot_truoc"))

    def test_e5_so_mo_phong_cach_ly_theo_tai_khoan_hang(self):
        a = ad_mock(mo_phong_chong_trung=True)
        b = ad_mock(dict(CRED_THU, customerCode="CC-KHAC"), mo_phong_chong_trung=True)
        self.assertTrue(a.createOrder(dict(DON_MAU)).ok)
        self.assertTrue(b.createOrder(dict(DON_MAU)).ok,
                        "hai tài khoản khác nhau dùng chung một ô chống trùng là rò tenant")

    def test_e6_xoa_so_mo_phong(self):
        ad = ad_mock(mo_phong_chong_trung=True)
        ad.createOrder(dict(DON_MAU))
        self.assertEqual(aj.SO_DON_MOCK.so_o(), 1)
        aj.xoa_so_mock()
        self.assertEqual(aj.SO_DON_MOCK.so_o(), 0)
        self.assertTrue(ad.createOrder(dict(DON_MAU)).ok)


class F_CachLyTenantVaBiMat(unittest.TestCase):
    def test_f1_moi_ket_qua_mock_khong_chua_bi_mat(self):
        ad = ad_mock()
        ra = [ad.createOrder(dict(DON_MAU)), ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail")),
              ad.cancelOrder("JTVN1", "huỷ"), ad.trackOrder("JTVN1"),
              ad.getShippingFee(dict(DON_MAU)), ad.getShippingLabel("JTVN1"),
              ad.kiem_ket_noi()]
        for kq in ra:
            doi_tuong = kq.tho if hasattr(kq, "tho") else kq
            self.assertEqual(quet_bi_mat(doi_tuong), [],
                             f"kết quả lộ bí mật: {doi_tuong}")

    def test_f2_TU_KIEM_bo_do_bi_mat_thuc_su_do_duoc(self):
        """Bộ dò luôn trả rỗng thì ca F1 xanh vô nghĩa. Ca này chứng minh nó dò được."""
        self.assertEqual(quet_bi_mat({"privateKey": BI_MAT[0]}), [BI_MAT[0]])
        self.assertEqual(quet_bi_mat({"ghi_chu": "không có gì"}), [])

    def test_f3_khong_co_bi_mat_trong_bien_module(self):
        ad_mock().createOrder(dict(DON_MAU))
        self.assertEqual(quet_bien_the_module(aj), [],
                         "credentials không được nằm ở biến cấp module — mọi tenant dùng chung")

    def test_f4_hai_tai_khoan_khac_nhau_thi_chu_ky_khac_nhau(self):
        a = ad_mock(dict(CRED_THU, privateKey="KHOA-A"))
        b = ad_mock(dict(CRED_THU, privateKey="KHOA-B"))
        ya = a.yeu_cau_tao_don(dict(DON_MAU))
        yb = b.yeu_cau_tao_don(dict(DON_MAU))
        self.assertEqual(ya["bizContent"], yb["bizContent"], "cùng đơn ⇒ cùng bizContent")
        self.assertNotEqual(ya["headers"]["digest"], yb["headers"]["digest"])
        self.assertNotEqual(ya["headers"]["apiAccount"], None)

    def test_f5_kiem_ket_noi_chi_neu_TEN_truong_thieu(self):
        kq = ad_mock({}).kiem_ket_noi()
        self.assertFalse(kq["du_credential"])
        self.assertEqual(sorted(kq["thieu_credential"]), sorted(aj.TRUONG_CREDENTIAL))
        for ten in kq["thieu_credential"]:
            self.assertRegex(ten, r"^[A-Za-z]+$", "danh sách thiếu chỉ được chứa TÊN trường")
        self.assertEqual(quet_bi_mat(kq), [])

    def test_f6_kiem_ket_noi_khong_tu_nhan_da_kiem_ket_noi(self):
        kq = ad_mock().kiem_ket_noi()
        self.assertIs(kq["chung_minh_ket_noi"], False)
        self.assertIs(kq["la_mock"], True)
        self.assertIs(kq["transport_that_da_viet"], False)
        self.assertIs(kq["chot_chan_D9_dang_bat"], True)
        self.assertIs(kq["city_co_gui"], False)
        self.assertTrue(str(kq["de_kiem_ket_noi_that"]).strip())
        self.assertIn("SANDBOX", kq["de_kiem_ket_noi_that"])

    def test_f7_kiem_ket_noi_liet_ke_dung_hai_nhom_duong_dan(self):
        kq = ad_mock().kiem_ket_noi()
        self.assertEqual(kq["duong_api_da_xac_nhan"], ["createOrder", "trackOrder"])
        self.assertEqual(kq["duong_api_chua_xac_nhan"],
                         ["cancelOrder", "getOrder", "getShippingFee", "getShippingLabel"])


class G_KhoaAnToanChanLive(unittest.TestCase):
    def test_g1_cho_phep_live_van_la_false(self):
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False)
        self.assertIs(adapter._DANG_KY["jt"].CHO_PHEP_LIVE, False)

    def test_g2_tao_adapter_ngoai_mock_bi_chan_ngay(self):
        for mt in ("sandbox", "production"):
            with self.assertRaises(PermissionError):
                adapter.tao_adapter("jt", dict(CRED_THU), mt)

    def test_g3_mo_tam_cho_phep_live_thi_chot_D9_van_chan_createOrder(self):
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                ad.createOrder(dict(DON_MAU))
            self.assertIn("D-9", e.exception.thong_diep)

    def test_g4_mo_tam_cho_phep_live_thi_cac_thao_tac_khac_dung_va_noi_ro_thieu_gi(self):
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "production")
            for ten, goi in (("cancelOrder", lambda: ad.cancelOrder("MVD1")),
                             ("getShippingFee", lambda: ad.getShippingFee(dict(DON_MAU))),
                             ("getShippingLabel", lambda: ad.getShippingLabel("MVD1")),
                             ("trackOrder", lambda: ad.trackOrder("MVD1"))):
                with self.assertRaises(aj.ChuaXacNhanTaiLieu) as e:
                    goi()
                self.assertEqual(e.exception.thao_tac, ten)
                self.assertTrue(e.exception.thieu, f"{ten}: phải nêu lý do còn thiếu")

    def test_g5_sau_khi_mo_tam_thi_khoa_duoc_tra_lai(self):
        with ChoPhepLiveTam():
            self.assertTrue(aj.AdapterJT.CHO_PHEP_LIVE)
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False)


if __name__ == "__main__":
    kq = unittest.main(verbosity=2, exit=False).result
    print()
    print("=" * 78)
    print("PHẠM VI ĐÃ ĐO: hành vi của app/adapter_jt.py ở môi trường MOCK + hàm đọc gói trả lời")
    print("  chạy trên gói JSON dựng theo quy ước tài liệu + các chốt chặn LIVE (đo bằng cách mở")
    print("  tạm CHO_PHEP_LIVE rồi đóng lại). KHÔNG có lượt gọi mạng nào.")
    print("NẰM NGOÀI: J&T thật có chấp nhận chữ ký/tham số không; mã lỗi thật của hãng có đúng")
    print("  như bảng đã đọc không; sandbox hãng có sống không; callback hãng ký bằng khoá nào.")
    print("  ⇒ G13 KHÔNG được báo 'LIVE VERIFIED': V-G09-01 và V-13906-05 CHƯA CẤP.")
    print(f"Tổng: {kq.testsRun} ca · hỏng {len(kq.failures)} · lỗi {len(kq.errors)} "
          f"· bỏ qua {len(kq.skipped)}")
    print("=" * 78)
    sys.exit(bool(kq.failures or kq.errors))
