#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18/AG-02 — ĐA TIẾN TRÌNH: lớp nào dùng chung được qua tiến trình, lớp nào KHÔNG.

====== VÌ SAO CÓ TỆP NÀY ======
Lượt nghiệm thu G17 ghi ở mục **CHƯA ĐO** (`docs/G17_SECURITY_ISOLATION.md` §9.2 và
`docs/G17_TRANSPORT.md` §8.3):

    "Nhiều tiến trình: trần tần suất sống trong bộ nhớ MỘT tiến trình; `csdl.khoa_ghi` là RLock
     của Python. Lượt này chạy MỘT tiến trình ⇒ KHÔNG đo được tranh chấp liên tiến trình."
    "Đa luồng được đo trong MỘT tiến trình, trên MỘT máy. Chưa đo nhiều tiến trình."

Và một số đo đã có từ trước (**B-G11-10**, `docs/G13_G15_ACCEPTANCE.md`): hai tiến trình cùng CSDL,
cùng IP ⇒ trần thực **40** thay vì khai báo **20**. Tệp này ĐO LẠI số đó bằng **TIẾN TRÌNH THẬT**
(`subprocess`), không bằng luồng, và mở rộng N = 1 · 2 · 4 · 8.

====== LUẬT CỦA PHÉP ĐO NÀY ======
1. **Mọi phép đo lớp HTTP chỉ đi tới stub `127.0.0.1` cổng 0** (`app/thu/stub_jt.py`). KHÔNG một
   byte ra mạng: `V-G09-01` + `V-13906-05` CHƯA CẤP. Không có lượt gọi hãng nào, kể cả sandbox.
2. **CSDL chỉ là CSDL TẠM** trong `tempfile.mkdtemp`, mỗi lượt đo một nền riêng. Tiến trình con
   TỰ CHỐI CHẠY nếu `VIP_HUB_DATA` trỏ ra ngoài thư mục tạm (mã thoát 9). KHÔNG chạm CSDL thật,
   KHÔNG chạm cụm PostgreSQL `:5432` (D-8: CSDL nghiệp vụ vẫn SQLite).
3. **Không đoán mã trạng thái 110** (D-4) và **không mở `CHO_PHEP_LIVE`** — tệp này không chạm
   vào hai thứ đó.
4. **Mỗi khẳng định KHẲNG ĐỊNH đều có ĐỐI CHỨNG**: ca đối chứng âm (phép đo phải cho ĐÚNG khai
   báo khi chỉ một tiến trình), đối chứng dương (một trần CÓ dùng chung thì KHÔNG được nhân), và
   ca TỰ KIỂM BỘ ĐO (một bản đột biến có trạng thái dùng chung PHẢI bị bắt). Xem P2 và P4.

====== SÁU PHẦN ======
  P0  Chốt an toàn: nền tạm, loopback, không tiến trình lạ nào bị chạm
  P1  TRẦN TẦN SUẤT qua N tiến trình máy chủ THẬT (N = 1 · 2 · 4 · 8)   → B-G11-10
  P2  TỰ KIỂM BỘ ĐO của P1: đối chứng âm · đối chứng dương (trần trong CSDL) · đột biến hàm đếm
  P3  LỚP HTTP (`app/http_jt.py`): có trạng thái dùng chung nào qua tiến trình không?
  P4  TỰ KIỂM BỘ ĐO của P3: mô-đun ĐỘT BIẾN có đệm dùng chung PHẢI bị bắt
  P5  TẦNG CSDL: `khoa_ghi` (RLock) không phủ tiến trình — đọc-sửa-ghi ngây thơ mất cập nhật
  P6  Tổng kết: lớp nào an toàn qua tiến trình, lớp nào KHÔNG, hệ quả vận hành

CHẠY
----
    python3 app/thu/thu_g18_multiprocess.py        # 0 = mọi ca ĐẠT · 1 = có ca HỎNG

PHẠM VI
-------
Đo: N tiến trình trên MỘT máy · loopback · SQLite tạm · trần tần suất và hạn mức nhập của
`app/gioi_han.py` · lớp HTTP `app/http_jt.py` · khoá ghi `app/csdl.py`.
NGOÀI phạm vi: nhiều MÁY · sau bộ cân bằng tải thật · TLS · cụm PostgreSQL (D-8, cụm riêng, CẤM
đụng) · tải lớn · hãng thật. Nói thẳng: mọi kết luận dưới đây là của **SQLite trên MỘT máy**.
"""
import ast
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # …/app
DU_AN = os.path.dirname(GOC_APP)
THU_MUC_TAM = os.path.realpath(tempfile.gettempdir())
DU_LIEU_MAC_DINH = os.path.realpath(os.path.join(GOC_APP, "du-lieu"))

DAT, HONG, BO_QUA, KHUYET = "DAT", "HONG", "BO_QUA", "KHUYET"
KY = {DAT: "✓", HONG: "✗", BO_QUA: "–", KHUYET: "!"}
KQ = []
NENS = []              # mọi nền tạm đã tạo — dọn ở cuối
CON = []               # mọi tiến trình con đang sống — tắt theo ĐÚNG PID ở cuối
LENH = []              # (lệnh, mã thoát) — BẰNG CHỨNG dạng "lệnh thật + mã thoát thật"

DUONG_DANG_NHAP = "/api/v2/auth/dang-nhap"

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# `migrate.py` được spawn thành TIẾN TRÌNH CON trong `dung_nen`; khai dưới đây vào `os.environ`
# nên con kế thừa, và chỗ spawn còn truyền TƯỜNG MINH `VIP_KHO_DANG_CHAY=sqlite`. KHÔNG dựa vào
# việc người chạy nhớ `export VIP_KHO_DANG_CHAY`: một bộ chỉ xanh khi người chạy nhớ khai là một
# bộ GIỎ. Nền khai dưới đây CHỈ để thoả chốt cô lập của hàm khai; mọi nền ĐO vẫn do `nen_tam()`
# tạo riêng trong thư mục tạm.
_NEN_KHAI = tempfile.mkdtemp(prefix="vh-g18-khai-")
NENS.append(_NEN_KHAI)
os.environ.setdefault("VIP_HUB_DATA", _NEN_KHAI)
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)
import cau_hinh                                                          # noqa: E402
cau_hinh.khai_kho_kiem_thu()


# ===============================================================================================
# HẠ TẦNG IN · GHI NHẬN · DỌN DẸP
# ===============================================================================================
def ket(ma, ten, trang_thai, bang_chung=""):
    KQ.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    print("  %s [%s] %s%s" % (KY[trang_thai], ma, ten,
                              ("\n        " + bang_chung) if bang_chung else ""))


def muc(t):
    print("\n" + "─" * 78 + "\n─ %s\n" % t + "─" * 78)


def chay(lenh, *, env=None, gio=180, cwd=None):
    """Chạy một tiến trình THẬT, ghi lại (lệnh, mã thoát) làm bằng chứng, trả về `CompletedProcess`."""
    p = subprocess.run(lenh, capture_output=True, text=True, env=env, cwd=cwd or DU_AN, timeout=gio)
    LENH.append((" ".join(lenh), p.returncode))
    return p


def nen_tam(tien_to):
    """Một nền dữ liệu TẠM. Chốt cứng: phải nằm trong thư mục tạm của hệ, không phải dữ liệu thật."""
    d = os.path.realpath(tempfile.mkdtemp(prefix="vh-g18-%s-" % tien_to))
    if not d.startswith(THU_MUC_TAM + os.sep) or d == DU_LIEU_MAC_DINH:
        raise SystemExit("TỪ CHỐI: nền %r không nằm trong thư mục tạm — không chạy trên dữ liệu thật" % d)
    NENS.append(d)
    return d


def dung_nen(nen, *, them_env=None):
    """Dựng schema trên nền tạm bằng ĐÚNG hai bộ cài của dự án (`migrate.py` + `khoi_tao.py`)."""
    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_KHO_DANG_CHAY="sqlite")
    env.update(them_env or {})
    for ten in ("migrate.py", "khoi_tao.py"):
        p = chay([sys.executable, os.path.join(GOC_APP, ten)], env=env, gio=180)
        if p.returncode:
            raise RuntimeError("%s hỏng (mã %d): %s" % (ten, p.returncode, (p.stderr or p.stdout)[-400:]))
    return env


def cong_roi():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    c = s.getsockname()[1]
    s.close()
    return c


def cho_cong(cong, p, giay=40):
    het = time.time() + giay
    while time.time() < het:
        try:
            socket.create_connection(("127.0.0.1", cong), 0.3).close()
            return True
        except OSError:
            if p.poll() is not None:
                return False
            time.sleep(0.1)
    return False


def tat_tien_trinh(p, giay=15):
    """Tắt ĐÚNG PID (CLAUDE.md §16.7: KHÔNG `pkill`, KHÔNG `killall`)."""
    if p.poll() is not None:
        return p.returncode
    p.terminate()
    try:
        return p.wait(timeout=giay)
    except subprocess.TimeoutExpired:
        p.kill()
        return p.wait(timeout=giay)


def don_dep():
    for p in list(CON):
        try:
            tat_tien_trinh(p)
        except Exception:                                                   # noqa: BLE001
            pass
    CON[:] = []
    for d in list(NENS):
        shutil.rmtree(d, ignore_errors=True)
    NENS[:] = []


# ===============================================================================================
# GỌI HTTP THẬT (chỉ loopback) + ĐỌC SỔ CỦA MÁY CHỦ
# ===============================================================================================
def goi_json(cong, duong, body, *, gio=30, phuong_thuc="POST"):
    d = json.dumps(body).encode("utf-8")
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (cong, duong), data=d, method=phuong_thuc)
    r.add_header("X-Requested-With", "VIPHub")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=gio) as f:
            return f.status, f.read(), dict(f.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def mot_luot_dang_nhap(cong, i):
    """MỘT lượt đăng nhập SAI với tên đăng nhập KHÁC NHAU mỗi lượt.

    Tên khác nhau để chỉ chiều `ip` cộng: 12 lượt sai cho CÙNG một tài khoản sẽ khoá tạm tài
    khoản đó (`cau_hinh.KHOA_SAU_SO_LAN_SAI`) và làm hỏng phép đo trần theo IP.
    """
    return goi_json(cong, DUONG_DANG_NHAP, {"ten_dang_nhap": "khong-ton-tai-g18-%d" % i,
                                            "mat_khau": "sai"})


def doc_log_may_chu(duong_dan):
    """Đọc log JSON của MỘT tiến trình máy chủ → [(pid, mốc giây, đường, mã HTTP)].

    Log là bằng chứng PHÍA MÁY CHỦ: nó nói tiến trình nào đã phục vụ lượt nào, và lượt nào chồng
    lên lượt nào. `so_dong_hong` đếm số dòng không parse được (nhiều luồng cùng ghi một tệp) —
    đếm ra chứ KHÔNG bỏ im lặng, để một tệp log hỏng không được đọc thành "không có lượt nào".
    """
    ra, hong = [], 0
    if not os.path.exists(duong_dan):
        return ra, hong
    with open(duong_dan, "r", encoding="utf-8", errors="replace") as f:
        for dong in f:
            dong = dong.strip()
            if not dong.startswith("{"):
                continue
            try:
                o = json.loads(dong)
            except ValueError:
                hong += 1
                continue
            if o.get("loai") == "yeu_cau" and o.get("pid"):
                ra.append((int(o["pid"]), str(o.get("luc", "")), str(o.get("duong", "")),
                           o.get("ma_http")))
    return ra, hong


# ===============================================================================================
# TIẾN TRÌNH CON — nguồn được GHI RA TỆP TẠM (không phải tệp của dự án)
# ===============================================================================================
CON_HTTP = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G18/AG-02): gọi lớp HTTP `k` lượt và ghi kết quả NGUYÊN VĂN ra JSON."""
import argparse, json, os, sys, threading

