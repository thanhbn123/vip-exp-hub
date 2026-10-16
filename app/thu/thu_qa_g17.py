#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G17 — AG-01 (QA/VERIFIER): bộ thử ĐỘC LẬP nghiệm thu trên NỀN ĐÓNG BĂNG `integration/g16 @ 98baeb3`.

VÌ SAO CÓ TỆP NÀY
-----------------
`docs/G16_ACCEPTANCE.md` §8 (§ danh sách "CHƯA ĐO") và `docs/QA_G13_G15.md` §L2.8 để lại
**bảy mục chưa đo** — và một danh sách "chưa đo" bị rút gọn là cách biến nó thành "đã đo".
Tệp này dựng phép đo ĐỘC LẬP cho phần đo được, và ghi thẳng phần KHÔNG đo được vào
`docs/QA_G17.md` §"CHƯA ĐO" (lỗ hổng phạm vi, KHÔNG phải ĐẠT).

AG-01 KHÔNG viết mã sản phẩm. Tệp này chỉ ĐỌC, DỰNG NỀN RIÊNG và ĐO.

BỐN LUẬT TỰ ÁP
--------------
1. **Không chạm mạng thật.** Mọi phép đo lớp HTTP chỉ dùng máy chủ CỦA CHÍNH DỰ ÁN bind
   `127.0.0.1` **cổng 0** (cổng hệ điều hành cấp, không cổng cố định ⇒ không tranh cổng với
   làn khác, không HỎNG GIẢ — R-13 `QA2_TEST_PLAN.md` §6). Không gọi hãng thật, kể cả sandbox
   (`V-G09-01` + `V-13906-05` CHƯA CẤP). Có nhóm `A6` canh chính điều đó bằng bộ đếm socket.
2. **CSDL riêng.** `VIP_HUB_DATA` trỏ vào thư mục tạm, KHÔNG BAO GIỜ `app/du-lieu/`.
3. **Hai chốt chặn** (`docs/QA_G13_G15.md` §6.3):
   · `F_TuKiemBoDo` — ca CỐ Ý HỎNG chạy trong TIẾN TRÌNH CON, khẳng định bộ dò THẤY nó hỏng;
     kèm **đột biến trên chính mã sản phẩm** (cây sao chép) để chứng minh từng cổng CÓ RĂNG;
   · `DOI_CHUNG` — mọi nhóm có ca PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG; `Z_TongKet` tự phán HỎNG
     nếu thiếu. Không có đối chứng dương thì "tầng chết hẳn" cũng làm mọi ca âm xanh vô nghĩa.
4. **Phán bằng MÃ THOÁT + SỐ CA**, không bằng chữ trong output (`chay_tat_ca.sh` dòng 40).

GHIM HEAD: đặt `VIP_G17_HEAD=98baeb357214d41a9380467fde2fee2b94fd31cc` thì phép ghim HEAD là
cổng CỨNG. Không đặt thì phép ghim chỉ GHI RA (vì tệp này còn phải chạy được sau khi gộp vào
nhánh khác — `docs/QA_G13_G15.md` §7.3: tạo một tệp thử làm đỏ hồi quy của làn khác là tác hại).

Chạy: VIP_G17_HEAD=98baeb357214d41a9380467fde2fee2b94fd31cc python3 app/thu/thu_qa_g17.py
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
import unittest

sys.dont_write_bytecode = True          # không để lại __pycache__ trong cây ĐANG ĐO (§41)

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)
THU_MUC_THU = os.path.dirname(os.path.abspath(__file__))

# CSDL riêng của lượt đo. `VIP_G17_DATA` chỉ để DRIVER ĐỘT BIẾN trỏ sang nền riêng của nó;
# bộ chạy hồi quy đặt `VIP_HUB_DATA` dùng chung nên tệp này CỐ Ý không dùng biến đó.
_TAM = os.environ.get("VIP_G17_DATA") or tempfile.mkdtemp(prefix="veh-g17-qa-")
os.environ["VIP_HUB_DATA"] = _TAM

# `append`, KHÔNG `insert(0)`: driver đột biến đặt cây đột biến LÊN TRƯỚC qua PYTHONPATH, và
# `insert(0)` ở đây sẽ kéo cây gốc trở lại vị trí đầu — đột biến biến mất mà không ai báo.
if GOC_APP not in sys.path:
    sys.path.append(GOC_APP)

import adapter                                                          # noqa: E402
import adapter_jt                                                       # noqa: E402
import adapter_vtp                                                      # noqa: E402
import bao_mat                                                          # noqa: E402
import cau_hinh                                                         # noqa: E402
import csdl                                                             # noqa: E402
import quyen                                                            # noqa: E402
import secret_provider                                                  # noqa: E402
import server                                                           # noqa: E402
import trang_thai_hang as tth                                           # noqa: E402

# CHỐT "CÂY SẠCH" + VÂN TAY + MÔI TRƯỜNG GIT — MỘT chỗ duy nhất (AG-05 G21). Ba bản sao của cùng
# một luật là ba bản sẽ trôi khỏi nhau — đúng khuôn `N-G18-00` (hai nhiệt kế, hai kết quả).
# `sys.path[0]` là thư mục chứa tệp này khi chạy trực tiếp; nhánh dưới chỉ để chắc chắn.
try:
    import thu_g21_chotcay as chotcay                                    # noqa: E402
except ImportError:                                                      # pragma: no cover
    sys.path.insert(0, THU_MUC_THU)
    import thu_g21_chotcay as chotcay                                    # noqa: E402

