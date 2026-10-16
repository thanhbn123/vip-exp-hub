#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 — AG-05: CHỐT "CÂY SẠCH" (TỰ DÒ) + VÂN TAY (GIT LÀ CHÍNH) + MÔI TRƯỜNG GIT (N-G18-00).

VÌ SAO CÓ TỆP NÀY
-----------------
Ba lỗi đã tái diễn nhiều lần trong dự án, mỗi lỗi đều là "thứ dùng để kiểm chứng lại hổng":

1. `N-G18-03` → `N-G19-03` (**CỔNG C1** của AG-01): chốt "cây sạch" của wave trước miễn trừ theo
   **DANH SÁCH TÊN CỨNG**, nên chỉ cần một làn KHÁC giao một **tệp MỚI** là cổng ĐỎ — không phải
   vì cây bẩn, mà vì người ta vừa làm ĐÚNG việc của mình. Ba wave liên tiếp.
   Chữa đúng: miễn trừ theo **QUY TẮC** (vùng thử/tài liệu), và bộ kiểm **TỰ TÌM** tệp mới bằng
   `git status -uall` — không ai phải nhớ thêm một dòng vào danh sách.
   **KHÔNG** nới thành "bỏ qua hết": đối chứng âm bắt buộc (tệp SẢN PHẨM bẩn ⇒ ĐỎ) nằm ngay
   trong tệp này và trong `A_Nen.test_a1d` của cả `thu_qa_g17.py` lẫn `thu_qa_g18.py`.

2. `G16-09`: lệnh vân tay cũ (`find app gateway thu_frontend thu_giao_dien -name '*.py' …`) **MÙ**
   với `docs/` và với `*.md` — sửa chính bản hợp đồng mà vân tay không nhúc nhích. Chữa đúng:
   **Git là CHÍNH** (`rev-parse HEAD` + `git diff HEAD` rỗng + `status --porcelain -uall` rỗng),
   vân tay thư mục chỉ là **DỰ PHÒNG** (luật §41 `docs/SHARED_CONTRACTS.md`).

3. `N-G17-00`/`N-G18-00`: `GIT_CONFIG_COUNT=N` mà thiếu `GIT_CONFIG_KEY_0..N-1` làm **MỌI** lệnh
   git thoát 128 (`fatal: unable to parse command-line config`) ⇒ **hai nhiệt kế cho hai kết quả
   khác nhau trên CÙNG một cây**. Chữa đúng: tự chuẩn hoá **KÈM CẢNH BÁO**, và **KHÔNG nuốt lỗi
   thật** — sau khi chuẩn hoá, lệnh git hỏng vì lý do THẬT vẫn phải hỏng, kèm stderr thật.

BA VIỆC, MỘT CHỖ
----------------
`thu_qa_g17.py`, `thu_qa_g18.py` và `chay_tat_ca.sh` đều gọi tệp này. Ba bản sao của cùng một
luật là ba bản sẽ trôi khỏi nhau — đó đúng là khuôn `N-G18-00` (hai nhiệt kế, hai kết quả).

CHẠY
----
    python3 app/thu/thu_g21_chotcay.py            # bộ tự kiểm (unittest)
    python3 app/thu/thu_g21_chotcay.py --chot     # in các dòng ĐỎ; thoát 1 nếu cây bẩn NGOÀI vùng
    python3 app/thu/thu_g21_chotcay.py --van-tay  # in vân tay (JSON một dòng) + chế độ đang dùng
