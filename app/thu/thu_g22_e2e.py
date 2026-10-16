#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — AG-06: CỔNG E2E TẦNG 3 (Chromium THẬT) — PHÁN BẰNG MÃ THOÁT, VÀ PHÂN BIỆT
"ỨNG DỤNG HỎNG" VỚI "NỀN CHẾT GIỮA LƯỢT".

VÌ SAO CÓ TỆP NÀY
-----------------
Lượt chạy 16:26 ngày 16/10/2026 (`sh thu_giao_dien/chay.sh`, GIỮ NGUYÊN không sửa một dòng mã
sản phẩm) in ra:

      5 failed · 14 did not run · 46 passed · mã thoát 1

Đọc con số ấy theo nghĩa thường thì kết luận sẽ là "năm ca sản phẩm hỏng". SỰ THẬT ĐO ĐƯỢC thì
khác hẳn: cả năm ca hỏng đều là `net::ERR_CONNECTION_REFUSED` trên CÙNG một cổng — **máy chủ đã
chết giữa lượt**, và 14 ca "did not run" chỉ là hệ quả `serial` của năm ca kia. KHÔNG một dòng
nào trong báo cáo nói ra điều đó. Một cái cổng chặn hồi quy báo "sản phẩm hỏng" khi thật ra
"nền hỏng" là một cái cổng sẽ bị người ta học cách bỏ qua — và đúng lúc ấy nó thôi chặn được gì.

TỆP NÀY ĐÓNG ĐÚNG KHOẢNG ẤY, và chỉ thế:

  (1) **Chạy trọn bộ** tầng 3 với CHÍNH cách của `chay.sh` (nền cô lập, cổng rỗng THỬ TRƯỚC,
      chờ máy chủ MỞ THẬT, tắt theo ĐÚNG PID), nhưng GIỮ LẠI ĐƯỢC log máy chủ và log playwright.
  (2) **Phán bằng MÃ THOÁT**, không bằng chữ trong output — và tách bốn phán quyết KHÁC NHAU:
      `DAT` · `HONG` (sản phẩm) · `HA_TANG_CHET` (nền) · `KHONG_DO_DUOC` (bộ đọc hỏng).
  (3) **"did not run" KHÔNG phải là ĐẠT.** Một ca không chạy không chứng minh được gì; nó là
      HỎNG ở đây, kể cả khi nguyên nhân là một ca khác hỏng trước nó.
  (4) **Ghim số ca** (`--so-ca`, mặc định 65): một bộ thử co lại còn 12 ca rồi báo "12 passed"
      là kiểu hỏng im lặng mà con số `passed` một mình không bắt được.
  (5) **Ghim binary Chromium** (`--ghim-chromium` in đường dẫn + phiên bản + sha256): QA lượt
      sau phải dùng ĐÚNG binary ấy, và không được bỏ qua tầng này.

BA LUẬT GIỮ NGUYÊN
------------------
* Bind `127.0.0.1` (từ chối chạy nếu `VIP_HUB_BIND` trỏ ra ngoài). KHÔNG mở `CHO_PHEP_LIVE`
  — và điều đó được KIỂM bằng `app.adapter.CHO_PHEP_LIVE is False`, không bằng lời hứa.
* KHÔNG `pkill`/`killall`: tắt theo ĐÚNG PID đã giữ, chờ nó CHẾT THẬT, xác minh danh tính
  trước khi dùng tín hiệu mạnh, và báo thẳng nếu còn tiến trình mồ côi.
* KHÔNG gọi ra hãng: nền cô lập + adapter ở chế độ mock.

CHẠY
----
    python3 app/thu/thu_g22_e2e.py --tu-kiem          # bộ tự kiểm (không cần trình duyệt)
    python3 app/thu/thu_g22_e2e.py --ghim-chromium    # in binary Chromium + sha256
    python3 app/thu/thu_g22_e2e.py                    # CHẠY CỔNG ĐẦY ĐỦ

MÃ THOÁT
--------
    0 DAT · 1 HONG (sản phẩm) · 2 KHONG_DUNG_DUOC_NEN · 3 HA_TANG_CHET · 4 KHONG_DO_DUOC
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_GD = os.path.join(GOC, "thu_giao_dien")
DAI_CONG = (18000, 19999)
SO_CA_GHIM = 65
BIN_CHROMIUM_TUONG_DOI = os.path.join(
    "node_modules", "playwright-core", ".local-browsers",
    "chromium_headless_shell-1194", "chrome-mac", "headless_shell")

MA_DAT, MA_HONG, MA_NEN, MA_HA_TANG, MA_KHONG_DO = 0, 1, 2, 3, 4


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. MÔI TRƯỜNG GIT (`N-G18-00`) — `GIT_CONFIG_COUNT=N` thiếu `GIT_CONFIG_KEY_*` làm MỌI lệnh git
#    thoát 128, kể cả `git rev-parse HEAD`. Ở đây chỉ cần ĐỌC HEAD và tình trạng cây để ghim số
#    đo vào một mốc mã; gặp gia đình biến dị dạng thì gỡ KÈM CẢNH BÁO (im lặng gỡ là che một môi
#    trường hỏng — xem `thu_g21_chotcay.py`, nơi luật này sống).
# ══════════════════════════════════════════════════════════════════════════════════════════════
def moi_truong_git_sach():
    """Trả (env, danh sách cảnh báo). Gỡ `GIT_CONFIG_*` CHỈ KHI dị dạng."""
    env = dict(os.environ)
    canh_bao = []
    dem = env.get("GIT_CONFIG_COUNT", "")
    if dem.isdigit() and int(dem) > 0:
        thieu = [i for i in range(int(dem)) if not env.get("GIT_CONFIG_KEY_%d" % i)]
        if thieu:
            canh_bao.append(
                "GIT_CONFIG_COUNT=%s nhưng thiếu GIT_CONFIG_KEY_%s — đã gỡ gia đình "
                "GIT_CONFIG_* (nếu không, MỌI lệnh git thoát 128)" % (dem, ",".join(map(str, thieu))))
            for ten in [k for k in env if k.startswith("GIT_CONFIG_")]:
                env.pop(ten, None)
    return env, canh_bao


