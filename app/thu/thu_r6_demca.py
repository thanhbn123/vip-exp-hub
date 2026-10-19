#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R6 — BỘ ĐẾM DÙNG CHUNG: đọc ĐÚNG khuôn báo cáo của từng LOẠI runner.

VÌ SAO CÓ TỆP NÀY
=================
`app/thu/chay_tat_ca.sh` từng tự viết regex trong shell (và `thu_g22_zeroca.py`,
`thu_g22_gioihan.py` giữ bản sao regex riêng). Ba bản sao ấy trôi khỏi nhau, và mỗi lần trôi
thì bảng tổng kết lại ghi một con số KHÁC con số bộ thử vừa công bố. Tệp này là **một** chỗ
duy nhất hiểu các khuôn báo cáo; `chay_tat_ca.sh` chỉ gọi nó.

Nó KHÔNG sửa bộ thử nào, KHÔNG sửa mã sản phẩm, KHÔNG gọi mạng, KHÔNG dùng credentials.

BA LOẠI RUNNER, BA KHUÔN KHÁC NHAU
==================================
1. **unittest** (phần lớn bộ thử):
       Ran 31 tests in 8.871s
       OK                                  (hoặc FAILED (failures=1, errors=2, skipped=3))
   `Ran N` ĐÃ GỒM ca skipped. Vì thế KHÔNG được gọi N là "số ca chạy thật": phải trừ
   `skipped=` ra mới được "có kết quả".

2. **Playwright** (cổng E2E):
       2 passed
       25 failed
       0 skipped
       53 did not run
       0 flaky
   Tổng kế hoạch = tổng sáu nhãn. "did not run" và "skipped" KHÔNG phải ca đã chạy. Bản cũ
   cộng cả 53 vào "ca chạy thật" — sai ngay ở mẫu số.

3. **bộ viết tay** (G18/G19/G21/G22…):
       ca ĐẠT: 27 · HỎNG: 3 · BỎ QUA: 0 · KHÔNG KẾT LUẬN: 2 · TỔNG: 32
       ca ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=38     (dấu `=`, dòng CUỐI của G21)
       27 ca — ĐẠT, 5 ca HỎNG          (dòng kết luận khi hỏng — HAI con số, không phải một)
       32 ca — ĐẠT                      (dòng kết luận khi đạt)
       TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)
       số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 2/25/0/53/0

   Khuôn `=` là chỗ bộ đếm cũ SAI THẬT: `thu_g21_gioihan.py` công bố `TỔNG=38` ở dòng cuối,
   nhưng phần bằng chứng phía trên có câu `['  22 ca — ĐẠT']` của bộ CON; bộ đếm cũ bắt câu 22
   và báo 22. Bộ đếm này lấy ứng viên KẾT THÚC MUỘN NHẤT trong output, nên đọc 38.

BỐN CON SỐ TÁCH RỜI (yêu cầu R6)
================================
    KE_HOACH     số ca runner CÔNG BỐ (gồm bỏ qua + chưa chạy)
    CO_KET_QUA   số ca THỰC SỰ có phán quyết đạt/hỏng (KHÔNG gồm skip, did-not-run, KHUYẾT)
    BO_QUA       ca bỏ qua có chủ đích (unittest `skipped=`, Playwright `skipped`)
    CHUA_CHAY    ca không chạy (Playwright `did not run`; các runner khác = 0)
    KHONG_KET_LUAN ca đã chạy nhưng không kết luận được (KHUYẾT, interrupted)

`N` (khoá cũ mà `thu_g22_demca2.py` / `thu_qa_nguyennhan.py` đọc) GIỮ NGUYÊN nghĩa: số ca
runner công bố. Nhờ thế tệp này thay được bộ đếm cũ mà không phải sửa bộ tự kiểm của QA.
Muốn biết "ca chạy thật" thì đọc `CO_KET_QUA`, KHÔNG đọc `N`.

LUẬT PHÁN — KHÔNG NỚI, CHỈ ĐỌC ĐÚNG HƠN
=======================================
    DAT     mã thoát 0 · KE_HOACH > 0 · có dấu vết đã chạy · không tự báo HỎNG · CHUA_CHAY = 0
    BO_QUA  mã thoát 0 · KE_HOACH = 0 · output có `skipped` / `skipped=N` (bỏ qua có chủ đích)
    HONG    mọi trường hợp còn lại, kèm lý do:
              · mã thoát ≠ 0
              · thoát 0 nhưng tự báo HỎNG / còn ca failed
              · thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào      ← XANH GIẢ, luôn HỎNG
              · thoát 0 nhưng KE_HOACH = 0                        ← "0 ca" không phải ĐẠT
              · thoát 0 nhưng còn `did not run`                   ← chưa chạy không phải ĐẠT

BẰNG CHỨNG TỰ KIỂM (chạy `python3 app/thu/thu_r6_demca.py`)
===========================================================
Mỗi điều kiện (a)–(e) có vế CHÍNH và **ĐỐI CHỨNG ÂM**. Mỗi mẫu được đo HAI lần: gọi thẳng
hàm `dem()` và gọi qua `sh app/thu/chay_tat_ca.sh --tinh-ca`; hai kết quả phải trùng nhau —
nếu ai đó chép lại regex vào shell, vế thứ hai sẽ lệch và bộ tự kiểm đỏ.

MÃ THOÁT
========
    0  mọi mẫu KHỚP       1  có mẫu LỆCH (bộ đếm sai)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAY = os.path.join(GOC, "app", "thu", "chay_tat_ca.sh")

MA_DAT, MA_HONG, MA_LOI = 0, 1, 2

DAT, HONG, BO_QUA = "DAT", "HONG", "BO_QUA"

# ── khuôn unittest ────────────────────────────────────────────────────────────────────────────
_RE_RAN = re.compile(r"^Ran (\d+) tests? in \d+(?:\.\d+)?s\s*$", re.M)
_RE_RAN_DU_PHONG = re.compile(r"^Ran (\d+) tests?\s*$", re.M)
_RE_KQ_UT = re.compile(r"^(OK|FAILED)\b[^\n]*", re.M)
_RE_SKIP = re.compile(r"\bskipped=(\d+)")
_RE_FAIL = re.compile(r"\bfailures=(\d+)")
_RE_LOI = re.compile(r"\berrors=(\d+)")

