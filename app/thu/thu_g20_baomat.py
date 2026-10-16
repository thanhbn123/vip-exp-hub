#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 — AG-05: BẢY LỖI TÁI DIỄN (regression security) + KHOÁ SỐ/CHUỖI.

VÌ SAO CÓ TỆP NÀY
-----------------
Wave G20 chỉ ĐÓNG KHOẢNG TRỎNG CÒN LẠI — không làm lại việc đã đạt (G16-A ba cổng · G17 1460
ca/38 bộ · G18 1631/44 · G19 1733 ca/47 bộ). Hai khoảng trống được giao cho AG-05:

  (a) `N-G19-03` / `N-G18-03` — **TÁI DIỄN nhiều lần**: cổng "cây sạch" trong `thu_qa_g17.py` và
      `thu_qa_g18.py` chỉ miễn trừ tệp của CHÍNH NÓ, nên chỉ cần một làn KHÁC giao tệp mới là
      cổng ĐỎ — và nó đã làm đỏ hồi quy chung ở G18 rồi G19. Tệp này ĐO ĐỘC LẬP bản vá đó, và
      quan trọng hơn: đo **RĂNG** của bản vá (đối chứng âm + đột biến), vì cách chữa rẻ nhất —
      nới miễn trừ thành "bỏ qua hết" — sẽ làm cổng xanh vĩnh viễn mà không ai thấy.
  (b) `N-G19-01` — mã hãng gửi dạng **SỐ** trượt khoá bảng dạng **CHUỖI**. AG-03 đã vá một phần
      ở G19; tệp này ĐO LẠI trên cả hai bảng và KHOÁ LẠI bằng khẳng định cho **CẢ HAI DẠNG**, kèm
      chốt `D-4`: mã chưa xác minh ⇒ `NEEDS_REVIEW`, KHÔNG được ánh xạ bừa.

BỐN LUẬT TỰ ÁP (giống các bộ AG-01 trước — lý do tồn tại của chúng không đổi)
-----------------------------------------------------------------------------
1. **Không chạm mạng thật.** Tệp này KHÔNG mở cổng nào, KHÔNG gọi HTTP, KHÔNG gọi hãng — kể cả
   sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Có ca tự kiểm `A_Nen.test_a6` quét AST trên
   CHÍNH tệp này để chứng minh điều đó, thay vì dặn lòng.
2. **CSDL riêng.** `VIP_HUB_DATA` trỏ vào thư mục tạm, KHÔNG BAO GIỜ `app/du-lieu/`. Vẫn SQLite
   (`D-8`); cụm PostgreSQL production của dự án KHÁC bị CHẶN CỨNG và có ca đo riêng (`A_Nen.test_a5`,
   `test_a7`) — số cổng được GHÉP LÚC CHẠY nên chính tệp này không chứa nó.
3. **HAI CHỐT CHẶN BẮT BUỘC** (`docs/QA_G13_G15.md` §6.3):
   · `T_TuKiemBoDo` — ca CỐ Ý HỎNG chạy trong **TIẾN TRÌNH CON**, khẳng định bộ dò THẤY nó hỏng,
     kèm **ĐỘT BIẾN trên bản sao của chính cổng đang đo** để chứng minh từng cổng CÓ RĂNG;
   · `DOI_CHUNG` — mọi nhóm có ca PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG; `Z_TongKet` tự phán HỎNG nếu
     thiếu. Không có đối chứng dương thì "tầng chết hẳn" cũng làm mọi ca âm xanh vô nghĩa.
4. **Phán bằng MÃ THOÁT + SỐ CA**, không bằng chữ trong output.

GHIM HEAD: `VIP_G20_HEAD=<sha>` thì phép ghim HEAD là cổng CỨNG. Không đặt thì chỉ GHI RA (tệp này
còn phải chạy được sau khi gộp vào nhánh khác — tạo một tệp thử làm đỏ hồi quy của làn khác là
tác hại, xem chính `N-G19-03`).

BIẾN MÔI TRƯỜNG
---------------
    VIP_G20_DATA   nền CSDL tạm (mặc định: thư mục tạm mới)
    VIP_G20_HEAD   ghim commit nền đo
    VIP_G20_NHANH=1 bỏ qua nhóm ĐỘT BIẾN (T/B4/B5/C6) khi cần một lượt chạy nhanh

Chạy: python3 app/thu/thu_g20_baomat.py
"""
import ast
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True          # không để lại __pycache__ trong cây ĐANG ĐO

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_CAY = os.path.dirname(GOC_APP)
DUONG_TEP_NAY = os.path.abspath(__file__)

# CSDL riêng của lượt đo. KHÔNG BAO GIỜ trỏ vào `app/du-lieu/`.
_TAM = os.environ.get("VIP_G20_DATA") or tempfile.mkdtemp(prefix="veh-g20-ag05-")
os.environ["VIP_HUB_DATA"] = _TAM

if GOC_APP not in sys.path:
    sys.path.append(GOC_APP)

HEAD_GHIM = os.environ.get("VIP_G20_HEAD", "").strip()
NHANH = os.environ.get("VIP_G20_NHANH", "") == "1"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# SỔ ĐỐI CHỨNG — cùng luật với các bộ AG-01 trước
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


# ══════════════════════════════════════════════════════════════════════════════════════════════
# PHẠM VI WAVE — khai ĐỘC LẬP, không mượn hằng của bộ thử khác (đo độc lập mới có nghĩa)
# ══════════════════════════════════════════════════════════════════════════════════════════════
# "CÂY SẠCH" = KHÔNG có thay đổi NÀO ngoài các tệp mà WAVE đang làm. Wave G20/AG-05 đang làm đúng
# bốn tệp dưới đây. Đây KHÔNG phải "bỏ qua hết": tệp SẢN PHẨM bẩn vẫn ĐỎ (đo ở `B_ChotCaySach`).
TEP_CUA_WAVE_G20 = (
    "app/thu/thu_qa_g17.py",            # làn này sửa cổng cây sạch của G17
    "app/thu/thu_qa_g18.py",            # làn này sửa cổng cây sạch của G18
    "app/thu/thu_g20_baomat.py",        # tệp này
    "docs/G20_BAOMAT.md",               # tài liệu của làn
)

# Hai bộ thử mà làn này ĐANG SỬA — chúng phải vẫn xanh sau bản vá.
BO_THU_DANG_DO = ("app/thu/thu_qa_g17.py", "app/thu/thu_qa_g18.py")

# Tên ca "cây sạch" của từng bộ, để gọi ĐÍCH DANH trong đối chứng âm.
CA_CAY_SACH = {
    "app/thu/thu_qa_g17.py": "A_Nen.test_a1_cay_sach_va_head",
    "app/thu/thu_qa_g18.py": "A_Nen.test_a1_cay_sach_theo_pham_vi_wave",
}
CA_TU_KIEM_PHAM_VI = {
    "app/thu/thu_qa_g17.py": "A_Nen.test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu",
    "app/thu/thu_qa_g18.py": "A_Nen.test_a1b_pham_vi_wave_chi_phu_bo_thu_va_tai_lieu",
}
CA_DOI_CHUNG_AM = {
    "app/thu/thu_qa_g17.py": "A_Nen.test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO",
    "app/thu/thu_qa_g18.py": "A_Nen.test_a1d_doi_chung_am_tep_san_pham_lam_chot_DO",
}


def _khop(duong, mau):
    """Đường có khớp mẫu (hoặc bằng đúng) không — cùng luật fnmatch như hai cổng đang đo."""
    return duong == mau or fnmatch.fnmatch(duong, mau)


def _trong_pham_vi(duong, pham_vi=TEP_CUA_WAVE_G20):
    return any(_khop(duong, m) for m in pham_vi)


def _loc_cay_ban(dong, pham_vi=TEP_CUA_WAVE_G20):
    """HÀM THUẦN: các dòng `git status --porcelain` nằm NGOÀI phạm vi wave."""
    ra = []
    for d in dong:
        if not d.strip():
            continue
        p = d[3:].strip().strip('"')
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        if _trong_pham_vi(p, pham_vi):
            continue
        ra.append(d)
    return ra


# ── Nhịp tim git: MỘT đường duy nhất, và nó GỠ `GIT_CONFIG_*` dị dạng ─────────────────────────
# `N-G17-00`/`N-G18-00` còn nguyên trên máy này: `GIT_CONFIG_COUNT=2` mà `GIT_CONFIG_KEY_0` rỗng
# ⇒ MỌI lệnh git thoát 128. Không gỡ thì tệp này đo nhầm môi trường thành lỗi sản phẩm.
def _git(*tham_so, goc=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    e["GIT_CONFIG_COUNT"] = "0"
    return subprocess.run(["git", "-C", goc or GOC_CAY] + list(tham_so), capture_output=True,
                          text=True, env=e, timeout=120)


def _chay_bo_thu(duong_tuong_doi, doi_so=None, giay=900):
    """Chạy THẬT một bộ thử trong TIẾN TRÌNH CON. Trả (mã thoát, output, số ca, số bỏ qua)."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG")}
    e["GIT_CONFIG_COUNT"] = "0"
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e["VIP_HUB_DATA"] = _TAM
    lenh = [sys.executable, duong_tuong_doi] + list(doi_so or [])
    r = subprocess.run(lenh, capture_output=True, text=True, cwd=GOC_CAY, env=e, timeout=giay)
    out = (r.stdout or "") + (r.stderr or "")
    m = re.findall(r"Ran (\d+)", out)
    so_ca = int(m[-1]) if m else 0
    m2 = re.search(r"skipped=(\d+)", out)
    return r.returncode, out, so_ca, (int(m2.group(1)) if m2 else 0)


