#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22/X1 — ĐO LẠI "0 CA": BỘ THỬ CHẾT TRƯỚC KHI CHẠY CA NÀO THÌ PHẢI BỊ BẮT.

VÌ SAO CÓ TỆP NÀY
-----------------
`sh app/thu/chay_tat_ca.sh` trên SHA `6949d8c` in ra:

    1961 ca · 69 bộ · EXIT=1 · 30 bộ đỏ

Trong đó **12 bộ in ra `0 ca`**. Nhưng "0 ca" là một con số KHÔNG NÓI VÌ SAO, và nó gộp
BỐN thứ khác hẳn nhau dưới cùng một nhãn:

    (1) bộ CHẾT THẬT trước khi chạy ca nào (import hỏng, migrate TỪ CHỐI, thiếu Chromium);
    (2) bộ CHẠY RỒI nhưng khuôn báo cáo không khớp hai `grep` của bộ chạy chung
        (ví dụ `TỔNG: 32 ca — HỎNG` không khớp `Ran N` lẫn `N ca — ĐẠT`);
    (3) bộ thoát 0 mà KHÔNG có dấu vết đã chạy ca nào — XANH GIẢ, hướng sai nguy hiểm nhất;
    (4) bộ tự bỏ qua có chủ đích (in `skipped`).

Một bộ chạy gộp bốn thứ ấy vào `0 ca` thì người đọc không biết bộ nào CHẾT, bộ nào CHẠY,
bộ nào XANH GIẢ. Tệp này là phép đo THỨ HAI, độc lập với `chay_tat_ca.sh`: nó chạy lại
từng bộ, đọc mã thoát + số ca + dấu vết, rồi PHÂN LOẠI. Mục tiêu không phải "bắt bộ đỏ
cho đẹp bảng" — bộ chạy chung đã bắt đỏ rồi — mà là **đo lại được khi một bộ chết mà
không ai biết**, và tách "chết" khỏi "chạy rồi mới hỏng".

BỐN PHÁN QUYẾT (mỗi bộ đúng một cái)
------------------------------------
    DAT              mã thoát 0  · số ca > 0
    HONG             mã thoát ≠ 0 · số ca > 0   ← CHẠY RỒI mới hỏng, KHÔNG phải 0 ca
    BO_QUA           mã thoát 0  · số ca = 0 · output có `skipped` (bỏ qua có chủ đích)
    TU_CHOI          số ca = 0 · output có `TỪ CHỐI` / `CHƯA KHAI` (tự chối vì thiếu khai)
    THIEU_PHU_THUOC  số ca = 0 · output có `ModuleNotFoundError` / `.local-browsers` / Chromium
    CHET_0CA         số ca = 0 · các trường hợp chết còn lại
    XANH_GIA_0CA     mã thoát 0  · số ca = 0 · KHÔNG `skipped` ← LUÔN là HỎNG
    QUA_HAN          quá thời gian chờ

