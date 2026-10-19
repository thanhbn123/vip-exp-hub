#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R3 — GHIM SỰ THẬT MÔI TRƯỜNG: KIỂM TRA BẤT BIẾN THAY CHO SỐ CŨ.

BỐI CẢNH
========
Bốn bộ đo cũ đang ĐỎ vì chúng GHIM SỐ CỦA MỘT LƯỢT ĐO, không phải vì sản phẩm hỏng:

  · `thu_g20_dahang.py`  ghim `{"CHUNG": 30, "DAC_THU_JT": 7}`, bốn số dòng
                          `(108, 115, 116, 831)` và bốn tọa độ nhánh `[285, 311, 343, 742]`;
  · `thu_g20_saoluu.py`  ghim phiên bản schema sau khôi phục là `9`;
  · `thu_qa_g18.py`      gọi `thu_frontend/thu_http.py`, nơi ghim đúng `10` trang demo;
  · `thu_g22_gioihan.py` đo C5 như thể C5 phải ĐỎ khi tiêm lỗi vào MỘT trong hai ứng viên —
                          trong khi hợp đồng C5 là OR ("ít nhất một ứng viên chạy thật").

Bộ này KHÔNG chạy lại bốn bộ kia. Nó là **bộ tự kiểm của chính bản vá R3**:
  1. Xác nhận các ghim số cũ đã BIẾN MẤT khỏi mã nguồn của bốn bộ.
  2. Đo lại các BẤT BIẾN mới bằng nguồn độc lập (AST), không dùng lại kết quả của bộ kia.
  3. ĐỐI CHỨNG ÂM: đưa từng ghim số cũ trở lại dưới dạng một assertion và đòi nó PHẢI ĐỎ
     trên số đo hiện tại. Nếu một ghim cũ bỗng khớp lại, ca này ĐỎ — vì khi đó "tiêm lại ghim
     cũ" không còn chứng minh được gì.
  4. ĐỐI CHỨNG DƯƠNG: chạy ca trang demo THẬT (`thu_frontend/thu_http.py`) và đòi ĐẠT.

BẤT BIẾN THAY CHO SỐ GHIM
=========================
  · G20 đa hãng — phân hoạch hàm: `DAC_THU_JT ⇔ hang_dac_thu != []`, `CHUNG ⇔ hang_dac_thu == []`;
    nhãn hãng trong thông điệp: hai phép quét AST độc lập phải ra CÙNG tập dòng; nhánh ràng buộc
    hãng: dòng báo cáo phải nằm TRONG hàm nó khai và hằng đặc thù phải được dùng trong thân hàm.
  · G20 sao lưu — phiên bản schema sau khôi phục phải BẰNG phiên bản schema của NGUỒN, đọc tại chỗ.
  · QA G18 — danh sách trang đọc từ đĩa, khác rỗng, và MỌI trang tải được + dùng CSS/JS chung.
  · G22 C5 — hợp đồng OR: `chay = min(Σ ứng viên chạy thật & thoát 0, 1)`; chiều ĐỎ của C5 chỉ
    đo được khi MỌI ứng viên đều hỏng, nên fixture phải CÔ LẬP còn một ứng viên trước khi tiêm.

CHẠY
====
    python3 app/thu/thu_r3_ghim.py

