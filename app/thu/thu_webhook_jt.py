# Bộ thử G14 — TÍCH HỢP WEBHOOK J&T (AG-03). File RIÊNG của AG-03 cho đợt G14; không giẫm chân
# `thu_webhook.py` (G06, vẫn giữ nguyên và phải tiếp tục xanh).
#
# Vì sao có file thứ hai thay vì thêm vào file cũ: `thu_webhook.py` chạy trên CSDL CHƯA migrate
# (thiếu các cột mở rộng của G06). Lỗi nặng nhất tìm được ở G14 — mã nhập nhằng đầu độc watermark
# — CHỈ hiện ra trên CSDL ĐÃ MIGRATE, tức là CSDL THẬT. Bộ thử cũ chạy trên schema khác nên nó
# xanh suốt trong khi CSDL thật sai. File này dựng ĐÚNG schema thật (v8) rồi mới thử.
#
# Nhóm:
#   A. Hợp đồng callback J&T — trường nào có tài liệu, trường nào BLOCKED (W02)
#   B. Chữ ký + chống phát lại + không cho người gửi chọn sơ đồ (W02/W05)
#   C. Chống trùng — CƯỠNG CHẾ BẰNG CSDL, không bằng `if` (W05)
#   D. Giải tenant + chéo tenant + tenant khai trong payload (W03)
#   E. Sai thứ tự: thứ hạng + watermark CHỈ tính sự kiện đã áp (W05)
#   F. Mã 110 nhập nhằng và mã lạ — chặn cứng, không DELIVERED, không đụng COD (W04)
#   G. Retry / DLQ / replay có phép + có trần (W05)
#   H. Đối chiếu hành trình, gồm phép kiểm chéo tenant (W05)
#   I. Máy chủ HTTP THẬT, bind 127.0.0.1, cổng do hệ điều hành cấp (W06)
#   J. Chốt chặn cấu trúc của G14
#
# Chạy: VIP_HUB_DATA=/tmp/veh_data_ag03 python3 app/thu/thu_webhook_jt.py
import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)
# Mỗi lượt chạy một CSDL MỚI. Tôn trọng `VIP_HUB_DATA` nếu có (để không giẫm cổng/thư mục của
# agent khác) nhưng LUÔN tạo thư mục con mới: chạy lại trên CSDL cũ thì các phép đếm "trước/sau"
# sai, và đó là loại hỏng im lặng đắt nhất của bộ thử.
_GOC_DU_LIEU = os.environ.get("VIP_HUB_DATA") or tempfile.gettempdir()
os.makedirs(_GOC_DU_LIEU, exist_ok=True)
os.environ["VIP_HUB_DATA"] = tempfile.mkdtemp(prefix="g14-", dir=_GOC_DU_LIEU)
# Backoff nhỏ để ca retry chạy trong vài phần trăm giây thay vì vài giây.
os.environ.setdefault("VIP_HUB_BACKOFF", "0.01")

import adapter          # noqa: E402
import adapter_jt       # noqa: E402,F401  (đăng ký adapter)
import adapter_vtp      # noqa: E402,F401
import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import quyen            # noqa: E402
import tai_chinh        # noqa: E402
import trang_thai_hang as tth   # noqa: E402
import webhook as wh    # noqa: E402

try:                                  # `server.py` của AG-00 — có thể đang được sửa song song
    import server
    LOI_IMPORT_SERVER = None
except Exception as _e:               # noqa: BLE001
    server = None
    LOI_IMPORT_SERVER = f"{type(_e).__name__}: {_e}"

SECRET_A = "secret-webhook-A-g14-111111"
SECRET_B = "secret-webhook-B-g14-222222"
SECRET_SB = "secret-callback-sandbox-g14-3333"
SECRET_TAT = "secret-tai-khoan-da-tat-g14-44"

# Cột mở rộng của G06 — CSDL THẬT (schema v8) có đủ. Bộ thử này dựng đúng trạng thái đó.
COT_THEM = (("hang_ma_goc", "TEXT"), ("hang_mo_ta_goc", "TEXT"), ("hang_su_kien_goc", "TEXT"),
            ("anh_xa_do_tin_cay", "TEXT"), ("anh_xa_nguon", "TEXT"),
            ("can_soat", "INTEGER NOT NULL DEFAULT 0"), ("hang_moc_thoi_gian", "TEXT"),
            ("don_id", "INTEGER"), ("trang_thai_chuan", "TEXT"))


# ---------------------------------------------------------------- hạ tầng fixture
def _user():
    n = csdl.mot("SELECT COUNT(*) c FROM users")["c"]
    return csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                    " VALUES (?,?,'U',?)",
                    (f"g14u{n}", bao_mat.bam_mat_khau("x" * 12), csdl.bay_gio())).lastrowid


def _tenant(ten, code):
    return csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,'pro',?)",
                    (code, ten, csdl.bay_gio())).lastrowid


def _account(tenant_id, hang, wh_ma, secret, moi_truong="mock", cred=None, kich_hoat=1):
    ban_ma, duoi = bao_mat.luu_credentials(cred or {"apiAccount": "API-A"},
                                           bao_mat.aad_credentials(tenant_id, hang))
    return csdl.ghi(
        "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
        "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,kich_hoat,tao_luc)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tenant_id, hang, f"{hang}-{wh_ma}", moi_truong, ban_ma, duoi, wh_ma,
         bao_mat.ma_hoa_wh(secret, wh_ma), kich_hoat, csdl.bay_gio())).lastrowid


def _don(tenant_id, user_id, account_id, ma_van_don, trang_thai_giao="cho_lay", hang_tt=1,
         cod=0):
    return csdl.ghi(
        "INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,nguoi_gui_dia_chi,"
        "nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,cod,"
        "carrier_account_id,ma_van_don,trang_thai,trang_thai_giao,hang_trang_thai_giao,"
        "nguoi_tao,tao_luc,cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'da_gui',?,?,?,?,?)",
        (tenant_id, f"MD-{ma_van_don}", "A", "0901111111", "x", "B", "0902222222", "y", "z", 500,
         cod, account_id, ma_van_don, trang_thai_giao, hang_tt, user_id,
         csdl.bay_gio(), csdl.bay_gio())).lastrowid


def biz_jt(bill, ma, scan_time, desc="mô tả gốc của hãng", **thua):
    ct = {"scanTime": scan_time, "scanTypeCode": ma, "desc": desc}
    ct.update(thua)
    return json.dumps({"billCode": bill, "details": [ct]}, ensure_ascii=False)


def body_jt(bill, ma, scan_time, desc="mô tả gốc của hãng", **thua):
    """Thân form ĐÚNG dạng tài liệu J&T: application/x-www-form-urlencoded + `bizContent`."""
    return urllib.parse.urlencode({"bizContent": biz_jt(bill, ma, scan_time, desc, **thua)}).encode()


def body_hub(event, mvd, event_id=None, **thua):
    d = {"event": event, "tracking_number": mvd}
    if event_id:
        d["event_id"] = event_id
    d.update(thua)
    return json.dumps(d, ensure_ascii=False).encode()


