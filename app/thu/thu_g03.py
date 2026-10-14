# Bộ thử G03 — Carrier Integration Engine (thuần local, không gọi hãng thật).
#   A. Hợp đồng adapter: chạy với MỌI adapter đã đăng ký (hãng mới thêm vào là tự bị kiểm).
#   B. Bảng ánh xạ trạng thái.
#   C. Khung retry/timeout.
#   D. Polling fallback.
# Chạy: python3 app/thu/thu_g03.py
import json
import os
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g03-")
os.environ["VIP_HUB_DATA"] = _tam

import adapter          # noqa: E402
import adapter_jt       # noqa: E402
import adapter_vtp      # noqa: E402
import bao_mat          # noqa: E402
import csdl             # noqa: E402
import don_hang         # noqa: E402
import polling          # noqa: E402
import quyen            # noqa: E402
import trang_thai_hang as tth   # noqa: E402
import transport as tp  # noqa: E402

HAM_CHUAN = ("createOrder", "cancelOrder", "getOrder", "trackOrder",
             "getShippingFee", "getShippingLabel")
DON_MAU = {"ma_don": "T-TEST-1", "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0901111111",
           "nguoi_gui_dia_chi": "x", "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0902222222",
           "nguoi_nhan_dia_chi": "y", "hang_hoa": "z", "khoi_luong_gram": 500, "cod": 0}


class A_HopDongAdapter(unittest.TestCase):
    """Chạy với MỌI adapter đã đăng ký — thêm hãng mới mà quên gì là hỏng ở đây."""

    def test_a1_du_ham_chuan(self):
        for ma, lop in adapter._DANG_KY.items():
            for ham in HAM_CHUAN:
                self.assertTrue(callable(getattr(lop, ham, None)), f"{ma} thiếu {ham}")
            self.assertTrue(callable(getattr(lop, "normalizeTrackingStatus", None)))
            self.assertTrue(lop.ma_hang and lop.ten_hang, f"{ma} thiếu tên")

    def test_a2_capability_khai_du_khoa(self):
        for ma, lop in adapter._DANG_KY.items():
            for k in list(HAM_CHUAN) + ["webhook"]:
                self.assertIn(k, lop.CAPABILITIES, f"{ma} chưa khai capability '{k}'")
                self.assertIsInstance(lop.CAPABILITIES[k], bool)

    def test_a3_capability_trung_thuc(self):
        """Khai False thì phải trả 'không hỗ trợ' tử tế, KHÔNG được ném lỗi hay giả vờ làm được."""
        for ma, lop in adapter._DANG_KY.items():
            ad = adapter.tao_adapter(ma, {}, "mock")
            for ham in HAM_CHUAN:
                if lop.CAPABILITIES.get(ham):
                    continue
                kq = getattr(ad, ham)(DON_MAU if ham in ("createOrder", "getShippingFee") else "MVD1")
                self.assertFalse(kq.ok, f"{ma}.{ham} khai không hỗ trợ nhưng trả ok=True")
                self.assertIn("không hỗ trợ", kq.loi or "")

    def test_a4_capability_true_thi_chay_duoc_o_mock(self):
        for ma, lop in adapter._DANG_KY.items():
            ad = adapter.tao_adapter(ma, {"customerCode": "C", "password": "P", "privateKey": "K"}, "mock")
            if lop.CAPABILITIES.get("createOrder"):
                kq = ad.createOrder(dict(DON_MAU))
                self.assertTrue(kq.ok and kq.ma_van_don, f"{ma}.createOrder mock hỏng: {kq.loi}")
            if lop.CAPABILITIES.get("getShippingFee"):
                kq = ad.getShippingFee(dict(DON_MAU))
                self.assertTrue(kq.ok and isinstance(kq.phi, int) and kq.phi > 0, f"{ma} phí sai")

    def test_a5_live_bi_khoa_moi_hang(self):
        for ma in adapter._DANG_KY:
            for mt in ("sandbox", "production"):
                with self.assertRaises(PermissionError, msg=f"{ma}/{mt} không bị khóa!"):
                    adapter.tao_adapter(ma, {}, mt)

    def test_a6_mock_tu_nhan_la_mock(self):
        """Không được giả lập API thật thành 'đang hoạt động'."""
        for ma, lop in adapter._DANG_KY.items():
            ad = adapter.tao_adapter(ma, {}, "mock")
            if lop.CAPABILITIES.get("createOrder"):
                kq = ad.createOrder(dict(DON_MAU))
                self.assertTrue((kq.tho or {}).get("mock") is True,
                                f"{ma} không tự nhận là mock trong kết quả")

    def test_a7_ba_ket_cuc_phan_biet_duoc(self):
        for ma, lop in adapter._DANG_KY.items():
            if not lop.CAPABILITIES.get("createOrder"):
                continue
            ad = adapter.tao_adapter(ma, {}, "mock")
            ok = ad.createOrder(dict(DON_MAU))
            tu_choi = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail"))
            het_gio = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout"))
            self.assertTrue(ok.ok and not ok.timeout)
            self.assertFalse(tu_choi.ok); self.assertFalse(tu_choi.timeout)
            self.assertFalse(het_gio.ok); self.assertTrue(het_gio.timeout, f"{ma} không báo timeout")

    def test_a8_normalize_tra_ket_qua_chuan(self):
        import cau_hinh
        hop_le = set(cau_hinh.HANG_TRANG_THAI_GIAO)
        for ma, lop in adapter._DANG_KY.items():
            ad = adapter.tao_adapter(ma, {}, "mock")
            la = ad.normalizeTrackingStatus("MA_KHONG_TON_TAI_123")
            self.assertFalse(la.biet_ma, f"{ma} nhận mã lạ là hợp lệ")
            self.assertIsNone(la.trang_thai, f"{ma} đổi trạng thái theo mã lạ — nguy hiểm")
            for ma_goc in tth.ma_da_biet(ma):
                kq = ad.normalizeTrackingStatus(ma_goc)
                self.assertTrue(kq.biet_ma)
                if kq.trang_thai is not None:
                    self.assertIn(kq.trang_thai, hop_le, f"{ma}:{ma_goc} ánh xạ ra trạng thái lạ")


