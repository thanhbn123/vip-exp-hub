# Bộ thử XOAY KHÓA CÓ KIỂM SOÁT (G12 / D-2) — AG-05.
# Chạy: python3 app/thu/thu_xoay_khoa.py
#
# Nguyên tắc (CLAUDE.md §12.1): mỗi khẳng định do MỘT phép đo thật tạo ra. Không grep mã nguồn
# để kết luận hành vi khi còn đo được hành vi. Riêng lớp `D_ChotKhongBoQuaDuoc` có một ca CỐ Ý
# đọc mã — vì câu cần chứng minh là "KHÔNG có biến môi trường nào nới chốt", mà câu phủ định
# toàn phần ấy không đo được bằng cách gọi hàm; ca đó ghi rõ phạm vi của chính nó.
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_REPO = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-xoaykhoa-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ.pop("VIP_HUB_RESET_TOKEN", None)
# PBKDF2 600.000 vòng × hàng chục lượt mở gói làm bộ thử chạy hàng phút. Hạ số vòng CHỈ TRONG
# BỘ THỬ là hợp lệ: nó không đổi hành vi được kiểm (mở/không mở được gói), và `sao_luu_khoa`
# vẫn TỪ CHỐI dưới 100.000 — ca `b5` đo đúng chốt đó.
os.environ["VIP_HUB_BACKUP_PBKDF2"] = "120000"

import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import khoi_tao         # noqa: E402
import quyen            # noqa: E402
import sao_luu_khoa as skb      # noqa: E402
import secret_provider as sp    # noqa: E402
import xoay_khoa as xk          # noqa: E402

PASS_THU = "passphrase-dien-tap-bo-thu-khong-phai-bi-mat-that"
CRED_THU = {"api_key": "KEY-THU-G12-0001", "secret": "SECRET-THU-G12-0001"}
WH_THU = "WEBHOOK-SECRET-THU-G12-0001"


def _dung_du_lieu():
    """Dựng CSDL + seed + MỘT tài khoản hãng có cả credentials và webhook secret."""
    csdl.mo()
    khoi_tao.chay()
    quyen.seed()
    tn = csdl.mot("SELECT id FROM tenants LIMIT 1")
    if tn is None:
        csdl.ghi("INSERT INTO tenants (code, ten, trang_thai, goi_id, tao_luc)"
                 " VALUES ('THU','Tenant thu','hoat_dong','free',?)", (csdl.bay_gio(),))
        tn = csdl.mot("SELECT id FROM tenants LIMIT 1")
    tid = tn["id"]
    wh_ma = "wh-thu-g12-0001"
    if csdl.mot("SELECT id FROM carrier_accounts WHERE webhook_ma=?", (wh_ma,)) is None:
        ban_ma, duoi = bao_mat.ma_hoa_cred(CRED_THU, tid, "jt")
        csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                 " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa,"
                 " kich_hoat, tao_luc) VALUES (?,?,?,?,?,?,?,?,1,?)",
                 (tid, "jt", "TK thu G12", "sandbox", ban_ma, duoi, wh_ma,
                  bao_mat.ma_hoa_wh(WH_THU, wh_ma), csdl.bay_gio()))
    return tid


def _tao_goi(thu_muc) -> str:
    """Tạo gói backup — CỐ Ý gọi `sao_luu_khoa` trực tiếp, KHÔNG qua `xoay_khoa`.

    Chính điều này là một phép đo: `xoay_khoa` không có đường nào tự tạo gói cho mình.
    """
    duong = os.path.join(thu_muc, "goi-thu.vipkb")
    skb.tao_goi(duong, passphrase=PASS_THU, cho_nhap=False)
    return duong


