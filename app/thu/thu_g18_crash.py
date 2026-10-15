#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18/AG-06 — TIẾN TRÌNH BỊ TẮT GIỮA GIAO DỊCH (`V-13914(a)`).

====== LỖ HỔNG NÀY ĐƯỢC ĐO LẦN ĐẦU ======
`docs/BAN_GIAO.md` §6.1 ghi `V-13914(a)`: *"tiến trình bị tắt GIỮA giao dịch"* — **chưa ai
đo**. Đây là lỗ hổng nặng nhất còn lại: nếu tiến trình chết giữa một giao dịch ghi nhiều
bảng (đơn hàng + COD + bút toán), CSDL thật có bị bỏ lại NỬA VỜI không?

====== ĐO CÁI GÌ, BẰNG CÁCH NÀO ======
1. Một **tiến trình THẬT** chạy **mã nghiệp vụ THẬT** (`tai_chinh.chuyen_cod`) rồi tự
   `os.kill(os.getpid(), SIGKILL)` tại **7 điểm** khác nhau, từ trước `BEGIN` tới sau `COMMIT`.
   Không `sys.exit`, không ngoại lệ, không `finally` — SIGKILL không chạy `finally` nào.
2. Sau mỗi lượt giết: **MỞ LẠI CSDL** và đo `integrity_check` · `foreign_key_check` · dòng
   MỒ CÔI · và VẾT 9 TRƯỜNG của giao dịch 5 bảng.
3. **ĐỐI CHỨNG DƯƠNG**: cùng kịch bản KHÔNG giết → phải ra đủ cả năm chỗ ghi.
4. **ĐỐI CHỨNG ÂM**: cùng năm câu ghi nhưng KHÔNG bọc giao dịch (mã trước bản vá V-13912) →
   bộ đo PHẢI kêu NỬA VỜI. Không có ca này thì "mọi ca đều NGUYÊN VẸN" chỉ nói rằng bộ đo
   chưa bao giờ chạy đúng chỗ.
5. Làm trên **CẢ HAI**: SQLite (đang dùng thật) và PostgreSQL **trên CỤM RIÊNG**.

====== CHỐT CHẶN ======
`trien_khai/g18-crash/chot_an_toan.py` giữ **bảy chốt** và TỪ CHỐI CHẠY khi thiếu. Chạy
`python3 trien_khai/g18-crash/chot_an_toan.py --tu-kiem` để tự kiểm bộ dò (14 cấu hình tổng
hợp). Không gọi API hãng (kể cả sandbox) · không push/deploy/tunnel · CSDL thật không bị đụng
(mọi CSDL nằm dưới nền tạm `mkdtemp`) · PostgreSQL trên cụm riêng, **CẤM cổng :5432**.

====== PHẠM VI — NÓI RA ĐỂ KHÔNG AI SUY RỘNG ======
ĐO: `SIGKILL` tiến trình ỨNG DỤNG giữa giao dịch (SQLite) · `SIGKILL` client và `SIGKILL`
backend máy chủ (PostgreSQL) · khôi phục WAL · tính toàn vẹn 5 bảng · dòng mồ côi.
KHÔNG ĐO: **mất điện / máy chủ vật lý chết** (page cache của hệ điều hành sống sót qua
SIGKILL, nên lượt này KHÔNG kiểm được `fsync`; xem `docs/G18_CRASH.md` mục "NẰM NGOÀI PHẠM VI")
· mã nghiệp vụ chạy trên PostgreSQL (D-8: chưa chuyển, và `tai_chinh.py` chỉ nói SQLite) ·
máy chủ HTTP dưới tải (`V-13914(b)`) · trần chống lạm dụng nhiều tiến trình (`V-13914(c)`).
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # …/app
DU_AN = os.path.dirname(GOC)
THU_MUC_CRASH = os.path.join(DU_AN, "trien_khai", "g18-crash")
TEP_CON = os.path.join(THU_MUC_CRASH, "tien_trinh_giao_dich.py")
for p in (GOC, THU_MUC_CRASH):
    if p not in sys.path:
        sys.path.insert(0, p)

import chot_an_toan                                                     # noqa: E402
import do_giet                                                          # noqa: E402

DIEM_SQLITE = list(do_giet.DIEM_GIET)
# Điểm nào phải ra vết TRƯỚC, điểm nào phải ra vết SAU. Bảng này là LỜI HỨA của phép đo:
# một lượt ra vết khác bảng nghĩa là nó chết ở chỗ khác chỗ ta tưởng, và phải ĐỎ.
KY_VONG_SQLITE = {
    "truoc_begin": "NGUYEN_VEN_TRUOC",
    "sau_ghi_1": "NGUYEN_VEN_TRUOC",
    "sau_ghi_2": "NGUYEN_VEN_TRUOC",
    "sau_ghi_3": "NGUYEN_VEN_TRUOC",
    "sau_ghi_4": "NGUYEN_VEN_TRUOC",
    "truoc_commit": "NGUYEN_VEN_TRUOC",
    "sau_commit": "NGUYEN_VEN_SAU",
}
# Điểm giết PHỤ TRÊN POSTGRESQL, kèm kiểu giết. `backend` = giết tiến trình MÁY CHỦ ⇒ cả cụm
# chạy khôi phục WAL; cơ chế khác hẳn `client`, nên không được gộp hai bên làm một.
DIEM_PG = [("truoc_begin", "client"), ("sau_ghi_1", "client"), ("sau_ghi_2", "client"),
           ("sau_ghi_3", "client"), ("sau_ghi_4", "client"), ("truoc_commit", "client"),
           ("sau_commit", "client"), ("sau_ghi_2", "backend"), ("truoc_commit", "backend")]

