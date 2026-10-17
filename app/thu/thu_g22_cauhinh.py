#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 / AG-01 — KHAI "KHO ĐANG CHẠY": HAI CHIỀU, VÀ ĐỐI CHỨNG ĐƯỜNG.

Chạy:  python3 app/thu/thu_g22_cauhinh.py
       `app/thu/chay_tat_ca.sh` tự dò `app/thu/thu_*.py` nên tệp này vào lượt hồi quy chung.

====== BA CÂU HỎI TỆP NÀY TRẢ LỜI, BẰNG MÃ THOÁT THẬT ======
(1) KHAI `sqlite` trong một môi trường kiểm thử CÔ LẬP ⇒ `migrate.py` CHẠY ĐƯỢC (rc 0, có bản
    sao lưu + dấu kiểm `.sha256`)? Và các cách khai hợp lệ (`sqlite3`, `  SQLite  `, biến môi
    trường, `cau_hinh.khai_kho_kiem_thu()`) có cho CÙNG một kết quả?
(2) KHÔNG KHAI ⇒ hệ vẫn TỪ CHỐI đúng như thiết kế fail-closed — và KHÔNG để lại `hub.db` giả
    trên đĩa? (Một `hub.db` do chính lượt bị từ chối tạo ra chính là "hub.db CŨ còn sót" của
    P-G15-02 `do2b`: lượt sau không phân biệt được nó với dữ liệu đang phục vụ.)
