#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G12 — bộ thử PostgreSQL: schema của dự án có dựng được trên PostgreSQL không.

====== ĐÂY KHÔNG PHẢI MỘT LƯỢT CHUYỂN CSDL ======
Quyết định **D-8 (anh Thành, 15/10/2026)**: *tiếp tục SQLite local; THỬ PostgreSQL trước
khi quyết định triển khai SaaS nhiều người dùng.* Bộ thử này **thử**. Nó không đụng
`app/du-lieu/hub.db`, không đổi `app/csdl.py`, không chuyển dữ liệu. Kết quả nó sinh ra là
**bằng chứng để anh Thành quyết**, không phải một quyết định đã làm thay anh.

====== VÌ SAO MẶC ĐỊNH BỎ QUA ======
`app/thu/chay_tat_ca.sh` TỰ DÒ mọi `app/thu/thu_*.py`, nên file này sẽ bị gom vào lượt chạy
chung. Nhưng nó cần **dựng một cụm PostgreSQL riêng** (đo trên MacBook M5, 15/10/2026:
`initdb` + `pg_ctl start` + nghiệm thu mất ~1,5–3 giây mỗi lượt), và nó để lại một tiến
trình `postgres` sống trong lúc chạy. Bắt mọi lượt chạy bộ thử phải trả cái giá đó là sai.

Nên: **mặc định BỎ QUA**. Bật bằng biến môi trường:

    VIP_THU_POSTGRES=1 python3 app/thu/thu_postgres.py

Hai cách dùng cụm:
  * tự dựng cụm tạm (mặc định khi bật) — bộ thử tự `initdb`, tự `pg_ctl stop`, tự xoá;
  * dùng cụm có sẵn: đặt `VHPG_SOCKET` (+ `VHPG_CONG`, `VHPG_NGUOI`), bộ thử **không**
    dựng và **không** xoá cụm đó.

Mọi đường bỏ qua đều nói rõ **thiếu cái gì** — một bộ thử bỏ qua im lặng là một bộ thử
báo đạt mà không đo gì (§12.1).

====== CHỐT CHẶN AN TOÀN ======
Máy này có cụm PostgreSQL hệ thống ở **:5432** đang giữ CSDL của dự án khác
(`vip_customs`, `vip_customs_g16`, `vip_customs_test`). `_kiem_cong_an_toan` TỪ CHỐI chạy
nếu cổng là 5432, kể cả khi người chạy cố tình đặt như vậy.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # …/app
DU_AN = os.path.dirname(GOC)
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.join(DU_AN, "trien_khai", "postgres"))

CONG_CAM = "5432"
LENH_CAN = ("initdb", "pg_ctl", "psql")


# --------------------------------------------------------------------------- tiện ích
def _thieu_gi():
    """Trả chuỗi nói THIẾU CÁI GÌ, hoặc None nếu đủ điều kiện chạy."""
    if os.environ.get("VIP_THU_POSTGRES", "") != "1":
        return ("chưa bật — bộ thử này dựng một cụm PostgreSQL riêng (~1,5–3 giây) nên "
                "không chạy mặc định. Bật bằng: VIP_THU_POSTGRES=1")
    co_san = os.environ.get("VHPG_SOCKET", "")
    can = ("psql",) if co_san else LENH_CAN
    thieu = [l for l in can if not shutil.which(l)]
    if thieu:
        return ("thiếu lệnh %s trên PATH. Cài bằng: brew install postgresql@16"
                % ", ".join("`%s`" % x for x in thieu))
    return None


def _kiem_cong_an_toan(cong):
    if str(cong) == CONG_CAM:
        raise AssertionError(
            "TỪ CHỐI chạy trên cổng %s: đó là cụm PostgreSQL hệ thống của máy này, đang giữ "
            "CSDL của dự án khác (vip_customs…). Bộ thử phải dùng cụm riêng." % CONG_CAM)


