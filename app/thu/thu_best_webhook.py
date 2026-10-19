# B3 — BỘ THỬ MOCK cho webhook BEST (AGENT B3).
#
# CHỈ CHẠY LOCAL + MOCK: không mở cổng HTTP, không gọi API BEST, không credentials thật,
# không tạo đơn thật. Mọi "đơn" dưới đây là dòng CSDL tạm trong `tempfile.mkdtemp`.
#
# Bộ thử này canh ĐÚNG 11 bước của `webhook_best.py`, KHÔNG chỉ canh "không nổ":
#   A. Bảng 23 mã liệt kê (đề bài nói 24 nhưng chỉ liệt kê 23 — xem `test_a01`) + ca mã lạ.
#   B. Tenant: thiếu tenant ⇒ DENY; không dùng merchant_order_code để giải tenant;
#      không cập nhật chéo tenant; payload khai tenant bị bỏ qua.
#   C. Trùng sự kiện: ACK idempotent, chỉ một dòng thô, chỉ một dòng lịch sử.
#   D. Cũ đến muộn: so `modified_at`, KHÔNG so số mã / thứ hạng; cùng mốc khác trạng thái ⇒ soát.
#   E. 605→606: máy trạng thái mở lại chiều giao; 606 cũ đến muộn không mở lại; 606 không
#      cứu đơn đã hủy nghiệp vụ.
#   F. Xác thực · lưu thất bại ⇒ KHÔNG ACK · không rò secret · đúng thân phản hồi · đủ 11 bước ·
#      BEST sandbox/production BLOCKED · sai hãng bị chặn.
#   G. Payload đủ 18 trường; dữ liệu sai bị từ chối trước khi ghi; nhãn `customer Cancel` giữ
#      nguyên nhãn gốc + cờ `customer_cancel` trong audit.
#   H. Bearer sandbox/production đúng/sai/thiếu; HMAC mock và Bearer KHÔNG lẫn nhau; token gắn
#      chết với tenant + account + `webhook_ma`; gửi lại bằng Bearer vẫn idempotent.
#   I. CSDL ĐÃ migrate: cột dấu vết + `hang_moc_thoi_gian` chỉ ghi khi sự kiện được áp.
#
# Chạy: python3 app/thu/thu_best_webhook.py
# Mã thoát: 0 = tất cả ca đạt; 1 = có ca hỏng/lỗi. "skip" chỉ dùng cho ca bị bỏ có lý do.
import hashlib
import hmac
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="vip-hub-b3-best-")

import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import quyen            # noqa: E402
import webhook as hub   # noqa: E402
import webhook_best as wb   # noqa: E402
import xac_thuc_best    # noqa: E402  — LỚP B: Bearer webhook của BEST

SECRET_A = "secret-best-webhook-A-11111111"
SECRET_B = "secret-best-webhook-B-22222222"
SECRET_GHOST = "secret-best-webhook-ghost-33333333"
SECRET_SB = "secret-best-webhook-sandbox-44444444"
SECRET_JT = "secret-jt-webhook-55555555"

WH_A = "best-wh-a"
WH_B = "best-wh-b"
WH_GHOST = "best-wh-ghost"
WH_SB = "best-wh-sandbox"
WH_JT = "jt-wh-test"

_BANG_CHUNG = []

# Ánh xạ ĐỘC LẬP với `wb.BANG_MA` — chép từ bảng tài liệu BEST (mục 7 của
# docs/BEST_EXPRESS_DOCX_AUDIT.md), KHÔNG đọc lại chính bảng đang được kiểm. Nếu ai sửa nhầm
# `BANG_MA` thì ca thử đỏ, thay vì "bảng tự khớp với chính nó".
#   mã: (trạng thái chung, cần người soát)
ANH_XA_DOC_LAP = {
    211: ("cho_lay", False),
    203: ("cho_lay", True),          # lấy hàng không thành công
    202: ("lay_hang", False),
    301: ("dang_giao", False),
    302: ("dang_giao", False),
    303: ("dang_giao", False),
    304: ("dang_giao", False),
    309: ("dang_giao", False),
    601: ("dang_giao", False),
    604: ("giao_that_bai", False),
    666: ("giao_thanh_cong", False),
    605: ("hoan_hang", False),       # xác nhận chuyển hoàn
    606: ("dang_giao", False),       # huỷ trạng thái trả hàng, mở lại chiều giao
    701: ("hoan_hang", False),
    702: ("hoan_hang", False),
    703: ("hoan_hang", False),
    704: ("hoan_hang", False),
    705: ("hoan_hang", False),
    707: ("hoan_hang", True),        # trả hàng không thành công
    708: ("hoan_hang", False),
    777: ("giao_that_bai", True),    # thất lạc
    1000: ("giao_that_bai", True),   # hư hỏng
    2: ("da_huy", False),            # huỷ đơn (customer Cancel)
}


def _ghi_bang_chung(loai, **kw):
    kw["loai"] = loai
    _BANG_CHUNG.append(kw)


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


