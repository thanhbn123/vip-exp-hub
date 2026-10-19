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
import datetime
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
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


def bang_mot_phan():
    """Những đường khai `mot_phan: true` — đường ĐÃ CÓ nhưng chưa đủ (thiếu tham số, hoặc trả
    siêu dữ liệu chứ chưa trả thứ cuối cùng). Đọc từ chính `logic.js` để không có bản thứ hai."""
    ma = doc_js("logic.js")
    i = ma.index("const API_CHO_BACKEND = [")
    j = ma.index("\n  ];", i)
    ra = set()
    for muc in ma[i:j].split("\n    {"):
        if "mot_phan: true" in muc:
            m = re.search(r'duong:\s*"([^"]+)"', muc)
            if m:
                ra.add(m.group(1))
    return ra


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


# ============================================================================
# G22/AG-06 — HỢP ĐỒNG LỌC Ở MÁY CHỦ: đọc các danh sách KHAI TRONG GIAO DIỆN
# ============================================================================
# Bốn mặt phải khớp nhau, mỗi mặt một phép đo ở dưới:
#   (1) ngữ nghĩa lọc   — `test_37`
#   (2) phân trang      — `test_38`
#   (3) tenant          — `test_39`
#   (4) phạm vi giao diện — `test_40` (+ tầng 3, `thu_giao_dien/01_luong_chinh.spec.js` ca 03)
# Các hàm dưới đây đọc THẲNG `admin/logic.js` và `admin/admin.js` — không chép danh sách sang
# Python: hai bản nội dung là hai bản sẽ lệch nhau (§14.6). Đọc không được ⇒ ca thử HỎNG, chứ
# không lặng lẽ kiểm 0 mục rồi báo đạt (§12.1 luật 5).

def _khoi_js(ten, mo_dau):
    ma = doc_js(ten)
    i = ma.index(mo_dau)
    j = ma.index("];", i)
    return ma[i:j]


def ds_tham_so_may_chu():
    """Tham số giao diện khai là GỬI LÊN MÁY CHỦ (`L.THAM_SO_MAY_CHU`)."""
    return re.findall(r'"([a-z_]+)"', _khoi_js("logic.js", "const THAM_SO_MAY_CHU = ["))


def ds_loc_tai_trang():
    """Điều kiện giao diện khai là CHỈ lọc tại trang (`L.THAM_SO_LOC_TAI_GIAO_DIEN`)."""
    return re.findall(r'"([a-z_]+)"', _khoi_js("logic.js", "const THAM_SO_LOC_TAI_GIAO_DIEN = ["))


def ds_sap_xep_giao_dien():
    """Khoá sắp xếp giao diện khai (`L.SAP_XEP_DON`) — phải nằm trong danh sách trắng của máy chủ."""
    return re.findall(r'\["([a-z_]+)",\s*"', _khoi_js("logic.js", "const SAP_XEP_DON = ["))


