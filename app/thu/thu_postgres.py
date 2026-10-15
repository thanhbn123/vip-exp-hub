#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G12 — bộ thử PostgreSQL: schema của dự án có dựng được trên PostgreSQL không.

====== ĐÂY KHÔNG PHẢI MỘT LƯỢT CHUYỂN CSDL ======
Quyết định **D-8 (anh Thành, 15/10/2026)**: *tiếp tục SQLite local; THỬ PostgreSQL trước
khi quyết định triển khai SaaS nhiều người dùng.* Bộ thử này **thử**. Nó không đụng
`app/du-lieu/hub.db`, không đổi `app/csdl.py`, không chuyển dữ liệu. Kết quả nó sinh ra là
**bằng chứng để anh Thành quyết**, không phải một quyết định đã làm thay anh.

====== CÁCH CHẠY: MẶC ĐỊNH **BẬT**, TẮT BẰNG `VIP_THU_POSTGRES=0` ======
`app/thu/chay_tat_ca.sh` TỰ DÒ mọi `app/thu/thu_*.py`, nên tệp này bị gom vào lượt chạy chung,
và nó cần **dựng một cụm PostgreSQL riêng** (`initdb` + `pg_ctl start`).

**Trước 15/10/2026 tệp này MẶC ĐỊNH BỎ QUA** (phải đặt `VIP_THU_POSTGRES=1`) với lý do ghi là
*"~1,5–3 giây mỗi lượt"*. Hậu quả ĐO ĐƯỢC: nó hiện dấu ✓ trong **mọi** báo cáo hồi quy mà chạy
**ĐÚNG 0 CA**, nên ai đọc *"27 bộ đạt"* cũng tưởng PostgreSQL đã được phủ — suốt thời gian đó
**chưa phủ gì**. Đo lại: cả bộ chạy hết trong **~2 giây**. Cái giá đó không đáng để giấu 25 phép kiểm.

**Nay: MẶC ĐỊNH BẬT.** Chạy:

    python3 app/thu/thu_postgres.py          # chạy thật, dựng cụm riêng, tự dọn
    VIP_THU_POSTGRES=0 python3 app/thu/thu_postgres.py   # TẮT (chỉ khi cần nhanh)

Đường TẮT **không im lặng**: `_thieu_gi()` trả lý do `"tắt bằng tay (VIP_THU_POSTGRES=0)"` và bộ
chạy chung in nó ra. Ba đường bỏ qua khác cũng vậy — thiếu lệnh `initdb`/`pg_ctl`/`psql`, cụm
dựng hỏng, cụm không truy vấn được. Một bộ thử bỏ qua im lặng là một bộ thử báo đạt mà không đo gì.
Riêng `VIP_THU_POSTGRES=0` là đường bỏ qua **do người chạy cố ý chọn** — cố ý thì được, miễn là nói ra.

Hai cách dùng cụm:
  * tự dựng cụm tạm (mặc định) — bộ thử tự `initdb`, tự `pg_ctl stop`, tự xoá;
  * dùng cụm có sẵn: đặt `VHPG_SOCKET` (+ `VHPG_CONG`, `VHPG_NGUOI`), bộ thử **không**
    dựng và **không** xoá cụm đó.

**25 ca, 5 lớp** — A schema dựng được · B ràng buộc còn hiệu lực · C khác biệt hành vi ·
D chốt chặn của chính bộ thử · **E bốn kết cục (G15/I02)**.

====== CHỐT CHẶN AN TOÀN ======
Máy này có cụm PostgreSQL hệ thống ở **:5432** đang giữ CSDL của dự án khác
(`vip_customs`, `vip_customs_g16`, `vip_customs_test`). `_kiem_cong_an_toan` TỪ CHỐI chạy
nếu cổng là 5432, kể cả khi người chạy cố tình đặt như vậy.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # …/app
DU_AN = os.path.dirname(GOC)
sys.path.insert(0, GOC)
sys.path.insert(0, os.path.join(DU_AN, "trien_khai", "postgres"))
import van_tay_cum                                                        # noqa: E402

CONG_CAM = "5432"
LENH_CAN = ("initdb", "pg_ctl", "psql")


# --------------------------------------------------------------------------- tiện ích
def _thieu_gi():
    """Trả chuỗi nói THIẾU CÁI GÌ, hoặc None nếu đủ điều kiện chạy."""
    # Trước 15/10/2026 bộ này TẮT mặc định (phải đặt VIP_THU_POSTGRES=1), lý do ghi là
    # "~1,5–3 giây". Hậu quả đo được: nó hiện dấu ✓ trong mọi lượt hồi quy mà chạy ĐÚNG 0 CA,
    # nên người đọc "27 bộ đạt" tưởng PostgreSQL đã được phủ — suốt thời gian đó chưa phủ gì.
    # Đo lại ngày 15/10/2026 trên Mac mini: cả 21 ca chạy hết trong 1,405 giây. Cái giá đó
    # không đáng để giấu 25 phép kiểm. Nay BẬT mặc định; ai cần nhanh thì VIP_THU_POSTGRES=0.
    if os.environ.get("VIP_THU_POSTGRES", "") == "0":
        # Chuỗi này phải mang dạng `Bật bằng: <BIẾN>=<số>`: bộ chạy chung (`chay_tat_ca.sh`)
        # TRÍCH dòng đó ra để in phán quyết BỎ QUA kèm cách bật lại. Không có nó thì người đọc
        # thấy "BỎ QUA — không nêu cách bật" và phải tự đi tìm. Docstring nói đường tắt "không
        # im lặng" — dòng này là chỗ giữ cho câu đó đúng.
        return "tắt bằng tay. Bật bằng: VIP_THU_POSTGRES=1"
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
# Vân tay cụm hệ thống :5432 — chụp TRƯỚC khi dựng bất cứ thứ gì, và SAU khi dọn xong.
# Yêu cầu G17/AG-05: mọi báo cáo phải chứng minh được lượt đo KHÔNG đụng cụm đang giữ
# CSDL của dự án khác. Xem `trien_khai/postgres/van_tay_cum.py`.
VT_TRUOC = None
VT_SAU = None


def setUpModule():
    global CUM, DDL_PG, VT_TRUOC
    ly_do = _thieu_gi()
    if ly_do:
        raise unittest.SkipTest("BỎ QUA bộ thử PostgreSQL — " + ly_do)
    # Chụp vân tay TRƯỚC khi `initdb` — để lượt chụp không thể bị chính cụm thử làm nhiễu.
    VT_TRUOC = van_tay_cum.chup(CONG_CAM)
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
    global VT_SAU
    if CUM is not None:
        CUM.psql("DROP DATABASE IF EXISTS %s" % CSDL_THU)
        CUM.dong()
    if VT_TRUOC is None:
        return
    VT_SAU = van_tay_cum.chup(CONG_CAM)
    van_tay_cum.in_van_tay(VT_SAU, "VÂN TAY CỤM :%s — SAU KHI CHẠY HẾT BỘ THỬ" % CONG_CAM)
    giong, lech = van_tay_cum.so_sanh(VT_TRUOC, VT_SAU)
    print("        TRƯỚC = SAU: %s%s"
          % ("ĐÚNG" if giong else "SAI — %s" % lech, ""))


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


