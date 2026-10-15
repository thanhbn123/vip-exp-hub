# Bộ thử G06 — Multi-Tenant Webhook Gateway (AG-03). File RIÊNG của AG-03, không giẫm chân
# thu_saas.py / thu_g03.py / thu_qa_soat.py.
#
# Cố ý KHÔNG mở máy chủ HTTP: cả vault đang có nhiều phiên chạy song song, cổng bận là chuyện
# thường và nó biến bộ thử thành thứ báo hỏng giả (§12.1 — thứ dùng để kiểm chứng phải tự nó
# đáng tin). Mọi ca ở đây gọi thẳng vào hàm, kể cả hàm mà tầng HTTP gọi (`kiem_chu_ky`).
#
# Nhóm:
#   A. Xác thực theo từng hãng (W02/W03)
#   B. Resolve tenant + chống chéo tenant (W02)
#   C. Chống trùng + định danh sự kiện bền (W04)
#   D. Sai thứ tự: thứ hạng + MỐC THỜI GIAN CỦA HÃNG (W05)
#   E. Mã 110 nhập nhằng — CẢ HAI hướng (W06)
#   F. Retry / DLQ / poison / replay (W04/W07)
#   G. Dấu vết ánh xạ + chịu được CSDL chưa migrate (W06)
#   H. Polling fallback (W08)
#   I. Chốt chặn cấu trúc — thêm đường mới mà quên là hỏng ở đây
#
# Chạy: python3 app/thu/thu_webhook.py
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
import time
import unittest
import urllib.parse

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-g06-")

import adapter          # noqa: E402
import adapter_jt       # noqa: E402
import adapter_vtp      # noqa: E402  (đăng ký adapter)
import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import polling          # noqa: E402
import quyen            # noqa: E402
import trang_thai_hang as tth   # noqa: E402
import webhook as wh    # noqa: E402

SECRET_A = "secret-webhook-cua-A-11111111"
SECRET_B = "secret-webhook-cua-B-22222222"
SECRET_SB = "secret-callback-sandbox-33333333"


# ---------------------------------------------------------------- hạ tầng fixture
def _tenant(ten, code):
    return csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,'pro',?)",
                    (code, ten, csdl.bay_gio())).lastrowid


def _user():
    return csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                    " VALUES (?,?,'U',?)",
                    (f"u{csdl.mot('SELECT COUNT(*) c FROM users')['c']}",
                     bao_mat.bam_mat_khau("x" * 12), csdl.bay_gio())).lastrowid


def _account(tenant_id, hang, wh_ma, secret, moi_truong="mock", cred=None):
    ban_ma, duoi = bao_mat.luu_credentials(cred or {"api_key": "demo"},
                                           bao_mat.aad_credentials(tenant_id, hang))
    return csdl.ghi(
        "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
        "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
        (tenant_id, hang, f"{hang}-{wh_ma}", moi_truong, ban_ma, duoi, wh_ma,
         bao_mat.ma_hoa_wh(secret, wh_ma), csdl.bay_gio())).lastrowid


def _don(tenant_id, user_id, account_id, ma_van_don, trang_thai_giao=None, hang_tt=0):
    return csdl.ghi(
        "INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,nguoi_gui_dia_chi,"
        "nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,"
        "carrier_account_id,ma_van_don,trang_thai,trang_thai_giao,hang_trang_thai_giao,"
        "nguoi_tao,tao_luc,cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'da_gui',?,?,?,?,?)",
        (tenant_id, f"MD-{ma_van_don}", "A", "0901111111", "x", "B", "0902222222", "y", "z", 500,
         account_id, ma_van_don, trang_thai_giao, hang_tt, user_id,
         csdl.bay_gio(), csdl.bay_gio())).lastrowid


def doc_file(duong):
    """Đọc và ĐÓNG hẳn — ResourceWarning làm bẩn kết quả chạy."""
    with open(duong, encoding="utf-8") as f:
        return f.read()


def body_hub(event, mvd, event_id=None, **thua):
    d = {"event": event, "tracking_number": mvd}
    if event_id:
        d["event_id"] = event_id
    d.update(thua)
    return json.dumps(d, ensure_ascii=False).encode()


def biz_jt(bill, ma, scan_time, desc="mô tả của hãng"):
    return json.dumps({"billCode": bill,
                       "details": [{"scanTime": scan_time, "scanTypeCode": ma, "desc": desc}]},
                      ensure_ascii=False)


def body_jt(bill, ma, scan_time, desc="mô tả của hãng"):
    """Thân form đúng dạng tài liệu J&T: application/x-www-form-urlencoded, trường bizContent."""
    return urllib.parse.urlencode({"bizContent": biz_jt(bill, ma, scan_time, desc)}).encode()


