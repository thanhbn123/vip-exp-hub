#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20/AG-03 — BỘ THỬ cho HARNESS HỢP ĐỒNG LỚP HTTP.

====== BỘ NÀY ĐO CÁI GÌ ======
Nó KHÔNG đo lớp HTTP của dự án — việc đó là của năm harness con. Nó đo **chính harness G20**,
tức là đo thứ mà mọi lời khai "hợp đồng ĐẠT" sẽ dựa vào:

  A. Hợp đồng là DỮ LIỆU máy đọc được, và dữ liệu ấy TỰ NHẤT QUÁN (đủ khoá, không trùng mã,
     chốt nào cũng có định nghĩa, không dùng biến thay thế lạ).
  B. Bảy chốt an toàn phân biệt được cấu hình AN TOÀN với cấu hình NGUY HIỂM — mỗi ca hỏng
     phải bị bắt bởi ĐÚNG chốt đang muốn đo, không phải "bị bắt vì lý do gì cũng được".
  C. Bộ phán ĐỎ ĐƯỢC: tiêm lỗi vào bản sao hợp đồng thì nó phải báo hỏng, và ở ĐỐI CHỨNG
     DƯƠNG thì nó phải xanh.
  D. Nó BẮC CẦU được ba kiểu báo cáo khác nhau của ba harness con (G16/G17 có `blocked`,
     G18 KHÔNG có; cả ba có `dem`).
  E. Nền và PID: hai lượt không dùng chung nền, và tiến trình con bị tắt theo ĐÚNG PID.

====== VÌ SAO KHÔNG CHẠY NĂM HARNESS CON Ở ĐÂY ======
Chúng tốn ~80 giây và spawn máy chủ thật. Việc đó là của `trien_khai/g20/chay_tat_ca.sh`.
Một bộ thử đơn vị mà chạy cả hệ thì không ai chạy nó mỗi lần sửa một dòng, và một bộ thử
không ai chạy là một bộ thử không tồn tại.

CHẠY
----
    python3 app/thu/thu_g20_hop_dong.py