def ds_dieu_kien_man_don():
    """Tên khoá mà `don()` trong admin.js THẬT SỰ đọc từ màn hình (`docDieuKien`).

    Đây là phép đo bắt lỗi "thêm một ô lọc rồi quên khai nó ở logic.js": khoá nào không nằm
    trong `THAM_SO_MAY_CHU` lẫn `THAM_SO_LOC_TAI_GIAO_DIEN` thì `chiaDieuKien()` bỏ vào túi
    `la` — và nếu ai đó lại im lặng bỏ qua túi ấy thì điều kiện người dùng chọn biến mất.
    """
    ma = doc_js("admin.js")
    i = ma.index("const docDieuKien = () => ({")
    j = ma.index("});", i)
    return re.findall(r'([a-z_]+):', ma[i:j])


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

    def test_04_moi_trang_demo_g00_khong_bi_pha(self):
        """F05: MỌI trang demo G00 dùng CHUNG CSS — sửa CSS không được làm chúng gãy.

        Bản cũ ghim `len(ten_trang) == 10`. Mười là số trang tại lượt đo G00; thêm một trang
        hợp lệ (`best.html`) làm phép thử ĐỎ dù không trang nào gãy. Bất biến đúng là:
          · danh sách trang ĐỌC TỪ ĐĨA, không chép tay;
          · danh sách KHÁC RỖNG (chốt chống phép đo rỗng);
          · MỌI trang đọc được phải tải được và dùng đúng hai tệp dùng chung.
        Số trang là KẾT QUẢ ĐO TẠI CHỖ, không còn là kỳ vọng ghim.
        """
        p = Phien(self.goc_url)
        ten_trang = sorted(x for x in os.listdir(os.path.join(GOC_DU_AN, "pages")) if x.endswith(".html"))
        self.assertGreaterEqual(len(ten_trang), 1,
                                "không có trang demo nào — phép đo rỗng, không chứng minh gì")
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
        """Mỗi đường giao diện khai là ĐANG DÙNG phải có thật trên máy chủ.

        `<id>` phải được thay bằng id THẬT trước khi bắn. Bản đầu không thay, vì lúc viết
        `API_DANG_DUNG` chỉ có đường GET không tham số; ngày 15/10 AG-00 khai thêm 11 đường
        G04 có `<id>` và ca này báo hỏng với `POST /api/v2/don/<id>/tu-choi → 404` — đó là
        404 cho chuỗi `<id>` chưa thay, KHÔNG phải route thiếu. Đo nhầm thứ mình nghĩ mình
        đang đo chính là §12.1: công cụ kiểm chứng tự nó phải được kiểm trước khi tin.
        """
        ds = api_dang_dung()
        self.assertGreaterEqual(len(ds), 8, "rút được quá ít endpoint — phép đo đang rỗng")
        don_id = self._tao_don()[1]["don"]["id"]
        for method, duong_khai in ds:
            duong = duong_khai.replace("<id>", str(don_id))
            # Thân rỗng cho POST/PUT: ca này chỉ hỏi "route CÓ tồn tại không", nên 400 (thiếu
            # trường) là câu trả lời ĐẠT — nó chứng minh route đã nhận và đã kiểm dữ liệu.
            st, kq, _ = self.a.goi(duong, method, {} if method in ("POST", "PUT") else None)
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
        mot_phan = bang_mot_phan()
        self.assertGreaterEqual(len(bang), 4, "rút được quá ít mục — phép đo đang rỗng")
        don_id = self._tao_don()[1]["don"]["id"]
        thay_the = {"<id>": str(don_id)}
        da_kiem, bo_qua = [], []
        for duong, method in bang:
            if duong in mot_phan:
                # Bỏ qua theo CỜ `mot_phan: true` trong chính logic.js, KHÔNG viết cứng đường
                # dẫn ở đây: viết cứng thì mỗi mục một-phần mới lại phải sửa mã Python, và
                # người sửa dễ quên — lúc đó ca thử lại báo hỏng giả. Mục bị bỏ qua được IN RA
                # ở cuối ca, không im lặng (§12.1 luật 5: nói rõ cái gì nằm ngoài phạm vi).
                bo_qua.append((method, duong))
                continue
            that = duong
            for k, v in thay_the.items():
                that = that.replace(k, v)
            m1 = method.split(" ")[0]
            st, kq, _ = self.a.goi(that, m1, {} if m1 in ("POST", "PUT") else None)
            da_kiem.append((m1, that, st))
            self.assertIn(st, (404, 405),
                          "giao diện khai '%s %s' là CHỜ BACKEND nhưng máy chủ trả %s — "
                          "backend đã có, phải gỡ nhãn và nối màn vào" % (m1, that, st))
        print("\n      [ca09] đã bắn thật: %s" % (da_kiem,))
        print("      [ca09] bỏ qua vì mot_phan=true: %s" % (bo_qua or "không có",))
        self.assertGreaterEqual(len(da_kiem), 3, da_kiem)

    def test_10_may_chu_loc_nang_cao_that_su_va_TU_CHOI_tham_so_la(self):
        """BẤT BIẾN MỚI (G22/AG-06) — `GET /api/v2/don` LỌC NÂNG CAO Ở MÁY CHỦ và TỪ CHỐI
        (400) tham số nó không nhận.

        Ca này là vế ĐỐI LẬP của bản trước. Bản trước khẳng định "máy chủ CHƯA lọc nâng cao"
        và đạt được là nhờ máy chủ BỎ QUA IM LẶNG mọi tham số lạ — tức là nó đo đúng cái hỏng
        mà G12 sinh ra để diệt. Nay AG-02 đã cắm route vào `app/truy_van.py::BANG_DON`
        (hợp đồng: docs/G22_HOPDONG_FRONTEND.md) nên bất biến đảo chiều:

          (a) một điều kiện KHÔNG khớp đơn nào ⇒ kết quả PHẢI RỖNG (không phải "trả hết");
          (b) tham số lạ ⇒ **400**, không được bỏ qua im lặng;
          (c) ba tham số máy chủ vốn đã hỗ trợ vẫn phải có hiệu lực;
          (d) phản hồi phải mang đủ trường phân trang mà giao diện đang đọc.

        ĐỐI CHỨNG ÂM (chạy được, không phải lời hứa): đặt lại máy chủ ĐÚNG BẢN TRƯỚC AG-02
        rồi chạy lại chính ca này —

            python3 thu_frontend/thu_http.py --doi-chung-am <đường-dẫn app/server.py BẢN CŨ>

        Cây sao chép ấy PHẢI làm ca này ĐỎ, và đỏ vì đúng câu "máy chủ BỎ QUA điều kiện ...".
        """
        for _ in range(2):
            self._tao_don()

        def dong_cua(kq):
            """Danh sách đơn của một phản hồi: `dong` là khoá của hợp đồng mới, `don` là khoá
            tương thích mà AG-02 còn giữ trong lượt chuyển tiếp. Ca này đo PHÉP LỌC; việc
            phản hồi có đủ khoá hay không do `test_40` canh — đọc cả hai ở đây để ca này
            không đỏ vì lý do của ca khác (đỏ vì lý do khác là một phép đo khác)."""
            return kq.get("dong", kq.get("don"))

        st, tat_ca, _ = self.a.goi("/api/v2/don?gioi_han=500")
        self.assertEqual(st, 200)
        self.assertIsNotNone(dong_cua(tat_ca), "phản hồi không có danh sách đơn (cả `dong` lẫn `don`)")
        n = len(dong_cua(tat_ca))
        self.assertGreater(n, 0, "nền không có đơn nào ⇒ ca này không chứng minh được gì")

        # (a) điều kiện KHÔNG khớp đơn nào ⇒ RỖNG. Mỗi dòng là một trường lọc khác nhau của
        # hợp đồng, để ca không chỉ đo một trường rồi suy ra cả sáu.
        for ten, truy_van in (
                ("cod_tu", "cod_tu=999999999"),
                ("tu_ngay", "tu_ngay=2099-01-01"),
                ("trang_thai_giao", "trang_thai_giao=khong_ton_tai"),
                ("hang", "hang=khong_co_hang"),
                ("carrier_account_id", "carrier_account_id=999999"),
                ("q", "q=khong-co-don-nao-nhu-the-nay"),
        ):
            st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + truy_van)
            self.assertEqual(st, 200, "%s → %s: %s" % (ten, st, kq))
            self.assertEqual(
                len(dong_cua(kq) or []), 0,
                "máy chủ BỎ QUA điều kiện %r (trả về %d/%d đơn) — lọc nâng cao CHƯA chạy ở "
                "máy chủ; đây đúng là cái hỏng mà ca này canh"
                % (ten, len(dong_cua(kq) or []), n))

        # (b) tham số lạ ⇒ 400. Bỏ qua im lặng là để người gõ sai tên nhận về danh sách KHÔNG
        # LỌC mà tin rằng đã lọc — không có gì báo, chỉ nhiều dòng hơn mong đợi.
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&trang_thai_gia0=nhap")
        self.assertEqual(st, 400,
                         "tham số lạ phải bị TỪ CHỐI (400); nhận %s — bỏ qua im lặng là hỏng "
                         "lâu dài mà không ai biết" % st)
        self.assertIn("loi", kq, "400 phải có thông điệp để giao diện hiện nguyên văn")

        # (c) ba tham số máy chủ vốn đã hỗ trợ: vẫn phải có hiệu lực thật
        st, kq, _ = self.a.goi("/api/v2/don?trang_thai=huy&gioi_han=500")
        self.assertEqual(st, 200)
        self.assertTrue(all(d["trang_thai"] == "huy" for d in dong_cua(kq) or []))
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=1")
        self.assertLessEqual(len(dong_cua(kq) or []), 1)

        # (d) hợp đồng phân trang: thiếu một trường là giao diện hết phân trang đúng được
        for khoa in ("dong", "tong", "tong_chinh_xac", "gioi_han", "trang", "con_nua",
                     "sap_xep", "loc_bo_qua"):
            self.assertIn(khoa, tat_ca, "phản hồi thiếu %r — giao diện không phân trang được" % khoa)
        self.assertEqual(tat_ca["tong"], n, "`tong` phải là số dòng KHỚP ĐIỀU KIỆN, không phải số dòng trang")
        self.assertEqual(tat_ca["trang"], 1)

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


    # ========== K. (G22/AG-06) HỢP ĐỒNG LỌC Ở MÁY CHỦ — BỐN MẶT PHẢI KHỚP ==========
    # Mỗi ca dưới đây đo MỘT mặt và in ra con số đo được. Bốn mặt:
    #   1 ngữ nghĩa lọc (test_37) · 2 phân trang (test_38) · 3 tenant (test_39) ·
    #   4 phạm vi giao diện (test_40, và ca 03 của tầng 3 đo trên DOM thật).
    # Hợp đồng: `docs/G22_HOPDONG_FRONTEND.md`; nguồn sự thật: `app/truy_van.py::BANG_DON`.

    def _don_g22(self, so, cod_goc, nhan):
        """Dựng `so` đơn có COD tăng dần + tên người nhận đánh dấu.

        Fixture RIÊNG của khối này, không mượn đơn của ca khác: mượn thì ca này đo dữ liệu của
        ca kia, và thứ tự chạy đổi là nó đổi theo (§12.1 — phép đo phải đứng một mình).
        """
        ra = []
        for i in range(so):
            st, kq, _ = self._tao_don(cod=cod_goc + i * 1000,
                                      nguoi_nhan_ten="%s-%d" % (nhan, i),
                                      hang_hoa="Kiện %s-%d" % (nhan, i))
            self.assertIn(st, (200, 201), kq)
            ra.append(kq["don"])
        return ra

    def test_37_ngu_nghia_loc_o_may_chu_khop_hop_dong(self):
        """MẶT 1 — NGỮ NGHĨA LỌC. Mỗi trường lọc của hợp đồng phải lọc ĐÚNG NGHĨA mà giao diện
        hứa với người dùng: hai đầu khoảng BAO GỒM, `q` tìm cả `hang_hoa`, `hang` đi qua tài
        khoản hãng, `can_doi_soat` là cờ 0/1, `sap_xep` là danh sách trắng.

        Đối chứng đường: mỗi vế "phải khớp" đều có vế "phải rỗng" đi kèm — chỉ khẳng định
        chiều khớp thì một bộ lọc LUÔN trả về 0 dòng cũng "đạt".
        """
        self._don_g22(5, 700000, "G22-M1")
        q = "q=G22-M1-"
        # COD: hai đầu BAO GỒM. `cod_tu=702000` mà thiếu đơn 702000 là lọc lệch một đồng.
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&cod_tu=702000")
        self.assertEqual(st, 200, kq)
        self.assertEqual(sorted(d["cod"] for d in kq["dong"]), [702000, 703000, 704000],
                         "cod_tu phải BAO GỒM chính giá trị chặn")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&cod_den=701000")
        self.assertEqual(sorted(d["cod"] for d in kq["dong"]), [700000, 701000],
                         "cod_den phải BAO GỒM chính giá trị chặn")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&cod_tu=701000&cod_den=703000")
        self.assertEqual(sorted(d["cod"] for d in kq["dong"]), [701000, 702000, 703000])
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&cod_tu=800000")
        self.assertEqual(len(kq["dong"]), 0, "khoảng COD không khớp mà vẫn trả dòng")

        # NGÀY: `tu_ngay`/`den_ngay` bao gồm CẢ NGÀY. Đây là chỗ dễ sai nhất: so `<=` cùng ngày
        # sẽ loại sạch mọi đơn TRONG ngày đó (vì "2026-10-17 08:00" > "2026-10-17").
        hom_nay = datetime.date.today().isoformat()
        hom_qua = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&tu_ngay=" + hom_nay)
        self.assertEqual(len(kq["dong"]), 5, "tu_ngay=hôm nay phải BAO GỒM đơn tạo trong hôm nay")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&den_ngay=" + hom_nay)
        self.assertEqual(len(kq["dong"]), 5, "den_ngay=hôm nay phải BAO GỒM CẢ NGÀY hôm nay")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&den_ngay=" + hom_qua)
        self.assertEqual(len(kq["dong"]), 0, "den_ngay=hôm qua mà vẫn thấy đơn hôm nay")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&tu_ngay=khong-phai-ngay")
        self.assertEqual(st, 400, "ngày sai định dạng phải bị TỪ CHỐI, không lặng lẽ bỏ qua")

        # `q` ở MÁY CHỦ tìm 5 cột, gồm `hang_hoa` — giao diện cũ chỉ tìm 4 cột TẠI TRANG. Chuyển
        # lên máy chủ là MỞ RỘNG phạm vi tìm, và điều đó phải đo được chứ không chỉ nói.
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&q=" +
                               urllib.parse.quote("Kiện G22-M1-3"))
        self.assertEqual([d["cod"] for d in kq["dong"]], [703000],
                         "`q` ở máy chủ phải tìm được trong `hang_hoa`")

        # `hang` đi qua `carrier_accounts` CỦA CHÍNH TENANT; `carrier_account_id` là cột thật.
        # Dựng một đơn ĐÃ GỬI HÃNG (adapter mock, không ra mạng) để hai trường này có dữ liệu.
        ds = self._don_g22(1, 750000, "G22-M1B")
        don_gui = ds[0]
        self.assertEqual(self.a.goi("/api/v2/don/%d/duyet" % don_gui["id"], "POST", {})[0], 200)
        st, kq, _ = self.a.goi("/api/v2/don/%d/gui" % don_gui["id"], "POST",
                               {"carrier_account_id": self.tk["id"]})
        self.assertEqual(st, 200, kq)
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&q=G22-M1B-0&carrier_account_id=%d"
                               % self.tk["id"])
        self.assertEqual([d["id"] for d in kq["dong"]], [don_gui["id"]],
                         "carrier_account_id không lọc đúng tài khoản hãng của đơn")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&q=G22-M1B-0&carrier_account_id=999999")
        self.assertEqual(len(kq["dong"]), 0, "carrier_account_id không tồn tại mà vẫn trả dòng")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&q=G22-M1B-0&hang=vtp")
        self.assertEqual([d["id"] for d in kq["dong"]], [don_gui["id"]],
                         "`hang` không lọc được qua bảng tài khoản hãng")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&q=G22-M1B-0&hang=khong_co_hang")
        self.assertEqual(len(kq["dong"]), 0)

        # `trang_thai` / `trang_thai_giao`: giá trị THẬT của đơn vừa gửi phải tìm lại được, và
        # mọi dòng trả về phải mang đúng giá trị ấy (không phải "lọc gần đúng").
        st, d1, _ = self.a.goi("/api/v2/don/%d" % don_gui["id"])
        tt, ttg = d1["don"]["trang_thai"], d1["don"]["trang_thai_giao"]
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&trang_thai=" + urllib.parse.quote(tt))
        self.assertIn(don_gui["id"], [d["id"] for d in kq["dong"]])
        self.assertTrue(all(d["trang_thai"] == tt for d in kq["dong"]))
        if ttg:
            st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&trang_thai_giao=" +
                                   urllib.parse.quote(ttg))
            self.assertIn(don_gui["id"], [d["id"] for d in kq["dong"]])

        # `can_doi_soat` là CỜ 0/1: cả hai chiều đều phải đúng trên chính dữ liệu trả về.
        for gt, mong in (("0", False), ("1", True)):
            st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&can_doi_soat=" + gt)
            self.assertEqual(st, 200, kq)
            self.assertTrue(all(bool(d["can_doi_soat_ket_qua"]) is mong for d in kq["dong"]),
                            "can_doi_soat=%s trả về dòng có cờ khác" % gt)

        # `sap_xep`: danh sách trắng, và chiều sắp xếp phải ĐO ĐƯỢC (không chỉ "không lỗi").
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&sap_xep=cod_cao")
        cods = [d["cod"] for d in kq["dong"]]
        self.assertEqual(cods, sorted(cods, reverse=True), "sap_xep=cod_cao không sắp giảm dần")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + q + "&sap_xep=cod_thap")
        cods = [d["cod"] for d in kq["dong"]]
        self.assertEqual(cods, sorted(cods), "sap_xep=cod_thap không sắp tăng dần")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&sap_xep=khong_co_khoa_nay")
        self.assertEqual(st, 400, "khoá sắp xếp lạ phải bị TỪ CHỐI, không rơi về mặc định im lặng")
        print("\n      [MẶT 1 · ngữ nghĩa lọc] cod 2 đầu bao gồm · ngày bao gồm cả ngày · "
              "q tìm cả hang_hoa · hang/carrier_account_id · trang_thai(_giao) · can_doi_soat · sap_xep")

    def test_38_phan_trang_khong_lap_khong_mat_tong_on_dinh(self):
        """MẶT 2 — PHÂN TRANG. Ba điều phải đo được, không suy ra từ "thấy ít dòng hơn":
          * `tong` ỔN ĐỊNH giữa các trang (đổi theo trang thì số trang vô nghĩa);
          * các trang KHÔNG lặp dòng và KHÔNG mất dòng (ghép trang = một lượt lấy đủ);
          * `con_nua` nói đúng, và `gioi_han` vượt trần bị KẸP **và trả ra giá trị thật**.
        """
        ds = self._don_g22(5, 800000, "G22-M2")
        ma = "q=G22-M2-&sap_xep=cod_cao"
        st1, t1, _ = self.a.goi("/api/v2/don?gioi_han=2&trang=1&" + ma)
        st2, t2, _ = self.a.goi("/api/v2/don?gioi_han=2&trang=2&" + ma)
        st3, t3, _ = self.a.goi("/api/v2/don?gioi_han=2&trang=3&" + ma)
        self.assertEqual([st1, st2, st3], [200, 200, 200], (t1, t2, t3))
        self.assertEqual([t1["tong"], t2["tong"], t3["tong"]], [5, 5, 5],
                         "`tong` đổi theo trang ⇒ số trang hiện trên giao diện là số bịa")
        ids1 = [d["id"] for d in t1["dong"]]
        ids2 = [d["id"] for d in t2["dong"]]
        ids3 = [d["id"] for d in t3["dong"]]
        self.assertEqual([len(ids1), len(ids2), len(ids3)], [2, 2, 1],
                         "chia trang sai số dòng (2/2/1 cho 5 đơn, mỗi trang 2)")
        self.assertEqual(set(ids1) & set(ids2), set(), "trang 1 và trang 2 LẶP dòng")
        self.assertEqual(set(ids1) & set(ids3), set(), "trang 1 và trang 3 LẶP dòng")
        self.assertEqual(sorted(ids1 + ids2 + ids3), sorted(d["id"] for d in ds),
                         "ba trang KHÔNG phủ đủ 5 đơn — phân trang làm MẤT dòng")
        self.assertTrue(t1["con_nua"] and t2["con_nua"], "còn trang sau mà `con_nua` nói không")
        self.assertFalse(t3["con_nua"], "trang cuối mà `con_nua` vẫn nói còn trang sau")
        # Ghép trang phải TRÙNG với một lượt lấy đủ: sắp xếp có khoá phá hoà nên thứ tự tất
        # định; nếu không, OFFSET cho ra lặp ở trang này và mất ở trang kia — hỏng im lặng
        # kinh điển của phân trang.
        st, t_all, _ = self.a.goi("/api/v2/don?gioi_han=5&trang=1&" + ma)
        self.assertEqual([d["id"] for d in t_all["dong"]], ids1 + ids2 + ids3,
                         "ghép ba trang LỆCH so với một lượt lấy đủ ⇒ thứ tự không tất định")
        # Hai cách đánh số cùng lúc là hai kết quả khác nhau ⇒ phải bị từ chối.
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=2&trang=1&lech=2")
        self.assertEqual(st, 400, "gửi cả `trang` lẫn `lech` phải bị từ chối: %s" % (kq,))
        # Trần `gioi_han`: KẸP (không phạt 400 — bấm quá đà là chuyện thường) nhưng giá trị
        # THẬT phải trả ra, nếu không giao diện tưởng mình đã xin 99 999 đơn.
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=99999")
        self.assertEqual(st, 200)
        self.assertEqual(kq["gioi_han"], 500,
                         "gioi_han vượt trần phải bị kẹp về 500 VÀ trả ra giá trị thật")
        print("\n      [MẶT 2 · phân trang] 3 trang (2/2/1) · tong=5 ổn định · không lặp không "
              "mất · con_nua đúng · gioi_han kẹp 99999→500")

    def test_39_loc_nang_cao_khong_ro_du_lieu_tenant_khac(self):
        """MẶT 3 — TENANT. Bộ lọc nâng cao chạy ở máy chủ, nên nó là chỗ MỚI để rò dữ liệu
        tenant khác: `hang` đi qua một câu con (`carrier_account_id IN (SELECT … WHERE
        tenant_id=?)`) và quên `tenant_id` ở đó là rò qua đường vòng — nhìn kết quả không
        thấy gì bất thường.

        Đối chứng đường BẮT BUỘC: cùng bộ lọc ấy, chạy trên tenant SỞ HỮU, phải RA đơn đó.
        Không có vế này thì "A thấy 0 dòng" cũng đúng khi bộ lọc hỏng hoàn toàn.
        """
        b = self._phien("fb-owner")
        # tài khoản hãng của B dùng CÙNG mã hãng "vtp" với A: nếu câu con thiếu tenant_id thì
        # nó khớp tài khoản của A và kéo đơn của B vào kết quả của A (hoặc ngược lại).
        st, tkb, _ = b.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "vtp", "ten": "VTP mock của B",
                            "credentials": {"api_key": "demo-key-B-chi-de-thu"}})
        self.assertEqual(st, 201, tkb)
        st, kqb, _ = b.goi("/api/v2/don", "POST",
                           dict(DON_MAU, cod=987654321, nguoi_nhan_ten="G22-M3-CUA-B",
                                hang_hoa="Kiện G22-M3 của B"))
        self.assertEqual(st, 201, kqb)
        don_b = kqb["don"]
        self.assertEqual(b.goi("/api/v2/don/%d/duyet" % don_b["id"], "POST", {})[0], 200)
        st, kq, _ = b.goi("/api/v2/don/%d/gui" % don_b["id"], "POST",
                          {"carrier_account_id": tkb["id"]})
        self.assertEqual(st, 200, kq)

        # (a) ĐỐI CHỨNG ĐƯỜNG — trên tenant sở hữu, bộ lọc PHẢI ra đơn đó
        st, kq, _ = b.goi("/api/v2/don?gioi_han=500&q=G22-M3-CUA-B")
        self.assertEqual([d["id"] for d in kq["dong"]], [don_b["id"]],
                         "bộ lọc không chạy ngay trên tenant sở hữu ⇒ mọi phép đo dưới vô nghĩa")
        # (b) A: cùng bộ lọc ⇒ 0, và `tong` cũng 0 (đếm rò còn khó thấy hơn danh sách rò)
        for truy_van in ("q=G22-M3-CUA-B",
                         "q=G22-M3&cod_tu=987000000",
                         "carrier_account_id=%d" % tkb["id"],
                         "q=G22-M3-CUA-B&hang=vtp"):
            st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&" + truy_van)
            self.assertEqual(st, 200, kq)
            self.assertEqual(len(kq["dong"]), 0, "A thấy đơn của B qua bộ lọc %r" % truy_van)
            self.assertEqual(kq["tong"], 0, "`tong` của A đếm cả đơn của B (%r)" % truy_van)
        # (c) và đơn của B không lọt vào trang nào của A, kể cả khi A lọc theo hãng "vtp"
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500")
        self.assertNotIn(don_b["id"], [d["id"] for d in kq["dong"]],
                         "đơn của tenant khác nằm trong danh sách của A")
        st, kq, _ = self.a.goi("/api/v2/don?gioi_han=500&hang=vtp")
        self.assertEqual(st, 200, kq)
        self.assertNotIn(don_b["id"], [d["id"] for d in kq["dong"]],
                         "lọc `hang=vtp` của A kéo về đơn của B")
        print("\n      [MẶT 3 · tenant] 4 bộ lọc của A → 0 dòng · đối chứng trên B → đúng 1 đơn "
              "(id %d) · hang=vtp của A không chứa đơn của B" % don_b["id"])

    def test_40_hop_dong_giao_dien_va_may_chu_khop_va_khong_loc_hai_cho(self):
        """MẶT 4 — PHẠM VI GIAO DIỆN. Dòng "phạm vi lọc" chỉ nói thật được nếu HAI danh sách
        khớp nhau: danh sách giao diện khai (`admin/logic.js`) và danh sách máy chủ nhận
        (`GET /api/v2/don/loc-mo-ta`). Ca này đo cả hai chiều:

          * mọi tham số giao diện khai là gửi lên máy chủ ⇒ máy chủ PHẢI nhận (bắn thật từng
            tham số, không tin lời tự mô tả);
          * mọi khoá sắp xếp giao diện khai ⇒ phải nằm trong danh sách trắng của máy chủ;
          * mọi ô lọc trên màn (`docDieuKien()` trong admin.js) ⇒ phải được khai ở MỘT trong
            hai danh sách, nếu không `chiaDieuKien()` bỏ nó vào túi `la` và điều kiện người
            dùng chọn biến mất im lặng;
          * điều kiện "lọc tại trang" phải KHÔNG nằm trong danh sách máy chủ nhận — lọc hai
            chỗ là kết quả đúng một cách tình cờ.
        """
        # (a) máy chủ TỰ MÔ TẢ bộ lọc
        st, mt, _ = self.a.goi("/api/v2/don/loc-mo-ta")
        self.assertEqual(st, 200, "máy chủ phải tự mô tả được bộ lọc: %s" % (mt,))
        ten_loc = set(t["ten"] for t in mt["truong"])
        self.assertGreaterEqual(len(ten_loc), 8, "máy chủ mô tả quá ít trường — phép đo rỗng")
        DieuKhien = set(["sap_xep", "gioi_han", "trang"])

        # (b) giao diện khai gì ⇒ máy chủ phải nhận cái đó
        khai = ds_tham_so_may_chu()
        self.assertGreaterEqual(len(khai), 8, "đọc được quá ít tham số từ admin/logic.js")
        thua = sorted(set(khai) - ten_loc - DieuKhien)
        self.assertEqual(thua, [], "giao diện khai %s là gửi lên máy chủ nhưng máy chủ KHÔNG "
                                   "nhận ⇒ người dùng bấm là 400" % thua)
        hom_nay = datetime.date.today().isoformat()
        gia_tri = {"q": "G22-M4", "trang_thai": "nhap", "trang_thai_giao": "cho_lay",
                   "hang": "vtp", "carrier_account_id": str(self.tk["id"]),
                   "cod_tu": "1", "cod_den": "999999999", "tu_ngay": hom_nay,
                   "den_ngay": hom_nay, "can_doi_soat": "1", "sap_xep": "cod_cao",
                   "gioi_han": "10", "trang": "1"}
        for ten in khai:
            self.assertIn(ten, gia_tri, "chưa có giá trị thử cho tham số %r" % ten)
            st, kq, _ = self.a.goi("/api/v2/don?" +
                                   urllib.parse.urlencode({ten: gia_tri[ten]}))
            self.assertEqual(st, 200, "giao diện gửi %r=%r nhưng máy chủ trả %s: %s"
                             % (ten, gia_tri[ten], st, kq))

        # (c) khoá sắp xếp của giao diện ⊆ danh sách trắng của máy chủ
        sx = ds_sap_xep_giao_dien()
        self.assertGreaterEqual(len(sx), 4, "đọc được quá ít khoá sắp xếp")
        self.assertEqual(sorted(set(sx) - set(mt["sap_xep_duoc"])), [],
                         "khoá sắp xếp giao diện khai mà máy chủ không nhận ⇒ chọn là 400")

        # (d) KHÔNG LỌC HAI CHỖ
        tt = ds_loc_tai_trang()
        self.assertEqual(tt, ["co_van_don"],
                         "danh sách 'lọc tại trang' đổi ⇒ dòng phạm vi của màn phải đổi theo")
        self.assertEqual(sorted(set(tt) & (ten_loc | DieuKhien)), [],
                         "một điều kiện vừa gửi lên máy chủ vừa lọc tại trang = LỌC HAI CHỖ")

        # (e) mọi ô lọc trên màn phải được khai ở một trong hai danh sách
        khoa = ds_dieu_kien_man_don()
        self.assertGreaterEqual(len(khoa), 10, "đọc được quá ít khoá từ admin.js")
        self.assertEqual(sorted(set(khoa) - set(khai) - set(tt)), [],
                         "ô lọc trên màn không được khai ở admin/logic.js ⇒ chiaDieuKien bỏ nó "
                         "vào túi `la` và điều kiện người dùng chọn biến mất")

        # (f) dòng "phạm vi" của màn phải nói bất biến MỚI, không còn câu của bản cũ
        with open(os.path.join(GOC_DU_AN, "admin", "admin.js"), encoding="utf-8") as f:
            ma_admin = f.read()
        self.assertNotIn("Giao diện lọc thêm", ma_admin,
                         "màn Đơn hàng còn câu 'Giao diện lọc thêm' của bản cũ")
        self.assertIn("không lọc gì thêm tại trang", ma_admin)
        self.assertIn("Máy chủ lọc trên", ma_admin)

        # (g) nhãn "một phần / CHỜ BACKEND" cho `/api/v2/don` phải đã được gỡ
        self.assertNotIn("/api/v2/don", bang_mot_phan(),
                         "giao diện vẫn dán nhãn 'một phần' cho route đã đủ")
        print("\n      [MẶT 4 · phạm vi giao diện] máy chủ tự mô tả %d trường · giao diện khai "
              "%d tham số + %d khoá sắp xếp, bắn thật từng cái: 200 · lọc tại trang = %s"
              % (len(ten_loc), len(khai), len(sx), tt))