HEAD_GHIM = os.environ.get("VIP_G17_HEAD", "").strip()
CONG_CO_DINH = {8888, 8899, 9000, 9999, 8947}       # cổng mà các bộ khác trong dự án bind cứng
SO_DUONG_API = re.compile(r'"(/api/v2/[^"]*)"')


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0b. CHỐT AN TOÀN — bộ thử TỪ CHỐI CHẠY nếu thiếu (yêu cầu Owner/Codex, msg_bb195b03f767:
#     "harness phải chạy được ở MOCK trên nền TẠM, chỉ loopback, và TỪ CHỐI CHẠY nếu thiếu chốt")
# ══════════════════════════════════════════════════════════════════════════════════════════════
def kiem_chot_an_toan(mt=None):
    """Trả LÝ DO TỪ CHỐI CHẠY, hoặc `None` nếu đủ ba chốt an toàn.

    Ba chốt, không thương lượng: (1) nền CSDL nằm trong THƯ MỤC TẠM và NGOÀI cây repo;
    (2) KHÔNG lớp adapter nào `CHO_PHEP_LIVE=True`; (3) máy chủ bind LOOPBACK.
    Thiếu một chốt ⇒ TỪ CHỐI CHẠY, chứ không chạy rồi báo ĐẠT.
    """
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
# 0. SỔ ĐỐI CHỨNG DƯƠNG + TIỆN ÍCH ĐO
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


# SỔ PHÁT HIỆN ĐÃ BIẾT — KHÔNG phải "danh sách bỏ qua". Mỗi mục phải kèm mã, mức độ, chỗ đứng
# và bằng chứng ĐO ĐƯỢC; `Z_TongKet` in sổ ra, và `test_c8` ĐỎ nếu mục trong sổ đã hết đúng
# (đã được sửa) — nhờ vậy một miễn trừ không âm thầm mục ruỗng theo thời gian.
PHAT_HIEN_DA_BIET = {
    "tenant.billing.quan_ly": {
        "ma": "N-G17-01",
        "muc": "LOW",
        "o": "app/server.py:1187",
        "mo_ta": ("`self._can(nc, \"tenant.billing.quan_ly\" if quyen.co_quyen(nc.role, "
                  "\"tenant.billing.quan_ly\") else \"tenant.membership.quan_ly\")` — quyền "
                  "`tenant.billing.quan_ly` KHÔNG có trong `quyen.QUYEN`."),
        "do_duoc": ("`quyen.co_quyen(role, 'tenant.billing.quan_ly')` = False cho MỌI vai trò "
                    "⇒ nhánh đầu là MÃ CHẾT; cửa luôn rơi về `tenant.membership.quan_ly`."),
        "muc_do_ly_do": ("KHÔNG phải lỗ hổng: đây là khuôn 'quyền tuỳ chọn ưu tiên, không có thì "
                         "lùi về quyền nền', và cửa vẫn MỞ bằng quyền nền (đo ở `test_c8`). "
                         "Rủi ro thật là ĐỘ LỆCH DANH MỤC: người đọc mã tưởng có một quyền "
                         "không tồn tại."),
    },
}


def _git(*tham_so, env=None, goc=None):
    """Chạy git với môi trường `GIT_CONFIG_*` ĐÃ CHUẨN HOÁ — **KÈM CẢNH BÁO**, không gỡ im lặng.

    `N-G18-00`: `GIT_CONFIG_COUNT=2` mà thiếu `GIT_CONFIG_KEY_0`/`_1` làm MỌI lệnh git thoát 128.
    Việc chuẩn hoá nay nằm MỘT chỗ (`thu_g21_chotcay.env_git`) để ba bản sao không trôi khỏi nhau,
    và nó PHÂN BIỆT hai thứ khác hẳn nhau:
      · MÔI TRƯỜNG hỏng  ⇒ gỡ gia đình biến + in cảnh báo ra `stderr`;
      · CÂY hỏng thật    ⇒ lệnh git vẫn hỏng, mã thoát + `stderr` được trả NGUYÊN VẸN cho người gọi.
    Không có nhánh nào biến một lỗi thật thành "thành công" (xem `thu_g21_chotcay.test_e3`).

    `goc` (mặc định cây đang đo) cho phép trỏ vào CÂY TẠM của đối chứng âm. Không truyền thì
    hành vi y như cũ.
    """
    return chotcay._git(*tham_so, goc=goc or GOC_CAY, env=env)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHẠM VI CỦA WAVE — cái gì được phép BẨN mà cổng "cây sạch" vẫn xanh
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# LỊCH SỬ — CÙNG MỘT LỖI, BA LẦN (đọc trước khi sửa):
#   · Bản đầu ghim CỨNG hai đường của LƯỢT 1 ⇒ chính làn này giao thêm tệp ở lượt sau là cổng ĐỎ (H5).
#   · Bản G20 khai ĐÍCH DANH từng tệp của làn khác (`PHAM_VI_LAN_KHAC`, 3 đường) ⇒ wave SAU giao
#     MỘT tệp MỚI là cổng ĐỎ LẦN NỮA. AG-01 đo được ở G20 (`docs/QA_G20.md` §2.1, CỔNG C1): **0/2**
#     cổng xanh, và `sh app/thu/chay_tat_ca.sh` đỏ vì lý do TÍCH HỢP — người nghiệm thu rất dễ đọc
#     nhầm thành "wave trước làm hỏng wave sau".
#
# NAY: miễn trừ theo **QUY TẮC**, KHÔNG theo tên tệp.
#     "CÂY SẠCH" = **KHÔNG có thay đổi NÀO ngoài các tệp mà WAVE ĐANG LÀM**
#     "các tệp mà wave đang làm" = mọi đường nằm trong **VÙNG THỬ/TÀI LIỆU** (`docs/` + mọi thư mục
#     có tên bắt đầu bằng `thu`). Tệp MỚI do `git status -uall` TỰ TÌM — không ai phải nhớ thêm một
#     dòng vào danh sách nào, nên `N-G19-03` không còn đường tái diễn.
#
# ĐÂY KHÔNG PHẢI "BỎ QUA HẾT" — điều đó được ĐO, không khẳng định suông:
#   · `test_a1d` — ĐỐI CHỨNG ÂM ba tầng trên CÂY GIT THẬT: tệp SẢN PHẨM bẩn ⇒ cổng ĐỎ;
#   · `thu_g21_chotcay.chung_minh_vung()` — CHỨNG MINH vùng thử không chạy trong sản phẩm (không
#     tệp sản phẩm nào import nó; `app/server.py` không phục vụ nó). Chứng minh hỏng ⇒ chốt TỪ CHỐI tha;
#   · `thu_g20_baomat.py::B_ChotCaySach` — bộ của wave TRƯỚC, KHÔNG sửa, vẫn đo được cả hai chiều.
PHAM_VI_LAN_NHA = ("app/thu/thu_qa_g17*.py", "docs/QA_G17*.md")

# Làn KHÁC trong cùng wave — NAY **RỖNG**, và phải RỖNG MÃI: miễn trừ theo quy tắc, không theo tên.
# Giữ TÊN biến (không xoá) vì `thu_g20_baomat.py` đọc nó bằng AST để đo ĐỘC LẬP, và `test_a1b`
# canh nó không được chứa ký tự mẫu lẫn đường dẫn sản phẩm.
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
# `TEP_CUA_AG01_G17` = HỌ BỘ KIỂM của làn này (câu hỏi HẸP, `_la_tep_ag01` trả lời);
# `MAU_TEP_CUA_AG01_G17` = mẫu vùng thử/tài liệu (câu hỏi RỘNG, chốt trả lời).
MAU_TEP_CUA_AG01_G17 = PHAM_VI_WAVE
TEP_CUA_AG01_G17 = PHAM_VI_LAN_NHA


def _la_tep_trong_pham_vi(duong):
    """Đường này có nằm trong VÙNG THỬ/TÀI LIỆU (được phép bẩn) không. QUY TẮC, không danh sách."""
    return any(fnmatch.fnmatch(duong, m) for m in PHAM_VI_WAVE)


def _la_tep_ag01(dong_porcelain):
    """HẸP CÓ CHỦ Ý — đường này có thuộc **HỌ BỘ KIỂM NGHIỆM THU của wave này** không.

    ⚠ ĐÂY **KHÔNG PHẢI** CHỐT "CÂY SẠCH". Chốt là `_chot_do()` (miễn trừ theo QUY TẮC vùng).
    Hàm này trả lời một câu hỏi HẸP HƠN, và giữ nguyên độ hẹp đó là CỐ Ý: `thu_qa_g20.py::test_g1`
    (bộ nghiệm thu của wave trước) đo đúng câu hỏi hẹp ấy — "cơ chế miễn trừ còn nhận ra tệp của
    CHÍNH NÓ không". Nới hàm này thành chốt rộng sẽ làm phép đo của wave trước trả lời SAI câu hỏi.
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
    sản phẩm; chứng minh hỏng ⇒ NÉM LỖI (không tha mù). Chỉ chạy chứng minh trên cây THẬT: cây
    git tạm của đối chứng âm không có `app/server.py`.
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


def van_tay_cay(bo_qua=(), env=None):
    """Vân tay cây: `{ git ls-files -s; git status --porcelain -uall; }` → sha256.

    `bo_qua=()` giữ NGUYÊN VĂN output của git. Truyền mẫu vào thì lọc theo dòng trước khi băm —
    dùng để so "trước/sau" mà bỏ qua chính những đường thuộc vùng thử/tài liệu.

    ⚠ Đây là vân tay **DỰ PHÒNG**. Vân tay **CHÍNH** là Git: `rev-parse HEAD` + `git diff HEAD`
    rỗng + `status --porcelain -uall` rỗng (`thu_g21_chotcay.van_tay_git`) — bản cũ chỉ `find` bốn
    thư mục theo bốn đuôi tệp nên **MÙ** với `docs/*.md` (`G16-09`).
    """
    ls = _git("ls-files", "-s", env=env).stdout
    st = _git("status", "--porcelain=v1", "-uall", env=env).stdout
    if bo_qua:
        giu = _loc_cay_ban(st.splitlines(), bo_qua)
        st = ("\n".join(giu) + "\n") if giu else ""
    return hashlib.sha256((ls + "\n" + st).encode("utf-8")).hexdigest()


VAN_TAY_LUC_NAN = van_tay_cay(bo_qua=PHAM_VI_WAVE)

# MỐC "LÚC NÃN" của VÂN TAY CHÍNH — so "trước/sau" theo LUẬT §41, KHÔNG đòi cây phải sạch:
# trên worktree của một làn đang làm việc thì `git diff HEAD` KHÔNG rỗng (chính làn đó đang sửa
# tệp), nên khẳng định "diff HEAD rỗng" sẽ đỏ vì lý do ĐÚNG-NHƯNG-VÔ-NGHĨA. Cái phải đo là
# "cây có ĐỔI trong lượt đo không", tức so với mốc chụp lúc bắt đầu.
HEAD_LUC_NAN = _git("rev-parse", "HEAD").stdout.strip()
VAN_TAY_THU_MUC_LUC_NAN = chotcay.van_tay_thu_muc()["theo_doi"]


def _doc_app(ten):
    """Đọc một tệp trong `app/`. MỘT chỗ duy nhất — để không chỗ nào quên đóng tệp."""
    with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
        return f.read()


def _quet_import_mang(nguon):
    """Trả danh sách import CHẠM MẠNG trong một nguồn Python (AST, không grep chú thích)."""
    cam = ("requests", "httpx", "urllib.request", "http.client", "socket")
    thay = []
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Import):
            for a in nut.names:
                if a.name in cam:
                    thay.append("import " + a.name)
        elif isinstance(nut, ast.ImportFrom):
            if (nut.module or "") in cam:
                thay.append("from " + nut.module)
    return thay


def _quet_driver_csdl(nguon):
    """Trả danh sách import driver CSDL KHÁC SQLite (D-8: nghiệp vụ VẪN SQLite)."""
    cam = ("psycopg", "psycopg2", "asyncpg", "pg8000", "mysql.connector", "pymysql")
    thay = []
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Import):
            for a in nut.names:
                if a.name.split(".")[0] in cam:
                    thay.append(a.name)
        elif isinstance(nut, ast.ImportFrom):
            if (nut.module or "").split(".")[0] in cam:
                thay.append(nut.module)
    return thay


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. NỀN ĐO: schema → quyền → 2 tenant A/B → máy chủ 127.0.0.1 CỔNG 0
# ══════════════════════════════════════════════════════════════════════════════════════════════
_MT = {}
MK = "qa-g17-mat-khau-thu"          # mật khẩu THỬ trong CSDL TẠM — không phải credential thật


def _user(ten_dn, vai_tro=None):
    return csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, platform_role, tao_luc)"
                    " VALUES (?,?,?,?,?)",
                    (ten_dn, bao_mat.bam_mat_khau(MK), ten_dn, vai_tro, csdl.bay_gio())).lastrowid


def _gan(uid, tid, role):
    csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc) VALUES (?,?,?,?)",
             (uid, tid, role, csdl.bay_gio()))


def moi_truong():
    """Dựng nền đo MỘT LẦN cho cả tệp. Trả dict: cổng, tenant A/B, canary, token từng vai."""
    if _MT:
        return _MT
    import migrate
    csdl.mo()                       # SCHEMA hiện hành (IF NOT EXISTS)
    migrate.chay(im_lang=True)      # đường nâng cấp THẬT như `chay_e2e.sh` vẫn làm
    quyen.seed()

    duoi = hashlib.sha256(os.urandom(16)).hexdigest()[:8].upper()
    canary = f"QA-G17-CANARY-{duoi}"            # chuỗi CHỈ tenant A có — dùng dò rò chéo
    tid_a = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                     (f"qa-a-{duoi}", f"Tenant A {canary}", "basic", csdl.bay_gio())).lastrowid
    tid_b = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                     (f"qa-b-{duoi}", f"Tenant B {duoi}", "basic", csdl.bay_gio())).lastrowid

    u_a_owner = _user("qa-g17-a-owner"); _gan(u_a_owner, tid_a, "TENANT_OWNER")
    u_a_staff = _user("qa-g17-a-staff"); _gan(u_a_staff, tid_a, "TENANT_STAFF")
    u_a_view = _user("qa-g17-a-viewer"); _gan(u_a_view, tid_a, "TENANT_VIEWER")
    u_b_owner = _user("qa-g17-b-owner"); _gan(u_b_owner, tid_b, "TENANT_OWNER")
    u_b_admin = _user("qa-g17-b-admin"); _gan(u_b_admin, tid_b, "TENANT_ADMIN")
    u_hai = _user("qa-g17-hai-tenant"); _gan(u_hai, tid_a, "TENANT_ADMIN"); _gan(u_hai, tid_b, "TENANT_VIEWER")

    kh_a = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                    (tid_a, f"Khach A {canary}", "0900000011", "1 Le Loi", csdl.bay_gio())).lastrowid
    kh_b = csdl.ghi("INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, tao_luc) VALUES (?,?,?,?,?)",
                    (tid_b, f"Khach B {duoi}", "0900000022", "2 Nguyen Hue", csdl.bay_gio())).lastrowid
    mem_a = csdl.ghi("SELECT id FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
                     (u_a_staff, tid_a)).fetchone()["id"]

    cred, wh = {"ghi_chu": "credential GIA trong CSDL TAM"}, {}
    for tid in (tid_a, tid_b):
        for hang in ("vtp", "jt"):
            wh_ma = f"qa17{tid}{hang}{duoi}".lower()
            ban_ma, _ = bao_mat.ma_hoa_cred(dict(cred, tenant=tid), tid, hang)
            csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                     " credentials_ma_hoa, credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
                     " VALUES (?,?,?,?,?,?,?,?,?)",
                     (tid, hang, f"TK {hang} cua tenant {tid} {canary if tid == tid_a else ''}".strip(),
                      "mock", ban_ma, "", wh_ma, bao_mat.ma_hoa_wh("secret-gia-" + wh_ma, wh_ma),
                      csdl.bay_gio()))
            wh[(tid, hang)] = wh_ma

    class _ImLang(server.BoXuLy):
        def log_message(self, *a):          # im lặng: không đổ log ra output bộ thử
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ImLang)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    atexit.register(lambda: (srv.shutdown(), srv.server_close()))

    def _tok(uid):
        t, _ = bao_mat.dang_nhap(csdl.mot("SELECT ten_dang_nhap t FROM users WHERE id=?", (uid,))["t"], MK)
        return t

    _MT.update(cong=srv.server_address[1], dia_chi=srv.server_address[0], srv=srv,
               duoi=duoi, canary=canary, tid_a=tid_a, tid_b=tid_b,
               kh_a=kh_a, kh_b=kh_b, mem_a=mem_a, wh=wh,
               a_owner=_tok(u_a_owner), a_staff=_tok(u_a_staff), a_view=_tok(u_a_view),
               b_owner=_tok(u_b_owner), b_admin=_tok(u_b_admin), hai=_tok(u_hai),
               uid={"a_owner": u_a_owner, "a_staff": u_a_staff, "a_view": u_a_view,
                    "b_owner": u_b_owner, "b_admin": u_b_admin, "hai": u_hai})
    return _MT


def goi(duong, token=None, method="GET", body=None, csrf=True, cong=None, headers=None):
    """Một lượt HTTP tới máy chủ CỦA DỰ ÁN trên 127.0.0.1 cổng động. Trả (mã, dict, chuỗi_thô)."""
    mt = moi_truong()
    kn = http.client.HTTPConnection("127.0.0.1", cong or mt["cong"], timeout=15)
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


def duong_tinh():
    """Rút MỌI đường API TĨNH từ chính `app/server.py` — không chép tay danh sách cửa."""
    ra = set()
    for d in SO_DUONG_API.findall(_doc_app("server.py")):
        if "(" in d or "\\" in d:            # bỏ mẫu regex `(\d+)`: không phải đường gọi được
            continue
        if d.startswith(("/api/v2/auth/", "/api/v2/platform/", "/api/v2/webhook/nhan")):
            continue
        ra.add(d)
    return sorted(ra)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. CỔNG NỀN (F0) — cây · HEAD · ổ khoá LIVE · đường mạng · CSDL
# ══════════════════════════════════════════════════════════════════════════════════════════════
class A_Nen(unittest.TestCase):
    """Vi phạm bất kỳ mục nào ở đây ⇒ CHẶN GỘP: mọi số đo khác trở nên vô hiệu."""

    def test_a1_cay_sach_va_head(self):
        """CỔNG "CÂY SẠCH" (F0-a) — miễn trừ theo **QUY TẮC VÙNG**, tệp MỚI do git TỰ TÌM.

        Trên nền G20 (a3400a8) cổng này ĐỎ chỉ vì một làn KHÁC giao tệp mới (`N-G19-03`). Nay
        "các tệp mà wave đang làm" được TỰ DÒ: `docs/` + mọi thư mục tên bắt đầu bằng `thu`.
        """
        vi = chotcay.chung_minh_vung(goc=GOC_CAY)
        self.assertEqual(vi, [], "VÙNG THỬ/TÀI LIỆU đã chạm sản phẩm ⇒ không được tha:\n  - "
                         + "\n  - ".join(vi))
        _dc_duong("cay-sach-vung-co-chung-minh")
        ban = _chot_do()
        self.assertEqual(ban, [], f"CÂY BẨN NGOÀI VÙNG THỬ/TÀI LIỆU tại mốc đo (F0-a) ⇒ "
                                 f"mọi số đo vô hiệu: {ban}")
        _dc_duong("cay-sach")
        head = _git("rev-parse", "HEAD").stdout.strip()
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", head), f"HEAD không đọc được: {head!r}")
        vt = chotcay.van_tay()
        print(f"\n  [nền] HEAD={head}")
        print(f"  [nền] vùng thử/tài liệu TỰ DÒ: {chotcay.vung_thu_tai_lieu()}")
        print(f"  [nền] vân tay Git (CHÍNH): HEAD={'ok' if re.fullmatch(r'[0-9a-f]{40}', vt['head']) else 'LỖI'}"
              f" · diff HEAD={len(vt['diff'])} đường · status -uall={len(vt['status'])} dòng"
              f" · chế độ={vt['che_do']}")
        print(f"  [nền] vân tay dự phòng (bỏ qua vùng thử)={VAN_TAY_LUC_NAN}")
        if HEAD_GHIM:
            self.assertEqual(head, HEAD_GHIM, "HEAD KHÁC mốc ghim `VIP_G17_HEAD`")
            _dc_duong("ghim-head")
        else:
            print("  [nền] KHÔNG ghim HEAD (thiếu `VIP_G17_HEAD`) — phép ghim chỉ GHI RA, không phán")

    # ── BA CỔNG TỰ KIỂM CHÍNH CÁI MIỄN TRỪ (AG-05 G21) ───────────────────────────────────────
    # Vì sao phải có: `N-G18-03`/`N-G19-03` tái diễn vì miễn trừ QUÁ HẸP (danh sách tên cứng).
    # Cách chữa rẻ nhất — và SAI — là nới cho rộng ra thành "bỏ qua hết". Ba ca dưới đây chặn
    # đúng nước đi sai đó: chúng không đo mã sản phẩm, chúng đo CHÍNH PHẠM VI MIỄN TRỪ.
    def test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu(self):
        """Phạm vi miễn trừ chỉ được trỏ vào VÙNG THỬ/TÀI LIỆU — và phải KHỚP cây, không trôi.

        Ca này PIN gì: (1) mọi mục khai báo nằm trong `THU_MUC_PHAM_VI`; (2) `PHAM_VI_LAN_KHAC`
        **RỖNG** — miễn trừ nay theo QUY TẮC, không theo tên tệp; (3) mẫu khai báo PHẢI BẰNG mẫu
        TỰ DÒ từ cây (`thu_g21_chotcay.mau_vung_chuan`) — lệch là ĐỎ, vì lệch nghĩa là một vùng
        thử không được khai (cổng sẽ đỏ vì một tệp hợp lệ) hoặc một vùng sản phẩm bị nuốt.
        """
        self.assertTrue(PHAM_VI_WAVE, "phạm vi wave RỖNG ⇒ mọi phép đo dưới đây vô nghĩa")
        for m in PHAM_VI_WAVE:
            self.assertTrue(m.startswith(THU_MUC_PHAM_VI),
                            f"miễn trừ {m!r} trỏ RA NGOÀI vùng thử/tài liệu ⇒ có thể nuốt mã sản phẩm")
        # (2) danh sách ĐÍCH DANH của làn khác phải RỖNG — nó chính là khoản nợ N-G19-03.
        for m in PHAM_VI_LAN_KHAC:
            self.assertFalse(any(c in m for c in "*?["),
                             f"miễn trừ làn khác {m!r} chứa KÝ TỰ MẪU ⇒ nuốt vô hình tệp chưa ai khai")
            self.assertTrue(m.startswith(THU_MUC_PHAM_VI),
                            f"miễn trừ làn khác {m!r} trỏ vào mã sản phẩm")
            self.assertNotIn(m, PHAM_VI_LAN_NHA)
        self.assertEqual(PHAM_VI_LAN_KHAC, (),
                         "`PHAM_VI_LAN_KHAC` KHÔNG còn rỗng ⇒ ai đó lại liệt kê tên tệp của làn khác; "
                         "miễn trừ phải theo QUY TẮC vùng (xem khối chú thích đầu tệp)")
        # (3) mẫu khai báo phải KHỚP mẫu tự dò từ cây — canh TRÔI giữa lời khai và cây thật.
        tu_do = chotcay.mau_vung_chuan(goc=GOC_CAY)
        self.assertEqual(tuple(sorted(PHAM_VI_WAVE)), tuple(sorted(tu_do)),
                         f"mẫu KHAI BÁO {PHAM_VI_WAVE} KHÁC mẫu TỰ DÒ {tu_do} ⇒ lời khai đã trôi "
                         f"khỏi cây")
        # Đối chứng dương: bộ dò phải THẤY được một mục cố ý đặt sai chỗ.
        self.assertFalse(all("app/webhook.py".startswith(t) for t in THU_MUC_PHAM_VI),
                         "bộ dò mù: nó cho `app/webhook.py` là nằm trong phạm vi")
        _dc_am("cay-sach-pham-vi")
        _dc_duong("cay-sach-pham-vi")
        print(f"  [nền] phạm vi wave: {len(PHAM_VI_WAVE)} mục VÙNG cho {len(PHAM_VI_LAN_NHA)} mẫu "
              f"của làn này · đích danh làn khác={len(PHAM_VI_LAN_KHAC)} (phải 0)")

    def test_a1c_pham_vi_wave_khong_muc_ruong(self):
        """Mỗi mục miễn trừ phải KHỚP một đường CÓ THẬT (git theo dõi hoặc có trên đĩa).

        Không có ca này thì một miễn trừ chết (gõ sai đường) vẫn nằm đó trông như đang canh gác.
        Với miễn trừ theo QUY TẮC, câu hỏi đổi thành: **mỗi VÙNG phải có thật** — một vùng bịa ra
        (`thu_khong_ton_tai/`) sẽ tha một thư mục chưa ai kiểm.
        """
        theo_doi = set(_git("ls-files").stdout.splitlines())
        self.assertGreater(len(theo_doi), 100, "`git ls-files` rỗng ⇒ ca này không đo gì")
        chet = []
        for m in PHAM_VI_WAVE:
            co = any(fnmatch.fnmatch(t, m) for t in theo_doi)
            if not co:                        # tệp MỚI chưa `git add`: vẫn phải có trên đĩa
                co = bool(glob.glob(os.path.join(GOC_CAY, m)))
            if not co:
                chet.append(m)
        self.assertEqual(chet, [], f"miễn trừ MỤC RUỖNG (không khớp đường nào có thật): {chet}")
        _dc_am("cay-sach-muc-ruong")
        _dc_duong("cay-sach-muc-ruong")
        print(f"  [nền] {len(PHAM_VI_WAVE)}/{len(PHAM_VI_WAVE)} VÙNG miễn trừ khớp đường có thật")

    def test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO(self):
        """ĐỐI CHỨNG ÂM BẮT BUỘC: sửa/tạo một tệp SẢN PHẨM ⇒ chốt "cây sạch" PHẢI ĐỎ.

        Bốn tầng, cố ý chồng nhau — một tầng xanh mà tầng khác đỏ thì ca này đỏ:
          (1) HÀM THUẦN: dòng porcelain của tệp sản phẩm không được lọc mất (kể cả dòng ĐỔI TÊN
              kéo tệp sản phẩm VÀO thư mục thử);
          (2) GIT THẬT trên CÂY TẠM: `app/webhook.py` (đã commit) bị sửa ⇒ cổng ĐỎ, còn khi chỉ
              tệp của vùng thử bẩn ⇒ cổng XANH (đối chứng DƯƠNG của chính phép đo);
          (3) GIT THẬT trên CÂY ĐANG ĐO: một tệp mới xuất hiện trong `app/` ⇒ cổng ĐỎ; xoá đi ⇒
              cổng XANH LẠI. Đây đúng khuôn `N-G19-03` — chỉ khác: lần này nó PHẢI đỏ;
          (4) GIT THẬT trên CÂY ĐANG ĐO: tệp mới trong VÙNG THỬ ⇒ cổng vẫn XANH (đúng N-G19-03).
        Không tệp sản phẩm nào của cây thật bị sửa nội dung: tầng (3)/(4) chỉ TẠO RỒI XOÁ một tệp
        tạm trong `finally`, tầng (2) sửa trên cây sao chép.
        """
        # (1) hàm thuần
        gia = [" M app/webhook.py", " M app/server.py", "?? mock/tep_moi.json", " M app/cau_hinh.py",
               "R  app/gioi_han.py -> thu_giao_dien/gioi_han.py"]
        self.assertEqual(_loc_cay_ban(gia, PHAM_VI_WAVE), gia,
                         "hàm lọc NUỐT tệp sản phẩm ⇒ cổng mất răng")
        self.assertEqual(_loc_cay_ban(["?? app/thu/thu_g21_chotcay.py"], PHAM_VI_WAVE), [],
                         "hàm lọc KHÔNG tha tệp của làn khác trong vùng thử ⇒ N-G19-03 tái diễn")
        self.assertEqual(_loc_cay_ban(gia), gia,
                         "`ngoai=()` phải là HÀM THUẦN (trả về MỌI dòng bẩn), không có chính sách ẩn")
        # (2) git THẬT trên cây tạm
        tam = tempfile.mkdtemp(prefix="veh-g17-dc-am-")
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
            # chỉ tệp CỦA VÙNG THỬ bẩn ⇒ phải XANH (đối chứng dương của chính phép đo)
            with open(os.path.join(tam, "app/thu/thu_g21_gia.py"), "a", encoding="utf-8") as f:
                f.write("them\n")
            self.assertEqual(_loc_cay_ban(
                _git("status", "--porcelain=v1", "-uall", goc=tam).stdout.splitlines(), mau_tam), [],
                "tệp của vùng thử làm cổng ĐỎ ⇒ N-G19-03 tái diễn")
            # SỬA TỆP SẢN PHẨM ⇒ phải ĐỎ
            with open(os.path.join(tam, "app/webhook.py"), "a", encoding="utf-8") as f:
                f.write("SUA SAN PHAM\n")
            ban = _loc_cay_ban(_git("status", "--porcelain=v1", "-uall", goc=tam).stdout.splitlines(),
                               mau_tam)
            self.assertEqual(len(ban), 1, f"cổng MÙ với tệp sản phẩm bị sửa: {ban}")
            self.assertIn("app/webhook.py", ban[0])
        finally:
            shutil.rmtree(tam, ignore_errors=True)

        # (3) git THẬT trên CÂY ĐANG ĐO — tạo rồi xoá, không đụng nội dung tệp nào
        tam_that = os.path.join(GOC_APP, "_ag05_doi_chung_am_tam_g17.py")
        self.assertFalse(os.path.exists(tam_that), f"đường tạm đã tồn tại: {tam_that}")
        try:
            with open(tam_that, "w", encoding="utf-8") as f:
                f.write("# TỆP TẠM CỦA ĐỐI CHỨNG ÂM — bộ thử tự xoá, không phải mã sản phẩm\n")
            ban = _chot_do()
            self.assertIn("_ag05_doi_chung_am_tam_g17.py", " ".join(ban),
                          f"cổng MÙ với tệp mới trong `app/`: {ban}")
            self.assertIn("_ag05_doi_chung_am_tam_g17.py", ban[0])
        finally:
            if os.path.exists(tam_that):
                os.remove(tam_that)
        self.assertEqual(_chot_do(), [], "cây KHÔNG sạch lại sau khi xoá tệp tạm")

        # (4) tệp MỚI TRONG VÙNG THỬ ⇒ cổng vẫn XANH (đúng N-G19-03, đo được chứ không suy luận)
        trong_vung = os.path.join(THU_MUC_THU, "_ag05_doi_chung_duong_g17.py")
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
        print("  [nền] ĐỐI CHỨNG ÂM: tệp sản phẩm bị sửa/tạo ⇒ cổng ĐỎ ở CẢ 4 tầng; "
              "tệp của làn khác trong VÙNG THỬ ⇒ cổng vẫn XANH")

    def test_a2_loi_moi_truong_git_config(self):
        """`N-G17-00`/`N-G18-00` — môi trường git DỊ DẠNG, đo bằng bộ soi DÙNG CHUNG.

        Ba khẳng định, và khẳng định thứ ba mới là khẳng định đáng giá:
          1. gia đình `GIT_CONFIG_*` dị dạng được NHẬN RA (không phải "git tự nhiên hỏng");
          2. dạng đã chuẩn hoá chạy được (exit 0) — nếu không thì MỌI số đo đều vô hiệu;
          3. **KHÔNG nuốt lỗi thật**: lệnh git hỏng vì lý do thật vẫn phải hỏng, kèm stderr thật
             (`thu_g21_chotcay::E_MoiTruongGit.test_e3` giữ phần chứng minh đầy đủ).
        """
        ban = chotcay.soi_gia_dinh_git()
        sach = _git("status", "--porcelain=v1")
        self.assertEqual(sach.returncode, 0, f"git hỏng NGAY CẢ khi đã chuẩn hoá: "
                                             f"{sach.stderr.strip()}")
        _dc_duong("git-sau-khi-go-bien")
        print(f"  [môi trường] GIT_CONFIG_COUNT={ban['count']!r} · khoá={ban['so_khoa']} · "
              f"giá trị={ban['so_gia_tri']} · dị dạng={ban['di_dang']}")
        if ban["di_dang"]:
            print(f"  [môi trường] {ban['ly_do']}")
            print(f"  [môi trường] ĐÃ CHUẨN HOÁ (kèm cảnh báo ở stderr): gỡ {ban['go_bo']}")
        # (3) lỗi THẬT không bị nuốt: rev không tồn tại phải hỏng, và stderr phải có nội dung.
        r = _git("rev-parse", "khong-co-rev-nay-dau-1234567")
        self.assertNotEqual(r.returncode, 0, "rev KHÔNG tồn tại mà git thoát 0 ⇒ nuốt lỗi thật")
        self.assertTrue((r.stderr or "").strip(), "lỗi thật nhưng KHÔNG có stderr để đối chiếu")
        print(f"  [môi trường] lỗi THẬT vẫn nổi lên: rev lạ → mã thoát {r.returncode} "
              f"({(r.stderr or '').strip().splitlines()[0][:60]}…)")

    def test_a3_nen_khong_lay_tu_main(self):
        """Đề bài: `main = de740dc` và KHÔNG chứa G13–G16 ⇒ phải đo được, không tin lời khai."""
        main = _git("rev-parse", "main")
        self.assertEqual(main.returncode, 0, "không đọc được nhánh `main`")
        m = main.stdout.strip()
        co = _git("cat-file", "-e", f"{m}:docs/G16_ACCEPTANCE.md").returncode
        self.assertNotEqual(co, 0, "`main` ĐÃ chứa docs/G16_ACCEPTANCE.md ⇒ nền không như đề bài")
        _dc_duong("main-khong-chua-g16")
        g16 = _git("cat-file", "-e", "HEAD:docs/G16_ACCEPTANCE.md")
        self.assertEqual(g16.returncode, 0, "HEAD thiếu docs/G16_ACCEPTANCE.md ⇒ sai nền")
        _dc_duong("head-co-g16")
        tien = _git("rev-list", "--count", f"{m}..HEAD").stdout.strip()
        nghich = _git("rev-list", "--count", f"HEAD..{m}").stdout.strip()
        la_goc = _git("merge-base", "--is-ancestor", m, "HEAD").returncode == 0
        print(f"  [nền] main={m[:7]} · main..HEAD={tien} · HEAD..main={nghich} · main là tổ tiên: {la_goc}")

    def test_a4_moi_lop_adapter_deu_tat_live(self):
        """F0-b: đọc ĐỘNG từ sổ đăng ký, không đọc hằng viết cứng."""
        self.assertGreaterEqual(len(adapter._DANG_KY), 2, "sổ đăng ký adapter rỗng ⇒ phép đo vô nghĩa")

        def quet(dang_ky):
            return sorted(m for m, lop in dang_ky.items() if getattr(lop, "CHO_PHEP_LIVE", False))

        self.assertEqual(quet(adapter._DANG_KY), [],
                         "có lớp adapter MỞ LIVE ⇒ CRITICAL, CHẶN (F0-b)")
        _dc_duong("cho-phep-live-tat")
        # ĐỐI CHỨNG DƯƠNG cho chính bộ dò: nó PHẢI thấy được một lớp giả có live=True.
        gia = type("AdapterGia", (), {"CHO_PHEP_LIVE": True})
        self.assertEqual(quet({"gia": gia}), ["gia"], "bộ dò live MÙ ⇒ 'tất cả đều tắt' không chứng minh gì")
        _dc_duong("bo-do-live-co-rang")
        print(f"  [live] sổ đăng ký: {sorted(adapter._DANG_KY)} — mở live: KHÔNG lớp nào")

    def test_a5_adapter_khong_co_duong_mang_that(self):
        """F0-c: quét AST (không grep) trên `app/adapter*.py`."""
        self.assertTrue(_quet_import_mang("import requests"),
                        "bộ quét import mạng MÙ với mẫu dương ⇒ kết quả 'sạch' không chứng minh gì")
        _dc_duong("bo-quet-mang-co-rang")
        for ten in ("adapter.py", "adapter_jt.py", "adapter_vtp.py"):
            thay = _quet_import_mang(_doc_app(ten))
            self.assertEqual(thay, [], f"{ten} có đường mạng thật ⇒ CRITICAL, CHẶN (F0-c): {thay}")
        _dc_duong("adapter-khong-co-mang")

    def test_a6_khong_co_ket_noi_ra_ngoai(self):
        """Bộ đếm socket: mọi lượt `connect` ra ngoài LOOPBACK đều bị chặn và GHI LẠI."""
        ghi = []

        class _Dem:
            def __enter__(s):
                s.goc = socket.socket.connect

                def _connect(sock, dia_chi):
                    host = dia_chi[0] if isinstance(dia_chi, tuple) else str(dia_chi)
                    if host in ("127.0.0.1", "::1", "localhost"):
                        return s.goc(sock, dia_chi)
                    ghi.append(host)
                    raise RuntimeError(f"CHẶN G17: cấm kết nối ra ngoài loopback ({host})")

                socket.socket.connect = _connect
                return s

            def __exit__(s, *a):
                socket.socket.connect = s.goc

        with _Dem():
            ad = adapter.tao_adapter("jt", {"apiAccount": "qa17", "privateKey": "pk-gia"}, "mock")
            kq = ad.createOrder({
                "ma_don": "QA17-D1", "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0900000001",
                "nguoi_gui_dia_chi": "1 Le Loi", "nguoi_gui_tinh": "HN", "nguoi_gui_quan": "Q1",
                "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0900000002", "nguoi_nhan_dia_chi": "2 NH",
                "nguoi_nhan_tinh": "HCM", "nguoi_nhan_quan": "Q2", "khoi_luong_gram": 1000,
                "cod": 0, "gia_tri_khai": 0})
            self.assertTrue(getattr(kq, "ok", False) or getattr(kq, "tho", None) is not None,
                            "lượt mock không trả kết quả ⇒ phép đo không chạy qua đường nào")
            ma, _, _ = goi("/api/v2/suc-khoe")          # cửa CÔNG KHAI, không cần phiên
            self.assertIn(ma, (200, 503), f"máy chủ nội bộ trả {ma} ⇒ phép đo không đi qua HTTP")
            self.assertEqual(ghi, [], f"CÓ kết nối ra NGOÀI loopback: {ghi}")
            _dc_duong("khong-ra-ngoai")
            # ĐỐI CHỨNG DƯƠNG: bộ đếm PHẢI bắt được một lượt ra ngoài (TEST-NET-3, không gói nào rời máy).
            with self.assertRaises(RuntimeError):
                socket.create_connection(("203.0.113.9", 80), timeout=1)
            self.assertEqual(ghi, ["203.0.113.9"], "bộ đếm KHÔNG thấy lượt ra ngoài ⇒ nó mù")
            _dc_duong("bo-dem-mang-co-rang")

    def test_a7_csdl_van_la_sqlite(self):
        """D-8: KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL."""
        kn = csdl.mo()
        self.assertEqual(type(kn).__module__, "sqlite3", "CSDL nghiệp vụ KHÔNG còn là SQLite (D-8)")
        self.assertTrue(cau_hinh.DUONG_DAN_CSDL.endswith("hub.db"), f"đường CSDL lạ: {cau_hinh.DUONG_DAN_CSDL}")
        self.assertIn(_TAM, cau_hinh.DUONG_DAN_CSDL, "bộ thử đang trỏ ra NGOÀI thư mục tạm của nó!")
        _dc_duong("sqlite-d8")
        self.assertTrue(_quet_driver_csdl("import psycopg2"),
                        "bộ quét driver CSDL MÙ với mẫu dương ⇒ 'sạch' không chứng minh gì")
        _dc_duong("bo-quet-csdl-co-rang")
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py"):
                continue
            thay = _quet_driver_csdl(_doc_app(ten))
            self.assertEqual(thay, [], f"app/{ten} import driver CSDL khác SQLite: {thay}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. V5 — CÁCH LY TENANT TOÀN CỤC (mục MỞ §L2.8 `QA_G13_G15.md`)
# ══════════════════════════════════════════════════════════════════════════════════════════════
class B_TenantCachLy(unittest.TestCase):
    """Hai tenant A/B THẬT trong CSDL tạm; mọi cửa `/api/v2/*` bị B gõ thử.

    FAIL nếu BẤT KỲ cửa nào để tenant B thấy/ghi/xoá dữ liệu của A, hoặc nhận `tenant_id`
    từ body/query thay vì từ PHIÊN.
    """

    def test_b0_may_chu_loopback_cong_dong(self):
        mt = moi_truong()
        self.assertEqual(mt["dia_chi"], "127.0.0.1", "máy chủ đo KHÔNG bind loopback")
        self.assertNotIn(mt["cong"], CONG_CO_DINH, "trùng cổng cố định của bộ khác ⇒ HỎNG GIẢ (R-13)")
        self.assertGreater(mt["cong"], 1024)
        _dc_duong("cong-dong-loopback")
        print(f"\n  [V5] máy chủ dự án: http://{mt['dia_chi']}:{mt['cong']} · CSDL tạm: {_TAM}")

    def test_b1_doi_chung_duong_chu_nha_thay_du_lieu_minh(self):
        mt = moi_truong()
        ma, than, tho = goi("/api/v2/khach-hang", mt["a_owner"])
        self.assertEqual(ma, 200, f"chủ tenant A không đọc được khách của mình: {than}")
        self.assertIn(mt["canary"], tho, "A KHÔNG thấy dữ liệu của chính A ⇒ mọi ca âm sau là vô nghĩa")
        ma2, than2, tho2 = goi("/api/v2/tenant", mt["a_owner"])
        self.assertEqual(ma2, 200)
        self.assertIn(mt["canary"], tho2, "tên tenant A phải hiện với chính A")
        _dc_duong("chu-nha-thay-du-lieu")
        print(f"  [V5] đối chứng dương: A thấy {len(than.get('khach_hang', []))} khách + tên tenant của mình")

    def test_b2_quet_moi_cua_khong_ro_canary(self):
        """Quét MỌI đường tĩnh rút từ `server.py`. B gọi từng cửa; canary của A phải VẮNG."""
        mt = moi_truong()
        cua = duong_tinh()
        self.assertGreaterEqual(len(cua), 15, f"chỉ rút được {len(cua)} cửa ⇒ phép quét không phủ")
        _dc_duong("rut-duoc-danh-sach-cua")
        so_200_b = so_200_a = 0
        for d in cua:
            ma, _, tho = goi(d, mt["b_owner"])
            self.assertNotIn(mt["canary"], tho, f"RÒ CHÉO TENANT qua {d} (B thấy dữ liệu A)")
            so_200_b += (ma == 200)
            ma_a, _, tho_a = goi(d, mt["a_owner"])
            so_200_a += (ma_a == 200)
        _dc_am("quet-moi-cua")
        self.assertGreaterEqual(so_200_a, 3,
                                f"chỉ {so_200_a}/{len(cua)} cửa trả 200 cho CHÍNH CHỦ ⇒ phép quét có thể đang "
                                "gõ vào tường chết, kết quả 'không rò' không chứng minh gì")
        _dc_duong("quet-moi-cua")
        print(f"  [V5] quét {len(cua)} cửa: A được 200 ở {so_200_a} cửa · B được 200 ở {so_200_b} cửa · "
              f"canary rò sang B: KHÔNG")

    def test_b3_doc_cheo_mot_ban_ghi(self):
        mt = moi_truong()
        ma_b, _, _ = goi(f"/api/v2/khach-hang/{mt['kh_a']}", mt["b_owner"])
        self.assertEqual(ma_b, 404, "B đọc được khách hàng của A (đáng lẽ 404)")
        _dc_am("doc-cheo-ban-ghi")
        ma_a, _, tho_a = goi(f"/api/v2/khach-hang/{mt['kh_a']}", mt["a_owner"])
        self.assertEqual(ma_a, 200, "A KHÔNG đọc được khách của chính A ⇒ ca âm trên vô nghĩa")
        self.assertIn(mt["canary"], tho_a)
        _dc_duong("doc-cheo-ban-ghi")

    def test_b4_tenant_id_trong_body_bi_bo_qua(self):
        mt = moi_truong()
        ma, than, _ = goi("/api/v2/khach-hang", mt["b_owner"], "POST",
                          {"ten": f"Khach do B tao {mt['duoi']}", "tenant_id": mt["tid_a"]})
        self.assertEqual(ma, 201, f"B không tạo được khách cho chính mình: {than}")
        _dc_duong("tao-khach-cua-minh")
        hang = csdl.mot("SELECT tenant_id FROM khach_hang WHERE id=?", (than["id"],))
        self.assertEqual(hang["tenant_id"], mt["tid_b"],
                         "`tenant_id` từ BODY được dùng ⇒ CRITICAL (phải lấy từ PHIÊN)")
        _dc_am("tenant-id-tu-body")
        _dc_duong("tenant-id-tu-body")

    def test_b5_tenant_id_tu_query_bi_bo_qua(self):
        mt = moi_truong()
        kq = do_ro_canary_sang_B()          # CÙNG hàm mà driver đột biến M4 dùng để đo
        self.assertEqual(kq["ma"], 200)
        self.assertFalse(kq["ro"], "`tenant_id` từ QUERY được dùng ⇒ CRITICAL (B thấy canary của A)")
        _dc_am("tenant-id-tu-query")
        ma_a, _, tho_a = goi(f"/api/v2/khach-hang?tenant_id={mt['tid_a']}", mt["a_owner"])
        self.assertEqual(ma_a, 200)
        self.assertIn(mt["canary"], tho_a, "A không thấy dữ liệu của chính A ⇒ ca âm vô nghĩa")
        _dc_duong("tenant-id-tu-query")

    def test_b6_doi_tenant_khong_co_membership(self):
        mt = moi_truong()
        ma, _, _ = goi("/api/v2/auth/doi-tenant", mt["b_owner"], "POST", {"tenant_id": mt["tid_a"]})
        self.assertEqual(ma, 403, "B đổi được sang tenant A mà không có membership")
        _dc_am("doi-tenant")
        _dc_duong("doi-tenant")
        ma2, than2, _ = goi("/api/v2/auth/doi-tenant", mt["hai"], "POST", {"tenant_id": mt["tid_b"]})
        self.assertEqual(ma2, 200, f"người CÓ membership hai tenant lại không đổi được: {than2}")

    def test_b7_xoa_cheo_membership(self):
        mt = moi_truong()
        u = _user(f"qa-g17-throwaway-{mt['duoi']}")
        _gan(u, mt["tid_a"], "TENANT_STAFF")
        mid = csdl.mot("SELECT id FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
                       (u, mt["tid_a"]))["id"]
        ma_b, _, _ = goi(f"/api/v2/memberships/{mid}", mt["b_owner"], "DELETE")
        self.assertEqual(ma_b, 404, "B XOÁ được membership của tenant A")
        self.assertIsNotNone(csdl.mot("SELECT 1 x FROM tenant_memberships WHERE id=?", (mid,)),
                             "membership của A đã bị B xoá thật")
        _dc_am("xoa-cheo-membership")
        ma_a, _, _ = goi(f"/api/v2/memberships/{mid}", mt["a_owner"], "DELETE")
        self.assertEqual(ma_a, 200, "chủ A không xoá được thành viên của chính A ⇒ ca âm vô nghĩa")
        _dc_duong("xoa-cheo-membership")

    def test_b8_tai_khoan_hang_khong_lo_sang_tenant_khac(self):
        mt = moi_truong()
        wh_a = mt["wh"][(mt["tid_a"], "jt")]
        ma, _, tho = goi("/api/v2/tai-khoan-hang", mt["b_owner"])
        self.assertEqual(ma, 200)
        self.assertNotIn(wh_a, tho, "B thấy `webhook_ma` của tài khoản hãng tenant A")
        _dc_am("tai-khoan-hang-cheo")
        ma2, _, tho2 = goi("/api/v2/tai-khoan-hang", mt["a_owner"])
        self.assertEqual(ma2, 200)
        self.assertIn(wh_a, tho2, "A KHÔNG thấy tài khoản hãng của chính A ⇒ ca âm vô nghĩa")
        _dc_duong("tai-khoan-hang-cheo")

    def test_b9_webhook_vo_danh_sai_chu_ky_khong_tao_su_kien(self):
        mt = moi_truong()
        wh_a = mt["wh"][(mt["tid_a"], "jt")]
        truoc = csdl.mot("SELECT COUNT(*) c FROM wh_su_kien")["c"]
        ma, _, _ = goi(f"/api/v2/webhook/nhan/{wh_a}", None, "POST", {"ma_van_don": "QA17-X"},
                       csrf=False, headers={"Content-Type": "application/json"})
        self.assertEqual(ma, 401, f"webhook không chặn chữ ký sai (trả {ma})")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM wh_su_kien")["c"], truoc,
                         "chữ ký SAI vẫn ghi được sự kiện")
        _dc_am("webhook-chu-ky-sai")
        ma2, _, _ = goi("/api/v2/webhook/nhan/khong-co-that-qa17", None, "POST", {},
                        csrf=False, headers={"Content-Type": "application/json"})
        self.assertEqual(ma2, 404, "cửa webhook không còn phân biệt được mã không tồn tại ⇒ ca âm vô nghĩa")
        _dc_duong("webhook-chu-ky-sai")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. V6 — RBAC (mục MỞ §L2.8) — ma trận ĐỘNG trên `role_permissions`
# ══════════════════════════════════════════════════════════════════════════════════════════════
class C_Rbac(unittest.TestCase):

    def test_c1_viewer_doc_duoc(self):
        """ĐỐI CHỨNG DƯƠNG cho cả nhóm: vai trò thấp nhất vẫn phải ĐỌC được đúng thứ nó có quyền."""
        mt = moi_truong()
        ma, _, tho = goi("/api/v2/khach-hang", mt["a_view"])
        self.assertEqual(ma, 200, "VIEWER không đọc được khách hàng (nó CÓ `tenant.khach.xem`)")
        self.assertIn(mt["canary"], tho)
        _dc_duong("viewer-doc")

    def test_c2_viewer_khong_ghi_duoc(self):
        mt = moi_truong()
        ma, _, _ = goi("/api/v2/khach-hang", mt["a_view"], "POST", {"ten": "Viewer thu ghi"})
        self.assertEqual(ma, 403, "VIEWER GHI được (nó KHÔNG có `tenant.khach.ghi`)")
        _dc_am("quyen-ghi-khach-hang")
        ma2, than2, _ = goi("/api/v2/khach-hang", mt["a_staff"], "POST", {"ten": f"Staff ghi {mt['duoi']}"})
        self.assertEqual(ma2, 201, f"STAFF có `tenant.khach.ghi` mà vẫn không ghi được: {than2}")
        _dc_duong("quyen-ghi-khach-hang")

    def test_c3_viewer_khong_doc_membership(self):
        mt = moi_truong()
        ma, _, _ = goi("/api/v2/memberships", mt["a_view"])
        self.assertEqual(ma, 403, "VIEWER đọc được danh sách thành viên (thiếu `tenant.membership.xem`)")
        _dc_am("quyen-doc-membership")
        ma2, _, _ = goi("/api/v2/memberships", mt["a_owner"])
        self.assertEqual(ma2, 200, "OWNER không đọc được danh sách thành viên ⇒ ca âm vô nghĩa")
        _dc_duong("quyen-doc-membership")

    def test_c4_chan_leo_thang_vai_tro(self):
        """`CAP_DUOC`: TENANT_ADMIN chỉ được cấp STAFF/VIEWER, KHÔNG được cấp OWNER."""
        mt = moi_truong()
        ma, _, _ = goi("/api/v2/memberships", mt["b_admin"], "POST",
                       {"ten_dang_nhap": f"qa-g17-leo-{mt['duoi']}", "mat_khau": "mat-khau-thu-123",
                        "role": "TENANT_OWNER"})
        self.assertEqual(ma, 403, "TENANT_ADMIN CẤP ĐƯỢC vai trò OWNER ⇒ leo thang đặc quyền")
        _dc_am("leo-thang-vai-tro")
        ma2, than2, _ = goi("/api/v2/memberships", mt["b_admin"], "POST",
                            {"ten_dang_nhap": f"qa-g17-thap-{mt['duoi']}", "mat_khau": "mat-khau-thu-123",
                             "role": "TENANT_VIEWER"})
        self.assertEqual(ma2, 201, f"ADMIN không cấp được VIEWER (được phép) ⇒ ca âm vô nghĩa: {than2}")
        _dc_duong("leo-thang-vai-tro")

    def test_c5_staff_khong_quan_ly_thanh_vien(self):
        mt = moi_truong()
        ma, _, _ = goi("/api/v2/memberships", mt["a_staff"], "POST",
                       {"ten_dang_nhap": f"qa-g17-s-{mt['duoi']}", "mat_khau": "mat-khau-thu-123",
                        "role": "TENANT_VIEWER"})
        self.assertEqual(ma, 403, "STAFF mời được thành viên (thiếu `tenant.membership.quan_ly`)")
        _dc_am("quyen-moi-thanh-vien")
        ma2, than2, _ = goi("/api/v2/memberships", mt["a_owner"], "POST",
                            {"ten_dang_nhap": f"qa-g17-o-{mt['duoi']}", "mat_khau": "mat-khau-thu-123",
                             "role": "TENANT_VIEWER"})
        self.assertEqual(ma2, 201, f"OWNER không mời được thành viên ⇒ ca âm vô nghĩa: {than2}")
        _dc_duong("quyen-moi-thanh-vien")

    def test_c6_ma_tran_trong_csdl_khop_nguon(self):
        """Ma trận ĐỘNG: đọc `role_permissions` trong CSDL rồi so với `quyen.MA_TRAN`."""
        moi_truong()

        def so_sanh(nguon):
            lech = {}
            for role, ds in nguon.items():
                trong_csdl = quyen.quyen_cua_vai_tro(role)
                if trong_csdl != set(ds):
                    lech[role] = {"thua": sorted(trong_csdl - set(ds)), "thieu": sorted(set(ds) - trong_csdl)}
            return lech

        tong = csdl.mot("SELECT COUNT(*) c FROM role_permissions")["c"]
        if not tong:
            self.skipTest("CHƯA ĐO: bảng `role_permissions` RỖNG — ma trận rỗng KHÔNG phải ĐẠT "
                          "(yêu cầu Owner/Codex 09:38)")
        print(f"  [V6] ma trận ĐỘNG đọc từ CSDL: {tong} ô (vai trò × quyền)")
        lech = so_sanh(quyen.MA_TRAN)
        self.assertEqual(lech, {}, f"CSDL và mã NGUỒN lệch nhau về quyền: {lech}")
        _dc_duong("ma-tran-khop")
        # ĐỐI CHỨNG DƯƠNG cho chính bộ so: tiêm một quyền lạ vào bản sao ⇒ PHẢI bị bắt.
        gia = dict(quyen.MA_TRAN)
        gia["TENANT_VIEWER"] = list(gia["TENANT_VIEWER"]) + ["tenant.khong.co.that"]
        self.assertNotEqual(so_sanh(gia), {}, "bộ so ma trận MÙ với lệch tiêm vào ⇒ 'khớp' không chứng minh gì")
        _dc_duong("bo-so-ma-tran-co-rang")

    def test_c7_moi_cua_goi_quyen_deu_co_that(self):
        """Mọi `self._can(nc, "X")` trong `server.py` phải dùng quyền CÓ trong `quyen.QUYEN`."""
        nguon = _doc_app("server.py")
        goi_ra = sorted(set(re.findall(r'_can\(nc,\s*"([^"]+)"', nguon)))
        self.assertGreaterEqual(len(goi_ra), 20, f"chỉ thấy {len(goi_ra)} chỗ gọi quyền ⇒ phép quét không phủ")
        la = sorted(p for p in goi_ra if p not in quyen.QUYEN)
        la_la = [p for p in la if p not in PHAT_HIEN_DA_BIET]
        self.assertEqual(la_la, [], f"cửa gọi quyền KHÔNG tồn tại trong `quyen.QUYEN`: {la_la}")
        _dc_duong("moi-cua-co-quyen-that")
        gia = nguon + '\n        self._can(nc, "quyen.khong.ton.tai")\n'
        self.assertIn("quyen.khong.ton.tai",
                      [p for p in re.findall(r'_can\(nc,\s*"([^"]+)"', gia) if p not in quyen.QUYEN],
                      "bộ quét quyền MÙ với quyền lạ tiêm vào")
        _dc_duong("bo-quet-quyen-co-rang")

    def test_c8_phat_hien_N_G17_01_con_dung_va_cua_van_mo(self):
        """`N-G17-01`: quyền ma `tenant.billing.quan_ly`. Sổ phát hiện KHÔNG được mục ruỗng."""
        mt = moi_truong()
        for p, tt in PHAT_HIEN_DA_BIET.items():
            if p in quyen.QUYEN:
                self.fail(f"sổ phát hiện đã CŨ: {p!r} nay đã có trong `quyen.QUYEN` — gỡ mục "
                          f"{tt['ma']} khỏi sổ rồi đo lại")
        self.assertIn("tenant.billing.quan_ly", PHAT_HIEN_DA_BIET,
                      "mục N-G17-01 biến mất khỏi sổ mà không ai gỡ ⇒ sổ không còn trung thực")
        for role in sorted(quyen.MA_TRAN):
            self.assertFalse(quyen.co_quyen(role, "tenant.billing.quan_ly"),
                             f"{role} nay CÓ quyền ma ⇒ mục N-G17-01 đã hết đúng")
        _dc_duong("N-G17-01-con-dung")
        # Cửa `/dang-ky/doi-goi` vẫn PHẢI mở được bằng quyền nền `tenant.membership.quan_ly`;
        # nếu không thì đây là cửa CHẾT và mức độ của N-G17-01 phải nâng lên HIGH.
        ma_v, _, _ = goi("/api/v2/dang-ky/doi-goi", mt["a_view"], "POST", {"goi_id": "pro"})
        self.assertEqual(ma_v, 403, "VIEWER đổi được gói dịch vụ")
        _dc_am("cua-doi-goi")
        ma_o, _, _ = goi("/api/v2/dang-ky/doi-goi", mt["a_owner"], "POST", {"goi_id": "pro"})
        self.assertNotEqual(ma_o, 403, "chủ tenant bị 403 ở cửa đổi gói ⇒ cửa CHẾT, N-G17-01 lên HIGH")
        _dc_duong("cua-doi-goi")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. V7 — AES-256-GCM ĐẦY ĐỦ (mục MỞ §L2.8) — bộ ca RIÊNG, không mượn `thu_bao_mat.py`
# ══════════════════════════════════════════════════════════════════════════════════════════════
class D_MaHoa(unittest.TestCase):

    def test_d1_di_ve_nguyen_ven(self):
        """ĐỐI CHỨNG DƯƠNG cho cả nhóm."""
        mt = moi_truong()
        ban_ma = bao_mat.ma_hoa_v3("bi-mat-g17", bao_mat.aad_credentials(mt["tid_a"], "jt"))
        self.assertEqual(bao_mat.giai_ma(ban_ma, bao_mat.aad_credentials(mt["tid_a"], "jt")),
                         "bi-mat-g17")
        _dc_duong("aes-di-ve")

    def test_d2_sua_mot_byte_ban_ma_phai_hong(self):
        moi_truong()
        ban_ma = bao_mat.ma_hoa_v3("bi-mat-g17", "aad-g17")
        phan = ban_ma.split("$")
        ct = bytearray(bytes.fromhex(phan[3]))
        ct[0] ^= 0x01                                   # LẬT MỘT BIT của bản mã
        hong = "$".join(phan[:3] + [bytes(ct).hex()])
        with self.assertRaises(Exception):
            bao_mat.giai_ma(hong, "aad-g17")
        _dc_am("aes-sua-ban-ma")
        # đối chứng dương: bản mã CHƯA sửa vẫn đọc được ⇒ ca âm không phải vì hàm hỏng
        self.assertEqual(bao_mat.giai_ma(ban_ma, "aad-g17"), "bi-mat-g17")
        _dc_duong("aes-sua-ban-ma")

    def test_d3_sai_aad_phai_hong(self):
        moi_truong()
        ban_ma = bao_mat.ma_hoa_v3("bi-mat-g17", "cred:1:jt")
        with self.assertRaises(Exception):
            bao_mat.giai_ma(ban_ma, "cred:2:jt")        # SAI AAD (tenant khác)
        _dc_am("aes-sai-aad")
        self.assertEqual(bao_mat.giai_ma(ban_ma, "cred:1:jt"), "bi-mat-g17")
        _dc_duong("aes-sai-aad")

    def test_d4_doi_cho_ban_ma_giua_hai_tenant(self):
        """Đổi chỗ HAI BẢN MÃ trong CSDL: hàng của A mang bản mã của B ⇒ đọc bằng AAD của A PHẢI hỏng."""
        mt = moi_truong()
        a = csdl.mot("SELECT id, credentials_ma_hoa FROM carrier_accounts WHERE tenant_id=? AND hang='jt'",
                     (mt["tid_a"],))
        b = csdl.mot("SELECT id, credentials_ma_hoa FROM carrier_accounts WHERE tenant_id=? AND hang='jt'",
                     (mt["tid_b"],))
        self.assertNotEqual(a["credentials_ma_hoa"], b["credentials_ma_hoa"], "hai tenant dùng CHUNG bản mã")
        self.assertEqual(bao_mat.giai_ma_cred(a["credentials_ma_hoa"], mt["tid_a"], "jt")["tenant"],
                         mt["tid_a"], "bản mã của A không đọc được bằng AAD của A")
        _dc_duong("aes-doi-cho-ban-ma")
        try:
            csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                     (b["credentials_ma_hoa"], a["id"]))
            with self.assertRaises(Exception):
                bao_mat.giai_ma_cred(b["credentials_ma_hoa"], mt["tid_a"], "jt")
            _dc_am("aes-doi-cho-ban-ma")
        finally:
            csdl.ghi("UPDATE carrier_accounts SET credentials_ma_hoa=? WHERE id=?",
                     (a["credentials_ma_hoa"], a["id"]))

    def test_d5_ban_ma_mang_key_id(self):
        moi_truong()
        ban_ma = bao_mat.ma_hoa_v3("bi-mat-g17", "aad-g17")
        kid = bao_mat.key_id_cua(ban_ma)
        self.assertIsNotNone(kid, "bản mã v3 KHÔNG mang `key_id` ⇒ không xoay khoá được")
        _dc_duong("aes-co-key-id")
        self.assertIsNone(bao_mat.key_id_cua("v2$00$00"), "bản mã v2 lại khai có key_id")
        self.assertFalse(bao_mat.can_xoay(ban_ma), "bản mã MỚI đã bị coi là cần xoay")

    def test_d6_khong_goi_tran_ma_hoa_giai_ma(self):
        """§3/§14: `ma_hoa`/`giai_ma` trần chỉ được dùng trong `bao_mat.py` và `migrate.py`."""
        cam = {"bao_mat.py", "migrate.py"}
        self.assertTrue(_goi_tran_ma_hoa("x.ma_hoa('a')"),
                        "bộ quét gọi trần MÙ với mẫu dương ⇒ 'sạch' không chứng minh gì")
        _dc_duong("bo-quet-goi-tran-co-rang")
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py") or ten in cam:
                continue
            thay = _goi_tran_ma_hoa(_doc_app(ten))
            self.assertEqual(thay, [], f"app/{ten} gọi TRẦN `ma_hoa`/`giai_ma`: {thay}")
        _dc_duong("khong-goi-tran")

    def test_d8_bon_ham_hop_dong_chi_duoc_goi_khong_duoc_viet_lai(self):
        """Hợp đồng §3 (yêu cầu Owner/Codex 09:38): bốn hàm `*_cred`/`*_wh` CHỈ được GỌI."""
        hop_dong = ("ma_hoa_cred", "giai_ma_cred", "ma_hoa_wh", "giai_ma_wh")
        for ten in hop_dong:
            self.assertTrue(callable(getattr(bao_mat, ten, None)), f"mất hàm hợp đồng `{ten}`")
        _dc_duong("hop-dong-bon-ham")

        def dinh_nghia_lai(nguon, ten_tep):
            return [f"{ten_tep}:{n.lineno} {n.name}"
                    for n in ast.walk(ast.parse(nguon))
                    if isinstance(n, ast.FunctionDef) and n.name in hop_dong]

        gia = "def giai_ma_cred(ban_ma, tenant_id, hang):\n    return {}\n"
        self.assertTrue(dinh_nghia_lai(gia, "gia.py"), "bộ quét định-nghĩa-lại MÙ với mẫu dương")
        _dc_duong("bo-quet-viet-lai-co-rang")
        thay = []
        for ten_tep in sorted(os.listdir(GOC_APP)):
            if ten_tep.endswith(".py") and ten_tep != "bao_mat.py":
                thay += dinh_nghia_lai(_doc_app(ten_tep), ten_tep)
        self.assertEqual(thay, [], f"VIẾT LẠI hợp đồng mã hoá ở nơi khác `bao_mat.py`: {thay}")
        _dc_am("hop-dong-khong-bi-viet-lai")
        _dc_duong("hop-dong-khong-bi-viet-lai")

        # Hợp đồng phải đang được DÙNG thật (nếu không thì đây là hàm chết, không phải hợp đồng).
        noi_goi = sorted(t for t in os.listdir(GOC_APP)
                         if t.endswith(".py") and t != "bao_mat.py"
                         and any(h + "(" in _doc_app(t) for h in hop_dong))
        self.assertGreaterEqual(len(noi_goi), 5, f"chỉ {len(noi_goi)} tệp gọi hợp đồng: {noi_goi}")
        _dc_duong("hop-dong-dang-duoc-dung")
        # Trôi dạt: AES-GCM TRỰC TIẾP chỉ được ở `bao_mat.py` và `sao_luu_khoa.py` (KEK của bản
        # sao lưu — lớp secret KHÁC, có chủ đích). Tệp thứ ba xuất hiện ⇒ có người tự dựng sơ đồ.
        tho = sorted(t for t in os.listdir(GOC_APP) if t.endswith(".py")
                     and ("AESGCM(" in _doc_app(t) or "from cryptography" in _doc_app(t)))
        self.assertEqual(tho, ["bao_mat.py", "sao_luu_khoa.py"],
                         f"AES-GCM trực tiếp xuất hiện ở tệp LẠ: {tho}")
        print(f"  [V7] AES-GCM trực tiếp chỉ ở {tho} · hợp đồng được gọi từ {len(noi_goi)} tệp")

    def test_d7_xoay_khoa_khong_mat_bi_mat(self):
        mt = moi_truong()
        truoc = csdl.mot("SELECT credentials_ma_hoa c FROM carrier_accounts WHERE tenant_id=? AND hang='jt'",
                         (mt["tid_a"],))["c"]
        kid_truoc = bao_mat.key_id_cua(truoc)
        kq = bao_mat.xoay_khoa()
        self.assertEqual(kq.get("hong"), [], f"xoay khoá báo HỎNG: {kq.get('hong')}")
        _dc_duong("xoay-khoa-chay")
        sau = csdl.mot("SELECT credentials_ma_hoa c FROM carrier_accounts WHERE tenant_id=? AND hang='jt'",
                       (mt["tid_a"],))["c"]
        self.assertNotEqual(bao_mat.key_id_cua(sau), kid_truoc, "xoay khoá mà key_id KHÔNG đổi")
        self.assertEqual(bao_mat.giai_ma_cred(sau, mt["tid_a"], "jt")["tenant"], mt["tid_a"],
                         "MẤT BÍ MẬT sau khi xoay khoá (CRITICAL)")
        _dc_duong("xoay-khoa-giu-bi-mat")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. D-9 (area) · D-4 (mã 110) · BỐN THAO TÁC `duong=None` — chốt cứng, không đoán
# ══════════════════════════════════════════════════════════════════════════════════════════════
class E_ChotChan(unittest.TestCase):

    def test_e1_area_chan_duong_live(self):
        with self.assertRaises(Exception) as ctx:
            adapter_jt.chot_chan_anh_xa_area("sandbox", da_xac_nhan=False, nguon="", cap="quan-huyen")
        self.assertIn("D-9", str(ctx.exception), "chặn nhưng KHÔNG nói ra là chốt D-9")
        _dc_am("area-live-bi-chan")
        adapter_jt.chot_chan_anh_xa_area("mock")             # MOCK luôn đi qua
        _dc_duong("area-live-bi-chan")

    def test_e2_area_du_ba_cua_thi_qua(self):
        """Chứng minh chốt D-9 KHÔNG phải 'luôn ném': đủ ba cửa thì phải ĐI QUA được."""
        adapter_jt.chot_chan_anh_xa_area(
            "sandbox", da_xac_nhan=True, cap="quan-huyen",
            nguon="J&T tra loi email ngay 01/01/2027, luu tai docs/JT_CAU_HOI_CHINH_THUC.md")
        _dc_duong("area-thieu-mot-cua")
        for thieu in ({"da_xac_nhan": True, "nguon": "", "cap": "quan-huyen"},
                      {"da_xac_nhan": True, "nguon": "todo", "cap": "quan-huyen"},
                      {"da_xac_nhan": True, "nguon": "x" * 30, "cap": "xa-phuong-la"}):
            with self.assertRaises(Exception):
                adapter_jt.chot_chan_anh_xa_area("sandbox", **thieu)
        _dc_am("area-thieu-mot-cua")

    def test_e3_ma_110_khong_duoc_doan(self):
        """D-4: mã CHƯA XÁC MINH ⇒ KHÔNG áp trạng thái; và TUYỆT ĐỐI không thành 'hoàn tất'."""
        qd = tth.quyet_dinh("jt", 110)
        self.assertTrue(qd.nhap_nhang, "110 không còn được coi là NHẬP NHẰNG ⇒ mất dấu vết D-4")
        self.assertIsNone(qd.trang_thai_ap, "110 bị ÁP một trạng thái ⇒ ĐOÁN (D-4)")
        self.assertIn(qd.nhan, ("AMBIGUOUS", "NEEDS_REVIEW"), f"nhãn soát của 110 là {qd.nhan!r}")
        self.assertNotIn(qd.trang_thai_ap, tth.TRANG_THAI_HOAN_TAT, "110 rơi vào trạng thái HOÀN TẤT")
        _dc_am("ma-110-khong-doan")
        for ma, mong in (("113", "giao_thanh_cong"), ("103", "cho_lay"), ("106", "lay_hang")):
            qd2 = tth.quyet_dinh("jt", ma)
            self.assertEqual(qd2.trang_thai_ap, mong, f"mã ĐÃ xác minh {ma} không áp được {mong}")
            self.assertEqual(qd2.nhan, "OK")
        _dc_duong("ma-110-khong-doan")

    def test_e4_bon_thao_tac_chua_xac_minh_duong(self):
        for tt in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            d = adapter_jt.DUONG_API[tt]
            self.assertIsNone(d["duong"], f"{tt} tự mọc ra một đường dẫn CHƯA xác minh")
            self.assertEqual(d["muc"], adapter_jt.MUC_CHUA_XAC_NHAN, f"{tt} bị đánh dấu ĐÃ ĐỌC")
        _dc_am("bon-thao-tac-duong-none")
        for tt in ("createOrder", "trackOrder"):
            self.assertIsNotNone(adapter_jt.DUONG_API[tt]["duong"], f"{tt} mất đường dẫn ĐÃ đọc")
            self.assertEqual(adapter_jt.DUONG_API[tt]["muc"], adapter_jt.MUC_DA_DOC)
        _dc_duong("bon-thao-tac-duong-none")

    def test_e5_chan_duong_chua_xac_nhan(self):
        for tt in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            adapter_jt.chan_duong_chua_xac_nhan(tt, "mock")          # mock: không có đường ra ngoài
            with self.assertRaises(Exception):
                adapter_jt.chan_duong_chua_xac_nhan(tt, "sandbox")
        _dc_am("chan-duong-chua-xac-nhan")
        adapter_jt.chan_duong_chua_xac_nhan("createOrder", "sandbox")   # ĐÃ đọc ⇒ đi qua
        _dc_duong("chan-duong-chua-xac-nhan")

    def test_e7_cham_hang_thi_TU_CHOI_kem_dung_giay_phep_con_thieu(self):
        """Mọi đường chạm hãng phải ghi BLOCKED kèm ĐÚNG giấy phép còn thiếu — KHÔNG tính là ĐẠT."""
        ok, ly = cau_hinh.jt_kiem_moi_truong("mock")
        self.assertTrue(ok, f"`mock` cũng bị chặn: {ly}")
        _dc_duong("cham-hang-bi-chan")           # đối chứng dương: mock ĐI QUA
        ok_sb, ly_sb = cau_hinh.jt_kiem_moi_truong("sandbox")
        self.assertFalse(ok_sb, "`sandbox` ĐƯỢC PHÉP ⇒ vi phạm tuyệt đối #1 của đề bài")
        _dc_am("cham-hang-bi-chan")
        for ma in ("V-G09-01", "V-13906-05"):
            self.assertIn(ma, ly_sb, f"lý do chặn KHÔNG nêu giấy phép còn thiếu `{ma}`: {ly_sb}")
        ok_pr, ly_pr = cau_hinh.jt_kiem_moi_truong("production")
        self.assertFalse(ok_pr, "`production` ĐƯỢC PHÉP")
        self.assertIn("duyệt", ly_pr.lower(), f"lý do chặn production không nói cần ai duyệt: {ly_pr}")
        with self.assertRaises(PermissionError) as ctx:
            adapter_jt.chan_moi_truong_chua_duoc_cap("sandbox")
        self.assertIn("V-G09-01", str(ctx.exception))
        for tt in ("cancelOrder", "getShippingFee", "getShippingLabel", "getOrder"):
            with self.assertRaises(Exception) as ctx2:
                adapter_jt.chan_duong_chua_xac_nhan(tt, "sandbox")
            self.assertIn(tt, str(ctx2.exception), f"lý do chặn không nêu thao tác `{tt}`")
            self.assertIn("CHƯA được xác minh", str(ctx2.exception))
        _dc_am("cham-hang-ten-giay-phep")
        # ĐỐI CHỨNG DƯƠNG: chốt đường dẫn KHÔNG phải "chặn tất" — thao tác ĐÃ đọc đường thì đi qua.
        adapter_jt.chan_duong_chua_xac_nhan("createOrder", "sandbox")
        _dc_duong("cham-hang-ten-giay-phep")

    def test_e6_dung_adapter_ngoai_mock_bi_chan(self):
        for ma_hang in sorted(adapter._DANG_KY):
            for mt in ("sandbox", "production"):
                with self.assertRaises(PermissionError):
                    adapter.tao_adapter(ma_hang, {"apiAccount": "x", "privateKey": "y"}, mt)
        _dc_am("dung-adapter-ngoai-mock")
        for ma_hang in sorted(adapter._DANG_KY):
            ad = adapter.tao_adapter(ma_hang, {"apiAccount": "x", "privateKey": "y"}, "mock")
            self.assertEqual(ad.moi_truong, "mock")
        _dc_duong("dung-adapter-ngoai-mock")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# F. TỰ KIỂM BỘ DÒ — ca cố ý hỏng trong tiến trình con + ĐỘT BIẾN trên cây sao chép
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


def _phan_quyet(ma_thoát, ra):
    """BẢN SAO luật phán của `app/thu/chay_tat_ca.sh`: MÃ THOÁT + DẤU VẾT ĐÃ CHẠY + SỐ CA."""
    m = re.findall(r"Ran (\d+)", ra) or re.findall(r"(\d+) ca — ĐẠT", ra)
    n = int(m[-1]) if m else 0
    co_dau_vet = bool(re.search(r"^OK( |$)|ca — ĐẠT", ra, re.M))
    if ma_thoát == 0 and co_dau_vet and n > 0:
        return "ĐẠT"
    if ma_thoát == 0 and n == 0 and "skipped" in ra:
        return "BỎ QUA"
    return "HỎNG"


def _chay_con(nguon, cay_app=None, giay=120, bien_them=None):
    """Chạy một đoạn mã trong TIẾN TRÌNH CON. Trả (mã thoát, output)."""
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    f.write(nguon)
    f.close()
    env = dict(os.environ)
    env["VIP_G17_DATA"] = tempfile.mkdtemp(prefix="veh-g17-drv-")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Cây đột biến (nếu có) đứng TRƯỚC cây gốc; thư mục bộ thử để driver import được chính tệp này.
    env["PYTHONPATH"] = os.pathsep.join(
        [cay_app or GOC_APP, THU_MUC_THU] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    env.update(bien_them or {})          # đè sau cùng: dùng để tiêm nền KHÔNG phải thư mục tạm
    r = subprocess.run([sys.executable, f.name], capture_output=True, text=True, env=env,
                       cwd=GOC_CAY, timeout=giay)
    return r.returncode, r.stdout + r.stderr


def _cay_dot_bien(thay_doi):
    """Sao chép `app/*.py` sang thư mục tạm rồi tiêm đột biến. KHÔNG đụng cây thật."""
    thu_muc = tempfile.mkdtemp(prefix="veh-g17-dotbien-")
    for ten in sorted(os.listdir(GOC_APP)):
        if ten.endswith(".py"):
            shutil.copy2(os.path.join(GOC_APP, ten), os.path.join(thu_muc, ten))
    for ten, cu, moi in thay_doi:
        duong = os.path.join(thu_muc, ten)
        with open(duong, encoding="utf-8") as f:
            nguon = f.read()
        if cu not in nguon:
            raise AssertionError(f"đột biến KHÔNG áp được: không thấy mẫu trong app/{ten}")
        with open(duong, "w", encoding="utf-8") as f:
            f.write(nguon.replace(cu, moi))
    return thu_muc


def _goi_tran_ma_hoa(nguon):
    """AST: các lượt gọi `ma_hoa(...)` / `giai_ma(...)` TRẦN (không tính `ma_hoa_v3`, `giai_ma_cred`…)."""
    thay = []
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Call):
            f = nut.func
            ten = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
            if ten in ("ma_hoa", "giai_ma"):
                thay.append(f"{ten}() dòng {nut.lineno}")
    return thay


def do_ro_canary_sang_B():
    """PHÉP ĐO dùng chung cho ca `b5` và cho DRIVER ĐỘT BIẾN `M4` (cùng một đường đo)."""
    mt = moi_truong()
    ma, _, tho = goi(f"/api/v2/khach-hang?tenant_id={mt['tid_a']}", mt["b_owner"])
    return {"ma": ma, "ro": mt["canary"] in tho, "dai": len(tho)}


DRIVER_DOT_BIEN = """import json
import thu_qa_g17 as q
kq = q.do_ro_canary_sang_B()
print("KETQUA=" + json.dumps(kq, ensure_ascii=False))
"""


class F_TuKiemBoDo(unittest.TestCase):
    """Không có nhóm này thì mọi dòng "✓ … ca" của tệp này KHÔNG chứng minh gì."""

    def test_f1_ca_co_y_hong_bi_bo_do_THAY(self):
        ma, ra = _chay_con(MA_THU_HONG)
        self.assertNotEqual(ma, 0, f"bộ dò KHÔNG thấy ca cố ý hỏng (mã thoát {ma})")
        self.assertIn("FAILED", ra, "output ca hỏng không có dấu hiệu hỏng")
        self.assertFalse(re.search(r"^OK( |$)", ra, re.M), "output vừa FAILED vừa có dòng OK")
        _dc_am("tu-kiem-bo-do")

    def test_f2_doi_chung_duong_ca_dat(self):
        ma, ra = _chay_con(MA_THU_DAT)
        self.assertEqual(ma, 0, f"ca ĐẠT lại thoát {ma}: {ra[-300:]}")
        self.assertRegex(ra, r"Ran 1 test")
        self.assertTrue(re.search(r"^OK( |$)", ra, re.M))
        _dc_duong("tu-kiem-bo-do")

    def test_f3_luat_phan_co_rang(self):
        """Luật phán phải TỪ CHỐI được ba kịch bản lừa: thoát 0 mà 0 ca · thoát 0 không dấu vết · thoát ≠ 0."""
        self.assertEqual(_phan_quyet(0, "OK\n"), "HỎNG", "thoát 0 KHÔNG chạy ca nào mà vẫn được ĐẠT")
        self.assertEqual(_phan_quyet(0, "chay xong, khong in gi"), "HỎNG", "thoát 0 không dấu vết vẫn ĐẠT")
        self.assertEqual(_phan_quyet(1, "Ran 5 tests\nOK\n"), "HỎNG", "in OK rồi thoát 1 vẫn được ĐẠT")
        self.assertEqual(_phan_quyet(0, "Ran 5 tests\nOK\n"), "ĐẠT")
        self.assertEqual(_phan_quyet(0, "Ran 0 tests\nskipped=3\n"), "BỎ QUA")
        ma_hong, ra_hong = _chay_con(MA_THU_HONG)
        self.assertEqual(_phan_quyet(ma_hong, ra_hong), "HỎNG")
        _dc_am("luat-phan")
        ma_dat, ra_dat = _chay_con(MA_THU_DAT)
        self.assertEqual(_phan_quyet(ma_dat, ra_dat), "ĐẠT")
        _dc_duong("luat-phan")

    def test_f4_dot_bien_M1_bo_AAD_thi_cong_phai_do(self):
        """M1: bỏ AAD khỏi AES-GCM ⇒ ca `d3` (sai AAD phải hỏng) PHẢI đỏ."""
        drv = ('import bao_mat\n'
               'b = bao_mat.ma_hoa_v3("bi-mat-g17", "cred:1:jt")\n'
               'try:\n'
               '    bao_mat.giai_ma(b, "cred:2:jt")\n'
               '    print("KETQUA=RO")\n'
               'except Exception:\n'
               '    print("KETQUA=CHAN")\n')
        _, ra_that = _chay_con(drv)
        self.assertIn("KETQUA=CHAN", ra_that, f"cây THẬT đã rò khi sai AAD: {ra_that[-200:]}")
        _dc_duong("dot-bien-M1")
        cay = _cay_dot_bien([("bao_mat.py", "aad.encode() if aad else None", "None")])
        _, ra_bien = _chay_con(drv, cay_app=cay)
        self.assertIn("KETQUA=RO", ra_bien,
                      f"đột biến bỏ AAD mà phép đo VẪN nói 'chặn' ⇒ cổng V7 KHÔNG có răng: {ra_bien[-200:]}")
        _dc_duong("dot-bien-M1")

    def test_f5_dot_bien_M2_xoa_so_ma_110_thi_cong_phai_do(self):
        drv = ('import trang_thai_hang as t\n'
               'q = t.quyet_dinh("jt", 110)\n'
               'print("KETQUA=" + ("DAT" if (q.nhap_nhang and q.trang_thai_ap is None) else "HONG"))\n')
        _, ra_that = _chay_con(drv)
        self.assertIn("KETQUA=DAT", ra_that, f"cây THẬT không đạt cổng 110: {ra_that[-200:]}")
        _dc_duong("dot-bien-M2")
        cay = _cay_dot_bien([("trang_thai_hang.py", '("jt", 110): {', '("jt", 99110): {')])
        _, ra_bien = _chay_con(drv, cay_app=cay)
        self.assertIn("KETQUA=HONG", ra_bien,
                      f"xóa 110 khỏi sổ nhập nhằng mà cổng VẪN xanh ⇒ cổng D-4 KHÔNG có răng: {ra_bien[-200:]}")
        _dc_duong("dot-bien-M2")

    def test_f6_dot_bien_M3_mo_chot_area_thi_cong_phai_do(self):
        drv = ('import adapter_jt as a\n'
               'try:\n'
               '    a.chot_chan_anh_xa_area("sandbox", da_xac_nhan=False, nguon="", cap="quan-huyen")\n'
               '    print("KETQUA=RO")\n'
               'except Exception:\n'
               '    print("KETQUA=CHAN")\n')
        _, ra_that = _chay_con(drv)
        self.assertIn("KETQUA=CHAN", ra_that, f"cây THẬT đã mở chốt D-9: {ra_that[-200:]}")
        _dc_duong("dot-bien-M3")
        cay = _cay_dot_bien([("adapter_jt.py",
                              '    if moi_truong == "mock":\n        return\n\n    da = ANH_XA_AREA_DA_XAC_NHAN',
                              '    if True:\n        return\n\n    da = ANH_XA_AREA_DA_XAC_NHAN')])
        _, ra_bien = _chay_con(drv, cay_app=cay)
        self.assertIn("KETQUA=RO", ra_bien,
                      f"mở chốt D-9 mà cổng VẪN xanh ⇒ cổng D-9 KHÔNG có răng: {ra_bien[-200:]}")
        _dc_duong("dot-bien-M3")

    def test_f7_dot_bien_M4_lay_tenant_tu_query_thi_cong_phai_do(self):
        """M4: `tenant_id` lấy từ QUERY ⇒ tenant B phải THẤY canary của A (cổng V5 đỏ)."""
        _, ra_that = _chay_con(DRIVER_DOT_BIEN, giay=180)
        self.assertIn('"ro": false', ra_that.replace("False", "false"),
                      f"cây THẬT đã rò canary sang B: {ra_that[-300:]}")
        _dc_duong("dot-bien-M4")
        cay = _cay_dot_bien([("server.py", "        tenant_id = nc.tenant_id",
                              '        tenant_id = int(ts.get("tenant_id") or nc.tenant_id)')])
        _, ra_bien = _chay_con(DRIVER_DOT_BIEN, cay_app=cay, giay=180)
        self.assertIn('"ro": true', ra_bien.replace("True", "true"),
                      f"lấy tenant từ query mà cổng V5 VẪN xanh ⇒ cổng cách ly KHÔNG có răng: {ra_bien[-300:]}")
        _dc_duong("dot-bien-M4")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# H. CHỐT AN TOÀN — bộ thử TỰ CHỐI CHẠY, và chứng minh nó THẬT SỰ chối
# ══════════════════════════════════════════════════════════════════════════════════════════════
class H_ChotAnToan(unittest.TestCase):

    def test_h1_nen_khong_phai_thu_muc_tam_thi_TU_CHOI_CHAY(self):
        khong_tam = os.path.join(os.path.expanduser("~"), ".veh-g17-phai-tu-choi")
        self.assertFalse(os.path.exists(khong_tam), f"đường thử đã tồn tại sẵn: {khong_tam}")
        ma, ra = _chay_con("import thu_qa_g17\nprint('LOT-QUA-DUOC')\n",
                           bien_them={"VIP_G17_DATA": khong_tam})
        self.assertNotEqual(ma, 0, "bộ thử CHẠY được trên nền KHÔNG phải thư mục tạm")
        self.assertIn("TỪ CHỐI CHẠY", ra, f"không thấy lời từ chối: {ra[-300:]}")
        self.assertNotIn("LOT-QUA-DUOC", ra, "bộ thử đã chạy tiếp sau khi phải từ chối")
        self.assertFalse(os.path.exists(khong_tam),
                         "bộ thử đã GHI ra ngoài thư mục tạm dù đáng lẽ phải từ chối")
        _dc_am("tu-choi-khi-thieu-chot")
        print(f"  [chốt an toàn] nền không phải thư mục tạm ⇒ thoát {ma}, KHÔNG tạo gì ở {khong_tam}")

    def test_h2_bo_do_chot_an_toan_co_rang(self):
        self.assertIsNone(kiem_chot_an_toan(), f"chốt an toàn báo sai ở môi trường thật: {_LY_DO_TU_CHOI}")
        _dc_duong("tu-choi-khi-thieu-chot")
        self.assertIsNotNone(kiem_chot_an_toan({"dia_chi": "0.0.0.0"}), "bộ kiểm MÙ với bind 0.0.0.0")
        self.assertIsNotNone(kiem_chot_an_toan({"dia_chi": "192.168.1.9"}), "bộ kiểm MÙ với bind LAN")
        gia = type("AdapterGiaLive", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live"] = gia
        try:
            ly = kiem_chot_an_toan()
        finally:
            adapter._DANG_KY.pop("gia-live", None)
        self.assertIsNotNone(ly, "bộ kiểm MÙ với adapter MỞ LIVE")
        self.assertIn("gia-live", ly or "")
        self.assertIsNone(kiem_chot_an_toan(), "sổ đăng ký adapter chưa được trả nguyên trạng")
        _dc_duong("bo-do-chot-an-toan-co-rang")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# G. V13 — BỘ CHẠY HỒI QUY: soát LUẬT PHÁN, không soát cảm giác
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _soat_bo_chay(nguon):
    """Trả danh sách vi phạm luật của `chay_tat_ca.sh` (N-01 / N-02)."""
    loi = []
    dong = nguon.splitlines()
    for i, d in enumerate(dong, 1):
        if d.lstrip().startswith("#"):
            continue
        if re.match(r"\s*OUT=\$\(", d) and "||" not in d:
            loi.append(f"dòng {i}: gán TRẦN không có `|| MA=$?` ⇒ mã thoát bị vứt (N-01 quay lại)")
        if re.search(r"if\s+!\s*OUT=", d):
            loi.append(f"dòng {i}: khuôn `if ! OUT=` XOÁ mã thoát (N-01 bản vá đầu)")
        if "5 hãng" in d or "cả 5" in d:
            loi.append(f"dòng {i}: hằng viết cứng về số hãng (N-02 quay lại)")
    if "TOI_THIEU=" not in nguon:
        loi.append("thiếu ngưỡng tối thiểu số bộ thử")
    if "OUT=$(python3 \"$t\" 2>&1) || MA=$?" not in nguon:
        loi.append("thiếu ĐÚNG khuôn `OUT=$(python3 \"$t\" 2>&1) || MA=$?`")
    if "PHAM_VI_HANG=$(python3" not in nguon:
        loi.append("khối phạm vi không lấy số hãng từ SỔ ĐĂNG KÝ (N-02)")
    return loi


class G_BoChay(unittest.TestCase):

    def test_g1_bo_chay_khong_con_lo_hong_N01_N02(self):
        with open(os.path.join(THU_MUC_THU, "chay_tat_ca.sh"), encoding="utf-8") as f:
            nguon = f.read()
        self.assertLessEqual(_soat_bo_chay(nguon), [], "bộ chạy vi phạm luật phán")
        _dc_duong("bo-chay-sach")
        # ĐỐI CHỨNG DƯƠNG: chính bộ soát phải BẮT được bản vá sai (N-01) khi tiêm lại.
        gia = nguon.replace('OUT=$(python3 "$t" 2>&1) || MA=$?', 'OUT=$(python3 "$t" 2>&1); MA=$?')
        self.assertNotEqual(gia, nguon, "không tiêm được bản vá sai ⇒ phép soát không đo gì")
        self.assertNotEqual(_soat_bo_chay(gia), [], "bộ soát MÙ với bản vá N-01 tiêm vào")
        _dc_duong("bo-soat-bo-chay-co-rang")

    def test_g2_bo_chay_la_script_sh_khong_phai_python(self):
        """Đo thẳng: `python3 app/thu/chay_tat_ca.sh` KHÔNG chạy được — nó là script POSIX sh."""
        duong = os.path.join(THU_MUC_THU, "chay_tat_ca.sh")
        with open(duong, encoding="utf-8") as f:
            dau = f.readline().strip()
        self.assertEqual(dau, "#!/bin/sh", f"shebang lạ: {dau!r}")
        # ĐỐI CHỨNG DƯƠNG cho ca âm dưới: tệp này PHẢI là script `sh` HỢP LỆ với `sh`.
        kiem = subprocess.run(["sh", "-n", duong], capture_output=True, text=True, timeout=30)
        self.assertEqual(kiem.returncode, 0, f"`sh -n` báo tệp sh KHÔNG hợp lệ: {kiem.stderr.strip()}")
        _dc_duong("python3-tren-script-sh")
        r = subprocess.run([sys.executable, duong], capture_output=True, text=True, timeout=60)
        self.assertNotEqual(r.returncode, 0, "`python3 <script sh>` lại chạy được?!")
        print(f"\n  [V13] `python3 app/thu/chay_tat_ca.sh` → mã thoát {r.returncode}: "
              f"{(r.stdout + r.stderr).strip().splitlines()[-1][:90]}")
        print("  [V13] cách chạy ĐÚNG (đã dùng cho baseline): `sh app/thu/chay_tat_ca.sh`")
        _dc_am("python3-tren-script-sh")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Z. TỔNG KẾT — sổ đối chứng + vân tay cây trước/sau + phạm vi
# ══════════════════════════════════════════════════════════════════════════════════════════════
class Z_TongKet(unittest.TestCase):

    def test_z1_moi_nhom_phu_dinh_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertEqual(thieu, [], f"nhóm có ca ÂM mà KHÔNG có đối chứng DƯƠNG: {thieu}")
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")
        _dc_duong("so-doi-chung-co-du-lieu")
        print("\nSỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))

    def test_z2_cay_khong_doi_trong_luot_do(self):
        """Cây KHÔNG đổi giữa lượt đo — đo bằng CẢ HAI vân tay, không chỉ bản dự phòng.

        Bản dự phòng (bỏ qua vùng thử) bắt được thay đổi MÃ SẢN PHẨM. Vân tay GIT (CHÍNH) bắt
        thêm `git diff HEAD` — tức mọi thay đổi trên tệp ĐÃ THEO DÕI, kể cả `docs/*.md` (`G16-09`).
        """
        sau = van_tay_cay(bo_qua=PHAM_VI_WAVE)
        self.assertEqual(sau, VAN_TAY_LUC_NAN,
                         "CÂY ĐỔI giữa lượt đo ⇒ mọi số đo phải coi là vô hiệu (§41)")
        vt = chotcay.van_tay()
        self.assertEqual(vt["head"], HEAD_LUC_NAN,
                         "HEAD ĐỔI giữa lượt đo ⇒ số đo thuộc HAI mốc mã khác nhau")
        self.assertEqual(vt["thu_muc"]["theo_doi"], VAN_TAY_THU_MUC_LUC_NAN,
                         "NỘI DUNG một tệp ĐÃ THEO DÕI đổi giữa lượt đo (kể cả `docs/*.md` — "
                         "`G16-09`) ⇒ số đo vô hiệu")
        _dc_duong("cay-khong-doi")
        head = _git("rev-parse", "HEAD").stdout.strip()
        print(f"\n  [kết] HEAD={head} · vân tay={sau} · CSDL tạm={_TAM}")
        print("  [kết] CHƯA ĐO (lỗ hổng phạm vi, KHÔNG phải ĐẠT): gọi hãng thật/TLS thật · "
              "bốn thao tác cancelOrder/getShippingFee/getShippingLabel/getOrder đầu-cuối · "
              "harness SANDBOX của AG-04 (trien_khai/g16) · tầng 3 Chromium · đa tiến trình · "
              "gộp `main` · deploy/push")


if __name__ == "__main__":
    print(f"NGƯỠNG CHE BÍ MẬT (http_jt): {getattr(__import__('http_jt'), 'DAI_TOI_THIEU_DE_CHE', 'n/a')}")
    print(f"NỀN ĐO: HEAD={_git('rev-parse', 'HEAD').stdout.strip()} · ghim={HEAD_GHIM or 'KHÔNG'} · CSDL={_TAM}")
    unittest.main(verbosity=2)


