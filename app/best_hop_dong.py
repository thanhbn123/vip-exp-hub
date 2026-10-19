# BEST EXPRESS — LỚP HỢP ĐỒNG CHÍNH THỨC (đọc toàn văn DOCX của hãng, 2026-10-19).
#
# Tệp này dùng cho đường kết nối thật (sandbox trước, production chỉ đọc):
#   · builder request đúng tên trường tài liệu: Code/ProductName/SourceCity/...;
#   · parser response đúng envelope Result/Message/Code + data/traceLogs;
#   · bảng 23 mã trạng thái chính thức + nhãn chữ `customer Cancel`;
#   · kiểm tra TLS không gửi credential;
#   · tải PDF qua HTTPS (nâng cấp URL http của hãng) với allowlist chống SSRF;
#   · cổng phê duyệt Owner bằng BIẾN MÔI TRƯỜNG + câu xác nhận; production KHÔNG ghi.
#
# NGUỒN: tệp `Tài liệu API của Best Express Việt Nam.docx` do Owner cung cấp; trích xuất
# `word/document.xml` (gồm bảng) ngày 2026-10-19. Xem `docs/BEST_EXPRESS_DOCX_AUDIT.md`.
#
# KHÔNG ghi credential/token vào log/response. `authorization` chỉ được dựng trong header gửi đi.
import json
import os
import re
import socket
import ssl
import time
from decimal import Decimal, InvalidOperation

import http_best
import transport

MOCK = "mock"
SANDBOX = "sandbox"
PRODUCTION = "production"
MOI_TRUONG_HOP_LE = (MOCK, SANDBOX, PRODUCTION)

HOST_PRODUCTION = http_best.HOST_PRODUCTION
HOST_SANDBOX = http_best.HOST_SANDBOX
HOST_QUERY_TEST = http_best.HOST_QUERY_TEST
BASE_PATH = "/VietNamV3/v3/api/process/sears"
BASE_URL = {
    SANDBOX: f"https://{HOST_SANDBOX}{BASE_PATH}",
    PRODUCTION: f"https://{HOST_PRODUCTION}{BASE_PATH}",
}
BASE_URL_QUERY = {
    SANDBOX: f"https://{HOST_QUERY_TEST}{BASE_PATH}",
    PRODUCTION: f"https://{HOST_PRODUCTION}{BASE_PATH}",
}
DUONG_API = {
    "login": "/User/Login",
    "createOrder": "/Order/Add",
    "updateOrder": "/Order/Update",
    "updateAddress": "/Order/UpdateAddress",
    "cancelOrder": "/Order/Cancel",
    "queryTracking": "/Order/Query",
    "estimateFee": "/Service/EstimateFee",
    "printWaybill": "/Print/PrintWayBill",
}
SERVICE_ID = 12491
SERVICE_ID_EXPRESS = 12490       # tài liệu nêu nhưng hiện chỉ hỗ trợ 12491
JOURNEY_TYPES = (1, 2, 3)
PICKUP_TYPES = (1, 2)
GIOI_HAN_QUERY = 10
GIOI_HAN_PRINT = 50
TOKEN_TTL_DAYS = 30
NGUON = ("Tài liệu API chính thức của BEST EXPRESS Việt Nam — DOCX Owner cung cấp "
         "(đọc toàn văn 2026-10-19; 824 dòng trích xuất)")
TEN_TAI_LIEU = "Tài liệu API của Best Express Việt Nam.docx"
CAU_XAC_NHAN_GHI = "TOI_DONG_Y_GOI_BEST_TEST"
TRANG_THAI_CUSTOMER_CANCEL = "customer Cancel"

# Danh sách trường WIRE đúng tài liệu — dùng để canh builder và để UI/bộ thử đọc.
TRUONG_ORDER_ADD = (
    "Code", "ProductName", "ProductPrice", "CollectAmount", "JourneyType", "PickupType",
    "ServiceId", "Weight", "Width", "Height", "Length", "Note", "NumberOfProducts",
    "BonusProductName1", "BonusProductName2", "SourceCity", "SourceDistrict", "SourceWard",
    "SourceAddress", "SourceName", "SourcePhoneNumber", "DestCity", "DestDistrict",
    "DestWard", "DestAddress", "DestName", "DestPhoneNumber", "ReturnCity", "ReturnDistrict",
    "ReturnWard", "ReturnAddress", "ReturnName", "ReturnPhoneNumber", "ShipmentPayer",
)
# 31 trường nền luôn được gửi. Ba trường Cargo/khuyến mãi chỉ thêm khi có dữ liệu:
# NumberOfProducts, BonusProductName1, BonusProductName2.
TRUONG_ORDER_ADD_NEN = tuple(x for x in TRUONG_ORDER_ADD
                             if x not in ("NumberOfProducts", "BonusProductName1",
                                          "BonusProductName2"))
TRUONG_UPDATE = ("Code", "ProductName", "ProductPrice", "CollectAmount", "ServiceId",
                 "Length", "Height", "Width", "Weight")
TRUONG_UPDATE_ADDRESS = ("Code", "AddressTypeId", "Address", "CityName", "DistrictName",
                         "WardName", "ContactName", "PhoneNumber1", "PhoneNumber2")
TRUONG_ESTIMATE = ("UserName", "ServiceId", "DestCity", "DestDistrict", "DestWard",
                   "SourceCity", "SourceDistrict", "SourceWard", "COD", "ProductPrice",
                   "DiscountCode", "Weight", "Length", "Height", "Width")
TRUONG_QUERY = ("LangType", "Codes")
TRUONG_PRINT = ("codes",)
TRUONG_WEBHOOK = ("code_best", "merchant_order_code", "cod", "product_price", "status",
                  "status_content", "freight_fee", "cod_fee", "insurance_fee", "vat_fee",
                  "return_fee", "discount", "modified_at", "total_fee", "weight", "length",
                  "width", "height")

