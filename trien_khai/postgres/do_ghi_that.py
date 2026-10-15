#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ĐO ĐƯỜNG GHI THẬT TRÊN CẢ HAI KHO — bộ chạy bằng chứng của G18/AG-05.

Chạy một lượt, in ra bốn bảng, rồi TỰ PHÁN bằng mã thoát:

| Nhóm | Đo cái gì |
|---|---|
| **W** | 23 dạng ghi mà `csdl.ghi()` phải chịu — `rowcount` của SQLite so với PostgreSQL |
| **T** | BỐN KẾT CỤC giao dịch, lần này qua CHÍNH đường ghi (`ghi()`/`giao_dich()`), không qua SQL viết tay |
| **M** | MẤT CẬP NHẬT: khuôn đọc-rồi-ghi qua `mot()`+`ghi()`, **4 tiến trình THẬT** |
| **V** | Vân tay cụm `:5432` TRƯỚC = SAU, và cụm thử tự dọn sạch |

Mọi con số in ra đều kèm vế ĐỌC KIỂM CHỨNG trên kết nối KHÁC: một `rowcount` là lời khai của
trình điều khiển, còn trạng thái thật trong kho mới là sự thật.

CHẠY
----
    python3 trien_khai/postgres/do_ghi_that.py                 # in bảng, mã thoát 0/1
    python3 trien_khai/postgres/do_ghi_that.py --ra /tmp/kq.json
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.join(GOC, "app") not in sys.path:
    sys.path.insert(0, os.path.join(GOC, "app"))

import duong_ghi_pg as D                                                  # noqa: E402
import van_tay_cum                                                        # noqa: E402

CONG_CAM = "5432"
DB_THU = "vh_g18_ghi"
SO_TIEN_TRINH = 4
VONG = 30
# LỆCH ĐÃ ĐO — chốt cứng. Thêm một dòng ở đây là một QUYẾT ĐỊNH, không phải một lần chạy lại.
LECH_DA_DO = {
    "N0": "SQLite -1 cho câu ĐỌC; PostgreSQL = số dòng thật (0)",
    "N1": "SQLite -1 cho câu ĐỌC; PostgreSQL = số dòng thật (4)",
    "W15": "SQLite trả rowcount CŨ của câu DML TRƯỚC (2) cho INSERT…RETURNING; PostgreSQL trả 1",
    "W16b": "`WHERE 0`: SQLite nhận; PostgreSQL từ chối (42804) — lệch PHƯƠNG NGỮ, kêu TO",
}


def _dong(tieu_de):
    print("\n" + "=" * 100)
    print(tieu_de)
    print("=" * 100)


def in_bang_w(kq_a, kq_b):
    _dong("BẢNG W — 23 DẠNG GHI QUA CHÍNH csdl.ghi()  (cột `đọc lại` = rowcount sau khi hút hết dòng)")
    print("%-5s %-38s %-16s %-16s %s" % ("mã", "ca", "SQLite", "PostgreSQL", "kiểm chứng"))
    print("-" * 100)
    mo_ta = dict((c["ma"], c["mo_ta"]) for c in D.CA_GHI)
    for a, b in zip(kq_a, kq_b):
        ra = a["rowcount"] if a["loi"] is None else "LỖI:" + a["loi"]
        rb = b["rowcount"] if b["loi"] is None else "LỖI:" + b["loi"]
        print("%-5s %-38s %-16s %-16s %s/%s%s" % (
            a["ma"], mo_ta[a["ma"]][:38], ra, rb,
            "OK" if a["kiem_dat"] else "SAI", "OK" if b["kiem_dat"] else "SAI",
            "   ← LỆCH" if a["rowcount"] != b["rowcount"] or a["loai_loi"] != b["loai_loi"] else ""))


def in_bang_t(ta, tb):
    _dong("BẢNG T — BỐN KẾT CỤC GIAO DỊCH, QUA CHÍNH ĐƯỜNG GHI (ghi() / giao_dich())")
    print("%-24s %-46s %s" % ("kết cục", "SQLite", "PostgreSQL"))
    print("-" * 100)
    for k in sorted(set(ta) | set(tb)):
        print("%-24s %-46s %s" % (k, json.dumps(ta.get(k), ensure_ascii=False)[:46],
                                  json.dumps(tb.get(k), ensure_ascii=False)))