class Cum(object):
    """Một cụm PostgreSQL thử. Tự dựng nếu chưa có, tự dọn nếu CHÍNH NÓ dựng."""

    def __init__(self):
        self.sock = os.environ.get("VHPG_SOCKET", "")
        self.cong = os.environ.get("VHPG_CONG", "55432")
        self.nguoi = os.environ.get("VHPG_NGUOI", "vhtest")
        self.tu_dung = not self.sock
        self.thu_muc = None
        _kiem_cong_an_toan(self.cong)

    def dung(self):
        if not self.tu_dung:
            return
        self.thu_muc = tempfile.mkdtemp(prefix="vhpg-thu-")
        moi = dict(os.environ, LANG="C", LC_ALL="C")
        p = subprocess.run(["initdb", "-D", os.path.join(self.thu_muc, "data"),
                            "--locale=C", "--encoding=UTF8", "-U", self.nguoi],
                           capture_output=True, text=True, env=moi)
        if p.returncode:
            raise unittest.SkipTest("initdb hỏng: " + (p.stderr or p.stdout)[-300:])
        # Socket PHẢI ở đường NGẮN: giới hạn sun_path của Unix socket là 103 byte, và thư
        # mục tạm của phiên có thể dài hơn thế. Đã dính một lần khi dựng.
        self.sock = tempfile.mkdtemp(prefix="vhpg.", dir="/tmp")
        # `LC_ALL=C` phải đặt cho CẢ `pg_ctl`, không chỉ `initdb`. Thiếu nó thì postmaster
        # chết ngay lúc khởi động với `FATAL: postmaster became multithreaded during
        # startup` — macOS nạp locale bằng một thư viện sinh thêm thread, và postmaster
        # từ chối chạy khi thấy mình đa luồng. Đã dính thật khi dựng bộ thử này: lượt chạy
        # tay trước đó `export LANG=C LC_ALL=C` nên che mất lỗi, lượt chạy trong Python
        # không kế thừa biến đó nên lộ ra.
        p = subprocess.run(["pg_ctl", "-D", os.path.join(self.thu_muc, "data"),
                            "-l", os.path.join(self.thu_muc, "pg.log"),
                            "-o", "-p %s -k %s -c listen_addresses=''" % (self.cong, self.sock),
                            "-w", "start"], capture_output=True, text=True, env=moi)
        if p.returncode:
            ghi = os.path.join(self.thu_muc, "pg.log")
            chi_tiet = open(ghi).read()[-400:] if os.path.exists(ghi) else ""
            raise unittest.SkipTest("pg_ctl start hỏng: %s | pg.log: %s"
                                    % ((p.stderr or p.stdout)[-200:], chi_tiet))

    def dong(self):
        """Dừng bằng `pg_ctl stop`. KHÔNG `kill`, KHÔNG `pkill` (CLAUDE.md §16.7)."""
        if not self.tu_dung:
            return
        if self.thu_muc:
            subprocess.run(["pg_ctl", "-D", os.path.join(self.thu_muc, "data"),
                            "stop", "-m", "fast"], capture_output=True, text=True)
            shutil.rmtree(self.thu_muc, ignore_errors=True)
        if self.sock:
            shutil.rmtree(self.sock, ignore_errors=True)

    def psql(self, sql, db="postgres", dung_lai_khi_loi=True):
        co = ["psql", "-h", self.sock, "-p", str(self.cong), "-U", self.nguoi, "-d", db, "-qtAX"]
        if dung_lai_khi_loi:
            co += ["-v", "ON_ERROR_STOP=1"]
        p = subprocess.run(co, input=sql, capture_output=True, text=True)
        return p.returncode, p.stdout.strip(), p.stderr.strip()


CUM = None
DDL_PG = None
CSDL_THU = "vh_g12_thu"


