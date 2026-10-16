#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — ĐO TÍNH **FAIL-CLOSED** CỦA SAO LƯU → KHÔI PHỤC.

Chạy tay:  python3 trien_khai/g20-saoluu/fail_closed.py            (bảng cho người đọc)
           python3 trien_khai/g20-saoluu/fail_closed.py --json F   (máy đọc)
           python3 trien_khai/g20-saoluu/fail_closed.py --nhanh    (bỏ qua PostgreSQL)
Bộ thử:    app/thu/thu_g21_saoluu.py  (gọi `chay_tat_ca()` và khẳng định theo bất biến)

================= CÂU HỎI DUY NHẤT CỦA MÔ-ĐUN NÀY =================
AG-04 đã đo VÒNG TRÒN LÀNH: 41 ca, mã thoát 0. Nhưng "đường lành chạy được" KHÔNG trả lời được
câu hỏi vận hành quan trọng hơn:

    Khi sao lưu hoặc khôi phục HỎNG, hệ DỪNG LẠI VÀ BÁO RÕ — hay nó IM LẶNG ĐI TIẾP
    và để lại một TRẠNG THÁI NỬA VỜI?

Mỗi trường hợp hỏng ghi lại BA thứ, không thiếu thứ nào:
    (1) MÃ THOÁT THẬT của tiến trình đã làm hỏng,
    (2) THÔNG BÁO THẬT nó in ra (nguyên văn),
    (3) TRẠNG THÁI CUỐI của CSDL ĐÍCH — TỪNG BẢNG, cả SỐ DÒNG lẫn TỔNG TIỀN (qua `khung_do`),
        cộng `bam_toan_kho`; ở những kịch bản không giữ được phép chụp đầy đủ thì vế (3) được
        dựng từ chính số đo của kịch bản đó và **NÓI RÕ nó dựng từ đâu**.

================= TIÊU CHÍ ĐẠT (fail-closed) =================
Một trường hợp HỎNG là FAIL_CLOSED khi và chỉ khi:
    (a) `rc != 0` — tiến trình thoát KHÁC 0;
    (b) có một dòng thông báo NÓI RA chỗ hỏng (xem `thong_bao_noi_ro`);
    (c) CSDL ĐÍCH còn NGUYÊN VẸN đúng như trước lượt hỏng — so TỪNG BẢNG (số dòng + tổng tiền)
        cộng băm toàn kho; nói cách khác: KHÔNG bị để lại nửa vời.
Thiếu bất kỳ vế nào ⇒ FAIL_OPEN, và `ly_do` ghi rõ thiếu vế nào.

**Một chỗ tôi cố ý KHÔNG làm chặt hơn thực tế:** khi hỏng, `migrate.khoi_phuc()` để một
traceback Python thoát ra. Một traceback CÓ nói ra chỗ hỏng (tên hàm, đường dẫn nguồn và đích),
nên vế (b) được tính là ĐẠT — nhưng nó KHÔNG phải thông báo cho người trực. Khác nhau đó được
ghi thành trường riêng `la_traceback_tho` và in ra ở bảng, **KHÔNG trộn vào phán quyết**: trộn
vào là làm hỏng phép đo, vì người sau sẽ đọc "FAIL_OPEN vì traceback" và tưởng lỗi nằm ở văn
phong thông báo, trong khi lỗi thật nằm ở vế (c).

================= MÔ PHỎNG "HẾT ĐĨA GIỮA ĐƯỜNG" BẰNG CÁCH NÀO =================
`RLIMIT_FSIZE` (giới hạn cứng của HĐH về số byte ghi được vào một tệp), đặt trong `preexec_fn`
của tiến trình con. Trung thực hơn "cắt tệp sau khi ghi xong" vì nó làm lần GHI THẬT SỰ thất bại
NGAY GIỮA ĐƯỜNG — đúng điều xảy ra khi hết đĩa. Đo được (macOS / CPython 3.9):
`OSError: [Errno 27] File too large`, KHÔNG phải SIGXFSZ — nên tiến trình còn sống để in thông
báo. Nếu một nền khác giết tiến trình bằng tín hiệu thì `rc` vẫn ghi được (`-25`).

================= CHỐT AN TOÀN (không đổi so với AG-04) =================
Mọi lượt đo chạy trong thư mục TẠM; `kich_ban.chot_an_toan()` TỪ CHỐI vùng dữ liệu thật.
KHÔNG gọi mạng. Cụm PostgreSQL là cụm RIÊNG, TỪ CHỐI cổng 5432. Mô-đun này KHÔNG sửa
`app/migrate.py` hay `app/csdl.py` — nó chỉ ĐỌC chúng, và có thể trỏ sang một bản sao để
ĐỐI CHỨNG (xem `G21_APP_DIR`).

================= `G21_APP_DIR` — chạy CÙNG phép đo trên một `migrate.py` ỨNG VIÊN =============
Mặc định `app/` của chính cây này. Đặt `G21_APP_DIR=<thư mục>` để mọi tiến trình con nạp
`migrate.py` từ thư mục đó. Dùng cho hai việc, cả hai đều là ĐỐI CHỨNG ĐƯỜNG BẮT BUỘC:
  * TIÊM một lỗi fail-open vào một bản `migrate.py` TỐT ⇒ bộ đo PHẢI bắt được (không thì bộ đo
    không có răng, và mọi kết luận ở trên vô nghĩa);
  * chạy trên bản `migrate.py` ĐÃ VÁ ⇒ mọi trường hợp hỏng PHẢI chuyển sang FAIL_CLOSED.
