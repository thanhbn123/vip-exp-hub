#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — CHẠY TAY vòng tròn SAO LƯU → KHÔI PHỤC, in bảng cho người đọc.

    python3 trien_khai/g20-saoluu/do_vong_tron.py            # 8 kịch bản, in bảng
    python3 trien_khai/g20-saoluu/do_vong_tron.py --json F   # ghi số đo ra F
    python3 trien_khai/g20-saoluu/do_vong_tron.py --chi 1 3  # chỉ chạy kịch bản 1 và 3

Bộ thử TỰ ĐỘNG dùng CÙNG các kịch bản này: `app/thu/thu_g20_saoluu.py`. Không có bản sao thứ
hai của logic đo — hai bản sẽ lệch nhau, và bản lệch là bản người ta đọc.

MÃ THOÁT: 0 nếu MỌI kịch bản ĐO ĐƯỢC (tức các bước chuẩn bị và các vế đối chứng đường đều
đạt). Phát hiện về sản phẩm KHÔNG làm mã thoát khác 0 — việc của bộ đo là đo, không phải phán.
Phán nằm ở `docs/G20_BACKUP_RESTORE.md`.
"""
import json
import os
import sys
import time

DAY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DAY)

import kich_ban  # noqa: E402

# (số, tên hàm, tên ngắn). Thứ tự CỐ Ý: vòng tròn lành trước, rồi mới tới các ca hỏng — người
# đọc thấy "đường lành chạy được" trước khi thấy "đường hỏng chạy ra sao".
KICH_BAN = [
    (1, kich_ban.ca_vong_tron,
     "Vòng tròn đầy đủ → CSDL MỚI (từng bảng: số dòng + tổng tiền)"),
    (2, kich_ban.ca_doi_chung_duong,
     "ĐỐI CHỨNG ĐƯỜNG — khôi phục ngược lại chính CSDL gốc"),
    (3, kich_ban.ca_sao_luu_cat_giua_duong,
     "SAO LƯU BỊ CẮT GIỮA ĐƯỜNG — 3 cách cắt"),
    (4, kich_ban.ca_sua_mot_byte,
     "TỆP SAO LƯU BỊ SỬA 1 BYTE — 5 chỗ"),
    (5, kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay,
     "KHÔI PHỤC ĐÈ lên CSDL đã có dữ liệu"),
    (6, kich_ban.ca_khoi_phuc_schema_thap_hon,
     "KHÔI PHỤC bản sao lưu SCHEMA THẤP HƠN"),
    (7, kich_ban.ca_khoi_phuc_nham_ban_dump_pg,
     "KHÔI PHỤC NHẦM tệp không phải SQLite"),
    (8, kich_ban.ca_khoa_khong_di_kem,
     "KHÔI PHỤC CSDL mà THIẾU KHÓA NỘI BỘ"),
]


def _giao_dien(kq):
    """In phần NGƯỜI ĐỌC CẦN: mã thoát, số ca, phát hiện — không in cả dict."""
    print("  đạt (kịch bản đo chạy đúng): %s" % ("CÓ" if kq.get("dat") else "KHÔNG"))
    for k in ("rc_gieo", "rc_phinh", "rc_sao_luu", "rc_khoi_phuc", "rc_them", "rc_dung_v6",
              "rc_seed_v6", "rc_nang_lai", "rc_ghi_tren_v6", "rc_luot_cat", "rc_select_1",
              "rc_tao_csdl", "rc_nap_ddl", "rc_gieo_v9", "rc_sao_luu_v6", "rc_giai_ma_o_goc",
              "rc_giai_ma_o_khoi_phuc"):
        if k in kq:
            print("    %-22s %s" % (k, kq[k]))

    n = kq.get("ten", "")
    if n.startswith("1."):
        print("    bản sao lưu          : %s byte · %s bảng"
              % (kq.get("so_byte_ban_sao"), kq.get("so_bang")))
        print("    tổng tiền            : %s → %s" % (kq.get("tong_tien_truoc"),
                                                      kq.get("tong_tien_sau")))
        print("    băm toàn kho khớp    : %s" % (kq.get("bam_truoc") == kq.get("bam_sau")))
        print("    lệch TỪNG BẢNG       : %d (số dòng + tổng tiền)" % len(kq.get("lech_sau_khoi_phuc") or []))
        print("    CSDL gốc bị đổi vì sao lưu: %d lệch" % len(kq.get("lech_sau_khi_sao_luu_goc") or []))
        if kq.get("_truoc") and kq.get("_sau"):
            print()
            import khung_do
            khung_do.in_bang(kq["_truoc"], kq["_sau"], "TỪNG BẢNG: GỐC → KHÔI PHỤC VÀO CSDL MỚI")
    elif n.startswith("2."):
        print("    (a) phép so LÀM ĐỎ được: %d lệch sau khi ghi thêm" % kq.get("so_lech_giua"))
        print("        ví dụ: %s" % (kq.get("vi_du_lech_giua") or [])[:2])
        print("    (b) sau khi khôi phục   : %d lệch" % kq.get("so_lech_sau_khoi_phuc"))
        print("    tenant tạo SAU mốc sao lưu còn lại: %s (phải là 0)"
              % kq.get("tenant_sau_backup_con_lai"))
    elif n.startswith("3."):
        print("    CSDL gốc %s byte · sao lưu trọn vẹn %.3fs ra %s byte"
              % (kq.get("co_csdl_goc"), kq.get("giay_sao_luu_tron"), kq.get("co_ban_sao_tron")))
        print("    %-18s %-12s %-8s %-9s %s" % ("CÁCH CẮT", "TỆP DỞ", "NHẬN?", "rc", "CSDL SAU"))
        for c in kq.get("cac_cach_cat") or []:
            print("    %-18s %-12s %-8s %-9s %s" % (
                c["cach"], c["co_tep_de"], "CÓ" if c["khoi_phuc_NHAN"] else "không",
                c["rc_khoi_phuc"], json.dumps(c["csdl_sau"], ensure_ascii=False)))
        print("    ĐỐI CHỨNG ĐƯỜNG (tệp lành): %s" % json.dumps(kq.get("doi_chung_duong"),
                                                                ensure_ascii=False))
    elif n.startswith("4."):
        print("    %-14s %-9s %-46s %-8s %-8s %s" % (
            "CHỖ SỬA", "VỊ TRÍ", "SQLITE TỰ BÁO", "rc_kp", "NHẬN?", "BĂM KHỚP GỐC"))
        for c in kq.get("cac_lan_sua") or []:
            print("    %-14s %-9s %-46s %-8s %-8s %s" % (
                c["nhan"], c["vi_tri"], str(c["sqlite_tu_bao"])[:46], c["rc_khoi_phuc"],
                "CÓ" if c["khoi_phuc_NHAN"] else "không", c["bam_khop_goc"]))
        print("    số lượt `khoi_phuc()` NHẬN tệp đã sửa: %s/%s"
              % (kq.get("so_lan_khoi_phuc_NHAN_tat_ca"), len(kq.get("cac_lan_sua") or [])))
        print("    ĐỐI CHỨNG ĐƯỜNG (tệp lành): %d lệch" % (kq.get("doi_chung_duong") or {}).get("so_lech"))
    elif n.startswith("5."):
        print("    (a) bản cất trước khôi phục : %s" % (kq.get("ban_cat") or []))
        print("        nội dung bản cất        : %s" % json.dumps(kq.get("noi_dung_ban_cat"),
                                                                  ensure_ascii=False))
        print("    (b) còn giữ được dữ liệu gốc: %s" % kq.get("ban_cat_con_giu_duoc_du_lieu_goc"))
        print("    (c) 1 lượt khôi phục → %s bản cất · 3 lượt liên tiếp (cùng giây) → %s bản cất"
              % (kq.get("so_ban_cat_sau_1_lan"), kq.get("so_ban_cat_sau_3_lan")))
        print("        băm bản cất sau 1 lượt  : %s" % str(kq.get("bam_ban_cat_sau_1_lan"))[:24])
        print("        băm bản cất sau 3 lượt  : %s" % str(kq.get("bam_ban_cat_sau_3_lan"))[:24])
        print("        băm dữ liệu lúc chụp    : %s" % str(kq.get("bam_du_lieu_luc_chup_day"))[:24])
    elif n.startswith("6."):
        print("    v6: %s bảng, phiên bản %s · v9: %s bảng, phiên bản %s"
              % (kq.get("so_bang_v6"), kq.get("phien_ban_v6"), kq.get("so_bang_v9_truoc"),
                 kq.get("phien_ban_v9_truoc")))
        print("    SAU khôi phục: %s" % json.dumps(kq.get("chup_sau"), ensure_ascii=False))
        print("    thông báo của `khoi_phuc()`: %s" % (kq.get("out_khoi_phuc") or "")[-160:])
        print("    ghi được trên v6 (rc=%s), cột đọc ra: %s"
              % (kq.get("rc_ghi_tren_v6"), (kq.get("out_ghi") or "")[:100]))
        print("    nâng lại bằng migrate.chay(): rc=%s → %s"
              % (kq.get("rc_nang_lai"), json.dumps(kq.get("chup_sau_khi_nang"), ensure_ascii=False)))
        print("    dữ liệu v6 còn nguyên sau khi nâng: %s" % kq.get("du_lieu_v6_con_nguyen_sau_nang"))
    elif n.startswith("7."):
        print("    `khoi_phuc()` NHẬN tệp lạ: %s (rc=%s)" % (kq.get("khoi_phuc_NHAN_tep_la"),
                                                            kq.get("rc_khoi_phuc_nham")))
        print("    CSDL sau đó: %s" % json.dumps(kq.get("csdl_sau_khi_nham"), ensure_ascii=False))
        print("    ĐỐI CHỨNG ĐƯỜNG (tệp SQLite thật): %d lệch" % kq.get("so_lech_duong_dung"))
    elif n.startswith("8."):
        print("    khôi phục khớp dữ liệu: %d lệch · %s bảng · tổng tiền %s · integrity %s"
              % (kq.get("so_lech_csdl"), kq.get("so_bang_khoi_phuc"),
                 kq.get("tong_tien_khoi_phuc"), kq.get("integrity_khoi_phuc")))
        print("    khóa ở bản gốc / bản khôi phục: %s / %s"
              % (kq.get("co_khoa_o_goc"), kq.get("co_khoa_o_ban_khoi_phuc")))
        print("    giải mã ở bản gốc          : %s" % (kq.get("out_giai_ma_o_goc") or "")[:90])
        print("    giải mã ở bản khôi phục    : %s" % (kq.get("out_giai_ma_o_khoi_phuc") or "")[-150:])
        print("    tự sinh khóa mới khi thiếu : %s" % (kq.get("tu_sinh_khoa_moi_khi_thieu") or []))


def _giao_dien_pg(kq):
    print("  cụm riêng cổng            : %s (tự dựng: %s)" % (kq.get("cong"), kq.get("tu_dung_cum")))
    if kq.get("bo_qua"):
        print("  BỎ QUA: %s" % kq["bo_qua"])
        return
    print("  CSDL PostgreSQL có dữ liệu: %s"
          % json.dumps(kq.get("pg_truoc", {}).get("bang"), ensure_ascii=False))
    print("  tổng tiền phía PostgreSQL : %s" % kq.get("pg_truoc", {}).get("tong_tien"))
    d1 = kq.get("do1_hub_db_khong_ton_tai", {})
    print("  ĐO 1 — `hub.db` KHÔNG tồn tại (máy chủ đã chuyển kho sang PostgreSQL):")
    print("    rc=%s · stderr=%r" % (d1.get("rc"), d1.get("stderr")))
    print("    bản sao     : %s byte · %s bảng · tổng tiền %s · integrity %s"
          % (d1.get("co_ban_sao"), d1.get("so_bang"), d1.get("tong_tien"), d1.get("integrity")))
    print("    có bảng don_hang: %s · dòng don_hang: %s · dòng tc_but_toan: %s"
          % (d1.get("co_bang_don_hang"), d1.get("dong_don_hang"), d1.get("dong_tc_but_toan")))
    d2 = kq.get("do2_hub_db_co_du_lieu_sqlite_khac", {})
    print("  ĐO 2 — `hub.db` CÓ dữ liệu SQLite cũ (khác dữ liệu PostgreSQL):")
    print("    rc=%s · bản sao %s byte · %s bảng · tổng tiền %s · băm khớp SQLite gốc: %s"
          % (d2.get("rc"), d2.get("co_ban_sao"), d2.get("ban_sao_so_bang"),
             d2.get("ban_sao_tong_tien"), d2.get("bam_ban_sao_khop_sqlite_goc")))
    d3 = kq.get("do3_khoi_phuc_tu_pg_dump", {})
    print("  ĐO 3 — `pg_dump -Fc` THẬT (%s byte, rc=%s) đưa cho `khoi_phuc()`:"
          % (kq.get("pg_dump", {}).get("co_byte"), kq.get("pg_dump", {}).get("rc")))
    print("    NHẬN=%s · CSDL sau %s byte · %s"
          % (d3.get("khoi_phuc_NHAN"), d3.get("csdl_sau_so_byte"), d3.get("csdl_sau_loi")))
    print("  ĐỐI CHỨNG ĐƯỜNG (cùng hàm, kho SQLite có dữ liệu): %s"
          % json.dumps(kq.get("doi_chung_duong_sqlite_co_du_lieu"), ensure_ascii=False))
    print("  KẾT LUẬN: %s" % json.dumps(kq.get("ket_luan"), ensure_ascii=False))
    print("  vân tay cụm :5432 không đổi: %s (lệch: %s)"
          % (kq.get("van_tay_5432_khong_doi"), kq.get("van_tay_5432_lech")))


def main():
    chi = None
    if "--chi" in sys.argv:
        i = sys.argv.index("--chi")
        chi = {int(x) for x in sys.argv[i + 1:] if x.isdigit()}
    duong_json = None
    if "--json" in sys.argv:
        duong_json = sys.argv[sys.argv.index("--json") + 1]

    tong = 0
    dat_het = True
    ket_qua = {}
    print("=" * 78)
    print(" G20 / AG-04 — VÒNG TRÒN SAO LƯU → KHÔI PHỤC")
    print(" Mọi lượt đo chạy trong thư mục TẠM. KHÔNG đụng dữ liệu thật, KHÔNG gọi mạng.")
    print("=" * 78)
    for so, ham, ten in KICH_BAN:
        if chi and so not in chi:
            continue
        print("\n=== KỊCH BẢN %d — %s ===" % (so, ten))
        t0 = time.time()
        try:
            kq = ham()
        except Exception as e:                                   # noqa: BLE001
            import traceback
            traceback.print_exc()
            kq = {"ten": "%d. %s" % (so, ten), "dat": False, "loi_ngoai_le": "%s: %s" % (type(e).__name__, e)}
        giay = time.time() - t0
        print("  thời gian: %.2fs" % giay)
        kq["_giay"] = round(giay, 3)
        if so != 8:
            _giao_dien(kq)
        else:
            _giao_dien(kq)
        ket_qua[so] = kq
        tong += 1
        if not kq.get("dat"):
            dat_het = False

    # Kịch bản 9 nằm ở tệp riêng vì nó cần một CỤM PostgreSQL; thiếu công cụ thì BỎ QUA và
    # nói rõ thiếu gì, chứ không im lặng tính là "đạt".
    if not chi or 9 in chi:
        print("\n=== KỊCH BẢN 9 — PostgreSQL: `sao_luu()` làm gì khi dữ liệu nằm ở PostgreSQL ===")
        t0 = time.time()
        import do_postgres
        kq = do_postgres.chay()
        print("  thời gian: %.2fs" % (time.time() - t0))
        _giao_dien_pg(kq)
        if kq.get("bo_qua"):
            kq["dat"] = False
            print("  (bỏ qua — KHÔNG tính là đo được)")
        ket_qua[9] = kq
        tong += 1

    print("\n" + "=" * 78)
    print(" TỔNG: %d kịch bản · đo được %d · không đo được %d"
          % (tong, sum(1 for k in ket_qua.values() if k.get("dat")),
             sum(1 for k in ket_qua.values() if not k.get("dat"))))
    for so in sorted(ket_qua):
        k = ket_qua[so]
        print("   %-2s %-8s %s" % (so, "ĐO ĐƯỢC" if k.get("dat") else "KHÔNG ĐO ĐƯỢC",
                                  k.get("ten", "")[:66]))
    print(" PHÁN: xem `docs/G20_BACKUP_RESTORE.md`. Bộ đo này KHÔNG tự quyết định sản phẩm.")
    print("=" * 78)
    if duong_json:
        with open(duong_json, "w", encoding="utf-8") as f:
            json.dump({str(k): {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                       for k, v in ket_qua.items()}, f, ensure_ascii=False, indent=2, default=str)
        print("Số đo đã ghi: %s" % duong_json)
    return 0 if dat_het else 1


if __name__ == "__main__":
    sys.exit(main())
