#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — ĐO CÁI GIÁ CỦA MẶC ĐỊNH MỚI TRÊN **8 BỘ THỬ NGOÀI VÙNG ĐƯỢC GHI** CỦA AG-02.

Vì sao phải đo chứ không được suy luận: `migrate.chay()` trên một thư mục dữ liệu MỚI CÓ gọi
`sao_luu()` (`csdl.mo()` tạo `schema_version` rỗng ⇒ `MAX(phien_ban) = 0` ⇒ chạy nâng cấp), nên
khi mặc định đổi thành "chưa khai ⇒ TỪ CHỐI", MỌI bộ thử gọi `migrate.chay()` mà không khai kho
sẽ TỪ CHỐI. Con số đó là CÁI GIÁ của quyết định — và nó phải là số ĐO ĐƯỢC, không phải lời phỏng
đoán trong tài liệu.

HAI LƯỢT CHO MỖI BỘ, và lượt thứ hai chính là ĐƯỜNG SỬA:
  * `chua_khai`      — KHÔNG đặt `VIP_KHO_DANG_CHAY` ⇒ đo cái giá;
  * `khai_sqlite`    — đặt `VIP_KHO_DANG_CHAY=sqlite` ⇒ chứng minh cái giá đó trả được bằng MỘT
                       dòng khai báo, không phải bằng cách nới chốt.
KHÔNG sửa tệp nào của 8 bộ đó (ngoài vùng được ghi của AG-02) — chỉ chạy và ghi lại mã thoát.

    python3 trien_khai/g20-saoluu/do_8_bo_ngoai.py            # in bảng
    python3 trien_khai/g20-saoluu/do_8_bo_ngoai.py --json F   # máy đọc
"""
import json
import os
import re
import subprocess
import sys

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
PY = sys.executable or "python3"

# Các bộ NGOÀI vùng được ghi của AG-02 có đi qua `sao_luu()` (đã đo bằng `grep`: mỗi bộ gọi
# `migrate.chay()`, mà `chay()` gọi `sao_luu()` trước khi nâng). Cột `co__main__` nói ra một
# chuyện ĐO ĐƯỢC chứ không phải chuyện hành chính: một tệp KHÔNG có khối `__main__` thì chạy nó
# trực tiếp KHÔNG đo gì (rc=0 ở cả hai chế độ), và đường vào thật của nó nằm ở tệp khác — ghi ra
# để người đọc không đọc nhầm `rc=0` thành "bộ này không bị ảnh hưởng".
BOS = (
    ("thu_giao_dich.py", "app/thu/thu_giao_dich.py", True),
    ("thu_han_muc_nguyen_tu.py", "app/thu/thu_han_muc_nguyen_tu.py", True),
    ("dong_thoi/do_dong_thoi.py", "app/thu/dong_thoi/do_dong_thoi.py", False),
    ("thu_qa_g18.py", "app/thu/thu_qa_g18.py", True),
    ("thu_header_bao_mat.py", "app/thu/thu_header_bao_mat.py", True),
    ("thu_qa_g19.py", "app/thu/thu_qa_g19.py", True),
    ("thu_g17.py", "app/thu/thu_g17.py", True),
    ("thu_g17_baomat.py", "app/thu/thu_g17_baomat.py", True),
    # Hai bộ ĐO THÊM, không nằm trong danh sách 8 của lượt trước, nhưng cũng đi qua `chay()`:
    # bộ đồng thời thật (8 tiến trình) và diễn tập khôi phục của AG-05 DEVOPS.
    ("thu_migrate_dong_thoi.py", "app/thu/thu_migrate_dong_thoi.py", True),
    ("dien_tap_khoi_phuc.sh", "trien_khai/dien_tap_khoi_phuc.sh", True),
)


def _chay(duong, khai_kho, timeout=3600):
    env = dict(os.environ)
    env.pop("VIP_KHO_DANG_CHAY", None)
    if khai_kho:
        env["VIP_KHO_DANG_CHAY"] = khai_kho
    lenh = ["sh", duong] if duong.endswith(".sh") else [PY, duong]
    p = subprocess.run(lenh, cwd=GOC, env=env, capture_output=True, text=True, timeout=timeout)
    ra = p.stdout + p.stderr
    m = re.search(r"Ran (\d+) tests?", ra)
    s = re.search(r"skipped=(\d+)", ra)
    return {"rc": p.returncode, "so_ca": int(m.group(1)) if m else None,
            "so_skip": int(s.group(1)) if s else 0,
            "so_fail": len(re.findall(r"^(?:FAIL|ERROR): ", ra, re.M)) or None,
            "tu_choi_vi_chua_khai": "CHƯA KHAI kho đang chạy" in ra,
            "dong_cuoi": [d for d in ra.strip().splitlines() if d.strip()][-1][:160] if ra.strip() else ""}


def main():
    ra = {}
    for ten, duong, co_main in BOS:
        ra[ten] = {"co__main__": co_main}
        for nhan, khai in (("chua_khai", None), ("khai_sqlite", "sqlite")):
            try:
                ra[ten][nhan] = _chay(duong, khai)
            except subprocess.TimeoutExpired:
                ra[ten][nhan] = {"rc": "TIMEOUT", "so_ca": None, "so_skip": None,
                                 "so_fail": None, "tu_choi_vi_chua_khai": None, "dong_cuoi": ""}
            d = ra[ten][nhan]
            print("%-28s %-12s rc=%-4s ca=%-5s skip=%-3s fail=%-4s từ-chối=%-5s %s"
                  % (ten, nhan, d["rc"], d["so_ca"], d["so_skip"], d["so_fail"],
                     d["tu_choi_vi_chua_khai"], d["dong_cuoi"][:48]))
    return ra


if __name__ == "__main__":
    kq = main()
    for i, a in enumerate(sys.argv):
        if a == "--json":
            with open(sys.argv[i + 1], "w", encoding="utf-8") as f:
                json.dump(kq, f, ensure_ascii=False, indent=1)
            print("→ %s" % sys.argv[i + 1])
