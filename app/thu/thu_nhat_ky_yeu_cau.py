#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G15 — CA THỬ ĐỐI CHỨNG DƯƠNG cho **P-G15-01**: log có cấu trúc phải THẬT SỰ chạy.

====== VÌ SAO CẦN TỆP NÀY ======
Đo ngày 15/10/2026 (AG-04, I04): `quan_sat` có đủ mô-đun — sinh `request_id`, JSONL, bộ che
bí mật, bộ đếm metric — nhưng `server.py` **chỉ** gọi nó cho `/suc-khoe`, `/san-sang`,
`/metric`. `bat_dau_yeu_cau()` / `ket_thuc_yeu_cau()` / `ghi()` **không được gọi ở đâu trong
đường yêu cầu**, nên log máy chủ thật có **0 dòng JSON** và không lượt HTTP nào có
`request_id`. Cùng đúng một khuôn với **V-13910** ("mã có, nhưng không ai gọi").

Vì sao các bộ thử sẵn có KHÔNG bắt được: `thu_quan_sat.py` kiểm `quan_sat` như **hàm thuần**
(gọi thẳng vào một `StringIO`), nên nó xanh trong khi đường HTTP thật không ghi gì. Một bộ thử
kiểm mô-đun **không** kiểm được việc mô-đun đó có được NỐI VÀO hay không. Tệp này kiểm đúng
khoảng hở đó: **gọi route THẬT qua HTTP rồi đọc log THẬT của tiến trình máy chủ.**

====== PHẠM VI ======
Đo: một tiến trình máy chủ · loopback · CSDL tạm · các route thật · đọc log của chính tiến
trình đó.
NGOÀI phạm vi: nhiều tiến trình ghi cùng một luồng log · log bị cắt vòng · tải lớn · TLS ·
định dạng log mà bộ thu log bên ngoài đọc.

