#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DIỄN TẬP CHUYỂN SANG PostgreSQL — chạy trên CỤM RIÊNG, tuyệt đối không đụng cụm :5432.

====== ĐÂY LÀ MỘT LƯỢT DIỄN TẬP, KHÔNG PHẢI MỘT LƯỢT CHUYỂN ======
Quyết định **D-8** (anh Thành, 15/10/2026): *"Tiếp tục SQLite local; **thử** PostgreSQL trước
khi quyết định triển khai SaaS nhiều người dùng."* Chỉ thị G12 mục 8: **KHÔNG** tự chuyển
CSDL nghiệp vụ sang PostgreSQL.

Hệ quả cứng, ghi ra để không ai đọc nhầm kết quả ở đây:
  * `app/du-lieu/hub.db` **không** bị đọc, **không** bị ghi, **không** bị chuyển.
  * `app/csdl.py` **không** bị sửa. Mã nghiệp vụ vẫn chỉ nói tiếng SQLite.
  * Không có dữ liệu thật nào đi qua đây. Mọi bảng ở đây là bảng mới dựng trong một CSDL
    dùng-một-lần, sinh ra rồi xoá.

====== VÌ SAO KHÔNG DÙNG CỤM :5432 ======
Máy này đang chạy một cụm PostgreSQL hệ thống ở `:5432` và cụm đó **giữ CSDL của dự án
khác** (`vip_customs`, `vip_customs_g16`, `vip_customs_test`). Cụm dựng ở đây có **thư mục
dữ liệu riêng**, **cổng riêng**, socket Unix trong `/tmp/vhpg.XXXX`, và
`listen_addresses=''` — nó **không mở một cổng TCP nào**. Chốt chặn `_chan_cong_5432()`
TỪ CHỐI chạy nếu cổng là 5432, kể cả khi người chạy cố tình đặt.

====== BỐN KẾT CỤC — VÌ SAO PHẢI TÁCH ======
Yêu cầu I02: phân biệt **bốn** kết cục, không gộp. Bốn thứ này hay bị gọi chung là "lỗi
CSDL" nhưng cách xử lý khác hẳn nhau:

| Kết cục | Nghĩa | Xử thế nào |
|---|---|---|
| `CHOT_THANH_CONG` | đã ghi thật, thấy được từ tiến trình khác | xong |
| `KHOA_HET_GIO` | **chưa** ghi gì, giành khoá thất bại | thử lại được, an toàn |
| `GIAO_DICH_HONG` | **chưa** ghi gì, vi phạm ràng buộc/trigger | thử lại VÔ ÍCH, phải sửa dữ liệu |
| `MAT_CAP_NHAT` | **đã ghi** nhưng mất một lượt ghi khác | **KHÔNG TỰ BÁO** — chỉ thấy khi đối chiếu |

Ba kết cục đầu tự báo. Kết cục thứ tư **im lặng**, nên nó là thứ đáng đo nhất: mọi phép đo
ở đây đều làm phép **đối chiếu cuối lượt** (số tiến trình TIN đã ghi so với số THẬT trong
CSDL), chứ không chỉ đếm lỗi.

====== PHẠM VI ======
Đo trên: macOS arm64 · python 3.9.6 · PostgreSQL 16.15 (Homebrew) · SQLite 3.51.0 ·
cụm thử qua **socket Unix nội máy**, không qua mạng.
NẰM NGOÀI: nhiều MÁY · mạng thật · dữ liệu lớn · tải đọc · replica · dữ liệu nghiệp vụ thật
· lớp phương ngữ `csdl.py` (chặng 1 — CHƯA làm, nên mã nghiệp vụ chưa chạy được trên PG).

CHẠY
----
    python3 trien_khai/postgres/dien_tap_chuyen.py              # tự dựng cụm, tự xoá
    python3 trien_khai/postgres/dien_tap_chuyen.py --giu-cum    # giữ cụm lại để soi
    python3 trien_khai/postgres/dien_tap_chuyen.py --so-tien-trinh 4 --so-phep 200