def ky_hub(secret, body):
    return {"x-webhook-signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()}


def ky_jt(secret, biz, api_account="API-A", ts=None):
    return {"digest": base64.b64encode(hashlib.md5((biz + secret).encode()).digest()).decode(),
            "apiaccount": api_account,
            "timestamp": str(ts if ts is not None else wh._bay_gio_ms())}


_NEN = {}


def _dung_nen():
    """Nền dùng chung. Dựng CSDL ở ĐÚNG schema thật (có cột mở rộng của G06)."""
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
    co = {r[1] for r in csdl.nhieu("PRAGMA table_info(wh_su_kien)")}
    for ten, kieu in COT_THEM:
        if ten not in co:
            csdl.ghi(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
    wh.xoa_cache_cot()
    uid = _user()
    ta = _tenant("Tenant A", "g14ta")
    tb = _tenant("Tenant B", "g14tb")
    _NEN.update(
        uid=uid, ta=ta, tb=tb,
        tk_a=_account(ta, "jt", "wh-g14-a", SECRET_A, cred={"apiAccount": "API-A"}),
        tk_b=_account(tb, "jt", "wh-g14-b", SECRET_B, cred={"apiAccount": "API-B"}),
        # Tài khoản SANDBOX: sơ đồ chữ ký riêng của hãng (jt_digest), KHÔNG ra mạng.
        tk_sb=_account(ta, "jt", "wh-g14-sb", SECRET_SB, moi_truong="sandbox",
                       cred={"apiAccount": "API-1", "privateKey": "pk"}),
        # Viettel Post: KHÔNG KÝ webhook, chưa có sơ đồ ⇒ BLOCKED ở mọi môi trường khác mock.
        tk_vtp_sb=_account(ta, "vtp", "wh-g14-vtpsb", SECRET_A, moi_truong="sandbox"),
        tk_tat=_account(ta, "jt", "wh-g14-tat", SECRET_TAT, kich_hoat=0),
    )
    return _NEN


class Nen(unittest.TestCase):
    """Nền dùng chung: hai tenant, tài khoản hãng, xử lý sự kiện ĐỒNG BỘ cho xác định."""

    @classmethod
    def setUpClass(cls):
        for k, v in _dung_nen().items():
            setattr(cls, k, v)

    def setUp(self):
        tth.bo_chot_nghia()

    # ---- tiện ích chung ----
    def row(self, account_id):
        return csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (account_id,))

    def gui(self, account_id, body, headers=None, secret=None):
        """ĐÚNG thứ tự tầng HTTP: tra account → kiểm chữ ký → lưu thô → xử lý đồng bộ."""
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

    def dem(self, bang, dieu_kien="1=1", ts=()):
        return csdl.mot(f"SELECT COUNT(*) c FROM {bang} WHERE {dieu_kien}", ts)["c"]

    def audit_co(self, hanh_dong, doi_tuong=None):
        sql = "SELECT COUNT(*) c FROM audit WHERE hanh_dong=?"
        ts = [hanh_dong]
        if doi_tuong:
            sql += " AND doi_tuong=?"
            ts.append(doi_tuong)
        return csdl.mot(sql, ts)["c"]

    def nen_moi(self, ten):
        """Tenant RIÊNG cho một ca đối chiếu — để phép đếm không dính dữ liệu của ca khác."""
        t = _tenant(ten, f"g14-{ten}-{self.dem('tenants')}")
        tk = _account(t, "jt", f"wh-g14-{ten}-{self.dem('carrier_accounts')}", SECRET_A,
                      cred={"apiAccount": "API-A"})
        return {"tenant_id": t, "tk": tk, "uid": self.uid}


# ============================================================================
class A_HopDongCallback(Nen):
    """W02 — hợp đồng callback: chỗ nào tài liệu nói, chỗ nào BLOCKED, và công thức ký."""

    def test_a01_moi_truong_bat_buoc_cua_W02_deu_co_mat(self):
        can = ("dinh_danh_url_phia_nhan", "phuong_thuc_http", "than_yeu_cau", "header_bat_buoc",
               "cong_thuc_chu_ky", "khoa_ky_chieu_callback", "chuoi_dem_di_ky", "vi_du_doi_chieu",
               "dinh_danh_su_kien", "moc_thoi_gian_scan", "header_timestamp",
               "chinh_sach_thu_lai", "phan_hoi_xac_nhan")
        for t in can:
            self.assertIn(t, wh.HOP_DONG_CALLBACK, f"thiếu trường hợp đồng: {t}")
            muc = wh.HOP_DONG_CALLBACK[t]
            self.assertIn(muc["muc"], (wh.DA_TAI_LIEU, wh.SUY_RA, wh.CHUA_TAI_LIEU))
            self.assertTrue(str(muc["ghi_chu"] or "").strip(), f"{t}: không ghi lý do")

    def test_a02_chua_co_tai_lieu_thi_phai_de_BLOCKED_khong_duoc_doan(self):
        # Đúng những chỗ mà trích lục trong repo KHÔNG trả lời được. Nếu ai đó đổi một dòng
        # thành DA_TAI_LIEU thì phải kèm căn cứ từ hãng — ca này bắt đúng lúc đó.
        phai_blocked = {"khoa_ky_chieu_callback", "chuoi_dem_di_ky", "chinh_sach_thu_lai",
                        "phuong_thuc_http", "header_timestamp", "phan_hoi_xac_nhan"}
        self.assertTrue(phai_blocked <= set(wh.CALLBACK_CHUA_TAI_LIEU),
                        f"thiếu: {phai_blocked - set(wh.CALLBACK_CHUA_TAI_LIEU)}")
        # Không có giá trị nào được khai cho những trường mà tài liệu KHÔNG trả lời. Riêng
        # `header_timestamp` giữ lại ĐÚNG câu tài liệu ('ms, UTC+7') vì chính câu đó là chỗ
        # mâu thuẫn — chép nguyên văn thì kiểm được, diễn giải lại thì không.
        for t in phai_blocked - {"header_timestamp"}:
            self.assertIsNone(wh.HOP_DONG_CALLBACK[t]["gia_tri"],
                              f"{t} khai giá trị trong khi tài liệu chưa trả lời")

    def test_a03_cong_thuc_chu_ky_dung_nguyen_van_tai_lieu(self):
        """`digest = base64( md5-BYTES(bizContent + privateKey) )` — md5 ra BYTE rồi mới base64."""
        tk = self.row(self.tk_sb)
        biz = biz_jt("MVD-A03", 113, "2026-10-15 10:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        dung = base64.b64encode(hashlib.md5((biz + SECRET_SB).encode("utf-8")).digest()).decode()
        ok, ly_do = wh.xac_thuc_jt_digest(tk, ky_jt(SECRET_SB, biz, "API-1"), body)
        self.assertTrue(ok, ly_do)
        # Biến thể SAI đã từng bị nhầm: hexdigest rồi mới base64.
        sai = base64.b64encode(
            hashlib.md5((biz + SECRET_SB).encode("utf-8")).hexdigest().encode()).decode()
        self.assertNotEqual(sai, dung)
        ok2, _ = wh.xac_thuc_jt_digest(tk, {"digest": sai, "apiaccount": "API-1",
                                            "timestamp": str(wh._bay_gio_ms())}, body)
        self.assertFalse(ok2, "nhận cả biến thể hexdigest-then-base64 (sai công thức tài liệu)")

    def test_a04_phan_hoi_xac_nhan_theo_dung_cho_tai_lieu_noi_toi(self):
        ma, than = wh.phan_hoi_xac_nhan(True)
        self.assertEqual(than["code"], 1, "trích lục câu 9: `code=1` là được nhận")
        self.assertEqual(ma, 200)
        _, trung_lap = wh.phan_hoi_xac_nhan(True, su_kien_id=7)
        self.assertEqual(trung_lap["code"], 1,
                         "callback trùng vẫn là THÀNH CÔNG (idempotent) — trả mã khác 1 là bị đẩy lại")
        _, tu_choi = wh.phan_hoi_xac_nhan(False, ly_do="chữ ký sai")
        self.assertNotEqual(tu_choi["code"], 1)

    def test_a05_khong_tu_nhan_muc_xac_thuc_cao_hon_thuc_te(self):
        bang = wh.bang_muc_xac_thuc()
        self.assertEqual(bang["jt"]["mock"]["muc"], wh.MUC_MOCK)
        self.assertEqual(bang["jt"]["sandbox_production"]["muc"], wh.MUC_DOCUMENTED,
                         "jt_digest mới ở mức DOCUMENTED (khoá ký chiều callback CHƯA có tài liệu)")
        self.assertEqual(bang["vtp"]["sandbox_production"]["muc"], wh.MUC_BLOCKED)
        for hang, muc in bang.items():
            for mt, v in muc.items():
                self.assertIn(v["muc"], wh.MUC_HOP_LE, f"{hang}/{mt} khai mức lạ {v['muc']!r}")
                self.assertNotIn(v["muc"], (wh.MUC_SANDBOX, wh.MUC_LIVE),
                                 f"{hang}/{mt} tự nhận đã kiểm với hãng thật — chưa hề có credentials")


# ============================================================================
class B_ChuKy(Nen):
    """W02/W05 — chữ ký, chống phát lại, và không cho người gửi chọn sơ đồ."""

    def test_b01_chu_ky_sai_thi_khong_nhan_va_co_audit(self):
        b = body_hub("lay_hang", "MVD-B01", "E-B01")
        truoc = self.dem("wh_su_kien")
        sk_id, _, ma = self.gui(self.tk_a, b, headers={"x-webhook-signature": "0" * 64})
        self.assertIsNone(sk_id)
        self.assertEqual(ma, 401)
        self.assertEqual(self.dem("wh_su_kien"), truoc, "sự kiện chữ ký sai vẫn được lưu thô")
        self.assertGreaterEqual(self.audit_co("webhook_chu_ky_tu_choi"), 1)

    def test_b02_thieu_header_bat_buoc(self):
        tk = self.row(self.tk_sb)
        biz = biz_jt("MVD-B02", 106, "2026-10-15 10:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        day_du = ky_jt(SECRET_SB, biz, "API-1")
        self.assertTrue(wh.xac_thuc_jt_digest(tk, day_du, body)[0])
        for thieu in ("digest", "timestamp"):
            hd = {k: v for k, v in day_du.items() if k != thieu}
            self.assertFalse(wh.xac_thuc_jt_digest(tk, hd, body)[0], f"thiếu {thieu} mà vẫn nhận")
        self.assertFalse(wh.xac_thuc_jt_digest(tk, day_du, b"khong-co-bizcontent")[0])

    def test_b03_apiAccount_la_thi_tu_choi(self):
        tk = self.row(self.tk_sb)
        biz = biz_jt("MVD-B03", 106, "2026-10-15 10:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        ok, ly_do = wh.xac_thuc_jt_digest(tk, ky_jt(SECRET_SB, biz, "API-KHAC"), body)
        self.assertFalse(ok)
        self.assertIn("apiAccount", ly_do)

    def test_b04_timestamp_lech_7_tieng_bi_tu_choi(self):
        """Câu 12/14 còn BLOCKED: (a) mốc Unix thật hay (b) giờ treo tường UTC+7 quy đổi.

        Mã đang hiểu theo (a). Ca này GHIM cách hiểu đó: nếu ai đổi sang (b) thì ở đây đỏ, và
        người đổi buộc phải trưng căn cứ từ hãng — đúng luật "cách hiểu chưa chốt thì phải là
        chốt chặn cứng, không được im lặng thành dữ kiện" (D-9 áp cho cả trường này).
        """
        tk = self.row(self.tk_sb)
        biz = biz_jt("MVD-B04", 106, "2026-10-15 10:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        lech = 7 * 3600 * 1000
        self.assertLess(wh.LECH_GIO_TOI_DA_MS, lech, "trần lệch giờ phải nhỏ hơn 7 tiếng")
        for dau in (-1, +1):
            ok, ly_do = wh.xac_thuc_jt_digest(
                tk, ky_jt(SECRET_SB, biz, "API-1", ts=wh._bay_gio_ms() + dau * lech), body)
            self.assertFalse(ok, f"timestamp lệch 7 tiếng (dấu {dau:+d}) mà vẫn nhận")
            self.assertIn("lệch", ly_do)

    def test_b05_nguoi_gui_khong_chon_duoc_so_do(self):
        """Tài khoản mock dùng sơ đồ của hub; gửi chữ ký J&T vào đó thì KHÔNG được nhận."""
        tk = self.row(self.tk_a)          # mock → hub_hmac
        self.assertEqual(wh.chon_so_do(tk)[0], "hub_hmac")
        biz = biz_jt("MVD-B05", 106, "2026-10-15 10:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        self.assertFalse(wh.chon_so_do(tk)[1](tk, ky_jt(SECRET_A, biz, "API-A"), body)[0],
                         "tài khoản mock lại nhận sơ đồ jt_digest")
        # Chiều ngược lại: tài khoản sandbox KHÔNG nhận sơ đồ của hub.
        tk_sb = self.row(self.tk_sb)
        self.assertEqual(wh.chon_so_do(tk_sb)[0], "jt_digest")
        self.assertFalse(wh.chon_so_do(tk_sb)[1](tk_sb, ky_hub(SECRET_SB, body), body)[0],
                         "tài khoản sandbox lại nhận sơ đồ hub_hmac")

    def test_b06_hang_chua_co_so_do_thi_BLOCKED(self):
        tk = self.row(self.tk_vtp_sb)
        ten, ham, muc = wh.chon_so_do(tk)
        self.assertIsNone(ham)
        self.assertEqual(muc, wh.MUC_BLOCKED)
        b = body_hub("lay_hang", "MVD-B06", "E-B06")
        self.assertFalse(wh.kiem_chu_ky(tk, ky_hub(SECRET_A, b), b))
        self.assertGreaterEqual(self.audit_co("webhook_chu_ky_tu_choi"), 1)


# ============================================================================
class C_ChongTrung(Nen):
    """W05 — chống trùng CƯỠNG CHẾ BẰNG CSDL (`UNIQUE(carrier_account_id, event_id)`)."""

    def test_c01_rang_buoc_UNIQUE_co_that_trong_schema(self):
        self.assertIn("UNIQUE (carrier_account_id, event_id)", csdl.SCHEMA,
                      "hợp đồng §12: ràng buộc phải nằm trong DDL")
        self.assertIn("UNIQUE (carrier_account_id, event_id)",
                      csdl.mot("SELECT sql FROM sqlite_master WHERE type='table'"
                               " AND name='wh_su_kien'")["sql"])

    def test_c02_CSDL_chan_that_khong_phai_ma_chan(self):
        """Nhồi thẳng bằng SQL, KHÔNG đi qua `nhan_su_kien` — nếu chỉ có `if` thì ca này lọt."""
        d = _don(self.ta, self.uid, self.tk_a, "MVD-C02", "cho_lay", 1)
        self.assertIsNotNone(d)
        b = body_hub("lay_hang", "MVD-C02", "E-C02")
        sk_id, trung, ma = self.gui(self.tk_a, b)
        self.assertFalse(trung)
        ev = self.sk(sk_id)["event_id"]
        with self.assertRaises(csdl.LoiToanVen,
                               msg="CSDL không chặn trùng — chống trùng đang nằm ở tầng mã"):
            csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                     "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                     (self.tk_a, ev, b, "{}", csdl.bay_gio()))
        self.assertEqual(self.dem("wh_su_kien", "carrier_account_id=? AND event_id=?",
                                  (self.tk_a, ev)), 1)

    def test_c03_gui_lai_y_nguyen_la_idempotent(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-C03", "cho_lay", 1)
        b = body_hub("dang_giao", "MVD-C03", "E-C03")
        sk1, trung1, ma1 = self.gui(self.tk_a, b)
        ls = self.dem("don_lich_su", "don_id=?", (d,))
        sk2, trung2, ma2 = self.gui(self.tk_a, b)
        self.assertFalse(trung1)
        self.assertEqual(ma1, 202)
        self.assertTrue(trung2, "callback gửi lại không bị coi là trùng")
        self.assertEqual(sk2, sk1, "trùng nhưng trả về id khác")
        self.assertEqual(ma2, 200)
        self.assertEqual(self.tt_don(d)[0], "dang_giao")
        self.assertEqual(self.dem("don_lich_su", "don_id=?", (d,)), ls,
                         "sự kiện trùng làm đổi lịch sử đơn lần thứ hai")

    def test_c04_khoa_chong_trung_tinh_theo_ACCOUNT_khong_theo_hang(self):
        """Hai tenant cùng dùng J&T. Cùng một event_id ở hai account là HAI sự kiện khác nhau."""
        d_a = _don(self.ta, self.uid, self.tk_a, "MVD-C04A", "cho_lay", 1)
        d_b = _don(self.tb, self.uid, self.tk_b, "MVD-C04B", "cho_lay", 1)
        b_a = body_hub("dang_giao", "MVD-C04A", "E-C04")
        b_b = body_hub("dang_giao", "MVD-C04B", "E-C04")
        _, t_a, _ = self.gui(self.tk_a, b_a)
        _, t_b, _ = self.gui(self.tk_b, b_b, secret=SECRET_B)
        self.assertFalse(t_a)
        self.assertFalse(t_b, "hai tenant khác nhau lại bị coi là trùng — mất sự kiện của một bên")
        self.assertEqual(self.tt_don(d_a)[0], "dang_giao")
        self.assertEqual(self.tt_don(d_b)[0], "dang_giao")

    def test_c05_dinh_danh_su_kien_JT_la_khoa_to_hop_billCode_scanTime_scanTypeCode(self):
        tk = self.row(self.tk_a)
        b1 = body_jt("MVD-C05", 106, "2026-10-15 08:00:00")
        b2 = body_jt("MVD-C05", 106, "2026-10-15 09:00:00")   # khác scanTime
        b3 = body_jt("MVD-C05", 113, "2026-10-15 08:00:00")   # khác scanTypeCode
        ids = {wh.dinh_danh_su_kien(tk, b) for b in (b1, b2, b3)}
        self.assertEqual(len(ids), 3, "ba bản quét khác nhau lại cùng một định danh")
        self.assertEqual(wh.dinh_danh_su_kien(tk, b1), wh.dinh_danh_su_kien(tk, b1))


# ============================================================================
class D_Tenant(Nen):
    """W03 — tenant chỉ đến từ carrier_account; chéo tenant là bất khả."""

    def test_d01_webhook_ma_khong_ton_tai(self):
        self.assertIsNone(wh.tim_account_theo_webhook_ma("khong-co-ma-nay"))
        self.assertIsNotNone(wh.tim_account_theo_webhook_ma("wh-g14-a"))

    def test_d02_tai_khoan_da_tat_thi_khong_tra_ve(self):
        self.assertIsNone(wh.tim_account_theo_webhook_ma("wh-g14-tat"),
                          "tài khoản kich_hoat=0 vẫn nhận được callback")
        self.assertIsNotNone(csdl.mot("SELECT id FROM carrier_accounts WHERE id=?", (self.tk_tat,)))

    def test_d03_khong_co_don_tuong_ung_thi_khong_dung_vao_don_cua_ai(self):
        truoc = {r["id"]: (r["trang_thai_giao"], r["hang_trang_thai_giao"])
                 for r in csdl.nhieu("SELECT id,trang_thai_giao,hang_trang_thai_giao FROM don_hang")}
        b = body_hub("giao_thanh_cong", "MVD-KHONG-CO", "E-D03")
        sk_id, trung, ma = self.gui(self.tk_a, b)
        self.assertFalse(trung)
        self.assertEqual(ma, 202)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertGreaterEqual(self.audit_co("webhook_khong_khop_don", f"su_kien:{sk_id}"), 1)
        for r in csdl.nhieu("SELECT id,trang_thai_giao,hang_trang_thai_giao FROM don_hang"):
            self.assertEqual((r["trang_thai_giao"], r["hang_trang_thai_giao"]), truoc[r["id"]],
                             f"đơn {r['id']} bị đụng bởi một sự kiện không khớp")

    def test_d04_CHÉO_TENANT_callback_cua_A_khong_duoc_cham_don_cua_B(self):
        """Ca gắt nhất của W03: cùng mã vận đơn, hai doanh nghiệp, hai tài khoản hãng."""
        d_b = _don(self.tb, self.uid, self.tk_b, "MVD-D04", "cho_lay", 1)
        b = body_jt("MVD-D04", 113, "2026-10-15 10:00:00")      # gửi vào tài khoản của A
        sk_id, trung, ma = self.gui(self.tk_a, b)
        self.assertFalse(trung)
        self.assertEqual(ma, 202)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertEqual(self.tt_don(d_b), ("cho_lay", 1),
                         "callback của tenant A đã cập nhật đơn của tenant B")
        self.assertGreaterEqual(self.audit_co("webhook_khong_khop_don", f"su_kien:{sk_id}"), 1)

    def test_d05_don_gan_sai_carrier_account_thi_cung_khong_duoc_cham(self):
        """Dữ liệu hỏng: đơn của tenant B nhưng gắn `carrier_account_id` của tenant A."""
        d = _don(self.tb, self.uid, self.tk_a, "MVD-D05", "cho_lay", 1)
        b = body_jt("MVD-D05", 113, "2026-10-15 10:00:00")
        sk_id, _, _ = self.gui(self.tk_a, b)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop")
        self.assertEqual(self.tt_don(d), ("cho_lay", 1),
                         "đơn gắn sai tài khoản hãng vẫn bị cập nhật")

    def test_d06_cung_ma_van_don_hai_tenant_thi_moi_ben_dung_don_cua_minh(self):
        d_a = _don(self.ta, self.uid, self.tk_a, "MVD-D06", "cho_lay", 1)
        d_b = _don(self.tb, self.uid, self.tk_b, "MVD-D06", "cho_lay", 1)
        b = body_jt("MVD-D06", 113, "2026-10-15 10:00:00")
        self.gui(self.tk_a, b)
        self.gui(self.tb, b, secret=SECRET_B)
        self.assertEqual(self.tt_don(d_a)[0], "giao_thanh_cong")
        self.assertEqual(self.tt_don(d_b)[0], "giao_thanh_cong")

    def test_d07_payload_khai_tenant_thi_GHI_LAI_roi_bo_qua(self):
        d_a = _don(self.ta, self.uid, self.tk_a, "MVD-D07", "cho_lay", 1)
        b = body_jt("MVD-D07", 106, "2026-10-15 08:00:00")
        biz = json.loads(urllib.parse.parse_qs(b.decode())["bizContent"][0])
        biz["tenant_id"] = self.tb                       # payload cố khai tenant B
        b = urllib.parse.urlencode({"bizContent": json.dumps(biz, ensure_ascii=False)}).encode()
        sk_id, _, _ = self.gui(self.tk_a, b)
        self.assertEqual(self.tt_don(d_a)[0], "lay_hang",
                         "payload khai tenant khác thì đơn CỦA ACCOUNT phải vẫn được cập nhật")
        self.assertGreaterEqual(self.audit_co("webhook_claim_tenant_bi_bo_qua", f"su_kien:{sk_id}"), 1)

    def test_d08_tenant_tu_account_la_nguon_duy_nhat(self):
        self.assertEqual(wh.tenant_tu_account(self.ta, 1), self.ta)
        with self.assertRaises(wh.LoiVinhVien):
            wh.tenant_tu_account(None, 1)
        with self.assertRaises(wh.LoiVinhVien):
            wh.tenant_tu_account("", 1)

    def test_d09_su_kien_mo_coi_bi_CSDL_chan_va_tang_xu_ly_van_khong_no(self):
        """Hai lớp: KHOÁ NGOẠI chặn từ đầu, và tầng xử lý vẫn phòng thủ nếu dòng ấy có thật."""
        with self.assertRaises(csdl.LoiToanVen,
                               msg="CSDL cho phép sự kiện trỏ vào tài khoản hãng không tồn tại"):
            csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                     "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                     (999999, "mo-coi-" + str(self.dem("wh_su_kien")),
                      body_hub("lay_hang", "MVD-D09"), "{}", csdl.bay_gio()))
        with self.assertRaises(wh.LoiVinhVien) as ctx:
            wh._xu_ly({"id": 0, "carrier_account_id": 999999,
                       "payload_tho": body_hub("lay_hang", "MVD-D09"),
                       "nhan_luc": csdl.bay_gio()})
        self.assertIn("biến mất", str(ctx.exception))


# ============================================================================
class E_SaiThuTu(Nen):
    """W05 — out-of-order: thứ hạng + watermark CHỈ tính sự kiện ĐÃ ÁP."""

    def test_e01_rank_guard_khong_keo_lui(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E01", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E01", 113, "2026-10-15 10:00:00"))
        self.gui(self.tk_a, body_jt("MVD-E01", 112, "2026-10-15 11:00:00"))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong")

    def test_e02_moc_hang_chan_ban_tin_CU_that_su(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E02", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E02", 112, "2026-10-15 12:00:00"))
        sk_id, _, _ = self.gui(self.tk_a, body_jt("MVD-E02", 113, "2026-10-15 08:00:00"))
        self.assertEqual(self.tt_don(d)[0], "dang_giao", "bản tin cũ ghi đè được trạng thái")
        self.assertGreaterEqual(self.audit_co("webhook_den_muon", f"don:{d}"), 1)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong")

    def test_e03_VÁ_G14_ma_110_KHONG_duoc_dau_doc_watermark(self):
        """LỖI ĐO ĐƯỢC (xem docs/G14_JT_WEBHOOK.md §4).

        Trước bản vá: `110` (không áp trạng thái) vẫn đẩy `hang_moc_thoi_gian` lên 10:00, nên
        `106` lúc 09:00 đến sau bị chặn với lý do "đến muộn" ⇒ mất một bước hành trình CÓ THẬT.
        """
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E03", "cho_lay", 1)
        sk110, _, _ = self.gui(self.tk_a, body_jt("MVD-E03", 110, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1))
        self.assertIsNone(wh.watermark(d),
                          "mã nhập nhằng (không áp trạng thái) đã đẩy watermark của đơn")
        sk106, _, _ = self.gui(self.tk_a, body_jt("MVD-E03", 106, "2026-10-15 09:00:00"))
        self.assertEqual(self.tt_don(d)[0], "lay_hang",
                         "bản quét CÓ THẬT bị chặn oan vì một mã không được áp đứng trước")
        self.assertEqual(self.audit_co("webhook_den_muon", f"don:{d}"), 0)
        # G14 vá triệt để (B12, 15/10/2026): sự kiện KHÔNG được áp không ghi cột mốc nữa.
        # Mất quyền ĐẨY MỐC, không mất dữ kiện — mốc gốc của hãng vẫn nằm trong audit ánh xạ.
        self.assertIsNone(self.sk(sk110)["hang_moc_thoi_gian"])
        self.assertIsNone(self.sk(sk110)["trang_thai_chuan"])
        au = csdl.mot("SELECT chi_tiet FROM audit WHERE hanh_dong='webhook_anh_xa'"
                      " AND doi_tuong=? ORDER BY id DESC LIMIT 1", (f"su_kien:{sk110}",))
        self.assertEqual(json.loads(au["chi_tiet"])["su_kien_hang_goc"]["moc_hang"],
                         wh._moc_chuan("2026-10-15 10:00:00"))
        self.assertEqual(self.sk(sk106)["trang_thai_chuan"], "lay_hang")
        self.assertEqual(self.sk(sk106)["hang_moc_thoi_gian"],
                         wh._moc_chuan("2026-10-15 09:00:00"))

    def test_e08_B12_su_kien_bi_RANK_GUARD_chan_KHONG_duoc_day_watermark(self):
        """Ca còn lại của §4.3 — mã CŨ vẫn để lọt.

        `don_hang.ap_trang_thai_giao` trả `ap_dung=0` khi sự kiện đến muộn theo THỨ HẠNG. Sự kiện
        ấy không đổi được gì, nhưng mã cũ vẫn ghi `hang_moc_thoi_gian` cho nó ⇒ mốc nhảy lên, và
        một bản quét CÓ THẬT đến sau với mốc cũ hơn (nhưng hạng cao hơn) bị chặn oan.

        Kịch bản cố ý dựng để CÔ LẬP đúng cơ chế: đơn đang `dang_giao` (mốc đã áp 09:00) → một
        bản quét `106` lúc 11:00 bị rank guard chặn (hạng 2 ≤ 3) → rồi `113 Delivered` lúc 10:00
        đến sau. Trước bản vá: mốc đã nhảy lên 11:00 nên `113` bị chặn ⇒ MẤT trạng thái giao
        thành công. Sau bản vá: mốc vẫn 09:00, `113` được áp.
        """
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E08", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E08", 112, "2026-10-15 09:00:00"))
        self.assertEqual(self.tt_don(d)[0], "dang_giao")
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 09:00:00"))

        sk_chan, _, _ = self.gui(self.tk_a, body_jt("MVD-E08", 106, "2026-10-15 11:00:00"))
        self.assertEqual(self.tt_don(d)[0], "dang_giao", "rank guard không chặn được sự kiện lùi")
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 09:00:00"),
                         "sự kiện bị rank guard chặn lại đẩy được mốc của đơn")
        self.assertIsNone(self.sk(sk_chan)["hang_moc_thoi_gian"])
        self.assertEqual(self.sk(sk_chan)["trang_thai_chuan"], "lay_hang",
                         "dấu vết ánh xạ phải còn, chỉ quyền đẩy mốc bị bỏ")
        self.assertGreaterEqual(self.audit_co("webhook_cap_nhat_don", f"don:{d}"), 1)

        self.gui(self.tk_a, body_jt("MVD-E08", 113, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong",
                         "bản quét HỢP LỆ bị chặn oan vì một sự kiện không đổi được gì đứng trước")
        self.assertEqual(self.audit_co("webhook_den_muon", f"don:{d}"), 0)
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 10:00:00"))

    def test_e09_du_lieu_CU_do_ma_chua_va_van_bi_bo_qua(self):
        """Bộ lọc `trang_thai_chuan IS NOT NULL` phải GIỮ: nó cứu dữ liệu đã nằm trong CSDL thật.

        Dòng dưới đây mô phỏng đúng thứ mã CŨ để lại: một sự kiện không được áp nhưng vẫn có
        `hang_moc_thoi_gian`. Xoá bộ lọc là lỗi cũ sống lại trên dữ liệu đang có.
        """
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E09", "cho_lay", 1)
        sk_cu = csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                         "headers_json,nhan_luc,trang_thai,don_id,hang_moc_thoi_gian,"
                         "trang_thai_chuan) VALUES (?,?,?,?,?,'xong',?,?,NULL)",
                         (self.tk_a, "cu-" + str(self.dem("wh_su_kien")), b"{}", "{}",
                          csdl.bay_gio(), d, "01792033200000")).lastrowid
        self.assertIsNotNone(sk_cu)
        self.assertIsNone(wh.watermark(d), "dòng do mã CŨ ghi lại đẩy được mốc")
        self.gui(self.tk_a, body_jt("MVD-E09", 112, "2026-10-15 09:00:00"))
        self.assertEqual(self.tt_don(d)[0], "dang_giao",
                         "dòng cũ (không áp) chặn oan bản quét có thật")

    def test_e04_VÁ_G14_ma_chi_ghi_nhan_KHONG_lam_mat_DELIVERED(self):
        """Ca đắt nhất: `121 FINISH` (không áp) lúc 10:00 chặn `113 Delivered` lúc 09:00."""
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E04", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E04", 121, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1))
        self.gui(self.tk_a, body_jt("MVD-E04", 113, "2026-10-15 09:00:00"))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong",
                         "đơn đã giao mà hệ thống KHÔNG BAO GIỜ biết — mã 121 chặn oan")

    def test_e05_su_kien_DUOC_AP_van_day_watermark_binh_thuong(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E05", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E05", 112, "2026-10-15 10:00:00"))
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 10:00:00"))
        self.gui(self.tk_a, body_jt("MVD-E05", 113, "2026-10-15 12:00:00"))
        self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 12:00:00"))

    def test_e06_khong_co_moc_thi_lui_ve_rank_guard(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E06", "cho_lay", 1)
        self.gui(self.tk_a, body_hub("lay_hang", "MVD-E06", "E-E06"))
        self.assertEqual(self.tt_don(d)[0], "lay_hang")

    def test_e07_csdl_chua_migrate_thi_lui_ve_nguon_audit_chu_khong_no(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-E07", "cho_lay", 1)
        self.gui(self.tk_a, body_jt("MVD-E07", 112, "2026-10-15 10:00:00"))
        that = wh.cot_co

        def gia(bang, cot):
            return False if (bang == "wh_su_kien" and cot in ("don_id", "hang_moc_thoi_gian",
                                                              "trang_thai_chuan")) \
                else that(bang, cot)

        wh.cot_co = gia
        try:
            self.assertEqual(wh.watermark(d), wh._moc_chuan("2026-10-15 10:00:00"),
                             "nguồn audit (chỉ ghi khi ĐÃ ÁP) không được dùng làm phương án lùi")
        finally:
            wh.cot_co = that


# ============================================================================
class F_Ma110(Nen):
    """W04 — mã nhập nhằng 110 + mã lạ + bộ mã thứ hai: chặn CỨNG, và không đụng tới tiền."""

    def _cod_truoc(self, tenant_id, don_id):
        """Mở sổ COD ở COD_EXPECTED rồi trả về ảnh chụp để so TRƯỚC/SAU."""
        tai_chinh.mo_so_cod(tenant_id, don_id, so_tien_du_kien=250000, tao_boi=self.uid)
        return (tai_chinh.cod_cua_don(tenant_id, don_id)["trang_thai"],
                self.dem("tc_cod_chuyen", "don_id=?", (don_id,)),
                self.dem("tc_but_toan", "don_id=?", (don_id,)))

    def test_f01_110_khong_doi_trang_thai_va_duoc_danh_dau_can_soat(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-F01", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_jt("MVD-F01", 110, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1))
        r = self.sk(sk_id)
        self.assertEqual(r["can_soat"], 1)
        self.assertIsNone(r["trang_thai_chuan"])
        self.assertEqual(r["hang_ma_goc"], "110")
        self.assertEqual(r["anh_xa_do_tin_cay"], tth.TIN_NHAP_NHANG)
        self.assertEqual(tth.quyet_dinh("jt", 110).nhan, "AMBIGUOUS")
        self.assertGreaterEqual(self.audit_co("webhook_can_soat", f"don:{d}"), 1)

    def test_f02_110_khong_bao_gio_ra_hoan_tat_du_chot_nghia_nao(self):
        for lam in (lambda: None,
                    lambda: tth.chot_nghia("jt", 110, "bang_tham_so", "G14 test", "giả định"),
                    lambda: tth.chot_nghia("jt", 110, "vi_du_tra_loi", "G14 test", "giả định")):
            tth.bo_chot_nghia()
            lam()
            mvd = "MVD-F02-" + str(self.dem("wh_su_kien"))
            d = _don(self.ta, self.uid, self.tk_a, mvd, "cho_lay", 1)
            self.gui(self.tk_a, body_jt(mvd, 110, "2026-10-15 10:00:00"))
            self.assertNotIn(self.tt_don(d)[0], tth.TRANG_THAI_HOAN_TAT,
                             "mã 110 đẩy được đơn sang trạng thái hoàn tất")
        tth.bo_chot_nghia()

    def test_f03_110_khong_duoc_ap_hoan_tat_ke_ca_khi_nhoi_thang_vao_so_chot(self):
        try:
            tth.NGHIA_DA_CHOT[("jt", 110)] = {"khoa_nghia": "nghia_bay",
                                              "trang_thai": "giao_thanh_cong",
                                              "nguoi_chot": "x", "can_cu": "y",
                                              "mo_ta_hang": "bịa"}
            d = _don(self.ta, self.uid, self.tk_a, "MVD-F03", "cho_lay", 1)
            self.gui(self.tk_a, body_jt("MVD-F03", 110, "2026-10-15 10:00:00"))
            self.assertEqual(self.tt_don(d), ("cho_lay", 1),
                             "nhồi sổ chốt là đẩy được đơn sang hoàn tất")
        finally:
            tth.bo_chot_nghia()

    def test_f04_ma_la_thi_NEEDS_REVIEW_khong_doan_nghia(self):
        """`999` không có trong bảng tham số đã đọc: chỉ ghi nhận, KHÔNG đổi trạng thái."""
        d = _don(self.ta, self.uid, self.tk_a, "MVD-F04", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_jt("MVD-F04", 999, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1))
        r = self.sk(sk_id)
        self.assertEqual(r["can_soat"], 1)
        self.assertEqual(r["anh_xa_do_tin_cay"], tth.TIN_MA_LA)
        self.assertIsNone(r["trang_thai_chuan"])
        self.assertEqual(tth.quyet_dinh("jt", 999).nhan, "NEEDS_REVIEW")

    def test_f05_BO_MA_THU_HAI_chua_kiem_thi_khong_duoc_keo_vao_hoan_tat(self):
        """Tài liệu còn một bộ mã KHÁC trong ví dụ: 10/50/92/94/100/110.

        Trong bộ đó `100` = "Ký nhận" (đã giao). Bộ mã này CHƯA được hãng xác nhận, nên `100`
        phải đi qua đúng đường của mã lạ: giữ nguyên đơn + đánh dấu cần soát.
        """
        self.assertNotIn(100, tth.JT_MA, "100 đã bị đưa vào bảng ánh xạ mà chưa có căn cứ")
        for ma in (10, 50, 92, 94, 100):
            mvd = f"MVD-F05-{ma}"
            d = _don(self.ta, self.uid, self.tk_a, mvd, "cho_lay", 1)
            sk_id, _, _ = self.gui(self.tk_a, body_jt(mvd, ma, "2026-10-15 10:00:00"))
            self.assertEqual(self.tt_don(d), ("cho_lay", 1), f"mã {ma} của bộ thứ hai bị đoán nghĩa")
            self.assertEqual(self.sk(sk_id)["can_soat"], 1, f"mã {ma} không được đánh dấu soát")

    def test_f06_W04_110_va_ma_la_KHONG_duoc_dung_toi_COD(self):
        t = self.nen_moi("f06")
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-F06", cod=250000)
        truoc = self._cod_truoc(t["tenant_id"], d)
        self.assertEqual(truoc[0], "COD_EXPECTED")
        self.gui(t["tk"], body_jt("MVD-F06", 110, "2026-10-15 10:00:00"))
        self.gui(t["tk"], body_jt("MVD-F06", 999, "2026-10-15 11:00:00"))
        self.assertEqual(self.tt_don(d), ("cho_lay", 1))
        self.assertEqual(
            (tai_chinh.cod_cua_don(t["tenant_id"], d)["trang_thai"],
             self.dem("tc_cod_chuyen", "don_id=?", (d,)),
             self.dem("tc_but_toan", "don_id=?", (d,))), truoc,
            "trạng thái CHƯA xác minh lại đụng được vào sổ COD")

    def test_f07_giao_thanh_cong_KHONG_phai_da_thu_tien(self):
        """Hợp đồng §18 — luật quan trọng nhất của G07. Giao hàng ≠ tiền COD đã về."""
        t = self.nen_moi("f07")
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-F07", cod=250000)
        truoc = self._cod_truoc(t["tenant_id"], d)
        self.gui(t["tk"], body_jt("MVD-F07", 113, "2026-10-15 10:00:00"))
        self.assertEqual(self.tt_don(d)[0], "giao_thanh_cong")
        self.assertEqual(
            (tai_chinh.cod_cua_don(t["tenant_id"], d)["trang_thai"],
             self.dem("tc_cod_chuyen", "don_id=?", (d,)),
             self.dem("tc_but_toan", "don_id=?", (d,))), truoc,
            "một sự kiện GIAO HÀNG lại chuyển được trạng thái COD")

    def test_f08_webhook_khong_co_duong_nao_cham_vao_tien(self):
        import inspect
        nguon = inspect.getsource(wh)
        for cam in ("import tai_chinh", "import doi_soat", "chuyen_cod", "ghi_but_toan",
                    "tc_cod", "UPDATE don_hang"):
            self.assertNotIn(cam, nguon, f"webhook.py có '{cam}' — vượt ranh giới §18")


# ============================================================================
class G_RetryDLQReplay(Nen):
    """W05 — retry có trần, DLQ, replay có phép + có trần + không mất im lặng."""

    def _day_toi_ket_cuc(self, sk_id, toi_da=12):
        for _ in range(toi_da):
            if self.sk(sk_id)["trang_thai"] in ("dlq", "xong", "khong_khop"):
                break
            wh._chay_mot(sk_id)
        return self.sk(sk_id)

    def test_g01_loi_tam_thoi_thi_thu_lai_roi_vao_DLQ(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-G01", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("dang_giao", "MVD-G01", "E-G01",
                                                   demo_force_fail=True))
        r = self.sk(sk_id)
        self.assertEqual(r["trang_thai"], "cho_thu_lai")
        self.assertEqual(r["so_lan_thu"], 1)
        self.assertIn("demo_force_fail", r["loi_cuoi"])
        r = self._day_toi_ket_cuc(sk_id)
        self.assertEqual(r["trang_thai"], "dlq")
        self.assertGreaterEqual(r["so_lan_thu"], cau_hinh.WEBHOOK_SO_LAN_THU - 1)
        self.assertGreaterEqual(self.audit_co("webhook_dlq", f"su_kien:{sk_id}"), 1)
        self.assertEqual(self.tt_don(d)[0], "cho_lay", "sự kiện hỏng vẫn đổi được trạng thái đơn")

    def test_g02_loi_vinh_vien_vao_DLQ_ngay_khong_dot_luot_thu_nao(self):
        sk_id = csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                         "headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                         (self.tk_a, f"rac-{self.dem('wh_su_kien')}", b"khong-phai-json",
                          "{}", csdl.bay_gio())).lastrowid
        wh._chay_mot(sk_id)
        r = self.sk(sk_id)
        self.assertEqual(r["trang_thai"], "dlq")
        self.assertEqual(r["so_lan_thu"], 0, "lỗi vĩnh viễn mà vẫn đốt lượt thử")
        self.assertIn("vinh vien", r["loi_cuoi"])

    def test_g03_nhan_viec_nguyen_tu_mot_nguoi_lay_duoc(self):
        b = body_hub("lay_hang", "MVD-G03", "E-G03")
        sk_id, _, _ = self.gui(self.tk_a, b)
        # sự kiện đã 'xong' ⇒ không ai nhận lại
        self.assertIsNone(wh._nhan_viec(sk_id))
        csdl.ghi("UPDATE wh_su_kien SET trang_thai='moi' WHERE id=?", (sk_id,))
        self.assertIsNotNone(wh._nhan_viec(sk_id))
        self.assertEqual(self.sk(sk_id)["trang_thai"], "dang_xu_ly")
        self.assertIsNone(wh._nhan_viec(sk_id), "hai worker cùng nhận được MỘT sự kiện")

    def test_g04_replay_duoc_phep_theo_tenant_va_co_audit(self):
        _don(self.ta, self.uid, self.tk_a, "MVD-G04", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-G04", "E-G04")
        sk_id, _, _ = self.gui(self.tk_a, b)
        # tenant B đòi replay sự kiện của A → từ chối. CỐ Ý KHÔNG ghi audit kèm số sự kiện:
        # tầng HTTP đã cố tình trả 404 giống hệt "không có" để không ai dò được ID bằng cách
        # so 404 với 409 (TEST-011). Ghi một dòng audit nói "ID này có nhưng không phải của bạn"
        # là mở lại đúng kênh dò ấy ở tầng đọc audit. Đánh đổi có ghi ở docs/G14_JT_WEBHOOK.md.
        truoc_audit = self.audit_co("webhook_replay_tu_choi")
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.tb)
        self.assertFalse(ok)
        self.assertEqual(self.audit_co("webhook_replay_tu_choi"), truoc_audit,
                         "ghi audit kèm số sự kiện là mở lại kênh dò ID")
        self.assertEqual(self.sk(sk_id)["trang_thai"], "xong", "tenant khác đổi được trạng thái")
        self.assertEqual(wh.so_lan_replay(sk_id), 0)
        self.assertEqual(self.dem("wh_su_kien", "id=? AND carrier_account_id=?",
                                  (sk_id, self.tk_a)), 1, "sự kiện bị đổi chủ")
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertTrue(ok, ly_do)
        self.assertEqual(wh.so_lan_replay(sk_id), 1)
        self.assertGreaterEqual(self.audit_co("webhook_replay", f"su_kien:{sk_id}"), 1)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "moi")

    def test_g05_replay_co_tran(self):
        b = body_hub("lay_hang", "MVD-G05", "E-G05")
        sk_id, _, _ = self.gui(self.tk_a, b)
        for i in range(wh.REPLAY_TOI_DA):
            ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
            self.assertTrue(ok, f"lượt {i}: {ly_do}")
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertFalse(ok, "replay không có trần — bấm mãi là vòng lặp vô hạn")
        self.assertIn("trần", ly_do)
        self.assertGreaterEqual(self.audit_co("webhook_replay_tu_choi", f"su_kien:{sk_id}"), 1)

    def test_g06_replay_khi_dang_xu_ly_thi_TU_CHOI_chu_khong_mat_im_lang(self):
        """VÁ G14: đặt 'moi' khi worker đang giữ sự kiện ⇒ lượt replay bị nuốt im lặng."""
        b = body_hub("lay_hang", "MVD-G06", "E-G06")
        sk_id, _, _ = self.gui(self.tk_a, b)
        csdl.ghi("UPDATE wh_su_kien SET trang_thai='dang_xu_ly' WHERE id=?", (sk_id,))
        truoc = wh.so_lan_replay(sk_id)
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertFalse(ok)
        self.assertIn("đang được xử lý", ly_do)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "dang_xu_ly")
        self.assertEqual(wh.so_lan_replay(sk_id), truoc)

    def test_g07_quyen_replay_do_tang_HTTP_kiem(self):
        for vai in ("TENANT_OWNER", "TENANT_ADMIN"):
            self.assertTrue(quyen.co_quyen(vai, "tenant.webhook.replay"), vai)
        for vai in ("TENANT_VIEWER", "TENANT_STAFF"):
            self.assertFalse(quyen.co_quyen(vai, "tenant.webhook.replay"), vai)
        self.assertTrue(quyen.co_quyen("TENANT_VIEWER", "tenant.webhook.xem"))

    def test_g08_replay_tu_DLQ_chay_lai_duoc(self):
        d = _don(self.ta, self.uid, self.tk_a, "MVD-G08", "cho_lay", 1)
        sk_id, _, _ = self.gui(self.tk_a, body_hub("dang_giao", "MVD-G08", "E-G08",
                                                   demo_force_fail=True))
        self._day_toi_ket_cuc(sk_id)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "dlq")
        # sửa nguyên nhân rồi replay: payload đổi nên là sự kiện MỚI, còn ca replay thật là
        # sự kiện cũ chạy lại và vẫn hỏng — ở đây kiểm ĐÚNG đường replay, không kiểm phép màu.
        ok, ly_do = wh.yeu_cau_replay(sk_id, self.ta, self.uid)
        self.assertTrue(ok, ly_do)
        self.assertEqual(self.sk(sk_id)["so_lan_thu"], 0)
        self.assertEqual(self.tt_don(d)[0], "cho_lay")


