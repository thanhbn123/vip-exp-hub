# Khoá chống chạy migration đồng thời + ngữ nghĩa lùi của DDL (chỉ thị G12 mục 5C, 11).
#
# Ba thứ bộ này khoá lại, cả ba đo được thật ngày 15/10/2026:
#   1. 8 tiến trình cùng migrate → phải ĐÚNG MỘT nâng cấp, 7 nhường, 0 lỗi.
#   2. `executescript` tự COMMIT giao dịch đang mở → migration CHƯA BAO GIỜ nguyên tử.
#   3. Một thread tự khoá chính mình qua hai kết nối → chờ hết giờ theo đợt 30 giây.
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DU_AN = os.path.dirname(GOC)
sys.path.insert(0, GOC)

_TM = tempfile.mkdtemp(prefix="vh-migdt-")
import cau_hinh                                                          # noqa: E402
cau_hinh.THU_MUC_DU_LIEU = _TM
cau_hinh.DUONG_DAN_CSDL = os.path.join(_TM, "hub.db")
import csdl                                                             # noqa: E402
import migrate                                                          # noqa: E402

SO_TIEN_TRINH = 8

CON_CHAY = r'''
import os, sys
sys.path.insert(0, %r)
import cau_hinh
cau_hinh.THU_MUC_DU_LIEU = os.environ["D"]
cau_hinh.DUONG_DAN_CSDL = os.path.join(os.environ["D"], "hub.db")
import time
import migrate
khi = float(os.environ["BAT_DAU"])
while time.time() < khi:
    time.sleep(0.001)
try:
    kq = migrate.chay(im_lang=True)
    print("%%s|%%s|%%s" %% (sys.argv[1], kq.get("da_nang"), kq.get("nhuong", False)), flush=True)
except Exception as e:
    print("%%s|LOI|%%s" %% (sys.argv[1], str(e)[:60]), flush=True)
''' % (GOC,)


