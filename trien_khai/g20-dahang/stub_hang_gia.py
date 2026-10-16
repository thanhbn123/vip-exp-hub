# G20/AG-06 — HÃNG GIẢ MẪU: stub loopback của một hãng CHUYỂN PHÁT THỨ HAI, KHÔNG phải J&T.
#
# ⚠️ ĐỌC DÒNG NÀY TRƯỚC: "HÃNG GIẢ MẪU" (`hang-gia-mau`) là một hãng do AG-06 TỰ ĐẶT RA. Nó
#    KHÔNG tồn tại. Mọi tên trường, đường dẫn, tên host và công thức chữ ký ở tệp này là BỊA có
#    chủ ý — không chép, không suy đoán, không "đoán gần đúng" từ bất kỳ API thật nào của bất kỳ
#    hãng nào. Không có endpoint thật nào bị đoán ở đây (yêu cầu 3 của AG-06).
#
#    Tên host dùng đuôi `.invalid` — RFC 6761 §6.4 dành riêng đuôi này và bảo đảm nó KHÔNG BAO
#    GIỜ phân giải được. Nhờ vậy, kể cả khi ai đó dán nhầm tên host giả vào một URL thật, lượt
#    gọi ĐỔ Ở TẦNG DNS chứ không đi đâu cả. Đây là chốt chặn thứ hai, độc lập với danh sách trắng.
#
# VÌ SAO CẦN HÃNG GIẢ NÀY: dự án tự khai là "trung tâm chuyển phát ĐA HÃNG", nhưng lớp HTTP thật
# (`app/http_jt.py`) được viết trong làn G16 cho RIÊNG J&T. Chưa ai ĐO xem lớp đó dùng lại được
# cho hãng thứ hai hay không. Hãng giả này là ĐỐI TƯỢNG ĐO: nó cố ý CHỈ KHÁC J&T ở đúng ba chỗ
# mà AG-06 nêu — (1) tên trường, (2) định dạng chữ ký, (3) tên host — và giống ở mọi chỗ còn lại
# (POST + `application/x-www-form-urlencoded`, thân là một chuỗi JSON nằm trong một trường form).
# Giống ở phần còn lại là CHỦ Ý: nếu nó khác cả giao thức thì phép đo sẽ nói "khác giao thức"
# chứ không nói được gì về chỗ GẮN CHẶT. Muốn đo dây ràng buộc thì phải giữ mọi thứ khác cố định.
#
# BA CHỐT AN TOÀN CỦA TỆP NÀY (AG-06 tuyệt đối (1) và (2)):
#   · bind `127.0.0.1` + cổng `0` (hệ điều hành tự cấp) — KHÔNG mở cổng ra ngoài, KHÔNG đụng
#     cổng của làn khác. Cổng cố định là `Address already in use` khi nhiều làn chạy song song.
#   · KHÔNG có credential thật nào trong tệp này. Ba "khoá" dưới đây là chuỗi bịa, chỉ sống trong
#     tiến trình bộ thử, và chúng tồn tại ĐÚNG để phép đo rò rỉ biết chính xác chuỗi cần tìm.
#   · Stub chỉ TRẢ LỜI trên socket do chính nó mở. Nó không bao giờ là client.
import base64
import hashlib
import hmac
import json
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

# ---- HỢP ĐỒNG CỦA HÃNG GIẢ MẪU (BỊA HOÀN TOÀN) -------------------------------------------------
TEN_HANG_GIA = "hang-gia-mau"
MO_TA_HANG_GIA = "HÃNG GIẢ MẪU do AG-06 tự đặt — không phải một hãng có thật"

# (3) TÊN HOST — khác J&T. Đuôi `.invalid` không phân giải được (RFC 6761 §6.4).
HOST_GIA_THAT = "api.hang-gia-mau.invalid"

# Đường dẫn bịa. Cố ý khác hình dạng `/webopenplatformapi/api/order/addOrder` của J&T.
DUONG_TAO_DON_GIA = "/cong-van/2/don/tao"

# (1) TÊN TRƯỜNG — khác J&T ở CẢ BA tầng: trường thân, header tài khoản, header chữ ký.
#
#        tầng            | J&T (thật, đã đọc tài liệu)  | hãng giả mẫu (BỊA)
#        ----------------+------------------------------+---------------------------
#        trường thân     | `bizContent`                 | `duLieuDon`
#        tài khoản       | header `apiAccount`          | header `X-Mau-Tai-Khoan`
#        chữ ký          | header `digest`              | header `X-Mau-Chu-Ky`
#        mốc thời gian   | header `timestamp`           | header `X-Mau-Thoi-Diem`
#        khoá bí mật     | `privateKey` (trong bizContent) | `khoaBiMatGia` (trong duLieuDon)
TRUONG_THAN_GIA = "duLieuDon"
HEADER_TAI_KHOAN_GIA = "X-Mau-Tai-Khoan"
HEADER_CHU_KY_GIA = "X-Mau-Chu-Ky"
HEADER_THOI_DIEM_GIA = "X-Mau-Thoi-Diem"