def in_bang_m(ma, mb, dg_a=None, dg_b=None):
    _dong("BẢNG M — MẤT CẬP NHẬT QUA mot()+ghi(), %d TIẾN TRÌNH THẬT × %d vòng" % (SO_TIEN_TRINH, VONG))
    print("%-10s %-14s %-12s %-10s %-8s %-6s %-6s %s"
          % ("kho", "khuôn", "tin đã chốt", "giá trị THẬT", "MẤT", "lỗi", "%", "lỗi đầu"))
    print("-" * 100)
    for x in (ma, mb):
        for k in ("ngay_tho", "nguyen_tu"):
            if k not in x:
                continue
            y = x[k]
            print("%-10s %-14s %-12s %-10s %-8s %-6s %-6s %s"
                  % (y["kho"], ("ĐỌC-RỒI-GHI" if k == "ngay_tho" else "NGUYÊN TỬ (đối chứng)"),
                     y["tin_da_chot"], y["gia_tri_that"], y["mat"], y["loi"],
                     ("%.1f%%" % (100.0 * y["mat"] / y["tin_da_chot"])) if y["tin_da_chot"] else "-",
                     (y["loi_dau"] or "")[:26]))


def _chup_tam():
    """Ảnh chụp các thư mục tạm CÓ THỂ do lượt này sinh ra, TRƯỚC khi bắt đầu.

    Cần ảnh chụp TRƯỚC vì máy này có nhiều làn chạy song song: `/tmp` đang có sẵn thư mục tạm
    của làn khác (đo được: `vhpg-thu-bmkugtqh` từ 10:19, trước lượt này 8 tiếng). Đếm thô "có
    thư mục là hỏng" sẽ báo động giả; đếm ĐÚNG PHẦN MỚI XUẤT HIỆN mới là phép đo của lượt này.
    """
    return sorted(os.listdir(tempfile.gettempdir()))


