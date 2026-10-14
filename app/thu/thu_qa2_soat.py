# Bộ soát QA2 (AG-05 QA / SECURITY VERIFIER) — WAVE 1, lượt xác minh thứ hai.
#
# Vì sao có file này dù đã có `thu_qa_soat.py`: bộ thử của phiên trước vừa là người phát hiện
# vừa là người nghiệm thu bản vá của chính phát hiện đó. §12.1 luật 1 của CLAUDE.md: thứ dùng
# để kiểm chứng phải ĐỘC LẬP với thứ được kiểm chứng. File này viết lại ca thử từ đầu, không
# gọi và không nhập bất cứ thứ gì từ `thu_qa_soat.py`.
#
# Quy ước tên ca:
#   test_rNN_KIN_…      → chốt một bản vá CÒN KÍN. PASS là đúng.
#   test_rNN_LOHONG_…   → chứng minh một lỗ hổng CHƯA vá. FAIL là đúng (và là phát hiện mới).
#   test_rNN_ANTOAN_…   → mối lo đã kiểm, kết luận không phải lỗ hổng, kèm phạm vi đã kiểm.
#   test_rNN_PHAMVI_…   → ghi lại phạm vi/giới hạn đo được, không phán xét an toàn.
#
# KHÔNG sửa mã sản phẩm. QA phát hiện, không vá.
# Chạy: python3 app/thu/thu_qa2_soat.py
import base64
import hashlib
import hmac
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timedelta

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_REPO = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_TAM = tempfile.mkdtemp(prefix="vip-hub-qa2-")
os.environ["VIP_HUB_DATA"] = _TAM
os.environ["VIP_HUB_BACKOFF"] = "0.05"
# CỐ Ý xoá biến này: cả bộ đo hệ ở ĐÚNG cấu hình mặc định, không tự nới cho mình dễ đạt.
os.environ.pop("VIP_HUB_RESET_TOKEN", None)

import adapter      # noqa: E402
import bao_mat      # noqa: E402
import billing      # noqa: E402
import cau_hinh     # noqa: E402
import csdl         # noqa: E402
import don_hang     # noqa: E402
import khoi_tao     # noqa: E402
import nhap_file    # noqa: E402
import gioi_han
import quyen        # noqa: E402
import secret_provider  # noqa: E402
import server       # noqa: E402
import trang_thai_hang  # noqa: E402
import webhook      # noqa: E402

# Cổng 0 = để hệ tự cấp một cổng RỖI. Cổng cố định làm bộ thử báo HỎNG GIẢ khi hai
# worktree chạy cùng lúc (AG-04 đo được 15/10: `Address already in use` ở lượt đầu,
# chạy lại thì đạt). Cổng thật đọc lại từ `sv.server_address[1]` sau khi bind.
CONG = 0                      # cổng riêng của AG-05, tránh đụng agent khác
# Không dựng ở mức module: lúc nạp file vẫn chưa bind nên CONG còn là 0. Hàm thì đọc
# CONG lúc GỌI, nên luôn đúng cổng thật.
def GOC_URL_F():
    return "http://127.0.0.1:%d" % CONG
MK = "MatKhauQA2-456"
LOG = io.StringIO()

DON_MAU = {
    "nguoi_gui_ten": "Shop QA2", "nguoi_gui_sdt": "0901234567",
    "nguoi_gui_dia_chi": "1 Đường QA2, Hà Nội",
    "nguoi_nhan_ten": "Khách QA2", "nguoi_nhan_sdt": "0907654321",
    "nguoi_nhan_dia_chi": "2 Phố QA2, TP HCM",
    "hang_hoa": "Thùng QA2", "khoi_luong_gram": 800, "cod": 250000,
}