class B_AnhXaTrangThai(unittest.TestCase):
    def test_b1_ma_that_cua_jt(self):
        # Mã chép từ tài liệu open.jtexpress.vn (đọc 14/10/2026)
        self.assertEqual(tth.anh_xa("jt", 106).trang_thai, "lay_hang")
        self.assertEqual(tth.anh_xa("jt", 113).trang_thai, "giao_thanh_cong")
        self.assertEqual(tth.anh_xa("jt", 118).trang_thai, "giao_that_bai")
        self.assertEqual(tth.anh_xa("jt", 116).trang_thai, "hoan_hang")
        for ma in (109, 110, 112):
            self.assertEqual(tth.anh_xa("jt", ma).trang_thai, "dang_giao")

    def test_b2_ma_chua_chac_thi_khong_doi_trang_thai(self):
        for ma in (104, 105, 120, 121):
            kq = tth.anh_xa("jt", ma)
            self.assertTrue(kq.biet_ma, f"{ma} phải có trong bảng")
            self.assertIsNone(kq.trang_thai, f"{ma} không được tự đổi trạng thái khi chưa chắc")

    def test_b3_ma_dang_chuoi_va_ma_la(self):
        self.assertEqual(tth.anh_xa("jt", "113").trang_thai, "giao_thanh_cong")  # chuỗi số vẫn hiểu
        self.assertFalse(tth.anh_xa("jt", "abc").biet_ma)
        self.assertFalse(tth.anh_xa("jt", 10).biet_ma)      # mã trong ví dụ tài liệu, chưa có nghĩa
        self.assertFalse(tth.anh_xa("hang_la", 1).biet_ma)


