# Chốt chặn BIÊN DRIVER: chỉ csdl.py được `import sqlite3`.
#
# Vì sao cần bộ thử chứ không phải một dòng dặn trong tài liệu: ngày 15/10/2026 đã gom
# 10 chỗ dùng driver ở 6 tệp về csdl.py. Lời dặn "đừng nạp sqlite3 nữa" thì tệp thứ 7
# viết tháng sau sẽ không ai đọc, và nó KHÔNG báo lỗi gì — mã chạy đúng y như cũ, chỉ là
# nợ kiến trúc mọc lại. CLAUDE.md §12.2: cấu trúc canh giữ, không canh bằng lời dặn.
#
# Dò bằng AST, KHÔNG bằng grep: grep đọc cả chú thích và chuỗi, nên nó sẽ báo nhầm ở
# app/server.py (chỗ đó CỐ Ý trích nguyên văn `"<sqlite3.Row object at 0x...>"` — thứ
# Python in ra khi quên dict(), người đi tìm lỗi grep đúng chuỗi ấy). Đây đúng dạng ca 6
# của §12.1: công cụ dò có phạm vi thì chỉ được nói trong phạm vi nó thật sự hiểu.
import ast
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Danh sách CHO PHÉP, không phải danh sách cấm — §18.2 chốt 4: quên một dòng ở đây thì
# bộ thử HỎNG (an toàn), chứ không phải cho qua im lặng.
DUOC_NAP = {"csdl.py"}
loi = []


def _nap_sqlite3(duong_dan):
    """Trả danh sách dòng có lệnh nạp sqlite3 THẬT (theo AST, bỏ qua chú thích/chuỗi)."""
    try:
        cay = ast.parse(open(duong_dan, encoding="utf-8").read())
    except SyntaxError as e:
        return [f"không phân tích được: {e}"]
    ra = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "sqlite3" or a.name.startswith("sqlite3."):
                    ra.append(n.lineno)
        elif isinstance(n, ast.ImportFrom) and (n.module or "").startswith("sqlite3"):
            ra.append(n.lineno)
    return ra


def ca_a1_chi_csdl_duoc_nap():
    """Không tệp nào trong app/ (trừ danh sách cho phép) được nạp sqlite3."""
    pham = sorted(f for f in os.listdir(GOC) if f.endswith(".py"))
    assert len(pham) >= 20, f"chỉ thấy {len(pham)} tệp .py trong app/ — đường dẫn sai?"
    xau = []
    for f in pham:
        if f in DUOC_NAP:
            continue
        d = _nap_sqlite3(os.path.join(GOC, f))
        if d:
            xau.append(f"{f} dòng {d}")
    assert not xau, "tệp nạp trực tiếp sqlite3 (phải dùng csdl.Row/LoiToanVen/ket_noi): " + "; ".join(xau)
    print(f"  a1: {len(pham)} tệp app/*.py — chỉ {sorted(DUOC_NAP)} nạp driver")


def ca_a2_csdl_that_su_co_nap():
    """Mặt sau của a1: csdl.py PHẢI còn nạp, nếu không a1 đạt vì lý do sai."""
    d = _nap_sqlite3(os.path.join(GOC, "csdl.py"))
    assert d, "csdl.py không nạp sqlite3 — a1 đang đạt vì cả dự án không còn driver?"
    print(f"  a2: csdl.py nạp driver ở dòng {d}")


def ca_a3_bon_ten_nghiep_vu_ton_tai():
    """Bốn tên thay thế phải dùng được thật, không chỉ có mặt."""
    sys.path.insert(0, GOC)
    import csdl
    import sqlite3 as that
    cap = [("Row", that.Row), ("LoiCSDL", that.Error),
           ("LoiToanVen", that.IntegrityError), ("LoiVanHanh", that.OperationalError)]
    for ten, dung in cap:
        co = getattr(csdl, ten, None)
        assert co is dung, f"csdl.{ten} là {co!r}, phải là {dung!r}"
    assert issubclass(csdl.LoiToanVen, csdl.LoiCSDL), "LoiToanVen phải là con của LoiCSDL"
    assert callable(csdl.ket_noi)
    print("  a3: Row/LoiCSDL/LoiToanVen/LoiVanHanh trỏ đúng kiểu, ket_noi() gọi được")


def ca_a4_tu_kiem_bo_do():
    """TỰ KIỂM: bộ dò có thật sự bắt được vi phạm không, và có bỏ qua chú thích không.

    Không có ca này thì a1 đạt mà chẳng chứng minh được gì — một hàm `_nap_sqlite3`
    luôn trả [] cũng làm a1 xanh (§12.1: thứ dùng để kiểm chứng phải được kiểm trước).
    """
    import tempfile
    mau = [("import sqlite3\n", True, "nạp trần"),
           ("import os, sqlite3\n", True, "nạp chung dòng"),
           ("from sqlite3 import Row\n", True, "from ... import"),
           ("import sqlite3.dbapi2\n", True, "nạp mô-đun con"),
           ("# import sqlite3\n", False, "trong chú thích"),
           ('x = "import sqlite3"\n', False, "trong chuỗi"),
           ('# ra `"<sqlite3.Row object>"` khi quên dict()\n', False, "chú thích trích output"),
           ("import csdl\n", False, "nạp csdl")]
    with tempfile.TemporaryDirectory() as t:
        for noi_dung, phai_bat, nhan in mau:
            p = os.path.join(t, "x.py")
            open(p, "w", encoding="utf-8").write(noi_dung)
            bat = bool(_nap_sqlite3(p))
            assert bat == phai_bat, f"mẫu '{nhan}': bộ dò {'bắt' if bat else 'bỏ qua'}, phải {'bắt' if phai_bat else 'bỏ qua'}"
    print(f"  a4: bộ dò đúng trên {len(mau)}/{len(mau)} mẫu (4 ca nạp thật + 4 ca không phải nạp)")


if __name__ == "__main__":
    print("[bien-driver] PHẠM VI: chỉ app/*.py tầng một. KHÔNG phủ app/thu/ (12 tệp thử")
    print("              CÓ nạp sqlite3 — cố ý: bộ thử cần dựng CSDL rời và bắt lỗi driver)")
    n = 0
    for ten, f in sorted(globals().items()):
        if ten.startswith("ca_"):
            f(); n += 1
    print(f"[bien-driver] {n} ca — ĐẠT")
