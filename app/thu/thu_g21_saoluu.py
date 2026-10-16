#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — BỘ THỬ: SAO LƯU / KHÔI PHỤC PHẢI **FAIL-CLOSED**.

Chạy:  python3 app/thu/thu_g21_saoluu.py
       `app/thu/chay_tat_ca.sh` tự dò tệp này (`app/thu/thu_*.py`) nên nó vào lượt hồi quy chung.

================= VÌ SAO CÓ TỆP NÀY, KHI ĐÃ CÓ `thu_g20_saoluu.py` =================
`thu_g20_saoluu.py` (AG-04, G20) đã đo VÒNG TRÒN LÀNH: 41 ca, mã thoát 0. Nhưng nó **PIN HÀNH
VI CŨ**: tám ca mang nhãn `ĐỘC HẠI ĐÃ BIẾT` khẳng định ĐÚNG cái sai — ví dụ
`assertEqual(khoi_phuc_NHAN_tat_ca, 5)` nghĩa là "5/5 tệp hỏng PHẢI được nhận thì ca này mới
xanh". Nên bộ 41 ca XANH trong khi nghiệm thu G20 kết luận **FAILED**: bộ thử đang canh một
hành vi fail-open, không canh một bất biến.

Tệp này KHÔNG lặp lại việc đo. Nó hỏi đúng MỘT câu, cho MỌI kịch bản hỏng:

    Khi sao lưu hoặc khôi phục HỎNG, hệ có DỪNG LẠI VÀ BÁO RÕ (fail-closed) không,
    hay nó IM LẶNG ĐI TIẾP và để lại một TRẠNG THÁI NỬA VỜI?

Câu trả lời đến từ `trien_khai/g20-saoluu/fail_closed.py` — nơi giữ số đo thô. Tệp này chỉ
KHẲNG ĐỊNH trên số đo đó, và mỗi khẳng định nói ra nó đòi gì.

================= BA LỚP, VÀ LỚP THỨ BA LÀ LỚP QUAN TRỌNG NHẤT =================
  A. `A_FailClosed`   — mỗi kịch bản hỏng phải FAIL_CLOSED. ĐỎ ở đây là LỖI SẢN PHẨM.
  B. `B_DoiChungDuong`— đường LÀNH phải ĐẠT, và phép đo phải CHỨNG MINH nó LÀM ĐỎ ĐƯỢC.
  C. `C_TuKiemBoDo`   — TIÊM lỗi fail-open vào chính bản vá và đòi bộ đo bắt được.
Không có lớp C thì hai lớp trên không chứng minh gì: một bộ đo luôn trả ĐỎ, hoặc một bộ đo
đọc nhầm `migrate.py`, đều cho ra cùng một bảng "FAIL_OPEN" ở lớp A.

================= VÌ SAO LỚP A SẼ ĐỎ, VÀ ĐÓ LÀ KẾT QUẢ ĐÚNG =================
Đo 16/10/2026 trên `integration/g20 @ a3400a8`: **9/10 kịch bản FAIL_OPEN**. Sửa lỗi nằm ở
`app/migrate.py` — TỆP CỦA AG-00, ngoài vùng được ghi của làn này. Bản vá ĐÃ ĐƯỢC VIẾT VÀ ĐO
(`trien_khai/g20-saoluu/ban_va.py`): chạy cùng bộ đo trên bản vá cho **9/10 FAIL_CLOSED**, và
khoảng trống còn lại được nêu tên (xem `docs/G21_BACKUP_RESTORE.md`).

Nên lớp A ĐỎ là TÌNH TRẠNG ĐÚNG của cây này, không phải bộ thử hỏng. **KHÔNG** nới điều kiện
cho nó xanh: nới ra là quay lại đúng thứ đã làm G20 nghiệm thu FAILED.

