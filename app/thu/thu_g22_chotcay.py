#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — AG-05: ĐO **CẢ N BẢN SAO** CỦA CHỐT "CÂY SẠCH" — TỰ DÒ, KHÔNG LIỆT KÊ TÊN.

VÌ SAO CÓ TỆP NÀY
-----------------
`N-G18-03`/`N-G19-03` — *chốt "cây sạch" miễn trừ bằng **DANH SÁCH TÊN CỨNG*** — đã tái diễn
**BỐN** lần trên bốn tệp khác nhau. G21 vá được hai bản đầu và **ĐẾM SAI**: báo cáo ghi
"0/2 → 2/2" trong khi trên cây còn hai bản nữa — một bản **ĐỎ** (`thu_g20_baomat.py::A_Nen`, đủ để
`chay_tat_ca.sh` exit 1 trên MỌI cây G21 có tệp mới) và một bản **DORMANT**
(`thu_qa_g19.py`, `setUpModule` bỏ qua cả bộ nên cổng cây sạch của nó chạy 0 ca).

Con số "2" ấy không phải do lười đo: nó do **CÁCH ĐẾM** — một danh sách tên viết trong báo cáo, y
hệt căn bệnh mà chốt này sinh ra để chữa. QA và Giám sát đều yêu cầu C1 phải đo **CẢ 3** bản sao.
Tệp này đếm bằng **QUY TẮC, trên cây**: bản sao thứ năm (nếu ai viết) tự vào bảng, không ai phải
nhớ thêm một dòng — và nếu một bản sao biến mất thì bảng ngắn lại, thấy được.

BỐN PHÉP ĐO CHO MỖI BẢN SAO (không phép nào suy ra từ phép nào)
--------------------------------------------------------------
  1. **XANH** — chạy CHÍNH CA CỔNG trên **BẢN SAO của HEAD** trong thư mục tạm, bản sao ấy có
     MỘT tệp mới của làn KHÁC ⇒ mã thoát 0. Cây thật KHÔNG bị tạo/xoá tệp nào và được canh
     `git status` trước/sau. Kèm phép canh chống RỖNG: bản sao PHẢI thật sự có thay đổi NGOÀI làn
     của từng bản sao — nếu cây sạch trơn thì "xanh" không chứng minh được gì (đó đúng là cách G21
     đếm ra "2/2"). (R27: bản cũ đòi CÂY THẬT phải bẩn; trên clone sạch D2 ĐỎ vì chống rỗng.)
  2. **RĂNG** — dựng một tệp **SẢN PHẨM** tạm ⇒ CÙNG ca ấy PHẢI **ĐỎ**; xoá đi ⇒ XANH LẠI.
     Không có tầng này thì "xanh" có thể chỉ là một cổng đã bị nới thành "bỏ qua hết".
  3. **QUY TẮC** — đọc NGUỒN của bản sao: miễn trừ phải đến từ **LUẬT VÙNG DÙNG CHUNG**
     (`thu_g21_chotcay`), không được là một danh sách tên riêng. Phép đo này là **HÀM THUẦN** trên
     nguồn, nên nó tự kiểm được HAI CHIỀU — và nó được kiểm trên **NGUỒN THẬT TRONG LỊCH SỬ GIT**
     (bản trước khi vá, đọc bằng `git show`): bản cũ PHẢI bị bắt, bản mới PHẢI qua. R27: chọn bản
     LỊCH SỬ **GẦN NHẤT MÀ BỘ DÒ BẮT ĐƯỢC**, không mặc định "bản khác gần nhất là bản trước khi
     vá" (trên nền này bản khác gần nhất đã ĐẠT quy tắc).
  4. **CHỨNG MINH VÙNG** — vùng được tha phải chứng minh được là không chạy trong sản phẩm
     (`thu_g21_chotcay.chung_minh_vung`); chứng minh hỏng ⇒ chốt TỪ CHỐI tha (không tha mù).

TỰ DÒ LÀ GÌ, VÀ KHÔNG LÀ GÌ — nói thẳng để không ai đọc quá lời
--------------------------------------------------------------
`bo_ung_vien()` KHÔNG biết tên tệp nào. Nó quét **mọi** `thu_*.py` trong VÙNG THỬ/TÀI LIỆU (vùng
ấy cũng TỰ DÒ, không liệt kê) rồi giữ những mô-đun có **lớp `A_Nen`** với **ca có tên chứa
`cay_sach`**. Đó là một QUY TẮC ĐẶT TÊN, không phải danh sách tệp — nhưng nó VẪN là một quy tắc,
nên nó có ca tự kiểm (`D5`: một bản sao GIẢ trong cây tạm phải được TÌM RA; `D4`: một nguồn theo
danh sách cứng phải bị BẮT). Một bộ dò không có đối chứng thì "0 vi phạm" chỉ là một bộ dò mù.

CHẠY
----
    python3 app/thu/thu_g22_chotcay.py            # bộ tự kiểm (unittest)
    python3 app/thu/thu_g22_chotcay.py --bang     # in BẢNG N bản sao + 4 cột đo; exit 1 nếu có bản hỏng
