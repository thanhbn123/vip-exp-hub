#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — BẢN VÁ **ĐÃ ÁP** VÀO `app/migrate.py`, VÀ BỐN PHÉP TIÊM LỖI ĐỐI CHỨNG.

====== LƯỢT TRƯỚC VÀ LƯỢT NÀY KHÁC NHAU Ở ĐÚNG MỘT CHỖ ======
Lượt trước bản vá **chưa được áp**: mô-đun này DỰNG RA một `app/` ứng viên trong thư mục tạm
(mọi tệp là symlink trỏ về cây thật, riêng `migrate.py` là bản dựng tại chỗ) rồi chạy bộ đo
trên đó. Kết quả 9/10 FAIL_CLOSED khi đó là kết quả **TRÊN BẢN SAO** — nó chứng minh bản vá
ĐÚNG, nhưng không chứng minh TỆP THẬT đúng.

Lượt này bản vá **đã nằm trong `app/migrate.py`**. Nên:

  * `ban_va` KHÔNG còn là một bản dựng — nó là **CHÍNH `app/migrate.py`**, đọc từ đĩa, và mọi
    phép đo của lượt này chạy trên tệp đó. `dung_bien_the()` chép NGUYÊN VĂN tệp thật vào thư
    mục ứng viên và `xac_nhan()` từ chối chạy nếu tệp thật thiếu bất kỳ mảnh mã nào của bản vá.
    Nhờ vậy "đo trên bản vá" là một khẳng định KIỂM ĐƯỢC, không phải một lời hứa.
  * `goc` là bản **ĐÓNG BĂNG** của tệp trước khi vá: `migrate_nguyenban.py`, lấy từ
    `git show HEAD:app/migrate.py` (md5 khớp từng byte với tệp thật ngay trước lượt vá — có
    in ra ở `main()`). Không có nó thì bảng "TRƯỚC / SAU" không dựng lại được sau khi đã vá.

====== VÌ SAO PHẢI CÓ BỐN PHÉP TIÊM ======
"Mọi kịch bản đều FAIL_CLOSED" chỉ có nghĩa khi bộ đo **PHÂN BIỆT ĐƯỢC**. Bốn phép tiêm dưới
đây gỡ **ĐÚNG MỘT** chốt khỏi bản vá, mỗi phép có một kịch bản PHẢI bắt được nó. Phép thay phải
KHỚP TỪNG KÝ TỰ — không khớp thì NÉM, chứ không im lặng bỏ qua: một phép tiêm "trượt" mà vẫn
chạy tiếp là kiểu hỏng tệ nhất, vì bộ đo sẽ báo ĐỎ trên một bản vá còn nguyên và người đọc
tưởng bộ đo có răng.

====== MỘT PHÉP TIÊM TÔI ĐÃ BỎ, VÀ VÌ SAO — ghi lại để người sau không thêm lại ======
Tôi đã định tiêm "gỡ chốt bắt buộc DẤU KIỂM `.sha256`" và kỳ vọng `S2` bắt được. ĐO RỒI THÌ
SAI: gỡ chốt đó KHÔNG tạo ra fail-open nào quan sát được, vì `khoi_phuc()` còn lớp kiểm cấu
trúc trên chính tệp tạm, và lớp đó bắt được cả hai bản sửa CÓ HẠI THẬT. Một phép tiêm không
tạo ra khác biệt quan sát được thì không chứng minh được gì.

