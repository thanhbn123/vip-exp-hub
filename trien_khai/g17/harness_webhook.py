#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G17 — HARNESS WEBHOOK: REPLAY CÓ UỶ QUYỀN + CHỐNG TRÙNG Ở TẦNG CSDL (AG-04).

Harness này đo HAI thứ mà bộ thử đơn vị không đo được: hành vi qua **HTTP thật** (máy chủ
`server.py`, cổng do hệ điều hành cấp, CHỈ loopback) và hành vi của **CSDL thật** (SQLite trên
nền tạm, câu INSERT nhồi thẳng, không qua hàm nghiệp vụ).

BA LOẠI PHÁN QUYẾT, và loại thứ ba là chỗ dễ tự lừa mình nhất:
  · `ĐẠT` / `ĐẠT (MOCK)` — chặng đã chạy THẬT trên nền tạm, bằng chứng là số đo.
  · `HỎNG` — chặng chạy được nhưng kết quả sai.
  · `BLOCKED` — chặng KHÔNG THỂ chạy vì thiếu giấy phép, và nó ghi ra **đúng cái còn thiếu**.
    `BLOCKED` **KHÔNG BAO GIỜ được tính là đạt**; bộ đếm ở `dem_phuong_an()` xếp nó một ô riêng,
    và `--tu-kiem` tự kiểm chính bộ đếm đó (một bộ đếm xếp `BLOCKED` vào ô "đạt" thì bảng tổng
    kết vẫn xanh trong khi chặng chạm hãng chưa từng chạy).

KHÔNG GỌI HÃNG THẬT, KỂ CẢ SANDBOX (`V-G09-01` + `V-13906-05` CHƯA CẤP). Mọi phép đo lớp HTTP
đi qua **stub bind `127.0.0.1` cổng `0`** (`StubHang`), không qua tên miền nào. Stub có chốt
loopback RIÊNG của nó: đích không phải loopback thì nó từ chối chuyển tiếp, kể cả khi ai đó đã
sửa chốt của harness.

CHẠY
----
    sh trien_khai/g17/chay_harness.sh
    python3 trien_khai/g17/harness_webhook.py --tu-kiem       # chỉ tự kiểm, không dựng gì
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
GOC_G17 = os.path.dirname(os.path.abspath(__file__))
if GOC_G17 not in sys.path:
    sys.path.insert(0, GOC_G17)
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)

import chot_an_toan                                                        # noqa: E402

DAT, DAT_MOCK, HONG, BLOCKED, BO_QUA = "DAT", "DAT_MOCK", "HONG", "BLOCKED", "BO_QUA"
KY_HIEU = {DAT: "✓", DAT_MOCK: "✓", HONG: "✗", BLOCKED: "⊘", BO_QUA: "–"}
NHAN = {DAT: "ĐẠT", DAT_MOCK: "ĐẠT (MOCK)", HONG: "HỎNG", BLOCKED: "BLOCKED", BO_QUA: "BỎ QUA"}

# Giấy phép còn thiếu cho mọi chặng CHẠM HÃNG. Không phải chuỗi trang trí: đây là thứ chốt an
# toàn số 7 đọc để từ chối chạy nếu có ai khai là đã cấp.
THIEU_GOI_HANG = ("V-G09-01 (gọi API hãng, kể cả sandbox)", "V-13906-05 (credentials sandbox J&T)")
THIEU_SANDBOX_CALLBACK = ("câu 24 (sandbox J&T có đẩy callback không)",
                          "câu 6–7 (khoá ký + chuỗi đem đi ký của chiều callback)")


def buoc_can_giay_phep():
    """Chặng nào CHẠM HÃNG thì phải khai mã giấy phép nó cần. Chốt an toàn số 7 đọc hàm này.

    Cố ý trả về ĐÚNG một chặng: harness G17 chỉ có một chặng chạm hãng, và nó là `BLOCKED`. Một
    danh sách rỗng ở đây nghĩa là chốt không canh gì — `chot_an_toan` từ chối đúng vì thế.
    """
    return {"G17-SANDBOX": ("V-G09-01", "V-13906-05")}


def phan_quyet_sandbox(cong_sb, cong_pr, duoc_sb):
    """Phán quyết cho chặng CHẠM HÃNG. Hàm riêng để bộ thử đơn vị gọi được mà không cần máy chủ.

    `cong_sb`/`cong_pr` là cổng môi trường đọc từ `cau_hinh`, `duoc_sb` là câu trả lời của hàm
    dẫn xuất trong adapter. Phán quyết LUÔN là `BLOCKED` — ba tham số chỉ để bằng chứng nói ra
    trạng thái ĐO ĐƯỢC của ba cổng, chứ không phải để chặng này có thể thành "đạt".
    """
    return {
        "trang_thai": BLOCKED,
        "bang_chung": ("thiếu: %s · %s · và biến môi trường %s. ĐO ĐƯỢC:"
                       " cau_hinh.JT_CHO_PHEP_SANDBOX=%s · JT_CHO_PHEP_PRODUCTION=%s ·"
                       " adapter_jt.moi_truong_duoc_chay('sandbox')=%s ⇒ chặng này KHÔNG chạy được,"
                       " và KHÔNG được tính là đạt."
                       % (" · ".join(THIEU_GOI_HANG), " · ".join(THIEU_SANDBOX_CALLBACK),
                          chot_an_toan.BIEN_GIAY_PHEP, cong_sb, cong_pr, duoc_sb)),
    }


BUOC = []


def ket(ma, ten, trang_thai, bang_chung=""):
    """Ghi một chặng. `bang_chung` là SỐ ĐO, không phải lời khai."""
    BUOC.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    print("  %s [%s] %s" % (KY_HIEU[trang_thai], ma, ten))
    if bang_chung:
        print("        %s" % bang_chung)
    return trang_thai


def la_dat(trang_thai):
    """`BLOCKED` và `BỎ QUA` KHÔNG phải đạt. Một dòng, để không chỗ nào tự định nghĩa lại."""
    return trang_thai in (DAT, DAT_MOCK)