# ============================================================================
class H_DoiChieu(Nen):
    """W05 — đối chiếu hành trình. Phép kiểm phải TỰ CHỨNG MINH là nó bắt được lỗi."""

    def test_h01_nen_sach_thi_khong_co_gi_de_bao(self):
        t = self.nen_moi("h01")
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H01", "cho_lay", 1)
        self.gui(t["tk"], body_jt("MVD-H01", 112, "2026-10-15 10:00:00"))
        tk = wh.doi_chieu_hanh_trinh(t["tenant_id"])
        self.assertTrue(tk["bat_bien_tenant_dat"])
        self.assertEqual(tk["lech_tenant"], [])
        self.assertEqual(tk["su_kien_mo_coi"], [])
        self.assertEqual(tk["khong_khop"], [])
        self.assertEqual(tk["cho_nguoi_soat"], [])
        self.assertEqual(tk["ket_dinh"], [])
        self.assertEqual(tk["bo_qua"], [], "CSDL đã đủ cột mà vẫn khai bỏ qua phần nào đó")
        self.assertEqual(self.tt_don(d)[0], "dang_giao")

    def test_h02_khong_khop_va_can_soat_va_DLQ_deu_hien_ra(self):
        t = self.nen_moi("h02")
        self.gui(t["tk"], body_jt("MVD-H02-LA", 106, "2026-10-15 08:00:00"))     # không có đơn
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H02", "cho_lay", 1)
        self.gui(t["tk"], body_jt("MVD-H02", 110, "2026-10-15 10:00:00"))        # nhập nhằng
        csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,"
                 "nhan_luc,trang_thai,loi_cuoi) VALUES (?,?,?,?,?,'dlq','hỏng')",
                 (t["tk"], "h02-dlq-" + str(self.dem("wh_su_kien")), b"rac", "{}", csdl.bay_gio()))
        tk = wh.doi_chieu_hanh_trinh(t["tenant_id"])
        self.assertEqual(len(tk["khong_khop"]), 1)
        self.assertEqual(len(tk["cho_nguoi_soat"]), 1)
        self.assertEqual(tk["cho_nguoi_soat"][0]["hang_ma_goc"], "110")
        self.assertEqual(len(tk["ket_dinh"]), 1)
        self.assertEqual(tk["ket_dinh"][0]["trang_thai"], "dlq")
        self.assertTrue(tk["bat_bien_tenant_dat"])
        self.assertEqual(self.tt_don(d)[0], "cho_lay")

    def test_h03_cach_ly_tenant_trong_bao_cao(self):
        t_a, t_b = self.nen_moi("h03a"), self.nen_moi("h03b")
        self.gui(t_a["tk"], body_jt("MVD-H03-A", 106, "2026-10-15 08:00:00"))
        self.gui(t_b["tk"], body_jt("MVD-H03-B", 106, "2026-10-15 08:00:00"))
        tk_a = wh.doi_chieu_hanh_trinh(t_a["tenant_id"])
        self.assertEqual(len(tk_a["khong_khop"]), 1, "báo cáo của A lẫn sự kiện của B")
        self.assertTrue(tk_a["khong_khop"][0]["event_id"].startswith("jt-"))
        tk_b = wh.doi_chieu_hanh_trinh(t_b["tenant_id"])
        self.assertEqual(len(tk_b["khong_khop"]), 1)

    def test_h04_PHEP_KIEM_TU_CHUNG_MINH_bom_don_cheo_tenant_thi_phai_bat_duoc(self):
        """§12.1: thứ dùng để kiểm chứng phải tự nó đáng tin.

        Nhồi thẳng một dòng `don_id` trỏ sang đơn của tenant KHÁC rồi xem phép đối chiếu có bắt
        được không. Không có ca này thì `lech_tenant == []` không chứng minh được gì cả.
        """
        t_a, t_b = self.nen_moi("h04a"), self.nen_moi("h04b")
        d_b = _don(t_b["tenant_id"], t_b["uid"], t_b["tk"], "MVD-H04-B", "cho_lay", 1)
        d_a = _don(t_a["tenant_id"], t_a["uid"], t_a["tk"], "MVD-H04-A", "cho_lay", 1)
        sk_id, _, _ = self.gui(t_a["tk"], body_jt("MVD-H04-A", 112, "2026-10-15 10:00:00"))
        self.assertEqual(wh.doi_chieu_hanh_trinh(t_a["tenant_id"])["lech_tenant"], [])
        csdl.ghi("UPDATE wh_su_kien SET don_id=? WHERE id=?", (d_b, sk_id))
        try:
            tk = wh.doi_chieu_hanh_trinh(t_a["tenant_id"])
            self.assertEqual(len(tk["lech_tenant"]), 1, "đối chiếu KHÔNG bắt được dòng chéo tenant")
            self.assertFalse(tk["bat_bien_tenant_dat"])
            self.assertEqual(tk["lech_tenant"][0]["tenant_don"], t_b["tenant_id"])
            self.assertEqual(tk["lech_tenant"][0]["tenant_account"], t_a["tenant_id"])
            # B KHÔNG được thấy dòng ấy: dòng thuộc account của A, nên báo cáo của B không
            # được phơi sự kiện của A ra — kể cả khi dòng đó đang trỏ sai vào đơn của B.
            self.assertEqual(wh.doi_chieu_hanh_trinh(t_b["tenant_id"])["lech_tenant"], [],
                             "báo cáo của B phơi sự kiện của A")
            # và đơn của B KHÔNG bị đụng: dòng nhồi chỉ là con trỏ hỏng, không phải cập nhật.
            self.assertEqual(self.tt_don(d_b), ("cho_lay", 1))
        finally:
            csdl.ghi("UPDATE wh_su_kien SET don_id=? WHERE id=?", (d_a, sk_id))
        self.assertEqual(wh.doi_chieu_hanh_trinh(t_a["tenant_id"])["lech_tenant"], [])

    def test_h05_su_kien_mo_coi_bi_bat(self):
        t = self.nen_moi("h05")
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H05", "cho_lay", 1)
        sk_id, _, _ = self.gui(t["tk"], body_jt("MVD-H05", 112, "2026-10-15 10:00:00"))
        csdl.ghi("UPDATE wh_su_kien SET don_id=? WHERE id=?", (d + 999999, sk_id))
        try:
            tk = wh.doi_chieu_hanh_trinh(t["tenant_id"])
            self.assertEqual(len(tk["su_kien_mo_coi"]), 1)
        finally:
            csdl.ghi("UPDATE wh_su_kien SET don_id=? WHERE id=?", (d, sk_id))

    def test_h06_don_treo_va_don_khong_su_kien(self):
        t = self.nen_moi("h06")
        d_treo = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H06-TREO", "dang_giao", 3)
        self.gui(t["tk"], body_jt("MVD-H06-TREO", 112, "2026-10-15 10:00:00"))
        d_khong = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H06-KHONG", "cho_lay", 1)
        tk = wh.doi_chieu_hanh_trinh(t["tenant_id"], giay_gan_nhat=0)   # ép mọi thứ thành "cũ"
        self.assertEqual([x["don_id"] for x in tk["don_treo"]], sorted([d_treo, d_khong]))
        self.assertEqual([x["don_id"] for x in tk["don_khong_su_kien"]], [d_khong])
        self.assertTrue(tk["can_polling"])

    def test_h07_doi_chieu_chi_DOC_khong_sua_gi(self):
        t = self.nen_moi("h07")
        _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H07", "cho_lay", 1)
        self.gui(t["tk"], body_jt("MVD-H07", 110, "2026-10-15 10:00:00"))
        truoc = (self.dem("wh_su_kien"), self.dem("don_hang"), self.dem("audit"))
        wh.doi_chieu_hanh_trinh(t["tenant_id"], giay_gan_nhat=0)
        self.assertEqual((self.dem("wh_su_kien"), self.dem("don_hang"), self.dem("audit")), truoc)

    def test_h08_csdl_chua_migrate_thi_noi_ro_phan_bo_qua_chu_khong_tra_rong_gia(self):
        t = self.nen_moi("h08")
        _don(t["tenant_id"], t["uid"], t["tk"], "MVD-H08", "cho_lay", 1)
        that = wh.cot_co

        def gia(bang, cot):
            return False if (bang == "wh_su_kien"
                             and cot in ("don_id", "can_soat", "hang_ma_goc")) else that(bang, cot)

        wh.cot_co = gia
        try:
            tk = wh.doi_chieu_hanh_trinh(t["tenant_id"])
            self.assertIsNone(tk["lech_tenant"],
                              "trả [] khi CHƯA kiểm được là nói dối rằng đã kiểm")
            self.assertIsNone(tk["bat_bien_tenant_dat"])
            self.assertTrue(tk["bo_qua"])
        finally:
            wh.cot_co = that


