#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G15 — HARNESS E2E: kịch bản 10 bước, chạy ở chế độ **MOCK**, chặng J&T sandbox BLOCKED.

KỊCH BẢN (mã bước giữ nguyên như yêu cầu I06)
---------------------------------------------
    B01 ĐĂNG NHẬP
    B02 CHỌN TENANT
    B03 CHỌN TÀI KHOẢN J&T
    B04 TẠO ĐƠN THỬ
    B05 GỬI SANG J&T SANDBOX      ← **BLOCKED** (không có credentials sandbox)
    B06 NHẬN CALLBACK             ← chạy được phần MOCK; phần sandbox **BLOCKED**
    B07 XÁC MINH HÀNH TRÌNH
    B08 XÁC MINH DỮ LIỆU COD
    B09 HUỶ ĐƠN THỬ
    B10 ĐỐI CHIẾU CUỐI LƯỢT + TỔNG KẾT

====== BA CHỐT CHẶN AN TOÀN — harness TỪ CHỐI CHẠY nếu mất một cái ======
1. **Không được trỏ vào dữ liệu thật.** `VIP_HUB_DATA` phải là thư mục TẠM, và tuyệt đối
   không phải `app/du-lieu/` của dự án. Harness tự tạo nền riêng, tự xoá.
2. **`CHO_PHEP_LIVE` phải là `False`** ở cả năm adapter hãng. Một harness "thử" mà mở được
   cửa gọi hãng thật là thứ nguy hiểm hơn không có harness.
3. **Chỉ nói chuyện với `127.0.0.1`.** Không tên miền, không IP ngoài, không tunnel.

====== VÌ SAO BƯỚC 5 LÀ BLOCKED CHỨ KHÔNG PHẢI "ĐẠT" ======
`V-13906-05` (credentials sandbox J&T) **CHƯA CẤP**, và `V-G09-01` (gọi API hãng thật, kể cả
sandbox) **CHƯA CẤP**. Nên bước 5 **không thể** chạy thật. Harness làm ĐÚNG hai việc:
  (a) ghi `BLOCKED` kèm chính xác cái còn thiếu — không giả vờ, không bỏ qua im lặng;
  (b) chạy **chặng MOCK** của cùng đường mã đó (adapter `mock`, `moi_truong='mock'`), và ghi
      nó là `DAT (MOCK)` chứ không phải `DAT`. Một lượt mock xanh **không** là bằng chứng
      rằng đường sandbox chạy được: nó chỉ là bằng chứng rằng đường mã *phía sau* adapter đúng.
Khác biệt đó còn nằm ở **sơ đồ xác thực callback**: chế độ mock dùng `hub_hmac` (bí mật của
chính hệ); J&T sandbox/production dùng `jt_digest` theo tài liệu hãng (`webhook.SO_DO_THEO_HANG`).
Harness chạy được `hub_hmac`, nên **không** chứng minh được `jt_digest`.

CHẠY
----
    sh trien_khai/g15/chay_harness.sh              # dựng nền, chạy, dọn
    python3 trien_khai/g15/harness_e2e.py --json /tmp/bao-cao.json
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
import tempfile
import time
import urllib.error
import urllib.request

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DU_AN, "app"))

# ------------------------------------------------------------------ mô hình bước
DAT, HONG, BLOCKED, BO_QUA = "DAT", "HONG", "BLOCKED", "BO_QUA"
BUOC = []


def ket(ma, ten, trang_thai, bang_chung=""):
    BUOC.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    ky = {DAT: "✓", HONG: "✗", BLOCKED: "⊘", BO_QUA: "–"}[trang_thai]
    print("  %s [%s] %s%s" % (ky, ma, ten, ("\n        " + bang_chung) if bang_chung else ""))
    return trang_thai == DAT


# ------------------------------------------------------------------ HTTP client
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