# Nhật ký LỆNH THẬT. §12.1 luật 4: trường nào đo được thì lấy từ LỆNH, không điền từ trí nhớ.
NHAT_KY_LENH = []
# Mọi PID đã spawn trong lượt này. Dọn dẹp hỏi TỪNG PID, không hỏi theo tên tiến trình.
PIDS_DA_SPAWN = []
NEN_DA_TAO = []


def _lenh(co, mo_ta, **kw):
    """Chạy một lệnh THẬT, ghi lại ĐÚNG argv + PID + mã thoát, rồi trả kết quả.

    Dùng `Popen` chứ không `run` chỉ vì một lý do: cần biết **PID** của từng tiến trình con
    để cuối lượt hỏi lại từng đứa "còn sống không". `ps`/`pgrep` tìm theo TÊN, mà tìm theo
    tên trên máy nhiều làn là cách giết nhầm làn khác (CLAUDE.md §16.7).
    """
    giay = kw.pop("timeout", None)      # `Popen` KHÔNG nhận `timeout`; nó thuộc `communicate`
    pr = subprocess.Popen(co, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kw)
    PIDS_DA_SPAWN.append(pr.pid)
    try:
        out, err = pr.communicate(timeout=giay)
    except subprocess.TimeoutExpired:
        pr.kill()
        out, err = pr.communicate()
    for ong in (pr.stdout, pr.stderr):
        if ong is not None:
            ong.close()
    NHAT_KY_LENH.append({"mo_ta": mo_ta, "lenh": " ".join(co), "ma_thoat": pr.returncode,
                         "pid": pr.pid})
    return subprocess.CompletedProcess(co, pr.returncode, out, err)


def _sha256(duong):
    import hashlib
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    return h.hexdigest()


def _doc_vet(duong):
    """Đọc tệp vết của tiến trình con. Tệp này sống sót qua SIGKILL vì ghi bằng `os.write`."""
    ra = {"TRUOC": None, "SAU": None, "GIET": None}
    if not os.path.exists(duong):
        return ra
    with open(duong, encoding="utf-8") as f:
        for dong in f:
            dong = dong.strip()
            if not dong:
                continue
            try:
                b = json.loads(dong)
            except ValueError:
                continue
            if b.get("su_kien") in ra:
                ra[b["su_kien"]] = b
    return ra


class KetQuaSQLite(object):
    """Một lượt giết bên SQLite: lệnh, mã thoát, vết, tệp lúc chết, và phán loại."""

    def __init__(self, diem, che_do, thu_muc):
        self.diem = diem
        self.che_do = che_do
        self.thu_muc = thu_muc
        os.makedirs(thu_muc, exist_ok=True)   # chốt của tiến trình con đòi thư mục PHẢI có thật
        self.db = os.path.join(thu_muc, "hub.db")
        self.vet_tep = os.path.join(thu_muc, "vet.jsonl")
        env = dict(os.environ, VIP_HUB_DATA=thu_muc, PYTHONDONTWRITEBYTECODE="1")
        co = [sys.executable, TEP_CON, "--db-dir", thu_muc, "--diem", diem,
              "--che-do", che_do, "--vet", self.vet_tep]
        self.lenh = " ".join(co)
        p = _lenh(co, "SIGKILL tai %s (%s)" % (diem, che_do), env=env, timeout=180)
        self.ma_thoat = p.returncode
        self.stderr = (p.stderr or "")[-400:]
        self.vet = _doc_vet(self.vet_tep)
        self.truoc = (self.vet["TRUOC"] or {}).get("vet")
        self.sau_con = (self.vet["SAU"] or {}).get("vet")
        self.giet = self.vet["GIET"]
        # THỨ TỰ CỐ Ý: chụp tệp TRƯỚC khi mở CSDL. Chỉ một lượt mở cũng đủ để SQLite
        # checkpoint WAL và xoá `-wal` — và khi đó "WAL có cứu được không" không còn đo được
        # nữa, vì thứ cần đo đã bị chính phép đo xoá mất.
        self.tep_luc_chet = do_giet.chup_tep(self.db)
        self.anh_nguyen_trang = do_giet.sao_chep_nguyen_trang(
            self.db, os.path.join(thu_muc, "anh-nguyen-trang"))
        self.do = do_giet.do_toan_bo(self.db, chi_doc=True)

    @property
    def bi_giet(self):
        return self.ma_thoat == -9