def _doc(duong_tuong_doi):
    with open(os.path.join(GOC_CAY, duong_tuong_doi), encoding="utf-8") as f:
        return f.read()


TEN_KHAI_PHAM_VI = ("PHAM_VI_LAN_NHA", "PHAM_VI_LAN_KHAC", "PHAM_VI_WAVE")


def _khai_pham_vi_tu_nguon(duong_tuong_doi):
    """Đọc phạm vi miễn trừ KHAI TRONG NGUỒN của một bộ thử khác, bằng AST (literal thuần).

    Vì sao AST chứ không `import`: những bộ kia dựng nền, mở máy chủ, chạy cả phút lúc import —
    nhập chúng vào đây là biến phép ĐO ĐỘC LẬP thành phép đo phụ thuộc.

    Nhận cả tên mới (`PHAM_VI_*`) LẪN tên cũ còn sót (`TEP_CUA_AG01_*`) để phép đo không mù với
    một bộ thử chưa đổi tên — `thu_qa_g19.py` đang ở đúng tình trạng đó.
    """
    ra = []
    for nut in ast.parse(_doc(duong_tuong_doi)).body:
        if not (isinstance(nut, ast.Assign) and len(nut.targets) == 1
                and isinstance(nut.targets[0], ast.Name)):
            continue
        ten = nut.targets[0].id
        if ten not in TEN_KHAI_PHAM_VI and not ten.startswith("TEP_CUA_AG01_"):
            continue
        try:
            gia = ast.literal_eval(nut.value)
        except ValueError:
            continue
        if isinstance(gia, (tuple, list)):
            ra.extend(str(x) for x in gia)
    return tuple(dict.fromkeys(ra))       # giữ thứ tự, bỏ trùng


def _khai_live(nguon):
    """Các giá trị literal gán cho `CHO_PHEP_LIVE` trong một nguồn Python (AST, không grep)."""
    ra = []
    for nut in ast.walk(ast.parse(nguon)):
        if isinstance(nut, ast.Assign) and isinstance(nut.value, ast.Constant) \
                and nut.value.value in (True, False):
            for t in nut.targets:
                if isinstance(t, ast.Name) and t.id == "CHO_PHEP_LIVE":
                    ra.append(nut.value.value)
    return ra


