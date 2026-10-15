#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18 — HARNESS TẢI HTTP THẬT (làn AG-04, vá lỗ hổng V-13914(b)).

LỖ HỔNG MÀ TỆP NÀY ĐƯỢC VIẾT RA ĐỂ ĐÓNG
----------------------------------------
`docs/BAN_GIAO.md` §6.1 ghi: *"máy chủ HTTP thật **dưới tải**"* — CHƯA AI ĐO, vì mọi bàn đo
trước đây gọi **thẳng hàm nghiệp vụ**, không đi qua `ThreadingHTTPServer`. Hệ quả: mọi con số về
đồng thời, về hạn chế tốc độ, về khoá đều đo trên **MỘT ĐƯỜNG KHÁC** với đường chạy thật.

Tệp này đo ĐÚNG đường chạy thật: dựng `app/server.py` (chính mã đang chạy), bind `127.0.0.1`
**cổng 0**, rồi bắn tải vào cửa GHI (webhook nhận sự kiện) và một cửa ĐỌC qua HTTP thật.

BA CÂU HỎI, VÀ CÁCH ĐO TỪNG CÂU
-------------------------------
1. **Bao nhiêu yêu cầu/giây, bao nhiêu lỗi, bao nhiêu 5xx?** — bộ đo đóng vòng (closed-loop)
   ở `BoTai`, mỗi luồng một kết nối HTTP, ghi lại mã trạng thái + số mili-giây TỪNG lượt.
2. **Hạn chế tốc độ (`app/gioi_han.py`) còn đúng khi đi qua HTTP thật không?** — đếm số lượt
   ĐƯỢC QUA trước lượt 429 đầu tiên, rồi **so với cùng phép đếm khi gọi thẳng hàm**. Hai đường
   phải cho cùng một trần; lệch nghĩa là đường HTTP có chỗ cộng/không cộng lượt mà đường hàm
   không có (hoặc ngược lại).
3. **Nhiều TIẾN TRÌNH máy chủ thì trần thực có NHÂN theo số bản không (B-G11-10)?** — dựng hai
   tiến trình `server.py` trên CÙNG một CSDL tạm, bắn xen kẽ, đếm tổng số lượt được qua.

ĐỐI CHỨNG ÂM
------------
Cùng kịch bản chạy với **một luồng** phải cho kết quả ĐÚNG và **không lỗi**. Không có nó thì
"20 lượt được qua ở hai tiến trình" có thể chỉ là hệ quả của một bộ đo hỏng, chứ không phải của
trần nhân theo số bản.

VÀ BỘ ĐO CŨNG PHẢI ĐƯỢC ĐO
---------------------------
`--tu-kiem` bắn bộ đo vào một **máy chủ giả cố tình hỏng** (bind `127.0.0.1` cổng 0, trả 500
theo chu kỳ, và cắt kết nối theo chu kỳ) rồi đòi bộ đo phải BÁO RA lỗi và 5xx. Cùng lúc nó bắn
vào một máy chủ giả LÀNH và đòi bộ đo phải báo **0 lỗi** — nếu không có ca lành, một bộ đo luôn
báo "có lỗi" cũng "bắt được" ca hỏng. Bộ phán quyết trần cũng được tự kiểm bằng ba chuỗi mã
trạng thái tổng hợp (đúng · thiếu 429 · 429 rồi lại cho qua).

CHẠY
----
    sh trien_khai/g18/chay_harness.sh
    python3 trien_khai/g18/harness_tai.py --tu-kiem      # chỉ tự kiểm, không dựng nền