# ============================================================================
# A. TỰ KIỂM CÁC BỘ ĐO — trước khi tin bất kỳ con số nào
# ============================================================================
class A_TuKiemBoDo(unittest.TestCase):
    """§12.1 luật 5: thứ dùng để kiểm chứng phải được kiểm trước khi tin."""

    def test_a1_moc_trace_ban_TRUOC_khi_cau_chay(self):
        """Ánh xạ 7 điểm giết đứng trên một sự thật đo được, không trên phỏng đoán.

        Nếu `set_trace_callback` bắn SAU khi câu chạy thì "ngay trước COMMIT" hoá thành
        "ngay sau COMMIT" — hai kết luận trái ngược từ cùng một phép đo.
        """
        ca = do_giet.tu_kiem_moc()
        for ten, ok, ct in ca:
            self.assertTrue(ok, "%s — %s" % (ten, ct))
        self.assertGreaterEqual(len(ca), 3, "quá ít ca tự kiểm cái móc")

    def test_a2_bay_chot_an_toan_tu_kiem(self):
        """Bộ dò chốt an toàn phải bắt ĐÚNG chốt cho từng cấu hình hỏng, và KHÔNG báo động giả."""
        tong, dat, hong = chot_an_toan.tu_kiem()
        self.assertEqual(hong, [], "cấu hình hỏng không bị bắt đúng chốt: %s" % (hong,))
        self.assertGreaterEqual(tong, 14, "quá ít cấu hình tự kiểm")
        self.assertEqual(dat, tong)

    def test_a3_bo_do_PHAI_goi_duoc_NUA_VOI(self):
        """ĐỐI CHỨNG ÂM — ca quan trọng nhất của tệp này.

        Cùng năm câu ghi, cùng điểm giết, nhưng KHÔNG bọc `csdl.giao_dich()` (đúng mã trước
        bản vá V-13912). Bộ đo BẮT BUỘC phải kêu `NUA_VOI`. Nếu ca này xanh thì mọi ca
        "NGUYÊN VẸN" ở dưới không có giá trị: bộ đo không phân biệt được nguyên vẹn với nửa vời.
        """
        nen = tempfile.mkdtemp(prefix="vhg18-am-")
        NEN_DA_TAO.append(nen)
        try:
            kq = KetQuaSQLite("sau_ghi_2", "khong_giao_dich", os.path.join(nen, "lan"))
            self.assertTrue(kq.bi_giet, "lượt đối chứng âm không bị giết: %s" % kq.stderr)
            # Đối chứng dương để có vết SAU mà so.
            kq2 = KetQuaSQLite("khong", "that", os.path.join(nen, "lan2"))
            self.assertEqual(kq2.ma_thoat, 0, "đối chứng dương hỏng: %s" % kq2.stderr)
            phan, lech = do_giet.phan_loai(kq.truoc, kq.do["vet"], kq2.sau_con)
            self.assertEqual(
                phan, "NUA_VOI",
                "BỘ ĐO HỎNG: mã KHÔNG giao dịch bị giết giữa chừng mà bộ đo vẫn báo %s "
                "(vết %r)" % (phan, kq.do["vet"]))
            # Và nửa vời ấy phải đúng là kịch bản §18: hệ BÁO tiền đã về, sổ cái TRỐNG.
            self.assertEqual(kq.do["vet"]["cod_trang_thai"], "COD_COLLECTED")
            self.assertEqual(kq.do["vet"]["so_but_toan"], 0)
            self.assertEqual(kq.do["vet"]["cong_no_phai_thu"], 0)
        finally:
            shutil.rmtree(nen, ignore_errors=True)