# ══════════════════════════════════════════════════════════════════════════════════════════════
# A. NỀN ĐO — cây · HEAD · ổ khoá LIVE · CSDL · phạm vi tự thân
# ══════════════════════════════════════════════════════════════════════════════════════════════
class A_Nen(unittest.TestCase):
    """Vi phạm bất kỳ mục nào ở đây ⇒ CHẶN GỘP: mọi số đo khác trở nên vô hiệu."""

    def test_a1_cay_sach_theo_pham_vi_wave(self):
        dong = _git("status", "--porcelain=v1", "-uall").stdout.splitlines()
        ban = _loc_cay_ban(dong)
        self.assertEqual(ban, [], f"CÂY BẨN ngoài phạm vi wave (F0) ⇒ mọi số đo vô hiệu: {ban}")
        _dc_duong("cay-sach-g20")
        print(f"\n  [A1] cây sạch ngoài {len(TEP_CUA_WAVE_G20)} tệp của wave · "
              f"HEAD={_git('rev-parse', 'HEAD').stdout.strip()[:12]}")

    def test_a2_nen_khong_lay_tu_main(self):
        """Đề bài: `main = de740dc` và KHÔNG chứa G13–G20 ⇒ phải ĐO, không tin lời khai."""
        m = _git("rev-parse", "main").stdout.strip()
        self.assertRegex(m, r"^[0-9a-f]{40}$", f"không đọc được nhánh `main`: {m!r}")
        for tep in ("docs/G16_ACCEPTANCE.md", "docs/G20_BAOMAT.md"):
            co = _git("cat-file", "-e", f"{m}:{tep}").returncode
            self.assertNotEqual(co, 0, f"`main` ĐÃ chứa {tep} ⇒ nền không như đề bài")
        goc = _git("merge-base", "--is-ancestor", m, "HEAD").returncode
        self.assertEqual(goc, 0, "`main` KHÔNG phải tổ tiên của HEAD ⇒ nền đo không hợp lệ")
        _dc_duong("main-khong-chua-g20")
        print(f"  [A2] main={m[:7]} · là tổ tiên của HEAD · KHÔNG chứa G16/G20")

    def test_a3_khong_adapter_nao_mo_live(self):
        """CHỐT `CHO_PHEP_LIVE`: đọc ĐỘNG từ sổ đăng ký, không đọc hằng viết cứng."""
        import adapter                                                   # noqa: E402
        import adapter_jt                                                # noqa: E402
        import adapter_vtp                                               # noqa: E402
        mo = sorted(m for m, lop in adapter._DANG_KY.items()
                    if getattr(lop, "CHO_PHEP_LIVE", False))
        self.assertGreaterEqual(len(adapter._DANG_KY), 2, "sổ đăng ký adapter RỖNG ⇒ ca vô nghĩa")
        self.assertEqual(mo, [], f"có adapter MỞ LIVE: {mo}")
        _dc_am("live-khoa")
        # ĐỐI CHỨNG DƯƠNG: bộ dò PHẢI thấy được một lớp giả đã mở.
        gia = type("AdapterGiaLiveG20", (), {"CHO_PHEP_LIVE": True})
        adapter._DANG_KY["gia-live-g20"] = gia
        try:
            thay = [m for m, lop in adapter._DANG_KY.items()
                    if getattr(lop, "CHO_PHEP_LIVE", False)]
        finally:
            adapter._DANG_KY.pop("gia-live-g20", None)
        self.assertEqual(thay, ["gia-live-g20"], "bộ dò MÙ với adapter MỞ LIVE")
        _dc_duong("live-khoa")
        print(f"  [A3] {len(adapter._DANG_KY)} lớp adapter · LIVE mở: 0 · bộ dò bắt được lớp giả")

    def test_a4_o_khoa_live_nam_o_adapter_khong_nam_o_cau_hinh(self):
        """`CHO_PHEP_LIVE` là khoá CHỐT CỨNG trong lớp adapter — KHÔNG được thành cần gạt config.

        Đo bằng AST trên nguồn (không `import`, không grep chú thích — chú thích của chính dự án
        có rất nhiều chỗ NHẮC tới `CHO_PHEP_LIVE`, grep sẽ báo động giả).
        """
        import glob as _glob
        nguon_ch = _doc("app/cau_hinh.py")
        self.assertEqual(_khai_live(nguon_ch), [],
                         "`app/cau_hinh.py` khai `CHO_PHEP_LIVE` ⇒ ổ khoá thành cần gạt cấu hình")
        tat_ca, so_lop = {}, 0
        for p in sorted(_glob.glob(os.path.join(GOC_APP, "adapter*.py"))):
            ten = os.path.relpath(p, GOC_CAY)
            gia = _khai_live(open(p, encoding="utf-8").read())
            if gia:
                tat_ca[ten] = gia
                so_lop += len(gia)
        self.assertGreaterEqual(so_lop, 2, f"quá ít khai báo CHO_PHEP_LIVE để đo: {tat_ca}")
        for ten, gia in tat_ca.items():
            self.assertEqual(set(gia), {False}, f"{ten}: CHO_PHEP_LIVE có giá trị {gia}")
        # ĐỐI CHỨNG DƯƠNG: bộ đọc AST phải BẮT được một dòng cố ý mở.
        self.assertEqual(_khai_live("class A:\n    CHO_PHEP_LIVE = True\n"), [True],
                         "bộ đọc AST MÙ với `CHO_PHEP_LIVE = True`")
        # ĐO TRỰC TIẾP: làn này KHÔNG đụng tới `app/cau_hinh.py` (git nói, không phải tôi nói).
        d = _git("status", "--porcelain=v1", "--", "app/cau_hinh.py").stdout.strip()
        self.assertEqual(d, "", f"`app/cau_hinh.py` ĐÃ bị đụng: {d}")
        _dc_am("cau-hinh-live")
        _dc_duong("cau-hinh-live")
        print(f"  [A4] `app/cau_hinh.py`: 0 khai báo CHO_PHEP_LIVE · càng nằm ở {tat_ca} · "
              "git xác nhận cau_hinh.py KHÔNG bị đụng")

    def test_a5_csdl_nghiep_vu_van_la_sqlite(self):
        """`D-8`: KHÔNG chuyển CSDL nghiệp vụ sang PostgreSQL. PostgreSQL chỉ cụm RIÊNG.

        Đọc bằng AST chứ không grep: `app/csdl.py` có CHÚ THÍCH nhắc `psycopg` (ghi chú khi sang
        PostgreSQL), grep sẽ báo động giả — và một cổng báo động giả là cổng bị học cách bỏ qua.
        """
        nguon = _doc("app/csdl.py")
        nhap, chuoi = set(), []
        for nut in ast.walk(ast.parse(nguon)):
            if isinstance(nut, ast.Import):
                nhap |= {a.name.split(".")[0] for a in nut.names}
            elif isinstance(nut, ast.ImportFrom) and nut.module:
                nhap.add(nut.module.split(".")[0])
            elif isinstance(nut, ast.Constant) and isinstance(nut.value, str):
                chuoi.append(nut.value)
        self.assertIn("sqlite3", nhap, f"`app/csdl.py` không import sqlite3 (nhập: {sorted(nhap)})")
        self.assertEqual(nhap & {"psycopg", "psycopg2", "asyncpg"}, set(),
                         "`app/csdl.py` import driver PostgreSQL ⇒ nghi vấn chuyển D-8")
        xau = [s for s in chuoi if "postgresql://" in s or "postgres://" in s]
        self.assertEqual(xau, [], f"`app/csdl.py` chứa chuỗi kết nối PostgreSQL: {xau}")
        _dc_duong("csdl-sqlite")
        print(f"  [A5] `app/csdl.py`: nhập {sorted(nhap)} · 0 driver PostgreSQL · "
              "0 chuỗi kết nối PostgreSQL (chú thích nhắc psycopg KHÔNG bị tính)")

    def test_a6_tep_nay_khong_cham_mang(self):
        """TỰ KIỂM: quét AST trên CHÍNH tệp này — không import mạng, không URL, không cổng."""
        nguon = _doc("app/thu/thu_g20_baomat.py")
        cam = ("requests", "httpx", "urllib.request", "http.client", "socket", "ssl", "ftplib")
        thay = []
        for nut in ast.walk(ast.parse(nguon)):
            if isinstance(nut, ast.Import):
                thay += [a.name for a in nut.names if a.name in cam]
            elif isinstance(nut, ast.ImportFrom) and (nut.module or "") in cam:
                thay.append("from " + nut.module)
        self.assertEqual(thay, [], f"tệp này import mô-đun CHẠM MẠNG: {thay}")
        urls = re.findall(r"https?://[^\s\"']+", nguon)
        self.assertEqual(urls, [], f"tệp này chứa URL mạng: {urls}")
        _dc_am("khong-cham-mang")
        # ĐỐI CHỨNG DƯƠNG: bộ quét phải THẤY được một import mạng giả.
        gia = "import socket\nimport requests\n"
        tim = []
        for nut in ast.walk(ast.parse(gia)):
            if isinstance(nut, ast.Import):
                tim += [a.name for a in nut.names if a.name in cam]
        self.assertEqual(tim, ["socket", "requests"], "bộ quét AST MÙ với import mạng")
        _dc_duong("khong-cham-mang")
        print("  [A6] tự quét AST: 0 import mạng · 0 URL trong tệp này (bộ quét bắt được ca giả)")

    def test_a7_khong_cham_cum_postgres_cam(self):
        """Cụm cổng cấm đang giữ dữ liệu dự án KHÁC (`vip_customs*`) ⇒ CHẶN CỨNG.

        Số cổng được GHÉP LÚC CHẠY (`CONG_CAM`) chứ không viết thẳng: nếu viết thẳng thì chính
        dòng khẳng định `assertNotIn("…")` đã chứa chuỗi cần cấm, và ca này tự làm mình đỏ.
        """
        nguon = _doc("app/thu/thu_g20_baomat.py")
        self.assertNotIn(CONG_CAM, nguon, f"tệp này có nhắc cổng cấm {CONG_CAM} ⇒ phải xét lại")
        _dc_am("khong-cong-cam")
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải BẮT được một chuỗi có cổng cấm.
        self.assertIn(CONG_CAM, f"host=127.0.0.1 port={CONG_CAM}",
                      "bộ dò MÙ với cổng cấm")
        _dc_duong("khong-cong-cam")
        print(f"  [A7] tệp này: 0 tham chiếu cổng {CONG_CAM} · CSDL đo dùng SQLite tạm")

    def test_a8_head_doc_duoc(self):
        head = _git("rev-parse", "HEAD").stdout.strip()
        self.assertRegex(head, r"^[0-9a-f]{40}$", f"HEAD không đọc được: {head!r}")
        if HEAD_GHIM:
            self.assertEqual(head, HEAD_GHIM, "HEAD KHÁC mốc ghim `VIP_G20_HEAD`")
            _dc_duong("ghim-head")
        else:
            print(f"  [A8] HEAD={head} · KHÔNG ghim (`VIP_G20_HEAD` trống) — phép ghim chỉ GHI RA")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B. CỔNG "CÂY SẠCH" — ĐO ĐỘC LẬP BẢN VÁ `N-G19-03`/`N-G18-03`, VÀ ĐO RĂNG CỦA NÓ
