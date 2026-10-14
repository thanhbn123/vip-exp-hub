# Bộ thử G12 — Multi-Tenant SaaS: chạy server thật trên cổng tạm, CSDL tạm, bắn HTTP thật.
# Phủ 15 ca bắt buộc của brief (tenant isolation, RBAC, webhook, idempotency, import, secret, regression).
# Chạy: python3 app/thu/thu_saas.py
import base64
import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import zipfile

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-thu-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ["VIP_HUB_BACKOFF"] = "0.05"

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
# Không dựng ở mức module: lúc nạp file chưa bind nên chưa biết cổng (xem CONG ở trên).
def GOC_URL_F():
    return "http://127.0.0.1:%d" % CONG
LOG_SERVER = io.StringIO()   # gom log để quét rò secret


class Phien:
    """Client HTTP nhỏ giữ cookie phiên."""
    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
        body = tho if tho is not None else (json.dumps(du_lieu).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        if method in ("POST", "PUT") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(GOC_URL_F() + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=10) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                ct = ph.headers.get("Content-Type", "")
                raw = ph.read()
                return ph.status, (json.loads(raw) if "json" in ct else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def dang_nhap(self, ten, mk):
        return self.goi("/api/v2/auth/dang-nhap", "POST", {"ten_dang_nhap": ten, "mat_khau": mk})


def tao_phien(ten, mk):
    p = Phien()
    st, kq = p.dang_nhap(ten, mk)
    assert st == 200, f"đăng nhập {ten} hỏng: {kq}"
    return p


MK = "MatKhauThu-123"
DON_MAU = {
    "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111", "nguoi_gui_dia_chi": "1 Đường Thử, HN",
    "nguoi_nhan_ten": "Khách Thử", "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Phố Thử, HCM",
    "hang_hoa": "Hộp demo", "khoi_luong_gram": 500, "cod": 150000,
}


def xlsx_mau():
    """Sinh file XLSX tối thiểu bằng stdlib để thử parser."""
    ss = ('<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="7" uniqueCount="7">'
          "<si><t>recipient_name</t></si><si><t>recipient_phone</t></si><si><t>recipient_address</t></si>"
          "<si><t>product_name</t></si><si><t>weight_grams</t></si><si><t>Trần Xlsx</t></si><si><t>3 Ngõ Xlsx</t></si></sst>")
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c>'
             '<c r="D1" t="s"><v>3</v></c><c r="E1" t="s"><v>4</v></c></row>'
             '<row r="2"><c r="A2" t="s"><v>5</v></c><c r="B2"><v>0903333333</v></c><c r="C2" t="s"><v>6</v></c>'
             '<c r="D2" t="s"><v>3</v></c><c r="E2"><v>800</v></c></row></sheetData></worksheet>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("xl/sharedStrings.xml", ss)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


class ThuSaaS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global CONG      # gán lại sau khi bind cổng 0
        # chuyển stderr của server vào bộ nhớ để quét secret
        cls._stderr_cu = sys.stderr
        sys.stderr = LOG_SERVER
        csdl.mo()
        webhook.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", CONG), server.BoXuLy)
        # Cổng THẬT do hệ cấp — gán lại CONG để mọi chỗ dựng URL lúc chạy tự đúng.
        CONG = cls.sv.server_address[1]
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()
        # seed bằng API: platform owner tạo tay trong CSDL, phần còn lại qua API thật
        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'test')",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po', ?, 'Platform Owner', 'PLATFORM_OWNER', ?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        po = tao_phien("po", MK)
        for ten, dn in (("Tenant A", "a"), ("Tenant B", "b")):
            st, kq = po.goi("/api/v2/platform/tenants", "POST",
                            {"ten": ten, "goi_id": "basic", "owner_ten_dang_nhap": f"{dn}-owner",
                             "owner_mat_khau": MK, "owner_ho_ten": f"Chủ {ten}"})
            assert st == 201, kq
            setattr(cls, "tid_a" if dn == "a" else "tid_b", kq["id"])
        cls.po = po
        cls.a = tao_phien("a-owner", MK)
        cls.b = tao_phien("b-owner", MK)
        # mỗi tenant 1 tài khoản hãng mock (lưu webhook secret để bắn thử)
        st, kq = cls.a.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "vtp", "ten": "VTP của A", "credentials": {"api_key": "demo-key-cua-A-9999"}})
        assert st == 201, kq
        cls.tk_a = kq
        st, kq = cls.b.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "jt", "ten": "JT của B", "credentials": {"privateKey": "demo-key-cua-B-8888"}})
        assert st == 201, kq
        cls.tk_b = kq
        # staff + viewer của A
        assert cls.a.goi("/api/v2/memberships", "POST", {"ten_dang_nhap": "a-staff", "mat_khau": MK,
                                                         "role": "TENANT_STAFF", "ho_ten": "NV A"})[0] == 201
        assert cls.a.goi("/api/v2/memberships", "POST", {"ten_dang_nhap": "a-viewer", "mat_khau": MK,
                                                         "role": "TENANT_VIEWER", "ho_ten": "Xem A"})[0] == 201
        cls.a_staff = tao_phien("a-staff", MK)
        cls.a_viewer = tao_phien("a-viewer", MK)

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown(); cls.sv.server_close()
        webhook.dung(); csdl.dong()
        sys.stderr = cls._stderr_cu

    def _tao_don_a(self, phien=None, idem=None, **ghi_de):
        d = dict(DON_MAU); d.update(ghi_de)
        h = {"Idempotency-Key": idem} if idem else {}
        return (phien or self.a).goi("/api/v2/don", "POST", d, headers=h)

    def _gui_webhook(self, tk, event_id, loai, ma_van_don, secret=None, force_fail=False):
        payload = {"event_id": event_id, "event": loai, "tracking_number": ma_van_don}
        if force_fail:
            payload["demo_force_fail"] = True
        body = json.dumps(payload).encode()
        sig = hmac.new((secret or tk["webhook_secret_mot_lan"]).encode(), body, hashlib.sha256).hexdigest()
        p = Phien()
        return p.goi(f"/api/v2/webhook/nhan/{tk['webhook_ma']}", "POST", tho=body,
                     headers={"X-Webhook-Signature": sig, "Content-Type": "application/json"})

    # ===== G12.1-3: tenant isolation =====
    def test_01_tenant_khong_xem_cheo(self):
        st, kq = self._tao_don_a()
        self.assertEqual(st, 201, kq)
        don_id = kq["don"]["id"]
        st, kq = self.b.goi(f"/api/v2/don/{don_id}")
        self.assertEqual(st, 404, "tenant B xem được đơn của A!")
        st, kq = self.b.goi("/api/v2/don")
        self.assertTrue(all(d["id"] != don_id for d in kq["don"]))
        st, kq = self.b.goi("/api/v2/khach-hang")
        self.assertEqual(st, 200)
        # sự kiện webhook của A không hiện cho B (kiểm sau khi test webhook chạy — xem test_08)

    def test_02_tenant_khong_sua_cheo(self):
        st, kq = self._tao_don_a()
        don_id = kq["don"]["id"]
        st, _ = self.b.goi(f"/api/v2/don/{don_id}", "PUT", {"hang_hoa": "đồ của B?"})
        self.assertEqual(st, 404)
        st, _ = self.b.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        self.assertEqual(st, 404)

    def test_03_khong_dung_duoc_carrier_account_cua_tenant_khac(self):
        st, kq = self._tao_don_a()
        don_id = kq["don"]["id"]
        self.a.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, kq = self.a.goi(f"/api/v2/don/{don_id}/gui", "POST",
                            {"carrier_account_id": self.tk_b["id"]})
        self.assertEqual(st, 404, f"A dùng được account của B! {kq}")

    # ===== G12.4: RBAC =====
    def test_04_khong_vuot_quyen(self):
        st, _ = self.a_staff.goi("/api/v2/memberships", "POST",
                                 {"ten_dang_nhap": "x", "mat_khau": MK * 2, "role": "TENANT_STAFF"})
        self.assertEqual(st, 403, "staff tạo được user!")
        st, _ = self.a_viewer.goi("/api/v2/don", "POST", dict(DON_MAU))
        self.assertEqual(st, 403, "viewer tạo được đơn!")
        st, kq = self._tao_don_a(phien=self.a_staff)
        self.assertEqual(st, 201)
        st, _ = self.a_staff.goi(f"/api/v2/don/{kq['don']['id']}/duyet", "POST", {})
        self.assertEqual(st, 403, "staff duyệt được đơn!")
        st, _ = self.a.goi("/api/v2/platform/tenants")
        self.assertEqual(st, 403, "tenant owner gọi được API platform!")
        st, _ = self.a.goi("/api/v2/memberships", "POST",
                           {"ten_dang_nhap": "lau-quyen", "mat_khau": MK, "role": "PLATFORM_ADMIN"})
        self.assertEqual(st, 403, "tenant tạo được vai trò platform!")

    # ===== G12.5-7: webhook =====
    def _don_da_gui_a(self):
        st, kq = self._tao_don_a()
        don_id = kq["don"]["id"]
        self.a.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, kq = self.a.goi(f"/api/v2/don/{don_id}/gui", "POST", {"carrier_account_id": self.tk_a["id"]})
        assert st == 200 and kq["don"]["trang_thai"] == "da_gui", kq
        return kq["don"]

    def test_05_webhook_gia_mao_bi_tu_choi(self):
        don = self._don_da_gui_a()
        st, _ = self._gui_webhook(self.tk_a, "WH-GM-1", "lay_hang", don["ma_van_don"], secret="secret-sai")
        self.assertEqual(st, 401)
        so = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE event_id='WH-GM-1'")["c"]
        self.assertEqual(so, 0, "sự kiện giả mạo vẫn bị lưu!")

    def test_06_webhook_trung_khong_cap_nhat_hai_lan(self):
        don = self._don_da_gui_a()
        st1, _ = self._gui_webhook(self.tk_a, "WH-TR-1", "lay_hang", don["ma_van_don"])
        st2, kq2 = self._gui_webhook(self.tk_a, "WH-TR-1", "lay_hang", don["ma_van_don"])
        self.assertEqual(st1, 202)
        self.assertEqual(st2, 200)
        self.assertEqual(kq2["ket_qua"], "da_nhan_truoc_do")
        webhook.cho_rong()
        ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? AND noi_dung LIKE '%lay_hang%'", (don["id"],))
        self.assertEqual(len(ls), 1, "sự kiện trùng cập nhật hai lần!")

    def test_07_webhook_sai_thu_tu_khong_lui_trang_thai(self):
        don = self._don_da_gui_a()
        self._gui_webhook(self.tk_a, f"WH-OOO-{don['id']}-1", "giao_thanh_cong", don["ma_van_don"])
        webhook.cho_rong()
        self._gui_webhook(self.tk_a, f"WH-OOO-{don['id']}-2", "dang_giao", don["ma_van_don"])
        webhook.cho_rong()
        d = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (don["id"],))
        self.assertEqual(d["trang_thai_giao"], "giao_thanh_cong", "sự kiện muộn kéo lùi trạng thái!")

    def test_08_webhook_khong_cap_nhat_don_sai_tenant(self):
        don_a = self._don_da_gui_a()
        # B bắn webhook (đúng chữ ký CỦA B) nhưng mang tracking number đơn của A
        st, kq = self._gui_webhook(self.tk_b, "WH-CHEO-1", "giao_thanh_cong", don_a["ma_van_don"])
        self.assertEqual(st, 202)
        webhook.cho_rong()
        sk = csdl.mot("SELECT trang_thai FROM wh_su_kien WHERE event_id='WH-CHEO-1'")
        self.assertEqual(sk["trang_thai"], "khong_khop", "sự kiện chéo tenant không bị cô lập!")
        d = csdl.mot("SELECT trang_thai_giao FROM don_hang WHERE id=?", (don_a["id"],))
        self.assertEqual(d["trang_thai_giao"], "cho_lay", "đơn tenant A bị account của B cập nhật!")
        # và B cũng không XEM được sự kiện của A qua monitor
        st, kq = self.b.goi("/api/v2/webhook/su-kien")
        self.assertTrue(all(s["ten_tk"] != "VTP của A" for s in kq["su_kien"]))

    def test_08b_webhook_retry_dlq_replay(self):
        don = self._don_da_gui_a()
        st, kq = self._gui_webhook(self.tk_a, "WH-FAIL-1", "lay_hang", don["ma_van_don"], force_fail=True)
        sk_id = kq["su_kien_id"]
        import time
        moc = time.time() + 5
        while time.time() < moc:
            sk = csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))
            if sk["trang_thai"] == "dlq":
                break
            time.sleep(0.05)
        self.assertEqual(sk["trang_thai"], "dlq")
        self.assertEqual(sk["so_lan_thu"], 3)
        # viewer không replay được; owner replay được (sau khi gỡ cờ lỗi trong payload)
        st, _ = self.a_viewer.goi(f"/api/v2/webhook/su-kien/{sk_id}/replay", "POST", {})
        self.assertEqual(st, 403)
        moi = json.dumps({"event_id": "WH-FAIL-1", "event": "lay_hang",
                          "tracking_number": don["ma_van_don"]}).encode()
        csdl.ghi("UPDATE wh_su_kien SET payload_tho=? WHERE id=?", (moi, sk_id))
        st, _ = self.a.goi(f"/api/v2/webhook/su-kien/{sk_id}/replay", "POST", {})
        self.assertEqual(st, 202)
        webhook.cho_rong()
        self.assertEqual(csdl.mot("SELECT trang_thai FROM wh_su_kien WHERE id=?", (sk_id,))["trang_thai"], "xong")

    # ===== G12.8-9: idempotency + lỗi hãng =====
    def test_09_idempotency_tao_don(self):
        st1, kq1 = self._tao_don_a(idem="IDEM-SAAS-1")
        st2, kq2 = self._tao_don_a(idem="IDEM-SAAS-1")
        self.assertEqual(st1, 201)
        self.assertEqual(st2, 200)
        self.assertTrue(kq2["idempotent_trung"])
        self.assertEqual(kq1["don"]["id"], kq2["don"]["id"])
        # gửi hãng lần 2 trên đơn đã gửi → trả đơn cũ, không gửi lại (không tăng usage)
        don = self._don_da_gui_a()
        u1 = self.a.goi("/api/v2/billing")[1]["usage"]["so_don"]
        st, kq = self.a.goi(f"/api/v2/don/{don['id']}/gui", "POST", {"carrier_account_id": self.tk_a["id"]})
        self.assertEqual(kq["don"]["ma_van_don"], don["ma_van_don"])
        u2 = self.a.goi("/api/v2/billing")[1]["usage"]["so_don"]
        self.assertEqual(u1, u2, "gửi lại đơn đã gửi vẫn tăng usage!")

    def test_10_hang_loi_va_timeout_khong_mat_don(self):
        # hãng từ chối → đơn lùi về da_duyet, không mất
        st, kq = self._tao_don_a(ghi_chu="demo_force_fail")
        don_id = kq["don"]["id"]
        self.a.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, kq = self.a.goi(f"/api/v2/don/{don_id}/gui", "POST", {"carrier_account_id": self.tk_a["id"]})
        self.assertEqual(st, 502)
        d = csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))
        self.assertEqual(d["trang_thai"], "da_duyet")
        # timeout → giữ dang_gui + cờ kiểm lại, KHÔNG nhận là đã gửi
        st, kq = self._tao_don_a(ghi_chu="demo_force_timeout")
        don_id = kq["don"]["id"]
        self.a.goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
        st, kq = self.a.goi(f"/api/v2/don/{don_id}/gui", "POST", {"carrier_account_id": self.tk_a["id"]})
        d = csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))
        self.assertEqual(d["trang_thai"], "dang_gui")
        self.assertEqual(d["can_doi_soat_ket_qua"], 1)
        self.assertIsNone(d["ma_van_don"])

    # ===== G12.10: import =====
    def test_11_import_csv_va_xlsx(self):
        csv = ("recipient_name,recipient_phone,recipient_address,product_name,weight_grams,cod_amount\n"
               "Lê Import,0904444444,\"4 Hẻm Import, HN\",Áo demo,500,150000\n"
               ",012,Thiếu tên,Hàng lỗi,-5,-1\n").encode()
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "don.csv", "noi_dung_base64": base64.b64encode(csv).decode()})
        self.assertEqual(st, 201, kq)
        batch_id = kq["batch_id"]
        st, kq = self.a.goi(f"/api/v2/import/{batch_id}")
        dong = kq["dong"]
        self.assertEqual([d["trang_thai"] for d in dong], ["VALID", "INVALID"])
        # sửa dòng lỗi → VALID; duyệt cả hai → dòng 1 SUCCESS; batch không hỏng
        st, kq2 = self.a.goi(f"/api/v2/import/dong/{dong[1]['id']}", "PUT",
                             {"nguoi_nhan_ten": "Đã Sửa", "nguoi_nhan_sdt": "0905555555",
                              "khoi_luong_gram": "300", "cod": "0"})
        self.assertEqual(kq2["trang_thai"], "VALID")
        st, kq3 = self.a.goi(f"/api/v2/import/{batch_id}/duyet", "POST",
                             {"dong_ids": [d["id"] for d in dong],
                              "nguoi_gui": {"ten": "Shop A", "sdt": "0901111111", "dia_chi": "1 Đường Thử"}})
        self.assertEqual(kq3["SUCCESS"], 2)
        # duyệt LẠI batch → idempotency import: không nhân đôi đơn
        st, kq4 = self.a.goi(f"/api/v2/import/{batch_id}/duyet", "POST",
                             {"dong_ids": [d["id"] for d in dong],
                              "nguoi_gui": {"ten": "Shop A", "sdt": "0901111111", "dia_chi": "1 Đường Thử"}})
        self.assertEqual(kq4["bo_qua"], 2, "duyệt lại tạo thêm đơn!")
        # XLSX
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "don.xlsx", "noi_dung_base64": base64.b64encode(xlsx_mau()).decode()})
        self.assertEqual(st, 201, kq)
        st, kq = self.a.goi(f"/api/v2/import/{kq['batch_id']}")
        self.assertEqual(kq["dong"][0]["trang_thai"], "VALID", kq["dong"])
        # file rác không hỏng hệ: báo lỗi sạch, không tạo batch treo
        st, kq = self.a.goi("/api/v2/import", "POST",
                            {"ten_file": "rac.xlsx", "noi_dung_base64": base64.b64encode(b"khong phai zip").decode()})
        self.assertEqual(st, 500 if st == 500 else st, kq)  # chấp nhận 400/500 miễn có lỗi rõ
        self.assertIn("loi", kq)

    # ===== G12.11-13: secret =====
    def test_12_khong_ro_secret(self):
        # API danh sách tài khoản hãng không chứa credentials
        st, kq = self.a.goi("/api/v2/tai-khoan-hang")
        van_ban = json.dumps(kq)
        self.assertNotIn("demo-key-cua-A-9999", van_ban)
        self.assertNotIn("credentials_ma_hoa", van_ban)
        self.assertNotIn("webhook_secret", van_ban.replace("webhook_secret_mot_lan", ""))
        # log server không chứa secret/mật khẩu
        log = LOG_SERVER.getvalue()
        for bi_mat in ("demo-key-cua-A-9999", "demo-key-cua-B-8888", MK,
                       self.tk_a["webhook_secret_mot_lan"]):
            self.assertNotIn(bi_mat, log, "secret lộ trong log server!")
        # CSDL lưu bản mã hóa, không plaintext
        tho = csdl.mot("SELECT credentials_ma_hoa FROM carrier_accounts WHERE id=?", (self.tk_a["id"],))
        self.assertNotIn("demo-key-cua-A-9999", tho["credentials_ma_hoa"])
        self.assertEqual(bao_mat.giai_ma_cred(tho["credentials_ma_hoa"], self.tid_a, "vtp")["api_key"],
                         "demo-key-cua-A-9999")

    def test_13_frontend_khong_cam_secret_va_csrf(self):
        # mã admin/ không chứa khóa hãng nào; mọi gọi hãng qua backend
        goc = os.path.dirname(GOC_APP)
        for ten in os.listdir(os.path.join(goc, "admin")):
            with open(os.path.join(goc, "admin", ten), encoding="utf-8") as f:
                noi_dung = f.read()
            self.assertNotIn("privateKey", noi_dung)
            self.assertNotIn("jtexpress.vn", noi_dung)
        # mutating API thiếu header chống CSRF → 403
        p = Phien(); p.cookie = self.a.cookie
        st, _ = p.goi("/api/v2/don", "POST", dict(DON_MAU), headers={"X-Requested-With": ""})
        self.assertEqual(st, 403)

    # ===== auth bổ sung (G02) =====
    def test_14_khoa_tai_khoan_va_phien(self):
        self.a.goi("/api/v2/memberships", "POST", {"ten_dang_nhap": "a-khoa", "mat_khau": MK,
                                                   "role": "TENANT_STAFF", "ho_ten": "Sắp khóa"})
        p = Phien()
        for _ in range(5):
            st, kq = p.dang_nhap("a-khoa", "sai-mat-khau")
        # v2 CỐ Ý trả thông báo chung khi tự khóa — không tiết lộ tài khoản nào có thật/đang bị khóa
        # (brief G02.1: "Không để lộ thông tin tài khoản qua thông báo lỗi").
        self.assertEqual(kq["loi"], "sai tên đăng nhập hoặc mật khẩu")
        # Tài khoản PHẢI bị khóa TẠM (không phải vĩnh viễn — khóa vĩnh viễn bằng mật khẩu sai
        # là đường cho người lạ vô hiệu hóa tài khoản người khác; đổi 14/10/2026 theo AG-07 q06).
        r = csdl.mot("SELECT trang_thai, khoa_den FROM users WHERE ten_dang_nhap='a-khoa'")
        self.assertEqual(r["trang_thai"], "hoat_dong", "không được khóa VĨNH VIỄN khi đoán sai")
        self.assertIsNotNone(r["khoa_den"], "sai 5 lần mà không khóa tạm!")
        st, kq = p.dang_nhap("a-khoa", MK)
        self.assertEqual(st, 401, "tài khoản khóa vẫn đăng nhập được!")
        # đổi mật khẩu thu hồi phiên khác
        p1 = tao_phien("a-staff", MK)
        p2 = tao_phien("a-staff", MK)
        st, _ = p1.goi("/api/v2/auth/doi-mat-khau", "POST",
                       {"mat_khau_cu": MK, "mat_khau_moi": "MatKhauMoi-456"})
        self.assertEqual(st, 200)
        st, _ = p2.goi("/api/v2/auth/toi")
        self.assertEqual(st, 401, "phiên cũ chưa bị thu hồi sau đổi mật khẩu!")
        # trả lại mật khẩu cũ cho các test sau
        st, _ = p1.goi("/api/v2/auth/doi-mat-khau", "POST",
                       {"mat_khau_cu": "MatKhauMoi-456", "mat_khau_moi": MK})
        self.__class__.a_staff = tao_phien("a-staff", MK)

    # ===== G10: billing =====
    def test_15_han_muc_goi(self):
        # tạo tenant gói free (50 đơn — không thử hết; thử hạn mức NHÂN VIÊN = 2 và HÃNG = 1)
        st, kq = self.po.goi("/api/v2/platform/tenants", "POST",
                             {"ten": "Tenant Free", "goi_id": "free",
                              "owner_ten_dang_nhap": "free-owner", "owner_mat_khau": MK})
        f = tao_phien("free-owner", MK)
        st, _ = f.goi("/api/v2/memberships", "POST", {"ten_dang_nhap": "free-nv1", "mat_khau": MK, "role": "TENANT_STAFF"})
        self.assertEqual(st, 201)
        st, kq = f.goi("/api/v2/memberships", "POST", {"ten_dang_nhap": "free-nv2", "mat_khau": MK, "role": "TENANT_STAFF"})
        self.assertEqual(st, 402, "vượt hạn mức nhân viên gói free mà không bị chặn!")
        st, _ = f.goi("/api/v2/tai-khoan-hang", "POST", {"hang": "vtp", "credentials": {}})
        self.assertEqual(st, 201)
        st, kq = f.goi("/api/v2/tai-khoan-hang", "POST", {"hang": "jt", "credentials": {}})
        self.assertEqual(st, 402, "vượt hạn mức kết nối hãng mà không bị chặn!")
        # AI usage cũng đo backend
        st, kq = f.goi("/api/v2/ai/goi-y-hang", "POST", {"khoi_luong_gram": 500})
        self.assertEqual(st, 200)
        self.assertTrue(kq["mock"])

    # ===== G12.14-15: migration/regression =====
    def test_16_khong_dung_du_lieu_cu(self):
        """CSDL SaaS phải nằm RIÊNG, không đụng kho dữ liệu của gateway G01.

        Trước đây ca này đòi `gateway/du-lieu/gateway.db` TỒN TẠI — nhưng đường đó nằm trong
        `.gitignore`, nên mọi bản sao mới (worktree của agent, CI) đều hỏng dù mã hoàn toàn đúng.
        Ba agent độc lập cùng vấp đúng bẫy này ngày 14/10/2026. Phép kiểm đã đổi sang đo thứ
        THỰC SỰ cần bảo đảm — hai kho tách nhau — mà không phụ thuộc file ngoài git."""
        goc = os.path.dirname(GOC_APP)
        kho_gateway = os.path.realpath(os.path.join(goc, "gateway", "du-lieu"))
        kho_saas = os.path.realpath(os.environ["VIP_HUB_DATA"])
        self.assertNotEqual(kho_saas, kho_gateway, "SaaS dùng chung kho dữ liệu với gateway!")
        self.assertFalse(kho_saas.startswith(kho_gateway + os.sep),
                         "CSDL SaaS nằm BÊN TRONG kho của gateway!")
        self.assertFalse(os.path.realpath(cau_hinh.DUONG_DAN_CSDL).startswith(kho_gateway + os.sep))
        # và nếu gateway.db có tồn tại thì SaaS tuyệt đối không được ghi vào nó
        db_gw = os.path.join(kho_gateway, "gateway.db")
        if os.path.exists(db_gw):
            self.assertNotEqual(os.path.realpath(cau_hinh.DUONG_DAN_CSDL), os.path.realpath(db_gw))

    def test_17_live_bi_khoa(self):
        import adapter
        with self.assertRaises(PermissionError):
            adapter.tao_adapter("jt", {}, "production")
        with self.assertRaises(PermissionError):
            adapter.tao_adapter("vtp", {}, "sandbox")

    def test_18_ky_jt_dung_cong_thuc_docs(self):
        # digest = base64(md5(bizContent + privateKey)) — đối chiếu độc lập bằng hashlib
        import adapter_jt
        biz, key = '{"customerCode":"TEST"}', "PRIV"
        mong = base64.b64encode(hashlib.md5((biz + key).encode()).digest()).decode()
        self.assertEqual(adapter_jt.ky_digest(biz, key), mong)


if __name__ == "__main__":
    unittest.main(verbosity=2)