"""
import argparse
import hashlib
import hmac
import http.client
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import threading
import time

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
GOC_G18 = os.path.dirname(os.path.abspath(__file__))
for _d in (GOC_G18, GOC_APP):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import chot_an_toan                                                        # noqa: E402

DAT, DAT_MOCK, HONG, BLOCKED, BO_QUA = "DAT", "DAT_MOCK", "HONG", "BLOCKED", "BO_QUA"
KY_HIEU = {DAT: "✓", DAT_MOCK: "✓", HONG: "✗", BLOCKED: "⊘", BO_QUA: "–"}
NHAN = {DAT: "ĐẠT", DAT_MOCK: "ĐẠT (MOCK)", HONG: "HỎNG", BLOCKED: "BLOCKED", BO_QUA: "BỎ QUA"}

# Giấy phép còn thiếu cho mọi chặng CHẠM HÃNG. Không phải chuỗi trang trí: chốt G17-7 đọc nó để
# từ chối chạy nếu có ai khai là đã cấp.
THIEU_GOI_HANG = ("V-G09-01 (gọi API hãng, kể cả sandbox)", "V-13906-05 (credentials sandbox J&T)")

HET_GIO_HTTP = 30.0        # giây, mỗi lượt HTTP
HET_GIO_CHO_SV = 20.0      # giây, chờ dòng log in ra cổng THẬT


def buoc_can_giay_phep():
    """Chặng nào CHẠM HÃNG thì phải khai mã giấy phép nó cần. Chốt G18-1..7 đọc hàm này.

    G18 KHÔNG có chặng chạm hãng nào chạy được: mọi phép đo đi qua stub/`mock`. Nhưng hàm này
    vẫn phải trả ĐÚNG một chặng `BLOCKED`, vì chốt 7 từ chối một danh sách RỖNG (danh sách rỗng
    nghĩa là chốt không canh gì). Đây là chỗ dễ làm sai nhất: xoá chặng này cho gọn là tắt luôn
    chốt 7, và không có gì báo.
    """
    return {"G18-CHAM-HANG": ("V-G09-01", "V-13906-05")}


BUOC = []


def ket(ma, ten, trang_thai, bang_chung=""):
    """Ghi một chặng. `bang_chung` là SỐ ĐO, không phải lời khai."""
    BUOC.append({"ma": ma, "ten": ten, "trang_thai": trang_thai, "bang_chung": bang_chung})
    print("  %s [%s] %s" % (KY_HIEU[trang_thai], ma, ten))
    if bang_chung:
        print("        %s" % bang_chung)
    return trang_thai


def la_dat(trang_thai):
    """`BLOCKED` và `BỎ QUA` KHÔNG phải đạt. Một dòng, để không chỗ nào tự định nghĩa lại."""
    return trang_thai in (DAT, DAT_MOCK)


def dem_phuong_an(ds):
    """Đếm theo phán quyết. `BLOCKED` có ô RIÊNG — không bao giờ cộng vào ô đạt."""
    dem = {DAT: 0, DAT_MOCK: 0, HONG: 0, BLOCKED: 0, BO_QUA: 0}
    for x in ds:
        dem[x["trang_thai"]] = dem.get(x["trang_thai"], 0) + 1
    return dem


# =======================================================================================
# BỘ ĐO TẢI — đóng vòng, mỗi luồng một kết nối HTTP
# =======================================================================================
class KhachTai(object):
    """Khách HTTP của bộ đo. Một kết nối cho MỖI luồng, dùng lại qua các lượt.

    Vì sao không `urllib.request.urlopen` mỗi lượt: `urlopen` dựng một `OpenerDirector` mới mỗi
    lần — đo được là nó chiếm phần lớn thời gian ở mức tải này, tức là bộ đo đang đo chính nó.
    `http.client.HTTPConnection` giữ kết nối và tự nối lại khi máy chủ đóng (máy chủ ở đây là
    HTTP/1.0 nên nó đóng sau mỗi phản hồi — `http.client` xử lý đúng chuyện đó).
    """

    def __init__(self, host, cong):
        self.host, self.cong = host, cong
        self.conn = None

    def _noi(self):
        if self.conn is None:
            self.conn = http.client.HTTPConnection(self.host, self.cong, timeout=HET_GIO_HTTP)
        return self.conn

    def dong(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:                                          # noqa: BLE001
                pass
            self.conn = None

    def goi(self, method, duong, than=None, header=None):
        """Trả `(ma_http, header_dict, than_bytes)`. Ném ra ngoài mọi lỗi tầng kết nối."""
        h = {"Connection": "close"}
        h.update(header or {})
        c = self._noi()
        try:
            c.request(method, duong, body=than, headers=h)
            ph = c.getresponse()
            du_lieu = ph.read()
            return ph.status, {k.lower(): v for k, v in ph.getheaders()}, du_lieu
        except Exception:
            self.dong()
            raise

    def json(self, method, duong, obj=None, header=None):
        than = None if obj is None else json.dumps(obj, ensure_ascii=False).encode()
        h = dict(header or {})
        if than is not None:
            h["Content-Type"] = "application/json"
        ma, _, du_lieu = self.goi(method, duong, than, h)
        try:
            return ma, json.loads(du_lieu or b"{}")
        except ValueError:
            return ma, {"_tho": du_lieu[:200].decode("utf-8", "replace")}


class BoTai(object):
    """Bộ sinh tải ĐÓNG VÒNG: `n` luồng, mỗi luồng gọi liên tiếp tới khi hết hạn hoặc hết lượt.

    Vì sao đóng vòng (mỗi luồng chờ phản hồi rồi mới gọi lượt kế): đây là dạng tải của một client
    thật, và nó cho số "yêu cầu/giây" có nghĩa — mở vòng (bắn không chờ) đo được sức chịu của
    hàng đợi TCP chứ không đo được máy chủ.
    """

    def __init__(self, host, cong, so_luong=8, ds_dich=None):
        # `ds_dich` = danh sách [(host, cổng), ...] để chia tải trên NHIỀU tiến trình máy chủ,
        # xoay vòng theo luồng. Cần nó cho phép đo "cùng 8 luồng, chia trên 2 tiến trình": phía
        # client y hệt nhau, chỉ phía máy chủ đổi — nhờ vậy mới tách được "nghẽn ở trong MỘT
        # tiến trình" khỏi "nghẽn ở phía client".
        self.ds_dich = ds_dich or [(host, cong)]
        self.host, self.cong, self.so_luong = host, cong, so_luong
        self.mau = []
        self._khoa = threading.Lock()
        self._dem = 0

    def _mot_luot(self, khach, dung_bai):
        t0 = time.perf_counter()
        try:
            ma, hdr, than = khach.goi(*dung_bai)
            ra = {"ma_http": ma, "loi": None, "rong": len(than),
                  "hdr": {k: hdr.get(k) for k in ("x-ratelimit-limit", "x-ratelimit-remaining",
                                                  "retry-after", "x-request-id")}}
        except socket.timeout:
            ra = {"ma_http": 0, "loi": "het_gio", "rong": 0, "hdr": {}}
        except Exception as e:                                          # noqa: BLE001
            ra = {"ma_http": 0, "loi": type(e).__name__, "rong": 0, "hdr": {}}
        ra["ms"] = (time.perf_counter() - t0) * 1000.0
        return ra

    def _luong(self, dung_bai, han, toi_da, chi_so=0):
        khach = KhachTai(*self.ds_dich[chi_so % len(self.ds_dich)])
        try:
            while True:
                if han is not None and time.monotonic() >= han:
                    return
                if toi_da is not None:
                    with self._khoa:
                        if self._dem >= toi_da:
                            return
                        self._dem += 1
                mau = self._mot_luot(khach, dung_bai)
                with self._khoa:
                    self.mau.append(mau)
        finally:
            khach.dong()

    def chay(self, dung_bai, giay=None, toi_da=None):
        """`dung_bai` = (method, duong, than, header). Trả dict số đo."""
        han = None if giay is None else time.monotonic() + giay
        t0 = time.perf_counter()
        ds = [threading.Thread(target=self._luong, args=(dung_bai, han, toi_da, i), daemon=True,
                               name="g18-tai-%d" % i) for i in range(self.so_luong)]
        for t in ds:
            t.start()
        for t in ds:
            t.join()
        return thong_ke(self.mau, time.perf_counter() - t0)


def thong_ke(ds_mau, giay):
    """Số đo của một lượt tải. Mọi khoá ở đây là SỐ ĐO, không phải suy đoán."""
    tong = len(ds_mau)
    theo_ma = {}
    for m in ds_mau:
        k = str(m["ma_http"])
        theo_ma[k] = theo_ma.get(k, 0) + 1
    loi_ket_noi = sum(1 for m in ds_mau if m["ma_http"] == 0)
    so_5xx = sum(1 for m in ds_mau if 500 <= m["ma_http"] < 600)
    ms = sorted(m["ms"] for m in ds_mau)

    def pct(p):
        if not ms:
            return 0.0
        i = min(len(ms) - 1, int(round((len(ms) - 1) * p)))
        return round(ms[i], 2)

    return {
        "tong": tong, "giay": round(giay, 3),
        "req_giay": round(tong / giay, 1) if giay > 0 else 0.0,
        "theo_ma": dict(sorted(theo_ma.items())),
        "loi_ket_noi": loi_ket_noi, "so_5xx": so_5xx,
        "ty_le_loi": round(loi_ket_noi / tong, 4) if tong else 0.0,
        "ty_le_5xx": round(so_5xx / tong, 4) if tong else 0.0,
        "ms_tb": round(sum(ms) / len(ms), 2) if ms else 0.0,
        "ms_p50": pct(0.50), "ms_p95": pct(0.95), "ms_p99": pct(0.99),
        "ms_max": round(ms[-1], 2) if ms else 0.0,
        "ds_loi": sorted({m["loi"] for m in ds_mau if m["loi"]}),
    }


def do_lanh(sd):
    """Tiêu chí "máy chủ LÀNH" của một lượt đo: CÓ lượt thật · 0 lỗi kết nối · 0 5xx.

    Tách ra thành hàm CÓ TÊN (không phải lambda nằm trong `tu_kiem_bo_do`) vì hai lý do:
      1. `app/thu/thu_g18_maysrv.py` phải tự kiểm được CHÍNH tiêu chí này — nạp lại một bản
         lambda ở tệp khác là kiểm một tiêu chí khác rồi tưởng đã kiểm tiêu chí này;
      2. điều kiện `tong > 0` là phần dễ bị bỏ sót nhất: một lượt chạy KHÔNG có yêu cầu nào cũng
         thỏa `loi_ket_noi == 0` và `so_5xx == 0`, nên nếu thiếu nó thì bộ đo báo "lành" trong khi
         nó chưa chạy gì. Đây là chỗ sinh ra bảng tổng kết xanh giả.
    """
    return bool(sd.get("tong", 0) > 0 and sd.get("loi_ket_noi", 0) == 0
                and sd.get("so_5xx", 0) == 0)


def tom_tat_so_do(sd):
    """Một dòng người đọc được từ dict số đo — để bảng tổng kết không phải mở JSON."""
    return ("%d lượt / %.2fs = %s yêu cầu/giây · mã=%s · lỗi kết nối=%d (%.2f%%) · 5xx=%d (%.2f%%)"
            " · ms tb=%s p95=%s max=%s"
            % (sd["tong"], sd["giay"], sd["req_giay"], sd["theo_ma"], sd["loi_ket_noi"],
               100 * sd["ty_le_loi"], sd["so_5xx"], 100 * sd["ty_le_5xx"], sd["ms_tb"],
               sd["ms_p95"], sd["ms_max"]))


def cpu_giay(pid):
    """CPU time TÍCH LUỸ của một tiến trình (giây, user+sys). `None` nếu không đọc được.

    GIỮ LẠI DÙ LƯỢT NÀY KHÔNG ĐO ĐƯỢC: trên máy này `ps` bị sandbox chặn
    (`/bin/ps: Operation not permitted`), nên hàm trả `None` và người gọi phải NÓI RA là không
    đo được (xem `G18-02c`). Giữ lại vì nó là phép đo ĐÚNG cho câu hỏi "nghẽn CPU hay nghẽn I/O",
    và vì xoá nó đi thì lượt sau sẽ lại đi tìm cách trả lời câu ấy bằng suy đoán.

    Vì sao câu hỏi ấy quan trọng: *"vì sao 8 luồng chỉ nhanh hơn 1 luồng 1,2 lần"* có hai câu
    trả lời rất khác nhau — **nghẽn CPU** (một lõi đã no; GIL của Python 3.9 không cho mã Python
    chạy song song) hay **nghẽn I/O** (khoá, đĩa). Đoán sai thì hướng vá sai: nghẽn CPU mà đi
    thêm luồng là đi lùi, còn nghẽn CPU mà đi thêm TIẾN TRÌNH thì đúng.
    """
    try:
        p = subprocess.run(["ps", "-o", "time=", "-p", str(pid)],
                           capture_output=True, text=True, timeout=10)
    except Exception:                                                  # noqa: BLE001
        return None
    tho = (p.stdout or "").strip()
    if not tho:
        return None
    try:
        so = [float(x) for x in tho.split(":")]
    except ValueError:
        return None
    if len(so) == 3:
        return so[0] * 3600 + so[1] * 60 + so[2]
    if len(so) == 2:
        return so[0] * 60 + so[1]
    return so[0] if so else None


# =======================================================================================
# BỘ PHÁN QUYẾT TRẦN TẦN SUẤT — và tự kiểm nó
# =======================================================================================
def phan_quyet_tran(ds_ma, tran_mong_doi, ma_chan=429, ma_cho_qua=401):
    """Phán quyết một chuỗi mã trạng thái HTTP có đúng luật trần không.

    Luật: `tran_mong_doi` lượt ĐẦU phải được qua (`ma_cho_qua`), lượt kế tiếp phải bị chặn
    (`ma_chan`), và **đã chặn thì phải chặn LIÊN TỤC** — trần mà cho qua lại sau một lượt chặn là
    trần hỏng: nó chỉ làm chậm kẻ dò chứ không chặn.

    Trả `(dat, ly_do)`.
    """
    if not ds_ma:
        return False, "không có lượt nào để phán"
    qua = [i for i, m in enumerate(ds_ma) if m == ma_cho_qua]
    chan = [i for i, m in enumerate(ds_ma) if m == ma_chan]
    if len(qua) != tran_mong_doi:
        return False, ("đếm được %d lượt qua (%s), mong đợi ĐÚNG %d — trần thực %s khai báo"
                       % (len(qua), ma_cho_qua, tran_mong_doi, "KHÁC" if len(qua) > tran_mong_doi
                          else "thấp hơn"))
    if not chan:
        return False, ("%d lượt qua rồi KHÔNG có lượt %d nào — trần không chặn gì"
                       % (len(qua), ma_chan))
    if chan[0] != tran_mong_doi:
        return False, ("lượt %d bị chặn ở vị trí %d, mong đợi đúng vị trí %d"
                       % (ma_chan, chan[0], tran_mong_doi))
    if len(chan) != len(ds_ma) - tran_mong_doi:
        lai = [ds_ma[i] for i in range(chan[0] + 1, len(ds_ma)) if ds_ma[i] != ma_chan]
        return False, "sau lượt chặn đầu tiên vẫn có lượt KHÔNG bị chặn: %s" % lai[:5]
    return True, ("ĐÚNG: %d lượt %s rồi %d lượt %s liên tục"
                  % (len(qua), ma_cho_qua, len(chan), ma_chan))


def _ca_tu_kiem_tran():
    """Ba chuỗi tổng hợp cho bộ phán quyết. Ca 1 là ĐỐI CHỨNG DƯƠNG: thiếu nó thì một hàm
    `return False` cũng "bắt được" hai ca hỏng và trông như đang hoạt động."""
    return [
        ("T1", "chuỗi ĐÚNG: 10 qua rồi 3 chặn", [401] * 10 + [429] * 3, 10, True),
        ("T2", "trần KHÔNG chặn: 13 lượt qua hết", [401] * 13, 10, False),
        ("T3", "chặn rồi CHO QUA LẠI ở lượt 12", [401] * 10 + [429, 401, 429], 10, False),
        ("T4", "chặn SỚM hơn khai báo (vị trí 4)", [401] * 4 + [429] * 3, 10, False),
    ]


def tu_kiem_tran(cho_in=True):
    so_hong, ket_qua = 0, []
    for ma, mo_ta, chuoi, tran, mong_doi in _ca_tu_kiem_tran():
        dat, ly_do = phan_quyet_tran(chuoi, tran)
        dung = (dat == mong_doi)
        if not dung:
            so_hong += 1
        ket_qua.append({"ma": ma, "mo_ta": mo_ta, "mong_doi_dat": mong_doi, "thuc_te_dat": dat,
                        "ly_do": ly_do, "dat": dung})
        if cho_in:
            print("  %s [%s] %s" % ("✓" if dung else "✗", ma, mo_ta))
            print("        %s" % ly_do)
    return len(ket_qua), so_hong, ket_qua


# =======================================================================================
# MÁY CHỦ GIẢ cho việc TỰ KIỂM BỘ ĐO TẢI
# =======================================================================================
class MayChuGia(object):
    """Máy chủ HTTP cổng 0 trên loopback, phục vụ BA đường:

      `/lanh`      — luôn 200. ĐỐI CHỨNG DƯƠNG: bộ đo phải báo 0 lỗi, 0 5xx.
      `/nam-tram`  — cứ 3 lượt thì 1 lượt 500. Bộ đo PHẢI thấy 5xx.
      `/cat-day`   — cứ 5 lượt thì 1 lượt cắt kết nối không phản hồi. Bộ đo PHẢI thấy lỗi.

    Vì sao phải có cả `/lanh`: một bộ đo luôn báo "có lỗi" cũng "bắt được" ca hỏng. Không có
    đối chứng dương thì phép tự kiểm này không chứng minh được gì.
    """

    def __init__(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self._dem = {"n": 0}
        self._khoa = threading.Lock()
        may = self

        class H(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *a):
                pass

            def do_GET(self):
                with may._khoa:
                    may._dem["n"] += 1
                    n = may._dem["n"]
                if self.path == "/lanh":
                    return self._ok()
                if self.path == "/nam-tram":
                    if n % 3 == 0:
                        return self._ma(500, b'{"loi":"co y hong"}')
                    return self._ok()
                if self.path == "/cat-day":
                    if n % 5 == 0:
                        # Cắt kết nối KHÔNG gửi gì: đây là dạng hỏng mà một bộ đo chỉ đếm mã
                        # trạng thái sẽ bỏ qua hoàn toàn.
                        self.close_connection = True
                        try:
                            self.connection.close()
                        except Exception:                              # noqa: BLE001
                            pass
                        return
                    return self._ok()
                return self._ma(404, b'{"loi":"khong co"}')

            def _ok(self):
                return self._ma(200, b'{"ok":true}')

            def _ma(self, ma, than):
                self.send_response(ma)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(than)))
                self.end_headers()
                self.wfile.write(than)

        self.sv = ThreadingHTTPServer(("127.0.0.1", 0), H)      # CỔNG 0 — hệ điều hành cấp
        self.cong = self.sv.server_address[1]
        threading.Thread(target=self.sv.serve_forever, name="g18-gia", daemon=True).start()

    def dung(self):
        self.sv.shutdown()
        self.sv.server_close()


def tu_kiem_bo_do(cho_in=True):
    """Bắn bộ đo vào máy chủ giả. Trả `(so_ca, so_hong, ket_qua)`.

    Bốn ca. Ba ca đầu đòi bộ đo PHẢI đạt (`mong_doi_dat=True`): lành ⇒ 0 lỗi · 0 5xx; 500 theo
    chu kỳ ⇒ thấy 5xx; cắt kết nối ⇒ thấy lỗi. Ca thứ tư đòi bộ đo PHẢI **KHÔNG** đạt: một lượt
    chạy **0 yêu cầu** không được phép được coi là "lành" — bộ đo không chạy gì mà báo 0 lỗi là
    bộ đo nói dối theo hướng nguy hiểm nhất, và nó là chỗ một bảng tổng kết xanh giả sinh ra.

    Vì sao ca thứ tư cần `mong_doi_dat` RIÊNG chứ không nhét vào cùng khuôn "phải đạt": đo được
    ngay ở lượt chạy đầu — bản đầu viết `lambda sd: sd["tong"] == 0 and False`, một ca LUÔN SAI,
    nên nó bị tính là HỎNG và `--tu-kiem` thoát 1. Một bộ tự kiểm không diễn đạt được "ca này
    phải bị bác" thì nó buộc người viết phải viết ra một ca luôn-đúng hoặc luôn-sai — cả hai đều
    là ca rỗng, và cả hai đều làm bảng tổng kết mất nghĩa.
    """
    may = MayChuGia()
    so_hong, ket_qua = 0, []
    try:
        for ma, mo_ta, duong, toi_da, kiem, mong_doi_dat in (
                ("BD1", "máy chủ LÀNH ⇒ 0 lỗi, 0 5xx (đối chứng dương)", "/lanh", 60,
                 do_lanh, True),
                ("BD2", "500 theo chu kỳ ⇒ bộ đo PHẢI thấy 5xx", "/nam-tram", 60,
                 lambda sd: sd["so_5xx"] > 0, True),
                ("BD3", "cắt kết nối theo chu kỳ ⇒ bộ đo PHẢI thấy lỗi", "/cat-day", 60,
                 lambda sd: sd["loi_ket_noi"] > 0, True),
                ("BD4", "0 yêu cầu ⇒ KHÔNG được coi là 'lành' (đối chứng âm của BỘ ĐO)",
                 "/lanh", 0, do_lanh, False)):
            bt = BoTai("127.0.0.1", may.cong, so_luong=4)
            sd = bt.chay(("GET", duong, None, None), toi_da=toi_da)
            dat = bool(kiem(sd)) == mong_doi_dat
            if not dat:
                so_hong += 1
            ket_qua.append({"ma": ma, "mo_ta": mo_ta, "dat": dat, "mong_doi_dat": mong_doi_dat,
                            "so_do": sd})
            if cho_in:
                print("  %s [%s] %s" % ("✓" if dat else "✗", ma, mo_ta))
                print("        %s" % tom_tat_so_do(sd))
    finally:
        may.dung()
    return len(ket_qua), so_hong, ket_qua


# =======================================================================================
# DỰNG NỀN + MÁY CHỦ
# =======================================================================================
def _doc_duong_hub(log):
    """Đọc cổng THẬT từ dòng log `server.py` in ra (`bind cổng 0` ⇒ hệ điều hành cấp)."""
    with open(log, encoding="utf-8", errors="replace") as f:
        m = re.search(r"chạy tại http://([0-9.]+):(\d+)", f.read())
    return ("http://%s:%s" % (m.group(1), m.group(2)), int(m.group(2))) if m else (None, None)


class TienTrinhMayChu(object):
    """MỘT tiến trình `app/server.py` bind loopback cổng 0. Tắt theo ĐÚNG PID."""

    def __init__(self, nhan, nen, env, log):
        self.nhan, self.nen, self.env, self.log = nhan, nen, env, log
        self.p = None
        self.pid = None
        self.cong = None
        self.goc = None

    def bat_dau(self):
        with open(self.log, "w") as f:
            # `-u`: KHÔNG đệm stdout — thiếu nó thì dòng in cổng THẬT nằm trong bộ đệm và harness
            # ngồi đợi một dòng đã viết ra từ lâu (đo được ở lượt chạy đầu của G17: log rỗng,
            # chờ 20 giây, thoát 3).
            self.p = subprocess.Popen(
                [sys.executable, "-u", os.path.join(GOC_APP, "server.py"), "0"],
                stdout=f, stderr=subprocess.STDOUT, env=self.env, cwd=DU_AN)
        self.pid = self.p.pid
        han = time.monotonic() + HET_GIO_CHO_SV
        while time.monotonic() < han:
            self.goc, self.cong = _doc_duong_hub(self.log)
            if self.goc:
                return self
            if self.p.poll() is not None:
                raise RuntimeError("máy chủ %s chết khi khởi động:\n%s"
                                   % (self.nhan,
                                      open(self.log, encoding="utf-8", errors="replace").read()[-600:]))
            time.sleep(0.1)
        raise RuntimeError("không đọc được cổng THẬT của %s từ log %s" % (self.nhan, self.log))

    def dung(self):
        """Tắt theo ĐÚNG PID. KHÔNG `pkill`/`killall` — xem chốt G18-11."""
        if self.p is None:
            return
        if self.p.poll() is None:
            self.p.terminate()
            try:
                self.p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.p.kill()
                self.p.wait(timeout=10)


def _tai_pid(nen, ds_tt):
    """Ghi PID của MỌI tiến trình ra tệp để `trap` của bộ chạy shell hứng được."""
    with open(os.path.join(nen, "hub.pid"), "w") as f:
        f.write("\n".join(str(t.pid) for t in ds_tt if t.pid) + "\n")


def _khach_dang_nhap(cong, ten, mat_khau):
    """Đăng nhập qua HTTP, trả `(cookie, ma_http)`. Cookie là thứ duy nhất cần cho cửa ĐỌC."""
    k = KhachTai("127.0.0.1", cong)
    try:
        ma, hdr, than = k.goi("POST", "/api/v2/auth/dang-nhap",
                              json.dumps({"ten_dang_nhap": ten,
                                          "mat_khau": mat_khau}).encode(),
                              {"Content-Type": "application/json",
                               "X-Requested-With": "VIPHub"})
        ck = hdr.get("set-cookie") or ""
        return (ck.split(";")[0] if ck else ""), ma
    finally:
        k.dong()


def _khach_co_phien(cong, cookie):
    """Khách đã có phiên — dùng cho mọi lượt của cửa ĐỌC."""
    class K(KhachTai):
        def goi(self, method, duong, than=None, header=None):
            h = dict(header or {})
            h["Cookie"] = cookie
            h["X-Requested-With"] = "VIPHub"
            return KhachTai.goi(self, method, duong, than, h)
    return K("127.0.0.1", cong)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    ap.add_argument("--giu-nen", action="store_true")
    ap.add_argument("--so-tien-trinh", type=int, default=chot_an_toan.SO_TIEN_TRINH_MAC_DINH)
    ap.add_argument("--tu-kiem", action="store_true",
                    help="chỉ tự kiểm BỘ ĐO + BỘ PHÁN QUYẾT, không dựng nền, không mở máy chủ")
    a = ap.parse_args()

    # ------------------------------------------------------------------ TỰ KIỂM (không dựng gì)
    if a.tu_kiem:
        print("═" * 78)
        print("TỰ KIỂM CỦA HARNESS G18 — không dựng nền, không mở máy chủ thật")
        print("═" * 78)
        print("\n── A. BỘ ĐO TẢI, bắn vào máy chủ giả 127.0.0.1 cổng 0 ──────────")
        t1, h1, _ = tu_kiem_bo_do()
        print("\n── B. BỘ PHÁN QUYẾT TRẦN TẦN SUẤT, chuỗi mã trạng thái tổng hợp ─")
        t2, h2, _ = tu_kiem_tran()
        print("\n" + "─" * 78)
        print("TỰ KIỂM: %d/%d ca đạt · %d hỏng" % (t1 + t2 - h1 - h2, t1 + t2, h1 + h2))
        if h1 or h2:
            print("BỘ ĐO HỎNG: mọi con số ở lượt này KHÔNG có giá trị — một bộ đo không phân biệt")
            print("được máy chủ lành với máy chủ hỏng thì nó đang đo chính nó.")
            return 1
        print("Bộ đo ĐẠT: phân biệt được máy chủ lành (0 lỗi) với máy chủ hỏng (có 5xx · có lỗi")
        print("kết nối), và bộ phán quyết trần phân biệt được chuỗi đúng với ba dạng chuỗi sai.")
        return 0

    nen = os.environ.get("VIP_HUB_DATA") or ""
    print("═" * 78)
    print("G18 — HARNESS TẢI HTTP THẬT · nền %s" % (nen or "<chưa đặt>"))
    print("═" * 78)

    # ------------------------------------------------------------------ mười hai chốt an toàn
    ds_bind = ["127.0.0.1"] * max(0, a.so_tien_trinh)
    ly_do = chot_an_toan.ly_do_tu_choi(
        nen, goc_url="http://127.0.0.1:0", so_tien_trinh=a.so_tien_trinh, ds_bind=ds_bind,
        env=dict(os.environ, VIP_HUB_BIND="127.0.0.1"),
        buoc_can_giay_phep=buoc_can_giay_phep(),
        duong_csdl=os.path.join(nen, "hub.db"))
    if ly_do:
        print("\nTỪ CHỐI CHẠY — mất ít nhất một chốt an toàn:")
        for x in ly_do:
            print("  · [%s] %s" % (x["chot"], x["ly_do"]))
        print("\nHarness này spawn NHIỀU tiến trình máy chủ và bắn tải HTTP thật. Chạy nó khi mất")
        print("chốt là thứ nguy hiểm hơn không có harness. Không có cờ nào để bỏ qua.")
        return 4
    print("  ✓ mười hai chốt an toàn: ĐỦ — bảy chốt mượn của G17 (G17-1..7: nền tạm · bind"
          " loopback · CHO_PHEP_LIVE=False · cổng hãng đóng · không cờ gọi hãng · đích loopback ·"
          " giấy phép đúng) + năm chốt riêng của G18 (G18-8 số tiến trình · G18-9 bind TỪNG tiến"
          " trình · G18-10 không dính PostgreSQL · G18-11 không pkill/killall · G18-12 nền tách"
          " khỏi G17)")

    env = dict(os.environ, VIP_HUB_DATA=nen, VIP_HUB_BIND="127.0.0.1", VIP_HUB_BACKOFF="0.01")
    for bien in (chot_an_toan.CO_GOI_HANG, chot_an_toan.BIEN_GIAY_PHEP,
                 "VIP_G17_CHO_PHEP_GOI_HANG", "VIP_G17_GIAY_PHEP"):
        env.pop(bien, None)
    ds_tt = []
    try:
        # -------------------------------------------------------------- dựng nền tạm
        print("\n── DỰNG NỀN TẠM ──────────────────────────────────────────────")
        for lenh, nhan in (("migrate.py", "migrate"), ("khoi_tao.py", "seed")):
            p = subprocess.run([sys.executable, os.path.join(GOC_APP, lenh)],
                               capture_output=True, text=True, env=env, cwd=DU_AN)
            if p.returncode:
                print("  ✗ %s hỏng: %s" % (nhan, (p.stderr or p.stdout)[-500:]))
                return 3
            print("  ✓ %s" % nhan)
        db = os.path.join(nen, "hub.db")

        def sql(q, ts=()):
            c = sqlite3.connect(db, timeout=30)
            c.row_factory = sqlite3.Row
            try:
                return [dict(x) for x in c.execute(q, ts)]
            finally:
                c.close()

        # -------------------------------------------------------------- tiến trình #1
        t1 = TienTrinhMayChu("may-chu-1", nen, env, os.path.join(nen, "server-1.log")).bat_dau()
        ds_tt.append(t1)
        _tai_pid(nen, ds_tt)
        print("  ✓ máy chủ 1: %s (pid %d) — bind CỔNG 0, chỉ loopback" % (t1.goc, t1.pid))
        ket("G18-00", "mười hai chốt + máy chủ thật loopback cổng 0",
            DAT, "nền=%s · pid=%d · địa chỉ thật=%s · số tiến trình theo kế hoạch=%d"
                 % (nen, t1.pid, t1.goc, a.so_tien_trinh))

        # -------------------------------------------------------------- nền nghiệp vụ
        print("\n── G18-01. NỀN NGHIỆP VỤ QUA HTTP THẬT ───────────────────────")
        mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`",
                             open(os.path.join(nen, "TAI-KHOAN-DEMO.md"),
                                  encoding="utf-8").read()))
        ck_po, ma_dn = _khach_dang_nhap(t1.cong, "platform-owner", mk["platform-owner"])
        k_po = _khach_co_phien(t1.cong, ck_po)
        ma_t, kq_t = k_po.json("POST", "/api/v2/platform/tenants",
                               {"ten": "Cty G18 Tải", "owner_ten_dang_nhap": "g18-owner",
                                "owner_mat_khau": "g18-owner-123", "goi_id": "pro"})
        tid = (kq_t.get("id") or (kq_t.get("tenant") or {}).get("id")) if isinstance(kq_t, dict) else None
        ket("G18-01a", "đăng nhập + tạo tenant qua cửa platform",
            DAT if (ma_dn == 200 and ma_t == 201 and tid) else HONG,
            "HTTP đăng nhập=%s · HTTP tạo tenant=%s · tenant=%s" % (ma_dn, ma_t, tid))
        if not tid:
            return 1

        ck_kh, ma_kh = _khach_dang_nhap(t1.cong, "g18-owner", "g18-owner-123")
        k_kh = _khach_co_phien(t1.cong, ck_kh)
        ma_tk, kq_tk = k_kh.json("POST", "/api/v2/tai-khoan-hang",
                                 {"hang": "jt", "ten": "J&T G18 (mock)",
                                  "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
        tk_id = kq_tk.get("id") if isinstance(kq_tk, dict) else None
        hang = sql("SELECT id, hang, moi_truong, kich_hoat, webhook_ma, webhook_secret_ma_hoa"
                   " FROM carrier_accounts WHERE id=?", (tk_id,)) if tk_id else []
        ket("G18-01b", "tài khoản hãng J&T môi trường MOCK (không gọi hãng)",
            DAT_MOCK if (ma_tk == 201 and hang and hang[0]["moi_truong"] == "mock") else HONG,
            "HTTP=%s · id=%s · môi trường=%s · webhook_ma=%s"
            % (ma_tk, tk_id, hang[0]["moi_truong"] if hang else "—",
               hang[0]["webhook_ma"] if hang else "—"))
        if not hang:
            return 1
        wh_ma = hang[0]["webhook_ma"]

        os.environ["VIP_HUB_DATA"] = nen
        import bao_mat                                                     # noqa: E402
        secret = bao_mat.giai_ma_wh(hang[0]["webhook_secret_ma_hoa"], wh_ma)

        # -------------------------------------------------------------- G18-02 CỬA ĐỌC, tải
        print("\n── G18-02. CỬA ĐỌC DƯỚI TẢI (GET /api/v2/webhook/su-kien) ────")
        k_doc = _khach_co_phien(t1.cong, ck_kh)
        ma_d, kq_d = k_doc.json("GET", "/api/v2/webhook/su-kien")
        print("  · một lượt lẻ trước khi đo tải: HTTP %s · %s"
              % (ma_d, list(kq_d)[:4] if isinstance(kq_d, dict) else type(kq_d).__name__))
        if ma_d != 200:
            ket("G18-02", "cửa ĐỌC trả 200 khi chưa tải", HONG, "HTTP %s · %s" % (ma_d, kq_d))
            return 1
        bt = BoTai("127.0.0.1", t1.cong, so_luong=8)
        so_dong_truoc = sql("SELECT COUNT(*) c FROM wh_su_kien")[0]["c"]
        sd_doc = bt.chay(("GET", "/api/v2/webhook/su-kien", None,
                          {"Cookie": ck_kh, "X-Requested-With": "VIPHub"}), giay=3.0)
        cpu_8 = cpu_giay(t1.pid)
        ket("G18-02a", "cửa ĐỌC (có phiên) dưới tải 8 luồng trong 3 giây · bảng %d dòng"
            % so_dong_truoc,
            DAT if (sd_doc["so_5xx"] == 0 and sd_doc["loi_ket_noi"] == 0
                    and sd_doc["theo_ma"].get("200", 0) == sd_doc["tong"] and sd_doc["tong"] > 0)
            else HONG,
            "%s · CPU tích luỹ đọc được=%s"
            % (tom_tat_so_do(sd_doc), "có" if cpu_8 is not None else "KHÔNG (ps bị chặn)"))
        # Đo lại y hệt nhưng MỘT luồng. Đây là mốc để nói được "8 luồng nhanh hơn 1 luồng bao
        # nhiêu lần" — thiếu nó thì con số 8 luồng không có gì để so, và một bộ đo bị nghẽn ở
        # phía client cũng cho ra một con số trông rất bình thường.
        sd_doc_1 = BoTai("127.0.0.1", t1.cong, so_luong=1).chay(
            ("GET", "/api/v2/webhook/su-kien", None, {"Cookie": ck_kh,
                                                      "X-Requested-With": "VIPHub"}), giay=3.0)
        ket("G18-02b", "CÙNG cửa ĐỌC, MỘT luồng (mốc so sánh) · 0 lỗi, 0 5xx",
            DAT if (sd_doc_1["so_5xx"] == 0 and sd_doc_1["loi_ket_noi"] == 0
                    and sd_doc_1["tong"] > 0) else HONG,
            "%s ⇒ 8 luồng nhanh hơn 1 luồng %.2f× (KHÔNG phải 8× — xem G18-06c)"
            % (tom_tat_so_do(sd_doc_1),
               sd_doc["req_giay"] / max(0.1, sd_doc_1["req_giay"])))
        # KẾT LUẬN VỀ ĐỘ CO GIÃN: 8 luồng KHÔNG cho 8 lần. Nhưng "vì sao" thì lượt này KHÔNG trả
        # lời được bằng CPU time — `ps` bị sandbox chặn trên máy này (`/bin/ps: Operation not
        # permitted`), nên `cpu_giay()` trả `None`. Cách trả lời bằng suy đoán ("chắc là GIL") là
        # đúng thứ tài liệu dự án cấm. Câu ấy được trả lời bằng một phép đo KHÁC ở `G18-06c`:
        # cùng 8 luồng client, chia trên HAI tiến trình máy chủ.
        ket("G18-02c", "8 luồng KHÔNG cho 8 lần; đo được tỉ lệ, KHÔNG đo được CPU time",
            BO_QUA,
            "1 luồng=%.1f yêu cầu/giây · 8 luồng=%.1f yêu cầu/giây = %.2f× (không phải 8×) ·"
            " CPU time: KHÔNG ĐO ĐƯỢC (`ps` bị sandbox chặn) ⇒ nguyên nhân KHÔNG được suy đoán ở"
            " đây; xem phép đo hai tiến trình ở G18-06c"
            % (sd_doc_1["req_giay"], sd_doc["req_giay"],
               sd_doc["req_giay"] / max(0.1, sd_doc_1["req_giay"])))

        # -------------------------------------------------------------- G18-03 CỬA GHI, tải
        print("\n── G18-03. CỬA GHI DƯỚI TẢI (POST webhook, chữ ký ĐÚNG) ──────")
        so_ghi = 300

        def than_su_kien(i):
            return json.dumps({"event": "dang_giao", "tracking_number": "G18-TAI-%d" % i,
                               "event_id": "g18-tai-%d" % i,
                               "hang_luc": "2026-10-15T08:00:00+07:00"},
                              ensure_ascii=False).encode()

        def dung_bai_ghi(i):
            b = than_su_kien(i)
            return ("POST", "/api/v2/webhook/nhan/%s" % wh_ma, b,
                    {"X-Webhook-Signature": hmac.new(secret.encode(), b, hashlib.sha256).hexdigest(),
                     "Content-Type": "application/json"})

        # Cửa GHI cần số thứ tự TĂNG DẦN cho mỗi lượt (xem `_chay_tai_dong`), nên nó dùng bộ
        # chạy riêng thay vì `BoTai.chay` (vốn nhận MỘT thân yêu cầu cố định cho mọi lượt).
        dem_sk = {"n": 0}
        khoa_sk = threading.Lock()

        def dung_bai_ghi_dong():
            with khoa_sk:
                dem_sk["n"] += 1
                i = dem_sk["n"]
            return dung_bai_ghi(i)

        sd_ghi = _chay_tai_dong(t1, so_ghi, dung_bai_ghi_dong, so_luong=8)
        so_dong = sql("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?", (tk_id,))[0]["c"]
        ma_ok = sd_ghi["theo_ma"].get("202", 0) + sd_ghi["theo_ma"].get("200", 0)
        ket("G18-03", "cửa GHI (webhook, chữ ký ĐÚNG) dưới tải 8 luồng · %d yêu cầu" % so_ghi,
            DAT_MOCK if (sd_ghi["so_5xx"] == 0 and sd_ghi["loi_ket_noi"] == 0
                         and ma_ok == so_ghi and so_dong == so_ghi) else HONG,
            "%s · dòng trong wh_su_kien=%d (mong đợi %d)"
            % (tom_tat_so_do(sd_ghi), so_dong, so_ghi))

        # ------------------------------------------------- G18-03b/03c TRẦN CỦA CHÍNH CỬA GHI
        print("\n── G18-03b. TRẦN `webhook.nhan` QUA HTTP (chữ ký ĐÚNG) ──────")
        # Cửa GHI có HAI trần, và trần thứ nhất (`webhook.nhan`, 600 lượt/60 giây) đếm MỌI lượt
        # — kể cả lượt có chữ ký ĐÚNG. Chính chú thích trong `gioi_han.py` lo điều này: "hãng thật
        # bắn dồn hàng loạt sự kiện sau một đợt quét kho và lượt bị chặn oan là sự kiện giao hàng
        # bị MẤT". Đây là chỗ đo xem điều đó có xảy ra THẬT qua HTTP không.
        #
        # Tài khoản RIÊNG, và phải là tài khoản mới: `webhook.nhan` đếm theo `dinh_danh` =
        # `webhook_ma`, nên dùng lại `wh_ma` (đã tiêu 300 lượt ở G18-03) thì phép đo bắt đầu từ
        # bộ đếm 300 và con số ra là "600 trừ 300", không phải trần.
        tk_moi = _tao_tk_hang_co_secret(k_kh, "J&T G18 TranNhan", db)
        # Mặc định `None`: hai biến này được dùng ở G18-06, mà chúng chỉ được gán BÊN TRONG nhánh
        # dưới. Không khởi tạo thì nhánh "tạo tài khoản hãng hỏng" biến một ca HỎNG đã báo đúng
        # thành một `NameError` ở tận G18-06 — và `NameError` thì không nói được ca nào hỏng.
        sd_doc_2, so_dong_sau = None, None
        if not tk_moi:
            ket("G18-03b", "tạo được tài khoản hãng cho phép đo trần `webhook.nhan`", HONG,
                "cửa tạo tài khoản hãng không trả 201")
        else:
            wh_moi, secret_moi = tk_moi
            so_bom = 640
            k_bom = KhachTai("127.0.0.1", t1.cong)
            ds_bom = []
            try:
                for i in range(so_bom):
                    b = json.dumps({"event": "dang_giao", "tracking_number": "G18-BOM-%d" % i,
                                    "event_id": "g18-bom-%d" % i,
                                    "hang_luc": "2026-10-15T08:00:00+07:00"},
                                   ensure_ascii=False).encode()
                    try:
                        ma, _, _ = k_bom.goi(
                            "POST", "/api/v2/webhook/nhan/%s" % wh_moi, b,
                            {"X-Webhook-Signature": hmac.new(secret_moi.encode(), b,
                                                             hashlib.sha256).hexdigest(),
                             "Content-Type": "application/json"})
                    except Exception:                                    # noqa: BLE001
                        # Lỗi tầng kết nối ghi thành mã 0, KHÔNG ném ra ngoài: một lượt hỏng
                        # giữa chừng mà làm chết cả phép đo thì ca này không bao giờ chạy xong,
                        # và "không có kết quả" dễ bị đọc thành "không có vấn đề".
                        ma = 0
                    ds_bom.append(ma)
            finally:
                k_bom.dong()
            nhan = ds_bom.count(202) + ds_bom.count(200)
            chan = ds_bom.count(429)
            vi_tri_dau = ds_bom.index(429) if 429 in ds_bom else None
            ma_khac = {m: ds_bom.count(m) for m in sorted(set(ds_bom)) if m not in (200, 202, 429)}
            ket("G18-03b", "chữ ký ĐÚNG, %d sự kiện trong một phút ⇒ trần `webhook.nhan` chặn ở đâu"
                % so_bom,
                DAT_MOCK if (nhan == 600 and chan == so_bom - 600 and vi_tri_dau == 600
                             and not ma_khac) else HONG,
                "nhận=%d · chặn(429)=%d · lượt 429 ĐẦU TIÊN ở vị trí %s (trần khai báo 600/60s)"
                " · mã khác=%s ⇒ sự kiện có chữ ký HỢP LỆ của hãng vẫn bị chặn"
                % (nhan, chan, vi_tri_dau, ma_khac or "không có"))

            # Đo lại cửa ĐỌC khi bảng đã dày lên. Cùng một câu truy vấn, khác số dòng — để con số
            # "yêu cầu/giây" ở G18-02a có KÈM điều kiện của nó, thay vì được đọc như một hằng số.
            so_dong_sau = sql("SELECT COUNT(*) c FROM wh_su_kien")[0]["c"]
            sd_doc_2 = BoTai("127.0.0.1", t1.cong, so_luong=8).chay(
                ("GET", "/api/v2/webhook/su-kien", None,
                 {"Cookie": ck_kh, "X-Requested-With": "VIPHub"}), giay=3.0)
            ket("G18-03c", "cửa ĐỌC đo LẠI khi bảng đã dày lên (%d → %d dòng)"
                % (so_dong_truoc, so_dong_sau),
                DAT if (sd_doc_2["so_5xx"] == 0 and sd_doc_2["loi_ket_noi"] == 0
                        and sd_doc_2["tong"] > 0) else HONG,
                "%s ⇒ so với lúc bảng %d dòng: %.1f → %.1f yêu cầu/giây (%.2f×) — con số"
                " yêu cầu/giây CHỈ có nghĩa kèm số dòng; đọc nó mà bỏ số dòng là đọc sai"
                % (tom_tat_so_do(sd_doc_2), so_dong_truoc, sd_doc["req_giay"],
                   sd_doc_2["req_giay"], sd_doc_2["req_giay"] / max(0.1, sd_doc["req_giay"])))

        # -------------------------------------------------------------- G18-04 trần qua HTTP
        print("\n── G18-04. TRẦN TẦN SUẤT QUA HTTP vs GỌI THẲNG HÀM ────────────")
        # Cửa `webhook.chu_ky_sai`: 10 lượt/tài khoản/60 giây rồi chặn 300 giây. Đếm số lượt ĐƯỢC
        # QUA trước lượt 429 đầu tiên, đi qua HTTP thật. MỘT luồng, tuần tự: đây vừa là phép đo
        # trần, vừa là ĐỐI CHỨNG ÂM của cả lượt (cùng kịch bản, một luồng, phải đúng và không lỗi).
        wh_sai = _tao_tk_hang(k_kh, "J&T G18 SaiChuKy", db) or wh_ma
        k_sai = KhachTai("127.0.0.1", t1.cong)
        ds_ma_sai = []
        try:
            for i in range(14):
                ma, _, _ = k_sai.goi("POST", "/api/v2/webhook/nhan/%s" % wh_sai,
                                     b'{"event":"dang_giao","tracking_number":"G18-SAI"}',
                                     {"X-Webhook-Signature": "0" * 64,
                                      "Content-Type": "application/json"})
                ds_ma_sai.append(ma)
        finally:
            k_sai.dong()
        dat_sai, ly_sai = phan_quyet_tran(ds_ma_sai, 10)
        ket("G18-04a", "ĐỐI CHỨNG ÂM (MỘT luồng): chữ ký SAI ⇒ đúng 10 lượt 401 rồi 429 liên tục",
            DAT if dat_sai else HONG,
            "chuỗi mã HTTP=%s · %s" % (ds_ma_sai, ly_sai))

        # Cùng phép đếm, nhưng gọi THẲNG hàm `gioi_han.kiem` trong tiến trình harness. Đây là
        # "đường khác" mà mọi bàn đo trước G18 đi — nếu hai đường cho cùng trần thì trần đúng ở
        # cả hai; lệch nghĩa là đường HTTP có chỗ cộng/không cộng lượt mà đường hàm không có.
        import gioi_han                                                     # noqa: E402
        gioi_han.xoa_het()
        kq_ham = []
        for _ in range(14):
            kq_ham.append("cho_qua" if gioi_han.kiem(
                "webhook.chu_ky_sai", ip="127.0.0.1", dinh_danh="g18-do-truc-tiep").cho_phep
                else "chan")
        so_qua_ham = kq_ham.count("cho_qua")
        ket("G18-04b", "cùng trần, đo bằng GỌI THẲNG HÀM `gioi_han.kiem` (đường cũ)",
            DAT if (so_qua_ham == 10 and kq_ham[10:] == ["chan"] * 4) else HONG,
            "chuỗi=%s · số lượt được qua=%d (HTTP cho qua=%d)"
            % (kq_ham, so_qua_ham, ds_ma_sai.count(401)))
        ket("G18-04c", "HAI ĐƯỜNG cho CÙNG một trần (HTTP thật ↔ gọi thẳng hàm)",
            DAT if (so_qua_ham == ds_ma_sai.count(401) == 10) else HONG,
            "HTTP=%d lượt qua · hàm=%d lượt qua · khác nhau nghĩa là đường HTTP cộng lượt khác"
            " đường hàm" % (ds_ma_sai.count(401), so_qua_ham))

        # -------------------------------------------------------------- G18-05 header trần
        print("\n── G18-05. HEADER TRẦN TRÊN LƯỢT BỊ CHẶN ─────────────────────")
        k_h = KhachTai("127.0.0.1", t1.cong)
        try:
            ma_h, hdr_h, _ = k_h.goi("POST", "/api/v2/webhook/nhan/%s" % wh_sai, b"{}",
                                     {"X-Webhook-Signature": "0" * 64,
                                      "Content-Type": "application/json"})
        finally:
            k_h.dong()
        co_ra = hdr_h.get("retry-after")
        ket("G18-05", "lượt bị chặn trả `Retry-After` + `X-RateLimit-*` đọc được qua HTTP",
            DAT if (ma_h == 429 and co_ra and str(co_ra).isdigit() and int(co_ra) > 0) else HONG,
            "HTTP=%s · Retry-After=%s · X-RateLimit-Limit=%s · X-RateLimit-Window=%s"
            % (ma_h, co_ra, hdr_h.get("x-ratelimit-limit"), hdr_h.get("x-ratelimit-window")))

        # -------------------------------------------------------------- G18-06 B-G11-10
        print("\n── G18-06. B-G11-10: TRẦN CÓ NHÂN THEO SỐ TIẾN TRÌNH KHÔNG ──")
        wh_da = _tao_tk_hang(k_kh, "J&T G18 ĐaTiếnTrình", db) or wh_ma
        # Đếm TRƯỚC khi tiến trình thứ hai khởi động — xem G18-06d. Đếm ở đây chứ không trong
        # nhánh `else` của G18-03b: biến dùng ở G18-06 mà chỉ được gán trong một nhánh `if` là
        # `NameError` chờ sẵn, và nó chỉ nổ khi nhánh kia chạy — tức là đúng lượt khó chẩn đoán nhất.
        so_dong_sau = sql("SELECT COUNT(*) c FROM wh_su_kien")[0]["c"]
        so_dang_xu_ly_truoc = sql("SELECT COUNT(*) c FROM wh_su_kien"
                                  " WHERE trang_thai='dang_xu_ly'")[0]["c"]
        # Một tiến trình: trần tham chiếu (đã đo ở G18-04a = 10). Hai tiến trình: CÙNG CSDL tạm,
        # bắn XEN KẼ. `gioi_han` giữ bộ đếm trong BỘ NHỚ TIẾN TRÌNH (đọc thẳng mã: `_lan` là
        # OrderedDict + threading.Lock, không có CSDL chống lưng), nên dự đoán là 2 × 10 = 20.
        t2 = TienTrinhMayChu("may-chu-2", nen, env, os.path.join(nen, "server-2.log")).bat_dau()
        ds_tt.append(t2)
        _tai_pid(nen, ds_tt)
        print("  · máy chủ 2: %s (pid %d) — CÙNG CSDL tạm, chỉ loopback" % (t2.goc, t2.pid))
        k1, k2 = KhachTai("127.0.0.1", t1.cong), KhachTai("127.0.0.1", t2.cong)
        ds_ma_2 = []
        dem_theo_tt = {t1.nhan: [], t2.nhan: []}
        try:
            for i in range(40):
                k = k1 if i % 2 == 0 else k2
                ma, _, _ = k.goi("POST", "/api/v2/webhook/nhan/%s" % wh_da, b"{}",
                                 {"X-Webhook-Signature": "0" * 64,
                                  "Content-Type": "application/json"})
                ds_ma_2.append(ma)
                dem_theo_tt[t1.nhan if i % 2 == 0 else t2.nhan].append(ma)
                if ds_ma_2.count(429) >= 20:
                    break
        finally:
            k1.dong()
            k2.dong()
        qua_2 = ds_ma_2.count(401)
        qua_1 = ds_ma_sai.count(401)
        ket("G18-06a", "ĐO ĐƯỢC trần thực khi có HAI tiến trình máy chủ (cùng CSDL, cùng IP)",
            BLOCKED if qua_2 != 20 else DAT,
            "tổng lượt được qua ở hai tiến trình=%d · một tiến trình (G18-04a)=%d · tỉ lệ=%.1f×"
            " · chuỗi=%s" % (qua_2, qua_1, qua_2 / max(1, qua_1), ds_ma_2[:24]))
        print("        · chia theo tiến trình: %s"
              % {k: (v.count(401), v.count(429)) for k, v in dem_theo_tt.items()})
        # Đối chứng: tổng số lượt bị chặn KHÔNG được vượt quá số lượt đã gửi — nếu không thì bộ
        # đếm đang đếm sai (một lượt trả hai mã là chuyện không xảy ra, nhưng cộng sai thì có).
        ket("G18-06b", "bộ đếm không tự mâu thuẫn: qua + chặn ≤ số lượt đã gửi",
            DAT if (ds_ma_2.count(401) + ds_ma_2.count(429) <= len(ds_ma_2)) else HONG,
            "gửi=%d · qua=%d · chặn=%d · mã khác=%s"
            % (len(ds_ma_2), ds_ma_2.count(401), ds_ma_2.count(429),
               {m: ds_ma_2.count(m) for m in set(ds_ma_2) if m not in (401, 429)}))

        # ------------------------------------------------- G18-06c BĂNG THÔNG: luồng vs tiến trình
        # BA NHÁNH, chạy LIỀN NHAU để điều kiện máy là như nhau:
        #   A ) 4 luồng, MỘT tiến trình          — tải mỗi tiến trình = 4 luồng
        #   A2) 8 luồng, MỘT tiến trình          — gấp đôi LUỒNG, y nguyên số tiến trình
        #   B ) 8 luồng chia trên HAI tiến trình — tải mỗi tiến trình = 4 luồng (bằng nhánh A)
        # A2 so với A trả lời "thêm LUỒNG trong một tiến trình được gì"; B so với A trả lời "thêm
        # TIẾN TRÌNH được gì" với tải mỗi tiến trình Y HỆT. Bản đầu lấy mốc A2 từ `G18-03c` —
        # tức là đo ở một THỜI ĐIỂM KHÁC — nên điều kiện máy xen vào giữa hai phép đo, và đó đúng
        # là chỗ một kết luận về co giãn dễ sai nhất.
        dung_bai_doc = ("GET", "/api/v2/webhook/su-kien", None,
                        {"Cookie": ck_kh, "X-Requested-With": "VIPHub"})
        sd_a_4l = BoTai("127.0.0.1", t1.cong, so_luong=4).chay(dung_bai_doc, giay=3.0)
        sd_a2_8l = BoTai("127.0.0.1", t1.cong, so_luong=8).chay(dung_bai_doc, giay=3.0)
        sd_b_2tt = BoTai("127.0.0.1", t1.cong, so_luong=8,
                         ds_dich=[("127.0.0.1", t1.cong), ("127.0.0.1", t2.cong)]).chay(
            dung_bai_doc, giay=3.0)
        if sd_doc_2 is None:
            ket("G18-06c", "BĂNG THÔNG cửa ĐỌC: cùng tải mỗi tiến trình, 1 vs 2 tiến trình",
                BO_QUA, "thiếu mốc bảng 900 dòng ở G18-03c để đối chiếu ⇒ không kết luận")
        else:
            ket("G18-06c", "BĂNG THÔNG cửa ĐỌC ở bảng %d dòng: thêm LUỒNG vs thêm TIẾN TRÌNH"
                % so_dong_sau,
                DAT if all(x["so_5xx"] == 0 and x["loi_ket_noi"] == 0 and x["tong"] > 0
                           for x in (sd_a_4l, sd_a2_8l, sd_b_2tt)) else HONG,
                "A) 4 luồng/MỘT tiến trình=%.1f · A2) 8 luồng/MỘT tiến trình=%.1f (%.2f× so với A)"
                " · B) 4+4 luồng/HAI tiến trình=%.1f (%.2f× so với A) ⇒ GẤP ĐÔI LUỒNG trong một"
                " tiến trình cho %.2f×, còn THÊM MỘT TIẾN TRÌNH (tải mỗi tiến trình y hệt A) cho"
                " %.2f× · đối chiếu G18-03c (8 luồng/MỘT tiến trình, đo ở lượt khác)=%.1f"
                % (sd_a_4l["req_giay"], sd_a2_8l["req_giay"],
                   sd_a2_8l["req_giay"] / max(0.1, sd_a_4l["req_giay"]), sd_b_2tt["req_giay"],
                   sd_b_2tt["req_giay"] / max(0.1, sd_a_4l["req_giay"]),
                   sd_a2_8l["req_giay"] / max(0.1, sd_a_4l["req_giay"]),
                   sd_b_2tt["req_giay"] / max(0.1, sd_a_4l["req_giay"]),
                   sd_doc_2["req_giay"]))

        # ------------------------------------------------- G18-06d MỘT QUAN SÁT CÓ THẬT
        # `webhook.khoi_dong()` của tiến trình thứ hai chạy trên CÙNG CSDL và có câu
        #     UPDATE wh_su_kien SET trang_thai='moi' WHERE trang_thai='dang_xu_ly'
        # tức là nó GIÀNH LẠI mọi sự kiện mà tiến trình thứ nhất đang xử lý dở. Đây là quan sát
        # giá trị ĐO ĐƯỢC, không phải lời khai về thiết kế: đếm số dòng `dang_xu_ly` ngay trước và
        # ngay sau khi tiến trình hai khởi động, rồi đếm xem có dòng nào bị xử lý HAI LẦN không.
        # (Ghi ra vì nó thuộc đúng câu hỏi của lượt: "nhiều tiến trình máy chủ thì sao".)
        ket("G18-06d", "quan sát: tiến trình máy chủ thứ hai chạm vào sự kiện của tiến trình thứ nhất",
            BO_QUA,
            "số dòng `wh_su_kien` ở trạng thái 'dang_xu_ly' TRƯỚC khi tiến trình 2 khởi động=%d ·"
            " SAU=%d · tổng số dòng=%d. Đây là QUAN SÁT, chưa phải lỗi đã chứng minh: lượt này"
            " không dựng được ca đủ chặt để khẳng định xử lý trùng. Cần một lượt riêng."
            % (so_dang_xu_ly_truoc, sql("SELECT COUNT(*) c FROM wh_su_kien"
                                        " WHERE trang_thai='dang_xu_ly'")[0]["c"],
               sql("SELECT COUNT(*) c FROM wh_su_kien")[0]["c"]))

        # -------------------------------------------------------------- G18-07 đối chứng âm
        print("\n── G18-07. ĐỐI CHỨNG ÂM: CÙNG KỊCH BẢN, MỘT LUỒNG ───────────")
        k_mot = KhachTai("127.0.0.1", t1.cong)
        ds_mot = []
        try:
            for i in range(50):
                b = than_su_kien(100000 + i)
                ma, _, _ = k_mot.goi(
                    "POST", "/api/v2/webhook/nhan/%s" % wh_ma, b,
                    {"X-Webhook-Signature": hmac.new(secret.encode(), b,
                                                     hashlib.sha256).hexdigest(),
                     "Content-Type": "application/json"})
                ds_mot.append(ma)
        finally:
            k_mot.dong()
        dung_het = ds_mot.count(202) + ds_mot.count(200) == 50
        ket("G18-07a", "50 lượt cửa GHI, MỘT luồng ⇒ 50 lượt nhận, KHÔNG 5xx, KHÔNG lỗi",
            DAT_MOCK if (dung_het and 500 not in ds_mot and 0 not in ds_mot) else HONG,
            "mã=%s" % {m: ds_mot.count(m) for m in sorted(set(ds_mot))})
        # Cùng câu hỏi cho cửa ĐỌC: một luồng, 30 lượt, phải 200 cả 30.
        k_motd = _khach_co_phien(t1.cong, ck_kh)
        ds_motd = []
        try:
            for _ in range(30):
                ma, _, _ = k_motd.goi("GET", "/api/v2/webhook/su-kien")
                ds_motd.append(ma)
        finally:
            k_motd.dong()
        ket("G18-07b", "30 lượt cửa ĐỌC, MỘT luồng ⇒ 200 cả 30, không lỗi",
            DAT if set(ds_motd) == {200} else HONG,
            "mã=%s" % {m: ds_motd.count(m) for m in sorted(set(ds_motd))})

        # -------------------------------------------------------------- G18-08 log có cấu trúc
        print("\n── G18-08. DẤU VẾT: LOG JSON + X-Request-Id TRÊN ĐƯỜNG TẢI ──")
        k_l = KhachTai("127.0.0.1", t1.cong)
        try:
            _, hdr_l, _ = k_l.goi("GET", "/api/v2/webhook/su-kien", None,
                                  {"Cookie": ck_kh, "X-Requested-With": "VIPHub"})
        finally:
            k_l.dong()
        rid = hdr_l.get("x-request-id")
        so_dong_json = 0
        for ten in ("server-1.log", "server-2.log"):
            duong = os.path.join(nen, ten)
            if os.path.isfile(duong):
                with open(duong, encoding="utf-8", errors="replace") as f:
                    for dong in f:
                        if dong.lstrip().startswith("{"):
                            so_dong_json += 1
        ket("G18-08", "mỗi lượt HTTP có `X-Request-Id`; log máy chủ THẬT có dòng JSON",
            DAT if (rid and so_dong_json > 0) else HONG,
            "X-Request-Id=%s · số dòng JSON trong log máy chủ=%d" % (rid, so_dong_json))

        # -------------------------------------------------------------- kết luận
        print("\n" + "═" * 78)
        dem = dem_phuong_an(BUOC)
        print("KẾT LUẬN: %d/%d ca đạt · %d hỏng · %d BLOCKED · %d bỏ qua"
              % (dem[DAT] + dem[DAT_MOCK], len(BUOC), dem[HONG], dem[BLOCKED], dem[BO_QUA]))
        for x in BUOC:
            print("  %s [%s] %s" % (KY_HIEU[x["trang_thai"]], x["ma"], x["ten"]))
        print("\nNẰM NGOÀI PHẠM VI (chưa đo, và KHÔNG được coi là đã đo):")
        print("  · TLS/HTTPS thật (`V-G11-01` CHƯA CẤP — không tunnel, không deploy)")
        print("  · MẠNG thật: mọi lượt đi qua loopback, không qua dây, không qua proxy")
        print("  · nhiều MÁY: hai tiến trình ở đây nằm CÙNG một máy, CÙNG một ổ đĩa")
        print("  · gọi hãng thật kể cả sandbox: %s" % " · ".join(THIEU_GOI_HANG))
        print("  · Docker/`mem_limit`/`pids_limit`: Docker CHƯA CÀI trên máy này")
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump({"nen": nen, "cau_hinh": {
                    "so_tien_trinh": a.so_tien_trinh, "so_luong_luong": 8,
                    "cua_doc": "GET /api/v2/webhook/su-kien", "cua_ghi":
                    "POST /api/v2/webhook/nhan/<webhook_ma>"},
                    "buoc": BUOC, "dem": dem}, f, ensure_ascii=False, indent=1)
            print("\nBáo cáo máy đọc được: %s" % a.json)
        return 0 if dem[HONG] == 0 else 1
    finally:
        for t in reversed(ds_tt):
            t.dung()
        if ds_tt:
            print("[g18] đã tắt %d tiến trình máy chủ theo ĐÚNG PID: %s"
                  % (len(ds_tt), ", ".join(str(t.pid) for t in ds_tt)))


def _chay_tai_dong(tt, so_luong_yeu_cau, sinh_dung_bai, so_luong=8):
    """Bộ chạy tải cho cửa GHI: mỗi lượt cần một THÂN YÊU CẦU KHÁC NHAU (số thứ tự tăng dần).

    Vì sao không dùng `BoTai.chay`: nó nhận MỘT `dung_bai` cố định cho mọi lượt. Nhồi cùng một
    `event_id` vào cửa GHI thì máy chủ trả 200 (đã nhận trước đó) thay vì 202, và phép đo "nhận
    sự kiện mới dưới tải" lặng lẽ biến thành phép đo chống trùng.
    """
    mau, khoa = [], threading.Lock()
    dem = {"n": 0}

    def luong():
        k = KhachTai("127.0.0.1", tt.cong)
        try:
            while True:
                with khoa:
                    if dem["n"] >= so_luong_yeu_cau:
                        return
                    dem["n"] += 1
                bt = BoTai("127.0.0.1", tt.cong, so_luong=1)
                mau.append(bt._mot_luot(k, sinh_dung_bai()))
        finally:
            k.dong()

    t0 = time.perf_counter()
    ds = [threading.Thread(target=luong, daemon=True, name="g18-ghi-%d" % i)
          for i in range(so_luong)]
    for t in ds:
        t.start()
    for t in ds:
        t.join()
    return thong_ke(mau, time.perf_counter() - t0)


def _secret_webhook_tu_db(db, tk_id):
    """Đọc và giải mã secret webhook của một tài khoản hãng. KHÔNG BAO GIỜ in giá trị ra.

    Trả `(webhook_ma, secret)` hoặc `None`. Dùng kết nối RIÊNG, không qua `csdl` — để phép đo
    đọc thẳng tầng CSDL chứ không mượn đường của mã đang được đo.
    """
    import bao_mat
    c = sqlite3.connect(db, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        r = c.execute("SELECT webhook_ma, webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?",
                      (tk_id,)).fetchone()
    finally:
        c.close()
    if not r or not r["webhook_ma"]:
        return None
    return r["webhook_ma"], bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], r["webhook_ma"])


def _tao_tk_hang(k_kh, ten, db):
    """Tạo thêm một tài khoản hãng MOCK và trả `webhook_ma` của nó (không cần secret)."""
    tk = _tao_tk_hang_co_secret(k_kh, ten, db)
    return tk[0] if tk else None


def _tao_tk_hang_co_secret(k_kh, ten, db):
    """Tạo thêm một tài khoản hãng MOCK, trả `(webhook_ma, secret)` — secret KHÔNG in ra log.

    Vì sao cần tài khoản RIÊNG cho mỗi phép đo trần: bucket của `gioi_han` khoá theo
    `dinh_danh` = `webhook_ma` (cả `webhook.chu_ky_sai` lẫn `webhook.nhan`). Đo lại trên cùng
    một `webhook_ma` thì lượt đo thứ hai bắt đầu từ bộ đếm đã có sẵn — con số ra sẽ là "trần trừ
    đi lượt trước", không phải trần. Đây là chỗ dễ tự lừa nhất trong cả lượt: nó KHÔNG báo lỗi,
    chỉ cho ra một số nhỏ hơn và trông như hệ đang chặn chặt hơn thực tế.
    """
    ma, kq = k_kh.json("POST", "/api/v2/tai-khoan-hang",
                       {"hang": "jt", "ten": ten,
                        "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
    if ma != 201 or not isinstance(kq, dict) or not kq.get("id"):
        return None
    return _secret_webhook_tu_db(db, kq["id"])


if __name__ == "__main__":
    sys.exit(main())
