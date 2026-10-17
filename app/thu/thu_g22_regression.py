#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — AGENT 04 · REGRESSION & SECURITY: BẢY MẶT, MỖI MẶT MỘT BẰNG CHỨNG ĐO ĐƯỢC.

VÌ SAO CÓ TỆP NÀY
=================
Lượt G22 có sáu làn, mỗi làn sửa một thứ. Sau sáu làn, câu hỏi hồi quy duy nhất còn đáng hỏi là:
*bảy tính chất an toàn dưới đây còn ĐÚNG không, và ĐO ĐƯỢC bằng gì?* Tệp này không sửa một dòng
mã sản phẩm nào; nó chỉ DỰNG NỀN GIẢ LẬP rồi đo:

    1. TENANT ISOLATION   — A không đọc được dữ liệu của B.
    2. RBAC               — vai không đủ quyền bị chặn ĐÚNG MÃ; vai đủ quyền đi qua được.
    3. FAIL-CLOSED        — thiếu cấu hình / bản sao lưu hỏng ⇒ TỪ CHỐI, không im lặng.
    4. IDEMPOTENCY        — cùng một yêu cầu gửi hai lần ⇒ KHÔNG nhân đôi.
    5. WEBHOOK SECURITY   — chữ ký sai bị từ chối; chữ ký đúng đi qua.
    6. KHÔNG RÒ RỈ CHÉO TENANT — thân phản hồi, log, và TỆP BẰNG CHỨNG do chính bộ đo ghi ra đĩa.
    7. KHÔNG GỬI ĐƠN PRODUCTION NGOÀI Ý MUỐN — mọi kết nối ra ngoài đều là loopback; mọi lệnh gọi
       hãng ở môi trường thật đều bị TỪ CHỐI (`CHO_PHEP_LIVE=False`).

LUẬT TỰ ÁP (không có thì mọi chữ "ĐẠT" ở đây vô nghĩa)
======================================================
A. **Mỗi ca PHỦ ĐỊNH phải có ĐỐI CHỨNG ĐƯỜNG.** "A không đọc được B" chỉ có nghĩa khi chứng minh
   được A ĐỌC ĐƯỢC A (200 + đúng dữ liệu A). Cùng nguyên tắc cho RBAC (vai đủ quyền đi qua),
   fail-closed (đường đúng vẫn chạy), webhook (chữ ký đúng đi qua), idempotency (khoá KHÁC thì
   CÓ nhân đôi — nên phép đếm NHÌN THẤY được sự nhân đôi), và mạng (một đích KHÔNG loopback bị
   bộ ghi nhận BẮT được, chứng minh bộ ghi không mù).
B. **Kim tự tháp "phép đo bắt được lỗi":** mỗi mặt ghi lại một phép TIÊM LỖI — làm cho phép đo
   phải ĐỎ nếu nó thật sự nhìn thấy thứ nó tuyên bố nhìn thấy. Sổ `TIEM_LOI` ở cuối tự phán HỎNG
   nếu thiếu mặt nào.
C. **Không skip.** Mọi thứ đo được local. Chỗ nào không dựng được phép đo thì báo HỎNG, không
   giả vờ BỎ QUA.
D. **Chỉ dữ liệu GIẢ.** Mọi tên/số/credential trong tệp này là chuỗi tự đặt. CSDL là thư mục
   `mktemp`; máy chủ HTTP là `127.0.0.1` cổng do hệ điều hành cấp. KHÔNG gọi API hãng (kể cả
   sandbox) · KHÔNG mở `CHO_PHEP_LIVE` · KHÔNG đụng `:5432` · KHÔNG đọc `.env`.

ĐỌC KÈM
=======
    docs/QA_G22.md §2 (baseline), §7 (chưa đo) · docs/OWNER_ACTIONS.md C4 (= D-8, BLOCKED OWNER,
    KHÔNG thực hiện) · docs/G22_SAOLUU.md §3 (chốt kho đang chạy), §8 (bất biến).

CHẠY
====
    python3 app/thu/thu_g22_regression.py            # mã thoát 0 = bảy mặt đều ĐẠT
    python3 app/thu/thu_g22_regression.py -v         # in tên từng ca

Ghi chú phạm vi: tệp này KHÔNG đo phần `KHO_DANG_CHAY` ở mức sửa mã (làn AGENT 01 sở hữu tệp
`app/cau_hinh.py`/`app/migrate.py`). Nó chỉ ĐO HÀNH VI qua **tiến trình con riêng** (mã thoát,
thông điệp, tệp trên đĩa) — không sửa một byte nào của làn khác.