# ============================================================================
class I_HTTPThat(Nen):
    """W06 — máy chủ THẬT, bind 127.0.0.1, cổng do hệ điều hành cấp (không giành cổng với ai)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if LOI_IMPORT_SERVER:
            raise unittest.SkipTest(f"không import được app/server.py: {LOI_IMPORT_SERVER}")
        from http.server import ThreadingHTTPServer
        # Worker THẬT của hub, không gọi tay `_chay_mot`: ca này phải đi hết đường HTTP → hàng đợi.
        wh.khoi_dong()
        cls.sv = ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
        cls.cong = cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, name="g14-http", daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        if not LOI_IMPORT_SERVER:
            wh.dung()
            cls.sv.shutdown()
            cls.sv.server_close()

    def post(self, wh_ma, body, headers):
        yc = urllib.request.Request(f"http://127.0.0.1:{self.cong}/api/v2/webhook/nhan/{wh_ma}",
                                    data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(yc, timeout=10) as ph:
                return ph.status, json.loads(ph.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_i01_chi_bind_127_0_0_1(self):
        self.assertEqual(self.sv.server_address[0], "127.0.0.1")

    def test_i02_webhook_ma_khong_ton_tai_tra_404(self):
        ma, _ = self.post("khong-co-ma-nay", b"{}", {"Content-Type": "application/json"})
        self.assertEqual(ma, 404)

    def test_i03_chu_ky_sai_tra_401_va_KHONG_luu_su_kien(self):
        # Tài khoản RIÊNG cho ca này: bộ đếm `webhook.chu_ky_sai` là 10 lượt/60 giây rồi chặn
        # 300 giây, nên không được đốt bộ đếm của tài khoản dùng chung.
        t = self.nen_moi("i03")
        wh_ma = csdl.mot("SELECT webhook_ma FROM carrier_accounts WHERE id=?", (t["tk"],))["webhook_ma"]
        b = body_hub("lay_hang", "MVD-I03", "E-I03")
        truoc = self.dem("wh_su_kien", "carrier_account_id=?", (t["tk"],))
        ma, than = self.post(wh_ma, b, {"X-Webhook-Signature": "0" * 64})
        self.assertEqual(ma, 401)
        self.assertEqual(self.dem("wh_su_kien", "carrier_account_id=?", (t["tk"],)), truoc,
                         "sự kiện không xác thực được lại vào kho")

    def test_i04_callback_hop_le_qua_HTTP_va_trung_lap(self):
        t = self.nen_moi("i04")
        d = _don(t["tenant_id"], t["uid"], t["tk"], "MVD-I04", "cho_lay", 1)
        wh_ma = csdl.mot("SELECT webhook_ma FROM carrier_accounts WHERE id=?", (t["tk"],))["webhook_ma"]
        b = body_hub("dang_giao", "MVD-I04", "E-I04")
        ma, than = self.post(wh_ma, b, ky_hub(SECRET_A, b))
        self.assertEqual(ma, 202, than)
        self.assertEqual(than["ket_qua"], "da_nhan")
        ma2, than2 = self.post(wh_ma, b, ky_hub(SECRET_A, b))
        self.assertEqual(ma2, 200)
        self.assertEqual(than2["ket_qua"], "da_nhan_truoc_do")
        self.assertTrue(wh.cho_rong(10), "worker nền không xử lý xong")
        self.assertEqual(self.tt_don(d)[0], "dang_giao")

    def test_i05_phan_hoi_HTTP_CO_truong_code_bang_1_o_CA_HAI_nhanh(self):
        """Khoảng hở đã ĐÓNG (AG-00 cắm `phan_hoi_xac_nhan` vào route ngày 15/10/2026).

        Ca này trước đây ĐO KHOẢNG HỞ (khẳng định route THIẾU `code`). Nay nó khẳng định điều
        ngược lại, và **vẫn giữ nguyên giới hạn**: đây KHÔNG phải bằng chứng hợp đồng phản hồi đã
        được xác minh.

        Cái đã biết chỉ là MỘT MẢNH của trích lục câu 9: phản hồi có trường `code`, và `code=1`
        là được nhận. Còn **`B3` CHƯA có trả lời**: mã HTTP nào là đúng, còn trường nào khác, và
        `200`/`202` có bị J&T coi là hỏng không. Vì vậy AG-00 **cố ý giữ nguyên mã HTTP cũ**
        (202 lượt mới · 200 lượt trùng) — đổi nó là đoán. Mức của trường `phan_hoi_xac_nhan`
        trong `webhook.HOP_DONG_CALLBACK` vẫn là `CHUA_TAI_LIEU`, và ca `test_a02` canh đúng điều
        đó: bản vá này KHÔNG được đọc thành "hợp đồng phản hồi đã xác minh".
        """
        t = self.nen_moi("i05")
        wh_ma = csdl.mot("SELECT webhook_ma FROM carrier_accounts WHERE id=?", (t["tk"],))["webhook_ma"]
        _don(t["tenant_id"], t["uid"], t["tk"], "MVD-I05", "cho_lay", 1)
        b = body_hub("lay_hang", "MVD-I05", "E-I05")
        ma, than = self.post(wh_ma, b, ky_hub(SECRET_A, b))
        self.assertEqual(ma, 202)
        self.assertEqual(than.get("code"), 1, f"lượt MỚI thiếu `code=1`: {than}")
        self.assertEqual(than["ket_qua"], "da_nhan", "bản vá không được phá trường cũ")
        ma2, than2 = self.post(wh_ma, b, ky_hub(SECRET_A, b))
        self.assertEqual(ma2, 200)
        self.assertEqual(than2.get("code"), 1,
                         f"lượt TRÙNG phải vẫn là thành công (idempotent): {than2}")
        self.assertEqual(than2["ket_qua"], "da_nhan_truoc_do")
        # Chốt chặn phạm vi: mức tài liệu KHÔNG được nâng lên vì bản vá này.
        self.assertEqual(wh.HOP_DONG_CALLBACK["phan_hoi_xac_nhan"]["muc"], wh.CHUA_TAI_LIEU)
        self.assertEqual(wh.phan_hoi_xac_nhan(True)[1]["code"], 1)


# ============================================================================
class J_ChotChan(Nen):
    """Chốt chặn cấu trúc của G14."""

    def _nguon(self, ten):
        with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
            return f.read()

    def test_j01_tai_lieu_G14_co_that_va_noi_du_hai_chot_chan(self):
        duong = os.path.join(os.path.dirname(GOC_APP), "docs", "G14_JT_WEBHOOK.md")
        self.assertTrue(os.path.exists(duong), "thiếu docs/G14_JT_WEBHOOK.md")
        with open(duong, encoding="utf-8") as f:
            n = f.read()
        for phai_co in ("BLOCKED", "110", "watermark", "thu_webhook_jt.py"):
            self.assertIn(phai_co, n, f"tài liệu G14 thiếu '{phai_co}'")

    def test_j02_khong_goi_mang_va_khong_mo_LIVE(self):
        n = self._nguon("webhook.py")
        for cam in ("import requests", "import httpx", "urllib.request", "http.client",
                    "socket.socket", "CHO_PHEP_LIVE = True"):
            self.assertNotIn(cam, n, f"webhook.py có '{cam}'")

    def test_j03_hop_dong_callback_khong_duoc_tu_dong_nang_muc(self):
        n = self._nguon("trang_thai_hang.py")
        self.assertIn("NHAP_NHANG", n)
        self.assertIn(("jt", 110), tth.NHAP_NHANG)
        self.assertEqual(tth.NGHIA_DA_CHOT, {}, "có nghĩa được chốt sẵn trong mã nguồn")
        for ma_hang, ma in tth.NHAP_NHANG:
            self.assertIn(ma, tth.JT_MA if ma_hang == "jt" else {}, f"mã nhập nhằng {ma} lạ")

    def test_j04_gateway_da_nghiem_thu_khong_bi_dung_lai(self):
        """W01: `gateway/` là bản G01 đã nghiệm thu. G14 KHÔNG dựng lại nó."""
        for ten in ("server.py", "csdl.py", "xac_thuc.py", "xu_ly.py", "hang_doi.py",
                    "cau_hinh.py", "mo_phong_hang.py"):
            duong = os.path.join(os.path.dirname(GOC_APP), "gateway", ten)
            self.assertTrue(os.path.exists(duong), f"gateway/{ten} biến mất")
        # Gateway có CSDL RIÊNG — không được trỏ vào CSDL nghiệp vụ.
        gc = self._nguon_gw("cau_hinh.py")
        self.assertIn("VIP_GATEWAY_DB", gc)
        self.assertNotIn("hub.db", gc)

    def _nguon_gw(self, ten):
        with open(os.path.join(os.path.dirname(GOC_APP), "gateway", ten), encoding="utf-8") as f:
            return f.read()


# ============================================================================
# G16-A (AG-04) — HỢP ĐỒNG CALLBACK CHỐT LẠI · CHỐT AN TOÀN CỦA HARNESS · TỰ KIỂM BỘ DÒ
# ============================================================================
GOC_DU_AN = os.path.dirname(GOC_APP)
GOC_G16 = os.path.join(GOC_DU_AN, "trien_khai", "g16")
HARNESS_G16 = os.path.join(GOC_G16, "harness_nghiem_thu.py")
CHOT_G16 = os.path.join(GOC_G16, "chot_an_toan.py")

SECRET_LA = "secret-tai-khoan-tenant-khong-ton-tai-g16-55"


def _account_tenant_khong_ton_tai(wh_ma, tenant_id=999999):
    """Tài khoản hãng trỏ vào một tenant KHÔNG có trong bảng `tenants`.

    Dựng bằng kết nối THÔ (`csdl.ket_noi()` — cố ý KHÔNG bật `foreign_keys`) vì `csdl.ghi()`
    sẽ chặn khoá ngoại. Đây là dữ liệu HỎNG có chủ ý: ca thử cần nó để đo đường "tenant không
    giải được thì sự kiện đi đâu".
    """
    ban_ma, duoi = bao_mat.luu_credentials({"apiAccount": "API-LA"},
                                           bao_mat.aad_credentials(tenant_id, "jt"))
    kn = csdl.ket_noi()
    try:
        cur = kn.execute(
            "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
            "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,kich_hoat,tao_luc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (tenant_id, "jt", "jt-tenant-la", "mock", ban_ma, duoi, wh_ma,
             bao_mat.ma_hoa_wh(SECRET_LA, wh_ma), 1, csdl.bay_gio()))
        kn.commit()
        return cur.lastrowid
    finally:
        kn.close()


class K_G16_HopDongVaChotAnToan(Nen):
    """G16-A — hợp đồng callback thành dữ liệu máy đọc được, và các chốt của harness."""

    def test_k01_bao_cao_hop_dong_may_doc_duoc_va_khong_tu_nang_muc(self):
        bc = wh.bao_cao_hop_dong_callback()
        self.assertEqual(bc["muc"], wh.MUC_DOCUMENTED,
                         "mức hợp đồng bị đổi — chưa hề có lượt đối chiếu nào với hãng")
        self.assertIs(bc["xac_minh_voi_hang"], False)
        self.assertIs(bc["phan_hoi_xac_minh"], False)
        self.assertEqual(wh.kiem_hop_dong_khong_tu_nang_muc(), [],
                         "bất biến trung thực của hợp đồng bị vi phạm")
        # ĐỐI CHỨNG DƯƠNG: báo cáo phải có phần BIẾT ĐƯỢC, không phải một danh sách rỗng
        # trông như "đã soát hết".
        self.assertTrue(bc["da_tai_lieu"], "báo cáo không có trường nào đã có tài liệu")
        self.assertIn("than_yeu_cau", bc["da_tai_lieu"])
        self.assertIn("header_bat_buoc", bc["da_tai_lieu"])
        self.assertEqual(bc["so_truong"], len(wh.HOP_DONG_CALLBACK))
        self.assertIn("KHÔNG PHẢI LÀ HỢP ĐỒNG ĐÃ XÁC MINH", bc["canh_bao"])

    def test_k02_nam_cho_ho_Owner_chi_dich_danh_deu_BLOCKED_kem_dung_cai_thieu(self):
        """Năm mục directive 15/10/2026 nêu đích danh — mỗi mục phải nói ĐÚNG cái còn thiếu."""
        can = {
            "khoa_ky_chieu_callback": ("câu 6", "khoá"),
            "chuoi_dem_di_ky": ("câu 7", "chuỗi"),
            "phuong_thuc_http": ("câu 2", "HTTP"),
            "phan_hoi_xac_nhan": ("câu 9", "phản hồi"),
            "chinh_sach_thu_lai": ("câu 9", "thử lại"),
        }
        theo_ten = {b["ten"]: b for b in wh.bao_cao_hop_dong_callback()["blocked"]}
        for ten, (cau_hoi, tu_khoa) in can.items():
            self.assertIn(ten, theo_ten, f"{ten} không nằm trong bảng chặn")
            self.assertEqual(wh.HOP_DONG_CALLBACK[ten]["muc"], wh.CHUA_TAI_LIEU,
                             f"{ten} bị nâng mức mà không có căn cứ từ hãng")
            self.assertIsNone(wh.HOP_DONG_CALLBACK[ten]["gia_tri"],
                              f"{ten} khai giá trị trong khi tài liệu chưa trả lời")
            b = theo_ten[ten]
            for khoa in ("cau_hoi", "thieu", "doan_thi_hong", "dang_chan", "go_khi"):
                self.assertTrue(str(b[khoa]).strip(), f"{ten} thiếu '{khoa}'")
            self.assertIn(cau_hoi, b["cau_hoi"], f"{ten} không trỏ đúng câu hỏi gửi hãng")
            self.assertIn(tu_khoa, b["thieu"] + b["dang_chan"])

    def test_k03_khong_doan_thuat_toan_ky_va_khong_them_so_do_thu_hai(self):
        """Cấm đoán: thuật toán ký vẫn ĐÚNG công thức tài liệu, không có sơ đồ thứ hai."""
        import inspect
        nguon = inspect.getsource(wh.xac_thuc_jt_digest)
        self.assertIn("hashlib.md5", nguon, "công thức tài liệu là md5, không phải thứ khác")
        self.assertIn("base64.b64encode", nguon)
        self.assertNotIn("hmac.new", nguon, "jt_digest KHÔNG phải HMAC — đừng trộn hai sơ đồ")
        self.assertNotIn("sha256", nguon)
        self.assertEqual(sorted(wh.BO_XAC_THUC), ["hub_hmac", "jt_digest"],
                         "một sơ đồ xác thực mới xuất hiện mà không có tài liệu")
        self.assertIn(wh.HOP_DONG_MUC, (wh.MUC_DOCUMENTED, wh.MUC_BLOCKED),
                      "mức hợp đồng vượt DOCUMENTED")
        # ĐỐI CHỨNG DƯƠNG: công thức tài liệu VẪN được chấp nhận (không phải chặn sạch).
        tk = self.row(self.tk_sb)
        biz = biz_jt("MVD-K03", 106, "2026-10-15 08:00:00")
        body = urllib.parse.urlencode({"bizContent": biz}).encode()
        ok, ly_do = wh.xac_thuc_jt_digest(tk, ky_jt(SECRET_SB, biz, "API-1"), body)
        self.assertTrue(ok, ly_do)

    def test_k04_chieu_callback_sandbox_van_BLOCKED_kem_dung_cai_thieu(self):
        b = {x["ten"]: x for x in wh.bao_cao_hop_dong_callback()["blocked"]}
        self.assertIn("sandbox_co_day_callback", b,
                      "chưa biết sandbox có đẩy callback không — phải nằm trong bảng chặn")
        self.assertIn("câu 24", b["sandbox_co_day_callback"]["cau_hoi"])
        gop = json.dumps(b["sandbox_co_day_callback"], ensure_ascii=False)
        for ma in ("V-G09-01", "V-13906-05"):
            self.assertIn(ma, gop, f"thiếu mã việc {ma} trong phần nói cái còn thiếu")
        # Chốt THẬT của mã sản phẩm: hai môi trường dưới `mock` chưa được cấp quyền.
        import adapter_jt
        self.assertFalse(adapter_jt.moi_truong_duoc_chay("sandbox"))
        self.assertFalse(adapter_jt.moi_truong_duoc_chay("production"))

    def test_k05_harness_tu_choi_chay_khi_co_chot_bi_mat_CHOT_AN_TOAN(self):
        """Chạy harness THẬT ở tiến trình con với một chốt bị mở ⇒ phải TỪ CHỐI, không dựng gì."""
        import subprocess
        nen = os.path.join(os.environ["VIP_HUB_DATA"], "g16-tu-kiem-tu-choi")
        os.makedirs(nen, exist_ok=True)
        env = dict(os.environ, VIP_HUB_DATA=nen, VIP_G16_CHO_PHEP_GOI_HANG="1")
        p = subprocess.run([sys.executable, HARNESS_G16], capture_output=True, text=True,
                           env=env, timeout=300, cwd=GOC_DU_AN)
        self.assertEqual(p.returncode, 4,
                         f"harness KHÔNG từ chối khi chốt 'cho phép gọi hãng' bị mở.\n"
                         f"stdout:\n{p.stdout[-800:]}\nstderr:\n{p.stderr[-400:]}")
        self.assertIn("TỪ CHỐI CHẠY", p.stdout)
        self.assertIn("V-G09-01", p.stdout)
        self.assertFalse(os.path.exists(os.path.join(nen, "hub.db")),
                         "harness đã dựng CSDL dù phải từ chối trước khi chạm gì")

    def test_k06_tu_kiem_bo_do_chot_an_toan_bat_DUNG_chot(self):
        import subprocess
        p = subprocess.run([sys.executable, CHOT_G16, "--tu-kiem"], capture_output=True,
                           text=True, timeout=300, cwd=GOC_DU_AN)
        self.assertEqual(p.returncode, 0, f"bộ dò chốt an toàn TỰ KIỂM HỎNG:\n{p.stdout[-1500:]}")
        self.assertIn("TỰ KIỂM:", p.stdout)
        self.assertIn("0 hỏng", p.stdout)
        # ĐỐI CHỨNG DƯƠNG trong chính bộ tự kiểm: ca A (đủ chốt) phải ĐI QUA, và có ít nhất
        # một ca hỏng được bắt bởi ĐÚNG chốt — nếu không thì bộ dò chỉ đang từ chối mọi thứ.
        self.assertIn("[A] cấu hình ĐỦ CHỐT", p.stdout)
        self.assertIn("bắt đúng chốt", p.stdout)
        # Và bộ dò phải TỪ CHỐI khi nền là dữ liệu THẬT — kiểm NGAY TRONG tiến trình này,
        # không spawn harness trên dữ liệu thật (không có lượt nào được phép chạm vào đó).
        sys.path.insert(0, GOC_G16)
        import chot_an_toan
        ly_do = chot_an_toan.ly_do_tu_choi(os.path.join(GOC_APP, "du-lieu"),
                                           goc_url="http://127.0.0.1:9", so_dang_ky={}, env={})
        self.assertTrue(any("dữ liệu THẬT" in x for x in ly_do),
                        f"bộ dò không nhận ra dữ liệu thật: {ly_do}")

    def test_k07_tu_kiem_BO_DO_THU_bat_duoc_ca_CO_Y_HONG(self):
        """Chạy một ca CỐ Ý HỎNG trong tiến trình con; bộ dò phải THẤY nó hỏng.

        Thiếu ca này thì "bộ thử xanh" không chứng minh gì: một bộ thử bắt hết lỗi rồi thoát 0
        mà không chạy ca nào cũng "xanh". Kèm ĐỐI CHỨNG DƯƠNG (ca đạt ⇒ thoát 0 + có `OK`).
        """
        import subprocess
        goc = os.environ["VIP_HUB_DATA"]
        hong = os.path.join(goc, "tu_kiem_hong_g16.py")
        with open(hong, "w", encoding="utf-8") as f:
            f.write("import unittest\n"
                    "class C(unittest.TestCase):\n"
                    "    def test_co_y_hong(self):\n"
                    "        self.assertEqual(1, 2, 'ca CO Y HONG de kiem bo do')\n"
                    "if __name__ == '__main__':\n"
                    "    unittest.main(verbosity=2)\n")
        p = subprocess.run([sys.executable, hong], capture_output=True, text=True, timeout=120)
        # `unittest` in bảng tổng kết ra STDERR, không phải stdout — gộp hai luồng rồi mới phán.
        # (Bản đầu của ca này chỉ đọc stdout nên nó HỎNG vì lý do của chính nó, không phải của
        # hệ: đúng bài học "thứ dùng để kiểm chứng phải được kiểm trước khi tin".)
        o = p.stdout + p.stderr
        self.assertNotEqual(p.returncode, 0, "bộ dò KHÔNG thấy ca cố ý hỏng")
        self.assertNotIn("\nOK", o, "bộ dò in OK cho một lượt có ca hỏng")
        self.assertIn("FAILED", o)
        # ĐỐI CHỨNG DƯƠNG: cùng khuôn, ca ĐẠT ⇒ thoát 0 và CÓ `OK`.
        lanh = os.path.join(goc, "tu_kiem_lanh_g16.py")
        with open(lanh, "w", encoding="utf-8") as f:
            f.write("import unittest\n"
                    "class C(unittest.TestCase):\n"
                    "    def test_dat(self):\n"
                    "        self.assertEqual(1, 1)\n"
                    "if __name__ == '__main__':\n"
                    "    unittest.main(verbosity=2)\n")
        p2 = subprocess.run([sys.executable, lanh], capture_output=True, text=True, timeout=120)
        o2 = p2.stdout + p2.stderr
        self.assertEqual(p2.returncode, 0, o2[-400:])
        self.assertIn("OK", o2)

    def test_k08_tenant_khong_ton_tai_thi_khong_cham_don_cua_ai(self):
        """Tài khoản hãng trỏ vào tenant KHÔNG có thật: sự kiện đi vào `khong_khop`, 0 dòng đơn."""
        d_a = _don(self.ta, self.uid, self.tk_a, "MVD-K08", "cho_lay", 1)
        tk_la = _account_tenant_khong_ton_tai(f"wh-g16-la-{self.dem('carrier_accounts')}")
        truoc = self.tt_don(d_a)
        truoc_don = self.dem("don_hang")
        sk_id, trung, _ = self.gui(tk_la, body_hub("dang_giao", "MVD-K08", "E-K08"),
                                   secret=SECRET_LA)
        self.assertFalse(trung)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "khong_khop",
                         "sự kiện của tenant không tồn tại lại được ÁP vào đâu đó")
        self.assertEqual(self.tt_don(d_a), truoc, "đơn của tenant KHÁC bị đổi trạng thái")
        self.assertEqual(self.dem("don_hang"), truoc_don)
        self.assertGreaterEqual(self.audit_co("webhook_khong_khop_don"), 1)
        # ĐỐI CHỨNG DƯƠNG: cùng payload ấy, qua tài khoản ĐÚNG tenant, thì ÁP được — nếu không
        # thì "khong_khop" ở trên không chứng minh được gì (payload có thể hỏng vì lý do khác).
        sk2, _, _ = self.gui(self.tk_a, body_hub("dang_giao", "MVD-K08", "E-K08"),
                             headers=None, secret=SECRET_A)
        self.assertEqual(self.sk(sk2)["trang_thai"], "xong")
        self.assertEqual(self.tt_don(d_a)[0], "dang_giao")

    def test_k09_tenant_rong_thi_DLQ_chu_khong_no(self):
        """Account mất tenant (dữ liệu hỏng): `tenant_tu_account` ném LoiVinhVien ⇒ DLQ, không nổ."""
        with self.assertRaises(wh.LoiVinhVien):
            wh.tenant_tu_account(None, 123)
        with self.assertRaises(wh.LoiVinhVien):
            wh.tenant_tu_account("", 123)
        tk_hong = _account(self.ta, "jt", f"wh-g16-hong-{self.dem('carrier_accounts')}", SECRET_A)
        b = body_hub("dang_giao", "MVD-K09", "E-K09")
        # Nhận sự kiện nhưng CHƯA xử lý: nếu xử lý trước rồi mới bẻ tenant thì sự kiện đã ở
        # trạng thái cuối và `_nhan_viec` sẽ bỏ qua — ca thử sẽ "đạt" mà không đo gì.
        tk_row = self.row(tk_hong)
        hd = ky_hub(SECRET_A, b)
        self.assertTrue(wh.kiem_chu_ky(tk_row, hd, b))
        sk_id, trung = wh.nhan_su_kien(tk_row, b, hd)
        self.assertFalse(trung)
        # Bẻ tenant của account thành chuỗi rỗng bằng kết nối THÔ (cột NOT NULL chặn NULL,
        # nhưng chuỗi rỗng thì lọt — và đó đúng là dữ liệu hỏng cần canh).
        kn = csdl.ket_noi()
        try:
            kn.execute("UPDATE carrier_accounts SET tenant_id='' WHERE id=?", (tk_hong,))
            kn.commit()
        finally:
            kn.close()
        wh._chay_mot(sk_id)
        self.assertEqual(self.sk(sk_id)["trang_thai"], "dlq",
                         "lỗi vĩnh viễn không được đẩy vào DLQ — nó sẽ thử lại mãi")
        self.assertIn("vinh vien", self.sk(sk_id)["loi_cuoi"] or "")
        self.assertGreaterEqual(self.audit_co("webhook_dlq"), 1)

    def test_k10_bang_phu_muc_yeu_cau_G16_deu_co_ca_canh(self):
        """Bảng phủ: MỌI hành vi directive G16 yêu cầu phải có một ca THẬT canh nó.

        Không phải phép kiểm hình thức: nó đọc danh sách ca mà bộ chạy THẬT SỰ nạp, nên xoá
        hay đổi tên một ca canh là ca này hỏng ngay — thay vì im lặng mất phạm vi.
        """
        mod = sys.modules[__name__]

        def _gom(s):
            for x in s:
                if isinstance(x, unittest.TestSuite):
                    for y in _gom(x):
                        yield y
                else:
                    yield x

        co = {t.id().rsplit(".", 1)[-1]
              for t in _gom(unittest.TestLoader().loadTestsFromModule(mod))}
        can = {
            "chữ ký sai": "test_b01_chu_ky_sai_thi_khong_nhan_va_co_audit",
            "chữ ký sai qua HTTP": "test_i03_chu_ky_sai_tra_401_va_KHONG_luu_su_kien",
            "callback trùng": "test_c03_gui_lai_y_nguyen_la_idempotent",
            "chống trùng ở tầng CSDL": "test_c02_CSDL_chan_that_khong_phai_ma_chan",
            "tài khoản hãng không tồn tại": "test_i02_webhook_ma_khong_ton_tai_tra_404",
            "tenant không tồn tại": "test_k08_tenant_khong_ton_tai_thi_khong_cham_don_cua_ai",
            "tenant rỗng ⇒ DLQ": "test_k09_tenant_rong_thi_DLQ_chu_khong_no",
            "chéo tenant": "test_d04_CHÉO_TENANT_callback_cua_A_khong_duoc_cham_don_cua_B",
            "sự kiện đến muộn": "test_e02_moc_hang_chan_ban_tin_CU_that_su",
            "mã lạ ⇒ NEEDS_REVIEW": "test_f04_ma_la_thi_NEEDS_REVIEW_khong_doan_nghia",
            "mã 110 ⇒ không hoàn tất": "test_f01_110_khong_doi_trang_thai_va_duoc_danh_dau_can_soat",
            "110/mã lạ không chạm COD": "test_f06_W04_110_va_ma_la_KHONG_duoc_dung_toi_COD",
            "retry": "test_g01_loi_tam_thoi_thi_thu_lai_roi_vao_DLQ",
            "DLQ lỗi vĩnh viễn": "test_g02_loi_vinh_vien_vao_DLQ_ngay_khong_dot_luot_thu_nao",
            "replay có phép + chéo tenant": "test_g04_replay_duoc_phep_theo_tenant_va_co_audit",
            "replay có trần": "test_g05_replay_co_tran",
            "quyền replay": "test_g07_quyen_replay_do_tang_HTTP_kiem",
            "đồng bộ hành trình": "test_h02_khong_khop_va_can_soat_va_DLQ_deu_hien_ra",
            "đồng bộ hành trình (đơn treo)": "test_h06_don_treo_va_don_khong_su_kien",
            "hợp đồng callback": "test_k01_bao_cao_hop_dong_may_doc_duoc_va_khong_tu_nang_muc",
        }
        thieu = {nhan: ten for nhan, ten in can.items() if ten not in co}
        self.assertEqual(thieu, {}, f"thiếu ca canh cho: {thieu}")
        # ĐỐI CHỨNG DƯƠNG: bảng phủ phải THẬT SỰ đọc được danh sách ca, không phải rỗng.
        self.assertGreater(len(co), 50, "không đọc được danh sách ca — bảng phủ vô nghĩa")


if __name__ == "__main__":
    print(f"CSDL thử G14: {os.environ['VIP_HUB_DATA']}")
    unittest.main(verbosity=2)