# ══════════════════════════════════════════════════════════════════════════════════════════════
TEP_TAM_SAN_PHAM = "app/_ag05_g20_tam_san_pham.py"
TEP_TAM_MOCK = "mock/_ag05_g20_tam_mock.json"
TEP_TAM_GATEWAY = "gateway/_ag05_g20_tam_gateway.py"

# Cổng PostgreSQL của dự án KHÁC — GHÉP LÚC CHẠY để chính tệp này không chứa chuỗi cần cấm
# (xem `A_Nen.test_a7`: một khẳng định viết thẳng số cổng sẽ tự làm mình đỏ).
CONG_CAM = "54" + "32"


class B_ChotCaySach(unittest.TestCase):
    """Bản vá `N-G19-03` phải vừa ĐỦ RỘNG (làn khác giao tệp ⇒ vẫn xanh) vừa CÒN RĂNG (tệp sản
    phẩm bẩn ⇒ ĐỎ). Đo bằng LỆNH THẬT trên CÂY THẬT, không bằng đọc mã."""

    def test_b1_hai_bo_thu_cu_deu_xanh_tren_cay_co_tep_cua_wave(self):
        """ĐO ĐỘC LẬP: `thu_qa_g17.py` và `thu_qa_g18.py` phải XANH khi có tệp của làn này.

        Đây là phép đo TRỰC TIẾP của lỗi tái diễn: trước bản vá, cả hai ĐỎ vì tệp
        `app/thu/thu_g20_baomat.py` + `docs/G20_BAOMAT.md` (đo được: `Ran 7 tests … FAILED
        (failures=1)` và `AssertionError: Lists differ: ['?? app/thu/thu_g20_baomat.py',
        '?? docs/G20_BAOMAT.md'] != []`, mã thoát 1 cho cả hai).
        """
        ket = {}
        for bo in BO_THU_DANG_DO:
            ma, out, ca, bo_qua = _chay_bo_thu(bo, ["A_Nen"])
            ket[bo] = (ma, ca, bo_qua)
            self.assertEqual(ma, 0,
                             f"{bo}::A_Nen ĐỎ (mã thoát {ma}) — cổng cây sạch chưa được vá:\n"
                             + "\n".join(d for d in out.splitlines()
                                         if d.startswith(("FAIL", "ERROR", "AssertionError"))))
            self.assertGreater(ca, 0, f"{bo}::A_Nen chạy 0 ca ⇒ không có dấu vết đã đo")
        _dc_duong("cay-sach-vá")
        print("  [B1] " + " · ".join(f"{os.path.basename(b)} {v[1]} ca ✓" for b, v in ket.items())
              + " (cây ĐANG có 4 tệp của wave)")

    def test_b2_doi_chung_am_tep_san_pham_lam_hai_cong_DO(self):
        """ĐỐI CHỨNG ÂM BẮT BUỘC: dựng tệp SẢN PHẨM mới ⇒ cổng cây sạch của CẢ HAI bộ PHẢI ĐỎ.

        Tệp được TẠO RỒI XOÁ trong `finally`; KHÔNG tệp sản phẩm nào bị sửa nội dung. Đây đúng
        khuôn `N-G19-03` đã làm đỏ hồi quy G18/G19 — chỉ khác: lần này nó PHẢI đỏ.
        """
        self.assertFalse(os.path.exists(os.path.join(GOC_CAY, TEP_TAM_SAN_PHAM)),
                         "đường tạm đã tồn tại trước lượt đo")
        ket = {}
        try:
            with open(os.path.join(GOC_CAY, TEP_TAM_SAN_PHAM), "w", encoding="utf-8") as f:
                f.write("# TỆP TẠM CỦA ĐỐI CHỨNG ÂM (AG-05 G20) — bộ thử tự xoá\n")
            for bo, ca in CA_CAY_SACH.items():
                ma, out, _, _ = _chay_bo_thu(bo, [ca])
                ket[bo] = (ma, out)
                self.assertNotEqual(ma, 0,
                                    f"{bo}::{ca} VẪN XANH dù có tệp SẢN PHẨM mới ⇒ cổng MẤT RĂNG")
                self.assertIn("FAIL:", out, f"{bo}::{ca} đỏ nhưng không có dòng FAIL: để đối chiếu")
        finally:
            if os.path.exists(os.path.join(GOC_CAY, TEP_TAM_SAN_PHAM)):
                os.remove(os.path.join(GOC_CAY, TEP_TAM_SAN_PHAM))
        # ĐỐI CHỨNG DƯƠNG của chính phép đo: xoá tệp tạm ⇒ cổng XANH LẠI (không phải "đỏ vĩnh viễn")
        for bo, ca in CA_CAY_SACH.items():
            ma, out, _, _ = _chay_bo_thu(bo, [ca])
            self.assertEqual(ma, 0, f"{bo}::{ca} vẫn ĐỎ sau khi xoá tệp tạm:\n{out[-800:]}")
        _dc_am("cay-sach-doi-chung-am")
        _dc_duong("cay-sach-doi-chung-am")
        print("  [B2] " + " · ".join(f"{os.path.basename(b)} đỏ khi có tệp lạ (mã thoát {v[0]})"
                                     for b, v in ket.items()) + " · xanh lại sau khi xoá")

    def test_b3_doi_chung_am_o_ca_mock_va_gateway(self):
        """Mở rộng đối chứng âm ra hai thư mục sản phẩm KHÁC (`mock/`, `gateway/`)."""
        for duong in (TEP_TAM_MOCK, TEP_TAM_GATEWAY):
            self.assertFalse(os.path.exists(os.path.join(GOC_CAY, duong)), f"đã tồn tại: {duong}")
        ket = {}
        try:
            for duong in (TEP_TAM_MOCK, TEP_TAM_GATEWAY):
                with open(os.path.join(GOC_CAY, duong), "w", encoding="utf-8") as f:
                    f.write("{}\n" if duong.endswith(".json") else "# tạm\n")
            for bo, ca in CA_CAY_SACH.items():
                ma, out, _, _ = _chay_bo_thu(bo, [ca])
                ket[bo] = ma
                self.assertNotEqual(ma, 0, f"{bo}::{ca} VẪN XANH với tệp lạ ở mock/ + gateway/")
                self.assertTrue(any(d in out for d in ("mock/", "gateway/")),
                                f"{bo}::{ca} đỏ nhưng không nhắc đường nào trong mock//gateway/")
        finally:
            for duong in (TEP_TAM_MOCK, TEP_TAM_GATEWAY):
                if os.path.exists(os.path.join(GOC_CAY, duong)):
                    os.remove(os.path.join(GOC_CAY, duong))
        _dc_am("cay-sach-doi-chung-am-2")
        _dc_duong("cay-sach-doi-chung-am-2")
        print("  [B3] tệp lạ ở `mock/` + `gateway/` ⇒ cả hai cổng ĐỎ: "
              + " · ".join(f"{os.path.basename(b)}={m}" for b, m in ket.items()))

    def test_b4_hai_cong_khai_dung_pham_vi_wave_cua_chinh_no(self):
        """ĐO ĐỘC LẬP bằng AST: phạm vi KHAI TRONG NGUỒN của hai cổng phải phủ ĐỦ 4 tệp của wave.

        Không mượn hằng của chúng (không `import`) — nếu không thì phép đo chỉ lặp lại lời khai.
        """
        for bo in BO_THU_DANG_DO:
            khai = _khai_pham_vi_tu_nguon(bo)
            self.assertTrue(khai, f"{bo}: không đọc được khai báo phạm vi nào bằng AST")
            thieu = [t for t in TEP_CUA_WAVE_G20
                     if not any(_khop(t, m) for m in khai) and t != bo]
            self.assertEqual(thieu, [], f"{bo}: phạm vi KHAI TRONG NGUỒN thiếu {thieu}")
        _dc_duong("pham-vi-khai-doc-lap")
        print("  [B4] AST trên nguồn hai cổng: phạm vi khai phủ đủ 4 tệp của wave")

    @unittest.skipIf(NHANH, "VIP_G20_NHANH=1")
    def test_b5_dot_bien_bo_qua_het_lam_chot_DO(self):
        """TỰ KIỂM BỘ ĐO — `N-G19-03` chữa sai cách: nới miễn trừ thành "bỏ qua hết".

        Đột biến trên BẢN SAO của chính cổng: `_loc_cay_ban` trả `[]` (không bao giờ bẩn). Khi đó
        cổng "cây sạch" XANH vĩnh viễn — và ĐỐI CHỨNG ÂM của chính nó (`test_a1d`) PHẢI ĐỎ. Ca
        này khẳng định đúng vòng đó, nên nó chứng minh `test_a1d` CÓ RĂNG chứ không phải trang trí.
        """
        for bo in BO_THU_DANG_DO:
            # BẢN GỐC chạy TRƯỚC, khi cây chưa có bản sao đột biến — nếu không, chính bản sao
            # (`app/thu/_ag05_db_*.py`, một tệp NGOÀI phạm vi wave) làm bản gốc đỏ và phép so vô nghĩa.
            ma_goc, out_goc, _, _ = _chay_bo_thu(bo, [CA_DOI_CHUNG_AM[bo]])
            self.assertEqual(ma_goc, 0,
                             f"{bo}: bản GỐC đã đỏ ⇒ đột biến không nói lên điều gì:\n"
                             + out_goc[-600:])
            duong_bien = _dat_dot_bien(bo, "bo_qua_het")
            try:
                ma, out, _, _ = _chay_bo_thu(duong_bien, [CA_DOI_CHUNG_AM[bo]])
                self.assertNotEqual(ma, 0,
                                    f"đột biến `bỏ qua hết` ở {bo} KHÔNG bị đối chứng âm bắt "
                                    f"⇒ đối chứng âm là trang trí")
                self.assertIn("FAIL:", out, f"{bo}: đỏ nhưng thiếu dòng FAIL: để đối chiếu")
            finally:
                _xoa_tam(duong_bien)
        _dc_am("dot-bien-bo-qua-het")
        _dc_duong("dot-bien-bo-qua-het")
        print("  [B5] đột biến `_loc_cay_ban → []` ở CẢ HAI cổng: `test_a1d` ĐỎ (bản gốc XANH)")

    @unittest.skipIf(NHANH, "VIP_G20_NHANH=1")
    def test_b6_dot_bien_nuot_ma_san_pham_lam_cong_tu_kiem_DO(self):
        """TỰ KIỂM BỘ ĐO — nước đi sai thứ hai: nhét `app/webhook.py` vào danh sách miễn trừ.

        Cổng tự kiểm phạm vi (`test_a1b`) PHẢI ĐỎ. Không có ca này thì một miễn trừ ôm mã sản
        phẩm sẽ đi qua im lặng, và cổng "cây sạch" thành cổng "cây nào cũng sạch".
        """
        for bo in BO_THU_DANG_DO:
            # BẢN GỐC chạy TRƯỚC, khi cây chưa có bản sao đột biến — nếu không, chính bản sao
            # (`app/thu/_ag05_db_*.py`, một tệp NGOÀI phạm vi wave) làm bản gốc đỏ và phép so vô nghĩa.
            ma_goc, out_goc, _, _ = _chay_bo_thu(bo, [CA_TU_KIEM_PHAM_VI[bo]])
            self.assertEqual(ma_goc, 0,
                             f"{bo}: bản GỐC đã đỏ ⇒ phép so với đột biến vô nghĩa:\n"
                             + out_goc[-600:])
            duong_bien = _dat_dot_bien(bo, "nuot_san_pham")
            try:
                ma, out, _, _ = _chay_bo_thu(duong_bien, [CA_TU_KIEM_PHAM_VI[bo]])
                self.assertNotEqual(ma, 0,
                                    f"đột biến `nuốt app/webhook.py` ở {bo} KHÔNG bị cổng tự kiểm "
                                    f"bắt ⇒ cổng tự kiểm là trang trí")
                self.assertIn("FAIL:", out, f"{bo}: đỏ nhưng thiếu dòng FAIL: để đối chiếu")
            finally:
                _xoa_tam(duong_bien)
        _dc_am("dot-bien-nuot-san-pham")
        _dc_duong("dot-bien-nuot-san-pham")
        print("  [B6] đột biến nhét `app/webhook.py` vào miễn trừ: `test_a1b` ĐỎ (bản gốc XANH)")

    def test_b7_ban_sao_thu_ba_o_thu_qa_g19_van_dormant(self):
        """`thu_qa_g19.py` có BẢN SAO THỨ BA của cùng lỗi (`TEP_CUA_AG01_G19`, dòng 79).

        Nó NGOÀI phạm vi được cấp của làn này, nên tôi KHÔNG sửa — tôi ĐO nó. Trên cây này nó
        DORMANT vì `setUpModule` tự bỏ qua khi HEAD khác nền đóng băng. Khẳng định ở đây là phép
        TUYỂN (bỏ qua ĐƯỢC, hoặc chạy mà XANH): nếu ai đó vá nó thì ca này vẫn xanh; nếu nó chạy
        thật mà ĐỎ thì đây là lỗi thật và phải đỏ.
        """
        ma, out, ca, bo_qua = _chay_bo_thu("app/thu/thu_qa_g19.py", ["A_Nen"])
        tg = khai = _khai_pham_vi_tu_nguon("app/thu/thu_qa_g19.py")
        print(f"  [B7] `thu_qa_g19.py::A_Nen` mã thoát {ma} · {ca} ca · {bo_qua} bỏ qua · "
              f"miễn trừ khai trong nguồn={tg}")
        if "skipped" in out and ca == 0:
            _dc_am("g19-ban-sao-thu-ba")
            _dc_duong("g19-ban-sao-thu-ba")
            self.assertNotIn("thu_g20_baomat.py", " ".join(khai),
                             "phạm vi g19 ĐÃ phủ tệp G20 — cập nhật lại nhận định trong tài liệu")
            return
        self.assertEqual(ma, 0, f"`thu_qa_g19.py::A_Nen` chạy THẬT và ĐỎ:\n{out[-1500:]}")
        _dc_am("g19-ban-sao-thu-ba")
        _dc_duong("g19-ban-sao-thu-ba")


