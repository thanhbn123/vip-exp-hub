#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R2 — ĐỐI CHỨNG ÂM cho các bộ quét/ hợp đồng đã sửa ở nhánh `best/integration`.

VÌ SAO CÓ TỆP NÀY
-----------------
Ba bộ QA cũ đỏ vì KỲ VỌNG CŨ / BỘ DÒ NHÌN SAI CHỖ, không phải vì sản phẩm hỏng:
  · `thu_qa_g16` — AST coi 3 CÂU THÔNG BÁO LỖI trong `MA_LOI` là credential hard-code;
  · `thu_qa_jt`  — cấm gốc `urllib` nên bắt `urllib.parse` (chỉ tách URL, không I/O);
  · `thu_qa_soat`— đòi 200 cho `GET /don?tenant_id=…` trong khi hợp đồng G22 TỪ CHỐI 400;
  · `thu_tich_hop` — `test_05` grep trúng `http.client` trong CHÚ THÍCH; `test_09` GIỮ R7.

Tệp này KHÔNG sửa sản phẩm và KHÔNG nới cổng. Nó làm ba việc:
  1. chạy THẬT bốn bộ, ghi exit + số ca + FAIL/ERROR + bỏ qua;
  2. TIÊM LẠI lỗi tương ứng (secret thật, I/O thật) và đòi bộ dò PHẢI thấy — đối chứng âm;
  3. đòi đường AN TOÀN (thông báo lỗi, `urllib.parse`, chú thích) KHÔNG bị kêu — đối chứng dương.

`thu_tich_hop.test_09` vẫn ĐỎ có chủ đích: luật "chỉ `http_jt.py` được nói chuyện với mạng"
mâu thuẫn với các mô-đun BEST mới (`http_best.py`, `xac_thuc_best.py`) mà
`docs/BEST_EXPRESS_API_CONTRACT.md` lại chủ động đưa vào. Chưa đủ căn cứ để sửa — GIỮ R7,
báo AG-00 chốt hợp đồng. Tệp này KHÔNG được coi là cổng nghiệm thu cho R7.

Chạy: `python3 app/thu/thu_r2_hopdong.py -v`
"""
import ast
import atexit
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC_THU = os.path.dirname(os.path.abspath(__file__))
GOC_APP = os.path.dirname(GOC_THU)
GOC_REPO = os.path.dirname(GOC_APP)
BO = ("thu_qa_g16", "thu_qa_jt", "thu_qa_soat", "thu_tich_hop")

_TAM = tempfile.mkdtemp(prefix="r2-hopdong-")
atexit.register(shutil.rmtree, _TAM, True)
os.environ.setdefault("VIP_HUB_DATA", _TAM)

# Tiêm vào cả phép gán, dict cấu hình, và CHÍNH mã lỗi từng bị bắt nhầm.
SECRET_TIEM = "Xk9#mQ2$vL7@nR4"
MA_LOI_BI_BAT_NHAM = ("CREDENTIAL_KHONG_HOP_LE", "TOKEN_KHONG_HOP_LE",
                      "CREDENTIAL_DA_DOI_KHONG_LUU")


def _moi_truong(data):
    """Môi trường đo: git sạch biến hỏng, kho tạm riêng, chỉ loopback, không kho nghiệp vụ."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    e.pop("VIP_KHO_DANG_CHAY", None)
    e.update(VIP_HUB_DATA=data, VIP_HUB_BIND="127.0.0.1", VIP_JT_MOI_TRUONG="mock",
             PYTHONDONTWRITEBYTECODE="1")
    return e


