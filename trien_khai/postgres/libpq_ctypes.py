#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CẦU NỐI libpq TỐI THIỂU qua `ctypes` — để đo `rowcount` của PostgreSQL mà không cài gì.

====== VÌ SAO TỆP NÀY TỒN TẠI ======
Việc G18/AG-05: đo **giá trị `rowcount` mà đường GHI THẬT của sản phẩm (`csdl.ghi`) trả về**
trên PostgreSQL, đối chiếu với SQLite. Muốn đo thì phải có một trình điều khiển PostgreSQL
chạy được trong tiến trình Python này.

Máy đo **không có** `psycopg2`/`psycopg`. Ba đường, và đây là lý do chọn đường thứ ba:

| Đường | Vì sao không dùng |
|---|---|
| `pip install psycopg2-binary` | Sửa môi trường Python của máy ngoài khu được cấp quyền ghi; và bộ thử sẽ **BỎ QUA** trên máy không có gói đó — tức lớp ca mới hiện dấu ✓ mà chạy 0 ca, đúng cái bẫy đã ghi ở đầu `app/thu/thu_postgres.py` |
| `psql` rồi đọc nhãn lệnh | `psql -q` **KHÔNG in** nhãn `INSERT 0 1`/`UPDATE 3` (đã đo: cột `out` rỗng ở mọi câu DML). Phải bật lại chế độ in rồi **tự phân tích chuỗi** — lúc đó con số là do *bộ phân tích của tôi* sinh ra, không phải do máy chủ |
| **`ctypes` + `libpq`** | **CHỌN.** `libpq` đã có sẵn trên máy (nó là thư viện `psql` đang dùng), và `PQcmdTuples` chính là **nguồn số mà `psycopg2.rowcount` đọc**. Đo qua đây là đo đúng con số sản phẩm sẽ nhận, không qua một bản diễn giải trung gian |

====== PHẠM VI — ĐỌC KỸ ======
Đây là **cầu nối để ĐO**, không phải một trình điều khiển production và không phải đề xuất
dùng nó làm trình điều khiển của sản phẩm. Nó cố ý **mô phỏng đúng những chỗ đã đo được của
`psycopg2`** để phép đối chiếu có nghĩa:

* `rowcount` lấy từ `PQcmdTuples`; chuỗi rỗng (lệnh không có số dòng, ví dụ `CREATE TABLE`)
  → **`-1`** — đúng như `psycopg2` trả.
* Câu có tập kết quả (`SELECT`) → `rowcount` = **số dòng trả về** — đúng như `psycopg2`.
* **KHÔNG có `lastrowid`.** `psycopg2` không có thuộc tính đó, nên ở đây cũng không định
  nghĩa nó: `cur.lastrowid` ném `AttributeError` y như thật. Đây là phép đo, không phải thiếu sót.
* Lỗi SQLSTATE `23xxx` → `LoiToanVen`; còn lại → `LoiVanHanh`. Trùng tên **nghiệp vụ** với
  `csdl.LoiToanVen`/`csdl.LoiVanHanh` (xem `app/csdl.py` dòng 233–239) — đó là hai cái tên
  mã nghiệp vụ đang bắt, không phải tên driver.
* `tu_dong_chot=False` mô phỏng chế độ **mặc định của `psycopg2`**: `BEGIN` tự động trước câu
  đầu, và `commit()` mới chốt. `tu_dong_chot=True` mô phỏng chế độ của `csdl.mo()` hiện nay
  (`isolation_level=None`: mỗi câu tự chốt).

**KHÔNG** hỗ trợ: tham số nhị phân, `COPY`, thông báo `LISTEN/NOTIFY`, pool, truy vấn bất đồng bộ.
Ngoài phạm vi thì nói ra, không giả vờ.

CHẠY THỬ
--------
    python3 trien_khai/postgres/libpq_ctypes.py            # tự kiểm cầu nối, cần một cụm đang chạy
    VHPG_SOCKET=/tmp/vhpg.XXXX python3 trien_khai/postgres/libpq_ctypes.py
