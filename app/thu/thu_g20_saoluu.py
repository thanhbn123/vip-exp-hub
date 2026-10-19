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
2. **BẤT BIẾN FAIL-CLOSED** — các đường hỏng phải DỪNG LẠI và BÁO RÕ, và CSDL ĐÍCH không được
   để lại nửa vời. Đỏ ở đây nghĩa là SẢN PHẨM CHƯA FAIL-CLOSED ⇒ phải sửa `app/migrate.py`.
   Xem `docs/G21_BACKUP_RESTORE.md`.
3. **TỰ KIỂM BỎ ĐỒ** (`I_TuKiemBoDo`) — chứng minh phép so LÀM ĐỎ ĐƯỢC. Thiếu lớp này thì một
   `so_sanh()` luôn trả `[]` cũng "đạt" hết mọi ca ở trên.

====== LỊCH SỬ CỦA TÁM CA `ĐỘC HẠI ĐÃ BIẾT` — ĐỌC TRƯỚC KHI "SỬA LẠI CHO XANH" ======
Lượt G20 (AG-04) viết tám ca mang nhãn `ĐỘC HẠI ĐÃ BIẾT` để **GHI LẠI** hành vi fail-open hiện
có, kèm câu "nếu ca này đỏ thì hành vi đã đổi". Chúng khẳng định ĐÚNG cái sai:
`assertEqual(khoi_phuc_NHAN_tat_ca, 5)` đòi 5/5 tệp hỏng PHẢI được nhận thì ca mới xanh.

Hệ quả đo được: bộ 41 ca **XANH**, mã thoát **0** — trong khi nghiệm thu G20 của AG-01 kết luận
**FAILED**, và chính `docs/QA_G20.md` §4.1 gọi bộ đỏ duy nhất là một lỗ hổng sản phẩm. Một bộ
thử canh hành vi fail-open thì không canh bất biến nào cả, và màu xanh của nó là màu xanh GIẢ.

**AG-02 (G21) đã VIẾT LẠI tám ca đó theo BẤT BIẾN ĐÚNG.** Chúng giờ ĐỎ trên cây này, và ĐỎ là
TÌNH TRẠNG ĐÚNG: lỗi nằm ở `app/migrate.py` — tệp của AG-00, ngoài vùng được ghi của AG-02.
Bản vá đã viết và đã đo (`trien_khai/g20-saoluu/ban_va.py`; xem `docs/G21_BACKUP_RESTORE.md`).

