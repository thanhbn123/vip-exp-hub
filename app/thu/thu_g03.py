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
import adapter_jt as ajt  # noqa: E402
import loi_hang as lh   # noqa: E402
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
            self.assertTrue(callable(getattr(lop, "getCapabilities", None)),
                            f"{ma} thiếu getCapabilities (hợp đồng SHARED_CONTRACTS mục 4)")
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
        with open(os.path.join(GOC_APP, "bao_mat.py"), encoding="utf-8") as f:
            nguon = f.read()
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


class F_GetCapabilities(unittest.TestCase):
    """getCapabilities() — hàm chuẩn của hợp đồng (SHARED_CONTRACTS mục 4)."""

    KHOA_BAT_BUOC = ("ma_hang", "ten_hang", "chuc_nang", "moi_truong", "la_mock", "live_mo",
                     "khoa_chong_trung", "createOrder_duoc_thu_lai", "ma_trang_thai_da_biet",
                     "so_ma_loi_da_biet")

    def test_f1_moi_adapter_tra_du_khoa(self):
        for ma in adapter._DANG_KY:
            c = adapter.tao_adapter(ma, {}, "mock").getCapabilities()
            self.assertIsInstance(c, dict)
            for k in self.KHOA_BAT_BUOC:
                self.assertIn(k, c, f"{ma}.getCapabilities thiếu khóa '{k}'")

    def test_f2_khop_voi_capability_va_danh_sach_hang(self):
        """Ba đường đọc capability KHÔNG được nói khác nhau — lệch là hỏng im lặng (§12.2)."""
        ds = adapter.danh_sach_hang()
        for ma, lop in adapter._DANG_KY.items():
            ad = adapter.tao_adapter(ma, {}, "mock")
            c = ad.getCapabilities()
            self.assertEqual(c["chuc_nang"], lop.CAPABILITIES)
            self.assertEqual(c["chuc_nang"], ds[ma]["capabilities"])
            self.assertEqual(c["live_mo"], ds[ma]["live_mo"])
            self.assertEqual(c["khoa_chong_trung"], ds[ma]["khoa_chong_trung"])
            for k, v in lop.CAPABILITIES.items():
                self.assertEqual(ad.capability(k), v, f"{ma}: capability('{k}') lệch getCapabilities")

    def test_f3_chuc_nang_la_ban_sao_khong_sua_duoc_vao_lop(self):
        ad = adapter.tao_adapter("jt", {}, "mock")
        c = ad.getCapabilities()
        c["chuc_nang"]["createOrder"] = "BI_SUA"
        self.assertIs(adapter._DANG_KY["jt"].CAPABILITIES["createOrder"], True,
                      "getCapabilities trả thẳng dict của lớp — sửa một chỗ hỏng mọi tenant")

    def test_f4_noi_dung_dung_su_that(self):
        ad = adapter.tao_adapter("jt", {}, "mock")
        c = ad.getCapabilities()
        self.assertEqual(c["moi_truong"], "mock")
        self.assertTrue(c["la_mock"], "chạy mock mà không tự nhận là mock")
        self.assertFalse(c["live_mo"], "LIVE phải đang khóa")
        self.assertTrue(c["khoa_chong_trung"] and c["createOrder_duoc_thu_lai"])
        self.assertEqual(set(c["ma_trang_thai_da_biet"]), {str(x) for x in tth.ma_da_biet("jt")})
        # J&T: đã đọc được bảng mã lỗi thật → phải > 0. VTP: chưa có tài liệu → phải = 0.
        self.assertGreater(c["so_ma_loi_da_biet"], 0)
        self.assertEqual(adapter.tao_adapter("vtp", {}, "mock").getCapabilities()["so_ma_loi_da_biet"],
                         0, "VTP chưa có tài liệu mã lỗi mà lại khai có — là bịa")


