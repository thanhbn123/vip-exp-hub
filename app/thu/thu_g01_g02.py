# Bộ thử G01 + G02 — TEST-001..TEST-015 theo brief, chạy server thật trên cổng tạm, CSDL tạm.
# Chạy: python3 app/thu/thu_g01_g02.py
import hashlib
import hmac
import io
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_DA = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g0102-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ["VIP_HUB_BACKOFF"] = "0.05"

import bao_mat   # noqa: E402
import csdl      # noqa: E402
import quyen     # noqa: E402
import server    # noqa: E402
import webhook   # noqa: E402
import khoi_tao  # noqa: E402

CONG = 18896
URL = f"http://127.0.0.1:{CONG}"
LOG = io.StringIO()
MK = "MatKhauThu-123"


class Phien:
    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
        body = tho if tho is not None else (json.dumps(du_lieu).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        if method in ("POST", "PUT", "DELETE") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(URL + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=10) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                raw = ph.read()
                ct = ph.headers.get("Content-Type", "")
                return ph.status, (json.loads(raw) if "json" in ct else raw)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def dang_nhap(self, ten, mk=MK):
        return self.goi("/api/v2/auth/dang-nhap", "POST", {"ten_dang_nhap": ten, "mat_khau": mk})


def phien(ten, mk=MK):
    p = Phien()
    st, kq = p.dang_nhap(ten, mk)
    assert st == 200, f"đăng nhập {ten} hỏng: {kq}"
    return p


DON = {"nguoi_gui_ten": "Shop", "nguoi_gui_sdt": "0901111111", "nguoi_gui_dia_chi": "1 Thu",
       "nguoi_nhan_ten": "Khach", "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Thu",
       "hang_hoa": "Hop", "khoi_luong_gram": 500, "cod": 100000}


class ThuG01G02(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._err = sys.stderr
        sys.stderr = LOG
        csdl.mo()
        quyen.seed()
        khoi_tao.seed_providers()
        csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'test')",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('po',?,'Platform Owner','PLATFORM_OWNER',?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                 " VALUES ('padmin',?,'Platform Admin','PLATFORM_ADMIN',?)",
                 (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))
        webhook.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", CONG), server.BoXuLy)
        threading.Thread(target=cls.sv.serve_forever, daemon=True).start()

        cls.po = phien("po")
        for ten, code, dn in (("Tenant A", "ta", "a-owner"), ("Tenant B", "tb", "b-owner")):
            st, kq = cls.po.goi("/api/v2/platform/tenants", "POST",
                                {"ten": ten, "code": code, "goi_id": "pro",
                                 "owner_ten_dang_nhap": dn, "owner_mat_khau": MK})
            assert st == 201, kq
            if code == "ta":
                cls.tid_a = kq["id"]
            else:
                cls.tid_b = kq["id"]
        cls.a = phien("a-owner")
        cls.b = phien("b-owner")
        # thành viên của A
        for dn, role in (("a-staff", "TENANT_STAFF"), ("a-viewer", "TENANT_VIEWER"),
                         ("a-admin", "TENANT_ADMIN")):
            st, kq = cls.a.goi("/api/v2/memberships", "POST",
                               {"ten_dang_nhap": dn, "mat_khau": MK, "ho_ten": dn, "role": role})
            assert st == 201, (dn, kq)
        cls.a_staff, cls.a_viewer, cls.a_admin = phien("a-staff"), phien("a-viewer"), phien("a-admin")
        # user thuộc CẢ hai tenant (kiểm switch tenant)
        st, kq = cls.a.goi("/api/v2/memberships", "POST",
                           {"ten_dang_nhap": "hai-ben", "mat_khau": MK, "role": "TENANT_STAFF"})
        assert st == 201, kq
        cls.uid_hai_ben = kq["user_id"]
        st, kq = cls.b.goi("/api/v2/memberships", "POST",
                           {"ten_dang_nhap": "hai-ben", "role": "TENANT_VIEWER"})
        assert st == 201, kq
        # tài khoản hãng mỗi bên
        st, kq = cls.a.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "vtp", "ten": "VTP-A", "credentials": {"api_key": "KEY-CUA-A-9999"}})
        assert st == 201, kq
        cls.tk_a = kq
        st, kq = cls.b.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "jt", "ten": "JT-B", "credentials": {"privateKey": "KEY-CUA-B-8888"}})
        assert st == 201, kq
        cls.tk_b = kq
        # khách + đơn của mỗi bên
        cls.kh_a = cls.a.goi("/api/v2/khach-hang", "POST", {"ten": "Khach cua A"})[1]["id"]
        cls.kh_b = cls.b.goi("/api/v2/khach-hang", "POST", {"ten": "Khach cua B"})[1]["id"]
        cls.don_a = cls.a.goi("/api/v2/don", "POST", dict(DON))[1]["don"]["id"]
        cls.don_b = cls.b.goi("/api/v2/don", "POST", dict(DON))[1]["don"]["id"]

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown(); cls.sv.server_close()
        webhook.dung(); csdl.dong()
        sys.stderr = cls._err

    # ---------- TEST-001 ----------
    def test_001_tenant_a_khong_doc_duoc_tenant_b(self):
        self.assertEqual(self.a.goi(f"/api/v2/don/{self.don_b}")[0], 404)
        self.assertEqual(self.a.goi(f"/api/v2/khach-hang/{self.kh_b}")[0], 404)
        st, kq = self.a.goi("/api/v2/don")
        self.assertTrue(all(d["id"] != self.don_b for d in kq["don"]))
        st, kq = self.a.goi("/api/v2/khach-hang")
        self.assertTrue(all(k["id"] != self.kh_b for k in kq["khach_hang"]))
        # audit của A không chứa dòng của B
        st, kq = self.a.goi("/api/v2/audit")
        self.assertTrue(all(x["tenant_id"] == self.tid_a for x in kq["audit"]))
        # tài khoản hãng của B không hiện ở A
        st, kq = self.a.goi("/api/v2/tai-khoan-hang")
        self.assertTrue(all(t["id"] != self.tk_b["id"] for t in kq["tai_khoan"]))

    # ---------- TEST-002 ----------
    def test_002_tenant_a_khong_sua_duoc_tenant_b(self):
        self.assertEqual(self.a.goi(f"/api/v2/don/{self.don_b}", "PUT", {"hang_hoa": "doi"})[0], 404)
        self.assertEqual(self.a.goi(f"/api/v2/don/{self.don_b}/duyet", "POST", {})[0], 404)
        d = dict(csdl.mot("SELECT hang_hoa FROM don_hang WHERE id=?", (self.don_b,)))
        self.assertEqual(d["hang_hoa"], "Hop", "đơn của B bị A sửa!")

    # ---------- TEST-003 ----------
    def test_003_tenant_a_khong_xoa_duoc_resource_b(self):
        self.assertEqual(self.a.goi(f"/api/v2/don/{self.don_b}", "DELETE")[0], 404)
        self.assertEqual(self.a.goi(f"/api/v2/tai-khoan-hang/{self.tk_b['id']}/khoa", "POST", {})[0], 404)
        self.assertIsNotNone(csdl.mot("SELECT 1 x FROM don_hang WHERE id=?", (self.don_b,)))
        tk = csdl.mot("SELECT kich_hoat FROM carrier_accounts WHERE id=?", (self.tk_b["id"],))
        self.assertEqual(tk["kich_hoat"], 1, "A khóa được tài khoản hãng của B!")

    # ---------- TEST-004 ----------
    def test_004_khong_dung_duoc_carrier_account_cua_tenant_khac(self):
        self.a.goi(f"/api/v2/don/{self.don_a}/duyet", "POST", {})
        st, kq = self.a.goi(f"/api/v2/don/{self.don_a}/gui", "POST",
                            {"carrier_account_id": self.tk_b["id"]})
        self.assertEqual(st, 404, f"A gửi đơn bằng account của B! {kq}")
        d = csdl.mot("SELECT trang_thai, ma_van_don FROM don_hang WHERE id=?", (self.don_a,))
        self.assertIsNone(d["ma_van_don"])

    # ---------- TEST-005 ----------
    def test_005_user_vo_hieu_khong_dang_nhap_duoc(self):
        st, kq = self.a.goi("/api/v2/memberships", "POST",
                            {"ten_dang_nhap": "sap-khoa", "mat_khau": MK, "role": "TENANT_STAFF"})
        uid = kq["user_id"]
        self.assertEqual(phien("sap-khoa").goi("/api/v2/auth/toi")[0], 200)
        csdl.ghi("UPDATE users SET trang_thai='khoa' WHERE id=?", (uid,))
        st, kq = Phien().dang_nhap("sap-khoa")
        self.assertEqual(st, 401, "user bị khóa vẫn đăng nhập được!")
        csdl.ghi("UPDATE users SET trang_thai='hoat_dong' WHERE id=?", (uid,))

    # ---------- TEST-006 ----------
    def test_006_membership_vo_hieu_mat_quyen_truy_cap(self):
        st, kq = self.a.goi("/api/v2/memberships", "POST",
                            {"ten_dang_nhap": "sap-vo-hieu", "mat_khau": MK, "role": "TENANT_STAFF"})
        mem_id = kq["membership_id"]
        p = phien("sap-vo-hieu")
        self.assertEqual(p.goi("/api/v2/don")[0], 200)
        st, _ = self.a.goi(f"/api/v2/memberships/{mem_id}", "PUT", {"trang_thai": "vo_hieu"})
        self.assertEqual(st, 200)
        # phiên cũ mất hiệu lực, và đăng nhập lại cũng không vào được tenant nào
        self.assertEqual(p.goi("/api/v2/don")[0], 401)
        st, kq = Phien().dang_nhap("sap-vo-hieu")
        self.assertEqual(st, 401, "membership vô hiệu vẫn vào được tenant!")

    # ---------- TEST-007 ----------
    def test_007_viewer_khong_tao_hoac_sua_du_lieu(self):
        self.assertEqual(self.a_viewer.goi("/api/v2/don", "POST", dict(DON))[0], 403)
        self.assertEqual(self.a_viewer.goi("/api/v2/khach-hang", "POST", {"ten": "x"})[0], 403)
        self.assertEqual(self.a_viewer.goi(f"/api/v2/don/{self.don_a}", "PUT", {"hang_hoa": "x"})[0], 403)
        self.assertEqual(self.a_viewer.goi(f"/api/v2/don/{self.don_a}/duyet", "POST", {})[0], 403)
        self.assertEqual(self.a_viewer.goi("/api/v2/don")[0], 200)   # nhưng vẫn xem được

    # ---------- TEST-008 ----------
    def test_008_staff_khong_doi_duoc_role(self):
        mem = csdl.mot("SELECT m.id FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                       " WHERE u.ten_dang_nhap='a-viewer'")
        self.assertEqual(self.a_staff.goi("/api/v2/memberships")[0], 403)
        self.assertEqual(self.a_staff.goi(f"/api/v2/memberships/{mem['id']}", "PUT",
                                          {"role": "TENANT_ADMIN"})[0], 403)
        self.assertEqual(self.a_staff.goi("/api/v2/memberships", "POST",
                                          {"ten_dang_nhap": "x1", "mat_khau": MK,
                                           "role": "TENANT_STAFF"})[0], 403)
        r = csdl.mot("SELECT role FROM tenant_memberships WHERE id=?", (mem["id"],))
        self.assertEqual(r["role"], "TENANT_VIEWER", "staff đổi được vai trò!")

    # ---------- TEST-009 ----------
    def test_009_tenant_admin_khong_cap_duoc_quyen_platform(self):
        # TENANT_ADMIN chỉ được cấp STAFF/VIEWER
        for role in ("PLATFORM_OWNER", "PLATFORM_ADMIN", "TENANT_OWNER", "TENANT_ADMIN"):
            st, kq = self.a_admin.goi("/api/v2/memberships", "POST",
                                      {"ten_dang_nhap": "leo-thang", "mat_khau": MK, "role": role})
            self.assertEqual(st, 403, f"TENANT_ADMIN cấp được {role}!")
        self.assertIsNone(csdl.mot("SELECT 1 x FROM users WHERE ten_dang_nhap='leo-thang'"))
        # và không gọi được API nền tảng
        self.assertEqual(self.a_admin.goi("/api/v2/platform/tenants")[0], 403)
        self.assertEqual(self.a.goi("/api/v2/platform/tenants", "POST", {"ten": "x"})[0], 403)
        # PLATFORM_ADMIN cũng không được tạo tenant hay đổi gói (quyền phân công hẹp hơn OWNER)
        pa = phien("padmin")
        self.assertEqual(pa.goi("/api/v2/platform/tenants", "POST",
                                {"ten": "X", "owner_ten_dang_nhap": "zz", "owner_mat_khau": MK})[0], 403)
        self.assertEqual(pa.goi(f"/api/v2/platform/tenants/{self.tid_a}/goi", "POST",
                                {"goi_id": "free"})[0], 403)
        self.assertEqual(pa.goi("/api/v2/platform/tenants")[0], 200)

    # ---------- TEST-010 ----------
    def test_010_doi_tenant_id_trong_request_khong_vuot_quyen(self):
        # nhét tenant_id của B vào body/query theo mọi kiểu — backend phải bỏ qua
        st, kq = self.a.goi("/api/v2/don", "POST", dict(DON, tenant_id=self.tid_b))
        self.assertEqual(st, 201)
        d = csdl.mot("SELECT tenant_id FROM don_hang WHERE id=?", (kq["don"]["id"],))
        self.assertEqual(d["tenant_id"], self.tid_a, "tenant_id trong body ghi đè được ngữ cảnh!")
        st, kq = self.a.goi(f"/api/v2/don?tenant_id={self.tid_b}")
        self.assertTrue(all(x["id"] != self.don_b for x in kq["don"]))
        st, kq = self.a.goi("/api/v2/khach-hang", "POST", {"ten": "KH", "tenant_id": self.tid_b})
        self.assertEqual(csdl.mot("SELECT tenant_id FROM khach_hang WHERE id=?",
                                  (kq["id"],))["tenant_id"], self.tid_a)
        # switch sang tenant mình KHÔNG thuộc → bị từ chối
        self.assertEqual(self.a.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": self.tid_b})[0], 403)

    # ---------- TEST-011 ----------
    def test_011_doi_resource_id_khong_lo_du_lieu_tenant_khac(self):
        for duong in (f"/api/v2/don/{self.don_b}", f"/api/v2/khach-hang/{self.kh_b}",
                      f"/api/v2/import/999999"):
            st, kq = self.a.goi(duong)
            self.assertIn(st, (404,), f"{duong} trả {st}")
            self.assertNotIn("Khach cua B", json.dumps(kq, ensure_ascii=False))
        # replay sự kiện webhook của B từ phiên A
        don_b = csdl.mot("SELECT * FROM don_hang WHERE id=?", (self.don_b,))
        st, _ = self.a.goi("/api/v2/webhook/su-kien/999999/replay", "POST", {})
        self.assertEqual(st, 404)

    # ---------- TEST-012 ----------
    def test_012_session_da_revoke_het_hieu_luc(self):
        # Dùng user RIÊNG: thu-hoi-phien hủy mọi phiên khác của cùng user, nếu mượn a-staff
        # thì các test sau (dùng cls.a_staff) sẽ bị 401 — lỗi của bộ thử, không phải của sản phẩm.
        self.a.goi("/api/v2/memberships", "POST",
                   {"ten_dang_nhap": "thu-phien", "mat_khau": MK, "role": "TENANT_STAFF"})
        p1, p2 = phien("thu-phien"), phien("thu-phien")
        self.assertEqual(p2.goi("/api/v2/auth/toi")[0], 200)
        st, _ = p1.goi("/api/v2/auth/thu-hoi-phien", "POST", {})
        self.assertEqual(st, 200)
        self.assertEqual(p2.goi("/api/v2/auth/toi")[0], 401, "phiên bị thu hồi vẫn dùng được!")
        self.assertEqual(p1.goi("/api/v2/auth/toi")[0], 200)
        # đăng xuất thì chính phiên đó cũng hết
        p1.goi("/api/v2/auth/dang-xuat", "POST", {})
        self.assertEqual(p1.goi("/api/v2/auth/toi")[0], 401)

    # ---------- TEST-013 ----------
    def test_013_khong_lo_password_hoac_token_trong_log(self):
        log = LOG.getvalue()
        for bi_mat in (MK, "KEY-CUA-A-9999", "KEY-CUA-B-8888",
                       self.tk_a["webhook_secret_mot_lan"], self.tk_b["webhook_secret_mot_lan"]):
            self.assertNotIn(bi_mat, log, "secret lộ trong log!")
        # cookie phiên (token) cũng không được vào log
        self.assertNotIn(self.a.cookie.split("=", 1)[1], log, "token phiên lộ trong log!")
        # API không trả secret
        st, kq = self.a.goi("/api/v2/tai-khoan-hang")
        self.assertNotIn("KEY-CUA-A-9999", json.dumps(kq))
        # CSDL lưu bản mã hóa
        r = csdl.mot("SELECT credentials_ma_hoa, mat_khau_hash FROM carrier_accounts"
                     " JOIN users ON users.ten_dang_nhap='a-owner' WHERE carrier_accounts.id=?",
                     (self.tk_a["id"],))
        self.assertNotIn("KEY-CUA-A-9999", r["credentials_ma_hoa"])
        self.assertNotIn(MK, r["mat_khau_hash"])

    # ---------- TEST-014 ----------
    def test_014_migration_bao_toan_du_lieu(self):
        """Dựng CSDL dạng v1 (schema cũ) có dữ liệu, chạy migrate thật, kiểm bảo toàn + rollback."""
        thu_muc = tempfile.mkdtemp(prefix="vip-hub-migr-")
        db = os.path.join(thu_muc, "hub.db")
        kn = sqlite3.connect(db)
        kn.executescript("""
        CREATE TABLE goi_dich_vu (id TEXT PRIMARY KEY, ten TEXT NOT NULL, gia_thang INTEGER NOT NULL,
          han_muc_don_thang INTEGER NOT NULL, han_muc_ai_thang INTEGER NOT NULL,
          so_nhan_vien INTEGER NOT NULL, so_tai_khoan_hang INTEGER NOT NULL);
        INSERT INTO goi_dich_vu VALUES ('basic','Cơ bản',299000,1000,500,5,3);
        CREATE TABLE tenants (id INTEGER PRIMARY KEY AUTOINCREMENT, ten TEXT NOT NULL,
          goi_id TEXT NOT NULL, trang_thai TEXT NOT NULL DEFAULT 'hoat_dong', tao_luc TEXT NOT NULL);
        INSERT INTO tenants (ten,goi_id,tao_luc) VALUES ('Shop Cũ','basic','2026-01-01');
        CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER,
          ten_dang_nhap TEXT NOT NULL UNIQUE, mat_khau_hash TEXT NOT NULL, ho_ten TEXT NOT NULL,
          vai_tro TEXT NOT NULL, trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',
          so_lan_sai INTEGER NOT NULL DEFAULT 0, tao_luc TEXT NOT NULL, doi_mat_khau_luc TEXT);
        INSERT INTO users (tenant_id,ten_dang_nhap,mat_khau_hash,ho_ten,vai_tro,tao_luc)
          VALUES (1,'cu-owner','h','Chủ cũ','TENANT_OWNER','2026-01-01'),
                 (NULL,'cu-po','h','PO cũ','PLATFORM_OWNER','2026-01-01');
        CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
          tao_luc TEXT NOT NULL, het_han TEXT NOT NULL, thu_hoi INTEGER NOT NULL DEFAULT 0, dia_chi TEXT);
        CREATE TABLE khach_hang (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL,
          ten TEXT NOT NULL, sdt TEXT, dia_chi TEXT, ghi_chu TEXT, tao_luc TEXT NOT NULL);
        INSERT INTO khach_hang (tenant_id,ten,tao_luc) VALUES (1,'Khách cũ','2026-01-01');
        CREATE TABLE carrier_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL,
          hang TEXT NOT NULL, ten TEXT NOT NULL, moi_truong TEXT NOT NULL DEFAULT 'mock',
          credentials_ma_hoa TEXT NOT NULL, credentials_duoi TEXT NOT NULL DEFAULT '',
          webhook_ma TEXT NOT NULL UNIQUE, webhook_secret_ma_hoa TEXT NOT NULL,
          kich_hoat INTEGER NOT NULL DEFAULT 1, tao_luc TEXT NOT NULL);
        INSERT INTO carrier_accounts (tenant_id,hang,ten,credentials_ma_hoa,webhook_ma,
          webhook_secret_ma_hoa,tao_luc) VALUES (1,'vtp','VTP cũ','x','whcu','y','2026-01-01');
        CREATE TABLE don_hang (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL,
          ma_don TEXT NOT NULL, idem_key TEXT, khach_hang_id INTEGER,
          nguoi_gui_ten TEXT NOT NULL, nguoi_gui_sdt TEXT NOT NULL, nguoi_gui_dia_chi TEXT NOT NULL,
          nguoi_nhan_ten TEXT NOT NULL, nguoi_nhan_sdt TEXT NOT NULL, nguoi_nhan_dia_chi TEXT NOT NULL,
          hang_hoa TEXT NOT NULL, khoi_luong_gram INTEGER NOT NULL, cod INTEGER NOT NULL DEFAULT 0,
          gia_tri_khai INTEGER NOT NULL DEFAULT 0, phi_van_chuyen INTEGER, ghi_chu TEXT,
          carrier_account_id INTEGER, ma_van_don TEXT, trang_thai TEXT NOT NULL DEFAULT 'nhap',
          can_doi_soat_ket_qua INTEGER NOT NULL DEFAULT 0, trang_thai_giao TEXT,
          hang_trang_thai_giao INTEGER NOT NULL DEFAULT 0, nguoi_tao INTEGER NOT NULL,
          tao_luc TEXT NOT NULL, cap_nhat_luc TEXT NOT NULL);
        INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,nguoi_gui_dia_chi,
          nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,nguoi_tao,
          tao_luc,cap_nhat_luc) VALUES (1,'OLD-1','a','0901111111','x','b','0902222222','y','z',
          100,1,'2026-01-01','2026-01-01');
        CREATE TABLE don_lich_su (id INTEGER PRIMARY KEY AUTOINCREMENT, don_id INTEGER NOT NULL,
          luc TEXT NOT NULL, nguon TEXT NOT NULL, noi_dung TEXT NOT NULL);
        CREATE TABLE wh_su_kien (id INTEGER PRIMARY KEY AUTOINCREMENT, carrier_account_id INTEGER NOT NULL,
          event_id TEXT NOT NULL, payload_tho BLOB NOT NULL, headers_json TEXT NOT NULL,
          nhan_luc TEXT NOT NULL, trang_thai TEXT NOT NULL DEFAULT 'moi',
          so_lan_thu INTEGER NOT NULL DEFAULT 0, loi_cuoi TEXT, xu_ly_xong_luc TEXT,
          UNIQUE (carrier_account_id, event_id));
        INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,nhan_luc)
          VALUES (1,'EVCU',X'7B7D','{}','2026-01-01');
        CREATE TABLE import_batch (id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL,
          ten_file TEXT NOT NULL, loai_file TEXT NOT NULL, trang_thai TEXT NOT NULL DEFAULT 'moi',
          nguoi_tao INTEGER NOT NULL, tao_luc TEXT NOT NULL);
        CREATE TABLE import_dong (id INTEGER PRIMARY KEY AUTOINCREMENT, batch_id INTEGER NOT NULL,
          stt INTEGER NOT NULL, du_lieu_json TEXT NOT NULL, trang_thai TEXT NOT NULL, loi TEXT,
          don_id INTEGER);
        CREATE TABLE usage_thang (tenant_id INTEGER NOT NULL, thang TEXT NOT NULL,
          so_don INTEGER NOT NULL DEFAULT 0, so_ai INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY (tenant_id, thang));
        CREATE TABLE audit (id INTEGER PRIMARY KEY AUTOINCREMENT, luc TEXT NOT NULL, tenant_id INTEGER,
          user_id INTEGER, hanh_dong TEXT NOT NULL, doi_tuong TEXT NOT NULL, chi_tiet TEXT, dia_chi TEXT);
        INSERT INTO audit (luc,hanh_dong,doi_tuong) VALUES ('2026-01-01','viec_cu','don:1');
        """)
        kn.commit(); kn.close()

        # chạy migrate trong tiến trình con (VIP_HUB_DATA trỏ vào CSDL v1 vừa dựng)
        moi_truong = dict(os.environ, VIP_HUB_DATA=thu_muc)
        kq = subprocess.run([sys.executable, os.path.join(GOC_APP, "migrate.py")],
                            capture_output=True, text=True, env=moi_truong, cwd=GOC_DA)
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("bảo toàn ĐẠT", kq.stdout)

        kn = sqlite3.connect(db); kn.row_factory = sqlite3.Row
        # dữ liệu cũ còn nguyên
        self.assertEqual(kn.execute("SELECT COUNT(*) FROM don_hang").fetchone()[0], 1)
        self.assertEqual(kn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 2)
        self.assertEqual(kn.execute("SELECT COUNT(*) FROM wh_su_kien").fetchone()[0], 1,
                         "sự kiện webhook cũ bị mất!")
        self.assertEqual(kn.execute("SELECT COUNT(*) FROM audit").fetchone()[0], 1)
        # vai trò đã chuyển sang membership, platform_role giữ đúng
        m = kn.execute("SELECT m.role FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                       " WHERE u.ten_dang_nhap='cu-owner'").fetchone()
        self.assertEqual(m["role"], "TENANT_OWNER")
        po = kn.execute("SELECT platform_role FROM users WHERE ten_dang_nhap='cu-po'").fetchone()
        self.assertEqual(po["platform_role"], "PLATFORM_OWNER")
        # KHÔNG gán tenant cho user nền tảng
        self.assertIsNone(kn.execute("SELECT 1 FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                                     " WHERE u.ten_dang_nhap='cu-po'").fetchone())
        self.assertEqual(kn.execute("SELECT MAX(phien_ban) FROM schema_version").fetchone()[0], 2)
        kn.close()

        # ROLLBACK về backup → phải trở lại schema v1 (còn cột vai_tro)
        bk = sorted(os.listdir(os.path.join(thu_muc, "sao-luu")))
        self.assertTrue(bk, "migration không tạo backup!")
        duong_bk = os.path.join(thu_muc, "sao-luu", [b for b in bk if "truoc-migrate" in b][0])
        kq = subprocess.run([sys.executable, os.path.join(GOC_APP, "migrate.py"), "--rollback", duong_bk],
                            capture_output=True, text=True, env=moi_truong, cwd=GOC_DA)
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        kn = sqlite3.connect(db)
        cot = [r[1] for r in kn.execute("PRAGMA table_info(users)")]
        self.assertIn("vai_tro", cot, "rollback không đưa được về schema cũ!")
        self.assertEqual(kn.execute("SELECT COUNT(*) FROM don_hang").fetchone()[0], 1)
        kn.close()
        shutil.rmtree(thu_muc, ignore_errors=True)

    # ---------- TEST-015 ----------
    def test_015_gateway_cu_van_dat(self):
        kq = subprocess.run([sys.executable, os.path.join(GOC_DA, "gateway", "thu", "thu_gateway.py")],
                            capture_output=True, text=True, cwd=GOC_DA)
        self.assertEqual(kq.returncode, 0, kq.stdout + kq.stderr)
        self.assertIn("Ran 9 tests", kq.stderr)
        self.assertIn("OK", kq.stderr)

    # ---------- bổ sung: switch tenant, reset mật khẩu, audit ----------
    def test_016_switch_tenant_dung_membership(self):
        p = phien("hai-ben")
        st, kq = p.goi("/api/v2/auth/toi")
        self.assertEqual(len(kq["tenant_kha_dung"]), 2, "user hai tenant không thấy đủ")
        self.assertEqual(kq["tenant"]["id"], self.tid_a)
        self.assertEqual(kq["vai_tro"], "TENANT_STAFF")
        # ở A là STAFF → tạo được đơn
        st, kq_a = p.goi("/api/v2/don", "POST", dict(DON))
        self.assertEqual(st, 201)
        don_tao_o_a = kq_a["don"]["id"]
        # switch sang B → vai trò VIEWER, KHÔNG tạo được đơn, và không thấy đơn của A
        st, kq = p.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": self.tid_b})
        self.assertEqual(st, 200)
        self.assertEqual(kq["vai_tro"], "TENANT_VIEWER")
        self.assertEqual(p.goi("/api/v2/don", "POST", dict(DON))[0], 403)
        st, kq = p.goi("/api/v2/don")
        self.assertTrue(all(d["id"] != don_tao_o_a for d in kq["don"]),
                        "switch tenant vẫn thấy dữ liệu tenant cũ!")
        # đơn vừa tạo thuộc A, không thuộc B
        self.assertEqual(csdl.mot("SELECT tenant_id FROM don_hang WHERE id=?",
                                  (don_tao_o_a,))["tenant_id"], self.tid_a)

    def test_017_reset_mat_khau_gia_lap(self):
        self.a.goi("/api/v2/memberships", "POST",
                   {"ten_dang_nhap": "quen-mk", "mat_khau": MK, "role": "TENANT_STAFF"})
        p_cu = phien("quen-mk")
        st, kq = Phien().goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "quen-mk"})
        self.assertEqual(st, 200)
        token = kq["token_gia_lap"]
        # tài khoản không tồn tại → cùng một thông báo, không lộ
        st, kq2 = Phien().goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "khong-co-ai"})
        self.assertEqual(st, 200)
        self.assertEqual(kq["thong_bao"], kq2["thong_bao"])
        self.assertNotIn("token_gia_lap", kq2)
        # đặt lại mật khẩu
        st, _ = Phien().goi("/api/v2/auth/dat-lai-mat-khau", "POST",
                            {"token": token, "mat_khau_moi": "MatKhauMoi-999"})
        self.assertEqual(st, 200)
        self.assertEqual(p_cu.goi("/api/v2/auth/toi")[0], 401, "phiên cũ còn sống sau reset!")
        self.assertEqual(Phien().dang_nhap("quen-mk", "MatKhauMoi-999")[0], 200)
        self.assertEqual(Phien().dang_nhap("quen-mk", MK)[0], 401)
        # token dùng một lần
        st, _ = Phien().goi("/api/v2/auth/dat-lai-mat-khau", "POST",
                            {"token": token, "mat_khau_moi": "LaiMotLanNua-1"})
        self.assertEqual(st, 400)

    def test_018_audit_du_truong_va_ghi_tu_choi(self):
        self.a_viewer.goi("/api/v2/don", "POST", dict(DON))   # bị từ chối → phải có audit
        r = csdl.mot("SELECT * FROM audit WHERE hanh_dong='tu_choi_quyen' ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(r, "từ chối quyền không được ghi audit")
        for c in ("luc", "user_id", "hanh_dong", "resource_type", "resource_id", "ket_qua"):
            self.assertIsNotNone(r[c], f"audit thiếu {c}")
        self.assertEqual(r["ket_qua"], "tu_choi")
        # đăng nhập sai cũng được ghi
        Phien().dang_nhap("a-owner", "sai-mat-khau")
        r2 = csdl.mot("SELECT * FROM audit WHERE hanh_dong='dang_nhap_that_bai' ORDER BY id DESC LIMIT 1")
        self.assertIsNotNone(r2)
        # audit không chứa mật khẩu
        het = " ".join(str(dict(x)) for x in csdl.nhieu("SELECT * FROM audit"))
        self.assertNotIn(MK, het)
        self.assertNotIn("sai-mat-khau", het)

    def test_019_rbac_lay_tu_csdl_khong_hardcode(self):
        # Bỏ một quyền khỏi CSDL → endpoint phải từ chối ngay (chứng minh không hard-code)
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma='TENANT_STAFF' AND perm_ma='tenant.don.ghi'")
        try:
            self.assertEqual(self.a_staff.goi("/api/v2/don", "POST", dict(DON))[0], 403)
        finally:
            csdl.ghi("INSERT OR IGNORE INTO role_permissions VALUES ('TENANT_STAFF','tenant.don.ghi')")
        self.assertEqual(self.a_staff.goi("/api/v2/don", "POST", dict(DON))[0], 201)

    def test_020_carrier_account_isolation_va_rotate(self):
        truoc = csdl.mot("SELECT credentials_ma_hoa FROM carrier_accounts WHERE id=?",
                         (self.tk_a["id"],))["credentials_ma_hoa"]
        st, _ = self.a.goi(f"/api/v2/tai-khoan-hang/{self.tk_a['id']}/rotate", "POST",
                           {"credentials": {"api_key": "KEY-MOI-CUA-A-7777"}})
        self.assertEqual(st, 200)
        sau = csdl.mot("SELECT credentials_ma_hoa, credentials_doi_luc FROM carrier_accounts WHERE id=?",
                       (self.tk_a["id"],))
        self.assertNotEqual(truoc, sau["credentials_ma_hoa"])
        self.assertIsNotNone(sau["credentials_doi_luc"])
        self.assertEqual(json.loads(bao_mat.giai_ma(sau["credentials_ma_hoa"]))["api_key"],
                         "KEY-MOI-CUA-A-7777")
        # B không rotate/revoke được account của A
        self.assertEqual(self.b.goi(f"/api/v2/tai-khoan-hang/{self.tk_a['id']}/rotate", "POST",
                                    {"credentials": {"x": 1}})[0], 404)
        # revoke: tắt + xóa credentials
        st, _ = self.a.goi(f"/api/v2/tai-khoan-hang/{self.tk_a['id']}/revoke", "POST", {})
        self.assertEqual(st, 200)
        r = csdl.mot("SELECT kich_hoat, credentials_ma_hoa FROM carrier_accounts WHERE id=?",
                     (self.tk_a["id"],))
        self.assertEqual(r["kich_hoat"], 0)
        self.assertEqual(json.loads(bao_mat.giai_ma(r["credentials_ma_hoa"])), {})
        self.a.goi(f"/api/v2/tai-khoan-hang/{self.tk_a['id']}/mo", "POST", {})

    def test_021_tenant_bi_khoa_thi_thanh_vien_mat_quyen(self):
        p = phien("b-owner")
        self.assertEqual(p.goi("/api/v2/don")[0], 200)
        self.po.goi(f"/api/v2/platform/tenants/{self.tid_b}/khoa", "POST", {})
        try:
            self.assertEqual(p.goi("/api/v2/don")[0], 401, "tenant bị khóa mà thành viên vẫn vào được!")
            self.assertEqual(Phien().dang_nhap("b-owner")[0], 401)
        finally:
            self.po.goi(f"/api/v2/platform/tenants/{self.tid_b}/mo", "POST", {})
        self.assertEqual(Phien().dang_nhap("b-owner")[0], 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