**KHÔNG nới điều kiện cho tám ca này xanh.** Nới ra là quay lại đúng thứ đã làm G20 FAILED.

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
        """BẤT BIẾN: khôi phục giữ NGUYÊN phiên bản schema của nguồn — không ghim một số cụ thể.

        Bản cũ đòi `phien_ban_sau == 9`. Đó là số của schema tại lượt đo G20; khi migration lên
        v10, phép thử ĐỎ dù bản sao lưu khôi phục ĐÚNG phiên bản của chính nó. Câu hỏi đúng là
        quan hệ NGUỒN → BẢN KHÔI PHỤC: hai bên phải cùng một phiên bản, bất kể phiên bản đó là 9,
        10 hay N. Số N được đọc TẠI CHỖ từ cùng lượt đo (`_truoc`), không chép tay vào tệp.
        """
        self.assertGreater(self.kq["so_byte_ban_sao"] or 0, 0, "bản sao lưu 0 byte")
        self.assertEqual(self.kq["integrity_sau"], "ok", "CSDL khôi phục không qua integrity_check")
        pb_truoc = self.kq["_truoc"].get("phien_ban")
        self.assertIsNotNone(pb_truoc, "không đọc được phiên bản schema của CSDL NGUỒN")
        self.assertEqual(self.kq["phien_ban_sau"], pb_truoc,
                         "phiên bản schema sau khôi phục KHÁC nguồn: %r != %r"
                         % (self.kq["phien_ban_sau"], pb_truoc))


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

    def test_c3_BAT_BIEN_khoi_phuc_PHAI_TU_CHOI_tep_de(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — `khoi_phuc()` phải TỪ CHỐI mọi tệp dở
        **LÀM KHÁC BẢN GỐC**.

        Ca này PIN: nhận một tệp dở KHÔNG phải tính năng. Đo 16/10/2026 trên mã chưa vá: cả 5
        lượt cắt đều được NHẬN với mã thoát 0 — trong đó lượt hết-chỗ-ghi để lại tệp **0 byte**,
        và tệp 0 byte LÀ một CSDL rỗng HỢP LỆ (`integrity_check` trả **"ok"**), nên CSDL đích
        bị thay bằng một CSDL RỖNG mà không một lời báo: 51 bảng → **0 bảng**, 34.336.000 đồng
        → **0 đồng**.

        KHÔNG đếm những lượt cắt để lại tệp ĐỦ BYTE: đo được một lượt `SIGKILL` ở 90% thời gian
        vẫn cho ra bản sao lưu trọn vẹn (51 bảng, đủ tiền). Nhận nó là ĐÚNG. Đếm nó là thổi
        phồng con số và làm mất lòng tin vào cả bảng.
        """
        hong = [c for c in self.kq["cac_cach_cat"]
                if c["khoi_phuc_NHAN"] and (
                    (c.get("csdl_sau") or {}).get("loi")
                    or (c.get("csdl_sau") or {}).get("so_bang") != self.kq["so_bang_goc"]
                    or (c.get("csdl_sau") or {}).get("tong_tien") != self.kq["tong_tien_goc"])]
        self.assertEqual(
            hong, [],
            "`khoi_phuc()` NHẬN tệp dở LÀM KHÁC BẢN GỐC ở: %s — CSDL đích bị thay bằng tệp dở. "
            "Sửa `app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
            % [c["cach"] for c in hong])
        self.assertGreaterEqual(self.kq["so_cach_tep_de_that_su_cut"], 3,
                                "phép đo RỖNG: không tạo được tệp dở thật nào")
        a = [c for c in self.kq["cac_cach_cat"] if c["cach"] == "a-het-cho-ghi"]
        self.assertTrue(a, "kịch bản hết-chỗ-ghi KHÔNG CHẠY — phép đo thiếu một vế")
        self.assertNotEqual(a[0]["rc_luot_cat"], 0,
                            "`sao_luu()` hết chỗ ghi mà vẫn thoát 0")


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

    def test_d4_BAT_BIEN_khoi_phuc_PHAI_TU_CHOI_ban_sua_LAM_DOI_DU_LIEU(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — `khoi_phuc()` phải TỪ CHỐI bản sửa **LÀM
        ĐỔI DỮ LIỆU**, và phải có ĐỐI CHỨNG ĐƯỜNG cho bản KHÔNG sửa.

        Ca này PIN: một chốt kiểm chứng chỉ có răng khi nó bắt được thay đổi DỮ LIỆU, không
        phải khi nó đếm số tệp bị nhận. Đo 16/10/2026: 5/5 bản bị sửa được NHẬN với mã thoát 0,
        kể cả bản mà CHÍNH SQLite báo `file is not a database`; CSDL đích bị thay bằng chính
        bản hỏng đó.

        KHÔNG đếm ba chỗ lật byte vào vùng trang TRỐNG (25/50/75%): đo được dữ liệu KHÔNG đổi
        (`bam_khop_goc = True`, `so_lech = 0`, `integrity = ok`) nên nhận chúng là ĐÚNG.
        """
        hong = [c for c in self.kq["cac_lan_sua"]
                if c["rc_khoi_phuc"] == 0 and (
                    (not c.get("bam_khop_goc")) or c.get("so_lech") or c.get("loi")
                    or c.get("integrity") != "ok")]
        self.assertEqual(
            hong, [],
            "`khoi_phuc()` NHẬN bản sửa LÀM KHÁC BẢN GỐC ở: %s — CSDL đích bị thay bằng bản "
            "hỏng. Sửa `app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
            % [c["nhan"] for c in hong])
        self.assertEqual(len(self.kq["cac_lan_sua"]), 5, "phép đo RỖNG: thiếu chỗ sửa")
        # ĐỐI CHỨNG ĐƯỜNG: bản KHÔNG sửa phải khôi phục ĐẠT. Thiếu vế này thì "từ chối bản sửa"
        # có thể chỉ là hệ quả của một `khoi_phuc()` hỏng với MỌI tệp — hai kết luận khác hẳn nhau.
        self.assertTrue(self.kq["doi_chung_duong_dat"],
                        "ĐỐI CHỨNG ĐƯỜNG HỎNG: bản KHÔNG sửa mà khôi phục cũng lệch: %s"
                        % (self.kq["doi_chung_duong"],))
        # Chốt chống MỤC: phép đo phải THẬT SỰ tạo ra được ít nhất một bản sửa có hại.
        co_hai = [c for c in self.kq["cac_lan_sua"] if c.get("bam_khop_goc") is False]
        self.assertTrue(co_hai, "không bản sửa nào làm đổi dữ liệu — kịch bản không chạy")


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

    def test_e3_BAT_BIEN_ba_luot_cung_giay_KHONG_duoc_xoa_nhau(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — lượt khôi phục sau KHÔNG được xoá bản cất
        của lượt trước.

        Ca này PIN: bản cất trước khi đè là thứ DUY NHẤT giữ dữ liệu vừa mất, nên tên nó không
        được đặt theo GIÂY. Đo 16/10/2026 trên mã chưa vá: ba lượt `khoi_phuc()` liên tiếp trong
        cùng một giây để lại **1** tệp `hub-truoc-rollback-*.db`, và băm của nó KHÁC băm dữ liệu
        vừa bị đè — tức bản cất của lượt ĐẦU (thứ duy nhất chứa dữ liệu thật) đã bị lượt SAU xoá.

        Đây ĐÚNG khuôn lỗi mà `sao_luu()` đã bị bắt và đã sửa (nó thêm hậu số `-1`, `-2`):
        cùng một tệp `app/migrate.py`, một hàm đã vá, một hàm chưa.
        """
        self.assertEqual(self.kq["so_ban_cat_sau_1_lan"], 1,
                         "sau MỘT lượt khôi phục phải có ĐÚNG 1 bản cất")
        self.assertGreaterEqual(
            self.kq["so_ban_cat_sau_3_lan"], 3,
            "ba lượt khôi phục chỉ để lại %s bản cất — lượt sau ĐÈ IM LẶNG lượt trước. Sửa "
            "`app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
            % self.kq["so_ban_cat_sau_3_lan"])
        self.assertGreaterEqual(
            self.kq["so_ban_cat_giu_du_lieu_goc"], 1,
            "KHÔNG bản cất nào giữ được dữ liệu vừa bị đè — không có đường lùi thật")
        # ĐỐI CHỨNG ĐƯỜNG: chính bản cất của lượt ĐẦU phải mở được và khớp dữ liệu lúc chụp.
        self.assertEqual(self.kq["noi_dung_ban_cat"]["integrity"], "ok",
                         "bản cất không mở được")


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

    def test_f2_BAT_BIEN_khoi_phuc_PHAI_TU_CHOI_ban_schema_thap_hon(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — khôi phục bản schema THẤP HƠN phải TỪ CHỐI
        và phải NÓI RA hai phiên bản, KHÔNG được để schema tụt im lặng.

        Ca này PIN: TỤT SCHEMA là hỏng. Đo 16/10/2026 trên mã chưa vá: v6 đè lên v9 với mã thoát
        **0**, thông báo duy nhất là "Đã khôi phục từ …". CSDL còn **20 bảng** thay vì 51 —
        **31 bảng** và toàn bộ dữ liệu của chúng biến mất, tổng tiền rơi từ 34.336.000 xuống
        1.298.000 đồng. Sau đó hệ VẪN CHẠY (rc 0) trên schema cũ.

        KHÔNG hạ cổng xuống cho vừa: `v6` là một bản sao lưu HỢP LỆ và migrate dựng lại được nó.
        Một lời từ chối ở đây là từ chối vì PHIÊN BẢN, không phải vì tệp hỏng.
        """
        self.assertNotEqual(self.kq["rc_khoi_phuc"], 0,
                            "`khoi_phuc()` NHẬN bản schema v%s đè lên v%s với mã thoát 0 — schema "
                            "tụt im lặng: %s bảng → %s bảng, tổng tiền %s → %s. Sửa "
                            "`app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
                            % (self.kq["phien_ban_v6"], self.kq["phien_ban_v9_truoc"],
                               self.kq["so_bang_v9_truoc"], self.kq["chup_sau"]["so_bang"],
                               self.kq["tong_tien_v9_truoc"], self.kq["tong_tien_v6"]))
        self.assertEqual(self.kq["phien_ban_sau_khoi_phuc"], self.kq["phien_ban_v9_truoc"],
                         "CSDL đích đã TỤT phiên bản: v%s → v%s"
                         % (self.kq["phien_ban_v9_truoc"], self.kq["phien_ban_sau_khoi_phuc"]))
        self.assertEqual(self.kq["chup_sau"]["so_bang"], self.kq["so_bang_v9_truoc"],
                         "số bảng của CSDL đích đã đổi")
        self.assertEqual(self.kq["chup_sau"]["tong_tien"], self.kq["tong_tien_v9_truoc"],
                         "tổng tiền của CSDL đích đã đổi")
        # Vế (b): lời từ chối phải NÓI RA hai phiên bản. Thông báo `SystemExit` đi ra STDERR.
        tb = (self.kq.get("err_khoi_phuc") or "") + (self.kq.get("out_khoi_phuc") or "")
        self.assertTrue(tb.strip(), "bị từ chối nhưng KHÔNG in thông báo nào")
        self.assertIn(str(self.kq["phien_ban_v6"]), tb,
                      "thông báo từ chối không nêu phiên bản bản sao lưu (v%s): %s"
                      % (self.kq["phien_ban_v6"], tb[-300:]))

    def test_f3_doi_chung_duong_ban_sao_luu_v6_KHONG_phai_tep_hong(self):
        """ĐỐI CHỨNG ĐƯỜNG cho F2 — bản v6 bị từ chối phải là một CSDL LÀNH.

        Thiếu vế này thì "bị từ chối" có thể chỉ là hệ quả của một tệp v6 hỏng, và kết luận rút
        ra sẽ SAI: "từ chối vì tệp hỏng" khác hẳn "từ chối vì tụt phiên bản". Hai câu đó chỉ
        phân biệt được bằng chính số đo này.
        """
        self.assertEqual(self.kq["integrity_ban_sao_luu_v6"], "ok",
                         "bản sao lưu v6 KHÔNG qua integrity_check — đối chứng đường hỏng")
        self.assertGreaterEqual(self.kq["so_bang_ban_sao_luu_v6"] or 0, 15,
                                "bản sao lưu v6 quá ít bảng — nhìn nhầm tệp")
        self.assertEqual(self.kq["rc_dung_v6"], 0, "dựng v6 hỏng: " + self.kq["loi_v6"][-200:])

    def test_f4_chot_chong_phep_do_RONG_tut_schema_phai_that(self):
        """Chốt chống phép đo RỖNG: v9 và v6 phải THẬT SỰ khác nhau về bảng và về tiền.

        Không có ca này thì một kịch bản "dựng v6 hỏng, v6 hoá ra bằng v9" vẫn cho ra mọi dòng
        ở F2/F3 màu xanh, và cả lớp F không đo gì.
        """
        self.assertGreater(self.kq["so_bang_v9_truoc"], self.kq["so_bang_v6"],
                           "v9 không nhiều bảng hơn v6 — kịch bản tụt schema không chạy")
        self.assertGreater(self.kq["tong_tien_v9_truoc"], self.kq["tong_tien_v6"],
                           "v9 không nhiều tiền hơn v6 — kịch bản không chạy")
        self.assertGreater(self.kq["tong_tien_v6"], 0, "v6 rỗng tiền — phép so TIỀN vô nghĩa")
        self.assertEqual(self.kq["rc_ghi_tren_v6"], 0,
                         "hệ không chạy được trên v6 — không đo được vế 'hệ vẫn chạy'")


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

    def test_g2_BAT_BIEN_khoi_phuc_PHAI_TU_CHOI_tep_khong_phai_SQLite(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — phải có phép kiểm "tệp này có phải SQLite
        không" TRƯỚC khi đụng CSDL đang chạy.

        Ca này PIN: không kiểm định dạng tệp là hỏng. Đo 16/10/2026: một tệp mang magic `PGDMP`
        được `khoi_phuc()` NHẬN (rc 0), và CSDL đang chạy trở thành một khối 65.544 byte mà
        SQLite trả `file is not a database`. Không một lời cảnh báo. Vế ĐỐI CHỨNG ĐƯỜNG nằm
        ngay trên: cùng lệnh đó, một bản sao lưu SQLite THẬT thì khôi phục ĐẠT.
        """
        self.assertNotEqual(
            self.kq["rc_khoi_phuc_nham"], 0,
            "`khoi_phuc()` NHẬN một tệp KHÔNG PHẢI SQLite với mã thoát 0 và làm chết CSDL đang "
            "chạy (%s byte, %s). Sửa `app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
            % (self.kq["so_byte_csdl_sau"], self.kq["csdl_sau_khi_nham"].get("loi")))
        self.assertEqual(self.kq["csdl_sau_khi_nham"].get("loi"), None,
                         "CSDL đích KHÔNG ĐỌC ĐƯỢC sau lượt nạp nhầm: %s"
                         % (self.kq["csdl_sau_khi_nham"],))
        self.assertEqual(self.kq["so_byte_csdl_sau"], self.kq["so_byte_csdl_truoc"],
                         "số byte CSDL đích đã đổi — nó đã bị ghi đè")
        self.assertTrue(self.kq["doi_chung_duong_dat"],
                        "ĐỐI CHỨNG ĐƯỜNG HỎNG: bản sao lưu SQLite THẬT mà khôi phục cũng lệch: %s"
                        % (self.kq["lech_duong_dung"],))


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

    def test_h3_khoa_khong_di_kem_va_he_PHAI_TU_CHOI_duoc(self):
        """KHOẢNG TRỐNG + ĐIỂM TỐT, khai cả hai. **Ca này KHÔNG đổi ở G21, và vì sao thì rõ:**

        KHOẢNG TRỐNG (còn nguyên): `khoi_phuc()` báo thành công trong khi bản khôi phục KHÔNG
        dùng được cho lời gọi hãng nào — khóa mã hoá credentials nằm ở tệp KHÁC
        (`cau_hinh.DUONG_DAN_KHOA`) và `sao_luu()` chỉ sao lưu `hub.db`. Người trực phải tự biết
        rằng còn một quy trình thứ hai (`app/sao_luu_khoa.py`, `trien_khai/sao_luu_ngoai/`).

        Vì sao KHÔNG gộp nó vào bất biến fail-closed của G21: "khôi phục CSDL" và "khôi phục
        khóa" là HAI quy trình có ranh giới rõ ràng, và bản vá G21 (`ban_va.py`) cố ý không mở
        rộng phạm vi sang tệp khóa — mở rộng là một quyết định sản phẩm, không phải một bản vá.
        Nói ra ở đây để nó không bị đọc thành "đã đóng".

        ĐIỂM TỐT (đo được, không suy đoán): hệ KHÔNG tự sinh khóa mới rồi giải mã ra rác. Nó NÉM
        `LoiKhoa` với thông báo nói thẳng phải làm gì: "Khôi phục khóa từ bản sao lưu, đừng sinh
        khóa mới." Đây là kiểu hỏng ỒN ÀO — đúng loại hỏng nên có. Nếu vế này đỏ, tức hệ đã bắt
        đầu im lặng, đó là ĐI LÙI.
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

    def test_k3_BAT_BIEN_sao_luu_PHAI_TU_CHOI_khi_kho_la_PostgreSQL(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — P-G15-02: `sao_luu()` KHÔNG được báo thành
        công với một ĐƯỜNG LÙI GIẢ.

        Ca này PIN: một bản sao lưu không chứa dữ liệu đang chạy là hỏng, dù nó "trông hợp lệ".
        Đo 16/10/2026 trên cụm riêng: `hub.db` không tồn tại (đúng trạng thái máy chủ đã chuyển
        kho sang PostgreSQL) → `sao_luu()` **KHÔNG ném lỗi**, mã thoát 0, sinh ra một tệp
        **4.096 byte, 0 BẢNG**, `PRAGMA integrity_check` trả `"ok"` — trong khi PostgreSQL đang
        giữ 6 đơn + 6 bút toán + 9.324.000 đồng. KHÔNG một byte nào của số đó nằm trong "bản sao
        lưu". Đây là dạng hỏng tệ nhất: không ném lỗi, không làm đúng, mà IM LẶNG.

        Chốt `so_byte <= 0` của `sao_luu()` KHÔNG cứu được: 4.096 byte > 0.
        """
        d1 = self.kq["do1_hub_db_khong_ton_tai"]
        self.assertNotEqual(
            d1["rc"], 0,
            "kho là PostgreSQL (không có hub.db) mà `sao_luu()` thoát 0 và trả một tệp %s byte / "
            "%s BẢNG trong khi PostgreSQL giữ %s dòng và %s đồng — ĐƯỜNG LÙI GIẢ, im lặng. Sửa "
            "`app/migrate.py` (tệp của AG-00), KHÔNG nới ca này."
            % (d1.get("co_ban_sao"), d1.get("so_bang"),
               self.kq["pg_truoc"]["bang"]["don_hang"]["dong"], self.kq["pg_truoc"]["tong_tien"]))

    def test_k4_BAT_BIEN_hub_db_CU_khong_duoc_coi_la_du_lieu_dang_chay(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — dạng hỏng thứ hai, khó thấy hơn dạng rỗng.

        Ca này PIN: một `hub.db` còn sót từ trước (dữ liệu SQLite CŨ, không còn là dữ liệu đang
        chạy) KHÔNG được coi là kho đang chạy. Đo 16/10/2026: `sao_luu()` trả một bản sao **trông
        hoàn toàn hợp lệ** — 51 bảng, 34.336.000 đồng, băm khớp đúng tệp SQLite đó. Người trực
        thấy một tệp sao lưu "đầy đủ" và tin nó. Nhưng nó không chứa một dòng nào của dữ liệu
        PostgreSQL đang chạy.

        ĐÂY LÀ KHOẢNG TRỐNG **CÒN HỞ** — bản vá G21 (`ban_va.py`) KHÔNG đóng được nó, và nói
        thẳng vì sao: hệ KHÔNG có khái niệm "kho đang chạy là kho nào", nên không có gì để đối
        chiếu; bịa một phép đoán (mtime, kích thước) là vi phạm nguyên tắc "không đoán". Muốn
        đóng thì cần một QUYẾT ĐỊNH SẢN PHẨM: một cờ cấu hình nói rõ kho đang chạy. Xem
        `docs/G21_BACKUP_RESTORE.md` §CÒN HỞ.
        """
        d2 = self.kq["do2_hub_db_co_du_lieu_sqlite_khac"]
        hong = (d2["rc"] == 0 and d2["bam_ban_sao_khop_sqlite_goc"]
                and d2["ban_sao_tong_tien"] != self.kq["pg_truoc"]["tong_tien"])
        self.assertFalse(
            hong,
            "`sao_luu()` trả một bản sao TRÔNG HỢP LỆ (%s bảng, %s đồng) mà KHÔNG chứa một dòng "
            "nào của dữ liệu đang chạy (%s đồng ở PostgreSQL) — CÒN HỞ, cần cờ cấu hình 'kho "
            "đang chạy'. Xem docs/G21_BACKUP_RESTORE.md §CÒN HỞ."
            % (d2["ban_sao_so_bang"], d2["ban_sao_tong_tien"], self.kq["pg_truoc"]["tong_tien"]))

    def test_k5_BAT_BIEN_khoi_phuc_PHAI_TU_CHOI_ban_pg_dump_that(self):
        """BẤT BIẾN FAIL-CLOSED (AG-02 viết lại) — một bản `pg_dump -Fc` THẬT (không phải tệp
        giả) đưa cho `khoi_phuc()`.

        Ca này PIN: cùng một lỗi với `G2`, đo trên tệp THẬT thay vì tệp giả — để không ai nói
        "chỉ là kịch bản dựng tay". Đo 16/10/2026: 124.700 byte, `pg_dump` trả mã thoát 0,
        `khoi_phuc()` NHẬN với mã thoát 0, CSDL SQLite đang chạy biến thành chính tệp dump đó.
        """
        d3 = self.kq["do3_khoi_phuc_tu_pg_dump"]
        self.assertEqual(self.kq["pg_dump"]["rc"], 0, "pg_dump hỏng")
        self.assertGreater(self.kq["pg_dump"]["co_byte"], 0)
        self.assertNotEqual(d3["rc_khoi_phuc"], 0,
                            "`khoi_phuc()` NHẬN một bản `pg_dump -Fc` THẬT với mã thoát 0 và làm "
                            "chết CSDL SQLite đang chạy (%s). Sửa `app/migrate.py` (tệp của "
                            "AG-00), KHÔNG nới ca này." % (d3.get("csdl_sau_loi"),))

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