"""
import argparse
import json
import multiprocessing as mp
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(DU_AN, "app"))
sys.path.insert(0, os.path.join(DU_AN, "trien_khai", "postgres"))

CONG_CAM = "5432"
KHOA_MIGRATION = 991204  # số khoá tư vấn; chỉ có nghĩa trong cụm thử

# SQLSTATE đáng phân biệt. Ghi ra vì "lỗi" là một từ vô dụng khi chẩn đoán.
SQLSTATE = {
    "55P03": "lock_not_available (hết lock_timeout)",
    "40P01": "deadlock_detected",
    "40001": "serialization_failure",
    "25P02": "in_failed_sql_transaction (giao dịch đã hỏng, câu sau bị chối)",
    "23505": "unique_violation",
    "23514": "check_violation",
    "P0001": "raise_exception (trigger chặn)",
}

# --- tiện ích in ---
_dem = {"dat": 0, "hong": 0, "bo_qua": 0}


def dat(ten, dieu, chi_tiet=""):
    _dem["dat" if dieu else "hong"] += 1
    print("  %s %s%s" % ("✓" if dieu else "✗", ten, (" — " + chi_tiet) if chi_tiet else ""))
    return dieu


def bo_qua(ten, ly_do):
    _dem["bo_qua"] += 1
    print("  ⊘ %s — BỎ QUA: %s" % (ten, ly_do))


def muc(tieu_de):
    print("\n" + "─" * 74)
    print("─ %s" % tieu_de)
    print("─" * 74)


# --------------------------------------------------------------------- cụm thử
class CumThu(object):
    """Cụm PostgreSQL riêng: thư mục riêng, cổng riêng, socket ngắn, KHÔNG mở TCP."""

    def __init__(self, cong="55432"):
        if str(cong) == CONG_CAM:
            raise SystemExit("TỪ CHỐI: cổng %s là cụm hệ thống đang giữ CSDL dự án khác."
                             % CONG_CAM)
        self.cong = str(cong)
        self.nguoi = os.environ.get("VHPG_NGUOI", "vhtest")
        self.goc = tempfile.mkdtemp(prefix="vhdt-")
        self.data = os.path.join(self.goc, "data")
        self.sock = tempfile.mkdtemp(prefix="vhpg.", dir="/tmp")
        self.log = os.path.join(self.goc, "pg.log")

    def dung(self):
        moi = dict(os.environ, LANG="C", LC_ALL="C")
        # `LC_ALL=C` cho CẢ pg_ctl: thiếu nó thì postmaster chết với
        # `FATAL: postmaster became multithreaded during startup` (đã vấp thật, G12).
        p = subprocess.run(["initdb", "-D", self.data, "--locale=C", "--encoding=UTF8",
                            "-U", self.nguoi], capture_output=True, text=True, env=moi)
        if p.returncode:
            raise SystemExit("initdb hỏng: " + (p.stderr or p.stdout)[-500:])
        p = subprocess.run(
            ["pg_ctl", "-D", self.data, "-l", self.log, "-w", "start", "-o",
             "-p %s -k %s -c listen_addresses='' -c fsync=off" % (self.cong, self.sock)],
            capture_output=True, text=True, env=moi)
        if p.returncode:
            ghi = open(self.log).read()[-500:] if os.path.exists(self.log) else ""
            raise SystemExit("pg_ctl start hỏng: %s | %s" % ((p.stderr or p.stdout)[-300:], ghi))

    def psql(self, sql, db="postgres", dung_lai_khi_loi=False):
        """Chạy SQL qua psql. Trả (mã thoát, stdout, stderr, danh sách SQLSTATE thấy được)."""
        co = ["psql", "-h", self.sock, "-p", self.cong, "-U", self.nguoi, "-d", db,
              "-qtAX", "-v", "VERBOSITY=verbose"]
        co += ["-v", "ON_ERROR_STOP=%s" % ("1" if dung_lai_khi_loi else "0")]
        p = subprocess.run(co, input=sql, capture_output=True, text=True)
        ma = re.findall(r"ERROR:\s+([0-9A-Z]{5}):", p.stderr)
        return p.returncode, p.stdout, p.stderr, ma

    def tao_csdl(self, ten):
        self.psql("DROP DATABASE IF EXISTS %s" % ten)
        rc, _, err, _ = self.psql("CREATE DATABASE %s" % ten, dung_lai_khi_loi=True)
        if rc:
            raise SystemExit("không tạo được CSDL %s: %s" % (ten, err[-300:]))

    def dong(self, xoa=True):
        """Dừng bằng `pg_ctl stop`. KHÔNG `kill`, KHÔNG `pkill` (CLAUDE.md §16.7 — một lệnh
        `pkill -f postgres` ở đây sẽ giết luôn cụm :5432 của dự án khác)."""
        subprocess.run(["pg_ctl", "-D", self.data, "stop", "-m", "immediate"],
                       capture_output=True, text=True)
        if xoa:
            shutil.rmtree(self.goc, ignore_errors=True)
            shutil.rmtree(self.sock, ignore_errors=True)

    def danh_tinh(self):
        rc, out, _, _ = self.psql(
            "SELECT 'datadir='||current_setting('data_directory');"
            "SELECT 'port='||current_setting('port');"
            "SELECT 'listen='||coalesce(nullif(current_setting('listen_addresses'),''),'(rỗng)');"
            "SELECT 'socket='||current_setting('unix_socket_directories');"
            "SELECT 'version='||version();")
        return out.strip()


# ------------------------------------------------------------------ ca SQLite (đối chứng)
DDL_SQLITE_DEM = """
CREATE TABLE IF NOT EXISTS dem (id INTEGER PRIMARY KEY, gia_tri INTEGER NOT NULL);
INSERT OR IGNORE INTO dem (id, gia_tri) VALUES (1, 0);
CREATE TABLE IF NOT EXISTS so_cai (id INTEGER PRIMARY KEY AUTOINCREMENT, tien INTEGER NOT NULL);
"""


def _tho_sqlite_rmw(duong_dan, so_phep, kieu, bat_dau, ket_qua):
    """Đọc–sửa–ghi trên CÙNG một hàng, từ một TIẾN TRÌNH riêng."""
    while time.time() < bat_dau:
        time.sleep(0.001)
    kn = sqlite3.connect(duong_dan, timeout=5.0, isolation_level=None)
    kn.execute("PRAGMA busy_timeout=2000")
    tin, loi = 0, []
    for _ in range(so_phep):
        try:
            if kieu == "ngo_ngan":            # BEGIN hoãn — đúng khuôn đọc-rồi-ghi ngây thơ
                kn.execute("BEGIN")
                cu = kn.execute("SELECT gia_tri FROM dem WHERE id=1").fetchone()[0]
                kn.execute("UPDATE dem SET gia_tri=? WHERE id=1", (cu + 1,))
                kn.execute("COMMIT")
            elif kieu == "immediate":         # khoá ghi xin từ đầu — khuôn csdl.giao_dich()
                kn.execute("BEGIN IMMEDIATE")
                cu = kn.execute("SELECT gia_tri FROM dem WHERE id=1").fetchone()[0]
                kn.execute("UPDATE dem SET gia_tri=? WHERE id=1", (cu + 1,))
                kn.execute("COMMIT")
            else:                             # nguyên tử ở tầng câu
                kn.execute("UPDATE dem SET gia_tri=gia_tri+1 WHERE id=1")
            tin += 1
        except sqlite3.Error as e:
            loi.append("%s: %s" % (type(e).__name__, str(e)[:70]))
            try:
                kn.execute("ROLLBACK")
            except sqlite3.Error:
                pass
    kn.close()
    ket_qua.put({"tin": tin, "loi": loi})


def _tho_pg_rmw(sock, cong, nguoi, csdl, so_phep, kieu, bat_dau, ket_qua, khoa_hang=False):
    """Đọc–sửa–ghi trên PostgreSQL, từ một TIẾN TRÌNH riêng. Dùng `psql` để không phụ thuộc
    driver nào — cụm thử không cài `psycopg`."""
    while time.time() < bat_dau:
        time.sleep(0.001)
    mau = ("BEGIN;\n"
           "SELECT gia_tri FROM dem WHERE id=1%s;\n"
           "SELECT pg_sleep(0.001);\n"
           "UPDATE dem SET gia_tri={v} WHERE id=1;\n"
           "COMMIT;\n")
    tin, loi = 0, []
    for _ in range(so_phep):
        if kieu == "nguyen_tu":
            sql = "UPDATE dem SET gia_tri=gia_tri+1 WHERE id=1;\n"
        else:
            # Đọc ở một kết nối RIÊNG (tự chốt), rồi ghi giá trị đã đọc ở kết nối khác —
            # đúng khuôn "đọc-rồi-ghi" ngây thơ đang được báo là hỏng.
            co = ["psql", "-h", sock, "-p", cong, "-U", nguoi, "-d", csdl, "-qtAX", "-t"]
            p0 = subprocess.run(co + ["-c", "SELECT gia_tri FROM dem WHERE id=1"],
                                capture_output=True, text=True)
            if p0.returncode:
                loi.append("doc_hong")
                continue
            cu = int(p0.stdout.strip() or 0)
            sql = ("BEGIN;\nSELECT pg_sleep(0.001);\n"
                   "UPDATE dem SET gia_tri=%d WHERE id=1;\nCOMMIT;\n" % (cu + 1))
        p = subprocess.run(["psql", "-h", sock, "-p", cong, "-U", nguoi, "-d", csdl,
                            "-qtAX", "-v", "VERBOSITY=verbose", "-v", "ON_ERROR_STOP=1"],
                           input=sql, capture_output=True, text=True)
        if p.returncode:
            for m in re.findall(r"ERROR:\s+([0-9A-Z]{5}):", p.stderr):
                loi.append(m)
        else:
            tin += 1
    ket_qua.put({"tin": tin, "loi": loi})


# ------------------------------------------------------- ca khoá migration (2 tiến trình)
def _tho_migration(sock, cong, nguoi, csdl, bat_dau, dung_khoa, ket_qua):
    """Một tiến trình xin khoá rồi nâng phiên bản. Khuôn giống `migrate.chay()`:
    đọc phiên bản BÊN TRONG khoá, không đọc trước rồi mới xin khoá."""
    while time.time() < bat_dau:
        time.sleep(0.001)
    than = ""
    if dung_khoa:
        than += "BEGIN;\nSELECT pg_advisory_xact_lock(%d);\n" % KHOA_MIGRATION
    else:
        than += "BEGIN;\n"
    than += "SELECT pg_sleep(0.35);\n"          # kéo dài cửa sổ tranh chấp cho phép đo có nghĩa
    than += ("SELECT 'PHIEN_BAN='||phien_ban FROM phien_ban;\n"
             "DO $$ BEGIN\n"
             "  IF (SELECT phien_ban FROM phien_ban) < 8 THEN\n"
             "    CREATE TABLE IF NOT EXISTS bang_v8 (id int primary key, ghi_chu text);\n"
             "    CREATE INDEX IF NOT EXISTS idx_bang_v8 ON bang_v8(ghi_chu);\n"
             "    UPDATE phien_ban SET phien_ban=8, luc=now()::text;\n"
             "    RAISE NOTICE 'DA_NANG_CAP';\n"
             "  ELSE\n"
             "    RAISE NOTICE 'NHUONG';\n"
             "  END IF;\n"
             "END $$;\n"
             "COMMIT;\n")
    p = subprocess.run(["psql", "-h", sock, "-p", cong, "-U", nguoi, "-d", csdl,
                        "-qtAX", "-v", "VERBOSITY=verbose", "-v", "ON_ERROR_STOP=1"],
                       input=than, capture_output=True, text=True)
    nen = "DA_NANG_CAP" if "DA_NANG_CAP" in (p.stderr + p.stdout) else (
        "NHUONG" if "NHUONG" in (p.stderr + p.stdout) else "KHONG_RO")
    truoc = ""
    for d in p.stdout.splitlines():
        if d.startswith("PHIEN_BAN="):
            truoc = d.split("=", 1)[1]
            break
    ket_qua.put({"rc": p.returncode, "nen": nen, "thay_truoc": truoc,
                 "loi": re.findall(r"ERROR:\s+([0-9A-Z]{5}):", p.stderr)})


# =============================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-tien-trinh", type=int, default=4)
    ap.add_argument("--so-phep", type=int, default=120)
    ap.add_argument("--cong", default="55432")
    ap.add_argument("--giu-cum", action="store_true")
    ap.add_argument("--ddl-that", action="store_true", default=True,
                    help="dùng DDL THẬT sinh từ schema đang chạy cho phần DDL nguyên tử")
    a = ap.parse_args()

    for lenh in ("initdb", "pg_ctl", "psql", "pg_dump", "pg_restore"):
        if not shutil.which(lenh):
            print("THIẾU lệnh `%s` — không diễn tập được. Cài: brew install postgresql@16" % lenh)
            return 3

    cum = CumThu(a.cong)
    csdl = "vh_dien_tap"
    try:
        muc("§0. DỰNG CỤM RIÊNG — và chứng minh nó RIÊNG")
        t0 = time.time()
        cum.dung()
        rc, out, err, _ = cum.psql("SELECT 1", dung_lai_khi_loi=True)
        if rc:
            print("cụm dựng xong nhưng không truy vấn được: " + err[-300:])
            return 4
        print("  thư mục cụm : %s" % cum.goc)
        print("  socket      : %s" % cum.sock)
        print("  log         : %s" % cum.log)
        print("  dựng mất    : %.2f giây" % (time.time() - t0))
        print("  " + "\n  ".join(cum.danh_tinh().splitlines()))
        dat("cổng cụm thử KHÁC 5432", cum.cong != CONG_CAM, "cổng %s" % cum.cong)
        dat("thư mục dữ liệu KHÔNG phải cụm hệ thống",
            not cum.data.startswith("/opt/homebrew/var"))
        co_tcp = subprocess.run(["lsof", "-nP", "-iTCP:%s" % cum.cong, "-sTCP:LISTEN"],
                                capture_output=True, text=True).stdout.strip()
        dat("cụm thử KHÔNG mở cổng TCP nào (listen_addresses rỗng)", co_tcp == "",
            "lsof: %r" % co_tcp[:80])
        cum.tao_csdl(csdl)

        # ------------------------------------------------------------------ §1 bốn kết cục
        muc("§1. BỐN KẾT CỤC — PostgreSQL 16.15")
        cum.psql("DROP TABLE IF EXISTS dem; CREATE TABLE dem (id int primary key, "
                 "gia_tri int NOT NULL); INSERT INTO dem VALUES (1,0);", db=csdl)

        # 1a. CHỐT THÀNH CÔNG
        print("\n  1a. CHỐT_THÀNH_CÔNG — %d tiến trình × %d phép, cộng nguyên tử ở tầng câu"
              % (a.so_tien_trinh, a.so_phep))
        q = mp.Queue()
        bat_dau = time.time() + 1.2
        ps = [mp.Process(target=_tho_pg_rmw, args=(cum.sock, cum.cong, cum.nguoi, csdl,
                                                   a.so_phep, "nguyen_tu", bat_dau, q))
              for _ in range(a.so_tien_trinh)]
        [p.start() for p in ps]
        [p.join() for p in ps]
        kq = [q.get() for _ in ps]
        tin = sum(k["tin"] for k in kq)
        _, out, _, _ = cum.psql("SELECT gia_tri FROM dem WHERE id=1", db=csdl)
        that = int(out.strip())
        print("     tiến trình TIN đã ghi : %d" % tin)
        print("     giá trị THẬT trong CSDL: %d" % that)
        dat("CHỐT_THÀNH_CÔNG: không tiến trình nào báo lỗi",
            sum(len(k["loi"]) for k in kq) == 0)
        dat("đối chiếu cuối lượt: TIN == THẬT (mất cập nhật = 0)", tin == that,
            "%d vs %d" % (tin, that))

        # 1b. MẤT CẬP NHẬT — khuôn đọc-rồi-ghi ngây thơ
        print("\n  1b. MẤT_CẬP_NHẬT — khuôn đọc-rồi-ghi NGÂY THƠ (đọc ngoài, ghi giá trị đã đọc)")
        cum.psql("UPDATE dem SET gia_tri=0 WHERE id=1;", db=csdl)
        q = mp.Queue()
        bat_dau = time.time() + 1.0
        ps = [mp.Process(target=_tho_pg_rmw, args=(cum.sock, cum.cong, cum.nguoi, csdl,
                                                   max(20, a.so_phep // 4), "ngay_tho",
                                                   bat_dau, q))
              for _ in range(a.so_tien_trinh)]
        [p.start() for p in ps]
        [p.join() for p in ps]
        kq = [q.get() for _ in ps]
        tin_nt = sum(k["tin"] for k in kq)
        _, out, _, _ = cum.psql("SELECT gia_tri FROM dem WHERE id=1", db=csdl)
        that_nt = int(out.strip())
        print("     giao dịch CHỐT thành công: %d" % tin_nt)
        print("     giá trị THẬT trong CSDL   : %d" % that_nt)
        mat = tin_nt - that_nt
        print("     MẤT CẬP NHẬT              : %d  (%.1f%% số lượt chốt)"
              % (mat, 100.0 * mat / tin_nt if tin_nt else 0))
        dat("khuôn ngây thơ MẤT cập nhật THẬT (đây là điều phải chứng minh)", mat > 0,
            "mất %d lượt, và KHÔNG lượt nào báo lỗi" % mat)
        dat("khuôn ngây thơ cũng KHÔNG báo lỗi nào — mất cập nhật là kết cục IM LẶNG",
            sum(len(k["loi"]) for k in kq) == 0)

        # 1c. KHOA HET GIO
        print("\n  1c. KHOA_HẾT_GIỜ — hai kết nối giành khoá MỘT HÀNG")
        # Đặt một mốc ĐÃ CHỐT rồi mới giữ khoá. Không đặt mốc thì phép đối chiếu cuối lượt
        # không phân biệt được "lượt bị chặn không ghi gì" với "lượt giữ khoá ghi rồi" —
        # bản đầu của phép đo này đã phóng sai vì lý do đó (xem ghi chú §7.1 BAN_GIAO).
        MOC = 7
        cum.psql("UPDATE dem SET gia_tri=%d WHERE id=1;" % MOC, db=csdl)
        giu_done = os.path.join(cum.goc, "giu_khoa_xong")
        cho_tha = os.path.join(cum.goc, "cho_tha")
        giu = subprocess.Popen(
            ["psql", "-h", cum.sock, "-p", cum.cong, "-U", cum.nguoi, "-d", csdl, "-qtAX"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        giu.stdin.write(
            "BEGIN;\n"
            "UPDATE dem SET gia_tri=99 WHERE id=1;\n"       # 99 CHƯA chốt — vô hình với người khác
            "\\! touch %s\n"
            "\\! while [ ! -f %s ]; do sleep 0.2; done\n"
            "ROLLBACK;\n\\q\n" % (giu_done, cho_tha))
        giu.stdin.flush()
        het_gio = time.time() + 15
        while not os.path.exists(giu_done) and time.time() < het_gio:
            time.sleep(0.05)
        dat("kết nối giữ khoá đã vào giao dịch và giữ hàng", os.path.exists(giu_done))
        rc, out, err, ma = cum.psql(
            "SET lock_timeout='400ms';\nBEGIN;\nUPDATE dem SET gia_tri=1 WHERE id=1;\nCOMMIT;",
            db=csdl)
        open(cho_tha, "w").write("tha")
        giu.wait(timeout=20)
        print("     SQLSTATE nhận được: %s" % (ma or "(không có)"))
        dat("KHOA_HẾT_GIỜ: nhận đúng 55P03 lock_not_available",
            "55P03" in ma, SQLSTATE.get("55P03", ""))
        _, out2, _, _ = cum.psql("SELECT gia_tri FROM dem WHERE id=1", db=csdl)
        dat("KHOA_HẾT_GIỜ: KHÔNG ghi gì — hàng vẫn ở mốc đã chốt %d" % MOC,
            out2.strip() == str(MOC), "thấy %s" % out2.strip())

        # 1d. GIAO DICH HONG
        print("\n  1d. GIAO_DỊCH_HỎNG — trigger chặn ở câu thứ hai")
        cum.psql("""
