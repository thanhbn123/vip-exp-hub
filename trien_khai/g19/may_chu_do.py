"""MÁY CHỦ ĐO của G19/AG-04 — chạy trong TIẾN TRÌNH RIÊNG, CSDL TẠM RIÊNG.

Vì sao phải là tiến trình riêng: `app/cau_hinh.py` đọc `VIP_HUB_DATA` ở thời điểm **import**,
nên mỗi phép đo muốn có một CSDL tạm sạch thì phải là một tiến trình mới. Đây cũng là cách
chạy được **bản sao đã đột biến** của `server.py` mà KHÔNG đụng vào tệp thật của dự án.

Máy chủ LUÔN bind `127.0.0.1` cổng `0` (cổng động do hệ điều hành cấp). Không mở cổng ra ngoài.

HAI CHẾ ĐỘ
----------
* `--che-do liet-ke` — nhận danh sách `[đường, phương_thức]`, bắn HTTP THẬT vào máy chủ đang
  chạy, phân loại từng lượt: `CO_ROUTE` / `ROI` (404 nhánh rơi) / `KHONG_KET_LUAN` (429).
* `--che-do cach-ly` — dựng dữ liệu A/B có ĐÁNH DẤU rồi chạy phép đo CÁCH LY TENANT.

LƯỚI AN TOÀN (đo được, không phải lời hứa)
------------------------------------------
`_gac_mang()` ghi lại MỌI lượt `socket.connect()`. Ca đo khẳng định **0 lượt ra ngoài loopback**
— đó là bằng chứng cho BAN 1 ("không gọi hãng kể cả sandbox").
"""

import argparse
import hashlib
import hmac
import http.client
import json
import os
import secrets
import socket
import sys
import threading
from datetime import datetime, timedelta

from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import bot_route_thi_hanh as BOT  # noqa: E402  (hằng số câu chữ nhánh rơi dùng CHUNG)

MK = "g19-mat-khau-thu-trong-csdl-tam"     # mật khẩu THỬ trong CSDL TẠM — không phải credential thật
LOOPBACK = ("127.0.0.1", "localhost", "::1", "0.0.0.0")

NHAT_KY_MANG = []


def _gac_mang():
    """Ghi lại mọi lượt connect(). Không chặn — chỉ ĐO, để ca đo còn khẳng định được."""
    goc = socket.socket.connect

    def boc(self, dia_chi, *a, **k):
        try:
            host = dia_chi[0] if isinstance(dia_chi, tuple) else str(dia_chi)
        except Exception:
            host = "?"
        NHAT_KY_MANG.append(str(host))
        return goc(self, dia_chi, *a, **k)

    socket.socket.connect = boc