"""
import ast
import atexit
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC_TEP = os.path.abspath(__file__)
GOC_THU = os.path.dirname(GOC_TEP)
GOC_APP = os.path.dirname(GOC_THU)
GOC_CAY = os.path.dirname(GOC_APP)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. MÔI TRƯỜNG GIT (`N-G17-00` / `N-G18-00`) — TỰ CHUẨN HOÁ **KÈM CẢNH BÁO**, KHÔNG NUỐT LỖI THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# `GIT_CONFIG_COUNT=N` bắt git đọc N cặp `GIT_CONFIG_KEY_i`/`GIT_CONFIG_VALUE_i`. Thiếu khoá ⇒
# git thoát 128 ngay ở bước parse, TRƯỚC cả khi biết mình đang ở đâu. Hệ quả đo được: cùng một
# cây, cùng `HEAD`, mà lượt "nguyên văn" báo 2 bộ hỏng còn lượt "đã gỡ biến" báo 0.
#
# BA LUẬT Ở ĐÂY:
#   (a) DỊ DẠNG thì CHUẨN HOÁ — nhưng phải IN RA. Im lặng gỡ biến là che mất một môi trường hỏng.
#   (b) HỢP LỆ thì KHÔNG ĐƯỢC GỠ. `GIT_CONFIG_COUNT=1, KEY_0=user.name, VALUE_0=x` là một cấu
#       hình CÓ THẬT; gỡ nó là nuốt một lỗi thật (git sẽ chạy với cấu hình khác ý người gọi).
#   (c) Sau khi chuẩn hoá, lệnh git hỏng vì lý do THẬT vẫn phải HỎNG — xem `test_e3`.

TEN_GIA_DINH = "GIT_CONFIG_"
_CANH_BAO_DA_IN = set()


def soi_gia_dinh_git(env=None):
    """Soi gia đình `GIT_CONFIG_*`. Trả bản ghi; KHÔNG sửa gì, KHÔNG in gì (hàm THUẦN)."""
    e = dict(os.environ if env is None else env)
    ra = {"count": e.get("GIT_CONFIG_COUNT"), "so_khoa": 0, "so_gia_tri": 0,
          "di_dang": False, "ly_do": "", "go_bo": [], "canh_bao": []}
    for k in e:
        if k.startswith(TEN_GIA_DINH + "KEY_"):
            ra["so_khoa"] += 1
        elif k.startswith(TEN_GIA_DINH + "VALUE_"):
            ra["so_gia_tri"] += 1

    raw = (e.get("GIT_CONFIG_COUNT") or "").strip()
    if raw == "":
        if ra["so_khoa"] or ra["so_gia_tri"]:
            # git BỎ QUA KEY_/VALUE_ khi thiếu COUNT ⇒ không hỏng, nhưng vẫn là dấu hiệu bất thường.
            ra["canh_bao"].append("có GIT_CONFIG_KEY_*/VALUE_* nhưng KHÔNG có GIT_CONFIG_COUNT "
                                  "(git bỏ qua chúng — chỉ ghi ra, KHÔNG gỡ)")
        return ra
    try:
        n = int(raw)
    except ValueError:
        n = None
    if n is None or n < 0:
        ra["di_dang"] = True
        ra["ly_do"] = "GIT_CONFIG_COUNT=%r không phải số nguyên không âm" % (raw,)
    else:
        thieu = []
        for i in range(n):
            k = (e.get("GIT_CONFIG_KEY_%d" % i) or "")
            if k.strip() == "":
                thieu.append("KEY_%d" % i)
            if ("GIT_CONFIG_VALUE_%d" % i) not in e:
                thieu.append("VALUE_%d" % i)
        if thieu:
            ra["di_dang"] = True
            ra["ly_do"] = ("GIT_CONFIG_COUNT=%d nhưng THIẾU %s ⇒ MỌI lệnh git thoát 128 "
                           "(fatal: unable to parse command-line config)" % (n, ", ".join(thieu)))
        # KEY_/VALUE_ nằm NGOÀI khoảng [0, n): git bỏ qua — ghi ra để không im lặng.
        la = []
        for k in sorted(e):
            m = re.fullmatch(re.escape(TEN_GIA_DINH) + r"(KEY|VALUE)_(\d+)", k)
            if m and int(m.group(2)) >= n:
                la.append(k)
        if la:
            ra["canh_bao"].append("biến NGOÀI khoảng [0,%d): %s (git bỏ qua — chỉ ghi ra)"
                                  % (n, ", ".join(la)))
    if ra["di_dang"]:
        ra["go_bo"] = sorted(k for k in e if k.startswith(TEN_GIA_DINH))
    return ra


def env_git(env=None, im_lang=False):
    """Môi trường ĐÃ CHUẨN HOÁ để chạy git. Dị dạng ⇒ gỡ CẢ gia đình `GIT_CONFIG_*` + CẢNH BÁO."""
    e = dict(os.environ if env is None else env)
    ban_ghi = soi_gia_dinh_git(e)
    if ban_ghi["di_dang"]:
        for k in ban_ghi["go_bo"]:
            e.pop(k, None)
        if not im_lang:
            khoa = tuple(ban_ghi["go_bo"])
            if khoa not in _CANH_BAO_DA_IN:
                _CANH_BAO_DA_IN.add(khoa)
                print("[cảnh báo N-G18-00] %s" % ban_ghi["ly_do"], file=sys.stderr)
                print("[cảnh báo N-G18-00] đã GỠ %d biến: %s"
                      % (len(khoa), ", ".join(khoa)), file=sys.stderr)
                print("[cảnh báo N-G18-00] đây là MÔI TRƯỜNG hỏng, KHÔNG phải cây hỏng — "
                      "lệnh git hỏng vì lý do THẬT vẫn sẽ hỏng và được báo nguyên văn.",
                      file=sys.stderr)
    for k in ban_ghi["canh_bao"]:
        khoa = (k,)
        if khoa not in _CANH_BAO_DA_IN:
            _CANH_BAO_DA_IN.add(khoa)
            print("[cảnh báo N-G18-00] %s" % k, file=sys.stderr)
    return e


def _git(*tham_so, goc=None, env=None, giay=60):
    """Chạy git trong cây `goc` với môi trường ĐÃ CHUẨN HOÁ. Trả `CompletedProcess` NGUYÊN VẸN.

    KHÔNG bao giờ tự phán "thành công": người gọi phải đọc `returncode` và `stderr`. Một hàm
    tự nuốt mã thoát là đúng chỗ để lỗi thật biến mất (`test_e3` canh điều đó).
    """
    e = env_git(env)
    return subprocess.run(["git", "-C", goc or GOC_CAY] + list(tham_so), capture_output=True,
                          text=True, env=e, timeout=giay)


def _git_hoac_chet(*tham_so, goc=None, env=None, giay=60):
    """Như `_git` nhưng NÉM LỖI kèm mã thoát + stderr THẬT nếu git hỏng. Không nuốt lỗi thật."""
    r = _git(*tham_so, goc=goc, env=env, giay=giay)
    if r.returncode != 0:
        raise RuntimeError("git %s hỏng (mã thoát %d): %s"
                           % (" ".join(tham_so), r.returncode, (r.stderr or "").strip()))
    return r


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. VÙNG THỬ/TÀI LIỆU — TỰ DÒ, VÀ CHỨNG MINH BẰNG MÁY RẰNG VÙNG KHÔNG CHỨA MÃ SẢN PHẨM
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# "CÂY SẠCH" = **KHÔNG có thay đổi NÀO ngoài các tệp mà WAVE ĐANG LÀM**. Vậy "các tệp mà wave
# đang làm" là gì? Nếu trả lời bằng một DANH SÁCH TÊN thì mỗi wave phải sửa danh sách — và ai quên
# là cổng ĐỎ vì một tệp hợp lệ (`N-G18-03`/`N-G19-03`, ba lần).
#
# Trả lời bằng QUY TẮC: một đường thuộc **VÙNG THỬ/TÀI LIỆU** nếu nó nằm trong thư mục `docs/`,
# hoặc trong BẤT KỲ thư mục nào có tên bắt đầu bằng `thu` (`app/thu/`, `thu_giao_dien/`,
# `thu_frontend/`, và thư mục thử MỚI chưa ai nghĩ ra). Quy tắc này KHÔNG cần sửa mỗi wave.
#
# Vì sao tha được: mã trong vùng thử/tài liệu KHÔNG chạy trong sản phẩm. Đó là một LỜI KHAI, nên
# `chung_minh_vung()` BIẾN NÓ THÀNH PHÉP ĐO — hai chứng minh độc lập:
#   (A1) KHÔNG tệp sản phẩm nào import / nạp một mô-đun nằm trong vùng (AST, không grep chú thích);
#   (A2) danh sách thư mục TĨNH mà máy chủ CHO PHÉP phục vụ (`app/server.py::THU_MUC_CHO_PHEP`)
#        KHÔNG chứa vùng nào ⇒ vùng không đi ra được tới người dùng qua HTTP.
# Chứng minh hỏng ⇒ `chot_cay_sach()` NÉM LỖI (không âm thầm tha một vùng đã thành sản phẩm).

def _la_ten_vung(duong_thu_muc):
    """Tên một THƯ MỤC có phải vùng thử/tài liệu không. Quy tắc, không danh sách."""
    ten = duong_thu_muc.rstrip("/").split("/")[-1].lower()
    return ten == "docs" or ten.startswith("thu")


def vung_thu_tai_lieu(goc=None, env=None):
    """VÙNG THỬ/TÀI LIỆU của cây — TỰ DÒ từ `git ls-files` (kể cả tệp chưa theo dõi).

    Trả tuple các tiền tố thư mục (có `/` cuối), ví dụ `('app/thu/', 'docs/', 'thu_frontend/')`.
    KHÔNG liệt kê tệp: một tệp mới trong vùng tự khớp, không ai phải thêm dòng nào.
    """
    ra = set()
    for doi_so in (("ls-files",), ("ls-files", "--others", "--exclude-standard")):
        r = _git(*doi_so, goc=goc, env=env)
        if r.returncode != 0:
            raise RuntimeError("`git %s` hỏng (mã thoát %d): %s"
                               % (" ".join(doi_so), r.returncode, (r.stderr or "").strip()))
        for p in r.stdout.splitlines():
            if not p.strip():
                continue
            phan = p.split("/")
            for i in range(1, len(phan)):          # tiền tố THƯ MỤC, bỏ tên tệp
                d = "/".join(phan[:i])
                if _la_ten_vung(d):
                    ra.add(d + "/")
    return tuple(sorted(ra))


def la_trong_vung(duong, vung):
    """Đường (tương đối gốc cây) có nằm trong một vùng thử/tài liệu không."""
    d = duong.lstrip("./")
    return any(d == v.rstrip("/") or d.startswith(v) for v in vung)


def mau_vung_chuan(goc=None, env=None):
    """Mẫu fnmatch của vùng thử/tài liệu — dạng dùng được với `fnmatch` như luật cũ."""
    return tuple(v + "**" for v in vung_thu_tai_lieu(goc=goc, env=env))


def _khop(duong, mau):
    """Khớp mẫu — CÙNG luật `fnmatch` mà `thu_g20_baomat.py` dùng để đọc khai báo bằng AST."""
    return duong == mau or fnmatch.fnmatch(duong, mau)


def _tach_import(nguon):
    """Các mô-đun được THAM CHIẾU trong một nguồn Python (AST — không grep chú thích)."""
    ra = []
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Import):
            ra.extend(a.name for a in nut.names)
        elif isinstance(nut, ast.ImportFrom):
            if nut.level == 0 and nut.module:
                ra.append(nut.module)
        elif isinstance(nut, ast.Call):
            f = nut.func
            ten = getattr(f, "attr", None) or getattr(f, "id", None)
            if ten in ("import_module", "__import__") and nut.args:
                a = nut.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    ra.append(a.value)
    return ra


def _giai_ma_thanh_duong(ten_mo_dun, goc):
    """Mô-đun `a.b.c` → đường dẫn tệp trong cây (nếu có). Thử cả gốc cây lẫn `app/`."""
    phan = ten_mo_dun.split(".")
    for g in (goc, os.path.join(goc, "app")):
        for duoi in (".py", "/__init__.py"):
            p = os.path.join(g, *phan) + duoi
            if os.path.exists(p):
                return os.path.relpath(p, goc).replace(os.sep, "/")
    return None


def _import_js(nguon):
    """Chuỗi đường dẫn trong `require(...)` / `from "..."` / `import("...")` của JS."""
    ra = []
    ra.extend(re.findall(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", nguon))
    ra.extend(re.findall(r"""from\s+['"]([^'"]+)['"]""", nguon))
    ra.extend(re.findall(r"""import\(\s*['"]([^'"]+)['"]\s*\)""", nguon))
    return ra


def _tep_san_xuat(goc, vung):
    """Tệp SẢN XUẤT = tệp ĐƯỢC THEO DÕI, nằm NGOÀI mọi vùng thử/tài liệu."""
    r = _git_hoac_chet("ls-files", goc=goc)
    ra = []
    for p in r.stdout.splitlines():
        if not p.strip() or la_trong_vung(p, vung):
            continue
        if p.endswith(".py") or p.endswith(".js") or p.endswith(".mjs"):
            ra.append(p)
    return sorted(ra)


def chung_minh_vung(goc=None, env=None, vung=None, mau=None):
    """PHÉP ĐO: vùng thử/tài liệu có THẬT SỰ không chạy trong sản phẩm không.

    Trả danh sách VI PHẠM (rỗng = chứng minh đứng vững). Không có phép đo này thì "tha cả vùng"
    chỉ là một lời khai, và một vùng lỡ trở thành sản phẩm sẽ được tha trong im lặng.
    """
    goc = goc or GOC_CAY
    vung = tuple(vung) if vung is not None else vung_thu_tai_lieu(goc=goc, env=env)
    mau = tuple(mau) if mau is not None else tuple(v + "**" for v in vung)
    vi = []
    for p in _tep_san_xuat(goc, vung):
        try:
            with open(os.path.join(goc, p), encoding="utf-8") as f:
                nguon = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        if p.endswith(".py"):
            for ten in _tach_import(nguon):
                d = _giai_ma_thanh_duong(ten, goc)
                if d and la_trong_vung(d, vung):
                    vi.append("%s imports %s → %s (nằm trong vùng thử)" % (p, ten, d))
        else:
            for tham in _import_js(nguon):
                if not tham.startswith("."):
                    continue
                d = os.path.normpath(os.path.join(os.path.dirname(p), tham)).replace(os.sep, "/")
                if la_trong_vung(d, vung):
                    vi.append("%s nạp %s → %s (nằm trong vùng thử)" % (p, tham, d))
    # (A2) danh sách thư mục TĨNH máy chủ cho phép phục vụ.
    bang = os.path.join(goc, "app", "server.py")
    if not os.path.exists(bang):
        vi.append("KHÔNG đọc được app/server.py ⇒ chứng minh (A2) không chạy được (không tha mù)")
        return vi
    with open(bang, encoding="utf-8") as f:
        cay = ast.parse(f.read())
    thay = None
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "THU_MUC_CHO_PHEP" for t in nut.targets):
            try:
                thay = ast.literal_eval(nut.value)
            except ValueError:
                thay = None
    if thay is None:
        vi.append("app/server.py KHÔNG còn `THU_MUC_CHO_PHEP` dạng literal ⇒ chứng minh (A2) "
                  "không chạy được (không tha mù)")
        return vi
    for t in thay:
        if la_trong_vung(str(t), vung):
            vi.append("app/server.py PHỤC VỤ %r — nằm trong vùng thử ⇒ vùng đã thành sản phẩm" % (t,))
    return vi


def _co_rang_chung_minh_vung():
    """ĐỐI CHỨNG DƯƠNG cho `chung_minh_vung`: bộ dò phải THẤY một vi phạm cố ý.

    Không có phép kiểm này thì "0 vi phạm" có thể chỉ là một bộ dò mù — và một bộ dò mù ở đây
    nghĩa là cả một vùng đã thành sản phẩm vẫn được tha.
    """
    tam = tempfile.mkdtemp(prefix="veh-g21-cm-")
    try:
        os.makedirs(os.path.join(tam, "app", "thu"), exist_ok=True)
        os.makedirs(os.path.join(tam, "admin"), exist_ok=True)
        with open(os.path.join(tam, "app", "thu", "thu_gia.py"), "w", encoding="utf-8") as f:
            f.write("# tệp trong vùng thử\n")
        with open(os.path.join(tam, "admin", "gia.js"), "w", encoding="utf-8") as f:
            f.write("const x = require('../app/thu/thu_gia.py');\n")
        # (A1) bộ dò import Python phải thấy `thu.thu_gia` chạm vùng
        d = _giai_ma_thanh_duong("thu.thu_gia", tam)
        if d != "app/thu/thu_gia.py":
            return False, "bộ giải mã mô-đun mù: thu.thu_gia → %r" % (d,)
        # (A2) bộ dò JS phải thấy đường dẫn chạm vùng
        with open(os.path.join(tam, "admin", "gia.js"), encoding="utf-8") as f:
            nguon = f.read()
        thay = False
        for tham in _import_js(nguon):
            dd = os.path.normpath(os.path.join("admin", tham)).replace(os.sep, "/")
            if la_trong_vung(dd, ("app/thu/",)):
                thay = True
        if not thay:
            return False, "bộ dò JS mù: không thấy require() trỏ vào vùng"
        return True, ""
    finally:
        shutil.rmtree(tam, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. CHỐT "CÂY SẠCH" — TỰ TÌM TỆP MỚI, KHÔNG LIỆT KÊ CỨNG, KHÔNG "BỎ QUA HẾT"
# ══════════════════════════════════════════════════════════════════════════════════════════════

def duong_tu_dong_porcelain(dong):
    """Đường của một dòng `git status --porcelain`. Dòng đổi tên trả CẢ HAI đường."""
    p = dong[3:].strip()
    if " -> " in p:
        cu, moi = p.split(" -> ", 1)
        return [x.strip().strip('"') for x in (cu, moi)]
    return [p.strip('"')]


def phan_loai(dong, mau):
    """HÀM THUẦN: chia các dòng `git status` thành THA ĐƯỢC và ĐỎ.

    ĐỎ = "thay đổi NGOÀI các tệp mà wave đang làm". Một dòng đổi tên bị ĐỎ nếu MỘT TRONG HAI
    đường nằm ngoài vùng: kéo một tệp sản phẩm vào thư mục thử vẫn là một thay đổi sản phẩm.
    """
    cho_phep, do = [], []
    for d in dong:
        if not d.strip():
            continue
        ds = duong_tu_dong_porcelain(d)
        if all(any(_khop(x, m) for m in mau) for x in ds):
            cho_phep.append(d)
        else:
            do.append(d)
    return {"cho_phep": cho_phep, "do": do}


def tim_tep_moi(goc=None, env=None):
    """Các TỆP MỚI (chưa theo dõi) — TỰ TÌM bằng git, không danh sách. Chỉ để IN RA, không nuốt."""
    r = _git_hoac_chet("ls-files", "--others", "--exclude-standard", goc=goc, env=env)
    return [p for p in r.stdout.splitlines() if p.strip()]


def chot_cay_sach(goc=None, env=None, mau=None, kiem_chung_minh=True):
    """CHỐT: trả các dòng `git status` ĐỎ (rỗng = cây sạch theo đúng nghĩa của wave).

    `kiem_chung_minh=True` ⇒ chạy `chung_minh_vung()` TRƯỚC; chứng minh hỏng thì NÉM LỖI, vì khi
    đó "tha cả vùng" không còn là một quyết định có căn cứ.
    """
    goc = goc or GOC_CAY
    if kiem_chung_minh:
        vi = chung_minh_vung(goc=goc, env=env)
        if vi:
            raise RuntimeError("VÙNG THỬ/TÀI LIỆU không còn vô hại — chốt TỪ CHỐI tha:\n  - "
                               + "\n  - ".join(vi))
    if mau is None:
        mau = mau_vung_chuan(goc=goc, env=env)
    r = _git_hoac_chet("status", "--porcelain=v1", "-uall", goc=goc, env=env)
    return phan_loai(r.stdout.splitlines(), mau)["do"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. VÂN TAY — GIT LÀ CHÍNH, THƯ MỤC LÀ DỰ PHÒNG (luật §41; vá `G16-09`)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def van_tay_git(goc=None, env=None):
    """VÂN TAY CHÍNH: `HEAD` + `git diff HEAD` + `git status --porcelain -uall`.

    Phủ MỌI tệp được theo dõi (kể cả `docs/**`, `.md`, `.env.example`, `.gitignore`) và mọi thay
    đổi CHƯA COMMIT (kể cả tệp mới). Đây là bản vá của `G16-09`: bản cũ chỉ `find` bốn thư mục
    theo bốn đuôi tệp nên `docs/*.md` nằm ngoài tầm nhìn.
    """
    h = _git("rev-parse", "HEAD", goc=goc, env=env)
    if h.returncode != 0:
        raise RuntimeError("`git rev-parse HEAD` hỏng (mã thoát %d): %s"
                           % (h.returncode, (h.stderr or "").strip()))
    head = h.stdout.strip()
    d = _git_hoac_chet("diff", "HEAD", "--name-only", goc=goc, env=env)
    s = _git_hoac_chet("status", "--porcelain=v1", "-uall", goc=goc, env=env)
    doi = [p for p in d.stdout.splitlines() if p.strip()]
    dong = [x for x in s.stdout.splitlines() if x.strip()]
    return {"head": head, "diff": doi, "status": dong, "sach": not doi and not dong}


def van_tay_git_status(goc=None, env=None):
    """Vân tay theo TÊN: `{ git ls-files -s; git status --porcelain -uall; }` → sha256.

    Rẻ, nhưng **KHÔNG thấy NỘI DUNG**: một tệp đã bẩn sẵn mà bị sửa thêm vẫn cho CÙNG một chuỗi.
    Vì thế nó KHÔNG phải bản dự phòng — bản dự phòng là `van_tay_thu_muc()` (băm nội dung).
    """
    ls = _git_hoac_chet("ls-files", "-s", goc=goc, env=env).stdout
    st = _git_hoac_chet("status", "--porcelain=v1", "-uall", goc=goc, env=env).stdout
    return hashlib.sha256((ls + "\x00" + st).encode("utf-8")).hexdigest()


def _bam_noi_dung(goc, ds):
    """sha256 của [đường dẫn + sha256 nội dung] cho một danh sách đường — băm NỘI DUNG, không tên."""
    h = hashlib.sha256()
    for p in sorted(ds):
        h.update(p.encode("utf-8"))
        h.update(b"\x00")
        try:
            with open(os.path.join(goc, p), "rb") as f:
                h.update(hashlib.sha256(f.read()).digest())
        except OSError:
            h.update(b"<khong-doc-duoc>")
        h.update(b"\x01")
    return h.hexdigest()


def van_tay_thu_muc(goc=None, env=None):
    """VÂN TAY THƯ MỤC (DỰ PHÒNG, băm **NỘI DUNG**).

    Phủ mọi tệp **KHÔNG bị `.gitignore`** — tệp được theo dõi LẪN tệp mới chưa theo dõi — và băm
    **nội dung** từng tệp. Nhờ đó nó bắt được cả thứ mà vân tay theo TÊN mù:
      · `docs/**`, `*.md`, `.gitignore`, `.env.example` (bản cũ `G16-09` chỉ `find` bốn thư mục
        theo bốn đuôi tệp ⇒ MÙ với đúng bản hợp đồng);
      · một tệp ĐÃ BẨN SẴN mà bị sửa thêm (tên tệp không đổi ⇒ vân tay theo tên không nhúc nhích).
    Và nó **CỐ Ý** bỏ qua tệp bị `.gitignore` — `thu_giao_dien/_bao-cao/**`, `_ket-qua/**`,
    `app/du-lieu/khoa-noi-bo.key`, `__pycache__/**` đổi SAU MỖI LƯỢT CHẠY; băm chúng thì vân tay
    báo "cây đã đổi" mỗi lần và người đọc sẽ học cách bỏ qua nó (bài học §1.0 `docs/QA_G20.md`).
    """
    goc = goc or GOC_CAY
    theo_doi = [p for p in _git_hoac_chet("ls-files", goc=goc, env=env).stdout.splitlines() if p]
    moi = [p for p in _git_hoac_chet("ls-files", "--others", "--exclude-standard", goc=goc,
                                     env=env).stdout.splitlines() if p]
    return {"theo_doi": _bam_noi_dung(goc, theo_doi), "chua_theo_doi": _bam_noi_dung(goc, moi),
            "so_theo_doi": len(theo_doi), "so_chua_theo_doi": len(moi)}


def van_tay(goc=None, env=None):
    """Bản ghi vân tay đầy đủ, kèm CHẾ ĐỘ đang dùng (`GIT` khi sạch, `THU_MUC` khi bẩn)."""
    r = van_tay_git(goc=goc, env=env)
    r["thu_muc"] = van_tay_thu_muc(goc=goc, env=env)
    r["theo_ten"] = van_tay_git_status(goc=goc, env=env)
    r["che_do"] = "GIT" if r["sach"] else "THU_MUC"
    return r


DUOI_TEP_BAN_MU_G16_09 = (".py", ".mjs", ".sh", ".json")
GOC_BAN_MU_G16_09 = ("app", "gateway", "thu_frontend", "thu_giao_dien")


def van_tay_mu_g16_09(goc=None):
    """BẢN MÙ CŨ (`G16-09`) — GIỮ LẠI CHỈ ĐỂ LÀM ĐỐI CHỨNG ÂM.

    Đúng lệnh cũ: `find app gateway thu_frontend thu_giao_dien -type f \\( -name '*.py' -o
    -name '*.mjs' -o -name '*.sh' -o -name '*.json' \\) | sort | shasum -a 256`. `docs/` KHÔNG
    nằm trong phạm vi và `.md` KHÔNG nằm trong danh sách đuôi ⇒ nó mù với chính bản hợp đồng.
    """
    goc = goc or GOC_CAY
    ra = []
    for g in GOC_BAN_MU_G16_09:
        for thu_muc, _, tep in os.walk(os.path.join(goc, g)):
            if "node_modules" in thu_muc.split(os.sep):
                continue
            for t in tep:
                if t.endswith(DUOI_TEP_BAN_MU_G16_09):
                    p = os.path.join(thu_muc, t)
                    with open(p, "rb") as f:
                        bam = hashlib.sha256(f.read()).hexdigest()
                    ra.append((os.path.relpath(p, goc).replace(os.sep, "/"), bam))
    return hashlib.sha256("\n".join("%s %s" % x for x in sorted(ra)).encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TỰ KIỂM — mọi khẳng định dưới đây chạy trên CÂY THẬT hoặc CÂY GIT TẠM, không đọc mã để đoán
# ══════════════════════════════════════════════════════════════════════════════════════════════
class A_Vung(unittest.TestCase):

    def test_a1_vung_tu_do_va_khong_lap_lai_ten_tep(self):
        """Vùng phải TỰ DÒ: quy tắc chỉ nói về THƯ MỤC, không nêu tên một tệp nào."""
        vung = vung_thu_tai_lieu()
        self.assertIn("app/thu/", vung)
        self.assertIn("docs/", vung)
        for v in vung:
            self.assertTrue(v.endswith("/"), f"vùng phải là thư mục: {v!r}")
            self.assertTrue(_la_ten_vung(v), f"vùng {v!r} không theo quy tắc tên")
        # ĐỐI CHỨNG ÂM: thư mục SẢN PHẨM không được lọt vào vùng.
        for x in ("app/", "admin/", "pages/", "gateway/", "mock/", "trien_khai/", "assets/"):
            self.assertNotIn(x, vung, f"thư mục SẢN PHẨM {x!r} bị coi là vùng thử ⇒ bỏ qua hết")
        print(f"\n  [A1] vùng thử/tài liệu TỰ DÒ: {vung}")

    def test_a2_chung_minh_vung_va_co_rang(self):
        """Vùng phải được CHỨNG MINH vô hại, và bộ chứng minh phải CÓ RĂNG."""
        dat, vi = _co_rang_chung_minh_vung()
        self.assertTrue(dat, f"bộ chứng minh vùng MÙ ⇒ '0 vi phạm' không chứng minh gì: {vi}")
        vi = chung_minh_vung()
        self.assertEqual(vi, [], f"vùng thử/tài liệu đã chạm sản phẩm:\n  - " + "\n  - ".join(vi))
        print("  [A2] chứng minh (A1) import + (A2) thư mục tĩnh: 0 vi phạm · bộ dò CÓ RĂNG")

    def test_a3_mau_vung_khop_tep_trong_vung_va_khong_khop_tep_san_pham(self):
        mau = mau_vung_chuan()
        for x in ("app/thu/thu_qa_g17.py", "docs/QA_G20.md", "thu_giao_dien/06_ban_phim.spec.js",
                  "gateway/thu/thu_gia.py"):
            self.assertTrue(any(_khop(x, m) for m in mau), f"tệp trong vùng {x!r} KHÔNG khớp mẫu")
        for x in ("app/webhook.py", "app/server.py", "mock/a.json", "gateway/b.py",
                  "playwright.config.js", "app/thu_la.py", "gateway/khac/thu_x.py"):
            self.assertFalse(any(_khop(x, m) for m in mau),
                             f"tệp SẢN PHẨM {x!r} khớp mẫu vùng ⇒ bỏ qua hết")
        print(f"  [A3] mẫu vùng: {mau}")


class B_Chot(unittest.TestCase):

    def test_b1_phan_loai_la_ham_thuan_va_khong_bo_qua_het(self):
        """ĐỐI CHỨNG ÂM cấp HÀM: tệp sản phẩm bẩn KHÔNG BAO GIỜ được tha, kể cả đường bịa."""
        mau = ("app/thu/**", "docs/**")
        gia = [" M app/webhook.py", " M app/server.py", "?? app/moi.py", " D app/cau_hinh.py",
               "R  app/gioi_han.py -> thu_giao_dien/gioi_han.py", "?? mock/tep_moi.json",
               " M docs/QA_G17.md", "?? app/thu/thu_la.py", "?? docs/la.md"]
        kq = phan_loai(gia, mau)
        self.assertEqual(kq["do"], gia[:6], "bộ lọc NUỐT tệp sản phẩm ⇒ chốt mất răng")
        self.assertEqual(kq["cho_phep"], gia[6:], "bộ lọc chặn tệp của wave ⇒ N-G19-03 tái diễn")
        # tệp BỊA trong vùng vẫn được tha ⇒ miễn trừ theo QUY TẮC, không theo danh sách tên
        self.assertEqual(phan_loai(["?? docs/khong_ai_biet_ten_nay.md"], mau)["do"], [])
        print("  [B1] hàm thuần: 6/9 dòng sản phẩm ĐỎ · 3/3 dòng trong vùng được tha · "
              "tên bịa trong vùng vẫn tha (theo quy tắc)")

    def test_b2_doi_chung_am_tren_cay_that_tep_san_pham_lam_chot_DO(self):
        """ĐỐI CHỨNG ÂM BẮT BUỘC trên CÂY THẬT: tạo tệp SẢN PHẨM ⇒ chốt ĐỎ; xoá ⇒ XANH LẠI."""
        truoc = chot_cay_sach()
        self.assertEqual(truoc, [], f"cây đã bẩn TRƯỚC phép đo ⇒ phép đo vô nghĩa: {truoc}")
        for duong in ("app/_ag05_g21_tam_san_pham.py", "mock/_ag05_g21_tam.json",
                      "gateway/_ag05_g21_tam.py"):
            p = os.path.join(GOC_CAY, duong)
            self.assertFalse(os.path.exists(p), f"đường tạm đã tồn tại: {duong}")
            try:
                with open(p, "w", encoding="utf-8") as f:
                    f.write("# TỆP TẠM CỦA ĐỐI CHỨNG ÂM (AG-05 G21) — tự xoá\n")
                ban = chot_cay_sach()
                self.assertEqual(len(ban), 1, f"chốt MÙ với tệp sản phẩm mới {duong}: {ban}")
                self.assertIn(duong, ban[0])
            finally:
                if os.path.exists(p):
                    os.remove(p)
            self.assertEqual(chot_cay_sach(), [],
                             f"cây KHÔNG sạch lại sau khi xoá {duong} ⇒ cổng đỏ vĩnh viễn")
        # ĐỐI CHỨNG DƯƠNG: tệp MỚI trong VÙNG THỬ không được làm chốt đỏ (đúng N-G19-03).
        p = os.path.join(GOC_CAY, "app", "thu", "thu_ag05_g21_tam_trong_vung.py")
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# làn KHÁC giao tệp mới trong vùng thử — chốt PHẢI vẫn xanh\n")
            self.assertEqual(chot_cay_sach(), [],
                             "tệp mới của làn khác trong vùng thử làm chốt ĐỎ ⇒ N-G19-03 tái diễn")
        finally:
            if os.path.exists(p):
                os.remove(p)
        print("  [B2] cây thật: 3/3 tệp SẢN PHẨM mới ⇒ ĐỎ · xoá ⇒ xanh lại · "
              "tệp mới TRONG VÙNG ⇒ vẫn xanh")

    def test_b3_tu_tim_tep_moi_khong_can_danh_sach(self):
        """`tim_tep_moi` phải THẤY tệp mới mà không ai khai tên nó."""
        ten = "app/thu/_ag05_g21_tu_tim.py"
        p = os.path.join(GOC_CAY, ten)
        self.assertFalse(os.path.exists(p))
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# tệp chưa ai khai tên\n")
            self.assertIn(ten, tim_tep_moi(), "bộ tự tìm KHÔNG thấy tệp mới ⇒ phải liệt kê cứng")
        finally:
            if os.path.exists(p):
                os.remove(p)
        self.assertNotIn(ten, tim_tep_moi())
        print("  [B3] tự tìm tệp mới: thấy tệp chưa ai khai tên, và thôi thấy sau khi xoá")


class D_VanTay(unittest.TestCase):

    def test_d1_van_tay_git_phu_moi_tep_theo_doi(self):
        vt = van_tay()
        self.assertRegex(vt["head"], r"^[0-9a-f]{40}$", f"HEAD không đọc được: {vt['head']!r}")
        self.assertIn(vt["che_do"], ("GIT", "THU_MUC"))
        self.assertEqual(vt["sach"], not vt["diff"] and not vt["status"])
        self.assertEqual(vt["che_do"], "GIT" if vt["sach"] else "THU_MUC")
        self.assertGreater(vt["thu_muc"]["so_theo_doi"], 100,
                           "vân tay thư mục chỉ thấy vài tệp ⇒ nó không phủ cây")
        print(f"  [D1] vân tay chế độ {vt['che_do']} · HEAD={vt['head'][:12]} · "
              f"diff HEAD={len(vt['diff'])} đường · status -uall={len(vt['status'])} dòng")
        print(f"       thư mục: {vt['thu_muc']['so_theo_doi']} tệp theo dõi "
              f"(nội dung={vt['thu_muc']['theo_doi'][:16]}) · "
              f"{vt['thu_muc']['so_chua_theo_doi']} tệp mới "
              f"(nội dung={vt['thu_muc']['chua_theo_doi'][:16]})")

    def test_d2_van_tay_bat_duoc_thay_doi_trong_docs_va_md(self):
        """ĐỐI CHỨNG ÂM của `G16-09`: sửa MỘT tệp `.md` trong `docs/` rồi đo lại.

        Bốn khẳng định, và khẳng định thứ tư mới là khẳng định đáng giá:
          1. vân tay CHÍNH (Git) thấy thay đổi (`git diff HEAD` +1 đường);
          2. vân tay THƯ MỤC (dự phòng, băm nội dung) cũng thấy;
          3. vân tay theo TÊN cũng thấy;
          4. bản MÙ cũ (`find` bốn thư mục, bốn đuôi tệp) **KHÔNG** thấy — đúng cái lỗi `G16-09`.
        Tệp được khôi phục NGUYÊN BYTE trong `finally`, và việc khôi phục được KIỂM LẠI bằng git.
        """
        duong = "docs/SHARED_CONTRACTS.md"
        p = os.path.join(GOC_CAY, duong)
        self.assertTrue(os.path.exists(p), f"thiếu {duong} ⇒ phép đo không chạy được")
        with open(p, "rb") as f:
            goc_bytes = f.read()

        def _khoi_phuc():
            with open(p, "wb") as f:
                f.write(goc_bytes)
        atexit.register(_khoi_phuc)

        truoc = van_tay()
        truoc_mu = van_tay_mu_g16_09()
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n<!-- ĐỐI CHỨNG ÂM AG-05 G21 (tự khôi phục) -->\n")
            sau = van_tay()
            sau_mu = van_tay_mu_g16_09()
            self.assertIn(duong, sau["diff"],
                          "vân tay CHÍNH (Git) MÙ với thay đổi trong `docs/` — G16-09 tái diễn")
            self.assertNotEqual(sau["thu_muc"]["theo_doi"], truoc["thu_muc"]["theo_doi"],
                                "vân tay THƯ MỤC mù với thay đổi NỘI DUNG trong `docs/`")
            self.assertNotEqual(sau["theo_ten"], truoc["theo_ten"],
                                "vân tay theo TÊN mù với thay đổi trong `docs/`")
            self.assertEqual(sau_mu, truoc_mu,
                             "bản MÙ cũ LẠI thấy `docs/*.md` ⇒ nó không còn mù như mô tả")
            self.assertFalse(sau["sach"])
        finally:
            _khoi_phuc()
            atexit.unregister(_khoi_phuc)
        kq = _git("diff", "--exit-code", "--", duong)
        self.assertEqual(kq.returncode, 0,
                         f"KHÔI PHỤC THẤT BẠI cho {duong}: {kq.stdout[-400:]}")
        lai = van_tay()
        self.assertEqual((lai["diff"], lai["status"], lai["theo_ten"], lai["thu_muc"]["theo_doi"]),
                         (truoc["diff"], truoc["status"], truoc["theo_ten"],
                          truoc["thu_muc"]["theo_doi"]),
                         "vân tay SAU khôi phục KHÁC vân tay TRƯỚC ⇒ phép đo để lại dấu vết")
        print(f"  [D2] sửa `{duong}`: Git thấy (diff HEAD +1) · THƯ MỤC thấy (nội dung đổi) · "
              "theo TÊN thấy · bản MÙ `G16-09` KHÔNG đổi (đúng lỗi cũ) · khôi phục, git diff = 0")


    def test_d3_van_tay_thu_muc_bat_duoc_sua_noi_dung_ma_van_tay_theo_ten_MU(self):
        """KHOẢNG CÁCH THẬT giữa "Git là CHÍNH" và "thư mục là DỰ PHÒNG".

        Khi cây ĐÃ BẨN (nhiều làn cùng ghi) thì `git status` chỉ nói **TÊN** tệp: `?? X` trước và
        `?? X` sau — sửa nội dung `X` mà vân tay theo TÊN **đứng yên**. Bản dự phòng băm **NỘI DUNG**
        nên vẫn thấy. Không có ca này thì "dự phòng" chỉ là bản sao yếu hơn của "chính".
        """
        duong = "app/thu/_ag05_g21_bam_noi_dung.py"
        p = os.path.join(GOC_CAY, duong)
        self.assertFalse(os.path.exists(p), f"đường tạm đã tồn tại: {duong}")
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# NOI DUNG A\n")
            truoc = van_tay()
            self.assertIn(duong, " ".join(truoc["status"]), "tệp tạm không xuất hiện trong status")
            self.assertNotIn(duong, truoc["diff"], "tệp chưa theo dõi lại nằm trong `diff HEAD`")
            with open(p, "w", encoding="utf-8") as f:      # CÙNG tên, KHÁC nội dung
                f.write("# NOI DUNG B\n")
            sau = van_tay()
            self.assertEqual(sau["theo_ten"], truoc["theo_ten"],
                             "vân tay theo TÊN lại thấy đổi nội dung ⇒ ca này không đo được gì")
            self.assertEqual(sau["diff"], truoc["diff"])
            self.assertNotEqual(sau["thu_muc"]["chua_theo_doi"], truoc["thu_muc"]["chua_theo_doi"],
                                "vân tay THƯ MỤC MÙ với đổi NỘI DUNG trên tệp chưa theo dõi")
        finally:
            if os.path.exists(p):
                os.remove(p)
        lai = van_tay()
        print("  [D3] sửa nội dung tệp CHƯA THEO DÕI (tên không đổi): vân tay theo TÊN đứng yên · "
              "vân tay THƯ MỤC đổi · xoá tệp ⇒ về nguyên trạng")


class E_MoiTruongGit(unittest.TestCase):
    def test_e1_di_dang_thi_chuan_hoa_kem_canh_bao(self):
        """`N-G18-00`: dị dạng ⇒ CHUẨN HOÁ, và **PHẢI** có cảnh báo (không gỡ trong im lặng)."""
        gia = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_COUNT": "2",
               "GIT_CONFIG_VALUE_0": "false", "GIT_CONFIG_VALUE_1": "false"}
        ban = soi_gia_dinh_git(gia)
        self.assertTrue(ban["di_dang"], "bộ soi KHÔNG thấy gia đình dị dạng ⇒ nó mù")
        self.assertEqual(ban["so_khoa"], 0)
        self.assertEqual(ban["so_gia_tri"], 2)
        e = env_git(gia)
        self.assertNotIn("GIT_CONFIG_COUNT", e, "chưa gỡ biến ⇒ MỌI lệnh git sẽ thoát 128")
        self.assertFalse([k for k in e if k.startswith(TEN_GIA_DINH)])
        print(f"  [E1] dị dạng nhận ra: {ban['ly_do'][:72]}… · đã gỡ {len(ban['go_bo'])} biến")

    def test_e2_moi_truong_nguyen_ban_hong_con_da_chuan_hoa_chay_duoc(self):
        """ĐO TRỰC TIẾP: trên CÙNG một cây, môi trường nguyên văn hỏng, môi trường đã gỡ chạy được."""
        nguyen_van = dict(os.environ)
        tho = subprocess.run(["git", "-C", GOC_CAY, "rev-parse", "HEAD"], capture_output=True,
                             text=True, env=nguyen_van)
        da_go = _git("rev-parse", "HEAD")
        con_di_dang = soi_gia_dinh_git(nguyen_van)["di_dang"]
        print(f"  [E2] môi trường nguyên văn: mã thoát {tho.returncode} "
              f"({(tho.stderr or '').strip().splitlines()[-1] if tho.returncode else 'OK'}) · "
              f"đã chuẩn hoá: mã thoát {da_go.returncode} · dị dạng={con_di_dang}")
        if con_di_dang:
            self.assertNotEqual(tho.returncode, 0,
                                "môi trường dị dạng mà git nguyên văn VẪN chạy ⇒ mô tả N-G18-00 sai")
        self.assertEqual(da_go.returncode, 0,
                         f"git ĐÃ chuẩn hoá vẫn hỏng ⇒ lỗi THẬT: {(da_go.stderr or '').strip()}")

    def test_e3_khong_nuot_loi_that(self):
        """LUẬT (c): sau chuẩn hoá, lỗi THẬT vẫn phải NỔI LÊN, kèm mã thoát + stderr nguyên văn.

        Ba phép đo: (1) git ngoài cây git ⇒ hỏng; (2) rev không tồn tại ⇒ hỏng; (3) `_git_hoac_chet`
        NÉM lỗi chứ không trả rỗng. Không có ca này thì "tự chuẩn hoá" có thể đang che một cây hỏng.
        """
        tam = tempfile.mkdtemp(prefix="veh-g21-khong-repo-")
        try:
            r = _git("rev-parse", "HEAD", goc=tam)
            self.assertNotEqual(r.returncode, 0, "git ngoài cây git LẠI thành công ⇒ bộ đo hỏng")
            self.assertTrue((r.stderr or "").strip(), "lỗi thật nhưng KHÔNG có stderr để đối chiếu")
            with self.assertRaises(RuntimeError):
                _git_hoac_chet("rev-parse", "HEAD", goc=tam)
            r2 = _git("rev-parse", "khong-co-rev-nay-dau-1234567")
            self.assertNotEqual(r2.returncode, 0, "rev không tồn tại LẠI thành công ⇒ nuốt lỗi thật")
            print(f"  [E3] lỗi THẬT vẫn nổi lên: ngoài cây git mã thoát {r.returncode} · "
                  f"rev lạ mã thoát {r2.returncode} · `_git_hoac_chet` NÉM RuntimeError")
        finally:
            shutil.rmtree(tam, ignore_errors=True)

    def test_e4_moi_truong_hop_le_thi_KHONG_duoc_go(self):
        """LUẬT (b): `COUNT=1, KEY_0, VALUE_0` là cấu hình CÓ THẬT — gỡ nó là nuốt một lỗi thật."""
        gia = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_COUNT": "1",
               "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "ag05"}
        ban = soi_gia_dinh_git(gia)
        self.assertFalse(ban["di_dang"], f"môi trường HỢP LỆ bị coi là dị dạng: {ban}")
        e = env_git(gia)
        self.assertEqual(e.get("GIT_CONFIG_KEY_0"), "user.name",
                         "môi trường hợp lệ bị GỠ ⇒ nuốt một cấu hình thật")
        self.assertEqual(e.get("GIT_CONFIG_VALUE_0"), "ag05")
        self.assertEqual(e.get("GIT_CONFIG_COUNT"), "1")
        print("  [E4] môi trường HỢP LỆ: giữ nguyên 3/3 biến (không gỡ bừa)")


def _in_chot():
    ban = chot_cay_sach()
    vung = vung_thu_tai_lieu()
    tep_moi = tim_tep_moi()
    print(f"VÙNG THỬ/TÀI LIỆU (tự dò): {vung}")
    print(f"TỆP MỚI (tự tìm, {len(tep_moi)}): {', '.join(tep_moi) if tep_moi else '—'}")
    if ban:
        print(f"CHỐT ĐỎ — {len(ban)} thay đổi NGOÀI vùng:")
        for d in ban:
            print("  " + d)
        return 1
    print("CHỐT XANH — 0 thay đổi ngoài vùng thử/tài liệu")
    return 0


def _in_van_tay():
    vt = van_tay()
    print(json.dumps({"head": vt["head"], "che_do": vt["che_do"], "sach": vt["sach"],
                      "thu_muc": vt["thu_muc"], "theo_ten": vt["theo_ten"],
                      "so_duong_diff": len(vt["diff"]), "so_dong_status": len(vt["status"])},
                     ensure_ascii=False))
    if not vt["sach"]:
        print("BẨN (git status --porcelain -uall):")
        for d in vt["status"]:
            print("  " + d)
    return 0


def _van_tay_ghi(duong):
    """Ghi vân tay TRƯỚC lượt chạy ra một tệp JSON (dùng cho `chay_tat_ca.sh`)."""
    vt = van_tay()
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(vt, f, ensure_ascii=False)
    print("VÂN TAY TRƯỚC: HEAD=%s · chế độ=%s · diff HEAD=%d đường · status -uall=%d dòng"
          % (vt["head"][:12], vt["che_do"], len(vt["diff"]), len(vt["status"])))
    print("  Git (CHÍNH): `rev-parse HEAD` + `git diff HEAD` rỗng + `status --porcelain -uall` rỗng")
    print("  Thư mục (DỰ PHÒNG, băm nội dung): %d tệp theo dõi = %s · %d tệp mới = %s"
          % (vt["thu_muc"]["so_theo_doi"], vt["thu_muc"]["theo_doi"][:16],
             vt["thu_muc"]["so_chua_theo_doi"], vt["thu_muc"]["chua_theo_doi"][:16]))
    return 0


MA_VAN_TAY = {0: "KHÔNG ĐỔI", 1: "HEAD ĐỔI", 2: "NỘI DUNG TỆP ĐÃ THEO DÕI ĐỔI",
              3: "CHỈ TỆP CHƯA THEO DÕI ĐỔI", 4: "KHÔNG ĐO ĐƯỢC"}


def _van_tay_so(duong):
    """So vân tay SAU lượt chạy với bản ghi TRƯỚC. Mã thoát NÓI RÕ cái gì đã đổi.

    0 = không đổi · 1 = HEAD đổi · 2 = NỘI DUNG tệp ĐÃ THEO DÕI đổi (kể cả `docs/*.md` — `G16-09`) ·
    3 = chỉ tập tệp CHƯA theo dõi đổi (một làn giao tệp giữa lượt chạy) · 4 = không đo được.
    """
    if not duong or not os.path.exists(duong):
        print("VÂN TAY SAU: KHÔNG có bản ghi TRƯỚC ⇒ không ghim được số đo vào cây nào")
        return 4
    with open(duong, encoding="utf-8") as f:
        truoc = json.load(f)
    try:
        sau = van_tay()
    except RuntimeError as e:
        print("VÂN TAY SAU: KHÔNG đo được: %s" % e)
        return 4
    print("VÂN TAY SAU:   HEAD=%s · chế độ=%s · diff HEAD=%d đường · status -uall=%d dòng"
          % (sau["head"][:12], sau["che_do"], len(sau["diff"]), len(sau["status"])))
    print("  Thư mục (DỰ PHÒNG, băm nội dung): %d tệp theo dõi = %s · %d tệp mới = %s"
          % (sau["thu_muc"]["so_theo_doi"], sau["thu_muc"]["theo_doi"][:16],
             sau["thu_muc"]["so_chua_theo_doi"], sau["thu_muc"]["chua_theo_doi"][:16]))
    if sau["head"] != truoc["head"]:
        print("  ✗ HEAD ĐỔI giữa lượt chạy: %s → %s ⇒ các con số thuộc HAI mốc mã khác nhau"
              % (truoc["head"][:12], sau["head"][:12]))
        return 1
    if sau["thu_muc"]["theo_doi"] != truoc["thu_muc"]["theo_doi"] or sau["diff"] != truoc["diff"]:
        print("  ✗ NỘI DUNG tệp ĐÃ THEO DÕI ĐỔI giữa lượt chạy (kể cả `docs/*.md` — `G16-09`): %s"
              % ", ".join(sorted(set(sau["diff"]) ^ set(truoc["diff"]))) or "cùng tên, khác nội dung")
        return 2
    if sau["thu_muc"]["chua_theo_doi"] != truoc["thu_muc"]["chua_theo_doi"]:
        doi = sorted(set(sau["status"]) ^ set(truoc["status"]))
        if doi:
            print("  ⚠ tập TỆP CHƯA THEO DÕI ĐỔI giữa lượt chạy (một làn giao tệp?) — "
                  "số bộ/ca đã chạy KHÔNG tái lập được nguyên vẹn:")
            for d in doi:
                print("      " + d)
        else:
            print("  ⚠ CÙNG tập tệp CHƯA THEO DÕI, nhưng NỘI DUNG đổi giữa lượt chạy "
                  "(ai đó vừa ghi vào tệp mới) — số bộ/ca đã chạy KHÔNG tái lập nguyên vẹn:")
            for d in sorted(truoc["status"]):
                print("      " + d)
        return 3
    print("  ✓ vân tay KHÔNG ĐỔI (trước = sau) — con số ghim được vào ĐÚNG cây này")
    return 0


if __name__ == "__main__":
    if "--chot" in sys.argv:
        sys.exit(_in_chot())
    if "--van-tay" in sys.argv:
        sys.exit(_in_van_tay())
    if "--van-tay-ghi" in sys.argv:
        sys.exit(_van_tay_ghi(sys.argv[sys.argv.index("--van-tay-ghi") + 1]))
    if "--van-tay-so" in sys.argv:
        sys.exit(_van_tay_so(sys.argv[sys.argv.index("--van-tay-so") + 1]))
    unittest.main(verbosity=2)