# ── khuôn Playwright: một KHỐI các dòng `<số> <nhãn>` liền nhau ────────────────────────────────
_RE_PW = re.compile(
    r"^[ \t]*(\d+)[ \t]+(passed|failed|skipped|did not run|flaky|interrupted)\b[^\n]*", re.M)

# ── khuôn node --test (tầng 1 frontend): `ℹ pass 56` / `# pass 56` ─────────────────────────────
# Bắt MỌI nhãn (kể cả `tests`, `suites`, `cancelled`, `duration_ms`) để một dòng như
# `ℹ cancelled 0` nằm giữa không cắt khối tổng kết làm hai.
_RE_NODE = re.compile(
    r"^[ \t]*(?:ℹ|#)[ \t]*([a-z_]+)[ \t]+(\d+)\b[^\n]*", re.M)

# ── khuôn bộ viết tay ─────────────────────────────────────────────────────────────────────────
_RE_CONG_E2E = re.compile(
    r"số ca[ \t]+ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN[ \t]*:[ \t]*"
    r"(\d+)/(\d+)/(\d+)/(\d+)/(\d+)")
_RE_TONG = re.compile(r"TỔNG:[ \t]*(\d+)[ \t]*ca[ \t]*—[ \t]*(ĐẠT|HỎNG)(?:[ \t]*\(([^)\n]*)\))?")
_RE_AGG = re.compile(
    r"ca ĐẠT:[ \t]*(\d+)[ \t]*·[ \t]*HỎNG:[ \t]*(\d+)[ \t]*·[ \t]*BỎ QUA:[ \t]*(\d+)"
    r"[ \t]*·[ \t]*KHÔNG KẾT LUẬN:[ \t]*(\d+)[ \t]*·[ \t]*TỔNG:[ \t]*(\d+)")
# Khuôn của G19/G21/G22 — dấu `=` chứ không phải `:`. ĐÂY LÀ LỖI ĐỌC THẬT ĐO ĐƯỢC:
# `thu_g21_gioihan.py` công bố `ca ĐẠT=38 … TỔNG=38` ở DÒNG CUỐI, nhưng bộ đếm cũ chỉ khớp
# `N ca — ĐẠT` nên bắt câu `['  22 ca — ĐẠT']` nằm trong phần BẰNG CHỨNG (số của bộ CON) —
# báo 22 trong khi bộ mẹ công bố 38. Cùng khuôn này đã có bộ thử `thu_g19_tich_hop.py` đọc.
_RE_AGG_BANG = re.compile(
    r"ca ĐẠT=(\d+)[ \t]*·[ \t]*HỎNG=(\d+)[ \t]*·[ \t]*BỎ QUA=(\d+)"
    r"[ \t]*·[ \t]*KHUYẾT=(\d+)[ \t]*·[ \t]*TỔNG=(\d+)")
_RE_DAT_HONG = re.compile(r"(\d+)[ \t]*ca[ \t]*—[ \t]*ĐẠT[ \t]*,[ \t]*(\d+)[ \t]*ca[ \t]*HỎNG")
_RE_DAT = re.compile(r"(\d+)[ \t]*ca[ \t]*—[ \t]*ĐẠT")
_RE_HONG = re.compile(r"(\d+)[ \t]*ca[ \t]*—[ \t]*HỎNG")
_RE_TONG_DON = re.compile(r"TỔNG:[ \t]*(\d+)[ \t]*ca")
_RE_KET_QUA = re.compile(r"KẾT QUẢ:[ \t]*(\d+)[ \t]*/[ \t]*(\d+)")

_RE_DAU_VET = re.compile(
    r"^OK( |$)|ca — ĐẠT|số ca[ \t]+ĐẠT/HỎNG|ca ĐẠT[=:]|"
    r"^[ \t]*\d+[ \t]+(?:passed|failed)\b|KẾT QUẢ:", re.M)

# Lý do dạng MÃ cho shell (giá trị không có dấu cách ⇒ `eval` an toàn).
LY_DO_MA = {
    "ma_thoat": "mã thoát khác 0",
    "tu_bao_hong": "thoát 0 nhưng báo cáo tự in `ca — HỎNG`",
    "khong_dau_vet": "thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào",
    "khong_ca": "thoát 0 nhưng đếm được 0 ca",
    "chua_chay": "thoát 0 nhưng còn ca `did not run`",
    "khong_doc_duoc": "không đọc được output",
}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# KẾT QUẢ
# ══════════════════════════════════════════════════════════════════════════════════════════════
class KetQua(object):
    """Một dòng bảng tổng kết: bốn con số tách rời + phán quyết + bằng chứng."""

    def __init__(self, ma=0, ke_hoach=0, co_ket_qua=0, dat=-1, hong=-1, bo_qua=0,
                 chua_chay=0, khong_ket_luan=0, loai="khong_ro", khuon="không khớp khuôn nào",
                 phan=HONG, ly_do="", ly_do_ma="khong_doc_duoc", dau_vet=0,
                 hong_tu_bao=0, vi_tri=-1):
        self.ma = ma
        self.ke_hoach = ke_hoach
        self.co_ket_qua = co_ket_qua
        self.dat = dat
        self.hong = hong
        self.bo_qua = bo_qua
        self.chua_chay = chua_chay
        self.khong_ket_luan = khong_ket_luan
        self.loai = loai
        self.khuon = khuon
        self.phan = phan
        self.ly_do = ly_do
        self.ly_do_ma = ly_do_ma
        self.dau_vet = dau_vet
        self.hong_tu_bao = hong_tu_bao
        self.vi_tri = vi_tri

    def khoa(self):
        """Dạng phẳng cho `--tinh-ca` (tương thích bộ tự kiểm QA) và `--shell`."""
        return {
            "N": self.ke_hoach,
            "KHUON": self.khuon,
            "PHAN": self.phan,
            "LY_DO": self.ly_do,
            "KE_HOACH": self.ke_hoach,
            "CO_KET_QUA": self.co_ket_qua,
            "DAT": self.dat,
            "HONG": self.hong,
            "BO_QUA": self.bo_qua,
            "CHUA_CHAY": self.chua_chay,
            "KHONG_KET_LUAN": self.khong_ket_luan,
            "LOAI": self.loai,
            "DAU_VET": self.dau_vet,
            "HONG_TU_BAO": self.hong_tu_bao,
        }

    def __repr__(self):
        return ("KetQua(ma=%r, plan=%r, co=%r, dat=%r, hong=%r, skip=%r, chua=%r, "
                "khuet=%r, phan=%r, loai=%r)"
                % (self.ma, self.ke_hoach, self.co_ket_qua, self.dat, self.hong,
                   self.bo_qua, self.chua_chay, self.khong_ket_luan, self.phan, self.loai))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# ĐỌC KHUÔN — mỗi hàm trả (KetQua hoặc None). `vi_tri` = vị trí kết thúc ứng viên trong output.
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _bam(dong):
    def _so(mau):
        m = mau.search(dong or "")
        return int(m.group(1)) if m else 0
    return _so(_RE_SKIP), _so(_RE_FAIL), _so(_RE_LOI)