================= MÔI TRƯỜNG =================
Mọi lượt đo chạy trong thư mục TẠM; `kich_ban.chot_an_toan()` TỪ CHỐI vùng dữ liệu thật.
KHÔNG gọi mạng (lớp HTTP chỉ chạm `127.0.0.1` cổng OS cấp). Cụm PostgreSQL là cụm RIÊNG,
TỪ CHỐI cổng 5432. `sao_luu()`/`khoi_phuc()` được ĐỌC, không được sửa.
"""
import os
import shutil
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAY_G20 = os.path.join(GOC, "trien_khai", "g20-saoluu")
sys.path.insert(0, DAY_G20)

import fail_closed as fc     # noqa: E402
import kich_ban              # noqa: E402
import ban_va                # noqa: E402

# Nhãn cho người đọc, và kịch bản nào PHẢI bắt được lỗi tiêm nào. Khai MỘT chỗ.
TIEM = {
    "D1": ("bỏ tệp tạm, chép THẲNG lên CSDL đang chạy", ("S6b",)),
    "D2": ("tên bản cất đặt theo GIÂY, cho phép đè", ("S4",)),
    "D3": ("bỏ chốt TỤT SCHEMA", ("S5",)),
    "D4": ("bỏ mọi phép kiểm chứng bản sao lưu", ("S3", "S7")),
}


# ============================================================================
# A — MỌI KỊCH BẢN HỎNG PHẢI FAIL-CLOSED   (ĐỎ = LỖI SẢN PHẨM, không phải lỗi bộ thử)
# ============================================================================
class A_FailClosed(unittest.TestCase):
    """Số đo thô do `fail_closed.chay_tat_ca()`. Không gọi lại lần hai cho mỗi ca."""

    kq = None
    loi = None

    @classmethod
    def setUpClass(cls):
        cls.kq = fc.chay_tat_ca()
        cls.loi = {}
        for ma in cls.kq["thu_tu"]:
            b = cls.kq["ban_ghi"][ma]
            cls.loi[ma] = fc.phan_quyet(b)
            print("\n        [%s] %-52s rc=%-3s %s"
                  % (ma, b["ten"][:52], b["rc"], fc.muc(b)))
            print("             (b) %s | traceback trần=%s"
                  % ((b["dong_bao_hong"] or "(không có)")[:120], b["la_traceback_tho"]))
        print("\n        app/ đang đo: %s" % cls.kq["app"])

    def _doi(self, ma):
        self.assertIn(ma, self.kq["ban_ghi"], "kịch bản %s KHÔNG CHẠY — bộ đo thiếu một vế" % ma)
        b = self.kq["ban_ghi"][ma]
        return b, self.loi[ma]

    def test_a0_bay_kich_ban_deu_chay(self):
        """Chốt chống phép đo RỖNG: thiếu một kịch bản thì mọi dòng ĐẠT ở dưới là vô nghĩa."""
        self.assertEqual(sorted(self.kq["thu_tu"]), sorted(fc.THU_TU),
                         "không chạy đủ 10 kịch bản; bỏ qua: %s" % (self.kq["bo_qua"],))

    def test_a1_sao_luu_bi_cat_giua_duong(self):
        """S1 — tệp dở LÀM KHÁC BẢN GỐC phải bị `khoi_phuc()` TỪ CHỐI; lượt cắt vì hết chỗ ghi
        phải có mã thoát khác 0. Ca này PIN: nhận một tệp dở là lỗi, không phải tính năng."""
        b, loi = self._doi("S1")
        self.assertEqual(loi, [], "S1 KHÔNG fail-closed: %s" % "; ".join(loi))
        self.assertGreaterEqual(b["bang_chung"]["so_cach_tep_de_that_su_cut"], 3,
                                "phép đo rỗng: không tạo được tệp dở thật nào")

    def test_a2_tep_sao_luu_bi_sua_mot_byte(self):
        """S2 — bản sửa LÀM KHÁC BẢN GỐC phải bị TỪ CHỐI. Ca này PIN: một chốt kiểm chứng chỉ
        có răng khi nó bắt được thay đổi DỮ LIỆU, không phải khi nó đếm số tệp bị nhận."""
        b, loi = self._doi("S2")
        self.assertEqual(loi, [], "S2 KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a3_tep_sao_luu_rong_0_byte(self):
        """S3 — tệp 0 byte. Ca này PIN: `integrity_check` trả **"ok"** cho tệp 0 byte (nó là
        một CSDL rỗng HỢP LỆ), nên bất biến ĐÚNG phải là SỐ BẢNG, không phải integrity."""
        b, loi = self._doi("S3")
        self.assertEqual(loi, [], "S3 KHÔNG fail-closed: %s" % "; ".join(loi))
        self.assertEqual(b["bang_chung"]["integrity_tep_rong"], "ok",
                         "chốt chống MỤC: tệp 0 byte mà integrity_check khác 'ok' — bất biến "
                         "của ca này đã đổi, đọc lại kết luận")
        self.assertEqual(b["bang_chung"]["so_bang_tep_rong"], 0)

    def test_a4_khoi_phuc_de_len_csdl_dang_chay(self):
        """S4 — khôi phục ĐÈ lên CSDL đã có dữ liệu. Ca này PIN: bất biến KHÔNG phải "đích
        không đổi" (đè thành công thì đích PHẢI đổi) mà là **dữ liệu trước khi đè còn cứu
        được**, và ba lượt trong cùng một giây không được xoá nhau."""
        b, loi = self._doi("S4")
        self.assertEqual(loi, [], "S4 KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a5_khoi_phuc_ban_schema_thap_hon(self):
        """S5 — v6 đè lên v9. Ca này PIN: TỤT SCHEMA là hỏng, phải TỪ CHỐI và phải nói ra hai
        phiên bản — không được để hệ chạy tiếp trên schema cũ trong im lặng."""
        b, loi = self._doi("S5")
        self.assertEqual(loi, [], "S5 KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a6_het_dia_khi_sao_luu(self):
        """S6a — hết đĩa giữa lúc `sao_luu()`. Ca này PIN: mã thoát khác 0 LÀ CHƯA ĐỦ; không
        được để lại một tệp dở MANG TÊN BẢN SAO LƯU mà người sau đem đi khôi phục."""
        b, loi = self._doi("S6a")
        self.assertEqual(loi, [], "S6a KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a7_het_dia_khi_khoi_phuc(self):
        """S6b — hết đĩa giữa lúc `khoi_phuc()` đang chép lên CSDL đang chạy. CA NẶNG NHẤT.

        Ca này PIN vế (c): CSDL ĐÍCH không được để lại nửa vời. Đo được trên mã chưa vá: CSDL
        đích còn 280.576 byte với `DatabaseError: database disk image is malformed` và MẤT
        SẠCH 20 bảng — mã thoát 1 và một traceback KHÔNG cứu được gì.
        """
        b, loi = self._doi("S6b")
        self.assertTrue(b["bang_chung"]["tien_quyet_dat"],
                        "PHÉP ĐO KHÔNG DỰNG ĐƯỢC: giới hạn ghi không rơi vào lần chép thứ hai "
                        "(%s)" % b["bang_chung"]["vi_tri_gioi_han"])
        self.assertEqual(loi, [], "S6b KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a8_khoi_phuc_nham_tep_khong_phai_sqlite(self):
        """S7 — nạp nhầm một tệp `pg_dump` vào `khoi_phuc()`. Ca này PIN: phải có phép kiểm
        "tệp này có phải SQLite không" TRƯỚC khi đụng CSDL đang chạy."""
        b, loi = self._doi("S7")
        self.assertEqual(loi, [], "S7 KHÔNG fail-closed: %s" % "; ".join(loi))

    def test_a9_postgresql_sao_luu_khong_duoc_bao_thanh_cong(self):
        """S8 (P-G15-02) — kho là PostgreSQL. Ca này PIN: `sao_luu()` KHÔNG được thoát 0 với
        một bản sao không chứa một dòng nào của dữ liệu đang chạy."""
        b, loi = self._doi("S8")
        self.assertEqual(loi, [], "S8 KHÔNG fail-closed: %s" % "; ".join(loi))


# ============================================================================
# B — ĐỐI CHỨNG ĐƯỜNG: ĐƯỜNG LÀNH PHẢI ĐẠT
# ============================================================================
class B_DoiChungDuong(unittest.TestCase):
    """Nếu đường LÀNH cũng hỏng thì mọi kết luận "hỏng ở đường X" ở lớp A đều vô nghĩa."""

    kq = None

    @classmethod
    def setUpClass(cls):
        cls.kq = fc.chay_tat_ca(chi=("DC",))

    def test_b1_sao_luu_roi_khoi_phuc_nguoc_lai_chinh_csdl_goc_y_nguyen(self):
        """sao lưu → ghi thêm dữ liệu → khôi phục về chính CSDL gốc → phải Y NGUYÊN TỪNG BẢNG.

        Đối chiếu cả SỐ DÒNG lẫn TỔNG TIỀN từng cột tiền từng bảng, cộng `bam_toan_kho`.
        """
        b = self.kq["ban_ghi"]["DC"]
        self.assertEqual(fc.phan_quyet(b), [], "ĐỐI CHỨNG ĐƯỜNG HỎNG: %s"
                         % "; ".join(fc.phan_quyet(b)))
        self.assertEqual(b["rc"], 0)
        self.assertEqual(b["bang_chung"]["so_lech_sau_khoi_phuc"], 0)
        self.assertEqual(b["bang_chung"]["tenant_sau_backup_con_lai"], 0,
                         "khôi phục không lùi được thời gian — nó không khôi phục gì cả")

    def test_b2_phep_so_LAM_DO_DUOC(self):
        """Chốt chống phép so CHẾT: ghi thêm tenant + đơn 999.000đ mà phép so vẫn im thì mọi
        dòng "khớp" ở trên là rỗng."""
        bc = self.kq["ban_ghi"]["DC"]["bang_chung"]
        self.assertGreater(bc["so_lech_giua"], 0,
                           "ghi thêm dữ liệu mà phép so KHÔNG thấy lệch")
        self.assertTrue(any("TIỀN" in x or "DÒNG" in x for x in bc["vi_du_lech_giua"]),
                        "phép so thấy lệch nhưng không ở trục DÒNG/TIỀN: %s"
                        % (bc["vi_du_lech_giua"],))

    def test_b3_phep_do_khong_rong(self):
        """Chốt chống phép đo RỖNG: CSDL gốc phải CÓ dữ liệu thì "khôi phục khớp" mới có nghĩa."""
        bc = self.kq["ban_ghi"]["DC"]["bang_chung"]
        self.assertGreaterEqual(bc["so_bang_goc"], 45, "quá ít bảng — nhìn nhầm CSDL")
        self.assertGreater(bc["tong_tien_goc"], 0, "tổng tiền bản gốc bằng 0")


# ============================================================================
# C — TỰ KIỂM BỘ ĐO: TIÊM LỖI FAIL-OPEN, BỘ ĐO PHẢI BẮT ĐƯỢC
# ============================================================================
class C_TuKiemBoDo(unittest.TestCase):
    """Không có lớp này thì lớp A không chứng minh gì.

    Hai vế, và vế thứ hai mới là vế nặng:
      C1 (TIÊM TỔNG HỢP) — dựng bản ghi ĐÃ BIẾT là fail-open và ĐÃ BIẾT là fail-closed, đòi
           `phan_quyet()` phán đúng. Rẻ, tất định, chạy mọi lượt.
      C2 (TIÊM THẬT)     — gỡ ĐÚNG MỘT chốt khỏi bản vá, chạy lại CHÍNH bộ đo trên đó, và đòi
           kịch bản tương ứng bắt được. Đây là vế chứng minh bộ đo PHÂN BIỆT ĐƯỢC, chứ không
           phải một cái ĐỎ cứng đơ bất kể đầu vào.

    `C2` chạy trong tiến trình con: nó phải nạp một `migrate.py` KHÁC, và `cau_hinh` đọc
    `VIP_HUB_DATA`/đường dẫn MỘT LẦN lúc nạp mô-đun — trong cùng tiến trình thì lượt đo thứ
    hai vẫn dùng đường dẫn của lượt đầu, và mọi phép so sau đó chỉ đang so một CSDL với chính nó.
    """

    nen = None
    bien_the = None

    @classmethod
    def setUpClass(cls):
        cls.nen = kich_ban.chot_an_toan(tempfile.mkdtemp(prefix="g21-tukiem-"))
        cls.bien_the = ban_va.dung_bien_the(cls.nen)
        print("\n        biến thể: %s" % sorted(cls.bien_the))

    @classmethod
    def tearDownClass(cls):
        if cls.nen:
            shutil.rmtree(cls.nen, ignore_errors=True)

    # ---------------------------------------------------------------- C1
    # `bang_chung` TỐI THIỂU để `phan_quyet()` trả [] cho từng mã. Khai ra ở đây để bản ghi
    # "đã ĐẠT" trong lượt tiêm là bản ghi THẬT SỰ ĐẠT, chứ không phải một dict rỗng mà phán
    # quyết tố cáo vì thiếu số đo — hai thứ khác hẳn nhau, và lẫn chúng là tự lừa mình.
    BC_DAT = {
        "S1": {"cac_cach_cat": [{"cach": "a-het-cho-ghi", "rc_luot_cat": 1}],
               "so_cach_tep_de_that_su_cut": 5, "cat_hong_that": [], "doi_chung_duong_dat": True},
        "S2": {"sua_hong_that": [], "so_lan_sua": 5, "doi_chung_duong_dat": True},
        "S3": {"khoi_phuc_NHAN_tep_rong": False, "integrity_tep_rong": "ok",
               "so_bang_tep_rong": 0},
        "S4": {"so_ban_cat_giu_du_lieu_goc": 3, "so_ban_cat_sau_1_lan": 1,
               "so_ban_cat_sau_3_lan": 3, "rc_kp1": 0, "rc_kp2": 0, "rc_kp3": 0},
        "S5": {"phien_ban_sau_khoi_phuc": 9, "phien_ban_v9_truoc": 9, "rc_ghi_tren_v6": 0},
        "S6a": {"tep_moi_dung_duoc": [], "so_tep_moi_de_lai": 0},
        "S6b": {},
        "S7": {"khoi_phuc_NHAN_tep_la": False, "loi_csdl_sau_khi_nham": None},
        "S8": {"do1_hub_db_khong_ton_tai": {"rc": 1, "so_bang": 0}, "pg_truoc": {"tong_tien": 1}},
        "DC": {"so_lech_sau_khoi_phuc": 0, "so_lech_giua": 3, "tenant_sau_backup_con_lai": 0},
    }

    def _ban_ghi(self, ma, **thay):
        """Một bản ghi TỐI THIỂU, đã ĐẠT, để tiêm từng lỗi vào một chỗ.

        `DC` là ĐỐI CHỨNG ĐƯỜNG nên mã thoát ĐẠT của nó là **0**; mọi mã còn lại là trường hợp
        HỎNG nên mã thoát ĐẠT là **khác 0**. Lấy một giá trị chung cho cả hai nhóm là làm bản ghi
        "đã ĐẠT" mâu thuẫn với chính bất biến của nó — và lượt tự kiểm sẽ tố cáo oan.
        """
        bg = {"ma": ma, "ten": "tiêm", "bat_buoc": "tiêm",
              "ap_dung_mau": ma in fc.AP_DUNG_MAU,
              "rc": 0 if ma == "DC" else 1,
              "thong_bao": "", "dong_bao_hong": "TỪ CHỐI: tệp hỏng",
              "co_dong_bao_hong": True, "la_traceback_tho": False,
              "c_dat": True, "c_lech": [], "csdl_dich_truoc": {}, "csdl_dich_sau": {},
              "bang_chung": dict(self.BC_DAT.get(ma, {}))}
        bg.update(thay)
        return bg

    def test_c1_tiem_tong_hop_moi_kich_ban_phai_bat_duoc_FAIL_OPEN(self):
        """Với MỌI mã kịch bản: một bản ghi cố tình fail-open PHẢI bị `phan_quyet()` tố cáo.

        **Vì sao vế (a) và (b) chỉ chạy trên `fc.AP_DUNG_MAU`:** chỉ nhóm đó có bất biến "mã
        thoát khác 0 + phải có thông báo" nằm ở trường `rc`/`co_dong_bao_hong`. Năm mã còn lại
        mang mã thoát ở CHỖ KHÁC, và ĐÚNG NHƯ THẾ mới đúng:
          * `S1` — mã thoát của TỪNG lượt cắt (`cac_cach_cat[i].rc_luot_cat`);
          * `S2` — cái đáng tố cáo không phải mã thoát mà là "NHẬN bản sửa có hại";
          * `S4` — bất biến là "bản cất giữ được dữ liệu"; mã thoát ĐẠT là **0**;
          * `S8` — mã thoát nằm ở `do1.rc` / `do3.khoi_phuc_NHAN`;
          * `DC` — ĐỐI CHỨNG ĐƯỜNG, mã thoát ĐẠT là **0**.
        Tiêm `rc = 0` vào `DC` là tiêm ĐÚNG thứ nó phải có, nên `phan_quyet` im lặng là ĐÚNG.
        Năm mã đó được canh ở `test_c2` bằng phép tiêm ĐÚNG TRƯỜNG của chúng.
        """
        # (a) mã thoát 0 — nhóm dùng khuôn chung
        for ma in sorted(fc.AP_DUNG_MAU):
            bg = self._ban_ghi(ma, rc=0)
            self.assertTrue(fc.phan_quyet(bg), "%s: mã thoát 0 mà KHÔNG bị tố cáo" % ma)
        # (b) im lặng
        for ma in sorted(fc.AP_DUNG_MAU):
            bg = self._ban_ghi(ma, co_dong_bao_hong=False, dong_bao_hong="")
            self.assertTrue(fc.phan_quyet(bg), "%s: im lặng mà KHÔNG bị tố cáo" % ma)
        # (c) CSDL đích nửa vời
        for ma in sorted(fc.AP_DUNG_MAU):
            bg = self._ban_ghi(ma, c_dat=False, c_lech=["CSDL đích không đọc được"])
            self.assertTrue(any("(c)" in x for x in fc.phan_quyet(bg)),
                            "%s: đích nửa vời mà KHÔNG bị tố cáo ở vế (c)" % ma)
        # ĐỐI CHỨNG DƯƠNG: chính bản ghi đó, để nguyên, phải QUA — cho MỌI mã.
        for ma in fc.THU_TU:
            self.assertEqual(fc.phan_quyet(self._ban_ghi(ma)), [],
                             "%s: một bản ghi ĐẠT mà vẫn bị tố cáo — phán quyết hỏng" % ma)

    def test_c2_tiem_tong_hop_bat_duoc_loi_O_NHANH_RIENG(self):
        """Mỗi nhánh bất biến riêng phải có răng: gỡ đúng MỘT trường ⇒ phải có lỗi ở nhánh đó.

        Mỗi mã được tiêm **ĐÚNG TRƯỜNG mang bất biến của nó** — kể cả `S1`, nơi mã thoát nằm ở
        `cac_cach_cat[i].rc_luot_cat` chứ không ở `rc`. Tiêm sai trường thì phép tiêm "trượt" mà
        vẫn xanh, và bộ đo trông có răng trong khi chỗ đó không ai canh.
        """
        ca = (
            # S1 — mã thoát của LƯỢT CẮT, không phải của `khoi_phuc()`
            ("S1", {"bang_chung": {"cac_cach_cat": [{"cach": "a-het-cho-ghi", "rc_luot_cat": 0}],
                                   "so_cach_tep_de_that_su_cut": 5, "cat_hong_that": [],
                                   "doi_chung_duong_dat": True}}),
            # S1 — tệp dở LÀM KHÁC BẢN GỐC bị nhận
            ("S1", {"bang_chung": {"cat_hong_that": ["a-het-cho-ghi: đích nhận tệp dở"],
                                   "so_cach_tep_de_that_su_cut": 5, "doi_chung_duong_dat": True,
                                   "cac_cach_cat": [{"cach": "a-het-cho-ghi", "rc_luot_cat": 1}]}}),
            ("S2", {"bang_chung": {"sua_hong_that": ["e-trang-dung: đích nhận bản sửa"],
                                   "so_lan_sua": 5, "doi_chung_duong_dat": True}}),
            ("S3", {"bang_chung": {"khoi_phuc_NHAN_tep_rong": True, "integrity_tep_rong": "ok",
                                   "so_bang_tep_rong": 0}}),
            ("S4", {"bang_chung": {"so_ban_cat_giu_du_lieu_goc": 0, "so_ban_cat_sau_1_lan": 1,
                                   "so_ban_cat_sau_3_lan": 1, "rc_kp1": 0, "rc_kp2": 0, "rc_kp3": 0}}),
            ("S5", {"bang_chung": {"phien_ban_sau_khoi_phuc": 6, "phien_ban_v9_truoc": 9,
                                   "so_bang_v9_truoc": 51, "so_bang_sau": 20,
                                   "tong_tien_v9_truoc": 34336000, "tong_tien_v6": 1298000,
                                   "rc_ghi_tren_v6": 0}}),
            ("S6a", {"bang_chung": {"tep_moi_dung_duoc": [], "so_tep_moi_de_lai": 1,
                                    "ten_tep_moi_de_lai": ["hub-truoc-migrate-x.db"]}}),
            ("S7", {"bang_chung": {"khoi_phuc_NHAN_tep_la": True,
                                   "loi_csdl_sau_khi_nham": "file is not a database"}}),
            ("S8", {"bang_chung": {"do1_hub_db_khong_ton_tai": {"rc": 0, "so_bang": 0,
                                                                "co_ban_sao": 4096,
                                                                "integrity": "ok"},
                                   "pg_truoc": {"tong_tien": 9324000,
                                                "bang": {"don_hang": {"dong": 6}}}}}),
            # DC — ĐỐI CHỨNG ĐƯỜNG: `rc` ĐẠT là 0, nên tiêm `rc = 1`
            ("DC", {"rc": 1, "bang_chung": {"so_lech_sau_khoi_phuc": 0, "so_lech_giua": 3,
                                            "tenant_sau_backup_con_lai": 0}}),
            ("DC", {"bang_chung": {"so_lech_sau_khoi_phuc": 4, "so_lech_giua": 3,
                                   "tenant_sau_backup_con_lai": 0}}),
        )
        for ma, thay in ca:
            bg = self._ban_ghi(ma, **thay)
            loi = fc.phan_quyet(bg)
            self.assertTrue(loi, "%s: tiêm lỗi ở nhánh riêng mà KHÔNG bị tố cáo: %s" % (ma, thay))
            self.assertNotIn("MÃ KỊCH BẢN KHÔNG NHẬN RA", " ".join(loi),
                             "%s: bị tố cáo vì THIẾU BẤT BIẾN, không phải vì lỗi tiêm" % ma)

    def test_c3_ma_kich_ban_la_thi_KHONG_duoc_tinh_la_DAT(self):
        """Chốt chống MỞ RỘNG ÂM THẦM: thêm mã kịch bản mới mà quên bất biến ⇒ phải ĐỎ."""
        bg = self._ban_ghi("S99")
        self.assertTrue(any("KHÔNG NHẬN RA" in x for x in fc.phan_quyet(bg)),
                        "mã kịch bản lạ được tính là ĐẠT — bất biến mới không ai canh")

    # ---------------------------------------------------------------- C2
    def _chay_bien_the(self, nhan, chi):
        """Chạy bộ đo trên một biến thể `app/`, trong TIẾN TRÌNH CON.

        Trả `{mã: {"muc": ..., "ly_do": [...]}}`. Trả cả LÝ DO chứ không chỉ màu, vì `S8` có
        một khoảng trống CÓ TÊN mà bản vá không đóng được — khẳng định "S8 phải xanh" sẽ là một
        khẳng định SAI, còn khẳng định "S8 chỉ còn ĐÚNG khoảng trống đã nêu tên" mới đo được.

        ====== `G21_APP_DIR` PHẢI ĐẶT **TRƯỚC** MỌI `import` — ĐO ĐƯỢC, ĐÃ TỪNG SAI ======
        `kich_ban` dựng các chuỗi `_MA_SAO_LUU`/`_MA_KHOI_PHUC`/`_MA_CAT` MỘT LẦN, lúc NẠP
        MÔ-ĐUN, từ `APP`. Gán `kich_ban.APP = ...` sau khi nạp KHÔNG dựng lại chúng. Lượt chạy
        đầu của ca này làm đúng thế và cho ra kết quả của **mã CHƯA VÁ** trên biến thể "đã vá" —
        tức một lượt tự kiểm GIẢ, đúng loại hỏng mà lớp này sinh ra để chặn. Nên biến môi trường
        được đặt ở dòng ĐẦU, trước cả `import fail_closed`.
        """
        ma = (
            "import os, sys, json\n"
            "os.environ['G21_APP_DIR'] = %r\n"
            "sys.path.insert(0, %r)\n"
            "import fail_closed as fc\n"
            "import kich_ban\n"
            "assert fc.APP == %r, 'fail_closed.APP = %%r' %% fc.APP\n"
            "assert kich_ban.APP == %r, 'kich_ban.APP = %%r' %% kich_ban.APP\n"
            "kq = fc.chay_tat_ca(chi=tuple(%r))\n"
            "print('__APP__' + fc.APP + '|' + kich_ban.APP + '|' + kq['app'])\n"
            "print('__JSON__' + json.dumps({m: {'muc': fc.muc(b), 'ly_do': fc.phan_quyet(b)}\n"
            "     for m, b in kq['ban_ghi'].items()}, ensure_ascii=False))\n"
            % (self.bien_the[nhan], DAY_G20, self.bien_the[nhan], self.bien_the[nhan], list(chi)))
        rc, out, err = kich_ban.chay_con(ma, self.nen, timeout=1800)
        self.assertEqual(rc, 0, "lượt đo trên biến thể %s hỏng (rc=%s): %s" % (nhan, rc, err[-600:]))
        # CHỐT CHỐNG LƯỢT TỰ KIỂM GIẢ: cả ba nơi giữ đường dẫn `app/` đều phải trỏ vào biến thể
        # đang đo. Thiếu chốt này thì một lượt tiêm "trượt" vẫn chạy trên mã GỐC và cho ra đúng
        # kết quả mà nó phải bắt — tức bộ đo trông có răng trong khi nó không hề được chạm tới.
        duong = [d for d in out.splitlines() if d.startswith("__APP__")]
        self.assertTrue(duong, "biến thể %s không khai đường dẫn app/ — không kiểm được" % nhan)
        for x in duong[0][len("__APP__"):].split("|"):
            self.assertEqual(x, self.bien_the[nhan],
                             "biến thể %s: một nơi vẫn trỏ vào %r — lượt tự kiểm sẽ đo NHẦM mã gốc"
                             % (nhan, x))
        for d in out.splitlines():
            if d.startswith("__JSON__"):
                import json
                return json.loads(d[len("__JSON__"):])
        self.fail("biến thể %s không trả JSON: %s" % (nhan, out[-400:]))

    def test_c4_ban_va_lam_moi_kich_ban_chuyen_sang_FAIL_CLOSED(self):
        """Chạy ĐÚNG bộ đo này trên `migrate.py` ĐÃ VÁ ⇒ mọi kịch bản phải FAIL_CLOSED.

        Đây là vế chứng minh các lỗi ở lớp A **SỬA ĐƯỢC**, không phải những cái ĐỎ vĩnh viễn.

        `S8` là NGOẠI LỆ ĐÃ KHAI TÊN. Đo được: bản vá đóng được `do1` (kho là PostgreSQL, không
        có `hub.db`) và `do3` (nạp nhầm `pg_dump`), nhưng KHÔNG đóng được `do2` — `hub.db` CŨ
        còn sót trong khi kho đang chạy là PostgreSQL. Lý do nằm ở SẢN PHẨM, không ở bản vá: hệ
        KHÔNG có khái niệm "kho đang chạy là kho nào" nên không có gì để đối chiếu, và bịa một
        phép đoán (mtime, kích thước) là vi phạm nguyên tắc "không đoán". Cần một QUYẾT ĐỊNH
        SẢN PHẨM. Nên ca này khẳng định ĐÚNG điều đo được: **S8 chỉ còn lại đúng khoảng trống
        đã nêu tên**, không lọt thêm lỗi nào khác.
        """
        kq = self._chay_bien_the("ban_va", fc.THU_TU)
        self.assertEqual(sorted(kq), sorted(fc.THU_TU), "bản vá không chạy đủ kịch bản")
        do = {m: v["ly_do"] for m, v in kq.items()
              if m != "S8" and v["muc"] != "FAIL_CLOSED"}
        self.assertEqual(do, {}, "bản vá CHƯA đóng được: %s" % do)
        self.assertEqual(kq["S8"]["muc"], "FAIL_OPEN",
                         "S8 đã xanh — khoảng trống đã đóng: gỡ mục §CÒN HỞ khỏi "
                         "docs/G21_BACKUP_RESTORE.md và cập nhật ca này")
        self.assertTrue(kq["S8"]["ly_do"], "S8 đỏ mà không nêu lý do")
        for x in kq["S8"]["ly_do"]:
            self.assertIn("CŨ còn sót", x,
                          "S8 còn lỗi KHÁC ngoài khoảng trống đã nêu tên: %s" % x)

    def test_c5_tiem_D1_bat_duoc_bo_tep_tam(self):
        """Gỡ chốt "ghi qua tệp tạm rồi `os.replace`" ⇒ `S6b` PHẢI bắt được."""
        self._kiem_tiem("D1")

    def test_c6_tiem_D2_bat_duoc_ten_ban_cat_de(self):
        """Gỡ chốt "tên bản cất không bao giờ đè" ⇒ `S4` PHẢI bắt được."""
        self._kiem_tiem("D2")

    def test_c7_tiem_D3_bat_duoc_chot_tut_schema(self):
        """Gỡ chốt "TỪ CHỐI khi bản sao lưu ở schema thấp hơn" ⇒ `S5` PHẢI bắt được."""
        self._kiem_tiem("D3")

    def test_c8_tiem_D4_bat_duoc_bo_kiem_chung(self):
        """Gỡ MỌI phép kiểm chứng bản sao lưu ⇒ `S3` và `S7` PHẢI bắt được."""
        self._kiem_tiem("D4")

    def _kiem_tiem(self, nhan):
        mo_ta, phai_bat = TIEM[nhan]
        kq = self._chay_bien_the("tiem_" + nhan.lower(), phai_bat)
        for ma in phai_bat:
            self.assertEqual(kq.get(ma, {}).get("muc"), "FAIL_OPEN",
                             "TIÊM LỖI %s (%s) KHÔNG BỊ BẮT: kịch bản %s vẫn báo %s ⇒ bộ đo "
                             "không có răng ở chỗ đó"
                             % (nhan, mo_ta, ma, kq.get(ma, {}).get("muc")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
