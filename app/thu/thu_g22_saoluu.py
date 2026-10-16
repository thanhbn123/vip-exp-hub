#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 / AG-02 — HAI BẤT BIẾN MỚI: KHO ĐANG CHẠY PHẢI KHAI · MỐC THỜI GIAN LÀ ĐẦU VÀO.

Chạy:  python3 app/thu/thu_g22_saoluu.py
       `app/thu/chay_tat_ca.sh` tự dò `app/thu/thu_*.py` nên tệp này vào lượt hồi quy chung.

================= VÌ SAO CÓ TỆP NÀY, KHI ĐÃ CÓ `thu_g20_*` VÀ `thu_g21_*` =================
`thu_g21_saoluu.py` hỏi: "khi sao lưu/khôi phục HỎNG, hệ có DỪNG LẠI VÀ BÁO RÕ không?". Tệp này
hỏi hai câu KHÁC, và cả hai đều là câu hỏi về ĐẦU VÀO của phép đo:

  (1) LÀM SAO BIẾT ĐƯỢC BẢN SAO LƯU NÀY CÓ CHỨA DỮ LIỆU ĐANG PHỤC VỤ?
      `sao_luu()` chỉ có nhánh SQLite. Khi dữ liệu đã sang PostgreSQL mà một `hub.db` CŨ còn sót
      lại, hàm cũ trả mã thoát **0** cùng một bản sao TRÔNG HỢP LỆ — 51 bảng, 34.336.000 đồng —
      mà không chứa một dòng nào của dữ liệu đang chạy. G21 gọi đó là khoảng hở `do2b` và để nó
      HỞ vì đóng nó là một quyết định sản phẩm. G22 CHỐT quyết định đó: **kho đang chạy phải được
      KHAI BÁO; chưa khai ⇒ TỪ CHỐI**. Không đoán từ mtime / kích thước / tên tệp, và KHÔNG có
      công tắc nào để nới.

  (2) CA ĐO "BA LƯỢT CÙNG MỘT GIÂY KHÔNG ĐƯỢC XOÁ NHAU" CÓ THẬT SỰ ĐO ĐƯỢC KHÔNG?
      Ca đó (`S4` trong bộ đo, `test_e3` trong bộ thử AG-04) đọc `datetime.now()` ở dưới sâu
      trong `migrate`, nên ba lượt có thể rơi vào hai-ba mốc khác nhau. Khi đó tên khác nhau,
      phép đếm ">= 3" XANH, mà ĐƯỜNG ĐÈ thì CHƯA HỀ được chạm tới — ca XANH trên một sản phẩm
      còn lỗi, và kết quả phụ thuộc TỐC ĐỘ MÁY (chạy riêng một kiểu, chạy chung một kiểu).
      G22 biến mốc thời gian thành **ĐẦU VÀO** (`sao_luu(luc=)` / `khoi_phuc(luc=)`), bộ đo
      truyền một mốc CỐ ĐỊNH, và bộ đo TỪ CHỐI kết luận nếu ba bản cất không cùng mang mốc đó.
      **KHÔNG retry:** chạy lại cho tới khi XANH là che mất đúng thứ ca này sinh ra để đo.

================= ĐỐI CHỨNG ĐƯỜNG Ở ĐÂU =================
Mọi ca PHỦ ĐỊNH trong tệp này đều có một vế anh em chạy ĐÚNG đường đó và cho kết quả KHÁC:
  * "chưa khai ⇒ TỪ CHỐI" đi kèm "khai `sqlite` ⇒ chạy được, bản sao CÓ dữ liệu";
  * "khai `postgresql` ⇒ TỪ CHỐI" đi kèm chính vế `sqlite` đó;
  * "tên mang MỐC ĐÃ TRUYỀN" đi kèm "tên KHÔNG mang giờ hệ thống" — vế thứ hai là thứ phân biệt
    "đồng hồ là đầu vào" với "đồng hồ đọc ngầm", và nó ĐO ĐƯỢC chứ không phải suy luận;
  * "bản ĐÓNG BĂNG không nhận được mốc" đi kèm "bản THẬT nhận được".

