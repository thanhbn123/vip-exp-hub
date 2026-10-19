#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22/Z2 — BỘ ĐẾM `chay_tat_ca.sh`: CHỨNG MINH NÓ ĐẾM ĐÚNG (và còn bắt được XANH GIẢ).

VÌ SAO CÓ TỆP NÀY
-----------------
X1 đo được một lỗi **ĐẾM**, không phải lỗi sản phẩm: `app/thu/thu_g22_gioihan.py` **CHẠY THẬT
32 ca**, nhưng bảng của `sh app/thu/chay_tat_ca.sh` ghi **`0 ca`**. Nguyên nhân: khi có ca
HỎNG/KHUYẾT, bộ thử viết tay in dòng cuối

    TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=5 · KHUYẾT=0)

còn bộ đếm cũ chỉ nhận `Ran N` (unittest) và `N ca — ĐẠT` (bộ viết tay, lượt đạt) ⇒ không khớp
khuôn nào ⇒ đọc thành 0. Sửa bộ đếm là chuyện nhỏ; **giữ cho nó không tái phát** mới là chuyện
cần chứng minh. Tệp này là phép đo ĐỘC LẬP của riêng bộ đếm.

NGUYÊN TẮC: ĐO CHÍNH BỘ ĐẾM, KHÔNG ĐO BẢN CHÉP
---------------------------------------------
`chay_tat_ca.sh` có chế độ

    sh app/thu/chay_tat_ca.sh --tinh-ca <mã-thoát> <tệp-output>

gọi ĐÚNG hàm `tinh_ca()` mà vòng lặp chính dùng. Tệp này chỉ chạy chế độ đó trên output của
những **bộ thử GIẢ** (tạo trong thư mục tạm, rồi xoá). Vì thế nếu ai sửa bộ đếm sai đi, tệp này
đỏ — không có bản sao thứ hai để trôi khỏi bản thật.

BỐN ĐIỀU PHẢI CHỨNG MINH (đề bài, mỗi điều kèm ĐỐI CHỨNG ÂM)
------------------------------------------------------------
    (a) bộ thử in `N ca` ĐÚNG            ⇒ đếm đúng N.
    (b) bộ thử in báo cáo **khuôn lạ**   ⇒ PHAI đếm đúng, KHÔNG được đếm 0.   ← lỗi X1
    (c) bộ thử in **0 ca thật**          ⇒ KHÔNG được coi là ĐẠT.
    (d) bộ thử **thoát 0** nhưng in dòng HỎNG ⇒ PHAI tính là ĐỎ.

ĐỐI CHỨNG ÂM ở đây là mẫu mà phép đo **KHÔNG được bắt nhầm**: một con số khác trong khuôn khác
(a2), khuôn mới gặp số 0 thật (b2), bỏ qua có chủ đích vẫn là phán quyết thứ ba (c3), và lượt
thoát 0 in ĐẠT không được biến thành ĐỎ (d2). Thiếu vế âm thì một bộ đếm "luôn trả 0" hoặc
"luôn trả HỎNG" cũng qua được bài kiểm.

BẰNG CHỨNG IN RA
----------------
Bảng `nhóm · mẫu · đối chứng · mã thoát · khuôn khớp · N(cũ→mới) · phán(chờ/đo)`, kèm nguyên
văn output của bốn mẫu đầu bảng, và dòng `TỔNG KẾT`. Cột **N(cũ)** là bộ đếm TRƯỚC bản vá (chép
trung thành hai `grep` cũ) — để thấy đúng chỗ 32 ca bị đọc thành 0.

CHẠY
----
    python3 app/thu/thu_g22_demca2.py                 # 0 = bộ đếm đúng · 1 = có mẫu lệch
    python3 app/thu/thu_g22_demca2.py --tu-log <tệp> <mã-thoát>
                                                      # đo một log THẬT bằng chính bộ đếm
    python3 app/thu/thu_g22_demca2.py --chi-tiet      # in nguyên văn output của MỌI mẫu

