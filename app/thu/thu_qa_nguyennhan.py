#!/usr/bin/env python3
"""Phân loại nguyên nhân bằng đối chứng nhân quả; chỉ tiêm lỗi vào bản sao tạm.

Chạy: python3 app/thu/thu_qa_nguyennhan.py -v
Không dùng bảng kết quả viết cứng để tự xác nhận. Không sửa bộ thử/sản phẩm gốc.
"""
import dataclasses
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(os.environ.get('QANN_REPO', Path(__file__).resolve().parents[2]))


@dataclasses.dataclass(frozen=True)
class Do:
    ma: int
    ra: str
    ca: int = 0


def phan_loai(do, *, khai_lai=None, nghiem_thu=None, doi_chung=None,
              ghim=None, phu_thuoc=None, dem=None):
    """Trả nhiều nhãn nếu có nhiều nguyên nhân. Không phán R5 chỉ vì exit != 0.

    khai_lai/nghiem_thu: cùng mã nguồn, chỉ thay đúng thiết lập tương ứng.
    ghim: (kỳ vọng của phép đo, sự thật đo độc lập).
    phu_thuoc: (tài nguyên thực sự thiếu, kết quả sau cung cấp tài nguyên).
    doi_chung: cùng harness, sản phẩm sạch phải xanh, bản tiêm phải đỏ.
    dem: (số ca từ sự kiện chạy độc lập, số bộ đếm đọc được).
    Người gọi chịu trách nhiệm thực hiện các can thiệp có kiểm soát này.
    """
    nhom = set()
    if dem is not None and dem[0] > 0 and dem[0] != dem[1]:
        nhom.add('R6')
    if do.ma == 0:
        return nhom or ({'XANH'} if do.ca > 0 else {'R7'})
    if (khai_lai is not None and 'CHƯA KHAI kho đang chạy' in do.ra
            and 'CHƯA KHAI kho đang chạy' not in khai_lai.ra):
        nhom.add('R1')  # Nhãn vẫn có giá trị nếu lỗi khác còn lại sau khai kho.
    if nghiem_thu is not None and nghiem_thu.ma == 0 and nghiem_thu.ca > 0:
        nhom.add('R2')
    if ghim is not None and ghim[0] != ghim[1]:
        nhom.add('R3')
    if (phu_thuoc is not None and phu_thuoc[0]
            and phu_thuoc[1].ma == 0 and phu_thuoc[1].ca > 0):
        nhom.add('R4')
    if doi_chung is not None and doi_chung.ma == 0 and doi_chung.ca > 0:
        nhom.add('R5')
    return nhom or {'R7'}


def chay(ma, env=None, app=None):
    with tempfile.TemporaryDirectory(prefix='qann-data-') as data:
        e = dict(os.environ, VIP_HUB_DATA=data, PYTHONDONTWRITEBYTECODE='1')
        e.pop('VIP_KHO_DANG_CHAY', None)
        e.update(env or {})
        e['PYTHONPATH'] = str(app or REPO / 'app')
        p = subprocess.run([sys.executable, '-c', ma], capture_output=True,
                           text=True, env=e, timeout=60)
        return Do(p.returncode, p.stdout + p.stderr, int(p.returncode == 0))