def chay_bo(ten):
    """Chạy THẬT một bộ trong tiến trình con; trả exit, số ca, FAIL/ERROR, bỏ qua."""
    with tempfile.TemporaryDirectory(prefix="r2-chay-") as data:
        p = subprocess.run([sys.executable, os.path.join(GOC_THU, ten + ".py")],
                           cwd=GOC_REPO, capture_output=True, text=True,
                           env=_moi_truong(data), timeout=300)
    ra = p.stdout + p.stderr
    m = re.search(r"^Ran (\d+) test", ra, re.M)
    fail = re.findall(r"^(?:FAIL|ERROR): ([^\s(]+)", ra, re.M)
    bo_qua = len(re.findall(r"\.\.\. skipped", ra))
    tong_ket = re.search(r"^(?:OK|FAILED)\s*(?:\(([^)]*)\))?", ra, re.M)
    if tong_ket and tong_ket.group(1):
        s = re.search(r"skipped=(\d+)", tong_ket.group(1))
        if s:
            bo_qua = max(bo_qua, int(s.group(1)))
    return {"ma": p.returncode, "ca": int(m.group(1)) if m else 0,
            "fail": fail, "bo_qua": bo_qua, "ra": ra}


def _nap(ten):
    """Nạp CHÍNH mô-đun bộ thử đã sửa để gọi lại đúng hàm dò của nó."""
    duong = os.path.join(GOC_THU, ten + ".py")
    spec = importlib.util.spec_from_file_location("r2_" + ten, duong)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _doc(ten):
    with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
        return f.read()


def _gia_tri_dict_ma_loi(nguon, ten_bien="MA_LOI"):
    """Đọc các giá trị của `MA_LOI` bằng AST — bảng 'thông báo lỗi vs secret' từ mã THẬT."""
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == ten_bien for t in nut.targets):
            if isinstance(nut.value, ast.Dict):
                return {k.value: v.value for k, v in zip(nut.value.keys, nut.value.values)
                        if isinstance(k, ast.Constant) and isinstance(k.value, str)
                        and isinstance(v, ast.Constant) and isinstance(v.value, str)}
    raise AssertionError(f"không tìm thấy {ten_bien} dạng dict trong nguồn")


def _ca_da_chay(ra, ten_ca):
    """Ca mục tiêu có mặt trong output -v (unittest in tên ca cả khi pass)."""
    return ten_ca in ra


def _ca_khong_hong(fail, ten_ca):
    """Ca mục tiêu KHÔNG nằm trong danh sách FAIL/ERROR."""
    return not any(ten_ca in f for f in fail)


def _chay_mot_ca(mod, ten_ca):
    """Chạy ĐÚNG MỘT ca của mô-đun đã nạp (nuốt output) — dùng cho phép đột biến."""
    bo = unittest.defaultTestLoader.loadTestsFromName(ten_ca, mod)
    return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(bo)


