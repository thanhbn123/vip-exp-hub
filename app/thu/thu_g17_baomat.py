# G17-AG06 — BẢO MẬT & CÁCH LY TENANT: bộ thử ĐỘC LẬP cho ba cổng V5/V6/V7 toàn cục.
#
# VÌ SAO CÓ TỆP NÀY
# -----------------
# `docs/QA_G13_G15.md` §L2.8 (AG-01 tự ghi) nói thẳng: ba cổng sau CHƯA BAO GIỜ được đo độc lập,
# và `docs/G16_ACCEPTANCE.md` §8 mục 3 xác nhận tới G16 chúng VẪN MỞ:
#
#   · V5 — CÁCH LY TENANT TOÀN CỤC: mới đo đường webhook; chưa quét mọi cửa `/api/v2/*`.
#   · V6 — RBAC: chưa chạy lại ma trận ĐỘNG `role × hành_động` lấy từ bảng `role_permissions`.
#   · V7 — AES-256-GCM ĐẦY ĐỦ: chưa tự sửa bản mã / đổi chỗ bản mã giữa hai tenant / thử sai AAD.
#
# Tệp này dựng phép đo RIÊNG cho cả ba, KHÔNG mượn `thu_bao_mat.py` (bộ đó đo ở tầng hàm; ở đây
# đo ở tầng HTTP + CSDL thật, đúng chỗ dữ liệu tenant nằm).
#
# BA NHÓM ĐO
# ----------
#   · `V_QuetCua`  — hai tenant THẬT (A và B) + quét MỌI cửa `/api/v2/*`:
#                    (a) mọi cửa phải được KHAI trong `CUA` (canh bằng AST trên `server.py`;
#                        thêm route mới mà quên khai ⇒ bộ thử ĐỎ);
#                    (b) mỗi cửa chạy HAI lượt: chủ sở hữu A (đối chứng DƯƠNG) và tenant B
#                        (lượt phủ định). B không được đọc/thấy dấu vết nào của A, không được
#                        nhận 2xx khi địa chỉ là tài nguyên CỦA A;
#                    (c) ẢNH CHỤP CSDL trước/sau lượt B: không một hàng nào CỦA A được thêm,
#                        sửa hay xoá bởi lượt của B (phân loại chủ sở hữu theo `tenant_id`,
#                        theo bảng cha, hoặc theo người dùng).
#   · `R_Rbac`     — ma trận ĐỘNG `role × hành_động` đọc từ `role_permissions`, đối chiếu
#                    từng ô với `quyen.co_quyen`; rồi ĐỘT BIẾN CSDL (cấp một quyền KHÔNG có
#                    trong hằng `MA_TRAN`, thu một quyền ĐANG có) để chứng minh phán quyết đi
#                    theo DỮ LIỆU chứ không theo hằng viết cứng — và đo lại qua HTTP thật.
#   · `M_Aes`      — AES-256-GCM qua BỐN HÀM HỢP ĐỒNG (`ma_hoa_cred`/`giai_ma_cred`/
#                    `ma_hoa_wh`/`giai_ma_wh` — chỉ GỌI, không viết lại): sửa 1 byte bản mã,
#                    đổi chỗ bản mã giữa hai tenant TRONG CSDL, sai AAD, sai key_id, và bản mã
#                    mới phải mang `v3$<key_id>$…`. Có đường HTTP thật đi kèm mỗi lượt âm.
#
# HAI CHỐT CHẶN TỰ CAM KẾT (giữ nguyên luật của AG-01 ở `thu_qa_jt.py`/`thu_qa_g16.py`)
# ------------------------------------------------------------------------------------
#   1. `E_TuKiemBoDo` — chạy một ca CỐ Ý HỎNG trong TIẾN TRÌNH CON và khẳng định bộ dò THẤY
#      nó hỏng; tiêm một route GIẢ vào bản sao `server.py` và khẳng định phép canh KHAI BÁO
#      thấy nó thiếu; đưa bộ dò rò rỉ một phản hồi GIẢ CÓ RÒ để khẳng định nó kêu; và chạy
#      TOÀN BỘ tệp này trên một bản sao ĐÃ BỊ ĐỘT BIẾN (bỏ bộ lọc tenant của một cửa) để
#      khẳng định bộ thử ĐỎ và chỉ ĐÚNG cửa đó.
#   2. `Z_TongKet` — nhóm nào có ca ÂM mà không có ca DƯƠNG nào ⇒ bộ thử TỰ BÁO HỎNG. Không có
#      nhóm này thì mọi dòng "B bị chặn" đều có thể đúng một cách vô nghĩa (vì cửa hỏng sẵn).
#
# PHẠM VI ĐÃ ĐO — VÀ CÁI GÌ NẰM NGOÀI (đọc kỹ, §12.1 luật 3)
# ---------------------------------------------------------
#   · ĐO: CSDL SQLite schema v8 trong thư mục TẠM riêng (`VIP_HUB_DATA`), máy chủ THẬT
#     `server.ThreadingHTTPServer` bind `127.0.0.1` CỔNG 0 (hệ tự cấp, không tranh cổng với
#     làn khác), mọi lượt đo đi qua HTTP thật + SQLite thật.
#   · KHÔNG ĐO (nằm ngoài): hãng thật/sandbox (adapter ở chế độ MOCK, KHÔNG một byte ra mạng);
#     PostgreSQL (D-8 — vẫn SQLite); nhiều tiến trình (bộ thử chạy một tiến trình, nên trần
#     tần suất trong bộ nhớ và khoá ghi liên tiến trình KHÔNG được đo ở đây); TLS/HTTPS thật;
#     VPS/triển khai; giao diện trình duyệt; mô hình đe doạ "quản trị nền tảng độc ác" (phép
#     đo này giả định PLATFORM_OWNER là bên tin cậy — B ở đây là tenant, không phải nền tảng).
#   · `CAP_DUOC` (vai trò nào được cấp vai trò nào) là HẰNG TRONG MÃ, không nằm trong
#     `role_permissions` ⇒ NẰM NGOÀI ma trận động V6. Nói ra để không ai đọc thành "RBAC đã
#     động hoàn toàn".
#
# Chạy: python3 app/thu/thu_g17_baomat.py
import ast
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-ag06-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ.setdefault("VIP_HUB_BACKOFF", "0.05")
os.environ.setdefault("VIP_HUB_RESET_TOKEN", "0")

import adapter_jt      # noqa: E402,F401  (đăng ký adapter vào sổ)
import adapter_vtp     # noqa: E402,F401
import bao_mat         # noqa: E402
import cau_hinh        # noqa: E402
import csdl            # noqa: E402
import khoi_tao        # noqa: E402
import quyen           # noqa: E402
import secret_provider  # noqa: E402
import server          # noqa: E402
import webhook         # noqa: E402
import ai_validator    # noqa: E402
import doi_soat        # noqa: E402
import nhap_file       # noqa: E402
import tai_chinh       # noqa: E402

MK = "MatKhauAg06-123"
# DẤU VẾT A: chuỗi NGẪU NHIÊN mỗi lượt chạy, nhét vào MỌI loại dữ liệu của A (tên tenant, tên
# khách, tên hàng, credentials, tên file, lý do điều chỉnh…). Nhờ vậy "B có thấy dữ liệu của A
# không" trở thành một phép `in` chuỗi, không phải một phép đoán.
SI = "AG06A-" + secrets.token_hex(3).upper()
SI_B = "AG06B-" + secrets.token_hex(3).upper()
DAU_VET_A = (SI, "a-owner", "a-admin", "a-staff", "a-viewer", "a-nhieu", "a-r1", "a-r2")

SO_CA = {}
DO_LUONG = {}          # các con số đo được, in ra ở khối phạm vi (không phải khẳng định)


def ca(nhom, am=0, duong=0):
    d = SO_CA.setdefault(nhom, {"am": 0, "duong": 0})
    d["am"] += am
    d["duong"] += duong


# =========================================================================================
# LỚP HTTP
# =========================================================================================
class Tra:
    """Một phản hồi HTTP: mã + bytes thô + JSON (nếu có). Giữ RAW vì phép dò rò rỉ phải quét
    cả đường CSV/ảnh, không chỉ JSON — đo một đường rồi kết luận là SAI (§7.1 BAN_GIAO)."""

    __slots__ = ("ma", "raw", "j", "headers")

    def __init__(self, ma, raw, j=None, headers=None):
        self.ma, self.raw, self.j, self.headers = ma, raw, j, headers or {}

    @property
    def text(self):
        return self.raw.decode("utf-8", "replace") if isinstance(self.raw, (bytes, bytearray)) \
            else str(self.raw)

    def __iter__(self):
        """Cho phép `ma, json = phien.goi(...)` — cùng nếp với các bộ thử khác của dự án."""
        return iter((self.ma, self.j))


class Phien:
    """Client HTTP giữ cookie phiên. KHÔNG tự khẳng định gì — trả nguyên phản hồi."""

    def __init__(self, ten=""):
        self.ten = ten
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None, timeout=30):
        body = tho if tho is not None else (
            json.dumps(du_lieu, ensure_ascii=False).encode() if du_lieu is not None else None)
        h = dict(headers or {})
        if method in ("POST", "PUT", "DELETE") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if body is not None:
            h.setdefault("Content-Type", "application/json")
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request("http://127.0.0.1:%d%s" % (CONG, duong), data=body,
                                    headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=timeout) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                raw = ph.read()
                ct = ph.headers.get("Content-Type", "")
                return Tra(ph.status, raw, json.loads(raw) if ("json" in ct and raw) else None,
                           dict(ph.headers))
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                j = json.loads(raw)
            except Exception:                                            # noqa: BLE001
                j = None
            return Tra(e.code, raw, j, dict(e.headers))

    def dang_nhap(self, ten, mk=MK):
        return self.goi("/api/v2/auth/dang-nhap", "POST",
                        {"ten_dang_nhap": ten, "mat_khau": mk})


CONG = 0


def _dang_nhap(ten, mk=MK):
    p = Phien(ten)
    tr = p.dang_nhap(ten, mk)
    if tr.ma != 200:
        raise AssertionError(f"đăng nhập {ten!r} hỏng: HTTP {tr.ma} {tr.j}")
    return p


# =========================================================================================
# NỀN: hai tenant THẬT + người dùng theo vai trò + fixture của A
# =========================================================================================
class Nen:
    pass


NEN = None


def _uid_tenant():
    ra = {}
    for r in csdl.nhieu("SELECT DISTINCT user_id, tenant_id FROM tenant_memberships"):
        ra.setdefault(r["user_id"], set()).add(r["tenant_id"])
    return ra


def _tao_user(ten_dn, ho_ten, platform_role=None):
    return csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role,"
                    " tao_luc) VALUES (?,?,?,?,?)",
                    (ten_dn, bao_mat.bam_mat_khau(MK), ho_ten, platform_role,
                     csdl.bay_gio())).lastrowid


def _tao_tenant(code, ten, goi="pro"):
    return csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                    (code, ten, goi, csdl.bay_gio())).lastrowid


def _gan(uid, tid, role):
    csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
             " VALUES (?,?,?,?)", (uid, tid, role, csdl.bay_gio()))


def _csv_nhap(si, dong_cong_thuc=False):
    dau = "nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,cod,ghi_chu"
    d1 = f"Nhan {si},0903333333,12 Pho {si} HCM,Hang {si},700,25000,"
    d2 = f"Nhan {si}-2,0904444444,34 Pho {si} Ha Noi,Hang {si}-2,900,0,"
    if dong_cong_thuc:
        # Ô bắt đầu bằng '=' ⇒ cảnh báo công thức ⇒ dòng NEEDS_REVIEW (không tự tạo đơn).
        d2 += "=1+1"
    return (dau + "\n" + d1 + "\n" + d2 + "\n").encode("utf-8")


def _don(si, ten_nguoi_gui=None, ghi_chu=None):
    return {"nguoi_gui_ten": ten_nguoi_gui or f"Gui {si}", "nguoi_gui_sdt": "0901111111",
            "nguoi_gui_dia_chi": f"1 Duong {si} Ha Noi", "nguoi_nhan_ten": f"Nhan {si}",
            "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": f"2 Pho {si} HCM",
            "hang_hoa": f"Hang {si}", "khoi_luong_gram": 500, "cod": 1000,
            "ghi_chu": ghi_chu or si}


def _lay_id(kq, *ten):
    """Rút id từ phản hồi: chấp cả dạng số trần, `{"id":…}`, `{"dot_id":…}`, `{"job":{...}}`."""
    if isinstance(kq, int):
        return kq
    for t in ten:
        if isinstance(kq, dict) and isinstance(kq.get(t), int):
            return kq[t]
    for t in ("id", "don", "job", "batch"):
        if isinstance(kq, dict) and isinstance(kq.get(t), dict) and isinstance(kq[t].get("id"), int):
            return kq[t]["id"]
    raise AssertionError(f"không rút được id từ phản hồi: {kq!r}")


def dung_nen():
    """Dựng nền MỘT lần: CSDL v8, hai tenant, người dùng theo vai trò, máy chủ cổng 0, fixture A."""
    global NEN, CONG
    if NEN is not None:
        return NEN
    n = Nen()
    csdl.mo()
    quyen.seed()
    khoi_tao.seed_providers()
    import migrate
    kq_mig = migrate.chay(im_lang=True)
    n.phien_ban = csdl.phien_ban_hien_tai()
    n.migrate = kq_mig

    n.uid = {}
    n.uid["po"] = _tao_user("po", "Chủ nền tảng", "PLATFORM_OWNER")
    n.uid["pa"] = _tao_user("pa", "Quản trị nền tảng", "PLATFORM_ADMIN")
    n.ta = _tao_tenant(f"ag06-a-{SI.lower()}", f"Shop A {SI}")
    n.tb = _tao_tenant(f"ag06-b-{SI_B.lower()}", f"Shop B {SI_B}")
    for ten in ("a-owner", "a-admin", "a-staff", "a-viewer", "a-nhieu", "a-r1", "a-r2",
                "a-tam1", "a-tam2", "a-tam3", "a-tam4"):
        n.uid[ten] = _tao_user(ten, "NV " + ten)
        _gan(n.uid[ten], n.ta, {"a-owner": "TENANT_OWNER", "a-admin": "TENANT_ADMIN",
                                "a-staff": "TENANT_STAFF", "a-viewer": "TENANT_VIEWER",
                                "a-nhieu": "TENANT_VIEWER", "a-r1": "TENANT_STAFF",
                                "a-r2": "TENANT_STAFF"}.get(ten, "TENANT_VIEWER"))
    for ten in ("b-owner", "b-tam1", "b-tam2", "b-tam3"):
        n.uid[ten] = _tao_user(ten, "NV " + ten)
        _gan(n.uid[ten], n.tb, "TENANT_OWNER")
    n.uid_tenant = _uid_tenant()

    # --- máy chủ THẬT, bind 127.0.0.1 CỔNG 0 (hệ tự cấp) ---
    n.stderr_cu = sys.stderr
    sys.stderr = open(os.path.join(_tam, "stderr-server.log"), "w", encoding="utf-8")
    webhook.khoi_dong()
    n.sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    CONG = n.sv.server_address[1]
    threading.Thread(target=n.sv.serve_forever, name="ag06-http", daemon=True).start()

    for ten in ("po", "pa", "a-owner", "a-admin", "a-staff", "a-viewer", "a-nhieu", "a-r1",
                "a-r2", "a-tam1", "a-tam2", "a-tam3", "a-tam4", "b-owner", "b-tam1",
                "b-tam2", "b-tam3"):
        setattr(n, ten.replace("-", "_"), _dang_nhap(ten))

    n.FIX = {"ta": n.ta, "tb": n.tb}
    _dung_du_lieu_B(n)
    _dung_du_lieu_A(n)
    n.uid_tenant = _uid_tenant()
    _dat_nen(n)
    return n


