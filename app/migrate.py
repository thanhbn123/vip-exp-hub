# G01.5 — Migration có quản lý phiên bản, backup và kiểm chứng bảo toàn dữ liệu.
# Chạy: python3 app/migrate.py            (nâng cấp, có backup + verify)
#       python3 app/migrate.py --kiem     (chỉ xem phiên bản, không sửa gì)
#       python3 app/migrate.py --rollback <file-backup>   (khôi phục từ backup)
#       python3 app/migrate.py --rollback <f> --toi-da-biet-chua-kiem-duoc
#           (CHỈ khi đã biết rõ tệp đó: bỏ chốt dấu kiểm `.sha256` và chốt tụt schema)
#
# Nguyên tắc: KHÔNG xóa dữ liệu, KHÔNG đụng gateway.db, KHÔNG gán tenant cho dữ liệu chưa rõ chủ.
#
# ==========================================================================
# G21 / AG-02 — ĐÃ ÁP BẢN VÁ FAIL-CLOSED CHO `sao_luu()` / `khoi_phuc()`
# ==========================================================================
# Bốn chốt, mỗi chốt ứng với một phép đo ĐỎ trên chính tệp này (docs/G21_BACKUP_RESTORE.md §6):
#   (1) DẤU KIỂM `<bản-sao-lưu>.sha256`, `sao_luu()` ghi và `khoi_phuc()` BẮT BUỘC kiểm.
#       Vế DUY NHẤT bắt được "lật 1 byte trong trang dữ liệu đang dùng": đo được
#       `PRAGMA integrity_check` vẫn trả "ok" cho tệp đó.
#   (2) GHI QUA TỆP TẠM rồi `os.replace` — hỏng giữa đường thì CSDL đang chạy KHÔNG bị đụng.
#   (3) TÊN BẢN CẤT KHÔNG BAO GIỜ ĐÈ + KIỂM PHIÊN BẢN SCHEMA trước khi đè.
#   (4) KHAI BÁO "KHO ĐANG CHẠY" — `sao_luu()` chỉ có nhánh SQLite, nên khi kho đang chạy là
#       PostgreSQL nó phải TỪ CHỐI, chứ không được đưa ra một ĐƯỜNG LÙI GIẢ (P-G15-02).
# Bộ đo: trien_khai/g20-saoluu/fail_closed.py · bộ thử: app/thu/thu_g21_saoluu.py
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime

GOC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GOC)

import cau_hinh   # noqa: E402
import csdl       # noqa: E402
import quyen      # noqa: E402

THU_MUC_SAO_LUU = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "sao-luu")

# Các bảng phải bảo toàn số dòng qua migration (dữ liệu nghiệp vụ đã có).
BANG_PHAI_GIU = ("tenants", "users", "khach_hang", "carrier_accounts", "don_hang",
                 "don_lich_su", "wh_su_kien", "import_batch", "import_dong", "audit")


def _co_bang(kn, ten):
    return kn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (ten,)).fetchone() is not None


def _cot(kn, bang):
    return [r[1] for r in kn.execute(f"PRAGMA table_info({bang})")]


def dem_dong(kn):
    ra = {}
    for b in BANG_PHAI_GIU:
        if _co_bang(kn, b):
            ra[b] = kn.execute(f"SELECT COUNT(*) FROM {b}").fetchone()[0]
    return ra


# ==========================================================================
# G21 / AG-02 — HẠ TẦNG FAIL-CLOSED (bốn chốt; xem banner đầu tệp)
# ==========================================================================
def _bam_tep(duong):
    """SHA-256 của một tệp, đọc theo khúc — không nạp cả tệp vào bộ nhớ."""
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    return h.hexdigest()


def _duong_chua_dung(goc_ten, duoi, luc=None):
    """Đường dẫn CHƯA TỒN TẠI: trùng tên thì thêm hậu tố, KHÔNG BAO GIỜ ghi đè.

    Cùng khuôn với `sao_luu()` — hàm đó đã bị bắt đúng lỗi này và đã vá; `khoi_phuc()` thì chưa.
    Đo được: ba lượt khôi phục trong cùng một giây để lại ĐÚNG MỘT tệp `hub-truoc-rollback-*`,
    tức bản cất của lượt đầu — thứ duy nhất giữ dữ liệu thật — đã bị lượt sau xoá.

    ====== `luc` — MỐC THỜI GIAN LÀ THAM SỐ, KHÔNG ĐỌC ĐỒNG HỒ NGẦM ======
    `luc=None` (mặc định, đường chạy thật) ⇒ `datetime.now()`. Bộ đo TRUYỀN một mốc CỐ ĐỊNH
    (`datetime`, hoặc chuỗi `%Y%m%d-%H%M%S` dùng NGUYÊN VĂN) để ba lượt liên tiếp rơi CHẮC CHẮN
    vào cùng một mốc.

    Vì sao phải truyền: bất biến "ba lượt cùng giây KHÔNG được xoá nhau" chỉ được đo khi ba lượt
    THẬT SỰ cùng một mốc. Đọc đồng hồ ngầm thì điều đó phụ thuộc tốc độ máy: ba lượt có thể rơi
    vào hai giây khác nhau, tên khác nhau, phép đo XANH — mà ĐƯỜNG ĐÈ thì chưa hề được chạm tới.
    Nghĩa là kết quả của ca phụ thuộc ĐỒNG HỒ HỆ THỐNG (chạy riêng một kiểu, chạy chung một
    kiểu), và nó có thể XANH trên một sản phẩm còn lỗi. Truyền mốc vào là cách duy nhất khiến ca
    TẤT ĐỊNH và khiến nó THẬT SỰ chạm vào đường ĐÈ. Xem docs/G22_SAOLUU.md §5.
    """
    if luc is None:
        hau = datetime.now().strftime("%Y%m%d-%H%M%S")
    elif hasattr(luc, "strftime"):
        hau = luc.strftime("%Y%m%d-%H%M%S")
    else:
        hau = str(luc)
    goc = os.path.join(THU_MUC_SAO_LUU, goc_ten + "-" + hau)
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
        with open(tam, "rb+") as f:
            f.flush()
            os.fsync(f.fileno())
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
    with open(duong, "rb") as f:
        dau = f.read(16)
    if not dau.startswith(b"SQLite format 3\x00"):
        raise SystemExit("[migrate] TỪ CHỐI: %s KHÔNG PHẢI CSDL SQLite (16 byte đầu: %r)"
                         % (duong, dau))
    try:
        kn = sqlite3.connect("file:%s?mode=ro&immutable=1" % duong.replace("?", "%3f"), uri=True)
        try:
            kq = kn.execute("PRAGMA integrity_check").fetchone()[0]
            if kq != "ok":
                raise SystemExit("[migrate] TỪ CHỐI: %s hỏng cấu trúc — integrity_check = %r"
                                 % (duong, kq))
            so_bang = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                                 " AND name NOT LIKE 'sqlite_%'").fetchone()[0]
            try:
                pb = kn.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
            except sqlite3.OperationalError:
                # CSDL SQLite HỢP LỆ nhưng KHÔNG có bảng `schema_version` (bản sao lưu của một hệ
                # trước G01.5). Đó KHÔNG phải lý do để từ chối — thiếu bảng thì phiên bản là 0,
                # và chốt TỤT SCHEMA ở dưới tự so tiếp. Từ chối ở đây là TỪ CHỐI NHẦM một bản sao
                # lưu TỐT, đúng cùng loại lỗi với cái bẫy `mode=ro` ở docstring trên.
                pb = 0
        finally:
            kn.close()
    except sqlite3.DatabaseError as e:
        raise SystemExit("[migrate] TỪ CHỐI: %s KHÔNG ĐỌC ĐƯỢC như CSDL SQLite: %s" % (duong, e))
    # CHỐT CHỐNG BẪY 0 BYTE: tệp SQLite dài 0 byte LÀ một CSDL rỗng HỢP LỆ —
    # `integrity_check` trả "ok" cho nó. Chỉ SỐ BẢNG mới bắt được. Đo được, không suy đoán.
    if so_bang < toi_thieu_bang:
        raise SystemExit("[migrate] TỪ CHỐI: %s chỉ có %d bảng (cần >= %d) — tệp dở hoặc rỗng, "
                         "KHÔNG phải bản sao lưu dùng được" % (duong, so_bang, toi_thieu_bang))
    return {"duong": duong, "so_byte": co, "so_bang": int(so_bang), "phien_ban": int(pb),
            "integrity": kq}


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
        with open(duong_dau, encoding="utf-8") as f:
            mong = f.read().split()[0].strip()
        that = _bam_tep(duong)
        if that != mong:
            raise SystemExit(
                "[migrate] TỪ CHỐI: %s KHÁC dấu kiểm %s\n"
                "          mong đợi %s\n          thực tế  %s\n"
                "          Tệp đã bị sửa. KHÔNG khôi phục từ nó."
                % (duong, os.path.basename(duong_dau), mong, that))
        tt["co_dau_kiem"] = True
    elif bat_buoc_dau_kiem:
        raise SystemExit(
            "[migrate] TỪ CHỐI: %s KHÔNG có dấu kiểm %s.\n"
            "          Không kiểm chứng được thì không khôi phục: một byte lật trong trang dữ "
            "liệu đang dùng\n          vẫn qua được `integrity_check` (đã đo).\n"
            "          Nếu đã biết rõ tệp này: gọi `khoi_phuc(..., toi_da_biet_chua_kiem_duoc=True)`\n"
            "          hoặc chạy `python3 app/migrate.py --rollback <tệp> --toi-da-biet-chua-kiem-duoc`."
            % (duong, os.path.basename(duong_dau)))
    else:
        tt["co_dau_kiem"] = False
    return tt


