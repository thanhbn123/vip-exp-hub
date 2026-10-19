# B1 — BỘ THỬ ADAPTER BEST EXPRESS.
#
# PHẠM VI ĐO — ĐỌC TRƯỚC KHI TIN BẤT KỲ CON SỐ NÀO:
#   · MOCK PASS, KHÔNG phải REAL PASS. Mọi lượt gọi đi tới STUB LOOPBACK `127.0.0.1` với cổng
#     do OS cấp (`port=0`). KHÔNG có lượt gọi nào tới `800best.com`, kể cả test host.
#   · Không credentials thật: toàn bộ chuỗi bí mật trong tệp này là bí mật GIẢ của bộ thử.
#   · Không đơn thật, không ghi CSDL nghiệp vụ: `VIP_HUB_DATA` trỏ vào thư mục tạm.
#   · Tài liệu BEST (Google Docs) KHÔNG đọc được ⇒ schema/response/mã trạng thái CHƯA XÁC MINH.
#     Bộ thử đo HỢP ĐỒNG NỘI BỘ và ĐƯỜNG GỬI trên stub, KHÔNG đo tính tương thích với BEST thật.
#
# Chạy: python3 app/thu/thu_best_adapter.py
import json
import os
import sys
import tempfile
import threading
import time
import tokenize
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock
from urllib.parse import urlsplit

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU_MUC_THU = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC_APP)
if THU_MUC_THU not in sys.path:
    sys.path.insert(0, THU_MUC_THU)

_tam = tempfile.mkdtemp(prefix="vip-hub-b1-best-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import adapter          # noqa: E402
import adapter_best as ab  # noqa: E402
import http_best as hb  # noqa: E402
import loi_hang as lh   # noqa: E402
import transport as tp  # noqa: E402
import trang_thai_hang as tth  # noqa: E402

# Bí mật GIẢ của bộ thử — cũng là bộ dò rò rỉ. Chuỗi nào xuất hiện trong kết quả/log là HỎNG.
CRED = {"tenant_id": "1", "carrier_id": "9", "carrier_account_id": "9",
        "username": "u-test", "password": "p-test"}
SECRETS = ("u-test", "p-test", "MOCK-TOKEN-KHONG-THAT", "TOKEN-BI-MAT")

XOA = object()


def make_don(**kw):
    d = {
        "tenant_id": "1", "carrier_account_id": "9",
        "ma_don": "T1-000001", "idem_key": "IDEM-1",
        "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111",
        "nguoi_gui_dia_chi": "1 Đường Gửi", "nguoi_gui_tinh": "Tỉnh Gửi",
        "nguoi_gui_quan": "Quận Gửi", "nguoi_gui_xa": "Phường Gửi",
        "nguoi_nhan_ten": "Khách Thử", "nguoi_nhan_sdt": "0902222222",
        "nguoi_nhan_dia_chi": "2 Đường Nhận", "nguoi_nhan_tinh": "Tỉnh Nhận",
        "nguoi_nhan_quan": None, "nguoi_nhan_xa": "Phường Nhận",
        "hang_hoa": "Áo thử", "khoi_luong_gram": 1500,
        "cod": 15000, "gia_tri_khai": 200000,
        "journey_type": 1,
        "chieu_dai_mm": 200, "chieu_rong_mm": 100, "chieu_cao_mm": 50,
        "ghi_chu": "ghi chú thử",
    }
    for k, v in kw.items():
        if v is XOA:
            d.pop(k, None)
        else:
            d[k] = v
    return d


def quet_bi_mat(doi_tuong, danh_sach=SECRETS):
    chuoi = json.dumps(doi_tuong, ensure_ascii=False, default=str)
    return [b for b in danh_sach if b and b in chuoi]


def ma_khong_comment(duong_dan):
    """Đọc mã nguồn đã bỏ comment/chuỗi thừa để kiểm chốt chặn cấp mã."""
    with open(duong_dan, "rb") as f:
        return " ".join(t.string for t in tokenize.tokenize(f.readline)
                        if t.type not in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE))


