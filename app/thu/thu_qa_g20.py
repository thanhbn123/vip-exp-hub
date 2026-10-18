#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-01 (G20) — BỘ KIỂM ĐỘC LẬP cho wave G20 "ĐON KHOẢNG TRỐNG CÒN LẠI".

VAI: tôi là NGƯỜI KIỂM, không phải người viết. Bộ này KHÔNG sửa một dòng mã sản phẩm nào.
Tìm thấy lỗi thì GHI LẠI và BÁO CÁO. Hai tệp được phép ghi trong lượt U2:
    app/thu/thu_qa_g20.py     (tệp này)
    docs/G20_MEASURE_FIX.md   (báo cáo phân loại STALE / LỖI THẬT + bằng chứng trước/sau)

NỀN LỊCH SỬ: integration/g19 @ 148ecd380a9009c7b01dc0c268a3f1a97327a164.
`HEAD_NEN` dưới đây chỉ còn là TỔ TIÊN (`merge-base --is-ancestor`) — KHÔNG BAO GIỜ so bằng
`HEAD == HEAD_NEN`: HEAD nhích ở mọi commit và phép so đó là GHIM STALE (`L-G20-A` / họ H5).
KHÔNG dùng `main` (de740dc) — `main` KHÔNG chứa G13–G20.

LỆNH CHẠY
    python3 app/thu/thu_qa_g20.py                    # làn MẶC ĐỊNH: 4 cổng G20 + hai chốt chặn
    VIP_G20_DAY_DU=1 python3 app/thu/thu_qa_g20.py   # + hồi quy toàn phần (chay_tat_ca.sh)
    VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py # NGHIỆM THU BẢN ĐÃ GỘP: nợ còn ⇒ ĐỎ

------------------------------------------------------------------------------------------------
VÌ SAO CỔNG Ở ĐÂY LÀ HAI CHIỀU — và vì sao "nửa vời" LUÔN là ĐỎ
------------------------------------------------------------------------------------------------
Mỗi cổng có một SỔ GIÁ TRỊ (`SO_DO`) ghi HAI trạng thái ĐÃ ĐO ĐƯỢC:

    "nen"  = giá trị đo trên nền đóng băng 148ecd3   (nợ CÒN NGUYÊN)
    "dong" = giá trị phải có khi khoản nợ đã đóng    (điều kiện nghiệm thu)

Phán quyết (`phan_quyet`):

    giá trị == "nen"   -> NEN
    giá trị == "dong"  -> DONG
    giá trị KHÁC CẢ HAI -> NUA_VOI  ==> LUÔN ĐỎ, ở mọi chế độ

Chốt thứ ba đó là điều làm cổng CÓ RĂNG theo cả hai mặt: một bản vá **nửa vời** (ví dụ 3/5
module có đường vào, hay tầng 3 còn 1 ca "did not run") KHÔNG rơi vào ô nào ⇒ ĐỎ. Đây là chỗ
tôi cố ý làm CHẶT HƠN khuôn G19 (chỉ có hai ô MỞ/ĐÓNG): ở G19 một giá trị lửng lơ vẫn có thể
được đọc là "chưa gộp"; ở đây nó là một phán quyết riêng và là ĐỎ.

Với `VIP_G20_CHE_DO=gop` (lượt nghiệm thu bản ĐÃ GỘP) thì ô "nen" cũng thành ĐỎ ⇒ nợ chưa đóng
KHÔNG THỂ lọt qua bằng cách viện cớ "nền còn đóng băng".

------------------------------------------------------------------------------------------------
HAI CHỐT CHẶN BẮT BUỘC
------------------------------------------------------------------------------------------------
(a) TỰ KIỂM BỘ ĐO chạy trong TIẾN TRÌNH CON — lớp `T_TuKiem`. Không có nó thì mọi dòng
    "✓ N ca" của tệp này không chứng minh gì. Cụ thể: một ca CỐ Ý HỎNG chạy bằng subprocess
    phải cho phán quyết HỎNG; và luật phán phải TỪ CHỐI bốn kiểu "xanh giả".
(b) ĐỐI CHỨNG DƯƠNG cho MỌI ca phủ định — sổ `DOI_CHUNG`, in ra ở `Z1`, và `Z1` TỰ PHÁN HỎNG
    nếu một nhóm phủ định không có ca dương. `Z1` cũng có ca tự kiểm: một nhóm âm cố ý KHÔNG
    có dương phải bị nó bắt được.

