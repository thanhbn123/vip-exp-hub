# -*- coding: utf-8 -*-
"""BỘ THỬ MOCK — xác thực + credential security BEST Express (AGENT B2).

Chạy: python3 app/thu/thu_best_auth.py

PHẠM VI (đọc kỹ trước khi tin con số):
  · Đây là **MOCK PASS**, KHÔNG phải REAL PASS. Không có lời gọi nào tới BEST, kể cả
    sandbox/test host. "Máy chủ" duy nhất là stub loopback 127.0.0.1 do chính bộ thử dựng.
  · Mọi secret dùng trong đây là chuỗi NGẪU NHIÊN sinh lúc chạy, không phải credential thật.
  · Token "đăng nhập" do stub sinh; mốc 30 ngày do module tự tính theo đặc tả đã xác nhận.

NGUYÊN TẮC ĐO (CLAUDE.md §12.1):
  · Mỗi khẳng định do một phép đo thật tạo ra: bộ đếm yêu cầu của stub, nội dung tệp đọc lại,
    bản ghi log thật, hàng audit thật trong SQLite.
  · MỌI CA PHỦ ĐỊNH ĐỀU CÓ ĐỐI CHỨNG DƯƠNG: ví dụ trước khi khẳng định "quét không thấy
    password trong kho", ta cấy một tệp plaintext vào chính thư mục dữ liệu tạm và chứng minh
    ĐÚNG phép quét đó TÌM THẤY nó; trước khi khẳng định "không có token trong log", ta ghi
    một canary khác vào logger và chứng minh bộ quét bắt được.
  · Số ca / số bỏ qua / mã thoát do unittest in ra; cuối file in bảng bằng chứng.

Ghi chú: bộ thử này KHÔNG import server.py/webhook.py/adapter*.py — nó chỉ đo module
`app/xac_thuc_best.py` và hợp đồng `app/bao_mat.py`.
"""

import ast
import datetime
import ipaddress
import json
import logging
import os
import secrets
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import http.server

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# ── CÔ LẬP DỮ LIỆU TRƯỚC KHI IMPORT BẤT KỲ MODULE APP NÀO ───────────────────────────────────
GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_TAM = tempfile.mkdtemp(prefix="vip-hub-best-auth-")
os.environ["VIP_HUB_DATA"] = _TAM
os.environ["VIP_KHO_DANG_CHAY"] = "sqlite"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import bao_mat            # noqa: E402
import cau_hinh           # noqa: E402
import csdl               # noqa: E402
import xac_thuc_best as xb  # noqa: E402

cau_hinh.khai_kho_kiem_thu()

THU_MUC_BEST_AUTH = os.path.join(_TAM, "best_auth")
TEP_CREDENTIAL = os.path.join(THU_MUC_BEST_AUTH, "credential_dang_nhap.enc.json")
TEP_TOKEN = os.path.join(THU_MUC_BEST_AUTH, "token_truy_cap.enc.json")
TEP_BEARER = os.path.join(THU_MUC_BEST_AUTH, "bearer_webhook.enc.json")

PREFIX_TOKEN_GIA = "BEST-TOKEN-GIA-LAP-"


# ============================================================================
# STUB LOOPBACK — "máy chủ BEST" giả, chỉ nằm ở 127.0.0.1
# ============================================================================
class _MayChuGiaLap:
    def __init__(self):
        self.khoa = threading.Lock()
        self.mode = "ok"
        self.tre_giay = 0.0
        self.so_lan_dang_nhap = 0
        self.so_token_da_cap = 0
        self.than_yeu_cau = []
        self.phan_hoi_cuoi = None
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.may_chu = self
        self.cong = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    @property
    def url(self):
        return "http://127.0.0.1:%d" % self.cong

    def bat_dau(self):
        self.thread.start()

    def dung(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def dat_lai(self):
        with self.khoa:
            self.mode = "ok"
            self.tre_giay = 0.0
            self.so_lan_dang_nhap = 0
            self.so_token_da_cap = 0
            self.than_yeu_cau = []
            self.phan_hoi_cuoi = None

    def dat_mode(self, mode, tre_giay=0.0):
        with self.khoa:
            self.mode = mode
            self.tre_giay = float(tre_giay)

    def ghi_nhan(self, path, than, headers):
        with self.khoa:
            self.so_lan_dang_nhap += 1
            self.than_yeu_cau.append({
                "path": path,
                "than": than,
                "headers": {str(k).lower(): str(v) for k, v in headers.items()},
            })
            return self.mode, self.tre_giay

    def cap_token(self):
        with self.khoa:
            self.so_token_da_cap += 1
            return "%s%d-%s" % (PREFIX_TOKEN_GIA, self.so_token_da_cap, secrets.token_urlsafe(12))


class _Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # không in ra stderr — log của stub không phải bằng chứng
        return

    def do_POST(self):
        may = self.server.may_chu
        try:
            do_dai = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            do_dai = 0
        if do_dai < 0 or do_dai > 65536:
            self._tra(413, {"loi": "qua lon"})
            return
        raw = self.rfile.read(do_dai) if do_dai else b""
        try:
            than = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, ValueError):
            self._tra(400, {"loi": "json"})
            return
        mode, tre = may.ghi_nhan(self.path, than, self.headers)
        if tre:
            time.sleep(tre)
        if self.path != "/User/Login":
            self._tra(404, {"loi": "sai duong"})
            return
        if mode == "unauthorized":
            self._tra(401, {"loi": "sai thong tin"})
        elif mode == "server_error":
            self._tra(500, {
                "loi": "may chu loi",
                "password": than.get("Password"),
                "token": "TOKEN-ECHO-TU-LOI-" + secrets.token_hex(8),
            })
        elif mode == "missing_token":
            self._tra(200, {"ok": True})
        elif mode == "token_not_str":
            self._tra(200, {"token": 12345})
        elif mode == "token_too_long":
            self._tra(200, {"token": "A" * 9000})
        elif mode == "huge":
            self._tra(200, {"token": "A" * 70000})
        elif mode == "redirect":
            # Đích chuyển hướng là loopback cổng 1 (chắc chắn không có dịch vụ) — kể cả
            # nếu lớp HTTP ngu ngốc đi theo, nó cũng KHÔNG chạm mạng ngoài.
            self._tra(302, {}, {"Location": "http://127.0.0.1:1/User/Login"})
        else:
            self._tra(200, {"token": may.cap_token()})

    def _tra(self, ma, doi_tuong, headers_them=None):
        du_lieu = json.dumps(doi_tuong, ensure_ascii=False).encode("utf-8")
        with self.server.may_chu.khoa:
            self.server.may_chu.phan_hoi_cuoi = du_lieu
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(du_lieu)))
        self.send_header("Connection", "close")
        for k, v in (headers_them or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(du_lieu)
        except OSError:
            pass
        self.close_connection = True


MAY_CHU = None


def setUpModule():
    global MAY_CHU
    MAY_CHU = _MayChuGiaLap()
    MAY_CHU.bat_dau()
    lg = logging.getLogger("vip.best_auth")
    lg.setLevel(logging.DEBUG)
    lg.propagate = False


def tearDownModule():
    if MAY_CHU is not None:
        MAY_CHU.dung()
    try:
        csdl.dong()
    except Exception:  # noqa: BLE001
        pass
    shutil.rmtree(_TAM, ignore_errors=True)


# ============================================================================
# TIỆN ÍCH ĐO
# ============================================================================
def _quet_thu_muc(goc, kim):
    """Trả đường dẫn tệp ĐẦU TIÊN chứa `kim` (bytes UTF-8), hoặc None.

    Quét NHỊ PHÂN mọi tệp, kể cả SQLite/WAL — không chỉ tệp .json.
    """
    kim_b = kim.encode("utf-8")
    for thu, _ds, ds_tep in os.walk(goc):
        for ten in sorted(ds_tep):
            duong = os.path.join(thu, ten)
            try:
                with open(duong, "rb") as f:
                    if kim_b in f.read():
                        return duong
            except OSError:
                continue
    return None


def _quet_van_ban(van_ban, kim):
    return kim in van_ban


def _tao_chung_chi_tu_ky(thu_muc):
    """Sinh chứng chỉ tự ký cho 127.0.0.1 — dùng để ĐO rằng client TỪ CHỐI cert lạ."""
    khoa = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ten = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.datetime.now(datetime.timezone.utc)
    chung_chi = (
        x509.CertificateBuilder()
        .subject_name(ten)
        .issuer_name(ten)
        .public_key(khoa.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]),
            critical=False,
        )
        .sign(khoa, hashes.SHA256())
    )
    tep_cert = os.path.join(thu_muc, "tls-tu-ky-cert.pem")
    tep_khoa = os.path.join(thu_muc, "tls-tu-ky-key.pem")
    with open(tep_cert, "wb") as f:
        f.write(chung_chi.public_bytes(serialization.Encoding.PEM))
    with open(tep_khoa, "wb") as f:
        f.write(khoa.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
    os.chmod(tep_cert, 0o600)
    os.chmod(tep_khoa, 0o600)
    return tep_cert, tep_khoa


def _doc_json(duong):
    with open(duong, "r", encoding="utf-8") as f:
        return json.load(f)


def _ghi_json(duong, du_lieu):
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False)
    os.chmod(duong, 0o600)


