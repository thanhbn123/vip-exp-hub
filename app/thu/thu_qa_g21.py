#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-01 (G21) — BỘ KIỂM ĐỘC LẬP cho wave G21. VAI: NGƯỜI KIỂM, không phải người viết.

NỀN ĐO: `integration/g20 @ a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1` (worktree `g21-ag01-qa`).
KHÔNG dùng `main` (`de740dc`) — `main` KHÔNG chứa G13–G21.
Hai tệp AG-01 G21 được phép tạo: `app/thu/thu_qa_g21.py` (tệp này) · `docs/QA_G21.md`.

LỆNH CHẠY
    python3 app/thu/thu_qa_g21.py                       # làn MẶC ĐỊNH (đo nợ trên nền)
    VIP_G21_CHE_DO=gop python3 app/thu/thu_qa_g21.py    # NGHIỆM THU BẢN ĐÃ GỘP: nợ còn ⇒ ĐỎ
    VIP_G21_DAY_DU=1 python3 app/thu/thu_qa_g21.py      # + hồi quy toàn phần (chay_tat_ca.sh)

--------------------------------------------------------------------------------------------
NĂM LÀN SỬA CỦA G21, VÀ CỔNG FAIL CỦA TỪNG LÀN
--------------------------------------------------------------------------------------------
Mỗi làn một cổng, mỗi cổng một giá trị ĐO ĐƯỢC, và mỗi cổng có một ĐIỀU KIỆN ĐỎ viết ra chứ
không phải một lời hứa. Nguồn khoản nợ lấy từ BẰNG CHỨNG TRONG REPO (không phải từ một bảng
phân công — bảng đó tôi không có):

  AG-02 `sao-luu-fail-closed`  ← `G20_BACKUP_RESTORE.md` §5 (K-1..K-5): `khoi_phuc()` là
        `shutil.copy2` trần, KHÔNG kiểm tệp trước khi đè. CỔNG: số đầu vào ĐỘC HẠI được NHẬN.
  AG-03 `ro-credential-ngan`   ← `G20_DA_HANG.md` §5 + §8 R-2: tầng che theo TÊN chỉ đúng cho
        bốn tên của J&T ⇒ credential NGẮN của hãng khác RÒ. CỔNG: số tổ hợp (tên, giá trị) RÒ.
  AG-04 `harness-gioi-han`     ← `G20_CONTRACT_HARNESS.md` §6 (`N-G20-01`): `gioi_han.xoa_het()`
        xoá kho đếm DÙNG CHUNG ⇒ chặng G18-05 ĐỎ. CỔNG: mã thoát `trien_khai/g18/chay_harness.sh`.
  AG-04 `bo-g19-tong-hop`      ← `QA_G20.md` §2.5 (`C5`/`N-G20-01`): 0 bộ `thu_qa_g19*.py` chạy.
  AG-05 `cong-cay-sach`        ← `QA_G20.md` §2.1 (`C1`/`N-G19-03`): cổng cây sạch miễn trừ theo
        TÊN CỨNG ⇒ tệp hợp lệ của làn khác làm cổng cũ ĐỎ.
  AG-05 `git-tho`              ← `QA_G20.md` §2.3 (`C3`/`N-G18-00`): `GIT_CONFIG_*` dị dạng ⇒
        MỌI lệnh git thoát 128.
  AG-06 `tang3-ban-phim`       ← `QA_G20.md` §2.2 (`C2`/`V-13911`): ca 04 chỉ vào được 1 điều
        khiển TRONG màn (đặc tả đòi >10), và 3 ca sau KHÔNG HỀ CHẠY.
  (KHÔNG LÀN NÀO) `truy-van-C6` ← `QA_G20.md` §2.4 (`C4`, C6 của G19 nửa vời). AG-00 xác nhận
        ngày 16/10/2026: **C4 KHÔNG CÓ CHỦ SỞ HỮU** ⇒ nghiệm thu G21 VẪN FAILED nếu C4 chưa đóng,
        dù năm làn kia xanh. Cổng này ở đây để không ai đọc nhầm "năm làn xanh = G21 đạt".

--------------------------------------------------------------------------------------------
LUẬT BẰNG CHỨNG
--------------------------------------------------------------------------------------------
Mọi khẳng định đi kèm LỆNH THẬT + MÃ THOÁT THẬT + SỐ CA + SỐ BỎ QUA. Mã thoát lấy NGAY sau
lệnh, không qua ống. Mọi ca PHỦ ĐỊNH có ĐỐI CHỨNG DƯƠNG trong sổ `DOI_CHUNG`; `Z1` TỰ PHÁN HỎNG
nếu một nhóm âm thiếu dương. Cái gì không đo được nằm ở `docs/QA_G21.md` §5 CHƯA ĐO — đó là
LỖ HỔNG PHẠM VI, KHÔNG phải ĐẠT.

PHẠM VI HTTP — TUYỆT ĐỐI: không một lời gọi nào ra hãng, kể cả sandbox (`V-G09-01` +
`V-13906-05` CHƯA CẤP). Mọi phép đo lớp HTTP chỉ chạm `127.0.0.1` với cổng do hệ điều hành cấp.
Cụm PostgreSQL `:5432` KHÔNG bị đụng tới (D-8: CSDL nghiệp vụ vẫn SQLite).
"""

import hashlib
import http.server
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC_CAY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GOC_APP = os.path.join(GOC_CAY, "app")
GOC_THU = os.path.join(GOC_CAY, "app", "thu")

# Nền bắt buộc phải là TỔ TIÊN của HEAD. KHÔNG so bằng `==` với HEAD hiện tại: đó đúng là lỗi
# của bàn đo G20 (`thu_qa_g20.py` dòng 520 ghim `HEAD_NEN = 148ecd3` vào ĐỐI CHỨNG DƯƠNG của
# cổng C3, nên trên cây đã gộp nó ĐỎ vì lý do giả — xem `docs/QA_G21.md` §4.1 `L-G20-A`).
NEN_GOC = "a3400a8f8e2ed9ec987bd4cf9c16a9f1e5fb11a1"

TEP_DUOC_PHEP = ("docs/QA_G21.md", "app/thu/thu_qa_g21.py", "docs/G21_MEASURE_FIX.md")
TEP_G20_TAM = "app/thu/thu_qa_g20.py"   # chỉ để ĐỐI CHIẾU CHÉO, không bắt buộc phải có

CHE_DO = os.environ.get("VIP_G21_CHE_DO", "nen")
if CHE_DO not in ("nen", "gop"):
    CHE_DO = "nen"
DAY_DU = os.environ.get("VIP_G21_DAY_DU") == "1"

LOG_DIR = os.environ.get("VIP_G21_LOG") or os.path.join(tempfile.gettempdir(), "veh_g21_ag01_qa_log")

# Nhị phân Chromium: KHÔNG dùng cache hệ thống của dự án khác, và `thu_giao_dien/chay.sh` ghim
# `PLAYWRIGHT_BROWSERS_PATH=0` (tức `node_modules/playwright-core/.local-browsers`) — thư mục đó
# KHÔNG tồn tại trong worktree này, nên chạy `chay.sh` nguyên bản HỎNG VÌ MÔI TRƯỜNG (đo được:
# 7 failed · 44 did not run, tất cả ở `browserType.launch`). Bản chỉ định dưới đây là bản
# `BAN_GIAO.md` §1 đã ghim, cùng khuôn `thu_qa_g18.py` / `thu_qa_g20.py`.
PW_BROWSERS_CHI_DINH = os.path.expanduser(
    "~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers")
PW_BROWSERS_REPO = os.path.join(GOC_CAY, "node_modules", "playwright-core", ".local-browsers")

SPEC_BAN_PHIM = "06_ban_phim.spec.js"
CA_TRONG_MAN = "04 — Tab vào được các điều khiển TRONG màn"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. SỔ GIÁ TRỊ — HAI Ô, VÀ "NỬA VỜI" LUÔN ĐỎ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# "nen"  = giá trị TÔI ĐO ĐƯỢC trên `a3400a8` (khoản nợ CÒN NGUYÊN) — xem docs/QA_G21.md §1–§2.
# "dong" = giá trị phải có khi khoản nợ đã đóng.
# Giá trị KHÁC CẢ HAI ⇒ NUA_VOI ⇒ ĐỎ ở MỌI chế độ. Ở chế độ `gop` thì "nen" CŨNG ĐỎ.

SO_DO = {
    # AG-02 — `khoi_phuc()` nhận tệp độc hại: đo độc lập bằng `do_sao_luu_fail_closed()`.
    # Nền 4/4 nhận (0 byte · cắt 40% · hỏng magic · PGDMP). Đóng 0/4, VÀ tệp lành vẫn phải nhận.
    "sao-luu-fail-closed": {"nen": 4, "dong": 0},

    # AG-03 — số tổ hợp (tên trường, giá trị) RÒ credential ra `than_da_che`/`str(e)`.
    # Nền 2/5 (`x-mau-khoa-bi-mat` + ngắn, `maTaiKhoanGia` + ngắn). Đóng 0/5.
    "ro-credential-ngan": {"nen": 2, "dong": 0},

    # AG-04 — mã thoát `trien_khai/g18/chay_harness.sh` (chặng G18-05 đỏ vì kho đếm bị xoá).
    "harness-gioi-han": {"nen": 1, "dong": 0},

    # AG-04 — số bộ `thu_qa_g19*.py` CHẠY THẬT được ≥1 ca và thoát 0 (min(...,1)).
    "bo-g19-tong-hop": {"nen": 0, "dong": 1},

    # AG-05 — số cổng "cây sạch" của wave TRƯỚC còn ĐỎ khi cây chỉ có tệp hợp lệ của làn QA.
    # ĐO TRÊN `a3400a8`: cả BA cổng trong `CONG_CAY_SACH` đều ĐỎ ⇒ nền = 3. Đóng = 0, và "0"
    # là bất biến: MỌI cổng trong danh sách phải XANH. Không ghim "3" như một con số thành tích
    # — giá trị đo là `len(CONG_CAY_SACH) - số cổng XANH`, đọc tại chỗ từ danh sách.
    "cong-cay-sach": {"nen": 3, "dong": 0},

    # AG-05 — mã thoát `git rev-parse HEAD` trong môi trường ĐÃ CHUẨN HOÁ bằng bộ dùng chung
    # (`thu_g21_chotcay.env_git`). "Nền 128" là TRIỆU CHỨNG của môi trường `GIT_CONFIG_*` dị
    # dạng trên MÁY NÀY — lỗi MÔI TRƯỜNG, không phải lỗi sản phẩm (docs/OWNER_ACTIONS §F,
    # docs/G22_A1_GIT.md §1.1a). Cổng đo BẤT BIẾN: sau chuẩn hoá git chạy được (0); ba vế đối
    # chứng nằm trong `G2`.
    "git-tho": {"nen": 128, "dong": 0},

    # AG-06 — tầng 3, `06_ban_phim.spec.js`: số ca (HỎNG + KHÔNG CHẠY).
    # Nền = 4: ca 04 chỉ vào được 1 điều khiển TRONG màn (đặc tả đòi > 10) và 3 ca sau KHÔNG HỀ
    # CHẠY (Playwright bỏ phần đuôi tệp khi một ca hỏng). Đóng = 0. TỔNG số ca KHÔNG ghim ở đây:
    # nó được ĐỌC TẠI CHỖ từ chính tệp đặc tả (xem `G3`), nên thêm một ca vào spec không làm cổng
    # ĐỎ vì lý do giả; ca ĐẠT thiếu so với spec vẫn bị bắt riêng.
    "tang3-ban-phim": {"nen": 4, "dong": 0},

    # KHÔNG LÀN NÀO SỞ HỮU — C6 của G19: (schema_ok, route_ok). Nền (True, False): migration v9
    # ĐÃ gộp nhưng `app/truy_van.py` KHÔNG được tệp SẢN XUẤT nào import.
    "truy-van-C6": {"nen": (True, False), "dong": (True, True)},
}

# Làn sở hữu từng cổng — in ra ở mọi dòng để không ai đọc nhầm cổng nào của ai.
CHU_SO_HUU = {
    "sao-luu-fail-closed": "AG-02 (g21-ag02-backup)",
    "ro-credential-ngan": "AG-03 (g21-ag03-bimat)",
    "harness-gioi-han": "AG-04 (g21-ag04-gioihan)",
    "bo-g19-tong-hop": "AG-04 (g21-ag04-gioihan)",
    "cong-cay-sach": "AG-05 (g21-ag05-chotcay)",
    "git-tho": "AG-05 (g21-ag05-chotcay)",
    "tang3-ban-phim": "AG-06 (g21-ag06-e2e)",
    "truy-van-C6": "KHÔNG CÓ CHỦ SỞ HỮU — AG-00 xác nhận 16/10/2026",
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
    """(đạt?, câu giải thích). NỬA VỜI luôn ĐỎ; ở chế độ `gop` thì NỀN cũng ĐỎ."""
    che = CHE_DO if che_do is None else che_do
    pq = phan_quyet(ten_cong, do_duoc)
    if pq == "NUA_VOI":
        return False, ("NỬA VỜI — giá trị %r không phải nền %r cũng không phải đóng %r"
                       % (do_duoc, SO_DO[ten_cong]["nen"], SO_DO[ten_cong]["dong"]))
    if pq == "NEN" and che == "gop":
        return False, "chế độ GỘP: khoản nợ %r VẪN CÒN NGUYÊN" % (do_duoc,)
    return True, pq


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. SỔ ĐỐI CHỨNG DƯƠNG — CHỐT (b)
# ══════════════════════════════════════════════════════════════════════════════════════════════

DOI_CHUNG = {}


def _dc_am(nhom):
    DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})["am"] += 1


def _dc_duong(nhom):
    DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})["duong"] += 1


def nhom_thieu_duong(so=None):
    """Nhóm có ca ÂM mà THIẾU ca DƯƠNG. `Z1` tự phán HỎNG nếu danh sách này khác rỗng."""
    so = DOI_CHUNG if so is None else so
    return sorted(k for k, v in so.items() if v["am"] > 0 and v["duong"] == 0)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. TIỆN ÍCH
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _git(*tham_so, env=None, tho=False):
    """Chạy `git` trong `GOC_CAY`.

    `tho=True` giữ NGUYÊN môi trường thừa hưởng — dùng để ĐO chính lỗi `GIT_CONFIG_*`. Mặc định
    thì gỡ gia đình biến dị dạng, vì nếu không MỌI lệnh git thoát 128.
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

    `bo_bien` GỠ HẲN biến khỏi môi trường con. Cần tham số riêng chứ không thể chỉ truyền `env`
    thiếu khoá: `env` được `update()` ĐÈ LÊN `os.environ`, nên biến có ở cha mà không có ở `env`
    vẫn SỐNG SÓT sang con — đúng cái bẫy đã gây ĐỆ QUY VÔ HẠN ở bàn đo G20 (`QA_G20.md` §4.4).
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
        ra = ex.stdout or b""
        if isinstance(ra, bytes):
            ra = ra.decode("utf-8", "replace")
        return 124, "[QUÁ HẠN %ss] %s" % (giay, ra), time.time() - t0


