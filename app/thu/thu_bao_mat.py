# Bộ thử bảo mật — key_id / SecretProvider / xoay khóa (AG-01).
# Chạy: python3 app/thu/thu_bao_mat.py
#
# Nguyên tắc của bộ thử này (CLAUDE.md §12.1): mỗi khẳng định phải do MỘT phép đo thật tạo ra.
# Không grep mã nguồn để kết luận hành vi khi còn có thể đo hành vi. Riêng ca "thiếu thư viện
# cryptography" thì đo bằng TIẾN TRÌNH CON có sys.path bị chắn, chứ không đọc mã rồi đoán.
import json
import os
import subprocess
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-baomat-")
os.environ["VIP_HUB_DATA"] = _tam

import adapter          # noqa: E402
import adapter_jt       # noqa: E402,F401
import adapter_vtp      # noqa: E402,F401
import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import khoi_tao         # noqa: E402
import quyen            # noqa: E402
import secret_provider as sp   # noqa: E402

SECRET_WH = "secret-webhook-RAT-DAC-BIET-9f3a"
CRED_KEY = "API-KEY-RAT-DAC-BIET-7b21"


def _ma_hoa_v1(ro: str) -> str:
    """Dựng bản mã ĐỊNH DẠNG v1 (XOR keystream + HMAC) đúng như bản cũ đã ghi ra CSDL."""
    import hashlib
    import hmac as _h
    import secrets as _s
    key = bao_mat._khoa_noi_bo()
    data = ro.encode()
    nonce = _s.token_bytes(16)
    ks, dem = b"", 0
    while len(ks) < len(data):
        ks += hashlib.sha256(key + nonce + dem.to_bytes(4, "big")).digest()
        dem += 1
    ct = bytes(a ^ b for a, b in zip(data, ks[:len(data)]))
    return nonce.hex() + "$" + ct.hex() + "$" + _h.new(key, nonce + ct, hashlib.sha256).hexdigest()


class A_DinhDangKeyId(unittest.TestCase):
    """v3 phải mang key_id, và vẫn đọc được v1/v2."""

    def test_a1_ban_ma_moi_la_v3_co_key_id(self):
        g = bao_mat.ma_hoa_v3("bi mat")
        phan = g.split("$")
        self.assertEqual(phan[0], "v3", f"không phải định dạng v3: {phan[0]}")
        self.assertEqual(len(phan), 4, "v3 phải có 4 phần: v3$key_id$nonce$ct")
        key_id_hh = sp.nha_cung_cap().khoa_hien_hanh()[0]
        self.assertEqual(phan[1], key_id_hh)
        self.assertEqual(bao_mat.key_id_cua(g), key_id_hh)
        self.assertEqual(len(phan[2]), 24, "nonce phải 12 byte (96 bit) chuẩn GCM")
        self.assertEqual(bao_mat.giai_ma(g), "bi mat")

    def test_a2_bon_ham_contract_deu_ghi_v3(self):
        """Nếu contract còn ghi v2 thì secret mới KHÔNG xoay khóa được — phải bắt được ở đây."""
        bm, duoi = bao_mat.ma_hoa_cred({"api_key": CRED_KEY}, 7, "vtp")
        self.assertTrue(bm.startswith("v3$"), bm[:16])
        self.assertEqual(duoi, CRED_KEY[-4:])
        self.assertEqual(bao_mat.giai_ma_cred(bm, 7, "vtp")["api_key"], CRED_KEY)
        wh = bao_mat.ma_hoa_wh(SECRET_WH, "wh-abc")
        self.assertTrue(wh.startswith("v3$"), wh[:16])
        self.assertEqual(bao_mat.giai_ma_wh(wh, "wh-abc"), SECRET_WH)

    def test_a3_doc_duoc_ca_v1_v2_v3(self):
        ro = "ba định dạng — có dấu tiếng Việt"
        v1 = _ma_hoa_v1(ro)
        v2 = bao_mat.ma_hoa(ro)
        v3 = bao_mat.ma_hoa_v3(ro)
        self.assertFalse(v1.startswith("v"), "v1 không mang tiền tố")
        self.assertTrue(v2.startswith("v2$"))
        self.assertTrue(v3.startswith("v3$"))
        for nhan, g in (("v1", v1), ("v2", v2), ("v3", v3)):
            self.assertEqual(bao_mat.giai_ma(g), ro, f"không đọc được {nhan}")
        # la_dinh_dang_cu chỉ còn True với v1 (thứ migrate phải chuyển)
        self.assertTrue(bao_mat.la_dinh_dang_cu(v1))
        self.assertFalse(bao_mat.la_dinh_dang_cu(v2))
        self.assertFalse(bao_mat.la_dinh_dang_cu(v3))
        # key_id: chỉ v3 có
        self.assertIsNone(bao_mat.key_id_cua(v1))
        self.assertIsNone(bao_mat.key_id_cua(v2))
        self.assertIsNotNone(bao_mat.key_id_cua(v3))
        # can_xoay: v1 và v2 đều phải được coi là CẦN chuyển sang khóa hiện hành
        self.assertTrue(bao_mat.can_xoay(v1))
        self.assertTrue(bao_mat.can_xoay(v2))
        self.assertFalse(bao_mat.can_xoay(v3))

    def test_a4_v3_sai_cau_truc_thi_hong_chu_khong_doan(self):
        for xau in ("v3$chi-co-ba$phan", "v3$a$b$c$d"):
            with self.assertRaises(Exception, msg=f"chấp nhận bản mã rác: {xau}"):
                bao_mat.giai_ma(xau)