def _dat_nen(n):
    global NEN
    NEN = n


def _thanh_cong(nhan, st, kq, ghi=""):
    if st not in (200, 201, 202):
        raise AssertionError(f"fixture {nhan} hỏng: HTTP {st} {kq} {ghi}")
    return kq


def _dung_du_lieu_B(n):
    """Fixture của B: một tài khoản hãng jt (để các cửa "tạo mới" của B có chỗ dựa)."""
    st, kq = n.b_owner.goi("/api/v2/tai-khoan-hang", "POST",
                           {"hang": "jt", "ten": f"JT B {SI_B}", "moi_truong": "mock",
                            "credentials": {"privateKey": SI_B + "-PK"}})
    kq = _thanh_cong("tai-khoan-hang B", st, kq)
    n.FIX["tk_b"] = kq["id"]
    n.wh_b = kq["webhook_ma"]
    n.wh_secret_b = kq["webhook_secret_mot_lan"]
    return kq


def _dung_du_lieu_A(n):
    """Fixture của A — dựng qua CHÍNH các cửa HTTP (nên chúng cũng là đối chứng dương đầu tiên)
    và qua hàm sản phẩm khi cửa HTTP cần hồ sơ phức tạp. Mọi fixture đều mang dấu vết SI."""
    a = n.a_owner
    F = n.FIX

    # tài khoản hãng: chính (jt) + phụ (vtp) cho khoa/mo/rotate/revoke
    st, kq = a.goi("/api/v2/tai-khoan-hang", "POST",
                   {"hang": "jt", "ten": f"JT {SI}", "moi_truong": "mock",
                    "credentials": {"api_key": SI + "-KEY", "privateKey": SI + "-PK"}})
    kq = _thanh_cong("tai-khoan-hang jt", st, kq)
    F["tk_a"] = kq["id"]
    n.wh_a = kq["webhook_ma"]
    n.wh_secret_a = kq["webhook_secret_mot_lan"]
    st, kq = a.goi("/api/v2/tai-khoan-hang", "POST",
                   {"hang": "vtp", "ten": f"VTP {SI}", "moi_truong": "mock",
                    "credentials": {"token": SI + "-VTP"}})
    F["tk_a2"] = _thanh_cong("tai-khoan-hang vtp", st, kq)["id"]

    # khách hàng
    st, kq = a.goi("/api/v2/khach-hang", "POST", {"ten": f"Khach {SI}", "sdt": "0905555555",
                                                  "dia_chi": f"5 Pho {SI} HCM"})
    F["kh_a"] = _thanh_cong("khach-hang", st, kq)["id"]

    # đơn hàng — mỗi cửa cần trạng thái riêng một đơn riêng (để lượt này không phá lượt kia)
    for ten, gc in (("don_a", "doc"), ("don_sua", "sua"), ("don_mh", "mat-hang"),
                    ("don_tc", "tu-choi"), ("don_ds", "doi-soat"), ("don_dst", "doi-soat-tay"),
                    ("don_duyet", "duyet"), ("don_gui", "gui"), ("don_huy", "huy"),
                    ("don_xoa", "xoa")):
        st, kq = a.goi("/api/v2/don", "POST", _don(SI, ghi_chu=f"{SI}-{gc}"))
        F[ten] = _thanh_cong(f"don {gc}", st, kq)["don"]["id"]
    # đơn cho lượt gửi hãng phải ở `da_duyet` trước
    _thanh_cong("duyet don_gui", *a.goi(f"/api/v2/don/{F['don_gui']}/duyet", "POST", {}))
    # ĐƠN ĐÃ GỬI HÃNG (cho cửa siêu dữ liệu nhãn) và ĐƠN CÓ SỔ COD ĐÃ ĐỐI SOÁT (cho cửa ghi
    # nhận thanh toán) — dựng bằng CHÍNH hàm sản phẩm, không đụng cửa nào đang được đo.
    import don_hang
    st, kq = a.goi("/api/v2/don", "POST", _don(SI, ghi_chu=f"{SI}-nhan"))
    F["don_nhan"] = _thanh_cong("don nhan", st, kq)["don"]["id"]
    don_hang.duyet_don(n.ta, n.uid["a-owner"], F["don_nhan"])
    don_hang.gui_don(n.ta, n.uid["a-owner"], F["don_nhan"], F["tk_a"])
    st, kq = a.goi("/api/v2/don", "POST", _don(SI, ghi_chu=f"{SI}-cod"))
    F["don_cod"] = _thanh_cong("don cod", st, kq)["don"]["id"]
    tai_chinh.mo_so_cod(n.ta, F["don_cod"])
    tai_chinh.chuyen_cod(n.ta, F["don_cod"], "COD_COLLECTED", "hang", f"fixture {SI}")
    tai_chinh.chuyen_cod(n.ta, F["don_cod"], "COD_RECONCILED", "hang", f"fixture {SI}",
                         so_tien_hang_bao=1000)

    # import: một lô đọc/xuất + một lô để duyệt + một dòng NEEDS_REVIEW để xác nhận
    st, kq = a.goi("/api/v2/import", "POST", {"ten_file": f"lo-{SI}.csv",
                                              "noi_dung_base64": base64.b64encode(
                                                  _csv_nhap(SI)).decode()})
    F["imp_a"] = _thanh_cong("import", st, kq)["batch_id"]
    st, kq = a.goi("/api/v2/import", "POST", {"ten_file": f"lo-duyet-{SI}.csv",
                                              "noi_dung_base64": base64.b64encode(
                                                  _csv_nhap(SI + "-D")).decode()})
    F["imp_duyet"] = _thanh_cong("import duyet", st, kq)["batch_id"]
    st, kq = a.goi("/api/v2/import", "POST", {"ten_file": f"lo-sua-{SI}.csv",
                                              "noi_dung_base64": base64.b64encode(
                                                  _csv_nhap(SI + "-S")).decode()})
    F["imp_edit"] = _thanh_cong("import sua", st, kq)["batch_id"]
    F["imp_dong"] = csdl.mot("SELECT id FROM import_dong WHERE batch_id=? ORDER BY id",
                             (F["imp_a"],))["id"]
    F["imp_dong_duyet"] = csdl.mot("SELECT id FROM import_dong WHERE batch_id=? ORDER BY id",
                                   (F["imp_duyet"],))["id"]
    F["imp_dong_sua"] = csdl.mot("SELECT id FROM import_dong WHERE batch_id=? ORDER BY id",
                                 (F["imp_edit"],))["id"]
    # dòng NEEDS_REVIEW: gieo THẲNG vào CSDL (fixture), không mượn cửa nào
    F["imp_nr"] = csdl.ghi(
        "INSERT INTO import_dong (batch_id, stt, du_lieu_json, trang_thai, loi)"
        " VALUES (?,99,?,'NEEDS_REVIEW',?)",
        (F["imp_a"], json.dumps({"nguoi_nhan_ten": f"NR {SI}", "nguoi_nhan_sdt": "0906666666",
                                 "nguoi_nhan_dia_chi": f"9 Pho {SI} HCM",
                                 "hang_hoa": f"Hang NR {SI}", "khoi_luong_gram": "800"},
                                ensure_ascii=False), "cần xem: fixture")).lastrowid

    # sự kiện webhook: một lượt ký ĐÚNG (đối chứng dương) + một lượt để replay
    for ten_fix, ev in (("sk_replay", "replay"),):
        F[ten_fix] = _ban_webhook(n, f"{SI}-{ev}")
    _thanh_cong("webhook A", *_ban_webhook(n, f"{SI}-doc", tra_ve=True))
    webhook.cho_rong(10)

    # membership: một để đổi vai trò, một để xoá
    ds = csdl.nhieu("SELECT id, user_id FROM tenant_memberships WHERE tenant_id=?", (n.ta,))
    theo_uid = {r["user_id"]: r["id"] for r in ds}
    F["mem_role"] = theo_uid[n.uid["a-r1"]]
    F["mem_del"] = theo_uid[n.uid["a-r2"]]
    F["mem_a"] = theo_uid[n.uid["a-staff"]]

    # tài chính: ba đợt thanh toán cho ba cửa ghi-nhan/chot/…
    for ten, ma_dot in (("dot_tt", "d1"), ("dot_tt2", "d2"), ("dot_tt3", "d3")):
        st, kq = a.goi("/api/v2/tai-chinh/dot-thanh-toan", "POST",
                       {"hang": "jt", "ma_dot": f"DOT-{SI}-{ma_dot}", "so_tien_hang_bao": 1000,
                        "carrier_account_id": F["tk_a"]})
        # `tai_chinh.tao_dot_thanh_toan` trả THẲNG id (số), không phải dict — chấp cả hai
        F[ten] = _lay_id(_thanh_cong(f"dot {ma_dot}", st, kq), "dot")

    # đối soát: nạp bảng kê bằng CHÍNH cửa HTTP, rồi đối chiếu để sinh chênh lệch
    for ten, ky in (("ds_dot", "2026-10"), ("ds_dot2", "2026-11"), ("ds_dot3", "2026-12"),
                    ("ds_dot4", "2027-01"), ("ds_dot5", "2027-03")):
        bang = _bang_ke(SI, ky)
        st, kq = a.goi("/api/v2/doi-soat/nap", "POST",
                       {"hang": "jt", "ten_file": f"bang-ke-{SI}-{ky}.csv",
                        "noi_dung_base64": base64.b64encode(bang).decode(),
                        "ky_thanh_toan": ky, "carrier_account_id": F["tk_a"]})
        F[ten] = _lay_id(_thanh_cong(f"doi-soat nap {ky}", st, kq), "dot_id")
    # đối chiếu cả bốn đợt: `duyet`/`tu-choi` chỉ chạy được khi đợt ở `CHO_DUYET`
    for ten in ("ds_dot", "ds_dot2", "ds_dot3", "ds_dot4"):
        doi_soat.doi_chieu(n.ta, F[ten])
    r = csdl.mot("SELECT id FROM ds_chenh_lech WHERE tenant_id=? ORDER BY id", (n.ta,))
    F["ds_cl"] = r["id"] if r else None

    # AI: ba việc cho ba cửa chay/duyet/tu-choi/de-xuat
    for ten, loai in (("ai_job", "chuan_hoa_truong"), ("ai_job2", "chuan_hoa_truong"),
                      ("ai_job3", "goi_y_hang")):
        st, kq = a.goi("/api/v2/ai/job", "POST",
                       {"loai": loai, "vao": {"dia_chi": f"9 Pho {SI} HCM", "hang_hoa": SI}})
        F[ten] = _lay_id(_thanh_cong(f"ai job {loai}", st, kq), "id")

    # tenant C: dựng qua CHÍNH cửa nền tảng (cũng là đối chứng dương cho cửa đó), để các cửa
    # theo-id của /platform/tenants/{id} có một đối tượng thật mà đo.
    st, kq = n.po.goi("/api/v2/platform/tenants", "POST",
                      {"ten": f"Tenant C {SI}", "code": f"ag06-c-{SI.lower()}", "goi_id": "free",
                       "owner_ten_dang_nhap": f"c-owner-{SI.lower()}", "owner_mat_khau": MK})
    F["tc"] = _lay_id(_thanh_cong("platform tao tenant C", st, kq), "id")

    # dấu vết A trong audit: một lượt ghi có SI trong chi tiết
    csdl.audit("ag06_dau_vet", "fixture:1", f"dấu vết {SI}", tenant_id=n.ta, user_id=n.uid["a-owner"])
    n.FIX = F
    return F


def _bang_ke(si, ky):
    """Bảng kê J&T tối thiểu (hàm THUẦN, không phụ thuộc fixture): một dòng trỏ vào vận đơn
    không tồn tại ⇒ `doi_chieu` sinh chênh lệch `thieu_don_he` để đo cửa xử lý chênh lệch."""
    dau = "billCode,orderId,codAmount,freight,settlement period"
    return (f"{dau}\nKHONG-CO-{si},{si}-KHONGCO,2000,600,{ky}\n"
            f"KHONG-CO2-{si},{si}-KHONGCO2,1000,300,{ky}\n").encode("utf-8")


def _ban_webhook(n, ma_van_don, tra_ve=False):
    body = json.dumps({"event": "da_giao", "tracking_number": ma_van_don,
                       "event_id": f"ev-{ma_van_don}"}, ensure_ascii=False).encode()
    ky = hmac.new(n.wh_secret_a.encode(), body, hashlib.sha256).hexdigest()
    p = Phien("webhook")
    tr = p.goi(f"/api/v2/webhook/nhan/{n.wh_a}", "POST", tho=body,
               headers={"X-Webhook-Signature": ky, "Content-Type": "application/json"})
    if tra_ve:
        return tr.ma, tr.j
    _thanh_cong("ban webhook", tr.ma, tr.j)
    return csdl.mot("SELECT id FROM wh_su_kien WHERE carrier_account_id=?"
                    " ORDER BY id DESC", (n.FIX["tk_a"],))["id"]


# =========================================================================================
# BẢNG CỬA — MỌI route /api/v2/* phải được KHAI ở đây
# =========================================================================================
# `loai`:
#   doc_ds  — cửa đọc phạm vi tenant; A phải 200 (+ dấu vết A nếu `sentinel`), B phải 200 và SẠCH
#   doc_id  — đọc MỘT đối tượng theo id; A 200, B phải 403/404
#   ghi_id  — ghi/sửa/xoá MỘT đối tượng theo id; A "qua được cửa", B phải 403/404
#   tao     — tạo mới; A và B đều tạo được, nhưng hàng mới phải thuộc về chính người gọi
#   toan_cuc— dữ liệu dùng chung, không theo tenant; hai bên đều 200
#   nen_tang— cửa nền tảng; A = phiên PLATFORM_*, B (tenant) phải 403
#   phien   — cửa tác động lên CHÍNH phiên/tài khoản người gọi
#   vo_danh — không cần phiên
#   rieng   — có ca thử RIÊNG trong nhóm T_VoDanh (vẫn phải khai để phép canh đủ)
# `chat=True` nghĩa là phép đo CHẶT (mã chính xác + dấu vết); `chat=False` là phép đo "qua được
# cửa" (mã ngoài 401/403/404/5xx) — dùng cho cửa ghi cần hồ sơ nghiệp vụ sâu. Số lượng hai loại
# được in ra ở khối phạm vi, KHÔNG gộp làm một.
OK_MO = (200, 201, 202, 400, 402, 409)


def _c(duong, method="GET", quyen=None, loai="doc_ds", ok_A=(200,), chan_B=(200,),
       than=None, than_B=None, sentinel=False, rb=False, chat=True, phien_A="a_owner",
       phien_B="b_owner", chu="", them_phuong_thuc=(), rong_B=False):
    return dict(duong=duong, method=method, quyen=quyen, loai=loai, ok_A=ok_A, chan_B=chan_B,
                than=than, than_B=than_B, sentinel=sentinel, rb=rb, chat=chat,
                phien_A=phien_A, phien_B=phien_B, chu=chu, them_phuong_thuc=them_phuong_thuc,
                rong_B=rong_B)


