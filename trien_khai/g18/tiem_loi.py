#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CHỨNG MINH NGƯỢC cho G18: tiêm lỗi vào BỘ ĐO và đòi bộ tự kiểm phải ĐỎ.

Vì sao cần tệp này: `harness_tai.py --tu-kiem` in ra "8/8 ca đạt". Một bộ tự kiểm LUÔN in "đạt"
cũng in ra đúng dòng ấy. Không có phép chứng minh ngược thì dòng "8/8" không có giá trị — đúng
luật của dự án (§7.1 BAN_GIAO: *"trước khi tin một con số, hỏi công cụ nào tạo ra nó, nó thật sự
kiểm cái gì"*).

Cách làm: nạp `harness_tai` theo đường dẫn (KHÔNG sao chép — bản sao sẽ lệch với bản thật), rồi
THAY một hàm phán quyết bằng bản hỏng, và chạy lại chính bộ tự kiểm. Mỗi phép tiêm phải làm bộ tự
kiểm báo HỎNG; nếu nó vẫn báo ĐẠT thì bộ tự kiểm ấy đang không kiểm gì cả.

CHẠY:  python3 trien_khai/g18/tiem_loi.py
"""
import importlib.util
import os
import sys

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUONG = os.path.join(DU_AN, "trien_khai", "g18", "harness_tai.py")


def nap():
    """Nạp MỚI mỗi lần — trạng thái tiêm của lượt trước không được rò sang lượt sau."""
    spec = importlib.util.spec_from_file_location("g18_ht_tiem", DUONG)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def chay(ten, tiem, mong_doi_hong):
    ht = nap()
    mo_ta = tiem(ht)
    t1, h1, _ = ht.tu_kiem_bo_do(cho_in=False)
    t2, h2, _ = ht.tu_kiem_tran(cho_in=False)
    tong, hong = t1 + t2, h1 + h2
    dung = (hong > 0) == mong_doi_hong
    print("  %s [%s] %s" % ("✓" if dung else "✗", ten, mo_ta))
    print("        bộ tự kiểm: %d/%d ca đạt · %d HỎNG · mong đợi có-hỏng=%s"
          % (tong - hong, tong, hong, mong_doi_hong))
    return dung


def main():
    print("═" * 78)
    print("CHỨNG MINH NGƯỢC: TIÊM LỖI VÀO BỘ ĐO CỦA G18")
    print("═" * 78)
    print("\n── ĐỐI CHỨNG DƯƠNG: không tiêm gì thì bộ tự kiểm phải ĐẠT ──────")
    ok = []

    def khong_tiem(ht):
        return "không tiêm gì — bộ tự kiểm phải ĐẠT (nếu không thì mọi ca dưới vô nghĩa)"
    ok.append(chay("T0", khong_tiem, mong_doi_hong=False))

    print("\n── TIÊM 1: `do_lanh` luôn trả True (bộ đo mù với mọi hỏng hóc) ──")

    def tiem_lanh(ht):
        ht.do_lanh = lambda sd: True
        return "`do_lanh` bị thay bằng hàm LUÔN trả True ⇒ ca BD4 (0 yêu cầu) phải ĐỎ"
    ok.append(chay("T1", tiem_lanh, mong_doi_hong=True))

    print("\n── TIÊM 2: `phan_quyet_tran` luôn trả ĐẠT ──────────────────────")

    def tiem_tran(ht):
        ht.phan_quyet_tran = lambda ds, tran, ma_chan=429, ma_cho_qua=401: (True, "luôn đạt")
        return "bộ phán quyết trần bị thay bằng hàm LUÔN ĐẠT ⇒ T2/T3/T4 phải ĐỎ"
    ok.append(chay("T2", tiem_tran, mong_doi_hong=True))

    print("\n── TIÊM 3: máy chủ giả KHÔNG BAO GIỜ hỏng (BD2/BD3 mất đối chứng) ─")

    def tiem_gia(ht):
        import http.server
        import threading

        class H(http.server.BaseHTTPRequestHandler):
            """Máy chủ giả LÀNH TUYỆT ĐỐI: mọi đường đều 200, không bao giờ cắt kết nối."""
            protocol_version = "HTTP/1.0"

            def log_message(self, *a):
                pass

            def do_GET(self):
                b = b'{"ok":true}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

        class MayLanh(object):
            def __init__(self):
                self.sv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
                self.cong = self.sv.server_address[1]
                threading.Thread(target=self.sv.serve_forever, daemon=True).start()

            def dung(self):
                self.sv.shutdown()
                self.sv.server_close()

        ht.MayChuGia = MayLanh
        return "máy chủ giả không còn hỏng theo chu kỳ ⇒ BD2 (5xx) và BD3 (cắt kết nối) phải ĐỎ"
    ok.append(chay("T3", tiem_gia, mong_doi_hong=True))

    print("\n" + "─" * 78)
    print("KẾT LUẬN: %d/%d phép tiêm cho kết quả MONG ĐỢI" % (sum(ok), len(ok)))
    if all(ok):
        print("Bộ tự kiểm của G18 ĐỎ ĐƯỢC: mỗi lỗi tiêm vào đều bị bắt. Con số '8/8 ca đạt'")
        print("trong báo cáo vì thế có nghĩa, không phải một dòng in sẵn.")
        return 0
    print("BỘ TỰ KIỂM KHÔNG ĐỎ ĐƯỢC ở ít nhất một phép tiêm ⇒ mọi lời khai 'đã tự kiểm' của")
    print("lượt này KHÔNG có giá trị.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
