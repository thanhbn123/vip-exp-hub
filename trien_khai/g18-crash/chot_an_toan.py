#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CHỐT AN TOÀN của làn G18/AG-06 (giết tiến trình giữa giao dịch).

====== VÌ SAO TÁCH RIÊNG MỘT TỆP ======
Lượt đo này **GIẾT TIẾN TRÌNH THẬT** (`os.kill(pid, SIGKILL)`) và **DỰNG CỤM PostgreSQL
RIÊNG**. Hai việc đó, làm nhầm đích, không báo lỗi — nó chỉ lặng lẽ phá dữ liệu của người
khác. Nên chốt chặn phải là một tệp riêng, chạy TRƯỚC, và **TỪ CHỐI CHẠY** khi thiếu chốt.

`--tu-kiem` chạy bộ dò trên **các cấu hình TỔNG HỢP** (1 cấu hình đủ chốt + 10 cấu hình
hỏng). Mỗi cấu hình hỏng phải bị bắt bởi **ĐÚNG chốt** mang tên nó — bắt bởi chốt khác là
HỎNG, vì như thế chốt kia đang che một lỗi nó không được thiết kế để bắt (§12.1 luật 5).

====== BẢY CHỐT ======
| Mã | Chốt | Bắt cái gì |
|---|---|---|
| C1 | Nền CSDL phải là thư mục TẠM, ngoài cây dự án | ghi vào `app/du-lieu/hub.db` thật |
| C2 | Cổng PostgreSQL ≠ 5432 | đụng cụm hệ thống giữ CSDL dự án khác |
| C3 | Cụm PG thử KHÔNG mở TCP (`listen_addresses=''`) | mở cửa mạng cho một cụm dùng một lần |
| C4 | Nguồn của làn này KHÔNG chứa `pkill`/`killall` | dọn tiến trình theo TÊN, giết cả làn khác |
| C5 | Không tiến trình con nào chạy mà không có PID ghi lại | bỏ lại tiến trình mồ côi |
| C6 | `CHO_PHEP_LIVE`/`JT_CHO_PHEP_SANDBOX` vẫn ĐÓNG | gọi API hãng khi chưa được cấp phép |
| C7 | Mọi tệp CSDL bị đụng đều nằm dưới nền tạm của lượt này | đo nhầm CSDL của làn khác |