def git(*tham_so):
    """Chạy git trong cây này. Trả (mã thoát, stdout đã strip)."""
    env, _ = moi_truong_git_sach()
    try:
        tt = subprocess.run(["git"] + list(tham_so), cwd=GOC, env=env,
                            capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:                       # noqa: BLE001
        return 127, "không chạy được git: %s" % e
    return tt.returncode, tt.stdout.strip()


def sha256_tep(duong):
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khuc in iter(lambda: f.read(1 << 20), b""):
            h.update(khuc)
    return h.hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. ĐỌC KẾT QUẢ — bộ đọc phải ĐỎ ĐƯỢC, nên nó là hàm thuần và có ca tự kiểm ở mục E.
# ══════════════════════════════════════════════════════════════════════════════════════════════
_MAU_TONG_KET = re.compile(
    r"^[ \t]*(\d+)[ \t]+(passed|failed|skipped|did not run|flaky|interrupted)\b", re.M)
_KHOA = {"passed": "passed", "failed": "failed", "skipped": "skipped",
         "did not run": "did_not_run", "flaky": "flaky", "interrupted": "interrupted"}

# Dấu hiệu NỀN CHẾT, không phải ca hỏng. `ERR_CONNECTION_REFUSED` là dấu hiệu ĐÃ ĐO ĐƯỢC ở
# lượt 16:26: cổng không còn ai nghe ⇒ tiến trình máy chủ đã chết, mọi ca sau đó là hệ quả.
_DAU_HIEU_NEN_CHET = (
    "ERR_CONNECTION_REFUSED",
    "ERR_CONNECTION_RESET",
    "ERR_EMPTY_RESPONSE",
    "ERR_SOCKET_NOT_CONNECTED",
)


def doc_tong_ket(van_ban):
    """Rút dòng tổng kết của Playwright. Trả dict, hoặc None nếu KHÔNG có dòng tổng kết nào.

    Lấy lần xuất hiện CUỐI của mỗi nhãn: bộ báo cáo `list` in tổng kết ở cuối, còn dòng chạy ca
    (`  ✓   1 [chromium] › …`) không khớp mẫu vì không phải `<số> <nhãn>`."""
    ra = {v: 0 for v in _KHOA.values()}
    thay = 0
    for m in _MAU_TONG_KET.finditer(van_ban or ""):
        ra[_KHOA[m.group(2)]] = int(m.group(1))
        thay += 1
    if thay == 0:
        return None
    ra["tong"] = sum(ra[k] for k in _KHOA.values())
    return ra


def dau_hieu_nen_chet(van_ban):
    """Danh sách dấu hiệu nền chết có mặt trong log (rỗng = không thấy)."""
    return [d for d in _DAU_HIEU_NEN_CHET if d in (van_ban or "")]


def phan_quyet(tk, may_chu_song, ma_playwright, so_ca_ghim=SO_CA_GHIM, dau_hieu=()):
    """BỐN phán quyết, không phải hai. Trả (mã thoát, nhãn, lý do).

    Thứ tự xét là CỐ Ý: nền chết được xét TRƯỚC mọi kết luận về sản phẩm, vì khi máy chủ chết
    thì `failed`/`did not run` KHÔNG đo được sản phẩm nữa — chúng đo cái nền. Xét sau sẽ là gán
    tội cho sản phẩm bằng một phép đo đã hỏng.
    """
    if tk is None:
        return MA_KHONG_DO, "KHONG_DO_DUOC", (
            "không đọc được dòng tổng kết nào của Playwright ⇒ lượt chạy này KHÔNG phán được "
            "(mã thoát playwright = %s)" % ma_playwright)
    if not may_chu_song:
        return MA_HA_TANG, "HA_TANG_CHET", (
            "tiến trình máy chủ KHÔNG còn sống khi lượt chạy kết thúc ⇒ %d ca hỏng / %d ca không "
            "chạy là HỆ QUẢ CỦA NỀN, không phải của sản phẩm" % (tk["failed"], tk["did_not_run"]))
    if dau_hieu:
        return MA_HA_TANG, "HA_TANG_CHET", (
            "log có dấu hiệu máy chủ mất kết nối (%s) dù tiến trình còn sống ⇒ kết quả không "
            "dùng để phán về sản phẩm được" % ", ".join(dau_hieu))

    loi = []
    if tk["failed"]:
        loi.append("%d ca HỎNG" % tk["failed"])
    if tk["did_not_run"]:
        loi.append("%d ca KHÔNG CHẠY (did-not-run KHÔNG phải là đạt)" % tk["did_not_run"])
    if tk["skipped"]:
        loi.append("%d ca BỎ QUA (skip KHÔNG phải là đạt)" % tk["skipped"])
    if tk["interrupted"]:
        loi.append("%d ca bị ngắt" % tk["interrupted"])
    if tk["flaky"]:
        loi.append("%d ca chập chờn" % tk["flaky"])
    if tk["passed"] != so_ca_ghim:
        loi.append("số ca ĐẠT = %d, GHIM = %d ⇒ bộ thử đã co lại hoặc phình ra, con số 'passed' "
                   "một mình không nói được điều đó" % (tk["passed"], so_ca_ghim))
    if ma_playwright != 0:
        loi.append("mã thoát playwright = %s" % ma_playwright)
    if loi:
        return MA_HONG, "HONG", "; ".join(loi)
    return MA_DAT, "DAT", "%d ca đạt · 0 hỏng · 0 bỏ qua · 0 không chạy · 0 chập chờn" % tk["passed"]


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. NỀN: CỔNG · MÁY CHỦ · DỌN THEO ĐÚNG PID
# ══════════════════════════════════════════════════════════════════════════════════════════════
def cong_dang_dung(cong):
    """Có ai đang NGHE trên 127.0.0.1:<cong> không. Thử KẾT NỐI, không đoán."""
    s = socket.socket()
    s.settimeout(0.25)
    try:
        s.connect(("127.0.0.1", cong))
        return True
    except OSError:
        return False
    finally:
        s.close()


def tim_cong_rong(dai=DAI_CONG, so_lan=60):
    """Cổng rỗng lấy ngẫu nhiên và THỬ TRƯỚC — không `sleep` rồi tin là rỗng."""
    import random
    for _ in range(so_lan):
        cong = random.randint(dai[0], dai[1])
        if not cong_dang_dung(cong):
            return cong
    return None


def tien_trinh_con_song(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def ten_tien_trinh(pid):
    try:
        return subprocess.run(["ps", "-o", "comm=", "-p", str(pid)],
                              capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):                            # noqa: BLE001
        return ""


def _con_song(pid, tt=None):
    """Tiến trình còn sống không.

    `tt` (Popen) mà có thì dùng `tt.poll()` — nó VỪA trả lời VỪA thu lại tiến trình đã chết.
    `os.kill(pid, 0)` một mình **NÓI DỐI với tiến trình ZOMBIE**: con đã chết nhưng chưa được
    `wait()` vẫn giữ nguyên PID và `kill(pid, 0)` vẫn thành công. Lỗi này ĐÃ ĐO ĐƯỢC ở lượt cổng
    G22 đầu tiên: bộ dọn báo "pid 46403 còn sống" cho một máy chủ đã chết hẳn. Xem `test_c5`.
    """
    if tt is not None:
        return tt.poll() is None
    if not pid:
        return False
    return tien_trinh_con_song(pid)


def dong_theo_pid(pid, nhan="", tt=None):
    """Tắt ĐÚNG PID đã giữ. Trả (đã_chết, ghi_chú).

    KHÔNG BAO GIỜ theo mẫu tên (§16.7): một lượt `pkill -f cat` đã giết cả Ollama và Synology
    Drive vì chữ "cat" nằm trong "Application". Tín hiệu mạnh chỉ dùng SAU khi xác minh danh
    tính vẫn là Python — PID có thể đã được cấp lại cho tiến trình khác. NGOẠI LỆ có căn cứ: khi
    `tt` là Popen của CHÍNH tiến trình này thì PID ấy chưa thể được cấp lại (nó là con của ta,
    chưa `wait()`), nên `SIGKILL` ở đó là an toàn và không cần `ps`.

    GHI RÕ PHẠM VI: `ps -o comm=` bị sandbox chặn ở phiên này (trả chuỗi rỗng), nên đường "xác
    minh danh tính rồi mới SIGKILL" KHÔNG chạy được ở đây — nó vẫn được giữ cho môi trường khác,
    và khi không xác minh được thì nó TỪ CHỐI giết rồi báo ra, chứ không giết bừa.
    """
    if not pid or not _con_song(pid, tt):
        return True, "%sđã chết trước khi dọn" % (nhan and nhan + " ")
    ghi_chu = []
    try:
        if tt is not None:
            tt.terminate()
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError as e:                                                     # noqa: BLE001
        ghi_chu.append("SIGTERM lỗi: %s" % e)
    het = time.time() + 5.0
    while time.time() < het and _con_song(pid, tt):
        if tt is not None:
            try:
                tt.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
        else:
            time.sleep(0.2)
    if _con_song(pid, tt):
        if tt is not None:
            ghi_chu.append("còn sống sau SIGTERM ⇒ SIGKILL (là CON của chính tiến trình này, "
                           "PID chưa thể cấp lại)")
            try:
                tt.kill()
                tt.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as e:                # noqa: BLE001
                ghi_chu.append("SIGKILL lỗi: %s" % e)
        else:
            ten = ten_tien_trinh(pid)
            if "ython" in ten:
                ghi_chu.append("còn sống sau SIGTERM, tên tiến trình '%s' ⇒ SIGKILL" % ten)
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError as e:                                         # noqa: BLE001
                    ghi_chu.append("SIGKILL lỗi: %s" % e)
                het = time.time() + 5.0
                while time.time() < het and _con_song(pid, tt):
                    time.sleep(0.2)
            else:
                ghi_chu.append("CẢNH BÁO: pid %s còn sống nhưng KHÔNG xác minh được tên "
                               "(tên đọc ra '%s' — `ps` có thể bị sandbox chặn) ⇒ KHÔNG SIGKILL. "
                               "Kiểm tay: kill -0 %s" % (pid, ten, pid))
    song = _con_song(pid, tt)
    if song:
        ghi_chu.append("CẢNH BÁO: pid %s VẪN SỐNG sau khi dọn — còn tiến trình mồ côi" % pid)
        return False, "; ".join(ghi_chu)
    if not ghi_chu:
        # ĐƯỜNG SẠCH phải NÓI RA nó sạch. Trả chuỗi RỖNG ở đây là một lỗi đã đo được ở lượt
        # cổng #3: nơi in dùng `bc.get("don_pid") or "không có pid nào"`, nên một lượt dọn THÀNH
        # CÔNG hiện ra y như một lượt KHÔNG CÓ PID NÀO — đúng chỗ người đọc dùng để tin rằng
        # không còn tiến trình mồ côi. Ca `test_c6` ghim điều này.
        ghi_chu.append("%sđã tắt SẠCH theo ĐÚNG PID %s (SIGTERM, đã xác minh chết)"
                       % (nhan, pid))
    return True, "; ".join(ghi_chu)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# D. GHIM BINARY CHROMIUM — QA lượt sau phải dùng ĐÚNG binary này
# ══════════════════════════════════════════════════════════════════════════════════════════════
def ghim_chromium():
    """Trả dict {duong, ton_tai, phien_ban, sha256, byte, playwright}. Không ném ngoại lệ."""
    duong = os.path.join(GOC, BIN_CHROMIUM_TUONG_DOI)
    ra = {"duong": duong, "ton_tai": os.path.isfile(duong), "phien_ban": None,
          "sha256": None, "byte": None, "playwright": None}
    try:
        goi = os.path.join(GOC, "node_modules", "playwright-core", "package.json")
        with open(goi, encoding="utf-8") as f:
            ra["playwright"] = json.load(f).get("version")
    except (OSError, ValueError):                                            # noqa: BLE001
        pass
    if not ra["ton_tai"]:
        return ra
    ra["byte"] = os.path.getsize(duong)
    ra["sha256"] = sha256_tep(duong)
    try:
        tt = subprocess.run([duong, "--version"], capture_output=True, text=True, timeout=60)
        ra["phien_ban"] = (tt.stdout or tt.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:                        # noqa: BLE001
        ra["phien_ban"] = "KHÔNG hỏi được phiên bản: %s" % e
    return ra


def nhan_binary_thuc_su():
    """Hỏi THẲNG Playwright binary nó spawn (`DEBUG=pw:browser`), không suy từ tài liệu.

    Vì sao không đoán: `chromium.executablePath()` trả đường dẫn Chromium ĐẦY ĐỦ, còn chế độ
    headless của Playwright ≥1.49 spawn `chromium_headless_shell` — hai đường dẫn KHÁC NHAU. Ghi
    vào báo cáo đường dẫn sai là ghim nhầm thứ cho QA lượt sau.
    """
    ma_js = (
        'const {chromium}=require(%s);(async()=>{const b=await chromium.launch({headless:true});'
        'const p=await b.newPage();await p.goto("about:blank");await b.close();'
        'console.log("VERSION="+b.version());})().catch(e=>{console.error("LOI:"+e.message);'
        'process.exit(1)});' % json.dumps(os.path.join(GOC, "node_modules", "playwright-core")))
    env, _ = moi_truong_git_sach()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    env["DEBUG"] = "pw:browser"
    try:
        tt = subprocess.run(["node", "-e", ma_js], cwd=GOC, env=env,
                            capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as e:                        # noqa: BLE001
        return {"duong": None, "phien_ban": None, "loi": str(e)}
    van_ban = (tt.stdout or "") + (tt.stderr or "")
    m = re.search(r"<launching>\s+(\S+)", van_ban)
    v = re.search(r"VERSION=(\S+)", van_ban)
    return {"duong": m.group(1) if m else None,
            "phien_ban": v.group(1) if v else None,
            "loi": None if (m and v) else van_ban.strip()[-400:]}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# E. BỘ TỰ KIỂM — chứng minh cổng ĐỎ ĐƯỢC, ở CẢ HAI chiều, TRƯỚC khi tin nó báo XANH.
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Nguyên văn khối tổng kết của lượt chạy HỎNG 16:26 (chép từ log thật, không dựng lại).
LOG_HONG_THAT = """\
  5 failed
    [chromium] › thu_giao_dien/06_ban_phim.spec.js:374:1 › 05 — Đăng xuất bấm được bằng bàn phím
    [chromium] › thu_giao_dien/07_trang_tinh.spec.js:53:1 › 01 — không trang nào còn `<script>`
  14 did not run
  46 passed (1.6m)
"""
DONG_REFUSED_THAT = ("    Error: page.goto: net::ERR_CONNECTION_REFUSED at "
                     "http://127.0.0.1:18856/admin/index.html")


class TuKiem(unittest.TestCase):
    """Mọi ca ở đây chạy KHÔNG cần trình duyệt, KHÔNG cần mạng, KHÔNG cần máy chủ."""

    # ---------- bộ đọc ----------
    def test_a1_doc_dung_khoi_tong_ket_that(self):
        tk = doc_tong_ket(LOG_HONG_THAT)
        self.assertIsNotNone(tk, "không đọc được khối tổng kết thật ⇒ bộ đọc hỏng")
        self.assertEqual((tk["passed"], tk["failed"], tk["did_not_run"]), (46, 5, 14))

    def test_a2_doc_dung_luot_xanh(self):
        tk = doc_tong_ket("  65 passed (2.0m)\n")
        self.assertEqual((tk["passed"], tk["failed"], tk["skipped"], tk["did_not_run"]),
                         (65, 0, 0, 0))

    def test_a3_rac_thi_KHONG_doan_bua(self):
        """Không có dòng tổng kết ⇒ None. Đoán '0 hỏng' ở đây là bịa ra một lượt đạt."""
        self.assertIsNone(doc_tong_ket("Running 8 tests using 1 worker\n  ✓  1 abc\n"))
        self.assertIsNone(doc_tong_ket(""))
        self.assertIsNone(doc_tong_ket(None))

    def test_a4_dong_chay_ca_KHONG_bi_dem_thanh_tong_ket(self):
        """`  ✓   1 [chromium] › …` không được khớp thành '1 passed' — nếu khớp, mọi lượt chạy
        đều 'đạt' vì dòng đầu tiên ai cũng có."""
        tk = doc_tong_ket("  ✓   1 [chromium] › a.spec.js:1:1 › x\n  65 passed (2.0m)\n")
        self.assertEqual(tk["passed"], 65)

    def test_a5_dau_hieu_nen_chet(self):
        self.assertEqual(dau_hieu_nen_chet(DONG_REFUSED_THAT), ["ERR_CONNECTION_REFUSED"])
        self.assertEqual(dau_hieu_nen_chet(LOG_HONG_THAT), [])

    # ---------- phán quyết ----------
    def test_b1_xanh_thi_DAT(self):
        ma, nhan, _ = phan_quyet(doc_tong_ket("  65 passed (2.0m)\n"), True, 0)
        self.assertEqual((ma, nhan), (MA_DAT, "DAT"))

    def test_b2_hong_that_thi_HONG(self):
        """46/5/14 với máy chủ CÒN SỐNG là HỎNG SẢN PHẨM — không được gọi là đạt."""
        ma, nhan, ly = phan_quyet(doc_tong_ket(LOG_HONG_THAT), True, 1)
        self.assertEqual((ma, nhan), (MA_HONG, "HONG"))
        self.assertIn("did-not-run", ly)

    def test_b3_CUNG_con_so_ay_nhung_may_chu_chet_thi_HA_TANG_CHET(self):
        """ĐỐI CHỨNG QUYẾT ĐỊNH — chính là lượt 16:26. Cùng khối số, khác phán quyết."""
        ma, nhan, ly = phan_quyet(doc_tong_ket(LOG_HONG_THAT), False, 1)
        self.assertEqual((ma, nhan), (MA_HA_TANG, "HA_TANG_CHET"))
        self.assertNotEqual(ma, MA_HONG, "nền chết KHÔNG được báo thành sản phẩm hỏng")
        self.assertIn("HỆ QUẢ CỦA NỀN", ly)

    def test_b4_dau_hieu_refused_du_may_chu_con_song_van_la_HA_TANG(self):
        ma, nhan, _ = phan_quyet(doc_tong_ket(LOG_HONG_THAT), True, 1,
                                 dau_hieu=dau_hieu_nen_chet(DONG_REFUSED_THAT))
        self.assertEqual((ma, nhan), (MA_HA_TANG, "HA_TANG_CHET"))

    def test_b5_did_not_run_mot_minh_van_la_HONG(self):
        """Điều khoản 3 của nhiệm vụ: 'did not run' KHÔNG phải là đạt."""
        ma, nhan, ly = phan_quyet(doc_tong_ket("  63 passed\n  2 did not run\n"), True, 1)
        self.assertEqual((ma, nhan), (MA_HONG, "HONG"))
        self.assertIn("KHÔNG CHẠY", ly)

    def test_b6_skip_mot_minh_van_la_HONG(self):
        ma, _, ly = phan_quyet(doc_tong_ket("  64 passed\n  1 skipped\n"), True, 0)
        self.assertEqual(ma, MA_HONG)
        self.assertIn("BỎ QUA", ly)

    def test_b7_bo_thu_co_lai_thi_BAT_DUOC(self):
        """12 ca đạt, 0 hỏng, thoát 0 — vẫn HỎNG vì GHIM 65. Đây là kiểu hỏng im lặng nhất."""
        ma, _, ly = phan_quyet(doc_tong_ket("  12 passed (55.3s)\n"), True, 0)
        self.assertEqual(ma, MA_HONG)
        self.assertIn("GHIM", ly)

    def test_b8_bo_thu_phinh_ra_cung_BAT_DUOC(self):
        ma, _, _ = phan_quyet(doc_tong_ket("  66 passed (2.0m)\n"), True, 0)
        self.assertEqual(ma, MA_HONG, "thêm ca mà không cập nhật ghim thì phải lộ ra, không im")

    def test_b9_khong_doc_duoc_thi_KHONG_DO_DUOC_chu_khong_phai_DAT(self):
        ma, nhan, _ = phan_quyet(None, True, 0)
        self.assertEqual((ma, nhan), (MA_KHONG_DO, "KHONG_DO_DUOC"))

    def test_b10_bon_phan_quyet_BON_MA_KHAC_NHAU(self):
        ma_bo = {MA_DAT, MA_HONG, MA_HA_TANG, MA_KHONG_DO}
        self.assertEqual(len(ma_bo), 4)
        self.assertEqual((MA_DAT, MA_HONG, MA_NEN, MA_HA_TANG, MA_KHONG_DO), (0, 1, 2, 3, 4))

    # ---------- cổng ----------
    def test_c1_tim_cong_rong_tra_cong_THAT_SU_rong(self):
        cong = tim_cong_rong(dai=(18000, 19999))
        self.assertIsNotNone(cong)
        self.assertFalse(cong_dang_dung(cong), "cổng 'rỗng' mà lại có người nghe ⇒ bộ chọn hỏng")

    def test_c2_cong_DANG_BI_CHIEM_thi_phai_thay_la_ban(self):
        """ĐỐI CHỨNG ÂM: tự chiếm một cổng rồi đòi `cong_dang_dung` nói CÓ."""
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        cong = s.getsockname()[1]
        try:
            self.assertTrue(cong_dang_dung(cong), "cổng đang bị chiếm mà báo rỗng ⇒ bộ dò hỏng")
        finally:
            s.close()

    def test_c3_pid_khong_ton_tai_thi_khong_keu_con_song(self):
        self.assertFalse(tien_trinh_con_song(99999999))
        self.assertFalse(tien_trinh_con_song(0))

    def test_c4_dong_theo_pid_khong_nem_voi_pid_chet(self):
        da_chet, ghi_chu = dong_theo_pid(99999999)
        self.assertTrue(da_chet)
        self.assertIn("đã chết", ghi_chu)

    def test_c5_KHONG_keu_ZOMBIE_la_con_song(self):
        """ĐỐI CHỨNG DƯƠNG cho một lỗi ĐÃ ĐO ĐƯỢC ở lượt cổng đầu tiên (pid 46403).

        Bộ dọn cũ hỏi `os.kill(pid, 0)` — nó THÀNH CÔNG với tiến trình ZOMBIE (con đã chết
        nhưng chưa `wait()`), nên bộ dọn báo "còn sống" cho một máy chủ đã chết hẳn, rồi TỪ CHỐI
        `SIGKILL` vì không đọc được tên qua `ps` (bị sandbox chặn). Ca này dựng ĐÚNG tình huống
        ấy bằng một tiến trình con THẬT và đòi bộ dọn phải nói CHẾT.
        """
        tt = subprocess.Popen(["sleep", "30"])
        try:
            time.sleep(0.4)
            self.assertTrue(tien_trinh_con_song(tt.pid), "đối chứng dương hỏng: `sleep` phải sống")
            da_chet, ghi_chu = dong_theo_pid(tt.pid, nhan="thử ", tt=tt)
            self.assertTrue(da_chet, "con của CHÍNH mình đã SIGTERM mà vẫn báo SỐNG: %s" % ghi_chu)
            self.assertIsNotNone(tt.poll(), "tiến trình con chưa được thu lại (còn zombie)")
        finally:
            if tt.poll() is None:
                tt.kill()
                tt.wait(timeout=5)

    def test_c6_duong_don_SACH_phai_NOI_RA_la_sach(self):
        """Lỗi đã đo được ở lượt cổng #3: dọn thành công mà ghi chú RỖNG.

        Nơi in dịch chuỗi rỗng thành "không có pid nào", nên một lượt tắt máy chủ SẠCH hiện ra y
        như một lượt không hề có pid — người đọc mất đúng dòng để tin là không còn mồ côi.
        """
        tt = subprocess.Popen(["sleep", "30"])
        try:
            time.sleep(0.4)
            da_chet, ghi_chu = dong_theo_pid(tt.pid, nhan="máy chủ ", tt=tt)
            self.assertTrue(da_chet)
            self.assertTrue(ghi_chu.strip(),
                            "đường dọn SẠCH trả ghi chú RỖNG ⇒ nơi in sẽ hiện 'không có pid nào'")
            self.assertIn("SẠCH", ghi_chu)
            self.assertIn(str(tt.pid), ghi_chu)
        finally:
            if tt.poll() is None:
                tt.kill()
                tt.wait(timeout=5)

    # ---------- ghim binary ----------
    def test_d1_binary_chromium_co_that_va_goi_duoc(self):
        g = ghim_chromium()
        if not g["ton_tai"]:
            self.skipTest("chưa cài Chromium của Playwright — chạy: "
                          "PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium")
        self.assertGreater(g["byte"], 1_000_000, "binary Chromium nhỏ bất thường")
        self.assertRegex(g["phien_ban"] or "", r"Chromium \d+\.\d+\.\d+\.\d+")
        self.assertRegex(g["sha256"] or "", r"^[0-9a-f]{64}$")

    def test_d2_binary_that_su_duoc_spawn_khop_voi_ghim(self):
        """Ghim đường dẫn mà không hỏi Playwright thì có ngày ghim nhầm binary khác."""
        g = ghim_chromium()
        if not g["ton_tai"]:
            self.skipTest("chưa cài Chromium của Playwright")
        t = nhan_binary_thuc_su()
        if t["duong"] is None:
            self.skipTest("không hỏi được Playwright binary nó spawn: %s" % t["loi"])
        self.assertEqual(os.path.realpath(t["duong"]), os.path.realpath(g["duong"]),
                         "binary Playwright SPAWN khác binary tài liệu GHIM")
        self.assertIn(t["phien_ban"], g["phien_ban"])

    def test_d3_khong_mo_CHO_PHEP_LIVE(self):
        """Bất biến của brief: adapter hãng phải ĐÓNG. Kiểm bằng mã, không bằng lời hứa.

        Phải IMPORT các adapter cụ thể trước: `danh_sach_hang()` chỉ liệt kê cái đã đăng ký, nên
        gọi trần nó trả `{}` — và một phép kiểm trên sổ RỖNG thì luôn xanh một cách vô nghĩa.
        """
        duong_app = os.path.join(GOC, "app")
        if duong_app not in sys.path:
            sys.path.insert(0, duong_app)
        import adapter                                                        # noqa: PLC0415
        import adapter_jt                                                     # noqa: PLC0415
        import adapter_vtp                                                    # noqa: PLC0415
        self.assertIs(adapter.CarrierAdapter.CHO_PHEP_LIVE, False,
                      "CHO_PHEP_LIVE của lớp nền đang MỞ ⇒ lượt chạy sẽ gọi ra hãng thật. DỪNG.")
        ds = adapter.danh_sach_hang()
        self.assertTrue(ds, "sổ đăng ký adapter RỖNG ⇒ phép kiểm 'không hãng nào mở live' "
                            "đang kiểm một tập rỗng, tức không kiểm gì")
        mo = sorted(m for m, t in ds.items() if t.get("live_mo"))
        self.assertEqual(mo, [], "hãng đang MỞ live: %s" % mo)
        for ten, mod in (("jt", adapter_jt), ("vtp", adapter_vtp)):
            for gia_tri in vars(mod).values():
                if isinstance(gia_tri, type) and issubclass(gia_tri, adapter.CarrierAdapter):
                    self.assertIs(gia_tri.CHO_PHEP_LIVE, False,
                                  "%s.%s.CHO_PHEP_LIVE đang MỞ" % (ten, gia_tri.__name__))

    def test_d4_ghep_hai_gia_dinh_GIT_CONFIG(self):
        """`GIT_CONFIG_COUNT` dị dạng phải bị gỡ KÈM CẢNH BÁO; hợp lệ thì KHÔNG được đụng."""
        cu = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update({"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_VALUE_0": "a",
                               "GIT_CONFIG_VALUE_1": "b"})
            _, cb = moi_truong_git_sach()
            self.assertTrue(cb, "gia đình dị dạng mà KHÔNG cảnh báo ⇒ gỡ trong im lặng")
            os.environ.clear()
            os.environ.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name",
                               "GIT_CONFIG_VALUE_0": "x"})
            for ten in [k for k in os.environ if k.startswith("GIT_CONFIG_")]:
                os.environ.pop(ten, None)
            os.environ.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name",
                               "GIT_CONFIG_VALUE_0": "x"})
            env, cb2 = moi_truong_git_sach()
            self.assertEqual(cb2, [], "cấu hình HỢP LỆ mà bị gỡ ⇒ nuốt một cấu hình thật")
            self.assertEqual(env.get("GIT_CONFIG_COUNT"), "1")
        finally:
            os.environ.clear()
            os.environ.update(cu)

    def test_d5_ghim_so_ca_khop_voi_danh_sach_that(self):
        """GHIM 65 phải khớp số ca Playwright THẬT SỰ liệt kê. Lệch ⇒ ghim đã cũ, và một cái
        ghim cũ sẽ làm cổng đỏ oan (hoặc xanh oan) mà không ai biết vì sao."""
        env, _ = moi_truong_git_sach()
        env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        env["VIP_GD_GOC"] = "http://127.0.0.1:1"      # chỉ ĐẾM, không kết nối
        try:
            tt = subprocess.run(["npx", "playwright", "test", "--list", "--reporter=list"],
                                cwd=GOC, env=env, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.SubprocessError) as e:                    # noqa: BLE001
            self.skipTest("không chạy được `playwright test --list`: %s" % e)
        if tt.returncode != 0:
            self.skipTest("`--list` hỏng (mã %s): %s" % (tt.returncode, tt.stderr.strip()[-300:]))
        tong = sum(1 for d in tt.stdout.splitlines()
                   if re.match(r"^\s*\[chromium\] › ", d))
        self.assertGreater(tong, 0, "không đếm được ca nào từ `--list` ⇒ bộ đếm hỏng")
        self.assertEqual(tong, SO_CA_GHIM,
                         "số ca THẬT (%d) khác GHIM (%d)" % (tong, SO_CA_GHIM))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# F. CHẠY CỔNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _in(giu, dong):
    print(dong, flush=True)
    giu.append(dong)