# =================================================================================================
# STUB CỤC BỘ — cổng do OS cấp, chỉ 127.0.0.1
# =================================================================================================
class StubBEST:
    def __init__(self):
        self.requests = []
        self._lock = threading.Lock()
        stub = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def log_error(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                than = self.rfile.read(n)
                path = urlsplit(self.path).path
                stub._ghi("POST", path, dict(self.headers), than)
                try:
                    data = json.loads(than.decode("utf-8")) if than else {}
                except (UnicodeDecodeError, ValueError):
                    data = {}
                stub._tra_loi(self, path, data)

            def do_GET(self):
                path = urlsplit(self.path).path
                stub._ghi("GET", path, dict(self.headers), b"")
                stub._tra_loi_get(self, path)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def base_url(self):
        return f"http://127.0.0.1:{self.port}/VietNamV3/v3/api/process/sears"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)

    def reset(self):
        with self._lock:
            self.requests = []

    def _ghi(self, method, path, headers, body):
        with self._lock:
            self.requests.append({"method": method, "path": path, "headers": headers,
                                  "body": body})

    def paths(self):
        return [(r["method"], r["path"]) for r in self.requests]

    def count(self, duoi):
        return sum(1 for r in self.requests if r["path"].endswith(duoi))

    def bodies(self, duoi):
        ra = []
        for r in self.requests:
            if r["path"].endswith(duoi) and r["method"] == "POST":
                try:
                    ra.append(json.loads(r["body"].decode("utf-8")))
                except (UnicodeDecodeError, ValueError):
                    ra.append(None)
        return ra

    def headers_for(self, duoi):
        return [r["headers"] for r in self.requests if r["path"].endswith(duoi)]

    def _gui(self, handler, status, body, content_type="application/json", headers=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        try:
            handler.send_response(status)
            handler.send_header("Content-Type", content_type)
            handler.send_header("Content-Length", str(len(body)))
            handler.send_header("Connection", "close")
            for k, v in (headers or {}).items():
                handler.send_header(k, v)
            handler.end_headers()
            handler.wfile.write(body)
        except OSError:
            pass

    def _tra_loi(self, handler, path, data):
        if path.endswith("/User/Login"):
            return self._gui(handler, 200, {"token": "MOCK-TOKEN-KHONG-THAT",
                                            "Result": 1, "Message": None})
        if path.endswith("/Order/Add"):
            ma = str(data.get("Code") or "")
            if ma.startswith("TIMEOUT"):
                time.sleep(0.6)
            if ma.startswith("FAIL500"):
                return self._gui(handler, 500, {"Result": 2, "Message": "server error"})
            if ma.startswith("FAIL400"):
                return self._gui(handler, 400, {"Result": 2, "Message": "bad request"})
            if ma.startswith("ECHOSECRET"):
                return self._gui(handler, 200, {"Result": 2, "Message": "p-test"})
            return self._gui(handler, 200, {"Result": 1, "Message": None,
                                            "Code": "BEST-" + ma,
                                            "RouteCode": "SG905-00-00-02"})
        if path.endswith("/Order/Query"):
            ma_list = data.get("Codes") or []
            if any(str(x).startswith("TIMEOUTQ") for x in ma_list):
                time.sleep(0.6)
            if any(str(x).startswith("FAILQ") for x in ma_list):
                return self._gui(handler, 500, {"Result": 2, "Message": "query failed"})
            return self._gui(handler, 200, {"Result": 1, "Message": None, "data": [
                {"merchant_order_code": str(x), "code_best": str(x),
                 "traceLogs": [{"status": "211", "modified_at": 1700000000000,
                                "cod": 15000.0}]} for x in ma_list]})
        if path.endswith("/Order/Update") or path.endswith("/Order/UpdateAddress"):
            return self._gui(handler, 200, {"Result": 1, "Message": "",
                                            "Code": str(data.get("Code") or ""),
                                            "RouteCode": "SG905",
                                            "AddressTypeId": data.get("AddressTypeId")})
        if path.endswith("/Order/Cancel"):
            return self._gui(handler, 200, {"Result": 1, "Message": ""})
        if path.endswith("/Service/EstimateFee"):
            return self._gui(handler, 200, {"Result": 1, "Message": "", "data": {
                "ServiceId": 12491, "ServiceType": "Giao hàng tiết kiệm",
                "FreightFee": 22000.0, "CODFee": 0.0, "InsuranceFee": 5500.0,
                "TotalFee": 27500.0, "TotalFeeVAT": 30250.0,
                "TotalFeeWithDiscount": 27500.0, "TotalFeeVATWithDiscount": 30250.0,
                "Cod": 15000.0, "COD": 15000.0}})
        if path.endswith("/Print/PrintWayBill"):
            ma = str((data.get("codes") or [""])[0])
            url = f"http://127.0.0.1:{self.port}/waybill/1.pdf"
            if ma == "SSRFMETA":
                url = "http://169.254.169.254/latest/meta-data/"
            elif ma == "SSRFPRIVATE":
                url = "http://10.0.0.1/x.pdf"
            elif ma == "SSRFLOCAL":
                url = f"http://localhost:{self.port}/waybill/1.pdf"
            elif ma == "SSRFHOST":
                url = "http://evil.example/x.pdf"
            elif ma == "REDIRECT":
                url = f"http://127.0.0.1:{self.port}/redirect"
            return self._gui(handler, 200, {"Result": 1, "Message": "",
                                            "Guid": "30341879-ae3d-49f1",
                                            "Url": url})
        if path.endswith("/429"):
            return self._gui(handler, 429, {"Result": 2}, headers={"Retry-After": "86400"})
        if path.endswith("/500"):
            return self._gui(handler, 500, {"Result": 2})
        if path.endswith("/400"):
            return self._gui(handler, 400, {"Result": 2})
        return self._gui(handler, 404, {"Result": 2})

    def _tra_loi_get(self, handler, path):
        if path.endswith("/waybill/1.pdf"):
            return self._gui(handler, 200, b"%PDF-1.4 MOCK-WAYBILL", "application/pdf")
        if path.endswith("/html"):
            return self._gui(handler, 200, b"<html>not a pdf</html>", "text/html")
        if path.endswith("/redirect"):
            return self._gui(handler, 302, b"", "text/plain",
                             headers={"Location": "http://169.254.169.254/latest/meta-data/"})
        return self._gui(handler, 404, b"", "text/plain")


STUB = None


def setUpModule():
    global STUB
    STUB = StubBEST()


def tearDownModule():
    if STUB is not None:
        STUB.stop()


# =================================================================================================
class Base(unittest.TestCase):
    def setUp(self):
        STUB.reset()

    def ad_mock(self, cred=None, **kw):
        return ab.AdapterBEST(dict(CRED if cred is None else cred), "mock", **kw)

    def ad_stub(self, cred=None, **kw):
        kw.setdefault("het_gio", 0.5)
        kw.setdefault("so_lan_doc", 1)
        return ab.AdapterBEST(dict(CRED if cred is None else cred), "mock",
                              base_url=STUB.base_url(), gui_http=True, **kw)

    def ad_stub_auth(self, cred=None, **kw):
        ad = self.ad_stub(cred=cred, **kw)
        kq = ad.authenticate()
        self.assertTrue(kq.ok, kq.loi)
        return ad


class CoBat:
    """Bật cờ lớp TẠM THỜI để đo cửa chặn, luôn khôi phục."""

    def __init__(self, **co):
        self.co = co
        self.cu = {}

    def __enter__(self):
        for k, v in self.co.items():
            self.cu[k] = getattr(ab.AdapterBEST, k)
            setattr(ab.AdapterBEST, k, v)
        return self

    def __exit__(self, *a):
        for k, v in self.cu.items():
            setattr(ab.AdapterBEST, k, v)
        return False


# =================================================================================================
# A. HỢP ĐỒNG
# =================================================================================================
class A_HopDong(Base):
    def test_a1_dang_ky_qua_tao_adapter(self):
        ad = adapter.tao_adapter("best", dict(CRED), "mock")
        self.assertIsInstance(ad, ab.AdapterBEST)
        cap = ad.getCapabilities()
        self.assertEqual(cap["ma_hang"], "best")
        self.assertEqual(cap["moi_truong"], "mock")
        self.assertTrue(all(cap["chuc_nang"].values()))
        self.assertEqual(cap["gioi_han"], {"queryTracking": 10, "printWaybill": 50})
        self.assertEqual(cap["service_id"], 12491)
        self.assertEqual(cap["journey_type_hop_le"], [1, 2, 3])
        self.assertTrue(cap["tai_lieu_da_xac_minh"])
        self.assertTrue(cap["schema_da_xac_minh"])
        self.assertTrue(cap["webhook_da_xac_thuc"])
        self.assertTrue(cap["bang_trang_thai_da_xac_minh"])
        self.assertEqual(cap["so_ma_trang_thai"], 23)

    def test_a2_du_muoi_chuc_nang(self):
        for ten in ("authenticate", "createOrder", "updateOrder", "updateAddress",
                    "cancelOrder", "queryTracking", "estimateFee", "printWaybill",
                    "parseWebhook", "normalizeStatus"):
            self.assertTrue(callable(getattr(ab.AdapterBEST, ten, None)), ten)
        self.assertTrue(callable(ab.AdapterBEST.normalizeTrackingStatus))
        self.assertTrue(callable(ab.AdapterBEST.getOrder))
        self.assertTrue(callable(ab.AdapterBEST.trackOrder))
        self.assertTrue(callable(ab.AdapterBEST.getShippingFee))
        self.assertTrue(callable(ab.AdapterBEST.getShippingLabel))

    def test_a3_bang_tam_endpoint(self):
        self.assertEqual(ab.DUONG_API, {
            "authenticate": "/User/Login",
            "createOrder": "/Order/Add",
            "updateOrder": "/Order/Update",
            "updateAddress": "/Order/UpdateAddress",
            "cancelOrder": "/Order/Cancel",
            "queryTracking": "/Order/Query",
            "estimateFee": "/Service/EstimateFee",
            "printWaybill": "/Print/PrintWayBill",
        })
        self.assertEqual(len(ab.DUONG_API), 8)

    def test_a4_base_url_dung_va_dung_https(self):
        self.assertEqual(ab.BASE_URL_PRODUCTION,
                         "https://sgp-seaedi.800best.com/VietNamV3/v3/api/process/sears")
        self.assertEqual(ab.BASE_URL_SANDBOX,
                         "https://sgp-seaedi-test.800best.com/VietNamV3/v3/api/process/sears")
        self.assertFalse(ab.CO_HTTP_CHUA_MA_HOA)
        self.assertFalse(hb.CO_HTTP_CHUA_MA_HOA)

    def test_a5_host_test_query_da_xac_minh_chi_dung_cho_query(self):
        self.assertEqual(ab.HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH,
                         "sea-edi-hxtest.800best.com")
        self.assertIn(ab.HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH, hb.HOST_HANG)
        self.assertTrue(hb.host_duoc_phep(ab.HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH))
        import best_hop_dong
        self.assertTrue(best_hop_dong.BASE_URL_QUERY["sandbox"].startswith(
            "https://sea-edi-hxtest.800best.com"))

    def test_a6_live_mac_dinh_dong(self):
        self.assertFalse(ab.AdapterBEST.CHO_PHEP_LIVE)
        self.assertFalse(ab.AdapterBEST.CHO_PHEP_SANDBOX)
        self.assertFalse(ab.AdapterBEST.CHO_PHEP_PRODUCTION)
        self.assertFalse(ab.AdapterBEST.CHO_PHEP_HTTP_KHONG_MA_HOA)
        self.assertTrue(ab.AdapterBEST.SCHEMA_DA_XAC_MINH)
        self.assertTrue(ab.TRANG_THAI_DA_XAC_MINH)

    def test_a7_31_truong_va_hang_so(self):
        self.assertEqual(len(ab.TRUONG_BAT_BUOC_ORDER_ADD), 31)
        self.assertEqual(len(set(ab.TRUONG_BAT_BUOC_ORDER_ADD)), 31)
        self.assertEqual(ab.DICH_VU_ID, 12491)
        self.assertNotEqual(ab.DICH_VU_ID, ab.DICH_VU_ID_CU_KHONG_DUNG)
        self.assertEqual(ab.DON_VI["Weight"], "GRAM")
        self.assertEqual(ab.DON_VI["Length"], "MILIMET")
        self.assertEqual(ab.DON_VI["Cod"], "VND")
        self.assertEqual(ab.DON_VI["ProductPrice"], "VND")


# =================================================================================================
# B. MÔI TRƯỜNG / HTTP CHƯA MÃ HOÁ
# =================================================================================================
class B_MoiTruong(Base):
    def test_b1_mock_khong_mo_socket(self):
        ad = self.ad_mock()
        with mock.patch.object(hb, "gui_json", side_effect=AssertionError("KHÔNG được gọi")):
            with mock.patch.object(hb, "tai_waybill", side_effect=AssertionError("KHÔNG được gọi")):
                self.assertTrue(ad.authenticate().ok)
                self.assertTrue(ad.createOrder(make_don()).ok)
                self.assertTrue(ad.queryTracking("X").ok)
                self.assertTrue(ad.estimateFee(make_don()).ok)
                self.assertTrue(ad.printWaybill(["X"]).ok)

    def test_b2_sandbox_mac_dinh_bi_chan(self):
        with self.assertRaises(PermissionError) as cm:
            ab.AdapterBEST(dict(CRED), "sandbox")
        self.assertIn("sandbox", str(cm.exception))

    def test_b3_production_mac_dinh_bi_chan(self):
        with self.assertRaises(PermissionError) as cm:
            ab.AdapterBEST(dict(CRED), "production")
        self.assertIn("production", str(cm.exception))

    def test_b4_http_chua_ma_hoa_bi_chan(self):
        # Mặc định đã là HTTPS; chỉ một base_url HTTP tường minh mới chạm chốt.
        with CoBat(CHO_PHEP_LIVE=True, CHO_PHEP_SANDBOX=True):
            with self.assertRaises(PermissionError) as cm:
                ab.AdapterBEST(dict(CRED), "sandbox",
                               base_url="http://sgp-seaedi-test.800best.com/VietNamV3/v3/api/process/sears")
            self.assertIn("HTTP CHƯA MÃ HOÁ", str(cm.exception))

    def test_b5_http_cho_phep_tuong_minh_va_schema_da_xac_minh(self):
        with CoBat(CHO_PHEP_LIVE=True, CHO_PHEP_SANDBOX=True,
                   CHO_PHEP_HTTP_KHONG_MA_HOA=True):
            ad = ab.AdapterBEST(dict(CRED), "sandbox", cho_phep_http_khong_ma_hoa=True,
                               base_url="http://sgp-seaedi-test.800best.com/VietNamV3/v3/api/process/sears")
            self.assertTrue(ad.base_url.startswith("http://"))
            self.assertTrue(ad.SCHEMA_DA_XAC_MINH)

    def test_b6_loopback_ngoai_mock_bi_chan(self):
        with CoBat(CHO_PHEP_LIVE=True, CHO_PHEP_SANDBOX=True,
                   CHO_PHEP_HTTP_KHONG_MA_HOA=True):
            with self.assertRaises((PermissionError, ValueError)):
                ab.AdapterBEST(dict(CRED), "sandbox", base_url="http://127.0.0.1:1/")

    def test_b7_mock_khong_duoc_tro_vao_host_hang(self):
        with self.assertRaises(PermissionError):
            ab.AdapterBEST(dict(CRED), "mock",
                           base_url="https://sgp-seaedi.800best.com/VietNamV3/v3/api/process/sears")

    def test_b8_moi_truong_la_bi_chan(self):
        with self.assertRaises(PermissionError):
            ab.AdapterBEST(dict(CRED), "staging")

    def test_b9_gui_http_ngoai_mock_bi_chan(self):
        with CoBat(CHO_PHEP_LIVE=True, CHO_PHEP_SANDBOX=True,
                   CHO_PHEP_HTTP_KHONG_MA_HOA=True):
            with self.assertRaises((PermissionError, ValueError)):
                ab.AdapterBEST(dict(CRED), "sandbox", base_url="http://127.0.0.1:1/",
                               gui_http=True)

    def test_b10_repr_khong_secret(self):
        ad = self.ad_stub_auth()
        self.assertEqual(quet_bi_mat(repr(ad)), [])
        self.assertNotIn("p-test", repr(ad))
        self.assertNotIn("u-test", repr(ad))

    def test_b11_base_url_co_query_bi_tu_choi(self):
        with self.assertRaises(ValueError):
            ab.AdapterBEST(dict(CRED), "mock",
                           base_url=f"{STUB.base_url()}?token=TOKEN-BI-MAT")

    def test_b12_thieu_credentials_dang_nhap_bi_tu_choi(self):
        # ĐỐI CHỨNG DƯƠNG: c1/c4 đăng nhập được khi CÓ username/password.
        cred = {k: v for k, v in CRED.items() if k not in ("username", "password")}
        ad = self.ad_stub(cred=cred)
        kq = ad.authenticate()
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(STUB.count("User/Login"), 0)


# =================================================================================================
# C. ĐƯỜNG ĐI 8 ENDPOINT QUA STUB
# =================================================================================================
class C_DuongDi(Base):
    def test_c1_du_8_endpoint_post(self):
        ad = self.ad_stub_auth()
        don = make_don(ma_don="T1-C1", idem_key="IDEM-C1")
        self.assertTrue(ad.createOrder(don).ok)
        self.assertTrue(ad.updateOrder(don, "BEST-T1-C1").ok)
        self.assertTrue(ad.updateAddress(don, "BEST-T1-C1").ok)
        self.assertTrue(ad.cancelOrder("BEST-T1-C1").ok)
        self.assertTrue(ad.queryTracking("BEST-T1-C1").ok)
        self.assertTrue(ad.estimateFee(don).ok)
        self.assertTrue(ad.printWaybill(["BEST-T1-C1"]).ok)
        post = [p for m, p in STUB.paths() if m == "POST"]
        self.assertEqual(set(post), {
            "/VietNamV3/v3/api/process/sears/User/Login",
            "/VietNamV3/v3/api/process/sears/Order/Add",
            "/VietNamV3/v3/api/process/sears/Order/Update",
            "/VietNamV3/v3/api/process/sears/Order/UpdateAddress",
            "/VietNamV3/v3/api/process/sears/Order/Cancel",
            "/VietNamV3/v3/api/process/sears/Order/Query",
            "/VietNamV3/v3/api/process/sears/Service/EstimateFee",
            "/VietNamV3/v3/api/process/sears/Print/PrintWayBill",
        })
        self.assertEqual(len(post), 8)
        self.assertEqual(STUB.count("waybill/1.pdf"), 1)

    def test_c2_khong_goi_800best(self):
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(ma_don="T1-C2", idem_key="IDEM-C2"))
        for r in STUB.requests:
            self.assertNotIn("800best.com", r["path"])
            self.assertTrue(r["path"].startswith("/VietNamV3/v3/api/process/sears/")
                            or r["path"].startswith("/waybill/")
                            or r["path"].startswith("/redirect")
                            or r["path"].startswith("/html"), r["path"])

    def test_c3_than_yeu_cau_la_json(self):
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(ma_don="T1-C3", idem_key="IDEM-C3"))
        body = STUB.bodies("Order/Add")[0]
        self.assertIsInstance(body, dict)
        h = {k.lower(): v for k, v in STUB.headers_for("Order/Add")[0].items()}
        self.assertIn("application/json", h.get("content-type", ""))

    def test_c4_token_khong_duoc_tra_ra(self):
        ad = self.ad_stub_auth()
        kq = ad.authenticate()
        self.assertTrue(kq.ok)
        self.assertTrue(kq.tho["co_token"])
        self.assertNotIn("MOCK-TOKEN-KHONG-THAT", json.dumps(kq.tho, default=str))
        self.assertTrue(ad.queryTracking("BEST-X").ok)
        h = STUB.headers_for("Order/Query")[-1]
        self.assertEqual(h.get("Authorization"), "Bearer MOCK-TOKEN-KHONG-THAT")
        self.assertNotIn("MOCK-TOKEN-KHONG-THAT", json.dumps(ad.queryTracking("BEST-X").tho,
                                                             default=str))

    def test_c5_ket_qua_khong_chua_secret(self):
        ad = self.ad_stub_auth()
        don = make_don(ma_don="T1-C5", idem_key="IDEM-C5")
        ds = [ad.createOrder(don), ad.queryTracking("BEST-X"), ad.estimateFee(don),
              ad.printWaybill(["BEST-X"]), ad.cancelOrder("BEST-X")]
        for kq in ds:
            self.assertEqual(quet_bi_mat({"loi": kq.loi, "tho": kq.tho}), [])

    def test_c6_ma_van_don_tu_goi_tra_loi(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(ma_don="T1-C6", idem_key="IDEM-C6"))
        self.assertTrue(kq.ok)
        self.assertEqual(kq.ma_van_don, "BEST-T1-C6")