====== CHỈ ĐỌC ======
`chot_an_toan.kiem()` chỉ ĐỌC biến môi trường, tên tệp và thuộc tính tiến trình. Nó không
tạo, không xoá, không dừng gì. Việc dừng cụm do `do_giet.py` làm, bằng `pg_ctl stop` và
theo ĐÚNG PID.
"""
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONG_CAM = 5432
TEN_CHOT = {
    "C1": "nền CSDL phải là thư mục TẠM ngoài cây dự án",
    "C2": "cổng PostgreSQL phải KHÁC 5432",
    "C3": "cụm PostgreSQL thử không được mở TCP",
    "C4": "nguồn của làn này không được chứa pkill/killall",
    "C5": "mọi tiến trình con phải có PID ghi lại để dọn theo PID",
    "C6": "cổng gọi hãng phải vẫn ĐÓNG (CHO_PHEP_LIVE / sandbox)",
    "C7": "mọi tệp CSDL bị đụng phải nằm dưới nền tạm của lượt này",
}

THU_MUC_CSDL_THAT = os.path.join(GOC, "app", "du-lieu")


def _la_trong(cay, con):
    """`con` có nằm trong `cay` không — so bằng ĐƯỜNG DẪN THẬT, không so chuỗi."""
    try:
        return os.path.commonpath([os.path.realpath(cay), os.path.realpath(con)]) == \
            os.path.realpath(cay)
    except ValueError:
        return False


# Tên lệnh dọn theo TÊN. Khai bằng hai mảnh ghép lại: nếu viết liền một chuỗi ở đây thì
# chính dòng này là một chuỗi chứa "pkill", và bộ dò dưới kia — vốn chỉ soi chuỗi ĐƯỢC ĐƯA
# CHO lệnh chạy tiến trình — vẫn không bắt nó, nhưng người đọc sau sẽ phải tự hỏi vì sao.
_TEN_DON = ("pk" + "ill", "kill" + "all")
_HAM_CHAY = ("system", "popen", "run", "call", "check_call", "check_output", "Popen",
             "getoutput", "getstatusoutput", "spawnv", "spawnl", "execv", "execvp", "execvp")


def _gop_chuoi(nut):
    """Ghép các hằng chuỗi nối bằng `+` thành MỘT chuỗi. None nếu không phải hằng."""
    import ast
    if isinstance(nut, ast.Constant) and isinstance(nut.value, str):
        return nut.value
    if isinstance(nut, ast.BinOp) and isinstance(nut.op, ast.Add):
        a, b = _gop_chuoi(nut.left), _gop_chuoi(nut.right)
        if a is not None and b is not None:
            return a + b
    return None


def _chuoi_trong_nut(nut):
    """Mọi chuỗi hằng nằm trong một nhánh AST (kể cả list/tuple/dict lồng nhau).

    Có GHÉP chuỗi nối bằng `+`: `subprocess.run(["pk" + "ill"])` là cùng một lệnh, và một
    bộ dò chỉ nhìn từng mảnh rời sẽ bỏ sót nó. Ghép rồi mới soi thì hai cách viết ra một
    kết quả.
    """
    import ast
    ra = []
    for con in ast.walk(nut):
        if isinstance(con, ast.Constant) and isinstance(con.value, str):
            ra.append(con.value)
            continue
        gop = _gop_chuoi(con)
        if gop is not None:
            ra.append(gop)
    return ra


def _lenh_don_theo_ten(tep):
    """Trả danh sách lý do vi phạm chốt C4 cho MỘT tệp. Rỗng = sạch.

    `.py`  → AST: chỉ soi chuỗi làm THAM SỐ của lệnh chạy tiến trình.
    `.sh`  → soi TỪNG DÒNG, bỏ dòng bắt đầu bằng `#`.
    Tệp khác → bỏ qua (không phải nơi chạy lệnh).
    """
    import ast
    if tep.endswith(".py"):
        try:
            with open(tep, "r", encoding="utf-8", errors="replace") as f:
                cay = ast.parse(f.read(), filename=tep)
        except (OSError, SyntaxError) as e:
            return ["không phân tích được %s: %s" % (os.path.basename(tep), e)]
        ra = []
        for nut in ast.walk(cay):
            if not isinstance(nut, ast.Call):
                continue
            ten_ham = ""
            if isinstance(nut.func, ast.Attribute):
                ten_ham = nut.func.attr
            elif isinstance(nut.func, ast.Name):
                ten_ham = nut.func.id
            if ten_ham not in _HAM_CHAY:
                continue
            for chuoi in _chuoi_trong_nut(nut):
                for ten in _TEN_DON:
                    if re.search(r"(^|[\s/;&|])" + ten + r"(\s|$)", chuoi):
                        ra.append("%s:%d đưa `%s` cho `%s` — dọn theo TÊN giết cả làn khác"
                                  % (os.path.basename(tep), nut.lineno, ten, ten_ham))
        return ra
    if tep.endswith(".sh"):
        ra = []
        try:
            with open(tep, "r", encoding="utf-8", errors="replace") as f:
                for so, dong in enumerate(f, 1):
                    if dong.lstrip().startswith("#"):
                        continue
                    for ten in _TEN_DON:
                        if re.search(r"(^|[\s;|&(])" + ten + r"(\s|$)", dong):
                            ra.append("%s:%d có lệnh dọn theo TÊN: %s"
                                      % (os.path.basename(tep), so, dong.strip()[:70]))
        except OSError as e:
            ra.append("không đọc được %s: %s" % (os.path.basename(tep), e))
        return ra
    return []


def kiem(cau_hinh_do):
    """Trả danh sách `(ma_chot, ly_do)`. RỖNG = đủ chốt để chạy.

    `cau_hinh_do` là dict:
      `nen`        — thư mục tạm của lượt đo (mọi CSDL phải nằm dưới nó)
      `cong_pg`    — cổng cụm PostgreSQL thử (None nếu lượt này không chạm PG)
      `pg_tcp`     — True nếu cụm thử có mở TCP
      `pids`       — danh sách PID tiến trình con đang chạy
      `pid_ghi`    — danh sách PID đã ghi ra tệp để dọn
      `csdl_dung`  — danh sách đường dẫn tệp CSDL sẽ bị đụng
      `nguon`      — danh sách tệp mã của làn này (để dò pkill/killall)
    """
    loi = []
    nen = cau_hinh_do.get("nen") or ""

    # C1 — nền phải là thư mục TẠM, ngoài cây dự án.
    if not nen:
        loi.append(("C1", "chưa khai nền tạm"))
    else:
        if _la_trong(GOC, nen):
            loi.append(("C1", "nền %r nằm TRONG cây dự án %r" % (nen, GOC)))
        if not os.path.isdir(nen):
            loi.append(("C1", "nền %r không tồn tại" % nen))
        if os.path.realpath(nen) == os.path.realpath(THU_MUC_CSDL_THAT):
            loi.append(("C1", "nền TRÙNG thư mục dữ liệu thật %r" % THU_MUC_CSDL_THAT))

    # C2 — cổng PG.
    cong = cau_hinh_do.get("cong_pg")
    if cong is not None and int(cong) == CONG_CAM:
        loi.append(("C2", "cổng %d là cụm hệ thống đang giữ CSDL dự án khác" % CONG_CAM))

    # C3 — cụm thử không mở TCP.
    if cau_hinh_do.get("pg_tcp"):
        loi.append(("C3", "cụm PostgreSQL thử đang MỞ TCP"))

    # C4 — không dọn tiến trình theo tên.
    #
    # Dò bằng AST cho `.py`, không grep: chính TỆP NÀY chứa chữ "pkill" (trong docstring và
    # trong chính mẫu dò), nên một phép grep sẽ tự bắt mình — và cách "sửa" hay gặp là thêm
    # tệp này vào danh sách miễn trừ, tức là khoét một lỗ đúng ở chỗ canh. AST hỏi đúng câu
    # cần hỏi: *chuỗi ấy có được ĐƯA CHO một lệnh chạy tiến trình không*, chứ không phải
    # *chuỗi ấy có xuất hiện ở đâu đó không*.
    for tep in cau_hinh_do.get("nguon") or []:
        for ly_do in _lenh_don_theo_ten(tep):
            loi.append(("C4", ly_do))

    # C5 — tiến trình con phải có PID ghi lại.
    thieu = [p for p in (cau_hinh_do.get("pids") or []) if p not in (cau_hinh_do.get("pid_ghi") or [])]
    if thieu:
        loi.append(("C5", "tiến trình %s chạy mà KHÔNG có PID trong tệp dọn" % thieu))

    # C6 — cổng gọi hãng vẫn đóng.
    app = os.path.join(GOC, "app")
    if app not in sys.path:
        sys.path.insert(0, app)
    try:
        import cau_hinh
        if getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", False):
            loi.append(("C6", "JT_CHO_PHEP_SANDBOX đang BẬT"))
        if getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", False):
            loi.append(("C6", "JT_CHO_PHEP_PRODUCTION đang BẬT"))
    except Exception as e:                                  # noqa: BLE001
        loi.append(("C6", "không nạp được app/cau_hinh.py: %s" % e))

    # C7 — tệp CSDL bị đụng phải nằm dưới nền.
    for d in cau_hinh_do.get("csdl_dung") or []:
        if not nen or not _la_trong(nen, d):
            loi.append(("C7", "CSDL %r nằm NGOÀI nền tạm %r" % (d, nen)))
        if _la_trong(THU_MUC_CSDL_THAT, d):
            loi.append(("C7", "CSDL %r nằm trong thư mục dữ liệu THẬT" % d))

    return loi


def chan(cau_hinh_do):
    """Như `kiem()` nhưng NÉM khi thiếu chốt — dùng ở đầu mọi đường chạy."""
    loi = kiem(cau_hinh_do)
    if loi:
        raise RuntimeError("THIẾU CHỐT AN TOÀN — TỪ CHỐI CHẠY:\n" + "\n".join(
            "  [%s] %s (%s)" % (m, TEN_CHOT.get(m, "?"), r) for m, r in loi))
    return True


# ============================================================================
# TỰ KIỂM BỘ DÒ — dựng cấu hình TỔNG HỢP rồi hỏi lại chính bộ dò
# ============================================================================
def _nen_chuan(con):
    return dict(nen=con.get("nen", "/tmp/vhg18-tu-kiem"), cong_pg=con.get("cong_pg"),
                pg_tcp=con.get("pg_tcp", False), pids=con.get("pids", []),
                pid_ghi=con.get("pid_ghi", []), csdl_dung=con.get("csdl_dung", []),
                nguon=con.get("nguon", []))


def tu_kiem(giu_lai=False):
    """Chạy bộ dò trên cấu hình TỔNG HỢP. Trả `(so_ca, so_dat, danh_sach_hong)`.

    Mỗi cấu hình hỏng phải bị bắt bởi ĐÚNG chốt mang tên nó. "Bắt được nhưng bởi chốt
    khác" tính là HỎNG: nếu chốt C1 bắt được lỗi cổng PG thì lúc đó C2 đang không làm việc,
    và lượt chạy thật sẽ lọt qua khe ấy.
    """
    import tempfile
    nen = tempfile.mkdtemp(prefix="vhg18-tu-kiem-")
    tep_nguon_sach = os.path.join(nen, "nguon_sach.py")
    with open(tep_nguon_sach, "w", encoding="utf-8") as f:
        f.write("# tệp tổng hợp: KHÔNG có pkill/killall\nx = 1\n")
    tep_nguon_ban = os.path.join(nen, "nguon_ban.py")
    with open(tep_nguon_ban, "w", encoding="utf-8") as f:
        # Cấu hình hỏng phải là một lệnh chạy THẬT, không phải một dòng chú thích: chốt C4
        # hỏi "chuỗi ấy có được ĐƯA CHO lệnh chạy tiến trình không", nên một chú thích chứa
        # chữ ấy là cấu hình ĐÚNG (sạch) — và một bộ dò bắt nó là bộ dò đang grep.
        f.write("import subprocess\nsubprocess.run(['" + _TEN_DON[0] + "', '-f', 'server.py'])\n")
    tep_nguon_ban_ghep = os.path.join(nen, "nguon_ban_ghep.py")
    with open(tep_nguon_ban_ghep, "w", encoding="utf-8") as f:
        # Cùng một lệnh, viết bằng hai mảnh ghép. Chốt C4 phải bắt CẢ HAI: một bộ dò bỏ sót
        # cách viết thứ hai là một bộ dò dạy người ta cách lách nó.
        f.write("import subprocess\nsubprocess.run(['pk' + 'ill', '-f', 'server.py'])\n")
    tep_nguon_sach_2 = os.path.join(nen, "nguon_sach_2.py")
    with open(tep_nguon_sach_2, "w", encoding="utf-8") as f:
        # Tệp SẠCH có nhắc tên lệnh ấy trong chú thích và trong chuỗi KHÔNG đưa cho lệnh
        # chạy. Nếu bộ dò bắt tệp này thì nó đang grep, và nó sẽ bắt cả chính tệp chốt.
        f.write("# dọn bằng " + _TEN_DON[0] + " là SAI — xem chot_an_toan.py\n"
                "GHI_CHU = 'khong dung " + _TEN_DON[0] + "'\nx = 1\n")

    csdl_trong_nen = os.path.join(nen, "hub.db")
    csdl_ngoai = "/tmp/vhg18-ngoai-<khong-thuoc-nen>.db"

    ca = []
    ca.append(("đủ chốt", None, _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen],
        "nguon": [tep_nguon_sach], "pids": [111], "pid_ghi": [111]})))
    ca.append(("C1 nền trong cây dự án", "C1", _nen_chuan({
        "nen": os.path.join(GOC, "app", "du-lieu"), "cong_pg": 55432})))
    ca.append(("C1 nền trùng thư mục dữ liệu thật", "C1", _nen_chuan({
        "nen": THU_MUC_CSDL_THAT, "cong_pg": 55432})))
    ca.append(("C1 nền rỗng", "C1", _nen_chuan({"nen": "", "cong_pg": 55432})))
    ca.append(("C2 cổng 5432", "C2", _nen_chuan({
        "nen": nen, "cong_pg": 5432, "csdl_dung": [csdl_trong_nen]})))
    ca.append(("C3 cụm thử mở TCP", "C3", _nen_chuan({
        "nen": nen, "cong_pg": 55432, "pg_tcp": True, "csdl_dung": [csdl_trong_nen]})))
    ca.append(("C4 nguồn có lệnh dọn theo tên", "C4", _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen],
        "nguon": [tep_nguon_ban]})))
    ca.append(("C4 nguồn ghép chuỗi để lách", "C4", _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen],
        "nguon": [tep_nguon_ban_ghep]})))
    ca.append(("C4 tệp SẠCH chỉ nhắc trong chú thích", None, _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen],
        "nguon": [tep_nguon_sach_2]})))
    ca.append(("C5 PID không được ghi lại", "C5", _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen], "pids": [111, 222],
        "pid_ghi": [111]})))
    ca.append(("C7 CSDL ngoài nền", "C7", _nen_chuan({
        "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_ngoai]})))
    ca.append(("C7 CSDL trong thư mục dữ liệu THẬT", "C7", _nen_chuan({
        "nen": nen, "cong_pg": 55432,
        "csdl_dung": [os.path.join(THU_MUC_CSDL_THAT, "hub.db")]})))
    # C6 CHỈ bắt được bằng cách BẬT THẬT cờ rồi hỏi lại NGAY — không thể xếp vào danh sách
    # để hỏi sau, vì lúc đó cờ đã được trả về nguyên trạng và phép đo sẽ ra "sạch" một cách
    # giả tạo. Nên hai ca C6 được ĐO TẠI CHỖ và ghi kết quả đã đo vào danh sách.
    # Trả cờ về nguyên trạng trong `finally`: một lượt tự kiểm để lại `CHO_PHEP_LIVE=True`
    # sau lưng còn nguy hơn không tự kiểm, vì nó biến chốt C6 thành chốt đã bị tắt lặng lẽ.
    do_ngay = []
    try:
        # `kiem()` tự đưa `app/` vào `sys.path` khi nó chạy; ở đây phải làm TRƯỚC, vì phép
        # đo C6 cần chạm chính mô-đun `cau_hinh` chứ không chỉ đọc cờ của nó.
        _app = os.path.join(GOC, "app")
        if _app not in sys.path:
            sys.path.insert(0, _app)
        import cau_hinh as _ch
        _cu = {"JT_CHO_PHEP_SANDBOX": _ch.JT_CHO_PHEP_SANDBOX,
               "JT_CHO_PHEP_PRODUCTION": _ch.JT_CHO_PHEP_PRODUCTION}
        try:
            for ten, khoa in (("C6 cổng hãng sandbox đang MỞ", "JT_CHO_PHEP_SANDBOX"),
                              ("C6 cổng hãng production đang MỞ", "JT_CHO_PHEP_PRODUCTION")):
                setattr(_ch, khoa, True)
                ma = sorted({m for m, _ in kiem(_nen_chuan({
                    "nen": nen, "cong_pg": 55432, "csdl_dung": [csdl_trong_nen]}))})
                do_ngay.append((ten, "C6", ma))
                setattr(_ch, khoa, _cu[khoa])
        finally:
            for k, v in _cu.items():
                setattr(_ch, k, v)
    except Exception as e:                                  # noqa: BLE001
        print("  ! không tự kiểm được chốt C6: %s" % e)

    dat = 0
    hong = []
    for ten, mong_doi, cauhinh in ca + do_ngay:
        # `do_ngay` mang KẾT QUẢ ĐÃ ĐO (danh sách mã chốt); `ca` mang CẤU HÌNH chưa đo.
        ma = cauhinh if isinstance(cauhinh, list) else sorted({m for m, _ in kiem(cauhinh)})
        if mong_doi is None:
            ok = (ma == [])
        else:
            ok = (ma == [mong_doi])
        dat += 1 if ok else 0
        if not ok:
            hong.append((ten, mong_doi, ma))
        print("  %s %-42s mong đợi=%-5s thấy=%-14s %s"
              % ("✓" if ok else "✗", ten, mong_doi or "sạch", ",".join(ma) or "sạch",
                 "" if ok else "← " + ("báo động giả" if mong_doi is None
                                       else "bắt bởi %s" % (ma or "KHÔNG AI"))))
    tong = len(ca) + len(do_ngay)
    if not giu_lai:
        import shutil
        shutil.rmtree(nen, ignore_errors=True)
    return tong, dat, hong


def main(argv):
    if "--tu-kiem" in argv:
        print("TỰ KIỂM CHỐT AN TOÀN G18/AG-06 — bộ dò trên cấu hình TỔNG HỢP")
        tong, dat, hong = tu_kiem(giu_lai="--giu-nen" in argv)
        print("\n%d/%d ca chốt an toàn ĐẠT" % (dat, tong))
        if hong:
            print("HỎNG: %s" % (hong,))
            return 1
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
