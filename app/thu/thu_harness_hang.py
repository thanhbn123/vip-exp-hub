# Bộ thử G09 — harness kết nối hãng. Thuần local, KHÔNG gọi hãng thật ở bất kỳ chế độ nào.
#
# Nhóm ca thử ở đây CANH CHÍNH BỘ HARNESS, không canh adapter. Vì sao cần: harness là thứ dùng
# để kiểm chứng adapter, mà §12.1 nói thứ dùng để kiểm chứng phải được kiểm TRƯỚC khi tin.
# Nặng nhất là nhóm C: chứng minh SANDBOX/LIVE bị TỪ CHỐI khi thiếu credentials, chứ không âm
# thầm rơi về MOCK rồi báo đạt.
#
# Chạy: python3 app/thu/thu_harness_hang.py
import json
import os
import sys
import tempfile
import time
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

if not os.environ.get("VIP_HUB_DATA"):
    os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-g09-")
# Phiên chạy bộ thử KHÔNG được thừa hưởng chế độ/duyệt từ shell của người chạy.
for _b in ("VIP_HUB_HARNESS_CHE_DO", "VIP_HUB_HARNESS_DUYET", "VIP_HUB_HARNESS_NGUOI_DUYET",
           "VIP_HUB_HARNESS_CRED_FILE"):
    os.environ.pop(_b, None)

import adapter          # noqa: E402
import harness_hang as hh   # noqa: E402
import trang_thai_hang as tth  # noqa: E402
import webhook          # noqa: E402

CRED_JT_DU = {"apiAccount": "669", "privateKey": "K", "customerCode": "C", "password": "P"}


class A_ChayMock(unittest.TestCase):
    """MOCK phải chạy được ngay, không cần gì."""

    def test_a1_mock_chay_duoc_khong_can_gi(self):
        kq = hh.chay("jt", hh.MOCK, moi_truong_os={})
        self.assertEqual(kq.che_do, hh.MOCK)
        self.assertGreater(kq.so_dat, 20)
        self.assertEqual(kq.so_hong, 0,
                         "ca hỏng: " + "; ".join(f"{c.ma_ca}:{c.chi_tiet}"
                                                 for c in kq.cac_ca if c.ket_qua == "hong"))

    def test_a2_chay_tat_ca_hang_da_dang_ky(self):
        ra = hh.chay_tat_ca(hh.MOCK, moi_truong_os={})
        self.assertEqual(set(ra), set(adapter._DANG_KY))
        for hang, kq in ra.items():
            self.assertIsInstance(kq, hh.KetQuaLanChay, hang)
            self.assertEqual(kq.so_hong, 0, hang)

    def test_a3_moi_ca_deu_phai_noi_DO_BANG_GI(self):
        """§12.1 luật 5: kết luận nào cũng phải nói đo bằng gì."""
        for hang in adapter._DANG_KY:
            for c in hh.chay(hang, hh.MOCK, moi_truong_os={}).cac_ca:
                self.assertTrue(c.do_bang_gi.strip(),
                                f"{hang}/{c.ma_ca} không nói đo bằng gì")

    def test_a4_ket_qua_mang_theo_pham_vi_do(self):
        d = hh.chay("jt", hh.MOCK, moi_truong_os={}).nhu_dict()
        self.assertIn("NẰM NGOÀI", d["pham_vi"])

    def test_a5_che_do_tra_ve_la_che_do_DA_CHAY(self):
        """Không bao giờ được báo một chế độ mà thực tế không chạy ở đó."""
        kq = hh.chay("jt", hh.MOCK, moi_truong_os={"VIP_HUB_HARNESS_CHE_DO": "SANDBOX"})
        self.assertEqual(kq.che_do, hh.MOCK)


