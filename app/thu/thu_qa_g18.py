#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18 — AG-01 (QA/VERIFIER): bộ thử ĐỘC LẬP ĐÓNG CÁC LỖ HỔNG "CHƯA ĐO" của G17.

VÌ SAO CÓ TỆP NÀY
-----------------
`docs/QA_G17.md` §5 để lại **11 mục CHƯA ĐO** (lỗ hổng phạm vi, KHÔNG phải ĐẠT). Wave G18 chỉ
đóng lỗ hổng đã ghi ra, không làm lại mục đã đạt. Tệp này dựng phép đo ĐỘC LẬP cho **sáu mục
đo được** trong danh sách đó, và ghi thẳng sáu mục còn lại vào `docs/QA_G18.md` §"CHƯA ĐO".

| Mục §5 QA_G17 | Nội dung | Làn đo trong tệp này |
|---|---|---|
| 3 | Harness SANDBOX AG-04 (`trien_khai/g16/**`) | `C_HarnessG16` |
| 4 | Tầng 3 — DOM/CSS Chromium | `B_Tang3` |
| 5 | Đa tiến trình thật (`app/thu/dong_thoi/chay.py`) | `D_DongThoi` |
| 6 | Ma trận `(cửa × POST/PUT/DELETE)` | `E_MaTranGhi` |
| 7 | Mặt phẳng `/api/v2/platform/*` | `F_PlaneNenTang` |
| 8 | Hai tầng frontend (56 + 36 ca) | `G_HaiTangFE` |
| 9 | V11 — PostgreSQL (cụm RIÊNG) | `H_Postgres` |

AG-01 KHÔNG viết mã sản phẩm. Tệp này chỉ ĐỌC, DỰNG NỀN RIÊNG và ĐO. Tìm thấy lỗi thì GHI LẠI
và BÁO CÁO — không tự sửa.

BỐN LUẬT TỰ ÁP
--------------
1. **Không chạm mạng thật.** Mọi phép đo lớp HTTP chỉ dùng máy chủ CỦA CHÍNH DỰ ÁN bind
   `127.0.0.1` **cổng 0**. Không gọi hãng thật kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA
   CẤP). Không push, không deploy, không tunnel, không mở `CHO_PHEP_LIVE`.
2. **CSDL riêng.** `VIP_HUB_DATA` trỏ vào thư mục tạm, KHÔNG BAO GIỜ `app/du-lieu/`.
   Cụm PostgreSQL thử (nếu chạy) là cụm RIÊNG cổng `55432`; cổng `5432` (đang giữ
   `vip_customs*` của dự án khác) bị CHẶN CỨNG và có ca phủ định chạy thật.
3. **HAI CHỐT CHẶN BẮT BUỘC** (`docs/QA_G13_G15.md` §6.3):
   · `J_TuKiemBoDo` — ca CỐ Ý HỎNG chạy trong **TIẾN TRÌNH CON**, khẳng định bộ dò THẤY nó
     hỏng; kèm **đột biến trên cây sao chép** để chứng minh từng cổng CÓ RĂNG;
   · `DOI_CHUNG` — mọi nhóm có ca PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG; `Z_TongKet` tự phán HỎNG
     nếu thiếu.
4. **Phán bằng MÃ THOÁT + SỐ CA**, không bằng chữ trong output.

GHIM HEAD: `VIP_G18_HEAD=7b741c88b3b280d65f80b5e11301f17ebd767b26` thì phép ghim là cổng CỨNG.
Không đặt thì phép ghim chỉ GHI RA (tệp này còn phải chạy được sau khi gộp vào nhánh khác).

BIẾN MÔI TRƯỜNG
---------------
    VIP_G18_DATA        nền CSDL tạm (mặc định: thư mục tạm mới)
    VIP_G18_HEAD        ghim commit nền đo
    VIP_G18_PW_BROWSERS thư mục nhị phân Playwright cho tầng 3 (mặc định: bản đã được
                        `docs/BAN_GIAO.md` §1 chỉ định — `~/code/veh4-g12-playwright/…`;
                        KHÔNG dùng cache hệ thống `~/Library/Caches/ms-playwright`)
    VIP_G18_DAY_DU=1    bật thêm làn TỐN THỜI (chạy trọn `thu_postgres.py`)
    VIP_G18_LOG         thư mục ghi log thô của các làn nặng

Chạy: VIP_G18_HEAD=7b741c88b3b280d65f80b5e11301f17ebd767b26 python3 app/thu/thu_qa_g18.py
"""
import ast
import atexit
import fnmatch
import glob
import hashlib
import http.client
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.dont_write_bytecode = True          # không để lại __pycache__ trong cây ĐANG ĐO

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)

# CHỐT "CÂY SẠCH" + VÂN TAY + MÔI TRƯỜNG GIT — MỘT chỗ duy nhất (AG-05 G21). Ba bản sao của cùng
# một luật là ba bản sẽ trôi khỏi nhau — đúng khuôn `N-G18-00` (hai nhiệt kế, hai kết quả).
try:
    import thu_g21_chotcay as chotcay                                    # noqa: E402
except ImportError:                                                      # pragma: no cover
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import thu_g21_chotcay as chotcay                                    # noqa: E402

THU_MUC_THU = os.path.dirname(os.path.abspath(__file__))

_TAM = os.environ.get("VIP_G18_DATA") or tempfile.mkdtemp(prefix="veh-g18-qa-")
os.environ["VIP_HUB_DATA"] = _TAM
LOG_DIR = os.environ.get("VIP_G18_LOG") or os.path.join(tempfile.gettempdir(), "veh_g18_ag01_qa_log")

# `append`, KHÔNG `insert(0)`: driver đột biến đặt cây đột biến LÊN TRƯỚC qua PYTHONPATH, và
# `insert(0)` ở đây sẽ kéo cây gốc trở lại vị trí đầu — đột biến biến mất mà không ai báo.
if GOC_APP not in sys.path:
    sys.path.append(GOC_APP)

import adapter                                                          # noqa: E402
import bao_mat                                                          # noqa: E402
import cau_hinh                                                         # noqa: E402
import csdl                                                             # noqa: E402
import quyen                                                            # noqa: E402
import server                                                           # noqa: E402

HEAD_GHIM = os.environ.get("VIP_G18_HEAD", "").strip()
DAY_DU = os.environ.get("VIP_G18_DAY_DU", "") == "1"
SO_DUONG_API = re.compile(r'"(/api/v2/[^"]*)"')

# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHẠM VI CỦA WAVE — cái gì được phép BẨN mà cổng "cây sạch" vẫn xanh
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# LỊCH SỬ — CÙNG MỘT LỖI, BA LẦN (đọc trước khi sửa):
#   · `N-G18-03` (chính làn này ghi ra ở `docs/QA_G18.md`): bản trước miễn trừ ĐÚNG HAI tệp của làn
#     này, nên chỉ cần một làn KHÁC giao tệp mới là cổng ĐỎ — không phải vì cây bẩn, mà vì người ta
#     vừa làm ĐÚNG việc của mình.
#   · Bản G20 khai ĐÍCH DANH từng tệp của làn khác (`PHAM_VI_LAN_KHAC`) ⇒ wave SAU giao một tệp MỚI
#     là cổng ĐỎ LẦN NỮA. AG-01 đo được ở G20 (`docs/QA_G20.md` §2.1, CỔNG C1): **0/2** cổng xanh,
#     và `sh app/thu/chay_tat_ca.sh` đỏ vì lý do TÍCH HỢP — rất dễ đọc nhầm thành "G21 làm hỏng G18".
#
# NAY: miễn trừ theo **QUY TẮC**, KHÔNG theo tên tệp.
#     "CÂY SẠCH" = **KHÔNG có thay đổi NÀO ngoài các tệp mà WAVE ĐANG LÀM**
#     "các tệp mà wave đang làm" = mọi đường nằm trong **VÙNG THỬ/TÀI LIỆU** (`docs/` + mọi thư mục
#     có tên bắt đầu bằng `thu`). Tệp MỚI do `git status -uall` TỰ TÌM.
#
# ĐÂY KHÔNG PHẢI "BỎ QUA HẾT" — điều đó được ĐO:
#   · `test_a1d` — ĐỐI CHỨNG ÂM bốn tầng trên CÂY GIT THẬT: tệp SẢN PHẨM bẩn ⇒ cổng ĐỎ;
#   · `thu_g21_chotcay.chung_minh_vung()` — CHỨNG MINH vùng thử không chạy trong sản phẩm;
#   · `thu_g20_baomat.py::B_ChotCaySach` — bộ của wave TRƯỚC, KHÔNG sửa, vẫn đo cả hai chiều.
PHAM_VI_LAN_NHA = ("docs/QA_G18*.md", "app/thu/thu_qa_g18*.py")

# Làn KHÁC trong cùng wave — NAY **RỖNG**, và phải RỖNG MÃI: miễn trừ theo quy tắc, không theo tên.
# Giữ TÊN biến (không xoá) vì `thu_g20_baomat.py` đọc nó bằng AST để đo ĐỘC LẬP, và `test_a1b` canh
# nó không được chứa ký tự mẫu lẫn đường dẫn sản phẩm.
PHAM_VI_LAN_KHAC = (
)

# MẪU VÙNG THỬ/TÀI LIỆU — phải KHỚP `thu_g21_chotcay.mau_vung_chuan()`; `test_a1b` canh trôi.
PHAM_VI_WAVE = (
    "app/thu/**",
    "docs/**",
    "gateway/thu/**",
    "thu_frontend/**",
    "thu_giao_dien/**",
)

# Các thư mục được phép xuất hiện trong phạm vi miễn trừ. Mã sản phẩm nằm NGOÀI.
THU_MUC_PHAM_VI = ("app/thu/", "docs/", "gateway/thu/", "thu_frontend/", "thu_giao_dien/")

# Giữ tên cũ cho tương thích các chỗ gọi hiện có.
# `TEP_CUA_AG01_G18` = HỌ BỘ KIỂM của làn này (câu hỏi HẸP, `_la_tep_ag01` trả lời);
# `MAU_TEP_CUA_AG01_G18` = mẫu vùng thử/tài liệu (câu hỏi RỘNG, chốt trả lời).
MAU_TEP_CUA_AG01_G18 = PHAM_VI_WAVE
TEP_CUA_AG01_G18 = PHAM_VI_LAN_NHA

# Nhị phân Chromium: `docs/BAN_GIAO.md` §1 chỉ định nguồn này (bản 1194 khớp
# playwright-core 1.56.1 của chính worktree) và CẤM dùng cache hệ thống của dự án khác.
PW_BROWSERS_CHI_DINH = os.path.expanduser(
    "~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers")
PW_BROWSERS_REPO = os.path.join(GOC_CAY, "node_modules", "playwright-core", ".local-browsers")

# Cửa CÔNG KHAI (không cần phiên) — tra thẳng từ `app/server.py`, không chép tay:
# ba cửa auth đầu + webhook (xác thực bằng chữ ký).
DUONG_CONG_KHAI = ("/api/v2/auth/dang-nhap", "/api/v2/auth/quen-mat-khau",
                   "/api/v2/auth/dat-lai-mat-khau")
RE_STATIC_WRITE = re.compile(r'duong == "(/api/v2/[^"]+)"\s*and\s*method\s+(?:==|in)\s+(.+)')
RE_STATIC_PLATFORM = re.compile(r'duong == "(/api/v2/platform/[^"]+)"')
RE_FULLMATCH = re.compile(r're\.fullmatch\(\s*r?["\'](/api/v2/[^"\']+)["\']')


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0a. SỔ ĐỐI CHỨNG DƯƠNG + TIỆN ÍCH ĐO
# ══════════════════════════════════════════════════════════════════════════════════════════════
DOI_CHUNG = {}


def _dc(nhom, loai):
    o = DOI_CHUNG.setdefault(nhom, {"duong": 0, "am": 0})
    o[loai] += 1


def _dc_duong(nhom):
    """ĐỐI CHỨNG DƯƠNG: khẳng định cửa/hàm CÓ chạy đúng khi đầu vào hợp lệ."""
    _dc(nhom, "duong")


def _dc_am(nhom):
    """Ca PHỦ ĐỊNH: khẳng định hệ TỪ CHỐI / KHÔNG để lọt."""
    _dc(nhom, "am")


def _doc_app(ten):
    with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
        return f.read()


def _git(*tham_so, env=None, goc=None):
    """Git với môi trường `GIT_CONFIG_*` ĐÃ CHUẨN HOÁ — **KÈM CẢNH BÁO**, không gỡ im lặng.

    Máy này có `GIT_CONFIG_COUNT=2` nhưng `GIT_CONFIG_KEY_0`/`_1` RỖNG ⇒ mọi lệnh git thoát 128
    (`fatal: unable to parse command-line config`) — `N-G17-00`, tái diễn thành `N-G18-00`. Việc
    chuẩn hoá nay nằm MỘT chỗ (`thu_g21_chotcay.env_git`) và nó PHÂN BIỆT hai thứ khác hẳn nhau:
      · MÔI TRƯỜNG hỏng  ⇒ gỡ gia đình biến + in cảnh báo ra `stderr`;
      · CÂY hỏng thật    ⇒ lệnh git vẫn hỏng, mã thoát + `stderr` trả NGUYÊN VẸN cho người gọi.
    Không nhánh nào biến một lỗi thật thành "thành công" (`thu_g21_chotcay::E_MoiTruongGit.test_e3`).

    `goc` (mặc định cây đang đo) cho phép trỏ vào CÂY TẠM của đối chứng âm.
    """
    return chotcay._git(*tham_so, goc=goc or GOC_CAY, env=env)


def _la_tep_trong_pham_vi(duong):
    """Đường này có nằm trong VÙNG THỬ/TÀI LIỆU (được phép bẩn) không. QUY TẮC, không danh sách."""
    return any(fnmatch.fnmatch(duong, m) for m in PHAM_VI_WAVE)


def _la_tep_ag01(dong_porcelain):
    """HẸP CÓ CHỦ Ý — đường này có thuộc **HỌ BỘ KIỂM NGHIỆM THU của wave này** không.

    ⚠ ĐÂY **KHÔNG PHẢI** CHỐT "CÂY SẠCH". Chốt là `_chot_do()` (miễn trừ theo QUY TẮC vùng). Giữ
    nguyên độ hẹp là CỐ Ý: `thu_qa_g20.py::test_g1` (bộ nghiệm thu wave trước) đo đúng câu hỏi hẹp
    ấy — "cơ chế miễn trừ còn nhận ra tệp của CHÍNH NÓ không". Nới hàm này thành chốt rộng sẽ làm
    phép đo của wave trước trả lời SAI câu hỏi.
    """
    d = _duong_porcelain(dong_porcelain)
    return bool(d) and any(fnmatch.fnmatch(d, m) for m in (PHAM_VI_LAN_NHA + PHAM_VI_LAN_KHAC))


def _duong_porcelain(dong):
    """Đường của một dòng `git status --porcelain`. Dòng đổi tên ⇒ lấy đường ĐÍCH."""
    if not dong or not dong.strip():
        return ""
    p = dong[3:].strip().strip('"')
    if " -> " in p:
        p = p.split(" -> ", 1)[1].strip().strip('"')
    return p


def _mau_chot(goc=None, env=None):
    """Mẫu của CHỐT — TỰ DÒ từ cây (`thu_g21_chotcay`), không liệt kê tệp nào."""
    return chotcay.mau_vung_chuan(goc=goc or GOC_CAY, env=env)


def _chot_do(env=None, goc=None):
    """CHỐT "CÂY SẠCH": các dòng ĐỎ = thay đổi **NGOÀI vùng thử/tài liệu**.

    Trước khi tha cả một vùng, `chung_minh_vung()` phải CHỨNG MINH được vùng đó không chạy trong
    sản phẩm; chứng minh hỏng ⇒ NÉM LỖI. Chỉ chạy chứng minh trên cây THẬT (cây git tạm của đối
    chứng âm không có `app/server.py`).
    """
    if goc is None:
        vi = chotcay.chung_minh_vung(goc=GOC_CAY, env=env)
        if vi:
            raise RuntimeError("VÙNG THỬ/TÀI LIỆU không còn vô hại — chốt TỪ CHỐI tha:\n  - "
                               + "\n  - ".join(vi))
    st = _git("status", "--porcelain=v1", "-uall", env=env, goc=goc).stdout
    return _loc_cay_ban(st.splitlines(), _mau_chot(goc=goc, env=env))


def _loc_cay_ban(dong, ngoai=()):
    """HÀM THUẦN: bỏ các dòng mà MỌI đường của nó khớp `ngoai`; giữ phần còn lại.

    `ngoai=()` ⇒ trả về **MỌI** dòng bẩn: hàm này KHÔNG tự áp chính sách ẩn nào. Chốt "cây sạch"
    là `_loc_cay_ban(dong, _mau_chot())` — xem `_chot_do()`.

    Dòng ĐỔI TÊN bị ĐỎ nếu **MỘT TRONG HAI** đường nằm ngoài `ngoai`: kéo một tệp sản phẩm vào
    thư mục thử vẫn là một thay đổi sản phẩm.
    """
    ra = []
    for d in dong:
        if not d.strip():
            continue
        ds = chotcay.duong_tu_dong_porcelain(d)
        if ngoai and all(any(fnmatch.fnmatch(x, m) for m in ngoai) for x in ds):
            continue
        ra.append(d)
    return ra


def _cay_ban(ngoai=(), env=None, goc=None):
    """Các dòng `git status` KHÔNG khớp `ngoai`. `goc` = cây git KHÁC (đối chứng âm).

    `ngoai=()` ⇒ trả về MỌI dòng bẩn — cùng lý do như `_loc_cay_ban`. Muốn câu hỏi "cây có gì bẩn
    NGOÀI phạm vi wave" thì dùng `_chot_do()`.
    """
    st = _git("status", "--porcelain=v1", "-uall", env=env, goc=goc).stdout
    return _loc_cay_ban(st.splitlines(), ngoai)


def van_tay_cay(env=None):
    """Vân tay cây: `{ git ls-files -s; git status --porcelain -uall; }` (lọc theo vùng thử).

    ⚠ Đây là vân tay **DỰ PHÒNG**. Vân tay **CHÍNH** là Git (`thu_g21_chotcay.van_tay_git`):
    `rev-parse HEAD` + `git diff HEAD` rỗng + `status --porcelain -uall` rỗng. Bản cũ chỉ `find`
    bốn thư mục theo bốn đuôi tệp nên **MÙ** với `docs/*.md` (`G16-09`).
    """
    ls = _git("ls-files", "-s", env=env)
    st = _git("status", "--porcelain=v1", "-uall", env=env)
    con = _loc_cay_ban(st.stdout.splitlines(), PHAM_VI_WAVE)
    return hashlib.sha256((ls.stdout + "\n" + "\n".join(con)).encode("utf-8")).hexdigest()


def _chay(lenh, env=None, giay=900, cwd=None):
    """Chạy một lệnh THẬT trong tiến trình con. Trả (mã thoát, output, số giây)."""
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e.update(env or {})
    t0 = time.time()
    r = subprocess.run(lenh, capture_output=True, text=True, env=e, timeout=giay,
                       cwd=cwd or GOC_CAY)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0


def _ghi_log(ten, ma, ra):
    """Ghi log THÔ của một làn nặng ra đĩa để người đọc soi lại được."""
    os.makedirs(LOG_DIR, exist_ok=True)
    duong = os.path.join(LOG_DIR, ten)
    with open(duong, "w", encoding="utf-8") as f:
        f.write("MA_THOAT=%s\n" % ma)
        f.write(ra)
    return duong


def _phan_quyet(ma_thoát, ra):
    """Luật phán của bộ chạy chung: mã thoát + DẤU VẾT ĐÃ CHẠY + số ca > 0."""
    n = 0
    m = re.findall(r"Ran (\d+)", ra)
    if m:
        n = int(m[-1])
    else:
        m2 = re.findall(r"(\d+) ca — ĐẠT", ra)
        if m2:
            n = int(m2[-1])
    co_dau_vet = bool(re.search(r"^OK( |$)|ca — ĐẠT", ra, re.M))
    if ma_thoát == 0 and co_dau_vet and n > 0:
        return "ĐẠT"
    if ma_thoát == 0 and n == 0 and "skipped" in ra:
        return "BỎ QUA"
    return "HỎNG"


def _so_ca(ra):
    """Số ca theo `Ran N` (unittest) hoặc `N ca — ĐẠT` (bộ viết tay). 0 nếu không thấy."""
    m = re.findall(r"Ran (\d+)", ra)
    if m:
        return int(m[-1])
    m2 = re.findall(r"(\d+) ca — ĐẠT", ra)
    return int(m2[-1]) if m2 else 0


def _so_skip(ra):
    m = re.findall(r"skipped=(\d+)", ra)
    return int(m[-1]) if m else 0


def _cong_ranh():
    """Cổng do hệ điều hành cấp (bind 0) — không tranh cổng với làn khác, không HỎNG GIẢ."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = s.getsockname()[1]
    s.close()
    return cong


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0b. CHỐT AN TOÀN — bộ thử TỪ CHỐI CHẠY nếu thiếu
# ══════════════════════════════════════════════════════════════════════════════════════════════
def kiem_chot_an_toan(mt=None):
    """Trả LÝ DO TỪ CHỐI CHẠY, hoặc `None` nếu đủ ba chốt an toàn."""
    loi = []
    duong = os.path.abspath(cau_hinh.THU_MUC_DU_LIEU)
    tam = os.path.abspath(tempfile.gettempdir())
    if duong.startswith(os.path.abspath(GOC_CAY) + os.sep) or not duong.startswith(tam + os.sep):
        loi.append(f"nền CSDL KHÔNG nằm trong thư mục tạm (hoặc nằm trong cây repo): {duong}")
    mo = sorted(m for m, lop in adapter._DANG_KY.items() if getattr(lop, "CHO_PHEP_LIVE", False))
    if mo:
        loi.append(f"có adapter MỞ LIVE: {mo}")
    if mt is not None and mt.get("dia_chi") != "127.0.0.1":
        loi.append(f"máy chủ KHÔNG bind loopback: {mt.get('dia_chi')!r}")
    return "; ".join(loi) or None