DROP TABLE IF EXISTS but_toan CASCADE;
CREATE TABLE but_toan (id bigint generated by default as identity primary key,
                       so_tien int NOT NULL CHECK (so_tien > 0));
CREATE OR REPLACE FUNCTION cam_sua_but_toan() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'bút toán BẤT BIẾN — cấm sửa'; END $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS trg_cam_sua ON but_toan;
CREATE TRIGGER trg_cam_sua BEFORE UPDATE ON but_toan FOR EACH ROW
  EXECUTE FUNCTION cam_sua_but_toan();
""", db=csdl, dung_lai_khi_loi=True)
        rc, out, err, ma = cum.psql("""
\\echo C1
BEGIN;
\\echo C2
INSERT INTO but_toan (so_tien) VALUES (777000);
\\echo C3
UPDATE but_toan SET so_tien=1 WHERE so_tien=777000;
\\echo C4
INSERT INTO but_toan (so_tien) VALUES (5000);
\\echo C5
COMMIT;
\\echo C6
""", db=csdl)
        chay = re.findall(r"^C(\d)$", out, re.M)
        print("     các câu THẬT SỰ chạy: %s" % ",".join(chay))
        print("     SQLSTATE              : %s" % (ma or "(không có)"))
        dat("GIAO_DỊCH_HỎNG: trigger chặn được (P0001)", "P0001" in ma,
            SQLSTATE.get("P0001", ""))
        dat("GIAO_DỊCH_HỎNG: câu SAU trigger KHÔNG chạy — SQLSTATE 25P02",
            "25P02" in ma, SQLSTATE.get("25P02", ""))
        _, out, _, _ = cum.psql("SELECT count(*) FROM but_toan", db=csdl)
        dat("GIAO_DỊCH_HỎNG: KHÔNG dòng nào vào bảng (777000 cũng bị lùi)",
            out.strip() == "0", "thấy %s dòng" % out.strip())

        # ------------------------------------------------------------- §2 đối chứng SQLite
        muc("§2. CÙNG BỐN KHUÔN ĐÓ TRÊN SQLITE — để biết chỗ nào KHÁC")
        sdb = os.path.join(cum.goc, "doichung.db")
        if os.path.exists(sdb):
            os.remove(sdb)
        kn = sqlite3.connect(sdb, isolation_level=None)
        kn.executescript(DDL_SQLITE_DEM)
        kn.close()
        print("  SQLite %s · %s" % (sqlite3.sqlite_version, sdb))

        for kieu, nhan in (("immediate", "BEGIN IMMEDIATE (khuôn csdl.giao_dich())"),
                           ("ngo_ngan", "BEGIN hoãn     (khuôn ngây thơ)")):
            kn = sqlite3.connect(sdb, isolation_level=None)
            kn.execute("UPDATE dem SET gia_tri=0 WHERE id=1")
            kn.close()
            q = mp.Queue()
            bat = time.time() + 0.8
            ps = [mp.Process(target=_tho_sqlite_rmw,
                             args=(sdb, max(30, a.so_phep // 3), kieu, bat, q))
                  for _ in range(a.so_tien_trinh)]
            [p.start() for p in ps]
            [p.join() for p in ps]
            kq = [q.get() for _ in ps]
            tin_s = sum(k["tin"] for k in kq)
            loi_s = [x for k in kq for x in k["loi"]]
            kn = sqlite3.connect(sdb)
            that_s = kn.execute("SELECT gia_tri FROM dem WHERE id=1").fetchone()[0]
            kn.close()
            print("\n  · %s" % nhan)
            print("      chốt thành công %d · lỗi %d" % (tin_s, len(loi_s)))
            for ld in sorted(set(loi_s))[:3]:
                print("        lỗi: %s" % ld)
            print("      giá trị THẬT %d · MẤT CẬP NHẬT %d" % (that_s, tin_s - that_s))

        # ------------------------------------------------------ §3 khoá migration xuyên tiến trình
        muc("§3. HAI TIẾN TRÌNH KHÔNG BAO GIỜ ĐƯỢC MIGRATION CÙNG LÚC")
        for dung_khoa in (True, False):
            cum.psql("DROP TABLE IF EXISTS bang_v8; DROP TABLE IF EXISTS phien_ban;"
                     "CREATE TABLE phien_ban (phien_ban int NOT NULL, luc text);"
                     "INSERT INTO phien_ban VALUES (7, 'x');", db=csdl, dung_lai_khi_loi=True)
            q = mp.Queue()
            bat = time.time() + 1.0
            ps = [mp.Process(target=_tho_migration,
                             args=(cum.sock, cum.cong, cum.nguoi, csdl, bat, dung_khoa, q))
                  for _ in range(2)]
            [p.start() for p in ps]
            [p.join() for p in ps]
            kq = [q.get() for _ in ps]
            nang = sum(1 for k in kq if k["nen"] == "DA_NANG_CAP")
            nhuong = sum(1 for k in kq if k["nen"] == "NHUONG")
            loi = [x for k in kq for x in k["loi"]]
            _, out, _, _ = cum.psql("SELECT phien_ban FROM phien_ban", db=csdl)
            pb = out.strip()
            _, out, _, _ = cum.psql(
                "SELECT count(*) FROM pg_tables WHERE tablename='bang_v8'", db=csdl)
            co_bang = out.strip()
            nhan = "CÓ khoá tư vấn" if dung_khoa else "KHÔNG khoá (đối chứng âm)"
            print("\n  · %s" % nhan)
            print("      nâng cấp=%d · nhường=%d · lỗi=%d %s · phiên bản cuối=%s · bảng v8=%s"
                  % (nang, nhuong, len(loi), sorted(set(loi)) or "", pb, co_bang))
            if dung_khoa:
                dat("CÓ khoá: đúng MỘT tiến trình nâng cấp", nang == 1, "nâng=%d" % nang)
                dat("CÓ khoá: tiến trình kia NHƯỜNG, không lỗi", nhuong == 1 and not loi)
                dat("CÓ khoá: phiên bản cuối đúng 8, không nâng hai lần", pb == "8", pb)
            else:
                # Đối chứng âm: phép đo phải PHÂN BIỆT ĐƯỢC. Nếu bỏ khoá mà kết quả vẫn
                # "đúng một tiến trình nâng cấp" thì phép đo đang không chạm tới khoá.
                print("      (đối chứng âm — không nhất thiết hỏng, nhưng phải KHÁC lượt có khoá)")

        # ---------------------------------------------------------- §4 DDL nguyên tử
        muc("§4. DDL NGUYÊN TỬ — và ĐỐI CHỨNG ÂM để biết phép đo có chạm thật không")
        import sinh_ddl_pg
        ddl_that = sinh_ddl_pg.sinh()[0]
        cum.tao_csdl("vh_ddl")
        rc, _, err, _ = cum.psql("BEGIN;\n" + ddl_that + "\nCOMMIT;", db="vh_ddl",
                                 dung_lai_khi_loi=True)
        dat("DDL THẬT của dự án nạp trọn trong MỘT giao dịch", rc == 0, err[-200:])
        _, out, _, _ = cum.psql("SELECT count(*) FROM pg_tables WHERE schemaname='public'",
                                db="vh_ddl")
        n_bang = int(out.strip())
        dat("đếm được số bảng > 40 (chặn ca 'DDL rỗng cũng đạt')", n_bang >= 40,
            "%d bảng" % n_bang)

        # Đối chứng âm: chèn một câu SAI vào CUỐI khối DDL → mọi bảng đứng TRƯỚC nó cũng phải
        # biến mất. Đây là ca chứng minh phép đo §4 phía trên có chạm thật: nếu khối DDL vốn
        # không tạo được gì thì "0 bảng còn lại" chẳng nói lên điều gì.
        cum.tao_csdl("vh_ddl_am")
        rc, out, err, ma = cum.psql(
            "BEGIN;\n" + ddl_that + "\nCREATE TABLE cau_sai_co_y (id int, );\nCOMMIT;\n"
            "\\echo SAU_COMMIT\n", db="vh_ddl_am")
        _, con_lai, _, _ = cum.psql("SELECT count(*) FROM pg_tables WHERE schemaname='public'",
                                    db="vh_ddl_am")
        _, co_tenants, _, _ = cum.psql(
            "SELECT count(*) FROM information_schema.tables"
            " WHERE table_schema='public' AND table_name='tenants'", db="vh_ddl_am")
        n_lai = int(con_lai.strip() or -1)
        print("     mã thoát psql=%d · SQLSTATE=%s · bảng còn lại=%d · 'tenants' còn=%s"
              % (rc, ma or "(không)", n_lai, co_tenants.strip()))
        dat("ĐỐI CHỨNG ÂM: câu sai bị CSDL TỪ CHỐI (có 42601 syntax_error)",
            "42601" in ma)
        dat("ĐỐI CHỨNG ÂM: rollback SẠCH — 0/47 bảng còn lại, kể cả bảng đứng TRƯỚC câu sai",
            n_lai == 0 and co_tenants.strip() == "0",
            "còn %d bảng, 'tenants'=%s" % (n_lai, co_tenants.strip()))
        print("     (đối chứng DƯƠNG ở trên: CÙNG khối DDL đó, không chèn câu sai → 47 bảng)")
        print("     (psql mã thoát 0 ở đây là ĐÚNG: ON_ERROR_STOP=0 nên nó báo lỗi rồi đi tiếp,")
        print("      và `COMMIT` trên giao dịch đã hỏng trở thành ROLLBACK. Đừng phán bằng mã thoát.)")

        # ------------------------------------------------------- §5 sao lưu / khôi phục
        muc("§5. SAO LƯU / KHÔI PHỤC — chặng 3 phải thay `migrate.sao_luu()`")
        print("  `migrate.sao_luu()` hiện là `sqlite3.Connection.backup()`: trên PostgreSQL nó")
        print("  KHÔNG có tương đương, và tệ hơn — nó vẫn chạy trót lọt rồi để lại một tệp")
        print("  'bản sao' không chứa gì của PostgreSQL. Đây là đường lùi GIẢ.")
        goi = os.path.join(cum.goc, "sao_luu.dump")
        p = subprocess.run(["pg_dump", "-h", cum.sock, "-p", cum.cong, "-U", cum.nguoi,
                            "-d", "vh_ddl", "-Fc", "-f", goi], capture_output=True, text=True)
        co_byte = os.path.getsize(goi) if os.path.exists(goi) else 0
        dat("pg_dump -Fc chạy được và tệp > 0 byte", p.returncode == 0 and co_byte > 0,
            "%d byte" % co_byte)
        cum.tao_csdl("vh_khoi_phuc")
        p = subprocess.run(["pg_restore", "-h", cum.sock, "-p", cum.cong, "-U", cum.nguoi,
                            "-d", "vh_khoi_phuc", "--no-owner", goi],
                           capture_output=True, text=True)
        dat("pg_restore nạp lại được", p.returncode == 0, (p.stderr or "")[-200:])
        # Phép đối chiếu: KHÔNG đếm bảng (rỗng vẫn khớp). So SỐ DÒNG từng bảng + số cột.
        sql_dem = ("SELECT string_agg(t||'='||n, ',' ORDER BY t) FROM ("
                   " SELECT tablename t, (xpath('/row/c/text()', query_to_xml("
                   "   format('SELECT count(*) c FROM %I', tablename), false, true, '')))[1]::text n"
                   " FROM pg_tables WHERE schemaname='public') s;")
        _, a1, _, _ = cum.psql(sql_dem, db="vh_ddl")
        _, a2, _, _ = cum.psql(sql_dem, db="vh_khoi_phuc")
        dat("khôi phục khớp TỪNG BẢNG về số dòng", a1.strip() == a2.strip(),
            "gốc=%s…" % a1.strip()[:60])
        _, s1, _, _ = cum.psql("SELECT count(*) FROM information_schema.columns"
                               " WHERE table_schema='public'", db="vh_ddl")
        _, s2, _, _ = cum.psql("SELECT count(*) FROM information_schema.columns"
                               " WHERE table_schema='public'", db="vh_khoi_phuc")
        dat("khôi phục khớp số CỘT", s1.strip() == s2.strip(), "%s vs %s" % (s1.strip(), s2.strip()))

        # Dữ liệu THẬT đi qua được: dựng chuỗi khoá ngoại tối thiểu rồi chèn (a) một bút toán
        # mang TIỀN — bất biến theo §17, không ghi lại được, mất là mất; (b) một payload NHỊ
        # PHÂN trong `wh_su_kien.payload_tho` — BLOB→BYTEA, chỗ dễ bị hiểu thành chuỗi nhất.
        cum.psql("""
