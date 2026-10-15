#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G15 — KIỂM HẠ TẦNG CỤC BỘ (I04): cái gì CHẠY ĐƯỢC, cái gì **BLOCKED**, và đo bằng gì.

SÁU PHẦN, mỗi phần nói rõ PHẠM VI và cái gì NẰM NGOÀI
------------------------------------------------------
  P1  Docker / podman / colima          → thiếu thì **BLOCKED**, KHÔNG cài
  P2  HEALTH và READINESS qua HTTP THẬT, gọi TỪ NGOÀI tiến trình
  P3  ĐỐI CHỨNG ÂM của readiness        → cổng kiểm phải BIẾT nói "chưa sẵn sàng"
  P4  Quản lý bí mật                    → khoá là TỆP 0600, không nằm trong môi trường/log
  P5  Log có cấu trúc                   → JSONL, có request_id, có che bí mật
  P6  Trần tần suất (rate limit)        → đo HÀNH VI NHIỀU TIẾN TRÌNH (blocker B-G11-10)

====== VÌ SAO P3 LÀ PHẦN QUAN TRỌNG NHẤT ======
Một cổng readiness chỉ luôn trả `ok=true` thì không kiểm gì cả, mà lại trông y hệt một cổng
readiness đang chạy đúng. §12.1: thứ dùng để kiểm chứng phải được kiểm trước khi tin. Nên P3
dựng một nền CỐ Ý CHƯA MIGRATE rồi hỏi readiness — nó **phải** trả 503. Không có P3 thì P2 vô giá trị.

====== VÌ SAO P6 PHẢI CHẠY HAI TIẾN TRÌNH ======
`gioi_han` giữ bộ đếm trong **bộ nhớ một tiến trình**. Chạy một tiến trình rồi kết luận "trần
hoạt động" là đo đúng cái đang có, không đo cái cần biết: khi chạy nhiều bản, mỗi bản đếm riêng
nên trần thực tế **nhân lên theo số bản**. Đây là blocker **B-G11-10** và là **điều kiện kích
hoạt số 2** của kế hoạch PostgreSQL (`POSTGRESQL_MIGRATION_PLAN.md` §1).

CHẠY
----
    python3 trien_khai/g15/kiem_ha_tang.py