class C_RetryTimeout(unittest.TestCase):
    def setUp(self):
        self.ngu = lambda s: None

    def test_c1_doc_duoc_thu_lai(self):
        n = [0]
        def f():
            n[0] += 1
            if n[0] < 3:
                raise tp.LoiTamThoi("chap")
            return "ok"
        kq, lan, _ = tp.goi(f, "trackOrder", ngu=self.ngu)
        self.assertEqual((kq, lan), ("ok", 3))

    def test_c2_create_order_khong_khoa_chong_trung_thi_KHONG_thu_lai(self):
        n = [0]
        def f():
            n[0] += 1
            raise tp.LoiTamThoi("het gio")
        with self.assertRaises(tp.LoiTamThoi):
            tp.goi(f, "createOrder", co_khoa_chong_trung=False, ngu=self.ngu)
        self.assertEqual(n[0], 1, "createOrder bị thử lại → nguy cơ tạo đơn TRÙNG ở hãng")

    def test_c3_create_order_co_khoa_chong_trung_thi_duoc_thu_lai(self):
        n = [0]
        def f():
            n[0] += 1
            if n[0] < 2:
                raise tp.LoiTamThoi("het gio")
            return "ok"
        kq, lan, _ = tp.goi(f, "createOrder", co_khoa_chong_trung=True, ngu=self.ngu)
        self.assertEqual(lan, 2)

    def test_c4_loi_vinh_vien_khong_thu_lai(self):
        n = [0]
        def f():
            n[0] += 1
            raise tp.LoiVinhVien("sai chu ky")
        with self.assertRaises(tp.LoiVinhVien):
            tp.goi(f, "trackOrder", ngu=self.ngu)
        self.assertEqual(n[0], 1)

    def test_c5_chinh_sach_theo_khoa_chong_trung_cua_adapter(self):
        # J&T có txlogisticId (tài liệu: "不支持重复") → được thử lại; VTP chưa có tài liệu → không
        self.assertTrue(adapter._DANG_KY["jt"].KHOA_CHONG_TRUNG)
        self.assertFalse(adapter._DANG_KY["vtp"].KHOA_CHONG_TRUNG)
        self.assertTrue(tp.chinh_sach_cho("createOrder", True).duoc_thu_lai)
        self.assertFalse(tp.chinh_sach_cho("createOrder", False).duoc_thu_lai)

    def test_c6_backoff_tang_dan(self):
        cho = []
        n = [0]
        def f():
            n[0] += 1
            if n[0] < 3:
                raise tp.LoiTamThoi("x")
            return 1
        tp.goi(f, "trackOrder", ngu=cho.append)
        self.assertEqual(len(cho), 2)
        self.assertLess(cho[0], cho[1], "backoff không tăng dần")