"""
import ast
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True          # không để lại __pycache__ trong cây ĐANG ĐO

GOC_TEP = os.path.abspath(__file__)
GOC_THU = os.path.dirname(GOC_TEP)
GOC_APP = os.path.dirname(GOC_THU)
GOC_CAY = os.path.dirname(GOC_APP)

if GOC_THU not in sys.path:
    sys.path.append(GOC_THU)
import thu_g21_chotcay as chotcay                                          # noqa: E402

# ── QUY TẮC ĐẶT TÊN (không phải danh sách tệp) ────────────────────────────────────────────────
TEN_NHOM_NEN = "A_Nen"          # lớp "nền đo" của mọi bộ AG-01/AG-05
TEN_CA_CONG = "cay_sach"        # ca cổng nói TÊN thứ nó đo
MAU_TEP_THU = ("thu_", ".py")   # mô-đun thử trong VÙNG THỬ/TÀI LIỆU

# ── TỆP TẠM CỦA ĐỐI CHỨNG ÂM — bộ thử TỰ TẠO RỒI TỰ XOÁ (không sửa tệp sản phẩm nào) ──────────
TEP_SAN_PHAM_TAM = "app/_ag05_g22_tam_san_pham.py"
TEP_TRONG_VUNG_TAM = "docs/_ag05_g22_tam_trong_vung.md"

DOI_CHUNG = {}


def _dc(nhom, loai):
    o = DOI_CHUNG.setdefault(nhom, {"duong": 0, "am": 0})
    o[loai] += 1


def _dc_duong(nhom):
    _dc(nhom, "duong")


def _dc_am(nhom):
    _dc(nhom, "am")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. TỰ DÒ BẢN SAO — QUY TẮC TRÊN CÂY, KHÔNG DANH SÁCH TÊN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def thu_muc_vung(goc=None):
    """Các THƯ MỤC thuộc VÙNG THỬ/TÀI LIỆU của cây (luật vùng: MỘT chỗ ở `thu_g21_chotcay`)."""
    return [v.rstrip("/") for v in chotcay.vung_thu_tai_lieu(goc=goc or GOC_CAY)]


def ung_vien(goc=None):
    """MỌI mô-đun thử trong vùng — quy tắc `thu_*.py`, KHÔNG tệp nào được viết tên ở đây."""
    goc = goc or GOC_CAY
    ra = []
    for d in thu_muc_vung(goc):
        p = os.path.join(goc, d)
        if not os.path.isdir(p):
            continue
        for ten in sorted(os.listdir(p)):
            if ten.startswith(MAU_TEP_THU[0]) and ten.endswith(MAU_TEP_THU[1]):
                ra.append(d + "/" + ten)
    return ra


def ca_cong_cay_sach(nguon):
    """Tên các ca CỔNG "CÂY SẠCH" trong một nguồn: ca trong lớp `A_Nen`, tên chứa `cay_sach`."""
    ra = []
    for n in ast.parse(nguon).body:
        if isinstance(n, ast.ClassDef) and n.name == TEN_NHOM_NEN:
            for m in n.body:
                if (isinstance(m, ast.FunctionDef) and m.name.startswith("test")
                        and TEN_CA_CONG in m.name):
                    ra.append(n.name + "." + m.name)
    return sorted(ra)


def bo_ung_vien(goc=None):
    """CÁC BẢN SAO của chốt "cây sạch" — TỰ DÒ. Trả `[{'duong', 'ca'}]`, thứ tự theo đường."""
    goc = goc or GOC_CAY
    ra = []
    for d in ung_vien(goc):
        try:
            with open(os.path.join(goc, d), encoding="utf-8") as f:
                nguon = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        try:
            ca = ca_cong_cay_sach(nguon)
        except SyntaxError:
            continue
        if ca:
            ra.append({"duong": d, "ca": ca})
    return ra


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. PHÉP ĐO "QUY TẮC" — HÀM THUẦN TRÊN NGUỒN (để tự kiểm được hai chiều)
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# VÌ SAO CẦN MỘT PHÉP ĐO TĨNH, khi đã có phép đo HÀNH VI (XANH + RĂNG):
#   · phép đo hành vi nói "cổng này CƯ XỬ đúng trên cây HÔM NAY";
#   · phép đo tĩnh nói "cổng này KHÔNG CÒN CƠ CHẾ gây lỗi" — và nó chạy được trên NGUỒN CŨ đọc từ
#     git, nên nó cho một bảng TRƯỚC/SAU thật chứ không phải một lời khẳng định.
# Hai phép đo độc lập: một cái có thể xanh vì may (cây chưa có tệp nào lạ), cái kia thì không.

def _goi_trong(fn):
    """Tên hàm/mô-đun được GỌI trong một hàm (AST) — dùng để dựng chuỗi gọi NỘI BỘ mô-đun."""
    ra = set()
    for nut in ast.walk(fn):
        if isinstance(nut, ast.Call):
            f = nut.func
            if isinstance(f, ast.Name):
                ra.add(f.id)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                ra.add(f.value.id)
    return ra


def _tham_chieu(fn):
    """Tên biến được ĐỌC trong THÂN một hàm (KHÔNG tính tham số mặc định của chính nó).

    Vì sao trừ tham số mặc định: `def _loc(dong, ngoai=TEP_CUA_WAVE_G20)` vẫn giữ một danh sách
    tên cứng "trên giấy", nhưng nếu MỌI chỗ gọi trong chuỗi của chốt đều truyền đối số thứ hai
    thì danh sách ấy KHÔNG được dùng làm miễn trừ. Phán "có tội" ở đây là phán oan — và một bộ
    dò phán oan sẽ bị học cách bỏ qua. Việc "có chỗ nào THẬT SỰ dựa vào mặc định không" do
    `_mac_dinh_duoc_dung()` đo riêng.
    """
    ra = set()
    for nut in fn.body:
        for n in ast.walk(nut):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                ra.add(n.id)
    return ra


def _mac_dinh_duoc_dung(cay, chuoi, tuples):
    """Các tuple TÊN CỨNG **thật sự được dùng** làm miễn trừ qua THAM SỐ MẶC ĐỊNH.

    Một mặc định chỉ "có tội" khi có chỗ gọi trong chuỗi của chốt BỎ QUA đối số ấy — khi đó chính
    danh sách tên cứng là thứ đang lọc, đúng khuôn `N-G19-03` (`_loc_cay_ban(dong)` bản cũ).
    """
    ra = set()
    for t in sorted(chuoi):
        fn = _ham(cay, t)
        if fn is None:
            continue
        tham = [a.arg for a in fn.args.args]
        mac_dinh = {}
        for ten_tham, gia in zip(tham[len(tham) - len(fn.args.defaults):], fn.args.defaults):
            if (isinstance(gia, ast.Name) and gia.id in tuples
                    and not any(_la_mau_vung(x) for x in tuples[gia.id])):
                mac_dinh[ten_tham] = gia.id
        if not mac_dinh:
            continue
        for g in sorted(chuoi):
            gfn = _ham(cay, g)
            if gfn is None:
                continue
            for nut in ast.walk(gfn):
                if not (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name)
                        and nut.func.id == t):
                    continue
                khoa = {k.arg for k in nut.keywords if k.arg}
                for i, ten_tham in enumerate(tham):
                    if ten_tham in mac_dinh and i >= len(nut.args) and ten_tham not in khoa:
                        ra.add(mac_dinh[ten_tham])
    return ra


def _tuple_literal(cay):
    """`{tên: tuple chuỗi}` cho các gán ở MỨC MÔ-ĐUN (literal thuần)."""
    ra = {}
    for n in cay.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            try:
                gia = ast.literal_eval(n.value)
            except (ValueError, SyntaxError):
                continue
            if isinstance(gia, (tuple, list)) and gia and all(isinstance(x, str) for x in gia):
                ra[n.targets[0].id] = tuple(gia)
    return ra


def _la_mau_vung(m):
    """Một mục miễn trừ có phải MẪU VÙNG không (có ký tự mẫu fnmatch)."""
    return any(c in m for c in "*?[")


def _chuoi_goi(cay, ten_bat_dau):
    """Các hàm NỘI BỘ mô-đun nằm trong CHUỖI GỌI xuất phát từ những hàm đã cho."""
    ham = {n.name: n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)}
    thay, hang = set(), [t for t in ten_bat_dau if t in ham]
    while hang:
        t = hang.pop()
        if t in thay:
            continue
        thay.add(t)
        for g in _goi_trong(ham[t]):
            if g in ham and g not in thay:
                hang.append(g)
    return thay


def kiem_quy_tac(nguon, mau_tu_do):
    """HÀM THUẦN: miễn trừ của chốt "cây sạch" trong `nguon` có theo **QUY TẮC VÙNG** không.

    Trả `{'dat': bool, 'ly_do': str, 'mau_khai': tuple, 'ten_cung': tuple, 'nguon_vung': str}`.

    HAI LUẬT, cả hai đều đo được:
      (1) **NGUỒN VÙNG**: chuỗi gọi của ca cổng phải lấy miễn trừ từ LUẬT VÙNG DÙNG CHUNG —
          hoặc (a) một tuple toàn MẪU VÙNG khai trong mô-đun và **BẰNG mẫu TỰ DÒ từ cây**, hoặc
          (b) một lời gọi `mau_vung_chuan` / `vung_thu_tai_lieu` trên mô-đun luật vùng.
          Miễn trừ "tự chế" bằng tên tệp không đạt được (a) vì nó không bằng mẫu tự dò.
      (2) **KHÔNG DANH SÁCH TÊN CỨNG**: không tuple nào TOÀN TÊN CỨNG (không ký tự mẫu) được
          chuỗi gọi của ca cổng THAM CHIẾU. Đây đúng là `N-G19-03`: một danh sách tên nằm trên
          đường đi của chốt thì mỗi wave phải sửa nó, và ai quên là cổng ĐỎ vì một tệp hợp lệ.
    """
    cay = ast.parse(nguon)
    ca = ca_cong_cay_sach(nguon)
    if not ca:
        return {"dat": False, "ly_do": "không có ca cổng nào (lớp `%s`, tên chứa `%s`)"
                                       % (TEN_NHOM_NEN, TEN_CA_CONG),
                "mau_khai": (), "ten_cung": (), "nguon_vung": ""}
    ten_ham = [c.split(".", 1)[1] for c in ca]
    chuoi = _chuoi_goi(cay, ten_ham)
    tuples = _tuple_literal(cay)

    # (1) nguồn vùng
    mau_khai, nguon_vung = (), ""
    # (1a) tuple toàn MẪU VÙNG, khai trong mô-đun, và BẰNG mẫu tự dò
    for ten, gt in tuples.items():
        if all(_la_mau_vung(x) for x in gt) and tuple(sorted(gt)) == tuple(sorted(mau_tu_do)):
            mau_khai, nguon_vung = gt, "tuple khai trong mô-đun: %s" % ten
            break
    # (1b) lời gọi luật vùng dùng chung nằm TRONG chuỗi gọi của ca cổng
    if not nguon_vung:
        for t in sorted(chuoi):
            ham = _ham(cay, t)
            if ham is None:
                continue
            for nut in ast.walk(ham):
                if (isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute)
                        and nut.func.attr in ("mau_vung_chuan", "vung_thu_tai_lieu")):
                    nguon_vung = "gọi `%s` trong `%s`" % (nut.func.attr, t)
                    break
            if nguon_vung:
                break
    if not nguon_vung and not mau_khai:
        return {"dat": False, "ly_do": "chuỗi gọi của ca cổng KHÔNG lấy miễn trừ từ luật vùng "
                                       "dùng chung, và mô-đun không khai tuple mẫu vùng nào bằng "
                                       "mẫu TỰ DÒ %s" % (mau_tu_do,),
                "mau_khai": (), "ten_cung": (), "nguon_vung": ""}

    # (2) danh sách tên cứng THẬT SỰ nằm trên đường đi của chốt — hai cách dùng, đo cả hai:
    #     (2a) thân hàm đọc thẳng tên tuple ấy;
    #     (2b) tham số mặc định của hàm lọc, mà chỗ gọi trong chuỗi BỎ QUA đối số ⇒ mặc định ấy
    #          chính là thứ đang lọc (đúng khuôn `_loc_cay_ban(dong)` của bản cũ).
    ten_cung = set()
    for t in sorted(chuoi):
        ham = _ham(cay, t)
        if ham is None:
            continue
        for ten in _tham_chieu(ham):
            gt = tuples.get(ten)
            if gt and not any(_la_mau_vung(x) for x in gt):
                ten_cung.add(ten)
    ten_cung |= _mac_dinh_duoc_dung(cay, chuoi, tuples)
    if ten_cung:
        return {"dat": False,
                "ly_do": "danh sách TÊN CỨNG nằm trên đường đi của chốt: %s"
                         % ", ".join(sorted(ten_cung)),
                "mau_khai": tuple(mau_khai), "ten_cung": tuple(sorted(ten_cung)),
                "nguon_vung": nguon_vung}
    return {"dat": True, "ly_do": "", "mau_khai": tuple(mau_khai), "ten_cung": (),
            "nguon_vung": nguon_vung}


def _ham(cay, ten):
    """Nút `FunctionDef` tên `ten` trong cây AST (không có ⇒ `None`)."""
    for n in ast.walk(cay):
        if isinstance(n, ast.FunctionDef) and n.name == ten:
            return n
    return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. PHÉP ĐO HÀNH VI — CHẠY CHÍNH CA CỔNG TRONG TIẾN TRÌNH CON
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dong_porcelain(goc=None):
    """Các dòng `git status --porcelain -uall` của cây ĐANG ĐO (môi trường git đã chuẩn hoá)."""
    r = chotcay._git("status", "--porcelain=v1", "-uall", goc=goc)
    if r.returncode != 0:
        raise RuntimeError("`git status` hỏng (mã thoát %d): %s"
                           % (r.returncode, (r.stderr or "").strip()))
    return [d for d in r.stdout.splitlines() if d.strip()]


def chay_ca(duong, ds_ca, giay=600, goc=None, tmpdir=None):
    """Chạy THẬT các ca của một bộ thử trong TIẾN TRÌNH CON. Trả (mã thoát, output, số ca, skip).

    `goc`/`tmpdir`: chạy trên BẢN SAO (R27/D2) và cô lập TMPDIR của tiến trình con — không để
    thư mục tạm của bộ thử được đo rơi vào TMPDIR dùng chung.
    """
    goc = goc or GOC_CAY
    e = chotcay.env_git(im_lang=True)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    if tmpdir:
        e["TMPDIR"] = tmpdir
        e["TMP"] = tmpdir
        e["TEMP"] = tmpdir
    r = subprocess.run([sys.executable, os.path.join(goc, duong)] + list(ds_ca),
                       capture_output=True, text=True, cwd=goc, env=e, timeout=giay)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.findall(r"Ran (\d+)", out)
    so_ca = int(m[-1]) if m else 0
    m2 = re.search(r"skipped=(\d+)", out)
    return r.returncode, out, so_ca, (int(m2.group(1)) if m2 else 0)


def _mau_ten_cung(nguon):
    """Mọi tuple TOÀN TÊN CỨNG (không ký tự mẫu) khai ở mức mô-đun — "làn của chính bộ thử"."""
    return [gt for gt in _tuple_literal(ast.parse(nguon)).values()
            if not any(_la_mau_vung(x) for x in gt)]


def thay_doi_ngoai_lan(nguon, duong, goc=None):
    """Các dòng `git status` KHÔNG thuộc "làn" của bộ thử này (tệp của chính nó + tên cứng của nó).

    Đây là phép canh CHỐNG RỖNG cho cột XANH: nếu cây không có thay đổi nào ngoài làn ấy thì
    "cổng xanh" không chứng minh được `N-G19-03` đã được chữa.
    """
    lan = [m for gt in _mau_ten_cung(nguon) for m in gt] + [duong]
    ra = []
    for d in _dong_porcelain(goc=goc):
        ds = chotcay.duong_tu_dong_porcelain(d)
        if all(any(fnmatch.fnmatch(x, m) for m in lan) for x in ds):
            continue
        ra.append(d)
    return ra


def nguon_truoc_khi_va(duong, goc=None):
    """Nguồn của `duong` ở lần sửa GẦN NHẤT mà nội dung KHÁC bản đang có. Trả `(sha, nguon)`.

    Không ghim SHA nào: lấy `git log -- <đường>` rồi so từng bản với tệp đang làm việc. Nhờ vậy
    bảng TRƯỚC/SAU dưới đây đọc được cả khi lịch sử đổi.
    """
    goc = goc or GOC_CAY
    with open(os.path.join(goc, duong), encoding="utf-8") as f:
        hien_tai = f.read()
    r = chotcay._git("log", "-n", "40", "--format=%H", "--", duong, goc=goc)
    if r.returncode != 0:
        return None, None
    for sha in [x.strip() for x in r.stdout.splitlines() if x.strip()]:
        s = chotcay._git("show", "%s:%s" % (sha, duong), goc=goc)
        if s.returncode != 0:
            continue
        if s.stdout != hien_tai:
            return sha, s.stdout
    return None, None


def nguon_cu_hong(duong, mau_tu_do, goc=None, so_ban=40):
    """Bản **LỊCH SỬ GẦN NHẤT mà `kiem_quy_tac` BẮT ĐƯỢC** của `duong`. Trả `(sha, nguon, kq)`.

    R27 — NGUYÊN NHÂN GỐC của D4: bản cũ lấy "bản khác bản đang có GẦN NHẤT" rồi ĐÒI nó hỏng.
    Trên nền `c909ebb`, bản gần nhất (`6ac4d0a8`) đã ĐẠT quy tắc, nên D4 ĐỎ dù bộ dò không mù:
    tiền đề "bản gần nhất là bản trước khi vá" SAI. Chọn đúng bản để kiểm = bỏ qua các bản đã đạt
    và lấy bản gần nhất THẬT SỰ bị quy tắc bắt; bản không có ca cổng (tệp còn quá cũ/đổi tên) cũng
    không phải "bản trước khi vá" nên bị bỏ qua. Không ghim SHA — lịch sử đổi vẫn đọc được.
    """
    goc = goc or GOC_CAY
    with open(os.path.join(goc, duong), encoding="utf-8") as f:
        hien_tai = f.read()
    r = chotcay._git("log", "-n", str(so_ban), "--format=%H", "--", duong, goc=goc)
    if r.returncode != 0:
        return None, None, None
    for sha in [x.strip() for x in r.stdout.splitlines() if x.strip()]:
        s = chotcay._git("show", "%s:%s" % (sha, duong), goc=goc)
        if s.returncode != 0 or s.stdout == hien_tai:
            continue
        if not ca_cong_cay_sach(s.stdout):
            continue                        # bản chưa có cổng: không phải "bản trước khi vá"
        kq = kiem_quy_tac(s.stdout, mau_tu_do)
        if not kq["dat"]:
            return sha, s.stdout, kq
    return None, None, None


def do_mot_ban_sao(ban, mau_tu_do=None, goc=None):
    """ĐO MỘT BẢN SAO: XANH · RĂNG · QUY TẮC (· và nguồn TRƯỚC để làm bảng đối chiếu)."""
    goc = goc or GOC_CAY
    mau_tu_do = mau_tu_do or chotcay.mau_vung_chuan(goc=goc)
    with open(os.path.join(goc, ban["duong"]), encoding="utf-8") as f:
        nguon = f.read()
    kq = {"duong": ban["duong"], "ca": ban["ca"]}
    kq["quy_tac"] = kiem_quy_tac(nguon, mau_tu_do)
    ma, out, so_ca, skip = chay_ca(ban["duong"], ban["ca"])
    kq["xanh"] = {"ma": ma, "ca": so_ca, "skip": skip, "dat": ma == 0 and so_ca > 0}
    kq["ngoai_lan"] = thay_doi_ngoai_lan(nguon, ban["duong"])
    sha, truoc, kq_truoc = nguon_cu_hong(ban["duong"], mau_tu_do, goc=goc)
    kq["truoc"] = None if truoc is None else {"sha": sha, "quy_tac": kq_truoc}
    return kq


def bang(goc=None):
    """BẢNG N bản sao × 4 cột đo. Trả `(danh_sach_ket_qua, so_ban_hong)`."""
    goc = goc or GOC_CAY
    mau_tu_do = chotcay.mau_vung_chuan(goc=goc)
    ds = bo_ung_vien(goc)
    ra = [do_mot_ban_sao(b, mau_tu_do=mau_tu_do, goc=goc) for b in ds]
    return ra, sum(0 if (r["xanh"]["dat"] and r["quy_tac"]["dat"]) else 1 for r in ra)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C2. D2 TRÊN BẢN SAO — R27: KHÔNG ĐÒI CÂY THẬT PHẢI BẨN, KHÔNG LÀM BẨN CÂY THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
# NGUYÊN NHÂN GỐC của D2 (QA_NGUYENNHAN §5): D2 chạy cổng trên CÂY THẬT và đòi cây ấy có sẵn một
# tệp mới của "làn khác" (`assertGreaterEqual(len(_dong_porcelain()), 1)`). Trên một bản clone sạch
# — đúng điều kiện "cây sạch" mà chốt cần đo — D2 ĐỎ vì phép canh chống rỗng, không phải vì sản
# phẩm. Cách chữa KHÔNG phải làm bẩn cây thật (hay tạo tệp rồi xoá trong lúc chạy): dựng **BẢN SAO**
# của HEAD trong thư mục tạm, tự tạo MỘT tệp của làn khác trong bản sao, chạy cổng ở đó, rồi xoá.
# Cây thật được chụp `git status` trước/sau và PHẢI không đổi.
LAN_KHAC_D2 = "docs/_r27_lan_khac.md"
NOI_DUNG_LAN_KHAC = "# Tệp của LÀN KHÁC (R27) — tạo trong BẢN SAO, không tạo trong cây thật\n"


def tao_ban_sao_d2(co_lan_khac=True):
    """Clone HEAD của cây ĐANG ĐO vào thư mục tạm; tuỳ chọn thêm tệp của làn khác.

    Trả dict: `goc` (thư mục tạm chứa tất cả), `cay` (bản sao), `tmp` (TMPDIR riêng cho tiến
    trình con), `head`, `head_that`, `status_truoc`, `tep_lan_khac`. Người gọi PHẢI xoá `goc`.
    """
    goc_tam = tempfile.mkdtemp(prefix="veh-g22-d2-")
    cay = os.path.join(goc_tam, "cay")
    tmp = os.path.join(goc_tam, "tmp")
    os.makedirs(tmp)
    e = chotcay.env_git()
    r = subprocess.run(["git", "clone", "-q", "--no-hardlinks", GOC_CAY, cay],
                       capture_output=True, text=True, env=e, timeout=300)
    if r.returncode != 0:
        shutil.rmtree(goc_tam, ignore_errors=True)
        raise RuntimeError("không dựng được BẢN SAO của cây (git clone thoát %d): %s"
                           % (r.returncode, (r.stderr or "").strip()))
    head = chotcay._git("rev-parse", "HEAD", goc=cay).stdout.strip()
    head_that = chotcay._git("rev-parse", "HEAD").stdout.strip()
    status_truoc = _dong_porcelain(goc=cay)
    tep = None
    if co_lan_khac:
        tep = os.path.join(cay, LAN_KHAC_D2)
        os.makedirs(os.path.dirname(tep), exist_ok=True)
        with open(tep, "w", encoding="utf-8") as f:
            f.write(NOI_DUNG_LAN_KHAC)
    return {"goc": goc_tam, "cay": cay, "tmp": tmp, "head": head, "head_that": head_that,
            "status_truoc": status_truoc, "tep_lan_khac": LAN_KHAC_D2 if co_lan_khac else None}


def do_d2_tren_cay(cay, ban_sao, tmpdir=None):
    """ĐO D2 trên cây `cay`: trả `(danh_sach_loi, bang, dong_status)`. Rỗng = ĐẠT.

    Tách khỏi `unittest` để `thu_r27_fixture.py` gọi được ĐỐI CHỨNG ÂM: cùng hàm này chạy trên
    bản sao KHÔNG có tệp của làn khác PHẢI trả lỗi "cây SẠCH TRƠN ⇒ phép đo rỗng".
    """
    loi, tds = [], []
    for b in ban_sao:
        ma, out, ca, skip = chay_ca(b["duong"], b["ca"], goc=cay, tmpdir=tmpdir)
        tds.append((b["duong"], ma, ca, skip, out))
        if ma != 0:
            loi.append("%s::%s ĐỎ trên bản sao (mã thoát %d, %d ca, %d skip):\n%s"
                       % (b["duong"], b["ca"], ma, ca, skip, out[-1200:]))
        if ca <= 0:
            loi.append("%s: chạy 0 ca (DORMANT?) ⇒ không đo được gì" % b["duong"])
    dong = _dong_porcelain(goc=cay)
    if len(dong) < 1:
        loi.append("cây SẠCH TRƠN ⇒ phép đo rỗng (không có tệp của làn khác để đo)")
    for b in ban_sao:
        with open(os.path.join(cay, b["duong"]), encoding="utf-8") as f:
            nguon = f.read()
        ngoai = thay_doi_ngoai_lan(nguon, b["duong"], goc=cay)
        if not ngoai:
            loi.append("%s: cây KHÔNG có thay đổi nào ngoài làn của nó ⇒ XANH ở trên không "
                       "chứng minh được `N-G19-03` đã được chữa" % b["duong"])
    return loi, tds, dong


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. CÁC NHÓM CA
# ══════════════════════════════════════════════════════════════════════════════════════════════
class D_BanSao(unittest.TestCase):
    """Bốn phép đo trên MỌI bản sao TỰ DÒ. Nhóm này ĐỎ thì con số "N/N bản sao" vô hiệu."""

    @classmethod
    def setUpClass(cls):
        cls.mau_tu_do = chotcay.mau_vung_chuan(goc=GOC_CAY)
        cls.ban_sao = bo_ung_vien(GOC_CAY)

    def test_d1_tu_do_ra_cac_ban_sao_va_khong_mu(self):
        """Bộ dò phải TÌM RA các bản sao — và phải TÌM RA ĐƯỢC (đối chứng dương ở `D5`)."""
        self.assertGreaterEqual(len(self.ban_sao), 3,
                                "chỉ dò ra %d bản sao — QA/Giám sát yêu cầu ĐO CẢ ba bản sao trở "
                                "lên: %s" % (len(self.ban_sao), [b["duong"] for b in self.ban_sao]))
        for b in self.ban_sao:
            self.assertTrue(b["ca"], "%s: không có ca cổng nào" % b["duong"])
        _dc_duong("tu-do-ban-sao")
        print("\n  [D1] TỰ DÒ %d bản sao của chốt cây sạch:" % len(self.ban_sao))
        for b in self.ban_sao:
            print("        · %-28s %s" % (b["duong"], ", ".join(b["ca"])))

    def test_d2_moi_ban_sao_xanh_tren_cay_co_tep_moi_cua_lan_khac(self):
        """C1: một tệp MỚI hợp lệ của làn KHÁC không được làm cổng của wave trước ĐỎ.

        R27: phép đo chạy trên **BẢN SAO của HEAD trong thư mục tạm**, không đòi cây thật phải
        bẩn và không tạo/xoá tệp nào trong cây thật. Bản sao được tự thêm đúng MỘT tệp của làn
        khác; cây thật được chụp `git status` trước/sau và phải KHÔNG đổi.

        Kèm phép canh CHỐNG RỖNG: mỗi bản sao phải thật sự thấy thay đổi NGOÀI làn của nó. Trên
        cây sạch trơn thì phép đo này xanh vô nghĩa — đúng cách G21 đếm ra "2/2".
        """
        truoc = _dong_porcelain()
        ban = tao_ban_sao_d2(co_lan_khac=True)
        try:
            self.assertEqual(ban["head"], ban["head_that"],
                             "bản sao không đúng HEAD của cây đang đo")
            self.assertEqual(ban["status_truoc"], [],
                             "bản sao HEAD phải SẠCH trước khi thêm tệp của làn khác: %r"
                             % (ban["status_truoc"],))
            dong_sau = _dong_porcelain(goc=ban["cay"])
            self.assertEqual(len(dong_sau), 1,
                             "bản sao phải có ĐÚNG MỘT tệp của làn khác: %r" % (dong_sau,))
            self.assertIn(ban["tep_lan_khac"], dong_sau[0],
                          "tệp của làn khác không xuất hiện trong `git status` bản sao")
            loi, tds, dong = do_d2_tren_cay(ban["cay"], self.ban_sao, tmpdir=ban["tmp"])
            self.assertEqual(loi, [], "D2 HỎNG trên bản sao:\n  - " + "\n  - ".join(loi))
        finally:
            shutil.rmtree(ban["goc"], ignore_errors=True)
        self.assertEqual(_dong_porcelain(), truoc,
                         "D2 đã ĐỔI cây thật — phép đo phải chạy trên bản sao")
        _dc_duong("cay-sach-c1")
        print("  [D2] C1 — %d/%d bản sao XANH trên BẢN SAO có tệp mới của làn khác:"
              % (len(self.ban_sao), len(self.ban_sao)))
        for duong, ma, ca, skip, _ in tds:
            print("        · %-28s mã thoát %d · %d ca · %d bỏ qua" % (duong, ma, ca, skip))
        print("        bản sao HEAD=%s · tệp làn khác=%s · cây thật KHÔNG đổi"
              % (ban["head"][:8], ban["tep_lan_khac"]))

    def test_d3_moi_ban_sao_con_RANG(self):
        """Tệp **SẢN PHẨM** tạm ⇒ MỌI bản sao PHẢI ĐỎ; xoá đi ⇒ XANH LẠI. Không có tầng này thì
        "xanh" có thể chỉ là một cổng đã bị nới thành "bỏ qua hết"."""
        p = os.path.join(GOC_CAY, TEP_SAN_PHAM_TAM)
        self.assertFalse(os.path.exists(p), "đường tạm đã tồn tại: %s" % TEP_SAN_PHAM_TAM)
        do = {}
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("# TỆP TẠM CỦA ĐỐI CHỨNG ÂM (AG-05 G22) — bộ thử tự xoá\n")
            for b in self.ban_sao:
                ma, out, ca, skip = chay_ca(b["duong"], b["ca"])
                do[b["duong"]] = (ma, ca, skip)
                self.assertNotEqual(ma, 0, "%s::%s VẪN XANH dù có tệp SẢN PHẨM mới ⇒ cổng MẤT RĂNG"
                                    % (b["duong"], b["ca"]))
                self.assertIn("FAIL:", out, "%s đỏ nhưng không có dòng `FAIL:` để đối chiếu"
                              % b["duong"])
        finally:
            if os.path.exists(p):
                os.remove(p)
        # ĐỐI CHỨNG DƯƠNG của chính phép đo: xoá tệp tạm ⇒ XANH LẠI (không phải "đỏ vĩnh viễn")
        for b in self.ban_sao:
            ma, out, ca, skip = chay_ca(b["duong"], b["ca"])
            self.assertEqual(ma, 0, "%s::%s vẫn ĐỎ sau khi xoá tệp tạm:\n%s"
                             % (b["duong"], b["ca"], out[-900:]))
        _dc_am("cay-sach-rang")
        _dc_duong("cay-sach-rang")
        print("  [D3] RĂNG — tệp sản phẩm tạm ⇒ %d/%d bản sao ĐỎ (%s) · xoá đi ⇒ XANH LẠI"
              % (len(do), len(self.ban_sao),
                 " · ".join("%s=%d" % (os.path.basename(k), v[0]) for k, v in do.items())))

    def test_d4_moi_ban_sao_theo_QUY_TAC_va_ban_CU_bi_bat(self):
        """QUY TẮC — và bảng TRƯỚC/SAU đọc từ **LỊCH SỬ GIT THẬT** (không phải nguồn tự bịa).

        Mỗi bản sao phải đạt `kiem_quy_tac`; một bản LỊCH SỬ THẬT của chính tệp ấy phải bị chính
        hàm đó BẮT. R27 sửa TIỀN ĐỀ: bản "khác bản đang có gần nhất" KHÔNG chắc là bản trước khi
        vá (trên nền này nó đã ĐẠT quy tắc). Chọn đúng bản = bản GẦN NHẤT mà bộ dò BẮT ĐƯỢC
        (`nguon_cu_hong`); các bản đã đạt bị bỏ qua và được in ra để thấy rõ. Nếu bản cũ cũng
        "đạt" thì bộ dò mù — và D6 là đối chứng mẫu sai TIÊM CÓ CHỦ ĐÍCH.
        """
        dong = []
        for b in self.ban_sao:
            with open(os.path.join(GOC_CAY, b["duong"]), encoding="utf-8") as f:
                nguon = f.read()
            kq = kiem_quy_tac(nguon, self.mau_tu_do)
            self.assertTrue(kq["dat"], "%s: miễn trừ KHÔNG theo quy tắc vùng — %s"
                            % (b["duong"], kq["ly_do"]))
            # Bản "khác gần nhất" (cách chọn CŨ) — chỉ để đối chiếu, không dùng để kết luận.
            sha_gan, nguon_gan = nguon_truoc_khi_va(b["duong"])
            kq_gan = kiem_quy_tac(nguon_gan, self.mau_tu_do) if nguon_gan is not None else None
            sha, truoc, kq_cu = nguon_cu_hong(b["duong"], self.mau_tu_do)
            self.assertIsNotNone(truoc, "%s: KHÔNG có bản lịch sử nào bị quy tắc bắt ⇒ không có "
                                        "đối chứng âm cho bộ dò (D6 là đối chứng mẫu tiêm)"
                                 % b["duong"])
            self.assertFalse(kq_cu["dat"], "%s: bản CŨ (%s) cũng ĐẠT ⇒ bộ dò QUY TẮC mù:\n%s"
                             % (b["duong"], sha[:8], json.dumps(kq_cu, ensure_ascii=False)))
            dong.append((b["duong"], sha, truoc, kq_cu, kq, sha_gan, kq_gan))
        _dc_am("quy-tac-truoc-sau")
        _dc_duong("quy-tac-truoc-sau")
        print("  [D4] QUY TẮC — %d/%d bản sao ĐẠT; mỗi tệp có một bản LỊCH SỬ bị bắt:"
              % (len(dong), len(self.ban_sao)))
        for duong, sha, truoc, kq_cu, kq, sha_gan, kq_gan in dong:
            bo_qua = ""
            if sha_gan and sha_gan != sha and kq_gan and kq_gan["dat"]:
                bo_qua = " · bỏ qua bản khác gần nhất %s (ĐẠT)" % sha_gan[:8]
            print("        · %-28s bản bị bắt %s (%s)%s"
                  % (duong, sha[:8], kq_cu["ly_do"][:60], bo_qua))
            print("        %-30s nay ĐẠT qua %s" % ("", kq["nguon_vung"]))

    def test_d5_bo_do_KHONG_mu_voi_mot_ban_sao_gia(self):
        """ĐỐI CHỨNG DƯƠNG cho bộ DÒ: một bản sao GIẢ dựng trong cây tạm phải được TÌM RA."""
        tam = tempfile.mkdtemp(prefix="veh-g22-do-")
        try:
            os.makedirs(os.path.join(tam, "app", "thu"), exist_ok=True)
            with open(os.path.join(tam, "app", "thu", "thu_gia.py"), "w", encoding="utf-8") as f:
                f.write("import unittest\n\n\n"
                        "class A_Nen(unittest.TestCase):\n"
                        "    def test_a1_cay_sach_gia(self):\n"
                        "        pass\n")
            # Vùng thử/tài liệu được TỰ DÒ bằng git, nên cây tạm phải là một kho git THẬT.
            # Không `commit`: bộ dò phải thấy cả tệp CHƯA THEO DÕI (`ls-files --others`).
            r = chotcay._git("init", "-q", goc=tam)
            self.assertEqual(r.returncode, 0, "không dựng được kho git tạm: %s" % r.stderr)
            self.assertEqual(thu_muc_vung(tam), ["app/thu"],
                             "vùng tự dò của cây tạm sai ⇒ phép thử này không đo gì")
            tim = bo_ung_vien(tam)
            self.assertEqual([b["duong"] for b in tim], ["app/thu/thu_gia.py"],
                             "bộ dò KHÔNG thấy bản sao giả ⇒ nó mù: %s" % (tim,))
        finally:
            shutil.rmtree(tam, ignore_errors=True)
        _dc_am("bo-do-mu")
        _dc_duong("bo-do-mu")
        print("  [D5] bộ dò TÌM RA bản sao giả dựng trong cây tạm (`app/thu/thu_gia.py`)")

    def test_d6_hai_bo_do_QUY_TAC_co_rang_hai_chieu(self):
        """ĐỐI CHỨNG cho hàm thuần `kiem_quy_tac`: nguồn QUY TẮC ⇒ ĐẠT, nguồn TÊN CỨNG ⇒ HỎNG."""
        mau = ("app/thu/**", "docs/**")
        theo_quy_tac = (
            "import unittest\n"
            "PHAM_VI_WAVE = ('app/thu/**', 'docs/**')\n"
            "def _loc(dong, ngoai=PHAM_VI_WAVE):\n"
            "    return [d for d in dong]\n"
            "class A_Nen(unittest.TestCase):\n"
            "    def test_a1_cay_sach(self):\n"
            "        return _loc([])\n")
        ten_cung = (
            "import unittest\n"
            "TEP_CUA_TOI = ('app/thu/thu_gia.py', 'docs/GIA.md')\n"
            "def _loc(dong, ngoai=TEP_CUA_TOI):\n"
            "    return [d for d in dong]\n"
            "class A_Nen(unittest.TestCase):\n"
            "    def test_a1_cay_sach(self):\n"
            "        return _loc([])\n")
        self.assertTrue(kiem_quy_tac(theo_quy_tac, mau)["dat"],
                        "nguồn THEO QUY TẮC bị phán HỎNG ⇒ bộ dò chặt oan")
        self.assertFalse(kiem_quy_tac(ten_cung, mau)["dat"],
                         "nguồn DANH SÁCH TÊN CỨNG được tha ⇒ bộ dò mù")
        _dc_am("quy-tac-hai-chieu")
        _dc_duong("quy-tac-hai-chieu")
        print("  [D6] `kiem_quy_tac` hai chiều: nguồn quy tắc ĐẠT · nguồn danh sách cứng HỎNG")

    def test_d7_vung_tha_phai_chung_minh_duoc(self):
        """Chỉ tha cả một vùng khi vùng ấy CHỨNG MINH được là không chạy trong sản phẩm."""
        vi = chotcay.chung_minh_vung(goc=GOC_CAY)
        self.assertEqual(vi, [], "VÙNG THỬ/TÀI LIỆU đã chạm sản phẩm ⇒ không được tha:\n  - "
                         + "\n  - ".join(vi))
        co_rang, ly_do = chotcay._co_rang_chung_minh_vung()
        self.assertTrue(co_rang, "bộ chứng minh vùng MÙ (đối chứng dương hỏng): %s" % ly_do)
        _dc_duong("chung-minh-vung")
        print("  [D7] vùng %s: 0 vi phạm · bộ chứng minh BẮT được vi phạm cố ý"
              % (chotcay.vung_thu_tai_lieu(goc=GOC_CAY),))


class Z_TongKet(unittest.TestCase):
    """Sổ đối chứng + vân tay cây + tệp tạm còn sót."""

    def test_z1_moi_nhom_am_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertEqual(thieu, [], "nhóm có ca ÂM mà KHÔNG có đối chứng DƯƠNG: %s" % thieu)
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")
        _dc_duong("so-doi-chung")
        print("\nSỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))

    def test_z2_khong_con_tep_tam_nao(self):
        con = [d for d in (TEP_SAN_PHAM_TAM, TEP_TRONG_VUNG_TAM)
               if os.path.exists(os.path.join(GOC_CAY, d))]
        self.assertEqual(con, [], "bộ thử để lại tệp tạm trong cây: %s" % con)
        _dc_am("tu-don-dep")
        p = os.path.join(GOC_CAY, TEP_SAN_PHAM_TAM)
        with open(p, "w", encoding="utf-8") as f:
            f.write("# gia\n")
        try:
            self.assertTrue(os.path.exists(p), "không dựng được tệp giả để đối chứng")
        finally:
            os.remove(p)
        _dc_duong("tu-don-dep")
        print("  [Z2] 0 tệp tạm còn lại (bộ dò bắt được tệp giả vừa dựng)")

    def test_z3_van_tay_cay_khong_doi_trong_luot_do(self):
        """Vân tay CHÍNH là Git (luật §41): HEAD + `git diff HEAD` + `status -uall`."""
        vt = chotcay.van_tay()
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", vt["head"]), "HEAD không đọc được")
        truoc = os.environ.get("VIP_G22_VAN_TAY_TRUOC", "").strip()
        if truoc:
            with open(truoc, encoding="utf-8") as f:
                t = json.load(f)
            self.assertEqual(vt["head"], t["head"], "HEAD ĐỔI giữa lượt đo")
            self.assertEqual(vt["status"], t["status"], "cây ĐỔI giữa lượt đo ⇒ số đo vô hiệu")
            print("  [Z3] vân tay KHÔNG ĐỔI (HEAD=%s · %d dòng status)"
                  % (vt["head"][:12], len(vt["status"])))
        else:
            print("  [Z3] vân tay: HEAD=%s · %d dòng status · chế độ=%s (mốc TRƯỚC bỏ trống — "
                  "chỉ GHI RA)" % (vt["head"][:12], len(vt["status"]), vt["che_do"]))
        _dc_duong("van-tay")

    def test_z4_pham_vi_da_do_va_cai_nam_ngoai(self):
        _dc_duong("pham-vi")
        print("\n  [Z4] PHẠM VI ĐÃ ĐO: %s %s · python %s"
              % (os.uname().sysname, os.uname().machine,
                 ".".join(map(str, sys.version_info[:3]))))
        print("       VÙNG THỬ/TÀI LIỆU (tự dò): %s" % (chotcay.vung_thu_tai_lieu(),))
        print("       BẢN SAO (tự dò): %d — %s"
              % (len(bo_ung_vien()), " · ".join(b["duong"] for b in bo_ung_vien())))
        print("       NGOÀI PHẠM VI: gọi hãng (kể cả sandbox — V-G09-01/V-13906-05 CHƯA CẤP) · "
              "push/deploy/tunnel · cổng ra ngoài · `CHO_PHEP_LIVE` · credentials thật · "
              "PostgreSQL nghiệp vụ (D-8) · Chromium/tầng 3")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. IN BẢNG (dùng cho báo cáo; cũng là cách đọc "N/N bản sao" bằng mắt)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _in_bang():
    ds, hong = bang()
    print("BẢNG BẢN SAO CHỐT \"CÂY SẠCH\" — TỰ DÒ, KHÔNG LIỆT KÊ TÊN")
    print("VÙNG THỬ/TÀI LIỆU (tự dò): %s" % (chotcay.vung_thu_tai_lieu(),))
    print("MẪU VÙNG (tự dò): %s" % (chotcay.mau_vung_chuan(),))
    print("%-30s %-6s %-10s %-12s %-9s %s"
          % ("BẢN SAO", "SỐ CA", "XANH", "BẢN CŨ BỊ BẮT", "QUY TẮC", "NGUỒN VÙNG"))
    for r in ds:
        print("%-30s %-6d %-10s %-12s %-9s %s"
              % (r["duong"], r["xanh"]["ca"], "✓" if r["xanh"]["dat"] else "✗ (mã %d)"
                 % r["xanh"]["ma"],
                 ("✓ (%s)" % r["truoc"]["sha"][:8]) if (r["truoc"]
                                                        and not r["truoc"]["quy_tac"]["dat"]) else "✗",
                 "✓" if r["quy_tac"]["dat"] else "✗", r["quy_tac"]["nguon_vung"]
                 or ("mẫu khai: %s" % (r["quy_tac"]["mau_khai"],))))
    print("KẾT LUẬN: %d/%d bản sao ĐẠT cả XANH lẫn QUY TẮC · %d bản HỎNG"
          % (len(ds) - hong, len(ds), hong))
    for r in ds:
        if not (r["xanh"]["dat"] and r["quy_tac"]["dat"]):
            print("  ✗ %s: xanh=%s · quy_tắc=%s" % (r["duong"], r["xanh"], r["quy_tac"]["ly_do"]))
    return 1 if hong else 0


if __name__ == "__main__":
    print("NỀN ĐO: HEAD=%s" % chotcay._git("rev-parse", "HEAD").stdout.strip())
    print("PHẠM VI: chỉ đọc cây + chạy các bộ thử khác trong TIẾN TRÌNH CON trên CÙNG cây này · "
          "KHÔNG cổng mạng · KHÔNG gọi hãng")
    if "--bang" in sys.argv:
        sys.exit(_in_bang())
    if "--van-tay-ghi" in sys.argv:
        with open(sys.argv[sys.argv.index("--van-tay-ghi") + 1], "w", encoding="utf-8") as f:
            json.dump(chotcay.van_tay(), f, ensure_ascii=False)
        print("đã ghi vân tay TRƯỚC")
        sys.exit(0)
    unittest.main(verbosity=2)
