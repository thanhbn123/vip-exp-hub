# Ranh giới giao dịch + ngữ nghĩa trigger/rollback (chỉ thị G12 mục 5B).
#
# Bộ này khoá lại HAI LỖI TIỀN đã đo được thật ngày 15/10/2026, và ghi ra ngữ nghĩa
# SQLite mà mã phải sống chung — nhất là điều dễ vấp nhất: `RAISE(ABORT)` huỷ CÂU, không
# huỷ GIAO DỊCH. Ai đọc "trigger chặn sửa sổ" mà tưởng cả giao dịch bị huỷ sẽ viết ra
# đúng loại lỗi mà ca b3 dưới đây mô tả.
import os
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_TM = tempfile.mkdtemp(prefix="vh-giaodich-")
import cau_hinh                                                          # noqa: E402
cau_hinh.THU_MUC_DU_LIEU = _TM
cau_hinh.DUONG_DAN_CSDL = os.path.join(_TM, "hub.db")
import csdl                                                             # noqa: E402
import migrate                                                          # noqa: E402
import tai_chinh                                                        # noqa: E402


def setUpModule():
    migrate.chay(im_lang=True)
    tai_chinh.quen_cache_bang()
    tai_chinh._dam_bao_bang()
    csdl.ghi("INSERT OR IGNORE INTO tenants (id,ten,goi_id,tao_luc) VALUES (1,'T','free',?)",
             (csdl.bay_gio(),))
    csdl.ghi("CREATE TABLE IF NOT EXISTS _thu_gd (x INTEGER)")


def _dem(bang="_thu_gd"):
    return csdl.mot(f"SELECT COUNT(*) c FROM {bang}")["c"]


# =========================================================== A. giao_dich() cơ bản
class A_GiaoDich(unittest.TestCase):

    def setUp(self):
        csdl.ghi("DELETE FROM _thu_gd")

    def test_a1_vao_het_khi_khong_loi(self):
        with csdl.giao_dich():
            csdl.ghi("INSERT INTO _thu_gd VALUES (1)")
            csdl.ghi("INSERT INTO _thu_gd VALUES (2)")
        self.assertEqual(_dem(), 2)

    def test_a2_khong_cau_nao_vao_khi_co_loi(self):
        with self.assertRaises(RuntimeError):
            with csdl.giao_dich():
                csdl.ghi("INSERT INTO _thu_gd VALUES (1)")
                raise RuntimeError("hỏng giữa chừng")
        self.assertEqual(_dem(), 0, "câu trước chỗ hỏng vẫn còn — giao dịch không lùi")

    def test_a3_benh_that_su_doc_duoc_tu_ket_noi_khac(self):
        """Lùi/chốt phải THẬT trên đĩa, không phải chỉ đúng trong bộ nhớ kết nối này.

        Đo bằng một kết nối THỨ HAI: `csdl.mot()` dùng chính kết nối vừa ghi, nên nó cũng
        thấy dữ liệu CHƯA commit. Tin nó là tự kiểm chứng bằng chính thứ cần kiểm (§12.1).
        """
        with csdl.giao_dich():
            csdl.ghi("INSERT INTO _thu_gd VALUES (7)")
        kn2 = csdl.ket_noi()
        try:
            self.assertEqual(kn2.execute("SELECT COUNT(*) FROM _thu_gd").fetchone()[0], 1)
        finally:
            kn2.close()

    def test_a4_long_nhau_ngoai_giu_trong_bo(self):
        with csdl.giao_dich():
            csdl.ghi("INSERT INTO _thu_gd VALUES (10)")
            try:
                with csdl.giao_dich():
                    csdl.ghi("INSERT INTO _thu_gd VALUES (20)")
                    raise ValueError("tầng trong hỏng")
            except ValueError:
                pass
            csdl.ghi("INSERT INTO _thu_gd VALUES (30)")
        self.assertEqual(sorted(r[0] for r in csdl.nhieu("SELECT x FROM _thu_gd")), [10, 30],
                         "tầng trong phải bị bỏ mà không kéo theo tầng ngoài")

    def test_a5_long_nhau_trong_hong_thi_ngoai_cung_hong(self):
        with self.assertRaises(ValueError):
            with csdl.giao_dich():
                csdl.ghi("INSERT INTO _thu_gd VALUES (10)")
                with csdl.giao_dich():
                    csdl.ghi("INSERT INTO _thu_gd VALUES (20)")
                    raise ValueError("không bắt")
        self.assertEqual(_dem(), 0)

    def test_a6_ghi_khong_tu_commit_khi_dang_trong_giao_dich(self):
        """Mấu chốt kỹ thuật: `csdl.ghi()` commit từng câu. Trong giao dịch thì KHÔNG được."""
        with csdl.giao_dich():
            csdl.ghi("INSERT INTO _thu_gd VALUES (99)")
            kn2 = csdl.ket_noi()
            try:
                thay = kn2.execute("SELECT COUNT(*) FROM _thu_gd").fetchone()[0]
            finally:
                kn2.close()
            self.assertEqual(thay, 0, "kết nối khác đã thấy dòng → ghi() đã commit sớm")
        self.assertEqual(_dem(), 1)

    def test_a7_bac_long_ve_0_sau_khi_hong(self):
        """Quên trả bậc là mọi lượt ghi SAU đó không bao giờ commit — hỏng im lặng."""
        try:
            with csdl.giao_dich():
                raise RuntimeError("x")
        except RuntimeError:
            pass
        self.assertEqual(getattr(csdl._local, "sau_giao_dich", 0), 0)
        csdl.ghi("INSERT INTO _thu_gd VALUES (5)")
        kn2 = csdl.ket_noi()
        try:
            self.assertEqual(kn2.execute("SELECT COUNT(*) FROM _thu_gd").fetchone()[0], 1,
                             "ghi() sau giao dịch hỏng không còn tự commit")
        finally:
            kn2.close()