def _ut_ung_vien(out):
    ung = []
    for mau in (_RE_RAN, _RE_RAN_DU_PHONG):
        for m in mau.finditer(out):
            n = int(m.group(1))
            tail = out[m.end():m.end() + 800]
            mk = _RE_KQ_UT.search(tail)
            vi_tri = (m.end() + mk.end()) if mk else m.end()
            skip = fail = err = 0
            if mk:
                skip, fail, err = _bam(mk.group(0))
            dat = max(0, n - skip - fail - err)
            ung.append(KetQua(
                ke_hoach=n, co_ket_qua=max(0, n - skip), dat=dat, hong=fail + err,
                bo_qua=skip, khong_ket_luan=0, loai="unittest",
                khuon="Ran N (unittest)" if mk else "Ran N (unittest · thiếu dòng OK/FAILED)",
                dau_vet=1 if ("ca — ĐẠT" in out or re.search(r"^OK( |$)", out, re.M)) else 0,
                vi_tri=vi_tri))
    return ung


def _pw_ung_vien(out):
    """Đọc tổng kết Playwright: lấy lần xuất hiện CUỐI của TỪNG nhãn.

    Vì sao không gom "khối dòng liền nhau": Playwright in phần CHI TIẾT ca hỏng (tên ca,
    trace, `npx playwright show-trace …`) **chen giữa** `1 failed` và `4 did not run`:

        1 failed
          [chromium] › thu_giao_dien/…spec.js:141:1 › 01 — …
        4 did not run
        75 passed (2.5m)

    Bản đầu gom theo khối nên tách mất `1 failed` ⇒ đọc 79 ca, **0 HỎNG** cho một lượt có
    1 ca hỏng thật (log thật `veh-g22-e2e-*.log` của cổng E2E). Lấy lần cuối từng nhãn khớp
    đúng khuôn bộ đọc của chính `thu_g22_e2e.py` (`doc_tong_ket`).
    """
    nhan = {}
    vi_tri = -1
    for m in _RE_PW.finditer(out):
        nhan[m.group(2)] = int(m.group(1))
        vi_tri = max(vi_tri, m.end())
    if not nhan:
        return []
    plan = sum(nhan.get(k, 0) for k in
               ("passed", "failed", "skipped", "did not run", "flaky", "interrupted"))
    chua = nhan.get("did not run", 0)
    skip = nhan.get("skipped", 0)
    khuet = nhan.get("interrupted", 0)
    dat = nhan.get("passed", 0) + nhan.get("flaky", 0)
    hong = nhan.get("failed", 0)
    return [KetQua(
        ke_hoach=plan, co_ket_qua=max(0, plan - skip - chua - khuet),
        dat=dat, hong=hong, bo_qua=skip, chua_chay=chua, khong_ket_luan=khuet,
        loai="playwright", khuon="Playwright (passed/failed/skipped/did not run/…)",
        dau_vet=1, vi_tri=vi_tri)]


def _node_ung_vien(out):
    khoi = []
    cur, cur_end = {}, -1
    for m in _RE_NODE.finditer(out):
        if cur and out[cur_end:m.start()].strip():
            khoi.append((dict(cur), cur_end))
            cur = {}
        cur[m.group(1)] = int(m.group(2))
        cur_end = m.end()
    if cur:
        khoi.append((dict(cur), cur_end))
    ung = []
    for nhan, vi_tri in khoi:
        plan = (nhan.get("pass", 0) + nhan.get("fail", 0) + nhan.get("skipped", 0)
                + nhan.get("todo", 0) + nhan.get("cancelled", 0))
        ung.append(KetQua(
            ke_hoach=plan, co_ket_qua=nhan.get("pass", 0) + nhan.get("fail", 0),
            dat=nhan.get("pass", 0), hong=nhan.get("fail", 0),
            bo_qua=nhan.get("skipped", 0) + nhan.get("todo", 0),
            chua_chay=nhan.get("cancelled", 0), loai="node",
            khuon="node --test (pass/fail/skipped/todo/cancelled)", dau_vet=1, vi_tri=vi_tri))
    return ung


def _cong_e2e(out):
    m = None
    for m in _RE_CONG_E2E.finditer(out):
        pass
    if not m:
        return None
    a, b, c, d, e = (int(x) for x in m.groups())
    return KetQua(
        ke_hoach=a + b + c + d + e, co_ket_qua=a + b, dat=a, hong=b, bo_qua=c,
        chua_chay=d, khong_ket_luan=e, loai="cong-e2e",
        khuon="số ca ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN", dau_vet=1, vi_tri=m.end())


def _tong(out):
    m = None
    for m in _RE_TONG.finditer(out):
        pass
    if not m:
        return None
    plan = int(m.group(1))
    nhan = m.group(2)
    dat = hong = khuet = skip = -1
    if m.group(3):
        dat = _lay_so(m.group(3), r"ĐẠT\s*=\s*(\d+)")
        hong = _lay_so(m.group(3), r"HỎNG\s*=\s*(\d+)")
        khuet = _lay_so(m.group(3), r"KHUYẾT\s*=\s*(\d+)")
        skip = _lay_so(m.group(3), r"BỎ QUA\s*=\s*(\d+)")
    if dat < 0 and nhan == "ĐẠT":
        dat = plan
        hong = 0
    if hong < 0 and nhan == "HỎNG":
        hong = plan - max(0, dat)
        dat = max(0, dat)
    if khuet < 0:
        khuet = 0
    if skip < 0:
        skip = 0
    co = (dat + hong) if (dat >= 0 and hong >= 0) else plan
    return KetQua(
        ke_hoach=plan, co_ket_qua=max(0, co), dat=max(0, dat), hong=max(0, hong),
        bo_qua=max(0, skip), khong_ket_luan=max(0, khuet), loai="viet-tay-tong",
        khuon="TỔNG: N ca — ĐẠT/HỎNG", dau_vet=1 if dat > 0 else 0, vi_tri=m.end())