def setUpModule():
    global CUM, DDL_PG
    ly_do = _thieu_gi()
    if ly_do:
        raise unittest.SkipTest("BỎ QUA bộ thử PostgreSQL — " + ly_do)
    import sinh_ddl_pg
    DDL_PG = sinh_ddl_pg.sinh()[0]
    CUM = Cum()
    CUM.dung()
    rc, _, err = CUM.psql("SELECT 1")
    if rc:
        CUM.dong()
        raise unittest.SkipTest("cụm dựng xong nhưng không truy vấn được: " + err[-200:])
    CUM.psql("DROP DATABASE IF EXISTS %s" % CSDL_THU)
    rc, _, err = CUM.psql("CREATE DATABASE %s" % CSDL_THU)
    if rc:
        CUM.dong()
        raise unittest.SkipTest("không tạo được CSDL thử: " + err[-200:])


def tearDownModule():
    if CUM is not None:
        CUM.psql("DROP DATABASE IF EXISTS %s" % CSDL_THU)
        CUM.dong()


def q(sql, db=CSDL_THU, dung_lai_khi_loi=True):
    return CUM.psql(sql, db, dung_lai_khi_loi)


# --------------------------------------------------------------------------- A. schema
class A_SchemaDungDuoc(unittest.TestCase):
    """DDL của dự án, sau bốn phép dịch của `sinh_ddl_pg.py`, dựng được trên PostgreSQL."""

    def test_a1_nap_tron_goi_trong_mot_giao_dich(self):
        """Nạp cả schema trong MỘT giao dịch. Hỏng một câu là rollback sạch, không nửa vời."""
        rc, _, err = q("BEGIN;\n" + DDL_PG + "\nCOMMIT;")
        self.assertEqual(rc, 0, "DDL không nạp được:\n" + err[-1500:])

    def test_a2_chay_lai_vo_hai(self):
        """Mọi câu là `IF NOT EXISTS` / `CREATE OR REPLACE`, nên lượt hai phải vô hại.
        Thiếu tính chất này thì migration chạy lại lần nữa là hỏng."""
        rc, _, err = q(DDL_PG)
        self.assertEqual(rc, 0, "lượt nạp thứ hai hỏng:\n" + err[-800:])

    def test_a3_du_bang_so_voi_sqlite(self):
        """Đối chiếu TẬP TÊN BẢNG hai bên. Phạm vi: chỉ tên bảng — KHÔNG so kiểu cột."""
        import sqlite3
        import csdl
        import ai_job, goi_dich_vu, harness_hang, quan_sat, tai_chinh
        kn = sqlite3.connect(":memory:")
        for s in (csdl.SCHEMA, tai_chinh.DDL_G07, goi_dich_vu.DDL_G08,
                  harness_hang.DDL_G09, ai_job.DDL_G10, quan_sat.DDL_G11):
            kn.executescript(s)
        # `sqlite_sequence` do chính SQLite tạo ra vì có AUTOINCREMENT — nó là cơ chế của
        # SQLite, không phải bảng của dự án, nên loại khỏi phép so.
        sl = {r[0] for r in kn.execute("SELECT name FROM sqlite_master WHERE type='table'")
              } - {"sqlite_sequence"}
        rc, out, _ = q("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        self.assertEqual(rc, 0)
        pg = set(out.split())
        self.assertEqual(sl - pg, set(), "PostgreSQL THIẾU bảng: %s" % sorted(sl - pg))
        self.assertEqual(pg - sl, set(), "PostgreSQL THỪA bảng: %s" % sorted(pg - sl))
        self.assertGreaterEqual(len(pg), 40, "số bảng quá ít — phép đo đang nhìn sai chỗ")

    def test_a4_du_cot_tung_bang(self):
        """Đối chiếu TÊN CỘT từng bảng. Phạm vi: tên cột — KHÔNG so kiểu, KHÔNG so ràng buộc."""
        import sqlite3
        import csdl
        import ai_job, goi_dich_vu, harness_hang, quan_sat, tai_chinh
        kn = sqlite3.connect(":memory:")
        for s in (csdl.SCHEMA, tai_chinh.DDL_G07, goi_dich_vu.DDL_G08,
                  harness_hang.DDL_G09, ai_job.DDL_G10, quan_sat.DDL_G11):
            kn.executescript(s)
        rc, out, _ = q("SELECT table_name||'|'||column_name FROM information_schema.columns"
                       " WHERE table_schema='public'")
        self.assertEqual(rc, 0)
        pg = {}
        for d in out.split():
            if "|" in d:
                t, c = d.split("|", 1)
                pg.setdefault(t, set()).add(c)
        lech = []
        for (ten,) in kn.execute("SELECT name FROM sqlite_master WHERE type='table'"
                                 " AND name<>'sqlite_sequence'"):
            cs = {r[1] for r in kn.execute("PRAGMA table_info(%s)" % ten)}
            if cs != pg.get(ten, set()):
                lech.append((ten, sorted(cs - pg.get(ten, set())),
                             sorted(pg.get(ten, set()) - cs)))
        self.assertEqual(lech, [], "bảng lệch cột: %s" % lech)


# -------------------------------------------------------------- B. ràng buộc còn hiệu lực
class B_RangBuocConHieuLuc(unittest.TestCase):
    """DDL nạp được CHƯA PHẢI là xong. Ràng buộc phải CHẶN THẬT — §12.1: thứ dùng để kiểm
    chứng (ở đây là bản dịch DDL) phải được kiểm trước khi tin."""

    @classmethod
    def setUpClass(cls):
        q("BEGIN;\n" + DDL_PG + "\nCOMMIT;")
        q("INSERT INTO goi_dich_vu VALUES ('co_ban','Cơ bản',100000,100,10,3,2)"
          " ON CONFLICT (id) DO NOTHING")
        q("INSERT INTO tenants (id,code,ten,goi_id,tao_luc) VALUES (1,'t1','T1','co_ban','x')"
          " ON CONFLICT (id) DO NOTHING")

    def _chen_but_toan(self, **kv):
        m = {"tenant_id": 1, "loai": "'cod'", "so_tien_dong": 1000, "chieu": "'ghi_no'",
             "nguon": "'hang'", "can_cu": "'thu COD'", "tao_luc": "'x'"}
        m.update(kv)
        return q("INSERT INTO tc_but_toan (%s) VALUES (%s) RETURNING id"
                 % (",".join(m), ",".join(str(v) for v in m.values())))

    def test_b1_trigger_cam_sua_but_toan(self):
        """§17 đòi bút toán BẤT BIẾN. SQLite cưỡng chế bằng `RAISE(ABORT)`; bản dịch dùng
        `RAISE EXCEPTION` của PL/pgSQL. Phải chặn thật, không chỉ tồn tại."""
        rc, out, _ = self._chen_but_toan()
        self.assertEqual(rc, 0, "không chèn nổi bút toán nền")
        ma_bt = out.strip().splitlines()[-1]
        rc, _, err = q("UPDATE tc_but_toan SET so_tien_dong=1 WHERE id=%s" % ma_bt)
        self.assertNotEqual(rc, 0, "UPDATE bút toán ĐƯỢC CHO QUA — bất biến đã mất")
        self.assertIn("bat bien", err.lower())

    def test_b2_trigger_cam_xoa_but_toan(self):
        rc, out, _ = self._chen_but_toan(can_cu="'de xoa'")
        ma_bt = out.strip().splitlines()[-1]
        rc, _, err = q("DELETE FROM tc_but_toan WHERE id=%s" % ma_bt)
        self.assertNotEqual(rc, 0, "DELETE bút toán ĐƯỢC CHO QUA — bất biến đã mất")
        self.assertIn("bat bien", err.lower())

    def test_b3_check_so_tien_khong_am(self):
        rc, _, err = self._chen_but_toan(so_tien_dong=-1)
        self.assertNotEqual(rc, 0, "CHECK so_tien_dong >= 0 không chặn")
        self.assertIn("check", err.lower())

    def test_b4_check_can_cu_khong_rong(self):
        """`CHECK (length(can_cu) > 0)` — `length()` có ở cả hai kho, chạy nguyên văn."""
        rc, _, err = self._chen_but_toan(can_cu="''")
        self.assertNotEqual(rc, 0, "CHECK length(can_cu) > 0 không chặn")
        self.assertIn("check", err.lower())

    def test_b5_partial_unique_index(self):
        """AG-01 đợt trước cảnh báo partial unique index sẽ không chạy trên PostgreSQL.
        ĐO ĐƯỢC: nó chạy NGUYÊN VĂN. Ca này canh cả hai vế — NULL thì cho nhiều, có giá
        trị thì chỉ một."""
        rc, out, _ = self._chen_but_toan(can_cu="'goc dao'")
        goc = out.strip().splitlines()[-1]
        rc1, _, _ = self._chen_but_toan(can_cu="'dao 1'", dao_cua=goc)
        self.assertEqual(rc1, 0, "dòng đảo đầu tiên bị chặn oan")
        rc2, _, err = self._chen_but_toan(can_cu="'dao 2'", dao_cua=goc)
        self.assertNotEqual(rc2, 0, "hai dòng cùng `dao_cua` ĐƯỢC CHO QUA — partial unique hỏng")
        self.assertIn("ux_tc_bt_dao", err)
        # Nhiều dòng `dao_cua IS NULL` phải vẫn được (đó là lý do index có mệnh đề WHERE).
        self.assertEqual(self._chen_but_toan(can_cu="'a'")[0], 0)
        self.assertEqual(self._chen_but_toan(can_cu="'b'")[0], 0)

    def test_b6_on_conflict_do_update(self):
        """`migrate.py` nạp `carrier_providers` bằng `ON CONFLICT(ma) DO UPDATE … excluded.…`.
        Cú pháp đó là cú pháp của PostgreSQL, SQLite mượn về — chạy được cả hai bên."""
        q("INSERT INTO carrier_providers (ma,ten,capabilities_json,live_mo,cap_nhat_luc)"
          " VALUES ('vtp','VTP','{}',0,'x') ON CONFLICT(ma) DO UPDATE SET ten=excluded.ten")
        rc, out, _ = q("INSERT INTO carrier_providers (ma,ten,capabilities_json,live_mo,"
                       "cap_nhat_luc) VALUES ('vtp','VTP-moi','{}',0,'x')"
                       " ON CONFLICT(ma) DO UPDATE SET ten=excluded.ten RETURNING ten")
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip().splitlines()[-1], "VTP-moi")

    def test_b7_bytea_nhan_nhi_phan(self):
        """`wh_su_kien.payload_tho` khai `BLOB` — PostgreSQL không có kiểu đó, bản dịch
        đổi sang `BYTEA`. Kiểm là nó thật sự nhận và trả đúng số byte."""
        q("INSERT INTO carrier_accounts (id,tenant_id,hang,ten,credentials_ma_hoa,webhook_ma,"
          "webhook_secret_ma_hoa,tao_luc) VALUES (1,1,'vtp','a','x','w1','y','x')"
          " ON CONFLICT (id) DO NOTHING")
        rc, out, err = q("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                         "headers_json,nhan_luc) VALUES (1,'e-bytea','\\x7b7d'::bytea,'{}','x')"
                         " RETURNING length(payload_tho)")
        self.assertEqual(rc, 0, err[-300:])
        self.assertEqual(out.strip().splitlines()[-1], "2")

    def test_b8_khoa_ngoai_chan_that(self):
        """SQLite chỉ cưỡng chế khoá ngoại khi `PRAGMA foreign_keys=ON`; PostgreSQL luôn
        cưỡng chế. Ca này canh rằng bản dịch KHÔNG đánh rơi khoá ngoại."""
        rc, _, err = q("INSERT INTO khach_hang (tenant_id,ten,tao_luc)"
                       " VALUES (999999,'ma','x')")
        self.assertNotEqual(rc, 0, "tenant_id không tồn tại mà vẫn chèn được")
        self.assertIn("foreign key", err.lower())