# ── Máy đột biến: LUÔN khẳng định phép thay đã GIEO ĐƯỢC, kẻo đột biến rỗng ruột ─────────────
DOT_BIEN = {
    # "bỏ qua hết": chèn `return []` ngay đầu hàm lọc.
    "bo_qua_het": (
        "    ra = []\n    for d in dong:\n        if not d.strip():",
        "    return []\n    ra = []\n    for d in dong:\n        if not d.strip():",
    ),
    # "nuốt mã sản phẩm": nhét đích danh một tệp sản phẩm vào danh sách miễn trừ của làn khác.
    "nuot_san_pham": (
        "PHAM_VI_LAN_KHAC = (\n",
        "PHAM_VI_LAN_KHAC = (\n    \"app/webhook.py\",\n",
    ),
}


def _duong_ban_sao(bo):
    """Đường TUYỆT ĐỐI của bản sao đột biến ứng với một bộ thử (chưa chắc đã tồn tại)."""
    goc = os.path.join(GOC_CAY, bo)
    return os.path.join(os.path.dirname(goc), "_ag05_db_" + os.path.basename(goc))


def _dat_dot_bien(bo, ten):
    """Ghi BẢN SAO đã đột biến của một bộ thử vào `app/thu/`, cạnh tệp gốc.

    Đặt cạnh tệp gốc chứ không ra thư mục tạm: bộ thử tự suy `GOC_CAY` từ `__file__`, nên bản sao
    ở nơi khác sẽ đo NHẦM CÂY. Tên bản sao KHÔNG khớp `thu_*.py` nên `chay_tat_ca.sh` không dò thấy.
    """
    duong_bien = _duong_ban_sao(bo)
    truoc, sau = DOT_BIEN[ten]
    nguon = _doc(bo)
    dem = nguon.count(truoc)
    if dem != 1:
        raise AssertionError(f"đột biến `{ten}` không gieo được vào {bo}: mẫu xuất hiện {dem} lần"
                             " ⇒ phép tự kiểm sẽ RỖNG RUỘT nếu bỏ qua chỗ này")
    with open(duong_bien, "w", encoding="utf-8") as f:
        f.write(nguon.replace(truoc, sau))
    return os.path.relpath(duong_bien, GOC_CAY)