def _ban_ma_cua(duong, tenant, tai_khoan):
    kho = _doc_json(duong)
    return kho["ban_ghi"][tenant][tai_khoan]["ban_ma"]


def _chep_ban_ma(duong, tenant_nguon, tk_nguon, tenant_dich, tk_dich, duong_dich=None):
    """Chép NGUYÊN bản mã từ bản ghi nguồn sang bản ghi đích (có thể khác tệp)."""
    ban_ma = _doc_json(duong)["ban_ghi"][tenant_nguon][tk_nguon]["ban_ma"]
    duong_dich = duong_dich or duong
    kho_dich = _doc_json(duong_dich)
    kho_dich["ban_ghi"].setdefault(tenant_dich, {})[tk_dich] = {
        "ban_ma": ban_ma,
        "cap_nhat_luc": time.time(),
        "phien_ban": 1,
    }
    _ghi_json(duong_dich, kho_dich)


def _xoa_ban_ghi(duong, tenant, tai_khoan):
    kho = _doc_json(duong)
    kho["ban_ghi"].get(tenant, {}).pop(tai_khoan, None)
    _ghi_json(duong, kho)


class _DongHo:
    def __init__(self, now):
        self.now = float(now)

    def __call__(self):
        return self.now


class _CoSo(unittest.TestCase):
    def setUp(self):
        MAY_CHU.dat_lai()
        xb.dat_transport_mac_dinh(None)
        hau_to = secrets.token_hex(5)
        self.tenant = "tenant-thu-" + hau_to
        self.tai_khoan = "BEST-THU-" + hau_to
        self.username = "user-thu-" + hau_to
        self.password = "MK-THU-RAT-DAC-BIET-" + secrets.token_hex(16)
        self.token_da_thay = []

    def tearDown(self):
        xb.dat_transport_mac_dinh(None)

    # ---- helper ----
    def transport(self):
        return xb.TransportDangNhapHTTPS(MAY_CHU.url, cho_phep_loopback=True)

    def luu(self, *, tenant=None, tai_khoan=None, username=None, password=None, dong_ho=None):
        return xb.luu_credential_dang_nhap(
            tenant if tenant is not None else self.tenant,
            tai_khoan if tai_khoan is not None else self.tai_khoan,
            username if username is not None else self.username,
            password if password is not None else self.password,
            dong_ho=dong_ho,
        )

    def lay(self, *, now=None, tenant=None, tai_khoan=None, transport="auto"):
        tr = self.transport() if transport == "auto" else transport
        dong_ho = now if callable(now) else (lambda: now) if now is not None else None
        return xb.lay_token(tenant if tenant is not None else self.tenant,
                            tai_khoan if tai_khoan is not None else self.tai_khoan,
                            transport=tr, dong_ho=dong_ho)

    def lay_va_ghi_nho(self, **kw):
        token = self.lay(**kw)
        self.token_da_thay.append(token)
        return token

    def luu_va_lay(self, *, now=None):
        self.luu()
        return self.lay_va_ghi_nho(now=now)

    def _assert_loi(self, ma, fn, *args, **kwargs):
        with self.assertRaises(xb.LoiXacThucBest) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.ma_loi, ma, "mã lỗi thật: %s" % ctx.exception)
        return ctx.exception

    def _assert_khong_co_secret(self, van_ban, *secrets_can_an):
        for bi_mat in secrets_can_an:
            self.assertNotIn(bi_mat, van_ban,
                             "secret rò rỉ vào văn bản: %r" % bi_mat[:6])

    def _audit_van_ban(self):
        hang = csdl.nhieu("SELECT hanh_dong, chi_tiet, doi_tuong FROM audit")
        return "\n".join("%s|%s|%s" % (r[0], r[1], r[2]) for r in hang)


# ============================================================================
# 01 — KHO: KHÔNG PLAINTEXT, HAI LỚP HAI TỆP, QUYỀN TỆP
# ============================================================================
class Test01_KhoVaPlaintext(_CoSo):
    def test_01_credential_khong_plaintext_trong_toan_bo_kho(self):
        self.luu()
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0, "lưu credential KHÔNG được gọi mạng")

        with open(TEP_CREDENTIAL, "r", encoding="utf-8") as f:
            van_ban = f.read()
        self.assertIn("v3$", van_ban, "bản mã phải là AES-256-GCM có key_id (hợp đồng bao_mat)")
        ban_ma = _doc_json(TEP_CREDENTIAL)["ban_ghi"][self.tenant][self.tai_khoan]["ban_ma"]
        self.assertIsNotNone(bao_mat.key_id_cua(ban_ma), "bản mã phải mang key_id để xoay khóa")
        self.assertNotIn(self.password, van_ban)
        self.assertNotIn(self.username, van_ban)

        # ĐO THẬT: quét nhị phân toàn bộ thư mục dữ liệu (gồm hub.db/WAL nếu có).
        self.assertIsNone(_quet_thu_muc(_TAM, self.password))
        self.assertIsNone(_quet_thu_muc(_TAM, self.username))

        # ĐỐI CHỨNG DƯƠNG: cấy plaintext vào CHÍNH thư mục dữ liệu, phép quét PHẢI thấy.
        tep_doi_chung = os.path.join(_TAM, "doi-chung-plaintext.txt")
        try:
            with open(tep_doi_chung, "w", encoding="utf-8") as f:
                f.write("x=" + self.password)
            self.assertEqual(_quet_thu_muc(_TAM, self.password), tep_doi_chung,
                             "phép quét không phát hiện plaintext đã cấy ⇒ phép đo vô nghĩa")
        finally:
            os.remove(tep_doi_chung)
        self.assertIsNone(_quet_thu_muc(_TAM, self.password))

    def test_02_quyen_tep_va_thu_muc(self):
        self.luu()
        self.assertEqual(stat.S_IMODE(os.stat(THU_MUC_BEST_AUTH).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(TEP_CREDENTIAL).st_mode), 0o600)
        # ĐỐI CHỨNG DƯƠNG: quyền đọc được thật sự (nếu tệp không tồn tại, stat đã nổ).
        self.assertTrue(os.path.isfile(TEP_CREDENTIAL))

    def test_03_hai_lop_hai_tep_rieng(self):
        bearer = "BEARER-WEBHOOK-RAT-DAC-BIET-" + secrets.token_hex(12)
        self.luu()
        xb.luu_bearer_webhook(self.tenant, self.tai_khoan, bearer, webhook_ma="wh-" + secrets.token_hex(4))
        self.assertNotEqual(TEP_CREDENTIAL, TEP_BEARER)
        with open(TEP_CREDENTIAL, "r", encoding="utf-8") as f:
            kho_a = f.read()
        with open(TEP_BEARER, "r", encoding="utf-8") as f:
            kho_b = f.read()
        self.assertIn("v3$", kho_a)
        self.assertIn("v3$", kho_b)
        self.assertNotIn(bearer, kho_a, "Bearer webhook KHÔNG được nằm trong kho credential")
        self.assertNotIn(self.password, kho_b, "Password KHÔNG được nằm trong kho webhook")
        self.assertNotIn(self.username, kho_b)
        # ĐỐI CHỨNG DƯƠNG: hai kho đều đọc được và có đúng một bản ghi.
        self.assertEqual(len(_doc_json(TEP_CREDENTIAL)["ban_ghi"][self.tenant]), 1)
        self.assertEqual(len(_doc_json(TEP_BEARER)["ban_ghi"][self.tenant]), 1)
        self.assertIsNone(_quet_thu_muc(_TAM, bearer))

    def test_04_kho_hong_thi_tu_choi_va_khong_ghi_de(self):
        self.luu()
        with open(TEP_CREDENTIAL, "rb") as f:
            goc = f.read()
        try:
            with open(TEP_CREDENTIAL, "wb") as f:
                f.write(b"{day-khong-phai-json")
            e = self._assert_loi("KHO_HONG", self.lay)
            self.assertEqual(e.http_status, None)
            self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0, "kho hỏng thì KHÔNG được gọi mạng")
            with open(TEP_CREDENTIAL, "rb") as f:
                sau = f.read()
            self.assertEqual(sau, b"{day-khong-phai-json", "module không được ghi đè kho hỏng")
        finally:
            with open(TEP_CREDENTIAL, "wb") as f:
                f.write(goc)
            os.chmod(TEP_CREDENTIAL, 0o600)
        # ĐỐI CHỨNG DƯƠNG: khôi phục xong thì đọc được bình thường.
        self.assertTrue(xb.trang_thai_credential(self.tenant, self.tai_khoan)["doc_duoc"])

    def test_05_token_cache_bi_sua_thi_dang_nhap_lai(self):
        self.luu()
        t0 = 1_700_000_000.0
        token1 = self.lay_va_ghi_nho(now=t0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        # còn hạn ⇒ dùng cache
        self.assertEqual(self.lay(now=t0 + 10), token1)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

        kho = _doc_json(TEP_TOKEN)
        ban_ma = kho["ban_ghi"][self.tenant][self.tai_khoan]["ban_ma"]
        cuoi = ban_ma[-1]
        kho["ban_ghi"][self.tenant][self.tai_khoan]["ban_ma"] = \
            ban_ma[:-1] + ("0" if cuoi != "0" else "1")
        _ghi_json(TEP_TOKEN, kho)

        token2 = self.lay(now=t0 + 20)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2, "cache hỏng ⇒ đăng nhập lại ĐÚNG MỘT lần")
        # ĐỐI CHỨNG DƯƠNG: token mới dùng được từ cache.
        self.assertEqual(self.lay(now=t0 + 30), token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)