================= MÔI TRƯỜNG =================
Mọi lượt đo chạy trong thư mục TẠM (`kich_ban.chot_an_toan()` TỪ CHỐI vùng dữ liệu thật).
KHÔNG gọi mạng. Không đụng cụm PostgreSQL nào — cả tệp này chỉ đo ĐẦU VÀO, không cần kho thật.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAY_G20 = os.path.join(GOC, "trien_khai", "g20-saoluu")
sys.path.insert(0, DAY_G20)

import ban_va       # noqa: E402
import fail_closed as fc   # noqa: E402
import kich_ban     # noqa: E402

APP_THAT = os.path.join(GOC, "app")
PY = sys.executable or "python3"

# MỐC THỜI GIAN DÙNG CHO MỌI CA Ở ĐÂY. Cố định, KHÁC hẳn giờ chạy thật — nhờ vậy "tên có mang
# mốc này không" là một câu hỏi ĐO ĐƯỢC: nếu mã đọc đồng hồ hệ thống thì tên sẽ không bao giờ
# khớp, và ca này ĐỎ. Dùng đúng hằng của bộ đo để hai chỗ không lệch nhau.
LUC = kich_ban.LUC_BA_LUOT


def _chay(ma, data_dir, app_dir=APP_THAT, khai_kho=kich_ban.KHAI_SQLITE, timeout=600):
    """Chạy `ma` trong tiến trình riêng, `VIP_HUB_DATA` trỏ vào thư mục tạm, `app/` chỉ định.

    Ba thứ đi qua THAM SỐ chứ không qua môi trường ngầm: thư mục dữ liệu, thư mục `app/`, và
    khai báo kho đang chạy. `kich_ban.chay_con` lo phần "luôn `pop` giá trị thừa hưởng" — nếu
    không, một `VIP_KHO_DANG_CHAY` lọt vào từ shell sẽ khiến nhánh "chưa khai" không bao giờ chạy.
    """
    ma_day_du = "import sys; sys.path.insert(0, %r)\n%s" % (app_dir, ma)
    return kich_ban.chay_con(ma_day_du, data_dir, timeout=timeout, khai_kho=khai_kho)


def _ten(p):
    return os.path.basename(p) if p else None


def _duong_in_ra(out):
    """Đường dẫn bản sao lưu, ĐỌC TỪ DÒNG `SAO_LUU ` — không quét cả stdout.

    Đo được ngay lượt chạy đầu của tệp này: `khoi_phuc()` cũng in ra đường dẫn (bản cất của nó),
    nên quét cả stdout sẽ nhặt lẫn `hub-truoc-rollback-*` vào danh sách "bản sao lưu" và ca ĐỎ vì
    chính phép đếm của mình. Một dấu mốc rõ ràng cho dòng cần đọc là cách sửa, không phải lọc bớt
    hậu tố cho tới khi XANH.
    """
    for d in out.splitlines():
        if d.startswith("SAO_LUU "):
            return _ten(d.split(" ", 1)[1].strip())
    return None