PHẠM VI
-------
Chỉ ĐỌC `app/thu/chay_tat_ca.sh` và chạy tiến trình con cục bộ trên tệp tạm. KHÔNG sửa bộ thử
nào, KHÔNG chạm CSDL thật, KHÔNG mở socket, KHÔNG gọi hãng.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# `VIP_CHAY_TAT_CA` CHỈ để đo ĐỘT BIẾN (mutation test): trỏ fixture vào một bản sao CỐ Ý HỎNG của
# bộ chạy, để chứng minh fixture ĐỎ ĐƯỢC khi bộ đếm tái phát lỗi cũ. Làn thường không đặt biến
# này — mặc định luôn là bộ chạy thật của cây.
CHAY = os.environ.get("VIP_CHAY_TAT_CA") or os.path.join(GOC, "app", "thu", "chay_tat_ca.sh")

MA_DAT, MA_HONG, MA_LOI = 0, 1, 2

# Khuôn phán quyết mà bộ đếm trả về (khớp `TC_PHAN` trong chay_tat_ca.sh).
DAT, HONG, BO_QUA = "DAT", "HONG", "BO_QUA"

# Mỗi mẫu: (nhóm, tên, đối-chứng, mã nguồn bộ thử GIẢ, mã thoát chờ, N chờ, phán chờ, vì sao)
# `đối-chứng`: "dương" = vế chính của yêu cầu · "âm" = mẫu KHÔNG được bắt nhầm.
MAU = (
    # ── (a) in `N ca` đúng ⇒ đếm đúng N ──────────────────────────────────────────────────────
    ("a", "a1_17ca_viet_tay", "dương",
     'import sys\nprint("17 ca — ĐẠT")\nsys.exit(0)\n', 0, 17, DAT,
     "khuôn `N ca — ĐẠT` của bộ viết tay"),
    ("a", "a2_doi_chung_am_4ca_unittest", "âm",
     'import sys\nprint("Ran 4 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n', 0, 4, DAT,
     "cùng là ĐẠT nhưng N KHÁC và khuôn KHÁC: bộ đếm không được trả hằng số"),

    # ── (b) khuôn LẠ (đúng lỗi X1) ⇒ vẫn phải đếm đúng, không 0 ─────────────────────────────
    ("b", "b1_khuon_TONG_32ca_HONG", "dương",
     'import sys\n'
     'print("  ca ĐẠT=27 · HỎNG=5 · BỎ QUA=0 · KHUYẾT=0 · TỔNG=32")\n'
     'print("  TỔNG: 32 ca — HỎNG (ĐẠT=27 · HỎNG=5 · KHUYẾT=0)")\n'
     'sys.exit(1)\n', 1, 32, HONG,
     "nguyên dạng dòng cuối của thu_g22_gioihan.py trên lượt đỏ"),
    ("b", "b2_doi_chung_am_TONG_0ca", "âm",
     'import sys\nprint("  TỔNG: 0 ca — HỎNG (ĐẠT=0 · HỎNG=0 · KHUYẾT=0)")\n'
     'sys.exit(1)\n', 1, 0, HONG,
     "cùng khuôn nhưng số THẬT là 0: khuôn mới không được bịa ra con số"),
    ("b", "b3_khuon_cong_E2E", "dương",
     'import sys\n'
     'print("  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 62/1/0/2/0  (ghim ĐẠT = 65)")\n'
     'sys.exit(1)\n', 1, 65, HONG,
     "khuôn báo cáo của cổng E2E — cùng lớp lỗi, khác khuôn: phải đếm 62+1+0+2+0=65"),
    ("b", "b4_doi_chung_am_cong_E2E_0ca", "âm",
     'import sys\n'
     'print("  số ca  ĐẠT/HỎNG/BỎ QUA/KHÔNG CHẠY/CHẬP CHỜN : 0/0/0/0/0  (ghim ĐẠT = 65)")\n'
     'sys.exit(0)\n', 0, 0, HONG,
     "vế âm: đủ khuôn E2E nhưng 0 ca thật ⇒ vẫn KHÔNG được phán ĐẠT"),

    # ── (c) 0 ca thật ⇒ không được coi là ĐẠT ───────────────────────────────────────────────
    ("c", "c1_khong_ca_nao_van_DAT", "dương",
     'import sys\nprint("0 ca — ĐẠT")\nsys.exit(0)\n', 0, 0, HONG,
     "tự in ĐẠT với 0 ca = XANH GIẢ, hướng sai nguy hiểm nhất"),
    ("c", "c2_ran_0_tests_OK", "dương",
     'import sys\nprint("Ran 0 tests in 0.00s")\nprint("OK")\nsys.exit(0)\n', 0, 0, HONG,
     "khuôn unittest rỗng: `Ran 0` + `OK` vẫn KHÔNG phải ĐẠT"),
    ("c", "c3_doi_chung_am_bo_qua", "âm",
     'import sys\nprint("Ran 0 tests in 0.00s")\n'
     'print("BỎ QUA: chưa cài PostgreSQL — Bật bằng: VIP_THU_POSTGRES=1")\n'
     'print("skipped=3")\nsys.exit(0)\n', 0, 0, BO_QUA,
     "bỏ qua CÓ CHỦ ĐÍCH vẫn là phán quyết thứ ba, không bị gộp vào HỎNG"),

    # ── (d) thoát 0 nhưng in HỎNG ⇒ phải là ĐỎ ───────────────────────────────────────────────
    ("d", "d1_thoat_0_van_in_HONG", "dương",
     'import sys\nprint("Ran 5 tests in 0.01s")\nprint("OK")\n'
     'print("  TỔNG: 5 ca — HỎNG (ĐẠT=4 · HỎNG=1 · KHUYẾT=0)")\nsys.exit(0)\n', 0, 5, HONG,
     "đủ mã thoát 0 + OK + N>0 mà tự báo HỎNG ⇒ KHÔNG được ghi ✓"),
    ("d", "d2_doi_chung_am_thoat_0_DAT", "âm",
     'import sys\nprint("Ran 5 tests in 0.01s")\nprint("OK")\n'
     'print("  TỔNG: 5 ca — ĐẠT")\nsys.exit(0)\n', 0, 5, DAT,
     "vế âm: cùng hình dạng nhưng ĐẠT thật ⇒ không được đỏ oan"),
    ("d", "d3_doi_chung_am_trich_dan_HONG", "âm",
     'import sys\n'
     'print("test_04_khuon_TONG_van_dem_duoc_ca (__main__.TuKiem)")\n'
     'print("Đúng lỗi: in `TỔNG: 32 ca — HỎNG` mà bộ chạy chung đọc 0. ... ok")\n'
     'print("Ran 1 tests in 0.01s")\nprint("OK")\nsys.exit(0)\n', 0, 1, DAT,
     "vế âm thứ hai: chữ HỎNG nằm trong TRÍCH DẪN giữa bài (docstring `unittest -v`) ⇒ không đỏ oan"),
)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# BỘ ĐẾM CŨ — chép TRUNG THÀNH hai `grep` TRƯỚC bản vá, chỉ để có cột "trước" trong bằng chứng.
# Đây KHÔNG phải thứ được kiểm: mọi phán quyết lấy từ `chay_tat_ca.sh --tinh-ca`.
# ══════════════════════════════════════════════════════════════════════════════════════════════
def dem_cu(out):
    m = re.findall(r"Ran [0-9]+", out)
    if m:
        return int(m[-1].split()[1])
    m = re.findall(r"[0-9]+ ca — ĐẠT", out)
    if m:
        return int(m[-1].split()[0])
    return 0


