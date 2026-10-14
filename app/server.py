# VIP Express Hub — backend Multi-Tenant SaaS (local-first), cổng 8897.
# Stdlib + SQLite. Bind 127.0.0.1. Phục vụ cả static (admin/, pages/, assets/) lẫn API /api/v2/*.
# Luật cứng: tenant lấy từ PHIÊN đăng nhập — không bao giờ tin tenant_id từ client.
import base64
import json
import mimetypes
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import adapter
import ai_gateway
import bao_mat
import billing
import cau_hinh
import csdl
import don_hang
import nhap_file
import webhook

GOC_TINH = cau_hinh.THU_MUC_GOC  # phục vụ file tĩnh từ gốc dự án


def _json(obj):
    return json.dumps(obj, ensure_ascii=False, default=str).encode()


class BoXuLy(BaseHTTPRequestHandler):
    server_version = "VIPExpressHub/0.2-SaaS"

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
        cookie = self.headers.get("Cookie", "")
        m = re.search(r"(?:^|;\s*)phien=([^;]+)", cookie)
        return m.group(1) if m else None

    def _nguoi_dung(self):
        return bao_mat.phien_hien_tai(self._token())

    def _can(self, hanh_dong, u):
        if not bao_mat.co_quyen(u, hanh_dong):
            raise don_hang.LoiNghiepVu("không đủ quyền", 403)

    def _can_csrf(self):
        # Mutating API phải mang header tùy biến — form chéo nguồn không gửi được header này.
        if self.headers.get("X-Requested-With") != "VIPHub":
            raise don_hang.LoiNghiepVu("thiếu header X-Requested-With: VIPHub (chống CSRF)", 403)

    def _truy_van(self):
        _, _, q = self.path.partition("?")
        ts = {}
        for cap in q.split("&"):
            if "=" in cap:
                k, v = cap.split("=", 1)
                from urllib.parse import unquote_plus
                ts[k] = unquote_plus(v)
        return ts

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
    def do_GET(self):
        try:
            duong = self.path.split("?")[0]
            if not duong.startswith("/api/"):
                return self._phuc_vu_tinh(duong)
            return self._api(duong, "GET")
        except don_hang.LoiNghiepVu as e:
            self._tra(e.ma, {"loi": str(e)})
        except billing.VuotHanMuc as e:
            self._tra(402, {"loi": f"vượt hạn mức gói: {e}"})
        except Exception as e:
            self._tra(500, {"loi": f"lỗi hệ thống: {type(e).__name__}"})
            sys.stderr.write(f"[hub] LOI 500: {type(e).__name__}: {e}\n")

    def do_POST(self):
        try:
            return self._api(self.path.split("?")[0], "POST")
        except don_hang.LoiNghiepVu as e:
            self._tra(e.ma, {"loi": str(e)})
        except billing.VuotHanMuc as e:
            self._tra(402, {"loi": f"vượt hạn mức gói: {e}"})
        except PermissionError as e:
            self._tra(403, {"loi": str(e)})
        except Exception as e:
            self._tra(500, {"loi": f"lỗi hệ thống: {type(e).__name__}"})
            sys.stderr.write(f"[hub] LOI 500: {type(e).__name__}: {e}\n")

    def do_PUT(self):
        self.do_POST()

    # ---------- API ----------
    def _api(self, duong, method):
        # --- webhook ingest: KHÔNG cần phiên, xác thực bằng chữ ký account ---
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

        # --- auth ---
        if duong == "/api/v2/auth/dang-nhap" and method == "POST":
            self._can_csrf()
            d = self._doc_json()
            token, kq = bao_mat.dang_nhap(d.get("ten_dang_nhap", ""), d.get("mat_khau", ""),
                                          self.client_address[0])
            if token is None:
                return self._tra(401, {"loi": kq})
            cookie = f"phien={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={cau_hinh.PHIEN_SONG_GIO * 3600}"
            return self._tra(200, {"ok": True, "vai_tro": kq["vai_tro"], "ho_ten": kq["ho_ten"]}, cookie=cookie)

        u = self._nguoi_dung()
        if u is None:
            return self._tra(401, {"loi": "chưa đăng nhập hoặc phiên hết hạn"})
        if method in ("POST", "PUT"):
            self._can_csrf()
        ts = self._truy_van()
        tenant_id = u["tenant_id"]

        if duong == "/api/v2/auth/dang-xuat" and method == "POST":
            bao_mat.dang_xuat(self._token())
            return self._tra(200, {"ok": True}, cookie="phien=; Max-Age=0; Path=/")
        if duong == "/api/v2/auth/toi":
            goi = billing.goi_cua_tenant(tenant_id) if tenant_id else None
            t = csdl.mot("SELECT * FROM tenants WHERE id=?", (tenant_id,)) if tenant_id else None
            return self._tra(200, {"id": u["id"], "ten_dang_nhap": u["ten_dang_nhap"], "ho_ten": u["ho_ten"],
                                   "vai_tro": u["vai_tro"], "tenant": dict(t) if t else None,
                                   "goi": dict(goi) if goi else None})
        if duong == "/api/v2/auth/doi-mat-khau" and method == "POST":
            d = self._doc_json()
            if not bao_mat.kiem_mat_khau(d.get("mat_khau_cu", ""), u["mat_khau_hash"]):
                return self._tra(400, {"loi": "mật khẩu cũ sai"})
            if len(d.get("mat_khau_moi", "")) < 8:
                return self._tra(400, {"loi": "mật khẩu mới phải từ 8 ký tự"})
            csdl.ghi("UPDATE users SET mat_khau_hash=?, doi_mat_khau_luc=? WHERE id=?",
                     (bao_mat.bam_mat_khau(d["mat_khau_moi"]), csdl.bay_gio(), u["id"]))
            bao_mat.thu_hoi_moi_phien(u["id"], tru_token=self._token())
            csdl.audit("doi_mat_khau", f"user:{u['id']}", "thu hồi các phiên khác",
                       tenant_id=tenant_id, user_id=u["id"])
            return self._tra(200, {"ok": True, "ghi_chu": "các phiên khác đã bị thu hồi"})
        if duong == "/api/v2/auth/thu-hoi-phien" and method == "POST":
            bao_mat.thu_hoi_moi_phien(u["id"], tru_token=self._token())
            csdl.audit("thu_hoi_phien", f"user:{u['id']}", "", tenant_id=tenant_id, user_id=u["id"])
            return self._tra(200, {"ok": True})

        # --- platform ---
        if duong.startswith("/api/v2/platform/"):
            if u["vai_tro"] not in cau_hinh.VAI_TRO_PLATFORM:
                return self._tra(403, {"loi": "chỉ dành cho quản trị nền tảng"})
            return self._api_platform(duong, method, u)

        # --- tenant APIs: bắt buộc là người của một tenant ---
        if tenant_id is None:
            return self._tra(403, {"loi": "API này dành cho người dùng doanh nghiệp (tenant)"})
        return self._api_tenant(duong, method, u, tenant_id, ts)

    # ---------- platform ----------
    def _api_platform(self, duong, method, u):
        if duong == "/api/v2/platform/tenants" and method == "GET":
            self._can("platform.tenant.quan_ly", u)
            ds = csdl.nhieu("SELECT t.*, g.ten ten_goi FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id ORDER BY t.id")
            return self._tra(200, {"tenants": [dict(x) for x in ds]})
        if duong == "/api/v2/platform/tenants" and method == "POST":
            self._can("platform.tenant.quan_ly", u)
            d = self._doc_json()
            if not d.get("ten") or not d.get("owner_ten_dang_nhap") or len(d.get("owner_mat_khau", "")) < 8:
                return self._tra(400, {"loi": "cần ten, owner_ten_dang_nhap, owner_mat_khau (≥8 ký tự)"})
            goi_id = d.get("goi_id", "free")
            if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
                return self._tra(400, {"loi": "gói không tồn tại"})
            if csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (d["owner_ten_dang_nhap"],)):
                return self._tra(400, {"loi": "tên đăng nhập đã tồn tại"})
            con = csdl.ghi("INSERT INTO tenants (ten, goi_id, tao_luc) VALUES (?,?,?)",
                           (d["ten"], goi_id, csdl.bay_gio()))
            t_id = con.lastrowid
            csdl.ghi("INSERT INTO users (tenant_id, ten_dang_nhap, mat_khau_hash, ho_ten, vai_tro, tao_luc)"
                     " VALUES (?,?,?,?,?,?)",
                     (t_id, d["owner_ten_dang_nhap"], bao_mat.bam_mat_khau(d["owner_mat_khau"]),
                      d.get("owner_ho_ten", "Chủ doanh nghiệp"), "TENANT_OWNER", csdl.bay_gio()))
            csdl.audit("tao_tenant", f"tenant:{t_id}", d["ten"], user_id=u["id"])
            return self._tra(201, {"id": t_id})
        m = re.fullmatch(r"/api/v2/platform/tenants/(\d+)/(khoa|mo|goi)", duong)
        if m and method == "POST":
            self._can("platform.tenant.quan_ly", u)
            t_id, viec = int(m.group(1)), m.group(2)
            if not csdl.mot("SELECT id FROM tenants WHERE id=?", (t_id,)):
                return self._tra(404, {"loi": "không có tenant"})
            if viec == "goi":
                self._can("platform.goi.quan_ly", u)
                goi_id = self._doc_json().get("goi_id")
                if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
                    return self._tra(400, {"loi": "gói không tồn tại"})
                csdl.ghi("UPDATE tenants SET goi_id=? WHERE id=?", (goi_id, t_id))
            else:
                csdl.ghi("UPDATE tenants SET trang_thai=? WHERE id=?",
                         ("khoa" if viec == "khoa" else "hoat_dong", t_id))
            csdl.audit(f"tenant_{viec}", f"tenant:{t_id}", "", user_id=u["id"])
            return self._tra(200, {"ok": True})
        if duong == "/api/v2/platform/goi":
            return self._tra(200, {"goi": [dict(x) for x in csdl.nhieu("SELECT * FROM goi_dich_vu")]})
        if duong == "/api/v2/platform/audit":
            self._can("platform.audit.xem", u)
            ds = csdl.nhieu("SELECT * FROM audit ORDER BY id DESC LIMIT 300")
            return self._tra(200, {"audit": [dict(x) for x in ds]})
        return self._tra(404, {"loi": "không có đường này"})

    # ---------- tenant ----------
    def _api_tenant(self, duong, method, u, tenant_id, ts):
        # --- users ---
        if duong == "/api/v2/users" and method == "GET":
            self._can("tenant.user.quan_ly", u)
            ds = csdl.nhieu("SELECT id, ten_dang_nhap, ho_ten, vai_tro, trang_thai, tao_luc FROM users"
                            " WHERE tenant_id=? ORDER BY id", (tenant_id,))
            return self._tra(200, {"users": [dict(x) for x in ds]})
        if duong == "/api/v2/users" and method == "POST":
            self._can("tenant.user.quan_ly", u)
            d = self._doc_json()
            vt = d.get("vai_tro", "")
            if vt not in ("TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"):
                return self._tra(400, {"loi": "vai_tro phải là TENANT_ADMIN/TENANT_STAFF/TENANT_VIEWER"})
            if vt == "TENANT_ADMIN" and u["vai_tro"] != "TENANT_OWNER":
                return self._tra(403, {"loi": "chỉ TENANT_OWNER được tạo TENANT_ADMIN"})
            if not d.get("ten_dang_nhap") or len(d.get("mat_khau", "")) < 8:
                return self._tra(400, {"loi": "cần ten_dang_nhap và mat_khau ≥ 8 ký tự"})
            billing.kiem_han_muc_nhan_vien(tenant_id)
            if csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (d["ten_dang_nhap"],)):
                return self._tra(400, {"loi": "tên đăng nhập đã tồn tại"})
            con = csdl.ghi("INSERT INTO users (tenant_id, ten_dang_nhap, mat_khau_hash, ho_ten, vai_tro, tao_luc)"
                           " VALUES (?,?,?,?,?,?)",
                           (tenant_id, d["ten_dang_nhap"], bao_mat.bam_mat_khau(d["mat_khau"]),
                            d.get("ho_ten", ""), vt, csdl.bay_gio()))
            csdl.audit("tao_user", f"user:{con.lastrowid}", vt, tenant_id=tenant_id, user_id=u["id"])
            return self._tra(201, {"id": con.lastrowid})
        m = re.fullmatch(r"/api/v2/users/(\d+)/(khoa|mo|thu-hoi-phien)", duong)
        if m and method == "POST":
            self._can("tenant.user.quan_ly", u)
            muc_tieu = csdl.mot("SELECT * FROM users WHERE id=? AND tenant_id=?", (int(m.group(1)), tenant_id))
            if not muc_tieu:
                return self._tra(404, {"loi": "không có người dùng này"})
            if muc_tieu["vai_tro"] == "TENANT_OWNER":
                return self._tra(403, {"loi": "không thao tác được trên TENANT_OWNER"})
            viec = m.group(2)
            if viec == "thu-hoi-phien":
                bao_mat.thu_hoi_moi_phien(muc_tieu["id"])
            else:
                csdl.ghi("UPDATE users SET trang_thai=?, so_lan_sai=0 WHERE id=?",
                         ("khoa" if viec == "khoa" else "hoat_dong", muc_tieu["id"]))
                if viec == "khoa":
                    bao_mat.thu_hoi_moi_phien(muc_tieu["id"])
            csdl.audit(f"user_{viec}", f"user:{muc_tieu['id']}", "", tenant_id=tenant_id, user_id=u["id"])
            return self._tra(200, {"ok": True})

        # --- khách hàng ---
        if duong == "/api/v2/khach-hang" and method == "GET":
            self._can("tenant.khach.xem", u)
            ds = csdl.nhieu("SELECT * FROM khach_hang WHERE tenant_id=? ORDER BY id DESC LIMIT 500", (tenant_id,))
            return self._tra(200, {"khach_hang": [dict(x) for x in ds]})
        if duong == "/api/v2/khach-hang" and method == "POST":
            self._can("tenant.khach.ghi", u)
            d = self._doc_json()
            if not d.get("ten", "").strip():
                return self._tra(400, {"loi": "thiếu tên khách"})
            con = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, ghi_chu, tao_luc) VALUES (?,?,?,?,?,?)",
                           (tenant_id, d["ten"].strip(), d.get("sdt", ""), d.get("dia_chi", ""),
                            d.get("ghi_chu", ""), csdl.bay_gio()))
            return self._tra(201, {"id": con.lastrowid})

        # --- hãng & tài khoản hãng ---
        if duong == "/api/v2/hang":
            self._can("tenant.hang.xem", u)
            return self._tra(200, {"hang": adapter.danh_sach_hang()})
        if duong == "/api/v2/tai-khoan-hang" and method == "GET":
            self._can("tenant.hang.xem", u)
            ds = csdl.nhieu("SELECT id, hang, ten, moi_truong, credentials_duoi, webhook_ma, kich_hoat, tao_luc"
                            " FROM carrier_accounts WHERE tenant_id=? ORDER BY id", (tenant_id,))
            return self._tra(200, {"tai_khoan": [dict(x) for x in ds]})  # KHÔNG trả secret
        if duong == "/api/v2/tai-khoan-hang" and method == "POST":
            self._can("tenant.hang.quan_ly", u)
            d = self._doc_json()
            if d.get("hang") not in adapter.danh_sach_hang():
                return self._tra(400, {"loi": "hãng chưa có adapter"})
            if d.get("moi_truong", "mock") != "mock":
                return self._tra(403, {"loi": "môi trường sandbox/production đang khóa — chờ Owner duyệt (BLOCKED)"})
            billing.kiem_han_muc_tai_khoan_hang(tenant_id)
            import secrets as _s
            cred = d.get("credentials") or {}
            cred_mh, duoi = bao_mat.luu_credentials(cred)
            wh_secret = _s.token_urlsafe(24)
            wh_ma = _s.token_urlsafe(12)
            con = csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
                           " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
                           (tenant_id, d["hang"], d.get("ten", d["hang"]), "mock", cred_mh, duoi,
                            wh_ma, bao_mat.ma_hoa(wh_secret), csdl.bay_gio()))
            csdl.audit("tao_tai_khoan_hang", f"carrier_account:{con.lastrowid}", d["hang"],
                       tenant_id=tenant_id, user_id=u["id"])
            # webhook_secret chỉ trả MỘT LẦN lúc tạo (để cấu hình phía hãng/mô phỏng), không xem lại được
            return self._tra(201, {"id": con.lastrowid, "webhook_ma": wh_ma, "webhook_secret_mot_lan": wh_secret,
                                   "webhook_url": f"/api/v2/webhook/nhan/{wh_ma}"})
        m = re.fullmatch(r"/api/v2/tai-khoan-hang/(\d+)/(khoa|mo|doi-credentials)", duong)
        if m and method == "POST":
            self._can("tenant.hang.quan_ly", u)
            tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=? AND tenant_id=?", (int(m.group(1)), tenant_id))
            if not tk:
                return self._tra(404, {"loi": "không có tài khoản hãng này"})
            viec = m.group(2)
            if viec == "doi-credentials":
                cred_mh, duoi = bao_mat.luu_credentials(self._doc_json().get("credentials") or {})
                csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=?, credentials_duoi=? WHERE id=?",
                         (cred_mh, duoi, tk["id"]))
            else:
                csdl.ghi("UPDATE carrier_accounts SET kich_hoat=? WHERE id=?", (0 if viec == "khoa" else 1, tk["id"]))
            csdl.audit(f"tai_khoan_hang_{viec}", f"carrier_account:{tk['id']}", "",
                       tenant_id=tenant_id, user_id=u["id"])
            return self._tra(200, {"ok": True})

        # --- đơn hàng ---
        if duong == "/api/v2/don" and method == "GET":
            self._can("tenant.don.xem", u)
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
            self._can("tenant.don.xem", u)
            ds = csdl.nhieu("SELECT * FROM don_hang WHERE tenant_id=? ORDER BY id DESC LIMIT 2000", (tenant_id,))
            cot = ["ma_don", "trang_thai", "trang_thai_giao", "ma_van_don", "nguoi_nhan_ten", "nguoi_nhan_sdt",
                   "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram", "cod", "phi_van_chuyen", "tao_luc"]
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
            self._can("tenant.don.ghi", u)
            don, trung = don_hang.tao_don(tenant_id, u["id"], self._doc_json(),
                                          idem_key=self.headers.get("Idempotency-Key"))
            return self._tra(200 if trung else 201, {"don": don, "idempotent_trung": trung})
        m = re.fullmatch(r"/api/v2/don/(\d+)", duong)
        if m:
            don_id = int(m.group(1))
            if method == "GET":
                self._can("tenant.don.xem", u)
                don = don_hang.lay_don(tenant_id, don_id)
                if not don:
                    return self._tra(404, {"loi": "không có đơn này"})
                ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don_id,))
                return self._tra(200, {"don": dict(don), "lich_su": [dict(x) for x in ls]})
            if method in ("PUT", "POST"):
                self._can("tenant.don.ghi", u)
                return self._tra(200, {"don": don_hang.sua_don(tenant_id, u["id"], don_id, self._doc_json())})
        m = re.fullmatch(r"/api/v2/don/(\d+)/(duyet|gui|huy)", duong)
        if m and method == "POST":
            don_id, viec = int(m.group(1)), m.group(2)
            if viec == "duyet":
                self._can("tenant.don.duyet", u)
                don = don_hang.duyet_don(tenant_id, u["id"], don_id)
            elif viec == "gui":
                self._can("tenant.don.duyet", u)
                tk_id = self._doc_json().get("carrier_account_id")
                don = don_hang.gui_don(tenant_id, u["id"], don_id, tk_id)
            else:
                self._can("tenant.don.duyet", u)
                don = don_hang.huy_don(tenant_id, u["id"], don_id)
            csdl.audit(f"don_{viec}", f"don:{don_id}", "", tenant_id=tenant_id, user_id=u["id"])
            return self._tra(200, {"don": don})

        # --- import ---
        if duong == "/api/v2/import" and method == "GET":
            self._can("tenant.don.xem", u)
            ds = csdl.nhieu("SELECT * FROM import_batch WHERE tenant_id=? ORDER BY id DESC LIMIT 100", (tenant_id,))
            return self._tra(200, {"batch": [dict(x) for x in ds]})
        if duong == "/api/v2/import" and method == "POST":
            self._can("tenant.import.ghi", u)
            d = self._doc_json()
            if not d.get("ten_file") or not d.get("noi_dung_base64"):
                return self._tra(400, {"loi": "cần ten_file và noi_dung_base64"})
            try:
                du_lieu = base64.b64decode(d["noi_dung_base64"])
            except Exception:
                return self._tra(400, {"loi": "noi_dung_base64 không hợp lệ"})
            batch_id = nhap_file.tao_batch(tenant_id, u["id"], d["ten_file"], du_lieu)
            csdl.audit("import_upload", f"batch:{batch_id}", d["ten_file"], tenant_id=tenant_id, user_id=u["id"])
            return self._tra(201, {"batch_id": batch_id})
        m = re.fullmatch(r"/api/v2/import/(\d+)", duong)
        if m and method == "GET":
            self._can("tenant.don.xem", u)
            b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (int(m.group(1)), tenant_id))
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
            self._can("tenant.import.ghi", u)
            return self._tra(200, nhap_file.sua_dong(tenant_id, int(m.group(1)), self._doc_json()))
        m = re.fullmatch(r"/api/v2/import/(\d+)/duyet", duong)
        if m and method == "POST":
            self._can("tenant.import.duyet", u)
            d = self._doc_json()
            ng = d.get("nguoi_gui") or {}
            if not all(ng.get(k, "").strip() for k in ("ten", "sdt", "dia_chi")):
                return self._tra(400, {"loi": "cần nguoi_gui {ten, sdt, dia_chi}"})
            kq = nhap_file.duyet_batch(tenant_id, u["id"], int(m.group(1)), d.get("dong_ids") or [], ng)
            return self._tra(200, kq)

        # --- webhook monitor (tenant chỉ thấy sự kiện của account MÌNH) ---
        if duong == "/api/v2/webhook/su-kien" and method == "GET":
            self._can("tenant.webhook.xem", u)
            ds = csdl.nhieu(
                "SELECT s.id, s.event_id, s.nhan_luc, s.trang_thai, s.so_lan_thu, s.loi_cuoi, c.hang, c.ten ten_tk"
                " FROM wh_su_kien s JOIN carrier_accounts c ON c.id=s.carrier_account_id"
                " WHERE c.tenant_id=? ORDER BY s.id DESC LIMIT 200", (tenant_id,))
            return self._tra(200, {"su_kien": [dict(x) for x in ds]})
        m = re.fullmatch(r"/api/v2/webhook/su-kien/(\d+)/replay", duong)
        if m and method == "POST":
            self._can("tenant.webhook.replay", u)
            sk = csdl.mot("SELECT s.*, c.tenant_id t FROM wh_su_kien s JOIN carrier_accounts c"
                          " ON c.id=s.carrier_account_id WHERE s.id=?", (int(m.group(1)),))
            if not sk or sk["t"] != tenant_id:
                return self._tra(404, {"loi": "không có sự kiện này"})
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='moi', so_lan_thu=0, loi_cuoi=NULL WHERE id=?", (sk["id"],))
            webhook.nap(sk["id"])
            csdl.audit("webhook_replay", f"su_kien:{sk['id']}", f"trạng thái trước: {sk['trang_thai']}",
                       tenant_id=tenant_id, user_id=u["id"])
            return self._tra(202, {"ok": True})

        # --- billing / audit / ai ---
        if duong == "/api/v2/billing":
            self._can("tenant.billing.xem", u)
            return self._tra(200, {"goi": dict(billing.goi_cua_tenant(tenant_id)),
                                   "usage": billing.usage_hien_tai(tenant_id)})
        if duong == "/api/v2/audit":
            self._can("tenant.audit.xem", u)
            ds = csdl.nhieu("SELECT * FROM audit WHERE tenant_id=? ORDER BY id DESC LIMIT 200", (tenant_id,))
            return self._tra(200, {"audit": [dict(x) for x in ds]})
        m = re.fullmatch(r"/api/v2/ai/(chuan-hoa-dia-chi|phat-hien-bat-thuong|goi-y-hang)", duong)
        if m and method == "POST":
            self._can("tenant.ai.dung", u)
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