def _doc(duong):
    with open(duong, encoding="utf-8") as f:
        return f.read()


def _ghi_log(ten, ma, ra):
    os.makedirs(LOG_DIR, exist_ok=True)
    duong = os.path.join(LOG_DIR, ten)
    with open(duong, "w", encoding="utf-8") as f:
        f.write("MA_THOAT=%s\n" % ma)
        f.write(ra)
    return duong


def _moi_truong_kho(data_dir):
    """Môi trường con cho MỘT nền KIỂM THỬ CÔ LẬP — khai kho bằng ĐÚNG đường của `cau_hinh`.

    G22 đổi hợp đồng: `migrate.py` TỪ CHỐI khi chưa khai kho đang chạy (`VIP_KHO_DANG_CHAY`).
    Bộ thử phải tự khai, và cách khai AN TOÀN là `cau_hinh.khai_kho_kiem_thu()`: hàm đó từ chối
    nếu thư mục dữ liệu không cô lập (chưa đặt `VIP_HUB_DATA`, hoặc trỏ vào cây repo / volume
    `/du-lieu`). Vì hàm ĐẶT biến môi trường, nó được gọi trong một khối có HOÀN NGUYÊN: tiến
    trình cha không giữ `VIP_KHO_DANG_CHAY`/`VIP_HUB_DATA` cho ca sau.

    Trả `dict` môi trường ĐẦY ĐỦ (thừa hưởng `os.environ`) + `VIP_HUB_DATA` + khai kho.
    """
    if GOC_APP not in sys.path:
        sys.path.insert(0, GOC_APP)
    import cau_hinh
    cu_hub = os.environ.get("VIP_HUB_DATA")
    cu_kho = os.environ.get("VIP_KHO_DANG_CHAY")
    cu_global = getattr(cau_hinh, "KHO_DANG_CHAY", None)
    os.environ["VIP_HUB_DATA"] = data_dir
    try:
        kho = cau_hinh.khai_kho_kiem_thu()
    finally:
        if cu_hub is None:
            os.environ.pop("VIP_HUB_DATA", None)
        else:
            os.environ["VIP_HUB_DATA"] = cu_hub
        if cu_kho is None:
            os.environ.pop("VIP_KHO_DANG_CHAY", None)
        else:
            os.environ["VIP_KHO_DANG_CHAY"] = cu_kho
        cau_hinh.KHO_DANG_CHAY = cu_global
    e = dict(os.environ)
    e["VIP_HUB_DATA"] = data_dir
    e["VIP_KHO_DANG_CHAY"] = kho
    return e


def _cay_ban():
    """Dòng `git status --porcelain` KHÔNG thuộc tệp được phép của AG-01 G21."""
    st = _git("status", "--porcelain=v1", "-uall").stdout
    ra = []
    for d in st.splitlines():
        if not d.strip():
            continue
        duong = d[3:].strip().strip('"')
        if " -> " in duong:
            duong = duong.split(" -> ", 1)[1]
        if duong not in TEP_DUOC_PHEP:
            ra.append(d)
    return ra


def van_tay_cay():
    """Vân tay CÂY ĐƯỢC THEO DÕI: `git ls-files -s`. KHÔNG băm cả cây làm việc.

    VÌ SAO: một lượt chạy GHI RA ĐĨA những tệp ĐƯỢC BỎ QUA (`app/du-lieu/khoa-noi-bo.key`,
    `thu_giao_dien/_bao-cao/**`, `thu_giao_dien/_ket-qua/**`), nên băm cả cây ĐỔI dù không một
    tệp sản phẩm nào bị sửa. Đo được trên `a3400a8`: `git status` RỖNG cả trước và sau, vân tay
    chỉ mục KHÔNG ĐỔI (`de394bac…`), nhưng băm cả cây đổi `d76198f3…` → `b98ecd76…`.
    """
    return hashlib.sha256(_git("ls-files", "-s").stdout.encode()).hexdigest()