def chay_cong(so_ca_ghim=SO_CA_GHIM, giu_nen=False, duong_log=None, ghi_chu=None):
    """Chạy trọn bộ tầng 3 trên nền cô lập. Trả (mã thoát, báo cáo dict)."""
    giu = ghi_chu if ghi_chu is not None else []
    bc = {"so_ca_ghim": so_ca_ghim, "gio": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    # ---- điều kiện tiên quyết, KIỂM TRƯỚC khi dựng nền ----
    if not os.path.isdir(os.path.join(GOC, "node_modules", "@playwright", "test")):
        _in(giu, "CHƯA CÀI Playwright. Chạy:  npm install")
        return MA_NEN, bc
    if shutil.which("npx") is None:
        _in(giu, "KHÔNG có `npx` trong PATH.")
        return MA_NEN, bc
    bind = os.environ.get("VIP_HUB_BIND")
    if bind and bind not in ("127.0.0.1", "localhost", "::1"):
        _in(giu, "TỪ CHỐI CHẠY: VIP_HUB_BIND=%s — cổng này chỉ chạy khi bind 127.0.0.1." % bind)
        return MA_NEN, bc

    env, canh_bao = moi_truong_git_sach()
    for c in canh_bao:
        _in(giu, "[cảnh báo] " + c)
    bc["canh_bao_git"] = canh_bao
    ma_head, head = git("rev-parse", "HEAD")
    bc["head"] = head if ma_head == 0 else None
    ma_st, _ = git("status", "--porcelain")
    bc["git_do"] = (ma_st != 0)
    bc["sha_san_pham"] = {}
    for ten in ("admin/ban_phim.js", "admin/billing.js", "admin/admin.js", "app/server.py"):
        d = os.path.join(GOC, ten)
        if os.path.isfile(d):
            bc["sha_san_pham"][ten] = sha256_tep(d)[:8]

    # ---- ghim binary ----
    g = ghim_chromium()
    bc["chromium_ghim"] = {k: g[k] for k in ("duong", "ton_tai", "phien_ban", "sha256", "byte")}
    bc["playwright"] = g["playwright"]
    if not g["ton_tai"]:
        _in(giu, "KHÔNG có binary Chromium của Playwright: %s" % g["duong"])
        _in(giu, "   cài:  PLAYWRIGHT_BROWSERS_PATH=0 npx playwright install chromium")
        return MA_NEN, bc

    # ---- cổng + nền ----
    cong = tim_cong_rong()
    if cong is None:
        _in(giu, "KHÔNG tìm được cổng rỗng trong dải %s-%s" % DAI_CONG)
        return MA_NEN, bc
    nen = tempfile.mkdtemp(prefix="veh-g22-e2e.")
    bc["cong"], bc["nen"] = cong, nen
    goc_url = "http://127.0.0.1:%d" % cong
    bc["goc_url"] = goc_url
    tep_log = duong_log or os.path.join(tempfile.gettempdir(),
                                        "veh-g22-e2e-%d.log" % int(time.time()))
    bc["log_playwright"] = tep_log

    env = dict(env)
    env["VIP_HUB_DATA"] = nen
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    pid = None
    sv = None
    sv_log = None
    try:
        for lenh, ten in ((["python3", "app/migrate.py"], "migrate"),
                          (["python3", "app/khoi_tao.py"], "seed")):
            tt = subprocess.run(lenh, cwd=GOC, env=env, capture_output=True, text=True, timeout=300)
            if tt.returncode != 0:
                _in(giu, "NỀN KHÔNG DỰNG ĐƯỢC: `%s` thoát %s\n%s"
                    % (" ".join(lenh), tt.returncode, (tt.stderr or tt.stdout).strip()[-600:]))
                return MA_NEN, bc
        tt = subprocess.run(["python3", "thu_giao_dien/chuan_bi.py", "mk"], cwd=GOC, env=env,
                            capture_output=True, text=True, timeout=300)
        if tt.returncode != 0:
            _in(giu, "NỀN KHÔNG DỰNG ĐƯỢC: `chuan_bi.py mk` thoát %s\n%s"
                % (tt.returncode, (tt.stderr or tt.stdout).strip()[-600:]))
            return MA_NEN, bc

        # GIỮ log máy chủ — đây chính là thứ `chay.sh` xoá mất khi dọn nền, và là thứ duy nhất
        # nói được VÌ SAO máy chủ chết.
        sv_log = open(os.path.join(tempfile.gettempdir(), "veh-g22-may-chu-%d.log" % cong),
                      "w", encoding="utf-8")
        bc["log_may_chu"] = sv_log.name
        sv = subprocess.Popen(["python3", "app/server.py", str(cong)], cwd=GOC, env=env,
                              stdout=sv_log, stderr=subprocess.STDOUT)
        pid = sv.pid
        bc["pid_may_chu"] = pid
        het = time.time() + 20.0
        while time.time() < het:
            if cong_dang_dung(cong):
                break
            if not tien_trinh_con_song(pid):
                sv_log.flush()
                _in(giu, "MÁY CHỦ CHẾT NGAY KHI KHỞI ĐỘNG (pid %s). 30 dòng cuối:" % pid)
                _in(giu, _duoi_tep(sv_log.name, 30))
                return MA_NEN, bc
            time.sleep(0.2)
        if not cong_dang_dung(cong):
            _in(giu, "máy chủ KHÔNG mở cổng %s sau 20 giây." % cong)
            return MA_NEN, bc

        tt = subprocess.run(["python3", "thu_giao_dien/chuan_bi.py", "don", goc_url],
                            cwd=GOC, env=env, capture_output=True, text=True, timeout=300)
        bc["chuan_bi_don"] = tt.returncode
        if tt.returncode != 0:
            _in(giu, "NỀN KHÔNG DỰNG ĐƯỢC: `chuan_bi.py don` thoát %s\n%s"
                % (tt.returncode, (tt.stderr or tt.stdout).strip()[-600:]))
            return MA_NEN, bc

        # ---- CHẠY ----
        env["VIP_GD_GOC"] = goc_url
        env["VIP_GD_NEN"] = nen
        env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        lenh = ["npx", "playwright", "test"]
        bc["lenh_that"] = " ".join(lenh)
        _in(giu, "[g22] nền=%s cổng=%s pid=%s" % (nen, cong, pid))
        _in(giu, "[g22] %s" % bc["lenh_that"])
        with open(tep_log, "w", encoding="utf-8") as f:
            f.write("LENH: %s\nNEN: %s\nCONG: %s\nPID: %s\n%s\n"
                    % (bc["lenh_that"], nen, cong, pid, "-" * 60))
            f.flush()
            tt = subprocess.run(lenh, cwd=GOC, env=env, stdout=f, stderr=subprocess.STDOUT)
            ma_pw = tt.returncode
        with open(tep_log, encoding="utf-8", errors="replace") as f:
            van_ban = f.read()
        bc["ma_playwright"] = ma_pw
        _in(giu, "[g22] mã thoát playwright (THẬT, ghi trước mọi pipe) = %s" % ma_pw)

        # ---- máy chủ còn sống? ----
        may_chu_song = tien_trinh_con_song(pid)
        bc["may_chu_song_cuoi"] = may_chu_song
        dau_hieu = dau_hieu_nen_chet(van_ban)
        bc["dau_hieu_nen_chet"] = dau_hieu
        tk = doc_tong_ket(van_ban)
        bc["dem"] = tk
        if not may_chu_song:
            sv_log.flush()
            _in(giu, "[g22] MÁY CHỦ ĐÃ CHẾT giữa lượt. 30 dòng cuối log máy chủ:")
            _in(giu, _duoi_tep(sv_log.name, 30))
        ma, nhan, ly = phan_quyet(tk, may_chu_song, ma_pw, so_ca_ghim, dau_hieu)
        bc.update({"ma": ma, "nhan": nhan, "ly_do": ly})
        return ma, bc
    finally:
        if sv_log is not None:
            try:
                sv_log.close()
            except OSError:
                pass
        da_chet, ghi_chu = dong_theo_pid(pid, nhan="máy chủ ", tt=sv)
        if pid:
            bc["don_pid"] = ghi_chu
            if not da_chet:
                _in(giu, "[g22] CẢNH BÁO: %s" % ghi_chu)
        if pid and cong_dang_dung(cong) and not _con_song(pid, sv):
            _in(giu, "[g22] CẢNH BÁO: cổng %s vẫn có người nghe sau khi máy chủ chết — "
                     "kiểm tay: lsof -nP -iTCP:%s" % (cong, cong))
        bc["con_mo_coi"] = _con_song(pid, sv)
        if giu_nen:
            _in(giu, "[g22] giữ nền theo yêu cầu: %s" % nen)
        else:
            shutil.rmtree(nen, ignore_errors=True)


def _duoi_tep(duong, so_dong):
    try:
        with open(duong, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-so_dong:]).rstrip()
    except OSError as e:                                                     # noqa: BLE001
        return "(không đọc được %s: %s)" % (duong, e)


