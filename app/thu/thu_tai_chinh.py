# Bộ thử TÀI CHÍNH G07 (sổ COD · phí · đợt thanh toán · công nợ · điều chỉnh · nhật ký).
# Chạy: python3 app/thu/thu_tai_chinh.py
#
# Nguyên tắc (CLAUDE.md §12.1): mỗi khẳng định do MỘT phép đo thật tạo ra.
#   - "Bút toán bất biến" đo bằng cách THỬ `UPDATE`/`DELETE` thật và đòi CSDL ném lỗi,
#     không bằng đọc comment trong mã.
#   - "An toàn đồng thời" đo bằng NHIỀU THREAD thật đua nhau, không bằng thấy có câu UPDATE.
#   - "Giao thành công không làm COD settled" đo bằng một đơn `giao_thanh_cong` thật rồi đòi
#     COD vẫn chưa settled, không bằng đọc tài liệu.
#   - Dữ liệu mẫu dựng theo cột THẬT của `don_hang` (đã đọc `PRAGMA table_info` trước khi
#     viết file này), không theo giả định.
import os
import sqlite3
import sys
import tempfile
import threading
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-taichinh-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl        # noqa: E402
import don_hang    # noqa: E402
import quyen       # noqa: E402
import tai_chinh   # noqa: E402


# ---------------------------------------------------------------- khuôn dữ liệu
def _dung_nen():
    """Dựng tenant/user/tài khoản hãng tối thiểu. Trả dict các id."""
    quyen.seed()
    csdl.ghi("INSERT OR IGNORE INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,"
             "han_muc_ai_thang,so_nhan_vien,so_tai_khoan_hang)"
             " VALUES ('basic','Cơ bản',0,100000,1000,50,10)")
    csdl.ghi("INSERT OR IGNORE INTO carrier_providers (ma, ten, capabilities_json, cap_nhat_luc)"
             " VALUES ('vtp','Viettel Post','{}',?)", (csdl.bay_gio(),))
    csdl.ghi("INSERT OR IGNORE INTO carrier_providers (ma, ten, capabilities_json, cap_nhat_luc)"
             " VALUES ('jt','J&T','{}',?)", (csdl.bay_gio(),))
    ra = {}
    for i, code in enumerate(("tA", "tB"), start=1):
        tid = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                       (code + os.urandom(3).hex(), "Tenant " + code, "basic",
                        csdl.bay_gio())).lastrowid
        uid_chu = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                           " VALUES (?,?,?,?)",
                           (f"chu-{code}-{os.urandom(3).hex()}", "x", "Chủ " + code,
                            csdl.bay_gio())).lastrowid
        uid_xem = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                           " VALUES (?,?,?,?)",
                           (f"xem-{code}-{os.urandom(3).hex()}", "x", "Xem " + code,
                            csdl.bay_gio())).lastrowid
        csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                 " VALUES (?,?, 'TENANT_OWNER', ?)", (uid_chu, tid, csdl.bay_gio()))
        csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                 " VALUES (?,?, 'TENANT_VIEWER', ?)", (uid_xem, tid, csdl.bay_gio()))
        ca = csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, credentials_ma_hoa,"
                      " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
                      " VALUES (?, 'vtp', 'VTP mock', 'x', '', ?, 'x', ?)",
                      (tid, f"wh-{code}-{os.urandom(4).hex()}", csdl.bay_gio())).lastrowid
        ra[f"t{i}"] = tid
        ra[f"u{i}"] = uid_chu
        ra[f"v{i}"] = uid_xem
        ra[f"ca{i}"] = ca
    return ra


_SO_DON = [0]


def _tao_don(tenant_id, nguoi_tao, cod=150_000, phi=30_000, ca_id=None, mvd=None,
             trang_thai="da_gui", trang_thai_giao=None):
    """Chèn đơn trực tiếp (bỏ qua tầng quyền) — bộ thử này thử TÀI CHÍNH, không thử tạo đơn."""
    _SO_DON[0] += 1
    n = _SO_DON[0]
    return csdl.ghi(
        "INSERT INTO don_hang (tenant_id, ma_don, nguoi_gui_ten, nguoi_gui_sdt, nguoi_gui_dia_chi,"
        " nguoi_nhan_ten, nguoi_nhan_sdt, nguoi_nhan_dia_chi, hang_hoa, khoi_luong_gram, cod,"
        " gia_tri_khai, phi_van_chuyen, carrier_account_id, ma_van_don, trang_thai,"
        " trang_thai_giao, nguoi_tao, tao_luc, cap_nhat_luc)"
        " VALUES (?,?, 'A','0900000001','Đ/c gửi', 'B','0900000002','Đ/c nhận', 'Hàng', 1000,"
        " ?,0,?,?,?,?,?,?,?,?)",
        (tenant_id, f"D{tenant_id}-{n:05d}", cod, phi, ca_id, mvd or f"VD{tenant_id}{n:05d}",
         trang_thai, trang_thai_giao, nguoi_tao, csdl.bay_gio(), csdl.bay_gio())).lastrowid


NEN = None


def setUpModule():
    global NEN
    csdl.mo()
    tai_chinh._dam_bao_bang()
    NEN = _dung_nen()