_LY_DO_TU_CHOI = kiem_chot_an_toan()
if _LY_DO_TU_CHOI:
    sys.stderr.write("TỪ CHỐI CHẠY — thiếu chốt an toàn: " + _LY_DO_TU_CHOI + "\n")
    raise SystemExit(3)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. NỀN ĐO: schema → quyền → 2 tenant A/B → máy chủ 127.0.0.1 CỔNG 0
# ══════════════════════════════════════════════════════════════════════════════════════════════
_MT = {}
MK = "qa-g18-mat-khau-thu"          # mật khẩu THỬ trong CSDL TẠM — không phải credential thật


def _user(ten_dn, vai_tro=None):
    return csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                    " VALUES (?,?,?,?,?)",
                    (ten_dn, bao_mat.bam_mat_khau(MK), ten_dn, vai_tro, csdl.bay_gio())).lastrowid


def _gan(uid, tid, role):
    csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc) VALUES (?,?,?,?)",
             (uid, tid, role, csdl.bay_gio()))


DON_MAU = {
    "nguoi_gui_ten": "Shop QA G18", "nguoi_gui_sdt": "0901111111",
    "nguoi_gui_dia_chi": "1 Duong Thu, Ha Noi",
    "nguoi_nhan_ten": "Khach QA G18", "nguoi_nhan_sdt": "0902220001",
    "nguoi_nhan_dia_chi": "2 Pho Thu, TP.HCM",
    "hang_hoa": "Kien thu G18", "khoi_luong_gram": 500, "cod": 350000,
}


def moi_truong():
    """Dựng nền đo MỘT LẦN cho cả tệp. Trả dict: cổng, tenant A/B, canary, token từng vai."""
    if _MT:
        return _MT
    import migrate
    csdl.mo()
    migrate.chay(im_lang=True)
    quyen.seed()

    duoi = hashlib.sha256(os.urandom(16)).hexdigest()[:8].upper()
    canary = f"QA-G18-CANARY-{duoi}"
    tid_a = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                     (f"qa18-a-{duoi}", f"Tenant A {canary}", "basic", csdl.bay_gio())).lastrowid
    tid_b = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                     (f"qa18-b-{duoi}", f"Tenant B {duoi}", "basic", csdl.bay_gio())).lastrowid

    u_a_owner = _user("qa18-a-owner"); _gan(u_a_owner, tid_a, "TENANT_OWNER")
    u_a_staff = _user("qa18-a-staff"); _gan(u_a_staff, tid_a, "TENANT_STAFF")
    u_b_owner = _user("qa18-b-owner"); _gan(u_b_owner, tid_b, "TENANT_OWNER")
    u_pl_adm = _user("qa18-plat-admin", "PLATFORM_ADMIN")
    u_pl_own = _user("qa18-plat-owner", "PLATFORM_OWNER")

    kh_a = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                    (tid_a, f"Khach A {canary}", "0900000011", "1 Le Loi", csdl.bay_gio())).lastrowid
    kh_b = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                    (tid_b, f"Khach B {duoi}", "0900000022", "2 Nguyen Hue", csdl.bay_gio())).lastrowid
    mem_a = csdl.ghi("SELECT id FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
                     (u_a_staff, tid_a)).fetchone()["id"]

    acc_a = {}
    for hang in ("vtp", "jt"):
        ban_ma, _ = bao_mat.ma_hoa_cred({"ghi_chu": "credential GIA trong CSDL TAM"}, tid_a, hang)
        wh_ma = f"qa18{tid_a}{hang}{duoi}".lower()
        acc_a[hang] = csdl.ghi(
            "INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
            " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (tid_a, hang, f"TK {hang} A {canary}", "mock", ban_ma, "", wh_ma,
             bao_mat.ma_hoa_wh("secret-gia-" + wh_ma, wh_ma), csdl.bay_gio())).lastrowid

    class _ImLang(server.BoXuLy):
        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ImLang)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    atexit.register(lambda: (srv.shutdown(), srv.server_close()))

    def _tok(uid):
        t, _ = bao_mat.dang_nhap(csdl.mot("SELECT ten_dang_nhap t FROM users WHERE id=?", (uid,))["t"], MK)
        return t

    _MT.update(cong=srv.server_address[1], dia_chi=srv.server_address[0],
               duoi=duoi, canary=canary, tid_a=tid_a, tid_b=tid_b, kh_a=kh_a, kh_b=kh_b,
               mem_a=mem_a, acc_a=acc_a,
               a_owner=_tok(u_a_owner), a_staff=_tok(u_a_staff), b_owner=_tok(u_b_owner),
               pl_admin=_tok(u_pl_adm), pl_owner=_tok(u_pl_own),
               uid={"a_owner": u_a_owner, "a_staff": u_a_staff, "b_owner": u_b_owner})
    return _MT


