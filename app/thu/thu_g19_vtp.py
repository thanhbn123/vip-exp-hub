# G19 (AG-03) — MÃ TRẠNG THÁI VIETTEL POST: ĐÓNG LỖ HỔNG `BAN_GIAO.md` §6.1.
#
# Lỗ hổng: «21 mã trạng thái Viettel Post (AG-03 khảo sát, chưa áp)». Bộ thử này là BẰNG CHỨNG
# cho việc áp 13 con số CÓ NGUỒN trong repo, và cho việc **KHÔNG** áp 8 con số không có nguồn.
#
# PHẠM VI — nói thẳng cái gì NẰM NGOÀI:
#   · KHÔNG gọi hãng, kể cả sandbox: `V-G09-01` + `V-13906-05` CHƯA CẤP. Tệp này không mở socket,
#     không HTTP, không credentials. Điều đó ÉP BẰNG MÃ ở lớp `F` (quét mã nguồn hai tệp).
#   · KHÔNG đo được nghĩa THẬT của 21 mã VTP: repo này chỉ có bản khảo sát GIÁN TIẾP. Cái đo được
#     là: 13 con số có tên trong repo đã vào bảng đúng mức tin cậy của chúng, và 12 mã chưa xác
#     minh KHÔNG bị ánh xạ bừa.
#   · KHÔNG đo được 8 con số còn thiếu của bộ 21 — chúng KHÔNG hề xuất hiện trong repo. Bộ thử
#     khẳng định đúng điều đó (không thể liệt kê cái không có nguồn) thay vì bịa ra chúng.
#
# BA LUẬT CỦA BỘ THỬ NÀY (theo docs/QA_G13_G15.md §6.3):
#   1. Mỗi khẳng định PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG. «12 mã không bị ánh xạ» chỉ có nghĩa khi
#      chứng minh được đường ánh xạ ĐANG chạy: mã 200 đi qua đúng và ra `lay_hang`, J&T 113 vẫn ra
#      `giao_thanh_cong`, khoá mô phỏng vẫn tra được.
#   2. Bộ dò phải TỰ KIỂM bằng ĐỘT BIẾN: tiêm một ánh xạ bừa vào bảng rồi chạy lại ĐÚNG bộ dò —
#      nó phải ĐỎ. Kèm ĐỐI CHỨNG ĐƯỜNG: không tiêm thì XANH.
#   3. Chốt cứng phải là chốt của MÃ SẢN PHẨM, không phải của bộ thử: ca `D3` sửa thẳng bảng rồi
#      kiểm `quyet_dinh()` vẫn chặn — nếu chốt chỉ nằm trong bộ thử thì nó không bảo vệ ai.
import os
import re
import sys
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
for _d in (GOC, THU):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import cau_hinh                                                         # noqa: E402
import trang_thai_hang as tth                                           # noqa: E402

# ============================================================================
# BẢNG ĐỐI CHIẾU CỦA G19 — mã → trạng thái được phép áp → nhãn soát → vì sao.
#
# Đây là bản CHẠY ĐƯỢC của bảng trong `docs/G19_VTP_CODES.md` §2. Sửa bảng kia mà không sửa đây
# thì hai tài liệu lệch nhau, và ca `a5` dưới sẽ đỏ.
# ============================================================================
DOI_CHIEU = {
    101: (None, "NEEDS_REVIEW", "huong_cuoi_khong_ro"),
    102: (None, "NEEDS_REVIEW", "chua_co_nghia"),
    104: (None, "NEEDS_REVIEW", "mau_thuan_tai_lieu"),
    107: (None, "NEEDS_REVIEW", "huong_cuoi_khong_ro"),
    200: ("lay_hang", "OK", None),
    201: (None, "NEEDS_REVIEW", "huong_cuoi_khong_ro"),
    202: (None, "NEEDS_REVIEW", "chua_co_nghia"),
    501: (None, "NEEDS_REVIEW", "huong_cuoi_khong_ro"),
    503: (None, "NEEDS_REVIEW", "chua_co_nghia"),
    504: (None, "NEEDS_REVIEW", "huong_cuoi_khong_ro"),
    505: (None, "NEEDS_REVIEW", "chua_co_nghia"),
    508: (None, "NEEDS_REVIEW", "chua_co_nghia"),
    550: (None, "NEEDS_REVIEW", "chua_co_nghia"),
}