# ================================================================= A. Tiền
class A_Tien(unittest.TestCase):
    """§16: tiền là `INTEGER` đồng. Không float, không cắt cụt im lặng."""

    def test_a1_chan_phan_thap_phan_khong_cat_cut(self):
        for xau in ("150000.7", 150000.7, "1.5"):
            with self.assertRaises(tai_chinh.LoiTaiChinh, msg=f"{xau!r} phải bị CHẶN"):
                tai_chinh.so_tien(xau, "COD")
        # Phần thập phân .00 là cách viết khác của số nguyên — cho qua, không mất đồng nào
        self.assertEqual(tai_chinh.so_tien("150000.00", "COD"), 150000)
        self.assertEqual(tai_chinh.so_tien(150000.0, "COD"), 150000)

    def test_a2_khong_cot_tien_nao_la_real_trong_DDL(self):
        """Đo trên SCHEMA THẬT trong CSDL, không đọc chuỗi DDL."""
        kn = csdl.mo()
        bang = [r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND (name LIKE 'tc_%' OR name LIKE 'ds_%')")]
        self.assertGreaterEqual(len(bang), 13, f"thiếu bảng G07, chỉ thấy {bang}")
        for b in bang:
            for c in kn.execute(f"PRAGMA table_info({b})"):
                ten, kieu = c[1], (c[2] or "").upper()
                self.assertNotIn("REAL", kieu, f"{b}.{ten} kiểu {kieu} — §16 cấm REAL")
                self.assertNotIn("FLOAT", kieu, f"{b}.{ten} kiểu {kieu} — §16 cấm FLOAT")
                if any(k in ten for k in ("so_tien", "so_du", "lech_dong", "cod_", "phi_")):
                    self.assertIn("INT", kieu, f"{b}.{ten} là cột tiền mà kiểu {kieu}")

    def test_a3_ti_le_luu_bang_diem_co_ban(self):
        import doi_soat
        self.assertIsInstance(doi_soat.NGUONG_LECH_BPS, int)
        self.assertEqual(doi_soat.NGUONG_LECH_BPS, 2000, "20% = 2000 điểm cơ bản")


# ================================================================= B. Bút toán bất biến
class B_ButToanBatBien(unittest.TestCase):
    """§17: bút toán không sửa, không xoá. Đo bằng cách THỬ sửa và đòi CSDL chặn."""

    def test_b1_UPDATE_bi_CSDL_chan(self):
        bt = tai_chinh.ghi_but_toan(NEN["t1"], "cod_hang_bao_thu", 100_000, "hang",
                                    "ca thử b1", carrier_account_id=NEN["ca1"])
        with self.assertRaises(sqlite3.IntegrityError) as c:
            csdl.ghi("UPDATE tc_but_toan SET so_tien_dong=1 WHERE id=?", (bt,))
        self.assertIn("bat bien", str(c.exception))
        r = csdl.mot("SELECT so_tien_dong FROM tc_but_toan WHERE id=?", (bt,))
        self.assertEqual(r["so_tien_dong"], 100_000, "số tiền đã bị đổi — trigger không chặn")

    def test_b2_DELETE_bi_CSDL_chan(self):
        bt = tai_chinh.ghi_but_toan(NEN["t1"], "phi_hang_tinh", 20_000, "hang", "ca thử b2")
        with self.assertRaises(sqlite3.IntegrityError):
            csdl.ghi("DELETE FROM tc_but_toan WHERE id=?", (bt,))
        self.assertIsNotNone(csdl.mot("SELECT 1 x FROM tc_but_toan WHERE id=?", (bt,)))

    def test_b3_sua_sai_bang_but_toan_dao(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        truoc = tai_chinh.cong_no(t)["tong_phai_thu"]
        bt = tai_chinh.ghi_but_toan(t, "cod_hang_bao_thu", 500_000, "hang", "nhập sai",
                                    carrier_account_id=ca)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], truoc + 500_000)
        dao = tai_chinh.dao_but_toan(t, bt, "nhập sai số, đảo lại", tao_boi=u)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], truoc,
                         "đảo xong công nợ phải về đúng số cũ")
        # Cả hai dòng còn nguyên — lịch sử dựng lại được
        self.assertIsNotNone(csdl.mot("SELECT 1 x FROM tc_but_toan WHERE id=?", (bt,)))
        self.assertEqual(csdl.mot("SELECT dao_cua FROM tc_but_toan WHERE id=?", (dao,))["dao_cua"], bt)
        # Đảo hai lần bị chặn ở tầng CSDL (UNIQUE), không phải bằng `if`
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.dao_but_toan(t, bt, "đảo lần hai")

    def test_b4_loai_but_toan_la_bi_tu_choi(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_but_toan(NEN["t1"], "loai_chua_ai_nghi_ra", 1000, "hang", "x")

    def test_b5_but_toan_phai_co_can_cu(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_but_toan(NEN["t1"], "phi_hang_tinh", 1000, "hang", "   ")

    def test_b6_nguon_phai_phan_biet_hang_nguoi_he_thong(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_but_toan(NEN["t1"], "phi_hang_tinh", 1000, "ai_do", "x")
        for ng in ("hang", "nguoi", "he_thong"):
            self.assertTrue(tai_chinh.ghi_but_toan(NEN["t1"], "phi_bao_gia", 1, ng, "ca thử b6"))


# ================================================================= C. Vòng đời COD
class C_VongDoiCOD(unittest.TestCase):
    def test_c1_sau_trang_thai_khong_gop(self):
        self.assertEqual(tai_chinh.TRANG_THAI_COD,
                         ("COD_EXPECTED", "COD_COLLECTED", "COD_RECONCILED", "COD_SETTLED",
                          "COD_DISPUTED", "COD_ADJUSTED"))
        self.assertEqual(len(set(tai_chinh.TRANG_THAI_COD)), 6)

    def test_c2_vong_doi_day_du_den_settled(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don = _tao_don(t, u, cod=200_000, ca_id=ca)
        c = tai_chinh.mo_so_cod(t, don)
        self.assertEqual(c["trang_thai"], "COD_EXPECTED")
        tai_chinh.chuyen_cod(t, don, "COD_COLLECTED", "hang", "hãng báo đã thu",
                             nguoi=u, so_tien_hang_bao=200_000)
        tai_chinh.chuyen_cod(t, don, "COD_RECONCILED", "nguoi", "duyệt đối soát", nguoi=u)
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-{don}", 200_000,
                                           carrier_account_id=ca)
        kq = tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 200_000)
        self.assertTrue(kq["du"])
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_SETTLED")
        # Lịch sử đủ 3 bước chuyển
        ls = tai_chinh.lich_su_cod(t, don)
        self.assertEqual([x["den"] for x in ls],
                         ["COD_COLLECTED", "COD_RECONCILED", "COD_SETTLED"])

    def test_c3_GIAO_THANH_CONG_KHONG_lam_COD_settled(self):
        """LUẬT QUAN TRỌNG NHẤT CỦA G07 (§18). Đơn giao xong mà chưa đối soát thì COD chưa về."""
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don = _tao_don(t, u, cod=300_000, ca_id=ca)
        tai_chinh.mo_so_cod(t, don)
        ap, ly_do = don_hang.ap_trang_thai_giao(t, don, "giao_thanh_cong", "ca thử c3")
        self.assertEqual(ap, 1, f"không áp được trạng thái giao: {ly_do}")
        self.assertEqual(csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?",
                                  (don,))["trang_thai_giao"], "giao_thanh_cong")
        c = tai_chinh.cod_cua_don(t, don)
        self.assertEqual(c["trang_thai"], "COD_EXPECTED",
                         "giao thành công đã tự đổi trạng thái COD — đúng cái §18 cấm")
        self.assertEqual(c["so_tien_da_tt"], 0)
        # Và không có cửa nào nhận tiền khi chưa đối soát
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-c3-{don}", 300_000)
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 300_000)
        self.assertIn("ĐỐI SOÁT", str(e.exception))
        # Tổng số tài chính cũng không được báo đồng nào đã thanh toán cho đơn này
        self.assertEqual(tai_chinh.tong_hop_cod(t)["theo_trang_thai"]["COD_SETTLED"],
                         csdl.mot("SELECT COUNT(*) c FROM tc_cod WHERE tenant_id=?"
                                  " AND trang_thai='COD_SETTLED'", (t,))["c"])

    def test_c4_chuyen_khong_hop_le_bi_chan(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=10_000, ca_id=NEN["ca1"])
        tai_chinh.mo_so_cod(t, don)
        # EXPECTED → RECONCILED là nhảy bước (chưa ai báo thu) → chặn
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.chuyen_cod(t, don, "COD_RECONCILED", "nguoi", "nhảy bước", nguoi=u)
        # COD_SETTLED không bao giờ đi qua chuyen_cod
        tai_chinh.chuyen_cod(t, don, "COD_COLLECTED", "hang", "hãng báo", nguoi=u,
                             so_tien_hang_bao=10_000)
        tai_chinh.chuyen_cod(t, don, "COD_RECONCILED", "nguoi", "chốt", nguoi=u)
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.chuyen_cod(t, don, "COD_SETTLED", "nguoi", "tự cho là đã trả", nguoi=u)
        self.assertIn("tiền thật", str(e.exception))

    def test_c5_tranh_chap_va_dieu_chinh_la_hai_trang_thai_rieng(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=50_000, ca_id=NEN["ca1"])
        tai_chinh.mo_so_cod(t, don)
        tai_chinh.chuyen_cod(t, don, "COD_DISPUTED", "nguoi", "khách nói chưa trả tiền",
                             nguoi=u, ly_do_tranh_chap="khách phủ nhận")
        c = tai_chinh.cod_cua_don(t, don)
        self.assertEqual(c["trang_thai"], "COD_DISPUTED")
        self.assertEqual(c["ly_do_tranh_chap"], "khách phủ nhận")
        tai_chinh.chuyen_cod(t, don, "COD_ADJUSTED", "nguoi", "chốt lại số sau tranh chấp",
                             nguoi=u, so_tien_hang_bao=40_000)
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_ADJUSTED")

    def test_c6_chuyen_cod_phai_co_can_cu(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, ca_id=NEN["ca1"])
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.chuyen_cod(t, don, "COD_COLLECTED", "hang", "", nguoi=u)