class B_CheDoVaCongChan(unittest.TestCase):

    def test_b1_che_do_mac_dinh_la_mock(self):
        self.assertEqual(hh.che_do_dang_xin({}), hh.MOCK)

    def test_b2_che_do_la_thi_bao_loi_khong_doan(self):
        with self.assertRaises(ValueError):
            hh.che_do_dang_xin({"VIP_HUB_HARNESS_CHE_DO": "PRODUCTION"})

    def test_b3_mock_khong_doi_gi(self):
        self.assertEqual(hh.thieu_gi_de_chay(hh.MOCK, "jt", {}), [])

    def test_b4_moi_truong_adapter_dung_ten(self):
        self.assertEqual(hh.moi_truong_adapter(hh.MOCK), "mock")
        self.assertEqual(hh.moi_truong_adapter(hh.SANDBOX), "sandbox")
        self.assertEqual(hh.moi_truong_adapter(hh.LIVE), "production")

    def test_b5_sau_muc_dung_bo_va_khong_lech_voi_webhook(self):
        self.assertEqual(len(hh.SAU_MUC), 6)
        self.assertEqual(len(set(hh.SAU_MUC)), 6)
        for m in webhook.MUC_HOP_LE:
            self.assertIn(m, hh.SAU_MUC,
                          "mức của webhook.py phải nằm trong bộ sáu mức — hai bản danh sách"
                          " là hai bản sẽ lệch nhau")
        self.assertEqual(set(hh.SAU_MUC) - set(webhook.MUC_HOP_LE), {hh.IMPLEMENTED})


class C_SandboxVaLiveBiTuChoi(unittest.TestCase):
    """NHÓM QUAN TRỌNG NHẤT: thiếu điều kiện thì TỪ CHỐI, không rơi về MOCK."""

    def test_c1_sandbox_khong_co_gi_thi_tu_choi(self):
        with self.assertRaises(hh.ThieuCauHinh) as c:
            hh.chay("jt", hh.SANDBOX, moi_truong_os={})
        self.assertEqual(c.exception.che_do, hh.SANDBOX)
        self.assertTrue(c.exception.thieu)

    def test_c2_sandbox_khong_AM_THAM_roi_ve_mock(self):
        """Ca canh thẳng vào kiểu hỏng đã nêu ở đầu file harness."""
        try:
            kq = hh.chay("jt", hh.SANDBOX, moi_truong_os={})
        except hh.ThieuCauHinh:
            return
        self.fail(f"SANDBOX thiếu credentials mà vẫn chạy và trả che_do={kq.che_do!r} —"
                  " đây là kiểu rơi về MOCK rồi báo đạt mà §12.1 cấm")

    def test_c3_thong_diep_tu_choi_noi_CHINH_XAC_thieu_gi(self):
        thieu = hh.thieu_gi_de_chay(hh.SANDBOX, "jt", {})
        chuoi = " | ".join(thieu)
        self.assertIn(hh.BIEN_DUYET, chuoi)
        self.assertIn(hh.BIEN_NGUOI_DUYET, chuoi)
        self.assertIn(hh.BIEN_CRED_FILE, chuoi)
        self.assertIn("CHO_PHEP_LIVE=False", chuoi)

    def test_c4_du_quyen_du_nguoi_van_thieu_credentials(self):
        env = {hh.BIEN_DUYET: "V-G09-01", hh.BIEN_NGUOI_DUYET: "anh Thành"}
        thieu = hh.thieu_gi_de_chay(hh.SANDBOX, "jt", env)
        self.assertTrue(any(hh.BIEN_CRED_FILE in t for t in thieu), thieu)

    def test_c5_credentials_thieu_truong_thi_noi_ro_truong_nao(self):
        env = {hh.BIEN_DUYET: "V-G09-01", hh.BIEN_NGUOI_DUYET: "anh Thành"}
        thieu = hh.thieu_gi_de_chay(hh.SANDBOX, "jt", env,
                                    cred={"apiAccount": "1", "privateKey": "2"})
        self.assertTrue(any("customerCode" in t for t in thieu), thieu)
        self.assertTrue(any("password" in t for t in thieu), thieu)

    def test_c6_ma_viec_sai_thi_van_tu_choi(self):
        env = {hh.BIEN_DUYET: "V-TU-NGHI-RA", hh.BIEN_NGUOI_DUYET: "ai đó"}
        thieu = hh.thieu_gi_de_chay(hh.SANDBOX, "jt", env, cred=dict(CRED_JT_DU))
        self.assertTrue(any("quyền chưa cấp" in t for t in thieu), thieu)

    def test_c7_du_HET_dieu_kien_mem_van_bi_CHO_PHEP_LIVE_chan(self):
        """Ổ khoá thứ tư nằm trong app/adapter.py — G09 không sửa được, và đó là chủ đích."""
        env = {hh.BIEN_DUYET: "V-G09-01", hh.BIEN_NGUOI_DUYET: "anh Thành"}
        thieu = hh.thieu_gi_de_chay(hh.SANDBOX, "jt", env, cred=dict(CRED_JT_DU))
        self.assertEqual(len(thieu), 1, thieu)
        self.assertIn("CHO_PHEP_LIVE=False", thieu[0])
        with self.assertRaises(hh.ThieuCauHinh):
            hh.chay("jt", hh.SANDBOX, cred=dict(CRED_JT_DU), moi_truong_os=env)

    def test_c8_vtp_chap_nhan_hai_cach_xac_thuc(self):
        env = {hh.BIEN_DUYET: "V-G09-01", hh.BIEN_NGUOI_DUYET: "anh Thành"}
        chi_token = hh.thieu_gi_de_chay(hh.SANDBOX, "vtp", env, cred={"vtp_token": "t"})
        chi_mk = hh.thieu_gi_de_chay(hh.SANDBOX, "vtp", env,
                                     cred={"vtp_username": "u", "vtp_password": "p"})
        khong_gi = hh.thieu_gi_de_chay(hh.SANDBOX, "vtp", env, cred={"vtp_username": "u"})
        for ds in (chi_token, chi_mk):
            self.assertFalse([t for t in ds if "credentials vtp" in t], ds)
        self.assertTrue([t for t in khong_gi if "credentials vtp" in t], khong_gi)

    def test_c9_live_thieu_phieu_duyet_thi_tu_choi(self):
        with self.assertRaises(hh.ThieuCauHinh):
            hh.chay("jt", hh.LIVE, moi_truong_os={})

    def test_c10_live_co_du_co_moi_truong_van_thieu_phieu(self):
        """Một cờ môi trường là KHÔNG đủ — đúng yêu cầu của chỉ thị G09."""
        env = {hh.BIEN_CHE_DO: "LIVE", hh.BIEN_DUYET: "V-G09-01",
               hh.BIEN_NGUOI_DUYET: "anh Thành"}
        thieu = hh.thieu_gi_de_chay(hh.LIVE, "jt", env, cred=dict(CRED_JT_DU))
        self.assertEqual([t for t in thieu if "CHO_PHEP_LIVE" in t], thieu,
                         "chỉ còn đúng ổ khoá adapter; các ổ mềm đã mở")
        with self.assertRaises(hh.ThieuCauHinh):
            hh.chay("jt", hh.LIVE, cred=dict(CRED_JT_DU), moi_truong_os=env)