# Nguồn của từng NHÓM mã, chép từ chính repo này (không phải từ trí nhớ, không phải từ hãng).
NGUON_NHOM = {
    "chua_co_nghia": ("docs/VTP_YEU_CAU_BO_SUNG.md:36 + docs/G12_VTP_KHAO_SAT.md:86 — sáu mã "
                      "(102, 202, 503, 505, 508, 550) mà chính repo nguồn CỐ Ý không ánh xạ"),
    "huong_cuoi_khong_ro": ("docs/VTP_YEU_CAU_BO_SUNG.md:80 (câu B1) — đoạn «Lưu ý» liệt kê "
                            "trạng thái cuối là 101/107/201/501/503/504, KHÔNG nói hướng nào"),
    "mau_thuan_tai_lieu": ("docs/VTP_YEU_CAU_BO_SUNG.md:80 + docs/G12_VTP_KHAO_SAT.md:150 + "
                           "docs/G09_FINAL_REPORT.md:200 — bảng nói 104 là trạng thái cuối, "
                           "«Lưu ý» nói không, mà 104 đứng trước 200"),
}

# SÁU mã mà chính repo nguồn để trống ánh xạ — nguồn nêu ĐÍCH DANH cả sáu.
SAU_MA_KHONG_ANH_XA = (102, 202, 503, 505, 508, 550)
# NĂM mã còn lại của nhóm «trạng thái cuối» sau khi trừ 503 (503 nằm ở nhóm trên).
NAM_MA_CUOI = (101, 107, 201, 501, 504)


class Nen(unittest.TestCase):
    def _nguon(self, ten):
        duong = os.path.join(GOC, ten) if ten.endswith(".py") else os.path.join(
            os.path.dirname(GOC), ten)
        with open(duong, encoding="utf-8") as f:
            return f.read()