# TÊN TRƯỜNG CREDENTIAL CỦA HÃNG GIẢ — hai tên CỐ Ý KHÔNG nằm trong `http_jt.TRUONG_CREDENTIAL`
# (bốn tên của J&T) và cũng KHÔNG nằm trong `http_jt.TRUONG_CREDENTIAL_PHAN_HOI` (danh sách mở
# rộng theo tên). Đây là DỤNG CỤ ĐO cho phép đo gắn chặt số 2 — xem `thu_g20_dahang.CaGanChat`.
TRUONG_CREDENTIAL_GIA = ("maTaiKhoanGia", "khoaBiMatGia")
HEADER_CREDENTIAL_GIA = ("x-mau-khoa-bi-mat",)

# Ba giá trị BỊA dùng làm canary. Không có khoá thật nào tồn tại trong dự án (SHARED_CONTRACTS §38).
KHOA_GIA_DAI = "KHOA-GIA-MAU-G20-KHONG-PHAI-KHOA-THAT"      # ≥ 8 ký tự ⇒ bị che THEO ĐỘ DÀI
KHOA_GIA_NGAN = "A1b2C"                                       # 5 ký tự ⇒ chỉ che được nếu TÊN có trong bảng
TAI_KHOAN_GIA = "tk-gia-mau-g20"

# ---- (2) ĐỊNH DẠNG CHỮ KÝ — khác J&T ------------------------------------------------------------
# J&T (đã đọc tài liệu, `adapter_jt.ky_digest`):  base64( md5( bizContent + privateKey ) )
# Hãng giả mẫu (BỊA):                             base64( HMAC-SHA256( khoá, "<đường>|<mốc>|<thân>" ) )
#
# Cố ý khác ở BA điểm: thuật toán (HMAC-SHA256 vs md5 trần), nguyên liệu (có đường dẫn + mốc thời
# gian, không chỉ hai chuỗi nối), và khoá (khoá HMAC thật vs khoá nối chuỗi). Nếu lớp HTTP chung
# còn sống được với công thức khác hẳn thì nó KHÔNG ràng buộc vào chữ ký của J&T.
def ky_chu_ky_gia(duong, moc, than, khoa=KHOA_GIA_DAI):
    """Chữ ký của HÃNG GIẢ MẪU. BỊA — không mô phỏng hãng nào có thật."""
    nguyen_lieu = f"{duong}|{moc}|{than}".encode("utf-8")
    return base64.b64encode(
        hmac.new(khoa.encode("utf-8"), nguyen_lieu, hashlib.sha256).digest()).decode("ascii")


# ---- CÁC CHẾ ĐỘ TRẢ LỜI — mỗi chế độ là một KẾT CỤC khác nhau, không gộp ------------------------
THANH_CONG = "thanh_cong"          # 200 + {"maVanDon": …}          → hãng nhận đơn
HANG_TU_CHOI = "hang_tu_choi"      # 200 + {"maLoi": …}             → hãng TỪ CHỐI (biết chắc hỏng)
HTTP_400 = "http_400"              # 400                            → tham số/chữ ký sai
HTTP_401 = "http_401"
HTTP_408 = "http_408"              # → LoiTamThoi, khong-gui-di (hãng bảo chưa nhận kịp)
HTTP_429 = "http_429"              # → LoiTamThoi, qua-han-muc (hãng bảo chờ)
HTTP_500 = "http_500"              # 500                            → LoiTamThoi, khong-biet
DOI_DAU = "doi_dau"                # 401 + ECHO LẠI header+thân     → đo rò rỉ bí mật
CHAM = "cham"                      # ngủ `do_tre` giây rồi mới trả lời → ép client hết giờ ĐỌC
CAT_KET_NOI = "cat_ket_noi"        # nhận rồi ĐÓNG, không trả lời    → khong-biet

CHE_DO = (THANH_CONG, HANG_TU_CHOI, HTTP_400, HTTP_401, HTTP_408, HTTP_429, HTTP_500,
          DOI_DAU, CHAM, CAT_KET_NOI)

MA_HTTP_THEO_CHE_DO = {HTTP_400: 400, HTTP_401: 401, HTTP_408: 408, HTTP_429: 429, HTTP_500: 500}

