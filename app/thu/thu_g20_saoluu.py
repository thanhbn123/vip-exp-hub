#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — BỘ THỬ: VÒNG TRÒN SAO LƯU → KHÔI PHỤC.

Chạy:  python3 app/thu/thu_g20_saoluu.py
       `app/thu/chay_tat_ca.sh` tự dò tệp này (`app/thu/thu_*.py`) nên nó vào lượt hồi quy chung.

====== BỘ NÀY ĐO CÁI GÌ, VÀ KHÔNG ĐO CÁI GÌ ======
ĐO: `migrate.sao_luu()` rồi `migrate.khoi_phuc()` — TỪNG BẢNG, cả SỐ DÒNG lẫn TỔNG TIỀN —
    trên CSDL có dữ liệu thật (3 tenant, 15 đơn COD, 57 bút toán, 31.141.000 đồng), và sáu
    đường hỏng: tệp bị cắt giữa đường, tệp bị sửa 1 byte, khôi phục đè lên CSDL đang chạy,
    khôi phục bản schema thấp hơn, khôi phục nhầm tệp không phải SQLite, khôi phục thiếu khóa.
KHÔNG ĐO: `pg_dump`/`pg_restore` (đã có `app/thu/thu_postgres.py` lớp K) · sao lưu khóa
    (đã có `trien_khai/sao_luu_ngoai/` + `app/sao_luu_khoa.py`) · sao lưu ngoài máy / đám mây.

====== BA LOẠI KHẲNG ĐỊNH TRONG TỆP NÀY, ĐỪNG LẪN ======
1. **BẮT BUỘC ĐÚNG** — đường lành phải khôi phục ra đúng dữ liệu, đối chứng đường phải làm
   ĐỎ được phép so. Đỏ ở đây là HỎNG THẬT.
2. **ĐẶC TẢ HÀNH VI ĐÃ ĐO** (characterization) — ghi lại hành vi HIỆN TẠI của `khoi_phuc()`
   ở các đường hỏng, kèm nhãn `ĐỘC HẠI ĐÃ BIẾT`. Đỏ ở đây nghĩa là HÀNH VI ĐÃ ĐỔI: nếu anh
   vừa vá `khoi_phuc()`, hãy cập nhật ca này VÀ `docs/G20_BACKUP_RESTORE.md`. Đó là mục đích
   của chúng — một khuyết điểm không có ca thử thì lần sau không ai biết nó còn hay mất.
3. **TỰ KIỂM BỎ ĐỒ** (`I_TuKiemBoDo`) — chứng minh phép so LÀM ĐỎ ĐƯỢC. Thiếu lớp này thì một
   `so_sanh()` luôn trả `[]` cũng "đạt" hết mọi ca ở trên.

====== MÔI TRƯỜNG ======
Mọi lượt đo chạy trong thư mục TẠM, qua tiến trình con với `VIP_HUB_DATA` riêng.
`kich_ban.chot_an_toan()` TỪ CHỐI mọi đường nằm trong vùng dữ liệu thật của dự án.
KHÔNG gọi mạng. Cụm PostgreSQL là cụm RIÊNG (socket Unix), TỪ CHỐI cổng 5432.
"""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAY_G20 = os.path.join(GOC, "trien_khai", "g20-saoluu")
sys.path.insert(0, DAY_G20)

import khung_do   # noqa: E402
import kich_ban   # noqa: E402


# ============================================================================
# A — VÒNG TRÒN ĐẦY ĐỦ TRÊN DỮ LIỆU THẬT, KHÔI PHỤC VÀO CSDL MỚI
# ============================================================================
class A_VongTronTrenDuLieuThat(unittest.TestCase):
    """`sao_luu()` → `khoi_phuc()` vào một thư mục dữ liệu TRỐNG. Đối chiếu TỪNG BẢNG."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_vong_tron()
        print("\n        gốc : %d bảng · tổng tiền %s · băm %s"
              % (cls.kq["so_bang"], cls.kq["tong_tien_truoc"], str(cls.kq["bam_truoc"])[:16]))
        print("        kp  : %d bảng · tổng tiền %s · băm %s · integrity %s"
              % (len(cls.kq["_sau"].get("bang") or {}), cls.kq["tong_tien_sau"],
                 str(cls.kq["bam_sau"])[:16], cls.kq["integrity_sau"]))

    def test_a1_ba_lenh_deu_thanh_cong(self):
        self.assertEqual(self.kq["rc_gieo"], 0, "gieo dữ liệu hỏng: " + self.kq["loi_gieo"])
        self.assertEqual(self.kq["rc_sao_luu"], 0, "sao_luu() hỏng")
        self.assertEqual(self.kq["rc_khoi_phuc"], 0, "khoi_phuc() hỏng: " + self.kq["loi_khoi_phuc"])

    def test_a2_khoi_phuc_khop_TUNG_BANG_ca_so_dong_lan_tong_tien(self):
        """Khẳng định trung tâm của cả wave: KHÔI PHỤC RA ĐÚNG DỮ LIỆU, không chỉ 'chạy được'."""
        self.assertEqual(self.kq["lech_sau_khoi_phuc"], [],
                         "khôi phục vào CSDL MỚI ra dữ liệu KHÁC bản gốc")
        self.assertEqual(self.kq["bam_truoc"], self.kq["bam_sau"],
                         "băm toàn kho khác — có bảng/dòng đổi nội dung dù số dòng khớp")

    def test_a3_phep_do_khong_rong(self):
        """Chốt chống phép đo RỖNG: mọi cột tiền khai báo phải KHÁC 0 ở bản gốc.

        Không có ca này thì một CSDL rỗng cũng cho `so_sanh() == []` và ca a2 "đạt" vô nghĩa.
        """
        c = self.kq["_truoc"]
        khung_do.kiem_khong_rong(c, "vòng tròn")
        co_tien = [b for b, d in c["bang"].items() if d["tien"]]
        self.assertGreaterEqual(len(co_tien), 10,
                                "quá ít bảng có cột tiền — phép so TIỀN không phủ gì")
        self.assertGreater(c["tong_tien_toan_kho"], 0, "tổng tiền bản gốc bằng 0")
        self.assertGreaterEqual(c["so_bang"], 45, "quá ít bảng — nhìn nhầm CSDL")

    def test_a4_sao_luu_khong_lam_doi_csdl_goc(self):
        """Một lượt SAO LƯU không được đổi CSDL nguồn. Phép đo rẻ nhất và hay bị bỏ nhất."""
        self.assertEqual(self.kq["lech_sau_khi_sao_luu_goc"], [],
                         "sao_luu() đã làm ĐỔI CSDL gốc")

    def test_a5_ban_sao_luu_co_byte_va_mo_duoc(self):
        self.assertGreater(self.kq["so_byte_ban_sao"] or 0, 0, "bản sao lưu 0 byte")
        self.assertEqual(self.kq["integrity_sau"], "ok", "CSDL khôi phục không qua integrity_check")
        self.assertEqual(self.kq["phien_ban_sau"], 9, "phiên bản schema sau khôi phục khác 9")