# 23 mã chính thức. `chung` là ánh xạ nội bộ sang 6 trạng thái giao vận của hub + da_huy.
# `can_soat=True` cho các mã cần người soát (mất/hỏng/lấy thất bại).
BANG_MA = {
    211: ("Đang đi lấy hàng", "cho_lay", False),
    203: ("Lấy hàng không thành công", "cho_lay", True),
    202: ("Lấy hàng thành công", "lay_hang", False),
    301: ("Nhận hàng vào bưu cục Nguồn", "dang_giao", False),
    302: ("Xuất hàng đến trung tâm khai thác", "dang_giao", False),
    303: ("Nhận hàng vào trung tâm khai thác", "dang_giao", False),
    304: ("Xuất hàng khỏi trung tâm khai thác", "dang_giao", False),
    309: ("Nhận hàng vào bưu cục phát hàng", "dang_giao", False),
    601: ("Xuất hàng để đi giao", "dang_giao", False),
    604: ("Giao hàng không thành công", "giao_that_bai", False),
    666: ("Giao hàng thành công", "giao_thanh_cong", False),
    605: ("Xác nhận chuyển hoàn", "hoan_hang", False),
    606: ("Hủy trạng thái trả hàng, mở lại chiều giao", "dang_giao", False),
    701: ("Xuất hàng khỏi bưu cục phát để trả về", "hoan_hang", False),
    702: ("Nhận hàng vào trung tâm khai thác để trả về", "hoan_hang", False),
    703: ("Xuất hàng khỏi trung tâm khai thác để trả về", "hoan_hang", False),
    704: ("Nhận hàng vào bưu cục trả hàng", "hoan_hang", False),
    705: ("Xuất hàng để trả về", "hoan_hang", False),
    707: ("Trả hàng không thành công", "hoan_hang", True),
    708: ("Trả hàng thành công", "hoan_hang", False),
    777: ("Thất lạc", "giao_that_bai", True),
    1000: ("Hư hỏng (Damage)", "giao_that_bai", True),
    2: ("Hủy đơn (customer Cancel)", "da_huy", False),
}
MA_MO_LAI = 606


class LoiHopDong(ValueError):
    """Dữ liệu không đúng hợp đồng tài liệu. Kế thừa ValueError để adapter cũ bắt cùng một chỗ."""
    def __init__(self, ly_do, ma="hop-dong"):
        super().__init__(ly_do)
        self.ly_do = ly_do
        self.ma = ma


# ============================================================================
# 0. TIỆN ÍCH KIỂU DỮ LIỆU — không đoán, không tự quy đổi
# ============================================================================
def _chuoi(v, ten, *, bat_buoc=False, toi_da=1024):
    if v is None:
        if bat_buoc:
            raise LoiHopDong(f"thiếu {ten}", "thieu-truong")
        return ""
    if isinstance(v, (dict, list, tuple, set)):
        raise LoiHopDong(f"{ten} phải là chuỗi", "sai-kieu")
    s = str(v).strip()
    if bat_buoc and not s:
        raise LoiHopDong(f"thiếu {ten}", "thieu-truong")
    if len(s) > toi_da:
        raise LoiHopDong(f"{ten} dài quá {toi_da} ký tự", "qua-dai")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", s):
        raise LoiHopDong(f"{ten} chứa ký tự điều khiển", "ky-tu")
    return s


