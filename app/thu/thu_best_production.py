# Bộ thử cho ĐƯỜNG PRODUCTION BEST (wave 2026-10-25). KHÔNG gọi hãng, KHÔNG credential thật:
# mọi lượt mạng đều bị chặn bằng stub `best_hop_dong._goi_json`.
#
# Phủ đúng bốn thứ vừa sửa, và mỗi ca viết ra điều gì sẽ sai nếu bản vá bị gỡ:
#   A. KHO TOKEN — trước bản vá, mỗi thao tác nghiệp vụ gọi `/User/Login` một lượt riêng (đo
#      được trên production 2026-10-24: 1 login + 1 lượt nghiệp vụ cho một lần Báo cước).
#   B. PRODUCTION CHỈ ĐỌC — đăng nhập/báo cước/tra cứu/in phải ĐI QUA; tạo/sửa/hủy phải bị
#      chặn ở CẢ HAI lớp (hàm bọc + `cua_phe_duyet(ghi=True)`).
#   C. CỬA WEBHOOK — GET phải trả 405 + `Allow: POST`, không phải 401 "chưa đăng nhập".
#   D. NGUỒN CALLBACK — `x-forwarded-for` phải nằm trong `headers_json` để phân biệt được
#      callback thật của hãng với lượt mô phỏng nội bộ.
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-best-prod-")

import bao_mat             # noqa: E402
import best_hop_dong as B  # noqa: E402
import csdl                # noqa: E402
import khoi_tao            # noqa: E402
import quyen               # noqa: E402
import server              # noqa: E402
import webhook_best        # noqa: E402
import xac_thuc_best       # noqa: E402

CRED = {"username": "nguoi-dung-gia", "password": "mat-khau-gia-cho-bo-thu"}
CRED2 = {"username": "nguoi-dung-gia", "password": "mat-khau-DA-DOI"}

_NEN = {}
_SV = None
_CONG = None
_COOKIE = None


def _dung_nen():
    if _NEN:
        return _NEN
    csdl.mo()
    quyen.seed()
    khoi_tao.seed_providers()
    tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('prod','PROD','pro',?)",
                   (csdl.bay_gio(),)).lastrowid
    uid = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                   " VALUES ('prodowner',?,'PROD',?)",
                   (bao_mat.bam_mat_khau("MatKhauProd123!"), csdl.bay_gio())).lastrowid
    csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc)"
             " VALUES (?,?,'TENANT_OWNER',?)", (uid, tid, csdl.bay_gio()))
    _NEN.update(tid=tid, uid=uid)
    return _NEN


class _Mang:
    """Thay `_goi_json`: đếm từng endpoint và trả phản hồi dựng sẵn. KHÔNG ra mạng.

    `loi_token_lan_dau=True` mô phỏng đúng ca khó: hãng trả HTTP 200 + `Result=2` +
    `Message="[401] token expired"` cho lượt nghiệp vụ đầu, nên không thể nhìn mã HTTP để biết
    token đã chết.
    """

    def __init__(self, loi_token_lan_dau=False):
        self.dem = {}
        self.loi_token_lan_dau = loi_token_lan_dau
        self.token_da_cap = []

    def __call__(self, url, payload, token=None, ems_key=None, timeout=10):
        duong = url.split("/VietNamV3/v3/api/process/sears", 1)[-1]
        self.dem[duong] = self.dem.get(duong, 0) + 1
        # `_goi_json` trả DATA ĐÃ BÓC bởi `boc_ket_qua`; với `Result=1` đó là chính envelope,
        # nên `token` nằm ở MỨC NGOÀI (xem `boc_token`). Stub phải giữ đúng hình dạng đó.
        if duong == "/User/Login":
            t = "token-gia-%d" % self.dem[duong]
            self.token_da_cap.append(t)
            return True, {"Result": 1, "Message": "", "token": t}, "", 200
        if self.loi_token_lan_dau and self.dem[duong] == 1:
            return False, None, "[401] token expired", 200
        self.token_dung_lan_cuoi = token
        return True, {"Result": 1, "Message": "", "TotalFee": 1000,
                      "data": [{"code": "MA-GIA-01", "status": 211,
                                "traceLogs": [{"status": 211, "modified_at": 1792834753131}]}],
                      "Url": "http://sgp-seaedi.800best.com/waybill/MA-GIA-01.pdf"}, "", 200

    @property
    def so_login(self):
        return self.dem.get("/User/Login", 0)