def goi(duong, token=None, method="GET", body=None, csrf=True, cong=None, headers=None):
    """Một lượt HTTP tới máy chủ CỦA DỰ ÁN trên 127.0.0.1 cổng động. Trả (mã, dict, chuỗi_thô)."""
    mt = moi_truong()
    kn = http.client.HTTPConnection("127.0.0.1", cong or mt["cong"], timeout=20)
    h = dict(headers or {})
    if token:
        h["Cookie"] = f"phien={token}"
    if csrf and method in ("POST", "PUT", "DELETE"):
        h["X-Requested-With"] = "VIPHub"
    du = None
    if body is not None:
        du = json.dumps(body).encode()
        h["Content-Type"] = "application/json"
    kn.request(method, duong, body=du, headers=h)
    r = kn.getresponse()
    tho = r.read()
    kn.close()
    try:
        return r.status, json.loads(tho or b"{}"), tho.decode("utf-8", "replace")
    except ValueError:
        return r.status, {"_khong_phai_json": True}, tho.decode("utf-8", "replace")


def tao_don(token, **ghi_de):
    """Tạo một đơn THẬT qua HTTP. Trả id, hoặc None nếu không tạo được."""
    d = dict(DON_MAU, **ghi_de)
    ma, kq, _ = goi("/api/v2/don", token, method="POST", body=d)
    if ma not in (200, 201):
        return None
    return kq["don"]["id"]


# ---------------------------------------------------------------- rút cửa từ chính mã nguồn
def duong_ghi_tinh():
    """MỌI cặp (đường TĨNH × phương thức GHI) rút từ `app/server.py`. Không chép tay."""
    ra = set()
    for dong in _doc_app("server.py").splitlines():
        m = RE_STATIC_WRITE.search(dong)
        if not m:
            continue
        duong, meth = m.group(1), m.group(2)
        if "(" in duong or "\\" in duong:
            continue
        if not re.search(r'"(POST|PUT|DELETE|PATCH)"', meth):
            continue
        if duong in DUONG_CONG_KHAI:
            continue
        ra.add((duong, meth.strip()))
    return sorted(ra)


def duong_ghi_dong():
    """MỌI đường GHI có THAM SỐ (`re.fullmatch` + `(\\d+)`/nhóm chữ) rút từ `app/server.py`."""
    ra = set()
    dong = _doc_app("server.py").splitlines()
    for i, d in enumerate(dong):
        m = RE_FULLMATCH.search(d)
        if not m:
            continue
        mau = m.group(1)
        if not mau.startswith("/api/v2/") or mau.startswith("/api/v2/webhook/nhan"):
            continue
        # tìm khối lệnh của chính đường này (tối đa 30 dòng) xem có phương thức GHI nào
        khoi = "\n".join(dong[i:i + 30])
        if not re.search(r'method (==|in) [^\n]*"(POST|PUT|DELETE)"', khoi):
            continue
        ra.add(mau)
    return sorted(ra)


def duong_platform():
    """MỌI đường `/api/v2/platform/*` rút từ `app/server.py` (tĩnh + có tham số)."""
    ra = set()
    nguon = _doc_app("server.py")
    for d in RE_STATIC_PLATFORM.findall(nguon):
        ra.add(d)
    for mau in RE_FULLMATCH.findall(nguon):
        if mau.startswith("/api/v2/platform/"):
            ra.add(re.sub(r"\(.*?\)", "1", mau))
    return sorted(ra)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. CÁC PHÉP ĐO RỜI — dùng CHUNG cho ca unittest và cho DRIVER ĐỘT BIẾN (cùng một đường đo)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def do_unauth_ghi():
    """Quét KHÔNG PHIÊN mọi cửa ghi tĩnh. Trả thống kê mã trả về."""
    dem, la = {}, []
    for duong, _ in duong_ghi_tinh():
        for method in ("POST", "PUT", "DELETE"):
            ma, _, _ = goi(duong, None, method=method, body={}, csrf=False)
            dem[ma] = dem.get(ma, 0) + 1
            if ma != 401:
                la.append(f"{method} {duong} -> {ma}")
    return {"tong": sum(dem.values()), "dem": dem, "khong_401": la}


def do_csrf():
    """Cửa ghi có phiên nhưng THIẾU `X-Requested-With` phải bị chặn 403."""
    mt = moi_truong()
    thieu, _, _ = goi("/api/v2/khach-hang", mt["a_owner"], method="POST",
                      body={"ten": "csrf-thieu"}, csrf=False)
    du, _, _ = goi("/api/v2/khach-hang", mt["a_owner"], method="POST",
                   body={"ten": "csrf-du"}, csrf=True)
    return {"thieu_header": thieu, "co_header": du}


def do_platform_chan():
    """Phiên KHÔNG có `platform_role` chạm `/api/v2/platform/*` phải bị chặn."""
    mt = moi_truong()
    dem, la = {}, []
    for duong in duong_platform():
        for method in ("GET", "POST"):
            ma, _, _ = goi(duong, mt["a_owner"], method=method, body={})
            dem[ma] = dem.get(ma, 0) + 1
            if ma != 403:
                la.append(f"{method} {duong} -> {ma}")
    return {"tong": sum(dem.values()), "dem": dem, "khong_403": la}


def _kh_trang_thai_km(token):
    """Đếm khách hàng của tenant A nhìn từ chính API (KHÔNG đọc thẳng CSDL)."""
    ma, kq, _ = goi("/api/v2/khach-hang", token)
    return ma, kq.get("khach_hang", [])


def do_ghi_cheo_membership():
    """B đổi vai trò một membership CỦA A. Trả mã + membership còn nguyên không."""
    mt = moi_truong()
    truoc = csdl.mot("SELECT role, trang_thai FROM tenant_memberships WHERE id=?", (mt["mem_a"],))
    ma_b, _, _ = goi(f"/api/v2/memberships/{mt['mem_a']}", mt["b_owner"], method="POST",
                     body={"role": "TENANT_VIEWER", "trang_thai": "vo_hieu"})
    sau = csdl.mot("SELECT role, trang_thai FROM tenant_memberships WHERE id=?", (mt["mem_a"],))
    con_nguyen = (dict(truoc) == dict(sau))
    ma_a = None
    if con_nguyen:
        # ĐỐI CHỨNG DƯƠNG: chủ hợp lệ PHẢI làm được việc đó (nếu không, ca âm vô nghĩa).
        ma_a, _, _ = goi(f"/api/v2/memberships/{mt['mem_a']}", mt["a_owner"], method="POST",
                         body={"trang_thai": "hoat_dong"})
    return {"ma_b": ma_b, "con_nguyen": con_nguyen, "ma_a": ma_a}


def do_quyen_admin_tao_tenant():
    """PLATFORM_ADMIN tạo tenant — phải 403 (`platform.tenant.tao` chỉ cấp cho PLATFORM_OWNER)."""
    mt = moi_truong()
    ma, _, _ = goi("/api/v2/platform/tenants", mt["pl_admin"], method="POST",
                   body={"ten": f"QA G18 M5 {mt['duoi']}", "owner_ten_dang_nhap": "qa18-m5",
                         "owner_mat_khau": "mat-khau-thu-123"})
    return {"admin_tao_tenant": ma}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. CỔNG NỀN — cây · HEAD · ổ khoá LIVE · đường mạng · CSDL · cụm :5432
# ══════════════════════════════════════════════════════════════════════════════════════════════
VAN_TAY_LUC_NAN = van_tay_cay()

# MỐC "LÚC NÃN" của VÂN TAY CHÍNH — so "trước/sau" theo LUẬT §41, KHÔNG đòi cây phải sạch: trên
# worktree của một làn đang làm việc thì `git diff HEAD` KHÔNG rỗng (chính làn đó đang sửa tệp).
HEAD_LUC_NAN = _git("rev-parse", "HEAD").stdout.strip()
VAN_TAY_THU_MUC_LUC_NAN = chotcay.van_tay_thu_muc()["theo_doi"]
VAN_TAY_5432_LUC_NAN = None


def _van_tay_5432():
    """Vân tay cụm PostgreSQL hệ thống :5432 — CHỈ ĐỌC (psql + lsof)."""
    r = subprocess.run([sys.executable, os.path.join(GOC_CAY, "trien_khai", "postgres",
                                                     "van_tay_cum.py"), "--chup", "--cong", "5432"],
                       capture_output=True, text=True, timeout=120, cwd=GOC_CAY)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except ValueError:
        return None