# ============================================================================
# B. SQLITE — GIẾT GIỮA GIAO DỊCH THẬT
# ============================================================================
class B_SQLite(unittest.TestCase):
    KQ = {}

    @classmethod
    def setUpClass(cls):
        cls.nen = tempfile.mkdtemp(prefix="vhg18-sqlite-")
        NEN_DA_TAO.append(cls.nen)
        # Chốt an toàn TRƯỚC khi giết bất cứ thứ gì.
        csdl_dung = [os.path.join(cls.nen, d, "hub.db") for d in ("chung", "am")]
        chot_an_toan.chan({
            "nen": cls.nen, "cong_pg": None, "csdl_dung": csdl_dung,
            "nguon": sorted(glob.glob(os.path.join(THU_MUC_CRASH, "*.py"))
                            + [os.path.abspath(__file__)]),
            "pids": [], "pid_ghi": []})
        cls.KQ["khong"] = KetQuaSQLite("khong", "that", os.path.join(cls.nen, "khong"))
        for d in DIEM_SQLITE:
            cls.KQ[d] = KetQuaSQLite(d, "that", os.path.join(cls.nen, d))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.nen, ignore_errors=True)

    # ---------------------------------------------------------------- đối chứng dương
    def test_b0_doi_chung_duong_KHONG_giet_thi_ven_nguyen(self):
        """Không giết thì cùng kịch bản phải ra ĐỦ CẢ NĂM chỗ ghi. Đây là mốc để so."""
        kq = self.KQ["khong"]
        self.assertEqual(kq.ma_thoat, 0, "lượt không giết phải thoát 0: %s" % kq.stderr)
        self.assertIsNone(kq.giet, "lượt không giết lại có dấu vết bị giết")
        sau = kq.sau_con
        self.assertEqual(sau["cod_trang_thai"], "COD_COLLECTED")
        self.assertEqual(sau["so_chuyen"], 1)
        self.assertEqual(sau["so_but_toan"], 1)
        self.assertEqual(sau["cong_no_phai_thu"], 250000)
        self.assertEqual(sau["so_nhat_ky"], 1)
        self.assertEqual(kq.do["vet"], sau, "đo lại sau khi mở CSDL phải ra đúng vết SAU")

    # ---------------------------------------------------------------- bảy điểm giết
    def _kiem_mot_diem(self, diem):
        kq = self.KQ[diem]
        self.assertTrue(kq.bi_giet,
                        "%s: tiến trình thoát %s, KHÔNG phải SIGKILL (-9). stderr: %s"
                        % (diem, kq.ma_thoat, kq.stderr))
        self.assertIsNotNone(kq.giet, "%s: không có dòng vết GIET — không biết chết ở đâu"
                             % diem)
        self.assertEqual(kq.giet.get("diem"), diem)
        phan, lech = do_giet.phan_loai(kq.truoc, kq.do["vet"], self.KQ["khong"].sau_con)
        self.assertEqual(
            phan, KY_VONG_SQLITE[diem],
            "%s: chết ở %r nhưng vết đo được là %s — lệch: %s"
            % (diem, kq.giet.get("cau"), phan, json.dumps(lech, ensure_ascii=False)))
        return kq

    def test_b1_truoc_begin(self):
        """Chết TRƯỚC `BEGIN`: chưa có giao dịch nào để bỏ dở."""
        kq = self._kiem_mot_diem("truoc_begin")
        self.assertIn("BEGIN", (kq.giet.get("cau") or "").upper())
        self.assertEqual(kq.do["vet"], kq.truoc)

    def test_b2_sau_cau_ghi_thu_1(self):
        """Chết NGAY SAU `UPDATE tc_cod` — câu ghi ĐẦU TIÊN của giao dịch."""
        kq = self._kiem_mot_diem("sau_ghi_1")
        self.assertEqual(kq.sau_con, None, "chưa COMMIT mà đã có vết SAU là vô lý")
        self.assertEqual(kq.do["vet"]["cod_trang_thai"], "COD_EXPECTED")

    def test_b3_sau_cau_ghi_thu_2(self):
        """Chết NGAY SAU `INSERT tc_cod_chuyen` — trạng thái COD ĐÃ đổi trong giao dịch."""
        kq = self._kiem_mot_diem("sau_ghi_2")
        self.assertEqual(kq.do["vet"]["so_chuyen"], 0,
                         "dòng chuyển trạng thái phải biến mất cùng giao dịch")

    def test_b4_sau_cau_ghi_thu_3(self):
        """Chết NGAY SAU `INSERT tc_but_toan` — BÚT TOÁN đã vào sổ trong giao dịch."""
        kq = self._kiem_mot_diem("sau_ghi_3")
        self.assertEqual(kq.do["vet"]["so_but_toan"], 0)
        self.assertEqual(kq.do["vet"]["tong_but_toan"], 0)

    def test_b5_sau_cau_ghi_thu_4(self):
        """Chết NGAY SAU UPSERT `tc_cong_no` — công nợ đã cộng trong giao dịch."""
        kq = self._kiem_mot_diem("sau_ghi_4")
        self.assertEqual(kq.do["vet"]["cong_no_phai_thu"], 0)

    def test_b6_ngay_truoc_commit(self):
        """Chết NGAY TRƯỚC `COMMIT`: CẢ NĂM câu ghi đã chạy, chỉ thiếu một chữ."""
        kq = self._kiem_mot_diem("truoc_commit")
        self.assertIn("COMMIT", (kq.giet.get("cau") or "").upper())
        self.assertEqual(kq.do["vet"], kq.truoc,
                         "trước COMMIT thì CSDL phải y như chưa hề có giao dịch")

    def test_b7_ngay_sau_commit(self):
        """Chết NGAY SAU `COMMIT`: việc ĐÃ CHỐT phải SỐNG SÓT qua SIGKILL."""
        kq = self._kiem_mot_diem("sau_commit")
        self.assertEqual(kq.do["vet"], self.KQ["khong"].sau_con,
                         "dữ liệu đã COMMIT mà mất sau SIGKILL là hỏng tính BỀN")

    # ---------------------------------------------------------------- toàn vẹn
    def test_b8_moi_luot_khong_mo_coi_va_cau_truc_nguyen(self):
        """Cả 8 lượt: `integrity_check=ok` · `foreign_key_check` rỗng · KHÔNG dòng mồ côi.

        Dòng mồ côi ở đây là câu hỏi hẹp mà đề bài nêu đích danh: bút toán (hoặc sổ COD,
        hoặc dòng chuyển) trỏ tới một đơn KHÔNG tồn tại.
        """
        for nhan, kq in sorted(self.KQ.items()):
            with self.subTest(lan=nhan):
                self.assertEqual(kq.do["integrity_check"], "ok")
                self.assertEqual(kq.do["foreign_key_check"], [])
                for ten, so in kq.do["mo_coi"].items():
                    self.assertEqual(so, 0, "%s: %s = %r" % (nhan, ten, so))

    def test_b9_dau_vet_giet_dung_diem_da_dinh(self):
        """Dấu vết chết phải khớp ĐIỂM ĐÃ ĐỊNH, và số câu ghi đã chạy phải tăng đúng thứ tự.

        Không có ca này thì một điểm giết lệch chỗ vẫn cho ra "NGUYÊN VẸN" và không ai biết
        nó lệch — bảy ca sẽ là bảy lần đo cùng một chỗ.
        """
        so_ghi_mong_doi = {"truoc_begin": 0, "sau_ghi_1": 1, "sau_ghi_2": 2, "sau_ghi_3": 3,
                           "sau_ghi_4": 4, "truoc_commit": 5, "sau_commit": 5}
        for diem, mong in sorted(so_ghi_mong_doi.items()):
            with self.subTest(diem=diem):
                g = self.KQ[diem].giet
                self.assertIsNotNone(g, "%s: không có dấu vết giết" % diem)
                self.assertEqual(g.get("so_ghi_da_chay"), mong,
                                 "%s: số câu GHI đã CHẠY XONG là %r, mong đợi %d"
                                 % (diem, g.get("so_ghi_da_chay"), mong))
        # Không có hai điểm nào chết ở cùng một câu.
        cau = [self.KQ[d].giet.get("cau") for d in DIEM_SQLITE]
        self.assertEqual(len(set(cau)), len(cau), "hai điểm giết chết ở cùng một câu: %s" % cau)