class B_HongKhiSaiKhoaSaiChoSuaByte(unittest.TestCase):
    """Ba cách tấn công: sai khóa · đổi chỗ bản mã · sửa một byte. Cả ba phải HỎNG."""

    def tearDown(self):
        sp.dat_nha_cung_cap(None)   # về nhà cung cấp mặc định sau mỗi ca

    def test_b1_sai_khoa_thi_giai_ma_hong(self):
        g = bao_mat.ma_hoa_v3("noi dung that", bao_mat.aad_credentials(1, "vtp"))
        key_id = bao_mat.key_id_cua(g)
        # Nhà cung cấp KHÁC: cùng key_id nhưng nội dung khóa khác hẳn
        thu_muc_khac = tempfile.mkdtemp(prefix="khoa-khac-")
        khac = sp.LocalSecretProvider(thu_muc=thu_muc_khac,
                                      duong_khoa_cu=os.path.join(thu_muc_khac, "khong-co.key"))
        khac._ghi_khoa(key_id, b"\x01" * 32)
        khac.dat_khoa_hien_hanh(key_id)
        sp.dat_nha_cung_cap(khac)
        with self.assertRaises(ValueError, msg="sai khóa mà vẫn giải được!"):
            bao_mat.giai_ma(g, bao_mat.aad_credentials(1, "vtp"))

    def test_b2_thieu_khoa_thi_bao_loi_chu_khong_sinh_khoa_moi(self):
        g = bao_mat.ma_hoa_v3("noi dung that")
        thu_muc_khac = tempfile.mkdtemp(prefix="khoa-trong-")
        khac = sp.LocalSecretProvider(thu_muc=thu_muc_khac,
                                      duong_khoa_cu=os.path.join(thu_muc_khac, "khong-co.key"))
        sp.dat_nha_cung_cap(khac)
        with self.assertRaises(sp.LoiKhoa):
            bao_mat.giai_ma(g)

    def test_b3_doi_cho_ban_ma_giua_hai_tenant_thi_hong(self):
        a = bao_mat.ma_hoa_cred({"api_key": "KEY-A"}, 1, "vtp")[0]
        b = bao_mat.ma_hoa_cred({"api_key": "KEY-B"}, 2, "vtp")[0]
        self.assertEqual(bao_mat.giai_ma_cred(a, 1, "vtp")["api_key"], "KEY-A")
        # chép bản mã của tenant 1 sang hàng của tenant 2 (và ngược lại) → phải hỏng
        with self.assertRaises(ValueError, msg="bản mã tenant 1 đọc được ở tenant 2!"):
            bao_mat.giai_ma_cred(a, 2, "vtp")
        with self.assertRaises(ValueError, msg="bản mã tenant 2 đọc được ở tenant 1!"):
            bao_mat.giai_ma_cred(b, 1, "vtp")
        # cùng tenant nhưng khác hãng cũng phải hỏng
        with self.assertRaises(ValueError):
            bao_mat.giai_ma_cred(a, 1, "jt")

    def test_b4_doi_cho_webhook_secret_giua_hai_account_thi_hong(self):
        w1 = bao_mat.ma_hoa_wh("secret-1", "wh-mot")
        w2 = bao_mat.ma_hoa_wh("secret-2", "wh-hai")
        self.assertEqual(bao_mat.giai_ma_wh(w1, "wh-mot"), "secret-1")
        with self.assertRaises(ValueError, msg="secret webhook A dùng được cho webhook B!"):
            bao_mat.giai_ma_wh(w1, "wh-hai")
        with self.assertRaises(ValueError):
            bao_mat.giai_ma_wh(w2, "wh-mot")

    def test_b5_sua_mot_byte_ban_ma_thi_hong(self):
        aad = bao_mat.aad_webhook("wh-byte")
        g = bao_mat.ma_hoa_v3("x" * 40, aad)
        v3, key_id, nonce, ct = g.split("$")
        # đổi ĐÚNG MỘT nửa byte ở từng vị trí: đầu, giữa, cuối của ciphertext
        for vt in (0, len(ct) // 2, len(ct) - 1):
            moi = "e" if ct[vt] != "e" else "d"
            hong = "$".join([v3, key_id, nonce, ct[:vt] + moi + ct[vt + 1:]])
            with self.assertRaises(ValueError, msg=f"sửa byte ở vị trí {vt} mà vẫn giải được!"):
                bao_mat.giai_ma(hong, aad)
        # sửa nonce cũng phải hỏng
        hong_nonce = "$".join([v3, key_id, ("0" if nonce[0] != "0" else "1") + nonce[1:], ct])
        with self.assertRaises(ValueError):
            bao_mat.giai_ma(hong_nonce, aad)


class C_SecretProvider(unittest.TestCase):
    def test_c1_di_cu_khoa_cu_thanh_key_id_dau_tien(self):
        """Khóa cũ `khoa-noi-bo.key` phải thành key_id 'goc' và GIỮ NGUYÊN file cũ.

        Xóa hay di chuyển file cũ = mất mọi bản mã v1/v2 (chúng không mang key_id).
        """
        thu_muc = tempfile.mkdtemp(prefix="di-cu-")
        duong_cu = os.path.join(thu_muc, "khoa-noi-bo.key")
        with open(duong_cu, "wb") as f:
            f.write(b"\x07" * 32)
        p = sp.LocalSecretProvider(thu_muc=os.path.join(thu_muc, "khoa"), duong_khoa_cu=duong_cu)
        key_id, khoa = p.khoa_hien_hanh()
        self.assertEqual(key_id, sp.KEY_ID_CU)
        self.assertEqual(khoa, b"\x07" * 32, "khóa di cư không giữ đúng nội dung")
        self.assertTrue(os.path.exists(duong_cu), "file khóa cũ bị mất → mất bản mã v1/v2")
        self.assertEqual(p.danh_sach_key_id(), [sp.KEY_ID_CU])

    def test_c2_quyen_file_khoa_la_0600(self):
        thu_muc = tempfile.mkdtemp(prefix="quyen-")
        p = sp.LocalSecretProvider(thu_muc=os.path.join(thu_muc, "khoa"),
                                   duong_khoa_cu=os.path.join(thu_muc, "cu.key"))
        kid = p.tao_khoa_moi()
        duong = p._duong(kid)
        self.assertEqual(oct(os.stat(duong).st_mode & 0o777), "0o600",
                         "file khóa không phải 0600 — người khác trên máy đọc được")
        self.assertEqual(len(p.lay_khoa(kid)), 32, "khóa phải 32 byte cho AES-256")

    def test_c3_khoa_cua_he_that_cung_la_0600(self):
        """Đo trên thư mục khóa THẬT của tiến trình này, không chỉ trên thư mục dựng riêng."""
        p = sp.nha_cung_cap()
        kid, _ = p.khoa_hien_hanh()
        self.assertEqual(oct(os.stat(p._duong(kid)).st_mode & 0o777), "0o600")

    def test_c4_key_id_khong_the_chua_ky_tu_pha_dinh_dang(self):
        """key_id lọt '$' hoặc '/' là phá được định dạng bản mã và lối ghi file."""
        for xau in ("co$dola", "../thoat-thu-muc", "co/gach", "", "CHU-HOA", "a" * 80):
            with self.assertRaises(sp.LoiKhoa, msg=f"chấp nhận key_id xấu: {xau!r}"):
                sp.kiem_key_id(xau)

    def test_c5_kms_chi_la_giao_dien(self):
        k = sp.KMSSecretProvider()
        for ham, doi in (("lay_khoa", ("k1",)), ("khoa_hien_hanh", ()),
                         ("danh_sach_key_id", ()), ("tao_khoa_moi", ()),
                         ("dat_khoa_hien_hanh", ("k1",))):
            with self.assertRaises(NotImplementedError, msg=f"KMS.{ham} đã triển khai?"):
                getattr(k, ham)(*doi)

    def test_c6_lop_nen_bat_lop_con_cai_du_ham(self):
        nen = sp.SecretProvider()
        for ham, doi in (("lay_khoa", ("k",)), ("khoa_hien_hanh", ()), ("danh_sach_key_id", ())):
            with self.assertRaises(NotImplementedError):
                getattr(nen, ham)(*doi)


class D_XoayKhoa(unittest.TestCase):
    """Xoay khóa thật trên CSDL thật của bộ thử."""

    @classmethod
    def setUpClass(cls):
        csdl.mo()
        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT OR IGNORE INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        cls.tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('t-xoay','T','pro',?)",
                           (csdl.bay_gio(),)).lastrowid
        cls.tid2 = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('t-xoay2','T2','pro',?)",
                            (csdl.bay_gio(),)).lastrowid

    @classmethod
    def tearDownClass(cls):
        csdl.dong()

    def _tai_khoan(self, tid, hang, wh_ma, cred_key, wh_secret):
        cred_mh, duoi = bao_mat.ma_hoa_cred({"api_key": cred_key}, tid, hang)
        return csdl.ghi(
            "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
            "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
            (tid, hang, "TK " + wh_ma, "mock", cred_mh, duoi, wh_ma,
             bao_mat.ma_hoa_wh(wh_secret, wh_ma), csdl.bay_gio())).lastrowid

    def test_d1_xoay_xong_van_doc_duoc_du_lieu_cu_va_moi_ban_ma_mang_key_id_moi(self):
        tk1 = self._tai_khoan(self.tid, "vtp", "wh-xoay-1", CRED_KEY, SECRET_WH)
        tk2 = self._tai_khoan(self.tid2, "jt", "wh-xoay-2", "KEY-TK2-4455", "SECRET-TK2-8899")
        key_id_truoc = sp.nha_cung_cap().khoa_hien_hanh()[0]
        so_khoa_truoc = len(sp.nha_cung_cap().danh_sach_key_id())

        kq = bao_mat.xoay_khoa()

        self.assertEqual(kq["hong"], [], f"xoay khóa có hàng hỏng: {kq['hong']}")
        self.assertNotEqual(kq["key_id"], key_id_truoc, "key_id không đổi → chưa xoay gì")
        self.assertEqual(kq["key_id_cu"], key_id_truoc)
        # Khóa CŨ phải còn — bản mã nào chưa chuyển thì còn cần nó
        self.assertIn(key_id_truoc, sp.nha_cung_cap().danh_sach_key_id(),
                      "khóa cũ bị xóa — bản mã chưa chuyển sẽ MẤT")
        self.assertEqual(len(sp.nha_cung_cap().danh_sach_key_id()), so_khoa_truoc + 1)

        # 1) dữ liệu cũ vẫn đọc được đúng nội dung
        for tk, tid, hang, wh_ma, ck, ws in ((tk1, self.tid, "vtp", "wh-xoay-1", CRED_KEY, SECRET_WH),
                                             (tk2, self.tid2, "jt", "wh-xoay-2", "KEY-TK2-4455",
                                              "SECRET-TK2-8899")):
            r = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (tk,))
            self.assertEqual(bao_mat.giai_ma_cred(r["credentials_ma_hoa"], tid, hang)["api_key"], ck)
            self.assertEqual(bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], wh_ma), ws)
            # 2) mọi bản mã mang key_id MỚI
            self.assertEqual(bao_mat.key_id_cua(r["credentials_ma_hoa"]), kq["key_id"])
            self.assertEqual(bao_mat.key_id_cua(r["webhook_secret_ma_hoa"]), kq["key_id"])
            self.assertFalse(bao_mat.can_xoay(r["credentials_ma_hoa"]))
            self.assertFalse(bao_mat.can_xoay(r["webhook_secret_ma_hoa"]))
        self.assertGreaterEqual(kq["so_credentials"], 2)
        self.assertGreaterEqual(kq["so_webhook_secret"], 2)

    def test_d2_xoay_khoa_phu_ca_ban_ma_v1_va_v2(self):
        """Hàng còn ở định dạng cũ cũng phải được chuyển, không bị bỏ sót im lặng."""
        cu_v1 = _ma_hoa_v1(json.dumps({"api_key": "KEY-V1-0001"}))
        cu_v2 = bao_mat.ma_hoa("SECRET-V2-0002", bao_mat.aad_webhook("wh-cu-dinh-dang"))
        tk = csdl.ghi(
            "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
            "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
            (self.tid, "vtp", "TK định dạng cũ", "mock", cu_v1, "0001", "wh-cu-dinh-dang",
             cu_v2, csdl.bay_gio())).lastrowid
        kq = bao_mat.xoay_khoa()
        self.assertEqual(kq["hong"], [], kq["hong"])
        r = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (tk,))
        self.assertEqual(bao_mat.key_id_cua(r["credentials_ma_hoa"]), kq["key_id"])
        self.assertEqual(bao_mat.key_id_cua(r["webhook_secret_ma_hoa"]), kq["key_id"])
        self.assertEqual(bao_mat.giai_ma_cred(r["credentials_ma_hoa"], self.tid, "vtp")["api_key"],
                         "KEY-V1-0001")
        self.assertEqual(bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], "wh-cu-dinh-dang"),
                         "SECRET-V2-0002")

    def test_d3_hang_hong_duoc_bao_ra_chu_khong_lam_no_ca_luot(self):
        tk_tot = self._tai_khoan(self.tid, "vtp", "wh-tot", "KEY-TOT-1111", "SECRET-TOT")
        tk_hong = csdl.ghi(
            "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
            "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
            (self.tid, "vtp", "TK rác", "mock", "rac-khong-giai-duoc", "", "wh-rac",
             "rac-nua", csdl.bay_gio())).lastrowid
        kq = bao_mat.xoay_khoa()
        self.assertTrue(any(f"carrier_account {tk_hong}" in x for x in kq["hong"]),
                        f"hàng rác không được báo ra: {kq['hong']}")
        self.assertEqual(len([x for x in kq["hong"] if f"carrier_account {tk_tot} " in x]), 0)
        # hàng tốt vẫn chuyển được dù có hàng rác
        r = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (tk_tot,))
        self.assertEqual(bao_mat.key_id_cua(r["credentials_ma_hoa"]), kq["key_id"])
        # audit phải ghi ket_qua that_bai khi có hàng hỏng — không báo đạt khi chưa đạt
        au = csdl.mot("SELECT * FROM audit WHERE hanh_dong='xoay_khoa_ma_hoa' ORDER BY id DESC LIMIT 1")
        self.assertEqual(au["ket_qua"], "that_bai")

    def test_d4_secret_khong_lot_vao_audit_hay_log(self):
        """Secret và nội dung khóa KHÔNG được xuất hiện ở audit, ở log, hay ở cột bản mã."""
        self._tai_khoan(self.tid2, "vtp", "wh-kin", CRED_KEY, SECRET_WH)
        tu_cam = [CRED_KEY, SECRET_WH]
        kq = bao_mat.xoay_khoa(user_id=None)

        # 1) toàn bộ bảng audit
        van_ban_audit = "\n".join(
            "|".join("" if v is None else str(v) for v in tuple(r))
            for r in csdl.nhieu("SELECT * FROM audit"))
        for t in tu_cam:
            self.assertNotIn(t, van_ban_audit, f"secret '{t[:8]}…' lọt vào audit!")
        self.assertIn("xoay_khoa_ma_hoa", van_ban_audit, "xoay khóa mà không ghi audit")
        # nội dung khóa (dạng hex) cũng không được nằm trong audit
        self.assertNotIn(sp.nha_cung_cap().lay_khoa(kq["key_id"]).hex(), van_ban_audit)

        # 2) kết quả trả về của xoay_khoa (thứ hay bị in ra màn hình/log)
        for t in tu_cam:
            self.assertNotIn(t, json.dumps(kq, ensure_ascii=False))

        # 3) cột bản mã trong CSDL
        for r in csdl.nhieu("SELECT credentials_ma_hoa, webhook_secret_ma_hoa FROM carrier_accounts"):
            for t in tu_cam:
                self.assertNotIn(t, r["credentials_ma_hoa"])
                self.assertNotIn(t, r["webhook_secret_ma_hoa"])

        # 4) thông báo lỗi khi giải mã hỏng không được chứa bản mã hay secret
        try:
            bao_mat.giai_ma_wh(bao_mat.ma_hoa_wh(SECRET_WH, "wh-a"), "wh-b")
            self.fail("đổi chỗ webhook mà không hỏng")
        except ValueError as e:
            for t in tu_cam:
                self.assertNotIn(t, str(e))