# ============================================================================
# A — KHO ĐANG CHẠY: KHAI BÁO, KHÔNG ĐOÁN
# ============================================================================
class A_KhoDangChay(unittest.TestCase):
    """Bốn nhánh của chốt (4)/(4b), đo bằng MÃ THOÁT THẬT của tiến trình đã chạy thật."""

    nen = None
    kq = None

    @classmethod
    def setUpClass(cls):
        cls.nen = kich_ban.chot_an_toan(tempfile.mkdtemp(prefix="g22-khodangchay-"))
        cls.kq = {}
        # Thư mục dữ liệu CÓ `hub.db` THẬT (51 bảng + dữ liệu): đúng trạng thái `do2b` — "hub.db
        # CŨ còn sót". Không gieo dữ liệu thì mọi bất biến dưới đây rỗng nghĩa.
        A = os.path.join(cls.nen, "A")
        os.makedirs(A, exist_ok=True)
        rc_gieo, _, err_gieo = kich_ban.gieo(A)
        cls.kq["rc_gieo"] = rc_gieo
        cls.kq["loi_gieo"] = err_gieo[-300:]
        cls.kq["co_hub_db"] = os.path.exists(kich_ban.db(A))
        cls.kq["A"] = A
        cls.kq["sao_luu_chua_khai"] = kich_ban.sao_luu(A, khai_kho=None)
        cls.kq["sao_luu_sqlite"] = kich_ban.sao_luu(A, khai_kho=kich_ban.KHAI_SQLITE)
        cls.kq["sao_luu_postgres"] = kich_ban.sao_luu(A, khai_kho=kich_ban.KHAI_POSTGRESQL)
        cls.kq["sao_luu_sai_chinh_ta"] = kich_ban.sao_luu(A, khai_kho="my-sql")
        cls.kq["sao_luu_viet_hoa"] = kich_ban.sao_luu(A, khai_kho="  SQLite  ")

    @classmethod
    def tearDownClass(cls):
        if cls.nen:
            shutil.rmtree(cls.nen, ignore_errors=True)

    def test_a0_phep_do_khong_rong(self):
        """Chốt chống phép đo RỖNG: phải có `hub.db` THẬT thì "hub.db cũ còn sót" mới có nghĩa."""
        self.assertEqual(self.kq["rc_gieo"], 0, "gieo dữ liệu hỏng: %s" % self.kq["loi_gieo"])
        self.assertTrue(self.kq["co_hub_db"], "không dựng được `hub.db` — mọi ca dưới đây rỗng")

    def test_a1_chua_khai_thi_TU_CHOI_va_noi_ro(self):
        """BẤT BIẾN (G22) — chưa khai kho đang chạy ⇒ rc != 0, và thông báo NÓI RÕ.

        Đây là chỗ đóng `do2b`. Ca PIN: trên đĩa có `hub.db` thật (51 bảng, có tiền), nhưng hệ
        KHÔNG được phép coi nó là dữ liệu đang phục vụ — vì nó có thể là tệp CŨ còn sót. Không
        có nguồn nào khác trả lời câu đó ngoài người triển khai, nên thiếu câu trả lời ⇒ TỪ CHỐI.
        """
        kq = self.kq["sao_luu_chua_khai"]
        self.assertNotEqual(kq["rc"], 0,
                            "CHƯA KHAI kho đang chạy mà `sao_luu()` vẫn thoát 0 và trả %r — đây "
                            "đúng là đường lùi giả của P-G15-02 `do2b`" % (kq["duong"],))
        self.assertIsNone(kq["duong"], "từ chối mà vẫn in ra một đường dẫn bản sao lưu: %r"
                          % (kq["duong"],))
        err = kq["err"]
        self.assertIn("CHƯA KHAI", err.upper(), "thông báo không nói ra việc thiếu khai: %r" % err)
        self.assertIn(kich_ban.BIEN_KHAI_KHO, err,
                      "thông báo không nêu TÊN chỗ khai (%s) — người trực phải đoán"
                      % kich_ban.BIEN_KHAI_KHO)
        self.assertIn("KHO_DANG_CHAY", err, "thông báo không nêu tên hằng cấu hình")
        self.assertIn("hub.db", err,
                      "thông báo không nói ra việc TRÊN ĐĨA ĐANG CÓ `hub.db` — manh mối duy nhất "
                      "người trực có: %r" % err)

    def test_a2_da_khai_sqlite_thi_chay_duoc_va_ban_sao_CO_du_lieu(self):
        """ĐỐI CHỨNG ĐƯỜNG của `a1` — CÙNG thư mục, CÙNG `hub.db`, khác ĐÚNG một biến: có khai.

        Thiếu vế này thì "từ chối" có thể chỉ là hệ quả của một `sao_luu()` hỏng với MỌI đầu vào
        — hai kết luận khác hẳn nhau, và chỉ vế này phân biệt được.
        """
        kq = self.kq["sao_luu_sqlite"]
        self.assertEqual(kq["rc"], 0, "ĐÃ KHAI `sqlite` mà vẫn hỏng: %s" % kq["err"])
        self.assertTrue(kq["duong"] and os.path.exists(kq["duong"]),
                        "khai `sqlite` mà không có bản sao lưu nào: %r" % (kq["duong"],))
        self.assertTrue(os.path.exists(kq["duong"] + ".sha256"),
                        "bản sao lưu thiếu dấu kiểm `.sha256`")

    def test_a3_khai_postgresql_thi_TU_CHOI_va_chi_dung_pg_dump(self):
        """Khai `postgresql` ⇒ TỪ CHỐI, và thông báo chỉ đúng đường thay thế (`pg_dump -Fc`)."""
        kq = self.kq["sao_luu_postgres"]
        self.assertNotEqual(kq["rc"], 0, "khai `postgresql` mà `sao_luu()` vẫn thoát 0")
        self.assertIsNone(kq["duong"], "khai `postgresql` mà vẫn trả một tệp SQLite: %r"
                          % (kq["duong"],))
        self.assertIn("pg_dump", kq["err"], "thông báo không chỉ đường thay thế: %r" % kq["err"])

    def test_a4_khai_sai_chinh_ta_KHONG_duoc_coi_la_chua_khai(self):
        """Khai sai chính tả ⇒ TỪ CHỐI kèm NGUYÊN VĂN giá trị sai.

        Vì sao đây là một ca riêng: coi `"my-sql"` là "chưa khai" thì hệ rơi về đúng chỗ đang muốn
        tránh, mà lại im lặng về việc người triển khai ĐÃ khai — chỉ khai sai. Thông báo phải nói
        ra giá trị sai thì mới sửa được.
        """
        kq = self.kq["sao_luu_sai_chinh_ta"]
        self.assertNotEqual(kq["rc"], 0, "khai sai chính tả mà `sao_luu()` vẫn thoát 0")
        self.assertIn("my-sql", kq["err"], "thông báo không nêu nguyên văn giá trị khai sai: %r"
                      % kq["err"])

    def test_a5_chuan_hoa_khai_bao_khong_phan_biet_hoa_thuong(self):
        """`'  SQLite  '` phải được nhận — nếu không, một khai báo ĐÚNG vẫn bị TỪ CHỐI oan."""
        kq = self.kq["sao_luu_viet_hoa"]
        self.assertEqual(kq["rc"], 0, "khai `'  SQLite  '` bị từ chối: %s" % kq["err"])
        self.assertTrue(kq["duong"], "khai hợp lệ mà không có bản sao lưu")