class A_Quyen(unittest.TestCase):
    """D-2: 'khóa bằng quyền quản trị đặc biệt'."""

    @classmethod
    def setUpClass(cls):
        _dung_du_lieu()

    def _user(self, vai_tro):
        ten = f"thu-g12-{(vai_tro or 'none').lower()}"
        u = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (ten,))
        if u is None:
            csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role,"
                     " trang_thai, so_lan_sai, tao_luc) VALUES (?,?,?,?,?,0,?)",
                     (ten, bao_mat.bam_mat_khau("x" * 20), ten, vai_tro, "hoat_dong",
                      csdl.bay_gio()))
            u = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (ten,))
        return u["id"]

    def test_a1_quyen_moi_khong_trung_quyen_co_san(self):
        """Quyền xoay khóa là quyền MỚI, không phải một quyền sẵn có dùng lại."""
        self.assertNotIn(xk.QUYEN_XOAY, quyen.QUYEN,
                         "`platform.khoa.xoay` đang trùng một quyền đã có — D-2 đòi quyền RIÊNG")

    def test_a2_chua_seed_thi_OWNER_cung_khong_xoay_duoc(self):
        """Chưa seed quyền vào `role_permissions` thì ngay cả OWNER cũng bị từ chối.

        CỐ Ý: `xoay_khoa` KHÔNG tự seed quyền cho mình. Mô-đun tự cấp quyền cho mình là mô-đun
        không có quyền nào cả.
        """
        csdl.ghi("DELETE FROM role_permissions WHERE perm_ma=?", (xk.QUYEN_XOAY,))
        with self.assertRaises(xk.LoiXoayKhoa) as e:
            xk.kiem_quyen(user_id=self._user("PLATFORM_OWNER"))
        self.assertIn(xk.QUYEN_XOAY, str(e.exception))

    def test_a3_seed_roi_thi_OWNER_qua(self):
        self._seed_quyen()
        kq = xk.kiem_quyen(user_id=self._user("PLATFORM_OWNER"))
        self.assertEqual(kq["vai_tro"], "PLATFORM_OWNER")

    def test_a4_PLATFORM_ADMIN_bi_tu_choi_DU_CO_SEED_NHAM_QUYEN(self):
        """Lớp hằng số trong MÃ chặn được cả trường hợp quyền bị seed nhầm cho ADMIN.

        Đây là lý do có HAI lớp kiểm: một dòng `INSERT` vào `role_permissions` không được phép
        biến ADMIN thành người xoay được khóa của cả nền tảng.
        """
        self._seed_quyen()
        csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma) VALUES (?,?)",
                 ("PLATFORM_ADMIN", xk.QUYEN_XOAY))
        self.assertTrue(quyen.co_quyen("PLATFORM_ADMIN", xk.QUYEN_XOAY),
                        "tiền đề của ca thử: quyền ĐÃ được seed nhầm cho ADMIN")
        with self.assertRaises(xk.LoiXoayKhoa) as e:
            xk.kiem_quyen(user_id=self._user("PLATFORM_ADMIN"))
        self.assertIn("PLATFORM_OWNER", str(e.exception))
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma='PLATFORM_ADMIN' AND perm_ma=?",
                 (xk.QUYEN_XOAY,))

    def test_a5_tenant_owner_va_vo_danh_bi_tu_choi(self):
        self._seed_quyen()
        for vt in (None, "PLATFORM_ADMIN"):
            with self.assertRaises(xk.LoiXoayKhoa):
                xk.kiem_quyen(user_id=self._user(vt))
        with self.assertRaises(xk.LoiXoayKhoa):
            xk.kiem_quyen()          # không nói ai xoay → từ chối

    def test_a6_user_bi_khoa_thi_tu_choi(self):
        self._seed_quyen()
        uid = self._user("PLATFORM_OWNER")
        csdl.ghi("UPDATE users SET trang_thai='khoa' WHERE id=?", (uid,))
        try:
            with self.assertRaises(xk.LoiXoayKhoa):
                xk.kiem_quyen(user_id=uid)
        finally:
            csdl.ghi("UPDATE users SET trang_thai='hoat_dong' WHERE id=?", (uid,))

    @staticmethod
    def _seed_quyen():
        csdl.ghi("INSERT OR IGNORE INTO permissions (ma, mo_ta) VALUES (?,?)",
                 (xk.QUYEN_XOAY, "Xoay khóa mã hóa nền tảng"))
        csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma) VALUES (?,?)",
                 ("PLATFORM_OWNER", xk.QUYEN_XOAY))


