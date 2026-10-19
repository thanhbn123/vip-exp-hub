#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B5 — BỘ ĐO 10 CỔNG CHO TÍCH HỢP BEST EXPRESS (LOCAL · MOCK · KHÔNG PHẢI REAL PASS).

VAI: NGƯỜI KIỂM. Tệp này KHÔNG sửa mã sản phẩm, KHÔNG gọi API hãng, KHÔNG dùng credentials thật,
KHÔNG ghi ra ngoài thư mục tạm. Mọi phép đo chạy trên cây hiện tại + một CSDL SQLite TẠM.

VÌ SAO CÓ TỆP NÀY
-----------------
Đề bài B5 đòi 10 cổng (BEST-01 … BEST-10), mỗi cổng một phán quyết PASS / FAIL / BLOCKED /
NOT TESTED kèm bằng chứng: LỆNH THẬT · MÃ THOÁT THẬT · SỐ CA · SỐ SKIP · BLOCKED. Tệp này là
chỗ DUY NHẤT sinh ra bảng đó, để báo cáo không phải là lời khai viết tay.

BA LUẬT BẰNG CHỨNG (lặp lại nguyên văn từ đề bài, và đây là chỗ chúng được thi hành):
  · MỌI khẳng định đi kèm lệnh thật + mã thoát thật, đọc NGAY sau lệnh.
  · MOCK PASS và REAL PASS là HAI KẾT QUẢ KHÁC NHAU. Bộ đo này chỉ đo LOCAL/MOCK.
  · Mọi ca phủ định phải có ĐỐI CHỨNG DƯƠNG — tức phép đo PHẢI chứng minh nó NHÌN THẤY lỗi
    khi lỗi được tiêm vào. Các đối chứng nằm ngay trong từng cổng, không phải lời hứa.

GIỚI HẠN PHẠM VI — ĐỌC TRƯỚC KHI TIN KẾT QUẢ
---------------------------------------------
  · Tại nền `cb23312` KHÔNG có mã tích hợp BEST Express (không `adapter_best.py`, 0 hit
    `12491`, 0 đăng ký `ma_hang="best"`). Vì thế các cổng phụ thuộc mã BEST là BLOCKED:
    chúng KHÔNG phải PASS, và cũng KHÔNG phải lỗi sản phẩm.
  · Tài liệu API BEST là Google Docs. Bộ đo KHÔNG đọc được tài liệu đó, nên chỉ dùng ĐẶC TẢ
    ĐÃ XÁC NHẬN trong đề bài (8 endpoint · 21 trường · ServiceId=12491 · District=" " ·
    giới hạn 10/50 · 11 bước webhook · 24 mã · 605→606 · 3 loại phí · PDF theo hostname).
    Mọi mục như vậy mang cờ `da_kiem_chung = False` và được in là CHƯA KIỂM CHỨNG.
  · Không có credentials thật, không có endpoint HTTPS đã xác minh ⇒ BEST-09 BLOCKED,
    BEST-10 PENDING. KHÔNG có đường nào để bộ đo này ghi PASS cho hai cổng đó.

LỆNH CHẠY
---------
    python3 app/thu/thu_best_qa.py                 # in bảng 10 cổng + chạy 10 ca (unittest)
    python3 app/thu/thu_best_qa.py --json          # cùng dữ liệu, dạng máy đọc
    python3 app/thu/thu_best_qa.py --giao-dien     # + chạy THẬT `sh thu_giao_dien/chay.sh`
    python3 app/thu/thu_best_qa.py --nghiem-thu    # thoát 1 trừ khi CẢ 10 cổng PASS

MÃ THOÁT
--------
    0 = bộ đo chạy xong, không cổng nào FAIL (BLOCKED/PENDING được phép và ĐƯỢC IN RÕ)
    1 = có cổng FAIL, hoặc cổng PASS nhưng kèm lỗi tự kiểm
    2 = không dựng được nền đo (CSDL tạm / git) — số đo KHÔNG đáng tin