def _bay_gio():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Do:
    """Nền đo: CSDL tạm → schema → quyền → tenant A/B → máy chủ 127.0.0.1:0."""

    def __init__(self, app_dir):
        self.app = app_dir
        self.duoi = secrets.token_hex(4)
        self.srv = None
        self.cong = None

    def dung(self):
        import csdl
        import migrate
        import quyen
        import khoi_tao
        import webhook
        self.csdl, self.migrate, self.quyen = csdl, migrate, quyen
        csdl.mo()
        migrate.chay(im_lang=True)
        quyen.seed()
        khoi_tao.seed_providers()
        # Worker webhook PHẢI sống: `/api/v2/san-sang` trả 503 nếu nó chết, và như thế là
        # HỎNG GIẢ do chính bộ đo gây ra (bài học §7.1 của G18).
        webhook.khoi_dong()
        self.webhook = webhook
        self._dung_nguoi()
        self._dung_may_chu()
        return self

    # ---------- người / tenant ----------
    def nguoi(self, ten_dn, platform_role=None, mk=None):
        import bao_mat
        return self.csdl.ghi(
            "INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
            " VALUES (?,?,?,?,?)",
            (ten_dn, bao_mat.bam_mat_khau(mk or MK), ten_dn, platform_role,
             self.csdl.bay_gio())).lastrowid

    def tenant(self, code, ten, goi="free"):
        return self.csdl.ghi(
            "INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
            (code, ten, goi, self.csdl.bay_gio())).lastrowid

    def gan(self, uid, tid, role):
        self.csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                      " VALUES (?,?,?,?)", (uid, tid, role, self.csdl.bay_gio()))

    def _dung_nguoi(self):
        d = self.duoi
        self.mk_a = "MatKhauA-" + d
        self.mk_b = "MatKhauB-" + d
        self.tid_a = self.tenant("g19-a-" + d, "G19 Tenant A " + d)
        self.tid_b = self.tenant("g19-b-" + d, "G19 Tenant B " + d)
        # MỘT người vừa có quyền nền tảng vừa có membership ở A ⇒ `ngu_canh()` trả ngữ cảnh có
        # CẢ `platform_role` LẪN `tenant_id`; nhờ vậy cùng phiên đi được vào cả `_api_platform`
        # lẫn `_api_tenant` — đúng thứ phép PHÂN LOẠI route cần.
        self.uid_do = self.nguoi("g19-do-" + d, "PLATFORM_ADMIN")
        self.gan(self.uid_do, self.tid_a, "TENANT_OWNER")
        self.uid_a = self.nguoi("g19-a-owner-" + d, None, self.mk_a)
        self.gan(self.uid_a, self.tid_a, "TENANT_OWNER")
        self.uid_b = self.nguoi("g19-b-owner-" + d, None, self.mk_b)
        self.gan(self.uid_b, self.tid_b, "TENANT_OWNER")

    def _dung_may_chu(self):
        import server

        class ImLang(server.BoXuLy):
            def log_message(self, *a):
                pass

        # BIND 127.0.0.1, CỔNG 0. Không có đường nào mở cổng ra ngoài.
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), ImLang)
        self.cong = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    # ---------- phiên ----------
    def token(self, uid, tid):
        """Phiên MỚI cho mỗi lượt đo.

        Vì sao không dùng lại: vài route THẬT SỰ thu hồi phiên (`/api/v2/auth/dang-xuat`) hoặc
        đổi ngữ cảnh; dùng lại thì lượt sau nhận 401 — mà 401 KHÁC câu chữ nhánh rơi, nên bộ
        phân loại sẽ kết luận nhầm thành "CÓ route".
        """
        import bao_mat
        t = secrets.token_urlsafe(32)
        het_han = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        self.csdl.ghi("INSERT INTO sessions (token_hash, user_id, active_tenant_id, tao_luc,"
                      " het_han, dia_chi) VALUES (?,?,?,?,?,?)",
                      (bao_mat._hash_token(t), uid, tid, self.csdl.bay_gio(), het_han, "127.0.0.1"))
        return t

    # ---------- HTTP ----------
    def goi(self, duong, method="GET", token=None, than=None, header=None):
        """MỘT lượt HTTP THẬT qua socket tới 127.0.0.1:cổng động. Trả dict."""
        h = dict(header or {})
        if token:
            h["Cookie"] = "phien=" + token
        if method in ("POST", "PUT", "DELETE"):
            h["X-Requested-With"] = "VIPHub"      # CSRF: router đòi ở MỌI lượt ghi
        du = None
        if than is not None:
            du = json.dumps(than).encode("utf-8")
            h["Content-Type"] = "application/json"
        kn = http.client.HTTPConnection("127.0.0.1", self.cong, timeout=60)
        kn.request(method, duong, body=du, headers=h)
        r = kn.getresponse()
        tho = r.read()
        hd = {k.lower(): v for k, v in r.getheaders()}
        kn.close()
        try:
            j = json.loads(tho or b"{}")
        except ValueError:
            j = None
        return {"ma": r.status, "j": j, "tho": tho.decode("utf-8", "replace"), "hd": hd,
                "du": du}

    def phan_loai(self, ma, j):
        if ma == 404 and isinstance(j, dict) and j.get("loi") == BOT.CAU_ROI:
            return "ROI"
        if ma == 429:
            return "KHONG_KET_LUAN"
        return "CO_ROUTE"

    # ---------- ổn định nền giữa các lượt ----------
    def on_dinh(self):
        """Trả nền về trạng thái chuẩn sau mỗi lượt đo.

        Vì sao BẮT BUỘC: phép liệt kê bắn cả POST/PUT/DELETE vào MỌI đường, kể cả đường THẬT
        như `/api/v2/platform/tenants/(\\d+)/(khoa|mo|goi)`. Một lượt như vậy có thể khoá tenant A;
        khi đó `ngu_canh()` trả `tenant_id=None` và MỌI đường tenant sau đó trả 403 — mà 403 thì
        KHÁC câu chữ nhánh rơi, nên sẽ thành "CÓ route" GIẢ.
        """
        csdl = self.csdl
        csdl.ghi("UPDATE tenants SET trang_thai='hoat_dong' WHERE id IN (?,?)",
                 (self.tid_a, self.tid_b))
        csdl.ghi("UPDATE users SET trang_thai='hoat_dong', so_lan_sai=0, khoa_den=NULL,"
                 " platform_role='PLATFORM_ADMIN' WHERE id=?", (self.uid_do,))
        csdl.ghi("UPDATE users SET trang_thai='hoat_dong', so_lan_sai=0, khoa_den=NULL"
                 " WHERE id IN (?,?)", (self.uid_a, self.uid_b))
        for uid, tid, role in ((self.uid_do, self.tid_a, "TENANT_OWNER"),
                               (self.uid_a, self.tid_a, "TENANT_OWNER"),
                               (self.uid_b, self.tid_b, "TENANT_OWNER")):
            csdl.ghi("UPDATE tenant_memberships SET trang_thai='hoat_dong'"
                     " WHERE user_id=? AND tenant_id=?", (uid, tid))
            if not csdl.mot("SELECT id FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
                            (uid, tid)):
                self.gan(uid, tid, role)

    def xoa_tran(self):
        """Xoá MỌI bộ đếm trần tần suất (CSDL TẠM, tiến trình riêng).

        Không có bước này thì lượt thứ N bị 429 và bộ phân loại phải nói "không kết luận" —
        tức là phép đo tự làm hỏng chính nó. Đặc biệt `auth.quen_mat_khau` chỉ cho 5 lượt/IP/15
        phút rồi BAN 15 phút, mà phép đo cần gọi nó nhiều lượt.
        """
        gh = sys.modules["gioi_han"]
        if hasattr(gh, "xoa_het"):
            gh.xoa_het()
        for ep in gh.CHINH_SACH:
            for uid, tid in ((self.uid_do, self.tid_a), (self.uid_a, self.tid_a),
                             (self.uid_b, self.tid_b), (None, None)):
                try:
                    gh.dat_lai(ep, ip="127.0.0.1", dinh_danh=uid, tenant_id=tid)
                except Exception:
                    pass

    def dong(self):
        for f in (lambda: (self.srv.shutdown(), self.srv.server_close()),
                  lambda: self.webhook.dung()):
            try:
                f()
            except Exception:
                pass


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CHẾ ĐỘ 1 — LIỆT KÊ: phân loại từng lượt (đường, phương thức) bằng phản hồi THẬT
# ═════════════════════════════════════════════════════════════════════════════════════════════
def che_do_liet_ke(do, chi):
    ra = []
    for duong, method in chi:
        ma = j = None
        for _lan in range(3):
            do.xoa_tran()
            tok = do.token(do.uid_do, do.tid_a)
            r = do.goi(duong, method, token=tok)
            ma, j = r["ma"], r["j"]
            if ma != 429:
                break
        ra.append({"duong": duong, "method": method, "ma": ma,
                   "than": j if isinstance(j, dict) else None,
                   "phan_loai": do.phan_loai(ma, j)})
        do.on_dinh()
    return {"ket_qua": ra}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CHẾ ĐỘ 2 — CÁCH LY TENANT. Mỗi ca phải có ĐỐI CHỨNG DƯƠNG (chủ sở hữu hợp lệ trả 200) và
