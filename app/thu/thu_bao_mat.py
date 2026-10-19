# Bộ thử bảo mật — key_id / SecretProvider / xoay khóa (AG-01).
# Chạy: python3 app/thu/thu_bao_mat.py
#
# Nguyên tắc của bộ thử này (CLAUDE.md §12.1): mỗi khẳng định phải do MỘT phép đo thật tạo ra.
# Không grep mã nguồn để kết luận hành vi khi còn có thể đo hành vi. Riêng ca "thiếu thư viện
# cryptography" thì đo bằng TIẾN TRÌNH CON có sys.path bị chắn, chứ không đọc mã rồi đoán.
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-baomat-")
os.environ["VIP_HUB_DATA"] = _tam
# CỐ Ý không đặt VIP_HUB_RESET_TOKEN: các lớp H..L đo hệ ở ĐÚNG cấu hình MẶC ĐỊNH.
os.environ.pop("VIP_HUB_RESET_TOKEN", None)

import adapter          # noqa: E402
import adapter_jt       # noqa: E402,F401
import adapter_vtp      # noqa: E402,F401
import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import khoi_tao         # noqa: E402
import quyen            # noqa: E402
import sao_luu_khoa as skb      # noqa: E402
import secret_provider as sp   # noqa: E402
import server                  # noqa: E402
import webhook                 # noqa: E402

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# `migrate.chay()`/`sao_luu()` TỪ CHỐI khi chưa khai kho. Bộ thử tự khai bằng giao diện chung
# `cau_hinh.khai_kho_kiem_thu()` — KHÔNG dựa vào việc người chạy nhớ `export VIP_KHO_DANG_CHAY`.
# `VIP_HUB_DATA` đã trỏ thư mục TẠM ở trên, nên hai chốt cô lập của hàm khai đều thoả.
cau_hinh.khai_kho_kiem_thu()

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


# =======================================================================================
# S03 — SAO LƯU / KHÔI PHỤC KHÓA (AG-01)
# =======================================================================================
# DIỄN TẬP KHÔI PHỤC (restore drill) chạy TRONG bộ thử, trong thư mục tạm CÔ LẬP, và
# **không di chuyển, không xóa khóa gốc** ở bất kỳ ca nào. Mỗi khẳng định một phép đo:
#   - "khôi phục được" = giải mã THẬT một credentials thử bằng khóa vừa khôi phục.
#   - "không lộ secret" = quét BYTE THÔ của gói tìm khóa/plaintext ở ba dạng (thô/hex/base64).
#   - "toàn vẹn" = so sha256 từng khóa với giá trị ghi trong gói.
PASS_THU = "passphrase-dien-tap-rat-dai-2026"


def _du_lieu_khoa_co_lap(prefix):
    """Dựng MỘT bộ khóa trong thư mục tạm riêng + một nhà cung cấp trỏ vào đó.

    Dùng thư mục riêng để diễn tập không bao giờ chạm thư mục khóa đang chạy.
    """
    goc = tempfile.mkdtemp(prefix=prefix)
    t_khoa = os.path.join(goc, "khoa")
    d_cu = os.path.join(goc, "khoa-noi-bo.key")
    p = sp.LocalSecretProvider(thu_muc=t_khoa, duong_khoa_cu=d_cu)
    p._dam_bao_co_khoa()
    return goc, t_khoa, d_cu, p