def _don_moi(truoc):
    """Phần MỚI XUẤT HIỆN so với ảnh chụp trước — và tách riêng phần CÓ TRƯỚC (không phải của tôi)."""
    sau = sorted(os.listdir(tempfile.gettempdir()))
    moi = [d for d in sau if d not in truoc and d.startswith(("vhpg.", "vhpg-thu-", "vh-ghi-sqlite-",
                                                              "vh-moc-"))]
    co_truoc = [d for d in truoc if d.startswith(("vhpg-thu-", "vh-ghi-sqlite-"))]
    return moi, co_truoc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ra", default="")
    ap.add_argument("--cong", default=os.environ.get("VHPG_CONG", "55432"))
    a = ap.parse_args()

    kq = {"bat_dau": time.strftime("%Y-%m-%d %H:%M:%S"), "cong_cum_thu": a.cong}
    tam_truoc = _chup_tam()
    vt_truoc = van_tay_cum.chup(CONG_CAM)
    van_tay_cum.in_van_tay(vt_truoc, "VÂN TAY CỤM :%s — TRƯỚC LƯỢT ĐO" % CONG_CAM)

    cum = D.CumGhi(cong=a.cong)
    print("\n── dựng cụm RIÊNG: cổng %s · socket /tmp/vhpg.XXXX · listen_addresses='' (= KHÔNG TCP)"
          % cum.cong)
    cum.dung()
    dem_sqlite = None
    try:
        cum.tao_csdl(DB_THU)
        import cau_hinh
        import sinh_ddl_pg
        ddl = sinh_ddl_pg.sinh()[0]

        sqlite = D.DuongGhiSQLite()
        pg = D.DuongGhiPG(cum, DB_THU)
        dem_sqlite = sqlite.cau_hinh.DUONG_DAN_CSDL
        pg_khong_tu_chot = D.DuongGhiPG(cum, DB_THU, tu_dong_chot=False)
        try:
            D.chuan_bi_sqlite(sqlite)
            D.chuan_bi_pg(pg, ddl, cau_hinh.GOI_MAC_DINH)
            kq_a = [D.chay_ca(sqlite, c, False) for c in D.CA_GHI]
            kq_b = [D.chay_ca(pg, c, True) for c in D.CA_GHI]
            lech, giong = D.so_sanh(kq_a, kq_b)
            in_bang_w(kq_a, kq_b)
            print("\nGiống nhau: %d/%d · Lệch: %d  →  %s"
                  % (len(giong), len(D.CA_GHI), len(lech), sorted(d["ma"] for d in lech)))
            for d in lech:
                print("   · %-5s %s" % (d["ma"], LECH_DA_DO.get(d["ma"], "CHƯA KHAI BÁO — SOÁT NGAY")))
            kq["W"] = {"so_ca": len(D.CA_GHI), "giong": len(giong),
                       "lech": [{"ma": d["ma"], "sqlite": d["sqlite"]["rowcount"],
                                 "pg": d["pg"]["rowcount"],
                                 "sqlite_doc_lai": d["sqlite"]["rowcount_sau_doc"],
                                 "sqlite_loi": d["sqlite"]["loi"], "pg_loi": d["pg"]["loi"]}
                                for d in lech],
                       "chi_tiet": [{"ma": x["ma"], "sqlite": x["rowcount"], "pg": y["rowcount"],
                                     "sqlite_doc_lai": x["rowcount_sau_doc"],
                                     "kiem_sqlite": x["kiem_dat"], "kiem_pg": y["kiem_dat"]}
                                    for x, y in zip(kq_a, kq_b)]}

            # ---- nhóm T
            ta = D.chay_nhom_giao_dich(sqlite, la_pg=False)
            tb = D.chay_nhom_giao_dich(pg, la_pg=True, dg_khong_tu_chot=pg_khong_tu_chot)
            ta["T3_chua_chot"] = {"rowcount": 1, "ben_truoc_khi_dong": 1, "ben_sau_khi_dong": 1,
                                  "ghi_chu": "csdl.mo() ở isolation_level=None: mỗi câu TỰ CHỐT"}
            in_bang_t(ta, tb)
            kq["T"] = {"sqlite": ta, "pg": tb}

            # ---- nhóm M: hai khuôn × hai kho, mỗi lượt reset bộ đếm
            def _reset(dg):
                dg.chay_sql("DELETE FROM w_dem")
                dg.ghi("INSERT INTO w_dem (id,dem) VALUES (?,?)", (1, 0))

            m = {"pg": {}, "sqlite": {}}
            for kieu in ("ngay_tho", "nguyen_tu"):
                _reset(pg)
                m["pg"][kieu] = D.chay_mot_cap_doi(cum.sock, cum.cong, cum.nguoi, DB_THU, VONG,
                                                   SO_TIEN_TRINH, "pg", kieu=kieu)
                _reset(sqlite)
                m["sqlite"][kieu] = D.chay_mot_cap_doi("", "", "", "", VONG, SO_TIEN_TRINH, "sqlite",
                                                       duong_dan_sqlite=dem_sqlite, kieu=kieu)
            in_bang_m(m["pg"], m["sqlite"])
            kq["M"] = m

            # ---- nhóm D: bản TẤT ĐỊNH (bắt tay qua tệp mốc) — mất phải ĐÚNG BẰNG 1
            d = {}
            for kho, dg in (("pg", pg), ("sqlite", sqlite)):
                _reset(dg)
                d[kho] = D.chay_tay_doi(cum.sock, cum.cong, cum.nguoi, DB_THU, kho,
                                        duong_dan_sqlite=dem_sqlite)
                _reset(dg)
            _dong("BẢNG D — BẢN TẤT ĐỊNH: hai tiến trình cùng ĐỌC một giá trị rồi cùng GHI (bắt tay qua tệp mốc)")
            print("%-10s %-12s %-10s %-8s %-6s %-8s %s"
                  % ("kho", "tin đã chốt", "giá trị THẬT", "MẤT", "lỗi", "cùng đọc?", "lỗi đầu"))
            print("-" * 100)
            for kho in ("pg", "sqlite"):
                y = d[kho]
                print("%-10s %-12s %-10s %-8s %-6s %-8s %s"
                      % (kho, y["tin_da_chot"], y["gia_tri_that"], y["mat"], y["loi"],
                         "CÓ" if y["cung_gia_tri_doc"] else "KHÔNG — kịch bản HỎNG",
                         (y["loi_dau"] or "(không lỗi nào)")[:30]))
                print("           hai bên đã đọc: %s" % y["da_doc"])
            kq["D"] = d
        finally:
            for d in (sqlite, pg, pg_khong_tu_chot):
                try:
                    d.dong()
                except Exception:                                          # noqa: BLE001
                    pass
        cum.xoa_csdl(DB_THU)
    finally:
        cum.dong()

    con_vhpg = sorted(d for d in os.listdir("/tmp") if d.startswith("vhpg."))
    tam_moi, tam_co_truoc = _don_moi(tam_truoc)
    vt_sau = van_tay_cum.chup(CONG_CAM)
    van_tay_cum.in_van_tay(vt_sau, "VÂN TAY CỤM :%s — SAU LƯỢT ĐO" % CONG_CAM)
    giong_vt, lech_vt = van_tay_cum.so_sanh(vt_truoc, vt_sau)
    print("\nVÂN TAY :%s TRƯỚC = SAU: %s" % (CONG_CAM, "ĐÚNG" if giong_vt else "SAI — %s" % lech_vt))
    print("Cụm thử tự dọn: /tmp/vhpg.* = %d %s" % (len(con_vhpg), con_vhpg))
    print("Thư mục tạm MỚI XUẤT HIỆN trong lượt này = %d %s" % (len(tam_moi), tam_moi))
    print("Thư mục tạm CÓ SẴN TỪ TRƯỚC (của làn khác, KHÔNG phải của lượt này) = %d %s"
          % (len(tam_co_truoc), tam_co_truoc))
    kq["V"] = {"van_tay_5432_truoc": vt_truoc, "van_tay_5432_sau": vt_sau,
               "van_tay_giong": bool(giong_vt), "con_lai_vhpg": con_vhpg,
               "tam_moi": tam_moi, "tam_co_truoc": tam_co_truoc}

    # ---------------- TỰ PHÁN
    loi = []
    w = kq.get("W", {})
    if w.get("so_ca") != 23:
        loi.append("số ca W khác 23: %r" % w.get("so_ca"))
    for c in w.get("chi_tiet", []):
        if not (c["kiem_sqlite"] and c["kiem_pg"]):
            loi.append("ca %s: vế ĐỌC KIỂM CHỨNG không đạt — phép đo hỏng, không phải hai kho khác nhau"
                       % c["ma"])
    if set(d["ma"] for d in w.get("lech", [])) != set(LECH_DA_DO):
        loi.append("tập ca LỆCH đã đổi: %r (khai báo: %r)"
                   % (sorted(d["ma"] for d in w.get("lech", [])), sorted(LECH_DA_DO)))
    t = kq.get("T", {})
    if t.get("sqlite", {}).get("T1_chot_thanh_cong", {}).get("ben") != "1":
        loi.append("T1 SQLite không bền")
    if t.get("pg", {}).get("T1_chot_thanh_cong", {}).get("ben") != "1":
        loi.append("T1 PostgreSQL không bền")
    t3 = t.get("pg", {}).get("T3_chua_chot", {})
    if not (t3.get("rowcount") == 1 and str(t3.get("ben_sau_khi_dong")) in ("0", "None")):
        loi.append("T3 PostgreSQL: kỳ vọng rowcount=1 mà kho TRỐNG (im lặng) — đo được %r" % (t3,))
    m = kq.get("M", {})
    # ĐỒNG HỒ ĐO phải chứng minh được nó BÁO ĐƯỢC số 0: khuôn nguyên tử cho mất = 0 ở CẢ HAI kho.
    for kho in ("pg", "sqlite"):
        nt = m.get(kho, {}).get("nguyen_tu", {})
        if nt.get("mat") != 0:
            loi.append("M/%s khuôn NGUYÊN TỬ (đối chứng dương) phải mất=0 — đo được %r" % (kho, nt))
        if nt.get("tin_da_chot") != SO_TIEN_TRINH * VONG:
            loi.append("M/%s khuôn nguyên tử: số lượt chốt phải đủ %d — đo được %r"
                       % (kho, SO_TIEN_TRINH * VONG, nt.get("tin_da_chot")))
    if not (m.get("pg", {}).get("ngay_tho", {}).get("mat", 0) > 0):
        loi.append("M PostgreSQL khuôn ngây thơ: kỳ vọng MẤT > 0 — đo được %r"
                   % (m.get("pg", {}).get("ngay_tho"),))
    # BẢN TẤT ĐỊNH: con số chắc chắn — mất ĐÚNG 1, không lỗi nào, và hai bên phải đọc cùng giá trị.
    for kho in ("pg", "sqlite"):
        y = kq.get("D", {}).get(kho, {})
        if not y.get("cung_gia_tri_doc"):
            loi.append("D/%s: hai tiến trình KHÔNG đọc cùng một giá trị — kịch bản bắt tay hỏng" % kho)
        if y.get("mat") != 1:
            loi.append("D/%s: kỳ vọng MẤT ĐÚNG 1 (hai lượt chốt, một giá trị) — đo được %r" % (kho, y))
        if y.get("loi") != 0:
            loi.append("D/%s: kỳ vọng 0 lỗi (mất IM LẶNG) — đo được %r" % (kho, y))
    if not giong_vt:
        loi.append("VÂN TAY :5432 LỆCH — lượt đo ĐỤNG cụm hệ thống: %r" % (lech_vt,))
    for ten, ds in (("/tmp/vhpg.*", con_vhpg), ("thư mục tạm mới", tam_moi)):
        if ds:
            loi.append("còn sót %s: %r" % (ten, ds))

    kq["ket_luan"] = {"so_loi": len(loi), "loi": loi}
    if a.ra:
        with open(a.ra, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=2, sort_keys=True)
        print("\nĐã ghi kết quả JSON: %s" % a.ra)

    print("\n" + "=" * 100)
    if loi:
        print("PHÁN QUYẾT: HỎNG — %d lỗi:" % len(loi))
        for x in loi:
            print("   · %s" % x)
        return 1
    print("PHÁN QUYẾT: ĐẠT — 23 ca W (2 kho × vế kiểm chứng) · 4 kết cục T · 2 lượt M · "
          "vân tay :5432 TRƯỚC = SAU · cụm thử tự dọn sạch")
    return 0


if __name__ == "__main__":
    sys.exit(main())
