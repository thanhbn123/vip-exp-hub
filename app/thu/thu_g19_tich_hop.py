#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21/AG-04 — CỔNG TỔNG HỢP: NỐI PHÉP ĐO VÀO BỘ CHẠY CHUNG, VÀ TỰ CHỨNG MINH CỔNG **ĐO ĐƯỢC**.

====== VÌ SAO CÓ TỆP NÀY ======
Làn `g21-ag04-gioihan` đã có một phép đo thật (`app/thu/thu_g21_gioihan.py`, chạy qua
`trien_khai/g21-gioihan/chay.sh`). Nhưng một phép đo **không tự vào bảng tổng kết**: bộ chạy
chung `app/thu/chay_tat_ca.sh` chỉ ghi nhận một bộ thử khi bộ đó

    (a) thoát 0, VÀ
    (b) có DẤU VẾT đã chạy ca (`^OK` hoặc `ca — ĐẠT`), VÀ
    (c) đếm được **số ca > 0**.

Thiếu một trong ba điều kiện, bộ đó bị xếp vào "HỎNG" hoặc "BỎ QUA". Một cổng không bao giờ được
chạy thì **không chứng minh gì** — và một cổng chạy mà không ai đếm thì cũng vậy.

Tệp này là **cổng tổng hợp** đó: nó gọi runner thật (`trien_khai/g21-gioihan/chay.sh`) và
**trả về ĐÚNG mã thoát của runner**.

====== NHƯNG "NỐI CHO NÓ XANH" LÀ CHƯA ĐỦ — PHẢI CHỨNG MINH CỔNG **ĐO ĐƯỢC** ======
Một cổng luôn xanh thì vô dụng, và một cổng luôn đỏ thì cũng vô dụng. Nên tệp này mang theo
**các ca TIÊM LỖI THẬT vào BẢN SAO của runner**, chạy TRƯỚC khi đo:

  (a) runner HỎNG (mã thoát khác 0)                     ⇒ cổng PHẢI ĐỎ   [lỗi tiêm vào bản sao]
  (b) runner KHÔNG CHẠY ĐƯỢC (không tồn tại · là thư mục) ⇒ cổng PHẢI ĐỎ và **PHẢI NÓI RÕ**
      "KHÔNG CHẠY ĐƯỢC" — tuyệt đối không được coi là đạt.
  (c) runner chạy nhưng **0 ca** ⇒ cổng PHẢI ĐỎ. Ca này dựng bằng một suite `unittest` **RỖNG
      thật**: nó in `Ran 0 tests` rồi `OK` và thoát 0 — ĐÚNG hình dạng "xanh giả" mà một luật
      chỉ nhìn mã thoát sẽ bỏ lọt.
  (d) runner thoát 0 nhưng **MỌI ca BỎ QUA** ⇒ cổng PHẢI ĐỎ (0 ca ĐO THẬT không phải là đạt).
  (+) **ĐỐI CHỨNG DƯƠNG**: chính runner THẬT ở phần 2 của lượt chạy. Không có nó thì một cổng
      "đỏ mù" (đỏ với mọi thứ) cũng qua được phép kiểm (a)–(d).

Vì sao (a) và (d) dùng **BẢN SAO** chứ không sửa runner thật: sửa tệp thật là làm bẩn cây nguồn
và có thể để lại rác. Và vì sao bản sao nằm **CÙNG THƯ MỤC** với runner: `chay.sh` tự suy gốc cây
bằng `dirname $0/../..`; đặt bản sao ở độ sâu khác thì nó hỏng vì **đường dẫn**, không phải vì
**lỗi được tiêm** — phép đo sẽ đo nhầm thứ. Mỗi ca tự kiểm còn khẳng định bản sao **KHÁC bản gốc
ĐÚNG MỘT DÒNG**, để "lỗi được tiêm" là ĐƠN NHÂN.

====== ĐỌC SỐ CA Ở HAI KÊNH ĐỘC LẬP ======
Cổng không tin một kênh: nó đếm ca từ **stdout của runner** và đếm lại từ **tệp log** mà runner
tự khai (`log  = <đường dẫn>`), rồi bắt hai kênh phải KHỚP. Tệp log chỉ được tính khi nó được
ghi TRONG chính lượt chạy này (so `mtime`), nếu không thì log cũ của lượt trước sẽ làm kênh thứ
hai nói dối. Cổng cũng đối chiếu `EXIT_BO_DO=<mã>` do runner tự in với mã thoát THẬT của tiến
trình: lệch nhau là bằng chứng tự mâu thuẫn ⇒ ĐỎ.

====== MÃ THOÁT ======
    python3 app/thu/thu_g19_tich_hop.py     # 0 = cổng ĐẠT · khác 0 = cổng ĐỎ (xem bảng dưới)

    0    runner thoát 0 và có ca ĐO THẬT   → mã thoát **nguyên văn của runner**
    x≠0  runner thoát x                    → mã thoát **nguyên văn của runner**
    127  runner KHÔNG CHẠY ĐƯỢC            → mã riêng của CỔNG (POSIX "không tìm thấy lệnh")
    124  runner QUÁ HẠN                    → mã riêng của CỔNG (cùng quy ước `timeout(1)`)
    4    runner thoát 0 nhưng 0 ca đo thật → mã riêng của CỔNG. **Đây là chỗ duy nhất cổng siết
         chặt hơn runner**, vì mã thoát 0 của runner ở đây là XANH GIẢ; ca (c)/(d) chứng minh.
    3    TỰ KIỂM của cổng hỏng             → cổng không đáng tin thì không được phép xanh.