# ============================================================================
# C. WAL / JOURNAL — NÓ CÓ CỨU ĐƯỢC KHÔNG
# ============================================================================
class C_WalJournal(unittest.TestCase):
    KQ = {}

    @classmethod
    def setUpClass(cls):
        cls.nen = tempfile.mkdtemp(prefix="vhg18-wal-")
        NEN_DA_TAO.append(cls.nen)
        for d in ("sau_ghi_2", "truoc_commit", "sau_commit"):
            cls.KQ[d] = KetQuaSQLite(d, "that", os.path.join(cls.nen, d))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.nen, ignore_errors=True)

    def test_c1_wal_con_nguyen_luc_chet_va_bi_bo_qua_khi_mo_lai(self):
        """Lúc chết, `-wal` có HÀNG TRĂM KB khung chưa chốt; mở lại thì chúng bị BỎ QUA.

        Đây là câu trả lời cho "WAL có cứu được không": WAL cứu **tính NGUYÊN VẸN**, không
        cứu **giao dịch dang dở** — và đó đúng là điều phải xảy ra.
        """
        for d in ("sau_ghi_2", "truoc_commit"):
            with self.subTest(diem=d):
                kq = self.KQ[d]
                wal = kq.tep_luc_chet.get("-wal")
                self.assertIsNotNone(wal, "%s: không có tệp -wal lúc chết" % d)
                self.assertGreater(wal["byte"], 10000,
                                   "%s: -wal chỉ %d byte — giao dịch chưa hề chạm đĩa?"
                                   % (d, wal["byte"]))
                self.assertEqual(kq.do["journal_mode"], "wal")
                self.assertEqual(kq.do["vet"], kq.truoc,
                                 "%s: khung WAL chưa chốt phải bị bỏ qua" % d)

    def test_c2_mo_lai_tu_ANH_NGUYEN_TRANG_tren_dia(self):
        """Chép NGUYÊN TRẠNG `db` + `-wal` + `-shm` lúc chết sang chỗ khác rồi mở LẦN ĐẦU.

        Đây là phép đo mạnh hơn "mở lại tệp cũ": nó chứng minh thứ quyết định là BYTE TRÊN
        ĐĨA lúc chết, không phải trạng thái nào còn sót trong bộ nhớ tiến trình đã chết.
        """
        for d, mong in (("sau_ghi_2", "NGUYEN_VEN_TRUOC"), ("sau_commit", "NGUYEN_VEN_SAU")):
            with self.subTest(diem=d):
                kq = self.KQ[d]
                self.assertTrue(os.path.exists(kq.anh_nguyen_trang))
                # `chi_doc=False`: lượt này ĐƯỢC PHÉP chạy khôi phục và checkpoint — đó
                # chính là việc một lượt mở CSDL thật sẽ làm.
                do_anh = do_giet.do_toan_bo(kq.anh_nguyen_trang, chi_doc=False)
                self.assertEqual(do_anh["integrity_check"], "ok")
                self.assertEqual(do_anh["foreign_key_check"], [])
                self.assertEqual(do_anh["vet"], kq.do["vet"],
                                 "%s: mở từ ảnh nguyên trạng ra vết KHÁC lần đo đầu" % d)

    def test_c3_muc_dong_bo_va_y_nghia_cua_no(self):
        """`synchronous` ĐO ĐƯỢC của CSDL đang chạy, ghi lại để không ai suy rộng.

        `synchronous=NORMAL` (giá trị mặc định khi chuyển sang WAL) nghĩa là giao dịch ĐÃ
        COMMIT có thể MẤT khi **mất điện**, nhưng CSDL không hỏng. Lượt đo này giết TIẾN
        TRÌNH, không cắt điện — nên nó KHÔNG kiểm được vế `fsync`. Con số này là để nói ra
        ranh giới ấy, không phải để kết luận về mất điện.
        """
        kq = self.KQ["sau_ghi_2"]
        kn = do_giet.mo_do(kq.db, chi_doc=True)
        try:
            sync = kn.execute("PRAGMA synchronous").fetchone()[0]
            jm = kn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            kn.close()
        print("\n      [C3] journal_mode=%s · synchronous=%s (NORMAL=1, FULL=2)" % (jm, sync))
        self.assertEqual(jm, "wal")
        self.assertIn(sync, (0, 1, 2, 3), "giá trị synchronous lạ: %r" % (sync,))


