#!/usr/bin/env python3
# Phép ĐO CSDL cho diễn tập khôi phục (G11). AG-05 DEVOPS sở hữu file này.
# Dùng:
#   python3 trien_khai/do_csdl.py                      -> in JSON số đo ra stdout
#   python3 trien_khai/do_csdl.py --in-gon <file.json> -> in bảng gọn cho người đọc
#   python3 trien_khai/do_csdl.py --so-sanh <truoc.json> <sau.json>
#
# ====== VÌ SAO FILE NÀY TỒN TẠI RIÊNG ======
# §12.1 luật 4: trường nào là dữ kiện ĐO ĐƯỢC — số file, số dòng, mã thoát, mốc thời gian — thì
# phải lấy từ LỆNH, không điền từ trí nhớ hay cảm giác. Báo cáo G11 phải dán số đo của lượt
# diễn tập; số đó đến từ đây, không từ người viết báo cáo.
#
# PHẠM VI phép đo (nói ra để không ai suy rộng):
#   ĐO: danh sách bảng, SỐ DÒNG từng bảng, `PRAGMA integrity_check`, `PRAGMA foreign_key_check`,
#       phiên bản schema, kích thước file, mã băm SHA-256 của file CSDL.
#   NGOÀI PHẠM VI: tính ĐÚNG của dữ liệu nghiệp vụ. `integrity_check` nói CSDL không hỏng về
#       cấu trúc; nó KHÔNG nói dữ liệu đúng. Một bảng bị ghi trắng vẫn `integrity_check = ok`.
#       Đó chính là lý do số dòng phải so TỪNG BẢNG, không so tổng.
import hashlib
import json
import os
import sqlite3
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC, "app"))
import cau_hinh  # noqa: E402


def do():
    duong = cau_hinh.DUONG_DAN_CSDL
    ra = {"duong_dan": duong, "ton_tai": os.path.exists(duong)}
    if not ra["ton_tai"]:
        return ra
    ra["so_byte"] = os.path.getsize(duong)
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    ra["sha256"] = h.hexdigest()
    kn = sqlite3.connect(duong)
    kn.row_factory = sqlite3.Row
    try:
        # `integrity_check` chạy TRƯỚC khi đếm: đếm trên một CSDL hỏng là đếm ra số vô nghĩa.
        ra["integrity_check"] = kn.execute("PRAGMA integrity_check").fetchone()[0]
        ra["foreign_key_check"] = len(kn.execute("PRAGMA foreign_key_check").fetchall())
        ra["journal_mode"] = kn.execute("PRAGMA journal_mode").fetchone()[0]
        bang = [r["name"] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            " ORDER BY name")]
        dem = {}
        for b in bang:
            # Tên bảng lấy TỪ `sqlite_master`, không từ người dùng, nên nội suy ở đây an toàn;
            # tham số hoá không dùng được cho tên bảng trong SQLite.
            dem[b] = kn.execute('SELECT COUNT(*) FROM "%s"' % b.replace('"', '""')).fetchone()[0]
        ra["so_bang"] = len(bang)
        ra["so_dong"] = dem
        ra["tong_dong"] = sum(dem.values())
        r = kn.execute("SELECT MAX(phien_ban) pb FROM schema_version").fetchone()
        ra["phien_ban_schema"] = r["pb"] if r else None
    finally:
        kn.close()
    return ra


def in_gon(d):
    if not d.get("ton_tai"):
        print(f"    CSDL KHONG TON TAI: {d['duong_dan']}")
        return
    print(f"    duong dan        : {d['duong_dan']}")
    print(f"    so byte          : {d['so_byte']}")
    print(f"    sha256           : {d['sha256'][:16]}...{d['sha256'][-8:]}")
    print(f"    schema           : v{d['phien_ban_schema']}")
    print(f"    integrity_check  : {d['integrity_check']}")
    print(f"    foreign_key_check: {d['foreign_key_check']} vi pham")
    print(f"    journal_mode     : {d['journal_mode']}")
    print(f"    so bang          : {d['so_bang']}")
    print(f"    tong dong        : {d['tong_dong']}")
    co = {k: v for k, v in sorted(d["so_dong"].items()) if v}
    print(f"    bang co du lieu  : {len(co)}/{d['so_bang']}")
    for k, v in co.items():
        print(f"      {k:<28} {v}")


