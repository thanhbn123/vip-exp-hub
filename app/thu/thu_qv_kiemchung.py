#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QV-01 — KIỂM CHỨNG ĐỘC LẬP BA NHÓM R1 / R2 / R27 TRƯỚC KHI GỘP.

VÌ SAO CÓ TỆP NÀY
-----------------
Ba nhánh `r1-bootstrap` · `r2-hopdong` · `r27-isolation` tự báo ĐẠT. Báo cáo tự khai
KHÔNG phải bằng chứng: một bộ thử sửa để luôn xanh, một phép đếm đọc nhầm, hay một lời
khai "đã chạy lại" đều cho cùng một bảng đẹp. Tệp này chạy LẠI bằng tiến trình riêng, đếm
số ca, và kiểm cả BỐN thứ mà bảng tự khai không chứng minh được:

  1. SỐ CA TRƯỚC/SAU — đọc `c909ebb` (nền của ba nhánh) bằng `git show`, so với cây đang
     đứng: test có bị XOÁ không, assertion có bị BỎ không, có `skip` mới không.
  2. ĐỐI CHỨNG ÂM — tiêm LẠI đúng lỗi rồi đòi phép thử ĐỎ. Không có vế này thì "xanh"
     không chứng minh lời khai là nguyên nhân (một bộ luôn xanh cũng cho cùng bảng).
  3. ĐỐI CHỨNG ĐƯỜNG — đường hợp lệ phải ĐẠT, đo trên SẢN PHẨM (không qua bộ thử đã sửa).
  4. HỢP ĐỒNG — `tenant_id` trong query bị TỪ CHỐI 400 (G12/G22), không bỏ qua im lặng.

KHÔNG sửa sản phẩm, KHÔNG sửa tệp của ba nhóm, KHÔNG ghi `.git`. Mọi thư mục dữ liệu là
`tempfile.mkdtemp()`; biến `GIT_CONFIG_*` hỏng của máy được gỡ cho tiến trình con.

CHẠY
    python3 app/thu/thu_qv_kiemchung.py          # toàn bộ; exit 0 = ĐẠT
    python3 app/thu/thu_qv_kiemchung.py -v       # in thêm bảng số ca từng bộ

KẾT QUẢ ĐỌC THẾ NÀO
    - `thu_tich_hop.py` ĐƯỢC PHÉP đỏ ĐÚNG MỘT ca `test_09` (R7: luật phân tầng mâu thuẫn
      với BEST, chờ AG-00 chốt). Mọi FAIL khác là HỎNG.
    - Mọi con số dưới đây là số ĐO ĐƯỢC ở lượt chạy này, không phải số trong báo cáo nhóm.
