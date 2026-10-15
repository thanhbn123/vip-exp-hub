# Bộ thử ĐỐI SOÁT TIỀN G07.4 (nạp bảng kê hãng · ánh xạ cột theo hãng · phân loại chênh lệch
# · phê duyệt · đồng thời · idempotent).
# Chạy: python3 app/thu/thu_doi_soat.py
#
# Nguyên tắc (CLAUDE.md §12.1):
#   - "Import idempotent" đo bằng cách nạp ĐÚNG file đó LẦN HAI rồi đếm tiền trong sổ, không
#     bằng đọc thấy có ràng buộc UNIQUE trong DDL.
#   - "Đối soát đồng thời không áp hai lần" đo bằng HAI THREAD thật đua nhau duyệt.
#   - "Mỗi loại lệch một nhãn riêng" đo bằng một file có đủ từng loại, rồi đếm theo loại.
#   - Mỗi hãng một file mẫu RIÊNG với tiêu đề thật khác nhau — không dùng một mẫu chung rồi
#     tưởng là đã thử hai hãng.
import io
import os
import sys
import tempfile
import threading
import unittest
import zipfile

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-doisoat-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl        # noqa: E402
import doi_soat    # noqa: E402
import don_hang    # noqa: E402
import quyen       # noqa: E402
import tai_chinh   # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from thu_tai_chinh import _dung_nen, _tao_don   # noqa: E402  — dùng lại khuôn dữ liệu


NEN = None


def setUpModule():
    global NEN
    csdl.mo()
    tai_chinh._dam_bao_bang()
    NEN = _dung_nen()


def _csv_vtp(dong):
    """Mẫu bảng kê VTP — tiêu đề tiếng Việt, tiền có dấu phân cách nghìn."""
    ra = ["Mã vận đơn,Mã đơn,Tiền COD,Cước chính,Kỳ đối soát,Trạng thái"]
    for mvd, mdon, cod, phi, ky in dong:
        ra.append(f"{mvd},{mdon},{cod},{phi},{ky},Đã giao")
    return ("\r\n".join(ra) + "\r\n").encode("utf-8")


def _csv_jt(dong):
    """Mẫu bảng kê J&T — tiêu đề tiếng Anh, THỨ TỰ CỘT KHÁC VTP."""
    ra = ["settlement period,billCode,codAmount,freight,orderId,status"]
    for mvd, mdon, cod, phi, ky in dong:
        ra.append(f"{ky},{mvd},{cod},{phi},{mdon},Delivered")
    return ("\r\n".join(ra) + "\r\n").encode("utf-8")


def _xlsx(hang_dau, cac_dong):
    """XLSX tối thiểu, chỉ inlineStr — đủ cho `nhap_file.doc_xlsx` đọc."""
    def o(v, c, r):
        return (f'<c r="{c}{r}" t="inlineStr"><is><t>'
                f'{str(v).replace("&", "&amp;").replace("<", "&lt;")}</t></is></c>')
    cot = "ABCDEFGHIJ"
    rows = []
    for ri, hang in enumerate([hang_dau] + cac_dong, start=1):
        rows.append(f'<row r="{ri}">' + "".join(o(v, cot[i], ri) for i, v in enumerate(hang))
                    + "</row>")
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>' + "".join(rows) + "</sheetData></worksheet>")
    bo = io.BytesIO()
    with zipfile.ZipFile(bo, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://'
                    'schemas.openxmlformats.org/package/2006/content-types"/>')
        zf.writestr("xl/workbook.xml", '<?xml version="1.0"?><workbook/>')
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return bo.getvalue()


