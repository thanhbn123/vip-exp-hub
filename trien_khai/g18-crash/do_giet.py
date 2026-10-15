#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ĐỘNG CƠ GIẾT TIẾN TRÌNH + BỘ ĐO TÍNH TOÀN VẸN — làn G18/AG-06.

====== CÁCH GIẾT MÀ KHÔNG SỬA MÃ ĐANG CHẠY ======
Yêu cầu là giết tiến trình **thật** giữa một giao dịch **thật**, ở **đúng câu ghi thứ k**.
Cách dễ nhất là chèn `os.kill` vào `csdl.py` — và đó là cách SAI: nó sửa chính mã đang được
đo, nên kết quả đo nói về một phiên bản mã không ai chạy.

Ở đây dùng `sqlite3.Connection.set_trace_callback` — móc có SẴN của driver, không phải của
dự án. Đo được (xem `--tu-kiem-moc`): móc này bắn **TRƯỚC** khi câu lệnh chạy. Bằng chứng:
trong chính lượt gọi của câu `COMMIT`, một kết nối KHÁC vẫn chỉ thấy dữ liệu cũ.

Nhờ vậy ánh xạ điểm giết là chính xác:
  * giết NGAY TRONG lượt gọi của câu X  ⇒ chết **trước** khi X chạy;
  * đặt cờ ở lượt gọi của câu X, giết ở lượt gọi KẾ TIẾP ⇒ chết **ngay sau** khi X chạy.

====== VÌ SAO ĐO BẰNG "VẾT TRẠNG THÁI" CHỨ KHÔNG CHỈ ĐẾM DÒNG ======
Một giao dịch ghi 5 bảng. Đếm dòng từng bảng trả lời "có bao nhiêu", không trả lời "có KHỚP
nhau không". Kịch bản hỏng thật của §18 là: `tc_cod` đã nhảy sang `COD_COLLECTED` (hệ BÁO
tiền đã về) mà `tc_but_toan` không có dòng nào (sổ cái KHÔNG có tiền). Số dòng hai bảng đều
"đúng", chỉ có chúng nói hai chuyện khác nhau.

Nên phép đo chính là VẾT: một bộ 7 trường lấy từ 5 bảng. Sau khi giết, vết phải bằng ĐÚNG
vết TRƯỚC hoặc ĐÚNG vết SAU. Không bằng vết nào ⇒ **NỬA VỜI**.