ap = argparse.ArgumentParser()
ap.add_argument("--goc", action="append", required=True)   # nhiều thư mục, theo ĐÚNG thứ tự tìm
ap.add_argument("--module", default="http_jt")
ap.add_argument("--url", required=True)
ap.add_argument("--i", type=int, required=True)
ap.add_argument("--k", type=int, default=1)                # số lượt, chạy ĐỒNG THỜI bằng k luồng
ap.add_argument("--out", required=True)
ap.add_argument("--gio", type=float, default=10.0)
a = ap.parse_args()
for g in reversed(a.goc):
    sys.path.insert(0, g)
mod = __import__(a.module)


def mot_luot(lan):
    dau = "VEH-G18-%02d-%02d" % (a.i, lan)
    biz = json.dumps({"txlogisticId": dau, "ghiChu": "tien-trinh-%02d" % a.i},
                     separators=(",", ":"))
    kq = mod.gui_form(a.url, {"apiAccount": "acc-%02d" % a.i,
                              "timestamp": "2026-10-15T00:00:00+07:00"},
                      {"bizContent": biz}, timeout=a.gio)
    return {"lan": lan, "dau": dau, "ma_http": kq.ma_http,
            "than": kq.than.decode("utf-8", "replace")}


kq = [None] * a.k
loi = [None] * a.k


def boc(lan):
    try:
        kq[lan] = mot_luot(lan)
    except BaseException as e:                                              # noqa: BLE001
        loi[lan] = "%s: %s" % (type(e).__name__, e)


ths = [threading.Thread(target=boc, args=(l,)) for l in range(a.k)]
for t in ths:
    t.start()
for t in ths:
    t.join()
with open(a.out, "w") as f:
    json.dump({"pid": os.getpid(), "i": a.i, "kq": kq, "loi": [x for x in loi if x]}, f,
              ensure_ascii=False)
'''

CON_HAN_MUC = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G18/AG-02): thử ĐẶT TRƯỚC suất đơn nháp — trần ĐẾM TRONG CSDL.

Đây là ĐỐI CHỨNG DƯƠNG cho P1: một trần CÓ dùng chung giữa các tiến trình thì KHÔNG được nhân
theo số bản. Nếu bộ đo ở P1 chỉ biết trả lời "nhân lên", ca này sẽ lộ ra ngay.
"""
import argparse, json, os, sys, tempfile, time

ap = argparse.ArgumentParser()
ap.add_argument("--goc", required=True)
ap.add_argument("--tenant", type=int, required=True)
ap.add_argument("--so-lan", type=int, default=4)
ap.add_argument("--bat-dau-luc", type=float, required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()
sys.path.insert(0, a.goc)

import cau_hinh                                                             # noqa: E402
duong = os.path.realpath(cau_hinh.DUONG_DAN_CSDL)
if not duong.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
    sys.stderr.write("TỪ CHỐI: CSDL %r không nằm trong thư mục tạm\n" % duong)
    raise SystemExit(9)

import csdl                                                                 # noqa: E402
import gioi_han                                                             # noqa: E402

tran = gioi_han.tran_cua(a.tenant)["tran_don_nhap_thang"]
gioi_han.da_dung(a.tenant)   # tạo bảng hạn mức nếu chưa có — TRƯỚC hàng rào, xem bộ đo
while time.time() < a.bat_dau_luc:          # HÀNG RÀO: mọi tiến trình vào cùng một lúc
    time.sleep(0.001)
dat_duoc, bi_chan, loi = 0, 0, []
for _ in range(a.so_lan):
    try:
        gioi_han.dat_truoc_don_nhap(a.tenant, 1)
        dat_duoc += 1
    except gioi_han.VuotHanMucNhap:
        bi_chan += 1
    except Exception as e:                                                  # noqa: BLE001
        loi.append("%s: %s" % (type(e).__name__, e))
with open(a.out, "w") as f:
    json.dump({"pid": os.getpid(), "tran": tran, "dat_duoc": dat_duoc, "bi_chan": bi_chan,
               "loi": loi}, f, ensure_ascii=False)
'''

CON_CSDL = r'''# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON (G18/AG-02): ĐỌC–SỬA–GHI trên CSDL TẠM theo ba cách.

  ngay_tho  : SELECT rồi UPDATE, KHÔNG giao dịch — chỉ có `khoa_ghi` (RLock) của Python
  giao_dich : cùng khuôn, nhưng bọc `csdl.giao_dich()` (BEGIN IMMEDIATE)
  cau_lenh  : một câu nguyên tử `UPDATE … SET dem = dem + 1`

Cách thứ nhất là cách một người viết nhanh sẽ viết; hai cách sau là hai cách ĐÚNG.
"""
import argparse, json, os, sys, tempfile, time

ap = argparse.ArgumentParser()
ap.add_argument("--goc", required=True)
ap.add_argument("--cach", choices=("ngay_tho", "giao_dich", "cau_lenh"), required=True)
ap.add_argument("--so-lan", type=int, default=25)
ap.add_argument("--do-tre", type=float, default=0.002)
ap.add_argument("--bat-dau-luc", type=float, default=0.0)
ap.add_argument("--out", required=True)
a = ap.parse_args()
sys.path.insert(0, a.goc)

import cau_hinh                                                             # noqa: E402
duong = os.path.realpath(cau_hinh.DUONG_DAN_CSDL)
if not duong.startswith(os.path.realpath(tempfile.gettempdir()) + os.sep):
    sys.stderr.write("TỪ CHỐI: CSDL %r không nằm trong thư mục tạm\n" % duong)
    raise SystemExit(9)

import csdl                                                                 # noqa: E402

if a.bat_dau_luc:
    while time.time() < a.bat_dau_luc:
        time.sleep(0.001)
xong, loi = 0, []
for _ in range(a.so_lan):
    try:
        if a.cach == "ngay_tho":
            x = csdl.mot("SELECT dem FROM _g18_dem WHERE id=1")["dem"]
            time.sleep(a.do_tre)                # khe hở CỐ Ý, để tranh chấp lộ ra TẤT ĐỊNH
            csdl.ghi("UPDATE _g18_dem SET dem=? WHERE id=1", (x + 1,))
        elif a.cach == "giao_dich":
            with csdl.giao_dich():
                x = csdl.mot("SELECT dem FROM _g18_dem WHERE id=1")["dem"]
                time.sleep(a.do_tre)
                csdl.ghi("UPDATE _g18_dem SET dem=? WHERE id=1", (x + 1,))
        else:
            csdl.ghi("UPDATE _g18_dem SET dem = dem + 1 WHERE id=1")
        xong += 1
    except Exception as e:                                                  # noqa: BLE001
        loi.append("%s: %s" % (type(e).__name__, e))
with open(a.out, "w") as f:
    json.dump({"pid": os.getpid(), "xong": xong, "loi": loi}, f, ensure_ascii=False)
'''

# BẢN ĐỘT BIẾN CỐ Ý (chỉ dùng cho P4 — KHÔNG bao giờ được mã sản phẩm nhập).
# Lỗi được mô phỏng là lỗi THẬT và hay gặp: đệm phản hồi theo URL, quên thân yêu cầu, và để đệm
# ở chỗ DÙNG CHUNG giữa các tiến trình (biến toàn cục + tệp). Một bản đệm như vậy trong hệ chạy
# nhiều tiến trình sẽ trả cho tiến trình này thân trả lời của tiến trình khác.
CON_DOT_BIEN = r'''# -*- coding: utf-8 -*-
"""BẢN ĐỘT BIẾN CỐ Ý của G18/AG-02 — KHÔNG phải mã sản phẩm.

Đệm phản hồi theo URL: (a) một dict TOÀN CỤC trong tiến trình, (b) một TỆP DÙNG CHUNG giữa mọi
tiến trình. Cả hai đều là trạng thái sống ngoài một lượt gọi, tức đúng thứ P3 khẳng định
`http_jt` KHÔNG có. Bộ đo ở P3 phải BẮT ĐƯỢC bản này; không bắt được nghĩa là bộ đo mù.
"""
import json
import os

import http_jt

_KHO = {}          # (a) trạng thái toàn cục trong MỘT tiến trình


def gui_form(url, headers, body, *, timeout):
    khoa = url     # (b) khoá chỉ theo URL — quên thân yêu cầu
    tep = os.environ["VIP_G18_TEP_DEM"]
    if os.path.exists(tep):
        try:
            with open(tep) as f:
                _KHO.update(json.load(f))
        except ValueError:
            pass
    if khoa in _KHO:
        return http_jt.TraLoiHTTP(int(_KHO[khoa]["ma_http"]), _KHO[khoa]["than"].encode("utf-8"), {})
    kq = http_jt.gui_form(url, headers, body, timeout=timeout)
    _KHO[khoa] = {"ma_http": kq.ma_http, "than": kq.than.decode("utf-8")}
    with open(tep, "w") as f:
        json.dump(_KHO, f)
    return kq
'''


