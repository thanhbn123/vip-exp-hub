#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ĐƯỜNG GHI của sản phẩm, chạy trên CẢ HAI kho — để đo `rowcount` mà mã nghiệp vụ nhận được.

====== LỖ HỔNG TỆP NÀY BỊT ======
AG-01 ghi ở mục CHƯA ĐỎ của lượt nghiệm thu G17:

    "PostgreSQL: đường GHI (csdl.ghi, rowcount) — AG-05 chỉ dùng SCHEMA"

Nghĩa là: schema đã nạp, bốn kết cục giao dịch đã đo — nhưng **hàm `csdl.ghi()` và giá trị
`rowcount` nó trả về CHƯA BAO GIỜ chạy trên PostgreSQL**. Mà `rowcount` là thứ mã sản phẩm
đang DÙNG ĐỂ QUYẾT ĐỊNH "ghi được hay không": đo được **19 chỗ** trong `app/` đọc `.rowcount`
(bảng đầy đủ ở `docs/G18_PG_WRITE.md` §2). Nếu PostgreSQL trả khác thì logic ấy sai **IM LẶNG**.

====== CÁCH ĐO — VÀ VÌ SAO ĐO ĐƯỢC ======
`app/csdl.py` **không bị sửa một dòng nào** (D-8 nguyên vẹn; và tệp đó ngoài danh sách được ghi).
Nên phép đo có hai vế, và vế nào cũng là ĐƯỜNG GHI THẬT:

* `DuongGhiSQLite` — gọi **CHÍNH `csdl.ghi()`** của sản phẩm, chỉ trỏ `cau_hinh.DUONG_DAN_CSDL`
  sang một tệp TẠM. `app/du-lieu/hub.db` **không bị đọc, không bị ghi**.
* `DuongGhiPG` — **bản sao đúng khuôn** của `mo()`/`ghi()`/`giao_dich()` trong `csdl.py`, chỉ
  đổi ĐÚNG ranh giới trình điều khiển: `sqlite3` → `libpq` (`libpq_ctypes.py`). Thân hàm giữ
  nguyên hình dạng (khoá ghi, trả con trỏ, tự chốt khi ngoài giao dịch) để phép so là so
  **ranh giới driver**, không phải so hai đoạn mã do hai người viết.

Phép dịch SQL duy nhất: `?` → `$n` (có bỏ qua `?` nằm trong chuỗi/định danh/chú thích). Lớp
phương ngữ đầy đủ của `csdl.py` (846 dấu `?`, `INSERT OR IGNORE`, `PRAGMA`) **CHƯA làm** —
xem `docs/G17_POSTGRES.md` §7. Ở đây chỉ dịch đúng chừng nào đủ để ĐO.

====== ĐỐI CHỨNG: MỌI CA ĐỀU CÓ VẾ "SỰ THẬT" ======
Một `rowcount` là lời KHAI của trình điều khiển. Nên mỗi ca, sau khi ghi, còn một lượt ĐỌC
KIỂM CHỨNG trên **kết nối KHÁC** — đếm/đọc thẳng trạng thái thật trong kho. Ca nào khai
`rowcount=1` mà kho không có dòng nào thì bị bắt ngay tại đây, không cần tin lời khai.

CHẠY
----
    python3 trien_khai/postgres/duong_ghi_pg.py            # tự kiểm: dựng cụm riêng, chạy bảng ca
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(GOC, "app")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import libpq_ctypes as lp                                                # noqa: E402

CONG_CAM = "5432"


def kiem_cong_an_toan(cong):
    """TỪ CHỐI cổng 5432 — cụm hệ thống đang giữ CSDL của dự án khác (`vip_customs*`)."""
    if str(cong) == CONG_CAM:
        raise AssertionError(
            "TỪ CHỐI chạy trên cổng %s: đó là cụm PostgreSQL hệ thống của máy này, đang giữ "
            "CSDL của dự án khác (vip_customs, vip_customs_g16, vip_customs_test). "
            "Đường ghi phải đo trên cụm riêng." % CONG_CAM)


