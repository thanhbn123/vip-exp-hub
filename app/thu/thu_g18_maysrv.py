#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18-AG04 — MÁY CHỦ HTTP THẬT: bộ thử hồi quy cho BỘ ĐO và cho TRẦN TẦN SUẤT qua HTTP.

VÌ SAO CÓ TỆP NÀY
-----------------
`docs/BAN_GIAO.md` §6.1 mục **V-13914(b)** ghi *"máy chủ HTTP thật dưới tải"* — CHƯA AI ĐO, vì
mọi bàn đo trước đây gọi **thẳng hàm nghiệp vụ**, không đi qua `ThreadingHTTPServer`. Harness
`trien_khai/g18/harness_tai.py` đo được điều đó, nhưng một phép đo chạy một lần thì lượt sau có
thể làm hỏng nó mà không ai biết. Tệp này giữ phần ĐO ĐƯỢC LẶP LẠI trong bộ hồi quy.

BA NHÓM, VÀ NHÓM ĐẦU LÀ NHÓM DỄ BỊ BỎ QUA NHẤT
----------------------------------------------
  · `A_BoDo`  — **tự kiểm BỘ ĐO**: bắn bộ đo vào máy chủ giả LÀNH (phải 0 lỗi) và vào máy chủ
                giả CỐ TÌNH HỎNG (phải thấy 5xx · phải thấy lỗi kết nối). Không có nhóm này thì
                một bộ đo luôn báo "0 lỗi" cũng làm mọi ca ở nhóm C xanh.
  · `B_Tran`  — trần tần suất đi qua **HTTP THẬT**: đếm số lượt được qua trước lượt 429 đầu tiên,
                rồi so với cùng phép đếm khi **gọi thẳng hàm**. Hai đường phải khớp.
  · `C_Tai`   — máy chủ THẬT (`server.ThreadingHTTPServer`, `127.0.0.1` **cổng 0**) dưới tải, và
                **ĐỐI CHỨNG ÂM**: cùng kịch bản với MỘT luồng phải đúng và không lỗi.

BỘ ĐO ĐƯỢC MƯỢN, KHÔNG ĐƯỢC CHÉP LẠI
------------------------------------
Bộ đo tải và bộ phán quyết trần được nạp từ `trien_khai/g18/harness_tai.py` **theo đường dẫn**.
Chép lại thành bản thứ hai là kiểm một bộ đo KHÁC với bộ đo đã in ra các con số trong
`docs/G18_HTTP_SERVER.md` — bộ thử sẽ xanh trong khi bộ đo thật đã hỏng.

CÁI KHÔNG ĐO ĐƯỢC Ở ĐÂY, VÀ NÓI THẲNG RA
-----------------------------------------
  · **Số tiến trình**: bộ hồi quy chạy MỘT tiến trình (spawn tiến trình trong bộ thử định kỳ là
    nguồn hỏng ngẫu nhiên, xem §7.1 BAN_GIAO). Nó kiểm **CƠ CHẾ** làm trần nhân theo số bản
    (`b6`: trần nằm trong BỘ NHỚ, khởi động lại là đầy lại, và KHÔNG có bảng nào trong CSDL giữ
    bộ đếm). **CON SỐ** `2 tiến trình ⇒ trần 20` do harness đo (`harness_tai.py` G18-06a).
  · **`webhook.nhan` 600 lượt/60 giây**: gửi 640 lượt trong bộ hồi quy là quá chậm. Ở đây kiểm
    **hợp đồng** của luật (`b5`); **HÀNH VI** do harness đo (G18-03b).
  · Chưa đo: TLS thật · mạng thật · nhiều máy · gọi hãng kể cả sandbox (`V-G09-01` +
    `V-13906-05` CHƯA CẤP) · Docker.

CHẠY
----
    python3 app/thu/thu_g18_maysrv.py            # tự dựng nền TẠM, tự tắt máy chủ theo ĐÚNG PID