class G_LoiHangChuanHoa(unittest.TestCase):
    """NormalizedCarrierError (app/loi_hang.py) — SHARED_CONTRACTS mục 5."""

    def test_g1_du_truong_bat_buoc(self):
        e = lh.NormalizedCarrierError(lh.THAM_SO_SAI, ma_goc_hang="145003050", thong_diep="x")
        for t in ("ma_chuan", "ma_goc_hang", "thong_diep", "co_the_thu_lai"):
            self.assertTrue(hasattr(e, t), f"thiếu trường bắt buộc '{t}'")
        self.assertIsInstance(e.co_the_thu_lai, bool)
        self.assertEqual(e.ma_goc_hang, "145003050")
        self.assertIsInstance(e, Exception, "phải ném được như ngoại lệ")

    def test_g2_ma_chuan_la_tap_dong(self):
        with self.assertRaises(ValueError, msg="mã chuẩn lạ phải hỏng TO, không đi tiếp âm thầm"):
            lh.NormalizedCarrierError("MA_TU_NGHI_RA")
        for m in lh.MA_CHUAN:
            self.assertIsInstance(lh.NormalizedCarrierError(m).co_the_thu_lai, bool)

    def test_g3_danh_sach_trang_cho_thu_lai(self):
        """Chỉ HET_GIO và QUA_HAN_MUC được thử lại; quên một loại phải ra KHÔNG thử lại."""
        for m in lh.MA_CHUAN:
            self.assertEqual(lh.NormalizedCarrierError(m).co_the_thu_lai,
                             m in (lh.HET_GIO, lh.QUA_HAN_MUC), f"{m} sai chính sách thử lại")
        self.assertFalse(lh.NormalizedCarrierError(lh.KHONG_RO).co_the_thu_lai,
                         "mã KHÔNG RÕ mà cho thử lại — đúng kiểu thử lại mù gây đơn trùng")
        # cấm nới lỏng: ép True cho loại ngoài danh sách trắng vẫn phải ra False
        self.assertFalse(lh.NormalizedCarrierError(lh.THAM_SO_SAI, co_the_thu_lai=True).co_the_thu_lai)
        # nhưng được siết chặt hơn
        self.assertFalse(lh.NormalizedCarrierError(lh.HET_GIO, co_the_thu_lai=False).co_the_thu_lai)

    def test_g4_bang_ma_loi_jt_that(self):
        """Mã chép từ open.jtexpress.vn/apiDoc/errorCode/index (đọc bằng trình duyệt 14/10/2026)."""
        self.assertIsNone(lh.doc_tra_loi_jt({"code": "1", "msg": "success"}), "code=1 là thành công")
        cho = {"145003030": lh.XAC_THUC_HONG, "145003031": lh.XAC_THUC_HONG,
               "999001030": lh.XAC_THUC_HONG, "145003050": lh.THAM_SO_SAI,
               "145003502": lh.THAM_SO_SAI, "145003204": lh.DON_TRUNG,
               "999010010": lh.HANG_TU_CHOI, "999002000": lh.KHONG_TIM_THAY}
        for ma, chuan in cho.items():
            e = lh.doc_tra_loi_jt({"code": ma, "msg": "m"}, thao_tac="createOrder")
            self.assertIsNotNone(e, f"mã {ma} phải là lỗi")
            self.assertEqual(e.ma_chuan, chuan, f"{ma} ánh xạ sai")
            self.assertEqual(e.ma_goc_hang, ma, "mất mã gốc của hãng")
            self.assertFalse(e.co_the_thu_lai, f"{ma} không được thử lại")

    def test_g5_ma_loi_la_khong_doan_nghia(self):
        e = lh.doc_tra_loi_jt({"code": "999999999", "msg": "loi la"})
        self.assertEqual(e.ma_chuan, lh.KHONG_RO)
        self.assertFalse(e.co_the_thu_lai)
        self.assertIn("999999999", e.thong_diep)
        # tài liệu ghi rõ 0 = fail — tuyệt đối không coi là thành công
        self.assertIsNotNone(lh.doc_tra_loi_jt({"code": "0", "msg": "fail"}))
        # gói trả lời dị dạng cũng không được lọt thành công
        for goi in ({}, {"msg": "x"}, [], "ok", None):
            self.assertIsNotNone(lh.doc_tra_loi_jt(goi), f"gói {goi!r} lọt thành công")

    def test_g6_vtp_chua_co_bang_ma_loi_thi_noi_thang(self):
        self.assertNotIn("vtp", lh.BANG_MA_LOI,
                         "VTP chưa có tài liệu mã lỗi mà đã có bảng — kiểm lại nguồn")
        e = lh.tu_ma_hang("vtp", "ABC", msg="loi gi do")
        self.assertEqual(e.ma_chuan, lh.KHONG_RO)
        self.assertFalse(e.co_the_thu_lai)

    def test_g7_tu_http(self):
        cho = {408: lh.HET_GIO, 429: lh.QUA_HAN_MUC, 500: lh.HET_GIO, 503: lh.HET_GIO,
               401: lh.XAC_THUC_HONG, 403: lh.XAC_THUC_HONG, 404: lh.KHONG_TIM_THAY,
               400: lh.THAM_SO_SAI, 422: lh.THAM_SO_SAI, 418: lh.KHONG_RO}
        for st, chuan in cho.items():
            e = lh.tu_http(st, hang="jt")
            self.assertEqual(e.ma_chuan, chuan, f"HTTP {st} phân loại sai")
            self.assertEqual(e.http_status, st)
        self.assertTrue(lh.tu_http(429).co_the_thu_lai)
        self.assertTrue(lh.tu_http(503).co_the_thu_lai)
        self.assertFalse(lh.tu_http(400).co_the_thu_lai)
        self.assertFalse(lh.tu_http(418).co_the_thu_lai, "4xx lạ mà cho thử lại")

    def test_g8_noi_hai_chieu_voi_transport(self):
        """co_the_thu_lai là thứ DUY NHẤT quyết định — hai lớp không được lệch nhau."""
        self.assertEqual(lh.tu_ngoai_le(tp.LoiTamThoi("chap"), hang="jt").ma_chuan, lh.HET_GIO)
        self.assertTrue(lh.tu_ngoai_le(tp.LoiTamThoi("chap")).co_the_thu_lai)
        self.assertEqual(lh.tu_ngoai_le(tp.LoiVinhVien("sai chu ky")).ma_chuan, lh.THAM_SO_SAI)
        self.assertFalse(lh.tu_ngoai_le(tp.LoiVinhVien("x")).co_the_thu_lai)
        self.assertEqual(lh.tu_ngoai_le(RuntimeError("la")).ma_chuan, lh.KHONG_RO)
        for m in lh.MA_CHUAN:
            e = lh.NormalizedCarrierError(m)
            lop_mong = tp.LoiTamThoi if e.co_the_thu_lai else tp.LoiVinhVien
            self.assertIsInstance(lh.thanh_ngoai_le_transport(e), lop_mong,
                                  f"{m}: hai lớp lệch chính sách thử lại")
        e = lh.NormalizedCarrierError(lh.HET_GIO)
        self.assertTrue(lh.tu_ngoai_le(lh.thanh_ngoai_le_transport(e)).co_the_thu_lai)

    def test_g9_don_trung_khong_bao_gio_thu_lai(self):
        """145003204 nghĩa là lượt trước ĐÃ vào hãng — thử lại nữa là chắc chắn sai."""
        e = lh.doc_tra_loi_jt({"code": "145003204", "msg": "订单重复"}, thao_tac="createOrder")
        self.assertEqual(e.ma_chuan, lh.DON_TRUNG)
        self.assertFalse(e.co_the_thu_lai)
        self.assertIsInstance(lh.thanh_ngoai_le_transport(e), tp.LoiVinhVien)

    def test_g10_nhu_dict_ghi_audit_duoc(self):
        e = lh.doc_tra_loi_jt({"code": "999001030", "msg": "sai mat khau"}, thao_tac="createOrder")
        d = e.nhu_dict()
        for k in ("ma_chuan", "ma_goc_hang", "thong_diep", "co_the_thu_lai"):
            self.assertIn(k, d)
        self.assertNotIn("tho", d, "nhu_dict() không được kéo theo dữ liệu thô chưa lọc")
        self.assertTrue(json.dumps(d, ensure_ascii=False))

    def test_g11_adapter_jt_dung_bang_ma_loi_that(self):
        """Ca ép lỗi của mock cũng phải đi qua mã lỗi THẬT, không bịa chuỗi lỗi riêng."""
        ad = adapter.tao_adapter("jt", {}, "mock")
        kq = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail"))
        self.assertFalse(kq.ok)
        self.assertEqual(kq.tho["loi_chuan"]["ma_chuan"], lh.THAM_SO_SAI)
        self.assertIn(kq.tho["loi_chuan"]["ma_goc_hang"], lh.JT_MA_LOI)
        kq2 = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout"))
        self.assertTrue(kq2.timeout)
        self.assertEqual(kq2.tho["loi_chuan"]["ma_chuan"], lh.HET_GIO)
        self.assertTrue(kq2.tho["loi_chuan"]["co_the_thu_lai"])


