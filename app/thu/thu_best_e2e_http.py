# AG-00 — E2E HTTP THẬT cho webhook BEST Express.
#
# PHẠM VI: LOCAL + MOCK. Máy chủ THẬT `server.BoXuLy` bind `127.0.0.1`, cổng do hệ điều hành
# cấp. Mọi callback đi qua route `POST /api/v2/webhook/nhan/<webhook_ma>` bằng HTTP thật, không
# gọi thẳng hàm xử lý. Không có lời gọi nào tới `800best.com` hay bất kỳ host ngoài loopback.
# CSDL là thư mục tạm `tempfile.mkdtemp`; không đụng CSDL nghiệp vụ.
#
# VÌ SAO CÓ TỆP NÀY: bộ 51 ca của B3 gọi thẳng `webhook_best.xu_ly_voi_account()`. Nó chứng minh
# bộ xử lý đúng, KHÔNG chứng minh route HTTP đã nối vào bộ xử lý ấy, cũng KHÔNG chứng minh
# callback BEST không đi qua HMAC/ACK/hàng đợi của J&T. Tệp này đo đúng khoảng hở đó.
#
# HỢP ĐỒNG HÃNG: CHƯA ĐỌC ĐƯỢC tài liệu chính thức (Google Docs không có URL trong workspace).
# Vì vậy:
#   · `{"Result":1,"Message":""}` là thân ACK DUY NHẤT đã xác nhận trong đề bài B3;
#   · mã HTTP, thân NACK, điều kiện hãng gửi lại, nghĩa 23 mã trạng thái và cơ chế xác thực
#     callback là CHƯA XÁC MINH. Các ca dưới đây đo HÀNH VI NỘI BỘ đã chọn (fail-closed), không
#     đo "BEST thật sẽ làm gì". Mỗi chỗ như vậy ghi rõ `CHUA_XAC_MINH`.
#
# Chạy: python3 app/thu/thu_best_e2e_http.py
# Mã thoát: 0 = tất cả ca đạt; 1 = có ca hỏng/lỗi.
import hashlib
import hmac
import http.client
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-best-e2e-")

import adapter              # noqa: E402
import adapter_best         # noqa: E402  — đăng ký adapter + đọc chốt LIVE
import bao_mat              # noqa: E402
import cau_hinh             # noqa: E402
import csdl                 # noqa: E402
import don_hang             # noqa: E402
import quan_sat            # noqa: E402
import quyen                # noqa: E402
import server               # noqa: E402
import webhook as hub       # noqa: E402
import webhook_best as wb   # noqa: E402
import xac_thuc_best        # noqa: E402

# Các cột dấu vết của hub đã migrate. Thêm tại chỗ để bộ thử chạy trên schema ĐẦY ĐỦ, không
# phải schema rút gọn — đường ghi dấu vết mới là đường dễ bỏ sót nhất.
COT_THEM = (("hang_ma_goc", "TEXT"), ("hang_mo_ta_goc", "TEXT"), ("hang_su_kien_goc", "TEXT"),
            ("anh_xa_do_tin_cay", "TEXT"), ("anh_xa_nguon", "TEXT"),
            ("can_soat", "INTEGER NOT NULL DEFAULT 0"), ("hang_moc_thoi_gian", "TEXT"),
            ("don_id", "INTEGER"), ("trang_thai_chuan", "TEXT"))

_LOG = io.StringIO()
quan_sat.dat_luong_log(_LOG)

_NEN = {}
_SV = None
_CONG = None


# ---------------------------------------------------------------- hạ tầng fixture
def _dem(bang):
    return csdl.mot(f"SELECT COUNT(*) c FROM {bang}")["c"]


def _user():
    n = _dem("users")
    return csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                    " VALUES (?,?,'U',?)",
                    (f"e2eu{n}-{uuid.uuid4().hex[:6]}",
                     bao_mat.bam_mat_khau("x" * 12), csdl.bay_gio())).lastrowid


def _tenant(ten="Tenant E2E"):
    n = _dem("tenants")
    return csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,'pro',?)",
                    (f"e2e-{n}-{uuid.uuid4().hex[:8]}", ten, csdl.bay_gio())).lastrowid


def _account(tenant_id, hang="best", secret=None, moi_truong="mock", kich_hoat=1):
    secret = secret or ("sec-" + uuid.uuid4().hex)
    ban_ma, duoi = bao_mat.luu_credentials({"api_key": "demo"},
                                           bao_mat.aad_credentials(tenant_id, hang))
    wh_ma = f"e2e-{hang}-{uuid.uuid4().hex[:12]}"
    aid = csdl.ghi(
        "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
        "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,kich_hoat,tao_luc)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tenant_id, hang, f"{hang}-{wh_ma}", moi_truong, ban_ma, duoi, wh_ma,
         bao_mat.ma_hoa_wh(secret, wh_ma), kich_hoat, csdl.bay_gio())).lastrowid
    return {"id": aid, "tenant_id": tenant_id, "hang": hang, "secret": secret, "wh_ma": wh_ma,
            "moi_truong": moi_truong, "kich_hoat": kich_hoat}


def _don(tenant_id, account_id, code, merchant=None, trang_thai_giao=None,
         trang_thai="da_gui"):
    merchant = merchant or f"MD-{code}"
    hang = cau_hinh.HANG_TRANG_THAI_GIAO.get(trang_thai_giao, 0)
    return csdl.ghi(
        "INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,"
        "nguoi_gui_dia_chi,nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,"
        "khoi_luong_gram,carrier_account_id,ma_van_don,trang_thai,trang_thai_giao,"
        "hang_trang_thai_giao,nguoi_tao,tao_luc,cap_nhat_luc)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tenant_id, merchant, "A", "0901111111", "x", "B", "0902222222", "y", "z", 800,
         account_id, code, trang_thai, trang_thai_giao, hang, _NEN["uid"],
         csdl.bay_gio(), csdl.bay_gio())).lastrowid


def _payload(code, merchant, status, moc, **thua):
    """Đúng 18 trường đã xác nhận trong đề bài B3. Dữ liệu là fixture MOCK, không phải BEST thật."""
    d = {
        "code_best": code,
        "merchant_order_code": merchant,
        "cod": 150000,
        "product_price": 300000,
        "status": status,
        "status_content": "MOCK fixture — không phải dữ liệu BEST thật",
        "freight_fee": 22000,
        "cod_fee": 3000,
        "insurance_fee": 1000,
        "vat_fee": 2000,
        "return_fee": 0,
        "discount": 5000,
        "modified_at": moc,
        "total_fee": 323000,
        "weight": 800,
        "length": 20,
        "width": 15,
        "height": 10,
    }
    d.update(thua)
    return d


def _body(p):
    return json.dumps(p, ensure_ascii=False).encode("utf-8")


def _ky(secret, body):
    return {"X-Webhook-Signature":
            hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}