# ================================================================= A. Ánh xạ cột theo hãng
class A_AnhXaCot(unittest.TestCase):
    def test_a1_moi_hang_mot_dinh_dang_rieng(self):
        """Hai hãng, hai tiêu đề khác nhau, hai thứ tự cột khác nhau — cùng đọc ra đúng."""
        t, u = NEN["t1"], NEN["u1"]
        don_v = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=NEN["ca1"])
        dv = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don_v,))
        kq_v = doi_soat.nap_bang_ke(t, u, "vtp", "vtp.csv",
                                    _csv_vtp([(dv["ma_van_don"], dv["ma_don"], "100.000",
                                               "20.000", "2026-10")]), ky_thanh_toan="2026-10")
        self.assertEqual(kq_v["so_nap"], 1)
        self.assertIn("cod_hang_bao", kq_v["cot_nhan_ra"])
        self.assertIn("phi_hang_bao", kq_v["cot_nhan_ra"])
        kq_j = doi_soat.nap_bang_ke(t, u, "jt", "jt.csv",
                                    _csv_jt([("JT999", "KHONGCO", "55000", "9000", "2026-10")]),
                                    ky_thanh_toan="2026-10")
        self.assertEqual(kq_j["so_nap"], 1)
        d = csdl.nhieu("SELECT * FROM ds_dong WHERE dot_id=?", (kq_j["dot_id"],))[0]
        self.assertEqual(d["ma_van_don"], "JT999")
        self.assertEqual(d["cod_hang_bao"], 55_000)
        self.assertEqual(d["phi_hang_bao"], 9_000)
        # Dòng VTP đọc đúng cả khi tiền có dấu chấm phân cách nghìn
        dvt = csdl.nhieu("SELECT * FROM ds_dong WHERE dot_id=?", (kq_v["dot_id"],))[0]
        self.assertEqual(dvt["cod_hang_bao"], 100_000)
        self.assertEqual(dvt["phi_hang_bao"], 20_000)

    def test_a2_hang_chua_khai_anh_xa_bi_TU_CHOI(self):
        """Không có ánh xạ thì từ chối, KHÔNG đoán bằng mẫu của hãng khác."""
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            doi_soat.nap_bang_ke(NEN["t1"], NEN["u1"], "hang_la", "x.csv", _csv_vtp([]))
        self.assertIn("chưa có ánh xạ cột", str(e.exception))

    def test_a3_anh_xa_co_phien_ban_va_ghi_de_duoc_trong_CSDL(self):
        t, u = NEN["t1"], NEN["u1"]
        doi_soat.dat_anh_xa("vtp", "2027-01", {"So hieu": "ma_van_don", "Thu ho thuc": "cod_hang_bao"},
                            tenant_id=t)
        bang, pb = doi_soat.anh_xa_cua_hang("vtp", "2027-01", t)
        self.assertEqual(pb, "2027-01")
        self.assertEqual(bang["sohieu"], "ma_van_don")
        kq = doi_soat.nap_bang_ke(t, u, "vtp", "moi.csv",
                                  b"So hieu,Thu ho thuc\r\nVDX1,12000\r\n",
                                  phien_ban="2027-01", ky_thanh_toan="2027-01")
        self.assertEqual(kq["so_nap"], 1)
        self.assertEqual(kq["anh_xa_phien_ban"], "2027-01")
        # Phiên bản cũ KHÔNG bị bản mới đè — bảng kê cũ vẫn đọc lại được
        bang_cu, pb_cu = doi_soat.anh_xa_cua_hang("vtp", "2026-10", t)
        self.assertEqual(pb_cu, "2026-10")
        self.assertEqual(bang_cu["mavandon"], "ma_van_don")

    def test_a4_anh_xa_ghi_de_tro_vao_truong_la_bi_chan(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.dat_anh_xa("vtp", "2027-02", {"X": "truong_khong_ton_tai"})

    def test_a5_bang_ke_khong_co_cot_ma_nao_bi_tu_choi(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            doi_soat.nap_bang_ke(NEN["t1"], NEN["u1"], "vtp", "xau.csv",
                                 b"Cot la,Cot khac\r\n1,2\r\n")
        self.assertIn("mã vận đơn", str(e.exception))

    def test_a6_doc_duoc_XLSX(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=60_000, phi=11_000, ca_id=NEN["ca1"])
        d = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        du = _xlsx(["Mã vận đơn", "Mã đơn", "Tiền COD", "Cước chính", "Kỳ đối soát"],
                   [[d["ma_van_don"], d["ma_don"], "60000", "11000", "2026-11"]])
        kq = doi_soat.nap_bang_ke(t, u, "vtp", "bk.xlsx", du, ky_thanh_toan="2026-11")
        self.assertEqual(kq["so_nap"], 1)

    def test_a7_dinh_dang_khac_bi_tu_choi_ro_rang(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            doi_soat.nap_bang_ke(NEN["t1"], NEN["u1"], "vtp", "bk.pdf", b"%PDF-1.4")
        self.assertIn("chỉ nạp", str(e.exception))

    def test_a8_o_tien_TRONG_khac_o_tien_bang_0(self):
        """Hãng không nói gì (ô trống) ≠ hãng báo thu 0 đồng. Gộp hai thứ là bịa dữ kiện."""
        self.assertIsNone(doi_soat._so_tien_o("", "x"))
        self.assertIsNone(doi_soat._so_tien_o(None, "x"))
        self.assertEqual(doi_soat._so_tien_o("0", "x"), 0)

    def test_a9_o_tien_co_phan_thap_phan_bi_CHAN(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat._so_tien_o("12345.67", "COD")


# ================================================================= B. Phân loại chênh lệch
class B_PhanLoai(unittest.TestCase):
    def test_b1_bay_loai_khong_gop_thanh_mot_nhan_loi(self):
        self.assertEqual(len(doi_soat.LOAI_CHENH_LECH), 7)
        self.assertNotIn("loi", doi_soat.LOAI_CHENH_LECH)

    def test_b2_moi_loai_duoc_phat_hien_rieng(self):
        t, u, ca = NEN["t2"], NEN["u2"], NEN["ca2"]
        # khớp hoàn toàn
        d_khop = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=ca)
        # COD lệch nhẹ (dưới ngưỡng bất thường)
        d_cod = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=ca)
        # phí lệch nhẹ
        d_phi = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=ca)
        # lệch quá ngưỡng → bất thường
        d_bt = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=ca)
        # hệ có mà hãng không báo
        d_thieu = _tao_don(t, u, cod=70_000, phi=20_000, ca_id=ca)
        g = {x: csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (x,))
             for x in (d_khop, d_cod, d_phi, d_bt, d_thieu)}
        dong = [
            (g[d_khop]["ma_van_don"], g[d_khop]["ma_don"], "100000", "20000", "2026-12"),
            (g[d_cod]["ma_van_don"], g[d_cod]["ma_don"], "95000", "20000", "2026-12"),
            (g[d_phi]["ma_van_don"], g[d_phi]["ma_don"], "100000", "21000", "2026-12"),
            (g[d_bt]["ma_van_don"], g[d_bt]["ma_don"], "900000", "20000", "2026-12"),
            ("VD-KHONG-TON-TAI", "D-KHONG-TON-TAI", "50000", "10000", "2026-12"),
            ("", "", "1000", "100", "2026-12"),                      # không có mã để khớp
            (g[d_khop]["ma_van_don"], g[d_khop]["ma_don"], "100000", "20000", "2026-12"),  # trùng
        ]
        kq = doi_soat.nap_bang_ke(t, u, "vtp", "bk-b2.csv", _csv_vtp(dong),
                                  ky_thanh_toan="2026-12", carrier_account_id=ca)
        self.assertEqual(kq["so_trung"], 1, "dòng trùng trong CÙNG file phải bị chặn")
        dc = doi_soat.doi_chieu(t, kq["dot_id"])
        tl = dc["theo_loai"]
        self.assertEqual(tl["cod_lech"], 1, f"theo_loai={tl}")
        self.assertEqual(tl["phi_lech"], 1, f"theo_loai={tl}")
        self.assertEqual(tl["dieu_chinh_bat_thuong"], 1, f"theo_loai={tl}")
        self.assertEqual(tl["thieu_don_he"], 1, f"theo_loai={tl}")
        self.assertEqual(tl["khong_khop_duoc"], 1, f"theo_loai={tl}")
        self.assertEqual(tl["dong_trung"], 1, f"theo_loai={tl}")
        self.assertGreaterEqual(tl["thieu_dong_hang"], 1, f"đơn {d_thieu} phải bị báo thiếu")
        self.assertEqual(dc["so_khop"], 1)
        # Mỗi chênh lệch giữ CẢ HAI số để người xử đối chiếu
        cl = doi_soat.chenh_lech_cua_dot(t, kq["dot_id"], "cod_lech")[0]
        self.assertEqual((cl["so_he"], cl["so_hang"], cl["lech_dong"]), (100_000, 95_000, -5_000))
        self.b2_dot = kq["dot_id"]

    def test_b3_nguong_bat_thuong_tinh_bang_so_nguyen(self):
        self.assertTrue(doi_soat._bat_thuong(100_000, 900_000))     # lệch 800k > 500k
        self.assertTrue(doi_soat._bat_thuong(1_000_000, 1_300_000))  # lệch 30% > 20%
        self.assertFalse(doi_soat._bat_thuong(1_000_000, 1_100_000))  # lệch 10%, 100k < 500k
        self.assertTrue(doi_soat._bat_thuong(100_000, -1))           # số âm là bất thường
        self.assertFalse(doi_soat._bat_thuong(None, 100))            # thiếu số thì KHÔNG kết luận

    def test_b4_bo_qua_chenh_lech_phai_ghi_ly_do(self):
        t, u = NEN["t2"], NEN["u2"]
        don = _tao_don(t, u, cod=10_000, ca_id=NEN["ca2"])
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        kq = doi_soat.nap_bang_ke(t, u, "vtp", "bk-b4.csv",
                                  _csv_vtp([(g["ma_van_don"], g["ma_don"], "9000", "", "2027-03")]),
                                  ky_thanh_toan="2027-03")
        doi_soat.doi_chieu(t, kq["dot_id"])
        cl = doi_soat.chenh_lech_cua_dot(t, kq["dot_id"], "cod_lech")[0]
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.xu_ly_chenh_lech(t, u, cl["id"], "bo_qua", "")
        self.assertTrue(doi_soat.xu_ly_chenh_lech(t, u, cl["id"], "bo_qua", "lệch 1k, hãng đã giải trình"))
        # Xử hai lần bị chặn
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.xu_ly_chenh_lech(t, u, cl["id"], "da_xu", "x")

    def test_b5_xuat_csv_chenh_lech_lam_sach_cong_thuc(self):
        t, u = NEN["t2"], NEN["u2"]
        kq = doi_soat.nap_bang_ke(t, u, "vtp", "bk-b5.csv",
                                  _csv_vtp([("=cmd|'/C calc'!A0", "D-X", "1000", "", "2027-04")]),
                                  ky_thanh_toan="2027-04")
        doi_soat.doi_chieu(t, kq["dot_id"])
        ra = doi_soat.xuat_csv_chenh_lech(t, kq["dot_id"])
        self.assertIn("=cmd", ra)
        self.assertNotIn('"=cmd', ra, "ô công thức chưa được vô hiệu bằng tiền tố '")
        self.assertIn("\"'=cmd", ra)


