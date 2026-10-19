# B1 — ADAPTER BEST EXPRESS (VietnamV3) — MOCK_VERIFIED, chưa có REAL PASS.
#
# TRẠNG THÁI, NÓI NGAY TỪ DÒNG ĐẦU:
#   · Tài liệu API BEST trong đề bài là một Google Docs. Task KHÔNG kèm URL, workspace KHÔNG có
#     bản sao, và agent bị CẤM đoán endpoint/request schema. Vì vậy tệp này chỉ dùng những gì
#     đề bài ĐÃ XÁC NHẬN: 8 đường dẫn, ServiceId=12491, JourneyType 1/2/3, đơn vị GRAM/MILIMET/VND,
#     địa chỉ 2 cấp với District=" ", giới hạn 10/50.
#   · Tên trường WIRE của BEST, hình dạng gói trả lời, mã trạng thái, cách gửi token — **CHƯA
#     XÁC MINH**. Tệp này KHÔNG giả vờ đã biết chúng. Đường LIVE bị chặn bằng
#     `SCHEMA_DA_XAC_MINH = False` (xem `_goi_that`) và `CHO_PHEP_LIVE = False` của lớp nền.
#   · Bộ thử dùng STUB LOOPBACK `127.0.0.1` cổng do OS cấp. KHÔNG có lượt gọi nào tới
#     `800best.com`, kể cả test host. Đây là **MOCK PASS**, KHÔNG phải REAL PASS.
#
# MƯỜI CHỨC NĂNG (đề bài) VÀ ÁNH XẠ ENDPOINT:
#   authenticate    → POST /User/Login
#   createOrder     → POST /Order/Add
#   updateOrder     → POST /Order/Update
#   updateAddress   → POST /Order/UpdateAddress
#   cancelOrder     → POST /Order/Cancel
#   queryTracking   → POST /Order/Query            (tối đa 10 mã/lần)
#   estimateFee     → POST /Service/EstimateFee
#   printWaybill    → POST /Print/PrintWayBill     (tối đa 50 mã/lần)
#   parseWebhook    → không gọi mạng; chỉ đọc gói đến
#   normalizeStatus → không gọi mạng; CHƯA có bảng mã BEST nên trả "chưa biết", không đoán
#
# BA KẾT CỤC, KHÔNG GỘP (`KetQuaHang`):
#   ok=True                → hãng xác nhận;
#   ok=False, timeout=False→ hãng TỪ CHỐI / bị chặn trước khi gửi (biết chắc không có đơn);
#   ok=False, timeout=True → KHÔNG BIẾT kết quả (hết giờ, 5xx, thân 2xx không đọc được).
#   Kết cục thứ ba KHÔNG BAO GIỜ được coi là thành công, và KHÔNG BAO GIỜ được coi là thất bại
#   chắc chắn. `createOrder` khi gặp nó sẽ tự kiểm tra lại bằng `queryTracking` trước.
#
# CHỐNG TRÙNG:
#   Mọi lệnh GHI mang đủ 5 khoá: tenant_id · carrier_id · merchant_order_code · idempotency_key ·
#   request_id. Sổ chống trùng trong tiến trình giữ kết quả theo
#   (thao_tác, tenant, carrier, merchant, idempotency_key) và trả lại NGUYÊN kết quả cũ, không
#   gửi lượt thứ hai. Sổ này KHÔNG bền qua tiến trình — lớp bền là UNIQUE(tenant_id, idem_key)
#   của Order Core. Adapter không thay thế lớp đó, chỉ thêm một chốt.
#   `KHOA_CHONG_TRUNG = False` vì tài liệu BEST CHƯA xác nhận hãng tự chặn mã đơn trùng; vì vậy
#   KHÔNG được thử lại mù thao tác ghi (`transport.chinh_sach_cho` cũng trả so_lan=1).
#
# ĐỊA CHỈ 2 CẤP:
#   `BestAddressAdapter` là một LỚP RIÊNG, không hardcode danh sách tỉnh/quận. District thiếu
#   được gửi đúng một khoảng trắng `" "` theo đặc tả — KHÔNG đổi thành None/"".
import hashlib
import json
import threading
import uuid
from collections import OrderedDict
from urllib.parse import urlsplit

import http_best
import loi_hang
import trang_thai_hang as tth
import transport
from adapter import CarrierAdapter, KetQuaHang, dang_ky

MA_HANG = "best"
TEN_HANG = "BEST Express"

MOCK = http_best.MOCK
SANDBOX = http_best.SANDBOX
PRODUCTION = http_best.PRODUCTION
MOI_TRUONG_HOP_LE = (MOCK, SANDBOX, PRODUCTION)

# ── 8 endpoint ĐÃ XÁC NHẬN trong đề bài ───────────────────────────────────────────────────────
DUONG_API = {
    "authenticate": "/User/Login",
    "createOrder": "/Order/Add",
    "updateOrder": "/Order/Update",
    "updateAddress": "/Order/UpdateAddress",
    "cancelOrder": "/Order/Cancel",
    "queryTracking": "/Order/Query",
    "estimateFee": "/Service/EstimateFee",
    "printWaybill": "/Print/PrintWayBill",
}
THAO_TAC_GHI = ("createOrder", "updateOrder", "updateAddress", "cancelOrder")

# Base URL: ĐÃ XÁC NHẬN trong đề bài; CẢ HAI LÀ HTTP, CHƯA MÃ HOÁ. Lớp `http_best` từ chối
# `http` cho host hãng trừ khi có cờ tường minh.
BASE_URL_PRODUCTION = http_best.BASE_URL[PRODUCTION]
BASE_URL_SANDBOX = http_best.BASE_URL[SANDBOX]
BASE_URL = {SANDBOX: BASE_URL_SANDBOX, PRODUCTION: BASE_URL_PRODUCTION}
CO_HTTP_CHUA_MA_HOA = True

# Endpoint test Order/Query dùng hostname KHÁC — CHƯA XÁC MINH, KHÔNG dùng.
HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH = http_best.HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH

# ── Hằng số nghiệp vụ ĐÃ XÁC NHẬN trong đề bài ───────────────────────────────────────────────
DICH_VU_ID = 12491
DICH_VU_ID_CU_KHONG_DUNG = 12490          # đề bài nói rõ KHÔNG mặc định 12490
JOURNEY_TYPE_HOP_LE = (1, 2, 3)
DON_VI = {"Weight": "GRAM", "Length": "MILIMET", "Width": "MILIMET", "Height": "MILIMET",
          "Cod": "VND", "ProductPrice": "VND"}
GIOI_HAN_QUERY = 10
GIOI_HAN_PRINT = 50

# ── 21 trường bắt buộc của Order/Add ─────────────────────────────────────────────────────────
# CẢNH BÁO NGUỒN: đề bài xác nhận "21 trường bắt buộc" và các NHÓM dữ liệu (người gửi/nhận,
# địa chỉ 2 cấp, khối lượng, kích thước, COD/ProductPrice, ServiceId, JourneyType, hàng hoá,
# ghi chú) nhưng KHÔNG liệt kê tên trường WIRE. Danh sách dưới đây là CÁCH PHÂN RÃ NỘI BỘ đúng
# 21 trường, dùng làm hợp đồng của bộ MOCK — KHÔNG phải schema BEST đã xác minh. Khi có tài
# liệu thật, phải đối chiếu từng tên rồi mới đặt `SCHEMA_DA_XAC_MINH = True`.
TRUONG_BAT_BUOC_ORDER_ADD = (
    "MerchantOrderCode",
    "ServiceId",
    "JourneyType",
    "SenderName",
    "SenderPhone",
    "SenderProvince",
    "SenderDistrict",
    "SenderAddress",
    "ReceiverName",
    "ReceiverPhone",
    "ReceiverProvince",
    "ReceiverDistrict",
    "ReceiverAddress",
    "Weight",
    "Length",
    "Width",
    "Height",
    "GoodsName",
    "Cod",
    "ProductPrice",
    "Remark",
)
assert len(TRUONG_BAT_BUOC_ORDER_ADD) == 21, "Order/Add phải đúng 21 trường bắt buộc"

# Bốn khoá chống trùng đi kèm gói (MerchantOrderCode đã nằm trong 21 trường ở trên).
TRUONG_META_CHONG_TRUNG = ("TenantId", "CarrierId", "IdempotencyKey", "RequestId")

BANG_TRANG_THAI_BEST = {}
TRANG_THAI_DA_XAC_MINH = False
NGUON_TAI_LIEU = ("Đề bài B1 (8 endpoint, 21 trường, ServiceId=12491, JourneyType 1/2/3, "
                  "GRAM/MILIMET/VND, District=' ', giới hạn 10/50) — Google Docs của BEST "
                  "KHÔNG có trong workspace và KHÔNG được cung cấp URL")
LY_DO_CHUA_XAC_MINH = (
    "Tài liệu API BEST là Google Docs, KHÔNG đọc được trong lượt này. Các mục sau CHƯA XÁC MINH: "
    "tên trường wire của Order/Add, hình dạng gói trả lời, mã trạng thái, mã lỗi, cách gửi token, "
    "response schema của 8 endpoint, và hostname test Order/Query "
    f"({HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH}). Không mục nào được đoán.")


class ChuaXacNhanTaiLieu(Exception):
    """Ném khi đường LIVE bị chặn vì schema/response CHƯA được xác nhận.

    Khác `PermissionError` (chưa được PHÉP chạy): đây là CHƯA BIẾT ĐỦ để dựng yêu cầu đúng.
    Hai việc phải sửa theo hai cách khác nhau, nên không gộp làm một ngoại lệ.
    """

    def __init__(self, thao_tac, thieu, moi_truong=None):
        self.thao_tac = thao_tac
        self.thieu = list(thieu or [])
        self.moi_truong = moi_truong
        super().__init__(
            f"BEST: CHƯA XÁC NHẬN tài liệu cho thao tác {thao_tac!r}"
            + (f" (môi trường {moi_truong!r})" if moi_truong else "")
            + ". Thiếu: " + "; ".join(self.thieu)
            + ". KHÔNG gửi lượt nào. Xem docs/BEST_EXPRESS_API_CONTRACT.md mục CHƯA XÁC MINH.")


