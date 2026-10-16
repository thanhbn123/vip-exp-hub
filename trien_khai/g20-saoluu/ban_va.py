#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — BẢN VÁ ĐỀ XUẤT CHO `app/migrate.py` + HAI ĐỐI CHỨNG ĐƯỜNG BẮT BUỘC.

`app/migrate.py` là TỆP CỦA AG-00 — làn này (AG-02) KHÔNG được sửa nó. Nên mô-đun này KHÔNG
sửa gì cả: nó DỰNG RA một `app/` ỨNG VIÊN trong thư mục tạm (mọi tệp là symlink trỏ về cây
thật, riêng `migrate.py` là bản dựng tại chỗ), rồi chạy ĐÚNG bộ đo `fail_closed.py` trên đó
qua `G21_APP_DIR`. Ba lượt chạy, ba câu trả lời khác nhau, và cả ba đều cần:

  1. `goc`     — `app/migrate.py` nguyên bản.            Kỳ vọng: nhiều FAIL_OPEN (đo được: 9/10).
  2. `ban_va`  — bản vá đề xuất ở tệp này.               Kỳ vọng: các ca hỏng chuyển FAIL_CLOSED.
  3. `tiem_loi`— CHÍNH bản vá, bị TIÊM LẠI một lỗi fail-open (gỡ đúng một chốt).
                                                          Kỳ vọng: bộ đo PHẢI bắt được.
Lượt 3 là lượt quan trọng nhất. Thiếu nó thì "bộ đo báo ĐỎ trên mã chưa vá" có thể chỉ là bộ đo
đọc nhầm tệp, hoặc một cái ĐỎ cứng đơ bất kể đầu vào — và mọi dòng FAIL_CLOSED ở lượt 2 không
chứng minh gì. Lượt 3 chứng minh bộ đo PHÂN BIỆT ĐƯỢC.

====== CÁCH VÁ ======
Không cắt dán thân hàm (dễ trượt, dễ hỏng im lặng). Bản dựng chèn các định nghĩa MỚI vào NGAY
TRƯỚC khối `if __name__ == "__main__":` của bản gốc — trong Python, định nghĩa sau thắng. Bản
dựng TỪ CHỐI chạy nếu không tìm thấy mốc chèn, nên nó không thể "vá trượt mà vẫn xanh".

====== BA CHỐT MỚI, VÀ VÌ SAO ĐÚNG BA CHỐT NÀY ======
  (1) DẤU KIỂM `.sha256` đi kèm mỗi bản sao lưu, do `sao_luu()` ghi và `khoi_phuc()` bắt buộc
      kiểm. Đây là vế DUY NHẤT bắt được "sửa 1 byte trong trang dữ liệu đang dùng": đo được
      `PRAGMA integrity_check` trả **"ok"** cho tệp đó, nên kiểm cấu trúc KHÔNG đủ.
      Không có dấu kiểm ⇒ TỪ CHỐI (trừ khi người trực nói rõ là đã biết chưa kiểm được).
  (2) GHI QUA TỆP TẠM RỒI `os.replace` — hỏng giữa đường thì CSDL đang chạy KHÔNG bị đụng.
      Đây là vế bắt được "hết đĩa giữa đường khi khôi phục" (đo được: bản gốc để lại CSDL
      đích ở trạng thái `database disk image is malformed`, MẤT SẠCH 20 bảng).
  (3) TÊN BẢN CẤT KHÔNG BAO GIỜ ĐÈ + KIỂM PHIÊN BẢN SCHEMA trước khi đè.