# ============================================================================
class A_BangDoiChieu(Nen):
    """13 con số CÓ NGUỒN đã vào bảng — và vào đúng chỗ theo mức tin cậy."""

    def test_a1_dung_muoi_ba_ma_that_da_vao_bang(self):
        """Tập mã THẬT của hãng trong bảng phải ĐÚNG BẰNG tập có nguồn trong repo.

        Không hơn (thêm mã không nguồn = bịa) và không kém (thiếu mã có nguồn = chưa đóng lỗ).
        """
        self.assertEqual(sorted(tth.VTP_MA), sorted(DOI_CHIEU),
                         "bảng VTP_MA và bảng đối chiếu của G19 lệch nhau")
        for ma in DOI_CHIEU:
            self.assertIsInstance(ma, int,
                                  f"mã hãng {ma!r} phải là SỐ (ORDER_STATUS của VTP là số)")

    def test_a2_sau_khoa_mo_phong_van_con_nguyen(self):
        """ĐỐI CHỨNG DƯƠNG cho đường MOCK: gộp bảng không được làm chết bộ mô phỏng."""
        for khoa in ("cho_lay", "lay_hang", "dang_giao", "giao_thanh_cong",
                     "giao_that_bai", "hoan_hang"):
            self.assertIn(khoa, tth.BANG["vtp"], f"mất khoá mô phỏng {khoa!r}")
            self.assertEqual(tth.anh_xa("vtp", khoa).trang_thai, khoa,
                             f"khoá mô phỏng {khoa!r} không còn ánh xạ đúng")

    def test_a3_moi_ma_that_deu_co_mo_ta(self):
        for ma, (mo_ta, _tt) in tth.VTP_MA.items():
            self.assertTrue(str(mo_ta or "").strip(), f"mã {ma} thiếu mô tả")

    def test_a4_nguon_va_phien_ban_tai_lieu_noi_dung_su_that(self):
        """Trước G19 ô này ghi «chưa có tài liệu». Nay có mã thật ⇒ phải khai nguồn THẬT."""
        self.assertNotIn("chua-co-tai-lieu", tth.PHIEN_BAN_TAI_LIEU["vtp"],
                         "đã có mã hãng trong bảng mà vẫn khai «chưa có tài liệu»")
        self.assertIn("VTP_YEU_CAU_BO_SUNG", tth.NGUON_BANG["vtp"],
                      "nguồn bảng VTP không dẫn tài liệu khảo sát trong repo")
        self.assertIn("CHƯA", tth.NGUON_BANG["vtp"].upper(),
                      "nguồn bảng VTP phải nói rõ là CHƯA đối chiếu trang hãng")
        self.assertFalse(tth.VTP_CO_NGUYEN_VAN_HANG,
                         "cờ «có nguyên văn của hãng» bật lên mà chưa ai đọc trang hãng")

    def test_a5_bang_doi_chieu_tung_ma(self):
        """Ca CHÍNH: từng mã → trạng thái được phép áp → nhãn soát → vì sao."""
        for ma, (tt, nhan, loai) in sorted(DOI_CHIEU.items()):
            qd = tth.quyet_dinh("vtp", ma)
            with self.subTest(ma=ma):
                self.assertTrue(qd.biet_ma, f"{ma}: mã có nguồn mà bị coi là mã lạ")
                self.assertEqual(qd.trang_thai_ap, tt, f"{ma}: trạng thái áp sai")
                self.assertEqual(qd.nhan, nhan, f"{ma}: nhãn soát sai")
                if loai is None:
                    self.assertIsNone(tth.CHUA_XAC_MINH.get(("vtp", ma)),
                                      f"{ma}: mã áp được mà lại nằm trong sổ chưa xác minh")
                else:
                    muc = tth.CHUA_XAC_MINH.get(("vtp", ma))
                    self.assertIsNotNone(muc, f"{ma}: mã chưa xác minh mà không có hồ sơ")
                    self.assertEqual(muc["loai"], loai, f"{ma}: phân loại chưa xác minh sai")
                    self.assertTrue(str(muc["ly_do"]).strip(), f"{ma}: thiếu lý do")
                    self.assertIn("VTP", muc["nguon"], f"{ma}: thiếu nguồn")

    def test_a6_moi_ma_chua_xac_minh_deu_co_nguon_dan_duoc(self):
        """Nguồn phải chỉ vào MỘT trong ba nhóm có thật trong repo — không nhóm nào bịa."""
        dem = {"chua_co_nghia": 0, "huong_cuoi_khong_ro": 0, "mau_thuan_tai_lieu": 0}
        for (_hang, _ma), muc in tth.CHUA_XAC_MINH.items():
            self.assertIn(muc["loai"], NGUON_NHOM)
            self.assertTrue(NGUON_NHOM[muc["loai"]].strip())
            dem[muc["loai"]] += 1
        self.assertEqual(dem["chua_co_nghia"], 6)
        self.assertEqual(dem["huong_cuoi_khong_ro"], 5)
        self.assertEqual(dem["mau_thuan_tai_lieu"], 1)

    def test_a7_bay_gio_khong_con_bi_bia(self):
        """Tám con số KHÔNG có nguồn thì KHÔNG được có mặt — kể cả trong tài liệu G19."""
        doc = os.path.join(os.path.dirname(GOC), "docs", "G19_VTP_CODES.md")
        self.assertTrue(os.path.exists(doc), "thiếu docs/G19_VTP_CODES.md")
        with open(doc, encoding="utf-8") as f:
            n = f.read()
        self.assertIn("8 con số", n, "tài liệu G19 không nói ra phần còn thiếu của bộ 21")
        self.assertIn("21", n)
        # Bảng mã trong mã nguồn KHÔNG được phình thêm mã nào ngoài 13 con số có nguồn.
        self.assertEqual(len(tth.VTP_MA), 13)