class D_PhieuDuyetLive(unittest.TestCase):

    def _phieu(self, thao_tac="createOrder", **kw):
        d = {"thao_tac": thao_tac, "ma_tham_chieu": "DON-1", "nguoi_duyet": "anh Thành",
             "ma_viec": "V-G09-01", "han_den_epoch": time.time() + 600}
        d.update(kw)
        return hh.PhieuDuyetLive(**d)

    def test_d1_phieu_chi_cho_thao_tac_ghi(self):
        with self.assertRaises(ValueError):
            self._phieu("trackOrder")

    def test_d2_phieu_doi_du_nguoi_duyet_va_ma_viec(self):
        for truong in ("nguoi_duyet", "ma_viec", "ma_tham_chieu"):
            with self.assertRaises(ValueError, msg=truong):
                self._phieu(**{truong: "  "})

    def test_d3_phieu_qua_han_la_khong_hop_le(self):
        p = self._phieu(han_den_epoch=time.time() - 1)
        self.assertTrue(any("quá hạn" in l for l in p.kiem("createOrder", "DON-1")))

    def test_d4_phieu_sai_thao_tac_hoac_sai_tham_chieu_thi_hong(self):
        p = self._phieu()
        self.assertTrue(p.kiem("cancelOrder", "DON-1"))
        self.assertTrue(p.kiem("createOrder", "DON-KHAC"))
        self.assertEqual(p.kiem("createOrder", "DON-1"), [])

    def test_d5_phieu_dung_mot_lan(self):
        p = self._phieu()
        self.assertEqual(p.kiem("createOrder", "DON-1"), [])
        p.danh_dau_da_dung()
        self.assertTrue(any("một lần" in l for l in p.kiem("createOrder", "DON-1")))

    def test_d6_phieu_ma_viec_ngoai_danh_sach_cap_quyen_thi_hong(self):
        p = self._phieu(ma_viec="V-TU-BIA")
        self.assertTrue(any("không nằm trong" in l for l in p.kiem("createOrder", "DON-1")))

    def test_d7_live_doi_phieu_cho_TUNG_thao_tac_ghi(self):
        with self.assertRaises(hh.ThieuPhieuDuyet) as c:
            hh._kiem_phieu_duyet_live([self._phieu("createOrder")])
        self.assertTrue(any("cancelOrder" in t for t in c.exception.thieu))

    def test_d8_phieu_khong_mang_bi_mat_nao(self):
        d = self._phieu().nhu_dict()
        self.assertEqual(set(d), {"thao_tac", "ma_tham_chieu", "nguoi_duyet", "ma_viec",
                                  "han_den_epoch", "ghi_chu", "da_dung"})


