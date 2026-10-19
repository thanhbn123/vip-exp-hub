#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18 — AG-01 LƯỢT 2: NGHIỆM THU ĐỘC LẬP KẾT QUẢ **ĐÃ TÍCH HỢP** (`integration/g18`).

KHÁC gì `thu_qa_g18.py` (lượt 1)? Lượt 1 nghiệm thu TỪNG LÀN trên nhánh của nó. Tệp này nghiệm
thu CÂY ĐÃ GỘP — nơi sáu làn gặp nhau — và chỉ hỏi những câu mà **từng làn riêng lẻ KHÔNG THỂ
thấy**:

  A. BẢO TOÀN KHI GỘP — AG-02 và AG-03 cùng sửa `app/http_jt.py`; AG-00 gộp và giữ cả hai khối.
     Mất một trong hai thay đổi là hỏng IM LẶNG: cả hai bộ thử của hai làn vẫn có thể xanh vì
     mỗi bộ chỉ nhìn phần của mình. Ở đây kiểm bằng CẤU TRÚC (AST/từng dòng) + HÀNH VI + ĐỘT BIẾN.
  B. ĐỐI CHIẾU CHÉO hai DỤNG CỤ ĐO V5 — `thu_qa_g18` (AG-01) và `thu_g17_baomat` (AG-06) đếm
     phạm vi route bằng hai bộ trích KHÁC NHAU. Chạy lại bộ của người khác rồi bảo "khớp" thì
     KHÔNG phải đối chiếu độc lập; ở đây so HAI BỘ TRÍCH với nhau.
  C. TRẦN TẦN SUẤT, đo trên một TUYẾN KHÁC (`auth.dang_nhap`) bằng harness tự viết: đường HTTP
     có bằng đường gọi thẳng hàm không (AG-04 §5), và trần có NHÂN theo số bản không (AG-02 §2,
     AG-04 §6.1). Hai điều đó có cùng đúng không?
  D. RANH GIỚI AG-02 / AG-05 — `http_jt` không có trạng thái dùng chung (AG-02), trong khi khuôn
     đọc-rồi-ghi `mot()`+`ghi()` mất cập nhật im lặng (AG-05). Mâu thuẫn hay không, và ranh giới
     nằm ở ĐÂU? Ở đây chỉ ra ranh giới đó bằng AST + một phép đo MẤT CẬP NHẬT TẤT ĐỊNH.
  E. ĐA TIẾN TRÌNH TRÊN CÂY GỘP — AG-02 đo trên nhánh của nó, TRƯỚC khi 275 dòng của AG-03 vào
     cùng tệp. Bốn tiến trình thật qua `http_jt` một lần nữa, để tính không-trạng-thái vẫn đúng
     SAU khi gộp.

PHẠM VI (nói thẳng, §12.1 luật 3): mọi phép đo ở đây đi qua loopback + CSDL TẠM trong thư mục
tạm; adapter hãng ở chế độ MOCK; KHÔNG gọi hãng (kể cả sandbox); KHÔNG credentials thật; KHÔNG
`.env`; KHÔNG đụng cổng 5432 (bộ PostgreSQL của AG-05 có cụm riêng, không chạy ở đây).