def _xoa_tam(duong_tuong_doi):
    p = os.path.join(GOC_CAY, duong_tuong_doi)
    if os.path.exists(p):
        os.remove(p)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# C. KHOÁ SỐ / CHUỖI — `N-G19-01` ĐO LẠI VÀ KHOÁ LẠI BẰNG CẢ HAI DẠNG
# ══════════════════════════════════════════════════════════════════════════════════════════════
def _do_hai_dang():
    """ĐO THẬT: với mọi khoá MANG MÃ SỐ trong mọi bảng, so dạng SỐ với dạng CHUỖI.

    Nhận CẢ HAI kiểu khoá: `200` (int — bảng hiện tại) và `"200"` (chuỗi-số — đúng hình dạng
    `N-G19-01` mô tả). Nhờ vậy cùng một phép đo bắt được cả bảng thật LẪN bảng đã bị dựng lại
    bằng khoá chuỗi ở ca tự kiểm `C5` — nếu chỉ nhận `int` thì `C5` sẽ "không thấy gì" và hoá ra
    là một phép đo rỗng ruột.
    """
    import trang_thai_hang as tth
    lech, so_khoa_so, so_ma, kieu = [], 0, {}, {}
    for hang, bang in sorted(tth.BANG.items()):
        kieu[hang] = sorted({type(k).__name__ for k in bang})
        for k in sorted(bang, key=str):
            if isinstance(k, bool):
                continue
            if isinstance(k, int):
                so, chuoi = k, str(k)
            elif isinstance(k, str) and k.strip().isdigit():
                so, chuoi = int(k.strip()), k.strip()
            else:
                continue                      # khoá MÔ PHỎNG dạng tên — đo riêng ở `C4`
            so_khoa_so += 1
            so_ma[hang] = so_ma.get(hang, 0) + 1
            a, b = tth.anh_xa(hang, so), tth.anh_xa(hang, chuoi)
            qa, qb = tth.quyet_dinh(hang, so), tth.quyet_dinh(hang, chuoi)
            if (a.biet_ma, a.trang_thai, a.chua_xac_minh, a.nhap_nhang, qa.nhan,
                    qa.trang_thai_ap) != (b.biet_ma, b.trang_thai, b.chua_xac_minh, b.nhap_nhang,
                                          qb.nhan, qb.trang_thai_ap):
                lech.append({"hang": hang, "ma": so,
                             "dang_so": [a.biet_ma, a.trang_thai, qa.nhan, qa.trang_thai_ap],
                             "dang_chuoi": [b.biet_ma, b.trang_thai, qb.nhan, qb.trang_thai_ap]})
    return {"lech": lech, "so_khoa_so": so_khoa_so, "so_ma": so_ma, "kieu_khoa": kieu}


def _do_ma_chua_xac_minh():
    """Mã CHƯA XÁC MINH (`D-4`): cả hai dạng phải ra `NEEDS_REVIEW`, KHÔNG được áp trạng thái."""
    import trang_thai_hang as tth
    xau, so_ma = [], 0
    for (hang, khoa) in sorted(tth.CHUA_XAC_MINH, key=str):
        for dang in (khoa, str(khoa)):
            so_ma += 1
            q = tth.quyet_dinh(hang, dang)
            if q.nhan != "NEEDS_REVIEW" or q.trang_thai_ap is not None \
                    or q.trang_thai_ap in tth.TRANG_THAI_HOAN_TAT:
                xau.append({"hang": hang, "khoa": dang, "nhan": q.nhan,
                            "ap": q.trang_thai_ap})
    return {"xau": xau, "so_lan_do": so_ma}


def _do_ma_la():
    """Mã KHÔNG có trong tài liệu: cả hai dạng ⇒ `biet_ma=False`, `NEEDS_REVIEW`, không áp gì."""
    import trang_thai_hang as tth
    xau, do = [], []
    for hang in sorted(tth.BANG):
        for ma in (999904, "999904", 888801, "888801"):
            q = tth.quyet_dinh(hang, ma)
            a = tth.anh_xa(hang, ma)
            do.append({"hang": hang, "ma": ma, "biet_ma": a.biet_ma, "nhan": q.nhan,
                       "ap": q.trang_thai_ap})
            if a.biet_ma or q.nhan != "NEEDS_REVIEW" or q.trang_thai_ap is not None:
                xau.append(do[-1])
    return {"xau": xau, "so_lan_do": len(do), "mau": do[:4]}


def _do_mock_khong_bi_chuan_hoa_qua_tay():
    """Bộ mô phỏng dùng khoá CHUỖI KHÔNG phải số (`cho_lay`) — chuẩn hoá không được đụng tới."""
    import trang_thai_hang as tth
    xau, do = [], []
    for khoa in sorted(tth.VTP_MA_MOCK):
        a, q = tth.anh_xa("vtp", khoa), tth.quyet_dinh("vtp", khoa)
        do.append({"khoa": khoa, "biet_ma": a.biet_ma, "trang_thai": a.trang_thai})
        if not a.biet_ma or a.trang_thai != khoa:
            xau.append(do[-1])
    return {"xau": xau, "so_khoa": len(do)}