# ============================================================================
# B — MỐC THỜI GIAN LÀ ĐẦU VÀO, KHÔNG ĐỌC ĐỒNG HỒ NGẦM
# ============================================================================
class B_DongHoLaDauVao(unittest.TestCase):
    """Tên bản sao lưu / bản cất phải mang MỐC ĐÃ TRUYỀN, không mang giờ hệ thống."""

    nen = None
    kq = None

    @classmethod
    def setUpClass(cls):
        cls.nen = kich_ban.chot_an_toan(tempfile.mkdtemp(prefix="g22-dongho-"))
        cls.kq = {}
        A = os.path.join(cls.nen, "A")
        os.makedirs(A, exist_ok=True)
        rc_gieo, _, err = kich_ban.gieo(A)
        cls.kq["rc_gieo"] = rc_gieo
        cls.kq["loi_gieo"] = err[-300:]
        cls.kq["A"] = A

        # Ba lượt `khoi_phuc()` LIÊN TIẾP với CÙNG một mốc, đo ở tầng API SẢN PHẨM (không qua bộ
        # đo), để bất biến không phụ thuộc vào việc bộ đo có gọi đúng hay không.
        cls.kq["luc"] = LUC
        ma = (
            "import migrate, os\n"
            "sl = migrate.sao_luu(luc=%r)\n"
            "print('SAO_LUU', sl)\n"
            "for i in range(3):\n"
            "    migrate.khoi_phuc(sl, luc=%r)\n"
            "print('XONG')\n" % (LUC, LUC))
        rc, out, err = _chay(ma, A)
        cls.kq["rc_3luot"] = rc
        cls.kq["out_3luot"] = out
        cls.kq["err_3luot"] = err[-500:]
        cls.kq["ten_ban_cat"] = sorted(
            f for f in kich_ban.liet_ke_sao_luu(A) if f.endswith(".db") and "rollback" in f)
        cls.kq["ten_ban_sao_luu"] = _duong_in_ra(out)

        # ĐỐI CHỨNG: CÙNG phép đo, MỐC KHÁC ⇒ tên phải KHÁC. Thiếu vế này thì "tên mang mốc"
        # có thể đúng một cách tình cờ (ví dụ mốc trùng giờ chạy).
        A2 = os.path.join(cls.nen, "A2")
        os.makedirs(A2, exist_ok=True)
        kich_ban.gieo(A2)
        rc2, out2, err2 = _chay(
            "import migrate\nprint('SAO_LUU', migrate.sao_luu(luc='20200101-000000'))\n", A2)
        cls.kq["rc_moc_khac"] = rc2
        cls.kq["ten_moc_khac"] = _duong_in_ra(out2)
        cls.kq["err_moc_khac"] = err2[-300:]

    @classmethod
    def tearDownClass(cls):
        if cls.nen:
            shutil.rmtree(cls.nen, ignore_errors=True)

    def test_b0_phep_do_khong_rong(self):
        self.assertEqual(self.kq["rc_gieo"], 0, "gieo hỏng: %s" % self.kq["loi_gieo"])
        self.assertEqual(self.kq["rc_3luot"], 0,
                         "ba lượt khôi phục hỏng: %s" % self.kq["err_3luot"])

    def test_b1_ten_ban_sao_luu_mang_MOC_DA_TRUYEN(self):
        """BẤT BIẾN — tên bản sao lưu chứa ĐÚNG mốc truyền vào, không chứa giờ hệ thống."""
        import datetime
        self.assertEqual(self.kq["ten_ban_sao_luu"],
                         "hub-truoc-migrate-%s.db" % self.kq["luc"],
                         "tên bản sao lưu KHÔNG mang mốc đã truyền (đo được %r)"
                         % (self.kq["ten_ban_sao_luu"],))
        bay_gio = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.assertNotIn(bay_gio, self.kq["ten_ban_sao_luu"],
                         "tên mang GIỜ HỆ THỐNG — mốc thời gian vẫn đang được đọc ngầm")

    def test_b2_ba_luot_CUNG_MOT_MOC_khong_xoa_nhau(self):
        """BẤT BIẾN của ca E3, đo ở tầng API: ba lượt CÙNG MỘT MỐC ⇒ BA bản cất, không xoá nhau.

        Trước G22 điều này KHÔNG được ép: ba lượt đọc đồng hồ ngầm nên có thể rơi vào hai-ba mốc
        khác nhau, và khi đó phép đếm XANH mà đường ĐÈ chưa hề được chạm tới.
        """
        ten = self.kq["ten_ban_cat"]
        self.assertEqual(len(ten), 3,
                         "ba lượt khôi phục cùng mốc %s mà chỉ để lại %s bản cất — lượt sau ĐÈ "
                         "IM LẶNG lượt trước" % (self.kq["luc"], len(ten)))
        for t in ten:
            self.assertTrue(t.startswith("hub-truoc-rollback-%s" % self.kq["luc"]),
                            "bản cất %r KHÔNG mang mốc đã truyền" % t)

    def test_b3_MOC_KHAC_thi_ten_KHAC(self):
        """ĐỐI CHỨNG ĐƯỜNG — cùng phép đo, mốc khác ⇒ tên khác.

        Thiếu vế này thì `b1` có thể đúng một cách tình cờ, và "mốc là đầu vào" trở thành một
        khẳng định không đo được.
        """
        self.assertEqual(self.kq["rc_moc_khac"], 0, "lượt mốc khác hỏng: %s"
                         % self.kq["err_moc_khac"])
        self.assertEqual(self.kq["ten_moc_khac"], "hub-truoc-migrate-20200101-000000.db",
                         "mốc KHÁC mà tên KHÔNG khác: %r" % (self.kq["ten_moc_khac"],))
        self.assertNotEqual(self.kq["ten_moc_khac"], self.kq["ten_ban_sao_luu"],
                            "hai mốc khác nhau cho ra cùng một tên — tham số `luc` bị bỏ qua")

    def test_b4_bo_do_truyen_MOC_CO_DINH_va_ket_qua_TAT_DINH(self):
        """Ca của bộ đo (`kich_ban`) dùng MỐC CỐ ĐỊNH, và chạy HAI lần cho CÙNG kết quả.

        Đây là vế "chạy riêng và chạy chung phải cùng kết quả" ở tầng ca đo: không phụ thuộc giờ
        chạy, không retry. So cả DANH SÁCH TÊN, không chỉ con số đếm — hai lượt có thể cùng cho
        "3 bản cất" mà tên khác nhau, và khi đó phép so con số sẽ bỏ lọt.
        """
        self.assertEqual(kich_ban.LUC_BA_LUOT, LUC,
                         "bộ đo đổi mốc cố định mà tệp này không biết: %r"
                         % (kich_ban.LUC_BA_LUOT,))
        lan1 = kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay()
        lan2 = kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay()
        for nhan, kq in (("lượt 1", lan1), ("lượt 2", lan2)):
            self.assertEqual(kq["luc"], LUC, "%s: ca đo không dùng mốc cố định" % nhan)
            self.assertTrue(kq["nhan_luc"],
                            "%s: `khoi_phuc()` KHÔNG nhận tham số mốc ⇒ ca đo về mốc không dựng "
                            "được trên bản này" % nhan)
            self.assertTrue(kq["cung_mot_moc"],
                            "%s: ba bản cất KHÔNG cùng mang mốc %s — đường ĐÈ chưa được chạm tới: "
                            "%s" % (nhan, LUC, kq["ban_cat"]))
            self.assertGreaterEqual(kq["so_ban_cat_sau_3_lan"], 3,
                                    "%s: ba lượt cùng mốc chỉ để lại %s bản cất"
                                    % (nhan, kq["so_ban_cat_sau_3_lan"]))
            self.assertGreaterEqual(kq["so_ban_cat_giu_du_lieu_goc"], 1,
                                    "%s: không bản cất nào giữ được dữ liệu vừa mất" % nhan)
        self.assertEqual(lan1["ban_cat"], lan2["ban_cat"],
                         "HAI LƯỢT CHẠY CHO TÊN BẢN CẤT KHÁC NHAU ⇒ ca còn phụ thuộc thời điểm "
                         "chạy: %s ≠ %s" % (lan1["ban_cat"], lan2["ban_cat"]))
        self.assertEqual([lan1["so_ban_cat_sau_1_lan"], lan1["so_ban_cat_sau_3_lan"]],
                         [lan2["so_ban_cat_sau_1_lan"], lan2["so_ban_cat_sau_3_lan"]],
                         "hai lượt cho số bản cất khác nhau")