class H_SaoLuuKhoa(unittest.TestCase):

    def tearDown(self):
        sp.dat_nha_cung_cap(None)

    # ---------- diễn tập đầy đủ ----------
    def test_h1_DIEN_TAP_backup_roi_khoi_phuc_roi_giai_ma_duoc(self):
        """Diễn tập: tạo khóa → mã hóa credentials → backup → khôi phục ở môi trường KHÁC →
        giải mã lại được. Đây là bằng chứng duy nhất đáng tin cho "có đường về"."""
        goc, t_khoa, d_cu, p_nguon = _du_lieu_khoa_co_lap("diental-nguon-")
        sp.dat_nha_cung_cap(p_nguon)
        key_id_moi = p_nguon.tao_khoa_moi()
        p_nguon.dat_khoa_hien_hanh(key_id_moi)
        bi_mat = "CRED-DIEN-TAP-" + base64.b16encode(os.urandom(6)).decode()
        ban_ma, _ = bao_mat.ma_hoa_cred({"api_key": bi_mat}, 42, "vtp")
        wh_ban_ma = bao_mat.ma_hoa_wh("WH-DIEN-TAP-" + bi_mat[-6:], "wh-dien-tap")
        self.assertEqual(bao_mat.key_id_cua(ban_ma), key_id_moi)

        goi = os.path.join(goc, "goi-dien-tap.vipkb")
        kq = skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                         gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        self.assertGreaterEqual(kq["so_khoa"], 2, f"phải gói CẢ khóa cũ và khóa mới: {kq}")
        self.assertIn(key_id_moi, kq["key_id"])
        self.assertEqual(kq["khoa_hien_hanh"], key_id_moi, "thiếu con trỏ khóa hiện hành")
        self.assertEqual(kq["quyen"], "0o600", f"gói backup phải 0600, đang {kq['quyen']}")

        # Toàn vẹn — kiểm TRƯỚC khi tin gói (CLAUDE.md §12.1)
        kt = skb.kiem_toan_ven(goi, passphrase=PASS_THU, cho_nhap=False)
        self.assertTrue(kt["dat"], f"gói không toàn vẹn: {kt['loi']}")

        # Khôi phục vào môi trường CÔ LẬP THỨ HAI
        goc2 = tempfile.mkdtemp(prefix="diental-dich-")
        t_khoa2, d_cu2 = os.path.join(goc2, "khoa"), os.path.join(goc2, "khoa-noi-bo.key")
        kp = skb.khoi_phuc(goi, t_khoa2, passphrase=PASS_THU, cho_nhap=False,
                           duong_khoa_cu_dich=d_cu2, ghi_audit=False)
        self.assertTrue(kp["dat"], f"khôi phục lỗi: {kp['loi']}")
        self.assertEqual(sorted(kp["da_ghi"]), sorted(kq["key_id"]))
        self.assertEqual(kp["con_tro_hien_hanh"], key_id_moi)

        # BẰNG CHỨNG: giải mã được bằng khóa vừa khôi phục, ở nhà cung cấp MỚI
        p_dich = sp.LocalSecretProvider(thu_muc=t_khoa2, duong_khoa_cu=d_cu2)
        sp.dat_nha_cung_cap(p_dich)
        self.assertEqual(bao_mat.giai_ma_cred(ban_ma, 42, "vtp")["api_key"], bi_mat)
        self.assertEqual(bao_mat.giai_ma_wh(wh_ban_ma, "wh-dien-tap"),
                         "WH-DIEN-TAP-" + bi_mat[-6:])
        self.assertEqual(p_dich.khoa_hien_hanh()[0], key_id_moi)

        # KHÔNG lộ secret: quét byte thô của gói
        lo = skb.kiem_khong_lo_secret(
            goi, [p_nguon.lay_khoa(k) for k in kq["key_id"]] + [bi_mat])
        self.assertTrue(lo["dat"], f"gói backup LỘ bí mật ở dạng {lo['dang_bi_lo']}")

        # KHÔNG di chuyển / không xóa khóa gốc
        for k in kq["key_id"]:
            self.assertTrue(os.path.exists(p_nguon._duong(k)), f"khóa gốc {k} đã biến mất!")
        self.assertTrue(os.path.exists(d_cu), "file khóa cũ gốc đã biến mất!")

    def test_h2_goi_bat_duoc_rang_buoc_tenant_va_hang(self):
        """Bản mã kèm `tenant_id`/`hang`/`webhook_ma` — đó là đầu vào dựng AAD, thiếu là
        khôi phục khóa xong vẫn không giải được."""
        csdl.mo()
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("rangbuoc-")
        goi = os.path.join(goc, "g.vipkb")
        skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                    gom_ban_ma=True, cho_nhap=False, ghi_audit=False)
        rb = skb.rang_buoc_ban_ma(goi, passphrase=PASS_THU, cho_nhap=False)
        self.assertTrue(rb, "CSDL có carrier_accounts mà gói không mang bản mã nào")
        for r in rb:
            for truong in ("tenant_id", "hang", "webhook_ma", "credentials_ma_hoa",
                           "webhook_secret_ma_hoa"):
                self.assertIn(truong, r, f"thiếu ràng buộc {truong}")
            # Và KHÔNG được chứa plaintext: credentials gốc là JSON, nên bản trong gói
            # tuyệt đối không được có dấu hiệu JSON hay chuỗi bí mật đã biết.
            bm = str(r["credentials_ma_hoa"] or "")
            self.assertTrue(bm, "bản mã credentials rỗng")
            for dau in ('{"', '"api_key"', CRED_KEY, SECRET_WH):
                self.assertNotIn(dau, bm, f"bản mã trong gói lộ plaintext ({dau!r})")

    def test_h3_passphrase_khong_duoc_la_chinh_khoa_dang_backup(self):
        """Luật cốt lõi của S03: bản backup phải được bảo vệ ĐỘC LẬP."""
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("passtrung-")
        khoa = p.khoa_hien_hanh()[1]
        goi = os.path.join(goc, "g.vipkb")
        for dang, gia_tri in (("hex", khoa.hex()),
                              ("base64", base64.b64encode(khoa).decode()),
                              ("byte thô", khoa)):
            with self.assertRaises(skb.LoiSaoLuu, msg=f"nhận passphrase = khóa dạng {dang}"):
                skb.tao_goi(goi, passphrase=gia_tri, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                            gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        self.assertFalse(os.path.exists(goi), "đã ghi gói ra đĩa trước khi kiểm passphrase")

    def test_h4_khong_tu_sinh_passphrase_thieu_thi_tu_choi(self):
        """Tự sinh rồi coi là xong = bí mật không ai giữ. Phải TỪ CHỐI."""
        cu = os.environ.pop(skb.BIEN_MT_PASS, None)
        try:
            with self.assertRaises(skb.LoiSaoLuu) as e:
                skb.lay_passphrase(None, cho_nhap=False)
            self.assertIn(skb.BIEN_MT_PASS, str(e.exception))
            # Ngắn và chuỗi giữ chỗ cũng bị từ chối
            with self.assertRaises(skb.LoiSaoLuu):
                skb.lay_passphrase("ngan", cho_nhap=False)
            with self.assertRaises(skb.LoiSaoLuu):
                skb.lay_passphrase("changeme", cho_nhap=False)
            # Lấy được từ biến môi trường
            os.environ[skb.BIEN_MT_PASS] = PASS_THU
            self.assertEqual(skb.lay_passphrase(None, cho_nhap=False), PASS_THU.encode())
        finally:
            os.environ.pop(skb.BIEN_MT_PASS, None)
            if cu is not None:
                os.environ[skb.BIEN_MT_PASS] = cu

    def test_h5_tu_choi_ghi_vao_thu_muc_static_dang_phuc_vu(self):
        """Gói backup trong `admin/ pages/ assets/ mock/` là tải về được bằng một GET vô danh."""
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("static-")
        goc_repo = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, os.pardir))
        for t in skb.THU_MUC_STATIC:
            with self.assertRaises(skb.LoiSaoLuu, msg=f"chấp nhận ghi vào {t}/"):
                skb.tao_goi(os.path.join(goc_repo, t, "khoa.vipkb"), passphrase=PASS_THU,
                            thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu, gom_ban_ma=False,
                            cho_nhap=False, ghi_audit=False)
            self.assertFalse(os.path.exists(os.path.join(goc_repo, t, "khoa.vipkb")))

    def test_h5b_danh_sach_static_khop_server(self):
        """Hai danh sách ở hai file — lệch nhau là lỗ hổng im lặng. So trực tiếp."""
        with open(os.path.join(GOC_APP, "server.py"), encoding="utf-8") as f:
            ma = f.read()
        import re as _re
        m = _re.search(r"THU_MUC_CHO_PHEP\s*=\s*\(([^)]*)\)", ma)
        self.assertIsNotNone(m, "không tìm thấy THU_MUC_CHO_PHEP trong server.py")
        cua_server = {x.strip().strip('\'"').rstrip("/") for x in m.group(1).split(",") if x.strip()}
        self.assertEqual(cua_server, set(skb.THU_MUC_STATIC),
                         "danh sách static của server.py và sao_luu_khoa.py đã LỆCH — "
                         "thư mục mới được phục vụ mà backup vẫn cho ghi vào đó")

    def test_h6_tu_choi_ghi_vao_cho_git_khong_chan_va_vao_thu_muc_khoa(self):
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("git-")
        goc_repo = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, os.pardir))
        duong_docs = os.path.join(goc_repo, "docs", "khoa.vipkb")
        with self.assertRaises(skb.LoiSaoLuu) as e:
            skb.tao_goi(duong_docs, passphrase=PASS_THU, thu_muc_khoa=t_khoa,
                        duong_khoa_cu=d_cu, gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        self.assertIn("git", str(e.exception).lower())
        # Và KHÔNG được để lại file nào. Bản đầu của `_kiem_duong_ra` dùng `isdir(.git)` nên
        # chốt chặn chết trong git worktree, và chính ca này đã GHI THẬT một gói khóa vào
        # `docs/khoa.vipkb` (phát hiện 15/10/2026 bằng `git status`). Đo luôn ở đây để lần sau
        # chốt chặn chết thì thấy ngay, không phải chờ ai nhìn `git status`.
        self.assertFalse(os.path.exists(duong_docs),
                         f"đã GHI gói khóa ra {duong_docs} dù lẽ ra phải từ chối")
        with self.assertRaises(skb.LoiSaoLuu):
            skb.tao_goi(os.path.join(sp.THU_MUC_KHOA, "k.vipkb"), passphrase=PASS_THU,
                        thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu, gom_ban_ma=False,
                        cho_nhap=False, ghi_audit=False)
        # Đuôi sai cũng từ chối (tránh gói bí mật mang tên trông như file thường)
        with self.assertRaises(skb.LoiSaoLuu):
            skb.tao_goi(os.path.join(goc, "khoa.txt"), passphrase=PASS_THU,
                        thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu, gom_ban_ma=False,
                        cho_nhap=False, ghi_audit=False)

    def test_h6b_khong_co_goi_backup_nao_lac_trong_repo(self):
        """Canh toàn repo: không file `.vipkb` nào được nằm trong cây mã nguồn.

        Ca này sinh ra vì chuyện đã xảy ra thật: `docs/khoa.vipkb` (một gói khóa HOÀN CHỈNH,
        mở được) nằm trong repo suốt mấy phút ngày 15/10/2026 vì chốt chặn gitignore hỏng. Một
        phép đo nhìn vào KẾT QUẢ trên đĩa, độc lập với mọi chốt chặn trong `_kiem_duong_ra`.
        """
        goc_repo = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, os.pardir))
        lac = []
        for goc, thu_muc, files in os.walk(goc_repo):
            thu_muc[:] = [t for t in thu_muc if t not in (".git", "__pycache__", "du-lieu")]
            lac += [os.path.join(goc, t) for t in files if t.endswith(skb.DUOI_GOI)]
        self.assertEqual(lac, [], f"gói backup khóa nằm trong repo: {lac}")

    def test_h7_sai_passphrase_hoac_sua_goi_thi_khong_mo_duoc(self):
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("sua-goi-")
        goi = os.path.join(goc, "g.vipkb")
        skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                    gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        with self.assertRaises(skb.LoiSaoLuu):
            skb.kiem_toan_ven(goi, passphrase=PASS_THU + "-sai", cho_nhap=False)
        # Sửa MỘT byte ciphertext → AES-GCM phát hiện
        with open(goi, "rb") as f:
            tho = bytearray(f.read())
        tho[-5] ^= 0x01
        goi2 = os.path.join(goc, "g-sua.vipkb")
        with open(goi2, "wb") as f:
            f.write(bytes(tho))
        with self.assertRaises(skb.LoiSaoLuu):
            skb.kiem_toan_ven(goi2, passphrase=PASS_THU, cho_nhap=False)

    def test_h8_ha_so_vong_pbkdf2_trong_header_thi_hong(self):
        """Header làm AAD: hạ `vong` xuống 1 để dò passphrase nhanh là giải mã HỎNG."""
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("vong-")
        goi = os.path.join(goc, "g.vipkb")
        skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                    gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        g = skb.doc_header(goi)
        h = dict(g["header"])
        h["vong"] = 1000
        hb = json.dumps(h, ensure_ascii=False, sort_keys=True).encode()
        import struct as _st
        goi2 = os.path.join(goc, "g-vong.vipkb")
        with open(goi2, "wb") as f:
            f.write(skb.MAGIC + _st.pack(">I", len(hb)) + hb + g["_ct"])
        with self.assertRaises(skb.LoiSaoLuu):
            skb.kiem_toan_ven(goi2, passphrase=PASS_THU, cho_nhap=False)
        # Và số vòng thấp bị từ chối ngay ở hàm dẫn xuất
        with self.assertRaises(skb.LoiSaoLuu):
            skb._dan_xuat(b"x" * 20, b"y" * 16, 10)

    def test_h9_khoi_phuc_khong_ghi_de_khoa_dang_co_khi_chua_cho_phep(self):
        """Ghi đè khóa đang dùng bằng khóa trong gói CŨ là mất dữ liệu đã mã hóa bằng khóa mới."""
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("ghide-")
        goi = os.path.join(goc, "g.vipkb")
        kq = skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                         gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        key_id = kq["key_id"][0]
        # Thay nội dung khóa ở ĐÍCH để thấy rõ có bị ghi đè hay không
        dich = os.path.join(goc, "dich")
        os.makedirs(dich, exist_ok=True)
        duong_dich = os.path.join(dich, key_id + sp.DUOI_KHOA)
        with open(duong_dich, "wb") as f:
            f.write(b"\x07" * 32)
        kp = skb.khoi_phuc(goi, dich, passphrase=PASS_THU, cho_nhap=False, ghi_audit=False)
        self.assertIn(key_id, kp["bo_qua"], f"đã ghi đè khóa đang có: {kp}")
        with open(duong_dich, "rb") as f:
            self.assertEqual(f.read(), b"\x07" * 32, "nội dung khóa ở đích đã bị ghi đè")
        # ghi_de=True thì ghi, và chỉ khi người gọi nói ra
        kp2 = skb.khoi_phuc(goi, dich, passphrase=PASS_THU, cho_nhap=False, ghi_de=True,
                            ghi_audit=False)
        self.assertIn(key_id, kp2["da_ghi"])

    def test_h10_thu_muc_khoa_rong_thi_tu_choi_chu_khong_bao_dat(self):
        rong = os.path.join(tempfile.mkdtemp(prefix="rong-"), "khoa")
        os.makedirs(rong, exist_ok=True)
        with self.assertRaises(skb.LoiSaoLuu) as e:
            skb.tao_goi(os.path.join(os.path.dirname(rong), "g.vipkb"), passphrase=PASS_THU,
                        thu_muc_khoa=rong, duong_khoa_cu=os.path.join(rong, "khong-co.key"),
                        gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        self.assertIn("không thấy khóa nào", str(e.exception))

    def test_h11_header_doc_duoc_khong_can_passphrase_va_khong_chua_bi_mat(self):
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("header-")
        goi = os.path.join(goc, "g.vipkb")
        kq = skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                         gom_ban_ma=False, cho_nhap=False, ghi_audit=False)
        h = skb.doc_header(goi)["header"]
        self.assertEqual(h["so_khoa"], kq["so_khoa"])
        self.assertGreaterEqual(h["vong"], 100_000, "số vòng PBKDF2 quá thấp")
        tho_header = json.dumps(h, ensure_ascii=False).encode()
        for k in kq["key_id"]:
            kb = p.lay_khoa(k)
            for x in (kb, kb.hex().encode(), base64.b64encode(kb)):
                self.assertNotIn(x, tho_header, "header chứa nội dung khóa!")
        self.assertNotIn(PASS_THU.encode(), tho_header, "header chứa passphrase!")

    def test_h12_goi_thieu_khoa_cua_ban_ma_thi_BAO_RA(self):
        """Gói đủ khóa nhưng thiếu đúng khóa mà bản mã đang dùng = khôi phục xong vẫn mất dữ
        liệu. Phải báo ở bước KIỂM, không để phát hiện lúc cần tới."""
        csdl.mo()
        goc, t_khoa, d_cu, p = _du_lieu_khoa_co_lap("thieu-khoa-")
        goi = os.path.join(goc, "g.vipkb")
        skb.tao_goi(goi, passphrase=PASS_THU, thu_muc_khoa=t_khoa, duong_khoa_cu=d_cu,
                    gom_ban_ma=True, cho_nhap=False, ghi_audit=False)
        # Gói trên có khóa 'goc'; CSDL thật đang có bản mã dưới khóa nào thì tùy, nên ở đây
        # dựng một gói GIẢ có bản mã trỏ key_id không tồn tại rồi kiểm.
        p_goi, h = skb._mo_goi(goi, PASS_THU, cho_nhap=False)
        p_goi["ban_ma"] = [{"bang": "carrier_accounts", "id": 1, "tenant_id": 1, "hang": "vtp",
                            "webhook_ma": "w", "credentials_duoi": "0000",
                            "credentials_ma_hoa": "v3$k-khong-ton-tai$aa$bb",
                            "webhook_secret_ma_hoa": "v3$k-khong-ton-tai$aa$bb"}]
        goi2 = _ghi_goi_tay(os.path.join(goc, "gia.vipkb"), p_goi, PASS_THU)
        kt = skb.kiem_toan_ven(goi2, passphrase=PASS_THU, cho_nhap=False)
        self.assertFalse(kt["dat"])
        self.assertIn("k-khong-ton-tai", kt["key_id_thieu"])