# ============================================================================
# B — ĐỐI CHỨNG ĐƯỜNG: KHÔI PHỤC NGƯỢC LẠI CHÍNH CSDL GỐC
# ============================================================================
class B_DoiChungDuong(unittest.TestCase):
    """Hai vế: (a) phép so PHẢI đỏ khi dữ liệu đổi; (b) sau khôi phục phải hết đỏ."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_doi_chung_duong()
        print("\n        (a) sau khi ghi thêm : %d lệch · ví dụ %s"
              % (cls.kq["so_lech_giua"], (cls.kq["vi_du_lech_giua"] or [])[:2]))
        print("        (b) sau khôi phục    : %d lệch · tenant tạo sau mốc còn lại: %s"
              % (cls.kq["so_lech_sau_khoi_phuc"], cls.kq["tenant_sau_backup_con_lai"]))

    def test_b1_ghi_them_du_lieu_thi_phep_so_PHAI_do(self):
        """Vế (a): nếu ghi thêm 1 tenant + 1 đơn 999.000đ mà phép so vẫn im, phép so đã chết."""
        self.assertGreater(self.kq["so_lech_giua"], 0,
                           "ghi thêm tenant + đơn 999.000đ mà phép so KHÔNG thấy lệch")
        self.assertTrue(any("TIỀN" in x or "DÒNG" in x for x in self.kq["vi_du_lech_giua"]),
                        "phép so thấy lệch nhưng không ở trục DÒNG/TIỀN: %s"
                        % (self.kq["vi_du_lech_giua"],))

    def test_b2_khoi_phuc_nguoc_lai_chinh_csdl_goc_ra_Y_NGUYEN(self):
        """Vế (b): khôi phục về chính CSDL gốc phải cho kết quả y nguyên từng bảng."""
        self.assertEqual(self.kq["rc_khoi_phuc"], 0, "khoi_phuc() hỏng")
        self.assertEqual(self.kq["so_lech_sau_khoi_phuc"], 0,
                         "khôi phục ngược lại CSDL gốc KHÔNG y nguyên: %s"
                         % (self.kq["lech_sau_khoi_phuc"],))

    def test_b3_du_lieu_tao_sau_moc_sao_luu_da_mat(self):
        """Khôi phục phải THẬT SỰ lùi thời gian — nếu không thì nó không khôi phục gì cả."""
        self.assertEqual(self.kq["tenant_sau_backup_con_lai"], 0,
                         "tenant tạo SAU mốc sao lưu vẫn còn — khôi phục không có tác dụng")

    def test_b4_co_cat_ban_truoc_khi_khoi_phuc(self):
        self.assertTrue(self.kq["ban_truoc_khoi_phuc"],
                        "không thấy bản `hub-truoc-rollback-*.db` — dữ liệu cũ mất không dấu vết")


# ============================================================================
# C — SAO LƯU BỊ CẮT GIỮA ĐƯỜNG
# ============================================================================
class C_SaoLuuBiCatGiuaDuong(unittest.TestCase):
    """Ba cách cắt: hết chỗ ghi · bị giết giữa lúc ghi · tệp cắt cụt sau khi ghi."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_sao_luu_cat_giua_duong()
        for c in cls.kq["cac_cach_cat"]:
            print("\n        %-18s tệp dở %-11s khoi_phuc NHẬN=%-5s CSDL sau: %s"
                  % (c["cach"], c["co_tep_de"], c["khoi_phuc_NHAN"],
                     (c["csdl_sau"] or {}).get("loi") or (c["csdl_sau"] or {}).get("so_bang")))

    def test_c1_doi_chung_duong_tep_lanh_khoi_phuc_dat(self):
        """Vế đối chứng: cùng đường đó, tệp LÀNH phải khôi phục khớp gốc.

        Không có vế này thì "tệp dở bị nhận" có thể chỉ là hệ quả của một `khoi_phuc()` hỏng
        với mọi tệp — hai kết luận khác hẳn nhau.
        """
        self.assertEqual(self.kq["doi_chung_duong"]["rc_khoi_phuc"], 0)
        self.assertEqual(self.kq["doi_chung_duong"]["so_lech"], 0,
                         "tệp LÀNH mà khôi phục cũng lệch — đối chứng đường hỏng")
        self.assertEqual(self.kq["doi_chung_duong"]["tong_tien"], self.kq["tong_tien_goc"])

    def test_c2_it_nhat_ba_tep_bi_cat_that_su(self):
        """Chốt chống phép đo rỗng: phải CÓ tệp dở thật, không phải 5 lượt cắt trượt."""
        self.assertGreaterEqual(self.kq["so_cach_tep_de_that_su_cut"], 3,
                                "không tạo được tệp dở nào — kịch bản cắt không chạy")

    def test_c3_DOC_HAI_DA_BIET_khoi_phuc_nhan_tep_de_khong_kiem_gi(self):
        """ĐỘC HẠI ĐÃ BIẾT — `khoi_phuc()` nhận MỌI tệp dở, kể cả tệp 0 byte.

        Đo 16/10/2026: cả 5 lượt cắt đều được `khoi_phuc()` NHẬN với mã thoát 0.
        Tệp 0 byte (hết chỗ ghi) đặc biệt nguy: `PRAGMA integrity_check` trả **"ok"** cho nó —
        vì tệp SQLite dài 0 byte LÀ một CSDL rỗng HỢP LỆ. Nghĩa là một bước "kiểm tra bản sao
        lưu bằng integrity_check" cũng KHÔNG bắt được ca này; chỉ kiểm SỐ BYTE / SỐ BẢNG mới bắt.

        Nếu ca này đỏ: hành vi `khoi_phuc()` ĐÃ ĐỔI. Cập nhật ca + `docs/G20_BACKUP_RESTORE.md`.
        """
        self.assertEqual(self.kq["so_cach_bi_NHAN"], len(self.kq["cac_cach_cat"]),
                         "khoi_phuc() đã BẮT ĐẦU từ chối tệp dở — hành vi đã đổi, cập nhật tài liệu")
        teo = [c for c in self.kq["cac_cach_cat"] if c["co_tep_de"] == 0]
        self.assertTrue(teo, "không còn ca tệp 0 byte — kịch bản hết chỗ ghi không chạy")
        self.assertEqual(teo[0]["csdl_sau"]["integrity"], "ok",
                         "tệp 0 byte không còn qua integrity_check — cập nhật nhận định")
        self.assertEqual(teo[0]["csdl_sau"]["so_bang"], 0,
                         "CSDL sau khi khôi phục từ tệp 0 byte KHÔNG rỗng — đo lại")