class B_Chot(unittest.TestCase):
    """Sáu điều kiện của chốt. Thiếu một là không xoay."""

    @classmethod
    def setUpClass(cls):
        _dung_du_lieu()
        A_Quyen._seed_quyen()
        cls.nen = tempfile.mkdtemp(prefix="vip-thu-chot-")
        cls.goi = _tao_goi(cls.nen)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.nen, ignore_errors=True)

    def test_b1_chua_co_chung_nhan_thi_chot_KHONG_dat(self):
        kq = xk.kiem_chot(self.goi, os.path.join(self.nen, "khong-ton-tai.json"),
                          passphrase=PASS_THU, cho_nhap=False)
        self.assertFalse(kq["dat"])
        self.assertIn("C3", kq["chua_dat"])
        self.assertIn("C5", kq["chua_dat"])

    def test_b2_chung_nhan_roi_thi_C3_C4_C5_C6_dat(self):
        """Phải chạy chứng nhận ở TIẾN TRÌNH KHÁC, nếu không C5 (pid) sẽ chặn — đúng thiết kế."""
        cn = self._chung_nhan_tien_trinh_khac(self.goi)
        self.assertEqual(cn["ket_qua"], "dat", cn)
        kq = xk.kiem_chot(self.goi, cn["duong_chung_nhan"], passphrase=PASS_THU, cho_nhap=False)
        self.assertTrue(kq["dat"], json.dumps(kq, ensure_ascii=False, indent=2))
        self.assertEqual(kq["chua_dat"], [])

    def test_b3_C5_chan_chung_nhan_do_CHINH_tien_trinh_nay_ghi(self):
        """Một tiến trình không được vừa làm chứng vừa thi hành (§12.1 — ca bộ cài tự chạy hộ)."""
        cn = xk.ghi_chung_nhan_khoi_phuc(self.goi, os.path.join(self.nen, "cn-cung-pid.json"),
                                         passphrase=PASS_THU, cho_nhap=False)
        self.assertEqual(cn["ket_qua"], "dat")
        self.assertEqual(cn["pid"], os.getpid())
        kq = xk.kiem_chot(self.goi, cn["duong_chung_nhan"], passphrase=PASS_THU, cho_nhap=False)
        self.assertFalse(kq["dat"])
        self.assertIn("C5", kq["chua_dat"])

    def test_b4_doi_ten_goi_cu_thanh_ten_moi_KHONG_qua_duoc_C3(self):
        """Chứng nhận buộc vào NỘI DUNG gói (sha256), không vào tên file."""
        cn = self._chung_nhan_tien_trinh_khac(self.goi)
        goi_khac = os.path.join(self.nen, "goi-khac.vipkb")
        skb.tao_goi(goi_khac, passphrase=PASS_THU, cho_nhap=False)   # gói MỚI, nội dung khác
        shutil.copy2(cn["duong_chung_nhan"], os.path.join(self.nen, "cn-lac.json"))
        kq = xk.kiem_chot(goi_khac, os.path.join(self.nen, "cn-lac.json"),
                          passphrase=PASS_THU, cho_nhap=False)
        self.assertFalse(kq["dat"])
        self.assertIn("C3", kq["chua_dat"])

    def test_b5_goi_THIEU_khoa_ma_CSDL_dang_dung_thi_C2_khong_dat(self):
        """Gói cũ + khóa mới sinh sau đó = khôi phục xong vẫn mất dữ liệu. Phải bắt TRƯỚC khi xoay."""
        goi_cu = os.path.join(self.nen, "goi-cu.vipkb")
        skb.tao_goi(goi_cu, passphrase=PASS_THU, cho_nhap=False)
        p = sp.nha_cung_cap()
        kid_moi = p.tao_khoa_moi()
        p.dat_khoa_hien_hanh(kid_moi)
        tid = csdl.mot("SELECT id FROM tenants LIMIT 1")["id"]
        bm, duoi = bao_mat.ma_hoa_cred({"api_key": "SAU-GOI"}, tid, "vtp")
        csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                 " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa,"
                 " kich_hoat, tao_luc) VALUES (?,?,?,?,?,?,?,?,1,?)",
                 (tid, "vtp", "TK sau goi", "sandbox", bm, duoi, "wh-sau-goi",
                  bao_mat.ma_hoa_wh("S", "wh-sau-goi"), csdl.bay_gio()))
        try:
            phu = xk.goi_co_phu_du_khong(goi_cu, passphrase=PASS_THU, cho_nhap=False)
            self.assertFalse(phu["dat"])
            self.assertIn(kid_moi, phu["key_id_thieu_so_voi_csdl"])
            kq = xk.kiem_chot(goi_cu, passphrase=PASS_THU, cho_nhap=False)
            self.assertIn("C2", kq["chua_dat"])
        finally:
            csdl.ghi("DELETE FROM carrier_accounts WHERE webhook_ma='wh-sau-goi'")

    def test_b6_goi_bi_sua_mot_byte_thi_C2_khong_dat(self):
        hong = os.path.join(self.nen, "goi-hong.vipkb")
        with open(self.goi, "rb") as f:
            tho = bytearray(f.read())
        tho[-1] ^= 0xFF
        with open(hong, "wb") as f:
            f.write(bytes(tho))
        kq = xk.kiem_chot(hong, passphrase=PASS_THU, cho_nhap=False)
        self.assertFalse(kq["dat"])
        self.assertIn("C2", kq["chua_dat"])

    def test_b7_khong_co_goi_thi_dung_ngay_o_C1(self):
        kq = xk.kiem_chot(os.path.join(self.nen, "khong-co.vipkb"), passphrase=PASS_THU,
                          cho_nhap=False)
        self.assertFalse(kq["dat"])
        self.assertEqual(kq["chua_dat"], ["C1"])

    def test_b8_chot_KHONG_tao_gi(self):
        """Chốt chỉ ĐỌC: chạy xong thư mục không thêm file nào, gói không đổi byte nào."""
        truoc = sorted(os.listdir(self.nen))
        st = os.stat(self.goi)
        xk.kiem_chot(self.goi, passphrase=PASS_THU, cho_nhap=False)
        self.assertEqual(sorted(os.listdir(self.nen)), truoc)
        self.assertEqual((st.st_size, st.st_mtime), (os.stat(self.goi).st_size,
                                                     os.stat(self.goi).st_mtime))

    def test_b9_chung_nhan_khong_chua_bi_mat(self):
        """Quét chứng nhận tìm khóa + plaintext ở ba dạng. Phép đo ĐỘC LẬP với việc mã hóa."""
        import base64
        cn = self._chung_nhan_tien_trinh_khac(self.goi)
        with open(cn["duong_chung_nhan"], "rb") as f:
            tho = f.read()
        p = sp.nha_cung_cap()
        bi_mat = [CRED_THU["api_key"].encode(), CRED_THU["secret"].encode(), WH_THU.encode(),
                  PASS_THU.encode()] + [p.lay_khoa(k) for k in p.danh_sach_key_id()]
        lo = []
        for b in bi_mat:
            for ten, x in (("tho", b), ("hex", b.hex().encode()),
                           ("b64", base64.b64encode(b).rstrip(b"="))):
                if len(x) >= 8 and x in tho:
                    lo.append(ten)
        self.assertEqual(lo, [], "chứng nhận khôi phục LỘ bí mật")

    @staticmethod
    def _chung_nhan_tien_trinh_khac(goi):
        """Chạy `xoay_khoa.py chung-nhan` ở TIẾN TRÌNH CON — đúng cách người vận hành làm."""
        duong = goi + ".chung-nhan.json"
        r = subprocess.run([sys.executable, os.path.join(GOC_APP, "xoay_khoa.py"),
                            "chung-nhan", goi, duong],
                           cwd=GOC_REPO, capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=GOC_APP,
                                    VIP_HUB_BACKUP_PASSPHRASE=PASS_THU))
        if r.returncode != 0:
            raise AssertionError(f"chung-nhan hỏng (mã {r.returncode}): {r.stderr[-1500:]}")
        cn = json.loads(r.stdout)
        cn["duong_chung_nhan"] = duong
        return cn


