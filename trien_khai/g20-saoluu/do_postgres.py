#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — ĐO HÀNH VI `migrate.sao_luu()` KHI DỮ LIỆU NGHIỆP VỤ NẰM Ở POSTGRESQL.

====== CÂU HỎI (khoảng trống P-G15-02 đang mở) ======
`migrate.sao_luu()` được viết cho SQLite: nó `csdl.ket_noi()` rồi `nguon.backup(ban)`. Khi kho
đổi sang PostgreSQL thì hàm này làm gì? Ba khả năng, và phải ĐO mới biết cái nào đúng:
  (1) NÉM LỖI ỒN ÀO (tốt — người trực biết ngay không có đường lùi);
  (2) IM LẶNG KHÔNG LÀM GÌ (xấu nhất — có "đường lùi" GIẢ);
  (3) LÀM ĐÚNG (không thể, vì không có nhánh PostgreSQL nào trong mã).

====== PHẠM VI VÀ CHỐT AN TOÀN ======
* Dùng CỤM RIÊNG do bộ đo tự dựng (socket Unix, `listen_addresses=''`, KHÔNG mở cổng TCP).
  `_kiem_cong_an_toan` TỪ CHỐI cổng 5432 — cụm hệ thống đang giữ `vip_customs*`.
* KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL (D-8). Đây là một phép ĐO trên cụm thử.
* KHÔNG sửa `app/csdl.py` hay `app/migrate.py`.
* Vân tay cụm :5432 được chụp TRƯỚC và SAU để chứng minh lượt đo không đụng vào nó.

====== NGOÀI PHẠM VI (đã có người làm, KHÔNG làm lại) ======
`app/thu/thu_postgres.py` lớp K đã đo `pg_dump -Fc` → `pg_restore` (đường ĐÚNG của PostgreSQL,
ở tầng công cụ). Bộ đo này KHÔNG đo lại việc đó. Nó đo đúng một chỗ lớp K không đo: HÀM SẢN
PHẨM `migrate.sao_luu()`.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
sys.path.insert(0, DAY)
APP = os.environ.get("G21_APP_DIR") or os.path.join(GOC, "app")
sys.path.insert(0, APP)
sys.path.insert(0, os.path.join(GOC, "app", "thu"))
sys.path.insert(0, os.path.join(GOC, "trien_khai", "postgres"))

import khung_do  # noqa: E402
import kich_ban  # noqa: E402

CSDL_GOC = "vh_g20_ag04_goc"
CONG_CAM = "5432"

# Dữ liệu nghiệp vụ gieo vào PostgreSQL. CỐ Ý có TIỀN và nhiều tenant: một phép đo "bản sao
# lưu rỗng" chỉ có nghĩa khi bản gốc KHÔNG rỗng.
SEED_PG = """
INSERT INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,han_muc_ai_thang,so_nhan_vien,
  so_tai_khoan_hang) VALUES ('basic','Cơ bản',299000,1000,500,5,3) ON CONFLICT (id) DO NOTHING;
INSERT INTO tenants (id,code,ten,goi_id,tao_luc) VALUES
  (1,'pg-a','Shop PG A','basic','2026-10-16'), (2,'pg-b','Shop PG B','basic','2026-10-16')
  ON CONFLICT (id) DO NOTHING;
INSERT INTO users (id,ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc) VALUES
  (1,'pg-owner','x','Chủ PG','2026-10-16') ON CONFLICT (id) DO NOTHING;
INSERT INTO carrier_providers (ma,ten,capabilities_json,live_mo,cap_nhat_luc)
  VALUES ('vtp','VTP','{}',0,'2026-10-16') ON CONFLICT (ma) DO NOTHING;
INSERT INTO carrier_accounts (id,tenant_id,hang,ten,moi_truong,credentials_ma_hoa,
  credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)
  VALUES (1,1,'vtp','TK VTP','mock','v3$k$n$c','abcd','wh-pg','v3$k$n$c','2026-10-16')
  ON CONFLICT (id) DO NOTHING;
INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,nguoi_gui_dia_chi,
  nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,khoi_luong_gram,cod,gia_tri_khai,
  nguoi_tao,tao_luc,cap_nhat_luc)
  SELECT (g % 2) + 1, 'PG-' || g, 'a','0','x','b','0','y','h', 100, g * 111000, g * 222000,
         1, '2026-10-16', '2026-10-16' FROM generate_series(1,6) g;
INSERT INTO tc_but_toan (tenant_id,loai,so_tien_dong,chieu,nguon,can_cu,tao_luc)
  SELECT (g % 2) + 1, 'cod', g * 111000, 'ghi_no', 'hang', 'thu COD PG ' || g, '2026-10-16'
  FROM generate_series(1,6) g;
INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,nhan_luc)
  SELECT 1, 'ev-pg-' || g, decode('00ff10ab5c7e','hex'), '{}', '2026-10-16'
  FROM generate_series(1,4) g;
"""

