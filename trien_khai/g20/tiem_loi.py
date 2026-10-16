#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 — TIÊM LỖI: chứng minh bộ phán của harness G20 ĐỎ ĐƯỢC.

====== VÌ SAO PHẢI CÓ TỆP NÀY ======
Một harness luôn in "ĐẠT" thì dòng "ĐẠT" ấy không có nghĩa. Câu hỏi duy nhất đáng hỏi về một
bộ phán là: *nó có ĐỎ được không, và đỏ vì ĐÚNG chỗ không?* Tệp này TIÊM lỗi vào một BẢN SAO
của hợp đồng thật rồi đòi harness phải báo đỏ.

BẢN SAO LÀ GÌ
------------
`ban_sao_hop_dong()` lấy hợp đồng THẬT (`hop_dong.json`), giữ nguyên **mọi chặng chạm hãng và
ngoài phạm vi** (chúng không thực thi gì, nên giữ lại là miễn phí), và thay ĐÚNG MỘT chặng
harness bằng `gia_lap_chang.py`. Nhờ vậy mỗi phép tiêm vẫn đi qua đúng bảy chốt an toàn thật,
đúng bộ đọc báo cáo thật, đúng bộ đối chiếu `mong_doi` thật — chỉ có thân của chặng là giả.

====== MƯỜI BA CA ======
| Mã | Tiêm gì vào bản sao | Phải ra |
|---|---|---|
| P0 | (ĐỐI CHỨNG DƯƠNG) chặng lành | `CHAY_DUOC`, mã thoát 0 |
| F01 | mã thoát 3 trong khi hợp đồng đòi 0 | `HONG` |
| F02 | không ghi báo cáo | `HONG` |
| F03 | ghi JSON hỏng | `HONG` |
| F04 | báo cáo thiếu khoá bắt buộc | `HONG` |
| F05 | báo cáo có 1 ca HỎNG (hợp đồng cho tối đa 0) | `HONG` |
| F06 | số BLOCKED lệch khai báo | `HONG` |
| F07 | số bước dưới ngưỡng khai báo | `HONG` |
| F08 | thiếu dấu vết stdout bắt buộc | `HONG` |
| F09 | gỡ chốt an toàn (`VIP_HUB_BIND=0.0.0.0`) | `KHONG_CHAY_DUOC`, KHÔNG đạt |
| F10 | khai `VIP_G20_GIAY_PHEP=V-G09-01` (tự cấp giấy phép) | cả lượt TỪ CHỐI, mã thoát 4 |
| F11 | đổi một chặng CHẠM HÃNG thành `loai: harness` (mở khoá lặng lẽ) | LỆCH khai báo ⇒ mã thoát 1 |
| F12 | hợp đồng RỖNG (0 chặng) | mã thoát 2 — chạy 0 chặng mà báo đạt là hỏng |

P0 là ca quan trọng nhất và dễ bị bỏ nhất: thiếu nó thì một bộ phán `return HONG` cho mọi
thứ cũng "bắt được" cả mười hai ca hỏng và trông như đang hoạt động.

CHẠY
----
    python3 trien_khai/g20/tiem_loi.py
    python3 trien_khai/g20/tiem_loi.py --giu-nen