class Nen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _dung_nen()

    def setUp(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "THU-PROD-001"
        self.goc_goi_json = B._goi_json
        self.goc_tls = B.kiem_tra_tls
        B.kiem_tra_tls = lambda host, timeout=10: {"ok": True, "host": host, "tls": "TLSv1.2"}
        B.bo_token(tat_ca=True)
        self.cookie = _COOKIE

    def tearDown(self):
        B._goi_json = self.goc_goi_json
        B.kiem_tra_tls = self.goc_tls
        B.bo_token(tat_ca=True)
        os.environ.pop("VIP_BEST_OWNER_APPROVED", None)
        os.environ.pop("VIP_BEST_OWNER_APPROVAL_ID", None)

    def don_bao_cuoc(self):
        return {"nguoi_gui_tinh": "Hồ Chí Minh", "nguoi_gui_quan": "Bình Thạnh",
                "nguoi_gui_xa": "Phường 12", "nguoi_gui_dia_chi": "1 Nguyễn Văn Trỗi",
                "nguoi_nhan_tinh": "Hồ Chí Minh", "nguoi_nhan_quan": "Tân Bình",
                "nguoi_nhan_xa": "Phường 10", "nguoi_nhan_dia_chi": "2 Cộng Hoà",
                "khoi_luong_gram": 500, "chieu_dai_mm": 100, "chieu_rong_mm": 100,
                "chieu_cao_mm": 100, "cod": 0, "gia_tri_khai": 0}

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", _CONG, timeout=10)
        h = {"Content-Type": "application/json", "X-Requested-With": "VIPHub"}
        if self.cookie:
            h["Cookie"] = self.cookie
        h.update(headers or {})
        c.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                  headers=h)
        r = c.getresponse()
        raw = r.read()
        hd = dict(r.getheaders())
        c.close()
        try:
            kq = json.loads(raw)
        except Exception:
            kq = None
        return r.status, kq, raw, hd


def setUpModule():
    global _SV, _CONG, _COOKIE
    _dung_nen()
    _SV = ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    _CONG = _SV.server_address[1]
    threading.Thread(target=_SV.serve_forever, daemon=True).start()
    c = http.client.HTTPConnection("127.0.0.1", _CONG, timeout=10)
    c.request("POST", "/api/v2/auth/dang-nhap",
              body=json.dumps({"ten_dang_nhap": "prodowner",
                               "mat_khau": "MatKhauProd123!"}).encode(),
              headers={"Content-Type": "application/json", "X-Requested-With": "VIPHub"})
    r = c.getresponse()
    r.read()
    _COOKIE = (r.getheader("Set-Cookie") or "").split(";")[0]
    c.close()


def tearDownModule():
    if _SV is not None:
        _SV.shutdown()
        _SV.server_close()