def _cong_ranh():
    """Cổng do hệ điều hành cấp (`bind 127.0.0.1:0`) — không tranh cổng với làn khác."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = s.getsockname()[1]
    s.close()
    return cong


def _pw_browsers():
    rieng = os.environ.get("VIP_G21_PW_BROWSERS", "")
    ung_vien = ([("VIP_G21_PW_BROWSERS", rieng)] if rieng else
                [("chỉ định BAN_GIAO §1", PW_BROWSERS_CHI_DINH), ("trong repo", PW_BROWSERS_REPO)])
    for ten, duong in ung_vien:
        if duong and os.path.isdir(duong):
            for con in sorted(os.listdir(duong)):
                if con.startswith("chromium_headless_shell-") or con.startswith("chromium-"):
                    return duong, ten, con
    return None, None, None


def dem_playwright(ra):
    """Đếm kết quả Playwright: `(đạt, hỏng, bỏ_qua, KHÔNG_CHẠY)`.

    `did not run` là phán quyết RIÊNG, KHÔNG gộp vào bỏ qua và KHÔNG BAO GIỜ gộp vào đạt: khi
    một ca quá hạn, Playwright đóng tiến trình con và các ca còn lại trong cùng tệp KHÔNG CHẠY
    (`QA_G20.md` §4.2 `N-G20-03`). Với `workers: 1` thì cả phần đuôi tệp bị mất.
    """
    def _so(mau):
        m = re.findall(mau, ra)
        return int(m[-1]) if m else 0
    return (_so(r"(\d+) passed"), _so(r"(\d+) failed"),
            _so(r"(\d+) skipped"), _so(r"(\d+) did not run"))


def dem_diem_dung_trong_man(ra):
    m = re.findall(r"lượt Tab:\s*(\d+)\s*điểm dừng là điều khiển trong màn", ra)
    return int(m[-1]) if m else None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. BỘ CHẠY TẦNG 3 — khuôn `thu_giao_dien/chay.sh`, chỉ khác ĐƯỜNG nhị phân Chromium
# ══════════════════════════════════════════════════════════════════════════════════════════════

def do_tang_3(spec=None, giay=900):
    """Dựng máy chủ trên nền CÔ LẬP (bind 127.0.0.1, cổng OS cấp) rồi chạy Playwright.

    Trả `(mã_thoát, output, ghi_chú)`. `mã_thoát = None` nghĩa là CHƯA ĐO ĐƯỢC (thiếu nhị phân
    Chromium) — khi đó là BỎ QUA / lỗ hổng phạm vi, KHÔNG BAO GIỜ là ĐẠT.
    """
    pw, nguon, ban = _pw_browsers()
    if pw is None:
        return None, "", "không có thư mục nhị phân Chromium"
    if not os.path.isdir(os.path.join(GOC_CAY, "node_modules", "@playwright", "test")):
        return None, "", "thiếu node_modules/@playwright/test"

    nen = tempfile.mkdtemp(prefix="veh-g21-gd-")
    cong = _cong_ranh()
    # Nền CÔ LẬP + KHAI KHO bằng đường chính thức của `cau_hinh` (G22): thiếu khai thì
    # `migrate` TỪ CHỐI và tầng 3 chạy 0 ca — đó là lỗi THIẾT LẬP ĐO, không phải lỗi sản phẩm.
    env = _moi_truong_kho(nen)
    env["PLAYWRIGHT_BROWSERS_PATH"] = pw
    # CHỐT CỨNG: ÉP bind `127.0.0.1`, không chỉ "không đặt gì". `server.py` mặc định là
    # 127.0.0.1, nhưng một biến THỪA HƯỞNG từ phiên ngoài có thể mở cổng ra ngoài — điều bị CẤM.
    env["VIP_HUB_BIND"] = "127.0.0.1"
    pid = None
    try:
        for lenh, nhan in ((["python3", "app/migrate.py"], "migrate"),
                           (["python3", "app/khoi_tao.py"], "khoi_tao"),
                           (["python3", "thu_giao_dien/chuan_bi.py", "mk"], "chuan_bi-mk")):
            ma, ra, _ = _chay(lenh, env=env, giay=180)
            if ma != 0:
                return ma, "[%s hỏng] %s" % (nhan, ra[-1500:]), "nền không dựng được"

        # Log máy chủ ra TỆP, KHÔNG qua ống: mỗi lượt HTTP một dòng JSON, ống đầy (64KB) thì máy
        # chủ CHẶN ở lệnh ghi và mọi lượt sau treo tới hết thời hạn.
        log_sv = open(os.path.join(nen, "server.log"), "w")
        try:
            tt = subprocess.Popen(["python3", "app/server.py", str(cong)], cwd=GOC_CAY, env=env,
                                  stdout=log_sv, stderr=subprocess.STDOUT)
            pid = tt.pid
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
        ma, ra, _ = _chay(["python3", "thu_giao_dien/chuan_bi.py", "don", goc_url], env=env, giay=180)
        if ma != 0:
            return ma, "[chuan_bi-don hỏng] %s" % ra[-1500:], "nền không dựng được"

        lenh = ["npx", "playwright", "test"] + ([spec] if spec else [])
        ma, ra, _ = _chay(lenh, env=dict(env, VIP_GD_GOC=goc_url, VIP_GD_NEN=nen), giay=giay)
        return ma, ra, "nhị phân: %s (%s)" % (nguon, ban)
    finally:
        if pid:
            # Tắt theo ĐÚNG PID đã giữ lúc khởi động. KHÔNG BAO GIỜ theo mẫu tên tiến trình.
            try:
                tt.terminate()
                tt.wait(timeout=10)
            except Exception:
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
        shutil.rmtree(nen, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. PHÉP ĐO CỦA AG-02 — `khoi_phuc()` CÓ FAIL-CLOSED KHÔNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dung_nen_du_lieu(d):
    # `migrate.py` (G22) TỪ CHỐI khi chưa khai kho ⇒ nền cô lập phải khai bằng ĐÚNG đường của
    # `cau_hinh` (xem `_moi_truong_kho`), không phải bằng một dòng `export` rải rác.
    env = _moi_truong_kho(d)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for lenh in (["python3", "app/migrate.py"], ["python3", "app/khoi_tao.py"]):
        ma, ra, _ = _chay(lenh, env=env, giay=300)
        if ma != 0:
            return None, "dựng nền hỏng: %s → %s" % (lenh, ra[-300:])
    return os.path.join(d, "hub.db"), ""


def _chup_csdl(duong):
    """Mở ĐỌC-GHI (không `mode=ro`): CSDL WAL chỉ mở read-only được khi còn `-shm`, mà
    `khoi_phuc()` vừa XOÁ `-wal`/`-shm` — nên `mode=ro` sẽ báo lỗi mở tệp và phép đo thành rác.
    """
    try:
        kn = sqlite3.connect(duong)
        bang = [r[0] for r in kn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        tong = 0
        for b in bang:
            try:
                tong += kn.execute('SELECT COUNT(*) FROM "%s"' % b).fetchone()[0]
            except Exception:
                pass
        try:
            ic = kn.execute("PRAGMA integrity_check").fetchone()[0]
        except Exception as e:
            ic = "LOI:" + type(e).__name__
        kn.close()
        return {"so_bang": len(bang), "tong_dong": tong, "integrity": ic}
    except Exception as e:
        return {"so_bang": None, "tong_dong": None, "integrity": "LOI:" + type(e).__name__}


def _sao_luu_chuan(d):
    """Tạo bản sao lưu bằng CHÍNH `migrate.sao_luu()` (có `.sha256`). Trả `(rc, đường, output)`.

    VÌ SAO KHÔNG `shutil.copy2`: từ bản vá fail-closed G21/G22, `khoi_phuc()` BẮT BUỘC có dấu
    kiểm `<tệp>.sha256`; một bản `copy2` trần là "bản sao lưu không kiểm chứng được" và bị TỪ
    CHỐI — đúng thiết kế. Bản cũ dùng `copy2` làm đối chứng dương nên đo ra "tệp LÀNH bị từ
    chối"; đó là STALE của phép đo, không phải lỗi sản phẩm.
    """
    ma, ra, _ = _chay(
        ["python3", "-c",
         "import sys; sys.path.insert(0, %r); import migrate;"
         " print('BACKUP=' + migrate.sao_luu())" % GOC_APP],
        env=_moi_truong_kho(d), giay=300)
    duong = ""
    for dong in reversed(ra.splitlines()):
        if dong.startswith("BACKUP="):
            duong = dong.split("=", 1)[1].strip()
            break
    return ma, duong, ra


def do_sao_luu_fail_closed():
    """Trả `(số đầu vào ĐỘC HẠI được NHẬN, chi tiết, đối_chứng)`.

    BỐN đầu vào độc hại (ánh xạ K-1/K-2/K-5 của `G20_BACKUP_RESTORE.md` §5), đi qua ĐÚNG đường
    người trực dùng: `python3 app/migrate.py --rollback <tệp>`. "NHẬN" = mã thoát 0.

    ĐỐI CHỨNG DƯƠNG: bản sao lưu do CHÍNH `migrate.sao_luu()` tạo (có `.sha256`) phải được nhận
    VÀ dữ liệu phải nguyên vẹn — không có vế này thì "0/4 nhận" có thể chỉ là một `khoi_phuc()`
    hỏng sẵn. ĐỐI CHỨNG ÂM của chính bản vá: bản `copy2` KHÔNG dấu kiểm phải bị TỪ CHỐI mặc
    định, và đường thoát tường minh (`--toi-da-biet-chua-kiem-duoc`) phải dùng được.
    """
    goc = tempfile.mkdtemp(prefix="g21-saoluu-")
    chi_tiet = []
    try:
        db, loi = _dung_nen_du_lieu(goc)
        if db is None:
            return None, [("dựng nền", loi)], None
        nen_chup = _chup_csdl(db)
        with open(db, "rb") as f:
            toan = f.read()
        ma_sl, lanh, ra_sl = _sao_luu_chuan(goc)
        if ma_sl != 0 or not lanh:
            return None, [("tạo bản sao lưu chuẩn",
                           "rc=%s · %s" % (ma_sl, ra_sl[-400:]))], None

        doc_hai = [("rong-0-byte", b""),
                   ("cat-cut-40-phan-tram", toan[:int(len(toan) * 0.4)]),
                   ("byte-0-magic-hong", b"\x00" + toan[1:]),
                   ("khong-phai-sqlite-PGDMP", b"PGDMP\x00\x01\x00" + b"\x00" * 60000)]

        def _thu(duong_nguon, them=()):
            d = tempfile.mkdtemp(prefix="g21-saoluu-con-")
            try:
                dbc, _ = _dung_nen_du_lieu(d)
                if dbc is None:
                    return None, None, ""
                ma, ra, _ = _chay(["python3", "app/migrate.py", "--rollback", duong_nguon]
                                  + list(them), env=_moi_truong_kho(d), giay=300)
                return ma, _chup_csdl(dbc), ra
            finally:
                shutil.rmtree(d, ignore_errors=True)

        nhan = 0
        for ten, than in doc_hai:
            p = os.path.join(goc, ten + ".db")
            with open(p, "wb") as f:
                f.write(than)
            ma, sau, _ = _thu(p)
            if ma == 0:
                nhan += 1
            chi_tiet.append((ten, ma, sau, sau != nen_chup))
        ma_lanh, sau_lanh, _ = _thu(lanh)

        # VẾ "STALE" ĐƯỢC SỬA: bản `copy2` trần từng được coi là LÀNH. Nay nó là đầu vào KHÔNG
        # kiểm chứng được: phải bị TỪ CHỐI mặc định; đường thoát tường minh phải nhận nó.
        khong_dau = os.path.join(goc, "LANH-khong-dau-kiem.db")
        shutil.copy2(db, khong_dau)
        ma_kd, _, ra_kd = _thu(khong_dau)
        ma_esc, sau_esc, _ = _thu(khong_dau, them=("--toi-da-biet-chua-kiem-duoc",))
        doi_chung = {"rc": ma_lanh, "sau": sau_lanh, "nen": nen_chup,
                     "du_lieu_nguyen": (ma_lanh == 0 and sau_lanh == nen_chup),
                     "thieu_dau_kiem_rc": ma_kd,
                     "thieu_dau_kiem_noi": "dấu kiểm" in ra_kd,
                     "escape_rc": ma_esc,
                     "escape_du_lieu_nguyen": (ma_esc == 0 and sau_esc == nen_chup)}
        return nhan, chi_tiet, doi_chung
    finally:
        shutil.rmtree(goc, ignore_errors=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. PHÉP ĐO CỦA AG-03 — CREDENTIAL NGẮN CÓ RÒ KHÔNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

class _StubEcho401(http.server.BaseHTTPRequestHandler):
    """ECHO LẠI nguyên header + thân nhận được, kèm HTTP 401 (khuôn `G20_DA_HANG.md` §5).

    Vì sao phải ECHO: nếu stub không trả giá trị về thì không có gì để rò, và phép đo sẽ xanh
    vì stub — một cách xanh sai. Chỉ bind `127.0.0.1`, cổng do OS cấp.
    """
    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        than = self.rfile.read(n).decode("utf-8", "replace")
        ra = json.dumps({"header": {k: v for k, v in self.headers.items()}, "than": than},
                        ensure_ascii=False).encode()
        self.send_response(401)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(ra)))
        self.end_headers()
        self.wfile.write(ra)

    def log_message(self, *a):
        pass


def do_ro_credential_ngan():
    """Trả `(số tổ hợp RÒ, chi tiết, đối_chứng)`.

    NĂM tổ hợp = 2 tên × 2 độ dài + 1 lặp tên thứ hai. `DAI_TOI_THIEU_DE_CHE = 8` nên giá trị
    5 ký tự KHÔNG được tầng theo ĐỘ DÀI che — nó chỉ được che nếu tên trường nằm trong bảng tên.
    ĐỐI CHỨNG DƯƠNG nằm NGAY TRONG 5 tổ hợp: hai tổ hợp DÀI phải KHÔNG rò (chứng minh phép đo
    NHÌN THẤY được việc che), và `privateKey` + NGẮN phải KHÔNG rò (chứng minh tầng theo TÊN
    còn sống). Nếu cả 5 đều "không rò" thì phép đo mù, không phải hệ sạch.
    """
    sys.path.insert(0, GOC_APP)
    try:
        import http_jt
        import transport
    except Exception as e:
        return None, [("import", "không import được http_jt/transport: %s" % e)], None

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = s.getsockname()[1]
    s.close()
    srv = http.server.HTTPServer(("127.0.0.1", cong), _StubEcho401)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/nhan" % cong

    nguong = getattr(http_jt, "DAI_TOI_THIEU_DE_CHE", None)
    ngan, dai = "A1b2C", "K7x" + "Qw9z" * 8
    chi_tiet = []
    try:
        for nhan, ten, gt in (("jt_ngan", "privateKey", ngan),
                              ("gia_ngan", "x-mau-khoa-bi-mat", ngan),
                              ("gia_ngan_2", "maTaiKhoanGia", ngan),
                              ("jt_dai", "privateKey", dai),
                              ("gia_dai", "x-mau-khoa-bi-mat", dai)):
            kenh, ghi = [], ""
            try:
                http_jt.gui_form(url, {"Content-Type": http_jt.CONTENT_TYPE_FORM, ten: gt},
                                 {"truong": gt}, timeout=5.0)
                ghi = "KHÔNG NÉM (stub trả 401 mà lớp HTTP không ném)"
            except transport.LoiVinhVien as e:
                if gt in e.than_da_che.decode("utf-8", "replace"):
                    kenh.append("than_da_che")
                if gt in str(e.headers_da_che):
                    kenh.append("headers_da_che")
                if gt in str(e):
                    kenh.append("str(e)")
            except Exception as e:
                ghi = "loại lỗi khác: %s: %s" % (type(e).__name__, e)
            chi_tiet.append((nhan, ten, kenh, ghi))
    finally:
        srv.shutdown()
    so_ro = sum(1 for _, _, k, _ in chi_tiet if k)
    doi_chung = {"nguong": nguong,
                 "dai_khong_ro": all(not k for n, _, k, _ in chi_tiet if n.endswith("_dai")),
                 "jt_ngan_khong_ro": all(not k for n, _, k, _ in chi_tiet if n == "jt_ngan")}
    return so_ro, chi_tiet, doi_chung


def _so_tep_san_xuat_import_truy_van():
    """Đếm tệp SẢN XUẤT (không kể `app/thu/**`) import `app/truy_van.py`."""
    dem = []
    for goc, _, tep in os.walk(GOC_APP):
        if os.path.join(GOC_APP, "thu") in goc:
            continue
        for t in sorted(tep):
            if not t.endswith(".py"):
                continue
            duong = os.path.join(goc, t)
            if re.search(r"^\s*(import\s+truy_van\b|from\s+truy_van\b)", _doc(duong), re.M):
                dem.append(os.path.relpath(duong, GOC_CAY))
    return sorted(dem)


CONG_CAY_SACH = (
    ("thu_qa_g17.py",
     ["python3", "app/thu/thu_qa_g17.py", "A_Nen.test_a1_cay_sach_va_head"]),
    ("thu_qa_g18.py",
     ["python3", "app/thu/thu_qa_g18.py", "A_Nen.test_a1_cay_sach_theo_pham_vi_wave"]),
    ("thu_g20_baomat.py",
     ["python3", "app/thu/thu_g20_baomat.py", "A_Nen.test_a1_cay_sach_theo_pham_vi_wave"]),
)


def phan_loai_cong_cay_sach(ra, ma):
    """`XANH` | `DO_THAT` | `PHEP_DO_CHET`. Ba lớp, vì hai lớp là không đủ.

    ĐO ĐƯỢC TRÊN `a3400a8`: tên ca cây sạch của `thu_qa_g18.py` đã **ĐỔI** sau khi gộp G20
    (`test_a1_cay_sach_mien_tru_dung_hai_tep_ag01` → `test_a1_cay_sach_theo_pham_vi_wave`).
    Gọi tên cũ cho `Ran 1 test in 0.000s · FAILED (errors=1)` — **ERROR, không phải FAILURE**.
    Nếu bộ đếm chỉ nhìn "mã thoát != 0" thì một **phép đo CHẾT** bị đếm thành một **cổng ĐỎ vì cây
    bẩn** — và người đọc kết luận sai về sản phẩm. Đây đúng là lỗi của bàn đo G20
    (`docs/QA_G21.md` §5.2 `L-G20-C`).
    """
    if ma == 0:
        return "XANH"
    if "FAILED (errors=" in ra or "Ran 0 tests" in ra:
        return "PHEP_DO_CHET"
    if re.search(r"Ran \d+ tests?", ra) and ("FAILED (failures=" in ra or "FAILED (" in ra):
        return "DO_THAT"
    return "PHEP_DO_CHET"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7. A — NỀN VÀ AN TOÀN TUYỆT ĐỐI
# ══════════════════════════════════════════════════════════════════════════════════════════════

class A_Nen(unittest.TestCase):
    """Vi phạm bất kỳ mục nào ở đây ⇒ mọi số đo khác trở nên vô hiệu."""

    def test_a1_head_nam_tren_nen_g20(self):
        """HEAD phải NẰM TRÊN `a3400a8` — kiểm bằng TỔ TIÊN, không bằng `==`."""
        head = _git("rev-parse", "HEAD").stdout.strip()
        self.assertRegex(head, r"^[0-9a-f]{40}$", "không đọc được HEAD: %r" % head)
        r = _git("merge-base", "--is-ancestor", NEN_GOC, head)
        self.assertIn(r.returncode, (0, 1), "git merge-base lỗi thật: %r" % r.stderr[:200])
        # ĐỐI CHỨNG DƯƠNG: cùng phép kiểm với một commit KHÔNG phải tổ tiên phải trả 1 —
        # nếu không, "is-ancestor = 0" có thể chỉ là git luôn trả 0.
        r2 = _git("merge-base", "--is-ancestor", head, NEN_GOC)
        print("\n  [A1] HEAD=%s · nền %s là TỔ TIÊN=%s · chiều ngược lại=%s"
              % (head[:12], NEN_GOC[:7], r.returncode == 0, r2.returncode))
        self.assertEqual(r.returncode, 0,
                         "HEAD %s KHÔNG nằm trên nền %s ⇒ mọi số đo vô hiệu" % (head, NEN_GOC))

    def test_a2_khong_adapter_nao_mo_LIVE(self):
        """0 lớp adapter mở `CHO_PHEP_LIVE` — gọi hãng kể cả sandbox là BỊ CẤM."""
        mo = []
        for t in sorted(os.listdir(GOC_APP)):
            if not t.startswith("adapter") or not t.endswith(".py"):
                continue
            if re.search(r"CHO_PHEP_LIVE\s*=\s*True", _doc(os.path.join(GOC_APP, t))):
                mo.append(t)
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải BẮT ĐƯỢC một adapter giả có mở LIVE.
        gia = "CHO_PHEP_LIVE = True  # adapter giả để thử bộ dò"
        self.assertTrue(re.search(r"CHO_PHEP_LIVE\s*=\s*True", gia),
                        "bộ dò KHÔNG bắt được adapter giả ⇒ nó mù")
        _dc_am("live-khoa")
        self.assertEqual(mo, [], "adapter MỞ LIVE: %s" % mo)
        _dc_duong("live-khoa")
        print("\n  [A2] adapter quét=%d · mở LIVE=%d · bộ dò bắt được adapter giả"
              % (len([t for t in os.listdir(GOC_APP) if t.startswith("adapter") and t.endswith(".py")]),
                 len(mo)))

    def test_a3_csdl_nghiep_vu_van_la_sqlite_D8(self):
        """D-8: 0 tệp `app/*.py` import driver PostgreSQL."""
        mau = re.compile(r"^\s*(import|from)\s+(psycopg2?|asyncpg|pg8000)\b", re.M)
        co = []
        for t in sorted(os.listdir(GOC_APP)):
            if t.endswith(".py") and mau.search(_doc(os.path.join(GOC_APP, t))):
                co.append(t)
        tong = len([t for t in os.listdir(GOC_APP) if t.endswith(".py")])
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải bắt được một tệp giả CÓ import psycopg2.
        self.assertTrue(mau.search("import psycopg2\n"), "bộ dò mù với `import psycopg2`")
        self.assertTrue(mau.search("from asyncpg import x\n"), "bộ dò mù với `from asyncpg`")
        _dc_am("sqlite-D8")
        self.assertEqual(co, [], "tệp app/*.py import driver PostgreSQL: %s" % co)
        _dc_duong("sqlite-D8")
        print("\n  [A3] %d tệp app/*.py quét · import driver PostgreSQL = %d" % (tong, len(co)))

    def test_a4_cum_5432_khong_bi_dung_toi(self):
        """Cụm PostgreSQL `:5432` CHỈ được ĐỌC bằng `lsof`, không bao giờ kết nối (giữ D-8)."""
        self.assertIn("5432", _doc(os.path.abspath(__file__)),
                      "bộ kiểm không nhắc `:5432` ⇒ phép kiểm vô nghĩa")
        try:
            r = subprocess.run(["lsof", "-nP", "-iTCP:5432", "-sTCP:LISTEN"],
                               capture_output=True, text=True, timeout=60)
        except Exception as e:
            self.skipTest("CHƯA ĐO: không chạy được `lsof` trong phiên này (%s)" % e)
        if r.returncode not in (0, 1):
            self.skipTest("CHƯA ĐO: `lsof` bị chặn trong phiên này (rc=%s · %r)"
                          % (r.returncode, r.stderr[:120]))
        dong = [d for d in r.stdout.splitlines() if d.strip()]
        # Bộ kiểm TỰ SOI: chính tệp này KHÔNG được import driver PostgreSQL. KHÔNG dùng
        # `assertNotIn("psycopg", than)` — chữ đó CÓ trong mẫu dò của `A3`, nên phép kiểm đó
        # sẽ đỏ vì chính mẫu dò (một cách đỏ giả). Kiểm bằng ĐÚNG mẫu import.
        than = _doc(os.path.abspath(__file__))
        self.assertIsNone(re.search(r"^\s*(import|from)\s+(psycopg2?|asyncpg|pg8000)\b", than, re.M),
                          "bộ kiểm import driver PostgreSQL ⇒ vi phạm D-8")
        _dc_am("cum-5432")
        _dc_duong("cum-5432")
        print("\n  [A4] cụm :5432 đang nghe: %d dòng lsof (CHỈ đọc, không kết nối)"
              % max(len(dong) - 1, 0))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 8. SÁU CỔNG CỦA NĂM LÀN + C4 KHÔNG CHỦ SỞ HỮU
# ══════════════════════════════════════════════════════════════════════════════════════════════

class G1_CaySach(unittest.TestCase):
    """AG-05 — cổng cây sạch của wave trước không được ĐỎ vì tệp HỢP LỆ của làn khác."""

    def test_g1_cong_cay_sach_wave_truoc(self):
        ket = []
        for ten, lenh in CONG_CAY_SACH:
            ma, ra, _ = _chay(lenh, giay=300)
            loai = phan_loai_cong_cay_sach(ra, ma)
            ket.append((ten, ma, loai))
            print("       %s → mã thoát %s · %s" % (ten, ma, loai))
        # PHÉP ĐO CHẾT phải làm cổng HỎNG NGAY, không được đếm là "cây bẩn": nếu không, một tên
        # ca bị đổi sẽ được đọc thành một khoản nợ sản phẩm (bài học `L-G20-C`).
        chet = [t for t, _, loai in ket if loai == "PHEP_DO_CHET"]
        self.assertEqual(chet, [], "PHÉP ĐO CHẾT (tên ca không tồn tại / 0 ca chạy): %s" % chet)
        xanh = sum(1 for _, _, loai in ket if loai == "XANH")
        con_do = len(CONG_CAY_SACH) - xanh
        dat, vi = dat_cong("cong-cay-sach", con_do)
        _dc_am("cong-cay-sach")

        # ĐỐI CHỨNG DƯƠNG + ÂM — dùng DÒNG PORCELAIN TỔNG HỢP, không đọc trạng thái git thật.
        # BẢN CŨ (STALE) đòi hai tệp QA phải đang là "?? …" trên cây. Sau khi gộp, chúng là tệp
        # ĐÃ THEO DÕI và cây SẠCH, nên `q17._cay_ban()` rỗng → phép đo tự tố cáo sai. Bất biến
        # đúng: bộ lọc của MỖI cổng miễn trừ vùng thử/tài liệu và KHÔNG miễn trừ tệp SẢN PHẨM.
        sys.path.insert(0, GOC_THU)
        import thu_qa_g17 as q17  # noqa: E402
        import thu_qa_g18 as q18  # noqa: E402
        import thu_g20_baomat as qb  # noqa: E402
        gia_lanh = ["?? %s" % t for t in TEP_DUOC_PHEP]
        gia_ban = ["?? app/webhook.py"]
        for ten, loc, mau in (
                ("g17", lambda d: q17._loc_cay_ban(d, q17._mau_chot()), q17._mau_chot()),
                ("g18", lambda d: q18._loc_cay_ban(d, q18._mau_chot()), q18._mau_chot()),
                ("g20_baomat", lambda d: qb._loc_cay_ban(d, qb._mau_chot()), qb._mau_chot())):
            self.assertTrue(mau, "%s: vùng miễn trừ RỖNG ⇒ cổng không tha gì (hướng an toàn)" % ten)
            self.assertEqual(loc(gia_lanh), [],
                             "%s: tệp thử/tài liệu HỢP LỆ bị coi là cây bẩn: %s"
                             % (ten, loc(gia_lanh)))
            self.assertEqual(loc(gia_ban), gia_ban,
                             "%s: tệp SẢN PHẨM bị miễn trừ ⇒ cổng mù với cây bẩn thật" % ten)
        # Và cơ chế miễn trừ của chính cổng g18 phải nhận ra tệp của CHÍNH NÓ (không phải "tha
        # tất"): đây là vế dương hẹp của cùng bộ lọc.
        self.assertTrue(any(q18._la_tep_ag01("?? %s" % t) for t in q18.TEP_CUA_AG01_G18),
                        "cổng g18 không nhận ra tệp của chính nó ⇒ cổng hỏng sẵn, không phải nợ")
        _dc_duong("cong-cay-sach")
        print("\n  [G1] cổng cây sạch wave trước: %d/%d XANH · còn ĐỎ=%d"
              " · chủ sở hữu=%s · phán quyết=%s"
              % (xanh, len(CONG_CAY_SACH), con_do, CHU_SO_HUU["cong-cay-sach"], vi))
        self.assertTrue(dat, "CỔNG `cong-cay-sach` ĐỎ: %s" % vi)


class G2_GitTho(unittest.TestCase):
    """AG-05 — `git` dưới môi trường `GIT_CONFIG_*` dị dạng (N-G18-00)."""

    def test_g2_git_voi_moi_truong_nguyen_ban(self):
        """Môi trường git phải được CHUẨN HOÁ **KÈM CẢNH BÁO**, và KHÔNG nuốt lỗi thật.

        BẢN CŨ (STALE) đo `git rev-parse HEAD` với môi trường THỪA HƯỞNG rồi ghim mã thoát 128
        vào cổng sản phẩm. Đo lại: `GIT_CONFIG_COUNT=2` thiếu `GIT_CONFIG_KEY_*` là lỗi MÔI
        TRƯỜNG của MÁY (docs/OWNER_ACTIONS §F; docs/G22_A1_GIT.md §1.1a), không phải mã sản
        phẩm; `chay_tat_ca.sh` đã tự gỡ từ G18. Bất biến đúng, ba vế:
          (1) môi trường DỊ DẠNG ⇒ bộ chuẩn hoá DÙNG CHUNG (`thu_g21_chotcay.env_git`) gỡ cả
              gia đình biến + CẢNH BÁO ra stderr;
          (2) môi trường HỢP LỆ ⇒ KHÔNG được gỡ (gỡ là nuốt một cấu hình thật);
          (3) sau chuẩn hoá, lỗi THẬT vẫn phải NỔI LÊN, kèm stderr nguyên văn.
        """
        sys.path.insert(0, GOC_THU)
        import thu_g21_chotcay as chotcay  # noqa: E402

        nguyen_van = dict(os.environ)
        ban = chotcay.soi_gia_dinh_git(nguyen_van)
        tho = subprocess.run(["git", "-C", GOC_CAY, "rev-parse", "HEAD"],
                             capture_output=True, text=True, env=nguyen_van)
        e_sach = {k: v for k, v in nguyen_van.items() if not k.startswith("GIT_CONFIG")}
        e_sach["GIT_CONFIG_COUNT"] = "0"
        sach = subprocess.run(["git", "-C", GOC_CAY, "rev-parse", "HEAD"],
                              capture_output=True, text=True, env=e_sach)
        da_chuan = chotcay._git("rev-parse", "HEAD")
        self.assertEqual(sach.returncode, 0,
                         "git với môi trường SẠCH vẫn hỏng ⇒ lỗi THẬT: %r" % sach.stderr[:200])
        self.assertEqual(da_chuan.returncode, 0,
                         "git sau chuẩn hoá vẫn hỏng ⇒ bộ chuẩn hoá không cứu được: %r"
                         % da_chuan.stderr[:200])
        _dc_am("git-tho")
        # ĐỐI CHỨNG ÂM: môi trường DỊ DẠNG ⇒ git NGUYÊN VĂN phải hỏng. Nếu nó "vẫn chạy" thì mô
        # tả N-G18-00 sai, và phép đo dưới đây không chứng minh được gì.
        if ban["di_dang"]:
            self.assertNotEqual(tho.returncode, 0,
                                "môi trường dị dạng mà git nguyên văn VẪN chạy ⇒ mô tả sai")
        else:
            self.assertEqual(tho.returncode, 0,
                             "môi trường HỢP LỆ mà git nguyên văn hỏng ⇒ lỗi THẬT: %r"
                             % tho.stderr[:200])
        # ĐỐI CHỨNG DƯƠNG: môi trường HỢP LỆ không được bị gỡ. `COUNT=1` + đủ KEY/VALUE là cấu
        # hình CÓ THẬT; xoá nó là nuốt một lỗi thật (luật (b) của `thu_g21_chotcay`).
        hop_le = dict(e_sach, GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="user.name",
                      GIT_CONFIG_VALUE_0="g21-do")
        ban_hl = chotcay.soi_gia_dinh_git(hop_le)
        self.assertFalse(ban_hl["di_dang"], "bộ soi báo oan môi trường HỢP LỆ")
        e_hl = chotcay.env_git(hop_le, im_lang=True)
        self.assertEqual(e_hl.get("GIT_CONFIG_KEY_0"), "user.name",
                         "bộ chuẩn hoá GỠ mất cấu hình HỢP LỆ ⇒ nuốt lỗi thật")
        self.assertEqual(e_hl.get("GIT_CONFIG_COUNT"), "1")
        # ĐỐI CHỨNG ÂM của luật (c): lỗi THẬT sau chuẩn hoá vẫn nổi lên, kèm stderr.
        tam = tempfile.mkdtemp(prefix="veh-g21-khong-repo-")
        try:
            r_ngoai = chotcay._git("rev-parse", "HEAD", goc=tam)
        finally:
            shutil.rmtree(tam, ignore_errors=True)
        self.assertNotEqual(r_ngoai.returncode, 0,
                            "git ngoài cây git LẠI thành công ⇒ bộ đo nuốt lỗi thật")
        self.assertTrue((r_ngoai.stderr or "").strip(),
                        "lỗi THẬT nhưng KHÔNG có stderr để đối chiếu")
        _dc_duong("git-tho")
        dat, vi = dat_cong("git-tho", da_chuan.returncode)
        print("\n  [G2] môi trường máy: COUNT=%s · KEY_*=%d · VALUE_*=%d · dị dạng=%s"
              " · git nguyên văn=%s · git đã chuẩn hoá=%s · git môi trường sạch=%s"
              " · chủ sở hữu=%s"
              % (ban["count"], ban["so_khoa"], ban["so_gia_tri"], ban["di_dang"],
                 tho.returncode, da_chuan.returncode, sach.returncode,
                 CHU_SO_HUU["git-tho"]))
        if ban["di_dang"]:
            print("       [N-G18-00] %s" % ban["ly_do"])
            print("       Đây là MÔI TRƯỜNG của máy, KHÔNG phải cây hỏng — docs/OWNER_ACTIONS §F")
        self.assertTrue(dat, "CỔNG `git-tho` ĐỎ: %s" % vi)


class G3_Tang3BanPhim(unittest.TestCase):
    """AG-06 — bàn phím TRONG màn, tầng 3 Chromium thật."""

    def test_g3_tang_3_ban_phim_trong_man(self):
        # TỔNG số ca ĐỌC TẠI CHỖ từ chính tệp đặc tả — KHÔNG ghim "7" của lượt trước. Spec đã
        # thành 8 ca; một con số cứng sẽ biến việc THÊM CA (làm đúng) thành cổng ĐỎ giả.
        spec = os.path.join(GOC_CAY, "thu_giao_dien", SPEC_BAN_PHIM)
        so_ca_spec = len(re.findall(r"^test\(", _doc(spec), re.M))
        self.assertGreater(so_ca_spec, 0,
                           "không đọc được ca nào trong %s ⇒ phép đo vô nghĩa" % SPEC_BAN_PHIM)
        ma, ra, ghi = do_tang_3(spec=SPEC_BAN_PHIM)
        if ma is None:
            _ghi_log("tang3_ban_phim_CHUA_DO.txt", ma, ra)
            self.fail("CHƯA ĐO ĐƯỢC: %s" % ghi)
        _ghi_log("tang3_ban_phim.txt", ma, ra)
        dat_, hong, bo, khong_chay = dem_playwright(ra)
        diem = dem_diem_dung_trong_man(ra)
        self.assertTrue(dat_ > 0 or hong > 0,
                        "bộ đếm không đọc ra ca nào ⇒ output lạ:\n%s" % ra[-1500:])
        _dc_am("tang3-ban-phim")
        # ĐỐI CHỨNG DƯƠNG: bộ đếm phải đọc ra CẢ BỐN số từ output tổng hợp ĐÃ BIẾT, và phép
        # đọc điểm dừng phải đọc ra số từ dòng đo tổng hợp.
        self.assertEqual(dem_playwright("1 failed · 3 did not run · 47 passed"), (47, 1, 0, 3),
                         "bộ đếm Playwright mù")
        self.assertEqual(dem_diem_dung_trong_man("[đo] 30 lượt Tab: 7 điểm dừng là điều khiển trong màn"), 7)
        # BẤT BIẾN: số ca ĐẠT phải bằng ĐÚNG số ca spec khai — thiếu ca là PHÉP ĐO CHẾT, không
        # phải đạt. Và ca 04 phải thật sự vào được > 10 điều khiển TRONG màn (đặc tả G21/AG-06).
        self.assertEqual(dat_, so_ca_spec,
                         "spec khai %d ca nhưng Playwright chỉ báo %d ĐẠT ⇒ mất ca"
                         % (so_ca_spec, dat_))
        self.assertEqual(ma, 0, "Playwright báo đủ %d ca đạt nhưng mã thoát %s" % (so_ca_spec, ma))
        self.assertIsNotNone(diem, "không đọc được số điểm dừng TRONG màn ⇒ ca 04 không in số")
        self.assertGreater(diem, 10,
                           "ca 04 chỉ vào được %s điều khiển TRONG màn (đặc tả đòi > 10)" % diem)
        _dc_duong("tang3-ban-phim")
        dat, vi = dat_cong("tang3-ban-phim", hong + khong_chay)
        print("\n  [G3] tầng 3 bàn phím: mã thoát=%s · (đạt, hỏng, KHÔNG CHẠY)=(%d, %d, %d)"
              " · bỏ qua=%d · spec khai %d ca"
              % (ma, dat_, hong, khong_chay, bo, so_ca_spec))
        print("       ca 04 vào được %s điều khiển TRONG màn (đặc tả đòi > 10) · chủ sở hữu=%s"
              % (diem, CHU_SO_HUU["tang3-ban-phim"]))
        self.assertTrue(dat, "CỔNG `tang3-ban-phim` ĐỎ: %s" % vi)

    def test_g3b_dem_playwright_khong_gop_did_not_run(self):
        """`did not run` KHÔNG được gộp vào đạt — nhiệt kế phải có vạch đó."""
        dat_, hong, bo, khong_chay = dem_playwright("4 passed · 1 did not run")
        self.assertEqual((dat_, khong_chay), (4, 1))
        _dc_am("dem-playwright")
        self.assertEqual(dem_playwright("51 passed (2.2m)"), (51, 0, 0, 0),
                         "bộ đếm không đọc được khuôn sạch ⇒ nó chỉ đọc được khuôn hỏng")
        _dc_duong("dem-playwright")
        print("\n  [G3b] `did not run` là phán quyết RIÊNG, không gộp vào đạt")


class G4_SaoLuu(unittest.TestCase):
    """AG-02 — `khoi_phuc()` phải FAIL-CLOSED."""

    def test_g4_sao_luu_fail_closed(self):
        nhan, chi_tiet, doi_chung = do_sao_luu_fail_closed()
        if nhan is None:
            self.fail("CHƯA ĐO ĐƯỢC: %s" % (chi_tiet,))
        _dc_am("sao-luu-fail-closed")
        # ĐỐI CHỨNG DƯƠNG BẮT BUỘC: bản sao lưu do CHÍNH `sao_luu()` tạo phải được NHẬN và dữ
        # liệu nguyên vẹn. Bản cũ dùng `shutil.copy2` trần làm "LÀNH"; bản vá fail-closed
        # G21/G22 cố ý TỪ CHỐI bản không có `.sha256` ⇒ đó là STALE của phép đo, không phải lỗi.
        self.assertIsNotNone(doi_chung, "thiếu đối chứng dương")
        self.assertEqual(doi_chung["rc"], 0,
                         "bản sao lưu CHUẨN (có `.sha256`) bị TỪ CHỐI ⇒ phép đo vô nghĩa")
        self.assertTrue(doi_chung["du_lieu_nguyen"],
                        "bản sao lưu CHUẨN khôi phục ra dữ liệu KHÁC nền sạch ⇒ phép đo vô nghĩa")
        # ĐỐI CHỨNG ÂM của chính bản vá: bản `copy2` KHÔNG dấu kiểm bị TỪ CHỐI mặc định; đường
        # thoát TƯỜNG MINH (`--toi-da-biet-chua-kiem-duoc`) phải nhận nó và dữ liệu nguyên vẹn.
        self.assertNotEqual(doi_chung["thieu_dau_kiem_rc"], 0,
                            "bản sao lưu KHÔNG có `.sha256` lại được nhận ⇒ chốt dấu kiểm hỏng")
        self.assertTrue(doi_chung["thieu_dau_kiem_noi"],
                        "bị từ chối nhưng KHÔNG nêu thiếu dấu kiểm ⇒ sai lý do")
        self.assertEqual(doi_chung["escape_rc"], 0,
                         "đường thoát `--toi-da-biet-chua-kiem-duoc` không dùng được")
        self.assertTrue(doi_chung["escape_du_lieu_nguyen"],
                        "đường thoát nhận bản sao lưu nhưng dữ liệu KHÔNG nguyên vẹn")
        _dc_duong("sao-luu-fail-closed")
        dat, vi = dat_cong("sao-luu-fail-closed", nhan)
        print("\n  [G4] đầu vào ĐỘC HẠI được NHẬN (rc=0): %d/%d · chủ sở hữu=%s"
              % (nhan, len(chi_tiet), CHU_SO_HUU["sao-luu-fail-closed"]))
        for ten, ma, sau, hong in chi_tiet:
            print("       %-24s rc=%-4s CSDL sau=%s%s" % (ten, ma, sau, "   ← HỎNG" if hong else ""))
        print("       ĐỐI CHỨNG DƯƠNG: bản `sao_luu()` rc=%s · dữ liệu nguyên vẹn=%s · nền sạch=%s"
              % (doi_chung["rc"], doi_chung["du_lieu_nguyen"], doi_chung["nen"]))
        print("       ĐỐI CHỨNG ÂM: `copy2` không dấu kiểm bị TỪ CHỐI rc=%s · đường thoát rc=%s"
              " (dữ liệu nguyên vẹn=%s)"
              % (doi_chung["thieu_dau_kiem_rc"], doi_chung["escape_rc"],
                 doi_chung["escape_du_lieu_nguyen"]))
        self.assertTrue(dat, "CỔNG `sao-luu-fail-closed` ĐỎ: %s" % vi)


class G5_CredentialNgan(unittest.TestCase):
    """AG-03 — credential NGẮN của hãng KHÁC J&T không được rò."""

    def test_g5_ro_credential_ngan(self):
        so_ro, chi_tiet, doi_chung = do_ro_credential_ngan()
        if so_ro is None:
            self.skipTest("CHƯA ĐO: %s" % chi_tiet)
        _dc_am("ro-credential-ngan")
        # ĐỐI CHỨNG DƯƠNG: hai tổ hợp DÀI phải KHÔNG rò (tầng theo ĐỘ DÀI còn sống) và
        # `privateKey`+NGẮN phải KHÔNG rò (tầng theo TÊN còn sống). Thiếu vế này thì "0 rò"
        # có thể chỉ là bộ dò mù.
        self.assertTrue(doi_chung["dai_khong_ro"],
                        "tổ hợp DÀI cũng rò ⇒ tầng che theo ĐỘ DÀI đã chết, phép đo không đọc được gì")
        self.assertTrue(doi_chung["jt_ngan_khong_ro"],
                        "`privateKey`+NGẮN rò ⇒ tầng che theo TÊN đã chết, phép đo không đọc được gì")
        _dc_duong("ro-credential-ngan")
        dat, vi = dat_cong("ro-credential-ngan", so_ro)
        print("\n  [G5] ngưỡng che theo độ dài `DAI_TOI_THIEU_DE_CHE`=%s · tổ hợp RÒ=%d/5 · chủ sở hữu=%s"
              % (doi_chung["nguong"], so_ro, CHU_SO_HUU["ro-credential-ngan"]))
        for nhan, ten, kenh, ghi in chi_tiet:
            print("       %-12s %-22s → %s%s" % (nhan, ten,
                                                 ("RÒ qua %s" % kenh) if kenh else "KHÔNG RÒ", ghi))
        self.assertTrue(dat, "CỔNG `ro-credential-ngan` ĐỎ: %s" % vi)


class G6_HarnessGioiHan(unittest.TestCase):
    """AG-04 — harness giới hạn tần suất phải chạy HẾT và XANH."""

    def test_g6_harness_gioi_han_tan_suat(self):
        ma, ra, _ = _chay(["sh", "trien_khai/g18/chay_harness.sh"], giay=1800)
        _ghi_log("harness_g18.txt", ma, ra)
        # ĐỐI CHỨNG DƯƠNG: output phải có dòng tổng kết thật (đã CHẠY), không phải "không chạy
        # được" — nếu không, mã thoát khác 0 có thể chỉ là harness không khởi động.
        co_chay = bool(re.search(r"\d+\s*/\s*\d+\s*ca", ra)) or ("G18-05" in ra)
        _dc_am("harness-gioi-han")
        self.assertTrue(co_chay, "harness không in dòng tổng kết ⇒ nó không chạy được:\n%s" % ra[-1200:])
        self.assertIn("127.0.0.1", ra, "harness không khai bind loopback ⇒ phép đo không an toàn")
        _dc_duong("harness-gioi-han")
        dat, vi = dat_cong("harness-gioi-han", ma)
        print("\n  [G6] `sh trien_khai/g18/chay_harness.sh` mã thoát=%s · chủ sở hữu=%s · phán quyết=%s"
              % (ma, CHU_SO_HUU["harness-gioi-han"], vi))
        if ma != 0:
            for d in ra.splitlines():
                if "G18-05" in d or "✗" in d:
                    print("       %s" % d.strip()[:150])
        self.assertTrue(dat, "CỔNG `harness-gioi-han` ĐỎ: %s" % vi)


class G7_BoG19TongHop(unittest.TestCase):
    """AG-04 — phải có ÍT NHẤT một bộ G19-tổng-hợp CHẠY THẬT."""

    def test_g7_co_bo_g19_tong_hop_chay_duoc(self):
        ung_vien = sorted(t for t in os.listdir(GOC_THU) if re.match(r"thu_qa_g19.*\.py$", t))
        _dc_am("bo-g19-tong-hop")
        # ĐỐI CHỨNG DƯƠNG: bộ đếm `Ran N tests` phải đọc ra số từ output tổng hợp ĐÃ BIẾT.
        self.assertEqual(int(re.findall(r"Ran (\d+) tests?", "Ran 7 tests in 0.1s")[-1]), 7,
                         "bộ đếm `Ran N tests` mù")
        _dc_duong("bo-g19-tong-hop")
        if not ung_vien:
            self.fail("không còn tệp `thu_qa_g19*.py` nào ⇒ phép đo vô nghĩa, KHÔNG phải ĐẠT")
        chi_tiet = []
        for t in ung_vien:
            ma, ra, _ = _chay(["python3", os.path.join("app", "thu", t)], giay=1800)
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
        print("\n  [G7] bộ `thu_qa_g19*.py` CHẠY THẬT: %d/%d · chủ sở hữu=%s · phán quyết=%s"
              % (chay, len(ung_vien), CHU_SO_HUU["bo-g19-tong-hop"], vi))
        for t, ma, n, bq, nc in chi_tiet:
            print("       %s → mã thoát %s · %d ca · %d BỎ QUA · %d CHẠY THẬT"
                  % (t, ma, n, bq, nc))
        self.assertTrue(dat, "CỔNG `bo-g19-tong-hop` ĐỎ: %s" % vi)


class G8_TruyVanC6(unittest.TestCase):
    """C4 — KHÔNG LÀN NÀO SỞ HỮU. Cổng này tồn tại để không ai đọc nhầm "năm làn xanh = G21 đạt"."""

    def test_g8_route_truy_van_va_migration_v9(self):
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
        # ĐỐI CHỨNG DƯƠNG: bộ dò import phải bắt được chính bộ thử `thu_truy_van.py` — nếu nó mù
        # thì "0 tệp sản xuất" không chứng minh được gì.
        than = _doc(os.path.join(GOC_THU, "thu_truy_van.py"))
        self.assertTrue(re.search(r"^\s*import\s+truy_van\b", than, re.M),
                        "bộ dò mẫu không khớp cả tệp thử CÓ import ⇒ mẫu sai")
        _dc_duong("truy-van-C6")
        print("\n  [G8] PHIEN_BAN_SCHEMA=%s · nang_len_v9=%s · tệp SẢN XUẤT import truy_van=%d · "
              "chủ sở hữu=%s" % (csdl.PHIEN_BAN_SCHEMA, hasattr(migrate, "nang_len_v9"),
                                 len(nhap), CHU_SO_HUU["truy-van-C6"]))
        self.assertTrue(dat, "CỔNG `truy-van-C6` ĐỎ: %s" % vi)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 9. T — CHỐT (a): TỰ KIỂM BỘ ĐO CHẠY TRONG **TIẾN TRÌNH CON**
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Vì sao TIẾN TRÌNH CON chứ không phải gọi hàm tại chỗ: một ca tự kiểm gọi thẳng hàm trong CÙNG
# tiến trình vẫn có thể "xanh" nhờ trạng thái đã bị chính bộ thử làm bẩn. Chạy bằng `subprocess`
# thì tiến trình mới HOÀN TOÀN, và cái được kiểm là ĐÚNG thứ người chấm sẽ chạy.

CA_TU_KIEM_HONG = "T_TuKiem.test_z9_ca_co_y_hong"
CA_TU_KIEM_DAT = "T_TuKiem.test_z8_ca_co_y_dat"
TEP_NAY = os.path.relpath(os.path.abspath(__file__), GOC_CAY)


class T_TuKiem(unittest.TestCase):

    def _chay_ca(self, ten_ca):
        ma, ra, _ = _chay(["python3", TEP_NAY, ten_ca], giay=600,
                          env={"VIP_G21_DO_THU": "1"}, bo_bien=("VIP_G21_DAY_DU",))
        return ma, ra

    def test_t1_luat_phan_tu_choi_bon_kieu_xanh_gia(self):
        """Luật phán phải TỪ CHỐI xanh giả. Kiểm bằng SỔ TỔNG HỢP, không đụng `SO_DO` thật."""
        gia = {"gia-cong": {"nen": 0, "dong": 2}}
        def _pq(v):
            ky = gia["gia-cong"]
            if v == ky["dong"]:
                return "DONG"
            if v == ky["nen"]:
                return "NEN"
            return "NUA_VOI"
        self.assertEqual(_pq(1), "NUA_VOI", "giá trị nửa vời 1/2 phải là NUA_VOI")
        self.assertEqual(_pq(3), "NUA_VOI", "giá trị vượt trần phải là NUA_VOI")
        self.assertEqual(_pq(0), "NEN")
        self.assertEqual(_pq(2), "DONG")
        # Và luật THẬT của tệp này phải theo đúng khuôn đó.
        self.assertEqual(phan_quyet("cong-cay-sach", 1), "NUA_VOI")
        self.assertEqual(phan_quyet("cong-cay-sach", 3), "NEN")
        self.assertEqual(phan_quyet("cong-cay-sach", 0), "DONG")
        self.assertEqual(phan_quyet("git-tho", 128), "NEN")
        self.assertEqual(phan_quyet("git-tho", 0), "DONG")
        self.assertEqual(phan_quyet("tang3-ban-phim", 4), "NEN")
        self.assertEqual(phan_quyet("tang3-ban-phim", 0), "DONG")
        self.assertEqual(phan_quyet("tang3-ban-phim", 1), "NUA_VOI")
        print("\n  [T1] luật phán TỪ CHỐI giá trị nửa vời ở cả cổng số lẫn cổng bộ ba")

    def test_t2_tu_kiem_bang_TIEN_TRINH_CON(self):
        """Ca CỐ Ý HỎNG phải cho HỎNG; ca CỐ Ý ĐẠT phải cho ĐẠT. Đây là chốt (a)."""
        ma, ra = self._chay_ca(CA_TU_KIEM_HONG)
        _dc_am("tu-kiem-con")
        self.assertEqual(ma, 1, "ca cố ý hỏng mà tiến trình con thoát %s:\n%s" % (ma, ra[-800:]))
        self.assertIn("FAILED", ra, "ca cố ý hỏng mà output không có FAILED")
        # ĐỐI CHỨNG DƯƠNG: cùng tệp, cùng đường chạy, ca ĐẠT phải thoát 0 và có OK.
        ma2, ra2 = self._chay_ca(CA_TU_KIEM_DAT)
        self.assertEqual(ma2, 0, "ca cố ý đạt mà tiến trình con thoát %s:\n%s" % (ma2, ra2[-800:]))
        self.assertIn("OK", ra2, "ca cố ý đạt mà output không có OK")
        self.assertIn("Ran 1 test", ra2, "không đọc được số ca ⇒ luật phán không đáng tin")
        _dc_duong("tu-kiem-con")
        print("\n  [T2] tiến trình con: ca cố ý hỏng → thoát 1 + FAILED · ca cố ý đạt → thoát 0 + OK")

    def test_t5_go_duoc_bien_moi_truong_khoi_tien_trinh_con(self):
        """`bo_bien` phải GỠ HẲN biến — cơ chế này từng KHÔNG có tác dụng và gây đệ quy vô hạn."""
        ma, ra, _ = _chay(["python3", "-c",
                           "import os;print('CO=%s' % ('VIP_G21_DAY_DU' in os.environ))"],
                          env={"VIP_G21_DAY_DU": "1", "VIP_G21_DO_THU": "1"})
        self.assertIn("CO=True", ra, "không đặt được biến ⇒ phép đo vô nghĩa")
        ma2, ra2, _ = _chay(["python3", "-c",
                             "import os;print('CO=%s' % ('VIP_G21_DAY_DU' in os.environ))"],
                            env={"VIP_G21_DAY_DU": "1", "VIP_G21_DO_THU": "1"},
                            bo_bien=("VIP_G21_DAY_DU",))
        _dc_am("go-bien")
        self.assertIn("CO=False", ra2, "`bo_bien` KHÔNG gỡ được biến ⇒ nguy cơ đệ quy vô hạn")
        self.assertEqual(ma2, 0)
        _dc_duong("go-bien")
        print("\n  [T5] `bo_bien` gỡ được biến (CO=False) · không gỡ thì biến còn (CO=True)")

    def test_t4_gia_tri_NUA_VOI_luon_la_DO(self):
        """Cùng một giá trị nửa vời phải ĐỎ ở CẢ HAI chế độ; giá trị ĐÓNG phải qua ở cả hai."""
        for che in ("nen", "gop"):
            for ten, nua_voi in (("cong-cay-sach", 1), ("git-tho", 7), ("bo-g19-tong-hop", 5)):
                dat, vi = dat_cong(ten, nua_voi, che_do=che)
                self.assertFalse(dat, "%s=%r ở chế độ %s phải ĐỎ" % (ten, nua_voi, che))
                self.assertIn("NỬA VỜI", vi)
            for ten, dong in (("cong-cay-sach", 0), ("git-tho", 0), ("bo-g19-tong-hop", 1),
                              ("sao-luu-fail-closed", 0), ("ro-credential-ngan", 0)):
                dat, _ = dat_cong(ten, dong, che_do=che)
                self.assertTrue(dat, "giá trị ĐÓNG %s=%r phải qua ở chế độ %s" % (ten, dong, che))
        print("\n  [T4] giá trị nửa vời bị phán NỬA VỜI = ĐỎ ở CẢ HAI chế độ · giá trị ĐÓNG đều qua")

    def test_z8_ca_co_y_dat(self):
        """Mồi ĐẠT cho `T2`. Không chạy trong làn thường."""
        if not os.environ.get("VIP_G21_DO_THU"):
            self.skipTest("mồi cho T2 — chỉ chạy trong tiến trình con của T2")
        self.assertEqual(1 + 1, 2)

    def test_z9_ca_co_y_hong(self):
        """Mồi HỎNG cho `T2`. Không chạy trong làn thường."""
        if not os.environ.get("VIP_G21_DO_THU"):
            self.skipTest("mồi cho T2 — chỉ chạy trong tiến trình con của T2")
        self.assertEqual(1, 2, "CA CỐ Ý HỎNG — chỉ dùng làm mồi cho T2")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 10. Z — CHỐT CHẶN
# ══════════════════════════════════════════════════════════════════════════════════════════════

VAN_TAY_TRUOC = None


class Z_ChotChan(unittest.TestCase):

    def test_z1_moi_ca_phu_dinh_deu_co_doi_chung_duong(self):
        """CHỐT (b). In sổ ra, và TỰ PHÁN HỎNG nếu một nhóm phủ định thiếu ca dương."""
        for k in sorted(DOI_CHUNG):
            print("  [Z1] %-24s âm=%d dương=%d" % (k, DOI_CHUNG[k]["am"], DOI_CHUNG[k]["duong"]))
        thieu = nhom_thieu_duong()
        # TỰ KIỂM: một nhóm âm CỐ Ý không có dương PHẢI bị bắt; nhóm đủ hai chiều KHÔNG bị báo oan.
        self.assertEqual(nhom_thieu_duong({"nhom-gia-thieu-duong": {"am": 1, "duong": 0}}),
                         ["nhom-gia-thieu-duong"], "Z1 KHÔNG bắt được nhóm thiếu đối chứng dương")
        self.assertEqual(nhom_thieu_duong({"nhom-gia-du": {"am": 1, "duong": 1}}), [],
                         "Z1 báo oan nhóm đã đủ hai chiều")
        self.assertEqual(thieu, [], "THIẾU ĐỐI CHỨNG DƯƠNG cho: %s" % thieu)
        print("  [Z1] %d nhóm · 0 nhóm thiếu đối chứng dương · Z1 tự bắt được nhóm giả"
              % len(DOI_CHUNG))

    def test_z2_cay_khong_doi_trong_luot_do(self):
        """Vân tay cây TRƯỚC = SAU, và ngoài các tệp được phép thì `git status` phải RỖNG."""
        la = _cay_ban()
        van_tay = van_tay_cay()
        self.assertRegex(van_tay, r"^[0-9a-f]{64}$")
        _dc_am("cay-sach")
        self.assertEqual(la, [], "cây có thay đổi NGOÀI các tệp được phép: %s" % la)
        # ĐỐI CHỨNG DƯƠNG: bộ lọc phải BẮT ĐƯỢC một dòng KHÔNG thuộc các tệp của tôi — nếu nó
        # miễn trừ tất thì khẳng định "ngoài các tệp = RỖNG" là rỗng nghĩa.
        gia = ["?? app/webhook.py", "?? docs/QA_G21.md"]
        loc = [d for d in gia if d[3:].strip().strip('"') not in TEP_DUOC_PHEP]
        self.assertEqual(loc, ["?? app/webhook.py"],
                         "bộ lọc miễn trừ NHẦM cả tệp sản phẩm ⇒ Z2 không đo được gì")
        _dc_duong("cay-sach")
        if VAN_TAY_TRUOC is not None:
            self.assertEqual(van_tay, VAN_TAY_TRUOC,
                             "vân tay cây ĐỔI trong lượt đo ⇒ có gì đó ghi vào cây ĐƯỢC THEO DÕI")
        print("\n  [Z2] vân tay cây (được theo dõi) = %s" % van_tay)
        print("       git status ngoài các tệp được phép: %s" % (la or "RỖNG"))
        print("       vân tay TRƯỚC=%s · SAU=%s · không đổi=%s"
              % (str(VAN_TAY_TRUOC)[:16], van_tay[:16], van_tay == VAN_TAY_TRUOC))

    def test_z3_bo_kiem_tu_soi_khong_goi_ra_ngoai(self):
        """Bộ kiểm TỰ SOI: không URL nào ngoài `127.0.0.1`, và ÉP bind loopback cho máy chủ."""
        than = _doc(os.path.abspath(__file__))
        ngoai = re.findall(r"https?://(?!127\.0\.0\.1)[A-Za-z0-9._-]+", than)
        _dc_am("khong-ra-ngoai")
        self.assertEqual(ngoai, [], "bộ kiểm có URL ra ngoài: %s" % sorted(set(ngoai)))
        self.assertIn('env["VIP_HUB_BIND"] = "127.0.0.1"', than,
                      "bộ kiểm KHÔNG ép bind 127.0.0.1 ⇒ cổng có thể mở ra ngoài")
        self.assertIn("127.0.0.1", than, "bộ kiểm không nhắc 127.0.0.1 ⇒ phép soi vô nghĩa")
        _dc_duong("khong-ra-ngoai")
        print("\n  [Z3] 0 URL ngoài 127.0.0.1 · ÉP bind `VIP_HUB_BIND=127.0.0.1` cho máy chủ tầng 3")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 11. X — ĐỐI CHIẾU CHÉO (không bắt buộc: chỉ chạy khi bộ kiểm G20 có mặt)
# ══════════════════════════════════════════════════════════════════════════════════════════════

class X_DoiChieuG20(unittest.TestCase):
    """Bộ kiểm G20 là bộ ĐỘC LẬP thứ hai. Nếu nó có mặt thì chạy, và ghi lại mã thoát THẬT.

    ĐỌC KỸ: bộ kiểm G20 có một LỖI CỦA CHÍNH NÓ (`docs/QA_G21.md` §4.1 `L-G20-A`): đối chứng
    dương của cổng C3 ghim `HEAD == 148ecd3`, nên trên cây đã gộp nó ĐỎ vì lý do GIẢ. Vì thế
    mã thoát của nó KHÔNG được dùng làm phán quyết ở đây — chỉ ghi lại để đối chiếu.
    """

    def test_x1_doi_chieu_bo_kiem_g20(self):
        duong = os.path.join(GOC_CAY, TEP_G20_TAM)
        if not os.path.exists(duong):
            self.skipTest("CHƯA ĐO: không có `%s` trong cây (không bắt buộc)" % TEP_G20_TAM)
        ma, ra, _ = _chay(["python3", TEP_G20_TAM], giay=1800)
        _ghi_log("doi_chieu_g20_mac_dinh.txt", ma, ra)
        m = re.findall(r"Ran (\d+) tests.*?\n(OK|FAILED[^\n]*)", ra, re.S)
        _dc_am("doi-chieu-g20")
        self.assertTrue(m, "không đọc được dòng tổng kết của bộ kiểm G20 ⇒ nó không chạy:\n%s"
                        % ra[-1000:])
        _dc_duong("doi-chieu-g20")
        print("\n  [X1] `python3 %s` (làn mặc định) mã thoát=%s · %s"
              % (TEP_G20_TAM, ma, m[-1]))
        print("       LƯU Ý: đối chứng dương của C3 trong bộ G20 ghim HEAD nền ⇒ ĐỎ GIẢ trên cây gộp")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 12. H — HỒI QUY TOÀN PHẦN (chỉ làn đầy đủ)
# ══════════════════════════════════════════════════════════════════════════════════════════════

# Nhóm hỏng ĐÃ CÓ TÊN. Một bộ đỏ chỉ được THA khi rơi vào một nhóm ở đây; bộ đỏ VÔ DANH ⇒
# HỎNG SẢN PHẨM ⇒ `H1` ĐỎ.
#
# ĐO ĐƯỢC, không suy đoán: khi cây chỉ có các tệp được phép của làn QA G21, hồi quy chung cho
# **3** bộ đỏ thuộc khoản nợ "cây sạch" (`thu_qa_g17.py`, `thu_qa_g18.py`, `thu_g20_baomat.py`).
# Cả ba nằm CÙNG một khoản nợ `N-G19-03` (`N-G21-05`) nên chúng được PHÂN LOẠI, không được tha:
# cổng riêng của khoản nợ đó là `G1`, và `G1` ĐỎ ở chế độ `gop` cho tới khi **cả ba** chuyển XANH.
# (Trên cây đã gộp hiện tại cả ba đã XANH — nhóm này là lưới an toàn cho cây chưa gộp.)
NHOM_HONG_DA_BIET = {
    "N-G19-03/N-G21-05 cổng cây sạch wave trước (3 bản sao)":
        lambda t: t in ("thu_qa_g17.py", "thu_qa_g18.py", "thu_g20_baomat.py"),
    "N-G18-01 ca 04 tầng 3 (khoản nợ bàn phím)": lambda t: t == "thu_qa_g18.py",
    "N-G21-01 ca E3 sao lưu phụ thuộc ĐỒNG HỒ TƯỜNG (docs/QA_G21.md §5.1)":
        lambda t: t == "thu_g20_saoluu.py",
}


def _phan_loai_hong(ten_bo):
    return [k for k, f in NHOM_HONG_DA_BIET.items() if f(ten_bo)]


class H_HoiQuy(unittest.TestCase):

    def test_h1_hoi_quy_toan_phan(self):
        if not DAY_DU:
            self.skipTest("CHƯA ĐO: làn đầy đủ (VIP_G21_DAY_DU=1)")
        ma, ra, giay = _chay(["sh", "app/thu/chay_tat_ca.sh"], giay=3600,
                             bo_bien=("VIP_G21_DAY_DU",))
        _ghi_log("hoi_quy.log", ma, ra)
        m = re.findall(r"python:\s+(\d+) ca · (\d+) bộ chạy thật", ra)
        self.assertTrue(m, "không đọc được dòng tổng kết hồi quy:\n%s" % ra[-2000:])
        so_ca, so_bo = int(m[-1][0]), int(m[-1][1])
        hong = sorted(re.findall(r"✗ (\S+\.py)", ra))
        _dc_am("hoi-quy")
        # ĐỐI CHỨNG DƯƠNG: phép đọc phải đọc ra được số từ output TỔNG HỢP ĐÃ BIẾT.
        self.assertEqual(re.findall(r"python:\s+(\d+) ca · (\d+) bộ chạy thật",
                                    "python:   1870 ca · 51 bộ chạy thật")[-1], ("1870", "51"))
        _dc_duong("hoi-quy")
        phan_loai = {}
        for ten in hong:
            nhom = _phan_loai_hong(ten)
            ma2, _, _ = _chay(["python3", os.path.join("app", "thu", ten)], giay=1800,
                              bo_bien=("VIP_G21_DAY_DU",))
            phan_loai[ten] = (nhom, ma2)
            self.assertTrue(nhom, "BỘ ĐỎ KHÔNG RƠI VÀO NHÓM NÀO = HỎNG SẢN PHẨM: %s" % ten)
        print("\n  [H1] `sh app/thu/chay_tat_ca.sh` mã thoát=%s · %d ca · %d bộ · %.0f giây"
              % (ma, so_ca, so_bo, giay))
        print("       bộ hỏng: %s" % (hong or "không bộ nào"))
        for ten, (nhom, ma2) in sorted(phan_loai.items()):
            print("       ↻ %s chạy lại một mình → thoát %s · nhóm=%s"
                  % (ten, ma2, " + ".join(nhom)))
        self.assertGreaterEqual(so_ca, 1870, "số ca TEO so với nền (1870) — cổng chống teo ca")
        self.assertGreaterEqual(so_bo, 51, "số bộ TEO so với nền (51)")


# ══════════════════════════════════════════════════════════════════════════════════════════════

def _in_dau():
    print("═" * 96)
    print("  AG-01 (G21) — BỘ KIỂM ĐỘC LẬP · nền `integration/g20 @ a3400a8`")
    print("  chế độ=%s%s" % (CHE_DO, "  (ô 'nen' cũng ĐỎ: nghiệm thu bản ĐÃ GỘP)"
                                   if CHE_DO == "gop" else "  (đo nợ trên nền)"))
    print("  làn=%s" % ("ĐẦY ĐỦ (hồi quy toàn phần)" if DAY_DU else "MẶC ĐỊNH"))
    print("  NĂM LÀN: AG-02 sao lưu · AG-03 bí mật · AG-04 giới hạn · AG-05 chốt cây · AG-06 E2E")
    print("  C4 (`truy-van-C6`) KHÔNG CÓ CHỦ SỞ HỮU ⇒ nghiệm thu G21 vẫn FAILED nếu C4 chưa đóng")
    print("  PHẠM VI: chỉ 127.0.0.1 · adapter MOCK · cổng hãng KHOÁ · cụm PostgreSQL :5432 KHÔNG đụng")
    print("═" * 96)


if __name__ == "__main__":
    VAN_TAY_TRUOC = van_tay_cay()
    _in_dau()
    print("  vân tay cây TRƯỚC lượt đo = %s" % VAN_TAY_TRUOC)
    unittest.main(verbosity=2)