def bang_cua():
    """Bảng cửa. `{...}` được thay bằng id fixture của A (xem `Nen.FIX`)."""
    D = _don(SI, ghi_chu=SI + "-B")
    DB = _don(SI_B, ghi_chu=SI_B + "-B")
    tk_A = {"hang": "vtp", "ten": f"TKV {SI}", "moi_truong": "mock",
            "credentials": {"token": SI + "-ROT"}}
    tk_B = {"hang": "vtp", "ten": f"TKV {SI_B}", "moi_truong": "mock",
            "credentials": {"token": SI_B + "-ROT"}}
    csv_A = {"ten_file": f"lo-b-{SI}.csv",
             "noi_dung_base64": base64.b64encode(_csv_nhap(SI + "-B")).decode()}
    csv_B = {"ten_file": f"lo-b-{SI_B}.csv",
             "noi_dung_base64": base64.b64encode(_csv_nhap(SI_B)).decode()}
    return [
        # ---------- vô danh / hạ tầng ----------
        _c("/api/v2/auth/dang-nhap", "POST", None, "rieng", phien_A=None, phien_B=None,
           chu="ca riêng T_VoDanh: đăng nhập"),
        _c("/api/v2/auth/quen-mat-khau", "POST", None, "rieng", phien_A=None, phien_B=None,
           chu="ca riêng T_VoDanh"),
        _c("/api/v2/auth/dat-lai-mat-khau", "POST", None, "rieng", phien_A=None, phien_B=None,
           chu="ca riêng T_VoDanh"),
        _c("/api/v2/webhook/nhan/{ma}", "POST", None, "rieng", phien_A=None, phien_B=None,
           chu="ca riêng T_VoDanh + W_Webhook"),
        _c("/api/v2/suc-khoe", "GET", None, "vo_danh", chan_B=(200,), phien_A=None, phien_B=None),
        _c("/api/v2/san-sang", "GET", None, "vo_danh", chan_B=(200,), phien_A=None, phien_B=None),

        # ---------- phiên / tài khoản ----------
        _c("/api/v2/auth/dang-xuat", "POST", None, "phien", phien_A="a_tam1", phien_B="b_tam1",
           chan_B=(200,)),
        _c("/api/v2/auth/toi", "GET", None, "doc_ds", sentinel=True),
        _c("/api/v2/auth/doi-tenant", "POST", None, "phien", than={"tenant_id": "{ta}"},
           than_B={"tenant_id": "{ta}"}, chan_B=(403,),
           chu="B đòi vào tenant A ⇒ phải 403 và phiên B KHÔNG đổi tenant"),
        _c("/api/v2/auth/doi-mat-khau", "POST", None, "phien",
           than={"mat_khau_cu": "sai-sai-sai", "mat_khau_moi": "MatKhauMoi-999"},
           than_B={"mat_khau_cu": "sai-sai-sai", "mat_khau_moi": "MatKhauMoi-999"},
           ok_A=(400,), chan_B=(400,), phien_A="a_tam3", phien_B="b_tam3", chat=True,
           chu="A: mật khẩu cũ SAI ⇒ 400 · B: cũng 400 cho CHÍNH tài khoản B (phiên B riêng, "
               "vì cửa đăng-xuất phía trước đã thu hồi phiên b-tam1)"),
        _c("/api/v2/auth/thu-hoi-phien", "POST", None, "phien", phien_A="a_tam2",
           phien_B="b_tam2", chan_B=(200,)),

        # ---------- nền tảng: B (tenant) phải bị chặn ở CỔNG CHUNG ----------
        _c("/api/v2/platform/tenants", "GET", "platform.tenant.xem", "nen_tang", phien_A="po",
           chan_B=(403,), rb=False),
        _c("/api/v2/platform/tenants", "POST", "platform.tenant.tao", "nen_tang", phien_A="po",
           than={"ten": f"Tenant C2 {SI}", "code": f"ag06-c2-{SI.lower()}", "goi_id": "free",
                 "owner_ten_dang_nhap": f"c2-owner-{SI.lower()}", "owner_mat_khau": MK},
           than_B={"ten": f"Tenant X {SI_B}", "code": f"ag06-x-{SI_B.lower()}", "goi_id": "free",
                   "owner_ten_dang_nhap": f"x-owner-{SI_B.lower()}", "owner_mat_khau": MK},
           ok_A=(201,), chan_B=(403,), chat=True, chu="tạo luôn tenant C để đo các cửa theo id"),
        _c("/api/v2/platform/tenants/{tc}", "GET", "platform.tenant.xem", "nen_tang",
           phien_A="po", chan_B=(403,)),
        _c("/api/v2/platform/tenants/{tc}", "PUT", "platform.tenant.sua", "nen_tang",
           phien_A="po", than={"ten": f"Tenant C {SI}"}, chan_B=(403,),
           them_phuong_thuc=("POST",)),
        _c("/api/v2/platform/tenants/{tc}/khoa", "POST", "platform.tenant.khoa", "nen_tang",
           phien_A="po", chan_B=(403,)),
        _c("/api/v2/platform/tenants/{tc}/mo", "POST", "platform.tenant.khoa", "nen_tang",
           phien_A="po", chan_B=(403,)),
        _c("/api/v2/platform/tenants/{tc}/goi", "POST", "platform.goi.doi", "nen_tang",
           phien_A="po", than={"goi_id": "free"}, chan_B=(403,)),
        _c("/api/v2/platform/goi", "GET", "platform.tenant.xem", "nen_tang", phien_A="po",
           chan_B=(403,)),
        _c("/api/v2/platform/vai-tro", "GET", "platform.tenant.xem", "nen_tang", phien_A="po",
           chan_B=(403,), chu="ma trận RBAC: tenant B KHÔNG được đọc (QA q03)"),
        _c("/api/v2/platform/quan-sat/metric", "GET", "platform.audit.xem", "nen_tang",
           phien_A="po", chan_B=(403,)),
        _c("/api/v2/platform/g09/harness", "POST", "platform.audit.xem", "nen_tang",
           phien_A="po", chan_B=(403,), chu="harness ép MOCK, không ra mạng"),
        _c("/api/v2/platform/audit", "GET", "platform.audit.xem", "nen_tang", phien_A="po",
           chan_B=(403,)),

        # ---------- tenant ----------
        _c("/api/v2/tenant", "GET", "tenant.xem", "doc_ds", sentinel=True),
        _c("/api/v2/tenant", "PUT", "tenant.sua", "ghi_id", than={"ten": f"Shop A {SI}"},
           ok_A=OK_MO, chat=False, them_phuong_thuc=("POST",)),
        _c("/api/v2/memberships", "GET", "tenant.membership.xem", "doc_ds"),
        _c("/api/v2/memberships", "POST", "tenant.membership.quan_ly", "tao", ok_A=(201,),
           than={"ten_dang_nhap": "a-nhieu2", "mat_khau": MK, "role": "TENANT_VIEWER"},
           than_B={"ten_dang_nhap": "b-nhieu2", "mat_khau": MK, "role": "TENANT_VIEWER"},
           chan_B=(201,)),
        _c("/api/v2/memberships/{mem_role}", "PUT", "tenant.membership.quan_ly", "ghi_id",
           than={"role": "TENANT_VIEWER"}, ok_A=OK_MO, chat=False, chan_B=(404,),
           them_phuong_thuc=("POST",)),
        _c("/api/v2/memberships/{mem_del}", "DELETE", "tenant.membership.quan_ly", "ghi_id",
           ok_A=(200,), chat=True, chan_B=(404,)),
        _c("/api/v2/khach-hang", "GET", "tenant.khach.xem", "doc_ds", sentinel=True),
        _c("/api/v2/khach-hang", "POST", "tenant.khach.ghi", "tao", ok_A=(201,),
           than={"ten": f"Khach B {SI}", "sdt": "0907777777"},
           than_B={"ten": f"Khach B {SI_B}", "sdt": "0907777778"}, chan_B=(201,)),
        _c("/api/v2/khach-hang/{kh_a}", "GET", "tenant.khach.xem", "doc_id", sentinel=True,
           chan_B=(403, 404)),
        _c("/api/v2/hang", "GET", "tenant.hang.xem", "toan_cuc", chan_B=(200,)),
        _c("/api/v2/tai-khoan-hang", "GET", "tenant.hang.xem", "doc_ds", sentinel=True,
           chu="và KHÔNG được trả secret (đo riêng ở V_KhongLoBiMat)"),
        _c("/api/v2/tai-khoan-hang", "POST", "tenant.hang.quan_ly", "tao", ok_A=(201,),
           than={"hang": "vtp", "ten": f"TKM {SI}", "moi_truong": "mock",
                 "credentials": {"token": SI + "-M"}},
           than_B={"hang": "vtp", "ten": f"TKM {SI_B}", "moi_truong": "mock",
                   "credentials": {"token": SI_B + "-M"}}, chan_B=(201,)),
        _c("/api/v2/tai-khoan-hang/{tk_a2}/rotate", "POST", "tenant.hang.quan_ly", "ghi_id",
           than=tk_A, than_B=tk_B, ok_A=(200,), chan_B=(403, 404)),
        _c("/api/v2/tai-khoan-hang/{tk_a2}/khoa", "POST", "tenant.hang.quan_ly", "ghi_id",
           ok_A=(200,), chan_B=(403, 404)),
        _c("/api/v2/tai-khoan-hang/{tk_a2}/mo", "POST", "tenant.hang.quan_ly", "ghi_id",
           ok_A=(200,), chan_B=(403, 404)),
        _c("/api/v2/tai-khoan-hang/{tk_a2}/revoke", "POST", "tenant.hang.quan_ly", "ghi_id",
           ok_A=(200,), chan_B=(403, 404)),

        # ---------- đơn hàng ----------
        _c("/api/v2/don/tim", "POST", "tenant.don.xem", "doc_ds", than={}, sentinel=True,
           than_B={}, rb=True),
        _c("/api/v2/don/kiem", "POST", "tenant.don.ghi", "tao", than=D, than_B=DB, ok_A=(200,),
           chan_B=(200,), rb=True),
        _c("/api/v2/don/can-doi-soat", "GET", "tenant.don.xem", "doc_ds", rb=True),
        _c("/api/v2/don", "GET", "tenant.don.xem", "doc_ds", sentinel=True, rb=True),
        _c("/api/v2/don/xuat-csv", "GET", "tenant.don.xem", "doc_ds", sentinel=True, rb=True),
        _c("/api/v2/don", "POST", "tenant.don.ghi", "tao", ok_A=(201,), than=D, than_B=DB,
           chan_B=(201,), rb=True),
        _c("/api/v2/don/{don_a}", "GET", "tenant.don.xem", "doc_id", sentinel=True, rb=True,
           chan_B=(404,)),
        _c("/api/v2/don/{don_sua}", "PUT", "tenant.don.ghi", "ghi_id",
           than={"ghi_chu": f"{SI}-SUA"}, ok_A=OK_MO, chat=False, rb=True, chan_B=(404,),
           them_phuong_thuc=("POST",)),
        _c("/api/v2/don/{don_xoa}", "DELETE", "tenant.don.duyet", "ghi_id", ok_A=(200,),
           chan_B=(403, 404)),
        _c("/api/v2/don/{don_a}/hanh-trinh", "GET", "tenant.don.xem", "doc_id", chan_B=(404,)),
        _c("/api/v2/don/{don_nhan}/nhan", "GET", "tenant.don.xem", "doc_id", chan_B=(404,)),
        _c("/api/v2/don/{don_a}/day-du", "GET", "tenant.don.xem", "doc_id", chan_B=(404,)),
        _c("/api/v2/don/{don_a}/kiem", "GET", "tenant.don.xem", "doc_id", chan_B=(404,)),
        _c("/api/v2/don/{don_a}/mat-hang", "GET", "tenant.don.xem", "doc_id", chan_B=(200,),
           rong_B=True, chu="B nhận 200 với danh sách RỖNG (cửa không 404) — không rò dữ liệu"),
        _c("/api/v2/don/{don_mh}/mat-hang", "PUT", "tenant.don.ghi", "ghi_id",
           than={"mat_hang": [{"ten": f"Mon {SI}", "so_luong": 1, "khoi_luong_gram": 100}]},
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/don/{don_tc}/tu-choi", "POST", "tenant.don.duyet", "ghi_id",
           than={"ly_do": f"Tu choi {SI}"}, ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/don/{don_ds}/doi-soat", "POST", "tenant.don.duyet", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/don/{don_dst}/doi-soat-tay", "POST", "tenant.don.duyet", "ghi_id",
           than={"ket_luan": "da_vao", "ma_van_don": f"MVD-{SI}"}, ok_A=OK_MO, chat=False,
           chan_B=(404,)),
        _c("/api/v2/don/{don_duyet}/duyet", "POST", "tenant.don.duyet", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/don/{don_gui}/gui", "POST", "tenant.don.duyet", "ghi_id",
           than={"carrier_account_id": "{tk_a}"}, ok_A=OK_MO, chat=False, chan_B=(404,),
           chu="adapter MOCK trong tiến trình, KHÔNG ra mạng"),
        _c("/api/v2/don/{don_huy}/huy", "POST", "tenant.don.duyet", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),

        # ---------- import ----------
        _c("/api/v2/import", "GET", "tenant.don.xem", "doc_ds", sentinel=True),
        _c("/api/v2/import", "POST", "tenant.import.ghi", "tao", ok_A=(201,), than=csv_A,
           than_B=csv_B, chan_B=(201,)),
        _c("/api/v2/import/{imp_a}", "GET", "tenant.don.xem", "doc_id", sentinel=True, chan_B=(404,)),
        _c("/api/v2/import/dong/{imp_dong_sua}", "PUT", "tenant.import.ghi", "ghi_id",
           than={"nguoi_nhan_ten": f"Sua {SI}"}, ok_A=OK_MO, chat=False, chan_B=(404,),
           them_phuong_thuc=("POST",)),
        _c("/api/v2/import/{imp_a}/xuat-csv", "GET", "tenant.don.xem", "doc_id", sentinel=True,
           chan_B=(404,)),
        _c("/api/v2/import/dong/{imp_nr}/xac-nhan", "POST", "tenant.import.ghi", "ghi_id",
           ok_A=(200,), chan_B=(403, 404)),
        _c("/api/v2/import/{imp_duyet}/duyet", "POST", "tenant.import.duyet", "ghi_id",
           than={"nguoi_gui": {"ten": f"Gui {SI}", "sdt": "0901111111",
                               "dia_chi": f"1 Duong {SI} Ha Noi"},
                 "dong_ids": ["{imp_dong_duyet}"]},
           than_B={"nguoi_gui": {"ten": f"Gui {SI_B}", "sdt": "0901111111",
                                 "dia_chi": f"1 Duong {SI_B} Ha Noi"},
                   "dong_ids": ["{imp_dong_duyet}"]},
           ok_A=(200,), chan_B=(403, 404), chat=True),
        _c("/api/v2/webhook/su-kien", "GET", "tenant.webhook.xem", "doc_ds"),
        _c("/api/v2/webhook/su-kien/{sk_replay}/replay", "POST", "tenant.webhook.replay",
           "ghi_id", ok_A=(202,), chan_B=(403, 404)),
        _c("/api/v2/polling/chay", "POST", "tenant.hang.quan_ly", "ghi_id", than={},
           ok_A=OK_MO, chat=False, chu="quét hãng ở chế độ MOCK"),

        # ---------- gói / mức dùng ----------
        _c("/api/v2/goi", "GET", "tenant.billing.xem", "toan_cuc", chan_B=(200,)),
        _c("/api/v2/dang-ky", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/dang-ky/doi-goi", "POST", "tenant.membership.quan_ly", "ghi_id",
           than={"goi_id": "pro"}, ok_A=OK_MO, chat=False, chan_B=OK_MO,
           chu="đổi gói tác động lên CHÍNH tenant người gọi — cách ly đo bằng ảnh chụp CSDL"),
        _c("/api/v2/usage", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/usage/bao-cao", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/usage/su-kien", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/usage/doi-soat", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/usage/tinh-phi", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/billing/du-thao", "GET", "tenant.billing.xem", "doc_ds"),
        _c("/api/v2/usage/dong-ky", "POST", "tenant.membership.quan_ly", "ghi_id",
           than={"ky": "2020-01"}, ok_A=OK_MO, chat=False),

        # ---------- G09 ----------
        _c("/api/v2/g09/suc-khoe-hang", "GET", "tenant.hang.xem", "toan_cuc", chan_B=(200,)),
        _c("/api/v2/g09/can-soat", "GET", "tenant.hang.xem", "toan_cuc", chan_B=(200,)),

        # ---------- AI ----------
        _c("/api/v2/ai/job", "POST", "tenant.ai.dung", "tao", ok_A=(201,),
           than={"loai": "chuan_hoa_truong", "vao": {"dia_chi": f"9 Pho {SI} HCM"}},
           than_B={"loai": "chuan_hoa_truong", "vao": {"dia_chi": f"9 Pho {SI_B} HCM"}},
           chan_B=(201,)),
        _c("/api/v2/ai/job", "GET", "tenant.ai.dung", "doc_ds"),
        _c("/api/v2/ai/su-kien", "GET", "tenant.ai.dung", "doc_ds"),
        _c("/api/v2/ai/thong-ke", "GET", "tenant.ai.dung", "doc_ds"),
        _c("/api/v2/ai/lo/{imp_dong}", "GET", "tenant.ai.dung", "doc_id", chan_B=(404,)),
        _c("/api/v2/ai/job/{ai_job}", "GET", "tenant.ai.dung", "doc_id", chan_B=(404,)),
        _c("/api/v2/ai/job/{ai_job2}/chay", "POST", "tenant.ai.dung", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,), chu="AI gateway ở chế độ MOCK nội bộ"),
        _c("/api/v2/ai/job/{ai_job2}/duyet", "POST", "tenant.don.ghi", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/ai/job/{ai_job3}/tu-choi", "POST", "tenant.don.ghi", "ghi_id",
           than={"ly_do": f"Tu choi AI {SI}"}, ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/ai/job/{ai_job2}/de-xuat", "POST", "tenant.ai.dung", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/ai/chuan-hoa-dia-chi", "POST", "tenant.ai.dung", "tao",
           than={"dia_chi": f"9 Pho {SI} HCM"}, than_B={"dia_chi": f"9 Pho {SI_B} HCM"},
           ok_A=(200,), chan_B=(200,)),
        _c("/api/v2/ai/phat-hien-bat-thuong", "POST", "tenant.ai.dung", "tao",
           than={"cod": 1000, "khoi_luong_gram": 500},
           than_B={"cod": 2000, "khoi_luong_gram": 700}, ok_A=(200,), chan_B=(200,)),
        _c("/api/v2/ai/goi-y-hang", "POST", "tenant.ai.dung", "tao",
           than={"hang_hoa": SI, "dia_chi": f"9 Pho {SI} HCM"},
           than_B={"hang_hoa": SI_B, "dia_chi": f"9 Pho {SI_B} HCM"}, ok_A=(200,),
           chan_B=(200,)),

        # ---------- tài chính ----------
        _c("/api/v2/tai-chinh/cod", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/tai-chinh/tong-so", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/tai-chinh/cong-no", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/tai-chinh/dieu-chinh", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/tai-chinh/dieu-chinh", "POST", "tenant.taichinh.ghi", "tao", ok_A=(201,),
           than={"loai": "cod", "so_tien_dong": 1000, "ly_do": f"Dieu chinh {SI}"},
           than_B={"loai": "cod", "so_tien_dong": 1000, "ly_do": f"Dieu chinh {SI_B}"},
           chan_B=(201,)),
        _c("/api/v2/tai-chinh/kiem-nhat-ky", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/tai-chinh/tinh-lai-cong-no", "POST", "tenant.taichinh.ghi", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=OK_MO, chu="việc trên TOÀN tenant người gọi"),
        _c("/api/v2/tai-chinh/dot-thanh-toan", "POST", "tenant.taichinh.ghi", "tao",
           ok_A=(201,),
           than={"hang": "jt", "ma_dot": f"DOT-B-{SI}", "so_tien_hang_bao": 500,
                 "carrier_account_id": "{tk_a}"},
           than_B={"hang": "jt", "ma_dot": f"DOT-B-{SI_B}", "so_tien_hang_bao": 500,
                   "carrier_account_id": "{tk_b}"}, chan_B=(201,)),
        _c("/api/v2/tai-chinh/dot-thanh-toan/{dot_tt2}/ghi-nhan", "POST", "tenant.taichinh.duyet",
           "ghi_id", than={"don_id": "{don_cod}", "so_tien_dong": 1000}, ok_A=OK_MO,
           chat=False, chan_B=(404,)),
        _c("/api/v2/tai-chinh/dot-thanh-toan/{dot_tt3}/chot", "POST", "tenant.taichinh.duyet",
           "ghi_id", ok_A=OK_MO, chat=False, chan_B=(409,),
           chu="PHÁT HIỆN F-03: đợt của A ⇒ B nhận 409 (như đợt ĐÃ CHỐT), không phải 404; câu UPDATE vẫn lọc tenant_id nên KHÔNG sửa được gì"),
        _c("/api/v2/tai-chinh/cod/{don_a}", "GET", "tenant.taichinh.xem", "doc_id",
           chan_B=(200,), chu="trả cấu trúc rỗng cho đơn không thuộc mình — đo bằng dấu vết"),

        # ---------- đối soát ----------
        _c("/api/v2/doi-soat/nap", "POST", "tenant.taichinh.ghi", "tao", ok_A=(201,),
           than={"hang": "jt", "ten_file": f"bk-b-{SI}.csv",
                 "noi_dung_base64": base64.b64encode(_bang_ke(SI, "2027-02")).decode(),
                 "ky_thanh_toan": "2027-02", "carrier_account_id": "{tk_a}"},
           than_B={"hang": "jt", "ten_file": f"bk-b-{SI_B}.csv",
                   "noi_dung_base64": base64.b64encode(_bang_ke(SI_B, "2027-02")).decode(),
                   "ky_thanh_toan": "2027-02", "carrier_account_id": "{tk_b}"},
           chan_B=(201,)),
        _c("/api/v2/doi-soat/dot", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/doi-soat/dot/{ds_dot5}/doi-chieu", "POST", "tenant.taichinh.ghi", "ghi_id",
           ok_A=(200,), chan_B=(404,),
           chu="đợt RIÊNG chưa đối chiếu (các đợt khác đã đối chiếu sẵn để đo duyet/tu-choi)"),
        _c("/api/v2/doi-soat/dot/{ds_dot3}/duyet", "POST", "tenant.taichinh.duyet", "ghi_id",
           ok_A=OK_MO, chat=False, chan_B=(404,)),
        _c("/api/v2/doi-soat/dot/{ds_dot4}/tu-choi", "POST", "tenant.taichinh.duyet", "ghi_id",
           than={"ly_do": f"Tu choi {SI}"}, ok_A=OK_MO, chat=False, chan_B=(409,),
           chu="PHÁT HIỆN F-03: đợt của A ⇒ B nhận 409, không phải 404; UPDATE vẫn lọc tenant"),
        _c("/api/v2/doi-soat/dot/{ds_dot}/bang-ke", "GET", "tenant.taichinh.xem", "doc_id",
           chan_B=(404,)),
        _c("/api/v2/doi-soat/dot/{ds_dot}/chenh-lech", "GET", "tenant.taichinh.xem", "doc_id",
           chan_B=(200,), rong_B=True,
           chu="cửa không 404 với đợt của tenant khác — trả RỖNG (đo bằng rong_B), không rò dữ liệu"),
        _c("/api/v2/doi-soat/dot/{ds_dot}/xuat-csv", "GET", "tenant.taichinh.xem", "doc_id",
           chan_B=(200, 404), chu="CSV của đợt A: B phải 404 hoặc CSV rỗng, không có dấu vết A"),
        _c("/api/v2/doi-soat/chenh-lech/{ds_cl}/xu-ly", "POST", "tenant.taichinh.ghi", "ghi_id",
           than={"xu_ly": "da_xu", "ghi_chu": f"Xu ly {SI}"}, ok_A=(200,), chan_B=(409,),
           chu="PHÁT HIỆN F-03: chênh lệch của A ⇒ B nhận 409 (như đã xử), không phải 404"),

        # ---------- billing / audit ----------
        _c("/api/v2/billing", "GET", "tenant.taichinh.xem", "doc_ds", rb=True),
        _c("/api/v2/audit", "GET", "tenant.audit.xem", "doc_ds", sentinel=True, rb=True),
    ]


# =========================================================================================
# QUÉT CỬA: đối chứng dương cho A, lượt phủ định cho B, ảnh chụp CSDL
# =========================================================================================
def _lap(duong, F):
    return duong.format(**{k: v for k, v in F.items() if v is not None})


def _doi_si(than):
    """Bản sao body dùng cho lượt B: MỌI dấu vết A đổi thành dấu vết B. Không có bước này thì
    phản hồi của B có thể chứa dấu vết A do CHÍNH B gửi vào (audit ghi lại chi tiết yêu cầu) —
    bộ dò sẽ kêu nhầm là rò rỉ. Đo một đường rồi kết luận là SAI (§7.1)."""
    if isinstance(than, dict):
        return {k: _doi_si(v) for k, v in than.items()}
    if isinstance(than, list):
        return [_doi_si(v) for v in than]
    if isinstance(than, str):
        return than.replace(SI, SI_B)
    return than


def _phien_cua(n, ten):
    if ten is None:
        return Phien("vo-danh")
    return getattr(n, ten)


def _cua_that(n):
    """Chạy hai lượt cho MỌI cửa đã khai. Trả kết quả từng cửa + ảnh chụp CSDL quanh lượt B."""
    F = dict(n.FIX)
    ds = []
    for e in bang_cua():
        if e["loai"] == "rieng":
            continue
        duong = _lap(e["duong"], F)
        than = e["than"]
        if isinstance(than, dict):
            than = {k: (_lap(v, F) if isinstance(v, str) else v) for k, v in than.items()}
            if e["duong"].endswith("{imp_duyet}/duyet"):
                than["dong_ids"] = [F["imp_dong_duyet"]]
        ds.append((e, duong, than))

    # ---- LƯỢT A (đối chứng dương) ----
    kq = []
    for e, duong, than in ds:
        p = _phien_cua(n, e["phien_A"])
        tr = p.goi(duong, e["method"], than)
        loi = _quyet_dinh_A(e, tr)
        kq.append({"e": e, "duong": duong, "A": tr.ma, "B": None, "B_text": None,
                   "loi_A": loi, "loi_B": []})
        ca("V", am=0, duong=0 if loi else 1)
    # ĐỢI worker webhook XỬ LÝ HẾT hàng đợi rồi mới chụp CSDL. KHÔNG `webhook.dung()`: cửa
    # `/api/v2/san-sang` kiểm "worker webhook sống", nên giết worker là tự tay làm cửa đó trả
    # 503 cho lượt B — một HỎNG GIẢ do chính bộ thử gây ra (bài học §7.1: thứ dùng để đo phải
    # được kiểm trước khi tin).
    if not webhook.cho_rong(10):
        raise AssertionError("worker webhook không xử lý hết hàng đợi trong 10 giây")
    time.sleep(0.3)

    # ---- ẢNH CHỤP CSDL (sau lượt A, trước lượt B) ----
    truoc = _chup(n)

    # ---- LƯỢT B (phủ định) ----
    for r in kq:
        e, duong, than = r["e"], r["duong"], None
        for e2, d2, t2 in ds:
            if e2 is e:
                than = t2
                break
        than_B = e["than_B"]
        if than_B is None:
            than_B = _doi_si(than)
        elif isinstance(than_B, dict):
            than_B = {k: (_lap(v, F) if isinstance(v, str) else v) for k, v in than_B.items()}
            if e["duong"].endswith("{imp_duyet}/duyet"):
                than_B["dong_ids"] = [F["imp_dong_duyet"]]
        p = _phien_cua(n, e["phien_B"])
        tr = p.goi(duong, e["method"], than_B)
        r["B"] = tr.ma
        r["B_text"] = tr.text
        r["loi_B"] = _quyet_dinh_B(e, tr.ma, tr.text, tr.j)
        ca("V", am=1, duong=0)

    # ---- ĐỐI CHIẾU CSDL: không hàng nào CỦA A bị B thêm/sửa/xoá ----
    sau = _chup(n)
    thay_doi = _so_sanh_chu_so_huu(n, truoc, sau)
    return {"cua": kq, "thay_doi": thay_doi}


def _quyet_dinh_A(e, tr):
    """Phán quyết lượt A. Trả danh sách lỗi. Đối chứng dương HỎNG ⇒ cửa coi như CHƯA ĐO ĐƯỢC,
    không được tính là "B bị chặn" (nếu không, một cửa hỏng sẵn cho mọi người sẽ "đạt")."""
    loi = []
    if tr.ma not in e["ok_A"]:
        loi.append(f"lượt A: HTTP {tr.ma} ngoài kỳ vọng {e['ok_A']}")
    if e["sentinel"] and SI not in tr.text:
        loi.append("lượt A: KHÔNG thấy dấu vết của A trong phản hồi ⇒ đối chứng dương vô hiệu")
    if tr.ma >= 500:
        loi.append(f"lượt A: HTTP {tr.ma} — lỗi hệ thống, cửa chưa đo được")
    return loi


def _quyet_dinh_B(e, ma, text, j=None):
    """Phán quyết lượt B. B không được: (1) nhận mã ngoài kỳ vọng, (2) thấy BẤT KỲ dấu vết nào
    của A trong phản hồi (quét RAW, nên phủ cả CSV/ảnh)."""
    loi = []
    if ma not in e["chan_B"]:
        loi.append(f"lượt B: HTTP {ma} ngoài kỳ vọng {e['chan_B']}")
    if ma < 500:
        for dv in DAU_VET_A:
            if dv in text:
                return loi + [f"lượt B: RÒ dấu vết của A ({dv!r}) trong phản hồi"]
    if e.get("rong_B") and isinstance(j, dict):
        for khoa, gt in j.items():
            if isinstance(gt, list) and gt:
                loi.append(f"lượt B: cửa này phải trả RỖNG mà trả {len(gt)} phần tử ở {khoa!r}")
    return loi


# ---- ảnh chụp CSDL + phân loại chủ sở hữu ----
CHU_QUA_CHA = {"don_lich_su": ("don_hang", "don_id"), "import_dong": ("import_batch", "batch_id"),
               "wh_su_kien": ("carrier_accounts", "carrier_account_id"),
               "don_mat_hang": ("don_hang", "don_id")}
# Bảng BẤT BIẾN: không cửa nào của tenant được phép đụng vào. ĐỔI một hàng trong đây là VI PHẠM.
# Đây KHÔNG phải danh sách "bỏ qua cho xanh" — nó là một khẳng định mạnh.
KHONG_DOI = ("schema_version", "roles", "permissions", "role_permissions", "goi_dich_vu",
             "carrier_providers")

# Bảng DÙNG CHUNG, ĐỔI ĐƯỢC: kho đếm toàn cục, khoá theo IP/định danh/endpoint chứ KHÔNG theo
# tenant. Chúng ĐỔI trong lượt của B là ĐÚNG — không phải rò rỉ, mà là bản chất của luật chống
# lạm dụng (kẻ tấn công không được nhân trần bằng cách tạo thêm tenant).
# Nên chúng không thuộc `KHONG_DOI` (bất biến) và cũng không phân loại được chủ sở hữu.
#
# VÁ G19 (AG-00): lần sửa ĐẦU của tôi thêm hai bảng này vào `KHONG_DOI` — SAI, vì tôi đọc
# `KHONG_DOI` là "bảng không thuộc tenant" trong khi nó nghĩa là "bảng KHÔNG ĐƯỢC ĐỔI". Ca thử
# kêu lại ngay (`bảng gioi_han_luot ĐỔI trong lượt B`) và nó kêu ĐÚNG. Đây là loại thứ ba.
DUNG_CHUNG = ("gioi_han_luot", "gioi_han_chan")


def _chup(n):
    ra = {}
    for t in csdl.nhieu("SELECT name FROM sqlite_master WHERE type='table'"
                        " AND name NOT LIKE 'sqlite_%'"):
        ten = t["name"]
        cols = [c[1] for c in csdl.nhieu(f"PRAGMA table_info({ten})")]
        ra[ten] = (cols, set(tuple(r) for r in csdl.nhieu(f"SELECT * FROM {ten}")))
    return ra


def _chu(n, ten_bang, cols, row):
    def idx(c):
        return cols.index(c) if c in cols else None
    if ten_bang == "tenants":
        return row[idx("id")]
    if ten_bang == "users":
        uid = row[idx("id")]
        for k, v in n.uid.items():
            if v == uid:
                return n.ta if k.startswith("a-") else (n.tb if k.startswith("b-") else None)
        r = csdl.nhieu("SELECT DISTINCT tenant_id FROM tenant_memberships WHERE user_id=?", (uid,))
        return {x["tenant_id"] for x in r} or {"MOI"}
    i = idx("tenant_id")
    if i is not None:
        return row[i]
    if ten_bang in ("sessions", "reset_tokens"):
        uid = row[idx("user_id")]
        return n.uid_tenant.get(uid, {"?"})
    cha = CHU_QUA_CHA.get(ten_bang)
    if cha:
        r = csdl.mot(f"SELECT tenant_id FROM {cha[0]} WHERE id=?", (row[idx(cha[1])],))
        return r["tenant_id"] if r else None
    return "KHONG_RO"


def _so_sanh_chu_so_huu(n, truoc, sau):
    """Trả vi phạm + SỐ HÀNG ĐỔI THEO CHỦ. Con số `so_B` quan trọng ngang danh sách vi phạm:
    nếu lượt B KHÔNG ghi được gì vào CSDL thì câu "không hàng nào của A bị đụng" là VÔ NGHĨA
    (một phép đo không bao giờ thấy thay đổi thì không chứng minh được gì)."""
    vi_pham, ghi_chu = [], []
    so_B = so_khac = so_audit_null = 0
    vi_du_null = []
    for ten, (cols, rows_truoc) in truoc.items():
        if ten.startswith("__"):
            continue
        cols2, rows_sau = sau.get(ten, (cols, set()))
        if rows_truoc == rows_sau:
            continue
        them = rows_sau - rows_truoc
        bot = rows_truoc - rows_sau
        if ten == "tenants":
            for row in them | bot:
                if row[cols.index("id")] == n.ta:
                    vi_pham.append(f"bảng tenants: tenant A bị ĐỔI trong lượt B: {tuple(row)[:4]}")
                elif row[cols.index("id")] not in (n.tb,) and row[cols.index("id")] not in                         [r[cols.index("id")] for r in (them | bot)]:
                    vi_pham.append(f"bảng tenants: hàng lạ bị ĐỔI: {tuple(row)[:4]}")
            continue
        if ten in DUNG_CHUNG:
            # Kho đếm toàn cục: ĐỔI được, và đổi trong lượt B là ĐÚNG. Không phân loại chủ.
            # Vẫn GHI RA để người đọc biết nó đã đổi và đổi bao nhiêu — im lặng bỏ qua thì
            # một bảng dùng chung bị lợi dụng làm kênh rò sẽ không ai thấy.
            ghi_chu.append(f"{ten}: bảng DÙNG CHUNG đổi trong lượt B (+{len(them)}/-{len(bot)})"
                           " — khoá theo IP/định danh/endpoint, KHÔNG theo tenant")
            continue
        if ten in KHONG_DOI:
            vi_pham.append(f"bảng {ten} ĐỔI trong lượt B (+{len(them)}/-{len(bot)}) — không "
                           f"cửa nào của tenant được phép đụng bảng này")
            continue
        for row in them | bot:
            chu = _chu(n, ten, cols, row)
            if ten == "audit":
                try:
                    i_hd = cols.index("hanh_dong")
                except ValueError:
                    i_hd = None
                if i_hd is not None and row[i_hd] == "webhook_chu_ky_tu_choi":
                    ghi_chu.append("audit: một dòng `webhook_chu_ky_tu_choi` ghi với tenant_id "
                                   "của chủ tài khoản (cửa webhook vô danh) — xem báo cáo F-02")
                    continue
            la_A = False
            if isinstance(chu, int):
                la_A = (chu == n.ta)
            elif isinstance(chu, set):
                la_A = (n.ta in chu)
            if chu is None and ten == "audit":
                # `audit` ghi bằng `tenant_id=NULL` khi lượt từ chối không có ngữ cảnh tenant
                # (đo được: `doi_tenant` từ chối của B). Vẫn là hàng CỦA B, chỉ thiếu nhãn
                # tenant — ĐẾM RIÊNG và in ra, không gộp vào "sạch" cũng không kể là vi phạm.
                so_audit_null += 1
                vi_du_null.append(f"{row[cols.index('hanh_dong')]} (user {row[cols.index('user_id')]})")
                continue
            if chu is None and ten not in ("audit",):
                vi_pham.append(f"bảng {ten}: hàng KHÔNG RÕ CHỦ SỞ HỮU bị đổi trong lượt B — "
                               f"phải khai cách phân loại: {tuple(row)[:6]}")
                continue
            if la_A or chu == "KHONG_RO":
                vi_pham.append(f"bảng {ten}: hàng của A (chủ={chu!r}) bị ĐỔI trong lượt B: "
                               f"{tuple(row)[:6]}")
            elif chu == n.tb or (isinstance(chu, set) and chu and chu <= {n.tb}):
                so_B += 1
            else:
                so_khac += 1
    return {"vi_pham": vi_pham, "ghi_chu": ghi_chu, "so_B": so_B, "so_khac": so_khac,
            "so_audit_null": so_audit_null, "vi_du_null": sorted(set(vi_du_null))}


KQ_QUET = None


def ket_qua_quet():
    global KQ_QUET
    if KQ_QUET is None:
        KQ_QUET = _cua_that(dung_nen())
    return KQ_QUET


# =========================================================================================
# V — CÁCH LY TENANT
# =========================================================================================
class V_QuetCua(unittest.TestCase):
    """V5 — quét mọi cửa /api/v2/*. Mọi khẳng định ở đây có ĐỐI CHỨNG DƯƠNG đi kèm trong cùng
    một phép đo: lượt A phải qua cửa, nếu không thì cửa đó bị coi là CHƯA ĐO ĐƯỢC."""

    def test_v1_bang_cua_phu_moi_route_trong_server(self):
        """Canh KHAI BÁO: mọi route (và method) so sánh trong `server.py` phải có mặt trong
        bảng cửa; và bảng cửa không được khai route không tồn tại. Thêm route mới mà quên khai
        ⇒ ca này ĐỎ."""
        cua_that = _cua_tu_nguon(os.path.join(GOC_APP, "server.py"))
        khai = {}
        for e in bang_cua():
            # tên tham số trong bảng cửa là tên FIXTURE (`{kh_a}`); server.py dùng `(\d+)`.
            d = _chuan_hoa_khai(e["duong"])
            khai.setdefault(d, set()).add(e["method"])
            khai[d].update(e.get("them_phuong_thuc", ()))
        khai["/api/v2/platform/"] = {None}      # tiền tố `duong.startswith(...)`
        thieu, thua = [], []
        for (duong, method), ln in sorted(cua_that.items(), key=lambda x: x[1]):
            ms = khai.get(duong)
            # `method is None` = server KHÔNG kiểm method ở cửa đó (mọi method vào handler)
            if ms is None or (method is not None and method not in ms):
                thieu.append(f"{method} {duong} (server.py:{ln})")
        for duong, ms in sorted(khai.items()):
            for m in ms:
                if (duong, m) in cua_that:
                    continue
                if m is not None and (duong, None) in cua_that:
                    continue                    # server không kiểm method ⇒ mọi method hợp lệ
                thua.append(f"{m} {duong}")
        ca("V1", duong=1, am=1)
        self.assertEqual([], thieu, "route trong server.py CHƯA được khai trong bảng cửa:\n  "
                         + "\n  ".join(thieu))
        self.assertEqual([], thua, "bảng cửa khai route KHÔNG có trong server.py:\n  "
                         + "\n  ".join(thua))
        self.assertGreater(len(cua_that), 80, "phép trích route dò được quá ít — nghi hỏng bộ dò")

    def test_v2_luot_A_qua_duoc_moi_cua(self):
        """Đối chứng DƯƠNG cho từng cửa: chủ sở hữu hợp lệ phải qua được."""
        kq = ket_qua_quet()
        hong = [f"{r['e']['method']} {r['duong']}: " + "; ".join(r["loi_A"])
                for r in kq["cua"] if r["loi_A"]]
        ca("V2", duong=len(kq["cua"]) - len(hong), am=len(hong))
        self.assertEqual([], hong, "cửa CHƯA ĐO ĐƯỢC (đối chứng dương hỏng) — không được tính "
                                   "là đã cách ly:\n  " + "\n  ".join(hong))

    def test_v3_B_khong_doc_ghi_xoa_duoc_du_lieu_cua_A(self):
        """Lượt PHỦ ĐỊNH: tenant B trên từng cửa của A."""
        kq = ket_qua_quet()
        hong = [f"{r['e']['method']} {r['duong']} (A={r['A']} B={r['B']}): " + "; ".join(r["loi_B"])
                for r in kq["cua"] if r["loi_B"]]
        ca("V3", am=len(kq["cua"]) - len(hong), duong=1 if not hong else 0)
        self.assertEqual([], hong, "CÁCH LY TENANT HỞ:\n  " + "\n  ".join(hong))

    def test_v4_csdl_cua_A_khong_bi_luot_B_dung_toi(self):
        """ẢNH CHỤP CSDL: so từng hàng trước/sau lượt B, phân loại chủ sở hữu."""
        kq = ket_qua_quet()
        ca("V4", am=1, duong=1 if not kq["thay_doi"]["vi_pham"] else 0)
        # ĐỐI CHỨNG DƯƠNG cho chính ảnh chụp: lượt B PHẢI ghi được hàng của B. Không có dòng
        # này thì "0 hàng của A bị đụng" có thể đúng chỉ vì ảnh chụp không thấy gì cả.
        self.assertGreater(kq["thay_doi"]["so_B"], 0,
                           "lượt B KHÔNG ghi được hàng nào của B ⇒ phép so ảnh chụp vô nghĩa")
        self.assertEqual([], kq["thay_doi"]["vi_pham"],
                         "DỮ LIỆU CỦA A BỊ LƯỢT B SỬA:\n  "
                         + "\n  ".join(kq["thay_doi"]["vi_pham"]))

    def test_v5_B_khong_doi_duoc_ngu_canh_sang_tenant_A(self):
        """Ca riêng cho switch-tenant: B đòi vào A ⇒ 403, và `active_tenant_id` của phiên B
        KHÔNG đổi (kiểm thẳng trong CSDL, không tin mã HTTP)."""
        n = dung_nen()
        truoc = csdl.mot("SELECT active_tenant_id t FROM sessions WHERE token_hash=?",
                         (bao_mat._hash_token(n.b_owner.cookie.split("=", 1)[1]),))["t"]
        tr = n.b_owner.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": n.ta})
        ca("V5", am=1, duong=1)
        self.assertEqual(403, tr.ma, tr.j)
        sau = csdl.mot("SELECT active_tenant_id t FROM sessions WHERE token_hash=?",
                       (bao_mat._hash_token(n.b_owner.cookie.split("=", 1)[1]),))["t"]
        self.assertEqual(truoc, sau, "phiên B bị đổi tenant dù không có membership!")
        # đối chứng dương: A đổi sang chính tenant A thì được
        tr2 = n.a_owner.goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": n.ta})
        self.assertEqual(200, tr2.ma, tr2.j)


    def test_v6_B_khong_lach_duoc_bang_tenant_id_tu_khai(self):
        """Luật cứng của dự án: `tenant_id` KHÔNG BAO GIỜ lấy từ query/body — chỉ từ phiên đã
        xác thực. Ca này bơm thẳng tenant A vào cả QUERY lẫn BODY của nhiều cửa và khẳng định:
        B không thấy dữ liệu A, và hàng B tạo ra vẫn thuộc B (kiểm thẳng trong CSDL)."""
        n = dung_nen()
        F = n.FIX
        ds = [
            ("GET", f"/api/v2/khach-hang?tenant_id={n.ta}", None),
            ("GET", f"/api/v2/don?tenant_id={n.ta}&gioi_han=500", None),
            ("GET", f"/api/v2/import?tenant_id={n.ta}", None),
            ("GET", f"/api/v2/audit?tenant_id={n.ta}", None),
            ("GET", f"/api/v2/tai-khoan-hang?tenant_id={n.ta}", None),
            ("POST", "/api/v2/don/tim", {"tenant_id": n.ta}),
            ("POST", "/api/v2/ai/job", {"loai": "chuan_hoa_truong", "tenant_id": n.ta,
                                        "vao": {"dia_chi": f"9 Pho {SI_B} HCM"}}),
        ]
        hong = []
        for method, duong, than in ds:
            tr = n.b_owner.goi(duong, method, than)
            for dv in DAU_VET_A:
                if dv in tr.text:
                    hong.append(f"{method} {duong}: RÒ {dv!r} khi B tự khai tenant_id của A")
            if tr.ma >= 500:
                hong.append(f"{method} {duong}: HTTP {tr.ma}")
        # hàng B TẠO RA với tenant_id tự khai phải thuộc B, không thuộc A
        truoc = csdl.mot("SELECT COUNT(*) c FROM khach_hang WHERE tenant_id=?", (n.ta,))["c"]
        tr = n.b_owner.goi("/api/v2/khach-hang", "POST",
                           {"ten": f"Khach tu khai {SI_B}", "tenant_id": n.ta})
        self.assertEqual(201, tr.ma, tr.j)
        sau = csdl.mot("SELECT COUNT(*) c FROM khach_hang WHERE tenant_id=?", (n.ta,))["c"]
        ca("V6", am=len(ds) + 1, duong=1 if not hong and sau == truoc else 0)
        self.assertEqual(truoc, sau, "B tạo được khách hàng GÁN VÀO TENANT A bằng body!")
        self.assertEqual([], hong, "LÁCH BẰNG tenant_id TỰ KHAI:\n  " + "\n  ".join(hong))


# =========================================================================================
# W — CỬA VÔ DANH & WEBHOOK (đối chứng dương + âm cho ba cửa không phiên)
# =========================================================================================
class W_VoDanh(unittest.TestCase):
    """Ba cửa vô danh + cửa webhook. Không có "tenant B" ở đây: kẻ gọi là NGƯỜI VÔ DANH."""

    def test_w1_dang_nhap_khong_tao_phien_cho_nguoi_sai(self):
        dung_nen()          # chạy LẺ nhóm này vẫn phải có máy chủ (CONG do hệ cấp)
        ca("W", am=1, duong=1)
        p = Phien("vd")
        tr = p.dang_nhap("b-owner", "mat-khau-sai-hoan-toan")
        self.assertEqual(401, tr.ma, tr.j)
        self.assertIsNone(p.cookie, "đăng nhập hỏng mà vẫn nhận cookie phiên!")
        ok = p.dang_nhap("b-owner", MK)
        self.assertEqual(200, ok.ma, ok.j)
        self.assertTrue(p.cookie, "đăng nhập đúng không nhận được phiên")

    def test_w2_quen_mat_khau_khong_lo_tai_khoan(self):
        dung_nen()
        ca("W", am=1, duong=1)
        p = Phien("vd")
        a1 = p.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "po"})
        a2 = p.goi("/api/v2/auth/quen-mat-khau", "POST", {"ten_dang_nhap": "khong-co-ai-ten-nay"})
        self.assertEqual(a1.ma, a2.ma)
        self.assertEqual((a1.j or {}).get("thong_bao"), (a2.j or {}).get("thong_bao"),
                         "hai câu trả lời khác nhau ⇒ dò được tài khoản nào có thật")
        self.assertNotIn("token_gia_lap", a1.j or {},
                         "cửa vô danh trả token đặt lại mật khẩu — chỉ được bật ở local có chủ ý")

    def test_w3_dat_lai_mat_khau_token_bia_thi_hong(self):
        dung_nen()
        ca("W", am=1, duong=1)
        p = Phien("vd")
        tr = p.goi("/api/v2/auth/dat-lai-mat-khau", "POST",
                   {"token": "token-bia-" + secrets.token_hex(8), "mat_khau_moi": "MatKhauMoi-999"})
        self.assertEqual(400, tr.ma, tr.j)

    def test_w4_webhook_chu_ky_sai_thi_tu_choi_va_khong_luu(self):
        """Cửa webhook: ký SAI ⇒ 401 và KHÔNG có hàng mới trong `wh_su_kien`; ký ĐÚNG ⇒ 202
        (đối chứng dương, ở `_dung_du_lieu_A`/`_ban_webhook`)."""
        n = dung_nen()
        dem_truoc = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                             (n.FIX["tk_a"],))["c"]
        body = json.dumps({"event": "da_giao", "tracking_number": SI + "-KYSAI"}).encode()
        p = Phien("vd")
        tr = p.goi(f"/api/v2/webhook/nhan/{n.wh_a}", "POST", tho=body,
                   headers={"X-Webhook-Signature": "00" * 32, "Content-Type": "application/json"})
        ca("W", am=1, duong=1)
        self.assertEqual(401, tr.ma, tr.j)
        dem_sau = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                           (n.FIX["tk_a"],))["c"]
        self.assertEqual(dem_truoc, dem_sau, "sự kiện chữ ký SAI vẫn được lưu vào CSDL!")
        # F-02: ĐO (không khẳng định) việc cửa VÔ DANH ghi audit mang `tenant_id` của CHỦ
        # tài khoản. Ba lượt nữa rồi đếm chênh lệch — con số này vào báo cáo.
        dem_a_truoc = csdl.mot("SELECT COUNT(*) c FROM audit WHERE tenant_id=? AND"
                               " hanh_dong='webhook_chu_ky_tu_choi'", (n.ta,))["c"]
        for i in range(3):
            p.goi(f"/api/v2/webhook/nhan/{n.wh_a}", "POST", tho=body + b" ",
                  headers={"X-Webhook-Signature": "11" * 32,
                           "Content-Type": "application/json"})
        DO_LUONG["audit_them_tu_webhook_sai"] = csdl.mot(
            "SELECT COUNT(*) c FROM audit WHERE tenant_id=? AND"
            " hanh_dong='webhook_chu_ky_tu_choi'", (n.ta,))["c"] - dem_a_truoc

    def test_w5_B_khong_dung_duoc_webhook_cua_A(self):
        """B gửi sự kiện vào webhook_ma của A: chữ ký của B không qua được, và KHÔNG sự kiện nào
        được ghi vào tài khoản của A."""
        n = dung_nen()
        dem_truoc = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                             (n.FIX["tk_a"],))["c"]
        body = json.dumps({"event": "da_giao", "tracking_number": SI + "-B-GUI"}).encode()
        # B ký bằng secret CỦA B (đúng cách B vẫn ký cho tài khoản của B)
        ky_B = hmac.new(n.wh_secret_b.encode(), body, hashlib.sha256).hexdigest()
        p = Phien("vd")
        tr = p.goi(f"/api/v2/webhook/nhan/{n.wh_a}", "POST", tho=body,
                   headers={"X-Webhook-Signature": ky_B, "Content-Type": "application/json"})
        ca("W", am=1, duong=1)
        self.assertEqual(401, tr.ma, tr.j)
        dem_sau = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                           (n.FIX["tk_a"],))["c"]
        self.assertEqual(dem_truoc, dem_sau, "sự kiện của B lọt vào tài khoản A!")
        # đối chứng dương: B ký ĐÚNG cho tài khoản B ⇒ 202
        ky = hmac.new(n.wh_secret_b.encode(), body, hashlib.sha256).hexdigest()
        tr2 = p.goi(f"/api/v2/webhook/nhan/{n.wh_b}", "POST", tho=body,
                    headers={"X-Webhook-Signature": ky, "Content-Type": "application/json"})
        self.assertEqual(202, tr2.ma, tr2.j)