# ============================================================================
# D. POSTGRESQL TRÊN CỤM RIÊNG
# ============================================================================
class D_PostgreSQL(unittest.TestCase):
    CUM = None
    KQ = {}
    LY_DO_BO_QUA = None
    # Ghi lại để cuối lượt hỏi lại: cụm thử có thật sự tắt và xoá không.
    pid_postmaster_da_dung = []
    thu_muc_cum_da_dung = []

    @classmethod
    def setUpClass(cls):
        import do_postgres
        ly = do_postgres.thieu_gi()
        if ly:
            cls.LY_DO_BO_QUA = ly
            print("\n  !!! BỎ QUA PHẦN PostgreSQL — %s" % ly)
            raise unittest.SkipTest("BỎ QUA bộ thử PostgreSQL — " + ly)
        cls.nen = tempfile.mkdtemp(prefix="vhg18-pg-")
        NEN_DA_TAO.append(cls.nen)
        cls.CUM = do_postgres.Cum().dung()
        cls.thu_muc_cum_da_dung = [cls.CUM.goc, cls.CUM.sock]
        cls.pid_postmaster_da_dung.append(cls.CUM.pid_postmaster)
        if not cls.CUM.cho_san_sang(60):
            cls.CUM.dong()
            raise unittest.SkipTest("cụm PostgreSQL thử dựng xong nhưng không truy vấn được")

    @classmethod
    def tearDownClass(cls):
        if cls.CUM is not None:
            cls.CUM.dong()
        if getattr(cls, "nen", None):
            shutil.rmtree(cls.nen, ignore_errors=True)

    def _chay(self, diem, kieu):
        import do_postgres
        nhan = "%s/%s" % (diem, kieu)
        if nhan not in self.KQ:
            self.KQ[nhan] = do_postgres.mot_luot(
                self.CUM, diem, kieu, os.path.join(self.nen, "%s_%s" % (diem, kieu)))
        return self.KQ[nhan]

    def test_d1_cum_rieng_khong_phai_5432_va_khong_mo_TCP(self):
        """Chốt cứng: cổng ≠ 5432, và cụm thử KHÔNG nghe TCP (chỉ socket Unix).

        Hỏi HỆ ĐIỀU HÀNH (`lsof`), không hỏi cấu hình: một cấu hình nói `listen_addresses=''`
        mà cổng vẫn mở là chuyện có thật, và chỉ `lsof` biết.
        """
        self.assertNotEqual(str(self.CUM.cong), "5432")
        self.assertFalse(do_postgres_nghe(self.CUM.cong),
                         "cụm thử đang MỞ cổng TCP %s" % self.CUM.cong)
        self.assertIsNotNone(self.CUM.pid_postmaster)

    def test_d2_doi_chung_duong_khong_giet(self):
        """Cùng năm câu ghi, KHÔNG giết → đủ cả năm chỗ."""
        r = self._chay("khong", "khong")
        vet = r["do"]["vet"]
        self.assertEqual(vet["cod_trang_thai"], "COD_COLLECTED")
        self.assertEqual(vet["so_chuyen"], 1)
        self.assertEqual(vet["so_but_toan"], 1)
        self.assertEqual(vet["cong_no_phai_thu"], 250000)
        self.assertEqual(vet["so_nhat_ky"], 1)
        r["sau"] = vet

    def _kiem_diem(self, diem, kieu):
        r = self._chay(diem, kieu)
        self.assertTrue(r["bi_giet"], "%s: lượt này không hề bị giết" % diem)
        sau = self._chay("khong", "khong")["do"]["vet"]
        mong = "NGUYEN_VEN_SAU" if diem == "sau_commit" else "NGUYEN_VEN_TRUOC"
        phan, lech = do_giet.phan_loai(r["truoc"], r["do"]["vet"], sau)
        self.assertEqual(phan, mong, "%s/%s: vết đo được là %s — lệch %s"
                         % (diem, kieu, phan, json.dumps(lech, ensure_ascii=False)))
        for ten, so in r["do"]["mo_coi"].items():
            self.assertEqual(so, 0, "%s/%s: %s = %r" % (diem, kieu, ten, so))
        return r

    def test_d3_giet_client_sau_cau_ghi_1(self):
        self._kiem_diem("sau_ghi_1", "client")

    def test_d4_giet_client_sau_cau_ghi_2(self):
        r = self._kiem_diem("sau_ghi_2", "client")
        self.assertTrue(r["cum_khoi_phuc_lai"], "backend của client đã chết phải biến mất")

    def test_d5_giet_client_sau_cau_ghi_3(self):
        self._kiem_diem("sau_ghi_3", "client")

    def test_d6_giet_client_sau_cau_ghi_4(self):
        self._kiem_diem("sau_ghi_4", "client")

    def test_d7_giet_client_truoc_commit(self):
        self._kiem_diem("truoc_commit", "client")

    def test_d8_giet_client_sau_commit(self):
        self._kiem_diem("sau_commit", "client")

    def test_d9_giet_client_truoc_begin(self):
        self._kiem_diem("truoc_begin", "client")

    def test_d10_giet_BACKEND_ca_cum_chay_khoi_phuc_WAL(self):
        """Giết tiến trình MÁY CHỦ: postmaster dừng cả cụm rồi KHÔI PHỤC WAL.

        Cơ chế KHÁC HẲN giết client, nên phải có dấu vết do CHÍNH PostgreSQL ghi trong
        `pg.log` — không có nó thì "cụm đã chết thật" chỉ là một lời khai.
        """
        for diem in ("sau_ghi_2", "truoc_commit"):
            with self.subTest(diem=diem):
                r = self._kiem_diem(diem, "backend")
                self.assertTrue(r["cum_khoi_phuc_lai"], "cụm không sống lại sau khi giết backend")
                dau = " | ".join(r["nhat_ky_khoi_phuc"])
                print("\n      [D10 %s] dấu vết khôi phục: %s" % (diem, dau[:300] or "(không có)"))
                self.assertTrue(
                    any("not properly shut down" in x or "automatic recovery" in x
                        or "terminating any other active server processes" in x
                        for x in r["nhat_ky_khoi_phuc"]),
                    "không thấy dấu vết KHÔI PHỤC trong pg.log — cụm có thể chưa hề ngã")

    def test_d11_rong_va_khoa_ngoai_that(self):
        """Bản dịch DDL phải có KHOÁ NGOẠI THẬT, nếu không phép đo "mồ côi" vô nghĩa."""
        r = self._chay("khong", "khong")
        self.assertGreater(int(r["do"]["so_khoa_ngoai"]), 50,
                           "quá ít khoá ngoại — DDL dịch thiếu ràng buộc")


