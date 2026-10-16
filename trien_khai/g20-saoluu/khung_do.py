#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — KHUNG ĐO cho vòng tròn SAO LƯU → KHÔI PHỤC.

====== VÌ SAO CHỈ ĐẾM SỐ DÒNG LÀ CHƯA ĐỦ ======
`trien_khai/do_csdl.py` (G11) đếm SỐ DÒNG từng bảng và tự khai giới hạn của nó:

    "NGOÀI PHẠM VI: tính ĐÚNG của dữ liệu nghiệp vụ. `integrity_check` nói CSDL không hỏng về
     cấu trúc; nó KHÔNG nói dữ liệu đúng. Một bảng bị ghi trắng vẫn `integrity_check = ok`."

Đúng. Và có một lớp hỏng mà phép đếm dòng KHÔNG BAO GIỜ thấy: **số dòng y nguyên, số tiền sai**.
Trong hệ này tiền là số nguyên VND trong các cột `so_tien_*`/`cod`/`phi_*`; một bản khôi phục
làm rơi mất một chữ số ở cột tiền vẫn cho `COUNT(*)` khớp hoàn hảo. Khung này đo thêm **TỔNG TIỀN
từng cột tiền của từng bảng**, nên lớp hỏng đó trở thành ĐỎ được.

====== DANH SÁCH CỘT TIỀN LÀ KHAI BÁO TƯỜNG MINH, CÓ CHỐT CHỐNG MỤC ======
`COT_TIEN` viết tay, không dò bằng regex — regex `gia` bắt luôn `trang_thai_giao`, regex `tt`
bắt luôn `stt`, và một danh sách rác thì phép đo cũng rác. Đổi lại, danh sách viết tay có thể
MỤC: thêm một cột tiền mới vào DDL mà không ai thêm vào đây thì phép đo im lặng bỏ sót nó.
Nên `kiem_danh_sach()` quét toàn bộ cột và **NÉM** nếu thấy một cột số có tên dạng tiền mà không
nằm trong danh sách. Danh sách mục là lỗi ỒN ÀO, không phải lỗi im lặng.

====== PHẠM VI (nói ra để không ai suy rộng) ======
ĐO: danh sách bảng · SỐ DÒNG từng bảng · TỔNG TIỀN từng cột tiền · `integrity_check` ·
    phiên bản schema · số byte · SHA-256 của tệp.
KHÔNG ĐO: tính đúng của từng DÒNG ngoài các cột tiền (một dòng bị đổi tên khách vẫn khớp số
    dòng và khớp tiền). Bù lại, `chup()` ghi thêm `bam_toan_kho`: SHA-256 trên toàn bộ nội dung
    các bảng — phép này bắt được MỌI thay đổi byte của dữ liệu logic, nhưng KHÔNG bắt được thay
    đổi ở tầng tệp (trang trống, thứ tự, mảnh WAL) — đúng thứ `sha256_tep` đo.