# ============================================================================
class B_CaDuong(Nen):
    """ĐƯỜNG ÁNH XẠ ĐANG CHẠY THẬT — nếu lớp này đỏ thì mọi khẳng định phủ định ở lớp C vô nghĩa."""

    def test_b1_ma_200_di_qua_va_ra_lay_hang(self):
        qd = tth.quyet_dinh("vtp", 200)
        self.assertEqual(qd.trang_thai_ap, "lay_hang")
        self.assertEqual(qd.nhan, "OK")
        self.assertTrue(qd.biet_ma)
        self.assertFalse(qd.can_soat)

    def test_b2_ma_200_dang_CHUOI_cung_ra_lay_hang(self):
        """ORDER_STATUS đi qua JSON nên có thể tới dạng chuỗi — chuỗi số phải hiểu được.

        Không có ca này thì một sự kiện thật gửi `"200"` rơi IM LẶNG vào nhánh «mã lạ».
        """
        qd = tth.quyet_dinh("vtp", "200")
        self.assertEqual(qd.trang_thai_ap, "lay_hang", "chuỗi số không được chuẩn hoá")
        self.assertEqual(qd.nhan, "OK")

    def test_b3_do_tin_cay_bi_ha_tran_vi_nguon_gian_tiep(self):
        """ĐỐI CHỨNG ĐƯỜNG cho trần tin cậy: J&T đọc trực tiếp ⇒ 'cao'; VTP gián tiếp ⇒ 'trung_binh'."""
        self.assertEqual(tth.quyet_dinh("vtp", 200).do_tin_cay, tth.TIN_TRUNG_BINH,
                         "nguồn gián tiếp mà khai độ tin cậy 'cao'")
        self.assertEqual(tth.quyet_dinh("jt", 106).do_tin_cay, tth.TIN_CAO,
                         "J&T đọc trực tiếp mà bị hạ trần — trần đang chặn nhầm")

    def test_b4_jt_van_chay_binh_thuong(self):
        """G19 chỉ được đụng VTP."""
        self.assertEqual(tth.quyet_dinh("jt", 113).trang_thai_ap, "giao_thanh_cong")
        self.assertEqual(tth.quyet_dinh("jt", 118).trang_thai_ap, "giao_that_bai")
        self.assertEqual(len(tth.JT_MA), 13, "bảng J&T bị G19 sửa số lượng mã")

    def test_b5_khong_ma_vtp_nao_duoc_ap_trang_thai_hoan_tat(self):
        """MÃ VTP CHƯA XÁC MINH THÌ KHÔNG ĐƯỢC ĐÓNG ĐƠN — kể cả mã 200 đã áp được.

        Hướng hoàn tất của VTP (giao xong / hoàn xong) chưa ai xác minh, nên không mã VTP nào
        được phép chạm `giao_thanh_cong` hay `hoan_hang`.
        """
        for ma in tth.VTP_MA:
            tt = tth.quyet_dinh("vtp", ma).trang_thai_ap
            self.assertNotIn(tt, tth.TRANG_THAI_HOAN_TAT, f"mã {ma} đóng đơn mà chưa xác minh")
        # ĐỐI CHỨNG DƯƠNG: đường đóng đơn CÓ thật và đang chạy — không phải «không bao giờ tới».
        self.assertIn(tth.quyet_dinh("jt", 113).trang_thai_ap, tth.TRANG_THAI_HOAN_TAT)

    def test_b6_moi_trang_thai_ap_duoc_deu_la_trang_thai_chuan(self):
        hop_le = set(cau_hinh.HANG_TRANG_THAI_GIAO)
        for ma in tth.VTP_MA:
            tt = tth.quyet_dinh("vtp", ma).trang_thai_ap
            if tt is not None:
                self.assertIn(tt, hop_le, f"mã {ma} ánh xạ ra trạng thái không có trong hệ")