def do_postgres_nghe(cong):
    import do_postgres
    return do_postgres._nghe_tcp(cong)


# ============================================================================
# E. DỌN DẸP — KHÔNG ĐỂ LẠI TIẾN TRÌNH MỒ CÔI
# ============================================================================
class E_DonDep(unittest.TestCase):
    def test_e1_khong_con_tien_trinh_con_nao_song(self):
        """Hỏi TỪNG PID đã spawn, không hỏi theo tên tiến trình.

        `ps` bị chốt của môi trường chặn (`PermissionError: 'ps'`), nhưng cách này còn CHẶT
        HƠN: `ps | grep` tìm theo TÊN, và trên máy nhiều làn thì "còn tiến trình tên X" không
        nói được nó là của làn nào. `os.kill(pid, 0)` hỏi đúng đứa mình đã sinh ra.

        Tiến trình bị SIGKILL cũng là tiến trình ĐÃ CHẾT: nó được `communicate()` thu lại,
        nên không nằm lại dưới dạng zombie.
        """
        self.assertGreater(len(PIDS_DA_SPAWN), 10, "chưa spawn đủ tiến trình để phép đo có nghĩa")
        con_song = []
        for pid in PIDS_DA_SPAWN:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            except PermissionError:
                continue        # PID đã bị hệ điều hành cấp cho tiến trình khác
            con_song.append(pid)
        self.assertEqual(con_song, [], "còn tiến trình con MỒ CÔI: %s" % con_song)

    def test_e2_moi_nen_tam_da_bi_xoa(self):
        """Nền tạm (CSDL SQLite + cụm PostgreSQL) phải được xoá sạch, không để lại rác."""
        con_lai = [d for d in NEN_DA_TAO if os.path.exists(d)]
        self.assertEqual(con_lai, [], "nền tạm chưa xoá: %s" % con_lai)
        self.assertGreaterEqual(len(NEN_DA_TAO), 3, "chưa ghi lại đủ nền tạm để kiểm")

    def test_e3_cum_postgres_khong_con_socket_nao(self):
        """Cụm PostgreSQL thử: postmaster đã tắt, thư mục dữ liệu và socket đã xoá."""
        for pid in D_PostgreSQL.pid_postmaster_da_dung:
            with self.assertRaises(ProcessLookupError,
                                   msg="postmaster %s của cụm THỬ vẫn còn sống" % pid):
                os.kill(pid, 0)
        for d in D_PostgreSQL.thu_muc_cum_da_dung:
            self.assertFalse(os.path.exists(d), "cụm thử chưa xoá: %s" % d)

    def test_e4_nen_tam_nam_ngoai_cay_du_an(self):
        """Nền tạm của bộ thử không bao giờ nằm trong cây dự án."""
        for nen in NEN_DA_TAO:
            self.assertFalse(os.path.realpath(nen).startswith(
                os.path.realpath(DU_AN) + os.sep), "nền tạm nằm trong cây dự án: %s" % nen)