class C_KhoaMaSoChuoi(unittest.TestCase):
    """`N-G19-01`: mã hãng gửi dạng SỐ trượt khoá bảng dạng CHUỖI. Khoá lại bằng CẢ HAI DẠNG."""

    def test_c1_moi_khoa_so_nhan_ra_o_ca_hai_dang(self):
        d = _do_hai_dang()
        self.assertGreaterEqual(d["so_khoa_so"], 20,
                                f"chỉ đo được {d['so_khoa_so']} khoá số ⇒ phép đo vô nghĩa")
        self.assertEqual(d["lech"], [],
                         "còn mã nhận ra ở dạng này mà TRƯỢT ở dạng kia (N-G19-01): "
                         + json.dumps(d["lech"], ensure_ascii=False))
        _dc_am("khoa-so-chuoi")
        _dc_duong("khoa-so-chuoi")
        print(f"\n  [C1] {d['so_khoa_so']} khoá số {d['so_ma']} · kiểu khoá bảng={d['kieu_khoa']} · "
              f"lệch SỐ↔CHUỖI = 0")

    def test_c2_ma_chua_xac_minh_roi_vao_NEEDS_REVIEW_o_ca_hai_dang(self):
        d = _do_ma_chua_xac_minh()
        self.assertGreaterEqual(d["so_lan_do"], 20, "quá ít mã chưa xác minh ⇒ phép đo vô nghĩa")
        self.assertEqual(d["xau"], [],
                         "mã CHƯA XÁC MINH bị ánh xạ bừa hoặc không vào NEEDS_REVIEW: "
                         + json.dumps(d["xau"], ensure_ascii=False))
        _dc_am("chua-xac-minh-needs-review")
        # ĐỐI CHỨNG DƯƠNG: mã ĐÃ có nghĩa (200) thì PHẢI áp được, kẻo "luôn NEEDS_REVIEW" là hằng số
        import trang_thai_hang as tth
        for dang in (200, "200"):
            q = tth.quyet_dinh("vtp", dang)
            self.assertEqual((q.nhan, q.trang_thai_ap), ("OK", "lay_hang"),
                             f"mã 200 dạng {dang!r} không áp được ⇒ phép đo trên là hằng số")
        _dc_duong("chua-xac-minh-needs-review")
        print(f"  [C2] {d['so_lan_do']} lượt đo (12 mã chưa xác minh × 2 dạng): 0 ánh xạ bừa · "
              "đối chứng dương mã 200 vẫn áp được ở cả hai dạng")

    def test_c3_ma_la_vao_NEEDS_REVIEW_o_ca_hai_dang(self):
        d = _do_ma_la()
        self.assertGreaterEqual(d["so_lan_do"], 8, "quá ít lượt đo mã lạ")
        self.assertEqual(d["xau"], [], "mã lạ bị coi là BIẾT hoặc bị áp trạng thái: "
                         + json.dumps(d["xau"], ensure_ascii=False))
        _dc_am("ma-la-needs-review")
        _dc_duong("ma-la-needs-review")
        print(f"  [C3] {d['so_lan_do']} lượt đo mã lạ (4 mã × 2 hãng × 2 dạng): biet_ma=False · "
              f"NEEDS_REVIEW · trạng thái áp=None · mẫu={json.dumps(d['mau'][:2], ensure_ascii=False)}")

    def test_c4_khoa_mo_phong_khong_bi_chuan_hoa_qua_tay(self):
        d = _do_mock_khong_bi_chuan_hoa_qua_tay()
        self.assertGreaterEqual(d["so_khoa"], 5, "sổ khoá mô phỏng rỗng ⇒ ca này không đo gì")
        self.assertEqual(d["xau"], [], "chuẩn hoá số đã ĐỤNG vào khoá mô phỏng: "
                         + json.dumps(d["xau"], ensure_ascii=False))
        _dc_am("mock-khong-bi-dung")
        _dc_duong("mock-khong-bi-dung")
        print(f"  [C4] {d['so_khoa']} khoá MÔ PHỎNG dạng chuỗi-không-số vẫn nguyên nghĩa")

    @unittest.skipIf(NHANH, "VIP_G20_NHANH=1")
    def test_c5_tu_kiem_bang_chuoi_lam_phep_do_DO(self):
        """TỰ KIỂM BỘ ĐO: DỰNG LẠI đúng hình dạng gốc của `N-G19-01` ⇒ phép đo `C1` PHẢI ĐỎ.

        Hai đột biến, cả hai đều là hình dạng THẬT đã xảy ra:
          · `_khoa_ma` trả nguyên giá trị cho `vtp` (đúng mã trước G19) ⇒ `"200"` trượt;
          · bảng dựng lại bằng khoá CHUỖI ⇒ payload SỐ trượt.
        Không đột biến nào ĐOÁN mã: chúng chỉ đổi KIỂU KHOÁ, tức đúng chỗ `N-G19-01` nói tới.
        """
        import trang_thai_hang as tth
        goc_khoa_ma, goc_bang = tth._khoa_ma, tth.BANG

        def _khoa_ma_truoc_g19(ma_hang, ma_trang_thai):
            if ma_hang == "jt":
                try:
                    return int(ma_trang_thai), None
                except (TypeError, ValueError):
                    return None, "scanTypeCode không phải số"
            return ma_trang_thai, None
        try:
            tth._khoa_ma = _khoa_ma_truoc_g19
            tth.BANG = {h: {str(k): v for k, v in b.items()} for h, b in goc_bang.items()}
            d = _do_hai_dang()
            self.assertTrue(d["lech"], "đột biến dựng lại ĐÚNG `N-G19-01` mà phép đo KHÔNG thấy "
                                       "⇒ `C1` là hằng số, không đo gì")
            print(f"  [C5] đột biến `N-G19-01` dựng lại: phép đo thấy {len(d['lech'])} mã lệch "
                  f"⇒ C1 CÓ RĂNG (mẫu: {json.dumps(d['lech'][0], ensure_ascii=False)})")
        finally:
            tth._khoa_ma, tth.BANG = goc_khoa_ma, goc_bang
        d2 = _do_hai_dang()
        self.assertEqual(d2["lech"], [], "khôi phục bảng thất bại ⇒ các ca sau đo trên cây bẩn")
        _dc_am("tu-kiem-n-g19-01")
        _dc_duong("tu-kiem-n-g19-01")

    def test_c6_chot_D4_ma_nhap_nhang_khong_vao_hoan_tat(self):
        """`D-4`: mã chưa chốt nghĩa KHÔNG bao giờ được thành trạng thái HOÀN TẤT."""
        import trang_thai_hang as tth
        xau = []
        for (hang, khoa) in sorted(tth.NHAP_NHANG, key=str):
            for dang in (khoa, str(khoa)):
                q = tth.quyet_dinh(hang, dang)
                if q.nhan not in ("AMBIGUOUS", "NEEDS_REVIEW") \
                        or q.trang_thai_ap in tth.TRANG_THAI_HOAN_TAT:
                    xau.append({"hang": hang, "khoa": dang, "nhan": q.nhan, "ap": q.trang_thai_ap})
        self.assertEqual(xau, [], "mã NHẬP NHẰNG rơi vào trạng thái hoàn tất: "
                         + json.dumps(xau, ensure_ascii=False))
        _dc_am("d4-khong-hoan-tat")
        _dc_duong("d4-khong-hoan-tat")
        print(f"  [C6] {len(tth.NHAP_NHANG)} mã nhập nhằng × 2 dạng: không mã nào vào "
              f"{list(tth.TRANG_THAI_HOAN_TAT)}")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# T. TỰ KIỂM BỘ ĐO — ca CỐ Ý HỎNG chạy trong TIẾN TRÌNH CON