def _ghi_goi_tay(duong, payload, passphrase):
    """Dựng một gói backup từ payload cho trước — chỉ dùng trong bộ thử để tạo ca xấu."""
    import gzip as _gz
    import secrets as _s
    import struct as _st
    ro = _gz.compress(json.dumps(payload, ensure_ascii=False).encode(), 9)
    salt, nonce = _s.token_bytes(16), _s.token_bytes(12)
    header = {"magic": "VIPHUBKEYBAK", "phien_ban": skb.PHIEN_BAN_GOI,
              "tao_luc": payload["tao_luc"], "kdf": "pbkdf2-hmac-sha256",
              "vong": 200_000, "salt_hex": salt.hex(), "nonce_hex": nonce.hex(),
              "ma_hoa": "aes-256-gcm", "nen": "gzip", "so_khoa": len(payload["khoa"]),
              "khoa_hien_hanh": payload["khoa_hien_hanh"], "so_ban_ma": len(payload["ban_ma"]),
              "sha256_ro": hashlib.sha256(ro).hexdigest()}
    hb = json.dumps(header, ensure_ascii=False, sort_keys=True).encode()
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _A
    kek = skb._dan_xuat(passphrase.encode(), salt, 200_000)
    with open(duong, "wb") as f:
        f.write(skb.MAGIC + _st.pack(">I", len(hb)) + hb + _A(kek).encrypt(nonce, ro, hb))
    return duong


