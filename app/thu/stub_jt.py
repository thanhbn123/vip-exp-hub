# Stub J&T CỤC BỘ cho lớp HTTP G16 — CHỈ bind `127.0.0.1`, cổng 0 (hệ điều hành tự cấp).
#
# Vì sao cổng 0 chứ không phải cổng cố định: bốn làn G16 chạy ĐỒNG THỜI trong CÙNG một cây làm
# việc. Cổng cố định (8888/8899/9000…) là `Address already in use` khi hai làn trùng nhau — và
# lỗi đó TRÔNG Y HỆT một lỗi ngắt quãng của mã sản phẩm (bài học N-05 / R-13). Bind 127.0.0.1 +
# cổng 0 thì mỗi lượt chạy có cổng riêng, không bao giờ đụng làn khác, và KHÔNG mở ra Internet.
#
# Vì sao stub này nói đúng giao thức J&T: `bizContent` là một trường form chứa CHUỖI JSON, ba
# header `apiAccount`/`digest`/`timestamp` (nguồn: open.jtexpress.vn/apiDoc, xem adapter_jt §2).
# Nó ghi lại THÂN THÔ và HEADER NGUYÊN VĂN của từng lượt nhận, nên bộ thử đo được ĐÚNG NHỮNG BYTE
# đã gửi đi — chứ không đo bản mô tả của những byte ấy.
#
# Stub KHÔNG BAO GIỜ gọi ra ngoài: nó chỉ trả lời trên socket do chính nó mở ở loopback.
import json
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

# Đường dẫn mặc định = ĐÚNG đường tạo đơn đã đọc được trong tài liệu (`adapter_jt.DUONG_TAO_DON`).
DUONG_TAO_DON = "/webopenplatformapi/api/order/addOrder"

# ---- Các chế độ trả lời. Mỗi chế độ là một kết cục KHÁC NHAU, không gộp --------------------------
THANH_CONG = "thanh_cong"          # 200 + {"code":"1",…}            → hãng xác nhận
HANG_TU_CHOI = "hang_tu_choi"      # 200 + {"code":"<mã lỗi thật>"}  → hãng TỪ CHỐI (biết chắc hỏng)
HTTP_500 = "http_500"              # 500 thân KHÔNG phải JSON        → lỗi phía hãng
HTTP_400 = "http_400"              # 400                             → tham số/chữ ký sai
HTTP_401 = "http_401"
HTTP_403 = "http_403"
HTTP_404 = "http_404"
HTTP_408 = "http_408"
HTTP_429 = "http_429"
HTTP_302 = "http_302"              # chuyển hướng sang host KHÁC     → cấm đi theo
DOI_DAU = "doi_dau"                # 401 + ECHO LẠI header+thân (và digest vào header) → đo rò rỉ
CHAM = "cham"                      # ngủ `do_tre` giây rồi mới trả lời → ép client hết giờ ĐỌC
CAT_KET_NOI = "cat_ket_noi"        # nhận yêu cầu rồi ĐÓNG, không trả lời → KHÔNG BIẾT
THAN_THIEU = "than_thieu"          # 200 nhưng Content-Length > số byte thật → thân đọc dở

CHE_DO = (THANH_CONG, HANG_TU_CHOI, HTTP_500, HTTP_400, HTTP_401, HTTP_403, HTTP_404, HTTP_408,
          HTTP_429, HTTP_302, DOI_DAU, CHAM, CAT_KET_NOI, THAN_THIEU)

MA_HTTP_THEO_CHE_DO = {HTTP_400: 400, HTTP_401: 401, HTTP_403: 403, HTTP_404: 404, HTTP_408: 408,
                       HTTP_429: 429, HTTP_500: 500, HTTP_302: 302}


