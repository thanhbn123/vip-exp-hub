# G20/AG-06 — BỘ ĐO LỚP HTTP DÙNG CHUNG CHO HÃNG THỨ HAI ("ĐÃ HÃNG").
#
# CÂU HỎI BỘ NÀY TRẢ LỜI: lớp HTTP thật (`app/http_jt.py`) viết ở G16 cho RIÊNG J&T. Dự án khai
# là "trung tâm chuyển phát ĐA HÃNG". Vậy lớp đó có DÙNG LẠI ĐƯỢC cho hãng thứ hai không — và nếu
# không thì GẮN CHẶT ở đâu?
#
# CÂU TRẢ LỜI NGẮN (số đo đầy đủ ở `docs/G20_DA_HANG.md`):
#   · LÕI DÙNG LẠI ĐƯỢC. Một hãng giả thứ hai — khác J&T ở đúng ba chỗ AG-06 nêu (tên trường, định
#     dạng chữ ký, tên host) — chạy trọn qua `http_jt.gui_form` MÀ KHÔNG PHẢI SỬA MỘT KÝ TỰ nào
#     của `app/http_jt.py`. Bằng chứng: SHA256 đo trước/sau, cộng `git hash-object` khớp blob HEAD.
#   · NHƯNG CÓ ĐÚNG HAI CHỖ GẮN CHẶT, cả hai ĐO ĐƯỢC chứ không suy đoán:
#       (1) DANH SÁCH TRẮNG HOST là hằng số ĐÓNG (`HOST_HANG`). Hãng thứ hai chỉ chạy được vì
#           stub của nó nằm trên loopback. Địa chỉ THẬT của nó bị TỪ CHỐI với `ket_cuc='khong-gui-di'`
#           và **0 lượt nối**. Mở được chỉ bằng SỬA MÃ — không tham số, không sổ đăng ký.
#       (2) BẢNG TÊN CREDENTIAL là bảng của J&T (`TRUONG_CREDENTIAL`). Tầng che "theo TÊN" — tầng
#           BẮT BUỘC để che credential NGẮN — KHÔNG chuyển sang hãng thứ hai. ĐO ĐƯỢC: bí mật 5 ký
#           tự dưới tên J&T bị che; CÙNG giá trị đó dưới tên hãng giả RÒ nguyên văn vào
#           `than_da_che`, `headers_da_che` VÀ `str(e)`.
#   · Cộng hai ràng buộc HÌNH DẠNG (không phải "gắn vào J&T" mà là "gắn vào một khuôn giao thức"):
#     `gui_form` chỉ có POST, và thân chỉ có `x-www-form-urlencoded`.
#
# BA CHỐT AN TOÀN CỦA BỘ THỬ (theo AG-06 tuyệt đối (1),(2)):
#   · `ChanMangNgoai` thay `socket.socket.connect` bằng chốt chỉ cho loopback qua, CỘNG máy đếm.
#     Không có nó thì một URL gõ sai biến bộ thử thành một lượt gọi ra ngoài — và IM LẶNG.
#   · KHÔNG credential thật nào trong tệp này. Mọi "khoá" là chuỗi bịa sống trong tiến trình.
#   · KHÔNG đoán endpoint/anh xạ của hãng thật nào (AG-06 yêu cầu 3). Hãng thứ hai là HÃNG GIẢ
#     MẪU, đặt tên rõ, host đuôi `.invalid` (RFC 6761 §6.4 — không bao giờ phân giải được).
#
# PHẠM VI — NÓI THẲNG CÁI NẰM NGOÀI:
#   · KHÔNG đo được hành vi thật của J&T: chữ ký có được chấp nhận không, mã lỗi thật là gì, TLS,
#     hạn mức. V-G09-01/V-13906-05 CHƯA CẤP nên chưa từng có lượt gọi hãng nào. Bộ này XANH KHÔNG
#     phải lời cho phép gọi sandbox, và KHÔNG được đọc thành "LIVE VERIFIED".
#   · KHÔNG đo được hãng thật thứ hai nào. "Hãng thứ hai" ở đây là hãng BỊA. Kết luận rút ra là về
#     RÀNG BUỘC CỦA LỚP HTTP, không phải về một API cụ thể nào.
#   · KHÔNG đo được tầng nghiệp vụ (ánh xạ trạng thái, mã lỗi hãng, đối soát) — đó là việc của
#     adapter, không phải của lớp HTTP.
#
# HAI CHỐT CHẶN BẮT BUỘC CỦA DỰ ÁN (docs/QA_G13_G15.md §6.3):
#   1. TỰ KIỂM BỘ DÒ: mỗi bộ dò có ĐỐI CHỨNG ĐƯỜNG (nguồn KHÔNG đột biến ⇒ XANH) và ca ĐỘT BIẾN
#      (nguồn CÓ đột biến ⇒ ĐỎ). Lớp `CaTuKiem`.
#   2. ĐỐI CHỨNG DƯƠNG CHO MỌI CA PHỦ ĐỊNH: mỗi ca "phải bị từ chối" đi kèm khẳng định cửa đó MỞ
#      khi hợp lệ. Xem `CaGanChat.test_c1b` và mọi `assertTrue` đứng cạnh một `assertRaises`.
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # app/
GOC_DU_AN = os.path.dirname(GOC)                                       # gốc dự án
THU = os.path.dirname(os.path.abspath(__file__))                        # app/thu/
G20 = os.path.join(GOC_DU_AN, "trien_khai", "g20-dahang")               # làn AG-06
for _d in (GOC, THU, G20):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import http_jt                                                          # noqa: E402
import transport                                                        # noqa: E402
from stub_jt import StubJT                                              # noqa: E402
from stub_hang_gia import (DUONG_TAO_DON_GIA, HEADER_CHU_KY_GIA,        # noqa: E402
                           HEADER_TAI_KHOAN_GIA, HEADER_THOI_DIEM_GIA, HOST_GIA_THAT,
                           KHOA_GIA_DAI, KHOA_GIA_NGAN, StubHangGia, TAI_KHOAN_GIA,
                           TRUONG_THAN_GIA, ky_chu_ky_gia)

import phan_tich_gan_chat as PT                                         # noqa: E402

DUONG_HTTP = os.path.join(GOC, "http_jt.py")
DUONG_ADAPTER = os.path.join(GOC, "adapter_jt.py")

# Số ca XANH của bộ thử J&T ở G16/G19, đo trên chính cây này TRƯỚC khi AG-06 thêm gì
# (`python3 app/thu/thu_http_jt.py` → "Ran 57 tests … OK", exit 0). Đây là MỐC HỒI QUY: bộ đó
# không được tụt xuống dưới con số này.
MOC_THU_HTTP_JT = 57