#              ĐỐI CHỨNG ĐƯỜNG cho vế phủ định (B trả dữ liệu CỦA B) — nếu không thì
#              "B không thấy dữ liệu A" có thể chỉ vì B chẳng nhận được gì.
# ═════════════════════════════════════════════════════════════════════════════════════════════
class DuLieu:
    """Dữ liệu A/B CÓ ĐÁNH DẤU: mọi hàng của A nhúng `canary_a`, của B nhúng `canary_b`."""

    def __init__(self, do):
        self.do = do
        self.F = {}

    def dung(self):
        import ai_job
        import bao_mat
        import goi_dich_vu
        import tai_chinh
        import usage
        csdl, do = self.do.csdl, self.do
        # Vài bảng G07/G08/G10 TỰ TẠO ở lần dùng đầu (`_dam_bao_bang`), KHÔNG do migrate dựng.
        # Không gọi trước thì INSERT fixture sẽ hỏng vì bảng chưa tồn tại.
        ai_job.bao_dam_bang()
        goi_dich_vu._dam_bao_bang()
        tai_chinh._dam_bao_bang()
        bay = csdl.bay_gio()
        ky = usage.ky_hien_tai()
        self.F.update({"ky": ky, "mk_a": do.mk_a, "mk_b": do.mk_b,
                       "ten_dn_a": "g19-a-owner-" + do.duoi, "ten_dn_b": "g19-b-owner-" + do.duoi})
        for nhan, tid, uid in (("a", do.tid_a, do.uid_a), ("b", do.tid_b, do.uid_b)):
            canary = "G19-%s-%s" % (nhan.upper(), do.duoi)
            so_luong = 2 if nhan == "a" else 5          # số phân biệt được A với B
            so_nk = 1 if nhan == "a" else 2
            self.F["canary_" + nhan] = canary
            self.F["so_luong_" + nhan] = so_luong
            self.F["so_dong_nk_" + nhan] = so_nk
            csdl.ghi("UPDATE tenants SET ten=? WHERE id=?", ("Tenant " + canary, tid))
            kh = csdl.ghi(
                "INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                (tid, "KH " + canary, "0900000000", "dc " + canary, bay)).lastrowid
            don = csdl.ghi(
                "INSERT INTO don_hang (tenant_id, ma_don, nguoi_gui_ten, nguoi_gui_sdt,"
                " nguoi_gui_dia_chi, nguoi_nhan_ten, nguoi_nhan_sdt, nguoi_nhan_dia_chi, hang_hoa,"
                " khoi_luong_gram, cod, trang_thai, can_doi_soat_ket_qua, nguoi_tao, tao_luc,"
                " cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, "DON-" + canary, "NG " + canary, "0900000001",
                 "dcg " + canary, "NN " + canary, "0900000002", "dcn " + canary, "HH " + canary,
                 500, 120000, "da_duyet", 1, uid, bay, bay)).lastrowid
            csdl.ghi("INSERT INTO ai_job (tenant_id, user_id, loai, trang_thai, vao_json,"
                     " nha_cung_cap, phien_ban_hop_dong, idem_key, tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
                     (tid, uid, canary, "moi", "{}", "mock", "v1", "idem-" + canary, bay))
            bi_mat = "bi-mat-gia-" + canary
            ban_ma, _ = bao_mat.ma_hoa_cred({"ghi_chu": canary}, tid, "vtp")
            wh_ma = ("g19%s%s" % (nhan, do.duoi)).lower()
            acc = csdl.ghi(
                "INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (tid, "vtp", "TK " + canary, "mock", ban_ma, "", wh_ma,
                 bao_mat.ma_hoa_wh(bi_mat, wh_ma), bay)).lastrowid
            csdl.ghi("INSERT INTO audit (luc, tenant_id, user_id, hanh_dong, doi_tuong, ket_qua,"
                     " chi_tiet) VALUES (?,?,?,?,?,?,?)",
                     (bay, tid, uid, "G19 " + canary, "g19:1", "thanh_cong", canary))
            csdl.ghi("INSERT OR REPLACE INTO usage_thang (tenant_id, thang, so_don, so_ai)"
                     " VALUES (?,?,?,?)",
                     (tid, ky, 7 if nhan == "a" else 23, 3 if nhan == "a" else 11))
            csdl.ghi("INSERT INTO su_kien_dung (tenant_id, loai, so_luong, idem_key, nguon,"
                     " tham_chieu, ky, tao_luc) VALUES (?,?,?,?,?,?,?,?)",
                     (tid, "api_thang", so_luong, "idem-" + canary, "he_thong", "SK " + canary,
                      ky, bay))
            csdl.ghi("INSERT INTO ai_su_kien (tenant_id, user_id, loai_su_kien, so_luot_ai,"
                     " chi_tiet, luc) VALUES (?,?,?,?,?,?)",
                     (tid, uid, "tao", 7, "AI " + canary, bay))
            csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id, event_id, payload_tho,"
                     " headers_json, nhan_luc, trang_thai) VALUES (?,?,?,?,?,?)",
                     (acc, "ev-" + canary, b"{}", json.dumps({"g19": canary}), bay, "moi"))
            csdl.ghi("INSERT INTO ds_dot (tenant_id, hang, carrier_account_id, ten_file, loai_file,"
                     " van_tay_file, ky_thanh_toan, trang_thai, so_dong, tao_boi, tao_luc)"
                     " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (tid, "vtp", acc, "DS " + canary + ".csv", "csv", "sha-" + do.duoi,
                      ky, "MOI", 1, uid, bay))
            csdl.ghi("INSERT INTO du_thao_hoa_don (tenant_id, ky, nhan_phap_ly, tien_goi_dong,"
                     " tong_dong, chi_tiet_json, tao_luc) VALUES (?,?,?,?,?,?,?)",
                     (tid, ky, "ban nhap G19", 1000, 1000, json.dumps({"g19": canary}), bay))
            csdl.ghi("INSERT INTO tc_cong_no (tenant_id, so, doi_tac, so_du_dong, cap_nhat_luc)"
                     " VALUES (?,?,?,?,?)", (tid, "phai_thu", "hang:" + canary, 5000, bay))
            csdl.ghi("INSERT INTO tc_cod (don_id, tenant_id, carrier_account_id, so_tien_du_kien,"
                     " tao_luc, cap_nhat_luc) VALUES (?,?,?,?,?,?)",
                     (don, tid, acc, 120000, bay, bay))
            for _i in range(so_nk):
                # Dựng bằng CHÍNH hàm của sản phẩm để móc băm đúng — INSERT tay phải tái tạo
                # đúng chuỗi sha256, và nếu sai thì `ok=false` là HỎNG GIẢ do bộ đo gây ra.
                tai_chinh.ghi_nhat_ky(tid, "tao", "cod:%d" % don, "TC " + canary, uid)
            csdl.ghi("INSERT INTO ky_tinh_phi (tenant_id, ky, bat_dau, ket_thuc, trang_thai,"
                     " tao_luc) VALUES (?,?,?,?,?,?)",
                     (tid, ky, ky + "-01", ky + "-28", "mo", bay))
            for k, v in (("kh", kh), ("don", don), ("acc", acc), ("wh_ma", wh_ma),
                         ("bi_mat", bi_mat), ("tid", tid), ("uid", uid)):
                self.F["%s_%s" % (k, nhan)] = v
        return self.F

    def lap(self, v):
        if isinstance(v, str):
            for k, gt in self.F.items():
                if isinstance(gt, (str, int)):
                    v = v.replace("{%s}" % k, str(gt))
            return v
        if isinstance(v, dict):
            return {k: self.lap(x) for k, x in v.items()}
        if isinstance(v, list):
            return [self.lap(x) for x in v]
        return v