# =================================================================================================
# 1. ĐỊA CHỈ 2 CẤP — LỚP RIÊNG, KHÔNG HARDCODE DANH SÁCH ĐỊA GIỚI
# =================================================================================================
def _chuoi(gia_tri):
    if gia_tri is None:
        return ""
    return str(gia_tri).strip()


def _kiem_khong_dieu_khien(s, ten):
    for c in s:
        if ord(c) < 0x20 or ord(c) == 0x7F:
            raise ValueError(f"{ten} chứa ký tự điều khiển — không gửi")
    return s


def _chuoi_bat_buoc(gia_tri, ten):
    s = _kiem_khong_dieu_khien(_chuoi(gia_tri), ten)
    if not s:
        raise ValueError(f"thiếu trường bắt buộc {ten}")
    return s


def _chuoi_tuy_chon(gia_tri, ten):
    s = _kiem_khong_dieu_khien(_chuoi(gia_tri), ten)
    return s


def _so_nguyen(gia_tri, ten, *, nho_nhat=None, lon_nhat=None):
    """Số nguyên THẬT. Float bị TỪ CHỐI — kể cả 1.0 — để không có phép làm tròn im lặng."""
    if isinstance(gia_tri, bool):
        raise ValueError(f"{ten} phải là số nguyên, không nhận bool")
    if isinstance(gia_tri, int):
        v = gia_tri
    elif isinstance(gia_tri, str):
        s = gia_tri.strip()
        if not s:
            raise ValueError(f"thiếu trường bắt buộc {ten}")
        if s[0] in "+-":
            if not s[1:].isdigit():
                raise ValueError(f"{ten} phải là số nguyên")
        elif not s.isdigit():
            raise ValueError(f"{ten} phải là số nguyên")
        v = int(s)
    else:
        raise ValueError(f"{ten} phải là số nguyên (nhận {type(gia_tri).__name__})")
    if nho_nhat is not None and v < nho_nhat:
        raise ValueError(f"{ten} phải >= {nho_nhat}")
    if lon_nhat is not None and v > lon_nhat:
        raise ValueError(f"{ten} phải <= {lon_nhat}")
    return v


class BestAddressAdapter:
    """Chuyển địa chỉ nội bộ → dạng 2 cấp mà BEST yêu cầu.

    LUẬT ĐÃ XÁC NHẬN: `District` thiếu phải gửi đúng chuỗi MỘT KHOẢNG TRẮNG `" "`, KHÔNG phải
    `None`/`""`. Tỉnh/thành và dòng địa chỉ vẫn phải có; thiếu thì TỪ CHỐI (không bịa).

    KHÔNG hardcode danh sách tỉnh/quận. Nếu cần đối chiếu danh mục địa giới, truyền một callable
    `tra_cuu_dia_gioi(tinh, quan) -> bool` từ ngoài vào — dữ liệu địa giới thuộc CSDL/dịch vụ,
    không thuộc logic nghiệp vụ của adapter.
    """

    DISTRICT_TRONG = " "

    def __init__(self, tra_cuu_dia_gioi=None):
        if tra_cuu_dia_gioi is not None and not callable(tra_cuu_dia_gioi):
            raise TypeError("tra_cuu_dia_gioi phải là callable hoặc None")
        self.tra_cuu_dia_gioi = tra_cuu_dia_gioi

    def chuan_hoa(self, tinh, quan, dia_chi, xa=None):
        tinh = _chuoi_bat_buoc(tinh, "Province")
        quan = _chuoi_tuy_chon(quan, "District")
        if not quan:
            # ĐẶC TẢ: District = " " — không được đổi thành None/"".
            quan = self.DISTRICT_TRONG
        dia_chi = _chuoi_bat_buoc(dia_chi, "Address")
        xa = _chuoi_tuy_chon(xa, "Ward")
        if xa and xa.lower() not in dia_chi.lower():
            # BEST chỉ nhận 2 cấp; phần xã/phường được giữ trong dòng địa chỉ thay vì bị bỏ mất.
            dia_chi = f"{dia_chi}, {xa}"
        if self.tra_cuu_dia_gioi is not None:
            if not self.tra_cuu_dia_gioi(tinh, quan):
                raise ValueError("cặp tỉnh/quận không có trong danh mục địa giới đã cấu hình")
        return {"Province": tinh, "District": quan, "Address": dia_chi}

    def nguoi_gui(self, don):
        return self.chuan_hoa(don.get("nguoi_gui_tinh"), don.get("nguoi_gui_quan"),
                              don.get("nguoi_gui_dia_chi"), don.get("nguoi_gui_xa"))

    def nguoi_nhan(self, don):
        return self.chuan_hoa(don.get("nguoi_nhan_tinh"), don.get("nguoi_nhan_quan"),
                              don.get("nguoi_nhan_dia_chi"), don.get("nguoi_nhan_xa"))