def _lay_so(text, mau):
    m = re.search(mau, text)
    return int(m.group(1)) if m else -1


def _agg(out):
    m = None
    for m in _RE_AGG.finditer(out):
        pass
    if not m:
        return None
    dat, hong, skip, khuet, plan = (int(x) for x in m.groups())
    return KetQua(
        ke_hoach=plan, co_ket_qua=dat + hong, dat=dat, hong=hong, bo_qua=skip,
        khong_ket_luan=khuet, loai="viet-tay-agg",
        khuon="ca ĐẠT/HỎNG/BỎ QUA/KHÔNG KẾT LUẬN/TỔNG", dau_vet=1, vi_tri=m.end())


def _agg_bang(out):
    m = None
    for m in _RE_AGG_BANG.finditer(out):
        pass
    if not m:
        return None
    dat, hong, skip, khuet, plan = (int(x) for x in m.groups())
    return KetQua(
        ke_hoach=plan, co_ket_qua=dat + hong, dat=dat, hong=hong, bo_qua=skip,
        khong_ket_luan=khuet, loai="viet-tay-bang",
        khuon="ca ĐẠT=… · HỎNG=… · BỎ QUA=… · KHUYẾT=… · TỔNG=…", dau_vet=1, vi_tri=m.end())


def _dat_hong(out):
    m = None
    for m in _RE_DAT_HONG.finditer(out):
        pass
    if not m:
        return None
    dat, hong = int(m.group(1)), int(m.group(2))
    return KetQua(
        ke_hoach=dat + hong, co_ket_qua=dat + hong, dat=dat, hong=hong, loai="viet-tay-dat-hong",
        khuon="N ca — ĐẠT, M ca HỎNG", dau_vet=1, vi_tri=m.end())


def _dat(out):
    m = None
    for m in _RE_DAT.finditer(out):
        pass
    if not m:
        return None
    n = int(m.group(1))
    return KetQua(
        ke_hoach=n, co_ket_qua=n, dat=n, hong=0, loai="viet-tay-dat",
        khuon="N ca — ĐẠT", dau_vet=1, vi_tri=m.end())


def _hong(out):
    m = None
    for m in _RE_HONG.finditer(out):
        pass
    if not m:
        return None
    n = int(m.group(1))
    return KetQua(
        ke_hoach=n, co_ket_qua=n, dat=0, hong=n, loai="viet-tay-hong",
        khuon="N ca — HỎNG", dau_vet=0, vi_tri=m.end())


def _tong_don(out):
    m = None
    for m in _RE_TONG_DON.finditer(out):
        pass
    if not m:
        return None
    n = int(m.group(1))
    return KetQua(
        ke_hoach=n, co_ket_qua=n, dat=-1, hong=-1, loai="tong-don",
        khuon="TỔNG: N ca", dau_vet=0, vi_tri=m.end())


def _ket_qua(out):
    m = None
    for m in _RE_KET_QUA.finditer(out):
        pass
    if not m:
        return None
    dat, plan = int(m.group(1)), int(m.group(2))
    return KetQua(
        ke_hoach=plan, co_ket_qua=plan, dat=dat, hong=max(0, plan - dat), loai="shell-ket-qua",
        khuon="KẾT QUẢ: x/y", dau_vet=1, vi_tri=m.end())


# Thứ tự ưu tiên CHỈ dùng khi hai ứng viên kết thúc ở CÙNG vị trí. Bình thường ứng viên
# NÀO KẾT THÚC MUỘN NHẤT thắng — dòng phán quyết thật của runner nằm ở cuối output.
_UU_TIEN = {"unittest": 0, "cong-e2e": 1, "playwright": 2, "node": 3, "viet-tay-agg": 4,
            "viet-tay-bang": 5, "viet-tay-tong": 6, "viet-tay-dat-hong": 7,
            "viet-tay-dat": 8, "viet-tay-hong": 9, "tong-don": 10, "shell-ket-qua": 11}


def _chon(out):
    ds = []
    ds += _ut_ung_vien(out)
    ds += _pw_ung_vien(out)
    ds += _node_ung_vien(out)
    for ham in (_cong_e2e, _tong, _agg, _agg_bang, _dat_hong, _dat, _hong, _tong_don,
                _ket_qua):
        kq = ham(out)
        if kq is not None:
            ds.append(kq)
    if not ds:
        return None
    kq = max(ds, key=lambda k: (k.vi_tri, -_UU_TIEN.get(k.loai, 99)))
    # Dòng kết luận cuối của bộ viết tay đôi khi chỉ có MỘT con số (`32 ca — ĐẠT`) trong khi
    # dòng tổng hợp ngay TRƯỚC đó có đủ ĐẠT/HỎNG/BỎ QUA/KHUYẾT. Giữ phán quyết của dòng cuối
    # nhưng mượn các cột chi tiết CÙNG số kế hoạch — nếu không, cột "bỏ qua" sẽ mất.
    if kq.loai in ("viet-tay-dat", "viet-tay-hong", "viet-tay-dat-hong", "tong-don"):
        for rich in ds:
            if (rich.ke_hoach == kq.ke_hoach and rich.vi_tri < kq.vi_tri
                    and rich.loai in ("viet-tay-agg", "viet-tay-bang", "viet-tay-tong")):
                kq.dat, kq.hong = rich.dat, rich.hong
                kq.bo_qua, kq.khong_ket_luan = rich.bo_qua, rich.khong_ket_luan
                kq.co_ket_qua = rich.co_ket_qua
                kq.khuon = "%s + %s" % (kq.khuon, rich.khuon)
                break
    return kq