# ------------------------------------------- E. BỐN KẾT CỤC, TÁCH RIÊNG (I02, G15)
class E_BonKetCuc(unittest.TestCase):
    """BỐN kết cục của một lượt ghi, đo trên CẢ HAI kho, KHÔNG gộp:

        CHOT_THANH_CONG · KHOA_HET_GIO · GIAO_DICH_HONG · MAT_CAP_NHAT

    Ba kết cục đầu TỰ BÁO (mã lỗi). Kết cục thứ tư **IM LẶNG** — nó chỉ hiện ra khi đối
    chiếu cuối lượt (số giao dịch *tin* đã chốt so với số *thật* trong CSDL). Nên mọi ca ở
    đây đều làm phép đối chiếu đó, không chỉ đếm lỗi.

    VÌ SAO e2/e3 LÀ QUAN TRỌNG NHẤT
    --------------------------------
    Cùng MỘT khuôn đọc-rồi-ghi ngây thơ (đọc ở kết nối riêng, ghi lại giá trị đã đọc), chạy
    nhiều TIẾN TRÌNH thật:

      · SQLite 3.51.0    → **TỪ CHỐI ỒN ÀO** (`database is locked`), MẤT CẬP NHẬT = 0
      · PostgreSQL 16.15 → **IM LẶNG MẤT**, 0 lượt nào báo lỗi

    Nghĩa là chuyển kho mà giữ nguyên khuôn đọc-rồi-ghi là **ĐỔI một lỗi ồn ào lấy một lỗi
    im lặng** — tệ hơn cho tiền. PostgreSQL KHÔNG tự sửa kết cục thứ tư; chỉ cộng ở TẦNG CÂU
    (`x = x + 1`) hoặc `SELECT … FOR UPDATE` mới sửa. Đó là lý do kỹ thuật để chặng 1 (lớp
    phương ngữ) phải đi CÙNG chặng "soát từng chỗ đọc-rồi-ghi".

    PHẠM VI: 2 tiến trình × 25 phép, socket Unix nội máy, dữ liệu nhỏ. NGOÀI phạm vi: nhiều
    máy · mạng thật · dữ liệu lớn · tải đọc. Số ở đây là bằng chứng ĐỊNH TÍNH có định lượng,
    KHÔNG phải một phép đo hiệu năng.
    """

    SO_TT = 2
    SO_PHEP = 25

    @classmethod
    def setUpClass(cls):
        q("BEGIN;\n" + DDL_PG + "\nCOMMIT;")
        cls._dat_lai()

    @staticmethod
    def _dat_lai():
        q("DROP TABLE IF EXISTS g15_dem;"
          " CREATE TABLE g15_dem (id int PRIMARY KEY, gia_tri int NOT NULL);"
          " INSERT INTO g15_dem VALUES (1,0);")

    @staticmethod
    def _psql_stdin():
        return subprocess.Popen(["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                                 "-d", CSDL_THU, "-qtAX", "-v", "ON_ERROR_STOP=1"],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)

    @staticmethod
    def _q_verbose(sql):
        """psql có `VERBOSITY=verbose` để stderr mang SQLSTATE. Cần SQLSTATE vì phán bằng CHỮ
        trong thông báo là phán bằng thứ có thể đổi theo phiên bản/locale."""
        p = subprocess.run(["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                            "-d", CSDL_THU, "-qtAX", "-v", "VERBOSITY=verbose"],
                           input=sql, capture_output=True, text=True)
        return p.returncode, p.stdout, p.stderr, re.findall(r"ERROR:\s+([0-9A-Z]{5}):", p.stderr)

    def _pg_khuon_ngay_tho(self):
        """Một script `psql` = MỘT tiến trình. Mỗi phép là một giao dịch riêng, và nó ĐỌC
        giá trị ở NGOÀI giao dịch rồi ghi lại giá trị đã đọc — đúng khuôn ngây thơ.
        Dùng psql chứ không `multiprocessing` để khỏi spawn lại chính mô-đun này."""
        mot = ("SELECT gia_tri AS v FROM g15_dem WHERE id=1 \\gset\n"
               "BEGIN;\nSELECT pg_sleep(0.002);\n"
               "UPDATE g15_dem SET gia_tri = :v + 1 WHERE id=1;\nCOMMIT;\n")
        return mot * self.SO_PHEP

    def test_e1_chot_thanh_cong_cong_nguyen_tu(self):
        """CHỐT_THÀNH_CÔNG: cộng ở TẦNG CÂU (`gia_tri = gia_tri + 1`), 2 tiến trình."""
        self._dat_lai()
        ps = [self._psql_stdin() for _ in range(self.SO_TT)]
        for p in ps:
            p.stdin.write("UPDATE g15_dem SET gia_tri = gia_tri + 1 WHERE id=1;\n"
                          * self.SO_PHEP)
            p.stdin.close()
        ma = [p.wait() for p in ps]
        for p in ps:                       # đóng ống để không rò tệp (ResourceWarning)
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(ma, [0] * self.SO_TT, "có tiến trình thoát khác 0")
        _, out, _ = q("SELECT gia_tri FROM g15_dem WHERE id=1")
        self.assertEqual(int(out.strip()), self.SO_TT * self.SO_PHEP,
                         "CHỐT_THÀNH_CÔNG mà số THẬT lệch số TIN đã ghi")

    # ---- BẮT TAY BẰNG TỆP MỐC: để phép đo KHÔNG phụ thuộc tải máy ----
    # Bản đầu của e2/e3 đo bằng CÁCH CHẠY ĐUA (2 tiến trình cùng đọc–ghi, đếm xem mất bao
    # nhiêu). Nó ĐÚNG về bản chất nhưng **HỎNG KHI MÁY TẢI**: nếu hai tiến trình bị hệ điều
    # hành xếp chạy nối đuôi thì không mất lượt nào, và ca thử báo hỏng trong khi hệ làm đúng
    # — đúng loại "báo hỏng giả" mà `BAN_GIAO.md` §7.1 cảnh báo. Đo được: 1/3 lượt hồi quy
    # đầy đủ (máy đang có agent khác chạy) so với 10/10 lượt chạy riêng.
    #
    # Nay ÉP thứ tự: CẢ HAI bên đọc xong (mỗi bên chạm tệp mốc của mình rồi chờ tệp mốc của
    # bên kia) RỒI mới ghi. Không còn phụ thuộc lịch trình của hệ điều hành, và phép đo mạnh
    # hơn: nó chỉ ra thẳng CƠ CHẾ (hai giao dịch cùng đọc một giá trị rồi cùng ghi).
    @staticmethod
    def _tep_moc(ten):
        goc = CUM.thu_muc or tempfile.gettempdir()
        return os.path.join(goc, "e23_%s.moc" % ten)

    @classmethod
    def _xoa_moc(cls):
        for ten in ("a", "b"):
            f = cls._tep_moc(ten)
            if os.path.exists(f):
                os.remove(f)

    CHO_MOC = "n=0; while [ ! -f %s ] && [ $n -lt 1200 ]; do sleep 0.05; n=$((n+1)); done\n"

    def test_e2_postgres_mat_cap_nhat_IM_LANG(self):
        """**PHÁT HIỆN CHÍNH, đo TẤT ĐỊNH.** PostgreSQL + khuôn đọc-rồi-ghi ngây thơ ⇒ mất
        cập nhật và **KHÔNG một lượt nào báo lỗi**.

        Phép đo không đếm xác suất: hai phiên CÙNG đọc `gia_tri=0`, bắt tay cho chắc cả hai
        đã đọc xong, rồi CẢ HAI ghi `0 + 1 = 1`. Hai giao dịch chốt thành công, giá trị cuối
        là **1** — mất đúng một cập nhật, im lặng. Nếu ca này bắt đầu HỎNG thì hoặc PostgreSQL
        đã đổi hành vi, hoặc phép đo hỏng — cả hai đều phải xem lại, ĐỪNG gỡ ca."""
        self._dat_lai()
        self._xoa_moc()
        kich_ban = ("SELECT gia_tri AS v FROM g15_dem WHERE id=1 \\gset\n"
                    "\\! touch %s\n"
                    "\\! " + self.CHO_MOC +
                    "UPDATE g15_dem SET gia_tri = :v + 1 WHERE id=1;\n")
        ps = []
        for ten, ten_kia in (("a", "b"), ("b", "a")):
            p = self._psql_stdin()
            p.stdin.write(kich_ban % (self._tep_moc(ten), self._tep_moc(ten_kia)))
            p.stdin.flush()
            ps.append(p)
        ma, loi = [], []
        for p in ps:
            p.stdin.close()
            ma.append(p.wait(timeout=180))
            loi.append(p.stderr.read())
            p.stdout.close()
            p.stderr.close()
        self.assertEqual(ma, [0, 0], "PostgreSQL báo lỗi: %s" % " | ".join(loi)[:300])
        self.assertEqual("".join(loi).strip(), "",
                         "có lỗi trên stderr — lượt này KHÔNG còn là 'im lặng'")
        _, out, _ = q("SELECT gia_tri FROM g15_dem WHERE id=1")
        self.assertEqual(int(out.strip()), 1,
                         "HAI giao dịch cùng đọc 0 rồi cùng ghi 1, nên giá trị cuối PHẢI là 1 "
                         "(= mất một cập nhật). Nhận %s — hành vi đã đổi, đọc "
                         "`docs/G15_INFRA.md` §2 trước khi sửa ca này." % out.strip())

    def test_e3_sqlite_tu_choi_on_ao(self):
        """Đối chứng: SQLite với CÙNG khuôn và CÙNG cách bắt tay thì **TỪ CHỐI** thay vì mất.

        Đây là vế làm cho e2 có nghĩa: không có nó thì không ai biết PostgreSQL khác SQLite ở
        ĐÂU. Bản trước đếm xác suất (`assertGreater(loi, 0)`) nên cũng phụ thuộc tải; bản này
        ép thứ tự đọc-trước-ghi-sau nên **tất định**."""
        import sqlite3
        thu_muc = tempfile.mkdtemp(prefix="vhg15-")
        duong = os.path.join(thu_muc, "nhap.db")
        kn = sqlite3.connect(duong, isolation_level=None)
        kn.execute("PRAGMA journal_mode=WAL")
        kn.execute("CREATE TABLE g15_dem (id INTEGER PRIMARY KEY, gia_tri INTEGER NOT NULL)")
        kn.execute("INSERT INTO g15_dem VALUES (1,0)")
        kn.close()
        moc = (os.path.join(thu_muc, "a.moc"), os.path.join(thu_muc, "b.moc"))
        tho = (
            "import os, sqlite3, sys, time\n"
            "moc, moc_kia, duong = sys.argv[1], sys.argv[2], sys.argv[3]\n"
            "kn = sqlite3.connect(duong, timeout=5.0, isolation_level=None)\n"
            "kn.execute('PRAGMA busy_timeout=2000')\n"
            "kn.execute('BEGIN')\n"                       # giao dịch HOÃN, như khuôn ngây thơ
            "cu = kn.execute('SELECT gia_tri FROM g15_dem WHERE id=1').fetchone()[0]\n"
            "open(moc, 'w').write('x')\n"                # đã ĐỌC xong
            "het = time.time() + 60\n"
            "while not os.path.exists(moc_kia) and time.time() < het: time.sleep(0.02)\n"
            "try:\n"                                      # cả hai đã đọc, giờ mới ghi
            "    kn.execute('UPDATE g15_dem SET gia_tri=? WHERE id=1', (cu + 1,))\n"
            "    kn.execute('COMMIT')\n"
            "    print('TIN', cu)\n"
            "except sqlite3.Error as e:\n"
            "    print('LOI', type(e).__name__, str(e)[:60])\n")
        ps = []
        try:
            for i in (0, 1):
                ps.append(subprocess.Popen(
                    [sys.executable, "-c", tho, moc[i], moc[1 - i], duong],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            ra = [p.communicate(timeout=180) for p in ps]
            self.assertEqual([p.returncode for p in ps], [0, 0],
                             "tiến trình SQLite thoát khác 0: %s" % str(ra)[:300])
            kn = sqlite3.connect(duong)
            that = kn.execute("SELECT gia_tri FROM g15_dem WHERE id=1").fetchone()[0]
            kn.close()
        finally:
            shutil.rmtree(thu_muc, ignore_errors=True)
        tin = sum(1 for x in ra if x[0].strip().startswith("TIN"))
        loi = [x[0].strip() for x in ra if x[0].strip().startswith("LOI")]
        # SQLite PHẢI từ chối ít nhất một bên: sau khi bên kia chốt, ảnh đọc của bên này đã cũ
        # nên lượt nâng khoá thất bại (`SQLITE_BUSY_SNAPSHOT`) — trả NGAY, `busy_timeout`
        # không chờ ca này (SHARED_CONTRACTS §30.4).
        self.assertEqual(tin, 1,
                         "SQLite cho qua %d lượt chốt (lẽ ra đúng 1). Nếu là 2 thì nó ĐÃ âm "
                         "thầm mất một cập nhật — TRÁI với số đo 15/10/2026, phải đo lại "
                         "trước khi tin. Chi tiết: %s" % (tin, ra))
        self.assertEqual(len(loi), 1, "SQLite lẽ ra phải TỪ CHỐI đúng một bên: %s" % ra)
        self.assertEqual(that, 1, "giá trị cuối phải là 1 (một lượt chốt), nhận %s" % that)
        print("        SQLite từ chối ồn ào: %s" % loi[0][:110])

    def test_e4_khoa_het_gio_va_giao_dich_hong(self):
        """Hai kết cục còn lại, phân biệt bằng SQLSTATE — không bằng chữ trong thông báo.

        · `55P03` lock_not_available  = KHOA_HET_GIO     (thử lại được, an toàn)
        · `P0001` + `25P02`           = GIAO_DICH_HONG   (thử lại VÔ ÍCH, phải sửa dữ liệu)
        """
        self._dat_lai()
        q("UPDATE g15_dem SET gia_tri=7 WHERE id=1")
        goc_tam = CUM.thu_muc or tempfile.gettempdir()
        moc, tha = os.path.join(goc_tam, "e4.giu"), os.path.join(goc_tam, "e4.tha")
        for f in (moc, tha):
            if os.path.exists(f):
                os.remove(f)
        giu = subprocess.Popen(["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                                "-d", CSDL_THU, "-qtAX"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        giu.stdin.write("BEGIN;\nUPDATE g15_dem SET gia_tri=99 WHERE id=1;\n"
                        "\\! touch %s\n\\! while [ ! -f %s ]; do sleep 0.1; done\nROLLBACK;\n\\q\n"
                        % (moc, tha))
        giu.stdin.flush()
        het = time.time() + 60
        while not os.path.exists(moc) and time.time() < het:
            time.sleep(0.05)
        self.assertTrue(os.path.exists(moc), "kết nối giữ khoá không vào được giao dịch")
        _, _, err, ma_loi = self._q_verbose(
            "SET lock_timeout='400ms';\nBEGIN;\n"
            "UPDATE g15_dem SET gia_tri=1 WHERE id=1;\nCOMMIT;")
        with open(tha, "w") as _f:
            _f.write("tha")
        giu.wait(timeout=20)
        giu.stdin.close()
        giu.stdout.close()
        giu.stderr.close()
        self.assertIn("55P03", ma_loi,
                      "KHOA_HET_GIO phải là SQLSTATE 55P03, nhận %s — stderr: %s"
                      % (ma_loi or "(không có SQLSTATE)", err[-200:]))
        _, out, _ = q("SELECT gia_tri FROM g15_dem WHERE id=1")
        self.assertEqual(out.strip(), "7", "KHOA_HET_GIO mà vẫn ghi được — sai")
        # GIAO_DICH_HONG: dùng chính bảng bút toán bất biến đã dựng ở lớp B.
        rc = q("INSERT INTO tc_but_toan (tenant_id,loai,so_tien_dong,chieu,nguon,can_cu,tao_luc)"
               " VALUES (1,'cod',1000,'ghi_no','hang','e4','x')")[0]
        self.assertEqual(rc, 0)
        ma_bt = q("SELECT max(id) FROM tc_but_toan")[1].strip()
        _, _, err_all, ma_all = self._q_verbose(
            "\\echo C1\nBEGIN;\n\\echo C2\n"
            "UPDATE tc_but_toan SET so_tien_dong=1 WHERE id=%s;\n\\echo C3\n"
            "INSERT INTO tc_but_toan (tenant_id,loai,so_tien_dong,chieu,nguon,can_cu,tao_luc)"
            " VALUES (1,'cod',5000,'ghi_no','hang','sau-trigger','x');\n\\echo C4\nCOMMIT;\n"
            % ma_bt)
        self.assertIn("P0001", ma_all, "trigger phải ném P0001: %s" % err_all[-200:])
        self.assertIn("25P02", ma_all,
                      "câu SAU trigger phải bị chối bằng 25P02 — PostgreSQL huỷ CẢ giao dịch, "
                      "khác `RAISE(ABORT)` của SQLite chỉ huỷ CÂU: %s" % err_all[-300:])


# =====================================================================================
# G17 / AG-05 — NĂM LỚP THÊM (F…K)
#
# Bốn thứ được yêu cầu ở G17 mà A…E CHƯA trả lời được:
#   F. chốt chặn cổng 5432 phải TỪ CHỐI THẬT (D chỉ kiểm hàm ở tầng đơn vị)
#   G. vân tay cụm hệ thống :5432 TRƯỚC = SAU (chưa có ở đâu)
#   H. khoá tư vấn cho migration, TẤT ĐỊNH và có ĐỐI CHỨNG ÂM
#   I. DDL nguyên tử — đối chiếu số BẢNG/CỘT TRƯỚC–SAU (A chỉ nói "nạp được")
#   J. đo KHỐI mất-cập-nhật, kèm ĐỐI CHỨNG DƯƠNG cho chính đồng hồ đo
#   K. sao lưu/khôi phục: số dòng từng bảng + tổng TIỀN + payload NHỊ PHÂN
# =====================================================================================
KHOA_MIGRATION = 991204          # số khoá tư vấn; chỉ có nghĩa trong cụm thử


def _tao_csdl(ten):
    """Tạo một CSDL mới tinh trong CỤM THỬ. Không bao giờ chạm cụm :5432."""
    CUM.psql("DROP DATABASE IF EXISTS %s" % ten, db="postgres")
    rc, _, err = CUM.psql("CREATE DATABASE %s" % ten, db="postgres")
    if rc:
        raise AssertionError("không tạo được CSDL %s: %s" % (ten, err[-300:]))


def _xoa_csdl(ten):
    CUM.psql("DROP DATABASE IF EXISTS %s" % ten, db="postgres")


def _psql_verbose(sql, db):
    """psql có `VERBOSITY=verbose` để stderr mang SQLSTATE. Cần SQLSTATE vì phán bằng CHỮ
    trong thông báo là phán bằng thứ đổi theo phiên bản/locale."""
    p = subprocess.run(["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                        "-d", db, "-qtAX", "-v", "VERBOSITY=verbose"],
                       input=sql, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr, re.findall(r"ERROR:\s+([0-9A-Z]{5}):", p.stderr)


def _dem_bang_cot(db):
    """Đếm BẢNG và CỘT của một CSDL PostgreSQL. Trả (số bảng, số cột)."""
    _, b, _ = CUM.psql("SELECT count(*) FROM pg_tables WHERE schemaname='public'", db=db)
    _, c, _ = CUM.psql("SELECT count(*) FROM information_schema.columns"
                       " WHERE table_schema='public'", db=db)
    return int(b.strip() or -1), int(c.strip() or -1)


def _schema_sqlite():
    """Dựng schema THẬT trong SQLite `:memory:` TỪ CHÍNH mã đang chạy.

    Không chép tay bản thứ hai, nên nó KHÔNG THỂ cũ hơn mã. Trả `{tên bảng: {tên cột}}`.
    """
    import sqlite3
    import csdl
    import ai_job
    import goi_dich_vu
    import harness_hang
    import quan_sat
    import tai_chinh
    kn = sqlite3.connect(":memory:")
    for s in (csdl.SCHEMA, tai_chinh.DDL_G07, goi_dich_vu.DDL_G08,
              harness_hang.DDL_G09, ai_job.DDL_G10, quan_sat.DDL_G11):
        kn.executescript(s)
    ra = {}
    for (ten,) in kn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        if ten == "sqlite_sequence":     # bảng của chính SQLite, không phải của dự án
            continue
        ra[ten] = {r[1] for r in kn.execute("PRAGMA table_info(%s)" % ten)}
    kn.close()
    return ra


# ------------------------------------------------- F. chốt chặn cổng 5432, chạy THẬT
class F_ChotChanCong5432ThatSu(unittest.TestCase):
    """Chốt chặn cổng 5432 phải TỪ CHỐI THẬT — không chỉ tồn tại trong mã.

    `D.test_d1` kiểm hàm `_kiem_cong_an_toan` ở tầng ĐƠN VỊ. Nó không trả lời được câu hỏi
    quan trọng nhất: khi ai đó THẬT SỰ trỏ cả bộ thử vào cổng 5432 thì chuyện gì xảy ra.
    Ở đây chạy ĐÚNG lệnh đó trong một tiến trình RIÊNG, rồi đối chiếu vân tay cụm :5432.

    Cặp ca f1/f2 là một cặp ĐỐI CHỨNG: cùng một lệnh, chỉ khác CỔNG. Thiếu f2 thì f1 chỉ
    nói được "lệnh đó thoát khác 0" — mà một lỗi cú pháp cũng thoát khác 0.
    """

    def _chay_bo_thu(self, cong, ten_lop):
        """Chạy bộ thử này trong tiến trình riêng, TMPDIR riêng để bắt được cả tệp tạm.

        `ten_lop` là BẮT BUỘC, và đó là một chốt chặn chứ không phải tiện lợi: nếu tiến
        trình con chạy CẢ bộ thử thì nó chạy lại chính lớp F, lớp F lại sinh một tiến trình
        con nữa — đệ quy. Đo được ngày 15/10/2026: khi chốt chặn cổng bị gỡ (đột biến), lượt
        chạy đệ quy và ca thử `f1` **XANH vì lý do SAI** (nó bắt được chữ `TỪ CHỐI` từ tầng
        đệ quy sâu hơn, trong thông báo lỗi của chính nó). Chạy đúng một lớp thì phép đo chỉ
        còn một biến số: CỔNG.
        """
        tmp = tempfile.mkdtemp(prefix="vhpg-f-")
        moi = dict(os.environ, VHPG_CONG=str(cong), TMPDIR=tmp, LANG="C", LC_ALL="C")
        moi.pop("VHPG_SOCKET", None)          # ép nó phải tự quyết định theo cổng
        p = subprocess.run([sys.executable, os.path.abspath(__file__), ten_lop],
                           capture_output=True, text=True, env=moi, cwd=DU_AN, timeout=600)
        return p, tmp

    @staticmethod
    def _sock_tmp():
        return set(glob.glob("/tmp/vhpg.*"))

    def test_f1_tro_vao_cong_5432_thi_tu_choi_va_khong_dung_gi(self):
        truoc = van_tay_cum.chup(CONG_CAM)
        if not truoc["truy_cap_duoc"]:
            self.skipTest("cụm :%s không chạy — không đo được vân tay" % CONG_CAM)
        sock_truoc = self._sock_tmp()
        # Chạy ĐÚNG lớp D (4 ca, không sinh tiến trình con) — xem `_chay_bo_thu`.
        p, tmp = self._chay_bo_thu(CONG_CAM, "D_ChotChanCuaBoThu")
        try:
            ra = p.stdout + p.stderr
            self.assertNotEqual(p.returncode, 0,
                                "bộ thử CHẠY trên cổng 5432 mà vẫn thoát 0 — chốt chặn đã mất")
            self.assertIn("TỪ CHỐI", ra, "không thấy lời từ chối: %s" % ra[-300:])
            self.assertIn("vip_customs", ra,
                          "lời từ chối phải NÓI RÕ cụm đó đang giữ CSDL của ai")
            self.assertIn("Ran 0 tests", ra,
                          "lẽ ra phải từ chối TRƯỚC khi chạy ca nào — thấy: %s"
                          % re.findall(r"Ran \d+ tests", ra))
            _, _, err, _ = _psql_verbose("SELECT 1", "postgres")   # cụm thử còn sống không
            self.assertEqual(err, "", "cụm thử có vấn đề: %s" % err[-200:])
            self.assertEqual(os.listdir(tmp), [],
                             "đã từ chối mà vẫn dựng thư mục dữ liệu trong TMPDIR riêng")
            self.assertEqual(self._sock_tmp() - sock_truoc, set(),
                             "đã từ chối mà vẫn tạo thư mục socket mới trong /tmp")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        giong, lech = van_tay_cum.so_sanh(truoc, van_tay_cum.chup(CONG_CAM))
        self.assertTrue(giong, "vân tay :%s ĐỔI sau lượt từ chối: %s" % (CONG_CAM, lech))

    def test_f2_doi_chung_duong_cong_khac_thi_khong_tu_choi(self):
        """ĐỐI CHỨNG DƯƠNG: CÙNG lệnh đó, chỉ đổi cổng sang 55433 → KHÔNG từ chối, chạy
        bình thường. Đây là vế làm cho f1 có nghĩa: nó chỉ ra nguyên nhân là CỔNG."""
        p, tmp = self._chay_bo_thu(55433, "D_ChotChanCuaBoThu")
        try:
            ra = p.stdout + p.stderr
            self.assertNotIn("TỪ CHỐI chạy trên cổng", ra, "cổng hợp lệ mà vẫn bị từ chối")
            self.assertEqual(p.returncode, 0, ra[-500:])
            self.assertIn("Ran 4 tests", ra, "đối chứng dương phải CHẠY ĐƯỢC ca: %s" % ra[-300:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------- G. vân tay cụm hệ thống :5432 TRƯỚC = SAU
class G_VanTayCumHeThong(unittest.TestCase):
    """Yêu cầu G17: *"mọi báo cáo phải ghi rõ … vân tay cụm :5432 TRƯỚC = SAU
    (PID postmaster, danh sách CSDL)"*. Một lời khai không phải một phép đo — lớp này đo.

    Lượt chụp TRƯỚC lấy ở `setUpModule`, TRƯỚC cả `initdb` của cụm thử. Gọi lại ở đây và
    đối chiếu. `tearDownModule` chụp thêm một lượt SAU khi đã dọn, in ra để báo cáo có số.
    """

    def test_g1_van_tay_khong_doi(self):
        if VT_TRUOC is None or not VT_TRUOC.get("truy_cap_duoc"):
            self.skipTest("cụm :%s không chạy trên máy này — không đo được vân tay. %s"
                          % (CONG_CAM, (VT_TRUOC or {}).get("ghi_chu", "")))
        sau = van_tay_cum.chup(CONG_CAM)
        giong, lech = van_tay_cum.so_sanh(VT_TRUOC, sau)
        self.assertTrue(giong, "VÂN TAY CỤM :%s ĐÃ ĐỔI giữa lượt chạy: %s" % (CONG_CAM, lech))

    def test_g2_van_tay_phai_doc_duoc_that(self):
        """TỰ CHẶN CA XANH GIẢ. Cụm không đọc được thì `chup()` trả `truy_cap_duoc=False`
        cho CẢ HAI lượt, và "TRƯỚC = SAU" đúng một cách vô nghĩa. Ca này đòi vân tay phải
        có NỘI DUNG THẬT — PID, `data_directory`, và danh sách CSDL phải chứa CSDL của
        dự án kia (tức là đang nhìn ĐÚNG cụm, không phải một cụm rỗng nào khác)."""
        if VT_TRUOC is None or not VT_TRUOC.get("truy_cap_duoc"):
            self.skipTest("cụm :%s không chạy — bỏ qua, có nêu lý do" % CONG_CAM)
        self.assertTrue(VT_TRUOC.get("pid"), "vân tay thiếu PID postmaster")
        self.assertTrue(VT_TRUOC.get("data_directory"), "vân tay thiếu data_directory")
        self.assertGreaterEqual(VT_TRUOC.get("so_csdl", 0), 1,
                                "danh sách CSDL rỗng — vân tay vô nghĩa")
        self.assertTrue(any(d.startswith("vip_customs") for d in VT_TRUOC["danh_sach_csdl"]),
                        "danh sách CSDL KHÔNG có `vip_customs*` — đang nhìn nhầm cụm: %s"
                        % VT_TRUOC["danh_sach_csdl"])

    def test_g3_phep_so_phat_hien_duoc_khac_biet(self):
        """TỰ KIỂM BỎ ĐỒ: phép so phải LÀM ĐỎ ĐƯỢC. Tiêm một khác biệt vào bản sao vân tay
        rồi đòi `so_sanh` báo lệch. Không có ca này thì một `so_sanh` luôn trả `True` cũng
        "đạt" ở g1 — và cả báo cáo "TRƯỚC = SAU" trở thành đồ trang trí."""
        if VT_TRUOC is None or not VT_TRUOC.get("truy_cap_duoc"):
            self.skipTest("cụm :%s không chạy" % CONG_CAM)
        for truong, gia_tri in (("pid", "999999"),
                                ("danh_sach_csdl",
                                 sorted(VT_TRUOC["danh_sach_csdl"] + ["csdl_them_vao"])),
                                ("postmaster_bat_dau", "2000-01-01 00:00:00+07"),
                                ("phien_ban_may_chu", "0.0-gia")):
            ban_sao = json.loads(json.dumps(VT_TRUOC))
            ban_sao[truong] = gia_tri
            if truong == "danh_sach_csdl":
                ban_sao["so_csdl"] = len(gia_tri)
            giong, lech = van_tay_cum.so_sanh(VT_TRUOC, ban_sao)
            self.assertFalse(giong, "so_sanh KHÔNG phát hiện `%s` đổi — phép so là đồ giả"
                             % truong)
            self.assertIn(truong, [x[0] for x in lech],
                          "lệch báo sai trường: %s" % lech)
        # Vế còn lại: một lượt chụp KHÔNG đọc được cụm thì KHÔNG được phán "giống".
        chet = dict(VT_TRUOC, truy_cap_duoc=False, so_csdl=0, danh_sach_csdl=[])
        self.assertFalse(van_tay_cum.so_sanh(VT_TRUOC, chet)[0],
                         "so_sanh phán 'giống' khi một bên không đọc được cụm")


# ------------------------------------------ H. khoá tư vấn: đúng MỘT tiến trình migration
class H_MigrationKhoaTuVan(unittest.TestCase):
    """Khoá tư vấn (advisory lock) để CHỈ MỘT tiến trình migration nâng cấp.

    Vì sao cần: `migrate.chay()` đọc phiên bản rồi mới nâng. Hai tiến trình cùng làm việc
    đó thì cả hai cùng thấy 7 và cùng nâng lên 8. Trên SQLite chuyện đó bị chặn bằng khoá
    ghi của tệp; trên PostgreSQL không có gì chặn — phải XIN khoá tường minh.

    PHÉP ĐO NÀY TẤT ĐỊNH, không dựa vào may rủi lịch trình: hai tiến trình BẮT TAY qua một
    bảng hàng rào (`hang_rao`) trước khi vào giao dịch nâng cấp, nên chắc chắn cả hai đã
    sẵn sàng. Có khoá thì cái thứ hai NHƯỜNG; không khoá (ĐỐI CHỨNG ÂM) thì cái thứ hai ĐỤNG.
    """

    @staticmethod
    def _dat_lai():
        q("DROP TABLE IF EXISTS pb_migration CASCADE;"
          " DROP TABLE IF EXISTS bang_v8 CASCADE;"
          " DROP TABLE IF EXISTS hang_rao CASCADE;"
          " CREATE TABLE pb_migration (phien_ban int PRIMARY KEY);"
          " INSERT INTO pb_migration VALUES (7);"
          " CREATE TABLE hang_rao (ten text PRIMARY KEY);")

    @staticmethod
    def _kich_ban(ten, dung_khoa):
        than = "INSERT INTO hang_rao (ten) VALUES ('%s');\n" % ten
        than += ("DO $$ DECLARE n int; BEGIN\n"
                 "  LOOP SELECT count(*) INTO n FROM hang_rao;"
                 " EXIT WHEN n >= 2; PERFORM pg_sleep(0.05); END LOOP;\n"
                 "END $$;\n")
        than += "BEGIN;\n"
        if dung_khoa:
            than += "SELECT pg_advisory_xact_lock(%d);\n" % KHOA_MIGRATION
        than += ("DO $$ DECLARE v int; BEGIN\n"
                 # `max(...)` chứ KHÔNG `SELECT phien_ban INTO v`: bảng phiên bản TÍCH LUỸ
                 # dòng, nên `SELECT phien_ban INTO v` lấy một dòng BẤT KỲ. Bản đầu của ca
                 # này viết thiếu `max()` và nó đọc trúng dòng CŨ (7) sau khi tiến trình kia
                 # đã nâng lên 8 — làm phép đo báo "khoá tư vấn không tác dụng" trong khi
                 # khoá vẫn tốt. Đo lại bằng `max()` mới thấy đúng: xem docs/G17_POSTGRES.md.
                 "  SELECT max(phien_ban) INTO v FROM pb_migration;\n"
                 # `pg_sleep` giữ cửa sổ ĐỌC–RỒI–GHI mở đủ rộng. Không có nó thì lượt
                 # KHÔNG khoá (đối chứng âm) có thể chạy nối đuôi nhau và cho ra kết quả
                 # GIỐNG lượt có khoá — đối chứng mất tác dụng. Bản đầu thiếu dòng này và
                 # h2 đã hỏng đúng vì lý do đó (đo 15/10/2026).
                 "  PERFORM pg_sleep(0.4);\n"
                 "  IF v < 8 THEN\n"
                 "    CREATE TABLE IF NOT EXISTS bang_v8 (id int primary key, ghi_chu text);\n"
                 "    INSERT INTO pb_migration VALUES (8);\n"
                 "    RAISE NOTICE 'DA_NANG_CAP';\n"
                 "  ELSE RAISE NOTICE 'NHUONG'; END IF;\n"
                 "END $$;\nCOMMIT;\n")
        return than

    def _chay_hai(self, dung_khoa):
        """Hai tiến trình `psql` THẬT, chạy chồng nhau (không nối đuôi)."""
        self._dat_lai()
        ps = []
        for ten in ("a", "b"):
            p = subprocess.Popen(
                ["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                 "-d", CSDL_THU, "-qtAX", "-v", "VERBOSITY=verbose", "-v", "ON_ERROR_STOP=1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            p.stdin.write(self._kich_ban(ten, dung_khoa))
            p.stdin.flush()
            ps.append(p)
        ra = []
        for p in ps:
            p.stdin.close()
            ma = p.wait(timeout=240)
            out, err = p.stdout.read(), p.stderr.read()
            p.stdout.close()
            p.stderr.close()
            ra.append({"rc": ma, "ra": out + err,
                       "loi": re.findall(r"ERROR:\s+([0-9A-Z]{5}):", err)})
        _, pb, _ = q("SELECT count(*)||'|'||max(phien_ban) FROM pb_migration")
        _, v8, _ = q("SELECT count(*) FROM pg_tables"
                     " WHERE schemaname='public' AND tablename='bang_v8'")
        return ra, pb.strip(), v8.strip()

    def test_h1_co_khoa_thi_dung_mot_tien_trinh_nang_cap(self):
        ra, pb, v8 = self._chay_hai(dung_khoa=True)
        nang = sum(1 for k in ra if "DA_NANG_CAP" in k["ra"])
        nhuong = sum(1 for k in ra if "NHUONG" in k["ra"])
        loi = [x for k in ra for x in k["loi"]]
        print("        CÓ khoá   : nâng=%d · nhường=%d · lỗi=%s · pb=%s · bảng v8=%s"
              % (nang, nhuong, sorted(set(loi)) or "không", pb, v8))
        self.assertEqual(nang, 1, "lẽ ra đúng MỘT tiến trình nâng cấp, nhận %d" % nang)
        self.assertEqual(nhuong, 1, "tiến trình kia phải NHƯỜNG, nhận %d" % nhuong)
        self.assertEqual(loi, [], "có tiến trình báo lỗi dù đã có khoá: %s" % loi)
        self.assertEqual(pb, "2|8", "phải đúng 2 dòng phiên bản và max=8, nhận %s" % pb)
        self.assertEqual(v8, "1", "bảng `bang_v8` phải có đúng một lần")

    def test_h2_doi_chung_am_bo_khoa_thi_dung_nhau(self):
        """ĐỐI CHỨNG ÂM — vế làm cho h1 có nghĩa. CÙNG kịch bản, CÙNG cách bắt tay, chỉ bỏ
        đúng một dòng `pg_advisory_xact_lock`. Kết quả PHẢI KHÁC h1; nếu vẫn giống thì phép
        đo ở h1 không hề chạm tới khoá, và "đúng một tiến trình nâng cấp" là do may."""
        ra, pb, v8 = self._chay_hai(dung_khoa=False)
        nang = sum(1 for k in ra if "DA_NANG_CAP" in k["ra"])
        nhuong = sum(1 for k in ra if "NHUONG" in k["ra"])
        loi = [x for k in ra for x in k["loi"]]
        print("        KHÔNG khoá: nâng=%d · nhường=%d · lỗi=%s · pb=%s · bảng v8=%s"
              % (nang, nhuong, sorted(set(loi)) or "không", pb, v8))
        self.assertTrue(loi, "bỏ khoá mà KHÔNG tiến trình nào đụng nhau — phép đo ở h1 "
                             "không chạm tới khoá, ĐỪNG tin kết quả h1")
        self.assertIn("23505", loi, "đụng độ phải là 23505 unique_violation, nhận %s" % loi)


# --------------------------------------------------- I. DDL nguyên tử: TRƯỚC–SAU số bảng/cột
class I_DDLNguyenTuTruocSau(unittest.TestCase):
    """Schema THẬT nạp trong MỘT giao dịch — và đối chiếu số BẢNG/CỘT TRƯỚC–SAU.

    `A.test_a1` đã khẳng định "nạp được". Lớp này thêm đúng thứ mà "nạp được" KHÔNG nói lên:
    TRƯỚC là bao nhiêu, SAU là bao nhiêu, con số SAU có khớp schema SQLite đang chạy không,
    và khi hỏng giữa khối thì có lùi về đúng con số TRƯỚC hay không.
    """

    CSDL_DUONG = "vh_g17_duong"
    CSDL_AM = "vh_g17_am"

    def test_i1_truoc_sau_va_khop_sqlite(self):
        _tao_csdl(self.CSDL_DUONG)
        try:
            b_truoc, c_truoc = _dem_bang_cot(self.CSDL_DUONG)
            self.assertEqual((b_truoc, c_truoc), (0, 0),
                             "CSDL mới tinh mà đã có bảng/cột — phép đo nhìn nhầm chỗ")
            rc, _, err = CUM.psql("BEGIN;\n" + DDL_PG + "\nCOMMIT;", db=self.CSDL_DUONG)
            self.assertEqual(rc, 0, "DDL không nạp trọn trong một giao dịch:\n" + err[-900:])
            b_sau, c_sau = _dem_bang_cot(self.CSDL_DUONG)
            sl = _schema_sqlite()
            so_cot_sl = sum(len(v) for v in sl.values())
            print("        TRƯỚC: %d bảng / %d cột  →  SAU: %d bảng / %d cột"
                  "   (SQLite đang chạy: %d bảng / %d cột)"
                  % (b_truoc, c_truoc, b_sau, c_sau, len(sl), so_cot_sl))
            self.assertGreaterEqual(b_sau, 40,
                                    "chỉ %d bảng — chặn ca 'DDL rỗng cũng nạp đạt'" % b_sau)
            self.assertEqual(b_sau, len(sl), "số BẢNG lệch với SQLite đang chạy")
            self.assertEqual(c_sau, so_cot_sl, "số CỘT lệch với SQLite đang chạy")
        finally:
            _xoa_csdl(self.CSDL_DUONG)

    def test_i2_doi_chung_am_hong_giua_khoi_thi_lui_ve_dung_truoc(self):
        """ĐỐI CHỨNG ÂM: cùng khối DDL đó, chèn một câu SAI vào CUỐI. Mọi bảng đứng TRƯỚC
        câu sai — kể cả `tenants` — phải BIẾN MẤT. Không có ca này thì "47 bảng" ở i1 có
        thể đạt được ngay cả khi giao dịch không hề nguyên tử."""
        _tao_csdl(self.CSDL_AM)
        try:
            rc, out, err, ma = _psql_verbose(
                "BEGIN;\n" + DDL_PG + "\nCREATE TABLE cau_sai_co_y (id int, );\nCOMMIT;\n",
                self.CSDL_AM)
            print("        đối chứng âm: mã thoát psql=%d · SQLSTATE=%s" % (rc, ma or "(không)"))
            self.assertIn("42601", ma, "câu sai lẽ ra phải bị từ chối bằng 42601 syntax_error")
            b_am, c_am = _dem_bang_cot(self.CSDL_AM)
            self.assertEqual((b_am, c_am), (0, 0),
                             "rollback KHÔNG sạch: còn %d bảng / %d cột" % (b_am, c_am))
            _, con, _ = CUM.psql(
                "SELECT count(*) FROM information_schema.tables"
                " WHERE table_schema='public' AND table_name='tenants'", db=self.CSDL_AM)
            self.assertEqual(con.strip(), "0",
                             "bảng `tenants` đứng TRƯỚC câu sai mà vẫn còn — giao dịch "
                             "KHÔNG nguyên tử")
        finally:
            _xoa_csdl(self.CSDL_AM)

    def test_i3_hai_bang_do_migration_nam_ngoai_bo_ddl(self):
        """GHIM PHẠM VI, bằng số đo. Bộ DDL 47 bảng là schema NỀN. Hai bảng `don_mat_hang`
        và `han_muc_nhap_thang` do `migrate.py` tạo ở đường ALTER (`nang_len_v7/v8`), nên
        CHƯA có trong phép diễn tập này.

        Ca này ghim con số đó lại: ai thêm một bảng mới mà quên đưa nó vào MỘT trong hai
        đường thì ca này KÊU — thay vì để phạm vi lặng lẽ trôi."""
        sl = _schema_sqlite()
        tat_ca = set()
        for f in glob.glob(os.path.join(DU_AN, "app", "*.py")):
            with open(f, encoding="utf-8") as fh:
                tat_ca |= set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?([a-z_0-9]+)",
                                         fh.read()))
        ngoai = sorted(tat_ca - set(sl))
        print("        %d bảng trong bộ DDL · %d bảng toàn bộ app/ · NGOÀI bộ DDL: %s"
              % (len(sl), len(tat_ca), ", ".join(ngoai)))
        self.assertEqual(ngoai, ["don_mat_hang", "han_muc_nhap_thang"],
                         "tập bảng NGOÀI bộ DDL 47 đã đổi: %s — cập nhật mục PHẠM VI của "
                         "docs/G17_POSTGRES.md trước khi sửa ca này" % ngoai)


# --------------------------------------- J. đo KHỐI mất-cập-nhật, có đối chứng cho đồng hồ
class J_DoiChieuMatCapNhat(unittest.TestCase):
    """PHÁT HIỆN LỚN, đo có ĐỐI CHỨNG: CÙNG khuôn đọc-rồi-ghi, nhiều TIẾN TRÌNH thật.

      · PostgreSQL 16.15 → **IM LẶNG MẤT**, không lượt nào báo lỗi
      · SQLite 3.51.0    → **TỪ CHỐI ỒN ÀO**, mất cập nhật = 0

    `E.test_e2/e3` là bản TẤT ĐỊNH (ép thứ tự, đúng một lượt mất). Lớp này là bản ĐO KHỐI:
    đếm số lượt CHỐT so với số THẬT trong CSDL, để câu "mất bao nhiêu phần trăm" có chỗ dựa.

    Và nó có HAI ĐỐI CHỨNG DƯƠNG cho chính cái đồng hồ đo — đúng hai khuôn ĐÚNG mà chỉ thị
    G17 nêu tên: cộng ở TẦNG CÂU (`gia_tri = gia_tri + 1`) và `SELECT … FOR UPDATE`. Cả hai
    PHẢI cho mất cập nhật = 0. Thiếu hai vế đó thì một đồng hồ luôn báo "mất" cũng "đạt".

    THAM SỐ ĐO (ghi ra vì con số chỉ có nghĩa kèm tham số): 4 TIẾN TRÌNH THẬT × 30 phép =
    120 lượt, trên MỘT hàng `g17_dem(id=1)`, qua socket Unix nội máy. Đo bằng tiến trình
    chứ không bằng thread: khoá ghi của Python chỉ phủ MỘT tiến trình, nên đo bằng thread là
    đo chính cái khoá đó rồi kết luận "an toàn" cho cả nó không phủ.
    """

    SO_TT = 4
    SO_PHEP = 30

    def _dat_lai(self):
        q("DROP TABLE IF EXISTS g17_dem;"
          " CREATE TABLE g17_dem (id int PRIMARY KEY, gia_tri int NOT NULL);"
          " INSERT INTO g17_dem VALUES (1,0);")

    def _tho_pg(self, kieu):
        mot = ("SELECT gia_tri AS v FROM g17_dem WHERE id=1 \\gset\n"
               "BEGIN;\nUPDATE g17_dem SET gia_tri = :v + 1 WHERE id=1;\nCOMMIT;\n"
               "\\echo COT_CHOT\n")
        if kieu == "nguyen_tu":
            mot = ("UPDATE g17_dem SET gia_tri = gia_tri + 1 WHERE id=1;\n\\echo COT_CHOT\n")
        elif kieu == "khoa_hang":
            # Khuôn ĐÚNG thứ hai: giữ khoá HÀNG bằng `FOR UPDATE` TRƯỚC khi đọc, nên lượt
            # đọc của tiến trình sau chỉ chạy khi tiến trình trước đã chốt.
            mot = ("BEGIN;\n"
                   "SELECT gia_tri AS v FROM g17_dem WHERE id=1 FOR UPDATE \\gset\n"
                   "UPDATE g17_dem SET gia_tri = :v + 1 WHERE id=1;\nCOMMIT;\n"
                   "\\echo COT_CHOT\n")
        return mot * self.SO_PHEP

    def _chay_pg(self, kieu):
        """Mỗi tiến trình = MỘT `psql`. Đếm số lượt CHỐT bằng dấu `\\echo COT_CHOT` in ra
        SAU `COMMIT` — không suy từ mã thoát, vì mã thoát không đếm được lượt."""
        self._dat_lai()
        ps = []
        for _ in range(self.SO_TT):
            p = subprocess.Popen(
                ["psql", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                 "-d", CSDL_THU, "-qtAX", "-v", "ON_ERROR_STOP=1"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            p.stdin.write(self._tho_pg(kieu))
            p.stdin.flush()
            ps.append(p)
        chot, loi = 0, []
        for p in ps:
            p.stdin.close()
            ma = p.wait(timeout=300)
            out, err = p.stdout.read(), p.stderr.read()
            p.stdout.close()
            p.stderr.close()
            chot += out.count("COT_CHOT")
            if ma:
                loi.append("psql thoát %d: %s" % (ma, err.strip()[-120:]))
        _, out, _ = q("SELECT gia_tri FROM g17_dem WHERE id=1")
        return chot, int(out.strip()), loi

    def test_j1_doi_chung_duong_cong_o_tang_cau(self):
        """ĐỒNG HỒ ĐO phải trả về 0 được — khuôn ĐÚNG thứ nhất: cộng ở TẦNG CÂU.
        `%d tiến trình × %d phép`, hàng `g17_dem(id=1)` → TIN == THẬT."""
        chot, that, loi = self._chay_pg("nguyen_tu")
        print("        cộng tầng câu : chốt=%d · thật=%d · mất=%d · lỗi=%d"
              % (chot, that, chot - that, len(loi)))
        self.assertEqual(loi, [], "có tiến trình lỗi: %s" % loi)
        self.assertEqual(chot, self.SO_TT * self.SO_PHEP, "không chốt đủ số lượt")
        self.assertEqual(that, chot, "cộng ở tầng câu mà vẫn mất cập nhật")

    def test_j2_postgres_mat_cap_nhat_im_lang(self):
        """VẾ CHÍNH: khuôn đọc-rồi-ghi ngây thơ trên PostgreSQL → CHỐT nhiều hơn THẬT, và
        KHÔNG một lượt nào báo lỗi. Mất cập nhật là kết cục IM LẶNG.

        THAM SỐ (`SO_TT` tiến trình THẬT × `SO_PHEP` phép = 120 lượt), trên MỘT hàng
        `g17_dem(id=1)`, socket Unix nội máy, cụm riêng. Tỉ lệ mất KHÔNG tất định — đo được
        43–71% giữa các lượt. Điều tất định, và là điều ca này khẳng định, là `mất > 0`
        cùng với `lỗi == 0`."""
        chot, that, loi = self._chay_pg("ngay_tho")
        mat = chot - that
        print("        đọc-rồi-ghi   : %d tiến trình × %d phép · chốt=%d · thật=%d · "
              "MẤT=%d (%.1f%%) · lỗi=%d"
              % (self.SO_TT, self.SO_PHEP, chot, that, mat,
                 100.0 * mat / chot if chot else 0, len(loi)))
        self.assertEqual(loi, [], "có lượt báo lỗi — lượt này KHÔNG còn là 'im lặng': %s" % loi)
        self.assertGreater(mat, 0,
                           "PostgreSQL KHÔNG mất cập nhật — hành vi đã đổi, đọc "
                           "docs/G17_POSTGRES.md trước khi sửa ca này")

    def test_j4_doi_chung_duong_khoa_hang_for_update(self):
        """ĐỒNG HỒ ĐO phải trả về 0 được — khuôn ĐÚNG thứ hai: `SELECT … FOR UPDATE`.

        Đây là vế mà chỉ thị G17 nêu đích danh. Nó quan trọng hơn `j1` ở một điểm: `j1` sửa
        được vì phép cộng nằm gọn trong MỘT câu; còn `FOR UPDATE` sửa được cả những chỗ
        LUẬT NGHIỆP VỤ nằm giữa lượt đọc và lượt ghi (đối soát, tính phí, trừ hạn mức) —
        những chỗ mà `x = x + 1` không thay thế được. Cùng tham số như j2."""
        chot, that, loi = self._chay_pg("khoa_hang")
        print("        FOR UPDATE    : chốt=%d · thật=%d · mất=%d · lỗi=%d"
              % (chot, that, chot - that, len(loi)))
        self.assertEqual(loi, [], "có tiến trình lỗi: %s" % loi)
        self.assertEqual(chot, self.SO_TT * self.SO_PHEP, "không chốt đủ số lượt")
        self.assertEqual(that, chot,
                         "giữ khoá HÀNG bằng FOR UPDATE mà vẫn mất cập nhật")

    def test_j3_sqlite_cung_khuon_thi_tu_choi(self):
        """VẾ ĐỐI CHỨNG: SQLite với CÙNG khuôn, CÙNG số tiến trình. Điều phải đúng ở đây
        là **số THẬT == số lượt CHỐT THÀNH CÔNG** — tức nó KHÔNG âm thầm mất. Lượt nào
        không chốt được thì nó BÁO LỖI (`database is locked`), không nuốt."""
        import sqlite3
        thu_muc = tempfile.mkdtemp(prefix="vhg17-j3-")
        duong = os.path.join(thu_muc, "j3.db")
        try:
            kn = sqlite3.connect(duong, isolation_level=None)
            kn.execute("PRAGMA journal_mode=WAL")
            kn.execute("CREATE TABLE g17_dem (id INTEGER PRIMARY KEY, gia_tri INTEGER NOT NULL)")
            kn.execute("INSERT INTO g17_dem VALUES (1,0)")
            kn.close()
            tho = (
                "import sqlite3, sys\n"
                "kn = sqlite3.connect(sys.argv[1], timeout=5.0, isolation_level=None)\n"
                "kn.execute('PRAGMA busy_timeout=2000')\n"
                "ok = 0; loi = 0\n"
                "for _ in range(int(sys.argv[2])):\n"
                "    try:\n"
                "        kn.execute('BEGIN')\n"
                "        cu = kn.execute('SELECT gia_tri FROM g17_dem WHERE id=1').fetchone()[0]\n"
                "        kn.execute('UPDATE g17_dem SET gia_tri=? WHERE id=1', (cu + 1,))\n"
                "        kn.execute('COMMIT'); ok += 1\n"
                "    except sqlite3.Error:\n"
                "        loi += 1\n"
                "        try: kn.execute('ROLLBACK')\n"
                "        except sqlite3.Error: pass\n"
                "print('KQ', ok, loi)\n")
            ps = [subprocess.Popen([sys.executable, "-c", tho, duong, str(self.SO_PHEP)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                  for _ in range(self.SO_TT)]
            ra = [p.communicate(timeout=300) for p in ps]
            self.assertEqual([p.returncode for p in ps], [0] * self.SO_TT,
                             "tiến trình SQLite thoát khác 0: %s" % str(ra)[:300])
            ok = loi = 0
            for out, _ in ra:
                for d in out.splitlines():
                    if d.startswith("KQ "):
                        _, a, b = d.split()
                        ok += int(a)
                        loi += int(b)
            kn = sqlite3.connect(duong)
            that = kn.execute("SELECT gia_tri FROM g17_dem WHERE id=1").fetchone()[0]
            kn.close()
            print("        SQLite        : chốt=%d · thật=%d · MẤT=%d · từ chối ồn ào=%d"
                  % (ok, that, ok - that, loi))
            self.assertEqual(that, ok,
                             "SQLite ÂM THẦM mất %d cập nhật — TRÁI số đo 15/10/2026; phải "
                             "đo lại trước khi tin" % (ok - that))
        finally:
            shutil.rmtree(thu_muc, ignore_errors=True)


# ----------------------------------------------------------- K. sao lưu / khôi phục
SEED_K = """
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
"""


def _chup_kho(db):
    """Chụp TRẠNG THÁI ĐO ĐƯỢC của một CSDL: số dòng TỪNG BẢNG, số CỘT, một TỔNG TIỀN,
    và md5 của một payload NHỊ PHÂN. Đếm bảng là chưa đủ — một bản khôi phục RỖNG cũng khớp
    số bảng."""
    _, dong, _ = CUM.psql(
        "SELECT string_agg(t||'='||n, ',' ORDER BY t) FROM ("
        " SELECT tablename t, (xpath('/row/c/text()', query_to_xml("
        "   format('SELECT count(*) c FROM %I', tablename), false, true, '')))[1]::text n"
        " FROM pg_tables WHERE schemaname='public') s;", db=db)
    _, cot, _ = CUM.psql("SELECT count(*) FROM information_schema.columns"
                         " WHERE table_schema='public'", db=db)
    _, tien, _ = CUM.psql("SELECT count(*)||'|'||coalesce(sum(so_tien_dong),0)"
                          " FROM tc_but_toan", db=db)
    _, bam, _ = CUM.psql("SELECT coalesce(md5(payload_tho),'(khong)') FROM wh_su_kien"
                         " WHERE event_id='ev1'", db=db)
    return {"so_dong_tung_bang": dong.strip(), "so_cot": cot.strip(),
            "but_toan": tien.strip(), "md5_payload": bam.strip()}


class K_SaoLuuKhoiPhuc(unittest.TestCase):
    """`pg_dump -Fc` → `pg_restore`: giữ SỐ DÒNG từng bảng, TỔNG TIỀN, payload NHỊ PHÂN.

    `§5` của `trien_khai/postgres/dien_tap_chuyen.py` đã làm việc này ở dạng script. Lớp
    này đưa nó vào bộ hồi quy — nơi nó được chạy MỖI LƯỢT — và thêm hai thứ mà bản script
    không có: `k2` chứng minh phép so LÀM ĐỎ ĐƯỢC, và `k3` chỉ ra vì sao không thể "khôi
    phục rồi sửa tiền cho khớp".
    """

    CSDL_GOC = "vh_g17_k_goc"
    CSDL_KP = "vh_g17_k_kp"
    _cap = None
    _goi = None

    @classmethod
    def setUpClass(cls):
        cls._goi = None
        _tao_csdl(cls.CSDL_GOC)
        rc, _, err = CUM.psql("BEGIN;\n" + DDL_PG + "\nCOMMIT;", db=cls.CSDL_GOC)
        if rc:
            raise AssertionError("nạp DDL vào %s hỏng: %s" % (cls.CSDL_GOC, err[-400:]))
        rc, _, err = CUM.psql(SEED_K, db=cls.CSDL_GOC)
        if rc:
            raise AssertionError("gieo dữ liệu vào %s hỏng: %s" % (cls.CSDL_GOC, err[-400:]))
        cls._goi = os.path.join(tempfile.mkdtemp(prefix="vhg17-k-"), "sao_luu.dump")
        p = subprocess.run(["pg_dump", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                            "-d", cls.CSDL_GOC, "-Fc", "-f", cls._goi],
                           capture_output=True, text=True)
        if p.returncode:
            raise AssertionError("pg_dump hỏng: %s" % p.stderr[-400:])
        _tao_csdl(cls.CSDL_KP)
        p = subprocess.run(["pg_restore", "-h", CUM.sock, "-p", str(CUM.cong), "-U", CUM.nguoi,
                            "-d", cls.CSDL_KP, "--no-owner", cls._goi],
                           capture_output=True, text=True)
        if p.returncode:
            raise AssertionError("pg_restore hỏng: %s" % p.stderr[-600:])
        cls._cap = (_chup_kho(cls.CSDL_GOC), _chup_kho(cls.CSDL_KP))

    @classmethod
    def tearDownClass(cls):
        _xoa_csdl(cls.CSDL_KP)
        _xoa_csdl(cls.CSDL_GOC)
        if cls._goi:
            shutil.rmtree(os.path.dirname(cls._goi), ignore_errors=True)

    def test_k1_khoi_phuc_giu_so_dong_va_tong_tien(self):
        goc, kp = self._cap
        so_bang = len(goc["so_dong_tung_bang"].split(","))
        print("        gốc      : %d bảng · cột=%s · bút toán=%s · md5=%s"
              % (so_bang, goc["so_cot"], goc["but_toan"], goc["md5_payload"][:12]))
        print("        khôi phục: %d bảng · cột=%s · bút toán=%s · md5=%s"
              % (len(kp["so_dong_tung_bang"].split(",")), kp["so_cot"], kp["but_toan"],
                 kp["md5_payload"][:12]))
        # CHỐT CHỐNG PHÉP ĐO RỖNG: hai chuỗi rỗng thì "bằng nhau" chẳng nói lên gì.
        self.assertGreaterEqual(so_bang, 40,
                                "phép đếm dòng rỗng/cụt — không chứng minh được gì")
        self.assertEqual(goc["but_toan"], "1|777000",
                         "dữ liệu gieo không đúng — phép đo TIỀN sẽ vô nghĩa")
        self.assertNotIn(goc["md5_payload"], ("", "(khong)"),
                         "không có payload NHỊ PHÂN để so")
        self.assertGreater(int(goc["so_cot"]), 400, "số cột quá ít — nhìn nhầm CSDL")
        self.assertEqual(goc, kp, "khôi phục LỆCH so với bản gốc")

    def test_k2_phep_so_lam_do_duoc(self):
        """TỰ KIỂM BỎ ĐỒ: sửa bản KHÔI PHỤC rồi đòi phép so PHẢI thấy khác. Không có ca
        này thì một `_chup_kho` luôn trả hằng số cũng "đạt" ở k1."""
        goc, kp = self._cap
        rc, _, err = CUM.psql("CREATE TABLE bang_them_vao (id int)", db=self.CSDL_KP)
        self.assertEqual(rc, 0, err[-200:])
        try:
            sau = _chup_kho(self.CSDL_KP)
            self.assertNotEqual(goc, sau,
                                "thêm một BẢNG vào bản khôi phục mà phép so KHÔNG thấy")
            self.assertNotEqual(goc["so_cot"], sau["so_cot"], "số CỘT không đổi dù thêm bảng")
        finally:
            CUM.psql("DROP TABLE bang_them_vao", db=self.CSDL_KP)
        # Và phép so TIỀN cũng phải nhạy: lệch đúng 1 đồng là phải thấy.
        gia = dict(kp, but_toan="1|777001")
        self.assertNotEqual(kp, gia, "phép so không nhìn tới trường TIỀN")
        # Và payload nhị phân: lệch một bit là phải thấy.
        gia2 = dict(kp, md5_payload="0" * 32)
        self.assertNotEqual(kp, gia2, "phép so không nhìn tới md5 payload")

    def test_k3_khong_the_khoi_phuc_roi_sua_tien_cho_khop(self):
        """Bút toán là BẤT BIẾN (§17) và bất biến đó đi qua được `pg_dump`/`pg_restore`.
        Nghĩa là nếu bản khôi phục lệch tiền thì KHÔNG có đường sửa lén — phải khôi phục lại.
        Đây là vế làm cho phép so TIỀN ở k1 có nghĩa."""
        rc, _, err = CUM.psql("UPDATE tc_but_toan SET so_tien_dong=1", db=self.CSDL_KP)
        self.assertNotEqual(rc, 0, "sửa được bút toán trên bản khôi phục — bất biến đã mất")
        rc, _, err = CUM.psql("DELETE FROM tc_but_toan", db=self.CSDL_KP)
        self.assertNotEqual(rc, 0, "xoá được bút toán trên bản khôi phục — bất biến đã mất")
        _, out, _ = q("SELECT 1")     # cụm thử còn sống
        self.assertEqual(out.strip(), "1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