class A_Nen(unittest.TestCase):
    """Vi phạm bất kỳ mục nào ở đây ⇒ CHẶN GỘP: mọi số đo khác trở nên vô hiệu."""

    def test_a1_cay_sach_theo_pham_vi_wave(self):
        """CỔNG "CÂY SẠCH" (F0) — miễn trừ theo **QUY TẮC VÙNG**, tệp MỚI do git TỰ TÌM.

        Trên nền G20 (a3400a8) cổng này ĐỎ chỉ vì một làn KHÁC giao tệp mới (`N-G19-03`). Nay "các
        tệp mà wave đang làm" được TỰ DÒ: `docs/` + mọi thư mục tên bắt đầu bằng `thu`.
        """
        vi = chotcay.chung_minh_vung(goc=GOC_CAY)
        self.assertEqual(vi, [], "VÙNG THỬ/TÀI LIỆU đã chạm sản phẩm ⇒ không được tha:\n  - "
                         + "\n  - ".join(vi))
        _dc_duong("cay-sach-vung-co-chung-minh")
        la = _chot_do()
        self.assertEqual(la, [], f"cây có thay đổi NGOÀI vùng thử/tài liệu {PHAM_VI_WAVE}: {la}")
        _dc_duong("cay-sach")
        vt = chotcay.van_tay()
        print(f"\n  [A1] cây sạch · vùng TỰ DÒ={chotcay.vung_thu_tai_lieu()}")
        print(f"  [A1] vân tay Git (CHÍNH): diff HEAD={len(vt['diff'])} đường · "
              f"status -uall={len(vt['status'])} dòng · chế độ={vt['che_do']} · dự phòng={VAN_TAY_LUC_NAN}")

    def test_a1_cay_sach_mien_tru_dung_hai_tep_ag01(self):
        """TÊN CŨ — `thu_qa_g20.py::CONG_CAY_SACH` (bộ nghiệm thu wave TRƯỚC) gọi ĐÍCH DANH tên này.

        Bản G20 đã ĐỔI TÊN ca này thành `test_a1_cay_sach_theo_pham_vi_wave` mà không giữ bí danh,
        nên lệnh đo của AG-01 (`python3 app/thu/thu_qa_g18.py
        A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01`) hỏng vì **AttributeError** — ĐỎ vì một
        lý do KHÁC HẲN "cây bẩn", và không dòng nào nói ra. Giữ HAI tên cho cùng một phép đo.
        """
        self.test_a1_cay_sach_theo_pham_vi_wave()

    # ── BA CỔNG TỰ KIỂM CHÍNH CÁI MIỄN TRỪ (AG-05 G21) ────────────────────────────────────────
    # `N-G18-03` tái diễn thành `N-G19-03` vì miễn trừ QUÁ HẸP (danh sách tên cứng). Cách chữa rẻ
    # nhất — và SAI — là nới cho rộng ra. Ba ca dưới đây chặn đúng nước đi sai đó: chúng không đo
    # mã sản phẩm, chúng đo CHÍNH PHẠM VI MIỄN TRỪ.
    def test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu(self):
        """Phạm vi miễn trừ chỉ được trỏ vào VÙNG THỬ/TÀI LIỆU — và phải KHỚP cây, không trôi.

        Ca này PIN gì: (1) mọi mục khai báo nằm trong `THU_MUC_PHAM_VI`; (2) `PHAM_VI_LAN_KHAC`
        **RỖNG** — miễn trừ nay theo QUY TẮC, không theo tên tệp; (3) mẫu khai báo PHẢI BẰNG mẫu
        TỰ DÒ từ cây — lệch là ĐỎ, vì lệch nghĩa là một vùng thử không được khai (cổng sẽ đỏ vì
        một tệp hợp lệ) hoặc một vùng sản phẩm bị nuốt.
        """
        self.assertTrue(PHAM_VI_WAVE, "phạm vi wave RỖNG ⇒ mọi phép đo dưới đây vô nghĩa")
        for m in PHAM_VI_WAVE:
            self.assertTrue(m.startswith(THU_MUC_PHAM_VI),
                            f"miễn trừ {m!r} trỏ RA NGOÀI vùng thử/tài liệu ⇒ có thể nuốt mã sản phẩm")
        for m in PHAM_VI_LAN_KHAC:
            self.assertFalse(any(c in m for c in "*?["),
                             f"miễn trừ làn khác {m!r} chứa KÝ TỰ MẪU ⇒ nuốt vô hình tệp chưa ai khai")
            self.assertTrue(m.startswith(THU_MUC_PHAM_VI),
                            f"miễn trừ làn khác {m!r} trỏ vào mã sản phẩm")
            self.assertNotIn(m, PHAM_VI_LAN_NHA)
        self.assertEqual(PHAM_VI_LAN_KHAC, (),
                         "`PHAM_VI_LAN_KHAC` KHÔNG còn rỗng ⇒ ai đó lại liệt kê tên tệp của làn khác; "
                         "miễn trừ phải theo QUY TẮC vùng (xem khối chú thích đầu tệp)")
        tu_do = chotcay.mau_vung_chuan(goc=GOC_CAY)
        self.assertEqual(tuple(sorted(PHAM_VI_WAVE)), tuple(sorted(tu_do)),
                         f"mẫu KHAI BÁO {PHAM_VI_WAVE} KHÁC mẫu TỰ DÒ {tu_do} ⇒ lời khai đã trôi "
                         f"khỏi cây")
        self.assertFalse(all("app/webhook.py".startswith(t) for t in THU_MUC_PHAM_VI),
                         "bộ dò mù: nó cho `app/webhook.py` là nằm trong phạm vi")
        _dc_am("cay-sach-pham-vi")
        _dc_duong("cay-sach-pham-vi")
        print(f"  [A1b] phạm vi wave: {len(PHAM_VI_WAVE)} mục VÙNG cho {len(PHAM_VI_LAN_NHA)} mẫu "
              f"của làn này · đích danh làn khác={len(PHAM_VI_LAN_KHAC)} (phải 0)")

    def test_a1c_pham_vi_wave_khong_muc_ruong(self):
        """Mỗi mục miễn trừ phải KHỚP một đường CÓ THẬT (git theo dõi hoặc có trên đĩa).

        Với miễn trừ theo QUY TẮC, câu hỏi đổi thành: **mỗi VÙNG phải có thật** — một vùng bịa ra
        (`thu_khong_ton_tai/`) sẽ tha một thư mục chưa ai kiểm.
        """
        theo_doi = set(_git("ls-files").stdout.splitlines())
        self.assertGreater(len(theo_doi), 100, "`git ls-files` rỗng ⇒ ca này không đo gì")
        chet = []
        for m in PHAM_VI_WAVE:
            co = any(fnmatch.fnmatch(t, m) for t in theo_doi)
            if not co:
                co = bool(glob.glob(os.path.join(GOC_CAY, m)))
            if not co:
                chet.append(m)
        self.assertEqual(chet, [], f"miễn trừ MỤC RUỖNG (không khớp đường nào có thật): {chet}")
        _dc_am("cay-sach-muc-ruong")
        _dc_duong("cay-sach-muc-ruong")
        print(f"  [A1c] {len(PHAM_VI_WAVE)}/{len(PHAM_VI_WAVE)} VÙNG miễn trừ khớp đường có thật")

    def test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO(self):
        """ĐỐI CHỨNG ÂM BẮT BUỘC: sửa/tạo một tệp SẢN PHẨM ⇒ chốt "cây sạch" PHẢI ĐỎ.

        Bốn tầng, cố ý chồng nhau — một tầng xanh mà tầng khác đỏ thì ca này đỏ:
          (1) HÀM THUẦN: dòng porcelain của tệp sản phẩm không được lọc mất (kể cả dòng ĐỔI TÊN kéo
              tệp sản phẩm VÀO thư mục thử);
          (2) GIT THẬT trên CÂY TẠM: `app/webhook.py` bị sửa ⇒ cổng ĐỎ, còn khi chỉ tệp của vùng thử
              bẩn ⇒ cổng XANH (đối chứng DƯƠNG của chính phép đo);
          (3) GIT THẬT trên CÂY ĐANG ĐO: tệp mới trong `app/` ⇒ cổng ĐỎ; xoá ⇒ cổng XANH LẠI;
          (4) GIT THẬT trên CÂY ĐANG ĐO: tệp mới trong VÙNG THỬ ⇒ cổng vẫn XANH (đúng N-G19-03).
        Không tệp sản phẩm nào của cây thật bị sửa nội dung.
        """
        gia = [" M app/webhook.py", " M app/server.py", "?? mock/tep_moi.json", " M app/cau_hinh.py",
               "R  app/gioi_han.py -> thu_giao_dien/gioi_han.py"]
        self.assertEqual(_loc_cay_ban(gia, PHAM_VI_WAVE), gia,
                         "hàm lọc NUỐT tệp sản phẩm ⇒ cổng mất răng")
        self.assertEqual(_loc_cay_ban(["?? app/thu/thu_g21_chotcay.py"], PHAM_VI_WAVE), [],
                         "hàm lọc KHÔNG tha tệp của làn khác trong vùng thử ⇒ N-G19-03 tái diễn")
        self.assertEqual(_loc_cay_ban(gia), gia,
                         "`ngoai=()` phải là HÀM THUẦN (trả về MỌI dòng bẩn), không chính sách ẩn")

        tam = tempfile.mkdtemp(prefix="veh-g18-dc-am-")
        try:
            _git("init", "-q", goc=tam)
            for d in ("app/thu", "docs", "app"):
                os.makedirs(os.path.join(tam, d), exist_ok=True)
            for duong, noi_dung in (("app/webhook.py", "SAN PHAM\n"),
                                    ("app/thu/thu_g21_gia.py", "bo thu cua lan khac\n"),
                                    ("docs/G21_GIA.md", "tai lieu\n")):
                with open(os.path.join(tam, duong), "w", encoding="utf-8") as f:
                    f.write(noi_dung)
            _git("-c", "user.email=ag05@local", "-c", "user.name=AG05", "add", "-A", goc=tam)
            _git("-c", "user.email=ag05@local", "-c", "user.name=AG05",
                 "commit", "-q", "-m", "nen", goc=tam)
            mau_tam = chotcay.mau_vung_chuan(goc=tam)
            self.assertEqual(_loc_cay_ban(
                _git("status", "--porcelain=v1", "-uall", goc=tam).stdout.splitlines(), mau_tam), [],
                "cây tạm SẠCH mà cổng báo bẩn ⇒ phép đo hỏng")
            with open(os.path.join(tam, "app/thu/thu_g21_gia.py"), "a", encoding="utf-8") as f:
                f.write("them\n")
            self.assertEqual(_loc_cay_ban(
                _git("status", "--porcelain=v1", "-uall", goc=tam).stdout.splitlines(), mau_tam), [],
                "tệp của vùng thử làm cổng ĐỎ ⇒ N-G19-03 tái diễn")
            with open(os.path.join(tam, "app/webhook.py"), "a", encoding="utf-8") as f:
                f.write("SUA SAN PHAM\n")
            ban = _loc_cay_ban(_git("status", "--porcelain=v1", "-uall", goc=tam).stdout.splitlines(),
                               mau_tam)
            self.assertEqual(len(ban), 1, f"cổng MÙ với tệp sản phẩm bị sửa: {ban}")
            self.assertIn("app/webhook.py", ban[0])
        finally:
            shutil.rmtree(tam, ignore_errors=True)

        tam_that = os.path.join(GOC_APP, "_ag05_doi_chung_am_tam_g18.py")
        self.assertFalse(os.path.exists(tam_that), f"đường tạm đã tồn tại: {tam_that}")
        try:
            with open(tam_that, "w", encoding="utf-8") as f:
                f.write("# TỆP TẠM CỦA ĐỐI CHỨNG ÂM — bộ thử tự xoá, không phải mã sản phẩm\n")
            ban = _chot_do()
            self.assertIn("_ag05_doi_chung_am_tam_g18.py", " ".join(ban),
                          f"cổng MÙ với tệp mới trong `app/`: {ban}")
            self.assertIn("_ag05_doi_chung_am_tam_g18.py", ban[0])
        finally:
            if os.path.exists(tam_that):
                os.remove(tam_that)
        self.assertEqual(_chot_do(), [], "cây KHÔNG sạch lại sau khi xoá tệp tạm")

        trong_vung = os.path.join(THU_MUC_THU, "_ag05_doi_chung_duong_g18.py")
        self.assertFalse(os.path.exists(trong_vung), f"đường tạm đã tồn tại: {trong_vung}")
        try:
            with open(trong_vung, "w", encoding="utf-8") as f:
                f.write("# làn KHÁC giao tệp mới TRONG VÙNG THỬ — cổng PHẢI vẫn xanh\n")
            self.assertEqual(_chot_do(), [],
                             "tệp mới của làn khác trong vùng thử làm cổng ĐỎ ⇒ N-G19-03 tái diễn")
        finally:
            if os.path.exists(trong_vung):
                os.remove(trong_vung)

        _dc_am("cay-sach-doi-chung-am")
        _dc_duong("cay-sach-doi-chung-am")
        print("  [A1d] ĐỐI CHỨNG ÂM: tệp sản phẩm bị sửa/tạo ⇒ cổng ĐỎ ở CẢ 4 tầng; "
              "tệp của làn khác trong VÙNG THỬ ⇒ cổng vẫn XANH")

    def test_a2_head_dung_moc_do(self):
        head = _git("rev-parse", "HEAD").stdout.strip()
        if HEAD_GHIM:
            self.assertEqual(head, HEAD_GHIM, "HEAD KHÁC mốc đo đã ghim")
            _dc_am("ghim-head")
            _dc_duong("ghim-head")
        else:
            _dc_duong("ghim-head")
        print(f"  [A2] HEAD={head} · ghim={HEAD_GHIM or 'KHÔNG ĐẶT (chỉ ghi ra)'}")

    def test_a3_moi_lop_adapter_deu_CHO_PHEP_LIVE_False(self):
        mo = sorted(m for m, lop in adapter._DANG_KY.items() if getattr(lop, "CHO_PHEP_LIVE", False))
        self.assertGreaterEqual(len(adapter._DANG_KY), 2, "sổ đăng ký adapter RỖNG ⇒ ca này vô nghĩa")
        self.assertEqual(mo, [], f"có adapter MỞ LIVE: {mo}")
        _dc_am("live-khoa")
        # ĐỐI CHỨNG DƯƠNG: bộ dò PHẢI thấy được một lớp giả đã mở.
        gia = type("AdapterGiaLive", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live-g18"] = gia
        try:
            thay = [m for m, lop in adapter._DANG_KY.items() if getattr(lop, "CHO_PHEP_LIVE", False)]
        finally:
            adapter._DANG_KY.pop("gia-live-g18", None)
        self.assertEqual(thay, ["gia-live-g18"], "bộ dò MÙ với adapter MỞ LIVE")
        _dc_duong("live-khoa")
        print(f"\n  [A3] {len(adapter._DANG_KY)} lớp adapter · LIVE mở: 0 · bộ dò bắt được lớp giả")

    def test_a4_adapter_khong_co_duong_mang_that(self):
        cam = ("requests", "httpx", "urllib.request", "http.client", "socket")
        thay = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not (ten.startswith("adapter") and ten.endswith(".py")):
                continue
            for nut in ast.walk(ast.parse(_doc_app(ten))):
                if isinstance(nut, ast.Import):
                    thay += [f"{ten}: import {a.name}" for a in nut.names if a.name in cam]
                elif isinstance(nut, ast.ImportFrom) and (nut.module or "") in cam:
                    thay.append(f"{ten}: from {nut.module}")
        self.assertEqual(thay, [], f"adapter có đường mạng thật: {thay}")
        _dc_am("adapter-khong-mang")
        # ĐỐI CHỨNG DƯƠNG: bộ quét PHẢI bắt được mẫu tiêm vào.
        gia = ast.parse("import requests\nfrom urllib.request import urlopen\n")
        bat = [n.names[0].name for n in ast.walk(gia) if isinstance(n, ast.Import)]
        self.assertIn("requests", bat, "bộ quét AST MÙ với `import requests`")
        _dc_duong("adapter-khong-mang")

    def test_a5_nghiep_vu_van_SQLite(self):
        cam = ("psycopg", "psycopg2", "asyncpg", "pg8000", "mysql.connector", "pymysql")
        thay = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py"):
                continue
            for nut in ast.walk(ast.parse(_doc_app(ten))):
                if isinstance(nut, ast.Import):
                    thay += [f"{ten}: {a.name}" for a in nut.names if a.name.split(".")[0] in cam]
                elif isinstance(nut, ast.ImportFrom) and (nut.module or "").split(".")[0] in cam:
                    thay.append(f"{ten}: {nut.module}")
        self.assertEqual(thay, [], f"app/*.py import driver CSDL khác SQLite (D-8): {thay}")
        self.assertTrue(cau_hinh.DUONG_DAN_CSDL.endswith(".db"), "CSDL nghiệp vụ không phải tệp .db")
        _dc_am("sqlite-d8")
        _dc_duong("sqlite-d8")

    def test_a6_khong_co_luot_ket_noi_ra_ngoai_loopback(self):
        """Bộ đếm socket: mọi `connect` trong lượt đo phải là loopback."""
        ra_ngoai = []
        goc = socket.socket.connect

        def _dem(self, dia_chi, *a, **k):
            if isinstance(dia_chi, tuple) and dia_chi and dia_chi[0] not in ("127.0.0.1", "::1", "localhost"):
                ra_ngoai.append(dia_chi)
            return goc(self, dia_chi, *a, **k)

        mt = moi_truong()
        socket.socket.connect = _dem
        try:
            goi("/api/v2/auth/toi", mt["a_owner"])
            goi("/api/v2/don", mt["a_owner"])
        finally:
            socket.socket.connect = goc
        self.assertEqual(ra_ngoai, [], f"có lượt connect RA NGOÀI loopback: {ra_ngoai[:5]}")
        _dc_am("khong-ra-ngoai")
        # ĐỐI CHỨNG DƯƠNG: bộ đếm PHẢI đếm được một lượt loopback thật, nếu không nó chết lặng.
        dem = []
        socket.socket.connect = lambda self, dc, *a, **k: (dem.append(dc), goc(self, dc, *a, **k))[1]
        try:
            goi("/api/v2/auth/toi", mt["a_owner"])
        finally:
            socket.socket.connect = goc
        self.assertTrue(dem, "bộ đếm socket KHÔNG thấy lượt loopback nào ⇒ nó không đo gì")
        _dc_duong("khong-ra-ngoai")

    def test_a7_cum_5432_khong_bi_dung_toi(self):
        """Vân tay cụm PostgreSQL hệ thống giữ `vip_customs*` — TRƯỚC = SAU."""
        global VAN_TAY_5432_LUC_NAN
        VAN_TAY_5432_LUC_NAN = _van_tay_5432()
        if VAN_TAY_5432_LUC_NAN is None:
            self.skipTest("CHƯA ĐO: không đọc được vân tay cụm :5432 (thiếu psql/lsof)")
        self.assertTrue(VAN_TAY_5432_LUC_NAN.get("truy_cap_duoc"),
                        f"không truy cập được cụm :5432: {VAN_TAY_5432_LUC_NAN.get('ghi_chu')}")
        self.assertEqual(VAN_TAY_5432_LUC_NAN.get("so_csdl"), 6,
                         "cụm :5432 đổi số CSDL — dừng ngay để người đọc biết")
        for csdl_cam in ("vip_customs", "vip_customs_g16", "vip_customs_test"):
            self.assertIn(csdl_cam, VAN_TAY_5432_LUC_NAN["danh_sach_csdl"],
                          f"CSDL {csdl_cam} KHÔNG còn trong cụm :5432 (đã bị đụng tới?)")
        _dc_am("5432-khong-dung")
        _dc_duong("5432-khong-dung")
        print(f"\n  [A7] cụm :5432 pid={VAN_TAY_5432_LUC_NAN['pid']} · "
              f"{VAN_TAY_5432_LUC_NAN['so_csdl']} CSDL: {', '.join(VAN_TAY_5432_LUC_NAN['danh_sach_csdl'])}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. §5.4 QA_G17 — TẦNG 3: DOM/CSS TRONG CHROMIUM THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _pw_browsers():
    """Thư mục nhị phân Playwright dùng được, hoặc None (kèm lý do).

    `VIP_G18_PW_BROWSERS` nếu ĐƯỢC ĐẶT thì là ý chí của người chạy: KHÔNG được lặng lẽ quay
    về đường mặc định khi thư mục đó rỗng — đó là cách một đối chứng âm trở thành xanh giả.
    """
    rieng = os.environ.get("VIP_G18_PW_BROWSERS", "")
    ung_vien = ([("VIP_G18_PW_BROWSERS", rieng)] if rieng else
                [("chỉ định BAN_GIAO §1", PW_BROWSERS_CHI_DINH), ("trong repo", PW_BROWSERS_REPO)])
    for ten, duong in ung_vien:
        if duong and os.path.isdir(duong):
            for con in sorted(os.listdir(duong)):
                if con.startswith("chromium_headless_shell-") or con.startswith("chromium-"):
                    return duong, ten, con
    return None, None, None


def do_tang_3(giay=300):
    """Chạy tầng 3 ĐÚNG khuôn `thu_giao_dien/chay.sh`, chỉ khác ĐƯỜNG nhị phân Chromium.

    `chay.sh` ghim `PLAYWRIGHT_BROWSERS_PATH=0` (tức `node_modules/playwright-core/.local-browsers`)
    và worktree này THIẾU thư mục đó; bản chỉ định của `BAN_GIAO.md` §1 có đúng bản 1194 khớp
    `playwright-core 1.56.1`. Không dùng cache hệ thống `~/Library/Caches/ms-playwright`.
    """
    pw, nguon, ban = _pw_browsers()
    if pw is None:
        return None, None, "không có thư mục nhị phân Chromium"
    nen = tempfile.mkdtemp(prefix="veh-g18-gd-")
    cong = _cong_ranh()
    env = dict(os.environ, VIP_HUB_DATA=nen, PLAYWRIGHT_BROWSERS_PATH=pw)
    pid = None
    try:
        for lenh, nhan in ((["python3", "app/migrate.py"], "migrate"),
                           (["python3", "app/khoi_tao.py"], "khoi_tao"),
                           (["python3", "thu_giao_dien/chuan_bi.py", "mk"], "chuan_bi-mk")):
            ma, ra, _ = _chay(lenh, env=env, giay=180)
            if ma != 0:
                return ma, f"[{nhan} hỏng] " + ra[-800:], nguon
        # Log máy chủ ra TỆP, KHÔNG qua ống: máy chủ ghi một dòng JSON mỗi lượt HTTP, ống đầy
        # (64KB) thì nó CHẶN ở lệnh ghi ⇒ mọi lượt sau treo tới hết timeout. Lượt đo đầu của
        # tôi vấp đúng cái này và nó suýt thành "5 ca hỏng của sản phẩm" — sự thật là 5 ca hỏng
        # của BÀN ĐO. `thu_giao_dien/chay.sh` cũng ghi ra tệp vì đúng lý do đó.
        log_sv = open(os.path.join(nen, "server.log"), "w")
        sv = subprocess.Popen([sys.executable, "app/server.py", str(cong)], cwd=GOC_CAY,
                              env=env, stdout=log_sv, stderr=subprocess.STDOUT, text=True)
        pid = sv.pid
        for _ in range(80):
            try:
                socket.create_connection(("127.0.0.1", cong), 0.3).close()
                break
            except OSError:
                time.sleep(0.25)
        goc_url = f"http://127.0.0.1:{cong}"
        ma, ra, _ = _chay(["python3", "thu_giao_dien/chuan_bi.py", "don", goc_url], env=env, giay=180)
        if ma != 0:
            return ma, "[chuan_bi-don hỏng] " + ra[-800:], nguon
        ma, ra, _ = _chay([os.path.join(GOC_CAY, "node_modules", ".bin", "playwright"),
                           "test"], env=dict(env, VIP_GD_GOC=goc_url, VIP_GD_NEN=nen), giay=giay)
        return ma, ra, nguon
    finally:
        if pid:
            try:
                os.kill(pid, 15)
            except OSError:
                pass
        shutil.rmtree(nen, ignore_errors=True)


def _dem_playwright(ra):
    """Đếm kết quả Playwright: (đạt, hỏng, bỏ qua)."""
    def _so(mau):
        m = re.findall(mau, ra)
        return int(m[-1]) if m else 0
    return (_so(r"(\d+) passed"), _so(r"(\d+) failed"), _so(r"(\d+) (?:skipped|did not run)"))


class B_Tang3(unittest.TestCase):
    """§5.4 QA_G17 — tầng 3 Chromium. Cổng: `failed == 0` VÀ `passed > 0`."""

    def test_b1_tang_3_chay_duoc_va_khong_co_ca_hong(self):
        if os.environ.get("VIP_G18_BO_TANG3") == "1":
            # Đường TẮT phải NÓI RA: bộ chạy chung không được phép phụ thuộc Chromium một cách
            # im lặng. Ai tắt thì phán quyết là BỎ QUA (lỗ hổng phạm vi), KHÔNG BAO GIỜ là ĐẠT.
            self.skipTest("CHƯA ĐO: người chạy cố ý tắt bằng VIP_G18_BO_TANG3=1")
        pw, nguon, ban = _pw_browsers()
        if pw is None:
            self.skipTest("CHƯA ĐO: thiếu nhị phân Chromium (xem docs/QA_G18.md §'CHƯA ĐO')")
        ma, ra, nguon = do_tang_3()
        duong = _ghi_log("tang3.log", ma, ra)
        dat, hong, bo = _dem_playwright(ra)
        print(f"\n  [B1] nhị phân: {nguon} ({ban}) · mã thoát={ma} · {dat} đạt · {hong} hỏng · {bo} bỏ qua"
              f" · log={duong}")
        self.assertEqual(ma, 0, f"tầng 3 KHÔNG đạt (mã thoát {ma}) — log: {duong}")
        self.assertEqual(hong, 0, f"tầng 3 có {hong} ca HỎNG — log: {duong}")
        self.assertGreater(dat, 0, f"tầng 3 chạy 0 ca mà vẫn xanh — log: {duong}")
        _dc_am("tang3")
        _dc_duong("tang3")
        self._dat, self._hong, self._bo = dat, hong, bo

    def test_b2_tang_3_CO_RANG_khi_thieu_nhi_phan(self):
        """ĐỐI CHỨNG ÂM cho B1: trỏ vào thư mục nhị phân RỖNG ⇒ tầng 3 PHẢI đỏ."""
        rong = tempfile.mkdtemp(prefix="veh-g18-pw-rong-")
        try:
            gia = dict(os.environ, VIP_G18_PW_BROWSERS=rong)
            ma, ra, _ = _chay([sys.executable, "-c",
                               "import os,sys; sys.path.insert(0,'app/thu');"
                               "import thu_qa_g18 as q;"
                               "print('PW=%r' % (q._pw_browsers()[0],))"],
                              env=gia, giay=120)
            self.assertIn("PW=None", ra,
                          f"bộ dò nhị phân KHÔNG thấy chỗ rỗng ⇒ nó không đo gì: {ra[-300:]}")
            # và `chay.sh` nguyên bản (ghim đường trong repo) phải ĐỎ vì lý do MÔI TRƯỜNG:
            if not os.path.isdir(PW_BROWSERS_REPO):
                ma2, ra2, _ = _chay(["sh", "thu_giao_dien/chay.sh"], giay=180)
                _ghi_log("tang3_chaysh_nguyenban.log", ma2, ra2)
                self.assertNotEqual(ma2, 0, "`chay.sh` nguyên bản lại xanh dù thiếu nhị phân?!")
                self.assertIn("Executable doesn't exist", ra2,
                              f"`chay.sh` đỏ vì lý do KHÁC môi trường — phải đọc lại: {ra2[-500:]}")
                print(f"\n  [B2] `sh thu_giao_dien/chay.sh` nguyên bản → mã thoát {ma2}, "
                      f"lý do: thiếu nhị phân Chromium (ĐỎ do MÔI TRƯỜNG, không phải do sản phẩm)")
            _dc_am("tang3-rang")
            _dc_duong("tang3-rang")
        finally:
            shutil.rmtree(rong, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. §5.3 QA_G17 — HARNESS SANDBOX AG-04 (`trien_khai/g16/**`)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def do_harness_g16(giay=600):
    """Chạy harness AG-04 trên nền tạm + tự kiểm bộ dò chốt an toàn của chính nó."""
    tu_kiem = _chay(["python3", "trien_khai/g16/chot_an_toan.py", "--tu-kiem"], giay=120)
    nen = tempfile.mkdtemp(prefix="veh-g18-g16-")
    try:
        ma, ra, _ = _chay(["sh", "trien_khai/g16/chay_harness.sh"],
                          env={"VIP_HUB_DATA": nen}, giay=giay)
        return tu_kiem, (ma, ra)
    finally:
        shutil.rmtree(nen, ignore_errors=True)


class C_HarnessG16(unittest.TestCase):
    """§5.3 QA_G17 — mục *"AG-01 chưa nghiệm thu"* của `G16_ACCEPTANCE.md` §8.5."""

    def test_c1_bo_do_chot_an_toan_tu_kiem_dat(self):
        ma, ra, _ = _chay(["python3", "trien_khai/g16/chot_an_toan.py", "--tu-kiem"], giay=120)
        _ghi_log("g16_chot_an_toan_tu_kiem.log", ma, ra)
        self.assertEqual(ma, 0, f"tự kiểm chốt an toàn HỎNG (mã thoát {ma}): {ra[-500:]}")
        so_ca = re.findall(r"(\d+) cấu hình tổng hợp", ra)
        self.assertTrue(so_ca, "tự kiểm không nêu số cấu hình — phải đọc lại")
        self.assertGreaterEqual(int(so_ca[-1]), 9, "tự kiểm chạy quá ít cấu hình")
        _dc_am("chot-an-toan-g16")
        _dc_duong("chot-an-toan-g16")
        print(f"\n  [C1] `chot_an_toan.py --tu-kiem` → mã thoát {ma} "
              f"({so_ca[-1]} cấu hình tổng hợp, bắt đúng cả 9 ca hỏng lẫn ca đủ chốt)")

    def test_c2_harness_chay_het_va_hai_chang_cham_hang_la_BLOCKED(self):
        (ma_tk, ra_tk, _), (ma, ra) = do_harness_g16()
        duong = _ghi_log("g16_harness.log", ma, ra)
        print(f"\n  [C2] `sh trien_khai/g16/chay_harness.sh` → mã thoát {ma} · log={duong}")
        self.assertEqual(ma_tk, 0, f"tự kiểm chốt hỏng: {ra_tk[-300:]}")
        self.assertEqual(ma, 0, f"harness AG-04 HỎNG (mã thoát {ma}) — log: {duong}")
        for giay_phep in ("V-G09-01", "V-13906-05"):
            self.assertIn(giay_phep, ra, f"chặng chạm hãng KHÔNG nêu đúng giấy phép {giay_phep}")
        self.assertIn("BLOCKED", ra, "không thấy phán quyết BLOCKED cho chặng chạm hãng")
        self.assertIn("sáu chốt an toàn: ĐỦ", ra, "harness không xác nhận đã qua sáu chốt an toàn")
        _dc_am("harness-g16")
        _dc_duong("harness-g16")

    def test_c3_harness_TU_CHOI_chay_ngoai_thu_muc_tam(self):
        """ĐỐI CHỨNG ÂM: nền KHÔNG phải thư mục tạm ⇒ harness PHẢI từ chối, KHÔNG tạo gì."""
        khong_tam = os.path.join(os.path.expanduser("~"), ".veh-g18-phai-tu-choi", "g16_harness")
        self.assertFalse(os.path.exists(khong_tam), f"đường thử đã tồn tại sẵn: {khong_tam}")
        ma, ra, _ = _chay(["python3", "trien_khai/g16/harness_nghiem_thu.py"],
                          env={"VIP_HUB_DATA": khong_tam}, giay=180)
        _ghi_log("g16_tu_choi.log", ma, ra)
        self.assertNotEqual(ma, 0, "harness CHẠY được trên nền NGOÀI thư mục tạm")
        self.assertIn("TỪ CHỐI CHẠY", ra, f"không thấy lời từ chối: {ra[-400:]}")
        self.assertFalse(os.path.exists(khong_tam), "harness đã GHI ra ngoài thư mục tạm")
        _dc_am("harness-g16-tu-choi")
        _dc_duong("harness-g16-tu-choi")
        print(f"\n  [C3] nền ngoài thư mục tạm ⇒ thoát {ma}, KHÔNG tạo gì ở {khong_tam}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. §5.5 QA_G17 — ĐA TIẾN TRÌNH THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
SO_TT = "8" if DAY_DU else os.environ.get("VIP_G18_SO_TT", "8")
SO_PHEP = "400" if DAY_DU else os.environ.get("VIP_G18_SO_PHEP", "400")


class D_DongThoi(unittest.TestCase):
    """§5.5 QA_G17 — `app/thu/dong_thoi/chay.py`, 8 tiến trình × 400 phép × 3 ca."""

    def test_d1_ban_do_dong_thoi_8_tien_trinh_dat(self):
        ma, ra, giay = _chay(["python3", "app/thu/dong_thoi/chay.py"],
                             env={"VIP_SO_TT": SO_TT, "VIP_SO_PHEP": SO_PHEP}, giay=1200)
        duong = _ghi_log("dong_thoi.log", ma, ra)
        print(f"\n  [D1] `python3 app/thu/dong_thoi/chay.py` ({SO_TT} tiến trình × {SO_PHEP} phép)"
              f" → mã thoát {ma} · {giay:.1f}s · log={duong}")
        self.assertEqual(ma, 0, f"bàn đo đồng thời HỎNG (mã thoát {ma}) — log: {duong}")
        for khoa in ("SỔ CÁI", "ĐỌC–SỬA–GHI", "HẠN MỨC"):
            self.assertIn(khoa, ra, f"bàn đo không chạy ca {khoa}")
        _dc_am("dong-thoi")
        _dc_duong("dong-thoi")

    def test_d2_ban_do_dong_thoi_CO_RANG_khi_mat_ghi(self):
        """ĐỐI CHỨNG ÂM: cây sao chép bị tiêm 'mất ghi' ⇒ bàn đo PHẢI đỏ."""
        cay = _cay_sao_chep()
        duong = os.path.join(cay, "thu", "dong_thoi", "nguoi_chay.py")
        with open(duong, encoding="utf-8") as f:
            nguon = f.read()
        cu = ('            tai_chinh.ghi_but_toan(TENANT, "cod_hang_bao_thu", 1000, "nguoi",\n'
              '                                   f"{NHAN}#{i}")\n')
        self.assertIn(cu, nguon, "không tiêm được đột biến: mẫu đã đổi")
        with open(duong, "w", encoding="utf-8") as f:
            f.write(nguon.replace(cu, ""))
        ma, ra, _ = _chay(["python3", os.path.join(cay, "thu", "dong_thoi", "chay.py")],
                          env={"VIP_SO_TT": "4", "VIP_SO_PHEP": "60"}, giay=600)
        print(f"\n  [D2] cây bị tiêm 'mất ghi' ⇒ mã thoát {ma} (phải KHÁC 0)")
        self.assertNotEqual(ma, 0, "bàn đo đồng thời KHÔNG bắt được mất ghi ⇒ cổng D1 không có răng")
        _dc_am("dong-thoi-rang")
        _dc_duong("dong-thoi-rang")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. §5.6 QA_G17 — MA TRẬN GHI `(cửa × POST/PUT/DELETE)`
# ══════════════════════════════════════════════════════════════════════════════════════════════
class E_MaTranGhi(unittest.TestCase):

    def test_e1_bo_dem_cua_ghi_rong_du_lon(self):
        """Tự kiểm phép rút cửa: rỗng ⇒ mọi ca dưới đây xanh vô nghĩa."""
        tinh, dong = duong_ghi_tinh(), duong_ghi_dong()
        self.assertGreaterEqual(len(tinh), 15, f"rút được quá ít cửa ghi TĨNH: {tinh}")
        self.assertGreaterEqual(len(dong), 8, f"rút được quá ít cửa ghi có THAM SỐ: {dong}")
        _dc_duong("ma-tran-ghi")
        print(f"\n  [E1] rút từ server.py: {len(tinh)} cửa ghi tĩnh · {len(dong)} cửa ghi có tham số")

    def test_e2_khong_phien_thi_MOI_cua_ghi_tra_401(self):
        kq = do_unauth_ghi()
        self.assertGreater(kq["tong"], 0, "phép quét không gửi lượt nào")
        self.assertEqual(kq["khong_401"], [],
                         f"cửa ghi trả mã KHÁC 401 khi KHÔNG có phiên: {kq['khong_401'][:8]}")
        _dc_am("ghi-khong-phien")
        print(f"\n  [E2] {kq['tong']} lượt ghi không phiên · mã trả về: {kq['dem']} · khác 401: 0")

    def test_e3_doi_chung_duong_ghi_khong_phien(self):
        """ĐỐI CHỨNG DƯƠNG: cùng cửa đó, CÓ chủ hợp lệ, phải đi qua được (không 401)."""
        mt = moi_truong()
        ma, kq, _ = goi("/api/v2/khach-hang", mt["a_owner"], method="POST",
                        body={"ten": f"Khach doi chung {mt['duoi']}"})
        self.assertIn(ma, (200, 201), f"chủ hợp lệ vẫn bị chặn: {ma} {kq}")
        _dc_duong("ghi-khong-phien")
        print(f"  [E3] đối chứng dương: POST /api/v2/khach-hang bằng chủ hợp lệ → {ma}")

    def test_e4_thieu_X_Requested_With_thi_403(self):
        kq = do_csrf()
        self.assertEqual(kq["thieu_header"], 403,
                         f"lượt ghi thiếu header chống CSRF trả {kq['thieu_header']}, không phải 403")
        self.assertIn(kq["co_header"], (200, 201),
                      f"đối chứng dương hỏng: có header vẫn {kq['co_header']}")
        _dc_am("csrf")
        _dc_duong("csrf")
        print(f"\n  [E4] thiếu X-Requested-With → {kq['thieu_header']} · có header → {kq['co_header']}")

    def test_e5_B_khong_doi_duoc_membership_cua_A(self):
        mt = moi_truong()
        kq = do_ghi_cheo_membership()
        self.assertEqual(kq["con_nguyen"], True, f"B ĐÃ ĐỔI được membership của A: {kq}")
        self.assertNotIn(kq["ma_b"], (200, 201), f"B ghi được membership của A: mã {kq['ma_b']}")
        self.assertIn(kq["ma_a"], (200, 201), f"đối chứng dương (chủ A) hỏng: {kq}")
        _dc_am("ghi-cheo")
        _dc_duong("ghi-cheo")
        print(f"\n  [E5] B đổi membership của A → {kq['ma_b']} (dữ liệu A còn nguyên) · "
              f"chủ A → {kq['ma_a']}")

    def _cheo(self, nhan, method, duong, body, doc=None):
        """Một phép ghi chéo: đối chứng dương bằng chủ A TRƯỚC, rồi B thử, rồi so dữ liệu."""
        mt = moi_truong()
        ma_a, kq_a, _ = goi(duong, mt["a_owner"], method=method, body=body)
        self.assertIn(ma_a, (200, 201),
                      f"{nhan}: ĐỐI CHỨNG DƯƠNG hỏng (chủ A nhận {ma_a}: {kq_a}) ⇒ ca âm vô nghĩa")
        truoc = doc() if doc else None
        ma_b, _, tho_b = goi(duong, mt["b_owner"], method=method, body=body)
        self.assertNotIn(ma_b, (200, 201), f"{nhan}: B GHI ĐƯỢC ({ma_b})")
        self.assertNotIn(mt["canary"], tho_b, f"{nhan}: phản hồi cho B rò canary của A")
        if doc:
            self.assertEqual(doc(), truoc, f"{nhan}: B ĐÃ ĐỔI dữ liệu của A")
        _dc_am("ghi-cheo")
        _dc_duong("ghi-cheo")
        print(f"  [E5] {nhan}: chủ A → {ma_a} · B → {ma_b} · dữ liệu A nguyên vẹn")

    def test_e6_B_khong_khoa_duoc_tai_khoan_hang_cua_A(self):
        mt = moi_truong()
        acc = mt["acc_a"]["vtp"]

        def _tt():
            return dict(csdl.mot("SELECT kich_hoat, credentials_ma_hoa FROM carrier_accounts WHERE id=?",
                                 (acc,)))

        self._cheo("khoá tài khoản hãng", "POST", f"/api/v2/tai-khoan-hang/{acc}/khoa", {}, _tt)

    def test_e7_B_khong_huy_duoc_don_cua_A(self):
        mt = moi_truong()
        don_a = tao_don(mt["a_owner"])
        self.assertIsNotNone(don_a, "không tạo được đơn của A ⇒ ca này vô nghĩa")
        don_x = tao_don(mt["a_owner"])
        self.assertIsNotNone(don_x, "không tạo được đơn đối chứng")
        # đối chứng dương trên đơn DÙNG MỘT LẦN (don_x), để đơn được canh (don_a) còn nguyên
        ma_a, _, _ = goi(f"/api/v2/don/{don_x}/huy", mt["a_owner"], method="POST", body={})
        self.assertIn(ma_a, (200, 201), f"đối chứng dương huỷ đơn hỏng: {ma_a}")

        def _tt():
            return dict(csdl.mot("SELECT trang_thai FROM don_hang WHERE id=?", (don_a,)))

        truoc = _tt()
        ma_b, _, tho_b = goi(f"/api/v2/don/{don_a}/huy", mt["b_owner"], method="POST", body={})
        self.assertNotIn(ma_b, (200, 201), f"B HUỶ ĐƯỢC đơn của A ({ma_b})")
        self.assertNotIn(mt["canary"], tho_b, "phản hồi cho B rò canary của A")
        self.assertEqual(_tt(), truoc, "B ĐÃ ĐỔI trạng thái đơn của A")
        _dc_am("ghi-cheo")
        _dc_duong("ghi-cheo")
        print(f"  [E7] huỷ đơn: chủ A → {ma_a} · B → {ma_b} · đơn của A nguyên trạng thái")

    def test_e8_B_khong_dat_duoc_don_vao_tenant_A(self):
        """Tham số `tenant_id` do kẻ gọi TỰ KHAI không được đổi chủ sở hữu dữ liệu."""
        mt = moi_truong()
        truoc = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (mt["tid_a"],))["c"]
        ma, kq, _ = goi("/api/v2/don", mt["b_owner"], method="POST",
                        body=dict(DON_MAU, tenant_id=mt["tid_a"], nguoi_nhan_ten="gán-tenant"))
        self.assertIn(ma, (200, 201), f"đối chứng dương hỏng: B không tạo nổi đơn cho chính B ({ma})")
        don_id = kq["don"]["id"]
        chu = csdl.mot("SELECT tenant_id FROM don_hang WHERE id=?", (don_id,))["tenant_id"]
        self.assertEqual(chu, mt["tid_b"], f"đơn của B lại mang tenant_id={chu} (A={mt['tid_a']})")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (mt["tid_a"],))["c"],
                         truoc, "số đơn của A ĐỔI sau lượt ghi của B")
        _dc_am("ghi-cheo")
        _dc_duong("ghi-cheo")
        print(f"  [E8] B khai tenant_id=A khi tạo đơn → đơn vẫn thuộc B ({chu}); đơn của A: {truoc} → không đổi")

    def test_e9_ghi_cheo_moi_cua_tham_so_khong_2xx(self):
        """Lưới rộng: MỌI cửa ghi có tham số, B thử với id của A (hoặc id=1) → không 2xx."""
        mt = moi_truong()
        xau = []
        for mau in duong_ghi_dong():
            if mau.startswith("/api/v2/platform/") or mau.startswith("/api/v2/webhook/nhan"):
                continue
            duong = re.sub(r"\(.*?\)", "1", mau)
            for method in ("POST", "PUT", "DELETE"):
                ma, _, tho = goi(duong, mt["b_owner"], method=method, body={"role": "TENANT_VIEWER"})
                if ma in (200, 201) or mt["canary"] in tho:
                    xau.append(f"{method} {duong} -> {ma}")
        self.assertEqual(xau, [], f"cửa ghi có tham số để B lọt: {xau}")
        _dc_am("ghi-cheo-luoi-rong")
        # ĐỐI CHỨNG DƯƠNG: lưới này PHẢI chạm được cửa thật — chủ A trên một cửa trong lưới.
        # Dùng membership CỦA NHÂN VIÊN A (không phải của chủ): hàng của TENANT_OWNER bị
        # chặn 403 theo thiết kế (`server.py` dòng 762) — đó là ĐÚNG, không phải lỗi.
        ma_a, _, _ = goi(f"/api/v2/memberships/{mt['mem_a']}", mt["a_owner"], method="POST", body={})
        self.assertNotIn(ma_a, (401, 403), f"chủ hợp lệ bị chặn ở cửa trong lưới: {ma_a}")
        _dc_duong("ghi-cheo-luoi-rong")
        print(f"\n  [E9] lưới rộng: {len(duong_ghi_dong())} cửa ghi có tham số · B lọt: 0")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# F. §5.7 QA_G17 — MẶT PHẲNG `/api/v2/platform/*`
# ══════════════════════════════════════════════════════════════════════════════════════════════
class F_PlaneNenTang(unittest.TestCase):

    def test_f1_phien_tenant_khong_vao_duoc_plane_nen_tang(self):
        ds = duong_platform()
        self.assertGreaterEqual(len(ds), 4, f"rút được quá ít cửa platform: {ds}")
        kq = do_platform_chan()
        self.assertEqual(kq["khong_403"], [],
                         f"phiên tenant KHÔNG bị 403 ở cửa platform: {kq['khong_403'][:8]}")
        _dc_am("plane-nen-tang")
        print(f"\n  [F1] {kq['tong']} lượt ({len(ds)} cửa platform) bằng phiên tenant · "
              f"mã: {kq['dem']} · không-403: 0")

    def test_f2_doi_chung_duong_platform_admin_di_qua_duoc(self):
        mt = moi_truong()
        ma, kq, _ = goi("/api/v2/platform/tenants", mt["pl_admin"])
        self.assertEqual(ma, 200, f"PLATFORM_ADMIN không đọc nổi danh sách tenant ({ma}: {kq})")
        self.assertIn("tenants", kq, "phản hồi không có khoá `tenants`")
        _dc_duong("plane-nen-tang")
        print(f"  [F2] đối chứng dương: PLATFORM_ADMIN GET /api/v2/platform/tenants → 200 "
              f"({len(kq['tenants'])} tenant)")

    def test_f3_platform_admin_KHONG_tao_duoc_tenant(self):
        """Ma trận quyền nền tảng: `PLATFORM_ADMIN` KHÔNG có `platform.tenant.tao`."""
        mt = moi_truong()
        self.assertFalse(quyen.co_quyen("PLATFORM_ADMIN", "platform.tenant.tao"),
                         "ma trận quyền đã đổi: PLATFORM_ADMIN nay có quyền tạo tenant")
        ma, _, _ = goi("/api/v2/platform/tenants", mt["pl_admin"], method="POST",
                       body={"ten": f"QA G18 {mt['duoi']}", "owner_ten_dang_nhap": "qa18-x",
                             "owner_mat_khau": "mat-khau-thu-123"})
        self.assertEqual(ma, 403, f"PLATFORM_ADMIN tạo được tenant (mã {ma})")
        truoc = csdl.mot("SELECT COUNT(*) c FROM tenants")["c"]
        ma2, kq2, _ = goi("/api/v2/platform/tenants", mt["pl_owner"], method="POST",
                          body={"ten": f"QA G18 {mt['duoi']}", "owner_ten_dang_nhap": "qa18-x",
                                "owner_mat_khau": "mat-khau-thu-123"})
        self.assertEqual(ma2, 201, f"đối chứng dương hỏng: PLATFORM_OWNER không tạo được tenant ({ma2}: {kq2})")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM tenants")["c"], truoc + 1,
                         "PLATFORM_OWNER tạo tenant mà CSDL không tăng")
        _dc_am("quyen-nen-tang")
        _dc_duong("quyen-nen-tang")
        print(f"\n  [F3] PLATFORM_ADMIN POST /platform/tenants → {ma} · PLATFORM_OWNER → {ma2} (CSDL +1)")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# G. §5.8 QA_G17 — HAI TẦNG FRONTEND (56 + 36 ca)