class C_DienTapBanSao(unittest.TestCase):
    """D-2: 'kiểm thử trên BẢN SAO trước'."""

    @classmethod
    def setUpClass(cls):
        _dung_du_lieu()

    def test_c1_DIEN_TAP_xoay_tren_ban_sao_roi_giai_ma_lai_duoc_CA_HAI_duong(self):
        kq = xk.dien_tap()
        self.assertTrue(kq["dat"], json.dumps(kq, ensure_ascii=False, indent=2))
        self.assertNotEqual(kq["key_id_truoc"], kq["key_id_sau"])
        self.assertEqual(kq["ban_ma_LECH_noi_dung"], [])
        self.assertEqual(kq["ban_ma_KHONG_giai_duoc_sau_xoay"], [])
        self.assertGreater(kq["so_ban_ma_do"], 0)
        self.assertEqual(kq["so_ban_ma_giai_lai_KHOP"], kq["so_ban_ma_do"])
        self.assertEqual(kq["duong_giai_ma_da_do"], ["giai_ma_cred", "giai_ma_wh"])

    def test_c2_khoa_cu_KHONG_bi_xoa(self):
        kq = xk.dien_tap()
        self.assertEqual(kq["khoa_cu_bi_xoa"], [])
        self.assertGreater(kq["so_khoa_sau"], kq["so_khoa_truoc"] - 1)

    def test_c3_dien_tap_KHONG_cham_nguon(self):
        """Nguồn phải còn nguyên: cùng tên file, cùng kích thước, cùng quyền."""
        anh_truoc = xk._anh_thu_muc(cau_hinh.THU_MUC_DU_LIEU)
        kid_truoc = sp.nha_cung_cap().khoa_hien_hanh()[0]
        kq = xk.dien_tap()
        self.assertTrue(kq["nguon_con_nguyen"])
        self.assertEqual(anh_truoc, xk._anh_thu_muc(cau_hinh.THU_MUC_DU_LIEU))
        self.assertEqual(kid_truoc, sp.nha_cung_cap().khoa_hien_hanh()[0],
                         "diễn tập đã đổi khóa hiện hành của NGUỒN — cách ly hỏng")

    def test_c4_ban_sao_bi_xoa_sau_khi_xong(self):
        kq = xk.dien_tap()
        self.assertFalse(os.path.exists(kq["ban_sao"]),
                         "bản sao còn lại trên đĩa — đó là một bản khóa thừa không ai canh")

    def test_c5_nguon_khong_co_khoa_thi_TU_CHOI_chu_khong_bao_dat(self):
        rong = tempfile.mkdtemp(prefix="vip-thu-rong-")
        try:
            with self.assertRaises(xk.LoiXoayKhoa):
                xk.dien_tap(rong)
        finally:
            shutil.rmtree(rong, ignore_errors=True)

    def test_c6_tien_trinh_con_TU_CHOI_khi_tro_vao_thu_muc_mac_dinh(self):
        """Chốt cuối: con chạy với `VIP_HUB_DATA` = thư mục mặc định thì thoát mã 9."""
        r = subprocess.run([sys.executable, os.path.join(GOC_APP, "xoay_khoa.py"),
                            "_chay-tren-ban-sao"], cwd=GOC_REPO, capture_output=True, text=True,
                           env=dict(os.environ, PYTHONPATH=GOC_APP,
                                    VIP_HUB_DATA=os.path.join(GOC_APP, "du-lieu")))
        self.assertEqual(r.returncode, 9, r.stdout + r.stderr)
        self.assertNotIn("du-lieu/khoa", os.listdir(GOC_APP))

    def test_c7_tien_trinh_con_TU_CHOI_khi_thieu_VIP_HUB_DATA(self):
        mt = {k: v for k, v in os.environ.items() if k != "VIP_HUB_DATA"}
        mt["PYTHONPATH"] = GOC_APP
        r = subprocess.run([sys.executable, os.path.join(GOC_APP, "xoay_khoa.py"),
                            "_chay-tren-ban-sao"], cwd=GOC_REPO, capture_output=True, text=True,
                           env=mt)
        self.assertEqual(r.returncode, 9, r.stdout + r.stderr)