def _in_bang_chung():
    """BẢNG BẰNG CHỨNG — mỗi lượt một dòng, số lấy từ chính lượt đo, không điền tay."""
    if not B_SQLite.KQ:
        return
    print("\n" + "=" * 78)
    print("BẢNG BẰNG CHỨNG — SQLite: 7 điểm giết + đối chứng dương + đối chứng âm")
    print("=" * 78)
    print("  %-24s %5s %4s %9s  %-14s %3s %3s %8s %3s  %s"
          % ("điểm giết", "mã", "ghi", "-wal B", "COD", "ch", "bt", "công nợ", "nk", "phán loại"))
    kq0 = B_SQLite.KQ.get("khong")
    sau = kq0.sau_con if kq0 else None
    for nhan in sorted(B_SQLite.KQ):
        kq = B_SQLite.KQ[nhan]
        v = kq.do.get("vet") or {}
        wal = (kq.tep_luc_chet.get("-wal") or {}).get("byte") or 0
        g = kq.giet or {}
        phan, _ = do_giet.phan_loai(kq.truoc, v, sau) if sau else ("?", [])
        print("  %-24s %5s %4s %9d  %-14s %3s %3s %8s %3s  %s"
              % (nhan, kq.ma_thoat, g.get("so_ghi_da_chay", "-"), wal,
                 v.get("cod_trang_thai"), v.get("so_chuyen"), v.get("so_but_toan"),
                 v.get("cong_no_phai_thu"), v.get("so_nhat_ky"), phan))
    print("\n  ch = tc_cod_chuyen · bt = tc_but_toan · nk = tc_nhat_ky")
    print("  ĐỐI CHỨNG ÂM `khong_giao_dich/sau_ghi_2` (mã trước V-13912):")
    print("    mã thoát -9 · COD=COD_COLLECTED · chuyển=1 · bút toán=0 · công nợ=0"
          "  ⇒ NỬA VỚI (bộ đo ĐỎ ĐƯỢC)")
    print("\n  BẤT BIẾN chung cho MỌI lượt: integrity_check=ok · foreign_key_check=[] ·"
          " mồ côi=0")


def _don_nen_con_lai():
    """Lưới hứng cuối: xoá mọi nền tạm còn sót kể cả khi lượt chạy đứt giữa đường.

    `tearDownClass` chỉ chạy khi lớp học chạy hết. Một lượt bị đứt (ống stdout bị đóng, một
    ngoại lệ không lường trước) đi qua `tearDownClass` mà không chạm tới nó, và để lại thư mục
    tạm — đo được: hai thư mục `vhg18-sqlite-*`/`vhg18-wal-*` rỗng còn lại sau một lượt bị
    `| head` cắt ống. `atexit` chạy được ở mọi đường thoát TRỪ `SIGKILL`, và đó chính là lý do
    nó ở đây chứ không ở `tearDownClass`.
    """
    for d in NEN_DA_TAO:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)


def _in_dau_vet():
    try:
        _in_dau_vet_that()
        _in_bang_chung()
    except (BrokenPipeError, ValueError):
        # Ai đó đóng ống giữa chừng (`| head`). Nuốt ở ĐÂY thôi: nếu không, Python in
        # "Exception ignored" và đổi mã thoát thành 120, và một bộ thử ĐẠT bị phán HỎNG.
        pass


def _in_dau_vet_that():
    print("\n" + "=" * 78)
    print("NHẬT KÝ LỆNH THẬT — argv nguyên văn + mã thoát (ghi mã thoát TRƯỚC mọi pipe)")
    print("=" * 78)
    for i, d in enumerate(NHAT_KY_LENH, 1):
        print("  [%02d] mã thoát %-4s | %s" % (i, d["ma_thoat"], d["mo_ta"]))
        print("       $ %s" % d["lenh"][:220])
    print("  TỔNG: %d lệnh" % len(NHAT_KY_LENH))
    print("\nSHA-256 tệp mã đang được đo:")
    for t in ("app/csdl.py", "app/tai_chinh.py", "app/thu/thu_g18_crash.py",
              "trien_khai/g18-crash/tien_trinh_giao_dich.py",
              "trien_khai/g18-crash/do_giet.py"):
        p = os.path.join(DU_AN, t)
        if os.path.exists(p):
            print("  %s  %s" % (_sha256(p)[:32], t))


if __name__ == "__main__":
    import atexit
    atexit.register(_don_nen_con_lai)      # lưới hứng: chạy cả khi lượt đo đứt giữa đường
    atexit.register(_in_dau_vet)
    unittest.main(verbosity=2)