Không sửa mã sản phẩm, không gọi mạng, không dùng credentials, không đụng CSDL nghiệp vụ.
"""
import ast
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(GOC, "app")
GOC_THU = os.path.join(GOC_APP, "thu")
for _d in (GOC_APP, GOC_THU,
           os.path.join(GOC, "trien_khai", "g20-dahang"),
           os.path.join(GOC, "trien_khai", "g20-saoluu")):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import kich_ban                                                          # noqa: E402
import phan_tich_gan_chat as PT                                         # noqa: E402

DUONG_HTTP = os.path.join(GOC_APP, "http_jt.py")
DUONG_ADAPTER = os.path.join(GOC_APP, "adapter_jt.py")
TEP_G20_DAHANG = os.path.join(GOC_THU, "thu_g20_dahang.py")
TEP_G20_SAOLUU = os.path.join(GOC_THU, "thu_g20_saoluu.py")
TEP_G22 = os.path.join(GOC_THU, "thu_g22_gioihan.py")
TEP_QA_G20 = os.path.join(GOC_THU, "thu_qa_g20.py")
TEP_THU_HTTP = os.path.join(GOC, "thu_frontend", "thu_http.py")
THU_MUC_TRANG = os.path.join(GOC, "pages")
CA_TRANG_DEMO = "ThuFrontendHTTP.test_04_moi_trang_demo_g00_khong_bi_pha"


def doc(duong):
    with open(duong, encoding="utf-8") as f:
        return f.read()


def dong(duong):
    return doc(duong).splitlines()


def vung_ham(duong):
    """Tên hàm → (dòng đầu, dòng cuối) của chính tệp đang đo."""
    cay = ast.parse(doc(duong), filename=duong)
    return {n.name: (n.lineno, n.end_lineno)
            for n in ast.walk(cay)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def vung_chuoi(duong):
    """Literal chuỗi: (dòng đầu, dòng cuối, giá trị)."""
    cay = ast.parse(doc(duong), filename=duong)
    return [(n.lineno, n.end_lineno, n.value)
            for n in ast.walk(cay)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def nhan_hieu_doc_lap(duong):
    """Quét ĐỘC LẬP nhãn hãng trong literal CHẠY ĐƯỢC (bỏ docstring)."""
    cay = ast.parse(doc(duong), filename=duong)
    docstring = set()
    for x in ast.walk(cay):
        if isinstance(x, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            d = ast.get_docstring(x, clean=False)
            if d is not None and x.body and isinstance(x.body[0], ast.Expr):
                docstring.add(id(x.body[0].value))
    dau = tuple(getattr(PT, "_DAU_HIEU_TEN_HANG", ("jtexpress", "j&t"))) + ("bizcontent",)
    return sorted({n.lineno for n in ast.walk(cay)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and id(n) not in docstring
                   and any(d in n.value.lower() for d in dau)})


def moi_truong_sach(**them):
    """Môi trường con: gỡ `GIT_CONFIG_*` (N-G18-00) và ép dữ liệu vào thư mục tạm."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    env.update({"VIP_HUB_BIND": "127.0.0.1", "VIP_JT_MOI_TRUONG": "mock",
                "PYTHONDONTWRITEBYTECODE": "1"})
    env.update(them)
    return env


