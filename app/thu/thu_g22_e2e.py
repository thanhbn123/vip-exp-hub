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
import threading
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

# Nguyên văn dòng của `chay.sh` — lượt BẢN CŨ (7d946928) có ca hỏng: dòng PHẠM VI BIẾN MẤT.
# Hai dòng đầu chép từ /tmp/ag06-t4-cu.log (lượt đo 16/10/2026, dispatch 2). Hai dòng sau GHÉP
# THÊM (ghi rõ để không ai đọc thành log thật): bản cũ KHÔNG BAO GIỜ in được chúng, vì `set -e`
# thoát trước — chúng ở đây để thử bộ đọc ở nhánh "máy chủ chết từ ngoài mà thiếu dòng PHẠM VI".
LOG_RUNNER_MAT_PHAM_VI = """\
[giao-dien] nền=/var/folders/v1/T/veh-giao-dien.hbFKDa cổng=19629 pid=38879
  1 failed
    [chromium] › thu_giao_dien/_tu_kiem_chay_sh_tam.spec.js:4:1 › CA HỎNG CỐ Ý — 1 phải bằng 2 ─────
[giao-dien] mã thoát THẬT 1
[giao-dien] máy chủ pid 38879 bị GIẾT BẰNG TÍN HIỆU: mã 137 = SIGKILL(9) — tín hiệu KHÔNG do bộ dọn gửi
"""
# Nguyên văn dòng của `chay.sh` BẢN ĐÃ VÁ, lượt chạy xanh (chép từ /tmp/ag06-luot1.log).
LOG_RUNNER_DAY_DU = """\
[giao-dien] PHẠM VI: chỉ Chromium (bản Playwright trong node_modules) · chỉ ba bề rộng 375/768/1280
[giao-dien] nền=/var/folders/v1/T/veh-giao-dien.ukKOHj cổng=18733 pid=79195
  65 passed (1.9m)
[giao-dien] mã thoát THẬT 0
[giao-dien] PHẠM VI (in lại khi kết thúc): chỉ Chromium (bản Playwright trong node_modules) · chỉ ba
[giao-dien] máy chủ pid 79195 còn sống khi lượt kết thúc
[giao-dien] bộ dọn đã tắt máy chủ pid 79195: mã 143 = SIGTERM(15) — tín hiệu do CHÍNH bộ dọn gửi
"""


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

    # ---------- ĐO GIỚI HẠN TIẾN TRÌNH (việc 2 · dispatch 2) ----------
    def test_e1_phat_hien_chet_tu_day_mau(self):
        """Hàm thuần: dãy mẫu "sống → chết" phải cho ra ĐÚNG giây chết; dãy sống suốt phải None.

        ĐỐI CHỨNG ÂM của phép đo cái chết: một bộ dò luôn nói "còn sống" thì không đo được gì,
        nên ca này đòi nó nói CHẾT ở dãy có mẫu chết VÀ nói SỐNG ở dãy không có mẫu chết."""
        song = [{"giay": g, "song": True, "sk": True} for g in (0.0, 0.4, 0.8)]
        self.assertEqual(phat_hien_chet(song)[0], None)
        chet = song + [{"giay": 1.2, "song": False, "sk": False}]
        giay, chi_so, ly = phat_hien_chet(chet)
        self.assertEqual((giay, chi_so), (1.2, 3))
        self.assertIn("không còn sống", ly)
        # Cổng ngừng trả lời NHƯNG tiến trình vẫn "sống" (đứng hình) cũng phải bị bắt:
        dung_hinh = song + [{"giay": 1.2, "song": True, "sk": False}]
        giay2, _, ly2 = phat_hien_chet(dung_hinh)
        self.assertEqual(giay2, 1.2)
        self.assertIn("ngừng trả lời", ly2)

    def test_e2_doc_dong_runner_bat_dung_PHAM_VI_va_ma_that(self):
        """Bộ đọc dòng của `chay.sh` phải ĐỎ ĐƯỢC: có dòng PHẠM VI ⇒ thấy; thiếu ⇒ BÁO THIẾU."""
        du = doc_dong_runner(LOG_RUNNER_MAT_PHAM_VI)
        self.assertEqual(du["pham_vi"], 0, "log KHÔNG có dòng PHẠM VI mà bộ đọc nói có")
        self.assertFalse(du["co_pham_vi"])
        self.assertEqual(du["ma_that"], 1)
        self.assertEqual((du["cong"], du["pid"]), (19629, 38879))
        self.assertTrue(du["chet_giua_luot"])
        self.assertEqual(du["ma_tin_hieu"], 137)
        self.assertIn("SIGKILL", du["tin_hieu"])
        self.assertFalse(du["tu_don"], "chết từ NGOÀI mà bộ đọc gán cho bộ dọn")
        day_du = doc_dong_runner(LOG_RUNNER_DAY_DU)
        self.assertEqual(day_du["pham_vi"], 2)
        self.assertTrue(day_du["co_pham_vi"])
        self.assertEqual(day_du["ma_that"], 0)
        self.assertFalse(day_du["chet_giua_luot"])

    def test_e3_chay_sh_thoat_som_van_in_PHAM_VI_va_giu_ma_thoat(self):
        """ĐỐI CHỨNG DƯƠNG, chạy THẬT: cây tạm thiếu Playwright ⇒ `chay.sh` thoát sớm mã 2.

        Bản CŨ (`set -e` nuốt) vẫn thoát 2 nhưng KHÔNG in dòng PHẠM VI ở cuối; bản này phải in.
        """
        with tempfile.TemporaryDirectory(prefix="veh-ag06-e3.") as t:
            os.makedirs(os.path.join(t, "thu_giao_dien"))
            shutil.copy(os.path.join(THU_GD, "chay.sh"), os.path.join(t, "thu_giao_dien", "chay.sh"))
            os.makedirs(os.path.join(t, "node_modules"))
            tt = subprocess.run(["sh", os.path.join(t, "thu_giao_dien", "chay.sh")],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(tt.returncode, 2, "mã thoát THẬT của đường thoát sớm bị nuốt")
        van_ban = tt.stdout + tt.stderr
        self.assertIn("mã thoát THẬT 2", van_ban)
        self.assertGreaterEqual(doc_dong_runner(van_ban)["pham_vi"], 1,
                                "thoát sớm mà KHÔNG in dòng PHẠM VI ⇒ bản vá hỏng")

    def test_e4_chay_sh_nen_hong_van_giu_ma_thoat(self):
        """Đường thoát sớm THỨ HAI (nền không dựng được) cũng phải in PHẠM VI + giữ mã thoát."""
        with tempfile.TemporaryDirectory(prefix="veh-ag06-e4.") as t:
            os.makedirs(os.path.join(t, "thu_giao_dien"))
            shutil.copy(os.path.join(THU_GD, "chay.sh"), os.path.join(t, "thu_giao_dien", "chay.sh"))
            os.makedirs(os.path.join(t, "node_modules", "@playwright", "test"))
            tt = subprocess.run(["sh", os.path.join(t, "thu_giao_dien", "chay.sh")],
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(tt.returncode, 2, "nền hỏng mà mã thoát không phải 2")
        van_ban = tt.stdout + tt.stderr
        self.assertIn("NỀN KHÔNG DỰNG ĐƯỢC", van_ban)
        self.assertGreaterEqual(doc_dong_runner(van_ban)["pham_vi"], 1)

    def test_e5_bo_do_gioi_han_DO_DUOC_fd_cong_va_cai_CHET(self):
        """ĐỐI CHỨNG DƯƠNG của BỘ ĐO: dựng một tiến trình THẬT, đo được fd + cổng đang nghe, rồi
        GIẾT nó và đòi bộ đo phải BẮT ĐƯỢC cái chết. Một bộ đo chưa từng thấy cái chết thì không
        chứng minh được gì về những lượt "không thấy chết"."""
        cong = tim_cong_rong(dai=(18100, 18299))
        self.assertIsNotNone(cong)
        tt = subprocess.Popen(["python3", "-m", "http.server", str(cong), "--bind", "127.0.0.1"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            het = time.time() + 10
            while time.time() < het and not cong_dang_dung(cong):
                time.sleep(0.1)
            self.assertTrue(cong_dang_dung(cong), "không dựng được tiến trình để đo")
            bd = BoDoGioiHan(tt.pid, cong, nhip=0.2)
            m1 = bd.lay_mau()
            self.assertTrue(m1["song"], "bộ đo nói CHẾT về một tiến trình đang sống")
            self.assertIsNotNone(m1["fd"], "không đo được số mô tả tệp (lsof)")
            self.assertGreater(m1["fd"], 0)
            self.assertIn(str(cong), m1["nghe"] or [], "không thấy cổng đang nghe ⇒ đo cổng hỏng")
            self.assertTrue(m1["sk"], "cổng đang mở mà phép đo sức khỏe nói hỏng")
            tt.kill()
            tt.wait(timeout=10)
            time.sleep(0.3)
            m2 = bd.lay_mau()
            self.assertFalse(m2["song"], "tiến trình đã bị giết mà bộ đo vẫn nói SỐNG")
            giay, _, _ = phat_hien_chet(bd.mau)
            self.assertIsNotNone(giay, "bộ đo KHÔNG bắt được cái chết ⇒ mọi lượt 'không chết' "
                                       "của nó là vô nghĩa")
        finally:
            if tt.poll() is None:
                tt.kill()
                tt.wait(timeout=5)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# G. ĐO GIỚI HẠN TIẾN TRÌNH CỦA CHÍNH LƯỢT CHẠY (việc 2 · dispatch 2)
#
# CÂU HỎI: 3/9 lượt `chay.sh` trước đây có MÁY CHỦ BỊ GIẾT TỪ NGOÀI giữa lượt (log đứt giữa dòng,
# 0 traceback, 20/22 dòng lỗi là ERR_CONNECTION_REFUSED). Đĩa/bộ nhớ/pkill/HTML reporter đã bị
# loại. Phần còn lại phải ĐO ĐƯỢC, không được đoán: mô tả tệp đang mở (so với `ulimit -n`), số ổ
# cắm TCP, cổng đang nghe, số tiến trình con, thời gian sống — và TÍN HIỆU làm nó chết.
#
# HAI LUẬT CỦA PHẦN NÀY:
#   (1) KHÔNG đo được thì ghi `None`, KHÔNG ghi 0. "0 mô tả tệp" và "không đo được" là hai
#       chuyện khác nhau; gộp chúng là bịa ra một phép đo.
#   (2) Phép đo phải BẮT ĐƯỢC CÁI CHẾT (ca tự kiểm `e5` + `--giet-luc`), nếu không thì mọi lượt
#       "không thấy chết" đều vô nghĩa.
# ══════════════════════════════════════════════════════════════════════════════════════════════
NHIP_MAU = 0.4          # giây giữa hai mẫu
HET_LUOT_MAC_DINH = 900  # giây: trần cứng cho một lượt `chay.sh` (một lượt thật ~2 phút)


def _lsof(tham_so, het=15):
    """Chạy `lsof`. Trả stdout, hoặc None nếu KHÔNG chạy được (thiếu lsof / bị chặn)."""
    try:
        tt = subprocess.run(["lsof"] + list(tham_so), capture_output=True, text=True, timeout=het)
    except (OSError, subprocess.SubprocessError):                            # noqa: BLE001
        return None
    return tt.stdout


def dem_fd(pid):
    """Số MÔ TẢ TỆP đang mở. None = không đo được (KHÔNG được trả 0)."""
    ra = _lsof(["-p", str(pid), "-F", "f"])
    if ra is None:
        return None
    return sum(1 for d in ra.splitlines() if d.startswith("f"))


def dem_con(pid):
    """Số tiến trình con TRỰC TIẾP (`pgrep -P`). None = không đo được."""
    try:
        tt = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):                            # noqa: BLE001
        return None
    if tt.returncode not in (0, 1):        # 1 = không có con nào (đo được, bằng 0)
        return None
    return len(tt.stdout.split())


def o_cam_tcp(pid):
    """(số ổ cắm TCP, danh sách cổng ĐANG NGHE) — (None, None) nếu không đo được.

    Định dạng `lsof -F fTn` là ba dòng LIỀN NHAU cho mỗi mô tả tệp: `f<fd>`, `n<địa chỉ>`,
    `TST=<trạng thái>` — nên phải gom theo fd rồi mới xét, không được đọc `n` trước `TST`
    (lượt tự kiểm đầu tiên của ca `e5` ĐỎ đúng vì đọc sai thứ tự này)."""
    ra = _lsof(["-nP", "-p", str(pid), "-a", "-iTCP", "-F", "fTn"])
    if ra is None:
        return None, None
    so, thong_tin, fd_hien = 0, {}, None
    for d in ra.splitlines():
        if d.startswith("f"):
            so += 1
            fd_hien = d[1:]
            thong_tin[fd_hien] = {"ten": None, "nghe": False}
        elif fd_hien is not None and d.startswith("n"):
            thong_tin[fd_hien]["ten"] = d[1:]
        elif fd_hien is not None and d.startswith("TST="):
            thong_tin[fd_hien]["nghe"] = d[4:].strip().upper().startswith("LISTEN")
    nghe = [t["ten"].rsplit(":", 1)[1] for t in thong_tin.values()
            if t["nghe"] and t["ten"] and ":" in t["ten"]]
    return so, nghe


def suc_khoe(goc_url, het=1.5):
    """Máy chủ còn TRẢ LỜI không: nối TCP + gửi `GET /`. Trả dict (ok · ms · mã HTTP).

    Đây là phép đo ĐẶT CẠNH `kill(pid, 0)`: một tiến trình còn sống nhưng đứng hình (không nhận
    kết nối nữa) vẫn "sống" với `kill`, nhưng KHÔNG trả lời được — và ca hỏng của lượt thật là
    `ERR_CONNECTION_REFUSED`, tức cái chết nằm ở tầng ổ cắm."""
    ra = {"ok": False, "ms": None, "ma_http": None}
    if "://" not in goc_url:
        return ra
    phan = goc_url.split("://", 1)[1]
    may, _, cong = phan.partition(":")
    cong = int(cong.split("/")[0] or 80)
    t0 = time.time()
    s = socket.socket()
    s.settimeout(het)
    try:
        s.connect((may, cong))
        s.sendall(b"GET / HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % may.encode())
        tra = s.recv(64)
        ra["ms"] = round((time.time() - t0) * 1000, 1)
        ra["ok"] = bool(tra)
        m = re.match(rb"HTTP/\d\.\d (\d{3})", tra or b"")
        if m:
            ra["ma_http"] = int(m.group(1))
    except OSError:
        ra["ms"] = round((time.time() - t0) * 1000, 1)
    finally:
        s.close()
    return ra


class BoDoGioiHan:
    """Lấy mẫu một tiến trình theo nhịp: mô tả tệp · ổ cắm · cổng nghe · con · sức khỏe cổng.

    Bộ đo KHÔNG phải cha của tiến trình được đo, nên nó không thể `wait()` để lấy mã thoát; nó
    phải nhận ra cái chết bằng hai dấu hiệu ĐỘC LẬP: `kill(pid, 0)` và "không còn mô tả tệp nào".
    Dấu hiệu thứ hai là thứ bắt được ZOMBIE — `kill(pid, 0)` vẫn thành công với một xác chết.
    """

    def __init__(self, pid, cong, nhip=NHIP_MAU, goc_url=None):
        self.pid = int(pid)
        self.cong = int(cong)
        self.nhip = float(nhip)
        self.goc_url = goc_url or ("http://127.0.0.1:%d" % self.cong)
        self.mau = []
        self._dung = threading.Event()
        self._th = None
        self.t_bat_dau = time.time()

    def lay_mau(self):
        t = time.time()
        fd = dem_fd(self.pid)
        song = tien_trinh_con_song(self.pid)
        if song and fd == 0:
            # Không còn mô tả tệp nào ⇒ đây là ZOMBIE (đã chết, chưa được `wait`), không phải sống.
            song = False
        so_tcp, nghe = o_cam_tcp(self.pid)
        con = dem_con(self.pid)
        sk = suc_khoe(self.goc_url)
        m = {"giay": round(t - self.t_bat_dau, 2), "t": t, "song": bool(song), "fd": fd,
             "tcp": so_tcp, "nghe": nghe or [], "con": con, "sk": sk["ok"], "ms": sk["ms"],
             "ma_http": sk["ma_http"]}
        self.mau.append(m)
        return m

    def chay(self):
        self._th = threading.Thread(target=self._vong, daemon=True)
        self._th.start()
        return self

    def _vong(self):
        while not self._dung.is_set():
            try:
                self.lay_mau()
            except Exception:                                                # noqa: BLE001
                pass
            self._dung.wait(self.nhip)

    def thoi(self):
        self._dung.set()
        if self._th is not None:
            self._th.join(timeout=10)

    def ket_qua(self):
        m = self.mau
        if not m:
            return {"so_mau": 0, "song_suot": None, "ly_do": "KHÔNG lấy được mẫu nào"}
        fd = [x["fd"] for x in m if x["fd"] is not None]
        tcp = [x["tcp"] for x in m if x["tcp"] is not None]
        con = [x["con"] for x in m if x.get("con") is not None]
        ms = [x["ms"] for x in m if x["ms"] is not None]
        giay_chet, chi_so, ly = phat_hien_chet(m)
        cuoi = m[-1]
        return {
            "so_mau": len(m),
            "nhip": self.nhip,
            "song_giay": m[-1]["giay"],
            "song_suot": giay_chet is None,
            "chet_o_giay": giay_chet,
            "ly_do_chet": ly,
            "mau_chet": m[chi_so] if chi_so is not None else None,
            "fd_min": min(fd) if fd else None,
            "fd_max": max(fd) if fd else None,
            "fd_cuoi": fd[-1] if fd else None,
            "tcp_max": max(tcp) if tcp else None,
            "cong_nghe": sorted({c for x in m for c in x["nghe"]}),
            "con_max": max(con) if con else None,
            "con_do_duoc": bool(con),
            "ms_trung_binh": round(sum(ms) / len(ms), 1) if ms else None,
            "ms_cao_nhat": max(ms) if ms else None,
            "tra_loi_cuoi_o_giay": next((x["giay"] for x in reversed(m) if x["sk"]), None),
            "ma_http_cuoi": cuoi.get("ma_http"),
        }


def phat_hien_chet(ds_mau):
    """HÀM THUẦN: (giây chết, chỉ số mẫu, lý do) từ một dãy mẫu. Không có mẫu chết ⇒ (None,None,…).

    Hai dấu hiệu độc lập, cố ý: tiến trình không còn sống, HOẶC cổng ngừng trả lời trong khi mẫu
    trước còn trả lời. Một bộ dò chỉ có một dấu hiệu sẽ bỏ sót đúng kiểu chết còn lại."""
    for i, m in enumerate(ds_mau):
        if not m.get("song"):
            return m.get("giay"), i, "tiến trình không còn sống (kill(pid,0) hoặc hết mô tả tệp)"
        if m.get("sk") is False and i > 0 and ds_mau[i - 1].get("sk"):
            return m.get("giay"), i, "cổng ngừng trả lời (mẫu trước còn trả lời)"
    return None, None, "còn sống tới hết lượt"


_MAU_NEN_RUNNER = re.compile(r"^\[giao-dien\] nền=(\S+) cổng=(\d+) pid=(\d+)", re.M)
_MAU_MA_THAT = re.compile(r"^\[giao-dien\] mã thoát THẬT (\d+)", re.M)
_MAU_PHAM_VI = re.compile(r"^\[giao-dien\] PHẠM VI", re.M)
_MAU_CHET_GIUA_LUOT = re.compile(r"^\[giao-dien\] CẢNH BÁO: máy chủ pid (\d+) ĐÃ CHẾT GIỮA LƯỢT", re.M)
_MAU_TIN_HIEU = re.compile(
    r"^\[giao-dien\] máy chủ pid (\d+) bị GIẾT BẰNG TÍN HIỆU: mã (\d+) = (\S+) — tín hiệu KHÔNG do bộ dọn gửi",
    re.M)


def doc_dong_runner(van_ban):
    """Đọc những dòng MÁY ĐỌC ĐƯỢC của `chay.sh`. Hàm thuần ⇒ tự kiểm được (ca `e2`).

    `pham_vi` = SỐ dòng `[giao-dien] PHẠM VI`. Đây là bất biến của bản vá việc 1: một lượt chạy
    mà `pham_vi == 0` là một lượt BÁO CÁO HỎNG, kể cả khi mọi ca đều đạt."""
    van_ban = van_ban or ""
    ra = {"pham_vi": len(_MAU_PHAM_VI.findall(van_ban)), "nen": None, "cong": None, "pid": None,
          "ma_that": None, "chet_giua_luot": False, "chet_pid": None, "ma_tin_hieu": None,
          "tin_hieu": None, "tu_don": False, "dong_giao_dien": 0}
    ra["co_pham_vi"] = ra["pham_vi"] > 0
    ra["dong_giao_dien"] = sum(1 for d in van_ban.splitlines() if d.startswith("[giao-dien]"))
    m = _MAU_NEN_RUNNER.search(van_ban)
    if m:
        ra["nen"], ra["cong"], ra["pid"] = m.group(1), int(m.group(2)), int(m.group(3))
    m = _MAU_MA_THAT.search(van_ban)
    if m:
        ra["ma_that"] = int(m.group(1))
    m = _MAU_CHET_GIUA_LUOT.search(van_ban)
    if m:
        ra["chet_giua_luot"] = True
        ra["chet_pid"] = int(m.group(1))
    m = _MAU_TIN_HIEU.search(van_ban)
    if m:
        ra["chet_giua_luot"] = True
        ra["chet_pid"] = int(m.group(1))
        ra["ma_tin_hieu"] = int(m.group(2))
        ra["tin_hieu"] = m.group(3)
    ra["tu_don"] = ("tín hiệu do CHÍNH bộ dọn gửi" in van_ban) and ra["tin_hieu"] is None
    return ra


def _giet_tu_ngoai(pid, tin_hieu=signal.SIGKILL):
    """ĐỐI CHỨNG DƯƠNG: giết máy chủ từ MỘT TIẾN TRÌNH KHÁC (chính bộ đo), không phải từ runner."""
    try:
        os.kill(int(pid), tin_hieu)
        return True
    except OSError:
        return False


def _gioi_han_he_thong():
    """Trần tài nguyên của chính phiên đo: `ulimit -n` (máy chủ THỪA HƯỞNG) + trần của HĐH."""
    ra = {"ulimit_n": None, "ulimit_Hn": None, "launchctl_maxfiles": None}
    try:
        tt = subprocess.run(["sh", "-c", "ulimit -n; ulimit -Hn"], capture_output=True, text=True,
                            timeout=15)
        dong = tt.stdout.split()
        if len(dong) >= 1:
            ra["ulimit_n"] = dong[0]
        if len(dong) >= 2:
            ra["ulimit_Hn"] = dong[1]
    except (OSError, subprocess.SubprocessError):                            # noqa: BLE001
        pass
    try:
        tt = subprocess.run(["launchctl", "limit", "maxfiles"], capture_output=True, text=True,
                            timeout=15)
        ra["launchctl_maxfiles"] = tt.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):                            # noqa: BLE001
        pass
    return ra


def _in_bang_do(ds, giu=None):
    """Bảng mỗi lượt một dòng — thứ để người đọc so sánh lượt đạt với lượt hỏng bằng MẮT."""
    giu = giu if giu is not None else []
    _in(giu, "")
    _in(giu, "  ┌ LUỢT · mã thoát · ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY · PHẠM VI · máy chủ sống · fd trần · tcp trần · con trần · mã HTTP · phán quyết")
    for r in ds:
        tk = r.get("dem") or {}
        gh = r.get("gioi_han") or {}
        _in(giu, "  │ %-4s %-4s %s/%s/%s/%s  PHẠM VI %-2s  sống %-7s  fd≤%-4s  tcp≤%-4s  con≤%-3s  HTTP %-4s  %s"
            % (r["lan"], r["ma_runner"], tk.get("passed"), tk.get("failed"), tk.get("skipped"),
               tk.get("did_not_run"), (r.get("runner") or {}).get("pham_vi"),
               ("%.1fs" % gh["song_giay"]) if gh.get("song_giay") is not None else "?",
               gh.get("fd_max"), gh.get("tcp_max"), gh.get("con_max"), gh.get("ma_http_cuoi"),
               r["nhan"]))
        if r.get("giet_luc"):
            _in(giu, "  │      ↳ ĐỐI CHỨNG DƯƠNG: bộ đo giết máy chủ ở giây %s ⇒ bộ đo bắt được ở giây %s (%s)"
                % (r["giet_luc"], gh.get("chet_o_giay"), gh.get("ly_do_chet")))
    _in(giu, "  └")
    return giu


def chay_chay_sh(so_lan=1, giet_luc=None, giet_tin_hieu=signal.SIGKILL, thu_muc_log=None,
                 so_ca_ghim=SO_CA_GHIM, ghi_chu=None, het_luot=HET_LUOT_MAC_DINH,
                 tham_so_them=()):
    """Chạy THẬT `sh thu_giao_dien/chay.sh` N lượt, đo giới hạn tiến trình từng lượt.

    Trả (mã thoát tổng, danh sách kết quả từng lượt). Mã thoát tổng = 0 chỉ khi MỌI lượt là `DAT`
    và MỌI lượt đều in được dòng PHẠM VI.
    """
    giu = ghi_chu if ghi_chu is not None else []
    thu_muc_log = thu_muc_log or tempfile.mkdtemp(prefix="veh-ag06-do.")
    os.makedirs(thu_muc_log, exist_ok=True)     # lượt đo ĐẦU TIÊN đã đỏ vì thiếu dòng này
    ds = []
    _in(giu, "[đo] giới hạn của phiên: %s" % json.dumps(_gioi_han_he_thong(), ensure_ascii=False))
    for lan in range(1, so_lan + 1):
        tep = os.path.join(thu_muc_log, "luot-%02d.log" % lan)
        _in(giu, "[đo] ── lượt %d/%d → %s" % (lan, so_lan, tep))
        tt = subprocess.Popen(["sh", os.path.join("thu_giao_dien", "chay.sh")] + list(tham_so_them),
                              cwd=GOC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, bufsize=1)
        bo_do, hen_giet, dong, t0 = None, None, [], time.time()
        bao_het = threading.Timer(het_luot, lambda: tt.kill())
        bao_het.daemon = True
        bao_het.start()
        try:
            with open(tep, "w", encoding="utf-8") as f:
                for d in tt.stdout:
                    f.write(d)
                    f.flush()
                    dong.append(d)
                    if bo_do is None:
                        m = _MAU_NEN_RUNNER.search(d)
                        if m:
                            pid, cong = int(m.group(3)), int(m.group(2))
                            bo_do = BoDoGioiHan(pid, cong).chay()
                            _in(giu, "[đo]    máy chủ pid %d · cổng %d → bắt đầu lấy mẫu mỗi %.2fs"
                                % (pid, cong, NHIP_MAU))
                            if giet_luc:
                                hen_giet = threading.Timer(giet_luc, _giet_tu_ngoai,
                                                           args=(pid, giet_tin_hieu))
                                hen_giet.daemon = True
                                hen_giet.start()
        finally:
            ma_runner = tt.wait()
            bao_het.cancel()
            if hen_giet is not None:
                hen_giet.cancel()
        giay_chay = round(time.time() - t0, 1)
        gh = {}
        if bo_do is not None:
            bo_do.thoi()
            gh = bo_do.ket_qua()
            if gh.get("con_max") is None:
                gh["con_max"] = dem_con(bo_do.pid)      # một lần, sau khi lượt kết thúc
        van_ban = "".join(dong)
        rd = doc_dong_runner(van_ban)
        tk = doc_tong_ket(van_ban)
        dau_hieu = dau_hieu_nen_chet(van_ban)
        may_chu_chet = bool(rd["chet_giua_luot"]) or (gh.get("song_suot") is False)
        ma_pq, nhan, ly = phan_quyet(tk, not may_chu_chet, ma_runner, so_ca_ghim, dau_hieu)
        if rd["pham_vi"] == 0:
            ma_pq = MA_HONG
            nhan = "HONG"
            ly = ("BÁO CÁO HỎNG: lượt chạy KHÔNG in dòng PHẠM VI nào (bất biến của bản vá việc 1). "
                  "Một lượt không nói được phạm vi của nó thì không được tính là đạt. (%s)" % ly)
        ds.append({"lan": lan, "gio": time.strftime("%H:%M:%S"), "ma_runner": ma_runner,
                   "giay_chay": giay_chay, "log": tep, "dem": tk, "runner": rd,
                   "gioi_han": gh, "giet_luc": giet_luc,
                   "may_chu_chet": may_chu_chet, "ma": ma_pq, "nhan": nhan, "ly_do": ly,
                   "dau_hieu_nen_chet": dau_hieu})
        _in(giu, "[đo]    exit=%s · %.1fs · %s ⇒ %s" % (ma_runner, giay_chay, nhan, ly[:140]))
    ma_tong = MA_DAT if all(r["ma"] == MA_DAT for r in ds) else (
        MA_HA_TANG if any(r["ma"] == MA_HA_TANG for r in ds) else MA_HONG)
    _in_bang_do(ds, giu)
    return ma_tong, ds


def do_tro_ngo(giay=180.0, nhip=1.0, thu_muc=None, ghi_chu=None):
    """BỐN tiến trình nền KHÁC NHAU, sống cùng `giay` giây, đo CÁI NÀO CHẾT và CHẾT VÌ GÌ.

    Mục đích: tách *"sản phẩm bị giết"* khỏi *"tiến trình nền dài hơi trong phiên này bị giết"*.
    Tiến trình KHÔNG liên quan gì tới sản phẩm mà cũng chết ⇒ cái chết không phải thuộc tính của
    sản phẩm. Đó là một PHÉP ĐO, không phải một lời biện hộ.

      P1 `sleep` trần                  — không tên giống, không cổng
      P2 ngủ, tên đường dẫn có `app/server.py` — GIỐNG TÊN, không cổng
      P3 ngủ, NGHE một cổng 18xxx      — không giống tên, CÓ CỔNG
      P4 chính `app/server.py` của repo, KHÔNG tải — giống tên + có cổng + là SẢN PHẨM
    """
    giu = ghi_chu if ghi_chu is not None else []
    thu_muc = thu_muc or tempfile.mkdtemp(prefix="veh-ag06-tro-ngo.")
    ds = []
    tt_ds = []
    cong_p3 = tim_cong_rong(dai=DAI_CONG)
    # P2 — bản sao tên: `app/server.py` nằm trong ĐƯỜNG DẪN, nhưng KHÔNG phải mã sản phẩm.
    os.makedirs(os.path.join(thu_muc, "gia-2", "app"), exist_ok=True)
    with open(os.path.join(thu_muc, "gia-2", "app", "server.py"), "w", encoding="utf-8") as f:
        f.write("import time\n# tiến trình GIẢ: chỉ ngủ. Không phải mã sản phẩm.\ntime.sleep(3600)\n")
    # P3 — bản sao cổng: tên khác hẳn, nhưng NGHE đúng dải cổng mà `chay.sh` dùng.
    with open(os.path.join(thu_muc, "gia-3.py"), "w", encoding="utf-8") as f:
        f.write("import socket, time\n"
                "s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
                "s.bind(('127.0.0.1', %d)); s.listen(8)\n"
                "while True: time.sleep(1)\n" % cong_p3)
    _in(giu, "[trò-ngo] sống %ss · cổng P3=%s · thư mục=%s" % (giay, cong_p3, thu_muc))
    try:
        tt_ds.append(("P1 sleep trần", subprocess.Popen(["sleep", str(int(giay) + 60)])))
        tt_ds.append(("P2 tên giống app/server.py",
                      subprocess.Popen(["python3", os.path.join(thu_muc, "gia-2", "app", "server.py")])))
        tt_ds.append(("P3 nghe cổng %d" % cong_p3,
                      subprocess.Popen(["python3", os.path.join(thu_muc, "gia-3.py")])))
        # P4 — máy chủ THẬT: nền cô lập đầy đủ, y như `chay_cong` dựng, nhưng KHÔNG có tải nào.
        nen = tempfile.mkdtemp(prefix="veh-ag06-tro-ngo-nen.")
        env, _ = moi_truong_git_sach()
        env["VIP_HUB_DATA"] = nen
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        dung_duoc = True
        for lenh in (["python3", "app/migrate.py"], ["python3", "app/khoi_tao.py"],
                     ["python3", "thu_giao_dien/chuan_bi.py", "mk"]):
            tt = subprocess.run(lenh, cwd=GOC, env=env, capture_output=True, text=True, timeout=300)
            if tt.returncode != 0:
                _in(giu, "[trò-ngo] P4 KHÔNG dựng được (%s thoát %s)" % (lenh[1], tt.returncode))
                dung_duoc = False
                break
        if dung_duoc:
            cong_p4 = tim_cong_rong(dai=DAI_CONG)
            log4 = open(os.path.join(thu_muc, "P4-may-chu.log"), "w", encoding="utf-8")
            tt_ds.append(("P4 app/server.py THẬT (không tải)",
                          subprocess.Popen(["python3", "app/server.py", str(cong_p4)], cwd=GOC,
                                           env=env, stdout=log4, stderr=subprocess.STDOUT)))
        t0 = time.time()
        while time.time() - t0 < giay:
            time.sleep(nhip)
        # Chốt trạng thái NGAY khi hết cửa sổ, TRƯỚC khi bộ đo tự tắt phần còn sống — nếu không,
        # mọi tiến trình sống sót đều mang mã -15 do CHÍNH bộ đo gửi và không phân biệt được nữa.
        song_cuoi = [(nhan, tt, tt.poll() is None) for nhan, tt in tt_ds]
    finally:
        for nhan, tt in tt_ds:
            if tt.poll() is None:
                tt.terminate()
        for nhan, tt in tt_ds:
            try:
                tt.wait(timeout=10)
            except subprocess.SubprocessError:                               # noqa: BLE001
                tt.kill()
    if not tt_ds:
        return ds
    if "song_cuoi" not in locals():
        song_cuoi = [(nhan, tt, False) for nhan, tt in tt_ds]
    for nhan, tt, con_song_cuoi in song_cuoi:
        ma = tt.returncode
        # Tiến trình này là CON của bộ đo ⇒ mã thoát ÂM = số tín hiệu đã giết nó.
        tin_hieu = signal.Signals(-ma).name if (ma is not None and ma < 0) else None
        chet_giua = (not con_song_cuoi) and tin_hieu is not None
        if chet_giua:
            ket_luan = "BỊ GIẾT BẰNG TÍN HIỆU %s giữa cửa sổ ⇒ không phải sản phẩm làm" % tin_hieu
        elif con_song_cuoi:
            ket_luan = "còn sống suốt %ss (bộ đo tự tắt)" % int(giay)
        else:
            ket_luan = "tự thoát với mã %s (KHÔNG do tín hiệu)" % ma
        ds.append({"nhan": nhan, "pid": tt.pid, "ma_thoát": ma, "tin_hieu": tin_hieu,
                   "song_cuoi_cua_so": con_song_cuoi, "chet_giua_luot": chet_giua,
                   "ket_luan": ket_luan})
        _in(giu, "[trò-ngo] %-34s pid %-7s mã %-6s %s" % (nhan, tt.pid, ma, ket_luan))
    return ds


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
    ap.add_argument("--do-chay-sh", type=int, default=0, metavar="N",
                    help="CHẠY LẠI TRỌN BỘ N lượt qua chính `thu_giao_dien/chay.sh` và ĐO giới hạn "
                         "tiến trình từng lượt (việc 2 + việc 3)")
    ap.add_argument("--giet-luc", type=float, default=0.0, metavar="GIAY",
                    help="ĐỐI CHỨNG DƯƠNG: giết máy chủ TỪ NGOÀI sau GIAY giây (đi với --do-chay-sh)")
    ap.add_argument("--giet-tin-hieu", default="KILL", choices=["KILL", "TERM"],
                    help="tín hiệu cho --giet-luc (mặc định KILL)")
    ap.add_argument("--thu-muc-log", default=None, help="chỗ ghi log từng lượt của --do-chay-sh")
    ap.add_argument("--tham-so", default="",
                    help="tham số thêm truyền cho `chay.sh` (ví dụ '--reporter=list'). Bỏ trống ⇒ "
                         "chạy ĐÚNG như người dùng gõ `sh thu_giao_dien/chay.sh`")
    ap.add_argument("--tro-ngo", type=float, default=0.0, metavar="GIAY",
                    help="đo sự sống của BỐN loại tiến trình nền khác nhau trong GIAY giây "
                         "(tách 'sản phẩm bị giết' khỏi 'mọi tiến trình nền đều bị giết')")
    ap.add_argument("--json-tong", default=None, help="ghi JSON tổng của --do-chay-sh/--tro-ngo")
    a = ap.parse_args(argv)

    if a.tro_ngo > 0:
        giu = []
        ds = do_tro_ngo(giay=a.tro_ngo, ghi_chu=giu)
        if a.json_tong:
            with open(a.json_tong, "w", encoding="utf-8") as f:
                json.dump({"tro_ngo": ds, "gio": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, f,
                          ensure_ascii=False, indent=2)
        return MA_DAT

    if a.do_chay_sh > 0:
        giu = []
        tin_hieu = signal.SIGKILL if a.giet_tin_hieu == "KILL" else signal.SIGTERM
        ma, ds = chay_chay_sh(so_lan=a.do_chay_sh, giet_luc=(a.giet_luc or None),
                              giet_tin_hieu=tin_hieu, thu_muc_log=a.thu_muc_log,
                              so_ca_ghim=a.so_ca, ghi_chu=giu,
                              tham_so_them=tuple(a.tham_so.split()))
        if a.json_tong:
            with open(a.json_tong, "w", encoding="utf-8") as f:
                json.dump({"gioi_han_he_thong": _gioi_han_he_thong(), "luot": ds,
                           "gio": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, f,
                          ensure_ascii=False, indent=2)
        _in(giu, "[đo] MÃ THOÁT TỔNG = %s" % ma)
        return ma

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
