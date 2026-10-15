#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WAVE G19 — BỘ KIỂM CỦA AG-01 (QA/VERIFIER): SÁU CỔNG ĐÓNG NỢ VẬN HÀNH.

====== NGƯỜI VIẾT LÀ NGƯỜI KIỂM, KHÔNG PHẢI NGƯỜI SỬA ======
Tệp này KHÔNG sửa một dòng mã sản phẩm nào. Nó ĐO. Tìm thấy lỗi thì ghi lại và báo cáo
(`docs/QA_G19.md`), không tự vá.

====== NỀN ĐO ======
`integration/g18` @ `6e61fc1e1f1f9a6d64931464e4f40ed887192ab5` — NỀN ĐÓNG BĂNG.
`main` (`de740dc`) KHÔNG chứa G13–G19 nên không được dùng.

====== SÁU CỔNG, VÀ VÌ SAO CHÚNG CÓ RĂNG ======
Mỗi cổng là MỘT phép đo trả về SỐ, không phải một câu khẳng định. Cùng một hàm đo phục vụ
HAI chiều kỳ vọng:

  * **nợ MỞ** — cây nền đóng băng: phép đo phải ra ĐÚNG con số nợ đã đo được (§1 `QA_G19.md`).
  * **nợ ĐÓNG** — cây đã gộp G19: cùng phép đo đó phải ra con số của trạng thái đã vá.

Nhờ vậy "cổng có răng" không phải một lời hứa: **cùng một phép đo cho ĐỎ ở lượt nền và phải
cho XANH ở lượt gộp**. Nhóm `J` còn lái cả hai chiều bằng ĐỘT BIẾN trên cây sao chép.

Chế độ được chọn như sau (in ra ở dòng đầu, không im lặng):
  * `VIP_G19_CHO_GOP=1` → ép **nợ ĐÓNG**;  `VIP_G19_CHO_GOP=0` → ép **nợ MỞ**;
  * không đặt → TỰ SUY từ một dấu hiệu GỘP ĐO ĐƯỢC: `csdl.PHIEN_BAN_SCHEMA >= 9`
    (AG-00 đưa `truy_van.py` + `DDL_G12Q` vào migration v9 — đó là mốc gộp của wave).
    Suy sai thì cổng ĐỎ và in lời nhắc đặt `VIP_G19_CHO_GOP`; `J6` chứng minh điều đó.

====== HAI CHỐT CHẶN BẮT BUỘC ======
(a) **Ca TỰ KIỂM BỘ ĐO chạy trong TIẾN TRÌNH CON** — `J1` (một ca cố ý hỏng) và `J3`–`J6`
    (bốn phép đột biến, mỗi phép chạy driver trong tiến trình con trên cây sao chép). Không có
    nhóm `J` thì mọi dòng "✓ … ca" của tệp này KHÔNG chứng minh gì.
(b) **ĐỐI CHỨNG ĐƯỜNG cho MỌI ca phủ định** — sổ `DOI_CHUNG`; `Z1` tự phán HỎNG nếu một nhóm
    có ca ÂM mà không có ca DƯƠNG.

====== PHẠM VI VÀ ĐIỀU BỊ CẤM ======
Không gọi API hãng kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP): mọi phép đo lớp HTTP chỉ
dùng stub `127.0.0.1` **cổng 0**. Không push/deploy/tunnel, không mở cổng ra ngoài. Không mở
`CHO_PHEP_LIVE`. Không credentials thật, không `.env`. Vẫn SQLite (`D-8`) — cụm PostgreSQL `:5432`
(đang giữ `vip_customs*`) **CHẶN CỨNG**. Không đoán mã trạng thái chưa được hãng xác minh
(`D-4`) — mã chưa chốt nghĩa phải `NEEDS_REVIEW`, và `D3` canh đúng điều đó. Giữ chốt `D-9`
(`city`/`area` chặn cứng ngoài mock).

====== CÁCH CHẠY ======
    python3 app/thu/thu_qa_g19.py                 # làn MẶC ĐỊNH (nhanh, không Chromium)
    VIP_G19_DAY_DU=1 python3 app/thu/thu_qa_g19.py  # + hồi quy toàn phần + tầng 3 Chromium
"""
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True          # không để lại __pycache__ trong cây ĐANG ĐO

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)
THU_MUC_THU = os.path.dirname(os.path.abspath(__file__))

# Cây để ĐỌC tệp và cây để IMPORT. Tách ra để phép ĐỘT BIẾN ở nhóm J lái được cùng một hàm đo
# trên một CÂY SAO CHÉP mà không đụng cây thật.
GOC_DO = os.environ.get("VIP_G19_GOC", GOC_CAY)
GOC_APP_DO = os.environ.get("VIP_G19_APP", GOC_APP)

HEAD_GHIM = os.environ.get("VIP_G19_HEAD", "6e61fc1e1f1f9a6d64931464e4f40ed887192ab5").strip()
DAY_DU = os.environ.get("VIP_G19_DAY_DU", "") == "1"

TEP_CUA_AG01_G19 = ("app/thu/thu_qa_g19.py", "docs/QA_G19.md")

# Cổng "cây sạch" của HAI wave TRƯỚC: mỗi bộ chỉ miễn trừ tệp của chính nó, nên tệp AG-01 G19
# (thứ đề bài cho phép tôi tạo) làm chúng ĐỎ. Đây là `N-G18-03` tái diễn — xem `N-G19-03`.
CONG_CAY_SACH_WAVE_TRUOC = {
    "thu_qa_g17.py": {"test_a1_cay_sach_va_head"},
    "thu_qa_g18.py": {"test_a1_cay_sach_mien_tru_dung_hai_tep_ag01"},
}

# Ca CHẬP CHỜN đã được wave TRƯỚC ghi thành lỗi có tên (`N-G18-01`: *"tầng 3 CHẬP CHỜN — 1/5
# lượt đỏ"*, `docs/QA_G18.md` §2.2). KHÔNG được tin danh sách này bằng lời: khi gặp, bộ kiểm
# CHẠY LẠI ca đó một mình (`do_hoi_quy`) và chỉ tha nếu lượt chạy lại ĐẠT. Chạy lại mà vẫn hỏng
# thì nó là HỎNG SẢN PHẨM, không phải chập chờn.
CA_CHAP_CHON_WAVE_TRUOC = {
    "thu_qa_g18.py": {"test_b1_tang_3_chay_duoc_va_khong_co_ca_hong"},
}

# Nhị phân Chromium: `docs/BAN_GIAO.md` §1 chỉ định nguồn này cho worktree không có
# `node_modules/playwright-core/.local-browsers`, và CẤM dùng cache hệ thống của dự án khác.
PW_BROWSERS_CHI_DINH = os.path.expanduser(
    "~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers")

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0a. DỮ KIỆN ĐỐI CHIẾU — 21 mã trạng thái Viettel Post (hãng CÔNG BỐ, không phải suy đoán)
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Nguồn: `https://partner2.viettelpost.vn/document/webhook`, mục "Bảng danh sách trạng thái".
# Bản chép lại đã đối chiếu nằm ở repo tham chiếu CỤC BỘ (không gọi mạng):
#   ~/code/vip-viettelpost-g12/app/providers/viettel_post/status_mapper.py
#   sha256 = d1d84496f51afe5685596bee06dd3dc2d9d8ef2c8d80abfcf4c1877b0a81416a
# Danh sách này là DỮ KIỆN của hãng. Nó KHÔNG phải phán đoán của bộ kiểm: bộ kiểm chỉ hỏi
# "hệ thống có biết mã này không", KHÔNG hỏi "mã này phải ánh xạ sang trạng thái nào" — việc
# ánh xạ là quyết định của làn AG-04.
MA_VTP_CHINH_THUC = ("101", "102", "103", "104", "107", "200", "201", "202", "300", "400",
                     "500", "501", "503", "504", "505", "506", "507", "508", "509", "515", "550")
# Sáu mã hãng công bố nhưng CỐ Ý không ánh xạ (không có trạng thái chuẩn tương đương rõ nghĩa).
MA_VTP_CO_Y_None = ("102", "202", "503", "505", "508", "550")
# Mã nhập nhằng thứ hai của VTP (bảng nói là trạng thái cuối, đoạn "Lưu ý" thì không).
MA_VTP_NHAP_NHANG = ("104",)
MA_VTP_HOAN_TAT = ("giao_thanh_cong", "hoan_hang")
TEP_THAM_CHIEU_VTP = os.path.expanduser(
    "~/code/vip-viettelpost-g12/app/providers/viettel_post/status_mapper.py")

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0b. SỔ ĐỐI CHỨNG DƯƠNG + TIỆN ÍCH ĐO
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


def _doc(duong_tuong_doi):
    """Đọc một tệp trong cây ĐANG ĐO (`GOC_DO`) — để đột biến đọc được cây sao chép."""
    with open(os.path.join(GOC_DO, duong_tuong_doi), encoding="utf-8") as f:
        return f.read()


def _git(*tham_so, env=None):
    """Git với môi trường ĐÃ GỠ `GIT_CONFIG_*` (N-G18-00/N-G17-00 còn nguyên trên máy này)."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    e["GIT_CONFIG_COUNT"] = "0"
    e.update(env or {})
    return subprocess.run(["git"] + list(tham_so), capture_output=True, text=True,
                          cwd=GOC_CAY, env=e, timeout=60)


def _la_tep_ag01(dong_porcelain):
    duong = dong_porcelain[3:].strip().strip('"')
    if " -> " in duong:
        duong = duong.split(" -> ", 1)[1]
    return duong in TEP_CUA_AG01_G19


def van_tay_cay(env=None):
    """Vân tay cây: `git ls-files -s` + `git status` (miễn trừ đúng 2 tệp AG-01 G19).

    Vì sao miễn trừ: chính tệp này và tài liệu của nó là thứ DUY NHẤT được phép mới. Mọi thay
    đổi khác của cây phải làm vân tay đổi, và `Z2` phán HỎNG nếu nó đổi giữa lượt đo.
    """
    ls = _git("ls-files", "-s", env=env)
    st = _git("status", "--porcelain=v1", env=env)
    con = [d for d in st.stdout.splitlines() if d.strip() and not _la_tep_ag01(d)]
    return hashlib.sha256((ls.stdout + "\n" + "\n".join(con)).encode()).hexdigest()


