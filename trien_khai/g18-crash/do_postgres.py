#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GIẾT GIỮA GIAO DỊCH TRÊN PostgreSQL — CỤM RIÊNG, KHÔNG PHẢI :5432.

====== BA CHỐT CHẶN CỨNG, KIỂM TRA TRƯỚC KHI DỰNG BẤT CỨ THỨ GÌ ======
1. Cổng **KHÔNG ĐƯỢC** là 5432. Máy này đang chạy một cụm PostgreSQL hệ thống ở :5432 giữ
   CSDL của **dự án khác** (`vip_customs`, `vip_customs_g16`, `vip_customs_test`). Mọi lệnh
   ở đây đi qua **socket Unix**; cụm thử đặt `listen_addresses=''` nên **không mở cổng TCP
   nào** — cổng chỉ là số định danh trong thư mục socket riêng.
2. Cụm thử dựng trong thư mục TẠM riêng, socket ở đường NGẮN (`/tmp/vhpg…`, giới hạn 103
   byte của `sun_path`), xoá sạch khi xong.
3. Dừng cụm bằng `pg_ctl stop`, **KHÔNG `kill`/`pkill`** (CLAUDE.md §16.7). Ngoại lệ duy
   nhất: `os.kill(SIGKILL)` vào **đúng PID backend của CHÍNH cụm thử** — đó là phép đo, không
   phải lệnh dọn.

====== VÌ SAO KHÔNG DÙNG `psycopg` ======
Máy này **không có** `psycopg2` lẫn `psycopg` (đo: `ModuleNotFoundError`). Bộ thử PostgreSQL
có sẵn của dự án (`app/thu/thu_postgres.py`) cũng nói PostgreSQL qua `psql`. Đi theo đúng
đường đã có thay vì cài thêm một thư viện vào máy anh Thành.

====== PHẠM VI — ĐỌC KỸ ======
Phép đo này chạy **NĂM CÂU GHI CÙNG HÌNH DẠNG** với `tai_chinh.chuyen_cod` (UPDATE tc_cod ·
INSERT tc_cod_chuyen · INSERT tc_but_toan · UPSERT tc_cong_no · INSERT tc_nhat_ky), trên DDL
do `sinh_ddl_pg.py` dịch **từ chính schema SQLite đang chạy**.

NÓ **KHÔNG** CHẠY `tai_chinh.py`: mô-đun đó chỉ nói SQLite (`import csdl` → `sqlite3`), và
quyết định **D-8** là *chưa chuyển CSDL nghiệp vụ sang PostgreSQL*. Nên đây là phép đo
**tầng CSDL**, không phải phép đo mã nghiệp vụ trên PostgreSQL. Câu "sản phẩm chạy đúng trên
PostgreSQL" **KHÔNG** được rút ra từ đây.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

GOC_CRASH = os.path.dirname(os.path.abspath(__file__))
GOC_DU_AN = os.path.dirname(os.path.dirname(GOC_CRASH))
GOC_APP = os.path.join(GOC_DU_AN, "app")
GOC_PG = os.path.join(GOC_DU_AN, "trien_khai", "postgres")
for p in (GOC_APP, GOC_CRASH, GOC_PG):
    if p not in sys.path:
        sys.path.insert(0, p)

CONG_CAM = "5432"
LENH_CAN = ("initdb", "pg_ctl", "psql")