# =========================================================================================
# X — KHÔNG LỘ BÍ MẬT (đường đọc của A cũng không được trả secret)
# =========================================================================================
class X_KhongLoBiMat(unittest.TestCase):
    def test_x1_danh_sach_tai_khoan_hang_khong_tra_secret(self):
        n = dung_nen()
        tr = n.a_owner.goi("/api/v2/tai-khoan-hang")
        ca("X", am=1, duong=1)
        self.assertEqual(200, tr.ma, tr.j)
        for bi_mat in (SI + "-KEY", SI + "-PK", SI + "-VTP", n.wh_secret_a):
            self.assertNotIn(bi_mat, tr.text,
                             "cửa danh sách tài khoản hãng trả cả secret!")
        # đối chứng dương: secret VẪN nằm trong CSDL dưới dạng bản mã v3 (không phải "đã mất")
        r = csdl.mot("SELECT credentials_ma_hoa, webhook_secret_ma_hoa FROM carrier_accounts"
                     " WHERE id=?", (n.FIX["tk_a"],))
        self.assertTrue(str(r["credentials_ma_hoa"]).startswith("v3$"))
        self.assertTrue(str(r["webhook_secret_ma_hoa"]).startswith("v3$"))


# =========================================================================================
# R — RBAC: ma trận ĐỘNG role × hành_động
# =========================================================================================
def _ma_tran_csdl():
    return {(r["role_ma"], r["perm_ma"]) for r in csdl.nhieu("SELECT * FROM role_permissions")}