# =======================================================================================
# Nền HTTP dùng chung cho các lớp I / J (S01, S02) — cổng RIÊNG của AG-01
# =======================================================================================
CONG_AG01 = 18921
URL = f"http://127.0.0.1:{CONG_AG01}"
MK_THU = "MatKhauThuAG01-123"


class Khach:
    """Client HTTP nhỏ, viết riêng cho bộ này (không chép của AG-07)."""

    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, csrf=True):
        body = json.dumps(du_lieu).encode() if du_lieu is not None else None
        h = dict(headers or {})
        if csrf and method in ("POST", "PUT", "DELETE"):
            h.setdefault("X-Requested-With", "VIPHub")
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(URL + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=30) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                raw = ph.read()
                ct = ph.headers.get("Content-Type", "")
                return ph.status, (json.loads(raw) if "json" in ct else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw


class _NenHttp(unittest.TestCase):
    _sv = None

    @classmethod
    def setUpClass(cls):
        if _NenHttp._sv is None:
            csdl.mo()
            quyen.seed()
            khoi_tao.seed_providers()
            webhook.khoi_dong()
            try:
                _NenHttp._sv = server.ThreadingHTTPServer(("127.0.0.1", CONG_AG01), server.BoXuLy)
            except OSError as e:
                raise unittest.SkipTest(
                    f"cổng {CONG_AG01} đang bận ({e}) — CỔNG BẬN, không phải test hỏng. "
                    "Chạy lại khi phiên khác nhả cổng.") from e
            threading.Thread(target=_NenHttp._sv.serve_forever, daemon=True).start()
            csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role,"
                     " tao_luc) VALUES ('ag01-po', ?, 'Chủ nền tảng AG-01', 'PLATFORM_OWNER', ?)",
                     (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
            csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role,"
                     " tao_luc) VALUES ('ag01-nan-nhan', ?, 'Nạn nhân', 'PLATFORM_OWNER', ?)",
                     (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))


class I_TokenReset(_NenHttp):
    """S01 — token đặt lại mật khẩu. Sáu tính chất, mỗi tính chất một phép đo."""

    def test_i1_mac_dinh_KHONG_tra_token_cho_nguoi_vo_danh(self):
        """Lỗ hổng cũ: người VÔ DANH gọi /auth/quen-mat-khau nhận token hợp lệ rồi chiếm tài khoản."""
        self.assertFalse(cau_hinh.HIEN_TOKEN_RESET,
                         "HIEN_TOKEN_RESET phải TẮT khi không đặt VIP_HUB_RESET_TOKEN")
        k = Khach()
        st, kq = k.goi("/api/v2/auth/quen-mat-khau", "POST",
                       {"ten_dang_nhap": "ag01-po"})
        self.assertEqual(st, 200)
        tho = json.dumps(kq, ensure_ascii=False)
        for truong in ("token_gia_lap", "token", "reset"):
            self.assertNotIn(truong, kq, f"phản hồi lộ trường {truong}: {tho}")
        # Và không có chuỗi nào dài trông như token trong phản hồi
        for v in kq.values():
            self.assertLess(len(str(v)), 120, f"phản hồi chứa chuỗi dài đáng ngờ: {tho}")

    def test_i2_khong_lo_tai_khoan_nao_co_that(self):
        k = Khach()
        a = k.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "ag01-po"})
        b = k.goi("/api/v2/auth/quen-mat-khau", "POST",
                  {"ten_dang_nhap": "khong-he-ton-tai-xyz"})
        self.assertEqual(a, b, "phản hồi khác nhau → dò được tài khoản nào có thật")

    def test_i3_token_het_han_thi_khong_dung_duoc(self):
        tk = bao_mat.tao_token_reset("ag01-nan-nhan")
        self.assertIsNotNone(tk)
        csdl.ghi("UPDATE reset_tokens SET het_han='2000-01-01 00:00:00' WHERE token_hash=?",
                 (bao_mat._hash_token(tk),))
        ok, ly_do = bao_mat.dat_lai_mat_khau(tk, "MatKhauMoi-123")
        self.assertFalse(ok)
        self.assertIn("hết hạn", ly_do)
        # Mật khẩu KHÔNG bị đổi
        u = csdl.mot("SELECT mat_khau_hash FROM users WHERE ten_dang_nhap='ag01-nan-nhan'")
        self.assertTrue(bao_mat.kiem_mat_khau(MK_THU, u["mat_khau_hash"]))

    def test_i4_token_dung_MOT_lan_va_chong_replay(self):
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-i4', ?, 'i4', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        tk = bao_mat.tao_token_reset("ag01-i4")
        ok, _ = bao_mat.dat_lai_mat_khau(tk, "MatKhauLan1-123")
        self.assertTrue(ok)
        # REPLAY: gửi lại ĐÚNG token đó
        for lan in range(3):
            ok2, ly_do = bao_mat.dat_lai_mat_khau(tk, "MatKhauLan2-999")
            self.assertFalse(ok2, f"replay lần {lan + 1} vẫn đổi được mật khẩu!")
            self.assertIn("đã dùng", ly_do)
        u = csdl.mot("SELECT mat_khau_hash FROM users WHERE ten_dang_nhap='ag01-i4'")
        self.assertTrue(bao_mat.kiem_mat_khau("MatKhauLan1-123", u["mat_khau_hash"]),
                        "replay đã ghi đè mật khẩu")

    def test_i5_doi_mat_khau_xong_thi_token_cu_het_hieu_luc(self):
        """Kẻ xấu xin token; chính chủ tự đổi mật khẩu; token cũ PHẢI chết."""
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-i5', ?, 'i5', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        tk_ke_xau = bao_mat.tao_token_reset("ag01-i5")
        time.sleep(1.1)                       # mốc tính theo giây — tách hai mốc ra rõ ràng
        k = Khach()
        st, _ = k.goi("/api/v2/auth/dang-nhap", "POST",
                      {"ten_dang_nhap": "ag01-i5", "mat_khau": MK_THU})
        self.assertEqual(st, 200)
        st, kq = k.goi("/api/v2/auth/doi-mat-khau", "POST",
                       {"mat_khau_cu": MK_THU, "mat_khau_moi": "ChinhChuDoi-123"})
        self.assertEqual(st, 200, kq)
        ok, ly_do = bao_mat.dat_lai_mat_khau(tk_ke_xau, "KeXauChiem-123")
        self.assertFalse(ok, "token sinh TRƯỚC lần đổi mật khẩu vẫn dùng được → chiếm tài khoản")
        u = csdl.mot("SELECT mat_khau_hash FROM users WHERE ten_dang_nhap='ag01-i5'")
        self.assertTrue(bao_mat.kiem_mat_khau("ChinhChuDoi-123", u["mat_khau_hash"]))

    def test_i6_dat_lai_mat_khau_thu_hoi_moi_phien_cu(self):
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-i6', ?, 'i6', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        k = Khach()
        self.assertEqual(k.goi("/api/v2/auth/dang-nhap", "POST",
                               {"ten_dang_nhap": "ag01-i6", "mat_khau": MK_THU})[0], 200)
        self.assertEqual(k.goi("/api/v2/auth/toi")[0], 200)
        tk = bao_mat.tao_token_reset("ag01-i6")
        self.assertTrue(bao_mat.dat_lai_mat_khau(tk, "SauKhiDatLai-123")[0])
        st, _ = k.goi("/api/v2/auth/toi")
        self.assertEqual(st, 401, "phiên cũ còn sống sau khi đặt lại mật khẩu")

    def test_i7_token_la_bam_trong_csdl_khong_luu_tho(self):
        """CSDL bị đọc thì token cũng không dùng lại được."""
        tk = bao_mat.tao_token_reset("ag01-nan-nhan")
        r = csdl.mot("SELECT * FROM reset_tokens WHERE token_hash=?",
                     (hashlib.sha256(tk.encode()).hexdigest(),))
        self.assertIsNotNone(r, "token không được băm bằng sha256 như mong đợi")
        for b in csdl.nhieu("SELECT name FROM sqlite_master WHERE type='table'"):
            for row in csdl.nhieu(f"SELECT * FROM {b['name']}"):
                self.assertNotIn(tk, "|".join("" if v is None else str(v) for v in tuple(row)),
                                 f"token THÔ nằm trong bảng {b['name']}")