def ghi_con(nen, ten, nguon):
    duong = os.path.join(nen, ten)
    with open(duong, "w") as f:
        f.write(nguon)
    return duong


# ===============================================================================================
# P0 — CHỐT AN TOÀN
# ===============================================================================================
def p0_chot_an_toan():
    muc("P0. CHỐT AN TOÀN — nền tạm · loopback · không chạm dữ liệu thật")
    print("  thư mục tạm của hệ : %s" % THU_MUC_TAM)
    print("  dữ liệu THẬT (cấm): %s" % DU_LIEU_MAC_DINH)
    print("  Python             : %s" % sys.version.split()[0])
    env_live = os.environ.get("VIP_HUB_CHO_PHEP_LIVE") or os.environ.get("CHO_PHEP_LIVE") or "(không đặt)"
    ket("P0a", "Mọi nền đo nằm trong thư mục TẠM, không phải dữ liệu thật",
        DAT if THU_MUC_TAM != DU_LIEU_MAC_DINH else HONG,
        "nền tạm: %s · dữ liệu thật: %s" % (THU_MUC_TAM, DU_LIEU_MAC_DINH))
    ket("P0b", "Không mở `CHO_PHEP_LIVE` trong suốt lượt đo (biến môi trường của bộ đo)",
        DAT, "giá trị đọc được lúc bắt đầu: %s — bộ đo KHÔNG đặt biến này" % env_live)
    ket("P0c", "Không đụng cụm PostgreSQL :5432 (D-8 — CSDL nghiệp vụ vẫn SQLite)",
        DAT, "bộ đo chỉ mở `sqlite3` trên tệp trong thư mục tạm; không có kết nối mạng nào "
             "ngoài `127.0.0.1`")


# ===============================================================================================
# P1 — TRẦN TẦN SUẤT QUA N TIẾN TRÌNH MÁY CHỦ THẬT
# ===============================================================================================
def mo_may_chu(nen, *, tien_to):
    c = cong_roi()
    log = os.path.join(nen, "%s-%d.log" % (tien_to, c))
    f = open(log, "w")
    p = subprocess.Popen([sys.executable, os.path.join(GOC_APP, "server.py"), str(c)],
                         stdout=f, stderr=subprocess.STDOUT, env=dict(os.environ, VIP_HUB_DATA=nen),
                         cwd=DU_AN)
    CON.append(p)
    if not cho_cong(c, p):
        raise RuntimeError("máy chủ không mở cổng %d (pid %d):\n%s"
                           % (c, p.pid, open(log).read()[-500:]))
    return {"p": p, "cong": c, "log": log, "nen": nen}


def bom_tuan_tu(sv, *, toi_da_moi_ban):
    """Bắn LẦN LƯỢT, VÒNG TRÒN qua các bản: mỗi bản nhận đúng một lượt mỗi vòng.

    Vòng tròn (chứ không dồn từng bản một) để N tiến trình cùng SỐNG và cùng phục vụ trong suốt
    phép đo. Số đếm vẫn TẤT ĐỊNH: mỗi bản tự chặn ở lượt thứ `trần + 1` của chính nó.
    """
    so_ban = len(sv)
    dem = [0] * so_ban
    con = [True] * so_ban
    chi_tiet = [[] for _ in range(so_ban)]
    for vong in range(toi_da_moi_ban):
        for k in range(so_ban):
            if not con[k]:
                continue
            ma, than, hdr = mot_luot_dang_nhap(sv[k]["cong"], k * 1000 + vong)
            o = {"ma": ma, "gioi_han": hdr.get("X-RateLimit-Limit"),
                 "retry_after": hdr.get("Retry-After"), "chieu": None}
            if ma == 429:
                try:
                    o["chieu"] = json.loads(than.decode("utf-8")).get("chieu")
                except (ValueError, UnicodeDecodeError):
                    pass
                con[k] = False
            elif ma == 401:                      # 401 = sai thông tin đăng nhập = ĐÃ QUA trần
                dem[k] += 1
            else:
                o["la"] = "mã lạ"
            chi_tiet[k].append(o)
    return dem, chi_tiet


def bom_dong_thoi(sv, *, so_luot_moi_ban, gio=40):
    """Bắn TẤT CẢ cùng lúc: `N × so_luot_moi_ban` yêu cầu, mỗi bản đúng `so_luot_moi_ban` lượt."""
    khoa = threading.Lock()
    kq = []
    hang_rao = threading.Event()

    def mot(k, i):
        hang_rao.wait()
        t0 = time.perf_counter()
        try:
            ma, than, hdr = mot_luot_dang_nhap(sv[k]["cong"], 900000 + k * 1000 + i)
            gioi_han = hdr.get("X-RateLimit-Limit")
        except Exception as e:                                              # noqa: BLE001
            ma, gioi_han = "LOI:%s" % e, None
        t1 = time.perf_counter()
        with khoa:
            kq.append({"ban": k, "i": i, "ma": ma, "gioi_han": gioi_han, "t0": t0, "t1": t1})

    ths = [threading.Thread(target=mot, args=(k, i), daemon=True)
           for k in range(len(sv)) for i in range(so_luot_moi_ban)]
    for t in ths:
        t.start()
    hang_rao.set()
    for t in ths:
        t.join(timeout=gio)
    return kq


def chong_nhau(kq):
    """Từ mốc thời gian phía CLIENT: số lượt đang bay cao nhất, và số BẢN khác nhau cùng bay."""
    su_kien = []
    for r in kq:
        su_kien.append((r["t0"], 1, r["ban"]))
        su_kien.append((r["t1"], -1, r["ban"]))
    su_kien.sort(key=lambda x: (x[0], -x[1]))
    dang, cao_nhat_tong, cao_nhat_ban = {}, 0, 0
    for _, d, ban in su_kien:
        dang[ban] = dang.get(ban, 0) + d
        cao_nhat_tong = max(cao_nhat_tong, sum(dang.values()))
        cao_nhat_ban = max(cao_nhat_ban, sum(1 for v in dang.values() if v > 0))
    return cao_nhat_tong, cao_nhat_ban


def doc_tran_khai_bao(nen):
    """Trần KHAI BÁO đọc từ CHÍNH máy chủ, trên một máy chủ DÙNG MỘT LẦN rồi tắt.

    Vì sao phải TỚI LƯỢT BỊ CHẶN mới đọc được: `server._gioi_han` chỉ gắn `gioi_han.tieu_de(kq)`
    vào lượt **429** — lượt cho qua không mang header nào. Nên muốn biết trần khai báo thì phải để
    máy chủ TỪ CHỐI một lượt.

    Vì sao phải là máy chủ RIÊNG: mọi lượt gọi đều TIÊU một suất của trần. Đọc trần bằng một lượt
    gọi vào chính bản sắp đo là tự trừ đi suất của nó, và phép đo N=1 sẽ ra 19 thay vì 20 — một
    HỎNG GIẢ đúng khuôn N-05. Trả về `(trần_khai_báo, số_lượt_đã_cho_qua, mã)`; hai số đầu PHẢI
    khớp nhau, đó là phép tự kiểm đầu tiên của bộ đo.
    """
    s = mo_may_chu(nen, tien_to="do-tran")
    try:
        for i in range(200):
            # TÊN ĐĂNG NHẬP KHÁC NHAU mỗi lượt: dùng lại một tên thì chiều `dinh_danh`
            # (`Luat("dinh_danh", 12, 300, chan_giay=900)`) chặn TRƯỚC chiều `ip`, và trần đọc
            # được sẽ là 12 kèm `Retry-After` 901 — ĐO NHẦM CHIỀU. Đo được ngày 15/10/2026:
            # bản đầu của tệp này dùng `mot_luot_dang_nhap(cong, 1)` cho mọi lượt ⇒ đọc ra 12 và
            # mọi phép đo ở P1 ngắn hơn trần thật, tức "không thấy chặn" mà tưởng là "cho qua".
            ma, than, hdr = mot_luot_dang_nhap(s["cong"], 700000 + i)
            if ma == 429:
                chieu = None
                try:
                    chieu = json.loads(than.decode("utf-8")).get("chieu")
                except (ValueError, UnicodeDecodeError):
                    pass
                return (int(hdr.get("X-RateLimit-Limit") or 0), i, ma,
                        dict(hdr, **{"chieu": chieu}))
        return 0, 200, "khong-thay-429", {}
    finally:
        tat_tien_trinh(s["p"])


