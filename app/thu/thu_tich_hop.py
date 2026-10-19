# Bộ thử TÍCH HỢP của AG-00 — canh những thứ CẤU TRÚC mà từng agent lẻ không thấy được.
# Mỗi ca ở đây sinh ra từ một cảnh báo thật của agent trong đợt 14/10/2026.
import os
import re
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_DA = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="vip-hub-tichhop-"))

import csdl      # noqa: E402
import bao_mat   # noqa: E402


def doc(duong):
    """Đọc file và ĐÓNG hẳn — tránh ResourceWarning làm bẩn kết quả chạy."""
    with open(duong, encoding="utf-8") as f:
        return f.read()


# ── Dò nhập thư viện gọi mạng bằng AST (test_05) ─────────────────────────────────────────────
# Grep bắt cả `http.client` trong CHÚ THÍCH (dương tính giả đã đo ở `adapter_best.py`) và bỏ
# sót `from urllib import request`. AST chỉ thấy MÃ CHẠY. `urllib.parse` là xử lý CHUỖI (tách
# URL) — không phải I/O; họ `urllib`/`http` chỉ cấm theo TÊN ĐẦY ĐỦ của mô-đun con.
MANG_GOC = {"requests", "httpx", "aiohttp", "urllib3", "socket", "socketserver",
            "ftplib", "telnetlib", "smtplib", "asyncio", "ssl", "xmlrpc", "pycurl",
            "websocket"}
MANG_DAY_DU = {"urllib.request", "urllib.error", "http.client", "http.server"}


def _vi_pham_nhap_mang(nguon):
    """Trả danh sách mô-đun gọi mạng được NHẬP trong mã chạy của `nguon`."""
    import ast
    vi_pham = []
    for n in ast.walk(ast.parse(nguon)):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in MANG_DAY_DU or a.name.split(".")[0] in MANG_GOC:
                    vi_pham.append(f"import {a.name}")
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module in MANG_DAY_DU or n.module.split(".")[0] in MANG_GOC:
                vi_pham.append(f"from {n.module} import …")
            else:
                for a in n.names:
                    if f"{n.module}.{a.name}" in MANG_DAY_DU:
                        vi_pham.append(f"from {n.module} import {a.name}")
    return vi_pham