# Năm câu ghi, đúng thứ tự của `tai_chinh.chuyen_cod` cho chuyển COD_EXPECTED → COD_COLLECTED.
# `{L}` là mốc thời gian, `{BAM}` là băm của dòng nhật ký — điền lúc dựng kịch bản.
GIA_TRI_HANG_BAO = 250000
CAC_CAU_GHI = [
    ("1. UPDATE tc_cod",
     "UPDATE tc_cod SET trang_thai='COD_COLLECTED', cap_nhat_luc='{L}', so_tien_hang_bao={T}"
     " WHERE don_id=1 AND tenant_id=1 AND trang_thai='COD_EXPECTED';"),
    ("2. INSERT tc_cod_chuyen",
     "INSERT INTO tc_cod_chuyen (tenant_id, don_id, tu, den, nguon, can_cu, nguoi, luc)"
     " VALUES (1,1,'COD_EXPECTED','COD_COLLECTED','hang','do G18 AG-06','1','{L}');"),
    ("3. INSERT tc_but_toan",
     "INSERT INTO tc_but_toan (tenant_id, loai, don_id, carrier_account_id, so_tien_dong,"
     " chieu, nguon, can_cu, tao_boi, tao_luc, batch_id, dao_cua)"
     " VALUES (1,'cod_hang_bao_thu',1,NULL,{T},'ghi_no','hang','do G18 AG-06',1,'{L}',NULL,NULL);"),
    ("4. UPSERT tc_cong_no",
     "INSERT INTO tc_cong_no (tenant_id, so, doi_tac, so_du_dong, cap_nhat_luc)"
     " VALUES (1,'phai_thu','noi_bo',{T},'{L}') ON CONFLICT (tenant_id, so, doi_tac)"
     " DO UPDATE SET so_du_dong = tc_cong_no.so_du_dong + excluded.so_du_dong,"
     " cap_nhat_luc = excluded.cap_nhat_luc;"),
    ("5. INSERT tc_nhat_ky",
     "INSERT INTO tc_nhat_ky (tenant_id, luc, hanh_dong, doi_tuong, chi_tiet, nguoi, bam_truoc,"
     " bam) VALUES (1,'{L}','chuyen_cod','don:1','COD_EXPECTED → COD_COLLECTED: do G18 AG-06',1,"
     "'',encode(sha256('g18-ag06|1|{L}'::bytea),'hex'));"),
]

# Điểm giết: chèn mốc + `pg_sleep` vào đúng chỗ trong kịch bản.
DIEM_GIET_PG = {
    "truoc_begin": "trước BEGIN — chưa mở giao dịch, chưa ghi gì",
    "sau_ghi_1": "trong giao dịch, NGAY SAU câu ghi thứ 1 (UPDATE tc_cod)",
    "sau_ghi_2": "trong giao dịch, NGAY SAU câu ghi thứ 2 (INSERT tc_cod_chuyen)",
    "sau_ghi_3": "trong giao dịch, NGAY SAU câu ghi thứ 3 (INSERT tc_but_toan)",
    "sau_ghi_4": "trong giao dịch, NGAY SAU câu ghi thứ 4 (UPSERT tc_cong_no)",
    "truoc_commit": "ngay TRƯỚC COMMIT — cả năm câu ghi đã chạy, chưa chốt",
    "sau_commit": "ngay SAU COMMIT — giao dịch đã chốt",
}
DIEM_KHONG_GIET = "khong"


def thieu_gi():
    """Trả chuỗi nói THIẾU GÌ, hoặc None. Bỏ qua phải NÓI RA, không được lặng (§7.1 BAN_GIAO)."""
    if os.environ.get("VIP_THU_POSTGRES", "") == "0":
        return "tắt bằng tay. Bật bằng: VIP_THU_POSTGRES=1"
    thieu = [l for l in LENH_CAN if not shutil.which(l)]
    if thieu:
        return ("thiếu lệnh %s trên PATH. Cài bằng: brew install postgresql@16"
                % ", ".join("`%s`" % x for x in thieu))
    return None