class R_Rbac(unittest.TestCase):
    """V6 — quyền phải đi theo BẢNG `role_permissions`, không theo hằng viết cứng."""

    @classmethod
    def setUpClass(cls):
        dung_nen()
        cls.ma_tran_truoc = _ma_tran_csdl()

    def test_r1_moi_o_trong_bang_dung_nhu_du_lieu(self):
        """Toàn bộ lưới roles × permissions, đối chiếu TỪNG Ô với bảng."""
        roles = [r["ma"] for r in csdl.nhieu("SELECT ma FROM roles ORDER BY ma")]
        perms = [r["ma"] for r in csdl.nhieu("SELECT ma FROM permissions ORDER BY ma")]
        self.assertGreaterEqual(len(roles), 6)
        self.assertGreaterEqual(len(perms), 25)
        ma_tran = _ma_tran_csdl()
        sai = []
        for r in roles:
            for p in perms:
                mong_doi = (r, p) in ma_tran
                thuc = quyen.co_quyen(r, p)
                if mong_doi != thuc:
                    sai.append(f"{r} × {p}: bảng={mong_doi} hàm={thuc}")
        ca("R1", am=0, duong=len(roles) * len(perms))
        self.assertEqual([], sai, "RBAC LỆCH KHỎI DỮ LIỆU:\n  " + "\n  ".join(sai))
        # đối chứng âm: ô KHÔNG có trong bảng phải là False (không phải "mặc định True")
        self.assertFalse(quyen.co_quyen("TENANT_VIEWER", "platform.tenant.tao"))

    def test_r2_cap_quyen_trong_csdl_thi_ham_doi_theo(self):
        """ĐỘT BIẾN CSDL: cấp một ô KHÔNG có trong hằng `MA_TRAN` ⇒ hàm phải đổi theo.
        Đây là phép chứng minh "theo dữ liệu, không theo hằng viết cứng"."""
        role, perm = "TENANT_VIEWER", "tenant.khach.ghi"
        self.assertNotIn(perm, quyen.MA_TRAN[role], "ô này vốn đã có trong hằng — chọn ô khác")
        ca("R2", am=1, duong=1)
        self.assertFalse(quyen.co_quyen(role, perm))
        csdl.ghi("INSERT INTO role_permissions (role_ma, perm_ma) VALUES (?,?)", (role, perm))
        try:
            self.assertTrue(quyen.co_quyen(role, perm),
                            "cấp quyền trong CSDL mà hàm KHÔNG đổi ⇒ đang đọc hằng viết cứng")
            self.assertNotIn(perm, quyen.MA_TRAN[role])
        finally:
            csdl.ghi("DELETE FROM role_permissions WHERE role_ma=? AND perm_ma=?", (role, perm))
        self.assertFalse(quyen.co_quyen(role, perm))

    def test_r3_thu_quyen_trong_csdl_thi_ham_doi_theo(self):
        """Chiều ngược lại: thu một quyền ĐANG có ⇒ hàm phải từ chối."""
        role, perm = "TENANT_OWNER", "tenant.khach.xem"
        ca("R3", am=1, duong=1)
        self.assertTrue(quyen.co_quyen(role, perm))
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma=? AND perm_ma=?", (role, perm))
        try:
            self.assertFalse(quyen.co_quyen(role, perm),
                             "thu quyền trong CSDL mà hàm vẫn cho qua ⇒ đang đọc hằng viết cứng")
        finally:
            csdl.ghi("INSERT INTO role_permissions (role_ma, perm_ma) VALUES (?,?)", (role, perm))
        self.assertTrue(quyen.co_quyen(role, perm))

    def test_r4_http_doi_theo_csdl_ca_hai_chieu(self):
        """Cùng phép đột biến nhưng qua HTTP THẬT — chứng minh endpoint tra CSDL ở TỪNG yêu cầu."""
        n = dung_nen()
        # (1) CẤP: viewer được cấp `tenant.khach.ghi` ⇒ POST /khach-hang phải 201
        truoc = n.a_viewer.goi("/api/v2/khach-hang", "POST", {"ten": f"Viewer {SI}"})
        self.assertEqual(403, truoc.ma, truoc.j)
        csdl.ghi("INSERT INTO role_permissions (role_ma, perm_ma) VALUES ('TENANT_VIEWER',"
                 "'tenant.khach.ghi')")
        try:
            sau = n.a_viewer.goi("/api/v2/khach-hang", "POST", {"ten": f"Viewer {SI}"})
            self.assertEqual(201, sau.ma,
                             "cấp quyền trong CSDL mà HTTP vẫn 403 ⇒ endpoint đọc hằng viết cứng")
        finally:
            csdl.ghi("DELETE FROM role_permissions WHERE role_ma='TENANT_VIEWER'"
                     " AND perm_ma='tenant.khach.ghi'")
        lai = n.a_viewer.goi("/api/v2/khach-hang", "POST", {"ten": f"Viewer {SI}"})
        self.assertEqual(403, lai.ma)
        # (2) THU: chủ doanh nghiệp bị thu `tenant.khach.xem` ⇒ GET phải 403
        self.assertEqual(200, n.a_owner.goi("/api/v2/khach-hang").ma)
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma='TENANT_OWNER'"
                 " AND perm_ma='tenant.khach.xem'")
        try:
            bi_thu = n.a_owner.goi("/api/v2/khach-hang")
            self.assertEqual(403, bi_thu.ma,
                             "thu quyền trong CSDL mà HTTP vẫn 200 ⇒ có đường vòng cứng")
        finally:
            csdl.ghi("INSERT INTO role_permissions (role_ma, perm_ma)"
                     " VALUES ('TENANT_OWNER','tenant.khach.xem')")
        self.assertEqual(200, n.a_owner.goi("/api/v2/khach-hang").ma)
        ca("R4", am=1, duong=1)

    def test_r5_ma_tran_http_theo_tung_vai_tro(self):
        """Lưới HTTP: mỗi cửa (có khai quyền) chạy bằng bốn phiên của A. Phán quyết phải khớp
        ô `(vai_tro, quyền)` trong CSDL: THIẾU ⇒ đúng 403; CÓ ⇒ không được 403."""
        n = dung_nen()
        ma_tran = _ma_tran_csdl()
        phien = {"TENANT_OWNER": n.a_owner, "TENANT_ADMIN": n.a_admin,
                 "TENANT_STAFF": n.a_staff, "TENANT_VIEWER": n.a_viewer}
        F = n.FIX
        sai, so_o = [], 0
        for e in bang_cua():
            # MỌI cửa ĐỌC của tenant vào lưới: GET không có tác dụng phụ, nên chạy được bằng
            # cả bốn vai trò. Cửa GHI chỉ vào lưới khi có cờ `rb` (đã cân nhắc tác dụng phụ).
            if not e["quyen"] or e["loai"] == "rieng" or not e["quyen"].startswith("tenant."):
                continue
            if not (e["rb"] or e["method"] == "GET"):
                continue
            duong = _lap(e["duong"], F)
            than = e["than"]
            if isinstance(than, dict):
                than = {k: (_lap(v, F) if isinstance(v, str) else v) for k, v in than.items()}
            for role, p in phien.items():
                so_o += 1
                tr = p.goi(duong, e["method"], than)
                co = (role, e["quyen"]) in ma_tran
                if not co and tr.ma != 403:
                    sai.append(f"{role} {e['method']} {duong}: thiếu {e['quyen']} mà "
                               f"HTTP {tr.ma} (phải 403)")
                if co and tr.ma == 403:
                    sai.append(f"{role} {e['method']} {duong}: CÓ {e['quyen']} trong CSDL mà "
                               f"bị 403")
        ca("R5", am=so_o, duong=so_o)
        self.assertGreater(so_o, 150, "lưới HTTP quá nhỏ — nghi bảng cửa hỏng")
        self.assertEqual([], sai, "RBAC QUA HTTP LỆCH:\n  " + "\n  ".join(sai[:40]))

    def test_r6_moi_quyen_tham_chieu_trong_ma_phai_co_trong_bang(self):
        """Canh QUYỀN CHẾT: mọi chuỗi quyền được `_can(...)`/`co_quyen(...)` hỏi tới phải tồn tại
        trong bảng `permissions`. Ngoại lệ đã BIẾT phải khai tường minh (kèm lý do); quyền mới
        xuất hiện ngoài danh sách ⇒ ca này ĐỎ."""
        tham_chieu = _quyen_tham_chieu_trong_ma(GOC_APP)
        co_trong_bang = {r["ma"] for r in csdl.nhieu("SELECT ma FROM permissions")}
        # NGOẠI LỆ ĐÃ BIẾT (xem docs/G17_SECURITY_ISOLATION.md §phát hiện F-01):
        # `tenant.billing.quan_ly` được `server.py` hỏi nhưng KHÔNG có trong bảng permissions,
        # nên nhánh ba ngôi ở `/api/v2/dang-ky/doi-goi` là nhánh CHẾT — cửa đó trên thực tế
        # đòi `tenant.membership.quan_ly`.
        biet = {"tenant.billing.quan_ly"}
        thieu = sorted(tham_chieu - co_trong_bang)
        ca("R6", am=1, duong=1)
        self.assertEqual(sorted(biet), thieu,
                         "tập quyền tham chiếu-trong-mã mà KHÔNG có trong bảng permissions ĐỔI: "
                         f"{thieu}. Thêm quyền mới ⇒ phải seed vào `quyen.QUYEN`; nếu là ngoại lệ "
                         "đã biết thì khai vào biến `biet` kèm lý do.")
        # CHIỀU CÒN LẠI: quyền seed mà KHÔNG mã nào hỏi tới cũng là quyền CHẾT. Đo được:
        # rỗng — kể cả `platform.khoa.xoay` cũng được hỏi thật, ở đường DÒNG LỆNH
        # (`xoay_khoa.py:414 quyen.co_quyen(vai_tro, QUYEN_XOAY)`), không phải cửa HTTP.
        khong_dung = sorted(co_trong_bang - tham_chieu)
        self.assertEqual([], khong_dung,
                         f"tập quyền seed mà không mã nào hỏi tới ĐỔI: {khong_dung}")