class YeuCau:
    """MỘT lượt yêu cầu stub đã nhận — bằng chứng thô, không diễn giải."""

    __slots__ = ("phuong_thuc", "duong_dan", "headers_goc", "than_tho", "luc")

    def __init__(self, phuong_thuc, duong_dan, headers_goc, than_tho):
        self.phuong_thuc = phuong_thuc
        self.duong_dan = duong_dan
        self.headers_goc = tuple(headers_goc)      # nguyên văn, giữ cả chữ hoa/thường và thứ tự
        self.than_tho = bytes(than_tho)            # ĐÚNG những byte đã nhận
        self.luc = time.time()

    @property
    def headers(self):
        """Dict tra theo tên KHÔNG phân biệt hoa/thường; trùng tên thì bản cuối thắng."""
        ra = {}
        for ten, gt in self.headers_goc:
            ra[ten.lower()] = gt
        return ra

    def header(self, ten):
        return self.headers.get(ten.lower())

    @property
    def ten_header(self):
        """TÊN header theo đúng thứ tự và chữ hoa/thường đã nhận trên dây."""
        return [ten for ten, _ in self.headers_goc]

    def form(self, giu_rong=True):
        """Trường form đã giải mã (UTF-8) — dùng `parse_qs` để `+` thành dấu cách như giao thức."""
        return parse_qs(self.than_tho.decode("utf-8"), keep_blank_values=giu_rong)

    def form_value(self, ten):
        gt = self.form().get(ten) or []
        return gt[0] if gt else None

    def __repr__(self):
        return (f"YeuCau({self.phuong_thuc} {self.duong_dan}, {len(self.than_tho)} byte, "
                f"{len(self.headers_goc)} header)")


class MayChuStub(ThreadingHTTPServer):
    daemon_threads = True       # luồng ngủ (chế độ CHAM) không được giữ tiến trình lại
    block_on_close = False      # và `server_close()` không được CHỜ chúng
    allow_reuse_address = True