class R2_HopDong(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kq = {}
        for ten in BO:
            cls.kq[ten] = chay_bo(ten)
        print("\nBỘ THỬ                | exit | ca | FAIL/ERROR | bỏ qua")
        for ten in BO:
            r = cls.kq[ten]
            print(f"{ten:22s}| {r['ma']:4d} | {r['ca']:2d} | {len(r['fail']):10d} | "
                  f"{r['bo_qua']:6d}")

    # ── 1. Bốn bộ chạy THẬT: exit + số ca + FAIL/ERROR + bỏ qua ──────────────────────────
    def test_01_g16_exit_0_du_61_ca(self):
        r = self.kq["thu_qa_g16"]
        self.assertEqual(r["ma"], 0, r["ra"][-3000:])
        self.assertEqual(r["ca"], 61, "số ca đã đổi — không cộng test con/hai lần")
        self.assertEqual(r["fail"], [])
        self.assertEqual(r["bo_qua"], 0)
        self.assertTrue(_ca_da_chay(r["ra"], "test_c5_khong_hard_code_secret"),
                        "ca c5 không chạy")
        self.assertTrue(_ca_khong_hong(r["fail"], "test_c5_khong_hard_code_secret"))

    def test_02_jt_exit_0_du_22_ca(self):
        r = self.kq["thu_qa_jt"]
        self.assertEqual(r["ma"], 0, r["ra"][-3000:])
        self.assertEqual(r["ca"], 22)
        self.assertEqual(r["fail"], [])
        self.assertEqual(r["bo_qua"], 0)
        self.assertTrue(_ca_da_chay(r["ra"], "test_a4_khong_co_duong_cham_mang"),
                        "ca a4 không chạy")
        self.assertTrue(_ca_khong_hong(r["fail"], "test_a4_khong_co_duong_cham_mang"))

    def test_03_soat_exit_0_du_30_ca(self):
        r = self.kq["thu_qa_soat"]
        self.assertEqual(r["ma"], 0, r["ra"][-3000:])
        self.assertEqual(r["ca"], 30)
        self.assertEqual(r["fail"], [])
        self.assertEqual(r["bo_qua"], 0)
        self.assertTrue(_ca_da_chay(r["ra"], "test_q09f_ANTOAN_tenant_id"),
                        "ca q09f không chạy")
        self.assertTrue(_ca_khong_hong(r["fail"], "test_q09f_ANTOAN_tenant_id"))

    def test_04_tich_hop_12_ca_test05_xanh_test09_GIU_R7(self):
        r = self.kq["thu_tich_hop"]
        self.assertEqual(r["ca"], 12)
        self.assertEqual(r["ma"], 1, "R7 phải còn ĐỎ; không được nới cổng để xanh")
        self.assertEqual(len(r["fail"]), 1, f"FAIL lạ: {r['fail']}")
        self.assertIn("test_09_", r["fail"][0], f"R7 không còn là test_09: {r['fail']}")
        self.assertEqual(r["bo_qua"], 0, "không được thêm skip để né R7")
        self.assertTrue(_ca_da_chay(r["ra"], "test_05_adapter_khong_co_duong_goi_mang"),
                        "test_05 không chạy")
        self.assertTrue(_ca_khong_hong(r["fail"], "test_05_adapter_khong_co_duong_goi_mang"),
                        "test_05 vẫn đỏ")

    # ── 2. G16: thông báo lỗi vs secret + tiêm secret thật ───────────────────────────────
    def test_05_g16_bang_thong_bao_loi_vs_secret(self):
        g16 = _nap("thu_qa_g16")
        nguon = _doc("xac_thuc_best.py")
        gia_tri = _gia_tri_dict_ma_loi(nguon)
        thieu = [k for k in MA_LOI_BI_BAT_NHAM if k not in gia_tri]
        self.assertEqual(thieu, [], f"MA_LOI đã đổi tên khoá: thiếu {thieu}")
        self.assertEqual(g16.quet_hardcode(nguon), [],
                         "còn dương tính giả trên mã sản phẩm THẬT")
        print("\nMÃ LỖI                               | là CÂU? | câu bị kêu? | "
              "cùng mã + secret bị bắt?")
        for khoa in MA_LOI_BI_BAT_NHAM:
            v = gia_tri[khoa]
            cau = g16._la_cau_thong_bao(khoa, v)
            # Bộ dò CŨ (không có luật 4) SẼ kêu 3 giá trị này — đột biến có thật, không phải
            # "đã vốn không kêu". Đây là đối chứng rằng luật ngữ cảnh đang LÀM VIỆC.
            cu_se_keu = bool(g16.TEN_NHAY_CAM.match(khoa) and g16._du_manh(v)
                             and not g16._la_giu_cho(v))
            mau_thong_bao = 'MA_LOI = {%r: %r}\n' % (khoa, v)
            mau_secret = 'MA_LOI = {%r: %r}\n' % (khoa, SECRET_TIEM)
            sach = g16.quet_hardcode(mau_thong_bao)
            bat = g16.quet_hardcode(mau_secret)
            print(f"{khoa:36s} | {str(cau):7s} | {str(bool(sach)):11s} | "
                  f"{str(bool(bat)):24s}")
            self.assertTrue(cau, f"{khoa}: câu thông báo lỗi bị coi là secret")
            self.assertTrue(cu_se_keu, f"{khoa}: không tái hiện được dương tính giả cũ")
            self.assertEqual(sach, [], f"{khoa}: câu thông báo lỗi vẫn bị kêu")
            self.assertTrue(bat, f"{khoa}: TIÊM secret vào CÙNG mã lỗi mà bộ dò im")
        # Đối chứng âm ở ba ngữ cảnh khác: phép gán, dict cấu hình, và bản sao tệp THẬT.
        self.assertTrue(g16.quet_hardcode('password = %r\n' % SECRET_TIEM))
        self.assertTrue(g16.quet_hardcode('CFG = {"privateKey": %r}\n' % SECRET_TIEM))
        ban_sao = nguon + ('\nTOKEN_TIEM = %r\nMA_LOI_TIEM = {"TOKEN_KHONG_HOP_LE": %r}\n'
                           % (SECRET_TIEM, SECRET_TIEM))
        self.assertTrue(g16.quet_hardcode(ban_sao),
                        "tiêm secret vào bản sao xac_thuc_best.py mà bộ dò KHÔNG thấy")
        # Đường an toàn: tên trường bí mật chuẩn vẫn bị bắt dù giá trị là câu nhiều từ.
        self.assertTrue(g16.quet_hardcode('PASSWORD = "correct horse battery staple"\n'))

    # ── 3. JT: urllib.parse vs I/O thật ─────────────────────────────────────────────────
    def test_06_jt_parse_khong_phai_io_va_tiem_io_that(self):
        jt = _nap("thu_qa_jt")
        self.assertEqual(jt._vi_pham_io_mang(_doc("adapter_best.py")), [],
                         "adapter_best.py chỉ dùng urllib.parse; không được coi là I/O")
        self.assertEqual(jt._vi_pham_io_mang("from urllib.parse import urlsplit\n"), [])
        self.assertEqual(jt._vi_pham_io_mang("# import urllib.request\n"), [])
        for mau in ("import urllib.request\n", "from urllib import request\n",
                    "import http.client\n", "import socket\n",
                    "urllib.request.urlopen(u)\n"):
            with self.subTest(tiem=mau.strip()):
                self.assertTrue(jt._vi_pham_io_mang(mau),
                                f"tiêm I/O thật {mau.strip()!r} mà bộ dò im")

    # ── 4. Tích hợp: test_05 chú thích vs mã thật ───────────────────────────────────────
    def test_07_tich_hop_test05_chu_thich_khong_phai_ma(self):
        th = _nap("thu_tich_hop")
        self.assertEqual(th._vi_pham_nhap_mang(_doc("adapter_best.py")), [])
        self.assertEqual(th._vi_pham_nhap_mang("# import http.client trong chú thích\n"), [],
                         "chú thích không phải mã chạy")
        self.assertEqual(th._vi_pham_nhap_mang("from urllib.parse import urlsplit\n"), [])
        for mau in ("import http.client\n", "from urllib import request\n", "import socket\n"):
            with self.subTest(tiem=mau.strip()):
                self.assertTrue(th._vi_pham_nhap_mang(mau),
                                f"tiêm I/O thật {mau.strip()!r} mà bộ dò im")

    # ── 5. Không bộ nào được "xanh" bằng bỏ qua ca ─────────────────────────────────────
    def test_08_khong_bo_qua_ca_nao(self):
        for ten in BO:
            self.assertEqual(self.kq[ten]["bo_qua"], 0, f"{ten} có ca bị bỏ qua")

    # ── 6. ĐỐI CHỨNG ÂM Ở MỨC PHÉP THỬ: tiêm lại KẾT QUẢ dương tính giả / lỗi cũ ──────
    # Mỗi ca dưới đây thay bộ dò (hoặc máy chủ giả) bằng đúng hành vi CŨ và đòi PHÉP THỬ ĐỎ.
    # Nếu bản sửa chỉ làm phép thử xanh bằng cách bỏ assertion, các ca này sẽ không đỏ ⇒ bắt được.
    def test_09_doi_chung_am_g16_c5_do_khi_bo_do_bao_vi_pham(self):
        g16 = _nap("thu_qa_g16")
        goc = g16.quet_hardcode
        # Đúng dương tính giả CŨ: coi câu thông báo lỗi trong MA_LOI là credential.
        g16.quet_hardcode = lambda nguon: [
            "app/xac_thuc_best.py:dòng 91: CREDENTIAL_KHONG_HOP_LE = <literal 75 ký tự>"]
        try:
            kq = _chay_mot_ca(
                g16, "C_Credentials.test_c5_khong_hard_code_secret_trong_ma_san_pham")
        finally:
            g16.quet_hardcode = goc
        self.assertEqual(len(kq.failures) + len(kq.errors), 1,
                         "bộ dò báo dương tính giả mà test_c5 vẫn XANH ⇒ phép thử vô giá trị")

    def test_10_doi_chung_am_jt_a4_do_khi_bat_urllib_parse(self):
        jt = _nap("thu_qa_jt")
        goc = jt._vi_pham_io_mang
        # Đúng lỗi CŨ: `urllib.parse` (xử lý chuỗi) bị coi là I/O.
        jt._vi_pham_io_mang = lambda nguon: ["from urllib.parse import urlsplit"]
        try:
            kq = _chay_mot_ca(
                jt, "A_ChuKyVaTransport.test_a4_khong_co_duong_cham_mang_bang_AST")
        finally:
            jt._vi_pham_io_mang = goc
        self.assertEqual(len(kq.failures) + len(kq.errors), 1,
                         "bắt nhầm urllib.parse mà test_a4 vẫn XANH ⇒ phép thử vô giá trị")

    def test_11_doi_chung_am_tich_hop_test05_do_khi_bat_chu_thich(self):
        th = _nap("thu_tich_hop")
        goc = th._vi_pham_nhap_mang
        # Đúng lỗi CŨ: grep trúng `http.client` trong CHÚ THÍCH.
        th._vi_pham_nhap_mang = lambda nguon: ["adapter_best.py: http.client (trong chú thích)"]
        try:
            kq = _chay_mot_ca(th, "CanhCauTruc.test_05_adapter_khong_co_duong_goi_mang_nao")
        finally:
            th._vi_pham_nhap_mang = goc
        self.assertEqual(len(kq.failures) + len(kq.errors), 1,
                         "bắt nhầm chú thích mà test_05 vẫn XANH ⇒ phép thử vô giá trị")

    def test_12_doi_chung_am_soat_q09f_do_khi_may_chu_tra_200(self):
        from unittest import mock
        soat = _nap("thu_qa_soat")

        class MayChuCu:
            """Hành vi CŨ: bỏ qua im lặng `tenant_id` trong query rồi trả 200."""

            def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
                if method == "POST" and duong == "/api/v2/don":
                    return 201, {"don": {"id": 99}}
                if method == "POST" and duong == "/api/v2/khach-hang":
                    return 201, {"id": 98}
                return 200, {"dong": []}

        ca = soat.ThuQaSoat(
            "test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh")
        ca.a, ca.b = MayChuCu(), MayChuCu()
        ca.tid_a, ca.tid_b = 1, 2
        with mock.patch.object(soat.csdl, "mot", return_value={"tenant_id": 1}):
            with self.assertRaises(AssertionError) as loi:
                ca.test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh()
        self.assertIn("400", str(loi.exception),
                      "phép thử không đỏ vì ĐÚNG lý do hợp đồng 400")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    sys.exit(0 if runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(R2_HopDong))
             .wasSuccessful() else 1)