Ngoài hai chỗ siết đó, mã thoát của cổng là **mã thoát nguyên văn của runner** — không viết lại,
không nuốt, không đổi thành 1 cho tiện.

====== SỐ CA MÀ BỘ CHẠY CHUNG GHI NHẬN ======
Là số ca **TỰ KIỂM của cổng** (dòng `Ran N tests` của `unittest`), KHÔNG phải TỔNG của runner:
`app/thu/thu_g21_gioihan.py` là tệp `thu_*.py` nên **chính bộ chạy chung đã tự dò và đếm nó
riêng**; in thêm TỔNG của runner ở đây là ĐẾM HAI LẦN. Con số của runner vẫn được in nguyên văn
trong bảng bằng chứng, chỉ không mang khuôn `N ca — ĐẠT` của bộ đếm.

CHẠY
----
    python3 app/thu/thu_g19_tich_hop.py     # tự kiểm (nhanh) rồi chạy runner thật (~70 giây)
"""

import atexit
import os
import re
import subprocess
import sys
import time
import unittest

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ — đường dẫn suy từ chính tệp này, không điền tay
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(GOC, "app")
THU_MUC_RUNNER = os.path.join(GOC, "trien_khai", "g21-gioihan")
RUNNER = os.path.join(THU_MUC_RUNNER, "chay.sh")

MA_KHONG_CHAY_DUOC = 127
MA_QUA_HAN = 124
MA_KHONG_CO_CA = 4
MA_TU_KIEM_HONG = 3
GIAY_TOI_DA = 2400

# Khuôn cần tiêm: dòng gọi bộ đo trong runner. Khẳng định `count == 1` trước khi thay, để một
# lần refactor runner làm khuôn biến mất thì ca tự kiểm HỎNG (kêu to) chứ không im lặng bỏ qua.
LENH_DO = "python3 -u app/thu/thu_g21_gioihan.py"
LENH_DO_HONG = "python3 -u app/thu/thu_g21_khong_ton_tai_GIA.py"
# Suite `unittest` RỖNG: in `Ran 0 tests` + `OK`, thoát 0 — hình dạng XANH GIẢ của ca (c).
LENH_DO_KHONG_CA = ('python3 -u -c "import unittest; '
                    'unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite())"')
# Thoát 0, có dòng tổng kết, nhưng MỌI ca BỎ QUA — ca (d).
LENH_DO_BO_QUA = "printf '  ca ĐẠT=0 · HỎNG=0 · BỎ QUA=5 · KHUYẾT=0 · TỔNG=5\\n'"

_RAC = []


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. ĐỌC / CHẠY / ĐẾM — ba việc nhỏ, tách ra để ca tự kiểm gọi được ĐÚNG thứ cổng dùng
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _doc(duong):
    with open(duong, encoding="utf-8") as f:
        return f.read()


def _head():
    """HEAD của cây đang đo. `GIT_CONFIG_*` bị gỡ vì môi trường này có `GIT_CONFIG_COUNT` nhưng
    THIẾU `GIT_CONFIG_KEY_*` (N-G18-00) — giữ nguyên thì `git` thoát 128 và dòng HEAD vô nghĩa."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    try:
        p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=GOC, env=e,
                           capture_output=True, text=True, timeout=30)
        return p.stdout.strip() or "(không đọc được)"
    except (OSError, subprocess.SubprocessError):
        return "(không đọc được)"


def _thong_ke(than):
    """Đếm ca trong MỘT luồng văn bản bằng hai khuôn của dự án.

    Khuôn 1: dòng tổng kết của bộ đo G21 — `ca ĐẠT=… · HỎNG=… · BỎ QUA=… · KHUYẾT=… · TỔNG=…`.
    Khuôn 2: `Ran N tests` của `unittest` (kèm `skipped=` nếu có).
    Không khớp khuôn nào ⇒ `nguon = "KHÔNG CÓ DẤU VẾT"` và `tong = 0`. Đây là chỗ LUẬT PHÁN đọc,
    nên nó phải nói được "tôi không thấy dấu vết nào", chứ không được đoán.
    """
    if than is None:
        return None
    m = re.search(r"ca ĐẠT=(\d+)\s*·\s*HỎNG=(\d+)\s*·\s*BỎ QUA=(\d+)\s*·\s*KHUYẾT=(\d+)"
                  r"\s*·\s*TỔNG=(\d+)", than)
    if m:
        return {"nguon": "dòng tổng kết của bộ đo", "dat": int(m.group(1)), "hong": int(m.group(2)),
                "bo_qua": int(m.group(3)), "khuyet": int(m.group(4)), "tong": int(m.group(5))}
    m = re.search(r"Ran (\d+) tests?", than)
    if m:
        sk = re.search(r"skipped=(\d+)", than)
        bo_qua = int(sk.group(1)) if sk else 0
        return {"nguon": "unittest `Ran N tests`", "dat": int(m.group(1)) - bo_qua, "hong": 0,
                "bo_qua": bo_qua, "khuyet": 0, "tong": int(m.group(1))}
    return {"nguon": "KHÔNG CÓ DẤU VẾT", "dat": 0, "hong": 0, "bo_qua": 0, "khuyet": 0, "tong": 0}


