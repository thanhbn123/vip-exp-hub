#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TỰ KIỂM BỎ ĐỒ cho lớp `L` — mỗi ca thử của đường GHI phải LÀM ĐỎ ĐƯỢC.

====== VÌ SAO CẦN TỆP NÀY (và vì sao nó KHÁC `thu_dot_bien.py`) ======
`trien_khai/postgres/thu_dot_bien.py` (G17) đã làm việc này cho sáu lớp `F…K`. Lớp `L` là mã
MỚI, nên nó cần lượt phá riêng: một ca thử mới toanh mà chưa ai phá thì chưa chứng minh được
nó nhìn thấy gì. Tệp này KHÔNG sửa `thu_dot_bien.py` — hai tệp độc lập, mỗi tệp canh phần của mình.

====== CÁCH LÀM ======
1. Chép dự án sang thư mục TẠM (bỏ `node_modules`, `.git`). **Không sửa gì trong thư mục thật.**
2. ĐỐI CHỨNG trước: bản chép NGUYÊN BẢN phải XANH (chạy đúng lớp `L`).
3. Với mỗi đột biến: trả tệp về nguyên bản, phá ĐÚNG MỘT thứ, chạy lớp `L`, đòi nó **THOÁT KHÁC 0**.

Đột biến nào mà lớp `L` VẪN XANH thì tệp này thoát khác 0 — đó là một ca thử ĐỒ GIẢ.

====== AN TOÀN ======
Mỗi lượt chạy dựng **cụm PostgreSQL RIÊNG** (cổng 55432, socket `/tmp/vhpg.XXXX`,
`listen_addresses=''`). Đột biến "bỏ chốt chặn cổng 5432" chỉ gỡ hàm `kiem_cong_an_toan` KHỎI
đường từ chối — nó **không** dựng cụm trên 5432 (không lượt nào gọi `CumGhi.dung()` với cổng
5432), nên cụm hệ thống vẫn không bị đụng. Vân tay `:5432` được chụp TRƯỚC/SAU ở cuối tệp.

CHẠY
----
    python3 trien_khai/postgres/thu_dot_bien_ghi.py
    python3 trien_khai/postgres/thu_dot_bien_ghi.py --giu     # giữ bản chép để soi
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import van_tay_cum                                                       # noqa: E402

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BO_QUA = {"node_modules", ".git", ".venv", "__pycache__", "thu_giao_dien", "assets",
          "playwright-report", "test-results"}

TP = "app/thu/thu_postgres.py"
DG = "trien_khai/postgres/duong_ghi_pg.py"
LP = "trien_khai/postgres/libpq_ctypes.py"
LOP = "L_DuongGhiSanPham"