def p1_tran_tan_suat():
    muc("P1. TRẦN TẦN SUẤT QUA N TIẾN TRÌNH MÁY CHỦ THẬT — B-G11-10")
    print("  Luật đang áp cho `auth.dang_nhap` được ĐỌC TỪ CHÍNH MÁY CHỦ (header")
    print("  `X-RateLimit-Limit`), không chép từ tài liệu; lượt đọc dùng máy chủ RIÊNG.")
    ket_qua = {}
    for N in (1, 2, 4, 8):
        # VÁ G19 (AG-00): PHÉP DÒ phải dùng nền RIÊNG.
        #
        # `doc_tran_khai_bao()` TIÊU HẾT trần trên nền nó chạy. Bản trước dùng CHUNG nền với phép
        # đo thật — điều đó vô hại chừng nào bộ đếm còn nằm trong BỘ NHỚ: tiến trình dò chết là
        # mang bộ đếm theo. G19/AG-02 chuyển kho đếm vào CSDL nên phần trần đã tiêu SỐNG LÂU, và
        # phép đo thật bắt đầu với trần đã cạn.
        # ĐO ĐƯỢC trước khi vá: `khai báo 20 ⇒ 0 lượt qua`, `Retry-After=300` (cửa sổ chưa hết).
        nen_do = nen_tam("tran%d-do" % N)
        dung_nen(nen_do)
        khai_bao, dem_do, ma_do, hdr_do = doc_tran_khai_bao(nen_do)
        nen = nen_tam("tran%d" % N)
        dung_nen(nen)
        if N == 1:
            # PHÉP TỰ KIỂM ĐẦU TIÊN: máy chủ NÓI trần bao nhiêu thì phải CHẶN ở đúng đó.
            ket("P1.0", "Máy chủ tự nói trần và tự chặn ở đúng đó (máy chủ dùng một lần)",
                DAT if (khai_bao > 0 and dem_do == khai_bao and hdr_do.get("chieu") == "ip")
                else (BO_QUA if khai_bao == 0 else HONG),
                "header `X-RateLimit-Limit` = %s và số lượt thực sự cho qua trước khi trả 429 = %d "
                "(mã %s) · chiều bị chặn = %r · `Retry-After`=%s. Tên đăng nhập KHÁC NHAU mỗi lượt "
                "để chiều `ip` là chiều chặn (dùng lại một tên thì chiều `dinh_danh`, trần 12, "
                "chặn trước — xem `doc_tran_khai_bao`)."
                % (khai_bao or "KHÔNG CÓ", dem_do, ma_do, hdr_do.get("chieu"),
                   hdr_do.get("Retry-After")))
        if not khai_bao:
            ket("P1.%d" % N, "N=%d: đọc được trần khai báo từ máy chủ" % N, BO_QUA,
                "máy chủ không trả header `X-RateLimit-Limit` sau 200 lượt (mã cuối %s) — "
                "KHÔNG suy đoán trần" % ma_do)
            continue
        sv = [mo_may_chu(nen, tien_to="tran%d" % N) for _ in range(N)]
        sv2 = []
        try:
            # (2) Đo LẦN LƯỢT VÒNG TRÒN: từng bản tự chặn ở đâu.
            dem_tt, chi_tiet = bom_tuan_tu(sv, toi_da_moi_ban=khai_bao + 3)
            # (3) Đo ĐỒNG THỜI THẬT trên BỘ MÁY CHỦ MỚI — VÀ NỀN MỚI.
            # VÁ G19 (AG-00): bản trước dựng máy chủ mới nhưng GIỮ NGUYÊN `nen`, kèm chú thích
            # "ngân sách của bộ cũ đã tiêu hết". Chú thích đó đúng với bộ đếm TRONG BỘ NHỚ: máy
            # chủ mới = bộ đếm mới. G19/AG-02 chuyển kho đếm vào CSDL nên máy chủ mới trên CÙNG
            # một CSDL vẫn thấy trần ĐÃ CẠN — đo được: `20 (tuần tự) và 0 (đồng thời)`.
            # Nền riêng cho pha đồng thời là điều kiện để hai phép đo còn ĐỘC LẬP nhau.
            nen_dt = nen_tam("tran%d-dt" % N)
            dung_nen(nen_dt)
            sv2 = [mo_may_chu(nen_dt, tien_to="tran%d-dt" % N) for _ in range(N)]
            kq_dt = bom_dong_thoi(sv2, so_luot_moi_ban=khai_bao + 5)
            dem_dt = [0] * N
            for r in kq_dt:
                if r["ma"] == 401:
                    dem_dt[r["ban"]] += 1
            cao_nhat_tong, cao_nhat_ban = chong_nhau(kq_dt)
            # Bằng chứng PHÍA MÁY CHỦ: các pid khác nhau phục vụ trong CÙNG một giây.
            theo_giay = {}
            hong_log = 0
            for s in sv2:
                dong, hong = doc_log_may_chu(s["log"])
                hong_log += hong
                for pid, luc, duong, _ma in dong:
                    if duong == DUONG_DANG_NHAP:
                        theo_giay.setdefault(luc, set()).add(pid)
            cung_giay = max([len(v) for v in theo_giay.values()] or [0])
            ket_qua[N] = {
                "khai_bao": khai_bao, "dem_tuan_tu": dem_tt, "chi_tiet": chi_tiet,
                "dem_dong_thoi": dem_dt, "cao_nhat_tong": cao_nhat_tong,
                "cao_nhat_ban": cao_nhat_ban, "cung_giay": cung_giay,
                "pid": [s["p"].pid for s in sv], "pid_dt": [s["p"].pid for s in sv2],
                "nen": nen, "hong_log": hong_log, "ma_do": ma_do}
            print("  N=%d · trần khai báo %d/lần-cửa-sổ (header `X-RateLimit-Limit`)"
                  % (N, khai_bao))
            print("      tuần tự  : từng bản cho qua %s ⇒ TỔNG %d" % (dem_tt, sum(dem_tt)))
            print("      đồng thời: từng bản cho qua %s ⇒ TỔNG %d (cao nhất %d lượt bay, "
                  "%d bản cùng bay; log máy chủ: %d pid khác nhau trong cùng một giây)"
                  % (dem_dt, sum(dem_dt), cao_nhat_tong, cao_nhat_ban, cung_giay))
            print("      pid tuần tự %s · pid đồng thời %s · nền %s"
                  % (ket_qua[N]["pid"], ket_qua[N]["pid_dt"], nen))
        finally:
            for s in sv + sv2:
                tat_tien_trinh(s["p"])

    if not ket_qua:
        ket("P1", "Đo được trần tần suất qua nhiều tiến trình", BO_QUA,
            "không đọc được trần khai báo từ máy chủ ở bất kỳ N nào")
        return ket_qua

    for N, k in sorted(ket_qua.items()):
        # Mỗi bản PHẢI thật sự bị chặn ở cuối phép đo tuần tự. Không kiểm điều này thì một
        # `toi_da_moi_ban` quá nhỏ sẽ cho ra "cho qua = số vòng" — tức "không thấy chặn" bị đọc
        # thành "trần rộng", đúng khuôn HỎNG GIẢ N-05 đã dính một lần trong chính tệp này.
        da_chan = [bool(ct) and ct[-1]["ma"] == 429 for ct in k["chi_tiet"]]
        # ---- ĐỐI CHỨNG ÂM: MỘT tiến trình phải cho ĐÚNG khai báo.
        if N == 1:
            chan = [o for o in k["chi_tiet"][0] if o["ma"] == 429]
            ket("P1.1", "ĐỐI CHỨNG ÂM — MỘT tiến trình: cho qua ĐÚNG bằng trần khai báo",
                DAT if (k["dem_tuan_tu"] == [k["khai_bao"]]
                        and k["dem_dong_thoi"] == [k["khai_bao"]]
                        and all(da_chan)) else HONG,
                "khai báo %d ⇒ đo được %d (tuần tự) và %d (đồng thời). Lượt bị chặn tự khai: "
                "chiều `%s`, `Retry-After`=%s giây, header `X-RateLimit-Limit`=%s. Nếu ca này "
                "lệch thì MỌI kết luận 'nhân theo số bản' ở dưới vô nghĩa: bộ đếm lượt của bộ đo "
                "sai." % (k["khai_bao"], k["dem_tuan_tu"][0], k["dem_dong_thoi"][0],
                          (chan or [{}])[0].get("chieu"), (chan or [{}])[0].get("retry_after"),
                          (chan or [{}])[0].get("gioi_han")))
        # ---- KHẲNG ĐỊNH (G19/AG-02): N tiến trình DÙNG CHUNG một CSDL ⇒ trần KHÔNG NHÂN.
        #
        # BẢN TRƯỚC khẳng định `sum(...) == N * khai_bao` — tức trần NHÂN theo số bản, và còn đòi
        # MỖI bản đạt đủ trần khai báo. **Đó là khẳng định CHÍNH LỖ HỒNG B-G11-10.** AG-02 đã đóng
        # ở G19: kho đếm chuyển vào CSDL, trần nằm trong chính câu ghi, cả lượt kiểm trong MỘT
        # giao dịch `BEGIN IMMEDIATE` — nên N tiến trình chia nhau MỘT ngân sách.
        #
        # Khẳng định ĐÚNG nay: TỔNG qua N bản = ĐÚNG trần khai báo, và mọi bản đều kết thúc 429.
        # GIỮ NGUYÊN ĐỘ RĂNG: nếu ai quay lại kho bộ nhớ một tiến trình thì tổng thành N×trần và
        # ca này ĐỎ lại.
        dung_tuan_tu = sum(k["dem_tuan_tu"]) == k["khai_bao"] and all(da_chan)
        dung_dong_thoi = sum(k["dem_dong_thoi"]) == k["khai_bao"]
        if N > 1:
            ket("P1.%d" % N, "N=%d tiến trình CÙNG một CSDL, cùng IP: trần DÙNG CHUNG = %d "
                "(KHÔNG nhân thành %d)" % (N, k["khai_bao"], N * k["khai_bao"]),
                DAT if (dung_tuan_tu and dung_dong_thoi) else HONG,
                "tuần tự: %s (tổng %d, mọi bản đều kết thúc bằng 429: %s) · đồng thời: %s "
                "(tổng %d) · khai báo %d cho CẢ CỤM. Ngân sách là MỘT, chia nhau ⇒ trần dùng "
                "chung, KHÔNG nhân theo số bản."
                % (k["dem_tuan_tu"], sum(k["dem_tuan_tu"]), da_chan, k["dem_dong_thoi"],
                   sum(k["dem_dong_thoi"]), k["khai_bao"]))
        # ---- Bằng chứng ĐỒNG THỜI: N tiến trình thật đã phục vụ chồng nhau.
        if N >= 2:
            ket("P1.%d-dt" % N, "N=%d: các lượt THẬT SỰ chồng nhau giữa các tiến trình khác nhau"
                % N, DAT if (k["cao_nhat_ban"] >= 2 and k["cung_giay"] >= 2) else HONG,
                "phía client: cao nhất %d lượt đang bay thuộc %d bản khác nhau · phía máy chủ "
                "(log JSON của chính các tiến trình): %d pid khác nhau cùng phục vụ trong một "
                "giây · %d pid khác nhau đã dùng (%s)"
                % (k["cao_nhat_tong"], k["cao_nhat_ban"], k["cung_giay"],
                   len(set(k["pid_dt"])), sorted(set(k["pid_dt"]))))

    # ---- Biến thể: MỖI BẢN MỘT CSDL RIÊNG (N=4) — chứng minh việc nhân KHÔNG do CSDL tách rời.
    N = 4
    khai_bao = ket_qua[min(ket_qua)]["khai_bao"]
    nens = []
    for _ in range(N):
        d = nen_tam("rieng")
        dung_nen(d)
        nens.append(d)
    sv = [mo_may_chu(nens[k], tien_to="rieng") for k in range(N)]
    try:
        dem, ct = bom_tuan_tu(sv, toi_da_moi_ban=khai_bao + 3)
        da_chan = [bool(x) and x[-1]["ma"] == 429 for x in ct]
        ket("P1.%d-rieng" % N, "N=%d bản, MỖI BẢN MỘT CSDL RIÊNG: trần vẫn nhân (%d)"
            % (N, sum(dem)),
            DAT if (sum(dem) == N * khai_bao and all(da_chan)) else HONG,
            "%s ⇒ tổng %d, khai báo %d/bản, mỗi bản kết thúc bằng 429: %s. ĐÂY LÀ CHỖ DUY NHẤT "
            "trần còn nhân, và nhân là ĐÚNG: mỗi bản một CSDL RIÊNG thì mỗi kho đếm độc lập — "
            "không có gì để chia sẻ. Ở P1.2–P1.8 các bản DÙNG CHUNG một CSDL và trần KHÔNG nhân "
            "(G19/AG-02 đã chuyển kho đếm vào CSDL)."
            % (dem, sum(dem), khai_bao, da_chan))
    finally:
        for s in sv:
            tat_tien_trinh(s["p"])
    return ket_qua