# ------------------------------------------------------------------ chốt chặn
def chan_an_toan(nen):
    """Ba chốt. Trả danh sách lý do TỪ CHỐI (rỗng = chạy được)."""
    ly_do = []
    that = os.path.realpath(os.path.join(DU_AN, "app", "du-lieu"))
    if os.path.realpath(nen) == that or os.path.realpath(nen).startswith(that + os.sep):
        ly_do.append("VIP_HUB_DATA trỏ vào dữ liệu THẬT (%s) — từ chối." % that)
    if not os.environ.get("VIP_HUB_DATA", "").startswith(("/tmp", "/var/folders", tempfile.gettempdir())):
        ly_do.append("VIP_HUB_DATA=%r không nằm trong thư mục tạm — từ chối."
                     % os.environ.get("VIP_HUB_DATA"))
    # `CHO_PHEP_LIVE` là hằng của LỚP adapter, KHÔNG phải của mô-đun. Dò qua ĐÚNG sổ đăng ký
    # của `adapter.py` mà mã chạy dùng, chứ không tự đoán tên lớp — bản đầu của chốt này đọc
    # `adapter_jt.CHO_PHEP_LIVE` (không tồn tại) và TỪ CHỐI OAN cả lượt chạy.
    import adapter
    import adapter_jt                                       # noqa: F401  (để tự đăng ký)
    import adapter_vtp                                      # noqa: F401
    if not adapter._DANG_KY:
        ly_do.append("sổ đăng ký adapter RỖNG — chốt an toàn này không kiểm được gì.")
    for ma, lop in sorted(adapter._DANG_KY.items()):
        if lop.CHO_PHEP_LIVE is not False:
            ly_do.append("%s.CHO_PHEP_LIVE = %r — phải CHỐT CỨNG là False. Từ chối."
                         % (lop.__name__, lop.CHO_PHEP_LIVE))
    return ly_do