class E_MigrateV4(unittest.TestCase):
    def test_e1_migrate_v4_dua_moi_secret_sang_v3(self):
        """Dựng CSDL ở schema v3 (bản mã v2) rồi chạy nâng cấp v4 trong TIẾN TRÌNH CON thật."""
        import shutil
        thu_muc = tempfile.mkdtemp(prefix="migrate-v4-")
        # Dựng CSDL bằng chính csdl.py trong tiến trình con để không giẫm vào CSDL của bộ thử
        ma_dung = (
            "import os,sys,json\n"
            f"sys.path.insert(0, {GOC_APP!r})\n"
            f"os.environ['VIP_HUB_DATA']={thu_muc!r}\n"
            "import csdl, quyen, bao_mat, khoi_tao, adapter_vtp, adapter_jt\n"
            "csdl.mo(); quyen.seed(); khoi_tao.seed_providers()\n"
            "csdl.ghi(\"INSERT INTO schema_version (phien_ban, ap_dung_luc) VALUES (3,?)\", (csdl.bay_gio(),))\n"
            "tid=csdl.ghi(\"INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('tm','TM','pro',?)\","
            " (csdl.bay_gio(),)).lastrowid\n"
            "cred=bao_mat.ma_hoa(json.dumps({'api_key':'KEY-MIG-3344'}), bao_mat.aad_credentials(tid,'vtp'))\n"
            "wh=bao_mat.ma_hoa('SECRET-MIG-5566', bao_mat.aad_webhook('wh-mig'))\n"
            "assert cred.startswith('v2$') and wh.startswith('v2$')\n"
            "tk=csdl.ghi(\"INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,"
            "credentials_ma_hoa,credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)"
            " VALUES (?,?,?,?,?,?,?,?,?)\", (tid,'vtp','TK','mock',cred,'3344','wh-mig',wh,"
            " csdl.bay_gio())).lastrowid\n"
            "print(json.dumps({'tid':tid,'tk':tk}))\n")
        r = subprocess.run([sys.executable, "-c", ma_dung], capture_output=True, text=True,
                           cwd=GOC_APP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        ids = json.loads(r.stdout.strip().splitlines()[-1])

        # Chạy migrate thật
        mt = dict(os.environ, VIP_HUB_DATA=thu_muc)
        r2 = subprocess.run([sys.executable, os.path.join(GOC_APP, "migrate.py")],
                            capture_output=True, text=True, env=mt, cwd=os.path.dirname(GOC_APP))
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        self.assertIn("bảo toàn ĐẠT", r2.stdout)
        # Secret KHÔNG được in ra màn hình migrate
        self.assertNotIn("KEY-MIG-3344", r2.stdout + r2.stderr)
        self.assertNotIn("SECRET-MIG-5566", r2.stdout + r2.stderr)

        # Kiểm trong tiến trình con khác: bản mã đã là v3 và đọc lại đúng nội dung
        ma_kiem = (
            "import os,sys,json\n"
            f"sys.path.insert(0, {GOC_APP!r})\n"
            f"os.environ['VIP_HUB_DATA']={thu_muc!r}\n"
            "import csdl, bao_mat\n"
            "csdl.mo()\n"
            f"r=csdl.mot('SELECT * FROM carrier_accounts WHERE id=?', ({ids['tk']},))\n"
            "print(json.dumps({'pb':csdl.phien_ban_hien_tai(),"
            " 'kid_cred':bao_mat.key_id_cua(r['credentials_ma_hoa']),"
            " 'kid_wh':bao_mat.key_id_cua(r['webhook_secret_ma_hoa']),"
            f" 'cred':bao_mat.giai_ma_cred(r['credentials_ma_hoa'], {ids['tid']}, 'vtp'),"
            " 'wh':bao_mat.giai_ma_wh(r['webhook_secret_ma_hoa'], 'wh-mig')}))\n")
        r3 = subprocess.run([sys.executable, "-c", ma_kiem], capture_output=True, text=True,
                            cwd=GOC_APP)
        self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)
        kq = json.loads(r3.stdout.strip().splitlines()[-1])
        self.assertEqual(kq["pb"], csdl.PHIEN_BAN_SCHEMA)
        self.assertIsNotNone(kq["kid_cred"], "migrate v4 không đưa credentials sang v3")
        self.assertIsNotNone(kq["kid_wh"], "migrate v4 không đưa webhook secret sang v3")
        self.assertEqual(kq["cred"]["api_key"], "KEY-MIG-3344")
        self.assertEqual(kq["wh"], "SECRET-MIG-5566")
        shutil.rmtree(thu_muc, ignore_errors=True)