class StubJT:
    """Máy chủ J&T giả, cục bộ, chạy được trong tiến trình bộ thử.

    Dùng:
        with StubJT(StubJT.THANH_CONG) as stub:
            kq = http_jt.gui_form(stub.url, headers, body, timeout=5)
            assert stub.yeu_cau[-1].than_tho == b"bizContent=..."
    """

    THANH_CONG = THANH_CONG
    HANG_TU_CHOI = HANG_TU_CHOI
    HTTP_500 = HTTP_500
    HTTP_400 = HTTP_400
    HTTP_401 = HTTP_401
    HTTP_403 = HTTP_403
    HTTP_404 = HTTP_404
    HTTP_408 = HTTP_408
    HTTP_429 = HTTP_429
    HTTP_302 = HTTP_302
    DOI_DAU = DOI_DAU
    CHAM = CHAM
    CAT_KET_NOI = CAT_KET_NOI
    THAN_THIEU = THAN_THIEU

    def __init__(self, che_do=THANH_CONG, *, do_tre=1.5, ma_loi="145005005",
                 thong_diep="获取运单号失败 — hãng không cấp được mã vận đơn",
                 ma_van_don="VH000000001VN", duong_mac_dinh=DUONG_TAO_DON,
                 host="127.0.0.1", them_header=None):
        if che_do not in CHE_DO:
            raise ValueError(f"chế độ lạ {che_do!r}; có {list(CHE_DO)}")
        self.che_do = che_do
        self.do_tre = do_tre
        self.ma_loi = ma_loi
        self.thong_diep = thong_diep
        self.ma_van_don = ma_van_don
        self.duong_mac_dinh = duong_mac_dinh
        self.yeu_cau = []
        self.da_tra_loi = []       # [{"ma": int, "than": bytes, "headers": {…}}, …]
        self.loi_may_chu = []      # lỗi phía stub (client cắt kết nối là chuyện thường ở đây)
        self.hang_doi = deque()
        # Header GẮN THÊM vào MỌI phản hồi (ví dụ `Retry-After`) — để đo đường 408/429 mà không
        # phải đẻ thêm một chế độ cho từng giá trị header.
        self.them_header = dict(them_header or {})
        self._may_chu = MayChuStub((host, 0), _BoXuLy)
        self._may_chu.stub = self
        self.cong = self._may_chu.server_address[1]
        self.host = host
        self._luong = threading.Thread(target=self._may_chu.serve_forever,
                                       kwargs={"poll_interval": 0.02}, daemon=True)
        self._luong.start()

    # ---- Vòng đời ----
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.dung()
        return False

    def dung(self):
        try:
            self._may_chu.shutdown()
        finally:
            self._may_chu.server_close()

    # ---- Địa chỉ ----
    @property
    def goc(self):
        return f"http://{self.host}:{self.cong}"

    @property
    def url(self):
        return self.goc + self.duong_mac_dinh

    def url_cho(self, duong):
        return self.goc + duong

    # ---- Lập trình phản hồi ----
    def dat_che_do(self, che_do, *, do_tre=None, ma_loi=None, thong_diep=None, ma_van_don=None,
                   them_header=None):
        if che_do not in CHE_DO:
            raise ValueError(f"chế độ lạ {che_do!r}; có {list(CHE_DO)}")
        self.che_do = che_do
        if do_tre is not None:
            self.do_tre = do_tre
        if ma_loi is not None:
            self.ma_loi = ma_loi
        if thong_diep is not None:
            self.thong_diep = thong_diep
        if ma_van_don is not None:
            self.ma_van_don = ma_van_don
        if them_header is not None:
            self.them_header = dict(them_header)

    def xep_hang_doi(self, *che_do):
        """Chế độ cho từng lượt KẾ TIẾP (để đo thử lại: 500, 500, thành công)."""
        for c in che_do:
            if c not in CHE_DO:
                raise ValueError(f"chế độ lạ {c!r}")
        self.hang_doi.extend(che_do)

    def _che_do_ke_tiep(self):
        return self.hang_doi.popleft() if self.hang_doi else self.che_do

    def xoa_yeu_cau(self):
        self.yeu_cau = []
        self.da_tra_loi = []

    # ---- Số đo ----
    @property
    def so_yeu_cau(self):
        return len(self.yeu_cau)

    @property
    def than_tra_loi_cuoi(self):
        return self.da_tra_loi[-1]["than"] if self.da_tra_loi else None

    # ---- Dựng thân trả lời ----
    def _than_theo_che_do(self, yeu_cau, che_do):
        if che_do == THANH_CONG:
            return 200, json.dumps(
                {"code": "1", "msg": "成功", "data": {"billCode": self.ma_van_don}},
                ensure_ascii=False).encode("utf-8"), {}
        if che_do == HANG_TU_CHOI:
            return 200, json.dumps(
                {"code": str(self.ma_loi), "msg": self.thong_diep, "data": None},
                ensure_ascii=False).encode("utf-8"), {}
        if che_do == HTTP_500:
            # Thân KHÔNG phải JSON: một lượt 5xx thật thường là trang lỗi của tầng proxy. Ca này
            # cũng chứng minh lớp HTTP là ống dẫn byte, KHÔNG đi parse JSON.
            return 500, b"<html><body>502 Bad Gateway</body></html>", {}
        if che_do == HTTP_302:
            # Chuyển hướng sang host KHÁC — đi theo là phá danh sách trắng máy chủ.
            return 302, b"", {"Location": "https://ke-tan-cong.invalid/webopenplatformapi/api"}
        if che_do == DOI_DAU:
            # Máy chủ "nói nhiều": echo nguyên header + thân yêu cầu vào thân trả lời, VÀ echo
            # digest vào một header phản hồi. Dùng để đo xem có rò rỉ bí mật ra ngoại lệ/log không.
            than_echo = {
                "code": "145003030", "msg": "请求头中的签名验证失败 — chữ ký trong header sai",
                "data": {"headers": {k: v for k, v in yeu_cau.headers_goc},
                         "than": yeu_cau.than_tho.decode("utf-8", "replace")}}
            return 401, json.dumps(than_echo, ensure_ascii=False).encode("utf-8"), {
                "X-Digest-Echo": yeu_cau.header("digest") or ""}
        if che_do in MA_HTTP_THEO_CHE_DO:
            ma = MA_HTTP_THEO_CHE_DO[che_do]
            return ma, json.dumps(
                {"code": str(self.ma_loi), "msg": self.thong_diep, "data": None},
                ensure_ascii=False).encode("utf-8"), {}
        raise ValueError(f"chế độ {che_do!r} không dựng được thân trả lời")

    def _tra_loi(self, bo_xu_ly, ma, than, headers_them, content_type=None):
        try:
            if content_type is None:
                content_type = ("text/html; charset=utf-8" if ma == HTTP_500
                                else "application/json; charset=utf-8")
            bo_xu_ly.send_response(ma)
            for ten, gt in {**self.them_header, **(headers_them or {})}.items():
                bo_xu_ly.send_header(ten, gt)
            bo_xu_ly.send_header("Content-Type", content_type)
            bo_xu_ly.send_header("Content-Length", str(len(than)))
            bo_xu_ly.end_headers()
            if than:
                bo_xu_ly.wfile.write(than)
            bo_xu_ly.wfile.flush()
            self.da_tra_loi.append({"ma": ma, "than": than,
                                    "headers": dict(headers_them or {})})
        except OSError as e:
            # Client đã bỏ đi (hết giờ) — chuyện thường ở các ca đo hết giờ, ghi lại chứ không in.
            self.loi_may_chu.append(f"{type(e).__name__}: {e}")