# ============================================================================
# 02 — TOKEN KHÔNG XUẤT HIỆN TRONG LOG / RESPONSE / AUDIT (QUÉT THẬT)
# ============================================================================
class Test02_KhongRoRiToken(_CoSo):
    def test_01_token_va_password_khong_trong_log(self):
        """Bắt log thật của CẢ vòng đời: cấp token, làm mới, hủy, rồi cấp lại."""
        canary_log = "CANARY-LOG-DOI-CHUNG-" + secrets.token_hex(10)
        t0 = 1_700_000_000.0
        tokens = []
        with self.assertLogs("vip.best_auth", level="DEBUG") as nhat_ky:
            self.luu()
            tokens.append(self.lay_va_ghi_nho(now=t0))
            tokens.append(xb.lam_moi_token(self.tenant, self.tai_khoan,
                                           token_cu=tokens[-1], transport=self.transport(),
                                           dong_ho=lambda: t0 + 1))
            xb.huy_token(self.tenant, self.tai_khoan, ly_do="THU_LOG")
            tokens.append(self.lay_va_ghi_nho(now=t0 + 2))
            xb.trang_thai_token(self.tenant, self.tai_khoan, dong_ho=lambda: t0 + 2)
            logging.getLogger("vip.best_auth").info("control=%s", canary_log)
        van_ban = "\n".join(nhat_ky.output)
        # ĐỐI CHỨNG DƯƠNG: bộ ghi log bắt được canary ⇒ phép quét log là thật.
        self.assertIn(canary_log, van_ban)
        # Log phải CÓ ÍCH: đúng tên sự kiện/lớp, không bị bộ lọc an toàn biến thành "KHAC".
        self.assertIn("su_kien=token_cap", van_ban)
        self.assertIn("su_kien=token_lam_moi", van_ban)
        self.assertIn("su_kien=token_huy", van_ban)
        self.assertIn("lop=token_truy_cap_best", van_ban)
        self.assertIn("ma_ly_do=OK", van_ban)
        self._assert_khong_co_secret(van_ban, self.password, self.username, *tokens)

    def test_02_response_mo_ta_khong_token(self):
        token = self.luu_va_lay(now=1_700_000_000.0)
        van_ban = json.dumps([
            xb.luu_credential_dang_nhap(self.tenant, self.tai_khoan, self.username, self.password),
            xb.trang_thai_credential(self.tenant, self.tai_khoan),
            xb.trang_thai_token(self.tenant, self.tai_khoan, dong_ho=lambda: 1_700_000_000.0),
            xb.trang_thai_bearer_webhook(self.tenant, self.tai_khoan),
        ], ensure_ascii=False)
        self._assert_khong_co_secret(van_ban, token, self.password, self.username)
        # ĐỐI CHỨNG DƯƠNG: nếu canary CÓ trong dict thì phép quét bắt được.
        self.assertTrue(_quet_van_ban(json.dumps({"x": token}), token))

    def test_03_audit_khong_token(self):
        t0 = 1_700_000_000.0
        token1 = self.luu_va_lay(now=t0)
        token2 = xb.lam_moi_token(self.tenant, self.tai_khoan, token_cu=token1,
                                  transport=self.transport(), dong_ho=lambda: t0 + 1)
        xb.huy_token(self.tenant, self.tai_khoan, ly_do="THU_AUDIT")
        token3 = self.lay_va_ghi_nho(now=t0 + 2)
        self.luu()  # tạo thêm hàng audit
        van_ban = self._audit_van_ban()
        self.assertIn("best_auth.token_cap", van_ban, "audit phải ghi lượt cấp token THẬT")
        self.assertIn("best_auth.token_lam_moi", van_ban)
        self.assertIn("best_auth.token_huy", van_ban)
        self._assert_khong_co_secret(van_ban, self.password, self.username,
                                     token1, token2, token3)

        # ĐỐI CHỨNG DƯƠNG: chèn một canary KHÁC vào audit, phép quét phải thấy.
        canary = "CANARY-AUDIT-DOI-CHUNG-" + secrets.token_hex(10)
        csdl.audit("best_auth.doi_chung", "best_auth:doi-chung",
                   chi_tiet="canary=" + canary, ket_qua="thanh_cong")
        van_ban_2 = self._audit_van_ban()
        self.assertIn(canary, van_ban_2)
        self._assert_khong_co_secret(van_ban_2, self.password, self.username,
                                     token1, token2, token3)

    def test_04_loi_http_khong_echo_secret(self):
        self.luu()
        MAY_CHU.dat_mode("server_error")
        with self.assertLogs("vip.best_auth", level="DEBUG") as nhat_ky:
            e = self._assert_loi("DANG_NHAP_THAT_BAI", self.lay, now=1_700_000_000.0)
        self.assertEqual(e.http_status, 500)
        # ĐỐI CHỨNG DƯƠNG: stub THẬT SỰ đã gửi password + token giả trong thân 500.
        phan_hoi = (MAY_CHU.phan_hoi_cuoi or b"").decode("utf-8")
        self.assertIn(self.password, phan_hoi)
        self.assertIn("TOKEN-ECHO-TU-LOI-", phan_hoi)
        # Nhưng lỗi/log/audit của module KHÔNG được chứa chúng.
        self._assert_khong_co_secret(str(e), self.password, "TOKEN-ECHO-TU-LOI-")
        self._assert_khong_co_secret("\n".join(nhat_ky.output), self.password, "TOKEN-ECHO-TU-LOI-")
        self._assert_khong_co_secret(self._audit_van_ban(), self.password, "TOKEN-ECHO-TU-LOI-")

    def test_05_khong_hardcode_token_va_chi_dung_hop_dong_bao_mat(self):
        with open(os.path.join(GOC_APP, "xac_thuc_best.py"), "r", encoding="utf-8") as f:
            nguon = f.read()
        cay = ast.parse(nguon)
        ten_goi = set()
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute):
                if isinstance(nut.func.value, ast.Name) and nut.func.value.id == "bao_mat":
                    ten_goi.add(nut.func.attr)
        # Hợp đồng §3/§14: chỉ bốn hàm, không gọi mã hóa trần.
        self.assertFalse(ten_goi & {"ma_hoa", "giai_ma", "ma_hoa_v3", "luu_credentials"},
                         "gọi hàm mã hóa NGOÀI hợp đồng: %s" % (ten_goi,))
        self.assertTrue({"ma_hoa_cred", "giai_ma_cred"} <= ten_goi,
                        "phải dùng cặp hàm hợp đồng credential: %s" % (ten_goi,))
        # Không có literal nào giống token/credential thật được nhúng.
        self.assertNotIn(PREFIX_TOKEN_GIA, nguon)
        self.assertNotIn(self.password, nguon)
        # Không in secret ra stdout/stderr — kể cả khi ai đó thêm print lúc gỡ lỗi.
        co_print = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
            for n in ast.walk(cay)
        )
        self.assertFalse(co_print, "module bảo mật không được dùng print()")
        self.assertNotIn("sys.stdout", nguon)
        self.assertNotIn("sys.stderr", nguon)

        # ĐỐI CHỨNG DƯƠNG: bộ dò AST PHẢI bắt được lời gọi trần trong một nguồn giả.
        gia = ast.parse("import bao_mat\nbao_mat.ma_hoa('x')\n")
        bat_duoc = set()
        for nut in ast.walk(gia):
            if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute):
                bat_duoc.add(nut.func.attr)
        self.assertIn("ma_hoa", bat_duoc)
        gia_print = ast.parse("print('secret')\n")
        self.assertTrue(any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print"
            for n in ast.walk(gia_print)
        ))