def _so(v, ten, *, nho_nhat=0, toi_da=10**15):
    if v is None or (isinstance(v, str) and not v.strip()):
        return Decimal(0)
    if isinstance(v, bool):
        raise LoiHopDong(f"{ten} phải là số, không phải boolean", "sai-kieu")
    try:
        d = Decimal(str(v).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        raise LoiHopDong(f"{ten} không phải số hợp lệ", "sai-kieu") from None
    if not d.is_finite():
        raise LoiHopDong(f"{ten} không hữu hạn", "sai-kieu")
    if d < nho_nhat:
        raise LoiHopDong(f"{ten} nhỏ hơn {nho_nhat}", "sai-gia-tri")
    if d > toi_da:
        raise LoiHopDong(f"{ten} quá lớn", "sai-gia-tri")
    return d


def _nguyen(v, ten, *, nho_nhat=0, toi_da=10**15):
    # `_so(None)` trả 0 cho trường TUỲ CHỌN. Nhưng một trường có sàn > 0 (Weight, ServiceId…)
    # mà thiếu thì phải TỪ CHỐI, không được lặng lẽ gửi 0 — BEST sẽ nhận một bưu kiện 0 gram.
    if (v is None or (isinstance(v, str) and not v.strip())) and nho_nhat > 0:
        raise LoiHopDong(f"thiếu {ten}", "thieu-truong")
    d = _so(v, ten, nho_nhat=nho_nhat, toi_da=toi_da)
    if d != d.to_integral_value():
        raise LoiHopDong(f"{ten} phải là số nguyên", "sai-kieu")
    return int(d)


def _dia_chi(city, district, ward, address, ten, *, bat_buoc_city=True,
             bat_buoc_ward=True):
    city = _chuoi(city, f"{ten}.City", bat_buoc=bat_buoc_city, toi_da=255)
    # Tài liệu đánh dấu Ward bằng `*` cho Order/Add và UpdateAddress; EstimateFee thì KHÔNG.
    # Vì vậy đây là tham số, không phải một luật chung cho mọi endpoint.
    ward = _chuoi(ward, f"{ten}.Ward", bat_buoc=bat_buoc_ward, toi_da=255)
    # Địa chỉ 2 cấp mới: District = đúng một khoảng trắng. Không đổi thành rỗng/None.
    district = _chuoi(district, f"{ten}.District", bat_buoc=False, toi_da=255) or " "
    address = _chuoi(address, f"{ten}.Address", bat_buoc=True, toi_da=1024)
    if ward and ward.lower() not in address.lower():
        address = f"{address}, {ward}"
    return city, district, ward or " ", address


def _lay(don, *khoa, default=None):
    for k in khoa:
        if isinstance(don, dict) and don.get(k) not in (None, ""):
            return don[k]
    return default


def _ma(v, ten):
    s = _chuoi(v, ten, bat_buoc=True, toi_da=128)
    if re.search(r"\s", s):
        raise LoiHopDong(f"{ten} chứa khoảng trắng", "sai-gia-tri")
    return s


# ============================================================================
# 1. BUILDER REQUEST — đúng tên trường tài liệu
# ============================================================================
def dung_login(username, password):
    return {"Username": _chuoi(username, "Username", bat_buoc=True, toi_da=255),
            "Password": _chuoi(password, "Password", bat_buoc=True, toi_da=1024)}


def _nguoi_gui(don, *, bat_buoc_ward=True):
    return _dia_chi(don.get("nguoi_gui_tinh"), don.get("nguoi_gui_quan"),
                    don.get("nguoi_gui_xa"), don.get("nguoi_gui_dia_chi"), "Source",
                    bat_buoc_ward=bat_buoc_ward)


def _nguoi_nhan(don, *, bat_buoc_ward=True):
    return _dia_chi(don.get("nguoi_nhan_tinh"), don.get("nguoi_nhan_quan"),
                    don.get("nguoi_nhan_xa"), don.get("nguoi_nhan_dia_chi"), "Dest",
                    bat_buoc_ward=bat_buoc_ward)


def _nguoi_tra(don, *, bat_buoc_ward=True):
    # Không có thông tin trả hàng ⇒ mặc định trả về người gửi (đúng thực tế vận đơn).
    if any(don.get(k) for k in ("nguoi_tra_tinh", "nguoi_tra_quan", "nguoi_tra_dia_chi")):
        return _dia_chi(don.get("nguoi_tra_tinh"), don.get("nguoi_tra_quan"),
                        don.get("nguoi_tra_xa"), don.get("nguoi_tra_dia_chi"), "Return",
                        bat_buoc_ward=bat_buoc_ward)
    return _dia_chi(don.get("nguoi_gui_tinh"), don.get("nguoi_gui_quan"),
                    don.get("nguoi_gui_xa"), don.get("nguoi_gui_dia_chi"), "Return",
                    bat_buoc_ward=bat_buoc_ward)


def dung_order_add(don, ctx):
    """Order/Add chính thức. Trả dict đúng 31 khoá tài liệu (không có TenantId nội bộ)."""
    if not isinstance(don, dict):
        raise LoiHopDong("đơn phải là dict", "sai-kieu")
    code = _ma(don.get("ma_don") or don.get("merchant_order_code") or ctx.get("merchant_order_code"),
               "Code")
    service_id = _nguyen(don.get("service_id") or don.get("dich_vu_id") or SERVICE_ID, "ServiceId")
    if service_id != SERVICE_ID:
        raise LoiHopDong(f"ServiceId phải là {SERVICE_ID} (Eco); nhận {service_id}. "
                         f"Không dùng {SERVICE_ID_EXPRESS}.", "service-id")
    journey = _nguyen(don.get("journey_type") or don.get("loai_hanh_trinh"), "JourneyType")
    if journey not in JOURNEY_TYPES:
        raise LoiHopDong(f"JourneyType phải thuộc {JOURNEY_TYPES}", "journey-type")
    pickup = don.get("pickup_type")
    pickup = 2 if pickup in (None, "") else _nguyen(pickup, "PickupType")
    if pickup not in PICKUP_TYPES:
        raise LoiHopDong("PickupType phải là 1 hoặc 2", "pickup-type")
    src_city, src_dist, src_ward, src_addr = _nguoi_gui(don)
    dst_city, dst_dist, dst_ward, dst_addr = _nguoi_nhan(don)
    ret_city, ret_dist, ret_ward, ret_addr = _nguoi_tra(don)
    payer = don.get("shipment_payer", don.get("nguoi_tra_phi", 0))
    payer = _nguyen(payer, "ShipmentPayer")
    if payer not in (0, 1):
        raise LoiHopDong("ShipmentPayer phải là 0 hoặc 1", "payer")
    so_kien = don.get("number_of_products", don.get("so_kien"))
    if so_kien not in (None, ""):
        so_kien = _nguyen(so_kien, "NumberOfProducts", nho_nhat=1)
        # Tài liệu: khách Cargo ("hàng nặng") chỉ hỗ trợ JourneyType=1 (Giao hàng).
        if so_kien > 1 and journey != 1:
            raise LoiHopDong("Cargo (NumberOfProducts > 1) chỉ hỗ trợ JourneyType=1",
                             "journey-type")
    payload = {
        "Code": code,
        "ProductName": _chuoi(don.get("hang_hoa") or don.get("goods_name") or don.get("product_name"),
                              "ProductName", bat_buoc=True, toi_da=1024),
        "ProductPrice": _so(don.get("gia_tri_khai", don.get("product_price")), "ProductPrice"),
        "CollectAmount": _so(don.get("cod"), "CollectAmount"),
        "JourneyType": journey,
        "PickupType": pickup,
        "ServiceId": SERVICE_ID,
        "Weight": _nguyen(don.get("khoi_luong_gram", don.get("weight_gram")),
                          "Weight (gram)", nho_nhat=1),
        "Width": _nguyen(_lay(don, "chieu_rong_mm", "width_mm", default=0), "Width (mm)"),
        "Height": _nguyen(_lay(don, "chieu_cao_mm", "height_mm", default=0), "Height (mm)"),
        "Length": _nguyen(_lay(don, "chieu_dai_mm", "length_mm", default=0), "Length (mm)"),
        "Note": _chuoi(don.get("ghi_chu") or don.get("note"), "Note", toi_da=1024),
        "SourceCity": src_city,
        "SourceDistrict": src_dist,
        "SourceWard": src_ward,
        "SourceAddress": src_addr,
        "SourceName": _chuoi(don.get("nguoi_gui_ten"), "SourceName", bat_buoc=True, toi_da=255),
        "SourcePhoneNumber": _chuoi(don.get("nguoi_gui_sdt"), "SourcePhoneNumber",
                                    bat_buoc=True, toi_da=255),
        "DestCity": dst_city,
        "DestDistrict": dst_dist,
        "DestWard": dst_ward,
        "DestAddress": dst_addr,
        "DestName": _chuoi(don.get("nguoi_nhan_ten"), "DestName", bat_buoc=True, toi_da=255),
        "DestPhoneNumber": _chuoi(don.get("nguoi_nhan_sdt"), "DestPhoneNumber",
                                  bat_buoc=True, toi_da=255),
        "ReturnCity": ret_city,
        "ReturnDistrict": ret_dist,
        "ReturnWard": ret_ward,
        "ReturnAddress": ret_addr,
        "ReturnName": _chuoi(don.get("nguoi_tra_ten") or don.get("nguoi_gui_ten"),
                             "ReturnName", bat_buoc=True, toi_da=255),
        "ReturnPhoneNumber": _chuoi(don.get("nguoi_tra_sdt") or don.get("nguoi_gui_sdt"),
                                    "ReturnPhoneNumber", bat_buoc=True, toi_da=255),
        "ShipmentPayer": payer,
    }
    if so_kien not in (None, ""):
        payload["NumberOfProducts"] = so_kien
    for k in ("bonus_product_name1", "bonus_product_name2"):
        if don.get(k):
            payload["BonusProductName1" if k.endswith("1") else "BonusProductName2"] = \
                _chuoi(don[k], k, toi_da=1024)
    # Địa chỉ 2 cấp: City + Ward bắt buộc; District = " ". Không nhận ward rỗng.
    for k in ("SourceWard", "DestWard", "ReturnWard"):
        if payload[k] == " ":
            raise LoiHopDong(f"thiếu {k} (địa chỉ 2 cấp cần phường/xã)", "thieu-truong")
    # Chốt chặn: sửa danh sách trường mà quên dựng là hỏng IM LẶNG. 31 trường nền phải có đủ;
    # NumberOfProducts/BonusProductName chỉ thêm khi có dữ liệu.
    thieu = set(TRUONG_ORDER_ADD_NEN) - set(payload)
    if thieu:
        raise LoiHopDong(f"Order/Add thiếu trường tài liệu: {sorted(thieu)}", "thieu-truong")
    # Decimal -> int/float JSON: giữ nguyên giá trị, không làm tròn tiền.
    for k in ("ProductPrice", "CollectAmount"):
        payload[k] = int(payload[k]) if payload[k] == payload[k].to_integral_value() else float(payload[k])
    return payload


def dung_update(don, code):
    if not isinstance(don, dict):
        raise LoiHopDong("đơn phải là dict")
    return {
        "Code": _ma(code, "Code"),
        "ProductName": _chuoi(don.get("hang_hoa") or don.get("product_name"),
                              "ProductName", bat_buoc=True, toi_da=1024),
        "ProductPrice": _so(don.get("gia_tri_khai", don.get("product_price")), "ProductPrice"),
        "CollectAmount": _so(don.get("cod"), "CollectAmount"),
        "ServiceId": SERVICE_ID,
        "Length": _nguyen(_lay(don, "chieu_dai_mm", "length_mm", default=0), "Length"),
        "Height": _nguyen(_lay(don, "chieu_cao_mm", "height_mm", default=0), "Height"),
        "Width": _nguyen(_lay(don, "chieu_rong_mm", "width_mm", default=0), "Width"),
        "Weight": _nguyen(_lay(don, "khoi_luong_gram", "weight_gram", default=0), "Weight"),
    }


def dung_update_address(don, code, address_type=2):
    """Order/UpdateAddress — địa chỉ phải khớp AddressTypeId, không luôn là người nhận.

    1 = Pickup Address (người gửi), 2 = Delivery Address (người nhận),
    3 = Return Address (người nhận hàng trả; mặc định người gửi).
    Bản cũ luôn lấy người nhận cho cả ba loại — sửa địa chỉ lấy hàng/trả hàng sẽ gửi sai người.
    """
    if not isinstance(don, dict):
        raise LoiHopDong("đơn phải là dict")
    at = _nguyen(address_type, "AddressTypeId")
    if at not in (1, 2, 3):
        raise LoiHopDong("AddressTypeId phải là 1/2/3", "address-type")
    if at == 1:
        city, district, ward, addr = _nguoi_gui(don)
        ten, sdt, sdt2 = don.get("nguoi_gui_ten"), don.get("nguoi_gui_sdt"), \
            don.get("nguoi_gui_sdt2")
        nhan = "Source"
    elif at == 2:
        city, district, ward, addr = _nguoi_nhan(don)
        ten, sdt, sdt2 = don.get("nguoi_nhan_ten"), don.get("nguoi_nhan_sdt"), \
            don.get("nguoi_nhan_sdt2")
        nhan = "Dest"
    else:
        city, district, ward, addr = _nguoi_tra(don)
        ten = don.get("nguoi_tra_ten") or don.get("nguoi_gui_ten")
        sdt = don.get("nguoi_tra_sdt") or don.get("nguoi_gui_sdt")
        sdt2 = don.get("nguoi_tra_sdt2") or don.get("nguoi_gui_sdt2")
        nhan = "Return"
    return {
        "Code": _ma(code, "Code"),
        "AddressTypeId": at,
        "Address": addr,
        "CityName": city,
        "DistrictName": district,
        "WardName": ward,
        "ContactName": _chuoi(ten, f"{nhan}.ContactName", bat_buoc=True, toi_da=255),
        "PhoneNumber1": _chuoi(sdt, f"{nhan}.PhoneNumber1", bat_buoc=True, toi_da=255),
        "PhoneNumber2": _chuoi(sdt2, f"{nhan}.PhoneNumber2", toi_da=255),
    }


def dung_cancel(code):
    return {"Code": _ma(code, "Code")}


def dung_query(codes, lang="en-US"):
    ds = _danh_sach(codes, GIOI_HAN_QUERY, "Codes")
    if lang not in ("zh-CN", "en-US"):
        lang = "en-US"
    return {"LangType": lang, "Codes": ds}


def dung_estimate(don):
    if not isinstance(don, dict):
        raise LoiHopDong("đơn phải là dict")
    # EstimateFee: tài liệu KHÔNG đánh dấu Ward bằng `*` (khác Order/Add).
    src_city, src_dist, src_ward, _ = _nguoi_gui(don, bat_buoc_ward=False)
    dst_city, dst_dist, dst_ward, _ = _nguoi_nhan(don, bat_buoc_ward=False)
    return {
        "UserName": _chuoi(don.get("username") or don.get("ten_dang_nhap"), "UserName", toi_da=255),
        "ServiceId": SERVICE_ID,
        "DestCity": dst_city, "DestDistrict": dst_dist, "DestWard": dst_ward,
        "SourceCity": src_city, "SourceDistrict": src_dist, "SourceWard": src_ward,
        "COD": _so(don.get("cod"), "COD"),
        "ProductPrice": _so(don.get("gia_tri_khai", don.get("product_price")), "ProductPrice"),
        "DiscountCode": _chuoi(don.get("discount_code"), "DiscountCode", toi_da=255),
        "Weight": _nguyen(don.get("khoi_luong_gram", don.get("weight_gram")), "Weight", nho_nhat=1),
        "Length": _nguyen(_lay(don, "chieu_dai_mm", "length_mm", default=0), "Length"),
        "Height": _nguyen(_lay(don, "chieu_cao_mm", "height_mm", default=0), "Height"),
        "Width": _nguyen(_lay(don, "chieu_rong_mm", "width_mm", default=0), "Width"),
    }


def dung_print(codes):
    return {"codes": _danh_sach(codes, GIOI_HAN_PRINT, "codes")}


def _danh_sach(codes, gioi_han, ten):
    if isinstance(codes, str):
        ds = [codes]
    elif isinstance(codes, (list, tuple)):
        ds = list(codes)
    else:
        raise LoiHopDong(f"{ten} phải là chuỗi hoặc danh sách", "sai-kieu")
    if not ds:
        raise LoiHopDong(f"{ten} rỗng", "rong")
    ra = []
    for x in ds:
        s = _ma(x, ten)
        if s in ra:
            raise LoiHopDong(f"{ten} có mã trùng", "trung")
        ra.append(s)
    if len(ra) > gioi_han:
        raise LoiHopDong(f"{ten} tối đa {gioi_han}/lần, nhận {len(ra)}", "qua-gioi-han")
    return ra


# ============================================================================
# 2. PARSER RESPONSE — Result/Message/Code + data/traceLogs
# ============================================================================
def _thong_diep(v, toi_da=500):
    s = re.sub(r"[\x00-\x1f\x7f]+", " ", str(v or "")).strip()
    return s[:toi_da]


def boc_ket_qua(goi):
    """Trả `(ok, data, loi, result)`. Hỗ trợ cả envelope mock cũ (`success/data`)."""
    if not isinstance(goi, dict):
        return False, None, "phản hồi không phải JSON object", None
    if "Result" in goi:
        try:
            result = int(goi.get("Result"))
        except (TypeError, ValueError):
            return False, None, "Result không phải số", None
        msg = _thong_diep(goi.get("Message"))
        if result == 1:
            return True, goi, "", result
        if result == 2:
            return False, None, msg or "hãng trả Result=2", result
        return False, None, f"Result lạ: {result}", result
    if "token" in goi:
        return True, goi, "", None
    # tương thích bộ MOCK cũ; đường thật không dùng
    if goi.get("success") is True:
        return True, goi.get("data") or goi, "", None
    if goi.get("success") is False:
        return False, None, _thong_diep(goi.get("message")) or "mock success=false", None
    return False, None, "phản hồi không có Result/token — KHÔNG BIẾT kết quả", None


def boc_token(goi):
    _, data, loi, _ = boc_ket_qua(goi)
    if not data:
        return None, loi
    tok = data.get("token") if isinstance(data, dict) else None
    if not isinstance(tok, str) or not tok.strip():
        return None, "login 2xx nhưng không có token"
    tok = tok.strip()
    if len(tok) > 8192 or any(ord(c) < 0x21 or ord(c) == 0x7F for c in tok):
        return None, "token có ký tự không hợp lệ"
    return tok, ""


def ma_van_don(data):
    if not isinstance(data, dict):
        return None
    for k in ("Code", "code", "WaybillCode", "waybill_code", "code_best", "TrackingNumber"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _thoi_gian(v):
    try:
        n = int(v)
    except (TypeError, ValueError):
        return 0
    return n if n > 10**12 else n * 1000


def chuan_hoa_ma_trang_thai(v):
    """Mã trạng thái BEST → `(số, chuỗi_gốc, là_customer_cancel, biết_mã)`.

    Tài liệu có 22 mã số và một nhãn chữ: `customer Cancel` (KHÔNG phải số). Vì vậy parser
    không được `int()` thẳng rồi vứt sự kiện — làm vậy là biến một ca hủy thật thành "mã lạ".
    `customer Cancel` được ánh xạ về mã 2 (cùng nghĩa đã hủy) nhưng `chuỗi_gốc` vẫn giữ nguyên
    để payload/audit không bịa rằng hãng gửi số 2.
    """
    raw = "" if v is None else str(v).strip()
    if not raw:
        return None, "", False, False
    gon = re.sub(r"[^a-z]", "", raw.lower())
    if gon == "customercancel":
        return 2, raw, True, True
    try:
        so = int(raw)
    except (TypeError, ValueError):
        return None, raw, False, False
    return so, raw, False, so in BANG_MA


def boc_query(goi):
    """Trả `(ok, danh_sach, loi)`. Mỗi item là trạng thái MỚI NHẤT trong traceLogs."""
    ok, data, loi, _ = boc_ket_qua(goi)
    if not ok:
        return False, [], loi
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return False, [], "Query 2xx nhưng không có data[]"
    ra = []
    for item in items:
        if not isinstance(item, dict):
            continue
        code = _chuoi(item.get("code_best") or item.get("code"), "code_best", toi_da=128)
        merchant = _chuoi(item.get("merchant_order_code"), "merchant_order_code", toi_da=128)
        logs = item.get("traceLogs") or item.get("tracelogs") or []
        if not isinstance(logs, list):
            logs = []
        logs = [x for x in logs if isinstance(x, dict)]
        logs.sort(key=lambda x: _thoi_gian(x.get("modified_at")))
        latest = logs[-1] if logs else {}
        status = latest.get("status", item.get("status"))
        status = "" if status is None else str(status).strip()
        so, raw, la_customer_cancel, biet_ma = chuan_hoa_ma_trang_thai(status)
        chung, can_soat = trang_thai_chung(status)
        ra.append({
            "code_best": code,
            "merchant_order_code": merchant,
            "status": status,
            "status_so": so,
            "status_raw": raw,
            "customer_cancel": la_customer_cancel,
            "status_content": _thoi_gian_text(latest.get("status_content")),
            "modified_at": latest.get("modified_at"),
            "trang_thai_chung": chung,
            "can_soat": bool(can_soat or not status),
            "biet_ma": biet_ma,
            "cod": latest.get("cod"),
            "product_price": latest.get("product_price"),
            "freight_fee": latest.get("freight_fee"),
            "cod_fee": latest.get("cod_fee"),
            "insurance_fee": latest.get("insurance_fee"),
            "vat_fee": latest.get("vat_fee"),
            "total_fee": latest.get("total_fee"),
            "weight": latest.get("weight"),
            "length": latest.get("length"),
            "width": latest.get("width"),
            "height": latest.get("height"),
            "traceLogs": logs,
        })
    return True, ra, ""


def _thoi_gian_text(v):
    return _thong_diep(v, 4000)


def boc_estimate(goi):
    """Trả `(ok, data, loi)`. Chuẩn hoá tên khóa thật đo được: hãng trả `Cod`, tài liệu ghi `COD`."""
    ok, data, loi, _ = boc_ket_qua(goi)
    if not ok:
        return False, None, loi
    d = data.get("data") if isinstance(data, dict) else None
    if not isinstance(d, dict):
        return False, None, "EstimateFee 2xx nhưng không có data object"
    # ĐO THẬT 2026-10-19: response trả `"Cod":100000.0` dù request gửi `"COD"`.
    # Chuẩn hoá cả hai để UI không hiện "?" trong khi hãng đã trả số.
    if "COD" not in d and "Cod" in d:
        d["COD"] = d["Cod"]
    if "Cod" not in d and "COD" in d:
        d["Cod"] = d["COD"]
    return True, d, ""


def phi_cuoi(d):
    """Phí cuối để hiển thị: ưu tiên tổng đã gồm VAT + discount, rồi tổng gồm VAT, rồi tổng.

    Tài liệu không chốt trường nào là "phí thu khách"; vì vậy không tự cộng/trừ. Chỉ chọn theo
    thứ tự trên và trả `None` nếu hãng không trả trường nào — UI phải nói "?" chứ không bịa 0.
    """
    if not isinstance(d, dict):
        return None
    for k in ("TotalFeeVATWithDiscount", "TotalFeeWithDiscount", "TotalFeeVAT", "TotalFee",
              "FreightFeeVAT", "FreightFee"):
        v = d.get(k)
        if v is not None and v != "":
            try:
                x = Decimal(str(v))
            except (InvalidOperation, ValueError):
                continue
            if x.is_finite():
                return x
    return None


def boc_print_full(goi):
    """Trả `(ok, {Url, Guid, Result, Message}, loi)`. URL PDF là dữ liệu NGOÀI, không tin."""
    ok, data, loi, _ = boc_ket_qua(goi)
    if not ok:
        return False, None, loi
    if not isinstance(data, dict):
        return False, None, "Print 2xx nhưng không phải object"
    url = data.get("Url") or data.get("url")
    if not isinstance(url, str) or not url.strip():
        return False, None, "Print 2xx nhưng không có Url"
    return True, {"Url": url.strip(), "Guid": data.get("Guid") or data.get("guid"),
                  "Result": data.get("Result"), "Message": data.get("Message")}, ""


def boc_print(goi):
    ok, d, loi = boc_print_full(goi)
    if not ok:
        return False, None, loi
    return True, d["Url"], ""


def trang_thai_chung(ma):
    so, _raw, _customer_cancel, biet_ma = chuan_hoa_ma_trang_thai(ma)
    if so is None or not biet_ma:
        return None, True
    row = BANG_MA.get(so)
    if row is None:
        return None, True
    return row[1], row[2]


# ============================================================================
# 3. CỔNG PHÊ DUYỆT OWNER — KHÔNG sửa cờ của adapter
# ============================================================================
def cua_phe_duyet(moi_truong, cho_phep_that, *, ghi=False, xac_nhan=None):
    """Trả `(ok, ly_do)`. Đây là cổng RIÊNG, không phải CHO_PHEP_LIVE của adapter."""
    mt = str(moi_truong or "").strip().lower()
    if mt not in (SANDBOX, PRODUCTION):
        return False, f"môi trường {moi_truong!r} không phải sandbox/production"
    if ghi and mt == PRODUCTION:
        return False, "PRODUCTION bị khóa cho thao tác ghi — không gửi đơn thật"
    if not cho_phep_that:
        return False, "chưa có xác nhận thao tác thật từ Owner trên giao diện"
    if os.environ.get("VIP_BEST_OWNER_APPROVED") != "1":
        return False, "thiếu VIP_BEST_OWNER_APPROVED=1 trong môi trường backend"
    if not os.environ.get("VIP_BEST_OWNER_APPROVAL_ID", "").strip():
        return False, "thiếu VIP_BEST_OWNER_APPROVAL_ID (mã phê duyệt)"
    if ghi and xac_nhan != CAU_XAC_NHAN_GHI:
        return False, f"thiếu câu xác nhận '{CAU_XAC_NHAN_GHI}'"
    return True, ""


# ============================================================================
# 4. TLS — KHÔNG gửi credential
# ============================================================================
def kiem_tra_tls(host, timeout=10):
    host = str(host or "").strip().lower()
    if host not in (HOST_SANDBOX, HOST_PRODUCTION, HOST_QUERY_TEST):
        return {"ok": False, "host": host, "loi": "host không nằm trong danh sách BEST"}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as s:
            with ctx.wrap_socket(s, server_hostname=host) as ss:
                cert = ss.getpeercert() or {}
                cn = ""
                for rdn in cert.get("subject", ()):
                    for k, v in rdn:
                        if k == "commonName":
                            cn = v
                issuer = ""
                for rdn in cert.get("issuer", ()):
                    for k, v in rdn:
                        if k == "commonName":
                            issuer = v
                return {"ok": True, "host": host, "tls": ss.version(),
                        "cipher": (ss.cipher() or ("?",))[0], "cn": cn,
                        "issuer": issuer, "not_after": cert.get("notAfter"),
                        "xac_minh_chung_chi": True}
    except ssl.SSLCertVerificationError as e:
        return {"ok": False, "host": host, "loi": f"TLS cert không xác minh: {type(e).__name__}"}
    except Exception as e:
        return {"ok": False, "host": host, "loi": f"TLS lỗi: {type(e).__name__}"}


# ============================================================================
# 5. GỬI THẬT — CHỈ SAU CỔNG PHÊ DUYỆT
# ============================================================================
def _url(thao_tac, moi_truong):
    base = BASE_URL_QUERY[SANDBOX] if (thao_tac == "queryTracking" and moi_truong == SANDBOX) \
        else BASE_URL[moi_truong]
    return base.rstrip("/") + DUONG_API[thao_tac]


def _headers(token=None, ems_key=None):
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    if ems_key:
        h["ems-key"] = str(ems_key)[:512]
    return h


def _json_hoa(v):
    """Decimal -> int/float để JSON gửi được; KHÔNG làm tròn đồng tiền."""
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, dict):
        return {k: _json_hoa(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_json_hoa(x) for x in v]
    return v


def _goi_json(url, payload, token=None, ems_key=None, timeout=10):
    payload = _json_hoa(payload)
    try:
        tra = http_best.gui_json(
            url, _headers(token, ems_key), payload, timeout=timeout,
            cho_phep_http_khong_ma_hoa=False, cho_phep_loopback=False)
    except transport.LoiVinhVien as e:
        ma = getattr(e, "ma", "") or ""
        http_status = getattr(e, "ma_http", 0) or 0
        return False, None, f"BEST từ chối/không gửi được: {ma} (HTTP {http_status})".strip(), http_status
    except transport.LoiTamThoi as e:
        return False, None, f"BEST không phản hồi chắc chắn: {getattr(e, 'ma', '')}", 0
    except Exception as e:
        return False, None, f"lỗi gửi BEST: {type(e).__name__}", 0
    try:
        goi = json.loads(tra.than.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return False, None, "BEST trả 2xx nhưng thân không phải JSON", tra.ma_http
    ok, data, loi, _ = boc_ket_qua(goi)
    return ok, data, loi, tra.ma_http


def lay_token_that(credentials, moi_truong, *, cho_phep_that, timeout=10):
    """Đăng nhập thật, trả `(token, meta, loi)`. Token KHÔNG ra khỏi hàm gọi nội bộ."""
    ok, ly_do = cua_phe_duyet(moi_truong, cho_phep_that)
    if not ok:
        return None, {"moi_truong": moi_truong, "blocked": True, "ly_do": ly_do}, ly_do
    if not isinstance(credentials, dict):
        return None, {}, "credentials phải là dict"
    try:
        payload = dung_login(credentials.get("username") or credentials.get("user"),
                             credentials.get("password") or credentials.get("mat_khau"))
    except LoiHopDong as e:
        return None, {"moi_truong": moi_truong}, e.ly_do
    url = _url("login", moi_truong)
    ok, data, loi, http_status = _goi_json(
        url, payload, ems_key=credentials.get("ems_key"), timeout=timeout)
    meta = {"moi_truong": moi_truong, "endpoint": DUONG_API["login"],
            "http_status": http_status, "base_url": BASE_URL[moi_truong]}
    if not ok:
        return None, meta, loi
    token, loi_token = boc_token(data)
    if not token:
        return None, meta, loi_token
    return token, meta, ""


def dang_nhap_that(credentials, moi_truong, *, cho_phep_that, timeout=10):
    token, meta, loi = lay_token_that(credentials, moi_truong, cho_phep_that=cho_phep_that,
                                      timeout=timeout)
    tls = None
    if not meta.get("blocked"):
        tls = kiem_tra_tls(HOST_SANDBOX if moi_truong == SANDBOX else HOST_PRODUCTION)
    return {"ok": token is not None, "co_token": token is not None,
            "blocked": bool(meta.get("blocked")),
            "moi_truong": moi_truong, "endpoint": DUONG_API["login"],
            "tls": tls, "meta": meta, "loi": loi}


def _goi_co_token(thao_tac, payload, credentials, moi_truong, *, cho_phep_that,
                  ghi=False, xac_nhan=None, timeout=10):
    ok, ly_do = cua_phe_duyet(moi_truong, cho_phep_that, ghi=ghi, xac_nhan=xac_nhan)
    if not ok:
        return False, None, ly_do, 0, {"blocked": True, "ly_do": ly_do}
    token, meta, loi = lay_token_that(credentials, moi_truong, cho_phep_that=cho_phep_that,
                                      timeout=timeout)
    if not token:
        return False, None, loi, 0, {"blocked": False, "ly_do": loi}
    url = _url(thao_tac, moi_truong)
    ok, data, loi, http_status = _goi_json(
        url, payload, token=token, ems_key=credentials.get("ems_key"), timeout=timeout)
    meta.update({"endpoint": DUONG_API[thao_tac], "http_status": http_status})
    return ok, data, loi, http_status, meta


def tao_don_that(don, credentials, moi_truong, *, cho_phep_that, xac_nhan=None, timeout=10):
    if moi_truong == PRODUCTION:
        return {"ok": False, "blocked": True, "loi": "PRODUCTION bị khóa cho tạo đơn"}
    try:
        payload = dung_order_add(don, {"merchant_order_code": don.get("ma_don")})
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "createOrder", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=True, xac_nhan=xac_nhan, timeout=timeout)
    return {"ok": ok, "blocked": bool(meta.get("blocked")),
            "ma_van_don": ma_van_don(data) if ok else None,
            "route_code": (data or {}).get("RouteCode") if ok else None,
            "loi": loi, "http_status": http_status, "meta": meta}


def cap_nhat_that(don, credentials, moi_truong, *, cho_phep_that, xac_nhan=None, timeout=10):
    """Order/Update — 9 trường tài liệu. Chỉ sandbox; production bị khoá."""
    if moi_truong == PRODUCTION:
        return {"ok": False, "blocked": True, "loi": "PRODUCTION bị khóa cho cập nhật đơn"}
    code = (don or {}).get("ma_van_don") or (don or {}).get("waybill_code") or \
        (don or {}).get("ma_don")
    try:
        payload = dung_update(don or {}, code)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "updateOrder", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=True, xac_nhan=xac_nhan, timeout=timeout)
    return {"ok": ok, "blocked": bool(meta.get("blocked")), "loi": loi,
            "http_status": http_status, "meta": meta}


def sua_dia_chi_that(don, credentials, moi_truong, *, cho_phep_that, xac_nhan=None,
                     address_type=None, timeout=10):
    """Order/UpdateAddress — AddressTypeId chọn đúng người gửi/nhận/trả."""
    if moi_truong == PRODUCTION:
        return {"ok": False, "blocked": True, "loi": "PRODUCTION bị khóa cho sửa địa chỉ"}
    code = (don or {}).get("ma_van_don") or (don or {}).get("waybill_code") or \
        (don or {}).get("ma_don")
    at = address_type if address_type is not None else (don or {}).get("address_type_id", 2)
    try:
        payload = dung_update_address(don or {}, code, at)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "updateAddress", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=True, xac_nhan=xac_nhan, timeout=timeout)
    return {"ok": ok, "blocked": bool(meta.get("blocked")),
            "address_type_id": payload.get("AddressTypeId"), "loi": loi,
            "http_status": http_status, "meta": meta}