def dem_phuong_an(ds):
    """Đếm theo phán quyết. `BLOCKED` có ô RIÊNG — không bao giờ cộng vào ô đạt."""
    dem = {DAT: 0, DAT_MOCK: 0, HONG: 0, BLOCKED: 0, BO_QUA: 0}
    for x in ds:
        dem[x["trang_thai"]] = dem.get(x["trang_thai"], 0) + 1
    return dem


def tu_kiem_dem():
    """TỰ KIỂM BỘ ĐẾM: `BLOCKED` không được tính là đạt, và `ĐẠT` thì phải được tính.

    Đối chứng DƯƠNG nằm trong chính bộ này (ca A, ca B): thiếu nó thì một hàm `la_dat()` luôn
    trả `False` cũng "bắt được" ca `BLOCKED` và trông như đang hoạt động.
    """
    ca = [("A", DAT, True), ("B", DAT_MOCK, True), ("C", BLOCKED, False),
          ("D", HONG, False), ("E", BO_QUA, False)]
    hong, ket_qua = 0, []
    for ma, tt, mong_doi in ca:
        thuc_te = la_dat(tt)
        dem = dem_phuong_an([{"trang_thai": tt}])
        # Ca `BLOCKED` phải nằm ở ô `BLOCKED` và ô đạt phải bằng 0 — nếu bộ đếm gộp nó vào
        # `DAT`/`DAT_MOCK` thì bảng tổng kết nói dối mà không ai thấy.
        dung_o = (dem[BLOCKED] == 1 and dem[DAT] + dem[DAT_MOCK] == 0) if tt == BLOCKED \
            else (dem.get(tt, 0) == 1)
        dat = (thuc_te == mong_doi) and dung_o
        if not dat:
            hong += 1
        ket_qua.append({"ma": ma, "trang_thai": tt, "mong_doi_la_dat": mong_doi,
                        "thuc_te_la_dat": thuc_te, "dung_o_dem": dung_o, "dat": dat})
    return len(ca), hong, ket_qua