# ============================================================================
# 03 — THIẾU CREDENTIAL / SAI TENANT / XOAY CREDENTIAL / HAI LỚP
# ============================================================================
class Test03_CredentialVaTenant(_CoSo):
    def test_01_thieu_credential_tu_choi_ro_rang(self):
        e = self._assert_loi("THIEU_CREDENTIAL", self.lay, now=1_700_000_000.0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0, "thiếu credential ⇒ KHÔNG gọi mạng")
        self.assertIn("credential", str(e).lower())
        # ĐỐI CHỨNG DƯƠNG: lưu credential xong thì cùng lượt gọi thành công.
        self.luu()
        token = self.lay(now=1_700_000_000.0)
        self.assertTrue(token.startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

    def test_02_thieu_tenant_thi_deny(self):
        tr = self.transport()
        for tenant_xau in (None, "", "   ", 123, "a" * 200, "tenant\x01x"):
            self._assert_loi("THIEU_TENANT", xb.lay_token, tenant_xau, self.tai_khoan,
                             transport=tr, dong_ho=lambda: 1_700_000_000.0)
        self._assert_loi("THIEU_TENANT", xb.luu_credential_dang_nhap,
                         None, self.tai_khoan, self.username, self.password)
        self._assert_loi("THIEU_TENANT", xb.kiem_bearer_webhook,
                         "", self.tai_khoan, "Bearer x")
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)
        # ĐỐI CHỨNG DƯƠNG: tenant hợp lệ đi qua được bước kiểm tra (lưu thành công).
        self.luu()
        self.assertTrue(xb.trang_thai_credential(self.tenant, self.tai_khoan)["co_credential"])

    def test_03_credential_sai_thi_khong_luu(self):
        for username_xau, password_xau in (
            ("", self.password),
            (self.username, ""),
            (None, self.password),
            (self.username, None),
            (self.username, 12345),
            ("u" * 257, self.password),
            (self.username, "p" * 1025),
            ("user\x00x", self.password),
        ):
            self._assert_loi("CREDENTIAL_KHONG_HOP_LE", xb.luu_credential_dang_nhap,
                             self.tenant, self.tai_khoan, username_xau, password_xau)
        self.assertFalse(xb.trang_thai_credential(self.tenant, self.tai_khoan)["co_credential"])
        # ĐỐI CHỨNG DƯƠNG: credential hợp lệ lưu được.
        self.luu()
        self.assertTrue(xb.trang_thai_credential(self.tenant, self.tai_khoan)["co_credential"])

    def test_04_credential_tenant_a_khong_dung_cho_tenant_b(self):
        self.luu()
        tenant_b = "tenant-b-" + secrets.token_hex(5)
        e = self._assert_loi("THIEU_CREDENTIAL", self.lay,
                             tenant=tenant_b, now=1_700_000_000.0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0,
                         "tenant B không có credential ⇒ KHÔNG được dùng credential tenant A")
        # ĐỐI CHỨNG DƯƠNG: tenant A dùng được chính credential của mình.
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        self.assertIn("credential", str(e).lower())

    def test_05_aad_chan_chep_ban_ma_credential_sang_tenant_b(self):
        self.luu()
        tenant_b = "tenant-b-" + secrets.token_hex(5)
        tai_khoan_b = self.tai_khoan
        _chep_ban_ma(TEP_CREDENTIAL, self.tenant, self.tai_khoan, tenant_b, tai_khoan_b)
        # Bản ghi tồn tại nhưng KHÔNG giải mã được bằng AAD của tenant B.
        e = self._assert_loi("KHONG_DOC_DUOC_CREDENTIAL", self.lay,
                             tenant=tenant_b, now=1_700_000_000.0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)
        self.assertNotIn(self.password, str(e))
        # ĐỐI CHỨNG DƯƠNG: bản gốc của tenant A vẫn giải mã + đăng nhập được.
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

    def test_06_credential_rieng_cua_tenant_b_hoat_dong(self):
        mk_b = "MK-B-RAT-DAC-BIET-" + secrets.token_hex(12)
        tk_b = "BEST-B-" + secrets.token_hex(4)
        tenant_b = "tenant-b-" + secrets.token_hex(6)
        self.luu()
        self.luu(tenant=tenant_b, tai_khoan=tk_b, password=mk_b)
        token_a = self.lay(now=1_700_000_000.0)
        token_b = self.lay(tenant=tenant_b, tai_khoan=tk_b, now=1_700_000_000.0)
        self.assertNotEqual(token_a, token_b)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        # Mỗi lượt đăng nhập phải dùng ĐÚNG password của tenant mình.
        than = [x["than"] for x in MAY_CHU.than_yeu_cau]
        self.assertIn(self.password, [t.get("Password") for t in than])
        self.assertIn(mk_b, [t.get("Password") for t in than])

    def test_07_xoay_credential_vo_hieu_token_cu(self):
        self.luu()
        token1 = self.lay(now=1_700_000_000.0)
        self.assertEqual(self.lay(now=1_700_000_010.0), token1)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        mk_moi = "MK-MOI-RAT-DAC-BIET-" + secrets.token_hex(12)
        self.luu(password=mk_moi)
        st = xb.trang_thai_token(self.tenant, self.tai_khoan, dong_ho=lambda: 1_700_000_020.0)
        self.assertFalse(st["co_ban_ghi"], "đổi credential phải vô hiệu token cache")
        token2 = self.lay(now=1_700_000_020.0)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        self.assertEqual(MAY_CHU.than_yeu_cau[-1]["than"]["Password"], mk_moi)
        # ĐỐI CHỨNG DƯƠNG: token mới được cache và dùng lại.
        self.assertEqual(self.lay(now=1_700_000_030.0), token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)

    def test_08_dung_lan_hai_lop_secret(self):
        # Lấy bản mã Bearer (lớp B) chép vào kho credential (lớp A).
        bearer = "BEARER-LOP-B-" + secrets.token_hex(16)
        tk2 = "BEST-LOP-B-" + secrets.token_hex(4)
        self.luu(tai_khoan=self.tai_khoan)                       # credential thật cho tk1
        xb.luu_bearer_webhook(self.tenant, tk2, bearer)          # bearer thật cho tk2
        _chep_ban_ma(TEP_BEARER, self.tenant, tk2, self.tenant, tk2,
                     duong_dich=TEP_CREDENTIAL)
        e = self._assert_loi("SAI_LOP_SECRET", self.lay, tai_khoan=tk2, now=1_700_000_000.0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)

        # Chiều ngược lại: chép bản mã credential vào kho Bearer.
        _chep_ban_ma(TEP_CREDENTIAL, self.tenant, self.tai_khoan, self.tenant, self.tai_khoan,
                     duong_dich=TEP_BEARER)
        kq = xb.kiem_bearer_webhook(self.tenant, self.tai_khoan, "Bearer " + self.password)
        self.assertFalse(kq.hop_le)
        self.assertEqual(kq.ma_ly_do, "SAI_LOP_SECRET")

        # ĐỐI CHỨNG DƯƠNG: mỗi lớp, dùng ĐÚNG kho của nó, vẫn hoạt động.
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        bearer2 = "BEARER-LOP-B-2-" + secrets.token_hex(16)
        tk3 = "BEST-LOP-B-2-" + secrets.token_hex(4)
        xb.luu_bearer_webhook(self.tenant, tk3, bearer2)
        self.assertTrue(xb.kiem_bearer_webhook(self.tenant, tk3, "Bearer " + bearer2).hop_le)

    def test_09_password_unicode_va_khoang_trang_van_luu_duoc(self):
        """Password là dữ liệu MỜ: không được tự thu hẹp bảng chữ khi chưa có đặc tả."""
        mk = "Mật khẩu có dấu và khoảng trắng " + secrets.token_hex(6)
        self.luu(password=mk)
        token = self.lay(now=1_700_000_000.0)
        self.assertTrue(token.startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.than_yeu_cau[-1]["than"]["Password"], mk)
        # ĐỐI CHỨNG DƯƠNG ở trên; dưới đây là khẳng định không plaintext.
        with open(TEP_CREDENTIAL, "r", encoding="utf-8") as f:
            self.assertNotIn(mk, f.read())
        self.assertIsNone(_quet_thu_muc(_TAM, mk))