"""
import hashlib
import hmac
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

# `VIP_HUB_DATA` phải được đặt TRƯỚC khi nạp bất kỳ mô-đun nào của `app/`: `cau_hinh` đọc biến
# này ở thời điểm NẠP MÔ-ĐUN, nên đặt sau là mọi đường dẫn CSDL đã trỏ vào dữ liệu THẬT rồi.
_tam = tempfile.mkdtemp(prefix="vip-hub-g18-thu-")
os.environ["VIP_HUB_DATA"] = _tam
os.environ["VIP_HUB_BACKOFF"] = "0.01"
# Cờ gọi hãng phải TẮT: `V-G09-01` + `V-13906-05` CHƯA CẤP. Bộ thử này không chạm mạng.
os.environ.pop("VIP_G18_CHO_PHEP_GOI_HANG", None)
os.environ.pop("VIP_G18_GIAY_PHEP", None)

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)


def _nap_harness():
    """Nạp bộ đo THẬT theo đường dẫn — xem "BỘ ĐO ĐƯỢC MƯỢN" ở docstring đầu tệp."""
    duong = os.path.join(DU_AN, "trien_khai", "g18", "harness_tai.py")
    if not os.path.isfile(duong):
        raise RuntimeError("không thấy bộ đo tại %s — bộ thử này KHÔNG có bản sao của bộ đo,"
                           " nên thiếu nó là không kiểm được gì." % duong)
    spec = importlib.util.spec_from_file_location("g18_harness_tai", duong)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


HT = _nap_harness()

NEN = None      # SimpleNamespace dựng ở setUpModule: máy chủ THẬT + tenant + tài khoản hãng

# Bộ đếm `event_id` dùng chung cho CẢ MÔ-ĐUN, không phải cho từng lượt gọi.
#
# ĐO ĐƯỢC ngay ở lượt chạy đầu: bản đầu để bộ đếm BÊN TRONG `_ghi()`, nên mỗi lượt gọi lại bắt
# đầu từ 1. `test_c2` gửi `g18-thu-1..60`, rồi `test_c3` gửi lại ĐÚNG `g18-thu-1..30` — và vì
# `UNIQUE(carrier_account_id, event_id)` chặn trùng ở tầng CSDL, cả 30 lượt trả **200** ("đã nhận
# trước đó") thay vì **202**. Ca thử đỏ vì một lý do KHÔNG liên quan tới thứ nó muốn đo (một luồng
# so với tám luồng) — đúng khuôn "hỏng GIẢ vì hai ca thử chung một tài nguyên" mà §7.1 BAN_GIAO
# cảnh báo, chỉ khác là tài nguyên ở đây là không gian `event_id`.
_dem_su_kien = {"n": 0}
_khoa_su_kien = threading.Lock()


def _sql(q, ts=(), db=None):
    c = sqlite3.connect(db or os.path.join(_tam, "hub.db"), timeout=30)
    c.row_factory = sqlite3.Row
    try:
        return [dict(x) for x in c.execute(q, ts)]
    finally:
        c.close()


def setUpModule():
    """Dựng nền TẠM, máy chủ THẬT loopback cổng 0, tenant + tài khoản hãng MOCK."""
    global NEN
    import types
    n = types.SimpleNamespace()

    for lenh in ("migrate.py", "khoi_tao.py"):
        p = subprocess.run([sys.executable, os.path.join(GOC_APP, lenh)],
                           capture_output=True, text=True, cwd=DU_AN,
                           env=dict(os.environ, VIP_HUB_DATA=_tam))
        if p.returncode:
            raise RuntimeError("%s hỏng: %s" % (lenh, (p.stderr or p.stdout)[-500:]))

    # Bốn mô-đun này nạp vì TÁC DỤNG PHỤ (đăng ký adapter, mở CSDL, dựng ngữ cảnh) rồi được
    # lấy lại qua `sys.modules` — nên `# noqa: F401` ở đây là ĐÚNG, không phải import thừa.
    import bao_mat                                                     # noqa: F401
    import gioi_han                                                    # noqa: F401
    import server
    import webhook                                                     # noqa: F401

    n.gioi_han = sys.modules["gioi_han"]
    n.webhook = sys.modules["webhook"]

    # --- máy chủ THẬT, bind `127.0.0.1` CỔNG 0 (hệ điều hành cấp). Không cổng cố định: hai làn
    # chạy song song mà cùng một cổng cố định là hỏng GIẢ ngẫu nhiên, và đã có tiền lệ (§7.1).
    n.stderr_cu = sys.stderr
    sys.stderr = open(os.path.join(_tam, "stderr-server.log"), "w", encoding="utf-8")
    n.webhook.khoi_dong()
    n.sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
    n.cong = n.sv.server_address[1]
    threading.Thread(target=n.sv.serve_forever, name="g18-http", daemon=True).start()
    n.goc = "http://127.0.0.1:%d" % n.cong

    # --- tenant + tài khoản hãng MOCK qua HTTP THẬT (không nhồi thẳng CSDL: cửa tạo tài khoản
    # hãng là chỗ sinh `webhook_ma` và secret, và nó cũng là một phần của đường đang được đo).
    mk = dict(re.findall(r"`([a-z\-]+)` / `([^`]+)`",
                         open(os.path.join(_tam, "TAI-KHOAN-DEMO.md"), encoding="utf-8").read()))
    n.ck_po, ma = HT._khach_dang_nhap(n.cong, "platform-owner", mk["platform-owner"])
    if ma != 200:
        raise RuntimeError("đăng nhập platform-owner hỏng: HTTP %s" % ma)
    k_po = HT._khach_co_phien(n.cong, n.ck_po)
    ma, kq = k_po.json("POST", "/api/v2/platform/tenants",
                       {"ten": "Cty G18 BộThử", "owner_ten_dang_nhap": "g18-thu-owner",
                        "owner_mat_khau": "g18-thu-owner-123", "goi_id": "pro"})
    if ma != 201:
        raise RuntimeError("tạo tenant hỏng: HTTP %s · %s" % (ma, kq))
    n.ck_kh, ma = HT._khach_dang_nhap(n.cong, "g18-thu-owner", "g18-thu-owner-123")
    if ma != 200:
        raise RuntimeError("đăng nhập chủ tenant hỏng: HTTP %s" % ma)
    n.k_kh = HT._khach_co_phien(n.cong, n.ck_kh)
    ma, kq = n.k_kh.json("POST", "/api/v2/tai-khoan-hang",
                         {"hang": "jt", "ten": "J&T G18 BộThử",
                          "credentials": {"apiAccount": "demo", "privateKey": "demo-key"}})
    if ma != 201:
        raise RuntimeError("tạo tài khoản hãng hỏng: HTTP %s · %s" % (ma, kq))
    n.tk_id = kq["id"]
    n.wh_ma = (kq.get("webhook_url") or "").rsplit("/", 1)[-1]
    row = _sql("SELECT webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?", (n.tk_id,))[0]
    n.secret = bao_mat.giai_ma_wh(row["webhook_secret_ma_hoa"], n.wh_ma)
    NEN = n


def tearDownModule():
    if NEN is None:
        return
    try:
        NEN.webhook.dung()
        NEN.sv.shutdown()
        NEN.sv.server_close()
    finally:
        try:
            sys.stderr.flush()
            sys.stderr.close()      # đóng tệp log: không đóng thì Python cảnh báo ResourceWarning
            sys.stderr = NEN.stderr_cu
        except Exception:                                              # noqa: BLE001
            pass
        shutil.rmtree(_tam, ignore_errors=True)


# =======================================================================================
# A. TỰ KIỂM BỘ ĐO — nhóm dễ bị bỏ qua nhất, và là nhóm làm mọi nhóm khác có nghĩa
# =======================================================================================
class A_BoDo(unittest.TestCase):
    """Bộ đo tải phải PHÂN BIỆT ĐƯỢC máy chủ lành với máy chủ hỏng. Không cần CSDL, không HTTP thật."""

    def setUp(self):
        self.may = HT.MayChuGia()          # 127.0.0.1 CỔNG 0, ba đường: /lanh · /nam-tram · /cat-day
        self.addCleanup(self.may.dung)

    def _tai(self, duong, toi_da=60, so_luong=4):
        return HT.BoTai("127.0.0.1", self.may.cong, so_luong=so_luong).chay(
            ("GET", duong, None, None), toi_da=toi_da)

    def test_a1_may_chu_lanh_thi_khong_co_loi_nao(self):
        """ĐỐI CHỨNG DƯƠNG: thiếu ca này thì một bộ đo luôn báo 'có lỗi' cũng bắt được ca a2/a3."""
        sd = self._tai("/lanh")
        self.assertGreater(sd["tong"], 0, "bộ đo không chạy được lượt nào")
        self.assertEqual(sd["loi_ket_noi"], 0, "máy chủ lành mà bộ đo báo lỗi kết nối")
        self.assertEqual(sd["so_5xx"], 0, "máy chủ lành mà bộ đo báo 5xx")
        self.assertEqual(sd["theo_ma"].get("200"), sd["tong"], "có mã trạng thái lạ: %s" % sd["theo_ma"])
        self.assertTrue(HT.do_lanh(sd))

    def test_a2_may_chu_tra_500_thi_bo_do_PHAI_thay_5xx(self):
        """Bộ đo phải ĐỎ được. Một ca thử chỉ xanh không chứng minh được gì (§7.1 BAN_GIAO)."""
        sd = self._tai("/nam-tram")
        self.assertGreater(sd["so_5xx"], 0, "máy chủ trả 500 theo chu kỳ mà bộ đo không thấy 5xx")
        self.assertGreater(sd["ty_le_5xx"], 0.0)
        self.assertFalse(HT.do_lanh(sd))

    def test_a3_cat_ket_noi_thi_bo_do_PHAI_thay_loi(self):
        """Dạng hỏng mà một bộ đo chỉ đếm mã trạng thái sẽ bỏ qua HOÀN TOÀN."""
        sd = self._tai("/cat-day")
        self.assertGreater(sd["loi_ket_noi"], 0, "kết nối bị cắt mà bộ đo không thấy lỗi nào")
        self.assertFalse(HT.do_lanh(sd))

    def test_a4_khong_chay_luot_nao_thi_KHONG_duoc_coi_la_lanh(self):
        """ĐỐI CHỨNG ÂM CỦA CHÍNH BỘ ĐO.

        `loi_ket_noi == 0` và `so_5xx == 0` đều ĐÚNG khi không có lượt nào. Thiếu điều kiện
        `tong > 0` thì một bộ đo chưa chạy gì cũng báo "lành" — đây là chỗ sinh ra bảng tổng kết
        xanh giả, và nó không báo lỗi ở đâu cả.
        """
        sd = self._tai("/lanh", toi_da=0)
        self.assertEqual(sd["tong"], 0)
        self.assertEqual(sd["loi_ket_noi"], 0)
        self.assertEqual(sd["so_5xx"], 0)
        self.assertFalse(HT.do_lanh(sd), "0 lượt mà bị coi là 'lành' — bộ đo nói dối")

    def test_a5_phan_quyet_tran_dung_tren_bon_chuoi_tong_hop(self):
        """Bộ phán quyết trần: một chuỗi ĐÚNG và BA dạng chuỗi SAI, mỗi dạng một kiểu hỏng."""
        ca = [([401] * 10 + [429] * 3, True, "đúng: 10 qua rồi chặn"),
              ([401] * 13, False, "trần không chặn gì"),
              ([401] * 10 + [429, 401, 429], False, "chặn rồi CHO QUA LẠI"),
              ([401] * 4 + [429] * 3, False, "chặn sớm hơn khai báo")]
        for chuoi, mong_doi, mo_ta in ca:
            dat, ly_do = HT.phan_quyet_tran(chuoi, 10)
            self.assertEqual(dat, mong_doi, "ca %r phán sai: %s" % (mo_ta, ly_do))

    def test_a6_bo_do_tu_kiem_lam_do_duoc_bang_so_do_GIA(self):
        """TỰ KIỂM BỘ DÒ, không cần máy chủ: đưa thẳng số đo GIẢ và đòi `do_lanh` trả False.

        Vì sao cần: `test_a1` khẳng định `do_lanh(sd) is True`. Một hàm `do_lanh` luôn trả `True`
        cũng làm `a1` xanh — nên phải có ca này làm nó ĐỎ được, bằng số đo tổng hợp chứ không
        bằng máy chủ thật. Ba số đo giả: có 5xx · có lỗi kết nối · không có lượt nào.
        """
        gia = [({"tong": 100, "loi_ket_noi": 0, "so_5xx": 1}, "có 5xx"),
               ({"tong": 100, "loi_ket_noi": 3, "so_5xx": 0}, "có lỗi kết nối"),
               ({"tong": 0, "loi_ket_noi": 0, "so_5xx": 0}, "không có lượt nào")]
        for sd, mo_ta in gia:
            self.assertFalse(HT.do_lanh(sd), "số đo giả (%s) mà bị coi là lành" % mo_ta)
        self.assertTrue(HT.do_lanh({"tong": 100, "loi_ket_noi": 0, "so_5xx": 0}),
                        "số đo giả LÀNH mà bị coi là hỏng — bộ dò luôn trả False cũng vô dụng")


# =======================================================================================
# B. TRẦN TẦN SUẤT QUA HTTP THẬT
# =======================================================================================
class B_Tran(unittest.TestCase):
    """Trần của `app/gioi_han.py` khi đi qua `ThreadingHTTPServer`, so với khi gọi thẳng hàm."""

    def setUp(self):
        # `xoa_het()` là hàm dựng riêng cho bộ thử (chính docstring của nó ghi vậy). Không có nó
        # thì ca thứ hai bắt đầu từ bộ đếm của ca thứ nhất và con số ra là "trần trừ lượt trước".
        NEN.gioi_han.xoa_het()

    def _day_sai_chu_ky(self, wh_ma, so_lan):
        k = HT.KhachTai("127.0.0.1", NEN.cong)
        ds = []
        try:
            for _ in range(so_lan):
                ma, _, _ = k.goi("POST", "/api/v2/webhook/nhan/%s" % wh_ma, b"{}",
                                 {"X-Webhook-Signature": "0" * 64,
                                  "Content-Type": "application/json"})
                ds.append(ma)
        finally:
            k.dong()
        return ds

    def test_b1_tran_chu_ky_sai_qua_HTTP_dung_muoi_roi_429(self):
        """10 lượt/tài khoản/60 giây, rồi chặn LIÊN TỤC. Đo bằng HTTP THẬT, tuần tự một luồng."""
        ds = self._day_sai_chu_ky(NEN.wh_ma, 14)
        self.assertEqual(ds[:10], [401] * 10, "mười lượt đầu phải là 401 (chữ ký sai): %s" % ds)
        self.assertEqual(ds[10:], [429] * 4, "sau lượt thứ 10 phải là 429 LIÊN TỤC: %s" % ds)
        dat, ly_do = HT.phan_quyet_tran(ds, 10)
        self.assertTrue(dat, ly_do)

    def test_b2_hai_duong_cho_CUNG_mot_tran(self):
        """HTTP THẬT và GỌI THẲNG HÀM phải cho cùng một trần.

        Đây là câu hỏi trung tâm của V-13914(b): bàn đo cũ gọi thẳng hàm. Nếu đường HTTP cộng
        lượt khác đường hàm (ví dụ bỏ sót lượt 401, hoặc cộng hai lần cho một lượt) thì mọi con
        số trần đo bằng đường hàm đều KHÔNG nói gì về hệ đang chạy.
        """
        ds_http = self._day_sai_chu_ky(NEN.wh_ma, 14)
        NEN.gioi_han.xoa_het()
        ds_ham = ["cho_qua" if NEN.gioi_han.kiem(
            "webhook.chu_ky_sai", ip="127.0.0.1", dinh_danh="g18-b2").cho_phep else "chan"
            for _ in range(14)]
        self.assertEqual(ds_http.count(401), 10, "HTTP cho qua %d lượt" % ds_http.count(401))
        self.assertEqual(ds_ham.count("cho_qua"), 10, "hàm cho qua %d lượt" % ds_ham.count("cho_qua"))
        self.assertEqual(ds_http.count(401), ds_ham.count("cho_qua"),
                         "HAI ĐƯỜNG LỆCH NHAU — mọi số đo trần bằng đường hàm đều không dùng được")

    def test_b3_luot_CHI_XEM_khong_tieu_luot(self):
        """`_gioi_han(..., ghi_nhan=False)` là cổng CHỈ XEM ở đầu route webhook.

        Nếu nó CỘNG lượt thì mỗi sự kiện hợp lệ bị đếm HAI lần (một ở cổng xem, một ở chỗ chữ ký
        sai) và trần `webhook.chu_ky_sai` sẽ chặn hãng thật — đúng thứ mà `ghi_nhan=False` sinh ra
        để tránh. Ca này đếm số lượt ĐƯỢC QUA: phải là 10, không phải 5.
        """
        NEN.gioi_han.xoa_het()
        ds = self._day_sai_chu_ky(NEN.wh_ma, 11)
        self.assertEqual(ds[:10], [401] * 10,
                         "cổng CHỈ XEM đang cộng lượt: chỉ %d lượt qua trước khi bị chặn"
                         % len([x for x in ds if x == 401]))

    def test_b4_luot_bi_chan_tra_header_doc_duoc(self):
        """429 phải kèm `Retry-After` và `X-RateLimit-*` — nếu không, bên gọi không biết chờ bao lâu."""
        self._day_sai_chu_ky(NEN.wh_ma, 11)
        k = HT.KhachTai("127.0.0.1", NEN.cong)
        try:
            ma, hdr, _ = k.goi("POST", "/api/v2/webhook/nhan/%s" % NEN.wh_ma, b"{}",
                               {"X-Webhook-Signature": "0" * 64,
                                "Content-Type": "application/json"})
        finally:
            k.dong()
        self.assertEqual(ma, 429)
        self.assertTrue(str(hdr.get("retry-after") or "").isdigit(),
                        "429 thiếu `Retry-After` đọc được: %r" % hdr.get("retry-after"))
        self.assertGreater(int(hdr["retry-after"]), 0)
        self.assertEqual(hdr.get("x-ratelimit-limit"), "10")
        self.assertEqual(hdr.get("x-ratelimit-window"), "60")

    def test_b5_hop_dong_luat_webhook_nhan_khong_bi_doi_im_lang(self):
        """Hợp đồng của luật `webhook.nhan`: 600 lượt/60 giây theo tài khoản, 1200/60 theo IP.

        HÀNH VI (600 rồi 429) do harness đo ở G18-03b — gửi 640 lượt ở đây là quá chậm cho bộ hồi
        quy. Ở đây giữ HỢP ĐỒNG: ai nới trần (hoặc siết) mà không nói ra thì ca này ĐỎ.

        Vì sao đáng canh: cửa webhook là cửa VÔ DANH, và mỗi lượt chữ ký sai vẫn buộc hệ giải mã
        AES-GCM rồi tính HMAC. Nới trần ở đây là mở một đường làm kiệt máy miễn phí.
        """
        luats = NEN.gioi_han.luat_cua("webhook.nhan")
        self.assertEqual([(x.chieu, x.so_lan, x.cua_so_giay) for x in luats],
                         [("dinh_danh", 600, 60.0), ("ip", 1200, 60.0)])
        sai = NEN.gioi_han.luat_cua("webhook.chu_ky_sai")
        self.assertEqual([(x.chieu, x.so_lan, x.cua_so_giay, x.chan_giay) for x in sai],
                         [("dinh_danh", 10, 60.0, 300.0), ("ip", 30, 60.0, 300.0)])
        # Ổ KHOÁ: `webhook.chu_ky_sai` phải CHẶT HƠN `webhook.nhan`. Đảo lại thì trần chặt không
        # còn che được chi phí CPU, mà cũng chẳng có gì báo.
        self.assertLess(sai[0].so_lan, luats[0].so_lan)

    def test_b6_co_che_nhan_tran_theo_so_tien_trinh(self):
        """CƠ CHẾ làm trần nhân theo số bản (B-G11-10) — KHÔNG phải con số.

        Con số `2 tiến trình ⇒ trần 20` do harness đo (G18-06a, 5/5 lượt = 20). Ở đây kiểm hai
        mệnh đề làm con số ấy TẤT YẾU:
          (a) trần nằm trong BỘ NHỚ TIẾN TRÌNH: xoá trạng thái (tương đương khởi động lại) là
              TRẦN ĐẦY LẠI — nên N tiến trình ⇒ N lần trần;
          (b) KHÔNG có bảng nào trong CSDL giữ bộ đếm — nên các tiến trình KHÔNG dùng chung.
        Mệnh đề (b) là mệnh đề dễ bị bỏ: ai thêm một bảng đếm dùng chung mà quên sửa ca này thì
        bộ hồi quy vẫn xanh trong khi con số 2× đã hết đúng.
        """
        def muoi_mot(dd):
            return [NEN.gioi_han.kiem("webhook.chu_ky_sai", ip="127.0.0.1",
                                      dinh_danh=dd).cho_phep for _ in range(11)]

        NEN.gioi_han.xoa_het()
        lan1 = muoi_mot("g18-b6")
        self.assertEqual(lan1.count(True), 10, "lần đầu: %d lượt qua, mong đợi 10" % lan1.count(True))
        self.assertFalse(lan1[10])

        # (a) "khởi động lại tiến trình" = mất sạch trạng thái trong bộ nhớ
        NEN.gioi_han.xoa_het()
        lan2 = muoi_mot("g18-b6")
        self.assertEqual(lan2.count(True), 10,
                         "sau khi khởi động lại chỉ %d lượt qua — trần KHÔNG đầy lại thì cơ chế"
                         " 'N tiến trình = N lần trần' không còn đúng và mọi kết luận về B-G11-10"
                         " phải xét lại" % lan2.count(True))

        # (b) G19/AG-02: kho đếm NAY NẰM TRONG CSDL — DÙNG CHUNG qua tiến trình.
        #
        # Bản trước của chốt này khẳng định ĐIỀU NGƯỢC LẠI ("KHÔNG có bảng nào trong CSDL giữ bộ
        # đếm"), và chính docstring của nó đã cảnh báo: "ai thêm một bảng đếm dùng chung mà quên
        # sửa ca này thì bộ hồi quy vẫn xanh trong khi con số 2× đã hết đúng". AG-02 ĐÃ thêm bảng
        # đó ở G19 (chuyển PHẦN A sang khuôn PHẦN B), nên mệnh đề cũ nay SAI.
        # ⇒ Ca này đã KÊU đúng lúc — nó làm đúng việc của nó. Đây là ca thử ghim HÀNH VI CŨ, và
        #   khi hành vi cũ được sửa thì khẳng định phải viết lại — KHÔNG phải xoá ca.
        #
        # Nay khẳng định BẤT BIẾN MỚI, chiều ngược lại: PHẢI CÓ bảng đếm dùng chung. Ca vẫn có
        # răng theo chiều kia: ai GỠ bảng đó (quay lại bộ nhớ một tiến trình) thì ca này ĐỎ lại,
        # và lúc đó "N tiến trình = N lần trần" tái phát.
        #
        # Bằng chứng HÀNH VI (không chỉ sự tồn tại của bảng) nằm ở `app/thu/thu_g19_gioihan.py`
        # của AG-02 — nó đo bằng TIẾN TRÌNH THẬT, có đối chứng âm (bản đột biến quay lại kho bộ
        # nhớ vẫn ra 160). Ở đây giữ phép kiểm RẺ để bộ hồi quy nhanh vẫn bắt được hồi quy.
        bang = [r["name"] for r in _sql("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertGreater(len(bang), 0, "đọc không ra bảng nào — chốt (b) không kiểm được gì")
        dung_chung = [b for b in bang
                      if any(t in b.lower() for t in ("gioi_han", "rate_limit", "ratelimit", "bucket"))]
        self.assertNotEqual(
            dung_chung, [],
            "KHÔNG thấy bảng đếm dùng chung nào trong CSDL — nếu bộ đếm quay lại BỘ NHỚ TIẾN"
            " TRÌNH thì trần LẠI NHÂN theo số bản (B-G11-10 tái phát), và mọi kết luận 'trần dùng"
            " chung' phải xét lại. Bảng mong đợi: gioi_han_luot / gioi_han_chan")

    def test_b7_cua_so_truot_va_chan_co_thoi_han(self):
        """Cửa sổ TRƯỢT: hết cửa sổ thì lượt lại được qua. Luật tạm, TIÊM vào `CHINH_SACH`.

        Không tiêm thì phải chờ 60 giây thật — và một ca thử ngủ 60 giây sẽ bị gỡ khỏi bộ hồi quy
        vì chậm, tức là bất biến này mất ca canh. Luật tiêm được GỠ trong `finally`: để lại thì
        mọi ca sau nhìn thấy một `CHINH_SACH` khác với mã đang chạy.
        """
        TEN = "thu.g18.cua_so"
        cu = NEN.gioi_han.CHINH_SACH.get(TEN)
        NEN.gioi_han.CHINH_SACH[TEN] = (NEN.gioi_han.Luat("ip", 2, 0.5),)
        try:
            self.assertTrue(NEN.gioi_han.kiem(TEN, ip="10.9.9.9").cho_phep)
            self.assertTrue(NEN.gioi_han.kiem(TEN, ip="10.9.9.9").cho_phep)
            kq = NEN.gioi_han.kiem(TEN, ip="10.9.9.9")
            self.assertFalse(kq.cho_phep, "lượt thứ 3 vẫn qua — trần không chặn")
            self.assertGreater(kq.cho_bao_lau, 0)
            # IP KHÁC không bị ảnh hưởng: đây là ĐỐI CHỨNG DƯƠNG của "trần tách theo chiều".
            self.assertTrue(NEN.gioi_han.kiem(TEN, ip="10.9.9.10").cho_phep,
                            "IP khác cũng bị chặn — trần đang gộp mọi người vào một bucket")
            time.sleep(0.6)
            self.assertTrue(NEN.gioi_han.kiem(TEN, ip="10.9.9.9").cho_phep,
                            "hết cửa sổ mà vẫn bị chặn — đây là chặn VĨNH VIỄN, không phải trần")
        finally:
            NEN.gioi_han.CHINH_SACH.pop(TEN, None)
            if cu is not None:
                NEN.gioi_han.CHINH_SACH[TEN] = cu
            NEN.gioi_han.xoa_het()


# =======================================================================================
# C. MÁY CHỦ THẬT DƯỚI TẢI + ĐỐI CHỨNG ÂM
# =======================================================================================
class C_Tai(unittest.TestCase):
    """Cửa GHI và cửa ĐỌC dưới tải, qua `ThreadingHTTPServer` THẬT. Không 5xx, không lỗi kết nối."""

    def setUp(self):
        NEN.gioi_han.xoa_het()

    def _doc(self, so_luong, toi_da):
        return HT.BoTai("127.0.0.1", NEN.cong, so_luong=so_luong).chay(
            ("GET", "/api/v2/webhook/su-kien", None,
             {"Cookie": NEN.ck_kh, "X-Requested-With": "VIPHub"}), toi_da=toi_da)

    def _ghi(self, so_luong, so_luong_luong):
        """Ghi qua cửa webhook, `event_id` KHÁC nhau từng lượt.

        Nhồi cùng một `event_id` thì lượt thứ hai trở đi trả **200** (đã nhận trước đó) thay vì
        **202**, và phép đo "nhận sự kiện mới dưới tải" lặng lẽ biến thành phép đo chống trùng.
        """
        def sinh():
            with _khoa_su_kien:
                _dem_su_kien["n"] += 1
                i = _dem_su_kien["n"]
            b = json.dumps({"event": "dang_giao", "tracking_number": "G18-THU-%d" % i,
                            "event_id": "g18-thu-%d" % i,
                            "hang_luc": "2026-10-15T08:00:00+07:00"},
                           ensure_ascii=False).encode()
            return ("POST", "/api/v2/webhook/nhan/%s" % NEN.wh_ma, b,
                    {"X-Webhook-Signature": hmac.new(NEN.secret.encode(), b,
                                                     hashlib.sha256).hexdigest(),
                     "Content-Type": "application/json"})

        return HT._chay_tai_dong(NEN, so_luong, sinh, so_luong=so_luong_luong)

    def test_c1_cua_doc_duoi_tai_tam_luong(self):
        """8 luồng × 200 lượt: mã phải TOÀN 200, không 5xx, không lỗi kết nối."""
        sd = self._doc(so_luong=8, toi_da=200)
        self.assertEqual(sd["tong"], 200, "bộ đo không chạy đủ 200 lượt: %d" % sd["tong"])
        self.assertEqual(sd["loi_ket_noi"], 0, "lỗi kết nối: %s" % sd["ds_loi"])
        self.assertEqual(sd["so_5xx"], 0, "có 5xx dưới tải: %s" % sd["theo_ma"])
        self.assertEqual(sd["theo_ma"], {"200": 200}, "mã trạng thái lạ: %s" % sd["theo_ma"])
        self.assertGreater(sd["req_giay"], 0)

    def test_c2_cua_ghi_duoi_tai_va_so_dong_trong_csdl(self):
        """60 sự kiện, 8 luồng ⇒ 60 lượt 202 VÀ ĐÚNG 60 dòng trong `wh_su_kien`.

        Đếm dòng là phần không được bỏ: một máy chủ trả 202 mà không ghi được gì thì mọi phép đo
        tốc độ ở trên đều đang đo một đường ống rỗng.
        """
        truoc = _sql("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                     (NEN.tk_id,))[0]["c"]
        sd = self._ghi(so_luong=60, so_luong_luong=8)
        sau = _sql("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                   (NEN.tk_id,))[0]["c"]
        self.assertEqual(sd["tong"], 60)
        self.assertEqual(sd["loi_ket_noi"], 0, "lỗi kết nối: %s" % sd["ds_loi"])
        self.assertEqual(sd["so_5xx"], 0, "có 5xx dưới tải: %s" % sd["theo_ma"])
        self.assertEqual(sd["theo_ma"], {"202": 60}, "mã trạng thái lạ: %s" % sd["theo_ma"])
        self.assertEqual(sau - truoc, 60, "nhận 60 sự kiện mà CSDL chỉ thêm %d dòng" % (sau - truoc))

    def test_c3_DOI_CHUNG_AM_cung_kich_ban_mot_luong(self):
        """ĐỐI CHỨNG ÂM: CÙNG kịch bản với MỘT luồng ⇒ kết quả ĐÚNG và KHÔNG lỗi.

        Vì sao bắt buộc: "chạy 8 luồng không có 5xx" chỉ đáng tin nếu chính kịch bản ấy, chạy một
        luồng, cho ra kết quả đúng. Nếu bản một luồng cũng hỏng thì ca 8 luồng đang đo một hệ đã
        hỏng sẵn, và "không có 5xx" chỉ là may.
        """
        sd_doc = self._doc(so_luong=1, toi_da=30)
        self.assertEqual(sd_doc["theo_ma"], {"200": 30}, "ĐỌC một luồng: %s" % sd_doc["theo_ma"])
        self.assertEqual(sd_doc["loi_ket_noi"], 0)
        truoc = _sql("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                     (NEN.tk_id,))[0]["c"]
        sd_ghi = self._ghi(so_luong=30, so_luong_luong=1)
        sau = _sql("SELECT COUNT(*) c FROM wh_su_kien WHERE carrier_account_id=?",
                   (NEN.tk_id,))[0]["c"]
        self.assertEqual(sd_ghi["theo_ma"], {"202": 30}, "GHI một luồng: %s" % sd_ghi["theo_ma"])
        self.assertEqual(sau - truoc, 30)
        self.assertEqual(sd_ghi["loi_ket_noi"] + sd_ghi["so_5xx"], 0)

    def test_c4_moi_luot_HTTP_co_dau_vet(self):
        """`X-Request-Id` trên phản hồi, và log máy chủ THẬT có dòng JSON.

        P-G15-01 đã vá chuyện này (trước: 0 dòng JSON trên đường yêu cầu). Ca này giữ nó khỏi
        hỏng lại — và nó canh đúng đường HTTP THẬT, không phải gọi thẳng `quan_sat.ghi()`.
        """
        k = HT.KhachTai("127.0.0.1", NEN.cong)
        try:
            ma, hdr, _ = k.goi("GET", "/api/v2/webhook/su-kien", None,
                               {"Cookie": NEN.ck_kh, "X-Requested-With": "VIPHub"})
        finally:
            k.dong()
        self.assertEqual(ma, 200)
        self.assertTrue(hdr.get("x-request-id"), "phản hồi thiếu `X-Request-Id`")
        log = os.path.join(_tam, "stderr-server.log")
        so_json = 0
        if os.path.isfile(log):
            with open(log, encoding="utf-8", errors="replace") as f:
                so_json = sum(1 for d in f if d.lstrip().startswith("{"))
        self.assertGreater(so_json, 0, "log máy chủ THẬT không có dòng JSON nào (P-G15-01 sống lại)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