# ============================================================================
# STUB BÊN GỬI CỦA HÃNG — bind 127.0.0.1 CỔNG 0, không ra khỏi máy
# ============================================================================
class StubHang(object):
    """Máy chủ stub đóng vai BÊN GỬI callback của hãng.

    Vì sao là một máy chủ HTTP chứ không phải một lời gọi `urllib` trần: mọi phép đo lớp HTTP
    của lượt này phải đi qua một stub bind `127.0.0.1` **cổng 0** (hệ điều hành cấp). Stub giữ
    bí mật ký trong bộ nhớ của tiến trình harness — bí mật KHÔNG đi qua HTTP và KHÔNG vào log.

    Stub còn một chốt RIÊNG, độc lập với `chot_an_toan`: đích không phải loopback thì nó từ chối
    chuyển tiếp. Hai chốt độc lập cho cùng một bất biến, vì đây là bất biến tuyệt đối của lượt.
    """

    def __init__(self, goc_hub, webhook_ma, secret):
        self.goc_hub = goc_hub
        self.webhook_ma = webhook_ma
        self._secret = secret
        self.so_lan_chuyen_tiep = 0
        self.sv = None
        self.cong = None

    def bat_dau(self):
        stub = self

        class BoXuLy(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):        # không in ra log: không bí mật, không ồn
                pass

            def _tra(self, ma, than):
                b = json.dumps(than, ensure_ascii=False).encode()
                self.send_response(ma)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def do_POST(self):
                if self.path != "/day-callback":
                    return self._tra(404, {"loi": "đường này không có"})
                n = int(self.headers.get("Content-Length") or 0)
                try:
                    d = json.loads(self.rfile.read(n) or b"{}")
                except ValueError:
                    return self._tra(400, {"loi": "thân yêu cầu không phải JSON"})
                than = base64.b64decode(d.get("than_b64") or "")
                # CHỐT LOOPBACK CỦA STUB: đích phải là 127.0.0.1/localhost/::1.
                host = urllib.parse.urlparse(stub.goc_hub).hostname or ""
                if host not in ("127.0.0.1", "localhost", "::1"):
                    return self._tra(500, {"loi": "stub từ chối đích không phải loopback: %r"
                                                  % stub.goc_hub})
                hdr = {"X-Webhook-Signature": hmac.new(stub._secret.encode(), than,
                                                       hashlib.sha256).hexdigest()}
                hdr.update(d.get("headers") or {})
                yc = urllib.request.Request(
                    "%s/api/v2/webhook/nhan/%s" % (stub.goc_hub, stub.webhook_ma),
                    data=than, headers=hdr, method="POST")
                stub.so_lan_chuyen_tiep += 1
                try:
                    with urllib.request.urlopen(yc, timeout=20) as ph:
                        return self._tra(200, {"http": ph.status,
                                               "than": json.loads(ph.read() or b"{}")})
                except urllib.error.HTTPError as e:
                    return self._tra(200, {"http": e.code, "than": json.loads(e.read() or b"{}")})
                except Exception as e:                                   # noqa: BLE001
                    return self._tra(200, {"http": 0, "loi": "%s: %s" % (type(e).__name__, e)})

        self.sv = ThreadingHTTPServer(("127.0.0.1", 0), BoXuLy)   # CỔNG 0 — hệ điều hành cấp
        self.cong = self.sv.server_address[1]
        threading.Thread(target=self.sv.serve_forever, name="g17-stub", daemon=True).start()
        return self

    def day(self, than, headers=None):
        """Gửi một callback qua stub. Trả `(http_cua_hub, than_cua_hub)`."""
        yc = urllib.request.Request(
            "http://127.0.0.1:%d/day-callback" % self.cong,
            data=json.dumps({"than_b64": base64.b64encode(than).decode(),
                             "headers": headers or {}}, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(yc, timeout=30) as ph:
            kq = json.loads(ph.read() or b"{}")
        return kq.get("http", 0), (kq.get("than") or {"loi": kq.get("loi")})

    def dung(self):
        if self.sv is not None:
            self.sv.shutdown()
            self.sv.server_close()


# ============================================================================
# KHÁCH HTTP (cookie + CSRF header) và tiện ích CSDL
# ============================================================================
class Khach(object):
    def __init__(self, goc):
        self.goc = goc
        self.ck = {}

    def goi(self, duong, pt="GET", body=None, tho=None, hdr=None):
        d = (tho if tho is not None else
             (json.dumps(body, ensure_ascii=False).encode() if body is not None else None))
        r = urllib.request.Request(self.goc + duong, data=d, method=pt)
        r.add_header("X-Requested-With", "VIPHub")
        if d is not None:
            r.add_header("Content-Type", "application/json")
        if self.ck:
            r.add_header("Cookie", "; ".join("%s=%s" % kv for kv in self.ck.items()))
        for k, v in (hdr or {}).items():
            r.add_header(k, v)
        try:
            with urllib.request.urlopen(r, timeout=25) as f:
                for h in f.headers.get_all("Set-Cookie") or []:
                    k, _, v = h.split(";")[0].partition("=")
                    self.ck[k] = v
                b = f.read()
                return f.status, (json.loads(b) if b[:1] == b"{" else b)
        except urllib.error.HTTPError as e:
            b = e.read()
            return e.code, (json.loads(b) if b[:1] == b"{" else b[:300])


def _doc_duong_hub(log):
    """Đọc cổng THẬT từ dòng log server.py in ra (`bind cổng 0` ⇒ cổng do hệ điều hành cấp)."""
    with open(log, encoding="utf-8", errors="replace") as f:
        m = re.search(r"chạy tại http://([0-9.]+):(\d+)", f.read())
    return ("http://%s:%s" % (m.group(1), m.group(2)), int(m.group(2))) if m else (None, None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--giu-nen", action="store_true")
    ap.add_argument("--tu-kiem", action="store_true",
                    help="chỉ tự kiểm bộ đếm phán quyết + bộ dò chốt an toàn, không dựng nền")
    a = ap.parse_args()

    if a.tu_kiem:
        print("═" * 78)
        print("TỰ KIỂM CỦA HARNESS G17 (không dựng nền, không mở máy chủ)")
        print("═" * 78)
        tong, hong, _ = tu_kiem_dem()
        print("  bộ đếm phán quyết: %d/%d ca đạt" % (tong - hong, tong))
        print("  (BLOCKED nằm ô riêng · ĐẠT và ĐẠT (MOCK) mới là đạt · HỎNG/BỎ QUA không là đạt)")
        for ma, tt, mong in (("A", DAT, True), ("C", BLOCKED, False)):
            d = dem_phuong_an([{"trang_thai": tt}])
            print("    [%s] %-8s → la_dat=%s (mong đợi %s) · đếm=%s"
                  % (ma, NHAN[tt], la_dat(tt), mong, {k: v for k, v in d.items() if v}))
        if hong:
            print("BỘ ĐẾM HỎNG — bảng tổng kết của harness này không đáng tin.")
            return 1
        print("Bộ đếm ĐẠT: %d/%d." % (tong - hong, tong))
        return 0

    nen = os.environ.get("VIP_HUB_DATA") or ""
    goc_hub_du_kien = "http://127.0.0.1:0"     # chỉ để chốt số 6 soi; cổng thật đọc từ log
    print("═" * 78)
    print("G17 — HARNESS WEBHOOK (REPLAY + CHỐNG TRÙNG) · nền %s" % (nen or "<chưa đặt>"))
    print("═" * 78)

    # ---------------------------------------------------------------- bảy chốt an toàn
    ly_do = chot_an_toan.ly_do_tu_choi(nen, goc_url=goc_hub_du_kien)
    if ly_do:
        print("\nTỪ CHỐI CHẠY — mất ít nhất một chốt an toàn:")
        for x in ly_do:
            print("  · " + x)
        print("\nHarness này TẠO dữ liệu THẬT trong CSDL và nói chuyện HTTP. Chạy nó khi mất chốt")
        print("là thứ nguy hiểm hơn không có harness. Không có cờ nào để bỏ qua.")
        return 4
    print("  ✓ bảy chốt an toàn: ĐỦ (nền tạm · bind loopback · CHO_PHEP_LIVE=False · không gọi"
          " hãng · chặng chạm hãng khai đúng giấy phép còn thiếu)")

    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1", VIP_HUB_BACKOFF="0.01")
    env.pop(chot_an_toan.CO_GOI_HANG, None)
    env.pop(chot_an_toan.BIEN_GIAY_PHEP, None)
    sv, stub = None, None
    try:
        # ------------------------------------------------------------ dựng nền tạm
        print("\n── DỰNG NỀN TẠM ──────────────────────────────────────────────")
        for lenh, nhan in (("migrate.py", "migrate"), ("khoi_tao.py", "seed")):
            p = subprocess.run([sys.executable, os.path.join(GOC_APP, lenh)],
                               capture_output=True, text=True, env=env, cwd=DU_AN)
            if p.returncode:
                print("  ✗ %s hỏng: %s" % (nhan, (p.stderr or p.stdout)[-400:]))
                return 3
            print("  ✓ %s" % nhan)
        log = os.path.join(nen, "server.log")
        with open(log, "w") as f:
            # `-u`: KHÔNG đệm stdout. Không có nó thì dòng in ra cổng THẬT nằm trong bộ đệm và
            # harness ngồi đợi một dòng đã được viết ra từ lâu — đo được ở lượt chạy đầu tiên
            # (log rỗng, chờ 20 giây, thoát 3). Cổng vẫn là 0: hệ điều hành cấp, và cổng thật
            # đọc từ chính dòng log ấy chứ không từ một hằng số viết sẵn.
            sv = subprocess.Popen([sys.executable, "-u", os.path.join(GOC_APP, "server.py"), "0"],
                                  stdout=f, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
        # Ghi PID ra tệp để bộ chạy shell dọn được theo ĐÚNG PID nếu tiến trình này chết giữa
        # đường. KHÔNG pkill/killall ở bất kỳ đâu: trên máy nhiều làn, `pkill -f server.py` giết
        # cả máy chủ của làn khác.
        with open(os.path.join(nen, "hub.pid"), "w") as f:
            f.write(str(sv.pid))
        goc, cong = None, None
        for _ in range(100):
            goc, cong = _doc_duong_hub(log)
            if goc:
                break
            if sv.poll() is not None:
                print("  ✗ máy chủ chết khi khởi động:\n%s"
                      % open(log, encoding="utf-8", errors="replace").read()[-600:])
                return 3
            time.sleep(0.2)
        if not goc:
            print("  ✗ không đọc được cổng THẬT từ log máy chủ")
            return 3
        print("  ✓ máy chủ %s (pid %d) — bind CỔNG 0, chỉ loopback" % (goc, sv.pid))
        ket("G17-00", "bảy chốt an toàn + máy chủ loopback cổng 0", DAT,
            "nền=%s · pid=%d · địa chỉ thật=%s" % (nen, sv.pid, goc))

        db = os.path.join(nen, "hub.db")

        def sql(q, p=()):
            c = sqlite3.connect(db, timeout=30)
            c.row_factory = sqlite3.Row
            try:
                return [dict(x) for x in c.execute(q, p)]
            finally:
                c.close()

        def ghi_thang(q, p=()):
            """Ghi bằng kết nối RIÊNG, không qua `csdl` — để đo đúng tầng CSDL."""
            c = sqlite3.connect(db, timeout=30, isolation_level=None)
            try:
                c.execute("PRAGMA busy_timeout=30000")
                return c.execute(q, p)
            finally:
                c.close()

        def dem(bang, dk="1=1", ts=()):
            return sql("SELECT COUNT(*) c FROM %s WHERE %s" % (bang, dk), ts)[0]["c"]

        def audit_dem(hanh_dong, sk_id):
            return dem("audit", "hanh_dong=? AND resource_type='su_kien' AND resource_id=?",
                       (hanh_dong, str(sk_id)))

        def doi_den(sk_id, cac_tt, toi_da=150):
            r = None
            for _ in range(toi_da):
                r = sql("SELECT trang_thai, so_lan_thu, loi_cuoi FROM wh_su_kien WHERE id=?",
                        (sk_id,))
                if r and r[0]["trang_thai"] in cac_tt:
                    return r[0]
                time.sleep(0.2)
            return r[0] if r else None

        os.environ["VIP_HUB_DATA"] = nen
        import adapter                     # noqa: E402,F401
        import adapter_jt                  # noqa: E402,F401
        import bao_mat                     # noqa: E402
        import cau_hinh                    # noqa: E402
        import webhook as wh               # noqa: E402

        # ------------------------------------------------------------ G17-01/02 nền nghiệp vụ
        print("\n── G17-01. ĐĂNG NHẬP + HAI TENANT ────────────────────────────")
        k = Khach(goc)
        mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`",
                             open(os.path.join(nen, "TAI-KHOAN-DEMO.md"),
                                  encoding="utf-8").read()))
        st, _ = k.goi("/api/v2/auth/dang-nhap", "POST",
                      {"ten_dang_nhap": "platform-owner", "mat_khau": mk["platform-owner"]})
        st_a, kq_a = k.goi("/api/v2/platform/tenants", "POST",
                           {"ten": "Cty G17A", "owner_ten_dang_nhap": "g17-owner-a",
                            "owner_mat_khau": "g17-owner-a-123", "goi_id": "pro"})
        st_b, kq_b = k.goi("/api/v2/platform/tenants", "POST",
                           {"ten": "Cty G17B", "owner_ten_dang_nhap": "g17-owner-b",
                            "owner_mat_khau": "g17-owner-b-123", "goi_id": "pro"})
        tid_a = (kq_a.get("id") or (kq_a.get("tenant") or {}).get("id")) if isinstance(kq_a, dict) else None
        tid_b = (kq_b.get("id") or (kq_b.get("tenant") or {}).get("id")) if isinstance(kq_b, dict) else None
        ket("G17-01", "đăng nhập + tạo hai tenant qua cửa platform",
            DAT if (st == 200 and st_a == 201 and st_b == 201) else HONG,
            "HTTP %s/%s/%s · tenant A=%s · tenant B=%s" % (st, st_a, st_b, tid_a, tid_b))
        if not tid_a or not tid_b:
            return 1

        k_a, k_b = Khach(goc), Khach(goc)
        k_a.goi("/api/v2/auth/dang-nhap", "POST",
                {"ten_dang_nhap": "g17-owner-a", "mat_khau": "g17-owner-a-123"})
        k_b.goi("/api/v2/auth/dang-nhap", "POST",
                {"ten_dang_nhap": "g17-owner-b", "mat_khau": "g17-owner-b-123"})

        print("\n── G17-02. TÀI KHOẢN HÃNG + ĐƠN (MOCK) ───────────────────────")
        st, kq = k_a.goi("/api/v2/tai-khoan-hang", "POST",
                         {"hang": "jt", "ten": "J&T G17 (mock)",
                          "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
        tk_id = kq.get("id") if isinstance(kq, dict) else None
        wh_ma = (kq.get("webhook_url", "") if isinstance(kq, dict) else "").rsplit("/", 1)[-1]
        row = sql("SELECT hang, moi_truong, kich_hoat, webhook_ma, webhook_secret_ma_hoa"
                  " FROM carrier_accounts WHERE id=?", (tk_id,)) if tk_id else []
        if not row or row[0]["moi_truong"] != "mock":
            ket("G17-02", "tài khoản hãng J&T môi trường mock", HONG,
                "HTTP %s · hàng=%s" % (st, row[0] if row else "không có"))
            return 1
        # Bí mật KHÔNG in ra: chỉ dùng để ký cục bộ, và chỉ kiểm DẠNG mã hoá at-rest.
        secret = bao_mat.giai_ma_wh(row[0]["webhook_secret_ma_hoa"], row[0]["webhook_ma"])
        kín = str(row[0]["webhook_secret_ma_hoa"]).startswith("v") and "$" in str(row[0]["webhook_secret_ma_hoa"])
        ket("G17-02", "tài khoản hãng J&T (mock) + bí mật mã hoá at-rest (không in giá trị)",
            DAT_MOCK if (st == 201 and tk_id and kín) else HONG,
            "HTTP %s · id=%s · môi trường=%s · webhook_ma=%s · dạng mã hoá=%s"
            % (st, tk_id, row[0]["moi_truong"], wh_ma, "v…$…" if kín else "LẠ"))

        st, kq = k_a.goi("/api/v2/don", "POST", {
            "nguoi_nhan_ten": "Người nhận G17", "nguoi_nhan_sdt": "0901234567",
            "nguoi_nhan_dia_chi": "12 Lê Lợi, Quận 1, TP HCM",
            "nguoi_gui_ten": "Kho G17", "nguoi_gui_sdt": "0900000000",
            "nguoi_gui_dia_chi": "1 Kho, Q7, TP HCM",
            "hang_hoa": "Áo thun thử", "khoi_luong_gram": 500, "cod": 250000,
            "tien_thu_ho": 250000})
        don = (kq.get("don") or {}) if isinstance(kq, dict) else {}
        don_id, mvd = don.get("id"), don.get("ma_van_don")
        k_a.goi("/api/v2/don/%d/duyet" % don_id, "POST", {})
        st_g, kq_g = k_a.goi("/api/v2/don/%d/gui" % don_id, "POST", {"carrier_account_id": tk_id})
        mvd = ((kq_g.get("don") or {}).get("ma_van_don") if isinstance(kq_g, dict) else None) or mvd
        ket("G17-02b", "đơn THỬ đã gửi qua adapter mock (không phải đơn thật)",
            DAT_MOCK if (don_id and mvd and st_g == 200) else HONG,
            "đơn id=%s · mã vận đơn=%s · HTTP gửi=%s" % (don_id, mvd, st_g))
        if not mvd:
            return 1

        stub = StubHang(goc, wh_ma, secret).bat_dau()
        print("  · stub bên gửi: 127.0.0.1:%d (cổng 0, hệ điều hành cấp) — mọi callback đi qua đây"
              % stub.cong)

        def day(body, headers=None):
            return stub.day(body, headers)

        def body_hub(event, evt_id, **thua):
            d = {"event": event, "tracking_number": mvd, "event_id": evt_id,
                 "hang_luc": "2026-10-15T08:00:00+07:00"}
            d.update(thua)
            return json.dumps(d, ensure_ascii=False).encode()

        # ------------------------------------------------------------ G17-03 callback hợp lệ
        print("\n── G17-03. CALLBACK HỢP LỆ QUA STUB 127.0.0.1:0 ──────────────")
        b1 = body_hub("dang_giao", "g17-evt-1")
        st1, kq1 = day(b1)
        sk1 = kq1.get("su_kien_id") if isinstance(kq1, dict) else None
        ket("G17-03", "ĐỐI CHỨNG DƯƠNG: callback hợp lệ được nhận, phản hồi có code=1",
            DAT_MOCK if (st1 == 202 and sk1 and kq1.get("code") == 1) else HONG,
            "HTTP %s · ket_qua=%s · code=%s · su_kien_id=%s · stub đã chuyển tiếp %d lượt"
            % (st1, kq1.get("ket_qua"), kq1.get("code"), sk1, stub.so_lan_chuyen_tiep))
        if not sk1:
            return 1
        r = doi_den(sk1, ("xong", "dlq", "khong_khop"))
        ket("G17-03b", "sự kiện được xử lý tới trạng thái cuối và đơn đổi trạng thái",
            DAT if (r and r["trang_thai"] == "xong") else HONG,
            "sự kiện=%s · đơn=%s" % (r, sql("SELECT trang_thai_giao FROM don_hang WHERE id=?",
                                            (don_id,))[0]["trang_thai_giao"]))

        # ------------------------------------------------------------ G17-04..06 CHỐNG TRÙNG
        print("\n── G17-04. GỬI LẠI Y NGUYÊN 5 LẦN ⇒ ĐÚNG MỘT DÒNG ────────────")
        b2 = body_hub("lay_hang", "g17-evt-trung")
        ma_http, sk_ids, ket_qua = [], [], []
        for _ in range(5):
            stx, kqx = day(b2)
            ma_http.append(stx)
            sk_ids.append(kqx.get("su_kien_id"))
            ket_qua.append(kqx.get("ket_qua"))
        mot_dong = dem("wh_su_kien", "carrier_account_id=? AND event_id=?", (tk_id, "g17-evt-trung"))
        cung_id = len(set(sk_ids)) == 1 and sk_ids[0] is not None
        ket("G17-04", "gửi lại CÙNG sự kiện 5 lần ⇒ 1 dòng, CÙNG sk_id",
            DAT if (mot_dong == 1 and cung_id and ma_http[0] == 202
                    and all(x == 200 for x in ma_http[1:])) else HONG,
            "HTTP=%s · ket_qua=%s · sk_id=%s · số dòng trong CSDL=%d"
            % (ma_http, ket_qua, sorted(set(sk_ids)), mot_dong))

        print("\n── G17-05. NHỒI THẲNG SQL (KHÔNG QUA HÀM NGHIỆP VỤ) ──────────")
        loi = None
        try:
            ghi_thang("INSERT INTO wh_su_kien (carrier_account_id, event_id, payload_tho,"
                      " headers_json, nhan_luc) VALUES (?,?,?,?,?)",
                      (tk_id, "g17-evt-trung", b"{}", "{}", "2026-10-15 00:00:00+0700"))
        except Exception as e:                                        # noqa: BLE001
            loi = e
        sau = dem("wh_su_kien", "carrier_account_id=? AND event_id=?", (tk_id, "g17-evt-trung"))
        ket("G17-05", "câu INSERT thẳng trùng khoá bị CSDL chặn (UNIQUE ở tầng CSDL)",
            DAT if (isinstance(loi, sqlite3.IntegrityError) and sau == 1) else HONG,
            "lỗi=%s: %s · số dòng sau khi nhồi=%d · UNIQUE(carrier_account_id, event_id)"
            % (type(loi).__name__ if loi else "KHÔNG CÓ LỖI", loi, sau))

        print("\n── G17-06. ĐỐI CHỨNG ĐƯỜNG: BỎ ĐÚNG DÒNG UNIQUE THÌ SAO ─────")
        ddl = sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='wh_su_kien'")[0]["sql"]
        # Bỏ ĐÚNG dòng UNIQUE — kèm dấu phẩy đứng trước nó, nếu không thì DDL còn dấu phẩy treo
        # và bảng "đối chứng" không dựng được (đo được ở lượt chạy đầu: `near ")": syntax error`).
        ddl_hong, so_lan_thay = re.subn(r",\s*UNIQUE \(carrier_account_id, event_id\)", "",
                                        ddl)
        ddl_hong = re.sub(r"\bwh_su_kien\b", "wh_su_kien_khong_chot", ddl_hong)
        self_diff = ddl_hong != ddl and so_lan_thay == 1
        ghi_thang(ddl_hong)
        loi2 = None
        for lan in (1, 2):
            try:
                ghi_thang("INSERT INTO wh_su_kien_khong_chot (carrier_account_id, event_id,"
                          " payload_tho, headers_json, nhan_luc) VALUES (?,?,?,?,?)",
                          (tk_id, "g17-evt-trung", b"{}", "{}", "2026-10-15 00:00:00+0700"))
            except Exception as e:                                    # noqa: BLE001
                loi2 = e
        n2 = dem("wh_su_kien_khong_chot")
        ket("G17-06", "cùng câu INSERT, bảng BỎ dòng UNIQUE ⇒ 2 dòng lọt (chốt thật là CSDL)",
            DAT if (self_diff and loi2 is None and n2 == 2) else HONG,
            "DDL chỉ khác đúng dòng UNIQUE · lỗi khi nhồi=%s · số dòng=%d ⇒ nếu không có UNIQUE"
            " thì tầng nghiệp vụ KHÔNG chặn được trùng" % (loi2, n2))

        # ------------------------------------------------------------ G17-07..14 REPLAY
        print("\n── G17-07. REPLAY KHI SỰ KIỆN ĐANG ĐƯỢC XỬ LÝ ───────────────")
        ghi_thang("UPDATE wh_su_kien SET trang_thai='dang_xu_ly' WHERE id=?", (sk1,))
        truoc_tc = audit_dem("webhook_replay_tu_choi", sk1)
        truoc_ok = audit_dem("webhook_replay", sk1)
        stx, kqx = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        r = sql("SELECT trang_thai FROM wh_su_kien WHERE id=?", (sk1,))[0]
        ket("G17-07", "replay khi ĐANG XỬ LÝ ⇒ 409, trạng thái giữ nguyên, KHÔNG mất im lặng",
            DAT if (stx == 409 and r["trang_thai"] == "dang_xu_ly"
                    and audit_dem("webhook_replay_tu_choi", sk1) == truoc_tc + 1
                    and audit_dem("webhook_replay", sk1) == truoc_ok) else HONG,
            "HTTP %s · lý do=%r · trạng thái=%s · audit từ chối %d→%d · audit replay thành công=%d"
            % (stx, (kqx or {}).get("loi"), r["trang_thai"], truoc_tc,
               audit_dem("webhook_replay_tu_choi", sk1), audit_dem("webhook_replay", sk1)))
        ghi_thang("UPDATE wh_su_kien SET trang_thai='xong' WHERE id=?", (sk1,))

        print("\n── G17-08. REPLAY KHI ĐÃ XONG ────────────────────────────────")
        don_truoc = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                        (don_id,))[0]
        stx, kqx = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        r = doi_den(sk1, ("xong", "dlq", "khong_khop"))
        don_sau = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                      (don_id,))[0]
        ap_dung_0 = dem("audit", "hanh_dong='webhook_cap_nhat_don' AND chi_tiet LIKE ?"
                                 " AND chi_tiet LIKE '%%ap_dung=0%%'",
                        ("%%su_kien:%d %%" % sk1,))
        ket("G17-08", "replay khi ĐÃ XONG ⇒ 202, chạy lại THẬT, đơn KHÔNG đổi (áp lại là vô hiệu)",
            DAT if (stx == 202 and r["trang_thai"] == "xong" and don_truoc == don_sau
                    and audit_dem("webhook_replay", sk1) == 1 and ap_dung_0 >= 1) else HONG,
            "HTTP %s · sự kiện về %s · đơn %s → %s (không đổi) · audit replay=%d · lượt áp lại"
            " bị rank guard chặn (ap_dung=0) %d lần"
            % (stx, r["trang_thai"], don_truoc["trang_thai_giao"], don_sau["trang_thai_giao"],
               audit_dem("webhook_replay", sk1), ap_dung_0))

        print("\n── G17-09. REPLAY TỪ DLQ (LỖI TẠM, ĐÃ SỬA NGUYÊN NHÂN) ──────")
        b3 = body_hub("dang_giao", "g17-evt-dlq-tam", demo_force_fail=True)
        stx, kqx = day(b3)
        sk_tam = kqx.get("su_kien_id")
        r = doi_den(sk_tam, ("dlq",), toi_da=100)
        truoc = r
        # Sửa NGUYÊN NHÂN (payload thôi hỏng) rồi mới replay — đúng việc người vận hành làm.
        ghi_thang("UPDATE wh_su_kien SET payload_tho=? WHERE id=?",
                  (body_hub("dang_giao", "g17-evt-dlq-tam"), sk_tam))
        stx2, kqx2 = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk_tam, "POST", {})
        r2 = doi_den(sk_tam, ("xong", "khong_khop"))
        don_sau = sql("SELECT trang_thai_giao FROM don_hang WHERE id=?", (don_id,))[0]
        ket("G17-09", "replay từ DLQ sau khi sửa nguyên nhân ⇒ 202 và chạy lại THÀNH CÔNG",
            DAT if (r["trang_thai"] == "dlq" and stx2 == 202 and r2["trang_thai"] == "xong"
                    and r2["so_lan_thu"] == 0
                    and don_sau["trang_thai_giao"] == "dang_giao") else HONG,
            "trước: %s (thử %d lần) · replay HTTP %s · sau: %s (so_lan_thu=%d) · đơn=%s"
            % (truoc["trang_thai"], truoc["so_lan_thu"], stx2, r2["trang_thai"],
               r2["so_lan_thu"], don_sau["trang_thai_giao"]))

        print("\n── G17-10. REPLAY TỪ DLQ (LỖI VĨNH VIỄN) ────────────────────")
        stx, kqx = day(b"khong-phai-json-cua-dang-nao")     # ký hợp lệ, nội dung không đọc được
        sk_vv = kqx.get("su_kien_id")
        r = doi_den(sk_vv, ("dlq",), toi_da=50)
        truoc_dlq = dem("audit", "hanh_dong='webhook_dlq' AND resource_id=?", (str(sk_vv),))
        stx2, kqx2 = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk_vv, "POST", {})
        r2 = doi_den(sk_vv, ("dlq",), toi_da=50)
        sau_dlq = dem("audit", "hanh_dong='webhook_dlq' AND resource_id=?", (str(sk_vv),))
        ket("G17-10", "replay từ DLQ lỗi VĨNH VIỄN ⇒ 202 rồi về DLQ ngay, KHÔNG đốt lượt thử",
            DAT if (r["trang_thai"] == "dlq" and r["so_lan_thu"] == 0 and stx2 == 202
                    and r2["trang_thai"] == "dlq" and r2["so_lan_thu"] == 0
                    and sau_dlq > truoc_dlq) else HONG,
            "trước: %s (thử %d) · replay HTTP %s · sau: %s (thử %d) · audit DLQ %d→%d"
            % (r["trang_thai"], r["so_lan_thu"], stx2, r2["trang_thai"], r2["so_lan_thu"],
               truoc_dlq, sau_dlq))

        print("\n── G17-11. REPLAY KHÔNG UỶ QUYỀN (TENANT_VIEWER) ────────────")
        st_v, kq_v = k_a.goi("/api/v2/memberships", "POST",
                             {"ten_dang_nhap": "g17-viewer-a", "mat_khau": "g17-viewer-a-123",
                              "role": "TENANT_VIEWER"})
        k_v = Khach(goc)
        st_dn, _ = k_v.goi("/api/v2/auth/dang-nhap", "POST",
                           {"ten_dang_nhap": "g17-viewer-a", "mat_khau": "g17-viewer-a-123"})
        truoc_ok = audit_dem("webhook_replay", sk1)
        truoc_tt = sql("SELECT trang_thai FROM wh_su_kien WHERE id=?", (sk1,))[0]["trang_thai"]
        stx, kqx = k_v.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        sau_tt = sql("SELECT trang_thai FROM wh_su_kien WHERE id=?", (sk1,))[0]["trang_thai"]
        audit_quyen = dem("audit", "hanh_dong='tu_choi_quyen' AND doi_tuong=?",
                          ("permission:tenant.webhook.replay",))
        # ĐỐI CHỨNG DƯƠNG: cùng người đó ĐỌC được sự kiện (thiếu quyền GHI, không thiếu quyền XEM)
        st_xem, _ = k_v.goi("/api/v2/webhook/su-kien")
        ket("G17-11", "replay KHÔNG UỶ QUYỀN ⇒ 403, không đổi gì, có audit từ chối quyền",
            DAT if (st_v == 201 and st_dn == 200 and stx == 403 and sau_tt == truoc_tt
                    and audit_dem("webhook_replay", sk1) == truoc_ok and audit_quyen >= 1
                    and st_xem == 200) else HONG,
            "thêm viewer HTTP %s · đăng nhập HTTP %s · replay HTTP %s · trạng thái %s→%s · audit"
            " replay thành công=%d (không tăng) · audit tu_choi_quyen=%d · viewer ĐỌC được (HTTP %s)"
            % (st_v, st_dn, stx, truoc_tt, sau_tt, audit_dem("webhook_replay", sk1),
               audit_quyen, st_xem))

        print("\n── G17-12. REPLAY CÓ UỶ QUYỀN (TENANT_OWNER) ────────────────")
        stx, kqx = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        r = doi_den(sk1, ("xong", "dlq", "khong_khop"))
        ket("G17-12", "replay CÓ UỶ QUYỀN ⇒ 202 và chạy lại", DAT if (stx == 202) else HONG,
            "HTTP %s · audit replay thành công=%d · trạng thái sau=%s"
            % (stx, audit_dem("webhook_replay", sk1), r["trang_thai"]))

        print("\n── G17-13. REPLAY CHÉO TENANT ────────────────────────────────")
        stx, kqx = k_b.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        st_doi, _ = k_b.goi("/api/v2/webhook/su-kien/%d/replay" % 999999, "POST", {})
        ket("G17-13", "tenant B replay sự kiện của A ⇒ 404 giống hệt ID không tồn tại (không dò được)",
            DAT if (stx == 404 and st_doi == 404) else HONG,
            "sự kiện của A: HTTP %s · ID không tồn tại: HTTP %s" % (stx, st_doi))

        print("\n── G17-14. TRẦN REPLAY ───────────────────────────────────────")
        so_lan, ma_ds = audit_dem("webhook_replay", sk1), []
        while so_lan < wh.REPLAY_TOI_DA:
            stx, _ = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
            ma_ds.append(stx)
            so_lan = audit_dem("webhook_replay", sk1)
            if stx != 202:
                break
            doi_den(sk1, ("xong", "dlq", "khong_khop"))
        stx_cuoi, kqx_cuoi = k_a.goi("/api/v2/webhook/su-kien/%d/replay" % sk1, "POST", {})
        ket("G17-14", "replay có TRẦN: đủ %d lượt thì lượt sau bị 409" % wh.REPLAY_TOI_DA,
            DAT if (so_lan == wh.REPLAY_TOI_DA and stx_cuoi == 409) else HONG,
            "các lượt tới trần: %s · lượt vượt trần HTTP %s (%s) · số lượt replay đã ghi=%d/%d"
            % (ma_ds, stx_cuoi, (kqx_cuoi or {}).get("loi"), so_lan, wh.REPLAY_TOI_DA))

        # ------------------------------------------------------------ G17-15 SANDBOX: BLOCKED
        print("\n── G17-15. CHẶNG CHẠM HÃNG (SANDBOX) ─────────────────────────")
        import adapter_jt
        cong_sb = bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True))
        cong_pr = bool(getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True))
        duoc_sb = adapter_jt.moi_truong_duoc_chay("sandbox")
        # Phán quyết dựng ở hàm RIÊNG (`phan_quyet_sandbox`) để bộ thử đơn vị gọi được mà không
        # phải spawn máy chủ — một phán quyết chỉ kiểm được bằng cách chạy cả harness thì lượt
        # sau không ai kiểm nữa.
        pq = phan_quyet_sandbox(cong_sb, cong_pr, duoc_sb)
        ket("G17-SANDBOX", "GỬI SANG J&T SANDBOX + CALLBACK THEO SƠ ĐỒ CỦA HÃNG",
            pq["trang_thai"], pq["bang_chung"])
        # Cổng phải THẬT SỰ đóng ở cả hai nguồn — nếu không thì "BLOCKED" chỉ là câu chữ.
        ket("G17-15b", "hai cổng chạm hãng ĐÓNG ở cả `cau_hinh` lẫn hàm dẫn xuất của adapter",
            DAT if (not cong_sb and not cong_pr and not duoc_sb) else HONG,
            "SANDBOX=%s · PRODUCTION=%s · moi_truong_duoc_chay(sandbox)=%s"
            % (cong_sb, cong_pr, duoc_sb))
        # Và không lượt nào của harness này chạm tới hãng: stub chỉ nói chuyện với loopback.
        host_stub = urllib.parse.urlparse(goc).hostname
        ket("G17-15c", "mọi phép đo HTTP của lượt này đi qua loopback (stub cổng 0)",
            DAT if (host_stub in ("127.0.0.1", "localhost", "::1")
                    and stub.so_lan_chuyen_tiep >= 8) else HONG,
            "máy chủ=%s · stub=127.0.0.1:%d · số callback stub đã chuyển tiếp=%d"
            % (goc, stub.cong, stub.so_lan_chuyen_tiep))

        # ------------------------------------------------------------ G17-16 bảng phủ
        print("\n── G17-16. BẢNG PHỦ NHÁNH REPLAY ─────────────────────────────")
        co = {x["ma"] for x in BUOC}
        can = {"đang xử lý": "G17-07", "đã xong": "G17-08", "DLQ (lỗi tạm)": "G17-09",
               "DLQ (lỗi vĩnh viễn)": "G17-10", "không uỷ quyền": "G17-11",
               "có uỷ quyền": "G17-12", "chéo tenant": "G17-13", "vượt trần": "G17-14",
               "chống trùng tầng CSDL": "G17-05", "đối chứng bỏ UNIQUE": "G17-06",
               "chặng chạm hãng": "G17-SANDBOX"}
        thieu = {k: v for k, v in can.items() if v not in co}
        ket("G17-16", "bảng phủ: MỌI nhánh replay + chống trùng đều có chặng THẬT",
            DAT if (not thieu and len(co) >= 15) else HONG,
            "thiếu=%s · số chặng đã chạy=%d" % (thieu or "không", len(co)))

        # ------------------------------------------------------------ tổng kết
        dem_tt = dem_phuong_an(BUOC)
        print("\n" + "═" * 78)
        print("TỔNG KẾT: đạt %d · ĐẠT (MOCK) %d · hỏng %d · BLOCKED %d · bỏ qua %d"
              % (dem_tt[DAT], dem_tt[DAT_MOCK], dem_tt[HONG], dem_tt[BLOCKED], dem_tt[BO_QUA]))
        print("BLOCKED — KHÔNG được tính là đạt:")
        for x in BUOC:
            if x["trang_thai"] == BLOCKED:
                print("  ⊘ [%s] %s" % (x["ma"], x["ten"]))
                print("      %s" % x["bang_chung"])
        print("ĐẠT (MOCK): chặn bởi (nền tạm · adapter mock · tự ký cục bộ) — không phải bằng chứng"
              " với hãng thật.")
        bao_cao = {
            "goc": "G17-AG04-WEBHOOK", "nen": nen, "pid_may_chu": sv.pid, "dia_chi": goc,
            "stub": {"dia_chi": "127.0.0.1:%d" % stub.cong, "so_lan_chuyen_tiep":
                     stub.so_lan_chuyen_tiep},
            "moi_truong_van_chuyen": chot_an_toan.bao_cao_moi_truong(),
            "buoc": BUOC, "dem": dem_tt,
            "blocked": [{"ma": x["ma"], "ten": x["ten"], "thieu": x["bang_chung"]}
                        for x in BUOC if x["trang_thai"] == BLOCKED],
            "pham_vi": {
                "trong": ["đăng nhập · tenant A/B · tài khoản J&T mock · đơn thử · callback hub_hmac"
                          " qua STUB 127.0.0.1:0 · chống trùng (HTTP + SQL thẳng) · replay: đang xử"
                          " lý / đã xong / DLQ tạm / DLQ vĩnh viễn / chéo tenant / không uỷ quyền /"
                          " có uỷ quyền / vượt trần"],
                "ngoai": ["J&T sandbox thật", "callback theo sơ đồ jt_digest của hãng", "TLS thật",
                          "tunnel/VPS", "deploy", "PostgreSQL", "nhiều tiến trình", "dữ liệu thật"],
            },
            "ket_luan": ("MOCK ĐẠT ở các chặng không chạm hãng; chặng chạm hãng là BLOCKED kèm đúng"
                         " giấy phép còn thiếu và KHÔNG được tính là đạt."),
        }
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(bao_cao, f, ensure_ascii=False, indent=2)
            print("báo cáo JSON: %s" % a.json)
        return 0 if dem_tt[HONG] == 0 else 1
    finally:
        if stub is not None:
            stub.dung()
        if sv is not None:
            sv.terminate()
            try:
                sv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                sv.kill()
            print("\n[dọn] đã tắt máy chủ pid %d theo ĐÚNG PID (không dọn theo tên tiến trình)"
                  % sv.pid)
        if not a.giu_nen and os.environ.get("VIP_HUB_DATA") != nen:
            shutil.rmtree(nen, ignore_errors=True)
            print("[dọn] đã xoá nền %s" % nen)
        elif a.giu_nen:
            print("[dọn] --giu-nen: giữ %s" % nen)


if __name__ == "__main__":
    sys.exit(main())