class E_BangSauMuc(unittest.TestCase):

    def test_e1_moi_dong_co_du_muc_va_do_bang_gi(self):
        bang = hh.bang_san_sang()
        self.assertEqual(set(bang), set(hh.NEN_SAN_SANG))
        for hang, dong in bang.items():
            self.assertEqual(set(dong), set(hh.HANG_MUC), hang)
            for hm, o in dong.items():
                self.assertIn(o["muc"], hh.SAU_MUC, f"{hang}/{hm}")
                self.assertTrue(o["do_bang_gi"].strip(), f"{hang}/{hm} không nói đo bằng gì")

    def test_e2_khong_co_duong_nao_ra_SANDBOX_hay_LIVE_VERIFIED(self):
        """Luật cứng của chỉ thị: cấm báo SANDBOX VERIFIED khi chưa kiểm thử thật."""
        for nguon in (None, hh.chay_tat_ca(hh.MOCK, moi_truong_os={})):
            for hang, dong in hh.bang_san_sang(nguon).items():
                for hm, o in dong.items():
                    self.assertNotIn(o["muc"], (hh.SANDBOX_VERIFIED, hh.LIVE_VERIFIED),
                                     f"{hang}/{hm} tự nhận mức chưa hề đo được")

    def test_e3_chua_chay_thi_khong_hang_muc_nao_duoc_la_MOCK_VERIFIED(self):
        for hang, dong in hh.bang_san_sang(None).items():
            for hm, o in dong.items():
                self.assertNotEqual(o["muc"], hh.MOCK_VERIFIED,
                                    f"{hang}/{hm} nhận MOCK VERIFIED mà chưa chạy ca nào")

    def test_e4_chay_xong_thi_hang_muc_co_ca_phu_duoc_nang(self):
        ra = hh.chay_tat_ca(hh.MOCK, moi_truong_os={})
        bang = hh.bang_san_sang(ra)
        self.assertEqual(bang["jt"]["chu_ky_request"]["muc"], hh.MOCK_VERIFIED)
        self.assertEqual(bang["jt"]["ma_loi"]["muc"], hh.MOCK_VERIFIED)
        # Hạng mục KHÔNG có ca phủ thì đứng yên — không được nâng theo đà.
        self.assertEqual(bang["jt"]["huy_don"]["muc"], hh.DOCUMENTED)
        self.assertEqual(bang["jt"]["bao_gia"]["muc"], hh.DOCUMENTED)

    def test_e5_ca_hong_thi_hang_muc_KHONG_duoc_nang(self):
        ra = hh.chay_tat_ca(hh.MOCK, moi_truong_os={})
        for c in ra["jt"].cac_ca:
            if c.ma_ca == "B1":
                c.ket_qua = "hong"
        self.assertEqual(hh.bang_san_sang(ra)["jt"]["chu_ky_request"]["muc"], hh.IMPLEMENTED)

    def test_e6_gioi_han_tan_suat_jt_la_BLOCKED(self):
        o = hh.bang_san_sang()["jt"]["gioi_han_tan_suat"]
        self.assertEqual(o["muc"], hh.BLOCKED)
        self.assertIn("không phải trần tần suất", o["do_bang_gi"])

    def test_e7_vtp_ma_loi_va_nhan_van_don_la_BLOCKED(self):
        bang = hh.bang_san_sang()["vtp"]
        self.assertEqual(bang["ma_loi"]["muc"], hh.BLOCKED)
        self.assertEqual(bang["nhan_van_don"]["muc"], hh.BLOCKED)