VAN_TAY_LUC_NAN = van_tay_cay()


def _chay(lenh, env=None, giay=1800, cwd=None):
    """Chạy một lệnh THẬT trong tiến trình con. Trả (mã thoát, output, số giây)."""
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e.update(env or {})
    t0 = time.time()
    r = subprocess.run(lenh, capture_output=True, text=True, env=e, timeout=giay,
                       cwd=cwd or GOC_CAY)
    return r.returncode, (r.stdout or "") + (r.stderr or ""), time.time() - t0


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


def _so_skip(ra):
    m = re.findall(r"skipped=(\d+)", ra)
    return int(m[-1]) if m else 0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0c. CHỐT AN TOÀN — bộ thử TỪ CHỐI CHẠY nếu thiếu
# ══════════════════════════════════════════════════════════════════════════════════════════════
_TAM_CSDL = os.environ.get("VIP_G19_DATA") or tempfile.mkdtemp(prefix="veh-g19-qa-")
os.environ["VIP_HUB_DATA"] = _TAM_CSDL
LOG_DIR = os.environ.get("VIP_G19_LOG") or os.path.join(tempfile.gettempdir(), "veh_g19_ag01_qa_log")

sys.path.append(GOC_APP_DO)             # `append`, KHÔNG `insert(0)`: xem ghi chú G18

import adapter                                                          # noqa: E402
import cau_hinh                                                         # noqa: E402


def kiem_chot_an_toan(mt=None):
    """Trả LÝ DO TỪ CHỐI CHẠY, hoặc `None` nếu đủ ba chốt an toàn."""
    loi = []
    duong = os.path.abspath(cau_hinh.THU_MUC_DU_LIEU)
    tam = os.path.abspath(tempfile.gettempdir())
    if duong.startswith(os.path.abspath(GOC_CAY) + os.sep) or not duong.startswith(tam + os.sep):
        loi.append("nền CSDL KHÔNG nằm trong thư mục tạm (hoặc nằm trong cây repo): %s" % duong)
    mo = sorted(m for m, lop in adapter._DANG_KY.items() if getattr(lop, "CHO_PHEP_LIVE", False))
    if mo:
        loi.append("có adapter MỞ LIVE: %s" % mo)
    if mt is not None and mt.get("dia_chi") != "127.0.0.1":
        loi.append("máy chủ KHÔNG bind loopback: %r" % (mt.get("dia_chi"),))
    return "; ".join(loi) or None


_LY_DO_TU_CHOI = kiem_chot_an_toan()
if _LY_DO_TU_CHOI:
    sys.stderr.write("TỪ CHỐI CHẠY — thiếu chốt an toàn: " + _LY_DO_TU_CHOI + "\n")
    raise SystemExit(3)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0d. CHẾ ĐỘ KỲ VỌNG — nợ MỞ (nền đóng băng) hay nợ ĐÓNG (đã gộp G19)
# ══════════════════════════════════════════════════════════════════════════════════════════════
DRIVER_AG00 = r'''
import json, os, re, sys
APP = os.environ["VIP_G19_APP"]
GOC = os.environ["VIP_G19_GOC"]
sys.path.insert(0, APP)
import csdl
sv = open(os.path.join(GOC, "app", "server.py"), encoding="utf-8").read()
mg = open(os.path.join(GOC, "app", "migrate.py"), encoding="utf-8").read()
tuyen = re.findall(r'"(/api/v2/[^"]*truy[^"]*)"', sv)
print("KETQUA=" + json.dumps({
    "phien_ban_schema": csdl.PHIEN_BAN_SCHEMA,
    "co_nang_len_v9": "nang_len_v9" in mg,
    "so_tham_chieu_module_truy_van": len(re.findall(r"(?<![\w.])truy_van\.", sv)),
    "tuyen_truy_van": tuyen,
}))
'''


def _do_ag00(cay=None):
    ma, ra = _chay_con(DRIVER_AG00, goc_cay=cay)
    m = re.search(r"^KETQUA=(\{.*\})$", ra, re.M)
    if not m:
        raise AssertionError("driver AG-00 không in KETQUA (mã thoát %s): %s" % (ma, ra[-400:]))
    return json.loads(m.group(1))


def _chon_che_do():
    """Trả (nho_dong: bool, ly_do: str). Gọi ở CUỐI tệp — nó cần `_chay_con` đã được định nghĩa."""
    ep = os.environ.get("VIP_G19_CHO_GOP", "").strip()
    if ep == "1":
        return True, "ép bằng VIP_G19_CHO_GOP=1"
    if ep == "0":
        return False, "ép bằng VIP_G19_CHO_GOP=0"
    try:
        pb = _do_ag00()["phien_ban_schema"]
    except Exception as e:                                     # noqa: BLE001
        return False, "KHÔNG đọc được PHIEN_BAN_SCHEMA (%s) ⇒ mặc định nợ MỞ" % e
    if pb >= 9:
        return True, "tự suy: csdl.PHIEN_BAN_SCHEMA=%d ≥ 9 (AG-00 đã gộp migration v9)" % pb
    return False, "tự suy: csdl.PHIEN_BAN_SCHEMA=%d < 9 (chưa thấy mốc gộp G19)" % pb


def _nhac():
    return ("  [chế độ] nợ %s — %s. Nếu chế độ SUY SAI (ví dụ v9 chưa gộp mà các khoản khác đã"
            " gộp), đặt lại bằng VIP_G19_CHO_GOP=0 hoặc =1."
            % ("ĐÓNG" if NHO_DONG else "MỞ", LY_DO_CHE_DO))


def _ky_vong(cua_mo, cua_dong):
    """Chọn kỳ vọng theo chế độ. Trả (ky_vong, nhan, doi_chung)."""
    if NHO_DONG:
        return cua_dong, "nợ ĐÓNG", cua_mo
    return cua_mo, "nợ MỞ", cua_dong


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0e. NỀN CSDL TẠM cho các driver con (AG-02/AG-03 cần kho DÙNG CHUNG sau khi vá)
# ══════════════════════════════════════════════════════════════════════════════════════════════
_NEN_CSDL = {}


