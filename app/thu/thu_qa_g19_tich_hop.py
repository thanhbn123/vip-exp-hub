#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21/AG-04 — BẢN UỶ QUYỀN MỎNG: tên tệp mà cổng C5/G7 đếm được, logic vẫn MỘT bản.

VÌ SAO TỆP NÀY TỒN TẠI (điểm vướng ownership — giải quyết bằng ĐO RỒI HỎI, không tự vượt)
---------------------------------------------------------------------------------------
Cổng `C5` (AG-01, `app/thu/thu_qa_g20.py`) và cổng `G7` (`app/thu/thu_qa_g21.py`) đếm bộ
G19-tổng-hợp bằng KHUÔN TÊN, không bằng nội dung:

    ung_vien = sorted(t for t in os.listdir(GOC_THU) if re.match(r"thu_qa_g19.*\\.py$", t))

Bộ tổng hợp thật của làn AG-04 tên là `app/thu/thu_g19_tich_hop.py` — **không bao giờ** khớp
khuôn đó. Vì vậy C5 đo được `0/1` dù bộ tổng hợp chạy thật và xanh. Đây là lỗi ĐẶT TÊN chứ
không phải lỗi sản phẩm: phép đo đúng, chỉ có chỗ nó nhìn là trống.

Lượt trước tôi dựng thử một bản uỷ quyền cùng tên rồi XOÁ — đúng, vì khi đó tệp nằm NGOÀI vùng
được cấp. Lượt này AG-00 đã cấp tường minh tệp này cho AG-04 và đã báo AG-01/AG-05 KHÔNG sửa
trùng. Nên nó Ở LẠI, và ở đây ghi rõ lý do tại sao.

BA CHỐT CỦA BẢN UỶ QUYỀN — và cái nó KHÔNG được làm
---------------------------------------------------
1. **MỘT bản logic duy nhất.** Tệp này KHÔNG chứa phép đo nào. Nó chạy
   `app/thu/thu_g19_tich_hop.py` trong tiến trình con, in NGUYÊN VĂN stdout+stderr của bộ đó,
   rồi **thoát bằng ĐÚNG mã thoát của bộ đó**. Không viết lại, không nuốt, không đổi thành 1.
2. **Không làm mất bảo đảm nào.** Vì mã thoát được chuyển NGUYÊN VĂN, toàn bộ 8 ca tự kiểm của
   bộ gốc còn nguyên hiệu lực: runner lỗi ⇒ cổng ĐỎ · runner không tồn tại ⇒ ĐỎ và in rõ
   "KHÔNG CHẠY ĐƯỢC" · suite rỗng (`Ran 0 tests` + `OK`) ⇒ ĐỎ vì 0 ca · mọi ca BỎ QUA ⇒ ĐỎ.
   Bản uỷ quyền chỉ THÊM đúng một chỗ siết: nếu chính bộ gốc KHÔNG TỒN TẠI thì nó không được
   phép thoát 0 — nó trả `127` và in "KHÔNG CHẠY ĐƯỢC".
3. **Không nới điều kiện, không bịa số.** Tệp này không sửa `thu_qa_g20.py`/`thu_qa_g21.py`
   (tệp của AG-01), không sửa `chay_tat_ca.sh`, và **không tự in ra dòng `Ran N tests` hay
   `N ca — ĐẠT` giả** — hai khuôn đó là của bộ đếm, in khống chúng là làm bộ đếm đọc một con số
   không do phép đo nào sinh ra. Con số hiện ra là con số THẬT của bộ gốc, in nguyên văn.

KHUÔN BÁO CÁO — chỗ dễ hỏng nhất, và cách nó được canh
------------------------------------------------------
Bộ đếm `chay_tat_ca.sh` lấy `Ran [0-9]+` **CUỐI CÙNG** trong output; `C5`/`G7` lấy phần tử cuối
của `re.findall(r"Ran (\\d+) tests?")`. Nghĩa là: **dòng `Ran N tests` cuối cùng phải là con số
THẬT**. Tệp này vì thế in phần thân bộ gốc ra TRƯỚC, rồi mới in bảng kết luận của mình — và bảng
kết luận KHÔNG chứa khuôn `Ran <số>`. Nó cũng ĐẾM LẠI dòng `Ran N tests` cuối trong thân bộ gốc
và in con số đó thành một dòng CHỮ, để người đọc đối chiếu được với thứ bộ đếm sẽ đọc.

CHẠY
----
    python3 app/thu/thu_qa_g19_tich_hop.py     # ~2 phút, phần lớn thời gian nằm ở bộ gốc