# =================================================================================================
# D. 21 TRƯỜNG ORDER/ADD
# =================================================================================================
class D_31Truong(Base):
    def _tao_va_lay_than(self, **kw):
        ad = self.ad_stub_auth()
        don = make_don(ma_don=kw.pop("ma_don", "T1-D"), idem_key=kw.pop("idem_key", "IDEM-D"), **kw)
        kq = ad.createOrder(don)
        self.assertTrue(kq.ok, kq.loi)
        return STUB.bodies("Order/Add")[-1]

    def test_d1_du_31_truong(self):
        body = self._tao_va_lay_than()
        self.assertEqual(len(ab.TRUONG_BAT_BUOC_ORDER_ADD), 31)
        for ten in ab.TRUONG_BAT_BUOC_ORDER_ADD:
            self.assertIn(ten, body)
        self.assertTrue(set(ab.TRUONG_BAT_BUOC_ORDER_ADD).issubset(body))
        self.assertEqual(len(set(body) & set(ab.TRUONG_BAT_BUOC_ORDER_ADD)), 31)
        # Metadata chống trùng là NỘI BỘ — tài liệu hãng không có các trường này.
        for ten in ab.TRUONG_META_CHONG_TRUNG:
            self.assertNotIn(ten, body)

    def test_d2_service_id_12491(self):
        body = self._tao_va_lay_than()
        self.assertEqual(body["ServiceId"], 12491)
        self.assertNotEqual(body["ServiceId"], 12490)

    def test_d3_service_id_12490_bi_tu_choi(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(service_id=12490, ma_don="T1-D3", idem_key="IDEM-D3"))
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_d4_journey_type_1_2_3(self):
        ad = self.ad_stub_auth()
        for i, jt in enumerate((1, 2, 3)):
            kq = ad.createOrder(make_don(journey_type=jt, ma_don=f"T1-D4-{i}",
                                         idem_key=f"IDEM-D4-{i}"))
            self.assertTrue(kq.ok, kq.loi)
            self.assertEqual(STUB.bodies("Order/Add")[-1]["JourneyType"], jt)
        self.assertEqual(STUB.count("Order/Add"), 3)
        for jt in (0, 4, "abc"):
            kq = ad.createOrder(make_don(journey_type=jt, ma_don=f"T1-D4-X{jt}",
                                         idem_key=f"IDEM-D4-X{jt}"))
            self.assertFalse(kq.ok, jt)
        kq = ad.createOrder(make_don(journey_type=XOA, ma_don="T1-D4-NONE",
                                     idem_key="IDEM-D4-NONE"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 3)

    def test_d5_weight_gram(self):
        body = self._tao_va_lay_than(ma_don="T1-D5", idem_key="IDEM-D5")
        self.assertEqual(body["Weight"], 1500)
        ad = self.ad_stub_auth()
        for kl, nhan in ((1500.5, "float"), (0, "zero"), (-1, "am")):
            kq = ad.createOrder(make_don(khoi_luong_gram=kl, ma_don=f"T1-D5-{nhan}",
                                         idem_key=f"IDEM-D5-{nhan}"))
            self.assertFalse(kq.ok, nhan)
        self.assertEqual(STUB.count("Order/Add"), 1)

    def test_d6_kich_thuoc_milimet(self):
        body = self._tao_va_lay_than(ma_don="T1-D6", idem_key="IDEM-D6")
        self.assertEqual((body["Length"], body["Width"], body["Height"]), (200, 100, 50))
        ad = self.ad_stub_auth()
        # Tài liệu KHÔNG đánh dấu kích thước là bắt buộc: 0/None hợp lệ.
        for i, truong in enumerate(("chieu_dai_mm", "chieu_rong_mm", "chieu_cao_mm")):
            kq = ad.createOrder(make_don(**{truong: 0},
                                         ma_don=f"T1-D6-Z{i}", idem_key=f"IDEM-D6-Z{i}"))
            self.assertTrue(kq.ok, (truong, kq.loi))
            self.assertEqual(STUB.bodies("Order/Add")[-1][
                {"chieu_dai_mm": "Length", "chieu_rong_mm": "Width",
                 "chieu_cao_mm": "Height"}[truong]], 0)
        for truong in ("chieu_dai_mm", "chieu_rong_mm", "chieu_cao_mm"):
            for gia_tri in (10.5, -1):
                kq = ad.createOrder(make_don(**{truong: gia_tri},
                                             ma_don=f"T1-D6-X-{truong}-{gia_tri}",
                                             idem_key=f"IDEM-D6-X-{truong}-{gia_tri}"))
                self.assertFalse(kq.ok, (truong, gia_tri))

    def test_d7_cod_va_product_price_vnd(self):
        body = self._tao_va_lay_than(ma_don="T1-D7", idem_key="IDEM-D7")
        self.assertEqual(body["CollectAmount"], 15000)
        self.assertEqual(body["ProductPrice"], 200000)
        ad = self.ad_stub_auth()
        # Tài liệu khai `decimal`: 1.5 hợp lệ và phải giữ nguyên, không làm tròn.
        for i, truong in enumerate(("cod", "gia_tri_khai")):
            kq = ad.createOrder(make_don(**{truong: 1.5},
                                         ma_don=f"T1-D7-DEC{i}", idem_key=f"IDEM-D7-DEC{i}"))
            self.assertTrue(kq.ok, (truong, kq.loi))
            khoa = "CollectAmount" if truong == "cod" else "ProductPrice"
            self.assertEqual(STUB.bodies("Order/Add")[-1][khoa], 1.5)
        for truong in ("cod", "gia_tri_khai"):
            for gia_tri in (-1, True):
                kq = ad.createOrder(make_don(**{truong: gia_tri},
                                             ma_don=f"T1-D7-X-{truong}-{gia_tri}",
                                             idem_key=f"IDEM-D7-X-{truong}-{gia_tri}"))
                self.assertFalse(kq.ok, (truong, gia_tri))

    def test_d8_thieu_truong_bat_buoc_bi_tu_choi(self):
        ad = self.ad_stub_auth()
        # Tài liệu đánh dấu `*`: người gửi/nhận, địa chỉ, hàng hoá, cân nặng, JourneyType,
        # Code. Kích thước KHÔNG bắt buộc nên không nằm trong danh sách này.
        truong_bat_buoc = ("nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi",
                           "nguoi_gui_tinh", "nguoi_gui_xa", "nguoi_nhan_ten",
                           "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "nguoi_nhan_tinh",
                           "nguoi_nhan_xa", "hang_hoa", "khoi_luong_gram",
                           "journey_type", "ma_don")
        for i, truong in enumerate(truong_bat_buoc):
            kw = {truong: XOA, "idem_key": f"IDEM-D8-{i}"}
            if truong != "ma_don":
                kw["ma_don"] = f"T1-D8-{i}"
            kq = ad.createOrder(make_don(**kw))
            self.assertFalse(kq.ok, truong)
            self.assertFalse(kq.timeout, truong)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_d9_khong_gui_khi_thieu_truong(self):
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(hang_hoa="", ma_don="T1-D9", idem_key="IDEM-D9"))
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_d10_meta_chong_trung_khong_gui_trong_body(self):
        body = self._tao_va_lay_than(ma_don="T1-D10", idem_key="IDEM-D10")
        self.assertEqual(body["Code"], "T1-D10")
        for ten in ab.TRUONG_META_CHONG_TRUNG:
            self.assertNotIn(ten, body)