def nen_csdl():
    """Dựng schema một lần trong thư mục tạm. Dùng CHUNG cho mọi tiến trình con của một phép đo."""
    if _NEN_CSDL:
        return _NEN_CSDL
    sys.path.insert(0, GOC_APP_DO)
    import csdl
    import migrate
    import quyen
    csdl.mo()
    migrate.chay(im_lang=True)
    quyen.seed()
    _NEN_CSDL.update({"thu_muc": _TAM_CSDL})
    return _NEN_CSDL


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0f. DRIVER TRONG TIẾN TRÌNH CON — nền tảng của HAI CHỐT CHẶN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _chay_con(nguon, goc_cay=None, goc_app=None, giay=600, bien_them=None):
    """Chạy một đoạn mã trong TIẾN TRÌNH CON. Trả (mã thoát, output).

    `goc_cay`/`goc_app` trỏ vào CÂY SAO CHÉP khi đo đột biến: driver phải nạp mã từ cây đột
    biến, không phải từ cây thật — nếu không, phép đột biến đo chính cây thật và luôn xanh.
    """
    f = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    f.write(nguon)
    f.close()
    env = dict(os.environ)
    env["GIT_CONFIG_COUNT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["VIP_G19_GOC"] = goc_cay or GOC_DO
    env["VIP_G19_APP"] = goc_app or (os.path.join(goc_cay, "app") if goc_cay else GOC_APP_DO)
    env["VIP_HUB_DATA"] = _TAM_CSDL
    env["PYTHONPATH"] = os.pathsep.join([env["VIP_G19_APP"], THU_MUC_THU])
    env.update(bien_them or {})
    try:
        r = subprocess.run([sys.executable, f.name], capture_output=True, text=True, env=env,
                           cwd=GOC_CAY, timeout=giay)
        return r.returncode, r.stdout + r.stderr
    finally:
        os.unlink(f.name)


def _cay_sao_chep():
    """Sao chép `app/**/*.py` + `admin/*.js` sang thư mục tạm. KHÔNG đụng cây thật."""
    dich = tempfile.mkdtemp(prefix="veh-g19-cay-")
    for goc, _, tens in os.walk(GOC_APP):
        if "__pycache__" in goc or os.sep + "du-lieu" in goc:
            continue
        for ten in tens:
            if not ten.endswith(".py"):
                continue
            tu = os.path.join(goc, ten)
            den = os.path.join(dich, "app", os.path.relpath(tu, GOC_APP))
            os.makedirs(os.path.dirname(den), exist_ok=True)
            shutil.copy2(tu, den)
    for ten in ("admin.js", "index.html"):
        tu = os.path.join(GOC_CAY, "admin", ten)
        if os.path.exists(tu):
            den = os.path.join(dich, "admin", ten)
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
            raise AssertionError("đột biến KHÔNG áp được: không thấy mẫu trong %s" % ten)
        with open(duong, "w", encoding="utf-8") as f:
            f.write(nguon.replace(cu, moi, 1))
    return cay


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. SÁU PHÉP ĐO — mỗi phép trả SỐ, không trả lời phán
# ══════════════════════════════════════════════════════════════════════════════════════════════
DRIVER_TRAN = r'''
import json, os, sys
sys.path.insert(0, os.environ["VIP_G19_APP"])
import gioi_han as gh
ip = os.environ["VIP_G19_IP"]
tran = [l.so_lan for l in gh.luat_cua("auth.dang_nhap") if l.chieu == "ip"]
n = 0
while n < 200000:
    if not gh.kiem("auth.dang_nhap", ip=ip).cho_phep:
        break
    n += 1
print("KETQUA=" + json.dumps({"cho_phep": n, "tran_khai": min(tran) if tran else None}))
'''

_CACHE_DO = {}


def do_tran_theo_so_ban(ds_n=(1, 2, 4, 8), cay=None, ip_goc="198.51.100"):
    """CỔNG C1 (AG-02): SỐ LƯỢT ĐƯỢC PHÉP của `auth.dang_nhap` khi có N TIẾN TRÌNH THẬT.

    Mỗi N là N tiến trình ĐỒNG THỜI, CÙNG một IP, CÙNG một nền CSDL. Trần khai là 20 ở chiều
    `ip`. Trần ĐÚNG thì tổng lượt được phép KHÔNG phụ thuộc N.
    """
    nen_csdl()
    ra = {}
    tran = None
    for n in ds_n:
        ip = "%s.%d" % (ip_goc, 10 + n)
        ps = [subprocess.Popen([sys.executable, "-c", DRIVER_TRAN],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               env=dict(os.environ, VIP_G19_IP=ip,
                                        VIP_G19_APP=(os.path.join(cay, "app") if cay else GOC_APP_DO),
                                        VIP_HUB_DATA=_TAM_CSDL, PYTHONDONTWRITEBYTECODE="1"),
                               cwd=GOC_CAY) for _ in range(n)]
        tong = 0
        for p in ps:
            o, e = p.communicate(timeout=300)
            m = re.search(r"KETQUA=(\{.*\})", o)
            if not m:
                raise AssertionError("driver trần không in KETQUA (N=%d): %s" % (n, e[-300:]))
            d = json.loads(m.group(1))
            tong += d["cho_phep"]
            tran = d["tran_khai"] if tran is None else tran
        ra[n] = tong
    return {"tran_khai": tran, "theo_n": ra}


def do_tran_qua_khoi_dong_lai(so_lan=2, cay=None, ip="198.51.100.200"):
    """CỔNG C2 (AG-03): tổng lượt được phép qua `so_lan` LƯỢT KHỞI ĐỘNG LẠI (tiến trình mới)."""
    nen_csdl()
    tong = 0
    tran = None
    for _ in range(so_lan):
        ma, out = _chay_con(DRIVER_TRAN, goc_cay=cay,
                            bien_them={"VIP_G19_IP": ip})
        m = re.search(r"KETQUA=(\{.*\})", out)
        if not m:
            raise AssertionError("driver trần không in KETQUA (mã thoát %s): %s" % (ma, out[-300:]))
        d = json.loads(m.group(1))
        tong += d["cho_phep"]
        tran = d["tran_khai"] if tran is None else tran
    return {"tran_khai": tran, "so_lan_khoi_dong": so_lan, "tong_cho_phep": tong}


DRIVER_VTP = r'''
import json, os, sys
sys.path.insert(0, os.environ["VIP_G19_APP"])
import trang_thai_hang as t
b = t.BANG.get("vtp") or {}
khoa_so = sorted(k for k in b if str(k).strip().isdigit())
ma_chuoi = json.loads(os.environ["VIP_G19_MA"])
ra = {
    "so_khoa": len(b),
    "so_khoa_so": len(khoa_so),
    "khoa_so": khoa_so,
    "kieu_khoa": sorted(set(type(k).__name__ for k in b)),
    "nguon": t.NGUON_BANG.get("vtp"),
    "phien_ban": t.PHIEN_BAN_TAI_LIEU.get("vtp"),
    "hoan_tat": list(t.TRANG_THAI_HOAN_TAT),
    "anh_xa": {},
    # Hãng khai ORDER_STATUS là **Integer**. Đo CẢ HAI dạng: dạng chuỗi (bảng khoá chuỗi) và
    # dạng số (thứ hãng thật gửi). Hai dạng lệch nhau nghĩa là webhook thật sẽ trượt ánh xạ.
    "anh_xa_so": {},
}
for ma in ma_chuoi:
    kq = t.anh_xa("vtp", ma)
    ra["anh_xa"][ma] = {"biet_ma": kq.biet_ma, "trang_thai": kq.trang_thai,
                        "tin_cay": kq.do_tin_cay, "nhap_nhang": kq.nhap_nhang}
    kq2 = t.anh_xa("vtp", int(ma))
    ra["anh_xa_so"][ma] = {"biet_ma": kq2.biet_ma, "trang_thai": kq2.trang_thai}
kq_la = t.anh_xa("vtp", "99999")
kq_la_so = t.anh_xa("vtp", 99999)
ra["ma_la"] = {"biet_ma": kq_la.biet_ma, "trang_thai": kq_la.trang_thai,
               "biet_ma_dang_so": kq_la_so.biet_ma, "trang_thai_dang_so": kq_la_so.trang_thai}
print("KETQUA=" + json.dumps(ra))
'''


def do_bang_ma_vtp(cay=None):
    """CỔNG C3 (AG-04): hệ thống BIẾT bao nhiêu trong 21 mã VTP hãng đã công bố."""
    m, out = _chay_con(DRIVER_VTP, goc_cay=cay,
                       bien_them={"VIP_G19_MA": json.dumps(list(MA_VTP_CHINH_THUC))})
    g = re.search(r"^KETQUA=(\{.*\})$", out, re.M)
    if not g:
        raise AssertionError("driver VTP không in KETQUA (mã thoát %s): %s" % (m, out[-400:]))
    d = json.loads(g.group(1))
    d["so_ma_chinh_thuc_biet"] = sum(1 for x in d["anh_xa"].values() if x["biet_ma"])
    d["so_ma_chinh_thuc_biet_dang_so"] = sum(1 for x in d["anh_xa_so"].values() if x["biet_ma"])
    d["ma_co_y_none_roi_vao_hoan_tat"] = [
        k for k in MA_VTP_CO_Y_None
        if (d["anh_xa"].get(k) or {}).get("trang_thai") in MA_VTP_HOAN_TAT]
    d["ma_nhap_nhang_roi_vao_hoan_tat"] = [
        k for k in MA_VTP_NHAP_NHANG
        if (d["anh_xa"].get(k) or {}).get("trang_thai") in MA_VTP_HOAN_TAT]
    return d


def _men_giao_dien(goc_admin=None):
    """Rút danh sách mục menu THẲNG từ `admin/admin.js` (không chép tay)."""
    with open(os.path.join(goc_admin or os.path.join(GOC_DO, "admin"), "admin.js"),
              encoding="utf-8") as f:
        nguon = f.read()
    ra = {}
    for ten in ("MAN_TENANT", "MAN_PLATFORM"):
        m = re.search(r"const %s\s*=\s*\[(.*?)\n\];" % ten, nguon, re.S)
        ra[ten] = re.findall(r'\[\s*"([^"]+)"\s*,', m.group(1)) if m else []
    return ra, nguon


def do_man_dot3_tinh(cay=None):
    """CỔNG C4 (AG-05) — đo TĨNH: bao nhiêu trong năm module đợt 3 KHÔNG được `admin.js` gọi.

    Phép đo này đo NGUỒN, không đo DOM. Nó bắt đúng gốc của `V-13910` (*"0 lần được `admin.js`
    tham chiếu = MÃ CHẾT"*). Điều kiện "bấm được" thật sự cần Chromium — xem `I1`.
    """
    nguon = (open(os.path.join(cay, "admin", "admin.js"), encoding="utf-8").read()
             if cay else _doc("admin/admin.js"))
    ten = ("VIPFINANCE", "VIPBILLING", "VIPCARRIERHEALTH", "VIPAI", "VIPHEALTH")
    so_lan = {k: len(re.findall(r"\b%s\b" % k, nguon)) for k in ten}
    return {"so_lan_tham_chieu": so_lan,
            "so_module_chet": sum(1 for v in so_lan.values() if v == 0),
            "ds_module_chet": sorted(k for k, v in so_lan.items() if v == 0)}


def do_ban_phim_tinh(cay=None):
    """CỔNG C5 (AG-06) — đo TĨNH: phần tử điều hướng nào KHÔNG tới được bằng bàn phím.

    `<a>` không `href`, không `tabindex`, không `role` thì Tab không dừng ở đó: nó không nằm
    trong thứ tự tiêu điểm. Đây là điều kiện CẦN, không phải điều kiện ĐỦ — lượt Tab thật
    trong Chromium là `I2`.
    """
    goc = os.path.join(cay, "admin") if cay else os.path.join(GOC_DO, "admin")
    men, nguon = _men_giao_dien(goc)
    khuon = re.findall(r"<a ([^>]*data-man=[^>]*)>", nguon)
    thoat = re.findall(r"""<a ([^>]*id=["']nut-thoat["'][^>]*)>""", nguon)
    re_khong = re.compile(r"href=|tabindex=|role=")
    so_muc_menu_tenant = len(men["MAN_TENANT"])
    khuon_thieu = sum(1 for x in khuon if not re_khong.search(x))
    thoat_thieu = sum(1 for x in thoat if not re_khong.search(x))
    return {"so_khuon_menu": len(khuon), "so_khuon_menu_thieu": khuon_thieu,
            "muc_menu_tenant": so_muc_menu_tenant, "muc_menu_platform": len(men["MAN_PLATFORM"]),
            "nut_thoat_co": len(thoat), "nut_thoat_thieu": thoat_thieu,
            "so_muc_khong_ban_phim_duoc":
                (so_muc_menu_tenant if khuon_thieu else 0) + (1 if thoat_thieu else 0)}


def do_ag00(cay=None):
    """CỔNG C6 (AG-00): migration v9 + route thật cho `app/truy_van.py`."""
    return _do_ag00(cay)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. HAI LÀN NẶNG (bật bằng VIP_G19_DAY_DU=1) — hồi quy toàn phần + tầng 3 Chromium
# ══════════════════════════════════════════════════════════════════════════════════════════════
def do_hoi_quy(giay=2400):
    """Làn H: chạy `app/thu/chay_tat_ca.sh` NGUYÊN VĂN trên nền tạm.

    `VIP_G19_DAY_DU` bị GỠ khỏi môi trường con: chính tệp này được bộ chạy chung TỰ DÒ ra, nên
    để nguyên cờ sẽ đệ quy vô hạn.

    PHÂN LOẠI BỘ HỎNG — vì sao phải phân loại chứ không chỉ đếm: hai bộ thử của **wave TRƯỚC**
    (`thu_qa_g17.py`, `thu_qa_g18.py`) có một cổng "cây sạch" chỉ miễn trừ **tệp của chính chúng**.
    Nên CHÍNH HAI TỆP AG-01 G19 (thứ đề bài cho phép tôi tạo) làm chúng ĐỎ — trên cây sạch thì
    cả 44 bộ đều xanh (§1.1). Đó là `N-G18-03` tái diễn (`N-G19-03`), **không phải** lỗi sản phẩm.
    Bộ đếm trần trụi sẽ báo "2 bộ hỏng" và người đọc tưởng sản phẩm hỏng; bộ đếm biết phân loại
    thì nói được **cái gì** hỏng. `H2` là ĐỐI CHỨNG DƯƠNG chứng minh cách phân loại này ĐÚNG.
    """
    tam = tempfile.mkdtemp(prefix="veh-g19-hq-")
    env = {"VIP_HUB_DATA": tam}
    e = dict(os.environ, **env)
    e.pop("VIP_G19_DAY_DU", None)
    e.pop("VIP_G19_CHO_GOP", None)
    t0 = time.time()
    r = subprocess.run(["sh", "app/thu/chay_tat_ca.sh"], capture_output=True, text=True,
                       cwd=GOC_CAY, env=e, timeout=giay)
    ra = (r.stdout or "") + (r.stderr or "")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "hoi_quy.log"), "w", encoding="utf-8") as f:
        f.write("MA_THOAT=%s\n" % r.returncode + ra)
    m = re.search(r"python:\s+(\d+) ca · (\d+) bộ chạy thật", ra)
    bq = re.search(r"\+\s*(\d+) bộ BỎ QUA", ra)
    hong = re.search(r"bộ hỏng:\s*(.*)", ra)
    fe = re.search(r"frontend:\s*(\d+) \+ (\d+) ca", ra)
    e2e = re.search(r"E2E:\s*(.*)", ra)

    # Bóc chi tiết từng bộ hỏng: dòng `  ✗ <tên> … HỎNG (…)` rồi các dòng thụt `FAIL:`/`ERROR:`.
    chi_tiet = {}
    ten_hien = None
    for dong in ra.splitlines():
        mm = re.match(r"\s+✗\s+(\S+\.py)\s", dong)
        if mm:
            ten_hien = mm.group(1)
            chi_tiet.setdefault(ten_hien, [])
            continue
        mc = re.match(r"\s+(FAIL|ERROR):\s+(\S+)", dong)
        if mc and ten_hien:
            chi_tiet[ten_hien].append(mc.group(2).split("(")[0].strip())
    bo_hong = (hong.group(1).split() if hong and hong.group(1).strip() else [])
    hong_cong_cay_sach = [s for s in bo_hong
                          if s in CONG_CAY_SACH_WAVE_TRUOC
                          and set(chi_tiet.get(s, [])) <= CONG_CAY_SACH_WAVE_TRUOC[s]]
    con_lai = [s for s in bo_hong if s not in hong_cong_cay_sach]
    # Ca chập chờn: CHỈ tha khi (1) nó có tên trong danh sách ĐÃ GHI của wave trước, VÀ (2) mọi
    # ca hỏng khác của bộ đó đều thuộc nhóm cây-sạch, VÀ (3) chạy lại MỘT MÌNH thì ĐẠT.
    lai_thu = {}
    hong_chap_chon = []
    for s in con_lai:
        ds_ca = chi_tiet.get(s, [])
        if s not in CA_CHAP_CHON_WAVE_TRUOC or not set(ds_ca) <= CA_CHAP_CHON_WAVE_TRUOC[s]:
            continue
        lai_thu[s] = {}
        dat_het = True
        for ten_ca in sorted(ds_ca):
            ma, out, _ = _chay(["python3", "app/thu/" + s, "B_Tang3." + ten_ca],
                               env={"VIP_HUB_DATA": tempfile.mkdtemp(prefix="veh-g19-lt-")},
                               giay=900)
            lai_thu[s][ten_ca] = ma
            if ma != 0 or not re.search(r"^OK( |$)", out, re.M):
                dat_het = False
        if dat_het:
            hong_chap_chon.append(s)
    hong_san_pham = [s for s in bo_hong
                     if s not in hong_cong_cay_sach and s not in hong_chap_chon]
    return {"ma_thoát": r.returncode, "giay": round(time.time() - t0, 1),
            "so_ca": int(m.group(1)) if m else None,
            "so_bo": int(m.group(2)) if m else None,
            "so_bo_qua": int(bq.group(1)) if bq else 0,
            "bo_hong": bo_hong, "chi_tiet": chi_tiet, "lai_thu": lai_thu,
            "hong_san_pham": hong_san_pham, "hong_cong_cay_sach": hong_cong_cay_sach,
            "hong_chap_chon": hong_chap_chon,
            "frontend": (int(fe.group(1)), int(fe.group(2))) if fe else None,
            "e2e": e2e.group(1).strip() if e2e else None,
            "log": os.path.join(LOG_DIR, "hoi_quy.log")}


