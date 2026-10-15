# Chuẩn bị nền CÔ LẬP cho tầng 3 (trình duyệt thật).
#
# Chạy HAI PHA, vì hai pha cần hai thứ khác nhau:
#   pha "mk"  — chạy TRƯỚC khi mở máy chủ, thao tác thẳng trên CSDL: đặt lại mật khẩu của
#               các tài khoản demo về MỘT giá trị biết trước. `khoi_tao.py` sinh mật khẩu
#               ngẫu nhiên rồi ghi ra `TAI-KHOAN-DEMO.md`; đọc ngược file đó là thêm một
#               nguồn chân lý thứ hai, nên thà đặt lại thẳng.
#   pha "don" — chạy SAU khi máy chủ mở, tạo đơn qua HTTP THẬT như giao diện tạo. Cố ý
#               không `INSERT` thẳng vào bảng `don`: dữ liệu mẫu dựng theo giả định của
#               chính mình là thứ làm bộ thử ĐẠT trong khi hệ thật HỎNG.
#
# Mật khẩu ở đây là mật khẩu THỬ của một nền tạm, xoá khi script kết thúc. Nó không phải
# mật khẩu của ai, không dùng ở đâu khác, và nền này không bao giờ rời máy.
import json
import os
import sys
import urllib.error
import urllib.request

GOC_DU_AN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GOC_DU_AN, "app"))

MK = "MatKhauThu-GiaoDien-123"

# Tám đơn cho tenant Shop Demo A — đủ để bộ lọc có cái mà lọc, và các con số ở bộ thử
# (8 → 3 → 4) là số ĐẾM ĐƯỢC từ chính bảng dưới đây, không phải số chép từ tài liệu cũ.
DON_MAU = []
for _i in range(8):
    DON_MAU.append({
        "nguoi_gui_ten": "Shop Demo A", "nguoi_gui_sdt": "0901111111",
        "nguoi_gui_dia_chi": "1 Đường Thử, Hà Nội",
        "nguoi_nhan_ten": "Khách G12 số %d" % (_i + 1), "nguoi_nhan_sdt": "090222%04d" % _i,
        "nguoi_nhan_dia_chi": "%d Phố Thử, TP.HCM" % (_i + 2),
        "hang_hoa": "Kiện thử G12 số %d" % (_i + 1),
        "khoi_luong_gram": 500 + _i * 100,
        # Bốn đơn COD >= 300.000 và bốn đơn dưới — để ca lọc có hai phía.
        "cod": 350000 + _i * 1000 if _i % 2 == 0 else 120000 + _i * 1000,
    })


def pha_mk():
    import bao_mat
    import csdl
    csdl.mo()
    bam = bao_mat.bam_mat_khau(MK)
    n = csdl.ghi("UPDATE users SET mat_khau_hash = ?", (bam,)).rowcount
    csdl.dong()
    print("[chuan-bi] đã đặt lại mật khẩu cho %d tài khoản demo" % n)
    if n < 8:
        print("[chuan-bi] CHƯA ĐỦ tài khoản — seed hỏng?", file=sys.stderr)
        return 2
    return 0


class Phien:
    def __init__(self, goc):
        self.goc = goc
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None):
        body = json.dumps(du_lieu).encode() if du_lieu is not None else None
        h = {}
        if method != "GET":
            h["X-Requested-With"] = "VIPHub"
        if body is not None:
            h["Content-Type"] = "application/json"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request(self.goc + duong, data=body, headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=15) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                return ph.status, json.loads(ph.read() or b"{}")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"tho": raw[:200].decode("utf-8", "replace")}


def pha_don(goc):
    p = Phien(goc)
    st, kq = p.goi("/api/v2/auth/dang-nhap", "POST",
                   {"ten_dang_nhap": "shopa-owner", "mat_khau": MK})
    if st != 200:
        print("[chuan-bi] đăng nhập shopa-owner HỎNG: %s %s" % (st, kq), file=sys.stderr)
        return 2
    tao = 0
    for d in DON_MAU:
        st, kq = p.goi("/api/v2/don", "POST", d)
        if st != 201:
            print("[chuan-bi] tạo đơn HỎNG: %s %s" % (st, kq), file=sys.stderr)
            return 2
        tao += 1
    st, kq = p.goi("/api/v2/don?gioi_han=500")
    co = len(kq.get("don", [])) if st == 200 else -1
    print("[chuan-bi] đã tạo %d đơn; API đếm lại được %d đơn" % (tao, co))
    # Đếm lại từ chính máy chủ, không tin con số của vòng lặp ở trên (§12.1 luật 1).
    if co != tao:
        print("[chuan-bi] SỐ ĐƠN KHÔNG KHỚP — dừng", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    pha = sys.argv[1] if len(sys.argv) > 1 else ""
    if pha == "mk":
        sys.exit(pha_mk())
    if pha == "don":
        sys.exit(pha_don(sys.argv[2]))
    print("dùng: chuan_bi.py mk | chuan_bi.py don <goc_url>", file=sys.stderr)
    sys.exit(2)