------------------------------------------------------------------------------------------------
PHẠM VI HTTP — TUYỆT ĐỐI
------------------------------------------------------------------------------------------------
Không một lời gọi nào ra hãng, kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Mọi phép đo
lớp HTTP ở đây chỉ chạm `127.0.0.1`. Máy chủ của tầng 3 do chính bộ này dựng trên nền CÔ LẬP,
cổng do hệ điều hành cấp (`bind 127.0.0.1:0`) rồi giữ đúng PID để tắt. Adapter hãng ở chế độ
MOCK (`CHO_PHEP_LIVE=False`) nên máy chủ cũng không gọi ra ngoài. Cụm PostgreSQL `:5432`
KHÔNG bị đụng tới (D-8: CSDL nghiệp vụ vẫn SQLite).
"""

import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ — mọi thứ ĐO ĐƯỢC thì lấy từ LỆNH, không điền tay vào tệp
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC_CAY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GOC_APP = os.path.join(GOC_CAY, "app")
GOC_THU = os.path.join(GOC_CAY, "app", "thu")
GOC_TGD = os.path.join(GOC_CAY, "thu_giao_dien")

HEAD_NEN = "148ecd380a9009c7b01dc0c268a3f1a97327a164"

sys.path.insert(0, GOC_THU)
import thu_g21_chotcay as chotcay  # noqa: E402

# Làn đầy đủ: thêm hồi quy toàn phần. Mặc định TẮT để bộ chạy chung không phình thời gian.
DAY_DU = os.environ.get("VIP_G20_DAY_DU") == "1"
# Chế độ nghiệm thu bản ĐÃ GỘP. "gop" ⇒ ô "nen" cũng ĐỎ.
CHE_DO = os.environ.get("VIP_G20_CHE_DO", "nen")
if CHE_DO not in ("nen", "gop"):
    CHE_DO = "nen"

LOG_DIR = os.environ.get("VIP_G20_LOG") or os.path.join(tempfile.gettempdir(), "veh_g20_ag01_qa_log")

# Nhị phân Chromium: KHÔNG dùng cache hệ thống của dự án khác. `chay.sh` ghim
# `PLAYWRIGHT_BROWSERS_PATH=0` (tức `node_modules/playwright-core/.local-browsers`) và worktree
# này THIẾU thư mục đó — nên tầng 3 chạy bằng chính bộ chạy của dự án sẽ HỎNG VÌ MÔI TRƯỜNG.
# Bản chỉ định dưới đây là bản `BAN_GIAO.md` §1 đã ghim, cùng khuôn `thu_qa_g18.py`.
PW_BROWSERS_CHI_DINH = os.path.expanduser(
    "~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers")
PW_BROWSERS_REPO = os.path.join(GOC_CAY, "node_modules", "playwright-core", ".local-browsers")

# Đặc tả tầng 3 canh BÀN PHÍM. Số hiệu ca 04 được B2 đọc từ LOG (không ghim nguyên văn tiêu đề).
SPEC_BAN_PHIM = "06_ban_phim.spec.js"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. SỔ GIÁ TRỊ — HAI CHIỀU, VÀ "NỬA VỜI" LÀ ĐỎ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Mỗi giá trị dưới đây là một con số TÔI ĐO ĐƯỢC, không phải một kỳ vọng đặt ra.
#
# HAI CỔNG ĐÃ BỎ KHỎI SỔ VÌ SỔ ĐÓ GHIM SỰ THẬT CŨ (lượt U2, docs/G20_MEASURE_FIX.md):
#   · `tang3-ban-phim` — bản cũ ghim `(3,1,3)` → `(7,0,0)`. Đặc tả đã thêm ca TỰ KIỂM `04b`
#     (8 ca) nên `(7,0,0)` thành GHIM STALE. Nay B1 canh BẤT BIẾN `phan_quyet_tang_3`: chạy
#     trọn vẹn + xanh (thoát 0, 0 hỏng, 0 bỏ qua, 0 "did not run"), KHÔNG ghim số ca.
#   · `git-tho` — bản cũ ghim `128 → 0`. `128` là dị dạng `GIT_CONFIG_*` của PHIÊN (N-G18-00),
#     không phải nợ sản phẩm; ghim nó làm chế độ `gop` ĐỎ vĩnh viễn. Nay C1 PHÂN LOẠI git thô
#     theo chữ ký và in cảnh báo; chỉ hỏng vì lý do KHÁC mới ĐỎ.

SO_DO = {
    # C1 (N-G19-03) — số cổng "cây sạch" của wave TRƯỚC chạy XANH khi cây chỉ bẩn trong VÙNG
    # thử/tài liệu (luật `thu_g21_chotcay`). Nền lịch sử: 0/2 (miễn trừ theo tên cứng làm cả
    # hai ĐỎ vì tệp hợp lệ). Đóng: 2/2 (miễn trừ theo quy tắc vùng). Cây có mã SẢN PHẨM bẩn thì
    # vẫn ĐỎ — đối chứng âm nằm ngay trong A5.
    "cong-cay-sach": {"nen": 0, "dong": 2},

    # C4 (C6 của G19 — "route `truy_van.py` + `DDL_G12Q` vào migration v9").
    # Giá trị là CẶP (schema_ok, route_ok):
    #   Nền ĐO ĐƯỢC: (True, False) — migration v9 ĐÃ gộp (`PHIEN_BAN_SCHEMA=9`, có `nang_len_v9`)
    #                nhưng `app/truy_van.py` KHÔNG được một tệp SẢN XUẤT nào import.
    #   Đóng:        (True, True) — `app/server.py` import + DÙNG `truy_van` (route thật).
    # Bản cũ (STALE) khẳng định thêm `nhap == []` — tức GHIM đúng trạng thái nền. Nay chỉ dùng
    # cặp (schema_ok, route_ok): `(False, True)` = NỬA VỜI ⇒ ĐỎ; `(True, False)` = NỀN ⇒ ĐỎ ở
    # chế độ gộp. Xem `docs/G22_CONTRACT.md` §0ter.
    "truy-van-C6": {"nen": (True, False), "dong": (True, True)},

    # C5 (N-G20-01, tôi phát hiện) — KHÔNG bộ thử G19-tổng-hợp nào chạy trên cây đã gộp.
    # Giá trị = min(số bộ khớp `thu_qa_g19*.py` chạy được ≥1 ca và thoát 0, 1).
    #   Nền: 0 — `thu_qa_g19.py` tự BỎ QUA (nó ghim nền cũ 6e61fc1), và tệp mà chính nó chỉ
    #        sang (`thu_qa_g19_tich_hop.py`) KHÔNG TỒN TẠI.
    #   Đóng: 1.
    "bo-g19-tong-hop": {"nen": 0, "dong": 1},
}


def phan_quyet(ten_cong, do_duoc):
    """'NEN' | 'DONG' | 'NUA_VOI'. Giá trị lửng lơ KHÔNG rơi vào ô nào ⇒ NUA_VOI."""
    ky = SO_DO[ten_cong]
    if do_duoc == ky["dong"]:
        return "DONG"
    if do_duoc == ky["nen"]:
        return "NEN"
    return "NUA_VOI"


def dat_cong(ten_cong, do_duoc, che_do=None):
    """(đạt?, câu giải thích). 'NỬA VỜI' luôn ĐỎ; ở chế độ `gop` thì 'NỀN' cũng ĐỎ."""
    che = CHE_DO if che_do is None else che_do
    pq = phan_quyet(ten_cong, do_duoc)
    if pq == "NUA_VOI":
        return False, ("NỬA VỜI — giá trị %r không phải nền %r cũng không phải đóng %r"
                       % (do_duoc, SO_DO[ten_cong]["nen"], SO_DO[ten_cong]["dong"]))
    if pq == "NEN" and che == "gop":
        return False, "chế độ GỘP: khoản nợ %r VẪN CÒN NGUYÊN" % (do_duoc,)
    return True, pq


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. SỔ ĐỐI CHỨNG DƯƠNG — chốt (b)
# ══════════════════════════════════════════════════════════════════════════════════════════════

DOI_CHUNG = {}


def _dc_am(nhom):
    o = DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})
    o["am"] += 1


def _dc_duong(nhom):
    o = DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})
    o["duong"] += 1


def nhom_thieu_duong(so=DOI_CHUNG):
    """Nhóm có ca ÂM nhưng THIẾU ca DƯƠNG. `Z1` tự phán HỎNG nếu danh sách này khác rỗng."""
    return sorted(k for k, v in so.items() if v["am"] > 0 and v["duong"] == 0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. TIỆN ÍCH: git, tiến trình con, vân tay cây
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _git(*tham_so, env=None, tho=False):
    """Chạy `git`.

    `tho=True` giữ NGUYÊN môi trường thừa hưởng — dùng để ĐO chính cái lỗi `GIT_CONFIG_*`
    (`C1`). Mặc định thì gỡ gia đình biến dị dạng, vì nếu không MỌI lệnh git thoát 128.
    """
    if tho:
        e = dict(os.environ)
    else:
        e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
        e["GIT_CONFIG_COUNT"] = "0"
    e.update(env or {})
    return subprocess.run(["git"] + list(tham_so), capture_output=True, text=True,
                          cwd=GOC_CAY, env=e, timeout=120)


def _chay(lenh, env=None, giay=900, cwd=None, bo_bien=()):
    """Chạy một lệnh THẬT trong tiến trình con. Trả (mã thoát, output, số giây).

    `bo_bien` GỠ HẲN các biến đó khỏi môi trường con. Cần tham số riêng chứ không thể chỉ
    truyền `env` thiếu khoá: `env` được `update()` ĐÈ LÊN `os.environ`, nên một biến có ở cha
    mà không có ở `env` vẫn SỐNG SÓT sang con. Lượt đo đầu của tôi vấp đúng chỗ này: `H1` gọi
    `chay_tat_ca.sh`, bộ chạy chung lại chạy chính tệp này ở làn đầy đủ (vì `VIP_G20_DAY_DU=1`
    vẫn còn), và nó ĐỆ QUY VÔ HẠN. Xem docs §4.3 — `T5` nay canh đúng chỗ đó.
    """
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e.update(env or {})
    for k in bo_bien:
        e.pop(k, None)
    t0 = time.time()
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, env=e, timeout=giay,
                           cwd=cwd or GOC_CAY)
        return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired as ex:
        ra = (ex.stdout or b"")
        if isinstance(ra, bytes):
            ra = ra.decode("utf-8", "replace")
        return 124, "[QUÁ HẠN %ss] %s" % (giay, ra), time.time() - t0


def _doc(duong):
    """Đọc một tệp văn bản — dùng `with` để không rò tệp (ResourceWarning làm nhiễu log)."""
    with open(duong, encoding="utf-8") as f:
        return f.read()


def _ghi_log(ten, ma, ra):
    os.makedirs(LOG_DIR, exist_ok=True)
    duong = os.path.join(LOG_DIR, ten)
    with open(duong, "w", encoding="utf-8") as f:
        f.write("MA_THOAT=%s\n" % ma)
        f.write(ra)
    return duong


def _vung_wave():
    """VÙNG thử/tài liệu = "các tệp mà wave đang làm" — TỰ DÒ, không danh sách tên cứng.

    Luật dùng chung với `thu_qa_g17.py`/`thu_qa_g18.py` nằm ở `thu_g21_chotcay.vung_thu_tai_lieu`:
    `docs/` + mọi thư mục có tên bắt đầu bằng `thu`. Nhờ vậy một tệp MỚI của làn khác tự khớp,
    không ai phải thêm một dòng vào danh sách miễn trừ (`N-G19-03`, tái diễn ba wave).
    """
    return chotcay.vung_thu_tai_lieu(goc=GOC_CAY)


def _la_dong_cua_wave(dong_porcelain, vung=None):
    """Dòng `git status --porcelain` có nằm TRONG vùng thử/tài liệu không.

    Dòng đổi tên phải có CẢ HAI đường trong vùng — kéo một tệp sản phẩm vào thư mục thử vẫn là
    thay đổi sản phẩm (`thu_g21_chotcay.phan_loai`).
    """
    if vung is None:
        vung = _vung_wave()
    return all(chotcay.la_trong_vung(d, vung)
               for d in chotcay.duong_tu_dong_porcelain(dong_porcelain))


def van_tay_cay(bo_qua_vung=True):
    """Vân tay CÂY ĐƯỢC THEO DÕI: `git ls-files -s` + `git status --porcelain` (đã lọc).

    VÌ SAO chỉ cây ĐƯỢC THEO DÕI, không băm cả cây làm việc: một lượt `chay_tat_ca.sh` GHI RA
    ĐĨA những tệp ĐƯỢC BỎ QUA (`app/du-lieu/khoa-noi-bo.key`, `thu_giao_dien/_bao-cao/**`,
    `thu_giao_dien/_ket-qua/**`). Băm cả cây làm việc thì vân tay ĐỔI dù không một tệp nào
    của sản phẩm bị sửa — một nhiệt kế đo nhầm thứ. Đo được: trước `032f4114…`, sau `90e6f226…`
    trong khi `git status --porcelain` RỖNG cả hai lượt.

    Bộ lọc dùng QUY TẮC VÙNG (`_la_dong_cua_wave`), KHÔNG dùng danh sách tên: một tệp mới của
    wave trong `docs/`/`thu*` không làm vân tay "bẩn", nhưng một tệp SẢN PHẨM bẩn thì vẫn lộ.
    """
    ls = _git("ls-files", "-s").stdout
    st = _git("status", "--porcelain=v1", "-uall").stdout
    dong = [d for d in st.splitlines() if d.strip()]
    if bo_qua_vung:
        vung = _vung_wave()
        dong = [d for d in dong if not _la_dong_cua_wave(d, vung)]
    return hashlib.sha256((ls + "\n" + "\n".join(sorted(dong))).encode()).hexdigest()


def _cong_ranh():
    """Cổng do hệ điều hành cấp (bind `127.0.0.1:0`) — không tranh cổng với làn khác."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = s.getsockname()[1]
    s.close()
    return cong


def _pw_browsers():
    rieng = os.environ.get("VIP_G20_PW_BROWSERS", "")
    ung_vien = ([("VIP_G20_PW_BROWSERS", rieng)] if rieng else
                [("chỉ định BAN_GIAO §1", PW_BROWSERS_CHI_DINH), ("trong repo", PW_BROWSERS_REPO)])
    for ten, duong in ung_vien:
        if duong and os.path.isdir(duong):
            for con in sorted(os.listdir(duong)):
                if con.startswith("chromium_headless_shell-") or con.startswith("chromium-"):
                    return duong, ten, con
    return None, None, None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. BỘ CHẠY TẦNG 3 — khuôn `thu_giao_dien/chay.sh`, chỉ khác ĐƯỜNG nhị phân Chromium
# ══════════════════════════════════════════════════════════════════════════════════════════════