# ============================================================================
# C — BỘ ĐO CÓ RĂNG, VÀ BẢN ĐÓNG BĂNG CHỨNG MINH KHIẾM KHUYẾT LÀ THẬT
# ============================================================================
class C_DoiChung(unittest.TestCase):
    """Không có lớp này thì hai lớp trên chỉ là hai lời khẳng định."""

    nen = None

    @classmethod
    def setUpClass(cls):
        cls.nen = kich_ban.chot_an_toan(tempfile.mkdtemp(prefix="g22-doichung-"))
        # `goc` = bản ĐÓNG BĂNG trước khi vá (`migrate_nguyenban.py`, md5 đã ghim trong `ban_va`).
        # Dùng `ban_va.dung_bien_the` để KHÔNG dựng lại một bản sao thứ hai của cùng một phép đo.
        cls.bt = ban_va.dung_bien_the(cls.nen, chi_tiem=())
        cls.kq = {}
        A = os.path.join(cls.nen, "A")
        os.makedirs(A, exist_ok=True)
        kich_ban.gieo(A)
        cls.kq["A"] = A

    @classmethod
    def tearDownClass(cls):
        if cls.nen:
            shutil.rmtree(cls.nen, ignore_errors=True)

    def test_c1_ban_DONG_BANG_khong_nhan_duoc_MOC(self):
        """BẢN ĐÓNG BĂNG (`migrate_nguyenban.py`) KHÔNG có tham số `luc` ⇒ rc != 0.

        Đây là vế chứng minh KHIẾM KHUYẾT LÀ THẬT, không phải một cách nói: trước G22, mốc thời
        gian KHÔNG THỂ là đầu vào của `khoi_phuc()` — nó chỉ có thể được đọc ngầm bên trong. Chạy
        thật trên bản đóng băng, lấy mã thoát thật.
        """
        rc, out, err = _chay(
            "import migrate\n"
            "print(migrate.khoi_phuc('/khong/co/that.db', luc=%r))\n" % LUC,
            self.kq["A"], app_dir=self.bt["goc"])
        self.assertNotEqual(rc, 0, "bản ĐÓNG BĂNG lại nhận được `luc` — nó không phải bản cũ?")
        self.assertIn("luc", err,
                      "bản đóng băng hỏng vì lý do KHÁC (không phải thiếu tham số `luc`), nên "
                      "kết luận 'mốc chưa từng là đầu vào' không đứng trên phép đo này: %r" % err)

    def test_c2_ban_THAT_nhan_duoc_MOC(self):
        """ĐỐI CHỨNG ĐƯỜNG của `c1` — CÙNG lời gọi, trên TỆP THẬT: nhận được mốc.

        Cố ý gọi với một tệp sao lưu KHÔNG tồn tại: điều đang đo là "tham số `luc` có được NHẬN
        không", không phải "khôi phục có thành công không". Nếu nó nổ vì thiếu tham số thì vế
        `c1` không chứng minh được gì (cả hai bản cùng nổ vì cùng một lý do).
        """
        rc, out, err = _chay(
            "import migrate\n"
            "print(migrate.khoi_phuc('/khong/co/that.db', luc=%r))\n" % LUC,
            self.kq["A"], app_dir=APP_THAT)
        self.assertNotEqual(rc, 0, "khôi phục từ một tệp không tồn tại mà vẫn thoát 0")
        self.assertNotIn("unexpected keyword argument", err,
                         "TỆP THẬT không nhận tham số `luc`: %r" % err)
        # Phép so với `c1` chỉ có nghĩa khi CẢ HAI cùng đi qua đúng chỗ nhận tham số. Nếu bản
        # thật nổ vì một lý do khác hẳn (ví dụ không thấy tệp) thì vẫn ổn — miễn là KHÔNG phải
        # "không nhận tham số".
        self.assertIn("that.db", err,
                      "bản thật nổ vì lý do lạ, không phải vì tệp sao lưu không tồn tại: %r" % err)

    def test_c3_chot_cung_mot_moc_CO_RANG(self):
        """Bản ghi `S4` có `cung_mot_moc = False` PHẢI bị tố cáo.

        Chốt mới chỉ có nghĩa nếu nó LÀM ĐỎ ĐƯỢC: một ca XANH vì ba lượt rơi vào ba mốc khác nhau
        phải bị `phan_quyet()` gọi tên là "PHÉP ĐO KHÔNG DỰNG ĐƯỢC", chứ không được tính là ĐẠT.
        """
        bg = {"ma": "S4", "rc": 0, "c_dat": True, "c_lech": [],
              "bang_chung": {"so_ban_cat_giu_du_lieu_goc": 3, "so_ban_cat_sau_1_lan": 1,
                             "so_ban_cat_sau_3_lan": 3, "rc_kp1": 0, "rc_kp2": 0, "rc_kp3": 0,
                             "cung_mot_moc": False, "nhan_luc": True, "luc": LUC,
                             "ban_cat": ["hub-truoc-rollback-20261016-120000.db",
                                         "hub-truoc-rollback-20261016-120001.db"]}}
        loi = fc.phan_quyet(bg)
        self.assertTrue(loi, "ba lượt KHÁC mốc mà `phan_quyet()` im lặng ⇒ chốt mới không ai canh")
        self.assertTrue(any("KHÔNG DỰNG ĐƯỢC" in x for x in loi),
                        "chốt mới tố cáo nhưng không nói ra 'PHÉP ĐO KHÔNG DỰNG ĐƯỢC': %s" % loi)
        # ĐỐI CHỨNG DƯƠNG: chính bản ghi đó, chỉ đổi `cung_mot_moc` sang True, phải ĐẠT.
        bg["bang_chung"]["cung_mot_moc"] = True
        bg["bang_chung"]["nhan_luc"] = True
        bg["bang_chung"]["ban_cat"] = ["hub-truoc-rollback-%s.db" % LUC]
        self.assertEqual(fc.phan_quyet(bg), [],
                         "bản ghi ĐẠT mà vẫn bị tố cáo — chốt mới đang ĐỎ GIẢ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