# ================================================================= D. Thanh toán
class D_ThanhToan(unittest.TestCase):
    def _san_sang(self, cod=100_000):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don = _tao_don(t, u, cod=cod, ca_id=ca)
        tai_chinh.mo_so_cod(t, don)
        tai_chinh.chuyen_cod(t, don, "COD_COLLECTED", "hang", "hãng báo thu", nguoi=u,
                             so_tien_hang_bao=cod)
        tai_chinh.chuyen_cod(t, don, "COD_RECONCILED", "nguoi", "chốt", nguoi=u)
        return t, u, don

    def test_d1_thanh_toan_TRUNG_bi_chan_o_tang_CSDL(self):
        """Trả lần hai trong CÙNG một đợt bị `UNIQUE(dot_id, don_id)` chặn.

        Cố ý trả MỘT PHẦN (50/100) để đơn còn ở `COD_RECONCILED`: nếu trả đủ thì đơn sang
        `COD_SETTLED` và lượt hai bị chốt chặn TRẠNG THÁI chặn trước, nên ca thử sẽ không
        còn đo được chốt chặn UNIQUE — đo sai cái mình tưởng đang đo (§12.1).
        """
        t, u, don = self._san_sang(100_000)
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d1-{don}", 100_000)
        tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 50_000)
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_RECONCILED")
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 50_000)
        self.assertIn("lần hai", str(e.exception))
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["so_tien_da_tt"], 50_000,
                         "cộng tiền hai lần cho một đơn trong một đợt")
        # Trả đủ ở đợt khác rồi trả thêm nữa → chốt chặn TRẠNG THÁI chặn (lớp thứ hai)
        dot2 = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d1b-{don}", 50_000)
        tai_chinh.ghi_nhan_thanh_toan(t, u, dot2, don, 50_000)
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_SETTLED")
        dot3 = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d1c-{don}", 50_000)
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_nhan_thanh_toan(t, u, dot3, don, 50_000)
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["so_tien_da_tt"], 100_000)

    def test_d2_dot_trung_ma_bi_chan(self):
        t, u = NEN["t1"], NEN["u1"]
        ma = f"DOT-d2-{os.urandom(3).hex()}"
        tai_chinh.tao_dot_thanh_toan(t, u, "vtp", ma, 1000)
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.tao_dot_thanh_toan(t, u, "vtp", ma, 1000)

    def test_d3_thanh_toan_MOT_PHAN_khong_thanh_settled(self):
        t, u, don = self._san_sang(100_000)
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d3a-{don}", 60_000)
        kq = tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 60_000)
        self.assertFalse(kq["du"])
        self.assertEqual(kq["con_lai"], 40_000)
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_RECONCILED",
                         "trả một phần đã bị coi là tất toán")
        # Trả nốt ở đợt sau → settled
        dot2 = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d3b-{don}", 40_000)
        kq2 = tai_chinh.ghi_nhan_thanh_toan(t, u, dot2, don, 40_000)
        self.assertTrue(kq2["du"])
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["trang_thai"], "COD_SETTLED")

    def test_d4_tra_vuot_so_phai_tra_bi_tu_choi(self):
        t, u, don = self._san_sang(100_000)
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d4-{don}", 100_000)
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.ghi_nhan_thanh_toan(t, u, dot, don, 100_001)
        self.assertIn("vượt", str(e.exception))
        self.assertEqual(tai_chinh.cod_cua_don(t, don)["so_tien_da_tt"], 0)

    def test_d5_tra_nhieu_lan_song_song_khong_vuot(self):
        """Mười thread cùng trả 30.000 cho đơn COD 100.000, mỗi lượt một đợt riêng.
        Tổng đã trả không được vượt 100.000 — điều kiện nằm trong WHERE nên CSDL tự so."""
        t, u, don = self._san_sang(100_000)
        dots = [tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d5-{don}-{i}", 30_000)
                for i in range(10)]
        ok, loi = [], []
        rao = threading.Barrier(10)

        def chay(i):
            rao.wait()
            try:
                tai_chinh.ghi_nhan_thanh_toan(t, u, dots[i], don, 30_000)
                ok.append(i)
            except Exception as e:      # noqa: BLE001 — thu lại để đếm, có ghi lý do
                loi.append(str(e))
            finally:
                csdl.dong()

        ths = [threading.Thread(target=chay, args=(i,)) for i in range(10)]
        for x in ths:
            x.start()
        for x in ths:
            x.join()
        da = tai_chinh.cod_cua_don(t, don)["so_tien_da_tt"]
        self.assertEqual(len(ok), 3, f"phải đúng 3 lượt 30.000 đi qua, thực {len(ok)}; lỗi={loi[:3]}")
        self.assertEqual(da, 90_000, f"tổng đã trả {da} — vượt hoặc mất tiền")
        self.assertLessEqual(da, 100_000)

    def test_d6_chot_dot_hai_lan_bi_chan(self):
        t, u = NEN["t1"], NEN["u1"]
        dot = tai_chinh.tao_dot_thanh_toan(t, u, "vtp", f"DOT-d6-{os.urandom(3).hex()}", 0)
        self.assertTrue(tai_chinh.dong_dot_thanh_toan(t, u, dot))
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.dong_dot_thanh_toan(t, u, dot)


