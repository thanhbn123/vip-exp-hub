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
import os
import socket
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

# Đường dẫn mặc định = ĐÚNG đường tạo đơn đã đọc được trong tài liệu (`adapter_jt.DUONG_TAO_DON`).
DUONG_TAO_DON = "/webopenplatformapi/api/order/addOrder"

# ---- ĐƯỜNG ĐIỀU KHIỂN (G18/AG-02) — KHÔNG phải đường của J&T --------------------------------
#
# Vì sao cần: đo ĐA TIẾN TRÌNH thì stub phải sống trong MỘT TIẾN TRÌNH RIÊNG, còn số đo của nó
# (`so_ket_noi`, `so_yeu_cau`, `cao_nhat_dang_xu_ly`) phải đọc được TỪ NGOÀI tiến trình đó. Không
# có đường này thì bộ đo chỉ còn cách suy từ phía client — mà "client tự khai" không phải bằng
# chứng về cái stub đã nhận (§12.1 luật 3).
#
# Đường này chỉ tồn tại trên loopback (stub chỉ bind `127.0.0.1`), trả về SỐ ĐO chứ không trả dữ
# liệu người dùng, và KHÔNG được tính vào `yeu_cau`/`da_tra_loi`: nếu tính thì chính lượt đọc số
# đo lại làm bẩn con số đang đọc (`so_ket_noi` thì vẫn tăng — bộ đo trừ hai mốc, xem `thong_ke`).
DUONG_THONG_KE = "/__stub/thong-ke"

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

# ---- Ba chế độ của G17/AG-02 (ĐO ĐA LUỒNG · ĐO HẠN ĐỌC) ----------------------------------------
#
# `VONG_LAP`: 200 với thân DỰNG TỪ CHÍNH YÊU CẦU. Nhờ nó, ca đa luồng phát hiện được LẪN DỮ LIỆU:
#   nếu hai lượt gửi dùng chung một socket/bộ đệm, luồng này sẽ nhận thân của luồng kia — và ca đo
#   so được `bizContent` nhận về với `bizContent` đã gửi. Một stub trả lời giống nhau cho mọi lượt
#   KHÔNG đo được điều đó.
# `DOI_DAU_LAP`: như `DOI_DAU` nhưng echo LẶP `so_lan_echo` lần và echo thêm dòng yêu cầu (đường dẫn
#   + query). Dùng để đo ba thứ: (c) bí mật bị DỚP LẶP trong thân, bí mật nằm ở QUERY của URL, và
#   dạng JSON `ensure_ascii=True` (`json_ascii=True`).
# `NHO_GIO`: gửi thân TỪNG BYTE một, cách nhau `do_tre`. Dùng để đo "hạn ĐỌC là hạn của TỪNG lần
#   đọc, KHÔNG phải hạn tổng": chênh lệch nhỏ hơn `timeout` ⇒ client KHÔNG hết giờ dù tổng thời gian
#   lớn hơn `timeout`; chênh lệch lớn hơn `timeout` ⇒ hết giờ NGAY GIỮA thân của một HTTP 200.
VONG_LAP = "vong_lap"
DOI_DAU_LAP = "doi_dau_lap"
NHO_GIO = "nho_gio"