# ---- CHỐT (4): KHO ĐANG CHẠY — ĐỌC TỪ KHAI BÁO, KHÔNG ĐOÁN -------------------------------
# `sao_luu()` chỉ có nhánh SQLite. Khi kho đang chạy là PostgreSQL thì mọi "bản sao lưu" nó
# tạo ra đều KHÔNG chứa dữ liệu đang phục vụ — một ĐƯỜNG LÙI GIẢ. Hệ KHÔNG có cách nào tự
# biết kho nào đang chạy (`app/csdl.py` thuần SQLite, không có nhánh PostgreSQL), nên câu trả
# lời phải đến từ một KHAI BÁO của người triển khai. Đọc theo thứ tự: `cau_hinh.KHO_DANG_CHAY`
# (chỗ chính thức) rồi tới biến môi trường. KHÔNG suy ra từ mtime / kích thước / tên tệp: một
# phép đoán ở đây sẽ im lặng đúng vào lúc cần nhất.
#
# Tên hằng và giá trị nằm ở `app/cau_hinh.py` (cấu hình thuộc về cấu hình). Ba dòng dưới chỉ
# GIỮ TÊN CŨ cho mã đang gọi tới, không định nghĩa lại giá trị.
KHO_SQLITE = cau_hinh.KHO_SQLITE
KHO_POSTGRESQL = cau_hinh.KHO_POSTGRESQL
BIEN_KHAI_KHO = cau_hinh.BIEN_KHAI_KHO

# ============================================================================
# CHÍNH SÁCH KHI CHƯA KHAI — **TỪ CHỐI**, VÀ KHÔNG CÒN CÔNG TẮC NÀO KHÁC
# ============================================================================
# Lượt trước để một công tắc tên `CHINH_SACH_CHUA_KHAI` với giá trị `"sqlite"`: chưa khai ⇒ coi
# kho là SQLite, chỉ in một dòng cảnh báo ra stderr. Đo được trên cụm PostgreSQL riêng
# (`do2b`, P-G15-02): `hub.db` CŨ còn sót + deployment CHƯA KHAI ⇒ `sao_luu()` thoát **0** và
# trả một bản sao TRÔNG HỢP LỆ — 51 bảng, 34.336.000 đồng, băm khớp đúng tệp SQLite đó — mà
# KHÔNG chứa một dòng nào của 9.324.000 đồng đang phục vụ ở PostgreSQL. Công tắc đó CHÍNH LÀ
# khoảng hở: nó biến "không biết" thành "coi như SQLite" mà vẫn trả mã thoát 0.
#
# Nên công tắc bị BỎ, không phải đổi giá trị. Chưa khai ⇒ `_tu_choi_chua_khai()` ⇒ rc != 0 kèm
# hướng dẫn khai. Không có nhánh nào để nới, nên không có nhánh nào bị nới nhầm.
#
# CÁI GIÁ (đo, không đoán — docs/G22_SAOLUU.md §4): 8 bộ thử NGOÀI vùng được ghi của AG-02 gọi
# `migrate.chay()` mà không khai kho, nên chúng TỪ CHỐI cho tới khi mỗi bộ khai một dòng
# (`VIP_KHO_DANG_CHAY=sqlite`). Đó là lựa chọn CỤC BỘ đã được uỷ quyền của AG-02, KHÔNG phải
# một quyết định thay Owner — và nó KHÔNG được vá bằng cách nới chốt.


def _tu_choi_chua_khai(nguon):
    """CHỐT (4b) — CHƯA KHAI kho đang chạy ⇒ TỪ CHỐI. Đây là chỗ đóng P-G15-02 `do2b`.

    Vì sao TỪ CHỐI chứ không "mặc định SQLite": `hub.db` CŨ còn sót lại và `hub.db` ĐANG PHỤC VỤ
    là hai thứ KHÔNG PHÂN BIỆT ĐƯỢC bằng mắt thường, bằng mtime hay bằng kích thước. Câu hỏi duy
    nhất phân biệt được là "kho đang chạy là kho nào", và nó chỉ có một nguồn trả lời: người
    triển khai. Thiếu câu trả lời đó thì bản sao lưu này KHÔNG kiểm chứng được, và một bản sao
    lưu không kiểm chứng được mà vẫn trả mã thoát 0 chính là đường lùi giả.

    Thông báo nói RÕ ba thứ: (i) đang thiếu gì, (ii) khai ở đâu, (iii) cái gì đang nằm trên đĩa —
    vì "hub.db còn sót" là manh mối duy nhất người trực có, và giấu nó đi là bắt họ tự đoán.
    """
    co_hub_db = os.path.exists(cau_hinh.DUONG_DAN_CSDL)
    them = ("          TRÊN ĐĨA ĐANG CÓ `hub.db` tại %s.\n"
            "          Tệp đó CÓ THỂ là kho đang phục vụ, CŨNG CÓ THỂ là tệp CŨ còn sót lại sau\n"
            "          khi dữ liệu đã chuyển sang PostgreSQL. Hai thứ đó KHÔNG phân biệt được\n"
            "          bằng mtime / kích thước / tên tệp — nên hàm này KHÔNG đoán.\n"
            % cau_hinh.DUONG_DAN_CSDL) if co_hub_db else \
           ("          Trên đĩa cũng KHÔNG có `hub.db` tại %s.\n"
            % cau_hinh.DUONG_DAN_CSDL)
    raise SystemExit(
        "[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy nên KHÔNG kiểm chứng được bản sao lưu này\n"
        "          có chứa dữ liệu đang phục vụ hay không (%s).\n"
        "%s"
        "          Khai MỘT trong hai:\n"
        "            · `KHO_DANG_CHAY = '%s'` (hoặc '%s') trong app/cau_hinh.py, hoặc\n"
        "            · biến môi trường %s=%s|%s cho tiến trình chạy `migrate`.\n"
        "          Nếu kho đang chạy là PostgreSQL: `sao_luu()` KHÔNG dùng được — sao lưu bằng\n"
        "          `pg_dump -Fc`; xem docs/G22_SAOLUU.md.\n"
        "          Nếu kho đang chạy là SQLite: khai `%s` rồi chạy lại. Chốt này cố ý KHÔNG có\n"
        "          mặc định: một mặc định ở đây là một phép đoán, và phép đoán đó trả mã thoát 0.\n"
        "          CHỈ khai `%s` cho môi trường KIỂM THỬ CÔ LẬP (thư mục dữ liệu TẠM). KHÔNG đặt\n"
        "          biến này cho tiến trình production: nếu dữ liệu thật đã sang PostgreSQL thì khai\n"
        "          `%s` ở đó biến mọi bản sao lưu thành ĐƯỜNG LÙI GIẢ mà vẫn trả mã thoát 0.\n"
        "          Bộ thử dùng SQLite: `cau_hinh.khai_kho_kiem_thu()` (từ chối nếu thư mục dữ liệu\n"
        "          không cô lập) — xem docs/G22_CAUHINH.md.\n"
        % ("nguồn khai: %s" % nguon if nguon else "chưa có nguồn nào khai", them,
           KHO_SQLITE, KHO_POSTGRESQL, BIEN_KHAI_KHO,
           KHO_SQLITE, KHO_POSTGRESQL, KHO_SQLITE, KHO_SQLITE, KHO_SQLITE))


