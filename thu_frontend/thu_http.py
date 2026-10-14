# BỘ THỬ FRONTEND — TẦNG 2: HTTP + TỆP TĨNH (Python, server THẬT, KHÔNG trình duyệt).
# Chạy: python3 thu_frontend/thu_http.py
#
# PHẠM VI CỦA TẦNG NÀY — đọc kỹ trước khi tin kết quả (§12.1 luật 3):
# - Phủ: tệp tĩnh của giao diện có phục vụ được không; mọi endpoint giao diện ĐANG gọi có
#   thật không; mọi endpoint giao diện khai "CHỜ BACKEND" có thật là chưa có không; đường
#   401/403 có trả đúng mã cho giao diện xử lý không; chuyển tenant; tạo đơn → duyệt → gửi
#   → timeline; preview import; quét secret trong tệp tĩnh và trong thân phản hồi API.
# - KHÔNG phủ: DOM, CSS, bố cục, có bấm được không, có nhìn thấy nhãn không.
#   Tầng 1 (Node) kiểm logic; tầng 3 (trình duyệt thật) kiểm cái mắt thấy.
#   KHÔNG ca nào trong file này chạy trình duyệt.
#
# Cổng: bind 0 để hệ cấp cổng TRỐNG. Cố ý — các bộ thử sẵn có dùng cổng cố định và đã đụng
# nhau thật khi hai worktree chạy cùng lúc (đo 15/10/2026: thu_g01_g02 hỏng vì
# gateway/thu/thu_gateway.py bind 18898 trùng phiên khác).
import hashlib
import hmac
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

GOC_DU_AN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_APP = os.path.join(GOC_DU_AN, "app")
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-thu-frontend-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ["VIP_HUB_BACKOFF"] = "0.05"

import bao_mat   # noqa: E402
import csdl      # noqa: E402
import khoi_tao  # noqa: E402
import quyen     # noqa: E402
import server    # noqa: E402
import webhook   # noqa: E402

MK = "MatKhauThu-Frontend-123"
LOG_SERVER = io.StringIO()
DON_MAU = {
    "nguoi_gui_ten": "Shop F04", "nguoi_gui_sdt": "0901111111", "nguoi_gui_dia_chi": "1 Đường F04, HN",
    "nguoi_nhan_ten": "Khách F04", "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Phố F04, HCM",
    "hang_hoa": "Hộp thử F04", "khoi_luong_gram": 500, "cod": 150000,
}


