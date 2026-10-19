# B1 — LỚP HTTP CHO BEST EXPRESS (VietnamV3).
#
# VÌ SAO CÓ TỆP NÀY (và vì sao KHÔNG dùng lại `http_jt.py`):
#   `http_jt.py` là lớp HTTP của J&T — nó đóng cứng danh sách trắng hai host J&T, gửi
#   `application/x-www-form-urlencoded`, và có nguyên một tầng che bí mật gắn với hình dạng
#   `bizContent` của J&T. BEST cần JSON, cần hai host KHÁC, và cần một chốt SSRF cho URL PDF
#   do hãng trả về. Dùng lại lớp J&T sẽ phải sửa `http_jt.py` — tệp thuộc làn khác và đã nghiệm
#   thu. Nên tệp này là lớp RIÊNG, cùng hợp đồng tinh thần §36: gửi MỘT lượt, KHÔNG tự thử lại,
#   KHÔNG tự ngủ, ba kết cục tách rời.
#
# SỰ THẬT NỀN TẢNG, GHI NGAY ĐẦU TỆP:
#   Hai base URL của BEST trong đề bài là **HTTP**, KHÔNG mã hoá:
#     production http://sgp-seaedi.800best.com/VietNamV3/v3/api/process/sears
#     test       http://sgp-seaedi-test.800best.com/VietNamV3/v3/api/process/sears
#   Gửi credential (mật khẩu, token) hoặc dữ liệu đơn thật qua HTTP là gửi bản rõ qua mạng.
#   Vì vậy lớp này **TỪ CHỐI** scheme `http` cho host hãng, trừ khi người gọi bật cờ
#   `cho_phep_http_khong_ma_hoa=True` MỘT CÁCH TƯỜNG MINH. Mặc định là CHẶN. Cờ đó chỉ để mở
#   cho một môi trường thử ĐÃ ĐƯỢC DUYỆT, không phải để tiện tay.
#
# BA KẾT CỤC — KHÔNG GỘP (hợp đồng `docs/SHARED_CONTRACTS.md` §4):
#   · `TraLoiHTTP` trả về            → có phản hồi HTTP, nơi gọi tự đọc thân;
#   · `transport.LoiVinhVien`        → biết chắc KHÔNG gửi được / hãng từ chối (4xx, URL sai,
#                                      host lạ, chứng chỉ TLS hỏng);
#   · `transport.LoiTamThoi`         → KHÔNG BIẾT kết quả (hết giờ, mạng đứt, 5xx, 408, 429).
#   Kết cục thứ ba không bao giờ được coi là thành công.
#
# LUẬT CỨNG:
#   1. KHÔNG tự thử lại, KHÔNG ngủ. Việc thử lại thuộc `transport.goi()`.
#   2. Danh sách TRẮNG host, so KHỚP CHÍNH XÁC — không so chuỗi con. `http://sgp-seaedi.800best.com.evil`
#      không được lọt.
#   3. Tải PDF waybill: chỉ tải từ hostname ĐÃ ĐƯỢC PHÉP, chặn localhost/private IP/metadata.
#      Đây là chống SSRF, không phải kiểm tra hình thức.
#   4. KHÔNG hạ TLS: không `verify=False`, không `_create_unverified_context`, không tự bỏ
#      kiểm tra chứng chỉ.
#   5. Thông điệp lỗi KHÔNG chép URL/query/thân yêu cầu — URL có thể chở token.
import http.client
import ipaddress
import json
import math
import socket
import ssl
from urllib.parse import urlsplit

import transport

MOCK = "mock"
SANDBOX = "sandbox"
PRODUCTION = "production"

# ── Host của BEST (ĐÃ XÁC NHẬN trong đề bài) ──────────────────────────────────────────────────
HOST_PRODUCTION = "sgp-seaedi.800best.com"
HOST_SANDBOX = "sgp-seaedi-test.800best.com"
HOST_HANG = frozenset({HOST_PRODUCTION, HOST_SANDBOX})

