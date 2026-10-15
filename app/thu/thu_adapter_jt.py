# G13 (J04/J06) + G16-A — HÀNH VI CỦA ADAPTER J&T: ba kết cục · đọc gói trả lời · chống trùng ·
# cách ly tenant · các ổ khoá chặn LIVE · ĐƯỜNG GỬI THẬT trên stub cục bộ.
#
# VÌ SAO CÓ FILE NÀY
# ------------------
# `thu_hop_dong_jt.py` kiểm gói yêu cầu DỰNG RA. File này kiểm cái QUAY VỀ: sáu thao tác trả
# `KetQuaHang` gì, lỗi của hãng có đi qua bảng mã lỗi thật không, và ba kết cục
# (ok / hãng-từ-chối / KHÔNG-BIẾT) có bị gộp làm một không.
#
# Bốn chỗ đáng chú ý:
#   · nhóm C dùng chính `doc_goi_tra_loi` của adapter với các gói `{code,msg,data}` theo quy ước
#     tài liệu, rồi đối chiếu với `don_hang._la_khong_tim_thay` — hàm THẬT của Order Service.
#     Nhờ vậy ca kiểm bắt được cả chỗ lệch tên khoá giữa hai lớp (`ma_chuan` vs `ma`), thứ mà
#     trước G13 không ca nào chạm tới: adapter phát `ma_chuan`, Order Service đọc `ma`.
#   · nhóm E kiểm khoá chống trùng bằng SỔ MÔ PHỎNG bật tường minh, và có CA ĐỐI CHỨNG: khi sổ
#     TẮT thì cùng một `ma_don` tạo được hai lượt — nếu thiếu ca đối chứng này thì "phát hiện
#     trùng" có thể chỉ là một phép kiểm luôn-đúng mà không ai biết.
#   · **nhóm H (G16-A)** chạy ĐƯỜNG GỬI THẬT: `adapter_jt._goi_that` → `transport.goi` →
#     `http_jt.gui_form` → socket tới stub `127.0.0.1` cổng 0 (`app/thu/stub_jt.py`, AG-02). Nó
#     đo ĐÚNG NHỮNG BYTE trên dây: `bizContent` là chuỗi đã đem ký, digest tính lại ở PHÍA MÁY
#     CHỦ, COD nằm ở `codMoney`, `privateKey` KHÔNG bao giờ rời đi. Bỏ qua kèm LÝ DO ĐỌC ĐƯỢC
#     nếu tệp của AG-02 chưa có trên đĩa.
#   · **nhóm I (G16-A)** chạy trên một lớp HTTP GIẢ rất mỏng, đúng hình dạng §36. Nó luôn chạy,
#     và nó là chỗ chứng minh "không một byte nào rời đi" bằng PHÉP ĐẾM khi cửa môi trường hoặc
#     chốt D-9 chặn — kèm ca tự kiểm bộ đếm (`test_i1`), vì một bộ đếm không bao giờ được gọi
#     thì mọi khẳng định "0 lượt" đều vô nghĩa.
#
# Chạy: python3 app/thu/thu_adapter_jt.py
import base64
import hashlib
import inspect
import json
import os
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU_MUC_THU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC_APP)
if THU_MUC_THU not in sys.path:
    sys.path.insert(0, THU_MUC_THU)

