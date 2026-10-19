# Bộ thử HTTP cho BÀN NGHIỆM THU BEST — không gọi hãng, không credential thật.
#
# Đo: route hợp đồng/trạng thái, tạo tài khoản mock/sandbox có phê duyệt, lưu Bearer webhook,
# và các đường thao tác thật phải trả BLOCKED trước khi chạm mạng nếu chưa đủ phê duyệt.
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
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-best-uat-")

import bao_mat          # noqa: E402
import csdl             # noqa: E402
import khoi_tao         # noqa: E402
import quyen            # noqa: E402
import server           # noqa: E402

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
    tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES ('uat','UAT','pro',?)",
                   (csdl.bay_gio(),)).lastrowid
    uid = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                   " VALUES ('uatowner',?, 'UAT', ?)",
                   (bao_mat.bam_mat_khau("MatKhauUat123!"), csdl.bay_gio())).lastrowid
    csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc)"
             " VALUES (?,?,'TENANT_OWNER',?)", (uid, tid, csdl.bay_gio()))
    _NEN.update(tid=tid, uid=uid)
    return _NEN


class Nen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _dung_nen()

    def setUp(self):
        os.environ.pop("VIP_BEST_OWNER_APPROVED", None)
        os.environ.pop("VIP_BEST_OWNER_APPROVAL_ID", None)
        self.cookie = _COOKIE

    def req(self, method, path, body=None, cookie=None):
        c = http.client.HTTPConnection("127.0.0.1", _CONG, timeout=10)
        h = {"Content-Type": "application/json", "X-Requested-With": "VIPHub"}
        if cookie or self.cookie:
            h["Cookie"] = cookie or self.cookie
        c.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                  headers=h)
        r = c.getresponse()
        raw = r.read()
        c.close()
        try:
            kq = json.loads(raw)
        except Exception:
            kq = None
        return r.status, kq, raw

    def _tk(self, mt="mock", ten="BEST UAT"):
        st, kq, raw = self.req("POST", "/api/v2/tai-khoan-hang",
                               {"hang": "best", "ten": ten, "moi_truong": mt,
                                "credentials": {"username": "uat", "password": "secret-uat"}})
        return st, kq, raw


def setUpModule():
    global _SV, _CONG, _COOKIE
    _dung_nen()
    _SV = ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    _CONG = _SV.server_address[1]
    threading.Thread(target=_SV.serve_forever, daemon=True).start()
    c = http.client.HTTPConnection("127.0.0.1", _CONG, timeout=10)
    c.request("POST", "/api/v2/auth/dang-nhap",
              body=json.dumps({"ten_dang_nhap": "uatowner",
                               "mat_khau": "MatKhauUat123!"}).encode(),
              headers={"Content-Type": "application/json", "X-Requested-With": "VIPHub"})
    r = c.getresponse()
    r.read()
    _COOKIE = (r.getheader("Set-Cookie") or "").split(";")[0]
    c.close()


def tearDownModule():
    if _SV is not None:
        _SV.shutdown()
        _SV.server_close()