# Hostname của endpoint test Order/Query mà đề bài nói tới nhưng CHƯA XÁC MINH. KHÔNG đưa vào
# danh sách trắng: một hostname chưa xác minh không được trở thành đường gửi chỉ vì nó được nhắc
# trong tài liệu. Ghi ra đây để người sau thấy nó đã được biết tới và cố ý KHÔNG dùng.
HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH = "sea-edi-hxtest.800best.com"

# Loopback chỉ để bộ thử dựng stub cục bộ (cổng do OS cấp). Không phải đường LIVE.
HOST_CUC_BO = frozenset({"127.0.0.1", "localhost", "::1"})

# Các host nội bộ/cloud metadata phải bị chặn dứt khoát khi tải URL do hãng trả về. Chúng đã
# nằm ngoài danh sách trắng, nhưng nêu tên riêng để thông điệp lỗi đọc được đúng lý do.
HOST_METADATA = frozenset({
    "169.254.169.254", "metadata.google.internal", "metadata.goog",
    "100.100.100.200",  # metadata Alibaba Cloud
})

# ── Base URL (ĐÃ XÁC NHẬN trong đề bài; CẢ HAI LÀ HTTP, CHƯA MÃ HOÁ) ─────────────────────────
BASE_URL = {
    PRODUCTION: f"http://{HOST_PRODUCTION}/VietNamV3/v3/api/process/sears",
    SANDBOX: f"http://{HOST_SANDBOX}/VietNamV3/v3/api/process/sears",
}
CO_HTTP_CHUA_MA_HOA = True          # sự thật của đề bài, không phải lựa chọn của lớp này
CONG_HTTPS = 443
CONG_HTTP = 80

# Giới hạn kỹ thuật của lớp HTTP. Không phải hạn mức nghiệp vụ của hãng.
HET_GIO_KET_NOI_TOI_DA = 5.0
KICH_THUOC_PHAN_HOI_TOI_DA = 5 * 1024 * 1024       # 5 MiB
KICH_THUOC_YEU_CAU_TOI_DA = 2 * 1024 * 1024        # 2 MiB


class TraLoiHTTP:
    """Kết quả MỘT lượt gửi. `than` là bytes thô; lớp này KHÔNG tự đoán JSON."""

    __slots__ = ("ma_http", "than", "headers")

    def __init__(self, ma_http, than, headers):
        self.ma_http = int(ma_http)
        self.than = bytes(than)
        self.headers = dict(headers or {})

    def json(self):
        """Đọc thân thành JSON. Ném `ValueError` nếu không phải JSON — nơi gọi phải xử lý."""
        return json.loads(self.than.decode("utf-8"))

    def __repr__(self):
        # KHÔNG in thân: thân có thể chứa token hoặc dữ liệu khách.
        return f"TraLoiHTTP(ma_http={self.ma_http}, so_byte={len(self.than)})"


# =================================================================================================
# 0. NGOẠI LỆ — cùng hình dạng transport.py, kèm dấu vết đủ để adapter phân loại
# =================================================================================================
def _loi_vinh_vien(ma, thong_diep, ket_cuc="khong-gui-di", **them):
    e = transport.LoiVinhVien(thong_diep)
    e.ma = ma
    e.ket_cuc = ket_cuc
    e.timeout = False
    e.ma_http = int(them.pop("ma_http", 0) or 0)
    for k, v in them.items():
        setattr(e, k, v)
    return e


def _loi_tam_thoi(ma, thong_diep, ket_cuc="khong-biet", cho_giay=None, **them):
    e = transport.LoiTamThoi(thong_diep, cho_giay=cho_giay)
    e.ma = ma
    e.ket_cuc = ket_cuc
    e.timeout = True
    e.ma_http = int(them.pop("ma_http", 0) or 0)
    for k, v in them.items():
        setattr(e, k, v)
    return e