# ------------------------------------------------------- C. khác biệt hành vi phải biết
class C_KhacBietHanhVi(unittest.TestCase):
    """Những chỗ hai kho CHẠY ĐƯỢC CẢ HAI nhưng HÀNH VI KHÁC. Đây là loại nguy hiểm nhất
    khi chuyển kho: không có thông báo lỗi nào, chỉ có kết quả khác đi."""

    @classmethod
    def setUpClass(cls):
        q("BEGIN;\n" + DDL_PG + "\nCOMMIT;")

    def test_c1_kieu_chat_khong_nhan_chuoi_vao_cot_so(self):
        """SQLite có *type affinity*: nhét chuỗi 'abc' vào cột INTEGER thì nó LƯU LUÔN.
        PostgreSQL từ chối. Mọi chỗ mã đang dựa vào tính lỏng đó sẽ lộ ra khi chuyển."""
        rc, _, err = q("INSERT INTO goi_dich_vu VALUES ('x','X','khong-phai-so',1,1,1,1)")
        self.assertNotEqual(rc, 0, "PostgreSQL nhận chuỗi vào cột INTEGER — sai giả định")
        self.assertIn("invalid input syntax", err.lower())

    def test_c2_trigger_pg_huy_ca_giao_dich(self):
        """Khác biệt THẬT, ghi ra để không ai vấp: `RAISE(ABORT)` của SQLite huỷ **câu
        lệnh**, còn `RAISE EXCEPTION` của PL/pgSQL huỷ **cả giao dịch**. Mã nào bắt lỗi
        rồi ghi tiếp trong cùng giao dịch sẽ gãy ở PostgreSQL.
        Vá đúng khi nào thật sự chuyển: dùng SAVEPOINT quanh lượt ghi có thể bị trigger chặn.
        """
        q("INSERT INTO goi_dich_vu VALUES ('c2','C2',1,1,1,1,1) ON CONFLICT (id) DO NOTHING")
        q("INSERT INTO tenants (id,code,ten,goi_id,tao_luc) VALUES (2,'t2','T2','c2','x')"
          " ON CONFLICT (id) DO NOTHING")
        q("INSERT INTO tc_but_toan (tenant_id,loai,so_tien_dong,chieu,nguon,can_cu,tao_luc)"
          " VALUES (2,'cod',1,'ghi_no','hang','c2','x')")
        # Trong MỘT giao dịch: một lượt UPDATE bị trigger chặn, rồi thử ghi tiếp.
        rc, _, err = q("BEGIN;\n"
                       "UPDATE tc_but_toan SET loai='x' WHERE tenant_id=2;\n"
                       "INSERT INTO tc_nhat_ky (tenant_id,luc,hanh_dong,doi_tuong,bam)"
                       " VALUES (2,'x','a','b:1','h');\n"
                       "COMMIT;", dung_lai_khi_loi=False)
        rc2, out, _ = q("SELECT count(*) FROM tc_nhat_ky WHERE tenant_id=2")
        self.assertEqual(out.strip().splitlines()[-1], "0",
                         "ghi SAU khi trigger chặn vẫn vào được — giả định về giao dịch sai")

    def test_c3_khong_co_pragma(self):
        """`PRAGMA` là của SQLite. Đo được 16 lượt dùng trong `app/*.py` (10 lượt là
        `PRAGMA table_info` — dò cột). PostgreSQL không có lệnh này; phải thay bằng
        `information_schema`. Ca này canh rằng PostgreSQL thật sự không nhận `PRAGMA`,
        để không ai tưởng nó im lặng bỏ qua."""
        rc, _, err = q("PRAGMA table_info(tenants)", dung_lai_khi_loi=True)
        self.assertNotEqual(rc, 0)
        rc, out, _ = q("SELECT count(*) FROM information_schema.columns"
                       " WHERE table_schema='public' AND table_name='tenants'")
        self.assertEqual(rc, 0)
        self.assertGreater(int(out.strip().splitlines()[-1]), 5)

    def test_c4_tham_so_dollar_khong_phai_dau_hoi(self):
        """846 dấu `?` trong 294 chuỗi SQL ở `app/*.py` (đo bằng AST, chỉ chuỗi có từ khoá
        SQL). PostgreSQL dùng `$1,$2`. Ca này canh rằng `?` KHÔNG phải cú pháp hợp lệ —
        tức là chỗ này buộc phải sửa, không trôi qua được."""
        rc, _, err = q("SELECT * FROM tenants WHERE id = ?")
        self.assertNotEqual(rc, 0, "PostgreSQL nhận `?` làm tham số — sai giả định")

    def test_c5_insert_or_ignore_khong_co(self):
        """13 lượt `INSERT OR IGNORE` + 2 lượt `INSERT OR REPLACE` trong `app/*.py`.
        Cả hai là cú pháp riêng của SQLite. Tương đương PostgreSQL:
        `ON CONFLICT DO NOTHING` và `ON CONFLICT … DO UPDATE SET …`."""
        rc, _, _ = q("INSERT OR IGNORE INTO goi_dich_vu VALUES ('z','Z',1,1,1,1,1)")
        self.assertNotEqual(rc, 0)
        rc, _, err = q("INSERT INTO goi_dich_vu VALUES ('z','Z',1,1,1,1,1)"
                       " ON CONFLICT (id) DO NOTHING")
        self.assertEqual(rc, 0, err[-200:])