"""

import hashlib
import os
import re
import subprocess
import sys

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ — suy từ chính tệp này, không điền tay
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BO_THU = os.path.join("app", "thu", "thu_g19_tich_hop.py")   # ← MỘT bản logic duy nhất

MA_KHONG_CHAY_DUOC = 127        # trùng mã mà bộ gốc dùng cho cùng tình huống
GIAY_TOI_DA = 1080              # phải NHỎ HƠN hạn 1200s của cổng C5, để kịp in lý do


def _lenh():
    """Lệnh chạy bộ gốc. Tách ra một chỗ để phép tiêm lỗi đổi được ĐÚNG MỘT dòng."""
    return [sys.executable, "-u", BO_THU]


def _doc(duong):
    try:
        with open(duong, "rb") as f:
            return f.read()
    except OSError:
        return None


def main():
    duong = os.path.join(GOC, BO_THU)
    than = _doc(duong)
    print("=" * 92)
    print("  BẢN UỶ QUYỀN MỎNG (G21/AG-04) — tên tệp khớp khuôn `thu_qa_g19*` của cổng C5/G7")
    print("  cây            : %s" % GOC)
    print("  bộ gốc (logic) : %s%s" % (BO_THU, "" if than is not None else "   ← KHÔNG CÓ"))
    if than is not None:
        print("  sha256 bộ gốc  : %s (%d byte)"
              % (hashlib.sha256(than).hexdigest()[:16], len(than)))
    print("  vai            : chạy bộ gốc · in NGUYÊN VĂN output · trả ĐÚNG mã thoát của nó")
    print("=" * 92)

    if than is None:
        # Chốt: bộ gốc không tồn tại thì TUYỆT ĐỐI không được thoát 0.
        print("\n  KHÔNG CHẠY ĐƯỢC: bộ gốc %s không tồn tại trong cây này." % BO_THU)
        print("  Bản uỷ quyền KHÔNG chứa logic thứ hai, nên không có gì để chạy ⇒ ĐỎ.")
        print("\n  MÃ THOÁT: %d  ← KHÔNG CHẠY ĐƯỢC (cố ý khác 0)" % MA_KHONG_CHAY_DUOC)
        return MA_KHONG_CHAY_DUOC

    lenh = _lenh()
    print("\n  $ %s\n" % " ".join(lenh))
    try:
        r = subprocess.run(lenh, cwd=GOC, capture_output=True, text=True, timeout=GIAY_TOI_DA)
        ma, ra, re_ = r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired as ex:
        ra = ex.stdout or ""
        if isinstance(ra, bytes):
            ra = ra.decode("utf-8", "replace")
        ma = 124
        re_ = "[QUÁ HẠN %ss — bản uỷ quyền tự cắt trước hạn của cổng C5]\n" % GIAY_TOI_DA
    except OSError as ex:
        print("  KHÔNG CHẠY ĐƯỢC: %s: %s" % (type(ex).__name__, ex))
        print("\n  MÃ THOÁT: %d  ← KHÔNG CHẠY ĐƯỢC (cố ý khác 0)" % MA_KHONG_CHAY_DUOC)
        return MA_KHONG_CHAY_DUOC

    sys.stdout.write(ra)
    if re_:
        sys.stderr.write(re_)
    sys.stdout.flush()

    # ── BẢNG KẾT LUẬN — KHÔNG chứa khuôn `Ran <số>` ─────────────────────────────────────────
    # Dòng `Ran N tests` THẬT đã in ở trên, trong thân bộ gốc, và không có dòng nào như thế
    # được in xuống dưới nó nữa. Ở đây chỉ ĐỌC LẠI con số đó và tả bằng chữ.
    m = re.findall(r"Ran (\d+) tests?", ra)
    so_ca_tu_kiem = int(m[-1]) if m else 0
    print("")
    print("=" * 92)
    print("  BẢN UỶ QUYỀN — KẾT LUẬN (không in lại khuôn đếm; con số dưới đây CHỈ để đối chiếu)")
    print("  mã thoát bộ gốc, chuyển NGUYÊN VĂN     : %d" % ma)
    print("  số lần khuôn `Ran N tests` xuất hiện   : %d" % len(m))
    print("  con số mà bộ đếm sẽ đọc (lần CUỐI)     : %d ca" % so_ca_tu_kiem)
    print("  bộ đếm còn đòi dấu vết `OK` / `ca — ĐẠT` và mã thoát 0 — cả hai do bộ gốc cung cấp.")
    print("=" * 92)
    return ma


if __name__ == "__main__":
    sys.exit(main())