def _quyen_tham_chieu_trong_ma(goc):
    """Trích các chuỗi quyền được hỏi qua `_can`/`_can_quyen`/`co_quyen` bằng AST (không grep,
    để không bắt nhầm NHÃN TRẦN TẦN SUẤT như 'platform.quan_tri' hay tên endpoint webhook)."""
    ra = set()
    for ten_tep in sorted(os.listdir(goc)):
        if not ten_tep.endswith(".py"):
            continue
        duong = os.path.join(goc, ten_tep)
        try:
            cay = ast.parse(_doc(duong), duong)
        except SyntaxError:
            continue
        hang = {}
        for n in cay.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                    and isinstance(n.value.value, str):
                for tg in n.targets:
                    if isinstance(tg, ast.Name):
                        hang[tg.id] = n.value.value
        for n in ast.walk(cay):
            if not isinstance(n, ast.Call):
                continue
            ten = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
            if ten not in ("_can", "_can_quyen", "_can_quyen_tc", "co_quyen"):
                continue
            for a in n.args:
                # ĐI CẢ VÀO TRONG biểu thức: `_can(nc, "platform.goi.doi" if method != "GET"
                # else "platform.tenant.xem")` — chỉ lấy đối số trực tiếp là bỏ sót quyền, và
                # bộ canh sẽ báo "quyền chết" sai (đã dính đúng một lần khi viết tệp này).
                for nut in ast.walk(a):
                    gia = None
                    if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
                        gia = nut.value
                    elif isinstance(nut, ast.Name) and nut.id in hang:
                        gia = hang[nut.id]
                    # chỉ nhận chuỗi DẠNG QUYỀN: `tai_chinh._can_quyen_tc(..., "duyet")` truyền
                    # quyền CON ('xem'/'ghi'/'duyet') — đó không phải mã quyền trong bảng.
                    if gia and re.match(r"^(tenant|platform)\.[a-z_.]+$", gia):
                        ra.add(gia)
    return ra