# ══════════════════════════════════════════════════════════════════════════════════════════════
# LUẬT PHÁN
# ══════════════════════════════════════════════════════════════════════════════════════════════
def dem(ma, out):
    """Đọc output của MỘT bộ thử, trả `KetQua`. Đây là bộ đếm DUY NHẤT của dự án."""
    out = out or ""
    dong_cuoi = ""
    for dong in out.splitlines():
        if dong.strip():
            dong_cuoi = dong.strip()

    kq = _chon(out)
    if kq is None:
        kq = KetQua(ma=ma, loai="khong-khop", khuon="không khớp khuôn nào",
                    dau_vet=1 if _RE_DAU_VET.search(out) else 0, vi_tri=len(out))
    kq.ma = ma
    kq.dau_vet = 1 if (_RE_DAU_VET.search(out) or kq.dau_vet) else 0

    # "Tự báo HỎNG": dòng CUỐI là phán quyết của runner. Chữ HỎNG nằm GIỮA bài là trích dẫn
    # (unittest -v in docstring) — `thu_g22_zeroca.py` từng bị gắn HỎNG oan vì đúng lỗi này.
    tu_bao = 1 if re.search(r"[0-9]+[ \t]*ca[ \t]*—[ \t]*HỎNG", dong_cuoi) else 0
    if not tu_bao and kq.hong > 0:
        tu_bao = 1
    kq.hong_tu_bao = tu_bao

    if ma == 0:
        if tu_bao:
            kq.phan, kq.ly_do_ma = HONG, "tu_bao_hong"
        elif kq.ke_hoach == 0:
            if kq.bo_qua > 0 or "skipped" in out:
                kq.phan, kq.ly_do_ma = BO_QUA, ""
            else:
                kq.phan, kq.ly_do_ma = HONG, ("khong_dau_vet" if not kq.dau_vet else "khong_ca")
        elif kq.chua_chay > 0:
            kq.phan, kq.ly_do_ma = HONG, "chua_chay"
        elif not kq.dau_vet:
            kq.phan, kq.ly_do_ma = HONG, "khong_dau_vet"
        else:
            kq.phan, kq.ly_do_ma = DAT, ""
    else:
        kq.phan, kq.ly_do_ma = HONG, "ma_thoat"
    kq.ly_do = LY_DO_MA.get(kq.ly_do_ma, "")
    return kq


def dem_tep(ma, duong):
    with open(duong, encoding="utf-8", errors="replace") as f:
        return dem(ma, f.read())


# ══════════════════════════════════════════════════════════════════════════════════════════════
# GIAO DIỆN DÒNG LỆNH
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _doc_stdin():
    du_lieu = sys.stdin.buffer.read()
    return du_lieu.decode("utf-8", "replace")


def _in_tinh_ca(kq):
    """Khoá cũ (N, KHUON, PHAN, LY_DO) + khoá mới. `N` = KE_HOACH để không phá bộ tự kiểm QA."""
    for k, v in kq.khoa().items():
        print("%s=%s" % (k, v))


def _in_shell(kq):
    """Biến shell — MỌI giá trị đều là số hoặc mã không dấu cách ⇒ `eval` an toàn."""
    print("TC_KE_HOACH=%d" % kq.ke_hoach)
    print("TC_CO_KET_QUA=%d" % kq.co_ket_qua)
    print("TC_DAT=%d" % kq.dat)
    print("TC_HONG=%d" % kq.hong)
    print("TC_BO_QUA=%d" % kq.bo_qua)
    print("TC_CHUA_CHAY=%d" % kq.chua_chay)
    print("TC_KHONG_KET_LUAN=%d" % kq.khong_ket_luan)
    print("TC_N=%d" % kq.ke_hoach)
    print("TC_KHUON_MA=%s" % kq.loai)
    print("TC_PHAN=%s" % kq.phan)
    print("TC_LY_DO_MA=%s" % (kq.ly_do_ma or "-"))
    print("TC_DAU_VET=%d" % kq.dau_vet)
    print("TC_HONG_TU_BAO=%d" % kq.hong_tu_bao)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Bộ đếm dùng chung R6 — đọc khuôn unittest / Playwright / bộ viết tay.")
    ap.add_argument("--tinh-ca", nargs=2, metavar=("MA_THOAT", "TEP_LOG"),
                    help="đọc log và in khoá `N/KHUON/PHAN/LY_DO/...`; TEP_LOG = `-` là stdin")
    ap.add_argument("--shell", metavar="MA_THOAT",
                    help="đọc stdin, in biến shell `TC_*` (dùng bởi chay_tat_ca.sh)")
    ap.add_argument("--json", action="store_true", help="in JSON thay vì KEY=VALUE")
    a = ap.parse_args(argv)

    if a.tinh_ca:
        ma_txt, tep = a.tinh_ca
        if not re.fullmatch(r"\d+", ma_txt or ""):
            print("mã thoát phải là số: %r" % ma_txt, file=sys.stderr)
            return 2
        if tep == "-":
            kq = dem(int(ma_txt), _doc_stdin())
        elif os.path.isfile(tep):
            kq = dem_tep(int(ma_txt), tep)
        else:
            print("KHÔNG có tệp log: %s" % tep, file=sys.stderr)
            return 2
        if a.json:
            print(json.dumps({"ma": kq.ma, **kq.khoa()}, ensure_ascii=False, indent=2))
        else:
            _in_tinh_ca(kq)
        return 0

    if a.shell is not None:
        if not re.fullmatch(r"\d+", a.shell or ""):
            print("mã thoát phải là số: %r" % a.shell, file=sys.stderr)
            return 2
        _in_shell(dem(int(a.shell), _doc_stdin()))
        return 0

    # MẶC ĐỊNH: tự kiểm. In `Ran N tests ... OK` để chính chay_tat_ca.sh đếm được tệp này.
    print("═══ R6 — TỰ KIỂM BỘ ĐẾM DÙNG CHUNG (không cần Chromium, không đụng CSDL thật) ═══")
    print("Bộ đếm: %s" % os.path.relpath(__file__, GOC))
    kq = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TuKiem))
    print("TỰ KIỂM: %d ca · hỏng %d · lỗi %d · bỏ qua %d"
          % (kq.testsRun, len(kq.failures), len(kq.errors), len(kq.skipped)))
    return MA_DAT if kq.wasSuccessful() else MA_HONG