# Bảng + cột tiền để chụp phía PostgreSQL — CÙNG danh sách với `khung_do.COT_TIEN`, để hai vế
# của phép so nói cùng một ngôn ngữ.
BANG_PG = ("don_hang", "tc_but_toan", "tc_cod", "tenants", "users", "wh_su_kien")


def _chup_pg(cum, ten_csdl):
    """Chụp phía PostgreSQL: số dòng từng bảng + tổng tiền từng cột tiền."""
    ra = {"csdl": ten_csdl, "bang": {}, "tong_tien": 0}
    for b in BANG_PG:
        rc, out, err = cum.psql(
            "SELECT count(*) FROM %s" % b, db=ten_csdl, dung_lai_khi_loi=False)
        d = {"dong": out.strip() if rc == 0 else "loi: %s" % err[-120:], "tien": {}}
        ra["bang"][b] = d
    for b, cot in (("don_hang", "cod"), ("don_hang", "gia_tri_khai"), ("tc_but_toan", "so_tien_dong")):
        rc, out, err = cum.psql("SELECT coalesce(sum(%s),0) FROM %s" % (cot, b), db=ten_csdl,
                                dung_lai_khi_loi=False)
        v = int(out.strip()) if rc == 0 and out.strip().lstrip("-").isdigit() else None
        ra["bang"][b]["tien"][cot] = v
        if v:
            ra["tong_tien"] += v
    return ra


def _chup_sqlite_bang(duong):
    """Chụp bản sao lưu SQLite bằng ĐÚNG khung đo của lượt đo SQLite — cùng thước, cùng đơn vị."""
    return khung_do.chup(duong)