def _chuan_hoa_kho(gia_tri):
    """`sqlite3` ⇒ sqlite · `pg`/`postgres` ⇒ postgresql · lạ ⇒ TỪ CHỐI.

    Khai báo sai chính tả KHÔNG được coi là "chưa khai": coi nó là chưa khai là âm thầm đưa hệ
    về đúng chỗ đang muốn tránh, mà lại im lặng.

    BẢNG BIẾN THỂ nằm ở `cau_hinh.KHO_DANG_CHAY_BIEN_THE` (một chỗ, dùng chung với đường khai
    của bộ thử `cau_hinh.khai_kho_kiem_thu()`); hàm này giữ TÊN CŨ cho mã đang gọi tới và giữ
    thông báo lỗi của `migrate` — nơi người trực gõ lệnh.
    """
    if gia_tri is None:
        return None
    v = str(gia_tri).strip().lower()
    if not v:
        return None
    kho = cau_hinh.chuan_hoa_kho(v)
    if kho:
        return kho
    raise SystemExit(
        "[migrate] TỪ CHỐI: khai báo kho đang chạy không nhận ra: %r.\n"
        "          Nhận 'sqlite' hoặc 'postgresql'." % (gia_tri,))


def kho_dang_chay():
    """Trả `(kho, nguồn)`. `kho is None` nghĩa là CHƯA KHAI — KHÔNG phải "mặc định SQLite"."""
    for nguon, gia_tri in (("cau_hinh.KHO_DANG_CHAY", getattr(cau_hinh, "KHO_DANG_CHAY", None)),
                           (BIEN_KHAI_KHO, os.environ.get(BIEN_KHAI_KHO))):
        kho = _chuan_hoa_kho(gia_tri)
        if kho:
            return kho, nguon
    return None, None


def _kiem_kho_truoc_khi_sao_luu():
    """CHỐT (4). NÉM `SystemExit` nếu kho đang chạy CHƯA KHAI hoặc KHÔNG PHẢI SQLite."""
    kho, nguon = kho_dang_chay()
    if kho == KHO_POSTGRESQL:
        raise SystemExit(
            "[migrate] TỪ CHỐI: kho đang chạy là PostgreSQL (khai ở %s) nhưng `sao_luu()`\n"
            "          KHÔNG CÓ NHÁNH PostgreSQL — nó chỉ biết `csdl.ket_noi()` của SQLite.\n"
            "          Chạy tiếp thì nó tạo ra một tệp SQLite KHÔNG chứa một dòng nào của dữ\n"
            "          liệu đang phục vụ: một ĐƯỜNG LÙI GIẢ, và im lặng. Đo được trên cụm\n"
            "          PostgreSQL riêng: 4.096 byte / 0 BẢNG / integrity_check = 'ok' trong khi\n"
            "          PostgreSQL giữ 6 đơn và 9.324.000 đồng (P-G15-02).\n"
            "          Sao lưu PostgreSQL bằng `pg_dump -Fc`; xem docs/G22_SAOLUU.md."
            % nguon)
    # ĐÂY là chỗ đóng `do2b`. Hai dòng dưới là MỘT mảnh được `ban_va` ghim: phép tiêm D5 thay
    # đúng hai dòng này bằng "chưa khai ⇒ coi là SQLite" (chính sách cũ) và `S8` PHẢI bắt được.
    # Đổi hình dạng hai dòng này thì phải đổi cả `ban_va.TIEM_LOI` — nếu không, phép tiêm TRƯỢT
    # và bộ đo sẽ báo ĐỎ trên một bản vá còn nguyên.
    if kho is None:
        _tu_choi_chua_khai(nguon)
    return kho


def sao_luu(luc=None):
    """Chụp một bản CSDL trước khi nâng cấp. Trả đường dẫn bản sao. **FAIL-CLOSED.**

    Bốn chốt, mỗi chốt ứng với một phép đo ĐỎ trên CHÍNH tệp này:
      (1) `hub.db` KHÔNG tồn tại ⇒ TỪ CHỐI, thay vì `csdl.ket_noi()` TẠO RA một CSDL rỗng rồi
          sao lưu nó. Đo được trên cụm PostgreSQL riêng: bản cũ thoát 0 và trả một tệp 4.096
          byte / 0 BẢNG / `integrity_check = ok` trong khi PostgreSQL giữ 6 đơn và 9.324.000
          đồng — một ĐƯỜNG LÙI GIẢ, và không một dòng cảnh báo. (P-G15-02)
      (2) Ghi ra tệp TẠM rồi `os.replace` sang tên thật. Hỏng giữa đường (hết đĩa) thì KHÔNG
          còn tệp dở nào mang tên bản sao lưu. Đo được: bản cũ để lại `hub-truoc-migrate-*.db`
          **0 byte** và không dọn.
      (3) Ghi DẤU KIỂM `<bản-sao-lưu>.sha256` sau khi tệp đã đóng và đã kiểm cấu trúc.
      (4) Kho đang chạy KHÔNG PHẢI SQLite (theo khai báo) ⇒ TỪ CHỐI — `_kiem_kho_truoc_khi_sao_luu`.
          **CHƯA KHAI cũng TỪ CHỐI**, và đó là chỗ đóng `do2b`: xem `_tu_choi_chua_khai`.

    `luc` = MỐC THỜI GIAN của tên bản sao lưu. `None` (đường chạy thật) ⇒ `datetime.now()`;
    bộ đo truyền một mốc CỐ ĐỊNH để kết quả không phụ thuộc đồng hồ hệ thống — xem
    `_duong_chua_dung` và docs/G22_SAOLUU.md §5.

    Giữ nguyên hai tính chất TỐT của bản trước (AG-05/AG-00 đã đo): tên KHÔNG BAO GIỜ ĐÈ
    (trùng giây thì thêm hậu tố), và dùng API backup của SQLite để lấy bản nhất quán kể cả khi
    có WAL.
    """
    _kiem_kho_truoc_khi_sao_luu()
    if not os.path.exists(cau_hinh.DUONG_DAN_CSDL):
        raise SystemExit(
            "[migrate] TỪ CHỐI: không thấy CSDL tại %s nên KHÔNG có gì để sao lưu.\n"
            "          (Bản cũ vẫn 'thành công' ở đây bằng cách TẠO RA một CSDL rỗng rồi sao "
            "lưu nó —\n           đó là đường lùi giả. Nếu kho đang chạy là PostgreSQL thì "
            "`sao_luu()` này không dùng được;\n           xem docs/G22_SAOLUU.md.)"
            % cau_hinh.DUONG_DAN_CSDL)
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)
    dich = _duong_chua_dung("hub-truoc-migrate", ".db", luc)
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
        with open(tam, "rb+") as f:
            f.flush()
            os.fsync(f.fileno())
        _kiem_cau_truc(tam, toi_thieu_bang=1)
        os.replace(tam, dich)
    except BaseException:
        if os.path.exists(tam):
            try:
                os.remove(tam)
            except OSError:
                pass
        raise
    bam = _bam_tep(dich)
    with open(dich + ".sha256", "w", encoding="utf-8") as f:
        f.write("%s  %s\n" % (bam, os.path.basename(dich)))
    return dich


def _slug(s, dung):
    co_ban = "".join(c.lower() if c.isalnum() else "-" for c in s).strip("-")
    co_ban = "-".join(p for p in co_ban.split("-") if p) or "tenant"
    ma, i = co_ban, 2
    while ma in dung:
        ma = f"{co_ban}-{i}"
        i += 1
    dung.add(ma)
    return ma