def _dung_nen():
    global _NEN
    if "_NEN" in globals():
        return _NEN
    csdl.mo()
    quyen.seed()
    csdl.ghi("INSERT OR IGNORE INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
             (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
    for ma, ten in (("best", "BEST Express"), ("jt", "J&T Express")):
        csdl.ghi("INSERT OR IGNORE INTO carrier_providers"
                 " (ma,ten,capabilities_json,live_mo,cap_nhat_luc) VALUES (?,?,?,?,?)",
                 (ma, ten, json.dumps({"webhook": True}), 0, csdl.bay_gio()))
    uid = _user()
    ta = _tenant("Tenant A", "ta")
    tb = _tenant("Tenant B", "tb")
    tk_a = _account(ta, "best", WH_A, SECRET_A)
    tk_b = _account(tb, "best", WH_B, SECRET_B)
    # Tài khoản SANDBOX: chứng minh BEST chưa có sơ đồ xác thực đã xác minh ⇒ BLOCKED.
    tk_sb = _account(tb, "best", WH_SB, SECRET_SB, moi_truong="sandbox",
                     cred={"api_key": "khong-dung"})
    # Tài khoản hỏng: trỏ tới tenant không tồn tại. Tạo với FK TẮT rồi bật lại — dữ liệu hỏng
    # có thật phải bị chặn, không được giả vờ là "không thể xảy ra".
    csdl.ghi("PRAGMA foreign_keys=OFF")
    try:
        tk_ghost = _account(999, "best", WH_GHOST, SECRET_GHOST)
    finally:
        csdl.ghi("PRAGMA foreign_keys=ON")
    tk_jt = _account(tb, "jt", WH_JT, SECRET_JT)
    _NEN = {"uid": uid, "ta": ta, "tb": tb, "tk_a": tk_a, "tk_b": tk_b, "tk_sb": tk_sb,
            "tk_ghost": tk_ghost, "tk_jt": tk_jt}
    return _NEN


class Nen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for k, v in _dung_nen().items():
            setattr(cls, k, v)

    # ---- tiện ích CSDL ----
    def _tk(self, tk_id):
        return csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (tk_id,))

    def _don(self, don_id):
        return csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))

    def _sk(self, sk_id):
        return csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))

    def _ls(self, don_id):
        return csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don_id,))

    def _audit(self, hanh_dong=None, resource_id=None):
        sql = "SELECT * FROM audit WHERE 1=1"
        ts = []
        if hanh_dong:
            sql += " AND hanh_dong=?"
            ts.append(hanh_dong)
        if resource_id is not None:
            sql += " AND resource_id=?"
            ts.append(str(resource_id))
        return csdl.nhieu(sql + " ORDER BY id", ts)

    def _so_su_kien(self, tk_id):
        return csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                        (tk_id,))["c"]

    def _dem_su_kien_theo_ma(self, tk_id, code):
        rows = csdl.nhieu("SELECT payload_tho FROM wh_su_kien WHERE carrier_account_id=?",
                          (tk_id,))
        n = 0
        for r in rows:
            try:
                if json.loads(bytes(r["payload_tho"]))["code_best"] == code:
                    n += 1
            except Exception:
                pass
        return n

    # ---- tiện ích dựng đơn / payload / gửi ----
    def _tao_don(self, tenant_id, account_id, code, merchant=None, trang_thai_giao=None,
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
             account_id, code, trang_thai, trang_thai_giao, hang, self.uid,
             csdl.bay_gio(), csdl.bay_gio())).lastrowid

    def _payload(self, code, merchant, status, moc, **thua):
        d = {
            "code_best": code,
            "merchant_order_code": merchant,
            "cod": 150000,
            "product_price": 300000,
            "status": status,
            "status_content": "Trạng thái thử MOCK — không phải dữ liệu BEST thật",
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

    def _ky(self, secret, body):
        return {"x-webhook-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}

    def _gui_body(self, tk_id, body, secret=SECRET_A, headers=None):
        tk = self._tk(tk_id) if not hasattr(tk_id, "keys") else tk_id
        hd = dict(headers) if headers is not None else self._ky(secret, body)
        return wb.xu_ly_voi_account(tk, body, hd)

    def _gui(self, tk_id, payload, secret=SECRET_A, headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode()
        return self._gui_body(tk_id, body, secret, headers)

    def _moc(self, s):
        return hub._moc_chuan(s)


# ============================================================================
# A. BẢNG MÃ — 23 mã liệt kê + ca mã lạ
# ============================================================================
class TestA_BangMa(Nen):
    def test_a01_bang_ma_phu_du_23_ma_va_ghi_ro_chenh_lech_24(self):
        """Đề bài nói 24 nhưng liệt kê 23: mô-đun KHÔNG bịa thêm mã; bộ thử phủ 23 + mã lạ."""
        self.assertEqual(len(wb.MA_TRONG_DE_BAI), 23)
        self.assertEqual(len(set(wb.MA_TRONG_DE_BAI)), 23)
        self.assertEqual(wb.SO_MA_DE_BAI, 23)
        self.assertEqual(wb.SO_MA_LIET_KE, 23)
        self.assertIn("23", wb.GHI_CHU_SO_LUONG)
        self.assertIn("23", wb.GHI_CHU_SO_LUONG)
        self.assertEqual(set(wb.BANG_MA), set(wb.MA_TRONG_DE_BAI))
        self.assertEqual(set(ANH_XA_DOC_LAP), set(wb.MA_TRONG_DE_BAI),
                         "bảng ánh xạ độc lập không phủ đúng 23 mã")
        self.assertEqual(wb.kiem_bat_bien(), [])
        for ma in wb.MA_TRONG_DE_BAI:
            self.assertEqual(wb.BANG_MA[ma]["muc"], wb.MUC_DA_TAI_LIEU,
                             f"mã {ma} không được tự nhận là đã kiểm chứng")
            # Đối chiếu với bản chép ĐỘC LẬP, không phải với chính bảng đang kiểm.
            self.assertEqual((wb.BANG_MA[ma]["chung"], bool(wb.BANG_MA[ma]["can_soat"])),
                             ANH_XA_DOC_LAP[ma], f"mã {ma}: lệch bảng tài liệu")
        self.assertTrue(wb.BANG_MA[606]["mo_lai"])
        self.assertEqual([m for m, d in wb.BANG_MA.items() if d["mo_lai"]], [606],
                         "chỉ 606 được mang cờ mở lại chiều giao")

    def _chay_ca_ma(self, ma):
        d = wb.BANG_MA[ma]
        chung_doc_lap, can_soat_doc_lap = ANH_XA_DOC_LAP[ma]
        self.assertEqual(d["chung"], chung_doc_lap, f"mã {ma}: lệch bảng tài liệu")
        self.assertIs(bool(d["can_soat"]), can_soat_doc_lap, f"mã {ma}: cờ soát sai")
        code = f"BEST-A2-{ma}"
        merchant = f"MD-A2-{ma}"
        # 606 chỉ có nghĩa "mở lại" khi đơn đang ở trạng thái cuối. Các mã khác bắt đầu từ đơn
        # chưa có trạng thái giao để chứng minh chính bảng mã tạo ra bước đầu tiên.
        dau = "hoan_hang" if ma == 606 else None
        don_id = self._tao_don(self.ta, self.tk_a, code, merchant, dau)
        moc = f"2026-10-19T10:{ma % 60:02d}:00+07:00"
        kq = self._gui(self.tk_a, self._payload(code, merchant, ma, moc))
        self.assertEqual(kq.http, 200, f"mã {ma}: {kq!r}")
        self.assertTrue(kq.thanh_cong, f"mã {ma}: {kq.body!r}")
        self.assertFalse(kq.trung, f"mã {ma} bị coi là trùng oan")
        self.assertEqual(kq.buoc, wb.TEN_BUOC, f"mã {ma}: không đủ 11 bước")
        self.assertEqual(kq.don_id, don_id)

        don = self._don(don_id)
        if chung_doc_lap == "da_huy":
            self.assertIsNone(don["trang_thai_giao"], "mã hủy 2 không được tự đổi trạng thái đơn")
            self.assertEqual(kq.ket_cuc, "ghi_nhan")
            self.assertEqual(len(self._ls(don_id)), 0, "mã hủy 2 không được bịa dòng lịch sử")
        else:
            self.assertEqual(don["trang_thai_giao"], chung_doc_lap, f"mã {ma}")
            self.assertEqual(kq.ket_cuc, "cap_nhat", f"mã {ma}")
            self.assertEqual(len(self._ls(don_id)), 1, f"mã {ma}: thiếu lịch sử")

        sk = self._sk(kq.su_kien_id)
        self.assertEqual(sk["trang_thai"], "xong")
        tho = json.loads(bytes(sk["payload_tho"]))
        self.assertEqual(tho["status"], ma)
        self.assertIn("status_content", tho)
        self.assertEqual(set(wb.TRUONG_PAYLOAD) - set(tho), set(), f"mã {ma}: thiếu trường thô")
        _ghi_bang_chung("ma", ma=ma, chung=chung_doc_lap, ket_cuc=kq.ket_cuc,
                        mo_lai=d["mo_lai"], don_id=don_id)

    def test_a03_ma_la_la_ca_thu_24_khong_doi_don_nhung_van_luu(self):
        """Đối chứng thứ 24: mã lạ. Phải LƯU THÔ + ACK, KHÔNG đoán nghĩa, KHÔNG đổi đơn."""
        code = "BEST-A3-LA"
        merchant = "MD-A3-LA"
        don_id = self._tao_don(self.ta, self.tk_a, code, merchant)
        kq = self._gui(self.tk_a, self._payload(code, merchant, 99999,
                                                "2026-10-19T11:00:00+07:00"))
        self.assertEqual(kq.http, 200)
        self.assertTrue(kq.thanh_cong)
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], None)
        self.assertEqual(len(self._ls(don_id)), 0)
        self.assertEqual(self._sk(kq.su_kien_id)["trang_thai"], "xong")
        self.assertTrue(self._audit("webhook_best_bo_qua", kq.su_kien_id))
        _ghi_bang_chung("ma", ma=99999, chung=None, ket_cuc=kq.ket_cuc, mo_lai=False,
                        don_id=don_id)


# 23 ca riêng biệt, một ca cho mỗi mã — để "số ca" trong bằng chứng đếm được, không gộp.
def _lam_ca_ma(ma):
    def ca(self):
        self._chay_ca_ma(ma)
    ca.__name__ = f"test_a02_ma_{ma}"
    ca.__doc__ = f"Mã BEST {ma}: chuẩn hoá + lưu thô + (nếu áp được) cập nhật đơn/lịch sử."
    return ca


for _ma in wb.MA_TRONG_DE_BAI:
    setattr(TestA_BangMa, f"test_a02_ma_{_ma}", _lam_ca_ma(_ma))


# ============================================================================
# B. TENANT — không dùng merchant_order_code, không chéo tenant
# ============================================================================
class TestB_Tenant(Nen):
    def test_b01_thieu_tenant_thi_deny_va_khong_ghi_su_kien(self):
        """Tài khoản trỏ tenant không tồn tại ⇒ DENY ở bước 3, không lưu, không ACK thành công."""
        code = "BEST-B1"
        merchant = "MD-B1"
        truoc = self._so_su_kien(self.tk_ghost)
        kq = self._gui(self.tk_ghost, self._payload(code, merchant, 211,
                                                   "2026-10-19T11:01:00+07:00"),
                       secret=SECRET_GHOST)
        self.assertEqual(kq.http, 403)
        self.assertEqual(kq.body["Result"], 0)
        self.assertIn("tenant", kq.body["Message"])
        self.assertIn("xac_dinh_tenant", kq.buoc)
        self.assertNotIn("luu_raw_event_an_toan", kq.buoc)
        self.assertEqual(self._so_su_kien(self.tk_ghost), truoc)
        self.assertTrue(self._audit("webhook_best_tu_choi", self.tk_ghost))

        # ĐỐI CHỨNG ĐƯỜNG: cùng payload với tài khoản có tenant thật ⇒ qua bước 3 và áp được.
        don_id = self._tao_don(self.ta, self.tk_a, code, merchant)
        kq2 = self._gui(self.tk_a, self._payload(code, merchant, 211,
                                                 "2026-10-19T11:01:00+07:00"))
        self.assertEqual(kq2.http, 200)
        self.assertTrue(kq2.thanh_cong)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "cho_lay")

    def test_b02_merchant_order_code_khong_quyet_dinh_tenant(self):
        """Mã đơn của tenant B không kéo được đơn tenant B khi callback thuộc tài khoản A."""
        a_code, a_md = "BEST-B2-A", "MD-B2-A"
        b_code, b_md = "BEST-B2-B", "MD-B2-B"
        a_don = self._tao_don(self.ta, self.tk_a, a_code, a_md)
        b_don = self._tao_don(self.tb, self.tk_b, b_code, b_md)
        truoc = self._so_su_kien(self.tk_a)

        # (1) tracking của A nhưng mã đơn của B ⇒ lệch cặp, KHÔNG áp đơn nào.
        kq1 = self._gui(self.tk_a, self._payload(a_code, b_md, 301,
                                                 "2026-10-19T11:02:00+07:00"))
        self.assertEqual(kq1.http, 200)
        self.assertTrue(kq1.thanh_cong)
        self.assertEqual(kq1.ket_cuc, "ghi_nhan")
        self.assertIsNone(self._don(a_don)["trang_thai_giao"])
        self.assertIsNone(self._don(b_don)["trang_thai_giao"])
        self.assertTrue(self._audit("webhook_best_bo_qua", kq1.su_kien_id))

        # (2) tracking của B + mã đơn của B, nhưng callback vào tài khoản A ⇒ không thấy đơn
        # trong tenant A, TUYỆT ĐỐI không đụng đơn B.
        kq2 = self._gui(self.tk_a, self._payload(b_code, b_md, 302,
                                                 "2026-10-19T11:03:00+07:00"))
        self.assertEqual(kq2.http, 200)
        self.assertTrue(kq2.thanh_cong)
        self.assertEqual(kq2.ket_cuc, "ghi_nhan")
        self.assertIsNone(self._don(b_don)["trang_thai_giao"])
        self.assertEqual(self._so_su_kien(self.tk_a), truoc + 2,
                         "sự kiện hợp lệ nhưng không khớp đơn vẫn phải được lưu bền")

    def test_b03_hai_tenant_cung_tracking_code_khong_cap_nhat_cheo(self):
        """Cùng một mã vận đơn tồn tại ở HAI tenant: chỉ đơn của tenant sở hữu callback đổi."""
        code = "BEST-B3-SHARED"
        a_don = self._tao_don(self.ta, self.tk_a, code, "MD-B3-A")
        b_don = self._tao_don(self.tb, self.tk_b, code, "MD-B3-B")
        kq = self._gui(self.tk_a, self._payload(code, "MD-B3-A", 301,
                                                "2026-10-19T11:04:00+07:00"))
        self.assertEqual(kq.http, 200)
        self.assertEqual(self._don(a_don)["trang_thai_giao"], "dang_giao")
        self.assertIsNone(self._don(b_don)["trang_thai_giao"],
                         "đơn tenant B bị cập nhật chéo — lỗi multi-tenant")
        self.assertEqual(kq.don_id, a_don)

    def test_b04_payload_khai_tenant_bi_bo_qua_va_ghi_audit(self):
        """Payload có tenant_id/tenantId/tenant của tenant khác: dùng tenant của ACCOUNT."""
        code = "BEST-B4"
        a_don = self._tao_don(self.ta, self.tk_a, code, "MD-B4-A")
        b_don = self._tao_don(self.tb, self.tk_b, "BEST-B4-B", "MD-B4-B")
        p = self._payload(code, "MD-B4-A", 203, "2026-10-19T11:05:00+07:00",
                          tenant_id=self.tb, tenantId=self.tb, tenant="tb")
        kq = self._gui(self.tk_a, p)
        self.assertEqual(kq.http, 200)
        self.assertEqual(kq.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(a_don)["trang_thai_giao"], "cho_lay")
        self.assertIsNone(self._don(b_don)["trang_thai_giao"])
        self.assertTrue(csdl.mot(
            "SELECT 1 x FROM audit WHERE hanh_dong='webhook_best_claim_tenant_bi_bo_qua'"
            " AND tenant_id=?", (self.ta,)))