_tam = tempfile.mkdtemp(prefix="vip-hub-g13-ad-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import adapter          # noqa: E402
import adapter_jt as aj  # noqa: E402
import don_hang         # noqa: E402
import loi_hang as lh   # noqa: E402
import trang_thai_hang as tth   # noqa: E402
import transport as tp  # noqa: E402

# Lớp HTTP THẬT và stub cục bộ đều do AG-02 sở hữu (§39). Làn này CHỈ GỌI — không sửa tệp của họ.
# Nếu chúng chưa có trên đĩa thì nhóm H tự bỏ qua kèm LÝ DO ĐỌC ĐƯỢC, chứ không báo xanh.
try:
    import http_jt as http_that
except ImportError:          # pragma: no cover — phụ thuộc thời điểm bốn làn chạy song song
    http_that = None
try:
    import stub_jt
except ImportError:          # pragma: no cover
    stub_jt = None

CO_HTTP_THAT = http_that is not None and stub_jt is not None
LY_DO_BO_QUA = ("chưa có `app/http_jt.py` + `app/thu/stub_jt.py` (AG-02, hợp đồng §36) trên đĩa"
                " — nhóm H chỉ chạy khi lớp HTTP thật đã có")

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
# Tài khoản THỨ HAI để đo cách ly tenant TRÊN DÂY (nhóm H). Là bí mật GIẢ của bộ thử, và cũng
# được đưa vào bộ dò rò rỉ.
CRED_THU_B = {"apiAccount": "ACC-B-G13", "privateKey": "KHOA-B-G13",
              "customerCode": "CC-B-G13", "password": "MAT-KHAU-B-G13"}
BI_MAT = BI_MAT + tuple(CRED_THU_B.values())

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
        # Cờ transport là ẢNH CHỤP của phép dò `app/http_jt.py` — KHÔNG phải hằng viết tay.
        # `False` khi AG-02 chưa giao tệp, `True` khi đã giao; cả hai đều KHÔNG mở môi trường.
        self.assertIs(kq["transport_that_da_viet"], aj._co_http_jt())
        self.assertIs(kq["moi_truong_duoc_chay"], True, "mock phải luôn chạy được")
        self.assertTrue(str(kq["ly_do_moi_truong"]).strip())
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

    def test_g4_mo_tam_CHO_PHEP_LIVE_KHONG_lam_production_chay_duoc(self):
        """HAI CỬA ĐỘC LẬP — AG-00 chốt 15/10/2026, và ca này cố ý CHẶT HƠN bản G13.

        Bản G13 chỉ đo "thế nào cũng ném một ngoại lệ", nên nó xanh kể cả khi cửa môi trường
        thực ra đã mở. Bản này khẳng định đúng bất biến: mở `CHO_PHEP_LIVE` **KHÔNG** kéo theo
        quyền môi trường, và lý do phải nêu đúng §37.

        Đo đường "đã viết transport" thì đi bằng `mock` + `_goi_that` (nhóm H/I) — KHÔNG mở
        `production` để tiện cho bộ thử.
        """
        with ChoPhepLiveTam():
            ad = aj.AdapterJT(dict(CRED_THU), "production")
            for ten, goi in (("trackOrder", lambda: ad.trackOrder("MVD1")),
                             ("getShippingFee", lambda: ad.getShippingFee(dict(DON_MAU))),
                             ("getShippingLabel", lambda: ad.getShippingLabel("MVD1"))):
                with self.assertRaises(PermissionError,
                                       msg=f"{ten} lọt qua cửa MÔI TRƯỜNG") as e:
                    goi()
                self.assertIn("duyệt riêng", str(e.exception))
                self.assertIn("§37", str(e.exception))
            # `cancelOrder` dựng gói yêu cầu TRƯỚC khi hỏi cửa môi trường, mà gói đó cần đường
            # dẫn chưa xác minh ⇒ dừng ở cửa ĐƯỜNG DẪN. Vẫn là DỪNG, chỉ khác chỗ dừng.
            with self.assertRaises(aj.ChuaXacNhanTaiLieu):
                ad.cancelOrder("MVD1")
            with self.assertRaises(lh.NormalizedCarrierError) as e2:
                ad.createOrder(dict(DON_MAU))       # dừng ở chốt D-9
            self.assertIn("D-9", e2.exception.thong_diep)
        # ĐỐI CHỨNG DƯƠNG: ở `mock` thì CÙNG những thao tác ấy ĐI QUA ĐƯỢC. Thiếu vế này thì
        # một bản "chặn tất cả" cũng làm mọi khẳng định ở trên xanh một cách vô nghĩa.
        mock = ad_mock()
        self.assertTrue(mock.trackOrder("JTVN1").ok)
        self.assertTrue(mock.getShippingFee(dict(DON_MAU)).ok)
        self.assertTrue(mock.getShippingLabel("JTVN1").ok)
        self.assertTrue(mock.cancelOrder("JTVN1").ok)
        self.assertTrue(mock.createOrder(dict(DON_MAU)).ok)

    def test_g5_sau_khi_mo_tam_thi_khoa_duoc_tra_lai(self):
        with ChoPhepLiveTam():
            self.assertTrue(aj.AdapterJT.CHO_PHEP_LIVE)
        self.assertIs(aj.AdapterJT.CHO_PHEP_LIVE, False)


# ════════════════════════════════════════════════════════════════════════════════════════════════
# G16-A — NỐI ADAPTER VÀO LỚP HTTP THẬT
# ════════════════════════════════════════════════════════════════════════════════════════════════
# Hai nhóm, và lý do có CẢ HAI:
#   · **H** chạy trên `app/http_jt.py` + `app/thu/stub_jt.py` THẬT của AG-02 — bằng chứng mạnh
#     nhất, đo ĐÚNG NHỮNG BYTE đã đi trên dây.
#   · **I** chạy trên một lớp HTTP GIẢ rất mỏng, đúng hình dạng §36 — nó luôn chạy, kể cả khi
#     tệp của AG-02 chưa có, và nó chứng minh adapter chỉ phụ thuộc HÌNH DẠNG hợp đồng chứ không
#     phụ thuộc bản cài đặt cụ thể. Bộ thử không được phép "xanh vì thiếu thứ để đo".
#
# Cả hai nhóm đều KHÔNG mở cửa môi trường: chúng đi vào đường gửi ở DƯỚI cửa đó (`_goi_that`).
# Cửa môi trường đang ĐÓNG (đúng §37) và bộ thử không được mở nó để tiện cho mình — nhóm H có
# ca riêng khẳng định cửa đó chặn TRƯỚC khi một byte nào rời đi.


class TraLoiGia:
    """`TraLoiHTTP` giả — đúng ba thuộc tính §36: `ma_http`, `than`, `headers`."""

    def __init__(self, ma_http=200, than=b"", headers=None):
        self.ma_http = int(ma_http)
        self.than = bytes(than)
        self.headers = dict(headers or {})


class HttpGia:
    """Lớp HTTP GIẢ, mỏng, ĐÚNG chữ ký §36: `gui_form(url, headers, body, *, timeout)`.

    Nó GHI LẠI từng lượt được gọi. Nhờ vậy "không có byte nào rời đi" là một phép ĐẾM, không
    phải một lời hứa — và ca đếm ấy có ca tự kiểm (`test_i1`) chứng minh bộ đếm thật sự đếm được.
    """

    def __init__(self, tra_loi=None, loi=None):
        self.tra_loi = tra_loi
        self.loi = loi
        self.lan = []

    def gui_form(self, url, headers, body, *, timeout):
        self.lan.append({"url": url, "headers": dict(headers), "body": dict(body),
                         "timeout": timeout})
        if self.loi is not None:
            raise self.loi
        return self.tra_loi


def ad_that(cred=None, **kw):
    """Adapter ở `mock`, nhưng ĐO ĐƯỢC đường gửi thật qua `_goi_that`.

    Vì sao không dựng adapter ở `sandbox`: cửa MÔI TRƯỜNG (`cau_hinh.JT_CHO_PHEP_SANDBOX`) đang
    ĐÓNG — đúng §37 — và bộ thử KHÔNG được mở nó để tiện cho mình. Đường gửi thật nằm DƯỚI cửa
    đó, nên vẫn đo được nguyên vẹn mà không mở gì.
    """
    return aj.AdapterJT(dict(CRED_THU if cred is None else cred), "mock", **kw)


def yeu_cau_that(ad, stub, thao_tac, doi_tuong=None, **kw):
    """Gói yêu cầu THẬT của một thao tác, URL trỏ vào stub cục bộ đang chạy.

    URL lấy từ `aj.url_cua(...)` dưới `DungDiemCuoiTam` — tức là đi qua CHÍNH bảng đường dẫn của
    adapter, không phải một chuỗi tự ghép trong bộ thử. Nhờ vậy ca kiểm đo luôn cả việc ghép
    đường dẫn, và `test_h0` ghim lại đúng điều đó.
    """
    if thao_tac == "createOrder":
        yc = ad.yeu_cau_tao_don(dict(doi_tuong or DON_MAU), **kw)
    elif thao_tac == "trackOrder":
        yc = ad.yeu_cau_tra_hanh_trinh(
            doi_tuong if doi_tuong is not None else "VH000000001VN", **kw)
    else:
        raise ValueError(f"chưa có hàm dựng gói cho {thao_tac!r}")
    with aj.DungDiemCuoiTam(stub.goc):
        yc["url"] = aj.url_cua(thao_tac, "sandbox")
    return yc


class ChoPhepLiveTam:
    def __enter__(self):
        self.cu = aj.AdapterJT.CHO_PHEP_LIVE
        aj.AdapterJT.CHO_PHEP_LIVE = True
        return self

    def __exit__(self, *a):
        aj.AdapterJT.CHO_PHEP_LIVE = self.cu
        return False


def _khoa_chong_trung_tam(gia_tri):
    """Tạm đổi cờ khoá chống trùng của lớp — CHỈ để đo ĐỐI CHỨNG về số lần thử lại."""

    class _Ctx:
        def __enter__(self):
            self.cu = aj.AdapterJT.KHOA_CHONG_TRUNG
            aj.AdapterJT.KHOA_CHONG_TRUNG = gia_tri
            return self

        def __exit__(self, *a):
            aj.AdapterJT.KHOA_CHONG_TRUNG = self.cu
            return False
    return _Ctx()


# ════════════════════════════════════════════════════════════════════════════════════════════════
@unittest.skipUnless(CO_HTTP_THAT, LY_DO_BO_QUA)
class H_NoiTransportThat_TrenStubCucBo(unittest.TestCase):
    """Đường gửi THẬT: `adapter_jt._goi_that` → `http_jt.gui_form` → stub `127.0.0.1:0`.

    Mọi ca ở đây đi qua socket thật trên vòng lặp nội bộ. KHÔNG ca nào chạm Internet: stub chỉ
    bind `127.0.0.1`, và danh sách trắng của `http_jt` chặn mọi host khác.
    """

    def test_h0_url_di_qua_bang_duong_dan_cua_adapter(self):
        """ĐỐI CHỨNG DƯƠNG cho mọi ca sau: URL phải là gốc stub + ĐÚNG đường dẫn tài liệu."""
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG) as stub:
            yc = yeu_cau_that(ad_that(), stub, "createOrder")
            self.assertEqual(yc["url"], stub.goc + aj.DUONG_TAO_DON)
            self.assertEqual(yc["url"], stub.url)
            self.assertEqual(yc["url"], aj.URL_TAO_DON["sandbox"].replace(
                "https://demoopenapi.jtexpress.vn", stub.goc))
            yc_tr = yeu_cau_that(ad_that(), stub, "trackOrder")
            self.assertEqual(yc_tr["url"], stub.url_cho(aj.DUONG_TRA_HANH_TRINH))

    def test_h1_createOrder_thanh_cong_va_do_DUNG_BYTE_tren_day(self):
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG, ma_van_don="VH000000123VN") as stub:
            ad = ad_that()
            yc = yeu_cau_that(ad, stub, "createOrder")
            kq = ad._goi_that(http_that, "createOrder", yc)
            self.assertEqual(stub.so_yeu_cau, 1, "phải có ĐÚNG một lượt đi trên dây")
            yeu_cau = stub.yeu_cau[-1]

        self.assertTrue(kq.ok, kq.loi)
        self.assertFalse(kq.timeout)
        self.assertEqual(kq.ma_van_don, "VH000000123VN")
        self.assertIs(kq.tho["mock"], False, "kết quả từ hãng KHÔNG được tự nhận là mock")
        self.assertEqual(kq.tho["so_lan_goi"], 1)
        self.assertEqual(kq.tho["transport"], "app/http_jt.py")
        # ── đo trên dây ──────────────────────────────────────────────────────────────────────
        self.assertEqual(yeu_cau.phuong_thuc, "POST")
        self.assertEqual(yeu_cau.duong_dan, aj.DUONG_TAO_DON)
        self.assertIn("application/x-www-form-urlencoded", yeu_cau.header("content-type"))
        self.assertEqual(yeu_cau.header("apiAccount"), CRED_THU["apiAccount"])
        self.assertEqual(len(str(yeu_cau.header("timestamp"))), 13, "timestamp phải là mili giây")
        # CHỮ KÝ: tính lại Ở PHÍA MÁY CHỦ, từ CHÍNH chuỗi nhận được — độc lập với adapter.
        biz_nhan = yeu_cau.form_value("bizContent")
        self.assertIsInstance(biz_nhan, str)
        tay = base64.b64encode(hashlib.md5(
            (biz_nhan + CRED_THU["privateKey"]).encode("utf-8")).digest()).decode()
        self.assertEqual(yeu_cau.header("digest"), tay,
                         "digest trên dây KHÔNG khớp chuỗi bizContent đã nhận")
        self.assertEqual(biz_nhan, yc["bizContent"], "chuỗi đem ký và chuỗi gửi phải là MỘT")
        self.assertEqual(yeu_cau.form_value("bizContent"), yeu_cau.form()["bizContent"][0])
        # KHÓA KÝ KHÔNG BAO GIỜ ĐI TRÊN DÂY — chỉ có digest của nó.
        self.assertNotIn(CRED_THU["privateKey"], yeu_cau.than_tho.decode("utf-8"))

    def test_h2_ba_ket_cuc_tren_day_KHONG_bi_gop(self):
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG) as stub:
            ad = ad_that()
            ok = ad._goi_that(http_that, "createOrder", yeu_cau_that(ad, stub, "createOrder"))
        with stub_jt.StubJT(stub_jt.StubJT.HANG_TU_CHOI, ma_loi="145005004") as stub:
            ad = ad_that()
            tu_choi = ad._goi_that(http_that, "createOrder",
                                   yeu_cau_that(ad, stub, "createOrder"))
        with stub_jt.StubJT(stub_jt.StubJT.HTTP_500) as stub:
            ad = ad_that()
            khong_biet = ad._goi_that(http_that, "createOrder",
                                      yeu_cau_that(ad, stub, "createOrder"))
            self.assertEqual(stub.so_yeu_cau, 3,
                             "5xx là lỗi TẠM THỜI ⇒ chính sách phải thử lại 3 lượt")
        self.assertEqual((ok.ok, ok.timeout), (True, False))
        self.assertEqual((tu_choi.ok, tu_choi.timeout), (False, False),
                         "hãng TỪ CHỐI không được gộp với 'không biết'")
        self.assertEqual((khong_biet.ok, khong_biet.timeout), (False, True),
                         "5xx là KHÔNG BIẾT kết quả — tuyệt đối không coi là thành công")
        self.assertEqual(khong_biet.tho["loi_chuan"]["ma_chuan"], lh.HET_GIO)
        self.assertEqual(tu_choi.tho["loi_chuan"]["ma_chuan"], lh.HANG_TU_CHOI)
        self.assertEqual(tu_choi.tho["loi_chuan"]["ma_goc_hang"], "145005004")
        self.assertIsNone(khong_biet.ma_van_don)
        self.assertEqual(khong_biet.tho["so_lan_goi"], 3)

    def test_h3_don_trung_KHONG_thu_lai_va_Order_Service_nhan_ra(self):
        """Chống trùng đơn: `145003204` ⇒ lượt TRƯỚC ĐÃ VÀO. Gửi lại là tạo đơn thứ hai."""
        with stub_jt.StubJT(stub_jt.StubJT.HANG_TU_CHOI, ma_loi="145003204",
                            thong_diep="订单重复") as stub:
            ad = ad_that()
            kq = ad._goi_that(http_that, "createOrder", yeu_cau_that(ad, stub, "createOrder"))
            so_lan = stub.so_yeu_cau
        self.assertEqual(so_lan, 1, "đơn trùng bị THỬ LẠI là mở đường tạo đơn thứ hai")
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.DON_TRUNG)
        self.assertFalse(kq.tho["loi_chuan"]["co_the_thu_lai"])
        self.assertIs(kq.tho.get("don_da_ton_tai_tai_hang"), True)
        self.assertIs(don_hang._la_don_trung(kq), True,
                      "Order Service không nhận ra DON_TRUNG của đường gọi THẬT")
        self.assertIs(don_hang._la_khong_tim_thay(kq), False,
                      "coi đơn trùng là 'chưa vào' là mở đường gửi lại mù")

    def test_h4_DOI_CHUNG_khong_co_khoa_chong_trung_thi_KHONG_thu_lai(self):
        """Thiếu ca này thì `h3` có thể xanh chỉ vì transport không bao giờ thử lại."""
        with stub_jt.StubJT(stub_jt.StubJT.HTTP_500) as stub:
            ad = ad_that()
            yc = yeu_cau_that(ad, stub, "createOrder")
            with _khoa_chong_trung_tam(False):
                kq = ad._goi_that(http_that, "createOrder", yc)
            self.assertEqual(stub.so_yeu_cau, 1,
                             "KHÔNG có khoá chống trùng thì thao tác GHI không được thử lại")
        self.assertTrue(kq.timeout)
        self.assertIs(aj.AdapterJT.KHOA_CHONG_TRUNG, True, "cờ phải được trả lại sau khối")

    def test_h5_ma_HTTP_4xx_VINH_VIEN_duoc_phan_loai_chu_khong_gop_vao_THAM_SO_SAI(self):
        """4xx VĨNH VIỄN đi qua ngoại lệ của `http_jt` — adapter đọc `ma_http` mà phân loại.

        `408`/`429` **KHÔNG** nằm ở đây: AG-00 chốt 15/10/2026 rằng hai mã đó là TẠM THỜI, nên
        chúng có ca riêng `test_h5b`. Tách ra như vậy để "4xx" không còn bị đối xử như một khối.
        """
        for che_do, ma_chuan, thu_lai in (("HTTP_401", lh.XAC_THUC_HONG, False),
                                          ("HTTP_400", lh.THAM_SO_SAI, False),
                                          ("HTTP_302", lh.KHONG_RO, False)):
            with stub_jt.StubJT(getattr(stub_jt.StubJT, che_do)) as stub:
                ad = ad_that()
                kq = ad._goi_that(http_that, "createOrder",
                                  yeu_cau_that(ad, stub, "createOrder"))
                so_lan = stub.so_yeu_cau
            chuan = kq.tho["loi_chuan"]
            self.assertEqual(chuan["ma_chuan"], ma_chuan, f"{che_do}: sai mã chuẩn")
            self.assertEqual(so_lan, 1, f"{che_do}: lỗi vĩnh viễn ⇒ không được thử lại")
            self.assertIs(chuan["co_the_thu_lai"], thu_lai,
                          f"{che_do}: cờ thử lại phải theo kết luận của lớp HTTP")
            self.assertFalse(kq.ok)
            self.assertFalse(kq.timeout)
        self.assertTrue(issubclass(tp.LoiVinhVien, Exception))

    def test_h5b_HAI_LOP_DONG_Y_ve_408_va_429(self):
        """CA CANH CHỐNG LỆCH — AG-00 chốt 15/10/2026: `408` và `429` là TẠM THỜI.

        Vì sao cần ca này: `http_jt` từng xếp **mọi** 4xx là vĩnh viễn, còn `loi_hang.tu_http`
        nói hai mã này **thử lại được**. Hai lớp phát hai câu trả lời cho cùng một lượt là khuôn
        "lệch im lặng": lượt gọi lẽ ra thành công (sau khi chờ đủ) bị bỏ, mà không có lỗi nào báo.
        Ca này đo **cả hai lớp** và khẳng định chúng ĐỒNG Ý — cộng vế thứ ba ở tầng adapter.

        Không có ca này thì lần sau ai đó gộp 408/429 trở lại vào "4xx = vĩnh viễn" cũng không ai
        biết, và chỗ ép `co_the_thu_lai=False` trong adapter sẽ lặng lẽ hạ chúng xuống.
        """
        import time
        # `timeout` mong đợi KHÁC nhau, và đây là chỗ dễ gộp sai nhất:
        #   · 429 → `QUA_HAN_MUC`: hãng TỪ CHỐI lượt này một cách rõ ràng ⇒ `timeout=False`.
        #   · 408 → `HET_GIO`: `loi_hang` (tệp của AG-00) xếp 408 vào "hết giờ", và
        #     `ket_qua_tu_loi` suy `timeout` từ `HET_GIO` ⇒ `timeout=True` ("KHÔNG BIẾT kết quả").
        #     GHI LẠI ĐỂ KHÔNG AI PHẢI ĐOÁN: hãng trả 408 nghĩa là nó KHÔNG NHẬN KỊP yêu cầu, tức
        #     trên lý thuyết mình BIẾT là chưa xử lý gì. Nhưng đường đi hiện tại là phía THẬN
        #     TRỌNG: `timeout=True` ⇒ Order Service giữ đơn ở `dang_gui` + bật cờ đối soát, thay
        #     vì hoàn suất rồi gửi lại. Thận trọng ở đây chỉ tốn một lượt đối soát; làm ngược lại
        #     mà đoán sai thì tốn một vận đơn thật. Đây là chỗ lệch CÓ CHỦ Ý giữa "hãng nói gì"
        #     và "hệ xử thế nào" — muốn đổi thì AG-00 đổi `loi_hang.tu_http`, KHÔNG đổi ở adapter.
        for che_do, ma_http, ma_chuan, timeout_mong in (
                ("HTTP_408", 408, lh.HET_GIO, True),
                ("HTTP_429", 429, lh.QUA_HAN_MUC, False)):
            # ── LỚP 1: `http_jt` nói gì? Đo MỘT lượt gọi trần, không qua adapter ──────────────
            with stub_jt.StubJT(getattr(stub_jt.StubJT, che_do)) as stub:
                try:
                    http_that.gui_form(stub.url,
                                       {"apiAccount": "A", "digest": "d" * 24,
                                        "timestamp": "1792054650790"},
                                       {"bizContent": "{}"}, timeout=5)
                    loai = "khong-nem"
                except tp.LoiTamThoi as e:
                    loai, ma_thay = "tam-thoi", getattr(e, "ma_http", None)
                except tp.LoiVinhVien:
                    loai, ma_thay = "vinh-vien", None
            # ── LỚP 2: `loi_hang` nói gì? ────────────────────────────────────────────────────
            chuan_ll = lh.tu_http(ma_http)
            # ── HAI LỚP PHẢI ĐỒNG Ý ──────────────────────────────────────────────────────────
            self.assertEqual(loai, "tam-thoi",
                             f"{ma_http}: `http_jt` KHÔNG coi là tạm thời — hai lớp lệch nhau")
            self.assertEqual(ma_thay, ma_http, f"{ma_http}: ngoại lệ không mang đúng `ma_http`")
            self.assertEqual(chuan_ll.ma_chuan, ma_chuan)
            self.assertIs(chuan_ll.co_the_thu_lai, True,
                          f"{ma_http}: `loi_hang` phải nói THỬ LẠI ĐƯỢC")
            # ── LỚP 3: adapter phát ra ĐÚNG thế, KHÔNG bị ghi đè ─────────────────────────────
            with stub_jt.StubJT(getattr(stub_jt.StubJT, che_do)) as stub:
                ad = ad_that()
                t0 = time.time()
                kq = ad._goi_that(http_that, "createOrder",
                                  yeu_cau_that(ad, stub, "createOrder"))
                giay = time.time() - t0
            c = kq.tho["loi_chuan"]
            self.assertEqual(c["ma_chuan"], ma_chuan, f"{ma_http}: adapter đổi mã chuẩn")
            self.assertIs(c["co_the_thu_lai"], True,
                          f"{ma_http}: adapter ÉP CHẶT cờ thử lại — đúng chiều lệch AG-00 đã bác")
            self.assertFalse(kq.ok, f"{ma_http}: KHÔNG BAO GIỜ được coi là thành công")
            self.assertIs(kq.timeout, timeout_mong,
                          f"{ma_http}: `timeout` sai — xem bảng mong đợi ở đầu ca này")
            self.assertEqual(c["http_status"], ma_http)
            # Stub KHÔNG gửi `Retry-After` ⇒ chỉ còn backoff chính sách (0,2 + 0,4 giây). Trần
            # rộng 5 giây để bắt một hồi quy kiểu "ngủ trong gui_form": AG-00 đã cấm `time.sleep`
            # ở lớp đó và có ca AST riêng, đây là vế đo hành vi.
            self.assertLess(giay, 5.0,
                            f"{ma_http}: lượt gọi mất {giay:.2f}s — lớp HTTP có vẻ đang TỰ NGỦ")

    def test_h5d_DOI_CHUNG_DUONG_co_che_ep_chat_van_con(self):
        """ĐỐI CHỨNG DƯƠNG cho `h5b` — cơ chế §5 phải CÒN, chỉ trừ đúng 408/429.

        Không có ca này thì `h5b` xanh kể cả khi ai đó **gỡ hẳn** chỗ ép chặt: ta sẽ mất cơ chế
        "lớp dưới nói vĩnh viễn thì adapter không được khuyên thử lại" chứ không phải sửa đúng một
        ngoại lệ. Ca này đo ở RANH GIỚI, bằng hai ngoại lệ tổng hợp cùng loại `LoiVinhVien`:
          · `ma_http=503` (một mã mà `loi_hang` nói THỬ LẠI ĐƯỢC)  ⇒ phải bị ÉP CHẶT về False;
          · `ma_http=429` (ngoại lệ AG-00 đã chốt)                  ⇒ phải ĐI THẲNG, giữ True.
        """
        def _ngoai_le(ma):
            e = tp.LoiVinhVien(f"lớp dưới nói vĩnh viễn, mã {ma}")
            e.ma_http = ma
            return e

        ep_chat = aj.AdapterJT._ket_qua_tu_ngoai_le_transport(_ngoai_le(503), "createOrder")
        self.assertIs(ep_chat.tho["loi_chuan"]["co_the_thu_lai"], False,
                      "cơ chế §5 đã bị gỡ: lớp dưới nói VĨNH VIỄN mà adapter vẫn khuyên thử lại")
        for ma in aj.MA_HTTP_HAI_LOP_PHAI_DONG_Y:
            di_thang = aj.AdapterJT._ket_qua_tu_ngoai_le_transport(_ngoai_le(ma), "createOrder")
            self.assertIs(di_thang.tho["loi_chuan"]["co_the_thu_lai"], True,
                          f"{ma}: adapter ghi đè lớp dưới — đúng chiều lệch AG-00 đã bác")

    def test_h5c_danh_sach_HAI_LOP_DONG_Y_phu_DUNG_hai_ma_va_khong_rong_hon(self):
        """Ghim hằng số: đúng 408 và 429, không hơn. Một mã 4xx khác lọt vào đây là NỚI luật."""
        self.assertEqual(tuple(sorted(aj.MA_HTTP_HAI_LOP_PHAI_DONG_Y)), (408, 429))
        for ma in aj.MA_HTTP_HAI_LOP_PHAI_DONG_Y:
            self.assertIs(lh.tu_http(ma).co_the_thu_lai, True,
                          f"{ma} nằm trong danh sách ĐỒNG Ý nhưng `loi_hang` nói không thử lại được")
        # ĐỐI CHỨNG ÂM: mã 4xx vĩnh viễn KHÔNG được nằm trong danh sách này.
        for ma in (400, 401, 403, 404, 422):
            self.assertNotIn(ma, aj.MA_HTTP_HAI_LOP_PHAI_DONG_Y,
                             f"{ma} là lỗi VĨNH VIỄN — đưa vào danh sách ĐỒNG Ý là nới luật")

    def test_h6_danh_sach_trang_chan_host_la_va_KHONG_gui_gi(self):
        """TỰ KIỂM bộ đếm: một URL ngoài danh sách trắng phải bị chặn và stub phải ĐẾM ĐƯỢC 0."""
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG) as stub:
            ad = ad_that()
            yc = yeu_cau_that(ad, stub, "createOrder")
            yc["url"] = "https://ke-tan-cong.invalid/webopenplatformapi/api/order/addOrder"
            kq = ad._goi_that(http_that, "createOrder", yc)
            self.assertEqual(stub.so_yeu_cau, 0,
                             "URL ngoài danh sách trắng mà vẫn có lượt đi ⇒ chốt chặn hở")
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(kq.tho["so_lan_goi"], 1, "URL sai là lỗi VĨNH VIỄN, thử lại vô ích")

    def test_h7_cach_ly_tenant_tren_day_va_khong_ro_bi_mat(self):
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG) as stub:
            a, b = ad_that(), ad_that(CRED_THU_B)
            a._goi_that(http_that, "createOrder",
                        yeu_cau_that(a, stub, "createOrder", dict(DON_MAU, ma_don="T-A")))
            b._goi_that(http_that, "createOrder",
                        yeu_cau_that(b, stub, "createOrder", dict(DON_MAU, ma_don="T-B")))
            r1, r2 = stub.yeu_cau
        self.assertNotEqual(r1.header("apiAccount"), r2.header("apiAccount"))
        self.assertNotEqual(r1.header("digest"), r2.header("digest"),
                            "hai tenant khác nhau mà cùng chữ ký ⇒ dùng chung khoá")
        self.assertIn("T-A", r1.form_value("bizContent"))
        self.assertIn("T-B", r2.form_value("bizContent"))
        self.assertNotIn("T-B", r1.form_value("bizContent"),
                         "đơn của tenant này đi lẫn sang lượt của tenant kia")
        for r in (r1, r2):
            self.assertNotIn(CRED_THU["privateKey"], r.than_tho.decode("utf-8"))
            self.assertNotIn(CRED_THU_B["privateKey"], r.than_tho.decode("utf-8"))
            self.assertNotIn(CRED_THU_B["privateKey"], json.dumps(r.headers))

    def test_h8_COD_di_dung_truong_tren_day(self):
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG) as stub:
            ad = ad_that()
            ad._goi_that(http_that, "createOrder",
                         yeu_cau_that(ad, stub, "createOrder", dict(DON_MAU, cod=150000)))
            biz = json.loads(stub.yeu_cau[-1].form_value("bizContent"))
        self.assertEqual(biz["codMoney"], "150000", "COD phải đi ở `codMoney`")
        self.assertIsInstance(biz["codMoney"], str)
        self.assertTrue(biz["codMoney"].isdigit(), "tiền phải là chuỗi CHỮ SỐ, không có dấu chấm")
        self.assertNotIn("itemsValue", biz, "itemsValue KHÔNG có trong bảng tham số của hãng")
        self.assertEqual(biz["goodsValue"], "200000")
        self.assertEqual(biz["isInsured"], 0)

    def test_h9_trackOrder_di_that_va_ton_trong_tran_30(self):
        with stub_jt.StubJT(stub_jt.StubJT.THANH_CONG, ma_van_don="VH000000009VN",
                            duong_mac_dinh=aj.DUONG_TRA_HANH_TRINH) as stub:
            ad = ad_that()
            yc = yeu_cau_that(ad, stub, "trackOrder", ["A1", "A2"])
            kq = ad._goi_that(http_that, "trackOrder", yc)
            self.assertEqual(stub.yeu_cau[-1].duong_dan, aj.DUONG_TRA_HANH_TRINH)
            biz = json.loads(stub.yeu_cau[-1].form_value("bizContent"))
        self.assertTrue(kq.ok, kq.loi)
        self.assertEqual(biz["billcodes"], "A1,A2")

    def test_h10_ket_qua_that_KHONG_tu_nhan_la_mock(self):
        with stub_jt.StubJT(stub_jt.StubJT.HANG_TU_CHOI, ma_loi="145003050") as stub:
            ad = ad_that()
            kq = ad._goi_that(http_that, "createOrder", yeu_cau_that(ad, stub, "createOrder"))
        self.assertIs(kq.tho["mock"], False)
        self.assertNotIn("url_mock", kq.tho)
        self.assertEqual(quet_bi_mat(kq.tho), [], f"kết quả thật lộ bí mật: {kq.tho}")