def dem_that(ma, ra):
    """Gọi CHÍNH hàm bộ đếm sản phẩm, không sao chép regex của nó."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', encoding='utf-8') as f:
        f.write(ra)
        f.flush()
        p = subprocess.run(['sh', str(REPO / 'app/thu/chay_tat_ca.sh'),
                            '--tinh-ca', str(ma), f.name], capture_output=True,
                           text=True, timeout=15, check=True)
    return dict(line.split('=', 1) for line in p.stdout.splitlines())


def bam_san_pham():
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (REPO / 'app').glob('*.py')}


class TuKiemNguyenNhan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.truoc = bam_san_pham()

    @classmethod
    def tearDownClass(cls):
        if cls.truoc != bam_san_pham():
            raise AssertionError('Mã sản phẩm gốc đã đổi trong lượt tự kiểm')

    def test_r1_migrate_that_thieu_khai_va_khai_lai(self):
        ma = 'import csdl,migrate; csdl.mo(); migrate.sao_luu(); print("OK")'
        do = chay(ma)
        lai = chay(ma, {'VIP_KHO_DANG_CHAY': 'sqlite'})
        self.assertNotEqual(do.ma, 0, do.ra)
        self.assertIn('CHƯA KHAI kho đang chạy', do.ra)
        self.assertEqual(lai.ma, 0, lai.ra)
        self.assertEqual(phan_loai(do, khai_lai=lai), {'R1'})
        self.assertEqual(phan_loai(lai), {'XANH'})

    def test_r1_khong_gan_nhan_chi_vi_trich_dan_thong_diep(self):
        do = Do(1, 'CHƯA KHAI kho đang chạy')
        self.assertEqual(phan_loai(do), {'R7'})
        self.assertEqual(phan_loai(do, khai_lai=do), {'R7'})

    def test_r2_tiem_che_do_cu_voi_doi_chung_nghiem_thu(self):
        ma = 'import os; assert os.environ.get("QANN_MODE") == "gop", "nền cũ"'
        do, lai = chay(ma), chay(ma, {'QANN_MODE': 'gop'})
        self.assertNotEqual(do.ma, 0)
        self.assertEqual(lai.ma, 0, lai.ra)
        self.assertEqual(phan_loai(do, nghiem_thu=lai), {'R2'})
        self.assertEqual(phan_loai(do, nghiem_thu=Do(1, 'vẫn đỏ')), {'R7'})

    def test_r3_tiem_schema_ghim_cu_do_su_that_doc_lap(self):
        ma = 'import csdl; assert csdl.PHIEN_BAN_SCHEMA == 9'
        do = chay(ma)
        that = chay('import csdl; print(csdl.PHIEN_BAN_SCHEMA)')
        self.assertEqual(that.ma, 0, that.ra)
        schema = int(that.ra.strip())
        self.assertNotEqual(do.ma, 0)
        self.assertEqual(phan_loai(do, ghim=(9, schema)), {'R3'})
        self.assertEqual(phan_loai(do, ghim=(schema, schema)), {'R7'})

    def test_r4_tiem_thieu_tep_phu_thuoc_va_cung_cap_lai(self):
        with tempfile.TemporaryDirectory(prefix='qann-dep-') as t:
            dep = Path(t) / 'dependency'
            ma = 'from pathlib import Path; Path(%r).read_bytes()' % str(dep)
            do = chay(ma)
            missing = not dep.exists()
            dep.write_bytes(b'fixture')
            lai = chay(ma)
        self.assertNotEqual(do.ma, 0)
        self.assertEqual(lai.ma, 0, lai.ra)
        self.assertEqual(phan_loai(do, phu_thuoc=(missing, lai)), {'R4'})
        self.assertEqual(phan_loai(do, phu_thuoc=(False, lai)), {'R7'})

    def test_r5_tiem_loi_san_pham_that_tren_ban_sao(self):
        # Dùng hàm chữ ký thật; chỉ thay mã ở bản sao, không thay harness.
        with tempfile.TemporaryDirectory(prefix='qann-product-') as t:
            app = Path(t) / 'app'
            shutil.copytree(REPO / 'app', app,
                            ignore=shutil.ignore_patterns('du-lieu', '__pycache__', 'thu'))
            ma = ('import adapter_jt,base64,hashlib; '
                  'assert adapter_jt.ky_digest("abc","k") == '
                  'base64.b64encode(hashlib.md5(b"abck").digest()).decode()')
            sach = chay(ma, app=app)
            self.assertEqual(sach.ma, 0, sach.ra)
            with (app / 'adapter_jt.py').open('a') as f:
                f.write('\n# TIÊM TRÊN BẢN SAO DUY NHẤT\ndef ky_digest(*a, **k):\n    return "SAI"\n')
            hong = chay(ma, app=app)
            self.assertNotEqual(hong.ma, 0)
            self.assertEqual(phan_loai(hong, doi_chung=sach), {'R5'})
            self.assertEqual(phan_loai(hong, doi_chung=hong), {'R7'})

    def test_r6_tiem_khuon_khong_duoc_dem_va_doi_chung_khuon_dung(self):
        # Hai ca unittest THẬT; tiêm lỗi vào kênh báo cáo bằng cách đổi một dòng summary.
        ma = ('import unittest\nclass T(unittest.TestCase):\n'
              ' def test_a(self): pass\n def test_b(self): pass\n'
              'r=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(T))\n'
              'print("EVENTS="+str(r.testsRun))\n')
        do = chay(ma)
        n = int(re.search(r'EVENTS=(\d+)', do.ra).group(1))
        self.assertEqual(n, 2)
        dung = dem_that(do.ma, do.ra)
        self.assertEqual(int(dung['N']), n)
        tiem = re.sub(r'Ran 2 tests', 'Executed 2 checks', do.ra)
        sai = dem_that(do.ma, tiem)
        self.assertEqual(int(sai['N']), 0)
        self.assertEqual(phan_loai(do, dem=(n, int(sai['N']))), {'R6'})
        self.assertEqual(phan_loai(do, dem=(n, int(dung['N']))), {'XANH'})

    def test_r6_khuon_gioihan_va_e2e_hien_tai_khong_bi_goi_sai(self):
        for text, n in [('TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)', 32),
                        ('số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 46/5/0/14/0', 65)]:
            with self.subTest(text=text):
                self.assertEqual(int(dem_that(1, text)['N']), n)

    def test_r6_tach_ca_chua_chay_khoi_ca_co_ket_qua(self):
        ra = 'số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 2/25/0/53/0'
        n = int(dem_that(1, ra)['N'])
        self.assertEqual(n, 80)  # Mẫu số kế hoạch của bộ đếm hiện tại.
        self.assertEqual(phan_loai(Do(1, ra, 27), dem=(2 + 25, n)), {'R6'})
        self.assertEqual(phan_loai(Do(1, ra, 27), dem=(27, 27)), {'R7'})

    def test_r7_loi_la_va_khong_chay_ca_nao(self):
        self.assertEqual(phan_loai(chay('raise RuntimeError("không rõ")')), {'R7'})
        self.assertEqual(phan_loai(Do(0, 'OK', 0)), {'R7'})

    def test_nhieu_nguyen_nhan_khong_bi_che_boi_r1(self):
        self.assertEqual(phan_loai(Do(1, 'CHƯA KHAI kho đang chạy'),
                         khai_lai=Do(1, 'schema khác'), ghim=(9, 10)), {'R1', 'R3'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