"""
import argparse
import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile

THU_MUC_G20 = os.path.dirname(os.path.abspath(__file__))
DU_AN = os.path.dirname(os.path.dirname(THU_MUC_G20))
for _d in (THU_MUC_G20, os.path.join(DU_AN, "app")):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import chay_hop_dong as HD                                                   # noqa: E402

GIA_LAP = os.path.join(THU_MUC_G20, "gia_lap_chang.py")


def ban_sao_hop_dong():
    """Bản sao hợp đồng THẬT: giữ mọi chặng không-thực-thi, thay chặng harness bằng chặng giả."""
    with open(HD.HOP_DONG_MAC_DINH, encoding="utf-8") as f:
        that = json.load(f)
    gia = {
        "ma": "GIA-LAP",
        "ten": "CHẶNG GIẢ LẬP (tiêm lỗi) — không đo gì về dự án",
        "nhom": "gia-lap",
        "loai": "harness",
        "trang_thai_mong_doi": HD.CHAY_DUOC,
        "chot_can": ["N1", "N2", "N3", "N4", "N6", "N7"],
        "cham_hang": False,
        "giay_phep_can": [],
        "buoc": [{"ten": "chặng giả lập", "lenh": ["python3", GIA_LAP, "--ra",
                                                   "${NEN}/gia-lap.json"], "ma_thoai": 0}],
        "bien_moi_truong": {},
        "bao_cao_json": "${NEN}/gia-lap.json",
        "het_gio": 60,
        "mong_doi": {"khoa_bat_buoc": ["dem", "buoc"], "dem_hong_toi_da": 0, "so_blocked": 0,
                     "so_buoc_toi_thieu": 3, "dem_toi_thieu": {"DAT": 1},
                     "stdout_bat_buoc": ["báo cáo JSON:"], "stdout_cam": []},
        "pham_vi_ngoai": [],
    }
    khac = [copy.deepcopy(c) for c in that["chang"] if c.get("loai") != "harness"]
    sao = copy.deepcopy(that)
    sao["chang"] = [gia] + khac
    sao["so_chang_toi_thieu"] = len(sao["chang"])
    sao["ten"] = "BẢN SAO hợp đồng G20 — dùng cho bộ tiêm lỗi"
    return sao


def _tim(sao, ma):
    for c in sao["chang"]:
        if c["ma"] == ma:
            return c
    raise KeyError(ma)


def bo_ca():
    """[(mã, mô tả, hàm(sao) -> None, mã_thoát_mong_đội, trạng_thái_mong_đội_của_GIA-LAP)]."""
    def doi_lenh(sao, **them):
        b = _tim(sao, "GIA-LAP")["buoc"][0]
        for k, v in them.items():
            b[k] = v
        return sao

    def doi_mong_doi(sao, **them):
        _tim(sao, "GIA-LAP")["mong_doi"].update(them)
        return sao

    def f01(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--ma-thoai", "3"])

    def f02(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--kieu", "khong-ghi"])

    def f03(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--kieu", "json-hong"])

    def f04(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--kieu", "thieu-khoa"])

    def f05(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--hong", "1"])

    def f06(sao):
        return doi_lenh(sao, lenh=["python3", GIA_LAP, "--ra", "${NEN}/gia-lap.json",
                                   "--blocked", "4"])

    def f07(sao):
        return doi_mong_doi(sao, so_buoc_toi_thieu=99)

    def f08(sao):
        return doi_mong_doi(sao, stdout_bat_buoc=["DAU VET KHONG BAO GIO CO"])

    def f09(sao):
        # Chặng tự khai một biến môi trường PHÁ chốt của CHÍNH NÓ. Chốt tầng trên vẫn xanh
        # (env của harness điều phối sạch), nên ca này đo ĐÚNG đường "chặng TỰ CHỐI CHẠY".
        _tim(sao, "GIA-LAP")["bien_moi_truong"] = {"VIP_HUB_BIND": "0.0.0.0"}
        return sao

    def f09b(sao):
        # Gỡ chốt ở TẦNG TRÊN: env của chính harness điều phối bị bẩn ⇒ cả lượt phải TỪ CHỐI.
        os.environ["VIP_HUB_BIND"] = "0.0.0.0"
        return sao

    def f10(sao):
        os.environ["VIP_G20_GIAY_PHEP"] = "V-G09-01"
        return sao

    def f11(sao):
        # Ai đó "mở khoá" một chặng chạm hãng bằng cách đổi `loai` — harness phải thấy LỆCH.
        for c in sao["chang"]:
            if c.get("loai") == "cham-hang":
                c["loai"] = "harness"
                c["buoc"] = [{"ten": "chặng chạm hãng bị mở khoá lặng lẽ",
                              "lenh": ["python3", GIA_LAP, "--ra", "${NEN}/gia-lap-2.json",
                                       "--in-ra", "ok"],
                              "ma_thoai": 0}]
                c["bao_cao_json"] = "${NEN}/gia-lap-2.json"
                break
        return sao

    return [
        ("P0", "ĐỐI CHỨNG DƯƠNG — chặng lành trong bản sao phải ĐẠT", lambda s: s, 0, HD.CHAY_DUOC),
        ("F01", "mã thoát 3 trong khi hợp đồng đòi 0", f01, 1, HD.HONG),
        ("F02", "không ghi báo cáo", f02, 1, HD.HONG),
        ("F03", "ghi JSON hỏng", f03, 1, HD.HONG),
        ("F04", "báo cáo thiếu khoá bắt buộc", f04, 1, HD.HONG),
        ("F05", "báo cáo có 1 ca HỎNG (hợp đồng cho tối đa 0)", f05, 1, HD.HONG),
        ("F06", "số BLOCKED lệch khai báo", f06, 1, HD.HONG),
        ("F07", "số bước dưới ngưỡng khai báo", f07, 1, HD.HONG),
        ("F08", "thiếu dấu vết stdout bắt buộc", f08, 1, HD.HONG),
        ("F09", "chặng tự khai biến môi trường PHÁ chốt của chính nó", f09, 1,
         HD.KHONG_CHAY_DUOC),
        ("F09b", "gỡ chốt ở TẦNG TRÊN: env harness điều phối có VIP_HUB_BIND=0.0.0.0", f09b, 4,
         None),
        ("F10", "tự cấp giấy phép: VIP_G20_GIAY_PHEP=V-G09-01", f10, 4, None),
        ("F11", "một chặng CHẠM HÃNG bị đổi thành `loai: harness`", f11, 1, None),
        ("F12", "hợp đồng RỖNG (0 chặng)", None, 2, None),
    ]


def _chay_mot(ca_ma, ham_sua, sao_goc, nen, giu_nen):
    """Chạy harness trên một bản sao đã tiêm. Trả (mã_thoát, báo_cáo, stdout)."""
    sao = copy.deepcopy(sao_goc)
    if ca_ma == "F12":
        sao["chang"] = []
        sao["so_chang_toi_thieu"] = 0
    elif ham_sua is not None:
        sao = ham_sua(sao)

    duong_hd = os.path.join(nen, "hop-dong-%s.json" % ca_ma)
    duong_bc = os.path.join(nen, "bao-cao-%s.json" % ca_ma)
    with open(duong_hd, "w", encoding="utf-8") as f:
        json.dump(sao, f, ensure_ascii=False, indent=1)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ma = HD.main(["--hop-dong", duong_hd, "--nen", os.path.join(nen, "chay-%s" % ca_ma),
                      "--json", duong_bc])
    bc = None
    if os.path.isfile(duong_bc):
        try:
            with open(duong_bc, encoding="utf-8") as f:
                bc = json.load(f)
        except Exception:                                                   # noqa: BLE001
            bc = None
    return ma, bc, buf.getvalue()


def chay_tat_ca(cho_in=True, giu_nen=False):
    """Trả (tổng, số_hỏng, chi_tiết). Mỗi ca phải khớp CẢ mã thoát LẪN trạng thái chặng."""
    sao_goc = ban_sao_hop_dong()
    nen = tempfile.mkdtemp(prefix="g20_tiem_loi_")
    ket_qua, so_hong = [], 0
    os.environ.setdefault("VIP_HUB_DATA", nen)
    try:
        for ma, mo_ta, ham_sua, ma_thoai_md, trang_thai_md in bo_ca():
            for bien in ("VIP_HUB_BIND", "VIP_G20_GIAY_PHEP", "VIP_G17_GIAY_PHEP",
                         "VIP_G20_CHO_PHEP_GOI_HANG", "VIP_G17_CHO_PHEP_GOI_HANG"):
                os.environ.pop(bien, None)
            ma_thoai, bc, van_ban = _chay_mot(ma, ham_sua, sao_goc, nen, giu_nen)
            thuc_te_tt, ly = None, []
            if bc:
                for c in bc.get("chang", []):
                    if c.get("ma") == "GIA-LAP":
                        thuc_te_tt = c.get("trang_thai")
                        ly = c.get("ly_do", [])
            dung_ma = (ma_thoai == ma_thoai_md)
            dung_tt = (trang_thai_md is None) or (thuc_te_tt == trang_thai_md)
            dat = dung_ma and dung_tt
            if not dat:
                so_hong += 1
            ket_qua.append({"ma": ma, "mo_ta": mo_ta, "dat": dat,
                            "ma_thoai": ma_thoai, "ma_thoai_mong_doi": ma_thoai_md,
                            "trang_thai": thuc_te_tt, "trang_thai_mong_doi": trang_thai_md,
                            "ly_do": ly[:2]})
            if cho_in:
                print("  %s [%s] %s" % ("✓" if dat else "✗", ma, mo_ta))
                print("        mã thoát %s (đòi %s) · chặng GIA-LAP = %s (đòi %s)"
                      % (ma_thoai, ma_thoai_md, thuc_te_tt or "—", trang_thai_md or "—"))
                if not dat and ly:
                    print("        lý do harness đưa ra: %s" % ly[0][:150])
    finally:
        if not giu_nen:
            shutil.rmtree(nen, ignore_errors=True)
        else:
            print("  --giu-nen: giữ %s" % nen)
    return len(ket_qua), so_hong, ket_qua


def main(argv=None):
    ap = argparse.ArgumentParser(description="G20 — tiêm lỗi để chứng minh bộ phán ĐỎ ĐƯỢC")
    ap.add_argument("--giu-nen", action="store_true")
    a = ap.parse_args(argv)
    print("═" * 78)
    print("G20 — TIÊM LỖI VÀO BẢN SAO HỢP ĐỒNG: bộ phán của harness có ĐỎ ĐƯỢC không?")
    print("(bản sao giữ nguyên MỌI chặng chạm hãng + ngoài phạm vi của hợp đồng thật)")
    print("═" * 78)
    tong, so_hong, _ = chay_tat_ca(giu_nen=a.giu_nen)
    print("─" * 78)
    print("TIÊM LỖI: %d/%d ca đạt · %d hỏng" % (tong - so_hong, tong, so_hong))
    if so_hong:
        print("BỘ PHÁN HỎNG: có phép tiêm nó KHÔNG bắt được — hoặc bắt sai chỗ.")
        print("Mọi lời khai 'hợp đồng ĐẠT' ở lượt này KHÔNG có giá trị.")
        return 1
    print("Bộ phán ĐỎ ĐƯỢC ở cả %d phép tiêm, và XANH ở đối chứng dương P0." % (tong - 1))
    print("⇒ Lời khai 'chặng X ĐẠT/HỎNG' mới có nghĩa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