def nang_len_v2(kn):
    """v1 → v2: tách vai trò tenant ra tenant_memberships, thêm code/platform_role/active_tenant_id,
    RBAC vào CSDL, carrier_providers, audit có resource_type/resource_id/ket_qua."""
    buoc = []

    # 1. tenants.code
    if "code" not in _cot(kn, "tenants"):
        kn.execute("ALTER TABLE tenants ADD COLUMN code TEXT")
        buoc.append("tenants.code")
    if "cap_nhat_luc" not in _cot(kn, "tenants"):
        kn.execute("ALTER TABLE tenants ADD COLUMN cap_nhat_luc TEXT")
        buoc.append("tenants.cap_nhat_luc")
    dung = set()
    for r in kn.execute("SELECT id, ten, code FROM tenants ORDER BY id"):
        if r[2]:
            dung.add(r[2])
    for r in kn.execute("SELECT id, ten, code FROM tenants ORDER BY id").fetchall():
        if not r[2]:
            kn.execute("UPDATE tenants SET code=? WHERE id=?", (_slug(r[1], dung), r[0]))
    kn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_tenant_code ON tenants(code)")

    # 2. users.platform_role
    cot_user = _cot(kn, "users")
    if "platform_role" not in cot_user:
        kn.execute("ALTER TABLE users ADD COLUMN platform_role TEXT")
        buoc.append("users.platform_role")
    if "vai_tro" in cot_user:
        kn.execute("UPDATE users SET platform_role=vai_tro WHERE vai_tro LIKE 'PLATFORM_%'")

    # 3. sessions.active_tenant_id
    if "active_tenant_id" not in _cot(kn, "sessions"):
        kn.execute("ALTER TABLE sessions ADD COLUMN active_tenant_id INTEGER")
        buoc.append("sessions.active_tenant_id")

    # 4. audit: resource_type / resource_id / ket_qua
    cot_audit = _cot(kn, "audit")
    for c, kieu in (("resource_type", "TEXT"), ("resource_id", "TEXT"),
                    ("ket_qua", "TEXT NOT NULL DEFAULT 'thanh_cong'")):
        if c not in cot_audit:
            kn.execute(f"ALTER TABLE audit ADD COLUMN {c} {kieu}")
            buoc.append("audit." + c)
    kn.execute("UPDATE audit SET resource_type = substr(doi_tuong, 1, instr(doi_tuong, ':')-1),"
               " resource_id = substr(doi_tuong, instr(doi_tuong, ':')+1)"
               " WHERE resource_type IS NULL AND instr(doi_tuong, ':') > 0")

    # 5. Chuyển vai trò tenant của user → tenant_memberships (KHÔNG mất ai)
    if "tenant_id" in cot_user and "vai_tro" in cot_user:
        chuyen = 0
        for r in kn.execute("SELECT id, tenant_id, vai_tro, tao_luc FROM users"
                            " WHERE tenant_id IS NOT NULL").fetchall():
            kn.execute("INSERT OR IGNORE INTO tenant_memberships"
                       " (user_id, tenant_id, role, trang_thai, tao_luc) VALUES (?,?,?,'hoat_dong',?)",
                       (r[0], r[1], r[2], r[3]))
            chuyen += 1
        buoc.append(f"tenant_memberships ← {chuyen} user")
        # phiên đang sống: đặt active_tenant_id theo tenant cũ của user
        kn.execute("UPDATE sessions SET active_tenant_id = ("
                   "SELECT u.tenant_id FROM users u WHERE u.id = sessions.user_id)"
                   " WHERE active_tenant_id IS NULL")

    # 6. carrier_providers — nạp từ registry adapter (không có secret)
    import adapter, adapter_jt, adapter_vtp  # noqa: F401
    for ma, h in adapter.danh_sach_hang().items():
        kn.execute("INSERT INTO carrier_providers (ma, ten, capabilities_json, live_mo, cap_nhat_luc)"
                   " VALUES (?,?,?,?,?) ON CONFLICT(ma) DO UPDATE SET"
                   " ten=excluded.ten, capabilities_json=excluded.capabilities_json,"
                   " live_mo=excluded.live_mo, cap_nhat_luc=excluded.cap_nhat_luc",
                   (ma, h["ten"], json.dumps(h["capabilities"]), 1 if h["live_mo"] else 0, csdl.bay_gio()))
    buoc.append("carrier_providers")

    if "credentials_doi_luc" not in _cot(kn, "carrier_accounts"):
        kn.execute("ALTER TABLE carrier_accounts ADD COLUMN credentials_doi_luc TEXT")
        buoc.append("carrier_accounts.credentials_doi_luc")

    # 7. Bỏ cột cũ SAU khi đã chuyển hết — một nguồn chân lý duy nhất cho vai trò
    cot_user = _cot(kn, "users")
    for c in ("tenant_id", "vai_tro"):
        if c in cot_user:
            kn.execute(f"ALTER TABLE users DROP COLUMN {c}")
            buoc.append(f"bỏ users.{c}")
    return buoc