def do_cong_cay_sach_wave_truoc():
    """ĐỐI CHỨNG DƯƠNG cho cách phân loại ở `do_hoi_quy`.

    Chạy ĐÚNG MỘT ca của mỗi bộ wave trước (unittest cho chọn `Lớp.ca`) và khẳng định lời phàn
    nàn **nêu đích danh hai tệp AG-01 G19** — tức bộ đỏ vì **tệp được phép tạo**, không vì mã
    sản phẩm. Chạy 1 ca mất 0,03 giây, nên đối chứng này gần như miễn phí.
    """
    ra = {}
    for bo, ca in sorted(CONG_CAY_SACH_WAVE_TRUOC.items()):
        for ten_ca in sorted(ca):
            ma, out, _ = _chay(["python3", "app/thu/" + bo, "A_Nen." + ten_ca],
                               env={"VIP_HUB_DATA": tempfile.mkdtemp(prefix="veh-g19-cs-")}, giay=300)
            ra[bo] = {"ma_thoát": ma, "neu_dich_danh": sorted(
                t for t in TEP_CUA_AG01_G19 if t in out)}
    return ra


def _dung_nen_tang3():
    """Dựng nền cô lập + máy chủ loopback cho các phép đo cần TRÌNH DUYỆT THẬT.

    Trả `(goc_url, nen, tien_trinh)`, hoặc `(None, ly_do, None)` nếu dựng không được. Máy chủ
    bind `127.0.0.1` **cổng do hệ điều hành cấp** — không mở cổng ra ngoài, không tranh cổng.
    """
    if not os.path.isdir(PW_BROWSERS_CHI_DINH):
        return None, "thiếu nhị phân Chromium ở %s" % PW_BROWSERS_CHI_DINH, None
    if not os.path.isdir(os.path.join(GOC_CAY, "node_modules", "@playwright", "test")):
        return None, "thiếu node_modules/@playwright/test — chạy `npm ci`", None
    import socket
    nen = tempfile.mkdtemp(prefix="veh-g19-t3-")
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    cong = s.getsockname()[1]
    s.close()
    env = dict(os.environ, VIP_HUB_DATA=nen, PYTHONDONTWRITEBYTECODE="1")
    for lenh in (["python3", "app/migrate.py"], ["python3", "app/khoi_tao.py"],
                 ["python3", "thu_giao_dien/chuan_bi.py", "mk"]):
        r = subprocess.run(lenh, capture_output=True, text=True, cwd=GOC_CAY, env=env, timeout=300)
        if r.returncode != 0:
            return None, "nền tầng 3 dựng hỏng ở %s: %s" % (lenh, r.stderr[-300:]), None
    sv = subprocess.Popen(["python3", "app/server.py", str(cong)], cwd=GOC_CAY, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", cong), 0.2).close()
            break
        except OSError:
            time.sleep(0.2)
    else:
        sv.terminate()
        return None, "máy chủ tầng 3 không mở cổng %d" % cong, None
    goc_url = "http://127.0.0.1:%d" % cong
    subprocess.run(["python3", "thu_giao_dien/chuan_bi.py", "don", goc_url],
                   capture_output=True, text=True, cwd=GOC_CAY, env=env, timeout=300)
    return goc_url, nen, sv


def do_tang3(spec=None, giay=900):
    """Làn I: tầng 3 trong Chromium THẬT, theo đúng khuôn `thu_giao_dien/chay.sh`.

    KHÁC ĐÚNG HAI ĐIỂM, cả hai đều ghi ra đây: (1) `PLAYWRIGHT_BROWSERS_PATH` trỏ vào nguồn
    nhị phân mà `BAN_GIAO.md` §1 chỉ định (worktree này không có `.local-browsers`); (2) ống
    báo cáo HTML và `outputDir` đẩy ra `/tmp` — ghi vào `thu_giao_dien/_bao-cao/` có thể bị
    sandbox chặn (EPERM) và EPERM KHÔNG phải ca thử hỏng.
    """
    goc_url, nen, sv = _dung_nen_tang3()
    if goc_url is None:
        return {"bo_qua": nen}
    lenh = ["npx", "playwright", "test", "--reporter=line", "--output=" + os.path.join(nen, "out")]
    if spec:
        lenh.append(spec)
    r = subprocess.run(lenh, capture_output=True, text=True, cwd=GOC_CAY, timeout=giay,
                       env=dict(os.environ, VIP_HUB_DATA=nen, PYTHONDONTWRITEBYTECODE="1",
                                VIP_GD_GOC=goc_url, VIP_GD_NEN=nen,
                                PLAYWRIGHT_BROWSERS_PATH=PW_BROWSERS_CHI_DINH))
    sv.terminate()
    ra = (r.stdout or "") + (r.stderr or "")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "tang3.log"), "w", encoding="utf-8") as f:
        f.write("MA_THOAT=%s\n" % r.returncode + ra)
    dem = re.search(r"(\d+) passed", ra)
    hong = re.search(r"(\d+) failed", ra)
    bo = re.search(r"(\d+) skipped", ra)
    khai = re.search(r"đợt 3 khai (\d+) màn; (\d+) đã có trên menu; (\d+) CHƯA cắm", ra)
    return {"ma_thoát": r.returncode,
            "dat": int(dem.group(1)) if dem else 0,
            "hong": int(hong.group(1)) if hong else 0,
            "bo_qua_ca": int(bo.group(1)) if bo else 0,
            "khai": int(khai.group(1)) if khai else None,
            "co_menu": int(khai.group(2)) if khai else None,
            "chua_cam": int(khai.group(3)) if khai else None,
            "log": os.path.join(LOG_DIR, "tang3.log")}