# =================================================================================================
# 1. KIỂM URL — chạy TRƯỚC mọi thao tác mạng
# =================================================================================================
def la_host_cuc_bo(host) -> bool:
    return (host or "").strip().lower().rstrip(".") in HOST_CUC_BO


def host_duoc_phep(host) -> bool:
    """Chỉ host BEST đã xác nhận hoặc loopback. So KHỚP CHÍNH XÁC."""
    h = (host or "").strip().lower().rstrip(".")
    return h in HOST_HANG or h in HOST_CUC_BO


def la_ip_noi_bo(host) -> bool:
    """True nếu `host` là IP và KHÔNG phải IP công khai (private/loopback/link-local/...).

    `localhost` không phải IP literal nên hàm này trả False; nó được chặn bởi danh sách trắng
    và bởi `la_host_cuc_bo`. Dùng hàm này cho IP literal để thông điệp lỗi nêu đúng lý do.
    """
    try:
        ip = ipaddress.ip_address(str(host).strip())
    except ValueError:
        return False
    return not ip.is_global


def _kiem_ky_tu(url):
    if not isinstance(url, str) or not url.strip():
        raise _loi_vinh_vien("url-sai", "URL phải là chuỗi khác rỗng")
    for i, c in enumerate(url):
        if ord(c) < 0x21 or ord(c) == 0x7F:
            # KHÔNG nêu ký tự: URL có thể chở token ở query.
            raise _loi_vinh_vien("url-sai", f"URL chứa ký tự không hợp lệ tại vị trí {i}")