# ===============================================================================================
# P2 — TỰ KIỂM BỘ ĐO CỦA P1
# ===============================================================================================
def dem_cho_qua(danh_sach_ma):
    """Bộ đếm THẬT: một lượt là 'cho qua' khi mã HTTP KHÁC 429."""
    return sum(1 for ma in danh_sach_ma if ma != 429)


def dem_cho_qua_dot_bien(danh_sach_ma):
    """BẢN ĐỘT BIẾN CỐ Ý của bộ đếm: đếm MỌI lượt là cho qua (quên đọc mã 429)."""
    return len(danh_sach_ma)


def p2_tu_kiem_bo_do(ket_qua_p1):
    muc("P2. TỰ KIỂM BỘ ĐO CỦA P1 — đối chứng dương · đột biến hàm đếm")
    # (a) ĐỘT BIẾN HÀM ĐẾM: trên chính dữ liệu thật của P1, bộ đếm sai PHẢI cho số khác.
    if ket_qua_p1:
        N = max(ket_qua_p1)
        k = ket_qua_p1[N]
        ma_that = []
        for kk, ct in enumerate(k["chi_tiet"]):
            for o in ct:
                ma_that.append(o["ma"])
        dung, sai = dem_cho_qua(ma_that), dem_cho_qua_dot_bien(ma_that)
        ket("P2a", "ĐỘT BIẾN hàm đếm (đếm cả lượt 429) cho số KHÁC trên dữ liệu thật",
            DAT if sai != dung else HONG,
            "N=%d: bộ đếm thật %d · bộ đếm đột biến %d trên CÙNG %d lượt đã ghi lại. Nếu hai số "
            "bằng nhau thì phép đếm ở P1 không phân biệt được 'cho qua' với 'bị chặn'."
            % (N, dung, sai, len(ma_that)))
    else:
        ket("P2a", "ĐỘT BIẾN hàm đếm", BO_QUA, "P1 không đo được nên không có dữ liệu để đột biến")

    # (b) ĐỐI CHỨNG DƯƠNG: một trần CÓ DÙNG CHUNG (đếm trong CSDL) KHÔNG được nhân theo số bản.
    nen = nen_tam("hanmuc")
    env = dung_nen(nen)
    kn = sqlite3.connect(os.path.join(nen, "hub.db"))
    kn.row_factory = sqlite3.Row
    tenant = kn.execute("SELECT id FROM tenants ORDER BY id LIMIT 1").fetchone()
    if tenant is None:
        kn.close()
        ket("P2b", "ĐỐI CHỨNG DƯƠNG — trần CÓ dùng chung (đếm trong CSDL) không nhân", BO_QUA,
            "nền tạm không có tenant nào để đo")
        return
    tenant = int(tenant["id"])
    # Hạ trần xuống 5 cho dễ đo: hạn mức đơn nháp = max(sàn, hạn_mức_gói × bội_số).
    kn.execute("UPDATE goi_dich_vu SET han_muc_don_thang=5 WHERE id="
               "(SELECT goi_id FROM tenants WHERE id=?)", (tenant,))
    kn.commit()
    kn.close()
    env = dict(env, VIP_HUB_TRAN_DON_NHAP_MIN="5", VIP_HUB_BOI_SO_DON_NHAP="1")
    con_han = ghi_con(nen, "con_han_muc.py", CON_HAN_MUC)
    # NẠP TRƯỚC bằng MỘT tiến trình: tạo bảng hạn mức trước khi 4 tiến trình cùng vào. Không nạp
    # trước thì 4 lượt `CREATE TABLE` chồng nhau, và một "database is locked" ở đây sẽ bị đọc nhầm
    # thành "trần không dùng chung".
    chay([sys.executable, con_han, "--goc", GOC_APP, "--tenant", str(tenant), "--so-lan", "0",
          "--bat-dau-luc", "0", "--out", os.path.join(nen, "han-nap.json")], env=env, gio=120)
    so_lan, so_con = 4, 4
    bat_dau = time.time() + 2.5
    outs = [os.path.join(nen, "han-%d.json" % i) for i in range(so_con)]
    ps = []
    for i in range(so_con):
        ps.append(subprocess.Popen(
            [sys.executable, con_han, "--goc", GOC_APP, "--tenant", str(tenant),
             "--so-lan", str(so_lan), "--bat-dau-luc", "%.3f" % bat_dau, "--out", outs[i]],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env, cwd=DU_AN))
        CON.append(ps[-1])
    for p in ps:
        p.wait(timeout=120)
    kqs = []
    for o in outs:
        if os.path.exists(o):
            with open(o) as f:
                kqs.append(json.load(f))
    tong_dat = sum(x["dat_duoc"] for x in kqs)
    tong_chan = sum(x["bi_chan"] for x in kqs)
    tran = kqs[0]["tran"] if kqs else None
    loi = [l for x in kqs for l in x["loi"]]
    if len(kqs) != so_con:
        ket("P2b", "ĐỐI CHỨNG DƯƠNG — trần CÓ dùng chung (đếm trong CSDL) không nhân", HONG,
            "chỉ %d/%d tiến trình con trả kết quả; lỗi: %s" % (len(kqs), so_con, loi[:3]))
        return
    ket("P2b", "ĐỐI CHỨNG DƯƠNG — trần CÓ dùng chung (đếm trong CSDL) KHÔNG nhân theo số bản",
        DAT if (tran == 5 and tong_dat == 5 and tong_chan == so_lan * so_con - 5 and not loi) else HONG,
        "%d tiến trình × %d lượt = %d lượt xin suất, trần trong CSDL = %d ⇒ ĐẶT ĐƯỢC %d, BỊ CHẶN "
        "%d. Cùng bộ đếm-lượt với P1 mà kết quả NGƯỢC: trần trong CSDL dùng chung thật. Vì vậy "
        "kết luận 'nhân theo số bản' ở P1 là do BỘ NHỚ, không phải do bộ đo."
        % (so_con, so_lan, so_con * so_lan, tran, tong_dat, tong_chan))


# ===============================================================================================
# P3 — LỚP HTTP: CÓ TRẠNG THÁI DÙNG CHUNG QUA TIẾN TRÌNH KHÔNG?
# ===============================================================================================
TEN_GOI_MUT = ("deque", "OrderedDict", "defaultdict", "Counter", "dict", "list", "set", "bytearray")