====== MỘT KHOẢNG TRỐNG BẢN VÁ NÀY **KHÔNG** ĐÓNG, NÓI THẲNG ======
Đo 2 (`hub.db` CŨ còn sót trong khi kho đang chạy là PostgreSQL) vẫn HỞ. Hệ KHÔNG có khái niệm
"kho đang chạy là kho nào", nên không có gì để đối chiếu — và bịa một phép đoán (mtime, kích
thước) là vi phạm nguyên tắc "không đoán". Muốn đóng thì cần một QUYẾT ĐỊNH SẢN PHẨM: một cờ
cấu hình nói rõ kho đang chạy (`SQLite`/`PostgreSQL`), do AG-00/AG-05 chốt. Xem
`docs/G21_BACKUP_RESTORE.md` §CÒN HỞ.
"""
import os
import shutil
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
MIGRATE_GOC = os.path.join(GOC, "app", "migrate.py")
MOC_CHEN = '\nif __name__ == "__main__":'


# ============================================================================
# THÂN HÀM MỚI — dán vào trước khối `__main__` của bản gốc
# ============================================================================
THAN_MOI = '''

# ==========================================================================
# G21 / AG-02 — BẢN VÁ FAIL-CLOSED (đề xuất; dán trước khối __main__)
# ==========================================================================
import hashlib as _hashlib
import sqlite3 as _sqlite3


def _bam_tep(duong):
    """SHA-256 của một tệp, đọc theo khúc — không nạp cả tệp vào bộ nhớ."""
    _h = _hashlib.sha256()
    with open(duong, "rb") as _f:
        for _khuc in iter(lambda: _f.read(1 << 20), b""):
            _h.update(_khuc)
    return _h.hexdigest()


def _duong_chua_dung(goc_ten, duoi):
    """Đường dẫn CHƯA TỒN TẠI: trùng tên thì thêm hậu tố, KHÔNG BAO GIỜ ghi đè.

    Cùng khuôn với `sao_luu()` — hàm đó đã bị bắt đúng lỗi này và đã vá; `khoi_phuc()` thì chưa.
    Đo được: ba lượt khôi phục trong cùng một giây để lại ĐÚNG MỘT tệp `hub-truoc-rollback-*`,
    tức bản cất của lượt đầu — thứ duy nhất giữ dữ liệu thật — đã bị lượt sau xoá.
    """
    goc = os.path.join(THU_MUC_SAO_LUU, goc_ten + "-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    dich, n = goc + duoi, 1
    while os.path.exists(dich):
        dich = "%s-%d%s" % (goc, n, duoi)
        n += 1
        if n > 1000:
            raise SystemExit("[migrate] TỪ CHỐI: quá 1000 bản cùng giây tại %s — có gì đó sai" % goc)
    return dich


def _chep_nguyen_tu(nguon, dich):
    """Chép qua tệp TẠM CÙNG THƯ MỤC rồi `os.replace`. Hỏng giữa đường thì `dich` KHÔNG ĐỔI."""
    tam = "%s.tam-%d" % (dich, os.getpid())
    try:
        shutil.copy2(nguon, tam)
        with open(tam, "rb+") as _f:
            _f.flush()
            os.fsync(_f.fileno())
        os.replace(tam, dich)
    except BaseException:
        if os.path.exists(tam):
            try:
                os.remove(tam)
            except OSError:
                pass
        raise
    return dich


def _kiem_cau_truc(duong, toi_thieu_bang=1):
    """Xác minh CẤU TRÚC một tệp CSDL. NÉM `SystemExit` nếu không dùng được. CHỈ ĐỌC.

    ====== CÁI BẪY ĐÃ ĐO ĐƯỢC, VÀ CÁCH NÓ ĐƯỢC TRÁNH Ở ĐÂY ======
    Bản sao lưu do `sao_luu()` sinh ra MANG CHẾ ĐỘ WAL (byte 18-19 của phần đầu = 2). Mở nó
    bằng `file:...?mode=ro` **THẤT BẠI** — `unable to open database file` — vì SQLite cần tạo
    được tệp `-shm` cạnh nó. Một bản vá ngây thơ dùng `mode=ro` sẽ TỪ CHỐI NHẦM MỌI bản sao lưu
    TỐT. Đo được 16/10/2026 trên chính cây này:
        mode=ro              -> OperationalError: unable to open database file
        mode=ro&immutable=1  -> integrity_check = ok · 51 bảng
    Nên ở đây dùng `immutable=1`. Đổi lại phải trả giá: `immutable=1` BỎ QUA tệp `-wal` đi kèm,
    nên nó chỉ đọc đúng phần đã nằm trong tệp chính. Với bản sao lưu của `sao_luu()` thì đúng
    (API backup của SQLite ghi thẳng nội dung vào tệp chính), và đó là lý do phép kiểm này đặt
    trên BẢN SAO LƯU, không đặt trên CSDL đang chạy.
    """
    if not os.path.exists(duong):
        raise SystemExit("[migrate] TỪ CHỐI: không thấy tệp %s" % duong)
    co = os.path.getsize(duong)
    if co <= 0:
        raise SystemExit("[migrate] TỪ CHỐI: %s RỖNG (0 byte) — không có gì để dùng" % duong)
    with open(duong, "rb") as _f:
        dau = _f.read(16)
    if not dau.startswith(b"SQLite format 3\\x00"):
        raise SystemExit("[migrate] TỪ CHỐI: %s KHÔNG PHẢI CSDL SQLite (16 byte đầu: %r)" % (duong, dau))
    try:
        _kn = _sqlite3.connect("file:%s?mode=ro&immutable=1" % duong.replace("?", "%3f"), uri=True)
        try:
            _kq = _kn.execute("PRAGMA integrity_check").fetchone()[0]
            if _kq != "ok":
                raise SystemExit("[migrate] TỪ CHỐI: %s hỏng cấu trúc — integrity_check = %r"
                                 % (duong, _kq))
            _so_bang = _kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                                   " AND name NOT LIKE 'sqlite_%'").fetchone()[0]
            _pb = _kn.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
        finally:
            _kn.close()
    except _sqlite3.DatabaseError as _e:
        raise SystemExit("[migrate] TỪ CHỐI: %s KHÔNG ĐỌC ĐƯỢC như CSDL SQLite: %s" % (duong, _e))
    # CHỐT CHỐNG BẪY 0 BYTE: tệp SQLite dài 0 byte LÀ một CSDL rỗng HỢP LỆ —
    # `integrity_check` trả "ok" cho nó. Chỉ SỐ BẢNG mới bắt được. Đo được, không suy đoán.
    if _so_bang < toi_thieu_bang:
        raise SystemExit("[migrate] TỪ CHỐI: %s chỉ có %d bảng (cần >= %d) — tệp dở hoặc rỗng, "
                         "KHÔNG phải bản sao lưu dùng được" % (duong, _so_bang, toi_thieu_bang))
    return {"duong": duong, "so_byte": co, "so_bang": int(_so_bang), "phien_ban": int(_pb),
            "integrity": _kq}


def _kiem_ban_sao_luu(duong, bat_buoc_dau_kiem=True):
    """Xác minh một bản sao lưu TRƯỚC khi tin nó: cấu trúc + DẤU KIỂM `.sha256` đi kèm.

    Vì sao dấu kiểm là BẮT BUỘC chứ không "kiểm nếu có": đo được rằng một byte bị lật trong
    TRANG DỮ LIỆU ĐANG DÙNG (`don_hang.ma_don`) làm ĐỔI DỮ LIỆU THẬT mà `integrity_check` vẫn
    trả **"ok"**. Không có dấu kiểm thì tệp đó đi qua mọi phép kiểm cấu trúc. Còn "kiểm nếu có"
    thì kẻ làm hỏng chỉ cần xoá tệp `.sha256` là xong — một chốt mà kẻ tấn công bỏ được thì
    không phải chốt.

    Đường thoát cho người trực: `khoi_phuc(..., toi_da_biet_chua_kiem_duoc=True)`. Mặc định là
    TỪ CHỐI — fail-closed, và nói rõ vì sao.
    """
    tt = _kiem_cau_truc(duong, toi_thieu_bang=1)
    duong_dau = duong + ".sha256"
    if os.path.exists(duong_dau):
        with open(duong_dau, encoding="utf-8") as _f:
            _mong = _f.read().split()[0].strip()
        _that = _bam_tep(duong)
        if _that != _mong:
            raise SystemExit(
                "[migrate] TỪ CHỐI: %s KHÁC dấu kiểm %s\\n"
                "          mong đợi %s\\n          thực tế  %s\\n"
                "          Tệp đã bị sửa. KHÔNG khôi phục từ nó."
                % (duong, os.path.basename(duong_dau), _mong, _that))
        tt["co_dau_kiem"] = True
    elif bat_buoc_dau_kiem:
        raise SystemExit(
            "[migrate] TỪ CHỐI: %s KHÔNG có dấu kiểm %s.\\n"
            "          Không kiểm chứng được thì không khôi phục: một byte lật trong trang dữ "
            "liệu đang dùng\\n          vẫn qua được `integrity_check` (đã đo).\\n"
            "          Nếu đã biết rõ tệp này, chạy lại với `toi_da_biet_chua_kiem_duoc=True`."
            % (duong, os.path.basename(duong_dau)))
    else:
        tt["co_dau_kiem"] = False
    return tt


def sao_luu():
    """Bản VÁ: chụp một bản CSDL trước khi nâng cấp. Trả đường dẫn bản sao.

    Ba thay đổi so với bản gốc, mỗi thay đổi ứng với một phép đo ĐỎ:
      (1) `hub.db` KHÔNG tồn tại ⇒ TỪ CHỐI, thay vì `csdl.ket_noi()` TẠO RA một CSDL rỗng rồi
          sao lưu nó. Đo được trên cụm PostgreSQL riêng: bản gốc thoát 0 và trả một tệp 4.096
          byte / 0 BẢNG / `integrity_check = ok` trong khi PostgreSQL giữ 6 đơn và 9.324.000
          đồng — một ĐƯỜNG LÙI GIẢ, và không một dòng cảnh báo.
      (2) Ghi ra tệp TẠM rồi `os.replace` sang tên thật. Hỏng giữa đường (hết đĩa) thì KHÔNG
          còn tệp dở nào mang tên bản sao lưu. Đo được: bản gốc để lại
          `hub-truoc-migrate-*.db` **0 byte** và không dọn.
      (3) Ghi DẤU KIỂM `<bản-sao-lưu>.sha256` sau khi tệp đã đóng và đã kiểm cấu trúc.
    """
    if not os.path.exists(cau_hinh.DUONG_DAN_CSDL):
        raise SystemExit(
            "[migrate] TỪ CHỐI: không thấy CSDL tại %s nên KHÔNG có gì để sao lưu.\\n"
            "          (Bản cũ vẫn 'thành công' ở đây bằng cách TẠO RA một CSDL rỗng rồi sao "
            "lưu nó —\\n           đó là đường lùi giả. Nếu kho đang chạy là PostgreSQL thì "
            "`sao_luu()` này không dùng được;\\n           xem docs/G21_BACKUP_RESTORE.md.)"
            % cau_hinh.DUONG_DAN_CSDL)
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    dich = _duong_chua_dung("hub-truoc-migrate", ".db")
    tam = dich + ".dang-ghi"
    try:
        nguon = csdl.ket_noi()
        ban = csdl.ket_noi(tam)
        try:
            with ban:
                nguon.backup(ban)
        finally:
            ban.close()
            nguon.close()
        with open(tam, "rb+") as _f:
            _f.flush()
            os.fsync(_f.fileno())
        tt = _kiem_cau_truc(tam, toi_thieu_bang=1)
        os.replace(tam, dich)
    except BaseException:
        if os.path.exists(tam):
            try:
                os.remove(tam)
            except OSError:
                pass
        raise
    bam = _bam_tep(dich)
    with open(dich + ".sha256", "w", encoding="utf-8") as _f:
        _f.write("%s  %s\\n" % (bam, os.path.basename(dich)))
    return dich


def khoi_phuc(duong_backup, toi_da_biet_chua_kiem_duoc=False):
    """Bản VÁ: rollback CSDL về đúng tệp backup — FAIL-CLOSED.

    ====== BẤT BIẾN ======
    Hỏng ở BẤT KỲ bước nào thì CSDL ĐANG CHẠY phải còn NGUYÊN VẸN, và phải có thông báo nói
    rõ hỏng ở đâu. Ba bước, theo đúng thứ tự này:
      1. KIỂM BẢN SAO LƯU **TRƯỚC KHI ĐỤNG** CSDL đang chạy (cấu trúc + dấu kiểm + phiên bản);
      2. CẤT bản đang chạy vào một tên KHÔNG BAO GIỜ ĐÈ, và kiểm bản cất đọc được;
      3. GHI BẢN MỚI RA TỆP TẠM cùng thư mục, kiểm lại, RỒI MỚI `os.replace`.
    Bước 3 là vế bắt được "hết đĩa giữa đường". Đo được trên bản gốc: CSDL đích bị để lại ở
    280.576 byte với `DatabaseError: database disk image is malformed` và MẤT SẠCH 20 bảng.
    """
    tt = _kiem_ban_sao_luu(duong_backup, bat_buoc_dau_kiem=not toi_da_biet_chua_kiem_duoc)
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)

    if os.path.exists(cau_hinh.DUONG_DAN_CSDL) and not toi_da_biet_chua_kiem_duoc:
        try:
            _hien_tai = _kiem_cau_truc(cau_hinh.DUONG_DAN_CSDL, toi_thieu_bang=1)["phien_ban"]
        except SystemExit:
            _hien_tai = None
        if _hien_tai and tt["phien_ban"] < _hien_tai:
            raise SystemExit(
                "[migrate] TỪ CHỐI: TỤT SCHEMA. Bản sao lưu ở phiên bản **v%d**, CSDL đang chạy "
                "ở **v%d**.\\n          Khôi phục sẽ bỏ rơi dữ liệu của %d phiên bản migration. "
                "Đo được: v6 đè lên v9 làm CSDL còn\\n          20 bảng thay vì 51 và tổng tiền "
                "rơi từ 34.336.000 xuống 1.298.000 đồng — KHÔNG một lời cảnh báo.\\n"
                "          Nếu đây đúng là ý định, chạy lại với `toi_da_biet_chua_kiem_duoc=True`."
                % (tt["phien_ban"], _hien_tai, _hien_tai - tt["phien_ban"]))

    cat_di = _duong_chua_dung("hub-truoc-rollback", ".db")
    if os.path.exists(cau_hinh.DUONG_DAN_CSDL):
        _chep_nguyen_tu(cau_hinh.DUONG_DAN_CSDL, cat_di)
        for _duoi in ("-wal", "-shm"):
            if os.path.exists(cau_hinh.DUONG_DAN_CSDL + _duoi):
                _chep_nguyen_tu(cau_hinh.DUONG_DAN_CSDL + _duoi, cat_di + _duoi)
        _kiem_cau_truc(cat_di, toi_thieu_bang=1)

    tam = cau_hinh.DUONG_DAN_CSDL + ".dang-khoi-phuc-%d" % os.getpid()
    try:
        shutil.copy2(duong_backup, tam)
        with open(tam, "rb+") as _f:
            _f.flush()
            os.fsync(_f.fileno())
        _kiem_cau_truc(tam, toi_thieu_bang=tt["so_bang"])
        for _duoi in ("-wal", "-shm"):
            _p = cau_hinh.DUONG_DAN_CSDL + _duoi
            if os.path.exists(_p):
                os.remove(_p)
        os.replace(tam, cau_hinh.DUONG_DAN_CSDL)
    except BaseException as _e:
        if os.path.exists(tam):
            try:
                os.remove(tam)
            except OSError:
                pass
        raise SystemExit(
            "[migrate] KHÔI PHỤC HỎNG: %s\\n"
            "          CSDL đang chạy KHÔNG bị đụng (bản mới chỉ nằm ở tệp tạm, đã dọn).\\n"
            "          Bản cất trước khi khôi phục: %s" % (_e, cat_di))
    print("[migrate] Đã khôi phục từ %s (kiểm cấu trúc + dấu kiểm TRƯỚC khi đè). "
          "Bản trước khi khôi phục cất ở %s" % (duong_backup, cat_di))
'''

# ============================================================================
# TIÊM LỖI FAIL-OPEN — mỗi phép thay phải KHỚP, không khớp thì NÉM
# ============================================================================
# Bốn phép tiêm, MỖI PHÉP GỠ ĐÚNG MỘT CHỐT và mỗi phép có một kịch bản PHẢI bắt được nó.
# Không khớp ⇒ AssertionError. Một phép tiêm "trượt" mà vẫn chạy tiếp là kiểu hỏng tệ nhất:
# bộ đo sẽ báo ĐỎ trên một bản vá còn nguyên, và người đọc tưởng bộ đo có răng.
#
# ====== MỘT PHÉP TIÊM TÔI ĐÃ BỎ, VÀ VÌ SAO — ghi lại để người sau không thêm lại ======
# Tôi đã định tiêm "gỡ chốt bắt buộc DẤU KIỂM `.sha256`" và kỳ vọng `S2` bắt được. ĐO RỒI THÌ
# SAI: gỡ chốt đó KHÔNG tạo ra fail-open nào quan sát được, vì `khoi_phuc()` còn lớp kiểm cấu
# trúc trên chính tệp tạm, và lớp đó bắt được cả hai bản sửa CÓ HẠI THẬT (`e-trang-dung` hỏng
# chỉ mục, `d-byte0` mất magic). Ba bản sửa còn lại lật byte vào vùng trống nên DỮ LIỆU KHÔNG
# ĐỔI — nhận chúng là ĐÚNG. Một phép tiêm không tạo ra khác biệt quan sát được thì không chứng
# minh được gì; giữ nó lại chỉ làm bảng tự kiểm trông đẹp hơn thực tế. Nên nó bị bỏ.
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
     '    cat_di = _duong_chua_dung("hub-truoc-rollback", ".db")\n',
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
)

# Vế thứ hai của D4 nằm ở chỗ KHÁC (tham số của lời gọi trong `khoi_phuc`), nên phải là một phép
# thay riêng — gộp vào bảng trên thì nó chạy cả khi người ta chỉ muốn tiêm D1/D2/D3.
D4_VE_HAI = (
    ("dấu kiểm không còn bắt buộc",
     'bat_buoc_dau_kiem=not toi_da_biet_chua_kiem_duoc)',
     'bat_buoc_dau_kiem=False)'),
)


def dung_ban_va(text=None):
    """Chèn thân hàm mới vào trước khối `__main__`. TỪ CHỐI nếu không thấy mốc chèn."""
    if text is None:
        with open(MIGRATE_GOC, encoding="utf-8") as f:
            text = f.read()
    if MOC_CHEN not in text:
        raise AssertionError("KHÔNG thấy mốc chèn %r trong %s — bản dựng TỪ CHỐI chạy tiếp, "
                             "vì 'vá trượt mà vẫn xanh' là kiểu hỏng tệ nhất."
                             % (MOC_CHEN.strip(), MIGRATE_GOC))
    if text.count(MOC_CHEN) != 1:
        raise AssertionError("mốc chèn xuất hiện %d lần — không rõ chèn vào đâu"
                             % text.count(MOC_CHEN))
    return text.replace(MOC_CHEN, THAN_MOI + MOC_CHEN)


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


def dung_bien_the(nen, chi_tiem=None):
    """Dựng các `app/` ứng viên trong `nen`. Trả {nhãn: đường dẫn}.

      `goc`     — mã nguyên bản;
      `ban_va`  — bản vá đề xuất;
      `tiem_d1`…`tiem_d4` — bản vá bị gỡ ĐÚNG MỘT chốt; mỗi cái có kịch bản PHẢI bắt được nó
                  (`ban_va.phai_bat("D1")` nói ra kịch bản nào).
    """
    with open(MIGRATE_GOC, encoding="utf-8") as f:
        goc = f.read()
    ban_va = dung_ban_va(goc)
    ra = {"goc": dung_thu_muc_app(os.path.join(nen, "app-goc"), goc),
          "ban_va": dung_thu_muc_app(os.path.join(nen, "app-ban-va"), ban_va)}
    for nhan in ("D1", "D2", "D3", "D4"):
        if chi_tiem is not None and nhan not in chi_tiem:
            continue
        ra["tiem_" + nhan.lower()] = dung_thu_muc_app(
            os.path.join(nen, "app-tiem-" + nhan.lower()), tiem_loi(ban_va, chon=(nhan,)))
    return ra