# ============================================================================
# C. TRÙNG SỰ KIỆN — ACK idempotent
# ============================================================================
class TestC_Trung(Nen):
    def test_c01_gui_lai_cung_su_kien_chi_mot_dong_va_mot_lich_su(self):
        code = "BEST-C1"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-C1")
        p = self._payload(code, "MD-C1", 301, "2026-10-19T11:06:00+07:00")
        kq1 = self._gui(self.tk_a, p)
        kq2 = self._gui(self.tk_a, p)
        self.assertTrue(kq1.thanh_cong)
        self.assertTrue(kq2.thanh_cong)
        self.assertFalse(kq1.trung)
        self.assertTrue(kq2.trung)
        self.assertEqual(kq1.su_kien_id, kq2.su_kien_id)
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_a, code), 1)
        self.assertEqual(len(self._ls(don_id)), 1, "gửi lại không được ghi lịch sử lần hai")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")
        self.assertTrue(self._audit("webhook_best_trung", kq1.su_kien_id))

    def test_c02_cung_su_kien_khac_dinh_dang_json_van_la_trung(self):
        code = "BEST-C2"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-C2")
        p = self._payload(code, "MD-C2", 301, "2026-10-19T11:07:00+07:00")
        body1 = json.dumps(p, ensure_ascii=False).encode()
        body2 = json.dumps(p, ensure_ascii=False, indent=2, sort_keys=True).encode()
        self.assertNotEqual(body1, body2)
        kq1 = self._gui_body(self.tk_a, body1)
        kq2 = self._gui_body(self.tk_a, body2)
        self.assertTrue(kq1.thanh_cong)
        self.assertTrue(kq2.thanh_cong)
        self.assertTrue(kq2.trung)
        self.assertEqual(kq1.su_kien_id, kq2.su_kien_id)
        self.assertEqual(len(self._ls(don_id)), 1)


