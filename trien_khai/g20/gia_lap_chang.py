#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 — CHẶNG GIẢ LẬP, chỉ để TIÊM LỖI vào bản sao hợp đồng.

Vì sao cần một chặng giả thay vì tiêm vào chặng thật: một phép tiêm chạy được chỉ khi nó
chạy NHANH và CHO KẾT QUẢ CHỌN TRƯỚC. Tiêm vào `trien_khai/g18` (26 giây, có phần tử ngẫu
nhiên theo tải máy) thì lượt "bộ dò có bắt được không" lại phụ thuộc vào tải máy — và một bộ
tự kiểm phụ thuộc tải máy là một bộ tự kiểm không đáng tin.

Chặng giả này KHÔNG đo gì về dự án. Nó chỉ trả lời đúng một câu: *harness G20 có phán ĐỎ
được không, khi một chặng vi phạm đúng một khai báo của hợp đồng?*

CHẠY (do `tiem_loi.py` gọi, không gọi tay)
------------------------------------------
    python3 gia_lap_chang.py --ra /tmp/bc.json --ma-thoai 0 --dat 5 --hong 0
    python3 gia_lap_chang.py --ra /tmp/bc.json --kieu khong-ghi
"""
import argparse
import json
import sys

KIEU = ("binh-thuong", "khong-ghi", "json-hong", "thieu-khoa")


def main(argv=None):
    ap = argparse.ArgumentParser(description="chặng giả lập cho bộ tiêm lỗi G20")
    ap.add_argument("--ra", default="", help="đường dẫn báo cáo con")
    ap.add_argument("--kieu", default="binh-thuong", choices=KIEU)
    ap.add_argument("--ma-thoai", type=int, default=0)
    ap.add_argument("--dat", type=int, default=5)
    ap.add_argument("--hong", type=int, default=0)
    ap.add_argument("--blocked", type=int, default=0)
    ap.add_argument("--bo-qua", type=int, default=0)
    ap.add_argument("--so-buoc", type=int, default=5)
    ap.add_argument("--in-ra", dest="in_ra", default="CHANG GIA LAP · báo cáo JSON:")
    a = ap.parse_args(argv)

    if a.in_ra:
        print(a.in_ra)
    if a.kieu == "khong-ghi":
        print("[giả lập] CỐ Ý không ghi báo cáo ra %s" % a.ra)
        return a.ma_thoai
    if a.kieu == "json-hong":
        with open(a.ra, "w", encoding="utf-8") as f:
            f.write("{ day khong phai JSON hop le ,,,")
        print("[giả lập] đã ghi JSON HỎNG ra %s" % a.ra)
        return a.ma_thoai

    bc = {
        "dem": {"DAT": a.dat, "DAT_MOCK": 0, "HONG": a.hong, "BLOCKED": a.blocked,
                "BO_QUA": a.bo_qua},
        "buoc": [{"ma": "GL-%02d" % i, "trang_thai": "DAT"} for i in range(a.so_buoc)],
        "blocked": [{"ma": "GL-B%d" % i} for i in range(a.blocked)],
        "gia_lap": True,
    }
    if a.kieu == "thieu-khoa":
        bc.pop("buoc", None)
        bc.pop("dem", None)
    with open(a.ra, "w", encoding="utf-8") as f:
        json.dump(bc, f, ensure_ascii=False, indent=1)
    print("[giả lập] đã ghi báo cáo ra %s (kiểu %s)" % (a.ra, a.kieu))
    return a.ma_thoai


if __name__ == "__main__":
    sys.exit(main())