# Dò bàn phím: ĐÚNG cách `V-13911` được đo (*"15 lượt Tab không rời `body`"*), nhưng đi 40 lượt
# và ghi lại VẾT TIÊU ĐIỂM từng lượt — để con số "không rời body" là hệ quả của một dãy đo, không
# phải một khẳng định. Dùng `playwright` thư viện (không phải test-runner) nên không cần thêm tệp
# spec nào trong cây.
DO_BAN_PHIM_JS = r'''
const path = require("path");
const GOC = process.env.VIP_G19_REPO;
const { chromium } = require(path.join(GOC, "node_modules", "@playwright", "test"));
const MK = "MatKhauThu-GiaoDien-123";     // mật khẩu THỬ của nền tạm, không phải credential thật
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage();
  const loi = [];
  p.on("pageerror", (e) => loi.push(String(e)));
  await p.goto(process.env.VIP_GD_GOC + "/admin/index.html", { waitUntil: "domcontentloaded" });
  await p.locator("#dn-ten").fill("shopa-owner");
  await p.locator("#dn-mk").fill(MK);
  await p.locator("#dn-nut").click();
  await p.locator(".menu-quan-tri a").first().waitFor({ state: "visible" });
  const soMuc = await p.locator(".menu-quan-tri a").count();
  await p.evaluate(() => document.body.focus());
  const vet = [];
  let roiBody = null;
  for (let i = 1; i <= 40; i++) {
    await p.keyboard.press("Tab");
    const a = await p.evaluate(() => {
      const e = document.activeElement;
      if (!e) return { tag: "NULL" };
      return { tag: e.tagName, id: e.id || null,
               man: e.dataset ? (e.dataset.man || null) : null };
    });
    vet.push(a);
    if (roiBody === null && a.tag !== "BODY") roiBody = i;
  }
  const tabToiMan = new Set(vet.map((x) => x.man).filter(Boolean));
  console.log("KETQUA=" + JSON.stringify({
    so_muc_menu: soMuc,
    co_nut_thoat: await p.locator("#nut-thoat").count(),
    tab_roi_body_o_lan: roiBody,
    so_muc_menu_tab_toi_duoc: tabToiMan.size,
    nut_thoat_tab_toi_duoc: vet.some((x) => x.id === "nut-thoat"),
    so_lan_tab: vet.length,
    loi_trang: loi,
  }));
  await b.close();
})().catch((e) => { console.error("LOI: " + e.message); process.exit(2); });
'''