# ============================================================================
# A. KHO TOKEN
# ============================================================================
class TestKhoToken(Nen):
    def test_a01_ba_thao_tac_doc_chi_dang_nhap_mot_lan(self):
        """Trước bản vá: 3 thao tác ⇒ 3 lượt `/User/Login`. Sau: đúng 1."""
        m = _Mang()
        B._goi_json = m
        for _ in range(3):
            kq = B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
            self.assertTrue(kq["ok"], kq)
        self.assertEqual(m.so_login, 1, f"đăng nhập {m.so_login} lượt cho 3 thao tác đọc")
        self.assertEqual(m.dem["/Service/EstimateFee"], 3)

    def test_a02_tra_cuu_dung_lai_token_cua_bao_cuoc(self):
        """Kho token dùng chung theo (môi trường, credential), không theo endpoint."""
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        B.tra_cuu_that(["MA-GIA-01"], CRED, B.PRODUCTION, cho_phep_that=True)
        B.in_that(["MA-GIA-01"], CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 1)

    def test_a03_doi_credential_thi_token_cu_khong_duoc_dung(self):
        """Khoá kho là băm của credential: đổi mật khẩu ⇒ phải đăng nhập lại."""
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 1)
        B.bao_gia_that(self.don_bao_cuoc(), CRED2, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 2, "credential đổi nhưng vẫn dùng token cũ")

    def test_a04_sandbox_va_production_khong_dung_chung_token(self):
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.SANDBOX, cho_phep_that=True)
        self.assertEqual(m.so_login, 2, "token của production bị dùng cho sandbox")

    def test_a05_kiem_ket_noi_luon_goi_login_that(self):
        """`dang_nhap_that` KHÔNG được trả 'thành công' từ cache: credential có thể đã bị khoá."""
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 1)
        kq = B.dang_nhap_that(CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertTrue(kq["ok"], kq)
        self.assertEqual(m.so_login, 2, "nút Kiểm tra kết nối chỉ đọc cache — không chứng minh gì")
        self.assertIs(kq["meta"].get("token_tu_kho"), False)

    def test_a06_token_bi_tu_choi_thi_dang_nhap_lai_mot_lan_roi_thu_lai(self):
        """Hãng thu hồi token trước hạn ⇒ thao tác ĐỌC phải tự lấy token mới và thử lại 1 lần."""
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 1)
        m.loi_token_lan_dau = True
        m.dem["/Order/Query"] = 0
        kq = B.tra_cuu_that(["MA-GIA-01"], CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 2, "token bị từ chối mà không đăng nhập lại")
        self.assertEqual(m.dem["/Order/Query"], 2, "không thử lại sau khi có token mới")
        self.assertTrue(kq["meta"].get("dang_nhap_lai_sau_401"))

    def test_a07_khong_thu_lai_mu_cho_thao_tac_ghi(self):
        """Thao tác GHI chỉ bỏ token, KHÔNG gửi lại: lượt đầu có thể đã tạo đơn ở hãng."""
        m = _Mang(loi_token_lan_dau=False)
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.SANDBOX, cho_phep_that=True)
        self.assertEqual(m.so_login, 1)
        m.loi_token_lan_dau = True
        kq = B.huy_that("MA-GIA-01", CRED, B.SANDBOX, cho_phep_that=True,
                        xac_nhan=B.CAU_XAC_NHAN_GHI)
        self.assertFalse(kq["ok"])
        self.assertEqual(m.dem["/Order/Cancel"], 1, "đã gửi lại một thao tác GHI — nguy cơ trùng")
        self.assertEqual(m.so_login, 1, "không được đăng nhập lại để thử lại thao tác ghi")
        self.assertTrue(kq["meta"].get("token_da_bo"))

    def test_a08_loi_tai_khoan_404_khong_bi_coi_la_loi_token(self):
        """`[404] The account not found or have been locked` là lỗi TÀI KHOẢN: đăng nhập lại
        chỉ nhận đúng lỗi đó lần hai và tiêu thêm một lượt credential."""
        self.assertFalse(B._la_loi_token("[404] The account not found or have been locked"))
        self.assertTrue(B._la_loi_token("[401] token expired"))
        self.assertTrue(B._la_loi_token("Unauthorized"))

    def test_a09_kho_token_khong_lo_token_khi_mo_ta(self):
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        tt = B.trang_thai_token_kho(CRED, B.PRODUCTION)
        raw = json.dumps(tt)
        self.assertTrue(tt["tai_khoan_nay"]["co_token"])
        self.assertFalse(tt["luu_tren_dia"])
        for t in m.token_da_cap:
            self.assertNotIn(t, raw)
        self.assertNotIn(CRED["password"], raw)

    def test_a10_bo_token_thi_lan_sau_dang_nhap_lai(self):
        m = _Mang()
        B._goi_json = m
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(B.bo_token(CRED, B.PRODUCTION), 1)
        B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=True)
        self.assertEqual(m.so_login, 2)

    def test_a11_khong_phe_duyet_thi_khong_cham_mang_va_khong_luu_token(self):
        m = _Mang()
        B._goi_json = m
        kq = B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION, cho_phep_that=False)
        self.assertFalse(kq["ok"])
        self.assertTrue(kq["blocked"])
        self.assertEqual(m.so_login, 0, "đã gọi hãng dù chưa có xác nhận")
        self.assertEqual(B.trang_thai_token_kho()["so_token_dang_nho"], 0)