def huy_that(code, credentials, moi_truong, *, cho_phep_that, xac_nhan=None, timeout=10):
    """Order/Cancel — body chỉ có Code; chỉ hủy được trước khi lấy hàng (202)."""
    if moi_truong == PRODUCTION:
        return {"ok": False, "blocked": True, "loi": "PRODUCTION bị khóa cho hủy đơn"}
    try:
        payload = dung_cancel(code)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "cancelOrder", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=True, xac_nhan=xac_nhan, timeout=timeout)
    return {"ok": ok, "blocked": bool(meta.get("blocked")), "loi": loi,
            "http_status": http_status, "meta": meta}


def bao_gia_that(don, credentials, moi_truong, *, cho_phep_that, timeout=10):
    try:
        payload = dung_estimate(don)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "estimateFee", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=False, timeout=timeout)
    return {"ok": ok, "blocked": bool(meta.get("blocked")),
            "data": data if ok else None, "loi": loi,
            "http_status": http_status, "meta": meta}


def tra_cuu_that(codes, credentials, moi_truong, *, cho_phep_that, timeout=10):
    try:
        payload = dung_query(codes)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "queryTracking", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=False, timeout=timeout)
    if not ok:
        return {"ok": False, "blocked": bool(meta.get("blocked")), "data": [],
                "loi": loi, "http_status": http_status, "meta": meta}
    ok2, ds, loi2 = boc_query(data)
    return {"ok": ok2, "blocked": bool(meta.get("blocked")), "data": ds,
            "loi": loi2, "http_status": http_status, "meta": meta}