def so_sanh(a, b, cho_phep=None):
    """So TỪNG BẢNG, không so tổng. Tổng khớp mà hai bảng lệch ngược nhau thì tổng vẫn khớp —
    và đó đúng là kiểu mất im lặng mà phép đo này sinh ra để chặn.

    `cho_phep` là {bang: (delta, ly_do)} — lệch ĐÃ KHAI TRƯỚC kèm lý do. Lệch khớp đúng con số
    đã khai thì in ra là "da khai"; lệch KHÁC con số đã khai, hoặc ở bảng chưa khai, thì HỎNG.
    Vì sao phải khai con số chính xác chứ không chỉ khai tên bảng: khai tên bảng là tắt phép đo
    cho cả bảng đó, và từ đó một lượt mất 500 dòng `audit` cũng đi qua im lặng. Khai con số thì
    đúng một delta đã hiểu được đi qua, mọi delta khác vẫn kêu.
    """
    cho_phep = cho_phep or {}
    print("--- SO SANH TRUOC / SAU ---")
    lech = []
    da_khai = []
    if not (a.get("ton_tai") and b.get("ton_tai")):
        print("  mot trong hai ban do khong co CSDL"); return 1
    for ten in ("phien_ban_schema", "integrity_check", "so_bang"):
        if a.get(ten) != b.get(ten):
            lech.append(f"{ten}: truoc={a.get(ten)!r} sau={b.get(ten)!r}")
    moi_bang = set(a["so_dong"]) | set(b["so_dong"])
    for bang in sorted(moi_bang):
        t, s = a["so_dong"].get(bang), b["so_dong"].get(bang)
        if t == s:
            continue
        if bang in cho_phep and t is not None and s is not None:
            delta, ly_do = cho_phep[bang]
            if s - t == delta:
                da_khai.append(f"bang {bang}: truoc={t} sau={s} (delta {delta:+d}) — {ly_do}")
                continue
            lech.append(f"bang {bang}: truoc={t} sau={s} (delta {s - t:+d}) "
                        f"nhung DA KHAI la {delta:+d} — con so KHONG khop")
            continue
        lech.append(f"bang {bang}: truoc={t} sau={s}")
    print(f"  integrity_check : truoc={a['integrity_check']} | sau={b['integrity_check']}")
    print(f"  tong dong       : truoc={a['tong_dong']} | sau={b['tong_dong']}")
    print(f"  so bang         : truoc={a['so_bang']} | sau={b['so_bang']}")
    print(f"  sha256 CSDL     : {'KHOP' if a['sha256'] == b['sha256'] else 'KHAC'}"
          "  (khac la binh thuong: backup/restore khong giu nguyen byte vi WAL)")
    for d in da_khai:
        print(f"  LECH DA KHAI TRUOC: {d}")
    if lech:
        print(f"  KET LUAN: LECH {len(lech)} cho CHUA KHAI:")
        for d in lech:
            print(f"    - {d}")
        return 1
    print(f"  KET LUAN: KHOP tung bang ({len(da_khai)} lech da khai truoc va khop con so).")
    print("  PHAM VI cau ket luan nay: khop ve SO DONG tung bang + integrity_check + so bang +")
    print("  phien ban schema. NGOAI pham vi: tinh DUNG cua NOI DUNG tung dong (mot bang bi ghi")
    print("  trang van integrity_check=ok), va kha nang GIAI MA credentials — do rieng o B11.")
    return 0


if __name__ == "__main__":
    if "--in-gon" in sys.argv:
        with open(sys.argv[sys.argv.index("--in-gon") + 1], encoding="utf-8") as f:
            in_gon(json.load(f))
    elif "--so-sanh" in sys.argv:
        i = sys.argv.index("--so-sanh")
        with open(sys.argv[i + 1], encoding="utf-8") as f:
            a = json.load(f)
        with open(sys.argv[i + 2], encoding="utf-8") as f:
            b = json.load(f)
        # --cho-phep-lech bang=+1:ly do  (lặp được nhiều lần)
        cp = {}
        for j, t in enumerate(sys.argv):
            if t == "--cho-phep-lech" and j + 1 < len(sys.argv):
                tho = sys.argv[j + 1]
                bang, _, con = tho.partition("=")
                so, _, ly = con.partition(":")
                cp[bang] = (int(so), ly or "(khong neu ly do)")
        raise SystemExit(so_sanh(a, b, cp))
    else:
        print(json.dumps(do(), ensure_ascii=False, indent=2))