class D_Polling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csdl.mo(); quyen.seed()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        for ma, h in adapter.danh_sach_hang().items():
            csdl.ghi("INSERT OR IGNORE INTO carrier_providers (ma,ten,capabilities_json,live_mo,cap_nhat_luc)"
                     " VALUES (?,?,?,?,?)", (ma, h["ten"], json.dumps(h["capabilities"]), 0, csdl.bay_gio()))
        cls.uid = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                           " VALUES ('u',?,'U',?)", (bao_mat.bam_mat_khau("x" * 10), csdl.bay_gio())).lastrowid
        cls.tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('t','T','pro',?)",
                           (csdl.bay_gio(),)).lastrowid
        csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc) VALUES (?,?,?,?)",
                 (cls.uid, cls.tid, "TENANT_OWNER", csdl.bay_gio()))
        # AAD buộc bản mã vào (tenant, hãng) và (webhook_ma) — fixture phải mã hóa ĐÚNG như bản chạy
        cred, duoi = bao_mat.luu_credentials({"k": "v"}, bao_mat.aad_credentials(cls.tid, "vtp"))
        cls.tk = csdl.ghi("INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,"
                          "credentials_ma_hoa,credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)"
                          " VALUES (?,?,?,?,?,?,?,?,?)",
                          (cls.tid, "vtp", "VTP", "mock", cred, duoi, "wh1",
                           bao_mat.ma_hoa("s", bao_mat.aad_webhook("wh1")), csdl.bay_gio())).lastrowid

    @classmethod
    def tearDownClass(cls):
        csdl.dong()

    def _don(self, trang_thai_giao, hang_tt, mvd):
        return csdl.ghi(
            "INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,nguoi_gui_dia_chi,"
            "nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,"
            "carrier_account_id,ma_van_don,trang_thai,trang_thai_giao,hang_trang_thai_giao,"
            "nguoi_tao,tao_luc,cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'da_gui',?,?,?,?,?)",
            (self.tid, "D" + mvd, "A", "0901111111", "x", "B", "0902222222", "y", "z", 500,
             self.tk, mvd, trang_thai_giao, hang_tt, self.uid, csdl.bay_gio(), csdl.bay_gio())).lastrowid

    def test_d1_chi_hoi_don_dang_chay(self):
        d_chay = self._don("lay_hang", 2, "MVD-CHAY")
        d_xong = self._don("giao_thanh_cong", 5, "MVD-XONG")
        ds = [r["id"] for r in polling.don_can_hoi(self.tid)]
        self.assertIn(d_chay, ds)
        self.assertNotIn(d_xong, ds, "polling hỏi cả đơn đã kết thúc — tốn API vô ích")

    def test_d2_cap_nhat_qua_rank_guard(self):
        d = self._don("cho_lay", 1, "MVD-RANK")
        tk = polling.chay_mot_luot(self.tid)
        self.assertGreaterEqual(tk["da_hoi"], 1)
        # mock VTP luôn trả 'dang_giao' (hạng 3) → đơn cho_lay (hạng 1) phải tiến lên
        r = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (d,))
        self.assertEqual(r["trang_thai_giao"], "dang_giao")
        # đơn đã ở hạng cao hơn thì KHÔNG bị kéo lùi
        d2 = self._don("giao_that_bai", 4, "MVD-KHONGLUI")
        polling.chay_mot_luot(self.tid)
        r2 = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (d2,))
        self.assertEqual(r2["trang_thai_giao"], "giao_that_bai", "polling kéo lùi trạng thái!")

    def test_d3_ghi_lich_su_va_audit(self):
        d = self._don("cho_lay", 1, "MVD-LS")
        polling.chay_mot_luot(self.tid)
        ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? AND nguon='polling'", (d,))
        self.assertTrue(ls, "polling cập nhật mà không ghi lịch sử")
        au = csdl.mot("SELECT * FROM audit WHERE hanh_dong='polling_cap_nhat' ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(au)

    def test_d4_bo_qua_hang_da_co_webhook(self):
        self._don("cho_lay", 1, "MVD-WH")
        tk = polling.chay_mot_luot(self.tid, chi_hang_khong_webhook=True)
        # VTP khai webhook=True → phải bị bỏ qua ở chế độ fallback
        self.assertTrue(any("đã có webhook" in x for x in tk["bo_qua_hang"]), tk)
        self.assertEqual(tk["da_hoi"], 0)

    def test_d5_ton_trong_gioi_han_lo_cua_tai_lieu(self):
        self.assertEqual(polling.so_van_don_moi_luot("jt"), 30,
                         "J&T: tài liệu ghi tối đa 30 vận đơn mỗi lượt tra")
        self.assertLessEqual(polling.so_van_don_moi_luot("vtp"), polling.MAC_DINH_MOI_LUOT)
        lo = list(polling._gom_lo(list(range(70)), 30))
        self.assertEqual([len(x) for x in lo], [30, 30, 10])

    def test_d6_khong_tu_chay(self):
        """Polling nền phải do người bật, không tự khởi động khi import."""
        p = polling.BatDauNen(moi_giay=0.05)
        self.assertIsNone(p._luong, "polling tự chạy khi chưa ai bật")
        p.bat(); self.assertTrue(p._luong.is_alive()); p.tat()


class E_MaHoaAESGCM(unittest.TestCase):
    """Owner duyệt 14/10/2026: credentials phải mã hóa bằng AES-256-GCM chuẩn."""

    def test_e1_dung_aes_gcm_that_khong_phai_tu_che(self):
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        g = bao_mat.ma_hoa("bi mat")
        self.assertTrue(g.startswith("v2$"), "không phải định dạng AES-GCM v2")
        nonce = g.split("$")[1]
        self.assertEqual(len(nonce), 24, "nonce phải 12 byte (96 bit) chuẩn GCM")

    def test_e2_vong_tron_va_nonce_khac_nhau(self):
        ro = "credentials 123 — có dấu tiếng Việt"
        g1, g2 = bao_mat.ma_hoa(ro), bao_mat.ma_hoa(ro)
        self.assertNotEqual(g1, g2, "cùng nội dung ra cùng bản mã → nonce bị lặp")
        self.assertEqual(bao_mat.giai_ma(g1), ro)
        self.assertEqual(bao_mat.giai_ma(g2), ro)

    def test_e3_phat_hien_sua_ban_ma(self):
        g = bao_mat.ma_hoa("x" * 40)
        hong = g[:-4] + ("beef" if not g.endswith("beef") else "dead")
        with self.assertRaises(ValueError):
            bao_mat.giai_ma(hong)

    def test_e4_aad_chan_chep_cheo_tenant(self):
        g = bao_mat.ma_hoa("key cua tenant 1", bao_mat.aad_credentials(1, "vtp"))
        self.assertEqual(bao_mat.giai_ma(g, bao_mat.aad_credentials(1, "vtp")), "key cua tenant 1")
        for sai in (bao_mat.aad_credentials(2, "vtp"), bao_mat.aad_credentials(1, "jt"), ""):
            with self.assertRaises(ValueError, msg=f"AAD sai '{sai}' vẫn giải được!"):
                bao_mat.giai_ma(g, sai)

    def test_e5_doc_duoc_dinh_dang_v1_cu(self):
        """Phải còn đọc được bản mã cũ, nếu không là MẤT credentials khi migrate."""
        import hashlib, hmac as _h, secrets as _s
        key = bao_mat._khoa_noi_bo()
        ro = b"secret dinh dang cu"
        nonce = _s.token_bytes(16)
        ks, dem = b"", 0
        while len(ks) < len(ro):
            ks += hashlib.sha256(key + nonce + dem.to_bytes(4, "big")).digest(); dem += 1
        ct = bytes(a ^ b for a, b in zip(ro, ks[:len(ro)]))
        mac = _h.new(key, nonce + ct, hashlib.sha256).hexdigest()
        cu = nonce.hex() + "$" + ct.hex() + "$" + mac
        self.assertTrue(bao_mat.la_dinh_dang_cu(cu))
        self.assertEqual(bao_mat.giai_ma(cu), ro.decode())
        self.assertFalse(bao_mat.la_dinh_dang_cu(bao_mat.ma_hoa("moi")))

    def test_e6_khong_am_tham_tut_ve_so_do_yeu(self):
        """Thiếu thư viện phải HỎNG TO, không được tự chuyển sang mã hóa yếu."""
        nguon = open(os.path.join(GOC_APP, "bao_mat.py"), encoding="utf-8").read()
        self.assertIn("raise ImportError", nguon)
        self.assertIn("CỐ Ý không chạy tiếp bằng sơ đồ mã hóa yếu", nguon)
        # và không còn hàm nào mã hóa MỚI bằng sơ đồ cũ
        self.assertNotIn("def _ma_hoa_v1", nguon)

    def test_e7_migrate_v3_doi_het_sang_gcm(self):
        """Dựng carrier_account mã hóa kiểu CŨ rồi chạy nâng cấp v3, kiểm đọc lại được."""
        import migrate
        cu_cred = _ma_hoa_kieu_cu(json.dumps({"api_key": "KEY-CU-1234"}))
        cu_wh = _ma_hoa_kieu_cu("secret-webhook-cu")
        tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('tv3','Tv3','pro',?)",
                       (csdl.bay_gio(),)).lastrowid
        tk = csdl.ghi("INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
                      "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)"
                      " VALUES (?,?,?,?,?,?,?,?,?)",
                      (tid, "vtp", "cu", "mock", cu_cred, "1234", "wh-v3", cu_wh, csdl.bay_gio())).lastrowid
        kn = csdl.mo()
        with kn:
            migrate.nang_len_v3(kn)
        r = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (tk,))
        self.assertTrue(r["credentials_ma_hoa"].startswith("v2$"), "v3 không đổi credentials")
        self.assertTrue(r["webhook_secret_ma_hoa"].startswith("v2$"), "v3 không đổi webhook secret")
        self.assertEqual(json.loads(bao_mat.giai_ma(r["credentials_ma_hoa"],
                         bao_mat.aad_credentials(tid, "vtp")))["api_key"], "KEY-CU-1234")
        self.assertEqual(bao_mat.giai_ma(r["webhook_secret_ma_hoa"],
                         bao_mat.aad_webhook("wh-v3")), "secret-webhook-cu")


def _ma_hoa_kieu_cu(ro: str) -> str:
    import hashlib, hmac as _h, secrets as _s
    key = bao_mat._khoa_noi_bo()
    data = ro.encode()
    nonce = _s.token_bytes(16)
    ks, dem = b"", 0
    while len(ks) < len(data):
        ks += hashlib.sha256(key + nonce + dem.to_bytes(4, "big")).digest(); dem += 1
    ct = bytes(a ^ b for a, b in zip(data, ks[:len(data)]))
    return nonce.hex() + "$" + ct.hex() + "$" + _h.new(key, nonce + ct, hashlib.sha256).hexdigest()


if __name__ == "__main__":
    unittest.main(verbosity=2)