class CanhCauTruc(unittest.TestCase):

    def test_01_moi_cot_ma_hoa_deu_duoc_xoay_khoa_phu(self):
        """AG-01 cảnh báo: `xoay_khoa()` chỉ phủ `carrier_accounts`. Thêm bảng có cột mã hóa
        mà quên thêm vào hàm xoay khóa thì bản mã đó sẽ KHÔNG BAO GIỜ xoay được — hỏng im lặng.
        Ca này quét schema, bắt mọi cột `*_ma_hoa` và đòi chúng nằm trong danh sách đã phủ."""
        cot_ma_hoa = set(re.findall(r"^\s*(\w*_ma_hoa)\s", csdl.SCHEMA, re.M))
        nguon = doc(os.path.join(GOC_APP, "bao_mat.py"))
        than = nguon[nguon.index("def ma_hoa_lai_carrier_accounts"):] if \
            "def ma_hoa_lai_carrier_accounts" in nguon else ""
        self.assertTrue(than, "không tìm thấy hàm mã hóa lại — xoay khóa đã biến mất?")
        than = than[:than.index("\ndef ", 5)] if "\ndef " in than[5:] else than
        thieu = [c for c in cot_ma_hoa if c not in than]
        self.assertEqual(thieu, [], f"Cột mã hóa KHÔNG được xoay khóa phủ: {thieu}. "
                                    "Thêm vào bao_mat.ma_hoa_lai_carrier_accounts() rồi thêm ca thử.")

    def test_02_ma_san_pham_khong_goi_ma_hoa_tran(self):
        """AG-01 cảnh báo: `ma_hoa()`/`giai_ma()` trần sinh bản mã KHÔNG mang key_id (không xoay
        khóa được) và KHÔNG có AAD (chép chéo tenant được). Chỉ `migrate.py` được dùng chúng,
        vì nó phải đọc định dạng lịch sử. Mã sản phẩm khác phải dùng 4 hàm contract."""
        duoc_phep = {"migrate.py", "bao_mat.py", "secret_provider.py"}
        vi_pham = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py") or ten in duoc_phep:
                continue
            noi_dung = doc(os.path.join(GOC_APP, ten))
            for so, dong in enumerate(noi_dung.splitlines(), 1):
                if re.search(r"bao_mat\.(ma_hoa|giai_ma)\s*\(", dong) and \
                   not re.search(r"bao_mat\.(ma_hoa|giai_ma)_(cred|wh)\s*\(", dong):
                    vi_pham.append(f"{ten}:{so}")
        self.assertEqual(vi_pham, [], "Gọi mã hóa trần ngoài migrate — dùng ma_hoa_cred/ma_hoa_wh: "
                                      + ", ".join(vi_pham))

    def test_03_chong_trung_webhook_do_CSDL_canh_khong_phai_if(self):
        """AG-02 cảnh báo: chống trùng webhook nên do ràng buộc CSDL cưỡng chế, không phải `if`.
        Ca này đòi UNIQUE thật trong schema."""
        self.assertRegex(csdl.SCHEMA, r"UNIQUE\s*\(\s*carrier_account_id\s*,\s*event_id\s*\)",
                         "wh_su_kien thiếu UNIQUE(carrier_account_id, event_id)")
        self.assertRegex(csdl.SCHEMA, r"UNIQUE\s*\(\s*tenant_id\s*,\s*idem_key\s*\)",
                         "don_hang thiếu UNIQUE(tenant_id, idem_key) — idempotency mất cưỡng chế")

    def test_04_khoa_ma_hoa_khong_duoc_vao_git(self):
        """Khóa lọt vào git là mất sạch secret. Canh bằng chính git, không bằng niềm tin."""
        import subprocess
        for duong in ("app/du-lieu/khoa", "app/du-lieu/khoa-noi-bo.key", "app/du-lieu/hub.db"):
            kq = subprocess.run(["git", "check-ignore", "-q", duong], cwd=GOC_DA)
            self.assertEqual(kq.returncode, 0, f"{duong} KHÔNG bị gitignore — nguy cơ lộ secret")
        theo_doi = subprocess.run(["git", "ls-files", "app/du-lieu"], cwd=GOC_DA,
                                  capture_output=True, text=True).stdout.strip()
        self.assertEqual(theo_doi, "", f"git đang theo dõi file trong app/du-lieu: {theo_doi}")

    def test_05_adapter_khong_co_duong_goi_mang_nao(self):
        """Mọi adapter còn ở chế độ MOCK: không file nào được nhập thư viện gọi mạng.

        Dò bằng **AST**, không grep: bản cũ trúng chữ `http.client` trong CHÚ THÍCH của
        `adapter_best.py` (dương tính giả đã đo), đồng thời bỏ sót `from urllib import request`.
        `urllib.parse` là xử lý CHUỖI (tách URL), không phải I/O.
        """
        for ten in [f for f in os.listdir(GOC_APP) if f.startswith("adapter")]:
            vi_pham = _vi_pham_nhap_mang(doc(os.path.join(GOC_APP, ten)))
            self.assertEqual(vi_pham, [], f"{ten} có thể gọi mạng thật qua: {vi_pham}")
        # ĐỐI CHỨNG ÂM — tiêm I/O thật vào mã: bộ dò PHẢI bắt.
        for mau in ("import http.client\n", "from urllib import request\n", "import socket\n"):
            with self.subTest(tiem=mau.strip()):
                self.assertTrue(_vi_pham_nhap_mang(mau),
                                f"tiêm {mau.strip()!r} mà bộ dò im ⇒ ca này vô giá trị")
        # ĐỐI CHỨNG DƯƠNG — chú thích và xử lý chuỗi KHÔNG được kêu.
        self.assertEqual(_vi_pham_nhap_mang("# import http.client trong chú thích\n"), [],
                         "chú thích không phải mã chạy")
        self.assertEqual(_vi_pham_nhap_mang("from urllib.parse import urlsplit\n"), [],
                         "urllib.parse chỉ tách URL, không mở socket")

    def test_06_live_bi_khoa_o_moi_adapter(self):
        import adapter, adapter_jt, adapter_vtp  # noqa: F401
        for ma, lop in adapter._DANG_KY.items():
            self.assertFalse(lop.CHO_PHEP_LIVE, f"{ma} đã MỞ đường LIVE — Owner chưa duyệt")