class R3_BatBien(unittest.TestCase):
    """Mỗi ca dưới đây đo một BẤT BIẾN, không đo một con số của lượt trước."""

    @classmethod
    def setUpClass(cls):
        cls.kq = PT.phan_tich(DUONG_HTTP, DUONG_ADAPTER)
        cls.nguon_http = dong(DUONG_HTTP)
        cls.html = sorted(x for x in os.listdir(THU_MUC_TRANG) if x.endswith(".html"))
        cls.kq_saoluu = kich_ban.ca_vong_tron()

    # ── 1. Ghim số cũ đã biến mất ──────────────────────────────────────────────────────────
    def test_01_g20_dahang_khong_con_ghim_so_cu(self):
        than = doc(TEP_G20_DAHANG)
        for cu in ('"CHUNG": 30', '"DAC_THU_JT": 7',
                   "[285, 311, 343, 742]", "(108, 115, 116, 831)"):
            with self.subTest(ghim=cu):
                self.assertNotIn(cu, than, f"ghim số cũ còn trong {TEP_G20_DAHANG}: {cu!r}")
        for moi in ("_nhan_hieu_doc_lap", "_vung_ham", "_vung_chuoi", "hang_dac_thu"):
            with self.subTest(bat_bien=moi):
                self.assertIn(moi, than, f"bất biến thay thế chưa có: {moi}")

    # ── 2. G20 đa hãng: phân hoạch hàm theo BẰNG CHỨNG ────────────────────────────────────
    def test_02_g20_dahang_phan_hoach_theo_bang_chung(self):
        ham = self.kq["ham"]
        dem = {}
        for v in ham.values():
            dem[v["vai_tro"]] = dem.get(v["vai_tro"], 0) + 1
        self.assertEqual(set(dem), {"CHUNG", "DAC_THU_JT"}, f"nhãn lạ: {dem}")
        self.assertEqual(sum(dem.values()), len(ham), f"phân hoạch thiếu hàm: {dem}")
        for ten, v in ham.items():
            with self.subTest(ham=ten):
                if v["vai_tro"] == "DAC_THU_JT":
                    self.assertTrue(v["hang_dac_thu"], f"{ten} DAC_THU mà không có bằng chứng")
                    self.assertLessEqual(set(v["hang_dac_thu"]), set(self.kq["hang"]),
                                         f"{ten} dẫn hằng không tồn tại")
                else:
                    self.assertEqual(v["hang_dac_thu"], [],
                                     f"{ten} CHUNG mà chạm hằng đặc thù")
        self.assertEqual(
            {t for t, v in ham.items() if v["vai_tro"] == "DAC_THU_JT"},
            {t for t, v in ham.items() if v["hang_dac_thu"]},
            "nhãn và bằng chứng lệch nhau")

    # ── 3. G20 đa hãng: hai phép quét nhãn hãng phải khớp ─────────────────────────────────
    def test_03_g20_dahang_nhan_hieu_doi_chieu_hai_nguon(self):
        ds = self.kq["nhan_hieu_ten_hang"]
        self.assertTrue(ds, "bộ dò không thấy nhãn hãng nào")
        cac_dong = [d["dong"] for d in ds]
        self.assertEqual(len(cac_dong), len(set(cac_dong)), f"dòng trùng: {cac_dong}")
        self.assertEqual(sorted(set(cac_dong)), nhan_hieu_doc_lap(DUONG_HTTP),
                         "bộ dò sản phẩm và phép quét AST độc lập lệch nhau")
        vung = vung_chuoi(DUONG_HTTP)
        for d in ds:
            with self.subTest(dong=d["dong"]):
                self.assertTrue([v for v in vung
                                 if v[0] == d["dong"] and d["trich"] in v[2]],
                                f"dòng {d['dong']} không có literal chứa {d['trich']!r}")

    # ── 4. G20 đa hãng: nhánh ràng buộc hãng nằm TRONG hàm nó khai ───────────────────────
    def test_04_g20_dahang_nhanh_nam_trong_ham(self):
        nhanh = self.kq["nhanh_ma_gan_hang"]
        self.assertTrue(nhanh, "bộ dò không thấy nhánh ràng buộc hãng")
        self.assertEqual(len({d["dong"] for d in nhanh}), len(nhanh),
                         f"dòng trùng: {[d['dong'] for d in nhanh]}")
        vung = vung_ham(DUONG_HTTP)
        nguon = self.nguon_http
        for d in nhanh:
            with self.subTest(ham=d["ham"], dong=d["dong"]):
                self.assertIn(d["ham"], vung, f"hàm không tồn tại: {d['ham']}")
                dau, cuoi = vung[d["ham"]]
                self.assertGreaterEqual(d["dong"], dau)
                self.assertLessEqual(d["dong"], cuoi)
                than = "\n".join(nguon[dau - 1:cuoi])
                for ten_bang in d["hang_dac_thu"]:
                    self.assertIn(ten_bang, than,
                                  f"{d['ham']} khai {ten_bang} mà thân hàm không dùng")
                self.assertGreaterEqual(d["so_lenh_trong_nhanh"], 1)
        self.assertEqual(
            {d["ham"] for d in nhanh},
            {"_gia_tri_trong_json", "_gia_tri_bi_mat_trong_json",
             "_gia_tri_bi_mat_tu_phan_hoi", "tach_url"},
            "tập hàm bị ràng buộc hãng đã đổi — xem lại ranh giới")

    # ── 5. G20 sao lưu: schema khôi phục = schema NGUỒN, đo tại chỗ ───────────────────────
    def test_05_saoluu_schema_theo_nguon(self):
        than = doc(TEP_G20_SAOLUU)
        self.assertNotIn('assertEqual(self.kq["phien_ban_sau"], 9', than,
                         "ghim schema 9 còn trong bộ sao lưu")
        self.assertIn('self.kq["_truoc"].get("phien_ban")', than,
                      "bộ sao lưu chưa đọc schema NGUỒN tại chỗ")
        kq = self.kq_saoluu
        self.assertIsNotNone(kq["_truoc"].get("phien_ban"),
                             "không đọc được schema nguồn")
        self.assertEqual(kq["phien_ban_sau"], kq["_truoc"]["phien_ban"],
                         "schema khôi phục KHÁC schema nguồn: %r != %r"
                         % (kq["phien_ban_sau"], kq["_truoc"]["phien_ban"]))
        self.assertEqual(kq["lech_sau_khoi_phuc"], [],
                         "khôi phục ra dữ liệu KHÁC nguồn")

    # ── 6. QA G18: đếm trang TẠI CHỖ, không ghim 10/11 ────────────────────────────────────
    def test_06_trang_dem_tai_cho(self):
        than = doc(TEP_THU_HTTP)
        self.assertNotIn("assertEqual(len(ten_trang), 10", than,
                         "ghim 10 trang còn trong bộ frontend")
        self.assertIn('os.listdir(os.path.join(GOC_DU_AN, "pages"))', than,
                      "danh sách trang không còn đọc từ đĩa")
        self.assertIn("assertGreaterEqual(len(ten_trang), 1", than,
                      "thiếu chốt chống phép đo rỗng")
        self.assertGreaterEqual(len(self.html), 1, "thư mục pages/ rỗng")
        for ten in self.html:
            with self.subTest(trang=ten):
                noi = doc(os.path.join(THU_MUC_TRANG, ten))
                self.assertIn("assets/css/style.css", noi)
                self.assertIn("assets/js/app.js", noi)

    # ── 7. C5: hợp đồng OR/AND được ghi rõ, fixture cô lập trước khi tiêm ────────────────
    def test_07_c5_hop_dong_or_va_co_lap_fixture(self):
        c5 = doc(TEP_QA_G20)
        # OR: chỉ cần MỘT ứng viên chạy thật + thoát 0.
        self.assertIn("chay = min(sum(1 for _, ma, n, bq, nc in chi_tiet", c5,
                      "công thức C5 không còn là OR trên danh sách ứng viên")
        self.assertIn("if ma == 0 and n > 0 and nc > 0", c5,
                      "C5 không còn đòi ca CHẠY THẬT (đã trừ skipped)")
        g22 = doc(TEP_G22)
        self.assertIn("_cach_ly_ung_vien_c5", g22,
                      "fixture G22 chưa có cơ chế cô lập ứng viên C5")
        self.assertIn("assert con_lai == [os.path.basename(BO_UY_QUYEN)]", g22,
                      "fixture G22 không chốt danh sách sau cô lập")
        ung_vien = sorted(t for t in os.listdir(GOC_THU)
                          if t.startswith("thu_qa_g19") and t.endswith(".py"))
        self.assertGreaterEqual(len(ung_vien), 1,
                                "không còn ứng viên C5 nào — phép đo vô nghĩa")
        # Nếu danh sách có từ 2 ứng viên, B2 PHẢI đo `1/2`; nếu chỉ 1, B2 phải đổi thành `1/1`.
        # Ghi ra để người sau đối chiếu với output thật thay vì đoán.
        print("\n  [C5] ứng viên hiện tại (%d): %s" % (len(ung_vien), ung_vien))

    # ── 8. ĐỐI CHỨNG ÂM: ghim số cũ PHẢI ĐỎ trên số đo hiện tại ──────────────────────────
    def test_08_doi_chung_am_ghim_cu_phai_do(self):
        """Mỗi ghim cũ được đưa trở lại dưới dạng assertion; nó PHẢI ném AssertionError.

        Nếu một ghim cũ bỗng khớp lại (ví dụ schema hạ về 9), ca này ĐỎ: khi đó phép "tiêm lại
        ghim cũ" không còn là đối chứng âm, và phải chọn phép đối chứng khác — không được giữ
        một đối chứng rỗng.
        """
        ham = self.kq["ham"]
        dem = {}
        for v in ham.values():
            dem[v["vai_tro"]] = dem.get(v["vai_tro"], 0) + 1
        with self.assertRaises(AssertionError):
            self.assertEqual(dem, {"CHUNG": 30, "DAC_THU_JT": 7})
        cac_dong = [d["dong"] for d in self.kq["nhan_hieu_ten_hang"]]
        with self.assertRaises(AssertionError):
            self.assertEqual(cac_dong, [108, 115, 116, 831])
        cac_nhanh = [d["dong"] for d in self.kq["nhanh_ma_gan_hang"]]
        with self.assertRaises(AssertionError):
            self.assertEqual(cac_nhanh, [285, 311, 343, 742])
        with self.assertRaises(AssertionError):
            self.assertEqual(self.kq_saoluu["phien_ban_sau"], 9)
        with self.assertRaises(AssertionError):
            self.assertEqual(len(self.html), 10)

    # ── 9. ĐỐI CHỨNG DƯƠNG: ca trang demo THẬT phải ĐẠT ─────────────────────────────────
    def test_09_doi_chung_duong_ca_trang_demo_dat(self):
        tam = tempfile.mkdtemp(prefix="veh-r3-ghim-")
        try:
            r = subprocess.run(
                [sys.executable, TEP_THU_HTTP, CA_TRANG_DEMO],
                cwd=GOC, capture_output=True, text=True, timeout=300,
                env=moi_truong_sach(VIP_HUB_DATA=tam))
            self.assertEqual(r.returncode, 0,
                             "ca trang demo ĐỎ trên đường hợp lệ:\n%s\n%s"
                             % (r.stdout[-2000:], r.stderr[-2000:]))
            self.assertIn("Ran 1 test", r.stderr + r.stdout,
                          "ca trang demo không chạy đúng 1 ca — phép đo rỗng")
        finally:
            shutil.rmtree(tam, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