"""
import hashlib
import json
import os
import re
import sqlite3

# --------------------------------------------------------------------------- cột tiền
# Khai báo TƯỜNG MINH. Khoá = tên bảng, giá trị = các cột chứa TIỀN (VND, số nguyên).
COT_TIEN = {
    "don_hang": ("cod", "gia_tri_khai", "phi_van_chuyen"),
    "ds_dong": ("phi_hang_bao",),
    "du_thao_hoa_don": ("tien_goi_dong", "tien_vuot_dong"),
    "goi_dich_vu": ("gia_thang",),
    "goi_phien_ban": ("gia_thang_dong",),
    "tc_but_toan": ("so_tien_dong",),
    "tc_cod": ("so_tien_du_kien", "so_tien_hang_bao", "so_tien_doi_soat", "so_tien_da_tt"),
    "tc_cong_no": ("so_du_dong",),
    "tc_dieu_chinh": ("so_tien_dong",),
    "tc_dot_tt": ("so_tien_hang_bao",),
    "tc_dot_tt_dong": ("so_tien_dong",),
    "tc_phi": ("so_tien_dong",),
}

# Cột TIỀN mà giá trị bằng 0 là ĐÚNG THIẾT KẾ — vẫn nằm trong `COT_TIEN` (vẫn được sao lưu và
# so), nhưng KHÔNG bị tính là "phép so rỗng". Khai ở đây kèm LÝ DO ĐO ĐƯỢC, không khai suông.
TIEN_RONG_CHAP_NHAN = {
    ("du_thao_hoa_don", "tien_vuot_dong"):
        "luôn 0 CÓ CHỦ ĐÍCH: `usage.tinh_phi()` trả cứng 0 cho cột này vì hệ CHẶN khi hết hạn "
        "mức chứ không cho dùng quá rồi thu thêm, và đơn giá phần vượt chưa có ai chốt "
        "(`app/usage.py`, khoá `ly_do_khong_thu_vuot`). Muốn cột này khác 0 thì phải có một "
        "quyết định về GIÁ của anh Thành — không phải việc của bộ đo.",
}

# Cột SỐ nhưng KHÔNG phải tiền — khai ra để chốt `kiem_danh_sach()` không báo động giả.
# Mỗi dòng kèm lý do; "không phải tiền" là một khẳng định, phải nói được vì sao.
KHONG_PHAI_TIEN = {
    ("don_hang", "hang_trang_thai_giao"): "thứ hạng trạng thái giao (1..6), không phải tiền",
    ("don_hang", "khoi_luong_gram"): "khối lượng gam",
    ("ds_dong", "stt"): "số thứ tự dòng",
    ("ds_dot", "duyet_boi"): "id người duyệt",
    ("import_dong", "stt"): "số thứ tự dòng",
    ("reset_tokens", "da_dung"): "cờ 0/1",
    ("schema_version", "phien_ban"): "phiên bản schema",
    ("tenant_memberships", "id"): "khoá chính",
    ("ds_anh_xa_cot", "phien_ban"): "phiên bản ánh xạ cột",
    ("usage_thang", "so_don"): "bộ đếm số đơn trong tháng",
    ("usage_thang", "so_ai"): "bộ đếm lượt gọi AI trong tháng",
    # Hai dòng dưới là BÁO ĐỘNG GIẢ của chính bộ đo, ghi lại để người sau không "sửa" lại:
    #   `han_muc_rieng.gia_tri` là HẠN MỨC (số đơn / số lượt AI được phép), không phải tiền;
    #   `quan_sat_su_kien.tien_trinh` là TIẾN TRÌNH ("progress"), không phải "tiền".
    ("han_muc_rieng", "gia_tri"): "hạn mức (số đơn / lượt AI được phép), không phải tiền",
    ("quan_sat_su_kien", "tien_trinh"): "'tiến trình' (progress) — trùng chữ 'tiền', không phải tiền",
}
# Tên cột bị coi là "dạng tiền" — hẹp có chủ đích, đủ để bắt cột tiền mới thêm vào DDL.
_MAU_TIEN = re.compile(r"^(so_tien|so_du|so_du_dong|gia_thang|gia_tri|phi_|cod$|cuoc|"
                       r"doanh_thu|thanh_tien|tien_)")


def _la_cot_so(kieu):
    return (kieu or "").upper() in ("INTEGER", "REAL", "NUMERIC", "DECIMAL", "BIGINT")


def _cot_trong_bang(kn, bang):
    return [(r[1], r[2]) for r in kn.execute("PRAGMA table_info(%s)" % _trich(bang))]


def _trich(ten):
    """Bọc tên bảng trong nháy kép — tên bảng đến từ `sqlite_master` của chính tệp đang đo."""
    return '"' + str(ten).replace('"', '""') + '"'


def danh_sach_bang(kn):
    return [r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        " ORDER BY name")]


def kiem_danh_sach(kn):
    """NÉM nếu có cột số tên-dạng-tiền chưa được khai. Trả về số cột tiền đã khai."""
    co, thua = set(), []
    for bang in danh_sach_bang(kn):
        for ten, kieu in _cot_trong_bang(kn, bang):
            if not _la_cot_so(kieu):
                continue
            if (bang, ten) in KHONG_PHAI_TIEN:
                continue
            if ten in COT_TIEN.get(bang, ()):
                co.add((bang, ten))
                continue
            if _MAU_TIEN.match(ten):
                thua.append("%s.%s" % (bang, ten))
    if thua:
        raise AssertionError(
            "DANH SÁCH CỘT TIỀN ĐÃ MỤC — thấy cột số dạng tiền chưa khai: %s. "
            "Thêm vào `COT_TIEN`, hoặc khai vào `KHONG_PHAI_TIEN` kèm lý do." % ", ".join(sorted(thua)))
    # Và chiều ngược: khai một cột không tồn tại là phép đo tự bịa.
    thieu = []
    for bang, cols in COT_TIEN.items():
        if bang not in danh_sach_bang(kn):
            thieu.append(bang + " (bảng không có)")
            continue
        that = {t for t, _ in _cot_trong_bang(kn, bang)}
        for c in cols:
            if c not in that:
                thieu.append("%s.%s" % (bang, c))
    if thieu:
        raise AssertionError("Khai cột tiền KHÔNG TỒN TẠI trong CSDL: %s" % ", ".join(sorted(thieu)))
    return len(co)


# --------------------------------------------------------------------------- phép chụp
def _bam_toan_kho(kn):
    """SHA-256 trên TOÀN BỘ nội dung logic: mọi bảng, mọi dòng, theo thứ tự ổn định.

    Vì sao cần thêm phép này khi đã có số dòng + tổng tiền: một dòng `khach_hang` bị đổi tên,
    hay một `payload_tho` BLOB bị lệch một bit, đều KHÔNG làm đổi số dòng lẫn tổng tiền. Không
    có phép này thì "khôi phục đúng dữ liệu" chỉ đúng ở hai trục hẹp.
    """
    h = hashlib.sha256()
    for bang in danh_sach_bang(kn):
        h.update(("\x1e" + bang).encode())
        cols = [t for t, _ in _cot_trong_bang(kn, bang)]
        # `ORDER BY rowid` chỉ có khi bảng KHÔNG phải WITHOUT ROWID; schema này không dùng
        # WITHOUT ROWID, nhưng vẫn phải chịu được trường hợp đó thay vì nổ.
        try:
            rows = kn.execute("SELECT * FROM %s ORDER BY rowid" % _trich(bang)).fetchall()
        except sqlite3.Error:
            rows = kn.execute("SELECT * FROM %s" % _trich(bang)).fetchall()
        h.update(("|".join(cols)).encode())
        for r in rows:
            for v in r:
                if isinstance(v, bytes):
                    h.update(b"\x00b" + v)
                elif v is None:
                    h.update(b"\x00n")
                else:
                    h.update(b"\x00s" + str(v).encode("utf-8", "surrogatepass"))
                h.update(b"\x1f")
            h.update(b"\x1d")
    return h.hexdigest()


def _sha256_tep(duong):
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    return h.hexdigest()


def chup(duong):
    """Chụp TRẠNG THÁI ĐO ĐƯỢC của một tệp CSDL SQLite.

    Không ném khi tệp hỏng: tệp hỏng CHÍNH LÀ thứ cần đo ở các ca hỏng. Lỗi được ghi vào
    `loi` và `integrity_check` để phép so nhìn thấy, thay vì làm cả phép đo chết.

    ====== VÌ SAO PHẢI CHÉP RA VÙNG TẠM TRƯỚC KHI MỞ ======
    Đo được ngày 16/10/2026: bản sao lưu do `migrate.sao_luu()` sinh ra MANG CHẾ ĐỘ `wal`
    (byte 18–19 của phần đầu tệp = 2). Mở một CSDL WAL ở `mode=ro` **thất bại** với
    `unable to open database file` — SQLite cần tạo được tệp `-shm` cạnh nó. Hệ quả nếu ai đó
    lấy chính lỗi này làm kết luận: "bản sao lưu KHÔNG mở được ⇒ hỏng" — trong khi bản sao lưu
    TỐT, chỉ có cách mở là sai.

    Nên phép chụp chép `db` (+ `-wal` nếu có) ra một thư mục tạm rồi mở ở đó. Hai cái lợi:
      * mở được cả CSDL WAL, không phụ thuộc quyền ghi thư mục;
      * KHÔNG tạo `-wal`/`-shm` trong thư mục đang đo — đo mà làm đổi thứ đang đo là hỏng
        phép đo (ca 3 đếm tệp trong `sao-luu/`; một `-shm` lạc vào đó sẽ thành "bản sao lưu ma").
    `-shm` CỐ Ý không chép: nó là bộ nhớ chia sẻ, SQLite dựng lại được; chép nó vào còn nguy
    hiểm hơn (ảnh chụp mâu thuẫn với `-wal`).
    """
    ra = {"duong_dan": duong, "ton_tai": os.path.exists(duong)}
    if not ra["ton_tai"]:
        return ra
    ra["so_byte"] = os.path.getsize(duong)
    ra["sha256_tep"] = _sha256_tep(duong)
    ra["bang"] = {}
    ra["tong_tien_toan_kho"] = 0
    tam = None
    kn = None
    try:
        import shutil
        import tempfile
        tam = tempfile.mkdtemp(prefix="g20-chup-")
        ban = os.path.join(tam, "d.db")
        shutil.copy2(duong, ban)
        for duoi in ("-wal",):
            if os.path.exists(duong + duoi):
                shutil.copy2(duong + duoi, ban + duoi)
        kn = sqlite3.connect(ban)
        kn.execute("PRAGMA query_only=ON")
        ra["integrity_check"] = kn.execute("PRAGMA integrity_check").fetchone()[0]
        try:
            ra["foreign_key_check"] = len(kn.execute("PRAGMA foreign_key_check").fetchall())
        except sqlite3.Error as e:
            ra["foreign_key_check"] = "loi: %s" % e
        try:
            ra["phien_ban"] = kn.execute(
                "SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
        except sqlite3.Error as e:
            ra["phien_ban"] = "loi: %s" % e
        for bang in danh_sach_bang(kn):
            d = {"dong": kn.execute("SELECT COUNT(*) FROM %s" % _trich(bang)).fetchone()[0],
                 "tien": {}}
            cot_that = {t for t, _ in _cot_trong_bang(kn, bang)}
            for c in COT_TIEN.get(bang, ()):
                if c not in cot_that:
                    continue
                v = kn.execute("SELECT COALESCE(SUM(%s),0) FROM %s" % (_trich(c), _trich(bang))
                               ).fetchone()[0]
                d["tien"][c] = int(v or 0)
                ra["tong_tien_toan_kho"] += int(v or 0)
            ra["bang"][bang] = d
        ra["bam_toan_kho"] = _bam_toan_kho(kn)
        ra["so_bang"] = len(ra["bang"])
    except sqlite3.Error as e:
        ra["loi"] = "%s: %s" % (type(e).__name__, e)
    finally:
        if kn is not None:
            try:
                kn.close()
            except sqlite3.Error:
                pass
        if tam:
            import shutil
            shutil.rmtree(tam, ignore_errors=True)
    return ra


def integrity_cua_tep(duong):
    """`PRAGMA integrity_check` trên một tệp bất kỳ, trả về chuỗi hoặc mô tả NGOẠI LỆ.

    Dùng chung đường chép-ra-tạm với `chup()` — cùng lý do (CSDL WAL không mở được `mode=ro`).
    """
    c = chup(duong)
    if c.get("loi"):
        return "NGOAI-LE %s" % c["loi"]
    return c.get("integrity_check")


# --------------------------------------------------------------------------- phép so
# Các trường của phép chụp được so TRỰC TIẾP. `sha256_tep` CỐ Ý nằm ngoài: hai tệp SQLite cùng
# nội dung logic vẫn khác byte (trang trống, mảnh WAL, thứ tự ghi) — so nó sẽ báo lệch giả.
TRUONG_SO = ("integrity_check", "phien_ban", "so_bang", "tong_tien_toan_kho",
             "bam_toan_kho", "so_byte")


def so_sanh(truoc, sau, bo_qua=()):
    """Trả DANH SÁCH lệch giữa hai phép chụp — TỪNG BẢNG, cả SỐ DÒNG lẫn TỔNG TIỀN.

    `bo_qua`: tập tên bảng được phép lệch, khai TRƯỚC khi đo và phải kèm lý do ở chỗ gọi.
    Khai cả bảng là tắt phép đo cho bảng đó; đó là lựa chọn có ý thức, không phải mặc định.
    """
    lech = []
    for t in TRUONG_SO:
        a, b = truoc.get(t), sau.get(t)
        if a != b:
            lech.append("%-12s %r -> %r" % (t, a, b))
    if truoc.get("loi") != sau.get("loi"):
        lech.append("loi          %r -> %r" % (truoc.get("loi"), sau.get("loi")))
    b1, b2 = truoc.get("bang", {}), sau.get("bang", {})
    for bang in sorted(set(b1) | set(b2)):
        if bang in bo_qua:
            continue
        d1, d2 = b1.get(bang), b2.get(bang)
        if d1 is None or d2 is None:
            lech.append("BẢNG %-18s %s -> %s" % (
                bang, "có" if d1 is not None else "MẤT",
                "có" if d2 is not None else "MẤT"))
            continue
        if d1["dong"] != d2["dong"]:
            lech.append("DÒNG %-18s %d -> %d" % (bang, d1["dong"], d2["dong"]))
        for c in sorted(set(d1["tien"]) | set(d2["tien"])):
            v1, v2 = d1["tien"].get(c), d2["tien"].get(c)
            if v1 != v2:
                lech.append("TIỀN %-18s %-18s %s -> %s" % (bang, c, v1, v2))
    return lech


def in_bang(truoc, sau, tieu_de="ĐỐI CHIẾU TỪNG BẢNG"):
    """In bảng người đọc được: mỗi bảng một dòng, SỐ DÒNG và TỔNG TIỀN trước → sau."""
    print("--- %s ---" % tieu_de)
    print("%-20s %-9s %-22s %-24s %s" % ("BẢNG", "DÒNG", "TRƯỚC -> SAU", "TIỀN TRƯỚC -> SAU", "OK"))
    b1, b2 = truoc.get("bang", {}), sau.get("bang", {})
    for bang in sorted(set(b1) | set(b2)):
        d1, d2 = b1.get(bang, {"dong": "-", "tien": {}}), b2.get(bang, {"dong": "-", "tien": {}})
        cot = sorted(set(d1["tien"]) | set(d2["tien"]))
        if cot:
            tens = " · ".join(
                "%s=%s→%s" % (c, d1["tien"].get(c), d2["tien"].get(c)) for c in cot)
            ok = "OK" if all(d1["tien"].get(c) == d2["tien"].get(c) for c in cot) else "LỆCH"
        else:
            tens, ok = "(không có cột tiền)", ""
        if d1["dong"] != d2["dong"]:
            ok = "LỆCH"
        print("%-20s %-9s %-22s %-24s %s" % (
            bang, d1["dong"], "%s -> %s" % (d1["dong"], d2["dong"]), tens, ok))
    print("%-20s %-9s %-22s %-24s %s" % (
        "TỔNG TIỀN TOÀN KHO", "", "",
        "%s -> %s" % (truoc.get("tong_tien_toan_kho"), sau.get("tong_tien_toan_kho")),
        "OK" if truoc.get("tong_tien_toan_kho") == sau.get("tong_tien_toan_kho") else "LỆCH"))
    print("băm toàn kho : %s -> %s" % (str(truoc.get("bam_toan_kho"))[:16],
                                       str(sau.get("bam_toan_kho"))[:16]))
    print("sha256 tệp   : %s -> %s  (KHÁC là bình thường — xem TRUONG_SO)" % (
        str(truoc.get("sha256_tep"))[:16], str(sau.get("sha256_tep"))[:16]))
    print("integrity    : %s -> %s · phiên bản schema %s -> %s" % (
        truoc.get("integrity_check"), sau.get("integrity_check"),
        truoc.get("phien_ban"), sau.get("phien_ban")))


def kiem_khong_rong(c, ten_ca=""):
    """NÉM nếu phép so TIỀN đang RỖNG — tức một cột tiền khai trong `COT_TIEN` mà cả hai vế
    đều bằng 0.

    Vì sao phải có chốt này: `so_sanh()` so hai con số. Hai số 0 thì "khớp" — và một bản khôi
    phục ĐÁNH RƠI cả bảng vẫn cho ra "khớp" nếu bảng đó vốn rỗng ở cả hai vế. Một phép đo rỗng
    báo ĐẠT là đúng kiểu hỏng mà CLAUDE.md §12.1 gọi tên: thứ dùng để kiểm chứng phải được kiểm
    trước khi tin. Ở đây chốt đặt trên BẢN GỐC: cột tiền nào gốc bằng 0 thì phép so nó vô nghĩa.
    """
    rong, chap_nhan = [], []
    for bang, d in (c.get("bang") or {}).items():
        for cot, v in d.get("tien", {}).items():
            if not v:
                if (bang, cot) in TIEN_RONG_CHAP_NHAN:
                    chap_nhan.append("%s.%s" % (bang, cot))
                else:
                    rong.append("%s.%s" % (bang, cot))
    if rong:
        raise AssertionError(
            "%sphép so TIỀN RỖNG ở: %s — cột tiền bằng 0 ở BẢN GỐC thì mọi khẳng định "
            "\"khôi phục khớp tiền\" cho cột đó là rỗng. Gieo thêm dữ liệu hoặc khai bỏ."
            % (("%s: " % ten_ca) if ten_ca else "", ", ".join(sorted(rong))))
    # Trả về danh sách cột tiền RỖNG ĐÃ KHAI, để chỗ gọi IN RA. Một cột tiền bằng 0 mà không
    # nói ra thì người đọc báo cáo tưởng nó đã được kiểm.
    return {"rong_chap_nhan": sorted(chap_nhan),
            "so_cot_tien_da_khai": sum(len(v) for v in COT_TIEN.values())}


def tom_tat_tien(c):
    """{bảng: tổng tiền} — để in gọn và để đối chiếu nhanh giữa hai vế."""
    return {b: sum(d["tien"].values()) for b, d in sorted((c.get("bang") or {}).items())
            if d.get("tien")}


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        print(json.dumps(chup(p), ensure_ascii=False, indent=2))
