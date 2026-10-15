#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G16-A — HARNESS NGHIỆM THU SANDBOX: kịch bản đầy đủ, chạy ở chế độ **MOCK**, loopback.

KỊCH BẢN (mã bước theo directive 15/10/2026, mục 15)
-----------------------------------------------------
    G01 ĐĂNG NHẬP
    G02 CHỌN TENANT
    G03 CHỌN TÀI KHOẢN J&T
    G04 TẠO ĐƠN THỬ
    G05 GỬI SANG J&T SANDBOX            ← **BLOCKED** (V-G09-01 + V-13906-05)
    G06 NHẬN CALLBACK                    ← chạy được phần MOCK (tự ký cục bộ); phần sandbox **BLOCKED**
    G07 XÁC MINH HÀNH TRÌNH
    G08 XÁC MINH DỮ LIỆU COD
    G09 HUỶ ĐƠN THỬ
    G10 ĐỐI CHIẾU / AUDIT
    G11 CHỐT CẤU TRÚC + HỢP ĐỒNG CALLBACK

BA PHÁN QUYẾT, KHÔNG GỘP
------------------------
`ĐẠT (MOCK)` **không phải** `ĐẠT`. Chặng nào chạm hãng thật mà chưa được cấp quyền thì ghi
`BLOCKED` kèm **chính xác cái còn thiếu** — không giả vờ, không bỏ qua im lặng. Một bộ thử chỉ
có ĐẠT/HỎNG sẽ buộc chặng sandbox phải chọn một trong hai, và cả hai đều sai.

SÁU CHỐT AN TOÀN — harness TỪ CHỐI CHẠY nếu mất một cái
-------------------------------------------------------
Xem `trien_khai/g16/chot_an_toan.py`. Bộ dò chốt có **tự kiểm** (`--tu-kiem`, 9 cấu hình tổng
hợp), vì chốt chặn cũng là thứ dùng để kiểm chứng nên nó cũng phải được kiểm.

CHẠY
----
    sh trien_khai/g16/chay_harness.sh              # dựng nền tạm, chạy, dọn
    sh trien_khai/g16/chay_harness.sh --giu-nen    # giữ nền để soi
    python3 trien_khai/g16/chot_an_toan.py --tu-kiem
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
import urllib.parse
import urllib.request

THU_MUC_G16 = os.path.dirname(os.path.abspath(__file__))
DU_AN = os.path.dirname(os.path.dirname(THU_MUC_G16))
GOC_APP = os.path.join(DU_AN, "app")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)

import chot_an_toan                                            # noqa: E402

# ------------------------------------------------------------------ mô hình bước
DAT, DAT_MOCK, HONG, BLOCKED, BO_QUA = "DAT", "DAT_MOCK", "HONG", "BLOCKED", "BO_QUA"
KY_HIEU = {DAT: "✓", DAT_MOCK: "✓", HONG: "✗", BLOCKED: "⊘", BO_QUA: "–"}
NHAN = {DAT: "ĐẠT", DAT_MOCK: "ĐẠT (MOCK)", HONG: "HỎNG", BLOCKED: "BLOCKED", BO_QUA: "BỎ QUA"}
BUOC = []

# Hai chặng KHÔNG được tính là đạt ở lượt này. Ghi một chỗ, để báo cáo và tài liệu không lệch.
THIEU_SANDBOX = ("credentials sandbox J&T CHƯA CẤP (V-13906-05) · gọi API hãng thật, kể cả"
                 " sandbox, CHƯA CẤP (V-G09-01)")
THIEU_CALLBACK_SANDBOX = (THIEU_SANDBOX + " · và chưa biết môi trường thử có đẩy callback không"
                          " (câu 24) · hình dạng chữ ký chiều callback chưa có tài liệu"
                          " (câu 6–7 ⇒ webhook.HOP_DONG_MUC = DOCUMENTED, không hơn)")


def ket(ma, ten, trang_thai, bang_chung=""):
    BUOC.append({"ma": ma, "ten": ten, "trang_thai": trang_thai,
                 "nhan": NHAN[trang_thai], "bang_chung": bang_chung})
    print("  %s [%s] %s — %s%s" % (KY_HIEU[trang_thai], ma, ten, NHAN[trang_thai],
                                   ("\n        " + bang_chung) if bang_chung else ""))
    return trang_thai


# ------------------------------------------------------------------ HTTP client
class Khach(object):
    def __init__(self, goc):
        self.goc = goc
        self.ck = {}
        self.luot_goi = 0

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
        self.luot_goi += 1
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