CHE_DO = (THANH_CONG, HANG_TU_CHOI, HTTP_500, HTTP_400, HTTP_401, HTTP_403, HTTP_404, HTTP_408,
          HTTP_429, HTTP_302, DOI_DAU, CHAM, CAT_KET_NOI, THAN_THIEU, VONG_LAP, DOI_DAU_LAP, NHO_GIO)

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
    # Hàng đợi `accept` mặc định của `socketserver` là 5. Với ca đo ĐA LUỒNG (hàng chục lượt nối
    # cùng lúc) hàng đợi 5 làm nhân hệ điều hành BỎ QUA SYN ⇒ client phải gửi lại ⇒ lượt nối chậm
    # bất thường, và một bộ thử vội vàng sẽ đọc đó thành "mã sản phẩm bị treo" (đúng khuôn HỎNG GIẢ
    # N-05). Nâng hàng đợi để phép đo chỉ còn đo MÃ SẢN PHẨM.
    request_queue_size = 128


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
    VONG_LAP = VONG_LAP
    DOI_DAU_LAP = DOI_DAU_LAP
    NHO_GIO = NHO_GIO

    def __init__(self, che_do=THANH_CONG, *, do_tre=1.5, ma_loi="145005005",
                 thong_diep="获取运单号失败 — hãng không cấp được mã vận đơn",
                 ma_van_don="VH000000001VN", duong_mac_dinh=DUONG_TAO_DON,
                 host="127.0.0.1", them_header=None, so_lan_echo=3, json_ascii=False,
                 so_byte_nho=6):
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
        # Tham số cho ba chế độ G17 (xem chú thích `VONG_LAP`/`DOI_DAU_LAP`/`NHO_GIO`).
        self.so_lan_echo = int(so_lan_echo)
        self.json_ascii = bool(json_ascii)
        self.so_byte_nho = int(so_byte_nho)
        # ---- SỐ ĐO ĐA LUỒNG (AG-02) ------------------------------------------------------------
        # `so_ket_noi`  : số kết nối TCP đã được CHẤP NHẬN (không phải số yêu cầu). Chênh lệch giữa
        #                 hai con số này chính là câu trả lời cho "lớp HTTP có dùng lại kết nối /
        #                 có pool không".
        # `cao_nhat_dang_xu_ly`: số yêu cầu CAO NHẤT đang được xử lý cùng lúc. Bằng 1 nghĩa là mọi
        #                 lượt gọi bị TUẦN TỰ HOÁ (dù người gọi có bao nhiêu luồng).
        self.so_ket_noi = 0
        self.dang_xu_ly = 0
        self.cao_nhat_dang_xu_ly = 0
        # Số lượt ĐỌC SỐ ĐO qua `DUONG_THONG_KE`. Trừ khỏi `so_ket_noi` khi báo cáo: lượt đọc số
        # đo cũng là một kết nối TCP, mà nó không phải lượt gọi của lớp HTTP đang được đo.
        self.so_dieu_khien = 0
        self._khoa_dem = threading.Lock()
        # Header GẮN THÊM vào MỌI phản hồi (ví dụ `Retry-After`) — để đo đường 408/429 mà không
        # phải đẻ thêm một chế độ cho từng giá trị header.
        self.them_header = dict(them_header or {})
        self._may_chu = MayChuStub((host, 0), _BoXuLy)
        self._may_chu.stub = self
        self.cong = self._may_chu.server_address[1]
        self.host = host
        _goc_get_request = self._may_chu.get_request

        def _get_request():
            kq = _goc_get_request()
            with self._khoa_dem:
                self.so_ket_noi += 1
            return kq

        self._may_chu.get_request = _get_request
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
                   them_header=None, so_lan_echo=None, json_ascii=None, so_byte_nho=None):
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
        if so_lan_echo is not None:
            self.so_lan_echo = int(so_lan_echo)
        if json_ascii is not None:
            self.json_ascii = bool(json_ascii)
        if so_byte_nho is not None:
            self.so_byte_nho = int(so_byte_nho)

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

    def thong_ke(self) -> dict:
        """SỐ ĐO của stub, đọc được TỪ TIẾN TRÌNH KHÁC qua `DUONG_THONG_KE`.

        `so_ket_noi` là số kết nối TCP của KHÁCH đã CHẤP NHẬN (đã trừ các lượt đọc số đo — chính
        chúng cũng là kết nối TCP, xem `so_dieu_khien`); `so_yeu_cau` là số yêu cầu J&T đã nhận.
        Hai con số khác nhau là câu trả lời cho "lớp HTTP có dùng lại kết nối không" — và khi bộ
        đo chạy NHIỀU TIẾN TRÌNH thì đây là bằng chứng DUY NHẤT không do client tự khai.
        """
        with self._khoa_dem:
            return {"pid": os.getpid(), "cong": self.cong, "che_do": self.che_do,
                    "so_ket_noi": self.so_ket_noi - self.so_dieu_khien,
                    "so_ket_noi_tho": self.so_ket_noi, "so_dieu_khien": self.so_dieu_khien,
                    "so_yeu_cau": len(self.yeu_cau),
                    "cao_nhat_dang_xu_ly": self.cao_nhat_dang_xu_ly}

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
        if che_do == VONG_LAP:
            # Thân DỰNG TỪ CHÍNH YÊU CẦU: mỗi luồng nhận lại ĐÚNG dấu vết của mình ⇒ ca đa luồng
            # phát hiện được lẫn dữ liệu (nếu hai lượt gửi chung một socket/bộ đệm, luồng này sẽ
            # nhận `bizContent` của luồng kia).
            return 200, json.dumps(
                {"code": "1", "msg": "成功", "data": {
                    "bizContent": yeu_cau.form_value("bizContent") or "",
                    "apiAccount": yeu_cau.header("apiaccount") or "",
                    "duong_dan": yeu_cau.duong_dan}},
                ensure_ascii=False).encode("utf-8"), {}
        if che_do == DOI_DAU_LAP:
            # Echo LẶP `so_lan_echo` lần, và echo CẢ dòng yêu cầu (đường dẫn + query). Ba đường rò
            # được đo bằng chế độ này: bí mật DỚP LẶP trong thân, bí mật nằm ở QUERY của URL, và
            # dạng JSON `ensure_ascii=True` (`json_ascii=True`) của bí mật phi-ASCII.
            khoi = {
                "headers": {k: v for k, v in yeu_cau.headers_goc},
                "than": yeu_cau.than_tho.decode("utf-8", "replace"),
                "form": {k: v[0] for k, v in yeu_cau.form().items()},
                "duong_dan": yeu_cau.duong_dan,
            }
            than_echo = {
                "code": "145003030", "msg": "请求头中的签名验证失败 — chữ ký trong header sai",
                "data": {"lap": [khoi] * max(1, self.so_lan_echo)}}
            return 401, json.dumps(than_echo, ensure_ascii=self.json_ascii).encode("utf-8"), {
                "X-Digest-Echo": yeu_cau.header("digest") or ""}
        if che_do == NHO_GIO:
            # Thân trả lời bình thường; VIỆC GỬI NHỎ GIỌT nằm ở `_nhan` (cần ghi từng byte).
            return 200, json.dumps(
                {"code": "1", "msg": "成功", "data": {"billCode": self.ma_van_don}},
                ensure_ascii=False).encode("utf-8"), {}
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
        # ĐIỀU KHIỂN đứng TRƯỚC `_nhan`: lượt đọc số đo không được cộng vào `yeu_cau` (nếu cộng
        # thì mỗi lần đọc số đo lại đổi chính con số vừa đọc) và không trả 405 như một GET lạ.
        if self.path.split("?", 1)[0] == DUONG_THONG_KE:
            self._tra_thong_ke()
            return
        self._nhan("GET")

    def _tra_thong_ke(self):
        """Trả số đo của stub dưới dạng JSON. Chỉ loopback (stub chỉ bind `127.0.0.1`)."""
        # Đếm TRƯỚC khi dựng số đo: chính lượt đọc này là một kết nối TCP vừa được chấp nhận,
        # nên nó phải bị trừ ra — không thì mỗi lần đọc số đo lại làm con số vừa đọc nhảy thêm 1
        # và bộ đo phải bù bằng số học đoán mò.
        with self.server.stub._khoa_dem:
            self.server.stub.so_dieu_khien += 1
        than = json.dumps(self.server.stub.thong_ke(), ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(than)))
        self.end_headers()
        self.wfile.write(than)
        self.wfile.flush()

    def do_POST(self):
        self._nhan("POST")

    def do_PUT(self):
        self._nhan("PUT")

    def _nhan(self, phuong_thuc):
        """ĐẾM SỐ YÊU CẦU ĐANG XỬ LÝ CÙNG LÚC, rồi mới xử lý.

        `cao_nhat_dang_xu_ly` là số đo trả lời câu "lớp HTTP có thật sự chạy song song không": bằng 1
        nghĩa là mọi lượt gọi bị TUẦN TỰ HOÁ dù người gọi mở bao nhiêu luồng. Bộ đếm nằm ở đây (chứ
        không ở `get_request`) vì một kết nối HTTP/1.1 có thể chở nhiều yêu cầu.
        """
        stub = self.server.stub
        with stub._khoa_dem:
            stub.dang_xu_ly += 1
            if stub.dang_xu_ly > stub.cao_nhat_dang_xu_ly:
                stub.cao_nhat_dang_xu_ly = stub.dang_xu_ly
        try:
            self._xu_ly(phuong_thuc)
        finally:
            with stub._khoa_dem:
                stub.dang_xu_ly -= 1

    def _xu_ly(self, phuong_thuc):
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
        if che_do == NHO_GIO:
            # Gửi thân TỪNG BYTE một, cách nhau `do_tre`: đo "hạn ĐỌC là hạn của TỪNG lần đọc".
            ma, than, headers_them = stub._than_theo_che_do(yeu_cau, NHO_GIO)
            self._nho_gio(stub, ma, than, headers_them)
            self.close_connection = True
            return
        if che_do in (VONG_LAP, DOI_DAU_LAP) and stub.do_tre:
            # Độ trễ CÓ CHỦ Ý để nhiều lượt gọi chồng lên nhau thật ⇒ số đo "đang xử lý cùng lúc"
            # mới có nghĩa (stub trả lời trong vài trăm micro-giây thì mọi lượt đều tách rời).
            time.sleep(stub.do_tre)
        ma, than, headers_them = stub._than_theo_che_do(yeu_cau, che_do)
        stub._tra_loi(self, ma, than, headers_them)

    def _nho_gio(self, stub, ma, than, headers_them):
        """Trả lời `ma` với `Content-Length` ĐÚNG, nhưng gửi thân nhỏ giọt rồi phần còn lại.

        Vì sao cần chế độ này: `timeout` của `http.client` là hạn của MỖI lần đọc trên socket, không
        phải hạn tổng của lượt gọi. Máy chủ gửi một byte mỗi `do_tre` giây với `do_tre < timeout` sẽ
        giữ được lượt gọi lâu hơn `timeout` mà client KHÔNG hết giờ. Đó là giới hạn đã biết của lớp
        này (xem `docs/G17_TRANSPORT.md` §4.4), và nó chỉ đo được bằng một máy chủ nhỏ giọt thật.
        """
        try:
            self.send_response(ma)
            for ten, gt in {**stub.them_header, **(headers_them or {})}.items():
                self.send_header(ten, gt)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(than)))
            self.end_headers()
            so = max(1, min(int(stub.so_byte_nho), len(than)))
            for i in range(so):
                self.wfile.write(than[i:i + 1])
                self.wfile.flush()
                time.sleep(stub.do_tre)          # CHỦ Ý: mỗi byte cách nhau ÍT HƠN `timeout` của ca đo
            if len(than) > so:
                self.wfile.write(than[so:])
                self.wfile.flush()
            stub.da_tra_loi.append({"ma": ma, "than": than, "headers": dict(headers_them or {})})
        except OSError as e:
            stub.loi_may_chu.append(f"{type(e).__name__}: {e}")

    def handle_one_request(self):
        try:
            BaseHTTPRequestHandler.handle_one_request(self)
        except (ConnectionResetError, BrokenPipeError) as e:
            self.server.stub.loi_may_chu.append(f"{type(e).__name__}: {e}")
            self.close_connection = True