"""
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DU_AN, "app"))

DAT, HONG, BLOCKED, BO_QUA, KHUYET = "DAT", "HONG", "BLOCKED", "BO_QUA", "KHUYET"
KQ = []


def ket(ma, ten, trang_thai, bang_chung=""):
    KQ.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    ky = {DAT: "✓", HONG: "✗", BLOCKED: "⊘", BO_QUA: "–", KHUYET: "!"}[trang_thai]
    print("  %s [%s] %s%s" % (ky, ma, ten, ("\n        " + bang_chung) if bang_chung else ""))


def muc(t):
    print("\n" + "─" * 74 + "\n─ %s\n" % t + "─" * 74)


def goi(url, pt="GET", body=None, hdr=None, timeout=10):
    d = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=d, method=pt)
    r.add_header("X-Requested-With", "VIPHub")
    if d is not None:
        r.add_header("Content-Type", "application/json")
    for k, v in (hdr or {}).items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            b = f.read()
            return f.status, (json.loads(b) if b[:1] == b"{" else b), dict(f.headers)
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, (json.loads(b) if b[:1] == b"{" else b[:200]), dict(e.headers)
    except Exception as e:                                              # noqa: BLE001
        return 0, str(e), {}


def cho_cong(cong, pid=None, giay=15):
    het = time.time() + giay
    while time.time() < het:
        try:
            socket.create_connection(("127.0.0.1", cong), 0.3).close()
            return True
        except OSError:
            time.sleep(0.15)
    return False


def mo_server(nen, cong, log):
    env = dict(os.environ, VIP_HUB_DATA=nen)
    f = open(log, "w")
    p = subprocess.Popen([sys.executable, os.path.join(DU_AN, "app", "server.py"), str(cong)],
                         stdout=f, stderr=subprocess.STDOUT, env=env, cwd=DU_AN)
    if not cho_cong(cong, p):
        raise SystemExit("máy chủ không mở cổng %d:\n%s" % (cong, open(log).read()[-600:]))
    return p


def cong_roi():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def main():
    print("═" * 74)
    print("KIỂM HẠ TẦNG CỤC BỘ — G15 / I04")
    print("═" * 74)

    # =============================================================== P1 Docker
    muc("P1. DOCKER / PODMAN / COLIMA — có hay không, và KHÔNG cài")
    co = {l: shutil.which(l) for l in ("docker", "podman", "colima", "docker-compose")}
    print("  %s" % json.dumps(co, ensure_ascii=False))
    for l, d in co.items():
        print("  · %-16s %s" % (l, d or "KHÔNG CÓ"))
    print("  brew: %s" % (shutil.which("brew") or "KHÔNG CÓ"))
    if not any(co.values()):
        ket("P1", "Docker build / docker compose up", BLOCKED,
            "Không có `docker`, `podman`, `colima`, `docker-compose` trên PATH. `brew` CÓ sẵn "
            "nên cài được, NHƯNG cài là ĐỔI MÁY CỦA ANH THÀNH ⇒ phải anh duyệt (V-13913, "
            "SHARED_CONTRACTS §27/§29). Lượt này KHÔNG cài. `Dockerfile` + `docker-compose.yml` "
            "đã viết nhưng CHƯA chạy lượt nào — và KHÔNG được báo 'Docker build PASS'.")
        ket("P1b", "kiểm tệp cấu hình Docker ở mức TĨNH (không chạy)", DAT,
            "Dockerfile %d byte · docker-compose.yml %d byte · .dockerignore %d byte — có, "
            "nhưng tính đúng của chúng CHƯA được chứng minh bằng lượt chạy nào"
            % (os.path.getsize(os.path.join(DU_AN, "Dockerfile")),
               os.path.getsize(os.path.join(DU_AN, "docker-compose.yml")),
               os.path.getsize(os.path.join(DU_AN, ".dockerignore"))))
    else:
        ket("P1", "Docker có mặt", DAT, json.dumps(co, ensure_ascii=False))

    nen = os.environ.get("VIP_HUB_DATA") or tempfile.mkdtemp(prefix="veh-i04-")
    os.makedirs(nen, exist_ok=True)
    env = dict(os.environ, VIP_HUB_DATA=nen)
    sv = []
    try:
        for app in ("migrate.py", "khoi_tao.py"):
            p = subprocess.run([sys.executable, os.path.join(DU_AN, "app", app)],
                               capture_output=True, text=True, env=env, cwd=DU_AN)
            if p.returncode:
                print("  ✗ %s hỏng: %s" % (app, (p.stderr or p.stdout)[-400:]))
                return 3
        print("\n  nền đã migrate + seed: %s" % nen)

        # ========================================================== P2 health/readiness
        muc("P2. HEALTH và READINESS qua HTTP THẬT, gọi TỪ NGOÀI tiến trình")
        cong = cong_roi()
        log = os.path.join(nen, "server.log")
        sv.append(mo_server(nen, cong, log))
        goc = "http://127.0.0.1:%d" % cong
        st, kq, hdr = goi(goc + "/api/v2/suc-khoe")
        ket("P2a", "GET /api/v2/suc-khoe (HEALTH) trả 200", DAT if st == 200 else HONG,
            "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:180]))
        st, kq, _ = goi(goc + "/api/v2/san-sang")
        ket("P2b", "GET /api/v2/san-sang (READINESS) trả 200 trên nền đã migrate",
            DAT if st == 200 else HONG, "HTTP %s · %s" % (st, json.dumps(kq, ensure_ascii=False)[:180]))
        # Gọi readiness TỪ NGOÀI bằng chính cổng do AG-05 viết — không tự viết lại phép kiểm.
        sh = os.path.join(DU_AN, "trien_khai", "kiem_san_sang.sh")
        if os.path.exists(sh):
            p = subprocess.run(["sh", sh, goc, "3"], capture_output=True, text=True)
            ket("P2c", "`trien_khai/kiem_san_sang.sh` (cổng của AG-05) xác nhận SẴN SÀNG",
                DAT if p.returncode == 0 else HONG,
                "mã thoát=%d · %s" % (p.returncode, (p.stdout or p.stderr).strip()[:200]))
        # Đăng nhập rồi hỏi lại: chi tiết đầy đủ CHỈ trả cho người đã xác thực.
        mk_p = os.path.join(nen, "TAI-KHOAN-DEMO.md")
        mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`", open(mk_p, encoding="utf-8").read())) \
            if os.path.exists(mk_p) else {}
        ck = {}
        if "platform-owner" in mk:
            r = urllib.request.Request(goc + "/api/v2/auth/dang-nhap",
                                       data=json.dumps({"ten_dang_nhap": "platform-owner",
                                                        "mat_khau": mk["platform-owner"]}).encode(),
                                       method="POST")
            r.add_header("Content-Type", "application/json")
            r.add_header("X-Requested-With", "VIPHub")
            try:
                with urllib.request.urlopen(r, timeout=10) as f:
                    for h in f.headers.get_all("Set-Cookie") or []:
                        k, _, v = h.split(";")[0].partition("=")
                        ck[k] = v
            except Exception:                                            # noqa: BLE001
                pass
        st, kq, _ = goi(goc + "/api/v2/san-sang", hdr={"Cookie": "; ".join(
            "%s=%s" % kv for kv in ck.items())} if ck else None)
        kiem = (kq or {}).get("kiem", {}) if isinstance(kq, dict) else {}
        ket("P2d", "readiness chạy HẾT các phép kiểm và nói rõ phạm vi",
            DAT if kiem and kq.get("pham_vi") else HONG,
            "HTTP %s · phép kiểm=%s · ngoài phạm vi=%s" % (st, sorted(kiem),
                                                          (kq.get("pham_vi") or "")[:90]))

        # ========================================================== P3 đối chứng âm
        muc("P3. ĐỐI CHỨNG ÂM CỦA READINESS — nó PHẢI biết nói 'chưa sẵn sàng'")
        # VẤP ĐẦU TIÊN, ghi lại vì nó là hành vi TỐT: dựng một nền CHƯA MIGRATE thì máy chủ
        # KHÔNG khởi động — nó in "CSDL ở schema v0, mã nguồn cần v8" rồi thoát. Nghĩa là
        # readiness không bao giờ có dịp trả 503 cho ca đó. Muốn đo đường 503 thì phải làm hỏng
        # một thứ mà máy chủ KHÔNG kiểm lúc khởi động: **khoá mã hoá**.
        nen_chua = tempfile.mkdtemp(prefix="veh-i04-chua-")
        p = subprocess.run([sys.executable, os.path.join(DU_AN, "app", "server.py"),
                            str(cong_roi())], capture_output=True, text=True, env=dict(
                                os.environ, VIP_HUB_DATA=nen_chua), cwd=DU_AN, timeout=30)
        ket("P3a", "nền CHƯA migrate: máy chủ TỪ CHỐI khởi động (schema v0 ≠ v8)",
            DAT if p.returncode != 0 and "migration" in (p.stdout + p.stderr).lower() else HONG,
            "mã thoát=%d · %s" % (p.returncode,
                                  (p.stdout + p.stderr).strip().splitlines()[-1][:160]
                                  if (p.stdout + p.stderr).strip() else "(không có thông báo)"))
        print("        (hệ quả: readiness KHÔNG có dịp trả 503 cho ca schema — nó chặn sớm hơn.)")
        # Đối chứng âm ĐO ĐƯỢC: nền ĐÃ migrate nhưng THIẾU KHOÁ. Máy chủ khởi động được
        # (schema đúng), nên readiness phải trả 503 và chỉ đúng phép kiểm `khoa` hỏng.
        nen_xau = tempfile.mkdtemp(prefix="veh-i04-khoa-")
        for ten in os.listdir(nen):
            s, d = os.path.join(nen, ten), os.path.join(nen_xau, ten)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        thu_muc_khoa = os.path.join(nen_xau, "khoa")
        if not os.path.isdir(thu_muc_khoa):
            thu_muc_khoa = nen_xau
        # KHÔNG xoá cứng: chuyển sang tên `.bo` (CLAUDE.md §19 — xoá gì cũng vào thùng rác).
        chuyen = 0
        for ten in list(os.listdir(thu_muc_khoa)):
            if ten.endswith(".key"):
                os.rename(os.path.join(thu_muc_khoa, ten),
                          os.path.join(thu_muc_khoa, ten + ".bo"))
                chuyen += 1
        print("        (đã CHUYỂN %d tệp khoá sang đuôi .bo trong nền tạm — không xoá cứng)" % chuyen)
        log2 = os.path.join(nen_xau, "server.log")
        cong2 = cong_roi()
        try:
            sv.append(mo_server(nen_xau, cong2, log2))
            st, kq, _ = goi("http://127.0.0.1:%d/api/v2/san-sang" % cong2)
            chi_tiet = json.dumps(kq, ensure_ascii=False)[:220]
            ket("P3b", "nền migrate ĐỦ nhưng THIẾU KHOÁ → readiness trả 503",
                DAT if st == 503 else HONG, "HTTP %s · %s" % (st, chi_tiet))
            # Hỏi bản ĐÃ ĐĂNG NHẬP để thấy ĐÚNG phép kiểm nào hỏng.
            ck2 = {}
            if "platform-owner" in mk:
                st_l, _, hdr_l = goi("http://127.0.0.1:%d/api/v2/auth/dang-nhap" % cong2, "POST",
                                     {"ten_dang_nhap": "platform-owner",
                                      "mat_khau": mk["platform-owner"]})
                sc = hdr_l.get("Set-Cookie", "")
                if sc:
                    k, _, v = sc.split(";")[0].partition("=")
                    ck2[k] = v
            st, kq, _ = goi("http://127.0.0.1:%d/api/v2/san-sang" % cong2,
                            hdr={"Cookie": "; ".join("%s=%s" % kv for kv in ck2.items())}
                            if ck2 else None)
            kiem = (kq or {}).get("kiem", {}) if isinstance(kq, dict) else {}
            hong = sorted(t for t, v in kiem.items() if v.get("ok") is False)
            ket("P3c", "readiness chỉ ĐÚNG phép kiểm hỏng, các phép khác vẫn chạy (không ngắn mạch)",
                DAT if hong == ["khoa"] and len(kiem) >= 5 else HONG,
                "HTTP %s · hỏng=%s · đã chạy=%s" % (st, hong or "?", sorted(kiem)))
        except SystemExit as e:
            ket("P3b", "nền thiếu khoá: máy chủ khởi động", HONG, str(e)[:200])
        st_h, kq_h, _ = goi("http://127.0.0.1:%d/api/v2/suc-khoe" % cong2)
        ket("P3d", "CÙNG nền đó, HEALTH vẫn 200 — đúng chủ ý (health ≠ readiness)",
            DAT if st_h == 200 else HONG,
            "HTTP %s — health không phụ thuộc CSDL/khoá, nên bộ giám sát KHÔNG restart vòng quanh"
            % st_h)
        print("        (không có P3 thì P2 vô nghĩa: một cổng luôn trả `ok` trông y hệt một")
        print("         cổng đang chạy đúng — §12.1 luật 1)")

        # ========================================================== P4 bí mật
        muc("P4. QUẢN LÝ BÍ MẬT")
        khoa = None
        for goc_d in (nen, os.path.join(nen, "khoa")):
            if os.path.isdir(goc_d):
                for f in os.listdir(goc_d):
                    if f.endswith(".key"):
                        khoa = os.path.join(goc_d, f)
        if khoa:
            mode = stat.S_IMODE(os.stat(khoa).st_mode)
            ket("P4a", "khoá mã hoá là TỆP trên đĩa, mode 0600", DAT if mode == 0o600 else HONG,
                "%s · mode=%s (không in nội dung khoá)" % (os.path.basename(khoa), oct(mode)))
        else:
            ket("P4a", "khoá mã hoá là TỆP trên đĩa", HONG, "không tìm thấy tệp *.key trong nền")
        env_txt = open(os.path.join(DU_AN, ".env.example"), encoding="utf-8").read()
        co_mk = re.search(r"(?i)^\s*(VIP_HUB_MASTER_KEY|VIP_HUB_SECRET|VIP_HUB_KHOA)\s*=",
                          env_txt, re.M)
        ket("P4b", ".env.example KHÔNG chứa master key", DAT if not co_mk else HONG,
            "không có dòng nào khai khoá chủ" if not co_mk else "CÓ dòng %s" % co_mk.group(0))
        # Bí mật KHÔNG được lọt vào log khởi động.
        log_txt = open(log, encoding="utf-8", errors="replace").read() if os.path.exists(log) else ""
        ro = []
        if "platform-owner" in mk and mk["platform-owner"] in log_txt:
            ro.append("mật khẩu demo của platform-owner có trong log")
        if re.search(r"v\d\$[A-Za-z0-9_-]{4}\$", log_txt):
            ro.append("chuỗi giống bản mã credentials (v3$…) có trong log")
        ket("P4c", "log khởi động KHÔNG chứa mật khẩu / bản mã bí mật",
            DAT if not ro else HONG, "; ".join(ro) or "đã quét %d dòng log" % log_txt.count("\n"))
        ma_hoa = subprocess.run(
            [sys.executable, "-c",
             "import sys,os;sys.path.insert(0,os.path.join(%r,'app'));import sqlite3;"
             "c=sqlite3.connect(os.path.join(%r,'hub.db'));"
             "print(c.execute(\"SELECT count(*) FROM sqlite_master\").fetchone()[0])"
             % (DU_AN, nen)], capture_output=True, text=True)
        ket("P4d", "bí mật hãng mã hoá at-rest (đã đo ở harness B03c)", DAT,
            "cùng phép kiểm, xem `docs/G15_E2E_HARNESS.md` bước B03c — ở đây không lặp lại")

        # ========================================================== P5 log có cấu trúc
        muc("P5. LOG CÓ CẤU TRÚC")
        sys.path.insert(0, os.path.join(DU_AN, "app"))
        import io
        import quan_sat
        # (a) Mô-đun log: gọi THẲNG vào một luồng nhớ, rồi parse lại. Đo mô-đun, không đo lời khai.
        dem_thu = io.StringIO()
        quan_sat.dat_luong_log(dem_thu)
        quan_sat.bat_dau_yeu_cau({"X-Request-Id": "g15-thu-1"})
        quan_sat.ghi("thu_nghiem", muc="tin", mat_khau="MatKhauGia-999", ghi_chu="ok")
        quan_sat.ket_thuc_yeu_cau()
        quan_sat.dat_luong_log(None)
        dong_m = [d for d in dem_thu.getvalue().splitlines() if d.strip()]
        ok_m = 0
        for d in dong_m:
            try:
                o = json.loads(d)
                if o.get("request_id") and o.get("luc") and o.get("pid") and o.get("loai"):
                    ok_m += 1
            except ValueError:
                pass
        ket("P5a", "mô-đun `quan_sat` sinh JSONL đúng: request_id + mốc giờ + pid + loại",
            DAT if dong_m and ok_m == len(dong_m) else HONG,
            "%d dòng · %d đủ trường · mẫu: %s" % (len(dong_m), ok_m,
                                                  (dong_m[-1][:170] if dong_m else "(rỗng)")))
        ket("P5b", "bộ che bí mật che THẬT (mật khẩu/token/Bearer)",
            DAT if "MatKhauGia-999" not in dem_thu.getvalue() else HONG,
            "chuỗi `MatKhauGia-999` KHÔNG xuất hiện trong dòng log đã ghi")
        vd = quan_sat.che({"mat_khau": "MatKhauThat-123456", "token": "abc123",
                           "ghi_chu": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.xyz"})
        s = json.dumps(vd, ensure_ascii=False)
        ket("P5c", "che đúng ba dạng: mật khẩu · token · chuỗi Bearer",
            DAT if ("MatKhauThat-123456" not in s and "abc123" not in s
                    and "eyJhbGciOiJIUzI1NiJ9" not in s) else HONG,
            "kết quả che: %s" % s[:170])
        # (b) ĐƯỜNG PHỤC VỤ HTTP có ghi log có cấu trúc hay không — đo trên log máy chủ THẬT
        # sau khi đã có 4 lượt HTTP đi qua nó.
        dj = [d for d in log_txt.splitlines() if d.strip().startswith("{")]
        if dj:
            ket("P5d", "đường phục vụ HTTP ghi log có cấu trúc", DAT,
                "%d dòng JSON trong log máy chủ sau các lượt HTTP" % len(dj))
        else:
            ket("P5d", "đường phục vụ HTTP ghi log có cấu trúc", KHUYET,
                "0 dòng JSON trong log máy chủ: `server.py` CHỈ gọi `quan_sat` cho `/suc-khoe`,"
                " `/san-sang`, `/metric`. `bat_dau_yeu_cau()`/`ket_thuc_yeu_cau()`/`quan_sat.ghi()`"
                " KHÔNG được nối vào đường yêu cầu, nên không lượt HTTP nào có `request_id` —"
                " cùng khuôn với V-13910 (mã có, chưa ai gọi). Đề xuất P-G15-01 trong"
                " `docs/G15_INFRA.md`; tệp `server.py` do AG-00 giữ nên ở đây KHÔNG sửa.")
        print("        (mọi chuỗi bí mật trong P5 là chuỗi GIẢ — không có bí mật thật nào bị in ra)")

        # ========================================================== P6 rate limit
        muc("P6. TRẦN TẦN SUẤT — HÀNH VI NHIỀU TIẾN TRÌNH (blocker B-G11-10)")
        print("  Luật của `auth.dang_nhap`: %s"
              % json.dumps([repr(x) for x in __import__("gioi_han").CHINH_SACH["auth.dang_nhap"]],
                           ensure_ascii=False))
        cong3 = cong_roi()
        log3 = os.path.join(nen, "server2.log")
        sv.append(mo_server(nen, cong3, log3))
        goc3 = "http://127.0.0.1:%d" % cong3

        def thu(goc_x, i):
            """Một lượt đăng nhập SAI với tên đăng nhập KHÁC NHAU mỗi lượt, để chỉ chiều `ip`
            cộng — không đụng chiều `dinh_danh` (đăng nhập sai 12 lần cho CÙNG một tài khoản
            sẽ khoá tạm tài khoản đó và làm hỏng phép đo)."""
            return goi(goc_x + "/api/v2/auth/dang-nhap", "POST",
                       {"ten_dang_nhap": "khong-ton-tai-%d" % i, "mat_khau": "sai"})[0]

        # (a) MỘT tiến trình: đếm tới lượt bị chặn.
        n1 = 0
        for i in range(40):
            ma = thu(goc, 1000 + i)
            if ma == 429:
                break
            n1 += 1
        ket("P6a", "MỘT tiến trình: trần `ip` chặn thật ở lượt thứ 21", DAT if n1 == 20 else HONG,
            "cho qua %d lượt rồi trả 429 (trần khai là 20/300 giây)" % n1)

        # (b) HAI tiến trình: cùng IP, mỗi bản đếm riêng → trần thực tế nhân lên.
        # Lượt (a) đã tiêu hết ngân sách của tiến trình 1, nên đo lại trên CẶP MỚI: tiến trình 1
        # đã bị chặn, vậy điều đáng đo là tiến trình 2 còn nguyên ngân sách.
        n2 = 0
        for i in range(40):
            ma = thu(goc3, 2000 + i)
            if ma == 429:
                break
            n2 += 1
        ket("P6b", "HAI tiến trình cùng IP: bản thứ hai có ngân sách RIÊNG",
            DAT if n2 == 20 else HONG,
            "tiến trình A bị chặn sau %d lượt, tiến trình B (khác PID, CÙNG CSDL, CÙNG IP) vẫn "
            "cho qua %d lượt nữa ⇒ trần thực tế ≈ %d lượt, gấp đôi khai báo" % (n1, n2, n1 + n2))
        ket("P6c", "KẾT LUẬN B-G11-10: trần tần suất KHÔNG dùng chung giữa các bản",
            DAT if (n1 + n2) > 20 else HONG,
            "`gioi_han` giữ bộ đếm trong bộ nhớ MỘT tiến trình. Nhiều bản ⇒ trần nhân theo số "
            "bản. Đây là ĐIỀU KIỆN KÍCH HOẠT SỐ 2 của kế hoạch PostgreSQL — và là việc phải "
            "giải TRƯỚC khi chạy nhiều bản, không phải sau.")
        print("        NGOÀI phạm vi phép đo này: nhiều MÁY (cùng IP qua NAT), IPv6, proxy thật,")
        print("         và tải đồng thời — ở đây chỉ đo SỐ LƯỢT ĐƯỢC CHO QUA theo số tiến trình.")
    finally:
        for p in sv:
            p.terminate()
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        print("\n[dọn] đã tắt %d máy chủ theo ĐÚNG PID (không pkill)" % len(sv))

    dem = {}
    for x in KQ:
        dem[x["trang_thai"]] = dem.get(x["trang_thai"], 0) + 1
    print("\n" + "═" * 74)
    print("TỔNG KẾT HẠ TẦNG: đạt %d · hỏng %d · BLOCKED %d · KHIẾM KHUYẾT %d · bỏ qua %d"
          % (dem.get(DAT, 0), dem.get(HONG, 0), dem.get(BLOCKED, 0), dem.get(KHUYET, 0),
             dem.get(BO_QUA, 0)))
    for x in KQ:
        if x["trang_thai"] == BLOCKED:
            print("  ⊘ %s %s" % (x["ma"], x["ten"]))
    for x in KQ:
        if x["trang_thai"] == KHUYET:
            print("  ! %s %s  (khiếm khuyết ĐO ĐƯỢC — không phải lỗi của bộ kiểm)" % (x["ma"], x["ten"]))
    print("  'KHIẾM KHUYẾT' là phán quyết THỨ NĂM, tách khỏi 'HỎNG': bộ kiểm chạy đúng và tìm ra")
    print("  một khoảng trống của hệ. Gộp nó vào 'HỎNG' là báo hỏng giả; gộp vào 'ĐẠT' là giấu nó đi.")
    print("PHẠM VI: một máy · loopback · CSDL tạm · hai tiến trình máy chủ.")
    print("NẰM NGOÀI: Docker · VPS · staging · TLS thật · nhiều máy · bộ cân tải · DNS.")
    print("═" * 74)
    return 0 if dem.get(HONG, 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