def do_tang_3(spec=None, giay=600):
    """Dựng máy chủ trên nền CÔ LẬP (bind 127.0.0.1, cổng OS cấp) rồi chạy Playwright.

    Trả `(mã_thoát, output, ghi_chú)`. `mã_thoát = None` nghĩa là CHƯA ĐO ĐƯỢC (thiếu nhị
    phân Chromium) — phán quyết khi đó là BỎ QUA / lỗ hổng phạm vi, KHÔNG BAO GIỜ là ĐẠT.
    """
    pw, nguon, ban = _pw_browsers()
    if pw is None:
        return None, "", "không có thư mục nhị phân Chromium"
    if not os.path.isdir(os.path.join(GOC_CAY, "node_modules", "@playwright", "test")):
        return None, "", "thiếu node_modules/@playwright/test"

    nen = tempfile.mkdtemp(prefix="veh-g20-gd-")
    cong = _cong_ranh()
    env = dict(os.environ, VIP_HUB_DATA=nen, PLAYWRIGHT_BROWSERS_PATH=pw)
    # KHAI KHO cho MÔI TRƯỜNG KIỂM THỬ CÔ LẬP (G22 `cau_hinh.KHAI_KHO`): `app/migrate.py` nay
    # TỪ CHỐI khi chưa ai khai kho đang chạy, vì một `hub.db` cũ trông y hệt một `hub.db` đang
    # phục vụ và bản sao lưu rỗng là ĐƯỜNG LÙI GIẢ. Đây là khai báo của BỘ THỬ cho thư mục TẠM
    # (`VIP_HUB_DATA=nen`, ngoài cây repo) — KHÔNG phải chuyển production sang SQLite (D-8).
    # Thiếu dòng này thì nền tầng 3 không dựng được và B1/B2 đo 0 ca (STALE, không phải lỗi sản phẩm).
    env["VIP_KHO_DANG_CHAY"] = "sqlite"
    # CHỐT CỨNG: ÉP bind `127.0.0.1`, không chỉ "không đặt gì". `server.py` đọc `VIP_HUB_BIND`
    # và mặc định là `127.0.0.1`, nhưng một biến thừa hưởng từ phiên ngoài có thể mở cổng ra
    # ngoài — điều bị CẤM TUYỆT ĐỐI. Ép tại đây thì không phụ thuộc vào việc phiên ngoài đặt gì.
    env["VIP_HUB_BIND"] = "127.0.0.1"
    pid = None
    try:
        for lenh, nhan in ((["python3", "app/migrate.py"], "migrate"),
                           (["python3", "app/khoi_tao.py"], "khoi_tao"),
                           (["python3", "thu_giao_dien/chuan_bi.py", "mk"], "chuan_bi-mk")):
            ma, ra, _ = _chay(lenh, env=env, giay=180)
            if ma != 0:
                return ma, "[%s hỏng] %s" % (nhan, ra[-1500:]), "nền không dựng được"

        # Log máy chủ ra TỆP, KHÔNG qua ống: mỗi lượt HTTP một dòng JSON, ống đầy (64KB) thì
        # máy chủ CHẶN ở lệnh ghi và mọi lượt sau treo tới hết thời hạn. Lượt đo đầu của G18
        # vấp đúng cái này và nó suýt thành "5 ca hỏng của sản phẩm".
        log_sv = open(os.path.join(nen, "server.log"), "w")
        try:
            tien_trinh = subprocess.Popen(["python3", "app/server.py", str(cong)],
                                          cwd=GOC_CAY, env=env, stdout=log_sv,
                                          stderr=subprocess.STDOUT)
            pid = tien_trinh.pid
        finally:
            log_sv.close()

        # Chờ máy chủ MỞ THẬT — không `sleep` một con số rồi tin là đã mở.
        mo = False
        for _ in range(80):
            s = socket.socket()
            s.settimeout(0.3)
            try:
                s.connect(("127.0.0.1", cong))
                mo = True
                break
            except OSError:
                time.sleep(0.25)
            finally:
                s.close()
        if not mo:
            return 2, "[máy chủ không mở cổng %s sau 20 giây]" % cong, "máy chủ không mở"

        goc_url = "http://127.0.0.1:%s" % cong
        ma, ra, _ = _chay(["python3", "thu_giao_dien/chuan_bi.py", "don", goc_url],
                          env=env, giay=180)
        if ma != 0:
            return ma, "[chuan_bi-don hỏng] %s" % ra[-1500:], "nền không dựng được"

        lenh = ["npx", "playwright", "test"] + ([spec] if spec else [])
        e2 = dict(env, VIP_GD_GOC=goc_url, VIP_GD_NEN=nen)
        ma, ra, _ = _chay(lenh, env=e2, giay=giay)
        return ma, ra, "nhị phân: %s (%s)" % (nguon, ban)
    finally:
        if pid:
            # Tắt theo ĐÚNG PID đã giữ lúc khởi động. KHÔNG BAO GIỜ theo mẫu tên (§16.7).
            try:
                tien_trinh.terminate()
                tien_trinh.wait(timeout=10)
            except Exception:
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
        shutil.rmtree(nen, ignore_errors=True)


def dem_playwright(ra):
    """Đếm kết quả Playwright. Trả `(đạt, hỏng, bỏ_qua, khong_chay)`.

    `khong_chay` ("did not run") là phán quyết RIÊNG, không gộp vào bỏ qua và KHÔNG BAO GIỜ
    gộp vào đạt: khi một ca của Playwright QUÁ HẠN, Playwright đóng tiến trình con và **các ca
    còn lại trong cùng tệp KHÔNG HỀ CHẠY**. Đo được trên nền G20: `1 failed · 3 did not run ·
    47 passed` — tức MỘT ca hỏng đã che MẤT BA phép đo bàn phím khác.
    """
    def _so(mau):
        m = re.findall(mau, ra)
        return int(m[-1]) if m else 0
    return (_so(r"(\d+) passed"), _so(r"(\d+) failed"),
            _so(r"(\d+) skipped"), _so(r"(\d+) did not run"))


def dem_diem_dung_trong_man(ra):
    """Đọc dòng `[đo] 30 lượt Tab: N điểm dừng là điều khiển trong màn` (ca 04)."""
    m = re.findall(r"lượt Tab:\s*(\d+)\s*điểm dừng là điều khiển trong màn", ra)
    return int(m[-1]) if m else None


def phan_quyet_tang_3(ma, dat, hong, bo, khong_chay):
    """BẤT BIẾN của cổng C2 — KHÔNG ghim số ca (bản cũ ghim `(7,0,0)` đã STALE).

    `DONG`      = Playwright chạy TRỌN VẸN và XANH: thoát 0, 0 hỏng, 0 bỏ qua, 0 "did not run",
                  và có ÍT NHẤT một ca đạt.
    `NEN`       = còn ca hỏng / bỏ qua / KHÔNG CHẠY (kể cả `did not run`) hoặc mã thoát ≠ 0.
    `KHONG_DO`  = 0 ca: phép đo CHẾT (nền không dựng được / bộ đếm mù) — ĐỎ, không phải BỎ QUA.

    Vì sao không đòi đúng một con số: đặc tả có thể được bổ sung ca TỰ KIỂM (ca 04b) mà không
    hề làm cổng yếu đi — điều cần canh là "không ca nào bị bỏ lại phía sau", không phải một
    con số của lượt đo cũ.
    """
    if dat + hong + bo + khong_chay == 0:
        return "KHONG_DO"
    if ma != 0 or hong > 0 or bo > 0 or khong_chay > 0:
        return "NEN"
    return "DONG" if dat > 0 else "KHONG_DO"


def dat_cong_tang_3(ma, dat, hong, bo, khong_chay):
    """(đạt?, câu giải thích) cho cổng C2 — chặt hơn bản cũ ở chỗ ĐÒI `bỏ qua == 0`."""
    pq = phan_quyet_tang_3(ma, dat, hong, bo, khong_chay)
    do_duoc = (dat, hong, bo, khong_chay)
    if pq == "DONG":
        return True, "ĐÓNG"
    if pq == "KHONG_DO":
        return False, ("PHÉP ĐO CHẾT — 0 ca chạy (mã thoát %s, đo được %r)" % (ma, do_duoc))
    return False, ("CÒN NỢ — (đạt, hỏng, bỏ qua, KHÔNG CHẠY)=%r, mã thoát %s" % (do_duoc, ma))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. A — NỀN VÀ AN TOÀN TUYỆT ĐỐI
# ══════════════════════════════════════════════════════════════════════════════════════════════