class F_BaoCao(unittest.TestCase):

    def test_f1_ket_luan_dung_ba_dong_bat_buoc(self):
        bc = hh.bao_cao_san_sang(hh.chay_tat_ca(hh.MOCK, moi_truong_os={}))
        self.assertEqual(set(bc["ket_luan"]),
                         {"G09 LOCAL READY", "G09 SANDBOX", "G09 LIVE"})
        self.assertEqual(bc["ket_luan"]["G09 LOCAL READY"], "PASS")
        self.assertEqual(bc["ket_luan"]["G09 SANDBOX"], hh.BLOCKED)
        self.assertEqual(bc["ket_luan"]["G09 LIVE"], hh.BLOCKED)

    def test_f2_chua_chay_thi_LOCAL_READY_la_FAIL_khong_phai_PASS(self):
        self.assertEqual(hh.bao_cao_san_sang(None)["ket_luan"]["G09 LOCAL READY"], "FAIL")

    def test_f3_bao_cao_noi_ro_thieu_gi_de_len_sandbox_va_live(self):
        bc = hh.bao_cao_san_sang(None)
        for hang, o in bc["hang"].items():
            self.assertTrue(o["thieu_de_sandbox"], hang)
            self.assertTrue(o["thieu_de_live"], hang)

    def test_f4_danh_sach_can_soat_co_jt_110(self):
        ds = hh.danh_sach_can_soat("jt")
        self.assertTrue(any(d["ma"] == 110 and d["nhan"] == "AMBIGUOUS"
                            and d["trang_thai_ap"] is None for d in ds), ds)
        self.assertTrue(all(len(d["cac_nghia"]) >= 2 for d in ds))

    def test_f5_can_soat_phan_anh_so_chot_THAT_khong_cung_nhac(self):
        try:
            tth.chot_nghia("jt", 110, "bang_tham_so", "ca-thu", "căn cứ ca thử")
            self.assertTrue(hh.danh_sach_can_soat("jt")[0]["da_chot"])
        finally:
            tth.bo_chot_nghia("jt", 110)
        self.assertFalse(hh.danh_sach_can_soat("jt")[0]["da_chot"])

    def test_f6_bao_cao_khong_lo_credentials(self):
        import json as _j
        van = _j.dumps(hh.bao_cao_san_sang(hh.chay_tat_ca(hh.MOCK, moi_truong_os={})),
                       ensure_ascii=False, default=str)
        for xau in ("KHOA-BI-MAT", "MAT-KHAU-XYZ", "KHOA-THU-MOCK", "MK-THU"):
            self.assertNotIn(xau, van, f"báo cáo lộ '{xau}'")