# =================================================================================================
# E. ĐỊA CHỈ 2 CẤP
# =================================================================================================
class E_DiaChi(Base):
    def test_e1_district_thieu_thanh_mot_khoang_trang(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(nguoi_gui_quan="", nguoi_nhan_quan=None,
                                     ma_don="T1-E1", idem_key="IDEM-E1"))
        self.assertTrue(kq.ok, kq.loi)
        body = STUB.bodies("Order/Add")[-1]
        self.assertEqual(body["SourceDistrict"], " ")
        self.assertEqual(body["DestDistrict"], " ")
        self.assertIsInstance(body["DestDistrict"], str)
        self.assertNotEqual(body["DestDistrict"], "")

    def test_e2_district_toan_khoang_trang(self):
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(nguoi_nhan_quan="   ", ma_don="T1-E2", idem_key="IDEM-E2"))
        self.assertEqual(STUB.bodies("Order/Add")[-1]["DestDistrict"], " ")

    def test_e3_update_address_cung_ap_dung(self):
        ad = self.ad_stub_auth()
        don = make_don(nguoi_nhan_quan=None, ma_don="T1-E3", idem_key="IDEM-E3")
        self.assertTrue(ad.updateAddress(don, "BEST-T1-E3").ok)
        body = STUB.bodies("Order/UpdateAddress")[-1]
        self.assertEqual(body["DistrictName"], " ")
        self.assertIsInstance(body["DistrictName"], str)

    def test_e4_khong_hardcode_danh_sach_dia_gioi(self):
        d = ab.BestAddressAdapter().chuan_hoa(
            "Tỉnh Không Có Thật 999", "Quận Không Có Thật 888", "Địa chỉ lạ 777")
        self.assertEqual(d["Province"], "Tỉnh Không Có Thật 999")
        self.assertEqual(d["District"], "Quận Không Có Thật 888")
        self.assertEqual(d["Address"], "Địa chỉ lạ 777")

    def test_e5_xa_duoc_giu_trong_dia_chi(self):
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(nguoi_nhan_xa="Phường 9", ma_don="T1-E5", idem_key="IDEM-E5"))
        body = STUB.bodies("Order/Add")[-1]
        self.assertTrue(body["DestAddress"].endswith(", Phường 9"), body["DestAddress"])

    def test_e6_thieu_tinh_bi_tu_choi(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(nguoi_nhan_tinh=XOA, ma_don="T1-E6", idem_key="IDEM-E6"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_e7_tra_cuu_dia_gioi_inject(self):
        d = ab.BestAddressAdapter(tra_cuu_dia_gioi=lambda t, q: False)
        with self.assertRaises(ValueError):
            d.chuan_hoa("Tỉnh A", "Quận B", "Địa chỉ C")

    def test_e8_lop_dia_chi_khong_chua_bang_dia_gioi(self):
        for k, v in vars(ab.BestAddressAdapter).items():
            if isinstance(v, (list, tuple, set, frozenset)):
                self.assertLessEqual(len(v), 3, f"{k} giống bảng địa giới hardcode")

    def test_e9_district_co_gia_tri_duoc_giu_nguyen(self):
        # ĐỐI CHỨNG DƯƠNG của e1/e2: không phải lúc nào cũng ghi " ".
        ad = self.ad_stub_auth()
        ad.createOrder(make_don(nguoi_gui_quan="Quận Gửi", nguoi_nhan_quan="Quận Nhận",
                                ma_don="T1-E9", idem_key="IDEM-E9"))
        body = STUB.bodies("Order/Add")[-1]
        self.assertEqual(body["SourceDistrict"], "Quận Gửi")
        self.assertEqual(body["DestDistrict"], "Quận Nhận")


# =================================================================================================
# F. GIỚI HẠN 10 / 50
# =================================================================================================
class F_GioiHan(Base):
    def test_f1_query_10_ma_ok(self):
        ad = self.ad_stub_auth()
        ds = [f"W{i}" for i in range(10)]
        kq = ad.queryTracking(ds)
        self.assertTrue(kq.ok, kq.loi)
        self.assertEqual(kq.tho["so_ma"], 10)
        self.assertEqual(len(kq.tho["ket_qua"]), 10)
        self.assertEqual(STUB.count("Order/Query"), 1)

    def test_f2_query_11_ma_bi_tu_choi_truoc_khi_gui(self):
        ad = self.ad_stub_auth()
        kq = ad.queryTracking([f"W{i}" for i in range(11)])
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertIn("10", kq.loi)
        self.assertEqual(STUB.count("Order/Query"), 0)

    def test_f3_query_rong_bi_tu_choi(self):
        ad = self.ad_stub_auth()
        self.assertFalse(ad.queryTracking([]).ok)
        self.assertEqual(STUB.count("Order/Query"), 0)

    def test_f4_query_trung_ma_bi_tu_choi(self):
        ad = self.ad_stub_auth()
        self.assertFalse(ad.queryTracking(["W1", "W1"]).ok)
        self.assertEqual(STUB.count("Order/Query"), 0)

    def test_f5_print_50_ma_ok(self):
        ad = self.ad_stub_auth()
        ds = [f"P{i}" for i in range(50)]
        kq = ad.printWaybill(ds)
        self.assertTrue(kq.ok, kq.loi)
        self.assertEqual(kq.tho["so_ma"], 50)
        self.assertEqual(kq.tho["so_tep"], 1)
        self.assertGreater(kq.tho["tong_byte"], 0)
        self.assertEqual(STUB.count("Print/PrintWayBill"), 1)

    def test_f6_print_51_ma_bi_tu_choi_truoc_khi_gui(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill([f"P{i}" for i in range(51)])
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertIn("50", kq.loi)
        self.assertEqual(STUB.count("Print/PrintWayBill"), 0)

    def test_f7_khong_cat_bot_im_lang(self):
        ad = self.ad_stub_auth()
        self.assertFalse(ad.queryTracking([f"W{i}" for i in range(11)]).ok)
        self.assertFalse(ad.printWaybill([f"P{i}" for i in range(51)]).ok)
        self.assertEqual(STUB.count("Order/Query"), 0)
        self.assertEqual(STUB.count("Print/PrintWayBill"), 0)

    def test_f8_bidanh_getorder_trackorder(self):
        ad = self.ad_stub_auth()
        self.assertTrue(ad.getOrder("W1").ok)
        self.assertTrue(ad.trackOrder("W2").ok)
        self.assertEqual(STUB.count("Order/Query"), 2)


# =================================================================================================
# G. SSRF
# =================================================================================================
class G_SSRF(Base):
    def test_g1_loopback_mac_dinh_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill(f"http://127.0.0.1:{STUB.port}/waybill/1.pdf", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "host-cuc-bo")
        self.assertEqual(STUB.count("waybill/1.pdf"), 0)

    def test_g2_private_ip_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill("http://10.0.0.1/x.pdf", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "ssrf-ip-noi-bo")

    def test_g3_metadata_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill("http://169.254.169.254/latest/meta-data/", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "ssrf-metadata")

    def test_g4_host_la_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill("http://evil.example/x.pdf", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "host-bi-tu-choi")

    def test_g5_userinfo_trong_url_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill("http://user:pass@sgp-seaedi.800best.com/x.pdf", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "url-sai")

    def test_g6_scheme_la_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill("ftp://sgp-seaedi.800best.com/x.pdf", timeout=0.5)
        self.assertEqual(getattr(cm.exception, "ma", None), "url-sai")

    def test_g7_http_host_hang_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tach_url("http://sgp-seaedi.800best.com/x")
        self.assertEqual(getattr(cm.exception, "ma", None), "http-khong-ma-hoa")
        self.assertEqual(hb.tach_url("http://sgp-seaedi.800best.com/x",
                                     cho_phep_http_khong_ma_hoa=True)[1],
                         "sgp-seaedi.800best.com")

    def test_g8_redirect_khong_di_theo(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill(f"http://127.0.0.1:{STUB.port}/redirect", timeout=0.5,
                           cho_phep_loopback=True)
        self.assertEqual(getattr(cm.exception, "ma", None), "chuyen-huong")
        self.assertEqual(STUB.count("latest/meta-data"), 0)

    def test_g9_content_type_khong_phai_pdf_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tai_waybill(f"http://127.0.0.1:{STUB.port}/html", timeout=0.5,
                           cho_phep_loopback=True)
        self.assertEqual(getattr(cm.exception, "ma", None), "waybill-khong-phai-pdf")

    def test_g10_tai_pdf_hop_le_tu_stub(self):
        pdf = hb.tai_waybill(f"http://127.0.0.1:{STUB.port}/waybill/1.pdf", timeout=0.5,
                             cho_phep_loopback=True)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_g11_print_ssrf_metadata_bi_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["SSRFMETA"])
        self.assertFalse(kq.ok)
        self.assertTrue(kq.timeout)
        self.assertTrue(kq.tho["in_da_gui"])
        self.assertTrue(kq.tho["tai_pdf_that_bai"])
        self.assertEqual(kq.tho["ly_do_tai"], "ssrf-metadata")
        self.assertEqual(STUB.count("latest/meta-data"), 0)

    def test_g12_print_ssrf_private_bi_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["SSRFPRIVATE"])
        self.assertTrue(kq.tho["tai_pdf_that_bai"])
        self.assertEqual(kq.tho["ly_do_tai"], "ssrf-ip-noi-bo")

    def test_g13_print_ssrf_localhost_khac_stub_bi_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["SSRFLOCAL"])
        self.assertTrue(kq.tho["tai_pdf_that_bai"])
        self.assertEqual(kq.tho["ly_do_tai"], "host-cuc-bo")
        self.assertEqual(STUB.count("waybill/1.pdf"), 0)

    def test_g14_print_ssrf_host_la_bi_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["SSRFHOST"])
        self.assertEqual(kq.tho["ly_do_tai"], "host-bi-tu-choi")

    def test_g15_print_redirect_bi_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["REDIRECT"])
        self.assertTrue(kq.tho["tai_pdf_that_bai"])
        self.assertEqual(kq.tho["ly_do_tai"], "chuyen-huong")
        self.assertEqual(STUB.count("latest/meta-data"), 0)

    def test_g16_print_hop_le_tai_pdf(self):
        ad = self.ad_stub_auth()
        kq = ad.printWaybill(["OK"])
        self.assertTrue(kq.ok, kq.loi)
        self.assertTrue(kq.tho["pdf"].startswith(b"%PDF"))
        self.assertGreater(kq.tho["tong_byte"], 0)

    def test_g17_ip_obfuscation_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.tai_waybill("http://2130706433/x.pdf", timeout=0.5)
        self.assertEqual(STUB.count("x.pdf"), 0)

    def test_g18_host_gia_mao_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.tach_url("http://sgp-seaedi.800best.com.evil/x")
        self.assertFalse(hb.host_duoc_phep("sgp-seaedi.800best.com.evil"))