"""
import json
import os
import resource
import subprocess
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
sys.path.insert(0, DAY)

import khung_do    # noqa: E402
import kich_ban    # noqa: E402

PY = sys.executable or "python3"

# Thư mục `app/` mà MỌI tiến trình con sẽ nạp `migrate.py` từ đó. Xem docstring.
APP = os.environ.get("G21_APP_DIR") or os.path.join(GOC, "app")


# ============================================================================
# HẠ TẦNG: chạy tiến trình con dưới GIỚI HẠN GHI (mô phỏng hết đĩa)
# ============================================================================
def chay_con_gioi_han_ghi(ma, data_dir, gioi_han, env_them=None, timeout=900):
    """Chạy `ma` trong tiến trình RIÊNG với `RLIMIT_FSIZE = gioi_han`.

    Vì sao phải là tiến trình riêng: `setrlimit` áp cho CẢ tiến trình hiện tại lẫn con của nó.
    Đặt trong tiến trình này thì chính bộ đo không ghi được báo cáo nữa.
    """
    if gioi_han <= 0:
        raise AssertionError("giới hạn ghi phải > 0, nhận %r" % (gioi_han,))

    def _dat_gioi_han():
        resource.setrlimit(resource.RLIMIT_FSIZE, (gioi_han, gioi_han))

    p = subprocess.run([PY, "-c", ma], capture_output=True, text=True, cwd=GOC,
                       env=kich_ban.moi_truong(data_dir, **(env_them or {})),
                       timeout=timeout, preexec_fn=_dat_gioi_han)
    return p.returncode, p.stdout, p.stderr


# ============================================================================
# VẾ (b): THÔNG BÁO CÓ NÓI RA CHỖ HỎNG KHÔNG
# ============================================================================
# Dấu hiệu "có chuyện không xong". Cố ý RỘNG: bỏ sót một thông báo hỏng thật là lỗi nặng hơn
# nhận nhầm một dòng vô hại. Vì sao vẫn đủ chặt: vế (a) `rc != 0` là điều kiện BẮT BUỘC đi kèm,
# nên một chữ "không" lạc lõng không thể một mình làm ca này ĐẠT.
DAU_HIEU_HONG = ("lỗi", "loi", "không", "khong", "error", "traceback", "exception",
                 "từ chối", "tu choi", "thiếu", "thieu", "hỏng", "hong", "thất bại",
                 "that bai", "refus", "cannot", "unable", "fail")


def thong_bao_noi_ro(out, err):
    """Trả (co_dong_bao_hong, dong_bao, la_traceback_tho). Ba giá trị, KHÔNG gộp.

    Một dòng được tính là "nói ra chỗ hỏng" khi: dài >= 15 ký tự VÀ chứa một dấu hiệu hỏng.
    Ngưỡng 15 ký tự để loại những dòng cụt như "loi" hay "0" — một dòng cụt không nói ra gì.

    Lấy dòng KHỚP **CUỐI CÙNG**, không phải đầu tiên: trong một traceback, dòng đầu là
    "Traceback (most recent call last):" (khớp chữ "traceback" nhưng KHÔNG cho biết hỏng ở đâu),
    còn dòng cuối là ngoại lệ thật kèm đường dẫn. Lấy dòng đầu là tự lừa mình bằng một thông báo
    trông-có-vẻ-rõ mà thực ra rỗng.

    `la_traceback_tho` đo một tính chất KHÁC (thông báo có phải traceback trần không) và KHÔNG
    tham gia phán quyết — xem docstring đầu tệp.
    """
    dong = [d.strip() for d in ((err or "") + "\n" + (out or "")).splitlines() if d.strip()]
    tb = "traceback (most recent call last)" in (err or "").lower()
    khop = [d for d in dong if len(d) >= 15 and any(m in d.lower() for m in DAU_HIEU_HONG)]
    if khop:
        return True, khop[-1][:300], tb
    return False, (dong[-1][:300] if dong else ""), tb


# ============================================================================
# VẾ (c): CSDL ĐÍCH CÒN NGUYÊN KHÔNG — TỪNG BẢNG, SỐ DÒNG **VÀ** TỔNG TIỀN
# ============================================================================
def so_lech_hai_chup(truoc, sau):
    """Danh sách lệch giữa hai phép chụp `khung_do`, cộng hai chốt đọc-được/cấu-trúc.

    Dùng ĐÚNG `khung_do.so_sanh` — tức so cả `integrity_check`, `phien_ban`, `so_bang`,
    `tong_tien_toan_kho`, `bam_toan_kho`, `so_byte`, VÀ TỪNG BẢNG (số dòng + từng cột tiền).
    Chỉ đếm số dòng là chưa đủ: xem docstring `khung_do` (số dòng y nguyên mà tiền sai).
    """
    if sau is None:
        return ["KHÔNG chụp được CSDL đích (kịch bản không giữ phép chụp)"]
    if not sau.get("ton_tai"):
        return ["CSDL đích KHÔNG CÒN TỒN TẠI sau lượt hỏng"]
    lech = khung_do.so_sanh(truoc, sau)
    if sau.get("loi"):
        lech.insert(0, "CSDL đích KHÔNG ĐỌC ĐƯỢC: %s" % sau["loi"])
    if sau.get("integrity_check") != "ok":
        lech.insert(0, "integrity_check = %r (khác 'ok')" % (sau.get("integrity_check"),))
    return lech


def _tom_tat_chup(c):
    if not c:
        return {"ton_tai": False}
    return {"ton_tai": c.get("ton_tai"), "so_byte": c.get("so_byte"),
            "so_bang": c.get("so_bang"), "phien_ban": c.get("phien_ban"),
            "integrity": c.get("integrity_check"), "tong_tien": c.get("tong_tien_toan_kho"),
            "bam": str(c.get("bam_toan_kho"))[:16], "loi": c.get("loi")}


# Nhóm dùng KHUÔN CHUNG (a) mã thoát · (b) thông báo · (c) CSDL đích nguyên vẹn: một lượt
# hỏng, một CSDL đích. Các mã còn lại có bất biến RIÊNG (S1/S2 là tập nhiều lượt cắt;
# S4 là "dữ liệu trước khi đè còn cứu được"; S8 là hành vi trên kho PostgreSQL; DC là ĐỐI
# CHỨNG ĐƯỜNG nên mã thoát ĐẠT của nó là 0, ngược lại mọi mã kia).
#
# Nhóm này được suy TỪ `ma`, KHÔNG từ một trường trong bản ghi. Đo được 16/10/2026: một trường
# `ap_dung_mau` do chỗ gọi tự khai sẽ lệch với `ma` lúc nào không biết, và khi đó `DC` bị áp
# khuôn "mã thoát phải khác 0" — một ĐỎ GIẢ ngay trong lượt tự kiểm của chính bộ đo.
AP_DUNG_MAU = frozenset({"S3", "S5", "S6a", "S6b", "S7"})


def _ghi(ma, ten, bat_buoc, rc, out, err, c_dat, c_lech, bang_chung,
         chup_truoc=None, chup_sau=None):
    """Đóng gói MỘT bản ghi đo theo cùng một khuôn. Mọi trường đều có thật, không suy diễn.

    `c_dat`  : vế (c) có ĐẠT không, theo phép đo RIÊNG của kịch bản đó.
    `c_lech` : vì sao không đạt (danh sách), hoặc [] khi đạt.
    """
    co_bao, dong, la_tb = thong_bao_noi_ro(out, err)
    return {
        "ma": ma, "ten": ten, "bat_buoc": bat_buoc, "ap_dung_mau": ma in AP_DUNG_MAU,
        "rc": rc,
        "thong_bao": ((out or "") + (err or "")).strip(),
        "dong_bao_hong": dong,
        "co_dong_bao_hong": co_bao,
        "la_traceback_tho": la_tb,
        "c_dat": bool(c_dat),
        "c_lech": list(c_lech or []),
        "csdl_dich_truoc": _tom_tat_chup(chup_truoc),
        "csdl_dich_sau": _tom_tat_chup(chup_sau),
        "bang_chung": bang_chung,
    }


# ============================================================================
# PHÁN QUYẾT — hàm THUẦN TÚY, để tự kiểm được bằng bản ghi TIÊM
# ============================================================================
def phan_quyet(bg):
    """Trả DANH SÁCH lỗi fail-closed của một bản ghi đo. Rỗng = FAIL_CLOSED (ĐẠT).

    Hàm THUẦN TÚY: chỉ đọc các trường đã đo trong `bg`, không tự đo gì thêm. Nhờ vậy
    `Z_TuKiemBoDo` trong `app/thu/thu_g21_saoluu.py` tiêm được bản ghi fail-open TỔNG HỢP và
    đòi hàm này phải NÓI RA — một bộ đo không chứng minh được nó LÀM ĐỎ ĐƯỢC thì mọi dòng ĐẠT
    của nó không chứng minh gì.
    """
    ma, loi = bg.get("ma"), []
    bc = bg.get("bang_chung") or {}

    # ---- khuôn chung (a)(b)(c) cho nhóm "một lượt hỏng, một CSDL đích" ----
    if ma in AP_DUNG_MAU:
        if bg.get("rc") == 0:
            loi.append("(a) mã thoát = 0 — hệ NHẬN lượt hỏng và đi tiếp")
        if not bg.get("co_dong_bao_hong"):
            loi.append("(b) không có dòng thông báo nào nói ra chỗ hỏng; dòng cuối: %r"
                       % (bg.get("dong_bao_hong"),))
        if not bg.get("c_dat"):
            loi.append("(c) CSDL ĐÍCH BỊ ĐỂ LẠI NỬA VỜI: %s" % "; ".join(bg.get("c_lech") or []))

    if ma == "S1":
        # Sao lưu bị cắt giữa đường. Bất biến CHỈ tính trên `cat_hong_that` — những lượt cắt mà
        # CSDL đích sau khi NHẬN tệp dở KHÁC bản gốc. Lượt cắt để lại tệp ĐỦ BYTE thì NHẬN là
        # ĐÚNG, không phải lỗi; xem docstring `ca_sao_luu_cat_giua_duong`.
        for x in bc.get("cat_hong_that") or []:
            loi.append("(a)+(c) `khoi_phuc()` NHẬN tệp dở LÀM KHÁC BẢN GỐC: %s" % x)
        # Chốt chống phép đo RỖNG. Đếm `so_luot_cat_khong_de_lai_tep` RIÊNG và cộng vào: một
        # bản vá fail-closed DỌN tệp tạm khi hỏng, nên "không còn tệp dở nào" là hành vi TỐT,
        # không phải kịch bản không chạy. Xem khối chú thích trong `kich_ban`.
        _cut = (bc.get("so_cach_tep_de_that_su_cut") or 0) + \
               (bc.get("so_luot_cat_khong_de_lai_tep") or 0)
        if _cut < 3:
            loi.append("PHÉP ĐO RỖNG: chỉ %s lượt cắt thật sự không sinh ra bản sao lưu trọn vẹn "
                       "(cần >= 3) — kịch bản cắt không chạy, đừng đọc kết quả này" % _cut)
        a = [c for c in (bc.get("cac_cach_cat") or []) if c.get("cach") == "a-het-cho-ghi"]
        if not a:
            loi.append("PHÉP ĐO THIẾU VẾ: kịch bản cắt vì hết chỗ ghi KHÔNG CHẠY")
        elif a[0].get("rc_luot_cat") == 0:
            loi.append("(a) `sao_luu()` hết chỗ ghi mà vẫn thoát 0")
        if not bg.get("c_dat"):
            loi.append("(c) CSDL nhận tệp dở KHÔNG khớp bản gốc: %s"
                       % "; ".join(bg.get("c_lech") or []))
        if not bc.get("doi_chung_duong_dat"):
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: tệp TRỌN VẸN mà khôi phục cũng lệch")

    elif ma == "S2":
        # Cùng nguyên tắc như S1: chỉ tính các bản sửa LÀM ĐỔI DỮ LIỆU. Ba trong năm chỗ lật
        # byte vào vùng trống — bản sao lưu vẫn ĐÚNG, nhận nó không phải lỗi.
        for x in bc.get("sua_hong_that") or []:
            loi.append("(a)+(c) `khoi_phuc()` NHẬN bản sửa LÀM KHÁC BẢN GỐC: %s" % x)
        if (bc.get("so_lan_sua") or 0) < 5:
            loi.append("PHÉP ĐO RỖNG: chỉ %s chỗ sửa được đo (cần 5)"
                       % (bc.get("so_lan_sua"),))
        if not bg.get("c_dat"):
            loi.append("(c) đích nhận bản sửa KHÔNG khớp bản gốc: %s"
                       % "; ".join(bg.get("c_lech") or []))
        if not bc.get("doi_chung_duong_dat"):
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: bản KHÔNG sửa mà khôi phục cũng lệch")

    elif ma == "S3":
        if bc.get("khoi_phuc_NHAN_tep_rong"):
            loi.append("(a) `khoi_phuc()` NHẬN tệp 0 byte (rc=0) — CSDL đích bị thay bằng một "
                       "CSDL RỖNG HỢP LỆ")
        if bc.get("integrity_tep_rong") != "ok":
            loi.append("chốt chống MỤC: tệp 0 byte mà `integrity_check` khác 'ok' (%r) — kịch "
                       "bản đã đổi, ĐỌC LẠI kết luận" % (bc.get("integrity_tep_rong"),))
        if bc.get("so_bang_tep_rong") not in (0, None):
            loi.append("chốt chống MỤC: tệp 0 byte mà có %s bảng — đo lại"
                       % (bc.get("so_bang_tep_rong"),))

    elif ma == "S4":
        # Khôi phục ĐÈ lên CSDL đã có dữ liệu. Bất biến KHÔNG phải "đích không đổi" (đè thành
        # công thì đích PHẢI đổi) mà là: dữ liệu TRƯỚC khi đè CÒN CỨU ĐƯỢC, và ba lượt trong
        # cùng một giây KHÔNG được xoá nhau.
        #
        # Câu hỏi đặt trên **MỌI** bản cất, không phải bản cuối theo thứ tự chữ cái: bản giữ dữ
        # liệu vừa mất là bản của lượt ĐẦU. Chỉ hỏi bản cuối là biến một bản vá ĐÚNG thành ĐỎ
        # GIẢ — xem khối chú thích trong `kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay`.
        if not bc.get("so_ban_cat_giu_du_lieu_goc"):
            loi.append("(c) KHÔNG bản cất nào giữ được dữ liệu lúc chụp: %s bản cất, băm dữ "
                       "liệu lúc chụp %s, băm các bản cất %s"
                       % (bc.get("so_ban_cat_sau_3_lan"), str(bc.get("bam_du_lieu_luc_chup_day"))[:16],
                          {k: str(v)[:12] for k, v in (bc.get("bam_moi_ban_cat_cuoi") or {}).items()}))
        if (bc.get("so_ban_cat_sau_3_lan") or 0) < 3 and (bc.get("so_ban_cat_sau_1_lan") or 0) == 1:
            loi.append("(c) 3 lượt khôi phục trong cùng một giây chỉ để lại %s bản cất — tên "
                       "đặt theo GIÂY nên lượt sau ĐÈ IM LẶNG lượt trước"
                       % (bc.get("so_ban_cat_sau_3_lan"),))
        if [bc.get("rc_kp1"), bc.get("rc_kp2"), bc.get("rc_kp3")] != [0, 0, 0]:
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: ba lượt khôi phục lành phải thoát 0, đo được %s"
                       % [bc.get("rc_kp1"), bc.get("rc_kp2"), bc.get("rc_kp3")])
        if (bc.get("so_ban_cat_sau_1_lan") or 0) != 1:
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: sau MỘT lượt khôi phục phải có ĐÚNG 1 bản cất, "
                       "đo được %s" % (bc.get("so_ban_cat_sau_1_lan"),))

    elif ma == "S5":
        if bc.get("phien_ban_sau_khoi_phuc") != bc.get("phien_ban_v9_truoc"):
            loi.append("(c) schema đã TỤT: v%s → v%s · %s bảng → %s bảng · tổng tiền %s → %s "
                       "(mất %s đồng)" % (bc.get("phien_ban_v9_truoc"),
                                          bc.get("phien_ban_sau_khoi_phuc"),
                                          bc.get("so_bang_v9_truoc"), bc.get("so_bang_sau"),
                                          bc.get("tong_tien_v9_truoc"), bc.get("tong_tien_v6"),
                                          (bc.get("tong_tien_v9_truoc") or 0)
                                          - (bc.get("tong_tien_v6") or 0)))
        if bc.get("rc_ghi_tren_v6") == 0 and bc.get("phien_ban_sau_khoi_phuc") != 9:
            loi.append("(c) sau khi tụt schema, hệ VẪN CHẠY được (rc=0) trên schema cũ — "
                       "không một lời cảnh báo")

    elif ma == "S6a":
        gia = bc.get("tep_moi_dung_duoc") or []
        if gia:
            loi.append("(c) để lại %d tệp MANG TÊN BẢN SAO LƯU mà vẫn 'dùng được' sau khi hỏng: %s"
                       % (len(gia), gia))
        if bc.get("so_tep_moi_de_lai"):
            loi.append("(c) để lại %d tệp dở trong `sao-luu/` và KHÔNG dọn: %s"
                       % (bc["so_tep_moi_de_lai"], bc.get("ten_tep_moi_de_lai")))

    elif ma == "S6b":
        pass  # đã phủ đủ bởi khuôn chung (a)(b)(c)

    elif ma == "S7":
        if bc.get("khoi_phuc_NHAN_tep_la"):
            loi.append("(a) `khoi_phuc()` NHẬN một tệp KHÔNG PHẢI SQLite (rc=0) và làm chết "
                       "CSDL đang chạy")
        if bc.get("loi_csdl_sau_khi_nham"):
            loi.append("(c) CSDL đích KHÔNG ĐỌC ĐƯỢC sau lượt nạp nhầm: %s"
                       % bc["loi_csdl_sau_khi_nham"])

    elif ma == "S8":
        # PostgreSQL: `sao_luu()` KHÔNG được BÁO THÀNH CÔNG với một đường lùi không chứa dữ liệu
        # đang chạy. Đây là khoảng trống P-G15-02.
        d1 = bc.get("do1_hub_db_khong_ton_tai") or {}
        d2 = bc.get("do2_hub_db_co_du_lieu_sqlite_khac") or {}
        d3 = bc.get("do3_khoi_phuc_tu_pg_dump") or {}
        pg = bc.get("pg_truoc") or {}
        pg_tien = pg.get("tong_tien")
        pg_dong = (pg.get("bang") or {}).get("don_hang", {}).get("dong")
        if d1.get("rc") == 0 and not (d1.get("so_bang") or 0):
            loi.append("(c) kho là PostgreSQL, `hub.db` KHÔNG tồn tại: `sao_luu()` thoát 0 và "
                       "trả một tệp %s byte / %s BẢNG / integrity=%r — trong khi PostgreSQL "
                       "đang giữ %s dòng và %s đồng. ĐƯỜNG LÙI GIẢ, và IM LẶNG"
                       % (d1.get("co_ban_sao"), d1.get("so_bang"), d1.get("integrity"),
                          pg_dong, pg_tien))
        if d2.get("rc") == 0 and d2.get("bam_ban_sao_khop_sqlite_goc") \
                and d2.get("ban_sao_tong_tien") != pg_tien:
            loi.append("(c) kho là PostgreSQL nhưng `hub.db` CŨ còn sót: `sao_luu()` trả một bản "
                       "sao TRÔNG HỢP LỆ (%s bảng, %s đồng) mà KHÔNG chứa một dòng nào của dữ "
                       "liệu đang chạy (%s đồng ở PostgreSQL)"
                       % (d2.get("ban_sao_so_bang"), d2.get("ban_sao_tong_tien"), pg_tien))
        if d3.get("khoi_phuc_NHAN"):
            loi.append("(a) `khoi_phuc()` NHẬN một bản `pg_dump -Fc` THẬT và làm chết CSDL "
                       "SQLite đang chạy")

    elif ma == "DC":
        # ĐỐI CHỨNG ĐƯỜNG: đường LÀNH phải ĐẠT. Một bộ đo chỉ biết nói ĐỎ thì vô dụng.
        if bg.get("rc") != 0:
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: khôi phục ngược lại chính CSDL gốc phải thoát 0, "
                       "đo được rc=%s" % bg.get("rc"))
        if not bg.get("c_dat"):
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: khôi phục ngược lại CSDL gốc KHÔNG y nguyên: %s"
                       % "; ".join(bg.get("c_lech") or []))
        if bc.get("so_lech_sau_khoi_phuc"):
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: %s lệch sau khôi phục"
                       % bc["so_lech_sau_khoi_phuc"])
        if not bc.get("so_lech_giua"):
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: ghi thêm dữ liệu mà phép so KHÔNG thấy lệch — "
                       "phép so đã chết, mọi kết luận 'khớp' ở trên là rỗng")
        if bc.get("tenant_sau_backup_con_lai") != 0:
            loi.append("ĐỐI CHỨNG ĐƯỜNG HỎNG: dữ liệu tạo SAU mốc sao lưu vẫn còn — khôi phục "
                       "không lùi được thời gian")

    else:
        loi.append("MÃ KỊCH BẢN KHÔNG NHẬN RA: %r — bản ghi này chưa có bất biến, KHÔNG được "
                   "tính là ĐẠT" % (ma,))
    return loi


def muc(bg):
    return "FAIL_CLOSED" if not phan_quyet(bg) else "FAIL_OPEN"


# ============================================================================
# S1 — SAO LƯU BỊ CẮT GIỮA ĐƯỜNG (đọc lại kịch bản AG-04 theo bất biến fail-closed)
# ============================================================================
def ca_sao_luu_cat_giua_duong():
    """Đọc lại kịch bản cắt của AG-04 theo bất biến fail-closed.

    ====== MỘT CHỖ TÔI CỐ Ý **KHÔNG** ĐẾM, VÀ NÓI RA ======
    Không phải mọi lượt cắt đều tạo ra một tệp HỎNG. Đo được: lượt `SIGKILL` ở 90% thời gian
    để lại một tệp **đủ byte, 51 bảng, 34.336.000 đồng** — tức bản sao lưu đã ghi xong trước khi
    tiến trình bị giết. `khoi_phuc()` NHẬN tệp đó là **ĐÚNG**, không phải lỗi.
    Nếu tôi đếm nó là lỗi thì con số "5/5 tệp dở bị nhận" nghe nặng hơn sự thật, và người sau
    sẽ mất niềm tin vào cả bảng. Nên ở đây tách làm hai danh sách:
        `cac_cach_cat` — mọi lượt cắt (số đo thô, không giấu gì);
        `cat_hong_that` — lượt cắt mà CSDL đích sau khi NHẬN **KHÁC bản gốc** ⇒ LỖI THẬT;
        `cat_vo_hai`   — lượt cắt mà tệp vẫn đủ ⇒ NHẬN là ĐÚNG, KHÔNG tính là lỗi.
    Bất biến chỉ tính trên `cat_hong_that`.
    """
    kq = kich_ban.ca_sao_luu_cat_giua_duong()
    sb, tt = kq["so_bang_goc"], kq["tong_tien_goc"]
    lech, vo_hai = [], []
    for c in kq["cac_cach_cat"]:
        s = c.get("csdl_sau") or {}
        if not c["khoi_phuc_NHAN"]:
            continue
        mo_ta = ("%s: đích nhận tệp dở → %s bảng (gốc %s) · %s đồng (gốc %s) · %s"
                 % (c["cach"], s.get("so_bang"), sb, s.get("tong_tien"), tt,
                    s.get("loi") or "integrity=%s" % s.get("integrity")))
        if s.get("loi") or s.get("so_bang") != sb or s.get("tong_tien") != tt:
            lech.append(mo_ta)
        else:
            vo_hai.append("%s: tệp đủ byte và khớp gốc (%s bảng · %s đồng) — NHẬN là ĐÚNG"
                          % (c["cach"], s.get("so_bang"), s.get("tong_tien")))
    return _ghi("S1", "1. SAO LƯU BỊ CẮT GIỮA ĐƯỜNG (5 cách cắt)",
                "mọi tệp dở LÀM KHÁC BẢN GỐC phải bị `khoi_phuc()` TỪ CHỐI · lượt cắt vì hết "
                "chỗ ghi phải rc != 0",
                kq["doi_chung_duong"]["rc_khoi_phuc"], "", "", not lech, lech,
                {"cac_cach_cat": [{"cach": c["cach"], "rc_luot_cat": c.get("rc_luot_cat"),
                                   "co_tep_de": c.get("co_tep_de"),
                                   "khoi_phuc_NHAN": c["khoi_phuc_NHAN"],
                                   "rc_khoi_phuc": c["rc_khoi_phuc"],
                                   "err_khoi_phuc": c.get("err_khoi_phuc"),
                                   "integrity_tep_de": (c.get("chup_tep_de") or {}).get("integrity_check"),
                                   "so_bang_tep_de": (c.get("chup_tep_de") or {}).get("so_bang"),
                                   "csdl_sau_so_bang": (c.get("csdl_sau") or {}).get("so_bang"),
                                   "csdl_sau_tong_tien": (c.get("csdl_sau") or {}).get("tong_tien"),
                                   "csdl_sau_loi": (c.get("csdl_sau") or {}).get("loi")}
                                  for c in kq["cac_cach_cat"]],
                 "so_cach_bi_NHAN": kq["so_cach_bi_NHAN"],
                 "so_cach_tep_de_that_su_cut": kq["so_cach_tep_de_that_su_cut"],
                 "so_luot_cat_khong_de_lai_tep": kq.get("so_luot_cat_khong_de_lai_tep"),
                 "cat_hong_that": lech, "so_cat_hong_that": len(lech),
                 "cat_vo_hai": vo_hai, "so_cat_vo_hai": len(vo_hai),
                 "doi_chung_duong": kq["doi_chung_duong"],
                 "doi_chung_duong_dat": kq["doi_chung_duong_dat"],
                 "so_bang_goc": sb, "tong_tien_goc": tt,
                 "nguon_ve_c": "từng cách cắt có `csdl_sau` (số bảng + tổng tiền) do chính kịch "
                               "bản AG-04 đo; đối chiếu với `so_bang_goc`/`tong_tien_goc`.",
                 "ghi_chu": "phép so ở đây là số bảng + tổng tiền toàn kho, KHÔNG phải từng bảng: "
                            "kịch bản AG-04 không giữ phép chụp đầy đủ của CSDL đích. Nói ra để "
                            "không ai đọc thành 'đã so từng bảng'."})


# ============================================================================
# S2 — TỆP SAO LƯU BỊ SỬA 1 BYTE
# ============================================================================
def ca_sua_mot_byte():
    """Đọc lại kịch bản sửa-1-byte của AG-04 theo bất biến fail-closed.

    Cùng lý do như `S1`: KHÔNG phải mọi byte bị lật đều làm hỏng bản sao lưu. Đo được: ba chỗ
    theo tỉ lệ (25/50/75%) rơi vào vùng trang TRỐNG nên dữ liệu KHÔNG đổi (`bam_khop_goc=True`,
    `so_lech=0`, `integrity=ok`) — `khoi_phuc()` nhận chúng là ĐÚNG. Chỉ hai chỗ làm ĐỔI DỮ LIỆU
    thật: byte đầu của mã đơn trong trang đang dùng, và byte 0 (magic tệp). Bất biến chỉ tính
    trên hai chỗ đó. Đếm cả năm là thổi phồng con số.
    """
    kq = kich_ban.ca_sua_mot_byte()
    lech, vo_hai = [], []
    for c in kq["cac_lan_sua"]:
        if c["rc_khoi_phuc"] != 0:
            continue
        mo_ta = ("%s: đích nhận bản sửa → băm khớp gốc=%s · %s lệch · %s"
                 % (c["nhan"], c.get("bam_khop_goc"), c.get("so_lech"),
                    c.get("integrity") or c.get("loi")))
        if (not c.get("bam_khop_goc")) or c.get("so_lech") or c.get("loi") \
                or c.get("integrity") != "ok":
            lech.append(mo_ta)
        else:
            vo_hai.append("%s: byte lật vào vùng không dùng — dữ liệu KHÔNG đổi "
                          "(băm khớp gốc, 0 lệch) ⇒ NHẬN là ĐÚNG" % (c["nhan"],))
    return _ghi("S2", "2. TỆP SAO LƯU BỊ SỬA 1 BYTE (5 chỗ)",
                "mọi bản sửa LÀM KHÁC BẢN GỐC phải bị `khoi_phuc()` TỪ CHỐI · đối chứng đường "
                "tệp KHÔNG sửa ĐẠT",
                kq["doi_chung_duong"]["rc_khoi_phuc"], "", "", not lech, lech,
                {"cac_lan_sua": [{"nhan": c["nhan"], "vi_tri": c.get("vi_tri"),
                                  "sqlite_tu_bao": c.get("sqlite_tu_bao"),
                                  "bam_khop_goc": c.get("bam_khop_goc"),
                                  "rc_khoi_phuc": c.get("rc_khoi_phuc"),
                                  "err_khoi_phuc": c.get("err_khoi_phuc"),
                                  "so_lech": c.get("so_lech"),
                                  "integrity": c.get("integrity"), "loi": c.get("loi")}
                                 for c in kq["cac_lan_sua"]],
                 "so_lan_khoi_phuc_NHAN_tat_ca": kq["so_lan_khoi_phuc_NHAN_tat_ca"],
                 "so_lan_sua": len(kq["cac_lan_sua"]),
                 "sua_hong_that": lech, "so_sua_hong_that": len(lech),
                 "sua_vo_hai": vo_hai, "so_sua_vo_hai": len(vo_hai),
                 "doi_chung_duong": kq.get("doi_chung_duong"),
                 "doi_chung_duong_dat": kq.get("doi_chung_duong_dat"),
                 "nguon_ve_c": "từng bản sửa có `bam_khop_goc` + `so_lech` (so TỪNG BẢNG cả số "
                               "dòng lẫn tổng tiền) do chính kịch bản AG-04 đo.",
                 "ghi_chu": "cùng lý do như S1: `khoi_phuc()` NHẬN bản đã sửa MÀ DỮ LIỆU KHÁC "
                            "nghĩa là CSDL đích bị thay bằng chính bản đó."})


# ============================================================================
# S3 — TỆP SAO LƯU RỖNG 0 BYTE (AG-04 chỉ đo lẫn trong kịch bản cắt; đây đo RIÊNG)
# ============================================================================
def ca_khoi_phuc_tep_rong_0_byte():
    """Đưa `khoi_phuc()` một tệp 0 byte — thứ `sao_luu()` có thể để lại khi hết đĩa.

    Vì sao phải đo RIÊNG: tệp SQLite dài 0 byte LÀ một CSDL rỗng HỢP LỆ. `PRAGMA
    integrity_check` trả **"ok"** cho nó. Nghĩa là một bước "kiểm bản sao lưu bằng
    integrity_check" — cách kiểm ai cũng nghĩ tới trước tiên — KHÔNG bắt được ca này. Bất biến
    đúng phải là SỐ BẢNG (hoặc số byte), và ca này chứng minh đúng điều đó bằng số.
    """
    with kich_ban.Nen("g21-teprong") as n:
        A = n.duong("A")
        rc_gieo, _, err_gieo = kich_ban.gieo(A)
        duong_db = kich_ban.db(A)
        truoc = khung_do.chup(duong_db)
        rong = os.path.join(n.goc, "ban-sao-luu-0-byte.db")
        with open(rong, "wb"):
            pass
        if os.path.getsize(rong) != 0:
            raise AssertionError("không tạo được tệp 0 byte — phép đo vô nghĩa")
        chup_rong = khung_do.chup(rong)
        kp = kich_ban.khoi_phuc(A, rong)
        sau = khung_do.chup(duong_db)
        return _ghi("S3", "3. TỆP SAO LƯU RỖNG 0 BYTE",
                    "rc != 0 · thông báo nói ra tệp rỗng · CSDL đích KHÔNG bị thay bằng CSDL rỗng",
                    kp["rc"], kp["out"], kp["err"],
                    not so_lech_hai_chup(truoc, sau), so_lech_hai_chup(truoc, sau),
                    {"rc_gieo": rc_gieo, "loi_gieo": err_gieo[-200:],
                     "so_byte_tep_rong": os.path.getsize(rong),
                     "integrity_tep_rong": chup_rong.get("integrity_check"),
                     "so_bang_tep_rong": chup_rong.get("so_bang"),
                     "khoi_phuc_NHAN_tep_rong": kp["rc"] == 0,
                     "so_bang_goc": truoc.get("so_bang"),
                     "tong_tien_goc": truoc.get("tong_tien_toan_kho")},
                    truoc, sau)


# ============================================================================
# S4 — KHÔI PHỤC ĐÈ LÊN CSDL ĐÃ CÓ DỮ LIỆU
# ============================================================================
def ca_khoi_phuc_de_len_csdl_dang_chay():
    kq = kich_ban.ca_khoi_phuc_de_len_csdl_dang_chay()
    nc = kq.get("noi_dung_ban_cat") or {}
    return _ghi("S4", "4. KHÔI PHỤC ĐÈ LÊN CSDL ĐÃ CÓ DỮ LIỆU",
                "dữ liệu TRƯỚC khi đè phải CÒN CỨU ĐƯỢC · ba lượt cùng một giây KHÔNG xoá nhau",
                kq["rc_kp1"], "", "", None, [],
                {"rc_gieo": kq["rc_gieo"], "rc_sao_luu": kq["rc_sao_luu"], "rc_them": kq["rc_them"],
                 "rc_kp1": kq["rc_kp1"], "rc_kp2": kq["rc_kp2"], "rc_kp3": kq["rc_kp3"],
                 "so_ban_cat_sau_1_lan": kq["so_ban_cat_sau_1_lan"],
                 "so_ban_cat_sau_3_lan": kq["so_ban_cat_sau_3_lan"],
                 "ban_cat": kq["ban_cat"],
                 "bam_ban_cat_sau_1_lan": kq["bam_ban_cat_sau_1_lan"],
                 "bam_ban_cat_sau_3_lan": kq["bam_ban_cat_sau_3_lan"],
                 "bam_du_lieu_luc_chup_day": kq["bam_du_lieu_luc_chup_day"],
                 "ban_cat_con_giu_duoc_du_lieu_goc": kq["ban_cat_con_giu_duoc_du_lieu_goc"],
                 "ban_cat_khop_du_lieu_luc_chup": bool(nc.get("khop_dung_luc_chup_day")),
         "bam_moi_ban_cat_cuoi": kq.get("bam_moi_ban_cat_cuoi"),
         "so_ban_cat_giu_du_lieu_goc": kq.get("so_ban_cat_giu_du_lieu_goc"),
                 "ban_cat_integrity": nc.get("integrity"), "ban_cat_so_bang": nc.get("so_bang"),
                 "lech_truoc_kp1": kq.get("lech_truoc_kp1"),
                 "nguon_ve_c": "bất biến của S4 KHÔNG phải 'đích không đổi' (khôi phục đè thành "
                               "công thì đích PHẢI đổi) mà là 'dữ liệu trước khi đè còn cứu "
                               "được': so băm bản cất với băm dữ liệu lúc chụp."})


# ============================================================================
# S5 — KHÔI PHỤC BẢN SCHEMA THẤP HƠN
# ============================================================================
def ca_khoi_phuc_schema_thap_hon():
    kq = kich_ban.ca_khoi_phuc_schema_thap_hon()
    lech = []
    if kq["phien_ban_sau_khoi_phuc"] != kq["phien_ban_v9_truoc"]:
        lech.append("phiên bản %s → %s" % (kq["phien_ban_v9_truoc"],
                                           kq["phien_ban_sau_khoi_phuc"]))
    if (kq.get("chup_sau") or {}).get("so_bang") != kq["so_bang_v9_truoc"]:
        lech.append("số bảng %s → %s" % (kq["so_bang_v9_truoc"],
                                         (kq.get("chup_sau") or {}).get("so_bang")))
    # TỔNG TIỀN **SAU** KHI KHÔI PHỤC, không phải tổng tiền của bản sao lưu v6. So
    # `tong_tien_v6` với `tong_tien_v9_truoc` là so hai con số KHÁC NHAU THEO THIẾT KẾ của
    # kịch bản — nó luôn "lệch", kể cả khi lượt khôi phục đã bị TỪ CHỐI và CSDL đích còn nguyên.
    # Đó là một ĐỎ GIẢ; đo được 16/10/2026 trên bản đã vá.
    if (kq.get("chup_sau") or {}).get("tong_tien") != kq["tong_tien_v9_truoc"]:
        lech.append("tổng tiền %s → %s" % (kq["tong_tien_v9_truoc"],
                                           (kq.get("chup_sau") or {}).get("tong_tien")))
    return _ghi("S5", "5. KHÔI PHỤC BẢN SCHEMA THẤP HƠN (v6 đè lên v9)",
                "rc != 0 (TỪ CHỐI) · thông báo nêu hai phiên bản · schema KHÔNG tụt im lặng",
                kq["rc_khoi_phuc"], kq["out_khoi_phuc"], kq.get("err_khoi_phuc") or "",
                not lech, lech,
                {"rc_dung_v6": kq["rc_dung_v6"], "phien_ban_v6": kq["phien_ban_v6"],
                 "so_bang_v6": kq["so_bang_v6"], "phien_ban_v9_truoc": kq["phien_ban_v9_truoc"],
                 "so_bang_v9_truoc": kq["so_bang_v9_truoc"],
                 "phien_ban_sau_khoi_phuc": kq["phien_ban_sau_khoi_phuc"],
                 "so_bang_sau": (kq.get("chup_sau") or {}).get("so_bang"),
                 "tong_tien_v6": kq["tong_tien_v6"], "tong_tien_v9_truoc": kq["tong_tien_v9_truoc"],
                 "rc_ghi_tren_v6": kq["rc_ghi_tren_v6"], "rc_nang_lai": kq["rc_nang_lai"],
                 "nguon_ve_c": "`chup_sau` của kịch bản có phiên bản + số bảng + tổng tiền; so "
                               "với `so_bang_v9_truoc`/`tong_tien_v9_truoc` đo trước khi đè."})


# ============================================================================
# S6a — HẾT ĐĨA GIỮA ĐƯỜNG KHI **SAO LƯU**
# ============================================================================
def ca_het_dia_khi_sao_luu():
    """`RLIMIT_FSIZE = 40% CSDL` trong lúc `sao_luu()`. Hỏi: mã thoát, thông báo, tệp còn lại.

    Điểm mấu chốt KHÔNG phải "nó có ném lỗi không" (ném thì tốt) mà là **cái gì còn lại trên
    đĩa**. Một tệp dở mang đúng tên `hub-truoc-migrate-*.db` là một ĐƯỜNG LÙI GIẢ: người trực
    thấy có tệp, tin là có đường lùi, và chỉ phát hiện khi đã quá muộn.
    """
    with kich_ban.Nen("g21-hetdia-sl") as n:
        A = n.duong("A")
        rc_gieo, _, err_gieo = kich_ban.gieo(A)
        duong_db = kich_ban.db(A)
        truoc = khung_do.chup(duong_db)
        co_db = os.path.getsize(duong_db)
        da_co = set(kich_ban.liet_ke_sao_luu(A))
        gioi_han = int(co_db * 0.40)
        rc, out, err = chay_con_gioi_han_ghi(kich_ban._MA_SAO_LUU, A, gioi_han)
        moi = sorted(set(kich_ban.liet_ke_sao_luu(A)) - da_co)
        tep_moi, dung_duoc = [], []
        for t in moi:
            p = os.path.join(kich_ban.thu_muc_sao_luu(A), t)
            c = khung_do.chup(p) if t.endswith(".db") else {"loi": "(không phải .db)"}
            g = {"ten": t, "so_byte": c.get("so_byte"), "so_bang": c.get("so_bang"),
                 "integrity": c.get("integrity_check"), "loi": c.get("loi"),
                 "bam_toan_kho": str(c.get("bam_toan_kho"))[:16]}
            g["dung_duoc"] = bool(c.get("integrity_check") == "ok"
                                  and (c.get("so_bang") or 0) >= (truoc.get("so_bang") or 10 ** 9))
            tep_moi.append(g)
            if g["dung_duoc"]:
                dung_duoc.append(t)
        sau = khung_do.chup(duong_db)
        return _ghi("S6a", "6a. HẾT ĐĨA GIỮA ĐƯỜNG khi SAO LƯU",
                    "rc != 0 · thông báo nói ra chỗ hỏng · CSDL NGUỒN nguyên · KHÔNG để lại tệp "
                    "dở mang tên bản sao lưu",
                    rc, out, err, not so_lech_hai_chup(truoc, sau),
                    so_lech_hai_chup(truoc, sau),
                    {"rc_gieo": rc_gieo, "loi_gieo": err_gieo[-200:],
                     "co_csdl_goc": co_db, "gioi_han_ghi": gioi_han,
                     "ty_le_gioi_han": round(gioi_han / float(co_db), 3),
                     "tep_da_co_truoc": sorted(da_co), "tep_moi_de_lai": tep_moi,
                     "so_tep_moi_de_lai": len(moi), "ten_tep_moi_de_lai": moi,
                     "tep_moi_dung_duoc": dung_duoc,
                     "nguon_ve_c": "CSDL NGUỒN chụp TRƯỚC/SAU bằng `khung_do.chup` → so từng "
                                   "bảng (số dòng + tổng tiền). CSDL ĐÍCH ở đây chính là nguồn: "
                                   "một lượt sao lưu không được đụng vào nó."},
                    truoc, sau)


# ============================================================================
# S6b — HẾT ĐĨA GIỮA ĐƯỜNG KHI **KHÔI PHỤC**   (ca nặng nhất)
# ============================================================================
def ca_het_dia_khi_khoi_phuc():
    """`RLIMIT_FSIZE` rơi ĐÚNG VÀO lúc `khoi_phuc()` đang chép bản sao lưu lên CSDL đang chạy.

    CÁCH DỰNG ĐỂ RƠI ĐÚNG CHỖ — chỗ dễ đo sai nhất, nên nói rõ:
    `khoi_phuc()` chép HAI lần. Lần 1: CSDL hiện tại → `hub-truoc-rollback-*.db` (bản cất).
    Lần 2: bản sao lưu → CSDL hiện tại (lượt đè). Muốn giới hạn rơi vào LẦN 2 thì phải có
        co(CSDL đích) < giới hạn < co(bản sao lưu).
    Nên: CSDL đích là một CSDL MỚI (ít dữ liệu, nhỏ), bản sao lưu là bản ĐẦY ĐỦ (lớn), giới hạn
    đặt giữa hai con số đó. `tien_quyet_dat` ghi lại bất đẳng thức này — thiếu nó thì một lượt
    đo "trượt chỗ" vẫn cho ra một con số trông như thật.
    """
    with kich_ban.Nen("g21-hetdia-kp") as n:
        A = n.duong("A")
        rc_gieo, _, err_gieo = kich_ban.gieo(A)
        sl = kich_ban.sao_luu(A)
        ban_sao = sl.get("duong") or ""
        co_ban_sao = os.path.getsize(ban_sao) if os.path.exists(ban_sao) else 0
        chup_nguon = khung_do.chup(kich_ban.db(A))

        B = n.duong("B")
        rc_mo, out_mo, err_mo = kich_ban.chay_con(
            "import sys; sys.path.insert(0, %r); import csdl; csdl.mo(); print('ok')" % APP, B)
        duong_B = kich_ban.db(B)
        co_B = os.path.getsize(duong_B) if os.path.exists(duong_B) else 0
        chup_B_truoc = khung_do.chup(duong_B)

        gioi_han = int(co_ban_sao * 0.5)
        tien_quyet = (0 < co_B < gioi_han < co_ban_sao)
        if not tien_quyet:
            raise AssertionError(
                "PHÉP ĐO KHÔNG DỰNG ĐƯỢC: cần co(CSDL đích)=%s < giới hạn=%s < co(bản sao lưu)=%s "
                "để giới hạn rơi vào LẦN CHÉP THỨ HAI. Sửa kịch bản, ĐỪNG đọc kết quả này."
                % (co_B, gioi_han, co_ban_sao))

        rc, out, err = chay_con_gioi_han_ghi(kich_ban._MA_KHOI_PHUC, B, gioi_han,
                                             {"G20_SAO_LUU": ban_sao})
        chup_B_sau = khung_do.chup(duong_B)
        ban_cat = [t for t in kich_ban.liet_ke_sao_luu(B) if t.startswith("hub-truoc-rollback-")]
        chup_ban_cat = {}
        for t in ban_cat:
            c = khung_do.chup(os.path.join(kich_ban.thu_muc_sao_luu(B), t))
            chup_ban_cat[t] = {"so_byte": c.get("so_byte"), "so_bang": c.get("so_bang"),
                               "integrity": c.get("integrity_check"), "loi": c.get("loi")}
        lech = so_lech_hai_chup(chup_B_truoc, chup_B_sau)
        return _ghi("S6b", "6b. HẾT ĐĨA GIỮA ĐƯỜNG khi KHÔI PHỤC",
                    "rc != 0 · thông báo nói ra chỗ hỏng · CSDL ĐÍCH không bị để lại nửa vời",
                    rc, out, err, not lech, lech,
                    {"rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "rc_mo_csdl_dich": rc_mo,
                     "loi_mo_csdl_dich": err_mo[-200:], "out_mo_csdl_dich": out_mo.strip()[-120:],
                     "ban_sao": ban_sao, "co_ban_sao": co_ban_sao, "co_csdl_dich": co_B,
                     "gioi_han_ghi": gioi_han, "tien_quyet_dat": tien_quyet,
                     "vi_tri_gioi_han": "co(đích)=%s < giới hạn=%s < co(bản sao lưu)=%s ⇒ rơi vào "
                                        "LẦN CHÉP THỨ HAI" % (co_B, gioi_han, co_ban_sao),
                     "so_bang_nguon": chup_nguon.get("so_bang"),
                     "tong_tien_nguon": chup_nguon.get("tong_tien_toan_kho"),
                     "ban_cat_de_lai": ban_cat, "chup_ban_cat": chup_ban_cat,
                     "so_bang_csdl_dich_truoc": chup_B_truoc.get("so_bang"),
                     "tong_tien_csdl_dich_truoc": chup_B_truoc.get("tong_tien_toan_kho")},
                    chup_B_truoc, chup_B_sau)


# ============================================================================
# S7 — KHÔI PHỤC NHẦM TỆP KHÔNG PHẢI SQLITE
# ============================================================================
def ca_khoi_phuc_nham_ban_dump_pg():
    kq = kich_ban.ca_khoi_phuc_nham_ban_dump_pg()
    sau = kq["csdl_sau_khi_nham"]
    lech = []
    if sau.get("loi"):
        lech.append("CSDL đích không đọc được: %s" % sau["loi"])
    if sau.get("so_bang") in (None, 0):
        lech.append("số bảng đọc được = %s" % (sau.get("so_bang"),))
    if sau.get("so_byte") != kq["so_byte_csdl_truoc"]:
        lech.append("số byte %s → %s" % (kq["so_byte_csdl_truoc"], sau.get("so_byte")))
    return _ghi("S7", "7. KHÔI PHỤC NHẦM TỆP KHÔNG PHẢI SQLITE (bản dump PostgreSQL)",
                "rc != 0 (TỪ CHỐI) · thông báo nói tệp không phải SQLite · CSDL đích nguyên vẹn",
                kq["rc_khoi_phuc_nham"], kq["out_khoi_phuc_nham"], kq["err_khoi_phuc_nham"],
                not lech, lech,
                {"rc_gieo": kq["rc_gieo"], "rc_sao_luu_dung": kq["rc_sao_luu_dung"],
                 "khoi_phuc_NHAN_tep_la": kq["khoi_phuc_NHAN_tep_la"],
                 "csdl_sau_khi_nham": sau,
                 "loi_csdl_sau_khi_nham": sau.get("loi"),
                 "so_byte_csdl_truoc": kq["so_byte_csdl_truoc"],
                 "so_byte_csdl_sau": kq["so_byte_csdl_sau"],
                 "doi_chung_duong_dat": kq["doi_chung_duong_dat"],
                 "so_lech_duong_dung": kq["so_lech_duong_dung"],
                 "nguon_ve_c": "`csdl_sau_khi_nham` (integrity/loi/so_bang/so_byte) do kịch bản "
                               "AG-04 đo, so với `so_byte_csdl_truoc` + `bam_truoc`."})


# ============================================================================
# S8 — POSTGRESQL (khoảng trống P-G15-02)
# ============================================================================
def ca_postgresql():
    """`migrate.sao_luu()` khi dữ liệu nghiệp vụ nằm ở PostgreSQL. Cụm RIÊNG, TỪ CHỐI :5432."""
    import do_postgres
    kq = do_postgres.chay()
    if kq.get("bo_qua"):
        raise RuntimeError("BỎ QUA kịch bản PostgreSQL — %s" % kq["bo_qua"])
    d1 = kq.get("do1_hub_db_khong_ton_tai") or {}
    return _ghi("S8", "8. POSTGRESQL: `sao_luu()` có phải đường lùi THẬT không (P-G15-02)",
                "`sao_luu()` không được thoát 0 với một bản sao KHÔNG chứa dữ liệu đang chạy",
                d1.get("rc"), "", "", None, [], kq)


# ============================================================================
# DC — ĐỐI CHỨNG ĐƯỜNG: sao lưu rồi khôi phục NGƯỢC LẠI CHÍNH CSDL GỐC
# ============================================================================
def ca_doi_chung_duong():
    """Bất biến: khôi phục ngược lại chính CSDL gốc phải cho kết quả Y NGUYÊN.

    Vì sao đây là ca quan trọng nhất trong tệp: nếu đường LÀNH cũng không y nguyên thì mọi kết
    luận "hỏng ở đường X" ở trên đều vô nghĩa — bộ đo đang đo một hệ hỏng sẵn.
    """
    kq = kich_ban.ca_doi_chung_duong()
    chup_truoc, chup_sau = kq.get("_truoc"), kq.get("_sau")
    lech = so_lech_hai_chup(chup_truoc, chup_sau) if (chup_truoc and chup_sau) else []
    return _ghi("DC", "ĐC. ĐỐI CHỨNG ĐƯỜNG — sao lưu rồi khôi phục lại chính CSDL gốc",
                "rc == 0 · CSDL gốc Y NGUYÊN từng bảng (số dòng + tổng tiền) · dữ liệu tạo sau "
                "mốc sao lưu mất hết",
                kq["rc_khoi_phuc"], "", "", not lech, lech,
                {"rc_gieo": kq["rc_gieo"], "rc_sao_luu": kq["rc_sao_luu"], "rc_them": kq["rc_them"],
                 "so_lech_giua": kq["so_lech_giua"], "vi_du_lech_giua": kq["vi_du_lech_giua"][:4],
                 "so_lech_sau_khoi_phuc": kq["so_lech_sau_khoi_phuc"],
                 "lech_sau_khoi_phuc": kq["lech_sau_khoi_phuc"][:8],
                 "tenant_sau_backup_con_lai": kq["tenant_sau_backup_con_lai"],
                 "ban_truoc_khoi_phuc": kq["ban_truoc_khoi_phuc"],
                 "so_bang_goc": (chup_truoc or {}).get("so_bang"),
                 "tong_tien_goc": (chup_truoc or {}).get("tong_tien_toan_kho"),
                 "co_chup_truoc_sau": bool(chup_truoc and chup_sau),
                 "nguon_ve_c": "`_truoc`/`_sau` của kịch bản là hai phép chụp `khung_do` ĐẦY ĐỦ "
                               "(từng bảng: số dòng + từng cột tiền) trước và sau khi khôi phục."},
                chup_truoc, chup_sau)


# ============================================================================
# CHẠY TẤT CẢ
# ============================================================================
# Thứ tự CỐ ĐỊNH để bảng in ra và bảng trong báo cáo luôn khớp nhau.
THU_TU = ("S1", "S2", "S3", "S4", "S5", "S6a", "S6b", "S7", "S8", "DC")

HAM = {
    "S1": ca_sao_luu_cat_giua_duong,
    "S2": ca_sua_mot_byte,
    "S3": ca_khoi_phuc_tep_rong_0_byte,
    "S4": ca_khoi_phuc_de_len_csdl_dang_chay,
    "S5": ca_khoi_phuc_schema_thap_hon,
    "S6a": ca_het_dia_khi_sao_luu,
    "S6b": ca_het_dia_khi_khoi_phuc,
    "S7": ca_khoi_phuc_nham_ban_dump_pg,
    "S8": ca_postgresql,
    "DC": ca_doi_chung_duong,
}


def chay_tat_ca(bo_qua=(), chi=None):
    """Chạy kịch bản. `chi` = chạy ĐÚNG danh sách mã này (dùng cho lượt tiêm lỗi, cho nhanh).

    Không nuốt lỗi kịch bản: một kịch bản ném thì lượt chạy HỎNG ỒN ÀO, không bị bỏ qua im lặng.
    """
    ra, bo = {}, {}
    for ma in THU_TU:
        if chi is not None and ma not in chi:
            continue
        if ma in bo_qua:
            bo[ma] = "bỏ qua theo yêu cầu của chỗ gọi"
            continue
        ra[ma] = HAM[ma]()
    return {"ban_ghi": ra, "bo_qua": bo, "app": APP,
            "thu_tu": [m for m in THU_TU if m in ra]}


def in_bang(kq):
    print("=" * 104)
    print(" G21 / AG-02 — FAIL-CLOSED CỦA SAO LƯU → KHÔI PHỤC")
    print(" app/ đang đo : %s" % kq["app"])
    print("=" * 104)
    print("%-5s %-50s %-6s %-12s %s" % ("MÃ", "KỊCH BẢN", "RC", "PHÁN QUYẾT", "CSDL ĐÍCH SAU"))
    for ma in THU_TU:
        b = kq["ban_ghi"].get(ma)
        if b is None:
            print("%-5s %-50s %-6s %-12s %s" % (ma, "(bỏ qua)", "-", "-", kq["bo_qua"].get(ma)))
            continue
        s = b["csdl_dich_sau"]
        if not s.get("ton_tai"):
            tt = "(kịch bản này không chụp CSDL đích)"
        elif s.get("loi"):
            tt = "%s byte · KHÔNG ĐỌC ĐƯỢC: %s" % (s.get("so_byte"), str(s["loi"])[:40])
        else:
            tt = "%s byte · %s bảng · integrity %s · %s đồng" % (
                s.get("so_byte"), s.get("so_bang"), s.get("integrity"), s.get("tong_tien"))
        print("%-5s %-50s %-6s %-12s %s" % (ma, b["ten"][:50], b["rc"], muc(b), tt))
    print("-" * 104)
    print(" CHI TIẾT TỪNG VẾ: (a) mã thoát · (b) thông báo · (c) CSDL đích")
    for ma in THU_TU:
        b = kq["ban_ghi"].get(ma)
        if b is None:
            continue
        print("\n[%s] %s" % (ma, b["ten"]))
        print("    bắt buộc     : %s" % b["bat_buoc"])
        print("    (a) rc       : %s" % b["rc"])
        print("    (b) thông báo: có=%s · traceback trần=%s | %s"
              % (b["co_dong_bao_hong"], b["la_traceback_tho"], b["dong_bao_hong"][:150]))
        print("    (c) đích     : %s"
              % (json.dumps(b["csdl_dich_sau"], ensure_ascii=False, default=str)[:150]))
        for x in (b["c_lech"] or [])[:8]:
            print("        lệch     : %s" % x)
        for x in phan_quyet(b):
            print("        LỖI      : %s" % x)
    print("\n" + "=" * 104)
    co = [m for m in THU_TU if kq["ban_ghi"].get(m)]
    n_ok = sum(1 for m in co if not phan_quyet(kq["ban_ghi"][m]))
    print(" KẾT LUẬN: %d/%d kịch bản FAIL_CLOSED · %d FAIL_OPEN"
          % (n_ok, len(co), len(co) - n_ok))
    print("=" * 104)
    return 0 if n_ok == len(co) else 1


def main(argv):
    bo_qua = ("S8",) if "--nhanh" in argv else ()
    kq = chay_tat_ca(bo_qua=bo_qua)
    if "--json" in argv:
        i = argv.index("--json")
        if len(argv) > i + 1:
            with open(argv[i + 1], "w", encoding="utf-8") as f:
                json.dump(kq, f, ensure_ascii=False, indent=1, default=str)
    return in_bang(kq)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