# ============================================================================
# ĐỐI CHỨNG ÂM — chứng minh phép đo BẮT ĐƯỢC, không chỉ khẳng định
# ============================================================================

def doi_chung_am(duong_server_cu):
    """Dựng CÂY SAO CHÉP mang `app/server.py` ĐÚNG BẢN TRƯỚC AG-02 rồi chạy lại CHÍNH bộ thử này.

    Vì sao phải có: một ca khẳng định "máy chủ lọc nâng cao" mà chỉ được chạy trên cây ĐÃ có
    bản vá thì nó không phân biệt được "phép đo bắt được lỗi" với "phép đo luôn đạt". Vế đối
    chứng âm là thứ phân biệt hai khả năng ấy: đặt lại máy chủ cũ ⇒ ca PHẢI ĐỎ, và phải đỏ
    ĐÚNG câu "máy chủ BỎ QUA điều kiện" — chứ không phải đỏ vì lỗi nạp mô-đun (đỏ vì lý do
    khác là một phép đo khác, không phải phép đo này).

    Trả 0 khi đối chứng âm ĐẠT (ca đã bắt được), 1 khi nó KHÔNG bắt được.
    """
    if not os.path.isfile(duong_server_cu):
        print("KHÔNG ĐỐI CHỨNG ÂM ĐƯỢC: không có tệp %r" % duong_server_cu)
        return 1
    tam = tempfile.mkdtemp(prefix="thu-http-doi-chung-am-")
    dich = os.path.join(tam, "cay")
    shutil.copytree(GOC_DU_AN, dich,
                    ignore=shutil.ignore_patterns("node_modules", ".git", "__pycache__",
                                                  "*.pyc", "_bao-cao", "_ket-qua"))
    shutil.copyfile(duong_server_cu, os.path.join(dich, "app", "server.py"))
    print("ĐỐI CHỨNG ÂM — cây sao chép: %s" % dich)
    print("  app/server.py := %s   (bản TRƯỚC AG-02)" % duong_server_cu)
    r = subprocess.run([sys.executable, os.path.join(dich, "thu_frontend", "thu_http.py"), "-v"],
                       cwd=dich, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ra = r.stdout.decode("utf-8", "replace")
    hong = re.findall(r"^(?:FAIL|ERROR): (test_\w+)", ra, re.M)
    tom_tat = [d for d in ra.splitlines() if d.startswith("Ran ") or d.startswith("FAILED")
               or d.startswith("OK")]
    print("  mã thoát bộ thử trên cây cũ: %s" % r.returncode)
    for d in tom_tat:
        print("  %s" % d)
    print("  ca ĐỎ trên cây cũ: %s" % (", ".join(sorted(set(hong))) or "KHÔNG CÓ"))
    bat_duoc = "test_10" in " ".join(hong)
    dung_ly_do = "BỎ QUA điều kiện" in ra
    print("  test_10 có ĐỎ không: %s · đỏ ĐÚNG lý do ('máy chủ BỎ QUA điều kiện'): %s"
          % (bat_duoc, dung_ly_do))
    if bat_duoc and dung_ly_do:
        print("ĐỐI CHỨNG ÂM ĐẠT: đặt lại máy chủ không lọc nâng cao ⇒ test_10 ĐỎ LẠI, đúng "
              "câu khẳng định của nó.")
        return 0
    print("ĐỐI CHỨNG ÂM KHÔNG ĐẠT: ca này KHÔNG bắt được cái nó khẳng định — sửa ca thử, "
          "đừng sửa kết luận.")
    return 1


if __name__ == "__main__":
    if "--doi-chung-am" in sys.argv:
        i = sys.argv.index("--doi-chung-am")
        if i + 1 >= len(sys.argv):
            print("Dùng: python3 thu_frontend/thu_http.py --doi-chung-am <app/server.py BẢN CŨ>")
            sys.exit(2)
        sys.exit(doi_chung_am(sys.argv[i + 1]))
    unittest.main(verbosity=2)