def _sha256(duong):
    with open(duong, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _git(*a):
    """Chạy git với môi trường `GIT_CONFIG_*` đã gỡ.

    Vì sao phải gỡ: phiên nào đặt `GIT_CONFIG_COUNT` mà thiếu `GIT_CONFIG_KEY_*` thì MỌI lệnh git
    thoát 128 (N-G18-00). Một bộ thử đọc SHA qua git mà không gỡ sẽ HỎNG vì lý do không liên quan
    gì tới điều nó đang đo — đúng khuôn HỎNG GIẢ N-05.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=GOC_DU_AN, env=env)


# =================================================================================================
# CHỐT CHẶN MẠNG — chỉ loopback, và ĐẾM
# =================================================================================================
def _la_loopback(host):
    return host in ("127.0.0.1", "localhost", "::1") or str(host).startswith("127.")


class ChanMangNgoai:
    """Chốt chặn mạng của bộ thử này: chỉ loopback đi qua, mọi lượt nối đều được ĐẾM.

    Đây là chốt DUY NHẤT khiến câu "KHÔNG gọi API hãng kể cả sandbox" (AG-06 tuyệt đối (1)) trở
    thành khẳng định ĐO ĐƯỢC thay vì lời hứa: URL gõ sai trong bất kỳ ca nào ném `AssertionError`
    ngay, chứ không lặng lẽ thành một lượt gọi ra Internet. Nó cũng là MÁY ĐẾM cho khẳng định
    "TỪ CHỐI trước khi mở socket" (0 lượt nối).
    """

    def __init__(self):
        self._goc = None
        self.da_noi = []

    def bat(self):
        if self._goc is not None:
            return          # bọc hai lần thì mỗi lượt nối bị ĐẾM HAI LẦN, mọi ca đếm sẽ sai gấp đôi
        self._goc = socket.socket.connect
        goc = self._goc
        da_noi = self.da_noi

        def connect(sock, dia_chi, *a, **kw):
            host = dia_chi[0] if isinstance(dia_chi, (tuple, list)) and dia_chi else dia_chi
            cong = dia_chi[1] if isinstance(dia_chi, (tuple, list)) and len(dia_chi) > 1 else None
            da_noi.append((host, cong))
            if not _la_loopback(host):
                raise AssertionError(
                    f"CHẶN MẠNG: bộ thử định nối ra {dia_chi!r} — chỉ được loopback. "
                    "AG-06: V-G09-01/V-13906-05 CHƯA CẤP, không lượt gọi hãng nào được phép.")
            return goc(sock, dia_chi, *a, **kw)

        socket.socket.connect = connect

    def tat(self):
        if self._goc is not None:
            socket.socket.connect = self._goc
            self._goc = None

    def so_lan(self):
        return len(self.da_noi)

    def xoa(self):
        self.da_noi.clear()


CHAN = ChanMangNgoai()

# SHA của hai tệp của làn khác, chụp NGAY LÚC NẠP MÔ-ĐUN.
#
# Vì sao chụp lúc nạp chứ không trong `setUpModule`: `setUpModule` KHÔNG chạy khi ai đó gọi
# `unittest.main()` với tên lớp cụ thể (`python3 thu_g20_dahang.py CaGanChat`) — `loadTestsFromNames`
# không kéo theo fixture mức mô-đun. ĐO ĐƯỢC: ca `b6` nổ `KeyError: 'http_jt'` khi chạy riêng lớp.
# Một bằng chứng chỉ tồn tại khi chạy cả tệp là một bằng chứng ai đó sẽ vô tình tắt.
_SHA_LUC_NAP = {"http_jt": None, "adapter_jt": None}


def _chup_sha():
    _SHA_LUC_NAP["http_jt"] = _sha256(DUONG_HTTP)
    _SHA_LUC_NAP["adapter_jt"] = _sha256(DUONG_ADAPTER)
    return _SHA_LUC_NAP


_chup_sha()


def setUpModule():
    CHAN.bat()


def tearDownModule():
    CHAN.tat()


# =================================================================================================
# HAI HỒ SƠ HÃNG — CÙNG MỘT PHÉP ĐO CHẠY TRÊN CẢ HAI
# =================================================================================================
class HoSo:
    """Mọi thứ phép đo cần biết về MỘT hãng, để CÙNG MỘT hàm đo chạy được cho cả hai.

    Vì sao tách ra: đối chứng đường của AG-06 đòi "cùng bộ đo chạy lại trên J&T stub phải cho kết
    quả như trước". Nếu mỗi hãng có một hàm đo riêng thì phép so là so hai thứ khác nhau, và kết
    quả "giống nhau" không nói được gì.
    """

    def __init__(self, ten, lop_stub, bang_che_do, dung_yeu_cau):
        self.ten = ten
        self.lop_stub = lop_stub
        self.bang_che_do = bang_che_do            # tên chế độ chung → tên chế độ của stub đó
        self.dung_yeu_cau = dung_yeu_cau          # () → (headers, body)

    def mo(self, che_do="thanh_cong", **kw):
        return self.lop_stub(self.bang_che_do[che_do], **kw)

    def dat(self, stub, che_do):
        stub.dat_che_do(self.bang_che_do[che_do])
        return stub


CHE_DO_CHUNG = ("thanh_cong", "hang_tu_choi", "http_400", "http_401", "http_408", "http_429",
                "http_500", "cham", "cat_ket_noi")


def ho_so_jt():
    """Hồ sơ J&T: `bizContent` + `apiAccount`/`digest`/`timestamp`, chữ ký md5 — ĐÚNG như G16."""
    def dung_yeu_cau():
        biz = json.dumps({"txlogisticId": "VEH-G20-0001", "nguoiNhan": "Nguyễn Văn Ước"},
                         ensure_ascii=False, separators=(",", ":"))
        digest = base64.b64encode(hashlib.md5((biz + KHOA_GIA_DAI).encode()).digest()).decode()
        return ({"Content-Type": "application/x-www-form-urlencoded", "apiAccount": TAI_KHOAN_GIA,
                 "digest": digest, "timestamp": "1700000000000"}, {"bizContent": biz})

    return HoSo("J&T (stub_jt của G16)", StubJT,
                {"thanh_cong": StubJT.THANH_CONG, "hang_tu_choi": StubJT.HANG_TU_CHOI,
                 "http_400": StubJT.HTTP_400, "http_401": StubJT.HTTP_401,
                 "http_408": StubJT.HTTP_408, "http_429": StubJT.HTTP_429,
                 "http_500": StubJT.HTTP_500, "cham": StubJT.CHAM,
                 "cat_ket_noi": StubJT.CAT_KET_NOI},
                dung_yeu_cau)


def ho_so_gia():
    """Hồ sơ HÃNG GIẢ MẪU: khác J&T ở tên trường, định dạng chữ ký và đường dẫn. BỊA hoàn toàn."""
    def dung_yeu_cau():
        than = json.dumps({"maDonGia": "GG-G20-0001", "nguoiNhan": "Nguyễn Văn Ước"},
                          ensure_ascii=False, separators=(",", ":"))
        moc = "1700000000000"
        return ({"Content-Type": "application/x-www-form-urlencoded",
                 HEADER_TAI_KHOAN_GIA: TAI_KHOAN_GIA,
                 HEADER_CHU_KY_GIA: ky_chu_ky_gia(DUONG_TAO_DON_GIA, moc, than),
                 HEADER_THOI_DIEM_GIA: moc}, {TRUONG_THAN_GIA: than})

    return HoSo("HÃNG GIẢ MẪU (stub_hang_gia của AG-06)", StubHangGia,
                {"thanh_cong": StubHangGia.THANH_CONG, "hang_tu_choi": StubHangGia.HANG_TU_CHOI,
                 "http_400": StubHangGia.HTTP_400, "http_401": StubHangGia.HTTP_401,
                 "http_408": StubHangGia.HTTP_408, "http_429": StubHangGia.HTTP_429,
                 "http_500": StubHangGia.HTTP_500, "cham": StubHangGia.CHAM,
                 "cat_ket_noi": StubHangGia.CAT_KET_NOI},
                dung_yeu_cau)


def do_mot_luot(ho_so, che_do="thanh_cong", *, timeout=5.0, do_tre=None):
    """PHÉP ĐO DUY NHẤT, dùng cho CẢ HAI hãng. → dict KẾT CỤC (không chứa gì riêng của hãng).

    Đầu ra cố ý chỉ gồm thứ vendor-neutral (`lop`, `ma_http`, `ket_cuc`, `timeout`, `co_cho_giay`)
    nên hai hồ sơ SO ĐƯỢC VỚI NHAU. Chính vì thế nó là đối chứng đường: nếu lớp chung có nhánh
    riêng cho J&T thì hai cột lệch nhau ngay.
    """
    kw = {"do_tre": do_tre} if do_tre is not None else {}
    stub = ho_so.mo(che_do, **kw)
    try:
        headers, body = ho_so.dung_yeu_cau()
        try:
            kq = http_jt.gui_form(stub.url, headers, body, timeout=timeout)
            return {"lop": "TraLoiHTTP", "ma_http": kq.ma_http, "ket_cuc": "2xx",
                    "timeout": None, "co_cho_giay": None}
        except transport.LoiTamThoi as e:
            return {"lop": "LoiTamThoi", "ma_http": e.ma_http, "ket_cuc": e.ket_cuc,
                    "timeout": e.timeout, "co_cho_giay": getattr(e, "cho_giay", None) is not None}
        except transport.LoiVinhVien as e:
            return {"lop": "LoiVinhVien", "ma_http": e.ma_http, "ket_cuc": e.ket_cuc,
                    "timeout": e.timeout, "co_cho_giay": None}
    finally:
        stub.dung()


# =================================================================================================
# BỘ KHUNG
# =================================================================================================
class CaGoc(unittest.TestCase):
    """Bộ khung chung: mở stub (tự dọn), chờ stub ghi xong, chạy tiến trình con."""

    def mo(self, ho_so, **kw):
        stub = ho_so.mo(**kw)
        self.addCleanup(stub.dung)          # dọn cả khi ca HỎNG (không để lại cổng/tiến trình)
        return stub

    def cho_tra_loi(self, stub, so=1, het_gio=3.0):
        """Chờ stub GHI XONG phản hồi rồi mới so — nếu không là HỎNG GIẢ (bài học N-05).

        Stub ghi vào `da_tra_loi` SAU khi đã gửi byte đi (đó mới là bản ghi trung thực), nên
        client có thể nhận đủ thân rồi quay về TRƯỚC khi luồng máy chủ kịp ghi lại.
        """
        han = time.time() + het_gio
        while len(stub.da_tra_loi) < so and time.time() < han:
            time.sleep(0.005)
        self.assertGreaterEqual(len(stub.da_tra_loi), so,
                                f"stub chưa ghi nhận phản hồi nào sau {het_gio}s")
        return stub.da_tra_loi[-1]["than"]

    def chay_con(self, ma, het_gio=180):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CONFIG_")}
        return subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True,
                              timeout=het_gio, cwd=GOC, env=env)


# =================================================================================================
# A. RANH GIỚI BẰNG AST — CƠ CHẾ CHUNG vs ĐẶC THÙ J&T
# =================================================================================================
class CaRanhGioi(CaGoc):
    """Đo ranh giới bằng AST. Không mở socket, không gọi hãng — chỉ đọc cây cú pháp."""

    @classmethod
    def setUpClass(cls):
        cls.kq = PT.phan_tich(DUONG_HTTP, DUONG_ADAPTER)

    def _pl(self, ten):
        return self.kq["hang"][ten]["phan_loai"]

    # -- a1: hằng của HÃNG được nhận đúng, hằng CHUNG không bị nhận nhầm -------------------------
    def test_a1_hang_cua_hang_bi_gan_nhan_dung_va_nguong_chung_thi_khong(self):
        # CON SỐ GIM: tài liệu `docs/G20_DA_HANG.md` §3.1 trích đúng những con số này. Gim ở đây để
        # tài liệu và mã không trôi khỏi nhau — tài liệu trích một con số không ai kiểm là một lời
        # khai, không phải một phép đo.
        dem = {}
        for v in self.kq["hang"].values():
            dem[v["phan_loai"]] = dem.get(v["phan_loai"], 0) + 1
        self.assertEqual(dem, {"CHUNG": 19, "DAC_THU_JT": 3, "DAN_XUAT_TU_DAC_THU": 3},
                         f"bảng phân loại hằng đã đổi: {dem}")
        self.assertEqual(len(self.kq["hang"]), 25)
        for ten in ("HOST_HANG_SANDBOX", "HOST_HANG_PRODUCTION", "TRUONG_CREDENTIAL"):
            with self.subTest(hang=ten):
                self.assertEqual(self._pl(ten), "DAC_THU_JT")
        # Hằng DẪN XUẤT: không chứa literal của hãng nhưng CHỈ là hai hằng kia gộp lại.
        for ten in ("HOST_HANG", "TRUONG_CREDENTIAL_PHAN_HOI"):
            with self.subTest(hang=ten):
                self.assertEqual(self._pl(ten), "DAN_XUAT_TU_DAC_THU")
        # ĐỐI CHỨNG DƯƠNG (chiều ngược): ngưỡng chung KHÔNG được gán cho hãng. `DAI_TOI_THIEU_DE_CHE`
        # nằm ngay cạnh `TRUONG_CREDENTIAL` trong cùng hai hàm — một bộ dò thô sẽ nuốt nó.
        for ten in ("DAI_TOI_THIEU_DE_CHE", "HET_GIO_KET_NOI_TOI_DA", "CONTENT_TYPE_FORM",
                    "KET_CUC_KHONG_BIET", "HOST_CUC_BO"):
            with self.subTest(hang=ten):
                self.assertEqual(self._pl(ten), "CHUNG",
                                 f"{ten} là cơ chế CHUNG, không phải đặc thù J&T")

    # -- a2: hàm giữ chốt chặn hãng vs hàm lõi -----------------------------------------------
    def test_a2_hai_ham_giu_chot_chan_hang_bi_gan_nhan_dung(self):
        # CON SỐ GIM: `docs/G20_DA_HANG.md` §3.2 trích "7/37 hàm chạm đặc thù; 30 vendor-neutral".
        dem = {}
        for v in self.kq["ham"].values():
            dem[v["vai_tro"]] = dem.get(v["vai_tro"], 0) + 1
        self.assertEqual(dem, {"CHUNG": 30, "DAC_THU_JT": 7}, f"bảng phân loại hàm đã đổi: {dem}")
        for ten in ("host_duoc_phep", "tach_url"):
            with self.subTest(ham=ten):
                self.assertEqual(self.kq["ham"][ten]["vai_tro"], "DAC_THU_JT")
                self.assertIn("HOST_HANG", self.kq["ham"][ten]["hang_dac_thu"])
        # ĐỐI CHỨNG DƯƠNG: lõi gửi/nhận/che/phân loại KHÔNG chạm hằng đặc thù nào. Đây chính là
        # phần "cơ chế chung" mà hãng thứ hai dùng lại được.
        for ten in ("gui_form", "_tra_loi_tu_http", "che_bi_mat", "_loi_tu_ngoai_le",
                    "_chuan_bi_headers", "_ma_hoa_form", "_doc_retry_after", "mo_ta_yeu_cau"):
            with self.subTest(ham=ten):
                self.assertEqual(self.kq["ham"][ten]["hang_dac_thu"], [],
                                 f"{ten} phải vendor-neutral")

    # -- a3: KHÔNG ĐIỂM TIÊM — bằng chứng trung tâm của AG-06 --------------------------------
    def test_a3_bang_host_va_bang_credential_la_HANG_SO_DONG_khong_diem_tiem(self):
        """Không có tham số, không có sổ đăng ký: thêm hãng thứ hai chỉ còn đường SỬA MÃ."""
        self.assertTrue(self.kq["diem_tiem"], "bộ dò phải tìm thấy ít nhất một bảng đặc thù")
        for d in self.kq["diem_tiem"]:
            with self.subTest(bang=d["bang"]):
                self.assertTrue(d["dong_bang"],
                                f"{d['bang']} có đường ghi vào — đó là một ĐIỂM TIÊM:\n{d}")
                self.assertEqual(d["so_lan_gan"], 1)
                self.assertEqual(d["truyen_cho_ham_noi_bo"], [])
                self.assertEqual(d["bi_bien_doi"], [])
        # Chốt chặn thứ hai, đọc thẳng chữ ký hàm: không hàm nào nhận một BẢNG làm tham số.
        self.assertEqual(self.kq["ham"]["gui_form"]["tham_so"], ["url", "headers", "body", "timeout"])
        self.assertEqual(self.kq["ham"]["host_duoc_phep"]["tham_so"], ["host"])
        self.assertEqual(self.kq["ham"]["tach_url"]["tham_so"], ["url"])
        # Và không hàm nào trong mô-đun nhận tham số có hình dạng "bảng/whitelist".
        for ten, v in self.kq["ham"].items():
            for ts in v.get("tham_so", []):
                with self.subTest(ham=ten, tham_so=ts):
                    for tu in ("danh_sach", "whitelist", "cho_phep_host", "bang_truong", "so_do"):
                        self.assertNotIn(tu, ts.lower())

    # -- a4: canh lệch host giữa lớp HTTP và adapter (chốt chặn đã có từ G16, chạy lại) -------
    def test_a4_host_trong_http_jt_khong_troi_khoi_adapter_jt(self):
        self.assertEqual(self.kq["canh_lech_host_voi_adapter"], [],
                         "host trong `adapter_jt.HOST_API` không có trong `http_jt` (hoặc ngược lại)")
        # ĐỐI CHỨNG DƯƠNG: bộ dò canh lệch phải BẮT được khi hai bên trôi khỏi nhau.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            gia = os.path.join(td, "adapter_gia.py")
            with open(gia, "w", encoding="utf-8") as f:
                f.write('HOST_API = {"sandbox": "https://host-hoan-toan-khac.example"}\n'
                        'TRUONG_CREDENTIAL = ("apiAccount", "privateKey", "customerCode", "password")\n')
            kq2 = PT.phan_tich(DUONG_HTTP, gia)
            self.assertTrue(kq2["canh_lech_host_voi_adapter"],
                            "bộ dò canh lệch KHÔNG bắt được host trôi khỏi adapter — bộ dò hỏng")

    # -- a5: hai ràng buộc HÌNH DẠNG của lớp chung -------------------------------------------
    def test_a5_lop_chung_chi_co_POST_va_chi_co_form_urlencoded(self):
        """Đây là "gắn vào KHUÔN GIAO THỨC", không phải "gắn vào J&T" — nhưng vẫn là ràng buộc."""
        ds = self.kq["phuong_thuc_http"]
        self.assertEqual(len(ds), 1, f"chỉ có đúng một chỗ gọi .request(): {ds}")
        self.assertEqual(ds[0]["phuong_thuc"], "POST")
        # ĐỐI CHỨNG DƯƠNG: bộ dò đọc được phương thức từ AST và BẮT được khi nó khác đi.
        with self._nguon_tam("def x():\n    k.request('GET', '/a')\n") as duong:
            kq2 = PT.phan_tich(duong, DUONG_ADAPTER)
            self.assertEqual(kq2["phuong_thuc_http"][0]["phuong_thuc"], "GET")
        # Và kiểu thân: `_ma_hoa_form` chỉ nhận dict và chỉ sinh form-urlencoded.
        self.assertEqual(http_jt.CONTENT_TYPE_FORM, "application/x-www-form-urlencoded")
        with self.assertRaises(transport.LoiVinhVien):
            http_jt._ma_hoa_form('{"a":1}')          # chuỗi JSON: không phải dict
        self.assertTrue(http_jt._ma_hoa_form({"duLieuDon": "{}"}))   # đối chứng dương: dict thì được

    # -- a6: BẢNG 4 chỉ tính chuỗi CHẠY ĐƯỢC, không tính docstring ---------------------------
    def test_a6_nhan_hieu_hang_trong_thong_diep_chi_tinh_chuoi_CHAY_DUOC(self):
        """Docstring là literal trong cây cú pháp nhưng KHÔNG BAO GIỜ được in ra cho ai.

        Bài học `thu_bien_driver.py` ca a4 ("grep đọc cả chú thích") lặp lại y hệt ở tầng AST nếu
        không lọc: bản đầu của bộ dò báo 10 dòng "nhãn hiệu lộ" trong khi thực tế chỉ 4 dòng thật.
        """
        dong = [d["dong"] for d in self.kq["nhan_hieu_ten_hang"]]
        self.assertTrue(dong, "bộ dò phải tìm thấy nhãn hiệu hãng trong thông điệp thật")
        # 4 chỗ THẬT trong `http_jt.py`: hằng hai host (115,116), tiền tố `J&T/` của
        # `chan_moi_truong` (108), và thông điệp thân-rỗng của `_ma_hoa_form` (831).
        for d in (108, 115, 116, 831):
            with self.subTest(dong=d):
                self.assertIn(d, dong)
        # ĐỐI CHỨNG DƯƠNG hai chiều: nhãn trong DOCSTRING không được tính; nhãn trong THÔNG ĐIỆP
        # thật thì phải được tính. Cùng một chuỗi "J&T", hai vị trí, hai kết quả khác nhau.
        with self._nguon_tam('def f():\n    """J&T la hang gi."""\n    return 1\n') as duong:
            self.assertEqual(PT.phan_tich(duong, DUONG_ADAPTER)["nhan_hieu_ten_hang"], [],
                             "docstring bị tính nhầm là thông điệp chạy được")
        with self._nguon_tam('def f():\n    raise ValueError("J&T tu choi")\n') as duong:
            self.assertEqual([d["dong"] for d in
                              PT.phan_tich(duong, DUONG_ADAPTER)["nhan_hieu_ten_hang"]], [2])

    # -- a7: bảng 2b — nhánh mã bị ràng buộc hãng, đo ở CHỖ DÙNG -----------------------------
    def test_a7_bon_nhanh_ma_bi_rang_buoc_hang(self):
        nhanh = self.kq["nhanh_ma_gan_hang"]
        self.assertEqual([d["dong"] for d in nhanh], [285, 311, 343, 742],
                         f"các nhánh ràng buộc hãng đã đổi: {nhanh}")
        the_ham = {d["dong"]: d["ham"] for d in nhanh}
        self.assertEqual(the_ham[742], "tach_url")
        self.assertEqual(the_ham[285], "_gia_tri_trong_json")

    # tiện ích: ghi một nguồn Python tạm để đột biến
    class _nguon_tam:
        def __init__(self, noi_dung):
            self.noi_dung = noi_dung
            self.duong = None

        def __enter__(self):
            import tempfile
            self._td = tempfile.TemporaryDirectory()
            self.duong = os.path.join(self._td.name, "nguon_tam.py")
            with open(self.duong, "w", encoding="utf-8") as f:
                f.write(self.noi_dung)
            return self.duong

        def __exit__(self, *a):
            self._td.cleanup()


# =================================================================================================
# B. HÃNG GIẢ THỨ HAI CHẠY TRÊN LỚP CHUNG — KHÔNG SỬA `http_jt.py`
# =================================================================================================
class CaHangGiaChayDuoc(CaGoc):
    """Lớp chung có dùng lại được cho hãng thứ hai không. Mọi lượt đi tới stub loopback."""

    # -- b1: ĐẦU-CUỐI: gửi được, nhận được, byte đúng ----------------------------------------
    def test_b1_hang_gia_gui_duoc_dau_cuoi_qua_lop_chung(self):
        ho_so = ho_so_gia()
        stub = self.mo(ho_so)
        headers, body = ho_so.dung_yeu_cau()
        kq = http_jt.gui_form(stub.url, headers, body, timeout=5.0)
        self.assertEqual(kq.ma_http, 200)
        # Thân 2xx phải NGUYÊN VĂN (hợp đồng §36) — không được diễn giải lại.
        self.assertEqual(kq.than, self.cho_tra_loi(stub))
        yc = stub.yeu_cau[-1]
        # Đúng ba thứ AG-06 nêu là KHÁC J&T, và lớp chung không hề can thiệp vào chúng:
        self.assertEqual(yc.phuong_thuc, "POST")
        self.assertEqual(yc.duong_dan, DUONG_TAO_DON_GIA)          # (3) đường dẫn/tên host khác
        self.assertEqual(yc.form_value(TRUONG_THAN_GIA), body[TRUONG_THAN_GIA])   # (1) tên trường
        self.assertEqual(yc.header(HEADER_CHU_KY_GIA), headers[HEADER_CHU_KY_GIA])  # (2) chữ ký
        self.assertIsNone(yc.header("digest"), "không được có header của J&T")
        self.assertIsNone(yc.form_value("bizContent"), "không được có trường của J&T")

    def test_b2_chu_ky_hang_gia_KHAC_HAN_chu_ky_JT_va_van_di_nguyen_van(self):
        """Chữ ký khác thuật toán, khác nguyên liệu, khác khoá — lớp chung không được quan tâm."""
        than = "{}"
        ck_gia = ky_chu_ky_gia(DUONG_TAO_DON_GIA, "1700000000000", than)
        ck_jt = base64.b64encode(hashlib.md5((than + KHOA_GIA_DAI).encode()).digest()).decode()
        self.assertNotEqual(ck_gia, ck_jt, "hai công thức chữ ký phải KHÁC nhau, nếu không phép đo vô nghĩa")
        ho_so = ho_so_gia()
        stub = self.mo(ho_so)
        headers, body = ho_so.dung_yeu_cau()
        http_jt.gui_form(stub.url, headers, body, timeout=5.0)
        self.assertEqual(stub.yeu_cau[-1].header(HEADER_CHU_KY_GIA), headers[HEADER_CHU_KY_GIA],
                         "chữ ký phải lên dây NGUYÊN VĂN, lớp chung không được sửa")

    # -- b3: ba kết cục, đo trên hãng giả ------------------------------------------------------
    def test_b3_ba_ket_cuc_dung_tren_hang_gia(self):
        ho_so = ho_so_gia()
        for che_do, lop, ket_cuc, ma in (
                ("http_500", "LoiTamThoi", "khong-biet", 500),
                ("http_400", "LoiVinhVien", "hang-tu-choi", 400),
                ("http_401", "LoiVinhVien", "hang-tu-choi", 401),
                ("http_429", "LoiTamThoi", "qua-han-muc", 429),
                ("http_408", "LoiTamThoi", "khong-gui-di", 408),
                ("cat_ket_noi", "LoiTamThoi", "khong-biet", 0)):
            with self.subTest(che_do=che_do):
                kq = do_mot_luot(ho_so, che_do)
                self.assertEqual(kq["lop"], lop)
                self.assertEqual(kq["ket_cuc"], ket_cuc)
                self.assertEqual(kq["ma_http"], ma)
        # ĐỐI CHỨNG DƯƠNG: cùng bộ đo ấy, ở chế độ thành công, phải cho một `TraLoiHTTP` 2xx.
        kq = do_mot_luot(ho_so, "thanh_cong")
        self.assertEqual(kq["lop"], "TraLoiHTTP")
        self.assertEqual(kq["ma_http"], 200)

    def test_b4_429_doc_duoc_Retry_After_tren_hang_gia_va_KHONG_ngu(self):
        """`cho_giay` là GỢI Ý; lớp này KHÔNG BAO GIỜ NGỦ — việc chờ thuộc `transport.goi()`."""
        ho_so = ho_so_gia()
        stub = self.mo(ho_so, them_header={"Retry-After": "7"})
        ho_so.dat(stub, "http_429")
        headers, body = ho_so.dung_yeu_cau()
        t0 = time.time()
        with self.assertRaises(transport.LoiTamThoi) as cm:
            http_jt.gui_form(stub.url, headers, body, timeout=5.0)
        troi = time.time() - t0
        e = cm.exception
        self.assertEqual(e.ket_cuc, "qua-han-muc")
        self.assertEqual(e.cho_giay, 7.0)
        self.assertTrue(e.retry_after_bi_cat is False)
        self.assertLess(troi, 3.0, f"lớp HTTP đã NGỦ {troi:.1f}s — việc chờ không thuộc nó")
        # ĐỐI CHỨNG DƯƠNG: `Retry-After` vượt trần phải bị KẸP, không treo tiến trình.
        stub2 = self.mo(ho_so, them_header={"Retry-After": "86400"})
        ho_so.dat(stub2, "http_429")
        with self.assertRaises(transport.LoiTamThoi) as cm2:
            http_jt.gui_form(stub2.url, *ho_so.dung_yeu_cau(), timeout=5.0)
        self.assertEqual(cm2.exception.cho_giay, transport.CHO_TOI_DA)
        self.assertTrue(cm2.exception.retry_after_bi_cat)

    def test_b5_het_gio_doc_tren_hang_gia_la_KHONG_BIET(self):
        ho_so = ho_so_gia()
        kq = do_mot_luot(ho_so, "cham", timeout=0.4, do_tre=2.0)
        self.assertEqual(kq["lop"], "LoiTamThoi")
        self.assertEqual(kq["ket_cuc"], "khong-biet")
        self.assertTrue(kq["timeout"], "hết giờ ⇒ `timeout=True` (KHÔNG BIẾT kết quả)")
        # ĐỐI CHỨNG DƯƠNG: CÙNG chế độ chậm, chờ đủ lâu thì phải THÀNH CÔNG — nếu không thì ca
        # trên xanh chỉ vì stub chậm chứ không vì hạn đọc hoạt động.
        stub = self.mo(ho_so, do_tre=0.6)
        ho_so.dat(stub, "cham")
        kq_ok = self._mot_luot_tren_stub(stub, ho_so, timeout=5.0)
        self.assertEqual(kq_ok["lop"], "TraLoiHTTP")
        self.assertEqual(kq_ok["ma_http"], 200)

    def _mot_luot_tren_stub(self, stub, ho_so, *, timeout):
        headers, body = ho_so.dung_yeu_cau()
        try:
            kq = http_jt.gui_form(stub.url, headers, body, timeout=timeout)
            return {"lop": "TraLoiHTTP", "ma_http": kq.ma_http, "ket_cuc": "2xx"}
        except transport.LoiTamThoi as e:
            return {"lop": "LoiTamThoi", "ma_http": e.ma_http, "ket_cuc": e.ket_cuc}
        except transport.LoiVinhVien as e:
            return {"lop": "LoiVinhVien", "ma_http": e.ma_http, "ket_cuc": e.ket_cuc}

    # -- b6: BẰNG CHỨNG TRUNG TÂM: không phải sửa `http_jt.py` --------------------------------
    def test_b6_http_jt_KHONG_BI_SUA_trong_suot_luot_chay(self):
        self.assertEqual(_SHA_LUC_NAP["http_jt"], _sha256(DUONG_HTTP),
                         "`http_jt.py` đã đổi trong lượt chạy — mọi khẳng định 'không phải sửa' "
                         "trong tệp này mất hiệu lực")
        self.assertEqual(_SHA_LUC_NAP["adapter_jt"], _sha256(DUONG_ADAPTER),
                         "`adapter_jt.py` (tệp của làn khác) đã bị đụng vào")
        # Và bản trên đĩa phải TRÙNG blob ở HEAD: nếu không, "không sửa" chỉ là "không sửa thêm".
        p = _git("hash-object", "app/http_jt.py")
        self.assertEqual(p.returncode, 0, f"git hash-object hỏng: {p.stderr}")
        p2 = _git("rev-parse", "HEAD:app/http_jt.py")
        self.assertEqual(p2.returncode, 0, f"git rev-parse hỏng: {p2.stderr}")
        self.assertEqual(p.stdout.strip(), p2.stdout.strip(),
                         "`http_jt.py` trên đĩa KHÁC bản ở HEAD — tệp của làn khác đã bị đụng vào")
        # ĐỐI CHỨNG DƯƠNG: phép đo SHA này phải BẮT được một thay đổi thật.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "x.py")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write("a = 1\n")
            s1 = _sha256(f)
            with open(f, "a", encoding="utf-8") as fh:
                fh.write("# doi mot chut\n")
            self.assertNotEqual(s1, _sha256(f), "hàm băm không bắt được thay đổi ⇒ bằng chứng vô nghĩa")


# =================================================================================================
# C. HAI CHỖ GẮN CHẶT — ĐO ĐƯỢC, KÈM ĐỐI CHỨNG DƯƠNG
# =================================================================================================
class CaGanChat(CaGoc):
    """Đây là KẾT QUẢ của AG-06: chỗ nào bắt buộc phải SỬA `http_jt.py` mới có hãng thứ hai."""

    # -- c1: GẮN CHẶT 1 — danh sách trắng host là hằng số ĐÓNG --------------------------------
    def test_c1a_dia_chi_that_cua_hang_gia_bi_TU_CHOI_truoc_khi_mo_socket(self):
        url = f"https://{HOST_GIA_THAT}{DUONG_TAO_DON_GIA}"
        CHAN.xoa()
        truoc = CHAN.so_lan()
        with self.assertRaises(transport.LoiVinhVien) as cm:
            http_jt.gui_form(url, {"Content-Type": http_jt.CONTENT_TYPE_FORM},
                             {"duLieuDon": "{}"}, timeout=5.0)
        self.assertEqual(CHAN.so_lan(), truoc, "đã MỞ SOCKET trước khi từ chối host")
        e = cm.exception
        self.assertEqual(e.loai, "host-bi-tu-choi")
        self.assertEqual(e.ket_cuc, "khong-gui-di", "chưa ra khỏi máy ⇒ thử lại AN TOÀN")
        self.assertFalse(e.timeout)
        self.assertEqual(e.ma_http, 0)
        # Từ chối kèm LÝ DO đọc được, và lý do đó nói thẳng hãng thứ hai không có trong danh sách.
        self.assertIn("danh sách trắng", str(e))

    def test_c1b_DOI_CHUNG_DUONG_cung_url_do_tren_loopback_thi_MO(self):
        """Đối chứng dương bắt buộc: cửa đó MỞ khi host hợp lệ.

        Không có ca này thì ca c1a xanh vì `gui_form` hỏng với mọi thứ, chứ không vì danh sách
        trắng — và bộ thử sẽ khen nhầm chính chốt chặn nó đang muốn đo.
        """
        ho_so = ho_so_gia()
        stub = self.mo(ho_so)
        headers, body = ho_so.dung_yeu_cau()
        kq = http_jt.gui_form(stub.url, headers, body, timeout=5.0)
        self.assertEqual(kq.ma_http, 200)
        # `host_duoc_phep` là hàm của chốt chặn: loopback CÓ, hãng giả KHÔNG.
        self.assertTrue(http_jt.host_duoc_phep("127.0.0.1"))
        self.assertTrue(http_jt.host_duoc_phep("localhost"))
        self.assertFalse(http_jt.host_duoc_phep(HOST_GIA_THAT))
        for h in http_jt.HOST_HANG:
            self.assertTrue(http_jt.host_duoc_phep(h), "host của J&T phải nằm trong danh sách trắng")

    def test_c1c_bang_host_la_hang_so_DONG_nen_mo_ra_chi_bang_SUA_MA(self):
        """Không tham số, không sổ đăng ký: đo bằng AST, không bằng lời khai."""
        kq = PT.phan_tich(DUONG_HTTP, DUONG_ADAPTER)
        d = {x["bang"]: x for x in kq["diem_tiem"]}["HOST_HANG"]
        self.assertTrue(d["dong_bang"])
        self.assertEqual(d["so_lan_gan"], 1)
        self.assertEqual(d["truyen_cho_ham_noi_bo"], [])
        self.assertEqual(d["bi_bien_doi"], [])
        self.assertEqual(sorted(d["cach_dung"]),
                         ["', '.join(…) (đọc để in/dựng)", "in / not in (kiểm thành viên)"])
        # Hệ quả đo được: host của hãng giả KHÔNG THỂ vào danh sách bằng bất kỳ lời gọi nào.
        self.assertNotIn(HOST_GIA_THAT, http_jt.HOST_HANG)
        self.assertFalse(http_jt.host_duoc_phep(HOST_GIA_THAT))

    # -- c2: GẮN CHẶT 2 — bảng tên credential là bảng của J&T ---------------------------------
    def test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia(self):
        """MA TRẬN 2×2 — phép đo sắc nhất của AG-06.

                       | tên của J&T          | tên của HÃNG GIẢ
            NGẮN (5)   | che (theo TÊN)       | *** RÒ ***   ← gắn chặt
            DÀI (35)   | che (theo ĐỘ DÀI)    | che (theo ĐỘ DÀI)
        """
        ket_qua = {}
        for nhan, ten, gt in (("jt_ngan", "privateKey", KHOA_GIA_NGAN),
                              ("gia_ngan", "x-mau-khoa-bi-mat", KHOA_GIA_NGAN),
                              ("gia_ngan_2", "maTaiKhoanGia", KHOA_GIA_NGAN),
                              ("jt_dai", "privateKey", KHOA_GIA_DAI),
                              ("gia_dai", "x-mau-khoa-bi-mat", KHOA_GIA_DAI)):
            with self.subTest(ca=nhan):
                ket_qua[nhan] = self._co_ro(ten, gt)
        # Tầng che BẮT BUỘC (theo TÊN) chỉ đúng cho bốn tên của J&T.
        self.assertFalse(ket_qua["jt_ngan"], "credential NGẮN của J&T phải bị che")
        self.assertTrue(ket_qua["gia_ngan"],
                        "ĐỔI HÀNH VI: credential ngắn của hãng giả nay ĐƯỢC che — nếu ai đó vừa mở "
                        "rộng `TRUONG_CREDENTIAL`, hãy cập nhật tài liệu và ca này")
        self.assertTrue(ket_qua["gia_ngan_2"])
        # Tầng che theo ĐỘ DÀI thì vendor-neutral: cả hai hãng đều được che.
        self.assertFalse(ket_qua["jt_dai"])
        self.assertFalse(ket_qua["gia_dai"],
                         "tầng che theo ĐỘ DÀI phải vendor-neutral — nếu không, gắn chặt còn nặng hơn")

    def _co_ro(self, ten, gia_tri):
        """→ True nếu `gia_tri` RÒ ra ngoài khi hãng echo lại nó. Dùng stub ECHO của hãng giả."""
        stub = StubHangGia(StubHangGia.DOI_DAU)
        self.addCleanup(stub.dung)
        try:
            http_jt.gui_form(stub.url, {"Content-Type": http_jt.CONTENT_TYPE_FORM, ten: gia_tri},
                             {"truong": gia_tri}, timeout=5.0)
            self.fail("stub ECHO trả 401 — lớp HTTP phải NÉM, không được trả về")
        except transport.LoiVinhVien as e:
            return (gia_tri in e.than_da_che.decode("utf-8", "replace")
                    or gia_tri in str(e.headers_da_che)
                    or gia_tri in str(e))

    def test_c2b_DOI_CHUNG_DUONG_bon_ten_cua_JT_deu_nam_trong_bang(self):
        """Đối chứng dương: bảng không rỗng và khớp 100% với `adapter_jt.TRUONG_CREDENTIAL`.

        Không có ca này thì c2a có thể xanh vì bảng RỖNG (che được mọi thứ) — một cách xanh sai.
        """
        self.assertEqual(len(http_jt.TRUONG_CREDENTIAL), 4)
        import ast as _ast
        with open(DUONG_ADAPTER, encoding="utf-8") as f:
            cay = _ast.parse(f.read())
        goc = None
        for n in cay.body:
            if isinstance(n, _ast.Assign):
                for t in n.targets:
                    if isinstance(t, _ast.Name) and t.id == "TRUONG_CREDENTIAL":
                        goc = tuple(_ast.literal_eval(n.value))
        self.assertIsNotNone(goc, "không đọc được `adapter_jt.TRUONG_CREDENTIAL`")
        self.assertEqual({t.lower() for t in http_jt.TRUONG_CREDENTIAL},
                         {t.lower() for t in goc},
                         "bảng tên credential của `http_jt` đã trôi khỏi `adapter_jt`")
        # Và tên của hãng giả KHÔNG nằm trong bảng — đó chính là cơ chế của phép đo c2a.
        for ten in ("maTaiKhoanGia", "x-mau-khoa-bi-mat"):
            with self.subTest(ten=ten):
                self.assertNotIn(ten.lower(), http_jt.TRUONG_CREDENTIAL)
                self.assertNotIn(ten.lower(), http_jt.TRUONG_CREDENTIAL_PHAN_HOI)

    # -- c3: ràng buộc HÌNH DẠNG — chỉ POST, chỉ form ----------------------------------------
    def test_c3_lop_chung_khong_gui_duoc_JSON_va_khong_gui_duoc_GET(self):
        """Hãng thứ hai dùng JSON body hoặc GET sẽ KHÔNG dùng lại được lớp này, phải viết lớp mới."""
        import inspect
        self.assertNotIn("gui_json", dir(http_jt))
        self.assertNotIn("gui_get", dir(http_jt))
        self.assertEqual([p for p in inspect.signature(http_jt.gui_form).parameters],
                         ["url", "headers", "body", "timeout"])
        # `body` BẮT BUỘC là mapping — không có đường nào gửi một chuỗi JSON thô làm thân.
        with self.assertRaises(transport.LoiVinhVien) as cm:
            http_jt._ma_hoa_form(json.dumps({"duLieuDon": "{}"}))
        self.assertEqual(cm.exception.loai, "tham-so-sai")
        # ĐỐI CHỨNG DƯƠNG: mapping thì đi được, nên phép đo trên đo ĐÚNG ràng buộc kiểu dữ liệu,
        # không phải đo một hàm hỏng.
        self.assertTrue(http_jt._ma_hoa_form({"duLieuDon": "{}"}))

    # -- c4: nhãn hiệu trong thông điệp -------------------------------------------------------
    def test_c4_thong_diep_tu_choi_mang_nhan_hieu_JT_ke_ca_cho_hang_gia(self):
        """Không phải chặn kỹ thuật — nhưng người trực đọc log sẽ tưởng sự cố của J&T."""
        with self.assertRaises(PermissionError) as cm:
            http_jt.chan_moi_truong(http_jt.SANDBOX)
        self.assertIn("J&T", str(cm.exception))
        self.assertIn("V-G09-01", str(cm.exception))
        # ĐỐI CHỨNG DƯƠNG: `mock` phải MỞ — nếu không, ca trên xanh vì mọi môi trường đều bị chặn.
        self.assertIsNone(http_jt.chan_moi_truong(http_jt.MOCK))
        # Và đây là lý do hãng thứ hai chỉ chạy được ở mock: cả sandbox lẫn production đều ĐÓNG.
        for mt in (http_jt.SANDBOX, http_jt.PRODUCTION):
            with self.subTest(moi_truong=mt):
                with self.assertRaises(PermissionError):
                    http_jt.chan_moi_truong(mt)


# =================================================================================================
# D. ĐỐI CHỨNG ĐƯỜNG — KHÔNG HỒI QUY
# =================================================================================================
class CaDoiChungDuong(CaGoc):
    """Cùng bộ đo, chạy trên J&T stub, phải cho kết quả như trước."""

    def test_d1_CUNG_BO_DO_hai_hang_cho_CUNG_ket_cuc_tung_che_do(self):
        """Phép so trung tâm: một hàm đo, hai hãng, cùng bảng kết cục.

        Nếu lớp chung có nhánh riêng cho J&T (tên trường, chữ ký, host), hai cột sẽ lệch — vì
        hai hồ sơ khác nhau ở đúng ba thứ đó. Hai cột GIỐNG NHAU là bằng chứng lớp đó vendor-neutral
        ở phần phân loại kết cục.
        """
        jt, gia = ho_so_jt(), ho_so_gia()
        bang = {}
        for che_do in CHE_DO_CHUNG:
            kw = {"timeout": 0.4, "do_tre": 2.0} if che_do == "cham" else {}
            a = do_mot_luot(jt, che_do, **kw)
            b = do_mot_luot(gia, che_do, **kw)
            bang[che_do] = (a, b)
            self.assertEqual(a, b, f"chế độ {che_do}: J&T cho {a}, hãng giả cho {b}")
        # Chốt chặn chống "cả hai cùng rỗng": bảng phải có ĐỦ chín chế độ với kết cục cụ thể.
        self.assertEqual(len(bang), 9)
        self.assertEqual(bang["thanh_cong"][0]["lop"], "TraLoiHTTP")
        self.assertEqual(bang["http_500"][0]["ket_cuc"], "khong-biet")
        self.assertEqual(bang["http_400"][0]["ket_cuc"], "hang-tu-choi")
        self.assertEqual(bang["http_429"][0]["ket_cuc"], "qua-han-muc")
        self.assertEqual(bang["http_408"][0]["ket_cuc"], "khong-gui-di")
        self.assertTrue(bang["cham"][0]["timeout"])

    def test_d2_bo_thu_http_jt_cua_G16_van_XANH_nguyen_so_ca(self):
        """HỒI QUY THẬT: chạy lại nguyên bộ thử J&T của G16 trên cây này.

        Đây là đối chứng đường mà AG-06 đòi: bộ đo cũ phải cho kết quả như trước. Đếm cả SỐ CA,
        không chỉ mã thoát — một bộ thử bị ai đó rút bớt ca vẫn thoát 0, và mã thoát một mình là
        một lời khai không đủ (§12.1 luật 5).
        """
        p = self.chay_con("import unittest, sys\n"
                          f"sys.path.insert(0, {GOC!r})\n"
                          f"sys.path.insert(0, {THU!r})\n"
                          "import thu_http_jt\n"
                          "r = unittest.TextTestRunner(verbosity=0).run("
                          "unittest.TestLoader().loadTestsFromModule(thu_http_jt))\n"
                          "print('SO_CA=%d' % r.testsRun)\n"
                          "print('HONG=%d' % (len(r.failures) + len(r.errors)))\n"
                          "raise SystemExit(0 if r.wasSuccessful() else 1)\n", het_gio=600)
        self.assertEqual(p.returncode, 0,
                         f"bộ thử J&T của G16 HỎNG sau khi AG-06 thêm tệp:\n{p.stdout[-3000:]}\n"
                         f"{p.stderr[-2000:]}")
        so_ca = int([l for l in p.stdout.splitlines() if l.startswith("SO_CA=")][0].split("=")[1])
        hong = int([l for l in p.stdout.splitlines() if l.startswith("HONG=")][0].split("=")[1])
        self.assertEqual(hong, 0)
        self.assertGreaterEqual(
            so_ca, MOC_THU_HTTP_JT,
            f"bộ thử J&T tụt từ {MOC_THU_HTTP_JT} xuống {so_ca} ca — có ca bị RÚT BỚT")
        # Ghi lại con số THẬT của lượt này để tài liệu và bộ thử không trôi khỏi nhau.
        print(f"\n    [đối chứng đường] thu_http_jt: {so_ca} ca, {hong} hỏng, exit {p.returncode}")

    def test_d3_stub_hang_gia_va_stub_jt_deu_CHI_bind_loopback(self):
        """Cả hai stub phải chỉ bind loopback — nếu không, 'hãng giả' thành một cổng mở ra ngoài."""
        import inspect
        import stub_hang_gia as SHG
        import stub_jt as SJT
        for mod, ten in ((SHG, "stub_hang_gia"), (SJT, "stub_jt")):
            with self.subTest(module=ten):
                nguon = inspect.getsource(mod)
                self.assertIn('host="127.0.0.1"', nguon)
                self.assertIn("(host, 0)", nguon, "phải bind cổng 0 để không đụng làn khác")
        ho_so = ho_so_gia()
        stub = self.mo(ho_so)
        self.assertEqual(stub.may_chu.server_address[0], "127.0.0.1")
        self.assertNotEqual(stub.cong, 0)


# =================================================================================================
# E. TỰ KIỂM BỘ DÒ
# =================================================================================================
class CaTuKiem(CaGoc):
    """Mỗi bộ dò của tệp này phải BẮT được khi bị phá — kèm đối chứng dương.

    Không có lớp này thì mọi ca XANH ở trên chỉ nói "không có gì báo động", chứ không nói "báo
    động còn hoạt động". Đó là khác biệt giữa một bộ thử và một bảng trang trí.
    """

    def test_e1_chot_chan_mang_cua_CHINH_bo_thu_nay_hoat_dong(self):
        """Ca tự kiểm cho `ChanMangNgoai`: nối ra ngoài phải NỔ, nối loopback phải QUA."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(s.close)
        CHAN.xoa()
        with self.assertRaises(AssertionError) as cm:
            s.connect(("example.com", 80))
        self.assertIn("CHẶN MẠNG", str(cm.exception))
        self.assertEqual(CHAN.so_lan(), 1, "máy đếm phải ghi cả lượt nối BỊ CHẶN")
        # ĐỐI CHỨNG DƯƠNG: loopback phải đi qua được.
        ho_so = ho_so_gia()
        stub = self.mo(ho_so)
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(s2.close)
        s2.settimeout(3.0)
        s2.connect(("127.0.0.1", stub.cong))
        self.assertEqual(CHAN.so_lan(), 2)

    def test_e2_bo_do_phan_loai_ast_BAT_duoc_khi_bi_pha(self):
        """Đột biến cây cú pháp: mỗi luật phân loại phải ĐỔI KẾT QUẢ khi nguồn bị phá."""
        import tempfile

        def phan_tich_nguon(noi_dung):
            with tempfile.TemporaryDirectory() as td:
                f = os.path.join(td, "m.py")
                with open(f, "w", encoding="utf-8") as fh:
                    fh.write(noi_dung)
                return PT.phan_tich(f, DUONG_ADAPTER)

        # (a) ĐỐI CHỨNG ĐƯỜNG: nguồn sạch ⇒ hằng chung là CHUNG.
        sach = "GIOI_HAN = 5\n\ndef f():\n    return GIOI_HAN\n"
        self.assertEqual(phan_tich_nguon(sach)["hang"]["GIOI_HAN"]["phan_loai"], "CHUNG")
        # (b) ĐỘT BIẾN: nhét đúng tên host của hãng vào ⇒ phải thành DAC_THU_JT.
        dot = 'GIOI_HAN = "demoopenapi.jtexpress.vn"\n\ndef f():\n    return GIOI_HAN\n'
        self.assertEqual(phan_tich_nguon(dot)["hang"]["GIOI_HAN"]["phan_loai"], "DAC_THU_JT")
        # (c) ĐỘT BIẾN: dẫn xuất từ bảng credential ⇒ phải thành DAN_XUAT_TU_DAC_THU.
        dot2 = ('TRUONG_CREDENTIAL = ("apiAccount",)\n'
                'BANG_MO_RONG = TRUONG_CREDENTIAL + ("token",)\n')
        self.assertEqual(phan_tich_nguon(dot2)["hang"]["BANG_MO_RONG"]["phan_loai"],
                         "DAN_XUAT_TU_DAC_THU")

    def test_e3_bo_do_DIEM_TIEM_bat_duoc_mot_so_dang_ky_that(self):
        """Đối chứng dương mạnh nhất: nếu `http_jt` CÓ một sổ đăng ký host, bộ dò phải thấy."""
        import tempfile
        # Nguồn đột biến: một sổ đăng ký thật — gán lại bảng và cho một hàm nội bộ nhận nó.
        dot = ('HOST_HANG = ("demoopenapi.jtexpress.vn",)\n'
               'TRUONG_CREDENTIAL = ("apiAccount", "privateKey", "customerCode", "password")\n'
               'def dang_ky_host(bang):\n'
               '    return bang\n'
               'HOST_HANG = dang_ky_host(HOST_HANG + ("api.hang-2.invalid",))\n')
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "m.py")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(dot)
            kq = PT.phan_tich(f, DUONG_ADAPTER)
        d = {x["bang"]: x for x in kq["diem_tiem"]}["HOST_HANG"]
        self.assertFalse(d["dong_bang"], "bộ dò KHÔNG thấy sổ đăng ký ⇒ nó sẽ bỏ sót điểm tiêm thật")
        self.assertGreater(d["so_lan_gan"], 1)
        self.assertTrue(d["truyen_cho_ham_noi_bo"])
        # ĐỐI CHỨNG ĐƯỜNG: trên nguồn THẬT thì cùng bộ dò kết luận ngược lại.
        that = {x["bang"]: x for x in PT.phan_tich(DUONG_HTTP, DUONG_ADAPTER)["diem_tiem"]}
        self.assertTrue(that["HOST_HANG"]["dong_bang"])

    def test_e4_bo_do_che_bi_mat_bat_duoc_khi_ten_bi_pha(self):
        """Đối chứng dương cho phép đo c2a: nếu ai đó MỞ RỘNG bảng tên, ca c2a phải đổi kết quả.

        Đo bằng cách chạy lại đúng phép đo `_co_ro` với bảng tên đã được vá TẠM trong bộ nhớ
        (không ghi ra đĩa). Nếu vá mà kết quả không đổi thì ca c2a đang đo nhầm thứ khác.
        """
        goc = http_jt.TRUONG_CREDENTIAL_PHAN_HOI
        try:
            http_jt.TRUONG_CREDENTIAL_PHAN_HOI = goc + ("x-mau-khoa-bi-mat",)
            # `_MAU_CAP_TEN_BI_MAT` được dựng lúc nạp mô-đun nên phải dựng lại thì mới thấy.
            import re
            http_jt._MAU_CAP_TEN_BI_MAT = re.compile(
                r"(?i)(?<![\w-])(" + "|".join(re.escape(t) for t in
                                              sorted(http_jt.TRUONG_CREDENTIAL_PHAN_HOI,
                                                     key=len, reverse=True)) +
                r")(?![\w-])\s*[\"']?\s*[:=]\s*[\"']?([^\"'\s&,;<>)\]}\\{]{1,4096})")
            self.assertFalse(self._co_ro_gia("x-mau-khoa-bi-mat", KHOA_GIA_NGAN),
                             "vá bảng tên mà bí mật vẫn rò ⇒ phép đo c2a không đo bảng tên")
        finally:
            http_jt.TRUONG_CREDENTIAL_PHAN_HOI = goc
            import re
            http_jt._MAU_CAP_TEN_BI_MAT = re.compile(
                r"(?i)(?<![\w-])(" + "|".join(re.escape(t) for t in
                                              sorted(goc, key=len, reverse=True)) +
                r")(?![\w-])\s*[\"']?\s*[:=]\s*[\"']?([^\"'\s&,;<>)\]}\\{]{1,4096})")

    def _co_ro_gia(self, ten, gia_tri):
        stub = StubHangGia(StubHangGia.DOI_DAU)
        self.addCleanup(stub.dung)
        try:
            http_jt.gui_form(stub.url, {"Content-Type": http_jt.CONTENT_TYPE_FORM, ten: gia_tri},
                             {"truong": gia_tri}, timeout=5.0)
            self.fail("stub ECHO trả 401 — lớp HTTP phải NÉM")
        except transport.LoiVinhVien as e:
            return (gia_tri in e.than_da_che.decode("utf-8", "replace")
                    or gia_tri in str(e.headers_da_che))


if __name__ == "__main__":
    unittest.main(verbosity=2)