# ============================================================================
class C_CaAm(Nen):
    """MÃ CHƯA XÁC MINH: KHÔNG ĐOÁN — và chứng minh được là KHÔNG đoán bừa."""

    def test_c1_muoi_hai_ma_chua_xac_minh_deu_NEEDS_REVIEW(self):
        for ma in tth.ma_chua_xac_minh("vtp"):
            qd = tth.quyet_dinh("vtp", ma)
            with self.subTest(ma=ma):
                self.assertTrue(qd.biet_ma, f"{ma}: mã có thật mà bị coi là mã lạ")
                self.assertIsNone(qd.trang_thai_ap, f"{ma}: ĐÃ ÁNH XẠ BỪA")
                self.assertEqual(qd.nhan, "NEEDS_REVIEW", f"{ma}: nhãn soát sai")
                self.assertTrue(qd.can_soat, f"{ma}: không bắt người soát")
                self.assertEqual(qd.do_tin_cay, tth.TIN_CHUA_XAC_MINH)
                self.assertIn("KHÔNG đoán", qd.ghi_chu, f"{ma}: dấu vết không nói vì sao bỏ qua")
                self.assertEqual(tth.ly_do_chua_xac_minh("vtp", ma),
                                 tth.CHUA_XAC_MINH[("vtp", ma)]["ly_do"],
                                 f"{ma}: hàm tra lý do trả khác hồ sơ")
        self.assertEqual(len(tth.ma_chua_xac_minh("vtp")), 12)

    def test_c2_sau_ma_nguon_CO_Y_khong_anh_xa_van_khong_bi_anh_xa(self):
        """Sáu mã mà chính repo nguồn để trống — nguồn nêu ĐÍCH DANH từng mã."""
        for ma in SAU_MA_KHONG_ANH_XA:
            self.assertIn(ma, tth.VTP_MA, f"{ma}: mã có nguồn mà chưa vào bảng")
            self.assertIsNone(tth.VTP_MA[ma][1], f"{ma}: bảng điền giá trị dù nguồn để trống")
            self.assertIsNone(tth.quyet_dinh("vtp", ma).trang_thai_ap, f"{ma}: ánh xạ bừa")

    def test_c3_nam_ma_cuoi_khong_ro_huong(self):
        """Nhóm «trạng thái cuối»: biết là cuối, KHÔNG biết cuối theo hướng nào ⇒ cấm đoán."""
        for ma in NAM_MA_CUOI:
            muc = tth.CHUA_XAC_MINH[("vtp", ma)]
            self.assertEqual(muc["loai"], "huong_cuoi_khong_ro")
            self.assertIn("hướng", muc["ly_do"].lower())
            self.assertIsNone(tth.quyet_dinh("vtp", ma).trang_thai_ap)
        # ĐỐI CHỨNG: 503 nằm trong CẢ hai danh sách của nguồn, nên nó ở nhóm chưa có nghĩa.
        self.assertIn(503, SAU_MA_KHONG_ANH_XA)

    def test_c4_ma_104_ghi_lai_mau_thuan_chu_khong_chon_ben(self):
        muc = tth.CHUA_XAC_MINH[("vtp", 104)]
        self.assertEqual(muc["loai"], "mau_thuan_tai_lieu")
        for phai_co in ("mâu thuẫn", "cuối", "200"):
            self.assertIn(phai_co, muc["ly_do"].lower(), f"hồ sơ 104 thiếu vế '{phai_co}'")
        qd = tth.quyet_dinh("vtp", 104)
        self.assertIsNone(qd.trang_thai_ap, "104 bị chọn một bên rồi áp vào đơn")
        self.assertEqual(qd.nhan, "NEEDS_REVIEW")
        self.assertIn("Lấy hàng điều phối bưu tá", qd.mo_ta_goc)

    def test_c5_ma_ngoai_bang_van_la_ma_la(self):
        """ĐỐI CHỨNG ÂM cho mọi ca trên: mã KHÔNG có nguồn thì vẫn là mã lạ, không phải NEEDS_REVIEW
        của sổ mới — hai thứ khác nhau và không được gộp."""
        for ma in (999, 0, 1, 250, 12345, "MA-LA-999", "abc"):
            qd = tth.quyet_dinh("vtp", ma)
            with self.subTest(ma=ma):
                self.assertFalse(qd.biet_ma, f"{ma}: mã không nguồn mà nhận là đã biết")
                self.assertIsNone(qd.trang_thai_ap)
                self.assertEqual(qd.nhan, "NEEDS_REVIEW")
                self.assertEqual(qd.do_tin_cay, tth.TIN_MA_LA)
                self.assertFalse(qd.chua_xac_minh)

    def test_c6_khong_chot_duoc_nghia_cho_ma_chua_xac_minh(self):
        """Sổ `CHUA_XAC_MINH` KHÔNG phải sổ nhập nhằng: không có nghĩa nào để «chốt».

        Nếu ai đó nhét mã chưa xác minh vào `NHAP_NHANG`, ca này đỏ — đó là đường vòng để
        biến một phỏng đoán thành «nghĩa đã chốt».
        """
        for ma in tth.ma_chua_xac_minh("vtp"):
            self.assertFalse(tth.la_nhap_nhang("vtp", ma), f"{ma} bị đưa vào sổ nhập nhằng")
            with self.assertRaises(KeyError):
                tth.chot_nghia("vtp", ma, "bat_ky", "nguoi-thu", "can-cu-thu")
        self.assertEqual(tth.NGHIA_DA_CHOT, {}, "có nghĩa được chốt sẵn trong mã nguồn")

    def test_c7_ho_so_chua_xac_minh_du_de_soat_lai(self):
        """Đủ dấu vết: mã gốc · mô tả gốc · nguồn · phiên bản tài liệu · vì sao · nhãn."""
        qd = tth.quyet_dinh("vtp", 550, su_kien_goc={"nguon": "ca-thu"})
        for t in ("ma_goc", "mo_ta_goc", "su_kien_hang_goc", "nguon_tai_lieu",
                  "phien_ban_tai_lieu", "nhan_luc", "ghi_chu", "do_tin_cay"):
            self.assertTrue(getattr(qd, t) not in (None, "", {}), f"thiếu dấu vết: {t}")
        self.assertEqual(qd.ma_goc, 550)
        self.assertIn("khảo sát", qd.nguon_tai_lieu)