DUONG_THONG_KE = "/__hang-gia-mau/thong-ke"


class YeuCauGia:
    """MỘT lượt yêu cầu stub đã nhận — bằng chứng THÔ, không diễn giải."""

    __slots__ = ("phuong_thuc", "duong_dan", "headers_goc", "than_tho", "luc")

    def __init__(self, phuong_thuc, duong_dan, headers_goc, than_tho):
        self.phuong_thuc = phuong_thuc
        self.duong_dan = duong_dan
        self.headers_goc = tuple(headers_goc)
        self.than_tho = bytes(than_tho)
        self.luc = time.time()

    @property
    def headers(self):
        ra = {}
        for ten, gt in self.headers_goc:
            ra[ten.lower()] = gt
        return ra

    def header(self, ten):
        return self.headers.get(ten.lower())

    @property
    def ten_header(self):
        return [ten for ten, _ in self.headers_goc]

    def form(self, giu_rong=True):
        return parse_qs(self.than_tho.decode("utf-8"), keep_blank_values=giu_rong)

    def form_value(self, ten):
        gt = self.form().get(ten) or []
        return gt[0] if gt else None

    def __repr__(self):
        return (f"YeuCauGia({self.phuong_thuc} {self.duong_dan}, {len(self.than_tho)} byte, "
                f"{len(self.headers_goc)} header)")