# =========================================================================================
# M — AES-256-GCM ĐẦY ĐỦ (bốn hàm hợp đồng: chỉ GỌI)
# =========================================================================================
class M_Aes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = dung_nen()

    def test_m1_bon_ham_hop_dong_con_nguyen_va_ghi_v3(self):
        """Hợp đồng: bốn hàm phải tồn tại ĐÚNG chữ ký, và bản mã MỚI phải mang `v3$<key_id>$`."""
        import inspect
        for ten, ts in (("ma_hoa_cred", ["cred", "tenant_id", "hang"]),
                        ("giai_ma_cred", ["ban_ma", "tenant_id", "hang"]),
                        ("ma_hoa_wh", ["secret", "webhook_ma"]),
                        ("giai_ma_wh", ["ban_ma", "webhook_ma"])):
            f = getattr(bao_mat, ten, None)
            self.assertTrue(callable(f), f"thiếu hàm hợp đồng {ten}")
            self.assertEqual(ts, [p for p in inspect.signature(f).parameters][:len(ts)],
                             f"chữ ký {ten} đã đổi — hợp đồng bị phá")
        F = self.n.FIX
        ban_ma, duoi = bao_mat.ma_hoa_cred({"api_key": SI + "-KEY"}, self.n.ta, "jt")
        mau = re.compile(r"^v3\$[A-Za-z0-9_\-]+\$[0-9a-f]{24}\$[0-9a-f]+$")
        ca("M1", am=1, duong=1)
        self.assertRegex(ban_ma, mau, "bản mã credentials KHÔNG mang key_id v3")
        self.assertEqual(bao_mat.key_id_cua(ban_ma),
                         secret_provider.nha_cung_cap().khoa_hien_hanh()[0])
        self.assertFalse(bao_mat.la_dinh_dang_cu(ban_ma))
        wh = bao_mat.ma_hoa_wh(SI + "-WH", "wh-m1")
        self.assertRegex(wh, mau, "bản mã webhook secret KHÔNG mang key_id v3")
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma, self.n.ta, "jt")["api_key"])
        self.assertEqual(SI + "-WH", bao_mat.giai_ma_wh(wh, "wh-m1"))
        # secret MỚI sinh qua HTTP cũng phải là v3 (đường sản phẩm, không chỉ tầng hàm)
        r = csdl.mot("SELECT credentials_ma_hoa, webhook_secret_ma_hoa FROM carrier_accounts"
                     " WHERE id=?", (F["tk_a"],))
        self.assertRegex(str(r["credentials_ma_hoa"]), mau)
        self.assertRegex(str(r["webhook_secret_ma_hoa"]), mau)
        self.assertEqual({"api_key": SI + "-KEY", "privateKey": SI + "-PK"},
                         bao_mat.giai_ma_cred(r["credentials_ma_hoa"], self.n.ta, "jt"))

    def test_m2_sua_mot_byte_ban_ma_thi_giai_ma_hong(self):
        """V7a — AEAD: sửa 1 byte ⇒ HỎNG. Kèm đối chứng dương (bản gốc giải được)."""
        n = self.n
        ban_ma = csdl.mot("SELECT credentials_ma_hoa m FROM carrier_accounts WHERE id=?",
                          (n.FIX["tk_a"],))["m"]
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma, n.ta, "jt")["api_key"])
        phan = ban_ma.split("$")
        self.assertEqual(4, len(phan))
        ct = bytearray(bytes.fromhex(phan[3]))
        ct[0] ^= 0x01
        phan[3] = bytes(ct).hex()
        ban_ma_sua = "$".join(phan)
        ca("M2", am=1, duong=1)
        with self.assertRaises(Exception, msg="sửa 1 byte mà VẪN giải được ⇒ AEAD không còn"):
            bao_mat.giai_ma_cred(ban_ma_sua, n.ta, "jt")
        # sửa byte trong phần NONCE cũng phải hỏng
        phan2 = ban_ma.split("$")
        nc = bytearray(bytes.fromhex(phan2[2]))
        nc[0] ^= 0x01
        phan2[2] = bytes(nc).hex()
        with self.assertRaises(Exception):
            bao_mat.giai_ma_cred("$".join(phan2), n.ta, "jt")

    def test_m3_doi_cho_ban_ma_giua_hai_tenant_trong_csdl_thi_hong(self):
        """V7b — AAD: chép bản mã credentials của B vào hàng của A (cùng hãng 'jt') ⇒ HỎNG.
        Đo CẢ HAI đường: hàm hợp đồng và đường HTTP thật (`gui_don` giải mã credentials)."""
        n = self.n
        st, kq = n.b_owner.goi("/api/v2/tai-khoan-hang", "POST",
                               {"hang": "jt", "ten": f"JT doi cho {SI_B}", "moi_truong": "mock",
                                "credentials": {"privateKey": SI_B + "-PK"}})
        self.assertEqual(201, st, kq)
        tk_b = kq["id"]
        n.FIX["tk_b"] = tk_b
        ban_ma_b = csdl.mot("SELECT credentials_ma_hoa m FROM carrier_accounts WHERE id=?",
                            (tk_b,))["m"]
        ban_ma_a = csdl.mot("SELECT credentials_ma_hoa m FROM carrier_accounts WHERE id=?",
                            (n.FIX["tk_a"],))["m"]
        # đối chứng dương trước: mỗi bản mã giải được ở ĐÚNG chỗ của nó
        self.assertEqual(SI_B + "-PK", bao_mat.giai_ma_cred(ban_ma_b, n.tb, "jt")["privateKey"])
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma_a, n.ta, "jt")["api_key"])
        # ĐỔI CHỖ trong CSDL
        csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?", (ban_ma_b, n.FIX["tk_a"]))
        try:
            ca("M3", am=1, duong=1)
            with self.assertRaises(Exception, msg="bản mã của B nằm ở hàng A mà VẪN giải được"):
                bao_mat.giai_ma_cred(ban_ma_b, n.ta, "jt")
            # đường HTTP: gửi đơn của A qua tài khoản A (credentials đã bị tráo) ⇒ KHÔNG được 200
            ma_don = csdl.mot("SELECT ma_don FROM don_hang WHERE id=?", (n.FIX["don_gui"],))["ma_don"]
            truoc = csdl.mot("SELECT trang_thai t FROM don_hang WHERE id=?",
                             (n.FIX["don_gui"],))["t"]
            tr = n.a_owner.goi(f"/api/v2/don/{n.FIX['don_gui']}/gui", "POST",
                               {"carrier_account_id": n.FIX["tk_a"]})
            self.assertNotEqual(200, tr.ma, f"tráo bản mã mà vẫn gửi được đơn: {tr.j}")
            sau = csdl.mot("SELECT trang_thai t FROM don_hang WHERE id=?",
                           (n.FIX["don_gui"],))["t"]
            self.assertEqual("da_duyet", sau, f"đơn {ma_don} đổi trạng thái {truoc}→{sau} "
                                              "dù credentials không giải được")
        finally:
            csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                     (ban_ma_a, n.FIX["tk_a"]))
        # đối chứng dương SAU khi hoàn nguyên: cửa gửi chạy lại được
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma_a, n.ta, "jt")["api_key"])

    def test_m4_doi_cho_webhook_secret_giua_hai_tenant_thi_hong(self):
        """V7b (đường thứ hai) — tráo `webhook_secret_ma_hoa` giữa A và B ⇒ chữ ký ĐÚNG của A
        không còn qua được; và đối chứng dương là chính chữ ký đó trước khi tráo."""
        n = self.n
        r_a = csdl.mot("SELECT webhook_ma, webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?",
                       (n.FIX["tk_a"],))
        r_b = csdl.mot("SELECT webhook_ma, webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?",
                       (n.FIX["tk_b"],))
        body = json.dumps({"event": "da_giao", "tracking_number": SI + "-M4"}).encode()
        p = Phien("vd")
        ky = hmac.new(n.wh_secret_a.encode(), body, hashlib.sha256).hexdigest()
        hd = {"X-Webhook-Signature": ky, "Content-Type": "application/json"}
        ok = p.goi(f"/api/v2/webhook/nhan/{r_a['webhook_ma']}", "POST", tho=body, headers=hd)
        self.assertIn(ok.ma, (200, 202), f"đối chứng dương hỏng trước khi tráo: {ok.j}")
        csdl.ghi("UPDATE carrier_accounts SET webhook_secret_ma_hoa=? WHERE id=?",
                 (r_b["webhook_secret_ma_hoa"], n.FIX["tk_a"]))
        try:
            ca("M4", am=1, duong=1)
            with self.assertRaises(Exception):
                bao_mat.giai_ma_wh(r_b["webhook_secret_ma_hoa"], r_a["webhook_ma"])
            dem = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                           (n.FIX["tk_a"],))["c"]
            tr = p.goi(f"/api/v2/webhook/nhan/{r_a['webhook_ma']}", "POST", tho=body, headers=hd)
            self.assertEqual(401, tr.ma,
                             f"secret bị tráo mà chữ ký cũ VẪN qua được: {tr.j}")
            self.assertEqual(dem, csdl.mot("SELECT COUNT(*) c FROM wh_su_kien WHERE"
                                           " carrier_account_id=?", (n.FIX["tk_a"],))["c"])
        finally:
            csdl.ghi("UPDATE carrier_accounts SET webhook_secret_ma_hoa=? WHERE id=?",
                     (r_a["webhook_secret_ma_hoa"], n.FIX["tk_a"]))

    def test_m5_sai_aad_thi_hong(self):
        """V7c — sai AAD (sai tenant / sai hãng / sai webhook_ma) ⇒ HỎNG; đúng AAD ⇒ ĐƯỢC."""
        n = self.n
        ban_ma, _ = bao_mat.ma_hoa_cred({"api_key": SI + "-KEY"}, n.ta, "jt")
        wh = bao_mat.ma_hoa_wh(SI + "-WH", "wh-m5")
        ca("M5", am=3, duong=2)
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma, n.ta, "jt")["api_key"])
        self.assertEqual(SI + "-WH", bao_mat.giai_ma_wh(wh, "wh-m5"))
        for tid, hang in ((n.tb, "jt"), (n.ta, "vtp"), (n.ta, "jt "), (99999, "jt")):
            with self.assertRaises(Exception, msg=f"AAD sai ({tid},{hang!r}) mà vẫn giải được"):
                bao_mat.giai_ma_cred(ban_ma, tid, hang)
        for ma_khac in ("wh-m5-khac", "", "wh-m5 "):
            with self.assertRaises(Exception):
                bao_mat.giai_ma_wh(wh, ma_khac)
        # gọi trần `giai_ma` với AAD rỗng cũng phải hỏng (không có đường AAD rỗng lách qua)
        with self.assertRaises(Exception):
            bao_mat.giai_ma(ban_ma, "")

    def test_m6_sai_key_id_thi_hong_va_khong_sinh_khoa_moi(self):
        """key_id trong bản mã phải được DÙNG: đổi sang key_id không tồn tại ⇒ hỏng; đổi sang
        một key_id CÓ THẬT (khóa khác) ⇒ cũng hỏng. Không được âm thầm sinh khóa mới."""
        n = self.n
        ban_ma, _ = bao_mat.ma_hoa_cred({"api_key": SI + "-KEY"}, n.ta, "jt")
        phan = ban_ma.split("$")
        bia = "$".join([phan[0], "khong-co-key-nay", phan[2], phan[3]])
        ca("M6", am=2, duong=1)
        self.assertEqual(SI + "-KEY", bao_mat.giai_ma_cred(ban_ma, n.ta, "jt")["api_key"])
        with self.assertRaises(Exception):
            bao_mat.giai_ma_cred(bia, n.ta, "jt")
        p = secret_provider.nha_cung_cap()
        kd_cu = p.khoa_hien_hanh()[0]
        kd_moi = p.tao_khoa_moi()          # khóa MỚI có thật, nhưng KHÔNG phải khóa của bản mã
        try:
            doi = "$".join([phan[0], kd_moi, phan[2], phan[3]])
            with self.assertRaises(Exception, msg="đổi key_id sang khóa khác mà vẫn giải được"):
                bao_mat.giai_ma_cred(doi, n.ta, "jt")
            self.assertEqual(kd_cu, bao_mat.key_id_cua(ban_ma))
        finally:
            p.dat_khoa_hien_hanh(kd_cu)

    def test_m7_aes_that_su_chay_va_co_iv_khac_nhau(self):
        """Đối chứng DƯƠNG cuối: cùng plaintext hai lượt ⇒ hai bản mã KHÁC NHAU (nonce ngẫu
        nhiên), và cả hai đều giải đúng. Không có ca này thì "hỏng khi sửa byte" có thể đúng
        một cách vô nghĩa vì mọi thứ đều hỏng."""
        n = self.n
        b1, _ = bao_mat.ma_hoa_cred({"k": SI}, n.ta, "jt")
        b2, _ = bao_mat.ma_hoa_cred({"k": SI}, n.ta, "jt")
        ca("M7", am=1, duong=2)
        self.assertNotEqual(b1, b2, "hai bản mã giống nhau ⇒ nonce bị dùng lại")
        self.assertEqual({"k": SI}, bao_mat.giai_ma_cred(b1, n.ta, "jt"))
        self.assertEqual({"k": SI}, bao_mat.giai_ma_cred(b2, n.ta, "jt"))
        with self.assertRaises(Exception):
            bao_mat.giai_ma_cred(b1, n.ta, "vtp")