# ----------------------------------------------------------- D. chốt chặn của chính bộ thử
class D_ChotChanCuaBoThu(unittest.TestCase):
    """Bộ thử cũng là một thứ dùng để kiểm chứng, nên nó cũng phải được kiểm (§12.1)."""

    def test_d1_tu_choi_cong_5432(self):
        """Nếu ai đó trỏ bộ thử vào cụm hệ thống thì nó phải TỪ CHỐI, không phải chạy."""
        with self.assertRaises(AssertionError):
            _kiem_cong_an_toan("5432")

    def test_d2_khong_chay_tren_cum_he_thong(self):
        self.assertNotEqual(str(CUM.cong), CONG_CAM)

    def test_d3_ddl_sinh_ra_khong_con_cu_phap_sqlite(self):
        """Bản dịch phải sạch bốn thứ. Phép đo: regex trên văn bản DDL đã sinh.
        NGOÀI phạm vi: khác biệt ngữ nghĩa (xem lớp C) — regex không thấy được loại đó."""
        self.assertIsNotNone(DDL_PG)
        for mau, ten in ((r"\bAUTOINCREMENT\b", "AUTOINCREMENT"),
                         (r"RAISE\s*\(\s*ABORT", "RAISE(ABORT)"),
                         (r"CREATE\s+TRIGGER\s+IF\s+NOT\s+EXISTS", "CREATE TRIGGER IF NOT EXISTS"),
                         (r"(?<![\w'])BLOB(?![\w'])", "BLOB")):
            self.assertIsNone(re.search(mau, DDL_PG, re.I),
                              "DDL sinh ra còn cú pháp SQLite: " + ten)

    def test_d4_ddl_sinh_ra_du_lon(self):
        """Chặn ca bản dịch rỗng/cụt mà vẫn 'nạp đạt' — một DDL rỗng nạp bao giờ cũng đạt."""
        self.assertGreater(DDL_PG.count("CREATE TABLE"), 40)
        self.assertGreaterEqual(DDL_PG.count("CREATE TRIGGER"), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