# ============================================================================
# B. PRODUCTION CHỈ ĐỌC
# ============================================================================
class TestProductionChiDoc(Nen):
    def test_b01_bon_thao_tac_doc_di_qua_duoc_tren_production(self):
        """Đây là cổng từng bị chặn SAI: `cua_phe_duyet` chỉ được từ chối production khi ghi."""
        m = _Mang()
        B._goi_json = m
        self.assertTrue(B.dang_nhap_that(CRED, B.PRODUCTION, cho_phep_that=True)["ok"])
        self.assertTrue(B.bao_gia_that(self.don_bao_cuoc(), CRED, B.PRODUCTION,
                                       cho_phep_that=True)["ok"])
        self.assertTrue(B.tra_cuu_that(["MA-GIA-01"], CRED, B.PRODUCTION,
                                       cho_phep_that=True)["ok"])
        for ghi in (False,):
            ok, ly_do = B.cua_phe_duyet(B.PRODUCTION, True, ghi=ghi)
            self.assertTrue(ok, ly_do)

    def test_b02_ba_thao_tac_ghi_bi_chan_o_ca_hai_lop(self):
        m = _Mang()
        B._goi_json = m
        for ten, goi in (
            ("tao_don", lambda: B.tao_don_that({"ma_don": "X"}, CRED, B.PRODUCTION,
                                               cho_phep_that=True,
                                               xac_nhan=B.CAU_XAC_NHAN_GHI)),
            ("cap_nhat", lambda: B.cap_nhat_that({"ma_van_don": "X"}, CRED, B.PRODUCTION,
                                                 cho_phep_that=True,
                                                 xac_nhan=B.CAU_XAC_NHAN_GHI)),
            ("sua_dia_chi", lambda: B.sua_dia_chi_that({"ma_van_don": "X"}, CRED, B.PRODUCTION,
                                                       cho_phep_that=True,
                                                       xac_nhan=B.CAU_XAC_NHAN_GHI)),
            ("huy", lambda: B.huy_that("X", CRED, B.PRODUCTION, cho_phep_that=True,
                                       xac_nhan=B.CAU_XAC_NHAN_GHI)),
        ):
            kq = goi()
            self.assertFalse(kq["ok"], f"{ten} production KHÔNG bị chặn")
            self.assertTrue(kq["blocked"], f"{ten} không báo blocked")
        # Lớp thứ hai: kể cả khi hàm bọc bị gỡ, cổng phê duyệt vẫn từ chối.
        ok, ly_do = B.cua_phe_duyet(B.PRODUCTION, True, ghi=True,
                                    xac_nhan=B.CAU_XAC_NHAN_GHI)
        self.assertFalse(ok)
        self.assertIn("PRODUCTION", ly_do)
        self.assertEqual(m.dem, {}, "một thao tác ghi production đã chạm tới lớp mạng")

    def test_b03_route_tao_don_production_tra_403_khong_cham_mang(self):
        m = _Mang()
        B._goi_json = m
        st, kq, raw, _ = self.req("POST", "/api/v2/tai-khoan-hang",
                                  {"hang": "best", "ten": "BEST prod", "moi_truong": "production",
                                   "credentials": CRED})
        self.assertEqual(st, 201, raw)
        tk = kq["id"]
        st2, kq2, raw2, _ = self.req("POST", "/api/v2/best/tao-don",
                                     {"tai_khoan_id": tk, "xac_nhan_that": True,
                                      "xac_nhan": B.CAU_XAC_NHAN_GHI,
                                      "don": {"ma_don": "KHONG-TAO"}})
        self.assertEqual(st2, 403, raw2)
        self.assertTrue(kq2["blocked"])
        self.assertEqual(m.dem, {}, "route tạo đơn production đã gọi hãng")

    def test_b04_route_bao_cuoc_production_di_qua(self):
        m = _Mang()
        B._goi_json = m
        st, kq, raw, _ = self.req("POST", "/api/v2/tai-khoan-hang",
                                  {"hang": "best", "ten": "BEST prod 2",
                                   "moi_truong": "production", "credentials": CRED})
        self.assertEqual(st, 201, raw)
        st2, kq2, raw2, _ = self.req("POST", "/api/v2/best/bao-gia",
                                     {"tai_khoan_id": kq["id"], "xac_nhan_that": True,
                                      "don": self.don_bao_cuoc()})
        self.assertEqual(st2, 200, raw2)
        self.assertTrue(kq2["ok"])
        self.assertNotIn(b"token-gia", raw2, "token đi ra response")