CHỐT CÂY: `git write-tree` bị sandbox chặn ghi `.git/index.lock` (lỗi môi trường đã biết, xem
`docs/QA_G22.md` §8.1). Bộ này KHÔNG tự vượt; nó chỉ đọc. Việc commit là của AG-00.
"""
import ast
import contextlib
import hashlib
import hmac
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

# =================================================================================================
# 0. NỀN ĐO — thư mục TẠM riêng, đặt biến môi trường TRƯỚC khi nạp mô-đun sản phẩm
# =================================================================================================
GOC_CAY = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(GOC_CAY, "app")
sys.path.insert(0, GOC_APP)

TMP = tempfile.mkdtemp(prefix="veh-g22-a4-regression-")
os.environ["VIP_HUB_DATA"] = os.path.join(TMP, "du-lieu")
os.environ["VIP_HUB_BACKOFF"] = "0.05"
# Môi trường KẾ THỪA không được quyết định kết quả: một `VIP_KHO_DANG_CHAY` lọt vào từ shell sẽ
# làm nhánh "chưa khai" không bao giờ chạy (đúng lỗi `kich_ban.py` của làn AG-02 đã ghi).
os.environ.pop("VIP_KHO_DANG_CHAY", None)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import adapter        # noqa: E402
import adapter_jt     # noqa: E402,F401  (đăng ký lớp adapter vào `adapter._DANG_KY`)
import adapter_vtp    # noqa: E402,F401
import bao_mat        # noqa: E402
import cau_hinh       # noqa: E402
import csdl           # noqa: E402
import don_hang       # noqa: E402
import http_jt        # noqa: E402
import khoi_tao       # noqa: E402
import quan_sat       # noqa: E402
import quyen          # noqa: E402
import server         # noqa: E402

MK = "MatKhauGiaLap-A4-123"

# Dấu hiệu CHỈ CHỮ CÁI, cố ý: bộ che đường dẫn của log (`http_jt._la_doan_bi_mat`) chỉ che đoạn
# trộn chữ+ số trông như credential. Dấu hiệu toàn chữ đi qua NGUYÊN VĂN, nên ca "log có chứa
# dấu hiệu khi nó thật sự nằm trong đường dẫn" đo được đối chứng dương — nếu dấu hiệu bị che,
# ta không phân biệt được "không rò" với "bộ che ăn mất chứng cứ".
MAT_A = "MATADANHDAU"
MAT_B = "MATBDANHDAU"

# Bảy mặt — tên cố định, dùng cho sổ bằng chứng và cho phán quyết cuối.
BAY_MAT = [
    "1-tenant-isolation",
    "2-rbac",
    "3-fail-closed",
    "4-idempotency",
    "5-webhook-security",
    "6-khong-ro-ri-cheo-tenant",
    "7-khong-gui-don-production",
]

BANG = {}        # mat -> [ {ca, do, dc} ]  (chỉ ghi SAU khi mọi assertion của ca đã qua)
TIEM_LOI = {}    # mat -> mô tả phép tiêm chứng minh phép đo KHÔNG mù


def _ghi(mat, ca, do, dc):
    """Ghi một dòng bằng chứng. Gọi ở CUỐI ca, sau assertion — ca hỏng thì không có dòng."""
    assert mat in BAY_MAT, f"mặt lạ: {mat}"
    BANG.setdefault(mat, []).append({"ca": ca, "do": do, "dc": dc})


# =================================================================================================
# 1. CHỐT MẠNG — GHI NHẬN MỌI KẾT NỐI, CHẶN MỌI ĐÍCH NGOÀI LOOPBACK (trước khi mở socket)
# =================================================================================================
class ChanMangNgoai(AssertionError):
    """Bộ đo cố nối ra ngoài vòng lặp. Đây là HỎNG của bộ đo, không phải của sản phẩm."""


def _la_loopback(host):
    if not isinstance(host, str):
        return False
    return host in ("localhost", "::1") or host.startswith("127.")


class GhiMang:
    """Vá `socket.socket.connect`: GHI LẠI đích rồi mới quyết định.

    Vì sao vá ở tầng socket chứ không phải đọc mã: câu cần trả lời là *"lượt chạy này có mở kết
    nối ra ngoài không"*, và chỉ tầng syscall trả lời được câu đó — một dòng `urlopen` trong mã
    sản phẩm có thể bị thay bằng thư viện khác mà không ai thấy.

    Đích KHÔNG loopback: GHI NHẬN rồi NÉM trước khi gọi `connect` thật ⇒ không một byte nào ra
    khỏi máy. Đó vừa là chốt an toàn, vừa là phép TIÊM LỖI: ca G4 tiêm một đích TEST-NET
    (RFC 5737, không định tuyến được) và đòi bộ ghi phải BẮT ĐƯỢC nó.
    """

    def __init__(self):
        self.da_noi = []
        self._goc = None

    def bat(self):
        if self._goc is not None:
            return self
        self._goc = socket.socket.connect
        goc, da_noi = self._goc, self.da_noi

        def connect(sock, dia_chi, *a, **kw):
            if isinstance(dia_chi, (tuple, list)) and dia_chi:
                host = dia_chi[0]
                port = dia_chi[1] if len(dia_chi) > 1 else None
            else:
                host, port = dia_chi, None
            da_noi.append((host, port))
            if not _la_loopback(host):
                # Đóng socket trước khi ném: `socket.create_connection` không dọn hộ khi `connect`
                # ném, nên để nguyên là rò một fd mỗi lượt tiêm — nhiễu đúng vào lúc đang đo.
                try:
                    sock.close()
                except OSError:
                    pass
                raise ChanMangNgoai(
                    "CHẶN MẠNG G22: bộ đo định nối ra %r:%r — chỉ được loopback. "
                    "V-G09-01/V-13906-05 CHƯA CẤP nên không lượt gọi hãng nào được phép."
                    % (host, port))
            return goc(sock, dia_chi, *a, **kw)

        socket.socket.connect = connect
        return self

    def tat(self):
        if self._goc is not None:
            socket.socket.connect = self._goc
            self._goc = None

    def ngoai_loopback(self):
        return [x for x in self.da_noi if not _la_loopback(x[0])]


GHI_MANG = GhiMang().bat()

# =================================================================================================
# 2. HTTP — chỉ tới 127.0.0.1, cổng do hệ điều hành cấp
# =================================================================================================
CONG = 0


def URL_GOC():
    return "http://127.0.0.1:%d" % CONG


def _doc_than(raw, loai):
    try:
        if "json" in (loai or "") or raw[:1] in (b"{", b"["):
            return json.loads(raw)
    except ValueError:
        pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw


class Phien:
    """Phiên HTTP. `goi` tự gắn CSRF cho POST/PUT/DELETE (đường thật đòi header đó)."""

    def __init__(self):
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, headers=None, tho=None):
        body = tho if tho is not None else (
            json.dumps(du_lieu, ensure_ascii=False).encode("utf-8") if du_lieu is not None else None)
        h = dict(headers or {})
        if method in ("POST", "PUT", "DELETE") and "X-Requested-With" not in h:
            h["X-Requested-With"] = "VIPHub"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(URL_GOC() + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=20) as ph:
                raw = ph.read()
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                return ph.status, _doc_than(raw, ph.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as e:
            raw = e.read()
            return e.code, _doc_than(raw, e.headers.get("Content-Type", ""))

    def dang_nhap(self, ten, mk=MK):
        return self.goi("/api/v2/auth/dang-nhap", "POST",
                        {"ten_dang_nhap": ten, "mat_khau": mk})


def phien(ten, mk=MK):
    p = Phien()
    st, kq = p.dang_nhap(ten, mk)
    assert st == 200, "đăng nhập %s hỏng: %s %s" % (ten, st, kq)
    return p


# =================================================================================================
# 3. NỀN GIẢ LẬP — hai tenant, hai chủ, ba vai trong A, dữ liệu đánh dấu riêng
# =================================================================================================
FIX = {}


def _db1(sql, tham_so=()):
    return csdl.mot(sql, tham_so)


def _dbn(sql, tham_so=()):
    return csdl.nhieu(sql, tham_so)


def _dem(sql, tham_so=()):
    return int(_db1(sql, tham_so)["c"])


DON_GOC = {
    "nguoi_gui_ten": "Shop Gia Lap", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Duong Thu", "nguoi_nhan_ten": "Khach Gia Lap",
    "nguoi_nhan_sdt": "0902222222", "nguoi_nhan_dia_chi": "2 Duong Thu",
    "hang_hoa": "Hop Gia Lap", "khoi_luong_gram": 500, "cod": 100000,
}


def _don(ten_nhan):
    d = dict(DON_GOC)
    d["nguoi_nhan_ten"] = ten_nhan
    return d


def _dung_nen():
    global CONG
    if FIX.get("xong"):
        return FIX
    csdl.mo()
    quyen.seed()
    khoi_tao.seed_providers()
    # Bộ thử dựng nền bằng `schema_version` ghim đúng PHIEN_BAN_SCHEMA (cùng đường của
    # `thu_g01_g02.py`): KHÔNG gọi `migrate.chay()`, nên KHÔNG chạm chốt `KHO_DANG_CHAY`
    # của làn AGENT 01. Schema cơ sở đã có đủ cột bộ này cần.
    csdl.ghi("INSERT INTO schema_version (phien_ban, ap_dung_luc, ghi_chu) VALUES (?,?,'g22-a4')",
             (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
    csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
             " VALUES ('po',?,'Platform Owner','PLATFORM_OWNER',?)",
             (bao_mat.bam_mat_khau(MK), csdl.bay_gio()))

    sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    sv.daemon_threads = True
    CONG = sv.server_address[1]
    FIX["sv"] = sv
    threading.Thread(target=sv.serve_forever, daemon=True, name="g22-a4-http").start()

    po = phien("po")
    FIX["po"] = po
    for ten, code, dn, khoa in (("Cong ty A", "cta", "a-owner", "tid_a"),
                                ("Cong ty B", "ctb", "b-owner", "tid_b")):
        st, kq = po.goi("/api/v2/platform/tenants", "POST",
                        {"ten": ten, "code": code, "goi_id": "pro",
                         "owner_ten_dang_nhap": dn, "owner_mat_khau": MK})
        assert st == 201, "tạo tenant %s hỏng: %s %s" % (code, st, kq)
        FIX[khoa] = kq["id"]

    a, b = phien("a-owner"), phien("b-owner")
    FIX["a"], FIX["b"] = a, b
    for dn, role in (("a-staff", "TENANT_STAFF"), ("a-viewer", "TENANT_VIEWER"),
                     ("a-admin", "TENANT_ADMIN")):
        st, kq = a.goi("/api/v2/memberships", "POST",
                       {"ten_dang_nhap": dn, "mat_khau": MK, "ho_ten": dn, "role": role})
        assert st == 201, "tạo %s hỏng: %s %s" % (dn, st, kq)
    FIX["a_staff"], FIX["a_viewer"], FIX["a_admin"] = (
        phien("a-staff"), phien("a-viewer"), phien("a-admin"))

    # Khách + đơn của MỖI bên, mang dấu hiệu riêng để quét chéo.
    st, kq = a.goi("/api/v2/khach-hang", "POST", {"ten": "Khach cua A " + MAT_A})
    assert st == 201, kq
    FIX["kh_a"] = kq["id"]
    st, kq = b.goi("/api/v2/khach-hang", "POST", {"ten": "Khach cua B " + MAT_B})
    assert st == 201, kq
    FIX["kh_b"] = kq["id"]

    st, kq = a.goi("/api/v2/don", "POST", _don("Nguoi nhan A " + MAT_A))
    assert st == 201, kq
    FIX["don_a"] = kq["don"]["id"]
    st, kq = b.goi("/api/v2/don", "POST", _don("Nguoi nhan B " + MAT_B))
    assert st == 201, kq
    FIX["don_b"] = kq["don"]["id"]

    # Tài khoản hãng của mỗi bên — chứa credential GIẢ, mang dấu hiệu của chính bên đó.
    st, kq = a.goi("/api/v2/tai-khoan-hang", "POST",
                   {"hang": "vtp", "ten": "VTP cua A",
                    "credentials": {"api_key": "KHOA-GIA-" + MAT_A}})
    assert st == 201, kq
    FIX["tk_a"] = kq
    st, kq = b.goi("/api/v2/tai-khoan-hang", "POST",
                   {"hang": "jt", "ten": "JT cua B",
                    "credentials": {"privateKey": "KHOA-GIA-" + MAT_B}})
    assert st == 201, kq
    FIX["tk_b"] = kq

    FIX["xong"] = True
    return FIX


def setUpModule():
    _dung_nen()


def tearDownModule():
    GHI_MANG.tat()
    sv = FIX.get("sv")
    if sv is not None:
        sv.shutdown()
        sv.server_close()
    try:
        csdl.dong()
    except Exception:                                             # noqa: BLE001
        pass


# =================================================================================================
# 4. TIỆN ÍCH ĐO — quét dấu hiệu, bắt log, chạy tiến trình con
# =================================================================================================
def _thanh_chu(obj):
    if isinstance(obj, (dict, list)):
        return json.dumps(obj, ensure_ascii=False, default=str)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", "replace")
    return str(obj)


def _quet(obj, dau_hieu):
    """True nếu `dau_hieu` có mặt trong thân phản hồi (đã chuyển thành chuỗi)."""
    return dau_hieu in _thanh_chu(obj)


@contextlib.contextmanager
def _bat_log():
    """Bắt HAI kênh log đang có thật trong hệ: JSONL có cấu trúc (`quan_sat`) và access log
    (`sys.stderr`, do `server.log_message` ghi). Trả hai StringIO."""
    log, err = io.StringIO(), io.StringIO()
    cu_log, cu_err = quan_sat.dat_luong_log(log), sys.stderr
    sys.stderr = err
    try:
        yield log, err
    finally:
        quan_sat.dat_luong_log(cu_log)
        sys.stderr = cu_err


def _cho_log(luong, so_dong, het_gio=5.0):
    moc = time.time() + het_gio
    while time.time() < moc:
        if luong.getvalue().count("\n") >= so_dong:
            return True
        time.sleep(0.02)
    return False


def _bam_tep(duong):
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    return h.hexdigest()


def _van_tay_csdl(thu_muc):
    """Vân tay CSDL = băm từng tệp `hub.db*` còn tồn tại, nối theo thứ tự tên.

    Phải gồm cả `-wal`/`-shm`: ở chế độ WAL, `hub.db` một mình không chứa hết dữ liệu đã ghi, nên
    băm mỗi tệp chính sẽ báo "không đổi" trong khi WAL đã đổi — một đối chứng mù.
    """
    ra = {}
    for ten in sorted(os.listdir(thu_muc)):
        if ten == "hub.db" or ten.startswith("hub.db-"):
            ra[ten] = _bam_tep(os.path.join(thu_muc, ten))
    return ra


def _thu_muc_con(ten):
    d = os.path.join(TMP, "con", ten)
    os.makedirs(d, exist_ok=True)
    return d


def _chay_con(ma, thu_muc, env_them=None, timeout=180):
    """Chạy một kịch bản Python trong TIẾN TRÌNH CON. Trả (rc, stdout, stderr).

    Mọi biến `VIP_*` kế thừa bị xoá trước: một biến lọt vào từ shell sẽ làm nhánh "chưa khai"
    không bao giờ chạy, và kết quả phụ thuộc người gọi nhớ gỡ biến hay không.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("VIP_")}
    env["VIP_HUB_DATA"] = thu_muc
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_them or {})
    p = subprocess.run([sys.executable, "-c", ma], cwd=GOC_CAY, env=env,
                       capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


# --- kịch bản con: chốt KHO ĐANG CHẠY + sao lưu/khôi phục (KHÔNG sửa tệp làn AGENT 01) --------
MA_SAO_LUU = r'''
import sys
sys.path.insert(0, "app")
import csdl, migrate
csdl.mo(); csdl.dong()
p = migrate.sao_luu(luc="20261016-120000")
print("BAN_SAO=" + p)
'''

MA_SAO_LUU_KHONG_MO = r'''
import sys
sys.path.insert(0, "app")
import migrate
print("TRUOC_SAO_LUU")
p = migrate.sao_luu(luc="20261016-120000")
print("BAN_SAO=" + p)
'''

MA_KHOI_PHUC = r'''
import sys, os
sys.path.insert(0, "app")
import migrate
migrate.khoi_phuc(os.environ["TEP_BACKUP"], luc="20261016-120000")
print("KHONG_DUOC_TOI_DAY")
'''

MA_POPULATE = r'''
import sys
sys.path.insert(0, "app")
import csdl
csdl.mo()
csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES ('cta','A','pro',?)",
         (csdl.bay_gio(),))
csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, tao_luc) VALUES (1,'khach-restore',?)",
         (csdl.bay_gio(),))
print("DEM_KHACH=%d" % csdl.mot("SELECT COUNT(*) c FROM khach_hang")["c"])
csdl.dong()
'''

MA_XOA_KHACH = r'''
import sys
sys.path.insert(0, "app")
import csdl
csdl.mo()
csdl.ghi("DELETE FROM khach_hang WHERE ten='khach-restore'")
print("DEM_KHACH=%d" % csdl.mot("SELECT COUNT(*) c FROM khach_hang")["c"])
csdl.dong()
'''

MA_DEM_KHACH = r'''
import sys
sys.path.insert(0, "app")
import csdl
csdl.mo()
print("DEM_KHACH=%d" % csdl.mot("SELECT COUNT(*) c FROM khach_hang")["c"])
csdl.dong()
'''

MA_TAO_TEP_HONG = r'''
import sys, os
sys.path.insert(0, "app")
import csdl
csdl.mo(); csdl.dong()
with open(os.path.join(os.environ["VIP_HUB_DATA"], "hong.db"), "wb") as f:
    f.write(b"KHONG-PHAI-SQLITE" * 50)
print("DA_TAO_TEP_HONG")
'''


# =================================================================================================
# MẶT 1 — TENANT ISOLATION
# =================================================================================================
class A_TenantIsolation(unittest.TestCase):
    """A không đọc được dữ liệu của B. MỌI ca phủ định đều có đối chứng dương trong cùng ca."""

    def test_a1_doi_chung_duong_a_doc_duoc_du_lieu_cua_a(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/don/%d" % f["don_a"])
        self.assertEqual(st, 200, "A phải đọc được đơn của CHÍNH A")
        self.assertEqual(kq["don"]["id"], f["don_a"])
        self.assertIn(MAT_A, _thanh_chu(kq))
        self.assertNotIn(MAT_B, _thanh_chu(kq))
        _ghi("1-tenant-isolation", self._testMethodName,
             "A đọc đơn A → 200 · đúng id=%d · thân chứa dấu hiệu của A" % f["don_a"],
             "ĐỐI CHỨNG DƯƠNG cho a2: cùng hàm, cùng đường HTTP, khác tenant")

    def test_a2_a_khong_doc_duoc_don_cua_b(self):
        f = FIX
        # (i) Phép đo: A đọc đơn của B.
        st, kq = f["a"].goi("/api/v2/don/%d" % f["don_b"])
        self.assertEqual(st, 404, "A đọc được đơn của B — HỎNG ISOLATION")
        self.assertNotIn(MAT_B, _thanh_chu(kq),
                         "phản hồi 404 vẫn mang dữ liệu của B — rò rỉ chéo tenant")
        # (ii) Chứng minh phép đo KHÔNG mù: dòng của B CÓ THẬT trong CSDL, và hàm lõi trả
        #      dòng đó khi hỏi ĐÚNG tenant B. Nếu thiếu vế này, "404" có thể chỉ vì đơn
        #      không tồn tại — một kết luận đúng nhưng không đo điều mình tưởng.
        self.assertIsNotNone(_db1("SELECT id FROM don_hang WHERE id=?", (f["don_b"],)),
                             "đơn của B phải tồn tại trong CSDL")
        self.assertIsNotNone(don_hang.lay_don(f["tid_b"], f["don_b"]),
                             "lay_don(tenant B) phải thấy đơn của B")
        self.assertIsNone(don_hang.lay_don(f["tid_a"], f["don_b"]),
                          "lay_don(tenant A) TRẢ VỀ đơn của B — lỗi tầng lõi")
        TIEM_LOI["1-tenant-isolation"] = (
            "cùng câu SELECT bỏ điều kiện tenant thấy dòng của B; thêm tenant_id=A ⇒ None ⇒ "
            "404 đo được là do TÁCH TENANT, không phải do thiếu dữ liệu")
        _ghi("1-tenant-isolation", self._testMethodName,
             "A→đơn B = 404 · thân KHÔNG chứa dấu hiệu B · dòng của B CÓ THẬT trong CSDL",
             "a1 (A→A = 200 + dấu hiệu A) + lay_don(tenant B) ≠ None")

    def test_a3_doi_chung_am_b_khong_doc_duoc_du_lieu_cua_a(self):
        f = FIX
        st, kq = f["b"].goi("/api/v2/don/%d" % f["don_a"])
        self.assertEqual(st, 404, "B đọc được đơn của A — HỎNG ISOLATION")
        self.assertNotIn(MAT_A, _thanh_chu(kq), "phản hồi mang dữ liệu của A")
        st, kq = f["b"].goi("/api/v2/khach-hang/%d" % f["kh_a"])
        self.assertEqual(st, 404, "B đọc được khách hàng của A")
        self.assertNotIn(MAT_A, _thanh_chu(kq), "phản hồi mang dữ liệu khách của A")
        # Đối chứng dương: B đọc đơn của chính B.
        st, kq = f["b"].goi("/api/v2/don/%d" % f["don_b"])
        self.assertEqual(st, 200)
        self.assertIn(MAT_B, _thanh_chu(kq))
        _ghi("1-tenant-isolation", self._testMethodName,
             "B→đơn A = 404 · B→khách A = 404 · hai thân đều KHÔNG chứa dấu hiệu A",
             "B→đơn B = 200 + dấu hiệu B (cùng phiên B, cùng đường)")

    def test_a4_danh_sach_tim_kiem_va_xuat_csv_khong_lot_du_lieu_cheo(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/don")
        self.assertEqual(st, 200)
        ids = [d["id"] for d in kq["don"]]
        self.assertIn(f["don_a"], ids)
        self.assertNotIn(f["don_b"], ids, "danh sách đơn của A chứa đơn của B")
        self.assertNotIn(MAT_B, _thanh_chu(kq))

        st, kq = f["a"].goi("/api/v2/don/tim", "POST", {"q": MAT_B})
        self.assertEqual(st, 200)
        self.assertEqual(kq["tong"], 0, "tìm bằng dấu hiệu của B trả về đơn — rò rỉ chéo tenant")
        st, kq = f["a"].goi("/api/v2/don/tim", "POST", {"q": MAT_A})
        self.assertEqual(st, 200)
        self.assertGreaterEqual(kq["tong"], 1, "tìm bằng dấu hiệu của A không thấy gì")

        st, csv = f["a"].goi("/api/v2/don/xuat-csv")
        self.assertEqual(st, 200)
        self.assertIn(MAT_A, csv, "CSV của A không chứa dữ liệu của A")
        self.assertNotIn(MAT_B, csv, "CSV của A chứa dữ liệu của B — rò rỉ qua đường xuất")
        _ghi("1-tenant-isolation", self._testMethodName,
             "danh sách A: 0 đơn của B · tìm q=B: tong=0 · CSV A: KHÔNG có dấu hiệu B",
             "danh sách chứa đơn A · tìm q=A: tong≥1 · CSV A CÓ dấu hiệu A")

    def test_a5_tai_khoan_hang_cheo_tenant_bi_chan(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/tai-khoan-hang/%d/rotate" % f["tk_b"]["id"],
                            "POST", {"credentials": {"privateKey": "GHI-DE"}})
        self.assertEqual(st, 404, "A xoay được khoá của tài khoản hãng thuộc B")
        self.assertNotIn(MAT_B, _thanh_chu(kq))
        # Đối chứng dương: A xoay tài khoản của CHÍNH A.
        st, _ = f["a"].goi("/api/v2/tai-khoan-hang/%d/rotate" % f["tk_a"]["id"],
                           "POST", {"credentials": {"api_key": "KHOA-GIA-" + MAT_A}})
        self.assertEqual(st, 200, "A không xoay được tài khoản của chính A")
        # Đường DANH SÁCH của A không được trả tài khoản của B.
        st, kq = f["a"].goi("/api/v2/tai-khoan-hang")
        self.assertEqual(st, 200)
        ids = [x["id"] for x in kq["tai_khoan"]]
        self.assertIn(f["tk_a"]["id"], ids)
        self.assertNotIn(f["tk_b"]["id"], ids)
        _ghi("1-tenant-isolation", self._testMethodName,
             "A→rotate tài khoản B = 404 · danh sách tài khoản A KHÔNG có tài khoản B",
             "A→rotate tài khoản A = 200 · danh sách A CÓ tài khoản A")

    def test_a6_doi_tenant_khong_co_membership_bi_chan(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": f["tid_b"]})
        self.assertEqual(st, 403, "A đổi được sang tenant B dù không có membership")
        self.assertNotIn(MAT_B, _thanh_chu(kq))
        st, kq = f["a"].goi("/api/v2/auth/toi")
        self.assertEqual(st, 200)
        self.assertEqual(kq["tenant"]["id"], f["tid_a"], "ngữ cảnh tenant bị đổi dù bị từ chối")
        # Đối chứng dương: đổi sang tenant MÌNH CÓ membership.
        st, kq = f["a"].goi("/api/v2/auth/doi-tenant", "POST", {"tenant_id": f["tid_a"]})
        self.assertEqual(st, 200, "đổi sang tenant của chính mình phải được")
        self.assertEqual(kq["tenant_id"], f["tid_a"])
        _ghi("1-tenant-isolation", self._testMethodName,
             "A→doi-tenant(B) = 403 · ngữ cảnh vẫn là tenant A",
             "A→doi-tenant(A) = 200 · ngữ cảnh đổi đúng sang A")


# =================================================================================================
# MẶT 2 — RBAC
# =================================================================================================
class B_RBAC(unittest.TestCase):
    """Vai không đủ quyền bị chặn ĐÚNG MÃ; vai đủ quyền đi qua được; quyền tra từ CSDL."""

    def test_b1_viewer_tao_don_bi_chan_403_va_khong_tao_dong_nao(self):
        f = FIX
        truoc = _dem("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (f["tid_a"],))
        st, kq = f["a_viewer"].goi("/api/v2/don", "POST", _don("Viewer thu tao"))
        self.assertEqual(st, 403, "TENANT_VIEWER tạo được đơn — HỎNG RBAC")
        self.assertEqual(kq.get("loi"), "không đủ quyền")
        sau = _dem("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (f["tid_a"],))
        self.assertEqual(sau, truoc, "yêu cầu bị 403 vẫn ghi thêm đơn")
        # Đối chứng dương: CÙNG payload, CÙNG đường, vai đủ quyền.
        st, kq = f["a_staff"].goi("/api/v2/don", "POST", _don("Staff thu tao"))
        self.assertEqual(st, 201, "TENANT_STAFF không tạo được đơn — chặn NHẦM vai")
        self.assertEqual(_dem("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (f["tid_a"],)),
                         truoc + 1)
        _ghi("2-rbac", self._testMethodName,
             "viewer→POST /don = 403 'không đủ quyền' · số đơn KHÔNG tăng (%d)" % truoc,
             "staff→POST /don = 201 · số đơn +1 (cùng payload)")

    def test_b2_viewer_xoa_don_bi_chan_va_admin_xoa_duoc(self):
        f = FIX
        st, kq = f["a_staff"].goi("/api/v2/don", "POST", _don("Don de xoa 1"))
        self.assertEqual(st, 201)
        don_1 = kq["don"]["id"]
        st, kq = f["a_staff"].goi("/api/v2/don", "POST", _don("Don de xoa 2"))
        self.assertEqual(st, 201)
        don_2 = kq["don"]["id"]
        st, kq = f["a_viewer"].goi("/api/v2/don/%d" % don_1, "DELETE")
        self.assertEqual(st, 403, "viewer xoá được đơn — HỎNG RBAC")
        self.assertEqual(_db1("SELECT trang_thai FROM don_hang WHERE id=?", (don_1,))["trang_thai"],
                         "nhap", "đơn bị đổi trạng thái dù lượt xoá bị 403")
        st, _ = f["a_admin"].goi("/api/v2/don/%d" % don_2, "DELETE")
        self.assertEqual(st, 200, "TENANT_ADMIN không xoá được đơn — chặn NHẦM vai")
        self.assertEqual(_db1("SELECT trang_thai FROM don_hang WHERE id=?", (don_2,))["trang_thai"],
                         "huy")
        _ghi("2-rbac", self._testMethodName,
             "viewer→DELETE /don = 403 · đơn GIỮ 'nhap'",
             "admin→DELETE /don = 200 · đơn thành 'huy'")

    def test_b3_staff_khong_quan_ly_thanh_vien_owner_thi_duoc(self):
        f = FIX
        st, kq = f["a_staff"].goi("/api/v2/memberships", "POST",
                                  {"ten_dang_nhap": "a-extra-1", "mat_khau": MK,
                                   "ho_ten": "extra", "role": "TENANT_STAFF"})
        self.assertEqual(st, 403, "TENANT_STAFF mời được thành viên — HỎNG RBAC")
        self.assertIsNone(_db1("SELECT id FROM users WHERE ten_dang_nhap='a-extra-1'"))
        st, kq = f["a"].goi("/api/v2/memberships", "POST",
                            {"ten_dang_nhap": "a-extra-1", "mat_khau": MK,
                             "ho_ten": "extra", "role": "TENANT_STAFF"})
        self.assertEqual(st, 201, "TENANT_OWNER không mời được thành viên — chặn NHẦM vai")
        self.assertIsNotNone(_db1("SELECT id FROM users WHERE ten_dang_nhap='a-extra-1'"))
        _ghi("2-rbac", self._testMethodName,
             "staff→POST /memberships = 403 · KHÔNG tạo user",
             "owner→POST /memberships = 201 · user được tạo")

    def test_b4_quyen_tra_tu_csdl_khong_hardcode(self):
        f = FIX
        # Gỡ đúng MỘT dòng quyền khỏi vai đang có quyền. Nếu RBAC hard-code trong mã, lượt
        # gọi dưới đây vẫn 201 và ca này ĐỎ — đó chính là phép tiêm.
        csdl.ghi("DELETE FROM role_permissions WHERE role_ma='TENANT_STAFF'"
                 " AND perm_ma='tenant.don.ghi'")
        try:
            st, kq = f["a_staff"].goi("/api/v2/don", "POST", _don("Staff sau khi go quyen"))
            self.assertEqual(st, 403, "gỡ quyền trong CSDL mà staff VẪN tạo được đơn ⇒ RBAC"
                                      " không tra CSDL")
            # Đối chứng dương: trả dòng quyền lại ⇒ CÙNG phiên, CÙNG đường, đi qua được.
            csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma)"
                     " VALUES ('TENANT_STAFF','tenant.don.ghi')")
            st, kq = f["a_staff"].goi("/api/v2/don", "POST", _don("Staff sau khi tra quyen"))
            self.assertEqual(st, 201, "trả quyền lại mà staff vẫn bị chặn")
        finally:
            csdl.ghi("INSERT OR IGNORE INTO role_permissions (role_ma, perm_ma)"
                     " VALUES ('TENANT_STAFF','tenant.don.ghi')")
        self.assertIsNotNone(_db1("SELECT 1 x FROM role_permissions WHERE role_ma='TENANT_STAFF'"
                                  " AND perm_ma='tenant.don.ghi'"))
        TIEM_LOI["2-rbac"] = ("xoá dòng role_permissions ⇒ cùng vai bị 403; chèn lại ⇒ 201 "
                              "⇒ quyết định đọc từ CSDL, không hard-code")
        _ghi("2-rbac", self._testMethodName,
             "gỡ 'tenant.don.ghi' của TENANT_STAFF trong CSDL ⇒ staff→POST /don = 403",
             "chèn lại dòng quyền ⇒ CÙNG phiên staff→POST /don = 201")


# =================================================================================================
# MẶT 3 — FAIL-CLOSED (thiếu cấu hình / khôi phục tệp hỏng ⇒ TỪ CHỐI, không im lặng)
# =================================================================================================
class C_FailClosed(unittest.TestCase):
    """Mọi phép đo là TIẾN TRÌNH CON: mã thoát THẬT + thông điệp THẬT + vân tay CSDL trên đĩa.

    Phạm vi: KHÔNG sửa `app/cau_hinh.py`/`app/migrate.py` (làn AGENT 01 sở hữu). Chỉ GỌI chúng.
    """

    def test_c1_sao_luu_tu_choi_khi_chua_khai_kho(self):
        tm = _thu_muc_con("fc1")
        rc, out, err = _chay_con(MA_SAO_LUU, tm)
        self.assertNotEqual(rc, 0, "CHƯA KHAI kho mà sao_luu() vẫn thoát 0 — FAIL-OPEN")
        self.assertIn("TỪ CHỐI", err)
        self.assertIn("CHƯA KHAI", err)
        self.assertNotIn("BAN_SAO=", out)
        # Đối chứng dương: khai `sqlite` ⇒ CÙNG kịch bản, CÙNG thư mục ⇒ chạy được.
        rc2, out2, err2 = _chay_con(MA_SAO_LUU, tm, {"VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertEqual(rc2, 0, "khai 'sqlite' mà vẫn từ chối: %s" % err2[-500:])
        m = re.search(r"BAN_SAO=(.+)", out2)
        self.assertIsNotNone(m, "không đọc được đường dẫn bản sao: %s" % out2)
        duong = m.group(1).strip()
        self.assertTrue(os.path.isfile(duong), "bản sao không tồn tại: %s" % duong)
        self.assertTrue(os.path.isfile(duong + ".sha256"), "thiếu dấu kiểm .sha256")
        TIEM_LOI["3-fail-closed"] = (
            "cùng kịch bản: thiếu khai ⇒ rc=%d + 'CHƯA KHAI'; khai sqlite ⇒ rc=0 + tệp thật"
            % rc)
        _ghi("3-fail-closed", self._testMethodName,
             "KHÔNG khai kho: rc=%d · stderr 'TỪ CHỐI … CHƯA KHAI' · KHÔNG có tệp bản sao" % rc,
             "khai sqlite: rc=%d · bản sao + .sha256 tồn tại trên đĩa" % rc2)

    def test_c2_khoi_phuc_ban_sao_hong_bi_tu_choi_va_csdl_khong_doi(self):
        tm = _thu_muc_con("fc2")
        rc, out, err = _chay_con(MA_TAO_TEP_HONG, tm)
        self.assertEqual(rc, 0, err)
        truoc = _van_tay_csdl(tm)
        self.assertIn("hub.db", truoc)
        env = {"TEP_BACKUP": os.path.join(tm, "hong.db"), "VIP_KHO_DANG_CHAY": "sqlite"}
        rc, out, err = _chay_con(MA_KHOI_PHUC, tm, env)
        self.assertNotEqual(rc, 0, "khôi phục từ tệp KHÔNG phải SQLite mà vẫn thoát 0")
        self.assertIn("TỪ CHỐI", err)
        self.assertIn("KHÔNG PHẢI CSDL SQLite", err)
        self.assertNotIn("KHONG_DUOC_TOI_DAY", out)
        self.assertEqual(_van_tay_csdl(tm), truoc, "CSDL đang chạy BỊ ĐỔI sau lượt từ chối")
        _ghi("3-fail-closed", self._testMethodName,
             "khôi phục từ tệp rác: rc=%d · 'KHÔNG PHẢI CSDL SQLite' · vân tay CSDL KHÔNG đổi"
             % rc,
             "c4 chứng minh bản sao TỐT vẫn khôi phục được (từ chối không phải 'luôn từ chối')")

    def test_c3_khoi_phuc_tu_choi_khi_dau_kiem_sai(self):
        tm = _thu_muc_con("fc3")
        rc, out, _ = _chay_con(MA_SAO_LUU, tm, {"VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertEqual(rc, 0)
        duong = re.search(r"BAN_SAO=(.+)", out).group(1).strip()
        # Làm sai DẤU KIỂM (không làm hỏng tệp): cấu trúc vẫn qua, nên lượt từ chối CHỈ có thể
        # đến từ chốt dấu kiểm — nếu không, ta không biết chốt nào đã cứu.
        with open(duong + ".sha256", "w", encoding="utf-8") as f:
            f.write("%s  %s\n" % ("0" * 64, os.path.basename(duong)))
        truoc = _van_tay_csdl(tm)
        env = {"TEP_BACKUP": duong, "VIP_KHO_DANG_CHAY": "sqlite"}
        rc, out, err = _chay_con(MA_KHOI_PHUC, tm, env)
        self.assertNotEqual(rc, 0, "dấu kiểm sai mà vẫn khôi phục — FAIL-OPEN")
        self.assertIn("KHÁC dấu kiểm", err)
        self.assertNotIn("KHONG_DUOC_TOI_DAY", out)
        self.assertEqual(_van_tay_csdl(tm), truoc, "CSDL bị đổi sau lượt từ chối vì dấu kiểm")
        _ghi("3-fail-closed", self._testMethodName,
             "dấu kiểm .sha256 sai: rc=%d · 'KHÁC dấu kiểm' · vân tay CSDL KHÔNG đổi" % rc,
             "c4: dấu kiểm ĐÚNG ⇒ khôi phục thành công")

    def test_c4_doi_chung_duong_khoi_phuc_ban_sao_tot(self):
        tm = _thu_muc_con("fc4")
        rc, out, err = _chay_con(MA_POPULATE, tm)
        self.assertEqual(rc, 0, err)
        self.assertIn("DEM_KHACH=1", out)
        rc, out, _ = _chay_con(MA_SAO_LUU, tm, {"VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertEqual(rc, 0)
        duong = re.search(r"BAN_SAO=(.+)", out).group(1).strip()
        rc, out, err = _chay_con(MA_XOA_KHACH, tm)
        self.assertEqual(rc, 0, err)
        self.assertIn("DEM_KHACH=0", out, "không xoá được dòng để dựng phép đo")
        rc, out, err = _chay_con(MA_KHOI_PHUC, tm,
                                 {"TEP_BACKUP": duong, "VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertEqual(rc, 0, "khôi phục bản sao TỐT bị từ chối: %s" % err[-800:])
        rc, out, err = _chay_con(MA_DEM_KHACH, tm)
        self.assertEqual(rc, 0, err)
        self.assertIn("DEM_KHACH=1", out, "khôi phục báo thành công nhưng dữ liệu KHÔNG về")
        _ghi("3-fail-closed", self._testMethodName,
             "bản sao TỐT: khôi phục rc=0 · dữ liệu về đúng (0 → 1 dòng 'khach-restore')",
             "ĐỐI CHỨNG DƯƠNG cho c2/c3: chốt từ chối KHÔNG phải 'luôn từ chối'")

    def test_c5_sao_luu_tu_choi_khi_khong_co_hub_db(self):
        tm = _thu_muc_con("fc5")
        self.assertFalse(os.path.exists(os.path.join(tm, "hub.db")))
        # Kịch bản KHÔNG gọi `csdl.mo()`: nếu gọi, chính nó tạo ra một `hub.db` RỖNG và phép đo
        # biến thành "sao lưu một CSDL rỗng" — đúng đường lùi giả mà chốt này sinh ra để chặn.
        rc, out, err = _chay_con(MA_SAO_LUU_KHONG_MO, tm, {"VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertNotEqual(rc, 0, "không có hub.db mà sao_luu() vẫn thoát 0 — đường lùi giả")
        self.assertIn("không thấy CSDL", err)
        self.assertNotIn("BAN_SAO=", out)
        self.assertFalse(os.path.exists(os.path.join(tm, "hub.db")),
                         "bị từ chối nhưng vẫn TẠO RA hub.db rỗng")
        # Đối chứng dương: CÙNG kịch bản, sau khi có hub.db thật.
        rc2, out2, err2 = _chay_con(MA_SAO_LUU, tm, {"VIP_KHO_DANG_CHAY": "sqlite"})
        self.assertEqual(rc2, 0, "có hub.db mà vẫn từ chối: %s" % err2[-500:])
        self.assertIn("BAN_SAO=", out2)
        _ghi("3-fail-closed", self._testMethodName,
             "không có hub.db: rc=%d · 'không thấy CSDL' · KHÔNG tạo CSDL rỗng" % rc,
             "dựng hub.db ⇒ cùng kịch bản rc=%d + tệp bản sao" % rc2)


# =================================================================================================
# MẶT 4 — IDEMPOTENCY
# =================================================================================================
class D_Idempotency(unittest.TestCase):
    """Cùng một yêu cầu gửi hai lần ⇒ KHÔNG nhân đôi. Chứng minh BẰNG SỐ, có đối chứng âm."""

    def _dem_don(self):
        return _dem("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (FIX["tid_a"],))

    def test_d1_cung_idempotency_key_hai_lan_chi_mot_don(self):
        f = FIX
        khoa = "idem-a4-1"
        truoc = self._dem_don()
        st1, kq1 = f["a"].goi("/api/v2/don", "POST", _don("Idem lan 1"),
                              headers={"Idempotency-Key": khoa})
        st2, kq2 = f["a"].goi("/api/v2/don", "POST", _don("Idem lan 1"),
                              headers={"Idempotency-Key": khoa})
        self.assertEqual((st1, st2), (201, 200),
                         "kỳ vọng lượt đầu 201 (mới) và lượt hai 200 (trùng): %s %s" % (st1, st2))
        self.assertFalse(kq1["idempotent_trung"])
        self.assertTrue(kq2["idempotent_trung"], "lượt hai KHÔNG báo trùng")
        self.assertEqual(kq1["don"]["id"], kq2["don"]["id"], "hai lượt tạo HAI đơn khác nhau")
        self.assertEqual(self._dem_don(), truoc + 1,
                         "số đơn tăng %d sau hai lượt cùng khoá" % (self._dem_don() - truoc))
        self.assertEqual(_dem("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=? AND idem_key=?",
                              (f["tid_a"], khoa)), 1)
        _ghi("4-idempotency", self._testMethodName,
             "cùng Idempotency-Key ×2 ⇒ (201,200) · CÙNG id=%d · số đơn +1 · 1 dòng idem_key"
             % kq1["don"]["id"],
             "d2: khoá KHÁC ×2 ⇒ số đơn +2 — phép đếm NHÌN THẤY được nhân đôi")

    def test_d2_doi_chung_am_khoa_khac_thi_co_hai_don(self):
        f = FIX
        truoc = self._dem_don()
        st1, kq1 = f["a"].goi("/api/v2/don", "POST", _don("Khac khoa 1"),
                              headers={"Idempotency-Key": "idem-a4-2a"})
        st2, kq2 = f["a"].goi("/api/v2/don", "POST", _don("Khac khoa 2"),
                              headers={"Idempotency-Key": "idem-a4-2b"})
        self.assertEqual((st1, st2), (201, 201), "hai khoá khác nhau mà lượt hai báo trùng")
        self.assertNotEqual(kq1["don"]["id"], kq2["don"]["id"])
        self.assertEqual(self._dem_don(), truoc + 2, "hai khoá khác nhau phải tạo hai đơn")
        TIEM_LOI["4-idempotency"] = (
            "khoá KHÁC nhau ⇒ 201+201 và số đơn +2 — CÙNG phép đếm của d1, nên nếu d1 báo '+1' "
            "thì đó là chặn trùng thật, không phải phép đếm không thấy đơn thứ hai")
        _ghi("4-idempotency", self._testMethodName,
             "hai khoá KHÁC nhau ⇒ 201+201 · hai id khác nhau · số đơn +2",
             "ĐỐI CHỨNG ÂM: chứng minh phép đếm của d1 KHÔNG mù với sự nhân đôi")

    def test_d3_hai_luot_song_song_cung_khoa_chi_mot_don(self):
        f = FIX
        khoa = "idem-a4-song-song"
        truoc = self._dem_don()
        ket = []
        rao = threading.Barrier(2)

        def gui():
            rao.wait(timeout=10)
            st, kq = f["a"].goi("/api/v2/don", "POST", _don("Idem song song"),
                                headers={"Idempotency-Key": khoa})
            ket.append((st, (kq.get("don") or {}).get("id"), kq.get("idempotent_trung")))

        ds = [threading.Thread(target=gui) for _ in range(2)]
        for t in ds:
            t.start()
        for t in ds:
            t.join(timeout=30)
        self.assertEqual(len(ket), 2, "một luồng không trả kết quả: %s" % ket)
        ids = {x[1] for x in ket}
        self.assertEqual(len(ids), 1, "hai luồng tạo HAI đơn cho cùng khoá: %s" % ket)
        self.assertEqual(self._dem_don(), truoc + 1,
                         "số đơn tăng %d cho hai lượt song song cùng khoá"
                         % (self._dem_don() - truoc))
        _ghi("4-idempotency", self._testMethodName,
             "2 luồng song song, cùng khoá ⇒ 1 id duy nhất · số đơn +1 (kết quả: %s)" % (ket,),
             "d2: hai khoá khác nhau ⇒ +2 — cùng phép đếm, khác điều kiện")

    def test_d4_rang_buoc_unique_o_tang_csdl_chan_dong_thu_hai(self):
        f = FIX
        khoa = "idem-a4-unique"
        st, kq = f["a"].goi("/api/v2/don", "POST", _don("Unique 1"),
                            headers={"Idempotency-Key": khoa})
        self.assertEqual(st, 201)
        with self.assertRaises(csdl.LoiToanVen,
                               msg="CSDL không có UNIQUE(tenant_id, idem_key) — khoá chỉ ở tầng mã"):
            csdl.ghi("INSERT INTO don_hang (tenant_id, ma_don, idem_key, nguoi_gui_ten,"
                     " nguoi_gui_sdt, nguoi_gui_dia_chi, nguoi_nhan_ten, nguoi_nhan_sdt,"
                     " nguoi_nhan_dia_chi, hang_hoa, khoi_luong_gram, nguoi_tao, tao_luc,"
                     " cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (f["tid_a"], "T%d-999999" % f["tid_a"], khoa, "x", "0901", "x", "y",
                      "0902", "y", "z", 1, 1, csdl.bay_gio(), csdl.bay_gio()))
        _ghi("4-idempotency", self._testMethodName,
             "INSERT thẳng dòng thứ hai cùng (tenant_id, idem_key) ⇒ IntegrityError",
             "d1: đường HTTP cho cùng kết quả bằng trả đơn cũ (201/200) — hai tầng cùng chặn")


# =================================================================================================
# MẶT 5 — WEBHOOK SECURITY
# =================================================================================================
class E_WebhookSecurity(unittest.TestCase):
    """Chữ ký HMAC: sai bị 401 và KHÔNG tạo sự kiện; đúng đi qua (202) và TẠO sự kiện."""

    def _body(self, khoa):
        return json.dumps({"event": "dang_giao", "tracking_number": "VTP-A4-%s" % khoa,
                           "sequence": 1}).encode("utf-8")

    def _ky(self, secret, body):
        return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    def _dem_su_kien(self, tk_id):
        return _dem("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?", (tk_id,))

    def test_e1_chu_ky_dung_di_qua_va_tao_su_kien(self):
        f = FIX
        tk = f["tk_a"]
        body = self._body("dung")
        truoc = self._dem_su_kien(tk["id"])
        st, kq = Phien().goi("/api/v2/webhook/nhan/" + tk["webhook_ma"], "POST", tho=body,
                             headers={"X-Webhook-Signature":
                                      self._ky(tk["webhook_secret_mot_lan"], body)})
        self.assertEqual(st, 202, "chữ ký ĐÚNG bị từ chối: %s %s" % (st, kq))
        self.assertEqual(kq.get("code"), 1)
        self.assertEqual(self._dem_su_kien(tk["id"]), truoc + 1, "sự kiện không được lưu")
        # Phát lại y nguyên: chữ ký vẫn đúng, nhưng sự kiện đã có ⇒ 200 "đã nhận trước đó",
        # KHÔNG tạo dòng thứ hai.
        st2, kq2 = Phien().goi("/api/v2/webhook/nhan/" + tk["webhook_ma"], "POST", tho=body,
                               headers={"X-Webhook-Signature":
                                        self._ky(tk["webhook_secret_mot_lan"], body)})
        self.assertEqual(st2, 200)
        self.assertEqual(kq2.get("ket_qua"), "da_nhan_truoc_do")
        self.assertEqual(self._dem_su_kien(tk["id"]), truoc + 1, "phát lại tạo sự kiện thứ hai")
        _ghi("5-webhook-security", self._testMethodName,
             "chữ ký ĐÚNG ⇒ 202 + 1 sự kiện · phát lại ⇒ 200 'da_nhan_truoc_do', số sự kiện +0",
             "ĐỐI CHỨNG DƯƠNG cho e2/e3/e4 (chữ ký đúng của CHÍNH account đi qua)")

    def test_e2_chu_ky_sai_bi_tu_choi_401_va_khong_tao_su_kien(self):
        f = FIX
        tk = f["tk_a"]
        body = self._body("sai")
        truoc = self._dem_su_kien(tk["id"])
        truoc_audit = _dem("SELECT COUNT(*) c FROM audit WHERE hanh_dong='webhook_chu_ky_tu_choi'")
        st, kq = Phien().goi("/api/v2/webhook/nhan/" + tk["webhook_ma"], "POST", tho=body,
                             headers={"X-Webhook-Signature": self._ky("secret-khong-dung", body)})
        self.assertEqual(st, 401, "chữ ký SAI được chấp nhận: %s %s" % (st, kq))
        self.assertEqual(self._dem_su_kien(tk["id"]), truoc, "chữ ký sai vẫn tạo sự kiện")
        self.assertGreater(_dem("SELECT COUNT(*) c FROM audit"
                                " WHERE hanh_dong='webhook_chu_ky_tu_choi'"),
                           truoc_audit, "lượt từ chối không để lại dấu vết audit")
        TIEM_LOI["5-webhook-security"] = (
            "cùng thân/cùng URL: secret SAI ⇒ 401 + 0 sự kiện; secret ĐÚNG ⇒ 202 + 1 sự kiện "
            "⇒ phép đo phân biệt được chữ ký, không phải 'luôn từ chối'")
        _ghi("5-webhook-security", self._testMethodName,
             "chữ ký SAI (secret khác) ⇒ 401 · 0 sự kiện · audit 'webhook_chu_ky_tu_choi' +1",
             "e1: cùng thân, cùng URL, secret ĐÚNG ⇒ 202 + sự kiện")

    def test_e3_thieu_chu_ky_bi_tu_choi_401(self):
        f = FIX
        tk = f["tk_a"]
        body = self._body("thieu")
        truoc = self._dem_su_kien(tk["id"])
        st, kq = Phien().goi("/api/v2/webhook/nhan/" + tk["webhook_ma"], "POST", tho=body)
        self.assertEqual(st, 401, "thiếu header chữ ký mà vẫn được nhận: %s %s" % (st, kq))
        self.assertEqual(self._dem_su_kien(tk["id"]), truoc, "lượt thiếu chữ ký vẫn tạo sự kiện")
        _ghi("5-webhook-security", self._testMethodName,
             "thiếu header x-webhook-signature ⇒ 401 · 0 sự kiện",
             "e1: CÙNG thân/URL có chữ ký ⇒ 202")

    def test_e4_chu_ky_cua_tenant_khac_khong_dung_duoc(self):
        f = FIX
        tk_a, tk_b = f["tk_a"], f["tk_b"]
        body = self._body("cheo-tenant")
        truoc = self._dem_su_kien(tk_a["id"])
        # Ký bằng secret của B nhưng gửi vào URL của A: đây là "mượn danh" — phải bị từ chối.
        st, kq = Phien().goi("/api/v2/webhook/nhan/" + tk_a["webhook_ma"], "POST", tho=body,
                             headers={"X-Webhook-Signature":
                                      self._ky(tk_b["webhook_secret_mot_lan"], body)})
        self.assertEqual(st, 401, "chữ ký của tenant B mở được webhook của tenant A")
        self.assertEqual(self._dem_su_kien(tk_a["id"]), truoc)
        # Đối chứng dương: CÙNG thân, ký bằng secret của A ⇒ đi qua.
        st, kq = Phien().goi("/api/v2/webhook/nhan/" + tk_a["webhook_ma"], "POST", tho=body,
                             headers={"X-Webhook-Signature":
                                      self._ky(tk_a["webhook_secret_mot_lan"], body)})
        self.assertEqual(st, 202, kq)
        self.assertEqual(self._dem_su_kien(tk_a["id"]), truoc + 1)
        _ghi("5-webhook-security", self._testMethodName,
             "secret của B ký, gửi vào URL webhook của A ⇒ 401 · 0 sự kiện",
             "CÙNG thân, secret của A ⇒ 202 + 1 sự kiện")


# =================================================================================================
# MẶT 6 — KHÔNG RÒ RỈ DỮ LIỆU CHÉO TENANT (thân phản hồi · log · tệp bằng chứng trên đĩa)
# =================================================================================================
class F_CrossTenantLeak(unittest.TestCase):
    """Quét dấu hiệu của B trên BA đường RA: thân phản hồi, hai kênh log, và tệp trên đĩa.

    Mỗi đường đều có đối chứng dương: dấu hiệu CÓ MẶT thì bộ quét PHẢI thấy (nếu không,
    "không thấy" chỉ là bộ quét mù).
    """

    def test_f1_than_phan_hoi_cua_a_khong_mang_du_lieu_b(self):
        f = FIX
        # (phương thức, đường, thân, MÃ MONG ĐỢI CHÍNH XÁC) — không dùng "mã nào cũng được":
        # một endpoint trả 500 cũng "không chứa dấu hiệu B", nhưng nó chứng minh điều ngược lại
        # với điều ta tuyên bố.
        duong = [
            ("GET", "/api/v2/don", None, 200),
            ("GET", "/api/v2/don/%d" % f["don_a"], None, 200),
            ("GET", "/api/v2/don/%d" % f["don_b"], None, 404),
            ("GET", "/api/v2/don/xuat-csv", None, 200),
            ("GET", "/api/v2/khach-hang/%d" % f["kh_b"], None, 404),
            ("GET", "/api/v2/tai-khoan-hang", None, 200),
            ("GET", "/api/v2/audit", None, 200),
            ("GET", "/api/v2/webhook/su-kien", None, 200),
            ("GET", "/api/v2/billing", None, 200),
            ("GET", "/api/v2/auth/toi", None, 200),
            ("POST", "/api/v2/don/tim", {"q": MAT_B}, 200),
        ]
        thay_b = []
        thay_a = 0
        for method, d, than, ma_mong_doi in duong:
            st, kq = f["a"].goi(d, method, than)
            self.assertEqual(st, ma_mong_doi, "mã %s ở %s (mong đợi %s)" % (st, d, ma_mong_doi))
            chu = _thanh_chu(kq)
            if MAT_B in chu:
                thay_b.append((method, d, st))
            if MAT_A in chu:
                thay_a += 1
        self.assertEqual(thay_b, [], "thân phản hồi của A mang dấu hiệu của B: %s" % thay_b)
        self.assertGreaterEqual(thay_a, 2, "không phản hồi nào của A chứa dữ liệu của A — "
                                           "bộ quét không có gì để so")
        # Đối chứng dương trên ĐƯỜNG THẬT: phiên B đọc dữ liệu B phải thấy dấu hiệu B.
        st, kq = f["b"].goi("/api/v2/don")
        self.assertEqual(st, 200)
        self.assertIn(MAT_B, _thanh_chu(kq), "B đọc đơn của B mà KHÔNG thấy dấu hiệu B — "
                                             "bộ quét/dữ liệu nền sai, không phải 'không rò'")
        _ghi("6-khong-ro-ri-cheo-tenant", self._testMethodName,
             "11 đường của A: 0 phản hồi chứa dấu hiệu B (thấy dấu hiệu A ở %d phản hồi)"
             % thay_a,
             "phiên B đọc dữ liệu B ⇒ THẤY dấu hiệu B (bộ quét không mù)")

    def test_f2_log_tren_dia_khong_mang_du_lieu_b_va_query_bi_cat(self):
        f = FIX
        with _bat_log() as (log, err):
            # Query mang dấu hiệu B — đường dễ rò nhất vào access log. Phải bị CẮT.
            f["a"].goi("/api/v2/don?q=" + MAT_B)
            # Đường dẫn mang dấu hiệu A — đối chứng dương: dấu hiệu phải XUẤT HIỆN trong log.
            f["a"].goi("/api/v2/khong-co-duong-nay/" + MAT_A)
            _cho_log(log, 2)
            _cho_log(err, 2)
            chu_log, chu_err = log.getvalue(), err.getvalue()
        self.assertIn(MAT_A, chu_log, "log JSONL không chứa dấu hiệu A trong ĐƯỜNG DẪN "
                                      "⇒ bộ quét không chứng minh được gì")
        self.assertIn(MAT_A, chu_err, "access log không chứa dấu hiệu A trong ĐƯỜNG DẪN")
        self.assertNotIn(MAT_B, chu_log, "log JSONL chứa dấu hiệu B (query không bị cắt)")
        self.assertNotIn(MAT_B, chu_err, "access log chứa dấu hiệu B (query không bị cắt)")
        # Ghi ra ĐĨA rồi đọc lại: phép đo phải chạy trên TỆP, không chỉ trên bộ nhớ.
        tep_log = os.path.join(TMP, "log_jsonl_tren_dia.jsonl")
        tep_err = os.path.join(TMP, "log_access_tren_dia.txt")
        with open(tep_log, "w", encoding="utf-8") as fh:
            fh.write(chu_log)
        with open(tep_err, "w", encoding="utf-8") as fh:
            fh.write(chu_err)
        for tep in (tep_log, tep_err):
            with open(tep, encoding="utf-8", errors="replace") as fh:
                tren_dia = fh.read()
            self.assertNotIn(MAT_B, tren_dia, "TỆP log trên đĩa chứa dấu hiệu B: %s" % tep)
            self.assertIn(MAT_A, tren_dia, "TỆP log trên đĩa không chứa dấu hiệu A: %s" % tep)
        TIEM_LOI["6-khong-ro-ri-cheo-tenant"] = (
            "đường dẫn chứa dấu hiệu A XUẤT HIỆN trong cả hai log (đối chứng dương); query "
            "chứa dấu hiệu B bị cắt ở cả hai (đo trên tệp sau khi ghi ra đĩa)")
        _ghi("6-khong-ro-ri-cheo-tenant", self._testMethodName,
             "2 tệp log trên đĩa: KHÔNG có dấu hiệu B; query ?q=B bị cắt",
             "cùng 2 tệp: CÓ dấu hiệu A trong đường dẫn (bộ quét nhìn thấy dấu hiệu)")

    def test_f3_tep_bang_chung_do_bo_do_sinh_ra_khong_mang_du_lieu_b(self):
        # Quét MỌI tệp bộ đo này đã ghi ra đĩa (log + báo cáo), trừ CSDL/khoá — nơi LƯU dữ liệu
        # của cả hai tenant là thiết kế, không phải rò rỉ. Phạm vi được nói ra, không suy rộng.
        goc = TMP
        tep_bo_qua = {os.path.join(TMP, "du-lieu", "hub.db")}
        da_quet, thay_b, thay_a = 0, [], []
        for thu_muc, _, tep in os.walk(goc):
            for ten in tep:
                duong = os.path.join(thu_muc, ten)
                if duong in tep_bo_qua or ten.startswith("hub.db") or ten.endswith(".key"):
                    continue
                if os.path.getsize(duong) > 8 * 1024 * 1024:
                    continue
                try:
                    with open(duong, "rb") as fh:
                        chu = fh.read().decode("utf-8", "replace")
                except OSError:
                    continue
                da_quet += 1
                if MAT_B in chu:
                    thay_b.append(duong)
                if MAT_A in chu:
                    thay_a.append(duong)
        self.assertGreaterEqual(da_quet, 2, "chỉ quét được %d tệp — phép đo rỗng" % da_quet)
        self.assertEqual(thay_b, [], "tệp bằng chứng trên đĩa chứa dấu hiệu B: %s" % thay_b)
        self.assertGreaterEqual(len(thay_a), 1,
                                "không tệp bằng chứng nào chứa dấu hiệu A ⇒ bộ quét mù")
        _ghi("6-khong-ro-ri-cheo-tenant", self._testMethodName,
             "quét %d tệp bằng chứng bộ đo ghi ra đĩa: 0 tệp chứa dấu hiệu B" % da_quet,
             "%d tệp trong cùng lượt quét CÓ dấu hiệu A (cùng bộ đọc, cùng tiêu chí)"
             % len(thay_a))


# =================================================================================================
# MẶT 7 — KHÔNG GỬI ĐƠN PRODUCTION NGOÀI Ý MUỐN
# =================================================================================================
class G_NoProductionOrder(unittest.TestCase):
    """Mọi đường gọi hãng ở môi trường thật bị TỪ CHỐI; mọi kết nối ra ngoài đều loopback."""

    def test_g1_moi_adapter_dong_cho_phep_live(self):
        ds = adapter.danh_sach_hang()
        self.assertGreaterEqual(len(ds), 2, "không có adapter nào được đăng ký")
        for ma, thong_tin in ds.items():
            self.assertIs(thong_tin["live_mo"], False, "adapter %s mở LIVE" % ma)
            with self.assertRaises(PermissionError, msg="adapter %s dựng được ở sandbox" % ma):
                adapter.tao_adapter(ma, {}, "sandbox")
            with self.assertRaises(PermissionError, msg="adapter %s dựng được ở production" % ma):
                adapter.tao_adapter(ma, {}, "production")
            # Đối chứng dương: mock DỰNG ĐƯỢC — nên các lượt từ chối trên không phải vì
            # adapter không tồn tại hay credentials rỗng.
            ad = adapter.tao_adapter(ma, {}, "mock")
            self.assertEqual(ad.moi_truong, "mock")
        _ghi("7-khong-gui-don-production", self._testMethodName,
             "%d/%d adapter: live_mo=False · dựng sandbox/production ⇒ PermissionError"
             % (len(ds), len(ds)),
             "cùng từng adapter dựng được ở 'mock' (đường dựng không bị hỏng)")

    def test_g2_cong_cau_hinh_va_tang_http_hang_tu_choi_moi_truong_that(self):
        self.assertFalse(cau_hinh.JT_CHO_PHEP_SANDBOX)
        self.assertFalse(cau_hinh.JT_CHO_PHEP_PRODUCTION)
        ok_sb, ly_do_sb = cau_hinh.jt_kiem_moi_truong("sandbox")
        self.assertFalse(ok_sb)
        self.assertIn("V-G09-01", ly_do_sb)
        ok_pr, ly_do_pr = cau_hinh.jt_kiem_moi_truong("production")
        self.assertFalse(ok_pr)
        self.assertIn("duyệt", ly_do_pr)
        with self.assertRaises(PermissionError):
            http_jt.chan_moi_truong("sandbox")
        with self.assertRaises(PermissionError):
            http_jt.chan_moi_truong("production")
        # Đối chứng dương: 'mock' phải MỞ, nếu không thì "từ chối" chỉ là hỏng toàn cục.
        ok_mock, _ = cau_hinh.jt_kiem_moi_truong("mock")
        self.assertTrue(ok_mock)
        http_jt.chan_moi_truong("mock")     # không ném
        _ghi("7-khong-gui-don-production", self._testMethodName,
             "sandbox/production: jt_kiem_moi_truong=False + http_jt.chan_moi_truong ⇒ "
             "PermissionError",
             "'mock' mở ở cả hai cổng (cổng không phải 'chặn tất cả')")

    def test_g3_http_khong_tao_duoc_tai_khoan_hang_production(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/tai-khoan-hang", "POST",
                            {"hang": "jt", "ten": "JT production thu",
                             "moi_truong": "production",
                             "credentials": {"apiKey": "gia-lap"}})
        self.assertEqual(st, 403, "tạo được tài khoản hãng production qua HTTP: %s %s" % (st, kq))
        self.assertIn("BLOCKED", _thanh_chu(kq))
        self.assertIsNone(_db1("SELECT id FROM carrier_accounts WHERE ten='JT production thu'"))
        # Đối chứng dương: CÙNG đường, môi trường mock ⇒ 201 (đường tạo tài khoản vẫn sống).
        st, kq = f["a"].goi("/api/v2/tai-khoan-hang", "POST",
                            {"hang": "jt", "ten": "JT mock thu",
                             "credentials": {"privateKey": "KHOA-GIA-MOCK"}})
        self.assertEqual(st, 201, "mock cũng bị chặn — cổng chặn nhầm: %s %s" % (st, kq))
        _ghi("7-khong-gui-don-production", self._testMethodName,
             "POST tài khoản hãng moi_truong=production ⇒ 403 'BLOCKED' · 0 dòng trong CSDL",
             "CÙNG đường, mặc định mock ⇒ 201")

    def test_g4_gui_don_mock_khong_tao_van_don_that_va_khong_ra_ngoai(self):
        f = FIX
        st, kq = f["a"].goi("/api/v2/don", "POST", _don("Don de gui mock"))
        self.assertEqual(st, 201)
        don_id = kq["don"]["id"]
        st, kq = f["a"].goi("/api/v2/don/%d/duyet" % don_id, "POST", {})
        self.assertEqual(st, 200, kq)
        truoc = len(GHI_MANG.da_noi)
        st, kq = f["a"].goi("/api/v2/don/%d/gui" % don_id, "POST",
                            {"carrier_account_id": f["tk_a"]["id"]})
        self.assertEqual(st, 200, "gửi đơn qua adapter MOCK hỏng: %s %s" % (st, kq))
        don = kq["don"]
        self.assertEqual(don["trang_thai"], "da_gui")
        self.assertRegex(don.get("ma_van_don") or "", r"^VTP\d{10}$",
                         "mã vận đơn không phải dạng GIẢ của adapter mock")
        moi = GHI_MANG.da_noi[truoc:]
        self.assertNotEqual(moi, [], "không ghi nhận kết nối nào — bộ ghi mạng có thể mù")
        self.assertEqual([x for x in moi if not _la_loopback(x[0])], [],
                         "lượt gửi đơn có kết nối RA NGOÀI loopback")
        # PHÉP TIÊM: một đích KHÔNG loopback (TEST-NET-3, RFC 5737) phải bị BẮT và CHẶN.
        truoc_tiem = len(GHI_MANG.da_noi)
        with self.assertRaises(ChanMangNgoai):
            socket.create_connection(("203.0.113.7", 443), timeout=0.05)
        self.assertEqual(len(GHI_MANG.da_noi), truoc_tiem + 1, "bộ ghi mạng KHÔNG thấy đích"
                                                               " ngoài loopback — nó mù")
        self.assertEqual(GHI_MANG.da_noi[-1][0], "203.0.113.7")
        GHI_MANG.da_noi.pop()      # bỏ mục tiêm khỏi tập "lượt chạy sạch"
        TIEM_LOI["7-khong-gui-don-production"] = (
            "gửi đơn mock: %d kết nối, 0 ngoài loopback; TIÊM đích 203.0.113.7 ⇒ bộ ghi BẮT "
            "ĐƯỢC và CHẶN trước syscall" % len(moi))
        _ghi("7-khong-gui-don-production", self._testMethodName,
             "gửi đơn mock ⇒ 'da_gui' + mã GIẢ VTP########## · %d kết nối, 0 ngoài loopback"
             % len(moi),
             "tiêm đích 203.0.113.7 ⇒ ChanMangNgoai, bộ ghi thấy đích (bộ ghi không mù)")

    def test_g5_toan_bo_luot_chay_chi_mo_ket_noi_loopback(self):
        # Không phải một ca mới về hành vi sản phẩm — đây là phán quyết trên TOÀN BỘ lượt chạy:
        # mọi kết nối đã mở (trừ mục tiêm đã bị chính ca G4 gỡ khỏi sổ) phải là loopback.
        ngoai = GHI_MANG.ngoai_loopback()
        self.assertEqual(ngoai, [], "lượt chạy có kết nối RA NGOÀI loopback: %s" % ngoai)
        self.assertGreater(len(GHI_MANG.da_noi), 10,
                           "chỉ ghi được %d kết nối — bộ ghi mạng có thể mù"
                           % len(GHI_MANG.da_noi))
        self.assertIn(CONG, {x[1] for x in GHI_MANG.da_noi},
                      "không thấy kết nối tới máy chủ của bộ đo (cổng %d) trong sổ" % CONG)
        # D-8 (PostgreSQL) là BLOCKED OWNER: lượt chạy này KHÔNG được có một kết nối nào tới
        # 5432, và đây là chỗ ĐO điều đó chứ không chỉ khai.
        self.assertNotIn(5432, {x[1] for x in GHI_MANG.da_noi},
                         "lượt chạy có kết nối tới cổng 5432 — D-8 là BLOCKED OWNER")
        # Đối chứng âm của chính hàm phân loại: phải nói KHÔNG với một địa chỉ ngoài.
        self.assertFalse(_la_loopback("203.0.113.7"))
        _ghi("7-khong-gui-don-production", self._testMethodName,
             "toàn bộ lượt chạy: %d kết nối đã mở, 0 đích ngoài loopback, 0 kết nối :5432"
             % len(GHI_MANG.da_noi),
             "có kết nối tới cổng %d của máy chủ bộ đo; hàm phân loại nói False với 203.0.113.7"
             % CONG)


# =================================================================================================
# Z — TỔNG KẾT: BẢNG BẢY MẶT + TỰ PHÁN
# =================================================================================================
def _in_bang():
    rong = 118
    print("\n" + "=" * rong)
    print("BẢNG BẰNG CHỨNG — 7 MẶT · AGENT 04 (G22 REGRESSION & SECURITY)")
    print("=" * rong)
    for mat in BAY_MAT:
        ds = BANG.get(mat, [])
        print("\n[%s]  %d ca có bằng chứng" % (mat, len(ds)))
        for ban in ds:
            print("   · %-46s ĐO ĐƯỢC : %s" % (ban["ca"], ban["do"]))
            print("     %-46s ĐỐI CHỨNG: %s" % ("", ban["dc"]))
        print("   · TIÊM LỖI: %s" % TIEM_LOI.get(mat, "<THIẾU — PHÉP ĐO CHƯA CHỨNG MINH BẮT ĐƯỢC>"))
    print("\n" + "-" * rong)
    print("TỔNG: %d/%d mặt có bằng chứng · %d ca ghi sổ · %d/%d mặt đã tiêm lỗi"
          % (len([m for m in BAY_MAT if BANG.get(m)]), len(BAY_MAT),
             sum(len(v) for v in BANG.values()),
             len([m for m in BAY_MAT if TIEM_LOI.get(m)]), len(BAY_MAT)))
    print("THƯ MỤC BẰNG CHỨNG TRÊN ĐĨA: %s" % TMP)
    print("=" * rong)


# =================================================================================================
# TIÊM LỖI NGOÀI (end-to-end) — chứng minh bộ kiểm KHÔNG PHẢI "luôn xanh"
# =================================================================================================
# Vì sao cần, khi mỗi mặt đã có phép tiêm nội bộ: phép tiêm nội bộ chứng minh PHÉP ĐO phân biệt
# được hai giá trị. Nó KHÔNG chứng minh rằng cả bộ kiểm sẽ ĐỎ nếu sản phẩm hồi quy. Muốn chứng
# minh điều đó thì phải TIÊM LỖI VÀO SẢN PHẨM rồi chạy lại. Việc đó KHÔNG được làm trên cây
# thật (phạm vi ghi của làn này chỉ có hai tệp), nên mỗi phép tiêm dựng một BẢN SAO trong TMP,
# sửa ĐÚNG một đoạn trong bản sao, rồi chạy CHÍNH bộ kiểm này trên bản sao đó.
BANG_TIEM_NGOAI = [
    ("1-tenant-isolation", "don_hang.py",
     'return csdl.mot("SELECT * FROM don_hang WHERE id=? AND tenant_id=?", (don_id, tenant_id))',
     'return csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))',
     "test_a2_a_khong_doc_duoc_don_cua_b"),
    ("2-rbac", "server.py",
     "        if not nc.co_quyen(hanh_dong):",
     "        if False and not nc.co_quyen(hanh_dong):",
     "test_b1_viewer_tao_don_bi_chan_403_va_khong_tao_dong_nao"),
    ("3-fail-closed", "migrate.py",
     "    if kho is None:\n        _tu_choi_chua_khai(nguon)",
     "    if kho is None:\n        pass  # TIEM_NGOAI: bo chot fail-closed",
     "test_c1_sao_luu_tu_choi_khi_chua_khai_kho"),
    ("4-idempotency", "don_hang.py",
     "if idem_key:",
     "if False:  # TIEM_NGOAI: bo khoa chong trung",
     "test_d1_cung_idempotency_key_hai_lan_chi_mot_don"),
    ("5-webhook-security", "webhook.py",
     "    return bool(ok)",
     "    return True  # TIEM_NGOAI: chap nhan moi chu ky",
     "test_e2_chu_ky_sai_bi_tu_choi_401_va_khong_tao_su_kien"),
    ("6-khong-ro-ri-cheo-tenant", "server.py",
     "                             duong=_doan_duong_dan_trong_log(\n"
     "                                 self.path.split(\"?\")[0].split(\"#\")[0])[:300],",
     "                             duong=self.path[:300],  # TIEM_NGOAI: ghi ca query",
     "test_f2_log_tren_dia_khong_mang_du_lieu_b_va_query_bi_cat"),
    ("7-khong-gui-don-production", "adapter_jt.py",
     "    CHO_PHEP_LIVE = False    # BLOCKED: cần credentials thật + Owner duyệt",
     "    CHO_PHEP_LIVE = True    # TIEM_NGOAI: mo live",
     "test_g1_moi_adapter_dong_cho_phep_live"),
]
TIEM_NGOAI = []


def _tiem_ngoai_mot_ca(mat, tep, cu, moi, ca):
    """Dựng bản sao cây trong TMP, tiêm ĐÚNG một đoạn trong bản sao, chạy CHÍNH bộ kiểm này.

    Trả `(rc, đầu ra gộp)`. `rc=None` nghĩa là phép tiêm của BỘ ĐO hỏng (không tìm thấy đoạn
    nguồn / bản tiêm không còn hợp lệ cú pháp) — phải báo HỎNG, không được tính là ĐẠT.
    """
    dich = tempfile.mkdtemp(prefix="ghe-%s-" % mat[:2], dir=TMP)
    shutil.copytree(GOC_APP, os.path.join(dich, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "du-lieu", "*.pyc"))
    duong = os.path.join(dich, "app", tep)
    with open(duong, encoding="utf-8") as f:
        nguon = f.read()
    if nguon.count(cu) < 1:
        return None, "KHÔNG tìm thấy đoạn nguồn để tiêm trong %s — phép tiêm của bộ đo HỎNG" % tep
    nguon_moi = nguon.replace(cu, moi)
    try:
        ast.parse(nguon_moi)
    except SyntaxError as e:
        return None, "bản tiêm vào %s KHÔNG hợp lệ cú pháp: %s" % (tep, e)
    with open(duong, "w", encoding="utf-8") as f:
        f.write(nguon_moi)
    env = {k: v for k, v in os.environ.items() if not k.startswith("VIP_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["VIP_G22_A4_KHONG_TIEM_NGOAI"] = "1"   # chống đệ quy: cây gương không tiêm lồng nhau
    p = subprocess.run([sys.executable, os.path.join("app", "thu", "thu_g22_regression.py")],
                       cwd=dich, env=env, capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


class Z_TongKet(unittest.TestCase):
    """Chốt chặn chạy CUỐI: bảng phải đủ bảy mặt, mọi ca phủ định phải có đối chứng, cả bảy mặt
    phải có phép tiêm lỗi, và phép tiêm lỗi NGOÀI (end-to-end) phải làm bộ kiểm ĐỎ ĐÚNG CA."""

    def test_z1_bang_bay_mat_du_va_moi_ca_co_doi_chung(self):
        thieu = [m for m in BAY_MAT if not BANG.get(m)]
        self.assertEqual(thieu, [], "mặt KHÔNG có bằng chứng: %s" % thieu)
        for mat in BAY_MAT:
            for ban in BANG[mat]:
                self.assertTrue(ban["dc"].strip(),
                                "ca %s (%s) là ca phủ định nhưng THIẾU đối chứng đường"
                                % (ban["ca"], mat))
        thieu_tiem = [m for m in BAY_MAT if not TIEM_LOI.get(m)]
        self.assertEqual(thieu_tiem, [], "mặt chưa TIÊM LỖI (phép đo chưa chứng minh bắt được "
                                        "lỗi): %s" % thieu_tiem)

    def test_z2_may_do_khong_mu_quet_dau_hieu_co_va_khong(self):
        # Cùng một hàm quét, hai đầu vào khác nhau: phải PHÂN BIỆT được.
        self.assertTrue(_quet({"ghi_chu": "truoc " + MAT_B + " sau"}, MAT_B))
        self.assertFalse(_quet({"ghi_chu": "truoc " + MAT_A + " sau"}, MAT_B))
        # Kênh log: tiêm dấu hiệu vào CHÍNH bộ ghi log của hệ rồi quét lại — chứng minh bộ quét
        # đọc được định dạng JSONL thật, không chỉ chuỗi tự dựng.
        bay = io.StringIO()
        cu = quan_sat.dat_luong_log(bay)
        try:
            quan_sat.ghi("kiem_tra_may_do", duong="/" + MAT_B)
        finally:
            quan_sat.dat_luong_log(cu)
        chu = bay.getvalue()
        self.assertIn(MAT_B, chu, "bộ ghi log không giữ dấu hiệu trong 'duong' ⇒ bộ quét của "
                                  "f2 có thể mù")
        self.assertIn('"loai": "kiem_tra_may_do"', chu, "dòng log không phải JSONL đọc được")
        _ghi("6-khong-ro-ri-cheo-tenant", self._testMethodName,
             "bộ quét: thấy dấu hiệu B trong thân/dòng log KHI nó có mặt",
             "bộ quét: KHÔNG báo dấu hiệu B khi chỉ có dấu hiệu A (không báo nhầm)")

    def test_z3_tiem_loi_ngoai_lam_bo_kiem_do_dung_ca(self):
        if os.environ.get("VIP_G22_A4_KHONG_TIEM_NGOAI") == "1":
            # Bản đang chạy LÀ cây gương của một phép tiêm ngoài: tiêm lồng nhau là đệ quy vô
            # hạn. Đây là chốt của BỘ ĐO, không phải một ca nghiệm thu bị bỏ qua.
            print("[tiem-ngoai] cây gương — bỏ qua phép tiêm ngoài để tránh đệ quy")
            return
        print("\nTIÊM LỖI NGOÀI — mỗi mặt một lỗi THẬT trong BẢN SAO cây, đòi bộ kiểm ĐỎ ĐÚNG CA")
        for mat, tep, cu, moi, ca in BANG_TIEM_NGOAI:
            rc, ra = _tiem_ngoai_mot_ca(mat, tep, cu, moi, ca)
            self.assertIsNotNone(rc, ra)
            self.assertNotEqual(
                rc, 0,
                "tiêm lỗi '%s' vào %s mà bộ kiểm VẪN XANH — phép đo KHÔNG bắt được lỗi\n%s"
                % (mat, tep, ra[-4000:]))
            self.assertIn(
                "FAIL: " + ca, ra,
                "bộ kiểm đỏ nhưng KHÔNG đúng ca '%s' — lỗi bị một ca KHÁC bắt, nên không chứng "
                "minh được ca này đo đúng thứ nó tuyên bố\n%s" % (ca, ra[-4000:]))
            TIEM_NGOAI.append((mat, tep, ca, rc))
        self.assertEqual(len(TIEM_NGOAI), len(BAY_MAT))
        print("\n%-30s %-16s %-4s %s" % ("MẶT", "TỆP BỊ TIÊM", "rc", "CA BẮT ĐƯỢC (ĐỎ)"))
        for mat, tep, ca, rc in TIEM_NGOAI:
            print("%-30s %-16s %-4s %s" % (mat, tep, rc, ca))
        print("TỰ PHÁN: %d/%d phép tiêm ngoài làm bộ kiểm ĐỎ ĐÚNG CA"
              % (len(TIEM_NGOAI), len(BAY_MAT)))

    def test_z9_in_bang_cuoi(self):
        """In bảng SAU CÙNG — để con số tổng kết bao gồm cả các dòng của Z2/Z3."""
        self.assertEqual(len(TIEM_NGOAI), len(BAY_MAT),
                         "chưa chạy đủ phép tiêm ngoài: %d/%d"
                         % (len(TIEM_NGOAI), len(BAY_MAT)))
        _in_bang()


if __name__ == "__main__":
    unittest.main(verbosity=2)