def ky_hub(secret, body):
    return {"x-webhook-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}


def ky_jt(secret, biz, api_account="API-1", ts=None):
    return {"digest": base64.b64encode(hashlib.md5((biz + secret).encode()).digest()).decode(),
            "apiaccount": api_account,
            "timestamp": str(ts if ts is not None else wh._bay_gio_ms())}


_NEN = {}


def _dung_nen():
    """Dựng nền MỘT lần cho cả module. (setUpClass chạy lại cho từng lớp con → trùng khóa.)"""
    if _NEN:
        return _NEN
    csdl.mo()
    quyen.seed()
    csdl.ghi("INSERT OR IGNORE INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
             (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
    for ma, h in adapter.danh_sach_hang().items():
        csdl.ghi("INSERT OR IGNORE INTO carrier_providers"
                 " (ma,ten,capabilities_json,live_mo,cap_nhat_luc) VALUES (?,?,?,?,?)",
                 (ma, h["ten"], json.dumps(h["capabilities"]), 0, csdl.bay_gio()))
    uid = _user()
    ta = _tenant("Tenant A", "ta")
    tb = _tenant("Tenant B", "tb")
    _NEN.update(
        uid=uid, ta=ta, tb=tb,
        tk_a=_account(ta, "jt", "wh-a", SECRET_A),
        tk_b=_account(tb, "jt", "wh-b", SECRET_B),
        tk_vtp=_account(ta, "vtp", "wh-vtp", SECRET_A),
        # Tài khoản SANDBOX để kiểm sơ đồ chữ ký riêng của hãng (không mạng, không tạo adapter).
        tk_sb=_account(tb, "jt", "wh-sb", SECRET_SB, moi_truong="sandbox",
                       cred={"apiAccount": "API-1", "privateKey": "pk"}),
        tk_sb_vtp=_account(tb, "vtp", "wh-sb-vtp", SECRET_SB, moi_truong="sandbox"))
    return _NEN


class Nen(unittest.TestCase):
    """Nền dùng chung: hai tenant, năm tài khoản hãng, xử lý sự kiện ĐỒNG BỘ cho xác định."""

    @classmethod
    def setUpClass(cls):
        for k, v in _dung_nen().items():
            setattr(cls, k, v)

    def setUp(self):
        tth.bo_chot_nghia()
        polling.xoa_han_muc()

    # ---- tiện ích ----
    def row(self, account_id):
        return csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (account_id,))

    def gui(self, account_id, body, headers=None, secret=None):
        """Mô phỏng ĐÚNG thứ tự của tầng HTTP: tìm account → kiểm chữ ký → nhận → xử lý đồng bộ."""
        tk = self.row(account_id)
        hd = dict(headers) if headers else ky_hub(secret or SECRET_A, body)
        if not wh.kiem_chu_ky(tk, hd, body):
            return None, False, 401
        sk_id, trung = wh.nhan_su_kien(tk, body, hd)
        if not trung:
            wh._chay_mot(sk_id)
        return sk_id, trung, 200 if trung else 202

    def sk(self, sk_id):
        return csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))

    def tt_don(self, don_id):
        r = csdl.mot("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                     (don_id,))
        return r["trang_thai_giao"], r["hang_trang_thai_giao"]

    def audit_co(self, hanh_dong, doi_tuong=None):
        sql = "SELECT COUNT(*) c FROM audit WHERE hanh_dong=?"
        ts = [hanh_dong]
        if doi_tuong:
            sql += " AND doi_tuong=?"
            ts.append(doi_tuong)
        return csdl.mot(sql, ts)["c"]


# ============================================================================
class A_XacThuc(Nen):
    """W02/W03 — mỗi hãng một sơ đồ; mức xác thực khai đúng thứ đã đo."""

    def test_a01_chu_ky_dung_thi_nhan(self):
        b = body_hub("lay_hang", "MVD-A01", "E-A01")
        tk = self.row(self.tk_a)
        self.assertTrue(wh.kiem_chu_ky(tk, ky_hub(SECRET_A, b), b))

    def test_a02_chu_ky_sai_bi_tu_choi(self):
        b = body_hub("lay_hang", "MVD-A02", "E-A02")
        tk = self.row(self.tk_a)
        self.assertFalse(wh.kiem_chu_ky(tk, ky_hub("secret-sai-hoan-toan", b), b))
        self.assertGreaterEqual(self.audit_co("webhook_chu_ky_tu_choi"), 1,
                                "chữ ký sai mà không ghi audit — không ai thấy việc dò secret")

    def test_a03_thieu_chu_ky_bi_tu_choi(self):
        b = body_hub("lay_hang", "MVD-A03", "E-A03")
        tk = self.row(self.tk_a)
        for hd in ({}, {"x-webhook-signature": ""}, {"authorization": "Bearer gi-do"}):
            self.assertFalse(wh.kiem_chu_ky(tk, hd, b), f"lọt với headers {hd}")

    def test_a04_chu_ky_cua_tenant_khac_khong_dung_duoc(self):
        """Secret của B không mở được cửa của A — mỗi account một khóa riêng."""
        b = body_hub("lay_hang", "MVD-A04", "E-A04")
        self.assertFalse(wh.kiem_chu_ky(self.row(self.tk_a), ky_hub(SECRET_B, b), b))

    def test_a05_so_do_chon_o_phia_may_chu_khong_phai_tu_header(self):
        """Người gửi không được chọn sơ đồ: thêm header của sơ đồ khác cũng không đổi được gì."""
        biz = biz_jt("MVD-A05", 113, "2026-10-15 08:00:00")
        b = urllib.parse.urlencode({"bizContent": biz}).encode()
        tk = self.row(self.tk_a)       # account MOCK → sơ đồ hub_hmac
        ten, _, muc = wh.chon_so_do(tk)
        self.assertEqual((ten, muc), ("hub_hmac", wh.MUC_MOCK))
        # gửi kèm digest J&T hợp lệ nhưng KHÔNG có HMAC của hub → phải bị từ chối
        self.assertFalse(wh.kiem_chu_ky(tk, ky_jt(SECRET_A, biz), b),
                         "header của sơ đồ khác lại mở được cửa — người gửi chọn được sơ đồ!")

    def test_a06_so_do_jt_theo_tai_lieu_o_moi_truong_that(self):
        """Sandbox J&T dùng digest = base64(md5-bytes(bizContent + khóa)), đúng công thức tài liệu."""
        biz = biz_jt("MVD-A06", 113, "2026-10-15 08:00:00")
        b = urllib.parse.urlencode({"bizContent": biz}).encode()
        tk = self.row(self.tk_sb)
        ten, _, muc = wh.chon_so_do(tk)
        self.assertEqual((ten, muc), ("jt_digest", wh.MUC_DOCUMENTED))
        self.assertTrue(wh.kiem_chu_ky(tk, ky_jt(SECRET_SB, biz), b))
        # md5 HEX rồi base64 là biến thể SAI hay gặp — phải bị từ chối
        sai = base64.b64encode(hashlib.md5((biz + SECRET_SB).encode()).hexdigest().encode()).decode()
        self.assertFalse(wh.kiem_chu_ky(tk, {"digest": sai, "apiaccount": "API-1",
                                             "timestamp": str(wh._bay_gio_ms())}, b))

    def test_a07_jt_doi_du_ba_header(self):
        biz = biz_jt("MVD-A07", 113, "2026-10-15 08:00:00")
        b = urllib.parse.urlencode({"bizContent": biz}).encode()
        tk = self.row(self.tk_sb)
        du = ky_jt(SECRET_SB, biz)
        for bo in ("digest", "timestamp"):
            thieu = {k: v for k, v in du.items() if k != bo}
            self.assertFalse(wh.kiem_chu_ky(tk, thieu, b), f"thiếu {bo} mà vẫn lọt")
        # apiAccount của tài khoản khác
        self.assertFalse(wh.kiem_chu_ky(tk, dict(du, apiaccount="API-KHAC"), b))
        # timestamp quá cũ → nghi phát lại
        self.assertFalse(wh.kiem_chu_ky(tk, ky_jt(SECRET_SB, biz, ts=wh._bay_gio_ms() - 3600_000), b))

    def test_a08_hang_chua_co_tai_lieu_callback_thi_BLOCKED(self):
        """VTP chưa có tài liệu Partner API → môi trường thật KHÔNG nhận callback, không đoán."""
        b = body_hub("lay_hang", "MVD-A08", "E-A08")
        tk = self.row(self.tk_sb_vtp)
        ten, ham, muc = wh.chon_so_do(tk)
        self.assertEqual((ten, ham, muc), (None, None, wh.MUC_BLOCKED))
        self.assertFalse(wh.kiem_chu_ky(tk, ky_hub(SECRET_SB, b), b),
                         "VTP sandbox nhận callback dù chưa có tài liệu ký — đang tự phát minh")

    def test_a09_hang_la_khong_co_so_do_thi_khoa(self):
        """Hãng không có trong sổ sơ đồ → BLOCKED, không rơi về sơ đồ 'mặc định' nào."""
        class RowGia(dict):
            def keys(self):
                return super().keys()
        tk = RowGia({"id": 999, "tenant_id": self.ta, "hang": "hang_la_chua_tung_thay",
                     "moi_truong": "production", "webhook_ma": "x",
                     "webhook_secret_ma_hoa": "x", "credentials_ma_hoa": "x"})
        self.assertEqual(wh.chon_so_do(tk)[2], wh.MUC_BLOCKED)
        self.assertFalse(wh.kiem_chu_ky(tk, {"x-webhook-signature": "bat-ky"}, b"{}"))

    def test_a10_bang_muc_xac_thuc_phu_moi_hang_da_dang_ky(self):
        """Thêm hãng mới mà quên khai mức xác thực là hỏng NGAY ở đây, không chờ ai nhớ."""
        bang = wh.bang_muc_xac_thuc()
        for ma in adapter._DANG_KY:
            self.assertIn(ma, bang, f"hãng {ma} chưa khai sơ đồ xác thực trong SO_DO_THEO_HANG")
            for khoa in ("mock", "sandbox_production"):
                self.assertIn(bang[ma][khoa]["muc"], wh.MUC_HOP_LE)
        self.assertEqual(bang["jt"]["sandbox_production"]["muc"], wh.MUC_DOCUMENTED)
        self.assertEqual(bang["vtp"]["sandbox_production"]["muc"], wh.MUC_BLOCKED)
        self.assertEqual(bang["jt"]["mock"]["muc"], wh.MUC_MOCK)


# ============================================================================
class B_ResolveTenant(Nen):
    """W02 — tenant CHỈ đến từ carrier account."""

    def test_b01_cap_nhat_duoc_don_cua_chinh_minh(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-B01", "cho_lay", 1)
        sk_id, trung, ma = self.gui(self.tk_a, body_hub("dang_giao", "MVD-B01", "E-B01"))
        self.assertEqual((ma, trung), (202, False))
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        self.assertEqual(self.tt_don(d)[0], "dang_giao")

    def test_b02_khong_cap_nhat_don_cua_tenant_khac(self):
        """Mã vận đơn TRÙNG ở hai tenant: account của B không được đụng đơn của A."""
        da = _don(self.ta, self.uid, self.tk_a, "MVD-TRUNG", "cho_lay", 1)
        db = _don(self.tb, self.uid, self.tk_b, "MVD-TRUNG", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_b, body_hub("giao_thanh_cong", "MVD-TRUNG", "E-B02"),
                               secret=SECRET_B)
        self.assertEqual(self.tt_don(da)[0], "cho_lay", "webhook của B cập nhật đơn của A!")
        self.assertEqual(self.tt_don(db)[0], "giao_thanh_cong")

    def test_b03_muu_toan_cheo_tenant_trong_payload_bi_bo_qua_va_ghi_lai(self):
        """Payload khai tenant_id của A: phải BỎ QUA và ghi audit, không bao giờ tin."""
        da = _don(self.ta, self.uid, self.tk_a, "MVD-B03A", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_b, body_hub("giao_thanh_cong", "MVD-B03A", "E-B03",
                                                   tenant_id=self.ta), secret=SECRET_B)
        self.assertEqual(self.tt_don(da)[0], "cho_lay", "payload tự khai tenant mà được tin!")
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertGreaterEqual(self.audit_co("webhook_claim_tenant_bi_bo_qua"), 1,
                                "mưu toan chéo tenant không để lại dấu vết nào")

    def test_b04_don_la_thi_khong_khop_khong_dung_den_don_nao(self):
        sk_id, _, _ = self.gui(self.tk_a, body_hub("dang_giao", "MVD-KHONG-TON-TAI", "E-B04"))
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertGreaterEqual(self.audit_co("webhook_khong_khop_don"), 1)

    def test_b05_dung_account_khac_cua_cung_tenant_cung_khong_duoc(self):
        """Đơn gắn account VTP của A: account J&T của A (cùng tenant) KHÔNG được cập nhật nó."""
        d = _don(self.ta, self.uid, self.tk_vtp, "MVD-B05", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("dang_giao", "MVD-B05", "E-B05"))
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertEqual(self.tt_don(d)[0], "cho_lay")

    def test_b06_account_la_khong_tim_thay(self):
        self.assertIsNone(wh.tim_account_theo_webhook_ma("wh-khong-ton-tai"))
        csdl.ghi("UPDATE carrier_accounts SET kich_hoat=0 WHERE id=?", (self.tk_vtp,))
        try:
            self.assertIsNone(wh.tim_account_theo_webhook_ma("wh-vtp"),
                              "account đã tắt vẫn nhận được webhook")
        finally:
            csdl.ghi("UPDATE carrier_accounts SET kich_hoat=1 WHERE id=?", (self.tk_vtp,))


# ============================================================================
class C_ChongTrung(Nen):
    """W04 — định danh bền + chống trùng do CSDL cưỡng chế."""

    def test_c01_event_id_trung_khong_xu_ly_hai_lan(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-C01", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-C01", "E-C01")
        sk1, t1, ma1 = self.gui(self.tk_a, b)
        sk2, t2, ma2 = self.gui(self.tk_a, b)
        self.assertEqual((t1, t2), (False, True))
        self.assertEqual(sk1, sk2, "sự kiện trùng tạo ra bản ghi thứ hai")
        self.assertEqual(ma2, 200)
        ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? AND noi_dung LIKE '%lay_hang%'", (d,))
        self.assertEqual(len(ls), 1, f"cập nhật {len(ls)} lần cho một sự kiện")

    def test_c02_rang_buoc_trung_do_CSDL_cuong_che(self):
        self.assertRegex(csdl.SCHEMA, r"UNIQUE\s*\(\s*carrier_account_id\s*,\s*event_id\s*\)")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError,
                              msg="chèn tay trùng khóa mà CSDL không chặn"):
            csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                     "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                     (self.tk_a, "E-C02-TAY", b"{}", "{}", csdl.bay_gio()))
            csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                     "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                     (self.tk_a, "E-C02-TAY", b"{}", "{}", csdl.bay_gio()))

    def test_c03_cung_event_id_khac_account_la_hai_su_kien(self):
        """Khóa trùng là (account, event_id): hai hãng/hai tenant trùng số không đè nhau."""
        _don(self.ta, self.uid, self.tk_a, "MVD-C03A", "cho_lay", 1)
        _don(self.tb, self.uid, self.tk_b, "MVD-C03B", "cho_lay", 1)
        sk1, _, _ = self.gui(self.tk_a, body_hub("lay_hang", "MVD-C03A", "E-DUNG-CHUNG"))
        sk2, _, _ = self.gui(self.tk_b, body_hub("lay_hang", "MVD-C03B", "E-DUNG-CHUNG"),
                             secret=SECRET_B)
        self.assertNotEqual(sk1, sk2)

    def test_c04_khong_co_event_id_thi_dinh_danh_theo_khoa_cua_hang(self):
        """J&T không cấp event_id: khóa billCode|scanTime|scanTypeCode phải chặn được trùng."""
        tk = self.row(self.tk_a)
        b = body_jt("MVD-C04", 112, "2026-10-15 09:00:00")
        id1 = wh.dinh_danh_su_kien(tk, b)
        self.assertTrue(id1.startswith("jt-"), f"định danh không dùng khóa hãng: {id1}")
        self.assertEqual(id1, wh.dinh_danh_su_kien(tk, body_jt("MVD-C04", 112, "2026-10-15 09:00:00")))
        # đổi bất kỳ thành phần nào của khóa → định danh phải khác
        self.assertNotEqual(id1, wh.dinh_danh_su_kien(tk, body_jt("MVD-C04", 112, "2026-10-15 09:00:01")))
        self.assertNotEqual(id1, wh.dinh_danh_su_kien(tk, body_jt("MVD-C04", 109, "2026-10-15 09:00:00")))
        self.assertNotEqual(id1, wh.dinh_danh_su_kien(tk, body_jt("MVD-KHAC", 112, "2026-10-15 09:00:00")))

    def test_c05_khong_co_khoa_nao_thi_bam_noi_dung(self):
        tk = self.row(self.tk_a)
        self.assertTrue(wh.dinh_danh_su_kien(tk, b'{"gi":"do"}').startswith("noid-"))

    def test_c06_nhan_viec_nguyen_tu_chi_mot_worker_lay_duoc(self):
        """Hai worker cùng nạp một sự kiện: chỉ một nhận được việc."""
        sk_id = csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                         "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                         (self.tk_a, "E-C06", b"{}", "{}", csdl.bay_gio())).lastrowid
        self.assertIsNotNone(wh._nhan_viec(sk_id))
        self.assertIsNone(wh._nhan_viec(sk_id), "hai worker cùng nhận một sự kiện!")


# ============================================================================
class D_SaiThuTu(Nen):
    """W05 — thứ hạng CỘNG mốc thời gian của hãng."""

    def test_d01_rank_guard_khong_keo_lui(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-D01", "cho_lay", 1)
        self.gui(self.tk_a, body_hub("giao_thanh_cong", "MVD-D01", "E-D01-1"))
        self.gui(self.tk_a, body_hub("dang_giao", "MVD-D01", "E-D01-2"))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong", "sự kiện cũ kéo lùi trạng thái!")

    def test_d02_moc_hang_chan_ca_rank_guard_KHONG_chan_duoc(self):
        """Ca thật mà thứ hạng một mình bỏ lọt: 'Delivered' CŨ đến sau 'On Delivery' MỚI.

        hạng(giao_thanh_cong)=5 > hạng(dang_giao)=3 ⇒ rank guard cho áp. Chỉ mốc scanTime của
        hãng mới biết bản tin kia là bản cũ.
        """
        d = _don(self.ta, self.uid, self.tk_a, "MVD-D02", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-D02", 112, "2026-10-15 12:00:00"),
                 headers=ky_hub(SECRET_A, body_jt("MVD-D02", 112, "2026-10-15 12:00:00")))
        self.assertEqual(self.tt_don(d)[0], "dang_giao")
        cu = body_jt("MVD-D02", 113, "2026-10-15 08:00:00")
        sk_id, _, _ = self.gui(self.tk_a, cu, headers=ky_hub(SECRET_A, cu))
        self.assertEqual(self.tt_don(d)[0], "dang_giao",
                         "bản tin CŨ của hãng vẫn ghi đè được trạng thái — mốc hãng không có tác dụng")
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        self.assertGreaterEqual(self.audit_co("webhook_den_muon", f"don:{d}"), 1)

    def test_d03_moc_hang_moi_hon_thi_ap_binh_thuong(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-D03", "cho_lay", 1)
        for ma, luc in ((112, "2026-10-15 08:00:00"), (113, "2026-10-15 15:30:00")):
            b = body_jt("MVD-D03", ma, luc)
            self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong")

    def test_d04_watermark_lay_tu_dau_vet_cua_chinh_duong_cap_nhat(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-D04", "cho_lay", 1)
        self.assertIsNone(wh.watermark(d))
        b = body_jt("MVD-D04", 112, "2026-10-15 10:00:00")
        self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 10:00:00"))

    def test_d05_moc_chuan_co_mui_gio_tuong_minh(self):
        """§12.2: mốc không nhãn múi giờ của J&T là UTC+7, không phải giờ máy."""
        self.assertEqual(wh._moc_chuan("2026-10-15 10:00:00"),
                         wh._moc_chuan("2026-10-15 03:00:00Z"))
        self.assertEqual(wh._moc_chuan("2026-10-15 10:00:00"),
                         wh._moc_chuan("2026-10-15 10:00:00+07:00"))
        self.assertLess(wh._moc_chuan("2026-10-15 09:59:59"), wh._moc_chuan("2026-10-15 10:00:00"))
        self.assertEqual(len(wh._moc_chuan("2026-10-15 10:00:00")), 14,
                         "mốc phải zero-pad 14 chữ số để MAX() và '<' chuỗi so đúng")
        for xau in (None, "", "khong-phai-ngay", "15/10/2026 ngay gi do", True):
            self.assertIsNone(wh._moc_chuan(xau), f"{xau!r} lại đọc ra mốc")

    def test_d06_khong_co_moc_hang_thi_lui_ve_rank_guard_chu_khong_chan_het(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-D06", "cho_lay", 1)
        self.gui(self.tk_a, body_hub("lay_hang", "MVD-D06", "E-D06"))
        self.assertEqual(self.tt_don(d)[0], "lay_hang",
                         "payload không có mốc hãng mà bị chặn oan")

    def test_d07_lay_ban_quet_moi_nhat_trong_details(self):
        tk = self.row(self.tk_a)
        biz = json.dumps({"billCode": "MVD-D07", "details": [
            {"scanTime": "2026-10-15 08:00:00", "scanTypeCode": 106},
            {"scanTime": "2026-10-15 18:00:00", "scanTypeCode": 113},
            {"scanTime": "2026-10-15 12:00:00", "scanTypeCode": 112}]}, ensure_ascii=False)
        sv = wh.doc_su_kien_hang(tk, urllib.parse.urlencode({"bizContent": biz}).encode())
        self.assertEqual(sv["ma_trang_thai"], 113)
        self.assertEqual(sv["moc_hang"], wh._moc_chuan("2026-10-15 18:00:00"))


# ============================================================================
class E_Ma110NhapNhang(Nen):
    """W06 — mã 110 của J&T: tài liệu TỰ MÂU THUẪN. Thử CẢ HAI hướng."""

    def test_e01_so_nhap_nhang_co_ghi_110_va_du_hai_nghia(self):
        muc = tth.NHAP_NHANG[("jt", 110)]
        self.assertEqual(set(muc["nghia"]), {"bang_tham_so", "vi_du_tra_loi"})
        self.assertEqual(muc["nghia"]["bang_tham_so"]["trang_thai"], "dang_giao")
        self.assertIsNone(muc["nghia"]["vi_du_tra_loi"]["trang_thai"])
        self.assertIn("110", muc["ly_do"])
        self.assertTrue(muc["nguon"], "mã nhập nhằng mà không ghi nguồn tài liệu")

    def test_e02_chua_chot_nghia_thi_KHONG_doi_trang_thai(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E02", "cho_lay", 1)
        b = body_jt("MVD-E02", 110, "2026-10-15 10:00:00", "Quét kiện / Arrival?")
        sk_id, _, _ = self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1),
                         "mã nhập nhằng mà hệ thống tự chọn một nghĩa rồi đổi trạng thái!")
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        self.assertGreaterEqual(self.audit_co("webhook_can_soat", f"don:{d}"), 1)

    def test_e03_du_tin_cay_va_nhan_AMBIGUOUS_duoc_luu(self):
        qd = tth.quyet_dinh("jt", 110, su_kien_goc={"tho": "x"})
        self.assertEqual(qd.nhan, "AMBIGUOUS")
        self.assertEqual(qd.do_tin_cay, tth.TIN_NHAP_NHANG)
        self.assertTrue(qd.can_soat)
        self.assertIsNone(qd.trang_thai_ap)
        # đủ dấu vết: mã gốc · mô tả gốc · sự kiện gốc · nguồn + phiên bản tài liệu · giờ nhận
        for t in ("ma_goc", "mo_ta_goc", "su_kien_hang_goc", "nguon_tai_lieu",
                  "phien_ban_tai_lieu", "nhan_luc", "cac_nghia"):
            self.assertTrue(getattr(qd, t) not in (None, "", {}), f"thiếu dấu vết: {t}")
        self.assertEqual(set(qd.cac_nghia), {"bang_tham_so", "vi_du_tra_loi"})

    def test_e04_HUONG_1_neu_110_la_Arrival(self):
        """Chốt nghĩa 'bảng tham số' (110 = Arrival) → đơn tiến lên dang_giao."""
        tth.chot_nghia("jt", 110, "bang_tham_so", "AG-03 (bộ thử)",
                       "giả định kiểm thử: hãng xác nhận bảng tham số")
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E04", "cho_lay", 1)
        b = body_jt("MVD-E04", 110, "2026-10-15 10:00:00")
        self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        self.assertEqual(self.tt_don(d)[0], "dang_giao")
        qd = tth.quyet_dinh("jt", 110)
        self.assertEqual(qd.nhan, "OK")
        self.assertFalse(qd.can_soat)
        self.assertEqual(qd.do_tin_cay, tth.TIN_TRUNG_BINH,
                         "nghĩa do người chốt mà lại khai độ tin cậy 'cao'")
        self.assertEqual(qd.nghia_da_chot["nguoi_chot"], "AG-03 (bộ thử)")

    def test_e05_HUONG_2_neu_110_la_quet_kien_co_van_de(self):
        """Chốt nghĩa 'ví dụ trả lời' (110 = kiện có vấn đề) → KHÔNG tiến trạng thái, vẫn ghi nhận."""
        tth.chot_nghia("jt", 110, "vi_du_tra_loi", "AG-03 (bộ thử)",
                       "giả định kiểm thử: hãng xác nhận bộ mã của ví dụ")
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E05", "cho_lay", 1)
        b = body_jt("MVD-E05", 110, "2026-10-15 10:00:00")
        sk_id, _, _ = self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1),
                         "nghĩa 'kiện có vấn đề' mà lại đẩy đơn đi tiếp")
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        qd = tth.quyet_dinh("jt", 110)
        self.assertIsNone(qd.trang_thai_ap)
        self.assertEqual(qd.nghia_da_chot["khoa_nghia"], "vi_du_tra_loi")

    def test_e06_khong_bao_gio_mac_dinh_sang_hoan_tat(self):
        """Dù chốt nghĩa hay không, 110 không bao giờ ra giao_thanh_cong / hoan_hang."""
        for lam in (lambda: None,
                    lambda: tth.chot_nghia("jt", 110, "bang_tham_so", "x", "y"),
                    lambda: tth.chot_nghia("jt", 110, "vi_du_tra_loi", "x", "y")):
            tth.bo_chot_nghia()
            lam()
            self.assertNotIn(tth.quyet_dinh("jt", 110).trang_thai_ap, tth.TRANG_THAI_HOAN_TAT)
        tth.bo_chot_nghia()
        # và không cho CHỐT một nghĩa dẫn tới hoàn tất, dù ai đó thêm nghĩa đó vào sổ
        tth.NHAP_NHANG[("jt", 110)]["nghia"]["nghia_bay"] = {
            "mo_ta_hang": "bịa", "trang_thai": "giao_thanh_cong", "nguon": "không có"}
        try:
            with self.assertRaises(ValueError):
                tth.chot_nghia("jt", 110, "nghia_bay", "x", "y")
            # chặn cứng ở cả quyet_dinh: nhồi thẳng vào sổ chốt cũng không lọt
            tth.NGHIA_DA_CHOT[("jt", 110)] = {"khoa_nghia": "nghia_bay",
                                              "trang_thai": "giao_thanh_cong",
                                              "nguoi_chot": "x", "can_cu": "y",
                                              "mo_ta_hang": "bịa"}
            qd = tth.quyet_dinh("jt", 110)
            self.assertIsNone(qd.trang_thai_ap, "nhồi sổ chốt là đẩy được đơn sang hoàn tất!")
            self.assertTrue(qd.can_soat)
            self.assertIn("CHẶN", qd.ghi_chu)
        finally:
            tth.NHAP_NHANG[("jt", 110)]["nghia"].pop("nghia_bay", None)
            tth.bo_chot_nghia()

    def test_e07_chot_nghia_doi_can_cu(self):
        for nguoi, can_cu in (("", "co can cu"), ("ai do", ""), ("  ", "  ")):
            with self.assertRaises(ValueError):
                tth.chot_nghia("jt", 110, "bang_tham_so", nguoi, can_cu)
        with self.assertRaises(KeyError):
            tth.chot_nghia("jt", 113, "bang_tham_so", "x", "y")   # 113 không nhập nhằng
        with self.assertRaises(KeyError):
            tth.chot_nghia("jt", 110, "nghia-khong-ton-tai", "x", "y")

    def test_e08_ma_ro_nghia_khac_khong_bi_anh_huong(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E08", "cho_lay", 1)
        for ma, cho_doi, luc in ((106, "lay_hang", "2026-10-15 08:00:00"),
                                 (110, "lay_hang", "2026-10-15 09:00:00"),   # nhập nhằng → giữ nguyên
                                 (113, "giao_thanh_cong", "2026-10-15 10:00:00")):
            b = body_jt("MVD-E08", ma, luc)
            self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
            self.assertEqual(self.tt_don(d)[0], cho_doi, f"sau mã {ma}")

    def test_e09_anh_xa_cu_van_doc_duoc_nhung_bi_danh_dau(self):
        """`anh_xa()` giữ nghĩa cũ cho bên ĐỌC, nhưng phải khai rõ là nhập nhằng."""
        a = tth.anh_xa("jt", 110)
        self.assertTrue(a.biet_ma)
        self.assertTrue(a.nhap_nhang)
        self.assertTrue(a.can_soat)
        self.assertEqual(a.do_tin_cay, tth.TIN_NHAP_NHANG)
        self.assertIsNone(a.trang_thai_ap, "anh_xa cho phép áp thẳng nghĩa chưa chốt")
        self.assertFalse(tth.anh_xa("jt", 113).nhap_nhang)
        self.assertTrue(tth.la_nhap_nhang("jt", 110))
        self.assertTrue(tth.la_nhap_nhang("jt", "110"))
        self.assertFalse(tth.la_nhap_nhang("jt", 113))


# ============================================================================
class F_RetryDLQReplay(Nen):
    """W04/W07 — retry có trần, DLQ, poison message, replay có phép + có trần."""

    def test_f01_loi_tam_thoi_thu_lai_roi_vao_DLQ(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-F01", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-F01", "E-F01", demo_force_fail=True)
        sk_id, _, _ = self.gui(self.tk_a, b)
        for _ in range(cau_hinh.WEBHOOK_SO_LAN_THU + 2):
            if self.sk(sk_id)["trang_thai"] == "dlq":
                break
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='cho_thu_lai' WHERE id=? AND trang_thai!='dlq'",
                     (sk_id,))
            wh._chay_mot(sk_id)
        r = self.sk(sk_id)
        self.assertEqual(r["trang_thai"], "dlq")
        self.assertGreaterEqual(r["so_lan_thu"], cau_hinh.WEBHOOK_SO_LAN_THU)
        self.assertGreaterEqual(self.audit_co("webhook_dlq", f"su_kien:{sk_id}"), 1)

    def test_f02_payload_hong_vao_DLQ_ngay_khong_dot_lan_thu(self):
        """Poison message: không bao giờ tự khỏi → vào DLQ ngay, không thử lại mù."""
        for mo_ta, b in (("không phải JSON", b"\xff\xfe khong phai json"),
                         ("JSON nhưng thiếu trường", b'{"chi":"co the nay"}'),
                         ("JSON là mảng", b'[1,2,3]'),
                         ("thiếu mã vận đơn", b'{"event":"lay_hang"}'),
                         ("rỗng", b"")):
            tk = self.row(self.tk_a)
            sk_id, trung = wh.nhan_su_kien(tk, b, {"x": "y"})
            wh._chay_mot(sk_id)
            r = self.sk(sk_id)
            self.assertEqual(r["trang_thai"], "dlq", f"{mo_ta}: không vào DLQ")
            self.assertEqual(r["so_lan_thu"], 0, f"{mo_ta}: còn đốt lượt thử cho lỗi vĩnh viễn")
            self.assertIn("vinh vien", r["loi_cuoi"])

    def test_f03_backoff_co_tran(self):
        self.assertLessEqual(cau_hinh.WEBHOOK_BACKOFF_GOC * (2 ** 19), 10 ** 9)  # cảnh báo số học
        tran = wh.BACKOFF_TRAN_GIAY
        for n in range(1, 25):
            self.assertLessEqual(min(cau_hinh.WEBHOOK_BACKOFF_GOC * (2 ** (n - 1)), tran), tran)
        self.assertLess(tran, 3600, "trần backoff lớn hơn một giờ — việc coi như mất")

    def test_f04_khoi_phuc_tu_DLQ_bang_replay(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-F04", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-F04", "E-F04", demo_force_fail=True)
        sk_id, _, _ = self.gui(self.tk_a, b)
        while self.sk(sk_id)["trang_thai"] != "dlq":
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='cho_thu_lai' WHERE id=?", (sk_id,))
            wh._chay_mot(sk_id)
        self.assertEqual(self.tt_don(d)[0], "cho_lay")
        # sửa nguyên nhân (bỏ cờ ép lỗi) rồi replay → phải khôi phục được
        csdl.ghi("UPDATE wh_su_kien SET payload_tho=? WHERE id=?",
                 (body_hub("lay_hang", "MVD-F04", "E-F04"), sk_id))
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertTrue(ok, ly_do)
        wh._chay_mot(sk_id)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        self.assertEqual(self.tt_don(d)[0], "lay_hang")

    def test_f05_replay_khong_duoc_cheo_tenant(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-F05", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("lay_hang", "MVD-F05", "E-F05"))
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.tb, self.uid)
        self.assertFalse(ok, "tenant B replay được sự kiện của tenant A")
        self.assertIn("không có sự kiện", ly_do)

    def test_f06_replay_co_TRAN_khong_vo_han(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-F06", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("lay_hang", "MVD-F06", "E-F06"))
        for i in range(wh.REPLAY_TOI_DA):
            ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
            self.assertTrue(ok, f"lần {i + 1}: {ly_do}")
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertFalse(ok, "replay không có trần — poison message replay được vô hạn")
        self.assertIn("trần", ly_do)
        self.assertGreaterEqual(self.audit_co("webhook_replay_tu_choi", f"su_kien:{sk_id}"), 1)
        self.assertEqual(wh.so_lan_replay(sk_id), wh.REPLAY_TOI_DA)

    def test_f07_replay_ghi_audit_moi_lan(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-F07", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("lay_hang", "MVD-F07", "E-F07"))
        truoc = self.audit_co("webhook_replay", f"su_kien:{sk_id}")
        wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertEqual(self.audit_co("webhook_replay", f"su_kien:{sk_id}"), truoc + 1)

    def test_f08_quyen_replay_dung_RBAC_trong_CSDL(self):
        """Quyền do tầng HTTP kiểm, nhưng bảng quyền phải nói đúng: VIEWER không được replay."""
        self.assertTrue(quyen.co_quyen("TENANT_OWNER", "tenant.webhook.replay"))
        self.assertTrue(quyen.co_quyen("TENANT_ADMIN", "tenant.webhook.replay"))
        self.assertFalse(quyen.co_quyen("TENANT_VIEWER", "tenant.webhook.replay"))
        self.assertFalse(quyen.co_quyen("TENANT_STAFF", "tenant.webhook.replay"))
        self.assertTrue(quyen.co_quyen("TENANT_VIEWER", "tenant.webhook.xem"))

    def test_f09_su_kien_o_trang_thai_cuoi_khong_bi_chay_lai(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-F09", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("lay_hang", "MVD-F09", "E-F09"))
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")
        wh._chay_mot(sk_id)   # không được làm gì
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")

    def test_f10_trang_thai_su_kien_nam_trong_hop_dong_dong_bang(self):
        """SHARED_CONTRACTS mục 12 khóa đúng 6 trạng thái — thêm giá trị lạ là phá hợp đồng."""
        hop_le = {"moi", "dang_xu_ly", "xong", "cho_thu_lai", "dlq", "khong_khop"}
        co = {r["trang_thai"] for r in csdl.nhieu("SELECT DISTINCT trang_thai FROM wh_su_kien")}
        self.assertTrue(co <= hop_le, f"trạng thái ngoài hợp đồng: {co - hop_le}")
        nguon = doc_file(os.path.join(GOC_APP, "webhook.py"))
        for tt in re.findall(r"trang_thai='([a-z_]+)'", nguon):
            self.assertIn(tt, hop_le, f"webhook.py đặt trạng thái lạ '{tt}'")


# ============================================================================
class G_DauVetAnhXa(Nen):
    """W06 — dấu vết đầy đủ, và chạy được trên CSDL CHƯA migrate."""

    def test_g01_csdl_chua_migrate_van_khong_mat_dau_vet(self):
        wh.xoa_cache_cot()
        self.assertFalse(wh.cot_co("wh_su_kien", "anh_xa_do_tin_cay"),
                         "CSDL thử đã có cột mở rộng — ca này đang kiểm nhánh sai")
        d = _don(self.ta, self.uid, self.tk_a, "MVD-G01", "cho_lay", 1)
        b = body_jt("MVD-G01", 110, "2026-10-15 10:00:00", "mô tả gốc của hãng")
        sk_id, _, _ = self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
        au = csdl.mot("SELECT chi_tiet FROM audit WHERE hanh_dong='webhook_anh_xa'"
                      " AND doi_tuong=? ORDER BY id DESC LIMIT 1", (f"su_kien:{sk_id}",))
        self.assertIsNotNone(au, "không migrate thì mất sạch dấu vết ánh xạ")
        ct = json.loads(au["chi_tiet"])
        self.assertEqual(ct["ma_goc"], 110)
        self.assertEqual(ct["nhan"], "AMBIGUOUS")
        self.assertEqual(ct["do_tin_cay"], tth.TIN_NHAP_NHANG)
        self.assertTrue(ct["can_soat"])
        self.assertIn("jtexpress", ct["nguon_tai_lieu"])
        self.assertEqual(ct["phien_ban_tai_lieu"], "doc-2026-10-14")
        self.assertTrue(ct["nhan_luc"])
        self.assertEqual(ct["su_kien_hang_goc"]["ma_van_don"], "MVD-G01")
        self.assertIsNone(ct["trang_thai_ap"])

    def test_g02_csdl_da_migrate_thi_ghi_vao_cot(self):
        """Dựng đúng DDL đã đề xuất cho AG-00 rồi kiểm nhánh ghi cột — không chỉ nói là sẽ chạy.

        G14 (15/10/2026): ca này đã được SỬA. Bản cũ ghim hành vi "ghi `hang_moc_thoi_gian` cho
        mọi sự kiện, kể cả sự kiện không được áp" — hành vi đó là LỖI (xem chú thích trong ca và
        `docs/G14_JT_WEBHOOK.md` §4.3). Nay ca kiểm đúng luật: cột chỉ được ghi khi sự kiện ĐÃ ÁP,
        dấu vết mốc gốc vẫn còn trong audit, và hai nguồn mốc phải khớp nhau.
        """
        cot = {r[1] for r in csdl.nhieu("PRAGMA table_info(wh_su_kien)")}
        them = [("hang_ma_goc", "TEXT"), ("hang_mo_ta_goc", "TEXT"), ("hang_su_kien_goc", "TEXT"),
                ("anh_xa_do_tin_cay", "TEXT"), ("anh_xa_nguon", "TEXT"),
                ("can_soat", "INTEGER NOT NULL DEFAULT 0"), ("hang_moc_thoi_gian", "TEXT"),
                ("don_id", "INTEGER"), ("trang_thai_chuan", "TEXT")]
        for ten, kieu in them:
            if ten not in cot:
                csdl.ghi(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
        wh.xoa_cache_cot()
        try:
            self.assertTrue(wh.cot_co("wh_su_kien", "anh_xa_do_tin_cay"))
            d = _don(self.ta, self.uid, self.tk_a, "MVD-G02", "cho_lay", 1)
            b = body_jt("MVD-G02", 110, "2026-10-15 10:00:00", "mô tả gốc của hãng")
            sk_id, _, _ = self.gui(self.tk_a, b, headers=ky_hub(SECRET_A, b))
            r = self.sk(sk_id)
            self.assertEqual(r["hang_ma_goc"], "110")
            self.assertEqual(r["anh_xa_do_tin_cay"], tth.TIN_NHAP_NHANG)
            self.assertEqual(r["can_soat"], 1)
            self.assertEqual(r["don_id"], d)
            # ĐÍNH CHÍNH G14 (AG-03, 15/10/2026) — ca này TRƯỚC ĐÂY ghim hành vi SAI.
            #
            # Bản cũ khẳng định `hang_moc_thoi_gian` được ghi cho mã 110 (sự kiện KHÔNG được áp):
            #     self.assertEqual(r["hang_moc_thoi_gian"], wh._moc_chuan("2026-10-15 10:00:00"))
            # Hành vi ấy chính là LỖI: mốc chỉ có nghĩa "mốc hãng mới nhất ĐÃ ÁP", nên ghi nó
            # cho một sự kiện không đổi được trạng thái là để nó chặn oan bản quét thật đến sau.
            # Đo được (docs/G14_JT_WEBHOOK.md §4.3): `121` lúc 10:00 rồi `113 Delivered` lúc 09:00
            # ⇒ đơn đã giao mà hệ thống không bao giờ biết. Ca cũ xanh vì nó KIỂM NHẦM CHỖ, không
            # phải vì mã đúng — nên nó được sửa theo hành vi đúng, KHÔNG phải nới ra cho vừa mã.
            self.assertIsNone(r["hang_moc_thoi_gian"],
                              "mã nhập nhằng (không áp) lại đẩy được mốc hãng của đơn")
            self.assertIsNone(r["trang_thai_chuan"])
            self.assertIsNone(wh.watermark(d), "mã nhập nhằng đẩy được watermark của đơn")
            # ...nhưng KHÔNG mất dấu vết: mốc gốc của hãng vẫn nằm trong audit ánh xạ.
            au = csdl.mot("SELECT chi_tiet FROM audit WHERE hanh_dong='webhook_anh_xa'"
                          " AND doi_tuong=? ORDER BY id DESC LIMIT 1", (f"su_kien:{sk_id}",))
            self.assertEqual(json.loads(au["chi_tiet"])["su_kien_hang_goc"]["moc_hang"],
                             wh._moc_chuan("2026-10-15 10:00:00"),
                             "bỏ quyền đẩy mốc mà xoá luôn dấu vết mốc gốc")
            self.assertIn("doc-2026-10-14", r["anh_xa_nguon"])
            self.assertIn("Arrival", r["hang_mo_ta_goc"] or "")
            # Sự kiện ĐÃ ÁP thì mốc được ghi, và HAI NGUỒN phải nói cùng một con số.
            d2 = _don(self.ta, self.uid, self.tk_a, "MVD-G02B", "cho_lay", 1)
            b2 = body_jt("MVD-G02B", 112, "2026-10-15 11:00:00")
            sk2, _, _ = self.gui(self.tk_a, b2, headers=ky_hub(SECRET_A, b2))
            self.assertEqual(self.sk(sk2)["hang_moc_thoi_gian"], wh._moc_chuan("2026-10-15 11:00:00"))
            self.assertEqual(wh.watermark(d2), wh._moc_chuan("2026-10-15 11:00:00"))
            au2 = csdl.mot("SELECT MAX(chi_tiet) m FROM audit WHERE hanh_dong='webhook_moc_hang'"
                           " AND resource_id=?", (str(d2),))
            self.assertEqual(au2["m"], self.sk(sk2)["hang_moc_thoi_gian"],
                             "nguồn CỘT và nguồn AUDIT nói hai con số khác nhau")
        finally:
            for ten, _ in them:
                if ten not in cot:
                    csdl.ghi(f"ALTER TABLE wh_su_kien DROP COLUMN {ten}")
            wh.xoa_cache_cot()

    def test_g03_khong_ghi_secret_vao_audit(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-G03", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-G03", "E-G03")
        self.gui(self.tk_a, b)
        van_ban = "\n".join(str(r["chi_tiet"] or "") for r in
                            csdl.nhieu("SELECT chi_tiet FROM audit"))
        for bi_mat in (SECRET_A, SECRET_B, SECRET_SB):
            self.assertNotIn(bi_mat, van_ban, "secret webhook lọt vào audit")

    def test_g04_duong_hang_doi_that_cung_chay(self):
        """Một ca đi qua worker nền thật, không chỉ gọi hàm trực tiếp."""
        d = _don(self.ta, self.uid, self.tk_a, "MVD-G04", "cho_lay", 1)
        wh.khoi_dong()
        try:
            tk = self.row(self.tk_a)
            b = body_hub("dang_giao", "MVD-G04", "E-G04")
            self.assertTrue(wh.kiem_chu_ky(tk, ky_hub(SECRET_A, b), b))
            wh.nhan_su_kien(tk, b, ky_hub(SECRET_A, b))
            self.assertTrue(wh.cho_rong(10), "hàng đợi không rỗng sau 10 giây")
        finally:
            wh.dung()
        self.assertEqual(self.tt_don(d)[0], "dang_giao")


# ============================================================================
class H_Polling(Nen):
    """W08 — rate limit, ngắt mạch, cách ly tenant, không tự chạy."""

    def test_h01_khong_tu_chay_khi_import(self):
        p = polling.BatDauNen(moi_giay=1)
        self.assertIsNone(p._luong, "polling tự chạy khi chưa ai bật")
        p.bat()
        self.assertTrue(p._luong.is_alive())
        p.tat()

    def test_h02_vong_nen_co_khoang_cach_toi_thieu(self):
        self.assertEqual(polling.BatDauNen(moi_giay=0.05).moi_giay_thuc,
                         polling.MOI_GIAY_TOI_THIEU,
                         "đặt 0.05 giây là nã API hãng 20 lượt/giây mà không ai chặn")
        self.assertEqual(polling.BatDauNen(moi_giay=0.05, cho_phep_nhanh=True).moi_giay_thuc, 0.05)
        self.assertEqual(polling.BatDauNen(moi_giay=600).moi_giay_thuc, 600)

    def test_h03_han_muc_tinh_rieng_tung_tenant(self):
        """Tenant A đốt hết hạn mức KHÔNG được làm tenant B hết lượt."""
        polling.xoa_han_muc()
        for _ in range(polling.GIOI_HAN_HOI_MOI_PHUT):
            self.assertTrue(polling._con_han_muc(self.ta))
        self.assertFalse(polling._con_han_muc(self.ta), "hạn mức không có trần")
        self.assertTrue(polling._con_han_muc(self.tb), "hạn mức của A ăn vào hạn mức của B!")

    def test_h04_qua_han_muc_thi_hoan_va_ghi_audit(self):
        polling.xoa_han_muc()
        _don(self.ta, self.uid, self.tk_vtp, "MVD-H04", "cho_lay", 1)
        polling._dau_vet_hoi[self.ta] = [time.monotonic()] * polling.GIOI_HAN_HOI_MOI_PHUT
        tk = polling.chay_mot_luot(self.ta)
        self.assertGreaterEqual(tk["qua_han_muc"], 1)
        self.assertEqual(tk["da_hoi"], 0)
        self.assertGreaterEqual(self.audit_co("polling_qua_han_muc"), 1)
        polling.xoa_han_muc()

    def test_h05_ma_nhap_nhang_qua_polling_cung_khong_doi_trang_thai(self):
        """Polling và webhook dùng CHUNG một chỗ quyết định — không có bảng ánh xạ thứ hai."""
        tth.bo_chot_nghia()
        qd = tth.quyet_dinh("jt", 110, su_kien_goc={"nguon": "polling"})
        self.assertIsNone(qd.trang_thai_ap)
        self.assertEqual(qd.nhan, "AMBIGUOUS")

    def test_h06_ton_trong_gioi_han_lo_cua_tai_lieu(self):
        self.assertEqual(polling.so_van_don_moi_luot("jt"), 30)
        self.assertLessEqual(polling.so_van_don_moi_luot("vtp"), polling.MAC_DINH_MOI_LUOT)
        self.assertEqual([len(x) for x in polling._gom_lo(list(range(70)), 30)], [30, 30, 10])

    def test_h07_cach_ly_tenant_o_tang_truy_van(self):
        _don(self.ta, self.uid, self.tk_vtp, "MVD-H07A", "cho_lay", 1)
        db = _don(self.tb, self.uid, self.tk_b, "MVD-H07B", "cho_lay", 1)
        ids = [r["id"] for r in polling.don_can_hoi(self.ta)]
        self.assertNotIn(db, ids, "polling của A thấy đơn của B")

    def test_h08_khong_goi_mang_that(self):
        nguon = doc_file(os.path.join(GOC_APP, "polling.py"))
        for cam in ("import requests", "import httpx", "urllib.request", "http.client",
                    "socket.socket"):
            self.assertNotIn(cam, nguon)
        for ma, lop in adapter._DANG_KY.items():
            self.assertFalse(lop.CHO_PHEP_LIVE, f"{ma} đã mở đường LIVE")


# ============================================================================
class I_ChotChanCauTruc(Nen):
    """Thêm đường mới mà quên luật là hỏng Ở ĐÂY, không chờ ai nhớ đọc tài liệu."""

    def _nguon(self, ten):
        return doc_file(os.path.join(GOC_APP, ten))

    def test_i01_moi_duong_cap_nhat_don_deu_qua_quyet_dinh(self):
        """Ai gọi `ap_trang_thai_giao` bằng mã của hãng thì phải đi qua `quyet_dinh()`."""
        for ten in ("webhook.py", "polling.py"):
            nguon = self._nguon(ten)
            if "ap_trang_thai_giao" not in nguon:
                continue
            self.assertIn("tth.quyet_dinh(", nguon,
                          f"{ten} cập nhật trạng thái mà không qua trang_thai_hang.quyet_dinh()")

    def test_i02_duong_ghi_khong_dung_truc_tiep_nghia_chua_chot(self):
        """`anh_xa(...).trang_thai` là nghĩa CHƯA chốt — cấm dùng ở đường ghi."""
        for ten in ("webhook.py", "polling.py"):
            nguon = self._nguon(ten)
            xau = re.findall(r"(?:anh_xa|normalizeTrackingStatus)\s*\([^)]*\)\s*\.trang_thai",
                             nguon)
            self.assertEqual(xau, [], f"{ten} dùng nghĩa chưa chốt để cập nhật đơn: {xau}")
            self.assertNotIn("ax.trang_thai", nguon,
                             f"{ten} còn dùng ax.trang_thai (nghĩa chưa chốt)")

    def test_i03_khong_tu_UPDATE_bang_don_hang(self):
        """Đổi trạng thái đơn phải gọi don_hang.ap_trang_thai_giao, không tự UPDATE."""
        for ten in ("webhook.py", "polling.py"):
            nguon = self._nguon(ten)
            self.assertEqual(re.findall(r"UPDATE\s+don_hang", nguon, re.I), [],
                             f"{ten} tự UPDATE bảng don_hang — vượt quyền sở hữu của AG-02")

    def test_i04_khong_tin_tenant_tu_payload(self):
        """Không có chỗ nào lấy tenant_id từ payload rồi dùng để truy vấn."""
        nguon = self._nguon("webhook.py")
        for xau in re.findall(r".*tenant.*", nguon):
            if "claim_tenant" in xau or "bo_qua" in xau or "#" in xau.split("tenant")[0]:
                continue
            self.assertNotRegex(
                xau, r"""(d|payload|sv|tho)\[['"]tenant_id['"]\]""",
                f"dòng này lấy tenant từ payload: {xau.strip()}")
        self.assertIn('tk["tenant_id"]', nguon, "tenant phải đến từ carrier_account")

    def test_i05_khong_mo_duong_LIVE_va_khong_goi_mang(self):
        nguon = self._nguon("webhook.py")
        for cam in ("import requests", "import httpx", "urllib.request", "http.client",
                    "socket.socket", "CHO_PHEP_LIVE = True"):
            self.assertNotIn(cam, nguon, f"webhook.py có '{cam}'")

    def test_i06_moi_hang_trong_bang_anh_xa_phai_khai_so_do_xac_thuc(self):
        for ma in tth.BANG:
            self.assertIn(ma, wh.SO_DO_THEO_HANG,
                          f"hãng {ma} có bảng ánh xạ nhưng chưa khai sơ đồ xác thực")
        for ma in wh.SO_DO_THEO_HANG:
            self.assertIn(ma, tth.NGUON_BANG, f"hãng {ma} chưa khai nguồn bảng ánh xạ")

    def test_i07_moi_ma_nhap_nhang_phai_du_ho_so(self):
        for (hang, ma), muc in tth.NHAP_NHANG.items():
            self.assertIn(hang, tth.BANG, f"{hang} không có bảng ánh xạ")
            self.assertIn(ma, tth.BANG[hang], f"{hang}:{ma} nhập nhằng nhưng không có trong bảng")
            self.assertTrue(muc.get("ly_do"), f"{hang}:{ma} thiếu lý do mâu thuẫn")
            self.assertTrue(muc.get("nguon"), f"{hang}:{ma} thiếu nguồn tài liệu")
            self.assertGreaterEqual(len(muc.get("nghia") or {}), 2,
                                    f"{hang}:{ma} khai nhập nhằng mà chỉ có một nghĩa")
            for khoa, n in muc["nghia"].items():
                self.assertIn("mo_ta_hang", n)
                self.assertIn("trang_thai", n)
                self.assertTrue(n.get("nguon"), f"{hang}:{ma}/{khoa} thiếu nguồn")
                self.assertTrue(n["trang_thai"] is None
                                or n["trang_thai"] in cau_hinh.HANG_TRANG_THAI_GIAO)
                self.assertNotIn(n["trang_thai"], tth.TRANG_THAI_HOAN_TAT,
                                 f"{hang}:{ma}/{khoa} dẫn tới trạng thái hoàn tất")

    def test_i08_tai_lieu_G06_co_that_va_noi_ve_ma_110(self):
        duong = os.path.join(os.path.dirname(GOC_APP), "docs", "G06_MULTI_TENANT_WEBHOOK.md")
        self.assertTrue(os.path.exists(duong), "thiếu docs/G06_MULTI_TENANT_WEBHOOK.md")
        noi_dung = doc_file(duong)
        for tu in ("110", "AMBIGUOUS", "BLOCKED", "DOCUMENTED", "scanTime", "DDL"):
            self.assertIn(tu, noi_dung, f"tài liệu G06 không nói về '{tu}'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
