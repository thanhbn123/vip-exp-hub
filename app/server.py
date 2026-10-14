# VIP Express Hub — backend Multi-Tenant SaaS v2 (local-first), cổng 8897.
# Stdlib + SQLite. Bind 127.0.0.1. Phục vụ static (admin/, pages/, assets/) + API /api/v2/*.
# TENANT CONTEXT MIDDLEWARE: mọi API nghiệp vụ chạy qua _ngu_canh() →
#   AUTHENTICATE USER → RESOLVE MEMBERSHIP → SELECT ACTIVE TENANT → AUTHORIZE → BUSINESS LOGIC.
# tenant_id KHÔNG BAO GIỜ nhận từ body/query của client.
import base64
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import adapter
import adapter_jt   # noqa: F401 — đăng ký adapter
import adapter_vtp  # noqa: F401
import ai_gateway
import bao_mat
import billing
import cau_hinh
import csdl
import don_hang
import nhap_file
import polling
import quyen
import webhook

GOC_TINH = cau_hinh.THU_MUC_GOC


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, default=str).encode()


class BoXuLy(BaseHTTPRequestHandler):
    server_version = "VIPExpressHub/0.3-SaaS"

    def log_message(self, fmt, *args):
        # Log KHÔNG BAO GIỜ chứa body/secret — chỉ dòng request chuẩn.
        sys.stderr.write("[hub] %s\n" % (fmt % args))

    # ---------- tiện ích ----------
    def _headers_thuong(self):
        return {k.lower(): v for k, v in self.headers.items()}

    def _tra(self, ma, obj, cookie=None):
        body = _json(obj)
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _doc_body(self, gioi_han=20 * 1024 * 1024):
        dai = int(self.headers.get("Content-Length") or 0)
        if dai > gioi_han:
            raise don_hang.LoiNghiepVu("body quá lớn", 413)
        return self.rfile.read(dai) if dai else b""

    def _doc_json(self):
        try:
            return json.loads(self._doc_body() or b"{}")
        except ValueError:
            raise don_hang.LoiNghiepVu("body không phải JSON")

    def _token(self):
        m = re.search(r"(?:^|;\s*)phien=([^;]+)", self.headers.get("Cookie", ""))
        return m.group(1) if m else None

    def _can_csrf(self):
        if self.headers.get("X-Requested-With") != "VIPHub":
            raise don_hang.LoiNghiepVu("thiếu header X-Requested-With: VIPHub (chống CSRF)", 403)

    def _truy_van(self):
        from urllib.parse import unquote_plus
        _, _, q = self.path.partition("?")
        ts = {}
        for cap in q.split("&"):
            if "=" in cap:
                k, v = cap.split("=", 1)
                ts[k] = unquote_plus(v)
        return ts

    def _can(self, nc, hanh_dong):
        """AUTHORIZE: tra quyền trong CSDL. Từ chối thì ghi audit rồi ném 403."""
        if not nc.co_quyen(hanh_dong):
            csdl.audit("tu_choi_quyen", f"permission:{hanh_dong}", f"vai trò {nc.role}",
                       tenant_id=nc.tenant_id, user_id=nc.user_id,
                       dia_chi=self.client_address[0], ket_qua="tu_choi")
            raise don_hang.LoiNghiepVu("không đủ quyền", 403)

    # ---------- static ----------
    def _phuc_vu_tinh(self, duong):
        if duong == "/":
            duong = "/admin/index.html"
        if duong.endswith("/"):
            duong += "index.html"
        an_toan = os.path.normpath(duong).lstrip("/")
        if an_toan.startswith(("..", "app/du-lieu", "gateway/du-lieu", ".git")):
            return self._tra(404, {"loi": "không có"})
        full = os.path.join(GOC_TINH, an_toan)
        if not os.path.isfile(full):
            return self._tra(404, {"loi": "không có file này"})
        loai = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", loai + ("; charset=utf-8" if loai.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    # ---------- router ----------
    def _chay(self, method):
        try:
            duong = self.path.split("?")[0]
            if method == "GET" and not duong.startswith("/api/"):
                return self._phuc_vu_tinh(duong)
            return self._api(duong, method)
        except don_hang.LoiNghiepVu as e:
            self._tra(e.ma, {"loi": str(e)})
        except billing.VuotHanMuc as e:
            self._tra(402, {"loi": f"vượt hạn mức gói: {e}"})
        except PermissionError as e:
            self._tra(403, {"loi": str(e)})
        except Exception as e:
            self._tra(500, {"loi": f"lỗi hệ thống: {type(e).__name__}"})
            sys.stderr.write(f"[hub] LOI 500: {type(e).__name__}: {e}\n")

    def do_GET(self):
        self._chay("GET")

    def do_POST(self):
        self._chay("POST")

    def do_PUT(self):
        self._chay("PUT")

    def do_DELETE(self):
        self._chay("DELETE")

    # ---------- API ----------
    def _api(self, duong, method):
        # --- webhook ingest: không cần phiên, xác thực bằng chữ ký của chính carrier account ---
        m = re.fullmatch(r"/api/v2/webhook/nhan/([A-Za-z0-9_-]+)", duong)
        if m and method == "POST":
            tk = webhook.tim_account_theo_webhook_ma(m.group(1))
            if not tk:
                return self._tra(404, {"loi": "webhook không tồn tại"})
            body = self._doc_body()
            if not webhook.kiem_chu_ky(tk, self._headers_thuong(), body):
                return self._tra(401, {"loi": "chữ ký webhook sai hoặc thiếu"})
            sk_id, trung = webhook.nhan_su_kien(tk, body, self._headers_thuong())
            if trung:
                return self._tra(200, {"ket_qua": "da_nhan_truoc_do", "su_kien_id": sk_id})
            return self._tra(202, {"ket_qua": "da_nhan", "su_kien_id": sk_id})

        # --- auth công khai ---
        if duong == "/api/v2/auth/dang-nhap" and method == "POST":
            self._can_csrf()
            d = self._doc_json()
            token, kq = bao_mat.dang_nhap(d.get("ten_dang_nhap", ""), d.get("mat_khau", ""),
                                          self.client_address[0])
            if token is None:
                return self._tra(401, {"loi": kq})
            cookie = f"phien={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={cau_hinh.PHIEN_SONG_GIO * 3600}"
            return self._tra(200, {"ok": True}, cookie=cookie)
        if duong == "/api/v2/auth/quen-mat-khau" and method == "POST":
            self._can_csrf()
            tk = bao_mat.tao_token_reset(self._doc_json().get("ten_dang_nhap", ""))
            # Luôn trả cùng một thông báo — không tiết lộ tài khoản nào có thật.
            ra = {"ok": True, "thong_bao": "Nếu tài khoản tồn tại, liên kết đặt lại đã được tạo."}
            if tk and cau_hinh.HIEN_TOKEN_RESET:
                # Provider giả lập (chưa cấu hình SMTP): chỉ bật ở local để kiểm thử luồng.
                ra["token_gia_lap"] = tk
                ra["ghi_chu"] = "GIẢ LẬP LOCAL — bản thật sẽ gửi qua email, không trả về API"
            return self._tra(200, ra)
        if duong == "/api/v2/auth/dat-lai-mat-khau" and method == "POST":
            self._can_csrf()
            d = self._doc_json()
            ok, ly_do = bao_mat.dat_lai_mat_khau(d.get("token", ""), d.get("mat_khau_moi", ""))
            return self._tra(200 if ok else 400, {"ok": ok} if ok else {"loi": ly_do})

        # --- TENANT CONTEXT MIDDLEWARE ---
        nc = bao_mat.ngu_canh(self._token())
        if nc is None:
            return self._tra(401, {"loi": "chưa đăng nhập hoặc phiên hết hạn"})
        if method in ("POST", "PUT", "DELETE"):
            self._can_csrf()
        ts = self._truy_van()

        if duong == "/api/v2/auth/dang-xuat" and method == "POST":
            bao_mat.dang_xuat(nc.token)
            csdl.audit("dang_xuat", f"user:{nc.user_id}", "", tenant_id=nc.tenant_id, user_id=nc.user_id)
            return self._tra(200, {"ok": True}, cookie="phien=; Max-Age=0; Path=/")
        if duong == "/api/v2/auth/toi":
            ds = bao_mat.memberships_cua(nc.user_id)
            goi = billing.goi_cua_tenant(nc.tenant_id) if nc.tenant_id else None
            return self._tra(200, {
                "id": nc.user_id, "ten_dang_nhap": nc.user["ten_dang_nhap"], "ho_ten": nc.user["ho_ten"],
                "platform_role": nc.platform_role, "vai_tro": nc.role,
                "tenant": ({"id": nc.tenant_id, "ten": nc.tenant_ten} if nc.tenant_id else None),
                "tenant_kha_dung": [dict(x) for x in ds],
                "quyen": sorted(quyen.quyen_cua_vai_tro(nc.role)),
                "goi": dict(goi) if goi else None})
        if duong == "/api/v2/auth/doi-tenant" and method == "POST":
            # tenant_id ở đây CHỈ là lựa chọn; backend vẫn xác minh membership trước khi đổi.
            muc_tieu = self._doc_json().get("tenant_id")
            m = bao_mat.doi_tenant(nc, muc_tieu)
            if not m:
                return self._tra(403, {"loi": "bạn không có quyền vào doanh nghiệp này"})
            return self._tra(200, {"ok": True, "tenant_id": m["tenant_id"], "vai_tro": m["role"]})
        if duong == "/api/v2/auth/doi-mat-khau" and method == "POST":
            d = self._doc_json()
            if not bao_mat.kiem_mat_khau(d.get("mat_khau_cu", ""), nc.user["mat_khau_hash"]):
                return self._tra(400, {"loi": "mật khẩu cũ sai"})
            if len(d.get("mat_khau_moi", "")) < 8:
                return self._tra(400, {"loi": "mật khẩu mới phải từ 8 ký tự"})
            csdl.ghi("UPDATE users SET mat_khau_hash=?, doi_mat_khau_luc=? WHERE id=?",
                     (bao_mat.bam_mat_khau(d["mat_khau_moi"]), csdl.bay_gio(), nc.user_id))
            bao_mat.thu_hoi_moi_phien(nc.user_id, tru_token=nc.token)
            csdl.audit("doi_mat_khau", f"user:{nc.user_id}", "thu hồi các phiên khác",
                       tenant_id=nc.tenant_id, user_id=nc.user_id)
            return self._tra(200, {"ok": True, "ghi_chu": "các phiên khác đã bị thu hồi"})
        if duong == "/api/v2/auth/thu-hoi-phien" and method == "POST":
            bao_mat.thu_hoi_moi_phien(nc.user_id, tru_token=nc.token)
            csdl.audit("thu_hoi_phien", f"user:{nc.user_id}", "", tenant_id=nc.tenant_id, user_id=nc.user_id)
            return self._tra(200, {"ok": True})

        if duong.startswith("/api/v2/platform/"):
            return self._api_platform(duong, method, nc)
        if nc.tenant_id is None:
            return self._tra(403, {"loi": "API này cần ngữ cảnh doanh nghiệp (tenant)"})
        return self._api_tenant(duong, method, nc, ts)

    # ---------- platform ----------
    def _api_platform(self, duong, method, nc):
        if duong == "/api/v2/platform/tenants" and method == "GET":
            self._can(nc, "platform.tenant.xem")
            ds = csdl.nhieu("SELECT t.*, g.ten ten_goi,"
                            " (SELECT COUNT(*) FROM tenant_memberships m WHERE m.tenant_id=t.id) so_thanh_vien"
                            " FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id ORDER BY t.id")
            return self._tra(200, {"tenants": [dict(x) for x in ds]})
        if duong == "/api/v2/platform/tenants" and method == "POST":
            self._can(nc, "platform.tenant.tao")
            d = self._doc_json()
            if not d.get("ten") or not d.get("owner_ten_dang_nhap") or len(d.get("owner_mat_khau", "")) < 8:
                return self._tra(400, {"loi": "cần ten, owner_ten_dang_nhap, owner_mat_khau (≥8 ký tự)"})
            goi_id = d.get("goi_id", "free")
            if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
                return self._tra(400, {"loi": "gói không tồn tại"})
            code = (d.get("code") or re.sub(r"[^a-z0-9]+", "-", d["ten"].lower()).strip("-"))[:40]
            if csdl.mot("SELECT id FROM tenants WHERE code=?", (code,)):
                return self._tra(400, {"loi": f"mã tenant '{code}' đã tồn tại"})
            con = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                           (code, d["ten"], goi_id, csdl.bay_gio()))
            t_id = con.lastrowid
            u = csdl.mot("SELECT * FROM users WHERE ten_dang_nhap=?", (d["owner_ten_dang_nhap"],))
            if u:
                u_id = u["id"]    # user đã có → chỉ thêm membership (một user thuộc nhiều tenant)
            else:
                u_id = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                                " VALUES (?,?,?,?)",
                                (d["owner_ten_dang_nhap"], bao_mat.bam_mat_khau(d["owner_mat_khau"]),
                                 d.get("owner_ho_ten", "Chủ doanh nghiệp"), csdl.bay_gio())).lastrowid
            csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, moi_boi, tao_luc)"
                     " VALUES (?,?,'TENANT_OWNER',?,?)", (u_id, t_id, nc.user_id, csdl.bay_gio()))
            csdl.audit("tao_tenant", f"tenant:{t_id}", d["ten"], user_id=nc.user_id)
            return self._tra(201, {"id": t_id, "code": code, "owner_user_id": u_id})
        m = re.fullmatch(r"/api/v2/platform/tenants/(\d+)", duong)
        if m:
            t_id = int(m.group(1))
            t = csdl.mot("SELECT t.*, g.ten ten_goi FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id"
                         " WHERE t.id=?", (t_id,))
            if not t:
                return self._tra(404, {"loi": "không có tenant"})
            if method == "GET":
                self._can(nc, "platform.tenant.xem")
                tv = csdl.nhieu("SELECT m.role, m.trang_thai, u.ten_dang_nhap, u.ho_ten"
                                " FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                                " WHERE m.tenant_id=?", (t_id,))
                return self._tra(200, {"tenant": dict(t), "thanh_vien": [dict(x) for x in tv]})
            if method in ("PUT", "POST"):
                self._can(nc, "platform.tenant.sua")
                d = self._doc_json()
                ten = d.get("ten", t["ten"]).strip() or t["ten"]
                csdl.ghi("UPDATE tenants SET ten=?, cap_nhat_luc=? WHERE id=?", (ten, csdl.bay_gio(), t_id))
                csdl.audit("sua_tenant", f"tenant:{t_id}", f"ten={ten}", user_id=nc.user_id)
                return self._tra(200, {"ok": True})
        m = re.fullmatch(r"/api/v2/platform/tenants/(\d+)/(khoa|mo|goi)", duong)
        if m and method == "POST":
            t_id, viec = int(m.group(1)), m.group(2)
            if not csdl.mot("SELECT id FROM tenants WHERE id=?", (t_id,)):
                return self._tra(404, {"loi": "không có tenant"})
            if viec == "goi":
                self._can(nc, "platform.goi.doi")
                goi_id = self._doc_json().get("goi_id")
                if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
                    return self._tra(400, {"loi": "gói không tồn tại"})
                csdl.ghi("UPDATE tenants SET goi_id=?, cap_nhat_luc=? WHERE id=?",
                         (goi_id, csdl.bay_gio(), t_id))
            else:
                self._can(nc, "platform.tenant.khoa")
                csdl.ghi("UPDATE tenants SET trang_thai=?, cap_nhat_luc=? WHERE id=?",
                         ("khoa" if viec == "khoa" else "hoat_dong", csdl.bay_gio(), t_id))
            csdl.audit(f"tenant_{viec}", f"tenant:{t_id}", "", user_id=nc.user_id)
            return self._tra(200, {"ok": True})
        if duong == "/api/v2/platform/goi":
            return self._tra(200, {"goi": [dict(x) for x in csdl.nhieu("SELECT * FROM goi_dich_vu")]})
        if duong == "/api/v2/platform/vai-tro":
            return self._tra(200, {
                "roles": [dict(x) for x in csdl.nhieu("SELECT * FROM roles ORDER BY pham_vi, ma")],
                "permissions": [dict(x) for x in csdl.nhieu("SELECT * FROM permissions ORDER BY ma")],
                "role_permissions": [dict(x) for x in csdl.nhieu("SELECT * FROM role_permissions")]})
        if duong == "/api/v2/platform/audit":
            self._can(nc, "platform.audit.xem")
            ds = csdl.nhieu("SELECT * FROM audit ORDER BY id DESC LIMIT 300")
            return self._tra(200, {"audit": [dict(x) for x in ds]})
        return self._tra(404, {"loi": "không có đường này"})

    # ---------- tenant ----------
    def _api_tenant(self, duong, method, nc, ts):
        tenant_id = nc.tenant_id

        # --- thông tin tenant hiện tại ---
        if duong == "/api/v2/tenant" and method == "GET":
            self._can(nc, "tenant.xem")
            t = csdl.mot("SELECT t.*, g.ten ten_goi FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id"
                         " WHERE t.id=?", (tenant_id,))
            return self._tra(200, {"tenant": dict(t)})
        if duong == "/api/v2/tenant" and method in ("PUT", "POST"):
            self._can(nc, "tenant.sua")
            ten = (self._doc_json().get("ten") or "").strip()
            if not ten:
                return self._tra(400, {"loi": "thiếu tên"})
            csdl.ghi("UPDATE tenants SET ten=?, cap_nhat_luc=? WHERE id=?", (ten, csdl.bay_gio(), tenant_id))
            csdl.audit("sua_tenant", f"tenant:{tenant_id}", f"ten={ten}",
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, {"ok": True})

        # --- membership ---
        if duong == "/api/v2/memberships" and method == "GET":
            self._can(nc, "tenant.membership.xem")
            ds = csdl.nhieu(
                "SELECT m.id, m.user_id, m.role, m.trang_thai, m.tao_luc,"
                " u.ten_dang_nhap, u.ho_ten, u.trang_thai tt_user"
                " FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                " WHERE m.tenant_id=? ORDER BY m.id", (tenant_id,))
            return self._tra(200, {"memberships": [dict(x) for x in ds]})
        if duong == "/api/v2/memberships" and method == "POST":
            # Mời/thêm thành viên: user đã có thì chỉ thêm membership (một user nhiều tenant)
            self._can(nc, "tenant.membership.quan_ly")
            d = self._doc_json()
            role = d.get("role", "")
            cho_phep = quyen.CAP_DUOC.get(nc.role, ())
            if role not in cho_phep:
                return self._tra(403, {"loi": f"vai trò {nc.role} chỉ được cấp: {', '.join(cho_phep) or 'không gì'}"})
            ten_dn = (d.get("ten_dang_nhap") or "").strip()
            if not ten_dn:
                return self._tra(400, {"loi": "thiếu ten_dang_nhap"})
            billing.kiem_han_muc_nhan_vien(tenant_id)
            u = csdl.mot("SELECT * FROM users WHERE ten_dang_nhap=?", (ten_dn,))
            if u:
                u_id = u["id"]
                if csdl.mot("SELECT 1 x FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
                            (u_id, tenant_id)):
                    return self._tra(400, {"loi": "người này đã là thành viên"})
            else:
                if len(d.get("mat_khau", "")) < 8:
                    return self._tra(400, {"loi": "user mới cần mat_khau ≥ 8 ký tự"})
                u_id = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                                " VALUES (?,?,?,?)",
                                (ten_dn, bao_mat.bam_mat_khau(d["mat_khau"]), d.get("ho_ten", ""),
                                 csdl.bay_gio())).lastrowid
            mid = csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, moi_boi, tao_luc)"
                           " VALUES (?,?,?,?,?)",
                           (u_id, tenant_id, role, nc.user_id, csdl.bay_gio())).lastrowid
            csdl.audit("them_membership", f"membership:{mid}", f"user {ten_dn} → {role}",
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(201, {"membership_id": mid, "user_id": u_id})
        m = re.fullmatch(r"/api/v2/memberships/(\d+)", duong)
        if m and method in ("PUT", "POST", "DELETE"):
            self._can(nc, "tenant.membership.quan_ly")
            mem = csdl.mot("SELECT * FROM tenant_memberships WHERE id=? AND tenant_id=?",
                           (int(m.group(1)), tenant_id))
            if not mem:
                return self._tra(404, {"loi": "không có thành viên này trong doanh nghiệp"})
            if mem["role"] == "TENANT_OWNER":
                return self._tra(403, {"loi": "không thao tác được trên TENANT_OWNER"})
            if mem["user_id"] == nc.user_id:
                return self._tra(403, {"loi": "không tự đổi vai trò/vô hiệu chính mình"})
            if method == "DELETE":
                csdl.ghi("DELETE FROM tenant_memberships WHERE id=?", (mem["id"],))
                bao_mat.thu_hoi_moi_phien(mem["user_id"])
                csdl.audit("xoa_membership", f"membership:{mem['id']}", "",
                           tenant_id=tenant_id, user_id=nc.user_id)
                return self._tra(200, {"ok": True})
            d = self._doc_json()
            if "role" in d:
                cho_phep = quyen.CAP_DUOC.get(nc.role, ())
                if d["role"] not in cho_phep:
                    csdl.audit("doi_vai_tro", f"membership:{mem['id']}", f"thử cấp {d['role']}",
                               tenant_id=tenant_id, user_id=nc.user_id, ket_qua="tu_choi")
                    return self._tra(403, {"loi": f"vai trò {nc.role} chỉ được cấp: {', '.join(cho_phep) or 'không gì'}"})
                csdl.ghi("UPDATE tenant_memberships SET role=? WHERE id=?", (d["role"], mem["id"]))
                csdl.audit("doi_vai_tro", f"membership:{mem['id']}", f"→ {d['role']}",
                           tenant_id=tenant_id, user_id=nc.user_id)
            if "trang_thai" in d and d["trang_thai"] in ("hoat_dong", "vo_hieu"):
                csdl.ghi("UPDATE tenant_memberships SET trang_thai=? WHERE id=?",
                         (d["trang_thai"], mem["id"]))
                if d["trang_thai"] == "vo_hieu":
                    bao_mat.thu_hoi_moi_phien(mem["user_id"])
                csdl.audit("doi_trang_thai_membership", f"membership:{mem['id']}", d["trang_thai"],
                           tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, {"ok": True})

        # --- khách hàng ---
        if duong == "/api/v2/khach-hang" and method == "GET":
            self._can(nc, "tenant.khach.xem")
            ds = csdl.nhieu("SELECT * FROM khach_hang WHERE tenant_id=? ORDER BY id DESC LIMIT 500",
                            (tenant_id,))
            return self._tra(200, {"khach_hang": [dict(x) for x in ds]})
        if duong == "/api/v2/khach-hang" and method == "POST":
            self._can(nc, "tenant.khach.ghi")
            d = self._doc_json()
            if not (d.get("ten") or "").strip():
                return self._tra(400, {"loi": "thiếu tên khách"})
            con = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, ghi_chu, tao_luc)"
                           " VALUES (?,?,?,?,?,?)",
                           (tenant_id, d["ten"].strip(), d.get("sdt", ""), d.get("dia_chi", ""),
                            d.get("ghi_chu", ""), csdl.bay_gio()))
            return self._tra(201, {"id": con.lastrowid})
        m = re.fullmatch(r"/api/v2/khach-hang/(\d+)", duong)
        if m and method == "GET":
            self._can(nc, "tenant.khach.xem")
            kh = csdl.mot("SELECT * FROM khach_hang WHERE id=? AND tenant_id=?",
                          (int(m.group(1)), tenant_id))
            if not kh:
                return self._tra(404, {"loi": "không có khách hàng này"})
            return self._tra(200, {"khach_hang": dict(kh)})

        # --- hãng & tài khoản hãng ---
        if duong == "/api/v2/hang":
            self._can(nc, "tenant.hang.xem")
            ds = csdl.nhieu("SELECT * FROM carrier_providers ORDER BY ma")
            return self._tra(200, {"hang": [
                {"ma": x["ma"], "ten": x["ten"], "capabilities": json.loads(x["capabilities_json"]),
                 "live_mo": bool(x["live_mo"])} for x in ds]})
        if duong == "/api/v2/tai-khoan-hang" and method == "GET":
            self._can(nc, "tenant.hang.xem")
            ds = csdl.nhieu("SELECT id, hang, ten, moi_truong, credentials_duoi, credentials_doi_luc,"
                            " webhook_ma, kich_hoat, tao_luc FROM carrier_accounts"
                            " WHERE tenant_id=? ORDER BY id", (tenant_id,))
            return self._tra(200, {"tai_khoan": [dict(x) for x in ds]})  # KHÔNG trả secret
        if duong == "/api/v2/tai-khoan-hang" and method == "POST":
            self._can(nc, "tenant.hang.quan_ly")
            d = self._doc_json()
            if not csdl.mot("SELECT ma FROM carrier_providers WHERE ma=?", (d.get("hang"),)):
                return self._tra(400, {"loi": "hãng chưa có adapter"})
            if d.get("moi_truong", "mock") != "mock":
                return self._tra(403, {"loi": "môi trường sandbox/production đang khóa — chờ Owner duyệt (BLOCKED)"})
            billing.kiem_han_muc_tai_khoan_hang(tenant_id)
            import secrets as _s
            wh_secret, wh_ma = _s.token_urlsafe(24), _s.token_urlsafe(12)
            cred_mh, duoi = bao_mat.ma_hoa_cred(d.get("credentials") or {}, tenant_id, d["hang"])
            con = csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                           " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
                           " VALUES (?,?,?,?,?,?,?,?,?)",
                           (tenant_id, d["hang"], d.get("ten", d["hang"]), "mock", cred_mh, duoi,
                            wh_ma, bao_mat.ma_hoa_wh(wh_secret, wh_ma), csdl.bay_gio()))
            csdl.audit("tao_tai_khoan_hang", f"carrier_account:{con.lastrowid}", d["hang"],
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(201, {"id": con.lastrowid, "webhook_ma": wh_ma,
                                   "webhook_secret_mot_lan": wh_secret,
                                   "webhook_url": f"/api/v2/webhook/nhan/{wh_ma}"})
        m = re.fullmatch(r"/api/v2/tai-khoan-hang/(\d+)/(khoa|mo|rotate|revoke)", duong)
        if m and method == "POST":
            self._can(nc, "tenant.hang.quan_ly")
            tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=? AND tenant_id=?",
                          (int(m.group(1)), tenant_id))
            if not tk:
                return self._tra(404, {"loi": "không có tài khoản hãng này"})
            viec = m.group(2)
            ra = {"ok": True}
            if viec == "rotate":
                cred_mh, duoi = bao_mat.ma_hoa_cred(
                    self._doc_json().get("credentials") or {}, tenant_id, tk["hang"])
                csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=?, credentials_duoi=?,"
                         " credentials_doi_luc=? WHERE id=?", (cred_mh, duoi, csdl.bay_gio(), tk["id"]))
            elif viec == "revoke":
                cred_mh, _ = bao_mat.ma_hoa_cred({}, tenant_id, tk["hang"])
                csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=?, credentials_duoi='',"
                         " kich_hoat=0, credentials_doi_luc=? WHERE id=?",
                         (cred_mh, csdl.bay_gio(), tk["id"]))
            else:
                csdl.ghi("UPDATE carrier_accounts SET kich_hoat=? WHERE id=?",
                         (0 if viec == "khoa" else 1, tk["id"]))
            csdl.audit(f"tai_khoan_hang_{viec}", f"carrier_account:{tk['id']}", "",
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, ra)

        # --- đơn hàng ---
        if duong == "/api/v2/don" and method == "GET":
            self._can(nc, "tenant.don.xem")
            dk, tsq = ["tenant_id=?"], [tenant_id]
            if ts.get("trang_thai"):
                dk.append("trang_thai=?"); tsq.append(ts["trang_thai"])
            if ts.get("q"):
                dk.append("(ma_don LIKE ? OR ma_van_don LIKE ? OR nguoi_nhan_ten LIKE ? OR nguoi_nhan_sdt LIKE ?)")
                tsq += [f"%{ts['q']}%"] * 4
            tsq.append(min(int(ts.get("gioi_han", "100")), 500))
            ds = csdl.nhieu(f"SELECT * FROM don_hang WHERE {' AND '.join(dk)} ORDER BY id DESC LIMIT ?", tsq)
            return self._tra(200, {"don": [dict(x) for x in ds]})
        if duong == "/api/v2/don/xuat-csv" and method == "GET":
            self._can(nc, "tenant.don.xem")
            ds = csdl.nhieu("SELECT * FROM don_hang WHERE tenant_id=? ORDER BY id DESC LIMIT 2000",
                            (tenant_id,))
            cot = ["ma_don", "trang_thai", "trang_thai_giao", "ma_van_don", "nguoi_nhan_ten",
                   "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram", "cod",
                   "phi_van_chuyen", "tao_luc"]
            def o(v):
                return '"' + str(v if v is not None else "").replace('"', '""') + '"'
            csv = "﻿" + ",".join(cot) + "\n" + "\n".join(",".join(o(d[c]) for c in cot) for d in ds)
            body = csv.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", "attachment; filename=don-hang.csv")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if duong == "/api/v2/don" and method == "POST":
            self._can(nc, "tenant.don.ghi")
            don, trung = don_hang.tao_don(tenant_id, nc.user_id, self._doc_json(),
                                          idem_key=self.headers.get("Idempotency-Key"))
            return self._tra(200 if trung else 201, {"don": don, "idempotent_trung": trung})
        m = re.fullmatch(r"/api/v2/don/(\d+)", duong)
        if m:
            don_id = int(m.group(1))
            if method == "GET":
                self._can(nc, "tenant.don.xem")
                don = don_hang.lay_don(tenant_id, don_id)
                if not don:
                    return self._tra(404, {"loi": "không có đơn này"})
                ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don_id,))
                return self._tra(200, {"don": dict(don), "lich_su": [dict(x) for x in ls]})
            if method in ("PUT", "POST"):
                self._can(nc, "tenant.don.ghi")
                return self._tra(200, {"don": don_hang.sua_don(tenant_id, nc.user_id, don_id,
                                                               self._doc_json())})
            if method == "DELETE":
                self._can(nc, "tenant.don.duyet")
                return self._tra(200, {"don": don_hang.huy_don(tenant_id, nc.user_id, don_id)})
        m = re.fullmatch(r"/api/v2/don/(\d+)/(duyet|gui|huy)", duong)
        if m and method == "POST":
            don_id, viec = int(m.group(1)), m.group(2)
            self._can(nc, "tenant.don.duyet")
            if viec == "duyet":
                don = don_hang.duyet_don(tenant_id, nc.user_id, don_id)
            elif viec == "gui":
                don = don_hang.gui_don(tenant_id, nc.user_id, don_id,
                                       self._doc_json().get("carrier_account_id"))
            else:
                don = don_hang.huy_don(tenant_id, nc.user_id, don_id)
            csdl.audit(f"don_{viec}", f"don:{don_id}", "", tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, {"don": don})

        # --- import ---
        if duong == "/api/v2/import" and method == "GET":
            self._can(nc, "tenant.don.xem")
            ds = csdl.nhieu("SELECT * FROM import_batch WHERE tenant_id=? ORDER BY id DESC LIMIT 100",
                            (tenant_id,))
            return self._tra(200, {"batch": [dict(x) for x in ds]})
        if duong == "/api/v2/import" and method == "POST":
            self._can(nc, "tenant.import.ghi")
            d = self._doc_json()
            if not d.get("ten_file") or not d.get("noi_dung_base64"):
                return self._tra(400, {"loi": "cần ten_file và noi_dung_base64"})
            try:
                du_lieu = base64.b64decode(d["noi_dung_base64"])
            except Exception:
                return self._tra(400, {"loi": "noi_dung_base64 không hợp lệ"})
            batch_id = nhap_file.tao_batch(tenant_id, nc.user_id, d["ten_file"], du_lieu)
            csdl.audit("import_upload", f"batch:{batch_id}", d["ten_file"],
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(201, {"batch_id": batch_id})
        m = re.fullmatch(r"/api/v2/import/(\d+)", duong)
        if m and method == "GET":
            self._can(nc, "tenant.don.xem")
            b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?",
                         (int(m.group(1)), tenant_id))
            if not b:
                return self._tra(404, {"loi": "không có batch này"})
            ds = csdl.nhieu("SELECT * FROM import_dong WHERE batch_id=? ORDER BY stt", (b["id"],))
            dong = []
            for x in ds:
                d2 = dict(x)
                d2["du_lieu"] = json.loads(d2.pop("du_lieu_json"))
                dong.append(d2)
            return self._tra(200, {"batch": dict(b), "dong": dong})
        m = re.fullmatch(r"/api/v2/import/dong/(\d+)", duong)
        if m and method in ("PUT", "POST"):
            self._can(nc, "tenant.import.ghi")
            return self._tra(200, nhap_file.sua_dong(tenant_id, int(m.group(1)), self._doc_json()))
        m = re.fullmatch(r"/api/v2/import/(\d+)/xuat-csv", duong)
        if m and method == "GET":
            self._can(nc, "tenant.don.xem")
            csv = nhap_file.xuat_csv(tenant_id, int(m.group(1)))   # đã làm sạch chống formula injection
            body = csv.encode()
            # Tên file do NGƯỜI DÙNG đặt — tuyệt đối không ghép thẳng vào header (CRLF/quote injection).
            ten_an_toan = "import-batch-%d.csv" % int(m.group(1))
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{ten_an_toan}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        m = re.fullmatch(r"/api/v2/import/dong/(\d+)/xac-nhan", duong)
        if m and method == "POST":
            self._can(nc, "tenant.import.ghi")
            kq = nhap_file.xac_nhan_dong(tenant_id, nc.user_id, int(m.group(1)))
            csdl.audit("import_xac_nhan_dong", f"import_dong:{m.group(1)}", "NEEDS_REVIEW → READY",
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, kq if isinstance(kq, dict) else {"ok": True})
        m = re.fullmatch(r"/api/v2/import/(\d+)/duyet", duong)
        if m and method == "POST":
            self._can(nc, "tenant.import.duyet")
            d = self._doc_json()
            ng = d.get("nguoi_gui") or {}
            if not all((ng.get(k) or "").strip() for k in ("ten", "sdt", "dia_chi")):
                return self._tra(400, {"loi": "cần nguoi_gui {ten, sdt, dia_chi}"})
            kq = nhap_file.duyet_batch(tenant_id, nc.user_id, int(m.group(1)), d.get("dong_ids") or [], ng)
            return self._tra(200, kq)

        # --- webhook monitor ---
        if duong == "/api/v2/webhook/su-kien" and method == "GET":
            self._can(nc, "tenant.webhook.xem")
            ds = csdl.nhieu(
                "SELECT s.id, s.event_id, s.nhan_luc, s.trang_thai, s.so_lan_thu, s.loi_cuoi,"
                " c.hang, c.ten ten_tk FROM wh_su_kien s JOIN carrier_accounts c"
                " ON c.id=s.carrier_account_id WHERE c.tenant_id=? ORDER BY s.id DESC LIMIT 200",
                (tenant_id,))
            return self._tra(200, {"su_kien": [dict(x) for x in ds]})
        m = re.fullmatch(r"/api/v2/webhook/su-kien/(\d+)/replay", duong)
        if m and method == "POST":
            self._can(nc, "tenant.webhook.replay")
            sk = csdl.mot("SELECT s.*, c.tenant_id t FROM wh_su_kien s JOIN carrier_accounts c"
                          " ON c.id=s.carrier_account_id WHERE s.id=?", (int(m.group(1)),))
            if not sk or sk["t"] != tenant_id:
                return self._tra(404, {"loi": "không có sự kiện này"})
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='moi', so_lan_thu=0, loi_cuoi=NULL WHERE id=?",
                     (sk["id"],))
            webhook.nap(sk["id"])
            csdl.audit("webhook_replay", f"su_kien:{sk['id']}", f"trạng thái trước: {sk['trang_thai']}",
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(202, {"ok": True})

        # --- polling hành trình (fallback khi hãng không đẩy webhook) ---
        if duong == "/api/v2/polling/chay" and method == "POST":
            self._can(nc, "tenant.hang.quan_ly")
            d = self._doc_json()
            tk = polling.chay_mot_luot(tenant_id,
                                       chi_hang_khong_webhook=bool(d.get("chi_hang_khong_webhook")))
            csdl.audit("polling_chay_tay", f"tenant:{tenant_id}", json.dumps(tk, ensure_ascii=False),
                       tenant_id=tenant_id, user_id=nc.user_id)
            return self._tra(200, tk)

        # --- billing / audit / ai ---
        if duong == "/api/v2/billing":
            self._can(nc, "tenant.billing.xem")
            return self._tra(200, {"goi": dict(billing.goi_cua_tenant(tenant_id)),
                                   "usage": billing.usage_hien_tai(tenant_id)})
        if duong == "/api/v2/audit":
            self._can(nc, "tenant.audit.xem")
            ds = csdl.nhieu("SELECT * FROM audit WHERE tenant_id=? ORDER BY id DESC LIMIT 200", (tenant_id,))
            return self._tra(200, {"audit": [dict(x) for x in ds]})
        m = re.fullmatch(r"/api/v2/ai/(chuan-hoa-dia-chi|phat-hien-bat-thuong|goi-y-hang)", duong)
        if m and method == "POST":
            self._can(nc, "tenant.ai.dung")
            d = self._doc_json()
            viec = m.group(1)
            if viec == "chuan-hoa-dia-chi":
                return self._tra(200, ai_gateway.chuan_hoa_dia_chi(tenant_id, d.get("dia_chi", "")))
            if viec == "phat-hien-bat-thuong":
                return self._tra(200, ai_gateway.phat_hien_bat_thuong(tenant_id, d))
            return self._tra(200, ai_gateway.goi_y_hang(tenant_id, d))

        return self._tra(404, {"loi": "không có đường này"})


def chay(cong=cau_hinh.CONG_MAC_DINH):
    csdl.mo()
    pb = csdl.phien_ban_hien_tai()
    if pb < csdl.PHIEN_BAN_SCHEMA:
        print(f"[hub] DỪNG: CSDL ở schema v{pb}, mã nguồn cần v{csdl.PHIEN_BAN_SCHEMA}.")
        print("[hub] Chạy migration trước: python3 app/migrate.py")
        raise SystemExit(3)
    quyen.seed()
    import khoi_tao
    khoi_tao.seed_providers()   # capability adapter đổi thì CSDL phải theo (vd J&T webhook)
    webhook.khoi_dong()
    sv = ThreadingHTTPServer(("127.0.0.1", cong), BoXuLy)
    print(f"[hub] VIP Express Hub SaaS (local) chạy tại http://127.0.0.1:{cong} — Ctrl+C để dừng")
    print(f"[hub] Giao diện quản trị: http://127.0.0.1:{cong}/admin/")
    try:
        sv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        webhook.dung()
        sv.server_close()


if __name__ == "__main__":
    chay(int(sys.argv[1]) if len(sys.argv) > 1 else cau_hinh.CONG_MAC_DINH)