# ══════════════════════════════════════════════════════════════════════════════════════════════
# GỌI BỘ ĐẾM THẬT qua chế độ `--tinh-ca`
# ══════════════════════════════════════════════════════════════════════════════════════════════
def dem_that(ma_thoat, duong_out):
    """Trả dict {N, KHUON, PHAN, LY_DO, ma}. Ném RuntimeError nếu chế độ không đọc được."""
    tt = subprocess.run(["sh", CHAY, "--tinh-ca", str(ma_thoat), duong_out],
                        cwd=GOC, capture_output=True, text=True, timeout=120)
    if tt.returncode != 0:
        raise RuntimeError("`--tinh-ca` thoát %d: %s"
                           % (tt.returncode, (tt.stderr or tt.stdout).strip()[-400:]))
    kq = {}
    for dong in tt.stdout.splitlines():
        if "=" in dong:
            k, v = dong.split("=", 1)
            kq[k] = v
    for k in ("N", "KHUON", "PHAN", "LY_DO"):
        if k not in kq:
            raise RuntimeError("`--tinh-ca` KHÔNG in `%s=` (output: %r)" % (k, tt.stdout[-300:]))
    kq["N"] = int(kq["N"])
    kq["ma"] = tt.returncode
    return kq


# ══════════════════════════════════════════════════════════════════════════════════════════════
# CHẠY MỘT MẪU: tạo bộ thử giả → chạy nó → đưa output cho bộ đếm THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════
def chay_mau(ten, ma_nguon, thu_muc):
    duong_py = os.path.join(thu_muc, ten + ".py")
    with open(duong_py, "w", encoding="utf-8") as f:
        f.write(ma_nguon)
    tt = subprocess.run([sys.executable, duong_py], capture_output=True, text=True,
                        timeout=120, cwd=thu_muc)
    out = (tt.stdout or "") + (tt.stderr or "")
    duong_out = os.path.join(thu_muc, ten + ".out")
    with open(duong_out, "w", encoding="utf-8") as f:
        f.write(out)
    kq = dem_that(tt.returncode, duong_out)
    kq["ma_gia"] = tt.returncode
    kq["out"] = out
    kq["n_cu"] = dem_cu(out)
    return kq