def in_that(codes, credentials, moi_truong, *, cho_phep_that, timeout=10):
    try:
        payload = dung_print(codes)
    except LoiHopDong as e:
        return {"ok": False, "blocked": False, "loi": e.ly_do, "ma": e.ma}
    ok, data, loi, http_status, meta = _goi_co_token(
        "printWaybill", payload, credentials, moi_truong, cho_phep_that=cho_phep_that,
        ghi=False, timeout=timeout)
    if not ok:
        return {"ok": False, "blocked": bool(meta.get("blocked")), "url": None,
                "loi": loi, "http_status": http_status, "meta": meta}
    ok2, d, loi2 = boc_print_full(data)
    if not ok2:
        return {"ok": False, "blocked": bool(meta.get("blocked")), "url": None,
                "loi": loi2, "http_status": http_status, "meta": meta}
    return {"ok": True, "blocked": bool(meta.get("blocked")), "url": d["Url"],
            "guid": d.get("Guid"), "loi": "", "http_status": http_status, "meta": meta}


def in_pdf_that(codes, credentials, moi_truong, *, cho_phep_that, timeout=10):
    """In + TẢI PDF qua HTTPS. Trả `(ok, pdf_bytes, url, loi, meta)`.

    Tài liệu trả URL dạng `http://...`; `http_best.nang_cap_https_cho_url_hang()` đổi sang
    HTTPS CHỈ khi host nằm đúng danh sách trắng BEST, rồi `tai_waybill()` áp luật SSRF
    (allowlist, chặn IP nội bộ, chặn redirect, Content-Type phải là PDF). Không tải bằng HTTP.
    """
    kq = in_that(codes, credentials, moi_truong, cho_phep_that=cho_phep_that, timeout=timeout)
    if not kq.get("ok"):
        return False, None, None, kq.get("loi") or "không lấy được URL PDF", kq.get("meta")
    url = kq.get("url")
    url_https = http_best.nang_cap_https_cho_url_hang(url)
    try:
        pdf = http_best.tai_waybill(url_https, timeout=timeout,
                                    cho_phep_http_khong_ma_hoa=False,
                                    cho_phep_loopback=False)
    except transport.LoiVinhVien as e:
        return (False, None, url, f"tải PDF bị từ chối: {getattr(e, 'ma', '')}",
                kq.get("meta"))
    except transport.LoiTamThoi as e:
        return (False, None, url, f"tải PDF không chắc chắn: {getattr(e, 'ma', '')}",
                kq.get("meta"))
    except Exception as e:  # noqa: BLE001
        return False, None, url, f"lỗi tải PDF: {type(e).__name__}", kq.get("meta")
    if not pdf:
        return False, None, url, "PDF rỗng", kq.get("meta")
    meta = dict(kq.get("meta") or {})
    meta["pdf_url_https"] = url_https != url
    meta["pdf_bytes"] = len(pdf)
    return True, pdf, url, "", meta