# ============================================================================
# D — TỆP SAO LƯU BỊ SỬA 1 BYTE
# ============================================================================
class D_SuaMotByte(unittest.TestCase):
    """Năm chỗ sửa: 25% · 50% · 75% · byte 0 · và một byte TRONG TRANG DỮ LIỆU ĐANG DÙNG."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_sua_mot_byte()
        for c in cls.kq["cac_lan_sua"]:
            print("\n        %-13s vị trí %-8s sqlite tự báo: %-44s băm khớp gốc: %-5s rc_kp=%s"
                  % (c["nhan"], c["vi_tri"], str(c["sqlite_tu_bao"])[:44], c["bam_khop_goc"],
                     c["rc_khoi_phuc"]))

    def test_d1_doi_chung_duong_tep_khong_sua_thi_dat(self):
        self.assertTrue(self.kq["doi_chung_duong_dat"],
                        "tệp KHÔNG sửa mà khôi phục cũng lệch: %s" % (self.kq["doi_chung_duong"],))

    def test_d2_byte_trong_trang_dung_lam_doi_du_lieu_va_bo_do_THAY(self):
        """Chốt quan trọng nhất của lớp này: có MỘT ca sửa 1 byte làm đổi dữ liệu THẬT.

        Bốn chỗ theo tỉ lệ (25/50/75%, byte 0) là may rủi — đo được: ba chỗ giữa tệp rơi vào
        vùng không dùng nên KHÔNG đổi gì. Nếu chỉ đo bốn chỗ đó thì kết luận rút ra là
        "sửa 1 byte vô hại", một kết luận SAI. Ca này tìm thẳng byte đầu của mã đơn
        `SHOP-A-002` trong `don_hang.ma_don` nên CHẮC CHẮN nằm trong trang có dữ liệu.
        """
        c = self.kq["cac_lan_sua"][0]
        self.assertEqual(c["nhan"], "e-trang-dung", "ca byte-trong-trang-dung không chạy")
        self.assertFalse(c["bam_khop_goc"],
                         "sửa byte trong trang dữ liệu đang dùng mà băm vẫn khớp — "
                         "băm toàn kho KHÔNG nhạy với thay đổi dữ liệu")
        self.assertGreater(c["so_lech"], 0, "phép so TỪNG BẢNG không thấy byte bị sửa")

    def test_d3_byte_0_lam_tep_khong_con_la_sqlite(self):
        c = [x for x in self.kq["cac_lan_sua"] if x["nhan"] == "d-byte0"][0]
        self.assertIn("not a database", str(c["loi"]) + str(c["sqlite_tu_bao"]),
                      "sửa byte 0 không còn làm hỏng phần đầu tệp — đo lại")
        self.assertIsNone(c["integrity"])

    def test_d4_DOC_HAI_DA_BIET_khoi_phuc_nhan_ca_5_ban_da_sua(self):
        """ĐỘC HẠI ĐÃ BIẾT — `khoi_phuc()` không kiểm tệp trước khi đè lên CSDL đang chạy.

        Đo 16/10/2026: 5/5 bản bị sửa được NHẬN với mã thoát 0, kể cả bản mà CHÍNH SQLite đã
        báo `file is not a database` và bản mà SQLite báo `row 2 missing from index …`.
        `khoi_phuc()` chỉ `shutil.copy2` — không `integrity_check`, không kiểm số bảng, không
        kiểm phần đầu tệp. Nếu ca này đỏ: hành vi ĐÃ ĐỔI, cập nhật ca + tài liệu.
        """
        self.assertEqual(self.kq["so_lan_khoi_phuc_NHAN_tat_ca"], len(self.kq["cac_lan_sua"]),
                         "khoi_phuc() đã bắt đầu từ chối tệp bị sửa — hành vi đã đổi")


# ============================================================================
# E — KHÔI PHỤC ĐÈ LÊN CSDL ĐÃ CÓ DỮ LIỆU
# ============================================================================
class E_KhoiPhucDeLenCsdlDangChay(unittest.TestCase):
    """Bản cất `hub-truoc-rollback-*.db` có thật sự cứu được dữ liệu vừa bị đè không?"""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay()
        print("\n        1 lượt khôi phục → %s bản cất · 3 lượt cùng giây → %s bản cất"
              % (cls.kq["so_ban_cat_sau_1_lan"], cls.kq["so_ban_cat_sau_3_lan"]))
        print("        bản cất còn giữ được dữ liệu vừa mất: %s"
              % cls.kq["ban_cat_con_giu_duoc_du_lieu_goc"])

    def test_e1_ba_luot_khoi_phuc_deu_thanh_cong(self):
        self.assertEqual([self.kq["rc_kp1"], self.kq["rc_kp2"], self.kq["rc_kp3"]], [0, 0, 0])

    def test_e2_ban_cat_sau_MOT_luot_chua_dung_du_lieu_vua_mat(self):
        """Vế ĐỐI CHỨNG (tích cực): `khoi_phuc()` CÓ cất bản trước khi đè, và bản đó ĐÚNG."""
        self.assertEqual(self.kq["so_ban_cat_sau_1_lan"], 1, "không cất bản trước khi đè")
        self.assertTrue(self.kq["noi_dung_ban_cat"]["khop_dung_luc_chup_day"],
                        "bản cất KHÔNG khớp dữ liệu lúc chụp: %s" % (self.kq["noi_dung_ban_cat"],))
        self.assertEqual(self.kq["noi_dung_ban_cat"]["integrity"], "ok")

    def test_e3_DOC_HAI_DA_BIET_ba_luot_cung_giay_ghi_de_mat_ban_cat_duy_nhat(self):
        """ĐỘC HẠI ĐÃ BIẾT — tên bản cất đặt theo GIÂY, lượt sau GHI ĐÈ IM LẶNG lượt trước.

        Đo 16/10/2026: ba lượt `khoi_phuc()` liên tiếp trong cùng một giây để lại **1** tệp
        `hub-truoc-rollback-*.db`, và băm của nó KHÁC băm dữ liệu vừa bị đè — tức bản cất của
        lượt ĐẦU (thứ duy nhất chứa dữ liệu thật) đã bị lượt SAU xoá mất.

        Đây ĐÚNG khuôn lỗi mà `sao_luu()` đã bị bắt và đã sửa (nó thêm hậu tố `-1`, `-2`):
        cùng một tệp `app/migrate.py`, một hàm đã vá, một hàm chưa. Nếu ca này đỏ: ai đó đã vá
        `khoi_phuc()` — cập nhật ca + `docs/G20_BACKUP_RESTORE.md`, và gỡ mục khỏi báo cáo.
        """
        self.assertEqual(self.kq["so_ban_cat_sau_1_lan"], 1)
        self.assertEqual(self.kq["so_ban_cat_sau_3_lan"], 1,
                         "số bản cất đã tăng — hành vi đã đổi, cập nhật tài liệu")
        self.assertFalse(self.kq["ban_cat_con_giu_duoc_du_lieu_goc"],
                         "bản cất vẫn giữ được dữ liệu gốc — hành vi đã đổi")
        self.assertNotEqual(self.kq["bam_ban_cat_sau_1_lan"], self.kq["bam_ban_cat_sau_3_lan"],
                            "băm không đổi — bản cất không bị ghi đè, đo lại")


# ============================================================================
# F — KHÔI PHỤC BẢN SAO LƯU CÓ SCHEMA THẤP HƠN
# ============================================================================
class F_SchemaThapHon(unittest.TestCase):
    """v6 đè lên v9: hệ có NÓI RA không?"""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_khoi_phuc_schema_thap_hon()
        print("\n        v6 %s bảng / phiên bản %s  →  v9 %s bảng / phiên bản %s"
              % (cls.kq["so_bang_v6"], cls.kq["phien_ban_v6"], cls.kq["so_bang_v9_truoc"],
                 cls.kq["phien_ban_v9_truoc"]))
        print("        SAU khôi phục: %s" % (cls.kq["chup_sau"],))
        print("        nâng lại bằng migrate.chay(): %s" % (cls.kq["chup_sau_khi_nang"],))

    def test_f1_dung_duoc_csdl_v6_bang_chinh_migrate(self):
        self.assertEqual(self.kq["rc_dung_v6"], 0, "dựng v6 hỏng: " + self.kq["loi_v6"][-200:])
        self.assertEqual(self.kq["phien_ban_v6"], 6)
        self.assertGreater(self.kq["so_bang_v6"], 15)

    def test_f2_khoi_phuc_v6_de_len_v9_ra_DUNG_csdl_v6(self):
        """Về mặt CƠ HỌC thì khôi phục đúng: CSDL sau = nguyên bản sao lưu v6."""
        self.assertEqual(self.kq["rc_khoi_phuc"], 0)
        self.assertTrue(self.kq["khoi_phuc_ra_dung_v6"], "CSDL sau khác bản sao lưu v6")

    def test_f3_DOC_HAI_DA_BIET_tut_schema_IM_LANG(self):
        """ĐỘC HẠI ĐÃ BIẾT — khôi phục bản cũ làm TỤT schema mà không một lời báo.

        Đo 16/10/2026: đưa bản sao lưu v6 cho `khoi_phuc()` đang chạy trên CSDL v9 → mã thoát 0,
        thông báo duy nhất là "Đã khôi phục từ …". Không so phiên bản, không cảnh báo. CSDL
        còn **20 bảng** thay vì 51 — 31 bảng và toàn bộ dữ liệu của chúng biến mất, im lặng.
        Sau đó hệ VẪN CHẠY (rc 0) trên schema cũ.

        Nếu ca này đỏ: `khoi_phuc()` đã bắt đầu kiểm phiên bản — cập nhật ca + tài liệu.
        """
        self.assertEqual(self.kq["phien_ban_sau_khoi_phuc"], 6,
                         "phiên bản sau khôi phục khác 6 — hành vi đã đổi")
        self.assertEqual(self.kq["chup_sau"]["so_bang"], self.kq["so_bang_v6"],
                         "số bảng sau khôi phục khác bản v6 — đo lại")
        self.assertLess(self.kq["chup_sau"]["so_bang"], self.kq["so_bang_v9_truoc"],
                        "không mất bảng nào — kịch bản tụt schema không chạy")
        self.assertEqual(self.kq["rc_ghi_tren_v6"], 0,
                         "hệ đã từ chối chạy trên schema cũ — hành vi đã đổi")

    def test_f4_nang_lai_duoc_nhung_DU_LIEU_MOI_da_mat(self):
        """Đường ra: cấu trúc nâng lại được, DỮ LIỆU thì không. Phải nói rõ cả hai vế."""
        self.assertEqual(self.kq["rc_nang_lai"], 0, "migrate.chay() hỏng: " + self.kq["loi_nang_lai"][-200:])
        self.assertEqual(self.kq["chup_sau_khi_nang"]["phien_ban"], 9)
        self.assertEqual(self.kq["chup_sau_khi_nang"]["integrity"], "ok")
        # Nâng cấp giữ NGUYÊN dữ liệu của bản v6 (đó là điều migration phải làm)…
        self.assertEqual(self.kq["chup_sau_khi_nang"]["tong_tien"], self.kq["tong_tien_v6"],
                         "nâng lại làm ĐỔI tổng tiền của dữ liệu v6 — migration không bảo toàn")
        # …và KHÔNG lấy lại được dữ liệu đã mất khi khôi phục bản cũ. Đây là vế đắt giá nhất:
        # cấu trúc thì cứu được, DỮ LIỆU thì không.
        self.assertLess(self.kq["tong_tien_v6"], self.kq["tong_tien_v9_truoc"],
                        "bản v6 không ít tiền hơn bản v9 — kịch bản không chạy")


# ============================================================================
# G — KHÔI PHỤC NHẦM TỆP KHÔNG PHẢI SQLITE
# ============================================================================
class G_NhamTepKhongPhaiSqlite(unittest.TestCase):
    """Người trực gõ nhầm một tệp `pg_dump` vào `khoi_phuc()`."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_khoi_phuc_nham_ban_dump_pg()
        print("\n        CSDL sau khi nạp nhầm: %s" % (cls.kq["csdl_sau_khi_nham"],))

    def test_g1_doi_chung_duong_tep_sqlite_that_thi_dat(self):
        self.assertTrue(self.kq["doi_chung_duong_dat"],
                        "đối chứng đường hỏng: %s" % (self.kq["lech_duong_dung"],))

    def test_g2_DOC_HAI_DA_BIET_khoi_phuc_nhan_tep_la_va_lam_chet_csdl(self):
        """ĐỘC HẠI ĐÃ BIẾT — không có phép kiểm "tệp này có phải SQLite không".

        Đo 16/10/2026: một tệp mang magic `PGDMP` được `khoi_phuc()` NHẬN (rc 0), và CSDL đang
        chạy trở thành một khối 65.544 byte mà SQLite trả `file is not a database`. Không một
        lời cảnh báo. Nếu ca này đỏ: hành vi đã đổi, cập nhật ca + tài liệu.
        """
        self.assertTrue(self.kq["khoi_phuc_NHAN_tep_la"], "khoi_phuc() đã từ chối tệp lạ — đổi rồi")
        self.assertIn("not a database", str(self.kq["csdl_sau_khi_nham"].get("loi")),
                      "CSDL sau khi nạp nhầm vẫn đọc được — đo lại")
        self.assertLess(self.kq["so_byte_csdl_sau"], self.kq["so_byte_csdl_truoc"],
                        "CSDL sau khi nạp nhầm không nhỏ hơn bản gốc")


