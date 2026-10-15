#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ĐỘT BIẾN — chứng minh mỗi ca thử XANH đều LÀM ĐỎ ĐƯỢC.

====== VÌ SAO CẦN TỆP NÀY ======
Yêu cầu bằng chứng của G17/AG-05: *"Nếu một ca thử xanh, phải có ca TỰ KIỂM BỎ ĐỒ
(làm nó đỏ được)."*

Một ca thử chỉ thoát 0 KHÔNG chứng minh nó đo được gì. Một ca viết `assertTrue(True)`,
một ca bị bỏ qua lặng lẽ, hay một ca so hai chuỗi rỗng — tất cả đều xanh. Cách duy nhất
phân biệt "ca thử tốt" với "ca thử trang trí" là **PHÁ HỎNG thứ nó canh rồi xem nó có đỏ
lên không**. Tệp này làm đúng việc đó, tự động, cho từng ca.

====== CÁCH LÀM ======
1. Chép dự án sang một thư mục TẠM (bỏ `node_modules`, `.git`) — **không sửa gì trong
   thư mục thật**. Mọi lượt chạy ở đây đều là trên BẢN CHÉP.
2. Với mỗi đột biến: trả tệp về nguyên bản, áp đúng MỘT phép sửa, chạy đúng lớp ca thử
   liên quan, rồi đòi nó **THOÁT KHÁC 0**.
3. In bảng: đột biến nào → ca nào phải đỏ → đỏ thật không.

Đột biến nào mà ca thử VẪN XANH thì tệp này thoát khác 0: đó là một ca thử ĐỒ GIẢ.

====== PHẠM VI ======
Đây là đo trên BẢN CHÉP, dùng chính bộ thử thật. Nó không đo "chất lượng mã" — nó chỉ đo
một điều hẹp: **ca thử có nhìn thấy thứ nó tuyên bố đang canh hay không.**
Mỗi lượt chạy vẫn dựng CỤM PostgreSQL RIÊNG (cổng riêng, socket riêng, không TCP), không
đụng cụm `:5432`.

CHẠY
----
    python3 trien_khai/postgres/thu_dot_bien.py
    python3 trien_khai/postgres/thu_dot_bien.py --giu   # giữ bản chép để soi
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BO_QUA = {"node_modules", ".git", ".venv", "__pycache__", "thu_giao_dien", "assets",
          "playwright-report", "test-results"}

TP = "app/thu/thu_postgres.py"
VT = "trien_khai/postgres/van_tay_cum.py"

# Mỗi mục: phá đúng MỘT thứ, rồi đòi ĐÚNG lớp ca thử canh thứ đó phải ĐỎ.
DOT_BIEN = [
    {
        "ten": "Bỏ chốt chặn cổng 5432",
        "tep": TP, "cu": "        _kiem_cong_an_toan(self.cong)",
        "moi": "        pass  # ĐỘT BIẾN: bỏ chốt chặn cổng",
        "ca": "F_ChotChanCong5432ThatSu",
        "vi_sao": "bộ thử sẽ chạy thẳng trên cụm :5432 của dự án khác",
    },
    {
        "ten": "Bỏ dòng xin khoá tư vấn khi migration",
        "tep": TP,
        "cu": '            than += "SELECT pg_advisory_xact_lock(%d);\\n" % KHOA_MIGRATION\n',
        "moi": "            pass  # ĐỘT BIẾN: không xin khoá, hai tiến trình cùng nâng cấp\n",
        "ca": "H_MigrationKhoaTuVan.test_h1_co_khoa_thi_dung_mot_tien_trinh_nang_cap",
        "vi_sao": "tiến trình thứ hai đụng độ 23505 thay vì NHƯỜNG",
    },
    {
        "ten": "DDL rỗng (nạp 'đạt' mà không tạo gì)",
        "tep": TP, "cu": "    DDL_PG = sinh_ddl_pg.sinh()[0]",
        "moi": '    DDL_PG = ""  # ĐỘT BIẾN: khối DDL rỗng',
        "ca": "I_DDLNguyenTuTruocSau.test_i1_truoc_sau_va_khop_sqlite",
        "vi_sao": "một khối DDL rỗng nạp bao giờ cũng 'đạt' — phải bị chốt >40 bảng chặn",
    },
    {
        "ten": "Khuôn đọc-rồi-ghi được viết lại thành nguyên tử",
        "tep": TP, "cu": '        if kieu == "nguyen_tu":\n',
        "moi": '        if True:  # ĐỘT BIẾN: mọi lượt đều cộng ở tầng câu\n',
        "ca": "J_DoiChieuMatCapNhat.test_j2_postgres_mat_cap_nhat_im_lang",
        "vi_sao": "đồng hồ đo mất-cập-nhật phải trả về 0 ⇒ ca phải đỏ",
    },
    {
        "ten": "Khôi phục bị MẤT một bảng",
        "tep": TP,
        "cu": ('        cls._cap = (_chup_kho(cls.CSDL_GOC), _chup_kho(cls.CSDL_KP))'),
        # `audit` là bảng LÁ — không bảng nào tham chiếu nó, nên `DROP` không bị khoá ngoại
        # chặn. Bản đầu của đột biến này dùng `khach_hang` và `DROP` đã HỎNG LẶNG LẼ vì
        # `don_hang` tham chiếu nó — ca thử vẫn xanh và tưởng là ca thử yếu. Xem mục
        # "ĐỘT BIẾN TỰ HỎNG" trong docs/G17_POSTGRES.md.
        "moi": ('        CUM.psql("DROP TABLE audit", db=cls.CSDL_KP)  # ĐỘT BIẾN\n'
                '        cls._cap = (_chup_kho(cls.CSDL_GOC), _chup_kho(cls.CSDL_KP))'),
        "ca": "K_SaoLuuKhoiPhuc.test_k1_khoi_phuc_giu_so_dong_va_tong_tien",
        "vi_sao": "phép so số dòng TỪNG BẢNG phải thấy bảng bị mất",
    },
    {
        "ten": "Khôi phục bị MẤT dòng và mất payload nhị phân",
        "tep": TP,
        "cu": ('        cls._cap = (_chup_kho(cls.CSDL_GOC), _chup_kho(cls.CSDL_KP))'),
        "moi": ('        CUM.psql("DELETE FROM wh_su_kien", db=cls.CSDL_KP)  # ĐỘT BIẾN\n'
                '        cls._cap = (_chup_kho(cls.CSDL_GOC), _chup_kho(cls.CSDL_KP))'),
        "ca": "K_SaoLuuKhoiPhuc.test_k1_khoi_phuc_giu_so_dong_va_tong_tien",
        "vi_sao": "số dòng TỪNG BẢNG và md5 payload phải nhạy với một dòng bị mất",
    },
    {
        "ten": "Phép so vân tay luôn trả 'giống nhau'",
        "tep": VT, "cu": "    return (not lech), lech",
        "moi": "    return True, []  # ĐỘT BIẾN: luôn phán 'giống nhau'",
        "ca": "G_VanTayCumHeThong.test_g3_phep_so_phat_hien_duoc_khac_biet",
        "vi_sao": "một phép so luôn-xanh làm cả báo cáo 'TRƯỚC = SAU' thành đồ trang trí",
    },
]