====== BIẾN THỂ `chinh_sach_tu_choi` ĐÃ BỊ BỎ (G22), VÀ THAY BẰNG GÌ ======
Lượt trước có một biến thể KHÔNG gỡ chốt nào: nó đổi **quyết định sản phẩm**
(`CHINH_SACH_CHUA_KHAI`) từ `"sqlite"` sang `"tu_choi"` để ĐO cái giá của việc từ chối. Lượt này
quyết định đó đã được CHỐT: chưa khai ⇒ TỪ CHỐI, và công tắc bị bỏ hẳn (nó chính là khoảng hở
`do2b`). Nên biến thể cũ không còn gì để đổi, và nó được thay bằng phép tiêm **`D5`**: DỰNG LẠI
chính sách cũ (chưa khai ⇒ coi là SQLite) và đòi `S8` PHẢI bắt được. Đó là vế có răng — biến
thể cũ chỉ ĐO, còn `D5` chứng minh bộ đo PHÂN BIỆT ĐƯỢC.
"""
import os
import shutil
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))

# TỆP THẬT — mọi phép đo của lượt này chạy trên đúng tệp này.
MIGRATE_THAT = os.path.join(GOC, "app", "migrate.py")
# Bản ĐÓNG BĂNG trước khi vá, để lượt "TRƯỚC" vẫn đo lại được.
MIGRATE_NGUYENBAN = os.path.join(DAY, "migrate_nguyenban.py")
# Băm của bản đóng băng, chép ra NGAY LÚC ĐO LƯỢT "TRƯỚC" (`md5 -q` lúc 15:0x 16/10/2026, khớp
# từng byte với `app/migrate.py` trước khi vá). Có nó thì con số "1/10 FAIL_CLOSED" của lượt
# TRƯỚC gắn chặt vào ĐÚNG tệp đã sinh ra nó; đổi tệp là lượt đo TỪ CHỐI chạy, chứ không âm thầm
# so một bảng TRƯỚC của tệp khác với một bảng SAU của tệp này.
MD5_NGUYENBAN = "611182a621fd279c3816d5fc5d2785e3"

# ============================================================================
# BẢN VÁ, KHAI THÀNH MẢNH — mỗi mảnh PHẢI có mặt trong tệp thật, đúng MỘT lần
# ============================================================================
# Đây là cách "bản vá đã áp" trở thành một khẳng định KIỂM ĐƯỢC thay vì một lời hứa: thiếu
# bất kỳ mảnh nào, `xac_nhan()` NÉM và không lượt đo nào chạy tiếp.
MANH_VA = (
    ("chốt 0a — băm tệp theo khúc",
     "def _bam_tep(duong):"),
    ("chốt 0b — tên KHÔNG BAO GIỜ ĐÈ (dùng chung cho sao lưu và bản cất)",
     "def _duong_chua_dung(goc_ten, duoi, luc=None):"),
    ("chốt 0c — chép nguyên tử qua tệp tạm",
     "def _chep_nguyen_tu(nguon, dich):"),
    ("chốt 1 — kiểm CẤU TRÚC, chốt chống bẫy 0 byte bằng SỐ BẢNG",
     "    if so_bang < toi_thieu_bang:"),
    ("chốt 2 — DẤU KIỂM `.sha256` là BẮT BUỘC, không phải 'kiểm nếu có'",
     "    elif bat_buoc_dau_kiem:"),
    ("chốt 2b — so băm thật với băm mong đợi",
     "        if that != mong:"),
    ("chốt 3 — CHỐT (4) kho đang chạy, đọc từ khai báo",
     "def _kiem_kho_truoc_khi_sao_luu():"),
    ("chốt 3b — khai `postgresql` ⇒ TỪ CHỐI khi sao lưu",
     "    if kho == KHO_POSTGRESQL:"),
    # G22: chốt (4b) THAY chốt 3c cũ. Chốt cũ là một CÔNG TẮC (`CHINH_SACH_CHUA_KHAI = "sqlite"`)
    # và chính công tắc đó là khoảng hở `do2b`: chưa khai ⇒ coi là SQLite ⇒ rc 0 với một đường
    # lùi giả. Nay chưa khai ⇒ TỪ CHỐI, không nhánh nào để nới.
    ("chốt 3c — CHƯA KHAI kho đang chạy ⇒ TỪ CHỐI (đóng `do2b`), KHÔNG còn công tắc nới",
     '    if kho is None:\n        _tu_choi_chua_khai(nguon)'),
    ("chốt 3d — thông báo chưa-khai nói RÕ thiếu gì và khai ở đâu",
     '"[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này\\n"'),
    ("chốt 4 — `hub.db` không tồn tại ⇒ TỪ CHỐI (P-G15-02 `do1`)",
     "    if not os.path.exists(cau_hinh.DUONG_DAN_CSDL):"),
    ("chốt 5 — `sao_luu()` ghi qua tệp tạm, KIỂM RỒI mới `os.replace`",
     "        _kiem_cau_truc(tam, toi_thieu_bang=1)\n        os.replace(tam, dich)"),
    ("chốt 6 — `sao_luu()` ghi DẤU KIỂM sau khi tệp đã đóng",
     '        f.write("%s  %s\\n" % (bam, os.path.basename(dich)))'),
    ("chốt 7 — `khoi_phuc()` TỪ CHỐI khi TỤT SCHEMA",
     '        if _hien_tai and tt["phien_ban"] < _hien_tai:'),
    ("chốt 8 — `khoi_phuc()` ghi bản mới ra tệp tạm rồi mới `os.replace`",
     "        os.replace(tam, cau_hinh.DUONG_DAN_CSDL)"),
    ("chốt 9 — `khoi_phuc()` bắt buộc kiểm dấu kiểm của bản sao lưu",
     "    tt = _kiem_ban_sao_luu(duong_backup, bat_buoc_dau_kiem=not toi_da_biet_chua_kiem_duoc)"),
    ("chốt 10 — đường thoát cho người trực, mặc định là TỪ CHỐI",
     "def khoi_phuc(duong_backup, toi_da_biet_chua_kiem_duoc=False, luc=None):"),
    # G22 — ĐỒNG HỒ LÀ ĐẦU VÀO. Bất biến "ba lượt cùng một mốc KHÔNG xoá nhau" chỉ đo được khi
    # ba lượt THẬT SỰ cùng một mốc; đọc `datetime.now()` ở dưới sâu làm kết quả phụ thuộc tốc độ
    # máy, và có thể XANH trên một sản phẩm còn lỗi.
    ("chốt 11 — MỐC THỜI GIAN là THAM SỐ của `sao_luu()`/`khoi_phuc()`, không đọc ngầm",
     "def sao_luu(luc=None):"),
    ("chốt 11b — `khoi_phuc()` truyền mốc xuống chỗ đặt tên bản cất",
     '    cat_di = _duong_chua_dung("hub-truoc-rollback", ".db", luc)'),
)

# Mảnh mã của BẢN GỐC phải VẮNG. Đây là vế chống "vá mà tệp thật không đổi": bốn dòng dưới là
# đúng bốn đường fail-open mà P-G15-02 / S3 / S6b / `do2b` đo được. Còn dòng nào trong tệp thật
# nghĩa là bản vá CHƯA thật sự thay thế hành vi cũ.
MANH_GOC_PHAI_VANG = (
    ("đường lui GIẢ: `csdl.ket_noi(dich)` TẠO RA CSDL rỗng rồi sao lưu nó",
     "csdl.ket_noi(dich)"),
    ("bản cất đặt tên theo GIÂY, ghi đè im lặng",
     '"hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db"'),
    ("chép THẲNG lên CSDL đang chạy, không qua tệp tạm",
     "    shutil.copy2(duong_backup, cau_hinh.DUONG_DAN_CSDL)"),
    # G22 — CHÍNH SÁCH CŨ. Còn dòng này nghĩa là chưa khai vẫn bị COI LÀ SQLITE và hàm vẫn trả
    # mã thoát 0: đúng đường lùi giả của `do2b`. Đây là mảnh mà phép tiêm `D5` dựng lại.
    ("chưa khai ⇒ COI KHO LÀ SQLITE rồi đi tiếp (chính sách cũ, khoảng hở `do2b`)",
     "— lượt này COI KHO LÀ SQLITE"),
)

# ============================================================================
# TIÊM LỖI FAIL-OPEN — mỗi phép thay phải KHỚP, không khớp thì NÉM
# ============================================================================
# Bốn phép tiêm, MỖI PHÉP GỠ ĐÚNG MỘT CHỐT và mỗi phép có một kịch bản PHẢI bắt được nó.
TIEM_LOI = (
    ("D1 — bỏ tệp tạm: chép THẲNG lên CSDL đang chạy (đúng lỗi gốc)",
     "PHẢI bị S6b bắt",
     '        shutil.copy2(duong_backup, tam)\n'
     '        with open(tam, "rb+") as _f:\n'
     '            _f.flush()\n'
     '            os.fsync(_f.fileno())\n'
     '        _kiem_cau_truc(tam, toi_thieu_bang=tt["so_bang"])\n'
     '        for _duoi in ("-wal", "-shm"):\n'
     '            _p = cau_hinh.DUONG_DAN_CSDL + _duoi\n'
     '            if os.path.exists(_p):\n'
     '                os.remove(_p)\n'
     '        os.replace(tam, cau_hinh.DUONG_DAN_CSDL)\n',
     '        for _duoi in ("-wal", "-shm"):\n'
     '            _p = cau_hinh.DUONG_DAN_CSDL + _duoi\n'
     '            if os.path.exists(_p):\n'
     '                os.remove(_p)\n'
     '        shutil.copy2(duong_backup, cau_hinh.DUONG_DAN_CSDL)\n'),

    ("D2 — tên bản cất đặt theo GIÂY, cho phép ĐÈ (đúng lỗi gốc)",
     "PHẢI bị S4 bắt",
     '    cat_di = _duong_chua_dung("hub-truoc-rollback", ".db", luc)\n',
     '    cat_di = os.path.join(THU_MUC_SAO_LUU,\n'
     '                          "hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")\n'),

    ("D3 — bỏ chốt TỤT SCHEMA (đúng lỗi gốc)",
     "PHẢI bị S5 bắt",
     '        if _hien_tai and tt["phien_ban"] < _hien_tai:\n',
     '        if False and _hien_tai and tt["phien_ban"] < _hien_tai:\n'),

    ("D4 — bỏ MỌI phép kiểm chứng bản sao lưu (`_kiem_cau_truc` không kiểm gì + dấu kiểm không "
     "bắt buộc)",
     "PHẢI bị S3 và S7 bắt",
     '    if not os.path.exists(duong):\n'
     '        raise SystemExit("[migrate] TỪ CHỐI: không thấy tệp %s" % duong)\n',
     '    return {"duong": duong, "so_byte": 0, "so_bang": toi_thieu_bang, "phien_ban": 9,\n'
     '            "integrity": "ok"}\n'
     '    if not os.path.exists(duong):\n'
     '        raise SystemExit("[migrate] TỪ CHỐI: không thấy tệp %s" % duong)\n'),

    # G22 — D5 KHÔNG gỡ một chốt kỹ thuật nào: nó DỰNG LẠI ĐÚNG CHÍNH SÁCH CŨ (chưa khai ⇒ coi
    # kho là SQLite) ở chỗ chốt (4b). Đây là phép tiêm quan trọng nhất của lượt này, vì nó là
    # ĐỐI CHỨNG ÂM cho kết luận "S8 đã đóng": nới lại chính sách mà `S8` vẫn XANH thì `S8` không
    # canh gì cả, và mọi dòng "đã đóng" ở trên là rỗng. Nó phải bắt được Ở HAI VẾ (`do2b` và
    # `do1b`) — nhưng nhãn dưới đây CHỈ ghi mã kịch bản: `chay_do.py` tách mã từ nhãn này bằng
    # `split("và")`, nên mọi chữ giải thích thêm ở đây sẽ bị đọc thành một MÃ KỊCH BẢN KHÔNG TỒN
    # TẠI và lượt đo sẽ chạy 0 ca (đã xảy ra đúng như thế ở lượt chạy đầu của G22 — xem
    # `chay_do.py`, chốt chống nhãn không phân tích được).
    ("D5 — nới lại CHÍNH SÁCH CŨ: chưa khai ⇒ coi kho là SQLite rồi đi tiếp (đúng khoảng hở "
     "`do2b`)",
     "PHẢI bị S8 bắt",
     '    if kho is None:\n        _tu_choi_chua_khai(nguon)\n',
     '    if kho is None:\n'
     '        kho = KHO_SQLITE  # D5: chưa khai ⇒ COI LÀ SQLITE (chính sách cũ, đã bị bỏ)\n'),
)

# Vế thứ hai của D4 nằm ở chỗ KHÁC (tham số của lời gọi trong `khoi_phuc`), nên phải là một phép
# thay riêng — gộp vào bảng trên thì nó chạy cả khi người ta chỉ muốn tiêm D1/D2/D3.
D4_VE_HAI = (
    ("dấu kiểm không còn bắt buộc",
     'bat_buoc_dau_kiem=not toi_da_biet_chua_kiem_duoc)',
     'bat_buoc_dau_kiem=False)'),
)

# Đổi QUYẾT ĐỊNH SẢN PHẨM. G22: chỗ này TRƯỚC ĐÂY là biến thể `chinh_sach_tu_choi` — nó đổi
# `CHINH_SACH_CHUA_KHAI` từ `"sqlite"` sang `"tu_choi"` để ĐO cái giá của phương án từ chối.
# Phương án đó NAY LÀ MẶC ĐỊNH của tệp thật, nên biến thể đó không còn gì để đổi — và nó được
# THAY bằng phép tiêm `D5` ở trên, tức vế NGƯỢC LẠI: nới lại chính sách cũ và đòi `S8` bắt được.
# Đây là phép thay có răng, còn biến thể cũ chỉ là một lượt đo (nó không chứng minh được gì về
# việc bộ đo có phân biệt được hay không).
BIEN_THE_CHINH_SACH = ()


# ============================================================================
# ĐỌC + XÁC NHẬN TỆP THẬT
# ============================================================================
def _doc(duong):
    with open(duong, encoding="utf-8") as f:
        return f.read()


def xac_nhan(text=None):
    """TỪ CHỐI chạy tiếp nếu `text` không phải một bản vá ĐẦY ĐỦ. Trả `text`.

    Ba vế, cả ba đều bắt buộc:
      1. mọi mảnh của `MANH_VA` có mặt ĐÚNG MỘT lần;
      2. mọi mảnh của `MANH_GOC_PHAI_VANG` VẮNG mặt;
      3. mọi mốc mà bốn phép tiêm cần để thay có mặt ĐÚNG MỘT lần — thiếu một mốc là phép tiêm
         đó sẽ "trượt", và một phép tiêm trượt cho ra ĐỎ GIẢ ở chỗ khác.
    """
    if text is None:
        text = _doc(MIGRATE_THAT)
    for mo_ta, manh in MANH_VA:
        n = text.count(manh)
        if n != 1:
            raise AssertionError("BẢN VÁ KHÔNG ĐẦY ĐỦ trong %s: mảnh %r (%s) xuất hiện %d lần "
                                 "(cần đúng 1). Lượt đo TỪ CHỐI chạy — 'vá trượt mà vẫn xanh' "
                                 "là kiểu hỏng tệ nhất." % (MIGRATE_THAT, manh[:60], mo_ta, n))
    for mo_ta, manh in MANH_GOC_PHAI_VANG:
        if manh in text:
            raise AssertionError("BẢN VÁ CHƯA THAY THẾ HÀNH VI CŨ trong %s: còn mảnh %r (%s). "
                                 "Đây đúng là một đường fail-open đã đo được."
                                 % (MIGRATE_THAT, manh[:60], mo_ta))
    for nhan, _phai_bat, cu, _moi in TIEM_LOI:
        n = text.count(cu)
        if n != 1:
            raise AssertionError("MỐC TIÊM LỆCH (%s): đoạn cần thay xuất hiện %d lần (cần đúng "
                                 "1) — phép tiêm sẽ trượt" % (nhan, n))
    for _nhan, cu, _moi in D4_VE_HAI:
        if text.count(cu) != 1:
            raise AssertionError("MỐC TIÊM LỆCH (D4 vế hai): %r xuất hiện %d lần"
                                 % (cu, text.count(cu)))
    return text


def doc_that():
    """NỘI DUNG `app/migrate.py` — đã qua `xac_nhan()`. Đây là thứ mọi lượt đo dùng."""
    return xac_nhan(_doc(MIGRATE_THAT))


def doc_nguyenban():
    """NỘI DUNG bản ĐÓNG BĂNG trước khi vá. Dùng cho lượt "TRƯỚC"."""
    import hashlib
    t = _doc(MIGRATE_NGUYENBAN)
    if "def _kiem_cau_truc" in t or "def _duong_chua_dung" in t:
        raise AssertionError("%s đã bị vá — nó phải là bản NGUYÊN BẢN, không được chứa mã của "
                             "bản vá, nếu không lượt 'TRƯỚC' sẽ đo nhầm chính bản vá."
                             % MIGRATE_NGUYENBAN)
    bam = hashlib.md5(t.encode("utf-8")).hexdigest()
    if bam != MD5_NGUYENBAN:
        raise AssertionError(
            "BẢN ĐÓNG BĂNG ĐÃ ĐỔI: md5 = %s, bản đã ĐO lượt 'TRƯỚC' là %s.\n"
            "  Con số 1/10 FAIL_CLOSED của lượt TRƯỚC chỉ có nghĩa với ĐÚNG tệp đã sinh ra nó.\n"
            "  Nếu thật sự muốn đổi bản đóng băng thì phải ĐO LẠI lượt TRƯỚC rồi cập nhật cả hai."
            % (bam, MD5_NGUYENBAN))
    return t


# ============================================================================
# TIÊM LỖI + ĐỔI CHÍNH SÁCH
# ============================================================================
def tiem_loi(text, chon=None):
    """Tiêm lại các lỗi fail-open vào bản ĐÃ VÁ. Mỗi phép thay phải KHỚP, không thì NÉM.

    `chon`: tập NHÃN muốn tiêm (mặc định: cả bốn). Tách được từng lỗi để lượt tự kiểm biết
    CHÍNH XÁC kịch bản nào phải bắt được lỗi nào — một lượt tiêm gộp chỉ nói được "có bắt",
    không nói được "bắt đúng chỗ".
    """
    ra = text
    for nhan, _phai_bat, cu, moi in TIEM_LOI:
        if chon is not None and nhan.split(" ")[0] not in chon:
            continue
        if cu not in ra:
            raise AssertionError("TIÊM LỖI TRƯỢT (%s): không tìm thấy đoạn cần thay — bản vá đã "
                                 "đổi mà phép tiêm chưa cập nhật" % nhan)
        ra = ra.replace(cu, moi, 1)
    for _nhan, cu, moi in D4_VE_HAI:
        if chon is not None and "D4" not in chon:
            continue
        if cu not in ra:
            raise AssertionError("TIÊM LỖI TRƯỢT (D4 vế hai): không thấy %r" % cu)
        ra = ra.replace(cu, moi, 1)
    return ra


def doi_chinh_sach(text, ten="chinh_sach_tu_choi"):
    """GIỮ LẠI để ai đó gọi tới không nổ, nhưng G22 đã bỏ hết biến thể chính sách.

    Chính sách "chưa khai ⇒ TỪ CHỐI" nay là MẶC ĐỊNH của tệp thật, nên không còn biến thể nào để
    đổi. Vế đối chứng thay thế là phép tiêm `D5` (`tiem_loi`), tức nới lại chính sách cũ và đòi
    `S8` bắt được — mạnh hơn: nó chứng minh bộ đo PHÂN BIỆT ĐƯỢC, không chỉ đo một lần.
    """
    for nhan, cu, moi in BIEN_THE_CHINH_SACH:
        if nhan.split(" ")[0] != ten:
            continue
        if text.count(cu) != 1:
            raise AssertionError("BIẾN THỂ CHÍNH SÁCH TRƯỢT (%s): %r xuất hiện %d lần"
                                 % (nhan, cu, text.count(cu)))
        ra = text.replace(cu, moi, 1)
        return ra
    raise AssertionError(
        "KHÔNG CÒN BIẾN THỂ CHÍNH SÁCH NÀO TÊN %r (G22): chính sách 'chưa khai ⇒ TỪ CHỐI' đã là "
        "mặc định của tệp thật. Vế đối chứng tương ứng là phép tiêm D5 — xem `TIEM_LOI`." % ten)


def phai_bat(nhan_tiem):
    """Kịch bản PHẢI bắt được một phép tiêm — khai một chỗ, dùng cho cả bộ thử."""
    for nhan, phai, _cu, _moi in TIEM_LOI:
        if nhan.startswith(nhan_tiem):
            return phai
    raise KeyError(nhan_tiem)


# ============================================================================
# DỰNG `app/` ỨNG VIÊN: symlink mọi tệp, riêng `migrate.py` là bản dựng tại chỗ
# ============================================================================
def dung_thu_muc_app(dich, migrate_text):
    """Dựng một `app/` dùng được: mọi thứ là symlink về `app/` thật, `migrate.py` là bản dựng.

    Vì sao symlink chứ không chép cả cây: `app/*.py` là các mô-đun phẳng, import lẫn nhau theo
    tên. Symlink giữ chúng ĐÚNG BẢN ĐANG ĐƯỢC ĐO ở mọi tệp trừ `migrate.py` — nếu chép cả cây
    thì một lượt đo có thể vô tình đo một bản `csdl.py` khác.
    """
    that = os.path.join(GOC, "app")
    os.makedirs(dich, exist_ok=True)
    for ten in sorted(os.listdir(that)):
        if ten == "migrate.py":
            continue
        nguon, duong = os.path.join(that, ten), os.path.join(dich, ten)
        if os.path.lexists(duong):
            continue
        os.symlink(nguon, duong)
    with open(os.path.join(dich, "migrate.py"), "w", encoding="utf-8") as f:
        f.write(migrate_text)
    return dich


def dung_bien_the(nen, chi_tiem=None, chi_chinh_sach=None):
    """Dựng các `app/` ứng viên trong `nen`. Trả `{nhãn: đường dẫn}`.

      `goc`     — `migrate_nguyenban.py` (TRƯỚC khi vá, đóng băng);
      `ban_va`  — **CHÍNH `app/migrate.py`**, nguyên văn (đã qua `xac_nhan()`);
      `tiem_d1`…`tiem_d5` — tệp THẬT bị gỡ ĐÚNG MỘT chốt (D5: nới lại chính sách cũ); mỗi cái
                  có kịch bản PHẢI bắt được nó (`ban_va.phai_bat("D1")` nói ra kịch bản nào).

    `chi_chinh_sach` GIỮ LẠI trong chữ ký cho mã cũ gọi tới, nhưng G22 đã bỏ hết biến thể chính
    sách: chính sách "chưa khai ⇒ TỪ CHỐI" nay là mặc định của tệp thật, và vế đối chứng của nó
    là phép tiêm `D5`.
    """
    that = doc_that()
    ra = {"goc": dung_thu_muc_app(os.path.join(nen, "app-goc"), doc_nguyenban()),
          "ban_va": dung_thu_muc_app(os.path.join(nen, "app-ban-va"), that)}
    for nhan in ("D1", "D2", "D3", "D4", "D5"):
        if chi_tiem is not None and nhan not in chi_tiem:
            continue
        ra["tiem_" + nhan.lower()] = dung_thu_muc_app(
            os.path.join(nen, "app-tiem-" + nhan.lower()), tiem_loi(that, chon=(nhan,)))
    return ra


def tom_tat():
    """Số đo để in ra ở báo cáo: tệp thật, bản đóng băng, các mảnh đã kiểm."""
    import hashlib
    def _h(p):
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    that = doc_that()
    return {
        "migrate_that": {"duong": MIGRATE_THAT, "so_dong": that.count("\n") + 1, "sha256_16": _h(MIGRATE_THAT)},
        "migrate_nguyenban": {"duong": MIGRATE_NGUYENBAN,
                              "so_dong": _doc(MIGRATE_NGUYENBAN).count("\n") + 1,
                              "sha256_16": _h(MIGRATE_NGUYENBAN)},
        "so_manh_va_da_kiem": len(MANH_VA),
        "so_manh_goc_phai_vang_da_kiem": len(MANH_GOC_PHAI_VANG),
        "so_phep_tiem": len(TIEM_LOI),
        "phai_bat": {nhan.split(" ")[0]: phai for nhan, phai, _c, _m in TIEM_LOI},
    }


if __name__ == "__main__":
    import json
    print(json.dumps(tom_tat(), ensure_ascii=False, indent=2))