class Cum(object):
    """Cụm PostgreSQL THỬ: cổng riêng, socket riêng, thư mục riêng, xoá sạch khi xong."""

    def __init__(self, cong=None, nguoi="vhtest"):
        self.cong = str(cong or os.environ.get("VHG18_CONG_PG", "55718"))
        self.nguoi = nguoi
        if self.cong == CONG_CAM:
            raise AssertionError("TỪ CHỐI: cổng %s là cụm hệ thống giữ CSDL dự án khác"
                                 % CONG_CAM)
        self.goc = None
        self.sock = None
        self.data = None
        self.pid_postmaster = None

    # ---------------------------------------------------------------- vòng đời
    def dung(self):
        self.goc = tempfile.mkdtemp(prefix="vhg18-pg-")
        self.data = os.path.join(self.goc, "data")
        # Socket PHẢI ở đường NGẮN: `sun_path` giới hạn 103 byte và thư mục tạm của phiên
        # có thể dài hơn. Đây là chỗ đã vấp một lần ở G12 — chép lại để không vấp lại.
        self.sock = tempfile.mkdtemp(prefix="vhpg.", dir="/tmp")
        moi = dict(os.environ, LANG="C", LC_ALL="C")
        p = subprocess.run(["initdb", "-D", self.data, "--locale=C", "--encoding=UTF8",
                            "-U", self.nguoi], capture_output=True, text=True, env=moi)
        if p.returncode:
            raise RuntimeError("initdb hỏng: " + (p.stderr or p.stdout)[-400:])
        self._khoi_dong()
        return self

    def _khoi_dong(self):
        moi = dict(os.environ, LANG="C", LC_ALL="C")
        # `listen_addresses=''` — cụm thử KHÔNG mở cổng TCP nào. Chỉ socket Unix.
        p = subprocess.run(["pg_ctl", "-D", self.data, "-l", os.path.join(self.goc, "pg.log"),
                            "-o", "-p %s -k %s -c listen_addresses=''" % (self.cong, self.sock),
                            "-w", "start"], capture_output=True, text=True, env=moi)
        if p.returncode:
            ghi = os.path.join(self.goc, "pg.log")
            ct = open(ghi).read()[-500:] if os.path.exists(ghi) else ""
            raise RuntimeError("pg_ctl start hỏng: %s | %s"
                               % ((p.stderr or p.stdout)[-200:], ct))
        self.pid_postmaster = self._doc_pid()

    def _doc_pid(self):
        ghi = os.path.join(self.data, "postmaster.pid")
        try:
            with open(ghi) as f:
                return int(f.readline().strip())
        except (OSError, ValueError):
            return None

    def cho_san_sang(self, giay=30):
        """Chờ cụm TRUY VẤN ĐƯỢC THẬT (không tin `pg_ctl` báo 'server started')."""
        het = time.time() + giay
        while time.time() < het:
            rc, out, _ = self.psql("SELECT 1", db="postgres")
            if rc == 0 and out.strip() == "1":
                self.pid_postmaster = self._doc_pid()
                return True
            time.sleep(0.2)
        return False

    def dong(self):
        """Dừng bằng `pg_ctl stop -m fast`. KHÔNG `kill`, KHÔNG `pkill`."""
        if self.data and os.path.isdir(self.data):
            moi = dict(os.environ, LANG="C", LC_ALL="C")
            subprocess.run(["pg_ctl", "-D", self.data, "stop", "-m", "fast"],
                           capture_output=True, text=True, env=moi)
        for d in (self.goc, self.sock):
            if d:
                shutil.rmtree(d, ignore_errors=True)
        self.goc = self.sock = self.data = None

    # ---------------------------------------------------------------- psql
    def psql(self, sql, db="postgres", dung_lai_khi_loi=True, tep=None):
        co = ["psql", "-h", self.sock, "-p", self.cong, "-U", self.nguoi, "-d", db, "-qtAX"]
        if dung_lai_khi_loi:
            co += ["-v", "ON_ERROR_STOP=1"]
        if tep:
            co += ["-f", tep]
            p = subprocess.run(co, capture_output=True, text=True)
        else:
            p = subprocess.run(co, input=sql, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()

    def psql_chay(self, tep, db):
        """Chạy MỘT tệp kịch bản, KHÔNG chờ — trả `Popen` để bên gọi giết được theo PID."""
        co = ["psql", "-h", self.sock, "-p", self.cong, "-U", self.nguoi, "-d", db, "-qtAX",
              "-v", "ON_ERROR_STOP=1", "-f", tep]
        return subprocess.Popen(co, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def tao_csdl(self, ten, ddl):
        self.psql("DROP DATABASE IF EXISTS %s" % ten)
        rc, _, err = self.psql("CREATE DATABASE %s" % ten)
        if rc:
            raise RuntimeError("không tạo được CSDL %s: %s" % (ten, err))
        rc, _, err = self.psql(ddl, db=ten)
        if rc:
            raise RuntimeError("DDL hỏng trên %s: %s" % (ten, err[-800:]))

    def xoa_csdl(self, ten):
        self.psql("DROP DATABASE IF EXISTS %s" % ten)

    def dau_van_khoi_phuc(self):
        """Dấu vết KHÔI PHỤC trong `pg.log` — bằng chứng cụm đã chết thật rồi sống lại.

        Không có dòng này thì "giết backend" chỉ là một lời khai: cụm có thể chưa hề ngã, và
        khi đó phép đo nói về một lượt chưa bao giờ xảy ra. Đây là dấu vết do CHÍNH PostgreSQL
        ghi, không do bộ thử viết.
        """
        ghi = os.path.join(self.goc or "", "pg.log")
        if not os.path.exists(ghi):
            return []
        ra = []
        with open(ghi, "r", encoding="utf-8", errors="replace") as f:
            for dong in f:
                if ("was not properly shut down" in dong or "automatic recovery in progress" in dong
                        or "database system is ready to accept connections" in dong
                        or "terminating any other active server processes" in dong
                        or "all server processes terminated" in dong):
                    ra.append(dong.strip()[:160])
        return ra


# ============================================================================
# DỰNG KỊCH BẢN
# ============================================================================
def _dong_moc(thu_muc, nhan):
    """Dòng psql `\\!` ghi một mốc ra tệp — để bên ngoài biết ĐÃ tới đâu rồi mới giết.

    Không có mốc thì bên giết phải đoán bằng `sleep`, và một `sleep` đoán sai sẽ giết vào
    chỗ khác — phép đo vẫn chạy, vẫn ra số, và số ấy nói về một điểm khác.
    """
    return "\\! printf '%%s\\n' '%s' >> %s" % (nhan, os.path.join(thu_muc, "moc"))


def dung_kich_ban(diem, thu_muc, co_moc=True):
    """Trả CHUỖI kịch bản psql. `\\!` + `pg_sleep` được chèn đúng điểm giết.

    `pg_sleep(20)` là CỬA SỔ, không phải thời gian chờ: bên giết thấy mốc là giết ngay
    (đo được: dưới 0,1 giây). Cửa sổ rộng để một lượt chậm cũng không tự đi tiếp rồi COMMIT
    trước khi bị giết — lúc đó phép đo sẽ báo "sau COMMIT" cho một điểm đáng lẽ là "trước
    COMMIT", và báo SAI một cách im lặng.

    HAI DÒNG ĐẦU ghi `pg_backend_pid()` của CHÍNH PHIÊN NÀY ra tệp. Không có nó thì kiểu
    giết `backend` chỉ còn cách đoán PID — và giết nhầm backend là giết nhầm phiên của người
    khác. Gọi `pg_backend_pid()` ở một phiên `psql` KHÁC thì trả về PID của phiên khác: đó là
    chỗ dễ sai nhất ở đây, nên nó phải nằm TRONG kịch bản.
    """
    L = "2026-10-15 12:00:00+07"
    T = str(GIA_TRI_HANG_BAO)
    dong = ["\\o %s" % os.path.join(thu_muc, "backend.pid"),
            "SELECT pg_backend_pid();",
            "\\o"]
    if co_moc and diem == "truoc_begin":
        dong += [_dong_moc(thu_muc, "diem"), "SELECT pg_sleep(20);"]
    dong.append("BEGIN;")
    for i, (nhan, cau) in enumerate(CAC_CAU_GHI, 1):
        dong.append("-- " + nhan)
        dong.append(cau.format(L=L, T=T))
        if co_moc and diem == "sau_ghi_%d" % i:
            dong += [_dong_moc(thu_muc, "diem"), "SELECT pg_sleep(20);"]
    if co_moc and diem == "truoc_commit":
        dong += [_dong_moc(thu_muc, "diem"), "SELECT pg_sleep(20);"]
    dong.append("COMMIT;")
    if co_moc and diem == "sau_commit":
        dong += [_dong_moc(thu_muc, "diem"), "SELECT pg_sleep(20);"]
    return "\n".join(dong) + "\n"


def kich_ban_gieo_nen():
    """Dữ liệu nền — CHỐT XONG trước khi giao dịch cần đo bắt đầu.

    Gói dịch vụ phải có trước: bên SQLite nó được `csdl._khoi_tao_schema` gieo sẵn, bên
    PostgreSQL thì không ai gieo — và `tenants.goi_id` có KHOÁ NGOẠI THẬT, nên thiếu nó là
    hỏng ngay tại dòng đầu. Chính việc nó hỏng là bằng chứng khoá ngoại của bản dịch DDL
    đang CƯỠNG CHẾ, không chỉ tồn tại trên giấy.
    """
    bgio = "2026-10-15 12:00:00+07"
    return """
INSERT INTO goi_dich_vu (id, ten, gia_thang, han_muc_don_thang, han_muc_ai_thang,
  so_nhan_vien, so_tai_khoan_hang) VALUES ('free','Mien phi',0,50,20,2,1)
  ON CONFLICT (id) DO NOTHING;
INSERT INTO tenants (id, code, ten, goi_id, tao_luc) VALUES (1,'t1','T1','free','%s');
INSERT INTO users (id, ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)
  VALUES (1,'u1','x','Nguoi dung 1','%s');
INSERT INTO don_hang (id, tenant_id, ma_don, nguoi_gui_ten, nguoi_gui_sdt, nguoi_gui_dia_chi,
  nguoi_nhan_ten, nguoi_nhan_sdt, nguoi_nhan_dia_chi, hang_hoa, khoi_luong_gram, cod,
  nguoi_tao, tao_luc, cap_nhat_luc)
  VALUES (1,1,'D1','Nguoi gui','0900','dia chi gui','Nguoi nhan','0901','dia chi nhan',
          'hang mau',500,%d,1,'%s','%s');
INSERT INTO tc_cod (don_id, tenant_id, carrier_account_id, so_tien_du_kien, trang_thai,
  tao_luc, cap_nhat_luc) VALUES (1,1,NULL,%d,'COD_EXPECTED','%s','%s');
""" % (bgio, bgio, GIA_TRI_HANG_BAO, bgio, bgio, GIA_TRI_HANG_BAO, bgio, bgio)


# ============================================================================
# ĐO
# ============================================================================
def _q1(cum, db, sql):
    rc, out, err = cum.psql(sql, db=db)
    if rc:
        return "LOI:%s" % err[:120]
    return out.strip()


VET_SQL = """
SELECT
 (SELECT trang_thai FROM tc_cod WHERE don_id=1 AND tenant_id=1),
 (SELECT COALESCE(so_tien_hang_bao,-1) FROM tc_cod WHERE don_id=1 AND tenant_id=1),
 (SELECT COUNT(*) FROM tc_cod_chuyen WHERE don_id=1 AND tenant_id=1),
 (SELECT COUNT(*) FROM tc_but_toan WHERE don_id=1 AND tenant_id=1),
 (SELECT COALESCE(SUM(so_tien_dong),0) FROM tc_but_toan WHERE don_id=1 AND tenant_id=1),
 (SELECT COALESCE(SUM(so_du_dong),0) FROM tc_cong_no WHERE tenant_id=1 AND so='phai_thu'),
 (SELECT COUNT(*) FROM tc_nhat_ky WHERE tenant_id=1),
 (SELECT COUNT(*) FROM don_hang WHERE tenant_id=1);
"""

MO_COI_SQL = """
SELECT
 (SELECT COUNT(*) FROM tc_but_toan c LEFT JOIN don_hang d ON d.id=c.don_id
   WHERE c.don_id IS NOT NULL AND d.id IS NULL),
 (SELECT COUNT(*) FROM tc_cod c LEFT JOIN don_hang d ON d.id=c.don_id WHERE d.id IS NULL),
 (SELECT COUNT(*) FROM tc_cod_chuyen c LEFT JOIN don_hang d ON d.id=c.don_id WHERE d.id IS NULL),
 (SELECT COUNT(*) FROM tc_but_toan b JOIN don_hang d ON d.id=b.don_id
   WHERE b.tenant_id<>d.tenant_id);
"""

KHOA_NGOAI_SQL = """
SELECT COUNT(*) FROM (
  SELECT conrelid::regclass::text AS bang FROM pg_constraint
   WHERE contype='f' AND connamespace='public'::regnamespace
) x;
"""


def vet_trang_thai(cum, db):
    """VẾT 8 TRƯỜNG — CÙNG hình dạng với vết bên SQLite, để hai bên so được với nhau."""
    tho = _q1(cum, db, VET_SQL)
    if tho.startswith("LOI:"):
        return {"loi": tho}
    phan = [x.strip() for x in tho.replace("\n", "|").split("|") if x.strip() != ""]
    if len(phan) != 8:
        return {"loi": "vết trả về %d trường, mong đợi 8: %r" % (len(phan), tho)}
    return {
        "cod_trang_thai": phan[0],
        "cod_hang_bao": int(phan[1]),
        "so_chuyen": int(phan[2]),
        "so_but_toan": int(phan[3]),
        "tong_but_toan": int(phan[4]),
        "cong_no_phai_thu": int(phan[5]),
        "so_nhat_ky": int(phan[6]),
        "so_don": int(phan[7]),
    }


def do_toan_bo(cum, db):
    ra = {"csdl": db}
    ra["vet"] = vet_trang_thai(cum, db)
    for ten, sql, n in (("mo_coi", MO_COI_SQL, 4),):
        tho = _q1(cum, db, sql)
        if tho.startswith("LOI:"):
            ra[ten] = tho
            continue
        phan = [int(x) for x in tho.replace("\n", "|").split("|") if x.strip() != ""]
        ra[ten] = dict(zip(("but_toan_mo_coi", "cod_mo_coi", "cod_chuyen_mo_coi",
                            "but_toan_lech_chu_the"), phan)) if len(phan) == n else phan
    ra["so_khoa_ngoai"] = _q1(cum, db, KHOA_NGOAI_SQL)
    ra["nghe_tcp"] = _nghe_tcp(cum.cong)
    return ra


def _nghe_tcp(cong):
    """Cụm thử có mở TCP không — hỏi HỆ ĐIỀU HÀNH, không hỏi cấu hình."""
    try:
        p = subprocess.run(["lsof", "-nP", "-iTCP:%s" % cong, "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=10)
        return bool(p.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return None


# ============================================================================
# MỘT LƯỢT GIẾT
# ============================================================================
def mot_luot(cum, diem, kieu_giet, thu_muc):
    """Dựng CSDL mới → gieo nền → chạy kịch bản → GIẾT → đo → dọn.

    `kieu_giet`:
      `client`  — SIGKILL tiến trình `psql`. Tương ứng đúng nhất với "tiến trình ỨNG DỤNG
                  bị tắt giữa giao dịch" (bên SQLite cũng giết tiến trình ứng dụng).
      `backend` — SIGKILL tiến trình MÁY CHỦ đang phục vụ kết nối ấy. Đây là "CSDL chết giữa
                  giao dịch": postmaster phát hiện backend chết, dừng các backend khác và
                  chạy KHÔI PHỤC WAL. Cơ chế KHÁC HẲN `client`, nên đo riêng.
    """
    ten_db = "vh_g18_%s_%s" % (diem, kieu_giet)
    os.makedirs(thu_muc, exist_ok=True)
    moc = os.path.join(thu_muc, "moc")
    tep_pid = os.path.join(thu_muc, "backend.pid")
    for p in (moc, tep_pid):
        if os.path.exists(p):
            os.remove(p)
    import sinh_ddl_pg
    ddl = sinh_ddl_pg.sinh()[0]
    cum.tao_csdl(ten_db, ddl)
    rc, _, err = cum.psql(kich_ban_gieo_nen(), db=ten_db)
    if rc:
        cum.xoa_csdl(ten_db)
        raise RuntimeError("gieo nền hỏng: " + err[-400:])
    truoc = vet_trang_thai(cum, ten_db)

    tep = os.path.join(thu_muc, "kich_ban.sql")
    with open(tep, "w", encoding="utf-8") as f:
        f.write(dung_kich_ban(diem, thu_muc))
    if diem == DIEM_KHONG_GIET:
        # ĐỐI CHỨNG DƯƠNG: cùng kịch bản, KHÔNG giết.
        with open(tep, encoding="utf-8") as f:
            kich_ban = f.read()
        rc, out, err = cum.psql(kich_ban, db=ten_db)
        if rc:
            cum.xoa_csdl(ten_db)
            raise RuntimeError("kịch bản không giết hỏng: " + err[-400:])
        do = do_toan_bo(cum, ten_db)
        cum.xoa_csdl(ten_db)
        return {"diem": diem, "kieu_giet": "khong", "ma_thoat_psql": rc, "truoc": truoc,
                "bi_giet": False, "do": do}

    sv = cum.psql_chay(tep, ten_db)

    # Chờ MỐC, không chờ đồng hồ.
    het = time.time() + 40
    while time.time() < het and not os.path.exists(moc):
        if sv.poll() is not None:
            break
        time.sleep(0.02)
    if not os.path.exists(moc):
        sv.kill()
        cum.xoa_csdl(ten_db)
        raise RuntimeError("không thấy mốc điểm giết %s trong 40 giây (psql thoát: %s)"
                           % (diem, sv.poll()))

    backend_pid = None
    if os.path.exists(tep_pid):
        try:
            with open(tep_pid, encoding="utf-8") as f:
                backend_pid = int(f.read().strip().splitlines()[-1])
        except (ValueError, IndexError, OSError):
            backend_pid = None

    # Mốc đã có nghĩa là các câu TRƯỚC mốc đã chạy xong. Giết ngay, không chờ thêm.
    if kieu_giet == "client":
        os.kill(sv.pid, signal.SIGKILL)
    else:
        if backend_pid is None:
            sv.kill()
            cum.xoa_csdl(ten_db)
            raise RuntimeError("không đọc được pg_backend_pid() — không giết mù được")
        os.kill(backend_pid, signal.SIGKILL)
    try:
        sv.wait(timeout=20)
    except subprocess.TimeoutExpired:
        sv.kill()
    ma_thoat = sv.returncode
    # Đóng hai ống của tiến trình con. Không đóng thì chúng chỉ được thu hồi lúc GC, và mỗi
    # lượt để lại một ResourceWarning — tiếng ồn che mất cảnh báo thật ở lượt sau.
    for ong in (sv.stdout, sv.stderr):
        if ong is not None:
            ong.close()

    if kieu_giet == "backend":
        # Backend chết ⇒ postmaster dừng cả cụm rồi KHÔI PHỤC. Phải chờ nó sống lại mới đo
        # được — đo ngay lúc này chỉ đo được "cụm đang tắt".
        if not cum.cho_san_sang(90):
            raise RuntimeError("cụm không sống lại sau khi giết backend %s" % backend_pid)
        khoi_phuc = True
    else:
        # Giết CLIENT thì máy chủ vẫn sống, nhưng nó CHƯA BIẾT client đã chết: backend đang
        # nằm trong `pg_sleep` của chính kịch bản đo, và `pg_sleep` không đọc socket. Trong
        # chạy thật, backend rảnh nên nó thấy EOF ngay; ở đây cái `pg_sleep` ấy là DỤNG CỤ
        # CHÈN, không phải hành vi của sản phẩm — nên phải nói ra và phải xử riêng.
        #
        # `pg_terminate_backend` chỉ làm NHANH việc máy chủ sẽ tự làm (huỷ phiên của một
        # client đã chết). Nó KHÔNG chốt giao dịch, KHÔNG ghi gì thêm — nên nó không thể
        # biến một giao dịch nửa vời thành nguyên vẹn. Đo được: bỏ bước này thì backend nằm
        # lại hết 20 giây ngủ rồi mới tự huỷ, và lượt đo chậm thêm 20 giây vô ích.
        if backend_pid is not None:
            cum.psql("SELECT pg_terminate_backend(%d)" % int(backend_pid), db="postgres",
                     dung_lai_khi_loi=False)
        khoi_phuc = _cho_backend_bien_mat(cum, backend_pid, 20) if backend_pid else None

    do = do_toan_bo(cum, ten_db)
    cum.xoa_csdl(ten_db)
    return {"diem": diem, "kieu_giet": kieu_giet, "ma_thoat_psql": ma_thoat,
            "backend_pid": backend_pid, "psql_pid": sv.pid, "bi_giet": True,
            "cum_khoi_phuc_lai": khoi_phuc, "truoc": truoc, "do": do,
            "nhat_ky_khoi_phuc": cum.dau_van_khoi_phuc()}


def _cho_backend_bien_mat(cum, backend_pid, giay):
    """Chờ backend biến mất khỏi `pg_stat_activity`. Trả True/False — KHÔNG trả 'chắc là rồi'."""
    het = time.time() + giay
    while time.time() < het:
        rc, out, _ = cum.psql("SELECT COUNT(*) FROM pg_stat_activity WHERE pid=%d"
                              % int(backend_pid), db="postgres")
        if rc == 0 and out.strip() == "0":
            return True
        time.sleep(0.05)
    return False


if __name__ == "__main__":
    print(__doc__)
    print("thiếu gì:", thieu_gi())