def tach_url(url, *, cho_phep_http_khong_ma_hoa=False, cho_phep_loopback=False):
    """→ (scheme, host, cổng, đường_dẫn). Ném `LoiVinhVien` nếu URL không được phép.

    Chạy TRƯỚC mọi thao tác mạng. Ba lớp chặn:
      · host phải nằm trong danh sách trắng (host BEST hoặc loopback khi được phép);
      · host BEST dùng `http` ⇒ TỪ CHỐI, trừ khi bật cờ tường minh;
      · URL chứa thông tin đăng nhập (`user@host`), fragment, scheme lạ ⇒ TỪ CHỐI.
    """
    _kiem_ky_tu(url)
    try:
        phan = urlsplit(url)
    except ValueError:
        # Không nêu URL: một URL hỏng vẫn có thể chở token.
        raise _loi_vinh_vien("url-sai", "URL không phân tích được (cú pháp sai)") from None
    if phan.scheme not in ("http", "https"):
        raise _loi_vinh_vien("url-sai", f"scheme {phan.scheme!r} không dùng được (chỉ http/https)")
    if phan.fragment:
        raise _loi_vinh_vien("url-sai", "URL chứa dấu # — dán sai, không gửi đi")
    if "@" in phan.netloc:
        raise _loi_vinh_vien(
            "url-sai", "URL chứa thông tin đăng nhập (user@host) — credentials KHÔNG đi qua URL")
    host = (phan.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise _loi_vinh_vien("url-sai", "URL không có tên máy chủ")
    try:
        cong = phan.port
    except ValueError:
        raise _loi_vinh_vien("url-sai", f"cổng trong URL không hợp lệ (host {host!r})") from None
    if cong is not None and not (1 <= cong <= 65535):
        raise _loi_vinh_vien(
            "url-sai", f"cổng {cong} ngoài khoảng 1..65535 — TỪ CHỐI trước khi mở socket",
            host=host)

    if host in HOST_HANG:
        if phan.scheme == "http":
            if not cho_phep_http_khong_ma_hoa:
                raise _loi_vinh_vien(
                    "http-khong-ma-hoa",
                    f"TỪ CHỐI gửi tới host hãng {host!r} bằng HTTP CHƯA MÃ HOÁ. "
                    "Credential và dữ liệu đơn thật không được đi qua kênh bản rõ. "
                    "Bật cờ cho_phep_http_khong_ma_hoa CHỈ khi môi trường đã được duyệt.",
                    ket_cuc="khong-gui-di", host=host)
            if cong not in (None, CONG_HTTP):
                raise _loi_vinh_vien(
                    "url-sai", f"host hãng {host!r} dùng http thì chỉ nhận cổng {CONG_HTTP}, "
                    f"nhận {cong}", host=host)
        else:  # https
            if cong not in (None, CONG_HTTPS):
                raise _loi_vinh_vien(
                    "url-sai", f"host hãng {host!r} chỉ nhận cổng {CONG_HTTPS}, nhận {cong}",
                    host=host)
    elif host in HOST_CUC_BO:
        if not cho_phep_loopback:
            raise _loi_vinh_vien(
                "host-cuc-bo",
                f"TỪ CHỐI máy chủ cục bộ {host!r}: chỉ bộ thử MOCK được phép dựng stub trên "
                "loopback. Đường LIVE không đi vào loopback.",
                host=host)
    else:
        if host in HOST_METADATA:
            raise _loi_vinh_vien(
                "ssrf-metadata",
                f"TỪ CHỐI {host!r}: đây là endpoint metadata của hạ tầng — không bao giờ tải.",
                host=host)
        if la_ip_noi_bo(host):
            raise _loi_vinh_vien(
                "ssrf-ip-noi-bo",
                f"TỪ CHỐI địa chỉ nội bộ {host!r}: URL do bên ngoài trả về không được trỏ vào "
                "mạng nội bộ (SSRF).",
                host=host)
        # KHÔNG in tên host lạ: tên miền cũng có thể bị nhét token vào nhãn con. Người trực
        # không cần tên host để hành động — mã lỗi `host-bi-tu-choi` đã đủ, và danh sách trắng
        # in kèm ở đây để biết đường hợp lệ.
        raise _loi_vinh_vien(
            "host-bi-tu-choi",
            "TỪ CHỐI máy chủ không nằm trong danh sách trắng "
            f"({', '.join(sorted(HOST_HANG))}). Lượt gọi này KHÔNG được gửi đi.",
            host=host)

    duong_dan = phan.path or "/"
    if not duong_dan.startswith("/"):
        raise _loi_vinh_vien("url-sai", "đường dẫn không bắt đầu bằng '/' — dán sai")
    if phan.query:
        duong_dan = duong_dan + "?" + phan.query
    return phan.scheme, host, cong, duong_dan


def _kiem_thoi_gian(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise _loi_vinh_vien("tham-so-sai", f"timeout phải là số giây, nhận {type(timeout).__name__}")
    t = float(timeout)
    if not math.isfinite(t) or t <= 0:
        raise _loi_vinh_vien("tham-so-sai", f"timeout phải là số hữu hạn > 0, nhận {t!r}")
    return t


def _kiem_headers(headers):
    if headers is None:
        return {}
    if not isinstance(headers, dict):
        raise _loi_vinh_vien("tham-so-sai", "headers phải là dict")
    ra = {}
    for k, v in headers.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise _loi_vinh_vien("tham-so-sai", "tên/giá trị header phải là chuỗi")
        if not k or ":" in k or any(ord(c) < 0x21 or ord(c) == 0x7F for c in k):
            raise _loi_vinh_vien("header-sai", "tên header không hợp lệ")
        if any(ord(c) in (0x0A, 0x0D) or ord(c) < 0x20 for c in v):
            raise _loi_vinh_vien("header-sai", f"giá trị header {k!r} chứa ký tự điều khiển")
        if k.lower() in ("host", "content-length", "transfer-encoding"):
            # Ta tự đặt ba header này; cho người gọi ghi đè là mở đường smuggling.
            raise _loi_vinh_vien("header-sai", f"header {k!r} do lớp HTTP tự đặt, không nhận từ ngoài")
        ra[k] = v
    return ra


def _json_bytes(payload):
    if not isinstance(payload, dict):
        raise _loi_vinh_vien("tham-so-sai", "payload phải là dict JSON")
    try:
        than = json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as e:
        raise _loi_vinh_vien("tham-so-sai", f"payload không mã hoá được JSON ({type(e).__name__})") from None
    if len(than) > KICH_THUOC_YEU_CAU_TOI_DA:
        raise _loi_vinh_vien(
            "yeu-cau-qua-lon",
            f"thân yêu cầu {len(than)} byte vượt trần {KICH_THUOC_YEU_CAU_TOI_DA} byte")
    return than


def _doc_retry_after(headers):
    """`Retry-After` (giây) đã kẹp trần. Không ngủ — chỉ trả gợi ý cho `transport.goi()`."""
    for k, v in (headers or {}).items():
        if str(k).lower() != "retry-after":
            continue
        try:
            giay = float(str(v).strip())
        except (TypeError, ValueError):
            return None
        if not math.isfinite(giay) or giay < 0:
            return None
        return min(giay, transport.CHO_TOI_DA)
    return None


def _headers_thanh_dict(headers_tra_loi):
    ra = {}
    for k, v in headers_tra_loi or []:
        # Header trùng tên: giữ giá trị đầu, không nối — nối là tự chế một giá trị mới.
        ra.setdefault(str(k).lower(), str(v))
    return ra


# =================================================================================================
# 2. GỬI MỘT LƯỢT — không thử lại, không ngủ
# =================================================================================================
def _mo_ket_noi(scheme, host, cong, timeout):
    if scheme == "https":
        # `create_default_context()` BẬT kiểm tra chứng chỉ + hostname. KHÔNG hạ TLS.
        return http.client.HTTPSConnection(
            host, cong or CONG_HTTPS, timeout=timeout, context=ssl.create_default_context())
    return http.client.HTTPConnection(host, cong or CONG_HTTP, timeout=timeout)


def _dong(ket_noi):
    try:
        if ket_noi is not None:
            ket_noi.close()
    except Exception:
        pass


def _gui(method, url, headers, than, *, timeout,
         cho_phep_http_khong_ma_hoa=False, cho_phep_loopback=False, kiem_ip_cong_khai=False):
    """Gửi ĐÚNG MỘT lượt. Trả `TraLoiHTTP` cho 2xx; ném lỗi transport cho mọi trường hợp khác."""
    scheme, host, cong, dich = tach_url(
        url, cho_phep_http_khong_ma_hoa=cho_phep_http_khong_ma_hoa,
        cho_phep_loopback=cho_phep_loopback)
    het_gio = _kiem_thoi_gian(timeout)
    headers_gui = _kiem_headers(headers)
    if host in HOST_HANG and kiem_ip_cong_khai:
        _kiem_ip_cong_khai(host)
    het_gio_ket_noi = min(het_gio, HET_GIO_KET_NOI_TOI_DA)

    ket_noi = None
    try:
        ket_noi = _mo_ket_noi(scheme, host, cong, het_gio_ket_noi)
        ket_noi.connect()
        try:
            ket_noi.sock.settimeout(het_gio)
        except (AttributeError, OSError):
            pass
        headers_day_du = dict(headers_gui)
        headers_day_du["Connection"] = "close"
        if than is not None:
            headers_day_du["Content-Length"] = str(len(than))
        ket_noi.request(method, dich, body=than, headers=headers_day_du)
        phan_hoi = ket_noi.getresponse()
        ma_http = int(phan_hoi.status)
        than_tra_loi = phan_hoi.read(KICH_THUOC_PHAN_HOI_TOI_DA + 1)
        headers_tra_loi = _headers_thanh_dict(phan_hoi.getheaders())
    except ssl.SSLCertVerificationError:
        raise _loi_vinh_vien(
            "tls-khong-xac-minh",
            "chứng chỉ TLS của máy chủ KHÔNG xác minh được — TỪ CHỐI, không hạ TLS") from None
    except ssl.SSLError:
        # Bắt tay TLS hỏng (không phải do chứng chỉ) ⇒ KHÔNG có byte ứng dụng nào đi qua.
        # Đây là lỗi VĨNH VIỄN của lượt này, không phải "không biết hãng đã xử lý chưa".
        raise _loi_vinh_vien(
            "tls-loi", "bắt tay TLS thất bại — TỪ CHỐI, không hạ TLS") from None
    except (socket.timeout, TimeoutError):
        raise _loi_tam_thoi(
            "het-gio", "hết giờ khi gọi hãng — KHÔNG BIẾT kết quả", timeout=True) from None
    except (ConnectionError, OSError):
        # KHÔNG chép `str(e)`: nó có thể mang host/đường dẫn của ta.
        raise _loi_tam_thoi(
            "mang", "kết nối tới hãng đứt — KHÔNG BIẾT kết quả", timeout=True) from None
    except http.client.HTTPException:
        raise _loi_tam_thoi(
            "giao-thuc-http", "lỗi giao thức HTTP — KHÔNG BIẾT kết quả", timeout=True) from None
    finally:
        _dong(ket_noi)

    if len(than_tra_loi) > KICH_THUOC_PHAN_HOI_TOI_DA:
        raise _loi_vinh_vien(
            "phan-hoi-qua-lon",
            f"phản hồi vượt trần {KICH_THUOC_PHAN_HOI_TOI_DA} byte — TỪ CHỐI đọc tiếp")
    if 200 <= ma_http < 300:
        return TraLoiHTTP(ma_http, than_tra_loi, headers_tra_loi)
    if 300 <= ma_http < 400:
        # KHÔNG đi theo chuyển hướng: đích chuyển hướng có thể trỏ vào mạng nội bộ (SSRF).
        raise _loi_vinh_vien(
            "chuyen-huong", f"hãng trả HTTP {ma_http} chuyển hướng — KHÔNG đi theo",
            ma_http=ma_http)
    if ma_http in (408, 429):
        loai = "het-gio" if ma_http == 408 else "qua-han-muc"
        raise _loi_tam_thoi(
            loai, f"hãng trả HTTP {ma_http} — tạm thời, KHÔNG BIẾT kết quả",
            cho_giay=_doc_retry_after(headers_tra_loi), ma_http=ma_http)
    if 500 <= ma_http <= 599:
        raise _loi_tam_thoi(
            "loi-may-chu", f"hãng trả HTTP {ma_http} — KHÔNG BIẾT kết quả", ma_http=ma_http)
    if ma_http in (401, 403):
        raise _loi_vinh_vien(
            "xac-thuc", f"hãng trả HTTP {ma_http} — xác thực/quyền bị từ chối", ma_http=ma_http)
    if ma_http == 404:
        raise _loi_vinh_vien(
            "khong-tim-thay", f"hãng trả HTTP {ma_http} — không tìm thấy", ma_http=ma_http)
    if ma_http in (400, 409, 422):
        raise _loi_vinh_vien(
            "tham-so", f"hãng trả HTTP {ma_http} — yêu cầu bị từ chối", ma_http=ma_http)
    raise _loi_vinh_vien(
        "http-4xx", f"hãng trả HTTP {ma_http} — không thử lại mù", ma_http=ma_http)


def gui_json(url, headers, payload, *, timeout,
             cho_phep_http_khong_ma_hoa=False, cho_phep_loopback=False):
    """POST MỘT lượt JSON. KHÔNG tự thử lại, KHÔNG ngủ. Hợp đồng tinh thần §36."""
    than = _json_bytes(payload)
    headers_gui = dict(_kiem_headers(headers))
    headers_gui.setdefault("Content-Type", "application/json; charset=utf-8")
    headers_gui.setdefault("Accept", "application/json")
    return _gui("POST", url, headers_gui, than, timeout=timeout,
                cho_phep_http_khong_ma_hoa=cho_phep_http_khong_ma_hoa,
                cho_phep_loopback=cho_phep_loopback,
                # Host hãng còn được kiểm IP công khai sau danh sách trắng: DNS trỏ về
                # 127.0.0.1/10.x cũng bị chặn. Loopback của stub không đi qua nhánh này.
                kiem_ip_cong_khai=True)


# =================================================================================================
# 3. TẢI WAYBILL — CHỐNG SSRF
# =================================================================================================
def _kiem_ip_cong_khai(host):
    """Phân giải `host` và TỪ CHỐI nếu BẤT KỲ địa chỉ nào không phải IP công khai.

    Đây là lớp thứ hai sau danh sách trắng, dành cho hostname của hãng: một bản ghi DNS bị đầu
    độc trỏ về `127.0.0.1`/`10.x` vẫn không được đi qua. Có một khe TOCTOU giữa lúc kiểm và lúc
    nối (DNS rebinding) — đã biết và ghi trong tài liệu; danh sách trắng host hẹp làm khe này
    khó dùng hơn nhiều.
    """
    try:
        ket_qua = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError):
        raise _loi_vinh_vien(
            "dns-khong-phan-giai", f"không phân giải được host {host!r} — TỪ CHỐI tải", host=host
        ) from None
    if not ket_qua:
        raise _loi_vinh_vien(
            "dns-khong-phan-giai", f"host {host!r} không có địa chỉ — TỪ CHỐI tải", host=host)
    for ho in ket_qua:
        ip_chuoi = ho[4][0]
        try:
            ip = ipaddress.ip_address(ip_chuoi)
        except ValueError:
            raise _loi_vinh_vien(
                "dns-ip-la", f"host {host!r} phân giải ra địa chỉ không đọc được — TỪ CHỐI",
                host=host) from None
        if not ip.is_global:
            raise _loi_vinh_vien(
                "ssrf-dns-noi-bo",
                f"TỪ CHỐI tải: host {host!r} phân giải vào địa chỉ KHÔNG công khai ({ip}). "
                "Đây là dấu hiệu SSRF/DNS rebinding.", host=host)


def tai_waybill(url, *, timeout, cho_phep_http_khong_ma_hoa=False, cho_phep_loopback=False):
    """Tải PDF waybill từ URL hãng trả về — CHỈ từ host đã được phép, KHÔNG đi theo redirect.

    Chặn: scheme lạ, userinfo trong URL, host ngoài danh sách trắng, IP nội bộ/metadata,
    chuyển hướng, phản hồi quá lớn, Content-Type không phải PDF/octet-stream.
    """
    scheme, host, cong, dich = tach_url(
        url, cho_phep_http_khong_ma_hoa=cho_phep_http_khong_ma_hoa,
        cho_phep_loopback=cho_phep_loopback)
    if host in HOST_HANG:
        _kiem_ip_cong_khai(host)
    headers = {"Accept": "application/pdf, application/octet-stream",
               "Accept-Encoding": "identity"}
    tra_loi = _gui("GET", url, headers, None, timeout=timeout,
                   cho_phep_http_khong_ma_hoa=cho_phep_http_khong_ma_hoa,
                   cho_phep_loopback=cho_phep_loopback)
    loai = ""
    for k, v in tra_loi.headers.items():
        if k.lower() == "content-type":
            loai = str(v).split(";", 1)[0].strip().lower()
            break
    if loai and loai not in ("application/pdf", "application/octet-stream"):
        raise _loi_vinh_vien(
            "waybill-khong-phai-pdf",
            f"URL waybill trả Content-Type {loai!r} — TỪ CHỐI, không phải PDF")
    if not tra_loi.than:
        raise _loi_vinh_vien("waybill-rong", "URL waybill trả thân RỖNG — không có PDF")
    return tra_loi.than