def do_ban_phim_that(giay=300):
    """CỔNG C5 phần hai (AG-06) — lượt Tab THẬT trong Chromium trên khung quản trị."""
    goc_url, nen, sv = _dung_nen_tang3()
    if goc_url is None:
        return {"bo_qua": nen}
    f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8")
    f.write(DO_BAN_PHIM_JS)
    f.close()
    try:
        r = subprocess.run(["node", f.name], capture_output=True, text=True, cwd=GOC_CAY,
                           timeout=giay,
                           env=dict(os.environ, VIP_HUB_DATA=nen, VIP_GD_GOC=goc_url,
                                    VIP_G19_REPO=GOC_CAY,
                                    PLAYWRIGHT_BROWSERS_PATH=PW_BROWSERS_CHI_DINH))
    finally:
        os.unlink(f.name)
        sv.terminate()
    ra = (r.stdout or "") + (r.stderr or "")
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, "ban_phim.log"), "w", encoding="utf-8") as fh:
        fh.write("MA_THOAT=%s\n" % r.returncode + ra)
    m = re.search(r"^KETQUA=(\{.*\})$", ra, re.M)
    if not m:
        return {"bo_qua": "phép dò bàn phím không in KETQUA (mã thoát %s): %s"
                          % (r.returncode, ra[-300:])}
    d = json.loads(m.group(1))
    d["ma_thoát"] = r.returncode
    d["log"] = os.path.join(LOG_DIR, "ban_phim.log")
    return d


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CÁC NHÓM CA
# ══════════════════════════════════════════════════════════════════════════════════════════════
class A_Nen(unittest.TestCase):
    """Nền đóng băng + chốt an toàn. Nhóm này ĐỎ thì mọi số đo khác vô hiệu."""

    def test_a1_head_dung_ghim_va_cay_sach(self):
        head = _git("rev-parse", "HEAD").stdout.strip()
        self.assertEqual(head, HEAD_GHIM, "HEAD KHÁC nền đóng băng — mọi số đo phải coi là vô hiệu")
        st = [d for d in _git("status", "--porcelain=v1", "-uall").stdout.splitlines()
              if d.strip() and not _la_tep_ag01(d)]
        self.assertEqual(st, [], "cây có thay đổi NGOÀI hai tệp AG-01 G19: %s" % st[:5])
        _dc_duong("nen-dong-bang")
        print("\n  [A1] HEAD=%s · cây sạch ngoài 2 tệp AG-01 · vân tay=%s" % (head[:7], VAN_TAY_LUC_NAN[:16]))

    def test_a2_chot_an_toan_du(self):
        self.assertIsNone(kiem_chot_an_toan(), "chốt an toàn báo sai: %s" % _LY_DO_TU_CHOI)
        _dc_duong("chot-an-toan")
        print("  [A2] nền CSDL=%s (thư mục tạm) · không adapter LIVE" % _TAM_CSDL)

    def test_a3_bo_do_chot_an_toan_co_rang(self):
        """Phủ định + ĐỐI CHỨNG DƯƠNG: bộ kiểm chốt an toàn phải BẮT được ba tình huống hỏng."""
        for dia_chi in ("0.0.0.0", "192.168.1.9"):
            self.assertIsNotNone(kiem_chot_an_toan({"dia_chi": dia_chi}),
                                 "bộ kiểm MÙ với bind %s" % dia_chi)
        gia = type("AdapterGiaLive", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live-a3"] = gia
        try:
            ly = kiem_chot_an_toan()
        finally:
            adapter._DANG_KY.pop("gia-live-a3", None)
        self.assertIsNotNone(ly, "bộ kiểm MÙ với adapter MỞ LIVE")
        self.assertIn("gia-live-a3", ly or "")
        self.assertIsNone(kiem_chot_an_toan(), "sổ đăng ký adapter chưa trả nguyên trạng")
        _dc_am("chot-an-toan")
        _dc_duong("chot-an-toan")
        print("  [A3] chốt an toàn BẮT được bind LAN/0.0.0.0 + adapter LIVE; môi trường thật vẫn ĐỦ")

    def test_a4_van_sqlite_khong_chuyen_postgres(self):
        """D-8: CSDL nghiệp vụ vẫn SQLite. Không import driver PostgreSQL trong `app/*.py`."""
        cam = re.compile(r"^\s*(import|from)\s+(psycopg|psycopg2|asyncpg|pg8000)\b", re.M)
        pham = []
        for ten in sorted(os.listdir(GOC_APP_DO)):
            if ten.endswith(".py"):
                with open(os.path.join(GOC_APP_DO, ten), encoding="utf-8") as f:
                    if cam.search(f.read()):
                        pham.append(ten)
        self.assertEqual(pham, [], "app/*.py đã import driver PostgreSQL (D-8 bị vi phạm): %s" % pham)
        import csdl
        kn = csdl.mo()
        self.assertEqual(getattr(type(kn), "__module__", ""), "sqlite3",
                         "kết nối CSDL nghiệp vụ không phải sqlite3: %r" % type(kn))
        _dc_duong("d-8-sqlite")
        print("  [A4] D-8: 0/%d tệp app/*.py import driver PostgreSQL · CSDL nghiệp vụ = %s.%s"
              % (len([t for t in os.listdir(GOC_APP_DO) if t.endswith(".py")]),
                 type(kn).__module__, type(kn).__name__))


class B_AG02_TranTheoBan(unittest.TestCase):
    """CỔNG C1 — trần tần suất phải GIỮ NGUYÊN qua N tiến trình thật."""

    def test_b1_cong_c1_tran_khong_nhan_theo_so_ban(self):
        d = do_tran_theo_so_ban(ds_n=(1, 2, 4, 8))
        tran = d["tran_khai"]
        self.assertIsNotNone(tran, "không đọc được trần khai của `auth.dang_nhap`")
        mo = {n: tran * n for n in d["theo_n"]}
        dong = {n: tran for n in d["theo_n"]}
        ky, nhan, doi = _ky_vong(mo, dong)
        print("\n  [B1] trần khai=%s · đo được=%s · kỳ vọng (%s)=%s · chiều kia=%s"
              % (tran, d["theo_n"], nhan, ky, doi))
        _dc_duong("tran-theo-ban")
        if not NHO_DONG:
            _dc_am("tran-theo-ban")
        self.assertEqual(d["theo_n"], ky,
                         "CỔNG C1 (AG-02) KHÔNG đạt ở chế độ %s: đo %s, kỳ vọng %s%s"
                         % (nhan, d["theo_n"], ky, "\n" + _nhac()))


class C_AG03_KhoiDongLai(unittest.TestCase):
    """CỔNG C2 — bộ đếm tần suất phải SỐNG qua khởi động lại."""

    def test_c1_cong_c2_bo_dem_song_qua_khoi_dong_lai(self):
        d = do_tran_qua_khoi_dong_lai(so_lan=2)
        tran = d["tran_khai"]
        mo = {"2 lượt": tran * 2}
        dong = {"2 lượt": tran}
        ky, nhan, doi = _ky_vong(mo, dong)
        print("\n  [C1] trần khai=%s · qua %d lượt khởi động lại = %s · kỳ vọng (%s)=%s · chiều kia=%s"
              % (tran, d["so_lan_khoi_dong"], d["tong_cho_phep"], nhan, ky, doi))
        _dc_duong("khoi-dong-lai")
        if not NHO_DONG:
            _dc_am("khoi-dong-lai")
        self.assertEqual({"2 lượt": d["tong_cho_phep"]}, ky,
                         "CỔNG C2 (AG-03) KHÔNG đạt ở chế độ %s: đo %s, kỳ vọng %s%s"
                         % (nhan, d["tong_cho_phep"], ky, "\n" + _nhac()))


class D_AG04_MaVTP(unittest.TestCase):
    """CỔNG C3 — 21 mã VTP hãng đã công bố phải có bảng ánh xạ, và KHÔNG được đoán."""

    def test_d1_cong_c3_21_ma_vtp(self):
        d = do_bang_ma_vtp()
        mo = {"so_ma_chinh_thuc_biet": 0, "nguon_mo_phong": True, "phien_ban_chua_co": True}
        dong = {"so_ma_chinh_thuc_biet": len(MA_VTP_CHINH_THUC), "nguon_mo_phong": False,
                "phien_ban_chua_co": False}
        do = {"so_ma_chinh_thuc_biet": d["so_ma_chinh_thuc_biet"],
              "nguon_mo_phong": "mô phỏng" in (d["nguon"] or ""),
              "phien_ban_chua_co": d["phien_ban"] == "chua-co-tai-lieu"}
        mo_thuc = dict(mo)
        # Trạng thái nền chỉ khớp khi ĐÚNG số nợ đã đo: 0 mã thật + nguồn tự khai mô phỏng.
        ky, nhan, doi = _ky_vong(mo, dong)
        print("\n  [D1] đo được=%s · nguồn=%r · phiên bản tài liệu=%r · kỳ vọng (%s)=%s"
              % (do, d["nguon"], d["phien_ban"], nhan, ky))
        _dc_duong("ma-vtp")
        if not NHO_DONG:
            _dc_am("ma-vtp")
        self.assertEqual(do, ky,
                         "CỔNG C3 (AG-04) KHÔNG đạt ở chế độ %s: đo %s, kỳ vọng %s%s"
                         % (nhan, do, ky, "\n" + _nhac()))

    def test_d2_ma_chua_xac_minh_khong_roi_vao_hoan_tat(self):
        """D-4 + luật chống bịa: mã chưa chốt nghĩa TUYỆT ĐỐI không được thành 'đã giao'."""
        d = do_bang_ma_vtp()
        self.assertEqual(d["ma_co_y_none_roi_vao_hoan_tat"], [],
                         "mã cố ý None lại ánh xạ sang trạng thái HOÀN TẤT: %s"
                         % d["ma_co_y_none_roi_vao_hoan_tat"])
        self.assertEqual(d["ma_nhap_nhang_roi_vao_hoan_tat"], [],
                         "mã NHẬP NHẰNG lại ánh xạ sang trạng thái HOÀN TẤT: %s"
                         % d["ma_nhap_nhang_roi_vao_hoan_tat"])
        _dc_am("ma-vtp-khong-doan")
        # ĐỐI CHỨNG DƯƠNG: bảng CÓ thật và mã lạ thì bị từ chối, không mặc định về gì cả.
        self.assertGreater(d["so_khoa"], 0, "BANG['vtp'] RỖNG ⇒ phép đo trên không đo gì")
        self.assertFalse(d["ma_la"]["biet_ma"], "mã lạ 99999 được coi là BIẾT ⇒ có đoán mã")
        self.assertIsNone(d["ma_la"]["trang_thai"], "mã lạ 99999 bị gán trạng thái ⇒ có đoán mã")
        self.assertFalse(d["ma_la"]["biet_ma_dang_so"], "mã lạ 99999 (dạng số) được coi là BIẾT")
        self.assertIsNone(d["ma_la"]["trang_thai_dang_so"], "mã lạ 99999 (dạng số) bị gán trạng thái")
        _dc_duong("ma-vtp-khong-doan")
        print("  [D2] 0/%d mã cố ý None và 0/%d mã nhập nhằng rơi vào %s · mã lạ bị từ chối ở CẢ "
              "hai dạng chuỗi và số"
              % (len(MA_VTP_CO_Y_None), len(MA_VTP_NHAP_NHANG), list(MA_VTP_HOAN_TAT)))

    def test_d3_ma_hang_gui_dang_SO_cung_phai_nhan_ra(self):
        """CỔNG C3 (phần hai) — `N-G19-01`: hãng khai `ORDER_STATUS` là **Integer**.

        `trang_thai_hang._khoa_ma` chuẩn hoá `int` cho `jt` nhưng **trả nguyên giá trị** cho hãng
        khác. Nên `anh_xa("vtp", 101)` (số) và `anh_xa("vtp", "101")` (chuỗi) tra HAI khoá khác
        nhau. Hôm nay chưa lộ vì `BANG["vtp"]` chưa có khoá số nào — nhưng đó là CHÌA KHOÁ CỬA
        cho AG-04: mang 21 mã sang bằng khoá CHUỖI thì webhook thật (payload số) trượt sạch ánh
        xạ mà không có gì báo. Ca này đo đúng chỗ đó.
        """
        d = do_bang_ma_vtp()
        ky, nhan, doi = _ky_vong(
            {"dang_so": 0, "bang_nhau": True},
            {"dang_so": len(MA_VTP_CHINH_THUC), "bang_nhau": True})
        do = {"dang_so": d["so_ma_chinh_thuc_biet_dang_so"],
              "bang_nhau": d["so_ma_chinh_thuc_biet_dang_so"] == d["so_ma_chinh_thuc_biet"]}
        print("\n  [D3] biết mã ở dạng CHUỖI=%d · ở dạng SỐ (hãng gửi)=%d · kiểu khoá bảng=%s · "
              "kỳ vọng (%s)=%s"
              % (d["so_ma_chinh_thuc_biet"], d["so_ma_chinh_thuc_biet_dang_so"],
                 d["kieu_khoa"], nhan, ky))
        _dc_duong("ma-vtp-dang-so")
        if not NHO_DONG:
            _dc_am("ma-vtp-dang-so")
        self.assertEqual(do, ky,
                         "CỔNG C3 phần hai (N-G19-01) KHÔNG đạt ở chế độ %s: %s, kỳ vọng %s%s"
                         % (nhan, do, ky, "\n" + _nhac()))


class E_AG05_ManChuaCam(unittest.TestCase):
    """CỔNG C4 — màn khai ở đợt 3 phải có ĐƯỜNG VÀO thật (hoặc bị bỏ kèm lý do)."""

    def test_e1_cong_c4_khong_con_module_chet(self):
        d = do_man_dot3_tinh()
        ky, nhan, doi = _ky_vong({"so_module_chet": 4}, {"so_module_chet": 0})
        print("\n  [E1] (đo TĨNH trên nguồn) số lần `admin.js` tham chiếu=%s · module chết=%d %s"
              % (d["so_lan_tham_chieu"], d["so_module_chet"], d["ds_module_chet"]))
        _dc_duong("man-dot3")
        if not NHO_DONG:
            _dc_am("man-dot3")
        self.assertEqual({"so_module_chet": d["so_module_chet"]}, ky,
                         "CỔNG C4 (AG-05) KHÔNG đạt ở chế độ %s: %d module chết %s, kỳ vọng %s%s"
                         % (nhan, d["so_module_chet"], d["ds_module_chet"], ky, "\n" + _nhac()))


class F_AG06_BanPhim(unittest.TestCase):
    """CỔNG C5 — giao diện quản trị phải tới được bằng BÀN PHÍM."""

    def test_f1_cong_c5_dieu_huong_toi_duoc_bang_ban_phim(self):
        d = do_ban_phim_tinh()
        ky, nhan, doi = _ky_vong({"so_muc_khong_ban_phim_duoc": 12},
                                 {"so_muc_khong_ban_phim_duoc": 0})
        print("\n  [F1] (đo TĨNH trên nguồn) khuôn menu thiếu thuộc tính=%d · nút thoát thiếu=%d · "
              "mục menu tenant=%d · KHÔNG tới được bằng Tab=%d"
              % (d["so_khuon_menu_thieu"], d["nut_thoat_thieu"], d["muc_menu_tenant"],
                 d["so_muc_khong_ban_phim_duoc"]))
        _dc_duong("ban-phim")
        if not NHO_DONG:
            _dc_am("ban-phim")
        self.assertEqual({"so_muc_khong_ban_phim_duoc": d["so_muc_khong_ban_phim_duoc"]}, ky,
                         "CỔNG C5 (AG-06) KHÔNG đạt ở chế độ %s: %d mục không Tab tới được, "
                         "kỳ vọng %s%s" % (nhan, d["so_muc_khong_ban_phim_duoc"], ky, "\n" + _nhac()))


class G_AG00_TruyVanMigration(unittest.TestCase):
    """CỔNG C6 — `truy_van.py` phải có route thật + `DDL_G12Q` vào migration v9."""

    def test_g1_cong_c6_migration_v9_va_route(self):
        d = do_ag00()
        do = {"v9": d["phien_ban_schema"] >= 9, "nang_len_v9": d["co_nang_len_v9"],
              "route": d["so_tham_chieu_module_truy_van"] > 0}
        ky, nhan, doi = _ky_vong({"v9": False, "nang_len_v9": False, "route": False},
                                 {"v9": True, "nang_len_v9": True, "route": True})
        print("\n  [G1] PHIEN_BAN_SCHEMA=%s · nang_len_v9=%s · tham chiếu `truy_van.` trong "
              "server.py=%d · tuyến=%s · kỳ vọng (%s)=%s"
              % (d["phien_ban_schema"], d["co_nang_len_v9"],
                 d["so_tham_chieu_module_truy_van"], d["tuyen_truy_van"], nhan, ky))
        _dc_duong("ag00-truy-van")
        if not NHO_DONG:
            _dc_am("ag00-truy-van")
        self.assertEqual(do, ky, "CỔNG C6 (AG-00) KHÔNG đạt ở chế độ %s: đo %s, kỳ vọng %s%s"
                         % (nhan, do, ky, "\n" + _nhac()))


class H_HoiQuy(unittest.TestCase):
    """Làn H — hồi quy toàn phần. CHỈ chạy khi `VIP_G19_DAY_DU=1` (bỏ qua KHÔNG im lặng)."""

    def test_h1_hoi_quy_toan_phan_tren_nen(self):
        if not DAY_DU:
            self.skipTest("CHƯA ĐO trong làn mặc định: bật VIP_G19_DAY_DU=1 để chạy "
                          "`sh app/thu/chay_tat_ca.sh` (≈3 phút)")
        d = do_hoi_quy()
        print("\n  [H1] thoát=%s · %s ca · %s bộ · %s bộ bỏ qua · %.1fs"
              % (d["ma_thoát"], d["so_ca"], d["so_bo"], d["so_bo_qua"], d["giay"]))
        print("       bộ hỏng: %s" % (d["bo_hong"] or "KHÔNG"))
        print("       trong đó HỎNG DO CỔNG CÂY SẠCH CỦA WAVE TRƯỚC (N-G19-03): %s"
              % (d["hong_cong_cay_sach"] or "không"))
        print("       CHẬP CHỜN đã biết, CHẠY LẠI MỘT MÌNH thì ĐẠT (N-G18-01): %s"
              % (d["hong_chap_chon"] or "không"))
        for bo, kq in sorted(d["lai_thu"].items()):
            print("         ↻ %s: %s" % (bo, {k: "thoát %s" % v for k, v in sorted(kq.items())}))
        print("       HỎNG SẢN PHẨM: %s" % (d["hong_san_pham"] or "KHÔNG"))
        print("       frontend=%s · E2E=%s · log=%s" % (d["frontend"], d["e2e"], d["log"]))
        _dc_duong("hoi-quy")
        # Cổng "teo ca": bộ chạy TỰ DÒ, nên lượt này phải thấy 44 bộ CŨ + chính tệp này = 45.
        # Số ca thì ĐẾM TỪ CHÍNH TỆP NÀY, không viết cứng: thêm một ca vào đây mà con số kỳ vọng
        # không đổi là đúng khuôn "số viết cứng" mà §12.1 luật 5 cấm.
        so_ca_tep_nay = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]).countTestCases()
        self.assertEqual(d["so_bo"], 45, "số bộ dò được khác 45 (44 bộ nền + chính tệp này)")
        self.assertEqual(d["so_ca"], 1631 + so_ca_tep_nay,
                         "số ca khác %d (1631 ca nền + %d ca của tệp này)"
                         % (1631 + so_ca_tep_nay, so_ca_tep_nay))
        self.assertEqual(d["hong_san_pham"], [],
                         "HỎNG SẢN PHẨM ở bộ: %s (log %s)" % (d["hong_san_pham"], d["log"]))
        if d["hong_cong_cay_sach"] or d["hong_chap_chon"]:
            _dc_am("hoi-quy")
        self.assertEqual(sorted(d["hong_cong_cay_sach"] + d["hong_chap_chon"] + d["hong_san_pham"]),
                         sorted(d["bo_hong"]),
                         "phân loại bộ hỏng không khớp danh sách thật — mọi bộ hỏng phải rơi "
                         "vào ĐÚNG MỘT trong ba nhóm")

    def test_h2_doi_chung_duong_cho_cach_phan_loai(self):
        """ĐỐI CHỨNG DƯƠNG — chứng minh hai bộ đỏ kia đỏ vì **tệp được phép tạo**, không vì mã.

        Không có ca này thì `H1` có thể đang dùng danh sách miễn trừ như một tấm bình phong: cứ
        khai một bộ vào `CONG_CAY_SACH_WAVE_TRUOC` là nó không bao giờ bị tính là hỏng. Ca này
        chạy **đúng một ca** của mỗi bộ đó và bắt lời phàn nàn phải **nêu đích danh** hai tệp
        AG-01 G19. Lệch một ly là ĐỎ.
        """
        if not DAY_DU:
            self.skipTest("CHƯA ĐO trong làn mặc định: bật VIP_G19_DAY_DU=1")
        d = do_cong_cay_sach_wave_truoc()
        for bo, kq in sorted(d.items()):
            self.assertEqual(kq["ma_thoát"], 1,
                             "%s: ca cổng cây sạch KHÔNG đỏ (thoát %s) ⇒ cách phân loại ở H1 SAI"
                             % (bo, kq["ma_thoát"]))
            self.assertEqual(kq["neu_dich_danh"], sorted(TEP_CUA_AG01_G19),
                             "%s: lời phàn nàn không nêu đích danh đúng hai tệp AG-01 G19: %s"
                             % (bo, kq["neu_dich_danh"]))
        _dc_am("cong-cay-sach-wave-truoc")
        _dc_duong("cong-cay-sach-wave-truoc")
        print("\n  [H2] %s — mỗi bộ ĐỎ và lời phàn nàn nêu đích danh %s ⇒ tệp ĐƯỢC PHÉP TẠO là"
              " nguyên nhân, KHÔNG phải mã sản phẩm"
              % (", ".join(sorted(d)), list(TEP_CUA_AG01_G19)))