# ══════════════════════════════════════════════════════════════════════════════════════════════
class G_HaiTangFE(unittest.TestCase):
    """§5.8 QA_G17 — AG-01 G17 để hai tầng này cho bộ chạy chung, không đo độc lập."""

    def test_g1_tang_1_node_logic_dat_va_khong_teo_ca(self):
        if shutil.which("node") is None:
            self.skipTest("CHƯA ĐO: không có `node` trên PATH")
        ma, ra, giay = _chay(["node", "--test", "thu_frontend/thu_logic.mjs"], giay=300)
        duong = _ghi_log("fe_tang1.log", ma, ra)
        # `node --test` (v26) in `ℹ pass 56`; bản cũ in `# pass 56` — nhận CẢ HAI.
        dat = int((re.findall(r"^[#ℹ] pass (\d+)", ra, re.M) or ["0"])[-1])
        hong = int((re.findall(r"^[#ℹ] fail (\d+)", ra, re.M) or ["0"])[-1])
        print(f"\n  [G1] `node --test thu_frontend/thu_logic.mjs` → mã thoát {ma} · "
              f"{dat} đạt · {hong} hỏng · {giay:.1f}s · log={duong}")
        self.assertEqual(ma, 0, f"tầng 1 HỎNG (mã thoát {ma}) — log: {duong}")
        self.assertEqual(hong, 0, f"tầng 1 có {hong} ca hỏng")
        self.assertGreaterEqual(dat, 56, f"tầng 1 TEO CA: {dat} < 56 (số đã đo ở G12/G17)")
        _dc_am("fe-tang1")
        _dc_duong("fe-tang1")

    def test_g2_tang_2_http_dat_va_khong_teo_ca(self):
        ma, ra, giay = _chay(["python3", "thu_frontend/thu_http.py"], giay=300)
        duong = _ghi_log("fe_tang2.log", ma, ra)
        so = _so_ca(ra)
        print(f"\n  [G2] `python3 thu_frontend/thu_http.py` → mã thoát {ma} · {so} ca · "
              f"{giay:.1f}s · log={duong}")
        self.assertEqual(ma, 0, f"tầng 2 HỎNG (mã thoát {ma}) — log: {duong}")
        self.assertGreaterEqual(so, 36, f"tầng 2 TEO CA: {so} < 36 (số đã đo ở G12/G17)")
        _dc_am("fe-tang2")
        _dc_duong("fe-tang2")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# H. §5.9 QA_G17 — V11 POSTGRESQL TRÊN CỤM RIÊNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