class HoDenKetNoi:
    """Hố đen TCP trên LOOPBACK: `listen` nhưng KHÔNG BAO GIỜ `accept` ⇒ không lượt nối nào hoàn tất.

    Vì sao cần một fixture riêng cho hạn NỐI: đo hạn nối cần một lượt nối TREO THẬT ở tầng TCP,
    không phải một `sleep` giả tiêm vào mã sản phẩm. Luật của dự án chỉ cho loopback, mà mọi cổng
    loopback bình thường đều trả lời trong vài chục micro-giây. Cách duy nhất để có một lượt nối
    treo trên loopback là LÀM ĐẦY hàng đợi `accept`: từ đó nhân hệ điều hành IM LẶNG BỎ QUA SYN, và
    `connect()` của client treo cho tới hạn của chính nó. (Đo trên macOS 15/10/2026: `listen(1)` cho
    đúng MỘT lượt nối hoàn tất, mọi lượt sau treo.)

    Hố đen KHÔNG BAO GIỜ nhận một byte yêu cầu nào — nó chưa từng `accept`, nên chưa từng có kết nối
    hoàn tất. Nhờ vậy nó cũng là đối chứng cho câu "hết giờ NỐI nghĩa là CHƯA GỬI ĐI".

    TỰ KIỂM BẮT BUỘC: `__init__` chỉ trả về khi một lượt nối thăm dò ĐÃ hết giờ. Nếu hàng đợi chưa
    đầy (hoặc hệ điều hành xử sự khác), nó NÉM NGAY — thà hỏng to còn hơn để một "hố đen" không thật
    làm ca đo hạn nối XANH một cách vô nghĩa (đúng khuôn HỎNG GIẢ N-05).
    """

    def __init__(self, host="127.0.0.1", het_gio_tham_do=0.25, toi_da_lan_bam=64):
        self.host = host
        self.so_bam = 0                     # số lượt nối ĐÃ hoàn tất trước khi hàng đợi đầy
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._s.bind((host, 0))
        self._s.listen(1)                   # hàng đợi NHỎ: đầy nhanh, và đầy được xác minh
        self.cong = self._s.getsockname()[1]
        self._lam_day(het_gio_tham_do, toi_da_lan_bam)

    def _lam_day(self, het_gio, toi_da):
        """Nối cho tới khi hàng đợi đầy, rồi TỰ KIỂM rằng lượt nối kế tiếp TREO."""
        for _ in range(toi_da):
            c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c.settimeout(het_gio)
            try:
                c.connect((self.host, self.cong))
            except OSError:
                # Đã đầy: lượt thăm dò này chính là bằng chứng.
                c.close()
                self.so_bam_hoan_tat = self.so_bam
                return
            self.so_bam += 1
            c.close()
        self._s.close()
        raise RuntimeError(
            f"hố đen KHÔNG đầy sau {toi_da} lượt nối — không đo được hạn NỐI bằng fixture này")

    # ---- Địa chỉ ----
    @property
    def goc(self):
        return f"http://{self.host}:{self.cong}"

    def url_cho(self, duong="/webopenplatformapi/api/order/addOrder"):
        return self.goc + duong

    @property
    def url(self):
        return self.url_cho()

    # ---- Vòng đời ----
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.dung()
        return False

    def dung(self):
        try:
            self._s.close()
        except OSError:
            pass