(3) Phép đo ở (2) có BẮT ĐƯỢC lỗi không? ĐỐI CHỨNG ĐƯỜNG: dựng lại CHÍNH SÁCH CŨ ("chưa khai ⇒
    coi là SQLite") trên một BẢN CHÉP của `app/`, chạy ĐÚNG lệnh đó ⇒ rc 0. Nếu phép đo không
    phân biệt được hai chính sách thì nó không chứng minh được gì.

====== VÌ SAO MỌI PHÉP ĐO Ở TIẾN TRÌNH CON ======
`app/cau_hinh.py` đọc `VIP_HUB_DATA`/`VIP_KHO_DANG_CHAY` MỘT LẦN lúc nạp mô-đun, nên trong cùng
một tiến trình, lượt đo thứ hai vẫn dùng cấu hình của lượt đầu — và mọi phép so sau đó chỉ đang
so một CSDL với chính nó. Mỗi ca dưới đây chạy trong tiến trình RIÊNG với môi trường RIÊNG.

====== PHẠM VI ======
Mọi thư mục dữ liệu là `tempfile.mkdtemp()`. KHÔNG chạm `app/du-lieu` (CSDL nghiệp vụ), KHÔNG
chạm `~/Projects/vip-express-hub`, KHÔNG mở kết nối mạng, KHÔNG PostgreSQL (D-8 giữ nguyên).
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(GOC, "app")
PY = sys.executable or "python3"
BIEN = "VIP_KHO_DANG_CHAY"

# "KHÔNG ĐẶT" khác "đặt chuỗi rỗng": cái sau là một khai báo RỖNG và phải bị coi là CHƯA KHAI.
KHONG_DAT = object()


def _moi_truong(data_dir, khai_kho=KHONG_DAT, **them):
    """Môi trường cho tiến trình con. `data_dir=None` ⇒ KHÔNG đặt `VIP_HUB_DATA`.

    Luôn `pop` `VIP_KHO_DANG_CHAY` thừa hưởng từ shell: một biến lọt vào từ ngoài sẽ khiến nhánh
    "chưa khai" KHÔNG BAO GIỜ chạy, mà phép đo vẫn in ra một con số trông như thật.
    """
    e = dict(os.environ)
    for k in (BIEN, "VIP_HUB_RESET_TOKEN"):
        e.pop(k, None)
    if data_dir is not None:
        e["VIP_HUB_DATA"] = data_dir
    else:
        e.pop("VIP_HUB_DATA", None)
    if khai_kho is not KHONG_DAT:
        e[BIEN] = khai_kho
    e["G22_GOC"] = GOC
    e.update(them)
    return e


def _chay(lenh, env, timeout=300):
    """Chạy lệnh THẬT. Trả `(rc, out, err)` — `rc` đọc NGAY sau lệnh, không qua ống."""
    p = subprocess.run(lenh, capture_output=True, text=True, cwd=GOC, env=env, timeout=timeout)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def _db(d):
    return os.path.join(d, "hub.db")


def _ban_sao(d):
    return sorted(glob.glob(os.path.join(d, "sao-luu", "hub-truoc-migrate-*.db")))


def _migrate():
    return os.path.join(APP, "migrate.py")


class A_ChuaKhaiPhaiTuChoi(unittest.TestCase):
    """CHIỀU ÂM — mặc định an toàn: CHƯA KHAI ⇒ TỪ CHỐI, và không để lại tệp giả.

    Đi kèm ĐỐI CHỨNG DƯƠNG ngay trong lớp: CÙNG lệnh, CÙNG nền trống, khác ĐÚNG một biến khai.
    """

    @classmethod
    def setUpClass(cls):
        cls.nen = tempfile.mkdtemp(prefix="g22-cauhinh-a-")
        cls.chua = os.path.join(cls.nen, "chua-khai")
        cls.khai = os.path.join(cls.nen, "da-khai")
        os.makedirs(cls.chua)
        os.makedirs(cls.khai)
        cls.rc_chua, cls.out_chua, cls.err_chua = _chay(
            [PY, _migrate()], _moi_truong(cls.chua))
        cls.rc_khai, cls.out_khai, cls.err_khai = _chay(
            [PY, _migrate()], _moi_truong(cls.khai, "sqlite"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.nen, ignore_errors=True)

    def test_a1_chua_khai_tu_choi_va_noi_ro_thieu_gi(self):
        """rc != 0 · TỪ CHỐI có chủ đích (KHÔNG phải traceback) · nêu biến + hằng cấu hình."""
        self.assertNotEqual(self.rc_chua, 0,
                            "CHƯA KHAI kho đang chạy mà `migrate.py` vẫn thoát 0 — đó là "
                            "fail-OPEN của P-G15-02 `do2b`")
        self.assertIn("TỪ CHỐI", self.err_chua, "không có dòng TỪ CHỐI: %r" % self.err_chua[-500:])
        self.assertNotIn("Traceback", self.err_chua,
                         "TỪ CHỐI phải là quyết định có chủ đích, không phải một vụ nổ: %r"
                         % self.err_chua[-500:])
        self.assertIn("CHƯA KHAI kho đang chạy", self.err_chua,
                      "thông báo không gọi đúng tên việc còn thiếu")
        self.assertIn(BIEN, self.err_chua, "thông báo không nêu TÊN biến phải đặt")
        self.assertIn("KHO_DANG_CHAY", self.err_chua,
                      "thông báo không nêu chỗ khai chính thức trong `app/cau_hinh.py`")

    def test_a2_tu_choi_khong_de_lai_hub_db_gia(self):
        """Lượt bị từ chối KHÔNG được tạo `hub.db`/`sao-luu`.

        Vì sao: `csdl.mo()` tạo `hub.db` nếu thiếu. Bản trước kiểm kho SAU `csdl.mo()`, nên một
        lượt CHƯA KHAI để lại `hub.db` 200.704 byte / 51 bảng — đúng thứ mà `do2b` gọi là "hub.db
        CŨ còn sót", và lượt sau không phân biệt được nó với dữ liệu đang phục vụ.
        """
        self.assertNotEqual(self.rc_chua, 0)
        self.assertFalse(os.path.exists(_db(self.chua)),
                         "một lượt TỪ CHỐI đã để lại `hub.db` — manh mối GIẢ cho lượt sau")
        self.assertFalse(os.path.exists(os.path.join(self.chua, "sao-luu")),
                         "một lượt TỪ CHỐI đã tạo thư mục `sao-luu`")

    def test_a3_doi_chung_duong_cung_lenh_chi_khac_mot_bien(self):
        """ĐỐI CHỨNG DƯƠNG của `a1`/`a2`: khai `sqlite` ⇒ rc 0, CÓ `hub.db`, CÓ bản sao + dấu kiểm.

        Thiếu vế này thì "từ chối" có thể chỉ là hệ quả của một `migrate.py` hỏng với MỌI đầu vào
        — hai kết luận khác hẳn nhau, và chỉ vế này phân biệt được.
        """
        self.assertEqual(self.rc_khai, 0, "ĐÃ KHAI `sqlite` mà vẫn hỏng: %s" % self.err_khai[-800:])
        self.assertIn("Đã backup", self.out_khai, "không thấy dòng backup trong stdout")
        self.assertTrue(os.path.exists(_db(self.khai)), "khai `sqlite` mà không có `hub.db`")
        ban = _ban_sao(self.khai)
        self.assertEqual(len(ban), 1, "phải có ĐÚNG một bản sao lưu cho một lượt nâng cấp: %r" % ban)
        self.assertTrue(os.path.exists(ban[0] + ".sha256"),
                        "bản sao lưu thiếu dấu kiểm `.sha256`")
        self.assertNotEqual(self.rc_chua, self.rc_khai,
                            "hai chế độ khai cho CÙNG một mã thoát ⇒ phép đo không phân biệt được")


class B_CacCachKhaiHopLe(unittest.TestCase):
    """CHIỀU DƯƠNG — biến thể hợp lệ chạy được; giá trị lạ và PostgreSQL bị TỪ CHỐI."""

    def _mot_luot(self, khai_kho, ten):
        d = tempfile.mkdtemp(prefix="g22-cauhinh-b-%s-" % ten)
        self.addCleanup(shutil.rmtree, d, True)
        return d, _chay([PY, _migrate()], _moi_truong(d, khai_kho))

    def test_b1_bien_the_hop_le_deu_chay_duoc(self):
        for gia_tri in ("sqlite3", "  SQLite  ", "SQLITE"):
            with self.subTest(khai=gia_tri):
                d, (rc, out, err) = self._mot_luot(gia_tri, "ok")
                self.assertEqual(rc, 0, "khai %r bị từ chối oan: %s" % (gia_tri, err[-600:]))
                self.assertEqual(len(_ban_sao(d)), 1, "khai %r mà không có bản sao lưu" % gia_tri)

    def test_b2_khai_postgresql_thi_tu_choi_va_chi_pg_dump(self):
        d, (rc, out, err) = self._mot_luot("postgresql", "pg")
        self.assertNotEqual(rc, 0, "khai `postgresql` mà `migrate.py` vẫn chạy SQLite")
        self.assertIn("pg_dump", err, "thông báo không chỉ đường sao lưu PostgreSQL")
        self.assertFalse(os.path.exists(_db(d)),
                         "khai PostgreSQL mà vẫn TẠO `hub.db` — đó là chuyển ngầm sang SQLite")

    def test_b3_khai_sai_chinh_ta_khong_duoc_coi_la_chua_khai(self):
        d, (rc, out, err) = self._mot_luot("my-sql", "sai")
        self.assertNotEqual(rc, 0, "khai sai chính tả mà vẫn thoát 0")
        self.assertIn("my-sql", err, "thông báo không nêu NGUYÊN VĂN giá trị khai sai")
        self.assertIn("không nhận ra", err, "thông báo không nói ra việc không nhận ra giá trị")
        self.assertFalse(os.path.exists(_db(d)), "khai sai chính tả mà vẫn tạo `hub.db`")

    def test_b4_khai_rong_la_chua_khai(self):
        """`VIP_KHO_DANG_CHAY=` (rỗng) KHÔNG phải một khai báo — vẫn phải TỪ CHỐI."""
        d, (rc, out, err) = self._mot_luot("", "rong")
        self.assertNotEqual(rc, 0, "khai RỖNG mà vẫn thoát 0")
        self.assertIn("CHƯA KHAI kho đang chạy", err, "khai rỗng không được coi là chưa khai")
        self.assertFalse(os.path.exists(_db(d)))


class C_HamKhaiKiemThu(unittest.TestCase):
    """`cau_hinh.khai_kho_kiem_thu()` — một dòng cho bộ thử, kèm HAI CHỐT CÔ LẬP.

    Mọi ca chạy ở tiến trình con: hàm này ĐẶT biến môi trường, nên gọi trong tiến trình này sẽ
    làm rò trạng thái sang các ca khác.
    """

    MA_THU = r'''
import os, subprocess, sys
sys.path.insert(0, os.path.join(os.environ["G22_GOC"], "app"))
import cau_hinh
_tham_so = os.environ.get("G22_KHAI")
try:
    gia_tri = cau_hinh.khai_kho_kiem_thu(*([_tham_so] if _tham_so is not None else []))
except SystemExit as e:
    print("TU_CHOI=" + str(e).splitlines()[0])
    print("BIEN=" + os.environ.get("VIP_KHO_DANG_CHAY", "KHONG"))
    sys.exit(1)          # mã thoát RIÊNG cho nhánh từ chối — không lẫn với một vụ nổ
else:
    print("TU_CHOI=KHONG")
    print("GIA_TRI=" + gia_tri)
    import migrate
    print("KHO=" + repr(migrate.kho_dang_chay()))
    p = subprocess.run(
        [sys.executable, os.path.join(os.environ["G22_GOC"], "app", "migrate.py")],
        capture_output=True, text=True)
    print("CON_RC=" + str(p.returncode))
    print("BIEN=" + os.environ.get("VIP_KHO_DANG_CHAY", "KHONG"))
'''

    def _chay_ma(self, data_dir, khai_kho=KHONG_DAT, **them):
        return _chay([PY, "-c", self.MA_THU], _moi_truong(data_dir, khai_kho, **them))

    def test_c1_khai_mot_dong_roi_migrate_chay_duoc(self):
        """ĐỐI CHỨNG DƯƠNG: mép cô lập + một dòng ⇒ tiến trình con của `migrate.py` rc 0."""
        d = tempfile.mkdtemp(prefix="g22-cauhinh-c1-")
        self.addCleanup(shutil.rmtree, d, True)
        rc, out, err = self._chay_ma(d)
        self.assertEqual(rc, 0, "script khai hỏng: %s" % (err or out)[-600:])
        self.assertIn("TU_CHOI=KHONG", out)
        self.assertIn("GIA_TRI=sqlite", out)
        self.assertIn("KHO=('sqlite'", out, "migrate không đọc được khai báo: %r" % out)
        self.assertIn("CON_RC=0", out, "khai rồi mà tiến trình con vẫn hỏng: %r" % out)
        self.assertIn("BIEN=sqlite", out, "hàm không đặt biến môi trường cho tiến trình con")

    def test_c2_chua_dat_vip_hub_data_thi_tu_choi(self):
        """CHỐT CÔ LẬP (1): không đặt `VIP_HUB_DATA` ⇒ thư mục mặc định của CSDL nghiệp vụ ⇒ TỪ CHỐI."""
        rc, out, err = self._chay_ma(None)
        self.assertNotEqual(rc, 0, "vẫn cho khai khi chưa đặt thư mục dữ liệu")
        self.assertIn("chưa đặt VIP_HUB_DATA", out)
        self.assertIn("BIEN=KHONG", out, "từ chối mà vẫn ĐẶT biến — có tác dụng phụ ngoài ý muốn")

    def test_c3_vip_hub_data_trong_cay_repo_thi_tu_choi(self):
        """CHỐT CÔ LẬP (2a): trỏ vào cây repo (kể cả `app/du-lieu`) ⇒ TỪ CHỐI."""
        rc, out, err = self._chay_ma(os.path.join(APP, "du-lieu"))
        self.assertNotEqual(rc, 0)
        self.assertIn("CÂY REPO", out)
        self.assertIn("BIEN=KHONG", out)

    def test_c4_vip_hub_data_la_volume_du_lieu_that_thi_tu_choi(self):
        """CHỐT CÔ LẬP (2b): `/du-lieu` (volume container) ⇒ TỪ CHỐI, không chạm đĩa."""
        rc, out, err = self._chay_ma("/du-lieu")
        self.assertNotEqual(rc, 0)
        self.assertIn("volume triển khai", out)
        self.assertIn("BIEN=KHONG", out)

    def test_c5_ham_nay_khong_mo_nhanh_postgresql(self):
        """Hàm chỉ dành cho nền kiểm thử SQLite; `postgresql` bị từ chối ngay (đối chứng: c1)."""
        d = tempfile.mkdtemp(prefix="g22-cauhinh-c5-")
        self.addCleanup(shutil.rmtree, d, True)
        rc, out, err = self._chay_ma(d, G22_KHAI="postgresql")
        self.assertNotEqual(rc, 0)
        self.assertIn("CHỈ dành cho môi trường kiểm thử dùng SQLite", out)
        self.assertIn("BIEN=KHONG", out)


class D_DoiChungDuong_PhepDoBatDuocLoi(unittest.TestCase):
    """CHỨNG MINH PHÉP ĐO CÓ RĂNG — không chỉ "hệ đang từ chối" mà "phép đo BẮT ĐƯỢC nới chốt".

    Dựng một BẢN CHÉP của `app/`, chạy ĐÚNG lệnh của `A` trên bản chép **chưa vá** (rc != 0) và
    trên bản chép **đã tiêm chính sách cũ** ("chưa khai ⇒ coi là SQLite", đúng `D5` của
    `trien_khai/g20-saoluu/ban_va.py`) — lượt sau PHẢI rc 0 và tạo `hub.db`. Cùng một lệnh, cùng
    một môi trường, khác ĐÚNG hai dòng mã.
    """

    CAP_CU = ("    if kho is None:\n        _tu_choi_chua_khai(nguon)\n",
              "    if kho is None:\n        kho = KHO_SQLITE  # D5: chính sách cũ, đã bị bỏ\n")

    def setUp(self):
        self.nen = tempfile.mkdtemp(prefix="g22-cauhinh-d-")
        self.addCleanup(shutil.rmtree, self.nen, True)
        self.app = os.path.join(self.nen, "app")
        shutil.copytree(APP, self.app,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "thu"))
        self.mg = os.path.join(self.app, "migrate.py")

    def test_d1_tiem_chinh_sach_cu_thi_phep_do_bat_duoc(self):
        chua = os.path.join(self.nen, "chua-tiem")
        os.makedirs(chua)
        rc_chua, out_chua, err_chua = _chay([PY, self.mg], _moi_truong(chua))
        self.assertNotEqual(rc_chua, 0, "bản chép CHƯA TIÊM phải TỪ CHỐI")
        self.assertIn("CHƯA KHAI kho đang chạy", err_chua)

        with open(self.mg, encoding="utf-8") as f:
            nguon = f.read()
        cu, moi = self.CAP_CU
        self.assertEqual(nguon.count(cu), 1,
                         "không tiêm được chính sách cũ: đoạn gốc không khớp ĐÚNG một lần")
        with open(self.mg, "w", encoding="utf-8") as f:
            f.write(nguon.replace(cu, moi, 1))

        da = os.path.join(self.nen, "da-tiem")
        os.makedirs(da)
        rc_da, out_da, err_da = _chay([PY, self.mg], _moi_truong(da))
        self.assertEqual(rc_da, 0,
                         "ĐÃ tiêm 'chưa khai ⇒ coi là SQLite' mà vẫn rc != 0 ⇒ phép đo của A "
                         "không chứng minh được gì: %s" % err_da[-600:])
        self.assertTrue(os.path.exists(_db(da)),
                        "chính sách cũ phải tạo `hub.db` — đây là đường fail-open phải bắt được")
        self.assertEqual(len(_ban_sao(da)), 1, "chính sách cũ phải đi tiếp tới bước sao lưu")


class E_HopDongCauHinh(unittest.TestCase):
    """HỢP ĐỒNG giữa cấu hình và mã đọc cấu hình, và hai chốt chống trôi tài liệu."""

    def test_e1_bang_bien_the_cua_cau_hinh_va_migrate_khop_nhau(self):
        sys.path.insert(0, APP)
        try:
            import cau_hinh
            import migrate
        finally:
            sys.path.pop(0)
        for gia_tri, mong in (("sqlite", "sqlite"), ("sqlite3", "sqlite"),
                              ("  SQLite  ", "sqlite"), ("pg", "postgresql"),
                              ("postgres", "postgresql"), ("postgresql", "postgresql"),
                              ("psql", "postgresql")):
            with self.subTest(khai=gia_tri):
                self.assertEqual(cau_hinh.chuan_hoa_kho(gia_tri), mong)
                self.assertEqual(migrate._chuan_hoa_kho(gia_tri), mong)
        self.assertIsNone(cau_hinh.chuan_hoa_kho("my-sql"))
        with self.assertRaises(SystemExit):
            migrate._chuan_hoa_kho("my-sql")

    def test_e2_mac_dinh_van_la_chua_khai(self):
        """MẶC ĐỊNH BẢO MẬT KHÔNG ĐỔI: tiến trình sạch ⇒ `KHO_DANG_CHAY is None` và TỪ CHỐI."""
        ma = ("import os,sys; sys.path.insert(0, os.path.join(os.environ['G22_GOC'],'app'));"
              "import cau_hinh, migrate;"
              "print('MAC_DINH=' + repr(cau_hinh.KHO_DANG_CHAY));"
              "print('DOC=' + repr(migrate.kho_dang_chay()))")
        rc, out, err = _chay([PY, "-c", ma], _moi_truong(None))
        self.assertEqual(rc, 0, err[-500:])
        self.assertIn("MAC_DINH=None", out, "mặc định đã bị đổi thành một giá trị khai sẵn")
        self.assertIn("DOC=(None, None)", out, "mặc định không còn là CHƯA KHAI")

    def test_e3_bo_chay_e2e_cua_b2_b3_khai_ro(self):
        """B2/B3 chạy qua `thu_giao_dien/chay.sh`; script đó PHẢI khai kho (nếu không nền không dựng)."""
        p = os.path.join(GOC, "thu_giao_dien", "chay.sh")
        with open(p, encoding="utf-8") as f:
            than = f.read()
        self.assertIn("export VIP_KHO_DANG_CHAY=sqlite", than,
                      "`thu_giao_dien/chay.sh` không còn khai kho ⇒ `migrate.py` sẽ TỪ CHỐI và "
                      "B2/B3 không có nền")

    def test_e4_env_example_khong_bat_khai_mac_dinh(self):
        """`.env.example` phải để DÒNG KHAI ở dạng COMMENT — bỏ comment là KHAI, không phải mẫu."""
        p = os.path.join(GOC, ".env.example")
        with open(p, encoding="utf-8") as f:
            dong = f.read().splitlines()
        hoat_dong = [d.strip() for d in dong
                     if d.strip().startswith("VIP_KHO_DANG_CHAY")]
        self.assertEqual(hoat_dong, [],
                         "`.env.example` đang BẬT khai kho mặc định: %r — mẫu không được tự khai"
                         % hoat_dong)
        self.assertIn("# VIP_KHO_DANG_CHAY=sqlite", dong,
                      "`.env.example` thiếu dòng mẫu COMMENT cho kho đang chạy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
