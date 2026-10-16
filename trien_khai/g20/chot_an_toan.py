#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 — CHỐT AN TOÀN của harness HỢP ĐỒNG LỚP HTTP (AG-03).

====== VÌ SAO CẦN MỘT CHỐT RIÊNG CHO MỘT HARNESS *ĐIỀU PHỐI* ======
Harness G20 không tự bắn HTTP. Nguy hiểm của nó nằm ở chỗ KHÁC: nó là thứ DUY NHẤT chạy
HẾT năm harness con, nên nó là thứ DUY NHẤT có thể **khuếch đại** một chốt bị gỡ ở một làn
thành năm lượt chạy mất chốt. Một harness điều phối không có chốt riêng thì mọi chốt của
các harness con đều bị vô hiệu hoá từ bên trên: nó chỉ cần đặt `VIP_HUB_BIND=0.0.0.0` một
lần là cả năm lượt cùng mở cổng.

BẢY CHỐT
--------
| Mã | Chốt | Bắt cái gì |
|---|---|---|
| N1 | Nền chạy phải là thư mục TẠM, ngoài `app/du-lieu/` | ghi đè CSDL nghiệp vụ thật |
| N2 | `CHO_PHEP_LIVE is False` trên MỌI adapter + cổng môi trường J&T ĐÓNG | gọi API hãng khi chưa được cấp phép |
| N3 | `VIP_HUB_BIND` trống hoặc loopback | mở cổng ra ngoài (`V-G11-01` CHƯA CẤP) |
| N4 | Cờ "cho phép gọi hãng" KHÔNG bật | một lượt chạy quên không thể tự mở đường gọi hãng |
| N5 | `VHG18_CONG_PG` ≠ 5432 | đụng cụm PostgreSQL hệ thống đang giữ `vip_customs*` |
| N6 | Nguồn của làn G20 KHÔNG chứa `pkill`/`killall` | dọn tiến trình theo TÊN là giết cả làn khác |
| N7 | KHÔNG ai khai `V-G09-01`/`V-13906-05` là đã cấp | harness tự cấp giấy phép cho chính nó |

N6 đọc CHÍNH MÃ CỦA LÀN NÀY. Nó không phải chốt hình thức: G20 spawn năm harness con, mỗi
harness con lại spawn máy chủ; một dòng `pkill -f server.py` ở đây giết máy chủ của mọi làn
đang chạy song song trên cùng máy (`CLAUDE.md` §16.7). Chốt này tự soi được vì nó soi mã,
không soi lời khai.

====== VÌ SAO CÓ `--tu-kiem` ======
Chốt chặn CŨNG là thứ dùng để kiểm chứng, nên nó phải được kiểm. `--tu-kiem` chạy bộ dò trên
**tám cấu hình tổng hợp**: một cấu hình ĐỦ CHỐT (phải ĐI QUA) và bảy cấu hình HỎNG, mỗi cái
phải bị bắt bởi **ĐÚNG chốt đang muốn đo**. Chỉ hỏi "có bị từ chối không" thì một ca hỏng vì
lý do KHÁC vẫn được tính là đạt — bộ dò trông như đang hoạt động trong khi nó không đo thứ nó
tuyên bố (bài học có thật của G16: ba ca "đạt" vì một `TypeError`).

CHẠY
----
    python3 trien_khai/g20/chot_an_toan.py --tu-kiem
    VIP_HUB_DATA=/tmp/... python3 trien_khai/g20/chot_an_toan.py