class _BoXuLy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "StubJT/1.0"
    sys_version = ""

    def log_message(self, *a):        # không in ra stdout/stderr: bộ thử đo cả hai luồng đó
        pass

    def do_GET(self):
        self._nhan("GET")

    def do_POST(self):
        self._nhan("POST")

    def do_PUT(self):
        self._nhan("PUT")

    def _nhan(self, phuong_thuc):
        stub = self.server.stub
        try:
            dai = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            dai = 0
        than = self.rfile.read(dai) if dai > 0 else b""
        yeu_cau = YeuCau(phuong_thuc, self.path, list(self.headers.items()), than)
        stub.yeu_cau.append(yeu_cau)
        che_do = stub._che_do_ke_tiep()
        if phuong_thuc != "POST":
            stub.da_tra_loi.append({"ma": 405, "than": b"", "headers": {}})
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if che_do == CAT_KET_NOI:
            # Nhận TRỌN yêu cầu rồi đóng kết nối mà KHÔNG trả lời: kết cục "KHÔNG BIẾT" thật sự,
            # khác hẳn "hết giờ" (client chờ) và khác "từ chối kết nối" (chưa gửi được gì).
            self.close_connection = True
            return
        if che_do == CHAM:
            # Ngủ TRƯỚC khi trả lời: client phải hết giờ ở giai đoạn "chờ phản hồi". Ghi lỗi đã
            # nằm trong `_tra_loi` (client bỏ đi là chuyện thường ở ca này).
            time.sleep(stub.do_tre)
            ma, than, headers_them = stub._than_theo_che_do(yeu_cau, THANH_CONG)
            stub._tra_loi(self, ma, than, headers_them)
            self.close_connection = True
            return
        if che_do == THAN_THIEU:
            # Khai Content-Length LỚN HƠN số byte thật gửi, rồi ngủ: client hết giờ NGAY GIỮA lúc
            # đọc thân của một lượt HTTP 200. Đây là ca then chốt: thân đọc dở TUYỆT ĐỐI không được
            # biến thành một `TraLoiHTTP` thành công.
            ma, than, headers_them = stub._than_theo_che_do(yeu_cau, THANH_CONG)
            try:
                self.send_response(ma)
                for ten, gt in stub.them_header.items():
                    self.send_header(ten, gt)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(than) + 200))
                self.end_headers()
                self.wfile.write(than)
                self.wfile.flush()
                stub.da_tra_loi.append({"ma": ma, "than": than, "headers": {},
                                        "than_khai_bao": len(than) + 200})
            except OSError as e:
                stub.loi_may_chu.append(f"{type(e).__name__}: {e}")
            time.sleep(stub.do_tre)
            self.close_connection = True
            return
        ma, than, headers_them = stub._than_theo_che_do(yeu_cau, che_do)
        stub._tra_loi(self, ma, than, headers_them)

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except (ConnectionResetError, BrokenPipeError) as e:
            self.server.stub.loi_may_chu.append(f"{type(e).__name__}: {e}")
            self.close_connection = True