class TestUATHTTP(Nen):
    def test_01_hop_dong_23_ma_va_8_endpoint(self):
        st, kq, raw = self.req("GET", "/api/v2/best/hop-dong")
        self.assertEqual(st, 200, raw)
        self.assertEqual(kq["so_ma"], 23)
        self.assertEqual(kq["service_id"], 12491)
        self.assertEqual(len(kq["endpoints"]), 8)
        self.assertTrue(kq["base_url"]["sandbox"].startswith("https://"))

    def test_02_trang_thai_khong_lo_secret(self):
        st, kq, raw = self.req("GET", "/api/v2/best/trang-thai")
        self.assertEqual(st, 200, raw)
        self.assertIn("co_phe_duyet_owner", kq)
        self.assertNotIn(b"password", raw.lower())
        self.assertNotIn(b"bearer", raw.lower())

    def test_03_tao_tai_khoan_mock_khong_tra_hmac_secret(self):
        st, kq, raw = self._tk("mock", "BEST mock UAT")
        self.assertEqual(st, 201, raw)
        self.assertNotIn("webhook_secret_mot_lan", kq)
        self.assertIn("webhook_url", kq)

    def test_04_sandbox_khong_phe_duyet_bi_chan(self):
        st, kq, raw = self._tk("sandbox", "BEST sandbox chưa duyệt")
        self.assertEqual(st, 403, raw)
        self.assertIn("BLOCKED", kq.get("loi", ""))

    def test_05_sandbox_co_phe_duyet_duoc_luu(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        st, kq, raw = self._tk("sandbox", "BEST sandbox UAT")
        self.assertEqual(st, 201, raw)
        self.assertNotIn("webhook_secret_mot_lan", kq)
        self._tk_id = kq["id"]

    def test_06_kiem_ket_noi_mock_bi_tu_choi(self):
        st, kq, raw = self._tk("mock", "BEST mock check")
        self.assertEqual(st, 201)
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/kiem-ket-noi",
                                  {"tai_khoan_id": kq["id"], "xac_nhan_that": False})
        self.assertEqual(st2, 400, raw2)
        self.assertIn("mock", kq2["loi"].lower())

    def test_07_kiem_ket_noi_sandbox_chua_xac_nhan_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        st, kq, raw = self._tk("sandbox", "BEST sandbox check")
        self.assertEqual(st, 201, raw)
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/kiem-ket-noi",
                                  {"tai_khoan_id": kq["id"], "xac_nhan_that": False})
        self.assertEqual(st2, 403, raw2)
        self.assertIn("xác nhận", kq2.get("loi", ""))
        self.assertNotIn(b"bearer", raw2.lower())
        self.assertNotIn(b"authorization", raw2.lower())

    def test_08_luu_bearer_webhook_khong_echo(self):
        st, kq, raw = self._tk("mock", "BEST mock webhook")
        self.assertEqual(st, 201)
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/webhook-bearer",
                                  {"tai_khoan_id": kq["id"], "bearer": "v9." + "b" * 30})
        self.assertEqual(st2, 200, raw2)
        self.assertTrue(kq2["ok"])
        self.assertNotIn(b"v9.", raw2.lower())

    def test_09_bao_gia_chua_phe_duyet_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        st, kq, raw = self._tk("sandbox", "BEST sandbox fee")
        self.assertEqual(st, 201, raw)
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/bao-gia",
                                  {"tai_khoan_id": kq["id"], "xac_nhan_that": False,
                                   "don": {"nguoi_gui_tinh": "Hồ Chí Minh",
                                           "nguoi_gui_quan": "Bình Thạnh",
                                           "nguoi_nhan_tinh": "Hồ Chí Minh",
                                           "nguoi_nhan_quan": "Tân Bình",
                                           "nguoi_gui_dia_chi": "1",
                                           "nguoi_nhan_dia_chi": "2",
                                           "khoi_luong_gram": 100}})
        self.assertEqual(st2, 403, raw2)
        self.assertTrue(kq2.get("blocked"))

    def test_10_tao_don_sandbox_chua_phe_duyet_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        st, kq, raw = self._tk("sandbox", "BEST sandbox order")
        self.assertEqual(st, 201, raw)
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/tao-don",
                                  {"tai_khoan_id": kq["id"], "xac_nhan_that": False,
                                   "don": {"ma_don": "UAT-X", "hang_hoa": "Hàng",
                                           "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0901",
                                           "nguoi_gui_tinh": "HCM", "nguoi_gui_xa": "P1",
                                           "nguoi_gui_dia_chi": "1",
                                           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0902",
                                           "nguoi_nhan_tinh": "HCM", "nguoi_nhan_xa": "P2",
                                           "nguoi_nhan_dia_chi": "2",
                                           "khoi_luong_gram": 500, "journey_type": 1}})
        self.assertEqual(st2, 403, raw2)
        self.assertTrue(kq2.get("blocked"))

    def test_11_tao_don_production_luon_bi_chan(self):
        os.environ["VIP_BEST_OWNER_APPROVED"] = "1"
        os.environ["VIP_BEST_OWNER_APPROVAL_ID"] = "UAT-2026-001"
        st, kq, raw = self._tk("sandbox", "BEST sandbox prod-block")
        self.assertEqual(st, 201, raw)
        # Đổi DB sang production để kiểm chốt; không gọi mạng.
        csdl.ghi("UPDATE carrier_accounts SET moi_truong='production' WHERE id=?", (kq["id"],))
        st2, kq2, raw2 = self.req("POST", "/api/v2/best/tao-don",
                                  {"tai_khoan_id": kq["id"], "xac_nhan_that": True,
                                   "xac_nhan": "TOI_DONG_Y_GOI_BEST_TEST",
                                   "don": {"ma_don": "UAT-P", "hang_hoa": "Hàng",
                                           "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0901",
                                           "nguoi_gui_tinh": "HCM", "nguoi_gui_xa": "P1",
                                           "nguoi_gui_dia_chi": "1",
                                           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0902",
                                           "nguoi_nhan_tinh": "HCM", "nguoi_nhan_xa": "P2",
                                           "nguoi_nhan_dia_chi": "2",
                                           "khoi_luong_gram": 500, "journey_type": 1}})
        self.assertEqual(st2, 403, raw2)
        self.assertIn("PRODUCTION", kq2.get("loi", ""))

    def test_12_lich_su_200(self):
        st, kq, raw = self.req("GET", "/api/v2/best/lich-su")
        self.assertEqual(st, 200, raw)
        self.assertIn("su_kien", kq)
        self.assertIn("audit", kq)


if __name__ == "__main__":
    import unittest as _ut
    kq = _ut.TextTestRunner(verbosity=2).run(
        _ut.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f"\nCa chạy: {kq.testsRun} · lỗi: {len(kq.errors)} · hỏng: {len(kq.failures)} "
          f"· skip: {len(kq.skipped)}")
    print("KẾT QUẢ:", "ĐẠT" if kq.wasSuccessful() else "HỎNG")
    sys.exit(0 if kq.wasSuccessful() else 1)