# ============================================================================
# H — KHÔI PHỤC CSDL MÀ THIẾU KHÓA NỘI BỘ
# ============================================================================
class H_ThieuKhoaNoiBo(unittest.TestCase):
    """`sao_luu()` chỉ sao lưu `hub.db`. Khóa mã hóa credentials nằm ở tệp KHÁC."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = kich_ban.ca_khoa_khong_di_kem()
        print("\n        gốc %s · khôi phục %s · giải mã ở gốc: %s · ở bản khôi phục: %s"
              % (cls.kq["co_khoa_o_goc"], cls.kq["co_khoa_o_ban_khoi_phuc"],
                 cls.kq["goc_giai_ma_dat"], cls.kq["khoi_phuc_giai_ma_dat"]))

    def test_h1_csdl_khoi_phuc_khop_TUNG_BANG_va_integrity_ok(self):
        """Vế dương: về mặt SỐ LIỆU, bản khôi phục hoàn hảo. Đó chính là chỗ nguy hiểm."""
        self.assertEqual(self.kq["rc_khoi_phuc"], 0)
        self.assertEqual(self.kq["so_lech_csdl"], 0, "bản khôi phục lệch dữ liệu")
        self.assertEqual(self.kq["integrity_khoi_phuc"], "ok")
        self.assertGreater(self.kq["tong_tien_khoi_phuc"], 0)

    def test_h2_doi_chung_duong_ban_goc_giai_ma_DAT(self):
        self.assertTrue(self.kq["co_khoa_o_goc"], "bản gốc không có khóa — kịch bản không chạy")
        self.assertTrue(self.kq["goc_giai_ma_dat"],
                        "bản gốc giải mã KHÔNG được: %s" % (self.kq["out_giai_ma_o_goc"],))

    def test_h3_DOC_HAI_DA_BIET_khoa_khong_di_kem_nhung_he_TU_CHOI_duoc(self):
        """KHOẢNG TRỐNG + ĐIỂM TỐT, khai cả hai.

        KHOẢNG TRỐNG: `khoi_phuc()` báo thành công trong khi bản khôi phục KHÔNG dùng được cho
        lời gọi hãng nào — khóa không đi kèm và không có gì nhắc. Người trực phải tự biết rằng
        còn một quy trình thứ hai (`app/sao_luu_khoa.py`, `trien_khai/sao_luu_ngoai/`).

        ĐIỂM TỐT (đo được, không suy đoán): hệ KHÔNG tự sinh khóa mới rồi giải mã ra rác. Nó
        NÉM `LoiKhoa` với thông báo nói thẳng phải làm gì: "Khôi phục khóa từ bản sao lưu, đừng
        sinh khóa mới." Đây là kiểu hỏng ỒN ÀO — đúng loại hỏng nên có. Nếu vế này đỏ, tức hệ
        đã bắt đầu im lặng, đó là ĐI LÙI.
        """
        self.assertFalse(self.kq["co_khoa_o_ban_khoi_phuc"],
                         "khóa CÓ đi kèm bản khôi phục — hành vi đã đổi, cập nhật tài liệu")
        self.assertFalse(self.kq["khoi_phuc_giai_ma_dat"],
                         "giải mã được ở bản khôi phục — hành vi đã đổi")
        self.assertIn("LoiKhoa", self.kq["out_giai_ma_o_khoi_phuc"],
                      "hệ không còn ném LoiKhoa — kiểm xem có phải nó đã im lặng không: %s"
                      % (self.kq["out_giai_ma_o_khoi_phuc"],))
        # `-wal`/`-shm` xuất hiện là bình thường (mở CSDL WAL là sinh chúng). Chỉ cấm tệp KHÓA.
        khoa_moi = [t for t in self.kq["tu_sinh_khoa_moi_khi_thieu"] if "khoa" in t]
        self.assertEqual(khoa_moi, [],
                         "hệ TỰ SINH tệp khóa mới khi thiếu khóa — credentials cũ thành rác "
                         "vĩnh viễn mà không ai biết")


# ============================================================================
# I — TỰ KIỂM BỎ ĐỒ: PHÉP SO PHẢI LÀM ĐỎ ĐƯỢC
# ============================================================================
class I_TuKiemBoDo(unittest.TestCase):
    """Không có lớp này thì `so_sanh()` luôn trả `[]` cũng "đạt" hết các lớp trên.

    Mọi ca ở đây SỬA BẢN SAO rồi đòi phép so PHẢI thấy khác. Sửa trên bản sao, không sửa trên
    bản gốc — để ca này không phá dữ liệu của chính nó.
    """

    nen = None
    goc = None
    duong_goc = None

    @classmethod
    def setUpClass(cls):
        cls.nen = kich_ban.chot_an_toan(tempfile.mkdtemp(prefix="g20-tukiem-"))
        A = os.path.join(cls.nen, "A")
        os.makedirs(A, exist_ok=True)
        rc, _, err = kich_ban.gieo(A)
        if rc:
            raise AssertionError("gieo hỏng: " + err[-300:])
        cls.duong_goc = kich_ban.db(A)
        cls.goc = khung_do.chup(cls.duong_goc)
        khung_do.kiem_khong_rong(cls.goc, "tự kiểm bỏ đồ")

    @classmethod
    def tearDownClass(cls):
        if cls.nen:
            shutil.rmtree(cls.nen, ignore_errors=True)

    def _ban_sao(self, ten):
        p = os.path.join(self.nen, ten)
        shutil.copy2(self.duong_goc, p)
        return p

    def test_i1_sua_TIEN_thi_phep_so_PHAI_do(self):
        """Sửa ĐÚNG 1 đồng ở một cột tiền → phép so phải thấy lệch ở trục TIỀN."""
        p = self._ban_sao("sua-tien.db")
        k = sqlite3.connect(p)
        k.execute("UPDATE don_hang SET cod = cod + 1 WHERE id = 1")
        k.commit()
        k.close()
        c = khung_do.chup(p)
        self.assertEqual(c["bang"]["don_hang"]["dong"], self.goc["bang"]["don_hang"]["dong"],
                         "số dòng đổi — ca này phải chỉ đổi TIỀN")
        lech = khung_do.so_sanh(self.goc, c)
        self.assertTrue(any(x.startswith("TIỀN") for x in lech),
                        "sửa 1 đồng mà phép so KHÔNG thấy lệch TIỀN: %s" % lech)
        self.assertNotEqual(c["tong_tien_toan_kho"], self.goc["tong_tien_toan_kho"])

    def test_i2_xoa_DONG_thi_phep_so_PHAI_do(self):
        p = self._ban_sao("xoa-dong.db")
        k = sqlite3.connect(p)
        k.execute("DELETE FROM don_lich_su WHERE id IN (SELECT id FROM don_lich_su LIMIT 3)")
        k.commit()
        k.close()
        c = khung_do.chup(p)
        lech = khung_do.so_sanh(self.goc, c)
        self.assertTrue(any(x.startswith("DÒNG") and "don_lich_su" in x for x in lech),
                        "xoá 3 dòng mà phép so KHÔNG thấy: %s" % lech)

    def test_i3_xoa_ca_BANG_thi_phep_so_PHAI_do(self):
        p = self._ban_sao("xoa-bang.db")
        k = sqlite3.connect(p)
        k.execute("DROP TABLE ds_dong")
        k.commit()
        k.close()
        c = khung_do.chup(p)
        lech = khung_do.so_sanh(self.goc, c)
        self.assertTrue(any("ds_dong" in x and ("MẤT" in x or "BẢNG" in x) for x in lech),
                        "mất cả bảng mà phép so KHÔNG thấy: %s" % lech)

    def test_i4_bam_toan_kho_bat_duoc_thay_doi_ngoai_so_dong_va_tien(self):
        """Đổi một cột KHÔNG phải tiền: số dòng và tổng tiền y nguyên, chỉ băm đổi.

        Đây là lý do `bam_toan_kho` tồn tại. Không có nó thì đổi tên khách, đổi số điện thoại,
        hay lệch một bit trong payload webhook đều đi qua im lặng.
        """
        p = self._ban_sao("sua-text.db")
        k = sqlite3.connect(p)
        k.execute("UPDATE khach_hang SET ten = ten || ' (đã sửa)' WHERE id = 1")
        k.commit()
        k.close()
        c = khung_do.chup(p)
        self.assertEqual(c["bang"]["khach_hang"]["dong"], self.goc["bang"]["khach_hang"]["dong"])
        self.assertEqual(c["tong_tien_toan_kho"], self.goc["tong_tien_toan_kho"],
                         "sửa cột tên mà tổng tiền đổi — ca này phải chỉ đổi băm")
        self.assertNotEqual(c["bam_toan_kho"], self.goc["bam_toan_kho"],
                            "sửa tên khách mà băm toàn kho KHÔNG đổi — băm không phủ bảng này")

    def test_i5_chot_chong_phep_do_RONG_phai_no(self):
        """`kiem_khong_rong` phải NÉM khi một cột tiền bằng 0 ở bản gốc."""
        rong = {"bang": {"don_hang": {"dong": 1, "tien": {"cod": 0}}}}
        with self.assertRaises(AssertionError) as cm:
            khung_do.kiem_khong_rong(rong, "ca-tu-kiem")
        self.assertIn("RỖNG", str(cm.exception))
        # Đối chứng dương: bản gốc THẬT có tiền thì KHÔNG được ném.
        self.assertTrue(khung_do.kiem_khong_rong(self.goc, "ca-tu-kiem"))

    def test_i6_danh_sach_cot_tien_phai_khong_MUC(self):
        """Chốt chống MỤC: khai một cột tiền không tồn tại thì `kiem_danh_sach` phải NÉM."""
        luu = dict(khung_do.COT_TIEN)
        try:
            khung_do.COT_TIEN["don_hang"] = tuple(luu["don_hang"]) + ("cot_tien_khong_co",)
            k = sqlite3.connect(self.duong_goc)
            with self.assertRaises(AssertionError) as cm:
                khung_do.kiem_danh_sach(k)
            k.close()
            self.assertIn("KHÔNG TỒN TẠI", str(cm.exception))
        finally:
            khung_do.COT_TIEN.clear()
            khung_do.COT_TIEN.update(luu)
        # Đối chứng dương: danh sách thật phải QUA.
        k = sqlite3.connect(self.duong_goc)
        self.assertGreaterEqual(khung_do.kiem_danh_sach(k), 10)
        k.close()

    def test_i7_khung_do_khong_lam_doi_thu_dang_do(self):
        """`chup()` chép ra vùng tạm trước khi mở. Chốt: nó KHÔNG được tạo tệp trong thư mục đo.

        Đo được 16/10/2026: bản sao lưu của `sao_luu()` mang chế độ `wal`, nên mở `mode=ro`
        thất bại và mở bình thường thì sinh `-wal`/`-shm` — một `-shm` lạc vào `sao-luu/` sẽ
        thành "bản sao lưu ma" trong phép đếm tệp của kịch bản 3.
        """
        truoc = sorted(os.listdir(os.path.dirname(self.duong_goc)))
        khung_do.chup(self.duong_goc)
        self.assertEqual(sorted(os.listdir(os.path.dirname(self.duong_goc))), truoc,
                         "chup() đã tạo tệp trong thư mục đang đo")


# ============================================================================
# K — POSTGRESQL: `sao_luu()` LÀM GÌ KHI DỮ LIỆU NẰM Ở POSTGRESQL
# ============================================================================
class K_PostgreSQL(unittest.TestCase):
    """Cụm RIÊNG, socket Unix, TỪ CHỐI cổng 5432. Thiếu công cụ thì BỎ QUA kèm LÝ DO.

    Không đo lại `pg_dump`/`pg_restore` — việc đó `thu_postgres.py` lớp K đã làm. Lớp này đo
    đúng chỗ lớp K không đo: HÀM SẢN PHẨM `migrate.sao_luu()`.
    """

    kq = None

    @classmethod
    def setUpClass(cls):
        import do_postgres
        kq = do_postgres.chay()
        if kq.get("bo_qua"):
            raise unittest.SkipTest("BỎ QUA kịch bản PostgreSQL — %s" % kq["bo_qua"])
        cls.kq = kq
        print("\n        cụm riêng cổng %s · PostgreSQL có %s dòng don_hang · tổng tiền %s"
              % (kq["cong"], kq["pg_truoc"]["bang"]["don_hang"]["dong"],
                 kq["pg_truoc"]["tong_tien"]))
        print("        `sao_luu()` khi KHÔNG có hub.db: rc=%s · %s byte · %s bảng · %s"
              % (kq["do1_hub_db_khong_ton_tai"]["rc"],
                 kq["do1_hub_db_khong_ton_tai"]["co_ban_sao"],
                 kq["do1_hub_db_khong_ton_tai"]["so_bang"],
                 kq["do1_hub_db_khong_ton_tai"]["integrity"]))

    def test_k1_cum_rieng_khong_dung_cong_5432(self):
        self.assertNotEqual(str(self.kq["cong"]), "5432")
        self.assertEqual(self.kq["van_tay_5432_khong_doi"], True,
                         "vân tay cụm :5432 ĐÃ ĐỔI: %s" % (self.kq.get("van_tay_5432_lech"),))
        self.assertIn("vip_customs", self.kq["van_tay_cum_5432"]["truoc"]["danh_sach_csdl"],
                      "không thấy vip_customs* trên :5432 — nhìn nhầm cụm")

    def test_k2_du_lieu_postgres_that_va_khong_rong(self):
        """Chốt chống phép đo rỗng: PostgreSQL phải CÓ dữ liệu thì "bản sao rỗng" mới có nghĩa."""
        b = self.kq["pg_truoc"]["bang"]
        self.assertEqual(int(b["don_hang"]["dong"]), 6)
        self.assertEqual(int(b["tc_but_toan"]["dong"]), 6)
        self.assertGreater(self.kq["pg_truoc"]["tong_tien"], 0)

    def test_k3_DOC_HAI_DA_BIET_sao_luu_IM_LANG_bao_thanh_cong_khi_kho_la_PostgreSQL(self):
        """ĐỘC HẠI ĐÃ BIẾT (P-G15-02) — `sao_luu()` báo thành công với một ĐƯỜNG LÙI GIẢ.

        Đo 16/10/2026 trên cụm riêng: `hub.db` không tồn tại (đúng trạng thái máy chủ đã chuyển
        kho sang PostgreSQL) → `sao_luu()` **KHÔNG ném lỗi**, mã thoát 0, sinh ra một tệp
        **4.096 byte, 0 BẢNG**, và `PRAGMA integrity_check` trả `"ok"`. Trong khi PostgreSQL
        đang giữ 6 đơn + 6 bút toán + 9.324.000 đồng — KHÔNG một byte nào của số đó nằm trong
        "bản sao lưu".

        Đây là dạng hỏng tệ nhất trong ba dạng: không phải ném lỗi (người trực biết ngay),
        không phải làm đúng (không thể — `csdl` không có nhánh PostgreSQL), mà là IM LẶNG.
        Chốt `so_byte <= 0` của `sao_luu()` KHÔNG cứu được: 4.096 byte > 0.

        Nếu ca này đỏ: `sao_luu()` đã bắt đầu ném lỗi hoặc kiểm kho — cập nhật ca + tài liệu.
        """
        d1 = self.kq["do1_hub_db_khong_ton_tai"]
        self.assertEqual(d1["rc"], 0, "sao_luu() đã ném lỗi trên PostgreSQL — hành vi đã đổi")
        self.assertEqual(d1["stderr"], "", "sao_luu() đã in cảnh báo — hành vi đã đổi")
        self.assertGreater(d1["co_ban_sao"] or 0, 0, "bản sao lưu 0 byte — chốt cũ đã bắt được")
        self.assertEqual(d1["so_bang"], 0, "bản sao lưu có bảng — hành vi đã đổi")
        self.assertEqual(d1["integrity"], "ok",
                         "integrity_check không còn 'ok' cho CSDL rỗng — đo lại")
        self.assertFalse(d1["co_bang_don_hang"], "bản sao lưu có bảng don_hang??")

    def test_k4_DOC_HAI_DA_BIET_hub_db_cu_thi_ban_sao_luu_chang_lien_quan_du_lieu_that(self):
        """ĐỘC HẠI ĐÃ BIẾT — dạng hỏng thứ hai, khó thấy hơn dạng rỗng.

        `hub.db` còn sót lại từ trước (dữ liệu SQLite CŨ, không còn là dữ liệu đang chạy):
        `sao_luu()` trả một bản sao **trông hoàn toàn hợp lệ** — 51 bảng, 31.141.000 đồng,
        băm khớp đúng tệp SQLite đó. Người trực thấy một tệp sao lưu "đầy đủ" và tin nó. Nhưng
        nó không chứa một dòng nào của dữ liệu PostgreSQL đang chạy.

        Không có phép kiểm nào trong hệ phân biệt được hai thứ này — vì không có chỗ nào hỏi
        "kho đang chạy là kho nào".
        """
        d2 = self.kq["do2_hub_db_co_du_lieu_sqlite_khac"]
        self.assertEqual(d2["rc"], 0)
        self.assertTrue(d2["bam_ban_sao_khop_sqlite_goc"],
                        "bản sao không khớp tệp SQLite nguồn — đo lại")
        self.assertEqual(d2["ban_sao_so_bang"], d2["sqlite_truoc_so_bang"])
        self.assertNotEqual(d2["ban_sao_tong_tien"], self.kq["pg_truoc"]["tong_tien"],
                            "tổng tiền bản sao TRÙNG tổng tiền PostgreSQL — kịch bản không chạy")

    def test_k5_DOC_HAI_DA_BIET_khoi_phuc_nhan_tep_pg_dump_that(self):
        """ĐỘC HẠI ĐÃ BIẾT — bản `pg_dump -Fc` THẬT (không phải tệp giả) đưa cho `khoi_phuc()`.

        Đo 16/10/2026: 124.700 byte, `pg_dump` trả mã thoát 0, `khoi_phuc()` NHẬN với mã thoát 0,
        CSDL SQLite đang chạy biến thành chính tệp dump đó → `file is not a database`.
        """
        d3 = self.kq["do3_khoi_phuc_tu_pg_dump"]
        self.assertEqual(self.kq["pg_dump"]["rc"], 0, "pg_dump hỏng")
        self.assertGreater(self.kq["pg_dump"]["co_byte"], 0)
        self.assertTrue(d3["khoi_phuc_NHAN"], "khoi_phuc() đã từ chối tệp pg_dump — hành vi đã đổi")
        self.assertIn("not a database", str(d3["csdl_sau_loi"]),
                      "CSDL sau khi nạp dump PostgreSQL vẫn đọc được — đo lại")

    def test_k6_doi_chung_duong_cung_ham_voi_kho_SQLITE_thi_ban_sao_co_du_lieu(self):
        """Vế đối chứng quyết định cách đọc kết quả: CÙNG hàm, kho SQLite có dữ liệu → ĐÚNG.

        Có vế này thì kết luận là "hàm không có nhánh PostgreSQL", KHÔNG phải "hàm hỏng".
        Hai câu đó khác nhau, và chỉ phép đo này phân biệt được.
        """
        d = self.kq["doi_chung_duong_sqlite_co_du_lieu"]
        self.assertEqual(d["rc"], 0)
        self.assertTrue(d["bam_khop_goc"], "cùng hàm mà kho SQLite cũng không sao lưu đúng")
        self.assertGreater(d["tong_tien"], 0)
        self.assertGreaterEqual(d["so_bang"], 45)


if __name__ == "__main__":
    unittest.main(verbosity=2)