# ============================================================================
# 04 — BEARER WEBHOOK (LỚP B)
# ============================================================================
class Test04_BearerWebhook(_CoSo):
    def setUp(self):
        super().setUp()
        self.bearer = "BEARER-WEBHOOK-RAT-DAC-BIET-" + secrets.token_hex(16)
        self.webhook_ma = "wh-" + secrets.token_hex(6)
        xb.luu_bearer_webhook(self.tenant, self.tai_khoan, self.bearer,
                              webhook_ma=self.webhook_ma)

    def _kiem(self, header, **kw):
        return xb.kiem_bearer_webhook(self.tenant, self.tai_khoan, header, **kw)

    def test_01_bearer_hop_le_va_khong_hop_le(self):
        self.assertTrue(self._kiem("Bearer " + self.bearer).hop_le)
        # ĐỐI CHỨNG DƯƠNG ở trên; dưới đây là các ca phủ định, mỗi ca có mã lý do riêng.
        self.assertEqual(self._kiem("bearer " + self.bearer).ma_ly_do, "OK")
        self.assertEqual(self._kiem("  Bearer   " + self.bearer + "  ").ma_ly_do, "OK")
        self.assertEqual(self._kiem("Bearer " + self.bearer + "x").ma_ly_do, "BEARER_KHONG_KHOP")
        self.assertEqual(self._kiem(self.bearer).ma_ly_do, "SAI_DINH_DANG_BEARER")
        self.assertEqual(self._kiem("Basic " + self.bearer).ma_ly_do, "SAI_DINH_DANG_BEARER")
        self.assertEqual(self._kiem("Bearer ").ma_ly_do, "SAI_DINH_DANG_BEARER")
        self.assertEqual(self._kiem(None).ma_ly_do, "THIEU_HEADER")
        self.assertEqual(self._kiem("").ma_ly_do, "THIEU_HEADER")
        self.assertEqual(self._kiem("Bearer " + "A" * 9000).ma_ly_do, "HEADER_QUA_DAI")
        self.assertEqual(self._kiem("Bearer " + self.bearer + "\nX: y").ma_ly_do,
                         "SAI_DINH_DANG_BEARER")

    def test_02_bearer_tenant_a_khong_dung_cho_tenant_b(self):
        tenant_b = "tenant-b-" + secrets.token_hex(5)
        kq = xb.kiem_bearer_webhook(tenant_b, self.tai_khoan, "Bearer " + self.bearer)
        self.assertFalse(kq.hop_le)
        self.assertEqual(kq.ma_ly_do, "KHONG_CO_BEARER_DA_LUU")
        # Chép bản mã A → B: AAD/AAD tenant khác ⇒ giải mã hỏng, KHÔNG được coi là khớp.
        _chep_ban_ma(TEP_BEARER, self.tenant, self.tai_khoan, tenant_b, self.tai_khoan)
        kq2 = xb.kiem_bearer_webhook(tenant_b, self.tai_khoan, "Bearer " + self.bearer)
        self.assertFalse(kq2.hop_le)
        self.assertEqual(kq2.ma_ly_do, "KHONG_DOC_DUOC_BEARER")
        # ĐỐI CHỨNG DƯƠNG: tenant A vẫn xác thực đúng.
        self.assertTrue(self._kiem("Bearer " + self.bearer).hop_le)

    def test_03_webhook_ma_binding(self):
        self.assertTrue(self._kiem("Bearer " + self.bearer, webhook_ma=self.webhook_ma).hop_le)
        kq = self._kiem("Bearer " + self.bearer, webhook_ma="wh-khac")
        self.assertFalse(kq.hop_le)
        self.assertEqual(kq.ma_ly_do, "DU_LIEU_KHONG_KHOP")

    def test_04_bearer_khong_ro_ri_qua_status(self):
        van_ban = json.dumps([
            xb.trang_thai_bearer_webhook(self.tenant, self.tai_khoan),
            xb.trang_thai_credential(self.tenant, self.tai_khoan),
            xb.trang_thai_token(self.tenant, self.tai_khoan),
            xb.luu_bearer_webhook(self.tenant, self.tai_khoan, self.bearer,
                                  webhook_ma=self.webhook_ma),
            repr(self._kiem("Bearer sai-hoan-toan")),
        ], ensure_ascii=False)
        self._assert_khong_co_secret(van_ban, self.bearer)
        # ĐỐI CHỨNG DƯƠNG: nếu bearer CÓ trong dict thì phép quét bắt được.
        self.assertTrue(_quet_van_ban(json.dumps({"bearer": self.bearer}), self.bearer))

    def test_05_bearer_bi_sua_thi_tu_choi(self):
        with open(TEP_BEARER, "rb") as f:
            goc = f.read()
        try:
            kho = _doc_json(TEP_BEARER)
            ban_ma = kho["ban_ghi"][self.tenant][self.tai_khoan]["ban_ma"]
            cuoi = ban_ma[-1]
            kho["ban_ghi"][self.tenant][self.tai_khoan]["ban_ma"] = \
                ban_ma[:-1] + ("0" if cuoi != "0" else "1")
            _ghi_json(TEP_BEARER, kho)
            kq = self._kiem("Bearer " + self.bearer)
            self.assertFalse(kq.hop_le)
            self.assertIn(kq.ma_ly_do, ("KHONG_DOC_DUOC_BEARER", "BEARER_KHONG_KHOP"))
        finally:
            with open(TEP_BEARER, "wb") as f:
                f.write(goc)
            os.chmod(TEP_BEARER, 0o600)
        # ĐỐI CHỨNG DƯƠNG: khôi phục thì xác thực đúng trở lại.
        self.assertTrue(self._kiem("Bearer " + self.bearer).hop_le)

    def test_06_bearer_khong_goi_mang(self):
        self._kiem("Bearer " + self.bearer)
        self._kiem("Bearer sai")
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0, "xác thực webhook không được gọi mạng")


