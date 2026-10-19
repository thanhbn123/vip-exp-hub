#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R1 — BỘ TỰ KIỂM CƠ CHẾ BOOTSTRAP KHAI KHO + CÁCH LY.

VÌ SAO CÓ TỆP NÀY
-----------------
QA `docs/QA_NGUYENNHAN.md` §4-§5 đo được ba bộ đỏ vì CÙNG một gốc: `migrate.py` gọi trong
TIẾN TRÌNH CON nhưng bộ thử không khai "kho đang chạy". Cổng fail-closed của G22 TỪ CHỐI
(`CHƯA KHAI kho đang chạy`) — đó là hành vi ĐÚNG của sản phẩm, không phải lỗi sản phẩm.

Bản vá R1 KHÔNG nới cổng: mỗi bộ thử tự khai bằng `cau_hinh.khai_kho_kiem_thu()` sau khi
`VIP_HUB_DATA` đã trỏ một thư mục TẠM, và lời khai đi vào `os.environ` để tiến trình con
(`env=dict(os.environ)`) kế thừa. Tệp này tự kiểm CHÍNH CƠ CHẾ ấy, trên fixture nhỏ — không
chạy lại toàn bộ ba bộ (bằng chứng thật nằm trong `docs/R1_BOOTSTRAP.md`).

LUẬT CỦA BỘ TỰ KIỂM
-------------------
* ĐỐI CHỨNG ÂM BẮT BUỘC: tiêm lại đúng lỗi "bỏ khai" (import hook vô hiệu hoá
  `khai_kho_kiem_thu`, KHÔNG sửa tệp bộ thử) ⇒ fixture PHẢI ĐỎ. Không có vế này thì mọi
  dòng XANH dưới đây không chứng minh gì.
* ĐỐI CHỨNG ĐƯỜNG: fixture sạch (khai đúng) PHẢI ĐẠT, và truy vấn/đường hợp lệ vẫn chạy.
* Ba entrypoint thật (G01/G02, G19 route, E2E shell) phải khai Ở BOOTSTRAP: kiểm bằng AST/văn
  bản trên CHÍNH tệp đang giao, không bằng niềm tin.
* Sản phẩm KHÔNG được mọc mặc định SQLite: `app/cau_hinh.py` vẫn đọc từ biến môi trường và
  `app/migrate.py` vẫn còn nguyên thông điệp TỪ CHỐI khi chưa khai.

CHẠY
----
    python3 app/thu/thu_r1_bootstrap.py -v