def _phien(do, nhan, F):
    if nhan in (None, "voda"):
        return None
    return {"do": (do.uid_do, F["tid_a"]), "a": (do.uid_a, F["tid_a"]),
            "b": (do.uid_b, F["tid_b"])}[nhan]


def _co(chuoi, ds):
    return all(x in chuoi for x in ds)


def _mot_luot(do, ca, F, dl, phia):
    """Một lượt đo (A hoặc B). Trả dict kết quả thô."""
    do.xoa_tran()
    nhan = ca.get("phien_" + phia, "a" if phia == "a" else "b")
    uid_tid = _phien(do, nhan, F)
    tok = do.token(*uid_tid) if uid_tid else None
    than = dl.lap(ca.get("than_" + phia, ca.get("than")))
    header = dl.lap(ca.get("header_" + phia, ca.get("header")))
    header = dict(header or {})
    ky_ten = ca.get("tu_ky_" + phia)
    if ky_ten:
        # Chữ ký webhook: HMAC-SHA256 THÂN THÔ bằng bí mật CỦA CHÍNH tenant đó.
        du = json.dumps(than).encode("utf-8") if than is not None else b""
        header["X-Webhook-Signature"] = hmac.new(F["bi_mat_" + ky_ten].encode(), du,
                                                 hashlib.sha256).hexdigest()
    r = do.goi(dl.lap(ca["duong"]), ca.get("method", "GET"), token=tok, than=than, header=header)
    do.on_dinh()
    return r


