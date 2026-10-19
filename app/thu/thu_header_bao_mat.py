"""Hồi quy: MỌI đường trả phản hồi phải mang header bảo mật, và cờ Secure/HSTS theo HTTPS.

Vì sao có bộ thử này: trước 15/10 máy chủ **không có một header bảo mật nào** — đo bằng
`curl -D -` trên máy chủ thật, chỉ về `Server/Date/Content-*/Cache-Control`. Khi thêm bốn
header, `_tra` có ngay nhưng **ba đường khác thiếu sạch** (tệp tĩnh · xuất CSV đơn · xuất CSV
import), vì mỗi đường tự dựng header riêng. Đã gộp cả ba vào `_tra_tep`.

Bộ thử này canh hai thứ khác nhau:
  - **động**: bắn HTTP thật, đòi header về đủ (ca a*)
  - **tĩnh**: đòi mọi lượt `end_headers()` trong `server.py` đều có `_header_bao_mat` phía
    trước (ca b1). Đây là chốt cho đường THỨ TƯ chưa ai viết — ca động chỉ phủ đường đã có,
    còn ca tĩnh phủ đường sẽ thêm.

PHẠM VI: HTTP trên 127.0.0.1, một tiến trình. **NGOÀI phạm vi**: hành vi thật của trình duyệt
với CSP này (chưa đo — V-13906-01), HTTPS thật, proxy thật.
"""
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="veh-hdr-"))

import cau_hinh     # noqa: E402
import migrate      # noqa: E402
import quyen        # noqa: E402
import server       # noqa: E402

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# `migrate.chay()` gọi TRỰC TIẾP trong tiến trình này (`setUpClass`) — không có tiến trình con
# nào chạy `migrate`. Bộ thử tự khai bằng giao diện chung `cau_hinh.khai_kho_kiem_thu()` —
# KHÔNG dựa vào việc người chạy nhớ `export VIP_KHO_DANG_CHAY`: một bộ chỉ xanh khi người chạy
# nhớ khai là một bộ GIỎ. `VIP_HUB_DATA` đã trỏ thư mục TẠM ở trên, nên hai chốt cô lập của hàm
# khai đều thoả.
cau_hinh.khai_kho_kiem_thu()

CONG = 0
BAT_BUOC = ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
            "Content-Security-Policy")


def _goi(duong):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (CONG, duong))
    r.add_header("X-Requested-With", "VIPHub")
    try:
        with urllib.request.urlopen(r, timeout=10) as f:
            return f.status, dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