class D_ChotKhongBoQuaDuoc(unittest.TestCase):
    """Chỉ thị: chốt phải KHÔNG bỏ qua được bằng một cờ môi trường."""

    @classmethod
    def setUpClass(cls):
        _dung_du_lieu()
        A_Quyen._seed_quyen()
        cls.nen = tempfile.mkdtemp(prefix="vip-thu-boqua-")
        cls.goi = _tao_goi(cls.nen)
        cls.uid = A_Quyen()._user("PLATFORM_OWNER")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.nen, ignore_errors=True)

    def test_d1_co_quyen_nhung_chot_chua_dat_thi_VAN_tu_choi(self):
        with self.assertRaises(xk.LoiXoayKhoa) as e:
            xk.xoay_that(self.goi, os.path.join(self.nen, "khong-co.json"),
                         user_id=self.uid, passphrase=PASS_THU, cho_nhap=False)
        self.assertIn("chốt chưa đạt", str(e.exception))

    def test_d2_mot_loat_co_moi_truong_trong_nhu_co_bo_qua_deu_VO_TAC_DUNG(self):
        co = ["VIP_HUB_BO_QUA_CHOT", "VIP_HUB_FORCE", "VIP_HUB_XOAY_KHOA_FORCE",
              "VIP_HUB_SKIP_GATE", "FORCE", "VIP_HUB_KHAN_CAP", "VIP_HUB_DEV",
              "VIP_HUB_XOAY_KHOA_BO_QUA_CHOT", "VIP_HUB_NO_VERIFY", "SKIP_CHECKS"]
        cu = {k: os.environ.get(k) for k in co}
        for k in co:
            os.environ[k] = "1"
        try:
            with self.assertRaises(xk.LoiXoayKhoa):
                xk.xoay_that(self.goi, os.path.join(self.nen, "khong-co.json"),
                             user_id=self.uid, passphrase=PASS_THU, cho_nhap=False)
        finally:
            for k, v in cu.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)

    def test_d3_xoay_that_KHONG_co_tham_so_nao_bo_qua_chot(self):
        """Đo bằng chữ ký hàm, không bằng đọc lướt."""
        import inspect
        ten = set(inspect.signature(xk.xoay_that).parameters)
        xau = {t for t in ten if any(x in t.lower() for x in
                                     ("bo_qua", "force", "skip", "khan_cap", "no_", "ep_"))}
        self.assertEqual(xau, set(), f"`xoay_that` có tham số nới chốt: {xau}")

    def test_d4_mo_dun_khong_doc_bien_moi_truong_nao_de_quyet_dinh_chot(self):
        """CA CỐ Ý ĐỌC MÃ — phạm vi hẹp, nói rõ.

        ĐO: trong `app/xoay_khoa.py` không có lượt đọc `os.environ` nào ngoài DUY NHẤT lượt đọc
        `VIP_HUB_DATA` trong `_chay_tren_ban_sao` (chốt cách ly của tiến trình con) và lượt
        `dict(os.environ, …)` dựng môi trường cho tiến trình con.
        KHÔNG ĐO: hành vi của `sao_luu_khoa`/`secret_provider` mà mô-đun này gọi
        (`VIP_HUB_BACKUP_PASSPHRASE` và `VIP_HUB_BACKUP_PBKDF2` là của `sao_luu_khoa`, và chúng
        cấp bí mật chứ không nới chốt), và không đo được câu "mọi cách nới chốt khác".
        """
        import re
        with open(os.path.join(GOC_APP, "xoay_khoa.py"), encoding="utf-8") as f:
            ma = f.read()
        doc = re.findall(r"os\.environ(?:\.get)?\(\s*[\"']([A-Z_0-9]+)[\"']", ma)
        self.assertEqual(sorted(set(doc)), ["VIP_HUB_DATA"], f"đọc thêm biến môi trường: {doc}")

    def test_d5_xoay_khoa_KHONG_tu_tao_goi_backup(self):
        """Thứ dùng để kiểm chứng phải ĐỘC LẬP: mô-đun không được tự dựng bằng chứng cho mình.

        ĐO bằng CÂY CÚ PHÁP (`ast`), không bằng `grep`. Lượt đầu ca này dùng `grep` và nó
        **báo hỏng oan** vì bắt phải chữ `tao_goi()` nằm trong một dòng CHÚ THÍCH nói rằng
        không được gọi hàm đó — đúng kiểu công cụ có bộ lọc nói quá phạm vi nó đo
        (CLAUDE.md §12.1 luật 3). `ast` chỉ thấy lượt GỌI thật.
        """
        import ast
        with open(os.path.join(GOC_APP, "xoay_khoa.py"), encoding="utf-8") as f:
            cay = ast.parse(f.read())
        goi = []
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Call):
                h = nut.func
                ten = h.attr if isinstance(h, ast.Attribute) else getattr(h, "id", None)
                if ten == "tao_goi":
                    goi.append(ast.unparse(nut.func))
        self.assertEqual(goi, [],
                         "`xoay_khoa` đang tự tạo gói backup — đó là tự làm chứng cho mình")

    def test_d6_tu_choi_duoc_ghi_audit(self):
        truoc = csdl.mot("SELECT COUNT(*) n FROM audit WHERE hanh_dong='xoay_khoa_tu_choi'")["n"]
        with self.assertRaises(xk.LoiXoayKhoa):
            xk.xoay_that(self.goi, os.path.join(self.nen, "khong-co.json"),
                         user_id=self.uid, passphrase=PASS_THU, cho_nhap=False)
        sau = csdl.mot("SELECT COUNT(*) n FROM audit WHERE hanh_dong='xoay_khoa_tu_choi'")["n"]
        self.assertEqual(sau, truoc + 1)

    def test_d7_khong_quyen_thi_dung_TRUOC_khi_cham_den_chot(self):
        """Thứ tự: quyền trước, chốt sau. Người không có quyền không được dò trạng thái chốt."""
        uid = A_Quyen()._user("PLATFORM_ADMIN")
        with self.assertRaises(xk.LoiXoayKhoa) as e:
            xk.xoay_that(self.goi, user_id=uid, passphrase=PASS_THU, cho_nhap=False)
        self.assertIn("PLATFORM_OWNER", str(e.exception))
        self.assertNotIn("chốt chưa đạt", str(e.exception))