"""
import ast
import os
import re
import sys
import tempfile
import tokenize

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)

THU_MUC_G20 = os.path.dirname(os.path.abspath(__file__))
LOOPBACK = ("127.0.0.1", "localhost", "::1")
THU_MUC_TAM = ("/tmp", "/var/folders", "/private/var/folders", tempfile.gettempdir())

BIEN_GOI_HANG = ("VIP_G20_CHO_PHEP_GOI_HANG", "VIP_G17_CHO_PHEP_GOI_HANG")
BIEN_GIAY_PHEP = ("VIP_G20_GIAY_PHEP", "VIP_G17_GIAY_PHEP")
GIAY_PHEP_CHAM_HANG = ("V-G09-01", "V-13906-05")
CONG_PG_CAM = "5432"
CONG_PG_MAC_DINH = "55718"

#: Nguồn của làn G20 — N6 soi đúng danh sách này. Thêm tệp mã mới vào làn thì thêm ở đây,
#: nếu không chốt N6 sẽ KHÔNG soi tệp mới (một chốt có danh sách cứng là một chốt có lỗ).
NGUON_PY = ("chot_an_toan.py", "chay_hop_dong.py", "tiem_loi.py", "gia_lap_chang.py")
NGUON_SH = ("chay_tat_ca.sh",)

TEN_CHOT = {
    "N1": "nền chạy phải là thư mục TẠM, ngoài app/du-lieu/",
    "N2": "CHO_PHEP_LIVE=False trên mọi adapter + cổng môi trường J&T ĐÓNG",
    "N3": "VIP_HUB_BIND trống hoặc loopback",
    "N4": "cờ cho phép gọi hãng KHÔNG bật",
    "N5": "VHG18_CONG_PG khác 5432",
    "N6": "nguồn của làn G20 không chứa pkill/killall",
    "N7": "không ai khai V-G09-01/V-13906-05 là đã cấp",
}
THU_TU_CHOT = ("N1", "N2", "N3", "N4", "N5", "N6", "N7")


# ===========================================================================
# Tiện ích
# ===========================================================================
def _trong_thu_muc_tam(duong):
    """Đường này có nằm trong một thư mục tạm không. So bằng realpath để `..` không lách được."""
    that = os.path.realpath(duong)
    for goc in THU_MUC_TAM:
        if goc and (that == os.path.realpath(goc) or that.startswith(os.path.realpath(goc) + os.sep)):
            return True
    return False


def _env_cua(bc):
    e = bc.get("env")
    return os.environ if e is None else e


def _la_ten_lenh(chuoi):
    """Chuỗi này có PHẢI là một lời gọi lệnh giết theo tên không.

    Khác hẳn "chuỗi này có NHẮC tới chữ ấy": một docstring giải thích *"không dùng pkill"* là
    văn xuôi, còn `["pkill", "-f", "server.py"]` là một LỜI GỌI. Phân biệt bằng vị trí: tên
    lệnh phải đứng ở ĐẦU chuỗi. Chỉ lọc thô theo từ khoá thì hoặc bỏ sót lời gọi, hoặc bắt oan
    chính dòng cảnh báo — và bộ dò bắt oan thì bị người ta tắt đi, còn bộ dò bỏ sót thì vô dụng.
    """
    return bool(re.match(r"^\s*(pkill|killall)\b", chuoi or ""))


def _chuoi_literal(nut):
    """Mọi chuỗi hằng nằm trong một nút AST (kể cả trong list/tuple/dict và f-string)."""
    ra = []
    for con in ast.walk(nut):
        if isinstance(con, ast.Constant) and isinstance(con.value, str):
            ra.append(con.value)
    return ra


#: Tên hàm mà một ĐỐI SỐ chuỗi của nó là một DÒNG LỆNH.
HAM_NHAN_LENH = ("system", "popen", "run", "call", "check_call", "check_output", "Popen")


def _vi_pham_py(tho):
    """Tìm LỜI GỌI giết-theo-tên trong mã Python — bằng AST, KHÔNG bằng so chuỗi.

    ====== VÌ SAO PHẢI LÀ AST ======
    Bộ dò phải đọc CHÍNH tệp định nghĩa nó (`chot_an_toan.py`), mà tệp ấy lại CHỨA các mẫu
    nguy hiểm dùng cho `--tu-kiem` — ví dụ chuỗi `"pkill -f server.py"`. So chuỗi thô thì bộ
    dò tự bắt chính dữ liệu thử của nó và ĐỎ VĨNH VIỄN. Bỏ hết chuỗi thì bộ dò BỎ SÓT
    `subprocess.run(["pkill", "-f", "server.py"])` — đúng lời gọi nó sinh ra để bắt.

    AST phân biệt được hai thứ ấy: một hằng chuỗi nằm TRƠ là dữ liệu; cùng hằng ấy nằm trong
    ĐỐI SỐ của `system`/`run`/`Popen` là một DÒNG LỆNH. Không có khuôn văn bản nào làm được
    phép phân biệt đó, nên chỗ này không được rút gọn thành regex.
    """
    try:
        cay = ast.parse(tho)
    except SyntaxError:
        return None                      # không đọc được mã thì KHÔNG được đoán
    ra = []
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Name) and nut.id in ("pkill", "killall"):
            ra.append("định danh %s" % nut.id)
        if not isinstance(nut, ast.Call):
            continue
        f = nut.func
        ten_goi = f.id if isinstance(f, ast.Name) else (
            f.attr if isinstance(f, ast.Attribute) else "")
        if ten_goi in ("pkill", "killall"):
            ra.append("gọi %s()" % ten_goi)
        if ten_goi in HAM_NHAN_LENH:
            for doi_so in list(nut.args) + [k.value for k in nut.keywords]:
                for s in _chuoi_literal(doi_so):
                    if _la_ten_lenh(s):
                        ra.append("dòng lệnh %r" % s.strip()[:60])
    return ra


def _loc_sh(tho):
    """Bỏ CHÚ THÍCH và CHUỖI TRÍCH DẪN khỏi một script shell, chỉ giữ mã.

    Vì sao phải bỏ cả CHUỖI chứ không chỉ chú thích: chính `chay_tat_ca.sh` có dòng
    `echo "dọn dẹp = theo ĐÚNG PID · không pkill/killall"` — một CẢNH BÁO, không phải một
    lệnh. Bộ dò đọc thô sẽ bắt chính dòng cảnh báo ấy rồi TỪ CHỐI mọi lượt chạy: lượt chạy
    đầu tiên của G20 đã đúng là đỏ như thế (mã thoát 4, 0 chặng nào chạy). Một bộ dò đỏ vì
    lời cảnh báo của chính nó là một bộ dò hỏng.

    Đổi lại, chuỗi nào ĐÚNG LÀ tên lệnh thì được GIỮ LẠI — `sh -c "pkill -f x"` là lời gọi
    thật, không phải văn xuôi.
    """
    ra = []
    for dong in tho.splitlines():
        out, i, n = [], 0, len(dong)
        while i < n:
            c = dong[i]
            if c == "#":
                break
            if c in ("'", '"'):
                q = c
                noi, i = [], i + 1
                while i < n and dong[i] != q:
                    if q == '"' and dong[i] == "\\":
                        noi.append(dong[i + 1] if i + 1 < n else "")
                        i += 2
                        continue
                    noi.append(dong[i])
                    i += 1
                i += 1
                gt = "".join(noi)
                out.append(gt if _la_ten_lenh(gt) else '""')
                continue
            out.append(c)
            i += 1
        ra.append("".join(out))
    return "\n".join(ra)


def loc_chu_thich_va_chuoi(ten, tho):
    """Bỏ CHÚ THÍCH và CHUỖI khỏi nguồn, chỉ giữ mã (trừ chuỗi ĐÚNG LÀ tên lệnh).

    Vì sao phải lọc: chính tệp này VIẾT RA chữ `pkill` trong chú thích và trong tài liệu.
    Một bộ dò đọc thô sẽ bắt chính lời giải thích "không dùng pkill" và biến nó thành vi phạm
    — bộ dò như thế ĐỎ VĨNH VIỄN, và một bộ dò luôn đỏ thì không ai đọc nữa.
    """
    if ten.endswith(".py"):
        ra = []
        # `FSTRING_START/_MIDDLE/_END` chỉ có từ Python 3.12; lấy bằng getattr để bộ lọc chạy
        # được trên cả 3.9–3.11 (chỗ này từng nổ `AttributeError` khi viết cứng tên).
        bo_qua = {tokenize.COMMENT, tokenize.STRING}
        for _ten in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
            _ma = getattr(tokenize, _ten, None)
            if _ma is not None:
                bo_qua.add(_ma)
        try:
            for tok in tokenize.generate_tokens(iter(tho.splitlines(True)).__next__):
                if tok.type in bo_qua:
                    continue
                ra.append(tok.string)
        except (tokenize.TokenError, IndentationError, SyntaxError):
            # Không đọc được mã thì KHÔNG được đoán: coi như còn nguyên để chốt còn thấy.
            return tho
        ma = " ".join(ra)
        # Lời gọi giết-theo-tên KHÔNG nằm trong phần văn bản ở trên (nó nằm trong ĐỐI SỐ, mà
        # đối số thì vừa bị bỏ đi). Gắn kết quả soi AST vào CUỐI, dưới dạng định danh trần, để
        # bộ dò chung phía dưới thấy được mà không phải có nhánh riêng.
        vi_pham = _vi_pham_py(tho)
        if vi_pham:
            ma = ma + "\n" + "\n".join(vi_pham)
        return ma
    if ten.endswith(".sh"):
        return _loc_sh(tho)
    return tho


def _doc_nguon_lan():
    """{tên tệp: mã đã lọc} cho mọi tệp mã của làn G20."""
    ra = {}
    for ten in NGUON_PY:
        d = os.path.join(THU_MUC_G20, ten)
        if os.path.isfile(d):
            with open(d, encoding="utf-8", errors="replace") as f:
                ra[ten] = loc_chu_thich_va_chuoi(ten, f.read())
    for ten in NGUON_SH:
        d = os.path.join(THU_MUC_G20, ten)
        if os.path.isfile(d):
            with open(d, encoding="utf-8", errors="replace") as f:
                ra[ten] = loc_chu_thich_va_chuoi(ten, f.read())
    thu = os.path.join(DU_AN, "app", "thu", "thu_g20_hop_dong.py")
    if os.path.isfile(thu):
        with open(thu, encoding="utf-8", errors="replace") as f:
            ra["app/thu/thu_g20_hop_dong.py"] = loc_chu_thich_va_chuoi("x.py", f.read())
    return ra


def giay_phep_duoc_khai(env=None):
    """Tập giấy phép mà môi trường ĐANG khai là đã cấp. Rỗng là trạng thái ĐÚNG của lượt này."""
    env = os.environ if env is None else env
    ra = set()
    for b in BIEN_GIAY_PHEP:
        tho = str(env.get(b, "") or "")
        ra |= {x.strip() for x in tho.replace(";", ",").split(",") if x.strip()}
    return ra


# ===========================================================================
# BẢY CHỐT — mỗi hàm trả (đạt: bool, lý_do: list[str]). Mọi đầu vào đều TIÊM ĐƯỢC.
# ===========================================================================
def kiem_nen_tam(bc):
    nen = bc.get("nen")
    if nen is None:
        nen = os.environ.get("VIP_HUB_DATA") or ""
    goc = bc.get("goc_du_an") or DU_AN
    that = os.path.realpath(os.path.join(goc, "app", "du-lieu"))
    ly = []
    if not nen:
        ly.append("nền chạy TRỐNG — harness chỉ chạy trên một nền TẠM do nó tự dựng.")
    else:
        n = os.path.realpath(nen)
        if n == that or n.startswith(that + os.sep):
            ly.append("nền %r trỏ vào dữ liệu THẬT (%s) — TỪ CHỐI." % (nen, that))
        elif not _trong_thu_muc_tam(nen):
            ly.append("nền %r không nằm trong thư mục tạm — TỪ CHỐI." % (nen,))
    return (not ly), ly


def kiem_cho_phep_live(bc):
    ly = []
    so = bc.get("so_dang_ky", None)
    if so is None:
        try:
            import adapter            # noqa: F401
            import adapter_jt         # noqa: F401
            import adapter_vtp        # noqa: F401
            so = adapter._DANG_KY
        except Exception as e:                                      # noqa: BLE001
            ly.append("không đọc được sổ đăng ký adapter (%s: %s) — không kiểm được thì TỪ CHỐI."
                      % (type(e).__name__, e))
            so = None
    if so is not None:
        if not so:
            ly.append("sổ đăng ký adapter RỖNG — chốt này không kiểm được gì.")
        for ma, lop in sorted(so.items()):
            live = getattr(lop, "CHO_PHEP_LIVE", "<thiếu>")
            if live is not False:
                ly.append("%s.CHO_PHEP_LIVE = %r — phải CHỐT CỨNG là False."
                          % (getattr(lop, "__name__", ma), live))

    cong = bc.get("cho_phep_jt", None)
    if cong is not None:
        if cong.get("sandbox"):
            ly.append("cổng môi trường J&T SANDBOX đang MỞ — chỉ được chạy MOCK.")
        if cong.get("production"):
            ly.append("cổng môi trường J&T PRODUCTION đang MỞ — không agent nào được mở.")
        return (not ly), ly
    try:
        import cau_hinh
        import adapter_jt
        if bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True)):
            ly.append("cau_hinh.JT_CHO_PHEP_SANDBOX đang MỞ — cần V-G09-01 + V-13906-05 mới được mở.")
        if bool(getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True)):
            ly.append("cau_hinh.JT_CHO_PHEP_PRODUCTION đang MỞ — không agent nào được mở.")
        for mt in ("sandbox", "production"):
            if adapter_jt.moi_truong_duoc_chay(mt):
                ly.append("adapter_jt.moi_truong_duoc_chay(%r)=True — LỆCH với cổng trong"
                          " `cau_hinh`. Hai nguồn nói hai điều khác nhau thì TỪ CHỐI." % mt)
    except Exception as e:                                          # noqa: BLE001
        ly.append("không đọc được cổng môi trường J&T (%s: %s) — không kiểm được thì TỪ CHỐI."
                  % (type(e).__name__, e))
    return (not ly), ly


def kiem_bind_loopback(bc):
    bind = str(_env_cua(bc).get("VIP_HUB_BIND", "") or "").strip()
    if bind and bind not in LOOPBACK:
        return False, ["VIP_HUB_BIND=%r không phải loopback — mở cổng ra ngoài là V-G11-01"
                       " (CHƯA CẤP). TỪ CHỐI." % bind]
    return True, []


def kiem_khong_goi_hang(bc):
    env = _env_cua(bc)
    ly = []
    for b in BIEN_GOI_HANG:
        v = str(env.get(b, "") or "").strip()
        if v not in ("", "0", "false", "False"):
            ly.append("%s=%r đang BẬT — V-G09-01 + V-13906-05 CHƯA CẤP, harness không có quyền"
                      " gọi hãng kể cả sandbox." % (b, v))
    return (not ly), ly


def kiem_khong_pg_5432(bc):
    cong = str(_env_cua(bc).get("VHG18_CONG_PG", CONG_PG_MAC_DINH) or "").strip()
    if cong == CONG_PG_CAM:
        return False, ["VHG18_CONG_PG=5432 là cụm PostgreSQL HỆ THỐNG đang giữ CSDL dự án khác"
                       " (vip_customs*). TỪ CHỐI."]
    return True, []


def kiem_khong_pkill(bc):
    nguon = bc.get("nguon")
    if nguon is None:
        nguon = _doc_nguon_lan()
    ly = []
    if not nguon:
        ly.append("không đọc được nguồn nào của làn G20 — chốt này không kiểm được gì thì TỪ CHỐI.")
        return False, ly
    for ten, ma in sorted(nguon.items()):
        for khop in re.finditer(r"\b(pkill|killall)\b", ma):
            ly.append("%s chứa `%s` — dọn tiến trình theo TÊN là giết cả làn khác đang chạy song"
                      " song. Mọi lượt dọn phải theo ĐÚNG PID." % (ten, khop.group(1)))
    return (not ly), ly


def kiem_giay_phep_chua_cap(bc):
    cap = bc.get("giay_phep", None)
    if cap is None:
        cap = giay_phep_duoc_khai(bc.get("env"))
    if cap:
        return False, ["có giấy phép được KHAI là ĐÃ CẤP (%s) — V-G09-01 và V-13906-05 KHÔNG phải"
                       " thứ một harness tự cấp. TỪ CHỐI." % ", ".join(sorted(cap))]
    return True, []


CHOT = {
    "N1": kiem_nen_tam,
    "N2": kiem_cho_phep_live,
    "N3": kiem_bind_loopback,
    "N4": kiem_khong_goi_hang,
    "N5": kiem_khong_pg_5432,
    "N6": kiem_khong_pkill,
    "N7": kiem_giay_phep_chua_cap,
}


def kiem_tat_ca(bc=None):
    """Chạy CẢ BẢY chốt. Trả {mã: [lý do]}, chỉ chứa chốt ĐỎ (rỗng = đủ chốt)."""
    bc = bc or {}
    do = {}
    for ma in THU_TU_CHOT:
        try:
            dat, ly = CHOT[ma](bc)
        except Exception as e:                                      # noqa: BLE001
            dat, ly = False, ["chốt %s NÉM LỖI (%s: %s) — chốt ném lỗi là chốt KHÔNG ĐẠT,"
                              " không được coi là đã qua." % (ma, type(e).__name__, e)]
        if not dat:
            do[ma] = ly
    return do


def bao_cao_moi_truong():
    """Dữ kiện ĐỌC ĐƯỢC về lớp vận chuyển thật — để BÁO CÁO, không phải một chốt."""
    tk = {}
    try:
        import cau_hinh
        tk["cau_hinh.JT_CHO_PHEP_SANDBOX"] = bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True))
        tk["cau_hinh.JT_CHO_PHEP_PRODUCTION"] = bool(
            getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True))
    except Exception as e:                                          # noqa: BLE001
        tk["loi_doc_cau_hinh"] = "%s: %s" % (type(e).__name__, e)
    try:
        import adapter
        import adapter_jt         # noqa: F401
        import adapter_vtp        # noqa: F401
        tk["adapter_cho_phep_live"] = {m: getattr(l, "CHO_PHEP_LIVE", "<thiếu>")
                                       for m, l in sorted(adapter._DANG_KY.items())}
    except Exception as e:                                          # noqa: BLE001
        tk["loi_doc_adapter"] = "%s: %s" % (type(e).__name__, e)
    tk["giay_phep_duoc_khai"] = sorted(giay_phep_duoc_khai())
    tk["VHG18_CONG_PG"] = str(os.environ.get("VHG18_CONG_PG", CONG_PG_MAC_DINH))
    tk["VIP_HUB_BIND"] = str(os.environ.get("VIP_HUB_BIND", "") or "")
    return tk


# ===========================================================================
# TỰ KIỂM BỘ DÒ — tám cấu hình tổng hợp, mỗi ca hỏng phải bị bắt bởi ĐÚNG chốt
# ===========================================================================
class _LopGia(object):
    def __init__(self, ten, live):
        self.__name__ = ten
        self.CHO_PHEP_LIVE = live


def _nen_tam_gia(ten="g20-tu-kiem-nen"):
    return os.path.join(tempfile.gettempdir(), ten)


def bo_ca_tu_kiem():
    """(mã, mô tả, phải_từ_chối, chuỗi_chứng_minh_đúng_chốt, kwargs) cho `--tu-kiem`.

    Đối chứng DƯƠNG là ca A: cấu hình đủ chốt phải ĐI QUA. Thiếu nó thì một bộ dò
    `return ["từ chối"]` cũng "bắt được" cả bảy ca hỏng và trông như đang hoạt động.
    """
    nen = _nen_tam_gia()
    dang_ky = {"jt": _LopGia("AdapterJT", False), "vtp": _LopGia("AdapterVTP", False)}
    env_sach = {"VIP_HUB_DATA": nen}
    khop = {"sandbox": False, "production": False}
    nguon_sach = {"chay_hop_dong.py": "PID = []\nos.kill(PID[0], 15)\n"}
    return [
        ("A", "cấu hình ĐỦ CHỐT (đối chứng dương) — phải ĐI QUA", False, None,
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon=nguon_sach)),
        ("B", "nền trỏ vào dữ liệu THẬT `app/du-lieu`", True, "dữ liệu THẬT",
         dict(nen=os.path.join(DU_AN, "app", "du-lieu"), so_dang_ky=dang_ky, env=env_sach,
              cho_phep_jt=khop, giay_phep=set(), nguon=nguon_sach)),
        ("C", "nền ngoài thư mục tạm", True, "thư mục tạm",
         dict(nen=os.path.join(DU_AN, "nen-khong-tam"), so_dang_ky=dang_ky, env=env_sach,
              cho_phep_jt=khop, giay_phep=set(), nguon=nguon_sach)),
        ("D", "một adapter có CHO_PHEP_LIVE = True", True, "CHO_PHEP_LIVE",
         dict(nen=nen, so_dang_ky={"jt": _LopGia("AdapterJT", True)}, env=env_sach,
              cho_phep_jt=khop, giay_phep=set(), nguon=nguon_sach)),
        ("E", "sổ đăng ký adapter RỖNG", True, "RỖNG",
         dict(nen=nen, so_dang_ky={}, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon=nguon_sach)),
        ("F", "VIP_HUB_BIND = 0.0.0.0 (mở cổng ra ngoài)", True, "VIP_HUB_BIND",
         dict(nen=nen, so_dang_ky=dang_ky, env=dict(env_sach, VIP_HUB_BIND="0.0.0.0"),
              cho_phep_jt=khop, giay_phep=set(), nguon=nguon_sach)),
        ("G", "cờ cho phép gọi hãng BẬT", True, "đang BẬT",
         dict(nen=nen, so_dang_ky=dang_ky,
              env=dict(env_sach, **{BIEN_GOI_HANG[0]: "1"}), cho_phep_jt=khop, giay_phep=set(),
              nguon=nguon_sach)),
        ("H", "cổng môi trường J&T SANDBOX bị MỞ", True, "SANDBOX đang MỞ",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach,
              cho_phep_jt={"sandbox": True, "production": False}, giay_phep=set(),
              nguon=nguon_sach)),
        ("I", "VHG18_CONG_PG = 5432 (cụm hệ thống)", True, "5432",
         dict(nen=nen, so_dang_ky=dang_ky, env=dict(env_sach, VHG18_CONG_PG="5432"),
              cho_phep_jt=khop, giay_phep=set(), nguon=nguon_sach)),
        ("J", "nguồn của làn chứa `pkill`", True, "pkill",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_tat_ca.sh": "pkill -f server.py\n"})),
        ("K", "nguồn làn chứa `killall` trong MÃ (không phải chú thích)", True, "killall",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_hop_dong.py": "import os\nos.system(\"killall python3\")\n"})),
        ("L", "biến môi trường KHAI là đã cấp giấy phép gọi hãng", True, "ĐÃ CẤP",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop,
              giay_phep={"V-G09-01"}, nguon=nguon_sach)),
        ("M", "chú thích có chữ `pkill` — KHÔNG được coi là vi phạm", False, None,
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_hop_dong.py": loc_chu_thich_va_chuoi(
                  "x.py", "# khong dung pkill hay killall\nPID = 1\n")})),
        ("N", "shell CHUỖI có chữ `pkill` (echo cảnh báo) — KHÔNG được coi là vi phạm",
         False, None,
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_tat_ca.sh": loc_chu_thich_va_chuoi(
                  "x.sh", "echo \"khong pkill, khong killall\"\nPID=1\nkill -TERM $PID\n")})),
        ("O", "python GỌI THẬT `[\"pkill\", ...]` — PHẢI bị bắt (chuỗi đúng là tên lệnh)",
         True, "pkill",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_hop_dong.py": loc_chu_thich_va_chuoi(
                  "x.py", "import subprocess\nsubprocess.run([\"pkill\", \"-f\", \"server.py\"])\n")})),
        ("P", "shell GỌI THẬT `sh -c \"pkill -f x\"` — PHẢI bị bắt", True, "pkill",
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chay_tat_ca.sh": loc_chu_thich_va_chuoi(
                  "x.sh", "sh -c \"pkill -f server.py\"\n")})),
        ("Q", "docstring python nhắc chữ `pkill` — KHÔNG được coi là vi phạm", False, None,
         dict(nen=nen, so_dang_ky=dang_ky, env=env_sach, cho_phep_jt=khop, giay_phep=set(),
              nguon={"chot_an_toan.py": loc_chu_thich_va_chuoi(
                  "x.py", "def kiem_khong_pkill(bc):\n"
                          "    \"\"\"Chot nay cam pkill va killall trong ma cua lan.\"\"\"\n"
                          "    return True, []\n")})),
    ]


def tu_kiem(cho_in=True):
    """Chạy bộ dò trên các cấu hình tổng hợp. Trả (tổng, số_hỏng, chi_tiết)."""
    so_hong, ket_qua = 0, []
    for ma, mo_ta, phai_tu_choi, chua, kw in bo_ca_tu_kiem():
        do = kiem_tat_ca(kw)
        bi_tu_choi = bool(do)
        dung_ket_qua = (bi_tu_choi == phai_tu_choi)
        ly_phang = [x for ds in do.values() for x in ds]
        dung_chot = (not phai_tu_choi) or any(chua in x for x in ly_phang)
        dat = dung_ket_qua and dung_chot
        if not dat:
            so_hong += 1
        ket_qua.append({"ma": ma, "mo_ta": mo_ta, "mong_doi_tu_choi": phai_tu_choi,
                        "thuc_te_tu_choi": bi_tu_choi, "dung_chot": dung_chot, "dat": dat,
                        "chot_do": sorted(do), "ly_do": ly_phang[:1]})
        if cho_in:
            print("  %s [%s] %s" % ("✓" if dat else "✗", ma, mo_ta))
            if not dat:
                print("        MONG ĐỢI từ chối=%s (bắt bởi chốt chứa %r) · THỰC TẾ=%s · chốt đỏ=%s"
                      % (phai_tu_choi, chua, bi_tu_choi, sorted(do) or "(không)"))
            elif ly_phang:
                print("        bắt đúng chốt: %s" % ly_phang[0])
    return len(ket_qua), so_hong, ket_qua


def main(argv):
    if "--tu-kiem" in argv:
        ds = bo_ca_tu_kiem()
        print("═" * 78)
        print("TỰ KIỂM BỘ DÒ CHỐT AN TOÀN G20 — %d cấu hình tổng hợp" % len(ds))
        print("(bảy chốt: nền tạm · CHO_PHEP_LIVE · bind · gọi hãng · cổng PG · pkill · giấy phép)")
        print("═" * 78)
        tong, hong, _ = tu_kiem()
        print("─" * 78)
        print("TỰ KIỂM: %d/%d ca đạt · %d hỏng" % (tong - hong, tong, hong))
        if hong:
            print("BỘ DÒ HỎNG: nó không phân biệt được cấu hình an toàn với cấu hình nguy hiểm,")
            print("hoặc bắt đúng kết quả nhưng vì lý do khác chốt đang muốn đo.")
            print("Mọi lời khai 'harness đã từ chối chạy' ở lượt này KHÔNG có giá trị.")
            return 1
        print("Bộ dò bắt ĐÚNG chốt ở cả %d cấu hình ⇒ lời khai 'TỪ CHỐI CHẠY' mới có nghĩa." % tong)
        print("Dữ kiện lớp vận chuyển: %s" % bao_cao_moi_truong())
        return 0
    nen = os.environ.get("VIP_HUB_DATA") or ""
    do = kiem_tat_ca({"nen": nen})
    if do:
        print("TỪ CHỐI CHẠY — mất ít nhất một chốt an toàn:")
        for ma in sorted(do):
            print("  · [%s] %s" % (ma, TEN_CHOT[ma]))
            for x in do[ma]:
                print("      %s" % x)
        return 4
    print("BẢY CHỐT AN TOÀN: ĐỦ. Nền %s · bind loopback · CHO_PHEP_LIVE=False · không gọi hãng"
          " · cổng PG ≠ 5432 · nguồn làn không pkill/killall · không ai tự cấp giấy phép." % nen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