# =================================================================================================
# 2. ADAPTER
# =================================================================================================
@dang_ky
class AdapterBEST(CarrierAdapter):
    ma_hang = MA_HANG
    ten_hang = TEN_HANG
    CAPABILITIES = {
        "createOrder": True, "cancelOrder": True, "getOrder": True,
        "trackOrder": True, "getShippingFee": True, "getShippingLabel": True,
        "webhook": True,
    }
    # BA cửa độc lập, tất cả đang ĐÓNG. Không agent nào được tự mở (xem tài liệu).
    CHO_PHEP_LIVE = False
    CHO_PHEP_SANDBOX = False
    CHO_PHEP_PRODUCTION = False
    CHO_PHEP_HTTP_KHONG_MA_HOA = False
    # Chưa có tài liệu BEST ⇒ schema/response CHƯA xác minh ⇒ LIVE bị chặn.
    SCHEMA_DA_XAC_MINH = False
    TRANSPORT_THAT_DA_VIET = True
    # Chưa xác nhận hãng tự chặn mã đơn trùng ⇒ KHÔNG thử lại mù thao tác ghi.
    KHOA_CHONG_TRUNG = False

    def __init__(self, credentials: dict, moi_truong: str = "mock", *, base_url=None,
                 gui_http=False, het_gio=10.0, so_lan_doc=3,
                 cho_phep_http_khong_ma_hoa=None, address_adapter=None):
        mt = "" if moi_truong is None else str(moi_truong).strip().lower()
        if mt not in MOI_TRUONG_HOP_LE:
            raise PermissionError(
                f"Adapter BEST: môi trường {moi_truong!r} không hợp lệ "
                f"(chỉ {', '.join(MOI_TRUONG_HOP_LE)}). Mặc định an toàn là 'mock'.")
        if not isinstance(credentials, dict):
            raise TypeError("credentials phải là dict")
        # Lớp nền chặn `sandbox`/`production` khi CHO_PHEP_LIVE=False. Giữ nguyên — không lách.
        super().__init__(dict(credentials), mt)
        self.credentials = dict(credentials)
        self.moi_truong = mt
        self.het_gio = self._kiem_het_gio(het_gio)
        self.so_lan_doc = self._kiem_so_lan(so_lan_doc)
        # PHẢI có CẢ HAI: cờ lớp `CHO_PHEP_HTTP_KHONG_MA_HOA` VÀ tham số tường minh của lượt
        # dựng. Một cờ thôi là một lần lỡ tay; hai cờ là hai lần lỡ tay. Mặc định vẫn CHẶN.
        self.cho_phep_http_khong_ma_hoa = (
            bool(cho_phep_http_khong_ma_hoa) and bool(self.CHO_PHEP_HTTP_KHONG_MA_HOA))
        self.address_adapter = address_adapter or BestAddressAdapter()
        self.gui_http = bool(gui_http)
        self._token = None
        self._token_lock = threading.Lock()
        self._so = OrderedDict()
        self._so_lock = threading.Lock()
        self._so_toi_da = 2048

        # ── Cửa MÔI TRƯỜNG của chính adapter (độc lập với CHO_PHEP_LIVE của lớp nền) ─────────
        if mt == SANDBOX and not self.CHO_PHEP_SANDBOX:
            raise PermissionError(
                "Adapter BEST: môi trường 'sandbox' CHƯA được cấp quyền. "
                "CHO_PHEP_SANDBOX đang False; bật nó KHÔNG đủ — còn CHO_PHEP_LIVE và "
                "SCHEMA_DA_XAC_MINH. Xem docs/BEST_EXPRESS_API_CONTRACT.md §BLOCKED.")
        if mt == PRODUCTION and not self.CHO_PHEP_PRODUCTION:
            raise PermissionError(
                "Adapter BEST: môi trường 'production' CHƯA được cấp quyền. "
                "CHO_PHEP_PRODUCTION đang False; xem docs/BEST_EXPRESS_API_CONTRACT.md §BLOCKED.")

        # ── Base URL ─────────────────────────────────────────────────────────────────────────
        if base_url is not None:
            if not isinstance(base_url, str) or not base_url.strip():
                raise ValueError("base_url phải là chuỗi khác rỗng")
            self.base_url = base_url.strip()
            self._kiem_base_url(self.base_url, mt)
        else:
            self.base_url = None if mt == MOCK else BASE_URL.get(mt)

        if self.gui_http:
            if mt != MOCK:
                raise PermissionError(
                    "Adapter BEST: `gui_http=True` chỉ dành cho bộ thử MOCK trên loopback. "
                    "Đường LIVE đi qua `_goi_that`, không qua cờ này.")
            if not self.base_url:
                raise PermissionError(
                    "Adapter BEST: `gui_http=True` cần `base_url` loopback (stub cục bộ).")
            host = (urlsplit(self.base_url).hostname or "").lower()
            if not http_best.la_host_cuc_bo(host):
                raise PermissionError(
                    f"Adapter BEST: `gui_http=True` chỉ nhận loopback, nhận host {host!r}.")
        elif mt == MOCK and self.base_url is not None:
            # Mock được phép có base_url để kiểm URL, nhưng KHÔNG được trỏ vào host hãng.
            host = (urlsplit(self.base_url).hostname or "").lower()
            if not http_best.la_host_cuc_bo(host):
                raise PermissionError(
                    f"Adapter BEST: môi trường MOCK không được trỏ vào host {host!r}. "
                    "Mock chỉ dựng stub trên loopback; gọi host hãng là vi phạm ràng buộc.")

        # ── HTTP chưa mã hoá: mặc định CHẶN cho sandbox/production ───────────────────────────
        if mt in (SANDBOX, PRODUCTION):
            self._kiem_http_cua_base_url(self.base_url, mt)

    # ── kiểm tham số cấu hình ────────────────────────────────────────────────────────────────
    @staticmethod
    def _kiem_het_gio(het_gio):
        if isinstance(het_gio, bool) or not isinstance(het_gio, (int, float)):
            raise ValueError("het_gio phải là số giây")
        v = float(het_gio)
        if not (v > 0 and v <= 120):
            raise ValueError("het_gio phải > 0 và <= 120 giây")
        return v

    @staticmethod
    def _kiem_so_lan(so_lan):
        if isinstance(so_lan, bool) or not isinstance(so_lan, int):
            raise ValueError("so_lan_doc phải là số nguyên")
        if not (1 <= so_lan <= 10):
            raise ValueError("so_lan_doc phải trong khoảng 1..10")
        return so_lan

    def _kiem_base_url(self, url, mt):
        if "?" in url or "#" in url:
            raise ValueError("base_url không được chứa query/fragment")
        try:
            scheme, host, cong, duong = http_best.tach_url(
                url, cho_phep_http_khong_ma_hoa=self.cho_phep_http_khong_ma_hoa,
                cho_phep_loopback=(mt == MOCK))
        except transport.LoiVinhVien as e:
            # Đổi sang ValueError/PermissionError để nơi dựng adapter thấy lỗi cấu hình rõ ràng.
            if getattr(e, "ma", "") == "http-khong-ma-hoa":
                raise PermissionError(
                    f"Adapter BEST: TỪ CHỐI base_url HTTP CHƯA MÃ HOÁ cho môi trường {mt!r}. "
                    "Bật cờ cho_phep_http_khong_ma_hoa CHỈ khi môi trường đã được duyệt."
                ) from None
            raise ValueError(f"base_url không dùng được: {e}") from None
        if mt == MOCK:
            if not http_best.la_host_cuc_bo(host):
                raise PermissionError(
                    f"Adapter BEST: MOCK chỉ nhận base_url loopback, nhận {host!r}.")
        else:
            if http_best.la_host_cuc_bo(host):
                raise PermissionError(
                    "Adapter BEST: sandbox/production KHÔNG được trỏ vào loopback.")
            host_mong_doi = http_best.HOST_SANDBOX if mt == SANDBOX else http_best.HOST_PRODUCTION
            if host != host_mong_doi:
                raise PermissionError(
                    f"Adapter BEST: môi trường {mt!r} chỉ nhận host {host_mong_doi!r}, "
                    f"nhận {host!r}.")

    def _kiem_http_cua_base_url(self, url, mt):
        if not url:
            return
        if url.lower().startswith("http://") and not self.cho_phep_http_khong_ma_hoa:
            raise PermissionError(
                f"Adapter BEST: TỪ CHỐI chạy {mt!r} trên HTTP CHƯA MÃ HOÁ ({url.split('/')[2]}). "
                "Credential và dữ liệu đơn thật không đi qua kênh bản rõ. "
                "Bật `cho_phep_http_khong_ma_hoa=True` CHỈ khi môi trường đã được duyệt.")

    # ── capabilities ─────────────────────────────────────────────────────────────────────────
    def getCapabilities(self) -> dict:
        ra = super().getCapabilities()
        ra.update({
            "endpoint": dict(DUONG_API),
            "gioi_han": {"queryTracking": GIOI_HAN_QUERY, "printWaybill": GIOI_HAN_PRINT},
            "don_vi": dict(DON_VI),
            "service_id": DICH_VU_ID,
            "journey_type_hop_le": list(JOURNEY_TYPE_HOP_LE),
            "tai_lieu_da_xac_minh": False,
            "schema_da_xac_minh": bool(self.SCHEMA_DA_XAC_MINH),
            "webhook_da_xac_thuc": False,
            "bang_trang_thai_da_xac_minh": bool(TRANG_THAI_DA_XAC_MINH),
            "ly_do_chua_xac_minh": LY_DO_CHUA_XAC_MINH,
            "host_test_order_query_chua_xac_minh": HOST_TEST_ORDER_QUERY_CHUA_XAC_MINH,
            "http_chua_ma_hoa": CO_HTTP_CHUA_MA_HOA,
            "base_url": self.base_url,
            "cho_phep_http_khong_ma_hoa": bool(self.cho_phep_http_khong_ma_hoa),
            "transport": "http_best" if (self.gui_http or self.moi_truong != MOCK) else "mock",
            "gui_http": bool(self.gui_http),
        })
        return ra

    def __repr__(self):
        # KHÔNG in credentials/token.
        return (f"<AdapterBEST moi_truong={self.moi_truong!r} "
                f"gui_http={self.gui_http} base_url={self.base_url!r}>")

    # =============================================================================================
    # 3. TENANT / CARRIER — KHÔNG XÁC ĐỊNH ĐƯỢC THÌ DENY
    # =============================================================================================
    def _tenant(self, don=None):
        tenant_cred = _chuoi(self.credentials.get("tenant_id"))
        tenant_don = _chuoi(don.get("tenant_id")) if isinstance(don, dict) else ""
        if tenant_cred and tenant_don and tenant_cred != tenant_don:
            raise PermissionError(
                "Adapter BEST: tenant_id trong đơn KHÁC tenant_id của credentials — DENY. "
                "Không có đường gọi chéo tenant.")
        tenant = tenant_don or tenant_cred
        if not tenant:
            raise PermissionError(
                "Adapter BEST: KHÔNG XÁC ĐỊNH ĐƯỢC tenant_id — DENY. "
                "Mọi truy vấn phải theo tenant; thiếu tenant thì không gửi gì.")
        return tenant

    def _carrier(self, don=None, *, bat_buoc=False):
        """Xác định carrier_id của lệnh. Ưu tiên dữ liệu ĐƠN, rồi mới tới credentials.

        Vì sao không gộp mọi giá trị rồi so tập: `carrier_id` (mã hãng, vd "best") và
        `carrier_account_id` (khoá tài khoản hãng trong CSDL) là HAI KHÔNG GIAN TÊN khác nhau.
        Gộp chúng lại sẽ DENY oan một cấu hình hợp lệ. Nhưng nếu HAI giá trị CÙNG không gian
        tên mà lệch nhau (đơn nói tài khoản 9, credentials nói tài khoản 10) thì phải DENY —
        đó là dấu hiệu dùng nhầm tài khoản.
        """
        don_account = _chuoi(don.get("carrier_account_id")) if isinstance(don, dict) else ""
        don_carrier = _chuoi(don.get("carrier_id")) if isinstance(don, dict) else ""
        cred_account = _chuoi(self.credentials.get("carrier_account_id"))
        cred_carrier = _chuoi(self.credentials.get("carrier_id"))
        # KHÔNG so `carrier_id` với `carrier_account_id`: chúng là hai không gian tên khác nhau
        # (mã hãng vs khoá tài khoản). Chỉ so trong CÙNG không gian tên.
        if don_carrier and cred_carrier and don_carrier != cred_carrier:
            raise PermissionError(
                "Adapter BEST: carrier_id trong đơn KHÁC credentials — DENY.")
        if don_account and cred_account and don_account != cred_account:
            raise PermissionError(
                "Adapter BEST: carrier_account_id trong đơn KHÁC credentials — DENY, "
                "không dùng nhầm tài khoản hãng.")
        carrier = don_account or don_carrier or cred_account or cred_carrier
        if bat_buoc and not carrier:
            raise PermissionError(
                "Adapter BEST: KHÔNG XÁC ĐỊNH ĐƯỢC carrier_id — DENY cho thao tác ghi.")
        return carrier

    @staticmethod
    def _kiem_request_id(request_id):
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError("request_id phải là chuỗi khác rỗng")
        request_id = request_id.strip()
        if len(request_id) > 128:
            raise ValueError("request_id quá dài (>128)")
        for c in request_id:
            # ASCII: request_id đi vào header `X-Request-Id`; ký tự ngoài latin-1 làm
            # `http.client` ném lỗi sau khi đã dựng yêu cầu — chặn từ đây, trước mọi I/O.
            if not (c.isascii() and c.isalnum()) and c not in "._:-":
                raise ValueError("request_id chỉ nhận chữ/số ASCII và . _ : -")
        return request_id

    @staticmethod
    def _kiem_idempotency_key(idem):
        if not isinstance(idem, str) or not idem.strip():
            raise ValueError("thiếu idempotency_key — không gửi thao tác ghi")
        idem = idem.strip()
        if len(idem) > 256:
            raise ValueError("idempotency_key quá dài (>256)")
        return _kiem_khong_dieu_khien(idem, "idempotency_key")

    @staticmethod
    def _kiem_ma_van_don(ma):
        ma = _chuoi(ma)
        if not ma:
            raise ValueError("thiếu mã vận đơn")
        if len(ma) > 128:
            raise ValueError("mã vận đơn quá dài (>128)")
        return _kiem_khong_dieu_khien(ma, "mã vận đơn")

    def _ctx_ghi(self, don, *, bat_buoc_carrier=True):
        if not isinstance(don, dict):
            raise ValueError("đơn phải là dict")
        tenant = self._tenant(don)
        carrier = self._carrier(don, bat_buoc=bat_buoc_carrier)
        merchant = _chuoi(don.get("ma_don") or don.get("merchant_order_code"))
        merchant = _kiem_khong_dieu_khien(merchant, "ma_don")
        if not merchant:
            raise ValueError("thiếu merchant_order_code (ma_don) — không gửi thao tác ghi")
        if len(merchant) > 128:
            raise ValueError("merchant_order_code quá dài (>128)")
        idem = self._kiem_idempotency_key(don.get("idempotency_key") or don.get("idem_key"))
        request_id = self._kiem_request_id(don.get("request_id") or uuid.uuid4().hex)
        return {"tenant_id": tenant, "carrier_id": carrier,
                "merchant_order_code": merchant, "idempotency_key": idem,
                "request_id": request_id}

    def _ctx_theo_ma(self, ma, tien_to):
        tenant = self._tenant()
        carrier = self._carrier(bat_buoc=False)
        ma = self._kiem_ma_van_don(ma)
        idem = self._kiem_idempotency_key(f"{tien_to}:{tenant}:{ma}")
        request_id = self._kiem_request_id(uuid.uuid4().hex)
        return {"tenant_id": tenant, "carrier_id": carrier,
                "merchant_order_code": ma, "idempotency_key": idem,
                "request_id": request_id}

    @staticmethod
    def _meta(ctx):
        return {"TenantId": ctx["tenant_id"], "CarrierId": ctx["carrier_id"],
                "IdempotencyKey": ctx["idempotency_key"], "RequestId": ctx["request_id"]}

    # =============================================================================================
    # 4. SỔ CHỐNG TRÙNG TRONG TIẾN TRÌNH (lớp bền là UNIQUE(tenant_id, idem_key) của Order Core)
    # =============================================================================================
    @staticmethod
    def _khoa_so(thao_tac, ctx):
        return (thao_tac, ctx["tenant_id"], ctx["carrier_id"],
                ctx["merchant_order_code"], ctx["idempotency_key"])

    def _lay_so(self, khoa):
        with self._so_lock:
            kq = self._so.get(khoa)
            if kq is not None:
                self._so.move_to_end(khoa)
            return kq

    def _ghi_so(self, khoa, kq):
        with self._so_lock:
            self._so[khoa] = kq
            self._so.move_to_end(khoa)
            while len(self._so) > self._so_toi_da:
                self._so.popitem(last=False)

    @staticmethod
    def _ban_sao(kq):
        return KetQuaHang(kq.ok, kq.ma_van_don, kq.phi, kq.loi, kq.timeout, dict(kq.tho))

    def _phat_lai(self, kq):
        moi = self._ban_sao(kq)
        moi.tho["phat_lai_idempotent"] = True
        return moi

    # =============================================================================================
    # 5. DỰNG GÓI — 21 TRƯỜNG ORDER/ADD
    # =============================================================================================
    @staticmethod
    def _lay(don, *ten):
        for t in ten:
            if t in don and don[t] is not None:
                return don[t]
        return None

    def _dung_payload_order_add(self, don, ctx):
        if not isinstance(don, dict):
            raise ValueError("đơn phải là dict")
        try:
            nguoi_gui = self.address_adapter.nguoi_gui(don)
            nguoi_nhan = self.address_adapter.nguoi_nhan(don)
        except ValueError as e:
            raise ValueError(f"địa chỉ: {e}") from None

        service_id = self._lay(don, "service_id", "dich_vu_id")
        service_id = DICH_VU_ID if service_id is None else _so_nguyen(service_id, "ServiceId")
        if service_id != DICH_VU_ID:
            raise ValueError(
                f"ServiceId phải là {DICH_VU_ID} theo đặc tả; nhận {service_id!r}. "
                f"KHÔNG dùng {DICH_VU_ID_CU_KHONG_DUNG}.")

        journey_type = self._lay(don, "journey_type", "loai_hanh_trinh")
        if journey_type is None:
            raise ValueError("thiếu JourneyType (1/2/3) — adapter KHÔNG tự chọn mặc định")
        journey_type = _so_nguyen(journey_type, "JourneyType")
        if journey_type not in JOURNEY_TYPE_HOP_LE:
            raise ValueError(f"JourneyType phải thuộc {JOURNEY_TYPE_HOP_LE}, nhận {journey_type}")

        weight = _so_nguyen(self._lay(don, "khoi_luong_gram", "weight_gram"),
                            "Weight (GRAM)", nho_nhat=1)
        length = _so_nguyen(self._lay(don, "chieu_dai_mm", "length_mm", "dai_mm"),
                            "Length (MILIMET)", nho_nhat=1)
        width = _so_nguyen(self._lay(don, "chieu_rong_mm", "width_mm", "rong_mm"),
                           "Width (MILIMET)", nho_nhat=1)
        height = _so_nguyen(self._lay(don, "chieu_cao_mm", "height_mm", "cao_mm"),
                            "Height (MILIMET)", nho_nhat=1)
        cod = _so_nguyen(self._lay(don, "cod") if self._lay(don, "cod") is not None else 0,
                         "Cod (VND)", nho_nhat=0, lon_nhat=10**15)
        gia_tri = self._lay(don, "gia_tri_khai", "product_price")
        gia_tri = _so_nguyen(0 if gia_tri is None else gia_tri,
                             "ProductPrice (VND)", nho_nhat=0, lon_nhat=10**15)

        truong = {
            "MerchantOrderCode": ctx["merchant_order_code"],
            "ServiceId": service_id,
            "JourneyType": journey_type,
            "SenderName": _chuoi_bat_buoc(self._lay(don, "nguoi_gui_ten"), "SenderName"),
            "SenderPhone": _chuoi_bat_buoc(self._lay(don, "nguoi_gui_sdt"), "SenderPhone"),
            "SenderProvince": nguoi_gui["Province"],
            "SenderDistrict": nguoi_gui["District"],
            "SenderAddress": nguoi_gui["Address"],
            "ReceiverName": _chuoi_bat_buoc(self._lay(don, "nguoi_nhan_ten"), "ReceiverName"),
            "ReceiverPhone": _chuoi_bat_buoc(self._lay(don, "nguoi_nhan_sdt"), "ReceiverPhone"),
            "ReceiverProvince": nguoi_nhan["Province"],
            "ReceiverDistrict": nguoi_nhan["District"],
            "ReceiverAddress": nguoi_nhan["Address"],
            "Weight": weight,
            "Length": length,
            "Width": width,
            "Height": height,
            "GoodsName": _chuoi_bat_buoc(self._lay(don, "hang_hoa", "goods_name"), "GoodsName"),
            "Cod": cod,
            "ProductPrice": gia_tri,
            "Remark": _chuoi_tuy_chon(self._lay(don, "ghi_chu", "remark"), "Remark"),
        }
        if set(truong) != set(TRUONG_BAT_BUOC_ORDER_ADD):
            # Chốt chặn nội bộ: sửa danh sách mà quên dựng trường là hỏng IM LẶNG. Ném ra.
            thieu = sorted(set(TRUONG_BAT_BUOC_ORDER_ADD) - set(truong))
            thua = sorted(set(truong) - set(TRUONG_BAT_BUOC_ORDER_ADD))
            raise ValueError(f"gói Order/Add lệch hợp đồng 21 trường (thiếu={thieu}, thừa={thua})")
        return dict(self._meta(ctx), **truong)

    def _dung_payload_estimate(self, don, ctx):
        service_id = self._lay(don, "service_id", "dich_vu_id")
        service_id = DICH_VU_ID if service_id is None else _so_nguyen(service_id, "ServiceId")
        if service_id != DICH_VU_ID:
            raise ValueError(f"ServiceId phải là {DICH_VU_ID}, nhận {service_id!r}")
        journey_type = self._lay(don, "journey_type", "loai_hanh_trinh")
        if journey_type is None:
            raise ValueError("thiếu JourneyType (1/2/3) — không tự chọn mặc định")
        journey_type = _so_nguyen(journey_type, "JourneyType")
        if journey_type not in JOURNEY_TYPE_HOP_LE:
            raise ValueError(f"JourneyType phải thuộc {JOURNEY_TYPE_HOP_LE}")
        nguoi_gui = self.address_adapter.nguoi_gui(don)
        nguoi_nhan = self.address_adapter.nguoi_nhan(don)
        cod = self._lay(don, "cod")
        gia_tri = self._lay(don, "gia_tri_khai", "product_price")
        return dict(self._meta(ctx), **{
            "ServiceId": service_id,
            "JourneyType": journey_type,
            "Weight": _so_nguyen(self._lay(don, "khoi_luong_gram", "weight_gram"),
                                 "Weight (GRAM)", nho_nhat=1),
            "Length": _so_nguyen(self._lay(don, "chieu_dai_mm", "length_mm", "dai_mm"),
                                 "Length (MILIMET)", nho_nhat=1),
            "Width": _so_nguyen(self._lay(don, "chieu_rong_mm", "width_mm", "rong_mm"),
                                "Width (MILIMET)", nho_nhat=1),
            "Height": _so_nguyen(self._lay(don, "chieu_cao_mm", "height_mm", "cao_mm"),
                                 "Height (MILIMET)", nho_nhat=1),
            "SenderProvince": nguoi_gui["Province"],
            "SenderDistrict": nguoi_gui["District"],
            "ReceiverProvince": nguoi_nhan["Province"],
            "ReceiverDistrict": nguoi_nhan["District"],
            "Cod": _so_nguyen(0 if cod is None else cod, "Cod (VND)", nho_nhat=0),
            "ProductPrice": _so_nguyen(0 if gia_tri is None else gia_tri,
                                       "ProductPrice (VND)", nho_nhat=0),
        })

    def _dung_payload_update_address(self, don, ctx, waybill):
        try:
            nguoi_nhan = self.address_adapter.nguoi_nhan(don)
        except ValueError as e:
            raise ValueError(f"địa chỉ nhận: {e}") from None
        return dict(self._meta(ctx), **{
            "WaybillCode": waybill,
            "ReceiverName": _chuoi_bat_buoc(self._lay(don, "nguoi_nhan_ten"), "ReceiverName"),
            "ReceiverPhone": _chuoi_bat_buoc(self._lay(don, "nguoi_nhan_sdt"), "ReceiverPhone"),
            "ReceiverProvince": nguoi_nhan["Province"],
            "ReceiverDistrict": nguoi_nhan["District"],
            "ReceiverAddress": nguoi_nhan["Address"],
        })

    def _dung_payload_huy(self, ctx, waybill, ly_do):
        return dict(self._meta(ctx), **{
            "WaybillCode": waybill,
            "Reason": _chuoi_tuy_chon(ly_do, "Reason"),
        })

    # =============================================================================================
    # 6. GỬI QUA http_best — CHỈ MOCK+STUB hoặc LIVE đã xác minh
    # =============================================================================================
    def _headers(self, request_id):
        h = {"X-Request-Id": request_id, "Accept": "application/json"}
        token = self._token
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _chinh_sach(self, thao_tac):
        if thao_tac in THAO_TAC_GHI:
            # Thao tác GHI: KHÔNG thử lại mù. Hãng chưa xác nhận khoá chống trùng của chính nó.
            return transport.ChinhSach(so_lan=1, duoc_thu_lai=False, het_gio=self.het_gio)
        return transport.ChinhSach(so_lan=self.so_lan_doc, het_gio=self.het_gio)

    def _url_endpoint(self, thao_tac):
        if thao_tac not in DUONG_API:
            raise ValueError(f"thao tác {thao_tac!r} không có trong DUONG_API")
        if not self.base_url:
            raise ChuaXacNhanTaiLieu(
                thao_tac, ["chưa có base_url — không ghép bừa URL"], self.moi_truong)
        return self.base_url.rstrip("/") + DUONG_API[thao_tac]

    def _kiem_cua_live(self, thao_tac):
        """Ba cửa độc lập cho đường LIVE. Mọi cửa đóng ⇒ ném, KHÔNG gửi."""
        if self.moi_truong == SANDBOX and not self.CHO_PHEP_SANDBOX:
            raise PermissionError("Adapter BEST: sandbox CHƯA được cấp quyền — không gửi.")
        if self.moi_truong == PRODUCTION and not self.CHO_PHEP_PRODUCTION:
            raise PermissionError("Adapter BEST: production CHƯA được cấp quyền — không gửi.")
        if self.moi_truong in (SANDBOX, PRODUCTION) and not self.CHO_PHEP_LIVE:
            raise PermissionError("Adapter BEST: CHO_PHEP_LIVE=False — không gửi.")
        if not self.SCHEMA_DA_XAC_MINH:
            raise ChuaXacNhanTaiLieu(
                thao_tac,
                ["tên trường wire + hình dạng gói trả lời của BEST CHƯA được xác nhận",
                 "Google Docs của BEST không có trong workspace và không có URL",
                 "đặt SCHEMA_DA_XAC_MINH=True CHỈ sau khi đã đối chiếu tài liệu thật"],
                self.moi_truong)

    def _gui_that(self, thao_tac, payload, request_id):
        """Gửi MỘT yêu cầu (qua `transport.goi`) và trả `(KetQuaHang, data|None)`."""
        if self.moi_truong == MOCK and not self.gui_http:
            raise RuntimeError("mock không dùng _gui_that — nhánh mock phải xử lý trước")
        if self.moi_truong != MOCK:
            self._kiem_cua_live(thao_tac)
        url = self._url_endpoint(thao_tac)
        cs = self._chinh_sach(thao_tac)
        dem = {"so_lan": 0}

        def _mot_lan():
            dem["so_lan"] += 1
            return http_best.gui_json(
                url, self._headers(request_id), payload, timeout=cs.het_gio,
                cho_phep_http_khong_ma_hoa=self.cho_phep_http_khong_ma_hoa,
                cho_phep_loopback=(self.moi_truong == MOCK))

        try:
            tra_loi, so_lan, _nhat_ky = transport.goi(_mot_lan, thao_tac, chinh_sach=cs)
        except (transport.LoiTamThoi, transport.LoiVinhVien) as e:
            return self._ket_qua_tu_loi(e, thao_tac, request_id, dem["so_lan"]), None

        try:
            goi = json.loads(tra_loi.than.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            kq = self._ket_qua_khong_biet(
                thao_tac, "HTTP 2xx nhưng thân KHÔNG phải JSON — KHÔNG BIẾT hãng đã xử lý chưa",
                request_id, so_lan_goi=dem["so_lan"])
            return kq, None
        if not isinstance(goi, dict):
            kq = self._ket_qua_khong_biet(
                thao_tac, "HTTP 2xx nhưng thân không phải JSON object — KHÔNG BIẾT kết quả",
                request_id, so_lan_goi=dem["so_lan"])
            return kq, None
        if goi.get("success") is False:
            # KHÔNG chép `message` nguyên văn: văn bản NGOÀI có thể echo credential.
            msg = str(goi.get("message") or "")
            kq = self._ket_qua_tu_choi(
                thao_tac, f"hãng từ chối (mock envelope; message dài {len(msg)} ký tự, "
                          "KHÔNG chép nguyên văn)", request_id, so_lan_goi=dem["so_lan"])
            return kq, None
        if goi.get("success") is not True:
            kq = self._ket_qua_khong_biet(
                thao_tac, "gói 2xx thiếu cờ success=true — KHÔNG BIẾT kết quả",
                request_id, so_lan_goi=dem["so_lan"])
            return kq, None
        kq = KetQuaHang(True, tho={
            "mock": self.moi_truong == MOCK, "moi_truong": self.moi_truong,
            "hang": MA_HANG, "thao_tac": thao_tac, "request_id": request_id,
            "endpoint": DUONG_API[thao_tac], "so_lan_goi": dem["so_lan"],
            "transport": "http_best",
        })
        return kq, goi.get("data")

    # ── dựng KetQuaHang ──────────────────────────────────────────────────────────────────────
    @staticmethod
    def _loi_chuan_dict(ma_chuan, thao_tac, ma_goc=None, thong_diep="", http_status=None):
        return {"ma_chuan": ma_chuan, "ma_goc_hang": None if ma_goc is None else str(ma_goc),
                "thong_diep": thong_diep, "co_the_thu_lai": ma_chuan in loi_hang.DUOC_THU_LAI,
                "hang": MA_HANG, "thao_tac": thao_tac, "http_status": http_status}

    def _ket_qua_tu_loi(self, e, thao_tac, request_id, so_lan_goi=0):
        ma_http = getattr(e, "ma_http", 0) or 0
        if ma_http and not (200 <= int(ma_http) < 300):
            loi = loi_hang.tu_http(
                int(ma_http), hang=MA_HANG, thao_tac=thao_tac,
                thong_diep=str(e))
        else:
            loi = loi_hang.tu_ngoai_le(e, hang=MA_HANG, thao_tac=thao_tac)
        return KetQuaHang(
            False, timeout=(loi.ma_chuan == loi_hang.HET_GIO), loi=str(loi),
            tho={"mock": self.moi_truong == MOCK, "moi_truong": self.moi_truong,
                 "hang": MA_HANG, "thao_tac": thao_tac, "request_id": request_id,
                 "endpoint": DUONG_API.get(thao_tac), "so_lan_goi": so_lan_goi,
                 "transport": "http_best",
                 "ket_cuc": getattr(e, "ket_cuc", None),
                 "loi_chuan": loi.nhu_dict()})

    def _ket_qua_tu_choi(self, thao_tac, ly_do, request_id, *, ma_goc=None,
                         so_lan_goi=0, **tho):
        d = {"mock": self.moi_truong == MOCK, "moi_truong": self.moi_truong,
             "hang": MA_HANG, "thao_tac": thao_tac, "request_id": request_id,
             "endpoint": DUONG_API.get(thao_tac), "so_lan_goi": so_lan_goi,
             "loi_chuan": self._loi_chuan_dict(loi_hang.THAM_SO_SAI, thao_tac,
                                               ma_goc=ma_goc, thong_diep=ly_do)}
        d.update(tho)
        return KetQuaHang(False, timeout=False, loi=f"BEST: {ly_do}", tho=d)

    def _ket_qua_khong_biet(self, thao_tac, ly_do, request_id, *, so_lan_goi=0, **tho):
        d = {"mock": self.moi_truong == MOCK, "moi_truong": self.moi_truong,
             "hang": MA_HANG, "thao_tac": thao_tac, "request_id": request_id,
             "endpoint": DUONG_API.get(thao_tac), "so_lan_goi": so_lan_goi,
             "can_doi_soat": True,
             "loi_chuan": self._loi_chuan_dict(loi_hang.HET_GIO, thao_tac,
                                               thong_diep=ly_do)}
        d.update(tho)
        return KetQuaHang(False, timeout=True, loi=f"BEST: KHÔNG BIẾT kết quả — {ly_do}", tho=d)

    def _ket_qua_ok(self, thao_tac, request_id, *, endpoint=None, **tho):
        d = {"mock": self.moi_truong == MOCK, "moi_truong": self.moi_truong,
             "hang": MA_HANG, "thao_tac": thao_tac, "request_id": request_id,
             "endpoint": endpoint or DUONG_API.get(thao_tac),
             "transport": "http_best" if (self.gui_http or self.moi_truong != MOCK) else "mock"}
        ma_van_don = tho.pop("ma_van_don", None)
        phi = tho.pop("phi", None)
        d.update(tho)
        return KetQuaHang(True, ma_van_don=ma_van_don, phi=phi, tho=d)

    # =============================================================================================
    # 7. XÁC THỰC
    # =============================================================================================
    def _thong_tin_dang_nhap(self):
        c = self.credentials
        user = _chuoi(c.get("username") or c.get("user") or c.get("tai_khoan") or c.get("account"))
        mat_khau = _chuoi(c.get("password") or c.get("mat_khau") or c.get("pass"))
        if not user or not mat_khau:
            raise ValueError("thiếu username/password trong credentials — không gửi /User/Login")
        return user, mat_khau

    def authenticate(self):
        """POST /User/Login. KHÔNG bao giờ trả token ra ngoài — chỉ giữ trong bộ nhớ."""
        tenant = self._tenant()
        request_id = self._kiem_request_id(uuid.uuid4().hex)
        try:
            user, mat_khau = self._thong_tin_dang_nhap()
        except ValueError as e:
            return self._ket_qua_tu_choi("authenticate", str(e), request_id)

        if self.moi_truong == MOCK and not self.gui_http:
            with self._token_lock:
                self._token = "MOCK-TOKEN-KHONG-THAT"
            return self._ket_qua_ok(
                "authenticate", request_id, mock=True, co_token=True,
                token_khong_duoc_tra_ra=True,
                ghi_chu="MOCK: token giả, không rời bộ nhớ, không xuất hiện trong kết quả")

        payload = {"TenantId": tenant, "Username": user, "Password": mat_khau}
        kq, data = self._gui_that("authenticate", payload, request_id)
        if not kq.ok:
            return kq
        token = self._lay_gia_tri(data, ("Token", "token", "AccessToken", "access_token"))
        if not isinstance(token, str) or not token.strip():
            return self._ket_qua_tu_choi(
                "authenticate", "login 2xx nhưng KHÔNG đọc được token — không dùng được",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        token = token.strip()
        if len(token) > 4096 or any(ord(c) < 0x21 or ord(c) == 0x7F for c in token):
            return self._ket_qua_tu_choi(
                "authenticate", "token trả về có ký tự không hợp lệ — TỪ CHỐI dùng",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        with self._token_lock:
            self._token = token
        kq.tho.update({"co_token": True, "token_khong_duoc_tra_ra": True})
        return kq

    def _dam_bao_token(self):
        """Đăng nhập nếu chưa có token. Trả `KetQuaHang` lỗi, hoặc None nếu ổn."""
        if self.moi_truong == MOCK and not self.gui_http:
            return None
        with self._token_lock:
            if self._token:
                return None
        kq = self.authenticate()
        if not kq.ok:
            return kq
        with self._token_lock:
            if not self._token:
                return self._ket_qua_tu_choi(
                    "authenticate", "login báo thành công nhưng không giữ được token",
                    kq.tho.get("request_id", ""))
        return None

    @staticmethod
    def _lay_gia_tri(data, ten_list):
        if isinstance(data, dict):
            for ten in ten_list:
                if ten in data and data[ten] not in (None, ""):
                    return data[ten]
        return None

    # =============================================================================================
    # 8. TẠO / CẬP NHẬT / HUỶ ĐƠN
    # =============================================================================================
    @staticmethod
    def _ma_van_don_tu_data(data):
        return AdapterBEST._lay_gia_tri(
            data, ("WaybillCode", "waybill_code", "WaybillNo", "OrderCode", "order_code",
                   "ma_van_don", "TrackingNumber", "tracking_number"))

    def _xu_ly_sau_timeout_tao_don(self, ctx, kq_timeout):
        """Timeout createOrder ⇒ tra cứu TRƯỚC, không gửi lại mù.

        Chỉ một kết cục được nâng thành THÀNH CÔNG: tra cứu thấy mã vận đơn. Mọi kết cục khác
        — kể cả "không tìm thấy" — giữ UNKNOWN, vì đơn có thể chưa kịp hiện bên hãng. Đây là
        chiều an toàn: một lượt đối soát thừa rẻ hơn một vận đơn trùng.
        """
        kq_timeout.tho["da_kiem_tra_sau_timeout"] = True
        try:
            tra = self.queryTracking(ctx["merchant_order_code"])
        except Exception:
            kq_timeout.tho["ket_qua_kiem_tra"] = "loi_khi_tra_cuu"
            return kq_timeout
        kq_timeout.tho["ket_qua_kiem_tra"] = "da_vao" if (tra.ok and tra.ma_van_don) else (
            "khong_tim_thay" if (not tra.timeout and tra.ok is False) else "chua_ro")
        if tra.ok and tra.ma_van_don:
            moi = self._ket_qua_ok(
                "createOrder", ctx["request_id"],
                ma_van_don=tra.ma_van_don, da_kiem_tra_sau_timeout=True,
                ket_qua_sau_timeout="da_vao",
                request_id_tra_cuu=tra.tho.get("request_id"),
                ghi_chu="createOrder timeout nhưng tra cứu thấy đơn ĐÃ VÀO — không gửi lại")
            return moi
        kq_timeout.tho["can_doi_soat"] = True
        return kq_timeout

    def createOrder(self, don) -> KetQuaHang:
        """POST /Order/Add. 21 trường bắt buộc; ServiceId=12491; chống trùng 5 khoá."""
        try:
            ctx = self._ctx_ghi(don, bat_buoc_carrier=True)
            payload = self._dung_payload_order_add(don, ctx)
        except (ValueError, PermissionError) as e:
            rid = ""
            try:
                rid = self._kiem_request_id(uuid.uuid4().hex)
            except ValueError:
                pass
            return self._ket_qua_tu_choi("createOrder", str(e), rid)

        khoa = self._khoa_so("createOrder", ctx)
        cu = self._lay_so(khoa)
        if cu is not None:
            return self._phat_lai(cu)

        if self.moi_truong == MOCK and not self.gui_http:
            ma = self._ma_van_don_mock(ctx)
            kq = self._ket_qua_ok("createOrder", ctx["request_id"], ma_van_don=ma, mock=True,
                                  so_truong=len(TRUONG_BAT_BUOC_ORDER_ADD), service_id=DICH_VU_ID)
            self._ghi_so(khoa, kq)
            return self._ban_sao(kq)

        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, data = self._gui_that("createOrder", payload, ctx["request_id"])
        if not kq.ok:
            if kq.timeout:
                kq = self._xu_ly_sau_timeout_tao_don(ctx, kq)
                self._ghi_so(khoa, kq)
            # TỪ CHỐI chắc chắn KHÔNG được cache: không có đơn nào được tạo, nên sửa dữ liệu
            # hoặc làm mới token rồi gọi lại cùng khoá là AN TOÀN. Cache một lỗi 401 sẽ khoá
            # mềm đơn hàng cho tới khi tiến trình khởi động lại — hỏng im lặng.
            return self._ban_sao(kq)
        ma = self._ma_van_don_tu_data(data)
        kq.ma_van_don = ma
        if ma is None:
            kq.tho["thieu_ma_van_don"] = True
            kq.tho["canh_bao"] = (
                "hãng xác nhận thành công nhưng gói trả lời KHÔNG có mã vận đơn — không bịa mã")
        self._ghi_so(khoa, kq)
        return self._ban_sao(kq)

    @staticmethod
    def _ma_van_don_mock(ctx):
        raw = f"{ctx['tenant_id']}|{ctx['carrier_id']}|{ctx['merchant_order_code']}".encode()
        return "BEST" + hashlib.sha256(raw).hexdigest()[:12].upper()

    def updateOrder(self, don, ma_van_don=None) -> KetQuaHang:
        """POST /Order/Update. Gói mock dùng lại 21 trường của Order/Add + WaybillCode."""
        try:
            if not isinstance(don, dict):
                raise ValueError("đơn phải là dict")
            ctx = self._ctx_ghi(don, bat_buoc_carrier=True)
            payload = self._dung_payload_order_add(don, ctx)
            waybill = self._kiem_ma_van_don(
                ma_van_don or don.get("ma_van_don") or don.get("waybill_code")
                or ctx["merchant_order_code"])
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("updateOrder", str(e), "")
        payload["WaybillCode"] = waybill

        khoa = self._khoa_so("updateOrder", ctx)
        cu = self._lay_so(khoa)
        if cu is not None:
            return self._phat_lai(cu)
        if self.moi_truong == MOCK and not self.gui_http:
            kq = self._ket_qua_ok("updateOrder", ctx["request_id"], ma_van_don=waybill, mock=True)
            self._ghi_so(khoa, kq)
            return self._ban_sao(kq)
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, _data = self._gui_that("updateOrder", payload, ctx["request_id"])
        if kq.ok:
            kq.ma_van_don = waybill
        if kq.ok or kq.timeout:
            self._ghi_so(khoa, kq)
        return self._ban_sao(kq)

    def updateAddress(self, don, ma_van_don=None) -> KetQuaHang:
        """POST /Order/UpdateAddress. District thiếu ⇒ đúng một khoảng trắng ' '."""
        try:
            if not isinstance(don, dict):
                raise ValueError("đơn phải là dict")
            ctx = self._ctx_ghi(don, bat_buoc_carrier=True)
            waybill = self._kiem_ma_van_don(
                ma_van_don or don.get("ma_van_don") or don.get("waybill_code")
                or ctx["merchant_order_code"])
            payload = self._dung_payload_update_address(don, ctx, waybill)
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("updateAddress", str(e), "")
        khoa = self._khoa_so("updateAddress", ctx)
        cu = self._lay_so(khoa)
        if cu is not None:
            return self._phat_lai(cu)
        if self.moi_truong == MOCK and not self.gui_http:
            kq = self._ket_qua_ok("updateAddress", ctx["request_id"], ma_van_don=waybill, mock=True)
            self._ghi_so(khoa, kq)
            return self._ban_sao(kq)
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, _data = self._gui_that("updateAddress", payload, ctx["request_id"])
        if kq.ok:
            kq.ma_van_don = waybill
        if kq.ok or kq.timeout:
            self._ghi_so(khoa, kq)
        return self._ban_sao(kq)

    def cancelOrder(self, ma_van_don, ly_do="") -> KetQuaHang:
        """POST /Order/Cancel. Không thử lại mù; timeout ⇒ UNKNOWN + cờ đối soát."""
        try:
            if isinstance(ma_van_don, dict):
                don = ma_van_don
                waybill = self._kiem_ma_van_don(
                    don.get("ma_van_don") or don.get("waybill_code") or don.get("ma_don"))
                ctx = self._ctx_ghi(don, bat_buoc_carrier=True)
                payload = self._dung_payload_huy(ctx, waybill, ly_do or don.get("ly_do", ""))
            else:
                waybill = self._kiem_ma_van_don(ma_van_don)
                ctx = self._ctx_theo_ma(waybill, "cancel")
                payload = self._dung_payload_huy(ctx, waybill, ly_do)
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("cancelOrder", str(e), "")

        khoa = self._khoa_so("cancelOrder", ctx)
        cu = self._lay_so(khoa)
        if cu is not None:
            return self._phat_lai(cu)
        if self.moi_truong == MOCK and not self.gui_http:
            kq = self._ket_qua_ok("cancelOrder", ctx["request_id"], ma_van_don=waybill, mock=True)
            self._ghi_so(khoa, kq)
            return self._ban_sao(kq)
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, _data = self._gui_that("cancelOrder", payload, ctx["request_id"])
        if kq.ok:
            kq.ma_van_don = waybill
        elif kq.timeout:
            kq.tho["can_doi_soat"] = True
        if kq.ok or kq.timeout:
            self._ghi_so(khoa, kq)
        return self._ban_sao(kq)

    # =============================================================================================
    # 9. TRA CỨU — TỐI ĐA 10 MÃ/LẦN
    # =============================================================================================
    @staticmethod
    def _danh_sach_ma(danh_sach, gioi_han, ten_thao_tac):
        if isinstance(danh_sach, str):
            ds = [danh_sach]
        elif isinstance(danh_sach, (list, tuple)):
            ds = list(danh_sach)
        else:
            raise ValueError(f"{ten_thao_tac}: cần một mã (str) hoặc danh sách mã")
        if not ds:
            raise ValueError(f"{ten_thao_tac}: danh sách mã RỖNG")
        ra = []
        for ma in ds:
            if not isinstance(ma, str):
                raise ValueError(f"{ten_thao_tac}: mã vận đơn phải là chuỗi")
            ma = ma.strip()
            if not ma:
                raise ValueError(f"{ten_thao_tac}: có mã vận đơn RỖNG")
            if len(ma) > 128:
                raise ValueError(f"{ten_thao_tac}: mã vận đơn quá dài (>128)")
            _kiem_khong_dieu_khien(ma, "mã vận đơn")
            if ma in ra:
                raise ValueError(f"{ten_thao_tac}: mã vận đơn TRÙNG trong cùng một lượt")
            ra.append(ma)
        if len(ra) > gioi_han:
            raise ValueError(
                f"{ten_thao_tac}: tối đa {gioi_han} mã/lần, nhận {len(ra)} — "
                "KHÔNG gửi, KHÔNG cắt bớt im lặng")
        return ra

    def queryTracking(self, danh_sach_ma) -> KetQuaHang:
        """POST /Order/Query — tối đa 10 mã/lần. Mã thứ 11 bị TỪ CHỐI trước khi mở socket."""
        try:
            ds = self._danh_sach_ma(danh_sach_ma, GIOI_HAN_QUERY, "queryTracking")
            tenant = self._tenant()
            carrier = self._carrier(bat_buoc=False)
            request_id = self._kiem_request_id(uuid.uuid4().hex)
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("queryTracking", str(e), "")
        payload = {"TenantId": tenant, "CarrierId": carrier, "RequestId": request_id,
                   "WaybillCodes": list(ds)}
        if self.moi_truong == MOCK and not self.gui_http:
            return self._ket_qua_ok(
                "queryTracking", request_id, mock=True, so_ma=len(ds),
                ma_van_don=(ds[0] if len(ds) == 1 else None),
                ket_qua=[{"WaybillCode": ma, "Status": None, "TrangThaiChuan": None,
                          "biet_ma": False, "can_soat": True,
                          "do_tin_cay": tth.TIN_MA_LA} for ma in ds])
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, data = self._gui_that("queryTracking", payload, request_id)
        if not kq.ok:
            if kq.timeout:
                kq.tho["can_doi_soat"] = True
            return kq
        items = self._lay_danh_sach(data, ("Items", "items", "Waybills", "waybills",
                                           "Tracking", "tracking", "Results", "results"))
        if items is None:
            return self._ket_qua_tu_choi(
                "queryTracking", "2xx nhưng không đọc được danh sách kết quả — không đoán",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        if not isinstance(items, list):
            return self._ket_qua_tu_choi(
                "queryTracking", "2xx nhưng kết quả không phải danh sách", request_id,
                so_lan_goi=kq.tho.get("so_lan_goi", 0))
        if len(items) > GIOI_HAN_QUERY:
            return self._ket_qua_tu_choi(
                "queryTracking", f"hãng trả {len(items)} > {GIOI_HAN_QUERY} kết quả — từ chối đọc",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        ket_qua = []
        for item in items:
            if not isinstance(item, dict):
                return self._ket_qua_tu_choi(
                    "queryTracking", "một phần tử kết quả không phải object", request_id,
                    so_lan_goi=kq.tho.get("so_lan_goi", 0))
            ma = self._ma_van_don_tu_data(item)
            trang_thai = self._lay_gia_tri(item, ("Status", "status", "StatusCode",
                                                  "status_code", "trang_thai"))
            anh_xa = self.normalizeStatus(trang_thai) if trang_thai is not None else None
            ket_qua.append({
                "WaybillCode": ma,
                "Status": trang_thai,
                "TrangThaiChuan": None if anh_xa is None else anh_xa.trang_thai_ap,
                "biet_ma": False if anh_xa is None else bool(anh_xa.biet_ma),
                "can_soat": True if anh_xa is None else bool(anh_xa.can_soat),
                "do_tin_cay": tth.TIN_MA_LA if anh_xa is None else anh_xa.do_tin_cay,
            })
        kq.tho["ket_qua"] = ket_qua
        kq.tho["so_ma"] = len(ket_qua)
        kq.ma_van_don = ket_qua[0]["WaybillCode"] if len(ket_qua) == 1 else None
        return kq

    @staticmethod
    def _lay_danh_sach(data, ten_list):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for ten in ten_list:
                if isinstance(data.get(ten), list):
                    return data[ten]
        return None

    def getOrder(self, ma_van_don) -> KetQuaHang:
        """Bí danh của hợp đồng cũ → queryTracking (một mã)."""
        return self.queryTracking(ma_van_don)

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        """Bí danh của hợp đồng cũ → queryTracking (một mã)."""
        return self.queryTracking(ma_van_don)

    # =============================================================================================
    # 10. PHÍ
    # =============================================================================================
    def estimateFee(self, don) -> KetQuaHang:
        """POST /Service/EstimateFee. Mock trả phí theo công thức MOCK, không phải giá hãng."""
        try:
            if not isinstance(don, dict):
                raise ValueError("đơn phải là dict")
            tenant = self._tenant(don)
            carrier = self._carrier(don, bat_buoc=False)
            ctx = {"tenant_id": tenant, "carrier_id": carrier,
                   "merchant_order_code": _chuoi(don.get("ma_don")),
                   "idempotency_key": _chuoi(don.get("idempotency_key") or don.get("idem_key"))
                   or f"fee:{tenant}",
                   "request_id": self._kiem_request_id(uuid.uuid4().hex)}
            payload = self._dung_payload_estimate(don, ctx)
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("estimateFee", str(e), "")
        if self.moi_truong == MOCK and not self.gui_http:
            kl = payload["Weight"]
            phi = 22000 + max(0, (kl - 1000 + 499) // 500) * 5500
            return KetQuaHang(True, phi=int(phi), tho={
                "mock": True, "moi_truong": MOCK, "hang": MA_HANG, "thao_tac": "estimateFee",
                "request_id": ctx["request_id"], "endpoint": DUONG_API["estimateFee"],
                "don_vi": "VND", "service_id": DICH_VU_ID,
                "ghi_chu": "PHÍ MOCK theo công thức nội bộ — KHÔNG phải báo giá của BEST"})
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, data = self._gui_that("estimateFee", payload, ctx["request_id"])
        if not kq.ok:
            if kq.timeout:
                kq.tho["can_doi_soat"] = True
            return kq
        phi = self._lay_gia_tri(data, ("Fee", "fee", "TotalFee", "total_fee", "phi"))
        try:
            phi = _so_nguyen(phi, "phí (VND)", nho_nhat=0, lon_nhat=10**15)
        except ValueError:
            return self._ket_qua_tu_choi(
                "estimateFee", "2xx nhưng không đọc được phí nguyên VND — không đoán",
                ctx["request_id"], so_lan_goi=kq.tho.get("so_lan_goi", 0))
        kq.phi = phi
        kq.tho["don_vi"] = "VND"
        return kq

    def getShippingFee(self, don) -> KetQuaHang:
        return self.estimateFee(don)

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        """Bí danh của hợp đồng cũ → printWaybill (một mã)."""
        return self.printWaybill(ma_van_don)

    # =============================================================================================
    # 11. IN WAYBILL — TỐI ĐA 50 MÃ/LẦN + SSRF
    # =============================================================================================
    def printWaybill(self, danh_sach_ma) -> KetQuaHang:
        """POST /Print/PrintWayBill — tối đa 50 mã/lần; URL trả về KHÔNG được tin.

        URL chỉ được tải nếu trỏ vào hostname đã cho phép. Loopback chỉ mở cho bộ thử MOCK.
        Redirect bị chặn; IP nội bộ/metadata bị chặn. Không đưa URL (có thể chứa token) ra
        kết quả — chỉ đưa tên host và số byte.
        """
        try:
            ds = self._danh_sach_ma(danh_sach_ma, GIOI_HAN_PRINT, "printWaybill")
            tenant = self._tenant()
            carrier = self._carrier(bat_buoc=False)
            request_id = self._kiem_request_id(uuid.uuid4().hex)
        except (ValueError, PermissionError) as e:
            return self._ket_qua_tu_choi("printWaybill", str(e), "")
        payload = {"TenantId": tenant, "CarrierId": carrier, "RequestId": request_id,
                   "WaybillCodes": list(ds)}
        if self.moi_truong == MOCK and not self.gui_http:
            return self._ket_qua_ok(
                "printWaybill", request_id, mock=True, so_ma=len(ds),
                ma_van_don=(ds[0] if len(ds) == 1 else None),
                # Order Core (`don_hang.sieu_du_lieu_nhan_van_don`) đọc khoá `label`; giữ đúng
                # quy ước MOCK của VTP để đường đọc nhãn không vỡ vì một khoá thiếu.
                label="MOCK-PDF",
                ghi_chu="MOCK: không gọi /Print/PrintWayBill thật, không tải PDF")
        loi_token = self._dam_bao_token()
        if loi_token is not None:
            return loi_token
        kq, data = self._gui_that("printWaybill", payload, request_id)
        if not kq.ok:
            if kq.timeout:
                kq.tho["can_doi_soat"] = True
            return kq
        urls = self._lay_danh_sach_url(data)
        if not urls:
            return self._ket_qua_tu_choi(
                "printWaybill", "2xx nhưng không có URL waybill — không đoán URL",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        if len(urls) > GIOI_HAN_PRINT:
            return self._ket_qua_tu_choi(
                "printWaybill", f"hãng trả {len(urls)} URL > {GIOI_HAN_PRINT} — từ chối tải",
                request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
        pdfs = []
        for url in urls:
            if not isinstance(url, str) or not url.strip():
                return self._ket_qua_tu_choi(
                    "printWaybill", "có URL waybill rỗng/không phải chuỗi", request_id,
                    so_lan_goi=kq.tho.get("so_lan_goi", 0))
            try:
                pdf = http_best.tai_waybill(
                    url, timeout=self.het_gio,
                    cho_phep_http_khong_ma_hoa=self.cho_phep_http_khong_ma_hoa,
                    cho_phep_loopback=self._cho_phep_loopback_cho_url(url))
            except (transport.LoiTamThoi, transport.LoiVinhVien) as e:
                # Lệnh in ĐÃ gửi và hãng đã xác nhận; chỉ phần tải PDF hỏng. Toàn bộ thao tác
                # là KHÔNG BIẾT (không phải thất bại chắc chắn) ⇒ timeout=True, mã chuẩn HET_GIO,
                # và KHÔNG đưa URL (có thể chở token) vào kết quả.
                loi = self._ket_qua_khong_biet(
                    "printWaybill",
                    "lệnh in ĐÃ gửi nhưng tải PDF thất bại — KHÔNG BIẾT đã lấy được waybill chưa",
                    request_id, so_lan_goi=kq.tho.get("so_lan_goi", 0))
                loi.tho["in_da_gui"] = True
                loi.tho["tai_pdf_that_bai"] = True
                loi.tho["ly_do_tai"] = getattr(e, "ma", None)
                return loi
            pdfs.append(pdf)
        if len(pdfs) == 1:
            kq.tho["pdf"] = pdfs[0]
        else:
            kq.tho["danh_sach_pdf"] = pdfs
        kq.tho["so_ma"] = len(ds)
        kq.tho["so_tep"] = len(pdfs)
        kq.tho["tong_byte"] = sum(len(x) for x in pdfs)
        kq.tho["dinh_dang"] = "pdf"
        kq.tho["do_lon_byte"] = kq.tho["tong_byte"]
        kq.tho["nguon_tai"] = "host-da-kiem"
        return kq

    def _cho_phep_loopback_cho_url(self, url):
        """Chỉ mở loopback cho URL TRÙNG ĐÚNG host+cổng của stub đang dùng trong MOCK.

        Vì sao không mở "mọi loopback khi MOCK": URL waybill là dữ liệu NGOÀI trả về. Một gói
        bị sửa có thể trỏ về `localhost` và biến bộ thử thành bàn đạp SSRF. Ở đây chỉ đúng
        host+cổng của `base_url` (stub do bộ thử dựng) mới được tải; mọi loopback khác vẫn bị
        `http_best.tach_url` chặn.
        """
        if not (self.moi_truong == MOCK and self.gui_http and self.base_url):
            return False
        try:
            b = urlsplit(self.base_url)
            u = urlsplit(url)
            cong_b = b.port or (443 if b.scheme == "https" else 80)
            cong_u = u.port or (443 if u.scheme == "https" else 80)
            return (u.hostname or "").lower() == (b.hostname or "").lower() and cong_u == cong_b
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _lay_danh_sach_url(data):
        if isinstance(data, dict):
            for ten in ("Urls", "urls", "PrintUrls", "print_urls", "Url", "url",
                        "PrintUrl", "print_url"):
                gt = data.get(ten)
                if isinstance(gt, str) and gt.strip():
                    return [gt.strip()]
                if isinstance(gt, list):
                    return gt
        if isinstance(data, str) and data.strip().startswith(("http://", "https://")):
            return [data.strip()]
        if isinstance(data, list):
            return data
        return None

    # =============================================================================================
    # 12. WEBHOOK + TRẠNG THÁI
    # =============================================================================================
    @classmethod
    def normalizeStatus(cls, ma_trang_thai):
        """Mã trạng thái BEST → trạng thái chuẩn. CHƯA CÓ BẢNG ⇒ không đoán, cần soát.

        Đây không phải chỗ "để trống cho xong": `BANG_TRANG_THAI_BEST` rỗng và
        `TRANG_THAI_DA_XAC_MINH=False` là chốt BẰNG MÃ. Khi có tài liệu thật, điền bảng rồi
        lật cờ; trước đó mọi mã đều `biet_ma=False`, `trang_thai_ap=None`, `can_soat=True`.
        """
        if TRANG_THAI_DA_XAC_MINH and BANG_TRANG_THAI_BEST:
            khoa = str(ma_trang_thai).strip()
            if khoa in BANG_TRANG_THAI_BEST:
                mo_ta, chuan = BANG_TRANG_THAI_BEST[khoa]
                return tth.KetQuaAnhXa(True, chuan, mo_ta, ma_trang_thai,
                                       do_tin_cay=tth.TIN_CAO, can_soat=False,
                                       nguon_tai_lieu=NGUON_TAI_LIEU, ma_hang=MA_HANG)
        return tth.KetQuaAnhXa(
            False, None,
            "BEST: CHƯA CÓ BẢNG MÃ TRẠNG THÁI đã đọc — KHÔNG đoán nghĩa, KHÔNG đổi trạng thái đơn",
            ma_trang_thai, do_tin_cay=tth.TIN_MA_LA, can_soat=True,
            nguon_tai_lieu="CHƯA CÓ TÀI LIỆU BEST (Google Docs không đọc được)", ma_hang=MA_HANG)

    @classmethod
    def normalizeTrackingStatus(cls, trang_thai_hang):
        return cls.normalizeStatus(trang_thai_hang)

    def parseWebhook(self, goi, tenant_id=None, xac_thuc=None):
        """Đọc một sự kiện webhook BEST. KHÔNG gọi mạng, KHÔNG tự nhận là đã xác thực.

        `xac_thuc` là callable tuỳ chọn do nơi gọi cấp (B3 sở hữu chữ ký webhook). Không có nó
        thì `da_xac_thuc=False` — nói thẳng, không giả vờ.
        """
        try:
            tenant = self._tenant({"tenant_id": tenant_id} if tenant_id is not None else None)
        except PermissionError as e:
            return {"ok": False, "ly_do": str(e), "da_xac_thuc": False}
        if isinstance(goi, (bytes, bytearray)):
            if len(goi) > 1024 * 1024:
                return {"ok": False, "ly_do": "gói webhook quá lớn (>1 MiB)", "da_xac_thuc": False}
            try:
                goi = json.loads(bytes(goi).decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return {"ok": False, "ly_do": "webhook không phải JSON UTF-8", "da_xac_thuc": False}
        elif isinstance(goi, str):
            if len(goi.encode("utf-8", "ignore")) > 1024 * 1024:
                return {"ok": False, "ly_do": "gói webhook quá lớn (>1 MiB)", "da_xac_thuc": False}
            try:
                goi = json.loads(goi)
            except ValueError:
                return {"ok": False, "ly_do": "webhook không phải JSON", "da_xac_thuc": False}
        if not isinstance(goi, dict):
            return {"ok": False, "ly_do": "webhook phải là JSON object", "da_xac_thuc": False}

        da_xac_thuc = False
        if xac_thuc is not None:
            try:
                da_xac_thuc = bool(xac_thuc(goi))
            except Exception:
                da_xac_thuc = False
        ma_van_don = self._lay_gia_tri(goi, ("WaybillCode", "waybill_code", "WaybillNo",
                                             "ma_van_don", "OrderCode", "order_code"))
        trang_thai = self._lay_gia_tri(goi, ("Status", "status", "StatusCode", "status_code",
                                             "trang_thai"))
        if not ma_van_don:
            return {"ok": False, "ly_do": "webhook thiếu mã vận đơn", "da_xac_thuc": da_xac_thuc}
        if trang_thai is None:
            return {"ok": False, "ly_do": "webhook thiếu trạng thái", "da_xac_thuc": da_xac_thuc}
        anh_xa = self.normalizeStatus(trang_thai)
        return {
            "ok": True,
            "hang": MA_HANG,
            "tenant_id": tenant,
            "ma_van_don": str(ma_van_don).strip(),
            "ma_su_kien": self._lay_gia_tri(goi, ("EventId", "event_id", "Id", "id")),
            "trang_thai_goc": trang_thai,
            "trang_thai_chuan": anh_xa.trang_thai_ap,
            "biet_ma": bool(anh_xa.biet_ma),
            "can_soat": bool(anh_xa.can_soat),
            "do_tin_cay": anh_xa.do_tin_cay,
            "da_xac_thuc": da_xac_thuc,
            "nguon_tai_lieu": anh_xa.nguon_tai_lieu,
            "ghi_chu": ("CHƯA xác thực chữ ký — B3 phải cấp `xac_thuc` trước khi tin gói này"
                        if not da_xac_thuc else ""),
        }

    # =============================================================================================
    # 13. ĐỐI SOÁT / SỨC KHOẺ (tiện cho vận hành; không thuộc 10 chức năng)
    # =============================================================================================
    def kiem_ket_noi(self) -> dict:
        """Trả mô tả cấu hình KHÔNG kèm secret. Không gọi mạng."""
        return {
            "hang": MA_HANG,
            "moi_truong": self.moi_truong,
            "base_url": self.base_url,
            "http_chua_ma_hoa": CO_HTTP_CHUA_MA_HOA,
            "cho_phep_http_khong_ma_hoa": bool(self.cho_phep_http_khong_ma_hoa),
            "schema_da_xac_minh": bool(self.SCHEMA_DA_XAC_MINH),
            "cho_phep_live": bool(self.CHO_PHEP_LIVE),
            "gui_http": bool(self.gui_http),
            "co_token": bool(self._token),
            "endpoint": dict(DUONG_API),
        }