class J_StaticKhongPhucVuBiMat(_NenHttp):
    """S02 — static chỉ phục vụ `admin/ pages/ assets/ mock/`. Mọi đường khác phải 404."""

    DUONG_PHAI_CHAN = [
        "/app/bao_mat.py", "/app/server.py", "/app/cau_hinh.py", "/app/secret_provider.py",
        "/app/gioi_han.py", "/app/sao_luu_khoa.py", "/app/csdl.py",
        "/gateway/cau_hinh.py", "/gateway/may_chu.py",
        "/app/du-lieu/hub.db", "/app/du-lieu/khoa-noi-bo.key",
        "/app/du-lieu/khoa/goc.key", "/app/du-lieu/khoa/hien-hanh",
        "/app/du-lieu/TAI-KHOAN-DEMO.md",
        "/.env", "/app/.env", "/.git/config", "/.git/HEAD", "/.gitignore",
        "/docs/MA_HOA.md", "/docs/SHARED_CONTRACTS.md", "/README.md",
        "/khoa-backup.vipkb", "/app/du-lieu/khoa-backup.vipkb",
        "/gateway/Caddyfile", "/Caddyfile", "/nginx.conf",
        "/app/thu/thu_bao_mat.py", "/requirements.txt",
    ]

    def test_j1_khong_phuc_vu_ma_nguon_csdl_khoa_git_cau_hinh(self):
        k = Khach()
        lot = []
        for d in self.DUONG_PHAI_CHAN:
            st, _ = k.goi(d)
            if st == 200:
                lot.append(d)
        self.assertEqual(lot, [], f"static PHỤC VỤ các đường phải chặn: {lot}")

    def test_j2_khong_lach_duoc_bang_ma_hoa_url_hay_duong_vong(self):
        k = Khach()
        lot = []
        for d in ("/%2e%2e/app/bao_mat.py", "/admin/../app/bao_mat.py",
                  "/admin/..%2fapp%2fbao_mat.py", "/./app/bao_mat.py",
                  "/admin/./../app/cau_hinh.py", "//app/bao_mat.py",
                  "/app//bao_mat.py", "/APP/BAO_MAT.PY",
                  "/admin/index.html/../../app/bao_mat.py"):
            st, _ = k.goi(d)
            if st == 200:
                lot.append(d)
        self.assertEqual(lot, [], f"lách được danh sách trắng qua: {lot}")

    def test_j3_khong_doc_duoc_file_ngoai_repo(self):
        k = Khach()
        for d in ("/etc/passwd", "/../../../../etc/passwd", "/%2e%2e%2f%2e%2e%2fetc%2fpasswd",
                  f"/..{os.path.expanduser('~')}/.ssh/id_rsa"):
            st, _ = k.goi(d)
            self.assertNotEqual(st, 200, f"đọc được file ngoài repo qua {d}")

    def test_j4_thu_muc_duoc_phep_van_phuc_vu_duoc(self):
        """Phép đo đối chứng: nếu MỌI đường đều 404 thì ca j1 đạt một cách vô nghĩa."""
        k = Khach()
        st, _ = k.goi("/admin/index.html")
        self.assertEqual(st, 200, "static không phục vụ được cả admin/index.html — "
                                  "ca j1 đạt vì mọi thứ đều 404, không phải vì chặn đúng")

    def test_j5_goi_backup_dat_trong_thu_muc_duoc_phep_cung_khong_tai_duoc(self):
        """Phòng hai lớp: đuôi `.vipkb` không nằm trong danh sách đuôi được phép."""
        goc_repo = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, os.pardir))
        duong = os.path.join(goc_repo, "assets", "bay-khoa.vipkb")
        try:
            with open(duong, "wb") as f:
                f.write(b"GIA-LAP-KHONG-PHAI-KHOA-THAT")
            st, _ = Khach().goi("/assets/bay-khoa.vipkb")
            self.assertNotEqual(st, 200, "tải được file .vipkb từ thư mục static")
        finally:
            if os.path.exists(duong):
                os.remove(duong)