class H_Postgres(unittest.TestCase):

    def test_h1_khong_con_cum_thu_nao_mo_cong_55432(self):
        r = subprocess.run(["lsof", "-iTCP:55432", "-sTCP:LISTEN"], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.stdout.strip(), "", f"còn cụm thử mở cổng 55432: {r.stdout.strip()}")
        _dc_am("postgres-cum-rieng")
        _dc_duong("postgres-cum-rieng")
        print("\n  [H1] `lsof -iTCP:55432 -sTCP:LISTEN` → rỗng (không cụm thử nào còn sót)")

    def test_h2_TU_CHOI_cong_5432_chay_that(self):
        """ĐỐI CHỨNG ÂM quan trọng nhất: trỏ CẢ bộ thử vào cổng :5432 ⇒ phải TỪ CHỐI."""
        truoc = _van_tay_5432()
        ma, ra, _ = _chay(["python3", "app/thu/thu_postgres.py"], env={"VHPG_CONG": "5432"}, giay=300)
        duong = _ghi_log("postgres_5432_tu_choi.log", ma, ra)
        self.assertNotEqual(ma, 0, f"bộ thử PostgreSQL CHẠY trên cổng :5432 mà vẫn thoát 0 — log: {duong}")
        self.assertIn("TỪ CHỐI", ra, f"không thấy lời từ chối cổng :5432: {ra[-400:]}")
        self.assertIn("5432", ra, "lời từ chối không nêu cổng")
        sau = _van_tay_5432()
        if truoc and sau:
            self.assertEqual(truoc, sau, "cụm :5432 ĐỔI sau lượt thử trỏ vào nó")
        _dc_am("postgres-5432")
        _dc_duong("postgres-5432")
        print(f"\n  [H2] `VHPG_CONG=5432 python3 app/thu/thu_postgres.py` → mã thoát {ma} "
              f"(từ chối thật) · vân tay :5432 trước = sau")

    def test_h3_chay_tron_tren_cum_rieng(self):
        if not DAY_DU:
            # Làn này TỐN THỜI và đã được chạy TRỌN ở ngoài (xem docs/QA_G18.md §V11).
            # Không im lặng bỏ qua: in ra vì sao, và vẫn kiểm chốt cổng :5432 ở H2.
            print("\n  [H3] làn TRỌN `thu_postgres.py` chỉ chạy khi VIP_G18_DAY_DU=1 — "
                  "số đo đầy đủ nằm ở docs/QA_G18.md §V11")
            self.skipTest("CHƯA ĐO trong làn mặc định: bật VIP_G18_DAY_DU=1 để chạy trọn")
        ma, ra, giay = _chay(["python3", "app/thu/thu_postgres.py"], giay=900)
        duong = _ghi_log("postgres_tron.log", ma, ra)
        print(f"\n  [H3] `python3 app/thu/thu_postgres.py` → mã thoát {ma} · {_so_ca(ra)} ca · "
              f"{_so_skip(ra)} bỏ qua · {giay:.1f}s · log={duong}")
        self.assertEqual(ma, 0, f"bộ thử PostgreSQL HỎNG (mã thoát {ma}) — log: {duong}")
        self.assertGreater(_so_ca(ra), 0, "bộ thử PostgreSQL chạy 0 ca mà vẫn xanh")
        _dc_am("postgres-tron")
        _dc_duong("postgres-tron")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# I. CHỐT AN TOÀN — bộ thử TỰ CHỐI CHẠY, và chứng minh nó THẬT SỰ chối
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _chay_con(nguon, cay_app=None, giay=600, bien_them=None):
    """Chạy một đoạn mã trong TIẾN TRÌNH CON. Trả (mã thoát, output)."""
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    f.write(nguon)
    f.close()
    env = dict(os.environ)
    env["GIT_CONFIG_COUNT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [cay_app or GOC_APP, THU_MUC_THU] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env.update(bien_them or {})
    try:
        r = subprocess.run([sys.executable, f.name], capture_output=True, text=True, env=env,
                           cwd=GOC_CAY, timeout=giay)
        return r.returncode, r.stdout + r.stderr
    finally:
        os.unlink(f.name)


def _cay_sao_chep():
    """Sao chép MỌI `*.py` dưới `app/` sang thư mục tạm (giữ cấu trúc). KHÔNG đụng cây thật."""
    dich = tempfile.mkdtemp(prefix="veh-g18-cay-")
    for goc, _, tens in os.walk(GOC_APP):
        if "__pycache__" in goc or os.sep + "du-lieu" in goc:
            continue
        for ten in tens:
            if not ten.endswith(".py"):
                continue
            tu = os.path.join(goc, ten)
            den = os.path.join(dich, os.path.relpath(tu, GOC_APP))
            os.makedirs(os.path.dirname(den), exist_ok=True)
            shutil.copy2(tu, den)
    return dich


def _cay_dot_bien(thay_doi):
    """Sao chép rồi tiêm đột biến. Trả đường dẫn cây đột biến."""
    cay = _cay_sao_chep()
    for ten, cu, moi in thay_doi:
        duong = os.path.join(cay, ten)
        with open(duong, encoding="utf-8") as f:
            nguon = f.read()
        if cu not in nguon:
            raise AssertionError(f"đột biến KHÔNG áp được: không thấy mẫu trong app/{ten}")
        with open(duong, "w", encoding="utf-8") as f:
            f.write(nguon.replace(cu, moi))
    return cay


class I_ChotAnToan(unittest.TestCase):

    def test_i1_nen_khong_phai_thu_muc_tam_thi_TU_CHOI_CHAY(self):
        khong_tam = os.path.join(os.path.expanduser("~"), ".veh-g18-phai-tu-choi")
        self.assertFalse(os.path.exists(khong_tam), f"đường thử đã tồn tại sẵn: {khong_tam}")
        ma, ra = _chay_con("import thu_qa_g18\nprint('LOT-QUA-DUOC')\n",
                           bien_them={"VIP_G18_DATA": khong_tam})
        self.assertNotEqual(ma, 0, "bộ thử CHẠY được trên nền KHÔNG phải thư mục tạm")
        self.assertIn("TỪ CHỐI CHẠY", ra, f"không thấy lời từ chối: {ra[-300:]}")
        self.assertNotIn("LOT-QUA-DUOC", ra, "bộ thử chạy tiếp sau khi đáng lẽ phải từ chối")
        self.assertFalse(os.path.exists(khong_tam), "bộ thử đã GHI ra ngoài thư mục tạm")
        _dc_am("tu-choi-khi-thieu-chot")
        _dc_duong("tu-choi-khi-thieu-chot")
        print(f"\n  [I1] nền ngoài thư mục tạm ⇒ thoát {ma}, KHÔNG tạo gì ở {khong_tam}")

    def test_i2_bo_do_chot_an_toan_co_rang(self):
        self.assertIsNone(kiem_chot_an_toan(), f"chốt an toàn báo sai ở môi trường thật: {_LY_DO_TU_CHOI}")
        _dc_duong("bo-do-chot-an-toan")
        self.assertIsNotNone(kiem_chot_an_toan({"dia_chi": "0.0.0.0"}), "bộ kiểm MÙ với bind 0.0.0.0")
        self.assertIsNotNone(kiem_chot_an_toan({"dia_chi": "192.168.1.9"}), "bộ kiểm MÙ với bind LAN")
        gia = type("AdapterGiaLive", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live-i2"] = gia
        try:
            ly = kiem_chot_an_toan()
        finally:
            adapter._DANG_KY.pop("gia-live-i2", None)
        self.assertIsNotNone(ly, "bộ kiểm MÙ với adapter MỞ LIVE")
        self.assertIn("gia-live-i2", ly or "")
        self.assertIsNone(kiem_chot_an_toan(), "sổ đăng ký adapter chưa được trả nguyên trạng")
        _dc_am("bo-do-chot-an-toan")
        print("\n  [I2] chốt an toàn: ĐÚNG ở môi trường thật · BẮT được bind LAN/0.0.0.0 và adapter LIVE")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# J. HAI CHỐT CHẶN BẮT BUỘC — ca cố ý hỏng trong TIẾN TRÌNH CON + đột biến cho từng cổng
# ══════════════════════════════════════════════════════════════════════════════════════════════
MA_THU_HONG = """import unittest
class T(unittest.TestCase):
    def test_co_y_hong(self):
        self.assertEqual(1, 2, "ca CO Y HONG de kiem bo do")
if __name__ == "__main__":
    unittest.main()
"""

MA_THU_DAT = """import unittest
class T(unittest.TestCase):
    def test_dat(self):
        self.assertTrue(True)
if __name__ == "__main__":
    unittest.main()
"""

DRIVER_UNAUTH = """import json
import thu_qa_g18 as q
print("KETQUA=" + json.dumps(q.do_unauth_ghi(), ensure_ascii=False))
"""

DRIVER_CSRF = """import json
import thu_qa_g18 as q
print("KETQUA=" + json.dumps(q.do_csrf(), ensure_ascii=False))
"""

DRIVER_PLATFORM = """import json
import thu_qa_g18 as q
print("KETQUA=" + json.dumps(q.do_platform_chan(), ensure_ascii=False))
"""

DRIVER_CHEO = """import json
import thu_qa_g18 as q
print("KETQUA=" + json.dumps(q.do_ghi_cheo_membership(), ensure_ascii=False))
"""

DRIVER_QUYEN = """import json
import thu_qa_g18 as q
print("KETQUA=" + json.dumps(q.do_quyen_admin_tao_tenant(), ensure_ascii=False))
"""


def _kq_driver(ra):
    m = re.search(r"^KETQUA=(\{.*\})$", ra, re.M)
    return json.loads(m.group(1)) if m else None


class J_TuKiemBoDo(unittest.TestCase):
    """Không có nhóm này thì mọi dòng "✓ … ca" của tệp này KHÔNG chứng minh gì."""

    def test_j1_ca_co_y_hong_bi_bo_do_THAY(self):
        ma, ra = _chay_con(MA_THU_HONG)
        self.assertNotEqual(ma, 0, f"bộ dò KHÔNG thấy ca cố ý hỏng (mã thoát {ma})")
        self.assertIn("FAILED", ra, "output ca hỏng không có dấu hiệu hỏng")
        self.assertFalse(re.search(r"^OK( |$)", ra, re.M), "output vừa FAILED vừa có dòng OK")
        self.assertEqual(_phan_quyet(ma, ra), "HỎNG")
        _dc_am("tu-kiem-bo-do")
        ma2, ra2 = _chay_con(MA_THU_DAT)
        self.assertEqual(ma2, 0, f"ca ĐẠT lại thoát {ma2}: {ra2[-300:]}")
        self.assertRegex(ra2, r"Ran 1 test")
        self.assertEqual(_phan_quyet(ma2, ra2), "ĐẠT")
        _dc_duong("tu-kiem-bo-do")
        print(f"\n  [J1] ca cố ý hỏng (tiến trình con) → thoát {ma} · bộ dò THẤY; "
              f"ca đạt → thoát {ma2}")

    def test_j2_luat_phan_tu_choi_ba_kich_ban_lua(self):
        self.assertEqual(_phan_quyet(0, "OK\n"), "HỎNG", "thoát 0 mà 0 ca vẫn được ĐẠT")
        self.assertEqual(_phan_quyet(0, "chay xong, khong in gi"), "HỎNG", "thoát 0 không dấu vết vẫn ĐẠT")
        self.assertEqual(_phan_quyet(1, "Ran 5 tests\nOK\n"), "HỎNG", "in OK rồi thoát 1 vẫn được ĐẠT")
        self.assertEqual(_phan_quyet(0, "Ran 5 tests\nOK\n"), "ĐẠT")
        _dc_am("luat-phan")
        _dc_duong("luat-phan")

    def test_j3_dot_bien_M1_bo_chan_401_thi_cong_E2_phai_do(self):
        """M1: bỏ nhánh 401 của middleware ⇒ `E2` (không phiên = 401) PHẢI đỏ."""
        _, ra_that = _chay_con(DRIVER_UNAUTH)
        kq_that = _kq_driver(ra_that)
        self.assertIsNotNone(kq_that, f"driver không in KETQUA: {ra_that[-400:]}")
        self.assertEqual(kq_that["khong_401"], [], f"cây THẬT đã hở cửa ghi: {kq_that['khong_401'][:5]}")
        _dc_duong("dot-bien-M1")
        cu = ('if nc is None:\n'
              '            return self._tra(401, {"loi": "chưa đăng nhập hoặc phiên hết hạn"})')
        moi = 'if nc is None:\n            return self._tra(500, {"loi": "M1"})'
        cay = _cay_dot_bien([("server.py", cu, moi)])
        _, ra_bien = _chay_con(DRIVER_UNAUTH, cay_app=cay)
        kq_bien = _kq_driver(ra_bien)
        self.assertIsNotNone(kq_bien, f"driver trên cây đột biến không in KETQUA: {ra_bien[-400:]}")
        self.assertNotEqual(kq_bien["khong_401"], [],
                            "bỏ chốt 401 mà phép quét VẪN sạch ⇒ cổng E2 KHÔNG có răng")
        _dc_am("dot-bien-M1")
        print(f"\n  [J3] M1 (bỏ 401): cây thật → 0 cửa hở · cây đột biến → "
              f"{len(kq_bien['khong_401'])} cửa hở ⇒ cổng E2 CÓ RĂNG")

    def test_j4_dot_bien_M2_bo_csrf_thi_cong_E4_phai_do(self):
        _, ra_that = _chay_con(DRIVER_CSRF)
        kq = _kq_driver(ra_that)
        self.assertIsNotNone(kq, f"driver CSRF không in KETQUA: {ra_that[-400:]}")
        self.assertEqual(kq["thieu_header"], 403, f"cây THẬT không chặn CSRF: {kq}")
        _dc_duong("dot-bien-M2")
        cay = _cay_dot_bien([("server.py",
                              'raise don_hang.LoiNghiepVu("thiếu header X-Requested-With: VIPHub'
                              ' (chống CSRF)", 403)', "return")])
        _, ra_bien = _chay_con(DRIVER_CSRF, cay_app=cay)
        kq2 = _kq_driver(ra_bien)
        self.assertIsNotNone(kq2, f"driver CSRF trên cây đột biến không in KETQUA: {ra_bien[-400:]}")
        self.assertNotEqual(kq2["thieu_header"], 403,
                            "bỏ chốt CSRF mà lượt thiếu header VẪN 403 ⇒ cổng E4 KHÔNG có răng")
        _dc_am("dot-bien-M2")
        print(f"  [J4] M2 (bỏ CSRF): cây thật → 403 · cây đột biến → {kq2['thieu_header']} ⇒ cổng E4 CÓ RĂNG")

    def test_j5_dot_bien_M3_bo_chan_platform_thi_cong_F1_phai_do(self):
        _, ra_that = _chay_con(DRIVER_PLATFORM)
        kq = _kq_driver(ra_that)
        self.assertIsNotNone(kq, f"driver platform không in KETQUA: {ra_that[-400:]}")
        self.assertEqual(kq["khong_403"], [], f"cây THẬT đã hở plane nền tảng: {kq['khong_403'][:5]}")
        _dc_duong("dot-bien-M3")
        cay = _cay_dot_bien([("server.py", "if not nc.platform_role:", "if False:")])
        _, ra_bien = _chay_con(DRIVER_PLATFORM, cay_app=cay)
        kq2 = _kq_driver(ra_bien)
        self.assertIsNotNone(kq2, f"driver platform trên cây đột biến không in KETQUA: {ra_bien[-400:]}")
        self.assertNotEqual(kq2["khong_403"], [],
                            "bỏ chốt `platform_role` mà phiên tenant VẪN bị 403 ⇒ cổng F1 KHÔNG có răng")
        _dc_am("dot-bien-M3")
        print(f"  [J5] M3 (bỏ chốt platform): cây thật → 0 cửa hở · cây đột biến → "
              f"{len(kq2['khong_403'])} cửa hở ⇒ cổng F1 CÓ RĂNG")

    def test_j6_dot_bien_M4_bo_loc_tenant_thi_cong_E5_phai_do(self):
        """M4: bỏ `AND tenant_id=?` khi tra membership ⇒ B SỬA ĐƯỢC hàng của A."""
        _, ra_that = _chay_con(DRIVER_CHEO)
        kq = _kq_driver(ra_that)
        self.assertIsNotNone(kq, f"driver ghi chéo không in KETQUA: {ra_that[-400:]}")
        self.assertTrue(kq["con_nguyen"], f"cây THẬT đã hở ghi chéo: {kq}")
        self.assertNotIn(kq["ma_b"], (200, 201), f"cây THẬT: B ghi được ({kq})")
        _dc_duong("dot-bien-M4")
        # Bỏ bộ lọc tenant trong phép tra membership: `? IS NOT NULL` luôn đúng, nên B tra
        # thấy hàng của A và (vì câu UPDATE chỉ lọc theo `id`) SỬA ĐƯỢC nó.
        cay = _cay_dot_bien([("server.py",
                              "SELECT * FROM tenant_memberships WHERE id=? AND tenant_id=?",
                              "SELECT * FROM tenant_memberships WHERE id=? AND ? IS NOT NULL")])
        _, ra_bien = _chay_con(DRIVER_CHEO, cay_app=cay)
        kq2 = _kq_driver(ra_bien)
        self.assertIsNotNone(kq2, f"driver trên cây đột biến không in KETQUA: {ra_bien[-400:]}")
        self.assertFalse(kq2["con_nguyen"],
                         "bỏ bộ lọc tenant mà dữ liệu của A VẪN nguyên ⇒ cổng E5 KHÔNG có răng "
                         f"(B nhận {kq2['ma_b']})")
        _dc_am("dot-bien-M4")
        print(f"  [J6] M4 (bỏ lọc tenant): cây thật → B bị chặn ({kq['ma_b']}, dữ liệu A nguyên) · "
              f"cây đột biến → B SỬA ĐƯỢC (mã {kq2['ma_b']}, dữ liệu A đổi) ⇒ cổng E5 CÓ RĂNG")

    def test_j7_dot_bien_M5_bo_kiem_quyen_thi_cong_F3_phai_do(self):
        """M5: `quyen.co_quyen` luôn True ⇒ PLATFORM_ADMIN tạo được tenant ⇒ F3 phải đỏ."""
        _, ra_that = _chay_con(DRIVER_QUYEN)
        kq = _kq_driver(ra_that)
        self.assertIsNotNone(kq, f"driver quyền không in KETQUA: {ra_that[-400:]}")
        self.assertEqual(kq["admin_tao_tenant"], 403, f"cây THẬT: PLATFORM_ADMIN không bị 403 ({kq})")
        _dc_duong("dot-bien-M5")
        cu = ('return csdl.mot("SELECT 1 x FROM role_permissions WHERE role_ma=? AND perm_ma=?",\n'
              '                    (role_ma, hanh_dong)) is not None')
        cay = _cay_dot_bien([("quyen.py", cu, "return True")])
        _, ra_bien = _chay_con(DRIVER_QUYEN, cay_app=cay)
        kq2 = _kq_driver(ra_bien)
        self.assertIsNotNone(kq2, f"cây đột biến M5 không chạy được: {ra_bien[-400:]}")
        self.assertNotEqual(kq2["admin_tao_tenant"], 403,
                            "bỏ hết phép kiểm quyền mà PLATFORM_ADMIN VẪN bị 403 ⇒ cổng F3 KHÔNG có răng")
        _dc_am("dot-bien-M5")
        print(f"  [J7] M5 (bỏ kiểm quyền): cây thật → PLATFORM_ADMIN 403 · cây đột biến → "
              f"{kq2['admin_tao_tenant']} ⇒ cổng F3 CÓ RĂNG")
        _dc_am("dot-bien-M5")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Z. TỔNG KẾT — sổ đối chứng + vân tay cây trước/sau + cụm :5432 trước/sau
# ══════════════════════════════════════════════════════════════════════════════════════════════
class Z_TongKet(unittest.TestCase):

    def test_z1_moi_nhom_phu_dinh_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertEqual(thieu, [], f"nhóm có ca ÂM mà KHÔNG có đối chứng DƯƠNG: {thieu}")
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")
        _dc_duong("so-doi-chung")
        print("\nSỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))

    def test_z2_cay_khong_doi_trong_luot_do(self):
        """Cây KHÔNG đổi giữa lượt đo — đo bằng CẢ HAI vân tay, không chỉ bản dự phòng.

        Bản dự phòng (bỏ qua vùng thử) bắt được thay đổi MÃ SẢN PHẨM. Vân tay GIT (CHÍNH) bắt thêm
        `git diff HEAD` — mọi thay đổi trên tệp ĐÃ THEO DÕI, kể cả `docs/*.md` (`G16-09`).
        """
        sau = van_tay_cay()
        self.assertEqual(sau, VAN_TAY_LUC_NAN,
                         "CÂY ĐỔI giữa lượt đo ⇒ mọi số đo phải coi là vô hiệu")
        vt = chotcay.van_tay()
        self.assertEqual(vt["head"], HEAD_LUC_NAN,
                         "HEAD ĐỔI giữa lượt đo ⇒ số đo thuộc HAI mốc mã khác nhau")
        self.assertEqual(vt["thu_muc"]["theo_doi"], VAN_TAY_THU_MUC_LUC_NAN,
                         "NỘI DUNG một tệp ĐÃ THEO DÕI đổi giữa lượt đo (kể cả `docs/*.md` — "
                         "`G16-09`) ⇒ số đo vô hiệu")
        _dc_duong("cay-khong-doi")
        head = _git("rev-parse", "HEAD").stdout.strip()
        print(f"\n  [Z2] HEAD={head} · vân tay={sau} (trước = sau) · CSDL tạm={_TAM} · log={LOG_DIR}")

    def test_z3_cum_5432_truoc_bang_sau(self):
        truoc = VAN_TAY_5432_LUC_NAN if VAN_TAY_5432_LUC_NAN is not None else _van_tay_5432()
        if truoc is None:
            self.skipTest("CHƯA ĐO: không đọc được vân tay cụm :5432")
        sau = _van_tay_5432()
        self.assertIsNotNone(sau, "không đọc lại được vân tay cụm :5432")
        self.assertEqual(truoc, sau, "cụm :5432 ĐỔI trong lượt đo (dữ liệu dự án khác bị đụng)")
        _dc_am("5432-khong-dung")
        _dc_duong("5432-khong-dung")
        print(f"  [Z3] vân tay cụm :5432 TRƯỚC = SAU ({truoc['so_csdl']} CSDL, "
              f"{', '.join(truoc['danh_sach_csdl'])})")


if __name__ == "__main__":
    print(f"NỀN ĐO: HEAD={_git('rev-parse', 'HEAD').stdout.strip()} · ghim={HEAD_GHIM or 'KHÔNG'}"
          f" · CSDL={_TAM}")
    print(f"PHẠM VI ĐO: chỉ loopback + CSDL tạm · adapter MOCK · cổng hãng KHOÁ "
          f"· cụm PostgreSQL :5432 CHẶN CỨNG")
    unittest.main(verbosity=2)