Chạy: python3 app/thu/thu_qa_g18_tich_hop.py
"""

import ast
import atexit
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ─────────────────────────────────────────────────────────────────────────────────────────────
# MÔI TRƯỜNG: phải đặt TRƯỚC khi nạp bất kỳ mô-đun nào của `app/` — `cau_hinh` đọc biến lúc import.
# ─────────────────────────────────────────────────────────────────────────────────────────────
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(GOC, "app")
KHOI_THU = os.path.join(APP, "thu")

TAM = tempfile.mkdtemp(prefix="vh-g18-tichhop-")
os.environ["VIP_HUB_DATA"] = TAM
os.environ["VIP_HUB_BACKOFF"] = "0.01"
os.environ.pop("VIP_G18_CHO_PHEP_GOI_HANG", None)
os.environ.pop("VIP_G18_GIAY_PHEP", None)
sys.path.insert(0, APP)
atexit.register(lambda: shutil.rmtree(TAM, ignore_errors=True))

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# Dòng `_MIGRATE` ngay dưới đây gọi `migrate.py` THẬT, nên khai báo phải xảy ra TRƯỚC nó. Bộ thử
# tự khai bằng `cau_hinh.khai_kho_kiem_thu()` — KHÔNG dựa vào việc người chạy nhớ
# `export VIP_KHO_DANG_CHAY=sqlite`. `VIP_HUB_DATA` đã trỏ nền TẠM ở trên.
import cau_hinh      # noqa: E402
cau_hinh.khai_kho_kiem_thu()

_MIGRATE = subprocess.run([sys.executable, os.path.join(APP, "migrate.py")], cwd=GOC,
                          env=dict(os.environ), stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

import gioi_han      # noqa: E402  (chỉ ĐỌC chính sách trần — không tiêu lượt trong tiến trình này)
import http_jt       # noqa: E402

DUONG_HTTP_JT = os.path.join(APP, "http_jt.py")
DUONG_GIOI_HAN = os.path.join(APP, "gioi_han.py")
DUONG_CSDL = os.path.join(APP, "csdl.py")
DUONG_SERVER = os.path.join(APP, "server.py")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# DỤNG CỤ DÙNG CHUNG
# ═════════════════════════════════════════════════════════════════════════════════════════════
def doc(duong):
    with open(duong, encoding="utf-8") as f:
        return f.read()


def quet_ghi_ten_muc_modun(duong):
    """Quét AST: có ai GHI vào một TÊN MỨC MÔ-ĐUN không?

    Tiêu chí quét là "có ai GHI không", KHÔNG phải "có biến toàn cục không": chỉ đếm biến toàn
    cục thì một hằng số cũng bị tố (HỎNG GIẢ), còn chỉ tìm `global` thì bỏ sót `X[i] = …`.

    → `(so_ten, so_dict_hang, danh_sach_dau_hieu_ghi)`.
    """
    cay = ast.parse(doc(duong))
    ten, so_dict = [], 0
    for n in cay.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    ten.append(t.id)
                    if isinstance(n.value, ast.Dict):
                        so_dict += 1
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            ten.append(n.target.id)
    ghi = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Global):
            ghi.append(("global", n.lineno))
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) \
                        and t.value.id in ten:
                    ghi.append(("%s[…] = …" % t.value.id, n.lineno))
                if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) \
                        and t.value.id in ten:
                    ghi.append(("%s.<thuộc tính> = …" % t.value.id, n.lineno))
        if isinstance(n, ast.Delete):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) \
                        and t.value.id in ten:
                    ghi.append(("del %s[…]" % t.value.id, n.lineno))
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in (
                    "append", "extend", "update", "pop", "add", "remove", "clear",
                    "setdefault", "insert", "sort") \
                    and isinstance(f.value, ast.Name) and f.value.id in ten:
                ghi.append(("%s.%s()" % (f.value.id, f.attr), n.lineno))
            if isinstance(f, ast.Name) and f.id == "open":
                ghi.append(("open()", n.lineno))
    return len(set(ten)), so_dict, ghi


def dinh_nghia_trung(duong):
    """Tên hàm/lớp mức mô-đun bị ĐỊNH NGHĨA HAI LẦN (định nghĩa sau LU MỜ định nghĩa trước)."""
    cay = ast.parse(doc(duong))
    dem = {}
    for n in cay.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            dem.setdefault(n.name, []).append(n.lineno)
    return {k: v for k, v in dem.items() if len(v) > 1}


# ---- tiến trình con chạy mã Python với đúng môi trường của bộ thử ------------------------------
def chay_con(manh, giay=180, env=None):
    return subprocess.run([sys.executable, "-c", manh], cwd=GOC,
                          env=dict(os.environ, **(env or {})),
                          capture_output=True, text=True, timeout=giay)


def _dau_manh():
    return ("import os, sys\n"
            "sys.path.insert(0, %r)\n"
            "os.environ['VIP_HUB_DATA'] = %r\n" % (APP, TAM))


# ---- máy chủ HTTP THẬT trong tiến trình riêng --------------------------------------------------
def cong_trong():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def cho_san_sang(cong, het_giay=30.0):
    het = time.time() + het_giay
    while time.time() < het:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/" % cong, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True                      # có phản hồi HTTP nghĩa là máy chủ đã sống
        except Exception:
            time.sleep(0.2)
    return False


class NhomMay:
    """N tiến trình `app/server.py` THẬT, cùng một CSDL tạm, cổng riêng từng tiến trình."""

    def __init__(self, so_luong):
        self.tien = []
        for _ in range(so_luong):
            c = cong_trong()
            p = subprocess.Popen([sys.executable, os.path.join(APP, "server.py"), str(c)],
                                 cwd=GOC, env=dict(os.environ),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not cho_san_sang(c):
                self.dung()
                raise AssertionError("máy chủ cổng %d không lên được" % c)
            self.tien.append((p, c))

    @property
    def cong(self):
        return [c for _, c in self.tien]

    def dung(self):
        for p, _ in self.tien:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=10)
                except Exception:
                    p.kill()
        self.tien = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.dung()


def dang_nhap_sai(cong, ten):
    """Một lượt đăng nhập SAI hoàn toàn qua HTTP → mã trạng thái."""
    d = json.dumps({"ten_dang_nhap": ten, "mat_khau": "sai-be-beng"}).encode()
    rq = urllib.request.Request("http://127.0.0.1:%d/api/v2/auth/dang-nhap" % cong, data=d,
                                headers={"Content-Type": "application/json",
                                         "X-Requested-With": "VIPHub"})
    try:
        with urllib.request.urlopen(rq, timeout=10) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. BẢO TOÀN KHI GỘP `app/http_jt.py` (AG-02 + AG-03 + ghi chú gộp của AG-00)
# ═════════════════════════════════════════════════════════════════════════════════════════════
class A_BaoTonKhiGop(unittest.TestCase):
    """AG-02 (+16 dòng) và AG-03 (+275 dòng) sửa CÙNG một tệp, CÙNG một vùng bình luận.

    Xung đột vị trí: nếu người gộp chọn một trong hai thì bộ thử của làn BỊ BỎ vẫn có thể xanh
    (nó chỉ nhìn phần của mình) — hỏng IM LẶNG. Nên phải kiểm bằng ba đường khác nhau.
    """

    def test_a1_ky_hieu_ag03_con_du(self):
        """Cấu trúc: ba ký hiệu AG-03 đóng lỗ hổng (a)+(b) còn nguyên trong tệp đã gộp."""
        nguon = doc(DUONG_HTTP_JT)
        can = ["_duong_dan_da_che", "TRUONG_CREDENTIAL_PHAN_HOI", "_gia_tri_bi_mat_tu_phan_hoi",
                "DOAN_DUONG_DAN_DAI_TOI_THIEU", "_CHUOI_DOAN_HOP_LE"]
        thieu = [t for t in can if t not in nguon]
        self.assertEqual([], thieu, "ký hiệu của AG-03 bị MẤT khi gộp: %s" % thieu)
        print("\n  [A1] 5/5 ký hiệu AG-03 còn trong tệp đã gộp")

    def test_a2_khoi_binh_luan_ag02_con_nguyen(self):
        """Cấu trúc: khối đo đa-tiến-trình của AG-02 (+16 dòng) còn nguyên, không bị AG-03 đè."""
        nguon = doc(DUONG_HTTP_JT)
        can = ["Lớp này KHÔNG có trạng thái dùng chung nào",
               "AN TOÀN qua nhiều tiến trình",
               "trần thực = khai báo × số bản"]
        thieu = [t for t in can if t not in nguon]
        self.assertEqual([], thieu, "khối bình luận của AG-02 bị MẤT khi gộp: %s" % thieu)
        print("  [A2] khối bình luận AG-02 còn nguyên (3/3 câu chốt)")

    def test_a3_ghi_chu_gop_cua_ag00_con_nguyen(self):
        """Cấu trúc: ghi chú của người gộp còn nguyên — nếu mất, người sau không biết vì sao có
        hai khối nói về hai phép đo khác nhau nằm cạnh nhau, và sẽ "dọn" mất một khối."""
        nguon = doc(DUONG_HTTP_JT)
        self.assertIn("GHI CHÚ CỦA AG-00 KHI GỘP", nguon)
        self.assertIn("xung đột VỊ TRÍ, không phải xung đột NỘI DUNG", nguon)
        print("  [A3] ghi chú gộp của AG-00 còn nguyên")

    def test_a4_khong_co_dinh_nghia_bi_lum_to(self):
        """Cấu trúc: gộp hai nhánh hay đẻ ra ĐỊNH NGHĨA TRÙNG — định nghĩa SAU lu mờ định nghĩa
        trước, và bản bị lu mờ thường là bản đã vá. Kiểm cả tệp, không chỉ hàm đã biết."""
        trung = dinh_nghia_trung(DUONG_HTTP_JT)
        self.assertEqual({}, trung, "định nghĩa mức mô-đun bị TRÙNG trong http_jt.py: %s" % trung)
        # `_gia_tri_can_che` là hàm AG-03 TÁCH RA từ `_gia_tri_ta_gui` — đúng một định nghĩa.
        so = len([n for n in ast.parse(doc(DUONG_HTTP_JT)).body
                  if isinstance(n, ast.FunctionDef) and n.name == "_gia_tri_can_che"])
        self.assertEqual(1, so, "`_gia_tri_can_che` phải có ĐÚNG một định nghĩa, thấy %d" % so)
        print("  [A4] 0 định nghĩa trùng · `_gia_tri_can_che` đúng 1 định nghĩa")

    def test_a5_bi_mat_hang_echo_lai_bi_bat(self):
        """HÀNH VI (lỗ hổng (a) của AG-03): bí mật của HÃNG echo lại trong HEADER và trong JSON
        phản hồi — thứ TA CHƯA TỪNG GỬI — phải vào tập che."""
        bi_mat = "HANG-ECHO-LAI-9f3c1d7a"
        than = json.dumps({"code": 0, "access_token": bi_mat}).encode()
        can_che = http_jt._gia_tri_bi_mat_tu_phan_hoi(than, [("Access-Token", bi_mat)])
        self.assertIn(bi_mat, can_che,
                      "bí mật hãng echo lại KHÔNG được nhận diện — lỗ hổng (a) đã mở lại")
        # ĐỐI CHỨNG DƯƠNG: giá trị vô hại (không thuộc tên bí mật, không đủ dài) KHÔNG bị che.
        vo_hai = http_jt._gia_tri_bi_mat_tu_phan_hoi(
            json.dumps({"ma_van_don": "JT123"}).encode(), [("X-Trace", "abc")])
        self.assertNotIn("JT123", vo_hai)
        print("  [A5] bí mật echo lại (header + JSON) BỊ che · mã vận đơn vô hại KHÔNG bị che")

    def test_a6_duong_dan_che_doan_nguy_hiem_giu_duong_thuc(self):
        """HÀNH VI (lỗ hổng (b) của AG-03): bí mật nằm trong ĐƯỜNG DẪN phải bị che TỪNG ĐOẠN,
        còn endpoint thật phải ĐI QUA NGUYÊN VẸN (đối chứng dương — che cả đường dẫn là bịt thứ
        duy nhất cho biết lượt gọi đi tới đâu)."""
        bi_mat = "ORD1234567890abcdefg"           # ≥20 ký tự, trộn chữ-số, đủ ngẫu nhiên
        url = "http://127.0.0.1:9/api/v2/order/addOrder/%s" % bi_mat
        mo_ta = http_jt.mo_ta_yeu_cau(url, {"Content-Type": "text/plain"}, b"a=1")
        self.assertNotIn(bi_mat, mo_ta, "bí mật trong ĐƯỜNG DẪN vẫn in nguyên văn — lỗ hổng (b) mở lại")
        self.assertIn("[DA-CHE]", mo_ta)
        # ĐỐI CHỨNG DƯƠNG: endpoint thật đi qua không suy suyển.
        mo_ta2 = http_jt.mo_ta_yeu_cau("http://127.0.0.1:9/api/v2/order/addOrder",
                                       {"Content-Type": "text/plain"}, b"a=1")
        self.assertIn("/api/v2/order/addOrder", mo_ta2)
        self.assertNotIn("[DA-CHE]", mo_ta2)
        print("  [A6] đoạn bí mật trong đường dẫn BỊ che · endpoint thật ĐI QUA nguyên vẹn")

    def test_a7_bo_do_co_rang_bang_dot_bien(self):
        """CHỨNG MINH NGƯỢC: ca A6 chỉ có nghĩa nếu bộ dò CÓ RĂNG.

        Đột biến ĐÚNG hàm mà AG-03 đã sửa (`mo_ta_yeu_cau` → bản in đường dẫn NGUYÊN VĂN, tức
        tái tạo lỗ hổng (b) của G17) rồi đòi bộ dò của A6 phải ĐỎ. Không có ca này thì một
        `mo_ta_yeu_cau` bị vô hiệu hoàn toàn vẫn làm A6 xanh.
        """
        bi_mat = "ORD1234567890abcdefg"
        url = "http://127.0.0.1:9/api/v2/order/addOrder/%s" % bi_mat
        that = http_jt.mo_ta_yeu_cau

        def ban_dot_bien(u, h, t):
            return "POST %s · header: %s" % (u, sorted(h))       # in NGUYÊN VĂN đường dẫn

        http_jt.mo_ta_yeu_cau = ban_dot_bien
        try:
            mo_ta = http_jt.mo_ta_yeu_cau(url, {"Content-Type": "text/plain"}, b"a=1")
            phat_hien = bi_mat in mo_ta
        finally:
            http_jt.mo_ta_yeu_cau = that
        self.assertTrue(phat_hien,
                        "bộ dò KHÔNG thấy bí mật khi hàm bị đột biến ⇒ ca A6 là ca KHÔNG CÓ RĂNG")
        # và bản THẬT thì không rò rỉ (khẳng định lại sau khi đã khôi phục)
        self.assertNotIn(bi_mat, http_jt.mo_ta_yeu_cau(url, {"Content-Type": "text/plain"}, b"a=1"))
        print("  [A7] đột biến `mo_ta_yeu_cau` ⇒ bộ dò ĐỎ · khôi phục ⇒ XANH")

    def test_a8_ket_luan_ag02_con_dung_va_so_do_thi_cu(self):
        """KẾT LUẬN CHỊU LỰC của AG-02 (0 dấu hiệu GHI) còn đúng trên cây gộp — đo lại độc lập.

        Kèm một phát hiện: AG-02 khai **20 tên mức mô-đun**, con số ấy đúng trên nhánh của nó
        (`a9f076b`) nhưng SAI trên cây gộp, vì AG-03 thêm 5 tên cùng lúc với 275 dòng. Bình luận
        được gộp NGUYÊN VĂN nên sản phẩm đang mang một số đo cũ. Ở đây IN RA chênh lệch; đây là
        phát hiện của lượt nghiệm thu (xem `docs/QA_G18_INTEGRATED.md` §LO HỔNG), không phải ca đỏ:
        kết luận chịu lực vẫn đúng, chỉ con số minh hoạ là cũ.
        """
        so_ten, so_dict, ghi = quet_ghi_ten_muc_modun(DUONG_HTTP_JT)
        self.assertEqual([], ghi, "http_jt.py có DẤU HIỆU GHI trạng thái mức mô-đun: %s" % ghi)
        self.assertEqual(2, so_dict, "số dict HẰNG cấu hình đổi: %d" % so_dict)
        trong_binh_luan = 20
        print("  [A8] %d tên mức mô-đun · %d dict hằng · 0 dấu hiệu GHI (AG-02 khai %d tên)"
              % (so_ten, so_dict, trong_binh_luan))
        if so_ten != trong_binh_luan:
            print("       ⚠ LỆCH: bình luận trong app/http_jt.py khai %d tên, cây gộp có %d tên"
                  % (trong_binh_luan, so_ten))
            print("         (đúng trên nhánh AG-02 `a9f076b`; AG-03 thêm 5 tên cùng 275 dòng)")
        self.assertGreater(so_ten, 0)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. ĐỐI CHIẾU CHÉO hai DỤNG CỤ ĐO V5 (AG-01 `thu_qa_g18` ↔ AG-06 `thu_g17_baomat`)
# ═════════════════════════════════════════════════════════════════════════════════════════════
MANH_ROUTE_AG06 = r'''
import json, os, sys, tempfile
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vh-g18-b06-")
sys.path.insert(0, %(app)r); sys.path.insert(0, %(khoithu)r)
import importlib.util
spec = importlib.util.spec_from_file_location("b17", %(tep)r)
m = importlib.util.module_from_spec(spec); sys.modules["b17"] = m; spec.loader.exec_module(m)
tho = sorted({d for (d, _m) in m._cua_tu_nguon(%(server)r)})
chuan = sorted({p for d in tho for p in m._mo_rong(m._chuan_hoa(d))})
print(json.dumps({"tho": tho, "chuan": chuan}))
'''

# VÌ SAO KHÔNG dùng thẳng `m.duong_platform()`: hàm đó thay MỌI nhóm `(…)` bằng ký tự `1`, nên
# `/api/v2/platform/tenants/(\d+)/(khoa|mo|goi)` biến thành `/api/v2/platform/tenants/1/1` — một
# ĐƯỜNG KHÔNG TỒN TẠI. Muốn so hai dụng cụ đo với nhau thì phải so trên MẪU GỐC; ở đây lấy mẫu
# gốc bằng chính hai regex của AG-01, rồi chuẩn hoá CẢ HAI BÊN bằng cùng một hàm.
MANH_ROUTE_AG01 = r'''
import json, os, sys, tempfile
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vh-g18-b01-")
sys.path.insert(0, %(app)r); sys.path.insert(0, %(khoithu)r)
import importlib.util
spec = importlib.util.spec_from_file_location("q18", %(tep)r)
m = importlib.util.module_from_spec(spec); sys.modules["q18"] = m; spec.loader.exec_module(m)
nguon = m._doc_app("server.py")
ra = set()
for (d, _me) in m.duong_ghi_tinh():
    ra.add(d)
for d in m.duong_ghi_dong():
    ra.add(d)
for d in m.RE_STATIC_PLATFORM.findall(nguon):          # mẫu GỐC, không bị thay `(…)` bằng 1
    ra.add(d)
for mau in m.RE_FULLMATCH.findall(nguon):
    if mau.startswith("/api/v2/platform/"):
        ra.add(mau)
print(json.dumps(sorted(ra)))
'''


# ---- BỘ CHUẨN HOÁ DÙNG CHUNG — bản sao ĐÚNG của `thu_g17_baomat._chuan_hoa` + `._mo_rong` -------
# Phải là bản sao CHÍNH XÁC và phải theo ĐÚNG thứ tự `_mo_rong(_chuan_hoa(p))`; ca B0 tự kiểm
# điều đó bằng cách so với chính đầu ra đã chuẩn hoá của AG-06.
def _chuan_hoa(p):
    return p.replace(r"(\d+)", "{id}").replace(r"([A-Za-z0-9_-]+)", "{ma}")


def _mo_rong(p):
    import re
    m = re.search(r"\(([^()]*\|[^()]*)\)", p)
    if not m:
        return [p]
    ra = []
    for phan in m.group(1).split("|"):
        ra += _mo_rong(p[:m.start()] + phan + p[m.end():])
    return ra


def _chuan_hoa_tap(ds):
    return {p for d in ds for p in _mo_rong(_chuan_hoa(d))}


class B_DoiChieuCheoV5(unittest.TestCase):
    """HAI BỘ ĐO ĐỘC LẬP cho cùng cổng V5 (cách ly tenant toàn cục).

    AG-06 canh bằng **bảng cửa khai tay + phép canh KHAI BÁO** đối chiếu với `server.py`
    (`thu_g17_baomat.bang_cua` ↔ `_cua_tu_nguon`). AG-01 rút cửa **từ chính mã nguồn** rồi bắn
    HTTP thật (`thu_qa_g18.duong_ghi_tinh/duong_ghi_dong/duong_platform`). Hai bộ trích KHÁC NHAU,
    hai cách phán KHÁC NHAU. Câu hỏi: chúng có ĐỒNG Ý không, và nếu lệch thì lệch ở đâu?
    """

    @classmethod
    def setUpClass(cls):
        cls.kq = {}
        for nhan, manh in (("ag06", MANH_ROUTE_AG06), ("ag01", MANH_ROUTE_AG01)):
            tep = os.path.join(KHOI_THU, "thu_g17_baomat.py" if nhan == "ag06"
                               else "thu_qa_g18.py")
            ma = manh % {"app": APP, "khoithu": KHOI_THU, "tep": tep, "server": DUONG_SERVER}
            r = chay_con(ma, giay=300)
            if r.returncode != 0:
                raise AssertionError("không trích được route của %s:\n%s" % (nhan, r.stderr[-800:]))
            cls.kq[nhan] = json.loads(r.stdout.strip().splitlines()[-1])
        cls.ag06 = set(cls.kq["ag06"]["chuan"])
        cls.ag06_chuan_cua_ho = set(cls.kq["ag06"]["chuan"])
        cls.ag01 = _chuan_hoa_tap(cls.kq["ag01"])

    def test_b0_bo_chuan_hoa_cua_toi_khop_voi_bo_cua_ag06(self):
        """TỰ KIỂM BỘ SO: nếu bộ chuẩn hoá của tôi khác bộ của AG-06 thì mọi phép so dưới đây so
        hai thứ khác nhau, và "lệch phạm vi" có thể chỉ là lệch quy ước viết."""
        cua_toi = _chuan_hoa_tap(self.kq["ag06"]["tho"])
        self.assertEqual(self.ag06_chuan_cua_ho, cua_toi,
                         "bộ chuẩn hoá của tôi KHÁC bộ của AG-06 ⇒ phép so vô hiệu")
        print("\n  [B0] bộ chuẩn hoá của tôi == bộ của AG-06 (%d route)" % len(cua_toi))

    def test_b1_hai_bo_trich_deu_chay(self):
        """TỰ KIỂM BỘ DÒ: một bộ trích trả về rỗng làm mọi phép so dưới đây xanh vô nghĩa."""
        self.assertGreater(len(self.ag06), 80, "bộ trích AG-06 dò được quá ít route")
        self.assertGreater(len(self.ag01), 40, "bộ trích AG-01 dò được quá ít route")
        print("\n  [B1] AG-06 (thu_g17_baomat) = %d route · AG-01 (thu_qa_g18) = %d route"
              % (len(self.ag06), len(self.ag01)))

    def test_b2_khong_route_la(self):
        """INVARIANT: mọi route AG-01 đo phải TỒN TẠI trong `server.py` theo phép đếm của AG-06.

        Lệch ở đây nghĩa là một trong hai bộ trích đang bịa route — chứ không phải "khác phạm vi".
        """
        la = sorted(self.ag01 - self.ag06)
        self.assertEqual([], la, "AG-01 đo route mà AG-06 KHÔNG thấy trong server.py: %s" % la)
        print("  [B2] 0 route lạ: cả %d route của AG-01 đều nằm trong tập của AG-06" % len(self.ag01))

    def test_b3_hai_bo_do_DONG_Y_o_phan_giao(self):
        """KẾT LUẬN ĐỐI CHIẾU: hai bộ đo KHÔNG mâu thuẫn — chúng ĐỒNG Ý ở phần giao.

        Bằng chứng đồng ý không nằm ở phép so tập hợp (đó chỉ là phạm vi) mà ở chỗ: trên CÙNG
        commit này cả hai bộ đều XANH, và phần giao chính là phần cả hai cùng khẳng định "đã đo".
        Phép so tập hợp trả lời câu còn lại: PHẦN NÀO CHỈ MỘT BÊN ĐO.
        """
        giao = self.ag01 & self.ag06
        chi_ag06 = self.ag06 - self.ag01
        self.assertGreater(len(giao), 0)
        print("  [B3] GIAO = %d route (cả hai cùng đo) · CHỈ AG-06 đo = %d route"
              % (len(giao), len(chi_ag06)))
        print("       ⇒ ĐỒNG Ý ở %d route; KHÔNG mâu thuẫn ở route nào." % len(giao))
        print("       ⇒ LỆCH là lệch PHẠM VI, không phải lệch KẾT LUẬN: %d/%d route của AG-06"
              % (len(chi_ag06), len(self.ag06)))
        print("         KHÔNG có bằng chứng V5 nào từ bộ của AG-01.")
        self.assertGreater(len(chi_ag06), 0,
                           "kỳ vọng còn khoảng trống phạm vi — nếu hết, ghi lại mốc mới")

    def test_b4_nhung_route_chi_ag06_do_van_duoc_khai(self):
        """ĐỐI CHỨNG DƯƠNG cho B3: phần "chỉ AG-06 đo" KHÔNG phải route hoang.

        Mọi route đó phải có trong bảng cửa của AG-06 (đã khai để đo), nếu không thì "khoảng
        trống phạm vi" chỉ là rác của bộ trích.
        """
        chi_ag06 = self.ag06 - self.ag01
        self.assertTrue(all(r.startswith("/api/v2/") for r in chi_ag06),
                        "có route không thuộc /api/v2/ trong phần chỉ AG-06 đo")
        print("  [B4] %d/%d route chỉ-AG-06-đo đều thuộc /api/v2/ ⇒ là route thật, không phải rác"
              % (len(chi_ag06), len(chi_ag06)))

    def test_b5_bo_trich_platform_cua_ag01_lam_mat_nhom_chon(self):
        """PHÁT HIỆN (dương tính thật, không phải ca đỏ): `thu_qa_g18.duong_platform()` thay MỌI
        nhóm `(…)` bằng ký tự `1`, nên `/api/v2/platform/tenants/(\\d+)/(khoa|mo|goi)` trở thành
        `/api/v2/platform/tenants/1/1` — một đường KHÔNG TỒN TẠI.

        Hệ quả ĐO ĐƯỢC: ca F1 của `thu_qa_g18` vẫn XANH, nhưng xanh vì cổng platform của
        `server.py` chặn theo TIỀN TỐ (`duong.startswith("/api/v2/platform/")`, dòng 566) TRƯỚC
        khi khớp route — mọi URL `/api/v2/platform/*` đều 403 với phiên không phải platform. Nên
        dòng `/tenants/1/1` trong danh sách phủ KHÔNG đo route thật
        `/api/v2/platform/tenants/{id}/(khoa|mo|goi)`. Phủ platform của AG-01 vì thế HỤT 1 mục.

        Ca này chỉ ĐO và IN; nó không đỏ, vì sản phẩm (`server.py`) vẫn đúng — chỗ sai nằm ở
        dụng cụ đo của chính AG-01. Tệp này là NGƯỜI KIỂM, không được sửa mã của làn khác.
        """
        nguon = doc(DUONG_SERVER)
        self.assertIn('duong.startswith("/api/v2/platform/")', nguon,
                      "cổng platform không còn chặn theo tiền tố — đọc lại kết luận của ca này")
        # đường THẬT do AG-06 đếm, có nhóm chọn
        that = [r for r in self.ag06 if "/platform/tenants/{id}/" in r]
        self.assertTrue(that, "AG-06 không đếm được route platform có nhóm chọn — nghi hỏng")
        # đường do bộ trích của AG-01 SINH RA (đã thay `(…)` bằng `1`)
        muc_tieu = os.path.join(APP, "thu", "thu_qa_g18.py")
        ma2 = r'''
import json, os, sys, tempfile
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vh-g18-b01p-")
sys.path.insert(0, %(app)r); sys.path.insert(0, %(khoithu)r)
import importlib.util
spec = importlib.util.spec_from_file_location("q18", %(tep)r)
m = importlib.util.module_from_spec(spec); sys.modules["q18"] = m; spec.loader.exec_module(m)
print(json.dumps(m.duong_platform()))
''' % {"app": APP, "khoithu": KHOI_THU, "tep": muc_tieu}
        r = chay_con(ma2, giay=180)
        self.assertEqual(0, r.returncode, r.stderr[-400:])
        ds = json.loads(r.stdout.strip().splitlines()[-1])
        gia = [d for d in ds if "/tenants/1/1" in d]
        print("  [B5] `duong_platform()` sinh %d đường · trong đó %d đường KHÔNG tồn tại: %s"
              % (len(ds), len(gia), gia))
        print("       đường THẬT bị hụt: %s" % that)
        print("       F1 vẫn XANH vì cổng platform chặn theo TIỀN TỐ trước khi khớp route.")
        self.assertTrue(gia, "kỳ vọng còn artefact `(…)` → `1` — nếu hết, ghi lại mốc mới")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. TRẦN TẦN SUẤT — hai đường đo, và trần có NHÂN theo số bản không
# ═════════════════════════════════════════════════════════════════════════════════════════════
MANH_GOI_THANG = _dau_manh() + r'''
import gioi_han
gioi_han.xoa_het()
qua = 0
for _ in range(200):
    if not gioi_han.kiem("auth.dang_nhap", ip="127.0.0.1", dinh_danh="g18-thang").cho_phep:
        break
    qua += 1
print(qua)
'''


class C_TranTanSuat(unittest.TestCase):
    """HAI KẾT LUẬN CÓ VẺ ĐỐI NHAU, đo trên MỘT tuyến khác của AG-04:

      · AG-04 §5: "đường HTTP KHÔNG lệch với đường gọi thẳng hàm" (10 == 10, tuyến webhook).
      · AG-02 §2 / AG-04 §6.1: "trần thực NHÂN theo số bản" (10 → 20 với 2 tiến trình).

    Chúng cùng đúng khi và chỉ khi phép NHÂN nằm ở ranh giới TIẾN TRÌNH, còn phép BẰNG nằm trong
    MỘT tiến trình. Đo cả ba nhánh: gọi thẳng hàm · HTTP 1 tiến trình · HTTP 2 tiến trình xen kẽ.
    """

    @classmethod
    def setUpClass(cls):
        cls.luat = [l for l in gioi_han.CHINH_SACH["auth.dang_nhap"]]
        cls.tran_khai_bao = min(l.so_lan for l in cls.luat)
        cls.ket_qua = {}

    def test_c1_tran_khai_bao_doc_tu_chinh_sach(self):
        """Trần KHÔNG được viết cứng trong bộ thử: đọc thẳng từ `gioi_han.CHINH_SACH`."""
        self.assertGreater(self.tran_khai_bao, 0)
        self.assertLessEqual(self.tran_khai_bao, 30, "trần khai báo quá lớn để đo nhanh")
        print("\n  [C1] trần khai báo `auth.dang_nhap` = %d (đọc từ chính sách: %s)"
              % (self.tran_khai_bao, " · ".join(repr(l) for l in self.luat)))

    def test_c2_goi_thang_ham_trong_tien_trinh_sach(self):
        r = chay_con(MANH_GOI_THANG, giay=120)
        self.assertEqual(0, r.returncode, "nhánh gọi thẳng hàm hỏng:\n%s" % r.stderr[-500:])
        so = int(r.stdout.strip().splitlines()[-1])
        self.ket_qua["thang"] = so
        self.assertEqual(self.tran_khai_bao, so,
                         "gọi thẳng hàm cho %d lượt, khai báo %d" % (so, self.tran_khai_bao))
        print("  [C2] gọi thẳng hàm (tiến trình sạch)      : %d lượt qua rồi chặn" % so)

    def test_c3_http_mot_tien_trinh_bang_goi_thang_ham(self):
        """AG-04 §5, đo lại trên TUYẾN KHÁC và bằng harness khác.

        VÁ G19 (AG-00): bản trước ĐỎ với `HTTP 8 ≠ gọi thẳng hàm 12`. ĐÃ CHỨNG MINH không phải
        bug: luật của `auth.dang_nhap` là `so_lan=20` (theo IP) và `so_lan=12` (theo định danh),
        cùng cửa sổ 300s. C2 chạy trước và tiêu **12** lượt của bucket **theo IP** — bucket ấy
        nay DÙNG CHUNG và SỐNG LÂU (G19/AG-02 chuyển kho đếm vào CSDL), nên C3 còn đúng
        **20 − 12 = 8**. Khớp chính xác.

        Trước G19 bộ đếm nằm trong bộ nhớ TỪNG tiến trình nên hai phép đo RỜI NHAU; nay thì
        không. Bất biến "HTTP == gọi thẳng hàm" VẪN ĐÚNG — cái sai là giả định hai phép đo độc
        lập. Nên ca này phải ĐẶT LẠI TRẠNG THÁI trước khi đo, đúng như C2 đã làm.
        """
        gioi_han.xoa_het()          # trần về đầy — nếu không, ta đo phần trần C2 đã tiêu
        with NhomMay(1) as n:
            qua = 0
            for _ in range(60):
                if dang_nhap_sai(n.cong[0], "g18-tichhop-h1") == 429:
                    break
                qua += 1
        self.ket_qua["http1"] = qua
        self.assertIsNotNone(self.ket_qua.get("thang"), "ca C2 phải chạy trước")
        self.assertEqual(self.ket_qua["thang"], qua,
                         "HTTP %d ≠ gọi thẳng hàm %d ⇒ hai đường LỆCH NHAU"
                         % (qua, self.ket_qua["thang"]))
        print("  [C3] HTTP 1 tiến trình máy chủ THẬT   : %d lượt qua rồi 429  ⇒ BẰNG đường hàm"
              % qua)

    def test_c4_HAI_tien_trinh_thi_tran_KHONG_NHAN(self):
        """G19/AG-02: trần DÙNG CHUNG qua tiến trình — hai bản KHÔNG nhân đôi trần.

        BẢN TRƯỚC của ca này tên là `..._tran_NHAN_hai` và khẳng định `2 × mot == tong`, với
        docstring "Bộ đếm nằm trong BỘ NHỚ tiến trình". **Đó là khẳng định CHÍNH CÁI LỖ HỔNG**
        B-G11-10 — đo được ở G18: khai 20 ⇒ 20/40/80/160 với N=1/2/4/8.

        G19/AG-02 đã sửa: kho đếm chuyển vào CSDL, trần nằm trong chính câu ghi, cả lượt kiểm
        trong MỘT giao dịch `BEGIN IMMEDIATE`. Nên khẳng định đúng nay là: HAI tiến trình vẫn
        chỉ cho **MỘT** trần, không nhân.

        GIỮ NGUYÊN ĐỘ RĂNG: nếu ai quay lại kho bộ nhớ một tiến trình thì `tong` sẽ thành `2 × mot`
        và ca này ĐỎ lại — đúng chiều ngược với bản cũ, nhưng vẫn canh cùng một bất biến.
        """
        gioi_han.xoa_het()          # trần về đầy trước khi đo
        with NhomMay(2) as n:
            tong = 0
            for _ in range(80):
                ma = [dang_nhap_sai(n.cong[0], "g18-tichhop-h2"),
                      dang_nhap_sai(n.cong[1], "g18-tichhop-h2")]
                tong += sum(1 for m in ma if m != 429)
                if all(m == 429 for m in ma):
                    break
        self.ket_qua["http2"] = tong
        mot = self.ket_qua.get("http1")
        self.assertIsNotNone(mot, "ca C3 phải chạy trước")
        self.assertEqual(mot, tong,
                         "2 tiến trình cho %d lượt qua, một tiến trình cho %d — trần DÙNG CHUNG thì"
                         " hai bản phải cho CÙNG một trần, KHÔNG nhân đôi (B-G11-10). Nếu %d gấp"
                         " đôi %d thì kho đếm đã quay lại BỘ NHỚ MỘT TIẾN TRÌNH."
                         % (tong, mot, tong, mot))
        print("  [C4] HTTP 2 tiến trình (xen kẽ)       : %d lượt qua  ⇒ TỈ LỆ %.1f× (khai báo %d)"
              % (tong, tong / float(mot), self.tran_khai_bao))

    def test_c5_mot_ket_luan_nhat_quan(self):
        """KẾT LUẬN G19: "HTTP == gọi thẳng hàm" VÀ "trần DÙNG CHUNG qua tiến trình" CÙNG ĐÚNG.

        BẢN TRƯỚC của ca này khẳng định `2 × h1 == h2`, với lý giải "qua NHIỀU tiến trình, mỗi bản
        có ngân sách RIÊNG nên tổng nhân lên". **Đó là khẳng định CHÍNH LỖ HỔNG B-G11-10** — đo
        được ở G18: khai 20 ⇒ 20/40/80/160 với N=1/2/4/8. G19/AG-02 đã sửa.

        Khẳng định ĐÚNG nay:
          · trong MỘT tiến trình, đường đi (HTTP hay gọi hàm) KHÔNG đổi con số;
          · qua NHIỀU tiến trình, ngân sách vẫn là MỘT — trần KHÔNG nhân.

        GIỮ NGUYÊN ĐỘ RĂNG: ai quay lại kho bộ nhớ một tiến trình thì `h2` thành `2 × h1` và ca
        này ĐỎ lại — đúng chiều ngược với bản cũ, nhưng vẫn canh cùng một bất biến.
        """
        thang, h1, h2 = (self.ket_qua.get("thang"), self.ket_qua.get("http1"),
                         self.ket_qua.get("http2"))
        self.assertEqual(thang, h1, "HTTP != gọi thẳng hàm trong CÙNG một tiến trình")
        self.assertEqual(h1, h2,
                         "1 tiến trình cho %d, 2 tiến trình cho %d — trần DÙNG CHUNG thì phải BẰNG"
                         " nhau, KHÔNG nhân đôi (B-G11-10). Nếu %d gấp đôi %d thì kho đếm đã quay"
                         " lại BỘ NHỚ MỘT TIẾN TRÌNH." % (h1, h2, h2, h1))
        print("  [C5] KẾT LUẬN: HTTP==hàm trong 1 tiến trình (%d==%d) VÀ trần DÙNG CHUNG qua"
              " 2 tiến trình (%d==%d, tỉ lệ 1.0×)." % (thang, h1, h1, h2))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. RANH GIỚI AG-02 / AG-05 — trạng thái dùng chung nằm ở ĐÂU
# ═════════════════════════════════════════════════════════════════════════════════════════════
MANH_DEM = _dau_manh() + r'''
import time
import csdl
che_do = %(che_do)r
def mot_lan():
    if che_do == "giao_dich":
        with csdl.giao_dich():
            v = csdl.mot("SELECT gia_tri g FROM g18_dem WHERE id=1")["g"]
            time.sleep(0.5)
            csdl.ghi("UPDATE g18_dem SET gia_tri=? WHERE id=1", (v + 1,))
    else:
        v = csdl.mot("SELECT gia_tri g FROM g18_dem WHERE id=1")["g"]
        time.sleep(0.5)
        csdl.ghi("UPDATE g18_dem SET gia_tri=? WHERE id=1", (v + 1,))
mot_lan()
'''

MANH_TAO_BANG = _dau_manh() + r'''
import csdl
csdl.ghi("CREATE TABLE IF NOT EXISTS g18_dem (id INTEGER PRIMARY KEY, gia_tri INTEGER)")
csdl.ghi("DELETE FROM g18_dem")
csdl.ghi("INSERT INTO g18_dem (id, gia_tri) VALUES (1, 0)")
'''

MANH_DOC_BANG = _dau_manh() + r'''
import csdl
print(csdl.mot("SELECT gia_tri g FROM g18_dem WHERE id=1")["g"])
'''


class D_RanhGioiAg02Ag05(unittest.TestCase):
    """AG-02: "lớp HTTP AN TOÀN qua nhiều tiến trình". AG-05: "khuôn đọc-rồi-ghi `mot()`+`ghi()`
    MẤT CẬP NHẬT IM LẶNG ở CẢ HAI kho". Mâu thuẫn không? Ranh giới ở đâu?

    Trả lời bằng CẤU TRÚC (trạng thái dùng chung nằm ở mô-đun NÀO) + HÀNH VI (mất cập nhật thật).
    """

    def test_d1_http_jt_khong_co_trang_thai_dung_chung(self):
        so_ten, so_dict, ghi = quet_ghi_ten_muc_modun(DUONG_HTTP_JT)
        self.assertEqual([], ghi, "http_jt.py CÓ ghi trạng thái mức mô-đun: %s" % ghi)
        print("\n  [D1] app/http_jt.py : %d tên mức mô-đun · %d dict hằng · %d dấu hiệu GHI"
              % (so_ten, so_dict, len(ghi)))

    def test_d2_gioi_han_phanA_CO_trang_thai_dung_chung(self):
        """ĐỐI CHỨNG DƯƠNG: cùng phép quét phải TÌM RA trạng thái dùng chung ở mô-đun khác.

        Nếu phép quét không tìm thấy gì ở BẤT KỲ mô-đun nào thì nó là phép quét mù, và D1 xanh
        vô nghĩa. `gioi_han` PHẦN A giữ bộ đếm trong bộ nhớ tiến trình — đúng chỗ AG-02 chỉ ra.
        """
        so_ten, _, ghi = quet_ghi_ten_muc_modun(DUONG_GIOI_HAN)
        self.assertGreater(len(ghi), 0, "phép quét KHÔNG thấy trạng thái dùng chung ở gioi_han ⇒ quét mù")
        ten_ghi = sorted({t for t, _ in ghi})
        # VÁ G19 (AG-00): bản trước đòi thấy `_lan` / `_chan_den` — tên bộ đếm TRONG BỘ NHỚ.
        # AG-02 đã chuyển kho đếm vào CSDL (bảng `gioi_han_luot` / `gioi_han_chan`), nên hai tên
        # đó KHÔNG còn là trạng thái mức mô-đun — và đó chính là điều G19 muốn.
        # Đối chứng dương vẫn phải chứng minh BỘ QUÉT KHÔNG MÙ, chứ không được bỏ ca: nay nó phải
        # thấy trạng thái mức mô-đun CÒN LẠI (cờ đệm `global _da_tao_bang_gh`), và phải thấy kho
        # đếm đã CHUYỂN SANG CSDL.
        self.assertTrue(len(ten_ghi) > 0,
                        "bộ quét KHÔNG thấy trạng thái mức mô-đun nào ở gioi_han ⇒ quét mù: %s"
                        % ten_ghi)
        self.assertIn("gioi_han_luot", open(DUONG_GIOI_HAN, encoding="utf-8").read(),
                      "kho đếm KHÔNG còn nhắc bảng CSDL `gioi_han_luot` ⇒ nó đã quay lại BỘ NHỚ"
                      " MỘT TIẾN TRÌNH, và trần lại nhân theo số bản (B-G11-10)")
        print("  [D2] app/gioi_han.py: %d dấu hiệu GHI ⇒ %s" % (len(ghi), ten_ghi))

    def test_d3_khoa_ghi_la_rlock_khong_phu_tien_trinh(self):
        """`csdl.khoa_ghi` là RLock — khoá TRONG một tiến trình, KHÔNG phủ tiến trình khác."""
        import csdl
        self.assertEqual("RLock", type(csdl.khoa_ghi).__name__,
                         "khoá ghi không còn là RLock — đọc lại kết luận về đa tiến trình")
        nguon = doc(DUONG_CSDL)
        self.assertIn("KHÔNG phủ nhiều tiến trình", nguon,
                      "chú thích về phạm vi của `giao_dich()` đã biến mất")
        print("  [D3] csdl.khoa_ghi = %s (khoá trong tiến trình) · chú thích phạm vi còn nguyên"
              % type(csdl.khoa_ghi).__name__)

    def _do_mat_cap_nhat(self, che_do):
        r = chay_con(MANH_TAO_BANG, giay=120)
        self.assertEqual(0, r.returncode, r.stderr[-400:])
        ps = [subprocess.Popen([sys.executable, "-c", MANH_DEM % {"che_do": che_do}], cwd=GOC,
                               env=dict(os.environ), stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE) for _ in range(2)]
        for p in ps:
            _, e = p.communicate(timeout=180)
            self.assertEqual(0, p.returncode, "tiến trình con hỏng: %s" % (e or b"")[-300:])
        r = chay_con(MANH_DOC_BANG, giay=60)
        self.assertEqual(0, r.returncode, r.stderr[-400:])
        return int(r.stdout.strip().splitlines()[-1])

    def test_d4_doc_roi_ghi_ngoai_giao_dich_thi_MAT_CAP_NHAT(self):
        """HÀNH VI: hai tiến trình, mỗi tiến trình đọc-rồi-ghi MỘT lần ⇒ phải ra 2. Ra 1 là MẤT
        CẬP NHẬT — và mất IM LẶNG: không ngoại lệ, không mã lỗi, `ghi()` trả về bình thường."""
        cuoi = self._do_mat_cap_nhat("ngoai_giao_dich")
        self.assertEqual(1, cuoi,
                         "kỳ vọng MẤT đúng 1 cập nhật (ra 1); ra %d nghĩa là hành vi đã đổi — "
                         "đọc lại kết luận của AG-05" % cuoi)
        print("  [D4] đọc-rồi-ghi NGOÀI `giao_dich()`, 2 tiến trình ⇒ giá trị cuối = %d "
              "(kỳ vọng 2) ⇒ MẤT 1, IM LẶNG" % cuoi)

    def test_d5_trong_giao_dich_thi_khong_mat(self):
        """RANH GIỚI, khẳng định bằng ĐỐI CHỨNG ÂM: CÙNG khuôn đọc-rồi-ghi, bọc `giao_dich()`,
        hai tiến trình ⇒ KHÔNG mất. Nghĩa là chỗ hở nằm ĐÚNG ở ranh giới TIẾN TRÌNH, không phải
        ở khuôn đọc-rồi-ghi nói chung."""
        cuoi = self._do_mat_cap_nhat("giao_dich")
        self.assertEqual(2, cuoi,
                         "trong `giao_dich()` mà vẫn mất cập nhật (ra %d) ⇒ ranh giới không phải "
                         "ở tiến trình như kết luận" % cuoi)
        print("  [D5] đọc-rồi-ghi TRONG `giao_dich()`, 2 tiến trình ⇒ giá trị cuối = %d "
              "(kỳ vọng 2) ⇒ KHÔNG mất" % cuoi)

    def test_d6_hai_ket_luan_noi_ve_hai_tang_khac_nhau(self):
        """KẾT LUẬN ĐỐI CHIẾU: KHÔNG mâu thuẫn. AG-02 nói về TẦNG VẬN CHUYỂN (không giữ trạng
        thái), AG-05 nói về TẦNG LƯU TRỮ (đọc-rồi-ghi không nguyên tử). Ranh giới là DÒNG TIẾN
        TRÌNH, và chính `app/csdl.py` đã ghi ranh giới ấy trong chú thích của `giao_dich()`.
        """
        _, _, ghi_jt = quet_ghi_ten_muc_modun(DUONG_HTTP_JT)
        _, _, ghi_gh = quet_ghi_ten_muc_modun(DUONG_GIOI_HAN)
        self.assertEqual(0, len(ghi_jt))
        self.assertGreater(len(ghi_gh), 0)
        self.assertNotEqual(DUONG_HTTP_JT, DUONG_GIOI_HAN)
        print("  [D6] KẾT LUẬN: http_jt 0 trạng thái chung · gioi_han PHẦN A %d · csdl RLock ⇒"
              " ba tầng khác nhau. KHÔNG mâu thuẫn; ranh giới = DÒNG TIẾN TRÌNH." % len(ghi_gh))


# ═════════════════════════════════════════════════════════════════════════════════════════════
# E. ĐA TIẾN TRÌNH TRÊN CÂY GỘP — 275 dòng của AG-03 có phá tính không-trạng-thái của AG-02?
# ═════════════════════════════════════════════════════════════════════════════════════════════
class _StubHTTP(BaseHTTPRequestHandler):
    def setup(self):
        self.server.so_ket_noi += 1
        self.so_cua_toi = self.server.so_ket_noi
        BaseHTTPRequestHandler.setup(self)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        self.rfile.read(n)
        than = json.dumps({"ket_noi": self.so_cua_toi}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(than)))
        self.end_headers()
        self.wfile.write(than)

    def log_message(self, *a):
        pass


MANH_GOI_HTTP_JT = _dau_manh() + r'''
import json
import http_jt
tl = http_jt.gui_form(%(url)r, {"Content-Type": "application/x-www-form-urlencoded"},
                      {"bizContent": json.dumps({"i": %(i)d})}, timeout=20)
print(tl.than.decode())
'''


class E_DaTienTrinhCayGop(unittest.TestCase):
    """AG-02 đo trên NHÁNH CỦA NÓ, TRƯỚC khi 275 dòng của AG-03 vào cùng tệp `http_jt.py`.

    Tính "không có trạng thái dùng chung" là tính chất của CẢ TỆP, nên nó phải được đo lại SAU
    khi gộp: một bộ đệm/bảng tra thêm vào ở tầng mô-đun sẽ phá nó mà bộ thử của AG-02 không thấy.
    """

    def test_e1_bon_tien_trinh_qua_http_jt_khong_lan_nhau(self):
        sv = ThreadingHTTPServer(("127.0.0.1", 0), _StubHTTP)
        sv.so_ket_noi = 0
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        try:
            url = "http://127.0.0.1:%d/api/v2/order/addOrder" % sv.server_address[1]
            ps = []
            for i in range(4):
                ma = MANH_GOI_HTTP_JT % {"url": url, "i": i}
                ps.append(subprocess.Popen([sys.executable, "-c", ma], cwd=GOC,
                                           env=dict(os.environ), stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, text=True))
            nhan = []
            for p in ps:
                ra, loi = p.communicate(timeout=120)
                self.assertEqual(0, p.returncode, "tiến trình con hỏng: %s" % (loi or "")[-400:])
                nhan.append(json.loads(ra.strip().splitlines()[-1])["ket_noi"])
        finally:
            sv.shutdown()

        self.assertEqual(4, sv.so_ket_noi,
                         "stub nhận %d kết nối TCP cho 4 lượt gọi ⇒ có dùng chung/pool kết nối"
                         % sv.so_ket_noi)
        self.assertEqual(4, len(set(nhan)),
                         "có tiến trình nhận thân trả lời của tiến trình khác: %s" % nhan)
        self.assertEqual({1, 2, 3, 4}, set(nhan),
                         "không phải mỗi lượt một kết nối riêng: %s" % nhan)
        print("\n  [E1] 4 tiến trình thật qua http_jt (SAU khi gộp AG-03): 4 kết nối TCP riêng biệt,"
              " 4 thân trả lời khác nhau, 0 lẫn nhau")


if __name__ == "__main__":
    print("═" * 84)
    print("G18 — AG-01 LƯỢT 2: NGHIỆM THU ĐỘC LẬP KẾT QUẢ ĐÃ TÍCH HỢP")
    print("  HEAD      : %s" % subprocess.run(["git", "rev-parse", "HEAD"], cwd=GOC,
                                             capture_output=True, text=True).stdout.strip())
    print("  CSDL tạm  : %s" % TAM)
    print("  migrate   : exit %d" % _MIGRATE.returncode)
    print("═" * 84)
    unittest.main(verbosity=2)