class K_MaHoaVaThuHoi(_NenHttp):
    """S06 — AES-GCM phát hiện sửa đổi, xoay khóa, cách ly credentials, thu hồi phiên."""

    def test_k1_sua_mot_byte_ban_ma_thi_giai_ma_hong(self):
        bm, _ = bao_mat.ma_hoa_cred({"api_key": CRED_KEY}, 11, "vtp")
        v, kid, nonce, ct = bm.split("$")
        for ten, hong in (("ciphertext", f"{v}${kid}${nonce}${_lat_bit_hex(ct)}"),
                          ("nonce", f"{v}${kid}${_lat_bit_hex(nonce)}${ct}")):
            with self.assertRaises(ValueError, msg=f"sửa {ten} mà vẫn giải được"):
                bao_mat.giai_ma_cred(hong, 11, "vtp")

    def test_k2_cach_ly_credentials_giua_tenant_va_hang(self):
        """Chép bản mã sang hàng khác (tenant khác / hãng khác) phải HỎNG, nhờ AAD."""
        bm, _ = bao_mat.ma_hoa_cred({"api_key": CRED_KEY}, 101, "vtp")
        self.assertEqual(bao_mat.giai_ma_cred(bm, 101, "vtp")["api_key"], CRED_KEY)
        for tid, hang, nhan in ((102, "vtp", "đổi tenant"), (101, "jt", "đổi hãng"),
                                (102, "jt", "đổi cả hai")):
            with self.assertRaises(ValueError, msg=f"{nhan} mà vẫn giải được"):
                bao_mat.giai_ma_cred(bm, tid, hang)
        wh = bao_mat.ma_hoa_wh(SECRET_WH, "wh-aaa")
        with self.assertRaises(ValueError, msg="chép webhook secret sang webhook khác vẫn đọc được"):
            bao_mat.giai_ma_wh(wh, "wh-bbb")

    def test_k3_xoay_khoa_chuyen_het_va_GIU_khoa_cu(self):
        csdl.mo()
        tid = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                       ("ag01-k3", "Tenant K3", "basic", csdl.bay_gio())).lastrowid
        cred_mh, duoi = bao_mat.ma_hoa_cred({"api_key": CRED_KEY}, tid, "vtp")
        wh_ma = "wh-k3-" + base64.b16encode(os.urandom(3)).decode().lower()
        csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                 " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa,"
                 " tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
                 (tid, "vtp", "K3", "mock", cred_mh, duoi, wh_ma,
                  bao_mat.ma_hoa_wh(SECRET_WH, wh_ma), csdl.bay_gio()))
        key_id_cu = sp.nha_cung_cap().khoa_hien_hanh()[0]
        kq = bao_mat.xoay_khoa()
        # CSDL của bộ thử này có sẵn hàng hỏng do lớp D_XoayKhoa CỐ Ý dựng, nên không khẳng
        # định "hong rỗng" (câu đó sẽ vượt phạm vi — CLAUDE.md §12.1 luật 5). Chỉ khẳng định
        # HÀNG CỦA CA NÀY không nằm trong danh sách hỏng.
        r = csdl.mot("SELECT * FROM carrier_accounts WHERE tenant_id=?", (tid,))
        for h in kq["hong"]:
            self.assertNotIn(f"carrier_account {r['id']} ", h,
                             f"hàng của ca này bị hỏng khi xoay khóa: {h}")
        self.assertNotEqual(kq["key_id"], key_id_cu)
        self.assertEqual(bao_mat.key_id_cua(r["credentials_ma_hoa"]), kq["key_id"])
        self.assertEqual(bao_mat.key_id_cua(r["webhook_secret_ma_hoa"]), kq["key_id"])
        self.assertEqual(bao_mat.giai_ma_cred(r["credentials_ma_hoa"], tid, "vtp")["api_key"],
                         CRED_KEY)
        self.assertEqual(bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], wh_ma), SECRET_WH)
        # Khóa cũ KHÔNG bị xóa — bản mã nào chưa chuyển thì còn phải giải được
        self.assertIn(key_id_cu, sp.nha_cung_cap().danh_sach_key_id())
        # Audit chỉ ghi key_id và số lượng, KHÔNG ghi secret
        a = csdl.mot("SELECT chi_tiet, doi_tuong FROM audit WHERE hanh_dong='xoay_khoa_ma_hoa'"
                     " ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(a)
        for bi in (CRED_KEY, SECRET_WH, sp.nha_cung_cap().khoa_hien_hanh()[1].hex()):
            self.assertNotIn(bi, a["chi_tiet"] + a["doi_tuong"], "audit lộ bí mật")

    def test_k4_thu_hoi_phien_co_hieu_luc_ngay(self):
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-k4', ?, 'k4', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        a, b = Khach(), Khach()
        for k in (a, b):
            self.assertEqual(k.goi("/api/v2/auth/dang-nhap", "POST",
                                   {"ten_dang_nhap": "ag01-k4", "mat_khau": MK_THU})[0], 200)
            self.assertEqual(k.goi("/api/v2/auth/toi")[0], 200)
        # a thu hồi các phiên KHÁC → b mất quyền ngay, a còn
        self.assertEqual(a.goi("/api/v2/auth/thu-hoi-phien", "POST", {})[0], 200)
        self.assertEqual(b.goi("/api/v2/auth/toi")[0], 401, "phiên khác vẫn sống sau thu hồi")
        self.assertEqual(a.goi("/api/v2/auth/toi")[0], 200, "thu hồi cả phiên của chính mình")
        # Đăng xuất → chính phiên đó mất quyền
        self.assertEqual(a.goi("/api/v2/auth/dang-xuat", "POST", {})[0], 200)
        self.assertEqual(a.goi("/api/v2/auth/toi")[0], 401)

    def test_k5_khoa_tai_khoan_thi_moi_phien_mat_quyen_ngay(self):
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-k5', ?, 'k5', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        k = Khach()
        self.assertEqual(k.goi("/api/v2/auth/dang-nhap", "POST",
                               {"ten_dang_nhap": "ag01-k5", "mat_khau": MK_THU})[0], 200)
        self.assertEqual(k.goi("/api/v2/auth/toi")[0], 200)
        csdl.ghi("UPDATE users SET trang_thai='khoa' WHERE ten_dang_nhap='ag01-k5'")
        self.assertEqual(k.goi("/api/v2/auth/toi")[0], 401,
                         "khóa tài khoản mà phiên đang mở vẫn dùng được")

    def test_k6_token_phien_luu_dang_bam(self):
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('ag01-k6', ?, 'k6', 'PLATFORM_ADMIN', ?)",
                 (bao_mat.bam_mat_khau(MK_THU), csdl.bay_gio()))
        token, _ = bao_mat.dang_nhap("ag01-k6", MK_THU)
        self.assertIsNotNone(token)
        self.assertIsNotNone(bao_mat.ngu_canh(token))
        for b in csdl.nhieu("SELECT name FROM sqlite_master WHERE type='table'"):
            for row in csdl.nhieu(f"SELECT * FROM {b['name']}"):
                self.assertNotIn(token, "|".join("" if v is None else str(v) for v in tuple(row)),
                                 f"token phiên THÔ nằm trong bảng {b['name']}")