# ══════════════════════════════════════════════════════════════════════════════════════════════
# TỰ KIỂM — mỗi điều kiện có vế CHÍNH và ĐỐI CHỨNG ÂM
# ══════════════════════════════════════════════════════════════════════════════════════════════
def an(x):
    """Vô hiệu hoá khuôn trong output ĐEM IN, để tệp tự kiểm không tự đầu độc phép đếm."""
    return (x.replace(" ca — ĐẠT", " ca ~ ĐẠT")
             .replace(" ca — HỎNG", " ca ~ HỎNG")
             .replace("Ran ", "Ran· ")
             .replace("TỔNG: ", "TỔNG· ")
             .replace("số ca ", "số·ca "))


def _do_mau(nguon, ten):
    """Đo CÙNG một output bằng hai đường: hàm trong tệp này và `chay_tat_ca.sh --tinh-ca`."""
    d = tempfile.mkdtemp(prefix="veh-r6-gia-")
    try:
        p = os.path.join(d, ten + ".py")
        with open(p, "w", encoding="utf-8") as f:
            f.write(nguon)
        tt = subprocess.run([sys.executable, p], capture_output=True, text=True,
                            timeout=60, cwd=d)
        out = (tt.stdout or "") + (tt.stderr or "")
        truc_tiep = dem(tt.returncode, out)
        tep = os.path.join(d, ten + ".out")
        with open(tep, "w", encoding="utf-8") as f:
            f.write(out)
        tt2 = subprocess.run(["sh", CHAY, "--tinh-ca", str(tt.returncode), tep],
                             capture_output=True, text=True, timeout=60, cwd=GOC)
        if tt2.returncode != 0:
            raise AssertionError("`--tinh-ca` thoát %d: %s"
                                 % (tt2.returncode, (tt2.stderr or tt2.stdout)[-400:]))
        shell = {}
        for dong in tt2.stdout.splitlines():
            if "=" in dong:
                k, v = dong.split("=", 1)
                shell[k] = v
        shell["N"] = int(shell["N"])
        return truc_tiep, shell, tt.returncode, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