def _chay_song_song(thu_muc, n):
    """Chạy n tiến trình migrate CÙNG một vạch xuất phát. Trả danh sách (nhãn, nâng, nhường)."""
    tep = os.path.join(thu_muc, "_con.py")
    with open(tep, "w", encoding="utf-8") as f:
        f.write(CON_CHAY)
    mt = dict(os.environ, D=thu_muc, BAT_DAU=str(time.time() + 2.0))
    ps = [subprocess.Popen([sys.executable, tep, "tt%d" % i], env=mt,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
          for i in range(n)]
    ra = []
    for p in ps:
        o, e = p.communicate(timeout=180)
        ra.append((o.strip(), e.strip()))
    return ra


class A_MigrationDongThoi(unittest.TestCase):
    """Vạch xuất phát chung là BẮT BUỘC, không phải cho chắc.

    Không có nó, chi phí nạp mô-đun làm các tiến trình so le nhau: lượt đo đầu ngày
    15/10/2026 cho 6/6 tiến trình đều "nâng=True, 0,20 giây" — nhìn như không ai phải chờ
    khoá, trong khi thật ra chúng chạy nối đuôi và phép đo chẳng chứng minh gì (§12.1).
    """

    def test_a1_dung_mot_tien_trinh_nang_cap(self):
        tm = tempfile.mkdtemp(prefix="vh-dt1-")
        kq = _chay_song_song(tm, SO_TIEN_TRINH)
        # HAI đường nhường, cả hai đều ĐÚNG — bản đầu của ca này chỉ tính một đường và
        # báo hỏng 3/5 lượt vì chuyện đó. Nếu tin nó thì em đã đi "sửa" mã đang chạy đúng.
        #   · `nhuong=True`  — chờ được khoá rồi đọc lại BÊN TRONG khoá, thấy việc đã xong.
        #   · `da_nang=False` không kèm `nhuong` — lượt đọc NGOÀI khoá ở đầu `chay()` đã thấy
        #     phiên bản đích, nên về sớm, không xin khoá. Rẻ hơn và cũng đúng.
        nang, nhuong_trong, ve_som, loi = [], [], [], []
        for o, e in kq:
            p = o.split("|")
            if len(p) != 3 or p[1] == "LOI":
                loi.append((o, e[-300:]))
            elif p[1] == "True":
                nang.append(p[0])
            elif p[2] == "True":
                nhuong_trong.append(p[0])
            else:
                ve_som.append(p[0])
        self.assertEqual(len(loi), 0, f"tiến trình hỏng: {loi}")
        self.assertEqual(len(nang), 1,
                         f"phải ĐÚNG 1 tiến trình nâng cấp, thực {len(nang)}: {nang}")
        self.assertEqual(len(nhuong_trong) + len(ve_som), SO_TIEN_TRINH - 1,
                         f"{SO_TIEN_TRINH - 1} tiến trình phải không nâng cấp; "
                         f"nhường-trong-khoá={nhuong_trong} về-sớm={ve_som}")
        # Ít nhất một tiến trình phải đi qua đúng đường KHOÁ, nếu không ca này không đo
        # được cái nó nói là đang đo (§12.1) — nó chỉ đo lượt về sớm.
        self.assertGreaterEqual(len(nhuong_trong), 1,
                                "không tiến trình nào chờ khoá rồi nhường — vạch xuất phát "
                                "chung không hiệu lực, phép đo này chưa chạm tới khoá")

    def test_a2_csdl_sau_cung_dung_mot_ban(self):
        """Nâng cấp hai lần là nhân đôi dữ liệu seed hoặc nổ ở UNIQUE. Đo trên CSDL thật."""
        tm = tempfile.mkdtemp(prefix="vh-dt2-")
        _chay_song_song(tm, SO_TIEN_TRINH)
        kn = csdl.ket_noi(os.path.join(tm, "hub.db"))
        try:
            dong = kn.execute("SELECT phien_ban, COUNT(*) FROM schema_version"
                              " GROUP BY phien_ban").fetchall()
            self.assertEqual(dong, [(csdl.PHIEN_BAN_SCHEMA, 1)], f"schema_version: {dong}")
            bang = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            self.assertGreaterEqual(bang, 45, f"chỉ {bang} bảng — migration chạy dở")
            tg = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
            self.assertGreaterEqual(tg, 4, f"chỉ {tg} trigger — DDL G07 chưa vào đủ")
            self.assertEqual(kn.execute("SELECT COUNT(*) FROM goi_dich_vu").fetchone()[0],
                             len(cau_hinh.GOI_MAC_DINH), "gói bị seed nhiều lần hoặc thiếu")
            self.assertEqual(kn.execute("SELECT COUNT(*) FROM permissions").fetchone()[0],
                             kn.execute("SELECT COUNT(DISTINCT ma) FROM permissions").fetchone()[0])
        finally:
            kn.close()


class B_DDLLuiDuoc(unittest.TestCase):

    def test_b1_executescript_tu_commit(self):
        """GHI RA ĐIỂM VẤP: `executescript` chốt giao dịch đang mở, lặng lẽ.

        Đây là lý do `chay_ddl_trong_giao_dich` phải tồn tại. Ca này hỏng nghĩa là python đã
        đổi hành vi — lúc đó mới được bỏ hàm kia, chứ không phải bỏ vì "trông thừa".
        """
        kn = csdl.ket_noi(os.path.join(_TM, "b1.db"), tuong_minh=True)
        try:
            kn.execute("BEGIN IMMEDIATE")
            self.assertTrue(kn.in_transaction)
            kn.executescript("CREATE TABLE a (x INTEGER);")
            self.assertFalse(kn.in_transaction,
                             "executescript KHÔNG còn tự commit — xem lại chay_ddl_trong_giao_dich")
        finally:
            kn.close()

    def test_b2_chay_ddl_khong_chot_giao_dich(self):
        kn = csdl.ket_noi(os.path.join(_TM, "b2.db"), tuong_minh=True)
        try:
            kn.execute("BEGIN IMMEDIATE")
            n = migrate.chay_ddl_trong_giao_dich(kn, """
CREATE TABLE b (x INTEGER);
CREATE TRIGGER tg_b BEFORE UPDATE ON b
  BEGIN SELECT RAISE(ABORT, 'bat bien'); END;
CREATE INDEX ix_b ON b(x);
""")
            self.assertEqual(n, 3, "phải tách đúng 3 câu")
            self.assertTrue(kn.in_transaction, "giao dịch bị chốt giữa đường")
            kn.execute("ROLLBACK")
            con = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN"
                             " ('b','tg_b','ix_b')").fetchone()[0]
            self.assertEqual(con, 0, "ROLLBACK phải lùi được CẢ DDL")
        finally:
            kn.close()

    def test_b3_khong_cat_trigger_theo_dau_cham_phay(self):
        """`CREATE TRIGGER ... BEGIN ...; END;` có `;` BÊN TRONG. Cắt theo `;` là sinh câu cụt."""
        kn = csdl.ket_noi(os.path.join(_TM, "b3.db"), tuong_minh=True)
        try:
            kn.execute("CREATE TABLE c (x INTEGER)")
            n = migrate.chay_ddl_trong_giao_dich(kn, """
CREATE TRIGGER tg_c BEFORE DELETE ON c
  BEGIN SELECT RAISE(ABORT, 'khong duoc xoa'); END;
""")
            self.assertEqual(n, 1, "khối trigger phải là MỘT câu, không phải hai")
            kn.execute("INSERT INTO c VALUES (1)")
            with self.assertRaises(csdl.LoiToanVen):
                kn.execute("DELETE FROM c")
        finally:
            kn.close()

    def test_b4_cau_chua_tron_thi_nem_khong_bo_qua(self):
        kn = csdl.ket_noi(os.path.join(_TM, "b4.db"), tuong_minh=True)
        try:
            with self.assertRaises(ValueError):
                migrate.chay_ddl_trong_giao_dich(kn, "CREATE TABLE d (x INTEGER")
        finally:
            kn.close()