"""
import importlib.util
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
BASE_GIT = "c909ebb"          # nền của cả ba nhánh; còn trong lịch sử sau khi gộp

# Bộ đo của từng nhóm. `ca` là số ca runner công bố (`Ran N`), không cộng ca con.
# `ma` là mã thoát ĐÚNG; `fail_cho_phep` là tên ca được phép đỏ (chỉ R7).
BO_DO = [
    # (nhóm, tệp, exit, số ca, ca được phép đỏ, ghi chú)
    ("R1", "thu_g01_g02.py", 0, 21, (), "bootstrap khai kho + hợp đồng test_010/014"),
    ("R1", "thu_g19_route.py", 0, 50, (), "bất biến tập hợp thay ghim 31/103"),
    ("R1", "thu_r1_bootstrap.py", 0, 11, (), "bộ tự kiểm cơ chế khai kho"),
    ("R2", "thu_qa_g16.py", 0, 61, (), "thông báo lỗi ≠ secret"),
    ("R2", "thu_qa_jt.py", 0, 22, (), "urllib.parse ≠ I/O"),
    ("R2", "thu_qa_soat.py", 0, 30, (), "tenant_id trong query ⇒ 400"),
    ("R2", "thu_tich_hop.py", 1, 12, ("test_09_",), "R7 GIỮ ĐỎ CÓ CHỦ ĐÍCH"),
    ("R2", "thu_r2_hopdong.py", 0, 12, (), "harness đột biến của R2"),
    ("R27", "thu_g21_bimat.py", 0, 33, (), "Z4 chỉ canh tài nguyên của chính lượt"),
    ("R27", "thu_g22_chotcay.py", 0, 11, (), "D2 trên bản sao, D4 chọn bản bị bắt"),
    ("R27", "thu_r27_fixture.py", 0, 4, (), "G21 song song + đối chứng âm D2/D4"),
]
E2E = ("R1", "chay_e2e.sh", 0, 41)

# Chín tệp bị sửa — dùng cho phép so "số ca / assertion / skip" trước-sau.
TEP_SUA = [
    "app/thu/chay_e2e.sh",
    "app/thu/thu_g01_g02.py",
    "app/thu/thu_g19_route.py",
    "app/thu/thu_qa_g16.py",
    "app/thu/thu_qa_jt.py",
    "app/thu/thu_qa_soat.py",
    "app/thu/thu_tich_hop.py",
    "app/thu/thu_g21_bimat.py",
    "app/thu/thu_g22_chotcay.py",
]

SKIP_MOI = re.compile(r"skipTest|@unittest\.skip|skip\s*=\s*True|addSkip|pytest\.mark\.skip")
RONG_GIA = re.compile(r"assertTrue\(\s*True\s*\)|assert\s+True\b|except\s*:\s*$")


def _moi_truong(data):
    """Môi trường đo: gỡ biến git hỏng, KHÔNG khai kho, dữ liệu là thư mục tạm."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    e.pop("VIP_KHO_DANG_CHAY", None)
    e.pop("VIP_HUB_DATA", None)
    e.update(VIP_HUB_DATA=data, VIP_HUB_BIND="127.0.0.1", VIP_JT_MOI_TRUONG="mock",
             PYTHONDONTWRITEBYTECODE="1")
    return e


def chay_tep(ten, timeout=600):
    """Chạy THẬT một tệp trong tiến trình con. Trả dict số đo, không đọc lời khai."""
    duong = os.path.join(GOC_THU, ten)
    lenh = ["sh", duong] if ten.endswith(".sh") else [sys.executable, duong]
    with tempfile.TemporaryDirectory(prefix="qv-chay-") as data:
        p = subprocess.run(lenh, cwd=GOC_REPO, capture_output=True, text=True,
                           env=_moi_truong(data), timeout=timeout)
    ra = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"^Ran (\d+) test", ra, re.M)
    fail = re.findall(r"^(?:FAIL|ERROR): (\S+)", ra, re.M)
    skip = 0
    s = re.search(r"skipped=(\d+)", ra)
    if s:
        skip = int(s.group(1))
    else:
        skip = len(re.findall(r"\.\.\. skipped", ra))
    return {"ma": p.returncode, "ca": int(m.group(1)) if m else 0, "fail": fail,
            "skip": skip, "ra": ra}