class MayChuGia(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True
    request_queue_size = 128

    def get_request(self):
        """Đếm ở TẦNG NHẬN KẾT NỐI, không ở tầng xử lý yêu cầu.

        Vì sao đếm ở đây: chế độ `CAT_KET_NOI` nhận kết nối rồi đóng mà KHÔNG đọc yêu cầu, nên
        một bộ đếm đặt trong `_nhan` sẽ báo 0 cho đúng lượt nối đã xảy ra. Số lượt nối là BẰNG
        CHỨNG cho khẳng định "TỪ CHỐI trước khi mở socket" — nó phải đếm được cả những lượt
        không đi tới đâu.
        """
        ket_noi, dia_chi = super().get_request()
        with self.stub._khoa:
            self.stub.so_ket_noi += 1
        return ket_noi, dia_chi


class StubHangGia:
    """Máy chủ HÃNG GIẢ MẪU, cục bộ, chạy trong tiến trình bộ thử. CHỈ bind `127.0.0.1`.

    Dùng:
        with StubHangGia() as stub:
            kq = http_jt.gui_form(stub.url, headers_gia(...), {"duLieuDon": …}, timeout=5)
    """

    THANH_CONG = THANH_CONG
    HANG_TU_CHOI = HANG_TU_CHOI
    HTTP_400 = HTTP_400
    HTTP_401 = HTTP_401
    HTTP_408 = HTTP_408
    HTTP_429 = HTTP_429
    HTTP_500 = HTTP_500
    DOI_DAU = DOI_DAU
    CHAM = CHAM
    CAT_KET_NOI = CAT_KET_NOI

    def __init__(self, che_do=THANH_CONG, *, do_tre=1.5, ma_loi="HGM-4001",
                 ma_van_don="HGM000000001VN", duong_mac_dinh=DUONG_TAO_DON_GIA,
                 host="127.0.0.1", them_header=None):
        self.che_do = che_do
        self.do_tre = do_tre
        self.ma_loi = ma_loi
        self.ma_van_don = ma_van_don
        self.duong_mac_dinh = duong_mac_dinh
        self.them_header = dict(them_header or {})
        self.yeu_cau = []
        self.da_tra_loi = []
        self._khoa = threading.Lock()
        self._hang_doi = deque()
        self.so_ket_noi = 0
        self.may_chu = MayChuGia((host, 0), _BoXuLyGia)
        self.may_chu.stub = self
        self._luong = threading.Thread(target=self.may_chu.serve_forever,
                                       kwargs={"poll_interval": 0.02}, daemon=True)
        self._luong.start()

    # -- vòng đời ------------------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.dung()

    def dung(self):
        try:
            self.may_chu.shutdown()
        except Exception:
            pass
        try:
            self.may_chu.server_close()
        except Exception:
            pass

    # -- địa chỉ -------------------------------------------------------------------------------
    @property
    def cong(self):
        return self.may_chu.server_address[1]

    @property
    def goc(self):
        return f"http://127.0.0.1:{self.cong}"

    @property
    def url(self):
        return self.goc + self.duong_mac_dinh

    def url_cho(self, duong):
        return self.goc + duong

    # -- điều khiển ----------------------------------------------------------------------------
    def dat_che_do(self, che_do, *, do_tre=None, ma_loi=None, ma_van_don=None):
        with self._khoa:
            self.che_do = che_do
            if do_tre is not None:
                self.do_tre = do_tre
            if ma_loi is not None:
                self.ma_loi = ma_loi
            if ma_van_don is not None:
                self.ma_van_don = ma_van_don
        return self

    def xoa_yeu_cau(self):
        with self._khoa:
            self.yeu_cau.clear()
            self.da_tra_loi.clear()
        return self

    @property
    def so_yeu_cau(self):
        with self._khoa:
            return len(self.yeu_cau)

    @property
    def than_tra_loi_cuoi(self):
        with self._khoa:
            return self.da_tra_loi[-1]["than"] if self.da_tra_loi else None

    def thong_ke(self):
        with self._khoa:
            return {"so_ket_noi": self.so_ket_noi, "so_yeu_cau": len(self.yeu_cau),
                    "so_tra_loi": len(self.da_tra_loi), "che_do": self.che_do}

    # -- dựng thân theo chế độ -----------------------------------------------------------------
    def _than_theo_che_do(self, yc, che_do):
        if che_do == THANH_CONG:
            return json.dumps({"maVanDon": self.ma_van_don, "trangThai": "da-tao"},
                              ensure_ascii=False).encode("utf-8")
        if che_do == HANG_TU_CHOI:
            return json.dumps({"maLoi": self.ma_loi, "thongDiep": "hãng giả mẫu từ chối đơn"},
                              ensure_ascii=False).encode("utf-8")
        if che_do == DOI_DAU:
            # ECHO LẠI NGUYÊN VĂN: mọi header đã nhận (trừ Content-Length để không phá giao thức)
            # và toàn bộ thân. Đây là stub TỆ NHẤT có thể — và đúng là thứ cần để đo rò rỉ.
            return yc.than_tho
        if che_do == HTTP_500:
            return "<html><body>502 Bad Gateway — hang-gia-mau</body></html>".encode("utf-8")
        return json.dumps({"maLoi": self.ma_loi, "cheDo": che_do}).encode("utf-8")

    def _tra_loi(self, bo_xu_ly, ma, than, headers_them=(), content_type=None):
        bo_xu_ly.send_response(ma)
        bo_xu_ly.send_header("Content-Type", content_type or "application/json; charset=utf-8")
        for ten, gt in dict(headers_them or {}).items():
            bo_xu_ly.send_header(ten, gt)
        bo_xu_ly.send_header("Content-Length", str(len(than)))
        bo_xu_ly.end_headers()
        bo_xu_ly.wfile.write(than)
        with self._khoa:
            self.da_tra_loi.append({"ma": ma, "than": than})


class _BoXuLyGia(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StubHangGia/1"
    sys_version = ""

    def log_message(self, *a):
        """KHÔNG in ra stdout/stderr: bộ thử đo cả hai luồng đó, in là làm bẩn phép đo."""

    def do_GET(self):
        if urlsplit(self.path).path == DUONG_THONG_KE:
            than = json.dumps(self.server.stub.thong_ke()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(than)))
            self.end_headers()
            self.wfile.write(than)
            return
        self._nhan("GET")

    def do_POST(self):
        self._nhan("POST")

    def do_PUT(self):
        self._nhan("PUT")

    def _nhan(self, phuong_thuc):
        stub = self.server.stub
        do_dai = int(self.headers.get("Content-Length") or 0)
        than = self.rfile.read(do_dai) if do_dai else b""
        yc = YeuCauGia(phuong_thuc, self.path, list(self.headers.items()), than)
        with stub._khoa:
            stub.yeu_cau.append(yc)
        self._xu_ly(yc)

    def _xu_ly(self, yc):
        stub = self.server.stub
        with stub._khoa:
            che_do = stub.che_do
            do_tre = stub.do_tre
        if che_do == CAT_KET_NOI:
            try:
                self.close_connection = True
                self.wfile.flush()
                self.connection.close()
            except Exception:
                pass
            return
        if che_do == CHAM:
            time.sleep(do_tre)
        than = stub._than_theo_che_do(yc, che_do)
        if che_do == DOI_DAU:
            # Echo header đã nhận (bỏ Content-Length: giá trị cũ sẽ cắt cụt thân mới).
            them = [(ten, gt) for ten, gt in yc.headers_goc if ten.lower() != "content-length"]
            stub._tra_loi(self, 401, than, them)
            return
        ma = MA_HTTP_THEO_CHE_DO.get(che_do, 200)
        stub._tra_loi(self, ma, than, stub.them_header)

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except (ConnectionResetError, BrokenPipeError, socket.timeout, OSError):
            self.close_connection = True