"""

import ast
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

APP = Path(__file__).resolve().parents[1]
GOC = APP.parent
MIGRATE = APP / "migrate.py"


def _moi_truong(**them):
    """Môi trường con SẠCH: không thừa hưởng lời khai kho từ shell của người chạy."""
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    e.pop("VIP_KHO_DANG_CHAY", None)
    e.pop("VIP_HUB_DATA", None)
    e.update(them)
    return e


def _chay_con(ma, env, cwd=None, giay=180):
    e = dict(env)
    e["PYTHONPATH"] = str(APP) + (os.pathsep + e["PYTHONPATH"]
                                  if e.get("PYTHONPATH") else "")
    return subprocess.run([sys.executable, "-c", textwrap.dedent(ma)],
                          capture_output=True, text=True, env=e,
                          cwd=str(cwd or GOC), timeout=giay)


def _dong_lenh_khai(nguon):
    """Dòng của lời gọi `X.khai_kho_kiem_thu()` ở CẤP MÔ-ĐUN; `None` nếu không có.

    Vì sao phải là cấp mô-đun: bootstrap phải chạy TRƯỚC mọi phép đo, không phải trong một ca
    (đặt trong ca thì các ca khác vẫn chạy khi chưa khai). Đếm cả lời gọi lồng trong `try` cấp
    mô-đun là chấp nhận được — điều bị cấm là nằm trong một hàm test.
    """
    cay = ast.parse(nguon)
    for nut in cay.body:
        for con in ast.walk(nut) if isinstance(nut, (ast.If, ast.Try)) else [nut]:
            if (isinstance(con, ast.Expr) and isinstance(con.value, ast.Call)
                    and isinstance(con.value.func, ast.Attribute)
                    and con.value.func.attr == "khai_kho_kiem_thu"):
                return con.lineno
        if (isinstance(nut, ast.Expr) and isinstance(nut.value, ast.Call)
                and isinstance(nut.value.func, ast.Attribute)
                and nut.value.func.attr == "khai_kho_kiem_thu"):
            return nut.value.lineno
    return None


class A_ChotCoLap(unittest.TestCase):
    """`khai_kho_kiem_thu()` chỉ nhận nền TẠM — ba chốt, ba đối chứng âm."""

    def test_a1_tu_choi_khi_chua_dat_thu_muc_du_lieu(self):
        kq = _chay_con("import cau_hinh; print(cau_hinh.khai_kho_kiem_thu())", _moi_truong())
        self.assertNotEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("chưa đặt VIP_HUB_DATA", kq.stdout + kq.stderr)

    def test_a2_tu_choi_du_lieu_trong_cay_repo(self):
        kq = _chay_con("import cau_hinh; print(cau_hinh.khai_kho_kiem_thu())",
                       _moi_truong(VIP_HUB_DATA=str(APP / "du-lieu")))
        self.assertNotEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("CÂY REPO", kq.stdout + kq.stderr)

    def test_a3_tu_choi_volume_trien_khai(self):
        kq = _chay_con("import cau_hinh; print(cau_hinh.khai_kho_kiem_thu())",
                       _moi_truong(VIP_HUB_DATA="/du-lieu/moi-truong-thu"))
        self.assertNotEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("volume triển khai", kq.stdout + kq.stderr)

    def test_a4_nhan_thu_muc_tam_va_dat_env_cho_tien_trinh_con(self):
        with tempfile.TemporaryDirectory(prefix="r1-bootstrap-") as tam:
            kq = _chay_con(
                "import os, cau_hinh\n"
                "print('KHO=' + cau_hinh.khai_kho_kiem_thu())\n"
                "print('ENV=' + os.environ['VIP_KHO_DANG_CHAY'])\n",
                _moi_truong(VIP_HUB_DATA=tam))
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("KHO=sqlite", kq.stdout)
        self.assertIn("ENV=sqlite", kq.stdout)


class B_ConKeThuaLoiKhai(unittest.TestCase):
    """Lõi R1: `migrate.py` trong TIẾN TRÌNH CON — thiếu khai thì đỏ, khai rồi thì đạt."""

    def test_b1_migrate_con_thieu_khai_thi_tu_choi(self):
        with tempfile.TemporaryDirectory(prefix="r1-bootstrap-") as tam:
            kq = subprocess.run([sys.executable, str(MIGRATE)], env=_moi_truong(VIP_HUB_DATA=tam),
                                capture_output=True, text=True, cwd=str(GOC), timeout=120)
        self.assertNotEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("TỪ CHỐI: CHƯA KHAI kho đang chạy", kq.stdout + kq.stderr,
                      "cổng fail-closed của sản phẩm đã bị nới!")

    def test_b2_khai_o_cha_thi_con_ke_thua_qua_os_environ(self):
        with tempfile.TemporaryDirectory(prefix="r1-bootstrap-") as tam:
            kq = _chay_con(
                "import os, subprocess, sys\n"
                "import cau_hinh\n"
                "cau_hinh.khai_kho_kiem_thu()\n"
                "r = subprocess.run([sys.executable, %r], env=dict(os.environ),\n"
                "                   capture_output=True, text=True, cwd=%r)\n"
                "print('CON_RC=%%d' %% r.returncode)\n"
                "sys.exit(r.returncode)\n" % (str(MIGRATE), str(GOC)),
                _moi_truong(VIP_HUB_DATA=tam))
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("CON_RC=0", kq.stdout)

    def test_b3_doi_chung_am_import_hook_bo_khai_thi_phai_do(self):
        """TIÊM LẠI LỖI, KHÔNG SỬA TỆP: hook thay `khai_kho_kiem_thu` bằng hàm rỗng.

        Fixture là một "bộ thử tí hon" đúng khuôn R1: đặt nền tạm → tự khai → chạy
        `migrate.py` trong con. Chạy sạch PHẢI đạt; chạy qua hook (bỏ khai) PHẢI đỏ đúng
        thông điệp `CHƯA KHAI`. Đây là chứng minh lời khai là NGUYÊN NHÂN, không phải trùng hợp.
        """
        fixture = (
            "import os, subprocess, sys\n"
            "import cau_hinh\n"
            "cau_hinh.khai_kho_kiem_thu()\n"
            "r = subprocess.run([sys.executable, %r], env=dict(os.environ),\n"
            "                   capture_output=True, text=True, cwd=%r)\n"
            "assert r.returncode == 0, r.stdout + r.stderr\n"
            "print('FIXTURE_OK')\n" % (str(MIGRATE), str(GOC)))
        hook = textwrap.dedent("""
            import importlib.abc, importlib.machinery, os, sys
            os.environ.pop('VIP_KHO_DANG_CHAY', None)

            class _Chan(importlib.abc.MetaPathFinder):
                def find_spec(self, ten, path=None, target=None):
                    if ten != 'cau_hinh':
                        return None
                    sys.meta_path.remove(self)
                    try:
                        spec = importlib.machinery.PathFinder.find_spec(ten, path)
                    finally:
                        sys.meta_path.insert(0, self)
                    if spec is None:
                        return None
                    goc = spec.loader.exec_module

                    def exec_module(module):
                        goc(module)
                        # ĐÚNG lỗi cần tiêm: lời khai không có tác dụng.
                        module.khai_kho_kiem_thu = lambda *a, **k: None
                    spec.loader.exec_module = exec_module
                    return spec

            sys.meta_path.insert(0, _Chan())
        """)
        with tempfile.TemporaryDirectory(prefix="r1-bootstrap-") as tam_sach, \
                tempfile.TemporaryDirectory(prefix="r1-bootstrap-") as tam_hong, \
                tempfile.TemporaryDirectory(prefix="r1-hook-") as hook_dir:
            Path(hook_dir, "sitecustomize.py").write_text(hook, encoding="utf-8")
            # Hai nền TÁCH BIỆT: nếu dùng lại một nền, lượt thứ hai thấy CSDL đã ở schema
            # hiện tại nên `migrate` không cần `sao_luu()` và cổng khai kho KHÔNG được chạm —
            # đối chứng âm sẽ xanh giả (đã dính đúng bẫy này ở lần chạy đầu).
            sach = _chay_con(fixture, _moi_truong(VIP_HUB_DATA=tam_sach))
            hong = _chay_con(fixture, _moi_truong(VIP_HUB_DATA=tam_hong,
                                                 PYTHONPATH=hook_dir))
        self.assertEqual(sach.returncode, 0, sach.stdout + sach.stderr)
        self.assertIn("FIXTURE_OK", sach.stdout)
        self.assertNotEqual(hong.returncode, 0,
                            "bỏ khai mà fixture vẫn đạt ⇒ lời khai không phải nguyên nhân")
        self.assertIn("CHƯA KHAI kho đang chạy", hong.stdout + hong.stderr)


class C_BaEntrypointKhaiOCapBootstrap(unittest.TestCase):
    """Kiểm TĨNH trên CHÍNH ba tệp đang giao: khai ở cấp mô-đun, trước phép đo đầu tiên."""

    def test_c1_g01_g02_tu_khai_truoc_khi_do(self):
        nguon = (APP / "thu" / "thu_g01_g02.py").read_text(encoding="utf-8")
        dong = _dong_lenh_khai(nguon)
        self.assertIsNotNone(dong, "G01/G02 mất lời khai kho ở bootstrap")
        dong_lop = nguon[:nguon.index("class ThuG01G02")].count("\n") + 1
        self.assertLess(dong, dong_lop, "lời khai phải đứng TRƯỚC lớp đo")
        # Khai qua giao diện có chốt cô lập, không phải gán biến môi trường trần.
        self.assertNotIn('os.environ["VIP_KHO_DANG_CHAY"]', nguon)

    def test_c2_g19_route_tu_khai_truoc_khi_do(self):
        nguon = (APP / "thu" / "thu_g19_route.py").read_text(encoding="utf-8")
        dong = _dong_lenh_khai(nguon)
        self.assertIsNotNone(dong, "G19 route mất lời khai kho ở bootstrap")
        dong_ca = nguon[:nguon.index("CAC_CA = [")].count("\n") + 1
        self.assertLess(dong, dong_ca, "lời khai phải đứng TRƯỚC danh sách ca đo")
        self.assertNotIn('os.environ["VIP_KHO_DANG_CHAY"]', nguon)

    def test_c3_e2e_shell_tu_khai_tren_nen_mktemp(self):
        duong = APP / "thu" / "chay_e2e.sh"
        dong = duong.read_text(encoding="utf-8").splitlines()
        dong_nen = [i for i, t in enumerate(dong)
                    if re.match(r"\s*NEN=\$\(mktemp -d", t)]
        self.assertEqual(1, len(dong_nen), "E2E phải dựng nền bằng ĐÚNG một mktemp -d")
        khai = [i for i, t in enumerate(dong)
                if not t.lstrip().startswith("#") and "VIP_KHO_DANG_CHAY=sqlite" in t]
        self.assertEqual(1, len(khai), "E2E phải khai kho ĐÚNG một lần, không trong chú thích")
        self.assertGreater(khai[0], dong_nen[0],
                           "phải XÁC MINH nền tạm (mktemp) TRƯỚC rồi mới khai")
        self.assertIn('VIP_HUB_DATA="$NEN"', dong[khai[0]],
                      "lời khai phải đi cùng nền dữ liệu nó khai — không phải export rời")
        self.assertTrue(any("python3 app/migrate.py" in t for t in dong),
                        "E2E phải còn bước migrate trong tiến trình con")

    def test_c4_san_pham_khong_moc_mac_dinh_sqlite(self):
        """Bản vá R1 KHÔNG được chuyển thành mặc định trong cấu hình/sản phẩm."""
        cau_hinh = (APP / "cau_hinh.py").read_text(encoding="utf-8")
        dong_khai = [t for t in cau_hinh.splitlines()
                     if re.match(r"KHO_DANG_CHAY\s*=", t)]
        self.assertEqual(1, len(dong_khai), "phải có ĐÚNG một chỗ khai KHO_DANG_CHAY")
        self.assertIn("os.environ.get(BIEN_KHAI_KHO)", dong_khai[0],
                      "KHO_DANG_CHAY phải đọc từ KHAI BÁO, không được gán cứng")
        self.assertNotIn('"sqlite"', dong_khai[0], "cấu hình mọc mặc định SQLite!")
        migrate = MIGRATE.read_text(encoding="utf-8")
        self.assertIn("TỪ CHỐI: CHƯA KHAI kho đang chạy", migrate,
                      "thông điệp fail-closed của migrate đã bị gỡ!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