class G_AnToan(unittest.TestCase):

    def test_g1_harness_khong_co_ma_goi_mang(self):
        with open(os.path.join(GOC_APP, "harness_hang.py"), encoding="utf-8") as f:
            nguon = f.read()
        for cam in ("import requests", "import httpx", "urllib.request", "http.client",
                    "socket.socket", "urlopen"):
            self.assertNotIn(cam, nguon, f"harness có mã gọi mạng ('{cam}')")

    def test_g2_harness_khong_sua_CHO_PHEP_LIVE_o_dau(self):
        # Đọc bằng AST, không bằng tìm chuỗi. Hai bản trước của ca này đều báo HỎNG GIẢ: bản
        # một bắt nhầm câu chú thích mô tả ổ khoá, bản hai bắt nhầm một chuỗi f-string chỉ ĐỌC
        # hằng ra để in. Phép đo sai làm hỏng đúng công dụng của ca canh (§12.1).
        import ast
        with open(os.path.join(GOC_APP, "harness_hang.py"), encoding="utf-8") as f:
            cay = ast.parse(f.read())
        KHOA_AN_TOAN = {"CHO_PHEP_LIVE", "KHOA_CHONG_TRUNG", "CAPABILITIES"}
        for nut in ast.walk(cay):
            dich = []
            if isinstance(nut, ast.Assign):
                dich = nut.targets
            elif isinstance(nut, (ast.AugAssign, ast.AnnAssign)):
                dich = [nut.target]
            for d in dich:
                ten = d.attr if isinstance(d, ast.Attribute) else getattr(d, "id", None)
                self.assertNotIn(ten, KHOA_AN_TOAN,
                                 f"harness GÁN vào khoá an toàn '{ten}' ở dòng {nut.lineno}")
            if isinstance(nut, ast.Call) and getattr(nut.func, "id", "") == "setattr":
                self.fail(f"harness dùng setattr() ở dòng {nut.lineno} — đường vòng để ghi đè"
                          " hằng của adapter")

    def test_g3_moi_adapter_van_dong_CHO_PHEP_LIVE(self):
        for ma, lop in adapter._DANG_KY.items():
            self.assertFalse(lop.CHO_PHEP_LIVE, f"{ma} đã bị mở đường LIVE")

    def test_g4_ddl_g09_khong_co_cot_tien_kieu_thuc(self):
        """Mục 16: cấm REAL/FLOAT cho tiền. Bảng harness không có cột tiền nào."""
        hoa = hh.DDL_G09.upper()
        for cam in (" REAL", " FLOAT", " DOUBLE", "NUMERIC", "DECIMAL"):
            self.assertNotIn(cam, hoa, f"DDL_G09 có kiểu {cam.strip()}")

    def test_g5_ddl_g09_chay_duoc_tren_sqlite(self):
        import sqlite3
        con = sqlite3.connect(":memory:")
        con.executescript("CREATE TABLE tenants (id INTEGER PRIMARY KEY);" + hh.DDL_G09)
        bang = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("g09_harness_lan_chay", bang)
        self.assertIn("g09_harness_ca", bang)
        con.close()

    def test_g6_chua_cam_migration_thi_luu_tra_None_khong_nuot_im(self):
        """AG-00 chưa viết migration v8 ⇒ bảng chưa có ⇒ phải NÓI RA, không giả vờ đã ghi."""
        kq = hh.chay("jt", hh.MOCK, moi_truong_os={})
        if hh.co_bang_harness():
            self.assertIsNotNone(hh.luu_lan_chay(kq, nguoi_chay="ca-thu"))
        else:
            self.assertIsNone(hh.luu_lan_chay(kq, nguoi_chay="ca-thu"))

    def test_g7_hang_chua_co_adapter_thi_bao_loi_khong_chay_bua(self):
        with self.assertRaises(KeyError):
            hh.chay("hang-khong-co-that", hh.MOCK, moi_truong_os={})


def _co_node():
    import shutil
    return shutil.which("node") is not None