"""
import ctypes
import ctypes.util
import os

# ------------------------------------------------------------------ hằng số libpq
CONNECTION_OK = 0
PGRES_EMPTY_QUERY = 0
PGRES_COMMAND_OK = 1
PGRES_TUPLES_OK = 2
PGRES_COPY_OUT = 3
PGRES_COPY_IN = 4
PGRES_BAD_RESPONSE = 5
PGRES_NONFATAL_ERROR = 6
PGRES_FATAL_ERROR = 7
PGRES_COPY_BOTH = 8
PGRES_SINGLE_TUPLE = 9
PG_DIAG_SQLSTATE = ord("C")

DUONG_LIBPQ = (
    os.environ.get("VHPG_LIBPQ", ""),
    "/opt/homebrew/lib/libpq.dylib",
    "/opt/homebrew/opt/postgresql@16/lib/libpq.dylib",
    "/usr/local/opt/postgresql@16/lib/libpq.dylib",
    "/usr/lib/libpq.dylib",
    "/usr/lib/x86_64-linux-gnu/libpq.so.5",
    "/usr/lib/aarch64-linux-gnu/libpq.so.5",
)


def nap_libpq(duong=None):
    """Nạp `libpq`. Trả `(thư_viện, đường_dẫn)`. Ném `OSError` nói RÕ đã thử những đâu."""
    ung_vien = [duong] if duong else []
    ung_vien += [d for d in DUONG_LIBPQ if d]
    tim = ctypes.util.find_library("pq")
    if tim:
        ung_vien.append(tim)
    da_thu = []
    for cand in ung_vien:
        if not cand or cand in da_thu:
            continue
        da_thu.append(cand)
        try:
            return ctypes.CDLL(cand), cand
        except OSError:
            continue
    raise OSError("không nạp được libpq; đã thử: %s. Đặt VHPG_LIBPQ=<đường dẫn .dylib/.so>."
                  % ", ".join(da_thu))


def _gan(lib):
    """Khai báo kiểu tham số/trả về. Thiếu bước này thì con trỏ bị cắt còn 32 bit và SEGFAULT."""
    p = ctypes.c_void_p
    cp = ctypes.c_char_p
    ci = ctypes.c_int
    lib.PQlibVersion.restype = ci
    lib.PQconnectdb.argtypes = [cp]
    lib.PQconnectdb.restype = p
    lib.PQstatus.argtypes = [p]
    lib.PQstatus.restype = ci
    lib.PQerrorMessage.argtypes = [p]
    lib.PQerrorMessage.restype = cp
    lib.PQserverVersion.argtypes = [p]
    lib.PQserverVersion.restype = ci
    lib.PQfinish.argtypes = [p]
    lib.PQfinish.restype = None
    lib.PQexec.argtypes = [p, cp]
    lib.PQexec.restype = p
    lib.PQexecParams.argtypes = [p, cp, ci, p, ctypes.POINTER(cp), p, p, ci]
    lib.PQexecParams.restype = p
    lib.PQresultStatus.argtypes = [p]
    lib.PQresultStatus.restype = ci
    lib.PQresultErrorMessage.argtypes = [p]
    lib.PQresultErrorMessage.restype = cp
    lib.PQresultErrorField.argtypes = [p, ci]
    lib.PQresultErrorField.restype = cp
    lib.PQntuples.argtypes = [p]
    lib.PQntuples.restype = ci
    lib.PQnfields.argtypes = [p]
    lib.PQnfields.restype = ci
    lib.PQfname.argtypes = [p, ci]
    lib.PQfname.restype = cp
    lib.PQgetvalue.argtypes = [p, ci, ci]
    lib.PQgetvalue.restype = cp
    lib.PQgetisnull.argtypes = [p, ci, ci]
    lib.PQgetisnull.restype = ci
    lib.PQcmdTuples.argtypes = [p]
    lib.PQcmdTuples.restype = cp
    lib.PQcmdStatus.argtypes = [p]
    lib.PQcmdStatus.restype = cp
    lib.PQclear.argtypes = [p]
    lib.PQclear.restype = None
    return lib


_LIB = None
_DUONG = None


def libpq():
    global _LIB, _DUONG
    if _LIB is None:
        _LIB, _DUONG = nap_libpq()
        _gan(_LIB)
    return _LIB


def duong_dan_libpq():
    libpq()
    return _DUONG


def phien_ban_libpq():
    return libpq().PQlibVersion()


# ------------------------------------------------------------------ lỗi
class LoiPG(Exception):
    """Lỗi tầng CSDL. Mang `sqlstate` — phán bằng MÃ, không bằng chữ trong thông báo."""

    def __init__(self, thong_diep, sqlstate=None):
        Exception.__init__(self, thong_diep)
        self.sqlstate = sqlstate


class LoiToanVen(LoiPG):
    """Vi phạm UNIQUE / FOREIGN KEY / CHECK / NOT NULL (SQLSTATE 23xxx)."""


class LoiVanHanh(LoiPG):
    """Khoá, hết giờ, giao dịch đã hỏng, cú pháp (mọi thứ còn lại)."""


def _lop_loi(sqlstate):
    if sqlstate and sqlstate.startswith("23"):
        return LoiToanVen
    return LoiVanHanh


# ------------------------------------------------------------------ hàng
class Hang(object):
    """Một hàng truy cập được theo TÊN cột — mượn dạng của `sqlite3.Row` để mã đọc giống nhau."""

    __slots__ = ("_ten", "_gt", "_null")

    def __init__(self, ten, gt, null):
        self._ten, self._gt, self._null = ten, gt, null

    def __getitem__(self, k):
        if isinstance(k, int):
            return None if self._null[k] else self._gt[k]
        try:
            i = self._ten.index(k)
        except ValueError:
            raise IndexError("không có cột %r; có: %s" % (k, self._ten))
        return None if self._null[i] else self._gt[i]

    def keys(self):
        return list(self._ten)

    def __iter__(self):
        return iter(self[k] for k in range(len(self._ten)))

    def __len__(self):
        return len(self._ten)

    def __repr__(self):
        return "Hang(%s)" % ", ".join("%s=%r" % (k, self[k]) for k in self._ten)


# ------------------------------------------------------------------ con trỏ
class ConTro(object):
    """Con trỏ mô phỏng ĐÚNG những gì `psycopg2` phơi ra — không thêm, không bớt.

    CỐ Ý KHÔNG có `lastrowid`: `psycopg2` không có nó, nên mã sản phẩm gọi `.lastrowid` sẽ
    ném `AttributeError` — và đó là một phép ĐO, không phải một thiếu sót của cầu nối.
    """

    def __init__(self, hang_loat, rowcount, trang_thai, thong_diep="", sqlstate=None):
        self._hang = hang_loat
        self.rowcount = rowcount
        self.trang_thai = trang_thai
        self.thong_diep = thong_diep
        self.sqlstate = sqlstate
        self._i = 0
        self._con_tro_gan = None       # giữ vòng đời

    # -- đọc
    def fetchone(self):
        if self._i >= len(self._hang):
            return None
        r = self._hang[self._i]
        self._i += 1
        return r

    def fetchall(self):
        r = self._hang[self._i:]
        self._i = len(self._hang)
        return list(r)

    def __iter__(self):
        while True:
            r = self.fetchone()
            if r is None:
                return
            yield r

    def close(self):
        self._hang = []


def _doc_ket_qua(lib, res):
    """Đổi `PGresult*` thành (danh sách Hàng, rowcount, trạng thái, thông điệp, sqlstate)."""
    tt = lib.PQresultStatus(res)
    if tt not in (PGRES_COMMAND_OK, PGRES_TUPLES_OK, PGRES_EMPTY_QUERY):
        sqlstate = lib.PQresultErrorField(res, PG_DIAG_SQLSTATE)
        sqlstate = sqlstate.decode("utf-8", "replace") if sqlstate else None
        loi = lib.PQresultErrorMessage(res)
        loi = loi.decode("utf-8", "replace").strip() if loi else "lỗi PostgreSQL không rõ"
        raise _lop_loi(sqlstate)(loi, sqlstate)

    nf = lib.PQnfields(res)
    if tt == PGRES_TUPLES_OK:
        ten = [lib.PQfname(res, j).decode("utf-8", "replace") for j in range(nf)]
        nt = lib.PQntuples(res)
        hang = []
        for i in range(nt):
            gt = [(lib.PQgetvalue(res, i, j) or b"").decode("utf-8", "replace") for j in range(nf)]
            null = [bool(lib.PQgetisnull(res, i, j)) for j in range(nf)]
            hang.append(Hang(ten, gt, null))
        # psycopg2: câu có tập kết quả → rowcount = SỐ DÒNG trả về (KHÁC sqlite3, xem báo cáo).
        return hang, nt, tt, "", None

    # Lệnh không có tập kết quả: số dòng = PQcmdTuples; rỗng → -1 (đúng như psycopg2).
    tho = lib.PQcmdTuples(res)
    tho = tho.decode("ascii", "replace") if tho else ""
    rc = int(tho) if tho.strip().isdigit() else -1
    return [], rc, tt, "", None


class KetNoi(object):
    """Một kết nối PostgreSQL. `tu_dong_chot=True` ⇒ mỗi câu tự chốt (giống `csdl.mo()`)."""

    def __init__(self, dsn, tu_dong_chot=True, ten="ket_noi"):
        self.dsn = dsn
        self.tu_dong_chot = tu_dong_chot
        self.ten = ten
        self._lib = libpq()
        self._conn = self._lib.PQconnectdb(dsn.encode("utf-8"))
        if not self._conn:
            raise LoiVanHanh("PQconnectdb trả con trỏ NULL")
        if self._lib.PQstatus(self._conn) != CONNECTION_OK:
            loi = self._lib.PQerrorMessage(self._conn)
            loi = loi.decode("utf-8", "replace").strip() if loi else "không rõ"
            self._lib.PQfinish(self._conn)
            self._conn = None
            raise LoiVanHanh("không kết nối được: " + loi)
        self._trong_giao_dich = False

    # -- nội bộ
    def _exec(self, sql, tham_so=None):
        if self._conn is None:
            raise LoiVanHanh("kết nối đã đóng")
        if tham_so:
            gt = [None if v is None else str(v).encode("utf-8") for v in tham_so]
            mang = (ctypes.c_char_p * (len(gt) + 1))()
            for i, v in enumerate(gt):
                mang[i] = v
            mang[len(gt)] = None
            res = self._lib.PQexecParams(self._conn, sql.encode("utf-8"), len(gt),
                                         None, mang, None, None, 0)
        else:
            res = self._lib.PQexec(self._conn, sql.encode("utf-8"))
        if not res:
            raise LoiVanHanh("PQexec trả con trỏ NULL: %s"
                             % (self._lib.PQerrorMessage(self._conn) or b"").decode("utf-8", "replace"))
        try:
            return _doc_ket_qua(self._lib, res)
        finally:
            self._lib.PQclear(res)

    def _mo_giao_dich(self):
        """Mô phỏng `psycopg2` mặc định: câu đầu tiên tự mở `BEGIN`, chốt khi gọi `commit()`."""
        if not self.tu_dong_chot and not self._trong_giao_dich:
            self._exec("BEGIN")
            self._trong_giao_dich = True

    # -- API
    def execute(self, sql, tham_so=None):
        self._mo_giao_dich()
        hang, rc, tt, td, ss = self._exec(sql, tham_so)
        return ConTro(hang, rc, tt, td, ss)

    def commit(self):
        if self._trong_giao_dich:
            self._exec("COMMIT")
            self._trong_giao_dich = False

    def rollback(self):
        if self._trong_giao_dich:
            self._exec("ROLLBACK")
            self._trong_giao_dich = False

    def close(self):
        """`psycopg2` lùi giao dịch còn dở khi đóng. Mô phỏng đúng như vậy — đó là chỗ IM LẶNG."""
        if self._conn is None:
            return
        if self._trong_giao_dich:
            try:
                self._exec("ROLLBACK")
            except LoiPG:
                pass
            self._trong_giao_dich = False
        self._lib.PQfinish(self._conn)
        self._conn = None

    @property
    def da_dong(self):
        return self._conn is None


def dsn(sock, cong, nguoi="vhtest", db="postgres"):
    """Chuỗi kết nối qua SOCKET UNIX. Không có `host=` TCP nào ở đây — cố ý."""
    return "host=%s port=%s user=%s dbname=%s" % (sock, cong, nguoi, db)


# ------------------------------------------------------------------ tự kiểm cầu nối
def _tu_kiem():
    sock = os.environ.get("VHPG_SOCKET", "")
    cong = os.environ.get("VHPG_CONG", "55432")
    nguoi = os.environ.get("VHPG_NGUOI", "vhtest")
    if not sock:
        print("CẦN VHPG_SOCKET trỏ tới socket của một cụm thử (xem dung_cum_thu.sh).")
        return 2
    print("libpq: %s · phiên bản %d" % (duong_dan_libpq(), phien_ban_libpq()))
    kn = KetNoi(dsn(sock, cong, nguoi))
    try:
        c = kn.execute("SELECT 1 AS mot, NULL::text AS khong")
        r = c.fetchone()
        print("SELECT 1 · rowcount=%r · mot=%r · khong=%r" % (c.rowcount, r["mot"], r["khong"]))
        kn.execute("CREATE TEMP TABLE _t (id int primary key, x int)")
        for nhan, sql, ts in [
            ("INSERT", "INSERT INTO _t (id,x) VALUES (?,?)", (1, 10)),
            ("UPDATE khop", "UPDATE _t SET x=? WHERE id=?", (11, 1)),
            ("UPDATE khong khop", "UPDATE _t SET x=? WHERE id=?", (12, 99)),
            ("DELETE khong khop", "DELETE FROM _t WHERE id=?", (99,)),
            ("ON CONFLICT DO NOTHING trung", "INSERT INTO _t (id,x) VALUES (?,?) ON CONFLICT DO NOTHING",
             (1, 99)),
        ]:
            c = kn.execute(sql, ts)
            print("%-30s rowcount=%r" % (nhan, c.rowcount))
        try:
            kn.execute("INSERT INTO _t (id,x) VALUES (?,?)", (1, 1))
        except LoiToanVen as e:
            print("trùng khoá → %s sqlstate=%s" % (type(e).__name__, e.sqlstate))
        try:
            kn.execute("SELECT * FROM _khong_co_bang_nay")
        except LoiVanHanh as e:
            print("bảng không có → %s sqlstate=%s" % (type(e).__name__, e.sqlstate))
        c = kn.execute("SELECT id FROM _t")
        print("lastrowid có trên con trỏ? %s" % hasattr(c, "lastrowid"))
    finally:
        kn.close()
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_tu_kiem())