# =========================================================== cụm thử (riêng hoàn toàn)
class CumGhi(object):
    """Cụm PostgreSQL dùng một lần: thư mục tạm riêng, socket `/tmp/vhpg.XXXX`, KHÔNG mở TCP.

    Dừng bằng `pg_ctl stop` rồi `rmtree` — **KHÔNG `pkill`/`killall`**: `CLAUDE.md` §16.7 cấm
    tắt tiến trình theo mẫu tên, và `pkill -f postgres` ở đây sẽ giết luôn cụm `:5432`.
    """

    def __init__(self, cong=None, nguoi=None):
        self.cong = str(cong or os.environ.get("VHPG_CONG", "55432"))
        self.nguoi = nguoi or os.environ.get("VHPG_NGUOI", "vhtest")
        kiem_cong_an_toan(self.cong)
        self.thu_muc = None
        self.sock = None
        self._dang_chay = False

    def dung(self):
        if shutil.which("initdb") is None or shutil.which("pg_ctl") is None:
            raise RuntimeError("thiếu `initdb`/`pg_ctl` trên PATH — cài: brew install postgresql@16")
        self.thu_muc = tempfile.mkdtemp(prefix="vhpg-thu-")
        # `LANG=C LC_ALL=C` cho CẢ `initdb` và `pg_ctl`: thiếu ở `pg_ctl` thì postmaster chết
        # với "became multithreaded during startup" (đã vấp thật, ghi ở dung_cum_thu.sh).
        moi = dict(os.environ, LANG="C", LC_ALL="C")
        p = subprocess.run(["initdb", "-D", os.path.join(self.thu_muc, "data"),
                            "--locale=C", "--encoding=UTF8", "-U", self.nguoi],
                           capture_output=True, text=True, env=moi)
        if p.returncode:
            raise RuntimeError("initdb hỏng: " + (p.stderr or p.stdout)[-400:])
        # sun_path giới hạn 103 byte ⇒ socket PHẢI ở đường ngắn, không nằm trong TMPDIR của phiên.
        self.sock = tempfile.mkdtemp(prefix="vhpg.", dir="/tmp")
        p = subprocess.run(["pg_ctl", "-D", os.path.join(self.thu_muc, "data"),
                            "-l", os.path.join(self.thu_muc, "pg.log"),
                            "-o", "-p %s -k %s -c listen_addresses=''" % (self.cong, self.sock),
                            "-w", "start"], capture_output=True, text=True, env=moi)
        if p.returncode:
            ghi = os.path.join(self.thu_muc, "pg.log")
            them = open(ghi, encoding="utf-8", errors="replace").read()[-400:] \
                if os.path.exists(ghi) else ""
            self.dong()
            raise RuntimeError("pg_ctl start hỏng: %s | pg.log: %s"
                               % ((p.stderr or p.stdout)[-200:], them))
        self._dang_chay = True
        return self

    def dong(self):
        """Dừng cụm rồi xoá thư mục. `-w` là BẮT BUỘC: thiếu nó, `pg_ctl stop` trả về trước khi
        postmaster thoát hẳn, `rmtree` chạy vào lúc máy chủ còn ghi tệp, và thư mục SÓT LẠI
        (đo được: `/tmp/vhpg-thu-XXXX` còn nguyên sau lượt chạy đầu). Xoá hỏng thì thử lại —
        và `do_ghi_that.py` vẫn đếm và KÊU, không im lặng."""
        if self.thu_muc and self._dang_chay:
            subprocess.run(["pg_ctl", "-D", os.path.join(self.thu_muc, "data"), "stop",
                            "-m", "fast", "-w"], capture_output=True, text=True)
            self._dang_chay = False
        for d in (self.thu_muc, self.sock):
            if not d:
                continue
            for lan in range(6):
                shutil.rmtree(d, ignore_errors=True)
                if not os.path.exists(d):
                    break
                time.sleep(0.25 * (lan + 1))
        self.thu_muc = self.sock = None

    # -- tiện ích
    def psql(self, sql, db="postgres", dung_lai_khi_loi=True):
        co = ["psql", "-h", self.sock, "-p", self.cong, "-U", self.nguoi, "-d", db, "-qtAX"]
        if dung_lai_khi_loi:
            co += ["-v", "ON_ERROR_STOP=1"]
        p = subprocess.run(co, input=sql, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    def tao_csdl(self, ten):
        self.psql("DROP DATABASE IF EXISTS %s" % ten)
        rc, _, err = self.psql("CREATE DATABASE %s" % ten)
        if rc:
            raise RuntimeError("không tạo được CSDL %s: %s" % (ten, err))

    def xoa_csdl(self, ten):
        self.psql("DROP DATABASE IF EXISTS %s" % ten)

    def dsn(self, db):
        return lp.dsn(self.sock, self.cong, self.nguoi, db)

    def mo(self, db, tu_dong_chot=True, ten="pg"):
        return lp.KetNoi(self.dsn(db), tu_dong_chot=tu_dong_chot, ten=ten)


# =========================================================== dịch tham số `?` → `$n`
def doi_tham_so(sql):
    """Đổi `?` thành `$1…$n`. BỎ QUA `?` trong chuỗi, định danh, chú thích.

    Vì sao phải có bộ quét chứ không `str.replace`: `LIKE '%?%'` là một chuỗi hợp lệ; thay bừa
    ở đó là đổi nghĩa câu lệnh mà không báo lỗi. Đây là bản dịch TỐI THIỂU để đo, không phải
    lớp phương ngữ của sản phẩm (chưa làm — `docs/G17_POSTGRES.md` §7).
    """
    ra, n, i, dai = [], 0, 0, len(sql)
    while i < dai:
        ch = sql[i]
        if ch == "'" or ch == '"':
            j = i + 1
            while j < dai:
                if sql[j] == ch:
                    if j + 1 < dai and sql[j + 1] == ch:      # '' hoặc "" đã escape
                        j += 2
                        continue
                    break
                j += 1
            ra.append(sql[i:j + 1])
            i = j + 1
            continue
        if ch == "-" and i + 1 < dai and sql[i + 1] == "-":
            j = sql.find("\n", i)
            j = dai if j < 0 else j
            ra.append(sql[i:j])
            i = j
            continue
        if ch == "?":
            n += 1
            ra.append("$%d" % n)
            i += 1
            continue
        ra.append(ch)
        i += 1
    return "".join(ra), n


# =========================================================== ĐƯỜNG GHI SQLite (SẢN PHẨM THẬT)
class DuongGhiSQLite(object):
    """Đường ghi THẬT của sản phẩm: gọi thẳng `csdl.ghi()`, CSDL trỏ vào thư mục TẠM.

    KHÔNG đụng `app/du-lieu/hub.db` (D-8): `cau_hinh.DUONG_DAN_CSDL` được trỏ sang tệp tạm
    TRƯỚC khi `csdl.mo()` mở kết nối lần đầu.
    """

    ten = "SQLite (csdl.ghi THẬT)"

    def __init__(self, thu_muc=None, tu_don=True):
        import cau_hinh
        import csdl
        self.cau_hinh, self.csdl = cau_hinh, csdl
        self.tu_don = tu_don
        self.thu_muc = thu_muc or tempfile.mkdtemp(prefix="vh-ghi-sqlite-")
        self._goc = (cau_hinh.THU_MUC_DU_LIEU, cau_hinh.DUONG_DAN_CSDL)
        cau_hinh.THU_MUC_DU_LIEU = self.thu_muc
        cau_hinh.DUONG_DAN_CSDL = os.path.join(self.thu_muc, "hub.db")
        csdl.dong()                       # quên dòng này là kết nối cũ còn trỏ CSDL thật
        os.makedirs(self.thu_muc, exist_ok=True)

    # -- API đường ghi, ĐÚNG hình dạng csdl
    def mo(self):
        return self.csdl.mo()

    def ghi(self, sql, tham_so=()):
        return self.csdl.ghi(sql, tham_so)

    def mot(self, sql, tham_so=()):
        return self.csdl.mot(sql, tham_so)

    def nhieu(self, sql, tham_so=()):
        return self.csdl.nhieu(sql, tham_so)

    def giao_dich(self):
        return self.csdl.giao_dich()

    def chay_sql(self, sql):
        return self.csdl.ghi(sql)

    def mo_doc_lap(self):
        """Kết nối ĐỘC LẬP để đọc kiểm chứng — không dùng kết nối của đường ghi."""
        return self.csdl.ket_noi(self.cau_hinh.DUONG_DAN_CSDL, timeout=10, theo_ten_cot=True)

    def doc_kiem_chung(self, sql, tham_so=()):
        kn = self.mo_doc_lap()
        try:
            return kn.execute(sql, tham_so).fetchall()
        finally:
            try:
                kn.close()
            except Exception:
                pass

    def dong(self):
        try:
            self.csdl.dong()
        except Exception:
            pass
        self.cau_hinh.THU_MUC_DU_LIEU, self.cau_hinh.DUONG_DAN_CSDL = self._goc
        if self.tu_don:
            shutil.rmtree(self.thu_muc, ignore_errors=True)


# =========================================================== ĐƯỜNG GHI PostgreSQL (BẢN SAO KHUÔN)
def boc_cum(cum):
    """Nhận một cụm CHỈ CÓ `.sock/.cong/.nguoi` (ví dụ `Cum` của `app/thu/thu_postgres.py`) và
    trả về một đối tượng có `.dsn()/.mo()`. Nhờ vậy đường ghi không bị buộc vào một lớp cụm cụ thể
    — bộ thử hồi quy dựng cụm theo cách của nó, còn ở đây chỉ cần địa chỉ cụm."""
    if hasattr(cum, "mo") and hasattr(cum, "dsn"):
        return cum
    return _CumNgoai(cum.sock, cum.cong, cum.nguoi)


class DuongGhiPG(object):
    """Bản sao `mo()/ghi()/giao_dich()` của `csdl.py`, chỉ đổi ranh giới driver sang libpq.

    `tu_dong_chot=True` (mặc định) giữ ĐÚNG chế độ hiện nay của `csdl.mo()`: kết nối
    `isolation_level=None` ⇒ **mỗi câu tự chốt**. Đặt `False` để mô phỏng chế độ **mặc định
    của psycopg2** (mở `BEGIN` ngầm, chỉ chốt khi `commit()`) — ca T3 đo chỗ đó.
    """

    ten = "PostgreSQL (bản sao khuôn csdl.ghi)"

    def __init__(self, cum, db, tu_dong_chot=True, tu_dong_mo=None):
        self.cum, self.db = boc_cum(cum), db
        self.tu_dong_chot = tu_dong_chot
        self.tu_dong_mo = tu_dong_chot if tu_dong_mo is None else tu_dong_mo
        self._kn = None
        self._sau_giao_dich = 0
        import threading
        self.khoa_ghi = threading.RLock()

    # -- mo() / dong() : cùng thứ tự cố ý như csdl.mo() (có kết nối thì trả NGAY)
    def mo(self):
        if self._kn is None or self._kn.da_dong:
            self._kn = self.cum.mo(self.db, tu_dong_chot=self.tu_dong_chot, ten=self.db)
        return self._kn

    def dong(self):
        if self._kn is not None:
            self._kn.close()
            self._kn = None
        self._sau_giao_dich = 0

    # -- ghi() : ĐÚNG hình dạng csdl.ghi
    def ghi(self, sql, tham_so=()):
        kn = self.mo()
        with self.khoa_ghi:
            cau, n = doi_tham_so(sql)
            if tham_so is None:
                tham_so = ()
            if n != len(tuple(tham_so)):
                raise AssertionError("số dấu ? (%d) khác số tham số (%d): %s"
                                     % (n, len(tuple(tham_so)), sql[:80]))
            return kn.execute(cau, tuple(tham_so))

    # -- mot()/nhieu() : đường ĐỌC, cùng hình dạng
    def mot(self, sql, tham_so=()):
        cau, _ = doi_tham_so(sql)
        return self.mo().execute(cau, tuple(tham_so or ())).fetchone()

    def nhieu(self, sql, tham_so=()):
        cau, _ = doi_tham_so(sql)
        return self.mo().execute(cau, tuple(tham_so or ())).fetchall()

    def chay_sql(self, sql):
        return self.mo().execute(sql)

    # -- giao_dich() : cùng cấu trúc SAVEPOINT/BEGIN của csdl.giao_dich
    def giao_dich(self):
        return _GiaoDichPG(self)

    def mo_doc_lap(self):
        return lp.KetNoi(self.cum.dsn(self.db), tu_dong_chot=True, ten=self.db + "-doc")

    def doc_kiem_chung(self, sql, tham_so=()):
        cau, _ = doi_tham_so(sql)
        kn = self.mo_doc_lap()
        try:
            return kn.execute(cau, tuple(tham_so or ())).fetchall()
        finally:
            kn.close()


class _GiaoDichPG(object):
    """`contextmanager` cùng luật với `csdl.giao_dich()`: tầng ngoài `BEGIN`, tầng trong
    `SAVEPOINT`, lỗi thì lùi, `BaseException` cũng lùi."""

    def __init__(self, dg):
        self.dg = dg

    def __enter__(self):
        dg = self.dg
        kn = dg.mo()
        dg.khoa_ghi.acquire()
        sau = dg._sau_giao_dich
        ten = "gd%d" % sau
        if sau == 0:
            kn.execute("BEGIN")
        else:
            kn.execute("SAVEPOINT " + ten)
        dg._sau_giao_dich = sau + 1
        self.sau, self.ten, self.kn = sau, ten, kn
        return kn

    def __exit__(self, loai, gt, tb):
        dg = self.dg
        try:
            if loai is not None:
                if self.sau == 0:
                    self.kn.execute("ROLLBACK")
                else:
                    self.kn.execute("ROLLBACK TO " + self.ten)
                    self.kn.execute("RELEASE " + self.ten)
                dg._sau_giao_dich = self.sau
                return False
            if self.sau == 0:
                self.kn.execute("COMMIT")
            else:
                self.kn.execute("RELEASE " + self.ten)
            dg._sau_giao_dich = self.sau
            return False
        finally:
            dg.khoa_ghi.release()


# =========================================================== BẢNG CA ĐO
# `rowcount` kỳ vọng điền SAU khi đo lần đầu (xem docs/G18_PG_WRITE.md §3) — ở đây để `None`
# nghĩa là "đo rồi ghi lại", KHÔNG phải "đoán".
DDL_BANG_DO = """
CREATE TABLE IF NOT EXISTS w_ghi (
  id INTEGER PRIMARY KEY,
  x INTEGER NOT NULL,
  y TEXT
)
"""


def _ca(ma, nhom, mo_ta, sql, ts=(), sql_pg=None, kiem=None, ghi_chu=""):
    return {"ma": ma, "nhom": nhom, "mo_ta": mo_ta, "sql": sql, "ts": tuple(ts),
            "sql_pg": sql_pg if sql_pg is not None else sql, "kiem": kiem, "ghi_chu": ghi_chu}


# `kiem` = (SQL đọc kiểm chứng, giá_trị_mong_đợi) — chạy trên KẾT NỐI KHÁC sau lượt ghi.
CA_GHI = [
    # ---- nhóm N: đường ghi có trả rowcount không, và trả cái gì
    _ca("N0", "N-đọc", "SELECT qua chính ghi() — 0 dòng khớp",
        "SELECT id FROM w_ghi WHERE id=?", (1,), kiem=("SELECT count(*) c FROM w_ghi WHERE id=1", 0)),
    # ---- nhóm W: các dạng ghi csdl.ghi() phải chịu
    _ca("W1", "W-INSERT", "INSERT 1 dòng",
        "INSERT INTO w_ghi (id,x,y) VALUES (?,?,?)", (1, 10, "a"),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=1", 1)),
    _ca("W2", "W-INSERT", "INSERT 3 dòng trong MỘT câu",
        "INSERT INTO w_ghi (id,x,y) VALUES (?,?,?),(?,?,?),(?,?,?)", (2, 20, "b", 3, 30, "c", 4, 40, "d"),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id IN (2,3,4)", 3)),
    _ca("N1", "N-đọc", "SELECT qua chính ghi() — 4 dòng khớp",
        "SELECT id FROM w_ghi ORDER BY id", (), kiem=("SELECT count(*) c FROM w_ghi", 4)),
    _ca("W3", "W-INSERT", "INSERT trùng khoá chính (phải NÉM LỖI, không trả rowcount)",
        "INSERT INTO w_ghi (id,x,y) VALUES (?,?,?)", (1, 99, "trung"),
        kiem=("SELECT x v FROM w_ghi WHERE id=1", "10")),
    _ca("W4", "W-INSERT-OR-IGNORE", "INSERT OR IGNORE khi ĐÃ có khoá (bỏ qua)",
        "INSERT OR IGNORE INTO w_ghi (id,x,y) VALUES (?,?,?)", (1, 99, "bo-qua"),
        sql_pg="INSERT INTO w_ghi (id,x,y) VALUES (?,?,?) ON CONFLICT DO NOTHING",
        kiem=("SELECT x v FROM w_ghi WHERE id=1", "10")),
    _ca("W5", "W-INSERT-OR-IGNORE", "INSERT OR IGNORE khi CHƯA có khoá (chèn thật)",
        "INSERT OR IGNORE INTO w_ghi (id,x,y) VALUES (?,?,?)", (5, 50, "e"),
        sql_pg="INSERT INTO w_ghi (id,x,y) VALUES (?,?,?) ON CONFLICT DO NOTHING",
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=5", 1)),
    _ca("W6", "W-INSERT-OR-REPLACE", "INSERT OR REPLACE khi ĐÃ có khoá (ghi đè)",
        "INSERT OR REPLACE INTO w_ghi (id,x,y) VALUES (?,?,?)", (5, 55, "e2"),
        sql_pg=("INSERT INTO w_ghi (id,x,y) VALUES (?,?,?) "
                "ON CONFLICT (id) DO UPDATE SET x=excluded.x, y=excluded.y"),
        kiem=("SELECT x v FROM w_ghi WHERE id=5", "55")),
    _ca("W7", "W-UPDATE", "UPDATE khớp ĐÚNG 1 dòng",
        "UPDATE w_ghi SET x=? WHERE id=?", (11, 1),
        kiem=("SELECT x v FROM w_ghi WHERE id=1", "11")),
    _ca("W8", "W-UPDATE", "UPDATE khớp 3 dòng",
        "UPDATE w_ghi SET x=? WHERE id IN (2,3,4)", (77,),
        kiem=("SELECT count(*) c FROM w_ghi WHERE x=77", 3)),
    _ca("W9", "W-UPDATE", "UPDATE KHÔNG khớp dòng nào",
        "UPDATE w_ghi SET x=? WHERE id=?", (12, 999),
        kiem=("SELECT count(*) c FROM w_ghi WHERE x=12", 0)),
    _ca("W10", "W-UPDATE", "UPDATE đặt LẠI đúng giá trị đang có (khớp 1 dòng, không đổi gì)",
        "UPDATE w_ghi SET x=? WHERE id=?", (11, 1),
        kiem=("SELECT x v FROM w_ghi WHERE id=1", "11")),
    _ca("W11", "W-DELETE", "DELETE khớp 1 dòng",
        "DELETE FROM w_ghi WHERE id=?", (5,),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=5", 0)),
    _ca("W12", "W-DELETE", "DELETE KHÔNG khớp dòng nào",
        "DELETE FROM w_ghi WHERE id=?", (999,),
        kiem=("SELECT count(*) c FROM w_ghi", 4)),
    _ca("W13", "W-DELETE", "DELETE khớp 2 dòng",
        "DELETE FROM w_ghi WHERE id IN (3,4)", (),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id IN (3,4)", 0)),
    _ca("W14", "W-DDL", "DDL qua chính ghi() (CREATE TABLE IF NOT EXISTS)",
        "CREATE TABLE IF NOT EXISTS w_ddl (a INTEGER)", (),
        kiem=("SELECT count(*) c FROM w_ddl", 0)),
    _ca("W15", "W-RETURNING", "INSERT … RETURNING id qua chính ghi() (ĐỌC TRƯỚC khi hút hết dòng)",
        "INSERT INTO w_ghi (id,x,y) VALUES (?,?,?) RETURNING id", (6, 60, "f"),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=6", 1)),
    _ca("W16", "W-INSERT-tu-SELECT", "INSERT … SELECT không chọn được dòng nào (WHERE 1=0)",
        "INSERT INTO w_ghi (id,x,y) SELECT CAST(? AS INTEGER),CAST(? AS INTEGER),CAST(? AS TEXT) WHERE 1=0",
        (7, 70, "g"),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=7", 0)),
    _ca("W16b", "W-INSERT-tu-SELECT", "ĐỐI CHỨNG PHƯƠNG NGỮ: WHERE 0 (SQLite nhận, PostgreSQL KHÔNG)",
        "INSERT INTO w_ghi (id,x,y) SELECT CAST(? AS INTEGER),CAST(? AS INTEGER),CAST(? AS TEXT) WHERE 0",
        (8, 80, "h"),
        kiem=("SELECT count(*) c FROM w_ghi WHERE id=8", 0)),
    _ca("W17", "W-nghiệp-vụ", "INSERT vào bảng NGHIỆP VỤ thật (tenants) bằng SQL của sản phẩm",
        "INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
        ("t-g18", "Tenant G18", "basic", "2026-10-15 10:00:00+0700"),
        kiem=("SELECT count(*) c FROM tenants WHERE code='t-g18'", 1)),
    _ca("W18", "W-nghiệp-vụ", "UPDATE nghiệp vụ khớp 1 dòng — khuôn `rowcount != 1` của doi_soat/webhook",
        "UPDATE tenants SET ten=? WHERE code=? AND goi_id=?", ("Tenant G18 B", "t-g18", "basic"),
        kiem=("SELECT ten v FROM tenants WHERE code='t-g18'", "Tenant G18 B")),
    _ca("W19", "W-nghiệp-vụ", "UPDATE nghiệp vụ KHÔNG khớp — chỗ `rowcount != 1` phải phát hiện tranh chấp",
        "UPDATE tenants SET ten=? WHERE code=? AND goi_id=?", ("Tenant G18 C", "t-g18", "pro"),
        kiem=("SELECT ten v FROM tenants WHERE code='t-g18'", "Tenant G18 B")),
    _ca("W20", "W-nghiệp-vụ", "DELETE nghiệp vụ khớp 1 dòng",
        "DELETE FROM tenants WHERE code=?", ("t-g18",),
        kiem=("SELECT count(*) c FROM tenants WHERE code='t-g18'", 0)),
]


def chuan_bi_sqlite(dg):
    """Fixture: schema sản phẩm do CHÍNH `csdl` dựng, rồi bảng đo."""
    dg.mo()                                   # csdl.mo() tự nạp SCHEMA + seed gói dịch vụ
    dg.chay_sql(DDL_BANG_DO)


def chuan_bi_pg(dg, ddl_pg, goi_mac_dinh):
    """Fixture: DDL SINH TỪ `csdl.SCHEMA` (không chép tay) + seed gói dịch vụ như SQLite."""
    dg.chay_sql(ddl_pg)
    for g in goi_mac_dinh:
        dg.ghi("INSERT INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,han_muc_ai_thang,"
               "so_nhan_vien,so_tai_khoan_hang) VALUES (?,?,?,?,?,?,?) ON CONFLICT (id) DO NOTHING",
               (g["id"], g["ten"], g["gia_thang"], g["han_muc_don_thang"], g["han_muc_ai_thang"],
                g["so_nhan_vien"], g["so_tai_khoan_hang"]))
    dg.chay_sql(DDL_BANG_DO)


def _chuan_hoa(v):
    """Giá trị đọc kiểm chứng: số về `str` để hai kho so được với nhau, NULL giữ là None."""
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


def loai_loi(e):
    """Quy loại lỗi về TÊN NGHIỆP VỤ — `toan_ven` / `van_hanh` — để hai trình điều khiển so được.

    So tên lớp Python (`IntegrityError` vs `LoiToanVen`) là so TÊN DRIVER, không phải so hành vi:
    `csdl.LoiToanVen` chính là `sqlite3.IntegrityError`, còn bên kia `psycopg2` cũng ánh xạ
    23xxx vào `IntegrityError`. Cái phải giống là *nhóm* lỗi, và SQLSTATE là bằng chứng.
    """
    if e is None:
        return None
    import sqlite3
    if isinstance(e, sqlite3.IntegrityError):
        return "toan_ven"
    if isinstance(e, sqlite3.Error):
        return "van_hanh"
    if isinstance(e, lp.LoiToanVen):
        return "toan_ven"
    if isinstance(e, lp.LoiPG):
        return "van_hanh"
    return "khac:" + type(e).__name__


def chay_ca(dg, ca, la_pg=False):
    """Chạy MỘT ca trên một đường ghi. Trả dict kết quả — KHÔNG ném ra ngoài.

    `rowcount` được đọc HAI lần, có chủ ý: **ngay sau `ghi()`** (đúng cách mã sản phẩm đọc) và
    **sau khi hút hết dòng trả về**. Hai lần này KHÁC NHAU ở câu `RETURNING` — xem ca `W15`.
    """
    sql = ca["sql_pg"] if la_pg else ca["sql"]
    kq = {"ma": ca["ma"], "rowcount": None, "rowcount_sau_doc": None, "loi": None,
          "loai_loi": None, "sqlstate": None, "tra_ve": None,
          "kiem_thay": None, "kiem_mong": None, "kiem_dat": None}
    try:
        c = dg.ghi(sql, ca["ts"])
        kq["rowcount"] = c.rowcount                  # ĐỌC NGAY — như mã sản phẩm đang làm
        try:
            hang = c.fetchall()
            kq["tra_ve"] = [r[0] for r in hang][:5]
        except Exception:                            # noqa: BLE001 — câu không có tập kết quả
            kq["tra_ve"] = None
        kq["rowcount_sau_doc"] = c.rowcount
    except Exception as e:                           # noqa: BLE001 — cố ý bắt HẾT để so LOẠI lỗi
        kq["loi"] = type(e).__name__
        kq["loai_loi"] = loai_loi(e)
        kq["sqlstate"] = getattr(e, "sqlstate", None)
    if ca["kiem"]:
        csql, mong = ca["kiem"]
        try:
            hang = dg.doc_kiem_chung(csql)
            kq["kiem_thay"] = _chuan_hoa(hang[0][0]) if hang else None
        except Exception as e:                       # noqa: BLE001
            kq["kiem_thay"] = "LỖI-ĐỌC:%s" % type(e).__name__
        kq["kiem_mong"] = _chuan_hoa(mong)
        kq["kiem_dat"] = (kq["kiem_thay"] == kq["kiem_mong"])
    return kq


def so_sanh(kq_sqlite, kq_pg):
    """So hai kết quả theo BỐN thứ: `rowcount` đọc ngay, nhóm lỗi, và vế kiểm chứng của CẢ HAI.

    Trả `(danh_sách_lệch, danh_sách_giống)`. Một ca chỉ được tính "giống" khi:
    `rowcount` bằng nhau · nhóm lỗi bằng nhau · và vế ĐỌC KIỂM CHỨNG của cả hai kho đều ĐẠT.
    Thiếu vế thứ ba thì hai kho "giống nhau" mà cùng sai.
    """
    lech, giong = [], []
    for a, b in zip(kq_sqlite, kq_pg):
        dong = {"ma": a["ma"], "sqlite": a, "pg": b}
        if a["rowcount"] != b["rowcount"] or a["loai_loi"] != b["loai_loi"] \
                or a["kiem_dat"] is not True or b["kiem_dat"] is not True:
            lech.append(dong)
        else:
            giong.append(dong)
    return lech, giong


# =========================================================== BỐN KẾT CỤC, QUA ĐƯỜNG GHI THẬT
DDL_BANG_GD = """
CREATE TABLE IF NOT EXISTS w_gd (id INTEGER PRIMARY KEY, x INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS w_dem (id INTEGER PRIMARY KEY, dem INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS w_lock (id INTEGER PRIMARY KEY, x INTEGER NOT NULL)
"""


def chuan_bi_giao_dich(dg):
    for c in DDL_BANG_GD.strip().rstrip(";").split(";"):
        if c.strip():
            dg.chay_sql(c.strip())
    for b in ("w_gd", "w_dem", "w_lock"):
        dg.chay_sql("DELETE FROM %s" % b)
    dg.ghi("INSERT INTO w_dem (id,dem) VALUES (?,?)", (1, 0))
    dg.ghi("INSERT INTO w_lock (id,x) VALUES (?,?)", (1, 0))


def _dem(dg, sql, ts=()):
    r = dg.doc_kiem_chung(sql, ts)
    return _chuan_hoa(r[0][0]) if r else None


def t1_chot_thanh_cong(dg):
    """CHỐT_THÀNH_CÔNG — ghi trong `giao_dich()` rồi chốt: phải BỀN."""
    kq = {}
    with dg.giao_dich():
        c = dg.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (1, 10))
        kq["rc_trong_khoi"] = c.rowcount
    kq["ben"] = _dem(dg, "SELECT count(*) c FROM w_gd WHERE id=1")
    kq["mong"] = "1"
    return kq


def t2_lui_khi_hong(dg):
    """GIAO_DỊCH_HỎNG (lùi) — `rowcount` ĐÃ trả 1 trong khối, nhưng kho phải TRỐNG sau khi lùi."""
    kq = {}
    try:
        with dg.giao_dich():
            c = dg.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (2, 20))
            kq["rc_trong_khoi"] = c.rowcount
            raise RuntimeError("hỏng giữa khối — cố ý")
    except RuntimeError:
        kq["da_lui"] = True
    kq["ben"] = _dem(dg, "SELECT count(*) c FROM w_gd WHERE id=2")
    kq["mong"] = "0"
    return kq


def t4_cau_sau_loi_trong_giao_dich(dg):
    """Câu chạy SAU một câu hỏng, trong CÙNG giao dịch.

    SQLite (`RAISE(ABORT)`/lỗi ràng buộc) chỉ huỷ CÂU ⇒ câu sau chạy được và commit.
    PostgreSQL huỷ CẢ GIAO DỊCH (25P02) ⇒ câu sau KHÔNG chạy, và `COMMIT` thành `ROLLBACK`.
    """
    kq = {}
    with dg.giao_dich():
        try:
            dg.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (3, 30))
            dg.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (3, 31))     # trùng khoá
            kq["loi_1"] = None
        except Exception as e:                                          # noqa: BLE001
            kq["loi_1"] = loai_loi(e)
            kq["sqlstate_1"] = getattr(e, "sqlstate", None)
        try:
            c = dg.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (4, 40))
            kq["rc_cau_sau"] = c.rowcount
            kq["loi_2"] = None
        except Exception as e:                                          # noqa: BLE001
            kq["rc_cau_sau"] = None
            kq["loi_2"] = loai_loi(e)
            kq["sqlstate_2"] = getattr(e, "sqlstate", None)
    kq["ben_3"] = _dem(dg, "SELECT count(*) c FROM w_gd WHERE id=3")
    kq["ben_4"] = _dem(dg, "SELECT count(*) c FROM w_gd WHERE id=4")
    kq["mong"] = "SQLite: câu sau chạy (1) và BỀN · PostgreSQL: 25P02 và KHÔNG bền"
    return kq


def t5_khoa_het_gio(dg, la_pg):
    """KHOA_HẾT_GIỜ — một kết nối khác đang giữ khoá HÀNG: lượt ghi phải THẤT BẠI RÕ, không ghi gì."""
    kq = {}
    if la_pg:
        giu = dg.cum.mo(dg.db, tu_dong_chot=True, ten="giu-khoa")
        giu.execute("BEGIN")
        giu.execute("UPDATE w_lock SET x=x+1 WHERE id=1")
        dg.chay_sql("SET lock_timeout='400ms'")
    else:
        import sqlite3
        giu = sqlite3.connect(dg.cau_hinh.DUONG_DAN_CSDL, timeout=5, isolation_level=None)
        giu.execute("BEGIN IMMEDIATE")
        giu.execute("UPDATE w_lock SET x=x+1 WHERE id=1")
        dg.mo().execute("PRAGMA busy_timeout=%d" % 400)     # CHỈ hạ thời gian CHỜ cho phép đo
    try:
        try:
            c = dg.ghi("UPDATE w_lock SET x=? WHERE id=?", (99, 1))
            kq["rowcount"] = c.rowcount
            kq["loi"] = None
        except Exception as e:                                       # noqa: BLE001
            kq["rowcount"] = None
            kq["loi"] = loai_loi(e)
            kq["sqlstate"] = getattr(e, "sqlstate", None)
        try:
            giu.execute("ROLLBACK")
        except Exception:                                            # noqa: BLE001
            pass
        kq["x_that"] = _dem(dg, "SELECT x FROM w_lock WHERE id=1")
        kq["mong"] = ("x_that=0: lượt ghi bị TỪ CHỐI nên không để lại dấu vết (số 99 không vào), "
                      "và +1 của bên giữ khoá đã bị chính nó lùi")
    finally:
        try:
            if la_pg:
                giu.close()
            else:
                giu.close()
        except Exception:                                            # noqa: BLE001
            pass
    return kq


def t3_chua_chot(dg_khong_tu_chot):
    """MẤT-IM-LẶNG #1 — chế độ MẶC ĐỊNH của psycopg2 (không tự chốt): `rowcount` trả 1,
    nhưng dòng CHƯA vào kho và bốc hơi khi đóng kết nối. Không một lỗi nào được ném ra.

    Vế SQLite của ca này là một lượt `ghi()` THƯỜNG (csdl.mo() ở `isolation_level=None`:
    mỗi câu tự chốt) — xem `t1`/`dem` trong báo cáo.
    """
    kq = {}
    c = dg_khong_tu_chot.ghi("INSERT INTO w_gd (id,x) VALUES (?,?)", (5, 50))
    kq["rowcount"] = c.rowcount
    kq["loi"] = None
    kq["ben_truoc_khi_dong"] = dg_khong_tu_chot.doc_kiem_chung(
        _doi(dg_khong_tu_chot, "SELECT count(*) c FROM w_gd WHERE id=5"))[0][0]
    dg_khong_tu_chot.dong()
    kq["ben_sau_khi_dong"] = dg_khong_tu_chot.doc_kiem_chung(
        _doi(dg_khong_tu_chot, "SELECT count(*) c FROM w_gd WHERE id=5"))[0][0]
    kq["mong"] = "SQLite: 1 · PostgreSQL không tự chốt: 0 (IM LẶNG)"
    return kq


def _doi(dg, sql):
    """SQL đọc kiểm chứng dùng chung cho cả hai kho: `tenants`/`w_gd` không có gì riêng biệt."""
    return sql


def chay_nhom_giao_dich(dg, la_pg, dg_khong_tu_chot=None):
    """Chạy nhóm T trên MỘT đường ghi. Trả dict `{mã: kết quả}`."""
    chuan_bi_giao_dich(dg)
    ra = {
        "T1_chot_thanh_cong": t1_chot_thanh_cong(dg),
        "T2_lui_khi_hong": t2_lui_khi_hong(dg),
        "T4_cau_sau_loi": t4_cau_sau_loi_trong_giao_dich(dg),
        "T5_khoa_het_gio": t5_khoa_het_gio(dg, la_pg),
    }
    if dg_khong_tu_chot is not None:
        ra["T3_chua_chot"] = t3_chua_chot(dg_khong_tu_chot)
    return ra


# =========================================================== MẤT CẬP NHẬT — 2 KIỂU, TIẾN TRÌNH THẬT
def tho_mota(sock, cong, nguoi, db, vong, kho, kieu="ngay_tho"):
    """Tiến trình THO: khuôn ĐỌC-RỒI-GHI ngây thơ qua CHÍNH `mot()` + `ghi()` của đường ghi.

    Chạy bằng TIẾN TRÌNH RIÊNG, không bằng thread: `khoa_ghi` của Python chỉ phủ MỘT tiến trình,
    đo bằng thread là đo chính cái khoá đó rồi kết luận "an toàn" cho cả nơi nó không phủ.

    `kieu="nguyen_tu"` là ĐỐI CHỨNG DƯƠNG của đồng hồ đo: cùng số tiến trình, cùng số vòng,
    nhưng phép cộng nằm gọn trong MỘT câu (`dem = dem + 1`) — khuôn này PHẢI cho `mất = 0`.
    Thiếu vế này thì một đồng hồ luôn báo "mất" cũng "đạt" ở bảng kia.
    """
    import json as _json
    duong = None
    if kho == "pg":
        duong = DuongGhiPG(_CumNgoai(sock, cong, nguoi), db)
    else:
        duong = DuongGhiSQLite(os.path.dirname(db or ""), tu_don=False)
    tin, loi, loi_dau = 0, 0, None
    try:
        for _ in range(vong):
            try:
                if kieu == "nguyen_tu":
                    duong.ghi("UPDATE w_dem SET dem = dem + 1 WHERE id=?", (1,))
                else:
                    r = duong.mot("SELECT dem FROM w_dem WHERE id=?", (1,))
                    duong.ghi("UPDATE w_dem SET dem=? WHERE id=?", (int(r["dem"]) + 1, 1))
                tin += 1
            except Exception as e:                                   # noqa: BLE001
                loi += 1
                if loi_dau is None:
                    loi_dau = "%s: %s" % (type(e).__name__, str(e)[:80])
    finally:
        duong.dong()
    print(_json.dumps({"kho": kho, "kieu": kieu, "tin_chot": tin, "loi": loi, "loi_dau": loi_dau}))


class _CumNgoai(object):
    """Bọc một cụm ĐANG CHẠY (do tiến trình cha dựng) — chỉ để lấy `dsn`. Không dựng, không dọn."""

    def __init__(self, sock, cong, nguoi):
        kiem_cong_an_toan(cong)
        self.sock, self.cong, self.nguoi = sock, str(cong), nguoi

    def dsn(self, db):
        return lp.dsn(self.sock, self.cong, self.nguoi, db)

    def mo(self, db, tu_dong_chot=True, ten="pg"):
        return lp.KetNoi(self.dsn(db), tu_dong_chot=tu_dong_chot, ten=ten)


def chay_mot_cap_doi(sock, cong, nguoi, db, vong, so_tien_trinh, kho, duong_dan_sqlite=None,
                     kieu="ngay_tho"):
    """Chạy `so_tien_trinh` tiến trình THO song song, rồi đọc giá trị THẬT. Trả dict số đo."""
    import json as _json
    con = []
    for _ in range(so_tien_trinh):
        if kho == "pg":
            co = [sys.executable, os.path.abspath(__file__), "--tho-mota", sock, cong, nguoi,
                  db, str(vong), "pg", kieu]
        else:
            co = [sys.executable, os.path.abspath(__file__), "--tho-mota", "", "", "",
                  duong_dan_sqlite or "", str(vong), "sqlite", kieu]
        con.append(subprocess.Popen(co, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, cwd=GOC))
    tin = loi = 0
    loi_dau = None
    for p in con:
        out, err = p.communicate()
        dong = [d for d in out.splitlines() if d.strip().startswith("{")]
        if not dong:
            raise RuntimeError("tiến trình tho không trả kết quả: %s" % (err or out)[-300:])
        d = _json.loads(dong[-1])
        tin += d["tin_chot"]
        loi += d["loi"]
        loi_dau = loi_dau or d["loi_dau"]
    if kho == "pg":
        kt = _CumNgoai(sock, cong, nguoi)
        kn = kt.mo(db)
        that = int(kn.execute("SELECT dem FROM w_dem WHERE id=1").fetchone()["dem"])
        kn.close()
    else:
        import sqlite3
        kn = sqlite3.connect(duong_dan_sqlite)
        that = int(kn.execute("SELECT dem FROM w_dem WHERE id=1").fetchone()[0])
        kn.close()
    return {"kho": kho, "kieu": kieu, "tien_trinh": so_tien_trinh, "vong_moi_tien_trinh": vong,
            "tin_da_chot": tin, "gia_tri_that": that, "mat": tin - that,
            "loi": loi, "loi_dau": loi_dau}


# =========================================================== BẢN TẤT ĐỊNH (bắt tay qua tệp mốc)
def _cham(thu_muc, ten):
    with open(os.path.join(thu_muc, ten), "w") as f:
        f.write("x")


def _doi_moc(thu_muc, ten, het_gio=20.0):
    duong = os.path.join(thu_muc, ten)
    t0 = time.time()
    while time.time() - t0 < het_gio:
        if os.path.exists(duong):
            return True
        time.sleep(0.02)
    return False


def tho_tay_doi(sock, cong, nguoi, db, kho, vai, thu_muc_moc):
    """Tiến trình THO của bản TẤT ĐỊNH: đọc → BẮT TAY (cả hai đã đọc xong) → ghi giá trị đã đọc + 1.

    Vì sao cần bản này bên cạnh bản đua: bản đua phụ thuộc lịch trình của hệ điều hành, nên nó
    chỉ nói được "mất > 0" chứ không nói được "mất đúng 1". Bản bắt tay ÉP thứ tự, nên kết quả
    là con số chắc chắn — và một con số chắc chắn thì mới chốt được vào bộ thử hồi quy.
    """
    import json as _json
    if kho == "pg":
        duong = DuongGhiPG(_CumNgoai(sock, cong, nguoi), db)
    else:
        duong = DuongGhiSQLite(os.path.dirname(db or ""), tu_don=False)
    kq = {"kho": kho, "vai": vai, "da_doc": None, "loi": None, "da_ghi": False}
    try:
        r = duong.mot("SELECT dem FROM w_dem WHERE id=?", (1,))
        kq["da_doc"] = int(r["dem"])
        _cham(thu_muc_moc, "%s_da_doc" % vai)
        _doi_moc(thu_muc_moc, "di", 20.0)          # chờ cha cho phép: CẢ HAI đã đọc xong
        duong.ghi("UPDATE w_dem SET dem=? WHERE id=?", (kq["da_doc"] + 1, 1))
        kq["da_ghi"] = True
        _cham(thu_muc_moc, "%s_da_ghi" % vai)
    except Exception as e:                          # noqa: BLE001
        kq["loi"] = "%s: %s" % (type(e).__name__, str(e)[:100])
    finally:
        duong.dong()
    print(_json.dumps(kq))


def chay_tay_doi(sock, cong, nguoi, db, kho, duong_dan_sqlite=None):
    """Chạy HAI tiến trình thật theo kịch bản bắt tay. Trả dict số đo (mất phải ĐÚNG BẰNG 1)."""
    import json as _json
    moc = tempfile.mkdtemp(prefix="vh-moc-")
    con = {}
    try:
        for vai in ("A", "B"):
            if kho == "pg":
                co = [sys.executable, os.path.abspath(__file__), "--tho-tay-doi", sock, cong,
                      nguoi, db, "pg", vai, moc]
            else:
                co = [sys.executable, os.path.abspath(__file__), "--tho-tay-doi", "", "", "",
                      duong_dan_sqlite or "", "sqlite", vai, moc]
            con[vai] = subprocess.Popen(co, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, cwd=GOC)
        # Chờ CẢ HAI đọc xong rồi mới mở cổng — đây là chỗ ép thứ tự, không phải chỗ đợi may rủi.
        for vai in ("A", "B"):
            if not _doi_moc(moc, "%s_da_doc" % vai, 20.0):
                for p in con.values():
                    p.kill()
                chi_tiet = {v: (p.communicate()[1] or "")[-300:] for v, p in con.items()}
                raise RuntimeError("tiến trình %s không đọc xong trong 20 giây · stderr: %r"
                                   % (vai, chi_tiet))
        _cham(moc, "di")
        kq_tho = {}
        for vai, p in con.items():
            out, err = p.communicate()
            dong = [d for d in out.splitlines() if d.strip().startswith("{")]
            if not dong:
                raise RuntimeError("tiến trình %s không trả kết quả: %s" % (vai, (err or out)[-200:]))
            kq_tho[vai] = _json.loads(dong[-1])
    finally:
        shutil.rmtree(moc, ignore_errors=True)
    if kho == "pg":
        kn = _CumNgoai(sock, cong, nguoi).mo(db)
        that = int(kn.execute("SELECT dem FROM w_dem WHERE id=1").fetchone()["dem"])
        kn.close()
    else:
        import sqlite3
        kn = sqlite3.connect(duong_dan_sqlite)
        that = int(kn.execute("SELECT dem FROM w_dem WHERE id=1").fetchone()[0])
        kn.close()
    tin = sum(1 for v in kq_tho.values() if v["da_ghi"])
    return {"kho": kho, "kieu": "tay_doi", "tin_da_chot": tin, "gia_tri_that": that,
            "mat": tin - that, "loi": sum(1 for v in kq_tho.values() if v["loi"]),
            "loi_dau": next((v["loi"] for v in kq_tho.values() if v["loi"]), None),
            "da_doc": {k: v["da_doc"] for k, v in kq_tho.items()},
            # TỰ KIỂM BỎ ĐỒ của chính kịch bản: hai bên phải đọc CÙNG một giá trị, nếu không thì
            # "bắt tay" đã hỏng và con số mất=1 bên dưới không nói lên điều gì.
            "cung_gia_tri_doc": len(set(v["da_doc"] for v in kq_tho.values())) == 1}


# =========================================================== BẪY IDENTITY (đo được, không suy ra)
DDL_IDT_SQLITE = "CREATE TABLE IF NOT EXISTS w_idt (id INTEGER PRIMARY KEY AUTOINCREMENT, x INTEGER NOT NULL)"
DDL_IDT_PG = ("CREATE TABLE IF NOT EXISTS w_idt "
              "(id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, x INTEGER NOT NULL)")


def do_bay_identity(dg, la_pg):
    """BẪY: chèn một dòng với `id` TƯỜNG MINH, rồi chèn một dòng KIỂU SẢN PHẨM (không có `id`).

    Đây là khuôn có thật: di trú dữ liệu / seed / phục hồi sao lưu đều chèn `id` tường minh,
    còn mã nghiệp vụ (`csdl.ghi`) thì **không** — nó dựa vào `id` tự sinh.

    * SQLite (`INTEGER PRIMARY KEY AUTOINCREMENT`): id tự sinh = `max(rowid) + 1` ⇒ **chạy**.
    * PostgreSQL (`GENERATED BY DEFAULT AS IDENTITY`): id tự sinh lấy từ **sequence**, mà
      sequence **không biết** lượt chèn tường minh nào ⇒ trả lại `1` ⇒ **`23505` trùng khoá**.

    Suy ra từ tài liệu là chưa đủ — ở đây nó được ĐO, và đo trên chính bảng dịch từ schema sản phẩm.
    """
    dg.chay_sql("DROP TABLE IF EXISTS w_idt")
    dg.chay_sql(DDL_IDT_PG if la_pg else DDL_IDT_SQLITE)
    kq = {}
    try:
        c = dg.ghi("INSERT INTO w_idt (id,x) VALUES (?,?)", (1, 10))
        kq["chen_tuong_minh"] = c.rowcount
        kq["chen_tuong_minh_loi"] = None
    except Exception as e:                                            # noqa: BLE001
        kq["chen_tuong_minh"] = None
        kq["chen_tuong_minh_loi"] = loai_loi(e)
    try:
        c = dg.ghi("INSERT INTO w_idt (x) VALUES (?)", (20,))
        kq["chen_kieu_san_pham"] = c.rowcount
        kq["loi"] = None
        kq["sqlstate"] = None
    except Exception as e:                                            # noqa: BLE001
        kq["chen_kieu_san_pham"] = None
        kq["loi"] = loai_loi(e)
        kq["sqlstate"] = getattr(e, "sqlstate", None)
    kq["so_dong"] = _dem(dg, "SELECT count(*) c FROM w_idt")
    kq["mong"] = "SQLite: chèn được (2 dòng) · PostgreSQL: 23505 (1 dòng)"
    return kq


# =========================================================== tự kiểm
def _tu_kiem():
    import cau_hinh
    import sinh_ddl_pg
    cum = CumGhi()
    print("── dựng cụm riêng (cổng %s, socket /tmp/vhpg.XXXX, listen_addresses='')" % cum.cong)
    cum.dung()
    try:
        cum.tao_csdl("vh_g18_ghi")
        ddl = sinh_ddl_pg.sinh()[0]
        a = DuongGhiSQLite()
        b = DuongGhiPG(cum, "vh_g18_ghi")
        try:
            chuan_bi_sqlite(a)
            chuan_bi_pg(b, ddl, cau_hinh.GOI_MAC_DINH)
            kq_a = [chay_ca(a, ca, False) for ca in CA_GHI]
            kq_b = [chay_ca(b, ca, True) for ca in CA_GHI]
        finally:
            a.dong()
            b.dong()
        print("\n%-5s %-32s %-9s %-9s %-9s %s" % ("mã", "ca", "SQLite", "đọc lại", "Postgres", "kiểm chứng"))
        for x, y in zip(kq_a, kq_b):
            mo_ta = dict((c["ma"], c["mo_ta"]) for c in CA_GHI)[x["ma"]][:32]
            print("%-5s %-32s %-9s %-9s %-9s %s/%s" % (
                x["ma"], mo_ta,
                x["rowcount"] if x["loi"] is None else "LỖI:" + x["loi"],
                x["rowcount_sau_doc"],
                y["rowcount"] if y["loi"] is None else "LỖI:" + y["loi"],
                "OK" if x["kiem_dat"] else "SAI", "OK" if y["kiem_dat"] else "SAI"))
        lech, giong = so_sanh(kq_a, kq_b)
        print("\nGiống nhau: %d/%d · Lệch: %d" % (len(giong), len(CA_GHI), len(lech)))
        for d in lech:
            print("   · %-5s SQLite %r/%s/%r  vs  PostgreSQL %r/%s/%r" % (
                d["ma"], d["sqlite"]["rowcount"], d["sqlite"]["loai_loi"],
                d["sqlite"]["rowcount_sau_doc"], d["pg"]["rowcount"],
                d["pg"]["loai_loi"], d["pg"]["rowcount_sau_doc"]))
    finally:
        cum.dong()
        con = sorted(d for d in os.listdir("/tmp") if d.startswith("vhpg."))
        print("\n/tmp/vhpg.* còn lại: %d %s" % (len(con), con))
    return 0


def _main(argv):
    if len(argv) > 1 and argv[1] == "--tho-tay-doi":
        # script --tho-tay-doi <sock> <cong> <nguoi> <db|duong_dan_sqlite> <kho> <vai> <thu_muc_moc>
        kho, vai, moc = argv[6], argv[7], argv[8]
        if kho == "sqlite":
            tho_tay_doi("", "", "", argv[5], "sqlite", vai, moc)
        else:
            tho_tay_doi(argv[2], argv[3], argv[4], argv[5], "pg", vai, moc)
        return 0
    if len(argv) > 1 and argv[1] == "--tho-mota":
        # script --tho-mota <sock> <cong> <nguoi> <db|duong_dan_sqlite> <vong> <kho> [kieu]
        kho = argv[7]
        kieu = argv[8] if len(argv) > 8 else "ngay_tho"
        if kho == "sqlite":
            tho_mota("", "", "", argv[5], int(argv[6]), "sqlite", kieu)
        else:
            tho_mota(argv[2], argv[3], argv[4], argv[5], int(argv[6]), "pg", kieu)
        return 0
    return _tu_kiem()


if __name__ == "__main__":
    sys.exit(_main(sys.argv))