# Mỗi mục: phá ĐÚNG một thứ, rồi đòi ĐÚNG ca thử canh thứ đó phải ĐỎ.
DOT_BIEN = [
    {
        "ten": "Bỏ `setval` sequence cho `tenants` (lớp B đã chèn id tường minh)",
        "tep": TP, "ca": "test_l1_hai_muoi_ba_ca_ghi_chay_tren_ca_hai_kho",
        "cu": ('                pg.chay_sql("SELECT setval(pg_get_serial_sequence(\'tenants\',\'id\'),"\n'
               '                            " GREATEST((SELECT COALESCE(max(id),0) FROM tenants),1))")\n'),
        "moi": "                pass  # ĐỘT BIẾN: không đồng bộ sequence\n",
        "vi_sao": "lượt chèn kiểu sản phẩm nhận 23505 ⇒ vế ĐỌC KIỂM CHỨNG phải bắt được",
    },
    {
        "ten": "Phép so hai kho luôn phán 'giống nhau'",
        "tep": DG, "ca": "test_l2_danh_sach_lech_dung_bang_bon_ca_da_do",
        "cu": "            lech.append(dong)\n        else:\n            giong.append(dong)",
        "moi": "            giong.append(dong)  # ĐỘT BIẾN: không bao giờ ghi nhận lệch\n        else:\n            giong.append(dong)",
        "vi_sao": "một phép so luôn-xanh làm cả bảng W thành đồ trang trí",
    },
    {
        "ten": "Trình điều khiển PostgreSQL trả -1 cho câu ĐỌC (bắt chước SQLite)",
        "tep": LP, "ca": "test_l3_cau_doc_sqlite_tra_am_mot_postgres_tra_so_dong",
        "cu": "        return hang, nt, tt, \"\", None",
        "moi": "        return hang, -1, tt, \"\", None  # ĐỘT BIẾN: giấu số dòng thật",
        "vi_sao": "lệch `SELECT`: SQLite -1 vs PostgreSQL số-dòng-thật phải biến mất",
    },
    {
        "ten": "Ca W13 xoá 1 dòng thay vì 2 (phá TIỀN ĐỀ của cơ chế rowcount-cũ)",
        "tep": DG, "ca": "test_l4_returning_sqlite_tra_rowcount_CU_cua_cau_truoc",
        "cu": '        "DELETE FROM w_ghi WHERE id IN (3,4)", (),',
        "moi": '        "DELETE FROM w_ghi WHERE id=3", (),  # ĐỘT BIẾN: câu DML trước chỉ đổi 1 dòng',
        "vi_sao": ("ca `W15` khẳng định SQLite trả con số CŨ (2 = số dòng `W13` xoá). Đổi W13 thành 1 "
                   "dòng thì con số cũ bằng 1 — TRÙNG với PostgreSQL — và ca phải ĐỎ, chứng minh nó "
                   "bám vào CƠ CHẾ chứ không bám vào một hằng số"),
    },
    {
        "ten": "Giao dịch hỏng thì CHỐT thay vì LÙI",
        "tep": DG, "ca": "test_l6_bon_ket_cuc_qua_duong_ghi_that",
        "cu": "                if self.sau == 0:\n                    self.kn.execute(\"ROLLBACK\")",
        "moi": "                if self.sau == 0:\n                    self.kn.execute(\"COMMIT\")  # ĐỘT BIẾN\n",
        "vi_sao": "T2: `rowcount` trả 1 trong khối rồi giao dịch hỏng — kho phải TRỐNG sau khi lùi",
    },
    {
        "ten": "Trình điều khiển TỰ LÙI rồi THỬ LẠI khi gặp 25P02",
        "tep": LP, "ca": "test_l7_cau_sau_loi_trong_giao_dich_hai_kho_KHAC_nhau",
        "cu": ("    def execute(self, sql, tham_so=None):\n"
               "        self._mo_giao_dich()\n"
               "        hang, rc, tt, td, ss = self._exec(sql, tham_so)\n"
               "        return ConTro(hang, rc, tt, td, ss)"),
        "moi": ("    def execute(self, sql, tham_so=None):\n"
                "        self._mo_giao_dich()\n"
                "        try:\n"
                "            hang, rc, tt, td, ss = self._exec(sql, tham_so)\n"
                "        except LoiVanHanh as e:  # ĐỘT BIẾN: 'tiện tay' cứu giao dịch đã hỏng\n"
                "            if e.sqlstate != '25P02':\n"
                "                raise\n"
                "            self._exec('ROLLBACK')\n"
                "            self._trong_giao_dich = False\n"
                "            hang, rc, tt, td, ss = self._exec(sql, tham_so)\n"
                "        return ConTro(hang, rc, tt, td, ss)"),
        "vi_sao": "PostgreSQL huỷ CẢ giao dịch (25P02) ⇒ câu sau KHÔNG chạy; tự lùi rồi thử lại là che mất khác biệt thật",
    },
    {
        "ten": "Đường ghi PostgreSQL ép chế độ TỰ CHỐT (giấu ca chưa-chốt)",
        "tep": DG, "ca": "test_l8_che_do_mac_dinh_cua_psycopg2_ghi_IM_LANG",
        "cu": "        self.tu_dong_chot = tu_dong_chot\n        self.tu_dong_mo = tu_dong_chot if tu_dong_mo is None else tu_dong_mo",
        "moi": "        self.tu_dong_chot = True  # ĐỘT BIẾN: luôn tự chốt\n        self.tu_dong_mo = True",
        "vi_sao": "chế độ mặc định của psycopg2 trả rowcount=1 mà kho TRỐNG — đột biến này làm nó BỀN, tức là giấu mất chỗ im lặng",
    },
    {
        "ten": "Kịch bản bắt tay đổi sang khuôn NGUYÊN TỬ",
        "tep": DG, "ca": "test_l9_mat_cap_nhat_qua_mot_va_ghi_la_that_va_o_CA_HAI_kho",
        "cu": ('        duong.ghi("UPDATE w_dem SET dem=? WHERE id=?", (kq["da_doc"] + 1, 1))'),
        "moi": '        duong.ghi("UPDATE w_dem SET dem = dem + 1 WHERE id=?", (1,))  # ĐỘT BIẾN\n',
        "vi_sao": "khuôn nguyên tử thì KHÔNG mất cập nhật ⇒ `mất = 1` phải thành `mất = 0`",
    },
    {
        "ten": "Đồng hồ đo mất-cập-nhật dùng khuôn NGÂY THƠ ở cả hai nhánh",
        "tep": DG, "ca": "test_l10_doi_chung_duong_cho_dong_ho_do",
        "cu": '                if kieu == "nguyen_tu":',
        "moi": '                if False:  # ĐỘT BIẾN: mọi lượt đều đọc-rồi-ghi\n',
        "vi_sao": "đối chứng dương phải cho `mất = 0`; phá nó là đối chứng mất tác dụng",
    },
    {
        "ten": "Phép so BỎ vế ĐỌC KIỂM CHỨNG (chỉ so rowcount)",
        "tep": DG, "ca": "test_l11_phep_so_lam_do_duoc",
        "cu": "                or a[\"kiem_dat\"] is not True or b[\"kiem_dat\"] is not True:",
        "moi": "                or False:  # ĐỘT BIẾN: bỏ vế đọc kiểm chứng\n",
        "vi_sao": "thiếu vế này thì hai kho CÙNG SAI vẫn được phán 'giống nhau'",
    },
    {
        "ten": "Chốt chặn cổng 5432 không từ chối nữa",
        "tep": DG, "ca": "test_l12_chot_chan_cong_5432_va_khong_mo_tcp",
        "cu": '    if str(cong) == CONG_CAM:',
        # Gỡ ĐÚNG đường từ chối. Lượt chạy này KHÔNG gọi `CumGhi.dung()` với cổng 5432, nên
        # không có cụm nào được dựng trên cổng của dự án khác — xem mục AN TOÀN ở đầu tệp.
        "moi": '    if False:  # ĐỘT BIẾN: thôi không từ chối cổng 5432\n',
        "vi_sao": "cầu nối mới có thể bị gọi từ tệp khác — chốt chặn phải nằm trong chính nó",
    },
    {
        "ten": "DDL bảng đo mất IDENTITY (còn `INTEGER PRIMARY KEY`)",
        "tep": DG, "ca": "test_l13_bay_identity_sqlite_chay_postgres_23505",
        "cu": 'DDL_IDT_PG = ("CREATE TABLE IF NOT EXISTS w_idt "\n'
              '              "(id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY, x INTEGER NOT NULL)")',
        "moi": 'DDL_IDT_PG = ("CREATE TABLE IF NOT EXISTS w_idt "\n'
               '              "(id BIGINT PRIMARY KEY, x INTEGER NOT NULL)")  # ĐỘT BIẾN\n',
        "vi_sao": "mất IDENTITY thì lượt chèn kiểu sản phẩm hỏng vì lý do KHÁC (23502) ⇒ ca phải đỏ",
    },
]