def _dem_e2e(ra):
    m = re.search(r"KẾT QUẢ: (\d+)/(\d+) phép đo đạt", ra)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def _doc_git(duong):
    """Đọc nội dung một tệp ở nền `BASE_GIT` — phép so TRƯỚC, không tin bản đang có."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    for ref in (BASE_GIT, "HEAD"):
        r = subprocess.run(["git", "show", "%s:%s" % (ref, duong)], cwd=GOC_REPO,
                           capture_output=True, text=True, env=e)
        if r.returncode == 0:
            return r.stdout
    return None


def _dem_ma(nguon):
    """Đếm test / assertion / dấu hiệu nới cổng trong một tệp nguồn."""
    return {
        "test": len(re.findall(r"^\s+def test_", nguon, re.M)),
        "assert": len(re.findall(r"\bself\.assert\w+\(", nguon)),
        "skip": len(SKIP_MOI.findall(nguon)),
        "rong": len(RONG_GIA.findall(nguon)),
    }


class QV_KiemChung(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.kq = {}
        for _, ten, _, _, _, _ in BO_DO:
            cls.kq[ten] = chay_tep(ten)
        cls.kq[E2E[1]] = chay_tep(E2E[1])
        if os.environ.get("QV_IM") != "1":
            print("\nBỘ THỬ                     | exit |  ca | FAIL/ERROR | bỏ qua")
            for _, ten, _, _, _, _ in BO_DO:
                r = cls.kq[ten]
                print("%-27s| %4d | %3d | %10d | %6d"
                      % (ten, r["ma"], r["ca"], len(r["fail"]), r["skip"]))
            e = cls.kq[E2E[1]]
            print("%-27s| %4d | %3d | %10s | %6s  (E2E: %d/%d phép đo)"
                  % (E2E[1], e["ma"], _dem_e2e(e["ra"])[0], "—", "—",
                     *_dem_e2e(e["ra"])))

    # ── 1. SỐ CA ĐÚNG + EXIT ĐÚNG, mỗi nhóm một ca ─────────────────────────────────────
    def _kiem_mot_bo(self, ten, ma, ca, fail_cho_phep=()):
        r = self.kq[ten]
        self.assertEqual(r["ma"], ma, "%s: exit %d, mong đợi %d.\n%s"
                         % (ten, r["ma"], ma, r["ra"][-3000:]))
        self.assertEqual(r["ca"], ca, "%s: đo được %d ca, mong đợi %d"
                         % (ten, r["ca"], ca))
        la = [f for f in r["fail"] if not any(f.startswith(p) for p in fail_cho_phep)]
        self.assertEqual(la, [], "%s: FAIL lạ %r\n%s" % (ten, la, r["ra"][-3000:]))
        if fail_cho_phep:
            self.assertTrue(r["fail"], "%s: mất ca R7 — cổng đã bị nới để xanh" % ten)
        self.assertEqual(r["skip"], 0, "%s: có %d ca bị BỎ QUA" % (ten, r["skip"]))

    def test_01_r1_g01_g02_exit_0_du_21_ca(self):
        self._kiem_mot_bo("thu_g01_g02.py", 0, 21)

    def test_02_r1_g19_route_exit_0_du_50_ca(self):
        self._kiem_mot_bo("thu_g19_route.py", 0, 50)

    def test_03_r1_bootstrap_tu_kiem_exit_0_du_11_ca(self):
        self._kiem_mot_bo("thu_r1_bootstrap.py", 0, 11)

    def test_04_r1_e2e_41_41_phep_do(self):
        r = self.kq[E2E[1]]
        self.assertEqual(r["ma"], 0, "E2E phải exit 0:\n%s" % r["ra"][-3000:])
        dat, tong = _dem_e2e(r["ra"])
        self.assertEqual((dat, tong), (41, 41), "E2E: %d/%d phép đo" % (dat, tong))

    def test_05_r2_g16_exit_0_du_61_ca(self):
        self._kiem_mot_bo("thu_qa_g16.py", 0, 61)

    def test_06_r2_jt_exit_0_du_22_ca(self):
        self._kiem_mot_bo("thu_qa_jt.py", 0, 22)

    def test_07_r2_soat_exit_0_du_30_ca(self):
        self._kiem_mot_bo("thu_qa_soat.py", 0, 30)

    def test_08_r2_tich_hop_12_ca_chi_con_R7(self):
        self._kiem_mot_bo("thu_tich_hop.py", 1, 12, fail_cho_phep=("test_09_",))

    def test_09_r2_harness_exit_0_du_12_ca(self):
        self._kiem_mot_bo("thu_r2_hopdong.py", 0, 12)

    def test_10_r27_g21_bimat_exit_0_du_33_ca(self):
        self._kiem_mot_bo("thu_g21_bimat.py", 0, 33)

    def test_11_r27_g22_chotcay_exit_0_du_11_ca(self):
        self._kiem_mot_bo("thu_g22_chotcay.py", 0, 11)

    # ── 2. ĐỐI CHỨNG ÂM: TIÊM LẠI LỖI, PHÉP THỬ PHẢI ĐỎ ───────────────────────────────
    def test_12_r27_fixture_song_song_va_doi_chung_am(self):
        """Bộ tự kiểm R27 chạy HAI lượt G21 song song + đối chứng âm D2/D4 trong 1 lượt."""
        self._kiem_mot_bo("thu_r27_fixture.py", 0, 4)

    def test_13_r1_bo_khai_kho_thi_g01_PHAI_do(self):
        """Bộ thử tự khai kho là NGUYÊN NHÂN xanh của G01: gỡ lời khai ⇒ phải đỏ lại.

        Dùng `sitecustomize` trên `PYTHONPATH` để thay `cau_hinh.khai_kho_kiem_thu` bằng
        hàm rỗng — KHÔNG sửa tệp nào. Đây đúng là đối chứng âm mà báo cáo R1 mô tả.
        """
        hook = tempfile.mkdtemp(prefix="qv-hook-")
        try:
            with open(os.path.join(hook, "sitecustomize.py"), "w", encoding="utf-8") as f:
                f.write(
                    "import os, sys\n"
                    "sys.path.insert(0, %r)\n"
                    "try:\n"
                    "    import cau_hinh\n"
                    "    cau_hinh.khai_kho_kiem_thu = lambda *a, **k: None\n"
                    "except Exception:\n"
                    "    pass\n"
                    "os.environ.pop('VIP_KHO_DANG_CHAY', None)\n"
                    % GOC_APP)
            with tempfile.TemporaryDirectory(prefix="qv-neg-") as data:
                e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
                e.pop("VIP_KHO_DANG_CHAY", None)
                e.update(VIP_HUB_DATA=data, VIP_HUB_BIND="127.0.0.1",
                         VIP_JT_MOI_TRUONG="mock", PYTHONDONTWRITEBYTECODE="1",
                         PYTHONPATH=hook)
                p = subprocess.run([sys.executable, os.path.join(GOC_THU, "thu_g01_g02.py")],
                                   cwd=GOC_REPO, capture_output=True, text=True, env=e,
                                   timeout=600)
            ra = (p.stdout or "") + (p.stderr or "")
            self.assertNotEqual(p.returncode, 0,
                                "gỡ lời khai kho mà thu_g01_g02 VẪN XANH ⇒ phép thử đọc sai chỗ")
            self.assertIn("CHƯA KHAI kho đang chạy", ra,
                          "lượt đỏ không nêu đúng nguyên nhân fail-closed")
        finally:
            shutil.rmtree(hook, ignore_errors=True)

    # ── 3. ĐỐI CHỨNG ĐƯỜNG + HỢP ĐỒNG, đo trên SẢN PHẨM ───────────────────────────────
    def test_14_hop_dong_truy_van_400_va_duong_hop_le_200(self):
        """`tenant_id` trong query bị 400; `gioi_han` hợp lệ chạy được — đo thẳng `truy_van`."""
        with tempfile.TemporaryDirectory(prefix="qv-contract-") as data:
            e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
            e.update(VIP_HUB_DATA=data, VIP_KHO_DANG_CHAY="sqlite",
                     PYTHONDONTWRITEBYTECODE="1")
            for lenh in (["app/migrate.py"], ["app/khoi_tao.py"]):
                subprocess.run([sys.executable] + lenh, cwd=GOC_REPO, env=e,
                               capture_output=True, text=True, timeout=600)
            ma = (
                "import sys; sys.path.insert(0, %r)\n"
                "import truy_van\n"
                "kq = truy_van.tim_don(1, {'gioi_han': '5'})\n"
                "print('DUONG_OK', sorted(kq) == sorted(['con_nua','dong','gioi_han','lech',"
                "'loc_bo_qua','sap_xep','tong','tong_chinh_xac','tong_it_nhat','trang']))\n"
                "try:\n"
                "    truy_van.tim_don(1, {'tenant_id': '2'})\n"
                "    print('CHAN_OK', False)\n"
                "except truy_van.LoiTruyVan as ex:\n"
                "    print('CHAN_OK', getattr(ex, 'ma', None) == 400)\n"
                % GOC_APP)
            p = subprocess.run([sys.executable, "-c", ma], cwd=GOC_REPO, env=e,
                               capture_output=True, text=True, timeout=600)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertIn("DUONG_OK True", p.stdout,
                          "đường truy vấn HỢP LỆ không chạy được:\n" + p.stdout + p.stderr)
            self.assertIn("CHAN_OK True", p.stdout,
                          "tenant_id trong query KHÔNG bị 400:\n" + p.stdout + p.stderr)

    def test_15_bo_do_R2_bat_IO_that_va_tha_urllib_parse(self):
        """Bộ dò mới phải BẮT I/O thật và THA `urllib.parse` — hai chiều, không chỉ một."""
        def nap(ten):
            spec = importlib.util.spec_from_file_location(
                "qv_" + ten, os.path.join(GOC_THU, ten + ".py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        jt = nap("thu_qa_jt")
        for mau in ("import http.client\n", "from urllib import request\n",
                    "import socket\n", "import urllib.request\n"):
            self.assertTrue(jt._vi_pham_io_mang(mau), "bộ dò JT bỏ sót I/O thật %r" % mau)
        self.assertEqual(jt._vi_pham_io_mang("from urllib.parse import urlsplit\n"), [],
                         "urllib.parse bị coi là I/O")
        th = nap("thu_tich_hop")
        self.assertTrue(th._vi_pham_nhap_mang("import http.client\n"))
        self.assertEqual(th._vi_pham_nhap_mang("from urllib.parse import urlsplit\n"), [])
        g16 = nap("thu_qa_g16")
        for mau in ('password = "Xk9#mQ2$vL7@nR4"\n',
                    'CFG = {"privateKey": "Xk9#mQ2$vL7@nR4"}\n',
                    'MA_LOI = {"CREDENTIAL_KHONG_HOP_LE": "Xk9#mQ2$vL7@nR4"}\n'):
            self.assertTrue(g16.quet_hardcode(mau), "bộ dò G16 bỏ sót secret thật %r" % mau)
        self.assertEqual(
            g16.quet_hardcode(
                'MA_LOI = {"CREDENTIAL_KHONG_HOP_LE": "Username rỗng/sai kiểu; Password dài"}\n'),
            [], "câu thông báo lỗi vẫn bị coi là secret")

    # ── 4. LUẬT §6: KHÔNG XOÁ TEST / BỎ ASSERTION / THÊM SKIP ─────────────────────────
    def test_16_khong_giam_so_ca_khong_them_skip_moi(self):
        thieu, giam, skip_moi, rong_moi = [], [], [], []
        for duong in TEP_SUA:
            cu = _doc_git(duong)
            if cu is None:
                thieu.append(duong)
                continue
            with open(os.path.join(GOC_REPO, duong), encoding="utf-8") as f:
                nay = f.read()
            a, b = _dem_ma(cu), _dem_ma(nay)
            if b["test"] < a["test"]:
                giam.append("%s: test %d → %d" % (duong, a["test"], b["test"]))
            if b["skip"] > a["skip"]:
                skip_moi.append("%s: skip %d → %d" % (duong, a["skip"], b["skip"]))
            if b["rong"] > a["rong"]:
                rong_moi.append("%s: dấu hiệu rỗng %d → %d"
                                % (duong, a["rong"], b["rong"]))
        self.assertEqual(thieu, [], "không đọc được bản nền %s của: %r" % (BASE_GIT, thieu))
        self.assertEqual(giam, [], "SỐ CA GIẢM: %r" % giam)
        self.assertEqual(skip_moi, [], "THÊM SKIP: %r" % skip_moi)
        self.assertEqual(rong_moi, [], "THÊM DẤU HIỆU RỖNG: %r" % rong_moi)

    def test_17_r27_khong_con_quet_TMPDIR_dung_chung(self):
        """Z4 phải canh tài nguyên của CHÍNH lượt; quét TMPDIR là nguyên nhân đỏ giả cũ."""
        with open(os.path.join(GOC_THU, "thu_g21_bimat.py"), encoding="utf-8") as f:
            nguon = f.read()
        self.assertNotIn("os.listdir(tempfile.gettempdir())", nguon,
                         "Z4 vẫn quét TMPDIR dùng chung")
        self.assertIn("_TAM_DA_TAO", nguon)
        # Mọi thư mục tạm của bộ đo phải nằm TRONG gốc của lượt.
        self.assertEqual(nguon.count("dir=_TAM_GOC"), 1,
                         "có đường tạo thư mục tạm NGOÀI gốc của lượt")
        with open(os.path.join(GOC_THU, "thu_g22_chotcay.py"), encoding="utf-8") as f:
            nguon22 = f.read()
        self.assertIn('"git", "clone"', nguon22, "D2 phải chạy trên BẢN SAO")
        self.assertIn("nguon_cu_hong", nguon22, "D4 phải chọn bản LỊCH SỬ bị bắt")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    kq = runner.run(unittest.defaultTestLoader.loadTestsFromTestCase(QV_KiemChung))
    sys.exit(0 if kq.wasSuccessful() else 1)