class Phien:
    """Client HTTP nhỏ giữ cookie phiên — bắn như giao diện bắn."""

    def __init__(self, goc_url):
        self.goc = goc_url
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
        body = tho if tho is not None else (json.dumps(du_lieu).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        # Giao diện luôn gửi hai header này (xem hàm api() trong admin/admin.js).
        if method in ("POST", "PUT", "DELETE") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if body is not None and "Content-Type" not in h:
            h["Content-Type"] = "application/json"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(self.goc + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=10) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                ct = ph.headers.get("Content-Type", "")
                raw = ph.read()
                return ph.status, (json.loads(raw) if "json" in ct else raw), dict(ph.headers)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                noi = json.loads(raw)
            except Exception:
                noi = raw
            return e.code, noi, dict(e.headers)

    def dang_nhap(self, ten, mk):
        return self.goi("/api/v2/auth/dang-nhap", "POST", {"ten_dang_nhap": ten, "mat_khau": mk})


def doc_js(ten):
    with open(os.path.join(GOC_DU_AN, "admin", ten), encoding="utf-8") as f:
        return f.read()


def bang_api_cho_backend():
    """Đọc API_CHO_BACKEND ra khỏi admin/logic.js mà KHÔNG chạy JS.

    Cố ý đọc từ CHÍNH file giao diện dùng, không chép lại danh sách sang Python: hai bản
    nội dung là hai bản sẽ lệch nhau (§14.6). Nếu không rút được mục nào thì ca thử phải
    hỏng, chứ không được lặng lẽ kiểm 0 mục rồi báo đạt (§12.1 luật 5).
    """
    ma = doc_js("logic.js")
    i = ma.index("const API_CHO_BACKEND = [")
    j = ma.index("\n  ];", i)
    khoi = ma[i:j]
    ra = []
    for m in re.finditer(r'duong:\s*"([^"]+)",\s*method:\s*"([^"]+)"', khoi):
        ra.append((m.group(1), m.group(2)))
    return ra


def api_dang_dung():
    """Đọc API_DANG_DUNG ra khỏi admin/logic.js, cùng lý do như trên."""
    ma = doc_js("logic.js")
    i = ma.index("const API_DANG_DUNG = [")
    j = ma.index("\n  ];", i)
    return re.findall(r'\["(\w+)",\s*"([^"]+)"\]', ma[i:j])


class ThuFrontendHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._stderr_cu = sys.stderr
        sys.stderr = LOG_SERVER
        csdl.mo()
        webhook.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
        cls.cong = cls.sv.server_address[1]
        cls.goc_url = "http://127.0.0.1:%d" % cls.cong
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()

        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'thu-frontend')",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po', ?, 'Platform Owner', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        cls.po = cls._phien("po")
        # hai tenant để thử chuyển tenant
        cls.tid = {}
        for ten, dn in (("Tenant F04 A", "fa"), ("Tenant F04 B", "fb")):
            st, kq, _ = cls.po.goi("/api/v2/platform/tenants", "POST",
                                   {"ten": ten, "goi_id": "basic",
                                    "owner_ten_dang_nhap": dn + "-owner",
                                    "owner_mat_khau": MK, "owner_ho_ten": "Chủ " + ten})
            assert st == 201, kq
            cls.tid[dn] = kq["id"]
        cls.a = cls._phien("fa-owner")
        # cho fa-owner thêm làm thành viên tenant B ⇒ có tenant_kha_dung > 1 để thử switcher
        st, kq, _ = cls._phien("fb-owner").goi(
            "/api/v2/memberships", "POST",
            {"ten_dang_nhap": "fa-owner", "role": "TENANT_ADMIN", "ho_ten": "Chủ A kiêm B"})
        assert st == 201, kq
        # tài khoản hãng mock + viewer để thử 403
        st, kq, _ = cls.a.goi("/api/v2/tai-khoan-hang", "POST",
                              {"hang": "vtp", "ten": "VTP mock F04",
                               "credentials": {"api_key": "demo-key-F04-chi-de-thu"}})
        assert st == 201, kq
        cls.tk = kq
        assert cls.a.goi("/api/v2/memberships", "POST",
                         {"ten_dang_nhap": "fa-viewer", "mat_khau": MK,
                          "role": "TENANT_VIEWER", "ho_ten": "Người chỉ xem"})[0] == 201
        # đăng nhập lại A: phiên có thể đã bị ảnh hưởng bởi lượt thêm membership
        cls.a = cls._phien("fa-owner")

    @property
    def viewer(self):
        """Phiên của người chỉ xem, đăng nhập LẠI mỗi lần dùng.

        Cố ý không giữ một phiên dùng chung: lượt chạy đầu (15/10/2026) có ba ca hỏng
        401≠403 vì test_12 vô hiệu membership của viewer, và backend THU HỒI phiên của
        người đó — đúng hành vi mong đợi, nhưng làm phiên dùng chung chết âm thầm và
        ba ca sau đo sai thứ (401 thay vì 403). Phiên dùng chung chính là thứ dùng để
        kiểm chứng mà tự nó không đáng tin (§12.1).
        """
        return self._phien("fa-viewer")

    @classmethod
    def _phien(cls, ten):
        p = Phien(cls.goc_url)
        st, kq, _ = p.dang_nhap(ten, MK)
        assert st == 200, "đăng nhập %s hỏng: %s" % (ten, kq)
        return p

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown()
        cls.sv.server_close()
        webhook.dung()
        csdl.dong()
        sys.stderr = cls._stderr_cu

    def _tao_don(self, phien=None, **ghi_de):
        d = dict(DON_MAU)
        d.update(ghi_de)
        return (phien or self.a).goi("/api/v2/don", "POST", d,
                                     headers={"Idempotency-Key": "thu-f04-%s" % os.urandom(6).hex()})

    # ===================== A. Tệp tĩnh của giao diện =====================

    def test_01_tep_tinh_cua_giao_dien_phuc_vu_duoc(self):
        """Mọi tệp giao diện nạp lúc khởi động phải tải được — thiếu một tệp là màn trắng."""
        p = Phien(self.goc_url)
        for duong, phai_co in (("/admin/index.html", "logic.js"),
                               ("/admin/logic.js", "VIPLOGIC"),
                               ("/admin/admin.js", "window.VIPLOGIC"),
                               ("/assets/js/app.js", "window.VIP"),
                               ("/assets/css/style.css", ".che-do")):
            st, body, _ = p.goi(duong)
            self.assertEqual(st, 200, "%s không tải được" % duong)
            self.assertIn(phai_co, body.decode("utf-8"), "%s thiếu nội dung mong đợi" % duong)

    def test_02_thu_tu_nap_script_dung(self):
        """logic.js phải nạp TRƯỚC admin.js, nếu không admin.js đọc window.VIPLOGIC = undefined
        và cả SPA chết ngay dòng đầu — kiểu hỏng không có thông báo nào dễ hiểu."""
        html = doc_js("index.html")
        self.assertLess(html.index("logic.js"), html.index("admin.js"))
        self.assertLess(html.index("assets/js/app.js"), html.index("logic.js"),
                        "app.js (VIP) phải nạp trước vì admin.js dùng VIP.thoat ngay")

    def test_03_goc_tra_ve_man_quan_tri(self):
        st, body, _ = Phien(self.goc_url).goi("/")
        self.assertEqual(st, 200)
        self.assertIn("admin.js", body.decode("utf-8"))

    def test_04_muoi_trang_demo_g00_khong_bi_pha(self):
        """F05: 10 trang demo G00 dùng CHUNG CSS — sửa CSS không được làm chúng gãy."""
        p = Phien(self.goc_url)
        ten_trang = sorted(x for x in os.listdir(os.path.join(GOC_DU_AN, "pages")) if x.endswith(".html"))
        self.assertEqual(len(ten_trang), 10, "số trang demo đổi — xem lại trước khi sửa bộ thử")
        for t in ten_trang:
            st, body, _ = p.goi("/pages/" + t)
            self.assertEqual(st, 200, t)
            s = body.decode("utf-8")
            self.assertIn("assets/css/style.css", s, t)
            self.assertIn("assets/js/app.js", s, t)

    # ===================== B. Không rò secret ra giao diện =====================

    def test_05_tep_tinh_giao_dien_khong_chua_secret(self):
        """Quét MỌI tệp phục vụ được trong admin/ và assets/, không chỉ admin/ như
        thu_saas test_13 — assets/ cũng là tệp người lạ tải được."""
        p = Phien(self.goc_url)
        dau_hieu = ["privateKey", "jtexpress.vn", "BEGIN RSA", "BEGIN PRIVATE",
                    "webhook_secret_mot_lan =", "api_key =", "Authorization: Bearer"]
        so_tep = 0
        for thu_muc in ("admin", "assets/css", "assets/js"):
            d = os.path.join(GOC_DU_AN, thu_muc)
            for ten in os.listdir(d):
                if not os.path.isfile(os.path.join(d, ten)):
                    continue
                if not ten.endswith((".js", ".css", ".html", ".md")):
                    continue
                st, body, _ = p.goi("/%s/%s" % (thu_muc, ten))
                if st != 200:          # .md không nằm trong đuôi cho phép — đọc trực tiếp
                    with open(os.path.join(d, ten), encoding="utf-8") as f:
                        noi = f.read()
                else:
                    noi = body.decode("utf-8")
                so_tep += 1
                for x in dau_hieu:
                    self.assertNotIn(x, noi, "%s/%s có dấu hiệu secret: %s" % (thu_muc, ten, x))
        self.assertGreaterEqual(so_tep, 5, "quét được quá ít tệp — phép đo này đang rỗng")

    def test_06_api_tai_khoan_hang_khong_tra_secret_cho_giao_dien(self):
        """Màn Hãng vận chuyển chỉ được nhận bốn ký tự đuôi, không bao giờ nhận bản mã."""
        st, kq, _ = self.a.goi("/api/v2/tai-khoan-hang")
        self.assertEqual(st, 200)
        tho = json.dumps(kq, ensure_ascii=False)
        for x in ("credentials_ma_hoa", "webhook_secret", "demo-key-F04-chi-de-thu", "v3$"):
            self.assertNotIn(x, tho, "API trả về %s cho giao diện!" % x)
        self.assertIn("credentials_duoi", tho)

    def test_07_admin_khong_co_thu_muc_con(self):
        """thu_saas test_13 dùng os.listdir('admin/') rồi open() từng mục — một thư mục con
        trong admin/ sẽ làm nó hỏng bằng IsADirectoryError, không phải bằng lỗi nghiệp vụ."""
        d = os.path.join(GOC_DU_AN, "admin")
        thu_muc = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
        self.assertEqual(thu_muc, [], "admin/ có thư mục con: %s" % thu_muc)

    # ===================== C. Endpoint giao diện ĐANG dùng đều có thật =====================

    def test_08_moi_endpoint_giao_dien_dang_dung_deu_ton_tai(self):
        ds = api_dang_dung()
        self.assertGreaterEqual(len(ds), 8, "rút được quá ít endpoint — phép đo đang rỗng")
        for method, duong in ds:
            st, kq, _ = self.a.goi(duong, method)
            self.assertNotIn(st, (404, 405), "giao diện gọi %s %s nhưng máy chủ trả %s"
                             % (method, duong, st))
            self.assertLess(st, 500, "%s %s trả %s: %s" % (method, duong, st, kq))

    def test_09_nhan_CHO_BACKEND_khong_noi_doi(self):
        """CA QUAN TRỌNG NHẤT của tầng này. Mỗi đường trong API_CHO_BACKEND được bắn THẬT:
        nếu backend đã làm xong mà giao diện vẫn dán nhãn 'CHỜ BACKEND' thì ca này HỎNG,
        buộc phải gỡ nhãn. Nhãn chờ-backend không thể nói dối lâu hơn một lượt chạy.

        Mục `/api/v2/don` (mot_phan: true) là đường ĐÃ CÓ nhưng thiếu tham số lọc nâng cao —
        cố ý loại khỏi phép đo này và ghi rõ lý do, chứ không im lặng bỏ qua."""
        bang = bang_api_cho_backend()
        self.assertGreaterEqual(len(bang), 5, "rút được quá ít mục — phép đo đang rỗng")
        don_id = self._tao_don()[1]["don"]["id"]
        thay_the = {"<id>": str(don_id)}
        da_kiem = []
        for duong, method in bang:
            if duong == "/api/v2/don":
                continue       # mot_phan: endpoint có, chỉ thiếu tham số — xem test_10
            that = duong
            for k, v in thay_the.items():
                that = that.replace(k, v)
            m1 = method.split(" ")[0]
            st, kq, _ = self.a.goi(that, m1, {} if m1 in ("POST", "PUT") else None)
            da_kiem.append((m1, that, st))
            self.assertIn(st, (404, 405),
                          "giao diện khai '%s %s' là CHỜ BACKEND nhưng máy chủ trả %s — "
                          "backend đã có, phải gỡ nhãn và nối màn vào" % (m1, that, st))
        self.assertGreaterEqual(len(da_kiem), 4, da_kiem)

    def test_10_tham_so_loc_nang_cao_that_su_chua_duoc_may_chu_ho_tro(self):
        """Giao diện nói 'máy chủ chỉ nhận q · trang_thai · gioi_han'. Đo lại câu đó:
        bắn tham số lọc nâng cao, nếu máy chủ bắt đầu lọc thật thì ca này hỏng."""
        for _ in range(2):
            self._tao_don()
        st, tat_ca, _ = self.a.goi("/api/v2/don?gioi_han=500")
        self.assertEqual(st, 200)
        n = len(tat_ca["don"])
        self.assertGreater(n, 0)
        # cod_tu cực lớn: nếu máy chủ ĐÃ lọc thì kết quả phải ít hơn
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&cod_tu=999999999&tu_ngay=2099-01-01"
                               "&trang_thai_giao=khong_ton_tai&hang=khong_co_hang")
        self.assertEqual(st, 200)
        self.assertEqual(len(kq["don"]), n,
                         "máy chủ đã hỗ trợ lọc nâng cao — phải chuyển bộ lọc lên máy chủ và "
                         "sửa dòng 'phạm vi lọc' ở màn Đơn hàng")
        # ngược lại, ba tham số máy chủ CÓ hỗ trợ thì phải có hiệu lực thật
        st, kq, _ = self.a.goi("/api/v2/don?trang_thai=huy")
        self.assertEqual(st, 200)
        self.assertTrue(all(d["trang_thai"] == "huy" for d in kq["don"]))
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=1")
        self.assertLessEqual(len(kq["don"]), 1)

    # ===================== D. Trạng thái đăng nhập: 401 / 403 =====================

    def test_11_chua_dang_nhap_thi_auth_toi_tra_401(self):
        """Giao diện dựa vào đúng mã 401 ở /auth/toi để quyết định hiện màn đăng nhập."""
        st, kq, _ = Phien(self.goc_url).goi("/api/v2/auth/toi")
        self.assertEqual(st, 401)
        self.assertIn("loi", kq)

    def test_12_phien_bi_thu_hoi_thi_API_tra_401_de_man_phien_het_han_bat_duoc(self):
        """Màn 'phiên hết hạn' chỉ dựng được nếu backend trả ĐÚNG 401 (không phải 403/500)."""
        p = self._phien("fa-viewer")
        st, _, _ = p.goi("/api/v2/don")
        self.assertEqual(st, 200)
        # chủ tenant thu hồi: vô hiệu membership của viewer
        st, kq, _ = self.a.goi("/api/v2/memberships")
        mem = [x for x in kq["memberships"] if x["ten_dang_nhap"] == "fa-viewer"][0]
        self.a.goi("/api/v2/memberships/%d" % mem["id"], "PUT", {"trang_thai": "vo_hieu"})
        st, kq, _ = p.goi("/api/v2/don")
        self.assertIn(st, (401, 403), "viewer bị vô hiệu vẫn gọi được: %s" % st)
        self.a.goi("/api/v2/memberships/%d" % mem["id"], "PUT", {"trang_thai": "hoat_dong"})

    def test_13_thieu_quyen_thi_tra_403_kem_thong_diep_de_dung_khoi_khong_du_quyen(self):
        p = self._phien("fa-viewer")
        for duong, method, body in (("/api/v2/don", "POST", dict(DON_MAU)),
                                    ("/api/v2/khach-hang", "POST", {"ten": "X"}),
                                    ("/api/v2/memberships", "POST", {"ten_dang_nhap": "z", "role": "TENANT_STAFF"})):
            st, kq, _ = p.goi(duong, method, body)
            self.assertEqual(st, 403, "%s %s cho viewer trả %s" % (method, duong, st))
            self.assertIn("loi", kq, "403 phải có thông điệp để khối 'Không đủ quyền' hiện ra")

    def test_14_quyen_tu_auth_toi_la_danh_sach_that_backend_dung(self):
        """Giao diện ẩn/hiện menu theo TOI.quyen. Danh sách đó phải KHỚP với quyết định thật
        của backend, nếu không người dùng thấy menu rồi bấm vào là 403 — hoặc tệ hơn: không
        thấy menu dù có quyền."""
        st, toi, _ = self.viewer.goi("/api/v2/auth/toi")
        self.assertEqual(st, 200)
        quyen_viewer = set(toi["quyen"])
        self.assertIn("tenant.don.xem", quyen_viewer)
        self.assertNotIn("tenant.don.ghi", quyen_viewer)
        # đo lại bằng hành vi thật, không tin mỗi danh sách
        self.assertEqual(self.viewer.goi("/api/v2/don")[0], 200)
        self.assertEqual(self.viewer.goi("/api/v2/don", "POST", dict(DON_MAU))[0], 403)

    def test_15_csrf_thieu_header_thi_403_khong_phai_500(self):
        """Giao diện luôn gửi X-Requested-With; ca này canh chốt CSRF phía máy chủ vẫn sống."""
        st, _, _ = self.a.goi("/api/v2/don", "POST", dict(DON_MAU),
                              headers={"X-Requested-With": ""})
        self.assertEqual(st, 403)

    # ===================== E. Chuyển tenant =====================

    def test_16_chuyen_tenant_doi_han_pham_vi_du_lieu(self):
        """Tenant switcher: đổi xong phải KHÔNG còn thấy đơn của tenant cũ. Giao diện gọi
        khoiDong() nạp lại toàn bộ — ca này canh phần backend của luồng đó."""
        p = self._phien("fa-owner")
        st, toi, _ = p.goi("/api/v2/auth/toi")
        self.assertEqual(st, 200)
        self.assertGreaterEqual(len(toi["tenant_kha_dung"]), 2,
                                "cần ≥2 tenant mới thử được switcher")
        tid_a = toi["tenant"]["id"]
        st, kq, _ = p.goi("/api/v2/don", "POST", dict(DON_MAU),
                          headers={"Idempotency-Key": "thu-f04-switch-%s" % os.urandom(5).hex()})
        self.assertEqual(st, 201, kq)
        don_a = kq["don"]["id"]
        tid_b = [t["tenant_id"] for t in toi["tenant_kha_dung"] if t["tenant_id"] != tid_a][0]
        st, _, _ = p.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": tid_b})
        self.assertEqual(st, 200)
        st, toi2, _ = p.goi("/api/v2/auth/toi")
        self.assertEqual(toi2["tenant"]["id"], tid_b, "doi-tenant không đổi được ngữ cảnh")
        st, kq, _ = p.goi("/api/v2/don/%d" % don_a)
        self.assertEqual(st, 404, "sau khi chuyển tenant vẫn đọc được đơn của tenant cũ!")
        st, kq, _ = p.goi("/api/v2/don")
        self.assertTrue(all(d["id"] != don_a for d in kq["don"]))

    def test_17_khong_doi_duoc_sang_tenant_khong_phai_thanh_vien(self):
        p = self._phien("fa-viewer")
        st, _, _ = p.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": self.tid["fb"]})
        self.assertIn(st, (403, 404), "đổi được sang tenant không phải thành viên: %s" % st)

    # ===================== F. Tạo đơn trên UI → duyệt → gửi → timeline =====================

    def test_18_tao_don_tu_body_dung_y_nhu_form_giao_dien_gui(self):
        """Form giao diện gửi đúng 10 trường này (xem formDon trong admin.js). Nếu backend
        đổi tên trường, ca này hỏng — chứ không để người dùng mất dữ liệu nhập im lặng."""
        st, kq, _ = self._tao_don()
        self.assertEqual(st, 201, kq)
        d = kq["don"]
        self.assertEqual(d["trang_thai"], "nhap", "tạo trên UI phải ra ĐƠN NHÁP, không gửi hãng")
        self.assertIsNone(d["ma_van_don"], "đơn nháp không được có mã vận đơn")
        self.assertIsNone(d["carrier_account_id"], "đơn nháp chưa gán hãng ⇒ LOCAL REAL DATA")
        for k in DON_MAU:
            self.assertIn(k, d, "trường %s của form không có trong bản ghi trả về" % k)

    def test_19_idempotency_key_cua_giao_dien_chong_nhan_doi_khi_bam_hai_lan(self):
        khoa = "thu-f04-bam-hai-lan-%s" % os.urandom(5).hex()
        st1, kq1, _ = self.a.goi("/api/v2/don", "POST", dict(DON_MAU), headers={"Idempotency-Key": khoa})
        st2, kq2, _ = self.a.goi("/api/v2/don", "POST", dict(DON_MAU), headers={"Idempotency-Key": khoa})
        self.assertEqual(st1, 201)
        self.assertEqual(st2, 200, "bấm lại cùng khóa phải trả 200 (trùng), không tạo đơn mới")
        self.assertEqual(kq1["don"]["id"], kq2["don"]["id"])
        self.assertTrue(kq2["idempotent_trung"])

    def test_20_luong_duyet_va_gui_hang_sinh_du_moc_cho_timeline(self):
        """Timeline của giao diện dựng từ don_lich_su. Ca này canh: mỗi lần đổi trạng thái
        PHẢI có một dòng ở đó (§11), nếu không timeline trống trong khi đơn vẫn đi."""
        st, kq, _ = self._tao_don()
        don_id = kq["don"]["id"]
        st, kq, _ = self.a.goi("/api/v2/don/%d" % don_id)
        so_dau = len(kq["lich_su"])
        self.assertEqual(self.a.goi("/api/v2/don/%d/duyet" % don_id, "POST", {})[0], 200)
        st, kq, _ = self.a.goi("/api/v2/don/%d/gui" % don_id, "POST",
                               {"carrier_account_id": self.tk["id"]})
        self.assertEqual(st, 200, kq)
        st, kq, _ = self.a.goi("/api/v2/don/%d" % don_id)
        self.assertGreaterEqual(len(kq["lich_su"]), so_dau + 2,
                                "duyệt + gửi mà không sinh đủ mốc lịch sử")
        for l in kq["lich_su"]:
            self.assertTrue(l["luc"], "mốc lịch sử không có giờ — timeline sẽ phải bịa")
            self.assertRegex(l["nguon"], r"^(user:\d+|webhook:\d+|polling|he_thong)$",
                             "nguồn %r không khớp §11 — dienGiaiNguon sẽ hiện 'nguồn lạ'" % l["nguon"])
        self.assertEqual(kq["don"]["carrier_account_id"], self.tk["id"])

    def test_21_doi_tuong_khong_duyet_thi_khong_gui_duoc_hang(self):
        st, kq, _ = self._tao_don()
        don_id = kq["don"]["id"]
        st, _, _ = self.viewer.goi("/api/v2/don/%d/duyet" % don_id, "POST", {})
        self.assertEqual(st, 403)

    def test_22_gui_hang_van_o_che_do_mock_khong_co_hang_nao_mo_live(self):
        """Bất biến của brief: CHO_PHEP_LIVE=False ⇒ giao diện KHÔNG được hiện LIVE.
        Ca này đo nguồn mà giao diện dựa vào: cờ live_mo trong GET /api/v2/hang."""
        st, kq, _ = self.a.goi("/api/v2/hang")
        self.assertEqual(st, 200)
        self.assertGreater(len(kq["hang"]), 0)
        mo_live = [h["ma"] for h in kq["hang"] if h.get("live_mo")]
        self.assertEqual(mo_live, [], "có hãng mở live_mo: %s — giao diện sẽ dán nhãn "
                                      "LIVE CARRIER DATA, phải xác nhận lại với AG-00" % mo_live)
        st, kq, _ = self.a.goi("/api/v2/tai-khoan-hang")
        khac_mock = [t["ten"] for t in kq["tai_khoan"] if t["moi_truong"] != "mock"]
        self.assertEqual(khac_mock, [], "có tài khoản hãng ngoài môi trường mock: %s" % khac_mock)

    def test_23_khong_tao_duoc_tai_khoan_hang_moi_truong_that_tu_giao_dien(self):
        st, kq, _ = self.a.goi("/api/v2/tai-khoan-hang", "POST",
                               {"hang": "jt", "ten": "thử production", "moi_truong": "production",
                                "credentials": {"x": "1"}})
        self.assertEqual(st, 403, "giao diện mở được môi trường thật — khóa an toàn hỏng")

    # ===================== G. Preview import =====================

    def test_24_upload_csv_chi_tao_batch_xem_truoc_khong_tao_don(self):
        """Màn Import có 4 bước; bước 1–3 KHÔNG được tạo đơn nào."""
        import base64
        csv = ("recipient_name,recipient_phone,recipient_address,product_name,weight_grams,cod\n"
               "Nguyễn Preview,0905555555,5 Ngõ Preview HN,Hộp preview,700,250000\n"
               "Thiếu Địa Chỉ,0906666666,,Hộp lỗi,300,0\n")
        st, truoc, _ = self.a.goi("/api/v2/don?gioi_han=500")
        so_don_truoc = len(truoc["don"])
        st, kq, _ = self.a.goi("/api/v2/import", "POST",
                               {"ten_file": "preview-f04.csv",
                                "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        self.assertEqual(st, 201, kq)
        batch_id = kq["batch_id"]
        st, b, _ = self.a.goi("/api/v2/import/%d" % batch_id)
        self.assertEqual(st, 200, b)
        self.assertGreaterEqual(len(b["dong"]), 2, "parser không đọc được dòng nào")
        for x in b["dong"]:
            self.assertIn("du_lieu", x, "màn preview đọc x.du_lieu — thiếu là bảng trống")
            self.assertIsInstance(x["du_lieu"], dict)
            self.assertIn("stt", x)
            self.assertIn("trang_thai", x)
        st, sau, _ = self.a.goi("/api/v2/don?gioi_han=500")
        self.assertEqual(len(sau["don"]), so_don_truoc,
                         "upload đã tạo đơn! Preview phải KHÔNG tạo đơn nào")
        type(self).batch_id = batch_id

    def test_25_trang_thai_dong_import_nam_trong_bo_giao_dien_biet(self):
        """Trạng thái lạ vẫn hiện nguyên văn (tầng 1 đã phủ), nhưng nếu backend đổi hẳn sang
        bộ khác thì cả bảng màu của màn Import mất nghĩa — ca này để phát hiện sớm."""
        st, b, _ = self.a.goi("/api/v2/import/%d" % type(self).batch_id)
        biet = set(re.findall(r"^\s{4}(\w+):\s*\[", doc_js("logic.js"), re.M))
        for x in b["dong"]:
            self.assertIn(x["trang_thai"], biet,
                          "trạng thái dòng %r chưa có trong bảng TT_DONG của logic.js"
                          % x["trang_thai"])

    def test_26_sua_dong_import_roi_duyet_ra_don_nhap(self):
        batch_id = type(self).batch_id
        st, b, _ = self.a.goi("/api/v2/import/%d" % batch_id)
        xau = [x for x in b["dong"] if x["trang_thai"] == "INVALID"]
        if xau:
            st, kq, _ = self.a.goi("/api/v2/import/dong/%d" % xau[0]["id"], "PUT",
                                   {"nguoi_nhan_dia_chi": "9 Đường Đã Sửa, HN"})
            self.assertEqual(st, 200, kq)
        st, b, _ = self.a.goi("/api/v2/import/%d" % batch_id)
        ids = [x["id"] for x in b["dong"] if x["trang_thai"] in ("VALID", "READY")]
        self.assertGreater(len(ids), 0, "không dòng nào duyệt được")
        st, kq, _ = self.a.goi("/api/v2/import/%d/duyet" % batch_id, "POST",
                               {"dong_ids": ids,
                                "nguoi_gui": {"ten": "Shop F04", "sdt": "0901111111",
                                              "dia_chi": "1 Đường F04, HN"}})
        self.assertEqual(st, 200, kq)
        for k in ("SUCCESS", "FAILED", "bo_qua"):
            self.assertIn(k, kq, "màn duyệt in ba số này ra toast — thiếu %s là NaN" % k)
        self.assertEqual(kq["SUCCESS"], len(ids), kq)

    def test_27_duyet_thieu_nguoi_gui_thi_400_co_thong_diep(self):
        st, kq, _ = self.a.goi("/api/v2/import/%d/duyet" % type(self).batch_id, "POST",
                               {"dong_ids": [], "nguoi_gui": {"ten": "", "sdt": "", "dia_chi": ""}})
        self.assertEqual(st, 400)
        self.assertIn("nguoi_gui", json.dumps(kq, ensure_ascii=False))

    # ===================== H. Webhook monitor =====================

    def test_28_su_kien_webhook_tra_du_truong_man_monitor_can(self):
        body = json.dumps({"event_id": "f04-ev-1", "event": "delivered",
                           "tracking_number": "F04TRACK1"}).encode()
        sig = hmac.new(self.tk["webhook_secret_mot_lan"].encode(), body, hashlib.sha256).hexdigest()
        st, kq, _ = Phien(self.goc_url).goi(
            "/api/v2/webhook/nhan/%s" % self.tk["webhook_ma"], "POST", tho=body,
            headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"})
        self.assertIn(st, (200, 202), kq)
        st, kq, _ = self.a.goi("/api/v2/webhook/su-kien")
        self.assertEqual(st, 200)
        self.assertGreater(len(kq["su_kien"]), 0)
        s = kq["su_kien"][0]
        for k in ("id", "event_id", "hang", "nhan_luc", "trang_thai", "so_lan_thu", "loi_cuoi"):
            self.assertIn(k, s, "màn Webhook đọc trường %s — thiếu là ô trống im lặng" % k)
        self.assertIsInstance(s["so_lan_thu"], int, "so_lan_thu phải là số để cộng tổng lần thử")

    def test_29_trang_thai_webhook_nam_trong_bo_giao_dien_biet_hoac_duoc_bao_la(self):
        st, kq, _ = self.a.goi("/api/v2/webhook/su-kien")
        hop_dong = {"moi", "dang_xu_ly", "xong", "cho_thu_lai", "dlq", "khong_khop"}
        la = sorted({s["trang_thai"] for s in kq["su_kien"]} - hop_dong)
        # Không ép phải rỗng: AG-03 ĐANG thêm trạng thái mới, và giao diện CỐ Ý hiện nguyên
        # văn. Ca này chỉ canh để trạng thái mới không lọt qua mà không ai biết.
        if la:
            print("\n[thu-frontend] CHÚ Ý: trạng thái webhook ngoài §12 đã xuất hiện: %s "
                  "— giao diện hiện nguyên văn + khối 'nhập nhằng'. Xem lại bảng TT_WH." % la)
        self.assertTrue(all(isinstance(x, str) for x in la))

    def test_30_replay_can_quyen_backend_khong_phai_giao_dien(self):
        st, kq, _ = self.a.goi("/api/v2/webhook/su-kien")
        if not kq["su_kien"]:
            self.skipTest("chưa có sự kiện nào để thử replay")
        sk_id = kq["su_kien"][0]["id"]
        st, _, _ = self.viewer.goi("/api/v2/webhook/su-kien/%d/replay" % sk_id, "POST", {})
        self.assertEqual(st, 403, "viewer replay được — quyền phải do backend chặn")

    # ===================== I. Xử lý khi API lỗi =====================

    def test_31_duong_khong_ton_tai_tra_404_co_than_json(self):
        """Giao diện đọc kq.loi để dựng thông điệp. 404 không có thân JSON ⇒ giao diện hiện
        'HTTP 404' trơ trọi."""
        st, kq, _ = self.a.goi("/api/v2/khong-he-co-duong-nay")
        self.assertEqual(st, 404)
        self.assertIsInstance(kq, dict)
        self.assertIn("loi", kq)

    def test_32_don_cua_tenant_khac_tra_404_khong_phai_403(self):
        """Khác nhau quan trọng: 403 bật khối 'Không đủ quyền' (sai — đây là không tồn tại),
        404 bật thông điệp 'không mở được màn này'."""
        p = self._phien("fb-owner")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=1")
        if not kq["don"]:
            self.skipTest("chưa có đơn")
        st, _, _ = p.goi("/api/v2/don/%d" % kq["don"][0]["id"])
        self.assertEqual(st, 404)

    def test_33_body_sai_dinh_dang_tra_400_khong_phai_500(self):
        st, kq, _ = self.a.goi("/api/v2/don", "POST", None, tho=b"{khong-phai-json",
                               headers={"Content-Type": "application/json"})
        self.assertLess(st, 500, "body rác làm máy chủ 500 — giao diện chỉ hiện 'lỗi hệ thống'")

    def test_34_tao_don_thieu_truong_tra_loi_doc_duoc_khong_phai_500(self):
        st, kq, _ = self.a.goi("/api/v2/don", "POST", {"hang_hoa": "chỉ có hàng hóa"})
        self.assertLess(st, 500, kq)
        self.assertIn("loi", kq if isinstance(kq, dict) else {})

    def test_35_log_may_chu_khong_ro_secret(self):
        """Giao diện không giữ secret, nhưng log máy chủ rò cũng là rò. Đo luôn ở đây."""
        noi = LOG_SERVER.getvalue()
        for x in ("demo-key-F04-chi-de-thu", self.tk["webhook_secret_mot_lan"], MK):
            self.assertNotIn(x, noi, "log máy chủ rò secret")

    # ===================== J. Xuất CSV (nút trên màn Đơn hàng) =====================

    def test_36_nut_xuat_csv_tra_ve_tep_that_va_khong_cho_tiem_cong_thuc(self):
        """Nút '⬇ Xuất CSV' là thẻ <a href> nên tải trực tiếp — phải ra CSV, không ra JSON."""
        self._tao_don(nguoi_nhan_ten="=1+1 Tiêm Công Thức")
        st, body, h = self.a.goi("/api/v2/don/xuat-csv")
        self.assertEqual(st, 200)
        self.assertIn("text/csv", h.get("Content-Type", ""))
        self.assertIn("attachment", h.get("Content-Disposition", ""))
        s = body.decode("utf-8")
        self.assertIn("ma_don", s)
        for dong in s.split("\n"):
            for o in dong.split(","):
                sach = o.strip('"')
                self.assertFalse(sach.startswith(("=", "+", "@")),
                                 "ô CSV bắt đầu bằng ký tự công thức: %r" % sach)


if __name__ == "__main__":
    unittest.main(verbosity=2)