def chep_du_an(dich):
    def bo_qua(thu_muc, ten):
        return [x for x in ten if x in BO_QUA]
    shutil.copytree(DU_AN, dich, ignore=bo_qua, symlinks=False)
    for r, _, fs in os.walk(dich):
        for f in list(fs):
            if f == ".git":
                os.remove(os.path.join(r, f))


def chay(dich):
    """Chạy ĐÚNG lớp `L` trên bản chép. Trả (mã thoát, output)."""
    p = subprocess.run([sys.executable, TP, LOP], cwd=dich,
                       capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu", action="store_true", help="giữ bản chép lại để soi")
    a = ap.parse_args()

    vt_truoc = van_tay_cum.chup("5432")
    goc = tempfile.mkdtemp(prefix="vhdb-ghi-")
    dich = os.path.join(goc, "ban-chep")
    print("Bản chép: %s" % dich)
    chep_du_an(dich)
    nguyen_ban = {}
    for d in DOT_BIEN:
        nguyen_ban.setdefault(d["tep"], open(os.path.join(dich, d["tep"]), encoding="utf-8").read())
    hong = []
    try:
        # ---- ĐỐI CHỨNG: bản chép KHÔNG đột biến phải XANH.
        print("\n── ĐỐI CHỨNG: bản chép nguyên bản, chạy lớp %s" % LOP)
        ma, ra = chay(dich)
        print("   %s mã thoát %d · %s" % ("✓" if ma == 0 else "✗", ma,
                                          [d for d in ra.splitlines() if d.startswith("Ran ")]))
        if ma != 0:
            hong.append("ĐỐI CHỨNG: bản chép nguyên bản đã hỏng")
            print(ra[-800:])

        print("\n── ĐỘT BIẾN: mỗi phép phá ĐÚNG MỘT thứ, đòi ca canh nó phải ĐỎ")
        for d in DOT_BIEN:
            duong = os.path.join(dich, d["tep"])
            goc_tep = nguyen_ban[d["tep"]]
            if goc_tep.count(d["cu"]) != 1:
                print("   ⊘ %-52s KHÔNG ÁP ĐƯỢC (mẫu xuất hiện %d lần)"
                      % (d["ten"], goc_tep.count(d["cu"])))
                hong.append("%s — mẫu đột biến không khớp" % d["ten"])
                continue
            with open(duong, "w", encoding="utf-8") as f:
                f.write(goc_tep.replace(d["cu"], d["moi"]))
            try:
                ma, ra = chay(dich)
                do = (ma != 0)
                print("   %s %-52s → %s (mã thoát %d)"
                      % ("✓" if do else "✗", d["ten"], "ĐỎ, đúng" if do else "VẪN XANH", ma))
                if not do:
                    hong.append("%s — lớp `L` VẪN XANH sau khi phá" % d["ten"])
                else:
                    that_bai = [x for x in ra.splitlines() if x.startswith("FAIL:") or x.startswith("ERROR:")]
                    for x in that_bai[:4]:
                        print("       ca đỏ: %s" % x)
                    if not any(d["ca"] in x for x in that_bai):
                        print("       ⚠ ca đỏ KHÔNG phải `%s` — đỏ vì lý do khác" % d["ca"])
                        hong.append("%s — đỏ nhưng không phải ca `%s`" % (d["ten"], d["ca"]))
                print("       vì sao phải đỏ: %s" % d["vi_sao"])
            finally:
                with open(duong, "w", encoding="utf-8") as f:
                    f.write(goc_tep)
    finally:
        if a.giu:
            print("\n--giu: bản chép còn ở %s" % dich)
        else:
            shutil.rmtree(goc, ignore_errors=True)

    vt_sau = van_tay_cum.chup("5432")
    giong, lech = van_tay_cum.so_sanh(vt_truoc, vt_sau)
    print("\nVÂN TAY :5432 TRƯỚC = SAU: %s" % ("ĐÚNG" if giong else "SAI — %s" % (lech,)))
    if not giong:
        hong.append("vân tay :5432 lệch — lượt đo ĐỤNG cụm hệ thống")

    print("\n" + "═" * 78)
    if hong:
        print("HỎNG %d:" % len(hong))
        for h in hong:
            print("   · %s" % h)
        return 1
    print("ĐẠT: %d/%d đột biến làm ĐỎ ĐÚNG ca canh nó, và bản chép nguyên bản vẫn XANH."
          % (len(DOT_BIEN), len(DOT_BIEN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