# =========================================================================================
# E — TỰ KIỂM BỘ ĐO (làm nó ĐỎ được)
# =========================================================================================
class E_TuKiemBoDo(unittest.TestCase):
    def test_e1_ca_co_y_hong_trong_tien_trinh_con_thi_bo_do_thay(self):
        """Chạy một ca CỐ Ý HỎNG trong tiến trình con: bộ dò phải thấy mã thoát ≠ 0 và không có
        dòng OK. Không có ca này thì "mọi ca xanh" không chứng minh gì."""
        ma = ("import unittest\n"
              "class X(unittest.TestCase):\n"
              "    def test_x(self):\n"
              "        self.assertEqual(1, 2, 'ca co y hong')\n"
              "unittest.main(verbosity=2)\n")
        r = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True, timeout=60)
        ca("E", am=1, duong=1)
        self.assertNotEqual(0, r.returncode, "bộ dò KHÔNG thấy ca hỏng")
        self.assertNotRegex(r.stderr, r"(?m)^OK$")

    def test_e2_canh_khai_bao_route_thay_route_moi(self):
        """Tiêm một route GIẢ vào bản sao `server.py` ⇒ phép canh KHAI BÁO phải kêu thiếu."""
        goc = _doc(os.path.join(GOC_APP, "server.py"))
        gia = '        if duong == "/api/v2/zz-kiem-tra-dot-bien" and method == "GET":\n' \
              '            return self._tra(200, {"ok": True})\n'
        neo = '        return self._tra(404, {"loi": "không có đường này"})\n\n\ndef chay('
        self.assertIn(neo, goc, "không tìm được chỗ tiêm — bộ tự kiểm cần cập nhật")
        ban_sao = os.path.join(_tam, "server_dot_bien.py")
        with open(ban_sao, "w", encoding="utf-8") as f:
            f.write(goc.replace(neo, gia + neo, 1))
        thay = _cua_tu_nguon(ban_sao)
        khai = {e["duong"] for e in bang_cua()}
        ca("E", am=1, duong=1)
        self.assertIn("/api/v2/zz-kiem-tra-dot-bien", {d for d, m in thay},
                      "phép trích route KHÔNG thấy route giả ⇒ bộ canh mù")
        self.assertNotIn("/api/v2/zz-kiem-tra-dot-bien", khai)
        # và ca canh thật sự kêu: mô phỏng đúng phép so của test_v1
        thieu = [(d, m) for (d, m) in thay if m not in {"GET"} or d not in khai]
        self.assertTrue(thieu, "phép canh khai báo không kêu khi có route lạ")

    def test_e3_bo_do_ro_ri_thay_phan_hoi_co_ro(self):
        """Đưa bộ dò rò rỉ một phản hồi GIẢ CÓ chứa dấu vết A ⇒ phải kêu; phản hồi SẠCH ⇒ im.
        Không có ca này thì "không rò" có thể chỉ là do bộ dò luôn im."""
        e = {"chan_B": (200,)}
        sach = _quyet_dinh_B(e, 200, '{"don": []}')
        ro = _quyet_dinh_B(e, 200, '{"khach_hang": [{"ten": "Khach %s"}]}' % SI)
        ca("E", am=1, duong=1)
        self.assertEqual([], sach)
        self.assertTrue(any("RÒ" in x for x in ro), f"bộ dò KHÔNG thấy rò rỉ: {ro}")
        # và nó cũng phải kêu khi mã HTTP sai kỳ vọng
        self.assertTrue(_quyet_dinh_B(e, 500, "loi"))

    def test_e4_chay_tren_ban_sao_dot_bien_thi_bo_thu_DO(self):
        """CHỐT CHẶN MẠNH NHẤT: sao toàn bộ `app/` sang thư mục tạm, BỎ BỘ LỌC TENANT của
        `GET /api/v2/khach-hang/<id>` rồi chạy CHÍNH tệp này ở bản sao đó. Bộ thử phải ĐỎ và
        phải chỉ đúng cửa vừa bị phá. Không có ca này thì mọi lời "bộ thử có răng" là lời nói."""
        if os.environ.get("VIP_AG06_KHONG_TU_DOT_BIEN") == "1":
            self.skipTest("đang chạy trong lượt đột biến (chống đệ quy)")
        goc_app = os.path.join(_tam, "cay-dot-bien", "app")
        if os.path.isdir(os.path.dirname(goc_app)):
            shutil.rmtree(os.path.dirname(goc_app))
        shutil.copytree(GOC_APP, goc_app)
        tep = os.path.join(goc_app, "server.py")
        src = _doc(tep)
        # ĐỘT BIẾN ĐÚNG NGHĨA: bỏ bộ lọc tenant mà GIỮ ĐÚNG số tham số. Bản đột biến chỉ xoá
        # chuỗi ` AND tenant_id=?` là bản HỎNG CÚ PHÁP SQL (thừa tham số) ⇒ 500 cho cả hai
        # tenant — bộ thử đỏ vì "chưa đo được", KHÔNG phải vì bắt được rò rỉ. Đo thử một lần
        # rồi mới biết: đột biến phải làm HỞ THẬT thì mới chứng minh được bộ dò có răng.
        neo = ('kh = csdl.mot("SELECT * FROM khach_hang WHERE id=? AND tenant_id=?",\n'
               '                          (int(m.group(1)), tenant_id))')
        moi = ('kh = csdl.mot("SELECT * FROM khach_hang WHERE id=?", (int(m.group(1)),))')
        self.assertIn(neo, src, "không tìm được chỗ đột biến — cập nhật ca này")
        with open(tep, "w", encoding="utf-8") as f:
            f.write(src.replace(neo, moi, 1))
        du_lieu = os.path.join(_tam, "du-lieu-dot-bien")
        moi_truong = dict(os.environ, VIP_HUB_DATA=du_lieu, VIP_AG06_KHONG_TU_DOT_BIEN="1")
        r = subprocess.run([sys.executable, os.path.join(goc_app, "thu", "thu_g17_baomat.py")],
                           capture_output=True, text=True, timeout=900, env=moi_truong, cwd=_tam)
        ra = r.stdout + r.stderr
        ca("E", am=1, duong=1)
        self.assertNotEqual(0, r.returncode,
                            "bản sao BỎ BỘ LỌC TENANT mà bộ thử vẫn XANH:\n" + ra[-3000:])
        self.assertIn("RÒ dấu vết của A", ra,
                      "bộ thử đỏ nhưng KHÔNG nói đó là RÒ RỈ dữ liệu:\n" + ra[-3000:])
        self.assertRegex(ra, r"khach-hang/\d+",
                         "bộ thử đỏ nhưng KHÔNG chỉ ra cửa vừa bị phá:\n" + ra[-3000:])


def _doc(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        return f.read()


def _cua_tu_nguon(duong_dan):
    """Trích mọi cặp (route, method) mà `server.py` thật sự so sánh, bằng AST + thứ tự nguồn.

    Vì sao AST chứ không grep: grep bắt cả chuỗi chỉ để DỰNG URL (`f"/api/v2/webhook/nhan/…"`)
    và cả nhãn trần tần suất — bộ canh sẽ kêu nhầm rồi bị tắt đi, đúng kiểu hỏng §12.2.
    """
    cay = ast.parse(_doc(duong_dan), duong_dan)
    nut = sorted(ast.walk(cay), key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))
    ra, dang_cho = {}, None

    def them(mau, method, ln):
        for p in _mo_rong(_chuan_hoa(mau)):
            ra[(p, method)] = ln

    for n in nut:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) \
                and getattr(n.value.func, "attr", None) == "fullmatch":
            a = n.value.args
            if a and isinstance(a[0], ast.Constant) and isinstance(a[0].value, str) \
                    and a[0].value.startswith("/api/v2"):
                dang_cho = a[0].value
            continue
        if not isinstance(n, ast.If):
            continue
        chuoi = [c.value for c in ast.walk(n.test) if isinstance(c, ast.Constant)
                 and isinstance(c.value, str) and c.value.startswith("/api/v2")]
        if chuoi:
            ms = _phuong_thuc(n.test) or {None}
            for c in chuoi:
                for m in ms:
                    them(c, m, n.lineno)
            dang_cho = None
            continue
        if dang_cho and any(isinstance(x, ast.Name) and x.id == "m" for x in ast.walk(n.test)):
            ms = _phuong_thuc(n.test)
            if not ms:
                for sub in ast.walk(n):
                    if isinstance(sub, ast.If) and sub is not n:
                        ms |= _phuong_thuc(sub.test)
            for m in (ms or {None}):
                them(dang_cho, m, n.lineno)
    return ra


def _phuong_thuc(test):
    ra = set()
    for n in ast.walk(test):
        if isinstance(n, ast.Compare) and any(
                isinstance(x, ast.Name) and x.id == "method" for x in [n.left]):
            for c in n.comparators:
                for k in ast.walk(c):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        ra.add(k.value)
    return ra


def _chuan_hoa(p):
    return p.replace(r"(\d+)", "{id}").replace(r"([A-Za-z0-9_-]+)", "{ma}")


def _chuan_hoa_khai(p):
    """Đưa tên tham số FIXTURE trong bảng cửa (`{kh_a}`, `{don_a}`…) về dạng của server.py."""
    return re.sub(r"\{(?!ma\})[a-z_0-9]+\}", "{id}", p)


def _mo_rong(p):
    m = re.search(r"\(([^()]*\|[^()]*)\)", p)
    if not m:
        return [p]
    ra = []
    for phan in m.group(1).split("|"):
        ra += _mo_rong(p[:m.start()] + phan + p[m.end():])
    return ra


# =========================================================================================
# Z — TỔNG KẾT: mọi nhóm có ca ÂM phải có ca DƯƠNG
# =========================================================================================
class Z_TongKet(unittest.TestCase):
    def test_z1_moi_nhom_co_ca_am_deu_co_ca_duong(self):
        thieu = [k for k, v in SO_CA.items() if v["am"] > 0 and v["duong"] == 0]
        self.assertEqual([], thieu, f"nhóm có ca ÂM mà KHÔNG có ca DƯƠNG: {thieu}")
        self.assertGreaterEqual(len(SO_CA), 5, f"quá ít nhóm được ghi sổ: {SO_CA}")

    def test_z2_in_so_do_pham_vi(self):
        kq = ket_qua_quet()
        n = dung_nen()
        so_chat = sum(1 for r in kq["cua"] if r["e"]["chat"])
        print("\n===== PHẠM VI ĐÃ ĐO (AG-06) =====")
        print(f"  CSDL      : SQLite schema v{n.phien_ban} tại {_tam}")
        print(f"  máy chủ   : 127.0.0.1:{CONG} (cổng 0, hệ tự cấp) · tiến trình đơn")
        print(f"  cửa quét  : {len(kq['cua'])} lượt cửa × 2 (A đối chứng dương + B phủ định) "
              f"= {2 * len(kq['cua'])} lượt HTTP")
        print(f"  đo CHẶT   : {so_chat} cửa (mã chính xác + dấu vết A) · "
              f"đo 'qua được cửa': {len(kq['cua']) - so_chat} cửa ghi có hồ sơ sâu")
        so_luoi = len([e for e in bang_cua() if e["quyen"] and e["loai"] != "rieng"
                       and e["quyen"].startswith("tenant.")
                       and (e["rb"] or e["method"] == "GET")])
        print(f"  RBAC      : lưới HTTP {so_luoi} cửa × 4 vai trò tenant = {so_luoi * 4} ô · "
              f"ma trận CSDL roles × permissions = 168 ô (đối chiếu từng ô)")
        print(f"  ảnh chụp  : hàng của B đổi trong lượt B: {kq['thay_doi']['so_B']} · "
              f"hàng CỦA A bị đụng: {len(kq['thay_doi']['vi_pham'])} · "
              f"audit thiếu nhãn tenant: {kq['thay_doi']['so_audit_null']}"
              + (f" ({', '.join(kq['thay_doi']['vi_du_null'])})" if kq['thay_doi']['vi_du_null'] else ""))
        if kq["thay_doi"]["so_khac"]:
            print(f"              hàng chủ khác (không phải A, không phải B): "
                  f"{kq['thay_doi']['so_khac']}")
        if "audit_them_tu_webhook_sai" in DO_LUONG:
            print(f"  đo thêm   : 3 lượt webhook CHỮ KÝ SAI (vô danh) ⇒ audit của tenant A thêm "
                  f"{DO_LUONG['audit_them_tu_webhook_sai']} dòng (F-02); wh_su_kien: 0 dòng")
        for g in kq["thay_doi"]["ghi_chu"]:
            print("   · " + g)
        print("  sổ nhóm   :", ", ".join(f"{k}(âm {v['am']}/dương {v['duong']})"
                                         for k, v in sorted(SO_CA.items())))
        print("  NGOÀI PHẠM VI: hãng thật/sandbox (adapter MOCK, không ra mạng) · PostgreSQL "
              "(D-8, vẫn SQLite) · nhiều tiến trình · TLS thật · triển khai · giao diện trình "
              "duyệt · CAP_DUOC (hằng trong mã, không nằm trong role_permissions)")
        print("=================================")


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        if NEN is not None:
            try:
                sys.stderr.flush()
                sys.stderr = NEN.stderr_cu
            except Exception:                                            # noqa: BLE001
                pass