def _kieu_dac_biet(do, ca, F, dl):
    """Ba cửa ĐĂNG NHẬP/ĐẶT LẠI không đo được bằng khuôn chung (không có dữ liệu tenant
    trong thân phản hồi, và vế phủ định phải so với một lượt KHÁC)."""
    kieu = ca["kieu"]
    if kieu == "dang-nhap":
        tot = _mot_luot(do, {**ca, "than_a": {"ten_dang_nhap": "{ten_dn_a}", "mat_khau": "{mk_a}"},
                             "phien_a": "voda", "tu_ky_a": None, "header_a": None}, F, dl, "a")
        xau = _mot_luot(do, {**ca, "than_b": {"ten_dang_nhap": "{ten_dn_a}",
                                              "mat_khau": "sai-mat-khau-g19"},
                             "phien_b": "voda", "tu_ky_b": None, "header_b": None}, F, dl, "b")
        cua_b = _mot_luot(do, {**ca, "than_a": {"ten_dang_nhap": "{ten_dn_b}", "mat_khau": "{mk_b}"},
                               "phien_a": "voda", "tu_ky_a": None, "header_a": None}, F, dl, "a")
        # Phiên B phải dẫn tới ĐÚNG tenant B — nếu không thì B đã lấy được ngữ cảnh của A.
        tok_b = None
        m = (cua_b["hd"].get("set-cookie") or "")
        for phan in m.split(";"):
            if phan.strip().startswith("phien="):
                tok_b = phan.strip()[len("phien="):]
        toi = do.goi("/api/v2/auth/toi", "GET", token=tok_b) if tok_b else {"ma": None, "tho": ""}
        return {
            "A": {"ma": tot["ma"], "dat": tot["ma"] == 200 and "ok" in tot["tho"]
                  and "phien=" in (tot["hd"].get("set-cookie") or ""),
                  "doi_chung": [200], "khang_dinh": ["ok", "Set-Cookie phien"]},
            "B": {"ma": xau["ma"], "dat": xau["ma"] == 401
                  and "set-cookie" not in xau["hd"]
                  and cua_b["ma"] == 200 and toi["ma"] == 200
                  and str(F["tid_b"]) in toi["tho"],
                  "doi_chung": [401], "khang_dinh": ["401 khi sai mật khẩu",
                                                     "B đăng nhập được và vào ĐÚNG tenant B"]},
            "ro_ri": False, "dat": None, "_tho_a": tot["tho"], "_tho_b": xau["tho"],
        }
    if kieu == "quen-mat-khau":
        that = _mot_luot(do, {**ca, "than_a": {"ten_dang_nhap": "{ten_dn_a}"}, "phien_a": "voda",
                              "header_a": None}, F, dl, "a")
        khong = _mot_luot(do, {**ca, "than_b": {"ten_dang_nhap": "khong-co-ai-g19"},
                               "phien_b": "voda", "header_b": None}, F, dl, "b")
        # KHÔNG dò tài khoản: thân phản hồi cho tên CÓ THẬT phải TRÙNG thân cho tên KHÔNG có.
        return {
            "A": {"ma": that["ma"], "dat": that["ma"] == 200 and "ok" in that["tho"],
                  "doi_chung": [200], "khang_dinh": ["ok"]},
            "B": {"ma": khong["ma"],
                  "dat": khong["ma"] == 200 and khong["tho"] == that["tho"]
                  and F["canary_a"] not in that["tho"],
                  "doi_chung": [200], "khang_dinh": ["thân phản hồi TRÙNG với tên không tồn tại",
                                                     "không lộ canary của A"]},
            "ro_ri": False, "dat": None, "_tho_a": that["tho"], "_tho_b": khong["tho"],
        }
    if kieu == "dat-lai-mat-khau":
        import bao_mat
        tot = _mot_luot(do, {**ca, "than_a": {"token": "{token_reset_a}",
                                              "mat_khau_moi": "MatKhauMoi-G19-A"},
                             "phien_a": "voda", "header_a": None}, F, dl, "a")
        h_a = do.csdl.mot("SELECT mat_khau_hash h FROM users WHERE id=?", (do.uid_a,))["h"]
        # PHỦ ĐỊNH: token ĐẶT LẠI của B KHÔNG được đụng vào mật khẩu của A.
        b_rieng = _mot_luot(do, {**ca, "than_b": {"token": "{token_reset_b}",
                                                  "mat_khau_moi": "MatKhauMoi-G19-B"},
                                 "phien_b": "voda", "header_b": None}, F, dl, "b")
        h_a2 = do.csdl.mot("SELECT mat_khau_hash h FROM users WHERE id=?", (do.uid_a,))["h"]
        # Token BỊA: phải hỏng, và cũng không được đụng vào A.
        bia = _mot_luot(do, {**ca, "than_b": {"token": "token-bia-g19-" + F["canary_a"],
                                              "mat_khau_moi": "MatKhauMoi-G19-X"},
                             "phien_b": "voda", "header_b": None}, F, dl, "b")
        h_a3 = do.csdl.mot("SELECT mat_khau_hash h FROM users WHERE id=?", (do.uid_a,))["h"]
        return {
            "A": {"ma": tot["ma"], "dat": tot["ma"] == 200 and "ok" in tot["tho"],
                  "doi_chung": [200], "khang_dinh": ["token hợp lệ ⇒ 200"]},
            "B": {"ma": b_rieng["ma"],
                  "dat": b_rieng["ma"] == 200 and h_a == h_a2 and bia["ma"] == 400 and h_a == h_a3,
                  "doi_chung": [200, 400],
                  "khang_dinh": ["token của B không đổi được mật khẩu A",
                                 "token bịa ⇒ 400"]},
            "ro_ri": False, "dat": None, "_tho_a": tot["tho"], "_tho_b": b_rieng["tho"],
        }
    raise ValueError("kiểu lạ: %r" % (kieu,))