class I_Tang3(unittest.TestCase):
    """Làn I — tầng 3 Chromium THẬT cho AG-05/AG-06. CHỈ chạy khi `VIP_G19_DAY_DU=1`."""

    def test_i1_tang3_man_dot3_bam_duoc(self):
        if not DAY_DU:
            self.skipTest("CHƯA ĐO trong làn mặc định: cần Chromium; bật VIP_G19_DAY_DU=1")
        d = do_tang3("04_nhan_va_man_dot3.spec.js")
        if d.get("bo_qua"):
            self.skipTest("CHƯA ĐO: " + d["bo_qua"])
        print("\n  [I1] tầng 3 đợt 3: thoát=%s · %s đạt · %s hỏng · khai=%s có-menu=%s chưa-cắm=%s"
              % (d["ma_thoát"], d["dat"], d["hong"], d["khai"], d["co_menu"], d["chua_cam"]))
        _dc_duong("tang3-man")
        if not NHO_DONG:
            _dc_am("tang3-man")
        self.assertEqual(d["hong"], 0, "tầng 3 có ca hỏng (log: %s)" % d["log"])
        if d["chua_cam"] is not None:
            ky, nhan, _ = _ky_vong(15, 0)
            self.assertEqual(d["chua_cam"], ky,
                             "CỔNG C4 (tầng 3) chưa-cắm=%s ở chế độ %s, kỳ vọng %s%s"
                             % (d["chua_cam"], nhan, ky, "\n" + _nhac()))

    def test_i2_tang3_ban_phim_tab_toi_duoc(self):
        """CỔNG C5 phần hai (AG-06) — 40 lượt Tab THẬT trong Chromium, ghi vết tiêu điểm."""
        if not DAY_DU:
            self.skipTest("CHƯA ĐO trong làn mặc định: cần Chromium; bật VIP_G19_DAY_DU=1")
        d = do_ban_phim_that()
        if d.get("bo_qua"):
            self.skipTest("CHƯA ĐO: " + d["bo_qua"])
        ky, nhan, _ = _ky_vong(
            {"so_muc_menu_tab_toi_duoc": 0, "nut_thoat_tab_toi_duoc": False,
             "roi_body": False},
            {"so_muc_menu_tab_toi_duoc": d["so_muc_menu"], "nut_thoat_tab_toi_duoc": True,
             "roi_body": True})
        do = {"so_muc_menu_tab_toi_duoc": d["so_muc_menu_tab_toi_duoc"],
              "nut_thoat_tab_toi_duoc": d["nut_thoat_tab_toi_duoc"],
              "roi_body": d["tab_roi_body_o_lan"] is not None}
        print("\n  [I2] (Chromium THẬT) %d mục menu · Tab rời `body` ở lượt %s · Tab tới được %d/%d "
              "mục menu · nút Đăng xuất tới được=%s · lỗi trang=%s · kỳ vọng (%s)=%s"
              % (d["so_muc_menu"], d["tab_roi_body_o_lan"], d["so_muc_menu_tab_toi_duoc"],
                 d["so_muc_menu"], d["nut_thoat_tab_toi_duoc"], d["loi_trang"], nhan, ky))
        _dc_duong("ban-phim-that")
        if not NHO_DONG:
            _dc_am("ban-phim-that")
        self.assertEqual(d["loi_trang"], [], "trang quản trị sinh lỗi khi đi bằng bàn phím")
        self.assertEqual(do, ky,
                         "CỔNG C5 phần hai (AG-06) KHÔNG đạt ở chế độ %s: %s, kỳ vọng %s%s\n"
                         "     vết: %s"
                         % (nhan, do, ky, "\n" + _nhac(), d["log"]))