def in_bang_chung(bc, giu=None):
    giu = giu if giu is not None else []
    g = bc.get("chromium_ghim", {})
    tk = bc.get("dem") or {}
    _in(giu, "")
    _in(giu, "════════════════ BẰNG CHỨNG CỔNG E2E TẦNG 3 (G22 · AG-06) ════════════════")
    _in(giu, "  lệnh thật           : %s" % bc.get("lenh_that", "(chưa chạy)"))
    _in(giu, "  mã thoát playwright : %s" % bc.get("ma_playwright"))
    _in(giu, "  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : %s/%s/%s/%s/%s  (ghim ĐẠT = %s)"
        % (tk.get("passed"), tk.get("failed"), tk.get("skipped"), tk.get("did_not_run"),
           tk.get("flaky"), bc.get("so_ca_ghim")))
    _in(giu, "  máy chủ còn sống    : %s   (pid %s)" % (bc.get("may_chu_song_cuoi"),
                                                       bc.get("pid_may_chu")))
    _in(giu, "  dấu hiệu nền chết   : %s" % (bc.get("dau_hieu_nen_chet") or "không"))
    _in(giu, "  cổng / nền          : %s / %s" % (bc.get("cong"), bc.get("nen")))
    _in(giu, "  Chromium (GHIM)     : %s" % g.get("duong"))
    _in(giu, "  Chromium phiên bản  : %s" % g.get("phien_ban"))
    _in(giu, "  Chromium sha256     : %s  (%s byte)" % (g.get("sha256"), g.get("byte")))
    _in(giu, "  playwright          : %s" % bc.get("playwright"))
    _in(giu, "  HEAD                : %s" % bc.get("head"))
    _in(giu, "  sha[:8] sản phẩm    : %s" % json.dumps(bc.get("sha_san_pham", {}),
                                                          ensure_ascii=False))
    _in(giu, "  log playwright      : %s" % bc.get("log_playwright"))
    _in(giu, "  log máy chủ         : %s" % bc.get("log_may_chu"))
    _in(giu, "  dọn tiến trình      : %s" % (bc.get("don_pid") or "không có pid nào"))
    _in(giu, "  còn mồ côi          : %s" % bc.get("con_mo_coi"))
    _in(giu, "  ── PHÁN QUYẾT: %s (mã thoát %s)" % (bc.get("nhan"), bc.get("ma")))
    _in(giu, "     %s" % bc.get("ly_do"))
    _in(giu, "══════════════════════════════════════════════════════════════════════════════")
    return giu


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Cổng E2E tầng 3 (Chromium thật) — phân biệt sản phẩm hỏng với nền chết.")
    ap.add_argument("--tu-kiem", action="store_true",
                    help="chạy bộ tự kiểm của chính cổng (không cần trình duyệt)")
    ap.add_argument("--ghim-chromium", action="store_true",
                    help="in đường dẫn/phiên bản/sha256 của binary Chromium rồi thoát")
    ap.add_argument("--so-ca", type=int, default=int(os.environ.get("VIP_E2E_SO_CA", SO_CA_GHIM)),
                    help="ghim số ca ĐẠT (mặc định %d)" % SO_CA_GHIM)
    ap.add_argument("--giu-nen", action="store_true", help="không xoá thư mục nền sau khi chạy")
    ap.add_argument("--log", default=None, help="chỗ ghi log playwright thô")
    ap.add_argument("--json", default=None, help="ghi báo cáo JSON ra tệp này")
    a = ap.parse_args(argv)

    if a.ghim_chromium:
        g = ghim_chromium()
        t = nhan_binary_thuc_su()
        print(json.dumps({"ghim": g, "thuc_su_spawn": t}, ensure_ascii=False, indent=2))
        return 0 if (g["ton_tai"] and t["duong"]) else MA_NEN

    if a.tu_kiem:
        # `--tu-kiem` phải chạy được CẢ KHI chưa cài Chromium: ca d1/d2 tự `skipTest` kèm lý do.
        import io
        buf = io.StringIO()
        kq = unittest.TextTestRunner(stream=buf, verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(TuKiem))
        print(buf.getvalue().rstrip())
        print("TỰ KIỂM: %d ca · hỏng %d · lỗi %d · bỏ qua %d"
              % (kq.testsRun, len(kq.failures), len(kq.errors), len(kq.skipped)))
        return MA_DAT if kq.wasSuccessful() else MA_HONG

    giu = []
    ma, bc = chay_cong(so_ca_ghim=a.so_ca, giu_nen=a.giu_nen, duong_log=a.log, ghi_chu=giu)
    in_bang_chung(bc, giu)
    if a.json:
        try:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(bc, f, ensure_ascii=False, indent=2)
        except OSError as e:                                                 # noqa: BLE001
            print("[g22] không ghi được %s: %s" % (a.json, e))
    print("[g22] MÃ THOÁT CỦA CỔNG = %s" % ma)
    return ma


if __name__ == "__main__":
    sys.exit(main())