def che_do_cach_ly(do, vao):
    dl = DuLieu(do)
    F = dl.dung()
    # Token đặt lại mật khẩu phải mint SAU khi có `users` (và `doi_mat_khau_luc` phải NULL).
    import bao_mat
    F["token_reset_a"] = bao_mat.tao_token_reset(F["ten_dn_a"])
    F["token_reset_b"] = bao_mat.tao_token_reset(F["ten_dn_b"])
    ra = []
    for ca in vao["ca"]:
        if ca.get("kieu") in ("dang-nhap", "quen-mat-khau", "dat-lai-mat-khau"):
            kq = _kieu_dac_biet(do, ca, F, dl)
            kq["dat"] = bool(kq["A"]["dat"] and kq["B"]["dat"] and not kq["ro_ri"])
            tho_a, tho_b = kq.pop("_tho_a"), kq.pop("_tho_b")
        else:
            a = _mot_luot(do, ca, F, dl, "a")
            b = _mot_luot(do, ca, F, dl, "b")
            kha_a, kha_b = ca.get("khang_dinh_a", []), ca.get("khang_dinh_b", [])
            dc_a = ca.get("doi_chung_a", [200])
            dc_b = ca.get("doi_chung_b", [200])
            kieu = ca.get("kieu", "tenant")
            a_dat = (a["ma"] in dc_a) and _co(a["tho"], dl.lap(kha_a))
            b_dat = (b["ma"] in dc_b) and _co(b["tho"], dl.lap(kha_b))
            if kieu == "toan_cuc":
                # Đường TOÀN CỤC: không được chứa dấu vết của BẤT KỲ tenant nào, cả hai lượt.
                a_dat = a_dat and F["canary_a"] not in a["tho"] and F["canary_b"] not in a["tho"]
                b_dat = b_dat and F["canary_a"] not in b["tho"] and F["canary_b"] not in b["tho"]
            ro_ri = (F["canary_a"] in b["tho"]) or (F["canary_a"] in b["hd"].get("set-cookie", ""))
            kq = {"A": {"ma": a["ma"], "dat": a_dat, "doi_chung": dc_a,
                        "khang_dinh": dl.lap(kha_a)},
                  "B": {"ma": b["ma"], "dat": b_dat, "doi_chung": dc_b,
                        "khang_dinh": dl.lap(kha_b)},
                  "ro_ri": bool(ro_ri),
                  "dat": bool(a_dat and b_dat and not ro_ri)}
            tho_a, tho_b = a["tho"], b["tho"]
        kq.update({"ten": ca["ten"], "duong": dl.lap(ca["duong"]), "mau": ca["duong"],
                   "method": ca.get("method", "GET"), "kieu": ca.get("kieu", "tenant"),
                   "ghi_chu": ca.get("ghi_chu", ""),
                   # Trích thân phản hồi THÔ làm BẰNG CHỨNG: người đọc báo cáo phải soi được
                   # chính chuỗi mà phép khẳng định đã so, không phải tin vào một chữ "ĐẠT".
                   # Lấy từ biến CỤC BỘ của chính lượt này — dùng lại biến của lượt trước là
                   # dán nhãn sai bằng chứng (đã dính đúng bẫy này ở lần viết đầu).
                   "tho_a": tho_a[:400], "tho_b": tho_b[:400]})
        ra.append(kq)
    return {"ca": ra, "fixture": {k: v for k, v in F.items()
                                  if isinstance(v, (str, int)) and "bi_mat" not in k}}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# CLI
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _main(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--app", required=True)
    p.add_argument("--che-do", required=True, choices=("liet-ke", "cach-ly"))
    p.add_argument("--vao", required=True)
    p.add_argument("--ra", required=True)
    p.add_argument("--du-lieu", required=True)
    a = p.parse_args(argv)

    os.environ["VIP_HUB_DATA"] = a.du_lieu
    os.environ["VIP_HUB_BIND"] = "127.0.0.1"     # không bao giờ bind ra ngoài
    os.environ.setdefault("VIP_HUB_HTTPS", "0")
    os.environ.pop("VIP_HUB_RESET_TOKEN", None)  # cửa trả token đặt-lại phải ĐÓNG (mặc định)
    _gac_mang()
    sys.path.insert(0, a.app)

    with open(a.vao, "r", encoding="utf-8") as f:
        vao = json.load(f)

    do = Do(a.app)
    try:
        do.dung()
        kq = che_do_liet_ke(do, vao) if a.che_do == "liet-ke" else che_do_cach_ly(do, vao)
    finally:
        do.dong()

    ngoai = sorted({h for h in NHAT_KY_MANG if h not in LOOPBACK})
    kq["giam_sat"] = {"so_luot_connect": len(NHAT_KY_MANG), "host_ngoai_loopback": ngoai}
    with open(a.ra, "w", encoding="utf-8") as f:
        json.dump(kq, f, ensure_ascii=False)
    print("[may-chu-do] cổng %s · %d lượt connect · ngoài loopback: %s"
          % (do.cong, len(NHAT_KY_MANG), ngoai or "KHÔNG CÓ"))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