class F_KhongTutVeSoDoYeu(unittest.TestCase):
    def test_f1_thieu_cryptography_thi_nem_loi_that(self):
        """ĐO thật: chặn `cryptography` trong tiến trình con, `import bao_mat` phải ném ImportError.

        Không grep mã nguồn — grep chỉ nói mã có chữ 'raise', không nói nó có chạy hay không.
        """
        chan = tempfile.mkdtemp(prefix="chan-crypto-")
        # 'cryptography' thành MODULE rỗng → `from cryptography.hazmat...` hỏng ngay
        with open(os.path.join(chan, "cryptography.py"), "w", encoding="utf-8") as f:
            f.write("# module rỗng để chặn thư viện thật\n")
        ma = ("import sys\n"
              f"sys.path.insert(0, {chan!r})\n"
              f"sys.path.insert(1, {GOC_APP!r})\n"
              "import os\n"
              f"os.environ['VIP_HUB_DATA']={_tam!r}\n"
              "try:\n"
              "    import bao_mat\n"
              "except ImportError as e:\n"
              "    print('IMPORTERROR:' + str(e)); sys.exit(0)\n"
              "print('KHONG_NEM_LOI: bao_mat import được dù thiếu cryptography'); sys.exit(1)\n")
        r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True, cwd=GOC_APP)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("IMPORTERROR:", r.stdout)
        self.assertIn("CỐ Ý không chạy tiếp bằng sơ đồ mã hóa yếu", r.stdout)

    def test_f2_khong_con_duong_ma_hoa_moi_bang_so_do_yeu(self):
        """Mọi hàm GHI bản mã mới đều phải ra v2/v3 (AES-GCM) — không hàm nào ra định dạng v1."""
        for ten in ("ma_hoa", "ma_hoa_v3"):
            g = getattr(bao_mat, ten)("thu")
            self.assertTrue(g.startswith(("v2$", "v3$")), f"{ten} ghi ra định dạng yếu: {g[:12]}")
        self.assertTrue(bao_mat.ma_hoa_cred({"a": "b"}, 1, "vtp")[0].startswith("v3$"))
        self.assertTrue(bao_mat.ma_hoa_wh("s", "w").startswith("v3$"))
        self.assertTrue(bao_mat.luu_credentials({"a": "b"})[0].startswith("v3$"))

    def test_f3_khoa_khong_nam_trong_csdl_va_khong_vao_git(self):
        # 1) khóa không nằm trong CSDL: không bảng/cột nào chứa nội dung khóa
        csdl.mo()
        khoa_hex = sp.nha_cung_cap().khoa_hien_hanh()[1].hex()
        for b in csdl.nhieu("SELECT name FROM sqlite_master WHERE type='table'"):
            for r in csdl.nhieu(f"SELECT * FROM {b['name']}"):
                self.assertNotIn(khoa_hex, "|".join("" if v is None else str(v) for v in tuple(r)),
                                 f"nội dung khóa nằm trong bảng {b['name']}!")
        # 2) khóa không vào git: git check-ignore phải chặn cả hai đường khóa
        goc_git = os.path.dirname(GOC_APP)
        for duong in (cau_hinh.DUONG_DAN_KHOA,
                      os.path.join(sp.THU_MUC_KHOA, "goc.key"),
                      os.path.join(sp.THU_MUC_KHOA, sp.TEN_FILE_TRO)):
            tuong_doi = os.path.relpath(
                os.path.join(GOC_APP, "du-lieu", os.path.relpath(duong, cau_hinh.THU_MUC_DU_LIEU)),
                goc_git)
            r = subprocess.run(["git", "check-ignore", "-q", tuong_doi],
                               cwd=goc_git, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"git KHÔNG chặn {tuong_doi} — khóa có thể lọt vào git")