class C_KhongTuKhoaChinhMinh(unittest.TestCase):
    """Khoá lại ca một thread tự khoá chính mình qua hai kết nối."""

    def test_c1_dong_roi_ghi_giua_giao_dich_khong_treo(self):
        """Mô phỏng đúng ca d5: thread khác gọi `dong()` xoá cờ khởi tạo (biến TOÀN CỤC)
        trong lúc thread này đang mở giao dịch, rồi thread này ghi tiếp.

        Trước bản vá, lượt ghi tiếp rơi vào `_khoi_tao_schema`, mở kết nối thứ hai, và chờ
        hết `busy_timeout`. Ca này đặt hạn 10 giây — treo thì nó HỎNG, không chờ mãi.
        """
        csdl.mo()
        csdl.ghi("CREATE TABLE IF NOT EXISTS _thu_tk (x INTEGER)")
        xong = threading.Event()
        loi = []

        def nguoi_ghi():
            try:
                with csdl.giao_dich():
                    csdl.ghi("INSERT INTO _thu_tk VALUES (1)")
                    csdl._da_khoi_tao.clear()      # ← thread khác vừa gọi dong()
                    csdl.ghi("INSERT INTO _thu_tk VALUES (2)")
                xong.set()
            except Exception as e:                  # noqa: BLE001 — thu lại để ca thử đọc
                loi.append("%s: %s" % (type(e).__name__, e))
                xong.set()

        th = threading.Thread(target=nguoi_ghi, daemon=True)
        th.start()
        self.assertTrue(xong.wait(10),
                        "treo quá 10 giây — thread tự khoá chính mình qua hai kết nối")
        self.assertEqual(loi, [], f"lỗi trong lượt ghi: {loi}")

    def test_c2_muoi_thread_ghi_khong_cho_het_gio(self):
        """10 thread ghi đồng thời phải xong trong vài trăm mili-giây, không theo đợt 30 giây."""
        csdl.mo()
        csdl.ghi("CREATE TABLE IF NOT EXISTS _thu_tk2 (x INTEGER)")
        rao = threading.Barrier(10)
        lau, loi = [], []

        def chay(i):
            rao.wait()
            a = time.time()
            try:
                with csdl.giao_dich():
                    csdl.ghi("INSERT INTO _thu_tk2 VALUES (?)", (i,))
            except Exception as e:                  # noqa: BLE001
                loi.append(str(e)[:40])
            finally:
                lau.append(time.time() - a)
                csdl.dong()

        ths = [threading.Thread(target=chay, args=(i,)) for i in range(10)]
        for x in ths:
            x.start()
        for x in ths:
            x.join(30)
        self.assertEqual(loi, [], f"lỗi: {loi}")
        self.assertEqual(len(lau), 10)
        self.assertLess(max(lau), 5.0,
                        f"lượt chậm nhất {max(lau):.2f}s — dấu hiệu chờ hết busy_timeout")


if __name__ == "__main__":
    print("[migrate-đồng-thời] PHẠM VI: %d tiến trình HỆ ĐIỀU HÀNH thật + 10 thread, trên"
          % SO_TIEN_TRINH)
    print("                     SQLite 3.51.0 · py 3.9.6 · macOS arm64, CSDL trên ổ nội bộ.")
    print("                     NGOÀI: PostgreSQL · NFS/ổ mạng (khoá SQLite không đáng tin ở đó)")
    print("                     · nhiều MÁY · tiến trình bị kill giữa migration.")
    unittest.main(verbosity=1)