class Khach:
    """Client HTTP tối giản, tự giữ cookie phiên. Viết lại, không mượn harness của phiên trước."""

    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None, csrf=True):
        body = tho if tho is not None else (
            json.dumps(du_lieu, ensure_ascii=False).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        if csrf and method in ("POST", "PUT", "DELETE"):
            h.setdefault("X-Requested-With", "VIPHub")
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(GOC_URL_F() + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=30) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                raw = ph.read()
                ct = ph.headers.get("Content-Type", "")
                return ph.status, (json.loads(raw) if "json" in ct else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw

    def vao(self, ten, mk=MK):
        st, kq = self.goi("/api/v2/auth/dang-nhap", "POST",
                          {"ten_dang_nhap": ten, "mat_khau": mk})
        assert st == 200, f"đăng nhập {ten} hỏng: {st} {kq}"
        return self


def _tho_duong(duong):
    """Gửi GET với đường dẫn ĐÚNG NGUYÊN VĂN qua socket thô.

    urllib tự chuẩn hoá đường dẫn (gộp `//`, giải `..`), nên dùng nó để thử path traversal là
    đo công cụ của mình chứ không đo máy chủ — đúng dạng §12.1 luật 3. Ở đây viết thẳng dòng
    request để byte nào mình gửi thì byte đó tới máy chủ.
    """
    import socket
    s = socket.create_connection(("127.0.0.1", CONG), timeout=15)
    try:
        s.sendall(("GET %s HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n" % duong)
                  .encode("latin-1", "replace"))
        ra = b""
        while True:
            k = s.recv(65536)
            if not k:
                break
            ra += k
    finally:
        s.close()
    dong1 = ra.split(b"\r\n", 1)[0]
    m = re.search(rb" (\d{3}) ", dong1 + b" ")
    return (int(m.group(1)) if m else 0), ra


class Qa2(unittest.TestCase):

    # ---------------------------------------------------------------- dựng nền
    @classmethod
    def setUpClass(cls):
        global CONG      # gán lại sau khi bind cổng 0
        cls._err = sys.stderr
        sys.stderr = LOG
        csdl.mo()
        webhook.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", CONG), server.BoXuLy)
        # Cổng THẬT do hệ cấp — gán lại CONG để mọi chỗ dựng URL lúc chạy tự đúng.
        CONG = cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()
        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'qa2')",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))

        def nguoi(ten, pr=None):
            return csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten,"
                            " platform_role, tao_luc) VALUES (?,?,?,?,?)",
                            (ten, bao_mat.bam_mat_khau(MK), ten, pr, csdl.bay_gio())).lastrowid

        cls.u_po = nguoi("qa2-po", "PLATFORM_OWNER")
        cls.u_padmin = nguoi("qa2-padmin", "PLATFORM_ADMIN")
        cls.u_reset = nguoi("qa2-reset")        # dành riêng cho các ca reset mật khẩu
        cls.u_khoa = nguoi("qa2-biKhoa")        # bị quản trị khóa
        csdl.ghi("UPDATE users SET trang_thai='khoa' WHERE id=?", (cls.u_khoa,))

        po = Khach().vao("qa2-po")
        cls.tenant = {}
        for ten, code in (("DN A", "qa2a"), ("DN B", "qa2b")):
            st, kq = po.goi("/api/v2/platform/tenants", "POST", {
                "ten": ten, "code": code, "goi_id": "pro",
                "owner_ten_dang_nhap": f"{code}-owner", "owner_mat_khau": MK})
            assert st == 201, f"tạo tenant {ten} hỏng: {st} {kq}"
            cls.tenant[code] = kq["id"]

        # u_reset phải có membership, không thì đăng nhập bị chặn vì "chưa gán doanh nghiệp"
        for uid in (cls.u_reset, cls.u_khoa):
            csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                     " VALUES (?,?,'TENANT_VIEWER',?)", (uid, cls.tenant["qa2a"], csdl.bay_gio()))

        # vai trò phụ trong tenant A
        a_owner = Khach().vao("qa2a-owner")
        for ten, role in (("qa2a-admin", "TENANT_ADMIN"), ("qa2a-staff", "TENANT_STAFF"),
                          ("qa2a-viewer", "TENANT_VIEWER")):
            st, kq = a_owner.goi("/api/v2/memberships", "POST",
                                 {"ten_dang_nhap": ten, "mat_khau": MK, "role": role})
            assert st == 201, f"thêm {ten} hỏng: {st} {kq}"
        cls.a_owner, cls.po = a_owner, po
        cls.b_owner = Khach().vao("qa2b-owner")

        # một tài khoản hãng mock + một đơn cho mỗi tenant
        cls.tk = {}
        cls.don = {}
        for code, kh in (("qa2a", a_owner), ("qa2b", cls.b_owner)):
            st, kq = kh.goi("/api/v2/tai-khoan-hang", "POST",
                            {"hang": "jt", "ten": f"JT {code}", "moi_truong": "mock",
                             "credentials": {"customerCode": f"C-{code}", "privateKey": "pk"}})
            assert st == 201, f"tạo tài khoản hãng {code} hỏng: {st} {kq}"
            cls.tk[code] = kq
            st, kq2 = kh.goi("/api/v2/don", "POST", dict(DON_MAU))
            assert st == 201, f"tạo đơn {code} hỏng: {st} {kq2}"
            cls.don[code] = kq2["don"]["id"]

    def setUp(self):
        # Trần tần suất giữ trạng thái trong BỘ NHỚ TIẾN TRÌNH và dùng chung cho cả bộ thử, nên
        # ca trước làm cạn ngân sách của ca sau (đo được: r46 đạt khi chạy riêng, hỏng trong bộ).
        # Mỗi ca là một tình huống độc lập, trong thực tế cách nhau về thời gian — đặt lại ở đây
        # chính là mô phỏng thời gian đã trôi. KHÔNG làm yếu hai ca r27/r28: chúng bắn 40 lượt
        # TRONG MỘT ca, nên vẫn chạm trần.
        gioi_han.xoa_het()

    @classmethod
    def tearDownClass(cls):
        webhook.dung()
        cls.sv.shutdown()
        cls.sv.server_close()
        sys.stderr = cls._err

    # ====================================================================
    # Q02-A — token đặt lại mật khẩu
    # ====================================================================
    def test_r01_KIN_quen_mat_khau_khong_tra_token_cho_vo_danh(self):
        """Mặc định phải TẮT provider giả lập. Bật là chiếm mọi tài khoản trong 3 yêu cầu."""
        self.assertFalse(cau_hinh.HIEN_TOKEN_RESET,
                         "HIEN_TOKEN_RESET mặc định phải TẮT")
        st, kq = Khach().goi("/api/v2/auth/quen-mat-khau", "POST",
                             {"ten_dang_nhap": "qa2-po"})
        self.assertEqual(st, 200)
        self.assertNotIn("token_gia_lap", kq, f"token lộ cho người vô danh: {kq}")
        for v in json.dumps(kq, ensure_ascii=False):
            pass
        self.assertNotRegex(json.dumps(kq, ensure_ascii=False), r"[A-Za-z0-9_-]{32,}",
                            "phản hồi chứa chuỗi dài giống token")

    def test_r02_KIN_quen_mat_khau_khong_lo_tai_khoan_co_that(self):
        """Phản hồi cho tài khoản CÓ và KHÔNG CÓ phải giống nhau từng byte."""
        a = Khach().goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "qa2-po"})
        b = Khach().goi("/api/v2/auth/quen-mat-khau", "POST",
                        {"ten_dang_nhap": "khong-ton-tai-bao-gio-xxx"})
        self.assertEqual(a, b, f"phản hồi khác nhau → dò được tài khoản: {a} vs {b}")

    def test_r03_KIN_token_reset_dung_mot_lan_va_chong_replay(self):
        """Token dùng lần hai phải bị từ chối — kể cả gửi lại y nguyên (replay)."""
        tk = bao_mat.tao_token_reset("qa2-reset")
        self.assertTrue(tk)
        ok, _ = bao_mat.dat_lai_mat_khau(tk, "MatKhauMoi-111")
        self.assertTrue(ok)
        for lan in range(3):                       # replay nhiều lượt, không lần nào được qua
            ok2, ly_do = bao_mat.dat_lai_mat_khau(tk, "MatKhauKhac-222")
            self.assertFalse(ok2, f"replay lần {lan + 1} lại được chấp nhận")
            self.assertIn("đã dùng", ly_do)
        # và mật khẩu vẫn là bản của lượt ĐẦU, không phải của lượt replay
        u = csdl.mot("SELECT mat_khau_hash FROM users WHERE id=?", (self.u_reset,))
        self.assertTrue(bao_mat.kiem_mat_khau("MatKhauMoi-111", u["mat_khau_hash"]))
        self.assertFalse(bao_mat.kiem_mat_khau("MatKhauKhac-222", u["mat_khau_hash"]))
        csdl.ghi("UPDATE users SET mat_khau_hash=? WHERE id=?",
                 (bao_mat.bam_mat_khau(MK), self.u_reset))

    def test_r04_KIN_token_reset_het_han_bi_tu_choi(self):
        """Hết hạn đo bằng cách ĐẨY LÙI mốc trong CSDL, không chờ 30 phút thật."""
        tk = bao_mat.tao_token_reset("qa2-reset")
        qua = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        csdl.ghi("UPDATE reset_tokens SET het_han=? WHERE token_hash=?",
                 (qua, hashlib.sha256(tk.encode()).hexdigest()))
        ok, ly_do = bao_mat.dat_lai_mat_khau(tk, "MatKhauHetHan-333")
        self.assertFalse(ok)
        self.assertIn("hết hạn", ly_do)

    def test_r05_KIN_dat_lai_mat_khau_thu_hoi_moi_phien_cu(self):
        """Đổi mật khẩu qua token → mọi phiên đang mở của người đó phải chết ngay."""
        kh = Khach().vao("qa2-reset")
        st, _ = kh.goi("/api/v2/auth/toi")
        self.assertEqual(st, 200, "phiên phải sống trước khi đặt lại")
        tk = bao_mat.tao_token_reset("qa2-reset")
        ok, _ = bao_mat.dat_lai_mat_khau(tk, "MatKhauThuHoi-444")
        self.assertTrue(ok)
        st2, _ = kh.goi("/api/v2/auth/toi")
        self.assertEqual(st2, 401, "phiên cũ còn sống sau khi đặt lại mật khẩu")
        csdl.ghi("UPDATE users SET mat_khau_hash=? WHERE id=?",
                 (bao_mat.bam_mat_khau(MK), self.u_reset))

    def test_r06_KIN_khoa_sai_mat_khau_chi_la_khoa_TAM(self):
        """5 lần sai không được khóa chết tài khoản người khác: phải là khóa TẠM, tự mở."""
        uid = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role,"
                       " tao_luc) VALUES ('qa2-brute', ?, 'Brute', 'PLATFORM_OWNER', ?)",
                       (bao_mat.bam_mat_khau(MK), csdl.bay_gio())).lastrowid
        for _ in range(cau_hinh.KHOA_SAU_SO_LAN_SAI + 2):
            Khach().goi("/api/v2/auth/dang-nhap", "POST",
                        {"ten_dang_nhap": "qa2-brute", "mat_khau": "sai-be-bet"})
        u = csdl.mot("SELECT trang_thai, khoa_den FROM users WHERE id=?", (uid,))
        self.assertEqual(u["trang_thai"], "hoat_dong",
                         "mật khẩu sai đã khóa VĨNH VIỄN tài khoản — người lạ vô hiệu hóa được ai cũng được")
        self.assertIsNotNone(u["khoa_den"], "không thấy mốc khóa tạm nào")
        # và khi hết khóa tạm thì đăng nhập lại được, không cần ai mở tay
        csdl.ghi("UPDATE users SET khoa_den=? WHERE id=?",
                 ((datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"), uid))
        st, _ = Khach().goi("/api/v2/auth/dang-nhap", "POST",
                            {"ten_dang_nhap": "qa2-brute", "mat_khau": MK})
        self.assertEqual(st, 200, "hết khóa tạm mà vẫn không vào được")

    def test_r07_LOHONG_thong_bao_dang_nhap_lo_tai_khoan_bi_khoa_co_that(self):
        """Thông báo của tài khoản BỊ QUẢN TRỊ KHÓA khác thông báo chung → dò được tài khoản.

        `dang_nhap` trả "tài khoản đã bị khóa — liên hệ quản trị" cho user có thật đang bị khóa,
        nhưng trả "sai tên đăng nhập hoặc mật khẩu" cho tên không tồn tại. Người vô danh gõ mật
        khẩu rác vẫn phân biệt được hai ca. Mức LOW: chỉ lộ sự tồn tại, không lộ mật khẩu.
        """
        _, a = Khach().goi("/api/v2/auth/dang-nhap", "POST",
                           {"ten_dang_nhap": "qa2-biKhoa", "mat_khau": "mat-khau-rac"})
        _, b = Khach().goi("/api/v2/auth/dang-nhap", "POST",
                           {"ten_dang_nhap": "khong-he-ton-tai-yyy", "mat_khau": "mat-khau-rac"})
        self.assertEqual(a, b, f"phân biệt được tài khoản bị khóa có thật: {a} vs {b}")

    # ====================================================================
    # Q02-B — static: danh sách trắng và path traversal
    # ====================================================================
    def test_r08_PHAMVI_static_con_phuc_vu_dung_thu_muc_duoc_phep(self):
        """Đối chứng DƯƠNG. Thiếu nó thì mọi ca 404 bên dưới có thể đạt chỉ vì static đã chết."""
        st, _ = Khach().goi("/admin/index.html")
        self.assertEqual(st, 200, "static chết hẳn — các ca 404 bên dưới mất ý nghĩa")
        st2, _ = Khach().goi("/")
        self.assertEqual(st2, 200)

    def test_r09_KIN_static_khong_phuc_vu_ma_nguon_csdl_khoa_git(self):
        duong = [
            "/app/server.py", "/app/bao_mat.py", "/app/cau_hinh.py", "/app/thu/thu_qa2_soat.py",
            "/gateway/cau_hinh.py", "/gateway/server.py", "/gateway/xac_thuc.py",
            "/app/du-lieu/hub.db", "/app/du-lieu/khoa-noi-bo.key",
            "/app/du-lieu/khoa/hien-hanh.txt", "/gateway/du-lieu/gateway.db",
            "/.git/config", "/.git/HEAD", "/.gitignore", "/README.md",
            "/docs/QA_FINDINGS.md", "/.env", "/app/.env", "/migrate.py",
        ]
        lo = []
        for d in duong:
            st, _ = Khach().goi(d)
            if st == 200:
                lo.append((d, st))
        self.assertEqual(lo, [], f"static trả 200 cho đường không được phép: {lo}")

    def test_r10_KIN_static_chan_path_traversal_nhieu_bien_the(self):
        """Gửi bằng socket thô để đường dẫn tới máy chủ ĐÚNG NGUYÊN VĂN."""
        bien_the = [
            "/assets/../app/server.py",
            "/assets/../../etc/passwd",
            "/admin/../../../../../../etc/passwd",
            "/%2e%2e/app/server.py",
            "/assets/%2e%2e/%2e%2e/app/bao_mat.py",
            "/..%2fapp%2fserver.py",
            "//app/server.py",
            "///app/server.py",
            "/assets//../app/server.py",
            "/app/server.py%00.css",
            "/app/server.py\x00.html",
            "/./app/server.py",
            "/admin/./../app/server.py",
            "/" + GOC_REPO.lstrip("/") + "/app/server.py",
            "/etc/passwd",
            "/assets/..;/app/server.py",
            "/assets/%252e%252e/app/server.py",
            "/assets/....//app/server.py",
        ]
        lo = []
        for d in bien_the:
            try:
                st, ra = _tho_duong(d)
            except OSError as e:
                lo.append((d, f"lỗi socket: {e}"))
                continue
            if st == 200:
                lo.append((d, st))
            # kể cả không 200, nội dung tuyệt đối không được chứa mã nguồn
            if b"import cau_hinh" in ra or b"root:x:0:0" in ra or b"PBKDF2_VONG" in ra:
                lo.append((d, "nội dung file kín lọt vào phản hồi"))
        self.assertEqual(lo, [], f"path traversal lọt: {lo}")

    def test_r11_ANTOAN_khoa_ma_hoa_khong_nam_trong_thu_muc_duoc_phuc_vu(self):
        """Đã kiểm, không phải lỗ hổng. Phạm vi: 4 thư mục trắng + index.html ở gốc repo.

        Chốt bằng CẤU TRÚC chứ không bằng tên: khóa và CSDL nằm ngoài mọi thư mục được phục vụ,
        nên kể cả danh sách trắng có nới thêm đuôi file thì chúng vẫn ngoài tầm.
        """
        for duong in (cau_hinh.DUONG_DAN_KHOA, cau_hinh.DUONG_DAN_CSDL):
            tuong_doi = os.path.relpath(os.path.abspath(duong), GOC_REPO)
            self.assertFalse(
                tuong_doi.startswith(("admin/", "pages/", "assets/", "mock/")),
                f"{duong} nằm trong thư mục được phục vụ static")

    def test_r12_PHAMVI_thu_muc_trang_khong_chua_file_bi_mat(self):
        """mock/ được phục vụ công khai và cho cả .json/.csv — soát xem có gì không nên lộ."""
        nghi = []
        for goc in ("admin", "pages", "assets", "mock"):
            for thu_muc, _, ten_ds in os.walk(os.path.join(GOC_REPO, goc)):
                for ten in ten_ds:
                    p = os.path.join(thu_muc, ten)
                    try:
                        with open(p, "rb") as f:
                            noi = f.read(400_000)
                    except OSError:
                        continue
                    for mau in (rb"privateKey", rb"BEGIN [A-Z ]*PRIVATE KEY", rb"secret\s*[:=]\s*['\"][^'\"]{12,}"):
                        if re.search(mau, noi):
                            nghi.append((os.path.relpath(p, GOC_REPO), mau.decode("latin-1")))
        self.assertEqual(nghi, [], f"file phục vụ công khai có vẻ chứa bí mật: {nghi}")

    # ====================================================================
    # Q02-C — vượt quyền ngang / dọc
    # ====================================================================
    def test_r13_KIN_cheo_tenant_doc_ghi_xoa_deu_bi_chan(self):
        """Tenant B lấy ĐÚNG id tài nguyên của tenant A rồi thử mọi cửa."""
        a_don, a_tk = self.don["qa2a"], self.tk["qa2a"]["id"]
        thu = [
            (f"/api/v2/don/{a_don}", "GET", None),
            (f"/api/v2/don/{a_don}", "PUT", {"hang_hoa": "bị B sửa"}),
            (f"/api/v2/don/{a_don}", "DELETE", None),
            (f"/api/v2/don/{a_don}/duyet", "POST", {}),
            (f"/api/v2/don/{a_don}/huy", "POST", {}),
            (f"/api/v2/tai-khoan-hang/{a_tk}/khoa", "POST", {}),
            (f"/api/v2/tai-khoan-hang/{a_tk}/rotate", "POST", {"credentials": {"x": "1"}}),
            (f"/api/v2/tai-khoan-hang/{a_tk}/revoke", "POST", {}),
        ]
        lo = []
        for duong, pt, body in thu:
            st, kq = self.b_owner.goi(duong, pt, body)
            if st not in (403, 404):
                lo.append((duong, pt, st, kq))
        self.assertEqual(lo, [], f"tenant B chạm được tài nguyên của tenant A: {lo}")
        # và dữ liệu của A không đổi một chữ
        don = csdl.mot("SELECT hang_hoa, trang_thai FROM don_hang WHERE id=?", (a_don,))
        self.assertEqual(don["hang_hoa"], DON_MAU["hang_hoa"])
        self.assertEqual(don["trang_thai"], "nhap")
        tk = csdl.mot("SELECT kich_hoat FROM carrier_accounts WHERE id=?", (a_tk,))
        self.assertEqual(tk["kich_hoat"], 1, "B khóa được tài khoản hãng của A")

    def test_r14_KIN_khong_gui_don_bang_tai_khoan_hang_cua_tenant_khac(self):
        """Dùng credentials hãng của tenant khác — cửa dễ quên nhất vì id là số trần."""
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        self.assertEqual(st, 201)
        don_id = kq["don"]["id"]
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st2, kq2 = self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST",
                                    {"carrier_account_id": self.tk["qa2b"]["id"]})
        self.assertIn(st2, (403, 404), f"A gửi được đơn bằng tài khoản hãng của B: {st2} {kq2}")
        d = csdl.mot("SELECT trang_thai, carrier_account_id FROM don_hang WHERE id=?", (don_id,))
        self.assertEqual(d["trang_thai"], "da_duyet")
        self.assertIsNone(d["carrier_account_id"])

    def test_r15_KIN_viewer_khong_ghi_duoc_gi(self):
        v = Khach().vao("qa2a-viewer")
        thu = [("/api/v2/don", "POST", dict(DON_MAU)),
               ("/api/v2/khach-hang", "POST", {"ten": "Khách lậu"}),
               ("/api/v2/tai-khoan-hang", "POST", {"hang": "jt", "moi_truong": "mock"}),
               ("/api/v2/tenant", "PUT", {"ten": "Đổi tên lậu"}),
               ("/api/v2/memberships", "POST", {"ten_dang_nhap": "lau", "mat_khau": MK,
                                                "role": "TENANT_ADMIN"}),
               ("/api/v2/import", "POST", {"ten_file": "a.csv", "noi_dung_base64": "YQ=="}),
               ("/api/v2/polling/chay", "POST", {})]
        lo = [(d, p, s) for d, p, b in thu for s, _ in [v.goi(d, p, b)] if s != 403]
        self.assertEqual(lo, [], f"TENANT_VIEWER ghi được: {lo}")

    def test_r16_KIN_tenant_admin_khong_leo_thang_vai_tro(self):
        """TENANT_ADMIN chỉ được cấp STAFF/VIEWER. Tự nâng mình hay nâng người khác đều phải chặn."""
        ad = Khach().vao("qa2a-admin")
        lo = []
        for role in ("TENANT_OWNER", "TENANT_ADMIN", "PLATFORM_OWNER", "PLATFORM_ADMIN"):
            st, _ = ad.goi("/api/v2/memberships", "POST",
                           {"ten_dang_nhap": f"qa2-leo-{role}", "mat_khau": MK, "role": role})
            if st != 403:
                lo.append(("tao", role, st))
        ds = csdl.nhieu("SELECT m.id, u.ten_dang_nhap FROM tenant_memberships m"
                        " JOIN users u ON u.id=m.user_id WHERE m.tenant_id=?",
                        (self.tenant["qa2a"],))
        mid_staff = next(x["id"] for x in ds if x["ten_dang_nhap"] == "qa2a-staff")
        for role in ("TENANT_OWNER", "TENANT_ADMIN"):
            st, _ = ad.goi(f"/api/v2/memberships/{mid_staff}", "PUT", {"role": role})
            if st != 403:
                lo.append(("sua", role, st))
        # và không tự đổi vai trò chính mình
        mid_self = next(x["id"] for x in ds if x["ten_dang_nhap"] == "qa2a-admin")
        st, _ = ad.goi(f"/api/v2/memberships/{mid_self}", "PUT", {"role": "TENANT_OWNER"})
        if st != 403:
            lo.append(("tu_nang", "TENANT_OWNER", st))
        self.assertEqual(lo, [], f"leo thang vai trò lọt: {lo}")
        self.assertEqual(
            csdl.mot("SELECT role FROM tenant_memberships WHERE id=?", (mid_staff,))["role"],
            "TENANT_STAFF")

    def test_r17_KIN_nguoi_trong_tenant_khong_vao_duoc_cua_platform(self):
        """Một cổng chung cho /platform/* — soát MỌI đường, không chỉ đường đã biết."""
        duong = ["/api/v2/platform/tenants", "/api/v2/platform/goi",
                 "/api/v2/platform/vai-tro", "/api/v2/platform/audit",
                 f"/api/v2/platform/tenants/{self.tenant['qa2b']}",
                 "/api/v2/platform/tenants/999999", "/api/v2/platform/khong-co-duong-nay"]
        lo = []
        for kh, nhan in ((Khach().vao("qa2a-owner"), "OWNER"),
                         (Khach().vao("qa2a-viewer"), "VIEWER")):
            for d in duong:
                st, kq = kh.goi(d)
                if st != 403:
                    lo.append((nhan, d, st, kq))
        self.assertEqual(lo, [], f"người trong tenant vào được cửa nền tảng: {lo}")

    def test_r18_KIN_404_vs_403_khong_dem_duoc_so_doanh_nghiep(self):
        """Người không quyền phải nhận CÙNG mã cho id có thật và id không có."""
        kh = Khach().vao("qa2a-owner")
        a, _ = kh.goi(f"/api/v2/platform/tenants/{self.tenant['qa2a']}")
        b, _ = kh.goi("/api/v2/platform/tenants/987654")
        self.assertEqual(a, b, f"mã trả lời khác nhau → đếm được tenant: {a} vs {b}")

    def test_r19_LOHONG_hai_cua_platform_khong_tra_ma_tran_quyen(self):
        """`/platform/goi` và `/platform/vai-tro` không gọi `_can()` — chỉ chặn ở cổng platform.

        Hệ quả: một PLATFORM_ADMIN bị gỡ sạch quyền trong `role_permissions` vẫn đọc trọn
        ma trận RBAC và bảng giá. Mức LOW (chỉ người có platform_role mới tới được), nhưng
        là ngoại lệ còn lại của luật "mọi endpoint đều tra quyền".
        """
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma='PLATFORM_ADMIN'")
        try:
            kh = Khach().vao("qa2-padmin")
            st_audit, _ = kh.goi("/api/v2/platform/audit")
            self.assertEqual(st_audit, 403, "đối chứng: đường CÓ _can phải chặn")
            lo = []
            for d in ("/api/v2/platform/goi", "/api/v2/platform/vai-tro"):
                st, kq = kh.goi(d)
                if st == 200:
                    lo.append((d, len(json.dumps(kq))))
            self.assertEqual(lo, [], f"đọc được dù không còn quyền nào: {lo}")
        finally:
            quyen.seed()

    # ====================================================================
    # Q02-D — thu hồi phiên, vô hiệu tài khoản / membership
    # ====================================================================
    def test_r20_KIN_thu_hoi_phien_co_hieu_luc_ngay(self):
        kh = Khach().vao("qa2a-staff")
        self.assertEqual(kh.goi("/api/v2/auth/toi")[0], 200)
        bao_mat.thu_hoi_moi_phien(
            csdl.mot("SELECT id FROM users WHERE ten_dang_nhap='qa2a-staff'")["id"])
        self.assertEqual(kh.goi("/api/v2/auth/toi")[0], 401, "phiên đã thu hồi vẫn dùng được")

    def test_r21_KIN_vo_hieu_tai_khoan_va_membership_cat_quyen_ngay(self):
        for ten, cach in (("qa2a-staff", "user"), ("qa2a-viewer", "membership")):
            uid = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (ten,))["id"]
            csdl.ghi("UPDATE users SET trang_thai='hoat_dong' WHERE id=?", (uid,))
            csdl.ghi("UPDATE tenant_memberships SET trang_thai='hoat_dong'"
                     " WHERE user_id=? AND tenant_id=?", (uid, self.tenant["qa2a"]))
            kh = Khach().vao(ten)
            self.assertEqual(kh.goi("/api/v2/auth/toi")[0], 200, f"{ten} phải vào được trước")
            if cach == "user":
                csdl.ghi("UPDATE users SET trang_thai='khoa' WHERE id=?", (uid,))
            else:
                csdl.ghi("UPDATE tenant_memberships SET trang_thai='vo_hieu'"
                         " WHERE user_id=? AND tenant_id=?", (uid, self.tenant["qa2a"]))
            st, _ = kh.goi("/api/v2/auth/toi")
            self.assertEqual(st, 401, f"vô hiệu bằng {cach} mà phiên {ten} còn dùng được")
            # dọn lại cho các ca sau
            csdl.ghi("UPDATE users SET trang_thai='hoat_dong' WHERE id=?", (uid,))
            csdl.ghi("UPDATE tenant_memberships SET trang_thai='hoat_dong'"
                     " WHERE user_id=? AND tenant_id=?", (uid, self.tenant["qa2a"]))

    def test_r22_KIN_tenant_bi_khoa_thi_thanh_vien_mat_quyen_ngay(self):
        kh = Khach().vao("qa2b-owner")
        self.assertEqual(kh.goi("/api/v2/don")[0], 200)
        self.po.goi(f"/api/v2/platform/tenants/{self.tenant['qa2b']}/khoa", "POST", {})
        try:
            st, _ = kh.goi("/api/v2/don")
            self.assertEqual(st, 401, "tenant bị khóa mà thành viên còn truy cập dữ liệu")
        finally:
            self.po.goi(f"/api/v2/platform/tenants/{self.tenant['qa2b']}/mo", "POST", {})
            self.__class__.b_owner = Khach().vao("qa2b-owner")

    # ====================================================================
    # Q02-E — AES-GCM
    # ====================================================================
    def test_r23_KIN_aes_gcm_phat_hien_sua_ban_ma(self):
        bm = bao_mat.ma_hoa_v3("bi-mat-that", bao_mat.aad_credentials(1, "jt"))
        v, kid, nonce, ct = bm.split("$")
        for ten, hong in (
            ("đổi 1 byte bản mã", f"{v}${kid}${nonce}${('0' if ct[0] != '0' else '1') + ct[1:]}"),
            ("đổi nonce", f"{v}${kid}${('0' if nonce[0] != '0' else '1') + nonce[1:]}${ct}"),
            ("cắt bớt bản mã", f"{v}${kid}${nonce}${ct[:-4]}"),
            ("nối thêm", f"{v}${kid}${nonce}${ct}aabb"),
        ):
            with self.assertRaises(Exception, msg=f"không phát hiện: {ten}"):
                bao_mat.giai_ma(hong, bao_mat.aad_credentials(1, "jt"))

    def test_r24_KIN_aes_gcm_sai_khoa_va_sai_aad_deu_hong(self):
        bm = bao_mat.ma_hoa_v3("bi-mat-that", bao_mat.aad_credentials(1, "jt"))
        with self.assertRaises(Exception):
            bao_mat.giai_ma(bm, bao_mat.aad_credentials(1, "vtp"))     # sai hãng
        with self.assertRaises(Exception):
            bao_mat.giai_ma(bm, "")                                     # thiếu AAD
        p = secret_provider.nha_cung_cap()
        kid_khac = p.tao_khoa_moi()
        bm_khac = bao_mat.ma_hoa_v3("x", bao_mat.aad_credentials(1, "jt"), key_id=kid_khac)
        _, kid_cu, nonce, ct = bm.split("$")
        with self.assertRaises(Exception):      # dán key_id khác lên bản mã cũ = sai khóa
            bao_mat.giai_ma(f"v3${kid_khac}${nonce}${ct}", bao_mat.aad_credentials(1, "jt"))
        self.assertTrue(bm_khac.startswith(f"v3${kid_khac}$"))

    def test_r25_KIN_doi_cho_ban_ma_giua_hai_tenant_thi_giai_ma_hong(self):
        """Ca thật: chép thẳng cột credentials của tenant A sang hàng của tenant B trong CSDL."""
        a, b = self.tk["qa2a"]["id"], self.tk["qa2b"]["id"]
        ra = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (a,))
        rb = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (b,))
        goc_b = rb["credentials_ma_hoa"]
        csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                 (ra["credentials_ma_hoa"], b))
        try:
            with self.assertRaises(Exception,
                                   msg="bản mã của tenant A giải được ở hàng của tenant B"):
                bao_mat.giai_ma_cred(ra["credentials_ma_hoa"], rb["tenant_id"], rb["hang"])
            st, kq = self.b_owner.goi(f"/api/v2/don/{self.don['qa2b']}/gui", "POST",
                                      {"carrier_account_id": b})
            self.assertNotEqual(st, 200, f"gửi đơn thành công bằng credentials chéo tenant: {kq}")
        finally:
            csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?", (goc_b, b))

    def test_r26_KIN_xoay_khoa_khong_lam_mat_secret_cu(self):
        truoc = {r["id"]: bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
                 for r in csdl.nhieu("SELECT * FROM carrier_accounts")}
        self.assertTrue(truoc, "không có tài khoản hãng nào để đo — ca này vô nghĩa")
        kq = bao_mat.xoay_khoa()
        self.assertEqual(kq["hong"], [], f"xoay khóa có hàng hỏng: {kq['hong']}")
        for r in csdl.nhieu("SELECT * FROM carrier_accounts"):
            self.assertEqual(
                bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"]),
                truoc[r["id"]], f"mất secret của tài khoản {r['id']} sau khi xoay khóa")
            self.assertEqual(bao_mat.key_id_cua(r["credentials_ma_hoa"]), kq["key_id"])
            self.assertEqual(bao_mat.key_id_cua(r["webhook_secret_ma_hoa"]), kq["key_id"])
        # webhook vẫn ký/xác thực được sau khi xoay khóa
        tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (self.tk["qa2a"]["id"],))
        secret = bao_mat.giai_ma_wh(tk["webhook_secret_ma_hoa"], tk["webhook_ma"])
        body = b'{"event":"lay_hang","tracking_number":"x"}'
        self.assertTrue(webhook.kiem_chu_ky(
            tk, {"x-webhook-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()},
            body))

    # ====================================================================
    # Q02-F — rate limiting và hạn mức import
    # ====================================================================
    def test_r27_LOHONG_khong_co_rate_limit_tren_dang_nhap(self):
        """Khóa tạm tính THEO TÀI KHOẢN, không theo IP → dò mật khẩu cả danh sách user tự do.

        Đo: 60 lượt đăng nhập sai từ cùng một địa chỉ, rải trên nhiều tên đăng nhập. Không lượt
        nào bị 429, không lượt nào bị chặn vì nguồn gọi. Khóa tạm 15 phút chỉ cứu MỘT tài khoản
        bị dồn, không cứu được kiểu rải mỏng (password spraying).
        """
        ma = []
        for i in range(60):
            st, _ = Khach().goi("/api/v2/auth/dang-nhap", "POST",
                                {"ten_dang_nhap": f"qa2-khong-co-{i}", "mat_khau": "x"})
            ma.append(st)
        self.assertIn(429, ma,
                      f"60 lượt sai liên tiếp từ một IP không có lượt nào bị chặn theo tốc độ "
                      f"(mã nhận được: {sorted(set(ma))})")

    def test_r28_LOHONG_khong_co_rate_limit_tren_quen_mat_khau(self):
        """Mỗi lượt vô danh sinh một hàng `reset_tokens` + một hàng audit, không mức chặn nào."""
        truoc = csdl.mot("SELECT COUNT(*) c FROM reset_tokens")["c"]
        ma = [Khach().goi("/api/v2/auth/quen-mat-khau", "POST",
                          {"ten_dang_nhap": "qa2-po"})[0] for _ in range(40)]
        sau = csdl.mot("SELECT COUNT(*) c FROM reset_tokens")["c"]
        self.assertIn(
            429, ma,
            f"40 yêu cầu quên-mật-khẩu vô danh đều được nhận (mã: {sorted(set(ma))}); "
            f"reset_tokens tăng {sau - truoc} hàng — không có mức chặn tốc độ nào")

    def test_r29_LOHONG_token_reset_cu_khong_bi_vo_hieu_khi_cap_token_moi(self):
        """Xin 5 token rồi dùng token ĐẦU TIÊN — vẫn được. Cửa sổ tấn công rộng ra vô hạn.

        Gộp với r28 (không có rate limit): kẻ xấu bơm hàng nghìn token sống đồng thời cho một
        tài khoản, token nào rò ra cũng dùng được trong 30 phút.
        """
        ds = [bao_mat.tao_token_reset("qa2-reset") for _ in range(5)]
        try:
            ok, ly_do = bao_mat.dat_lai_mat_khau(ds[0], "MatKhauTokenCu-555")
            self.assertFalse(
                ok, "token cấp đầu tiên vẫn dùng được sau khi đã cấp 4 token mới "
                    f"({len(ds)} token sống đồng thời cho một tài khoản)")
        finally:
            csdl.ghi("UPDATE users SET mat_khau_hash=? WHERE id=?",
                     (bao_mat.bam_mat_khau(MK), self.u_reset))
            csdl.ghi("UPDATE reset_tokens SET da_dung=1 WHERE user_id=?", (self.u_reset,))

    def test_r30_KIN_han_muc_import_chan_dong_o_va_dung_luong(self):
        """Hạn mức import CÓ. Đo ở tầng API thật, không chỉ ở hàm."""
        kh = self.a_owner
        qua_dong = "nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram\n" + \
                   "".join(f"A{i},0901234567,Đâu đó,Hàng,500\n"
                           for i in range(nhap_file.GIOI_HAN_SO_DONG + 10))
        st, kq = kh.goi("/api/v2/import", "POST", {
            "ten_file": "qua-dong.csv",
            "noi_dung_base64": base64.b64encode(qua_dong.encode()).decode()})
        self.assertEqual(st, 413, f"nhận file {nhap_file.GIOI_HAN_SO_DONG + 10} dòng: {kq}")
        st2, _ = kh.goi("/api/v2/import", "POST", {
            "ten_file": "qua-nang.csv",
            "noi_dung_base64": base64.b64encode(b"a," * (6 * 1024 * 1024)).decode()})
        self.assertEqual(st2, 413)

    def test_r31_KIN_duyet_batch_chan_do_dai_danh_sach_dong(self):
        st, kq = self.a_owner.goi("/api/v2/import/1/duyet", "POST", {
            "nguoi_gui": {"ten": "A", "sdt": "0901234567", "dia_chi": "Đâu đó"},
            "dong_ids": list(range(50_000))})
        self.assertEqual(st, 400, f"nhận 50.000 id trong một lượt duyệt: {kq}")
        self.assertIn("quá nhiều", json.dumps(kq, ensure_ascii=False))

    def test_r32_KIN_body_lon_bi_chan_va_van_doc_duoc_ma_loi(self):
        """413 phải ĐỌC được: đóng kết nối ngay thì bên gửi chỉ thấy broken pipe."""
        st, kq = Khach().goi("/api/v2/auth/dang-nhap", "POST", tho=b"x" * (200 * 1024))
        self.assertEqual(st, 413, f"body 200KB vào cửa vô danh: {st} {kq}")
        self.assertIn("quá lớn", json.dumps(kq, ensure_ascii=False))

    def test_r33_LOHONG_webhook_giai_ma_secret_truoc_moi_muc_chan_toc_do(self):
        """Cửa webhook vô danh: mỗi yêu cầu rác buộc hệ giải mã AES-GCM + băm HMAC.

        `_api` → `tim_account_theo_webhook_ma` → `kiem_chu_ky` (giải mã secret) chạy TRƯỚC khi
        có bất kỳ mức chặn tốc độ nào — vì không có mức nào. Người biết `webhook_ma` (nó nằm
        trong URL, không phải bí mật) bơm yêu cầu sai chữ ký là bơm việc giải mã cho máy chủ.
        """
        wh = self.tk["qa2a"]["webhook_ma"]
        body = b'{"event":"lay_hang","tracking_number":"khong-co"}'
        ma = []
        for _ in range(40):
            st, _ = Khach().goi(f"/api/v2/webhook/nhan/{wh}", "POST", tho=body,
                                headers={"X-Webhook-Signature": "sai"})
            ma.append(st)
        self.assertIn(429, ma,
                      f"40 yêu cầu webhook sai chữ ký đều được xử lý tới tầng giải mã "
                      f"(mã: {sorted(set(ma))})")

    # ====================================================================
    # Q03/Q04 — phát hiện mới
    # ====================================================================
    def test_r34_LOHONG_gui_don_dong_thoi_goi_hang_HAI_LAN(self):
        """Hai yêu cầu `POST /don/{id}/gui` song song đều qua được chốt trạng thái.

        `don_hang.gui_don` đọc trạng thái, kiểm điều kiện, rồi mới ghi `dang_gui` — ba việc
        KHÔNG nằm trong `csdl.khoa_ghi`, trong khi `tao_don` và `ap_trang_thai_giao` thì có.
        Hệ quả: hãng nhận HAI đơn cho một vận đơn, và `billing.kiem_va_tang_don` bị tính hai
        lần. Với hãng không có khóa chống trùng của chính nó (`KHOA_CHONG_TRUNG=False`, mặc
        định của mọi adapter) thì không có gì ở phía hãng gỡ lại được.

        Đo bằng cách bọc `adapter.tao_adapter` trong BỘ THỬ (không sửa mã sản phẩm): adapter
        giả đếm số lượt `createOrder` và giữ cả hai luồng ở trong đó cùng lúc bằng Barrier.
        """
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        don_id = kq["don"]["id"]
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})

        dem = {"n": 0}
        khoa = threading.Lock()
        chan = threading.Barrier(2, timeout=8)
        that = adapter.tao_adapter

        class Giả:
            ma_hang = ten_hang = "jt"

            def capability(self, t):
                return t in ("createOrder", "getShippingFee")

            def createOrder(self, don):
                with khoa:
                    dem["n"] += 1
                try:
                    chan.wait()        # giữ cả hai luồng ở ĐÂY cùng lúc
                except threading.BrokenBarrierError:
                    pass
                return adapter.KetQuaHang(True, ma_van_don="QA2-DOUBLE")

            def getShippingFee(self, don):
                return adapter.KetQuaHang(True, phi=12345)

        adapter.tao_adapter = lambda *a, **k: Giả()
        ket = []
        try:
            def chay():
                kh = Khach().vao("qa2a-owner")
                ket.append(kh.goi(f"/api/v2/don/{don_id}/gui", "POST",
                                  {"carrier_account_id": self.tk["qa2a"]["id"]})[0])
            ts = [threading.Thread(target=chay) for _ in range(2)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(20)
        finally:
            adapter.tao_adapter = that
        self.assertEqual(dem["n"], 1,
                         f"createOrder được gọi {dem['n']} lần cho MỘT đơn (mã trả về: {ket}) "
                         f"— đơn trùng ở phía hãng, và usage bị tính {dem['n']} lần")

    def test_r35_PHAMVI_han_muc_goi_kiem_roi_moi_tang_CHUA_tai_hien_duoc_vuot(self):
        """Rủi ro CẤU TRÚC, CHƯA tái hiện được thành lỗi — ghi ra đúng như đo được.

        `billing.kiem_va_tang_don` đọc usage rồi mới `_tang`; chỉ `_tang` nằm trong
        `csdl.khoa_ghi`, phần KIỂM thì không. Về cấu trúc đây là check-then-act, cùng họ với
        r34. Nhưng phép đo dưới đây (8 luồng Python, cùng một tiến trình, nhả khỏi Barrier cùng
        lúc) **không** làm nó vượt hạn mức: GIL cộng với lượt ghi rất ngắn khiến các luồng bị
        tuần tự hóa trên thực tế.

        Phạm vi kết luận (§12.1 luật 3): "không tái hiện được" chỉ đúng cho **8 luồng trong MỘT
        tiến trình CPython 3.9 trên máy này**. Nó KHÔNG phải lời bảo đảm cho nhiều tiến trình
        (gunicorn/uwsgi nhiều worker), nhiều máy, hay SQLite đặt trên ổ mạng. Ca này để FAIL
        được khi nền chạy đổi — đừng xoá nó vì "đang xanh".
        """
        tid = self.tenant["qa2b"]
        goi = billing.goi_cua_tenant(tid)
        thang = csdl.thang_nay()
        csdl.ghi("INSERT OR IGNORE INTO usage_thang (tenant_id, thang) VALUES (?,?)", (tid, thang))
        csdl.ghi("UPDATE usage_thang SET so_don=? WHERE tenant_id=? AND thang=?",
                 (goi["han_muc_don_thang"] - 1, tid, thang))     # còn đúng 1 suất
        N = 8
        chan = threading.Barrier(N, timeout=8)
        qua = []
        khoa = threading.Lock()

        def chay():
            try:
                chan.wait()
            except threading.BrokenBarrierError:
                pass
            try:
                billing.kiem_va_tang_don(tid)
                with khoa:
                    qua.append(1)
            except billing.VuotHanMuc:
                pass
        ts = [threading.Thread(target=chay) for _ in range(N)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(20)
        self.assertEqual(len(qua), 1,
                         f"còn 1 suất mà {len(qua)}/{N} luồng qua được chốt hạn mức; "
                         f"so_don nay = "
                         f"{csdl.mot('SELECT so_don FROM usage_thang WHERE tenant_id=? AND thang=?', (tid, thang))['so_don']}"
                         f"/{goi['han_muc_don_thang']}")

    def test_r36_LOHONG_webhook_khong_chuan_hoa_ma_trang_thai_cua_hang(self):
        """Chú thích đầu `webhook.py` ghi pipeline có bước NORMALIZE. Mã thì không có bước đó.

        `webhook._xu_ly` lấy `d["event"]` rồi đưa thẳng vào `cau_hinh.HANG_TRANG_THAI_GIAO` —
        bảng chứa TÊN NỘI BỘ (`lay_hang`, `dang_giao`…). Mã riêng của hãng không bao giờ đi qua
        `trang_thai_hang.anh_xa`, dù `polling.py` thì có gọi. Nên khi J&T thật đẩy
        `scanTypeCode=106`/`110`, sự kiện vào tới hàng đợi, lưu thô, rồi bị ghi là
        "loại sự kiện lạ" và đơn KHÔNG đổi trạng thái — hỏng im lặng, không vào DLQ.

        Đây cũng là chỗ **mã 110 nhập nhằng** nằm: hai tầng hiểu 110 khác nhau, mà tầng webhook
        thì chưa hiểu gì cả.
        """
        tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (self.tk["qa2a"]["id"],))
        secret = bao_mat.giai_ma_wh(tk["webhook_secret_ma_hoa"], tk["webhook_ma"])
        # đơn đã gửi thật để webhook resolve được
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        don_id = kq["don"]["id"]
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, kq = self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST",
                                  {"carrier_account_id": tk["id"]})
        self.assertEqual(st, 200, f"không gửi được đơn để đo: {kq}")
        mvd = csdl.mot("SELECT ma_van_don FROM don_hang WHERE id=?", (don_id,))["ma_van_don"]

        body = json.dumps({"event_id": "qa2-jt-106", "event": "106",
                           "tracking_number": mvd}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        st2, _ = Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body,
                             headers={"X-Webhook-Signature": sig})
        self.assertIn(st2, (200, 202))
        webhook.cho_rong(10)
        don = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (don_id,))
        # 106 = Picked Up = lay_hang theo trang_thai_hang.JT_MA
        self.assertEqual(
            trang_thai_hang.anh_xa("jt", "106").trang_thai, "lay_hang",
            "bảng ánh xạ của dự án không còn hiểu 106 — ca này cần viết lại")
        self.assertEqual(
            don["trang_thai_giao"], "lay_hang",
            f"webhook nhận scanTypeCode=106 (Picked Up) mà trạng thái giao vẫn là "
            f"{don['trang_thai_giao']!r} — mã hãng không đi qua trang_thai_hang.anh_xa")

    def test_r37_ANTOAN_webhook_chong_trung_chong_replay_va_khong_cheo_tenant(self):
        """Đã kiểm, không phải lỗ hổng. Phạm vi: một account, một event_id, chữ ký HMAC-SHA256."""
        tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (self.tk["qa2a"]["id"],))
        secret = bao_mat.giai_ma_wh(tk["webhook_secret_ma_hoa"], tk["webhook_ma"])
        tk_b = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (self.tk["qa2b"]["id"],))
        secret_b = bao_mat.giai_ma_wh(tk_b["webhook_secret_ma_hoa"], tk_b["webhook_ma"])
        mvd = csdl.mot("SELECT ma_van_don FROM don_hang WHERE id=? ", (self.don["qa2b"],))

        body = json.dumps({"event_id": "qa2-dup-1", "event": "lay_hang",
                           "tracking_number": "KHONG-CO"}).encode()
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        # 1. chữ ký sai → 401, và secret của account KHÁC cũng không mở được cửa này
        for ten, s in (("chữ ký rác", "deadbeef"),
                       ("secret của tenant khác",
                        hmac.new(secret_b.encode(), body, hashlib.sha256).hexdigest())):
            st, _ = Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body,
                                headers={"X-Webhook-Signature": s})
            self.assertEqual(st, 401, f"{ten} lại được nhận")
        # 2. chữ ký đúng → 202 lần đầu, 200 "đã nhận trước đó" các lần sau (chống trùng/replay)
        st1, kq1 = Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body,
                               headers={"X-Webhook-Signature": sig})
        self.assertEqual(st1, 202)
        for _ in range(3):
            st2, kq2 = Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body,
                                   headers={"X-Webhook-Signature": sig})
            self.assertEqual(st2, 200)
            self.assertEqual(kq2["ket_qua"], "da_nhan_truoc_do")
            self.assertEqual(kq2["su_kien_id"], kq1["su_kien_id"])
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?"
                     " AND event_id='qa2-dup-1'", (tk["id"],))["c"], 1,
            "chống trùng không do ràng buộc CSDL cưỡng chế")
        # 3. ánh xạ sai tenant: ký đúng bằng secret của A nhưng trỏ vận đơn của B
        body2 = json.dumps({"event_id": "qa2-cross-1", "event": "giao_thanh_cong",
                            "tracking_number": mvd["ma_van_don"] or "x"}).encode()
        sig2 = hmac.new(secret.encode(), body2, hashlib.sha256).hexdigest()
        Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body2,
                    headers={"X-Webhook-Signature": sig2})
        webhook.cho_rong(10)
        sk = csdl.mot("SELECT trang_thai FROM wh_su_kien WHERE event_id='qa2-cross-1'")
        self.assertEqual(sk["trang_thai"], "khong_khop",
                         "sự kiện của account A khớp vào đơn của tenant B")

    def test_r38_ANTOAN_webhook_sai_thu_tu_khong_keo_lui_trang_thai(self):
        """Đã kiểm. Phạm vi: rank guard của 6 trạng thái trong cau_hinh.HANG_TRANG_THAI_GIAO."""
        tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (self.tk["qa2a"]["id"],))
        secret = bao_mat.giai_ma_wh(tk["webhook_secret_ma_hoa"], tk["webhook_ma"])
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        don_id = kq["don"]["id"]
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST", {"carrier_account_id": tk["id"]})
        mvd = csdl.mot("SELECT ma_van_don FROM don_hang WHERE id=?", (don_id,))["ma_van_don"]

        def day(ev, eid):
            b = json.dumps({"event_id": eid, "event": ev, "tracking_number": mvd}).encode()
            Khach().goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=b,
                        headers={"X-Webhook-Signature":
                                 hmac.new(secret.encode(), b, hashlib.sha256).hexdigest()})
            webhook.cho_rong(10)
        day("giao_thanh_cong", f"qa2-oo-1-{don_id}")
        self.assertEqual(csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?",
                                  (don_id,))["trang_thai_giao"], "giao_thanh_cong")
        day("lay_hang", f"qa2-oo-2-{don_id}")      # sự kiện đến muộn, hạng thấp hơn
        self.assertEqual(csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?",
                                  (don_id,))["trang_thai_giao"], "giao_thanh_cong",
                         "sự kiện đến muộn kéo lùi được trạng thái giao")

    def test_r39_ANTOAN_idempotency_tao_don_do_rang_buoc_CSDL(self):
        """Đã kiểm. Phạm vi: `Idempotency-Key` trên POST /don, kể cả gửi song song."""
        key = "qa2-idem-" + os.urandom(4).hex()
        ket, khoa = [], threading.Lock()
        chan = threading.Barrier(6, timeout=8)

        def chay():
            kh = Khach().vao("qa2a-owner")
            try:
                chan.wait()
            except threading.BrokenBarrierError:
                pass
            st, kq = kh.goi("/api/v2/don", "POST", dict(DON_MAU),
                            headers={"Idempotency-Key": key})
            with khoa:
                ket.append((st, kq.get("don", {}).get("id")))
        ts = [threading.Thread(target=chay) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(20)
        ids = {i for _, i in ket if i}
        self.assertEqual(len(ids), 1, f"6 yêu cầu cùng Idempotency-Key tạo {len(ids)} đơn: {ket}")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE idem_key=?",
                                  (key,))["c"], 1)

    def test_r40_ANTOAN_sql_cham_bang_co_tenant_id_deu_co_dieu_kien_tenant(self):
        """Soát TĨNH, viết lại độc lập. Phạm vi: chuỗi SQL hằng trong app/*.py (trừ thu/).

        Giới hạn ghi rõ (§12.1 luật 3): chỉ thấy SQL viết thành chuỗi trong mã, không thấy SQL
        ghép động ở thời gian chạy. Danh sách miễn ở dưới là các câu CỐ Ý không mang tenant vì
        đã lọc tenant ở lượt tra trước đó — mỗi dòng miễn phải có lý do.
        """
        co_tenant = {"don_hang", "khach_hang", "carrier_accounts", "import_batch",
                     "tenant_memberships", "usage_thang"}
        # Mỗi dòng miễn phải nêu LÝ DO và lý do phải kiểm được bằng mắt trên mã.
        MIEN = {
            ("don_hang.py", "don_hang"): "các câu còn lại đều mang tenant_id; "
                                         "ap_trang_thai_giao ĐÃ nhận tenant_id từ 15/10 (G04-L2)",
            ("nhap_file.py", "import_batch"): "_lay_dong/chuyen_batch: đã tra theo tenant ở lượt trước",
            ("nhap_file.py", "don_hang"): "đi qua don_hang.tao_don(tenant_id, …)",
            ("webhook.py", "carrier_accounts"): "tra account theo webhook_ma — chính nó XÁC ĐỊNH tenant",
            ("webhook.py", "don_hang"): "câu resolve CÓ tenant_id; câu còn lại đi qua don_hang",
            ("polling.py", "carrier_accounts"): "join sẵn với don_hang đã lọc tenant",
            ("bao_mat.py", "carrier_accounts"): "xoay khóa: CỐ Ý chạy trên MỌI tenant",
            ("sao_luu_khoa.py", "carrier_accounts"):
                "sao lưu khóa: CỐ Ý chạy trên MỌI tenant — gói backup phải phủ hết bản mã, "
                "lọc theo tenant thì khôi phục sẽ thiếu. KIỂM ĐƯỢC: `grep sao_luu_khoa "
                "app/server.py` ra rỗng ⇒ module KHÔNG có cửa HTTP nào, chỉ gọi được từ dòng "
                "lệnh của người vận hành, nên không có đường để một tenant chạm dữ liệu "
                "tenant khác. Cùng loại miễn với bao_mat.py ngay trên.",
            ("server.py", "carrier_accounts"): "ba câu UPDATE … WHERE id=? chạy SAU lượt tra "
                                               "'WHERE id=? AND tenant_id=?' + 404 nếu không có "
                                               "(đã đọc tay app/server.py nhánh /tai-khoan-hang/<id>/<viec>)",
            ("migrate.py", "carrier_accounts"): "migration: CỐ Ý chạy trên mọi tenant",
            ("migrate.py", "import_batch"): "migration: CỐ Ý chạy trên mọi tenant",
            ("migrate.py", "don_hang"): "migration: CỐ Ý chạy trên mọi tenant",
            ("server.py", "tenant_memberships"): "ba câu … WHERE id=? chạy SAU lượt tra "
                                                 "'WHERE id=? AND tenant_id=?' + 404 nếu không có "
                                                 "(nhánh /memberships/<id>); đối chứng ĐỘNG ở cuối ca này",
        }
        thieu = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py"):
                continue
            with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
                src = f.read()
            # GỘP chuỗi liền nhau trước khi soát: SQL trong mã này trải trên nhiều dòng
            # ("SELECT …" " WHERE tenant_id=?"), nên soát từng chuỗi lẻ là tự tạo báo động giả —
            # đúng dạng §12.1 luật 3: công cụ do mình giới hạn cũng phải nghi.
            gop = re.sub(r'"\s*(?:#[^\n]*\n\s*)?"', "", src)
            gop = re.sub(r"'\s*'", "", gop)
            for m in re.finditer(r'"((?:SELECT|UPDATE|DELETE FROM|INSERT INTO)[^"]*)"', gop):
                cau = re.sub(r"\s+", " ", m.group(1))
                for bang in co_tenant:
                    if not re.search(r"\b" + bang + r"\b", cau):
                        continue
                    if re.search(r"tenant_id\s*(=|IN|IS)", cau) or ".tenant_id" in cau:
                        continue
                    if cau.startswith("INSERT INTO") and "tenant_id" in cau:
                        continue
                    if "{' AND '.join(dk)}" in cau:
                        continue        # dk[0] luôn là "tenant_id=?" (app/server.py, GET /don)
                    if (ten, bang) in MIEN:
                        continue
                    thieu.append((ten, bang, cau[:110]))
        self.assertEqual(thieu, [], f"SQL chạm bảng có tenant_id mà không có điều kiện tenant: {thieu}")

        # ĐỐI CHỨNG ĐỘNG cho dòng miễn nặng nhất: ba câu `… tenant_memberships … WHERE id=?`
        # trong server.py. Soát tĩnh chỉ nói "có lượt tra tenant ở trên"; ca dưới đây ĐO thật
        # rằng tenant B không sửa/xoá được membership của tenant A dù biết đúng id.
        mid_a = csdl.mot("SELECT m.id FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                         " WHERE m.tenant_id=? AND u.ten_dang_nhap='qa2a-staff'",
                         (self.tenant["qa2a"],))["id"]
        role_truoc = csdl.mot("SELECT role FROM tenant_memberships WHERE id=?", (mid_a,))["role"]
        for pt, body in (("PUT", {"role": "TENANT_VIEWER"}),
                         ("PUT", {"trang_thai": "vo_hieu"}),
                         ("DELETE", None)):
            st, kq = self.b_owner.goi(f"/api/v2/memberships/{mid_a}", pt, body)
            self.assertIn(st, (403, 404), f"B {pt} được membership của A: {st} {kq}")
        con = csdl.mot("SELECT role, trang_thai FROM tenant_memberships WHERE id=?", (mid_a,))
        self.assertIsNotNone(con, "B xoá được membership của A")
        self.assertEqual(con["role"], role_truoc)
        self.assertEqual(con["trang_thai"], "hoat_dong")

    def test_r41_ANTOAN_moi_duong_api_tenant_deu_qua_mot_cong_kiem_quyen(self):
        """Soát TĨNH + đối chứng ĐỘNG. Phạm vi: `_api_tenant` trong app/server.py.

        Đếm số nhánh `if duong ==` / `re.fullmatch` trong `_api_tenant` và đòi mỗi nhánh có một
        lượt `self._can(` trong khối của nó. Giới hạn: đếm theo văn bản, nên một nhánh gọi
        `_can` ở hàm con sẽ bị báo thiếu — phải xem tay, không tin số máy đếm.
        """
        with open(os.path.join(GOC_APP, "server.py"), encoding="utf-8") as f:
            src = f.read()
        than = src.split("def _api_tenant(")[1].split("\ndef chay(")[0]
        khoi = re.split(r"\n        (?:if |m = re\.fullmatch)", than)
        thieu = [k.split("\n")[0][:90] for k in khoi[1:]
                 if "return" in k and "self._can(" not in k and "self._tra(404" not in k]
        self.assertEqual(thieu, [], f"nhánh API tenant không thấy lượt kiểm quyền: {thieu}")
        # đối chứng động: VIEWER bị chặn đúng ở cửa đã soát (xem r15)
        self.assertEqual(Khach().vao("qa2a-viewer").goi("/api/v2/don", "POST", dict(DON_MAU))[0],
                         403)

    def test_r42_ANTOAN_huy_don_va_sua_don_khong_doi_duoc_don_da_gui(self):
        """Đã kiểm. Phạm vi: vòng đời nhap → da_duyet → da_gui, ba cửa sửa/duyệt/hủy."""
        tk_id = self.tk["qa2a"]["id"]
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        don_id = kq["don"]["id"]
        # chưa duyệt thì không gửi được
        st, _ = self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST",
                                 {"carrier_account_id": tk_id})
        # Nhận CẢ 400 VÀ 409. Đơn chưa duyệt bị TỪ CHỐI thật — AG-00 đọc `don_hang.gui_don`
        # trên bản gộp: `if don["trang_thai"] != "da_duyet": raise LoiNghiepVu(..., 409)`.
        # 409 Conflict là mã đúng nghĩa cho "yêu cầu hợp lệ nhưng trạng thái hiện tại không cho
        # phép", đúng họ với hai ca 409 khác của cùng hàm (đang gửi ở lượt khác / đã gửi rồi).
        # Điều ca thử này canh là ĐƠN KHÔNG ĐƯỢC GỬI, không phải con số mã nào — chốt theo mã
        # cụ thể làm ca hỏng khi mã đổi cho đúng hơn, mà bất biến thật vẫn còn nguyên.
        self.assertIn(st, (400, 409), f"gửi được đơn chưa duyệt (mã {st})")
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, _ = self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        # Cùng lý do như trên: 409 Conflict là mã đúng cho "sai trạng thái", và điều cần canh là
        # lượt duyệt thứ hai BỊ TỪ CHỐI — không phải con số mã.
        self.assertIn(st, (400, 409), f"duyệt lại đơn đã duyệt mà không báo lỗi (mã {st})")
        st, kq = self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST",
                                  {"carrier_account_id": tk_id})
        self.assertEqual(st, 200, f"không gửi được: {kq}")
        st, _ = self.a_owner.goi(f"/api/v2/don/{don_id}", "PUT", {"hang_hoa": "sửa sau khi gửi"})
        self.assertIn(st, (400, 409), f"sửa được đơn đã gửi hãng (mã {st})")
        self.assertEqual(csdl.mot("SELECT hang_hoa FROM don_hang WHERE id=?",
                                  (don_id,))["hang_hoa"], DON_MAU["hang_hoa"])

    def test_r43_ANTOAN_ket_qua_hang_khong_ro_khong_bi_nhan_la_thanh_cong(self):
        """Đã kiểm. Phạm vi: nhánh `timeout=True` của adapter — đơn giữ dang_gui + cờ đối soát."""
        st, kq = self.a_owner.goi("/api/v2/don", "POST", dict(DON_MAU))
        don_id = kq["don"]["id"]
        self.a_owner.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        that = adapter.tao_adapter

        class Treo:
            ma_hang = ten_hang = "jt"

            def capability(self, t):
                return t == "createOrder"

            def createOrder(self, don):
                return adapter.KetQuaHang(False, timeout=True, loi="không rõ kết quả")
        adapter.tao_adapter = lambda *a, **k: Treo()
        try:
            self.a_owner.goi(f"/api/v2/don/{don_id}/gui", "POST",
                             {"carrier_account_id": self.tk["qa2a"]["id"]})
        finally:
            adapter.tao_adapter = that
        d = csdl.mot("SELECT trang_thai, can_doi_soat_ket_qua, ma_van_don FROM don_hang"
                     " WHERE id=?", (don_id,))
        self.assertEqual(d["trang_thai"], "dang_gui", "timeout bị nhận là kết quả dứt khoát")
        self.assertEqual(d["can_doi_soat_ket_qua"], 1, "không bật cờ phải kiểm lại")
        self.assertIsNone(d["ma_van_don"])

    def test_r44_ANTOAN_khong_doc_duoc_dong_import_cua_tenant_khac(self):
        """Đã kiểm. Phạm vi: 4 cửa /import/* nhận id trần từ client."""
        csv = ("nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram\n"
               "Khách A,0901234567,Số 1 Hà Nội,Hàng A,500\n")
        st, kq = self.a_owner.goi("/api/v2/import", "POST", {
            "ten_file": "a.csv", "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        self.assertEqual(st, 201, f"không tạo được batch: {kq}")
        batch = kq["batch_id"]
        dong = csdl.mot("SELECT id FROM import_dong WHERE batch_id=?", (batch,))["id"]
        lo = []
        for duong, pt, body in ((f"/api/v2/import/{batch}", "GET", None),
                                (f"/api/v2/import/{batch}/xuat-csv", "GET", None),
                                (f"/api/v2/import/dong/{dong}", "PUT", {"hang_hoa": "B sửa"}),
                                (f"/api/v2/import/dong/{dong}/xac-nhan", "POST", {}),
                                (f"/api/v2/import/{batch}/duyet", "POST",
                                 {"nguoi_gui": {"ten": "B", "sdt": "0901234567", "dia_chi": "x"},
                                  "dong_ids": [dong]})):
            st2, kq2 = self.b_owner.goi(duong, pt, body)
            if st2 not in (403, 404):
                lo.append((duong, pt, st2, kq2))
        self.assertEqual(lo, [], f"tenant B chạm được import của tenant A: {lo}")

    def test_r45_PHAMVI_ma_jt_110_nhap_nhang_da_duoc_ghi_ra(self):
        """Không phán xét an toàn — chỉ chốt rằng rủi ro 110 ĐANG được ghi lại trong mã.

        §12.1: rủi ro cố ý bỏ qua thì phải ghi ra. Ca này hỏng nếu ai đó dọn chú thích đi mà
        chưa giải quyết được nhập nhằng. Hiện 110 ánh xạ theo BẢNG THAM SỐ = `dang_giao`.
        """
        with open(os.path.join(GOC_APP, "trang_thai_hang.py"), encoding="utf-8") as f:
            src = f.read()
        self.assertIn("110", src)
        self.assertRegex(src, r"(?s)110.*(kiện vấn đề|mâu thuẫn)",
                         "nhập nhằng mã 110 không còn được ghi ra trong mã")
        self.assertEqual(trang_thai_hang.anh_xa("jt", 110).trang_thai, "dang_giao")
        self.assertEqual(trang_thai_hang.anh_xa("jt", "110").trang_thai, "dang_giao")
        self.assertFalse(trang_thai_hang.anh_xa("jt", 999).biet_ma)
        self.assertIsNone(trang_thai_hang.anh_xa("jt", 999).trang_thai,
                          "mã lạ lại đổi trạng thái đơn")

    def test_r46_ANTOAN_khong_doi_duoc_tenant_khong_co_membership(self):
        """Đã kiểm. Phạm vi: /auth/doi-tenant + membership vô hiệu."""
        kh = Khach().vao("qa2a-owner")
        st, _ = kh.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": self.tenant["qa2b"]})
        self.assertEqual(st, 403)
        # Phạm vi ca này: KHÔNG đổi được tenant. Mã HTTP cho kiểu dữ liệu lạ xem r48.
        for xau in (0, -1, 999999, "1 OR 1=1", None, [1], {"a": 1}):
            st2, _ = kh.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": xau})
            self.assertIn(st2, (400, 403, 500), f"đổi được sang tenant_id={xau!r}: {st2}")
            self.assertNotEqual(st2, 200, f"đổi được sang tenant_id={xau!r}")
        self.assertEqual(
            csdl.mot("SELECT active_tenant_id a FROM sessions WHERE token_hash=?",
                     (hashlib.sha256(kh.cookie.split("=", 1)[1].encode()).hexdigest(),))["a"],
            self.tenant["qa2a"])

    def test_r47_ANTOAN_secret_khong_lot_ra_api_audit_hay_log(self):
        """Đã kiểm. Phạm vi: phản hồi 6 cửa + bảng audit + stderr của máy chủ trong lượt chạy này."""
        cred = "QA2-SECRET-KHONG-DUOC-LO-" + os.urandom(6).hex()
        st, kq = self.a_owner.goi("/api/v2/tai-khoan-hang", "POST",
                                  {"hang": "vtp", "ten": "VTP soát", "moi_truong": "mock",
                                   "credentials": {"token": cred}})
        self.assertEqual(st, 201, f"không tạo được tài khoản hãng: {kq}")
        lo = []
        for d in ("/api/v2/tai-khoan-hang", "/api/v2/hang", "/api/v2/audit",
                  "/api/v2/webhook/su-kien", "/api/v2/auth/toi", "/api/v2/billing"):
            _, r = self.a_owner.goi(d)
            if cred in json.dumps(r, ensure_ascii=False, default=str):
                lo.append(d)
        for bang, cot in (("audit", "chi_tiet"), ("don_lich_su", "noi_dung"),
                          ("wh_su_kien", "loi_cuoi")):
            for r in csdl.nhieu(f"SELECT {cot} v FROM {bang}"):
                if r["v"] and cred in str(r["v"]):
                    lo.append(f"{bang}.{cot}")
        if cred in LOG.getvalue():
            lo.append("stderr máy chủ")
        self.assertEqual(lo, [], f"credentials lọt ra: {lo}")
        # bản mã trong CSDL cũng không được chứa chuỗi rõ
        for r in csdl.nhieu("SELECT credentials_ma_hoa v FROM carrier_accounts"):
            self.assertNotIn(cred, str(r["v"]))

    def test_r48_LOHONG_kieu_du_lieu_la_trong_body_thanh_HTTP_500(self):
        """JSON hợp lệ nhưng kiểu sai (list/dict ở chỗ chờ số/chuỗi) → 500, không phải 400.

        500 là "máy chủ hỏng", 400 là "anh gửi sai". Nhầm hai thứ này làm hai việc hỏng cùng
        lúc: người dùng không biết sửa gì, và người vận hành thấy biểu đồ lỗi 5xx đầy rác nên
        không nhận ra lúc máy chủ hỏng thật. Phiên trước đã vá hai ca cùng kiểu (`gioi_han=abc`,
        `cod` không phải số) — nhưng vá theo từng tham số, nên các tham số khác vẫn hở. Đúng
        §12.2: cấu trúc hỏng LẦN THỨ HAI theo cùng một kiểu thì đổi cấu trúc, đừng vá thêm
        một tham số nữa.
        """
        kh = Khach().vao("qa2a-owner")
        lo = []
        thu = [
            ("/api/v2/auth/doi-tenant", "POST", {"tenant_id": [1]}),
            ("/api/v2/auth/doi-tenant", "POST", {"tenant_id": {"a": 1}}),
            ("/api/v2/don", "POST", dict(DON_MAU, khoi_luong_gram=[500])),
            ("/api/v2/khach-hang", "POST", {"ten": {"x": 1}}),
            ("/api/v2/tenant", "PUT", {"ten": [1, 2]}),
            ("/api/v2/import", "POST", {"ten_file": ["a.csv"], "noi_dung_base64": "YQ=="}),
        ]
        for duong, pt, body in thu:
            st, kq = kh.goi(duong, pt, body)
            if st >= 500:
                lo.append((duong, st, kq))
        self.assertEqual(lo, [], f"kiểu dữ liệu lạ trong body làm máy chủ trả 5xx: {lo}")

    def test_r49_ANTOAN_thong_bao_500_khong_lo_chi_tiet_noi_bo(self):
        """Đã kiểm. Dù r48 còn hở, thân phản hồi 500 chỉ nêu TÊN ngoại lệ, không nêu SQL/đường dẫn."""
        kh = Khach().vao("qa2a-owner")
        st, kq = kh.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": [1]})
        if st < 500:
            self.skipTest("không còn tái hiện được 500 — r48 đã được vá, ca này hết việc")
        van = json.dumps(kq, ensure_ascii=False)
        for xau in ("Traceback", "sqlite3", "SELECT", "/Users/", GOC_REPO, "bao_mat.py"):
            self.assertNotIn(xau, van, f"thân 500 lộ chi tiết nội bộ: {xau}")


if __name__ == "__main__":
    unittest.main(verbosity=2, exit=True)