def cong_loopback():
    """Cổng do HỆ ĐIỀU HÀNH cấp (bind cổng 0 rồi nhả ngay). Cổng cố định gây HỎNG GIẢ khi bốn
    làn chạy cùng lúc trên một cây."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def _nguon(ten):
    with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--giu-nen", action="store_true")
    a = ap.parse_args()

    nen = os.environ.get("VIP_HUB_DATA") or ""
    goc = "http://127.0.0.1:%d" % cong_loopback()
    print("═" * 78)
    print("G16-A — HARNESS NGHIỆM THU SANDBOX (MOCK) · nền %s" % (nen or "<chưa đặt>"))
    print("═" * 78)

    # ---------------------------------------------------------------- sáu chốt an toàn
    ly_do = chot_an_toan.ly_do_tu_choi(nen, goc_url=goc)
    if ly_do:
        print("\nTỪ CHỐI CHẠY — mất ít nhất một chốt an toàn:")
        for x in ly_do:
            print("  · " + x)
        print("\nHarness này TẠO dữ liệu THẬT trong CSDL và nói chuyện HTTP. Chạy nó khi mất chốt")
        print("là thứ nguy hiểm hơn không có harness. Không có cờ nào để bỏ qua.")
        return 4
    print("  ✓ sáu chốt an toàn: ĐỦ (nền tạm · bind loopback · CHO_PHEP_LIVE=False · không gọi hãng)")

    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1")
    env.pop(chot_an_toan.CO_GOI_HANG, None)
    cong = int(goc.rsplit(":", 1)[1])
    sv = None
    try:
        # ------------------------------------------------------------ dựng nền
        print("\n── DỰNG NỀN TẠM ──────────────────────────────────────────────")
        for lenh, nhan in (("migrate.py", "migrate"), ("khoi_tao.py", "seed")):
            p = subprocess.run([sys.executable, os.path.join(GOC_APP, lenh)],
                               capture_output=True, text=True, env=env, cwd=DU_AN)
            if p.returncode:
                print("  ✗ %s hỏng: %s" % (nhan, (p.stderr or p.stdout)[-400:]))
                return 3
            print("  ✓ %s" % nhan)
        log = open(os.path.join(nen, "server.log"), "w")
        sv = subprocess.Popen([sys.executable, os.path.join(GOC_APP, "server.py"), str(cong)],
                              stdout=log, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cong), 0.3).close()
                break
            except OSError:
                if sv.poll() is not None:
                    print("  ✗ máy chủ chết khi khởi động:\n%s"
                          % open(os.path.join(nen, "server.log")).read()[-600:])
                    return 3
                time.sleep(0.2)
        print("  ✓ máy chủ 127.0.0.1:%d (pid %d) — CHỈ loopback" % (cong, sv.pid))

        db = os.path.join(nen, "hub.db")

        def sql(q, p=()):
            c = sqlite3.connect(db)
            c.row_factory = sqlite3.Row
            try:
                return [dict(x) for x in c.execute(q, p)]
            finally:
                c.close()

        def dem(bang, dk="1=1", ts=()):
            return sql("SELECT COUNT(*) c FROM %s WHERE %s" % (bang, dk), ts)[0]["c"]

        k = Khach(goc)
        duong_mk = os.path.join(nen, "TAI-KHOAN-DEMO.md")
        mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`", open(duong_mk, encoding="utf-8").read()))
        if "platform-owner" not in mk:
            print("  ✗ không đọc được mật khẩu demo từ %s" % duong_mk)
            return 3

        # ============================================================ G01 ĐĂNG NHẬP
        print("\n── G01. ĐĂNG NHẬP ─────────────────────────────────────────────")
        st, kq = k.goi("/api/v2/auth/dang-nhap", "POST",
                       {"ten_dang_nhap": "platform-owner", "mat_khau": mk["platform-owner"]})
        ket("G01", "đăng nhập platform-owner qua HTTP loopback",
            DAT if st == 200 else HONG,
            "HTTP %s · khoá trả về=%s" % (st, sorted(kq.keys()) if isinstance(kq, dict) else kq))
        st, kq = k.goi("/api/v2/platform/tenants", "POST",
                       {"ten": "Cty G16", "owner_ten_dang_nhap": "g16-owner",
                        "owner_mat_khau": "g16-owner-123", "goi_id": "pro"})
        tid = (kq.get("id") or (kq.get("tenant") or {}).get("id")) if isinstance(kq, dict) else None
        # Tenant THỨ HAI: có thật, để phép kiểm chéo tenant ở G06d không phải dựa vào một id bịa.
        st2, kq2 = k.goi("/api/v2/platform/tenants", "POST",
                         {"ten": "Cty G16B", "owner_ten_dang_nhap": "g16-owner-b",
                          "owner_mat_khau": "g16-owner-b-123", "goi_id": "pro"})
        tid_b = (kq2.get("id") or (kq2.get("tenant") or {}).get("id")) if isinstance(kq2, dict) else None
        if not tid or not tid_b:
            ket("G01b", "tạo hai tenant thử (A và B)", HONG, "HTTP %s/%s · %s" % (st, st2, kq))
            return 1
        ket("G01b", "tạo HAI tenant thử + owner qua cửa platform (đường THẬT)",
            DAT if st == 201 and st2 == 201 else HONG,
            "tenant A id=%s · tenant B id=%s (B dùng cho phép kiểm CHÉO TENANT ở G06d)"
            % (tid, tid_b))

        # ============================================================ G02 CHỌN TENANT
        print("\n── G02. CHỌN TENANT ───────────────────────────────────────────")
        k.ck = {}
        st, _ = k.goi("/api/v2/auth/dang-nhap", "POST",
                      {"ten_dang_nhap": "g16-owner", "mat_khau": "g16-owner-123"})
        st_me, me = k.goi("/api/v2/auth/toi")
        tenant_phien = (me.get("tenant") or {}).get("id") if isinstance(me, dict) else None
        ket("G02", "tenant đến từ PHIÊN đã xác thực, KHÔNG từ body",
            DAT if (st == 200 and tenant_phien == tid) else HONG,
            "HTTP %s · tenant=%s (mong đợi %s) · vai_tro=%s"
            % (st_me, tenant_phien, tid, me.get("vai_tro") if isinstance(me, dict) else "?"))

        # ============================================================ G03 TÀI KHOẢN J&T
        print("\n── G03. CHỌN TÀI KHOẢN J&T ────────────────────────────────────")
        st, kq = k.goi("/api/v2/tai-khoan-hang", "POST",
                       {"hang": "jt", "ten": "J&T G16 (mock)",
                        "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
        tk = kq.get("id") if isinstance(kq, dict) else None
        wh_ma = (kq.get("webhook_url", "") if isinstance(kq, dict) else "").rsplit("/", 1)[-1]
        row = sql("SELECT hang, moi_truong, kich_hoat, webhook_ma, webhook_secret_ma_hoa"
                  " FROM carrier_accounts WHERE id=?", (tk,))
        mt = row[0]["moi_truong"] if row else "?"
        ket("G03", "tạo tài khoản hãng J&T",
            DAT if st == 201 and tk else HONG,
            "HTTP %s · id=%s · hãng=%s · môi trường=%s · webhook_ma=%s"
            % (st, tk, row[0]["hang"] if row else "?", mt, wh_ma))
        if not tk or mt != "mock":
            ket("G03b", "tài khoản hãng PHẢI ở môi trường 'mock'", HONG,
                "môi trường thật là %r — harness CHỈ chạy mock, DỪNG cả lượt" % mt)
            return 1
        ket("G03b", "môi trường tài khoản = 'mock' (không sandbox/production)",
            DAT_MOCK, "nếu là sandbox/production thì harness DỪNG cả lượt — đây là chốt, không"
                      " phải cảnh báo")
        # Bí mật KHÔNG được in ra: chỉ kiểm dạng đã mã hoá at-rest.
        kin = all(str(row[0][c]).startswith("v") and "$" in str(row[0][c])
                  for c in ("webhook_secret_ma_hoa",))
        st_cred = sql("SELECT credentials_ma_hoa FROM carrier_accounts WHERE id=?", (tk,))[0]
        kin = kin and str(st_cred["credentials_ma_hoa"]).count("$") >= 2
        ket("G03c", "credentials + webhook secret mã hoá at-rest (chỉ kiểm DẠNG, không in giá trị)",
            DAT if kin else HONG, "hai trường bí mật đều có dạng v3$<key_id>$…")

        # ============================================================ G04 TẠO ĐƠN THỬ
        print("\n── G04. TẠO ĐƠN THỬ ──────────────────────────────────────────")
        st, kq = k.goi("/api/v2/don", "POST", {
            "nguoi_nhan_ten": "Người nhận G16", "nguoi_nhan_sdt": "0901234567",
            "nguoi_nhan_dia_chi": "12 Lê Lợi, Quận 1, TP HCM",
            "nguoi_gui_ten": "Kho G16", "nguoi_gui_sdt": "0900000000",
            "nguoi_gui_dia_chi": "1 Kho, Q7, TP HCM",
            "hang_hoa": "Áo thun thử", "khoi_luong_gram": 500, "cod": 250000,
            "tien_thu_ho": 250000})
        don = kq.get("don", {}) if isinstance(kq, dict) else {}
        don_id, ma_don = don.get("id"), don.get("ma_don")
        ket("G04", "tạo đơn THỬ (không phải đơn thật)",
            DAT if st in (200, 201) and don_id else HONG,
            "HTTP %s · id=%s · mã=%s · trạng thái=%s · COD=%s"
            % (st, don_id, ma_don, don.get("trang_thai"), don.get("cod") or don.get("tien_thu_ho")))
        if not don_id:
            return 1
        st, kq = k.goi("/api/v2/don/%d/duyet" % don_id, "POST", {})
        ket("G04b", "duyệt đơn thử", DAT if st == 200 else HONG,
            "HTTP %s · trạng thái=%s" % (st, (kq.get("don") or {}).get("trang_thai")
                                         if isinstance(kq, dict) else kq))

        # ============================================================ G05 GỬI SANG SANDBOX
        print("\n── G05. GỬI SANG J&T SANDBOX ──────────────────────────────────")
        ket("G05", "GỬI SANG J&T SANDBOX", BLOCKED, "thiếu: " + THIEU_SANDBOX)
        st, kq = k.goi("/api/v2/don/%d/gui" % don_id, "POST", {"carrier_account_id": tk})
        d = (kq.get("don") or {}) if isinstance(kq, dict) else {}
        mvd = d.get("ma_van_don")
        ket("G05-MOCK", "chặng MOCK của CÙNG đường mã: gửi qua adapter mock",
            DAT_MOCK if st == 200 and mvd else HONG,
            "HTTP %s · mã vận đơn=%s · trạng thái=%s · tài khoản môi trường=%s (KHÔNG phải sandbox)"
            % (st, mvd, d.get("trang_thai"), mt))
        if not mvd:
            return 1
        st, kq = k.goi("/api/v2/don/%d/nhan" % don_id)
        ket("G05b", "nhãn vận đơn KHÔNG phải nhãn thật",
            DAT_MOCK if st == 200 and not kq.get("nhan_that") else HONG,
            "HTTP %s · nhan_that=%s · la_mock=%s" % (st, kq.get("nhan_that"), kq.get("la_mock")))

        # ============================================================ G06 NHẬN CALLBACK
        print("\n── G06. NHẬN CALLBACK (tự ký CỤC BỘ bằng bí mật của chính account) ──")
        os.environ["VIP_HUB_DATA"] = nen
        import bao_mat
        import webhook as wh
        secret = bao_mat.giai_ma_wh(row[0]["webhook_secret_ma_hoa"], row[0]["webhook_ma"])

        def ky(than):
            return {"X-Webhook-Signature": hmac.new(secret.encode(), than, hashlib.sha256).hexdigest()}

        def gui_cb(than, hdr=None):
            return k.goi("/api/v2/webhook/nhan/%s" % row[0]["webhook_ma"], "POST", tho=than,
                         hdr=hdr if hdr is not None else ky(than))

        def doi_den(ma_sk, toi_da=60):
            for _ in range(toi_da):
                r = sql("SELECT trang_thai, loi_cuoi FROM wh_su_kien WHERE id=?", (ma_sk,))
                if r and r[0]["trang_thai"] in ("xong", "dlq", "khong_khop"):
                    return r[0]
                time.sleep(0.2)
            return r[0] if r else None

        # --- G06a: ĐỐI CHỨNG DƯƠNG trước mọi ca phủ định. Một bộ thử chỉ toàn ca phủ định mà
        #     không chứng minh đường đi được thì "bị từ chối" không nói lên điều gì.
        pl = json.dumps({"event": "lay_hang", "tracking_number": mvd, "event_id": "g16-evt-1",
                         "hang_luc": "2026-10-15T08:00:00+07:00"}, ensure_ascii=False).encode()
        st, kq = gui_cb(pl)
        sk1 = kq.get("su_kien_id") if isinstance(kq, dict) else None
        ket("G06a", "ĐỐI CHỨNG DƯƠNG: callback HỢP LỆ được nhận (chữ ký đúng)",
            DAT_MOCK if st == 202 and sk1 else HONG,
            "HTTP %s · su_kien_id=%s · %s" % (st, sk1, json.dumps(kq, ensure_ascii=False)[:120]
                                              if isinstance(kq, dict) else kq))
        if not sk1:
            return 1
        r = doi_den(sk1)
        ket("G06a2", "sự kiện xử xong và trục GIAO VẬN đổi theo callback",
            DAT_MOCK if (r and r["trang_thai"] == "xong"
                         and sql("SELECT trang_thai_giao g FROM don_hang WHERE id=?",
                                 (don_id,))[0]["g"] == "lay_hang") else HONG,
            "sự kiện=%s · trục giao vận=%s" % (r["trang_thai"] if r else "?",
                                               sql("SELECT trang_thai_giao g FROM don_hang WHERE id=?",
                                                   (don_id,))[0]["g"]))

        # --- G06b: trùng lặp — chống trùng CƯỠNG CHẾ BẰNG CSDL, không bằng `if`
        n_truoc = dem("wh_su_kien", "carrier_account_id=?", (tk,))
        st2, kq2 = gui_cb(pl)
        n_sau = dem("wh_su_kien", "carrier_account_id=?", (tk,))
        sk2 = kq2.get("su_kien_id") if isinstance(kq2, dict) else None
        ket("G06b", "gửi lại Y NGUYÊN: idempotent, KHÔNG nhân đôi sự kiện",
            DAT_MOCK if (st2 == 200 and n_sau == n_truoc and sk2 == sk1) else HONG,
            "HTTP %s · sự kiện %s→%s (mong đợi không đổi) · sk_id %s==%s"
            % (st2, n_truoc, n_sau, sk2, sk1))
        # Bằng chứng ràng buộc nằm ở TẦNG CSDL: nhồi thẳng bằng SQL phải bị chặn.
        try:
            c = sqlite3.connect(db)
            c.execute("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,"
                      "nhan_luc) VALUES (?,?,?,?,?)",
                      (tk, sql("SELECT event_id e FROM wh_su_kien WHERE id=?", (sk1,))[0]["e"],
                       b"x", "{}", "2026-10-15 00:00:00+0700"))
            c.commit()
            chan_o_csdl = False
        except sqlite3.IntegrityError:
            chan_o_csdl = True
        finally:
            try:
                c.close()
            except Exception:                                   # noqa: BLE001
                pass
        ket("G06b2", "chống trùng nằm ở TẦNG CSDL (nhồi thẳng bằng SQL vẫn bị chặn)",
            DAT if chan_o_csdl else HONG,
            "UNIQUE(carrier_account_id, event_id) — INSERT thẳng %s"
            % ("BỊ CHẶN (IntegrityError)" if chan_o_csdl else "LỌT ⇒ chống trùng đang ở tầng mã"))

        # --- G06c: chữ ký SAI
        n_truoc = dem("wh_su_kien", "carrier_account_id=?", (tk,))
        bad = json.dumps({"event": "dang_giao", "tracking_number": mvd,
                          "event_id": "g16-evt-sai-chu-ky"}, ensure_ascii=False).encode()
        st3, _ = gui_cb(bad, hdr={"X-Webhook-Signature": "0" * 64})
        ket("G06c", "chữ ký SAI bị từ chối và KHÔNG lưu sự kiện",
            DAT if (st3 == 401 and dem("wh_su_kien", "carrier_account_id=?", (tk,)) == n_truoc)
            else HONG,
            "HTTP %s (mong đợi 401) · sự kiện %s→%s (mong đợi không đổi)"
            % (st3, n_truoc, dem("wh_su_kien", "carrier_account_id=?", (tk,))))

        # --- G06d: CHÉO TENANT — payload khai tenant B, account thuộc tenant A
        n_claim = dem("audit", "hanh_dong='webhook_claim_tenant_bi_bo_qua'")
        pl_x = json.dumps({"event": "dang_giao", "tracking_number": mvd,
                           "event_id": "g16-evt-cheo-tenant", "tenant_id": tid_b},
                          ensure_ascii=False).encode()
        st4, kq4 = gui_cb(pl_x)
        sk4 = kq4.get("su_kien_id") if isinstance(kq4, dict) else None
        if sk4:
            doi_den(sk4)
        d_don = sql("SELECT tenant_id, trang_thai_giao, ma_van_don FROM don_hang WHERE id=?",
                    (don_id,))[0]
        n_claim_sau = dem("audit", "hanh_dong='webhook_claim_tenant_bi_bo_qua'")
        ket("G06d", "CHÉO TENANT: tenant chỉ đến từ carrier_account, lời khai trong payload bị BỎ QUA",
            DAT_MOCK if (st4 == 202 and d_don["tenant_id"] == tid and n_claim_sau > n_claim) else HONG,
            "HTTP %s · đơn vẫn thuộc tenant A (%s) · đi tiếp bình thường (trục=%s) · audit"
            " 'webhook_claim_tenant_bi_bo_qua' %s→%s"
            % (st4, d_don["tenant_id"], d_don["trang_thai_giao"], n_claim, n_claim_sau))
        n_don_b = dem("don_hang", "tenant_id=?", (tid_b,))
        ket("G06d2", "tenant B KHÔNG bị chạm: 0 đơn, 0 sự kiện của B",
            DAT if (n_don_b == 0 and dem("wh_su_kien",
                                         "carrier_account_id IN (SELECT id FROM carrier_accounts"
                                         " WHERE tenant_id=?)", (tid_b,)) == 0) else HONG,
            "%d đơn của tenant B · 0 sự kiện gắn account của B" % n_don_b)

        # --- G06e: mã 110 nhập nhằng + mã lạ ⇒ NEEDS_REVIEW, 0 dòng sổ COD
        def so_cod():
            return {b: dem(b) for b in ("tc_cod", "tc_cod_chuyen", "tc_but_toan")}

        truoc_cod = so_cod()
        truoc_tt = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                       (don_id,))[0]
        for ma_qt, ten_qt in ((110, "110 (nhập nhằng, D-4)"), (9999, "9999 (mã lạ)")):
            biz = json.dumps({"billCode": mvd,
                              "details": [{"scanTime": "2026-10-15 09:%02d:00" % (ma_qt % 60),
                                           "scanTypeCode": ma_qt, "desc": "quét thử G16"}]},
                             ensure_ascii=False)
            than = urllib.parse.urlencode({"bizContent": biz}).encode()
            stx, kqx = gui_cb(than)
            skx = kqx.get("su_kien_id") if isinstance(kqx, dict) else None
            if skx:
                doi_den(skx)
            r_sk = sql("SELECT can_soat, hang_ma_goc, trang_thai, trang_thai_chuan"
                       " FROM wh_su_kien WHERE id=?", (skx,)) if skx else []
            sau_tt = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                         (don_id,))[0]
            kq_ok = (stx == 202 and r_sk and r_sk[0]["can_soat"] == 1
                     and r_sk[0]["trang_thai_chuan"] is None
                     and sau_tt == truoc_tt)
            ket("G06e-%s" % ma_qt, "%s → NEEDS_REVIEW, KHÔNG đổi trạng thái đơn" % ten_qt,
                DAT_MOCK if kq_ok else HONG,
                "HTTP %s · can_soat=%s · trạng_thái_chuẩn=%s · đơn giữ nguyên (%s/hạng %s)"
                % (stx, r_sk[0]["can_soat"] if r_sk else "?",
                   r_sk[0]["trang_thai_chuan"] if r_sk else "?",
                   sau_tt["trang_thai_giao"], sau_tt["hang_trang_thai_giao"]))
        sau_cod = so_cod()
        ket("G06e2", "mã chưa xác minh KHÔNG chạm sổ COD: 0 dòng mới ở cả ba bảng",
            DAT if sau_cod == truoc_cod else HONG,
            "trước=%s · sau=%s (cả ba phải bằng 0)" % (truoc_cod, sau_cod))
        ket("G06e3", "đơn KHÔNG bị đánh dấu giao thành công bởi mã chưa xác minh",
            DAT if sql("SELECT trang_thai_giao g FROM don_hang WHERE id=?",
                       (don_id,))[0]["g"] != "giao_thanh_cong" else HONG,
            "trục giao vận=%s (cấm 'giao_thanh_cong' từ mã 110/9999)"
            % sql("SELECT trang_thai_giao g FROM don_hang WHERE id=?", (don_id,))[0]["g"])

        # --- G06f: callback sandbox thật → BLOCKED
        ket("G06-SANDBOX", "CALLBACK THEO SƠ ĐỒ CỦA HÃNG (`jt_digest`)", BLOCKED,
            "thiếu: " + THIEU_CALLBACK_SANDBOX)
        so_do = wh.SO_DO_THEO_HANG.get("jt")
        ket("G06-SANDBOX2", "mức xác thực callback của hãng KHÔNG được tự nâng",
            DAT if (so_do == "jt_digest"
                    and wh.bang_muc_xac_thuc()["jt"]["sandbox_production"]["muc"]
                    == wh.MUC_DOCUMENTED) else HONG,
            "sơ đồ=%s · mức=%s (DOCUMENTED nghĩa là VIẾT THEO TÀI LIỆU, chưa đối chiếu hãng)"
            % (so_do, wh.bang_muc_xac_thuc()["jt"]["sandbox_production"]["muc"]))

        # ============================================================ G07 XÁC MINH HÀNH TRÌNH
        print("\n── G07. XÁC MINH HÀNH TRÌNH ───────────────────────────────────")
        pl_g = json.dumps({"event": "dang_giao", "tracking_number": mvd,
                           "event_id": "g16-evt-2", "hang_luc": "2026-10-15T10:00:00+07:00"},
                          ensure_ascii=False).encode()
        _, kqg = gui_cb(pl_g)
        if kqg.get("su_kien_id"):
            doi_den(kqg["su_kien_id"])
        # Sự kiện CŨ đến SAU (out-of-order) — phải bị chặn bởi mốc của hãng.
        pl_cu = json.dumps({"event": "lay_hang", "tracking_number": mvd,
                            "event_id": "g16-evt-cu-den-sau",
                            "hang_luc": "2026-10-15T07:00:00+07:00"}, ensure_ascii=False).encode()
        _, kqc = gui_cb(pl_cu)
        skc = kqc.get("su_kien_id") if isinstance(kqc, dict) else None
        if skc:
            doi_den(skc)
        d_don = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?",
                    (don_id,))[0]
        ket("G07a", "sự kiện đến MUỘN (mốc cũ hơn) KHÔNG kéo lùi trạng thái",
            DAT_MOCK if d_don["trang_thai_giao"] == "dang_giao" else HONG,
            "trục giao vận=%s (hạng %s) — sự kiện cũ đến sau bị chặn"
            % (d_don["trang_thai_giao"], d_don["hang_trang_thai_giao"]))
        st, kq = k.goi("/api/v2/don/%d/hanh-trinh" % don_id)
        moc = kq.get("moc", []) if isinstance(kq, dict) else []
        moc_wh = [x for x in moc if str(x.get("nguon", "")).startswith("webhook:")]
        ket("G07b", "đường tra hành trình thấy ĐÚNG các mốc do CALLBACK sinh ra (đồng bộ hành trình)",
            DAT_MOCK if (st == 200 and moc_wh
                         and "KHÔNG gọi hãng" in str(kq.get("nguon_du_lieu", ""))) else HONG,
            "HTTP %s · %d mốc, trong đó %d mốc nguồn 'webhook:…' · %s"
            % (st, len(moc), len(moc_wh), kq.get("nguon_du_lieu") if isinstance(kq, dict) else kq))
        st, kq = k.goi("/api/v2/don/%d" % don_id)
        n_ls = len(kq.get("lich_su", [])) if isinstance(kq, dict) else 0
        ket("G07c", "mỗi lượt đổi trạng thái có dòng lịch sử (hợp đồng §11)",
            DAT if n_ls else HONG, "%d dòng lịch sử" % n_ls)
        st, kq = k.goi("/api/v2/webhook/su-kien")
        ds = kq.get("su_kien", []) if isinstance(kq, dict) else []
        ket("G07d", "cửa xem sự kiện webhook thấy các sự kiện của tenant này",
            DAT if st == 200 and ds else HONG, "HTTP %s · %d sự kiện" % (st, len(ds)))
        st, kq = k.goi("/api/v2/polling/chay", "POST", {"chi_hang_khong_webhook": True})
        ket("G07e", "đường polling (dự phòng khi hãng không đẩy) gọi được",
            DAT_MOCK if st in (200, 202) else HONG,
            "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:120]
                              if isinstance(kq, dict) else kq))

        # ============================================================ G08 DỮ LIỆU COD
        print("\n── G08. XÁC MINH DỮ LIỆU COD ──────────────────────────────────")
        don_cod = sql("SELECT cod FROM don_hang WHERE id=?", (don_id,))[0]["cod"]
        ket("G08a", "số COD khai trên đơn KHÔNG bị callback làm đổi",
            DAT if int(don_cod or 0) == 250000 else HONG, "don_hang.cod=%s" % don_cod)
        truoc = dem("tc_cod", "don_id=?", (don_id,))
        ket("G08b", "sổ COD CHƯA mở vì callback — đúng thiết kế (COD_EXPECTED không sinh bút toán)",
            DAT if truoc == 0 else HONG, "%d dòng tc_cod cho đơn này" % truoc)
        r_phi = sql("SELECT COALESCE(SUM(so_tien_dong),0) t, COUNT(*) c FROM tc_phi"
                    " WHERE tenant_id=? AND don_id=? AND loai='bao_gia'", (tid, don_id))[0]
        phi_he = (r_phi["t"] if r_phi["c"] else
                  sql("SELECT phi_van_chuyen p FROM don_hang WHERE id=?", (don_id,))[0]["p"])
        csv = ("billCode,codAmount,freight,settlement period,status\n%s,250000,%s,2026-10,delivered\n"
               % (mvd, "" if phi_he is None else phi_he)).encode()
        st, kq = k.goi("/api/v2/doi-soat/nap", "POST", {
            "ten_file": "bang-ke-jt-g16.csv", "hang": "jt",
            "noi_dung_base64": base64.b64encode(csv).decode(),
            "ky_thanh_toan": "2026-10", "carrier_account_id": tk})
        dot = kq.get("dot_id") if isinstance(kq, dict) else None
        k.goi("/api/v2/doi-soat/dot/%d/doi-chieu" % dot, "POST", {}) if dot else None
        _, kq_duyet = k.goi("/api/v2/doi-soat/dot/%d/duyet" % dot, "POST", {}) if dot else (0, {})
        cod_db = sql("SELECT * FROM tc_cod WHERE don_id=?", (don_id,))
        ket("G08c", "ĐỐI CHỨNG DƯƠNG: sổ COD CHỈ mở qua ĐƯỜNG ĐỐI SOÁT (nạp bảng kê → duyệt)",
            DAT if (dot and cod_db and int(cod_db[0]["so_tien_du_kien"]) == 250000
                    and cod_db[0]["trang_thai"] == "COD_RECONCILED") else HONG,
            "đợt=%s · đã áp=%s · tc_cod: dự kiến=%s · hãng báo=%s · trạng thái=%s"
            % (dot, kq_duyet.get("da_ap") if isinstance(kq_duyet, dict) else "?",
               cod_db[0]["so_tien_du_kien"] if cod_db else "?",
               cod_db[0]["so_tien_hang_bao"] if cod_db else "?",
               cod_db[0]["trang_thai"] if cod_db else "KHÔNG CÓ DÒNG"))
        st, kq = k.goi("/api/v2/tai-chinh/cod")
        ds = kq.get("cod", []) if isinstance(kq, dict) else []
        ket("G08d", "bảng COD qua HTTP (cửa người dùng) thấy đúng đơn thử",
            DAT if st == 200 and any(x.get("don_id") == don_id for x in ds) else HONG,
            "HTTP %s · %d dòng COD" % (st, len(ds)))
        st, kq = k.goi("/api/v2/tai-chinh/kiem-nhat-ky")
        ket("G08e", "kiểm nhật ký tài chính (móc băm) không phát hiện sửa đổi",
            DAT if st == 200 and not (kq.get("hong") or kq.get("loi")) else HONG,
            "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:160]
                              if isinstance(kq, dict) else kq))

        # ============================================================ G09 HUỶ ĐƠN THỬ
        print("\n── G09. HUỶ ĐƠN THỬ ───────────────────────────────────────────")
        st, kq = k.goi("/api/v2/don/%d/huy" % don_id, "POST", {})
        d = sql("SELECT trang_thai FROM don_hang WHERE id=?", (don_id,))[0]
        ket("G09", "huỷ đơn thử", DAT if st == 200 and d["trang_thai"] == "huy" else HONG,
            "HTTP %s · trạng thái=%s" % (st, d["trang_thai"]))

        # ============================================================ G10 ĐỐI CHIẾU / AUDIT
        print("\n── G10. ĐỐI CHIẾU / AUDIT ─────────────────────────────────────")
        dch = wh.doi_chieu_hanh_trinh(tid)
        ket("G10a", "đối chiếu hành trình: BẤT BIẾN chéo tenant còn nguyên",
            DAT if dch["bat_bien_tenant_dat"] is True and not dch["lech_tenant"] else HONG,
            "lech_tenant=%s · không_khớp=%d · chờ người soát=%s · DLQ/chờ thử=%d"
            % (dch["lech_tenant"], len(dch["khong_khop"]),
               len(dch["cho_nguoi_soat"] or []), len(dch["ket_dinh"])))
        ket("G10b", "đối chiếu thấy ĐÚNG các sự kiện cần người soát (110/9999), không giấu",
            DAT if len(dch["cho_nguoi_soat"] or []) >= 2 else HONG,
            "%d sự kiện can_soat=1: %s" % (len(dch["cho_nguoi_soat"] or []),
                                           [x["hang_ma_goc"] for x in (dch["cho_nguoi_soat"] or [])]))
        st, kq = k.goi("/api/v2/audit")
        n_audit = len(kq.get("audit", kq) if isinstance(kq, dict) else []) if st == 200 else 0
        ket("G10c", "audit ghi được vòng đời lượt thử (tạo/gửi/callback/huỷ)",
            DAT if n_audit else HONG, "HTTP %s · %s dòng audit" % (st, n_audit))
        n_tat_ca_don = dem("don_hang")
        ket("G10d", "KHÔNG có lượt nào ra ngoài loopback (không tunnel, không VPS)",
            DAT if k.luot_goi and k.goc.startswith("http://127.0.0.1:") else HONG,
            "%d lượt HTTP, tất cả tới http://127.0.0.1:%d · %d đơn nằm trong nền TẠM"
            % (k.luot_goi, cong, n_tat_ca_don))

        # ============================================================ G11 CHỐT CẤU TRÚC
        print("\n── G11. CHỐT CẤU TRÚC + HỢP ĐỒNG CALLBACK ─────────────────────")
        ng = _nguon("webhook.py")
        n_wm = ng.count("UPDATE wh_su_kien SET hang_moc_thoi_gian")
        ket("G11a", "ĐÚNG MỘT nơi ghi cột watermark, và chỉ khi sự kiện ĐƯỢC ÁP",
            DAT if n_wm == 1 and "if ap_dung and moc:" in ng else HONG,
            "%d câu UPDATE cột mốc trong webhook.py (mong đợi 1) · điều kiện 'ap_dung and moc'"
            " %s" % (n_wm, "có" if "if ap_dung and moc:" in ng else "THIẾU"))
        ket("G11b", "tầng ĐỌC vẫn lọc dữ liệu CŨ (`trang_thai_chuan IS NOT NULL`)",
            DAT if "trang_thai_chuan IS NOT NULL" in ng else HONG,
            "bộ lọc này cứu các dòng do mã CŨ ghi trong CSDL THẬT — bỏ nó là lỗi G14 sống lại")
        ket("G11c", "đường webhook KHÔNG có cửa gọi mạng và không mở LIVE",
            DAT if not any(x in ng for x in ("urllib.request", "socket.socket", "http.client",
                                             "CHO_PHEP_LIVE = True")) else HONG,
            "không có urllib.request/socket/http.client · không có CHO_PHEP_LIVE = True")
        ràng = sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='wh_su_kien'")[0]["sql"]
        ket("G11d", "ràng buộc chống trùng có THẬT trong schema CSDL đang chạy",
            DAT if "UNIQUE (carrier_account_id, event_id)" in ràng else HONG,
            "sqlite_master.wh_su_kien chứa UNIQUE(carrier_account_id, event_id)")
        bc = wh.bao_cao_hop_dong_callback()
        loi_hd = wh.kiem_hop_dong_khong_tu_nang_muc()
        ket("G11e", "hợp đồng callback: mức DOCUMENTED, KHÔNG tự nhận đã xác minh",
            DAT if (bc["muc"] == "DOCUMENTED" and bc["xac_minh_voi_hang"] is False
                    and not loi_hd) else HONG,
            "mức=%s · xác minh với hãng=%s · %d trường · %d chỗ BLOCKED · vi phạm=%s"
            % (bc["muc"], bc["xac_minh_voi_hang"], bc["so_truong"], len(bc["blocked"]), loi_hd))
        canh_bao = bc["canh_bao"]
        ket("G11f", "năm chỗ hở Owner chỉ đích danh đều BLOCKED kèm đúng cái còn thiếu",
            DAT if all(any(b["ten"] == t for b in bc["blocked"]) for t in
                       ("khoa_ky_chieu_callback", "chuoi_dem_di_ky", "phuong_thuc_http",
                        "phan_hoi_xac_nhan", "chinh_sach_thu_lai")) else HONG,
            "khoá ký · chuỗi ký · phương thức HTTP · hình dạng phản hồi · chính sách thử lại"
            " — mỗi chỗ có câu hỏi gửi hãng + đường mã đang bị chặn")
        ket("G11g", "không câu nào trong báo cáo đọc như 'đã xác minh với hãng'",
            DAT if "KHÔNG PHẢI LÀ HỢP ĐỒNG ĐÃ XÁC MINH" in canh_bao else HONG,
            canh_bao[:180] + "…")

        # ------------------------------------------------------------------ tổng kết
        dem_tt = {}
        for x in BUOC:
            dem_tt[x["trang_thai"]] = dem_tt.get(x["trang_thai"], 0) + 1
        print("\n" + "═" * 78)
        print("TỔNG KẾT: đạt %d · ĐẠT (MOCK) %d · hỏng %d · BLOCKED %d · bỏ qua %d"
              % (dem_tt.get(DAT, 0), dem_tt.get(DAT_MOCK, 0), dem_tt.get(HONG, 0),
                 dem_tt.get(BLOCKED, 0), dem_tt.get(BO_QUA, 0)))
        print("BLOCKED — KHÔNG được tính là đạt:")
        for x in BUOC:
            if x["trang_thai"] == BLOCKED:
                print("  ⊘ %s %s" % (x["ma"], x["ten"]))
                print("      %s" % x["bang_chung"])
        print("PHẠM VI: 127.0.0.1 · CSDL TẠM · adapter MOCK · CHO_PHEP_LIVE=False · không gọi hãng.")
        print("NẰM NGOÀI: J&T sandbox thật · callback jt_digest thật · TLS/tunnel/VPS · deploy ·")
        print("           tải nhiều tiến trình · dữ liệu thật.")
        print("MỘT LƯỢT MOCK XANH KHÔNG PHẢI BẰNG CHỨNG ĐƯỜNG SANDBOX CHẠY ĐƯỢC.")
        print("═" * 78)
        bc_out = wh.bao_cao_hop_dong_callback()
        bao_cao = {
            "gate": "G16-A", "agent": "AG-04 (WEBHOOK)", "ngay": "2026-10-15",
            "nen": nen, "cong": cong, "bind": "127.0.0.1", "che_do": "MOCK",
            "chot_an_toan": {"so_chot": 6, "dat": True,
                             "tu_kiem_bo_do": "xem chot_an_toan.py --tu-kiem"},
            "moi_truong_van_chuyen": chot_an_toan.bao_cao_moi_truong(),
            "buoc": BUOC, "dem": dem_tt,
            "blocked": [{"ma": x["ma"], "ten": x["ten"], "thieu": x["bang_chung"]}
                        for x in BUOC if x["trang_thai"] == BLOCKED],
            "hop_dong_callback": {"muc": bc_out["muc"], "xac_minh_voi_hang": bc_out["xac_minh_voi_hang"],
                                  "so_truong": bc_out["so_truong"],
                                  "so_blocked": len(bc_out["blocked"]),
                                  "blocked": [b["ten"] for b in bc_out["blocked"]]},
            "pham_vi": {
                "trong": ["đăng nhập · chọn tenant · tài khoản J&T · tạo đơn · callback hub_hmac"
                          " (tự ký cục bộ) · trùng lặp · chữ ký sai · chéo tenant · mã 110/mã lạ"
                          " · đến muộn · hành trình · COD · huỷ · đối chiếu · audit"],
                "ngoai": ["J&T sandbox thật", "callback jt_digest thật", "TLS thật", "tunnel/VPS",
                          "deploy", "nhiều tiến trình", "dữ liệu thật"],
            },
            "ket_luan": ("MOCK ĐẠT ở các bước không chạm hãng; HAI chặng chạm hãng là BLOCKED và"
                         " KHÔNG được tính là đạt."),
        }
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(bao_cao, f, ensure_ascii=False, indent=2)
            print("báo cáo JSON: %s" % a.json)
        return 0 if dem_tt.get(HONG, 0) == 0 else 1
    finally:
        if sv is not None:
            sv.terminate()
            try:
                sv.wait(timeout=10)
            except subprocess.TimeoutExpired:
                sv.kill()
            print("\n[dọn] đã tắt máy chủ pid %d theo ĐÚNG PID (không pkill/killall)" % sv.pid)
        if not a.giu_nen and os.environ.get("VIP_HUB_DATA") != nen:
            shutil.rmtree(nen, ignore_errors=True)
            print("[dọn] đã xoá nền %s" % nen)
        elif a.giu_nen:
            print("[dọn] --giu-nen: giữ %s" % nen)


if __name__ == "__main__":
    sys.exit(main())