class A_Nen(unittest.TestCase):
    """Vi phạm bất kỳ mục nào ở đây ⇒ mọi số đo khác trở nên vô hiệu."""

    def test_a1_head_dung_goc_nen_dong_bang(self):
        """HEAD phải NẰM TRÊN nền đóng băng — không phải một nhánh khác.

        Cố ý KHÔNG đòi `HEAD == 148ecd3`: lượt nghiệm thu bản ĐÃ GỘP chạy trên commit đã gộp,
        nên đòi bằng nhau sẽ làm cả bộ kiểm ĐỎ vì lý do đúng-việc-đang-làm. Đòi ĐÚNG tính chất
        cần: nền là TỔ TIÊN của HEAD (mọi thứ wave này làm đều đắp lên nền).
        """
        head = _git("rev-parse", "HEAD").stdout.strip()
        r = _git("merge-base", "--is-ancestor", HEAD_NEN, head)
        self.assertEqual(r.returncode, 0,
                         "HEAD=%s KHÔNG nằm trên nền đóng băng %s — sai gốc đo" % (head, HEAD_NEN))
        main = _git("rev-parse", "main").stdout.strip()
        self.assertNotEqual(head, main, "đang đo trên `main` (de740dc) — KHÔNG chứa G13–G20")
        _dc_am("goc-do")
        _dc_duong("goc-do")  # dương: chính phép `merge-base` đã chạy và cho 0 ở trên
        print("\n  [A1] HEAD=%s · nền %s là TỔ TIÊN · main=%s (khác HEAD) · chế độ=%s · làn đầy đủ=%s"
              % (head[:12], HEAD_NEN[:7], main[:7], CHE_DO, DAY_DU))

    def test_a2_chay_tat_ca_khong_duoc_bat_ky_adapter_mo_LIVE(self):
        sys.path.insert(0, GOC_APP)
        import adapter  # noqa: E402
        import adapter_jt  # noqa: F401,E402
        import adapter_vtp  # noqa: F401,E402
        mo = sorted(m for m, lop in adapter._DANG_KY.items()
                    if getattr(lop, "CHO_PHEP_LIVE", False))
        self.assertGreaterEqual(len(adapter._DANG_KY), 2, "sổ đăng ký adapter RỖNG ⇒ ca vô nghĩa")
        self.assertEqual(mo, [], "có adapter MỞ LIVE: %s" % mo)
        _dc_am("live-khoa")
        # ĐỐI CHỨNG DƯƠNG: bộ dò PHẢI thấy được một lớp giả đã mở.
        gia = type("AdapterGiaLive", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live-g20"] = gia
        try:
            thay = [m for m, lop in adapter._DANG_KY.items()
                    if getattr(lop, "CHO_PHEP_LIVE", False)]
        finally:
            adapter._DANG_KY.pop("gia-live-g20", None)
        self.assertEqual(thay, ["gia-live-g20"], "bộ dò MÙ với adapter MỞ LIVE")
        _dc_duong("live-khoa")
        print("  [A2] %d lớp adapter · LIVE mở: 0 · bộ dò bắt được lớp giả"
              % len(adapter._DANG_KY))

    def test_a3_csdl_nghiep_vu_van_la_sqlite_D8(self):
        """D-8: KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL. PostgreSQL chỉ CỤM RIÊNG."""
        cam = ("psycopg", "psycopg2", "asyncpg", "pg8000", "postgresql")
        thay = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py"):
                continue
            with open(os.path.join(GOC_APP, ten), encoding="utf-8") as f:
                than = f.read()
            for c in cam:
                if re.search(r"^\s*(import|from)\s+%s\b" % re.escape(c), than, re.M):
                    thay.append("%s: %s" % (ten, c))
        self.assertEqual(thay, [], "app/*.py có driver PostgreSQL: %s" % thay)
        _dc_am("sqlite-D8")
        # ĐỐI CHỨNG DƯƠNG: chính bộ dò phải BẮT ĐƯỢC một import cấm trong tệp giả.
        gia = os.path.join(tempfile.mkdtemp(prefix="veh-g20-pg-"), "gia_pg.py")
        try:
            with open(gia, "w", encoding="utf-8") as f:
                f.write("import psycopg2\n")
            with open(gia, encoding="utf-8") as f:
                than = f.read()
            bat = [c for c in cam
                   if re.search(r"^\s*(import|from)\s+%s\b" % re.escape(c), than, re.M)]
            self.assertEqual(bat, ["psycopg2"], "bộ dò MÙ với import PostgreSQL")
        finally:
            shutil.rmtree(os.path.dirname(gia), ignore_errors=True)
        _dc_duong("sqlite-D8")
        print("  [A3] 0/%d tệp app/*.py import driver PostgreSQL · bộ dò bắt được tệp giả"
              % len([t for t in os.listdir(GOC_APP) if t.endswith(".py")]))

    def test_a4_cum_5432_khong_bi_dung_toi(self):
        """Cụm `:5432` đang giữ dữ liệu DỰ ÁN KHÁC (`vip_customs*`) — CẤM đụng."""
        if shutil.which("lsof") is None:
            self.skipTest("CHƯA ĐO: máy này không có `lsof`")
        ra = _chay(["sh", "-c", "lsof -nP -iTCP:5432 -sTCP:LISTEN 2>/dev/null | wc -l"], giay=60)[1]
        so = int(ra.strip() or 0)
        if so < 1:
            self.skipTest("CHƯA ĐO: cụm :5432 không nghe ⇒ không có gì để canh (đổi cách đo)")
        # Bộ thử PostgreSQL của dự án chỉ được dùng cụm RIÊNG 55432.
        than = _doc(os.path.join(GOC_THU, "thu_postgres.py"))
        self.assertIn("55432", than, "bộ thử PostgreSQL KHÔNG khai cụm riêng 55432")
        _dc_am("cum-5432")
        _dc_duong("cum-5432")  # dương: `lsof` PHẢI thấy tiến trình đang nghe (assert ở trên)
        print("  [A4] cụm :5432 đang nghe: %d dòng lsof · bộ thử PostgreSQL dùng cụm riêng 55432"
              % so)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. C — MÔI TRƯỜNG: `GIT_CONFIG_*` DỊ DẠNG (N-G18-00)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def phan_loai_git_tho(ma, stderr):
    """Phân loại kết quả `git` gọi với môi trường THỪA HƯỞNG.

    `THOÁT 0`      ⇒ môi trường lành (ô ĐÓNG của khoản nợ cũ).
    `N-G18-00`     ⇒ `GIT_CONFIG_COUNT=N` thiếu `GIT_CONFIG_KEY_*`: MÔI TRƯỜNG của phiên hỏng,
                      KHÔNG phải cây hỏng và KHÔNG phải lỗi sản phẩm. Đây là khoản nợ NGOÀI repo
                      (chủ AG-00, docs/G21_CHOTCAY.md §5.1) — bộ kiểm phải IN RA, không được
                      nuốt, nhưng không được biến nó thành "nợ sản phẩm" của bản gộp.
    `LOI_KHAC`     ⇒ git hỏng vì lý do THẬT ⇒ ca PHẢI ĐỎ, báo nguyên văn stderr.

    Đây là bản vá GHIM STALE: bản cũ coi `128` là ô "nền" của cổng và ở chế độ `gop` biến một
    dị dạng MÔI TRƯỜNG thành ĐỎ của sản phẩm — trong khi từ trong repo KHÔNG sửa được gốc.
    """
    if ma == 0:
        return "OK"
    loi = (stderr or "").lower()
    if ma == 128 and "git_config_key_0" in loi and "parse command-line config" in loi:
        return "N-G18-00"
    return "LOI_KHAC"


class C_MoiTruong(unittest.TestCase):

    def test_c1_git_voi_moi_truong_NGUYEN_BAN(self):
        """CỔNG C3 — `git` với môi trường THỪA HƯỞNG phải ĐO ĐƯỢC và được PHÂN LOẠI đúng.

        Bản cũ (STALE) ghim `HEAD == HEAD_NEN` (148ecd3) ở đối chứng dương, nên trên cây đã gộp
        nó ĐỎ vì HEAD đã nhích — đúng `L-G20-A`. Nó còn biến `128` (dị dạng `GIT_CONFIG_*` của
        PHIÊN, N-G18-00) thành ô "nền" của một cổng mà chế độ `gop` luôn ĐỎ, dù đó là khoản nợ
        MÔI TRƯỜNG ngoài repo. Bất biến đúng, đọc TẠI CHỖ:
          (1) git thô hoặc THOÁT 0, hoặc hỏng ĐÚNG chữ ký N-G18-00 (in cảnh báo, chủ AG-00);
              hỏng vì lý do khác ⇒ ĐỎ kèm stderr thật;
          (2) git ĐÃ CHUẨN HOÁ môi trường phải thoát 0, trả HEAD hợp lệ, và HEAD phải NẰM TRÊN
              nền lịch sử (`merge-base --is-ancestor`) — KHÔNG so bằng.
        """
        r = _git("rev-parse", "HEAD", tho=True)
        loai = phan_loai_git_tho(r.returncode, r.stderr)
        _dc_am("git-tho")

        # ĐỐI CHỨNG ÂM của CHÍNH BỘ PHÂN LOẠI: nó phải phân biệt dị dạng môi trường với lỗi thật.
        self.assertEqual(phan_loai_git_tho(
            128, "error: missing config key GIT_CONFIG_KEY_0\n"
                 "fatal: unable to parse command-line config"),
            "N-G18-00", "bộ phân loại KHÔNG nhận ra chữ ký N-G18-00")
        self.assertEqual(phan_loai_git_tho(1, "fatal: not a git repository"),
                         "LOI_KHAC", "bộ phân loại NUỐT một lỗi git THẬT thành N-G18-00")
        self.assertIn(loai, ("OK", "N-G18-00"),
                      "git thô hỏng vì lý do KHÁC N-G18-00: mã thoát %s · stderr=%r"
                      % (r.returncode, r.stderr[:300]))

        # ĐỐI CHỨNG DƯƠNG: CÙNG lệnh, chỉ khác là ĐÃ CHUẨN HOÁ gia đình biến ⇒ phải thoát 0.
        # KHÔNG ghim giá trị HEAD vào đối chứng (L-G20-A): đọc TẠI CHỖ, chỉ đòi nó hợp lệ và
        # nằm trên nền lịch sử.
        r2 = _git("rev-parse", "HEAD")
        r3 = _git("status", "--porcelain=v1", "-uall")
        self.assertEqual(r2.returncode, 0, "gỡ biến rồi mà git vẫn hỏng: %r" % r2.stderr[:200])
        self.assertEqual(r3.returncode, 0, "gỡ biến rồi mà `git status` vẫn hỏng: %r"
                         % r3.stderr[:200])
        head = r2.stdout.strip()
        self.assertRegex(head, r"^[0-9a-f]{40}$", "HEAD đọc tại chỗ không hợp lệ: %r" % head)
        self.assertEqual(_git("merge-base", "--is-ancestor", HEAD_NEN, head).returncode, 0,
                         "HEAD=%s KHÔNG nằm trên nền lịch sử %s" % (head, HEAD_NEN))
        _dc_duong("git-tho")
        print("\n  [C1] git thô=%s (%s) · git đã chuẩn hoá=0 · HEAD=%s (hậu duệ của nền)"
              % (r.returncode, loai, head[:12]))
        if loai == "N-G18-00":
            print("       CẢNH BÁO: khoản nợ MÔI TRƯỜNG N-G18-00 VẪN MỞ (GIT_CONFIG_COUNT thiếu "
                  "KEY_*) — chủ AG-00, KHÔNG phải nợ sản phẩm; mọi lệnh git của bộ kiểm đi qua "
                  "môi trường đã chuẩn hoá.")

    def test_c2_bien_moi_truong_di_dang_duoc_nhan_dien(self):
        """Mô tả ĐÚNG cái dị dạng, để báo cáo không phải phỏng đoán."""
        dem = os.environ.get("GIT_CONFIG_COUNT")
        if dem is None:
            self.skipTest("CHƯA ĐO: phiên này KHÔNG đặt GIT_CONFIG_COUNT")
        khoa = [k for k in os.environ if k.startswith("GIT_CONFIG_KEY_")]
        gia_tri = [k for k in os.environ if k.startswith("GIT_CONFIG_VALUE_")]
        print("\n  [C2] GIT_CONFIG_COUNT=%s · KEY_*=%.0f · VALUE_*=%d"
              % (dem, len(khoa), len(gia_tri)))
        if int(dem) > 0 and not khoa:
            self.assertEqual(len(gia_tri), int(dem),
                             "dị dạng KHÁC mô tả trong N-G18-00 — phải đọc lại")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7. B — GIAO DIỆN: BÀN PHÍM TRONG MÀN (V-13911, phần còn lại)
# ══════════════════════════════════════════════════════════════════════════════════════════════

class B_GiaoDien(unittest.TestCase):

    def test_b1_tang_3_ban_phim_trong_man(self):
        """CỔNG C2 — đặc tả `06_ban_phim.spec.js` phải chạy HẾT và XANH.

        Bộ bốn đo được: (ĐẠT, HỎNG, BỎ QUA, KHÔNG CHẠY). Chỉ đếm `hỏng == 0` là KHÔNG ĐỦ: một
        ca hỏng làm Playwright bỏ luôn các ca sau trong cùng tệp, nên "0 hỏng" có thể che phép
        đo chưa hề chạy. Bất biến đúng KHÔNG GHIM SỐ CA (bản cũ ghim `(7,0,0)`; đặc tả đã thêm
        ca TỰ KIỂM `04b`, nên số ca đúng là ĐỌC TẠI CHỖ): thoát 0 + không hỏng + không bỏ qua +
        không "did not run" + ít nhất một ca đạt.

        Nền tầng 3 phải được KHAI KHO SQLite cho thư mục TẠM (`do_tang_3`); thiếu khai báo thì
        `app/migrate.py` TỪ CHỐI và đây là HỎNG THẬT của phép đo — `self.fail`, KHÔNG `skipTest`.
        """
        pw, nguon, ban = _pw_browsers()
        if pw is None:
            self.skipTest("CHƯA ĐO: thiếu nhị phân Chromium (BAN_GIAO §1)")
        ma, ra, ghi_chu = do_tang_3(spec=SPEC_BAN_PHIM, giay=420)
        if ma is None:
            self.skipTest("CHƯA ĐO: %s" % ghi_chu)
        duong = _ghi_log("tang3_ban_phim.log", ma, ra)
        dat, hong, bo, khong_chay = dem_playwright(ra)
        trong_man = dem_diem_dung_trong_man(ra)
        print("\n  [B1] %s · mã thoát=%s · %d đạt · %d hỏng · %d bỏ qua · %d KHÔNG CHẠY"
              % (ghi_chu, ma, dat, hong, bo, khong_chay))
        print("       ca 04 đo được: %s điểm dừng là điều khiển TRONG màn" % trong_man)
        _dc_am("tang3-ban-phim")

        # NỀN KHÔNG DỰNG ĐƯỢC là HỎNG THẬT — không được đọc thành "0 ca nên bỏ qua".
        if ghi_chu in ("nền không dựng được", "máy chủ không mở"):
            self.fail("KHÔNG dựng được NỀN tầng 3 (%s) — đây là HỎNG THẬT của phép đo, KHÔNG "
                      "phải BỎ QUA. Lý do:\n%s\nLog: %s"
                      % (ghi_chu, ra[-1200:], duong))
        self.assertGreater(dat + hong + bo + khong_chay, 0,
                           "tầng 3 chạy 0 ca mà vẫn im lặng — log: %s" % duong)
        # ĐỐI CHỨNG DƯƠNG của BỘ ĐẾM: output TỔNG HỢP đã biết phải đọc ra đúng cả bốn số.
        self.assertEqual(dem_playwright("  8 passed (1.2s)\n  1 failed\n  2 skipped\n"
                                        "  3 did not run\n"), (8, 1, 2, 3),
                         "bộ đếm Playwright mù với khuôn tổng hợp")
        # ĐỐI CHỨNG DƯƠNG của phép đo THẬT: phải thấy ít nhất một ca đã chạy và đạt.
        self.assertGreater(dat, 0, "bộ đếm không thấy ca ĐẠT nào ⇒ nó không đo gì")

        dat_c, vi = dat_cong_tang_3(ma, dat, hong, bo, khong_chay)
        _dc_duong("tang3-ban-phim")
        print("       phán quyết cổng C2 = %s (%s)" % (vi, "ĐẠT" if dat_c else "ĐỎ"))
        self.assertTrue(dat_c, "CỔNG C2 ĐỎ: tầng 3 bàn phím — %s (log: %s)" % (vi, duong))

    def test_b2_ca_04_phai_do_hien_duoc_so_diem_dung(self):
        """Chỉ ĐỌC LẠI log của `B1` — không chạy tầng 3 lần thứ hai.

        Nếu ca 04 hỏng/không chạy, log PHẢI nêu ra con số. Một ca hỏng mà không có số là một ca
        hỏng không đo được gì. KHÔNG ghim nguyên văn tiêu đề ca (đặc tả có thể thêm chữ): chỉ
        đòi log nhắc số hiệu `04` và có DÒNG ĐO điểm dừng trong màn.
        """
        duong = os.path.join(LOG_DIR, "tang3_ban_phim.log")
        if not os.path.exists(duong):
            self.skipTest("CHƯA ĐO: chưa có log tầng 3 (B1 bỏ qua)")
        ra = _doc(duong)
        co_ca_04 = re.search(r"\b04\s*—", ra) is not None
        self.assertTrue(co_ca_04, "log tầng 3 KHÔNG nhắc ca 04 ⇒ đặc tả đã đổi, phải đọc lại")
        _dc_am("tang3-so-do")
        trong_man = dem_diem_dung_trong_man(ra)
        self.assertIsNotNone(trong_man, "log không nêu số điểm dừng trong màn ⇒ phép đo câm")
        # ĐỐI CHỨNG DƯƠNG: bộ đọc PHẢI đọc ra đúng số từ một dòng TỔNG HỢP đã biết.
        gia = "[đo] 30 lượt Tab: 11 điểm dừng là điều khiển trong màn · 0 lượt ở body"
        self.assertEqual(dem_diem_dung_trong_man(gia), 11, "bộ đọc số bị mù")
        _dc_duong("tang3-so-do")
        print("\n  [B2] ca 04 trên nền: %s điểm dừng là điều khiển TRONG màn (ngưỡng đặc tả: >10)"
              % trong_man)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 8. A5 — CỔNG "CÂY SẠCH" CỦA WAVE TRƯỚC (N-G19-03) — NAY THEO LUẬT VÙNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# BẢN CŨ (STALE): đo "0/2 cổng cũ XANH" — tức GHIM khoản nợ "tệp hợp lệ của tôi làm cổng cũ ĐỎ".
# Khoản nợ đó đã được đóng bằng LUẬT VÙNG của `thu_g21_chotcay` (g17/g18 miễn trừ `docs/` + mọi
# thư mục `thu*`). Giữ nguyên số 0/2 là bắt bản gộp phải tái tạo một lỗi đã sửa — đúng loại
# GHIM STALE đang phải diệt.
#
# BẢN MỚI: bất biến "KHÔNG có thay đổi NGOÀI các tệp mà wave đang làm". "Tệp wave đang làm" =
# vùng thử/tài liệu, TỰ DÒ từ cây; cổng cũ phải XANH khi cây chỉ bẩn trong vùng đó. ĐỐI CHỨNG ÂM
# giữ nguyên răng: một tệp SẢN PHẨM bẩn phải bị luật bắt; và hai ca `a1b` của chính g17/g18 (canh
# phạm vi miễn trừ) phải XANH — nếu ai đó quay lại danh sách tên cứng, chúng ĐỎ ngay.

CONG_CAY_SACH = (
    ("thu_qa_g17.py", ["python3", "app/thu/thu_qa_g17.py", "A_Nen.test_a1_cay_sach_va_head"]),
    ("thu_qa_g18.py",
     ["python3", "app/thu/thu_qa_g18.py", "A_Nen.test_a1_cay_sach_mien_tru_dung_hai_tep_ag01"]),
)

# Hai ca TỰ KIỂM của chính g17/g18 canh PHẠM VI miễn trừ (không phải canh cây). Chúng ĐỎ nếu
# miễn trừ quay lại danh sách tên cứng hoặc trôi khỏi vùng TỰ DÒ — nên đây là đối chứng âm
# KHÔNG phụ thuộc việc cây có bẩn hay không.
TU_KIEM_PHAM_VI = (
    ("thu_qa_g17.py", ["python3", "app/thu/thu_qa_g17.py",
                       "A_Nen.test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu"]),
    ("thu_qa_g18.py", ["python3", "app/thu/thu_qa_g18.py",
                       "A_Nen.test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu"]),
)


class A5_CongCaySach(unittest.TestCase):

    def test_g1_cong_cay_sach_wave_truoc_khong_do_vi_tep_AG01_hop_le(self):
        """CỔNG C1 — cổng "cây sạch" của wave trước phải XANH khi cây chỉ bẩn trong VÙNG wave.

        Bất biến đúng (đọc TẠI CHỖ, không ghim tên tệp):
          (1) `thu_qa_g17.py` + `thu_qa_g18.py` chạy XANH trên cây này, và phép đo của chúng
              không được CHẾT (`AttributeError` / `Ran 0 tests`) — một phép đo chết không phải
              "cây bẩn";
          (2) mọi dòng `git status` thật đều nằm trong vùng thử/tài liệu (`docs/`, `thu*`);
          (3) hai ca tự kiểm phạm vi của chính g17/g18 XANH — quay lại danh sách tên cứng là ĐỎ.
        ĐỐI CHỨNG ÂM: một đường SẢN PHẨM bẩn (`admin/admin.js`) PHẢI bị luật bắt.
        """
        _dc_am("cong-cay-sach")
        ket = []
        for ten, lenh in CONG_CAY_SACH:
            ma, ra, _ = _chay(lenh, giay=300)
            ket.append((ten, ma, ra))
            print("       %s → mã thoát %s" % (ten, ma))
            self.assertIsNone(re.search(r"AttributeError|Ran 0 tests", ra),
                              "PHÉP ĐO CHẾT ở %s (tên ca đổi / 0 ca) — KHÔNG phải cây bẩn:\n%s"
                              % (ten, ra[-800:]))
        xanh = sum(1 for _, ma, _ in ket if ma == 0)
        dat, vi = dat_cong("cong-cay-sach", xanh)

        # (2) BẤT BIẾN CỦA A5: "cây sạch" = không thay đổi NGOÀI tệp mà wave đang làm.
        vung = _vung_wave()
        st = _git("status", "--porcelain=v1", "-uall").stdout.splitlines()
        ngoai_vung = [d for d in st if d.strip() and not _la_dong_cua_wave(d, vung)]
        self.assertEqual(ngoai_vung, [],
                         "cây có thay đổi NGOÀI vùng thử/tài liệu %s: %s"
                         % (vung, ngoai_vung))
        # ĐỐI CHỨNG ÂM: luật vùng (dùng chung `thu_g21_chotcay`) PHẢI bắt được tệp sản phẩm.
        mau = chotcay.mau_vung_chuan(goc=GOC_CAY)
        self.assertEqual(chotcay.phan_loai([" M admin/admin.js"], mau)["do"],
                         [" M admin/admin.js"],
                         "luật miễn trừ NUỐT mã sản phẩm ⇒ 'cây sạch' vô nghĩa")
        self.assertEqual(chotcay.phan_loai(["?? app/server.py"], mau)["do"],
                         ["?? app/server.py"], "luật miễn trừ NUỐT tệp sản phẩm MỚI")
        # ĐỐI CHỨNG DƯƠNG: tệp MỚI của wave trong vùng thử/tài liệu PHẢI được tha — nếu không,
        # "cây sạch" bất khả thi ngay khi wave tạo tệp hợp lệ (N-G19-03 tái diễn).
        self.assertEqual(chotcay.phan_loai(
            ["?? docs/G20_MEASURE_FIX.md", "?? app/thu/thu_moi.py"], mau)["do"], [],
            "luật miễn trừ CHẶN tệp hợp lệ trong vùng thử/tài liệu")

        # (3) ĐỐI CHỨNG ÂM ĐỘC LẬP với cây: phạm vi miễn trừ của g17/g18 phải còn theo LUẬT.
        for ten, lenh in TU_KIEM_PHAM_VI:
            ma, ra, _ = _chay(lenh, giay=300)
            print("       %s tự kiểm phạm vi → mã thoát %s" % (ten, ma))
            self.assertEqual(ma, 0, "PHẠM VI MIỄN TRỪ ĐÃ TRÔI về danh sách tên cứng ở %s:\n%s"
                             % (ten, ra[-800:]))

        _dc_duong("cong-cay-sach")
        print("\n  [G1] cổng cây sạch wave trước XANH: %d/2 · vùng wave TỰ DÒ=%s · "
              "thay đổi ngoài vùng=0 · luật bắt được tệp sản phẩm · phán quyết=%s"
              % (xanh, vung, vi))
        self.assertTrue(dat, "CỔNG C1 ĐỎ: %s" % vi)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 8b. C4/C5 — HAI KHOẢN NỢ ĐO ĐƯỢC KHÁC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _so_tep_san_xuat_import_truy_van(goc_app=None):
    """Đếm tệp SẢN XUẤT (không kể `app/thu/**`) import `app/truy_van.py`.

    Bộ thử `app/thu/thu_truy_van.py` CÓ import — nhưng đó là bộ thử, không phải đường vào của
    người dùng. Một mô-đun chỉ được bộ thử gọi là mô-đun KHÔNG CÓ ĐƯỜNG VÀO.

    `goc_app` cho phép đo trên một cây TẠM (đối chứng âm/dương của chính bộ dò), mặc định là
    `app/` của cây thật.
    """
    goc_app = GOC_APP if goc_app is None else goc_app
    dem = []
    for goc, _, tep in os.walk(goc_app):
        if os.path.join(goc_app, "thu") in goc:
            continue
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            duong = os.path.join(goc, t)
            if re.search(r"^\s*(import\s+truy_van\b|from\s+truy_van\b)", _doc(duong), re.M):
                dem.append(os.path.relpath(duong, GOC_CAY))
    return sorted(dem)


class C4_C5_NoKhac(unittest.TestCase):

    def test_c4_route_truy_van_va_migration_v9(self):
        """CỔNG C4 — C6 của G19: v9 VÀ route thật. Nửa vời (một trong hai) là ĐỎ.

        BẢN CŨ (STALE) có dòng 702 `assertEqual(nhap, [])` — nó GHIM TRẠNG THÁI NỀN "chưa tệp
        SẢN XUẤT nào import `truy_van`". Khi route được đóng thật (`app/server.py` import và dùng
        `truy_van`), phép đo đúng lại bị bắt ĐỎ vì sản phẩm đã sửa đúng — `docs/G22_CONTRACT.md`
        §0ter ghi rõ đây là họ `H5`/`L-G20-A`. Bất biến đúng, không ghim trạng thái nền:
          - `PHIEN_BAN_SCHEMA >= 9` (SÀN, không ghim đúng 9) và có `nang_len_v9`;
          - có ÍT NHẤT một tệp SẢN XUẤT tham chiếu `truy_van` ⇒ cổng ĐÓNG.
        ĐỐI CHỨNG ÂM: trên cây TẠM, gỡ import route ⇒ bộ dò trả 0 và cổng `(True, False)` PHẢI
        ĐỎ ở chế độ `gop` — nếu không, "route đã đóng" chỉ là một lời khai.
        """
        sys.path.insert(0, GOC_APP)
        import csdl  # noqa: E402
        import migrate  # noqa: E402
        schema_ok = (int(getattr(csdl, "PHIEN_BAN_SCHEMA", 0)) >= 9
                     and hasattr(migrate, "nang_len_v9"))
        nhap = _so_tep_san_xuat_import_truy_van()
        route_ok = len(nhap) >= 1
        do_duoc = (schema_ok, route_ok)
        dat, vi = dat_cong("truy-van-C6", do_duoc)
        _dc_am("truy-van-C6")
        # ĐỐI CHỨNG DƯƠNG: mẫu dò phải khớp chính bộ thử `thu_truy_van.py` (nếu mù thì "0 tệp
        # sản xuất" không chứng minh được gì).
        than = _doc(os.path.join(GOC_THU, "thu_truy_van.py"))
        self.assertTrue(re.search(r"^\s*import\s+truy_van\b", than, re.M),
                        "bộ dò mẫu không khớp cả tệp thử CÓ import ⇒ mẫu sai")
        # ĐỐI CHỨNG ÂM/DƯƠNG LÀM THẬT trên cây TẠM — không khẳng định suông.
        tam = tempfile.mkdtemp(prefix="veh-g20-tv-")
        try:
            gia = os.path.join(tam, "server_gia.py")
            with open(gia, "w", encoding="utf-8") as f:
                f.write("import truy_van\ntruy_van.tim_don('x')\n")
            self.assertTrue(any(p.endswith("server_gia.py")
                                for p in _so_tep_san_xuat_import_truy_van(tam)),
                            "bộ dò MÙ với tệp SẢN XUẤT có import truy_van")
            with open(gia, "w", encoding="utf-8") as f:
                f.write("# import truy_van\ntruy_van.tim_don('x')\n")
            self.assertEqual(_so_tep_san_xuat_import_truy_van(tam), [],
                             "bộ dò vẫn thấy route sau khi import bị GỠ ⇒ dương tính giả")
        finally:
            shutil.rmtree(tam, ignore_errors=True)
        # NỀN CŨ (route chưa mở) PHẢI ĐỎ ở chế độ nghiệm thu bản đã gộp — đây là "đối chứng âm"
        # của chính cổng, không phải một con số lịch sử được miễn trừ.
        dat_nen, vi_nen = dat_cong("truy-van-C6", (True, False), che_do="gop")
        self.assertFalse(dat_nen, "cổng C4 CHO QUA trạng thái nền (True, False) ở chế độ gộp: %s"
                         % vi_nen)
        _dc_duong("truy-van-C6")
        print("\n  [C4] PHIEN_BAN_SCHEMA=%s · nang_len_v9=%s · tệp SẢN XUẤT import truy_van=%d %s"
              % (csdl.PHIEN_BAN_SCHEMA, hasattr(migrate, "nang_len_v9"), len(nhap), nhap or ""))
        print("       phán quyết cổng C4 = %s (%s) · nền (True, False) bị phán ĐỎ khi gộp"
              % (vi, "ĐẠT" if dat else "ĐỎ"))
        self.assertTrue(dat, "CỔNG C4 ĐỎ: %s" % vi)

    def test_c5_co_bo_thu_g19_tong_hop_chay_duoc(self):
        """CỔNG C5 — phải có ÍT NHẤT một bộ G19-tổng-hợp CHẠY THẬT trên cây đã gộp."""
        ung_vien = sorted(t for t in os.listdir(GOC_THU)
                          if re.match(r"thu_qa_g19.*\.py$", t))
        self.assertTrue(ung_vien, "không còn tệp `thu_qa_g19*.py` nào ⇒ phép đo vô nghĩa")
        chi_tiet = []
        for t in ung_vien:
            ma, ra, _ = _chay(["python3", os.path.join("app", "thu", t)], giay=1200)
            m = re.findall(r"Ran (\d+) tests?", ra)
            n = int(m[-1]) if m else 0
            # VÁ `N-G22-01`: `Ran N` KỂ ca BỎ QUA ⇒ phải TRỪ ra mới biết có ca nào CHẠY.
            bq = int((re.findall(r"skipped=(\d+)", ra) or ["0"])[-1])
            chi_tiet.append((t, ma, n, bq, max(n - bq, 0)))
            print("       %s → mã thoát %s · %d ca · %d BỎ QUA · %d CHẠY THẬT"
                  % (t, ma, n, bq, max(n - bq, 0)))
        # XANH chỉ khi có ca THẬT SỰ CHẠY và ĐẠT: `nc > 0` (ĐÃ TRỪ bỏ qua), không phải `n > 0`.
        chay = min(sum(1 for _, ma, n, bq, nc in chi_tiet
                       if ma == 0 and n > 0 and nc > 0), 1)
        dat, vi = dat_cong("bo-g19-tong-hop", chay)
        _dc_am("bo-g19-tong-hop")
        # ĐỐI CHỨNG DƯƠNG: chính bộ đếm `Ran N tests` phải đọc ra được số từ output TỔNG HỢP
        # đã biết — nếu không, "0 ca" có thể chỉ là bộ đếm mù.
        self.assertEqual(int(re.findall(r"Ran (\d+) tests?", "Ran 7 tests in 0.1s")[-1]), 7)
        _dc_duong("bo-g19-tong-hop")
        print("  [C5] bộ `thu_qa_g19*.py` CHẠY THẬT trên cây này: %d/%d · phán quyết=%s"
              % (chay, len(ung_vien), vi))
        self.assertTrue(dat, "CỔNG C5 ĐỎ: %s" % vi)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 9. T — CHỐT (a): TỰ KIỂM BỘ ĐO CHẠY TRONG TIẾN TRÌNH CON
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Vì sao TIẾN TRÌNH CON chứ không phải gọi hàm tại chỗ: một ca tự kiểm gọi thẳng hàm trong
# CÙNG tiến trình vẫn có thể "xanh" nhờ trạng thái đã bị chính bộ thử làm bẩn. Chạy bằng
# `subprocess` thì tiến trình mới HOÀN TOÀN, và cái được kiểm là ĐÚNG thứ người chấm sẽ chạy:
# `python3 <tệp> <ca>`.

CA_TU_KIEM = "T_TuKiem.test_z9_ca_CO_Y_HONG_de_tu_kiem"


class T_TuKiem(unittest.TestCase):

    def test_t1_luat_phan_tu_choi_bon_kieu_xanh_gia(self):
        """Luật phán của bộ chạy chung phải TỪ CHỐI xanh giả. Kiểm bằng dữ liệu TỔNG HỢP."""
        sys.path.insert(0, GOC_THU)
        # Nạp ĐÚNG hàm phán của bộ chạy chung, không phải bản chép lại.
        than = _doc(os.path.join(GOC_THU, "chay_tat_ca.sh"))
        self.assertIn("ca — ĐẠT", than, "bộ chạy chung đã đổi luật phán — phải đọc lại")
        # Luật: ĐẠT khi mã thoát 0 VÀ có dấu vết đã chạy VÀ số ca > 0.
        def phan(ma, ra, n):
            co = bool(re.search(r"^OK( |$)|ca — ĐẠT", ra, re.M))
            return ma == 0 and co and n > 0
        _dc_am("luat-phan")
        self.assertFalse(phan(0, "", 0), "thoát 0 + 0 ca mà vẫn ĐẠT")
        self.assertFalse(phan(0, "chay xong", 5), "thoát 0 nhưng KHÔNG dấu vết đã chạy")
        self.assertFalse(phan(1, "OK\nRan 5 tests", 5), "in OK rồi thoát 1 mà vẫn ĐẠT")
        self.assertFalse(phan(0, "OK\nRan 0 tests", 0), "Ran 0 tests + OK mà vẫn ĐẠT")
        _dc_duong("luat-phan")
        self.assertTrue(phan(0, "OK\nRan 5 tests", 5), "lượt chạy TỐT lại bị phán HỎNG")
        print("\n  [T1] luật phán TỪ CHỐI 4 kiểu xanh giả · NHẬN lượt chạy tốt")

    def test_t2_tu_kiem_bang_TIEN_TRINH_CON(self):
        """CHỐT (a) — ca CỐ Ý HỎNG chạy bằng subprocess phải cho mã thoát KHÁC 0 và có FAILED."""
        # `VIP_G20_CHAY_MOI=1` chỉ mở ĐÚNG ca mồi, và chỉ trong tiến trình con này. Làn thường
        # KHÔNG BAO GIỜ đặt biến đó, nên ca mồi luôn là BỎ QUA ở làn thường.
        ma, ra, _ = _chay([sys.executable, os.path.abspath(__file__), CA_TU_KIEM],
                          env={"VIP_G20_CHAY_MOI": "1"}, giay=180)
        self.assertNotEqual(ma, 0, "ca cố ý hỏng mà tiến trình con thoát 0 — chốt (a) VÔ HIỆU")
        self.assertIn("FAILED", ra, "không thấy FAILED trong output tiến trình con")
        _dc_am("tu-kiem-con")
        # ĐỐI CHỨNG DƯƠNG: CÙNG tiến trình con, chạy một ca ĐẠT ⇒ phải thoát 0 và có `OK`.
        ma2, ra2, _ = _chay([sys.executable, os.path.abspath(__file__),
                             "T_TuKiem.test_t1_luat_phan_tu_choi_bon_kieu_xanh_gia"],
                            env={"VIP_G20_CHAY_MOI": "1"}, giay=180)
        self.assertEqual(ma2, 0, "ca ĐẠT mà tiến trình con thoát %s" % ma2)
        self.assertIn("OK", ra2, "ca ĐẠT mà không có dòng OK")
        _dc_duong("tu-kiem-con")
        print("\n  [T2] tiến trình con: ca cố ý hỏng → thoát %s + FAILED · ca đạt → thoát 0 + OK"
              % ma)

    def test_t3_bo_dem_playwright_co_rang(self):
        """Bộ đếm `did not run` — chốt chống "0 hỏng" che phép đo chưa chạy."""
        gia = ("  1 failed\n  3 did not run\n  47 passed (2.0m)\n")
        self.assertEqual(dem_playwright(gia), (47, 1, 0, 3), "bộ đếm đọc SAI output tổng hợp")
        _dc_am("dem-playwright")
        tot = "  47 passed (2.0m)\n"
        self.assertEqual(dem_playwright(tot), (47, 0, 0, 0))
        self.assertEqual(dem_playwright(""), (0, 0, 0, 0))
        _dc_duong("dem-playwright")
        print("\n  [T3] bộ đếm: (đạt, hỏng, bỏ qua, KHÔNG CHẠY) đọc đúng cả 3 khuôn")

    def test_t5_go_duoc_bien_moi_truong_khoi_tien_trinh_con(self):
        """CHỐT CHỐNG ĐỆ QUY — `bo_bien` phải THẬT SỰ gỡ biến khỏi tiến trình con.

        Ca này tồn tại vì `H1` đã ĐỆ QUY VÔ HẠN một lượt: nó gọi `chay_tat_ca.sh`, bộ chạy
        chung chạy lại chính tệp này ở làn đầy đủ (cờ vẫn còn), và cứ thế. Một ca tự kiểm
        chạy trong tiến trình con là cách duy nhất để biết việc gỡ biến có tác dụng thật.
        """
        lenh = [sys.executable, "-c",
                "import os;print('CO=%r' % ('VIP_G20_DAY_DU' in os.environ))"]
        _dc_am("go-bien")
        ma, ra, _ = _chay(lenh, env={"VIP_G20_DAY_DU": "1"},
                          bo_bien=("VIP_G20_DAY_DU",), giay=60)
        self.assertIn("CO=False", ra,
                      "`bo_bien` KHÔNG gỡ được biến ⇒ H1 sẽ ĐỆ QUY VÔ HẠN (mã thoát %s)" % ma)
        # ĐỐI CHỨNG DƯƠNG: KHÔNG gỡ thì biến PHẢI còn — nếu không, phép đo trên là mù.
        ma2, ra2, _ = _chay(lenh, env={"VIP_G20_DAY_DU": "1"}, giay=60)
        self.assertIn("CO=True", ra2, "biến chưa từng được đặt ⇒ phép đo trên vô nghĩa")
        _dc_duong("go-bien")
        print("\n  [T5] `bo_bien` gỡ được biến (CO=False) · không gỡ thì biến còn (CO=True)")

    def test_t4_gia_tri_NUA_VOI_luon_la_DO(self):
        """RĂNG của cổng: một bản vá NỬA VỜI không được lọt qua ở BẤT KỲ chế độ nào.

        Hai cổng còn lại được kiểm bằng dữ liệu TỔNG HỢP:
          · `cong-cay-sach`: 1/2 cổng xanh = NỬA VỜI ⇒ ĐỎ cả hai chế độ;
          · `tang3-ban-phim`: bất biến "chạy TRỌN VẸN + xanh" — 0 hỏng nhưng còn ca KHÔNG CHẠY
            vẫn ĐỎ; và số ca ĐƯỢC PHÉP đổi (7 hay 9 đều ĐÓNG) vì không ghim con số của lượt cũ.
        """
        _dc_am("nua-voi")
        # Cổng hai chiều: 1/2 cổng cây sạch = NỬA VỜI.
        self.assertEqual(phan_quyet("cong-cay-sach", 1), "NUA_VOI",
                         "cổng cây sạch coi 1/2 là hợp lệ ⇒ bản vá nửa vời lọt qua")
        for che in ("nen", "gop"):
            dat, _ = dat_cong("cong-cay-sach", 1, che_do=che)
            self.assertFalse(dat, "cổng cây sạch cho 1/2 qua ở chế độ %s" % che)

        # Cổng tầng 3: MỌI dạng "chưa trọn vẹn" đều ĐỎ; đổi số ca không được làm nó ĐỎ.
        for gia in ((0, 5, 0, 0, 2),   # 0 hỏng NHƯNG 2 ca "did not run"
                    (0, 5, 1, 0, 0),   # có ca hỏng
                    (0, 5, 0, 1, 0),   # có ca bị bỏ qua (chưa chạy hết)
                    (1, 5, 0, 0, 0)):  # Playwright thoát ≠ 0
            dat, vi = dat_cong_tang_3(*gia)
            self.assertFalse(dat, "cổng tầng 3 CHO QUA %r: %s" % (gia, vi))
        dat, vi = dat_cong_tang_3(0, 0, 0, 0, 0)
        self.assertFalse(dat, "0 ca chạy mà cổng tầng 3 vẫn ĐẠT: %s" % vi)
        for gia in ((0, 7, 0, 0, 0), (0, 8, 0, 0, 0), (0, 9, 0, 0, 0)):
            dat, vi = dat_cong_tang_3(*gia)
            self.assertTrue(dat, "lượt chạy TRỌN VẸN %r lại bị phán ĐỎ: %s" % (gia, vi))
        _dc_duong("nua-voi")
        # Dương: giá trị ĐÓNG thật của cổng còn lại PHẢI qua được ở chế độ gộp.
        dat, vi = dat_cong("cong-cay-sach", SO_DO["cong-cay-sach"]["dong"])
        self.assertTrue(dat, "giá trị ĐÓNG của cổng cây sạch lại bị phán ĐỎ: %s" % vi)
        print("\n  [T4] 1/2 cổng cây sạch + mọi dạng tầng 3 chưa trọn vẹn đều ĐỎ · "
              "số ca 7/8/9 đều ĐÓNG (KHÔNG ghim số) · giá trị ĐÓNG qua được")

    def test_z9_ca_CO_Y_HONG_de_tu_kiem(self):
        """CA CỐ Ý HỎNG — chỉ dùng làm mồi cho `T2`. KHÔNG chạy trong làn thường."""
        if os.environ.get("VIP_G20_CHAY_MOI") != "1":
            self.skipTest("mồi cho T2 — chỉ chạy trong tiến trình con của T2")
        self.assertEqual(1, 2, "ca cố ý hỏng: dùng để chứng minh chốt (a) có răng")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 10. Z — CHỐT (b) + VÂN TAY CÂY
# ══════════════════════════════════════════════════════════════════════════════════════════════

class Z_ChotChan(unittest.TestCase):

    def test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong(self):
        """CHỐT (b). In sổ ra, và TỰ PHÁN HỎNG nếu một nhóm phủ định thiếu ca dương."""
        thieu = nhom_thieu_duong()
        print()
        for k in sorted(DOI_CHUNG):
            v = DOI_CHUNG[k]
            print("  [Z1] %-22s âm=%d dương=%d" % (k, v["am"], v["duong"]))
        # TỰ KIỂM chính Z1: một nhóm âm CỐ Ý không có dương PHẢI bị bắt.
        gia = {"nhom-gia-thieu-duong": {"am": 1, "duong": 0}}
        self.assertEqual(nhom_thieu_duong(gia), ["nhom-gia-thieu-duong"],
                         "Z1 MÙ: nhóm âm thiếu dương mà nó không bắt được")
        self.assertEqual(nhom_thieu_duong({"ok": {"am": 1, "duong": 1}}), [],
                         "Z1 báo động giả với nhóm đã đủ hai chiều")
        self.assertGreaterEqual(len(DOI_CHUNG), 6, "sổ đối chứng quá mỏng ⇒ chốt (b) hình thức")
        self.assertEqual(thieu, [], "THIẾU ĐỐI CHỨNG DƯƠNG cho: %s" % thieu)
        print("  [Z1] %d nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả"
              % len(DOI_CHUNG))

    def test_z2_cay_khong_doi_ngoai_vung_wave(self):
        """Vân tay cây ĐƯỢC THEO DÕI, miễn trừ theo VÙNG thử/tài liệu — KHÔNG theo tên tệp.

        Bản cũ đòi "chỉ đúng hai tệp AG-01 G20" — trong repo nhiều làn song song, điều đó bất
        khả thi và chính là `N-G19-03` (`docs/G22_GIOIHAN.md` §6.2). Bất biến đúng: KHÔNG có
        thay đổi NGOÀI vùng thử/tài liệu; một `docs/…`/`app/thu/…` mới của wave tự khớp.
        """
        van_tay = van_tay_cay()
        vung = _vung_wave()
        st = _git("status", "--porcelain=v1", "-uall").stdout.splitlines()
        la = [d for d in st if d.strip() and not _la_dong_cua_wave(d, vung)]
        self.assertEqual(la, [], "cây có thay đổi NGOÀI vùng thử/tài liệu %s: %s"
                         % (vung, la))
        self.assertRegex(van_tay, r"^[0-9a-f]{64}$")
        _dc_am("cay-sach")
        # ĐỐI CHỨNG ÂM: tệp SẢN PHẨM (kể cả tệp MỚI) KHÔNG được miễn trừ.
        for dong in (" M admin/admin.js", "?? app/webhook.py", "?? app/server.py"):
            self.assertFalse(_la_dong_cua_wave(dong, vung),
                             "bộ lọc miễn trừ NHẦM tệp sản phẩm: %r" % dong)
        # Đổi tên kéo tệp sản phẩm vào vùng thử vẫn là thay đổi sản phẩm.
        self.assertFalse(_la_dong_cua_wave("R  app/server.py -> docs/server.py", vung),
                         "bộ lọc miễn trừ NHẦM một lần ĐỔI TÊN từ sản phẩm vào docs")
        # ĐỐI CHỨNG DƯƠNG: tệp của wave trong vùng thử/tài liệu PHẢI được miễn trừ — nếu không,
        # cổng "cây sạch" bất khả thi ngay khi wave tạo tài liệu/bộ thử hợp lệ.
        for dong in ("?? docs/G20_MEASURE_FIX.md", " M app/thu/thu_qa_g20.py",
                     "?? thu_giao_dien/_bao-cao/moi.json"):
            self.assertTrue(_la_dong_cua_wave(dong, vung),
                            "bộ lọc CHẶN tệp hợp lệ trong vùng thử/tài liệu: %r" % dong)
        _dc_duong("cay-sach")
        print("\n  [Z2] vân tay cây (miễn trừ vùng %s) = %s" % (vung, van_tay))
        print("       git status ngoài vùng thử/tài liệu: %s" % (la or "RỖNG"))

    def test_z3_khong_co_luot_goi_ra_ngoai_trong_bo_kiem(self):
        """Bộ kiểm TỰ SOI chính nó: không URL nào ngoài `127.0.0.1`."""
        than = _doc(os.path.abspath(__file__))
        ngoai = re.findall(r"https?://(?!127\.0\.0\.1)[A-Za-z0-9._-]+", than)
        self.assertEqual(ngoai, [], "bộ kiểm có URL ra ngoài: %s" % sorted(set(ngoai)))
        # CHỐT BIND: phải ÉP `VIP_HUB_BIND=127.0.0.1` cho máy chủ tầng 3, không chỉ trông cậy
        # vào giá trị mặc định — một biến thừa hưởng có thể mở cổng ra ngoài (BỊ CẤM).
        self.assertIn('env["VIP_HUB_BIND"] = "127.0.0.1"', than,
                      "bộ kiểm KHÔNG ép bind 127.0.0.1 ⇒ cổng có thể mở ra ngoài")
        _dc_am("khong-ra-ngoai")
        self.assertIn("127.0.0.1", than, "bộ kiểm không nhắc 127.0.0.1 ⇒ phép soi vô nghĩa")
        _dc_duong("khong-ra-ngoai")
        print("\n  [Z3] 0 URL ngoài 127.0.0.1 · ÉP bind `VIP_HUB_BIND=127.0.0.1` cho máy chủ tầng 3")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 11. H — HỒI QUY TOÀN PHẦN (chỉ làn đầy đủ)
# ══════════════════════════════════════════════════════════════════════════════════════════════

# Nhóm hỏng ĐÃ CÓ TÊN của wave trước. Một bộ đỏ chỉ được tha khi rơi vào một nhóm ở đây VÀ
# chạy lại một mình thì ĐẠT — nếu không nó rơi vào HỎNG SẢN PHẨM và cổng H1 ĐỎ.
NHOM_HONG_DA_BIET = {
    "N-G19-03 cổng cây sạch wave trước": lambda t: t in ("thu_qa_g17.py", "thu_qa_g18.py"),
    "N-G18-01 ca 04 tầng 3 (khoản nợ G20)": lambda t: t == "thu_qa_g18.py",
}


def _phan_loai_hong(ten_bo):
    return [k for k, f in NHOM_HONG_DA_BIET.items() if f(ten_bo)]


class H_HoiQuy(unittest.TestCase):

    def test_h1_hoi_quy_toan_phan(self):
        if not DAY_DU:
            self.skipTest("CHƯA ĐO: làn đầy đủ (VIP_G20_DAY_DU=1)")
        # GỠ cờ làn đầy đủ khỏi tiến trình con: nếu không, bộ chạy chung sẽ chạy lại chính
        # tệp này ở làn đầy đủ ⇒ ĐỆ QUY VÔ HẠN. Phải dùng `bo_bien` — tự lọc ra một dict rồi
        # truyền vào `env` là VÔ HIỆU, vì `_chay` `update()` đè lên `os.environ`.
        BO = ("VIP_G20_DAY_DU", "VIP_G20_CHE_DO")
        ma, ra, giay = _chay(["sh", "app/thu/chay_tat_ca.sh"], giay=2400, bo_bien=BO)
        duong = _ghi_log("hoi_quy.log", ma, ra)
        m = re.search(r"python:\s+(\d+) ca · (\d+) bộ chạy thật", ra)
        self.assertIsNotNone(m, "không đọc được bảng tổng kết — log: %s" % duong)
        so_ca, so_bo = int(m.group(1)), int(m.group(2))
        mh = re.search(r"bộ hỏng:(.*)", ra)
        hong = (mh.group(1).strip().split() if mh else [])
        mq = re.search(r"\+ (\d+) bộ BỎ QUA", ra)
        bo_qua = int(mq.group(1)) if mq else 0
        me = re.search(r"E2E:\s+([^\n]+)", ra)
        print("\n  [H1] thoát=%s · %d ca · %d bộ · %d bỏ qua · %d hỏng %s · %.1fs"
              % (ma, so_ca, so_bo, bo_qua, len(hong), hong, giay))
        print("       E2E=%s · log=%s" % (me.group(1) if me else "?", duong))

        # Cổng "teo ca": số ca phải LỚN HƠN nền 1733 (nền + số ca của chính tệp này).
        self.assertGreater(so_ca, 1733, "số ca TEO so với nền 1733 — phép dò đang nhìn sai chỗ")
        self.assertGreaterEqual(so_bo, 47, "số bộ TEO so với nền 47")
        _dc_am("hoi-quy")
        # MỌI bộ đỏ phải rơi vào một nhóm ĐÃ CÓ TÊN. Bộ nào không rơi được = HỎNG SẢN PHẨM.
        #
        # Cố ý KHÔNG đòi `hong == []`: trên nền này hai khoản nợ CÓ THẬT (N-G19-03 và N-G18-01)
        # làm hồi quy đỏ, và đó là kết quả ĐÚNG. Việc của `H1` không phải là "không có bộ đỏ" —
        # mà là "KHÔNG có bộ đỏ nào VÔ DANH". Hai khoản nợ kia có cổng riêng (`G1`, `B1`) và
        # chúng ĐỎ ở chế độ `gop`; ở đây chúng chỉ được PHÂN LOẠI, không được tha.
        phan_loai = {}
        for ten in hong:
            nhom = _phan_loai_hong(ten)
            ma2, _, _ = _chay(["python3", os.path.join("app", "thu", ten)], giay=900, bo_bien=BO)
            phan_loai[ten] = (nhom, ma2)
            print("       ↻ %s chạy lại một mình → thoát %s · nhóm=%s"
                  % (ten, ma2, nhom or "KHÔNG CÓ NHÓM"))
            self.assertTrue(nhom, "BỘ ĐỎ KHÔNG RƠI VÀO NHÓM NÀO = HỎNG SẢN PHẨM: %s" % ten)
        _dc_duong("hoi-quy")
        print("       PHÂN LOẠI: %s"
              % "; ".join("%s → %s" % (t, "+".join(v[0])) for t, v in sorted(phan_loai.items()))
              or "       PHÂN LOẠI: không bộ nào đỏ")
        self.assertLessEqual(len(hong), 3,
                             "quá nhiều bộ đỏ (%d) — phải đọc lại: %s" % (len(hong), hong))


# ══════════════════════════════════════════════════════════════════════════════════════════════

def _in_dau():
    print("═" * 92)
    print("  AG-01 (G20) — BỘ KIỂM ĐỘC LẬP · nền đóng băng 148ecd3")
    print("  chế độ=%s%s" % (CHE_DO, "  (ô 'nen' cũng ĐỎ: nghiệm thu bản ĐÃ GỘP)"
                                 if CHE_DO == "gop" else "  (đo nợ trên nền)"))
    print("  làn=%s" % ("ĐẦY ĐỦ (hồi quy toàn phần)" if DAY_DU else "MẶC ĐỊNH"))
    print("  PHẠM VI: chỉ 127.0.0.1 · adapter MOCK · cổng hãng KHOÁ · cụm PostgreSQL :5432 KHÔNG đụng")
    print("═" * 92)


if __name__ == "__main__":
    _in_dau()
    unittest.main(verbosity=2)