# ================================================================= C. Phê duyệt
class C_PheDuyet(unittest.TestCase):
    def _dot_khop(self, t, u, ca, cod=200_000, phi=25_000, ky="2027-05"):
        don = _tao_don(t, u, cod=cod, phi=phi, ca_id=ca)
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        tai_chinh.ghi_phi(t, don, "bao_gia", phi, "hang", "báo giá khi tạo đơn")
        kq = doi_soat.nap_bang_ke(t, u, "vtp", f"bk-{ky}-{don}.csv",
                                  _csv_vtp([(g["ma_van_don"], g["ma_don"], str(cod), str(phi), ky)]),
                                  ky_thanh_toan=ky, carrier_account_id=ca)
        doi_soat.doi_chieu(t, kq["dot_id"])
        return don, kq["dot_id"]

    def test_c1_nap_file_KHONG_tu_ap_so_cua_hang_vao_so(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-05")
        self.assertIsNone(tai_chinh.cod_cua_don(t, don),
                          "nạp file đã tự mở sổ COD và áp số — đúng cái §18 cấm")
        self.assertEqual(csdl.mot("SELECT trang_thai FROM ds_dot WHERE id=?", (dot,))["trang_thai"],
                         "CHO_DUYET")

    def test_c2_duyet_moi_ap_vao_so(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-06")
        pt_truoc = tai_chinh.cong_no(t)["tong_phai_thu"]
        kq = doi_soat.duyet_dot(t, u, dot)
        self.assertEqual(kq["da_ap"], 1, f"lỗi: {kq['loi']}")
        c = tai_chinh.cod_cua_don(t, don)
        self.assertEqual(c["trang_thai"], "COD_RECONCILED")
        self.assertEqual(c["so_tien_doi_soat"], 200_000)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], pt_truoc + 200_000)
        p = tai_chinh.phi_cua_don(t, don)
        self.assertEqual(p["tong_theo_loai"]["thuc_te_hang"], 25_000)
        for k in p["khoan"]:
            if k["loai"] == "thuc_te_hang":
                self.assertEqual(k["nguon"], "hang", "phí hãng tính phải mang NGUỒN 'hang'")
                self.assertIn("đợt đối soát", k["can_cu"])
        # Công nợ dựng lại từ bút toán vẫn khớp
        self.assertTrue(tai_chinh.tong_so_tai_chinh(t)["cong_no_khop"])

    def test_c3_vai_tro_chi_xem_khong_duyet_duoc(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-07")
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            doi_soat.duyet_dot(t, NEN["v1"], dot)
        self.assertEqual(e.exception.ma, 403)
        self.assertIsNone(tai_chinh.cod_cua_don(t, don))

    def test_c4_duyet_hai_lan_bi_chan(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-08")
        doi_soat.duyet_dot(t, u, dot)
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            doi_soat.duyet_dot(t, u, dot)
        self.assertIn("không áp lần hai", str(e.exception))

    def test_c5_duyet_DONG_THOI_chi_mot_luot_ap(self):
        """Tám thread cùng duyệt một đợt. Chỉ MỘT được áp, và số tiền vào sổ đúng một lần."""
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, cod=333_000, ky="2027-09")
        pt_truoc = tai_chinh.cong_no(t)["tong_phai_thu"]
        thang, thua = [], []
        rao = threading.Barrier(8)

        def chay():
            rao.wait()
            try:
                thang.append(doi_soat.duyet_dot(t, u, dot))
            except Exception as e:      # noqa: BLE001 — thu lại để đếm
                thua.append(str(e))
            finally:
                csdl.dong()

        ths = [threading.Thread(target=chay) for _ in range(8)]
        for x in ths:
            x.start()
        for x in ths:
            x.join()
        self.assertEqual(len(thang), 1, f"{len(thang)} lượt cùng áp — tiền vào sổ nhiều lần")
        self.assertEqual(len(thua), 7)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], pt_truoc + 333_000)
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM tc_but_toan WHERE tenant_id=? AND don_id=?"
                     " AND loai='cod_hang_bao_thu'", (t, don))["c"], 1,
            "có hơn một bút toán 'hãng báo thu' cho cùng một đơn")

    def test_c6_dong_LECH_khong_tu_ap(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don = _tao_don(t, u, cod=100_000, phi=20_000, ca_id=ca)
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        kq = doi_soat.nap_bang_ke(t, u, "vtp", f"bk-c6-{don}.csv",
                                  _csv_vtp([(g["ma_van_don"], g["ma_don"], "88000", "", "2027-10")]),
                                  ky_thanh_toan="2027-10", carrier_account_id=ca)
        doi_soat.doi_chieu(t, kq["dot_id"])
        r = doi_soat.duyet_dot(t, u, kq["dot_id"])
        self.assertEqual(r["da_ap"], 0, "dòng LỆCH đã bị áp tự động — chọn tin hãng hộ người")
        self.assertIsNone(tai_chinh.cod_cua_don(t, don))
        self.assertEqual(len(doi_soat.chenh_lech_cua_dot(t, kq["dot_id"], "cod_lech")), 1)

    def test_c7_tu_choi_dot_phai_co_ly_do_va_khong_ap_gi(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-11")
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.tu_choi_dot(t, u, dot, "")
        self.assertTrue(doi_soat.tu_choi_dot(t, u, dot, "nạp nhầm file của hãng khác"))
        self.assertIsNone(tai_chinh.cod_cua_don(t, don))
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.duyet_dot(t, u, dot)

    def test_c8_doi_chieu_hai_lan_bi_chan(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don, dot = self._dot_khop(t, u, ca, ky="2027-12")
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            doi_soat.doi_chieu(t, dot)


# ================================================================= D. Idempotent
class D_Idempotent(unittest.TestCase):
    def test_d1_nap_lai_CUNG_FILE_khong_nhan_doi_so(self):
        """Phép đo thật: nạp → duyệt → nạp LẠI đúng file đó → duyệt. Tiền trong sổ không đổi."""
        t, u, ca = NEN["t2"], NEN["u2"], NEN["ca2"]
        don = _tao_don(t, u, cod=500_000, phi=40_000, ca_id=ca)
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        tai_chinh.ghi_phi(t, don, "bao_gia", 40_000, "hang", "báo giá")
        du = _csv_vtp([(g["ma_van_don"], g["ma_don"], "500000", "40000", "2028-01")])

        k1 = doi_soat.nap_bang_ke(t, u, "vtp", "lap.csv", du, ky_thanh_toan="2028-01",
                                  carrier_account_id=ca)
        doi_soat.doi_chieu(t, k1["dot_id"])
        doi_soat.duyet_dot(t, u, k1["dot_id"])
        pt = tai_chinh.cong_no(t)["tong_phai_thu"]
        so_bt = csdl.mot("SELECT COUNT(*) c FROM tc_but_toan WHERE tenant_id=?", (t,))["c"]

        k2 = doi_soat.nap_bang_ke(t, u, "vtp", "lap.csv", du, ky_thanh_toan="2028-01",
                                  carrier_account_id=ca)
        self.assertEqual(k2["so_nap"], 0, "nạp lại cùng file mà vẫn tạo dòng mới")
        self.assertEqual(k2["so_trung"], 1)
        doi_soat.doi_chieu(t, k2["dot_id"])
        r = doi_soat.duyet_dot(t, u, k2["dot_id"])
        self.assertEqual(r["da_ap"], 0)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], pt,
                         "nạp lại cùng file đã nhân đôi công nợ")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM tc_but_toan WHERE tenant_id=?",
                                  (t,))["c"], so_bt, "nạp lại cùng file đã sinh bút toán mới")
        self.assertEqual(tai_chinh.phi_cua_don(t, don)["tong_theo_loai"]["thuc_te_hang"], 40_000)

    def test_d2_chot_idempotent_la_RANG_BUOC_CSDL_khong_phai_phep_kiem_trong_ma(self):
        """Kiểm chứng của kiểm chứng: đọc schema THẬT và đòi có đúng ràng buộc UNIQUE đó."""
        kn = csdl.mo()
        ds = [r[1] for r in kn.execute("PRAGMA index_list(ds_dong)")]
        thay = False
        for ten in ds:
            cot = [r[2] for r in kn.execute(f"PRAGMA index_info({ten})")]
            if cot == ["tenant_id", "hang", "ky_thanh_toan", "van_tay_dong"]:
                thay = True
        self.assertTrue(thay, f"không thấy UNIQUE(tenant_id,hang,ky_thanh_toan,van_tay_dong);"
                              f" chỉ mục đang có: {ds}")
        # Và đòi CSDL thật ném lỗi khi chèn trùng (không chỉ tin PRAGMA)
        t, u = NEN["t2"], NEN["u2"]
        dot = csdl.ghi("INSERT INTO ds_dot (tenant_id, hang, ten_file, loai_file, van_tay_file,"
                       " ky_thanh_toan, tao_luc) VALUES (?, 'vtp', 'x.csv', 'csv', 'vt', 'K', ?)",
                       (t, csdl.bay_gio())).lastrowid
        for _ in range(1):
            csdl.ghi("INSERT INTO ds_dong (dot_id, tenant_id, hang, stt, ky_thanh_toan,"
                     " tho_json, van_tay_dong) VALUES (?,?, 'vtp', 1, 'K', '{}', 'VT-D2')",
                     (dot, t))
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            csdl.ghi("INSERT INTO ds_dong (dot_id, tenant_id, hang, stt, ky_thanh_toan,"
                     " tho_json, van_tay_dong) VALUES (?,?, 'vtp', 2, 'K', '{}', 'VT-D2')",
                     (dot, t))

    def test_d3_cung_van_don_KY_KHAC_thi_KHONG_la_trung(self):
        """Kỳ khác là giao dịch khác (ví dụ truy thu phí tháng sau) — không được coi là trùng."""
        t, u, ca = NEN["t2"], NEN["u2"], NEN["ca2"]
        don = _tao_don(t, u, cod=80_000, phi=10_000, ca_id=ca)
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        for ky in ("2028-02", "2028-03"):
            kq = doi_soat.nap_bang_ke(t, u, "vtp", f"ky-{ky}.csv",
                                      _csv_vtp([(g["ma_van_don"], g["ma_don"], "80000",
                                                 "10000", ky)]),
                                      ky_thanh_toan=ky, carrier_account_id=ca)
            self.assertEqual(kq["so_nap"], 1, f"kỳ {ky} bị coi là trùng")


