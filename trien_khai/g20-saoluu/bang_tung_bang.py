#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — BẢNG **SỐ DÒNG + TỔNG TIỀN TỪNG BẢNG**, sinh thẳng từ số đo thô.

    python3 trien_khai/g20-saoluu/bang_tung_bang.py ket_qua/sau.json          # in ra màn hình
    python3 trien_khai/g20-saoluu/bang_tung_bang.py ket_qua/sau.json --md F   # ghi markdown

====== VÌ SAO PHẢI LÀ MỘT BƯỚC RIÊNG ======
Một khẳng định "CSDL đích Y NGUYÊN" chỉ kiểm chứng được nếu có **số của TỪNG BẢNG** để đối
chiếu. Bản tóm tắt (`so_bang` + `tong_tien_toan_kho`) không dựng lại được số từng bảng: nó chỉ
nói "tổng không đổi", mà tổng không đổi là điều kiện CẦN, không phải điều kiện ĐỦ — hai bảng
đổi cho nhau (bảng này mất 3 dòng, bảng kia thêm 3 dòng) vẫn cho ra cùng một tổng.

Nên tệp này đọc `chup_day_du` (phép chụp ĐẦY ĐỦ do `fail_closed._ghi` giữ lại) và in ra bảng
thật: từng bảng · số dòng TRƯỚC/SAU · tổng tiền TRƯỚC/SAU · kết luận.
"""
import json
import os
import sys

DAY = os.path.dirname(os.path.abspath(__file__))


def _tien(b):
    return sum(v for v in (b.get("tien") or {}).values() if isinstance(v, (int, float)))


def _dong_bang(ten, t, s, bo_qua=()):
    """So MỘT bảng giữa hai phép chụp."""
    bt = (t.get("bang") or {}).get(ten) or {}
    bs = (s.get("bang") or {}).get(ten) or {}
    dt, ds = bt.get("dong"), bs.get("dong")
    tt, ts = _tien(bt), _tien(bs)
    if ten in bo_qua:
        ket = "(bỏ qua theo khai báo)"
    elif dt != ds:
        ket = "**LỆCH DÒNG**"
    elif tt != ts:
        ket = "**LỆCH TIỀN**"
    else:
        ket = "khớp"
    return "| `%s` | %s | %s | %s | %s | %s |" % (ten, dt, ds, tt, ts, ket)


def in_mot(ma, b, ra):
    dd = b.get("chup_day_du") or {}
    t, s = dd.get("truoc"), dd.get("sau")
    ra.append("### %s · %s" % (ma, b.get("ten", "")))
    ra.append("")
    ra.append("`rc=%s` · phán quyết **%s**" % (b.get("rc"), "FAIL_CLOSED"
                                               if not b.get("_loi") else "FAIL_OPEN"))
    if not t or not s:
        ra.append("")
        ra.append("_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: "
                  "`%s`)._"
                  % json.dumps(b.get("csdl_dich_sau"), ensure_ascii=False)[:180])
        ra.append("")
        return
    if not (t.get("ton_tai") and s.get("ton_tai")):
        ra.append("")
        ra.append("_CSDL đích không tồn tại ở một trong hai mốc: trước=%s sau=%s._"
                  % (t.get("ton_tai"), s.get("ton_tai")))
        ra.append("")
        return
    ra.append("")
    ra.append("| Bảng | Số dòng TRƯỚC | Số dòng SAU | Tiền TRƯỚC | Tiền SAU | Kết |")
    ra.append("|---|---|---|---|---|---|")
    bo_qua = tuple(b.get("c_lech_bo_qua") or ())
    lech = 0
    for ten in sorted(set(t.get("bang") or {}) | set(s.get("bang") or {})):
        d = _dong_bang(ten, t, s, bo_qua)
        if "LỆCH" in d:
            lech += 1
        ra.append(d)
    ra.append("| **TỔNG (toàn kho)** | %s | %s | **%s** | **%s** | %s |"
              % (t.get("so_bang"), s.get("so_bang"), t.get("tong_tien_toan_kho"),
                 s.get("tong_tien_toan_kho"),
                 "**LỆCH**" if t.get("tong_tien_toan_kho") != s.get("tong_tien_toan_kho")
                 else "khớp"))
    ra.append("")
    ra.append("`integrity_check`: %s → %s · `bam_toan_kho`: `%s` → `%s` · số bảng LỆCH: **%d**"
              % (t.get("integrity_check"), s.get("integrity_check"),
                 str(t.get("bam_toan_kho"))[:16], str(s.get("bam_toan_kho"))[:16], lech))
    ra.append("")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    duong = argv[0]
    kq = json.load(open(duong, encoding="utf-8"))
    import fail_closed as fc
    ra = ["# BẢNG SỐ DÒNG + TỔNG TIỀN TỪNG BẢNG",
          "",
          "Nguồn: `%s` · `app/` đang đo: `%s`" % (duong, kq.get("app")),
          "",
          "Mỗi bảng dưới đây là một dòng của phép chụp ĐẦY ĐỦ (`khung_do.chup`), không phải bản",
          "tóm tắt. Cột **Tiền** là tổng MỌI cột tiền của bảng đó (`khung_do.COT_TIEN`).",
          ""]
    for ma in fc.THU_TU:
        b = kq["ban_ghi"].get(ma)
        if b is None:
            continue
        b["_loi"] = fc.phan_quyet(b)
        in_mot(ma, b, ra)
    van = "\n".join(ra)
    if "--md" in argv:
        p = argv[argv.index("--md") + 1]
        with open(p, "w", encoding="utf-8") as f:
            f.write(van + "\n")
        print("đã ghi %s (%d dòng)" % (p, van.count("\n") + 1))
    else:
        print(van)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