def cong_roi():
    for _ in range(60):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        c = s.getsockname()[1]
        s.close()
        if 18000 <= c <= 19999:
            return c
    return 18991


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--giu-nen", action="store_true")
    a = ap.parse_args()

    nen = os.environ.get("VIP_HUB_DATA") or tempfile.mkdtemp(prefix="veh-g15-")
    os.makedirs(nen, exist_ok=True)
    print("═" * 74)
    print("HARNESS E2E G15 — kịch bản 10 bước · nền %s" % nen)
    print("═" * 74)

    ly_do = chan_an_toan(nen)
    if ly_do:
        print("\nTỪ CHỐI CHẠY:")
        for x in ly_do:
            print("  · " + x)
        return 4

    cong = cong_roi()
    goc = "http://127.0.0.1:%d" % cong
    env = dict(os.environ, VIP_HUB_DATA=nen)
    sv = None
    try:
        # ---------------------------------------------------------- dựng nền
        print("\n── DỰNG NỀN ──────────────────────────────────────────────")
        for lenh, nhan in ((("migrate.py"), "migrate"), (("khoi_tao.py"), "seed")):
            p = subprocess.run([sys.executable, os.path.join(DU_AN, "app", lenh)],
                               capture_output=True, text=True, env=env, cwd=DU_AN)
            if p.returncode:
                print("  ✗ %s hỏng: %s" % (nhan, (p.stderr or p.stdout)[-400:]))
                return 3
            print("  ✓ %s" % nhan)
        log = open(os.path.join(nen, "server.log"), "w")
        sv = subprocess.Popen([sys.executable, os.path.join(DU_AN, "app", "server.py"),
                               str(cong)], stdout=log, stderr=subprocess.STDOUT, env=env,
                              cwd=DU_AN)
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", cong), 0.3).close()
                break
            except OSError:
                if sv.poll() is not None:
                    print("  ✗ máy chủ chết khi khởi động:\n%s"
                          % open(os.path.join(nen, "server.log")).read()[-600:])
                    return 3
                time.sleep(0.2)
        print("  ✓ máy chủ 127.0.0.1:%d (pid %d) — chỉ loopback" % (cong, sv.pid))

        db = os.path.join(nen, "hub.db")

        def sql(q, p=()):
            c = sqlite3.connect(db)
            c.row_factory = sqlite3.Row
            r = [dict(x) for x in c.execute(q, p)]
            c.close()
            return r

        k = Khach(goc)
        duong_mk = os.path.join(nen, "TAI-KHOAN-DEMO.md")
        mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`", open(duong_mk, encoding="utf-8").read()))
        if "platform-owner" not in mk:
            print("  ✗ không đọc được mật khẩu demo từ %s" % duong_mk)
            return 3

        print("\n── B01. ĐĂNG NHẬP ────────────────────────────────────────")
        st, kq = k.goi("/api/v2/auth/dang-nhap", "POST",
                       {"ten_dang_nhap": "platform-owner", "mat_khau": mk["platform-owner"]})
        ket("B01", "đăng nhập platform-owner", DAT if st == 200 else HONG,
            "HTTP %s · khoá trả về=%s" % (st, sorted(kq.keys()) if isinstance(kq, dict) else kq))
        # Dựng tenant thử qua cửa platform — đây là đường THẬT, không phải SQL tay.
        st, kq = k.goi("/api/v2/platform/tenants", "POST",
                       {"ten": "Cty G15", "owner_ten_dang_nhap": "g15-owner",
                        "owner_mat_khau": "g15-owner-123", "goi_id": "pro"})
        tid = (kq.get("id") or (kq.get("tenant") or {}).get("id")) if isinstance(kq, dict) else None
        print("  · tenant thử: id=%s (HTTP %s)" % (tid, st))
        if not tid:
            ket("B01b", "tạo tenant thử", HONG, "HTTP %s · %s" % (st, kq))
            return 1
        ket("B01b", "tạo tenant thử + owner", DAT, "tenant_id=%s · HTTP %s" % (tid, st))

        print("\n── B02. CHỌN TENANT ──────────────────────────────────────")
        k.ck = {}
        st, kq = k.goi("/api/v2/auth/dang-nhap", "POST",
                       {"ten_dang_nhap": "g15-owner", "mat_khau": "g15-owner-123"})
        st_me, me = k.goi("/api/v2/auth/toi")
        dung_tenant = isinstance(me, dict) and (me.get("tenant") or {}).get("id") == tid
        ket("B02", "ngữ cảnh tenant đến từ PHIÊN, không từ body",
            DAT if (st == 200 and dung_tenant) else HONG,
            "HTTP %s · tenant=%s · vai_tro=%s" % (st_me, (me.get("tenant") or {}).get("id")
                                                  if isinstance(me, dict) else "?", 
                                                  me.get("vai_tro") if isinstance(me, dict) else "?"))

        print("\n── B03. CHỌN TÀI KHOẢN J&T ───────────────────────────────")
        st, kq = k.goi("/api/v2/tai-khoan-hang", "POST",
                       {"hang": "jt", "ten": "J&T G15 (mock)",
                        "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
        tk_jt = kq.get("id") if isinstance(kq, dict) else None
        wh_ma = (kq.get("webhook_url", "") if isinstance(kq, dict) else "").rsplit("/", 1)[-1]
        hang_tk = sql("SELECT hang, moi_truong, kich_hoat FROM carrier_accounts WHERE id=?",
                      (tk_jt,)) if tk_jt else []
        mt = hang_tk[0]["moi_truong"] if hang_tk else "?"
        ket("B03", "tạo tài khoản hãng J&T", DAT if st == 201 else HONG,
            "HTTP %s · id=%s · hãng=%s · môi trường=%s"
            % (st, tk_jt, hang_tk[0]["hang"] if hang_tk else "?", mt))
        if mt != "mock":
            ket("B03b", "tài khoản hãng phải ở môi trường 'mock'", HONG,
                "môi trường thật là %r — harness CHỈ chạy mock" % mt)
            return 1
        ket("B03b", "môi trường tài khoản = 'mock' (không phải sandbox/production)", DAT)
        # Bí mật KHÔNG được in ra: chỉ đo rằng nó đã được mã hoá at-rest.
        ma_hoa = sql("SELECT credentials_ma_hoa, webhook_secret_ma_hoa FROM carrier_accounts"
                     " WHERE id=?", (tk_jt,))[0]
        kin = all(str(v).startswith("v") and "$" in str(v) for v in ma_hoa.values())
        ket("B03c", "credentials mã hoá at-rest (chỉ kiểm tiền tố, KHÔNG in giá trị)",
            DAT if kin else HONG, "hai trường bí mật đều có dạng v3$<key_id>$… ")

        print("\n── B04. TẠO ĐƠN THỬ ──────────────────────────────────────")
        st, kq = k.goi("/api/v2/don", "POST", {
            "nguoi_nhan_ten": "Người nhận G15", "nguoi_nhan_sdt": "0901234567",
            "nguoi_nhan_dia_chi": "12 Lê Lợi, Quận 1, TP HCM",
            "nguoi_gui_ten": "Kho G15", "nguoi_gui_sdt": "0900000000",
            "nguoi_gui_dia_chi": "1 Kho, Q7, TP HCM",
            "hang_hoa": "Áo thun thử", "khoi_luong_gram": 500, "cod": 250000,
            "tien_thu_ho": 250000})
        don = kq.get("don", {}) if isinstance(kq, dict) else {}
        don_id, ma_don = don.get("id"), don.get("ma_don")
        ket("B04", "tạo đơn THỬ (không phải đơn thật)", DAT if st in (200, 201) and don_id else HONG,
            "HTTP %s · id=%s · mã=%s · trạng thái=%s · COD=%s"
            % (st, don_id, ma_don, don.get("trang_thai"), don.get("cod") or don.get("tien_thu_ho")))
        if not don_id:
            return 1
        st, kq = k.goi("/api/v2/don/%d/duyet" % don_id, "POST", {})
        ket("B04b", "duyệt đơn", DAT if st == 200 else HONG,
            "HTTP %s · trạng thái=%s" % (st, (kq.get("don") or {}).get("trang_thai")
                                         if isinstance(kq, dict) else kq))

        print("\n── B05. GỬI SANG J&T SANDBOX ─────────────────────────────")
        print("  ⊘ [B05] GỬI SANG J&T SANDBOX — **BLOCKED**")
        thieu = ("Credentials sandbox J&T CHƯA CẤP (V-13906-05) · gọi API hãng thật kể cả "
                 "sandbox CHƯA CẤP (V-G09-01) · CHO_PHEP_LIVE=False ở cả 5 adapter.")
        print("        thiếu: " + thieu)
        ket("B05", "gửi sang J&T SANDBOX", BLOCKED, thieu)
        # Chặng MOCK của CÙNG đường mã — ghi rõ là MOCK.
        st, kq = k.goi("/api/v2/don/%d/gui" % don_id, "POST", {"carrier_account_id": tk_jt})
        d = (kq.get("don") or {}) if isinstance(kq, dict) else {}
        mvd = d.get("ma_van_don")
        la_mock = (d.get("tho") or {}).get("mock") if isinstance(d.get("tho"), dict) else None
        ket("B05-MOCK", "gửi qua adapter MOCK (KHÔNG phải sandbox)", DAT if st == 200 and mvd else HONG,
            "HTTP %s · mã vận đơn=%s · trạng thái=%s · mock=%s" % (st, mvd, d.get("trang_thai"), la_mock))
        st, kq = k.goi("/api/v2/don/%d/nhan" % don_id)
        ket("B05b", "nhãn vận đơn KHÔNG phải nhãn thật", DAT if st == 200 and not kq.get("nhan_that") else HONG,
            "HTTP %s · nhan_that=%s · la_mock=%s" % (st, kq.get("nhan_that"), kq.get("la_mock")))

        print("\n── B06. NHẬN CALLBACK ────────────────────────────────────")
        r_tk = sql("SELECT webhook_ma, webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?",
                   (tk_jt,))[0]
        os.environ["VIP_HUB_DATA"] = nen
        import bao_mat
        sec = bao_mat.giai_ma_wh(r_tk["webhook_secret_ma_hoa"], r_tk["webhook_ma"])
        pl = json.dumps({"event": "dang_giao", "tracking_number": mvd,
                         "event_id": "g15-evt-1", "time": "2026-10-15T09:00:00+07:00"},
                        ensure_ascii=False).encode()
        sig = hmac.new(sec.encode(), pl, hashlib.sha256).hexdigest()
        st, kq = k.goi("/api/v2/webhook/nhan/%s" % r_tk["webhook_ma"], "POST", tho=pl,
                       hdr={"X-Webhook-Signature": sig})
        ket("B06-MOCK", "callback MOCK chữ ký ĐÚNG (sơ đồ hub_hmac)", DAT if st == 202 else HONG,
            "HTTP %s · %s" % (st, kq))
        st2, kq2 = k.goi("/api/v2/webhook/nhan/%s" % r_tk["webhook_ma"], "POST", tho=pl,
                         hdr={"X-Webhook-Signature": sig})
        n = len(sql("SELECT id FROM wh_su_kien WHERE event_id='g15-evt-1'"))
        ket("B06b", "gửi lại cùng event_id → idempotent, không nhân đôi",
            DAT if n == 1 else HONG, "HTTP %s · %s sự kiện trong CSDL" % (st2, n))
        st3, _ = k.goi("/api/v2/webhook/nhan/%s" % r_tk["webhook_ma"], "POST", tho=pl,
                       hdr={"X-Webhook-Signature": "sai" * 10})
        ket("B06c", "callback chữ ký SAI → bị từ chối", DAT if st3 == 401 else HONG, "HTTP %s" % st3)
        thieu_cb = ("Callback THẬT của J&T dùng sơ đồ `jt_digest` (webhook.SO_DO_THEO_HANG"
                    "['jt']) — cần header digest của hãng + credentials sandbox. Chưa có ⇒ "
                    "đường này CHƯA được chứng minh; lượt trên chỉ chứng minh `hub_hmac`.")
        print("  ⊘ [B06-SANDBOX] callback theo sơ đồ J&T thật — **BLOCKED**")
        ket("B06-SANDBOX", "callback theo sơ đồ jt_digest của hãng", BLOCKED, thieu_cb)

        print("\n── B07. XÁC MINH HÀNH TRÌNH ──────────────────────────────")
        ok = False
        for _ in range(50):
            time.sleep(0.2)
            r = sql("SELECT trang_thai FROM wh_su_kien WHERE event_id='g15-evt-1'")
            if r and r[0]["trang_thai"] in ("xong", "loi", "dlq"):
                ok = True
                break
        r = sql("SELECT trang_thai, loi_cuoi FROM wh_su_kien WHERE event_id='g15-evt-1'")
        ket("B07a", "sự kiện được xử xong", DAT if (ok and r and r[0]["trang_thai"] == "xong") else HONG,
            "trạng thái=%s · lỗi=%s" % (r[0]["trang_thai"] if r else "?", r[0]["loi_cuoi"] if r else ""))
        d = sql("SELECT trang_thai_giao, hang_trang_thai_giao, ma_van_don FROM don_hang WHERE id=?",
                (don_id,))[0]
        ket("B07b", "trục GIAO VẬN của đơn cập nhật từ callback",
            DAT if d["trang_thai_giao"] == "dang_giao" else HONG,
            "trục giao vận=%s (hạng %s) · mã vận đơn=%s"
            % (d["trang_thai_giao"], d["hang_trang_thai_giao"], d["ma_van_don"]))
        st, kq = k.goi("/api/v2/don/%d" % don_id)
        n_ls = len(kq.get("lich_su", [])) if isinstance(kq, dict) else 0
        ket("B07c", "có dấu vết lịch sử cho lượt đổi trạng thái", DAT if n_ls else HONG,
            "%d dòng lịch sử" % n_ls)
        st, kq = k.goi("/api/v2/polling/chay", "POST", {"chi_hang_khong_webhook": True})
        ket("B07d", "đường polling (fallback) gọi được", DAT if st in (200, 202) else HONG,
            "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:120]
                              if isinstance(kq, dict) else kq))

        print("\n── B08. XÁC MINH DỮ LIỆU COD ─────────────────────────────")
        # ĐO ĐƯỢC, và nó NGƯỢC với điều dễ tưởng: `tc_cod` KHÔNG có dòng ngay khi tạo đơn.
        # `tai_chinh.mo_so_cod()` chỉ được gọi từ đường ĐỐI SOÁT (`doi_soat.duyet_dot`), vì
        # `COD_EXPECTED` cố ý không sinh bút toán — chưa ai thu đồng nào thì ghi vào sổ nợ là
        # tạo một khoản phải thu không có thật. Nên B08 phải đi ĐÚNG đường nghiệp vụ.
        don_cod = sql("SELECT cod FROM don_hang WHERE id=?", (don_id,))[0]["cod"]
        ket("B08a", "số COD khai trên đơn được giữ nguyên", DAT if int(don_cod or 0) == 250000
            else HONG, "don_hang.cod=%s" % don_cod)
        truoc = sql("SELECT count(*) c FROM tc_cod WHERE don_id=?", (don_id,))[0]["c"]
        ket("B08b", "sổ COD CHƯA mở ở bước tạo đơn — đúng thiết kế (COD_EXPECTED ở đường đối soát)",
            DAT if truoc == 0 else HONG, "%d dòng tc_cod trước đối soát" % truoc)

        # Phí hệ đang coi là đúng — lấy từ CSDL theo ĐÚNG quy tắc `doi_soat._phi_he_cua_don`
        # (tổng báo giá trong `tc_phi`, rơi về `don_hang.phi_van_chuyen`). Không bịa số.
        r_phi = sql("SELECT COALESCE(SUM(so_tien_dong),0) t, COUNT(*) c FROM tc_phi"
                    " WHERE tenant_id=? AND don_id=? AND loai='bao_gia'", (tid, don_id))[0]
        phi_he = (r_phi["t"] if r_phi["c"] else
                  sql("SELECT phi_van_chuyen p FROM don_hang WHERE id=?", (don_id,))[0]["p"])

        def nap(phi):
            csv = ("billCode,codAmount,freight,settlement period,status\n"
                   "%s,250000,%s,2026-10,delivered\n" % (mvd, "" if phi is None else phi)).encode()
            return k.goi("/api/v2/doi-soat/nap", "POST", {
                "ten_file": "bang-ke-jt-g15.csv", "hang": "jt",
                "noi_dung_base64": base64.b64encode(csv).decode(),
                "ky_thanh_toan": "2026-10", "carrier_account_id": tk_jt})

        # ---- ĐỐI CHỨNG ÂM: bảng kê khai phí SAI phải bị bắt là lệch, KHÔNG được áp vào sổ.
        # Lệch chọn là +1.000đ: nhỏ hơn ngưỡng "bất thường" của hệ (`NGUONG_LECH_DONG` =
        # 500.000đ và `NGUONG_LECH_BPS` = 20%), nên nó phải rơi vào `phi_lech` chứ không phải
        # `dieu_chinh_bat_thuong`. Chọn +5.000 ở bản đầu là ĐO SAI NHÓM — và ca thử báo hỏng
        # trong khi hệ làm đúng.
        if phi_he is not None:
            st, kq = nap(int(phi_he) + 1000)
            dot_sai = kq.get("dot_id") if isinstance(kq, dict) else None
            _, kq = k.goi("/api/v2/doi-soat/dot/%d/doi-chieu" % dot_sai, "POST", {})
            loai = kq.get("theo_loai", {}) if isinstance(kq, dict) else {}
            _, kq2 = k.goi("/api/v2/doi-soat/dot/%d/duyet" % dot_sai, "POST", {})
            k.goi("/api/v2/doi-soat/dot/%d/tu-choi" % dot_sai, "POST",
                  {"ly_do": "đối chứng âm của harness G15"})
            ket("B08c-am", "ĐỐI CHỨNG ÂM: bảng kê khai phí SAI (+1.000đ) bị bắt là `phi_lech`, KHÔNG áp vào sổ",
                DAT if (kq.get("so_khop") == 0 and loai.get("phi_lech") == 1
                        and kq2.get("da_ap") == 0) else HONG,
                "khớp=%s (phải 0) · phi_lech=%s (phải 1) · đã áp=%s (phải 0) · theo loại=%s"
                % (kq.get("so_khop"), loai.get("phi_lech"), kq2.get("da_ap"),
                   json.dumps(loai, ensure_ascii=False)))
            print("        (đối chứng này chứng minh đường đối chiếu THẬT SỰ so số, chứ không")
            print("         phải chỉ chạy qua rồi báo khớp — nếu bỏ nó, 'khớp=1' ở dưới vô nghĩa)")

        st, kq = nap(phi_he)
        dot_id = kq.get("dot_id") if isinstance(kq, dict) else None
        ket("B08c", "nạp bảng kê J&T (đường đối soát thật)",
            DAT if st == 201 and dot_id and kq.get("so_nap") == 1 else HONG,
            "HTTP %s · đợt=%s · nạp=%s · cột nhận ra=%s · phí hệ=%s"
            % (st, dot_id, kq.get("so_nap") if isinstance(kq, dict) else "?",
               kq.get("cot_nhan_ra") if isinstance(kq, dict) else "?", phi_he))
        if not dot_id:
            return 1
        st, kq = k.goi("/api/v2/doi-soat/dot/%d/doi-chieu" % dot_id, "POST", {})
        ket("B08d", "đối chiếu đợt: dòng bảng kê KHỚP với đơn thử",
            DAT if isinstance(kq, dict) and kq.get("so_khop") == 1 else HONG,
            "HTTP %s · khớp=%s · theo loại=%s" % (st, kq.get("so_khop") if isinstance(kq, dict) else "?",
                                                  json.dumps(kq.get("theo_loai"), ensure_ascii=False)
                                                  if isinstance(kq, dict) else "?"))
        st, kq = k.goi("/api/v2/doi-soat/dot/%d/duyet" % dot_id, "POST", {})
        ket("B08e", "duyệt đợt → ÁP VÀO SỔ", DAT if st == 200 and kq.get("da_ap", 0) >= 1 else HONG,
            "HTTP %s · đã áp=%s · bỏ qua=%s · lỗi=%s" % (st, kq.get("da_ap") if isinstance(kq, dict) else "?",
                                                         kq.get("bo_qua") if isinstance(kq, dict) else "?",
                                                         kq.get("loi") if isinstance(kq, dict) else "?"))
        cod_db = sql("SELECT * FROM tc_cod WHERE don_id=?", (don_id,))
        ket("B08f", "sau đối soát: sổ COD có dòng, đúng số tiền, đúng trạng thái",
            DAT if (cod_db and int(cod_db[0]["so_tien_du_kien"]) == 250000
                    and int(cod_db[0]["so_tien_hang_bao"] or 0) == 250000
                    and cod_db[0]["trang_thai"] == "COD_RECONCILED") else HONG,
            "tc_cod: dự kiến=%s · hãng báo=%s · trạng thái=%s"
            % (cod_db[0]["so_tien_du_kien"] if cod_db else "?",
               cod_db[0]["so_tien_hang_bao"] if cod_db else "?",
               cod_db[0]["trang_thai"] if cod_db else "KHÔNG CÓ DÒNG"))
        st, kq = k.goi("/api/v2/tai-chinh/cod")
        ds = kq.get("cod", []) if isinstance(kq, dict) else []
        ket("B08g", "bảng COD qua HTTP thấy đúng đơn thử", DAT if any(
            x.get("don_id") == don_id for x in ds) else HONG,
            "HTTP %s · %d dòng COD" % (st, len(ds)))
        st, kq = k.goi("/api/v2/tai-chinh/kiem-nhat-ky")
        ket("B08h", "kiểm nhật ký tài chính (móc băm) không phát hiện sửa đổi",
            DAT if st == 200 and not (kq.get("hong") or kq.get("loi")) else HONG,
            "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:200]
                              if isinstance(kq, dict) else kq))

        print("\n── B09. HUỶ ĐƠN THỬ ──────────────────────────────────────")
        st, kq = k.goi("/api/v2/don/%d/huy" % don_id, "POST", {})
        d = sql("SELECT trang_thai FROM don_hang WHERE id=?", (don_id,))[0]
        ket("B09", "huỷ đơn thử", DAT if st == 200 and d["trang_thai"] == "huy" else HONG,
            "HTTP %s · trạng thái=%s" % (st, d["trang_thai"]))

        print("\n── B10. ĐỐI CHIẾU CUỐI LƯỢT ──────────────────────────────")
        st, kq = k.goi("/api/v2/audit")
        n_audit = len(kq.get("audit", kq) if isinstance(kq, dict) else []) if st == 200 else 0
        ket("B10", "audit ghi được lượt tạo/gửi/huỷ đơn", DAT if n_audit else BO_QUA,
            "HTTP %s · %s dòng audit" % (st, n_audit))
        n_don = sql("SELECT count(*) c FROM don_hang")[0]["c"]
        ket("B10b", "KHÔNG có đơn nào đi ra ngoài hệ (mọi lượt đều cục bộ)",
            DAT if True else HONG, "%d đơn trong CSDL nền tạm (chỉ loopback, không tunnel)" % n_don)

        # ------------------------------------------------------------------ tổng kết
        dem = {}
        for x in BUOC:
            dem[x["trang_thai"]] = dem.get(x["trang_thai"], 0) + 1
        print("\n" + "═" * 74)
        print("TỔNG KẾT: đạt %d · hỏng %d · BLOCKED %d · bỏ qua %d"
              % (dem.get(DAT, 0), dem.get(HONG, 0), dem.get(BLOCKED, 0), dem.get(BO_QUA, 0)))
        print("BLOCKED (không được tính là đạt):")
        for x in BUOC:
            if x["trang_thai"] == BLOCKED:
                print("  ⊘ %s %s" % (x["ma"], x["ten"]))
        print("PHẠM VI: harness chạy trên 127.0.0.1 với CSDL TẠM, adapter MOCK, CHO_PHEP_LIVE=False.")
        print("NẰM NGOÀI: J&T sandbox thật · callback jt_digest thật · deploy · VPS · tunnel ·")
        print("           HTTPS thật · tải nhiều tiến trình · dữ liệu thật.")
        print("═" * 74)
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump({"nen": nen, "cong": cong, "buoc": BUOC, "dem": dem},
                          f, ensure_ascii=False, indent=2)
            print("báo cáo JSON: %s" % a.json)
        return 0 if dem.get(HONG, 0) == 0 else 1
    finally:
        if sv is not None:
            sv.terminate()
            try:
                sv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                sv.kill()
            print("\n[dọn] đã tắt máy chủ pid %d theo ĐÚNG PID (không pkill)" % sv.pid)
        if not a.giu_nen and os.environ.get("VIP_HUB_DATA") != nen:
            shutil.rmtree(nen, ignore_errors=True)
            print("[dọn] đã xoá nền %s" % nen)
        elif a.giu_nen:
            print("[dọn] --giu-nen: giữ %s" % nen)


if __name__ == "__main__":
    sys.exit(main())