# ============================================================================
# 05 — VÒNG ĐỜI TOKEN: CACHE · HẾT HẠN · ĐỒNG THỜI · LÀM MỚI CÓ KIỂM SOÁT
# ============================================================================
class Test05_VongDoiToken(_CoSo):
    def test_01_han_30_ngay_va_cache(self):
        self.assertEqual(xb.HAN_TOKEN_GIAY, 30 * 24 * 60 * 60)
        self.luu()
        t0 = 1_700_000_000.0
        token1 = self.lay_va_ghi_nho(now=t0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

        # ĐO THẬT: token đã cache KHÔNG được nằm plaintext trong bất kỳ tệp dữ liệu nào.
        self.assertIsNone(_quet_thu_muc(_TAM, token1))
        with open(TEP_TOKEN, "r", encoding="utf-8") as f:
            self.assertNotIn(token1, f.read())
        # ĐỐI CHỨNG DƯƠNG: cấy token plaintext vào chính thư mục dữ liệu ⇒ phép quét PHẢI thấy.
        tep_doi_chung = os.path.join(_TAM, "doi-chung-token-plain.txt")
        try:
            with open(tep_doi_chung, "w", encoding="utf-8") as f:
                f.write("token=" + token1)
            self.assertEqual(_quet_thu_muc(_TAM, token1), tep_doi_chung,
                             "phép quét token không hoạt động ⇒ phép đo vô nghĩa")
        finally:
            os.remove(tep_doi_chung)
        self.assertIsNone(_quet_thu_muc(_TAM, token1))

        self.assertEqual(self.lay(now=t0 + 1), token1)
        self.assertEqual(self.lay(now=t0 + xb.HAN_TOKEN_GIAY - 1), token1)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1, "còn hạn ⇒ KHÔNG đăng nhập lại")
        st = xb.trang_thai_token(self.tenant, self.tai_khoan,
                                 dong_ho=lambda: t0 + xb.HAN_TOKEN_GIAY - 1)
        self.assertTrue(st["con_han"])
        self.assertNotIn(token1, json.dumps(st))

        token2 = self.lay(now=t0 + xb.HAN_TOKEN_GIAY)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2, "đúng mốc hết hạn ⇒ làm mới ĐÚNG MỘT lần")
        self.assertIsNone(_quet_thu_muc(_TAM, token2), "token làm mới cũng không được plaintext")
        self.assertEqual(self.lay(now=t0 + xb.HAN_TOKEN_GIAY + 1), token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        st2 = xb.trang_thai_token(self.tenant, self.tai_khoan,
                                  dong_ho=lambda: t0 + xb.HAN_TOKEN_GIAY)
        self.assertTrue(st2["con_han"])
        self.assertGreater(st2["het_han_luc"], t0 + xb.HAN_TOKEN_GIAY)

    def test_02_nhieu_thread_dong_thoi_chi_dang_nhap_mot_lan(self):
        self.luu()
        t0 = 1_700_000_000.0
        self.lay(now=t0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        MAY_CHU.dat_mode("ok", tre_giay=0.20)
        dong_ho = _DongHo(t0 + xb.HAN_TOKEN_GIAY + 1)
        so_thread = 16
        rao = threading.Barrier(so_thread)
        ket_qua = []
        loi = []
        khoa = threading.Lock()

        def viec():
            try:
                rao.wait(timeout=10)
                token = xb.lay_token(self.tenant, self.tai_khoan,
                                     transport=self.transport(), dong_ho=dong_ho)
                with khoa:
                    ket_qua.append(token)
            except Exception as e:  # noqa: BLE001
                with khoa:
                    loi.append(repr(e))

        ds = [threading.Thread(target=viec) for _ in range(so_thread)]
        for t in ds:
            t.start()
        for t in ds:
            t.join(timeout=20)
            self.assertFalse(t.is_alive(), "thread treo")
        self.assertEqual(loi, [])
        self.assertEqual(len(ket_qua), so_thread)
        self.assertEqual(len(set(ket_qua)), 1, "mọi thread phải nhận cùng token")
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2,
                         "16 thread cùng hết hạn ⇒ CHỈ MỘT lượt đăng nhập thêm")

    def test_03_nhieu_tien_trinh_dong_thoi_chi_dang_nhap_mot_lan(self):
        self.luu()
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)
        MAY_CHU.dat_mode("ok", tre_giay=0.40)
        ma = r'''
import os, sys, time
sys.path.insert(0, os.environ["BEST_GOC_APP"])
import xac_thuc_best as xb
bat_dau = float(os.environ["BEST_BAT_DAU"])
while time.time() < bat_dau:
    time.sleep(0.005)
tr = xb.TransportDangNhapHTTPS(os.environ["BEST_STUB_URL"], cho_phep_loopback=True)
token = xb.lay_token(os.environ["BEST_TENANT"], os.environ["BEST_TAI_KHOAN"], transport=tr)
assert isinstance(token, str) and token
print("OK")
'''
        bat_dau = time.time() + 2.0
        env = os.environ.copy()
        env.update({
            "BEST_GOC_APP": GOC_APP,
            "BEST_STUB_URL": MAY_CHU.url,
            "BEST_TENANT": self.tenant,
            "BEST_TAI_KHOAN": self.tai_khoan,
            "BEST_BAT_DAU": repr(bat_dau),
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        ds = []
        try:
            ds = [subprocess.Popen([sys.executable, "-c", ma], env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                  for _ in range(3)]
            for p in ds:
                out, err = p.communicate(timeout=40)
                self.assertEqual(p.returncode, 0, "tiến trình con hỏng: %s" % err[-800:])
                self.assertIn("OK", out)
                self.assertNotIn(PREFIX_TOKEN_GIA, out + err, "token không được in ra stdout/stderr")
        finally:
            for p in ds:
                if p.poll() is None:
                    p.kill()
                    try:
                        p.wait(timeout=5)
                    except Exception:  # noqa: BLE001
                        pass
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1,
                         "3 tiến trình cùng hết hạn ⇒ CHỈ MỘT lượt đăng nhập")
        st = xb.trang_thai_token(self.tenant, self.tai_khoan)
        self.assertTrue(st["con_han"])

    def test_04_lam_moi_co_kiem_soat_sau_401(self):
        self.luu()
        t0 = 1_700_000_000.0
        token1 = self.lay(now=t0)
        tr = self.transport()
        token2 = xb.lam_moi_token(self.tenant, self.tai_khoan, token_cu=token1,
                                  transport=tr, dong_ho=lambda: t0 + 1)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        # "Bão 401": tiến trình khác đã làm mới xong; token_cu cũ ⇒ KHÔNG đăng nhập lần nữa.
        token3 = xb.lam_moi_token(self.tenant, self.tai_khoan, token_cu=token1,
                                  transport=tr, dong_ho=lambda: t0 + 2)
        self.assertEqual(token3, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        # Hủy token ⇒ lượt sau đăng nhập lại.
        self.assertTrue(xb.huy_token(self.tenant, self.tai_khoan, ly_do="THU_NGHIEM"))
        self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan)["co_ban_ghi"])
        self.assertNotEqual(self.lay(now=t0 + 3), token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 3)

    def test_05_loi_dang_nhap_khong_cache_va_thu_lai_duoc(self):
        self.luu()
        MAY_CHU.dat_mode("unauthorized")
        self._assert_loi("DANG_NHAP_THAT_BAI", self.lay, now=1_700_000_000.0)
        self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan)["co_ban_ghi"])
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        MAY_CHU.dat_mode("ok")
        token = self.lay(now=1_700_000_000.0)
        self.assertTrue(token.startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        # ĐỐI CHỨNG DƯƠNG: sau thành công, cache hoạt động.
        self.assertEqual(self.lay(now=1_700_000_001.0), token)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)

    def test_06_dong_ho_lui_thi_lam_moi(self):
        self.luu()
        t0 = 1_700_000_000.0
        token1 = self.lay(now=t0)
        token2 = self.lay(now=t0 - 10_000)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2,
                         "đồng hồ lùi bất thường ⇒ không tin mốc hạn cũ, làm mới")

    def test_08_token_cache_khong_dung_cheo_tai_khoan(self):
        """AAD buộc tenant+hãng, KHÔNG buộc tài khoản; phần bên trong bản mã phải tự buộc."""
        tk_a = "BEST-A-" + secrets.token_hex(4)
        tk_b = "BEST-B-" + secrets.token_hex(4)
        mk_b = "MK-B-" + secrets.token_hex(12)
        self.luu(tai_khoan=tk_a)
        self.luu(tai_khoan=tk_b, password=mk_b)
        token_a = self.lay(tai_khoan=tk_a, now=1_700_000_000.0)
        # Chép NGUYÊN bản mã token của A sang bản ghi B (cùng tenant ⇒ AAD vẫn đúng).
        _chep_ban_ma(TEP_TOKEN, self.tenant, tk_a, self.tenant, tk_b)
        token_b = self.lay(tai_khoan=tk_b, now=1_700_000_000.0)
        self.assertNotEqual(token_a, token_b, "token của A không được dùng cho B")
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        self.assertEqual(MAY_CHU.than_yeu_cau[-1]["than"]["Password"], mk_b)
        # ĐỐI CHỨNG DƯƠNG: token B sau đó dùng lại từ cache, không đăng nhập thêm.
        self.assertEqual(self.lay(tai_khoan=tk_b, now=1_700_000_001.0), token_b)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)

    def test_09_lam_moi_that_bai_khong_de_token_cu_trong_cache(self):
        """Token vừa bị 401 phải bị xóa TRƯỚC khi thử đăng nhập; login hỏng thì cache rỗng."""
        self.luu()
        t0 = 1_700_000_000.0
        token1 = self.lay(now=t0)
        tr = self.transport()
        MAY_CHU.dat_mode("unauthorized")
        e = self._assert_loi("DANG_NHAP_THAT_BAI", xb.lam_moi_token,
                             self.tenant, self.tai_khoan,
                             token_cu=token1, transport=tr, dong_ho=lambda: t0 + 1)
        self.assertNotIn(token1, str(e))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)
        self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan,
                                             dong_ho=lambda: t0 + 1)["co_ban_ghi"],
                         "login hỏng sau 401 KHÔNG được để token chết trong cache")
        # ĐỐI CHỨNG DƯƠNG: khi BEST hoạt động lại, lay_token phải đăng nhập mới, không trả token chết.
        MAY_CHU.dat_mode("ok")
        token2 = self.lay(now=t0 + 2)
        self.assertNotEqual(token1, token2)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 3)

    def test_10_credential_doi_giua_dang_nhap_thi_tu_choi(self):
        """Token vừa lấy thuộc credential CŨ ⇒ không được trả ra; lượt sau dùng credential mới."""
        self.luu()
        t0 = 1_700_000_000.0
        mk_moi = "MK-MOI-GIUA-CHUNG-" + secrets.token_hex(10)
        da_goi = []
        tenant, tai_khoan, username = self.tenant, self.tai_khoan, self.username

        class _Xoay:
            def dang_nhap(self, username_nhan, password):
                da_goi.append(password)
                # Mô phỏng lượt đổi credential rơi ĐÚNG giữa lúc gọi mạng.
                xb.luu_credential_dang_nhap(tenant, tai_khoan, username, mk_moi)
                return "BEST-TOKEN-XOAY-" + "A" * 8

        e = self._assert_loi("CREDENTIAL_DA_DOI_KHONG_LUU", self.lay,
                             now=t0, transport=_Xoay())
        self.assertEqual(da_goi, [self.password])
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)
        self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan,
                                             dong_ho=lambda: t0 + 1)["co_ban_ghi"])
        self._assert_khong_co_secret(str(e), self.password, mk_moi)
        # ĐỐI CHỨNG DƯƠNG: credential mới đăng nhập được và được dùng đúng.
        token = self.lay(now=t0 + 2)
        self.assertTrue(token.startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.than_yeu_cau[-1]["than"]["Password"], mk_moi)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

    def test_11_huy_token_thang_luot_dang_nhap_dang_chay(self):
        """huy_token phải khóa theo cặp, nếu không login đang chạy sẽ ghi lại token sau khi hủy."""
        self.luu()

        class _Cham:
            def __init__(self):
                self.da_vao = threading.Event()
                self.cho = threading.Event()
                self.so_lan = 0

            def dang_nhap(self, username, password):
                self.so_lan += 1
                self.da_vao.set()
                self.cho.wait(timeout=5)
                return "BEST-TOKEN-CHAM-" + "A" * 8

        tr = _Cham()
        ket_qua = []
        loi = []

        def viec():
            try:
                ket_qua.append(xb.lay_token(self.tenant, self.tai_khoan, transport=tr))
            except Exception as e:  # noqa: BLE001
                loi.append(repr(e))

        t = threading.Thread(target=viec)
        t.start()
        bo_hen = None
        try:
            self.assertTrue(tr.da_vao.wait(timeout=5), "transport chưa được gọi")
            bo_hen = threading.Timer(0.2, tr.cho.set)
            bo_hen.start()
            # Nếu huy_token chỉ lấy khóa ghi toàn cục, nó xóa cache (đang rỗng) rồi thoát;
            # lượt login đang chạy sau đó ghi token ⇒ token tưởng hủy vẫn sống.
            xb.huy_token(self.tenant, self.tai_khoan, ly_do="THU_DUA")
            t.join(timeout=10)
        finally:
            tr.cho.set()
            t.join(timeout=5)
            if bo_hen is not None:
                bo_hen.join(timeout=1)
        self.assertFalse(t.is_alive(), "thread treo")
        self.assertEqual(loi, [])
        self.assertEqual(len(ket_qua), 1)
        self.assertEqual(tr.so_lan, 1)
        self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan)["co_ban_ghi"],
                         "hủy token phải thắng lượt đăng nhập đang chạy")
        # ĐỐI CHỨNG DƯƠNG: cache đã bị hủy thật ⇒ lượt sau phải đăng nhập lại.
        token2 = xb.lay_token(self.tenant, self.tai_khoan, transport=tr)
        self.assertTrue(token2.startswith("BEST-TOKEN-CHAM-"))
        self.assertEqual(tr.so_lan, 2)

    def test_07_het_han_nhieu_luot_lien_tiep_chi_mot_lan(self):
        self.luu()
        t0 = 1_700_000_000.0
        self.lay(now=t0)
        het = t0 + xb.HAN_TOKEN_GIAY
        ds = [self.lay(now=het) for _ in range(5)]
        self.assertEqual(len(set(ds)), 1)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)