def _post(wh_ma, body, headers=None, timeout=10):
    """POST thật qua loopback. Trả `(status, raw_bytes, headers_dict)`."""
    hd = {"Content-Type": "application/json", "Connection": "close"}
    if headers:
        hd.update(headers)
    c = http.client.HTTPConnection("127.0.0.1", _CONG, timeout=timeout)
    try:
        c.request("POST", f"/api/v2/webhook/nhan/{wh_ma}", body=body, headers=hd)
        r = c.getresponse()
        raw = r.read()
        return r.status, raw, dict(r.getheaders())
    finally:
        c.close()


def _gui(tk, p, headers=None, secret=None):
    body = _body(p)
    hd = _ky(secret or tk["secret"], body) if headers is None else headers
    return _post(tk["wh_ma"], body, hd)


def _json(raw):
    try:
        return json.loads(raw)
    except Exception:
        return None


def _sk(tk_id):
    return csdl.nhieu("SELECT * FROM wh_su_kien WHERE carrier_account_id=? ORDER BY id", (tk_id,))


def _sk_id(sk_id):
    return csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))


def _don_row(don_id):
    return csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))


def _ls(don_id):
    return csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don_id,))


def _audit(hanh_dong=None, resource_id=None):
    sql = "SELECT * FROM audit WHERE 1=1"
    ts = []
    if hanh_dong:
        sql += " AND hanh_dong=?"
        ts.append(hanh_dong)
    if resource_id is not None:
        sql += " AND resource_id=?"
        ts.append(str(resource_id))
    return csdl.nhieu(sql + " ORDER BY id", ts)


def _quet_bay(canary):
    """Quét MỌI tệp trong thư mục dữ liệu tạm. Canary không được xuất hiện ở bất kỳ đâu."""
    for goc, _, ten in os.walk(cau_hinh.THU_MUC_DU_LIEU):
        for t in ten:
            duong = os.path.join(goc, t)
            try:
                with open(duong, "rb") as f:
                    if canary.encode() in f.read():
                        return duong
            except OSError:
                continue
    return None