class H_ChuKyJT(unittest.TestCase):
    """Hợp đồng chữ ký J&T — đối chiếu TÀI LIỆU, không đối chiếu mã của chính mình.
    Nguồn: open.jtexpress.vn/apiDoc, trang 极兔API简介, đọc bằng trình duyệt 14/10/2026."""

    def test_h1_cong_thuc_digest_dung_tai_lieu(self):
        """digest = base64( md5-BYTES( bizContent + privateKey ) ) — md5 ra byte rồi mới base64."""
        import base64 as b64
        import hashlib as hl
        biz, key = '{"customerCode":"024E000014","key":"Z354nbj1"}', "Z354nbj1"
        mong = b64.b64encode(hl.md5((biz + key).encode("utf-8")).digest()).decode()
        self.assertEqual(ajt.ky_digest(biz, key), mong)
        # và phải KHÁC biến thể sai hay gặp: base64 của chuỗi hex md5
        sai_hex = b64.b64encode(hl.md5((biz + key).encode()).hexdigest().encode()).decode()
        self.assertNotEqual(ajt.ky_digest(biz, key), sai_hex,
                            "đang base64 chuỗi hex — sai so với tài liệu")
        self.assertEqual(len(ajt.ky_digest(biz, key)), 24, "md5 16 byte → base64 phải 24 ký tự")

    def test_h2_chu_ky_phu_thuoc_ca_hai_dau_vao(self):
        a = ajt.ky_digest('{"a":1}', "K1")
        self.assertNotEqual(a, ajt.ky_digest('{"a":2}', "K1"), "đổi bizContent mà chữ ký không đổi")
        self.assertNotEqual(a, ajt.ky_digest('{"a":1}', "K2"), "đổi privateKey mà chữ ký không đổi")

    def test_h3_tieng_viet_co_dau_ky_theo_utf8(self):
        """Tài liệu ghi 字符编码默认统一采用UTF-8. Ký bằng bảng mã khác là sai chữ ký im lặng."""
        import base64 as b64
        import hashlib as hl
        biz = '{"name":"Nguyễn Đình Thành"}'
        self.assertEqual(ajt.ky_digest(biz, "K"),
                         b64.b64encode(hl.md5((biz + "K").encode("utf-8")).digest()).decode())

    def test_h4_bizcontent_la_CHUOI_json_khong_phai_object(self):
        s = ajt.dung_bizcontent({"customerCode": "C", "txlogisticId": "T1"})
        self.assertIsInstance(s, str, "bizContent phải là chuỗi JSON (tài liệu: json格式的string)")
        self.assertEqual(json.loads(s)["txlogisticId"], "T1")
        body = ajt.dung_body(s)
        self.assertEqual(list(body), ["bizContent"], "thân form chỉ có đúng trường bizContent")
        self.assertIsInstance(body["bizContent"], str)

    def test_h5_header_du_ba_truong_va_content_type(self):
        biz = ajt.dung_bizcontent({"a": 1})
        h = ajt.dung_headers("669375073659916329", biz, "KEY")
        for k in ("apiAccount", "digest", "timestamp"):
            self.assertIn(k, h, f"thiếu header bắt buộc '{k}'")
        self.assertEqual(h["Content-Type"], "application/x-www-form-urlencoded")
        self.assertEqual(h["digest"], ajt.ky_digest(biz, "KEY"))
        self.assertEqual(h["apiAccount"], "669375073659916329")

    def test_h6_timestamp_mili_giay_mui_gio_utc7(self):
        """Tài liệu: 时间戳，毫秒 / 时区：UTC+7. Tính tường minh, không mượn múi giờ của máy."""
        import datetime as dt
        ts = ajt.dung_headers("1", "{}", "K")["timestamp"]
        self.assertTrue(ts.isdigit(), "timestamp phải là chuỗi số")
        tz7 = dt.timezone(dt.timedelta(hours=7))
        moc = dt.datetime(2026, 10, 14, 12, 0, 0, tzinfo=tz7)
        self.assertEqual(ajt.dau_thoi_gian_ms(moc), int(moc.timestamp() * 1000))
        self.assertEqual(len(str(ajt.dau_thoi_gian_ms())), 13,
                         "timestamp đang là giây, không phải mili giây")

    def test_h7_goi_tao_don_ky_dung_chuoi_da_gui_di(self):
        """Chữ ký phải ký ĐÚNG chuỗi bizContent nằm trong thân yêu cầu, không ký bản khác."""
        ad = adapter.tao_adapter("jt", {"apiAccount": "A1", "customerCode": "C",
                                        "password": "P", "privateKey": "K"}, "mock")
        yc = ad.yeu_cau_tao_don(dict(DON_MAU))
        self.assertEqual(yc["body"]["bizContent"], yc["bizContent"])
        self.assertEqual(yc["headers"]["digest"], ajt.ky_digest(yc["bizContent"], "K"))
        self.assertEqual(json.loads(yc["bizContent"])["txlogisticId"], DON_MAU["ma_don"])
        self.assertIsNone(yc["url"], "môi trường mock KHÔNG được có URL thật để lỡ gọi ra ngoài")

    def test_h8_mock_tach_bach_khong_co_ma_goi_mang(self):
        for ten in ("adapter.py", "adapter_jt.py", "adapter_vtp.py", "loi_hang.py"):
            with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
                nguon = f.read()
            for cam in ("import requests", "import httpx", "urllib.request", "http.client",
                        "socket.socket"):
                self.assertNotIn(cam, nguon, f"{ten} có mã gọi mạng ('{cam}') — mock phải sạch")


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