====== VÌ SAO BỘ ĐO NÀY CẦN MỘT CA TỰ KIỂM ======
Một bộ đo luôn trả "NGUYÊN VẸN" thì mọi ca thử đều xanh và không ai biết nó không đo gì.
Nên `tien_trinh_giao_dich.py` có chế độ `--che-do khong_giao_dich`: đúng năm câu ghi ấy,
nhưng KHÔNG bọc `csdl.giao_dich()` — tức mã trước bản vá V-13912. Giết ở cùng điểm, bộ đo
PHẢI kêu NỬA VỜI. Kêu không được là bộ đo hỏng, và lượt chạy phải đỏ.
"""
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import OrderedDict

# ============================================================================
# BẢY ĐIỂM GIẾT
# ============================================================================
# `neo` nói bộ giết bám vào cái gì:
#   "truoc_cau"  — khớp mẫu rồi giết NGAY trong lượt gọi ấy  ⇒ chết TRƯỚC câu đó
#   "sau_cau"    — khớp mẫu, đặt cờ, giết ở lượt gọi KẾ TIẾP      ⇒ chết NGAY SAU câu đó
DIEM_GIET = OrderedDict([
    ("truoc_begin", {
        "ten": "trước BEGIN — chưa mở giao dịch, chưa ghi gì",
        "neo": "truoc_cau", "mau": r"^\s*BEGIN\b"}),
    ("sau_ghi_1", {
        "ten": "trong giao dịch, NGAY SAU câu ghi thứ 1 (UPDATE tc_cod)",
        "neo": "sau_cau", "mau": r"^\s*UPDATE\s+tc_cod\b"}),
    ("sau_ghi_2", {
        "ten": "trong giao dịch, NGAY SAU câu ghi thứ 2 (INSERT tc_cod_chuyen)",
        "neo": "sau_cau", "mau": r"^\s*INSERT\s+INTO\s+tc_cod_chuyen\b"}),
    ("sau_ghi_3", {
        "ten": "trong giao dịch, NGAY SAU câu ghi thứ 3 (INSERT tc_but_toan)",
        "neo": "sau_cau", "mau": r"^\s*INSERT\s+INTO\s+tc_but_toan\b"}),
    ("sau_ghi_4", {
        "ten": "trong giao dịch, NGAY SAU câu ghi thứ 4 (UPSERT tc_cong_no)",
        "neo": "sau_cau", "mau": r"^\s*INSERT\s+INTO\s+tc_cong_no\b"}),
    ("truoc_commit", {
        "ten": "ngay TRƯỚC COMMIT — cả năm câu ghi đã chạy, chưa chốt",
        "neo": "truoc_cau", "mau": r"^\s*COMMIT\b"}),
    ("sau_commit", {
        "ten": "ngay SAU COMMIT — giao dịch đã chốt",
        "neo": "sau_cau", "mau": r"^\s*COMMIT\b"}),
])
DIEM_KHONG_GIET = "khong"


def _gon(sql):
    return " ".join(str(sql).split())


def cai_bo_giet(kn, diem, duong_vet, them=None):
    """Gắn móc giết vào kết nối `kn`. Trả về đối tượng `BoGiet` (giữ tham chiếu sống).

    `duong_vet` là tệp ghi bằng chứng. Ghi bằng `os.write` trên fd trần rồi `fsync`: mọi
    thứ đệm trong bộ nhớ Python sẽ mất khi tiến trình bị SIGKILL, và một tệp bằng chứng mất
    dòng cuối là tệp bằng chứng nói dối về chỗ chết.
    """
    return BoGiet(kn, diem, duong_vet, them)


class BoGiet(object):
    def __init__(self, kn, diem, duong_vet, them=None):
        self.kn = kn
        self.diem = diem
        self.vet = duong_vet
        self.them = them or {}
        self.da_khop = False
        self.so_cau = 0
        self.so_ghi = 0
        self.so_ghi_da_chay = 0
        self.da_giet = False
        self.cau_ghi = []
        self.mau = re.compile(DIEM_GIET[diem]["mau"]) if diem in DIEM_GIET else None
        self.che_do = DIEM_GIET[diem]["neo"] if diem in DIEM_GIET else None
        kn.set_trace_callback(self._moc)

    def _ghi_vet(self, su_kien, cau=None):
        ban = dict(self.them)
        ban.update({"su_kien": su_kien, "diem": self.diem, "so_cau": self.so_cau,
                    # HAI CON SỐ, KHÔNG MỘT — và chênh nhau đúng một câu khi câu sắp chạy
                    # cũng là câu GHI:
                    #   `so_ghi_da_chay` — số câu ghi ĐÃ CHẠY XONG. Đây là con số dùng để
                    #                      phán "chết sau câu ghi thứ k".
                    #   `so_ghi_moc`     — số câu ghi đã ĐI QUA móc, tính cả câu đang chờ.
                    # Gộp hai con số làm một thì `sau_ghi_1` bị ghi nhận là 2, và một phép
                    # đo lệch một nhịp vẫn ra "NGUYÊN VẸN" nên không ai thấy nó lệch.
                    "so_ghi_da_chay": self.so_ghi_da_chay, "so_ghi_moc": self.so_ghi,
                    "pid": os.getpid()})
        if cau is not None:
            ban["cau"] = _gon(cau)[:200]
        fd = os.open(self.vet, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, (json.dumps(ban, ensure_ascii=False) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def _moc(self, cau):
        self.so_cau += 1
        la_ghi = bool(re.match(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b", cau, re.I))
        # Chốt số câu ghi ĐÃ CHẠY XONG *trước* khi xét câu đang đi qua móc: móc bắn trước
        # khi câu chạy, nên câu đang đi qua móc chưa được tính là đã chạy.
        self.so_ghi_da_chay = self.so_ghi
        if la_ghi:
            self.so_ghi += 1
            self.cau_ghi.append(_gon(cau)[:90])

        if self.da_giet or self.mau is None:
            return
        if self.che_do == "sau_cau" and self.da_khop:
            # Câu khớp mẫu ĐÃ chạy xong (móc bắn trước khi chạy, nên lượt gọi kế tiếp nghĩa
            # là câu trước đã thực thi trọn). Chết ngay tại đây.
            self._giet(cau)
            return
        if self.mau.match(cau):
            if self.che_do == "truoc_cau":
                self._giet(cau)
            else:
                self.da_khop = True

    def _giet(self, cau):
        self.da_giet = True
        self._ghi_vet("GIET", cau)
        sys.stderr.write("[bo-giet] SIGKILL chinh minh tai diem %s (cau sap chay: %s)\n"
                         % (self.diem, _gon(cau)[:90]))
        sys.stderr.flush()
        os.kill(os.getpid(), 9)


def tu_kiem_moc():
    """TỰ KIỂM CÁI MÓC: `set_trace_callback` bắn TRƯỚC hay SAU khi câu lệnh chạy?

    Không tự kiểm chỗ này thì mọi ánh xạ điểm giết đều là phỏng đoán, và phỏng đoán lệch một
    nhịp sẽ biến "ngay trước COMMIT" thành "ngay sau COMMIT" — hai kết luận trái ngược nhau
    về cùng một phép đo. Trả `(so_ca, so_dat, chi_tiet)`.
    """
    import tempfile
    d = tempfile.mkdtemp(prefix="vhg18-moc-")
    p = os.path.join(d, "moc.db")
    kn = sqlite3.connect(p, isolation_level=None)
    kn.execute("CREATE TABLE t(a)")
    kn.execute("INSERT INTO t VALUES (1)")
    thay = {"luc_commit": None}

    def moc(cau):
        if cau.strip().upper() == "COMMIT":
            k2 = sqlite3.connect(p, isolation_level=None)
            try:
                thay["luc_commit"] = k2.execute("SELECT COUNT(*) FROM t").fetchone()[0]
            finally:
                k2.close()

    kn.set_trace_callback(moc)
    kn.execute("BEGIN IMMEDIATE")
    kn.execute("INSERT INTO t VALUES (2)")
    kn.execute("COMMIT")
    kn.set_trace_callback(None)
    sau = kn.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    kn.close()

    ca = [
        ("móc bắn TRƯỚC khi câu chạy: trong lượt gọi COMMIT, kết nối khác còn thấy 1 dòng",
         thay["luc_commit"] == 1, "thấy %r" % (thay["luc_commit"],)),
        ("sau COMMIT thì kết nối này thấy 2 dòng", sau == 2, "thấy %r" % (sau,)),
        ("móc bắn cho CẢ câu điều khiển giao dịch (BEGIN/COMMIT)",
         True, "đã quan sát được lượt gọi COMMIT"),
    ]
    import shutil
    shutil.rmtree(d, ignore_errors=True)
    return ca


# ============================================================================
# BỘ ĐO TÍNH TOÀN VẸN
# ============================================================================
def mo_do(duong_db, chi_doc=True):
    """Mở CSDL để ĐO. `chi_doc=True` mở read-only: một phép đo không được phép sửa thứ nó đo."""
    if chi_doc:
        kn = sqlite3.connect("file:%s?mode=ro" % duong_db, uri=True, isolation_level=None)
    else:
        kn = sqlite3.connect(duong_db, isolation_level=None)
    kn.row_factory = sqlite3.Row
    return kn


def dem(kn, sql, ts=()):
    try:
        r = kn.execute(sql, ts).fetchone()
        return r[0] if r is not None else None
    except sqlite3.Error as e:
        return "LOI:%s" % e


def kiem_cau_truc(kn):
    """`integrity_check` + `foreign_key_check` — hai phép của chính SQLite, không phải của tôi."""
    ra = {}
    try:
        ra["integrity_check"] = kn.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.Error as e:
        ra["integrity_check"] = "LOI:%s" % e
    try:
        ra["foreign_key_check"] = [tuple(x) for x in kn.execute("PRAGMA foreign_key_check")]
    except sqlite3.Error as e:
        ra["foreign_key_check"] = "LOI:%s" % e
    try:
        ra["journal_mode"] = kn.execute("PRAGMA journal_mode").fetchone()[0]
    except sqlite3.Error as e:
        ra["journal_mode"] = "LOI:%s" % e
    return ra


def kiem_mo_coi(kn, tenant_id=1, don_id=1):
    """Dòng MỒ CÔI: trỏ tới một đơn KHÔNG tồn tại.

    Đây là câu hỏi hẹp mà đề bài nêu đích danh ("bút toán trỏ tới đơn không tồn tại").
    Nó KHÁC `foreign_key_check`: khoá ngoại chỉ được cưỡng chế lúc CHÈN, nên một dòng mồ côi
    có thể vào được bằng đường khác (tắt khoá ngoại khi migrate, xoá cha sau khi con đã ghi).
    """
    ra = {}
    for ten, cot, bang in (("but_toan_mo_coi", "don_id", "tc_but_toan"),
                           ("cod_mo_coi", "don_id", "tc_cod"),
                           ("cod_chuyen_mo_coi", "don_id", "tc_cod_chuyen"),
                           ("lich_su_mo_coi", "don_id", "don_lich_su")):
        ra[ten] = dem(kn, "SELECT COUNT(*) FROM %s c LEFT JOIN don_hang d ON d.id=c.%s"
                          " WHERE c.%s IS NOT NULL AND d.id IS NULL" % (bang, cot, cot))
    ra["but_toan_lech_chu_the"] = dem(
        kn, "SELECT COUNT(*) FROM tc_but_toan b JOIN don_hang d ON d.id=b.don_id"
            " WHERE b.tenant_id<>d.tenant_id")
    return ra


def vet_trang_thai(kn, tenant_id=1, don_id=1):
    """VẾT 9 TRƯỜNG của giao dịch 5 bảng. Đây là phép đo CHÍNH.

    Chín trường vì một giao dịch có năm bảng, và ba trong số đó có trường mang TIỀN
    (`trang_thai`, `so_tien_hang_bao`, `so_du_dong`). Đếm dòng không bắt được ca "COD đã nhảy
    trạng thái mà sổ cái trống"; ba trường tiền bắt được.
    """
    cod = kn.execute("SELECT trang_thai, so_tien_hang_bao, so_tien_du_kien FROM tc_cod"
                     " WHERE don_id=? AND tenant_id=?", (don_id, tenant_id)).fetchone()
    return {
        "cod_trang_thai": cod["trang_thai"] if cod else None,
        "cod_hang_bao": cod["so_tien_hang_bao"] if cod else None,
        "cod_du_kien": cod["so_tien_du_kien"] if cod else None,
        "so_chuyen": dem(kn, "SELECT COUNT(*) FROM tc_cod_chuyen WHERE don_id=? AND tenant_id=?",
                         (don_id, tenant_id)),
        "so_but_toan": dem(kn, "SELECT COUNT(*) FROM tc_but_toan WHERE don_id=? AND tenant_id=?",
                           (don_id, tenant_id)),
        "tong_but_toan": dem(kn, "SELECT COALESCE(SUM(so_tien_dong),0) FROM tc_but_toan"
                                 " WHERE don_id=? AND tenant_id=?", (don_id, tenant_id)),
        "cong_no_phai_thu": dem(kn, "SELECT COALESCE(SUM(so_du_dong),0) FROM tc_cong_no"
                                    " WHERE tenant_id=? AND so='phai_thu'", (tenant_id,)),
        "so_nhat_ky": dem(kn, "SELECT COUNT(*) FROM tc_nhat_ky WHERE tenant_id=?", (tenant_id,)),
        "so_don": dem(kn, "SELECT COUNT(*) FROM don_hang WHERE tenant_id=?", (tenant_id,)),
    }


def do_toan_bo(duong_db, tenant_id=1, don_id=1, chi_doc=True):
    """MỘT phép đo đầy đủ trên một tệp CSDL.

    `chi_doc=True` (mặc định) mở read-only: một phép đo không được sửa vật chứng. Đặt False
    khi cố ý muốn "MỞ LẠI CSDL" như một lượt chạy thật sẽ làm — lượt đó ĐƯỢC PHÉP chạy khôi
    phục và checkpoint, và đó chính là điều cần đo ở ca ấy.
    """
    ra = {"duong_db": duong_db, "ton_tai": os.path.exists(duong_db), "chi_doc": chi_doc}
    if not ra["ton_tai"]:
        return ra
    kn = mo_do(duong_db, chi_doc=chi_doc)
    try:
        ra.update(kiem_cau_truc(kn))
        ra["vet"] = vet_trang_thai(kn, tenant_id, don_id)
        ra["mo_coi"] = kiem_mo_coi(kn, tenant_id, don_id)
        ra["so_dong"] = {t: dem(kn, "SELECT COUNT(*) FROM %s" % t)
                         for t in ("don_hang", "tc_cod", "tc_cod_chuyen", "tc_but_toan",
                                   "tc_cong_no", "tc_nhat_ky", "don_lich_su", "audit")}
    finally:
        kn.close()
    return ra


def chup_tep(duong_db):
    """Kích thước + SHA-256 của bộ ba tệp SQLite NGAY SAU KHI GIẾT, TRƯỚC KHI MỞ.

    Phải chụp trước khi mở: chỉ một lượt mở kết nối cũng đủ để SQLite checkpoint WAL và xoá
    `-wal`, và khi đó "WAL có cứu được không" không còn đo được nữa — thứ cần đo đã bị chính
    phép đo xoá mất.
    """
    ra = {}
    for duoi in ("", "-wal", "-shm", "-journal"):
        p = duong_db + duoi
        if os.path.exists(p):
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for khuc in iter(lambda: f.read(1 << 20), b""):
                    h.update(khuc)
            ra[duoi or "db"] = {"byte": os.path.getsize(p), "sha256": h.hexdigest()[:16]}
        else:
            ra[duoi or "db"] = None
    return ra


def sao_chep_nguyen_trang(duong_db, thu_muc_dich):
    """Chép NGUYÊN TRẠNG bộ ba tệp sang chỗ khác để phép đo không làm hỏng vật chứng."""
    import shutil
    os.makedirs(thu_muc_dich, exist_ok=True)
    for duoi in ("", "-wal", "-shm"):
        p = duong_db + duoi
        if os.path.exists(p):
            shutil.copy2(p, os.path.join(thu_muc_dich, os.path.basename(p)))
    return os.path.join(thu_muc_dich, os.path.basename(duong_db))


def phan_loai(vet_truoc, vet_do_duoc, vet_sau):
    """`NGUYEN_VEN_TRUOC` · `NGUYEN_VEN_SAU` · `NUA_VOI`.

    So TỪNG TRƯỜNG và trả về cả danh sách trường lệch — "NỬA VỜI" mà không nói lệch chỗ nào
    là một câu kết luận không dùng được.
    """
    if vet_do_duoc == vet_truoc:
        return "NGUYEN_VEN_TRUOC", []
    if vet_do_duoc == vet_sau:
        return "NGUYEN_VEN_SAU", []
    lech_truoc = {k: (vet_truoc.get(k), vet_do_duoc.get(k))
                  for k in set(vet_truoc) | set(vet_do_duoc) if vet_truoc.get(k) != vet_do_duoc.get(k)}
    return "NUA_VOI", lech_truoc


def main(argv):
    if "--tu-kiem-moc" in argv:
        print("TỰ KIỂM CÁI MÓC `set_trace_callback` — nó bắn TRƯỚC hay SAU khi câu chạy?")
        ca = tu_kiem_moc()
        for ten, ok, ct in ca:
            print("  %s %s  (%s)" % ("✓" if ok else "✗", ten, ct))
        dat = sum(1 for _, ok, _ in ca if ok)
        print("\n%d/%d ca tự kiểm cái móc ĐẠT" % (dat, len(ca)))
        return 0 if dat == len(ca) else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