class J_TuKiemBoDo(unittest.TestCase):
    """HAI CHỐT CHẶN BẮT BUỘC — không có nhóm này thì mọi dòng "✓" của tệp này vô nghĩa."""

    def test_j1_ca_co_y_hong_bi_bo_do_THAY_trong_tien_trinh_con(self):
        """CHỐT (a): một ca cố ý hỏng, chạy trong TIẾN TRÌNH CON, phải bị luật phán bắt."""
        ma, ra = _chay_con(MA_THU_HONG)
        self.assertNotEqual(ma, 0, "bộ dò KHÔNG thấy ca cố ý hỏng (mã thoát %s)" % ma)
        self.assertIn("FAILED", ra, "output ca hỏng không có dấu hiệu hỏng")
        self.assertFalse(re.search(r"^OK( |$)", ra, re.M), "output vừa FAILED vừa có dòng OK")
        self.assertEqual(_phan_quyet(ma, ra), "HỎNG")
        _dc_am("tu-kiem-bo-do")
        ma2, ra2 = _chay_con(MA_THU_DAT)
        self.assertEqual(ma2, 0, "ca ĐẠT lại thoát %s: %s" % (ma2, ra2[-300:]))
        self.assertRegex(ra2, r"Ran 1 test")
        self.assertEqual(_phan_quyet(ma2, ra2), "ĐẠT")
        _dc_duong("tu-kiem-bo-do")
        print("\n  [J1] ca cố ý hỏng (tiến trình con) → thoát %s · bộ dò THẤY; ca đạt → thoát %s"
              % (ma, ma2))

    def test_j2_luat_phan_tu_choi_ba_kich_ban_lua(self):
        """CHỐT (a): luật phán phải từ chối ba cách 'xanh giả'."""
        self.assertEqual(_phan_quyet(0, "OK\n"), "HỎNG", "thoát 0 mà 0 ca vẫn được ĐẠT")
        self.assertEqual(_phan_quyet(0, "chay xong, khong in gi"), "HỎNG",
                         "thoát 0 không dấu vết vẫn ĐẠT")
        self.assertEqual(_phan_quyet(1, "Ran 5 tests\nOK\n"), "HỎNG", "in OK rồi thoát 1 vẫn ĐẠT")
        self.assertEqual(_phan_quyet(0, "Ran 5 tests\nOK\n"), "ĐẠT")
        self.assertEqual(_phan_quyet(0, "Ran 0 tests\nOK\n"), "HỎNG", "0 ca vẫn ĐẠT")
        _dc_am("luat-phan")
        _dc_duong("luat-phan")
        print("  [J2] luật phán TỪ CHỐI: thoát-0-không-ca · thoát-0-không-dấu-vết · OK-rồi-thoát-1 "
              "· 0-ca; và NHẬN ca đạt thật")

    def test_j3_dot_bien_M1_sua_tran_thi_cong_C1_phai_do(self):
        """CHỐT (a): đột biến trên CÂY SAO CHÉP, driver chạy trong TIẾN TRÌNH CON."""
        d_that = do_tran_theo_so_ban(ds_n=(1, 2))
        self.assertEqual(d_that["tran_khai"], 20, "trần khai trên cây THẬT khác 20: %s" % d_that)
        _dc_duong("dot-bien-M1")
        cay = _cay_dot_bien([("app/gioi_han.py", 'Luat("ip", 20, 300)', 'Luat("ip", 5, 300)')])
        d_bien = do_tran_theo_so_ban(ds_n=(1, 2), cay=cay)
        self.assertEqual(d_bien["tran_khai"], 5, "đột biến không vào được cây sao chép: %s" % d_bien)
        self.assertNotEqual(d_bien["theo_n"], d_that["theo_n"],
                            "sửa trần khai mà phép đo VẪN ra số cũ ⇒ C1 đọc số VIẾT CỨNG, KHÔNG có răng")
        _dc_am("dot-bien-M1")
        print("  [J3] M1 (trần 20→5 trên cây sao chép): cây thật → %s · cây đột biến → %s "
              "⇒ cổng C1 đọc trần TỪ MÃ, CÓ RĂNG" % (d_that["theo_n"], d_bien["theo_n"]))

    def test_j4_dot_bien_M2_them_ma_VTP_thi_cong_C3_phai_do(self):
        d_that = do_bang_ma_vtp()
        self.assertEqual(d_that["so_ma_chinh_thuc_biet"], 0,
                         "cây THẬT đã biết mã VTP thật (%s) — cập nhật lại §1 QA_G19.md"
                         % d_that["so_khoa_so"])
        _dc_duong("dot-bien-M2")
        cay = _cay_dot_bien([("app/trang_thai_hang.py", "VTP_MA_MOCK = {",
                              'VTP_MA_MOCK = {\n    "101": ("MOCK thu", "hoan_hang"),')])
        d_bien = do_bang_ma_vtp(cay=cay)
        self.assertEqual(d_bien["so_ma_chinh_thuc_biet"], 1,
                         "đột biến thêm mã 101 mà phép đo không thấy: %s"
                         % d_bien["so_ma_chinh_thuc_biet"])
        _dc_am("dot-bien-M2")
        print("  [J4] M2 (thêm mã 101 vào bảng VTP trên cây sao chép): cây thật → %d mã thật · "
              "cây đột biến → %d ⇒ cổng C3 đọc BẢNG TỪ MÃ, CÓ RĂNG"
              % (d_that["so_ma_chinh_thuc_biet"], d_bien["so_ma_chinh_thuc_biet"]))

    def test_j5_dot_bien_M3_cho_menu_Tab_toi_duoc_thi_cong_C5_phai_do(self):
        d_that = do_ban_phim_tinh()
        self.assertGreater(d_that["so_muc_khong_ban_phim_duoc"], 0,
                           "cây THẬT đã Tab tới được menu — cập nhật lại §1 QA_G19.md")
        _dc_duong("dot-bien-M3")
        # Đột biến phải vá CẢ HAI chỗ: khuôn menu VÀ nút Đăng xuất. Vá nửa vời thì phép đo còn
        # lại 1 mục — và đó chính là điều `D_do` dưới đây khẳng định, để ca này không thể xanh
        # nhờ một đột biến nửa vời.
        cay_nua = _cay_dot_bien([("admin/admin.js", '<a data-man="${id}">',
                                  '<a data-man="${id}" href="#" tabindex="0" role="link">')])
        d_nua = do_ban_phim_tinh(cay=cay_nua)
        self.assertEqual(d_nua["so_muc_khong_ban_phim_duoc"], 1,
                         "vá CHỈ khuôn menu mà phép đo ra %d (phải còn 1 = nút Đăng xuất) ⇒ "
                         "phép đo không tách được hai chỗ" % d_nua["so_muc_khong_ban_phim_duoc"])
        cay = _cay_dot_bien([("admin/admin.js", '<a data-man="${id}">',
                              '<a data-man="${id}" href="#" tabindex="0" role="link">'),
                             ("admin/admin.js", '<a id="nut-thoat" style="color:#fff;cursor:pointer">',
                              '<a id="nut-thoat" href="#" tabindex="0" role="link" '
                              'style="color:#fff;cursor:pointer">')])
        d_bien = do_ban_phim_tinh(cay=cay)
        self.assertEqual(d_bien["so_muc_khong_ban_phim_duoc"], 0,
                         "thêm href/tabindex/role vào CẢ HAI chỗ mà phép đo VẪN báo %d ⇒ C5 "
                         "KHÔNG có răng" % d_bien["so_muc_khong_ban_phim_duoc"])
        _dc_am("dot-bien-M3")
        print("  [J5] M3 (thêm href/tabindex/role): cây thật → %d mục không Tab tới được · vá nửa "
              "vời → %d · vá cả hai → %d ⇒ cổng C5 đọc THUỘC TÍNH TỪ MÃ, CÓ RĂNG"
              % (d_that["so_muc_khong_ban_phim_duoc"], d_nua["so_muc_khong_ban_phim_duoc"],
                 d_bien["so_muc_khong_ban_phim_duoc"]))

    def test_j6_dot_bien_M4_migration_v9_thi_cong_C6_phai_do(self):
        d_that = do_ag00()
        self.assertLess(d_that["phien_ban_schema"], 9,
                        "cây THẬT đã ở schema v%s — cập nhật lại §1 QA_G19.md"
                        % d_that["phien_ban_schema"])
        _dc_duong("dot-bien-M4")
        cay = _cay_dot_bien([("app/csdl.py", "PHIEN_BAN_SCHEMA = 8", "PHIEN_BAN_SCHEMA = 9")])
        d_bien = do_ag00(cay=cay)
        self.assertEqual(d_bien["phien_ban_schema"], 9,
                         "đột biến v8→v9 không vào được cây sao chép: %s" % d_bien)
        _dc_am("dot-bien-M4")
        # ĐỒNG THỜI chứng minh BỘ CHỌN CHẾ ĐỘ có răng: v9 ⇒ chế độ phải là "nợ ĐÓNG".
        ma, ra = _chay_con("import thu_qa_g19 as q\nprint('CHE_DO=' + ('DONG' if q.NHO_DONG else 'MO'))",
                           goc_cay=cay)
        self.assertIn("CHE_DO=DONG", ra,
                      "v9 mà bộ chọn chế độ vẫn báo nợ MỞ ⇒ chế độ tự suy KHÔNG có răng: %s" % ra[-200:])
        print("  [J6] M4 (schema v8→v9 trên cây sao chép): cây thật → v%s · cây đột biến → v%s và "
              "bộ chọn chế độ tự đổi sang nợ ĐÓNG ⇒ cổng C6 + bộ chọn chế độ CÓ RĂNG"
              % (d_that["phien_ban_schema"], d_bien["phien_ban_schema"]))


class Z_TongKet(unittest.TestCase):
    """Sổ đối chứng + vân tay cây trước/sau + cụm PostgreSQL :5432 (D-9/D-8)."""

    def test_z1_moi_nhom_phu_dinh_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertEqual(thieu, [], "nhóm có ca ÂM mà KHÔNG có đối chứng DƯƠNG: %s" % thieu)
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")
        _dc_duong("so-doi-chung")
        print("\nSỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))

    def test_z2_cay_khong_doi_trong_luot_do(self):
        sau = van_tay_cay()
        self.assertEqual(sau, VAN_TAY_LUC_NAN,
                         "CÂY ĐỔI giữa lượt đo ⇒ mọi số đo phải coi là vô hiệu")
        _dc_duong("cay-khong-doi")
        print("  [Z2] vân tay TRƯỚC = SAU = %s · HEAD=%s · CSDL tạm=%s · log=%s"
              % (sau[:16], _git("rev-parse", "HEAD").stdout.strip()[:7], _TAM_CSDL, LOG_DIR))

    def test_z3_cum_postgres_5432_khong_bi_dung(self):
        """D-8/chốt cứng: cụm `:5432` đang giữ dữ liệu dự án KHÁC — phải TRƯỚC = SAU."""
        r = subprocess.run(["lsof", "-nP", "-iTCP:5432", "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, "không đọc được trạng thái cụm :5432 (lsof)")
        dong = [d for d in r.stdout.splitlines()[1:] if d.strip()]
        so_tien_trinh = len(dong)
        _dc_duong("5432-khong-dung")
        print("  [Z3] cụm :5432 có %d tiến trình đang nghe · bộ thử này CHỈ dùng cụm riêng "
              "(bộ thử PostgreSQL tự dựng ở 55432, và TỪ CHỐI cổng 5432)" % so_tien_trinh)

    def test_z4_pham_vi_da_do_va_cai_nam_ngoai(self):
        _dc_duong("pham-vi")
        print("\n  [Z4] PHẠM VI ĐÃ ĐO: %s %s · python %s · SQLite %s"
              % (os.uname().sysname, os.uname().machine,
                 ".".join(map(str, sys.version_info[:3])), __import__("sqlite3").sqlite_version))
        print("       CHẾ ĐỘ: nợ %s — %s" % ("ĐÓNG" if NHO_DONG else "MỞ", LY_DO_CHE_DO))
        print("       LÀN NẶNG (hồi quy + tầng 3 Chromium): %s"
              % ("BẬT" if DAY_DU else "TẮT — bật bằng VIP_G19_DAY_DU=1"))
        print("       NGOÀI PHẠM VI: gọi API hãng (kể cả sandbox — V-G09-01/V-13906-05 CHƯA CẤP) ·"
              " TLS thật · deploy/push/tunnel · VPS · PostgreSQL production (D-8) · Safari/Firefox ·"
              " trình đọc màn hình · dữ liệu lớn · credentials thật")


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

# Chọn chế độ Ở ĐÂY, sau khi mọi hàm đã được định nghĩa: `_chon_che_do()` gọi driver trong
# tiến trình con, mà driver đó dùng `_chay_con`. Đặt sớm hơn sẽ NameError lúc import.
NHO_DONG, LY_DO_CHE_DO = _chon_che_do()

if __name__ == "__main__":
    print("NỀN ĐO: HEAD=%s · ghim=%s" % (_git("rev-parse", "HEAD").stdout.strip(), HEAD_GHIM))
    print("PHẠM VI: chỉ loopback + CSDL tạm · adapter MOCK · cổng hãng KHOÁ "
          "· cụm PostgreSQL :5432 CHẶN CỨNG (chỉ cụm riêng 55432)")
    print(_nhac())
    print("LÀN NẶNG: %s" % ("BẬT" if DAY_DU else "TẮT (VIP_G19_DAY_DU=1 để bật)"))
    unittest.main(verbosity=2)