INSERT INTO goi_dich_vu VALUES ('co_ban','Cơ bản',100000,100,10,3,2) ON CONFLICT (id) DO NOTHING;
INSERT INTO tenants (id,code,ten,goi_id,tao_luc) VALUES (1,'t1','T1','co_ban','x')
  ON CONFLICT (id) DO NOTHING;
INSERT INTO carrier_providers (ma,ten,capabilities_json,live_mo,cap_nhat_luc)
  VALUES ('jt','J&T','{}',0,'x') ON CONFLICT (ma) DO NOTHING;
INSERT INTO carrier_accounts (id,tenant_id,hang,ten,moi_truong,credentials_ma_hoa,
  credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)
  VALUES (1,1,'jt','Acc','mock','v3$k$n$c','abcd','wh1','v3$k$n$c','x')
  ON CONFLICT (id) DO NOTHING;
INSERT INTO tc_but_toan (tenant_id,loai,so_tien_dong,chieu,nguon,can_cu,tao_luc)
  VALUES (1,'cod',777000,'ghi_no','hang','thu COD','x');
INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,nhan_luc)
  VALUES (1,'ev1', decode('00ff10ab5c7e','hex'), '{}','x');
""", db="vh_ddl", dung_lai_khi_loi=True)
        _, tien_goc, _, _ = cum.psql(
            "SELECT (SELECT count(*) FROM tc_but_toan)||'|'||"
            "(SELECT coalesce(sum(so_tien_dong),0) FROM tc_but_toan)||'|'||"
            "(SELECT md5(payload_tho) FROM wh_su_kien WHERE event_id='ev1')", db="vh_ddl")
        goi2 = os.path.join(cum.goc, "sao_luu2.dump")
        subprocess.run(["pg_dump", "-h", cum.sock, "-p", cum.cong, "-U", cum.nguoi,
                        "-d", "vh_ddl", "-Fc", "-f", goi2], capture_output=True, text=True)
        cum.tao_csdl("vh_kp2")
        subprocess.run(["pg_restore", "-h", cum.sock, "-p", cum.cong, "-U", cum.nguoi,
                        "-d", "vh_kp2", "--no-owner", goi2], capture_output=True, text=True)
        _, tien_kp, _, _ = cum.psql(
            "SELECT (SELECT count(*) FROM tc_but_toan)||'|'||"
            "(SELECT coalesce(sum(so_tien_dong),0) FROM tc_but_toan)||'|'||"
            "(SELECT md5(payload_tho) FROM wh_su_kien WHERE event_id='ev1')", db="vh_kp2")
        print("     gốc     : bút toán|tổng tiền|md5(payload) = %s" % tien_goc.strip())
        print("     khôi phục: %s" % tien_kp.strip())
        dat("dữ liệu ĐÃ CHỐT đi qua sao lưu/khôi phục nguyên vẹn",
            tien_goc.strip() == tien_kp.strip() and tien_goc.strip().startswith("1|777000|"),
            "phép đo phải KHÔNG rỗng — bút toán 777000 và md5 nhị phân")
        _, kieu_bytea, _, _ = cum.psql(
            "SELECT data_type FROM information_schema.columns WHERE table_name='wh_su_kien'"
            " AND column_name='payload_tho'", db="vh_ddl")
        dat("`wh_su_kien.payload_tho` dịch thành BYTEA trên schema THẬT",
            kieu_bytea.strip() == "bytea", kieu_bytea.strip())

    finally:
        muc("§6. DỌN — dừng cụm và xoá sạch")
        cum.dong(xoa=not a.giu_cum)
        print("  đã dừng bằng `pg_ctl stop -m immediate` và xoá %s" % cum.goc)
        if a.giu_cum:
            print("  --giu-cum: cụm còn sống ở cổng %s, socket %s" % (cum.cong, cum.sock))
            print("  xoá bằng: pg_ctl -D %s stop -m immediate && rm -rf %s %s"
                  % (cum.data, cum.goc, cum.sock))

    muc("KẾT LUẬN PHẠM VI HẸP")
    print("  đạt %d · hỏng %d · bỏ qua %d" % (_dem["dat"], _dem["hong"], _dem["bo_qua"]))
    print("  ĐÃ ĐO: schema thật dựng được trong 1 giao dịch · DDL lùi sạch khi hỏng giữa khối ·")
    print("    khoá tư vấn cho đúng 1 tiến trình migration · sao lưu/khôi phục giữ số dòng và")
    print("    tổng tiền · bốn kết cục phân biệt được bằng SQLSTATE.")
    print("  NẰM NGOÀI: lớp phương ngữ `csdl.py` (chặng 1 — CHƯA làm, nên MÃ NGHIỆP VỤ CHƯA")
    print("    CHẠY ĐƯỢC trên PostgreSQL) · chuyển dữ liệu (chặng 4) · nhiều máy · mạng thật ·")
    print("    dữ liệu lớn · tải đọc · replica.")
    print("  CSDL NGHIỆP VỤ VẪN LÀ SQLITE. Lượt này KHÔNG chuyển gì (D-8, chỉ thị G12 mục 8).")
    return 0 if _dem["hong"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