"""
import argparse
import atexit
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

GOC_TEP = os.path.abspath(__file__)
GOC_THU = os.path.dirname(GOC_TEP)
GOC_APP = os.path.dirname(GOC_THU)
GOC_CAY = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

# ── NỀN ĐO: thư mục dữ liệu TẠM, đặt TRƯỚC khi import cau_hinh ────────────────────────────────
# `cau_hinh` từ chối thư mục dữ liệu mặc định (G22 fail-closed). Bộ đo tự dựng nền riêng và
# tự khai kho kiểm thử; không bao giờ chạm `app/du-lieu/` hay CSDL thật.
_TAM = tempfile.mkdtemp(prefix="veh-b5-best-qa-")
os.environ["VIP_HUB_DATA"] = _TAM
os.environ.pop("VIP_HUB_RESET_TOKEN", None)


def _don_tam():
    try:
        import csdl
        csdl.dong()
    except Exception:
        pass
    shutil.rmtree(_TAM, ignore_errors=True)


atexit.register(_don_tam)

import adapter          # noqa: E402
import adapter_jt       # noqa: E402,F401
import adapter_vtp      # noqa: E402,F401
import bao_mat          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import don_hang         # noqa: E402
import http_jt          # noqa: E402
import khoi_tao         # noqa: E402
import loi_hang         # noqa: E402
import migrate          # noqa: E402
import quyen            # noqa: E402
import tai_chinh        # noqa: E402
import transport        # noqa: E402
import trang_thai_hang  # noqa: E402
import webhook          # noqa: E402

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. ĐẶC TẢ ĐÃ XÁC NHẬN — nguồn DUY NHẤT là đề bài B5, KHÔNG phải Google Docs
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Mỗi mục mang `da_kiem_chung` + `nguon`. Tài liệu Google Docs CHƯA đọc được trong môi trường
# này, nên mọi mục ở đây là CHƯA KIỂM CHỨNG với tài liệu hãng — đúng chỉ thị "KHÔNG đoán".
NGUON_DE_BAI = "đề bài B5 (dispatch task_59cadfd43f8e) — KHÔNG phải tài liệu Google Docs"
DAC_TA_XAC_NHAN = {
    "so_endpoint": 8,
    "so_truong": 21,
    "service_id": 12491,
    "district": " ",
    "gioi_han": (10, 50),
    "so_buoc_webhook": 11,
    "so_ma_trang_thai": 24,
    "ma_chuyen": (605, 606),
    "loai_phi": ("Estimated", "Actual", "Contract"),
    "pdf_hostname_allowlist": True,
    "muc": {
        "endpoint": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "truong": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "service_id": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "district": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "gioi_han": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "webhook": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "ma_trang_thai": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "phi": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
        "pdf_hostname": {"da_kiem_chung": False, "nguon": NGUON_DE_BAI},
    },
}

# 6 điều cấm của đề bài → 6 ca + đối chứng dương (BEST-07). Cách gộp được ghi rõ để người đọc
# đối chiếu lại với danh sách "BẮT BUỘC TUYỆT ĐỐI" trong đề bài, không phải một danh sách tự chế.
SAU_DIEU_CAM = [
    ("C1", "Local-only: không push/deploy/production, không gọi API BEST, không credentials thật"),
    ("C2", "Không xoá dữ liệu / reset DB / phá adapter hiện có (adapter.py · adapter_jt.py · adapter_vtp.py)"),
    ("C3", "Không đổi kiến trúc multi-tenant; mọi truy vấn theo tenant_id; không xác định tenant ⇒ DENY"),
    ("C4", "Không đoán endpoint/schema; tài liệu chưa đọc được ⇒ chỉ dùng đặc tả đã xác nhận + CHƯA KIỂM CHỨNG"),
    ("C5", "Không ghi secret/token vào log/audit/response; không trả token ra API công khai"),
    ("C6", "Không hạ TLS / tắt xác minh chứng chỉ / dùng HTTP cho dữ liệu thật"),
]

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. TIỆN ÍCH ĐO — git, tệp, nền CSDL tạm
# ══════════════════════════════════════════════════════════════════════════════════════════════
PHAM_VI_NEN = "LOCAL · MOCK · KHÔNG PHẢI REAL PASS"
NEN_HEAD = "cb23312dc702a6a1bf51e9cb53c7397770cd9637"
NEN_HEAD_NGAN = NEN_HEAD[:12]
GIT_CONFIG_MOI = ("GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")
_VUNG_THU_TAI_LIEU = ("docs/", "app/thu/", "thu_frontend/", "thu_giao_dien/", "gateway/thu/")


def _moi_truong_git():
    """Gỡ gia đình `GIT_CONFIG_*` DỊ DẠNG (N-G18-00) — nếu không mọi lệnh git thoát 128.

    Đây là chuẩn hoá để ĐO ĐƯỢC; lỗi git vì lý do THẬT sau đó vẫn phải nổi lên (xem `_git`).
    """
    env = dict(os.environ)
    raw = env.get("GIT_CONFIG_COUNT")
    if raw is not None:
        try:
            n = int(raw)
        except ValueError:
            n = None
        thieu = n is None
        if n is not None:
            for i in range(n):
                if not (env.get("GIT_CONFIG_KEY_%d" % i) or "").strip():
                    thieu = True
        if thieu:
            for k in list(env):
                if k.startswith(GIT_CONFIG_MOI):
                    env.pop(k, None)
    return env


def _git(*args, giay=60):
    """Chạy git THẬT, trả (mã_thoát, stdout, stderr). Không nuốt lỗi."""
    try:
        r = subprocess.run(["git"] + list(args), cwd=GOC_CAY, env=_moi_truong_git(),
                           capture_output=True, text=True, timeout=giay)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 127, "", "%s: %s" % (type(e).__name__, e)


def _doc(duong):
    with open(duong, encoding="utf-8", errors="replace") as f:
        return f.read()


def _bam_noi_dung(duong):
    with open(duong, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _chay(tham_so, giay=600, env=None):
    """Chạy một lệnh THẬT trong cây repo; trả (mã_thoát, stdout+stderr)."""
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        r = subprocess.run(tham_so, cwd=GOC_CAY, env=e, capture_output=True, text=True,
                           timeout=giay)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as ex:
        ra = ex.stdout or ""
        if isinstance(ra, bytes):
            ra = ra.decode("utf-8", "replace")
        return 124, ra + "\n[QUÁ HẠN %ss]" % giay


_DA_DUNG_NEN = {"xong": False, "loi": ""}


def _dung_nen():
    """Dựng CSDL SQLite TẠM + dữ liệu demo. Chỉ một lần. Không chạm dữ liệu thật."""
    if _DA_DUNG_NEN["xong"]:
        return
    if _DA_DUNG_NEN["loi"]:
        raise RuntimeError(_DA_DUNG_NEN["loi"])
    try:
        cau_hinh.khai_kho_kiem_thu()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            migrate.chay(im_lang=True)
            csdl.mo()
            quyen.seed()
            khoi_tao.seed_providers()
            khoi_tao.chay()
        _DA_DUNG_NEN["xong"] = True
    except Exception as e:
        _DA_DUNG_NEN["loi"] = "không dựng được nền đo: %s: %s" % (type(e).__name__, e)
        raise


def _dem(sql, tham_so=()):
    r = csdl.mot(sql, tham_so)
    if r is None:
        return 0
    return int(list(dict(r).values())[0])


def _van_tay():
    """Đọc vân tay bằng ĐÚNG hiện thực chuẩn của dự án (`thu_g21_chotcay.py --van-tay`)."""
    ma, ra = _chay([sys.executable, os.path.join(GOC_CAY, "app/thu/thu_g21_chotcay.py"),
                    "--van-tay"], giay=120)
    for dong in ra.splitlines():
        dong = dong.strip()
        if dong.startswith("{"):
            try:
                vt = json.loads(dong)
                vt["ma_thoát"] = ma
                return vt
            except ValueError:
                pass
    return {"loi": "không đọc được vân tay (mã %s): %s" % (ma, ra[:300])}


def _best_trong_cay():
    """Quét mã SẢN PHẨM (app/gateway/pages, trừ app/thu) tìm dấu vết tích hợp BEST.

    Trả bản ghi đếm được + danh sách tệp khớp. `mock/carriers.json` cố ý KHÔNG tính: đó là
    dữ liệu demo của hub, không phải mã tích hợp hãng.
    """
    mau = {
        "service_id_12491": re.compile(r"12491"),
        "dang_ky_best": re.compile(r"ma_hang\s*=\s*[\"']best[\"']", re.I),
        "host_best": re.compile(r"bestexpress|best-express|api\.best", re.I),
        "adapter_best": re.compile(r"adapter_best|AdapterBEST", re.I),
        # Nhãn demo KHÔNG phải tích hợp, nhưng phải đếm được: nếu bộ quét không thấy cả nhãn
        # "BEST Express" đang có trong `pages/*` thì "0 hit" ở các mục khác là mù, không phải vắng.
        "nhan_demo": re.compile(r"BEST Express", re.I),
    }
    ket_qua = {k: [] for k in mau}
    for thu_muc in ("app", "gateway", "pages"):
        goc = os.path.join(GOC_CAY, thu_muc)
        for dirpath, dirnames, filenames in os.walk(goc):
            dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "du-lieu", "thu")]
            for ten in filenames:
                if not ten.endswith((".py", ".js", ".mjs", ".html", ".json")):
                    continue
                duong = os.path.join(dirpath, ten)
                try:
                    noi_dung = _doc(duong)
                except OSError:
                    continue
                for k, rx in mau.items():
                    if rx.search(noi_dung):
                        ket_qua[k].append(os.path.relpath(duong, GOC_CAY))
    return {
        "co_adapter_best": os.path.exists(os.path.join(GOC_APP, "adapter_best.py")),
        "co_dang_ky_best": bool(ket_qua["dang_ky_best"]),
        "hit": {k: sorted(set(v)) for k, v in ket_qua.items()},
        "tong_hit": sum(len(set(v)) for v in ket_qua.values()),
    }


def _kiem_dac_ta(dac_ta=None):
    """Tự kiểm đặc tả: đúng số/đúng chữ, và KHÔNG mục nào được 'xác nhận' mà thiếu bằng chứng."""
    d = DAC_TA_XAC_NHAN if dac_ta is None else dac_ta
    loi = []
    if d["so_endpoint"] != 8:
        loi.append("so_endpoint=%r (đề bài: 8)" % (d["so_endpoint"],))
    if d["so_truong"] != 21:
        loi.append("so_truong=%r (đề bài: 21)" % (d["so_truong"],))
    if str(d["service_id"]) != "12491":
        loi.append("service_id=%r (đề bài: 12491)" % (d["service_id"],))
    if d["district"] != " ":
        loi.append("district=%r (đề bài: đúng MỘT dấu cách)" % (d["district"],))
    if tuple(d["gioi_han"]) != (10, 50):
        loi.append("gioi_han=%r (đề bài: 10/50)" % (d["gioi_han"],))
    if d["so_buoc_webhook"] != 11:
        loi.append("so_buoc_webhook=%r (đề bài: 11)" % (d["so_buoc_webhook"],))
    if d["so_ma_trang_thai"] != 24:
        loi.append("so_ma_trang_thai=%r (đề bài: 24)" % (d["so_ma_trang_thai"],))
    if tuple(d["ma_chuyen"]) != (605, 606):
        loi.append("ma_chuyen=%r (đề bài: 605→606)" % (d["ma_chuyen"],))
    for ten, muc in d["muc"].items():
        if muc.get("da_kiem_chung") and not str(muc.get("bang_chung") or "").strip():
            loi.append("mục %s khai ĐÃ KIỂM CHỨNG nhưng không có bằng chứng" % ten)
    return loi


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. MƯỜI CỔNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
class KetQua:
    def __init__(self, ma, ten, ket_qua, bang_chung=None, ly_do="", so_ca=0, so_skip=0):
        self.ma = ma
        self.ten = ten
        self.ket_qua = ket_qua
        self.bang_chung = list(bang_chung or [])
        self.ly_do = ly_do
        self.so_ca = so_ca
        self.so_skip = so_skip

    def dong(self):
        return {"ma": self.ma, "ten": self.ten, "ket_qua": self.ket_qua,
                "bang_chung": self.bang_chung, "ly_do": self.ly_do,
                "so_ca": self.so_ca, "so_skip": self.so_skip}

    def chuoi_bang_chung(self):
        return self.bang_chung[0] if self.bang_chung else "(không)"


def _gate_01():
    """BEST-01 — Repository Baseline."""
    bc = []
    ma_nhanh, nhanh, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    ma_head, head, _ = _git("rev-parse", "HEAD")
    ma_st, status, _ = _git("status", "--porcelain", "-uall")
    ma_df, diff, _ = _git("diff", "HEAD", "--name-only")
    ma_ls, ls, _ = _git("ls-files")
    so_tep = len([x for x in ls.splitlines() if x.strip()])
    so_bo = 0
    for goc_con in ("app/thu", "gateway/thu"):
        g = os.path.join(GOC_CAY, goc_con)
        if os.path.isdir(g):
            so_bo += len([f for f in os.listdir(g)
                          if f.startswith("thu_") and f.endswith(".py")
                          and f not in ("thu_e2e.py", "thu_best_qa.py")])
    so_bo_b5 = 1 if os.path.exists(GOC_TEP) else 0
    schema = "?"
    m = re.search(r"^PHIEN_BAN_SCHEMA\s*=\s*(\d+)", _doc(os.path.join(GOC_APP, "csdl.py")), re.M)
    if m:
        schema = m.group(1)
    dong_status = [d for d in status.splitlines() if d.strip()]
    thay_doi = [d for d in dong_status if not d.startswith("??")]
    moi = [d[3:].strip() for d in dong_status if d.startswith("??")]
    moi_ngoai_vung = [p for p in moi
                      if not any(p.startswith(v) for v in _VUNG_THU_TAI_LIEU)]
    vt = _van_tay()

    # ĐỐI CHỨNG DƯƠNG: trên một repo TẠM, sửa một tệp đã commit rồi hỏi lại `git status`.
    # Nếu phép dò không thấy "bẩn" ở đó thì nó cũng không đáng tin ở cây thật.
    doi_chung = False
    try:
        g = os.path.join(_TAM, "git-doi-chung")
        os.makedirs(g, exist_ok=True)

        def _g(*a):
            return subprocess.run(["git"] + list(a), cwd=g, env=_moi_truong_git(),
                                  capture_output=True, text=True, timeout=30)

        _g("init", "-q")
        with open(os.path.join(g, "a.txt"), "w", encoding="utf-8") as f:
            f.write("1")
        _g("add", "a.txt")
        _g("-c", "user.name=B5", "-c", "user.email=b5@local", "commit", "-qm", "nen")
        with open(os.path.join(g, "a.txt"), "w", encoding="utf-8") as f:
            f.write("2")
        doi_chung = bool(_g("status", "--porcelain").stdout.strip())
    except Exception:
        doi_chung = False

    bc.append("`git rev-parse HEAD` → %s (mã %s)" % (head.strip()[:12] or "?", ma_head))
    bc.append("`git status --porcelain -uall` → %d dòng (mã %s)" % (len(dong_status), ma_st))
    bc.append("`git diff HEAD` → %d đường (mã %s)" % (len([x for x in diff.splitlines() if x.strip()]), ma_df))
    bc.append("`git ls-files` → %d tệp theo dõi (mã %s)" % (so_tep, ma_ls))
    bc.append("bộ thử tự dò được: %d bộ nền (chưa kể B5) + %d bộ của B5 = %d "
              "(app/thu + gateway/thu, trừ thu_e2e.py)" % (so_bo, so_bo_b5, so_bo + so_bo_b5))
    bc.append("PHIEN_BAN_SCHEMA = %s" % schema)
    bc.append("đối chứng dương (repo tạm bị sửa ⇒ `git status` phải thấy): %s"
              % ("CÓ" if doi_chung else "KHÔNG"))
    if "thu_muc" in vt:
        tm = vt["thu_muc"]
        bc.append("vân tay thư mục (dự phòng): %d tệp theo dõi = %s · %d tệp mới = %s"
                  % (tm.get("so_theo_doi"), str(tm.get("theo_doi"))[:16],
                     tm.get("so_chua_theo_doi"), str(tm.get("chua_theo_doi"))[:16]))

    if not doi_chung:
        return KetQua("BEST-01", "Repository Baseline", "FAIL", bc,
                      "đối chứng dương HỎNG: `git status` không thấy thay đổi trên repo tạm — "
                      "phép đo cây sạch là mù")
    if ma_head != 0 or not head.strip():
        return KetQua("BEST-01", "Repository Baseline", "FAIL", bc,
                      "không đọc được HEAD (mã git %s)" % ma_head)
    if thay_doi:
        return KetQua("BEST-01", "Repository Baseline", "FAIL", bc,
                      "có %d thay đổi ĐÃ THEO DÕI chưa commit: %s"
                      % (len(thay_doi), ", ".join(thay_doi[:5])))
    if moi_ngoai_vung:
        return KetQua("BEST-01", "Repository Baseline", "FAIL", bc,
                      "có tệp mới NGOÀI vùng thử/tài liệu: %s" % ", ".join(moi_ngoai_vung[:5]))
    if head.strip() != NEN_HEAD:
        return KetQua("BEST-01", "Repository Baseline", "NOT TESTED", bc,
                      "HEAD hiện tại %s KHÁC nền được giao %s — số đo phải làm lại"
                      % (head.strip()[:12], NEN_HEAD_NGAN))
    bc.append("kết luận: HEAD == nền giao %s; không thay đổi đã theo dõi; "
              "%d tệp mới nằm trong vùng thử/tài liệu" % (NEN_HEAD_NGAN, len(moi)))
    return KetQua("BEST-01", "Repository Baseline", "PASS", bc, so_ca=1)


def _gate_02():
    """BEST-02 — API Contract (8 endpoint · 21 trường · 12491 · District=' ' · 10/50)."""
    bc = []
    quet = _best_trong_cay()
    loi_dac_ta = _kiem_dac_ta()
    # Đối chứng dương cho phép tự kiểm đặc tả: một mục khai ĐÃ KIỂM CHỨNG mà không có bằng
    # chứng PHẢI bị bắt. Nếu không bắt được thì chính phép kiểm là mù.
    gia = json.loads(json.dumps(DAC_TA_XAC_NHAN))
    gia["muc"]["service_id"] = {"da_kiem_chung": True, "nguon": "tự phong"}
    bat_duoc_gia = bool(_kiem_dac_ta(gia))
    bc.append("đặc tả đã ghim: 8 endpoint · 21 trường · 12491 · District=1 dấu cách · 10/50")
    bc.append("tự kiểm đặc tả: %d lỗi; đối chứng dương (mục tự phong) bắt được: %s"
              % (len(loi_dac_ta), "CÓ" if bat_duoc_gia else "KHÔNG"))
    bc.append("quét mã sản phẩm: %d tệp khớp dấu vết BEST" % quet["tong_hit"])
    for k, ds in quet["hit"].items():
        bc.append("  · %s: %d tệp%s" % (k, len(ds), (" — " + ", ".join(ds[:3])) if ds else ""))
    bc.append("`app/adapter_best.py` tồn tại: %s" % ("CÓ" if quet["co_adapter_best"] else "KHÔNG"))

    if not bat_duoc_gia:
        return KetQua("BEST-02", "API Contract", "FAIL", bc,
                      "tự kiểm đặc tả KHÔNG bắt được mục khai khống — phép kiểm mù")
    if loi_dac_ta:
        return KetQua("BEST-02", "API Contract", "FAIL", bc, "; ".join(loi_dac_ta))
    if not quet["co_adapter_best"] and not quet["co_dang_ky_best"]:
        return KetQua("BEST-02", "API Contract", "BLOCKED", bc,
                      "KHÔNG có mã tích hợp BEST trong cây (0 adapter · 0 đăng ký · 0 hit 12491) "
                      "⇒ không có hợp đồng nào để đo. Đặc tả đã ghim, chưa đối chiếu được với mã.",
                      so_ca=1, so_skip=1)
    # Có mã BEST: kiểm bằng chứng hợp đồng ở mức nguồn — chỉ những gì đã xác nhận, không đoán.
    duong = os.path.join(GOC_APP, "adapter_best.py")
    if not os.path.exists(duong):
        return KetQua("BEST-02", "API Contract", "BLOCKED", bc,
                      "có đăng ký 'best' nhưng không thấy adapter_best.py — cần người chỉ đúng tệp")
    nguon = _doc(duong)
    thieu = []
    if "12491" not in nguon:
        thieu.append("thiếu ServiceId 12491")
    if not re.search(r"District\s*[:=]\s*[\"'] [\"']", nguon):
        thieu.append("thiếu District=\" \" (đúng một dấu cách)")
    if "10" not in nguon or "50" not in nguon:
        thieu.append("thiếu giới hạn 10/50")
    bc.append("adapter_best.py: %d byte · 12491=%s · District 1 dấu cách=%s"
              % (len(nguon), "12491" in nguon, bool(re.search(r"District\s*[:=]\s*[\"'] [\"']", nguon))))
    if thieu:
        return KetQua("BEST-02", "API Contract", "FAIL", bc, "; ".join(thieu))
    return KetQua("BEST-02", "API Contract", "PASS", bc,
                  "đối chiếu được các hằng đã xác nhận; 21 trường/8 endpoint vẫn CHƯA KIỂM CHỨNG "
                  "với tài liệu hãng", so_ca=1)


def _gate_03():
    """BEST-03 — Authentication: 2 loại secret tách rời · AES-256-GCM · token không lộ."""
    _dung_nen()
    bc = []
    # (a) AES-256-GCM thật: mã hoá → giải mã, nonce 12 byte, AAD sai phải hỏng.
    ro = "BEST-CRED-RAT-DAC-BIET-9f3a"
    aad = bao_mat.aad_credentials(7, "best")
    ban_ma = bao_mat.ma_hoa_v3(ro, aad)
    phan = ban_ma.split("$")
    nonce_byte = len(phan[2]) // 2 if len(phan) == 4 else -1
    giai = bao_mat.giai_ma(ban_ma, aad)
    aad_sai_hong = False
    try:
        bao_mat.giai_ma(ban_ma, bao_mat.aad_credentials(8, "best"))
    except Exception:
        aad_sai_hong = True
    khong_lo_ro = ro not in ban_ma
    bc.append("AES-GCM: tiền tố=%s · nonce=%d byte · giải lại=%s · AAD sai hỏng=%s · "
              "bản rõ có trong bản mã=%s (mã 0)"
              % (phan[0], nonce_byte, giai == ro, aad_sai_hong, not khong_lo_ro))
    # (b) Hai loại secret TÁCH RỜI ở tầng schema.
    cot = [r["name"] for r in csdl.nhieu("PRAGMA table_info(carrier_accounts)")]
    co_cred = "credentials_ma_hoa" in cot
    co_wh = "webhook_secret_ma_hoa" in cot
    # Đối chứng dương: một bảng chỉ có MỘT cột phải bị phép kiểm bắt là thiếu.
    con_tam = sqlite3.connect(":memory:")
    con_tam.execute("CREATE TABLE carrier_accounts (id INTEGER, credentials_ma_hoa TEXT)")
    cot_gia = [r[1] for r in con_tam.execute("PRAGMA table_info(carrier_accounts)")]
    con_tam.close()
    bat_duoc_thieu = ("credentials_ma_hoa" in cot_gia) and ("webhook_secret_ma_hoa" not in cot_gia)
    bc.append("cột secret: credentials_ma_hoa=%s · webhook_secret_ma_hoa=%s · "
              "đối chứng dương bắt bảng thiếu cột=%s"
              % (co_cred, co_wh, "CÓ" if bat_duoc_thieu else "KHÔNG"))
    # (c) Token không lộ: bộ che + bản mã không chứa bản rõ.
    tho_bi_mat = ("Authorization: Bearer " + ro).encode()
    da_che = http_jt.che_bi_mat(tho_bi_mat, [ro])
    con_nguyen = http_jt.che_bi_mat(tho_bi_mat, [])
    bc.append("che bí mật: đã che=%s · đối chứng dương (không đưa giá trị ⇒ còn nguyên)=%s"
              % (ro.encode() not in da_che, ro.encode() in con_nguyen))
    # (d) Bề mặt BEST cụ thể.
    so_best = _dem("SELECT COUNT(*) FROM carrier_accounts WHERE hang='best'")
    co_best = "best" in adapter._DANG_KY
    bc.append("tài khoản hãng BEST: %d · adapter 'best' đã đăng ký: %s" % (so_best, co_best))

    if not (nonce_byte == 12 and giai == ro and aad_sai_hong and khong_lo_ro
            and co_cred and co_wh and bat_duoc_thieu
            and (ro.encode() not in da_che) and (ro.encode() in con_nguyen)):
        return KetQua("BEST-03", "Authentication", "FAIL", bc,
                      "nền tảng KHÔNG đạt một trong các vế AES-GCM / tách secret / che token")
    if not co_best:
        return KetQua("BEST-03", "Authentication", "BLOCKED", bc,
                      "chưa có adapter/tài khoản BEST ⇒ chưa đo được 2 secret của BEST, token BEST. "
                      "Nền tảng đạt 4/4 phép kiểm liên quan (KHÔNG phải PASS cho BEST).",
                      so_ca=1, so_skip=1)
    return KetQua("BEST-03", "Authentication", "PASS", bc,
                  "nền tảng + BEST cùng đạt", so_ca=1)


def _gate_04():
    """BEST-04 — Create/Update/Cancel: idempotency · timeout ⇒ UNKNOWN · không retry mù."""
    _dung_nen()
    bc = []
    # (a) createOrder/cancelOrder KHÔNG thử lại mù; đọc thì có.
    so_lan = {"tao": 0, "doc": 0}

    def _ham_loi():
        so_lan["tao"] += 1
        raise transport.LoiTamThoi("mạng chập")

    try:
        transport.goi(_ham_loi, "createOrder", ngu=lambda s: None)
        tao_ket_qua = "KHÔNG NÉM"
    except transport.LoiTamThoi:
        tao_ket_qua = "NÉM"
    cs_tao = transport.chinh_sach_cho("createOrder")
    cs_doc = transport.chinh_sach_cho("getOrder")

    def _ham_doc():
        so_lan["doc"] += 1
        if so_lan["doc"] < 3:
            raise transport.LoiTamThoi("mạng chập")
        return "ok"

    kq_doc, so_lan_doc, _ = transport.goi(_ham_doc, "getOrder", ngu=lambda s: None)
    bc.append("createOrder: chính sách so_lan=%d duoc_thu_lai=%s · gọi thật %d lần · kết cục %s "
              "(mã 0)" % (cs_tao.so_lan, cs_tao.duoc_thu_lai, so_lan["tao"], tao_ket_qua))
    bc.append("getOrder: chính sách so_lan=%d · gọi thật %d lần · kết quả=%r"
              % (cs_doc.so_lan, so_lan_doc, kq_doc))
    # (b) Timeout ⇒ UNKNOWN, KHÔNG phải thành công.
    ad = adapter.tao_adapter("vtp", {}, "mock")
    kq_timeout = ad.createOrder({"ghi_chu": "demo_force_timeout"})
    kq_ok = ad.createOrder({"ghi_chu": "bình thường"})
    bc.append("mock VTP: timeout ⇒ ok=%s timeout=%s · bình thường ⇒ ok=%s"
              % (kq_timeout.ok, kq_timeout.timeout, kq_ok.ok))
    # (c) Idempotency thật ở Order Core.
    tid = csdl.mot("SELECT id FROM tenants WHERE code='shop-b'")["id"]
    uid = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap='shopb-owner'")["id"]
    don = {"nguoi_gui_ten": "A", "nguoi_gui_sdt": "0900000001", "nguoi_gui_dia_chi": "X",
           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0900000002", "nguoi_nhan_dia_chi": "Y",
           "hang_hoa": "hàng", "khoi_luong_gram": 100}
    idem = "b5-%d" % int(time.time() * 1000)
    d1, trung1 = don_hang.tao_don(tid, uid, don, idem_key=idem, kiem_quyen=False)
    d2, trung2 = don_hang.tao_don(tid, uid, don, idem_key=idem, kiem_quyen=False)
    bc.append("idempotency: lần 1 id=%s trùng=%s · lần 2 id=%s trùng=%s · cùng đơn=%s"
              % (d1["id"], trung1, d2["id"], trung2, d1["id"] == d2["id"]))
    # (d) Bề mặt BEST.
    co_best = "best" in adapter._DANG_KY
    bc.append("adapter 'best': %s" % ("CÓ" if co_best else "KHÔNG"))
    nen_dat = (cs_tao.so_lan == 1 and not cs_tao.duoc_thu_lai and so_lan["tao"] == 1
               and so_lan_doc == 3 and kq_doc == "ok"
               and kq_timeout.ok is False and kq_timeout.timeout is True
               and kq_ok.ok is True and d1["id"] == d2["id"] and trung2 is True)
    if not nen_dat:
        return KetQua("BEST-04", "Create/Update/Cancel", "FAIL", bc,
                      "nền tảng KHÔNG đạt idempotency / timeout-UNKNOWN / không-retry-mù")
    if not co_best:
        return KetQua("BEST-04", "Create/Update/Cancel", "BLOCKED", bc,
                      "chưa có adapter BEST ⇒ chưa đo được create/update/cancel của BEST. "
                      "Nền tảng đạt 3/3 phép kiểm liên quan (KHÔNG phải PASS cho BEST).",
                      so_ca=1, so_skip=1)
    return KetQua("BEST-04", "Create/Update/Cancel", "PASS", bc, so_ca=1)


def _gate_05():
    """BEST-05 — Webhook + Tracking: 11 bước · 24 mã · 605→606 · đến muộn · tenant."""
    _dung_nen()
    bc = []
    so_ma = {k: len(v) for k, v in trang_thai_hang.BANG.items()}
    so_loi = {k: len(v) for k, v in loi_hang.BANG_MA_LOI.items()}
    so_do = webhook.bang_muc_xac_thuc()
    bc.append("bảng mã trạng thái: %s · bảng mã lỗi: %s · sơ đồ xác thực webhook: %s (mã 0)"
              % (so_ma, so_loi, sorted(so_do)))
    co_best_ma = trang_thai_hang.BANG.get("best")
    co_best_wh = "best" in so_do
    bc.append("BEST: bảng mã=%s · sơ đồ webhook=%s" % (bool(co_best_ma), co_best_wh))
    if co_best_ma is not None:
        bc.append("BEST: %d mã trạng thái (đề bài: 24)" % len(co_best_ma))
        for ma in (605, 606):
            kq = trang_thai_hang.anh_xa("best", ma)
            bc.append("  · ánh xạ %d → %r" % (ma, kq.trang_thai))
    else:
        bc.append("BEST: 0 mã trạng thái đã đăng ký ⇒ KHÔNG đo được 24 mã / 605→606")
    bc.append("11 bước webhook: CHƯA KIỂM CHỨNG (đề bài nêu số bước, KHÔNG nêu tên bước; "
              "không được đoán)")
    if co_best_ma is None and not co_best_wh:
        return KetQua("BEST-05", "Webhook+Tracking", "BLOCKED", bc,
                      "chưa có bảng mã / sơ đồ webhook BEST ⇒ không có bề mặt để đo 24 mã, "
                      "605→606, đến muộn, tenant của BEST. Nền tảng chỉ có %s."
                      % ", ".join(sorted(so_ma)), so_ca=1, so_skip=1)
    thieu = []
    if co_best_ma is None or len(co_best_ma) != 24:
        thieu.append("số mã trạng thái BEST != 24")
    if co_best_ma is not None:
        a = trang_thai_hang.anh_xa("best", 605)
        b = trang_thai_hang.anh_xa("best", 606)
        if a.trang_thai == b.trang_thai:
            thieu.append("605 và 606 ánh xạ như nhau (đề bài: 605→606)")
    if not co_best_wh:
        thieu.append("thiếu sơ đồ xác thực webhook BEST")
    if thieu:
        return KetQua("BEST-05", "Webhook+Tracking", "FAIL", bc, "; ".join(thieu))
    return KetQua("BEST-05", "Webhook+Tracking", "PASS", bc, so_ca=1)


def _gate_06():
    """BEST-06 — Fee + PDF: tách Estimated/Actual/Contract · PDF chỉ từ hostname cho phép."""
    _dung_nen()
    bc = []
    tid = csdl.mot("SELECT id FROM tenants WHERE code='shop-b'")["id"]
    uid = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap='shopb-owner'")["id"]
    don = {"nguoi_gui_ten": "A", "nguoi_gui_sdt": "0900000001", "nguoi_gui_dia_chi": "X",
           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0900000002", "nguoi_nhan_dia_chi": "Y",
           "hang_hoa": "hàng", "khoi_luong_gram": 100}
    d, _ = don_hang.tao_don(tid, uid, don, idem_key="b5-phi-%d" % int(time.time() * 1000),
                            kiem_quyen=False)
    tai_chinh.ghi_phi(tid, d["id"], "bao_gia", 30000, "hang", "bao giá BEST (Estimated)")
    tai_chinh.ghi_phi(tid, d["id"], "thuc_te_hang", 35000, "hang", "phí thật BEST (Actual)")
    tai_chinh.ghi_phi(tid, d["id"], "du_kien_thu_khach", 40000, "nguoi", "giá hợp đồng (Contract)")
    p = tai_chinh.phi_cua_don(tid, d["id"])
    t = p["tong_theo_loai"]
    bc.append("phí 3 loại TÁCH RỜI: bao_gia=%s · thuc_te_hang=%s · du_kien_thu_khach=%s"
              % (t["bao_gia"], t["thuc_te_hang"], t["du_kien_thu_khach"]))
    bc.append("chênh lệch KHÔNG gộp: lệch báo giá=%s · lệch thu khách=%s"
              % (p["lech_so_bao_gia"], p["lech_so_thu_khach"]))
    # PDF/SSRF: nền tảng có danh sách trắng + ép HTTPS cho host hãng; BEST chưa có host.
    best_host = "api.bestexpress.vn"
    best_duoc_phep = http_jt.host_duoc_phep(best_host)
    http_bi_chan = https_ok = evil_bi_chan = False
    try:
        http_jt.tach_url("http://%s/nhan.pdf" % http_jt.HOST_HANG[0])
    except Exception as e:
        http_bi_chan = (getattr(e, "loai", "") == "url-sai")
    try:
        https_ok = http_jt.tach_url("https://%s/nhan.pdf" % http_jt.HOST_HANG[0])[0] == "https"
    except Exception:
        https_ok = False
    try:
        http_jt.tach_url("https://evil.example.com/nhan.pdf")
    except Exception as e:
        evil_bi_chan = (getattr(e, "loai", "") == "host-bi-tu-choi")
    bc.append("SSRF nền tảng: http host hãng bị chặn=%s · https host hãng nhận=%s · "
              "host lạ bị chặn=%s (đối chứng dương)" % (http_bi_chan, https_ok, evil_bi_chan))
    bc.append("BEST host %r nằm trong danh sách trắng=%s ⇒ CHƯA có đường tải PDF BEST"
              % (best_host, best_duoc_phep))
    co_best = "best" in adapter._DANG_KY
    nen_dat = (t["bao_gia"] == 30000 and t["thuc_te_hang"] == 35000
               and t["du_kien_thu_khach"] == 40000
               and p["lech_so_bao_gia"] == 5000 and p["lech_so_thu_khach"] == 5000
               and http_bi_chan and https_ok and evil_bi_chan)
    if not nen_dat:
        return KetQua("BEST-06", "Fee+PDF", "FAIL", bc,
                      "nền tảng KHÔNG đạt tách phí hoặc chặn SSRF")
    if not co_best:
        return KetQua("BEST-06", "Fee+PDF", "BLOCKED", bc,
                      "chưa có adapter BEST ⇒ chưa đo được phí BEST; PDF BEST chưa có hostname "
                      "được phép. Nền tảng đạt 2/2 phép kiểm liên quan (KHÔNG phải PASS cho BEST).",
                      so_ca=1, so_skip=1)
    if not best_duoc_phep:
        return KetQua("BEST-06", "Fee+PDF", "FAIL", bc,
                      "adapter BEST có nhưng hostname PDF chưa nằm trong danh sách trắng")
    return KetQua("BEST-06", "Fee+PDF", "PASS", bc, so_ca=1)


def _dong_claim_nguy_hai(nguon):
    """Đối chứng dương cho C3: dùng tenant trong payload để QUYẾT ĐỊNH phải bị bắt."""
    for dong in nguon.splitlines():
        if "claim_tenant" not in dong:
            continue
        if re.search(r"(SELECT|UPDATE|DELETE|INSERT|WHERE|tenant_id\s*=)", dong):
            return True
    return False


def _quet_tat_xac_minh(nguon):
    """Đối chứng dương cho C6: tìm dấu hiệu tắt xác minh chứng chỉ."""
    mau = re.compile(r"_create_unverified_context|CERT_NONE|check_hostname\s*=\s*False|"
                     r"verify\s*=\s*False|ssl\.CERT_NONE")
    return bool(mau.search(nguon))


def _gate_07():
    """BEST-07 — Multi-tenant Security: 6 điều cấm, mỗi điều một ca + đối chứng dương."""
    _dung_nen()
    bc = []
    dat = {}
    # ── C1: local-only, không gọi API BEST, không credentials thật ────────────────────────────
    ma_remote, remote, _ = _git("remote", "-v")
    so_remote = len([x for x in remote.splitlines() if x.strip()])
    so_bien_best = len([k for k in os.environ if re.search(r"best", k, re.I)])
    live_khoa = all(getattr(lop, "CHO_PHEP_LIVE", False) is False
                    for lop in adapter._DANG_KY.values())
    live_chan = False
    try:
        adapter.tao_adapter("vtp", {}, "production")
    except PermissionError:
        live_chan = True
    mock_mo = adapter.tao_adapter("vtp", {}, "mock") is not None
    best_host_chan = not http_jt.host_duoc_phep("api.bestexpress.vn")
    dat["C1"] = (so_remote == 0 and so_bien_best == 0 and live_khoa and live_chan
                 and mock_mo and best_host_chan)
    bc.append("C1: remote=%d · biến môi trường chứa 'best'=%d · mọi adapter khoá LIVE=%s · "
              "tạo production bị chặn=%s · mock mở được=%s · host BEST bị chặn=%s"
              % (so_remote, so_bien_best, live_khoa, live_chan, mock_mo, best_host_chan))
    # ── C2: không xoá dữ liệu / phá adapter ──────────────────────────────────────────────────
    ba_adapter = ("app/adapter.py", "app/adapter_jt.py", "app/adapter_vtp.py")
    ma_diff, diff, _ = _git("diff", "HEAD", "--", *ba_adapter)
    nguyen_ven = True
    for p in ba_adapter:
        ma_rev, blob_head, _ = _git("rev-parse", "HEAD:" + p)
        bam_head = blob_head.strip()
        bam_hien_tai = _git("hash-object", p)[1].strip()
        if ma_rev != 0 or bam_head != bam_hien_tai:
            nguyen_ven = False
    truoc = {b: _dem("SELECT COUNT(*) FROM %s" % b) for b in ("tenants", "users", "carrier_accounts")}
    # Đối chứng dương: băm phải đổi khi nội dung đổi.
    tep_tam = os.path.join(_TAM, "bam-thu.txt")
    with open(tep_tam, "w", encoding="utf-8") as f:
        f.write("a")
    bam_1 = _bam_noi_dung(tep_tam)
    with open(tep_tam, "w", encoding="utf-8") as f:
        f.write("b")
    bam_2 = _bam_noi_dung(tep_tam)
    phat_hien_doi = bam_1 != bam_2
    ngoai_cay = os.path.commonpath([os.path.abspath(_TAM), GOC_CAY]) != GOC_CAY
    dat["C2"] = (len([x for x in diff.splitlines() if x.strip()]) == 0 and nguyen_ven
                 and phat_hien_doi and ngoai_cay)
    bc.append("C2: diff 3 adapter=%d đường · blob y HEAD=%s · dữ liệu nền=%s · CSDL tạm ngoài cây=%s · "
              "đối chứng dương băm bắt đổi byte=%s"
              % (len([x for x in diff.splitlines() if x.strip()]), nguyen_ven, truoc,
                 ngoai_cay, phat_hien_doi))
    # ── C3: tenant_id; không xác định tenant ⇒ DENY ────────────────────────────────────────
    tid_a = csdl.mot("SELECT id FROM tenants WHERE code='shop-a'")["id"]
    tid_b = csdl.mot("SELECT id FROM tenants WHERE code='shop-b'")["id"]
    uid_b = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap='shopb-owner'")["id"]
    don = {"nguoi_gui_ten": "A", "nguoi_gui_sdt": "0900000001", "nguoi_gui_dia_chi": "X",
           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0900000002", "nguoi_nhan_dia_chi": "Y",
           "hang_hoa": "hàng", "khoi_luong_gram": 100}
    d, _ = don_hang.tao_don(tid_b, uid_b, don, idem_key="b5-tenant-%d" % int(time.time() * 1000),
                            kiem_quyen=False)
    doc_cheo = don_hang.lay_don(tid_a, d["id"])
    doc_dung = don_hang.lay_don(tid_b, d["id"])
    deny = False
    try:
        webhook.tenant_tu_account(None, 1)
    except webhook.LoiVinhVien:
        deny = True
    tenant_ok = webhook.tenant_tu_account(7, 1) == 7
    nguon_wh = _doc(os.path.join(GOC_APP, "webhook.py"))
    than_xu_ly = nguon_wh.split("def _xu_ly(sk):", 1)[1].split("\ndef ", 1)[0] \
        if "def _xu_ly(sk):" in nguon_wh else ""
    dung_account = bool(re.search(r"tenant_id\s*=\s*tenant_tu_account\(tk\[\"tenant_id\"\]",
                                  than_xu_ly))
    claim_trong_sql = _dong_claim_nguy_hai(than_xu_ly)
    gia_nguy_hai = 'csdl.mot("SELECT * FROM don_hang WHERE tenant_id=?", (sv.get("claim_tenant"),))'
    bat_duoc_gia = _dong_claim_nguy_hai(gia_nguy_hai)
    dat["C3"] = (doc_cheo is None and doc_dung is not None and deny and tenant_ok
                 and dung_account and not claim_trong_sql and bat_duoc_gia)
    bc.append("C3: đọc chéo tenant A→đơn B=%r · đọc đúng tenant B=%s · thiếu tenant bị DENY=%s · "
              "tenant hợp lệ trả 7=%s · tenant lấy từ carrier_account=%s · payload tenant vào SQL=%s · "
              "đối chứng dương bắt được=%s"
              % (doc_cheo, doc_dung is not None, deny, tenant_ok, dung_account,
                 claim_trong_sql, bat_duoc_gia))
    # ── C4: không đoán endpoint/schema ──────────────────────────────────────────────────────
    quet = _best_trong_cay()
    moi_muc_chua_kiem = all(not m.get("da_kiem_chung") for m in DAC_TA_XAC_NHAN["muc"].values())
    khong_host_best = not quet["hit"]["host_best"]
    dat["C4"] = moi_muc_chua_kiem and khong_host_best and not _kiem_dac_ta()
    bc.append("C4: %d/%d mục đặc tả còn CHƯA KIỂM CHỨNG · hit host BEST=%d · tự kiểm đặc tả=%s"
              % (sum(1 for m in DAC_TA_XAC_NHAN["muc"].values() if not m.get("da_kiem_chung")),
                 len(DAC_TA_XAC_NHAN["muc"]), len(quet["hit"]["host_best"]),
                 "ĐẠT" if not _kiem_dac_ta() else "HỎNG"))
    # ── C5: không ghi secret/token vào log/audit/response ─────────────────────────────────
    bi_mat = "BEST-TOKEN-RAT-DAC-BIET-9f3a"
    da_che = http_jt.che_bi_mat(("Bearer " + bi_mat).encode(), [bi_mat])
    nguyen_ban = http_jt.che_bi_mat(("Bearer " + bi_mat).encode(), [])
    ban_ma = bao_mat.ma_hoa_v3(bi_mat, bao_mat.aad_credentials(7, "best"))
    loi_aad = ""
    try:
        bao_mat.giai_ma(ban_ma, bao_mat.aad_credentials(8, "best"))
    except Exception as e:
        loi_aad = str(e)
    dat["C5"] = (bi_mat.encode() not in da_che and bi_mat.encode() in nguyen_ban
                 and bi_mat not in ban_ma and bi_mat not in loi_aad)
    bc.append("C5: che token=%s · đối chứng dương (không che ⇒ còn nguyên)=%s · "
              "token trong bản mã=%s · token trong thông điệp lỗi=%s"
              % (bi_mat.encode() not in da_che, bi_mat.encode() in nguyen_ban,
                 bi_mat in ban_ma, bi_mat in loi_aad))
    # ── C6: TLS ─────────────────────────────────────────────────────────────────────────────
    http_chan = False
    try:
        http_jt.tach_url("http://%s/x" % http_jt.HOST_HANG[0])
    except Exception as e:
        http_chan = (getattr(e, "loai", "") == "url-sai")
    https_ok = False
    try:
        https_ok = http_jt.tach_url("https://%s/x" % http_jt.HOST_HANG[0])[0] == "https"
    except Exception:
        https_ok = False
    nguon_http = _doc(os.path.join(GOC_APP, "http_jt.py"))
    dung_mac_dinh = "ssl.create_default_context" in nguon_http
    tat_xac_minh = _quet_tat_xac_minh(nguon_http)
    bat_duoc_gia = _quet_tat_xac_minh("ctx = ssl._create_unverified_context()")
    dat["C6"] = (http_chan and https_ok and dung_mac_dinh and not tat_xac_minh and bat_duoc_gia)
    bc.append("C6: HTTP host hãng bị chặn=%s · HTTPS nhận=%s · dùng create_default_context=%s · "
              "dấu hiệu tắt xác minh=%s · đối chứng dương bắt được=%s"
              % (http_chan, https_ok, dung_mac_dinh, tat_xac_minh, bat_duoc_gia))
    # C2 (tiếp): sau TOÀN BỘ phép đo, các bảng nền KHÔNG được giảm dòng — đo lại, không suy.
    sau = {b: _dem("SELECT COUNT(*) FROM %s" % b) for b in ("tenants", "users", "carrier_accounts")}
    khong_xoa = all(sau[b] >= truoc[b] for b in truoc)
    dat["C2"] = dat["C2"] and khong_xoa
    bc.append("C2 (sau đo): %s · không bảng nền nào giảm dòng=%s" % (sau, khong_xoa))
    so_dat = sum(1 for v in dat.values() if v)
    bc.append("TỔNG 6 điều cấm: %d/6 đạt trên HIỆN TRẠNG (chưa có mã BEST)" % so_dat)
    if so_dat != 6:
        hong = [k for k, v in dat.items() if not v]
        return KetQua("BEST-07", "Multi-tenant Security", "FAIL", bc,
                      "điều cấm không đạt: " + ", ".join(hong), so_ca=6, so_skip=6 - so_dat)
    return KetQua("BEST-07", "Multi-tenant Security", "PASS", bc,
                  "6/6 điều cấm đạt trên cây hiện tại. Chưa có mã BEST nên đây là PASS của "
                  "HIỆN TRẠNG, phải chạy lại sau khi B1–B4 hợp nhất.", so_ca=6)


def _chay_giao_dien(giay=900):
    ma, ra = _chay(["sh", "thu_giao_dien/chay.sh"], giay=giay)
    return ma, ra


def _gate_08(chay_that=False, ket_qua_ngoai=None):
    """BEST-08 — Frontend E2E: chạy THẬT `sh thu_giao_dien/chay.sh`."""
    bc = []
    ma = ra = None
    bc.append("BEST trong giao diện: dữ liệu DEMO trong `mock/carriers.json` (không phải tích hợp thật)")
    if ket_qua_ngoai is not None:
        ma, ra = ket_qua_ngoai
        bc.append("nguồn: kết quả do người chạy cung cấp (mã thoát %s)" % ma)
    elif chay_that:
        ma, ra = _chay_giao_dien()
        bc.append("`sh thu_giao_dien/chay.sh` → mã thoát %s" % ma)
    else:
        return KetQua("BEST-08", "Frontend E2E", "NOT TESTED", bc,
                      "chưa chạy trong lượt này — chạy `python3 app/thu/thu_best_qa.py --giao-dien` "
                      "(mất ~1 phút, cần Chromium trong node_modules)")
    so_pass = re.findall(r"(\d+) passed", ra)
    so_skip = re.findall(r"(\d+) skipped", ra)
    so_fail = re.findall(r"(\d+) failed", ra)
    khong_chay = re.findall(r"(\d+) did not run", ra)
    bc.append("playwright: passed=%s · failed=%s · skipped=%s · did not run=%s"
              % (so_pass[-1] if so_pass else "?", so_fail[-1] if so_fail else "0",
                 so_skip[-1] if so_skip else "0", khong_chay[-1] if khong_chay else "0"))
    if "Executable doesn't exist" in ra or "browserType.launch" in ra:
        return KetQua("BEST-08", "Frontend E2E", "BLOCKED", bc,
                      "KHÔNG chạy được Chromium trong worktree (thiếu nhị phân Playwright) — "
                      "lỗi MÔI TRƯỜNG, không phải lỗi sản phẩm", so_ca=1, so_skip=1)
    if ma != 0:
        loi = re.findall(r"✘\s+\d+ \[chromium\][^\n]+", ra)
        for x in loi[:3]:
            bc.append("  · " + x.strip()[:160])
        return KetQua("BEST-08", "Frontend E2E", "FAIL", bc,
                      "script thoát %s, %s ca hỏng" % (ma, so_fail[-1] if so_fail else "?"),
                      so_ca=int(so_pass[-1] or 0) + int(so_fail[-1] or 0) if so_pass else 0,
                      so_skip=int(so_skip[-1] or 0) if so_skip else 0)
    bc.append("BEST trong giao diện: chỉ là dữ liệu DEMO (`mock/carriers.json`), KHÔNG phải "
              "tích hợp thật")
    return KetQua("BEST-08", "Frontend E2E", "PASS", bc,
                  "bộ E2E giao diện chung đạt; phần BEST chỉ ở mức DEMO — KHÔNG phải REAL PASS",
                  so_ca=int(so_pass[-1]) if so_pass else 0,
                  so_skip=int(so_skip[-1]) if so_skip else 0)


def _gate_09():
    """BEST-09 — Real Account Connectivity: BLOCKED nếu thiếu credentials/HTTPS/TLS."""
    _dung_nen()
    bc = []
    quet = _best_trong_cay()
    so_bien = len([k for k in os.environ if re.search(r"(best|carrier).*(key|secret|token|pass)",
                                                      k, re.I)])
    co_best_account = _dem("SELECT COUNT(*) FROM carrier_accounts WHERE hang='best'")
    ma_remote, remote, _ = _git("remote", "-v")
    bc.append("credentials BEST trong môi trường: %d · tài khoản BEST trong CSDL tạm: %d"
              % (so_bien, co_best_account))
    bc.append("host/endpoint BEST trong mã: %d hit · adapter BEST: %s"
              % (len(quet["hit"]["host_best"]), quet["co_adapter_best"]))
    bc.append("remote git: %d (không có đường push)" % len([x for x in remote.splitlines() if x.strip()]))
    bc.append("bằng chứng TLS/hostname cho endpoint BEST: 0 (không có endpoint nào để xác minh)")
    thieu = []
    if not quet["co_adapter_best"]:
        thieu.append("adapter BEST")
    if so_bien == 0:
        thieu.append("credentials thật (chưa có, và KHÔNG được dùng ở lượt này)")
    if not quet["hit"]["host_best"]:
        thieu.append("endpoint HTTPS đã xác minh (chưa có endpoint nào)")
    thieu.append("bản ghi xác minh chứng chỉ + hostname (TLS)")
    thieu.append("phê duyệt của chủ doanh nghiệp + tài khoản test")
    return KetQua("BEST-09", "Real Account Connectivity", "BLOCKED", bc,
                  "THIẾU: " + "; ".join(thieu) + ". KHÔNG được ghi PASS khi chưa có đủ.",
                  so_ca=1, so_skip=1)


def _gate_10():
    """BEST-10 — Owner Acceptance: PENDING, chỉ chủ doanh nghiệp xác nhận."""
    bc = []
    # CHỈ một bản ký của Owner (ngoài repo) mới là bằng chứng. Hai tài liệu quy trình của B5
    # KHÔNG phải bản ký, nên không được đếm — đếm chúng là tự cho mình điểm.
    so_van_ban = 0
    for dirpath, dirnames, filenames in os.walk(os.path.join(GOC_CAY, "docs")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for ten in filenames:
            if not ten.endswith(".md") or "best" not in ten.lower():
                continue
            if ten in ("BEST_EXPRESS_QA.md", "BEST_EXPRESS_REAL_ACCEPTANCE.md"):
                continue          # tài liệu quy trình, không phải bản ký
            try:
                n = _doc(os.path.join(dirpath, ten))
            except OSError:
                continue
            if re.search(r"người xác nhận\s*\|\s*\S", n) and "PENDING" not in n:
                so_van_ban += 1
    bc.append("bản ký Owner cho BEST trong repo: %d (bản ký thật phải ở kênh NGOÀI repo)" % so_van_ban)
    bc.append("chỉ chủ doanh nghiệp được xác nhận — agent KHÔNG được tự ghi PASS")
    return KetQua("BEST-10", "Owner Acceptance", "PENDING", bc,
                  "PENDING: chưa có xác nhận của chủ doanh nghiệp. Đây không phải việc agent "
                  "được phép tự quyết.", so_ca=1, so_skip=1)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CHẠY 10 CỔNG + IN BẢNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
_CACHE = {}


def chay_ca_10(chay_giao_dien=False, kq_giao_dien=None):
    if _CACHE:
        return _CACHE
    ham = [("BEST-01", _gate_01), ("BEST-02", _gate_02), ("BEST-03", _gate_03),
           ("BEST-04", _gate_04), ("BEST-05", _gate_05), ("BEST-06", _gate_06),
           ("BEST-07", _gate_07),
           ("BEST-08", lambda: _gate_08(chay_that=chay_giao_dien, ket_qua_ngoai=kq_giao_dien)),
           ("BEST-09", _gate_09), ("BEST-10", _gate_10)]
    for ma, f in ham:
        try:
            kq = f()
        except Exception as e:
            kq = KetQua(ma, "?", "FAIL", ["ngoại lệ khi đo: %s: %s" % (type(e).__name__, e)],
                        "bộ đo hỏng ở cổng này — số đo KHÔNG đáng tin")
        _CACHE[ma] = kq
    return _CACHE


def in_bang(ket_qua):
    print("═" * 86)
    print("BẢNG 10 CỔNG — TÍCH HỢP BEST EXPRESS")
    print("CHẾ ĐỘ: %s" % PHAM_VI_NEN)
    print("NỀN: HEAD %s · cây %s" % (NEN_HEAD_NGAN, GOC_CAY))
    print("═" * 86)
    for ma in sorted(ket_qua):
        kq = ket_qua[ma]
        print("%-8s %-26s %-10s %s" % (kq.ma, kq.ten, kq.ket_qua, kq.chuoi_bang_chung()))
        for dong in kq.bang_chung[1:]:
            print("         " + dong)
        if kq.ly_do:
            print("         LÝ DO: " + kq.ly_do)
        if kq.so_ca or kq.so_skip:
            print("         ca=%d · skip=%d" % (kq.so_ca, kq.so_skip))
        print("-" * 86)
    dem = {}
    for kq in ket_qua.values():
        dem[kq.ket_qua] = dem.get(kq.ket_qua, 0) + 1
    print("TỔNG: " + " · ".join("%s=%d" % (k, dem[k]) for k in
                               ("PASS", "FAIL", "BLOCKED", "NOT TESTED", "PENDING") if k in dem))
    print("REAL PASS: 0 — mọi kết quả ở đây là LOCAL/MOCK.")
    print("═" * 86)


def in_json(ket_qua):
    vt = _van_tay()
    ra = {
        "pham_vi": PHAM_VI_NEN,
        "head": (vt.get("head") or "")[:12],
        "che_do_van_tay": vt.get("che_do"),
        "cay_sach": vt.get("sach"),
        "gates": [ket_qua[k].dong() for k in sorted(ket_qua)],
        "tong_ket": {k: sum(1 for x in ket_qua.values() if x.ket_qua == k)
                     for k in ("PASS", "FAIL", "BLOCKED", "NOT TESTED", "PENDING")},
    }
    print(json.dumps(ra, ensure_ascii=False, indent=1))


class ThuMuoiCong(unittest.TestCase):
    """10 ca — mỗi cổng một ca. BLOCKED/PENDING/NOT TESTED là SKIP có lý do, KHÔNG phải PASS."""

    def _ca(self, ma):
        kq = _CACHE[ma]
        if kq.ket_qua == "FAIL":
            self.fail("%s: %s — %s" % (ma, kq.ly_do, " | ".join(kq.bang_chung[:4])))
        if kq.ket_qua == "PASS":
            self.assertTrue(True, "%s PASS" % ma)
        else:
            self.skipTest("%s %s: %s" % (ma, kq.ket_qua, kq.ly_do))

    def test_01_baseline(self):
        self._ca("BEST-01")

    def test_02_api_contract(self):
        self._ca("BEST-02")

    def test_03_authentication(self):
        self._ca("BEST-03")

    def test_04_create_update_cancel(self):
        self._ca("BEST-04")

    def test_05_webhook_tracking(self):
        self._ca("BEST-05")

    def test_06_fee_pdf(self):
        self._ca("BEST-06")

    def test_07_multi_tenant_security(self):
        self._ca("BEST-07")

    def test_08_frontend_e2e(self):
        self._ca("BEST-08")

    def test_09_real_account(self):
        self._ca("BEST-09")

    def test_10_owner_acceptance(self):
        self._ca("BEST-10")


def main(argv=None):
    ap = argparse.ArgumentParser(description="B5 — 10 cổng QA BEST Express (LOCAL/MOCK)")
    ap.add_argument("--json", action="store_true", help="in JSON thay cho bảng")
    ap.add_argument("--giao-dien", action="store_true",
                    help="chạy THẬT sh thu_giao_dien/chay.sh cho cổng BEST-08")
    ap.add_argument("--nghiem-thu", action="store_true",
                    help="thoát 1 trừ khi CẢ 10 cổng PASS")
    ap.add_argument("--khong-unittest", action="store_true",
                    help="chỉ in bảng, không chạy lớp unittest")
    args = ap.parse_args(argv)
    try:
        kq = chay_ca_10(chay_giao_dien=args.giao_dien)
    except Exception as e:
        print("KHÔNG DỰNG ĐƯỢC NỀN ĐO: %s: %s" % (type(e).__name__, e))
        return 2
    if args.json:
        in_json(kq)
    else:
        in_bang(kq)
    co_fail = any(x.ket_qua == "FAIL" for x in kq.values())
    if args.nghiem_thu and any(x.ket_qua != "PASS" for x in kq.values()):
        print("NGHIỆM THU: HỎNG — còn cổng không PASS.")
        return 1
    if args.khong_unittest or args.json:
        return 1 if co_fail else 0
    # Chạy 10 ca để bộ chạy toàn dự án đếm được `Ran N` và phán bằng MÃ THOÁT.
    sys.stdout.flush()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ThuMuoiCong)
    ket = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if ket.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