# ============================================================================
class D_TuKiemBangDotBien(Nen):
    """Bộ dò PHẢI ĐỎ ĐƯỢC. Không có lớp này thì «12 mã không bị ánh xạ bừa» chỉ là lời nói."""

    def _vi_pham(self):
        """Bộ dò ĐỘC LẬP: đọc thẳng bảng + sổ, không tin `quyet_dinh()`."""
        loi = []
        for ma in tth.VTP_MA:
            if tth.VTP_MA[ma][1] is not None:
                continue
            if ("vtp", ma) not in tth.CHUA_XAC_MINH:
                loi.append(f"{ma}: bảng để None mà không có hồ sơ chưa xác minh")
        for ma in tth.ma_chua_xac_minh("vtp"):
            if tth.VTP_MA.get(ma, (None, None))[1] is not None:
                loi.append(f"{ma}: vừa chưa xác minh vừa có giá trị trong bảng")
        return loi

    def setUp(self):
        self._goc = dict(tth.VTP_MA)

    def tearDown(self):
        tth.VTP_MA.clear()
        tth.VTP_MA.update(self._goc)
        tth.BANG["vtp"] = dict(tth.VTP_MA, **tth.VTP_MA_MOCK)

    def test_d1_doi_chung_duong_khong_tiem_thi_XANH(self):
        self.assertEqual(self._vi_pham(), [], "bộ dò báo đỏ trên cây SẠCH — bộ dò hỏng")

    def test_d2_TIEM_anh_xa_bua_thi_bo_do_PHAI_DO(self):
        """Tiêm `giao_thanh_cong` cho mã 550 (mã chưa xác minh) ⇒ bộ dò phải thấy."""
        tth.VTP_MA[550] = ("bịa", "giao_thanh_cong")
        tth.BANG["vtp"][550] = ("bịa", "giao_thanh_cong")
        self.assertNotEqual(self._vi_pham(), [], "ánh xạ bừa lọt qua bộ dò")
        self.assertIsNone(tth.quyet_dinh("vtp", 550).trang_thai_ap,
                          "CHỐT CỦNG của sản phẩm không giữ: bảng bị sửa là đơn bị đổi trạng thái")
        self.assertEqual(tth.quyet_dinh("vtp", 550).nhan, "NEEDS_REVIEW")

    def test_d3_TIEM_trang_thai_hoan_tat_thi_van_bi_chan(self):
        """Kể cả tiêm thẳng `hoan_hang` (trạng thái HOÀN TẤT) — chốt cứng của sản phẩm vẫn chặn."""
        for ma in (101, 550):
            tth.VTP_MA[ma] = ("bịa", "hoan_hang")
            tth.BANG["vtp"][ma] = ("bịa", "hoan_hang")
        for ma in (101, 550):
            qd = tth.quyet_dinh("vtp", ma)
            with self.subTest(ma=ma):
                self.assertIsNone(qd.trang_thai_ap, "mã chưa xác minh đóng được đơn")
                self.assertIn("CHẶN", qd.ghi_chu)
                self.assertEqual(qd.nhan, "NEEDS_REVIEW")

    def test_d4_TIEM_xoa_ho_so_thi_bo_do_PHAI_DO(self):
        """Đường vòng thứ hai: giữ bảng None nhưng XOÁ hồ sơ chưa xác minh ⇒ mất dấu vết."""
        tth.CHUA_XAC_MINH.pop(("vtp", 508))
        try:
            self.assertNotEqual(self._vi_pham(), [], "xoá hồ sơ mà bộ dò không thấy")
        finally:
            tth.CHUA_XAC_MINH[("vtp", 508)] = {
                "loai": "chua_co_nghia", "ly_do": "khôi phục sau ca thử", "nguon": tth.NGUON_VTP}