====== VÌ SAO CÓ CA VỀ BÍ MẬT ======
Nối log vào đường yêu cầu là mở một đường rò MỚI. Nên phải có ca khẳng định mật khẩu gửi
trong body và token giả gửi trong query **KHÔNG** xuất hiện trong log. Ca đó dùng chuỗi GIẢ,
không phải bí mật thật của bất kỳ ai.
"""
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
import unittest
import urllib.error
import urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # …/app
DU_AN = os.path.dirname(GOC)

# Chuỗi GIẢ, cố ý trông như bí mật để phép dò có nghĩa. KHÔNG phải bí mật của ai.
MK_GIA = "MatKhau-GIA-cho-ca-thu-PG1501"
TOKEN_GIA = "token-GIA-trong-query-PG1501"

SV = None
NEN = None
CONG = None
LOG = None


def _cong_roi():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def setUpModule():
    """Dựng nền RIÊNG (không dùng `VIP_HUB_DATA` của bộ chạy chung) + một máy chủ thật."""
    global SV, NEN, CONG, LOG
    NEN = tempfile.mkdtemp(prefix="vh-g15log-")
    LOG = os.path.join(NEN, "server.log")
    env = dict(os.environ, VIP_HUB_DATA=NEN)
    for lenh in ("migrate.py", "khoi_tao.py"):
        p = subprocess.run([sys.executable, os.path.join(GOC, lenh)],
                           capture_output=True, text=True, env=env, cwd=DU_AN)
        if p.returncode:
            shutil.rmtree(NEN, ignore_errors=True)
            raise unittest.SkipTest("không dựng được nền (%s hỏng): %s"
                                    % (lenh, (p.stderr or p.stdout)[-300:]))
    CONG = _cong_roi()
    f = open(LOG, "w")
    SV = subprocess.Popen([sys.executable, os.path.join(GOC, "server.py"), str(CONG)],
                          stdout=f, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
    het = time.time() + 25
    while time.time() < het:
        try:
            socket.create_connection(("127.0.0.1", CONG), 0.3).close()
            return
        except OSError:
            if SV.poll() is not None:
                break
            time.sleep(0.2)
    shutil.rmtree(NEN, ignore_errors=True)
    raise unittest.SkipTest("máy chủ không mở cổng %s:\n%s"
                            % (CONG, open(LOG).read()[-400:] if os.path.exists(LOG) else ""))


def tearDownModule():
    """Tắt theo ĐÚNG PID. KHÔNG `pkill`, KHÔNG `killall` (CLAUDE.md §16.7)."""
    if SV is not None:
        SV.terminate()
        try:
            SV.wait(timeout=10)
        except subprocess.TimeoutExpired:
            SV.kill()
    if NEN:
        shutil.rmtree(NEN, ignore_errors=True)


def goi(duong, pt="GET", body=None, hdr=None):
    """Trả (mã HTTP, thân đã parse, headers). KHÔNG tự động theo cookie — ca thử này chỉ cần
    một lượt, không cần phiên."""
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (CONG, duong), data=d, method=pt)
    r.add_header("X-Requested-With", "VIPHub")
    if d is not None:
        r.add_header("Content-Type", "application/json")
    for k, v in (hdr or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=15) as f:
            b = f.read()
            return f.status, (json.loads(b) if b[:1] == b"{" else b), dict(f.headers)
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, (json.loads(b) if b[:1] == b"{" else b[:200]), dict(e.headers)


def _dong_json():
    """Các dòng JSON trong log máy chủ. Log trộn dòng `[hub] "GET …" 200 -` của
    `BaseHTTPRequestHandler` với dòng JSONL của `quan_sat` — cố ý: dòng cũ giữ nguyên để
    không phá thứ ai đó đang đọc."""
    with open(LOG, encoding="utf-8", errors="replace") as f:
        return [d for d in f.read().splitlines() if d.strip().startswith("{")]


def _dong_yeu_cau():
    ra = []
    for d in _dong_json():
        try:
            o = json.loads(d)
        except ValueError:
            continue
        if o.get("loai") == "yeu_cau":
            ra.append(o)
    return ra


class A_LogCoCauTrucTrenDuongThat(unittest.TestCase):
    """ĐỐI CHỨNG DƯƠNG: log phải có dòng, và dòng phải đúng. Thiếu ca này thì 'đã nối' vẫn
    chỉ là lời khai."""

    def test_a1_route_that_sinh_dong_json(self):
        """Gọi vài route THẬT rồi khẳng định log có > 0 dòng JSON. Đây là ca mà bản trước khi
        vá HỎNG (0 dòng) — và là lý do tệp này tồn tại."""
        goi("/api/v2/suc-khoe")
        goi("/api/v2/san-sang")
        goi("/api/v2/khong-co-duong-nay")
        dj = _dong_json()
        self.assertGreater(len(dj), 0,
                           "log máy chủ có 0 dòng JSON sau 3 lượt HTTP thật — quan sát CHƯA "
                           "được nối vào đường yêu cầu (P-G15-01)")

    def test_a2_moi_dong_yeu_cau_du_truong_va_co_request_id(self):
        goi("/api/v2/suc-khoe")
        d = _dong_yeu_cau()
        self.assertGreater(len(d), 0, "không có dòng `loai=yeu_cau` nào")
        for o in d:
            for truong in ("request_id", "correlation_id", "luc", "pid", "method",
                           "duong", "ma_http", "ms"):
                self.assertIn(truong, o, "dòng thiếu trường %s: %s" % (truong, o))
            self.assertRegex(o["request_id"], r"^[A-Za-z0-9_-]{1,64}$")
            # `ma_http` PHẢI là SỐ, không được là `***`. `quan_sat.che()` dùng DANH SÁCH
            # TRẮNG tên trường, nên đặt sai tên là giá trị bị che — ca này canh đúng chỗ đó.
            self.assertIsInstance(o["ma_http"], int,
                                  "`ma_http` bị che (`%r`) — tên trường không nằm trong "
                                  "quan_sat.TRUONG_CHO_PHEP" % o["ma_http"])

    def test_a3_request_id_tra_ra_header_va_khop_voi_log(self):
        """Đối chiếu được log ↔ yêu cầu là mục đích của cả việc này. Không khớp được thì
        `request_id` chỉ là một chuỗi đẹp."""
        st, _, hdr = goi("/api/v2/suc-khoe")
        self.assertEqual(st, 200)
        rid = hdr.get("X-Request-Id")
        self.assertTrue(rid, "phản hồi THIẾU header X-Request-Id")
        self.assertIn(rid, [o["request_id"] for o in _dong_yeu_cau()],
                      "X-Request-Id=%r không có dòng log nào khớp" % rid)

    def test_a4_luot_HONG_cung_co_dong_log(self):
        """`finally`, không phải cuối đường đi bình thường: lượt 401/404 là lượt cần dấu vết
        nhất. Nếu ai đó đổi `finally` thành lời gọi ở cuối hàm, ca này đỏ."""
        before = len(_dong_yeu_cau())
        st1, _, h1 = goi("/api/v2/don")                      # 401 chưa đăng nhập
        st2, _, h2 = goi("/api/v2/webhook/nhan/khong-co-ma-nay", "POST", {"x": 1})   # 404
        after = _dong_yeu_cau()
        self.assertEqual(st1, 401)
        self.assertEqual(st2, 404)
        self.assertGreaterEqual(len(after) - before, 2, "lượt 401/404 KHÔNG sinh dòng log")
        ma = [o["ma_http"] for o in after[-2:]]
        self.assertIn(401, ma)
        self.assertIn(404, ma)

    def test_a5_duong_dan_khop_that_va_khong_keo_theo_query(self):
        """Dòng log phải mang ĐÚNG đường đã gọi, và phải CẮT query — query có thể mang token."""
        goi("/api/v2/suc-khoe?token=%s" % TOKEN_GIA)
        d = _dong_yeu_cau()
        self.assertTrue(any(o["duong"] == "/api/v2/suc-khoe" for o in d),
                        "không thấy dòng cho /api/v2/suc-khoe")
        self.assertFalse(any(TOKEN_GIA in json.dumps(o, ensure_ascii=False) for o in d),
                         "query (có thể mang token) ĐÃ LỌT vào log")

    def test_a6_body_va_mat_khau_KHONG_lot_vao_log(self):
        """Nối log là mở một đường rò MỚI. Ca này canh đúng đường đó."""
        goi("/api/v2/auth/dang-nhap", "POST",
            {"ten_dang_nhap": "platform-owner", "mat_khau": MK_GIA})
        goi("/api/v2/don", "POST", {"mat_khau": MK_GIA, "ghi_chu": MK_GIA})       # 401
        with open(LOG, encoding="utf-8", errors="replace") as f:
            toan_bo = f.read()
        self.assertNotIn(MK_GIA, toan_bo,
                         "MẬT KHẨU trong body ĐÃ LỌT vào log — đây là lỗi chặn phát hành")
        for o in _dong_yeu_cau():
            self.assertNotIn("mat_khau", o, "dòng log mang trường `mat_khau`")
            self.assertNotIn("headers", o)
            self.assertNotIn("cookie", o)

    def test_a7_dong_log_la_JSONL_parse_duoc_tung_dong(self):
        """Một dòng một JSON: log bị cắt giữa dòng vẫn đọc được các dòng trước."""
        goi("/api/v2/suc-khoe")
        for d in _dong_json():
            try:
                json.loads(d)
            except ValueError as e:
                self.fail("dòng log không parse được: %s | %s" % (e, d[:200]))
            self.assertLess(len(d), 8 * 1024, "một dòng log dài quá giới hạn của bộ đọc")

    def test_a8_phan_hoi_tinh_cung_co_request_id(self):
        """Đường TĨNH đi qua cùng một chỗ (`_chay` → `_phuc_vu_tinh`), nên nó cũng phải có
        header. Nếu ai đó chỉ vá `_tra`, ca này bắt được."""
        st, _, hdr = goi("/admin/")
        self.assertIn(st, (200, 301, 302, 404))
        self.assertTrue(hdr.get("X-Request-Id"),
                        "phản hồi đường TĨNH thiếu X-Request-Id — vá chỉ ở `_tra` là thiếu chỗ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