# ════════════════════════════════════════════════════════════════════════════════════════════════
class I_LopHttpGia_DungHopDong36(unittest.TestCase):
    """Adapter chỉ được phụ thuộc HÌNH DẠNG §36 — nhóm này chạy được cả khi AG-02 chưa giao tệp."""

    def test_i1_TU_KIEM_lop_gia_thuc_su_duoc_goi(self):
        """Nếu lớp giả không bao giờ được gọi thì mọi ca "không có byte nào rời đi" vô nghĩa."""
        fake = HttpGia(tra_loi=TraLoiGia(200, b'{"code":"1","data":{"billCode":"X1"}}'))
        ad = ad_that()
        with aj.ThayHttpJtTam(fake):
            yc = ad.yeu_cau_tao_don(dict(DON_MAU))
            yc["url"] = "http://127.0.0.1:1"        # lớp GIẢ không mở socket nào
            kq = ad._goi_that(fake, "createOrder", yc)
        self.assertTrue(kq.ok, kq.loi)
        self.assertEqual(kq.ma_van_don, "X1")
        self.assertEqual(len(fake.lan), 1, "lớp HTTP giả KHÔNG được gọi ⇒ ca đếm vô nghĩa")
        self.assertEqual(kq.tho["transport"], "tam-thay-the")
        self.assertEqual(list(fake.lan[0]["body"]), ["bizContent"])
        self.assertIn("digest", fake.lan[0]["headers"])
        self.assertIsInstance(fake.lan[0]["timeout"], float)

    def test_i2_cua_moi_truong_chan_TRUOC_khi_mot_byte_nao_roi_di(self):
        """Cửa môi trường đang ĐÓNG: bộ đếm phải ở 0 sau khi thao tác bị từ chối."""
        fake = HttpGia(tra_loi=TraLoiGia(200, b'{"code":"1"}'))
        with ChoPhepLiveTam(), aj.ThayHttpJtTam(fake):
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(PermissionError) as e:
                ad.trackOrder("VH1")
        self.assertIn("V-G09-01", str(e.exception))
        self.assertEqual(fake.lan, [], "có byte rời đi TRƯỚC khi cửa môi trường kịp chặn")

    def test_i3_chot_D9_chan_TRUOC_khi_mot_byte_nao_roi_di(self):
        fake = HttpGia(tra_loi=TraLoiGia(200, b'{"code":"1"}'))
        with ChoPhepLiveTam(), aj.ThayHttpJtTam(fake):
            ad = aj.AdapterJT(dict(CRED_THU), "sandbox")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                ad.createOrder(dict(DON_MAU))
            self.assertIn("D-9", e.exception.thong_diep)
        self.assertEqual(fake.lan, [], "đơn đi ra trước khi chốt D-9 kịp chặn")

    def test_i4_loi_tam_thoi_va_vinh_vien_thanh_hai_ket_cuc_khac_nhau(self):
        ad = ad_that()
        yc = ad.yeu_cau_tao_don(dict(DON_MAU))
        yc["url"] = "http://127.0.0.1:1"
        tam_thoi = HttpGia(loi=tp.LoiTamThoi("mạng chập"))
        kq_tt = ad._goi_that(tam_thoi, "trackOrder", dict(yc, url="http://127.0.0.1:1"))
        vinh_vien = HttpGia(loi=tp.LoiVinhVien("URL sai"))
        kq_vv = ad._goi_that(vinh_vien, "trackOrder", dict(yc, url="http://127.0.0.1:1"))
        self.assertTrue(kq_tt.timeout, "LoiTamThoi ⇒ KHÔNG BIẾT kết quả")
        self.assertFalse(kq_tt.ok)
        self.assertEqual(kq_tt.tho["loi_chuan"]["ma_chuan"], lh.HET_GIO)
        self.assertFalse(kq_vv.timeout, "LoiVinhVien ⇒ biết chắc là hỏng")
        self.assertFalse(kq_vv.ok)
        self.assertNotEqual(kq_tt.tho["loi_chuan"]["ma_chuan"],
                            kq_vv.tho["loi_chuan"]["ma_chuan"],
                            "hai loại lỗi bị gộp làm một ⇒ mất phân biệt ba kết cục")
        self.assertEqual(len(tam_thoi.lan), 3, "LoiTamThoi phải được thử lại theo chính sách")
        self.assertEqual(len(vinh_vien.lan), 1, "LoiVinhVien KHÔNG được thử lại")

    def test_i5_khong_co_url_thi_dung_chu_khong_gui_bua(self):
        fake = HttpGia(tra_loi=TraLoiGia(200, b'{"code":"1"}'))
        ad = ad_that()
        yc = ad.yeu_cau_tao_don(dict(DON_MAU))
        self.assertIsNone(yc["url"], "ở mock URL phải là None")
        with self.assertRaises(aj.ChuaXacNhanTaiLieu):
            ad._goi_that(fake, "createOrder", yc)
        self.assertEqual(fake.lan, [], "gửi đi khi CHƯA biết URL")

    def test_i6_lop_gia_dung_chu_ky_hop_dong_36(self):
        """TỰ KIỂM: lớp giả phải trùng chữ ký §36, nếu không thì nhóm I đo một hợp đồng khác."""
        r = inspect.signature(HttpGia.gui_form)
        self.assertEqual(list(r.parameters), ["self", "url", "headers", "body", "timeout"])
        self.assertIs(r.parameters["timeout"].kind, inspect.Parameter.KEYWORD_ONLY)
        if http_that is not None:
            r2 = inspect.signature(http_that.gui_form)
            self.assertEqual(list(r2.parameters), ["url", "headers", "body", "timeout"],
                             "lớp HTTP THẬT lệch chữ ký §36")
            self.assertIs(r2.parameters["timeout"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertTrue(callable(getattr(http_that, "gui_form", None))
                        if http_that is not None else True)


if __name__ == "__main__":
    kq = unittest.main(verbosity=2, exit=False).result
    print()
    print("=" * 78)
    print("PHẠM VI ĐÃ ĐO: hành vi của app/adapter_jt.py ở môi trường MOCK + hàm đọc gói trả lời")
    print("  chạy trên gói JSON dựng theo quy ước tài liệu + các chốt chặn LIVE (đo bằng cách mở")
    print("  tạm CHO_PHEP_LIVE rồi đóng lại).")
    print("  G16-A THÊM: đường gửi THẬT (adapter → transport.goi → http_jt.gui_form → socket) đo")
    print("  trên stub CỤC BỘ 127.0.0.1 cổng 0; nhóm H bỏ qua kèm lý do nếu AG-02 chưa giao tệp.")
    print("  KHÔNG có lượt gọi nào ra Internet: stub chỉ bind vòng lặp nội bộ, và danh sách trắng")
    print("  của http_jt chặn mọi host khác.")
    print("NẰM NGOÀI: J&T thật có chấp nhận chữ ký/tham số không; mã lỗi thật của hãng có đúng")
    print("  như bảng đã đọc không; sandbox hãng có sống không; callback hãng ký bằng khoá nào.")
    print("  ⇒ KHÔNG được báo 'LIVE VERIFIED': V-G09-01 và V-13906-05 CHƯA CẤP.")
    print(f"Tổng: {kq.testsRun} ca · hỏng {len(kq.failures)} · lỗi {len(kq.errors)} "
          f"· bỏ qua {len(kq.skipped)}")
    print("=" * 78)
    sys.exit(bool(kq.failures or kq.errors))