# ================================================================= E. Cách ly tenant
class E_CachLy(unittest.TestCase):
    def test_e1_tenant_khac_khong_thay_khong_duyet_duoc_dot(self):
        tA, uA, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        tB, uB = NEN["t2"], NEN["u2"]
        don = _tao_don(tA, uA, cod=120_000, phi=15_000, ca_id=ca)
        g = csdl.mot("SELECT ma_don, ma_van_don FROM don_hang WHERE id=?", (don,))
        kq = doi_soat.nap_bang_ke(tA, uA, "vtp", "bk-e1.csv",
                                  _csv_vtp([(g["ma_van_don"], g["ma_don"], "120000",
                                             "15000", "2029-01")]),
                                  ky_thanh_toan="2029-01", carrier_account_id=ca)
        doi_soat.doi_chieu(tA, kq["dot_id"])
        for ham, args in ((doi_soat.duyet_dot, (tB, uB, kq["dot_id"])),
                          (doi_soat.bang_ke_cua_dot, (tB, kq["dot_id"])),
                          (doi_soat.doi_chieu, (tB, kq["dot_id"]))):
            with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
                ham(*args)
            self.assertEqual(e.exception.ma, 404, f"{ham.__name__} rò rỉ đợt của tenant khác")
        self.assertNotIn(kq["dot_id"], {d["id"] for d in doi_soat.danh_sach_dot(tB, 10_000)})
        self.assertIn(kq["dot_id"], {d["id"] for d in doi_soat.danh_sach_dot(tA, 10_000)})

    def test_e2_ma_van_don_cua_tenant_khac_KHONG_tu_khop(self):
        """Hai tenant trùng mã vận đơn: bảng kê của A không được khớp vào đơn của B."""
        tA, uA, caA = NEN["t1"], NEN["u1"], NEN["ca1"]
        tB, uB, caB = NEN["t2"], NEN["u2"], NEN["ca2"]
        mvd = "VD-TRUNG-" + os.urandom(3).hex()
        donA = _tao_don(tA, uA, cod=111_000, phi=10_000, ca_id=caA, mvd=mvd)
        donB = _tao_don(tB, uB, cod=222_000, phi=10_000, ca_id=caB, mvd=mvd)
        kq = doi_soat.nap_bang_ke(tA, uA, "vtp", "bk-e2.csv",
                                  _csv_vtp([(mvd, "", "111000", "10000", "2029-02")]),
                                  ky_thanh_toan="2029-02", carrier_account_id=caA)
        doi_soat.doi_chieu(tA, kq["dot_id"])
        d = csdl.nhieu("SELECT don_id FROM ds_dong WHERE dot_id=?", (kq["dot_id"],))[0]
        self.assertEqual(d["don_id"], donA, "khớp sang đơn của tenant khác")
        doi_soat.duyet_dot(tA, uA, kq["dot_id"])
        self.assertIsNone(tai_chinh.cod_cua_don(tB, donB), "sổ COD của tenant B bị đụng")


if __name__ == "__main__":
    unittest.main(verbosity=2)