`XANH_GIA_0CA` là phán quyết mà `chay_tat_ca.sh` ĐÃ bắt đúng (dòng "thoát 0 nhưng KHÔNG
có dấu vết đã chạy ca nào"). Tệp này không thay nó; nó đo lại ĐỘC LẬP và giữ cùng luật.

SỔ GHIM (`SO_CA_GHIM`) — điều kiện để "đo lại" có nghĩa
------------------------------------------------------
Một phép đo lại chỉ có nghĩa khi có MỐC để so. Sổ dưới đây ghim, cho từng bộ, **số ca đã
đo được** và phán quyết tại SHA `6949d8c` — sinh từ chính bảng của `chay_tat_ca.sh` ở lượt
đó, với MỘT chỗ sửa: `thu_g22_gioihan.py` ghim **32 ca** (đo trực tiếp), không phải 0, vì
bộ chạy chung đếm sai khuôn của nó. Sổ là DỮ KIỆN ĐÃ ĐO, không phải kỳ vọng đẹp.

Luật so sánh — cố ý BẤT ĐỐI XỨNG:
  * bộ TỪNG CHẠY > 0 ca nay còn 0 ca            ⇒ **HỎNG** (chết im lặng — đây là mục tiêu);
  * bộ thoát 0 mà 0 ca (xanh giả)               ⇒ **HỎNG** (luôn luôn);
  * bộ TỪNG 0 ca nay chạy > 0 ca                ⇒ **HỒI SINH** (mốc cũ, không phải lỗi);
  * số ca đổi nhưng vẫn > 0                     ⇒ **CẢNH BÁO** (không phải chết).
Hướng "nhiều ca hơn" KHÔNG bị phạt: nó chỉ làm mốc cũ đi. Hướng "0 ca" bị phạt.

CHẠY
----
    python3 app/thu/thu_g22_zeroca.py                  # TỰ KIỂM bộ dò (nhanh, dùng unittest)
    python3 app/thu/thu_g22_zeroca.py --do-lai         # đo lại 12 bộ đã biết (≈25 giây)
    python3 app/thu/thu_g22_zeroca.py --do-lai --khai-kho
                                                       # đo lại sau khi khai VIP_KHO_DANG_CHAY=sqlite
    python3 app/thu/thu_g22_zeroca.py --bo thu_giao_dich.py      # đo MỘT bộ, in đầu đuôi
    python3 app/thu/thu_g22_zeroca.py --tat-ca          # đo lại TOÀN BỘ bộ thử theo sổ ghim
    python3 app/thu/thu_g22_zeroca.py --do-lai --json /tmp/zeroca.json

MÃ THOÁT
--------
    0 KHỚP mốc (mọi bộ còn đúng chỗ cũ)        1 CÓ BỘ CHẾT MỚI / XANH GIẢ / QUÁ HẠN
    2 Mốc CŨ: có bộ hồi sinh (cần cập nhật sổ)   3 Lỗi dùng / không tìm thấy bộ

GIỚI HẠN — NÓI TRƯỚC
--------------------
* Bộ này KHÔNG sửa bộ thử nào, KHÔNG sửa mã sản phẩm, KHÔNG đụng CSDL thật: mọi tiến trình
  con chạy trong thư mục tạm của chính bộ thử đó. Chạy trên máy local, không gọi ra mạng.
* Nó đo lại **hành vi**, không đọc mã để đoán. Vì thế nó chỉ trả lời được "bộ này có chạy
  ca nào không / chạy rồi hỏng hay chết trước", KHÔNG trả lời "vì sao sản phẩm hỏng".
* Số ca là con số bộ thử TỰ CÔNG BỐ (khớp `Ran N`, `N ca — ĐẠT/HỎNG`, `TỔNG: N ca`). Một
  bộ in số ca SAI thì bộ này đọc sai theo — cùng giới hạn với `chay_tat_ca.sh`; khác biệt
  là nó đọc thêm khuôn thứ ba (`TỔNG: N ca`) và lấy số LỚN NHẤT trong các khuôn khớp.
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
import time
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THU_MUC = os.path.join(GOC, "app", "thu")
SHA_GHIM = "6949d8c567320993d72bb8156dc226acf90bddfe"

# 12 bộ in `0 ca` trong bảng của `chay_tat_ca.sh` tại SHA 6949d8c — danh sách của đề bài,
# giữ nguyên thứ tự để đối chiếu được với báo cáo `docs/G22_ZERO_CA_DIAG.md`.
DS_12 = (
    "thu_bien_driver.py",
    "thu_g17_baomat.py",
    "thu_g18_maysrv.py",
    "thu_g18_multiprocess.py",
    "thu_g19_gioihan.py",
    "thu_g21_gioihan.py",
    "thu_g22_gioihan.py",
    "thu_giao_dich.py",
    "thu_han_muc_nguyen_tu.py",
    "thu_header_bao_mat.py",
    "thu_truy_van.py",
    "thu_g22_e2e.py",
)

# Sổ ghim 12 bộ: (phán quyết, số ca) tại SHA 6949d8c.
#   · "khong_khai" : môi trường NGUYÊN VĂN như `chay_tat_ca.sh` (KHÔNG đặt VIP_KHO_DANG_CHAY).
#   · "khai_kho"   : đặt `VIP_KHO_DANG_CHAY=sqlite` — đo ngày 18/10/2026, xem báo cáo §4.
SO_CA_GHIM = {
    "khong_khai": {
        "thu_bien_driver.py": ("CHET_0CA", 0),          # AssertionError: migrate.py dòng [26]
        "thu_g17_baomat.py": ("TU_CHOI", 0),            # migrate TỪ CHỐI trong ca e4
        "thu_g18_maysrv.py": ("TU_CHOI", 0),            # setUpModule: migrate hỏng
        "thu_g18_multiprocess.py": ("TU_CHOI", 0),
        "thu_g19_gioihan.py": ("TU_CHOI", 0),
        "thu_g21_gioihan.py": ("TU_CHOI", 0),
        "thu_g22_gioihan.py": ("HONG", 32),             # CHẠY 32 ca, 5 đỏ — KHÔNG chết
        "thu_giao_dich.py": ("TU_CHOI", 0),
        "thu_han_muc_nguyen_tu.py": ("TU_CHOI", 0),
        "thu_header_bao_mat.py": ("TU_CHOI", 0),
        "thu_truy_van.py": ("TU_CHOI", 0),
        "thu_g22_e2e.py": ("THIEU_PHU_THUOC", 0),       # thiếu Chromium ghim 1194
    },
    "khai_kho": {
        "thu_bien_driver.py": ("CHET_0CA", 0),          # không liên quan biến khai kho
        "thu_g17_baomat.py": ("HONG", 31),              # 31 ca · 1 đỏ THẬT (route loc-mo-ta)
        "thu_g18_maysrv.py": ("DAT", 17),
        "thu_g18_multiprocess.py": ("DAT", 26),
        "thu_g19_gioihan.py": ("DAT", 22),
        "thu_g21_gioihan.py": ("DAT", 22),
        "thu_g22_gioihan.py": ("HONG", 32),             # 32 ca · 3 đỏ THẬT (cổng C5)
        "thu_giao_dich.py": ("DAT", 17),
        "thu_han_muc_nguyen_tu.py": ("DAT", 5),
        "thu_header_bao_mat.py": ("DAT", 8),
        "thu_truy_van.py": ("DAT", 40),
        "thu_g22_e2e.py": ("THIEU_PHU_THUOC", 0),
    },
}

# Sổ ghim TOÀN BỘ bộ thử (69 bộ Python trong bảng `chay_tat_ca.sh` + `thu_gateway.py`).
# Khoá = tên tệp, giá trị = (phán quyết đã đo, số ca đã đo) tại SHA 6949d8c.
# Chỉ dùng cho `--tat-ca`; ở đó số ca > 0 là ĐIỀU KIỆN SỐNG, không phải điểm số đẹp.
# `thu_g22_gioihan.py` ghim 32 (đo trực tiếp), KHÔNG phải 0 như bảng của bộ chạy chung.
SO_CA_TOAN_BO = {
    "thu_adapter_jt.py": ("DAT", 84),
    "thu_ai_job.py": ("DAT", 87),
    "thu_anh_xa_area.py": ("DAT", 16),
    "thu_bao_mat.py": ("HONG", 57),
    "thu_bien_driver.py": ("HONG", 0),
    "thu_doi_soat.py": ("DAT", 27),
    "thu_don_hang.py": ("DAT", 66),
    "thu_g01_g02.py": ("HONG", 21),
    "thu_g03.py": ("DAT", 53),
    "thu_g17_baomat.py": ("HONG", 0),
    "thu_g18_bi_mat.py": ("DAT", 15),
    "thu_g18_crash.py": ("DAT", 31),
    "thu_g18_maysrv.py": ("HONG", 0),
    "thu_g18_multiprocess.py": ("HONG", 0),
    "thu_g19_gioihan.py": ("HONG", 0),
    "thu_g19_route.py": ("HONG", 14),
    "thu_g19_tich_hop.py": ("HONG", 8),
    "thu_g19_vtp.py": ("DAT", 31),
    "thu_g19c6_v10.py": ("DAT", 10),
    "thu_g20_baomat.py": ("HONG", 28),
    "thu_g20_dahang.py": ("HONG", 27),
    "thu_g20_hop_dong.py": ("DAT", 36),
    "thu_g20_saoluu.py": ("HONG", 41),
    "thu_g21_bimat.py": ("HONG", 33),
    "thu_g21_chotcay.py": ("DAT", 13),
    "thu_g21_gioihan.py": ("HONG", 0),
    "thu_g21_saoluu.py": ("HONG", 23),
    "thu_g22_a1.py": ("DAT", 5),
    "thu_g22_bimat.py": ("HONG", 23),
    "thu_g22_cauhinh.py": ("DAT", 17),
    "thu_g22_chotcay.py": ("HONG", 11),
    "thu_g22_e2e.py": ("HONG", 0),
    "thu_g22_gioihan.py": ("HONG", 32),
    "thu_g22_regression.py": ("DAT", 35),
    "thu_g22_saoluu.py": ("DAT", 14),
    "thu_giao_dich.py": ("HONG", 0),
    "thu_gioi_han.py": ("DAT", 34),
    "thu_goi_dich_vu.py": ("DAT", 37),
    "thu_han_muc_nguyen_tu.py": ("HONG", 0),
    "thu_harness_hang.py": ("DAT", 57),
    "thu_header_bao_mat.py": ("HONG", 0),
    "thu_hop_dong_jt.py": ("DAT", 84),
    "thu_http_jt.py": ("DAT", 57),
    "thu_ma_la_hang.py": ("DAT", 6),
    "thu_migrate_dong_thoi.py": ("HONG", 8),
    "thu_nhap_file.py": ("DAT", 21),
    "thu_nhat_ky_yeu_cau.py": ("BO_QUA", 0),
    "thu_postgres.py": ("DAT", 55),
    "thu_qa_g16.py": ("DAT", 61),
    "thu_qa_g17.py": ("HONG", 56),
    "thu_qa_g18_tich_hop.py": ("HONG", 26),
    "thu_qa_g18.py": ("HONG", 47),
    "thu_qa_g19_tich_hop.py": ("HONG", 8),
    "thu_qa_g19.py": ("DAT", 29),
    "thu_qa_g20.py": ("DAT", 21),
    "thu_qa_g21.py": ("DAT", 24),
    "thu_qa_g22.py": ("HONG", 29),
    "thu_qa_jt.py": ("DAT", 22),
    "thu_qa_soat.py": ("HONG", 30),
    "thu_qa2_soat.py": ("DAT", 49),
    "thu_quan_sat.py": ("DAT", 45),
    "thu_saas.py": ("DAT", 19),
    "thu_tai_chinh.py": ("DAT", 51),
    "thu_tich_hop.py": ("DAT", 12),
    "thu_truy_van.py": ("HONG", 0),
    "thu_usage.py": ("DAT", 41),
    "thu_webhook_jt.py": ("DAT", 99),
    "thu_webhook.py": ("DAT", 68),
    "thu_xoay_khoa.py": ("DAT", 30),
    "thu_gateway.py": ("DAT", 9),
}

MAU_SO_CA = (
    re.compile(r"Ran (\d+) tests?"),                 # khuôn unittest
    re.compile(r"(\d+) ca — (?:ĐẠT|HỎNG)"),          # khuôn bộ thử viết tay
    re.compile(r"TỔNG: (\d+) ca"),                   # khuôn bảng tổng (g22_gioihan)
)

MAU_THIEU_PHU_THUOC = re.compile(
    r"KHÔNG có binary Chromium|\.local-browsers|ModuleNotFoundError|No module named|"
    r"^ImportError:", re.M)
# `TỪ CHỐI:` bị CẮT ĐUÔI ở một số bộ: chúng nhúng 400 ký tự CUỐI của stderr vào
# `RuntimeError`, nên phần đầu (chứa chữ "TỪ CHỐI:") mất, chỉ còn câu hướng dẫn
# "khai `sqlite` ..." — vẫn là cùng một sự kiện, nên khuôn phải bắt cả hai dạng.
MAU_TU_CHOI = re.compile(
    r"TỪ CHỐI:|CHƯA KHAI kho đang chạy|khai `sqlite`|khai_kho_kiem_thu\(\)")
MAU_DONG_LOI = re.compile(
    r"^(?:ERROR:|FAIL:|✗|[A-Za-z_][\w.]*(?:Error|Exception):|\[migrate\] TỪ CHỐI|"
    r"\[cau_hinh\] TỪ CHỐI|KHÔNG có binary Chromium)")
MAU_DONG_LOI_DU_PHONG = re.compile(
    r"^(?:Traceback \(most recent call last\)|FAILED)")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. MÔI TRƯỜNG — cùng luật với `chay_tat_ca.sh` / `thu_g21_chotcay.py`
# ══════════════════════════════════════════════════════════════════════════════════════════════
def moi_truong_git_sach():
    """Trả (env, cảnh báo). Gỡ `GIT_CONFIG_*` CHỈ KHI dị dạng (`N-G18-00`).

    Sao chép LUẬT, không sao chép mã: `GIT_CONFIG_COUNT=N` thiếu `GIT_CONFIG_KEY_*` làm MỌI
    lệnh git thoát 128. Gỡ im lặng là che một môi trường hỏng, nên có cảnh báo.
    """
    env = dict(os.environ)
    canh_bao = []
    dem = env.get("GIT_CONFIG_COUNT", "")
    if dem.isdigit() and int(dem) > 0:
        thieu = [i for i in range(int(dem)) if not env.get("GIT_CONFIG_KEY_%d" % i)]
        if thieu:
            canh_bao.append(
                "GIT_CONFIG_COUNT=%s nhưng thiếu GIT_CONFIG_KEY_%s — đã gỡ gia đình "
                "GIT_CONFIG_*" % (dem, ",".join(map(str, thieu))))
            for ten in [k for k in env if k.startswith("GIT_CONFIG_")]:
                env.pop(ten, None)
    return env, canh_bao


def head_hien_tai():
    """`git rev-parse HEAD` với môi trường đã sửa; trả `None` nếu không đọc được."""
    env, _ = moi_truong_git_sach()
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=GOC, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. BỘ ĐO — chạy MỘT bộ thử, đọc mã thoát + số ca + dấu vết, rồi phân loại
# ══════════════════════════════════════════════════════════════════════════════════════════════
def dem_ca(out):
    """Số ca bộ thử TỰ CÔNG BỐ. Lấy số LỚN NHẤT khớp, không lấy lần cuối.

    Vì sao khác `chay_tat_ca.sh`: bộ chạy chung lấy lần CUỐI của `Ran N` — đúng cho một dòng
    `Ran N` duy nhất, nhưng mù với khuôn `TỔNG: N ca` (nên `thu_g22_gioihan.py` bị ghi 0 dù
    chạy 32 ca). Ở đây câu hỏi là "bộ có chạy ca NÀO không", nên số LỚN NHẤT là câu trả lời
    đúng hướng: một dòng `Ran 0` in sau không xoá được 32 ca đã chạy.
    """
    so = []
    for mau in MAU_SO_CA:
        for m in mau.finditer(out):
            try:
                so.append(int(m.group(1)))
            except (TypeError, ValueError):
                pass
    return max(so) if so else 0


def dong_loi_dau(out):
    """Dòng đầu tiên TRÔNG GIỐNG LỖI; không có thì trả chuỗi rỗng.

    Cố ý KHÔNG lấy "dòng không rỗng đầu tiên": bộ ĐẠT in dòng tiến trình bình thường, gán nó
    vào cột "lỗi" là gieo một dòng đỏ giả vào báo cáo.
    """
    for mau in (MAU_DONG_LOI, MAU_DONG_LOI_DU_PHONG):
        for ln in out.splitlines():
            if mau.match(ln.strip()):
                return ln.strip()[:300]
    return ""


def phan_loai(ma, so_ca, out, qua_han=False):
    """Trả (phán quyết, bằng chứng ngắn). Thứ tự xét là THỨ TỰ NHÂN QUẢ, không phải thứ tự đẹp."""
    if qua_han:
        return "QUA_HAN", "vượt thời gian chờ"
    if so_ca > 0:
        return ("DAT", "%d ca · mã thoát 0" % so_ca) if ma == 0 else \
               ("HONG", "%d ca · mã thoát %s" % (so_ca, ma))
    # EXIT 0 + 0 CA là XANH GIẢ **bất kể output nói gì** — trừ khi bỏ qua có chủ đích.
    # Xét trước các nhãn "có lý do" để một bộ vừa in `TỪ CHỐI` vừa thoát 0 không được
    # khoan hồng: thoát 0 mà không chạy ca nào là hướng sai nguy hiểm nhất, không có ngoại lệ.
    if ma == 0:
        if "skipped" in out:
            return "BO_QUA", "0 ca · bỏ qua có chủ đích (có `skipped`)"
        return "XANH_GIA_0CA", "mã thoát 0 nhưng KHÔNG có dấu vết đã chạy ca nào"
    if MAU_THIEU_PHU_THUOC.search(out):
        return "THIEU_PHU_THUOC", "0 ca · thiếu phụ thuộc (Chromium/module)"
    if MAU_TU_CHOI.search(out):
        return "TU_CHOI", "0 ca · bộ/migrate TỪ CHỐI vì thiếu KHAI BÁO"
    return "CHET_0CA", "0 ca · chết trước ca đầu (mã thoát %s)" % ma


def do_bo(duong, ten=None, env_them=None, giay=300):
    """Chạy MỘT bộ thử bằng đúng thứ tự `python3 <đường>` của `chay_tat_ca.sh`."""
    ten = ten or os.path.basename(duong)
    env, canh_bao = moi_truong_git_sach()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env_them:
        for k, v in env_them.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
    bd = time.time()
    qua_han = False
    try:
        r = subprocess.run([sys.executable, duong], cwd=GOC, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, timeout=giay)
        ma, out = r.returncode, r.stdout or ""
    except subprocess.TimeoutExpired as e:
        qua_han = True
        ma = 124
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
    except OSError as e:
        qua_han = False
        ma = 125
        out = "%s: %s" % (type(e).__name__, e)
    giay = round(time.time() - bd, 2)
    so_ca = dem_ca(out)
    pl, bang_chung = phan_loai(ma, so_ca, out, qua_han)
    return {
        "ten": ten,
        "duong": duong,
        "ma": ma,
        "so_ca": so_ca,
        "phan_loai": pl,
        "bang_chung": bang_chung,
        "dong_loi_dau": dong_loi_dau(out),
        "giay": giay,
        "qua_han": qua_han,
        "canh_bao_git": canh_bao,
        "ra": out,
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. BỘ SO SÁNH — bất đối xứng có chủ đích (xem đầu tệp)
# ══════════════════════════════════════════════════════════════════════════════════════════════
def so_sanh(kq, ky_vong):
    """Trả (kết luận, ghi chú). `ky_vong` = (phán quyết, số ca) hoặc `None`."""
    if kq["phan_loai"] == "XANH_GIA_0CA":
        return "FAIL", "XANH GIẢ: thoát 0 mà không có dấu vết chạy ca nào"
    if kq["phan_loai"] == "QUA_HAN":
        return "FAIL", "quá hạn — không đo được"
    if ky_vong is None:
        return "MOI", "không có trong sổ ghim (bộ mới?)"
    pl_ghim, ca_ghim = ky_vong
    if ca_ghim > 0 and kq["so_ca"] == 0:
        return "FAIL", "từng chạy %d ca, NAY 0 CA (%s) — chết im lặng" % (ca_ghim, kq["phan_loai"])
    if ca_ghim == 0 and kq["so_ca"] > 0:
        return "HOI_SINH", "mốc ghim 0 ca, nay %d ca — sổ cũ, không phải lỗi" % kq["so_ca"]
    if ca_ghim > 0 and kq["so_ca"] != ca_ghim:
        return "CANH_BAO", "số ca đổi: ghim %d · đo %d" % (ca_ghim, kq["so_ca"])
    if kq["phan_loai"] != pl_ghim:
        return "CANH_BAO", "phân loại đổi: ghim %s · đo %s" % (pl_ghim, kq["phan_loai"])
    return "KHOP", ""


def in_bang(ket_qua):
    print("%-30s %-6s %-5s %-16s %s" % ("BỘ", "EXIT", "SỐ CA", "PHÁN QUYẾT", "KẾT LUẬN"))
    print("-" * 110)
    for kq in ket_qua:
        kl, ghi_chu = kq["ket_luan"], kq["ghi_chu"]
        print("%-30s %-6s %-5d %-16s %s%s" % (
            kq["ten"], kq["ma"], kq["so_ca"], kq["phan_loai"], kl,
            (" — " + ghi_chu) if ghi_chu else ""))
        if kq["dong_loi_dau"]:
            print("%34s↳ %s" % ("", kq["dong_loi_dau"][:160]))
    print("-" * 110)


def ghi_json(duong, du_lieu):
    with open(duong, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)
    print("[json] đã ghi %s" % duong)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CHẾ ĐỘ `--do-lai`: đo lại 12 bộ đã biết, so với sổ ghim
# ══════════════════════════════════════════════════════════════════════════════════════════════
def chay_do_lai(ds, so_ghim, khai_kho, giay, json_duong):
    env_them = {"VIP_KHO_DANG_CHAY": "sqlite"} if khai_kho else {"VIP_KHO_DANG_CHAY": None}
    ket_qua = []
    print("═══ ĐO LẠI %d BỘ · chế độ: %s ═══" % (
        len(ds), "KHAI KHO (VIP_KHO_DANG_CHAY=sqlite)" if khai_kho else "NGUYÊN VĂN (chưa khai kho)"))
    for ten in ds:
        duong = os.path.join(THU_MUC, ten)
        if not os.path.isfile(duong):
            kq = {"ten": ten, "ma": None, "so_ca": 0, "phan_loai": "KHONG_CO_TEP",
                  "bang_chung": "không tìm thấy tệp", "dong_loi_dau": "",
                  "giay": 0, "qua_han": False, "canh_bao_git": [], "ra": ""}
        else:
            kq = do_bo(duong, env_them=env_them, giay=giay)
        kl, ghi_chu = so_sanh(kq, so_ghim.get(ten))
        if kq["phan_loai"] == "KHONG_CO_TEP":
            kl, ghi_chu = "FAIL", "KHÔNG CÓ TỆP %s" % duong
        kq["ket_luan"], kq["ghi_chu"] = kl, ghi_chu
        ket_qua.append(kq)
        print("  → %-30s %s · %s" % (ten, kq["phan_loai"], kl))
    print()
    in_bang(ket_qua)
    dem = {}
    for kq in ket_qua:
        dem[kq["ket_luan"]] = dem.get(kq["ket_luan"], 0) + 1
    print("TỔNG KẾT: " + " · ".join("%s=%d" % (k, dem[k]) for k in sorted(dem)))
    if json_duong:
        ghi_json(json_duong, {
            "sha_ghim": SHA_GHIM, "sha_do": head_hien_tai(),
            "che_do": "khai_kho" if khai_kho else "khong_khai",
            "bo": [{k: v for k, v in kq.items() if k != "ra"} for kq in ket_qua],
            "tong_ket": dem,
        })
    if dem.get("FAIL"):
        return 1
    if dem.get("HOI_SINH"):
        return 2
    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. CHẾ ĐỘ `--tat-ca`: đo lại MỌI bộ theo sổ ghim toàn bộ — "chết mà không ai biết"
# ══════════════════════════════════════════════════════════════════════════════════════════════
def ds_bo_that():
    """Dò như `chay_tat_ca.sh`: `app/thu` + `gateway/thu`, trừ `thu_e2e.py`; trừ CHÍNH bộ này."""
    ds = []
    for goc in (os.path.join(GOC, "app", "thu"), os.path.join(GOC, "gateway", "thu")):
        if not os.path.isdir(goc):
            continue
        for ten in sorted(os.listdir(goc)):
            if not (ten.startswith("thu_") and ten.endswith(".py")):
                continue
            duong = os.path.join(goc, ten)
            # Bỏ `thu_e2e.py` (bộ chạy chung cũng bỏ) và CHÍNH bộ này — so theo realpath,
            # không theo tên, để bản sao đổi tên không tự chạy chính nó.
            if ten == "thu_e2e.py" or os.path.realpath(duong) == os.path.realpath(__file__):
                continue
            ds.append((ten, duong))
    return ds


def chay_tat_ca(khai_kho, giay, json_duong):
    env_them = {"VIP_KHO_DANG_CHAY": "sqlite"} if khai_kho else {"VIP_KHO_DANG_CHAY": None}
    ds = ds_bo_that()
    ket_qua = []
    print("═══ ĐO LẠI TOÀN BỘ %d BỘ · chế độ: %s ═══" % (
        len(ds), "KHAI KHO" if khai_kho else "NGUYÊN VĂN"))
    for ten, duong in ds:
        kq = do_bo(duong, env_them=env_them, giay=giay)
        kl, ghi_chu = so_sanh(kq, SO_CA_TOAN_BO.get(ten))
        # Ở chế độ toàn bộ, "hồi sinh" KHÔNG phải lỗi: nó chỉ làm sổ cũ đi. Chỉ giữ FAIL
        # (chết im lặng / xanh giả / quá hạn) và ghi nhận mọi thay đổi khác.
        if kl == "HOI_SINH":
            kl, ghi_chu = "CANH_BAO", ghi_chu
        kq["ket_luan"], kq["ghi_chu"] = kl, ghi_chu
        ket_qua.append(kq)
        print("  %-4s %-30s %3d ca · %s" % ("OK" if kl == "KHOP" else kl[:4], ten,
                                            kq["so_ca"], kq["phan_loai"]))
    print()
    in_bang(ket_qua)
    dem = {}
    for kq in ket_qua:
        dem[kq["ket_luan"]] = dem.get(kq["ket_luan"], 0) + 1
    tong_ca = sum(kq["so_ca"] for kq in ket_qua)
    print("TỔNG KẾT: %d bộ · %d ca · " % (len(ket_qua), tong_ca)
          + " · ".join("%s=%d" % (k, dem[k]) for k in sorted(dem)))
    if json_duong:
        ghi_json(json_duong, {
            "sha_ghim": SHA_GHIM, "sha_do": head_hien_tai(),
            "che_do": "khai_kho" if khai_kho else "khong_khai",
            "bo": [{k: v for k, v in kq.items() if k != "ra"} for kq in ket_qua],
            "tong_ca": tong_ca, "tong_ket": dem,
        })
    return 1 if dem.get("FAIL") else 0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. TỰ KIỂM — chứng minh bộ dò BẮT ĐƯỢC và KHÔNG bắt nhầm
# ══════════════════════════════════════════════════════════════════════════════════════════════
MAU_BO_GIA = {
    # (tên, mã nguồn, phán quyết phải ra, số ca phải ra)
    "khoe": (
        'import sys\nprint("Ran 3 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n', "DAT", 3),
    "khoe_viet_tay": (
        'import sys\nprint("17 ca — ĐẠT")\nsys.exit(0)\n', "DAT", 17),
    "hong_that": (
        'import sys\nprint("Ran 5 tests in 0.01s")\nprint("FAILED (failures=1)")\nsys.exit(1)\n',
        "HONG", 5),
    "hong_khuon_tong": (
        'import sys\nprint("ca ĐẠT=27 · HỎNG=5 · TỔNG=32")\n'
        'print("TỔNG: 32 ca — HỎNG")\nsys.exit(1)\n', "HONG", 32),
    "chet_import": (
        'raise ImportError("No module named \'xyz_khong_ton_tai\'")\n', "THIEU_PHU_THUOC", 0),
    "chet_tu_choi": (
        'import sys\nprint("[migrate] TỪ CHỐI: CHƯA KHAI kho đang chạy")\nsys.exit(1)\n',
        "TU_CHOI", 0),
    "chet_truoc_ca": (
        'import sys\nprint("Traceback (most recent call last):")\n'
        'print("AssertionError: hỏng trước ca đầu")\nsys.exit(1)\n', "CHET_0CA", 0),
    "xanh_gia_khong_in_gi": (
        'import sys\nsys.exit(0)\n', "XANH_GIA_0CA", 0),
    "xanh_gia_ran_0": (
        'import sys\nprint("Ran 0 tests in 0.00s")\nprint("OK")\nsys.exit(0)\n',
        "XANH_GIA_0CA", 0),
    "thieu_chromium": (
        'import sys\nprint("KHÔNG có binary Chromium: …/chromium_headless_shell-1194/'
        'chrome-mac/headless_shell")\nsys.exit(2)\n', "THIEU_PHU_THUOC", 0),
}


def _chay_ma_gia(ma_nguon, ten):
    d = tempfile.mkdtemp(prefix="veh-zeroca-gia-")
    try:
        p = os.path.join(d, ten + ".py")
        with open(p, "w", encoding="utf-8") as f:
            f.write(ma_nguon)
        return do_bo(p, ten=ten + ".py", giay=60)
    finally:
        shutil.rmtree(d, ignore_errors=True)


class TuKiem(unittest.TestCase):
    """Mỗi ca kiểm MỘT tính chất của bộ dò. Có cả ca ÂM (không được bắt nhầm)."""

    def test_01_khoe_thi_KHONG_bi_bat(self):
        """ĐỐI CHỨNG ÂM: bộ khoẻ phải ra DAT, không bị gắn cờ 0 ca."""
        kq = _chay_ma_gia(MAU_BO_GIA["khoe"][0], "khoe")
        self.assertEqual(kq["phan_loai"], "DAT")
        self.assertEqual(kq["so_ca"], 3)

    def test_02_khoe_khuon_viet_tay(self):
        kq = _chay_ma_gia(MAU_BO_GIA["khoe_viet_tay"][0], "khoe_viet_tay")
        self.assertEqual((kq["phan_loai"], kq["so_ca"]), ("DAT", 17))

    def test_03_hong_that_KHONG_bi_goi_la_0_ca(self):
        """ĐỐI CHỨNG ÂM thứ hai: chạy 5 ca rồi hỏng KHÔNG phải '0 ca'."""
        kq = _chay_ma_gia(MAU_BO_GIA["hong_that"][0], "hong_that")
        self.assertEqual((kq["phan_loai"], kq["so_ca"]), ("HONG", 5))

    def test_04_khuon_TONG_van_dem_duoc_ca(self):
        """Đúng lỗi của `thu_g22_gioihan.py`: in `TỔNG: 32 ca — HỎNG` mà bộ chạy chung đọc 0."""
        kq = _chay_ma_gia(MAU_BO_GIA["hong_khuon_tong"][0], "hong_khuon_tong")
        self.assertEqual((kq["phan_loai"], kq["so_ca"]), ("HONG", 32))

    def test_05_chet_import_bi_bat(self):
        kq = _chay_ma_gia(MAU_BO_GIA["chet_import"][0], "chet_import")
        self.assertEqual(kq["phan_loai"], "THIEU_PHU_THUOC")
        self.assertEqual(kq["so_ca"], 0)

    def test_06_tu_choi_bi_bat(self):
        kq = _chay_ma_gia(MAU_BO_GIA["chet_tu_choi"][0], "chet_tu_choi")
        self.assertEqual(kq["phan_loai"], "TU_CHOI")

    def test_07_chet_truoc_ca_dau_bi_bat(self):
        kq = _chay_ma_gia(MAU_BO_GIA["chet_truoc_ca"][0], "chet_truoc_ca")
        self.assertEqual(kq["phan_loai"], "CHET_0CA")

    def test_08_XANH_GIA_thoát_0_khong_dau_vet_PHAI_bi_bat(self):
        """Hướng sai nguy hiểm nhất: thoát 0, không in gì. Bộ dò PHẢI gắn cờ."""
        kq = _chay_ma_gia(MAU_BO_GIA["xanh_gia_khong_in_gi"][0], "xanh_gia_khong_in_gi")
        self.assertEqual(kq["phan_loai"], "XANH_GIA_0CA")

    def test_09_XANH_GIA_ran_0_tests_PHAI_bi_bat(self):
        kq = _chay_ma_gia(MAU_BO_GIA["xanh_gia_ran_0"][0], "xanh_gia_ran_0")
        self.assertEqual(kq["phan_loai"], "XANH_GIA_0CA")

    def test_10_thieu_chromium_bi_bat(self):
        kq = _chay_ma_gia(MAU_BO_GIA["thieu_chromium"][0], "thieu_chromium")
        self.assertEqual(kq["phan_loai"], "THIEU_PHU_THUOC")

    def test_11_bo_so_sanh_bat_duoc_chet_im_lang(self):
        """ĐỐI CHỨNG DƯƠNG của bộ SO SÁNH: mốc 17 ca, đo 0 ca ⇒ FAIL."""
        kq = {"phan_loai": "CHET_0CA", "so_ca": 0, "qua_han": False}
        self.assertEqual(so_sanh(kq, ("DAT", 17))[0], "FAIL")

    def test_12_bo_so_sanh_KHONG_phat_bo_khoe(self):
        """ĐỐI CHỨNG ÂM của bộ SO SÁNH: mốc 17 ca, đo 17 ca ⇒ KHỚP."""
        kq = {"phan_loai": "DAT", "so_ca": 17, "qua_han": False}
        self.assertEqual(so_sanh(kq, ("DAT", 17))[0], "KHOP")

    def test_13_bo_so_sanh_ghi_nhan_hoi_sinh(self):
        kq = {"phan_loai": "DAT", "so_ca": 17, "qua_han": False}
        self.assertEqual(so_sanh(kq, ("TU_CHOI", 0))[0], "HOI_SINH")

    def test_14_that_thu_giao_dich_tu_choi_roi_chay_duoc(self):
        """ĐO THẬT trên một bộ thật: thiếu khai kho ⇒ 0 ca; khai kho ⇒ 17 ca.

        Đây là đối chứng (a) của báo cáo, chạy lại được ở mọi lượt: nó chứng minh "0 ca" của
        `thu_giao_dich.py` KHÔNG phải bộ thử hỏng, mà là do thiếu MỘT dòng khai.
        """
        duong = os.path.join(THU_MUC, "thu_giao_dich.py")
        self.assertTrue(os.path.isfile(duong), "thiếu %s" % duong)
        khong = do_bo(duong, env_them={"VIP_KHO_DANG_CHAY": None}, giay=120)
        self.assertEqual(khong["so_ca"], 0, "chưa khai kho mà vẫn chạy được ca nào?")
        self.assertEqual(khong["phan_loai"], "TU_CHOI")
        co = do_bo(duong, env_them={"VIP_KHO_DANG_CHAY": "sqlite"}, giay=120)
        self.assertEqual((co["phan_loai"], co["so_ca"], co["ma"]), ("DAT", 17, 0))

    def test_15_that_g22_e2e_KHONG_duoc_XANH_GIA(self):
        """Bộ tự nhận là cổng chống XANH GIẢ thì chính nó không được thoát 0 mà 0 ca."""
        duong = os.path.join(THU_MUC, "thu_g22_e2e.py")
        self.assertTrue(os.path.isfile(duong), "thiếu %s" % duong)
        kq = do_bo(duong, env_them={"VIP_KHO_DANG_CHAY": None}, giay=120)
        self.assertNotEqual(kq["phan_loai"], "XANH_GIA_0CA",
                            "cổng E2E thoát 0 mà không có dấu vết chạy ca nào")
        self.assertFalse(kq["ma"] == 0 and kq["so_ca"] == 0)

    def test_16_du_12_bo_trong_so_ghim_va_ton_tai(self):
        for ten in DS_12:
            self.assertIn(ten, SO_CA_GHIM["khong_khai"])
            self.assertIn(ten, SO_CA_GHIM["khai_kho"])
            self.assertTrue(os.path.isfile(os.path.join(THU_MUC, ten)), "thiếu tệp %s" % ten)

    def test_17_so_ghim_toan_bo_khong_khai_rong(self):
        self.assertGreaterEqual(len(SO_CA_TOAN_BO), 60,
                                "sổ ghim toàn bộ quá ngắn — có bộ mới chưa được ghim?")
        for ten, (pl, ca) in SO_CA_TOAN_BO.items():
            self.assertIn(pl, ("DAT", "HONG", "BO_QUA"), "%s: phán quyết lạ %r" % (ten, pl))
            self.assertIsInstance(ca, int)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. CLI
# ══════════════════════════════════════════════════════════════════════════════════════════════
def in_mot_bo(kq):
    print("BỘ        : %s" % kq["ten"])
    print("ĐƯỜNG     : %s" % os.path.relpath(kq["duong"], GOC))
    print("MÃ THOÁT  : %s" % kq["ma"])
    print("SỐ CA     : %d" % kq["so_ca"])
    print("PHÂN LOẠI : %s — %s" % (kq["phan_loai"], kq["bang_chung"]))
    dau = kq["dong_loi_dau"] or next((ln.strip() for ln in kq["ra"].splitlines() if ln.strip()), "")
    print("DÒNG ĐẦU  : %s" % (dau or "(không in gì)"))
    print("THỜI GIAN : %ss" % kq["giay"])
    print("── 40 dòng cuối ──")
    for ln in kq["ra"].splitlines()[-40:]:
        print("  " + ln)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Đo lại '0 ca': phân biệt bộ CHẾT với bộ CHẠY RỒI HỎNG và XANH GIẢ.")
    ap.add_argument("--do-lai", action="store_true",
                    help="đo lại 12 bộ đã biết và so với sổ ghim (≈25 giây)")
    ap.add_argument("--tat-ca", action="store_true",
                    help="đo lại TOÀN BỘ bộ thử theo sổ ghim toàn bộ (chậm)")
    ap.add_argument("--khai-kho", action="store_true",
                    help="đặt VIP_KHO_DANG_CHAY=sqlite cho tiến trình con (chứng minh nhóm (a))")
    ap.add_argument("--bo", default=None, metavar="TÊN",
                    help="chỉ đo MỘT bộ (tên tệp trong app/thu, ví dụ thu_giao_dich.py)")
    ap.add_argument("--giay", type=int, default=300, metavar="N",
                    help="thời gian chờ mỗi bộ (mặc định 300)")
    ap.add_argument("--json", default=None, metavar="TỆP", help="ghi báo cáo JSON")
    a = ap.parse_args(argv)

    if a.bo:
        ten = os.path.basename(a.bo)
        duong = os.path.join(THU_MUC, ten)
        if not os.path.isfile(duong):
            print("KHÔNG CÓ TỆP: %s" % duong)
            return 3
        env_them = {"VIP_KHO_DANG_CHAY": "sqlite"} if a.khai_kho else {"VIP_KHO_DANG_CHAY": None}
        kq = do_bo(duong, env_them=env_them, giay=a.giay)
        in_mot_bo(kq)
        if a.json:
            ghi_json(a.json, {k: v for k, v in kq.items() if k != "ra"})
        return 0

    if a.tat_ca:
        return chay_tat_ca(a.khai_kho, a.giay, a.json)

    if a.do_lai:
        che_do = "khai_kho" if a.khai_kho else "khong_khai"
        return chay_do_lai(DS_12, SO_CA_GHIM[che_do], a.khai_kho, a.giay, a.json)

    # MẶC ĐỊNH: tự kiểm — nhanh, in `Ran N tests ... OK` cho bộ chạy chung đếm được.
    print("═══ TỰ KIỂM BỘ DÒ '0 CA' (không cần Chromium, không đụng CSDL thật) ═══")
    print("SHA ghim : %s" % SHA_GHIM)
    print("SHA đo   : %s" % (head_hien_tai() or "(không đọc được)"))
    print("Mốc 12 bộ: %s" % ", ".join(DS_12))
    kq = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TuKiem))
    print("TỰ KIỂM: %d ca · hỏng %d · lỗi %d · bỏ qua %d"
          % (kq.testsRun, len(kq.failures), len(kq.errors), len(kq.skipped)))
    return 0 if kq.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