def _dung_nen():
    if _NEN:
        return _NEN
    csdl.mo()
    quyen.seed()
    csdl.ghi("INSERT OR IGNORE INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
             (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
    for ma, ten in (("best", "BEST Express"), ("jt", "J&T Express")):
        csdl.ghi("INSERT OR IGNORE INTO carrier_providers"
                 " (ma,ten,capabilities_json,live_mo,cap_nhat_luc) VALUES (?,?,?,?,?)",
                 (ma, ten, json.dumps({"webhook": True}), 0, csdl.bay_gio()))
    co = {r[1] for r in csdl.nhieu("PRAGMA table_info(wh_su_kien)")}
    for ten, kieu in COT_THEM:
        if ten not in co:
            csdl.ghi(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
    hub.xoa_cache_cot()
    _NEN["uid"] = _user()
    return _NEN


def setUpModule():
    global _SV, _CONG
    _dung_nen()
    _SV = ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    _CONG = _SV.server_address[1]
    threading.Thread(target=_SV.serve_forever, name="best-e2e-http", daemon=True).start()
    hub.khoi_dong()


def tearDownModule():
    hub.dung()
    hub.cho_rong(5)
    if _SV is not None:
        _SV.shutdown()
        _SV.server_close()


class Nen(unittest.TestCase):
    """Tiện ích dùng chung. Mỗi ca tự dựng tenant/tài khoản/đơn RIÊNG để phép đếm độc lập."""

    def tk_moi(self, **kw):
        return _account(_tenant(), **kw)

    def tk_trong_tenant(self, tenant_id, **kw):
        return _account(tenant_id, **kw)

    def tao_don(self, tk, code, merchant=None, **kw):
        return _don(tk["tenant_id"], tk["id"], code, merchant, **kw)

    def soi(self, status, raw):
        return status, _json(raw), raw


# ============================================================================
# A. ĐƯỜNG HỢP LỆ — đúng ACK, lưu event, cập nhật đơn/lịch sử/audit
# ============================================================================
class A_HopLe(Nen):
    def test_a01_callback_hop_le_qua_http_du_11_buoc_va_du_lieu(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-A1", "MD-A1")
        p = _payload("BEST-A1", "MD-A1", 211, "2026-10-19T10:00:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(than, {"Result": 1, "Message": ""},
                         "ACK thành công phải ĐÚNG hai khóa, không thêm trường")

        dsk = _sk(tk["id"])
        self.assertEqual(len(dsk), 1, "một callback hợp lệ phải có đúng một sự kiện thô")
        sk = dsk[0]
        self.assertEqual(sk["trang_thai"], "xong")
        self.assertEqual(sk["trang_thai_chuan"], "cho_lay")
        self.assertEqual(sk["don_id"], don_id)
        self.assertIsNotNone(sk["hang_moc_thoi_gian"])
        self.assertEqual(sk["can_soat"], 0)
        tho = json.loads(bytes(sk["payload_tho"]))
        self.assertEqual(set(wb.TRUONG_PAYLOAD) - set(tho), set(),
                         "payload thô phải giữ đủ 18 trường đã xác nhận")
        hd = json.loads(sk["headers_json"])
        self.assertNotIn("x-webhook-signature", hd, "chữ ký không được lưu vào sự kiện")
        self.assertNotIn("authorization", hd, "Authorization không được lưu vào sự kiện")

        don = _don_row(don_id)
        self.assertEqual(don["trang_thai_giao"], "cho_lay")
        self.assertEqual(don["hang_trang_thai_giao"],
                         cau_hinh.HANG_TRANG_THAI_GIAO["cho_lay"])

        ls = _ls(don_id)
        self.assertEqual(len(ls), 1)
        self.assertIn(f"webhook_best:{sk['id']}", ls[0]["nguon"])

        self.assertTrue(_audit("webhook_best_cap_nhat_don", str(sk["id"])))
        self.assertTrue(_audit("webhook_best_moc_hang", don_id))
        self.assertNotIn(b"token", raw.lower())
        self.assertNotIn(b"secret", raw.lower())

    def test_a02_route_that_su_di_qua_server_va_co_request_id(self):
        """Chứng minh đây là HTTP thật qua `server.BoXuLy`, không phải gọi hàm."""
        tk = self.tk_moi()
        self.tao_don(tk, "BEST-A2", "MD-A2")
        p = _payload("BEST-A2", "MD-A2", 211, "2026-10-19T10:01:00+07:00")
        status, raw, hs = _gui(tk, p)
        self.assertEqual(status, 200)
        self.assertIn("X-Request-Id", hs, "route thật phải gắn X-Request-Id")
        self.assertTrue(hs["X-Request-Id"])
        # Route đã trả JSON; chứng minh header bảo mật của server vẫn còn.
        self.assertEqual(hs.get("X-Content-Type-Options"), "nosniff")

    def test_a03_khong_co_duong_tat_bo_qua_kho_su_kien(self):
        """ACK chỉ sau khi dòng `wh_su_kien` đã bền: event phải tồn tại trước/đồng thời ACK."""
        tk = self.tk_moi()
        self.tao_don(tk, "BEST-A3", "MD-A3")
        p = _payload("BEST-A3", "MD-A3", 211, "2026-10-19T10:02:00+07:00")
        status, raw, _ = _gui(tk, p)
        self.assertEqual(status, 200)
        sk = _sk(tk["id"])
        self.assertEqual(len(sk), 1)
        self.assertEqual(sk[0]["trang_thai"], "xong")
        self.assertIsNotNone(sk[0]["xu_ly_xong_luc"])


# ============================================================================
# B. XÁC THỰC — sai/thiếu, chốt LIVE, định danh, tài khoản khóa, sai hãng
# ============================================================================
class B_XacThuc(Nen):
    def test_b01_thieu_chu_ky_tra_401_va_khong_ghi_gi(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-B1", "MD-B1")
        p = _payload("BEST-B1", "MD-B1", 211, "2026-10-19T11:00:00+07:00")
        status, than, raw = self.soi(*_post(tk["wh_ma"], _body(p),
                                           {"Content-Type": "application/json"})[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertTrue(than["Message"])
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertEqual(_ls(don_id), [])
        self.assertTrue(_audit("webhook_best_tu_choi", str(tk["id"])))

    def test_b02_chu_ky_sai_tra_401_va_khong_ghi_gi(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-B2", "MD-B2")
        p = _payload("BEST-B2", "MD-B2", 211, "2026-10-19T11:01:00+07:00")
        status, than, raw = self.soi(*_post(tk["wh_ma"], _body(p),
                                           {"X-Webhook-Signature": "0" * 64})[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_b03_chu_ky_cua_tai_khoan_khac_tra_401(self):
        tk_a = self.tk_moi()
        tk_b = self.tk_moi()
        self.tao_don(tk_a, "BEST-B3", "MD-B3")
        p = _payload("BEST-B3", "MD-B3", 211, "2026-10-19T11:02:00+07:00")
        status, than, raw = self.soi(*_gui(tk_a, p, secret=tk_b["secret"])[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk_a["id"]), [])

    def test_b04_best_sandbox_bi_tu_choi_fail_closed(self):
        """Chưa có sơ đồ xác thực BEST đã xác minh ⇒ KHÔNG đoán, KHÔNG nhận callback."""
        tk = self.tk_moi(moi_truong="sandbox")
        don_id = self.tao_don(tk, "BEST-B4", "MD-B4")
        p = _payload("BEST-B4", "MD-B4", 211, "2026-10-19T11:03:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertIn("BLOCKED", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertTrue(_audit("webhook_best_tu_choi", str(tk["id"])))

    def test_b05_best_production_bi_tu_choi_fail_closed(self):
        tk = self.tk_moi(moi_truong="production")
        don_id = self.tao_don(tk, "BEST-B5", "MD-B5")
        p = _payload("BEST-B5", "MD-B5", 211, "2026-10-19T11:04:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_b11_sandbox_bearer_hop_le_duoc_nhan_va_cap_nhat(self):
        """Webhook BEST thật dùng JWT Bearer, không phải HMAC. Token lưu mã hoá theo account."""
        tk = self.tk_moi(moi_truong="sandbox")
        don_id = self.tao_don(tk, "BEST-B11", "MD-B11")
        bearer = "v9." + uuid.uuid4().hex
        xac_thuc_best.luu_bearer_webhook(str(tk["tenant_id"]), str(tk["id"]), bearer,
                                         webhook_ma=tk["wh_ma"])
        p = _payload("BEST-B11", "MD-B11", 211, "2026-10-19T11:09:00+07:00")
        status, than, raw = self.soi(*_post(tk["wh_ma"], _body(p),
                                           {"Authorization": "Bearer " + bearer})[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(than, {"Result": 1, "Message": ""})
        self.assertEqual(len(_sk(tk["id"])), 1)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "cho_lay")

    def test_b12_sandbox_bearer_sai_bi_tu_choi(self):
        tk = self.tk_moi(moi_truong="sandbox")
        don_id = self.tao_don(tk, "BEST-B12", "MD-B12")
        bearer = "v9." + uuid.uuid4().hex
        xac_thuc_best.luu_bearer_webhook(str(tk["tenant_id"]), str(tk["id"]), bearer,
                                         webhook_ma=tk["wh_ma"])
        p = _payload("BEST-B12", "MD-B12", 211, "2026-10-19T11:10:00+07:00")
        status, than, raw = self.soi(*_post(tk["wh_ma"], _body(p),
                                           {"Authorization": "Bearer " + "x" * 20})[:2])
        self.assertEqual(status, 401, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_b06_dinh_danh_khong_ton_tai_tra_404(self):
        truoc = _dem("wh_su_kien")
        status, than, raw = self.soi(*_post("khong-co-dinh-danh-nay", b"{}",
                                           {"Content-Type": "application/json"})[:2])
        self.assertEqual(status, 404, raw)
        self.assertIn("loi", than)
        self.assertEqual(_dem("wh_su_kien"), truoc)

    def test_b07_tai_khoan_bi_khoa_khong_nhan_callback(self):
        tk = self.tk_moi(kich_hoat=0)
        don_id = self.tao_don(tk, "BEST-B7", "MD-B7")
        p = _payload("BEST-B7", "MD-B7", 211, "2026-10-19T11:06:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 404, raw)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_b08_sai_hang_khong_di_vao_bo_xu_ly_best(self):
        """Payload BEST gửi vào định danh J&T, ký bằng secret BEST ⇒ J&T từ chối ở HMAC."""
        tk_jt = self.tk_moi(hang="jt")
        don_id = self.tao_don(tk_jt, "BEST-B8", "MD-B8")
        p = _payload("BEST-B8", "MD-B8", 211, "2026-10-19T11:07:00+07:00")
        status, than, raw = self.soi(*_gui(tk_jt, p, secret="secret-best-khac")[:2])
        self.assertEqual(status, 401, raw)
        self.assertIn("loi", than)
        self.assertEqual(_sk(tk_jt["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        rows = [r for r in _audit("webhook_best_cap_nhat_don")
                if "BEST-B8" in (r["chi_tiet"] or "")]
        self.assertEqual(rows, [], "payload sai hãng không được đi qua bộ xử lý BEST")


    def test_b09_payload_best_vao_tai_khoan_jt_voi_chu_ky_jt_dung_di_duong_jt(self):
        """Phân luồng theo HÃNG CỦA ACCOUNT, không theo hình dạng payload.

        Gửi thân BEST vào định danh J&T nhưng ký ĐÚNG secret J&T: J&T nhận nó như sự kiện thô
        của chính nó (202, `code=1`), KHÔNG có `Result` của BEST và KHÔNG có audit cập nhật BEST.
        """
        tk_jt = self.tk_moi(hang="jt")
        p = _payload("BEST-B9", "MD-B9", 211, "2026-10-19T11:08:00+07:00")
        body = _body(p)
        status, than, raw = self.soi(*_post(tk_jt["wh_ma"], body,
                                           _ky(tk_jt["secret"], body))[:2])
        self.assertEqual(status, 202, raw)
        self.assertEqual(than.get("ket_qua"), "da_nhan")
        self.assertIn("code", than)
        self.assertNotIn("Result", than)
        self.assertEqual(len(_sk(tk_jt["id"])), 1)
        self.assertFalse([r for r in _audit("webhook_best_cap_nhat_don")
                          if "BEST-B9" in (r["chi_tiet"] or "")])

    def test_b10_payload_jt_vao_tai_khoan_best_tra_422_khong_luu(self):
        """Thân form J&T gửi vào định danh BEST: BEST từ chối JSON sai, không lưu, không ACK."""
        tk = self.tk_moi()
        body = b"bizContent=%7B%22billCode%22%3A%22JT-B10%22%7D"
        status, than, raw = self.soi(*_post(tk["wh_ma"], body,
                                           _ky(tk["secret"], body))[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])


# ============================================================================
# C. PAYLOAD — sai/thiếu/sai kiểu/quá lớn
# ============================================================================
class C_Payload(Nen):
    def _nen_ca(self, code):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, code, f"MD-{code}")
        return tk, don_id

    def test_c01_json_hong_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C1")
        body = b'{"code_best":'
        status, than, raw = self.soi(*_post(tk["wh_ma"], body, _ky(tk["secret"], body))[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c02_thieu_truong_bat_buoc_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C2")
        p = _payload("BEST-C2", "MD-BEST-C2", 211, "2026-10-19T11:10:00+07:00")
        del p["status"]
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertIn("status", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c03_sai_kieu_status_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C3")
        p = _payload("BEST-C3", "MD-BEST-C3", "abc", "2026-10-19T11:11:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])

    def test_c04_sai_kieu_modified_at_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C4")
        p = _payload("BEST-C4", "MD-BEST-C4", 211, "khong-phai-thoi-gian")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertIn("modified_at", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])

    def test_c05_status_content_qua_dai_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C5")
        p = _payload("BEST-C5", "MD-BEST-C5", 211, "2026-10-19T11:13:00+07:00",
                     status_content="x" * (wb.GIOI_HAN_MO_TA + 1))
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(_sk(tk["id"]), [])

    def test_c06_than_qua_lon_tra_413_va_khong_luu(self):
        tk, don_id = self._nen_ca("BEST-C6")
        p = _payload("BEST-C6", "MD-BEST-C6", 211, "2026-10-19T11:14:00+07:00",
                     padding="x" * (wb.GIOI_HAN_BODY + 1024))
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 413, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c11_than_lon_hon_64KiB_nhung_duoi_tran_best_duoc_nhan(self):
        """Ca BIÊN của trần body: 100 KiB > trần mặc định 64 KiB của server, < 256 KiB của BEST.

        Thiếu ca này, `test_c06` không phân biệt được trần 256 KiB với trần 64 KiB: cả hai đều
        trả 413 cho thân 300 KiB. Đây là ca làm phép tiêm "đọc bằng trần mặc định" phải ĐỎ.
        """
        tk, don_id = self._nen_ca("BEST-C11")
        p = _payload("BEST-C11", "MD-BEST-C11", 211, "2026-10-19T11:18:00+07:00",
                     padding="x" * (100 * 1024))
        body = _body(p)
        self.assertGreater(len(body), 64 * 1024)
        self.assertLess(len(body), wb.GIOI_HAN_BODY)
        status, than, raw = self.soi(*_post(tk["wh_ma"], body,
                                           _ky(tk["secret"], body))[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(than, {"Result": 1, "Message": ""})
        self.assertEqual(len(_sk(tk["id"])), 1)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "cho_lay")

    def test_c12_modified_at_nan_tra_422(self):
        """NaN không phải mốc thời gian; phải là 422 Result/Message, không phải 500 generic."""
        tk, don_id = self._nen_ca("BEST-C12")
        p = _payload("BEST-C12", "MD-BEST-C12", 211, float("nan"))
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c13_modified_at_infinity_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C13")
        p = _payload("BEST-C13", "MD-BEST-C13", 211, float("inf"))
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c14_modified_at_offset_sai_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C14")
        p = _payload("BEST-C14", "MD-BEST-C14", 211, "2026-10-19T10:00:00+99:99")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c15_modified_at_xa_tuong_lai_tra_422(self):
        """14 chữ số nhưng là năm ~5138: không được đẩy watermark rồi đóng băng đơn."""
        tk, don_id = self._nen_ca("BEST-C15")
        p = _payload("BEST-C15", "MD-BEST-C15", 211, 99999999999999)
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c16_modified_at_qua_cu_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C16")
        p = _payload("BEST-C16", "MD-BEST-C16", 211, "2000-01-01T00:00:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(than["Result"], 0)
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])

    def test_c07_sai_utf8_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C7")
        status, than, raw = self.soi(*_post(tk["wh_ma"], b"\xff\xfe\x00",
                                           _ky(tk["secret"], b"\xff\xfe\x00"))[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(_sk(tk["id"]), [])

    def test_c08_json_khong_phai_object_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C8")
        body = b"[]"
        status, than, raw = self.soi(*_post(tk["wh_ma"], body, _ky(tk["secret"], body))[:2])
        self.assertEqual(status, 422, raw)
        self.assertIn("đối tượng", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])

    def test_c09_ma_co_khoang_trang_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C9")
        p = _payload("BEST C9", "MD-BEST-C9", 211, "2026-10-19T11:16:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertIn("khoảng trắng", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])

    def test_c10_so_tien_am_tra_422(self):
        tk, don_id = self._nen_ca("BEST-C10")
        p = _payload("BEST-C10", "MD-BEST-C10", 211, "2026-10-19T11:17:00+07:00", cod=-1)
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 422, raw)
        self.assertEqual(_sk(tk["id"]), [])


# ============================================================================
# D. TENANT — payload khai tenant, chéo tenant, cùng mã, tenant hỏng
# ============================================================================
class D_Tenant(Nen):
    def test_d01_payload_khai_tenant_khac_bi_bo_qua(self):
        ta = _tenant("Tenant A")
        tb = _tenant("Tenant B")
        tk_a = self.tk_trong_tenant(ta)
        tk_b = self.tk_trong_tenant(tb)
        don_a = self.tao_don(tk_a, "BEST-D1-A", "MD-D1-A")
        don_b = self.tao_don(tk_b, "BEST-D1-B", "MD-D1-B")
        p = _payload("BEST-D1-A", "MD-D1-A", 211, "2026-10-19T12:00:00+07:00",
                     tenant_id=tb)
        status, than, raw = self.soi(*_gui(tk_a, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(_don_row(don_a)["trang_thai_giao"], "cho_lay")
        self.assertIsNone(_don_row(don_b)["trang_thai_giao"],
                          "payload khai tenant B không được kéo đơn tenant B")
        self.assertTrue(_audit("webhook_best_claim_tenant_bi_bo_qua", str(tk_a["id"])))
        # Event lưu theo tenant của ACCOUNT A.
        sk = _sk(tk_a["id"])
        self.assertEqual(len(sk), 1)
        self.assertEqual(sk[0]["trang_thai_chuan"], "cho_lay")

    def test_d02_tracking_thuoc_tenant_khac_khong_bi_cap_nhat(self):
        ta = _tenant("Tenant A")
        tb = _tenant("Tenant B")
        tk_a = self.tk_trong_tenant(ta)
        tk_b = self.tk_trong_tenant(tb)
        don_b = self.tao_don(tk_b, "BEST-D2-B", "MD-D2-B")
        p = _payload("BEST-D2-B", "MD-D2-B", 211, "2026-10-19T12:01:00+07:00")
        status, than, raw = self.soi(*_gui(tk_a, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(len(_sk(tk_a["id"])), 1)
        self.assertEqual(_sk(tk_b["id"]), [])
        self.assertIsNone(_don_row(don_b)["trang_thai_giao"],
                          "callback của tenant A không được cập nhật đơn tenant B")
        self.assertEqual(_ls(don_b), [])

    def test_d03_merchant_lech_khong_cap_nhat_don(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-D3", "MD-D3-DUNG")
        p = _payload("BEST-D3", "MD-D3-SAI", 211, "2026-10-19T12:02:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(_sk(tk["id"])[0]["trang_thai"], "xong")
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertEqual(_ls(don_id), [])

    def test_d04_cung_ma_van_don_hai_tenant_chi_don_cua_account_doi(self):
        ta = _tenant("Tenant A")
        tb = _tenant("Tenant B")
        tk_a = self.tk_trong_tenant(ta)
        tk_b = self.tk_trong_tenant(tb)
        don_a = self.tao_don(tk_a, "BEST-D4-SHARED", "MD-D4-A")
        don_b = self.tao_don(tk_b, "BEST-D4-SHARED", "MD-D4-B")
        p = _payload("BEST-D4-SHARED", "MD-D4-A", 211, "2026-10-19T12:03:00+07:00")
        status, than, raw = self.soi(*_gui(tk_a, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertEqual(_don_row(don_a)["trang_thai_giao"], "cho_lay")
        self.assertIsNone(_don_row(don_b)["trang_thai_giao"])

    def test_d05_account_tro_tenant_khong_ton_tai_tra_403(self):
        csdl.ghi("PRAGMA foreign_keys=OFF")
        try:
            tk = _account(999999999, "best")
        finally:
            csdl.ghi("PRAGMA foreign_keys=ON")
        p = _payload("BEST-D5", "MD-D5", 211, "2026-10-19T12:04:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 403, raw)
        self.assertEqual(than["Result"], 0)
        self.assertIn("tenant", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])


    def test_d06_tracking_cung_tenant_nhung_tai_khoan_khac_tra_409(self):
        """Cùng tenant, tracking thuộc tài khoản hãng khác ⇒ DENY trước khi lưu thô."""
        ta = _tenant("Tenant A")
        tk1 = self.tk_trong_tenant(ta)
        tk2 = self.tk_trong_tenant(ta)
        don2 = self.tao_don(tk2, "BEST-D6", "MD-D6")
        p = _payload("BEST-D6", "MD-D6", 211, "2026-10-19T12:05:00+07:00")
        status, than, raw = self.soi(*_gui(tk1, p)[:2])
        self.assertEqual(status, 409, raw)
        self.assertEqual(than["Result"], 0)
        self.assertIn("tài khoản", than["Message"])
        self.assertEqual(_sk(tk1["id"]), [], "bị chặn trước bước lưu thô")
        self.assertIsNone(_don_row(don2)["trang_thai_giao"])


# ============================================================================
# E. TRÙNG — tuần tự, đồng thời, cùng mốc khác định dạng
# ============================================================================
class E_Trung(Nen):
    def test_e01_gui_trung_tuan_tu_mot_event_mot_lich_su(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-E1", "MD-E1")
        p = _payload("BEST-E1", "MD-E1", 211, "2026-10-19T13:00:00+07:00")
        body = _body(p)
        r1 = _post(tk["wh_ma"], body, _ky(tk["secret"], body))
        r2 = _post(tk["wh_ma"], body, _ky(tk["secret"], body))
        self.assertEqual(r1[0], 200)
        self.assertEqual(r2[0], 200)
        self.assertEqual(_json(r1[1]), {"Result": 1, "Message": ""})
        self.assertEqual(_json(r2[1]), {"Result": 1, "Message": ""})
        self.assertEqual(len(_sk(tk["id"])), 1, "gửi trùng không được tạo sự kiện thứ hai")
        self.assertEqual(len(_ls(don_id)), 1, "gửi trùng không được ghi lịch sử lần hai")
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "cho_lay")

    def test_e02_gui_dong_thoi_nam_luong_mot_event_mot_lich_su(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-E2", "MD-E2")
        p = _payload("BEST-E2", "MD-E2", 211, "2026-10-19T13:01:00+07:00")
        body = _body(p)
        hd = _ky(tk["secret"], body)
        rao = threading.Barrier(5)

        def go(_):
            rao.wait(timeout=10)
            return _post(tk["wh_ma"], body, hd)

        with ThreadPoolExecutor(max_workers=5) as ex:
            ds = list(ex.map(go, range(5)))
        self.assertTrue(all(r[0] == 200 for r in ds),
                        f"có lượt đồng thời không ACK: {[r[0] for r in ds]}")
        self.assertTrue(all(_json(r[1]) == {"Result": 1, "Message": ""} for r in ds))
        self.assertEqual(len(_sk(tk["id"])), 1)
        self.assertEqual(len(_ls(don_id)), 1)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "cho_lay")

    def test_e03_cung_moc_khac_dinh_dang_van_la_mot_su_kien(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-E3", "MD-E3")
        p1 = _payload("BEST-E3", "MD-E3", 211, "2026-10-19T10:00:00+07:00")
        p2 = _payload("BEST-E3", "MD-E3", 211, "2026-10-19T03:00:00Z")  # cùng thời điểm
        r1 = _gui(tk, p1)
        r2 = _gui(tk, p2)
        self.assertEqual(r1[0], 200)
        self.assertEqual(r2[0], 200)
        self.assertEqual(len(_sk(tk["id"])), 1,
                         "cùng mốc ở hai định dạng phải là CÙNG sự kiện")
        self.assertEqual(len(_ls(don_id)), 1)


# ============================================================================
# F. THỨ TỰ — cũ đến muộn, cùng mốc khác trạng thái, mã nhỏ mốc mới
# ============================================================================
class F_ThuTu(Nen):
    def test_f01_su_kien_cu_den_muon_khong_doi_don(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F1", "MD-F1")
        p1 = _payload("BEST-F1", "MD-F1", 301, "2026-10-19T10:00:00+07:00")
        p2 = _payload("BEST-F1", "MD-F1", 302, "2026-10-19T09:00:00+07:00")
        self.assertEqual(_gui(tk, p1)[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao")
        r2 = _gui(tk, p2)
        self.assertEqual(r2[0], 200, "sự kiện cũ vẫn phải được lưu và ACK")
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao",
                         "mốc cũ hơn không được ghi đè trạng thái mới hơn")
        self.assertEqual(len(_ls(don_id)), 1)
        sk_id = _sk(tk["id"])[1]["id"]
        bo_qua = _audit("webhook_best_bo_qua", str(sk_id))
        self.assertTrue(any("đến muộn" in (r["chi_tiet"] or "") for r in bo_qua),
                        "phải ghi audit lý do đến muộn")

    def test_f02_cung_moc_khac_trang_thai_khong_doan(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F2", "MD-F2")
        p1 = _payload("BEST-F2", "MD-F2", 301, "2026-10-19T10:00:00+07:00")
        p2 = _payload("BEST-F2", "MD-F2", 604, "2026-10-19T10:00:00+07:00")
        self.assertEqual(_gui(tk, p1)[0], 200)
        r2 = _gui(tk, p2)
        self.assertEqual(r2[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao",
                         "cùng mốc khác trạng thái: không được đoán bên nào đúng")
        self.assertEqual(len(_ls(don_id)), 1)
        sk_id = _sk(tk["id"])[1]["id"]
        bo_qua = _audit("webhook_best_bo_qua", str(sk_id))
        self.assertTrue(any("xung đột mốc" in (r["chi_tiet"] or "") for r in bo_qua))

    def test_f03_ma_nho_hon_nhung_moc_moi_van_duoc_ap(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F3", "MD-F3", trang_thai_giao="hoan_hang")
        p1 = _payload("BEST-F3", "MD-F3", 606, "2026-10-19T10:00:00+07:00")
        p2 = _payload("BEST-F3", "MD-F3", 605, "2026-10-19T11:00:00+07:00")
        self.assertEqual(_gui(tk, p1)[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao")
        self.assertEqual(_gui(tk, p2)[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "hoan_hang",
                         "quyết định theo modified_at, KHÔNG theo thứ hạng số mã")
        self.assertEqual(len(_ls(don_id)), 2)

    def test_f04_trang_thai_cuoi_chi_mo_bang_606(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F4", "MD-F4", trang_thai_giao="giao_thanh_cong")
        p1 = _payload("BEST-F4", "MD-F4", 301, "2026-10-19T11:00:00+07:00")
        p2 = _payload("BEST-F4", "MD-F4", 606, "2026-10-19T12:00:00+07:00")
        self.assertEqual(_gui(tk, p1)[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "giao_thanh_cong",
                         "trạng thái cuối không được hạ bằng mã thường")
        self.assertEqual(_gui(tk, p2)[0], 200)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao",
                         "606 phải mở lại chiều giao")
        self.assertEqual(len(_ls(don_id)), 1,
                         "lượt 301 bị chặn không được bịa lịch sử")

    def test_f05_606_khong_mo_don_da_huy_nghiep_vu(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F5", "MD-F5", trang_thai="huy")
        p = _payload("BEST-F5", "MD-F5", 606, "2026-10-19T12:00:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 200, raw)
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertEqual(_ls(don_id), [])

    def test_f06_ma_la_van_luu_va_ack_khong_doi_don(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F6", "MD-F6")
        p = _payload("BEST-F6", "MD-F6", 99999, "2026-10-19T12:01:00+07:00")
        status, than, raw = self.soi(*_gui(tk, p)[:2])
        self.assertEqual(status, 200, raw)
        sk = _sk(tk["id"])
        self.assertEqual(len(sk), 1)
        self.assertEqual(sk[0]["trang_thai"], "xong")
        self.assertIsNone(sk[0]["trang_thai_chuan"])
        self.assertEqual(sk[0]["can_soat"], 1)
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertEqual(_ls(don_id), [])


    def _huy_sau_khi_tim_don(self):
        """Giả lập hủy đơn xen giữa `tim_don()` và bước cập nhật (race đọc-rồi-ghi)."""
        that = wb.tim_don

        def tim_don_roi_huy(tk_row, tenant_id, p):
            don, ly_do = that(tk_row, tenant_id, p)
            if don is not None:
                csdl.ghi("UPDATE don_hang SET trang_thai='huy' WHERE id=?", (don["id"],))
            return don, ly_do

        return that, tim_don_roi_huy

    def test_f07_huy_don_xen_giua_doc_va_606_khong_bi_ghi_de(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F7", "MD-F7", trang_thai_giao="hoan_hang")
        p = _payload("BEST-F7", "MD-F7", 606, "2026-10-19T12:02:00+07:00")
        that, ham = self._huy_sau_khi_tim_don()
        wb.tim_don = ham
        try:
            status, than, raw = self.soi(*_gui(tk, p)[:2])
        finally:
            wb.tim_don = that
        self.assertEqual(status, 200, raw)
        self.assertEqual(_don_row(don_id)["trang_thai"], "huy")
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "hoan_hang",
                         "606 không được ghi đè đơn vừa bị hủy")
        self.assertEqual(_ls(don_id), [])

    def test_f08_huy_don_xen_giua_doc_va_buoc_thuong_khong_bi_ghi_de(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-F8", "MD-F8")
        p = _payload("BEST-F8", "MD-F8", 301, "2026-10-19T12:03:00+07:00")
        that, ham = self._huy_sau_khi_tim_don()
        wb.tim_don = ham
        try:
            status, than, raw = self.soi(*_gui(tk, p)[:2])
        finally:
            wb.tim_don = that
        self.assertEqual(status, 200, raw)
        self.assertEqual(_don_row(don_id)["trang_thai"], "huy")
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"],
                          "bước thường không được ghi đè đơn vừa bị hủy")
        self.assertEqual(_ls(don_id), [])


# ============================================================================
# G. 605 → 606 — cặp mở lại chiều giao (nghĩa 605 vẫn CHƯA XÁC MINH)
# ============================================================================
class G_605_606(Nen):
    def test_g01_luong_605_606_qua_http(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-G1", "MD-G1", trang_thai_giao="dang_giao")
        p605 = _payload("BEST-G1", "MD-G1", 605, "2026-10-19T10:00:00+07:00")
        p606 = _payload("BEST-G1", "MD-G1", 606, "2026-10-19T11:00:00+07:00")
        status1, than1, raw1 = self.soi(*_gui(tk, p605)[:2])
        self.assertEqual(status1, 200, raw1)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "hoan_hang")
        status2, than2, raw2 = self.soi(*_gui(tk, p606)[:2])
        self.assertEqual(status2, 200, raw2)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "dang_giao")
        ls = _ls(don_id)
        self.assertEqual(len(ls), 2)
        self.assertIn("mở lại chiều giao", ls[-1]["noi_dung"])
        self.assertEqual(len(_audit("webhook_best_moc_hang", don_id)), 2)

    def test_g02_bang_ma_23_va_muc_bang_chung_khong_bi_nang(self):
        """Đề bài nói 24 nhưng chỉ liệt kê 23: KHÔNG bịa mã thứ 24, KHÔNG tự nhận đã kiểm chứng."""
        self.assertEqual(len(wb.MA_TRONG_DE_BAI), 23)
        self.assertEqual(set(wb.BANG_MA), set(wb.MA_TRONG_DE_BAI))
        self.assertEqual(wb.SO_MA_DE_BAI, 23)
        self.assertEqual(wb.SO_MA_LIET_KE, 23)
        self.assertNotIn(99999, wb.BANG_MA)
        self.assertTrue(wb.BANG_MA[606]["mo_lai"])
        self.assertEqual([m for m, d in wb.BANG_MA.items() if d["mo_lai"]], [606])
        for ma, d in wb.BANG_MA.items():
            self.assertEqual(d["muc"], wb.MUC_DA_TAI_LIEU, f"mã {ma} sai mức")
        self.assertEqual(wb.kiem_bat_bien(), [])


# ============================================================================
# H. LƯU BỀN THẤT BẠI — không ACK thành công, đối chứng dương
# ============================================================================
class H_LuuThatBai(Nen):
    def test_h01_insert_su_kien_no_tra_500_va_khong_doi_du_lieu(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-H1", "MD-H1")
        p = _payload("BEST-H1", "MD-H1", 211, "2026-10-19T14:00:00+07:00")
        body = _body(p)
        hd = _ky(tk["secret"], body)
        that = csdl.ghi

        def hong(sql, tham_so=()):
            if "INSERT INTO wh_su_kien" in sql:
                raise RuntimeError("disk I/O error (giả lập)")
            return that(sql, tham_so)

        csdl.ghi = hong
        try:
            status, raw, _ = _post(tk["wh_ma"], body, hd)
        finally:
            csdl.ghi = that
        self.assertEqual(status, 500, raw)
        than = _json(raw)
        self.assertEqual(than["Result"], 0, "lưu thất bại KHÔNG được ACK thành công")
        self.assertIn("không lưu", than["Message"])
        self.assertEqual(_sk(tk["id"]), [])
        self.assertIsNone(_don_row(don_id)["trang_thai_giao"])
        self.assertEqual(_ls(don_id), [])
        self.assertTrue(_audit("webhook_best_loi_luu", str(tk["id"])))

    def test_h02_doi_chung_duong_sau_khi_go_loi_van_ack_va_cap_nhat(self):
        tk = self.tk_moi()
        don_id = self.tao_don(tk, "BEST-H2", "MD-H2")
        p = _payload("BEST-H2", "MD-H2", 211, "2026-10-19T14:01:00+07:00")
        body = _body(p)
        hd = _ky(tk["secret"], body)
        that = csdl.ghi

        def hong(sql, tham_so=()):
            if "INSERT INTO wh_su_kien" in sql:
                raise RuntimeError("disk I/O error (giả lập)")
            return that(sql, tham_so)

        csdl.ghi = hong
        try:
            status_loi, raw_loi, _ = _post(tk["wh_ma"], body, hd)
        finally:
            csdl.ghi = that
        self.assertEqual(status_loi, 500)
        self.assertEqual(_json(raw_loi)["Result"], 0)

        status, raw, _ = _post(tk["wh_ma"], body, hd)
        self.assertEqual(status, 200, raw)
        self.assertEqual(_json(raw), {"Result": 1, "Message": ""})
        self.assertEqual(len(_sk(tk["id"])), 1)
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "cho_lay")
        self.assertEqual(len(_ls(don_id)), 1)


# ============================================================================
# I. HỒI QUY HÃNG KHÁC — J&T vẫn chạy qua route chung
# ============================================================================
class I_HoiQuyJT(Nen):
    def test_i01_jt_mock_van_nhan_202_va_luu_su_kien(self):
        tk = self.tk_moi(hang="jt")
        don_id = self.tao_don(tk, "JT-I1")
        body = json.dumps({"event": "lay_hang", "tracking_number": "JT-I1",
                           "event_id": "E-JT-I1"}, ensure_ascii=False).encode()
        status, raw, _ = _post(tk["wh_ma"], body, _ky(tk["secret"], body))
        self.assertEqual(status, 202, raw)
        than = _json(raw)
        self.assertEqual(than["ket_qua"], "da_nhan")
        self.assertEqual(than.get("code"), 1)
        self.assertEqual(len(_sk(tk["id"])), 1)
        self.assertTrue(hub.cho_rong(10), "worker nền J&T không xử lý xong")
        self.assertEqual(_don_row(don_id)["trang_thai_giao"], "lay_hang")

    def test_i02_jt_chu_ky_sai_van_tra_401_va_khong_luu(self):
        tk = self.tk_moi(hang="jt")
        body = json.dumps({"event": "lay_hang", "tracking_number": "JT-I2",
                           "event_id": "E-JT-I2"}).encode()
        status, raw, _ = _post(tk["wh_ma"], body, {"X-Webhook-Signature": "0" * 64})
        self.assertEqual(status, 401, raw)
        self.assertEqual(_sk(tk["id"]), [])


# ============================================================================
# J. BẢO MẬT — không rò secret/token trong response/log/event/audit
# ============================================================================
class J_BaoMat(Nen):
    def test_j01_khong_ro_secret_token_trong_response_event_audit_log(self):
        canary = "CANARY-" + uuid.uuid4().hex
        secret_canary = "SECRET-" + uuid.uuid4().hex
        tk = self.tk_moi(secret=secret_canary)
        don_id = self.tao_don(tk, "BEST-J1", "MD-J1")
        p = _payload("BEST-J1", "MD-J1", 211, "2026-10-19T15:00:00+07:00",
                     token=canary, password=canary, api_key=canary)
        body = _body(p)
        hd = _ky(tk["secret"], body)
        hd["Authorization"] = "Bearer " + canary
        hd["Cookie"] = "sid=" + canary
        hd["X-Best-Timestamp"] = "2026-10-19T15:00:00+07:00"
        err = io.StringIO()
        import contextlib
        with contextlib.redirect_stderr(err):
            status, raw, _ = _post(tk["wh_ma"], body, hd)
        self.assertEqual(status, 200, raw)
        self.assertNotIn(canary.encode(), raw, "token rò trong response")
        self.assertNotIn(secret_canary.encode(), raw, "secret rò trong response")

        sk = _sk(tk["id"])
        self.assertEqual(len(sk), 1)
        self.assertNotIn(canary.encode(), bytes(sk[0]["payload_tho"]),
                         "token rò trong payload_tho")
        self.assertNotIn(canary.encode(), str(sk[0]["headers_json"]).encode(),
                         "token rò trong headers_json")
        self.assertNotIn(secret_canary.encode(), bytes(sk[0]["payload_tho"]))
        self.assertIn(b"[DA_CHE]", bytes(sk[0]["payload_tho"]),
                      "khóa nhạy cảm phải bị che, không chỉ bị bỏ")
        for truong in ("hang_mo_ta_goc", "hang_su_kien_goc", "loi_cuoi"):
            self.assertNotIn(canary, str(sk[0][truong] or ""), f"token rò trong {truong}")
            self.assertNotIn(secret_canary, str(sk[0][truong] or ""),
                             f"secret rò trong {truong}")
        for r in csdl.nhieu("SELECT noi_dung FROM don_lich_su"):
            self.assertNotIn(canary, r["noi_dung"] or "", "token rò trong lịch sử đơn")
            self.assertNotIn(secret_canary, r["noi_dung"] or "",
                             "secret rò trong lịch sử đơn")
        self.assertNotIn(secret_canary, str(sk[0]["headers_json"]))
        self.assertNotIn(secret_canary, err.getvalue(), "secret rò ra stderr")
        self.assertNotIn(secret_canary, _LOG.getvalue(), "secret rò ra log quan sát")
        hd_luu = json.loads(sk[0]["headers_json"])
        self.assertNotIn("authorization", hd_luu)
        self.assertNotIn("cookie", hd_luu)
        self.assertNotIn("x-webhook-signature", hd_luu)

        for r in csdl.nhieu("SELECT chi_tiet FROM audit"):
            ct = r["chi_tiet"] or ""
            self.assertNotIn(canary, ct, "token rò trong audit")
            self.assertNotIn(secret_canary, ct, "secret rò trong audit")
        self.assertNotIn(canary, err.getvalue(), "token rò ra stderr")
        self.assertNotIn(canary, _LOG.getvalue(), "token rò ra log quan sát")
        self.assertIsNone(_quet_bay(canary), "token rò xuống tệp dữ liệu")
        self.assertIsNone(_quet_bay(secret_canary), "secret rò xuống tệp dữ liệu")


# ============================================================================
# K. CHỐT TÍCH HỢP — nhánh BEST đúng chỗ, không lấy tenant từ payload, LIVE đóng
# ============================================================================
class K_ChotTichHop(Nen):
    def _nguon(self, ten):
        with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
            return f.read()

    def test_k01_nhanh_best_dat_truoc_hmac_va_ack_cua_jt(self):
        n = self._nguon("server.py")
        i_best = n.index('if str(tk["hang"] or "") == "best":')
        i_hmac = n.index("if not webhook.kiem_chu_ky(tk")
        i_ack = n.index("webhook.nhan_su_kien(tk")
        self.assertLess(i_best, i_hmac, "nhánh BEST phải đặt TRƯỚC HMAC J&T")
        self.assertLess(i_best, i_ack, "nhánh BEST phải đặt TRƯỚC ACK/hàng đợi J&T")
        self.assertIn("webhook_best.xu_ly_voi_account(tk, body, self._headers_thuong())", n)
        self.assertNotIn("tenant_id=body", n)
        self.assertNotIn("tenant_id=p.get", n)

    def test_k02_chot_live_va_schema_van_dong(self):
        self.assertFalse(adapter_best.AdapterBEST.CHO_PHEP_LIVE)
        self.assertFalse(adapter_best.AdapterBEST.CHO_PHEP_SANDBOX)
        self.assertFalse(adapter_best.AdapterBEST.CHO_PHEP_PRODUCTION)
        self.assertFalse(adapter_best.AdapterBEST.CHO_PHEP_HTTP_KHONG_MA_HOA)
        self.assertFalse(adapter_best.AdapterBEST.SCHEMA_DA_XAC_MINH)
        self.assertFalse(adapter_best.AdapterBEST.KHOA_CHONG_TRUNG)
        self.assertFalse(adapter_best.TRANG_THAI_DA_XAC_MINH)

    def test_k03_bo_thu_chi_dung_loopback_va_khong_mo_mang_ngoai(self):
        import ast
        self.assertEqual(_SV.server_address[0], "127.0.0.1",
                         "máy chủ phải bind loopback")
        n = self._nguon(os.path.join("thu", "thu_best_e2e_http.py"))
        self.assertIn('ThreadingHTTPServer(("127.0.0.1", 0)', n)
        cay = ast.parse(n)
        ten = set()
        thuoc_tinh = set()
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import):
                ten.update(a.name for a in nut.names)
            elif isinstance(nut, ast.ImportFrom) and nut.module:
                ten.add(nut.module)
            elif isinstance(nut, ast.Attribute):
                thuoc_tinh.add(nut.attr)
            elif isinstance(nut, ast.Name):
                thuoc_tinh.add(nut.id)
            elif isinstance(nut, ast.Constant) and isinstance(nut.value, str):
                self.assertFalse(nut.value.lower().startswith(("ht" + "tp://",
                                                               "http" + "s://")),
                                 f"bộ thử có URL ngoài: {nut.value[:80]!r}")
        for cam in ("requests", "httpx", "urllib.request", "socket"):
            self.assertNotIn(cam, ten, f"bộ thử import thư viện mạng '{cam}'")
        self.assertNotIn("HTTPS" + "Connection", thuoc_tinh)
        self.assertNotIn("url" + "open", thuoc_tinh)


# ============================================================================
# L. TÀI LIỆU BÀN GIAO — phải nói đúng phần CHƯA XÁC MINH
# ============================================================================
class L_TaiLieu(Nen):
    def test_l01_tai_lieu_ban_giao_ghi_ro_hop_dong_chua_xac_minh(self):
        duong = os.path.join(os.path.dirname(GOC_APP), "docs", "BEST_EXPRESS_HTTP_E2E.md")
        self.assertTrue(os.path.exists(duong), "thiếu tài liệu bàn giao E2E")
        with open(duong, encoding="utf-8") as f:
            n = f.read()
        for phai_co in ("CHƯA XÁC MINH", "BEST-09", "BEST-10", "605", "606", "23", "24",
                        "BLOCKED", "thu_best_e2e_http.py"):
            self.assertIn(phai_co, n, f"tài liệu thiếu '{phai_co}'")


if __name__ == "__main__":
    import unittest as _ut
    _ket = _ut.TextTestRunner(verbosity=2).run(_ut.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    print(f"\nCa chạy: {_ket.testsRun} · lỗi: {len(_ket.errors)} · hỏng: "
          f"{len(_ket.failures)} · skip: {len(_ket.skipped)}")
    print("KẾT QUẢ:", "ĐẠT" if _ket.wasSuccessful() else "HỎNG")
    sys.exit(0 if _ket.wasSuccessful() else 1)