# ================================================================= E. Phí
class E_Phi(unittest.TestCase):
    def test_e1_bay_loai_phi_moi_khoan_co_nguon_va_moc_thoi_gian(self):
        t, u, ca = NEN["t1"], NEN["u1"], NEN["ca1"]
        don = _tao_don(t, u, cod=0, phi=30_000, ca_id=ca)
        tai_chinh.ghi_phi(t, don, "bao_gia", 30_000, "hang", "hãng báo giá khi tạo đơn",
                          tao_boi=u, ghi_nhan_luc="2026-10-01 08:00:00+0700")
        tai_chinh.ghi_phi(t, don, "du_kien_thu_khach", 35_000, "nguoi", "giá bán cho khách",
                          tao_boi=u)
        tai_chinh.ghi_phi(t, don, "thuc_te_hang", 32_000, "hang", "bảng kê hãng", tao_boi=u)
        tai_chinh.ghi_phi(t, don, "phu_phi", 5_000, "hang", "phụ phí vùng xa", tao_boi=u)
        tai_chinh.ghi_phi(t, don, "hoan", 2_000, "hang", "hãng hoàn phí sai vùng", tao_boi=u)
        p = tai_chinh.phi_cua_don(t, don)
        self.assertEqual(p["tong_theo_loai"]["bao_gia"], 30_000)
        self.assertEqual(p["phi_thuc_te"], 32_000 + 5_000 - 2_000)
        self.assertEqual(p["lech_so_bao_gia"], 35_000 - 30_000)
        self.assertEqual(p["lech_so_thu_khach"], 35_000 - 35_000)
        for k in p["khoan"]:
            self.assertIn(k["nguon"], ("hang", "nguoi", "he_thong"), "khoản phí thiếu NGUỒN")
            self.assertTrue(k["ghi_nhan_luc"], "khoản phí thiếu THỜI ĐIỂM ghi nhận")
        self.assertEqual(p["khoan"][0]["ghi_nhan_luc"], "2026-10-01 08:00:00+0700",
                         "mốc của hãng bị thay bằng giờ hệ")

    def test_e2_phi_lech_hien_ra_duoc(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=0, phi=30_000, ca_id=NEN["ca1"])
        tai_chinh.ghi_phi(t, don, "bao_gia", 30_000, "hang", "báo giá")
        tai_chinh.ghi_phi(t, don, "thuc_te_hang", 45_000, "hang", "hãng tính thật")
        self.assertEqual(tai_chinh.phi_cua_don(t, don)["lech_so_bao_gia"], 15_000)

    def test_e3_loai_phi_la_bi_tu_choi(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_phi(NEN["t1"], None, "phi_la", 1000, "hang", "x")

    def test_e4_phi_am_phai_dung_loai_rieng(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.ghi_phi(NEN["t1"], None, "thuc_te_hang", -1000, "hang", "x")


# ================================================================= F. Điều chỉnh
class F_DieuChinh(unittest.TestCase):
    def test_f1_khong_ly_do_khong_dieu_chinh(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.dieu_chinh(NEN["t1"], NEN["u1"], "cod", 10_000, "  ")

    def test_f2_dieu_chinh_ghi_du_ly_do_nguoi_lich_su(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=100_000, ca_id=NEN["ca1"])
        truoc = tai_chinh.cong_no(t)["tong_phai_thu"]
        kq = tai_chinh.dieu_chinh(t, u, "cod", -20_000, "hãng làm mất 20k, trừ phải thu",
                                  don_id=don)
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], truoc - 20_000)
        ls = tai_chinh.lich_su_dieu_chinh(t)
        self.assertEqual(ls[0]["id"], kq["dieu_chinh_id"])
        self.assertEqual(ls[0]["nguoi"], u)
        self.assertEqual(ls[0]["so_tien_dong"], -20_000)
        self.assertIn("mất 20k", ls[0]["ly_do"])
        self.assertIsNotNone(ls[0]["but_toan_id"], "điều chỉnh không gắn bút toán nào")

    def test_f3_dieu_chinh_phi_vao_ca_so_phi(self):
        t, u = NEN["t1"], NEN["u1"]
        don = _tao_don(t, u, cod=0, ca_id=NEN["ca1"])
        tai_chinh.dieu_chinh(t, u, "phi", 7_000, "hãng truy thu phụ phí", don_id=don)
        p = tai_chinh.phi_cua_don(t, don)
        self.assertEqual(p["tong_theo_loai"]["dieu_chinh_tang"], 7_000)

    def test_f4_nguoi_khong_ton_tai_bi_chan(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.dieu_chinh(NEN["t1"], 99_999_999, "cod", 1000, "lý do", kiem_quyen=False)

    def test_f5_vai_tro_chi_xem_khong_dieu_chinh_duoc(self):
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.dieu_chinh(NEN["t1"], NEN["v1"], "cod", 1000, "thử quyền")
        self.assertEqual(e.exception.ma, 403)


# ================================================================= G. Nhật ký bất biến
class G_NhatKy(unittest.TestCase):
    def test_g1_moc_bam_lien_mach(self):
        t = NEN["t2"]
        for i in range(5):
            tai_chinh.ghi_nhat_ky(t, "ca_thu_g1", f"x:{i}", f"lần {i}")
        kq = tai_chinh.kiem_nhat_ky(t)
        self.assertTrue(kq["ok"], f"móc băm hỏng ở {kq['dong_hong']}")
        self.assertGreaterEqual(kq["so_dong"], 5)

    def test_g2_CSDL_chan_sua_va_xoa_nhat_ky(self):
        t = NEN["t2"]
        nid = tai_chinh.ghi_nhat_ky(t, "ca_thu_g2", "x:1", "nội dung gốc")
        with self.assertRaises(sqlite3.IntegrityError):
            csdl.ghi("UPDATE tc_nhat_ky SET chi_tiet='đã sửa' WHERE id=?", (nid,))
        with self.assertRaises(sqlite3.IntegrityError):
            csdl.ghi("DELETE FROM tc_nhat_ky WHERE id=?", (nid,))
        self.assertEqual(csdl.mot("SELECT chi_tiet FROM tc_nhat_ky WHERE id=?",
                                  (nid,))["chi_tiet"], "nội dung gốc")

    def test_g3_bam_phat_hien_sua_vong_qua_trigger(self):
        """Kiểm chứng của kiểm chứng: nếu ai đó gỡ trigger rồi sửa, móc băm vẫn tố giác."""
        t = NEN["t2"]
        tai_chinh.ghi_nhat_ky(t, "ca_thu_g3", "x:1", "gốc")
        nid = tai_chinh.ghi_nhat_ky(t, "ca_thu_g3", "x:2", "gốc 2")
        kn = csdl.mo()
        with csdl.khoa_ghi:
            kn.execute("DROP TRIGGER trg_tc_nhat_ky_cam_sua")
            kn.execute("UPDATE tc_nhat_ky SET chi_tiet='bị sửa ngầm' WHERE id=?", (nid,))
            kn.commit()
        try:
            kq = tai_chinh.kiem_nhat_ky(t)
            self.assertFalse(kq["ok"], "sửa ngầm mà kiem_nhat_ky vẫn báo ok")
            self.assertIn(nid, kq["dong_hong"])
        finally:
            with csdl.khoa_ghi:
                kn.execute("UPDATE tc_nhat_ky SET chi_tiet='gốc 2' WHERE id=?", (nid,))
                kn.executescript(
                    "CREATE TRIGGER IF NOT EXISTS trg_tc_nhat_ky_cam_sua BEFORE UPDATE"
                    " ON tc_nhat_ky BEGIN SELECT RAISE(ABORT,'tc_nhat_ky bat bien:"
                    " khong duoc sua'); END;")
                kn.commit()
        self.assertTrue(tai_chinh.kiem_nhat_ky(t)["ok"])


# ================================================================= H. Cách ly tenant
class H_CachLyTenant(unittest.TestCase):
    def test_h1_khong_ghi_but_toan_cho_don_tenant_khac(self):
        don_b = _tao_don(NEN["t2"], NEN["u2"], cod=10_000, ca_id=NEN["ca2"])
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.ghi_but_toan(NEN["t1"], "cod_hang_bao_thu", 10_000, "hang", "chéo tenant",
                                   don_id=don_b)
        self.assertEqual(e.exception.ma, 404)

    def test_h2_khong_mo_so_COD_cho_don_tenant_khac(self):
        don_b = _tao_don(NEN["t2"], NEN["u2"], ca_id=NEN["ca2"])
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.mo_so_cod(NEN["t1"], don_b)
        with self.assertRaises(tai_chinh.LoiTaiChinh):
            tai_chinh.chuyen_cod(NEN["t1"], don_b, "COD_COLLECTED", "hang", "chéo", nguoi=NEN["u1"])

    def test_h3_bang_COD_cua_A_khong_chua_don_cua_B(self):
        don_b = _tao_don(NEN["t2"], NEN["u2"], cod=777_777, ca_id=NEN["ca2"])
        tai_chinh.mo_so_cod(NEN["t2"], don_b)
        ids = {r["don_id"] for r in tai_chinh.bang_cod(NEN["t1"], gioi_han=10_000)}
        self.assertNotIn(don_b, ids)
        self.assertIn(don_b, {r["don_id"] for r in tai_chinh.bang_cod(NEN["t2"], gioi_han=10_000)})

    def test_h4_khong_doc_duoc_dot_thanh_toan_cua_tenant_khac(self):
        dot_b = tai_chinh.tao_dot_thanh_toan(NEN["t2"], NEN["u2"], "vtp",
                                             f"DOT-h4-{os.urandom(3).hex()}", 1000)
        don_a = _tao_don(NEN["t1"], NEN["u1"], ca_id=NEN["ca1"])
        with self.assertRaises(tai_chinh.LoiTaiChinh) as e:
            tai_chinh.ghi_nhan_thanh_toan(NEN["t1"], NEN["u1"], dot_b, don_a, 1000)
        self.assertEqual(e.exception.ma, 404)

    def test_h5_moi_cau_SQL_trong_hai_module_deu_co_tenant_id(self):
        """Phép đo có PHẠM VI HẸP, nói rõ ra: đếm các câu SELECT/UPDATE trên bảng `tc_*`/`ds_*`
        trong mã nguồn và đòi mỗi câu có `tenant_id`. Nó KHÔNG chứng minh cách ly khi chạy —
        ba ca h1..h4 làm việc đó. Nó chặn người sau thêm một câu quên tenant."""
        import re
        bo_qua_ok = 0
        for ten in ("tai_chinh.py", "doi_soat.py"):
            with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
                noi_dung = f.read()
            # NỐI các chuỗi literal liền nhau ("..." "..." và f"..." trên nhiều dòng) TRƯỚC khi
            # quét. Bản đầu của ca thử này quét từng literal rời nên đọc được một mảnh câu SQL
            # rồi báo thiếu `tenant_id` — chính là §12.1: công cụ tự mình giới hạn cũng phải nghi.
            noi_dung = re.sub(r'"\s*f?"', "", noi_dung)
            for m in re.finditer(r'"((?:SELECT|UPDATE|INSERT|DELETE)[^"]*)"', noi_dung):
                sql_up = " ".join(m.group(1).split())
                if not re.search(r"\b(tc_|ds_)", sql_up):
                    continue
                if sql_up.startswith("INSERT"):
                    continue          # INSERT truyền tenant_id ở cột, không ở WHERE
                if "tenant_id" in sql_up:
                    bo_qua_ok += 1
                    continue
                # Ngoại lệ ĐƯỢC KHAI (chỉ một): câu dò schema, không đọc dữ liệu tenant nào.
                self.assertTrue(
                    "sqlite_master" in sql_up,
                    f"{ten}: câu SQL trên bảng tài chính thiếu tenant_id → {sql_up[:120]}")
        self.assertGreater(bo_qua_ok, 20, "phép đo không quét được câu nào — bộ thử vô dụng")


# ================================================================= I. Tổng số tài chính
class I_TongSo(unittest.TestCase):
    def test_i1_cong_no_luu_khop_voi_cong_no_tinh_lai(self):
        """Bảng tổng hợp phải dựng lại được từ `tc_but_toan`. Lệch = bộ thử hỏng."""
        for t in (NEN["t1"], NEN["t2"]):
            a, b = tai_chinh.cong_no(t), tai_chinh.tinh_lai_cong_no(t)
            self.assertEqual(a["tong_phai_thu"], b["tong_phai_thu"],
                             f"tenant {t}: phải thu lưu {a['tong_phai_thu']} ≠ tính lại "
                             f"{b['tong_phai_thu']}")
            self.assertEqual(a["tong_phai_tra"], b["tong_phai_tra"])
            self.assertEqual(a["phai_thu"], b["phai_thu"], "số dư theo đối tác lệch")

    def test_i2_tong_so_tai_chinh_bao_dung_co_khop(self):
        ts = tai_chinh.tong_so_tai_chinh(NEN["t1"])
        self.assertTrue(ts["cong_no_khop"])
        self.assertTrue(ts["nhat_ky"]["ok"])
        for k in ("du_kien", "hang_bao_da_thu", "da_doi_soat", "da_thanh_toan", "con_cho",
                  "chenh_lech_hang_bao_vs_du_kien", "hoan_dieu_chinh"):
            self.assertIsInstance(ts["cod"][k], int, f"cod.{k} không phải số nguyên")

    def test_i3_con_cho_khong_lay_du_kien_lam_goc(self):
        """Đơn mới tạo (chưa ai thu) KHÔNG được cộng vào 'còn chờ hãng trả'."""
        t, u = NEN["t2"], NEN["u2"]
        truoc = tai_chinh.tong_hop_cod(t)["con_cho"]
        don = _tao_don(t, u, cod=1_000_000, ca_id=NEN["ca2"])
        tai_chinh.mo_so_cod(t, don)
        self.assertEqual(tai_chinh.tong_hop_cod(t)["con_cho"], truoc,
                         "COD dự kiến đã bị cộng vào 'còn chờ' — báo tiền không có thật")

    def test_i4_tong_cong_no_cong_dung_khong_mat_dong_nao(self):
        t, u, ca = NEN["t2"], NEN["u2"], NEN["ca2"]
        truoc = tai_chinh.cong_no(t)["tong_phai_thu"]
        tong = 0
        for so in (1, 7, 33, 999, 1_000_001):
            tai_chinh.ghi_but_toan(t, "cod_hang_bao_thu", so, "hang", "ca thử i4",
                                   carrier_account_id=ca)
            tong += so
        self.assertEqual(tai_chinh.cong_no(t)["tong_phai_thu"], truoc + tong)


# ================================================================= J. Giao diện tài chính
class J_GiaoDien(unittest.TestCase):
    """`admin/finance.js` là LOGIC THUẦN nên thử được bằng Node, không cần trình duyệt.

    PHẠM VI (§12.1 luật 3): tầng này phủ QUYẾT ĐỊNH của giao diện (nhãn nào, màn nào chờ
    backend, kiểm form). KHÔNG phủ DOM, CSS, bố cục, fetch thật — những thứ đó ở tầng 2/3
    của `thu_frontend/`, và file này KHÔNG chạy chúng.
    """

    GOC = os.path.dirname(GOC_APP)

    def _node(self, js):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            # Nói thẳng là KHÔNG đo được, không báo đạt. Máy không có Node thì ca này trống.
            self.skipTest("máy này không có `node` — KHÔNG đo được logic giao diện ở đây")
        mo = ('const F=require(' + repr(os.path.join(self.GOC, "admin", "finance.js")) + ');')
        kq = subprocess.run([node, "-e", mo + js], capture_output=True, text=True,
                            cwd=self.GOC, timeout=60)
        self.assertEqual(kq.returncode, 0, f"node báo lỗi:\n{kq.stderr}")
        return kq.stdout.strip()

    def test_j1_nap_duoc_va_co_dung_sau_trang_thai_COD(self):
        ra = self._node(
            'const k=Object.keys(F.TT_COD);'
            'if(k.length!==6) throw new Error("phải đúng 6 trạng thái COD, thấy "+k.length);'
            'for(const m of ["COD_EXPECTED","COD_COLLECTED","COD_RECONCILED","COD_SETTLED",'
            '"COD_DISPUTED","COD_ADJUSTED"]){const d=F.nhanCod(m);'
            'if(d.la) throw new Error(m+" giao diện không biết");'
            'if(!d.ten||d.ten===m) throw new Error(m+" thiếu tên tiếng Việt");}'
            'if(!F.nhanCod("COD_LA_LUNG").la) throw new Error("trạng thái lạ bị nuốt im lặng");'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j2_tien_so_nguyen_khong_lam_tron_ho(self):
        ra = self._node(
            'const t=F.dinhDangTien(1234567);'
            'if(t.van_ban!=="1.234.567\\u0111") throw new Error("định dạng sai: "+t.van_ban);'
            'for(const x of [1.5,"150000.7",0.1+0.2]){const d=F.dinhDangTien(x);'
            'if(!d.la) throw new Error(x+" đã được làm tròn im lặng");}'
            'if(F.dinhDangTien(0).van_ban!=="0\\u0111") throw new Error("0 đồng phải hiện 0đ");'
            'if(!F.dinhDangTien(null).trong) throw new Error("trống phải khác 0");'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j3_moi_man_khai_DUNG_tinh_trang_backend(self):
        """Mỗi màn phải khai ĐÚNG tình trạng backend — không phải khai "CHỜ BACKEND" mãi mãi.

        Bản đầu của ca này đòi **mọi** màn mang nhãn `CHỜ BACKEND`, đúng hiện trạng lúc AG-01
        viết (chưa có route G07 nào). AG-00 cắm 18 route ngày 15/10, nên chốt kiểu đó biến ca
        thử thành **cửa khoá chết ngược chiều tiến bộ**: backend làm xong là ca HỎNG. Cùng cái
        bẫy `thu_frontend` ca 52 đã dính ở đợt 2.

        Ý định thật của ca: nhãn phải KHỚP thực tế, và màn nào còn chờ thì phải khai phạm vi.
        Nên chốt theo ý định: mỗi màn có `cho_backend=true` thì PHẢI có nhãn và phạm vi; màn
        nào `false` thì KHÔNG được mang nhãn chờ.
        """
        ra = self._node(
            'const ms=F.tatCaManHinh();'
            'if(ms.length!==7) throw new Error("phải đúng 7 màn, thấy "+ms.length);'
            'for(const m of ms){'
            'if(m.cho_backend){'
            '  if(m.nhan!=="CHỜ BACKEND") throw new Error(m.ma+" chờ backend mà thiếu nhãn");'
            '  if(!m.ghi_chu_pham_vi) throw new Error(m.ma+" chờ backend mà không khai phạm vi");'
            '} else {'
            '  if(m.nhan==="CHỜ BACKEND") throw new Error(m.ma+" route đã có mà vẫn dán nhãn chờ");'
            '}}'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j4_nhan_CHO_BACKEND_khong_noi_doi_duoc(self):
        """Đọc `server.py` THẬT: đường nào đã cắm mà vẫn khai chờ backend thì ca này HỎNG.

        Đây là chốt chống nhãn nói dối lâu — đúng khuôn `API_CHO_BACKEND` của `admin/logic.js`.
        """
        import json as _json
        ds = _json.loads(self._node(
            'console.log(JSON.stringify(F.API_CHO_BACKEND_TC.map(x=>x.duong)));'))
        da_dung = _json.loads(self._node(
            'console.log(JSON.stringify(F.API_DANG_DUNG_TC.map(x=>x[1])));'))
        # Sàn đếm TỔNG hai bảng, không chỉ bảng chờ. Bản đầu đòi bảng CHỜ >= 10 — nhưng khi
        # AG-00 cắm hết 18 route thì bảng chờ phải RỖNG, và rỗng bị tính là hỏng. Sàn tồn tại
        # để chặn ca thử thành vô nghĩa (đọc 0 mục rồi báo đạt, §12.1 luật 5); đếm tổng giữ
        # đúng tác dụng đó mà không chặn chiều tiến bộ.
        self.assertGreaterEqual(
            len(ds) + len(da_dung), 10,
            f"cả hai bảng chỉ có {len(ds) + len(da_dung)} đường — ca thử đang canh gần như "
            f"không gì. Một đường biến mất khỏi CẢ HAI bảng là đường không ai còn canh.")
        with open(os.path.join(GOC_APP, "server.py"), encoding="utf-8") as f:
            sv = f.read()
        for duong in set(ds):
            mau = duong.split("<")[0].rstrip("/")
            self.assertNotIn(mau, sv,
                             f"{duong} ĐÃ có trong server.py mà finance.js vẫn khai CHỜ BACKEND "
                             f"— chuyển dòng đó sang API_DANG_DUNG_TC")
        # Chiều ngược lại, cũng phải canh: khai ĐANG DÙNG mà route KHÔNG có là nhãn nói dối
        # theo hướng tệ hơn — giao diện sẽ gọi thật rồi báo lỗi lạ cho người dùng.
        thieu = [d for d in set(da_dung) if d.split("<")[0].rstrip("/") not in sv]
        self.assertEqual(thieu, [],
                         f"finance.js khai ĐANG DÙNG nhưng server.py KHÔNG có: {thieu}")

    def test_j5_kiem_form_doi_dung_ba_dieu_backend_cung_doi(self):
        ra = self._node(
            'const a=F.kiemTraDieuChinh({loai:"cod",so_tien_dong:1000,ly_do:""});'
            'if(!a.some(x=>x.truong==="ly_do")) throw new Error("thiếu lý do mà vẫn cho qua");'
            'const b=F.kiemTraDieuChinh({loai:"cod",so_tien_dong:0,ly_do:"x"});'
            'if(!b.some(x=>x.truong==="so_tien_dong")) throw new Error("0 đồng vẫn cho qua");'
            'const c=F.kiemTraDieuChinh({loai:"cod",so_tien_dong:1.5,ly_do:"x"});'
            'if(!c.some(x=>x.truong==="so_tien_dong")) throw new Error("số thập phân cho qua");'
            'if(F.kiemTraDieuChinh({loai:"phi",so_tien_dong:-2000,ly_do:"hãng hoàn"}).length)'
            ' throw new Error("điều chỉnh âm hợp lệ bị chặn oan");'
            'if(!F.kiemTraNapBangKe({hang:"vtp",ten_file:"a.pdf"}).length)'
            ' throw new Error("PDF vẫn cho nạp");'
            'if(F.kiemTraNapBangKe({hang:"vtp",ten_file:"a.xlsx"}).length)'
            ' throw new Error("xlsx hợp lệ bị chặn oan");'
            'if(!F.kiemTraXuLyChenhLech({xu_ly:"bo_qua",ghi_chu:" "}).length)'
            ' throw new Error("bỏ qua không ghi lý do vẫn cho qua");'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j6_bay_loai_chenh_lech_giu_du_nhom_ke_ca_nhom_rong(self):
        ra = self._node(
            'if(F.LOAI_CHENH_LECH.length!==7) throw new Error("phải 7 loại");'
            'const g=F.nhomChenhLech([{loai:"cod_lech"},{loai:"loai_la"}]);'
            'if(g.filter(x=>!x.la).length!==7) throw new Error("nhóm rỗng bị bỏ khỏi màn hình");'
            'if(!g.some(x=>x.la)) throw new Error("loại lạ bị nuốt im lặng");'
            'for(const x of g.filter(y=>!y.la)) if(!x.cach_xu)'
            ' throw new Error(x.ma+" thiếu cách xử — gộp thành nhãn lỗi chung");'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j7_canh_bao_khong_nuot_cong_no_lech_va_nhat_ky_hong(self):
        ra = self._node(
            'const c=F.canhBao({cong_no_khop:false,nhat_ky:{ok:false,dong_hong:[7]},cod:{}});'
            'if(!c.some(x=>x.ma==="cong_no_lech")) throw new Error("công nợ lệch bị nuốt");'
            'if(!c.some(x=>x.ma==="nhat_ky_hong")) throw new Error("nhật ký hỏng bị nuốt");'
            'const d=F.donGiaoXongChuaDoiSoat('
            '[{trang_thai_giao:"giao_thanh_cong",trang_thai:"COD_EXPECTED"},'
            ' {trang_thai_giao:"giao_thanh_cong",trang_thai:"COD_SETTLED"}]);'
            'if(d.length!==1) throw new Error("đếm sai đơn giao xong chưa đối soát");'
            'if(!F.NHAC_GIAO_KHAC_THU.includes("KHÔNG")) throw new Error("thiếu câu nhắc §18");'
            'console.log("ok");')
        self.assertEqual(ra, "ok")

    def test_j8_admin_khong_co_thu_muc_con(self):
        """`thu_saas.test_13` dùng `os.listdir` + `open` nên gặp thư mục là `IsADirectoryError`."""
        d = os.path.join(self.GOC, "admin")
        con = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
        self.assertEqual(con, [], f"admin/ có thư mục con: {con}")
        self.assertIn("finance.js", os.listdir(d))

    def test_j9_finance_js_khong_cam_secret(self):
        with open(os.path.join(self.GOC, "admin", "finance.js"), encoding="utf-8") as f:
            nd = f.read()
        # Hai chuỗi này là đúng phép đo của `thu_saas.test_13` — giữ cùng phạm vi.
        for xau in ("privateKey", "jtexpress.vn"):
            self.assertNotIn(xau, nd, f"finance.js chứa {xau!r}")
        # Và KHÔNG có gán bí mật nào. Chỉ chặn dạng GÁN, không chặn chữ trong lời bình:
        # chặn cả chữ trong lời bình thì câu "KHÔNG giữ secret" cũng bị báo lỗi, và người
        # sau sẽ học cách gỡ lời bình thay vì gỡ bí mật.
        import re as _re
        for m in _re.finditer(r"(secret|token|api[_-]?key|password|authorization)\s*[:=]\s*[\"']",
                              nd, _re.I):
            self.fail(f"finance.js có gán bí mật: {nd[m.start():m.start() + 60]!r}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