def chay(giu_lai=False):
    """Trả một dict kết quả. Không ném khi thiếu công cụ — trả `bo_qua` kèm LÝ DO."""
    ra = {"ten": "9. PostgreSQL: `sao_luu()` làm gì khi dữ liệu nằm ở PostgreSQL",
          "cong": None, "bo_qua": None}
    import thu_postgres
    if str(os.environ.get("VHPG_CONG", "55432")) == CONG_CAM:
        ra["bo_qua"] = "TỪ CHỐI: cổng 5432 là cụm hệ thống (giữ vip_customs*)."
        return ra
    ly_do = thu_postgres._thieu_gi()
    if ly_do:
        ra["bo_qua"] = "thiếu điều kiện chạy: " + ly_do
        return ra

    import van_tay_cum
    vt_truoc = van_tay_cum.chup(CONG_CAM)
    cum = thu_postgres.Cum()
    ra["cong"] = cum.cong
    ra["tu_dung_cum"] = cum.tu_dung
    nen = tempfile.mkdtemp(prefix="g20-pg-")
    try:
        cum.dung()
        rc, out, err = cum.psql("SELECT 1")
        if rc:
            ra["bo_qua"] = "cụm dựng xong nhưng không truy vấn được: " + err[-200:]
            return ra
        ra["rc_select_1"] = rc

        # ---- dựng CSDL PostgreSQL có DỮ LIỆU THẬT, dùng DDL SINH TỪ SCHEMA CỦA DỰ ÁN ----
        import sinh_ddl_pg
        ddl, thong_ke = sinh_ddl_pg.sinh()
        ra["ddl_so_cau"] = thong_ke if isinstance(thong_ke, int) else str(thong_ke)[:120]
        cum.psql("DROP DATABASE IF EXISTS %s" % CSDL_GOC)
        rc, out, err = cum.psql("CREATE DATABASE %s" % CSDL_GOC)
        ra["rc_tao_csdl"] = rc
        if rc:
            ra["bo_qua"] = "không tạo được CSDL thử: " + err[-200:]
            return ra
        rc, out, err = cum.psql("BEGIN;\n" + ddl + "\nCOMMIT;", db=CSDL_GOC)
        ra["rc_nap_ddl"] = rc
        if rc:
            ra["loi_nap_ddl"] = err[-400:]
            return ra
        rc, out, err = cum.psql(SEED_PG, db=CSDL_GOC)
        ra["rc_gieo"] = rc
        ra["loi_gieo"] = err[-300:]
        pg_truoc = _chup_pg(cum, CSDL_GOC)
        ra["pg_truoc"] = pg_truoc

        # ---- ĐO 1: `sao_luu()` khi `hub.db` CHƯA HỀ TỒN TẠI ----
        # Đây là trạng thái thật của một máy chủ đã chuyển kho sang PostgreSQL: thư mục dữ
        # liệu không còn `hub.db` nữa.
        D1 = os.path.join(nen, "D1")
        os.makedirs(D1, exist_ok=True)
        sl1 = kich_ban.sao_luu(D1)
        ra["do1_hub_db_khong_ton_tai"] = {
            "rc": sl1["rc"], "duong": sl1["duong"], "stderr": sl1["err"][-300:],
            "hub_db_sinh_ra": os.path.exists(os.path.join(D1, "hub.db")),
            "co_ban_sao": os.path.getsize(sl1["duong"]) if sl1["duong"] else None,
        }
        if sl1["duong"]:
            c1 = _chup_sqlite_bang(sl1["duong"])
            ra["do1_hub_db_khong_ton_tai"].update({
                "so_bang": c1.get("so_bang"), "tong_tien": c1.get("tong_tien_toan_kho"),
                "integrity": c1.get("integrity_check"), "loi": c1.get("loi"),
                "co_bang_don_hang": "don_hang" in (c1.get("bang") or {}),
                "dong_don_hang": ((c1.get("bang") or {}).get("don_hang") or {}).get("dong"),
                "dong_tc_but_toan": ((c1.get("bang") or {}).get("tc_but_toan") or {}).get("dong"),
            })

        # ---- ĐO 2: `sao_luu()` khi `hub.db` CÓ dữ liệu SQLite CŨ (khác dữ liệu PG) ----
        D2 = os.path.join(nen, "D2")
        os.makedirs(D2, exist_ok=True)
        rc_gieo2, _, err_gieo2 = kich_ban.gieo(D2)
        truoc2 = khung_do.chup(kich_ban.db(D2))
        sl2 = kich_ban.sao_luu(D2)
        c2 = _chup_sqlite_bang(sl2["duong"]) if sl2["duong"] else {}
        ra["do2_hub_db_co_du_lieu_sqlite_khac"] = {
            "rc_gieo_sqlite": rc_gieo2, "loi_gieo": err_gieo2[-200:],
            "rc": sl2["rc"], "co_ban_sao": os.path.getsize(sl2["duong"]) if sl2["duong"] else None,
            "sqlite_truoc_so_bang": truoc2.get("so_bang"),
            "sqlite_truoc_tong_tien": truoc2.get("tong_tien_toan_kho"),
            "ban_sao_so_bang": c2.get("so_bang"), "ban_sao_tong_tien": c2.get("tong_tien_toan_kho"),
            "bam_ban_sao_khop_sqlite_goc": c2.get("bam_toan_kho") == truoc2.get("bam_toan_kho"),
        }

        # ---- ĐO 3: `khoi_phuc()` với một tệp `pg_dump -Fc` THẬT ----
        # Đây là nhầm lẫn vận hành thật: cùng thư mục có hai loại tệp sao lưu, gõ nhầm một cái.
        goi = os.path.join(nen, "pg-that.dump")
        p = subprocess.run(["pg_dump", "-h", cum.sock, "-p", str(cum.cong), "-U", cum.nguoi,
                            "-d", CSDL_GOC, "-Fc", "-f", goi], capture_output=True, text=True)
        ra["pg_dump"] = {"rc": p.returncode, "co_byte": os.path.getsize(goi) if os.path.exists(goi) else None,
                         "stderr": p.stderr[-200:]}
        D3 = os.path.join(nen, "D3")
        os.makedirs(D3, exist_ok=True)
        rc_gieo3, _, _ = kich_ban.gieo(D3)
        truoc3 = khung_do.chup(kich_ban.db(D3))
        kp = kich_ban.khoi_phuc(D3, goi)
        sau3 = khung_do.chup(kich_ban.db(D3))
        ra["do3_khoi_phuc_tu_pg_dump"] = {
            "rc_gieo_sqlite": rc_gieo3, "rc_khoi_phuc": kp["rc"], "err": kp["err"][-200:],
            "out": kp["out"][-250:],
            "khoi_phuc_NHAN": kp["rc"] == 0,
            "csdl_sau_so_byte": sau3.get("so_byte"), "csdl_sau_loi": sau3.get("loi"),
            "csdl_sau_so_bang": sau3.get("so_bang"),
            "sqlite_truoc_tong_tien": truoc3.get("tong_tien_toan_kho"),
        }

        # ---- ĐỐI CHỨNG ĐƯỜNG ----
        # Cùng hàm `sao_luu()`, nhưng kho là SQLite CÓ dữ liệu: bản sao phải chứa dữ liệu thật.
        # Có vế này thì kết luận mới là "hàm không có nhánh PostgreSQL", KHÔNG phải
        # "hàm hỏng" — hai câu đó khác nhau và chỉ phép đo này phân biệt được.
        D4 = os.path.join(nen, "D4")
        os.makedirs(D4, exist_ok=True)
        rc_gieo4, _, _ = kich_ban.gieo(D4)
        truoc4 = khung_do.chup(kich_ban.db(D4))
        sl4 = kich_ban.sao_luu(D4)
        c4 = _chup_sqlite_bang(sl4["duong"]) if sl4["duong"] else {}
        ra["doi_chung_duong_sqlite_co_du_lieu"] = {
            "rc_gieo": rc_gieo4, "rc": sl4["rc"],
            "so_bang": c4.get("so_bang"), "tong_tien": c4.get("tong_tien_toan_kho"),
            "bam_khop_goc": c4.get("bam_toan_kho") == truoc4.get("bam_toan_kho"),
        }

        # ---- Kết luận ba khả năng ----
        d1 = ra["do1_hub_db_khong_ton_tai"]
        d2 = ra["do2_hub_db_co_du_lieu_sqlite_khac"]
        ra["ket_luan"] = {
            "nem_loi_chi_tiet": d1["rc"] != 0,
            "im_lang_bao_thanh_cong": d1["rc"] == 0,
            "ban_sao_chua_du_lieu_pg": (
                d1.get("dong_don_hang") in (0, None) and d1.get("dong_tc_but_toan") in (0, None)),
            "du_lieu_pg_that": {"dong_don_hang": pg_truoc["bang"]["don_hang"]["dong"],
                                "dong_tc_but_toan": pg_truoc["bang"]["tc_but_toan"]["dong"],
                                "tong_tien": pg_truoc["tong_tien"]},
        }
        return ra
    finally:
        cum.psql("DROP DATABASE IF EXISTS %s" % CSDL_GOC, dung_lai_khi_loi=False)
        cum.dong()
        ra["van_tay_cum_5432"] = {"truoc": vt_truoc, "sau": van_tay_cum.chup(CONG_CAM)}
        # `van_tay_cum.so_sanh` trả BỘ ĐÔI `(giống_nhau, danh_sách_lệch)` — không phải danh
        # sách. So với `[]` thì lúc nào cũng sai; lấy phần tử [0] và in cả phần lệch ra.
        giong, lech_vt = van_tay_cum.so_sanh(vt_truoc, ra["van_tay_cum_5432"]["sau"])
        ra["van_tay_5432_khong_doi"] = giong
        ra["van_tay_5432_lech"] = lech_vt
        # `dat` = KỊCH BẢN ĐO chạy được, KHÔNG phải "sản phẩm đúng". Phán về sản phẩm nằm ở
        # `ket_luan`. Đặt ở ĐÂY (trong `finally`) chứ không trong `try`: vân tay cụm :5432 chỉ
        # có sau khi dọn, và điều kiện "không đụng cụm hệ thống" là một phần của "đo được".
        ra["dat"] = bool(ra.get("rc_select_1") == 0 and ra.get("rc_tao_csdl") == 0
                         and ra.get("rc_nap_ddl") == 0 and ra.get("rc_gieo") == 0
                         and (ra.get("pg_dump") or {}).get("rc") == 0
                         and (ra.get("doi_chung_duong_sqlite_co_du_lieu") or {}).get("bam_khop_goc") is True
                         and giong is True)
        if giu_lai:
            ra["nen"] = nen
        else:
            shutil.rmtree(nen, ignore_errors=True)


if __name__ == "__main__":
    k = chay(giu_lai="--giu-lai" in sys.argv)
    print(json.dumps(k, ensure_ascii=False, indent=2, default=str))