# ============================================================================
class E_GiuNguyenD4(Nen):
    """D-4 (J&T 110) — nguyên tắc «KHÔNG đoán mã» giữ nguyên, không nới cho VTP."""

    def test_e1_jt_110_van_AMBIGUOUS_va_khong_doi_don(self):
        qd = tth.quyet_dinh("jt", 110)
        self.assertEqual(qd.nhan, "AMBIGUOUS")
        self.assertIsNone(qd.trang_thai_ap)
        self.assertTrue(qd.can_soat)
        self.assertEqual(qd.do_tin_cay, tth.TIN_NHAP_NHANG)
        self.assertGreaterEqual(len(qd.cac_nghia or {}), 2)
        self.assertEqual(tth.anh_xa("jt", 110).trang_thai, "dang_giao",
                         "nghĩa theo bảng tham số dùng cho ĐỌC vẫn phải giữ")

    def test_e2_hai_so_mot_hang_mot_kieu_khong_gop(self):
        """110 của J&T và các mã VTP chưa xác minh: hai CƠ CHẾ khác nhau, hai nhãn khác nhau."""
        self.assertEqual(tth.quyet_dinh("jt", 110).nhan, "AMBIGUOUS")
        self.assertEqual(tth.quyet_dinh("vtp", 104).nhan, "NEEDS_REVIEW")
        self.assertTrue(tth.la_nhap_nhang("jt", 110))
        self.assertFalse(tth.la_nhap_nhang("vtp", 104),
                         "104 là ca CHƯA XÁC MINH, không phải ca đã đọc được hai nghĩa")

    def test_e3_khong_ai_chot_san_nghia_nao(self):
        self.assertEqual(tth.NGHIA_DA_CHOT, {})
        self.assertEqual(sorted(tth.NHAP_NHANG), [("jt", 110)],
                         "sổ nhập nhằng bị thêm mục ngoài J&T 110 — kiểm lại phạm vi G19")


# ============================================================================
class F_KhongGoiHang(Nen):
    """BẰNG CHỨNG «KHÔNG gọi hãng» — ép bằng mã, không bằng lời hứa.

    Phép quét NEO Ở ĐẦU DÒNG. Bản đầu quét `assertNotIn("import socket", n)` và **tự bắt chính
    nó** — chuỗi đó nằm ngay trong danh sách cấm của tệp này. Một bộ dò tự bắt mình là bộ dò
    không đo được gì; neo đầu dòng thì danh sách cấm không còn khớp với chính nó.
    """
    CAM_NHAP = re.compile(
        r"^\s*(?:import|from)\s+(socket|urllib|requests|httpx|http\.client)\b", re.M)
    CAM_LIVE = re.compile(r"CHO_PHEP_LIVE\s*=")

    def _quet(self, n, ten):
        self.assertEqual(self.CAM_NHAP.findall(n), [], f"{ten} nhập mô-đun mạng")
        self.assertEqual(self.CAM_LIVE.findall(n), [], f"{ten} gán CHO_PHEP_LIVE")

    def test_f1_module_anh_xa_khong_co_duong_ra_mang(self):
        self._quet(self._nguon("trang_thai_hang.py"), "trang_thai_hang.py")

    def test_f2_bo_thu_nay_cung_khong_ra_mang(self):
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            self._quet(f.read(), "chính bộ thử")

    def test_f3_doi_chung_duong_phep_quet_BAT_DUOC_chieu_cam(self):
        """ĐỐI CHỨNG DƯƠNG của chính bộ quét: đưa vào một dòng bị cấm thì nó PHẢI thấy."""
        mau = "import os\n" + "import " + "socket\n" + "x = 1\n"
        self.assertNotEqual(self.CAM_NHAP.findall(mau), [], "bộ quét không bắt được dòng cấm")
        self.assertNotEqual(self.CAM_LIVE.findall("CHO_PHEP_LIVE" + " = True\n"), [])
        # ...và KHÔNG bắt bừa: dòng hợp lệ phải đi qua.
        self.assertEqual(self.CAM_NHAP.findall("import os\nimport re\n"), [])
        self.assertEqual(self.CAM_LIVE.findall("# nhắc tới CHO_PHEP_LIVE trong chú thích\n"), [])

    def test_f4_khong_co_credentials_trong_tep_thu(self):
        with open(os.path.abspath(__file__), encoding="utf-8") as f:
            n = f.read()
        self.assertEqual(re.findall(r"(?i)(password|secret|api[_-]?key|token)\s*=", n), [],
                         "bộ thử khai biến kiểu credentials")


if __name__ == "__main__":
    unittest.main(verbosity=2)