# ══════════════════════════════════════════════════════════════════════════════════════════════
MA_CO_Y_HONG = """import unittest
class T(unittest.TestCase):
    def test_co_y_hong(self):
        self.assertEqual(1, 2, "ca CO Y HONG de kiem bo do")
if __name__ == "__main__":
    unittest.main()
"""

MA_CO_Y_DAT = """import unittest
class T(unittest.TestCase):
    def test_dat(self):
        self.assertTrue(True)
if __name__ == "__main__":
    unittest.main()
"""


class T_TuKiemBoDo(unittest.TestCase):
    """Chốt chặn: bộ chạy PHẢI thấy được một ca hỏng, và PHẢI thấy một ca đạt là đạt."""

    def _ghi_va_chay(self, ten, nguon):
        d = tempfile.mkdtemp(prefix="veh-g20-tukiem-")
        try:
            p = os.path.join(d, ten)
            with open(p, "w", encoding="utf-8") as f:
                f.write(nguon)
            r = subprocess.run([sys.executable, p], capture_output=True, text=True, timeout=120)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_t1_bo_do_thay_ca_co_y_hong(self):
        ma, out = self._ghi_va_chay("thu_co_y_hong.py", MA_CO_Y_HONG)
        self.assertNotEqual(ma, 0, "bộ chạy KHÔNG thấy ca cố ý hỏng ⇒ mọi phán quyết vô hiệu")
        self.assertIn("FAIL:", out, "ca hỏng không sinh dòng FAIL: để đối chiếu")
        _dc_am("tu-kiem-bo-do")
        _dc_duong("tu-kiem-bo-do")
        print(f"  [T1] ca CỐ Ý HỎNG: bộ chạy thấy (mã thoát {ma}, có `FAIL:`)")

    def test_t2_bo_do_thay_ca_dat_la_dat(self):
        ma, out = self._ghi_va_chay("thu_dat.py", MA_CO_Y_DAT)
        self.assertEqual(ma, 0, f"ca ĐẠT mà bộ chạy báo hỏng:\n{out[-500:]}")
        self.assertIn("OK", out, "ca đạt không có dấu vết `OK`")
        print("  [T2] ca ĐẠT: mã thoát 0 · có `OK`")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# Z. TỔNG KẾT
# ══════════════════════════════════════════════════════════════════════════════════════════════
class Z_TongKet(unittest.TestCase):

    def test_z1_moi_nhom_am_deu_co_doi_chung_duong(self):
        thieu = [n for n, o in sorted(DOI_CHUNG.items()) if o["am"] > 0 and o["duong"] == 0]
        self.assertTrue(DOI_CHUNG, "sổ đối chứng RỖNG ⇒ chốt chặn này không đo gì")
        self.assertEqual(thieu, [], f"nhóm có ca PHỦ ĐỊNH mà KHÔNG có ĐỐI CHỨNG DƯƠNG: {thieu}")
        print("\nSỔ ĐỐI CHỨNG DƯƠNG:", json.dumps(DOI_CHUNG, ensure_ascii=False, sort_keys=True))

    def test_z2_khong_con_tep_tam_nao(self):
        """Bộ thử tự dọn: không được để lại tệp tạm / bản sao đột biến nào trong cây."""
        con = []
        for d in (TEP_TAM_SAN_PHAM, TEP_TAM_MOCK, TEP_TAM_GATEWAY):
            if os.path.exists(os.path.join(GOC_CAY, d)):
                con.append(d)
        for bo in BO_THU_DANG_DO:
            p = _duong_ban_sao(bo)
            if os.path.exists(p):
                con.append(os.path.relpath(p, GOC_CAY))
        self.assertEqual(sorted(set(con)), [], f"còn tệp tạm trong cây: {sorted(set(con))}")
        _dc_am("tu-don-dep")
        # ĐỐI CHỨNG DƯƠNG: bộ dò phải THẤY một đường cố ý dựng.
        p = os.path.join(GOC_CAY, TEP_TAM_SAN_PHAM)
        with open(p, "w", encoding="utf-8") as f:
            f.write("# gia\n")
        try:
            self.assertTrue(os.path.exists(p), "không dựng được tệp giả để đối chứng")
        finally:
            os.remove(p)
        _dc_duong("tu-don-dep")
        print("  [Z2] 0 tệp tạm còn lại (bộ dò bắt được tệp giả vừa dựng)")

    def test_z3_vet_cay_khong_doi_trong_luot_do(self):
        """Vân tay cây (ngoài phạm vi wave) phải ĐỨNG YÊN suốt lượt đo."""
        h = hashlib.sha256(("\n".join(_loc_cay_ban(
            _git("status", "--porcelain=v1", "-uall").stdout.splitlines())) + "\n"
        ).encode("utf-8")).hexdigest()
        self.assertEqual(h, VAN_TAY_CUOI, "cây ĐỔI giữa lượt đo ⇒ mọi số đo phải coi là vô hiệu")
        _dc_am("vet-cay-dung-yen")
        _dc_duong("vet-cay-dung-yen")
        print(f"  [Z3] vân tay cây ngoài phạm vi wave không đổi: {h[:16]}…")

    def test_z4_pham_vi_da_do_va_cai_nam_ngoai(self):
        _dc_duong("pham-vi")
        print("\n  [Z4] PHẠM VI ĐÃ ĐO: %s %s · python %s · SQLite %s · CSDL=%s"
              % (os.uname().sysname, os.uname().machine,
                 ".".join(map(str, sys.version_info[:3])), __import__("sqlite3").sqlite_version,
                 _TAM))
        print("       CHẾ ĐỘ: %s" % ("NHANH (bỏ nhóm đột biến)" if NHANH else "ĐẦY ĐỦ"))
        print("       KHÔNG GỌI HÃNG (kể cả sandbox — V-G09-01/V-13906-05 CHƯA CẤP) · "
              "không mở cổng · không push/deploy/tunnel · không mở CHO_PHEP_LIVE")
        print("       NGOÀI PHẠM VI: TLS thật · webhook thật · PostgreSQL production "
              f"(:{CONG_CAM} CHẶN CỨNG) · giao diện/Chromium · hãng thứ ba ngoài jt/vtp · "
              "`thu_qa_g19.py` (bản sao thứ ba của lỗi cây sạch — NGOÀI phạm vi được cấp, chỉ ĐO)")


VAN_TAY_CUOI = hashlib.sha256(("\n".join(_loc_cay_ban(
    _git("status", "--porcelain=v1", "-uall").stdout.splitlines())) + "\n").encode("utf-8")
).hexdigest()


if __name__ == "__main__":
    print("NỀN ĐO: HEAD=%s · ghim=%s" % (_git("rev-parse", "HEAD").stdout.strip(),
                                         HEAD_GHIM or "KHÔNG"))
    print("PHẠM VI: chỉ đọc cây + gọi git · KHÔNG cổng mạng · KHÔNG gọi hãng · CSDL tạm %s" % _TAM)
    unittest.main(verbosity=2)