# ============================================================================
# D. CŨ ĐẾN MUỘN — so modified_at, không so số mã
# ============================================================================
class TestD_DenMuon(Nen):
    def test_d01_su_kien_cu_den_muon_khong_ghi_de_trang_thai_moi(self):
        """301 (dang_giao) đến trước; 604 (giao_that_bai) đến sau nhưng modified_at CŨ ⇒ KHÔNG áp.

        Chọn 604 — khác trạng thái và khác hạng — để nếu chống đến muộn hỏng thì trạng thái đơn
        ĐỔI THẬT và ca thử bắt được; dùng một mã cùng trạng thái (302 cũng là dang_giao) sẽ
        không phân biệt được "bỏ qua vì đến muộn" với "áp nhưng trùng trạng thái".
        """
        code = "BEST-D1"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-D1")
        kq1 = self._gui(self.tk_a, self._payload(code, "MD-D1", 301,
                                                 "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq1.ket_cuc, "cap_nhat")
        kq2 = self._gui(self.tk_a, self._payload(code, "MD-D1", 604,
                                                 "2026-10-19T09:00:00+07:00"))
        self.assertEqual(kq2.http, 200)
        self.assertTrue(kq2.thanh_cong)
        self.assertEqual(kq2.ket_cuc, "ghi_nhan")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao",
                         "webhook cũ đã ghi đè trạng thái mới hơn")
        self.assertEqual(len(self._ls(don_id)), 1,
                         "sự kiện đến muộn không được ghi lịch sử trạng thái")
        self.assertTrue(self._audit("webhook_best_bo_qua", kq2.su_kien_id))
        self.assertEqual(wb._moc_da_ap(don_id, self.ta),
                         self._moc("2026-10-19T10:00:00+07:00"))
        _ghi_bang_chung("cu_den_muon", ma=604, moc_cu="09:00", moc_da_ap="10:00",
                        trang_thai_sau=self._don(don_id)["trang_thai_giao"], ket_cuc="giu")

    def test_d02_khong_gia_dinh_ma_tang_dan_605_moi_hon_606_van_ap(self):
        """606 (số lớn hơn) đến trước, 605 (số nhỏ hơn) đến sau với modified_at MỚI HƠN ⇒ áp."""
        code = "BEST-D2"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-D2", "hoan_hang")
        kq1 = self._gui(self.tk_a, self._payload(code, "MD-D2", 606,
                                                 "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq1.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")
        kq2 = self._gui(self.tk_a, self._payload(code, "MD-D2", 605,
                                                 "2026-10-19T11:00:00+07:00"))
        self.assertEqual(kq2.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "hoan_hang",
                         "605 mới hơn phải áp được dù số nhỏ hơn 606")
        _ghi_bang_chung("cu_den_muon", ma=605, moc_cu="11:00 > 10:00", moc_da_ap="11:00",
                        trang_thai_sau="hoan_hang", ket_cuc="ap")

    def test_d03_cung_modified_at_nhung_khac_trang_thai_thi_khong_doan(self):
        code = "BEST-D3"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-D3")
        self._gui(self.tk_a, self._payload(code, "MD-D3", 301,
                                           "2026-10-19T10:00:00+07:00"))
        kq = self._gui(self.tk_a, self._payload(code, "MD-D3", 604,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertIn("xung đột mốc", kq.chi_tiet["ly_do"])
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

    def test_d04_modified_at_epoch_ms_int_va_chuoi_cung_dong_ho(self):
        """Đặc tả: `modified_at` là epoch mili giây. Số int và chuỗi số phải cùng một mốc.

        2026-10-19 10:00 +07 = 1792378800000 ms; 09:00 = 1792375200000; 11:00 = 1792382400000.
        Ca này canh CẢ hai dạng, và canh thứ tự đến muộn bằng số chứ không bằng chuỗi ISO.
        """
        code = "BEST-D4"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-D4")
        kq1 = self._gui(self.tk_a, self._payload(code, "MD-D4", 301, 1792378800000))
        self.assertEqual(kq1.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

        # Cùng mốc 10:00 nhưng viết dạng chuỗi 13 chữ số ⇒ CÙNG sự kiện (trùng), không phải mới.
        kq2 = self._gui(self.tk_a, self._payload(code, "MD-D4", 301, "1792378800000"))
        self.assertTrue(kq2.trung)
        self.assertEqual(len(self._ls(don_id)), 1)

        # 09:00 (chuỗi) đến sau ⇒ cũ hơn mốc đã áp, không được lùi trạng thái.
        kq3 = self._gui(self.tk_a, self._payload(code, "MD-D4", 302, "1792375200000"))
        self.assertEqual(kq3.ket_cuc, "ghi_nhan")
        self.assertIn("đến muộn", kq3.chi_tiet["ly_do"])
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

        # 11:00 bằng số int ⇒ mới hơn, được áp.
        kq4 = self._gui(self.tk_a, self._payload(code, "MD-D4", 666, 1792382400000))
        self.assertEqual(kq4.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "giao_thanh_cong")
        self.assertEqual(wb._moc_da_ap(don_id, self.ta),
                         hub._moc_chuan(1792382400000))


# ============================================================================
# E. 605 → 606: MÁY TRẠNG THÁI, KHÔNG PHẢI SO SỐ
# ============================================================================
class TestE_605_606(Nen):
    def test_e01_605_roi_606_mo_lai_chieu_giao(self):
        code = "BEST-E1"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-E1", "dang_giao")
        kq1 = self._gui(self.tk_a, self._payload(code, "MD-E1", 605,
                                                 "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq1.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "hoan_hang")
        kq2 = self._gui(self.tk_a, self._payload(code, "MD-E1", 606,
                                                 "2026-10-19T11:00:00+07:00"))
        self.assertEqual(kq2.ket_cuc, "cap_nhat")
        don = self._don(don_id)
        self.assertEqual(don["trang_thai_giao"], "dang_giao")
        self.assertEqual(don["hang_trang_thai_giao"],
                         cau_hinh.HANG_TRANG_THAI_GIAO["dang_giao"],
                         "606 phải hạ hạng trạng thái khi mở lại chiều giao")
        ls = self._ls(don_id)
        self.assertEqual(len(ls), 2)
        self.assertIn("mở lại chiều giao", ls[-1]["noi_dung"])
        self.assertEqual(wb._moc_da_ap(don_id, self.ta),
                         self._moc("2026-10-19T11:00:00+07:00"))
        _ghi_bang_chung("605_606", buoc="605 → 606", truoc="dang_giao", sau="hoan_hang → dang_giao",
                        hang_sau=don["hang_trang_thai_giao"], lich_su=len(ls), ket_cuc="ap")

    def test_e02_606_tu_trang_thai_cuoi_giao_thanh_cong_van_mo_lai_duoc(self):
        code = "BEST-E2"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-E2", "giao_thanh_cong")
        kq = self._gui(self.tk_a, self._payload(code, "MD-E2", 606,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.ket_cuc, "cap_nhat")
        don = self._don(don_id)
        self.assertEqual(don["trang_thai_giao"], "dang_giao")
        self.assertEqual(don["hang_trang_thai_giao"], 3)
        _ghi_bang_chung("605_606", buoc="giao_thanh_cong → 606",
                        truoc="giao_thanh_cong", sau="dang_giao", hang_sau=3,
                        lich_su=1, ket_cuc="ap")

    def test_e03_606_cu_den_muon_khong_mo_lai(self):
        code = "BEST-E3"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-E3", "hoan_hang")
        self._gui(self.tk_a, self._payload(code, "MD-E3", 606,
                                           "2026-10-19T11:00:00+07:00"))
        kq = self._gui(self.tk_a, self._payload(code, "MD-E3", 606,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao",
                         "606 cũ đã mở lại lần nữa — chống đến muộn hỏng")
        self.assertTrue(self._audit("webhook_best_bo_qua", kq.su_kien_id))

    def test_e04_606_khong_cuu_don_da_huy_nghiep_vu(self):
        code = "BEST-E4"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-E4", None, trang_thai="huy")
        kq = self._gui(self.tk_a, self._payload(code, "MD-E4", 606,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertEqual(self._don(don_id)["trang_thai"], "huy")
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertIn("đơn đã hủy", kq.chi_tiet["ly_do"])

    def test_e05_duyet_ca_23_ma_chi_606_mo_duoc_trang_thai_cuoi(self):
        """Đơn đang `giao_thanh_cong`: duyệt LẦN LƯỢT cả 23 mã, chỉ 606 được mở lại.

        Đây là ca canh bảng mã + máy trạng thái CÙNG LÚC: thêm một mã mới mang cờ `mo_lai` sẽ
        làm ca này đỏ ngay; một mã thường lọt qua trạng thái cuối cũng đỏ.
        """
        for i, ma in enumerate(wb.MA_TRONG_DE_BAI):
            with self.subTest(ma=ma):
                code = f"BEST-E5-{ma}"
                merchant = f"MD-E5-{ma}"
                don_id = self._tao_don(self.ta, self.tk_a, code, merchant, "giao_thanh_cong")
                moc = 1792378800000 + i * 60_000
                kq = self._gui(self.tk_a, self._payload(code, merchant, ma, moc))
                self.assertEqual(kq.http, 200, f"mã {ma}: {kq!r}")
                self.assertTrue(kq.thanh_cong, f"mã {ma}: {kq.body!r}")
                don = self._don(don_id)
                if ma == 606:
                    self.assertEqual(kq.ket_cuc, "cap_nhat", "606 phải mở lại chiều giao")
                    self.assertEqual(don["trang_thai_giao"], "dang_giao")
                    self.assertEqual(don["hang_trang_thai_giao"], 3)
                    self.assertEqual(len(self._ls(don_id)), 1)
                else:
                    self.assertEqual(kq.ket_cuc, "ghi_nhan",
                                     f"mã {ma} không được mở lại trạng thái cuối")
                    self.assertEqual(don["trang_thai_giao"], "giao_thanh_cong",
                                     f"mã {ma} đã ghi đè trạng thái cuối")
                    self.assertEqual(len(self._ls(don_id)), 0,
                                     f"mã {ma} không được bịa dòng lịch sử")


# ============================================================================
# F. XÁC THỰC · LƯU THẤT BẠI · BÍ MẬT · PHẢN HỒI · 11 BƯỚC
# ============================================================================
class TestF_AnToan(Nen):
    def test_f01_sai_chu_ky_khong_luu_va_khong_doi_don(self):
        code = "BEST-F1"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-F1")
        truoc = self._so_su_kien(self.tk_a)
        payload = self._payload(code, "MD-F1", 301, "2026-10-19T10:00:00+07:00")
        body = json.dumps(payload).encode()
        kq = self._gui_body(self.tk_a, body, headers={"x-webhook-signature": "0" * 64})
        self.assertEqual(kq.http, 401)
        self.assertEqual(kq.body["Result"], 0)
        self.assertEqual(self._so_su_kien(self.tk_a), truoc)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertTrue(self._audit("webhook_best_tu_choi", self.tk_a))

        # ĐỐI CHỨNG ĐƯỜNG: đúng chữ ký trên CÙNG thân yêu cầu thì qua và cập nhật.
        kq_ok = self._gui_body(self.tk_a, body)
        self.assertEqual(kq_ok.http, 200)
        self.assertTrue(kq_ok.thanh_cong)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

    def test_f02_luu_that_bai_thi_khong_ack_thanh_cong(self):
        """Có ĐỐI CHỨNG DƯƠNG: cùng payload chạy thật thì ACK; khi INSERT wh_su_kien nổ thì KHÔNG."""
        # Đối chứng dương
        code_ok = "BEST-F2-OK"
        don_ok = self._tao_don(self.ta, self.tk_a, code_ok, "MD-F2-OK")
        kq_ok = self._gui(self.tk_a, self._payload(code_ok, "MD-F2-OK", 301,
                                                   "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq_ok.http, 200)
        self.assertTrue(kq_ok.thanh_cong)
        self.assertEqual(self._don(don_ok)["trang_thai_giao"], "dang_giao")

        # Đối chứng âm: chỉ câu INSERT wh_su_kien nổ, audit vẫn ghi được.
        code = "BEST-F2-FAIL"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-F2-FAIL")
        goc = csdl.ghi

        def ghi_hong(sql, tham_so=()):
            if "INSERT INTO wh_su_kien" in sql:
                raise csdl.LoiVanHanh("disk I/O error (MOCK fault injection)")
            return goc(sql, tham_so)

        with mock.patch.object(csdl, "ghi", side_effect=ghi_hong):
            kq = self._gui(self.tk_a, self._payload(code, "MD-F2-FAIL", 301,
                                                    "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.http, 500)
        self.assertEqual(kq.body["Result"], 0,
                         "lưu thất bại nhưng vẫn ACK thành công — vi phạm bước 7")
        self.assertNotEqual(kq.body.get("Message"), "")
        self.assertEqual(kq.ket_cuc, "loi_luu")
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_a, code), 0)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertEqual(len(self._ls(don_id)), 0)
        self.assertTrue(self._audit("webhook_best_loi_luu", self.tk_a))

    def test_f03_khong_ghi_secret_token_chu_ky_vao_tho_audit_response(self):
        code = "BEST-F3"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-F3")
        payload = self._payload(code, "MD-F3", 301, "2026-10-19T10:00:00+07:00",
                                token="SECRET-PAYLOAD-XYZ")
        body = json.dumps(payload, ensure_ascii=False).encode()
        headers = self._ky(SECRET_A, body)
        headers.update({"authorization": "Bearer SECRET-TOKEN-XYZ",
                        "cookie": "phien=SECRET-COOKIE-XYZ",
                        "x-custom": "SECRET-CUSTOM-XYZ"})
        kq = self._gui_body(self.tk_a, body, headers=headers)
        self.assertEqual(kq.http, 200)
        self.assertNotIn("SECRET", json.dumps(kq.body, ensure_ascii=False))

        sk = self._sk(kq.su_kien_id)
        headers_json = sk["headers_json"]
        payload_tho = bytes(sk["payload_tho"]).decode("utf-8")
        for bi_mat in ("SECRET-TOKEN-XYZ", "SECRET-COOKIE-XYZ", "SECRET-CUSTOM-XYZ",
                       "SECRET-PAYLOAD-XYZ"):
            self.assertNotIn(bi_mat, headers_json)
            self.assertNotIn(bi_mat, payload_tho)
        self.assertNotIn("x-webhook-signature", headers_json.lower())
        self.assertNotIn("authorization", headers_json.lower())
        self.assertIn("[DA_CHE]", payload_tho)

        for r in csdl.nhieu("SELECT chi_tiet, dia_chi FROM audit"):
            van_ban = f"{r['chi_tiet']} {r['dia_chi']}"
            for bi_mat in ("SECRET-TOKEN-XYZ", "SECRET-COOKIE-XYZ", "SECRET-CUSTOM-XYZ",
                           "SECRET-PAYLOAD-XYZ"):
                self.assertNotIn(bi_mat, van_ban)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

    def test_f04_than_phan_hoi_thanh_cong_dung_dac_ta(self):
        code = "BEST-F4"
        self._tao_don(self.ta, self.tk_a, code, "MD-F4")
        kq = self._gui(self.tk_a, self._payload(code, "MD-F4", 301,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.body, {"Result": 1, "Message": ""})
        self.assertEqual(set(kq.body), {"Result", "Message"})
        self.assertEqual(kq.http, 200)
        # Ca từ chối cũng chỉ dùng đúng hai khóa, Result khác 1, Message không rỗng.
        body = json.dumps(self._payload("BEST-F4-X", "MD-F4-X", 301,
                                        "2026-10-19T10:00:00+07:00")).encode()
        kq2 = self._gui_body(self.tk_a, body, headers={"x-webhook-signature": "x"})
        self.assertEqual(set(kq2.body), {"Result", "Message"})
        self.assertNotEqual(kq2.body["Result"], 1)
        self.assertNotEqual(kq2.body["Message"], "")

    def test_f05_du_11_buoc_dung_thu_tu(self):
        code = "BEST-F5"
        self._tao_don(self.ta, self.tk_a, code, "MD-F5")
        kq = self._gui(self.tk_a, self._payload(code, "MD-F5", 301,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertEqual(kq.buoc, wb.TEN_BUOC)
        self.assertEqual(len(kq.buoc), 11)
        self.assertEqual(wb.kiem_bat_bien(), [])

    def test_f06_best_sandbox_bi_blocked_khong_doan_chu_ky(self):
        code = "BEST-F6"
        p = self._payload(code, "MD-F6", 301, "2026-10-19T10:00:00+07:00")
        kq = self._gui(self.tk_sb, p, secret=SECRET_SB)
        self.assertEqual(kq.http, 401)
        self.assertEqual(kq.body["Result"], 0)
        self.assertIn("BLOCKED", kq.body["Message"])
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_sb, code), 0)
        self.assertTrue(self._audit("webhook_best_tu_choi", self.tk_sb))

        # ĐỐI CHỨNG ĐƯỜNG: cùng payload vào tài khoản MOCK thì qua — BLOCKED là do thiếu sơ đồ
        # xác thực thật, không phải do payload hay do mã BEST.
        kq_ok = self._gui(self.tk_a, p)
        self.assertEqual(kq_ok.http, 200)
        self.assertTrue(kq_ok.thanh_cong)

    def test_f07_sai_hang_bi_tu_choi_o_buoc_tai_khoan_hang(self):
        code = "BEST-F7"
        body = json.dumps(self._payload(code, "MD-F7", 301,
                                        "2026-10-19T10:00:00+07:00")).encode()
        kq = wb.xu_ly_theo_dinh_danh(WH_JT, self._ky(SECRET_JT, body), body)
        self.assertEqual(kq.http, 403)
        self.assertEqual(kq.body["Result"], 0)
        self.assertIn("xac_dinh_tai_khoan_hang", kq.buoc)
        self.assertNotIn("luu_raw_event_an_toan", kq.buoc)
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_jt, code), 0)

        # ĐỐI CHỨNG ĐƯỜNG: cùng thân, đúng định danh BEST thì qua bước 2.
        kq_ok = wb.xu_ly_theo_dinh_danh(WH_A, self._ky(SECRET_A, body), body)
        self.assertEqual(kq_ok.http, 200)
        self.assertTrue(kq_ok.thanh_cong)

    def test_f08_dinh_danh_webhook_khong_ton_tai_tra_404(self):
        kq = wb.xu_ly_theo_dinh_danh("khong-co-webhook-nay",
                                     {"x-webhook-signature": "x"}, b"{}")
        self.assertEqual(kq.http, 404)
        self.assertNotEqual(kq.body["Result"], 1)

    def test_f09_payload_sai_bi_tu_choi_truoc_khi_luu(self):
        code_loi = "BEST-F9"
        truoc = self._so_su_kien(self.tk_a)
        for ten, payload in (
            ("thiếu status", self._payload(code_loi, "MD-F9", 301,
                                           "2026-10-19T10:00:00+07:00") | {"status": None}),
            ("cod âm", self._payload(code_loi, "MD-F9", 301,
                                     "2026-10-19T10:00:00+07:00", cod=-1)),
            ("modified_at rác", self._payload(code_loi, "MD-F9", 301, "không-phải-thời-gian")),
        ):
            with self.subTest(ten=ten):
                kq = self._gui(self.tk_a, payload)
                self.assertEqual(kq.http, 422, ten)
                self.assertEqual(kq.body["Result"], 0, ten)
        self.assertEqual(self._so_su_kien(self.tk_a), truoc,
                         "payload sai vẫn bị ghi thô — bước 4/5 phải chặn trước bước 7")

    def test_f10_than_qua_lon_bi_tu_choi_413(self):
        than = b'{"x":"' + (b"A" * (wb.GIOI_HAN_BODY + 10)) + b'"}'
        kq = wb.xu_ly_voi_account(self._tk(self.tk_a), than, self._ky(SECRET_A, than))
        self.assertEqual(kq.http, 413)
        self.assertEqual(kq.body["Result"], 0)

    def test_f11_chi_mot_cau_update_don_hang_va_danh_cho_606(self):
        """Chốt cấu trúc: mọi bước thường đi qua Order Service, chỉ 606 được tự UPDATE.

        Đây là bản sao TINH THẦN của `thu_webhook.test_i03` cho tệp mới. Nếu ai thêm một câu
        `UPDATE don_hang` thứ hai (ví dụ để "tiện" sửa trạng thái), ca này hỏng ngay.
        """
        nguon = open(os.path.join(GOC_APP, "webhook_best.py"), encoding="utf-8").read()
        # Đếm CÂU SQL thật (chuỗi bắt đầu bằng dấu nháy), không đếm chữ trong chú thích.
        self.assertEqual(len(re.findall(r"""["']UPDATE\s+don_hang""", nguon, re.I)), 1,
                         "webhook_best.py có nhiều hơn một câu UPDATE don_hang")
        self.assertIn("def _mo_lai_chieu_giao", nguon)
        self.assertIn("don_hang.ap_trang_thai_giao", nguon)

    def test_f12_dlq_va_gui_lai_su_kien_da_luu_van_hoan_tat(self):
        """Lỗi SAU bước 7: sự kiện đã bền nhưng chưa xử lý xong ⇒ 500 + dlq, KHÔNG ACK xong.

        Lượt gửi lại dùng ĐÚNG dòng thô cũ (không tạo sự kiện thứ hai), xử lý nốt và chỉ ghi
        MỘT dòng lịch sử. Đây là ca canh "ACK chỉ sau khi lưu bền + xử lý xong", bổ khuyết cho
        ca f02 (lỗi NGAY ở bước lưu).
        """
        code = "BEST-F12"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-F12")
        p = self._payload(code, "MD-F12", 301, "2026-10-19T10:00:00+07:00")

        def no_ra(*_a, **_kw):
            raise RuntimeError("hỏng sau khi đã lưu thô (MOCK fault injection)")

        with mock.patch.object(wb, "_cap_nhat_don", side_effect=no_ra):
            kq_hong = self._gui(self.tk_a, p)
        self.assertEqual(kq_hong.http, 500)
        self.assertEqual(kq_hong.body["Result"], 0)
        self.assertEqual(kq_hong.ket_cuc, "loi_xu_ly")
        self.assertEqual(self._sk(kq_hong.su_kien_id)["trang_thai"], "dlq")
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertEqual(len(self._ls(don_id)), 0)

        kq_lai = self._gui(self.tk_a, p)
        self.assertEqual(kq_lai.http, 200)
        self.assertTrue(kq_lai.thanh_cong)
        self.assertFalse(kq_lai.trung)
        self.assertEqual(kq_lai.su_kien_id, kq_hong.su_kien_id,
                         "gửi lại phải dùng đúng sự kiện đã lưu, không tạo dòng thứ hai")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")
        self.assertEqual(len(self._ls(don_id)), 1)
        self.assertEqual(self._sk(kq_lai.su_kien_id)["trang_thai"], "xong")

    def test_f13_audit_cuoi_hong_thi_khong_ack_va_cho_thu_lai(self):
        """Bước 11 (audit) hỏng sau khi đã áp đơn: KHÔNG được ACK xong, phải đánh dấu chờ thử lại.

        Sự kiện + đơn đã bền, nhưng mất dấu audit là mất khả năng điều tra; trả 200 lúc này sẽ
        che mất lỗi. Lượt gửi lại thấy mốc đã áp nên KHÔNG cập nhật đơn lần hai, chỉ hoàn tất
        audit + đánh dấu xong.
        """
        code = "BEST-F13"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-F13")
        p = self._payload(code, "MD-F13", 301, "2026-10-19T10:00:00+07:00")
        with mock.patch.object(wb, "_audit", return_value=False):
            kq_hong = self._gui(self.tk_a, p)
        self.assertEqual(kq_hong.http, 500)
        self.assertEqual(kq_hong.ket_cuc, "loi_audit")
        self.assertEqual(kq_hong.body["Result"], 0)
        self.assertEqual(self._sk(kq_hong.su_kien_id)["trang_thai"], "cho_thu_lai")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")
        self.assertEqual(len(self._ls(don_id)), 1)

        kq_lai = self._gui(self.tk_a, p)
        self.assertEqual(kq_lai.http, 200)
        self.assertTrue(kq_lai.thanh_cong)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")
        self.assertEqual(len(self._ls(don_id)), 1, "gửi lại đã cập nhật đơn lần hai")
        self.assertEqual(self._sk(kq_lai.su_kien_id)["trang_thai"], "xong")

        # Đối chứng dương: cùng payload trên đơn khác, audit KHÔNG hỏng ⇒ 200 như thường.
        don_ok = self._tao_don(self.ta, self.tk_a, "BEST-F13-OK", "MD-F13-OK")
        kq_ok = self._gui(self.tk_a, self._payload("BEST-F13-OK", "MD-F13-OK", 301,
                                                   "2026-10-19T10:01:00+07:00"))
        self.assertEqual(kq_ok.http, 200)
        self.assertEqual(self._don(don_ok)["trang_thai_giao"], "dang_giao")


# ============================================================================
# G. PAYLOAD ĐỦ 18 TRƯỜNG + GIỮ NGUYÊN THÔ
# ============================================================================
class TestG_Payload(Nen):
    def test_g01_du_18_truong_va_giu_nguyen_raw_status_status_content(self):
        code = "BEST-G1"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-G1")
        p = self._payload(code, "MD-G1", 301, "2026-10-19T10:00:00+07:00",
                          status_content="Đã giao cho khách — nội dung RAW của BEST")
        kq = self._gui(self.tk_a, p)
        self.assertTrue(kq.thanh_cong)
        tho = json.loads(bytes(self._sk(kq.su_kien_id)["payload_tho"]))
        self.assertEqual(set(wb.TRUONG_PAYLOAD) - set(tho), set())
        self.assertEqual(tho["status"], 301)
        self.assertEqual(tho["status_content"], p["status_content"])
        self.assertEqual(tho["cod"], 150000)
        self.assertEqual(tho["merchant_order_code"], "MD-G1")
        self.assertEqual(tho["modified_at"], p["modified_at"])
        don = self._don(don_id)
        self.assertEqual(don["trang_thai_giao"], "dang_giao")
        # Lịch sử do Order Service ghi (ap_trang_thai_giao), không phải mô-đun tự chèn.
        ls = self._ls(don_id)[0]["noi_dung"]
        self.assertIn("dang_giao", ls)
        # Trạng thái RAW vẫn còn trong audit + payload thô, dù lịch sử chỉ ghi trạng thái chung.
        audit = self._audit("webhook_best_cap_nhat_don", kq.su_kien_id)
        self.assertTrue(audit)
        self.assertIn("301", audit[0]["chi_tiet"])

    def test_g03_nhan_customer_cancel_giu_nguyen_nhan_goc(self):
        """Tài liệu có nhãn chữ `customer Cancel`; không được vứt sự kiện vì không phải số."""
        code = "BEST-G3"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-G3", trang_thai_giao="dang_giao")
        kq = self._gui(self.tk_a, self._payload(code, "MD-G3", "customer Cancel",
                                                "2026-10-19T10:00:00+07:00"))
        self.assertTrue(kq.thanh_cong)
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        sk = self._sk(kq.su_kien_id)
        tho = json.loads(bytes(sk["payload_tho"]))
        self.assertEqual(tho["status"], "customer Cancel")
        # Cột dấu vết là TUỲ CHỌN (chỉ có sau migrate); payload_tho mới là nguồn đầy đủ.
        if "hang_ma_goc" in sk.keys():
            self.assertEqual(sk["hang_ma_goc"], "customer Cancel")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao",
                         "hủy là quyết định nghiệp vụ — webhook chỉ ghi nhận, không hạ trạng thái")

    def test_g02_ma_lan_can_soat_nhung_van_luu_du(self):
        code = "BEST-G2"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-G2")
        kq = self._gui(self.tk_a, self._payload(code, "MD-G2", 88888,
                                                "2026-10-19T10:00:00+07:00"))
        self.assertTrue(kq.thanh_cong)
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertEqual(self._sk(kq.su_kien_id)["trang_thai"], "xong")

    def test_g04_nhan_customer_cancel_giu_dau_vet_trong_audit(self):
        """Nhãn chữ `customer Cancel` → mã 2 nhưng KHÔNG được đánh rơi dấu vết nhãn gốc.

        Ca g03 canh payload thô; ca này canh tầng QUYẾT ĐỊNH + audit: cờ `customer_cancel`
        phải sống sót qua bước chuẩn hoá, nếu không audit không phân biệt được hủy-bằng-nhãn
        với hủy-bằng-số 2 và mất đúng phần "có nhãn chữ" của đặc tả.
        """
        code = "BEST-G4"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-G4", "dang_giao")
        kq = self._gui(self.tk_a, self._payload(code, "MD-G4", "CUSTOMER CANCEL",
                                                1792378800000))
        self.assertEqual(kq.http, 200)
        self.assertTrue(kq.thanh_cong)
        self.assertEqual(kq.ket_cuc, "ghi_nhan")
        self.assertEqual(kq.chi_tiet["chung"], "da_huy")
        self.assertTrue(kq.chi_tiet["customer_cancel"],
                        "cờ nhãn chữ bị mất sau bước chuẩn hoá")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

        audit = self._audit("webhook_best_bo_qua", kq.su_kien_id)
        self.assertTrue(audit)
        chi_tiet = json.loads(audit[0]["chi_tiet"])
        self.assertEqual(chi_tiet["status"], 2)
        self.assertEqual(chi_tiet["status_raw"], "CUSTOMER CANCEL",
                         "audit phải giữ NHÃN GỐC, không chỉ số đã chuẩn hoá")
        self.assertIs(chi_tiet["customer_cancel"], True)
        self.assertEqual(chi_tiet["trang_thai_chung"], "da_huy")
        # Nhãn gốc còn trong payload thô + cột dấu vết (nếu đã migrate).
        sk = self._sk(kq.su_kien_id)
        self.assertEqual(json.loads(bytes(sk["payload_tho"]))["status"], "CUSTOMER CANCEL")
        if "hang_ma_goc" in sk.keys():
            self.assertEqual(sk["hang_ma_goc"], "CUSTOMER CANCEL")

    def test_g05_nhan_customer_cancel_va_so_2_la_hai_su_kien_khac_nguon(self):
        """`customer Cancel` và số `2` cùng nghĩa nhưng KHÁC khoá sự kiện (giữ nhãn gốc).

        Gộp chúng sẽ làm mất dấu vết nguồn gửi; tách chúng là chủ ý của `_khoa_su_kien`.
        Cả hai đều chỉ GHI NHẬN, không đổi trạng thái đơn.
        """
        code = "BEST-G5"
        don_id = self._tao_don(self.ta, self.tk_a, code, "MD-G5", "dang_giao")
        moc = 1792378800000
        kq_nhan = self._gui(self.tk_a, self._payload(code, "MD-G5", "customer Cancel", moc))
        kq_so = self._gui(self.tk_a, self._payload(code, "MD-G5", 2, moc))
        self.assertTrue(kq_nhan.thanh_cong)
        self.assertTrue(kq_so.thanh_cong)
        self.assertEqual(kq_nhan.ket_cuc, "ghi_nhan")
        self.assertEqual(kq_so.ket_cuc, "ghi_nhan")
        self.assertNotEqual(kq_nhan.event_id, kq_so.event_id)
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_a, code), 2)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")

        chi_nhan = json.loads(self._audit("webhook_best_bo_qua", kq_nhan.su_kien_id)[0]["chi_tiet"])
        chi_so = json.loads(self._audit("webhook_best_bo_qua", kq_so.su_kien_id)[0]["chi_tiet"])
        self.assertEqual(chi_nhan["status_raw"], "customer Cancel")
        self.assertIs(chi_nhan["customer_cancel"], True)
        self.assertEqual(chi_so["status_raw"], "2")
        self.assertIs(chi_so["customer_cancel"], False)

    def test_g06_surrogate_don_le_bi_tu_choi_422_khong_lam_sap(self):
        """JSON hợp lệ vẫn có thể chứa surrogate đơn lẻ (`"\\ud800"`). Trường nghiệp vụ phải bị
        từ chối 422 TRƯỚC khi băm khoá/ghi CSDL; trường LẠ không được làm sập bước lưu thô.

        Trước khi vá: `_kiem_ma` cho surrogate đi qua rồi `_khoa_su_kien().encode("utf-8")`
        ném `UnicodeEncodeError` ngoài mọi try ⇒ 500 mù, không lưu thô, không audit.
        """
        truoc = self._so_su_kien(self.tk_a)
        ca = (
            ("code_best", lambda p: p.__setitem__("code_best", "BEST\ud800X")),
            ("merchant_order_code",
             lambda p: p.__setitem__("merchant_order_code", "MD\ud800X")),
            # Parser bỏ dấu chỉ giữ chữ cái, nên nhãn này lọt qua như "customer Cancel".
            ("status", lambda p: p.__setitem__("status", "customer \ud800 cancel")),
            ("status_content", lambda p: p.__setitem__("status_content", "x\ud800y")),
        )
        for ten, sua in ca:
            with self.subTest(truong=ten):
                p = self._payload(f"BEST-G6-{ten}", f"MD-G6-{ten}", 211, 1792378800000)
                sua(p)
                # ensure_ascii=True (mặc định) ⇒ surrogate thành escape JSON hợp lệ.
                body = json.dumps(p).encode()
                kq = self._gui_body(self.tk_a, body)
                self.assertEqual(kq.http, 422, f"{ten}: {kq!r}")
                self.assertEqual(kq.body["Result"], 0, ten)
                self.assertNotEqual(kq.body["Message"], "", ten)
        self.assertEqual(self._so_su_kien(self.tk_a), truoc,
                         "payload surrogate vẫn bị ghi thô")

        # Trường LẠ: bỏ qua khi quyết định, nhưng phải LƯU được bằng JSON escape. Kèm
        # `tenant_id` surrogate để canh cả đường audit "claim tenant bị bỏ qua".
        p = self._payload("BEST-G6-EXTRA", "MD-G6-EXTRA", 211, 1792378800000,
                          ghi_chu="x\ud800y", tenant_id="\ud800")
        kq = self._gui_body(self.tk_a, json.dumps(p).encode())
        self.assertEqual(kq.http, 200)
        self.assertTrue(kq.thanh_cong)
        tho = json.loads(bytes(self._sk(kq.su_kien_id)["payload_tho"]))
        self.assertEqual(tho["ghi_chu"], "x\ud800y",
                         "trường lạ có surrogate bị mất khi lưu thô")


# ============================================================================
# H. XÁC THỰC BEARER (sandbox/production) — KHÁC HẲN HMAC CỦA MOCK
# ============================================================================
class TestH_XacThucBearer(Nen):
    """BEST thật dùng JWT Bearer; mock dùng HMAC của hub. Bộ thử canh CẢ HAI chiều không lẫn.

    `xac_thuc_best` là LỚP B (kho Bearer mã hoá) do AG-00 sở hữu; ở đây chỉ gọi hàm CÔNG KHAI
    `luu_bearer_webhook`, không sửa tệp đó. Mỗi ca tự tạo tài khoản sandbox riêng để không phụ
    thuộc thứ tự chạy của các lớp khác (đặc biệt `test_f06` cần `tk_sb` KHÔNG có Bearer).
    """

    def _tai_khoan_sandbox(self, wh_ma, tenant_id=None):
        return _account(tenant_id if tenant_id is not None else self.ta,
                        "best", wh_ma, "secret-" + wh_ma, moi_truong="sandbox")

    def _luu_bearer(self, tk_id, tenant_id, bearer, wh_ma):
        xac_thuc_best.luu_bearer_webhook(str(tenant_id), str(tk_id), bearer,
                                         webhook_ma=wh_ma)

    def _goi_bearer(self, tk_id, payload, bearer):
        body = json.dumps(payload, ensure_ascii=False).encode()
        return wb.xu_ly_voi_account(self._tk(tk_id), body,
                                    {"authorization": "Bearer " + bearer})

    def test_h01_bearer_dung_duoc_nhan_cap_nhat_va_ack_dung_dac_ta(self):
        """Token ĐÚNG của ĐÚNG account/môi trường: qua 11 bước, ACK đặc tả, đơn đổi."""
        wh = "best-wh-h1"
        tk_id = self._tai_khoan_sandbox(wh)
        bearer = "v9." + "h1" * 24
        self._luu_bearer(tk_id, self.ta, bearer, wh)
        don_id = self._tao_don(self.ta, tk_id, "BEST-H1", "MD-H1")
        kq = self._goi_bearer(tk_id, self._payload("BEST-H1", "MD-H1", 211, 1792378800000),
                              bearer)
        self.assertEqual(kq.http, 200)
        self.assertEqual(kq.body, {"Result": 1, "Message": ""})
        self.assertEqual(kq.buoc, wb.TEN_BUOC)
        self.assertEqual(kq.ket_cuc, "cap_nhat")
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "cho_lay")
        self.assertEqual(self._sk(kq.su_kien_id)["trang_thai"], "xong")

        audit = self._audit("webhook_best_cap_nhat_don", kq.su_kien_id)
        self.assertTrue(audit)
        chi_tiet = json.loads(audit[0]["chi_tiet"])
        self.assertEqual(chi_tiet["so_do_xac_thuc"], "best_bearer")
        self.assertEqual(chi_tiet["muc_xac_thuc"], wb.MUC_DA_TAI_LIEU)

        # Bearer KHÔNG được rơi vào kho thô/headers/audit/response.
        sk = self._sk(kq.su_kien_id)
        self.assertNotIn(bearer, str(sk["headers_json"]))
        self.assertNotIn(bearer, bytes(sk["payload_tho"]).decode("utf-8"))
        self.assertNotIn(bearer, json.dumps(kq.body, ensure_ascii=False))
        for r in csdl.nhieu("SELECT chi_tiet, dia_chi FROM audit"):
            self.assertNotIn(bearer, f"{r['chi_tiet']} {r['dia_chi']}")

    def test_h02_bearer_sai_bi_tu_choi_khong_luu_khong_doi_don(self):
        wh = "best-wh-h2"
        tk_id = self._tai_khoan_sandbox(wh)
        bearer = "v9." + "h2" * 24
        self._luu_bearer(tk_id, self.ta, bearer, wh)
        don_id = self._tao_don(self.ta, tk_id, "BEST-H2", "MD-H2")
        kq = self._goi_bearer(tk_id, self._payload("BEST-H2", "MD-H2", 211, 1792378800000),
                              "x" * 48)
        self.assertEqual(kq.http, 401)
        self.assertEqual(kq.body["Result"], 0)
        self.assertIn("BEARER_KHONG_KHOP", kq.body["Message"])
        self.assertEqual(self._dem_su_kien_theo_ma(tk_id, "BEST-H2"), 0)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])
        self.assertTrue(self._audit("webhook_best_tu_choi", tk_id))

    def test_h03_thieu_hoac_sai_dinh_dang_bearer_deu_401(self):
        wh = "best-wh-h3"
        tk_id = self._tai_khoan_sandbox(wh)
        bearer = "v9." + "h3" * 24
        self._luu_bearer(tk_id, self.ta, bearer, wh)
        don_id = self._tao_don(self.ta, tk_id, "BEST-H3", "MD-H3")
        body = json.dumps(self._payload("BEST-H3", "MD-H3", 211, 1792378800000)).encode()
        tk = self._tk(tk_id)
        for ten, headers, ma in (
            ("thiếu header", {}, "THIEU_HEADER"),
            ("thiếu token", {"authorization": "Bearer"}, "SAI_DINH_DANG_BEARER"),
            ("sai tiền tố", {"authorization": "Token " + bearer}, "SAI_DINH_DANG_BEARER"),
        ):
            with self.subTest(ten=ten):
                kq = wb.xu_ly_voi_account(tk, body, headers)
                self.assertEqual(kq.http, 401, ten)
                self.assertIn(ma, kq.body["Message"], ten)
        self.assertEqual(self._dem_su_kien_theo_ma(tk_id, "BEST-H3"), 0)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])

    def test_h04_sandbox_khong_chap_nhan_hmac_mock_du_chu_ky_dung(self):
        """Môi trường THẬT chỉ Bearer: HMAC đúng của mock cũng bị từ chối (không có đường lùi)."""
        wh = "best-wh-h4"
        tk_id = self._tai_khoan_sandbox(wh)
        don_id = self._tao_don(self.ta, tk_id, "BEST-H4", "MD-H4")
        body = json.dumps(self._payload("BEST-H4", "MD-H4", 211, 1792378800000)).encode()
        chu_ky = hmac.new(("secret-" + wh).encode(), body, hashlib.sha256).hexdigest()
        kq = wb.xu_ly_voi_account(self._tk(tk_id), body,
                                  {"x-webhook-signature": chu_ky})
        self.assertEqual(kq.http, 401)
        self.assertIn("THIEU_HEADER", kq.body["Message"],
                      "HMAC mock đã lọt vào đường Bearer")
        self.assertEqual(self._dem_su_kien_theo_ma(tk_id, "BEST-H4"), 0)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])

    def test_h05_mock_khong_chap_nhan_bearer_du_token_dung(self):
        """Môi trường mock vẫn là HMAC của hub: Bearer (dù đúng kho) không phải vé vào."""
        bearer = "v9." + "h5" * 24
        self._luu_bearer(self.tk_a, self.ta, bearer, WH_A)
        don_id = self._tao_don(self.ta, self.tk_a, "BEST-H5", "MD-H5")
        body = json.dumps(self._payload("BEST-H5", "MD-H5", 211, 1792378800000)).encode()
        kq = wb.xu_ly_voi_account(self._tk(self.tk_a), body,
                                  {"authorization": "Bearer " + bearer})
        self.assertEqual(kq.http, 401)
        self.assertIn("x-webhook-signature", kq.body["Message"])
        self.assertEqual(self._dem_su_kien_theo_ma(self.tk_a, "BEST-H5"), 0)
        self.assertIsNone(self._don(don_id)["trang_thai_giao"])

    def test_h06_bearer_gan_chet_voi_account_va_webhook_ma(self):
        """Token của account A KHÔNG dùng được cho account B; token lưu sai `webhook_ma` cũng bị chặn."""
        wh_a, wh_b = "best-wh-h6-a", "best-wh-h6-b"
        tk_a = self._tai_khoan_sandbox(wh_a)
        tk_b = self._tai_khoan_sandbox(wh_b)
        bearer_a, bearer_b = "v9." + "6a" * 24, "v9." + "6b" * 24
        self._luu_bearer(tk_a, self.ta, bearer_a, wh_a)
        self._luu_bearer(tk_b, self.ta, bearer_b, wh_b)
        don_b = self._tao_don(self.ta, tk_b, "BEST-H6", "MD-H6")
        p = self._payload("BEST-H6", "MD-H6", 211, 1792378800000)

        kq = self._goi_bearer(tk_b, p, bearer_a)
        self.assertEqual(kq.http, 401, "token account A lọt vào account B")
        self.assertIn("BEARER_KHONG_KHOP", kq.body["Message"])
        self.assertEqual(self._dem_su_kien_theo_ma(tk_b, "BEST-H6"), 0)
        self.assertIsNone(self._don(don_b)["trang_thai_giao"])

        # Token ĐÚNG nhưng lưu kèm `webhook_ma` khác ⇒ từ chối, không đoán.
        self._luu_bearer(tk_a, self.ta, bearer_a, "best-wh-h6-khac")
        kq2 = self._goi_bearer(tk_a, p, bearer_a)
        self.assertEqual(kq2.http, 401)
        self.assertIn("DU_LIEU_KHONG_KHOP", kq2.body["Message"])

    def test_h07_bearer_khong_qua_duoc_tenant_khac(self):
        wh_a, wh_b = "best-wh-h7-a", "best-wh-h7-b"
        tk_a = self._tai_khoan_sandbox(wh_a, tenant_id=self.ta)
        tk_b = self._tai_khoan_sandbox(wh_b, tenant_id=self.tb)
        bearer_a, bearer_b = "v9." + "7a" * 24, "v9." + "7b" * 24
        self._luu_bearer(tk_a, self.ta, bearer_a, wh_a)
        self._luu_bearer(tk_b, self.tb, bearer_b, wh_b)
        don_b = self._tao_don(self.tb, tk_b, "BEST-H7", "MD-H7")
        kq = self._goi_bearer(tk_b, self._payload("BEST-H7", "MD-H7", 211, 1792378800000),
                              bearer_a)
        self.assertEqual(kq.http, 401)
        self.assertEqual(self._dem_su_kien_theo_ma(tk_b, "BEST-H7"), 0)
        self.assertIsNone(self._don(don_b)["trang_thai_giao"],
                          "Bearer tenant A đã cập nhật đơn tenant B")

    def test_h08_gui_lai_cung_su_kien_bang_bearer_van_idempotent(self):
        wh = "best-wh-h8"
        tk_id = self._tai_khoan_sandbox(wh)
        bearer = "v9." + "h8" * 24
        self._luu_bearer(tk_id, self.ta, bearer, wh)
        don_id = self._tao_don(self.ta, tk_id, "BEST-H8", "MD-H8")
        p = self._payload("BEST-H8", "MD-H8", 301, 1792378800000)
        kq1 = self._goi_bearer(tk_id, p, bearer)
        kq2 = self._goi_bearer(tk_id, p, bearer)
        self.assertTrue(kq1.thanh_cong)
        self.assertTrue(kq2.thanh_cong)
        self.assertFalse(kq1.trung)
        self.assertTrue(kq2.trung)
        self.assertEqual(kq1.su_kien_id, kq2.su_kien_id)
        self.assertEqual(self._dem_su_kien_theo_ma(tk_id, "BEST-H8"), 1)
        self.assertEqual(len(self._ls(don_id)), 1)
        self.assertEqual(self._don(don_id)["trang_thai_giao"], "dang_giao")


# ============================================================================
# I. CSDL ĐÃ MIGRATE — CỘT DẤU VẾT CỦA HUB ĐƯỢC GHI THẬT
# ============================================================================
class TestI_CSDLDaMigrate(Nen):
    """Lớp CUỐI: chạy lại đường ĐÃ MIGRATE của `wh_su_kien` (bộ chính canh đường chưa migrate).

    `migrate.py` mới thêm các cột dấu vết; nếu mô-đun chỉ "chạy được" mà không ghi đúng cột thì
    dashboard/soát DLQ sẽ trống. Lớp này thêm ĐÚNG bộ cột đó (không đụng tệp ngoài phạm vi),
    xoá cache dò cột của hub, rồi canh: mã gốc, cờ cần soát, trạng thái chuẩn, `don_id`, và
    `hang_moc_thoi_gian` CHỈ có khi sự kiện thực sự được áp.
    """

    COT_MIGRATE = (("hang_ma_goc", "TEXT"), ("hang_mo_ta_goc", "TEXT"),
                   ("hang_su_kien_goc", "TEXT"), ("anh_xa_do_tin_cay", "TEXT"),
                   ("anh_xa_nguon", "TEXT"), ("can_soat", "INTEGER NOT NULL DEFAULT 0"),
                   ("hang_moc_thoi_gian", "TEXT"),
                   ("don_id", "INTEGER REFERENCES don_hang(id)"),
                   ("trang_thai_chuan", "TEXT"))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        da_co = {r[1] for r in csdl.nhieu("PRAGMA table_info(wh_su_kien)")}
        for ten, kieu in cls.COT_MIGRATE:
            if ten not in da_co:
                csdl.ghi(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
        hub.xoa_cache_cot()

    def test_i01_cot_dau_vet_va_moc_chi_ghi_khi_su_kien_duoc_ap(self):
        # (1) Sự kiện ĐƯỢC ÁP: đủ dấu vết + mốc hãng.
        don_ap = self._tao_don(self.ta, self.tk_a, "BEST-I1-AP", "MD-I1-AP")
        moc_ap = 1792378800000
        kq_ap = self._gui(self.tk_a, self._payload("BEST-I1-AP", "MD-I1-AP", 301, moc_ap))
        self.assertEqual(kq_ap.ket_cuc, "cap_nhat")
        sk_ap = self._sk(kq_ap.su_kien_id)
        self.assertEqual(sk_ap["hang_ma_goc"], "301")
        self.assertEqual(sk_ap["trang_thai_chuan"], "dang_giao")
        self.assertEqual(sk_ap["can_soat"], 0)
        self.assertEqual(sk_ap["don_id"], don_ap)
        self.assertEqual(sk_ap["hang_moc_thoi_gian"], hub._moc_chuan(moc_ap))
        self.assertIn("301", sk_ap["hang_su_kien_goc"])

        # (2) customer Cancel: biết mã nhưng KHÔNG áp ⇒ can_soat=1, không trạng thái chuẩn,
        # KHÔNG được đẩy mốc hãng (nếu đẩy, một sự kiện có thật đến sau bị chặn oan).
        don_nhan = self._tao_don(self.ta, self.tk_a, "BEST-I1-NHAN", "MD-I1-NHAN", "dang_giao")
        kq_nhan = self._gui(self.tk_a, self._payload("BEST-I1-NHAN", "MD-I1-NHAN",
                                                     "customer Cancel", moc_ap + 60_000))
        self.assertEqual(kq_nhan.ket_cuc, "ghi_nhan")
        sk_nhan = self._sk(kq_nhan.su_kien_id)
        self.assertEqual(sk_nhan["hang_ma_goc"], "customer Cancel")
        self.assertEqual(sk_nhan["hang_mo_ta_goc"], "Trạng thái thử MOCK — không phải dữ liệu BEST thật")
        self.assertIsNone(sk_nhan["trang_thai_chuan"])
        self.assertEqual(sk_nhan["can_soat"], 1)
        self.assertIsNone(sk_nhan["hang_moc_thoi_gian"],
                          "sự kiện KHÔNG áp đã đẩy mốc hãng — lỗi G14 tái phát")
        self.assertEqual(sk_nhan["don_id"], don_nhan)
        self.assertIn("customer Cancel", sk_nhan["hang_su_kien_goc"])
        self.assertEqual(self._don(don_nhan)["trang_thai_giao"], "dang_giao")

    def test_i02_ma_can_soat_duoc_ap_van_giu_co_can_soat(self):
        """203/707/777/1000 ĐƯỢC ÁP nhưng tài liệu đánh dấu CẦN SOÁT (lấy/trả thất bại, thất lạc,
        hư hỏng). Cột `can_soat` không được suy từ "có áp hay không" — nếu suy, đúng những sự
        kiện cần người soát nhất lại rơi khỏi hàng đợi soát.
        """
        for ma in (203, 707, 777, 1000):
            with self.subTest(ma=ma):
                code = f"BEST-I2-{ma}"
                don_id = self._tao_don(self.ta, self.tk_a, code, f"MD-I2-{ma}")
                kq = self._gui(self.tk_a, self._payload(code, f"MD-I2-{ma}", ma,
                                                        1792378800000 + ma))
                self.assertEqual(kq.ket_cuc, "cap_nhat", f"mã {ma}: {kq!r}")
                sk = self._sk(kq.su_kien_id)
                self.assertEqual(sk["can_soat"], 1,
                                 f"mã {ma} được áp nhưng MẤT cờ cần soát")
                self.assertEqual(sk["trang_thai_chuan"], ANH_XA_DOC_LAP[ma][0])
                self.assertEqual(self._don(don_id)["trang_thai_giao"],
                                 ANH_XA_DOC_LAP[ma][0])

        # Đối chứng: mã thường được áp ⇒ can_soat=0.
        don_ok = self._tao_don(self.ta, self.tk_a, "BEST-I2-OK", "MD-I2-OK")
        kq_ok = self._gui(self.tk_a, self._payload("BEST-I2-OK", "MD-I2-OK", 301,
                                                   1792380000000))
        self.assertEqual(kq_ok.ket_cuc, "cap_nhat")
        self.assertEqual(self._sk(kq_ok.su_kien_id)["can_soat"], 0)
        self.assertEqual(self._don(don_ok)["trang_thai_giao"], "dang_giao")


# ============================================================================
# IN BẰNG CHỨNG — bảng lấy từ dữ liệu thật của lần chạy, không chép tay
# ============================================================================
def _in_bang_chung(ket_qua):
    print("\n" + "=" * 78)
    print("BẰNG CHỨNG MOCK — BEST WEBHOOK (KHÔNG gọi API BEST, KHÔNG credentials thật)")
    print("=" * 78)
    print(f"Mã thoát dự kiến: {0 if ket_qua.wasSuccessful() else 1}")
    print(f"Ca chạy: {ket_qua.testsRun} · lỗi: {len(ket_qua.errors)} · "
          f"hỏng: {len(ket_qua.failures)} · skip: {len(ket_qua.skipped)}")
    print(f"KẾT QUẢ: {'MOCK PASS' if ket_qua.wasSuccessful() else 'MOCK FAIL'}")
    print("\nBẢNG 23 MÃ LIỆT KÊ + 1 DÒNG ĐỐI CHỨNG MÃ LẠ (tổng 24 dòng):")
    print(f"  {'mã':>5} · {'trạng thái chung':<18} · {'mở lại':<6} · mức")
    for ma, mo_ta, chung, mo_lai, muc in wb.bang_ma_van_ban():
        print(f"  {ma:>5} · {str(chung):<18} · {'CÓ' if mo_lai else '-':<6} · {muc}")
    # Dòng 24 KHÔNG phải mã hãng: nó là đối chứng "mã lạ" của bộ thử, in ra để bảng đủ 24 dòng
    # mà không ai đọc nhầm thành mã BEST thứ 24.
    print(f"  {'99999':>5} · {'None':<18} · {'-':<6} · {wb.MUC_CHUA_KIEM_CHUNG}"
          "  ← MÃ LẠ ĐỐI CHỨNG, không phải mã hãng")
    print(f"  GHI CHÚ: {wb.GHI_CHU_SO_LUONG}")
    print("\nBẢNG 605→606 (từ ca thử thật):")
    for r in _BANG_CHUNG:
        if r["loai"] != "605_606":
            continue
        print(f"  {r['buoc']}: {r['truoc']} → {r['sau']} · hạng sau={r.get('hang_sau')} · "
              f"số dòng lịch sử={r.get('lich_su')} · {r['ket_cuc']}")
    print("\nBẢNG 'CŨ ĐẾN MUỘN' (từ ca thử thật):")
    for r in _BANG_CHUNG:
        if r["loai"] != "cu_den_muon":
            continue
        print(f"  mã {r['ma']} · {r['moc_cu']} · mốc đã áp={r['moc_da_ap']} · "
              f"trạng thái sau={r['trang_thai_sau']} · {r['ket_cuc']}")
    print("\nBẢNG 23 LƯỢT MÃ ĐÃ CHẠY QUA WEBHOOK:")
    for r in _BANG_CHUNG:
        if r["loai"] != "ma":
            continue
        print(f"  mã {str(r['ma']):>5} → {str(r['chung']):<18} · {r['ket_cuc']}")
    print("=" * 78)


if __name__ == "__main__":
    bo = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    kq = unittest.TextTestRunner(verbosity=2).run(bo)
    _in_bang_chung(kq)
    sys.exit(0 if kq.wasSuccessful() else 1)