def chep_du_an(dich):
    def bo_qua(thu_muc, ten):
        return [x for x in ten if x in BO_QUA]
    shutil.copytree(DU_AN, dich, ignore=bo_qua, symlinks=False)
    # `.git` ở đây là một TỆP con trỏ (worktree) — chép nó sang là vô nghĩa và gây lẫn.
    for r, _, fs in os.walk(dich):
        for f in list(fs):
            if f == ".git":
                os.remove(os.path.join(r, f))


def chay(dich, ten_ca):
    p = subprocess.run([sys.executable, TP, ten_ca], cwd=dich,
                       capture_output=True, text=True, timeout=900)
    return p.returncode, p.stdout + p.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--giu", action="store_true", help="giữ bản chép lại để soi")
    a = ap.parse_args()

    goc = tempfile.mkdtemp(prefix="vhdb-")
    dich = os.path.join(goc, "ban-chep")
    print("Bản chép: %s" % dich)
    chep_du_an(dich)
    nguyen_ban = {}
    for d in DOT_BIEN:
        nguyen_ban.setdefault(d["tep"], open(os.path.join(dich, d["tep"]),
                                             encoding="utf-8").read())
    hong = []
    try:
        # ---- ĐỐI CHỨNG: bản chép KHÔNG đột biến thì phải XANH. Thiếu lượt này thì mọi
        # "đỏ" ở dưới có thể chỉ là do bản chép hỏng, chứ không phải do đột biến.
        print("\n── ĐỐI CHỨNG: bản chép nguyên bản, chạy cả 6 lớp mới")
        for ten_ca in ("F_ChotChanCong5432ThatSu", "G_VanTayCumHeThong",
                       "H_MigrationKhoaTuVan", "I_DDLNguyenTuTruocSau",
                       "J_DoiChieuMatCapNhat", "K_SaoLuuKhoiPhuc"):
            ma, ra = chay(dich, ten_ca)
            dat = (ma == 0)
            print("   %s %-32s mã thoát %d" % ("✓" if dat else "✗", ten_ca, ma))
            if not dat:
                hong.append("ĐỐI CHỨNG %s (bản chép nguyên bản đã hỏng)" % ten_ca)
                print(ra[-600:])

        # ---- TỪNG ĐỘT BIẾN ----
        print("\n── ĐỘT BIẾN: mỗi phép phá ĐÚNG MỘT thứ, đòi ca canh nó phải ĐỎ")
        for d in DOT_BIEN:
            duong = os.path.join(dich, d["tep"])
            goc_tep = nguyen_ban[d["tep"]]
            if goc_tep.count(d["cu"]) != 1:
                print("   ⊘ %-48s KHÔNG ÁP ĐƯỢC (mẫu xuất hiện %d lần)"
                      % (d["ten"], goc_tep.count(d["cu"])))
                hong.append("%s — mẫu đột biến không khớp" % d["ten"])
                continue
            with open(duong, "w", encoding="utf-8") as f:
                f.write(goc_tep.replace(d["cu"], d["moi"]))
            try:
                ma, ra = chay(dich, d["ca"])
                do = (ma != 0)
                print("   %s %-46s → %s (mã thoát %d)"
                      % ("✓" if do else "✗", d["ten"], "ĐỎ, đúng" if do else "VẪN XANH",
                         ma))
                if not do:
                    hong.append("%s — ca `%s` VẪN XANH sau khi phá" % (d["ten"], d["ca"]))
                print("       vì sao phải đỏ: %s" % d["vi_sao"])
            finally:
                with open(duong, "w", encoding="utf-8") as f:
                    f.write(goc_tep)
    finally:
        if a.giu:
            print("\n--giu: bản chép còn ở %s" % dich)
        else:
            shutil.rmtree(goc, ignore_errors=True)

    print("\n" + "═" * 74)
    if hong:
        print("HỎNG %d:" % len(hong))
        for h in hong:
            print("   · %s" % h)
        return 1
    print("ĐẠT: %d/%d đột biến làm ĐỎ đúng ca canh nó, và bản chép nguyên bản vẫn XANH."
          % (len(DOT_BIEN), len(DOT_BIEN)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