# ============================================================================
# 06 — TRANSPORT: ĐẶC TẢ REQUEST · TLS · LỖI AN TOÀN · REDIRECT
# ============================================================================
class Test06_Transport(_CoSo):
    def test_01_url_validation(self):
        self._assert_loi("HTTP_KHONG_DUOC_PHEP", xb.TransportDangNhapHTTPS,
                         "http://example.com")
        self._assert_loi("HTTP_KHONG_DUOC_PHEP", xb.TransportDangNhapHTTPS,
                         "http://127.0.0.1:1234")
        # ĐỐI CHỨNG DƯƠNG: loopback + cờ kiểm thử thì dựng được.
        tr = xb.TransportDangNhapHTTPS(MAY_CHU.url, cho_phep_loopback=True)
        self.assertTrue(tr._base_url.startswith("http://127.0.0.1:"))
        for url_xau in ("ftp://example.com", "https://user:pass@example.com",
                        "https://example.com/api", "https://example.com?x=1",
                        "https://example.com#f", "https://example.com:abc", "", None):
            self._assert_loi("URL_KHONG_HOP_LE", xb.TransportDangNhapHTTPS, url_xau)
        self._assert_loi("THAM_SO_KHONG_HOP_LE", xb.TransportDangNhapHTTPS,
                         "https://example.com", thoi_gian_cho_giay=0)

    def test_02_tls_khong_bi_ha(self):
        tr = xb.TransportDangNhapHTTPS("https://example.com")
        self.assertEqual(tr._ngu_canh.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(tr._ngu_canh.check_hostname)
        # ĐỐI CHỨNG DƯƠNG: context thật sự dùng được để mở kết nối (không phải None).
        self.assertTrue(hasattr(tr._ngu_canh, "wrap_socket"))

    def test_03_request_dung_dac_ta_da_xac_nhan(self):
        self.luu()
        token = self.lay(now=1_700_000_000.0)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        yeu_cau = MAY_CHU.than_yeu_cau[-1]
        self.assertEqual(yeu_cau["path"], "/User/Login")
        self.assertEqual(set(yeu_cau["than"].keys()), {"Username", "Password"})
        self.assertEqual(yeu_cau["than"]["Username"], self.username)
        self.assertEqual(yeu_cau["than"]["Password"], self.password)
        self.assertNotIn("authorization", yeu_cau["headers"])
        self.assertIn("application/json", yeu_cau["headers"].get("content-type", ""))
        self.assertNotIn(token, json.dumps(yeu_cau["than"]))
        # ĐỐI CHỨNG DƯƠNG: phản hồi có token thật và được module chấp nhận.
        self.assertTrue(token.startswith(PREFIX_TOKEN_GIA))

    def test_04_phan_hoi_sai_dac_ta(self):
        self.luu()
        for mode, ma in (
            ("missing_token", "PHAN_HOI_KHONG_HOP_LE"),
            ("token_not_str", "TOKEN_KHONG_HOP_LE"),
            ("token_too_long", "TOKEN_KHONG_HOP_LE"),
            ("huge", "PHAN_HOI_QUA_LON"),
        ):
            MAY_CHU.dat_mode(mode)
            e = self._assert_loi(ma, self.lay, now=1_700_000_000.0)
            self.assertNotIn(self.password, str(e))
            self.assertFalse(xb.trang_thai_token(self.tenant, self.tai_khoan)["co_ban_ghi"])
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 4)
        # ĐỐI CHỨNG DƯƠNG: phản hồi đúng thì đăng nhập thành công.
        MAY_CHU.dat_mode("ok")
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 5)

    def test_05_http_error_khong_ro_ri(self):
        self.luu()
        for mode, status in (("unauthorized", 401), ("server_error", 500)):
            MAY_CHU.dat_mode(mode)
            e = self._assert_loi("DANG_NHAP_THAT_BAI", self.lay, now=1_700_000_000.0)
            self.assertEqual(e.http_status, status)
            self._assert_khong_co_secret(str(e), self.password, "TOKEN-ECHO-TU-LOI-")
        # ĐỐI CHỨNG DƯƠNG: lỗi được phân loại bằng mã HTTP thật, không bằng chữ trong body.
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 2)

    def test_06_redirect_bi_chan(self):
        self.luu()
        MAY_CHU.dat_mode("redirect")
        e = self._assert_loi("DANG_NHAP_THAT_BAI", self.lay, now=1_700_000_000.0)
        self.assertEqual(e.http_status, 302)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1,
                         "không được gửi lại credential sang đích chuyển hướng")

    def test_07_chua_cau_hinh_transport_thi_tu_choi(self):
        self.luu()
        xb.dat_transport_mac_dinh(None)
        self._assert_loi("CHUA_CAU_HINH_TRANSPORT", self.lay, transport=None)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0, "chưa cấu hình ⇒ KHÔNG gọi mạng")
        # ĐỐI CHỨNG DƯƠNG: đặt transport tường minh thì chạy.
        xb.dat_transport_mac_dinh(self.transport())
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)

    def test_08_transport_sai_giao_dien(self):
        self._assert_loi("TRANSPORT_KHONG_HOP_LE", xb.dat_transport_mac_dinh, object())
        self.luu()
        self._assert_loi("TRANSPORT_KHONG_HOP_LE", self.lay, transport=object())
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)

    def test_09_token_tra_ve_duoc_kiem_tra_lai(self):
        self.luu()
        self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
        self.assertTrue(all(t.startswith(PREFIX_TOKEN_GIA) for t in [self.lay(now=1_700_000_001.0)]))

    def test_10_transport_doc_hai_khong_nhet_secret_vao_loi(self):
        """Transport là biên tin cậy: mã lỗi lạ không được đi vào exception/log/audit."""
        self.luu()
        canary = "TOKEN-MA-LOI-LA-" + secrets.token_hex(10)
        da_goi = []

        class _TransportDocHai:
            def dang_nhap(self, username, password):
                da_goi.append(canary)
                raise xb.LoiXacThucBest(canary)

        with self.assertLogs("vip.best_auth", level="DEBUG") as nhat_ky:
            e = self._assert_loi("TRANSPORT_LOI", self.lay,
                                 now=1_700_000_000.0, transport=_TransportDocHai())
        # ĐỐI CHỨNG DƯƠNG: transport THẬT SỰ đã được gọi và ném mã chứa canary.
        self.assertEqual(da_goi, [canary], "transport giả chưa hề được gọi ⇒ ca đo vô nghĩa")
        self._assert_khong_co_secret(str(e), canary)
        self._assert_khong_co_secret("\n".join(nhat_ky.output), canary, self.password)
        self._assert_khong_co_secret(self._audit_van_ban(), canary, self.password)
        self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0)

    def test_11_tls_tu_choi_chung_chi_tu_ky(self):
        """ĐO THẬT bằng handshake TLS: cert tự ký phải bị từ chối trước khi gửi credential.

        Ca test_02 chỉ kiểm thuộc tính SSLContext — một handler bị thay bằng context không
        xác minh vẫn có thể lọt. Ở đây client thật sự bắt tay với server loopback dùng cert
        tự ký; nếu xác minh chứng chỉ bị tắt, request sẽ đi qua và ca này HỎNG.
        """
        self.luu()
        tep_cert, tep_khoa = _tao_chung_chi_tu_ky(_TAM)
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        httpd.may_chu = MAY_CHU
        httpd.handle_error = lambda *a, **k: None
        ngu_canh = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ngu_canh.load_cert_chain(tep_cert, tep_khoa)
        cong = httpd.server_address[1]
        httpd.socket = ngu_canh.wrap_socket(httpd.socket, server_side=True)
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        try:
            tls_url = "https://127.0.0.1:%d" % cong
            tr = xb.TransportDangNhapHTTPS(tls_url, thoi_gian_cho_giay=3)
            e = self._assert_loi("KHONG_KET_NOI_DUOC", self.lay,
                                 now=1_700_000_000.0, transport=tr)
            self._assert_khong_co_secret(str(e), self.password)
            self.assertEqual(MAY_CHU.so_lan_dang_nhap, 0,
                             "TLS phải hỏng TRƯỚC khi credential được gửi")
            # ĐỐI CHỨNG DƯƠNG: cùng module, cùng payload, chỉ khác HTTP loopback ⇒ đăng nhập được.
            self.assertTrue(self.lay(now=1_700_000_000.0).startswith(PREFIX_TOKEN_GIA))
            self.assertEqual(MAY_CHU.so_lan_dang_nhap, 1)
        finally:
            httpd.shutdown()
            httpd.server_close()
            th.join(timeout=5)
            for duong in (tep_cert, tep_khoa):
                if os.path.exists(duong):
                    os.remove(duong)