def in_dong(s):
    print("  " + s)


def an(x):
    """Che khuôn phán quyết trong output ĐEM IN của mẫu giả.

    Vì sao: output mẫu giả phải in ra làm BẰNG CHỨNG, nhưng nếu in nguyên văn `32 ca — HỎNG`
    thì chính bộ đếm của `chay_tat_ca.sh` — khi chạy tệp NÀY như một bộ thử — sẽ đọc câu đó như
    phán quyết của tệp này (một bộ tự kiểm không được tự đầu độc phép đo của chính nó). Đổi
    `—` thành `~` và chèn `·` sau `Ran ` giữ nguyên nội dung đọc được, chỉ vô hiệu hoá khuôn.
    """
    return (x.replace(" ca — ĐẠT", " ca ~ ĐẠT")
             .replace(" ca — HỎNG", " ca ~ HỎNG")
             .replace("Ran ", "Ran· "))


def main():
    ap = argparse.ArgumentParser(description="Chứng minh bộ đếm chay_tat_ca.sh đếm ĐÚNG")
    ap.add_argument("--tu-log", nargs=2, metavar=("TEP_LOG", "MA_THOAT"),
                    help="đo một log THẬT (tệp output, mã thoát) bằng chính bộ đếm")
    ap.add_argument("--chi-tiet", action="store_true", help="in nguyên văn output của mọi mẫu")
    tham = ap.parse_args()

    print("=" * 100)
    print("  G22/Z2 — BỘ ĐẾM `chay_tat_ca.sh`: ĐẾM ĐÚNG HAY ĐẾM 0?")
    print("  bộ đếm thật: %s" % CHAY)
    print("=" * 100)

    if not os.path.isfile(CHAY):
        in_dong("KHÔNG có %s ⇒ không đo được bộ đếm." % CHAY)
        return MA_LOI

    # ---- chế độ đo một LOG THẬT (không tạo mẫu giả) ----
    if tham.tu_log:
        tep, ma_txt = tham.tu_log
        if not ma_txt.isdigit():
            in_dong("mã thoát phải là số: %r" % ma_txt)
            return MA_LOI
        if not os.path.isfile(tep):
            in_dong("KHÔNG có tệp log: %s" % tep)
            return MA_LOI
        try:
            kq = dem_that(int(ma_txt), tep)
        except RuntimeError as e:                                          # noqa: BLE001
            in_dong("BỘ ĐẾM KHÔNG ĐỌC ĐƯỢC: %s" % e)
            return MA_LOI
        out = open(tep, encoding="utf-8", errors="replace").read()
        print()
        in_dong("log         : %s" % tep)
        in_dong("mã thoát    : %s" % ma_txt)
        in_dong("bộ đếm CŨ   : %d ca" % dem_cu(out))
        in_dong("bộ đếm MỚI  : %d ca  · khuôn=%s · phán=%s · lý do=%s"
                % (kq["N"], kq["KHUON"], kq["PHAN"], kq["LY_DO"] or "(không)"))
        print()
        return MA_DAT

    # ---- chạy đủ bộ mẫu ----
    thu_muc = tempfile.mkdtemp(prefix="veh-g22-demca2-")
    ket_qua = []
    try:
        for (nhom, ten, chieu, nguon, ma_cho, n_cho, phan_cho, vi_sao) in MAU:
            kq = chay_mau(ten, nguon, thu_muc)
            kq.update(nhom=nhom, ten=ten, chieu=chieu, ma_cho=ma_cho,
                      n_cho=n_cho, phan_cho=phan_cho, vi_sao=vi_sao)
            kq["khong_hop"] = []
            if kq["ma_gia"] != ma_cho:
                kq["khong_hop"].append("mã thoát giả %d ≠ chờ %d" % (kq["ma_gia"], ma_cho))
            if kq["N"] != n_cho:
                kq["khong_hop"].append("N đo %d ≠ chờ %d" % (kq["N"], n_cho))
            if kq["PHAN"] != phan_cho:
                kq["khong_hop"].append("phán %s ≠ chờ %s" % (kq["PHAN"], phan_cho))
            ket_qua.append(kq)
    except RuntimeError as e:                                              # noqa: BLE001
        print()
        in_dong("KHÔNG ĐỌC ĐƯỢC BỘ ĐẾM — phép đo vô hiệu, KHÔNG được coi là ĐẠT: %s" % e)
        return MA_LOI
    finally:
        shutil.rmtree(thu_muc, ignore_errors=True)

    # ---- bảng bằng chứng ----
    print()
    print("  BẢNG 4 NHÓM — mỗi nhóm có vế CHÍNH và ĐỐI CHỨNG ÂM")
    print("  " + "-" * 96)
    print("  %-4s %-30s %-6s %-5s %-16s %-11s %-10s %s"
          % ("nhóm", "mẫu", "đ.chứng", "mã", "khuôn khớp", "N (cũ→mới)", "phán", "kết quả"))
    print("  " + "-" * 96)
    for kq in ket_qua:
        dau = "✓" if not kq["khong_hop"] else "✗"
        phan_hien = "%s/%s" % (kq["phan_cho"], kq["PHAN"])
        print("  %-4s %-30s %-6s %-5d %-16s %5d → %-5d %-10s %s"
              % (kq["nhom"], kq["ten"], kq["chieu"], kq["ma_gia"], kq["KHUON"],
                 kq["n_cu"], kq["N"], phan_hien,
                 dau if not kq["khong_hop"] else dau + " LỆCH"))
    print("  " + "-" * 96)

    # ---- nguyên văn bốn mẫu đầu bảng (bằng chứng đọc được, không phải tóm tắt) ----
    print()
    print("  NGUYÊN VĂN output của bốn mẫu chính (a1 · b1 · c1 · d1):")
    for kq in ket_qua:
        if kq["ten"] in ("a1_17ca_viet_tay", "b1_khuon_TONG_32ca_HONG",
                         "c1_khong_ca_nao_van_DAT", "d1_thoat_0_van_in_HONG"):
            print("  ┌ %s — bộ thử giả thoát %d" % (kq["ten"], kq["ma_gia"]))
            for d in an(kq["out"]).rstrip("\n").splitlines():
                print("  │ %s" % d)
            print("  └ bộ đếm CŨ: %d ca · bộ đếm MỚI: %d ca · phán %s (%s)"
                  % (kq["n_cu"], kq["N"], kq["PHAN"], kq["KHUON"]))
    if tham.chi_tiet:
        print()
        print("  NGUYÊN VĂN output của MỌI mẫu (--chi-tiet):")
        for kq in ket_qua:
            print("  ┌ %s — thoát %d" % (kq["ten"], kq["ma_gia"]))
            for d in an(kq["out"]).rstrip("\n").splitlines():
                print("  │ %s" % d)
            print("  └ CŨ=%d · MỚI=%d · %s" % (kq["n_cu"], kq["N"], kq["PHAN"]))

    # ---- vì sao từng mẫu ----
    print()
    print("  VÌ SAO TỪNG MẪU (điều kiện đề bài → mẫu):")
    for kq in ket_qua:
        print("    (%s) %-30s %-6s %s"
              % (kq["nhom"], kq["ten"], kq["chieu"], an(kq["vi_sao"])))

    # ---- chốt: đúng lỗi X1 phải nhìn thấy được ở cột "trước" ----
    loi = [kq for kq in ket_qua if kq["ten"] == "b1_khuon_TONG_32ca_HONG"][0]
    print()
    print("  CHỐT LỖI X1: cùng output `b1`, bộ đếm CŨ đọc %d ca, bộ đếm MỚI đọc %d ca."
          % (loi["n_cu"], loi["N"]))
    if loi["n_cu"] != 0:
        loi["khong_hop"].append("bộ đếm CŨ không tái hiện lỗi (đọc %d, chờ 0)" % loi["n_cu"])

    # ---- tổng kết ----
    lech = [kq for kq in ket_qua if kq["khong_hop"]]
    so_nhom = {}
    for kq in ket_qua:
        so_nhom.setdefault(kq["nhom"], []).append(kq)
    print()
    print("  " + "-" * 96)
    print("  TỔNG KẾT: %d mẫu · %d KHỚP · %d LỆCH  (%s)"
          % (len(ket_qua), len(ket_qua) - len(lech), len(lech),
             " · ".join("(%s) %d mẫu" % (n, len(v)) for n, v in sorted(so_nhom.items()))))
    for kq in lech:
        print("    ✗ %-30s %s" % (kq["ten"], " · ".join(kq["khong_hop"])))
    print("  " + "-" * 96)
    if lech:
        print("  KẾT LUẬN: BỘ ĐẾM SAI — %d mẫu lệch. Đây là lỗi của bộ đếm, không phải của bộ thử."
              % len(lech))
        # Dòng phán quyết CUỐI, đúng khuôn bộ đếm đọc — N là SỐ MẪU ĐÃ CHẠY (kể cả mẫu lệch).
        print("  %d ca — HỎNG" % len(ket_qua))
        return MA_HONG
    print("  KẾT LUẬN: BỘ ĐẾM ĐẾM ĐÚNG ở cả 4 điều kiện (a)(b)(c)(d), kể cả đối chứng âm.")
    # Dòng phán quyết CUỐI — để khi `chay_tat_ca.sh` chạy chính tệp này, nó đọc được số mẫu đã
    # chạy và phán ĐẠT, thay vì "thoát 0 nhưng không có dấu vết đã chạy ca nào".
    print("  %d ca — ĐẠT" % len(ket_qua))
    return MA_DAT


if __name__ == "__main__":
    sys.exit(main())