def do_runner(duong, giay=GIAY_TOI_DA, cwd=None):
    """Chạy runner THẬT trong tiến trình con và trả về một BẢN ĐO — **không phán**.

    Tách "đo" khỏi "phán" là điều kiện để ca tiêm lỗi kiểm được chính LUẬT PHÁN: bản sao hỏng và
    runner thật đi qua đúng một hàm `phan_quyet`, không phải hai bản luật khác nhau.
    """
    kq = {"duong": duong, "chay_duoc": False, "ly_do_khong_chay": "", "qua_han": False,
          "ma": None, "ra": "", "giay": 0.0, "log": "", "log_tuoi": False, "log_than": "",
          "tong_stdout": None, "tong_log": None, "exit_tu_khai": None, "khop_exit": None}
    if not os.path.isfile(duong):
        kq["ly_do_khong_chay"] = ("KHÔNG CHẠY ĐƯỢC: %s không phải TỆP THƯỜNG (không tồn tại, "
                                  "hoặc là thư mục)" % duong)
        return kq
    if not os.access(duong, os.R_OK):
        kq["ly_do_khong_chay"] = "KHÔNG CHẠY ĐƯỢC: %s không đọc được" % duong
        return kq
    # `PYTHONDONTWRITEBYTECODE`: không để `__pycache__` rơi vào cây nguồn — có những cổng
    # "cây sạch" (`thu_qa_g17.py::A_Nen`) sẽ đỏ vì một tệp rác không liên quan tới sản phẩm.
    moi_truong = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    t0 = time.time()
    p = None
    try:
        p = subprocess.Popen(["sh", duong], cwd=cwd or GOC, env=moi_truong,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        ra, _ = p.communicate(timeout=giay)
        ma = p.returncode
    except subprocess.TimeoutExpired:
        p.kill()
        ra, _ = p.communicate()
        kq.update({"chay_duoc": True, "qua_han": True, "ma": MA_QUA_HAN, "ra": ra or "",
                   "giay": time.time() - t0})
        return kq
    except OSError as e:
        kq["ly_do_khong_chay"] = "KHÔNG CHẠY ĐƯỢC: không khởi động được tiến trình: %s" % e
        return kq
    kq.update({"chay_duoc": True, "ma": ma, "ra": ra or "", "giay": time.time() - t0})
    kq["tong_stdout"] = _thong_ke(kq["ra"])
    m = re.search(r"^log\s*=\s*(.+?)\s*$", kq["ra"], re.M)
    if m:
        kq["log"] = m.group(1)
        try:
            # KÊNH THỨ HAI chỉ được tính khi log được ghi TRONG lượt này: log của lượt trước còn
            # nằm đó sẽ làm kênh độc lập nói dối (một runner rỗng vẫn "thấy" 38 ca của người khác).
            kq["log_tuoi"] = os.path.getmtime(kq["log"]) >= t0 - 1.0
            if kq["log_tuoi"]:
                kq["log_than"] = _doc(kq["log"])
                kq["tong_log"] = _thong_ke(kq["log_than"])
        except OSError:
            kq["tong_log"] = None
    m = re.search(r"^EXIT_BO_DO=(\d+)\s*$", kq["ra"], re.M)
    if m:
        kq["exit_tu_khai"] = int(m.group(1))
        kq["khop_exit"] = (kq["exit_tu_khai"] == ma)
    return kq


def kenh_so_ca(kq):
    """KÊNH QUYẾT ĐỊNH số ca — `(thống_kê, tên_kênh)`. Một chỗ duy nhất, dùng cho cả LUẬT PHÁN
    lẫn ca tự kiểm: nếu ca tự kiểm đọc một kênh khác với kênh luật phán đọc thì nó kiểm một thứ
    khác với thứ cổng dùng, và lời khẳng định "cổng có răng" thành vô nghĩa.

    Kênh 1 là stdout của runner. Runner in bảng tổng kết bằng cách CẮT LOG từ dòng
    `BẢNG N / TỔNG LƯỢT QUA`, nên có những hình dạng log chỉ hiện ở kênh 2 (ví dụ `Ran 0 tests`
    của một suite rỗng nằm TRƯỚC dòng cắt) — khi kênh 1 không có dấu vết nào thì kênh 2 bù vào.
    """
    tk = kq.get("tong_stdout") or _thong_ke(None)
    if tk["nguon"] == "KHÔNG CÓ DẤU VẾT" and kq.get("tong_log"):
        return kq["tong_log"], "kênh 2 (tệp log)"
    return tk, "kênh 1 (stdout runner)"


def phan_quyet(kq):
    """LUẬT PHÁN DUY NHẤT của cổng. Trả `(dat, lý_do)`.

    Thứ tự kiểm là thứ tự "cái gì chết trước": chạy được → mã thoát → dấu vết → số ca ĐO THẬT →
    bằng chứng tự mâu thuẫn. Mọi nhánh ĐỎ đều trả một câu NÓI RÕ VÌ SAO, vì "ĐỎ mà không nói vì
    sao" buộc người sau phải đoán.
    """
    if not kq["chay_duoc"]:
        return False, kq["ly_do_khong_chay"]
    if kq.get("qua_han"):
        return False, ("KHÔNG CHẠY ĐƯỢC (QUÁ HẠN %s giây): runner treo, không có phán quyết nào"
                       % GIAY_TOI_DA)
    if kq["ma"] != 0:
        return False, "runner HỎNG: mã thoát %d (KHÁC 0)" % kq["ma"]
    tk, _ten_kenh = kenh_so_ca(kq)
    if tk["nguon"] == "KHÔNG CÓ DẤU VẾT":
        return False, ("runner thoát 0 nhưng output KHÔNG có dấu vết đã chạy ca nào "
                       "(không `TỔNG=`, không `Ran N tests`) ⇒ KHÔNG được coi là đạt")
    if tk["tong"] - tk["bo_qua"] <= 0:
        if tk["tong"] <= 0:
            return False, "runner thoát 0 nhưng 0 ca (0 ca KHÔNG phải là đạt)"
        return False, ("runner thoát 0 nhưng MỌI ca đều BỎ QUA (%d/%d) ⇒ 0 ca ĐO THẬT, "
                       "KHÔNG phải là đạt" % (tk["bo_qua"], tk["tong"]))
    if kq.get("khop_exit") is False:
        return False, ("bằng chứng TỰ MÂU THUẪN: tiến trình thoát %d nhưng runner tự khai "
                       "`EXIT_BO_DO=%d`" % (kq["ma"], kq["exit_tu_khai"]))
    tl = kq.get("tong_log")
    if tl and tl["nguon"] != "KHÔNG CÓ DẤU VẾT" and tl["tong"] != tk["tong"]:
        return False, ("HAI KÊNH LỆCH NHAU: stdout nói TỔNG=%d, tệp log nói TỔNG=%d"
                       % (tk["tong"], tl["tong"]))
    return True, ("runner thoát 0 · %d ca đo thật (ĐẠT %d · BỎ QUA %d)"
                  % (tk["tong"], tk["dat"], tk["bo_qua"]))


def _mo_ta(kq):
    """Một dòng bằng chứng cho một bản đo — in ra ở mọi ca tự kiểm."""
    tk = kq["tong_stdout"] or {}
    tl = kq["tong_log"] or {}
    quyet, ten = kenh_so_ca(kq) if kq.get("chay_duoc") else ({"tong": 0}, "không chạy được")
    return ("mã thoát=%s · %.1f giây · kênh 1 (stdout): %d ca (%s) · kênh 2 (log): %s · "
            "KÊNH QUYẾT ĐỊNH: %s = %d ca"
            % (kq["ma"], kq["giay"], tk.get("tong", 0), tk.get("nguon", "?"),
               ("%d ca (%s, tươi)" % (tl.get("tong", 0), tl.get("nguon", "?"))) if tl
               else "không tính (thiếu/không tươi)", ten, quyet.get("tong", 0)))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. TIÊM LỖI VÀO BẢN SAO — cơ chế của ba ca (a)/(c)/(d)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _ban_sao_tiem_loi(ten, cu, moi):
    """Sao runner thật ra MỘT TỆP CÙNG THƯ MỤC rồi thay ĐÚNG MỘT khuôn.

    Trả `(đường_dẫn, thân_gốc, thân_mới)` để ca tự kiểm tự khẳng định phép tiêm là ĐƠN NHÂN.
    """
    than_goc = _doc(RUNNER)
    if than_goc.count(cu) != 1:
        raise AssertionError("khuôn cần tiêm phải xuất hiện ĐÚNG MỘT LẦN trong %s (thấy %d lần): %r"
                             % (RUNNER, than_goc.count(cu), cu))
    than_moi = than_goc.replace(cu, moi)
    duong = os.path.join(THU_MUC_RUNNER, ".tam_tiem_loi_%d_%s.sh" % (os.getpid(), ten))
    with open(duong, "w", encoding="utf-8") as f:
        f.write(than_moi)
    os.chmod(duong, 0o755)
    _RAC.append(duong)
    return duong, than_goc, than_moi


def don_dep():
    """Không để lại rác: mọi bản sao tiêm lỗi bị xoá, kể cả khi tệp này nổ giữa đường."""
    for d in list(_RAC):
        try:
            os.remove(d)
        except OSError:
            pass
        _RAC.remove(d)


atexit.register(don_dep)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. TỰ KIỂM — TIÊM LỖI THẬT RỒI HỎI CHÍNH LUẬT PHÁN CỦA CỔNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

class T_CongCoRang(unittest.TestCase):
    """Bốn ca tiêm lỗi + hai đối chứng dương cho chính luật phán.

    Mọi ca ở đây chạy **tiến trình thật** trên **bản sao thật của runner**: không ca nào khẳng
    định bằng lời, và không ca nào chạm vào tệp runner gốc.
    """

    def tearDown(self):
        """Xoá NGAY bản sao của ca vừa chạy — không để rác cho cổng "cây sạch" của làn khác."""
        don_dep()

    def _khac_biet(self, than_goc, than_moi):
        """Danh sách các dòng KHÁC nhau giữa bản gốc và bản sao — phải ĐÚNG MỘT dòng."""
        return [(a, b) for a, b in zip(than_goc.splitlines(), than_moi.splitlines()) if a != b]

    # ── (a) runner HỎNG ⇒ cổng PHẢI ĐỎ ────────────────────────────────────────────────────────
    def test_a1_runner_hong_thi_cong_phai_do(self):
        """Lỗi tiêm: bộ đo bị gọi SAI ĐƯỜNG DẪN ⇒ runner thoát khác 0."""
        duong, goc, moi = _ban_sao_tiem_loi("hong", LENH_DO, LENH_DO_HONG)
        khac = self._khac_biet(goc, moi)
        self.assertEqual(1, len(khac), "phép tiêm phải ĐƠN NHÂN — thấy %d dòng khác: %s"
                         % (len(khac), khac))
        self.assertIn(LENH_DO, khac[0][0])
        self.assertIn(LENH_DO_HONG, khac[0][1])
        kq = do_runner(duong)
        dat, ly = phan_quyet(kq)
        print("\n  [(a)] bản sao HỎNG: %s" % _mo_ta(kq))
        print("        phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertTrue(kq["chay_duoc"], "bản sao phải CHẠY ĐƯỢC (nó là runner thật + 1 lỗi)")
        self.assertNotEqual(0, kq["ma"], "bản sao tiêm lỗi phải thoát KHÁC 0 (thấy %r)" % kq["ma"])
        self.assertFalse(dat, "cổng ĐẠT trên một runner HỎNG ⇒ cổng mù")
        self.assertIn("HỎNG", ly)
        self.assertIn(str(kq["ma"]), ly)

    # ── (b) runner KHÔNG CHẠY ĐƯỢC ⇒ cổng PHẢI ĐỎ và PHẢI NÓI RÕ ──────────────────────────────
    def test_b1_runner_khong_ton_tai_thi_cong_phai_do_va_noi_RO(self):
        """Không có tệp runner ⇒ cổng KHÔNG được coi là đạt, và phải nói rõ 'KHÔNG CHẠY ĐƯỢC'."""
        duong = os.path.join(THU_MUC_RUNNER, ".khong_ton_tai_%d.sh" % os.getpid())
        self.assertFalse(os.path.exists(duong))
        kq = do_runner(duong)
        dat, ly = phan_quyet(kq)
        print("\n  [(b1)] runner không tồn tại: %s" % _mo_ta(kq))
        print("         phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertFalse(kq["chay_duoc"])
        self.assertIsNone(kq["ma"], "không được bịa ra một mã thoát cho runner không tồn tại")
        self.assertFalse(dat, "runner KHÔNG CHẠY ĐƯỢC mà cổng vẫn ĐẠT")
        self.assertIn("KHÔNG CHẠY ĐƯỢC", ly)

    def test_b2_runner_la_thu_muc_thi_cong_phai_do(self):
        """Đường dẫn tồn tại nhưng KHÔNG phải tệp (thư mục) ⇒ vẫn là KHÔNG CHẠY ĐƯỢC."""
        kq = do_runner(THU_MUC_RUNNER)
        dat, ly = phan_quyet(kq)
        print("\n  [(b2)] runner là thư mục: %s" % _mo_ta(kq))
        print("         phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertFalse(kq["chay_duoc"])
        self.assertFalse(dat)
        self.assertIn("KHÔNG CHẠY ĐƯỢC", ly)

    # ── (c) runner chạy nhưng 0 CA ⇒ cổng PHẢI ĐỎ ─────────────────────────────────────────────
    def test_c1_runner_0_ca_thi_cong_phai_do(self):
        """Suite `unittest` RỖNG: đếm ra 0 ca, vẫn in `OK` và thoát 0 — xanh giả điển hình.

        Cố ý KHÔNG viết khuôn đếm ra ở đây dưới dạng có chữ số: `verbosity=2` IN docstring này
        vào stdout, và bộ đếm của `chay_tat_ca.sh` / `C5` lấy dòng khuôn CUỐI CÙNG. Một chữ số
        lọt vào đây là một DÒNG MỒI nằm trước con số thật — hôm nay vô hại, mai đổi thứ tự là
        bộ đếm đọc sai. Xem `THEO_KHUON` ở cuối `main()`: cổng tự kiểm chính điều đó.
        """
        duong, goc, moi = _ban_sao_tiem_loi("khong_ca", LENH_DO, LENH_DO_KHONG_CA)
        self.assertEqual(1, len(self._khac_biet(goc, moi)), "phép tiêm phải ĐƠN NHÂN")
        kq = do_runner(duong)
        dat, ly = phan_quyet(kq)
        print("\n  [(c)] bản sao chạy NHƯNG 0 ca: %s" % _mo_ta(kq))
        print("        output của runner có `OK` (dấu vết xanh) — cổng vẫn phải ĐỎ.")
        print("        phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertTrue(kq["chay_duoc"])
        self.assertEqual(0, kq["ma"], "ca này chỉ có nghĩa khi runner thoát 0 (thấy %r)" % kq["ma"])
        # `OK` nằm ở KÊNH 2: `unittest` in ra stderr, runner gom cả hai vào log, và bảng tổng kết
        # chỉ in phần log SAU dòng cắt — nên đây đúng là chỗ kênh độc lập phải làm việc.
        self.assertIn("OK", kq["log_than"],
                      "bản sao phải in `OK` — nếu không thì đây không phải ca xanh giả")
        self.assertIn("Ran 0 tests", kq["log_than"])
        tk, ten = kenh_so_ca(kq)
        self.assertEqual(0, tk["tong"], "kênh quyết định (%s) phải đọc ra 0 ca" % ten)
        self.assertFalse(dat, "runner thoát 0 với 0 ca mà cổng vẫn ĐẠT ⇒ cổng chỉ nhìn mã thoát")
        self.assertIn("0 ca", ly)

    # ── (d) thoát 0 nhưng MỌI ca BỎ QUA ⇒ cổng PHẢI ĐỎ ────────────────────────────────────────
    def test_d1_moi_ca_bo_qua_thi_cong_phai_do(self):
        """`TỔNG=5` mà `BỎ QUA=5`: đếm được ca nhưng KHÔNG ca nào ĐO THẬT."""
        duong, goc, moi = _ban_sao_tiem_loi("bo_qua", LENH_DO, LENH_DO_BO_QUA)
        self.assertEqual(1, len(self._khac_biet(goc, moi)), "phép tiêm phải ĐƠN NHÂN")
        kq = do_runner(duong)
        dat, ly = phan_quyet(kq)
        print("\n  [(d)] bản sao thoát 0, mọi ca BỎ QUA: %s" % _mo_ta(kq))
        print("        phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertEqual(0, kq["ma"])
        tk, ten = kenh_so_ca(kq)
        self.assertEqual(5, tk["tong"], "kênh quyết định (%s) phải đọc ra TỔNG=5" % ten)
        self.assertFalse(dat, "5 ca BỎ QUA mà cổng vẫn ĐẠT ⇒ 'BỎ QUA' bị gộp vào 'ĐẠT'")
        self.assertIn("BỎ QUA", ly)

    # ── (c2) tệp RỖNG: thoát 0, không một dấu vết nào ⇒ cổng PHẢI ĐỎ ──────────────────────────
    def test_c2_runner_rong_khong_dau_vet_thi_cong_phai_do(self):
        """Một tệp rỗng `sh` chạy trót lọt (thoát 0) mà không in gì — vẫn phải ĐỎ."""
        duong = os.path.join(THU_MUC_RUNNER, ".tam_tiem_loi_%d_rong.sh" % os.getpid())
        with open(duong, "w", encoding="utf-8") as f:
            f.write("")
        os.chmod(duong, 0o755)
        _RAC.append(duong)
        kq = do_runner(duong)
        dat, ly = phan_quyet(kq)
        print("\n  [(c2)] bản sao RỖNG (thoát 0, không dấu vết): %s" % _mo_ta(kq))
        print("         phán quyết cổng: %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertEqual(0, kq["ma"])
        self.assertFalse(dat)
        self.assertIn("KHÔNG có dấu vết", ly)

    # ── (+) ĐỐI CHỨNG DƯƠNG của chính LUẬT PHÁN (dữ liệu TỔNG HỢP) ─────────────────────────────
    def test_e1_doi_chung_DUONG_luat_phan_khong_do_mu(self):
        """Luật phán phải ĐẠT trên một bản đo TỐT. Không có ca này thì (a)–(d) chỉ chứng minh
        được 'cổng luôn đỏ' — và một cổng luôn đỏ thì cũng không đo được gì."""
        ra = ("EXIT_BO_DO=0\n  ca ĐẠT=7 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=7\n")
        tot = {"duong": "gia", "chay_duoc": True, "qua_han": False, "ma": 0, "ra": ra,
               "giay": 1.0, "log": "", "log_tuoi": False, "tong_stdout": _thong_ke(ra),
               "tong_log": None, "exit_tu_khai": 0, "khop_exit": True}
        dat, ly = phan_quyet(tot)
        print("\n  [(e1)] bản đo TỐT tổng hợp (thoát 0 · TỔNG=7): %s — %s"
              % ("ĐẠT" if dat else "ĐỎ", ly))
        self.assertTrue(dat, "luật phán ĐỎ trên một bản đo TỐT ⇒ cổng đỏ mù: %s" % ly)
        self.assertIn("7 ca", ly)
        # Và đối chứng dương thứ hai: lệch HAI KÊNH phải bị bắt (nếu không, kênh thứ hai là trang trí).
        lech = dict(tot, tong_log={"nguon": "dòng tổng kết của bộ đo", "dat": 9, "hong": 0,
                                   "bo_qua": 0, "khuyet": 0, "tong": 9})
        dat2, ly2 = phan_quyet(lech)
        print("  [(e2)] hai kênh LỆCH nhau (7 vs 9): %s — %s" % ("ĐẠT" if dat2 else "ĐỎ", ly2))
        self.assertFalse(dat2, "hai kênh lệch nhau mà cổng vẫn ĐẠT ⇒ kênh độc lập là trang trí")
        self.assertIn("HAI KÊNH LỆCH", ly2)

    # ── (z) KHÔNG ĐỂ LẠI RÁC ──────────────────────────────────────────────────────────────────
    def test_z1_khong_de_lai_ban_sao_nao(self):
        """Bản sao tiêm lỗi phải bị xoá; cây nguồn không được dính rác của phép đo."""
        con = sorted(d for d in os.listdir(THU_MUC_RUNNER) if d.startswith(".tam_tiem_loi_"))
        print("\n  [(z)] bản sao còn lại trong %s: %s" % (THU_MUC_RUNNER, con or "KHÔNG CÓ"))
        self.assertEqual([], con, "còn rác bản sao tiêm lỗi: %s" % con)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. ĐIỀU KHIỂN — tự kiểm trước, rồi chạy runner thật, rồi trả ĐÚNG mã thoát của runner
# ══════════════════════════════════════════════════════════════════════════════════════════════

class _Tee:
    """Ghi ra stdout THẬT và ĐỒNG THỜI giữ lại bản sao.

    Cần bản sao để cuối lượt cổng TỰ ĐỌC LẠI toàn bộ output của chính nó và kiểm khuôn báo cáo
    (xem `THEO_KHUON` ở cuối `main()`). Không có nó thì "dòng khuôn cuối cùng là số thật" chỉ là
    một LỜI HỨA trong docstring — mà lời hứa thì người sau không kiểm được.
    """

    def __init__(self, that):
        self.that = that
        self.dem = []

    def write(self, s):
        self.dem.append(s)
        return self.that.write(s)

    def flush(self):
        return self.that.flush()

    def isatty(self):
        return False


def main():
    _goc_stdout = sys.stdout
    tee = _Tee(_goc_stdout)
    sys.stdout = tee
    print("═" * 84)
    print("G21/AG-04 — CỔNG TỔNG HỢP: gọi runner thật và trả về ĐÚNG mã thoát của runner")
    print("  cây    : %s" % GOC)
    print("  HEAD   : %s" % _head())
    print("  runner : %s" % os.path.relpath(RUNNER, GOC))
    print("  mã thoát riêng của CỔNG: %d không chạy được · %d quá hạn · %d 0 ca · %d tự kiểm hỏng"
          % (MA_KHONG_CHAY_DUOC, MA_QUA_HAN, MA_KHONG_CO_CA, MA_TU_KIEM_HONG))
    print("═" * 84)

    print("\n── PHẦN 1/2: TỰ KIỂM CỔNG (tiêm lỗi THẬT vào bản sao của runner) ──")
    kq_tk = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(T_CongCoRang))
    tu_kiem_dat = kq_tk.wasSuccessful()
    print("\n  [tự kiểm] %d ca · hỏng=%d · lỗi=%d ⇒ %s"
          % (kq_tk.testsRun, len(kq_tk.failures), len(kq_tk.errors),
             "ĐẠT" if tu_kiem_dat else "HỎNG"))
    don_dep()

    print("\n── PHẦN 2/2: CHẠY RUNNER THẬT (đối chứng DƯƠNG của chính cổng) ──")
    print("  $ sh %s\n" % os.path.relpath(RUNNER, GOC))
    kq = do_runner(RUNNER)
    if kq["ra"]:
        print(kq["ra"].rstrip())
    dat, ly = phan_quyet(kq)

    tk = kq["tong_stdout"] or {}
    tl = kq["tong_log"] or {}
    quyet, ten_quyet = (kenh_so_ca(kq) if kq["chay_duoc"]
                        else ({"tong": 0, "dat": 0, "bo_qua": 0}, "không chạy được"))
    print("\n" + "─" * 84)
    print("  BẢNG BẰNG CHỨNG — CỔNG TỔNG HỢP G19 (G21/AG-04)")
    print("─" * 84)
    print("  runner                                 : %s" % os.path.relpath(RUNNER, GOC))
    print("  chạy được                              : %s%s"
          % (kq["chay_duoc"], "" if kq["chay_duoc"] else " — " + kq["ly_do_khong_chay"]))
    print("  mã thoát TIẾN TRÌNH runner             : %s" % kq["ma"])
    print("  mã thoát runner TỰ KHAI (EXIT_BO_DO)   : %s%s"
          % (kq["exit_tu_khai"], "" if kq["khop_exit"] is not False else "  ← LỆCH!"))
    print("  kênh 1 (stdout runner)                 : TỔNG=%s · ĐẠT=%s · HỎNG=%s · BỎ QUA=%s "
          "· KHUYẾT=%s (%s)" % (tk.get("tong", 0), tk.get("dat", 0), tk.get("hong", 0),
                                tk.get("bo_qua", 0), tk.get("khuyet", 0), tk.get("nguon", "?")))
    print("  kênh 2 (tệp log, mtime trong lượt này): %s" % (
        "TỔNG=%s (%s)" % (tl.get("tong"), tl.get("nguon")) if tl else "không tính được"))
    print("  KÊNH QUYẾT ĐỊNH số ca                  : %s ⇒ TỔNG=%s · ĐẠT=%s · BỎ QUA=%s"
          % (ten_quyet, quyet.get("tong", 0), quyet.get("dat", 0), quyet.get("bo_qua", 0)))
    print("  thời gian                              : %.1f giây" % kq["giay"])
    print("  log                                    : %s" % (kq["log"] or "(không thấy)"))
    print("  PHÁN QUYẾT CỔNG                        : %s — %s" % ("ĐẠT" if dat else "ĐỎ", ly))

    if not tu_kiem_dat:
        ma_cong = MA_TU_KIEM_HONG
        print("  MÃ THOÁT CỔNG                          : %d  ← TỰ KIỂM HỎNG: cổng không đáng tin "
              "thì không được xanh" % ma_cong)
    elif not kq["chay_duoc"]:
        ma_cong = MA_KHONG_CHAY_DUOC
        print("  MÃ THOÁT CỔNG                          : %d  ← runner KHÔNG CHẠY ĐƯỢC"
              % ma_cong)
    elif kq["ma"] != 0:
        ma_cong = kq["ma"]
        print("  MÃ THOÁT CỔNG                          : %d  ← NGUYÊN VĂN mã thoát của runner"
              % ma_cong)
    elif not dat:
        ma_cong = MA_KHONG_CO_CA
        print("  MÃ THOÁT CỔNG                          : %d  ← runner thoát 0 nhưng 0 ca ĐO THẬT "
              "(đây là chỗ DUY NHẤT cổng siết chặt hơn runner)" % ma_cong)
    else:
        ma_cong = 0
        print("  MÃ THOÁT CỔNG                          : 0  ← trùng mã thoát của runner")
    print("─" * 84)
    if ma_cong == 0:
        print("  KẾT LUẬN: %s ca ĐO THẬT · cổng ĐẠT · bộ chạy chung ghi nhận bộ này là ĐẠT."
              % quyet.get("tong", 0))
    else:
        print("  KẾT LUẬN: cổng ĐỎ (mã thoát %d) — bộ chạy chung sẽ ghi nhận bộ này là HỎNG."
              % ma_cong)
    print("─" * 84)

    # ── TỰ KIỂM KHUÔN BÁO CÁO CỦA CHÍNH CỔNG NÀY ─────────────────────────────────────────────
    # Vì sao cần: bộ đếm `chay_tat_ca.sh` lấy `Ran [0-9]+` CUỐI CÙNG, còn `C5`/`G7` lấy phần tử
    # cuối của `re.findall(r"Ran (\d+) tests?")`. Nếu BẤT KỲ dòng nào chứa khuôn đó xuất hiện
    # SAU dòng tổng kết thật của `unittest`, hai bộ đếm kia đọc một con số KHÔNG DO PHÉP ĐO SINH
    # RA. Đó là một lỗi im lặng: output vẫn trông bình thường. Nên cổng TỰ ĐỌC LẠI toàn bộ
    # stdout của chính nó và khẳng định con số cuối cùng đúng bằng số ca tự kiểm thật.
    sys.stdout = _goc_stdout
    _toan_bo = "".join(tee.dem)
    _m = re.findall(r"Ran (\d+) tests?", _toan_bo)
    _cuoi = int(_m[-1]) if _m else -1
    _theo_khuon = (_cuoi == kq_tk.testsRun and kq_tk.testsRun > 0)
    print("  TỰ KIỂM KHUÔN BÁO CÁO: %d lần khớp `Ran <số> tests?` · lần CUỐI = %s · số ca tự kiểm "
          "thật = %d ⇒ %s" % (len(_m), _cuoi if _m else "KHÔNG CÓ", kq_tk.testsRun,
                              "KHỚP" if _theo_khuon else "LỆCH"))
    if not _theo_khuon:
        ma_cong = MA_TU_KIEM_HONG
        print("  MÃ THOÁT CỔNG                          : %d  ← KHUÔN BÁO CÁO HỎNG: bộ đếm sẽ đọc "
              "sai số ca, nên cổng không được phép xanh" % ma_cong)
    print("─" * 84)
    return ma_cong


if __name__ == "__main__":
    try:
        MA = main()
    finally:
        sys.stdout = sys.__stdout__      # trả stdout về thật, kể cả khi cổng NỔ giữa chừng
        don_dep()
    sys.exit(MA)