# ============================================================================
# G16 — cấu hình credentials, cổng môi trường, và LUẬT PHÂN TẦNG của lớp HTTP
# ============================================================================
class G16_CauHinhVaPhanTang(unittest.TestCase):
    """Bốn ca sinh ra từ yêu cầu G16: credentials an toàn, tách MOCK/SANDBOX/PRODUCTION,
    và chỉ MỘT mô-đun được nói chuyện với mạng."""

    def test_07_credential_chi_tra_TEN_truong_khong_bao_gio_tra_gia_tri(self):
        """`jt_thieu_truong` là thứ sẽ bị đưa vào log/màn hình. Nó phải trả ĐÚNG tên trường.

        Ca này gieo một giá trị BÍ MẬT giả vào dict credentials rồi khẳng định chuỗi đó
        KHÔNG xuất hiện ở bất kỳ đâu trong kết quả — kể cả khi in cả list ra.
        """
        import cau_hinh
        self.assertEqual(sorted(cau_hinh.JT_TRUONG_CREDENTIALS),
                         sorted(["apiAccount", "privateKey", "customerCode", "password"]),
                         "tên trường credentials đã đổi — hợp đồng §38 ghi bốn tên này")
        BI_MAT = "ZZZ-KHONG-DUOC-LO-RA-9f3a"
        # đủ cả bốn ⇒ không thiếu gì
        self.assertEqual(cau_hinh.jt_thieu_truong(
            {t: BI_MAT for t in cau_hinh.JT_TRUONG_CREDENTIALS}), [])
        # thiếu hai ⇒ trả ĐÚNG HAI TÊN, và KHÔNG kèm giá trị nào
        thieu = cau_hinh.jt_thieu_truong({"apiAccount": BI_MAT, "privateKey": BI_MAT})
        self.assertEqual(sorted(thieu), ["customerCode", "password"])
        self.assertNotIn(BI_MAT, repr(thieu) + str(thieu),
                         "giá trị credential lọt ra qua kết quả của jt_thieu_truong")
        # đầu vào rỗng/None cũng không được nổ
        self.assertEqual(len(cau_hinh.jt_thieu_truong(None)), 4)
        self.assertEqual(len(cau_hinh.jt_thieu_truong({})), 4)

    def test_08_cong_moi_truong_MAC_DINH_chan_sandbox_va_production(self):
        """Mặc định phải là MOCK, và hai mức dưới phải TỪ CHỐI kèm lý do đọc được."""
        import cau_hinh
        self.assertEqual(cau_hinh.JT_MOI_TRUONG, "mock", "mặc định KHÔNG còn là mock")
        self.assertFalse(cau_hinh.JT_CHO_PHEP_SANDBOX, "cổng sandbox đã bị mở — Owner chưa cấp")
        self.assertFalse(cau_hinh.JT_CHO_PHEP_PRODUCTION, "cổng production đã bị mở")
        ok, ly_do = cau_hinh.jt_kiem_moi_truong("mock")
        self.assertTrue(ok, ly_do)
        for mt in ("sandbox", "production", "la-bay", ""):
            ok, ly_do = cau_hinh.jt_kiem_moi_truong(mt)
            self.assertFalse(ok, f"{mt!r} phải bị CHẶN")
            self.assertTrue(str(ly_do).strip(), f"{mt!r} bị chặn nhưng không nêu lý do")
        # đối chứng: mock ĐI QUA được — thiếu vế này thì một hàm "chặn tất cả" cũng xanh
        self.assertTrue(cau_hinh.jt_kiem_moi_truong("mock")[0])

    def test_09_chi_MOT_mo_dun_san_pham_duoc_noi_chuyen_voi_mang(self):
        """Từ G16, adapter ĐƯỢC gọi mạng — nhưng chỉ QUA `http_jt.py`.

        Đây là bất biến phân tầng: mọi lượt HTTP của hãng đi qua đúng một tệp, nên chốt chặn
        (danh sách trắng máy chủ, hết giờ, không tự thử lại) chỉ cần đúng ở một chỗ.
        Dò bằng **AST**, không bằng grep: `urllib.parse` là xử lý CHUỖI, không phải gọi mạng,
        và grep sẽ bắt nhầm nó — hoặc bỏ sót `from urllib import request`.
        """
        import ast
        # Hai danh sách TÁCH RỜI, và đó là chỗ bản đầu của ca này SAI — đo được bằng đột biến:
        #   · `import urllib.request` là `ast.Import` với tên ĐẦY ĐỦ "urllib.request"; lấy
        #     `name.split(".")[0]` ra "urllib" nên nó LỌT (bản đầu chỉ so tên gốc ⇒ bỏ sót).
        #   · `urllib.parse` là xử lý CHUỖI, không phải gọi mạng — cấm "urllib" là bắt nhầm nó.
        # Nên: tên GỐC cấm theo gốc, còn họ `urllib`/`http` chỉ cấm theo tên ĐẦY ĐỦ.
        MANG_GOC = {"requests", "httpx", "aiohttp", "urllib3", "socket", "pycurl", "websocket"}
        MANG_DAY_DU = {"urllib.request", "urllib.error", "http.client"}
        # Ba dạng viết đều phải bắt được:
        #   import urllib.request            → Import,        name="urllib.request"
        #   from urllib import request       → ImportFrom,    module="urllib", alias="request"
        #   import socket                    → Import,        name="socket"
        duoc_phep = {"http_jt.py"}
        vi_pham = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py") or ten in duoc_phep:
                continue
            duong = os.path.join(GOC_APP, ten)
            try:
                cay = ast.parse(doc(duong))
            except SyntaxError as e:
                vi_pham.append(f"{ten}: KHÔNG PHÂN TÍCH ĐƯỢC ({e})")
                continue
            for nut in ast.walk(cay):
                if isinstance(nut, ast.Import):
                    for a in nut.names:
                        if a.name in MANG_DAY_DU or a.name.split(".")[0] in MANG_GOC:
                            vi_pham.append(f"{ten}: import {a.name}")
                elif isinstance(nut, ast.ImportFrom) and nut.module:
                    if nut.module in MANG_DAY_DU or nut.module.split(".")[0] in MANG_GOC:
                        vi_pham.append(f"{ten}: from {nut.module} import …")
                    else:
                        # dạng `from urllib import request` — tên bị cấm nằm ở ALIAS
                        for a in nut.names:
                            if f"{nut.module}.{a.name}" in MANG_DAY_DU:
                                vi_pham.append(f"{ten}: from {nut.module} import {a.name}")
        self.assertEqual(vi_pham, [], "chỉ `http_jt.py` được nói chuyện với mạng; "
                                      "chỗ khác phải đi qua nó: " + ", ".join(vi_pham))

    def test_10_env_mau_khai_du_bon_TEN_va_khong_chua_gi_bi_mat(self):
        """`.env.example` là tài liệu đi theo repo — nó phải KHAI TÊN và để GIÁ TRỊ RỖNG."""
        duong = os.path.join(GOC_DA, ".env.example")
        self.assertTrue(os.path.exists(duong), "thiếu .env.example")
        noi_dung = doc(duong)
        for ten in ("apiAccount", "privateKey", "customerCode", "password"):
            self.assertIn(ten, noi_dung, f".env.example không nhắc tên trường {ten}")
        self.assertIn("VIP_JT_MOI_TRUONG=mock", noi_dung,
                      "mặc định trong .env.example phải là mock")
        # KHÔNG được có dòng nào gán giá trị thật cho bốn trường credentials
        for dong in noi_dung.splitlines():
            d = dong.strip()
            if d.startswith("#") or "=" not in d:
                continue
            khoa, _, gia_tri = d.partition("=")
            if khoa.strip() in ("apiAccount", "privateKey", "customerCode", "password"):
                self.assertEqual(gia_tri.strip(), "",
                                 f".env.example đang gán giá trị cho {khoa.strip()} — CẤM")

    def test_11_khong_co_secret_that_trong_cay_lam_viec(self):
        """Không tệp `.env` thật nào được tồn tại trong cây, và `.env*` phải bị git chặn."""
        import subprocess
        for ten in os.listdir(GOC_DA):
            if ten == ".env" or (ten.startswith(".env.") and ten != ".env.example"):
                self.fail(f"có tệp cấu hình bí mật trong cây: {ten} — phải nằm ngoài repo")
        for duong in (".env", ".env.local"):
            kq = subprocess.run(["git", "check-ignore", "-q", duong], cwd=GOC_DA)
            self.assertEqual(kq.returncode, 0, f"{duong} KHÔNG bị gitignore")

    def test_12_goi_y_thoi_gian_cho_khi_thu_lai_co_TRAN(self):
        """HTTP 429/408 nói *"thử lại sau"*, thường kèm `Retry-After`.

        Nếu lớp trên cứ thử lại theo backoff 0,2 giây thì lượt thử lại vừa vô ích vừa làm hạn
        mức tệ thêm — "thử lại được" trên giấy mà hỏng trong thực tế. Nên lớp dưới được gợi ý
        thời gian chờ; nhưng **phải có TRẦN**, nếu không một `Retry-After: 86400` biến "thử lại
        được" thành "treo tiến trình một ngày" — hãng không được quyết định điều đó.
        """
        import transport as T
        self.assertEqual(T.LoiTamThoi("x").cho_giay, None, "chữ ký cũ phải còn chạy")

        def _cho(cho_giay):
            waits, lan = [], [0]

            def hong():
                lan[0] += 1
                raise T.LoiTamThoi("429", cho_giay=cho_giay)
            try:
                T.goi(hong, thao_tac="trackOrder", ngu=waits.append)
            except T.LoiTamThoi:
                pass
            return lan[0], waits

        # không gợi ý -> backoff của chính sách
        n, w = _cho(None)
        self.assertEqual(n, 3, "thao tác ĐỌC phải được thử lại 3 lần")
        self.assertEqual([round(x, 3) for x in w], [0.2, 0.4])
        # gợi ý LỚN HƠN backoff -> theo gợi ý
        self.assertEqual(_cho(5)[1], [5.0, 5.0])
        # gợi ý nhỏ hơn backoff -> giữ backoff (lấy max, không rút ngắn)
        self.assertEqual([round(x, 3) for x in _cho(0.001)[1]], [0.2, 0.4])
        # TRẦN: hãng không được bắt hệ chờ vô hạn
        for x in _cho(86400)[1]:
            self.assertLessEqual(x, T.CHO_TOI_DA, "gợi ý vượt trần — phải bị kẹp")
        self.assertEqual(_cho(86400)[1], [T.CHO_TOI_DA, T.CHO_TOI_DA])
        # và thao tác GHI vẫn KHÔNG được thử lại, dù có gợi ý thời gian chờ
        lan = [0]

        def hong_ghi():
            lan[0] += 1
            raise T.LoiTamThoi("429", cho_giay=5)
        with self.assertRaises(T.LoiTamThoi):
            T.goi(hong_ghi, thao_tac="createOrder", co_khoa_chong_trung=False,
                  ngu=lambda s: None)
        self.assertEqual(lan[0], 1, "createOrder bị gửi lại — nguy cơ tạo đơn trùng!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