def nang_len_v3(kn):
    """v3: mã hóa lại mọi secret từ định dạng v1 (XOR+HMAC) sang AES-256-GCM, kèm AAD.
    Giải bằng đường cũ rồi mã lại bằng đường mới — KHÔNG đụng nội dung secret."""
    import bao_mat
    buoc = []
    kn.row_factory = csdl.Row
    doi_cred = doi_wh = 0
    hong = []
    for r in kn.execute("SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                        " webhook_secret_ma_hoa FROM carrier_accounts").fetchall():
        # Một hàng hỏng KHÔNG được làm nổ cả migration — ghi lại rồi đi tiếp, nhưng phải BÁO RA,
        # không im lặng bỏ qua (secret đó sẽ còn ở định dạng cũ cho tới khi người xử lý).
        if bao_mat.la_dinh_dang_cu(r["credentials_ma_hoa"]):
            try:
                ro = bao_mat.giai_ma(r["credentials_ma_hoa"])    # đọc định dạng v1
                kn.execute("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                           (bao_mat.ma_hoa(ro, bao_mat.aad_credentials(r["tenant_id"], r["hang"])), r["id"]))
                doi_cred += 1
            except Exception as e:
                hong.append(f"carrier_account {r['id']} credentials: {type(e).__name__}")
        if bao_mat.la_dinh_dang_cu(r["webhook_secret_ma_hoa"]):
            try:
                ro = bao_mat.giai_ma(r["webhook_secret_ma_hoa"])
                kn.execute("UPDATE carrier_accounts SET webhook_secret_ma_hoa=? WHERE id=?",
                           (bao_mat.ma_hoa(ro, bao_mat.aad_webhook(r["webhook_ma"])), r["id"]))
                doi_wh += 1
            except Exception as e:
                hong.append(f"carrier_account {r['id']} webhook_secret: {type(e).__name__}")
    buoc.append(f"AES-256-GCM: {doi_cred} credentials + {doi_wh} webhook secret")
    if hong:
        buoc.append("KHÔNG mã hóa lại được (giữ nguyên định dạng cũ, CẦN NGƯỜI XỬ): " + "; ".join(hong))
    return buoc


def nang_len_v4(kn):
    """v4: đưa mọi secret sang định dạng `v3$<key_id>$...` để từ nay XOAY KHÓA ĐƯỢC.

    Bản mã v2 không mang định danh khóa, nên trước v4 đổi khóa là mọi bản mã cũ thành rác.
    Lượt này giải bằng đúng đường của định dạng đang có rồi mã lại bằng khóa HIỆN HÀNH, kèm AAD
    như cũ — KHÔNG đụng nội dung secret, KHÔNG sinh khóa mới (khóa mới là việc của bao_mat.xoay_khoa).
    Một hàng không giải được thì ghi ra rồi đi tiếp, giữ nguyên bản cũ cho người xử.
    """
    import bao_mat
    kq = bao_mat.ma_hoa_lai_carrier_accounts(kn)
    buoc = [f"key_id (v3) khóa '{kq['key_id']}': {kq['so_credentials']} credentials"
            f" + {kq['so_webhook_secret']} webhook secret trên {kq['so_hang_da_doc']} tài khoản hãng"]
    if kq["hong"]:
        buoc.append("KHÔNG mã hóa lại được (giữ nguyên định dạng cũ, CẦN NGƯỜI XỬ): "
                    + "; ".join(kq["hong"]))
    return buoc


def nang_len_v5(kn):
    """v5: đổi giá trị trạng thái import_batch cũ sang bộ chuẩn của SHARED_CONTRACTS mục 6.
    Mã đã tự đọc được giá trị cũ, lượt này chỉ để dọn cho nhất quán."""
    buoc = []
    cot = [r[1] for r in kn.execute("PRAGMA table_info(import_batch)")]
    if "loi" not in cot:
        kn.execute("ALTER TABLE import_batch ADD COLUMN loi TEXT")
        buoc.append("import_batch.loi")
    doi = 0
    for cu, moi in (("moi", "READY"), ("da_duyet_mot_phan", "PARTIAL_FAILED"), ("xong", "COMPLETED")):
        con = kn.execute("UPDATE import_batch SET trang_thai=? WHERE trang_thai=?", (moi, cu))
        doi += con.rowcount
    buoc.append(f"trang_thai import_batch: đổi {doi} dòng sang bộ chuẩn")
    la = [r[0] for r in kn.execute(
        "SELECT DISTINCT trang_thai FROM import_batch WHERE trang_thai NOT IN"
        " ('UPLOADED','PARSING','VALIDATING','READY','APPROVED','PROCESSING','COMPLETED',"
        "'PARTIAL_FAILED','FAILED')")]
    if la:
        buoc.append("CÒN giá trị lạ (CẦN NGƯỜI XỬ): " + ", ".join(map(str, la)))
    return buoc


def nang_len_v6(kn):
    """v6: thêm users.khoa_den (khóa TẠM) và gỡ các tài khoản đang bị khóa vĩnh viễn
    DO ĐOÁN SAI MẬT KHẨU. Không đụng tài khoản do quản trị cố ý khóa — nhưng schema cũ
    không phân biệt được hai loại, nên chỉ thêm cột và để nguyên trạng thái hiện có."""
    buoc = []
    if "khoa_den" not in [r[1] for r in kn.execute("PRAGMA table_info(users)")]:
        kn.execute("ALTER TABLE users ADD COLUMN khoa_den TEXT")
        buoc.append("users.khoa_den (khóa tạm thay cho khóa vĩnh viễn khi đoán sai)")
    so_khoa = kn.execute("SELECT COUNT(*) FROM users WHERE trang_thai='khoa'").fetchone()[0]
    if so_khoa:
        buoc.append(f"GHI CHÚ: còn {so_khoa} tài khoản ở trạng thái 'khoa' — schema cũ không phân "
                    "biệt được do quản trị khóa hay do đoán sai, người vận hành tự xem và mở")
    return buoc


def nang_len_v7(kn):
    """v7: gộp ba đợt WAVE 1 — AG-02 ORDERS (G04), AG-03 WEBHOOK (G06), AG-01 hạn mức nhập.

    TOÀN BỘ là thao tác THÊM: `ADD COLUMN`, `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX
    IF NOT EXISTS`. Không `DROP`, không `DELETE`, không `UPDATE` dữ liệu sẵn có, không đổi
    kiểu hay ràng buộc cột cũ — nên dòng cũ giữ nguyên và mã cũ vẫn đọc được bảng.

    Cột `NOT NULL` duy nhất (`wh_su_kien.can_soat`) có `DEFAULT 0`, nên SQLite điền được
    cho dòng đã có. Mọi cột khác để NULL cố ý: NULL ở đây nghĩa là "sự kiện có trước đợt
    này, hãng không gửi thông tin đó" — khác hẳn với 0 hay chuỗi rỗng.
    """
    buoc = []

    # ---- AG-02 ORDERS (G04): don_hang + don_mat_hang -------------------------
    co = [r[1] for r in kn.execute("PRAGMA table_info(don_hang)")]
    them_don = [
        ("external_reference", "TEXT"),
        ("approved_by", "INTEGER REFERENCES users(id)"),
        ("approved_luc", "TEXT"),
        ("ly_do_tu_choi", "TEXT"),
        ("tu_choi_boi", "INTEGER REFERENCES users(id)"),
        ("tu_choi_luc", "TEXT"),
        ("nguoi_gui_tinh", "TEXT"), ("nguoi_gui_quan", "TEXT"),
        ("nguoi_gui_xa", "TEXT"), ("nguoi_gui_buu_chinh", "TEXT"),
        ("nguoi_nhan_tinh", "TEXT"), ("nguoi_nhan_quan", "TEXT"),
        ("nguoi_nhan_xa", "TEXT"), ("nguoi_nhan_buu_chinh", "TEXT"),
    ]
    n = 0
    for ten, kieu in them_don:
        if ten not in co:
            kn.execute(f"ALTER TABLE don_hang ADD COLUMN {ten} {kieu}")
            n += 1
    if n:
        buoc.append(f"don_hang +{n} cột (G04: duyệt/từ chối/địa chỉ hành chính/mã đối chiếu)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_don_extref ON don_hang(tenant_id, external_reference)")

    if not _co_bang(kn, "don_mat_hang"):
        kn.execute("""
            CREATE TABLE don_mat_hang (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tenant_id INTEGER NOT NULL REFERENCES tenants(id),
              don_id INTEGER NOT NULL REFERENCES don_hang(id),
              stt INTEGER NOT NULL,
              ten TEXT NOT NULL,
              ma_sku TEXT NOT NULL DEFAULT '',
              so_luong INTEGER NOT NULL DEFAULT 1,
              don_gia INTEGER NOT NULL DEFAULT 0,
              khoi_luong_gram INTEGER NOT NULL DEFAULT 0,
              ghi_chu TEXT NOT NULL DEFAULT '',
              tao_luc TEXT NOT NULL,
              UNIQUE (don_id, stt)
            )""")
        buoc.append("bảng MỚI don_mat_hang (tiền là số nguyên ĐỒNG, khối lượng là GRAM — cấm float)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_mh_don ON don_mat_hang(don_id)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_mh_tenant ON don_mat_hang(tenant_id)")

    # ---- AG-03 WEBHOOK (G06): wh_su_kien ------------------------------------
    cw = [r[1] for r in kn.execute("PRAGMA table_info(wh_su_kien)")]
    them_wh = [
        ("hang_ma_goc", "TEXT"),
        ("hang_mo_ta_goc", "TEXT"),
        ("hang_su_kien_goc", "TEXT"),
        ("anh_xa_do_tin_cay", "TEXT"),
        ("anh_xa_nguon", "TEXT"),
        ("can_soat", "INTEGER NOT NULL DEFAULT 0"),
        ("hang_moc_thoi_gian", "TEXT"),
        ("don_id", "INTEGER REFERENCES don_hang(id)"),
        ("trang_thai_chuan", "TEXT"),
    ]
    m = 0
    for ten, kieu in them_wh:
        if ten not in cw:
            kn.execute(f"ALTER TABLE wh_su_kien ADD COLUMN {ten} {kieu}")
            m += 1
    if m:
        buoc.append(f"wh_su_kien +{m} cột (G06: mã gốc hãng, độ tin cậy ánh xạ, cần soát, mốc hãng)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_wh_don  ON wh_su_kien(don_id, hang_moc_thoi_gian)")
    kn.execute("CREATE INDEX IF NOT EXISTS ix_wh_soat ON wh_su_kien(can_soat, id)")

    # ---- AG-01: hạn mức nhập ------------------------------------------------
    # `gioi_han.py` tự tạo bảng này khi dùng lần đầu, nên hệ chạy được dù chưa migrate.
    # Tạo sẵn ở đây để schema khai báo đủ ở một chỗ, không phụ thuộc lượt gọi đầu tiên.
    if not _co_bang(kn, "han_muc_nhap_thang"):
        kn.execute("""
            CREATE TABLE han_muc_nhap_thang (
              tenant_id INTEGER NOT NULL REFERENCES tenants(id),
              thang TEXT NOT NULL,
              so_don_nhap INTEGER NOT NULL DEFAULT 0,
              so_dong INTEGER NOT NULL DEFAULT 0,
              so_file INTEGER NOT NULL DEFAULT 0,
              so_byte INTEGER NOT NULL DEFAULT 0,
              cap_nhat_luc TEXT,
              PRIMARY KEY (tenant_id, thang)
            )""")
        buoc.append("bảng MỚI han_muc_nhap_thang (bộ đếm hạn mức nhập, sống qua restart)")

    return buoc


def chay_ddl_trong_giao_dich(kn, ddl):
    """Chạy một khối DDL mà KHÔNG chốt giao dịch đang mở. Dùng thay `executescript`.

    `kn.executescript()` tự COMMIT giao dịch đang mở trước khi chạy — lặng lẽ, không báo gì.
    Đo được ngày 15/10/2026 (py 3.9.6): sau `BEGIN IMMEDIATE` thì `in_transaction` là True,
    sau một `executescript` thành True→False, và `COMMIT` sau đó nổ "cannot commit - no
    transaction is active". Hậu quả nặng hơn một lỗi cú pháp: lượt nâng cấp nạp 5 khối DDL
    của G07–G11 qua `executescript`, nên migration CHƯA BAO GIỜ nguyên tử — hỏng sau khối
    đầu là để lại CSDL nâng cấp nửa vời, trong khi thông báo lỗi vẫn hứa "rollback". Đúng
    dạng §12.2: hệ thống nói sai về chính nó.

    Tách câu bằng `sqlite3.complete_statement`, KHÔNG bằng `ddl.split(";")`: khối
    `CREATE TRIGGER ... BEGIN SELECT RAISE(ABORT,'...'); END;` có dấu `;` BÊN TRONG, nên cắt
    theo dấu `;` là sinh ra những câu cụt vẫn "chạy được" một phần — hỏng im lặng.
    """
    cau, dem = "", 0
    for dong in ddl.splitlines(True):
        cau += dong
        if csdl.cau_sql_du(cau) and cau.strip():
            kn.execute(cau)
            dem += 1
            cau = ""
    con = cau.strip()
    if con and not con.lstrip().startswith("--"):
        raise ValueError(f"DDL còn câu chưa trọn sau khi tách: {con[:120]!r}")
    return dem


def nang_len_v8(kn):
    """v8: gộp năm hằng DDL của đợt 3 — G07 tài chính · G08 gói dịch vụ · G09 harness hãng
    · G10 công việc AI · G11 quan sát.

    **Không viết lại DDL ở đây.** Năm hằng nằm trong module của chính nó
    (`tai_chinh.DDL_G07`, `goi_dich_vu.DDL_G08`, `harness_hang.DDL_G09`, `ai_job.DDL_G10`,
    `quan_sat.DDL_G11`) và migration CHẠY ĐÚNG CHUỖI ĐÓ. Chép sang đây là tạo bản thứ hai,
    và hai bản nội dung là hai bản sẽ lệch nhau — lúc đó bộ thử của agent chạy một chuỗi còn
    CSDL thật mang một chuỗi khác, không ai thấy cho tới khi có cột thiếu.

    AG-00 đã đo trên cả năm chuỗi (bỏ lời bình trước khi quét): **27 bảng · 21 index ·
    4 trigger · 0 DROP · 0 ALTER · 0 DELETE ngoài trigger · 0 cột REAL/FLOAT · 0 trùng tên**
    — cả giữa các agent với nhau và với 23 bảng đang có. Toàn bộ là `IF NOT EXISTS` nên chạy
    lại vô hại.

    Bốn trigger của G07 là **chốt chặn SỬA/XOÁ bút toán** (`BEFORE UPDATE/DELETE ... RAISE
    (ABORT)`) — tức là ngược với xoá. Đừng bắt nhầm chữ `DELETE` trong đó: §17 đòi bút toán
    bất biến, và trigger là cách cưỡng chế bằng CSDL thay vì bằng lời dặn.
    """
    buoc = []
    # Nạp muộn, trong hàm: năm module này không cần có mặt lúc `migrate` được import, và
    # một module hỏng không được làm chết cả đường migration.
    import ai_job
    import goi_dich_vu
    import harness_hang
    import quan_sat
    import tai_chinh

    for ten, ddl in (("G07 tài chính + đối soát", tai_chinh.DDL_G07),
                     ("G08 gói dịch vụ + mức dùng", goi_dich_vu.DDL_G08),
                     ("G09 harness hãng", harness_hang.DDL_G09),
                     ("G10 công việc AI", ai_job.DDL_G10),
                     ("G11 quan sát", quan_sat.DDL_G11)):
        truoc = {r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index','trigger')")}
        chay_ddl_trong_giao_dich(kn, ddl)
        sau = {r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('table','index','trigger')")}
        them = sorted(sau - truoc)
        buoc.append(f"{ten}: +{len(them)} đối tượng" + (f" ({', '.join(them[:4])}…)" if them else ""))
    return buoc


def nang_len_v9(kn):
    """v9: bảng trạng thái của GIỚI HẠN TẦN SUẤT — G19/AG-02.

    **Không viết lại DDL ở đây.** Hằng nằm trong module của chính nó (`gioi_han.DDL_GIOI_HAN`) và
    migration CHẠY ĐÚNG HẰNG ĐÓ — cùng lý do đã ghi ở `nang_len_v8`: chép sang đây là tạo bản thứ
    hai, và hai bản nội dung là hai bản sẽ lệch nhau.

    Vì sao cần bước này (không chỉ để `CREATE TABLE IF NOT EXISTS` trong module tự lo):
    PHẦN A trước G19 giữ bộ đếm **trong bộ nhớ MỘT tiến trình**, nên trần thực = khai báo × số bản
    (đo được: khai 20 ⇒ **20/40/80/160** với N=1/2/4/8) và **mất sạch khi khởi động lại**. Nay
    trạng thái nằm trong CSDL. Module tự tạo bảng khi chạy, nhưng CSDL **đã tồn tại** phải được
    nâng cấp TƯỜNG MINH: để nó tự lo thì lần ghi đầu tiên mới phát hiện thiếu bảng, và lúc đó
    đường ghi đang nằm trong giao dịch nghiệp vụ — hỏng ở giữa đường chứ không hỏng lúc nâng cấp.

    `moc` là **epoch giây** (`time.time()`), KHÔNG phải `monotonic`: monotonic là thang riêng của
    từng tiến trình, không so sánh được qua tiến trình — dùng nó làm mốc thì trần lại thủng im lặng,
    đúng cái lỗi bước này đóng.
    """
    buoc = []
    import gioi_han

    # `chay_ddl_trong_giao_dich` nhận MỘT CHUỖI có các câu KẾT BẰNG `;` (nó tách theo `;` và
    # báo lỗi nếu còn câu chưa trọn), và đó là dạng của `DDL_G07..G11`. `DDL_GIOI_HAN` của G19 lại
    # là một TUPLE từng câu KHÔNG có `;` (module tự `execute()` từng câu). Không sửa helper dùng
    # chung — helper đang phục vụ v8 và đã được đo; thích ứng Ở ĐÂY, và ghi rõ vì sao hai dạng khác
    # nhau để người sau không tưởng một trong hai là sai.
    ddl = gioi_han.DDL_GIOI_HAN
    if not isinstance(ddl, str):
        ddl = ";\n".join(c.strip().rstrip(";") for c in ddl) + ";"

    truoc = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    chay_ddl_trong_giao_dich(kn, ddl)
    sau = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    them = sorted(sau - truoc)
    buoc.append("G19 giới hạn tần suất (kho trong CSDL): "
                f"+{len(them)} đối tượng" + (f" ({', '.join(them)})" if them else " (đã có sẵn)"))
    return buoc


def nang_len_v10(kn):
    """v10: 9 chỉ mục của LỚP TRUY VẤN G12 — `truy_van.DDL_G12Q` (G19/C6).

    **Không viết lại DDL ở đây.** Hằng nằm trong module của chính nó (`truy_van.DDL_G12Q`) và
    migration CHẠY ĐÚNG HẰNG ĐÓ — cùng lý do đã ghi ở `nang_len_v8`: chép sang đây là tạo bản
    thứ hai, và hai bản nội dung là hai bản sẽ lệch nhau. Đo ở `thu_g19c6_v10` ca E: thay hằng
    của module bằng một chỉ mục đánh dấu thì CSDL nhận đúng chỉ mục đánh dấu đó — bằng chứng
    migration đọc hằng lúc CHẠY, không phải bản chép.

    VÌ SAO BƯỚC NÀY PHẢI TỒN TẠI (đây là toàn bộ lý do của bản vá): route `GET /api/v2/don` đã
    nối vào `truy_van`, nhưng một CSDL **ĐANG Ở v9** đã chạy xong `nang_len_v9` và sẽ KHÔNG BAO
    GIỜ chạy lại nó (`chay()` chỉ đi các bước có `pb < n`). Nhét `DDL_G12Q` vào thân v9 chỉ giúp
    CSDL MỚI (đi qua cả thang) và CSDL còn ở v8; CSDL đã ở v9 thì `nang_len_v9` không chạy nữa,
    nên 9 chỉ mục KHÔNG BAO GIỜ được tạo — im lặng, vì truy vấn vẫn trả đúng kết quả, chỉ chậm.
    Bước v10 biến trạng thái "đã ở v9" thành một mốc nâng cấp THẬT.

    DDL chỉ có `CREATE INDEX IF NOT EXISTS` nên gọi lại vô hại: chạy `migrate.chay()` trên CSDL
    đã ở v10 thì `chay()` về sớm, còn gọi THẲNG hàm này hai lượt thì lượt hai không tạo thêm đối
    tượng nào (đo ở `thu_g19c6_v10`, ca C2).
    """
    buoc = []
    # Nạp muộn, trong hàm: cùng lý do như `nang_len_v8` — module không cần có mặt lúc `migrate`
    # được import, và một module hỏng không được làm chết cả đường migration.
    import truy_van

    truoc = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    chay_ddl_trong_giao_dich(kn, truy_van.DDL_G12Q)
    sau = {r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    them = sorted(sau - truoc)
    buoc.append("G19/C6 chỉ mục lớp truy vấn G12 (`truy_van.DDL_G12Q`): "
                f"+{len(them)} đối tượng" + (f" ({', '.join(them)})" if them else " (đã có sẵn)"))
    return buoc


# Chờ tối đa bao lâu để lấy khoá nâng cấp. 60 giây: đủ cho một lượt nâng cấp thật
# (lượt v1→v8 trên CSDL rỗng đo được dưới 1 giây; CSDL có dữ liệu thì lâu hơn), và ngắn hơn
# mọi ngưỡng chờ của người. Hết giờ thì NÉM, không chạy chồng — §13 của chỉ thị G12:
# thử lại vô hạn không phải là phương án xử lý.
KHOA_CHO_GIAY = 60


# `BEGIN IMMEDIATE` trong `chay()` làm BA việc cùng lúc, nên không tách ra được:
#   1. KHOÁ XUYÊN TIẾN TRÌNH. `csdl.khoa_ghi` là RLock của Python — nó chỉ phủ MỘT tiến
#      trình, nên hai lượt `python3 -m migrate` song song đi xuyên qua nó như không có gì.
#      SQLite khoá ở tầng tệp nên chặn được thật (đo ca L: tiến trình hai nhận
#      "database is locked", và vào được ngay khi bên kia nhả).
#   2. RANH GIỚI LÙI CHO CẢ DDL. `with kn:` của python KHÔNG mở giao dịch cho
#      `CREATE`/`ALTER` — chỉ cho DML (đo ca J: ép hỏng giữa chừng thì INSERT lùi, còn
#      bảng vừa CREATE Ở LẠI). Nên câu cũ "CSDL giữ nguyên trạng thái trước (transaction
#      rollback)" ĐÚNG VỚI DML và SAI VỚI DDL — một lời nói sai về chính hệ thống, đúng
#      dạng §12.2. `BEGIN` tường minh thì lùi sạch cả DDL (đo ca K).
#   3. CHỐT ĐỌC-RỒI-LÀM. Phiên bản đọc ở đầu hàm nằm ngoài mọi khoá; đọc lại bên trong
#      khoá thì tiến trình đến sau thấy việc đã xong và nhường, thay vì nâng cấp lần hai.
def chay(im_lang=False):
    def noi(*a):
        if not im_lang:
            print(*a)

    # CHỐT (4) PHẢI CHẠY TRƯỚC KHI `csdl.mo()` CHẠM ĐĨA, khi CSDL CHƯA TỒN TẠI. `csdl.mo()` TẠO
    # `hub.db` nếu thiếu; đo được (17/10/2026, dispatch `g22-a1-cauhinh`): một lượt `migrate.py`
    # CHƯA KHAI kho vẫn để lại `hub.db` 200.704 byte / đủ 51 bảng rồi mới TỪ CHỐI. Tệp đó chính
    # là "hub.db CŨ còn sót" của P-G15-02 `do2b` — lượt sau nhìn vào nó KHÔNG phân biệt được với
    # dữ liệu đang phục vụ. Từ chối TRƯỚC khi tạo thì một lượt hỏng không để lại manh mối GIẢ.
    # Dùng `isfile`, KHÔNG dùng `exists`: mảnh nguồn `os.path.exists(...)` của `sao_luu()` là một
    # phần của bản vá bị `ban_va.MANH_VA` ghim ĐÚNG MỘT LẦN — thêm một bản y hệt là phép đo của
    # AG-02 tự báo "tệp đã trôi". CSDL ĐÃ TỒN TẠI: giữ nguyên đường cũ — `sao_luu()` mới là chỗ
    # kiểm (chỉ khi có nâng cấp), nên `migrate.py` trên CSDL đã ở phiên bản mới nhất vẫn chạy.
    if not os.path.isfile(cau_hinh.DUONG_DAN_CSDL):
        _kiem_kho_truoc_khi_sao_luu()

    csdl.mo()  # tạo bảng mới (IF NOT EXISTS) nếu thiếu
    kn_kiem = csdl.ket_noi()
    pb = kn_kiem.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
    truoc = dem_dong(kn_kiem)
    kn_kiem.close()

    if pb >= csdl.PHIEN_BAN_SCHEMA:
        noi(f"[migrate] CSDL đã ở phiên bản {pb} — không cần nâng cấp.")
        return {"phien_ban": pb, "da_nang": False}

    noi(f"[migrate] Phiên bản hiện tại: {pb} → đích: {csdl.PHIEN_BAN_SCHEMA}")
    ban_sao = sao_luu()
    noi(f"[migrate] Đã backup: {ban_sao}")
    noi(f"[migrate] Số dòng trước: {truoc}")

    kn = csdl.ket_noi(timeout=KHOA_CHO_GIAY, tuong_minh=True)
    # THỨ TỰ BẮT BUỘC: `PRAGMA foreign_keys` phải đặt TRƯỚC `BEGIN`. Đo được (ca M):
    # trong giao dịch, SQLite BỎ QUA lệnh này không báo lỗi gì — đổi thứ tự là chạy cả
    # migration với khoá ngoại BẬT mà không ai thấy.
    kn.execute("PRAGMA foreign_keys=OFF")
    kn.execute("PRAGMA busy_timeout=%d" % (KHOA_CHO_GIAY * 1000))
    # `BEGIN IMMEDIATE` làm BA việc cùng lúc — xem khối chú thích ở KHOA_CHO_GIAY.
    try:
        kn.execute("BEGIN IMMEDIATE")
    except csdl.LoiVanHanh as e:
        kn.close()
        noi(f"[migrate] KHÔNG lấy được khoá sau {KHOA_CHO_GIAY}s: {e}")
        noi("[migrate] Có tiến trình khác đang nâng cấp CSDL này. KHÔNG chạy chồng.")
        raise
    # ĐỌC LẠI phiên bản BÊN TRONG khoá. Lượt đọc ở đầu hàm nằm ngoài mọi khoá, nên giữa nó
    # và chỗ này một tiến trình khác có thể đã nâng xong. Đây là đua đọc-rồi-làm kinh điển.
    pb_trong = kn.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
    if pb_trong >= csdl.PHIEN_BAN_SCHEMA:
        kn.execute("ROLLBACK")
        kn.close()
        noi(f"[migrate] Tiến trình khác đã nâng lên {pb_trong} trong lúc chờ khoá — không làm lại.")
        return {"phien_ban": pb_trong, "da_nang": False, "nhuong": True}
    pb = pb_trong
    try:
        buoc = []
        if pb < 2:
            buoc += nang_len_v2(kn)
        if pb < 3:
            buoc += nang_len_v3(kn)
        if pb < 4:
            buoc += nang_len_v4(kn)
        if pb < 5:
            buoc += nang_len_v5(kn)
        if pb < 6:
            buoc += nang_len_v6(kn)
        if pb < 7:
            buoc += nang_len_v7(kn)
        if pb < 8:
            buoc += nang_len_v8(kn)
        if pb < 9:
            buoc += nang_len_v9(kn)
        if pb < 10:
            buoc += nang_len_v10(kn)
        kn.execute("INSERT OR REPLACE INTO schema_version (phien_ban, ap_dung_luc, ghi_chu)"
                   " VALUES (?,?,?)",
                   (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio(), "; ".join(buoc)))
        kn.execute("COMMIT")
    except Exception as e:
        try:
            kn.execute("ROLLBACK")
        except csdl.LoiCSDL:
            pass        # đã tự lùi rồi; không che lỗi gốc bằng lỗi lùi
        kn.close()
        noi(f"[migrate] HỎNG: {type(e).__name__}: {e}")
        noi(f"[migrate] Đã ROLLBACK — kể cả CREATE/ALTER (BEGIN tường minh, đo ca K). Backup: {ban_sao}")
        raise
    sau = dem_dong(kn)
    kn.close()

    # KIỂM CHỨNG bảo toàn dữ liệu — không bảng nào được mất dòng
    mat = {b: (truoc.get(b, 0), sau.get(b, 0)) for b in truoc if sau.get(b, 0) < truoc.get(b, 0)}
    if mat:
        noi(f"[migrate] CẢNH BÁO MẤT DỮ LIỆU: {mat} — khôi phục từ {ban_sao}")
        khoi_phuc(ban_sao)
        raise SystemExit(2)

    csdl.dong()
    quyen.seed()
    # Quên mọi cache SCHEMA sau khi nâng cấp. Thiếu bước này thì một tiến trình đang chạy
    # vẫn nhớ "bảng chưa có" và tiếp tục đi đường lùi — hỏng im lặng, vì đường lùi vẫn trả
    # kết quả hợp lệ, chỉ là kết quả của schema cũ.
    for mod, ham in (("billing", "quen_cache_phien_ban"), ("webhook", "xoa_cache_cot"),
                     ("don_hang", "quen_cache_schema"), ("tai_chinh", "quen_cache_bang"),
                     ("goi_dich_vu", "nap_lai_bang")):
        try:
            __import__(mod)
            f = getattr(sys.modules[mod], ham, None)
            if f:
                f()
        except Exception as e:
            noi(f"[migrate] bỏ qua {mod}.{ham}: {type(e).__name__}: {e}")
    noi(f"[migrate] Bước đã làm: {'; '.join(buoc)}")
    noi(f"[migrate] Số dòng sau: {sau}  → bảo toàn ĐẠT")
    noi(f"[migrate] Xong, phiên bản {csdl.PHIEN_BAN_SCHEMA}. Rollback nếu cần: "
        f"python3 app/migrate.py --rollback {ban_sao}")
    return {"phien_ban": csdl.PHIEN_BAN_SCHEMA, "da_nang": True, "backup": ban_sao,
            "truoc": truoc, "sau": sau, "buoc": buoc}


def khoi_phuc(duong_backup, toi_da_biet_chua_kiem_duoc=False, luc=None):
    """Rollback CSDL về đúng tệp backup — **FAIL-CLOSED**.

    ====== BẤT BIẾN ======
    Hỏng ở BẤT KỲ bước nào thì CSDL ĐANG CHẠY phải còn NGUYÊN VẸN, và phải có thông báo nói
    rõ hỏng ở đâu. Ba bước, theo đúng thứ tự này:
      1. KIỂM BẢN SAO LƯU **TRƯỚC KHI ĐỤNG** CSDL đang chạy (cấu trúc + dấu kiểm + phiên bản);
      2. CẤT bản đang chạy vào một tên KHÔNG BAO GIỜ ĐÈ, và kiểm bản cất đọc được;
      3. GHI BẢN MỚI RA TỆP TẠM cùng thư mục, kiểm lại, RỒI MỚI `os.replace`.
    Bước 3 là vế bắt được "hết đĩa giữa đường". Đo được trên bản gốc: CSDL đích bị để lại ở
    280.576 byte với `DatabaseError: database disk image is malformed` và MẤT SẠCH 20 bảng.

    `toi_da_biet_chua_kiem_duoc=True` là ĐƯỜNG THOÁT cho người trực đã biết rõ tệp này chưa
    kiểm chứng được (bỏ chốt dấu kiểm + chốt tụt schema). Mặc định là TỪ CHỐI.

    `luc` = MỐC THỜI GIAN của tên BẢN CẤT `hub-truoc-rollback-*`. `None` (đường chạy thật) ⇒
    `datetime.now()`; bộ đo truyền một mốc CỐ ĐỊNH để ba lượt liên tiếp rơi chắc chắn vào cùng
    một mốc và ca đo KHÔNG phụ thuộc đồng hồ hệ thống — xem `_duong_chua_dung`.
    """
    tt = _kiem_ban_sao_luu(duong_backup, bat_buoc_dau_kiem=not toi_da_biet_chua_kiem_duoc)
    os.makedirs(THU_MUC_SAO_LUU, exist_ok=True)

    if os.path.exists(cau_hinh.DUONG_DAN_CSDL) and not toi_da_biet_chua_kiem_duoc:
        try:
            _hien_tai = _kiem_cau_truc(cau_hinh.DUONG_DAN_CSDL, toi_thieu_bang=1)["phien_ban"]
        except SystemExit:
            # CSDL đang chạy CÓ nhưng KHÔNG đọc được (đang hỏng, đang bị khoá, một tiến trình
            # khác đang ghi). Cố ý ĐI TIẾP chứ không TỪ CHỐI: khôi phục chính là đường CỨU một
            # CSDL hỏng, nên từ chối ở đây là chặn đúng lúc cần nhất. Cái mất là chốt TỤT SCHEMA
            # cho riêng lượt này — và cái mất đó ĐƯỢC NÓI RA ở thông báo dưới, không im lặng.
            _hien_tai = None
            print("[migrate] GHI CHÚ: không đọc được phiên bản của CSDL đang chạy nên BỎ QUA "
                  "chốt TỤT SCHEMA cho lượt này.")
        if _hien_tai and tt["phien_ban"] < _hien_tai:
            raise SystemExit(
                "[migrate] TỪ CHỐI: TỤT SCHEMA. Bản sao lưu ở phiên bản **v%d**, CSDL đang chạy "
                "ở **v%d**.\n          Khôi phục sẽ bỏ rơi dữ liệu của %d phiên bản migration. "
                "Đo được: v6 đè lên v9 làm CSDL còn\n          20 bảng thay vì 51 và tổng tiền "
                "rơi từ 34.336.000 xuống 1.298.000 đồng — KHÔNG một lời cảnh báo.\n"
                "          Nếu đây đúng là ý định, chạy lại với `toi_da_biet_chua_kiem_duoc=True`."
                % (tt["phien_ban"], _hien_tai, _hien_tai - tt["phien_ban"]))

    cat_di = _duong_chua_dung("hub-truoc-rollback", ".db", luc)
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
            "[migrate] KHÔI PHỤC HỎNG: %s\n"
            "          CSDL đang chạy KHÔNG bị đụng (bản mới chỉ nằm ở tệp tạm, đã dọn).\n"
            "          Bản cất trước khi khôi phục: %s" % (_e, cat_di))
    print("[migrate] Đã khôi phục từ %s (kiểm cấu trúc + dấu kiểm TRƯỚC khi đè). "
          "Bản trước khi khôi phục cất ở %s" % (duong_backup, cat_di))


if __name__ == "__main__":
    if "--kiem" in sys.argv:
        csdl.mo()
        print(f"Phiên bản schema trong CSDL: {csdl.phien_ban_hien_tai()} (mã nguồn: {csdl.PHIEN_BAN_SCHEMA})")
    elif "--rollback" in sys.argv:
        # VÌ SAO ĐƯỜNG THOÁT NÀY **PHẢI** CÓ Ở DÒNG LỆNH: mọi bản sao lưu sinh ra TRƯỚC bản vá
        # này đều KHÔNG có tệp `.sha256` đi kèm, nên mặc định chúng bị TỪ CHỐI. Một đường thoát
        # chỉ gọi được từ Python thì với người trực đang gõ `migrate.py --rollback` nó KHÔNG TỒN
        # TẠI — và một chốt không có đường thoát sẽ bị gỡ bằng cách tệ nhất: sửa mã lúc 3 giờ sáng.
        khoi_phuc(sys.argv[sys.argv.index("--rollback") + 1],
                  toi_da_biet_chua_kiem_duoc="--toi-da-biet-chua-kiem-duoc" in sys.argv)
    else:
        chay()