class TuKiem(unittest.TestCase):
    """Mỗi ca đo MỘT tính chất. Mẫu giả nằm trong thư mục tạm, không đụng bộ thử thật."""

    def _kiem(self, nguon, ten, plan=None, co=None, phan=None, dat=None, hong=None,
              skip=None, chua=None, khuet=None, ly_do_ma=None):
        kq, shell, ma_gia, out = _do_mau(nguon, ten)
        # Đường 1: hàm thật trong tệp này.
        if plan is not None:
            self.assertEqual(kq.ke_hoach, plan, an(out))
        if co is not None:
            self.assertEqual(kq.co_ket_qua, co, an(out))
        if phan is not None:
            self.assertEqual(kq.phan, phan, an(out))
        if dat is not None:
            self.assertEqual(kq.dat, dat, an(out))
        if hong is not None:
            self.assertEqual(kq.hong, hong, an(out))
        if skip is not None:
            self.assertEqual(kq.bo_qua, skip, an(out))
        if chua is not None:
            self.assertEqual(kq.chua_chay, chua, an(out))
        if khuet is not None:
            self.assertEqual(kq.khong_ket_luan, khuet, an(out))
        if ly_do_ma is not None:
            self.assertEqual(kq.ly_do_ma, ly_do_ma, an(out))
        # Đường 2: ĐÚNG đường mà chay_tat_ca.sh dùng. Hai đường phải trùng — nếu ai chép lại
        # regex vào shell thì vế này lệch và bộ tự kiểm đỏ.
        self.assertEqual(shell["N"], kq.ke_hoach, an(out))
        self.assertEqual(shell["PHAN"], kq.phan, an(out))
        self.assertEqual(int(shell["CO_KET_QUA"]), kq.co_ket_qua, an(out))
        self.assertEqual(int(shell["CHUA_CHAY"]), kq.chua_chay, an(out))
        self.assertEqual(int(shell["BO_QUA"]), kq.bo_qua, an(out))
        return kq, shell

    # ── (a) bộ thử in `N ca` đúng ⇒ đếm đúng N ───────────────────────────────────────────────
    def test_a1_in_17_ca_thi_dem_17(self):
        self._kiem('import sys\nprint("17 ca — ĐẠT")\nsys.exit(0)\n',
                   "a1_17ca", plan=17, co=17, phan=DAT, dat=17)

    def test_a2_doi_chung_am_4ca_khong_phai_hang_so(self):
        """ĐỐI CHỨNG ÂM của (a): cùng khuôn, N khác ⇒ bộ đếm không được trả hằng số 17."""
        self._kiem('import sys\nprint("4 ca — ĐẠT")\nsys.exit(0)\n',
                   "a2_4ca", plan=4, co=4, phan=DAT, dat=4)

    # ── (b) khuôn lạ ⇒ vẫn đếm đúng, KHÔNG 0 ────────────────────────────────────────────────
    def test_b1_khuon_TONG_32ca_HONG_van_dem_32(self):
        self._kiem(
            'import sys\n'
            'print("  ca ĐẠT: 27 · HỎNG: 3 · BỎ QUA: 0 · KHÔNG KẾT LUẬN: 2 · TỔNG: 32")\n'
            'print("  TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=3 · KHUYẾT=2)")\n'
            'sys.exit(1)\n',
            "b1_TONG_32", plan=32, co=30, phan=HONG, dat=27, hong=3, khuet=2)

    def test_b2_doi_chung_am_TONG_0ca_khong_bia_so(self):
        """ĐỐI CHỨNG ÂM của (b): cùng khuôn nhưng 0 ca THẬT ⇒ không được bịa 32."""
        self._kiem(
            'import sys\nprint("TỔNG: 0 ca — HỎNG (ĐẠT=0 · HỎNG=0 · KHUYẾT=0)")\n'
            'sys.exit(1)\n',
            "b2_TONG_0", plan=0, co=0, phan=HONG)

    def test_b3_dong_ket_luan_HAI_con_so_khong_bi_dem_thieu(self):
        """Lỗi đọc THẬT: `27 ca — ĐẠT, 5 ca HỎNG` là 32 ca. Bộ đếm cũ chỉ đọc 27."""
        kq, shell = self._kiem(
            'import sys\nprint("  KẾT LUẬN: có ca HỎNG")\n'
            'print("  27 ca — ĐẠT, 5 ca HỎNG")\nsys.exit(1)\n',
            "b3_dat_hong", plan=32, co=32, phan=HONG, dat=27, hong=5)
        self.assertNotEqual(kq.ke_hoach, 27, "đọc thiếu vế HỎNG của dòng kết luận")

    def test_b4_doi_chung_am_32ca_dat(self):
        """ĐỐI CHỨNG ÂM của (b3): dòng một con số vẫn phải đọc đúng 32, không cộng bừa."""
        self._kiem('import sys\nprint("32 ca — ĐẠT")\nsys.exit(0)\n',
                   "b4_32dat", plan=32, co=32, phan=DAT, dat=32, hong=0)

    def test_b5_khuon_BANG_that_doc_dung_38_khong_doc_so_bo_con(self):
        """LỖI ĐỌC THẬT của `thu_g21_gioihan.py`: dòng cuối là `ca ĐẠT=38 … TỔNG=38`, nhưng
        phần bằng chứng phía trên có câu `['  22 ca — ĐẠT']` (số của bộ CON). Bộ đếm cũ bắt
        câu 22 và bỏ dòng 38. Đây là miscount THẬT, không phải mẫu giả tưởng."""
        kq, _ = self._kiem(
            'import sys\n'
            'print("        $ python3 app/thu/thu_g19_gioihan.py → dòng cuối: '
            "['  22 ca — ĐẠT']\")\n"
            'print("  ca ĐẠT=38 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=38")\n'
            'print("  thời gian: 65.1 giây · HEAD: (không đặt)")\n'
            'sys.exit(0)\n',
            "b5_bang_38", plan=38, co=38, phan=DAT, dat=38, hong=0)
        self.assertNotEqual(kq.ke_hoach, 22, "đọc số của bộ CON thay vì dòng tổng kết bộ MẸ")

    def test_b6_doi_chung_am_khuon_BANG_0ca(self):
        """ĐỐI CHỨNG ÂM của (b5): cùng khuôn, TỔNG=0 thật ⇒ không được bịa 38."""
        self._kiem(
            'import sys\nprint("ca ĐẠT=0 · HỎNG=0 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=0")\n'
            'sys.exit(0)\n', "b6_bang_0", plan=0, co=0, phan=HONG)

    # ── (c) 0 ca thật ⇒ KHÔNG được coi là ĐẠT ───────────────────────────────────────────────
    def test_c1_khong_ca_nao_van_tu_in_DAT_la_HONG(self):
        self._kiem('import sys\nprint("0 ca — ĐẠT")\nsys.exit(0)\n',
                   "c1_0ca_dat", plan=0, phan=HONG)

    def test_c2_ran_0_tests_OK_la_HONG(self):
        self._kiem('import sys\nprint("Ran 0 tests in 0.00s")\nprint("OK")\nsys.exit(0)\n',
                   "c2_ran0", plan=0, phan=HONG)

    def test_c3_doi_chung_am_bo_qua_co_chu_dich(self):
        """ĐỐI CHỨNG ÂM của (c): bỏ qua CÓ CHỦ ĐÍCH là phán quyết thứ ba, không gộp HỎNG."""
        self._kiem(
            'import sys\nprint("Ran 0 tests in 0.00s")\n'
            'print("BỎ QUA: chưa cài PostgreSQL — Bật bằng: VIP_THU_POSTGRES=1")\n'
            'print("OK (skipped=1)")\nsys.exit(0)\n',
            "c3_boqua", plan=0, phan=BO_QUA, skip=1)

    def test_c4_doi_chung_am_mot_ca_that_van_DAT(self):
        """ĐỐI CHỨNG ÂM của (c): 1 ca thật ≠ 0 ca ⇒ DAT, để (c) không biến thành 'luôn HỎNG'."""
        self._kiem('import sys\nprint("1 ca — ĐẠT")\nsys.exit(0)\n',
                   "c4_1ca", plan=1, phan=DAT, dat=1)

    # ── (d) thoát 0 nhưng in HỎNG ⇒ PHẢI là ĐỎ ──────────────────────────────────────────────
    def test_d1_thoat_0_van_in_HONG_la_HONG(self):
        self._kiem(
            'import sys\nprint("Ran 5 tests in 0.01s")\nprint("OK")\n'
            'print("TỔNG: 5 ca — HỎNG (ĐẠT=4 · HỎNG=1 · KHUYẾT=0)")\nsys.exit(0)\n',
            "d1_0_hong", plan=5, phan=HONG, hong=1)

    def test_d2_doi_chung_am_thoat_0_in_DAT(self):
        """ĐỐI CHỨNG ÂM của (d): cùng hình dạng nhưng ĐẠT thật ⇒ không được đỏ oan."""
        self._kiem(
            'import sys\nprint("Ran 5 tests in 0.01s")\nprint("OK")\n'
            'print("TỔNG: 5 ca — ĐẠT")\nsys.exit(0)\n',
            "d2_0_dat", plan=5, phan=DAT)

    def test_d3_doi_chung_am_chu_HONG_trong_trich_dan(self):
        """ĐỐI CHỨNG ÂM thứ hai của (d): HỎNG nằm trong docstring giữa bài ⇒ không đỏ oan."""
        self._kiem(
            'import sys\n'
            'print("test_04 (__main__.TuKiem)")\n'
            'print("Đúng lỗi: in `TỔNG: 32 ca — HỎNG` mà bộ đếm đọc 0. ... ok")\n'
            'print("Ran 1 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n',
            "d3_trich_dan", plan=1, phan=DAT)

    # ── (e) thoát 0, KHÔNG dấu vết chạy ca nào ⇒ PHẢI là ĐỎ ─────────────────────────────────
    def test_e1_thoat_0_khong_dau_vet_la_HONG(self):
        self._kiem('import sys\nsys.exit(0)\n', "e1_im_lang", plan=0, phan=HONG,
                   ly_do_ma="khong_dau_vet")

    def test_e2_doi_chung_am_thoat_0_co_dau_vet(self):
        """ĐỐI CHỨNG ÂM của (e): thoát 0 + có dấu vết 3 ca ⇒ DAT."""
        self._kiem('import sys\nprint("Ran 3 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n',
                   "e2_3ca", plan=3, phan=DAT)

    # ── (f) Playwright: "did not run" KHÔNG được cộng vào ca có kết quả ───────────────────────
    def test_f1_playwright_tach_53_chua_chay(self):
        self._kiem(
            'import sys\n'
            'print("  2 passed (1.2s)")\nprint("  25 failed")\nprint("  0 skipped")\n'
            'print("  53 did not run")\nprint("  0 flaky")\nsys.exit(1)\n',
            "f1_pw", plan=80, co=27, phan=HONG, dat=2, hong=25, chua=53)
        # Chốt sống: mẫu số cũ (80) KHÔNG được gọi là ca có kết quả.
        self.assertNotEqual(80, 27)

    def test_f2_doi_chung_am_playwright_chay_het(self):
        """ĐỐI CHỨNG ÂM của (f): chạy hết 80 ⇒ có kết quả 80, không bịa 'did not run'."""
        self._kiem('import sys\nprint("  80 passed (9.9s)")\nsys.exit(0)\n',
                   "f2_pw", plan=80, co=80, phan=DAT, dat=80, chua=0)

    def test_f3_playwright_ca_hong_Chen_giua_khong_bi_mat(self):
        """Log THẬT: phần chi tiết ca hỏng nằm GIỮA `1 failed` và `4 did not run`.
        Bản gom-khối đọc 79 ca / 0 HỎNG; đúng là 80 ca / 1 HỎNG / 4 chưa chạy."""
        self._kiem(
            'import sys\n'
            'print("  1 failed")\n'
            'print("    [chromium] › thu_giao_dien/10_trang_tinh_du_lieu.spec.js:141:1 › 01 — …")\n'
            'print("4 did not run")\n'
            'print("75 passed (2.5m)")\n'
            'sys.exit(1)\n',
            "f3_pw_chen", plan=80, co=76, phan=HONG, dat=75, hong=1, chua=4)

    # ── (g) unittest: `Ran N` gồm skipped ⇒ phải trừ ra khỏi ca có kết quả ───────────────────
    def test_g1_unittest_skip_khong_vao_co_ket_qua(self):
        self._kiem(
            'import sys\nprint("Ran 35 tests in 0.10s")\nprint("OK (skipped=1)")\nsys.exit(0)\n',
            "g1_skip", plan=35, co=34, phan=DAT, skip=1)

    def test_g2_doi_chung_am_unittest_khong_skip(self):
        """ĐỐI CHỨNG ÂM của (g): không có skipped ⇒ 35 ca có kết quả, không trừ oan."""
        self._kiem(
            'import sys\nprint("Ran 35 tests in 0.10s")\nprint("OK")\nsys.exit(0)\n',
            "g2_noskip", plan=35, co=35, phan=DAT, skip=0)

    # ── (h) CHỈ MỘT bộ đếm: chay_tat_ca.sh không được giữ bản sao regex ────────────────────
    def test_h1_chay_tat_ca_dung_bo_dem_chung(self):
        with open(CHAY, encoding="utf-8") as f:
            than = f.read()
        self.assertIn("thu_r6_demca.py", than,
                      "chay_tat_ca.sh không gọi bộ đếm dùng chung")
        self.assertNotRegex(than, r"grep[^\n]*Ran \[0-9\]",
                            "chay_tat_ca.sh còn giữ regex `Ran [0-9]` — bản sao thứ hai")
        self.assertNotRegex(than, r"grep[^\n]*ca — ĐẠT",
                            "chay_tat_ca.sh còn giữ regex `N ca — ĐẠT` — bản sao thứ hai")

    def test_h2_doi_chung_am_bo_dem_sai_thi_bi_bat(self):
        """ĐỐI CHỨNG ÂM của (h): chèn lại regex cũ vào MỘT bản sao ⇒ phép canh phải ĐỎ."""
        with open(CHAY, encoding="utf-8") as f:
            than = f.read()
        gia = than + '\n# TIÊM: regex cũ\n_dem_cu=$(printf x | grep -oE "Ran [0-9]+")\n'

        def canh(noi_dung):
            return ("thu_r6_demca.py" in noi_dung
                    and not re.search(r"grep[^\n]*Ran \[0-9\]", noi_dung)
                    and not re.search(r"grep[^\n]*ca — ĐẠT", noi_dung))
        self.assertTrue(canh(than), "bản thật phải đạt phép canh")
        self.assertFalse(canh(gia), "phép canh KHÔNG bắt được regex cũ ⇒ phép đo rỗng")

    # ── (j) node --test: dòng `cancelled` nằm giữa không được cắt khối tổng kết ───────────────
    def test_j1_node_doc_dung_khoi_co_cancelled(self):
        self._kiem(
            'import sys\n'
            'print("ℹ tests 3")\nprint("ℹ suites 1")\nprint("ℹ pass 2")\nprint("ℹ fail 1")\n'
            'print("ℹ cancelled 0")\nprint("ℹ skipped 0")\nprint("ℹ todo 0")\n'
            'print("ℹ duration_ms 12.3")\nsys.exit(1)\n',
            "j1_node", plan=3, co=3, phan=HONG, dat=2, hong=1)

    def test_j2_doi_chung_am_node_chay_het(self):
        """ĐỐI CHỨNG ÂM của (j): 56/56 pass ⇒ DAT, không bị `cancelled 0` cắt khối."""
        self._kiem(
            'import sys\n'
            'print("ℹ tests 56")\nprint("ℹ pass 56")\nprint("ℹ fail 0")\n'
            'print("ℹ cancelled 0")\nprint("ℹ skipped 0")\nprint("ℹ todo 0")\n'
            'sys.exit(0)\n', "j2_node", plan=56, co=56, phan=DAT, dat=56)

    # ── (i) bộ đếm không được 'luôn 0' hay 'luôn HỎNG' ──────────────────────────────────────
    def test_i1_khong_phai_hang_so(self):
        """Ba mẫu khác nhau cho ba con số khác nhau — chốt chống bộ đếm trả hằng số."""
        so = []
        for ten, nguon in (
                ("i1_a", 'import sys\nprint("7 ca — ĐẠT")\nsys.exit(0)\n'),
                ("i1_b", 'import sys\nprint("Ran 12 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n'),
                ("i1_c", 'import sys\nprint("Ran 0 tests in 0.00s")\n'
                         'print("OK (skipped=2)")\nsys.exit(0)\n')):
            kq, _ = self._kiem(nguon, ten)
            so.append(kq.ke_hoach)
        self.assertEqual(so, [7, 12, 0])
        self.assertNotEqual(len(set(so)), 1)


if __name__ == "__main__":
    sys.exit(main())