# ===============================================================================================
# CHẠY STUB NHƯ MỘT TIẾN TRÌNH RIÊNG (G18/AG-02) — `python3 app/thu/stub_jt.py --ghi-cong <tệp>`
# ===============================================================================================
#
# Vì sao phải có: đo ĐA TIẾN TRÌNH bằng stub nằm TRONG tiến trình bộ thử là vô nghĩa — mọi
# "tiến trình khác" sẽ nói chuyện với stub của chính tiến trình bộ thử, và số đo `so_ket_noi`
# chỉ là số đo trong MỘT tiến trình. Stub phải sống ở tiến trình riêng thì mới là phép đo
# liên tiến trình thật.
#
# CỔNG 0 vẫn là mặc định và là LUẬT của bộ thử (không cổng cố định): tiến trình con bind
# `127.0.0.1:0`, hệ cấp cổng, rồi GHI cổng thật ra tệp `--ghi-cong` để tiến trình cha đọc.
# Không có đường nào để stub này mở ra ngoài Internet: `host` mặc định `127.0.0.1` và bị chặn
# nếu khác (xem dưới).
def chay_nhu_tien_trinh(argv=None) -> int:
    import argparse
    import signal
    import sys

    ap = argparse.ArgumentParser(description="Stub J&T cục bộ chạy như một tiến trình riêng")
    ap.add_argument("--che-do", default=THANH_CONG, choices=list(CHE_DO))
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--do-tre", type=float, default=0.0)
    ap.add_argument("--ghi-cong", required=True,
                    help="tệp JSON nhận {'cong': <cổng thật>, 'pid': <pid>} sau khi bind xong")
    a = ap.parse_args(argv)
    if a.host not in ("127.0.0.1", "localhost"):
        # Chốt cứng: stub này KHÔNG được bind ra địa chỉ khác. Bind 0.0.0.0 là mở một máy chủ
        # giả ra mạng — bất kể ai gọi nó, nó cũng là một cửa không ai canh.
        sys.stderr.write("TỪ CHỐI: stub chỉ được bind loopback, không bind %r\n" % a.host)
        return 2
    stub = StubJT(a.che_do, host=a.host, do_tre=a.do_tre)
    with open(a.ghi_cong, "w") as f:
        json.dump({"cong": stub.cong, "pid": os.getpid()}, f)
        f.flush()
        os.fsync(f.fileno())

    def _dung(_signum, _khung):
        # Chỉ RA HIỆU thoát; việc tắt máy chủ nằm ở `finally` — gọi `dung()` hai lần (một lần
        # trong hàm bắt tín hiệu, một lần ở `finally`) là tự tạo một đường tắt máy chủ hai lượt
        # mà không ai cần.
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _dung)
    signal.signal(signal.SIGINT, _dung)
    try:
        while True:
            time.sleep(0.2)
    finally:
        stub.dung()
    return 0


if __name__ == "__main__":
    raise SystemExit(chay_nhu_tien_trinh())