class ThuHeaderBaoMat(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global CONG
        migrate.chay(im_lang=True)
        quyen.seed()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
        CONG = cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown()
        cls.sv.server_close()

    def test_a1_tep_tinh_co_du_header(self):
        st, h = _goi("/index.html")
        self.assertEqual(st, 200)
        for k in BAT_BUOC:
            self.assertIn(k, h, f"tệp tĩnh thiếu {k}")

    def test_a2_api_co_du_header_ke_ca_khi_loi(self):
        """Đường lỗi cũng phải có header. Đường lỗi hay bị quên nhất, mà nó lại là đường mà
        kẻ dò hệ gặp nhiều nhất."""
        for duong in ("/api/v2/auth/toi", "/api/v2/khong-he-co"):
            st, h = _goi(duong)
            self.assertGreaterEqual(st, 400, f"{duong} phải là đường lỗi")
            for k in BAT_BUOC:
                self.assertIn(k, h, f"{duong} (HTTP {st}) thiếu {k}")

    def test_a3_khong_gui_HSTS_khi_chua_co_HTTPS(self):
        """HSTS qua HTTP là vô nghĩa, và nếu trình duyệt từng thấy nó trên một tên miền thì
        nó sẽ TỪ CHỐI HTTP của tên miền đó về sau — hỏng rất khó gỡ."""
        self.assertFalse(server.BoXuLy._dung_https(),
                         "bộ thử này chạy ở HTTP; nếu VIP_HUB_HTTPS=1 thì ca sau vô nghĩa")
        _, h = _goi("/index.html")
        self.assertNotIn("Strict-Transport-Security", h,
                         "gửi HSTS khi chưa có HTTPS")

    def test_a4_CSP_khong_co_unsafe_eval_va_chan_frame(self):
        _, h = _goi("/index.html")
        csp = h.get("Content-Security-Policy", "")
        self.assertNotIn("unsafe-eval", csp, "CSP cho unsafe-eval")
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("base-uri 'none'", csp)

    # ---------- chốt TĨNH cho đường chưa ai viết ----------
    def test_b1_moi_HAM_goi_end_headers_deu_goi_header_bao_mat(self):
        """Soát TĨNH `server.py` bằng **AST**, xét trong PHẠM VI TỪNG HÀM.

        Bản đầu của ca này nhìn lùi 16 DÒNG — và nó **hỏng**: AG-00 thêm một hàm trả phản hồi
        không có header, ca thử **vẫn đạt**, vì cửa sổ 16 dòng với tới lượt gọi
        `_header_bao_mat` của hàm `_tra_tep` nằm ngay phía trên. Chốt đã bị qua mà không ai
        thấy — tức là nó sẽ để đường thứ tư lọt đúng như đường thứ hai, ba đã lọt.

        Đây là lần thứ NĂM trong ngày cùng một họ lỗi: công cụ kiểm chứng tự nó sai (AG-01 ca
        `h5` đọc mảnh f-string · AG-05 `kiem_cau_hinh.py` cắt tại chữ trong ghi chú · phép
        soát `r40` không tính tiền tố f · phép quét DDL đọc chữ trong lời bình · và cửa sổ
        dòng ở đây). §12.2: hỏng lần thứ hai cùng kiểu thì ĐỔI CẤU TRÚC — nên bỏ hẳn cửa sổ
        dòng, dùng AST để biết chính xác lượt gọi nào thuộc hàm nào.
        """
        import ast
        with open(os.path.join(GOC, "server.py"), encoding="utf-8") as f:
            cay = ast.parse(f.read())

        def ten_goi(node):
            """Tên hàm được gọi, dạng `self.x` → `x`."""
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute):
                    return f.attr
            return None

        thieu = []
        for ham in ast.walk(cay):
            if not isinstance(ham, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            goi = {ten_goi(n) for n in ast.walk(ham) if isinstance(n, ast.Call)}
            if "end_headers" not in goi:
                continue
            if "_header_bao_mat" not in goi:
                thieu.append(f"{ham.name} (dòng {ham.lineno})")
        self.assertEqual(
            thieu, [],
            f"các hàm sau gọi end_headers() mà KHÔNG gọi _header_bao_mat() trong cùng hàm: "
            f"{thieu}. Đừng thêm `_header_bao_mat()` tại chỗ — dùng `self._tra` hoặc "
            f"`self._tra_tep`, nếu không thì đường thứ năm lại quên.")

    def test_b1b_chinh_chot_b1_phai_bat_duoc_ham_sai(self):
        """Kiểm chính bộ kiểm: dựng một hàm sai trong BỘ NHỚ và đòi phép soát của `b1` tố
        giác nó. Không có ca này thì `b1` có thể lại âm thầm vô dụng như bản cửa sổ dòng."""
        import ast
        ma_sai = (
            "class X:\n"
            "    def _tra_tot(self):\n"
            "        self._header_bao_mat()\n"
            "        self.end_headers()\n"
            "    def _tra_sai(self):\n"
            "        self.send_response(200)\n"
            "        self.end_headers()\n")
        cay = ast.parse(ma_sai)
        thieu = []
        for ham in ast.walk(cay):
            if not isinstance(ham, ast.FunctionDef):
                continue
            goi = {n.func.attr for n in ast.walk(ham)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
            if "end_headers" in goi and "_header_bao_mat" not in goi:
                thieu.append(ham.name)
        self.assertEqual(thieu, ["_tra_sai"],
                         f"phép soát của b1 KHÔNG tố giác đúng hàm sai: {thieu}")

    def test_b2_cookie_Secure_theo_CO_khong_bat_cung(self):
        """`Secure` phải theo cờ. Bật cứng làm mọi lượt đăng nhập local im lặng thất bại, và
        màn hình chỉ nói "sai mật khẩu" trong khi mật khẩu chưa bao giờ sai — đúng ca sinh ra
        §12.2 của CLAUDE.md. Ca này canh cả hai chiều."""
        with open(os.path.join(GOC, "server.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("_dung_https()", src, "không thấy cờ HTTPS")
        m = re.search(r'them_secure\s*=\s*"; Secure" if ([^\n]+) else ""', src)
        self.assertIsNotNone(m, "cờ Secure không đi qua điều kiện — có thể đang bật cứng")
        self.assertIn("_dung_https", m.group(1))

    def test_b3_bind_mac_dinh_van_la_127_0_0_1(self):
        """Mở ra ngoài phải là việc người vận hành CHỦ ĐỘNG khai, không phải thứ xảy ra vì
        ai đó nâng cấp mã."""
        with open(os.path.join(GOC, "server.py"), encoding="utf-8") as f:
            src = f.read()
        m = re.search(r'os\.environ\.get\("VIP_HUB_BIND",\s*"([^"]+)"\)', src)
        self.assertIsNotNone(m, "không thấy VIP_HUB_BIND")
        self.assertEqual(m.group(1), "127.0.0.1", "mặc định bind KHÔNG còn là 127.0.0.1")
        self.assertIn("HIEN_TOKEN_RESET", src,
                      "thiếu chốt chặn: bind ra ngoài + cửa trả token reset đang mở")


if __name__ == "__main__":
    unittest.main(verbosity=2)