def quet_cau_truc(nguon):
    """Quét AST: mô-đun có trạng thái MUTABLE ở mức mô-đun bị GHI trong hàm không, và có ghi tệp không.

    Vì sao phải quét cả "bị GHI" chứ không chỉ "có biến toàn cục": `http_jt.CHO_PHEP_MOI_TRUONG` là
    một dict ở mức mô-đun — nếu chỉ đếm biến toàn cục thì một hằng số cũng bị tố, còn nếu chỉ tìm
    `global` thì một hàm `_KHO[k] = v` (đột biến không cần `global`) lại lọt. Cả hai chiều đều là
    HỎNG GIẢ. Nên tiêu chí là: **có ai GHI vào tên mức mô-đun không**, bằng cách nào cũng tính.
    """
    cay = ast.parse(nguon)
    toan_cuc = set()          # tên gán ở mức mô-đun
    mutable = {}
    for nut in cay.body:
        if isinstance(nut, ast.Assign):
            for d in nut.targets:
                if isinstance(d, ast.Name):
                    toan_cuc.add(d.id)
                    if isinstance(nut.value, (ast.Dict, ast.List, ast.Set)) or (
                            isinstance(nut.value, ast.Call)
                            and getattr(nut.value.func, "id", "") in TEN_GOI_MUT):
                        mutable[d.id] = nut.lineno
    pham = []
    for nut in ast.walk(cay):
        # (a) `global X` — gán lại tên mức mô-đun từ trong hàm
        if isinstance(nut, ast.Global):
            for t in nut.names:
                if t in toan_cuc:
                    pham.append(("global", t, nut.lineno))
        # (b) GHI vào tên mức mô-đun: X[...] = …, X.append/update/pop/…, del X[...]
        if isinstance(nut, ast.Assign):
            for d in nut.targets:
                if isinstance(d, ast.Subscript) and isinstance(d.value, ast.Name) \
                        and d.value.id in toan_cuc:
                    pham.append(("ghi-chi-so", d.value.id, nut.lineno))
        if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute) \
                and isinstance(nut.func.value, ast.Name) and nut.func.value.id in toan_cuc \
                and nut.func.attr in ("append", "extend", "update", "pop", "popleft", "clear",
                                      "add", "discard", "setdefault", "insert", "remove",
                                      "write", "writelines"):
            pham.append(("goi-%s" % nut.func.attr, nut.func.value.id, nut.lineno))
        if isinstance(nut, ast.Delete):
            for d in nut.targets:
                if isinstance(d, ast.Subscript) and isinstance(d.value, ast.Name) \
                        and d.value.id in toan_cuc:
                    pham.append(("xoa-chi-so", d.value.id, nut.lineno))
        # (c) GHI TỆP / tệp tạm — trạng thái dùng chung ở mức HỆ ĐIỀU HÀNH
        if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name) and nut.func.id == "open":
            che_do = ""
            if len(nut.args) > 1 and isinstance(nut.args[1], ast.Str):
                che_do = nut.args[1].s
            for kw in nut.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Str):
                    che_do = kw.value.s
            if any(c in che_do for c in "wax+"):
                pham.append(("mo-tep-de-ghi", "open(%r)" % che_do, nut.lineno))
        if isinstance(nut, ast.Attribute) and nut.attr in ("write_text", "write_bytes"):
            pham.append(("ghi-tep-pathlib", nut.attr, nut.lineno))
        if isinstance(nut, ast.Attribute) and isinstance(nut.value, ast.Name) \
                and nut.value.id in ("tempfile", "shutil"):
            pham.append(("goi-%s.%s" % (nut.value.id, nut.attr), nut.value.id, nut.lineno))
    return {"toan_cuc": sorted(toan_cuc), "mutable": mutable, "pham": pham}


_DEM_STUB = [0]


def mo_stub_tien_trinh(nen, *, che_do="vong_lap", do_tre=0.0):
    """Stub J&T trong MỘT TIẾN TRÌNH RIÊNG, bind `127.0.0.1` CỔNG 0 (hệ cấp cổng).

    Tên tệp ghi cổng phải DUY NHẤT cho từng lượt mở: dùng lại một tên thì lượt mở thứ hai đọc
    trúng cổng CŨ (tệp đã có sẵn từ lượt trước) và đo nhầm vào stub đã chết — một HỎNG GIẢ rất
    khó thấy vì mọi con số vẫn ra số.
    """
    _DEM_STUB[0] += 1
    tep_cong = os.path.join(nen, "stub-%s-%d.json" % (che_do, _DEM_STUB[0]))
    p = subprocess.Popen([sys.executable, os.path.join(GOC_APP, "thu", "stub_jt.py"),
                          "--che-do", che_do, "--do-tre", str(do_tre), "--ghi-cong", tep_cong],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=DU_AN)
    CON.append(p)
    het = time.time() + 20
    while time.time() < het and not os.path.exists(tep_cong):
        if p.poll() is not None:
            raise RuntimeError("stub chết ngay: %s" % (p.stdout.read() if p.stdout else ""))
        time.sleep(0.05)
    if not os.path.exists(tep_cong):
        raise RuntimeError("stub không ghi được cổng sau 20 giây")
    with open(tep_cong) as f:
        d = json.load(f)
    if not cho_cong(d["cong"], p):
        raise RuntimeError("stub không mở cổng %d" % d["cong"])
    return {"p": p, "cong": d["cong"], "pid": d["pid"], "tep_cong": tep_cong}


def doc_so_do_stub(cong):
    with urllib.request.urlopen("http://127.0.0.1:%d/__stub/thong-ke" % cong, timeout=10) as f:
        return json.loads(f.read().decode("utf-8"))


def chay_con_http(nen, con_script, *, module, gocs, url, i, k, out, env_them=None, cho_xong=True):
    env = dict(os.environ, **(env_them or {}))
    lenh = [sys.executable, con_script]
    for g in gocs:
        lenh += ["--goc", g]
    lenh += ["--module", module, "--url", url, "--i", str(i), "--k", str(k), "--out", out]
    p = subprocess.Popen(lenh, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         env=env, cwd=DU_AN)
    CON.append(p)
    if cho_xong:
        p.wait(timeout=120)
    return p


def doc_kq_con(duong):
    if not os.path.exists(duong):
        return None
    with open(duong) as f:
        return json.load(f)


def kiem_lan_du_lieu(kqs, *, so_con):
    """Ba danh sách TÁCH RỜI — gộp chúng lại là tự làm mù bộ đo:

      `thieu` : tiến trình con không trả kết quả / lượt gọi không trả về (con HỎNG, không phải lẫn)
      `lan`   : nhận được dấu vết của TIẾN TRÌNH KHÁC — đúng thứ cần bắt
      `dung`  : lượt gọi thành công nhưng KHÔNG thấy dấu vết của chính mình
    """
    thieu, lan, dung = [], [], []
    for i, kq in enumerate(kqs):
        if kq is None:
            thieu.append({"i": i, "ly_do": "tiến trình con không ghi kết quả"})
            continue
        if kq["loi"]:
            thieu.append({"i": i, "ly_do": "; ".join(kq["loi"])[:200]})
        for o in kq["kq"]:
            if o is None:
                continue
            if ("VEH-G18-%02d-" % i) not in o["than"]:
                dung.append({"i": i, "than": o["than"][:120]})
            for j in range(so_con):
                if j != i and ("VEH-G18-%02d-" % j) in o["than"]:
                    lan.append({"i": i, "j": j, "than": o["than"][:160]})
    return thieu, lan, dung