# ============================================================================
# IN BẢNG BẰNG CHỨNG — chỉ in PASS khi unittest thật sự đạt
# ============================================================================
if __name__ == "__main__":
    chuong_trinh = unittest.main(exit=False, verbosity=2)
    kq = chuong_trinh.result
    so_ca = kq.testsRun
    so_skip = len(kq.skipped)
    so_hong = len(kq.failures) + len(kq.errors)
    print("")
    print("════════════ BẰNG CHỨNG MOCK · xac_thuc_best ════════════")
    if kq.wasSuccessful():
        print("MOCK PASS — KHÔNG PHẢI REAL PASS (không gọi BEST, không credentials thật)")
    else:
        print("MOCK FAIL — không được dùng con số này để kết luận")
    print("Số ca: %d · Bỏ qua: %d · Hỏng: %d" % (so_ca, so_skip, so_hong))
    if kq.wasSuccessful():
        print("Quét token/password trong log + response + audit: KHÔNG THẤY")
        print("Quét plaintext trong toàn bộ thư mục dữ liệu: KHÔNG THẤY")
        print("(cả hai phép quét đều có ĐỐI CHỨNG DƯƠNG — xem Test01/Test02)")
    print("═════════════════════════════════════════════════════════")
    sys.exit(0 if kq.wasSuccessful() else 1)