"""
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC_G20 = os.path.join(DU_AN, "trien_khai", "g20")
for _d in (THU_MUC_G20, os.path.join(DU_AN, "app")):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import chay_hop_dong as HD                                                   # noqa: E402
import chot_an_toan as CHOT                                                  # noqa: E402
import tiem_loi as TL                                                        # noqa: E402

LOAI_HOP_LE = {"harness", "cham-hang", "ngoai-pham-vi"}
TRANG_THAI_MONG_DOI_HOP_LE = {HD.CHAY_DUOC, HD.BLOCKED}
KHOA_CHANG_BAT_BUOC = ("ma", "ten", "loai", "trang_thai_mong_doi", "chot_can", "buoc",
                       "bao_cao_json", "mong_doi")
#: Chặng KHÔNG BAO GIỜ chạy chỉ cần khai được nó là gì và vì sao bị chặn.
KHOA_CHANG_KHAI_BAO = ("ma", "ten", "loai", "trang_thai_mong_doi", "ly_do_blocked")
BIEN_THAY_THE_HOP_LE = ("${NEN}", "${CONG_PG}")


def doc_hop_dong():
    with open(HD.HOP_DONG_MAC_DINH, encoding="utf-8") as f:
        return json.load(f)


class A_HopDongLaDuLieu(unittest.TestCase):
    """Hợp đồng phải là DỮ LIỆU tự nhất quán — không phải văn xuôi đọc bằng mắt."""

    def setUp(self):
        self.hd = doc_hop_dong()
        self.chang = self.hd["chang"]

    def test_a01_doc_duoc_va_co_phien_ban(self):
        self.assertIn("phien_ban", self.hd)
        self.assertIsInstance(self.hd["phien_ban"], int)
        self.assertTrue(self.hd.get("ten"))
        self.assertGreater(len(self.chang), 0)

    def test_a02_moi_chang_du_khoa_bat_buoc(self):
        # Chặng `cham-hang`/`ngoai-pham-vi` KHÔNG BAO GIỜ chạy, nên nó không có `buoc` lẫn
        # `mong_doi` — đó là thiết kế, không phải thiếu sót. Khoá ấy chỉ bắt buộc với chặng
        # THỰC THI.
        thieu = {}
        for c in self.chang:
            can = KHOA_CHANG_BAT_BUOC if c["loai"] == "harness" else KHOA_CHANG_KHAI_BAO
            t = [k for k in can if k not in c]
            if t:
                thieu[c.get("ma", "?")] = t
        self.assertEqual(thieu, {}, "chặng thiếu khoá bắt buộc: %s" % thieu)

    def test_a03_ma_chang_khong_trung(self):
        ma = [c["ma"] for c in self.chang]
        trung = {m for m in ma if ma.count(m) > 1}
        self.assertEqual(trung, set(), "mã chặng trùng: %s" % trung)

    def test_a04_du_so_chang_toi_thieu(self):
        self.assertGreaterEqual(len(self.chang), int(self.hd["so_chang_toi_thieu"]))
        # Năm harness con PHẢI có mặt — thiếu một cái là hợp đồng mất một mắt xích.
        for ma in ("G16", "G17", "G18", "G18-CRASH", "G19"):
            self.assertIn(ma, [c["ma"] for c in self.chang])

    def test_a05_loai_hop_le(self):
        for c in self.chang:
            self.assertIn(c["loai"], LOAI_HOP_LE, "chặng %s có loai lạ" % c["ma"])

    def test_a06_trang_thai_mong_doi_hop_le(self):
        for c in self.chang:
            self.assertIn(c["trang_thai_mong_doi"], TRANG_THAI_MONG_DOI_HOP_LE,
                          "chặng %s khai trạng thái mong đợi lạ" % c["ma"])

    def test_a07_cham_hang_phai_khai_giay_phep(self):
        for c in self.chang:
            if c["loai"] == "cham-hang":
                self.assertTrue(c.get("giay_phep_can"),
                                "chặng CHẠM HÃNG %s không khai mã giấy phép" % c["ma"])
                self.assertTrue(c.get("ly_do_blocked"),
                                "chặng CHẠM HÃNG %s không khai lý do bị chặn" % c["ma"])

    def test_a08_chang_harness_phai_co_lenh_va_bao_cao(self):
        for c in self.chang:
            if c["loai"] != "harness":
                continue
            self.assertTrue(c["buoc"], "chặng %s không có bước nào" % c["ma"])
            for b in c["buoc"]:
                self.assertTrue(b.get("lenh"), "chặng %s có bước rỗng" % c["ma"])
                self.assertIn("ma_thoai", b, "chặng %s có bước không khai mã thoát" % c["ma"])
            self.assertTrue(c["bao_cao_json"] or c["ma"] == "G18-CRASH",
                            "chặng %s không khai báo cáo và cũng không nói vì sao" % c["ma"])

    def test_a09_chot_can_phai_co_dinh_nghia(self):
        dinh_nghia = set(self.hd["chot_can_dinh_nghia"])
        self.assertEqual(dinh_nghia, set(CHOT.THU_TU_CHOT),
                         "định nghĩa chốt trong hợp đồng LỆCH với mã chốt trong mã")
        for c in self.chang:
            for k in c.get("chot_can", []):
                self.assertIn(k, dinh_nghia, "chặng %s đòi chốt không có định nghĩa: %s"
                              % (c["ma"], k))

    def test_a11_chang_cham_hang_khong_bao_gio_duoc_chay(self):
        """Chặng chạm hãng KHÔNG được có lệnh — có lệnh nghĩa là nó SẼ chạy khi ai đó gỡ chốt."""
        for c in self.chang:
            if c["loai"] in ("cham-hang", "ngoai-pham-vi"):
                self.assertEqual(c.get("buoc", []), [],
                                 "chặng bị chặn %s lại có lệnh để chạy" % c["ma"])
                self.assertEqual(c["trang_thai_mong_doi"], HD.BLOCKED,
                                 "chặng bị chặn %s không khai trạng thái mong đợi là BLOCKED"
                                 % c["ma"])

    def test_a10_bien_thay_the_chi_dung_bien_cho_phep(self):
        import re
        for c in self.chang:
            tho = json.dumps(c, ensure_ascii=False)
            for bien in re.findall(r"\$\{[A-Z_]+\}", tho):
                self.assertIn(bien, BIEN_THAY_THE_HOP_LE,
                              "chặng %s dùng biến thay thế lạ %s" % (c["ma"], bien))


class B_ChotAnToan(unittest.TestCase):
    """Bảy chốt phải PHÂN BIỆT được cấu hình an toàn với cấu hình nguy hiểm."""

    def test_b01_tu_kiem_toan_bo_ca_dat(self):
        tong, hong, _ = CHOT.tu_kiem(cho_in=False)
        self.assertEqual(hong, 0, "%d/%d ca tự kiểm chốt HỎNG" % (hong, tong))
        self.assertGreaterEqual(tong, 14)

    def test_b02_doi_chung_duong_di_qua(self):
        """Thiếu ca này thì một bộ dò `return ['từ chối']` cũng 'bắt' được mọi ca hỏng."""
        ca = CHOT.bo_ca_tu_kiem()
        duong = [c for c in ca if not c[2]]
        self.assertTrue(duong, "bộ ca tự kiểm KHÔNG có đối chứng dương nào")
        for _, mo_ta, _, _, kw in duong:
            self.assertEqual(CHOT.kiem_tat_ca(kw), {}, "đối chứng dương bị từ chối: %s" % mo_ta)

    def test_b03_moi_ca_hong_bi_bat_boi_dung_chot(self):
        for ma, mo_ta, phai_tu_choi, chua, kw in CHOT.bo_ca_tu_kiem():
            if not phai_tu_choi:
                continue
            with self.subTest(ca=ma):
                do = CHOT.kiem_tat_ca(kw)
                self.assertTrue(do, "ca %s KHÔNG bị từ chối" % ma)
                phang = [x for ds in do.values() for x in ds]
                self.assertTrue(any(chua in x for x in phang),
                                "ca %s bị bắt nhưng KHÔNG bởi chốt chứa %r: %s" % (ma, chua, phang))

    def test_b04_moi_truong_that_hien_tai_du_chot(self):
        nen = tempfile.mkdtemp(prefix="g20_thu_chot_")
        try:
            do = CHOT.kiem_tat_ca({"nen": nen})
            self.assertEqual(do, {}, "môi trường HIỆN TẠI đang mất chốt: %s" % do)
        finally:
            os.rmdir(nen)

    def test_b05_nguon_lan_khong_goi_giet_theo_ten(self):
        """Chốt N6 soi CHÍNH mã của làn này: không được có lệnh giết theo TÊN tiến trình."""
        do = CHOT.kiem_tat_ca({"nen": tempfile.gettempdir()})
        self.assertNotIn("N6", do, "nguồn làn G20 có lệnh giết theo tên: %s" % do.get("N6"))
        nguon = CHOT._doc_nguon_lan()
        self.assertTrue(nguon, "chốt N6 không đọc được nguồn nào — chốt mù")
        self.assertIn("chay_tat_ca.sh", nguon, "chốt N6 KHÔNG soi script shell của làn")


class C_TiemLoi(unittest.TestCase):
    """Bộ phán phải ĐỎ ĐƯỢC — và phải XANH ở đối chứng dương."""

    @classmethod
    def setUpClass(cls):
        cls.tong, cls.hong, cls.chi_tiet = TL.chay_tat_ca(cho_in=False)

    def test_c01_tiem_loi_toan_bo_ca_dat(self):
        self.assertEqual(self.hong, 0, "các phép tiêm KHÔNG bắt được: %s"
                         % [c["ma"] for c in self.chi_tiet if not c["dat"]])
        self.assertGreaterEqual(self.tong, 14)

    def test_c02_doi_chung_duong_P0_phai_xanh(self):
        p0 = [c for c in self.chi_tiet if c["ma"] == "P0"]
        self.assertEqual(len(p0), 1, "bộ tiêm lỗi KHÔNG có đối chứng dương P0")
        self.assertTrue(p0[0]["dat"], "P0 HỎNG: %s" % p0[0])
        self.assertEqual(p0[0]["trang_thai"], HD.CHAY_DUOC)

    def test_c03_moi_phep_tiem_deu_bat_duoc(self):
        for c in self.chi_tiet:
            with self.subTest(ca=c["ma"]):
                self.assertTrue(c["dat"], "%s: %s" % (c["ma"], c))

    def test_c04_bon_loai_loi_deu_co_ca(self):
        """Bốn nhóm lỗi khác nhau phải đều có mặt — một nhóm thiếu là một lỗ mù."""
        ma = {c["ma"] for c in self.chi_tiet}
        for nhom in (("F01", "F02", "F03", "F04"),      # mã thoát, báo cáo thiếu/hỏng/thiếu khoá
                     ("F05", "F06", "F07", "F08"),      # nội dung báo cáo sai
                     ("F09", "F09b", "F10", "F11"),     # chốt an toàn và giấy phép
                     ("F12",)):                         # hợp đồng rỗng
            self.assertTrue(set(nhom) <= ma, "thiếu nhóm phép tiêm %s" % (nhom,))


class D_BacCauBaoCao(unittest.TestCase):
    """Ba harness con có BA kiểu báo cáo — bộ bắc cầu phải hiểu cả ba."""

    def test_d01_hieu_bao_cao_co_dem_lan_blocked(self):
        bc = {"dem": {"DAT": 32, "DAT_MOCK": 12, "BLOCKED": 2}, "blocked": [{"ma": "G05"}] * 2}
        self.assertEqual(HD._dem_blocked(bc), (True, 2))

    def test_d02_hieu_bao_cao_CHI_co_dem(self):
        """G18 KHÔNG có khoá `blocked` — chỉ có `dem.BLOCKED`. Đây là chỗ dễ bắc cầu sai nhất."""
        bc = {"dem": {"DAT": 12, "HONG": 1, "BLOCKED": 1}}
        self.assertEqual(HD._dem_blocked(bc), (True, 1))
        self.assertNotIn("blocked", bc)

    def test_d03_bao_cao_la_thi_noi_KHONG_DOC_DUOC(self):
        for bc in ({}, {"route": [1, 2, 3]}, {"dem": {"DAT": 1}}):
            with self.subTest(bc=bc):
                doc_duoc, so = HD._dem_blocked(bc)
                self.assertFalse(doc_duoc, "báo cáo lạ mà dám khai đọc được số BLOCKED: %s" % bc)
                self.assertEqual(so, 0)

    def _bc_g18_chuan(self):
        return {"dem": {"DAT": 12, "DAT_MOCK": 4, "HONG": 1, "BLOCKED": 1, "BO_QUA": 2},
                "buoc": [{"ma": "G18-%02d" % i} for i in range(20)], "cau_hinh": {}}

    def test_d04_bat_thieu_khoa_bat_buoc(self):
        md = {"khoa_bat_buoc": ["buoc", "dem", "cau_hinh"]}
        bc = self._bc_g18_chuan()
        bc.pop("cau_hinh")
        dat, ly, _ = HD._kiem_bao_cao({}, bc, md)
        self.assertFalse(dat)
        self.assertTrue(any("cau_hinh" in x for x in ly), ly)

    def test_d05_bat_so_ca_HONG_vuot_nguong(self):
        dat, ly, dk = HD._kiem_bao_cao({}, self._bc_g18_chuan(), {"dem_hong_toi_da": 0})
        self.assertFalse(dat, "báo cáo có 1 ca HỎNG mà bộ phán cho qua")
        self.assertEqual(dk["dem"]["HONG"], 1)

    def test_d06_bat_lech_so_BLOCKED(self):
        bc = self._bc_g18_chuan()
        dat, _, dk = HD._kiem_bao_cao({}, bc, {"so_blocked": 1})
        self.assertTrue(dat, "hợp đồng khai 1, báo cáo khai 1 — phải khớp")
        dat2, ly2, _ = HD._kiem_bao_cao({}, bc, {"so_blocked": 2})
        self.assertFalse(dat2, "lệch số BLOCKED mà bộ phán cho qua")
        self.assertTrue(any("BLOCKED" in x for x in ly2), ly2)

    def test_d07_bat_thieu_buoc_va_thieu_route(self):
        bc = self._bc_g18_chuan()
        dat, ly, _ = HD._kiem_bao_cao({}, bc, {"so_buoc_toi_thieu": 99})
        self.assertFalse(dat)
        self.assertTrue(any("99" in x for x in ly), ly)
        dat2, ly2, _ = HD._kiem_bao_cao({}, {"route": [1] * 5}, {"so_route_toi_thieu": 80})
        self.assertFalse(dat2)
        self.assertTrue(any("route" in x for x in ly2), ly2)

    def test_d08_bat_so_blocked_khi_bao_cao_khong_doc_duoc(self):
        dat, ly, _ = HD._kiem_bao_cao({}, {"route": [1, 2]}, {"so_blocked": 0})
        self.assertFalse(dat, "hợp đồng khai số BLOCKED nhưng báo cáo không có — phải là HỎNG")
        self.assertTrue(any("BLOCKED" in x for x in ly), ly)

    def test_d09_bat_bao_cao_thieu_va_json_hong(self):
        ok, _, loi = HD.doc_json("/khong/co/that/g20.json")
        self.assertFalse(ok)
        self.assertIn("KHÔNG có tệp báo cáo", loi)
        d = tempfile.mkdtemp(prefix="g20_thu_json_")
        try:
            p = os.path.join(d, "hong.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{ hong ,,,")
            ok2, _, loi2 = HD.doc_json(p)
            self.assertFalse(ok2)
            self.assertIn("không đọc được", loi2)
        finally:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


class E_NenVaPID(unittest.TestCase):
    """Nền tách nhau, và mọi lượt dọn theo ĐÚNG PID."""

    def test_e01_hai_lan_goi_cho_hai_nen_KHAC_nhau(self):
        goc = tempfile.mkdtemp(prefix="g20_thu_nen_")
        try:
            a = HD.dung_nen(goc)
            b = HD.dung_nen(goc)
            self.assertNotEqual(a, b, "hai lượt dùng CHUNG một nền — hai làn sẽ giẫm lên nhau")
            self.assertTrue(os.path.isdir(a) and os.path.isdir(b))
        finally:
            import shutil
            shutil.rmtree(goc, ignore_errors=True)

    def test_e02_nen_nam_trong_thu_muc_tam(self):
        goc = tempfile.mkdtemp(prefix="g20_thu_nen2_")
        try:
            self.assertTrue(CHOT._trong_thu_muc_tam(HD.dung_nen(goc)))
        finally:
            import shutil
            shutil.rmtree(goc, ignore_errors=True)

    def test_e03_chuan_hoa_git_go_gia_dinh_di_dang(self):
        env = {"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_VALUE_0": "false",
               "GIT_CONFIG_VALUE_1": "false", "KHAC": "giu"}
        sach, da_go = HD.chuan_hoa_git(env)
        self.assertTrue(da_go, "gia đình GIT_CONFIG_* dị dạng KHÔNG bị gỡ")
        self.assertEqual([k for k in sach if k.startswith("GIT_CONFIG_")], [])
        self.assertEqual(sach["KHAC"], "giu")

    def test_e04_chuan_hoa_git_khong_dung_gia_dinh_lanh(self):
        for env in ({}, {"GIT_CONFIG_COUNT": "0"},
                    {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name",
                     "GIT_CONFIG_VALUE_0": "x"}):
            with self.subTest(env=env):
                sach, da_go = HD.chuan_hoa_git(env)
                self.assertFalse(da_go, "gia đình git LÀNH mà bị gỡ: %s" % env)
                self.assertEqual(sach, env)

    def test_e05_tat_tien_trinh_con_theo_DUNG_PID(self):
        nen = tempfile.mkdtemp(prefix="g20_thu_pid_")
        try:
            bo = HD.BoChay(nen)
            ma, _, pid, het, loi = bo.chay(
                [sys.executable, "-c", "import time; time.sleep(60)"], dict(os.environ), 1)
            self.assertEqual(loi, "")
            self.assertTrue(het, "tiến trình ngủ 60s mà KHÔNG bị coi là hết giờ")
            self.assertIsInstance(pid, int)
            self.assertEqual(bo.con_song(), [], "PID %s vẫn sống sau khi dọn" % pid)
            self.assertTrue(os.path.isfile(bo.pid_file), "không ghi PID ra tệp để trap đọc")
            with open(bo.pid_file, encoding="utf-8") as f:
                self.assertIn(str(pid), f.read())
        finally:
            import shutil
            shutil.rmtree(nen, ignore_errors=True)

    def test_e06_nguon_lan_khong_co_lenh_giet_theo_ten(self):
        """Ca ĐỘC LẬP với N6: đọc thẳng mã, không qua bộ lọc của chốt.

        Dùng ĐÚNG khuôn `\\b` như chốt N6. `assertNotIn("pkill", ...)` thô sẽ bắt oan chính
        tên hàm `kiem_khong_pkill` — và một ca thử bắt oan thì sẽ bị người sau nới lỏng cho
        qua, rồi chốt thật mất luôn ca thử.
        """
        for ten in ("chay_hop_dong.py", "chot_an_toan.py", "tiem_loi.py", "gia_lap_chang.py",
                    "chay_tat_ca.sh"):
            p = os.path.join(THU_MUC_G20, ten)
            self.assertTrue(os.path.isfile(p), "thiếu tệp mã của làn: %s" % ten)
            with open(p, encoding="utf-8") as f:
                ma = CHOT.loc_chu_thich_va_chuoi(ten, f.read())
            with self.subTest(tep=ten):
                self.assertEqual(re.findall(r"\b(?:pkill|killall)\b", ma), [],
                                 "%s có lệnh giết theo TÊN" % ten)

    def test_e07_nguon_lan_that_su_bi_soi(self):
        """Một chốt có danh sách cứng là một chốt có lỗ: tệp mã mới phải tự vào tầm soi."""
        for ten in ("chay_hop_dong.py", "chot_an_toan.py", "tiem_loi.py", "gia_lap_chang.py"):
            self.assertIn(ten, CHOT.NGUON_PY, "chốt N6 KHÔNG soi %s" % ten)
        self.assertIn("chay_tat_ca.sh", CHOT.NGUON_SH, "chốt N6 KHÔNG soi script shell của làn")
        nguon = CHOT._doc_nguon_lan()
        self.assertIn("app/thu/thu_g20_hop_dong.py", nguon,
                      "chốt N6 KHÔNG soi chính bộ thử này")


if __name__ == "__main__":
    unittest.main(verbosity=2)