@unittest.skipUnless(_co_node(), "máy không có node — ca này BỎ QUA, không coi là đạt")
class H_ManSucKhoeHang(unittest.TestCase):
    """Màn `admin/carrier_health.js` chạy bằng Node trên dữ liệu THẬT của backend.

    Vì sao đặt ở đây chứ không ở `thu_frontend/thu_logic.mjs`: file đó thuộc AG-06, đợt này
    G09 CHỈ ĐỌC. Ca dưới đây gọi Node từ Python nên không phải ghi vào làn người khác.
    """

    @classmethod
    def setUpClass(cls):
        import json
        import subprocess
        cls.GOC = os.path.dirname(GOC_APP)
        bc = hh.bao_cao_san_sang(hh.chay_tat_ca(hh.MOCK, moi_truong_os={}))
        cls.bc_json = json.dumps(bc, ensure_ascii=False, default=str)
        kich_ban = r"""
const fs = require('fs');
const H = require(process.argv[2]);
const bc = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const man = H.dungMan(bc);
const ra = {
  muc_cua_man: Object.keys(H.MUC),
  so_hang: man.hang.length,
  ket_luan: man.ket_luan.map(k => k.ten + '=' + k.gia_tri + '/' + k.lop),
  dong_thieu_do_bang_gi: man.hang.flatMap(h => h.bang.filter(d => d.thieu_do_bang_gi)
                                                     .map(d => h.ma + '/' + d.ma)),
  muc_la: man.hang.flatMap(h => h.bang.filter(d => d.muc_la).map(d => h.ma + '/' + d.ma)),
  can_soat: man.can_soat_tat_ca.map(c => c.ma + ':' + c.nhan + ':' + c.khong_doi_trang_thai
                                         + ':' + c.cho_phep_chot_tren_man),
  ngat_mach_chua_do: H.ngatMach(null).biet,
  che_bi_mat: JSON.stringify(H.locBiMat({privateKey: 'LO', a: {password: 'LO'}})),
  canh_bao_cao: man.canh_bao.filter(c => c.muc === 'cao').map(c => c.chu),
};
process.stdout.write(JSON.stringify(ra));
"""
        import tempfile as _tf
        cls.tam = _tf.mkdtemp(prefix="g09-node-")
        with open(os.path.join(cls.tam, "kb.js"), "w", encoding="utf-8") as f:
            f.write(kich_ban)
        with open(os.path.join(cls.tam, "bc.json"), "w", encoding="utf-8") as f:
            f.write(cls.bc_json)
        p = subprocess.run(
            ["node", os.path.join(cls.tam, "kb.js"),
             os.path.join(cls.GOC, "admin", "carrier_health.js"),
             os.path.join(cls.tam, "bc.json")],
            capture_output=True, text=True)
        if p.returncode != 0:
            raise AssertionError(f"chạy carrier_health.js bằng Node hỏng: {p.stderr}")
        cls.ra = json.loads(p.stdout)

    def test_h1_cu_phap_js_dat(self):
        import subprocess
        p = subprocess.run(["node", "--check",
                            os.path.join(self.GOC, "admin", "carrier_health.js")],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_h2_sau_muc_cua_man_KHOP_voi_backend(self):
        """Hai bản danh sách là hai bản sẽ lệch nhau — ca này là chỗ bắt lúc chúng lệch."""
        self.assertEqual(sorted(self.ra["muc_cua_man"]), sorted(hh.SAU_MUC))

    def test_h3_man_khong_gap_muc_la_va_khong_thieu_do_bang_gi(self):
        self.assertEqual(self.ra["muc_la"], [])
        self.assertEqual(self.ra["dong_thieu_do_bang_gi"], [])

    def test_h4_man_hien_dung_ba_dong_ket_luan(self):
        self.assertEqual(self.ra["ket_luan"],
                         ["G09 LOCAL READY=PASS/hh-xanh",
                          "G09 SANDBOX=BLOCKED/hh-vang",
                          "G09 LIVE=BLOCKED/hh-vang"])

    def test_h5_man_hien_jt_110_va_KHONG_cho_chot_nghia_tren_man(self):
        self.assertIn("110:AMBIGUOUS:true:false", self.ra["can_soat"])

    def test_h6_ngat_mach_chua_do_thi_KHONG_bao_binh_thuong(self):
        self.assertFalse(self.ra["ngat_mach_chua_do"],
                         "chưa có dữ liệu mà màn dám nói ngắt mạch bình thường")

    def test_h7_man_che_moi_truong_nghi_la_bi_mat(self):
        self.assertNotIn("LO", self.ra["che_bi_mat"])

    def test_h8_khong_co_canh_bao_muc_cao_tren_du_lieu_sach(self):
        self.assertEqual(self.ra["canh_bao_cao"], [])

    def test_h9_admin_khong_co_thu_muc_con(self):
        duong = os.path.join(self.GOC, "admin")
        con = [t for t in os.listdir(duong) if os.path.isdir(os.path.join(duong, t))]
        self.assertEqual(con, [], f"admin/ có thư mục con: {con}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