# =================================================================================================
# H. CHỐNG TRÙNG + TIMEOUT
# =================================================================================================
class H_ChongTrungTimeout(Base):
    def test_h1_phat_lai_khong_gui_lan_hai(self):
        ad = self.ad_stub_auth()
        don = make_don(ma_don="T1-H1", idem_key="IDEM-H1")
        kq1 = ad.createOrder(don)
        kq2 = ad.createOrder(don)
        self.assertTrue(kq1.ok)
        self.assertTrue(kq2.ok)
        self.assertEqual(kq1.ma_van_don, kq2.ma_van_don)
        self.assertTrue(kq2.tho.get("phat_lai_idempotent"))
        self.assertEqual(STUB.count("Order/Add"), 1)

    def test_h2_tenant_khac_bi_deny(self):
        ad = self.ad_stub_auth()
        self.assertTrue(ad.createOrder(make_don(ma_don="T1-H2", idem_key="IDEM-H2")).ok)
        kq = ad.createOrder(make_don(tenant_id="2", ma_don="T1-H2B", idem_key="IDEM-H2B"))
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(STUB.count("Order/Add"), 1)

    def test_h3_thieu_tenant_bi_deny(self):
        cred = {k: v for k, v in CRED.items() if k != "tenant_id"}
        ad = self.ad_stub(cred=cred)
        kq = ad.createOrder(make_don(tenant_id=XOA, ma_don="T1-H3", idem_key="IDEM-H3"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 0)
        self.assertFalse(ad.queryTracking("X").ok)

    def test_h4_thieu_carrier_bi_deny(self):
        cred = {k: v for k, v in CRED.items() if k not in ("carrier_id", "carrier_account_id")}
        ad = self.ad_stub(cred=cred)
        kq = ad.createOrder(make_don(carrier_account_id=XOA, ma_don="T1-H4",
                                     idem_key="IDEM-H4"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_h5_thieu_idempotency_bi_deny(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(idem_key=XOA, ma_don="T1-H5"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_h6_thieu_ma_don_bi_deny(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(ma_don=XOA, idem_key="IDEM-H6"))
        self.assertFalse(kq.ok)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_h7_timeout_khong_retry_mu_va_kiem_tra_lai(self):
        ad = self.ad_stub_auth(het_gio=0.2, so_lan_doc=1)
        kq = ad.createOrder(make_don(ma_don="TIMEOUT-OK", idem_key="IDEM-H7"))
        self.assertTrue(kq.ok, kq.loi)
        self.assertTrue(kq.tho.get("da_kiem_tra_sau_timeout"))
        self.assertEqual(kq.tho.get("ket_qua_sau_timeout"), "da_vao")
        self.assertEqual(STUB.count("Order/Add"), 1)       # KHÔNG thử lại mù
        self.assertEqual(STUB.count("Order/Query"), 1)     # kiểm tra trạng thái trước

    def test_h8_timeout_ca_tra_cuu_la_unknown(self):
        ad = self.ad_stub_auth(het_gio=0.2, so_lan_doc=1)
        kq = ad.createOrder(make_don(ma_don="TIMEOUTQ-1", idem_key="IDEM-H8"))
        self.assertFalse(kq.ok)
        self.assertTrue(kq.timeout)
        self.assertTrue(kq.tho.get("can_doi_soat"))
        self.assertIn("KHÔNG BIẾT", kq.loi)
        self.assertEqual(STUB.count("Order/Add"), 1)
        self.assertEqual(STUB.count("Order/Query"), 1)

    def test_h9_khong_bao_that_bai_chi_vi_timeout(self):
        ad = self.ad_stub_auth(het_gio=0.2, so_lan_doc=1)
        kq = ad.createOrder(make_don(ma_don="TIMEOUTQ-2", idem_key="IDEM-H9"))
        self.assertTrue(kq.timeout)
        self.assertFalse(kq.ok)
        self.assertNotIn("từ chối", kq.loi.lower())

    def test_h10_http_500_la_timeout_roi_kiem_tra_lai(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(ma_don="FAIL500", idem_key="IDEM-H10"))
        self.assertTrue(kq.ok, kq.loi)
        self.assertTrue(kq.tho.get("da_kiem_tra_sau_timeout"))
        self.assertEqual(STUB.count("Order/Add"), 1)
        self.assertEqual(STUB.count("Order/Query"), 1)

    def test_h11_http_400_la_tu_choi_chac_chan(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(ma_don="FAIL400", idem_key="IDEM-H11"))
        self.assertFalse(kq.ok)
        self.assertFalse(kq.timeout)
        self.assertEqual(STUB.count("Order/Add"), 1)
        self.assertEqual(STUB.count("Order/Query"), 0)

    def test_h12_query_timeout_la_unknown(self):
        ad = self.ad_stub_auth(het_gio=0.2, so_lan_doc=1)
        kq = ad.queryTracking("TIMEOUTQ-3")
        self.assertFalse(kq.ok)
        self.assertTrue(kq.timeout)
        self.assertTrue(kq.tho.get("can_doi_soat"))


# =================================================================================================
# I. BÍ MẬT
# =================================================================================================
class I_BiMat(Base):
    def test_i1_ket_qua_khong_chua_secret(self):
        ad = self.ad_stub_auth()
        don = make_don(ma_don="T1-I1", idem_key="IDEM-I1")
        for kq in (ad.authenticate(), ad.createOrder(don), ad.queryTracking("X"),
                   ad.estimateFee(don), ad.printWaybill(["X"]), ad.cancelOrder("X"),
                   ad.updateAddress(don, "X"), ad.updateOrder(don, "X")):
            self.assertEqual(quet_bi_mat({"loi": kq.loi, "tho": kq.tho}), [])

    def test_i2_repr_khong_secret(self):
        ad = self.ad_stub_auth()
        self.assertEqual(quet_bi_mat(repr(ad)), [])

    def test_i3_loi_khong_echo_message_cua_hang(self):
        ad = self.ad_stub_auth()
        kq = ad.createOrder(make_don(ma_don="ECHOSECRET", idem_key="IDEM-I3"))
        self.assertFalse(kq.ok)
        self.assertNotIn("p-test", json.dumps({"loi": kq.loi, "tho": kq.tho},
                                              ensure_ascii=False, default=str))

    def test_i4_token_khong_ra_khoi_bo_nho(self):
        ad = self.ad_stub_auth()
        for kq in (ad.authenticate(), ad.createOrder(make_don(ma_don="T1-I4",
                                                              idem_key="IDEM-I4"))):
            self.assertNotIn("MOCK-TOKEN-KHONG-THAT",
                             json.dumps({"loi": kq.loi, "tho": kq.tho}, default=str))
        self.assertEqual(ad._token, "MOCK-TOKEN-KHONG-THAT")

    def test_i5_module_khong_chua_secret(self):
        for mod in (ab, hb):
            for k, v in vars(mod).items():
                self.assertNotIn("p-test", repr(v), k)
                self.assertNotIn("u-test", repr(v), k)

    def test_i6_url_co_token_khong_bi_echo(self):
        with self.assertRaises(tp.LoiVinhVien) as cm:
            hb.tach_url("http://127.0.0.1:1/x?token=TOKEN-BI-MAT")
        self.assertNotIn("TOKEN-BI-MAT", str(cm.exception))


# =================================================================================================
# J. WEBHOOK / TRẠNG THÁI
# =================================================================================================
class J_Webhook(Base):
    @staticmethod
    def _wh(**thua):
        d = {"code_best": "W1", "merchant_order_code": "M1", "status": "211",
             "modified_at": 1700000000000}
        d.update(thua)
        return d

    def test_j1_parse_hop_le_nhung_chua_xac_thuc(self):
        ad = self.ad_mock()
        kq = ad.parseWebhook(self._wh(status="99"))
        self.assertTrue(kq["ok"])
        self.assertFalse(kq["da_xac_thuc"])
        self.assertIsNone(kq["trang_thai_chuan"])
        self.assertTrue(kq["can_soat"])
        self.assertEqual(kq["tenant_id"], "1")

    def test_j2_parse_bytes(self):
        ad = self.ad_mock()
        kq = ad.parseWebhook(json.dumps(self._wh(status=211)).encode())
        self.assertTrue(kq["ok"])
        self.assertEqual(kq["trang_thai_chuan"], "cho_lay")

    def test_j3_parse_khong_phai_json(self):
        ad = self.ad_mock()
        self.assertFalse(ad.parseWebhook(b"<html>")["ok"])

    def test_j4_parse_thieu_ma_van_don(self):
        ad = self.ad_mock()
        self.assertFalse(ad.parseWebhook(self._wh(code_best=""))["ok"])

    def test_j5_parse_thieu_trang_thai(self):
        ad = self.ad_mock()
        self.assertFalse(ad.parseWebhook({"code_best": "W1",
                                          "merchant_order_code": "M1"})["ok"])

    def test_j6_parse_qua_lon(self):
        ad = self.ad_mock()
        self.assertFalse(ad.parseWebhook(b"x" * (1024 * 1024 + 1))["ok"])

    def test_j7_xac_thuc_callable(self):
        ad = self.ad_mock()
        self.assertTrue(ad.parseWebhook(self._wh(), xac_thuc=lambda g: True)["da_xac_thuc"])
        self.assertFalse(ad.parseWebhook(self._wh(), xac_thuc=lambda g: False)["da_xac_thuc"])

    def test_j8_normalize_khong_doan(self):
        for ma in (0, 1, 99, "DELIVERED", "giao_thanh_cong", None):
            r = ab.AdapterBEST.normalizeStatus(ma)
            self.assertFalse(r.biet_ma, ma)
            self.assertIsNone(r.trang_thai_ap, ma)
            self.assertTrue(r.can_soat, ma)
            self.assertEqual(r.do_tin_cay, tth.TIN_MA_LA)

    def test_j9_ma_tai_lieu_va_customer_cancel(self):
        self.assertEqual(ab.AdapterBEST.normalizeStatus("666").trang_thai_ap,
                         "giao_thanh_cong")
        self.assertEqual(ab.AdapterBEST.normalizeStatus("606").trang_thai_ap, "dang_giao")
        r = ab.AdapterBEST.normalizeStatus("customer Cancel")
        self.assertTrue(r.biet_ma)
        self.assertEqual(r.trang_thai_ap, "da_huy")
        for ma in (99, "DELIVERED"):
            self.assertNotIn(ab.AdapterBEST.normalizeStatus(ma).trang_thai_ap,
                             tth.TRANG_THAI_HOAN_TAT)

    def test_j10_webhook_khong_echo_payload(self):
        ad = self.ad_mock()
        kq = ad.parseWebhook(self._wh(Password="p-test", Token="TOKEN-BI-MAT"))
        self.assertTrue(kq["ok"])
        self.assertEqual(quet_bi_mat(kq), [])

    def test_j11_webhook_tenant_khac_bi_deny(self):
        ad = self.ad_mock()
        kq = ad.parseWebhook(self._wh(), tenant_id="2")
        self.assertFalse(kq["ok"])


# =================================================================================================
# K. LỚP HTTP RIÊNG
# =================================================================================================
class K_HTTP(Base):
    def test_k1_gui_json_dung_json(self):
        tra_loi = hb.gui_json(f"{STUB.base_url()}/Order/Add", {"X-Request-Id": "r1"},
                              {"A": 1}, timeout=0.5, cho_phep_loopback=True)
        self.assertEqual(tra_loi.ma_http, 200)
        self.assertEqual(STUB.bodies("Order/Add")[-1], {"A": 1})
        h = {k.lower(): v for k, v in STUB.headers_for("Order/Add")[-1].items()}
        self.assertIn("application/json", h.get("content-type", ""))

    def test_k2_http_500_la_tam_thoi(self):
        with self.assertRaises(tp.LoiTamThoi) as cm:
            hb.gui_json(f"{STUB.base_url()}/500", {}, {}, timeout=0.5,
                        cho_phep_loopback=True)
        self.assertTrue(cm.exception.timeout)
        self.assertEqual(cm.exception.ma_http, 500)

    def test_k3_http_400_la_vinh_vien(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.gui_json(f"{STUB.base_url()}/400", {}, {}, timeout=0.5,
                        cho_phep_loopback=True)

    def test_k4_retry_after_bi_kep_tran(self):
        with self.assertRaises(tp.LoiTamThoi) as cm:
            hb.gui_json(f"{STUB.base_url()}/429", {}, {}, timeout=0.5,
                        cho_phep_loopback=True)
        self.assertEqual(cm.exception.cho_giay, tp.CHO_TOI_DA)

    def test_k5_http_khong_tu_ngu(self):
        # `gui_json` CẤM ngủ. Nếu nó ngủ theo Retry-After 86400, ca này treo tới hết giờ.
        t0 = time.monotonic()
        with self.assertRaises(tp.LoiTamThoi):
            hb.gui_json(f"{STUB.base_url()}/429", {}, {}, timeout=0.5,
                        cho_phep_loopback=True)
        self.assertLess(time.monotonic() - t0, 2.0)

    def test_k6_http_chua_ma_hoa(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.tach_url("http://sgp-seaedi.800best.com/x")
        self.assertEqual(hb.tach_url("http://sgp-seaedi.800best.com/x",
                                     cho_phep_http_khong_ma_hoa=True)[1],
                         "sgp-seaedi.800best.com")

    def test_k7_https_sai_cong_bi_chan(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.tach_url("https://sgp-seaedi.800best.com:8443/x")
        # ĐỐI CHỨNG DƯƠNG: https đúng cổng 443 được nhận (không mở kết nối ở đây).
        self.assertEqual(hb.tach_url("https://sgp-seaedi.800best.com/x")[0], "https")
        self.assertEqual(hb.tach_url("https://sgp-seaedi.800best.com/x")[1],
                         "sgp-seaedi.800best.com")

    def test_k7b_cong_ngoai_khoang_bi_tu_choi(self):
        for url in (f"http://127.0.0.1:0/x", f"http://127.0.0.1:65536/x"):
            with self.assertRaises(tp.LoiVinhVien):
                hb.tach_url(url, cho_phep_loopback=True)
        self.assertEqual(STUB.count("x"), 0)

    def test_k8_khong_ha_tls(self):
        ma = ma_khong_comment(os.path.join(GOC_APP, "http_best.py"))
        for cam in ("verify=False", "_create_unverified_context", "CERT_NONE",
                    "check_hostname = False", "time.sleep", "import time"):
            self.assertNotIn(cam, ma, cam)

    def test_k9_timeout_sai_bi_tu_choi(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.gui_json(f"{STUB.base_url()}/Order/Add", {}, {}, timeout=0,
                        cho_phep_loopback=True)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_k10_header_injection_bi_tu_choi(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.gui_json(f"{STUB.base_url()}/Order/Add", {"X": "a\r\nB"}, {},
                        timeout=0.5, cho_phep_loopback=True)
        self.assertEqual(STUB.count("Order/Add"), 0)

    def test_k11_payload_nan_bi_tu_choi(self):
        with self.assertRaises(tp.LoiVinhVien):
            hb.gui_json(f"{STUB.base_url()}/Order/Add", {}, {"x": float("nan")},
                        timeout=0.5, cho_phep_loopback=True)
        self.assertEqual(STUB.count("Order/Add"), 0)


# =================================================================================================
# L. CHỐT CHẶN TĨNH
# =================================================================================================
class L_ChotChan(Base):
    def test_l1_host_allowlist_chinh_xac(self):
        self.assertTrue(hb.host_duoc_phep("sgp-seaedi.800best.com"))
        self.assertTrue(hb.host_duoc_phep("sgp-seaedi-test.800best.com"))
        self.assertTrue(hb.host_duoc_phep("127.0.0.1"))
        self.assertTrue(hb.host_duoc_phep("localhost"))
        self.assertFalse(hb.host_duoc_phep("sgp-seaedi.800best.com.evil"))
        self.assertFalse(hb.host_duoc_phep("800best.com"))
        self.assertFalse(hb.host_duoc_phep("169.254.169.254"))

    def test_l2_base_url_dung_https(self):
        for mt in (hb.SANDBOX, hb.PRODUCTION):
            self.assertTrue(hb.BASE_URL[mt].startswith("https://"))
            self.assertFalse(hb.BASE_URL[mt].startswith("http://"))

    def test_l3_default_mock_khong_goi_http(self):
        ad = self.ad_mock()
        with mock.patch.object(hb, "gui_json", side_effect=AssertionError("KHÔNG gọi")):
            with mock.patch.object(hb, "tai_waybill", side_effect=AssertionError("KHÔNG gọi")):
                ad.authenticate()
                ad.createOrder(make_don())
                ad.queryTracking("X")
                ad.estimateFee(make_don())
                ad.printWaybill(["X"])

    def test_l4_mock_print_khong_tai_pdf(self):
        ad = self.ad_mock()
        kq = ad.printWaybill(["X"])
        self.assertTrue(kq.ok)
        self.assertNotIn("pdf", kq.tho)
        self.assertEqual(kq.tho["label"], "MOCK-PDF")
        self.assertIn("MOCK", kq.tho["ghi_chu"])

    def test_l5_adapter_khong_tu_goi_800best(self):
        # Mọi base_url mặc định của sandbox/production là host hãng, nhưng adapter chỉ dùng
        # chúng sau khi qua cửa; ở mock base_url là None. Không có nhánh nào tự gọi host hãng.
        ad = self.ad_mock()
        self.assertIsNone(ad.base_url)
        with mock.patch.object(hb, "gui_json", side_effect=AssertionError("KHÔNG gọi")):
            self.assertTrue(ad.createOrder(make_don()).ok)

    def test_l6_mock_khong_phan_giai_dns(self):
        ad = self.ad_mock()
        with mock.patch("socket.getaddrinfo", side_effect=AssertionError("KHÔNG DNS")):
            self.assertTrue(ad.authenticate().ok)
            self.assertTrue(ad.createOrder(make_don(ma_don="T1-L6",
                                                    idem_key="IDEM-L6")).ok)
            self.assertTrue(ad.queryTracking("X").ok)
            self.assertTrue(ad.estimateFee(make_don()).ok)
            self.assertTrue(ad.printWaybill(["X"]).ok)

    def test_l7_getshippinglabel_alias_tra_label_mock(self):
        ad = self.ad_mock()
        kq = ad.getShippingLabel("X")
        self.assertTrue(kq.ok)
        self.assertEqual(kq.tho["label"], "MOCK-PDF")


if __name__ == "__main__":
    unittest.main(verbosity=2)