# ================================================= B. ngữ nghĩa trigger (khác biệt THẬT)
class B_NguNghiaTrigger(unittest.TestCase):
    """`RAISE(ABORT)` của SQLite huỷ CÂU, không huỷ GIAO DỊCH. PostgreSQL thì ngược lại."""

    def setUp(self):
        csdl.ghi("DELETE FROM _thu_gd")

    def test_b1_trigger_bat_bien_van_chan_sua_but_toan(self):
        bt = tai_chinh.ghi_but_toan(1, "cod_hang_bao_thu", 1000, "nguoi", "ca b1")
        with self.assertRaises(csdl.LoiToanVen):
            csdl.ghi("UPDATE tc_but_toan SET so_tien_dong=2000 WHERE id=?", (bt,))
        with self.assertRaises(csdl.LoiToanVen):
            csdl.ghi("DELETE FROM tc_but_toan WHERE id=?", (bt,))
        self.assertEqual(
            csdl.mot("SELECT so_tien_dong s FROM tc_but_toan WHERE id=?", (bt,))["s"], 1000)

    def test_b2_khong_bo_giao_dich_thi_cau_SAU_trigger_van_vao(self):
        """Ghi ra ĐIỂM VẤP, không phải ghi ra cái đúng: đây là hành vi SQLite phải sống chung.

        Bắt `LoiToanVen` rồi ĐI TIẾP trong cùng giao dịch thì câu sau VẪN commit. Ai tưởng
        'trigger chặn nên cả giao dịch hỏng' sẽ viết đúng loại lỗi này.
        """
        bt = tai_chinh.ghi_but_toan(1, "cod_hang_bao_thu", 1000, "nguoi", "ca b2")
        with csdl.giao_dich():
            csdl.ghi("INSERT INTO _thu_gd VALUES (1)")
            try:
                csdl.ghi("UPDATE tc_but_toan SET so_tien_dong=9 WHERE id=?", (bt,))
            except csdl.LoiToanVen:
                pass            # ← CỐ Ý nuốt: mô phỏng mã nuốt lỗi rồi đi tiếp
            csdl.ghi("INSERT INTO _thu_gd VALUES (2)")
        self.assertEqual(_dem(), 2, "SQLite: RAISE(ABORT) chỉ huỷ CÂU — hai dòng kia vẫn vào")

    def test_b3_khong_nuot_thi_giao_dich_lui_sach(self):
        """Cách dùng ĐÚNG: để lỗi trigger nổ ra ngoài thì `giao_dich()` cuốn sạch."""
        bt = tai_chinh.ghi_but_toan(1, "cod_hang_bao_thu", 1000, "nguoi", "ca b3")
        with self.assertRaises(csdl.LoiToanVen):
            with csdl.giao_dich():
                csdl.ghi("INSERT INTO _thu_gd VALUES (1)")
                csdl.ghi("UPDATE tc_but_toan SET so_tien_dong=9 WHERE id=?", (bt,))
        self.assertEqual(_dem(), 0, "câu trước trigger phải bị cuốn theo")