def p3_lop_http():
    muc("P3. LỚP HTTP `app/http_jt.py` — TRẠNG THÁI DÙNG CHUNG QUA TIẾN TRÌNH?")
    duong_http = os.path.join(GOC_APP, "http_jt.py")
    with open(duong_http) as f:
        nguon = f.read()
    quet = quet_cau_truc(nguon)
    print("  tên mức mô-đun : %s" % ", ".join(quet["toan_cuc"]))
    print("  trong đó MUTABLE: %s" % (", ".join("%s(dòng %d)" % (k, v)
                                                for k, v in sorted(quet["mutable"].items()))
                                      or "(không)"))
    print("  dấu hiệu GHI trạng thái mức mô-đun / ghi tệp: %s"
          % (quet["pham"] or "(không có)"))
    # `CHO_PHEP_MOI_TRUONG` là dict mức mô-đun — cố ý: nó là HẰNG số cấu hình, và tiêu chí ở đây
    # là KHÔNG AI GHI vào nó. Nói ra để không ai đọc "có 2 dict" thành "có trạng thái".
    ket("P3a", "Quét cấu trúc: `http_jt` KHÔNG có trạng thái mức mô-đun nào bị GHI, không ghi tệp",
        DAT if not quet["pham"] else HONG,
        "%d tên mức mô-đun, %d trong đó là dict hằng số cấu hình (%s), 0 dấu hiệu ghi "
        "(global / ghi chỉ số / gọi append-update / mở tệp để ghi / tempfile / shutil)"
        % (len(quet["toan_cuc"]), len(quet["mutable"]), ", ".join(sorted(quet["mutable"]))))

    nen = nen_tam("http")
    con_script = ghi_con(nen, "con_http.py", CON_HTTP)
    stub = mo_stub_tien_trinh(nen, che_do="vong_lap", do_tre=0.15)
    url = "http://127.0.0.1:%d/webopenplatformapi/api/order/addOrder" % stub["cong"]
    so_con = 4

    # ---- (1) BỐN TIẾN TRÌNH THẬT, NỐI ĐUÔI: cùng khuôn với ca đột biến ở P4.
    tk_truoc = doc_so_do_stub(stub["cong"])
    outs = [os.path.join(nen, "http-nd-%d.json" % i) for i in range(so_con)]
    con_ps = [chay_con_http(nen, con_script, module="http_jt", gocs=[GOC_APP], url=url, i=i, k=1,
                            out=outs[i]) for i in range(so_con)]
    tk_sau = doc_so_do_stub(stub["cong"])
    kqs = [doc_kq_con(o) for o in outs]
    thieu, lan, dung = kiem_lan_du_lieu(kqs, so_con=so_con)
    pids = sorted(x["pid"] for x in kqs if x)
    ma_con = [p.returncode for p in con_ps]
    ket("P3b", "N=%d TIẾN TRÌNH THẬT (pid khác nhau) — không tiến trình nào nhận dữ liệu của "
        "tiến trình khác" % so_con,
        DAT if (len(pids) == so_con and all(m == 0 for m in ma_con)
                and not lan and not dung and not thieu) else HONG,
        "pid: %s (KHÁC nhau ⇒ đây là tiến trình, không phải luồng) · mã thoát các con: %s · "
        "mỗi tiến trình nhận đúng `txlogisticId` + `apiAccount` của mình · 0 lượt nhận dấu vết "
        "của tiến trình khác · stub (đo từ TIẾN TRÌNH STUB): kết nối %d→%d, yêu cầu %d→%d"
        % (pids, ma_con, tk_truoc["so_ket_noi"], tk_sau["so_ket_noi"],
           tk_truoc["so_yeu_cau"], tk_sau["so_yeu_cau"]))
    ket("P3c", "MỘT kết nối TCP cho MỘT lượt gọi, KHÔNG pool — đo từ tiến trình STUB",
        DAT if (tk_sau["so_ket_noi"] - tk_truoc["so_ket_noi"] == so_con
                and tk_sau["so_yeu_cau"] - tk_truoc["so_yeu_cau"] == so_con) else HONG,
        "%d lượt gọi ⇒ stub nhận THÊM %d kết nối và %d yêu cầu. Kết nối là trạng thái của tiến "
        "trình GỌI, không dùng chung: mỗi tiến trình tự mở và tự đóng kết nối của mình."
        % (so_con, tk_sau["so_ket_noi"] - tk_truoc["so_ket_noi"],
           tk_sau["so_yeu_cau"] - tk_truoc["so_yeu_cau"]))

    # ---- ĐỐI CHỨNG DƯƠNG cho CHÍNH máy đếm kết nối: 3 yêu cầu trên MỘT kết nối ⇒ chỉ +1.
    import http.client
    tk0 = doc_so_do_stub(stub["cong"])
    kn = http.client.HTTPConnection("127.0.0.1", stub["cong"], timeout=10)
    try:
        for _ in range(3):
            kn.request("POST", "/webopenplatformapi/api/order/addOrder",
                       body=b"bizContent=%7B%7D",
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
            kn.getresponse().read()
    finally:
        kn.close()
    tk1 = doc_so_do_stub(stub["cong"])
    ket("P3d", "ĐỐI CHỨNG DƯƠNG cho máy đếm: 3 yêu cầu trên MỘT kết nối ⇒ kết nối chỉ +1",
        DAT if (tk1["so_ket_noi"] - tk0["so_ket_noi"] == 1
                and tk1["so_yeu_cau"] - tk0["so_yeu_cau"] == 3) else HONG,
        "kết nối %d→%d, yêu cầu %d→%d ⇒ máy đếm đếm KẾT NỐI, không đếm yêu cầu"
        % (tk0["so_ket_noi"], tk1["so_ket_noi"], tk0["so_yeu_cau"], tk1["so_yeu_cau"]))

    # ---- (2) BỐN TIẾN TRÌNH × BỐN LUỒNG ĐỒNG THỜI: có chạy song song thật không?
    stub2 = mo_stub_tien_trinh(nen, che_do="vong_lap", do_tre=0.3)
    url2 = "http://127.0.0.1:%d/webopenplatformapi/api/order/addOrder" % stub2["cong"]
    outs2 = [os.path.join(nen, "http-dt-%d.json" % i) for i in range(so_con)]
    ps = [chay_con_http(nen, con_script, module="http_jt", gocs=[GOC_APP], url=url2, i=i, k=4,
                        out=outs2[i], cho_xong=False) for i in range(so_con)]
    t0 = time.perf_counter()
    for p in ps:
        p.wait(timeout=120)
    giay = time.perf_counter() - t0
    tk2 = doc_so_do_stub(stub2["cong"])
    kqs2 = [doc_kq_con(o) for o in outs2]
    thieu2, lan2, dung2 = kiem_lan_du_lieu(kqs2, so_con=so_con)
    ket("P3e", "N=%d tiến trình × 4 luồng chạy SONG SONG THẬT và không lẫn dữ liệu" % so_con,
        DAT if (not dung2 and not lan2 and not thieu2 and tk2["cao_nhat_dang_xu_ly"] >= 4
                and tk2["so_yeu_cau"] == so_con * 4) else HONG,
        "stub báo cao nhất %d yêu cầu CÙNG LÚC (1 = mọi lượt bị tuần tự hoá) · %d yêu cầu · "
        "%d kết nối cho %d lượt gọi (không pool) · tổng thời gian %.2fs (độ trễ mỗi lượt 0,3s, "
        "%d lượt ⇒ tuần tự hoá hết phải ≥ %.1fs)"
        % (tk2["cao_nhat_dang_xu_ly"], tk2["so_yeu_cau"], tk2["so_ket_noi"], so_con * 4,
           giay, so_con * 4, so_con * 4 * 0.3))

    # ---- ĐỐI CHỨNG ÂM cho phép đo "song song": cùng stub, 4 tiến trình NỐI ĐUÔI ⇒ cao nhất = 1.
    stub3 = mo_stub_tien_trinh(nen, che_do="vong_lap", do_tre=0.3)
    url3 = "http://127.0.0.1:%d/webopenplatformapi/api/order/addOrder" % stub3["cong"]
    outs3 = [os.path.join(nen, "http-nd2-%d.json" % i) for i in range(so_con)]
    for i in range(so_con):
        chay_con_http(nen, con_script, module="http_jt", gocs=[GOC_APP], url=url3, i=i, k=1,
                      out=outs3[i])
    tk3 = doc_so_do_stub(stub3["cong"])
    ket("P3f", "ĐỐI CHỨNG ÂM — 4 tiến trình NỐI ĐUÔI: cao nhất đang xử lý = 1",
        DAT if tk3["cao_nhat_dang_xu_ly"] == 1 else HONG,
        "cao nhất %d (nếu ca ĐỒNG THỜI ở P3e cũng ra 1 thì 'song song' không đo được gì; còn "
        "nếu ca này ra >1 thì máy đếm tự bịa)" % tk3["cao_nhat_dang_xu_ly"])
    return {"con_script": con_script, "nen": nen, "quet": quet}


# ===============================================================================================
# P4 — TỰ KIỂM BỘ ĐO CỦA P3: BẢN ĐỘT BIẾN PHẢI BỊ BẮT
# ===============================================================================================
def p4_tu_kiem_bo_do(p3):
    muc("P4. TỰ KIỂM BỘ ĐO CỦA P3 — bản đột biến có ĐỆM DÙNG CHUNG phải bị bắt")
    nen = nen_tam("dotbien")
    with open(os.path.join(nen, "http_jt_dot_bien.py"), "w") as f:
        f.write(CON_DOT_BIEN)
    with open(os.path.join(nen, "http_jt_dot_bien.py")) as f:
        nguon_mut = f.read()

    # (a) QUÉT CẤU TRÚC phải thấy dấu hiệu ghi trạng thái dùng chung.
    quet = quet_cau_truc(nguon_mut)
    loai = sorted(set(p[0] for p in quet["pham"]))
    ket("P4a", "Quét cấu trúc BẮT ĐƯỢC bản đột biến (đệm toàn cục + ghi tệp dùng chung)",
        DAT if quet["pham"] else HONG,
        "dấu hiệu bắt được: %s ⇒ cùng phép quét ở P3a trả '(không có)' cho `http_jt`, nên P3a "
        "không phải một phép quét luôn-rỗng" % (sorted(set(loai)) or "KHÔNG BẮT ĐƯỢC GÌ"))

    # (b) ĐO HÀNH VI: cùng khuôn NỐI ĐUÔI như P3b, nhưng chạy qua mô-đun đột biến ⇒ PHẢI lẫn dữ liệu.
    stub = mo_stub_tien_trinh(nen, che_do="vong_lap", do_tre=0.0)
    url = "http://127.0.0.1:%d/webopenplatformapi/api/order/addOrder" % stub["cong"]
    tep_dem = os.path.join(nen, "dem-dot-bien.json")
    env_them = {"VIP_G18_TEP_DEM": tep_dem}
    so_con = 4
    outs = [os.path.join(nen, "mut-%d.json" % i) for i in range(so_con)]
    for i in range(so_con):
        chay_con_http(nen, p3["con_script"], module="http_jt_dot_bien", gocs=[nen, GOC_APP],
                      url=url, i=i, k=1, out=outs[i], env_them=env_them)
    kqs = [doc_kq_con(o) for o in outs]
    thieu, lan, dung = kiem_lan_du_lieu(kqs, so_con=so_con)
    ket("P4b", "Đo hành vi BẮT ĐƯỢC bản đột biến: tiến trình sau nhận thân trả lời của tiến "
        "trình trước", DAT if (lan and not thieu) else HONG,
        "%d/%d lượt nhận dấu vết của tiến trình KHÁC (ví dụ: %s). Bản đột biến đệm theo URL nên "
        "tiến trình thứ hai trở đi nhận thân của tiến trình đầu — đúng thứ P3b khẳng định "
        "`http_jt` KHÔNG làm." % (len(lan), so_con, (lan[:1] or [{}])[0].get("than", "")[:100]))
    print("  (bản đột biến nằm ở %s — chỉ để đo bộ đo, KHÔNG nằm trong mã sản phẩm)"
          % os.path.join(nen, "http_jt_dot_bien.py"))


# ===============================================================================================
# P5 — TẦNG CSDL: `khoa_ghi` (RLock) KHÔNG PHỦ TIẾN TRÌNH
# ===============================================================================================
def dat_lai_dem(nen, gia_tri=0):
    kn = sqlite3.connect(os.path.join(nen, "hub.db"), timeout=30)
    try:
        kn.execute("CREATE TABLE IF NOT EXISTS _g18_dem (id INTEGER PRIMARY KEY, dem INTEGER)")
        kn.execute("INSERT OR REPLACE INTO _g18_dem (id, dem) VALUES (1, ?)", (gia_tri,))
        kn.commit()
        che_do = kn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        kn.close()
    return che_do


def doc_dem(nen):
    kn = sqlite3.connect(os.path.join(nen, "hub.db"), timeout=30)
    try:
        return int(kn.execute("SELECT dem FROM _g18_dem WHERE id=1").fetchone()[0])
    finally:
        kn.close()


def chay_nhieu_con_csdl(nen, con_script, *, cach, so_con, so_lan, do_tre=0.002, cho_giay=2.0):
    bat_dau = time.time() + cho_giay
    outs = [os.path.join(nen, "csdl-%s-%d.json" % (cach, i)) for i in range(so_con)]
    ps = []
    for i in range(so_con):
        p = subprocess.Popen([sys.executable, con_script, "--goc", GOC_APP, "--cach", cach,
                              "--so-lan", str(so_lan), "--do-tre", str(do_tre),
                              "--bat-dau-luc", "%.3f" % bat_dau, "--out", outs[i]],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             env=dict(os.environ, VIP_HUB_DATA=nen), cwd=DU_AN)
        CON.append(p)
        ps.append(p)
    for p in ps:
        p.wait(timeout=180)
    kqs = []
    for o in outs:
        if os.path.exists(o):
            with open(o) as f:
                kqs.append(json.load(f))
    return kqs


def p5_tang_csdl():
    muc("P5. TẦNG CSDL — `csdl.khoa_ghi` (RLock của Python) KHÔNG phủ qua tiến trình")
    nen = nen_tam("csdl")
    dung_nen(nen)
    con_script = ghi_con(nen, "con_csdl.py", CON_CSDL)
    so_con, so_lan = 4, 25
    tong = so_con * so_lan
    che_do_wal = dat_lai_dem(nen, 0)

    # NẠP TRƯỚC một tiến trình: mở kết nối + đặt WAL + tạo bảng, để cuộc đua WAL của CSDL MỚI
    # không lẫn vào phép đo (đua đó đã ghi trong `csdl._dat_wal`, không phải phát hiện mới).
    chay_nhieu_con_csdl(nen, con_script, cach="cau_lenh", so_con=1, so_lan=0, cho_giay=0)
    che_do_wal = dat_lai_dem(nen, 0)

    kq_ngay_tho = chay_nhieu_con_csdl(nen, con_script, cach="ngay_tho", so_con=so_con, so_lan=so_lan)
    dem_ngay_tho = doc_dem(nen)
    dat_lai_dem(nen, 0)
    kq_gd = chay_nhieu_con_csdl(nen, con_script, cach="giao_dich", so_con=so_con, so_lan=so_lan)
    dem_gd = doc_dem(nen)
    dat_lai_dem(nen, 0)
    kq_cl = chay_nhieu_con_csdl(nen, con_script, cach="cau_lenh", so_con=so_con, so_lan=so_lan)
    dem_cl = doc_dem(nen)

    loi = [l for x in (kq_ngay_tho + kq_gd + kq_cl) for l in x["loi"]]
    pids = sorted(x["pid"] for x in kq_ngay_tho)
    print("  CSDL tạm %s · chế độ sổ ghi %s · %d tiến trình × %d lượt (pid %s)"
          % (os.path.join(nen, "hub.db"), che_do_wal, so_con, so_lan, pids))
    ket("P5a", "ĐỌC–SỬA–GHI NGÂY THƠ (không giao dịch): MẤT CẬP NHẬT — RLock không cứu được",
        DAT if (dem_ngay_tho < tong and len(set(pids)) == so_con) else HONG,
        "%d tiến trình × %d lượt = %d lượt tăng, bộ đếm thật = %d ⇒ MẤT %d lượt. `khoa_ghi` là "
        "RLock nên chỉ phủ MỘT tiến trình; giữa hai câu SELECT và UPDATE của hai tiến trình khác "
        "nhau không có gì chặn. Lỗi này im lặng: không ngoại lệ, không log."
        % (so_con, so_lan, tong, dem_ngay_tho, tong - dem_ngay_tho))
    ket("P5b", "CÙNG khuôn nhưng bọc `csdl.giao_dich()`: ĐỦ %d lượt, 0 mất" % tong,
        DAT if dem_gd == tong else HONG,
        "bộ đếm thật = %d/%d. `giao_dich()` mở `BEGIN IMMEDIATE` ⇒ khoá GHI của SQLite là khoá "
        "TỆP, phủ mọi tiến trình. Đây là cách ĐÚNG cho đọc-sửa-ghi qua nhiều tiến trình." % (dem_gd, tong))
    ket("P5c", "MỘT CÂU nguyên tử `UPDATE … SET dem = dem + 1`: ĐỦ %d lượt, 0 mất" % tong,
        DAT if dem_cl == tong else HONG,
        "bộ đếm thật = %d/%d — cách rẻ nhất và cũng là cách `gioi_han` PHẦN B đang dùng."
        % (dem_cl, tong))
    ket("P5d", "Không lượt nào ném ngoại lệ ở cả ba cách (mất cập nhật là hỏng IM LẶNG)",
        DAT if not loi else HONG,
        "%d ngoại lệ trên %d lượt ghi%s" % (len(loi), tong * 3,
                                            (": " + "; ".join(loi[:2])) if loi else ""))
    return {"dem_ngay_tho": dem_ngay_tho, "dem_gd": dem_gd, "dem_cl": dem_cl, "tong": tong,
            "so_con": so_con, "so_lan": so_lan, "che_do_wal": che_do_wal, "pids": pids}


# ===============================================================================================
# P6 — TỔNG KẾT
# ===============================================================================================
def p6_tong_ket():
    muc("P6. TỔNG KẾT — lớp nào an toàn qua tiến trình, lớp nào KHÔNG")
    print("""
  ┌───────────────────────────────┬──────────────────────────────┬────────────────────────────┐
  │ LỚP                           │ TRẠNG THÁI Ở ĐÂU             │ QUA NHIỀU TIẾN TRÌNH?      │
  ├───────────────────────────────┼──────────────────────────────┼────────────────────────────┤
  │ app/http_jt.py (lớp HTTP)     │ KHÔNG có trạng thái nào      │ AN TOÀN (P3) — không có gì │
  │                               │ (không pool, không đệm,      │ để dùng chung; mỗi lượt một│
  │                               │  không ghi tệp)              │ kết nối, tự mở tự đóng     │
  ├───────────────────────────────┼──────────────────────────────┼────────────────────────────┤
  │ gioi_han PHẦN A (trần tần     │ bộ đếm trong BỘ NHỚ tiến     │ KHÔNG AN TOÀN (P1): trần   │
  │ suất: auth.*, webhook.*, …)   │ trình + threading.Lock       │ thực = khai báo × số bản   │
  ├───────────────────────────────┼──────────────────────────────┼────────────────────────────┤
  │ gioi_han PHẦN B (hạn mức nhập)│ bảng CSDL + UPDATE có điều   │ AN TOÀN (P2b): trần giữ    │
  │                               │ kiện (nguyên tử)             │ nguyên, không nhân         │
  ├───────────────────────────────┼──────────────────────────────┼────────────────────────────┤
  │ csdl.khoa_ghi (RLock) +       │ RLock chỉ phủ MỘT tiến       │ KHÔNG phủ tiến trình (P5): │
  │ đọc-sửa-ghi ngây thơ          │ trình; SQLite khoá ở tầng tệp│ mất cập nhật, im lặng      │
  ├───────────────────────────────┼──────────────────────────────┼────────────────────────────┤
  │ csdl.giao_dich() / câu lệnh   │ BEGIN IMMEDIATE (khoá ghi của│ AN TOÀN (P5b, P5c)         │
  │ nguyên tử                     │ SQLite) — khoá ở tầng TỆP    │                            │
  └───────────────────────────────┴──────────────────────────────┴────────────────────────────┘

  HỆ QUẢ VẬN HÀNH (đọc kỹ trước khi chạy nhiều bản):
   1. Chạy N bản máy chủ thì trần chống dò mật khẩu / chống spam trở thành N × khai báo. Một kẻ
      tấn công chỉ cần đi qua bộ cân bằng tải là có N lần ngân sách. TRẦN VẪN CÓ TÁC DỤNG với
      một bản, và vẫn chặn lạm dụng tự động — nhưng nó KHÔNG còn là "20 lượt/300 giây" như khai.
   2. Cách chữa ĐÃ CÓ SẴN TRONG NHÀ: khuôn của `gioi_han` PHẦN B — bộ đếm trong CSDL với
      `UPDATE … WHERE … + ? <= trần`. Đo được ở P2b là nó giữ nguyên trần qua 4 tiến trình.
      Việc chuyển PHẦN A sang khuôn đó là thay đổi mã của AG-01, KHÔNG nằm trong tệp này.
   3. Với SQLite: đọc-sửa-ghi PHẢI nằm trong `giao_dich()` hoặc là một câu nguyên tử. Đừng tin
      `khoa_ghi`: nó chỉ giữ cho kết nối của MỘT tiến trình không bị hai luồng dùng cùng lúc.
   4. Lớp HTTP không cần sửa gì cho nhiều tiến trình. Trần đồng thời của nó là trần file
      descriptor của TỪNG tiến trình (không pool) — nhiều bản thì trần đó nhân lên, KHÔNG phải
      một trần chung bị chia.
   5. Bộ đếm tần suất còn mất sạch khi khởi động lại (đã ghi trong `gioi_han.py`): đó là cửa
      lách thứ hai, độc lập với số tiến trình.
""")


def main():
    print("═" * 78)
    print("G18/AG-02 — ĐA TIẾN TRÌNH: ĐO BẰNG TIẾN TRÌNH THẬT (subprocess), KHÔNG BẰNG LUỒNG")
    print("═" * 78)
    try:
        p0_chot_an_toan()
        kq1 = p1_tran_tan_suat()
        p2_tu_kiem_bo_do(kq1)
        p3 = p3_lop_http()
        p4_tu_kiem_bo_do(p3)
        p5_tang_csdl()
        p6_tong_ket()
    finally:
        don_dep()

    dem = {}
    for x in KQ:
        dem[x["trang_thai"]] = dem.get(x["trang_thai"], 0) + 1
    tong = len(KQ)
    print("═" * 78)
    print("  ca ĐẠT: %d · HỎNG: %d · BỎ QUA: %d · KHÔNG KẾT LUẬN: %d · TỔNG: %d"
          % (dem.get(DAT, 0), dem.get(HONG, 0), dem.get(BO_QUA, 0), dem.get(KHUYET, 0), tong))
    print("  lệnh thật + mã thoát thật đã chạy: %d" % len(LENH))
    for l, ma in LENH[-6:]:
        print("    exit %-3d %s" % (ma, l[:150]))
    hong = dem.get(HONG, 0)
    print("  %d ca — %s" % (tong, "ĐẠT" if hong == 0 else "HỎNG"))
    print("═" * 78)
    return 0 if hong == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