class E_XoayThatTrenNenCoLap(unittest.TestCase):
    """Chuỗi ĐẦY ĐỦ chạy thật: tạo gói → chứng nhận (tiến trình khác) → chốt đạt → xoay.

    Chạy trên nền `VIP_HUB_DATA` CÔ LẬP của bộ thử, KHÔNG phải dữ liệu thật của ai.
    """

    def test_e1_chuoi_day_du(self):
        _dung_du_lieu()
        A_Quyen._seed_quyen()
        uid = A_Quyen()._user("PLATFORM_OWNER")
        nen = tempfile.mkdtemp(prefix="vip-thu-e1-")
        try:
            goi = _tao_goi(nen)
            cn = B_Chot._chung_nhan_tien_trinh_khac(goi)
            self.assertEqual(cn["ket_qua"], "dat")
            chot = xk.kiem_chot(goi, cn["duong_chung_nhan"], passphrase=PASS_THU, cho_nhap=False)
            self.assertTrue(chot["dat"], json.dumps(chot, ensure_ascii=False, indent=2))

            p = sp.nha_cung_cap()
            ds_truoc = set(p.danh_sach_key_id())
            kq = xk.xoay_that(goi, cn["duong_chung_nhan"], user_id=uid, dia_chi="bo-thu",
                              passphrase=PASS_THU, cho_nhap=False)
            self.assertTrue(kq["dat"], json.dumps(kq, ensure_ascii=False, indent=2, default=str))
            self.assertEqual(kq["khoa_cu_bi_mat"], [], "xoay đã XÓA khóa cũ — cấm")
            self.assertTrue(ds_truoc <= set(p.danh_sach_key_id()))
            self.assertGreater(kq["nghiem_thu_sau_xoay"]["cred_giai_duoc"], 0)
            self.assertGreater(kq["nghiem_thu_sau_xoay"]["wh_giai_duoc"], 0)
            self.assertEqual(kq["nghiem_thu_sau_xoay"]["cred_hong"], 0)
            self.assertEqual(kq["nghiem_thu_sau_xoay"]["wh_hong"], 0)

            # Bản mã cũ VẪN đọc được sau khi xoay — đây là điểm sống còn của v3 + giữ khóa cũ.
            tid = csdl.mot("SELECT id FROM tenants LIMIT 1")["id"]
            r = csdl.mot("SELECT credentials_ma_hoa FROM carrier_accounts WHERE webhook_ma=?",
                         ("wh-thu-g12-0001",))
            self.assertEqual(bao_mat.giai_ma_cred(r["credentials_ma_hoa"], tid, "jt"), CRED_THU)

            # Audit có dấu vết, và KHÔNG chứa khóa/passphrase.
            a = csdl.mot("SELECT chi_tiet, user_id FROM audit WHERE hanh_dong='xoay_khoa_nghiem_thu'"
                         " ORDER BY id DESC LIMIT 1")
            self.assertIsNotNone(a)
            self.assertEqual(a["user_id"], uid)
            for bi in (PASS_THU, CRED_THU["api_key"], WH_THU):
                self.assertNotIn(bi, a["chi_tiet"] or "")
            for k in p.danh_sach_key_id():
                self.assertNotIn(p.lay_khoa(k).hex(), a["chi_tiet"] or "")
        finally:
            shutil.rmtree(nen, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