class Q_SeedQuyenKhongCapLaiQuyenDaThu(unittest.TestCase):
    """`quyen.seed()` là đường CẤP quyền — KHÔNG được là đường CẤP LẠI quyền đã bị thu.

    Quyền là dữ liệu SỐNG: mọi endpoint tra `co_quyen` (bảng `role_permissions`) ở từng yêu
    cầu, và đường duy nhất hiện có để THU một quyền là xoá đúng dòng trong bảng. Bản cũ chạy
    lại toàn bộ ma trận ở mỗi lần khởi động/migration, nên dòng vừa bị xoá SỐNG LẠI — im lặng.
    Đo được trên bản cũ: xoá (TENANT_STAFF, tenant.don.ghi) → `co_quyen` False; gọi `seed()`
    → True. Cùng lớp lỗi ở chiều ngược lại: quyền đã gỡ khỏi `MA_TRAN` vẫn sống mãi trong CSDL
    cũ vì bản cũ chỉ THÊM.
    """

    ROLE, PERM = "TENANT_STAFF", "tenant.don.ghi"

    def setUp(self):
        quyen.seed()
        self.assertTrue(quyen.co_quyen(self.ROLE, self.PERM),
                        "ma trận chưa được seed — phép đo vô nghĩa")

    def tearDown(self):
        # Trả CSDL + hằng số về đúng trạng thái trước ca (không để ca sau kế thừa đột biến).
        csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma) VALUES (?,?)",
                 (self.ROLE, self.PERM))
        for p in ("tenant.thu_nghiem.moi", "tenant.thu_nghiem.hong"):
            quyen.QUYEN.pop(p, None)
            ds = quyen.MA_TRAN.get("TENANT_VIEWER", [])
            if p in ds:
                ds.remove(p)
        quyen.MA_TRAN.pop("KHONG_CO_ROLE", None)
        csdl.ghi("DELETE FROM role_permissions WHERE perm_ma LIKE 'tenant.thu_nghiem.%'")
        csdl.ghi("DELETE FROM permissions WHERE ma LIKE 'tenant.thu_nghiem.%'")

    def test_01_thu_quyen_roi_seed_khong_duoc_cap_lai(self):
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma=? AND perm_ma=?",
                 (self.ROLE, self.PERM))
        self.assertFalse(quyen.co_quyen(self.ROLE, self.PERM))
        quyen.seed()          # mô phỏng khởi động lại / migration chạy lại
        self.assertFalse(quyen.co_quyen(self.ROLE, self.PERM),
                         "seed() CẤP LẠI quyền vừa bị thu — quyền không thể thu được")

    def test_02_quyen_MOI_cua_ban_moi_van_duoc_seed(self):
        p = "tenant.thu_nghiem.moi"
        quyen.QUYEN[p] = "Quyền thử của bản mới"
        quyen.MA_TRAN["TENANT_VIEWER"].append(p)
        self.assertFalse(quyen.co_quyen("TENANT_VIEWER", p))
        quyen.seed()
        self.assertTrue(quyen.co_quyen("TENANT_VIEWER", p),
                        "bản mới thêm quyền mà seed() không cấp — nâng cấp hỏng im lặng")

    def test_03_seed_hong_giua_chung_thi_khong_de_lai_ma_tran_nua_voi(self):
        p = "tenant.thu_nghiem.hong"
        quyen.QUYEN[p] = "Quyền thử gây hỏng"
        quyen.MA_TRAN["TENANT_VIEWER"].append(p)    # ô này sẽ chèn TRƯỚC ô hỏng
        quyen.MA_TRAN["KHONG_CO_ROLE"] = [p]        # role không tồn tại ⇒ FK chặn
        with self.assertRaises(csdl.LoiToanVen):
            quyen.seed()
        self.assertIsNone(csdl.mot("SELECT 1 x FROM permissions WHERE ma=?", (p,)),
                          "seed hỏng nhưng permission vẫn còn — không phải MỘT giao dịch")
        self.assertFalse(quyen.co_quyen("TENANT_VIEWER", p),
                         "seed hỏng nhưng đã kịp cấp quyền — ma trận nửa vời")
        # ĐỐI CHỨNG DƯƠNG: bỏ đúng ô hỏng ⇒ CÙNG seed cấp được quyền mới.
        quyen.MA_TRAN.pop("KHONG_CO_ROLE")
        quyen.seed()
        self.assertTrue(quyen.co_quyen("TENANT_VIEWER", p))


def _lat_bit_hex(h: str) -> str:
    """Lật một bit trong chuỗi hex — để chứng minh AEAD bắt được sửa đổi."""
    b = bytearray(bytes.fromhex(h))
    b[0] ^= 0x01
    return bytes(b).hex()


if __name__ == "__main__":
    unittest.main(verbosity=2)