# ============================================================================
# C. CỬA WEBHOOK — GET phải 405, không phải 401
# ============================================================================
class TestCuaWebhook(Nen):
    def test_c01_get_tra_405_va_allow_post(self):
        st, kq, raw, hd = self.req("GET", "/api/v2/webhook/nhan/dinh-danh-khong-co-that")
        self.assertEqual(st, 405, raw)
        self.assertEqual(hd.get("Allow"), "POST")
        self.assertEqual(kq.get("Result"), 0)
        self.assertNotIn("đăng nhập", json.dumps(kq, ensure_ascii=False))

    def test_c02_get_khong_tiet_lo_dinh_danh_nao_co_that(self):
        """Hai định danh — một có thật, một không — phải cho câu trả lời GIỐNG NHAU."""
        st, kq, raw, _ = self.req("POST", "/api/v2/tai-khoan-hang",
                                  {"hang": "best", "ten": "BEST wh", "moi_truong": "mock",
                                   "credentials": CRED})
        self.assertEqual(st, 201, raw)
        ma_that = csdl.mot("SELECT webhook_ma FROM carrier_accounts WHERE id=?",
                           (kq["id"],))["webhook_ma"]
        a = self.req("GET", f"/api/v2/webhook/nhan/{ma_that}")
        b = self.req("GET", "/api/v2/webhook/nhan/khong-ton-tai-chac-chan")
        self.assertEqual((a[0], a[1]), (b[0], b[1]))

    def test_c03_post_van_di_vao_duong_webhook_chu_khong_bi_405(self):
        """Chốt 405 không được chặn luôn POST — đó là cửa thật của hãng.

        Định danh lạ trả 404 với hình dạng CHUNG (`{"loi":...}`), không phải `{"Result":...}`:
        chưa tra được tài khoản thì chưa biết đây là BEST hay hãng khác, nên không được chọn
        hình dạng phản hồi của một hãng cụ thể. Ca này chỉ canh KHÔNG phải 405.
        """
        st, kq, raw, _ = self.req("POST", "/api/v2/webhook/nhan/khong-ton-tai", {})
        self.assertEqual(st, 404, raw)
        self.assertIsNone(kq.get("Result"))