def thong_tin_hop_dong():
    """Mô tả KHÔNG secret cho UI/trạng thái API."""
    return {
        "nguon": NGUON,
        "endpoints": dict(DUONG_API),
        "base_url": {k: v for k, v in BASE_URL.items()},
        "base_url_query": {k: v for k, v in BASE_URL_QUERY.items()},
        "hosts": [HOST_SANDBOX, HOST_PRODUCTION, HOST_QUERY_TEST],
        "service_id": SERVICE_ID,
        "gioi_han": {"query": GIOI_HAN_QUERY, "print": GIOI_HAN_PRINT},
        "token_ttl_days": TOKEN_TTL_DAYS,
        "so_ma": len(BANG_MA),
        "bang_ma": {str(k): {"mo_ta": v[0], "chung": v[1], "can_soat": v[2]}
                    for k, v in BANG_MA.items()},
        "trang_thai_chu": TRANG_THAI_CUSTOMER_CANCEL,
        # Không lặp lại TÊN trường bí mật ở đây: mô tả công khai chỉ cần header/quy ước.
        "auth": {"header": "Authorization", "scheme": "JWT",
                 "ems_key": "tuỳ chọn — Best Customer Identity Key",
                 "login": "POST /User/Login; token sống 30 ngày"},
        "truong": {"order_add": list(TRUONG_ORDER_ADD), "update": list(TRUONG_UPDATE),
                    "update_address": list(TRUONG_UPDATE_ADDRESS),
                    "estimate": list(TRUONG_ESTIMATE), "query": list(TRUONG_QUERY),
                    "print": list(TRUONG_PRINT), "webhook": list(TRUONG_WEBHOOK)},
        "webhook": {"auth": "JWT", "ack": {"Result": 1, "Message": ""}},
        "http": "https (tài liệu ghi http; TLS đã đo được trên cả ba host)",
        "tai_khoan_test_trong_tai_lieu":
            "Tài khoản test công khai trong tài liệu đã bị khóa/không tồn tại "
            "(đo 2026-10-19: Result=2, Message '[404] The account not found or have been locked'). "
            "Cần tài khoản test do BEST cấp.",
        "ten_tai_lieu": TEN_TAI_LIEU,
    }