# ============================================== C. hai lỗi tiền đã đo — khoá lại
class C_HaiLoiTienDaDo(unittest.TestCase):

    def test_c1_but_toan_va_cong_no_cung_vao_hoac_cung_khong(self):
        """Lỗi 1 (đo 15/10/2026): bút toán 777.000đ vào sổ mà công nợ đứng yên."""
        def tong():
            b = csdl.mot("SELECT COALESCE(SUM(so_tien_dong),0) s FROM tc_but_toan"
                         " WHERE tenant_id=1 AND loai='cod_hang_bao_thu'")["s"]
            c = csdl.mot("SELECT COALESCE(SUM(so_du_dong),0) s FROM tc_cong_no"
                         " WHERE tenant_id=1 AND so='phai_thu'")["s"]
            return b, c
        b0, c0 = tong()
        goc = tai_chinh._cap_nhat_cong_no
        tai_chinh._cap_nhat_cong_no = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("ép bước công nợ hỏng"))
        try:
            with self.assertRaises(RuntimeError):
                tai_chinh.ghi_but_toan(1, "cod_hang_bao_thu", 777000, "nguoi", "ca c1")
        finally:
            tai_chinh._cap_nhat_cong_no = goc
        b1, c1 = tong()
        self.assertEqual((b1, c1), (b0, c0),
                         f"bút toán mồ côi: sổ {b0}→{b1} mà công nợ {c0}→{c1}")

    def test_c2_dot_thanh_toan_khong_de_lai_dong_mo_coi(self):
        """Lỗi 2 (đo 15/10/2026): trả quá tay bị từ chối nhưng để lại dòng 90.000đ kẹt."""
        import thu_tai_chinh as T
        # Dựng nền của chính bộ thử tài chính thay vì chép lại cách tạo tenant/đơn/COD:
        # chép lại là có hai cách dựng nền, và hai cách sẽ lệch nhau lúc nào không ai biết.
        if T.NEN is None:
            T.setUpModule()
        ca = T.D_ThanhToan("test_d1_thanh_toan_TRUNG_bi_chan_o_tang_CSDL")
        t, u, don = ca._san_sang(100_000)
        dotA = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"GD-A-{don}", 100_000)
        tai_chinh.ghi_nhan_thanh_toan(t, u, dotA, don, 50_000)
        dotB = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"GD-B-{don}", 90_000)
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_nhan_thanh_toan(t, u, dotB, don, 90_000)
        dong = csdl.nhieu("SELECT dot_id, so_tien_dong FROM tc_dot_tt_dong WHERE don_id=?", (don,))
        tong_dong = sum(r["so_tien_dong"] for r in dong)
        da_tt = tai_chinh.cod_cua_don(t, don)["so_tien_da_tt"]
        self.assertEqual(tong_dong, da_tt,
                         f"đợt ghi tổng {tong_dong} mà tc_cod ghi đã trả {da_tt}")
        self.assertEqual(len(dong), 1, f"còn dòng mồ côi: {[(r['dot_id'], r['so_tien_dong']) for r in dong]}")

    def test_c3_cong_no_luu_khop_cong_no_dung_lai(self):
        """Nghiệm thu bằng hàm dựng lại từ bút toán — độc lập với bảng tổng hợp (§12.1)."""
        luu = tai_chinh.cong_no(1)
        dung_lai = tai_chinh.tinh_lai_cong_no(1)
        self.assertEqual(luu["tong_phai_thu"], dung_lai["tong_phai_thu"])
        self.assertEqual(luu["tong_phai_tra"], dung_lai["tong_phai_tra"])


if __name__ == "__main__":
    print("[giao-dich] PHẠM VI: MỘT tiến trình, SQLite 3.51.0, py 3.9.6.")
    print("            NGOÀI: nhiều tiến trình · PostgreSQL · máy chủ thật.")
    unittest.main(verbosity=1)