# ============================================================================
# D. PHÂN BIỆT CALLBACK THẬT VỚI MÔ PHỎNG NỘI BỘ
# ============================================================================
class TestNguonCallback(Nen):
    def _tk_sandbox_co_bearer(self, bearer):
        st, kq, raw, _ = self.req("POST", "/api/v2/tai-khoan-hang",
                                  {"hang": "best", "ten": "BEST nguon",
                                   "moi_truong": "sandbox", "credentials": CRED})
        self.assertEqual(st, 201, raw)
        st2, _, raw2, _ = self.req("POST", "/api/v2/best/webhook-bearer",
                                   {"tai_khoan_id": kq["id"], "bearer": bearer})
        self.assertEqual(st2, 200, raw2)
        ma = csdl.mot("SELECT webhook_ma FROM carrier_accounts WHERE id=?",
                      (kq["id"],))["webhook_ma"]
        return kq["id"], ma

    def test_d01_x_forwarded_for_duoc_luu_de_truy_nguon(self):
        bearer = "v9.bearer-gia-" + "d" * 24
        tk_id, ma = self._tk_sandbox_co_bearer(bearer)
        than = {"code_best": "SIM-NGUON-01", "merchant_order_code": "SIM-NGUON-01",
                "status": "211", "modified_at": 1792834753131,
                "status_content": "mô phỏng nội bộ"}
        st, kq, raw, _ = self.req(
            "POST", f"/api/v2/webhook/nhan/{ma}", than,
            headers={"Authorization": f"Bearer {bearer}",
                     "X-Forwarded-For": "203.0.113.7",
                     "User-Agent": "vip-hub-mo-phong-noi-bo"})
        self.assertEqual(st, 200, raw)
        self.assertEqual(kq, {"Result": 1, "Message": ""})
        r = csdl.mot("SELECT headers_json FROM wh_su_kien WHERE carrier_account_id=?", (tk_id,))
        hd = json.loads(r["headers_json"])
        self.assertEqual(hd.get("x-forwarded-for"), "203.0.113.7",
                         "không ghi nguồn ⇒ không phân biệt được callback thật với mô phỏng")
        self.assertEqual(hd.get("user-agent"), "vip-hub-mo-phong-noi-bo")

    def test_d02_authorization_khong_bao_gio_duoc_luu(self):
        bearer = "v9.bearer-gia-" + "e" * 24
        tk_id, ma = self._tk_sandbox_co_bearer(bearer)
        than = {"code_best": "SIM-NGUON-02", "merchant_order_code": "SIM-NGUON-02",
                "status": "202", "modified_at": 1792834753131}
        st, _, raw, _ = self.req("POST", f"/api/v2/webhook/nhan/{ma}", than,
                                 headers={"Authorization": f"Bearer {bearer}",
                                          "X-Forwarded-For": "203.0.113.8"})
        self.assertEqual(st, 200, raw)
        r = csdl.mot("SELECT headers_json, payload_tho FROM wh_su_kien"
                     " WHERE carrier_account_id=?", (tk_id,))
        self.assertNotIn("authorization", r["headers_json"].lower())
        self.assertNotIn(bearer, r["headers_json"])
        self.assertNotIn(bearer.encode(), bytes(r["payload_tho"]))

    def test_d03_ack_dung_dac_ta_va_chong_trung(self):
        bearer = "v9.bearer-gia-" + "f" * 24
        tk_id, ma = self._tk_sandbox_co_bearer(bearer)
        than = {"code_best": "SIM-NGUON-03", "merchant_order_code": "SIM-NGUON-03",
                "status": "211", "modified_at": 1792834753131}
        h = {"Authorization": f"Bearer {bearer}"}
        for _ in range(3):
            st, kq, raw, _ = self.req("POST", f"/api/v2/webhook/nhan/{ma}", than, headers=h)
            self.assertEqual(st, 200, raw)
            self.assertEqual(kq, {"Result": 1, "Message": ""})
        n = csdl.mot("SELECT count(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                     (tk_id,))["c"]
        self.assertEqual(n, 1, "callback trùng tạo nhiều dòng")

    def test_d04_bearer_sai_thi_401_va_khong_luu_gi(self):
        bearer = "v9.bearer-gia-" + "g" * 24
        tk_id, ma = self._tk_sandbox_co_bearer(bearer)
        than = {"code_best": "SIM-NGUON-04", "merchant_order_code": "SIM-NGUON-04",
                "status": "211", "modified_at": 1792834753131}
        st, kq, raw, _ = self.req("POST", f"/api/v2/webhook/nhan/{ma}", than,
                                  headers={"Authorization": "Bearer sai-hoan-toan"})
        self.assertEqual(st, 401, raw)
        self.assertEqual(kq.get("Result"), 0)
        n = csdl.mot("SELECT count(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                     (tk_id,))["c"]
        self.assertEqual(n, 0, "đã lưu sự kiện dù Bearer sai")

    def test_d05_bearer_dang_nhap_api_khong_dung_duoc_cho_webhook(self):
        """Hai lớp khoá PHẢI rời nhau: token `/User/Login` không phải Bearer webhook."""
        bearer = "v9.bearer-gia-" + "h" * 24
        tk_id, ma = self._tk_sandbox_co_bearer(bearer)
        m = _Mang()
        B._goi_json = m
        token_api, _meta, loi = B.lay_token_that(CRED, B.SANDBOX, cho_phep_that=True)
        self.assertTrue(token_api, loi)
        than = {"code_best": "SIM-NGUON-05", "merchant_order_code": "SIM-NGUON-05",
                "status": "211", "modified_at": 1792834753131}
        st, kq, raw, _ = self.req("POST", f"/api/v2/webhook/nhan/{ma}", than,
                                  headers={"Authorization": f"Bearer {token_api}"})
        self.assertEqual(st, 401, raw)
        kq_b = xac_thuc_best.kiem_bearer_webhook(
            str(_NEN["tid"]), str(tk_id), f"Bearer {token_api}")
        self.assertFalse(kq_b.hop_le)
        self.assertEqual(kq_b.ma_ly_do, "BEARER_KHONG_KHOP")

    def test_d06_ack_cua_mo_dun_dung_hang_dac_ta(self):
        self.assertEqual(webhook_best.thanh_cong(), {"Result": 1, "Message": ""})
        self.assertEqual(webhook_best.kiem_bat_bien(), [])


if __name__ == "__main__":
    import unittest as _ut
    kq = _ut.TextTestRunner(verbosity=2).run(
        _ut.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f"\nCa chạy: {kq.testsRun} · lỗi: {len(kq.errors)} · hỏng: {len(kq.failures)} "
          f"· skip: {len(kq.skipped)}")
    print("KẾT QUẢ:", "ĐẠT" if kq.wasSuccessful() else "HỎNG")
    sys.exit(0 if kq.wasSuccessful() else 1)