class G_GiuNguyenContract(unittest.TestCase):
    """Bốn chữ ký contract có mã khác đang gọi — đổi là vỡ chỗ khác (docs/SHARED_CONTRACTS.md §3)."""

    def test_g1_du_bon_ham_dung_chu_ky(self):
        import inspect
        mong_doi = {
            "ma_hoa_cred": ["cred", "tenant_id", "hang"],
            "giai_ma_cred": ["ban_ma", "tenant_id", "hang"],
            "ma_hoa_wh": ["secret", "webhook_ma"],
            "giai_ma_wh": ["ban_ma", "webhook_ma"],
        }
        for ten, tham_so in mong_doi.items():
            ham = getattr(bao_mat, ten, None)
            self.assertTrue(callable(ham), f"mất hàm contract {ten}")
            thuc = list(inspect.signature(ham).parameters)
            self.assertEqual(thuc, tham_so, f"{ten} đổi chữ ký: {thuc}")

    def test_g2_ngu_canh_va_quyen_con_nguyen(self):
        self.assertTrue(callable(bao_mat.ngu_canh))
        self.assertTrue(callable(quyen.co_quyen))
        self.assertIn("TENANT_OWNER", quyen.CAP_DUOC)


if __name__ == "__main__":
    unittest.main(verbosity=2)
